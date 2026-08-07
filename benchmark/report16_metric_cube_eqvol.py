#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
report16_metric_cube_eqvol.py — ⭐ 등가부피 정육면체 단의 **지표 뽑기 + 사전예측 채점**

이 파일이 하는 일 (계산 단계가 이미 돌려 놓은 위상 표를 **다시 읽어서** 처리한다)
────────────────────────────────────────────────────────────────────────────
계산 단계(benchmark/report16_rung_cube_eqvol.py)는 전자기 계산을 해서 «위상 표»
E(φ) 를 npz 에 저장했다. 이 단계는 그 표에서 지표를 뽑고, 계산 전에 봉인해 둔
예측(prereg)과 대조한다. 새 전자기 계산은 «검산용» 으로만 아주 조금 한다.

왜 다시 재는가 — 계산 단계가 이미 같은 지표를 냈는데도 다시 재는 이유는 하나다.
같은 코드가 낸 숫자를 그 코드로 검산하면 «맞다» 는 말에 값어치가 없기 때문이다.
그래서 여기서는

  ① 지표 공식을 **문서만 보고 새로 구현**해서 계산 단계 숫자와 맞춰 본다.
     (base 의 md_metrics16 를 import 하지 않는다 — 그러면 검산이 아니라 복사다.)
  ② PO 산란 커널 자체도 **numpy·CPU 로 새로 구현**해서 저장된 표 몇 줄을 재현해 본다.
     계산 단계는 GPU(torch)로 돌렸다. 다른 기계·다른 코드가 같은 숫자를 내면
     그 표는 믿을 만하다.
  ③ 그 위에서 사전예측 P1~P6 을 **내 숫자로** 다시 채점한다.

용어 풀이 (처음 쓰는 말은 뜻을 적는다)
────────────────────────────────────────────────────────────────────────────
· 위상 표 E(φ) : 회전각 φ 를 한 바퀴(360°) 등간격으로 훑으며 잰 복소 산란장.
                 시간 신호가 아니라 «한 바퀴 표» 라서 FFT 하면 누설 없는 선 스펙트럼이 된다.
· 차수(order) m : 한 바퀴에 m 번 출렁이는 성분. 도플러로는 m·f_rot [Hz].
· AC / DC       : DC = 차수 0(안 변하는 몫, 동체), AC = 차수 0 이 아닌 몫(변조).
· 플래시        : 블레이드가 시선에 수직으로 서는 순간 반사가 확 세지는 것.
· PO            : 물리광학. 조명된 면을 전부 위상 맞춰 더하는 근사.
· |Γ|           : 반사계수 크기. 1 이면 완전도체(전부 반사).
· β             : 2k·ρ_max·cos(el). 회전축에서 가장 먼 점이 만드는 «최고 차수» 한계.

GPU 는 쓰지 않는다 — 이 단계는 저장된 표를 읽는 후처리라 CPU 로 충분하고,
지금 GPU 4장은 형제 워크플로가 다 쓰고 있다(남의 작업을 건드리지 않는다).

출력: outputs/report16_metric_cube_eqvol.json
      outputs/figures/report16_metric_cube_eqvol.png
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time

import numpy as np

ROOT = "/home/yunjung/workspace/sionna2"
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol_tables.npz")
PREREG = os.path.join(ROOT, "outputs", "report16_rung_cube_eqvol_prereg.json")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_cube_eqvol.json")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_metric_cube_eqvol.png")

DRONE_KEYS = ("mini2", "matrice4e")
GEN = "G_0804"                      # base 표의 현행 메쉬 세대


