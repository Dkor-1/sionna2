# -*- coding: utf-8 -*-
"""
sbr_grid_convergence_md.py — ⭐**광선 격자를 촘촘히 하면 날개끝 밖 바닥이 내려가나**

무엇을 묻나
------------
바이스태틱 편(`outputs/report07b_bistatic_md.json`)이 이렇게 적었다:

  우리 SBR 팔의 슬로타임 스펙트럼에는 공칭 날개끝 f_tip **밖**까지 이어지는 광대역 바닥이
  있다. 블레이드 대역 전력 중 f_tip 밖 비율이 **SBR 6.05 % · Sionna 2.12 % · 순수 PO 0.02 %**.

이것이 **광선 격자의 이산화 잡음**이면 격자를 촘촘히 할수록 내려가야 한다. 안 내려가면
원인이 다른 데 있고, 그게 더 큰 발견이다. 이 스크립트가 그 판정을 한다.

단일축
------
기체·자세·회전수·주파수·PRF·표본 수를 `outputs/report07_three_engines.json` 의 `_meta`
에서 **읽어서** 쓰고(하드코딩 없음), **격자 간격 d = λ/div 만** 바꾼다.
사다리: λ/8 · λ/12(생산 기본 `rcs_sbr.DEFAULT_DIV`) · λ/16 · λ/24 · λ/32.

⭐ 세 팔을 같은 자세에서 동시에 낸다 (여기가 이 스크립트의 설계 핵심)
--------------------------------------------------------------------
`sbr_field` 의 광선 격자는 **자세마다 다시 정의된다**:

    ctr  = ½(V.max+V.min)          ← 블레이드가 돌면 bbox 가 흔들려 **원점이 움직인다**
    Rout = max|V−ctr|·pad + 3d     ← 같은 이유로 **격자 크기가 변한다**
    n    = ceil(2·Rout/d)          ← 정수라 **한 칸씩 튄다**
    E    = Σ Γ·exp(j2k(p−ctr)·û)·d²  ← 위상 원점도 그 흔들리는 ctr 이다

즉 «격자 간격» 말고도 슬로타임 방향으로 흔들리는 것이 둘 더 있다. 이걸 갈라야 원인을 안다.

  A. `prod`   생산 그대로. 자세마다 격자·위상원점 재정의.
  B. `phase`  A 의 결과에 exp(+j2k(ctr_i−ctr₀)·û) 를 곱해 **위상 원점만** 고정.
              (사후 보정이라 계산이 0 이다 — ctr_i·û 를 자세마다 기록해 두면 된다.)
  C. `froz`   ⭐**격자 자체를 얼린다** — 모든 자세에서 같은 ctr₀·같은 Rout₀·같은 n₀.
              광선이 실공간의 **같은 자리**를 지나므로 히트점이 자세 사이에 이어진다.

A→B 차이 = 위상원점 흔들림의 몫. B→C 차이 = 격자 이동·크기변경의 몫.
남는 것(C 의 바닥) = 순수한 «히트 켜짐/꺼짐» 이산화 잡음.

⚠ C 는 커널을 고치지 않는다 — 이 파일 안의 `_field_grid()` 가 `rcs_sbr.sbr_field` 의 몸통을
  격자 인자만 열어 그대로 옮긴 것이고, 자세별 격자를 주면 `sbr_field` 와 **수치적으로 같아야**
  한다. `--gate` 가 그것을 검사한다(상대오차 한계 1e-12).

예측 (실험 전에 적는다)
------------------------
날개끝 실루엣이 격자를 가로지르며 광선이 켜졌다 꺼진다. 한 칸 토글의 크기는 Γd², 토글 개수는
(둘레 L/d)×(변위 Δs/d) 이므로 잡음 전력 ∝ (L Δs/d²)·(d²)² = L Δs d². 신호는 |E|²∝A².
  ⇒ **대역밖 비율 ∝ d² ∝ 1/div²** — div 2배마다 −6 dB.
이 기울기가 나오면 «이산화 잡음» 이 맞다. 안 나오면 다른 원인이다.

순수 PO 대조 (같은 사다리를 태운다)
------------------------------------
PO 점구름은 **몸에 붙어 같이 돈다**(라그랑주). 표본이 사라지거나 생기지 않으므로 이산화가
슬로타임 불연속을 만들지 않는다 — 그래서 PO 의 대역밖 비율은 점 간격에 **거의 무관**해야
한다. 이 대조가 «격자냐 점구름이냐» 의 차이를 그대로 보여준다.

    cd sionna2
    # 워커 (격자 하나씩, 병렬로 띄운다)
    SIONNA2_GPU=3 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/sbr_grid_convergence_md.py --div 32
    # 회귀 게이트 (커널과 같은 값인가)
    SIONNA2_GPU=3 ... --gate
    # 집계 + 그림
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/sbr_grid_convergence_md.py --analyze

원장
  outputs/sbr_grid_convergence.json   격자별 대역밖 비율·바닥·시간·수렴 판정
  outputs/sbr_grid_convergence.npz    세 팔의 슬로타임 계열 + 자세별 진단(ctr·û, n, 히트수)
  outputs/figures/sbr_grid_conv_f1.{png,pdf}
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import socket
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402

SRC = os.path.join(_ROOT, "outputs", "report07_three_engines.json")
SRCZ = os.path.join(_ROOT, "outputs", "report07_three_engines.npz")
OUTJ = os.path.join(_ROOT, "outputs", "sbr_grid_convergence.json")
OUTZ = os.path.join(_ROOT, "outputs", "sbr_grid_convergence.npz")
FIGD = os.path.join(_ROOT, "outputs", "figures")
SCRATCH = os.path.join(_ROOT, "outputs", "archive", "sbr_grid_conv_parts")

DIVS = [8, 12, 16, 24, 32]           # ⭐사다리. 12 는 생산 기본(rcs_sbr.DEFAULT_DIV)
PO_DIVS = [8, 11, 16, 24, 32]        # 순수 PO 점구름 사다리 (11 이 생산 기본)
PAD = 1.15                           # sbr_field 기본과 같은 값


def meta():
    """리포트 7 원장의 `_meta` — 이 실험의 모든 세팅이 여기서 온다(하드코딩 금지)."""
    return json.load(open(SRC))["_meta"]


def look(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


# ═══════════════════════════════════════════════════════════════════════════ #
#  격자를 인자로 여는 SBR 장 — `rcs_sbr.sbr_field` 의 몸통 그대로
# ═══════════════════════════════════════════════════════════════════════════ #
def _field_grid(rsb, mesh, group_mat, fc, u, d, ctr, Rout, shells, penetrate=True):
    """복소 산란장 E [m²] 와 진단값.

    `rcs_sbr.sbr_field` 와 **같은 식**이되 `ctr`(격자 중심 = 위상 원점)·`Rout`(격자 반경)을
    호출자가 준다. 자세의 것을 그대로 주면 `sbr_field` 와 수치적으로 같다(`--gate` 가 검사).
    반환 (E, n_grid, n_lit)."""
    import mitsuba as mi
    k = 2.0 * np.pi * float(fc) / rsb.C0
    u = np.asarray(u, float); u = u / np.linalg.norm(u)

    scene, shapes, gammas, matk = rsb._scene_for(mesh, group_mat, None, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    shell_pos = [i for i, gn in enumerate(group_names) if gn in shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        scene_i, shapes_i, gammas_i, matk_i = rsb._scene_for(mesh, group_mat, None, fc,
                                                             exclude=shells)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]

    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))
    ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                   d=mi.Vector3f(*D.T.astype(np.float32)))

    def _field(sc, shptr, gam, mk=None):
        si = sc.ray_intersect(ray)
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        which = np.full(P.shape[0], -1, int)
        for _i, (sp, gm) in enumerate(zip(shptr, gam)):
            hit = np.asarray(si.shape == sp).astype(bool)
            g = np.where(hit, gm, g)
            which = np.where(hit, _i, which)
        sgn = np.sign(Nn @ u); sgn[sgn == 0] = 1.0
        Nn = Nn * sgn[:, None]
        cos_i = Nn @ u
        lit = valid & (cos_i > 1e-6)
        if rsb.ANGLE_GAMMA and mk is not None:
            from materials import gamma_shape as _gsh
            for _i, _key in enumerate(mk):
                if _key is None:
                    continue
                sel = (which == _i) & lit
                if sel.any():
                    g[sel] = g[sel] * _gsh(_key, fc, cos_i[sel])
        return valid, lit, g, np.exp(1j * 2.0 * k * ((P - ctr) @ u)), si

    valid, lit, g, phase, si = _field(scene, shape_ptrs, gammas, matk)
    E = np.sum(np.where(lit, g, 0.0) * phase)
    n_lit = int(lit.sum())
    if do_pen:
        tau = np.zeros(valid.shape[0])
        for i in shell_pos:
            tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                           1.0 - gammas[i] ** 2, tau)
        _, lit2, g2, phase2, _ = _field(scene_i, shptr_i, gammas_i, matk_i)
        E = E + np.sum(np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2)
        n_lit += int((lit2 & (tau > 0)).sum())
    return complex(E) * d * d, n, n_lit


# ═══════════════════════════════════════════════════════════════════════════ #
#  측정기 — 리포트 7b 와 **같은 잣대**를 쓴다 (그래야 6.05 % 와 이어진다)
# ═══════════════════════════════════════════════════════════════════════════ #
def spectrum(E, prf, pad=4):
    E = np.asarray(E, complex)
    w = np.hanning(len(E))
    nf = int(pad * len(E))
    S = np.fft.fftshift(np.abs(np.fft.fft(E * w, nf)))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / prf))
    return f, S


def envelope(f, S, smooth_hz):
    P = np.asarray(S, float) ** 2
    df = float(f[1] - f[0])
    n = max(3, int(round(smooth_hz / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same")


def floor_rel_db(P_env, f, f_lo):
    m = np.abs(f) > f_lo
    return float(10 * np.log10(np.median(P_env[m]) / P_env.max()))


def edge_of(P_env, f, f_body, drop_db=25.0):
    m = np.abs(f) > f_body
    thr = P_env[m].max() * 10 ** (-drop_db / 10.0)
    a = np.abs(f)[m]; p = P_env[m]
    o = np.argsort(a); a, p = a[o], p[o]
    above = np.where(p > thr)[0]
    return float(a[above[-1]]) if above.size else float("nan")


def measure(E, prf, f_tip, f_flash):
    """리포트 7b `mono_ledger_engine_floors_db` 와 **같은 세 숫자** + 레벨."""
    f_body = 0.15 * f_tip
    smooth = 4.0 * f_flash
    f, S = spectrum(np.asarray(E, complex), prf)
    P = envelope(f, S, smooth)
    blade = np.abs(f) > f_body
    out = blade & (np.abs(f) > f_tip)
    return dict(
        frac_power_beyond_ftip=float(P[out].sum() / P[blade].sum()),
        floor_rel_db=floor_rel_db(P, f, 1.5 * f_tip),
        edge_hz=edge_of(P, f, f_body),
        level_db=float(10 * np.log10(np.mean(np.abs(E) ** 2) + 1e-300)),
        ptp_db=float((20 * np.log10(np.abs(E) + 1e-30)).max()
                     - (20 * np.log10(np.abs(E) + 1e-30)).min()),
    )


def spec_env(E, prf, f_flash):
    f, S = spectrum(np.asarray(E, complex), prf)
    return f, envelope(f, S, 4.0 * f_flash)


# ═══════════════════════════════════════════════════════════════════════════ #
#  워커 — 격자 하나
# ═══════════════════════════════════════════════════════════════════════════ #
def run_div(div, n_t=None, gate_only=False):
    os.environ.setdefault("SIONNA2_GPU", "3")
    from gpu import pick
    pick(verbose=True)
    import rcs_sbr as rsb
    from rcs_sbr import sbr_field
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT

    GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    M = meta()
    spec = DRONES[M["drone"]]
    fp = FastPoser(spec)
    rpms = np.asarray(M["rpm_per_rotor"], float)
    prf = float(M["prf_hz"]); FC = float(M["fc_hz"])
    NT = int(n_t or M["n"])
    u = look(M["az_deg"], M["el_deg"])
    lam = rsb.C0 / FC
    d = lam / div
    tt = np.arange(NT) / prf
    ph = rotor_phases(tt, rpms, fp.dirs)
    group_names = sorted(set(np.asarray(fp.g).tolist()))
    shells = rsb._resolve_shells(group_names, GM, None)

    # ── 얼린 격자의 중심·반경: 모든 자세를 덮도록 미리 잰다(광선은 아직 안 쏜다) ──
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    for i in range(NT):
        V = fp.pose(ph[i]).v
        lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    ctr0 = 0.5 * (lo + hi)
    Rmax = 0.0
    for i in range(NT):
        V = fp.pose(ph[i]).v
        Rmax = max(Rmax, float(np.linalg.norm(V - ctr0, axis=1).max()))
    Rout0 = Rmax * PAD + 3 * d

    if gate_only:
        # 회귀 게이트 — 자세별 격자를 주면 커널과 같은 값이 나오는가
        worst = 0.0
        for i in (0, 7, 33, 101):
            mv = fp.pose(ph[i])
            V = np.asarray(mv.v, float)
            c = 0.5 * (V.max(0) + V.min(0))
            R = float(np.linalg.norm(V - c, axis=1).max()) * PAD + 3 * d
            e_mine, _, _ = _field_grid(rsb, mv, GM, FC, u, d, c, R, shells)
            e_ker = sbr_field(mv, GM, FC, u, spacing=d)
            worst = max(worst, abs(e_mine - e_ker) / (abs(e_ker) + 1e-300))
        print(f"[gate] div {div}: max rel err vs rcs_sbr.sbr_field = {worst:.3e}")
        return {"div": div, "gate_max_rel_err": float(worst), "ok": bool(worst < 1e-12)}

    E_prod = np.zeros(NT, complex)
    E_froz = np.zeros(NT, complex)
    ctr_u = np.zeros(NT)          # ctr_i·û  — 위상 원점의 흔들림
    n_grid = np.zeros(NT, int)    # 자세별 격자 한 변 (정수 튐)
    n_lit_p = np.zeros(NT, int)
    n_lit_f = np.zeros(NT, int)

    print(f"[div {div}] d={d*1e3:.3f} mm · 얼린 격자 n0={int(np.ceil(2*Rout0/d))} "
          f"· NT={NT} · prf={prf:.0f}", flush=True)
    t0 = time.time()
    t_prod = t_froz = 0.0
    for i in range(NT):
        mv = fp.pose(ph[i])
        V = np.asarray(mv.v, float)
        c = 0.5 * (V.max(0) + V.min(0))
        R = float(np.linalg.norm(V - c, axis=1).max()) * PAD + 3 * d
        ctr_u[i] = float(c @ u)
        ta = time.time()
        E_prod[i], n_grid[i], n_lit_p[i] = _field_grid(rsb, mv, GM, FC, u, d, c, R, shells)
        tb = time.time()
        E_froz[i], _, n_lit_f[i] = _field_grid(rsb, mv, GM, FC, u, d, ctr0, Rout0, shells)
        tc = time.time()
        t_prod += tb - ta; t_froz += tc - tb
        if i and i % 512 == 0:
            el = time.time() - t0
            print(f"    {i}/{NT}  {el:.0f}s  ETA {(NT-i)/i*el/60:.1f}분", flush=True)
    sec = time.time() - t0
    print(f"[div {div}] ✅ {sec:.0f}s  (prod {t_prod/NT*1e3:.1f} ms/자세 · "
          f"froz {t_froz/NT*1e3:.1f} ms/자세)", flush=True)

    os.makedirs(SCRATCH, exist_ok=True)
    out = os.path.join(SCRATCH, f"div{div:03d}.npz")
    np.savez_compressed(out, E_prod=E_prod, E_froz=E_froz, ctr_u=ctr_u,
                        n_grid=n_grid, n_lit_prod=n_lit_p, n_lit_froz=n_lit_f,
                        div=np.array([div]), d=np.array([d]),
                        ctr0=ctr0, Rout0=np.array([Rout0]), nt=np.array([NT]),
                        sec=np.array([sec]),
                        sec_prod=np.array([t_prod]), sec_froz=np.array([t_froz]))
    print(f"[div {div}] → {out}")
    return {"div": div, "seconds": sec}


# ═══════════════════════════════════════════════════════════════════════════ #
#  순수 PO 사다리 — 점구름은 몸에 붙어 돈다(라그랑주)
# ═══════════════════════════════════════════════════════════════════════════ #
def run_po(n_t=None):
    os.environ.setdefault("SIONNA2_GPU", "3")
    from gpu import pick
    pick(verbose=False)
    from drones import DRONES
    from microdoppler import microdoppler_series
    import rcs_sbr as rsb
    M = meta()
    spec = DRONES[M["drone"]]
    rpms = np.asarray(M["rpm_per_rotor"], float)
    NT = int(n_t or M["n"])
    lam = rsb.C0 / float(M["fc_hz"])
    rows, series = [], {}
    for div in PO_DIVS:
        t0 = time.time()
        _, Ep, _ = microdoppler_series(spec, fc=float(M["fc_hz"]), az=M["az_deg"],
                                       el=M["el_deg"], prf=float(M["prf_hz"]), n_t=NT,
                                       rpm_per_rotor=rpms, spacing=lam / div)
        series[f"po_div{div}"] = Ep
        rows.append(dict(div=div, spacing_m=lam / div, seconds=time.time() - t0))
        print(f"[po div {div}] {rows[-1]['seconds']:.1f}s", flush=True)
    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, "po.npz"), **series,
                        divs=np.array(PO_DIVS),
                        sec=np.array([r["seconds"] for r in rows]))
    return rows


# ═══════════════════════════════════════════════════════════════════════════ #
#  집계 + 판정 + 그림
# ═══════════════════════════════════════════════════════════════════════════ #
def loglog_slope(x, y):
    """log y = a·log x + b 의 a. 대역밖 비율이 d^p 라면 div 에 대해 p 는 −slope 다."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = (x > 0) & (y > 0)
    if m.sum() < 2:
        return float("nan"), float("nan")
    A = np.stack([np.log(x[m]), np.ones(m.sum())], 1)
    coef, res, *_ = np.linalg.lstsq(A, np.log(y[m]), rcond=None)
    pred = A @ coef
    ss = float(np.sum((np.log(y[m]) - np.log(y[m]).mean()) ** 2))
    r2 = float(1 - np.sum((np.log(y[m]) - pred) ** 2) / ss) if ss > 0 else float("nan")
    return float(coef[0]), r2


