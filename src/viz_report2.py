# -*- coding: utf-8 -*-
"""
viz_report2.py — (report2) **SBR 로의 전환**을 눈으로 증명하는 그림들 + Sionna PHY 파형 검증
================================================================================================
이 모듈이 report2 의 새 헤드라인을 만든다:

  ■ 목표 A — RCS 엔진: 순수 PO → **SBR**(Mitsuba 광선 + PO 적분, 가림 포함)
      report2_sbr_validate.png  : SBR 커널 검증 — 금속구·평판 해석해 대비 격자 수렴
      report2_po_vs_sbr.png     : **가림이 RCS 를 얼마나 부풀렸나** (드론 5종 × 3대역)
      report2_occlusion_3d.png  : PO 가 '조명면'이라 부른 면 vs **광선이 실제로 맞은 면**

  ■ 목표 B — 파형: 자작 OFDM 을 **Sionna PHY 로 교차검증**
      report2_sionna_waveforms.png : CarrierConfig 뉴머롤로지 + OFDMModulator 상관 1.0000

■ 정직하게 — SBR 이 무조건 '더 옳은' 게 아니다 (측정으로 분해했다)
  mavic4pro @3.5 GHz, el=15°, 방위평균:
      PO (재질 가중 + 내부 배터리/PCB)   −16.93 dBsm
      PO (내부 산란체 제외)              −18.67 dBsm     ← 내부 기여 +1.74 dB
      SBR (가림 O)                       −20.93 dBsm     ← 가림 효과 −2.26 dB
  즉 PO→SBR 의 −4.00 dB 는 **두 항의 합**이다:
    ① **가림(−2.26 dB)** — SBR 이 옳다. PO 는 앞 구조에 가려진 뒷면까지 적분했다.
    ② **내부 산란체(−1.74 dB)** — 여기선 **SBR 쪽이 못 하는 것**이다. SBR 은 첫 충돌만
       채택하므로 반투명 셸을 **투과**해 배터리·PCB 를 때리는 경로가 없다(실측: 그 두 그룹의
       광선 적중 수 = **0**). PO 는 그걸 '셸 |Γ| 축소 + 내부 |Γ|=1 합산'으로 근사했었다.
  ⇒ 1-bounce SBR 은 **외피(exterior) RCS** 를 정확히 준다. 내부 투과 기여는 별도 물리다.
     이 리포트는 SBR 값을 채택하되(가림은 실재하고, 내부 근사는 상한 성격), 위 분해를 명시한다.
"""
from __future__ import annotations

import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, build_drone, drone_gamma_map, DRONE_GROUP_MAT
from rcs_po import (mesh_to_points, rcs_from_points, drone_rcs_pattern_bw,
                    angular_smooth, dbsm)

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
C0 = 299792458.0

_NAME = {k: DRONES[k].name.split("  ")[0].replace("DJI ", "") for k in DRONES}
_COL = {"mini5pro": "#1565c0", "mavic4pro": "#2e7d32", "matrice4e": "#ef6c00",
        "s1000plus": "#000000", "phantom4": "#c62828"}
BANDS = [("LTE 1.84 GHz", 1.84e9), ("5G 3.5 GHz", 3.5e9), ("WiFi 5.21 GHz", 5.21e9)]

C_PO, C_SBR = "#9e9e9e", "#00695c"        # PO = 회색(옛 엔진), SBR = 청록(새 엔진)
EL_REF = 15.0                              # 기준 고각(레이더가 드론을 올려다보는 전형각)


# --------------------------------------------------------------------------- #
#  공통 — 그룹 재질 맵 / SBR 호출 래퍼
# --------------------------------------------------------------------------- #
def _gm(pec=False):
    """그룹 → 재질키(문자열) 맵. pec=True 면 전부 |Γ|=1 (고전 PO 비교모드)."""
    if pec:
        return {g: 1.0 for g in DRONE_GROUP_MAT}
    return {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}


def _sbr(key, fc, az, el=EL_REF, pec=False, mesh=None):
    from rcs_sbr import rcs_sbr_batch
    m = mesh if mesh is not None else build_drone(DRONES[key])
    return rcs_sbr_batch(m, _gm(pec), fc, az_deg=az, el_deg=el,
                         cache_key=(key, "pec" if pec else "mat"))


def _po(key, fc, az, el=EL_REF, internals=True, mesh=None):
    m = mesh if mesh is not None else build_drone(DRONES[key])
    g = dict(drone_gamma_map(DRONES[key]))
    if not internals:
        g["battery"] = 0.0; g["pcb"] = 0.0
    P, N, dA, w = mesh_to_points(m, C0 / fc / 7.0, gamma=g)
    return rcs_from_points(P, N, dA, fc, az, el_deg=el, w=w)


