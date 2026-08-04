# -*- coding: utf-8 -*-
"""
lowfreq_anchor.py — **해석해가 있는 물체**로 저주파 격차의 원인을 가른다
================================================================================
왜 이 파일이 있는가
--------------------------------------------------------------------------------
`outputs/lowfreq_grid.json` 은 드론(Phantom 3)에서 저주파 격차의 원인을 **표본화(A)** 와
**PO 근본한계(B)** 로 가르려 했고 B 로 판정했다. 그런데 드론에는 **참값이 없다** — 판정은
"격자를 조여도 안 움직인다" 는 음성 증거와 "가파른 구간이 blade/λ≈0.27 에서 끝난다" 는
정황 증거의 결합이었다. 참값이 없으니 "PO 자체가 저 ka 에서 얼마나 틀리는가" 는 **재지 못했다**.

이 파일은 그 구멍을 메운다. 드론에는 없지만 **참값이 있는 두 물체**로 같은 진단을 반복한다:

  ① **PEC 구** — 정확 Mie 급수해(Maxwell 엄밀해)가 있다. r 을 고정하고 f 를 낮춰 ka=1~20 을
     쓸면서, 광선격자를 (a) λ/12 상대격자 (b) **절대값[mm] 사다리**로 조인다.
     ⭐ 판정: 저 ka 에서 |커널 − Mie| 가 **줄어드는가, 그대로인가?**
       · 줄어든다 → 저 ka 오차의 일부는 **표본화**였다
       · 그대로다 → 그건 **PO 자체**다
  ② **얇은 띠/판** — 폭 a=0.15λ 로 드론의 팔·블레이드를 대표한다. 정면입사 평판의
     **PO 닫힌형 4πA²/λ² 는 근사가 아니라 PO 의 정확한 답**이므로 수치 수렴의 과녁이 되고,
     2D MoM(EFIE, 근사 없음)이 **물리 참값**을 준다. 즉 이 물체는 참값과 PO 과녁을 **둘 다** 가진다.

핵심 분해 (구·판 공통)
    (커널 − 참값) = (커널 − 해석 PO)  +  (해석 PO − 참값)
                     ↑ 우리 수치오차       ↑ PO 모델을 쓴 대가 (격자로 못 줄인다)
격자를 조이면 왼쪽 항만 줄어든다. 오른쪽 항이 남으면 그것이 답이다.

⚠ 구는 매끄러워서 **특징 치수 = 반경 하나**뿐이다 — 드론(팔 0.18~0.27λ, 블레이드 0.083λ,
  동체 0.5λ 가 한 몸에 섞여 있음)과 다르다. 그래서 ②(얇은 판)를 반드시 같이 본다.

실행
    SIONNA2_GPU=3 python benchmark/lowfreq_anchor.py sphere     # → partial/sphere.json
    SIONNA2_GPU=2 python benchmark/lowfreq_anchor.py plate      # → partial/plate.json
    python benchmark/lowfreq_anchor.py mom                      # → partial/mom.json (CPU)
    python benchmark/lowfreq_anchor.py merge                    # → outputs/lowfreq_anchor.json

산출: outputs/lowfreq_anchor.json, outputs/figs/lowfreq_anchor.png (그림 라벨 영어)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
PART_DIR = os.path.join(_ROOT, "outputs", "partial", "lowfreq_anchor")
OUT_JSON = os.path.join(_ROOT, "outputs", "lowfreq_anchor.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figs", "lowfreq_anchor.png")

# ── 규약 (생산 커널과 맞춘다) ────────────────────────────────────────────────
JITTER = 3                 # 격자위상 평균 J²=9 오프셋 (생산 검증 규약, verify_sbr_kr_sweep 와 동일)
PEC = {"metal": 1.0}       # |Γ|=1

# ── ① 구 ────────────────────────────────────────────────────────────────────
SPH_R = 0.10                                   # 반경 고정 [m] — ka 는 **주파수**로만 쓴다
KA_LADDER = (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0)
#  광선격자: 상대(생산 규약) + **절대[mm] 사다리**. 절대격자는 ka 와 무관하게 같은 촘촘함이다.
SPH_REL_DIVS = (8, 12, 16)
SPH_ABS_MM = (8.0, 4.0, 2.0, 1.0, 0.5, 0.25)
#  ⚠ 0.125 mm 계단은 뺐다 — ka=1 에서 0.25 mm(=λ/2513)에 이미 |커널−해석PO| = 0.000 dB 라
#    더 조여도 배울 것이 없고, 공용 GPU 에서 Dr.Jit 이 메모리를 터뜨렸다(실측).
SPH_ABS_MM_LOWKA = ()
SPH_LOWKA_MAX = 1.0
#  Dr.Jit 한 번의 호출에 올릴 광선 수 상한 — 카드를 남과 나눠 쓰므로 스스로 조인다.
SPH_MAX_RAYS_PER_CALL = 4_000_000
#  메쉬는 **모든 ka 에서 과분할**로 고정한다 — 격자축과 메쉬축이 섞이지 않게.
SPH_SEG, SPH_RINGS = 720, 360                  # 면 변 ≈ 2πr/720 = 0.87 mm
#  입사방향: uv_sphere 는 극에 특이점이 있어 등방이 아니다 → el×az 격자로 평균한다.
#  ⚠ 24 vs 48 방향은 이미 수렴이 확인돼 있다(verify_sbr_kr_sweep 주석: 0.1952 vs 0.2006 dB).
SPH_EL = (0.0, 25.0, 50.0, 75.0)
SPH_AZ_N = 6                                   # → 24 방향
#  메쉬 사다리(부차축): 격자를 **넉넉히 고정**하고 메쉬만 바꾼다(격자축과 분리).
SPH_MESH_LADDER_KA = (1.0, 3.0)
SPH_MESH_SEGS = (48, 96, 192, 384, 720, 1440)
SPH_MESH_LADDER_D_MM = 0.5                     # 이미 수렴한 계단(위 사다리에서 확인됨)

# ── ② 얇은 판 ───────────────────────────────────────────────────────────────
PLATE_FC = 1.8e9                               # 드론 저대역 (λ=166.55 mm)
PLATE_A_LAM = (0.15, 0.30, 0.60, 1.00, 2.00)   # 시선면 폭 [λ] — 0.15λ 가 드론 대표
PLATE_B_LAM = 6.0                              # 시선수직 span [λ] — 2D↔3D 대응이 서도록 길게
PLATE_DIVS = (8, 12, 16, 32, 64, 128, 256, 512)  # λ 고정이므로 상대=절대. mm 로도 같이 적는다
PLATE_THETA_DEG = (0.0, 15.0, 30.0, 45.0)      # 부차: 각도평균이 결론을 바꾸는지
PLATE_THETA_DIVS = (12, 128)
MOM_SEG_PER_LAM = 400                          # MoM 세그먼트 밀도 (얇은 띠라 매우 조밀)
MOM_SEG_MIN, MOM_SEG_MAX = 60, 240


def _dbsm(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, float), 1e-300))


def _mkdir():
    os.makedirs(PART_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)


# =========================================================================== #
#  ① PEC 구
# =========================================================================== #
def run_sphere():
    from gpu import pick, gpu_status, oom_backoff
    pick()
    from geom import uv_sphere
    from rcs_sbr import rcs_sbr_batch
    from mie_pec_sphere import mie_pec_backscatter_norm, po_sphere_norm

    _mkdir()
    t_wall = time.perf_counter()
    r = SPH_R
    pi_r2 = np.pi * r ** 2
    az_all = np.linspace(0.0, 360.0, SPH_AZ_N, endpoint=False)
    n_inc = len(SPH_EL) * SPH_AZ_N

    print(f"[sphere] r={r} m 고정, ka 를 주파수로만 쓴다. 메쉬 seg={SPH_SEG} rings={SPH_RINGS} "
          f"(면 변 ≈ {2*np.pi*r/SPH_SEG*1000:.3f} mm), 입사 {n_inc} 방향, jitter={JITTER}")
    sph = uv_sphere(r, seg=SPH_SEG, rings=SPH_RINGS, group="metal")
    print(f"[sphere] 삼각형 {len(sph.f):,} 개")

    def _sigma(mesh, fc, d, key):
        """입사 24 방향 σ 의 선형평균.

        ⚠ chunk_az 를 **직접 정한다** — `rcs_sbr_batch` 의 자동 산정(160 B/광선)은 Dr.Jit 의
          실제 사용량을 과소평가해서, 카드를 다른 작업과 나눠 쓸 때 터진다(실측: 0.125 mm
          계단에서 jit_flush_malloc_cache 뒤 Vector3f 생성 실패)."""
        Rout = float(np.linalg.norm(np.asarray(mesh.v, float)
                                    - 0.5 * (np.asarray(mesh.v, float).max(0)
                                             + np.asarray(mesh.v, float).min(0)),
                                    axis=1).max()) * 1.15 + 3 * d
        rays_per_az = int(np.ceil(2 * Rout / d)) ** 2
        ch = int(max(1, min(len(az_all), SPH_MAX_RAYS_PER_CALL // max(1, rays_per_az))))
        acc = []
        for el in SPH_EL:
            v = oom_backoff(lambda batch: rcs_sbr_batch(
                mesh, PEC, fc, az_deg=az_all, el_deg=float(el), spacing=float(d),
                jitter=JITTER, penetrate=False, cache_key=key, chunk_az=batch), batch=ch)
            acc.append(np.atleast_1d(np.asarray(v, float)))
        s = np.concatenate(acc)
        return float(s.mean()), float(s.std()), s

    rows = []
    for ka in KA_LADDER:
        lam = 2.0 * np.pi * r / ka
        fc = C0 / lam
        s_po = float(po_sphere_norm(ka)) * pi_r2
        s_mie = float(mie_pec_backscatter_norm(ka)) * pi_r2
        ds = [("rel", lam / div, div) for div in SPH_REL_DIVS]
        abs_mm = SPH_ABS_MM + (SPH_ABS_MM_LOWKA if ka <= SPH_LOWKA_MAX else ())
        ds += [("abs", mm * 1e-3, mm) for mm in abs_mm]
        print(f"\n[sphere] ka={ka:5.2f}  f={fc/1e9:7.4f} GHz  λ={lam*1000:8.2f} mm   "
              f"PO {_dbsm(s_po):+7.3f} · Mie {_dbsm(s_mie):+7.3f} dBsm "
              f"(PO−Mie {_dbsm(s_po)-_dbsm(s_mie):+6.3f} dB)")
        print(f"    {'kind':>4} {'d[mm]':>9} {'d/λ':>9} {'rays/az':>10} "
              f"{'σ[dBsm]':>9} {'−PO[dB]':>9} {'−Mie[dB]':>9} {'t[s]':>6}")
        for kind, d, tag in ds:
            t0 = time.perf_counter()
            mu, sd, _ = _sigma(sph, fc, d, key=("lfa_sph", SPH_SEG))
            dt = time.perf_counter() - t0
            n_ray = int(np.ceil(2 * (r * 1.15 + 3 * d) / d)) ** 2
            row = dict(ka=ka, fc_hz=float(fc), lam_m=float(lam), kind=kind, d_m=float(d),
                       d_mm=float(d * 1e3), d_over_lam=float(d / lam), lam_over_d=float(lam / d),
                       rays_per_az=n_ray, sigma_m2=mu, sigma_dbsm=float(_dbsm(mu)),
                       inc_std_lin=sd, po_sigma_m2=s_po, mie_sigma_m2=s_mie,
                       vs_po_db=float(_dbsm(mu) - _dbsm(s_po)),
                       vs_mie_db=float(_dbsm(mu) - _dbsm(s_mie)),
                       po_minus_mie_db=float(_dbsm(s_po) - _dbsm(s_mie)),
                       n_inc=n_inc, runtime_s=float(dt))
            rows.append(row)
            print(f"    {kind:>4} {d*1e3:9.3f} {d/lam:9.5f} {n_ray:10,d} "
                  f"{row['sigma_dbsm']:+9.3f} {row['vs_po_db']:+9.3f} {row['vs_mie_db']:+9.3f} "
                  f"{dt:6.1f}", flush=True)

    # ── 메쉬 사다리 (부차축): 격자를 최고로 고정하고 메쉬만 바꾼다 ──
    mesh_rows = []
    print("\n[sphere] 메쉬 사다리 — 격자를 최고(절대 최소 d)로 고정하고 **메쉬만** 바꾼다")
    for ka in SPH_MESH_LADDER_KA:
        lam = 2.0 * np.pi * r / ka
        fc = C0 / lam
        d = SPH_MESH_LADDER_D_MM * 1e-3
        s_po = float(po_sphere_norm(ka)) * pi_r2
        s_mie = float(mie_pec_backscatter_norm(ka)) * pi_r2
        for seg in SPH_MESH_SEGS:
            m = uv_sphere(r, seg=seg, rings=max(6, seg // 2), group="metal")
            t0 = time.perf_counter()
            mu, sd, _ = _sigma(m, fc, d, key=("lfa_sph_mesh", seg))
            mesh_rows.append(dict(ka=ka, seg=seg, n_tri=int(len(m.f)),
                                  facet_mm=float(2 * np.pi * r / seg * 1e3),
                                  facet_over_lam=float(2 * np.pi * r / seg / lam),
                                  d_mm=float(d * 1e3), sigma_dbsm=float(_dbsm(mu)),
                                  vs_po_db=float(_dbsm(mu) - _dbsm(s_po)),
                                  vs_mie_db=float(_dbsm(mu) - _dbsm(s_mie)),
                                  runtime_s=float(time.perf_counter() - t0)))
            rr = mesh_rows[-1]
            print(f"    ka={ka:4.1f} seg={seg:5d} 면{rr['facet_mm']:7.3f}mm "
                  f"(λ/{1/max(rr['facet_over_lam'],1e-12):8.1f})  σ {rr['sigma_dbsm']:+8.3f}  "
                  f"−PO {rr['vs_po_db']:+7.3f}  −Mie {rr['vs_mie_db']:+7.3f}", flush=True)

    out = dict(part="sphere", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               radius_m=r, ka_ladder=list(KA_LADDER), jitter=JITTER,
               mesh=dict(seg=SPH_SEG, rings=SPH_RINGS, n_tri=int(len(sph.f)),
                         facet_mm=float(2 * np.pi * r / SPH_SEG * 1e3)),
               incidence=dict(el_deg=list(SPH_EL), n_az=SPH_AZ_N, n_total=n_inc,
                              stat="μ = 10log10(mean_inc σ_lin)"),
               rows=rows, mesh_ladder=mesh_rows,
               gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
               gpu_status=gpu_status(), runtime_s=float(time.perf_counter() - t_wall))
    p = os.path.join(PART_DIR, "sphere.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[sphere] → {p}  ({out['runtime_s']:.0f} s)")


# =========================================================================== #
#  ② 얇은 판
# =========================================================================== #
def _rect_plate(a, b):
    """z=0 평면 위 a(x) × b(y) 인 **두께 0** PEC 판 (사각형 → 삼각형 2 장).

    두께를 주면 옆면이 저주파에서 기여를 섞는다 — 참조해(PO 닫힌형·2D MoM)는 둘 다
    두께 0 이므로 판도 두께 0 으로 둔다."""
    from geom import quad
    return quad((-a / 2, -b / 2, 0.0), (a / 2, -b / 2, 0.0),
                (a / 2, b / 2, 0.0), (-a / 2, b / 2, 0.0), group="metal")


def run_plate():
    from gpu import pick, gpu_status
    pick()
    from rcs_sbr import rcs_sbr_batch

    _mkdir()
    t_wall = time.perf_counter()
    lam = C0 / PLATE_FC
    b = PLATE_B_LAM * lam
    print(f"[plate] f={PLATE_FC/1e9:.2f} GHz  λ={lam*1000:.3f} mm  b={PLATE_B_LAM}λ={b*1000:.1f} mm, "
          f"jitter={JITTER}")

    rows = []
    for al in PLATE_A_LAM:
        a = al * lam
        A = a * b
        s_po = 4.0 * np.pi * A ** 2 / lam ** 2       # 정면입사 PO **정확해**(근사 아님)
        print(f"\n[plate] a={al:5.2f}λ = {a*1000:7.2f} mm   PO 닫힌형 4πA²/λ² = {_dbsm(s_po):+8.3f} dBsm")
        print(f"    {'d[mm]':>9} {'λ/d':>6} {'a/d':>7} {'rays/az':>11} {'σ[dBsm]':>10} "
              f"{'−PO[dB]':>9} {'t[s]':>6}")
        pl = _rect_plate(a, b)
        for div in PLATE_DIVS:
            d = lam / div
            t0 = time.perf_counter()
            #  판은 xy 평면에 있다 → el=90° 가 정면입사
            s = float(rcs_sbr_batch(pl, PEC, PLATE_FC, az_deg=0.0, el_deg=90.0, spacing=d,
                                    jitter=JITTER, penetrate=False, cache_key=("lfa_pl", al)))
            dt = time.perf_counter() - t0
            Rout = float(np.linalg.norm([a / 2, b / 2, 0.0])) * 1.15 + 3 * d
            n_ray = int(np.ceil(2 * Rout / d)) ** 2
            row = dict(a_lam=al, a_m=float(a), b_m=float(b), div=div, d_m=float(d),
                       d_mm=float(d * 1e3), samples_across_width=float(a / d),
                       rays_per_az=n_ray, sigma_m2=s, sigma_dbsm=float(_dbsm(s)),
                       po_closed_m2=float(s_po), po_closed_dbsm=float(_dbsm(s_po)),
                       vs_po_db=float(_dbsm(s) - _dbsm(s_po)), runtime_s=float(dt))
            rows.append(row)
            print(f"    {d*1e3:9.4f} {div:6d} {a/d:7.2f} {n_ray:11,d} {row['sigma_dbsm']:+10.3f} "
                  f"{row['vs_po_db']:+9.3f} {dt:6.1f}", flush=True)

    # ── 부차: 각도평균이 결론을 바꾸는가 (드론은 방위 360 평균이었다) ──
    obl = []
    print("\n[plate] 경사입사 — 각도평균이 격자민감도를 바꾸는지 (PO 닫힌형: A·cosθ·sinc(ka sinθ))")
    for al in PLATE_A_LAM:
        a = al * lam
        pl = _rect_plate(a, b)
        for div in PLATE_THETA_DIVS:
            d = lam / div
            for th in PLATE_THETA_DEG:
                k = 2 * np.pi / lam
                X = k * a * np.sin(np.radians(th))
                W = a * np.cos(np.radians(th)) * np.sinc(X / np.pi)
                s_po = 4.0 * np.pi * (W * b) ** 2 / lam ** 2
                s = float(rcs_sbr_batch(pl, PEC, PLATE_FC, az_deg=0.0,
                                        el_deg=90.0 - th, spacing=d, jitter=JITTER,
                                        penetrate=False, cache_key=("lfa_pl", al)))
                obl.append(dict(a_lam=al, div=div, theta_deg=th, sigma_dbsm=float(_dbsm(s)),
                                po_closed_dbsm=float(_dbsm(s_po)),
                                vs_po_db=float(_dbsm(s) - _dbsm(s_po))))
        rr = [o for o in obl if o["a_lam"] == al]
        print(f"    a={al:5.2f}λ  λ/12 평균|−PO| {np.mean([abs(o['vs_po_db']) for o in rr if o['div']==PLATE_THETA_DIVS[0]]):6.3f} dB "
              f"→ λ/{PLATE_THETA_DIVS[-1]} {np.mean([abs(o['vs_po_db']) for o in rr if o['div']==PLATE_THETA_DIVS[-1]]):6.3f} dB", flush=True)

    out = dict(part="plate", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               fc_hz=PLATE_FC, lam_m=float(lam), b_lam=PLATE_B_LAM, b_m=float(b),
               a_lam_list=list(PLATE_A_LAM), divs=list(PLATE_DIVS), jitter=JITTER,
               rows=rows, oblique=obl,
               gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
               gpu_status=gpu_status(), runtime_s=float(time.perf_counter() - t_wall))
    p = os.path.join(PART_DIR, "plate.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[plate] → {p}  ({out['runtime_s']:.0f} s)")


# =========================================================================== #
#  ②-참값: 2D MoM (CPU)
# =========================================================================== #
def run_mom():
    """얇은 띠의 **물리 참값** — 2D EFIE MoM(근사 없음), TM·TE 양편파.

    3D 대응: σ_3D = (2b²/λ)·σ_2D,  σ_2D = k|W|².  PO 항과 on-cone 모서리에 대해 정확하다."""
    import mom2d_reference as mom
    _mkdir()
    lam = C0 / PLATE_FC
    k = 2.0 * np.pi / lam
    b = PLATE_B_LAM * lam
    conv = 2.0 * b ** 2 / lam
    u = np.array([0.0, 1.0])            # θ=0 (정면)
    e_r = np.array([-1.0, 0.0])
    rows = []
    print(f"[mom] 2D EFIE MoM 참값 — λ={lam*1000:.3f} mm, σ_3D = (2b²/λ)σ_2D, b={PLATE_B_LAM}λ")
    print(f"    {'a/λ':>6} {'M':>5} {'σ2D_PO':>10} {'σ2D_TM':>10} {'σ2D_TE':>10} "
          f"{'PO−TM[dB]':>10} {'PO−TE[dB]':>10} {'t[s]':>6}")
    for al in PLATE_A_LAM:
        a = al * lam
        s2_po = k * a ** 2                          # θ=0 → W_PO = a
        for M in (int(np.clip(round(MOM_SEG_PER_LAM * al), MOM_SEG_MIN, MOM_SEG_MAX)),
                  int(np.clip(round(2 * MOM_SEG_PER_LAM * al), MOM_SEG_MIN, MOM_SEG_MAX))):
            t0 = time.perf_counter()
            nd = mom.strip_nodes(a, M)
            W_tm = (mom.Z0 / 2) * mom.solve_tm(mom.assemble_tm(nd, k), u)[0]
            W_te = (mom.Z0 / 2) * mom.solve_te(mom.assemble_te(nd, k, closed=False), u, e_r)[0]
            s2_tm, s2_te = k * abs(W_tm) ** 2, k * abs(W_te) ** 2
            rows.append(dict(a_lam=al, a_m=float(a), n_seg=M, seg_per_lam=float(M / al),
                             sigma2d_po=float(s2_po), sigma2d_tm=float(s2_tm),
                             sigma2d_te=float(s2_te),
                             sigma3d_po_dbsm=float(_dbsm(conv * s2_po)),
                             sigma3d_tm_dbsm=float(_dbsm(conv * s2_tm)),
                             sigma3d_te_dbsm=float(_dbsm(conv * s2_te)),
                             po_minus_tm_db=float(_dbsm(s2_po) - _dbsm(s2_tm)),
                             po_minus_te_db=float(_dbsm(s2_po) - _dbsm(s2_te)),
                             runtime_s=float(time.perf_counter() - t0)))
            r = rows[-1]
            print(f"    {al:6.2f} {M:5d} {s2_po:10.5f} {s2_tm:10.5f} {s2_te:10.5f} "
                  f"{r['po_minus_tm_db']:+10.3f} {r['po_minus_te_db']:+10.3f} "
                  f"{r['runtime_s']:6.1f}", flush=True)
    # 자기검증: 원형 실린더 정확해 대조
    st = mom.selftest(verbose=False)
    out = dict(part="mom", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
               fc_hz=PLATE_FC, lam_m=float(lam), b_lam=PLATE_B_LAM,
               conv_2d_to_3d=float(conv), rows=rows,
               selftest=dict(worst_abs_db_at_240seg=st["worst_abs_db_at_240seg"],
                             passes=bool(st["passes"]),
                             reference=st["reference"]))
    p = os.path.join(PART_DIR, "mom.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n[mom] → {p}   자기검증(원형 실린더 정확해) 최악 {st['worst_abs_db_at_240seg']:.4f} dB "
          f"{'PASS' if st['passes'] else 'FAIL'}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "sphere":
        run_sphere()
    elif mode == "plate":
        run_plate()
    elif mode == "mom":
        run_mom()
    elif mode == "merge":
        from lowfreq_anchor_merge import merge
        merge()
    else:
        raise SystemExit("사용법: lowfreq_anchor.py [sphere|plate|mom|merge]")