def analyze(make_fig=True):
    M = meta()
    PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
    FC = float(M["fc_hz"]); lam = 299792458.0 / FC
    u = look(M["az_deg"], M["el_deg"])
    k = 2 * np.pi / lam

    parts = sorted(glob.glob(os.path.join(SCRATCH, "div*.npz")))
    if not parts:
        raise SystemExit(f"워커 결과가 없다: {SCRATCH}/div*.npz")

    rows, keep = [], {}
    NT = None
    for p in parts:
        z = np.load(p)
        div = int(z["div"][0]); d = float(z["d"][0]); nt = int(z["nt"][0])
        NT = nt if NT is None else min(NT, nt)
        Ep = z["E_prod"]; Ef = z["E_froz"]; cu = z["ctr_u"]
        # ⭐B 팔 — 위상 원점만 고정(사후 보정, 계산 0)
        Eph = Ep * np.exp(1j * 2 * k * (cu - cu[0]))
        keep[div] = dict(prod=Ep, phase=Eph, froz=Ef, ctr_u=cu,
                         n_grid=z["n_grid"], n_lit=z["n_lit_prod"])
        r = dict(div=div, spacing_m=d, spacing_mm=d * 1e3,
                 n_grid_min=int(z["n_grid"].min()), n_grid_max=int(z["n_grid"].max()),
                 n_grid_jumps=int(np.sum(np.diff(z["n_grid"]) != 0)),
                 rays_per_pose=int(float(np.mean(z["n_grid"])) ** 2),
                 n_lit_mean=float(z["n_lit_prod"].mean()),
                 n_lit_ptp=int(z["n_lit_prod"].max() - z["n_lit_prod"].min()),
                 ctr_u_ptp_mm=float((cu.max() - cu.min()) * 1e3),
                 ctr_u_phase_ptp_rad=float(2 * k * (cu.max() - cu.min())),
                 seconds_total=float(z["sec"][0]),
                 ms_per_pose_prod=float(z["sec_prod"][0]) / nt * 1e3,
                 ms_per_pose_froz=float(z["sec_froz"][0]) / nt * 1e3)
        for arm, E in (("prod", Ep), ("phase", Eph), ("froz", Ef)):
            for kk, vv in measure(E, PRF, FTIP, FFL).items():
                r[f"{arm}_{kk}"] = vv
        rows.append(r)
    rows.sort(key=lambda r: r["div"])
    divs = [r["div"] for r in rows]

    # ── 대조: 리포트 7 원장의 세 팔 (같은 잣대) ────────────────────────────
    ledger = {}
    if os.path.exists(SRCZ):
        Z = np.load(SRCZ)
        for kk in ("sbr", "po", "sionna"):
            if kk in Z:
                ledger[kk] = measure(np.asarray(Z[kk])[:NT], PRF, FTIP, FFL)

    # 회귀 — 우리 div12 prod 가 원장 sbr 팔과 같은가
    reg = None
    if "sbr" in ledger and 12 in keep:
        a = keep[12]["prod"][:NT]; b = np.asarray(np.load(SRCZ)["sbr"])[:NT]
        rel = np.abs(a - b) / (np.abs(b) + 1e-300)
        reg = dict(n=int(NT), max_rel_err=float(rel.max()),
                   median_rel_err=float(np.median(rel)),
                   n_bit_identical=int(np.sum(a == b)),
                   source="outputs/report07_three_engines.npz['sbr']",
                   note=("div12 = 생산 기본. 완전 동일이 기대값이지만 Mitsuba/OptiX 는 "
                         "부동소수 재현성이 비트 단위로 보장되지 않는다 — 상대오차로 본다."))

    # ── 순수 PO 사다리 ────────────────────────────────────────────────────
    po_rows = []
    pop = os.path.join(SCRATCH, "po.npz")
    if os.path.exists(pop):
        zp = np.load(pop)
        for j, div in enumerate(np.asarray(zp["divs"]).tolist()):
            E = zp[f"po_div{div}"][:NT]
            rr = dict(div=int(div), spacing_m=float(lam / div),
                      seconds=float(zp["sec"][j]))
            rr.update(measure(E, PRF, FTIP, FFL))
            po_rows.append(rr)

    # ── 수렴 판정 ─────────────────────────────────────────────────────────
    def _slopes(arm):
        y = [r[f"{arm}_frac_power_beyond_ftip"] for r in rows]
        s, r2 = loglog_slope(divs, y)
        return dict(values=y, slope_vs_div=s, r2=r2,
                    implied_power_of_d=-s,
                    ratio_first_over_last=float(y[0] / y[-1]) if y[-1] > 0 else None)

    conv = {arm: _slopes(arm) for arm in ("prod", "phase", "froz")}
    y_prod = conv["prod"]["values"]
    # 판정 규칙 — 미리 정한다. 이산화 잡음이면 기울기 ≈ −2 (전력 ∝ d²)
    sl = conv["prod"]["slope_vs_div"]
    drop_db = float(10 * np.log10(y_prod[0] / y_prod[-1])) if y_prod[-1] > 0 else float("nan")
    if not np.isfinite(sl):
        verdict_txt = "판정 불가"
    elif sl > -0.3:
        verdict_txt = ("**수렴하지 않는다** — 격자를 4배 촘촘히 해도 대역밖 비율이 거의 안 "
                       "내려간다. 원인은 광선 밀도가 아니다.")
    elif sl < -1.5:
        verdict_txt = ("**d² 이산화 잡음** — 기울기가 −2 근처다. 격자를 촘촘히 하면 예측대로 "
                       "내려간다.")
    else:
        verdict_txt = ("**부분 수렴** — 내려가되 d² 보다 느리다. 이산화 잡음 위에 격자로 안 "
                       "지워지는 성분이 얹혀 있다.")

    # 순수 PO 가 격자에 얼마나 둔감한가
    po_slope = po_r2 = None
    if len(po_rows) >= 2:
        po_slope, po_r2 = loglog_slope([r["div"] for r in po_rows],
                                       [r["frac_power_beyond_ftip"] for r in po_rows])

    # 생산 격자를 바꿔야 하나 — λ/12 대비 얻는 것과 치르는 것
    r12 = next((r for r in rows if r["div"] == 12), None)
    reco = []
    if r12 is not None:
        for r in rows:
            if r["div"] <= 12:
                continue
            reco.append(dict(
                div=r["div"],
                oob_ratio_vs_div12=float(r["prod_frac_power_beyond_ftip"]
                                         / r12["prod_frac_power_beyond_ftip"]),
                oob_gain_db=float(10 * np.log10(r12["prod_frac_power_beyond_ftip"]
                                                / r["prod_frac_power_beyond_ftip"])),
                cost_ratio_rays=float((r["div"] / 12.0) ** 2),
                cost_ratio_time=float(r["ms_per_pose_prod"] / r12["ms_per_pose_prod"]),
                level_shift_db=float(r["prod_level_db"] - r12["prod_level_db"])))
    # PO 바닥까지 가려면 필요한 div (측정된 기울기로 외삽)
    need_div = None
    if po_rows and np.isfinite(sl) and sl < -0.1 and r12 is not None:
        target = float(np.median([r["frac_power_beyond_ftip"] for r in po_rows]))
        need_div = float(12.0 * (target / r12["prod_frac_power_beyond_ftip"]) ** (1.0 / sl))

    out = dict(
        _meta=dict(
            generated=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            host=socket.gethostname(), script="benchmark/sbr_grid_convergence_md.py",
            gpu=os.environ.get("SIONNA2_GPU"),
            question=("SBR 슬로타임 스펙트럼의 날개끝 밖 광대역 바닥이 **광선 격자의 이산화 "
                      "잡음인가** — 격자를 촘촘히 하면 내려가나."),
            inherited_from="outputs/report07_three_engines.json['_meta'] — 하드코딩 없음",
            drone=M["drone"], name=M["name"], fc_hz=FC, az_deg=M["az_deg"],
            el_deg=M["el_deg"], n=NT, prf_hz=PRF, f_tip_hz=FTIP, f_flash_hz=FFL,
            rpm_per_rotor=M["rpm_per_rotor"], lam_m=lam, pad=PAD,
            divs=divs, po_divs=[r["div"] for r in po_rows],
            arms=dict(
                prod="생산 그대로 — 자세마다 격자 중심 ctr·반경 Rout·격자수 n 을 다시 정한다",
                phase="prod 에 exp(+j2k(ctr_i−ctr₀)·û) 를 곱해 **위상 원점만** 고정(사후 보정)",
                froz="⭐격자를 얼린다 — 모든 자세에 같은 ctr₀·Rout₀·n₀"),
            estimator=("리포트 7b 와 동일: Hann·4배 제로패딩 주기도 → 폭 4·f_flash 이동평균 포락 "
                       "→ 블레이드 대역(|f|>0.15 f_tip) 전력 중 |f|>f_tip 비율"),
            prediction=("실루엣이 격자를 가로지르며 광선이 토글 → 잡음 ∝ d² → "
                        "대역밖 비율의 log-log 기울기 ≈ −2 (div 에 대해)"),
        ),
        rows=rows,
        po_rows=po_rows,
        ledger_report07=ledger,
        regression_div12_vs_ledger=reg,
        convergence=conv,
        po_convergence=dict(slope_vs_div=po_slope, r2=po_r2,
                            values=[r["frac_power_beyond_ftip"] for r in po_rows],
                            note=("PO 점구름은 표면에 붙어 **같이 돈다** — 표본이 켜졌다 꺼지지 "
                                  "않으므로 점 간격이 슬로타임 불연속을 만들지 않는다.")),
        verdict=dict(
            slope_vs_div=sl, r2=conv["prod"]["r2"],
            drop_db_div8_to_div32=drop_db,
            text=verdict_txt,
            arm_split=dict(
                note=("A→B 는 위상 원점 흔들림의 몫, B→C 는 격자 이동·크기변경의 몫, "
                      "C 에 남은 것이 순수 켜짐/꺼짐 이산화 잡음이다."),
                per_div=[dict(div=r["div"],
                              prod=r["prod_frac_power_beyond_ftip"],
                              phase=r["phase_frac_power_beyond_ftip"],
                              froz=r["froz_frac_power_beyond_ftip"],
                              phase_gain_db=float(10 * np.log10(
                                  r["prod_frac_power_beyond_ftip"]
                                  / max(r["phase_frac_power_beyond_ftip"], 1e-30))),
                              froz_gain_db=float(10 * np.log10(
                                  r["phase_frac_power_beyond_ftip"]
                                  / max(r["froz_frac_power_beyond_ftip"], 1e-30))))
                         for r in rows]),
            recommendation=reco,
            div_needed_to_reach_po_floor=need_div,
        ),
    )
    os.makedirs(os.path.dirname(OUTJ), exist_ok=True)
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"→ {OUTJ}")

    sav = {}
    for div, kk in keep.items():
        sav[f"E_prod_div{div}"] = kk["prod"]
        sav[f"E_phase_div{div}"] = kk["phase"]
        sav[f"E_froz_div{div}"] = kk["froz"]
        sav[f"ctr_u_div{div}"] = kk["ctr_u"]
        sav[f"n_grid_div{div}"] = kk["n_grid"]
        sav[f"n_lit_div{div}"] = kk["n_lit"]
    if os.path.exists(pop):
        zp = np.load(pop)
        for kf in zp.files:
            if kf.startswith("po_div"):
                sav[kf] = zp[kf]
    np.savez_compressed(OUTZ, **sav)
    print(f"→ {OUTZ}")

    if make_fig:
        figure(out, keep, po_path=pop if os.path.exists(pop) else None)
    return out