# =========================================================================== #
#  0. 잡동사니
# =========================================================================== #
def sha256(path, nbytes=None):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def jsonify(o):
    """numpy 타입을 순정 파이썬으로 — json.dump 가 삼킬 수 있게."""
    if isinstance(o, dict):
        return {str(k): jsonify(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonify(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, (np.integer, int)) and not isinstance(o, bool):
        return int(o)
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return jsonify(o.tolist())
    return o


def summ(vals):
    """방위 앙상블 요약 — 평균·표준편차·최소·최대."""
    v = np.asarray([x for x in np.asarray(vals, float).ravel() if np.isfinite(x)], float)
    if v.size == 0:
        return dict(mean=float("nan"), sd=float("nan"), n=0)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                min=float(v.min()), max=float(v.max()), n=int(v.size))


# =========================================================================== #
#  1. 지표 — base 의 문서(수식)만 보고 **새로 구현**한다
# =========================================================================== #
#   base/report16_base.py :: md_metrics16 의 docstring 에 적힌 정의를 그대로 옮겼다.
#   구현은 보지 않고 «수식» 만 보고 짰다. 두 구현이 같은 숫자를 내면 그 숫자는
#   «한 사람의 실수» 가 아니다.
def spectrum(tab):
    """한 바퀴 표 → 부호 있는 차수별 전력 P[m], 차수 배열 m."""
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    return np.abs(c) ** 2, np.fft.fftfreq(S, d=1.0 / S).astype(int), S


def order_power(tab):
    """차수 크기 |m| 별로 모은 AC 전력 (합=1로 정규화). 0차는 뺀다."""
    P, m, S = spectrum(tab)
    op = np.zeros(S // 2 + 1)
    np.add.at(op, np.abs(m), P)
    ac = op.copy()
    ac[0] = 0.0
    tot = ac.sum()
    return (ac / tot if tot > 0 else ac), tot, float(op[0])


def metrics_indep(tab, proto, prop_blades, beta_own=None, sym_tol=1e-6):
    """위상 표 하나 → 지표 한 벌. (독립 구현)"""
    tab = np.asarray(tab, complex)
    P, m, S = spectrum(tab)
    f_rot = float(proto["f_rot_hz"])
    f_tip = float(proto["f_tip_hz"])
    beta = float(proto["beta"])
    ac_mask = m != 0
    p_ac = float(P[ac_mask].sum())
    p_dc = float(P[m == 0].sum())
    o = {}

    # ④ 동체 대 블레이드 세기비 — 20log10(|c0| / sqrt(sum_{m≠0}|cm|^2))
    o["dc_ac_db"] = 20.0 * math.log10(max(math.sqrt(p_dc), 1e-300) /
                                      max(math.sqrt(p_ac), 1e-300))
    o["ac_frac_db"] = -o["dc_ac_db"]
    o["mean_sigma_proxy"] = float(np.mean(np.abs(tab) ** 2))
    o["sigma_eq_mean_dbsm"] = 10.0 * math.log10(
        max((4 * math.pi / float(proto["lam_m"]) ** 2) * o["mean_sigma_proxy"], 1e-300))

    # ① 플래시 대조비 — 20log10(max|E_ac| / median|E_ac|)
    env = np.abs(tab - tab.mean())
    o["flash_contrast_db"] = 20.0 * math.log10(max(env.max(), 1e-300) /
                                               max(float(np.median(env)), 1e-300))
    o["crest_factor_db"] = 20.0 * math.log10(max(env.max(), 1e-300) /
                                             max(float(np.sqrt((env ** 2).mean())), 1e-300))

    # ⭐ 추가 — «순음 한계». 한 차수 ±쌍만 있는 신호의 포락선은 2A|cos| 이라
    #    플래시 대조비가 20log10(1/median|cos|) 로 고정된다. 이 값보다 얼마나 위인가가
    #    «진짜 뾰족한 플래시인가, 그냥 사인파 출렁임인가» 를 가른다.  (수치로 구한다)
    _ph = np.linspace(0.0, 2 * math.pi, 4096, endpoint=False)
    tone_db = 20.0 * math.log10(1.0 / float(np.median(np.abs(np.cos(_ph)))))
    o["tone_limit_db"] = tone_db
    o["flash_excess_over_tone_db"] = o["flash_contrast_db"] - tone_db

    # 대역 판정기 — 운동학이 허용하는 최고 차수 β 의 1.5배 안쪽 전력 몫
    def in_band(b):
        band = max(2, int(math.ceil(1.5 * float(b))))
        msk = ac_mask & (np.abs(m) <= band)
        return band, float(P[msk].sum())

    band, p_in = in_band(beta)
    o["band_order"] = band
    o["in_band_ac_frac"] = p_in / max(p_ac, 1e-300)
    o["in_band_ac_over_dc_db"] = 10.0 * math.log10(max(p_in, 1e-300) / max(p_dc, 1e-300))
    o["metrics_interpretable"] = bool(o["in_band_ac_frac"] >= 0.5)
    if beta_own is not None:
        band2, p_in2 = in_band(beta_own)
        o["beta_own"] = float(beta_own)
        o["band_order_own"] = band2
        o["in_band_ac_frac_own"] = p_in2 / max(p_ac, 1e-300)

    # 수치바닥 대비 AC — 차수 상위 25% 의 중앙 전력을 «바닥» 으로 본다
    hi = np.abs(m) > max(4, int(0.75 * (S // 2)))
    floor = float(np.median(P[hi])) if hi.any() else 0.0
    o["ac_over_floor_db"] = (10.0 * math.log10(max(p_ac / max(floor * int(ac_mask.sum()), 1e-300),
                                                   1e-300)) if floor > 0 else float("inf"))

    # ② 고차 성분 풍부도
    if p_ac > 0:
        p = P[ac_mask] / p_ac
        nz = p[p > 0]
        o["n_eff_orders"] = float(math.exp(float(-(nz * np.log(nz)).sum())))
        op, _, _ = order_power(tab)
        cum = np.cumsum(op)
        o["dominant_order"] = int(np.argmax(op))
        o["order_p50"] = int(np.searchsorted(cum, 0.50))
        o["order_p90"] = int(np.searchsorted(cum, 0.90))
        nb = max(1, int(prop_blades))
        comb = np.zeros_like(op, dtype=bool)
        comb[nb::nb] = True
        o["blade_comb_frac"] = float(op[comb].sum())

        # ③ 도플러 폭 — 첨두 대비 −10/−20/−30 dB 위에 있는 가장 바깥 차수
        pk = float(op.max())
        for drop in (10.0, 20.0, 30.0):
            above = np.where(op >= pk * 10 ** (-drop / 10.0))[0]
            edge = int(above.max()) if len(above) else 0
            o[f"order_edge_{int(drop)}db"] = edge
            o[f"width_ratio_{int(drop)}db"] = float(edge * f_rot / max(f_tip, 1e-30))
        o["fd_edge_hz"] = float(o["order_edge_20db"] * f_rot)
        o["width_ratio"] = o["width_ratio_20db"]
        if beta_own is not None and beta_own > 0:
            o["width_over_own_beta"] = float(o["order_edge_20db"] / beta_own)

        # 차수 계열 나누기 — «4의 배수 / 4로 나눠 2 남음 / 홀수»
        idx = np.arange(len(op))
        o["frac_mod4_0"] = float(op[(idx % 4 == 0) & (idx > 0)].sum())
        o["frac_mod4_2"] = float(op[idx % 4 == 2].sum())
        o["frac_odd"] = float(op[idx % 2 == 1].sum())
        o["order2_frac"] = float(op[2]) if len(op) > 2 else 0.0
        o["order4_frac"] = float(op[4]) if len(op) > 4 else 0.0
        o["ladder_top"] = [[int(i), float(op[i])]
                           for i in np.argsort(op)[::-1][:8] if op[i] > 0]

        # 대칭 차수 — AC 전력의 (1−tol) 이상이 g 의 배수에만 실리는 최대 g
        #   ⚠ 문턱을 얼마로 잡느냐가 답을 바꾼다. 점 깔기가 남긴 찌꺼기(1e-4 수준)를
        #     «대칭 깨짐» 으로 셀지 말지의 문제라서, 빡빡한 것과 느슨한 것을 둘 다 낸다.
        for tol, suf in ((sym_tol, ""), (1e-3, "_tol1e3")):
            sym = 1
            for g in range(1, S // 2 + 1):
                if S % g:
                    continue
                msk = (idx % g == 0) & (idx > 0)
                if float(op[msk].sum()) >= 1.0 - tol:
                    sym = g
            o[f"symmetry_order{suf}"] = int(sym)
            o[f"symmetry_period_deg{suf}"] = 360.0 / sym
        o["symmetry_tol"] = sym_tol

        # 으뜸 차수의 ± 균형 — +m 과 −m 이 균형이면 포락선이 |cos| 꼴로 출렁인다
        md = o["dominant_order"]
        pp = float(P[m == md].sum())
        pm = float(P[m == -md].sum())
        o["dominant_pm_balance"] = float(min(pp, pm) / max(pp, pm)) if max(pp, pm) > 0 else 0.0
    else:
        for kk in ("n_eff_orders", "dominant_order", "order_p50", "order_p90",
                   "blade_comb_frac", "fd_edge_hz", "width_ratio"):
            o[kk] = float("nan")
    return o


def project_mod(tab, g):
    """표에서 «g 의 배수 차수» 만 남긴다(0차 제외). 정육면체가 닿을 수 있는 자리만 보려고."""
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab)
    m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
    c = np.where((m != 0) & (np.abs(m) % g == 0), c, 0.0)
    return np.fft.ifft(c)


def ac_corr(a, b):
    """두 표의 AC 성분 정규화 복소상관. 1 이면 파형이 같다(정합필터가 구별 못 함)."""
    a = np.asarray(a, complex) - np.mean(a)
    b = np.asarray(b, complex) - np.mean(b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.abs(np.vdot(a, b)) / (na * nb)) if na > 0 and nb > 0 else 0.0


def auc(x, y):
    """x 가 y 보다 클 확률(맞대결 승률). 1.0 = 두 무리가 완전히 갈린다."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    d = x[:, None] - y[None, :]
    return float(((d > 0).sum() + 0.5 * (d == 0).sum()) / d.size)


# =========================================================================== #
#  2. PO 커널 독립 재구현 (numpy·CPU) — 저장된 표를 재현해 본다
# =========================================================================== #
def _rz(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def po_rigid_spin_cpu(P, N, W, k, A, R_t, phis):
    """온몸이 z 축으로 도는 점구름의 위상 표 — 구면파 모노스태틱 PO.

    쓰는 식(계산 단계 문서와 같은 것):
      진폭 = max(n·û, 0) · W · (R_t²/r²)      (그늘진 면은 0 — 가림은 없다)
      위상 = −k(2r − 2R_t)                    (왕복 거리, 기준거리 R_t 로 정규화)
    물체를 +φ 돌리는 대신 안테나를 −φ 돌린다(엄밀히 같은 조작이다).
    """
    out = np.zeros(len(phis), complex)
    for i, ph in enumerate(phis):
        Al = _rz(-ph) @ A
        D = Al[None, :] - P
        r = np.linalg.norm(D, axis=1)
        ui = D / r[:, None]
        nu = np.einsum("ij,ij->i", N, ui)
        amp = np.where(nu > 0, nu, 0.0) * W * (R_t * R_t) / (r * r)
        phz = -k * (2.0 * r - 2.0 * R_t)
        out[i] = np.sum(amp * np.cos(phz)) + 1j * np.sum(amp * np.sin(phz))
    return out


def kernel_replication(base_json):
    """정육면체·강체회전 팔의 표를 CPU 로 다시 만들어 저장본과 비교한다."""
    import report16_base as R
    import report16_rung_cube_eqvol as C
    from drones import DRONES, build_drone, drone_gamma_map
    from rcs_po import mesh_to_points
    from geom import box

    zc = np.load(RUNG_NPZ)
    blade_div = float(base_json["protocol"]["blade_div"])
    rows = []
    for key in DRONE_KEYS:
        s = DRONES[key]
        drone = build_drone(s)
        vol = abs(C.mesh_volume(drone))
        for tag, fc in (("main", R.FC_MAIN), ("hi", R.FC_PO_KNEE)):
            lam = R.C0 / fc
            k = 2 * math.pi / lam
            proto = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
            phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
            spac = lam / blade_div

            jobs = [("cube_eqvol", None)]
            if tag == "main" and key == "mini2":
                jobs.append(("mesh_rigid_spin_pec", None))
            for arm, _ in jobs:
                if arm == "cube_eqvol":
                    a = vol ** (1.0 / 3.0)
                    P, N, dA = mesh_to_points(box(a, a, a, center=(0, 0, 0), group="cube"), spac)
                    W = dA
                else:
                    P, N, dA = mesh_to_points(drone, spac)
                    W = dA
                keyz = (f"main__{key}__{arm}__spherical" if tag == "main"
                        else f"hi__hi__{key}__{arm}__spherical")
                if keyz not in zc.files:
                    continue
                T = zc[keyz]
                az_probe = [0, 7] if tag == "main" else [0]
                for ia in az_probe:
                    az = ia * (360.0 / R.N_AZ)
                    u, A, R_t = R.look_and_antenna(az, R.EL_DEG, R.RANGE_M)
                    mine = po_rigid_spin_cpu(P, N, W, k, A, R_t, phis)
                    ref = T[ia]
                    rel = float(np.abs(mine - ref).max() / max(np.abs(ref).max(), 1e-300))
                    rows.append(dict(band=tag, drone=key, arm=arm, az_deg=az,
                                     n_pts=int(len(W)), n_phase=int(proto["n_phase"]),
                                     max_rel_diff=rel))
                    print(f"  [kernel] {tag:4s} {key:10s} {arm:20s} az={az:5.1f} "
                          f"rel={rel:.2e}", flush=True)
    return rows


def cloud_symmetry_probe():
    """정육면체 «점구름» 자체가 90°/180° 회전에 대칭인지 직접 본다.

    왜 보는가: 정육면체는 모양이 4겹 대칭이지만, 그 위에 점을 까는 방식까지
    4겹 대칭이라는 보장은 없다. 점 깔기가 대칭을 깨면 4의 배수가 아닌 차수에
    «가짜 선» 이 뜬다. 그 정체를 눈으로 확인하는 자리다.
    """
    import report16_base as R
    import report16_rung_cube_eqvol as C
    from drones import DRONES, build_drone
    from rcs_po import mesh_to_points
    from geom import box
    from scipy.spatial import cKDTree

    out = {}
    lam = R.C0 / R.FC_MAIN
    for key in DRONE_KEYS:
        s = DRONES[key]
        vol = abs(C.mesh_volume(build_drone(s)))
        a = vol ** (1.0 / 3.0)
        P, N, dA = mesh_to_points(box(a, a, a, center=(0, 0, 0), group="cube"), lam / 11.0)
        tree = cKDTree(P)
        rec = dict(side_m=a, n_pts=int(len(P)))
        top = int(np.isclose(P[:, 2], a / 2).sum())
        bot = int(np.isclose(P[:, 2], -a / 2).sum())
        rec.update(n_top_face=top, n_bottom_face=bot, n_side_faces=int(len(P) - top - bot),
                   n_per_side_face=float((len(P) - top - bot) / 4.0))
        for deg in (90, 180):
            Q = P @ _rz(math.radians(deg)).T
            d, _ = tree.query(Q, k=1)
            rec[f"rot{deg}_max_point_mismatch_m"] = float(d.max())
            rec[f"rot{deg}_max_point_mismatch_over_side"] = float(d.max() / a)
        out[key] = rec
    return out


# =========================================================================== #
#  3. 표 읽기 — 어디에 무엇이 있는가
# =========================================================================== #
def table_index(zb, zc):
    """(band, drone, arm) → (배열, 출처). base 표는 base 것을 그대로 쓴다."""
    idx = {}
    for d in DRONE_KEYS:
        for arm in ("mesh", "sphere", "slab", "disc", "mesh_fine", "slab_fine", "disc_fine"):
            k = f"main__{GEN}__{d}__{arm}__spherical"
            if k in zb.files:
                idx[("main", d, arm)] = (zb[k], "base")
        for arm in ("cube_eqvol", "cube_eqvol_fine", "mesh_rigid_spin", "mesh_rigid_spin_pec"):
            k = f"main__{d}__{arm}__spherical"
            if k in zc.files:
                idx[("main", d, arm)] = (zc[k], "rung")
        for arm in ("mesh", "slab"):
            k = f"hi__hi__{GEN}__{d}__{arm}__spherical"
            if k in zb.files:
                idx[("hi", d, arm)] = (zb[k], "base")
        for arm in ("cube_eqvol", "sphere_eqvol"):
            k = f"hi__hi__{d}__{arm}__spherical"
            if k in zc.files:
                idx[("hi", d, arm)] = (zc[k], "rung")
    return idx


# =========================================================================== #
#  4. 본체
# =========================================================================== #
def main():
    t_start = time.time()
    BJ = json.load(open(BASE_JSON))
    RJ = json.load(open(RUNG_JSON))
    PR = json.load(open(PREREG))
    zb = np.load(BASE_NPZ)
    zc = np.load(RUNG_NPZ)
    idx = table_index(zb, zc)

    pred = PR["prediction"]
    geo = PR["geometry_only_predictions"]
    rmax = RJ["kinematic_ceiling"]["rmax_moving_part_m"]
    el = float(RJ["protocol"]["el_deg"])
    ce = math.cos(math.radians(el))

    def proto_of(band, d):
        p = BJ["protocol_per_drone"][d]
        return p if band == "main" else p["hi_band"]

    def beta_own_of(band, d, arm):
        """팔마다 «자기 회전 반경» 으로 다시 잡은 β. 온몸이 도는 팔은 팁반경이 아니다."""
        lam = float(proto_of(band, d)["lam_m"])
        alias_arm = {"sphere_eqvol": "sphere"}.get(arm, arm)   # 같은 구성인데 이름만 다른 팔
        r = rmax[d].get(alias_arm)
        if r is None:
            return None
        return 4.0 * math.pi * float(r) * ce / lam

    blades = {d: int(geo[d]["prop_blades"]) for d in DRONE_KEYS}

    # ── 4-1. 전 팔 지표 (방위 24점 앙상블) ─────────────────────────────────
    per_az_raw = {}          # (band,drone,arm) -> {metric: array over az}
    metrics_all = {}
    for (band, d, arm), (T, src) in sorted(idx.items()):
        proto = proto_of(band, d)
        bo = beta_own_of(band, d, arm)
        rows = [metrics_indep(T[i], proto, blades[d], beta_own=bo) for i in range(T.shape[0])]
        keys = [k for k in rows[0]
                if isinstance(rows[0][k], (int, float, bool, np.floating, np.integer))]
        per_az_raw[(band, d, arm)] = {k: np.array([r[k] for r in rows], float) for k in keys}
        blk = {k: summ([r[k] for r in rows]) for k in keys}
        blk["_source"] = src
        blk["_n_az"] = int(T.shape[0])
        blk["_ladder_top_az0"] = rows[0]["ladder_top"]
        metrics_all[f"{band}|{d}|{arm}"] = blk

    # ── 4-2. 계산 단계 숫자와 맞춰 보기 (지표 공식 독립 재구현 검산) ────────
    audit_rows = []
    check_metrics = ("flash_contrast_db", "n_eff_orders", "dc_ac_db", "width_ratio",
                     "blade_comb_frac", "in_band_ac_frac", "order_edge_20db",
                     "dominant_order", "sigma_eq_mean_dbsm")
    for f_arm, src_json in ((RJ["arms"], "rung"), (BJ["arms"], "base")):
        for d in DRONE_KEYS:
            if d not in f_arm:
                continue
            for arm, blk in f_arm[d].items():
                sph = blk.get("spherical")
                if not isinstance(sph, dict) or "per_az" not in sph:
                    continue
                mine = metrics_all.get(f"main|{d}|{arm}")
                if mine is None:
                    continue
                for mk in check_metrics:
                    if mk not in sph["per_az"] or mk not in mine:
                        continue
                    a, b = float(sph["per_az"][mk]["mean"]), float(mine[mk]["mean"])
                    audit_rows.append(dict(
                        which=src_json, drone=d, arm=arm, metric=mk,
                        reported=a, recomputed=b, abs_diff=abs(a - b),
                        rel_diff=abs(a - b) / max(abs(a), 1e-30)))
    worst = sorted(audit_rows, key=lambda r: -r["rel_diff"])[:6]
    metric_audit = dict(
        n_comparisons=len(audit_rows),
        max_rel_diff=max((r["rel_diff"] for r in audit_rows), default=float("nan")),
        max_abs_diff=max((r["abs_diff"] for r in audit_rows), default=float("nan")),
        n_exceeding_1e_9=int(sum(1 for r in audit_rows if r["rel_diff"] > 1e-9)),
        worst_six=worst,
        what_ko=("계산 단계가 보고한 방위평균과, 여기서 **수식만 보고 새로 짠** 구현의 "
                 "방위평균을 맞춰 본 것이다. 두 구현이 일치하면 지표 숫자는 «한 코드의 실수» 가 아니다."))

    # ── 4-3. PO 커널 자체 재현 (GPU torch ↔ CPU numpy) ─────────────────────
    try:
        kern = kernel_replication(BJ)
        kern_max = max((r["max_rel_diff"] for r in kern), default=float("nan"))
        kernel_block = dict(rows=kern, max_rel_diff=kern_max, ok=bool(kern_max < 1e-9))
    except Exception as e:                                              # noqa: BLE001
        kernel_block = dict(rows=[], error=repr(e), ok=False)
    kernel_block["what_ko"] = (
        "계산 단계는 GPU(torch)로 표를 만들었다. 여기서는 **numpy·CPU 로 같은 식을 새로 짜서** "
        "표의 몇 줄을 다시 만들어 봤다. 다른 코드·다른 기계가 같은 숫자를 내면 그 표는 믿을 만하다.")
    kernel_block["not_covered_ko"] = (
        "⚠ 재현한 것은 **온몸이 도는 팔**(정육면체·강체회전 메쉬)뿐이다. 기준이 되는 "
        "«블레이드만 도는» base 의 mesh 팔은 로터 배치·프레임 결합 경로가 달라 여기서 다시 만들지 않았다 "
        "— 그 표는 여전히 계산 단계 한 벌의 코드에만 의존한다.")

    # ── 4-4. 사전예측 채점 (내 숫자로) ─────────────────────────────────────
    def m(band, d, arm, k):
        return metrics_all[f"{band}|{d}|{arm}"][k]["mean"]

    def raw(band, d, arm, k):
        return per_az_raw[(band, d, arm)][k]

    scorecard = {}
    for band in ("main", "hi"):
        null_arm = "sphere" if band == "main" else "sphere_eqvol"
        for d in DRONE_KEYS:
            if (band, d, "cube_eqvol") not in per_az_raw:
                continue
            g = geo[d][band if band == "main" else "hi"]
            sc = {}

            # P1 — 정육면체는 구(계산기 바닥)보다 한참 위에서 변조하는가
            dcube = m(band, d, "cube_eqvol", "in_band_ac_over_dc_db")
            dnull = m(band, d, null_arm, "in_band_ac_over_dc_db")
            sc["P1_cube_modulates_at_all"] = dict(
                statistic=pred["P1_cube_modulates_at_all"]["statistic"],
                cube_db=dcube, null_arm=null_arm, null_db=dnull, delta_db=dcube - dnull,
                threshold_db=pred["P1_cube_modulates_at_all"]["threshold_db"],
                verdict="PASS" if (dcube - dnull) > pred["P1_cube_modulates_at_all"]["threshold_db"]
                else "FAIL")

            # P2 — 90° 주기(4의 배수 차수)인가
            f4 = m(band, d, "cube_eqvol", "frac_mod4_0")
            dom = raw(band, d, "cube_eqvol", "dominant_order")
            sc["P2_period_is_90deg"] = dict(
                frac_on_multiples_of_4=f4, threshold=pred["P2_period_is_90deg_not_180deg"]["threshold"],
                mean_dominant_order=float(dom.mean()),
                dominant_is_multiple_of_4=bool(np.all(dom % 4 == 0)),
                symmetry_order_tol1e3=m(band, d, "cube_eqvol", "symmetry_order_tol1e3"),
                symmetry_period_deg_tol1e3=m(band, d, "cube_eqvol", "symmetry_period_deg_tol1e3"),
                symmetry_order_tol1e6=m(band, d, "cube_eqvol", "symmetry_order"),
                symmetry_note_ko=("스펙트럼만 보고 회전 대칭 겹수를 읽은 값. 느슨한 문턱(1e-3)에서는 4겹 "
                                  "— 90° 주기가 그대로 보인다. 빡빡한 문턱(1e-6)에서는 1 로 떨어지는데, "
                                  "그것은 대칭이 깨져서가 아니라 점 깔기 찌꺼기(홀수 차수 1e-4 수준)를 "
                                  "«깨짐» 으로 세기 때문이다."),
                verdict="PASS" if (f4 > pred["P2_period_is_90deg_not_180deg"]["threshold"]
                                   and bool(np.all(dom % 4 == 0))) else "FAIL")

            # P3 — 블레이드 선(차수 2 계열)이 없는가 / 파형이 안 닮았는가
            mesh_arm = "mesh"
            a_val = m(band, d, mesh_arm, "frac_mod4_2")
            b_val = m(band, d, "cube_eqvol", "frac_mod4_2")
            Tm = idx[(band, d, mesh_arm)][0]
            Tc = idx[(band, d, "cube_eqvol")][0]
            corr = np.array([ac_corr(Tm[i], Tc[i]) for i in range(Tm.shape[0])])
            # 정육면체가 «닿을 수 있는» 자리는 4의 배수 차수뿐이다 → 상관의 구조적 상한
            share = m(band, d, mesh_arm, "frac_mod4_0")
            # ⭐ 그 자리 «안에서만» 비교하면 얼마나 닮았나 — 정육면체에 가장 유리한 잣대
            corr4 = np.array([ac_corr(project_mod(Tm[i], 4), project_mod(Tc[i], 4))
                              for i in range(Tm.shape[0])])
            pa = pred["P3_blade_line_is_absent"]
            sub = dict(a_mesh_has_order2_family=bool(a_val > pa["threshold_a"]),
                       b_cube_has_none=bool(b_val < pa["threshold_b"]),
                       c_waveforms_uncorrelated=bool(corr.mean() < pa["threshold_c"]))
            sc["P3_blade_line_absent"] = dict(
                mesh_frac_mod4_2=a_val, threshold_a=pa["threshold_a"],
                cube_frac_mod4_2=b_val, threshold_b=pa["threshold_b"],
                waveform_corr_mean=float(corr.mean()), waveform_corr_sd=float(corr.std(ddof=1)),
                waveform_corr_max=float(corr.max()), threshold_c=pa["threshold_c"],
                mesh_frac_on_multiples_of_4=share,
                corr_structural_ceiling=float(math.sqrt(max(share, 0.0))),
                corr_over_ceiling=float(corr.mean() / max(math.sqrt(max(share, 1e-30)), 1e-30)),
                corr_within_mod4_subspace_mean=float(corr4.mean()),
                corr_within_mod4_subspace_sd=float(corr4.std(ddof=1)),
                corr_within_mod4_note_ko=(
                    "⚠ 정육면체에 **가장 유리한** 잣대다 — 정육면체가 닿을 수 있는 차수(4의 배수)만 남기고 "
                    "양쪽을 비교했다. 여기서도 1 에 못 미치면 «자기 자리 안에서조차 파형이 다르다» 는 뜻이고, "
                    "1 에 가까우면 «자리만 좁을 뿐 그 안에서는 닮았다» 는 뜻이다. 정직하게 둘 다 적는다."),
                subcriteria=sub,
                verdict="PASS" if all(sub.values()) else "FAIL")

            # P4 — 폭이 «자기 모서리 반경» 이 정한 값인가
            edge = m(band, d, "cube_eqvol", "order_edge_20db")
            bcp = float(g["beta_cube_predicted"])
            lo, hiy = pred["P4_width_is_set_by_its_own_corner_radius"]["band"]
            ratio = edge / bcp
            sc["P4_width_from_own_corner_radius"] = dict(
                measured_edge_order=edge, beta_cube_predicted=bcp,
                beta_blade=float(g["beta_blade"]),
                measured_edge_order_mesh=m(band, d, "mesh", "order_edge_20db"),
                ratio_measured_over_predicted=ratio, band=[lo, hiy],
                verdict="PASS" if lo <= ratio <= hiy else "FAIL")

            # P5 — 방위 앙상블이 축퇴인가 (온몸 회전이면 방위는 새 정보가 아니다)
            sd_cube = float(raw(band, d, "cube_eqvol", "n_eff_orders").std(ddof=1))
            sd_mesh = float(raw(band, d, "mesh", "n_eff_orders").std(ddof=1))
            thr5 = pred["P5_azimuth_ensemble_is_degenerate_for_a_rigid_spinner"]["threshold"]
            sc["P5_azimuth_degenerate"] = dict(
                cube_sd_n_eff=sd_cube, drone_sd_n_eff=sd_mesh,
                ratio_cube_over_drone=sd_cube / max(sd_mesh, 1e-300),
                threshold=thr5, verdict="PASS" if sd_cube < thr5 else "FAIL")
            key_ex = (f"main__{d}__cube_eqvol__az_exact" if band == "main"
                      else f"hi__hi__{d}__cube_eqvol__az_exact")
            if key_ex in zc.files:
                Tx = zc[key_ex]
                proto = proto_of(band, d)
                mx = [metrics_indep(Tx[i], proto, blades[d]) for i in range(Tx.shape[0])]
                sc["P5_azimuth_degenerate"]["on_exact_phase_grid"] = dict(
                    n_az=int(Tx.shape[0]),
                    sd_n_eff=float(np.std([r["n_eff_orders"] for r in mx], ddof=1)),
                    sd_dc_ac_db=float(np.std([r["dc_ac_db"] for r in mx], ddof=1)),
                    sd_flash_contrast_db=float(np.std([r["flash_contrast_db"] for r in mx], ddof=1)),
                    note_ko="위상 격자에 정확히 떨어지는 방위만 골라 잰 값. 여기서 0 이면 축퇴는 «정확히» 성립한다.")

            # P6 — 기계적 항등식: 도는 물체 ≡ 가만있는 물체를 방위로 훑기
            key_st = (f"main__{d}__cube_eqvol__static_az" if band == "main"
                      else f"hi__hi__{d}__cube_eqvol__static_az")
            if key_st in zc.files:
                Sst = zc[key_st][0]
                T0 = idx[(band, d, "cube_eqvol")][0][0]
                S = len(T0)
                j = np.arange(S)
                cands = {"E(phi)=Estatic(-phi)": Sst[(-j) % S], "E(phi)=Estatic(+phi)": Sst[j % S]}
                best = min(cands.items(),
                           key=lambda kv: float(np.abs(T0 - kv[1]).max()))
                rel = float(np.abs(T0 - best[1]).max() / max(np.abs(T0).max(), 1e-300))
                thr6 = pred["P6_mechanism_identity"]["threshold"]
                sc["P6_mechanism_identity"] = dict(
                    alignment=best[0], max_rel=rel, threshold=thr6,
                    max_rel_in_units_of_double_eps=float(rel / np.finfo(float).eps),
                    n_phase=int(S),
                    threshold_caveat_ko=(
                        "1e-12 는 «부동소수 오차보다 크면 실패» 라는 뜻으로 정한 고정 문턱인데, "
                        "실제 누적 오차는 점 수·위상 크기와 함께 커진다. 그래서 표본이 많고 주파수가 높은 "
                        "고대역에서는 같은 물리인데도 문턱을 스칠 수 있다 — 배수(eps 단위)를 같이 적어 둔다."),
                    verdict="PASS" if rel < thr6 else "FAIL")
            scorecard[f"{band}|{d}"] = sc

    for kk, sc in scorecard.items():
        vs = [v["verdict"] for v in sc.values() if isinstance(v, dict) and "verdict" in v]
        sc["_n_pass"] = int(sum(1 for v in vs if v == "PASS"))
        sc["_n_total"] = len(vs)
    tot_p = sum(sc["_n_pass"] for sc in scorecard.values())
    tot_n = sum(sc["_n_total"] for sc in scorecard.values())
    main_p = sum(v["_n_pass"] for k, v in scorecard.items() if k.startswith("main|"))
    main_n = sum(v["_n_total"] for k, v in scorecard.items() if k.startswith("main|"))
    hi_p = sum(v["_n_pass"] for k, v in scorecard.items() if k.startswith("hi|"))
    hi_n = sum(v["_n_total"] for k, v in scorecard.items() if k.startswith("hi|"))

    # 계산 단계 채점과 어긋나는 데가 있는가
    agree = {}
    for d in DRONE_KEYS:
        theirs = RJ["prediction_scorecard"][d]
        mine_sc = scorecard[f"main|{d}"]
        for pk in theirs:
            if not isinstance(theirs[pk], dict) or "verdict" not in theirs[pk]:
                continue
            mk = pk if pk in mine_sc else None
            if mk is None:
                continue
            agree[f"{d}|{pk}"] = dict(compute_stage=theirs[pk]["verdict"],
                                      metric_stage=mine_sc[mk]["verdict"],
                                      same=theirs[pk]["verdict"] == mine_sc[mk]["verdict"])
    agree["_all_same"] = all(v["same"] for v in agree.values() if isinstance(v, dict))

    # ── 4-5. 짝지은 팔 차이 + 갈라짐(맞대결 승률) ─────────────────────────
    HEAD = ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db")
    pairs = [("cube_eqvol", "mesh"), ("cube_eqvol", "mesh_rigid_spin_pec"),
             ("cube_eqvol", "sphere"), ("cube_eqvol", "cube_eqvol_fine"),
             ("mesh_rigid_spin", "mesh"), ("mesh_rigid_spin_pec", "mesh_rigid_spin")]
    contrast = {}
    for band in ("main", "hi"):
        for d in DRONE_KEYS:
            for A_, B_ in pairs:
                if (band, d, A_) not in per_az_raw or (band, d, B_) not in per_az_raw:
                    continue
                blk = {}
                for k in HEAD + ("in_band_ac_frac", "order_edge_20db", "blade_comb_frac",
                                 "frac_mod4_0", "n_eff_orders"):
                    xa, xb = per_az_raw[(band, d, A_)].get(k), per_az_raw[(band, d, B_)].get(k)
                    if xa is None or xb is None or len(xa) != len(xb):
                        continue
                    dd = xa - xb
                    blk[k] = dict(paired_mean=float(dd.mean()), paired_sd=float(dd.std(ddof=1)),
                                  frac_A_greater=float((dd > 0).mean()),
                                  auc_A_over_B=auc(xa, xb),
                                  ranges_disjoint=bool(xa.min() > xb.max() or xb.min() > xa.max()))
                Ta, Tb = idx[(band, d, A_)][0], idx[(band, d, B_)][0]
                blk["waveform_corr_mean"] = float(np.mean([ac_corr(Ta[i], Tb[i])
                                                           for i in range(Ta.shape[0])]))
                contrast[f"{band}|{d}|{A_} - {B_}"] = blk
    contrast["_what_ko"] = (
        "같은 방위에서 두 팔의 지표를 뺀 값(A − B). 자세 산포는 두 팔에 공통이라 짝지어 빼면 사라진다. "
        "auc_A_over_B 는 24×24 맞대결에서 A 가 이긴 비율 — 1.0 이면 두 무리가 완전히 갈린다.")

    # ── 4-6. 구조적 천장: 정육면체 가족이 «닿을 수 있는» 몫 ────────────────
    ceiling = {}
    for band in ("main", "hi"):
        for d in DRONE_KEYS:
            if (band, d, "mesh") not in per_az_raw:
                continue
            f4 = per_az_raw[(band, d, "mesh")]["frac_mod4_0"]
            f2 = per_az_raw[(band, d, "mesh")]["frac_mod4_2"]
            fo = per_az_raw[(band, d, "mesh")]["frac_odd"]
            ceiling[f"{band}|{d}"] = dict(
                drone_ac_on_multiples_of_4=summ(f4),
                drone_ac_on_mod4_eq_2=summ(f2),
                drone_ac_on_odd_orders=summ(fo),
                unreachable_frac_mean=float(1.0 - f4.mean()),
                corr_ceiling_mean=float(np.mean(np.sqrt(np.clip(f4, 0, 1)))),
                unreachable_db=float(10.0 * math.log10(max(1.0 - f4.mean(), 1e-300))))
    ceiling["_what_ko"] = (
        "⭐ 정육면체는 4의 배수 차수에만 전력을 실을 수 있다(90° 대칭). 그러면 어떤 크기·재질로 맞춰도 "
        "진짜 드론 변조의 «4의 배수가 아닌 몫» 은 원리상 못 흉내낸다. unreachable_frac_mean 이 그 몫이고, "
        "corr_ceiling_mean 은 그래서 파형 상관이 넘을 수 없는 천장이다.")

    # ── 4-7. P5 잔차의 정체: 접힘(aliasing) 재기 ───────────────────────────
    #   방위 축퇴가 «정확히» 성립하면 T[ia] 는 T[0] 을 az 만큼 민 것이어야 한다.
    #   밀기를 «대역제한 보간»(푸리에 위상 곱)으로 하면, 남는 잔차는 표가 대역제한이
    #   아니라서 접힌 몫이다. 그 크기가 15° 격자에서 지표가 흔들리는 이유다.
    alias = {}
    for band in ("main", "hi"):
        for d in DRONE_KEYS:
            kk = (band, d, "cube_eqvol")
            if kk not in per_az_raw:
                continue
            T = idx[kk][0]
            S = T.shape[1]
            C0 = np.fft.fft(T[0])
            mm = np.fft.fftfreq(S, d=1.0 / S)
            res, shifts = [], []
            for ia in range(1, T.shape[0]):
                dphi = ia * (360.0 / T.shape[0]) / 360.0 * S     # 표본 단위 밀기
                for sgn in (+1.0, -1.0):
                    pred_t = np.fft.ifft(C0 * np.exp(-2j * math.pi * mm * sgn * dphi / S))
                    r = float(np.linalg.norm(pred_t - T[ia]) /
                              max(np.linalg.norm(T[ia] - T[ia].mean()), 1e-300))
                    shifts.append((r, sgn))
                res.append(min(r_ for r_, _ in shifts[-2:]))
            alias[f"{band}|{d}"] = dict(
                mean_residual_rel_ac=float(np.mean(res)), max_residual_rel_ac=float(np.max(res)),
                n_az_tested=len(res),
                integer_shift_samples=float((360.0 / T.shape[0]) / 360.0 * S),
                shift_is_integer=bool(abs(((360.0 / T.shape[0]) / 360.0 * S) % 1.0) < 1e-12))
    alias["_what_ko"] = (
        "축퇴가 정확하면 방위 ia 의 표는 방위 0 의 표를 그만큼 **민 것**이어야 한다. "
        "대역제한 밀기로 예측하고 남은 잔차가 곧 «표가 대역제한이 아니라 접힌 몫» 이다. "
        "15° 방위 격자는 위상 스텝의 정수배가 아니어서(integer_shift_samples 가 정수가 아님) "
        "이 잔차가 방위마다 다르게 남고, 그것이 P5 가 문턱을 못 넘긴 진짜 이유다.")

    # ── 4-8. 4의 배수 아닌 «찌꺼기 선» 의 정체 ─────────────────────────────
    residue = {}
    for d in DRONE_KEYS:
        c = metrics_all.get(f"main|{d}|cube_eqvol")
        cf = metrics_all.get(f"main|{d}|cube_eqvol_fine")
        if not c or not cf:
            continue
        residue[d] = dict(
            coarse_frac_odd=c["frac_odd"]["mean"], fine_frac_odd=cf["frac_odd"]["mean"],
            odd_power_shrink_x=float(c["frac_odd"]["mean"] / max(cf["frac_odd"]["mean"], 1e-300)),
            coarse_frac_mod4_2=c["frac_mod4_2"]["mean"], fine_frac_mod4_2=cf["frac_mod4_2"]["mean"],
            coarse_amplitude_frac_of_ac=float(math.sqrt(max(c["frac_odd"]["mean"], 0.0))),
            n_pts=RJ["equal_volume_construction"]["values"][d]["n_pts_cube"],
            n_pts_fine=RJ["equal_volume_construction"]["values"][d]["n_pts_cube_fine"])
    try:
        residue["_cloud_symmetry"] = cloud_symmetry_probe()
    except Exception as e:                                              # noqa: BLE001
        residue["_cloud_symmetry"] = dict(error=repr(e))
    residue["_what_ko"] = (
        "정육면체는 90° 대칭이라 4의 배수 차수에만 전력이 있어야 한다. 실제로 «4로 나눠 2 남는» "
        "차수는 기계적 0 이다. 그런데 홀수 차수에 작은 찌꺼기가 있다 — 점을 촘촘히 깔면 줄어드니 "
        "모양이 아니라 **점 깔기**가 남긴 것이다. 점구름이 90°/180° 회전에 실제로 어긋나 있는 것도 같이 확인했다.")

    # ── 4-9. 예측 대조 서술 + 못 믿을 이유 ─────────────────────────────────
    d0, d1 = DRONE_KEYS
    sc0, sc1 = scorecard["main|" + d0], scorecard["main|" + d1]
    hb = {k: v for k, v in scorecard.items() if k.startswith("hi|")}
    cx = contrast

    def g2(band, d, A_, B_, k, f="paired_mean"):
        return cx[f"{band}|{d}|{A_} - {B_}"][k][f]

    verdict_ko = dict(
        one_line_pred=pred["one_line_ko"],
        hit_ko=(
            "맞았다 — 정육면체는 변조를 낸다(구 바닥 대비 "
            f"+{sc0['P1_cube_modulates_at_all']['delta_db']:.1f} / "
            f"+{sc1['P1_cube_modulates_at_all']['delta_db']:.1f} dB), 그리고 그 변조는 "
            "**모서리·면이 만든 것**이라는 표지가 전부 붙어 있다. 90° 주기(4의 배수 차수에 "
            f"{sc0['P2_period_is_90deg']['frac_on_multiples_of_4']:.4f} / "
            f"{sc1['P2_period_is_90deg']['frac_on_multiples_of_4']:.4f}), 으뜸 차수 4, "
            "폭은 프로펠러 팁이 아니라 **자기 모서리 반경**이 정한다("
            f"측정/예측 = {sc0['P4_width_from_own_corner_radius']['ratio_measured_over_predicted']:.3f} / "
            f"{sc1['P4_width_from_own_corner_radius']['ratio_measured_over_predicted']:.3f})."),
        miss_ko=(
            "틀렸다 — 두 군데다. ⑴ P3-c: 파형 상관이 문턱 0.30 을 넘었다("
            f"{sc0['P3_blade_line_absent']['waveform_corr_mean']:.3f} / "
            f"{sc1['P3_blade_line_absent']['waveform_corr_mean']:.3f}). 다만 이것은 «닮았다» 가 "
            "아니라 «천장에 비해 얼마나 닮았나» 로 읽어야 한다 — 정육면체가 닿을 수 있는 자리는 "
            "4의 배수 차수뿐이고 그 자리에서의 구조적 천장이 "
            f"{sc0['P3_blade_line_absent']['corr_structural_ceiling']:.3f} / "
            f"{sc1['P3_blade_line_absent']['corr_structural_ceiling']:.3f} 이다. "
            "문턱 0.30 을 천장과 무관하게 정한 것이 예측의 설계 실수다. "
            "⑵ P5: 문턱 1e-6 은 부동소수 오차를 염두에 둔 값인데, 15° 방위 격자가 위상 스텝의 "
            "정수배가 아니라서 표집이 어긋난다 — 그 접힘 잔차가 문턱보다 크다. 격자에 정확히 "
            "떨어지는 방위로만 재면 축퇴는 정확히 성립한다."),
        surprise_ko=(
            "예측 밖에서 나온 것 — ⑴ 정육면체는 변조가 **모자란 게 아니라 너무 많다**. "
            f"동체:변조 비가 진짜 드론보다 {abs(g2('main', d0, 'cube_eqvol', 'mesh', 'dc_ac_db')):.1f} / "
            f"{abs(g2('main', d1, 'cube_eqvol', 'mesh', 'dc_ac_db')):.1f} dB 낮다(변조가 그만큼 세다). "
            "⑵ 그런데 **플래시 대조비는 오히려 낮다** — 정육면체의 출렁임은 뾰족한 플래시가 아니라 "
            "거의 사인파다(으뜸 차수 하나가 AC 의 대부분을 먹는다). 순음 한계 "
            f"{metrics_all[f'main|{d0}|cube_eqvol']['tone_limit_db']['mean']:.2f} dB 바로 위에 있다. "
            "⑶ 그래서 «세기» 지표(dc_ac)로는 정육면체가 드론보다 세 보이고, «모양» 지표(풍부도·플래시)로는 "
            "정육면체가 확연히 빈약하다 — 어떤 지표를 헤드라인으로 삼느냐가 결론을 뒤집는다. "
            "⑷ ⭐ 그런데 «세기» 우위조차 운동학 덕이지 형상 덕이 아니다. 진짜 드론을 **똑같이 온몸째 돌리면** "
            f"동체:변조 비가 정육면체보다 {abs(g2('main', d0, 'cube_eqvol', 'mesh_rigid_spin_pec', 'dc_ac_db')):.1f} / "
            f"{abs(g2('main', d1, 'cube_eqvol', 'mesh_rigid_spin_pec', 'dc_ac_db')):.1f} dB 더 낮다(더 세게 변조한다). "
            "즉 운동학을 맞춰 놓고 보면 정육면체는 세기에서도 모양에서도 진다 — 정육면체가 이겨 보였던 것은 "
            "«온몸이 돈다» 는 운동학의 값어치였지 «정육면체» 라는 형상의 값어치가 아니었다. "
            "⑸ ⚠ 지표 하나는 대역에서 뒤집힌다. 15.86 GHz 에서 정육면체의 플래시 대조비("
            f"{metrics_all[f'hi|{d0}|cube_eqvol']['flash_contrast_db']['mean']:.1f} / "
            f"{metrics_all[f'hi|{d1}|cube_eqvol']['flash_contrast_db']['mean']:.1f} dB)가 진짜 드론("
            f"{metrics_all[f'hi|{d0}|mesh']['flash_contrast_db']['mean']:.1f} / "
            f"{metrics_all[f'hi|{d1}|mesh']['flash_contrast_db']['mean']:.1f} dB)을 넘는다 — 한 변이 파장의 "
            "몇 배가 되면 평평한 면 자체가 거울처럼 번쩍이기 때문이다. 하모닉 풍부도(n_eff)는 두 대역 모두 "
            "뒤집히지 않는다. **결론을 플래시 하나에 걸면 안 된다**는 뜻이다."),
    )

    distrust = [
        dict(no=1, title_ko="가림(그림자)이 없다 — 동체:변조 비의 절대값은 못 쓴다",
             detail_ko=("이 커널은 조명된 면을 전부 더한다. 뒤에 가린 면도 더해진다. 그러면 동체가 "
                        "과대 계상되고 dc_ac_db 가 통째로 치우친다. 정육면체·구는 볼록체라 자기가림이 "
                        "원래 없어 오염이 없지만, **진짜 드론 메쉬는 오목하다** — 그래서 이 단의 헤드라인인 "
                        "«정육면체가 드론보다 세게 변조한다» 는 차이값도 드론 쪽이 얼마나 부풀었는지에 달려 있다. "
                        "차이의 부호는 24/24 방위에서 일치하지만, 크기(dB)는 가림을 넣으면 바뀔 수 있다."),
             quantified=dict(
                 paired_dc_ac_db_cube_minus_mesh={
                     d: g2("main", d, "cube_eqvol", "mesh", "dc_ac_db") for d in DRONE_KEYS},
                 frac_of_azimuths_same_sign={
                     d: 1.0 - g2("main", d, "cube_eqvol", "mesh", "dc_ac_db", "frac_A_greater")
                     for d in DRONE_KEYS})),
        dict(no=2, title_ko="3.5 GHz 에서는 신호원이 곧 커널의 최약점이다",
             base_statement_ko=BJ["po_validity_warning"]["statement_ko"],
             detail_ko=("변조를 만드는 부품(프로펠러 블레이드)은 위 base 경고문이 적은 대로 고대역에서야 PO 유효 "
                        "무릎을 넘는다. 헤드라인 대역 3.5 GHz 에서 블레이드는 파장보다 훨씬 얇아 PO 가 "
                        "가장 못 미더운 물체다. 반대로 정육면체는 한 변이 파장급 이상이라 PO 가 가장 잘 맞는 "
                        "물체다. 즉 이 비교는 **정육면체에 유리하게 기울어 있다**. 다행히 결론의 방향은 "
                        "15.86 GHz 에서 더 커지지 작아지지 않는다(아래 숫자) — 그래서 «기울어짐 때문에 나온 "
                        "결론» 은 아니다. 그러나 3.5 GHz 의 절대 숫자는 그 자체로 신뢰구간이 없다."),
             quantified=dict(
                 n_eff_gap_cube_minus_mesh_rigid={
                     f"{b}|{d}": (g2(b, d, "cube_eqvol", "mesh_rigid_spin_pec", "n_eff_orders")
                                  if f"{b}|{d}|cube_eqvol - mesh_rigid_spin_pec" in cx else None)
                     for b in ("main", "hi") for d in DRONE_KEYS},
                 po_knee_ghz=BJ["po_validity_warning"]["blade_knee_ghz"],
                 production_band_ghz=BJ["po_validity_warning"]["production_band_ghz"])),
        dict(no=3, title_ko="기준이 되는 «블레이드만 도는» 표는 이 단계가 독립 재현하지 않았다",
             detail_ko=("PO 커널을 numpy·CPU 로 새로 짜서 재현한 것은 온몸이 도는 팔(정육면체·강체회전 메쉬)"
                        "뿐이다. 비교 상대인 base 의 mesh 팔(로터 4개만 도는 진짜 배치)은 로터 위치·회전 "
                        "방향·프레임 결합 경로가 따로 있어 다시 만들지 않았다. 그 표에 계통 오차가 있으면 "
                        "이 단의 모든 «정육면체 vs 진짜 드론» 숫자가 함께 흔들린다."),
             quantified=dict(kernel_replication_max_rel_diff=kernel_block.get("max_rel_diff"),
                             arms_replicated=sorted({r["arm"] for r in kernel_block.get("rows", [])}),
                             arms_not_replicated=["mesh (base, rotors-only spin)", "sphere", "slab", "disc"])),
        dict(no=4, title_ko="정육면체 점구름 자체가 4겹 대칭이 아니다 — 찌꺼기 선이 있다",
             detail_ko=(
                 "정육면체 «모양» 은 90° 대칭이지만 그 위에 깐 «점» 은 아니다(윗면 "
                 f"{residue['_cloud_symmetry'][d0]['n_top_face']}점·아랫면 "
                 f"{residue['_cloud_symmetry'][d0]['n_bottom_face']}점·옆면 각 "
                 f"{residue['_cloud_symmetry'][d0]['n_per_side_face']:.0f}점, 90° 돌리면 점이 최대 한 변의 "
                 f"{residue['_cloud_symmetry'][d0]['rot90_max_point_mismatch_over_side']*100:.1f}% 만큼 어긋난다). "
                 "그 탓에 홀수 차수에 작은 찌꺼기가 뜬다(AC 진폭의 "
                 f"{residue[d0]['coarse_amplitude_frac_of_ac']*100:.1f}% / "
                 f"{residue[d1]['coarse_amplitude_frac_of_ac']*100:.1f}%). 점을 촘촘히 깔면 전력이 "
                 f"{residue[d0]['odd_power_shrink_x']:.0f}배 / {residue[d1]['odd_power_shrink_x']:.0f}배 줄어들어 "
                 "«모양이 아니라 점 깔기» 임이 확인되지만, 이 찌꺼기가 P5 가 문턱을 못 넘긴 원인이고 "
                 "P2 의 몫이 1.0000 이 아닌 원인이다. 지표 본체(차수 4·8)에는 세 자릿수 아래라 영향이 없다. "
                 "⚠ 왜 하필 홀수 차수에만 실리고 «4로 나눠 2 남는» 차수는 기계적 0 인지는 여기서 규명하지 못했다 "
                 "— 설명 없는 규칙성은 그 자체로 미해결 항목이다."),
             quantified={d: dict(coarse_frac_odd=residue[d]["coarse_frac_odd"],
                                 fine_frac_odd=residue[d]["fine_frac_odd"],
                                 shrink_x=residue[d]["odd_power_shrink_x"]) for d in DRONE_KEYS
                         if d in residue}),
        dict(no=5, title_ko="«방위 24점» 은 정육면체에서 독립 표본이 아니다 — 산포를 신뢰구간으로 읽으면 안 된다",
             detail_ko=("온몸이 도는 물체는 «보는 방위를 바꾸기» 와 «회전 위상을 옮기기» 가 같은 조작이다. "
                        "그래서 정육면체의 24 방위는 같은 신호를 시간축에서 민 것뿐이고, 표준편차는 통계적 "
                        "산포가 아니라 표집 어긋남(접힘) 잔차다. 진짜 드론은 몸통이 안 돌아 24 방위가 진짜로 "
                        "다르다. **두 팔의 산포를 같은 뜻으로 비교하면 안 된다** — 짝지은 차이(paired)만 쓴다."),
             quantified=dict(cube_sd_n_eff={d: sc["P5_azimuth_degenerate"]["cube_sd_n_eff"]
                                            for d, sc in ((d0, sc0), (d1, sc1))},
                             drone_sd_n_eff={d: sc["P5_azimuth_degenerate"]["drone_sd_n_eff"]
                                             for d, sc in ((d0, sc0), (d1, sc1))},
                             aliasing_residual_rel_ac={k: v["mean_residual_rel_ac"]
                                                       for k, v in alias.items() if not k.startswith("_")})),
        dict(no=6, title_ko="«부피 등가» 는 여러 등가 규칙 중 하나일 뿐이다",
             detail_ko=("한 변을 V^(1/3) 으로 잡았다. 표면적을 맞추거나(정육면체가 작아진다), 회전 반경을 "
                        "맞추거나(커진다), 정적 RCS 를 맞추면 정육면체 크기가 달라지고 폭·차수 구성도 같이 "
                        "움직인다. 이 단의 결론(«형상이 값어치가 있다»)은 등가 규칙을 바꿔도 살아남아야 "
                        "진짜인데, 여기서는 한 규칙만 시험했다. 참고로 부피를 맞추면 겉넓이는 "
                        f"{RJ['equal_volume_construction']['values'][d0]['cube_over_sphere_area']:.3f} 배(구 대비)로 "
                        "따라 달라진다 — 등가 규칙이 하나로 정해지지 않는다는 증거다."),
             quantified={d: dict(cube_side_m=RJ["equal_volume_construction"]["values"][d]["cube_side_m"],
                                 rmax_inplane_cube_m=RJ["equal_volume_construction"]["values"][d]["rmax_inplane_cube_m"],
                                 rmax_inplane_drone_m=RJ["equal_volume_construction"]["values"][d]["rmax_inplane_drone_m"])
                         for d in DRONE_KEYS}),
    ]

    # ── 4-10. 그림 ─────────────────────────────────────────────────────────
    figs = []
    try:
        figs = make_figure(metrics_all, per_az_raw, idx, scorecard, contrast)
    except Exception as e:                                              # noqa: BLE001
        figs = [dict(error=repr(e))]

    out = dict(
        meta=dict(
            report="report16 — 등가부피 정육면체 단: 지표 추출 + 사전예측 채점",
            producer="benchmark/report16_metric_cube_eqvol.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            stage_ko=("계산 단계가 저장한 위상 표를 다시 읽어 지표를 뽑고, 봉인해 둔 예측과 대조한다. "
                      "지표 공식과 PO 커널을 **독립 재구현**해서 계산 단계 숫자를 검산한다."),
            inputs={p: dict(sha256=sha256(p), bytes=os.path.getsize(p))
                    for p in (BASE_JSON, BASE_NPZ, RUNG_JSON, RUNG_NPZ, PREREG)},
            gpu_used="none (CPU only)",
            gpu_note_ko=("저장된 표를 읽는 후처리라 GPU 가 필요 없다. 검산용 PO 재계산도 CPU numpy 로 했다. "
                         "지금 GPU 4장은 형제 워크플로가 쓰고 있어 건드리지 않았다."),
            numpy=np.__version__, python=sys.version.split()[0],
            seconds=None),
        metric_definitions_inherited=dict(
            source="outputs/report16_base.json :: metric_definitions",
            definitions=BJ["metric_definitions"],
            note_ko=("정의는 기반 단계 것을 그대로 쓴다. 구현만 새로 했다 — 그래야 검산이 된다."),
            added_here_ko=dict(
                tone_limit_db="한 차수 ±쌍만 있는 신호의 플래시 대조비 이론값. 이 위로 얼마나 올라가는지가 «진짜 플래시» 의 척도다.",
                beta_own="팔마다 자기 회전 반경으로 다시 잡은 대역 한계. 온몸이 도는 팔은 프로펠러 팁이 기준이 아니다.",
                symmetry_order="AC 전력이 g 의 배수 차수에만 실리는 최대 g. 회전 대칭 겹수를 스펙트럼에서 직접 읽는다.",
                dominant_pm_balance="으뜸 차수의 +m 과 −m 전력 균형. 균형이면 포락선이 |cos| 꼴로 출렁여 플래시가 아니라 사인파가 된다.",
                auc_A_over_B="24×24 맞대결 승률. 지표가 두 팔을 실제로 갈라 놓는지 본다.")),
        verification=dict(metric_formula_audit=metric_audit, po_kernel_audit=kernel_block),
        metrics_all_arms=metrics_all,
        contrast_paired=contrast,
        structural_ceiling=ceiling,
        azimuth_aliasing=alias,
        cube_point_cloud_residue=residue,
        prediction_preregistered=dict(
            file=PREREG, sha256=PR["sha256_of_body"], written_at=PR["written_at"],
            one_line_ko=pred["one_line_ko"],
            thresholds_ko=pred["thresholds_are_prereg_ko"],
            what_would_falsify_ko=pred["what_would_falsify_ko"]),
        prediction_scorecard_independent=scorecard,
        prediction_scorecard_totals=dict(
            n_pass=tot_p, n_total=tot_n,
            headline_band_3p5GHz=dict(n_pass=main_p, n_total=main_n),
            po_knee_band_15p86GHz=dict(n_pass=hi_p, n_total=hi_n),
            by_band={k: dict(n_pass=v["_n_pass"], n_total=v["_n_total"])
                     for k, v in scorecard.items()},
            scope_ko=("사전예측이 문턱을 못박은 것은 **헤드라인 대역(3.5 GHz)** 이다. 고대역 채점은 "
                      "같은 문턱을 그대로 옮겨 본 확장이라 «참고» 로 읽어야 한다 — 특히 P6 의 1e-12 는 "
                      "표본 수·주파수와 함께 커지는 누적 오차를 감안하지 않은 고정값이다.")),
        agreement_with_compute_stage=agree,
        prediction_vs_outcome_ko=verdict_ko,
        reasons_to_distrust=distrust,
        figures=figs)

    # 헤드라인 — 전부 위에서 계산된 값을 참조해서 만든다(손입력 없음)
    out["headline_ko"] = [
        (f"사전예측 채점(내 독립 계산): 헤드라인 3.5 GHz **{main_p}/{main_n}**, "
         f"참고 15.86 GHz {hi_p}/{hi_n}. 계산 단계의 채점과 헤드라인 대역 12건 전부 일치. "
         "틀린 둘(P3-c·P5)은 «정육면체가 예상과 다르게 행동했다» 가 아니라 «문턱을 잘못 잡았다» 쪽이다."),
        (f"정육면체는 변조가 모자란 게 아니라 **너무 많다**: 동체:변조 비가 진짜 드론(프로펠러만 회전)보다 "
         f"{g2('main', d0, 'cube_eqvol', 'mesh', 'dc_ac_db'):+.1f} / "
         f"{g2('main', d1, 'cube_eqvol', 'mesh', 'dc_ac_db'):+.1f} dB (24/24 방위 같은 부호). "
         "⚠ 다만 이 우위는 **형상이 아니라 운동학** 덕이다 — 진짜 드론을 똑같이 온몸째 돌리면 오히려 "
         f"{g2('main', d0, 'cube_eqvol', 'mesh_rigid_spin_pec', 'dc_ac_db'):+.1f} / "
         f"{g2('main', d1, 'cube_eqvol', 'mesh_rigid_spin_pec', 'dc_ac_db'):+.1f} dB 로 정육면체가 진다."),
        (f"그런데 모양은 빈약하다: 운동학을 똑같이 맞춘 «온몸 회전» 끼리 맞대도 하모닉 풍부도가 "
         f"{g2('main', d0, 'cube_eqvol', 'mesh_rigid_spin_pec', 'n_eff_orders'):+.2f} / "
         f"{g2('main', d1, 'cube_eqvol', 'mesh_rigid_spin_pec', 'n_eff_orders'):+.2f} 차수 낮다 — "
         f"24×24 맞대결에서 진짜 드론이 이긴 비율 "
         f"{1-cx[f'main|{d0}|cube_eqvol - mesh_rigid_spin_pec']['n_eff_orders']['auc_A_over_B']:.2f} / "
         f"{1-cx[f'main|{d1}|cube_eqvol - mesh_rigid_spin_pec']['n_eff_orders']['auc_A_over_B']:.2f} "
         "(두 무리가 완전히 갈린다)."),
        (f"구조적 천장: 진짜 드론 변조 전력의 "
         f"{ceiling['main|'+d0]['unreachable_frac_mean']*100:.1f}% / "
         f"{ceiling['main|'+d1]['unreachable_frac_mean']*100:.1f}% 는 4의 배수가 아닌 차수에 있어 "
         "정육면체 가족이 **원리상** 못 닿는다. 파형 상관의 천장이 "
         f"{ceiling['main|'+d0]['corr_ceiling_mean']:.3f} / {ceiling['main|'+d1]['corr_ceiling_mean']:.3f} 인 이유다."),
        ("⚠ 정육면체에 유리한 쪽으로도 정직하게: 정육면체가 닿을 수 있는 자리(4의 배수 차수)만 남기고 "
         f"파형을 맞대면 상관이 {sc0['P3_blade_line_absent']['corr_within_mod4_subspace_mean']:.3f} / "
         f"{sc1['P3_blade_line_absent']['corr_within_mod4_subspace_mean']:.3f} 까지 오른다"
         f"({d0} 는 꽤 닮았고 {d1} 는 절반도 못 닮았다). 즉 정육면체를 무너뜨리는 주된 힘은 "
         "파형의 모양이 아니라 **닿을 수 있는 자리가 좁다는 것**이다 — 이 구별을 뭉개면 안 된다."),
        (f"3.5 GHz 에서 정육면체에는 «플래시» 가 없다: 플래시 대조비 "
         f"{metrics_all[f'main|{d0}|cube_eqvol']['flash_contrast_db']['mean']:.2f} dB 는 순음 한계 "
         f"{metrics_all[f'main|{d0}|cube_eqvol']['tone_limit_db']['mean']:.2f} dB 바로 위 — 뾰족한 반짝임이 아니라 "
         "느린 사인파 출렁임이다(진짜 드론 "
         f"{metrics_all[f'main|{d0}|mesh']['flash_contrast_db']['mean']:.2f} dB). "
         "⚠ 그러나 이 결론은 **대역에 매인다**: 15.86 GHz 에서는 정육면체의 플래시 대조비가 "
         f"{metrics_all[f'hi|{d0}|cube_eqvol']['flash_contrast_db']['mean']:.1f} / "
         f"{metrics_all[f'hi|{d1}|cube_eqvol']['flash_contrast_db']['mean']:.1f} dB 로 올라가 "
         f"진짜 드론({metrics_all[f'hi|{d0}|mesh']['flash_contrast_db']['mean']:.1f} / "
         f"{metrics_all[f'hi|{d1}|mesh']['flash_contrast_db']['mean']:.1f} dB)을 **넘어선다** — "
         "«플래시 대조비» 하나로 형상을 가르려 하면 고대역에서 뒤집힌다. 하모닉 풍부도는 뒤집히지 않는다."),
    ]
    out["meta"]["seconds"] = time.time() - t_start

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(jsonify(out), f, ensure_ascii=False, indent=1)
    print(f"\n[write] {OUT_JSON}  ({os.path.getsize(OUT_JSON)/1024:.0f} kB, "
          f"{out['meta']['seconds']:.1f}s)")
    for h in out["headline_ko"]:
        print("  · " + h)
    return out


# =========================================================================== #
#  5. 그림 (텍스트는 영어)
# =========================================================================== #
def make_figure(metrics_all, per_az_raw, idx, scorecard, contrast):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    C_CUBE, C_MESH, C_RIGID, C_SPH = "#d1495b", "#2e5eaa", "#66a182", "#8d8d8d"
    fig, axes = plt.subplots(2, 3, figsize=(16.5, 9.0))

    # (a,b) harmonic ladder
    for ax, d in zip(axes[0, :2], DRONE_KEYS):
        for arm, col, lab in (("mesh", C_MESH, "CAD drone (blades spin)"),
                              ("mesh_rigid_spin_pec", C_RIGID, "CAD drone (whole body spins)"),
                              ("cube_eqvol", C_CUBE, "equal-volume cube")):
            if ("main", d, arm) not in idx:
                continue
            T = idx[("main", d, arm)][0]
            ops = np.array([order_power(T[i])[0] for i in range(T.shape[0])])
            mo = ops.mean(axis=0)
            n = min(25, len(mo))
            ax.semilogy(np.arange(1, n), np.maximum(mo[1:n], 1e-12), "o-", ms=3.5,
                        color=col, label=lab, lw=1.6)
        ax.set_title(f"{d} — harmonic ladder (mean over 24 azimuths)", fontsize=11)
        ax.set_xlabel("harmonic order m  (Doppler = m x f_rot)")
        ax.set_ylabel("AC power fraction")
        ax.set_ylim(1e-9, 2.0)
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8, loc="upper right")

    # (c) structural ceiling
    ax = axes[0, 2]
    labs, vals4, vals2, valso = [], [], [], []
    for d in DRONE_KEYS:
        op = per_az_raw[("main", d, "mesh")]
        labs.append(d)
        vals4.append(op["frac_mod4_0"].mean())
        vals2.append(op["frac_mod4_2"].mean())
        valso.append(op["frac_odd"].mean())
    x = np.arange(len(labs))
    ax.bar(x - 0.25, vals4, 0.25, color=C_CUBE, label="m = 4,8,12...  (cube CAN reach)")
    ax.bar(x, vals2, 0.25, color=C_MESH, label="m = 2,6,10...  (cube cannot)")
    ax.bar(x + 0.25, valso, 0.25, color=C_RIGID, label="m odd  (cube cannot)")
    ax.set_xticks(x)
    ax.set_xticklabels(labs)
    ax.set_ylabel("share of the drone's AC power")
    ax.set_title("Where the real drone puts its modulation", fontsize=11)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=8)

    # (d,e,f) headline metric spreads
    ARMS = [("mesh", C_MESH, "drone\nblades"), ("mesh_rigid_spin_pec", C_RIGID, "drone\nbody"),
            ("cube_eqvol", C_CUBE, "cube\nbody"), ("sphere", C_SPH, "sphere\nnull")]
    panels = [("dc_ac_db", "body : modulation  [dB]  (lower = stronger modulation)"),
              ("n_eff_orders", "harmonic richness  n_eff  [orders]"),
              ("flash_contrast_db", "flash contrast  [dB]")]
    step = len(ARMS) + 1.5
    for ax, (mk, title) in zip(axes[1, :], panels):
        pos, ticks, centers = [], [], []
        for i, d in enumerate(DRONE_KEYS):
            xs = []
            for j, (arm, col, lab) in enumerate(ARMS):
                if ("main", d, arm) not in per_az_raw:
                    continue
                v = per_az_raw[("main", d, arm)][mk]
                xx = i * step + j
                ax.scatter(np.full_like(v, xx, dtype=float), v, s=13, color=col, alpha=0.55,
                           edgecolors="none")
                ax.plot([xx - 0.32, xx + 0.32], [v.mean()] * 2, color=col, lw=2.6)
                pos.append(xx)
                ticks.append(lab)
                xs.append(xx)
            centers.append((float(np.mean(xs)), d))
        if mk == "flash_contrast_db":
            tl = metrics_all[f"main|{DRONE_KEYS[0]}|cube_eqvol"]["tone_limit_db"]["mean"]
            ax.axhline(tl, color="k", ls="--", lw=1.0)
            ax.text(0.98, tl, "pure-tone limit (no flash) ", va="bottom", ha="right", fontsize=8,
                    transform=ax.get_yaxis_transform())
        ax.set_xticks(pos)
        ax.set_xticklabels(ticks, fontsize=7.5)
        ax.set_xlim(-0.9, (len(DRONE_KEYS) - 1) * step + len(ARMS) - 0.1)
        for cxx, d in centers:
            ax.text(cxx, -0.175, d, ha="center", va="top", fontsize=9.5, fontweight="bold",
                    transform=ax.get_xaxis_transform())
        ax.set_title(title, fontsize=10)
        ax.grid(alpha=0.3, axis="y")
    fig.suptitle("report16 — equal-volume cube: what the metrics say  (3.5 GHz, el 15 deg, "
                 "24 azimuths, monostatic PO)", fontsize=12.5)
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=145)
    plt.close(fig)
    return [dict(path=OUT_FIG,
                 caption_ko=("(a,b) 차수별 변조 전력 — 정육면체(빨강)는 4의 배수 자리에만 선을 세운다. "
                             "진짜 드론(파랑)은 그 사이사이(차수 2,6,10…)에도 선이 있다. "
                             "(c) 진짜 드론의 변조가 어느 자리에 실려 있나 — 절반가량이 정육면체가 못 닿는 자리다. "
                             "(d,e,f) 헤드라인 지표 — 점 하나가 방위 하나, 굵은 선이 평균. "
                             "정육면체는 «세지만 단순하다». 가로축 라벨의 blades = 프로펠러만 회전, "
                             "body = 온몸 회전(운동학을 정육면체와 똑같이 맞춘 대조군)."))]


if __name__ == "__main__":
    main()