# --------------------------------------------------------------------------- #
#  (1) SBR 커널 검증 — 해석해가 있는 표적으로 격자 수렴을 본다
# --------------------------------------------------------------------------- #
def fig_sbr_validate(outdir=FIG, fc=3.5e9):
    """SBR 이 맞다는 근거. 금속구(σ=πr²)·금속평판(σ=4πA²/λ²) 을 격자 간격을 좁혀가며 잰다.

    ⚠ 평판 수직입사는 위상항이 사라져(P·û≡0) 진단력이 약하다 — 커널을 실제로 시험하는 건 **구**다
    (report6 §PO 진단과 같은 주의). 그래서 두 표적을 함께 그리고, 구를 주인공으로 둔다."""
    from rcs_sbr import rcs_sbr
    from geom import uv_sphere, box
    lam = C0 / fc
    divs = np.array([4, 6, 8, 10, 12, 16, 20, 24])
    DEF = 12                                            # rcs_sbr.DEFAULT_DIV

    r = 0.5
    sph = uv_sphere(r, seg=180, rings=90, group="metal")
    sph_exact = np.pi * r ** 2
    a = 0.4
    plate = box(a, a, 0.002, group="metal")
    plate_exact = 4 * np.pi * (a * a) ** 2 / lam ** 2

    # 구는 회전대칭이라 **어느 방위에서 봐도 물리는 같다** — 그런데 SBR 값은 조금씩 다르다.
    # 그 산포가 곧 **광선 격자가 곡면 실루엣 가장자리를 재는 데서 오는 양자화 오차**다.
    # 그래서 8방위를 재서 평균과 min/max 를 함께 그린다 (오차를 숨기지 않고 크기를 보여준다).
    az_j = np.arange(0, 360, 45.0)
    s_sph, s_pla, n_rays, sph_lo, sph_hi = [], [], [], [], []
    for d in divs:
        sp = lam / d
        ss = np.atleast_1d(rcs_sbr(sph, {"metal": "metal"}, fc, az_deg=az_j, el_deg=0.0, spacing=sp))
        s_sph.append(ss.mean()); sph_lo.append(ss.min()); sph_hi.append(ss.max())
        s_pla.append(rcs_sbr(plate, {"metal": "metal"}, fc, az_deg=0.0, el_deg=90.0, spacing=sp))
        n_rays.append(int(np.ceil(2 * (r * 1.15 + 3 * sp) / sp)) ** 2)
    s_sph, s_pla = np.array(s_sph), np.array(s_pla)
    sph_lo, sph_hi = np.array(sph_lo), np.array(sph_hi)
    e_sph = dbsm(s_sph) - dbsm(sph_exact)
    e_pla = dbsm(s_pla) - dbsm(plate_exact)
    e_lo = dbsm(sph_lo) - dbsm(sph_exact)
    e_hi = dbsm(sph_hi) - dbsm(sph_exact)

    fig, axes = plt.subplots(1, 3, figsize=(14.6, 4.5), constrained_layout=True)
    fig.suptitle("The SBR kernel is right — analytic targets", fontsize=14, fontweight="bold")
    fig.supxlabel("Mitsuba rays find the lit surface, PO integrates it. Grid spacing d = "
                  r"$\lambda$/div; the solver default is $\lambda$/12." "\n"
                  "The sphere is the real test: at normal incidence on a plate the phase term vanishes, "
                  "so a plate cannot expose a kernel bug.\n"
                  "The sphere band is 8 look directions (physically identical): it is only ~0.1 dB wide, "
                  "so the solver is repeatable. The error instead OSCILLATES with grid pitch --\n"
                  "the curved silhouette edge is resampled differently at each d. The default "
                  r"$\lambda$/12 lands on a +1.5 dB bump; $\lambda$/10 gives +0.4 dB. Read absolute SBR "
                  "RCS with a ~1.5 dB bar.",
                  fontsize=8.5, color="0.45")

    ax = axes[0]
    ax.fill_between(divs, dbsm(sph_lo), dbsm(sph_hi), color=C_SBR, alpha=0.18,
                    label=f"8 look dirs (spread < {np.max(e_hi-e_lo):.2f} dB)")
    ax.plot(divs, dbsm(s_sph), "o-", color=C_SBR, lw=1.8, ms=5, label="SBR (mean)")
    ax.axhline(dbsm(sph_exact), color="#c62828", ls="--", lw=1.4,
               label=r"analytic $\sigma=\pi r^2$")
    ax.axvline(DEF, color="0.6", ls=":", lw=1.2)
    ax.annotate("default", xy=(DEF, 0.02), xycoords=("data", "axes fraction"),
                fontsize=8, color="0.45", ha="center", va="bottom",
                bbox=dict(fc="white", ec="none", alpha=0.8))
    ax.set_xlabel(r"Rays per wavelength  $\lambda$/d"); ax.set_ylabel("RCS [dBsm]")
    ax.set_title(f"(a) Metal sphere r = {r} m  (r = {r/lam:.1f}" + r"$\lambda$)", fontsize=11)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5)

    ax = axes[1]
    ax.plot(divs, dbsm(s_pla), "o-", color=C_SBR, lw=1.8, ms=5, label="SBR")
    ax.axhline(dbsm(plate_exact), color="#c62828", ls="--", lw=1.4,
               label=r"analytic $\sigma=4\pi A^2/\lambda^2$")
    ax.axvline(DEF, color="0.6", ls=":", lw=1.2)
    ax.set_xlabel(r"Rays per wavelength  $\lambda$/d"); ax.set_ylabel("RCS [dBsm]")
    ax.set_title(f"(b) Metal plate {a}x{a} m, normal incidence", fontsize=11)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5)

    ax = axes[2]
    ax.axhspan(-1, 1, color="#c8e6c9", alpha=0.55, zorder=0, label="+/-1 dB")
    ax.fill_between(divs, e_lo, e_hi, color=C_SBR, alpha=0.18, zorder=1)
    ax.plot(divs, e_sph, "o-", color=C_SBR, lw=1.8, ms=5, label="sphere (8 dirs)")
    ax.plot(divs, e_pla, "s--", color="#1565c0", lw=1.6, ms=5, label="plate")
    ax.axhline(0, color="k", lw=1)
    i_def = int(np.where(divs == DEF)[0][0])
    ax.plot([DEF], [e_sph[i_def]], "*", ms=16, color="#c62828", zorder=5)
    ax.annotate(f"default {r'$\lambda$'}/12\nsphere {e_sph[i_def]:+.2f} dB\n"
                f"plate {e_pla[i_def]:+.2f} dB\n{n_rays[i_def]:,} rays",
                xy=(DEF, e_sph[i_def]), xytext=(15.0, 2.6), fontsize=8.5, color="0.3",
                arrowprops=dict(arrowstyle="->", color="0.5", lw=1))
    ax.set_xlabel(r"Rays per wavelength  $\lambda$/d"); ax.set_ylabel("Error vs analytic [dB]")
    ax.set_title("(c) Convergence", fontsize=11)
    ax.set_ylim(-2.8, 5.0); ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="upper right")

    fn = os.path.join(outdir, "report2_sbr_validate.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[r2]", os.path.relpath(fn))
    return dict(divs=divs.tolist(), sphere_err_db=e_sph.tolist(), plate_err_db=e_pla.tolist(),
                sphere_jitter_db=float(np.max(e_hi - e_lo)),
                default_div=DEF, sphere_err_default=float(e_sph[i_def]),
                plate_err_default=float(e_pla[i_def]), n_rays_default=n_rays[i_def], fn=fn)


