# -*- coding: utf-8 -*-
"""refute_nadir_area_invariance.py — 반증자용 재측정 (CPU 전용, GPU 미사용, SBR 호출 없음).

검사 대상 주장
  «나딧에서 투영 면적은 회전에 대해 «정확히» 불변이다 → 후보 (a) 는 죽었다»
  원장 outputs/verify_nadir_flash.json → C_D_geometry.{nadir_projected_area_ac_over_dc_db,
  nadir_projected_area_props_ac_over_dc_db, nadir_plane_wave_ac_over_dc_db}
  = −319.06 / −315.13 / −305.01 dB

하는 일
  G1 원장 3 숫자를 같은 코드 경로로 재계산 (같은 메쉬·같은 4096 위상).
  G2 ⭐가림(occlusion)을 켠 «실제로 보이는» 투영 면적을 z-버퍼로 재고 AC/DC 를 낸다.
     원장의 대리모형은 note 에 «no occlusion» 이라고 스스로 적어 두었다.
  G3 ⭐기체가 아주 조금 기울면(호버 피치/롤) 어떻게 되는가 — 로터 축이 시선과
     어긋나는 순간 불변성이 성립하는지.
  결과는 outputs/refute_nadir_area_invariance.json 에만 쓴다(기존 원장 미변경).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from articulated_fast import FastPoser, rotor_phases      # noqa: E402
from drones import DRONES                                  # noqa: E402
from geom import rotate                                    # noqa: E402

OUT = f"{ROOT}/outputs/refute_nadir_area_invariance.json"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
PRF = float(TJ["prf_hz"])
N = int(TJ["n"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)
FC = 3.5e9
K = 2 * np.pi / (2.998e8 / FC)
DRONE = TJ.get("drone", "matrice4e")


def facets(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(n, axis=1)
    return n / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def acdc(x):
    """원장과 **글자 그대로 같은** 정의: 10log10( mean |x/mean(x) - 1|^2 )."""
    x = np.asarray(x, complex)
    return round(float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300)), 2)


# ─────────────────────────────────────────────────────────────────────────────
def g1_reproduce(fp, ph, f, isp):
    u90 = np.array([0.0, 0.0, -1.0])
    upl = np.array([np.cos(np.radians(-90.0)), 0.0, np.sin(np.radians(-90.0))])
    A_all = np.zeros(N)
    A_pr = np.zeros(N)
    Spl = np.zeros(N, complex)
    t0 = time.time()
    for i in range(N):
        v = fp.pose(ph[i]).v
        nn, ar, cen = facets(v, f)
        w = np.maximum(nn @ u90, 0.0) * ar
        A_all[i] = w.sum()
        A_pr[i] = w[isp].sum()
        ww = np.maximum(nn @ upl, 0.0) * ar
        Spl[i] = (ww * np.exp(-1j * 2 * K * (cen @ upl))).sum()
    return dict(
        n_poses=N,
        nadir_projected_area_ac_over_dc_db=acdc(A_all.astype(complex)),
        nadir_projected_area_props_ac_over_dc_db=acdc(A_pr.astype(complex)),
        nadir_plane_wave_ac_over_dc_db=acdc(Spl),
        facet_sum_area_m2_mean=round(float(A_all.mean()), 9),
        facet_sum_area_m2_ptp=float(np.ptp(A_all)),
        facet_sum_area_rel_ptp=float(np.ptp(A_all) / A_all.mean()),
        seconds=round(time.time() - t0, 1))


# ─────────────────────────────────────────────────────────────────────────────
def zbuf_area(v, f, res, lo, hi):
    """나딧(−z 방향에서 봄) 에서 **가림을 켠** 가시 투영 면적 [m²].

    x·y 평면을 res×res 격자로 잘라 각 화소에서 가장 낮은 z(관측자는 아래에 있다)를
    갖는 삼각형만 남긴다. 삼각형은 화소 중심 포함 판정으로 래스터화한다.
    반환: (가시 면적, 프롭이 차지한 가시 면적)."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    px = (hi[0] - lo[0]) / res
    py = (hi[1] - lo[1]) / res
    cell = px * py
    zb = np.full((res, res), np.inf)
    ib = np.full((res, res), -1, np.int64)
    x0 = lo[0] + (np.arange(res) + 0.5) * px
    y0 = lo[1] + (np.arange(res) + 0.5) * py
    for t in range(len(f)):
        A, B, C = a[t], b[t], c[t]
        ix0 = int(np.floor((min(A[0], B[0], C[0]) - lo[0]) / px))
        ix1 = int(np.ceil((max(A[0], B[0], C[0]) - lo[0]) / px))
        iy0 = int(np.floor((min(A[1], B[1], C[1]) - lo[1]) / py))
        iy1 = int(np.ceil((max(A[1], B[1], C[1]) - lo[1]) / py))
        ix0 = max(ix0, 0); iy0 = max(iy0, 0)
        ix1 = min(ix1, res); iy1 = min(iy1, res)
        if ix1 <= ix0 or iy1 <= iy0:
            continue
        X, Y = np.meshgrid(x0[ix0:ix1], y0[iy0:iy1], indexing="ij")
        d = ((B[1] - C[1]) * (A[0] - C[0]) + (C[0] - B[0]) * (A[1] - C[1]))
        if abs(d) < 1e-18:
            continue
        l1 = ((B[1] - C[1]) * (X - C[0]) + (C[0] - B[0]) * (Y - C[1])) / d
        l2 = ((C[1] - A[1]) * (X - C[0]) + (A[0] - C[0]) * (Y - C[1])) / d
        l3 = 1.0 - l1 - l2
        m = (l1 >= 0) & (l2 >= 0) & (l3 >= 0)
        if not m.any():
            continue
        z = l1 * A[2] + l2 * B[2] + l3 * C[2]
        sub_z = zb[ix0:ix1, iy0:iy1]
        sub_i = ib[ix0:ix1, iy0:iy1]
        upd = m & (z < sub_z)          # 관측자는 −z 쪽 → z 가 작을수록 앞
        sub_z[upd] = z[upd]
        sub_i[upd] = t
    vis = ib >= 0
    return float(vis.sum() * cell), ib


