# -*- coding: utf-8 -*-
"""
verify_facet_mechanism.py — **면 하나짜리 최소 대조로 기전을 확정한다**
=======================================================================
검사 대상 가설 H:
    "Sionna RT 기본 path solver 의 표적 에코는 **면(facet)당 정반사 경로 1개**이고,
     그 경로의 진폭은 **면의 크기와 무관**하다(= image-source 진폭)."

이 스크립트는 드론 같은 복잡 메쉬를 치우고, **단일 평판 / 같은 평판의 세분 / 구의 테셀레이션**
세 가지 최소 사례만으로 H 를 검사한다. 기하는 자유공간 준-모노스태틱이다.

  [A] 단일 평판 크기 스윕 — 변 0.1/0.2/0.5/1/2/4 m.
      σ_PO = 4πA²/λ² 는 변⁴ 로 커지므로 0.1→4 m 사이 진폭은 이론상 +64 dB 여야 한다.
      RT 진폭이 불변이면 H 지지. (⭐ 우리 과거 기록 outputs/rt_no_rcs_verify.json 의
       'A_plate: 변 0.2→4 m 에서 ratio_db 불변' 재현 여부를 함께 판정한다.)

  [B] 같은 평판을 삼각형 2/8/32/128/512 개로 세분 — **형상이 완전히 동일**하고 삼각형 수만 는다.
      전력이 변하면 '삼각형 수' 가 진폭을 만든다는 뜻이고, 안 변하면 '형상만' 이 진폭을 만든다.

  [C] 구 테셀레이션 — 반지름 고정, 삼각형 수만 48→16128.
      구는 정반사점이 하나뿐이므로 면 수가 늘어도 전력이 안 변해야 정상이다.
      다만 그 '불변값'이 πr² 짜리 구의 값인지 거울판 값인지는 별개 문제 → 함께 잰다.

⚠ 광선 예산(samples_per_src)과 max_depth 를 모든 셀에 명시해 기록하고, 예산을 바꿔
   결과가 안정한지 확인한다. 소형 표적은 '진폭'이 아니라 '경로를 찾느냐(검출확률)'가
   예산에 걸리므로, 발견율과 발견시 진폭을 **분리해서** 보고한다.

실행: SIONNA2_GPU=3 python benchmark/verify_facet_mechanism.py
"""
from __future__ import annotations

import os
import sys
import json
import math
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

# ⚠ GPU 는 mitsuba/sionna import 전에 고정해야 한다.
#   GPU2 는 benchmark/rcs_anchor.py 가 쓰는 중 → 절대 건드리지 않는다(호출부에서 SIONNA2_GPU 강제).
os.environ.setdefault("SIONNA2_GPU", "3")
os.environ.setdefault("SIONNA2_PREFER_GPUS", "3,0")
from gpu import pick  # noqa: E402

_GPU = pick()

import mitsuba as mi  # noqa: E402
import sionna.rt as rt  # noqa: E402

from geom import Mesh, uv_sphere  # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC

SCRATCH = "/tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/facet"
os.makedirs(SCRATCH, exist_ok=True)
OUT = os.path.join(ROOT, "outputs", "facet_mechanism.json")

# --- 자유공간 준-모노스태틱 기하 ------------------------------------------------ #
#   TX·RX 를 0.10 m(≈1.17λ) 만 띄운다. 바이스태틱각 β≈0.29° → 사실상 모노스태틱이지만
#   완전 동일좌표에서 생기는 퇴화(LOS τ=0, 법선 정의 불가)를 피한다.
TX = np.array([0.0, 0.0, 0.0])
RX = np.array([0.0, 0.10, 0.0])
TGT = np.array([20.0, 0.0, 0.0])


def geom_params():
    """(R1, R2, 이등분선 법선 n, 평판 접평면 기저 a·b, 바이스태틱각 β[deg])."""
    d1 = TX - TGT
    d2 = RX - TGT
    R1 = float(np.linalg.norm(d1))
    R2 = float(np.linalg.norm(d2))
    u1, u2 = d1 / R1, d2 / R2
    n = u1 + u2
    n /= np.linalg.norm(n)                      # 이등분선 = 정반사 법선(표적→레이더 방향)
    a = np.cross(n, [0.0, 0.0, 1.0]); a /= np.linalg.norm(a)
    b = np.cross(n, a)
    beta = math.degrees(math.acos(float(np.clip(u1 @ u2, -1, 1))))
    return R1, R2, n, a, b, beta