# --------------------------------------------------------------------------- #
#  (2) 헤드라인 — 가림이 RCS 를 얼마나 부풀렸나
# --------------------------------------------------------------------------- #
def fig_po_vs_sbr(outdir=FIG, target="mavic4pro", fc=3.5e9, bw=100e6):
    """**이 리포트의 새 헤드라인.** 옛 PO 는 가림이 없어 RCS 를 과대평가했다.

    (a) 같은 드론·같은 방위에서 두 엔진의 패턴 (대역평균 100 MHz + 3° 창 — 널 깊이는 인용 불가)
    (b) 5종 × 3대역 방위평균: PO vs SBR
    (c) 차이의 **분해** — 가림(SBR 이 옳다) / 내부 산란체(SBR 이 못 한다) / 다중반사(무시 가능)"""
    from rcs_sbr import rcs_sbr
    az = np.arange(0, 360, 1.0)
    az2 = np.arange(0, 360, 2.0)

    fig = plt.figure(figsize=(16.5, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.25, 1.0])
    fig.suptitle("Physical optics without ray tracing over-counts the drone",
                 fontsize=14.5, fontweight="bold")
    fig.supxlabel("SBR = Mitsuba rays find the first-hit surface, then PO integrates it. "
                  "The old PO integrated every face with " + r"$\hat n\cdot\hat u>0$"
                  " -- including faces hidden behind the airframe.\n"
                  "Panels (a),(b): band-averaged (100 MHz) and 3" + r"$^\circ$"
                  "-smoothed -- the value a radar actually sees. Null depths are not quotable.",
                  fontsize=8.5, color="0.45")

    # (a) 패턴 대조 (대역평균 + 각도평활)
    ax = fig.add_subplot(gs[0, 0])
    s_po = np.zeros_like(az); s_sb = np.zeros_like(az)
    freqs = np.linspace(fc - bw / 2, fc + bw / 2, 9)
    m = build_drone(DRONES[target])
    for f in freqs:
        s_po += _po(target, f, az, mesh=m)
        s_sb += _sbr(target, f, az, mesh=m)
    s_po /= len(freqs); s_sb /= len(freqs)
    s_po = angular_smooth(s_po, 3.0, 1.0); s_sb = angular_smooth(s_sb, 3.0, 1.0)
    ax.plot(az, dbsm(s_po), color=C_PO, lw=1.6, label=f"PO (no occlusion)   avg {dbsm(s_po.mean()):+.2f}")
    ax.plot(az, dbsm(s_sb), color=C_SBR, lw=1.8, label=f"SBR (occlusion)     avg {dbsm(s_sb.mean()):+.2f}")
    ax.axhline(dbsm(s_po.mean()), color=C_PO, ls="--", lw=1)
    ax.axhline(dbsm(s_sb.mean()), color=C_SBR, ls="--", lw=1)
    ax.set_xlim(0, 360); ax.set_xticks([0, 90, 180, 270, 360])
    ax.set_xlabel("Azimuth [deg]"); ax.set_ylabel("RCS [dBsm]")
    ax.set_title(f"(a) {_NAME[target]} @ {fc/1e9:.1f} GHz, el = {EL_REF:.0f}" + r"$^\circ$", fontsize=11)
    ax.grid(alpha=0.3); ax.legend(fontsize=8.5, loc="lower right")

    # (b) 5종 x 3대역
    ax = fig.add_subplot(gs[0, 1])
    keys = list(DRONES.keys())
    po_m = np.zeros((len(keys), len(BANDS))); sb_m = np.zeros_like(po_m)
    for i, k in enumerate(keys):
        mk = build_drone(DRONES[k])
        for j, (_, f) in enumerate(BANDS):
            po_m[i, j] = dbsm(_po(k, f, az2, mesh=mk).mean())
            sb_m[i, j] = dbsm(_sbr(k, f, az2, mesh=mk).mean())
    x = np.arange(len(keys)); w = 0.13
    base = float(np.floor(min(po_m.min(), sb_m.min()))) - 3.0
    alphas = [0.45, 0.70, 1.0]                  # 대역: 옅음(LTE) → 진함(WiFi)
    for j, (lab, _) in enumerate(BANDS):
        off = (j - 1) * 2 * w
        ax.bar(x + off - w / 2, po_m[:, j] - base, w, bottom=base, color=C_PO, alpha=alphas[j])
        ax.bar(x + off + w / 2, sb_m[:, j] - base, w, bottom=base, color=C_SBR, alpha=alphas[j])
        for i in range(len(keys)):
            ax.text(x[i] + off, max(po_m[i, j], sb_m[i, j]) + 0.35,
                    f"{sb_m[i,j]-po_m[i,j]:+.1f}", ha="center", fontsize=6.6, color="#00695c")
    ax.set_xticks(x); ax.set_xticklabels([_NAME[k] for k in keys], fontsize=8.5)
    ax.set_ylim(base, max(po_m.max(), sb_m.max()) + 3.2)
    ax.set_ylabel("Azimuth-avg RCS [dBsm]")
    ax.set_title("(b) 5 drones x 3 carriers  (numbers = SBR - PO, dB)", fontsize=11)
    ax.grid(axis="y", alpha=0.3)
    from matplotlib.patches import Patch
    h_eng = [Patch(facecolor=C_PO, label="PO (no occlusion)"),
             Patch(facecolor=C_SBR, label="SBR (occlusion)")]
    h_band = [Patch(facecolor="0.35", alpha=alphas[j], label=lab)
              for j, (lab, _) in enumerate(BANDS)]
    lg = ax.legend(handles=h_eng, fontsize=8.2, loc="upper left", framealpha=0.95)
    ax.add_artist(lg)
    ax.legend(handles=h_band, fontsize=7.4, loc="upper left", bbox_to_anchor=(0.0, 0.80),
              ncol=3, framealpha=0.95, title="carrier (bar shade)", title_fontsize=7.4)

    # (c) 차이의 분해 (워터폴)
    ax = fig.add_subplot(gs[0, 2])
    v_po = dbsm(_po(target, fc, az2, mesh=m).mean())
    v_noint = dbsm(_po(target, fc, az2, internals=False, mesh=m).mean())
    v_sbr = dbsm(_sbr(target, fc, az2, mesh=m).mean())
    azc = np.linspace(0, 360, 24, endpoint=False)
    s3 = rcs_sbr(m, _gm(), fc, az_deg=azc, el_deg=EL_REF, max_bounce=3)
    s1 = rcs_sbr(m, _gm(), fc, az_deg=azc, el_deg=EL_REF, max_bounce=1)
    d_mb = dbsm(s3.mean()) - dbsm(s1.mean())

    steps = [("PO\n(material +\ninternals)", v_po, "#9e9e9e"),
             ("- internal\nscatterers\n(SBR cannot\nsee them)", v_noint, "#ff8f00"),
             ("- occlusion\n(SBR is right)", v_sbr, "#00695c"),
             ("+ multi-bounce\n(3 bounces)", v_sbr + d_mb, "#1565c0")]
    xs = np.arange(len(steps))
    lo = min(s[1] for s in steps) - 1.6
    for i, (lab, val, c) in enumerate(steps):
        ax.bar(i, val - lo, 0.62, bottom=lo, color=c)
        ax.text(i, val + 0.18, f"{val:+.2f}", ha="center", fontsize=9, fontweight="bold")
    top = max(s[1] for s in steps)
    for i in range(len(steps) - 1):
        d = steps[i + 1][1] - steps[i][1]
        y = top + 0.6 + 0.42 * i                       # 델타 표기는 막대 위 빈 공간에 계단식으로
        ax.annotate("", xy=(i + 1, y), xytext=(i, y),
                    arrowprops=dict(arrowstyle="->", color="0.45", lw=1.2))
        ax.text(i + 0.5, y + 0.06, f"{d:+.2f} dB", ha="center", va="bottom",
                fontsize=8.2, color="0.2", fontweight="bold")
    ax.set_xticks(xs); ax.set_xticklabels([s[0] for s in steps], fontsize=7.4)
    ax.set_ylim(lo, top + 2.8)
    ax.set_ylabel("Azimuth-avg RCS [dBsm]")
    ax.set_title(f"(c) Where the {v_sbr-v_po:+.2f} dB comes from", fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    fn = os.path.join(outdir, "report2_po_vs_sbr.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[r2]", os.path.relpath(fn))
    return dict(po=float(v_po), po_no_internals=float(v_noint), sbr=float(v_sbr),
                d_internals=float(v_noint - v_po), d_occlusion=float(v_sbr - v_noint),
                d_multibounce=float(d_mb), d_total=float(v_sbr - v_po),
                po_matrix=po_m.tolist(), sbr_matrix=sb_m.tolist(),
                keys=keys, bands=[b[0] for b in BANDS], fn=fn)


# --------------------------------------------------------------------------- #
#  (3) 가림 시각화 — PO 가 센 면 vs 광선이 실제로 맞은 면
# --------------------------------------------------------------------------- #
def _hit_analysis(mesh, fc, az, el, spacing=None):
    """Mitsuba 로 ① 광선 충돌점, ② PO 가 '조명면'이라 부르지만 **실제로는 가려진 면** 을 찾는다.

    반환 dict:
      P_hit   : 광선이 맞은 점 (n,3)
      lit     : 면 인덱스 — n̂·û>0 이고 **실제로 보이는** (SBR 도 PO 도 인정)
      ghost   : 면 인덱스 — n̂·û>0 인데 **앞 구조에 가려진** (PO 만 세는 유령면)
      back    : 나머지(후면)
      area_po : Σ(n̂·û)dA  — PO 가 적분한 투영면적 [m²]
      area_sbr: 광선 적중 수 × d²  — 진짜 실루엣 면적 [m²]"""
    import mitsuba as mi
    from rcs_sbr import _mi_scene_from_mesh, _look
    lam = C0 / fc
    d = spacing or lam / 12
    u = _look(az, el)
    scene, _, _ = _mi_scene_from_mesh(mesh, _gm())

    # ① 평행 광선 격자 (rcs_sbr 과 동일 규약)
    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * 1.15 + 3 * d
    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    tmp = np.array([0., 0., 1.]) if abs(u[2]) < 0.9 else np.array([1., 0., 0.])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))
    si = scene.ray_intersect(mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                                      d=mi.Vector3f(*D.T.astype(np.float32))))
    valid = np.asarray(si.is_valid()).astype(bool)
    P_all = np.asarray(mi.Point3f(si.p)).T
    P_hit = P_all[valid]

    # ② 면 단위 가시성 — 각 면 무게중심에서 레이더 방향(+û)으로 광선을 쏴 탈출하는지 본다
    F = np.asarray(mesh.f)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nhat = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-30)
    cen = (v0 + v1 + v2) / 3.0
    nu = nhat @ u
    front = nu > 0                                     # PO 가 '조명면'이라 부르는 집합
    idx = np.where(front)[0]
    Oc = cen[idx] + 1e-3 * u                           # 자기 자신과의 재교차 방지
    si2 = scene.ray_intersect(mi.Ray3f(o=mi.Point3f(*Oc.T.astype(np.float32)),
                                       d=mi.Vector3f(*np.tile(u, (len(idx), 1)).T.astype(np.float32))))
    blocked = np.asarray(si2.is_valid()).astype(bool)  # 앞을 막는 구조가 있다 → 가려짐

    ghost = idx[blocked]
    lit = idx[~blocked]
    back = np.where(~front)[0]
    return dict(P_hit=P_hit, lit=lit, ghost=ghost, back=back,
                area_po=float(np.sum(np.where(front, nu, 0.0) * area)),
                area_sbr=float(valid.sum() * d * d),
                n_rays=int(O.shape[0]), n_hit=int(valid.sum()),
                u=u, V=V, F=F, area=area,
                area_ghost=float(np.sum(nu[ghost] * area[ghost])),
                area_lit=float(np.sum(nu[lit] * area[lit])))