def figure(J, keep, po_path=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import textwrap
    from md_mapstyle import auto_periods, flash_spec, draw

    M = J["_meta"]
    PRF = M["prf_hz"]; FTIP = M["f_tip_hz"]; FFL = M["f_flash_hz"]
    rows = J["rows"]; divs = [r["div"] for r in rows]

    map_divs = [d for d in (8, 12, 32) if d in keep] or divs[:3]
    fig = plt.figure(figsize=(15.0, 9.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.06], hspace=0.42, wspace=0.30,
                          left=0.062, right=0.985, top=0.905, bottom=0.115)

    # ── 윗줄: 맵 자체를 나란히 ────────────────────────────────────────────
    ref = None
    for j, dv in enumerate(map_divs):
        ax = fig.add_subplot(gs[0, j])
        E = keep[dv]["prod"]
        f, t, S, nper = flash_spec(E, PRF, FFL, auto_periods(PRF, FFL))
        if ref is None:
            ref = float((S ** 2).max())
        draw(ax, t, f, S, FTIP, ref=ref)
        ax.set_title(f"SBR map, ray grid $\\lambda$/{dv}", fontsize=11)
        ax.set_xlabel("Time [ms]", fontsize=9)
        if j == 0:
            ax.set_ylabel("Doppler [Hz]", fontsize=9)

    # ── 아랫줄 ①: 스펙트럼 포락 ──────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 0])
    cmap = plt.get_cmap("viridis")
    for i, dv in enumerate(divs):
        f, P = spec_env(keep[dv]["prod"], PRF, FFL)
        ax.plot(f, 10 * np.log10(P / P.max()), lw=1.0,
                color=cmap(i / max(1, len(divs) - 1)), label=f"$\\lambda$/{dv}")
    if po_path:
        zp = np.load(po_path)
        kf = [x for x in zp.files if x.startswith("po_div")]
        if kf:
            E = zp[sorted(kf)[0]][:len(keep[divs[0]]["prod"])]
            f, P = spec_env(E, PRF, FFL)
            ax.plot(f, 10 * np.log10(P / P.max()), lw=1.2, color="crimson", ls="--",
                    label="pure PO")
    ax.axvline(FTIP, color="k", lw=0.8, ls=":")
    ax.axvline(-FTIP, color="k", lw=0.8, ls=":")
    ax.set_xlim(-2.6 * FTIP, 2.6 * FTIP); ax.set_ylim(-140, 3)
    ax.set_xlabel("Doppler [Hz]", fontsize=9)
    ax.set_ylabel("Slow-time spectrum envelope [dB]", fontsize=9)
    ax.set_title("Broadband floor beyond the blade band", fontsize=11)
    ax.legend(fontsize=7.5, ncol=2, loc="lower center", framealpha=0.9)
    ax.grid(alpha=0.25)

    # ── 아랫줄 ②: 수렴 ───────────────────────────────────────────────────
    ax = fig.add_subplot(gs[1, 1])
    for arm, c, mk, lab in (("prod", "#1f77b4", "o", "as shipped"),
                            ("phase", "#ff7f0e", "s", "phase origin frozen"),
                            ("froz", "#2ca02c", "^", "whole ray grid frozen")):
        y = [100 * r[f"{arm}_frac_power_beyond_ftip"] for r in rows]
        ax.plot(divs, y, mk + "-", color=c, ms=5.5, lw=1.4, label=lab)
    if J["po_rows"]:
        yp = [100 * r["frac_power_beyond_ftip"] for r in J["po_rows"]]
        ax.plot([r["div"] for r in J["po_rows"]], yp, "d--", color="crimson", ms=5,
                lw=1.2, label="pure PO (body-fixed cloud)")
    y0 = 100 * rows[0]["prod_frac_power_beyond_ftip"]
    ax.plot(divs, [y0 * (divs[0] / d) ** 2 for d in divs], ":", color="gray", lw=1.4,
            label="$\\propto d^{2}$ reference")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(divs); ax.set_xticklabels([str(d) for d in divs])
    ax.set_xlabel("Rays per wavelength  (grid = $\\lambda$/div)", fontsize=9)
    ax.set_ylabel("Power beyond $f_{tip}$  [% of blade band]", fontsize=9)
    ax.set_title("Does refining the grid remove the floor?", fontsize=11)
    ax.legend(fontsize=7.5, loc="lower left", framealpha=0.9)
    ax.grid(alpha=0.25, which="both")

    # ── 아랫줄 ③: 바닥 레벨 + 비용 ───────────────────────────────────────
    ax = fig.add_subplot(gs[1, 2])
    ax.plot(divs, [r["prod_floor_rel_db"] for r in rows], "o-", color="#1f77b4",
            ms=5.5, label="as shipped")
    ax.plot(divs, [r["froz_floor_rel_db"] for r in rows], "^-", color="#2ca02c",
            ms=5.5, label="grid frozen")
    if J["po_rows"]:
        ax.plot([r["div"] for r in J["po_rows"]],
                [r["floor_rel_db"] for r in J["po_rows"]], "d--", color="crimson",
                ms=5, label="pure PO")
    ax.set_xscale("log"); ax.set_xticks(divs); ax.set_xticklabels([str(d) for d in divs])
    ax.set_xlabel("Rays per wavelength", fontsize=9)
    ax.set_ylabel("Spectrum floor re peak [dB]", fontsize=9)
    ax.set_title("Floor level and its price", fontsize=11)
    ax.grid(alpha=0.25, which="both")
    ax.legend(fontsize=7.5, loc="lower left", framealpha=0.9)
    ax2 = ax.twinx()
    ax2.plot(divs, [r["ms_per_pose_prod"] for r in rows], "x-", color="0.45", lw=1.1,
             ms=5, label="cost")
    ax2.set_ylabel("Time per pose [ms]", fontsize=9, color="0.35")
    ax2.tick_params(axis="y", colors="0.35")

    V = J["verdict"]
    cap = (f"Ray-grid convergence of the SBR micro-Doppler kernel. One axis only: the same "
           f"{M['name']}, pose, rotor speeds, carrier and slow-time grid "
           f"({M['n']} samples at {M['prf_hz']:.0f} Hz); only the ray spacing changes. "
           f"Metric is the report-7b one: fraction of blade-band power that lands beyond the "
           f"nominal tip Doppler {M['f_tip_hz']:.0f} Hz. Log-log slope versus rays per "
           f"wavelength is {V['slope_vs_div']:+.2f} (R2 {V['r2']:.2f}); a pure discretisation "
           f"noise would give -2. Green shows the same kernel with the ray grid frozen in the "
           f"lab frame instead of re-derived from each pose's bounding box.")
    fig.text(0.5, 0.022, textwrap.fill(cap, 178), ha="center", va="bottom", fontsize=8.0)
    fig.suptitle("Is the out-of-band floor a ray-grid artefact?", fontsize=13.5, y=0.968)

    os.makedirs(FIGD, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIGD, f"sbr_grid_conv_f1.{ext}"), dpi=170)
    plt.close(fig)
    print(f"→ {os.path.join(FIGD, 'sbr_grid_conv_f1.png')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--div", type=int, default=None, help="워커: 이 격자 하나만 계산")
    ap.add_argument("--po", action="store_true", help="순수 PO 사다리")
    ap.add_argument("--gate", action="store_true", help="커널 회귀 게이트만")
    ap.add_argument("--analyze", action="store_true", help="집계 + 판정 + 그림")
    ap.add_argument("--fig-only", action="store_true")
    ap.add_argument("--n", type=int, default=None, help="슬로타임 표본 수(기본: 원장 그대로)")
    a = ap.parse_args()

    if a.gate:
        res = [run_div(d, n_t=a.n, gate_only=True) for d in (a.div,) if d] or \
              [run_div(d, n_t=a.n, gate_only=True) for d in DIVS]
        os.makedirs(SCRATCH, exist_ok=True)
        json.dump(res, open(os.path.join(SCRATCH, "gate.json"), "w"), indent=1)
        return
    if a.po:
        run_po(n_t=a.n); return
    if a.div:
        run_div(a.div, n_t=a.n); return
    if a.fig_only:
        J = json.load(open(OUTJ))
        Z = np.load(OUTZ)
        keep = {}
        for kf in Z.files:
            if kf.startswith("E_prod_div"):
                dv = int(kf.split("div")[1])
                keep[dv] = dict(prod=Z[kf], phase=Z[f"E_phase_div{dv}"],
                                froz=Z[f"E_froz_div{dv}"])
        pop = os.path.join(SCRATCH, "po.npz")
        figure(J, keep, po_path=pop if os.path.exists(pop) else None)
        return
    if a.analyze:
        J = analyze()
        print("\n판정:", J["verdict"]["text"])
        return
    ap.error("--div / --po / --gate / --analyze 중 하나를 골라라")


if __name__ == "__main__":
    main()