R1, R2, NRM, AX, BX, BETA = geom_params()
RSUM = R1 + R2
TAU_E = RSUM / C0


# ============================================================================== #
#  메쉬 만들기
# ============================================================================== #
def _rot(v, axis, deg):
    """로드리게스 회전."""
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    th = math.radians(deg)
    return (v * math.cos(th) + np.cross(a, v) * math.sin(th)
            + a * float(a @ v) * (1 - math.cos(th)))


def plate_mesh(side: float, k: int = 1, tilt_deg: float = 0.0) -> Mesh:
    """정반사 법선에 맞춘 정사각 금속 평판. k×k 격자로 나눠 삼각형 2·k² 개.
    ⭐ k 가 달라져도 **형상(꼭짓점이 이루는 사각형)은 완전히 동일**하다.
    tilt_deg 는 이등분선에서 평판을 기울인 각(정반사 조건을 일부러 깬다)."""
    m = Mesh(group="plate")
    h = side / 2.0
    ax_, bx_ = AX, BX
    if abs(tilt_deg) > 1e-12:                       # BX 축을 중심으로 접평면을 기울인다
        ax_ = _rot(AX, BX, tilt_deg)
    idx = [[0] * (k + 1) for _ in range(k + 1)]
    for i in range(k + 1):
        for j in range(k + 1):
            s = -h + side * i / k
            t = -h + side * j / k
            p = TGT + s * ax_ + t * bx_
            idx[i][j] = m.add_vertex(*p)
    for i in range(k):
        for j in range(k):
            m.add_quad(idx[i][j], idx[i + 1][j], idx[i + 1][j + 1], idx[i][j + 1])
    return m


def write_obj(m: Mesh, tag: str) -> str:
    fn = os.path.join(SCRATCH, f"{tag}.obj")
    m.write_obj(fn)
    return fn


# ============================================================================== #
#  RT 실행
# ============================================================================== #
_METAL = None


def metal_material():
    """ITU metal(σ=1e7 S/m, 산란계수 0) — 정반사만 열어 둔다."""
    global _METAL
    if _METAL is None:
        _METAL = rt.RadioMaterial(name="facet_metal", relative_permittivity=1.0,
                                  conductivity=1e7, scattering_coefficient=0.0)
    return _METAL