def fig_occlusion_3d(outdir=FIG, target="mavic4pro", fc=3.5e9, az=0.0, el=EL_REF):
    """**가장 설득력 있는 그림** — 같은 방위에서 PO 가 센 면과 SBR 이 실제로 맞은 면을 나란히.

    빨강 = PO 가 '조명면'(n̂·û>0)이라 적분했지만 **앞 구조에 가려져 광선이 도달하지 못하는 면**.
    이 면들이 옛 PO 의 과대평가를 만들었다."""
    m = build_drone(DRONES[target])
    h = _hit_analysis(m, fc, az, el)
    V, F, u = h["V"], h["F"], h["u"]

    fig = plt.figure(figsize=(15.5, 5.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.0, 0.85])
    fig.suptitle("What PO counted vs what the rays actually hit",
                 fontsize=14.5, fontweight="bold")
    fig.supxlabel("Same drone, same look direction. PO calls every face with "
                  r"$\hat n\cdot\hat u>0$" " illuminated -- but many of them sit behind the "
                  "airframe.\nMitsuba keeps only the first hit, so occlusion is free. "
                  "The hidden faces are what inflated the old RCS.",
                  fontsize=8.5, color="0.45")

    b0, b1 = V.min(0), V.max(0)
    c = (b0 + b1) / 2
    ext = (b1 - b0) * 0.56 + 1e-6                       # 실제 bbox 에 맞춘 축 — 정육면체로 두면
    L = float(ext.max())                                # 납작한 드론이 화면 한가운데 작게 뜬다

    def _setup(ax, title):
        ax.set_xlim(c[0] - ext[0], c[0] + ext[0])
        ax.set_ylim(c[1] - ext[1], c[1] + ext[1])
        ax.set_zlim(c[2] - ext[2], c[2] + ext[2])
        try: ax.set_box_aspect(tuple(ext / ext.max()))   # 등축척 유지(형상 왜곡 금지)
        except Exception: pass
        ax.set_axis_off(); ax.view_init(elev=el + 16, azim=az + 38)
        ax.set_title(title, fontsize=11)
        base = c + u * L * 2.0; tip = c + u * L * 1.05
        ax.quiver(base[0], base[1], base[2], *(tip - base), color="#1565c0", lw=2.4,
                  arrow_length_ratio=0.28)
        ax.text(*(c + u * L * 2.1), "Radar", color="#1565c0", fontsize=9)

    tri = lambda ids: [[V[a], V[b], V[cc]] for (a, b, cc) in F[ids]]

    # (a) PO 의 세계 — 조명면 전부 (가려진 것도 포함)
    #     ⚠ 유령면은 정의상 **앞 구조에 가려져** 있다 → 그냥 그리면 안 보인다.
    #        보이는 조명면을 반투명(alpha 0.30)으로 깔고 유령면을 zorder 위로 올려 '투시'시킨다.
    ax = fig.add_subplot(gs[0, 0], projection="3d")
    ax.add_collection3d(Poly3DCollection(tri(h["back"]), facecolors=(0.86, 0.86, 0.88, 0.10),
                                         edgecolors="none", zorder=1))
    ax.add_collection3d(Poly3DCollection(tri(h["lit"]), facecolors=(1.0, 0.72, 0.0, 0.16),
                                         edgecolors=(0.6, 0.45, 0.0, 0.35), linewidths=0.2, zorder=2))
    ax.add_collection3d(Poly3DCollection(tri(h["ghost"]), facecolors="#c62828",
                                         edgecolors=(0.35, 0, 0, 0.8), linewidths=0.25, zorder=3))
    _setup(ax, "(a) PO: every face with " + r"$\hat n\cdot\hat u>0$" +
           f"\n{len(h['lit']):,} visible (amber) + {len(h['ghost']):,} HIDDEN (red, x-rayed)")

    # (b) SBR 의 세계 — 광선이 실제로 맞은 점
    ax = fig.add_subplot(gs[0, 1], projection="3d")
    ax.add_collection3d(Poly3DCollection(tri(np.arange(len(F))),
                                         facecolors=(0.88, 0.88, 0.90, 0.22),
                                         edgecolors="none", zorder=1))
    P = h["P_hit"]
    ax.scatter(P[:, 0], P[:, 1], P[:, 2], s=5.5, c="#00695c", depthshade=False, alpha=0.95,
               zorder=3)
    _setup(ax, f"(b) SBR: first-hit points only\n{h['n_hit']:,} of {h['n_rays']:,} rays hit")

    # (c) 투영면적 + RCS
    ax = fig.add_subplot(gs[0, 2])
    az2 = np.arange(0, 360, 2.0)
    v_po = dbsm(_po(target, fc, az2, el=el, mesh=m).mean())
    v_sbr = dbsm(_sbr(target, fc, az2, el=el, mesh=m).mean())
    ax2 = ax.twinx()
    xs = np.array([0, 1])
    ax.bar(xs - 0.17, [h["area_po"] * 1e4, h["area_sbr"] * 1e4], 0.3,
           color=["#c62828", "#00695c"], alpha=0.85)
    ax.set_xticks(xs); ax.set_xticklabels(["PO", "SBR"], fontsize=10)
    ax.set_ylabel(r"Projected area [cm$^2$]  (bars)")
    for xi, v in zip(xs - 0.17, [h["area_po"] * 1e4, h["area_sbr"] * 1e4]):
        ax.text(xi, v + 8, f"{v:.0f}", ha="center", fontsize=9.5, fontweight="bold")
    ax2.plot(xs + 0.17, [v_po, v_sbr], "o-", color="0.2", lw=1.8, ms=9)
    for xi, v in zip(xs + 0.17, [v_po, v_sbr]):
        ax2.text(xi, v + 0.35, f"{v:+.2f}", ha="center", fontsize=9.5, color="0.2")
    ax2.set_ylabel("Azimuth-avg RCS [dBsm]  (line)")
    ax2.set_ylim(min(v_po, v_sbr) - 1.6, max(v_po, v_sbr) + 1.8)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, h["area_po"] * 1e4 * 1.28)
    ax.set_title(f"(c) PO integrates {h['area_po']/h['area_sbr']:.2f}x the true silhouette\n"
                 f"-> RCS {v_sbr-v_po:+.2f} dB", fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    fn = os.path.join(outdir, "report2_occlusion_3d.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[r2]", os.path.relpath(fn))
    return dict(n_lit=len(h["lit"]), n_ghost=len(h["ghost"]), n_rays=h["n_rays"],
                n_hit=h["n_hit"], area_po=h["area_po"], area_sbr=h["area_sbr"],
                ratio=h["area_po"] / h["area_sbr"], po=float(v_po), sbr=float(v_sbr), fn=fn)


# --------------------------------------------------------------------------- #
#  (4) 목표 B — 파형을 Sionna PHY 로 (교차검증)
# --------------------------------------------------------------------------- #
def fig_sionna_waveforms(outdir=FIG):
    """자작 OFDM 변조기가 **Sionna 와 비트 단위로 일치**함을 보인다.

    ⚠ 정직하게: **Sionna PHY 에는 WiFi/LTE 가 없다(5G NR 만)**. SSB 생성기도 없다.
      그래서 waveforms.py 를 버리지 않는다 — Sionna 는 **OFDM 엔진이자 검증자**다.
      · 뉴머롤로지: 5G 는 Sionna CarrierConfig 가 3GPP 표를 준다 (우리가 안 짠다).
      · 변조: 세 표준 모두 **Sionna OFDMModulator** 로 재변조해 자작판과 대조한다.
      · 파일럿 배치(CRS/SSB/VHT-LTF): Sionna 에 없다 → 우리가 스펙대로 넣는다."""
    from waveforms_sionna import crosscheck, nr_table, ofdm_from_grid
    from waveforms import all_waveforms

    rows = crosscheck(verbose=False)
    nrows = nr_table(verbose=False)
    wfs = all_waveforms("G3")

    fig = plt.figure(figsize=(16.2, 5.9), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0], width_ratios=[1.35, 1.0, 1.15])
    fig.suptitle("Sionna PHY as the OFDM engine and the referee",
                 fontsize=14.5, fontweight="bold")
    fig.supxlabel("Sionna PHY has 5G NR only -- no 802.11, no LTE, no SSB generator. So waveforms.py stays: "
                  "it places CRS / SSB / VHT-LTF per spec.\n"
                  "What Sionna gives us is (i) the 3GPP numerology from CarrierConfig and (ii) an "
                  "independent OFDM modulator that agrees with ours to -135 dB.",
                  fontsize=8.5, color="0.45")

    # (a) Sionna CarrierConfig 가 준 3GPP 뉴머롤로지 표
    ax = fig.add_subplot(gs[:, 0]); ax.axis("off")
    cols = ["Channel", "SCS", r"$\mu$", "RB", "Subcarriers", "Sym/slot", "Slots/frame", "Slot", "CP"]
    body = [[r["bw"], f"{r['scs_hz']/1e3:.0f} kHz", str(r["mu"]), str(r["n_size_grid"]),
             f"{r['num_subcarriers']:,}", str(r["num_symbols_per_slot"]),
             str(r["num_slots_per_frame"]), f"{r['slot_duration_s']*1e6:.0f} " + r"$\mu$s",
             r["cyclic_prefix"]] for r in nrows if "error" not in r]
    # bbox 로 표의 자리를 못박는다 — loc="center" 는 축 높이에 따라 표가 아래로 흘러 제목과 벌어진다.
    t = ax.table(cellText=body, colLabels=cols, cellLoc="center",
                 bbox=[0.0, 0.42, 1.0, 0.40])
    t.auto_set_font_size(False); t.set_fontsize(8.6)
    for cc in range(len(cols)):
        t[0, cc].set_facecolor("#2e7d32"); t[0, cc].set_text_props(color="white", fontweight="bold")
    for i in range(1, len(body) + 1):
        if body[i - 1][0] == "100 MHz" and body[i - 1][1] == "30 kHz":
            for cc in range(len(cols)):
                t[i, cc].set_facecolor("#e8f5e9")
    ax.text(0.5, 0.90, "(a) 3GPP NR numerology -- read from Sionna CarrierConfig",
            transform=ax.transAxes, ha="center", fontsize=11, fontweight="bold")
    ax.text(0.5, 0.855, "we do not hand-write this table.  Green = the n78 row this report uses.",
            transform=ax.transAxes, ha="center", fontsize=8.8, color="0.4")

    # (b) 교차검증 막대 (NMSE)
    ax = fig.add_subplot(gs[0, 1])
    names = [r["name"].split()[0] for r in rows]
    nmse = [r["nmse_db"] for r in rows]
    ax.barh(np.arange(len(rows)), nmse, 0.55, color=["#1565c0", "#ef6c00", "#2e7d32"])
    ax.set_yticks(np.arange(len(rows))); ax.set_yticklabels(names, fontsize=9)
    for i, r in enumerate(rows):
        ax.text(nmse[i] + 2, i, f"corr {r['corr']:.4f}", va="center", fontsize=8.5, color="0.25")
    ax.set_xlim(min(nmse) - 12, 8)
    ax.set_ylim(-0.7, len(rows) - 0.1)
    ax.axvline(-100, color="0.6", ls="--", lw=1)
    ax.text(-100, -0.62, " float32 floor", fontsize=7.5, color="0.45", va="bottom")
    ax.set_xlabel("NMSE vs Sionna OFDMModulator [dB]")
    ax.set_title("(b) Our modulator == Sionna's", fontsize=10.5)
    ax.grid(axis="x", alpha=0.3)

    # (c) 샘플 수 / 심볼별 CP 여부
    ax = fig.add_subplot(gs[1, 1]); ax.axis("off")
    b2 = [[r["name"].split()[0], f"{r['n']:,}",
           "same" if r["same_cp"] else "per-symbol", f"{r['corr']:.4f}", f"{r['nmse_db']:.0f} dB"]
          for r in rows]
    t2 = ax.table(cellText=b2, colLabels=["Waveform", "Samples", "CP", "Corr.", "NMSE"],
                  loc="center", cellLoc="center")
    t2.auto_set_font_size(False); t2.set_fontsize(8.4); t2.scale(1, 1.7)
    for cc in range(5):
        t2[0, cc].set_facecolor("#1565c0"); t2[0, cc].set_text_props(color="white", fontweight="bold")
    ax.set_title("LTE/NR carry a longer CP on the first symbol of a slot --\n"
                 "feed the per-symbol array or the waveform breaks.", fontsize=8.6, color="0.35", pad=6)

    # (c) NR 파형 시간영역 겹쳐 그리기 + 잔차
    wf = wfs["nr"]
    x_ours = np.asarray(wf.tx, complex)
    x_sio = ofdm_from_grid(np.asarray(wf.grid), int(wf.fft),
                           np.atleast_1d(np.asarray(wf.cp_lens)))
    n = min(len(x_ours), len(x_sio))
    a = x_ours[:n] / (np.sqrt(np.mean(np.abs(x_ours[:n]) ** 2)) + 1e-30)
    b = x_sio[:n] / (np.sqrt(np.mean(np.abs(x_sio[:n]) ** 2)) + 1e-30)
    sl = slice(0, 700)
    ax = fig.add_subplot(gs[0, 2])
    ax.plot(np.real(a[sl]), color="#2e7d32", lw=1.5, label="waveforms.py (ours)")
    ax.plot(np.real(b[sl]), color="#c62828", lw=0.9, ls="--", label="Sionna OFDMModulator")
    ax.set_xlabel("Sample"); ax.set_ylabel("Re{x}")
    ax.set_title("(c) 5G NR time domain -- the two curves coincide", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[1, 2])
    err = 20 * np.log10(np.abs(a - b) + 1e-16)
    ax.plot(err[:6000], color="0.35", lw=0.7)
    ax.axhline(20 * np.log10(np.sqrt(np.mean(np.abs(a - b) ** 2))), color="#c62828", ls="--", lw=1.3,
               label=f"RMS {10*np.log10(np.mean(np.abs(a-b)**2)):.0f} dB")
    ax.set_ylim(-200, -40)
    ax.set_xlabel("Sample"); ax.set_ylabel("|error| [dB]")
    ax.set_title("Residual = float32 rounding, not physics", fontsize=9.5)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    fn = os.path.join(outdir, "report2_sionna_waveforms.png")
    fig.savefig(fn, dpi=130, bbox_inches="tight"); plt.close(fig)
    print("[r2]", os.path.relpath(fn))
    return dict(rows=rows, nr=nrows, fn=fn)


# --------------------------------------------------------------------------- #
def build_all(outdir=FIG):
    os.makedirs(outdir, exist_ok=True)
    out = {}
    out["validate"] = fig_sbr_validate(outdir)
    out["po_vs_sbr"] = fig_po_vs_sbr(outdir)
    out["occlusion"] = fig_occlusion_3d(outdir)
    out["waveforms"] = fig_sionna_waveforms(outdir)
    print("report2 (SBR/Sionna) 그림 완료 →", os.path.relpath(outdir))
    return out


if __name__ == "__main__":
    build_all()