def g2_occlusion(fp, ph, f, isp, res=420, n_pose=64):
    """같은 로터 위상 열에서 균등하게 n_pose 개를 뽑아 가시 면적을 잰다."""
    idx = np.linspace(0, N - 1, n_pose).astype(int)
    v0 = fp.pose(ph[0]).v
    # 모든 자세를 감싸는 고정 xy 창 (프롭 디스크 반경까지)
    R = float(np.max(np.linalg.norm(v0[:, :2], axis=1))) * 1.05
    lo = np.array([-R, -R]); hi = np.array([R, R])
    tot = np.zeros(n_pose); pr = np.zeros(n_pose); nofix = np.zeros(n_pose)
    t0 = time.time()
    for j, i in enumerate(idx):
        v = fp.pose(ph[int(i)]).v
        A, ib = zbuf_area(v, f, res, lo, hi)
        tot[j] = A
        cell = (hi[0] - lo[0]) / res * (hi[1] - lo[1]) / res
        pr[j] = float(((ib >= 0) & isp[np.clip(ib, 0, None)]).sum() * cell)
        nn, ar, cen = facets(v, f)
        nofix[j] = (np.maximum(nn @ np.array([0.0, 0.0, -1.0]), 0.0) * ar).sum()
    return dict(
        method="z-buffer rasterisation of the nadir silhouette, pixel-centre inclusion",
        grid=res, window_m=round(2 * R, 4), pixel_mm=round((hi[0] - lo[0]) / res * 1e3, 3),
        n_poses=n_pose,
        visible_area_m2_mean=round(float(tot.mean()), 6),
        visible_area_ac_over_dc_db=acdc(tot.astype(complex)),
        visible_area_rel_ptp=round(float(np.ptp(tot) / tot.mean()), 6),
        visible_prop_area_m2_mean=round(float(pr.mean()), 6),
        visible_prop_area_ac_over_dc_db=acdc(pr.astype(complex)),
        control_facet_sum_ac_over_dc_db=acdc(nofix.astype(complex)),
        control_facet_sum_rel_ptp=float(np.ptp(nofix) / nofix.mean()),
        seconds=round(time.time() - t0, 1))


# ─────────────────────────────────────────────────────────────────────────────
def g3_tilt(spec, ph, tilts=(0.0, 0.1, 0.5, 1.0, 2.0, 5.0), n_pose=256):
    """기체를 피치 θ 로 기울인 채 **나딧에서** 본다 (로터 축이 시선과 θ 만큼 어긋난다)."""
    idx = np.linspace(0, N - 1, n_pose).astype(int)
    u90 = np.array([0.0, 0.0, -1.0])
    out = {}
    for th in tilts:
        fp = FastPoser(DRONES[spec], body_rpy=(0.0, float(th), 0.0))
        f = np.asarray(fp.f)
        A = np.zeros(n_pose)
        S = np.zeros(n_pose, complex)
        for j, i in enumerate(idx):
            v = fp.pose(ph[int(i)]).v
            nn, ar, cen = facets(v, f)
            w = np.maximum(nn @ u90, 0.0) * ar
            A[j] = w.sum()
            S[j] = (w * np.exp(-1j * 2 * K * (cen @ u90))).sum()
        out[f"pitch_{th:g}deg"] = dict(
            projected_area_ac_over_dc_db=acdc(A.astype(complex)),
            projected_area_rel_ptp=float(np.ptp(A) / A.mean()),
            plane_wave_ac_over_dc_db=acdc(S))
    return dict(n_poses=n_pose, note="facet-sum projected area, still NO occlusion", rows=out)


def main():
    fp = FastPoser(DRONES[DRONE])
    f = np.asarray(fp.f)
    g = np.asarray(fp.g)
    isp = g == "prop"
    ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)
    print("G1 재계산 (4096 자세)…", flush=True)
    g1 = g1_reproduce(fp, ph, f, isp)
    print(json.dumps(g1, ensure_ascii=False), flush=True)
    print("G2 가림 켠 가시 면적…", flush=True)
    g2 = g2_occlusion(fp, ph, f, isp)
    print(json.dumps(g2, ensure_ascii=False), flush=True)
    print("G3 기체 기울기…", flush=True)
    g3 = g3_tilt(DRONE, ph)
    print(json.dumps(g3, ensure_ascii=False), flush=True)
    ledger = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))["C_D_geometry"]
    doc = {
        "_meta": {
            "generator": "benchmark/refute_nadir_area_invariance.py",
            "gpu": "not used; no sbr_field call; CPU numpy only",
            "drone": DRONE, "n_slowtime": N, "prf_hz": PRF, "fc_hz": FC,
            "rpm_per_rotor": TJ["rpm_per_rotor"],
            "claim_under_test": "at nadir the projected area is EXACTLY invariant under rotor rotation, so candidate (a) is dead",
        },
        "ledger_quoted": {k: ledger[k] for k in (
            "nadir_projected_area_ac_over_dc_db",
            "nadir_projected_area_props_ac_over_dc_db",
            "nadir_plane_wave_ac_over_dc_db",
            "nadir_spherical_10m_ac_over_dc_db",
            "measured_ours_el90_ac_over_dc_db", "note")},
        "G1_reproduce_no_occlusion": g1,
        "G2_with_occlusion": g2,
        "G3_body_tilt": g3,
    }
    with open(OUT, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