def run_rt(obj_path: str, spp: int, seed: int, max_depth: int, diffuse: bool = False):
    """장면에 물체 하나만 놓고 경로를 푼다 → 표적 에코 지표 dict."""
    scene = rt.load_scene()
    scene.frequency = FC
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    o = rt.SceneObject(fname=obj_path, name="tgt", radio_material=metal_material())
    scene.edit(add=[o])
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in TX])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in RX])))

    paths = rt.PathSolver()(scene, max_depth=int(max_depth), los=True,
                            specular_reflection=True, diffuse_reflection=bool(diffuse),
                            refraction=False, diffraction=False,
                            samples_per_src=int(spp), seed=int(seed))
    ar = np.asarray(paths.a[0]); ai = np.asarray(paths.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = a.shape[0]
    tau = np.asarray(paths.tau).reshape(-1, P)[0]
    inter = np.asarray(paths.interactions)[:, 0, 0, :]
    hit = (inter != 0).any(axis=0)                  # 물체와 상호작용한 경로 = 표적 에코

    los_amp = float(abs(complex(np.sum(a[~hit])))) if (~hit).any() else 0.0
    out = dict(spp=int(spp), seed=int(seed), max_depth=int(max_depth),
               n_paths_total=int(P), n_paths_target=int(hit.sum()),
               los_amp=los_amp)
    if hit.any():
        at = a[hit]
        out["coh_db"] = float(20 * np.log10(abs(complex(np.sum(at))) + 1e-300))
        out["incoh_db"] = float(10 * np.log10(float(np.sum(np.abs(at) ** 2)) + 1e-300))
        out["tau_ns_mean"] = float(np.mean(tau[hit]) * 1e9)
        out["tau_ns_expect"] = float(TAU_E * 1e9)
        out["amp_max"] = float(np.max(np.abs(at)))
    else:
        out["coh_db"] = None
        out["incoh_db"] = None
        out["tau_ns_mean"] = None
        out["tau_ns_expect"] = float(TAU_E * 1e9)
        out["amp_max"] = None
    del scene, paths
    return out


def cell(obj_path, spp, seeds, max_depth, diffuse=False):
    """여러 시드로 돌려 (발견율, 발견시 진폭 평균/표준편차)를 분리해 요약."""
    runs = [run_rt(obj_path, spp, s, max_depth, diffuse) for s in seeds]
    ok = [r for r in runs if r["coh_db"] is not None]
    det = len(ok) / len(runs)
    summ = dict(spp=int(spp), max_depth=int(max_depth), n_seeds=len(seeds),
                detect_rate=det,
                n_paths_target_mean=float(np.mean([r["n_paths_target"] for r in runs])),
                n_paths_target_set=sorted({r["n_paths_target"] for r in runs}),
                runs=runs)
    if ok:
        c = np.array([r["coh_db"] for r in ok])
        i = np.array([r["incoh_db"] for r in ok])
        summ.update(coh_db=float(c.mean()), coh_sd=float(c.std()),
                    incoh_db=float(i.mean()), incoh_sd=float(i.std()),
                    coh_min=float(c.min()), coh_max=float(c.max()),
                    tau_ns_mean=float(np.mean([r["tau_ns_mean"] for r in ok])))
    else:
        summ.update(coh_db=None, coh_sd=None, incoh_db=None, incoh_sd=None,
                    coh_min=None, coh_max=None, tau_ns_mean=None)
    return summ


# ============================================================================== #
#  이론 기준선
# ============================================================================== #
def sigma_plate_po(side):
    """모노스태틱 정입사 평판 PO: σ = 4πA²/λ²."""
    A = side * side
    return 4 * math.pi * A * A / (LAM ** 2)


def amp_from_sigma(sigma):
    """등방 안테나 레이더식 |a|² = λ²σ/((4π)³R1²R2²) → 진폭."""
    return math.sqrt((LAM ** 2) * sigma / ((4 * math.pi) ** 3 * (R1 ** 2) * (R2 ** 2)))


def amp_image_source():
    """무한 거울 근사(image source): 진폭 = λ/(4π·(R1+R2)) — **크기 무관**."""
    return LAM / (4 * math.pi * RSUM)


def db(x):
    return float(20 * math.log10(max(float(x), 1e-300)))


# ============================================================================== #
#  본체
# ============================================================================== #
def main():
    t0 = time.time()
    SEEDS = [1, 2, 3, 4, 5]
    BUDGETS = [1_000_000, 4_000_000, 16_000_000, 64_000_000]
    DEPTHS = [1, 2]

    res = {
        "_meta": {
            "task": "면 하나짜리 최소 대조로 'facet 당 정반사 1개·진폭 크기무관' 기전을 확정",
            "date": "2026-08-03",
            "sionna": "2.0.1",
            "gpu": str(_GPU),
            "fc_hz": FC, "lambda_m": LAM,
            "geometry": dict(tx=TX.tolist(), rx=RX.tolist(), tgt=TGT.tolist(),
                             R1=R1, R2=R2, R_sum=RSUM, bistatic_deg=BETA,
                             note="자유공간 준-모노스태틱(TX·RX 0.10 m 이격). 벽·바닥 없음."),
            "solver": dict(specular_reflection=True, diffuse_reflection=False,
                           refraction=False, diffraction=False, los=True,
                           material="ITU-metal 근사(conductivity=1e7, S=0)",
                           budgets=BUDGETS, depths=DEPTHS, seeds=SEEDS),
            "tau_expect_ns": TAU_E * 1e9,
        },
        "theory": {
            "amp_image_source_db": db(amp_image_source()),
            "note": "image_source = λ/(4π(R1+R2)), 크기 무관. po = 레이더식 with σ=4πA²/λ².",
        },
    }

    # ---- 0) 규약 교정: LOS 진폭이 λ/(4πd) 인지 확인한다 ---------------------- #
    #      (Sionna 의 a 규약을 실측으로 못박아야 아래 dB 비교가 의미를 가진다)
    obj0 = write_obj(plate_mesh(1.0, 1), "cal_plate")
    r0 = run_rt(obj0, 1_000_000, 1, 1)
    d_txrx = float(np.linalg.norm(TX - RX))
    res["_meta"]["convention_check"] = dict(
        los_amp_measured_db=db(r0["los_amp"]),
        los_amp_friis_db=db(LAM / (4 * math.pi * d_txrx)),
        d_tx_rx=d_txrx,
        note="일치하면 a 는 등방 Friis 규약(λ/4πd)이다.")
    print(f"[cal] LOS 실측 {db(r0['los_amp']):.3f} dB  vs Friis {db(LAM/(4*math.pi*d_txrx)):.3f} dB")

    # =========================================================================== #
    #  [A] 단일 평판 크기 스윕
    # =========================================================================== #
    print("\n=== [A] 평판 크기 스윕 ===")
    A_rows = []
    for side in (0.1, 0.2, 0.5, 1.0, 2.0, 4.0):
        obj = write_obj(plate_mesh(side, 1), f"plate_{side:.2f}")
        sig = sigma_plate_po(side)
        row = dict(side_m=side, n_tri=2, area_m2=side * side,
                   sigma_po_dbsm=float(10 * math.log10(sig)),
                   amp_po_db=db(amp_from_sigma(sig)),
                   far_field_dist_m=2 * (side * math.sqrt(2)) ** 2 / LAM,
                   budget=[])
        for spp in BUDGETS:
            c = cell(obj, spp, SEEDS, max_depth=1)
            row["budget"].append(c)
            print(f"  side={side:4.1f} spp={spp/1e6:5.1f}M  det={c['detect_rate']:.1f} "
                  f"n={c['n_paths_target_set']} coh={c['coh_db']}")
        # 예산 최대에서의 대표값
        best = row["budget"][-1]
        row["coh_db"] = best["coh_db"]
        row["n_paths_target_set"] = best["n_paths_target_set"]
        row["detect_rate"] = best["detect_rate"]
        A_rows.append(row)
    res["A_plate_size"] = A_rows

    # max_depth 안정성 (대표 크기 1 m)
    obj1 = write_obj(plate_mesh(1.0, 1), "plate_depth")
    res["A_depth_check"] = [cell(obj1, 16_000_000, SEEDS, max_depth=d) for d in DEPTHS]

    # =========================================================================== #
    #  [B] 같은 평판을 삼각형 N 개로 세분 (형상 동일)
    # =========================================================================== #
    print("\n=== [B] 동일 형상 세분 ===")
    B_rows = []
    for side in (1.0, 0.2):
        for k in (1, 2, 4, 8, 16):
            m = plate_mesh(side, k)
            obj = write_obj(m, f"sub_{side:.2f}_k{k}")
            row = dict(side_m=side, k=k, n_tri=len(m.f), n_vert=len(m.v), budget=[])
            for spp in BUDGETS:
                c = cell(obj, spp, SEEDS, max_depth=1)
                row["budget"].append(c)
            best = row["budget"][-1]
            row.update(coh_db=best["coh_db"], detect_rate=best["detect_rate"],
                       n_paths_target_set=best["n_paths_target_set"])
            print(f"  side={side} k={k:2d} tri={len(m.f):4d}  det={best['detect_rate']:.1f} "
                  f"n={best['n_paths_target_set']} coh={best['coh_db']}")
            B_rows.append(row)
    res["B_subdivide"] = B_rows

    # =========================================================================== #
    #  [C] 구 테셀레이션
    # =========================================================================== #
    print("\n=== [C] 구 테셀레이션 ===")
    C_rows = []
    r_sph = 0.5
    sigma_sph = math.pi * r_sph ** 2                        # GO: σ = πr²
    res["theory"]["sphere_sigma_dbsm"] = float(10 * math.log10(sigma_sph))
    res["theory"]["sphere_amp_db"] = db(amp_from_sigma(sigma_sph))
    res["theory"]["sphere_kr"] = 2 * math.pi * r_sph / LAM
    for seg, rings in ((8, 4), (16, 8), (32, 16), (64, 32), (128, 64)):
        m = uv_sphere(r_sph, center=tuple(float(v) for v in TGT), seg=seg, rings=rings)
        obj = write_obj(m, f"sph_{seg}x{rings}")
        row = dict(r_m=r_sph, seg=seg, rings=rings, n_tri=len(m.f), n_vert=len(m.v),
                   budget=[])
        for spp in BUDGETS:
            c = cell(obj, spp, SEEDS, max_depth=1)
            row["budget"].append(c)
        best = row["budget"][-1]
        row.update(coh_db=best["coh_db"], detect_rate=best["detect_rate"],
                   n_paths_target_set=best["n_paths_target_set"])
        print(f"  seg={seg:3d} rings={rings:3d} tri={len(m.f):6d}  det={best['detect_rate']:.1f} "
              f"n={best['n_paths_target_set']} coh={best['coh_db']}")
        C_rows.append(row)
    res["C_sphere_tessellation"] = C_rows

    # ---- C2) 구 반지름 스윕 — 근접면을 x=20 m 에 고정하고 곡률만 바꾼다 ------- #
    #   기전 예측: 평면 근사에서 정반사점(수선의 발)은 면 법선이 시선에서 δ 만큼 기울면
    #   면 중심에서 ≈R·δ 만큼 밀려난다. 면의 반크기는 r·δ 이므로, 정반사점이 면 안에
    #   남으려면 **r ≳ R** 이어야 한다. 즉 테셀레이션을 아무리 올려도(둘 다 δ 에 비례)
    #   곡면은 경로를 못 만든다. r 을 키워야만 생긴다 — 이걸 직접 잰다.
    print("\n=== [C2] 구 반지름 스윕(근접면 고정) ===")
    C2 = []
    for rr in (0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 80.0):
        ctr = (float(TGT[0] + rr), 0.0, 0.0)        # 근접면이 항상 x=20 m
        m = uv_sphere(rr, center=ctr, seg=64, rings=32)
        obj = write_obj(m, f"sphR_{rr:g}")
        c = cell(obj, 16_000_000, SEEDS, max_depth=1)
        row = dict(r_m=rr, n_tri=len(m.f), ratio_r_over_R=rr / R1,
                   detect_rate=c["detect_rate"], coh_db=c["coh_db"],
                   n_paths_target_set=c["n_paths_target_set"], cell=c)
        print(f"  r={rr:6.2f} r/R={rr/R1:5.2f}  det={c['detect_rate']:.1f} coh={c['coh_db']}")
        C2.append(row)
    res["C2_sphere_radius"] = C2

    # ---- D) 각도 허용폭 — 평판을 기울여 정반사가 언제 끊기는지 --------------- #
    #   기전 예측: 정반사점은 기울기 δ 에 대해 ≈R·δ 만큼 밀려나므로, 반변 side/2 인
    #   평판은 δ_max ≈ (side/2)/R 에서 경로를 잃는다. 즉 **면 크기는 진폭이 아니라
    #   '각도 허용폭'으로만 들어온다**. 이게 확인되면 기전이 완전히 닫힌다.
    print("\n=== [D] 기울기 허용폭 ===")
    D = []
    for side in (0.2, 1.0, 4.0):
        pred = math.degrees((side / 2.0) / R1)
        for tilt in (0.0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4):
            m = plate_mesh(side, 1, tilt_deg=tilt)
            obj = write_obj(m, f"tilt_{side:g}_{tilt:g}")
            c = cell(obj, 16_000_000, SEEDS, max_depth=1)
            D.append(dict(side_m=side, tilt_deg=tilt, tilt_pred_max_deg=pred,
                          detect_rate=c["detect_rate"], coh_db=c["coh_db"],
                          n_paths_target_set=c["n_paths_target_set"]))
            print(f"  side={side:4.1f} tilt={tilt:5.2f} (pred_max={pred:5.2f}) "
                  f"det={c['detect_rate']:.1f} coh={c['coh_db']}")
    res["D_tilt_acceptance"] = D

    # 구 대조군: 재질·메쉬·솔버가 정상인지 (같은 자리 평판은 즉시 잡힌다)
    m = uv_sphere(r_sph, center=tuple(float(v) for v in TGT), seg=48, rings=24)
    obj = write_obj(m, "sph_ctrl")
    obj_ref = write_obj(plate_mesh(1.0, 1), "ctrl_plate")
    res["C_control"] = dict(
        sphere_specular_only=cell(obj, 16_000_000, SEEDS, max_depth=1, diffuse=False),
        plate_same_place=cell(obj_ref, 1_000_000, SEEDS, max_depth=1, diffuse=False),
        note="같은 자리 평판은 spp=1M 으로도 즉시 잡힌다 → 메쉬·재질·솔버는 정상. "
             "구가 0 인 것은 버그가 아니라 곡면 정반사점 문제다.")

    res["_meta"]["elapsed_sec"] = time.time() - t0
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("\n[saved]", OUT, f"({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
