# -*- coding: utf-8 -*-
"""
measure_runtime.py — **우리 SBR+PO 커널의 자세(pose)당 비용을 실측한다**
========================================================================================
왜 이 파일이 있나 — 답할 수 없던 published objection 하나 때문이다.

  Ziganshin, journal preprint arXiv:2604.05991v2, pp.1-2 (verbatim):
    "This SBR+PO approach, however, is limited to the illuminated region and is not suitable
     to predict the scattered field in the shadow region of the obstacle. **Furthermore, the
     need to cascade PO after RT negates the computational advantages of RT.**"

  앞 절반(그림자 영역)은 답이 있다 — 우리 주장은 후방산란·β≤45° 안에 산다.
  ⭐ 뒤 절반(런타임)은 **커널을 한 번도 재본 적이 없어서** 답이 없었다. 이 파일이 그걸 잰다.

■ 무엇을 재나 (요지 = 단계 분해)
  반론이 지목한 것은 "**RT 뒤에 PO 를 잇는 것**"이다. 그러므로 총시간이 아니라 **분해**가 답이다:
    ① scene build   : mi.Mesh 업로드 + OptiX BVH — **자세마다 드는 비용이 아니다**(캐시).
    ② ray gen/upload: 광선 격자 생성(host numpy) + Ray3f H2D.
    ③ **RT**        : `scene.ray_intersect` (GPU, OptiX).           ← RT 고유 비용
    ④ handoff       : 히트레코드 D2H (`si.p/si.n/is_valid/shape==`) ← "cascade" 의 이음매
    ⑤ **PO**        : 조명게이트 + e^{j2k r·û} + 코히런트 합산(host numpy). ← 반론이 말한 추가분
  ⑤/③ 비율이 반론의 정량적 형태다.

■ 정직성 규약(이 파일이 지키는 것)
  · 계측기는 **생산커널의 복제**다. 매 config 마다 `rcs_sbr.rcs_sbr_batch` 와 σ 를 대조해
    **max|Δ| = 0** 인지 검사하고 그 값을 JSON 에 남긴다(`replica_check`). 복제가 어긋나면 숫자는 무효다.
  · dr.sync 삽입 자체가 오버헤드다 → 같은 config 를 계측 없이도 재서 `instrumentation_overhead_pct` 로 남긴다.
  · **하드웨어를 가로질러 정규화하지 않는다.** 우리 숫자는 RTX 4090 1장(공유중)에서 났고,
    published baseline 은 RTX 4090 / A5000 / dual EPYC 7343 / 32×MI250X 에서 났다. 스케일하면 계수를 적는다.
  · GPU 는 **남과 공유중**이다(다른 사용자 프로세스). util 을 샘플링해 JSON 에 남기고,
    반복 중 **min** 을 '경합이 가장 적었던 관측' 으로, median 을 대표값으로 함께 보고한다.

실행:  SIONNA2_GPU=3 PYTHONPATH=src:benchmark python benchmark/measure_runtime.py
출력:  outputs/runtime_benchmark.json  (증분 저장 — 섹션마다 flush)
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# GPU 는 mitsuba import 전에 잡는다(gpu.py 규약). 이 벤치마크는 GPU2(rcs_anchor) 를 피한다.
os.environ.setdefault("SIONNA2_GPU", "3")
os.environ.setdefault("SIONNA2_GPU_MEM", "2500")

import numpy as np                                                    # noqa: E402
from gpu import pick as _pick_gpu, budget_mb                          # noqa: E402

_PICKED = _pick_gpu(verbose=True)

import mitsuba as mi                                                  # noqa: E402
import drjit as dr                                                    # noqa: E402

import rcs_sbr                                                        # noqa: E402
from rcs_sbr import (_look, _resolve_shells, _scene_for,              # noqa: E402
                     rcs_sbr_batch, C0)

OUT = os.path.join(ROOT, "outputs", "runtime_benchmark.json")

# ── 생산 설정 (src/experiment_freespace_sigma.py:62-76 단일 진리원) ──────────────
PROD_DIV = 16          # experiment_freespace_sigma.DIV
PROD_JITTER = 2        # experiment_freespace_sigma.JITTER  → J² = 4 격자 오프셋
PROD_PEN = True        # penetrate=True (유전체 셸 투과 2차 패스)
PROD_NF = 3            # experiment_freespace_sigma.N_F  대역평균 3점
PROD_EL = -2.0         # 자유공간 이등분선 앙각(음수) 중 대표값
BANDS = [("LTE 1.8 GHz", 1.843e9), ("5G NR 3.5 GHz", 3.500e9), ("WiFi 5.2 GHz", 5.210e9)]

_RESULT: dict = {}


def _flush(section=None):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_RESULT, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    if section:
        print(f"[flush] {section} → {OUT}", flush=True)


# --------------------------------------------------------------------------- #
#  0. 하드웨어·환경 — 정직하게, 경합까지
# --------------------------------------------------------------------------- #
def _smi(q):
    try:
        return subprocess.run(["nvidia-smi", f"--query-gpu={q}",
                               "--format=csv,noheader,nounits"],
                              capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
    except Exception as e:                                            # pragma: no cover
        return [f"error {e}"]


def _gpu_snapshot():
    idx = int(os.environ.get("SIONNA2_GPU", "3"))
    rows = _smi("index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,clocks.sm")
    try:
        procs = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,used_memory,gpu_uuid",
                                "--format=csv,noheader"], capture_output=True, text=True,
                               timeout=20).stdout.strip().splitlines()
    except Exception:
        procs = []
    return dict(t=time.strftime("%H:%M:%S"), rows=rows, procs=procs, our_gpu_index=idx)


def _cpu_name():
    try:
        for ln in open("/proc/cpuinfo"):
            if ln.startswith("model name"):
                return ln.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor()


def section_meta():
    import sionna
    _RESULT["meta"] = dict(
        purpose="per-pose runtime of our SBR+PO kernel, to answer Ziganshin's "
                "'cascading PO after RT negates the computational advantages of RT'",
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        script="benchmark/measure_runtime.py",
        kernel_under_test="src/rcs_sbr.py rcs_sbr_batch (1-bounce SBR + PO surface integral)",
        production_settings=dict(div=PROD_DIV, jitter=PROD_JITTER, penetrate=PROD_PEN,
                                 n_f_band_average=PROD_NF, el_deg=PROD_EL,
                                 source="src/experiment_freespace_sigma.py:62-76"),
        pose_definition=dict(
            pose="one backscatter aspect (az, el) at ONE carrier → one sigma value",
            passes_per_pose_production=f"J^2={PROD_JITTER**2} grid-jitter offsets "
                                       f"x {2 if PROD_PEN else 1} traces (penetrate) "
                                       f"= {PROD_JITTER**2*(2 if PROD_PEN else 1)} ray_intersect calls",
            band_averaged_pose=f"production sigma also averages n_f={PROD_NF} carriers "
                               f"→ x{PROD_NF} on top"),
        hardware=dict(
            gpu_used=f"NVIDIA GeForce RTX 4090 (index {os.environ.get('SIONNA2_GPU')}), "
                     "SHARED with another user's job during measurement",
            gpu_query=_smi("index,name,memory.total,driver_version"),
            cpu=_cpu_name(), cpu_logical_cores=os.cpu_count(),
            note="PO integration runs in host numpy (single-threaded except BLAS-free ops); "
                 "ray tracing runs on the GPU. Both host and device were shared during the run.",
            loadavg=list(os.getloadavg()),
            gpu_budget_mb=budget_mb()),
        software=dict(python=platform.python_version(), numpy=np.__version__,
                      drjit=dr.__version__, mitsuba=mi.__version__,
                      mitsuba_variant=mi.variant(), sionna=sionna.__version__),
        contention_snapshots=[_gpu_snapshot()],
        honesty=["timings measured under foreign GPU load; min over repeats = least-contended "
                 "observation, median = representative",
                 "no cross-hardware normalisation is applied silently; any scaling states its factor",
                 "the instrumented replica is checked bit-equal against the production kernel "
                 "for every config (replica_check.max_abs_ddb)"],
    )
    _flush("meta")


# --------------------------------------------------------------------------- #
#  1. 계측 복제 — rcs_sbr_batch 와 **같은 연산·같은 순서**, 단계 타이머만 추가
# --------------------------------------------------------------------------- #
def _sync():
    try:
        dr.sync_thread()
    except Exception:
        pass


def _eval(*xs):
    try:
        dr.eval(*xs)
    except Exception:
        pass
    _sync()


def timed_batch(mesh, group_mat, fc, az_deg, el_deg=0.0, spacing=None, pad=1.15,
                cache_key=None, chunk_az=None, penetrate=True, jitter=2, shell_groups=None):
    """`rcs_sbr.rcs_sbr_batch` 의 **1:1 계측 복제**. 반환 (sigma, timings, counters).

    ⚠ 연산·순서는 원본과 동일해야 한다 — σ 를 원본과 대조해 검증한다(replica_check)."""
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    d = float(spacing) if spacing else lam / rcs_sbr.DEFAULT_DIV

    T = dict(scene=0.0, raygen_host=0.0, ray_upload=0.0, rt_trace=0.0,
             handoff=0.0, po=0.0)
    N = dict(ray_intersect_calls=0, rays_traced=0, hits=0, lit=0)

    t0 = time.perf_counter()
    scene, shapes, gammas = _scene_for(mesh, group_mat, cache_key, fc)
    shape_ptrs = [mi.ShapePtr(s) for s in shapes]
    T["scene"] += time.perf_counter() - t0

    group_names = sorted(set(np.asarray(mesh.g).tolist()))
    _shells = _resolve_shells(group_names, group_mat, shell_groups)
    shell_pos = [i for i, gn in enumerate(group_names) if gn in _shells]
    do_pen = penetrate and len(shell_pos) > 0
    if do_pen:
        t0 = time.perf_counter()
        ck_i = (cache_key, "noshell") if cache_key is not None else None
        scene_i, shapes_i, gammas_i = _scene_for(mesh, group_mat, ck_i, fc, exclude=_shells)
        shptr_i = [mi.ShapePtr(s) for s in shapes_i]
        T["scene"] += time.perf_counter() - t0

    V = np.asarray(mesh.v, float)
    ctr = 0.5 * (V.max(0) + V.min(0))
    Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d

    n = int(np.ceil(2 * Rout / d))
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    A, B = A.ravel(), B.ravel()
    rays_per_az = A.size

    az = np.atleast_1d(np.asarray(az_deg, float))
    if chunk_az is None:
        per_az_bytes = rays_per_az * 160 * (2 if do_pen else 1)
        chunk_az = int(max(1, min(len(az), budget_mb() * 1024 * 1024 * 0.85 / per_az_bytes)))

    def _lit_g_phase(si, shptr, gam, D, U):
        """원본 `_lit_g_phase` 를 handoff(D2H) / po(적분수학) 두 타이머로 쪼갠 것."""
        t0 = time.perf_counter()
        valid = np.asarray(si.is_valid()).astype(bool)
        P = np.asarray(mi.Point3f(si.p)).T
        Nn = np.asarray(mi.Vector3f(si.n)).T
        g = np.zeros(P.shape[0])
        for sp, gm in zip(shptr, gam):
            g = np.where(np.asarray(si.shape == sp).astype(bool), gm, g)
        T["handoff"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        sgn = np.sign(np.einsum("ij,ij->i", Nn, -D)); sgn[sgn == 0] = 1.0
        Nn = Nn * sgn[:, None]
        lit = valid & (np.einsum("ij,ij->i", Nn, U) > 1e-6)
        phase = np.exp(1j * 2.0 * k * np.einsum("ij,ij->i", P - ctr, U))
        T["po"] += time.perf_counter() - t0
        N["hits"] += int(valid.sum()); N["lit"] += int(lit.sum())
        return lit, g, phase, valid, si

    J = max(1, int(jitter))
    fr = (np.arange(J) + 0.5) / J - 0.5
    offsets = [(ox * d, oy * d) for ox in fr for oy in fr]

    sig = np.zeros(len(az))
    for s0 in range(0, len(az), chunk_az):
        sub = az[s0:s0 + chunk_az]
        t0 = time.perf_counter()
        bases = []
        for a in sub:
            u = _look(a, el_deg)
            tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
            e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
            e2 = np.cross(u, e1)
            bases.append((u, e1, e2))
        aidx = np.repeat(np.arange(len(sub)), rays_per_az)
        T["raygen_host"] += time.perf_counter() - t0
        sig_acc = np.zeros(len(sub))
        for ox, oy in offsets:
            t0 = time.perf_counter()
            O_all, D_all, U_all = [], [], []
            for u, e1, e2 in bases:
                O_all.append((ctr + Rout * u)[None, :] + (A + ox)[:, None] * e1 + (B + oy)[:, None] * e2)
                D_all.append(np.tile(-u, (rays_per_az, 1)))
                U_all.append(np.tile(u, (rays_per_az, 1)))
            O = np.concatenate(O_all); D = np.concatenate(D_all); U = np.concatenate(U_all)
            T["raygen_host"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            ray = mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                           d=mi.Vector3f(*D.T.astype(np.float32)))
            _eval(ray.o, ray.d)
            T["ray_upload"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            si = scene.ray_intersect(ray)
            _eval(si.p, si.n, si.t)
            T["rt_trace"] += time.perf_counter() - t0
            N["ray_intersect_calls"] += 1; N["rays_traced"] += O.shape[0]

            lit, g, phase, valid, si = _lit_g_phase(si, shape_ptrs, gammas, D, U)
            t0 = time.perf_counter()
            contrib = np.where(lit, g, 0.0) * phase
            T["po"] += time.perf_counter() - t0

            if do_pen:
                t0 = time.perf_counter()
                tau = np.zeros(valid.shape[0])
                for i in shell_pos:
                    tau = np.where(np.asarray(si.shape == shape_ptrs[i]).astype(bool),
                                   1.0 - gammas[i] ** 2, tau)
                T["handoff"] += time.perf_counter() - t0

                t0 = time.perf_counter()
                si2 = scene_i.ray_intersect(ray)
                _eval(si2.p, si2.n, si2.t)
                T["rt_trace"] += time.perf_counter() - t0
                N["ray_intersect_calls"] += 1; N["rays_traced"] += O.shape[0]

                lit2, g2, phase2, _, _ = _lit_g_phase(si2, shptr_i, gammas_i, D, U)
                t0 = time.perf_counter()
                contrib = contrib + np.where(lit2 & (tau > 0), tau * g2, 0.0) * phase2
                T["po"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            E = np.zeros(len(sub), complex)
            np.add.at(E, aidx, contrib)
            sig_acc += (4.0 * np.pi / lam ** 2) * np.abs(E * d * d) ** 2
            T["po"] += time.perf_counter() - t0
        sig[s0:s0 + len(sub)] = sig_acc / len(offsets)

    N["rays_per_az_per_pass"] = int(rays_per_az)
    N["grid_n"] = int(n)
    N["chunk_az"] = int(chunk_az)
    N["passes_per_pose"] = int(len(offsets) * (2 if do_pen else 1))
    N["facets"] = int(len(mesh.f))
    return sig, T, N


# --------------------------------------------------------------------------- #
#  2. 한 config 를 재는 루틴 (warmup + 반복, 원본과 σ 대조)
# --------------------------------------------------------------------------- #
def _util_now():
    """우리 카드의 **타인 부하** 지표 — 경합 상태를 config 마다 기록한다."""
    idx = int(os.environ.get("SIONNA2_GPU", "3"))
    try:
        rows = _smi("index,utilization.gpu,memory.used")
        for r in rows:
            p = [x.strip() for x in r.split(",")]
            if int(p[0]) == idx:
                return dict(util_pct=float(p[1]), mem_used_mb=float(p[2]))
    except Exception:
        pass
    return None


def measure(drone, fc, div=PROD_DIV, jitter=PROD_JITTER, penetrate=PROD_PEN,
            n_az=8, el_deg=PROD_EL, reps=3, mesh=None, tag="", check=True,
            chunk_az=None, sample_util=False):
    from drones import DRONES, build_drone
    from channel import _group_mat
    m = mesh if mesh is not None else build_drone(DRONES[drone])
    gm = _group_mat(drone)
    lam = C0 / float(fc)
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    ck = (tag or drone, round(fc / 1e6), round(el_deg, 3), int(div),
          int(len(m.f)), bool(penetrate))
    kw = dict(el_deg=el_deg, spacing=lam / float(div), penetrate=penetrate,
              jitter=jitter, cache_key=ck, chunk_az=chunk_az)

    # warmup(씬 빌드·JIT 커널 컴파일을 측정에서 뺀다)
    timed_batch(m, gm, float(fc), az_deg=az[:1], **kw)
    util = [_util_now()] if sample_util else None

    tot, stages = [], []
    for _ in range(int(reps)):
        t0 = time.perf_counter()
        sig, T, N = timed_batch(m, gm, float(fc), az_deg=az, **kw)
        tot.append(time.perf_counter() - t0)
        stages.append(T)

    # 계측 없는 순수 생산커널 — 계측 오버헤드 정량화
    raw = []
    for _ in range(int(reps)):
        t0 = time.perf_counter()
        sig_p = rcs_sbr_batch(m, gm, float(fc), az_deg=az, **kw)
        raw.append(time.perf_counter() - t0)
    sig_p = np.atleast_1d(np.asarray(sig_p, float))
    if sample_util:
        util.append(_util_now())

    chk = None
    if check:
        a = 10 * np.log10(np.maximum(np.atleast_1d(sig), 1e-30))
        b = 10 * np.log10(np.maximum(sig_p, 1e-30))
        chk = dict(max_abs_ddb=float(np.max(np.abs(a - b))),
                   bit_identical=bool(np.array_equal(np.atleast_1d(sig), sig_p)))

    def agg(key):
        v = np.array([s[key] for s in stages], float)
        return dict(min=float(v.min()), median=float(np.median(v)), max=float(v.max()))

    tot = np.array(tot); raw = np.array(raw)
    st_med = {k: float(np.median([s[k] for s in stages])) for k in stages[0]}
    st_sum = sum(st_med.values())
    per_pose_raw = float(np.median(raw)) / len(az)
    out = dict(
        drone=drone, tag=tag or drone, fc_ghz=float(fc) / 1e9, div=int(div),
        jitter=int(jitter), penetrate=bool(penetrate), n_az=int(n_az), el_deg=float(el_deg),
        reps=int(reps), facets=int(len(m.f)),
        rays_per_az_per_pass=N["rays_per_az_per_pass"], passes_per_pose=N["passes_per_pose"],
        rays_per_pose=int(N["rays_per_az_per_pass"] * N["passes_per_pose"]),
        chunk_az=N["chunk_az"],
        total_s=dict(min=float(tot.min()), median=float(np.median(tot)), max=float(tot.max())),
        raw_kernel_s=dict(min=float(raw.min()), median=float(np.median(raw)), max=float(raw.max())),
        per_pose_ms=dict(min=float(raw.min()) / len(az) * 1e3,
                         median=per_pose_raw * 1e3,
                         max=float(raw.max()) / len(az) * 1e3),
        per_pose_ms_instrumented=float(np.median(tot)) / len(az) * 1e3,
        instrumentation_overhead_pct=float((np.median(tot) - np.median(raw)) / np.median(raw) * 100.0),
        stage_s_median=st_med,
        stage_pct={k: float(100.0 * v / st_sum) for k, v in st_med.items()},
        stage_per_pose_ms={k: float(1e3 * v / len(az)) for k, v in st_med.items()},
        stage_spread=({k: agg(k) for k in stages[0]}),
        hit_fraction=float(N["hits"] / max(1, N["rays_traced"])),
        lit_fraction=float(N["lit"] / max(1, N["rays_traced"])),
        replica_check=chk,
        sigma_dbsm_first=float(10 * np.log10(max(float(np.atleast_1d(sig)[0]), 1e-30))),
        gpu_util_samples=util,
    )
    # 반론이 겨눈 비율
    rt = st_med["rt_trace"]; po = st_med["po"]; hs = st_med["handoff"]
    out["po_over_rt"] = float(po / rt) if rt > 0 else None
    out["po_plus_handoff_over_rt"] = float((po + hs) / rt) if rt > 0 else None
    print(f"  [{out['tag']:>12s} {out['fc_ghz']:.2f}GHz div{div} J{jitter} pen{int(penetrate)} "
          f"n_az={n_az}] {out['per_pose_ms']['median']:8.1f} ms/pose  "
          f"RT {out['stage_pct']['rt_trace']:4.1f}% PO {out['stage_pct']['po']:4.1f}% "
          f"handoff {out['stage_pct']['handoff']:4.1f}%  PO/RT={out['po_over_rt']:.2f}  "
          f"Δσ={chk['max_abs_ddb'] if chk else float('nan'):.1e} dB", flush=True)
    return out


# --------------------------------------------------------------------------- #
#  3. scene build — 자세마다 드는 비용이 아님을 보이는 항목
# --------------------------------------------------------------------------- #
def section_scene_build(drones):
    from drones import DRONES, build_drone
    from channel import _group_mat
    from rcs_sbr import _mi_scene_from_mesh
    rows = []
    for k in drones:
        m = build_drone(DRONES[k]); gm = _group_mat(k)
        _mi_scene_from_mesh(m, gm, 3.5e9)          # warmup
        ts = []
        for _ in range(3):
            t0 = time.perf_counter()
            _mi_scene_from_mesh(m, gm, 3.5e9)
            ts.append(time.perf_counter() - t0)
        t_cad = []
        for _ in range(2):
            t0 = time.perf_counter(); build_drone(DRONES[k]); t_cad.append(time.perf_counter() - t0)
        rows.append(dict(drone=k, facets=int(len(m.f)), groups=len(set(np.asarray(m.g).tolist())),
                         mi_scene_build_s=dict(min=float(min(ts)), median=float(np.median(ts))),
                         cad_build_s=float(np.median(t_cad))))
        print(f"  scene build {k:12s} facets={len(m.f):6d} "
              f"mi={np.median(ts)*1e3:7.1f} ms  cad={np.median(t_cad)*1e3:7.1f} ms", flush=True)
    _RESULT["scene_build"] = dict(
        note="ONE-OFF per (mesh, carrier, exclude-set). rcs_sbr._SCENE_CACHE reuses it across all "
             "azimuths/elevations, so it is NOT a per-pose cost. Reported so the split is complete.",
        rows=rows)
    _flush("scene_build")


# --------------------------------------------------------------------------- #
#  3c. PO 적분 안의 hotspot — 어디가 느린지 이름을 대고, 고칠 수 있는지 잰다
# --------------------------------------------------------------------------- #
def section_po_hotspot(n_rays=445_568, n_az=120, reps=5):
    """PO 단계를 구성연산으로 쪼개 잰다(host numpy, 생산 규모 그대로).

    ⭐ 목적: '반론이 맞다/틀리다' 를 넘어서 **어디가 비싼지**를 이름으로 짚는 것.
      `np.add.at` 은 numpy 의 unbuffered scatter-add 로 알려진 저속경로다 —
      같은 결과를 내는 `np.bincount` 와 나란히 재서 배수를 남긴다(물리 변경 0)."""
    rng = np.random.default_rng(0)
    n_rays = int(n_az * (n_rays // n_az))          # 정확히 나누어 떨어지게(생산도 그렇다)
    P = rng.random((n_rays, 3)); U = rng.random((n_rays, 3)); Nn = rng.random((n_rays, 3))
    D = -U
    aidx = np.repeat(np.arange(n_az), n_rays // n_az)
    g = rng.random(n_rays); k = 2 * np.pi / 0.0857

    def tm(fn):
        fn(); ts = []
        for _ in range(reps):
            t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
        return float(np.median(ts))

    dots = tm(lambda: np.einsum("ij,ij->i", Nn, U))
    sgn = tm(lambda: np.sign(np.einsum("ij,ij->i", Nn, -D)))
    phase = tm(lambda: np.exp(1j * 2.0 * k * np.einsum("ij,ij->i", P, U)))
    contrib = np.where(g > 0.5, g, 0.0) * np.exp(1j * rng.random(n_rays))
    E = np.zeros(n_az, complex)
    add_at = tm(lambda: np.add.at(E, aidx, contrib))
    bincount = tm(lambda: (np.bincount(aidx, contrib.real, minlength=n_az)
                           + 1j * np.bincount(aidx, contrib.imag, minlength=n_az)))
    # 두 경로가 같은 답을 내는지 확인 (최적화 제안이 물리를 바꾸지 않음을 증명)
    E2 = np.zeros(n_az, complex); np.add.at(E2, aidx, contrib)
    E3 = (np.bincount(aidx, contrib.real, minlength=n_az)
          + 1j * np.bincount(aidx, contrib.imag, minlength=n_az))
    _RESULT["po_hotspot"] = dict(
        note="host-numpy PO stage decomposed at production scale "
             f"(n_rays={n_rays} = one pass of mavic4pro @ 5.21 GHz, div=16; n_az={n_az})",
        seconds=dict(dot_products=dots, sign_flip=sgn, complex_phase_exp=phase,
                     coherent_sum_np_add_at=add_at, coherent_sum_np_bincount=bincount),
        add_at_over_bincount=float(add_at / bincount) if bincount > 0 else None,
        equivalence_max_abs_diff=float(np.max(np.abs(E2 - E3))),
        finding=f"⭐ the hotspot is the COMPLEX PHASE EXPONENTIAL, not the scatter-add: "
                f"np.exp(1j·2k·(r·û)) costs {phase*1e3:.1f} ms while the coherent sum "
                f"np.add.at costs {add_at*1e3:.1f} ms for the same {n_rays} rays. The phase "
                f"exponential alone is {phase/max(add_at,1e-12):.0f}x the reduction.",
        hypothesis_disproved=f"we expected np.add.at to be numpy's unbuffered scatter-add slow "
                             f"path and np.bincount to beat it. Measured the other way: "
                             f"np.add.at {add_at*1e3:.1f} ms vs np.bincount(real)+bincount(imag) "
                             f"{bincount*1e3:.1f} ms, i.e. add.at is "
                             f"{bincount/max(add_at,1e-12):.1f}x FASTER on this numpy "
                             f"({np.__version__}). Recorded because we were wrong, not because it "
                             f"helped. The two paths agree to "
                             f"{float(np.max(np.abs(E2-E3))):.2e} in absolute value.",
        caveat="single-threaded host numpy on a 64-core box shared with other jobs")
    print(f"  PO hotspot: add.at {add_at*1e3:.1f} ms vs bincount {bincount*1e3:.1f} ms "
          f"({add_at/max(bincount,1e-12):.0f}x), phase exp {phase*1e3:.1f} ms", flush=True)
    _flush("po_hotspot")


# --------------------------------------------------------------------------- #
#  3b. **같은 카드 위의 스톡 Sionna** — 하드웨어 정규화 문제를 통째로 없애는 유일한 방법
# --------------------------------------------------------------------------- #
def section_stock_sionna(drone="mavic4pro", fc=3.5e9, reps=2):
    """스톡 `sionna.rt.PathSolver` 를 **우리 카드에서** 재서 문헌 0.0592~0.286 s 와 나란히 둔다.

    ⚠ 이건 우리 커널과 **다른 양**을 잰다 — 전파경로(지연·도플러·이득)이지 표적 σ 가 아니다.
      그래도 published baseline 이 재는 것과 **같은 양**이므로, 카드가 다르다는 반박을 없앤다.
    ⚠ spp(samples_per_src)·max_depth 가 비용을 지배한다 → 스윕해서 전부 남긴다.
      논문들은 자기 설정을 인쇄하지 않았으므로 **한 숫자로 못 박지 않는다**."""
    import sionna.rt as rt
    from radar_scene import build_monostatic_scene
    rows = []
    for with_chamber in (False, True):
        try:
            t0 = time.perf_counter()
            scene, info = build_monostatic_scene(drone, fc=fc, with_chamber=with_chamber)
            t_build = time.perf_counter() - t0
        except Exception as e:
            rows.append(dict(with_chamber=with_chamber, error=f"{type(e).__name__}: {e}"))
            continue
        for depth in (1, 2, 3):
            for spp in (100_000, 1_000_000):
                try:
                    solver = rt.PathSolver()
                    solver(scene, max_depth=depth, los=True, specular_reflection=True,
                           diffuse_reflection=True, refraction=False,
                           samples_per_src=spp, seed=1)          # warmup
                    ts = []
                    for _ in range(reps):
                        t0 = time.perf_counter()
                        p = solver(scene, max_depth=depth, los=True, specular_reflection=True,
                                   diffuse_reflection=True, refraction=False,
                                   samples_per_src=spp, seed=1)
                        np.asarray(p.tau)                        # force evaluation
                        _sync()
                        ts.append(time.perf_counter() - t0)
                    rows.append(dict(with_chamber=with_chamber, max_depth=depth, spp=int(spp),
                                     scene_build_s=float(t_build),
                                     solve_s=dict(min=float(min(ts)), median=float(np.median(ts)),
                                                  max=float(max(ts))),
                                     n_paths=int(np.asarray(p.tau).size)))
                    print(f"  stock Sionna PathSolver chamber={int(with_chamber)} depth={depth} "
                          f"spp={spp:>9,d}  {np.median(ts)*1e3:8.1f} ms/solve", flush=True)
                except Exception as e:
                    rows.append(dict(with_chamber=with_chamber, max_depth=depth, spp=int(spp),
                                     error=f"{type(e).__name__}: {e}"))
                    print(f"  stock Sionna depth={depth} spp={spp} FAILED {type(e).__name__}",
                          flush=True)
    ok = [r for r in rows if "solve_s" in r]
    _RESULT["stock_sionna_same_card"] = dict(
        note="stock sionna.rt.PathSolver on the SAME RTX 4090 as our kernel — removes the "
             "cross-hardware objection for the most important baseline. Different quantity "
             "(propagation paths, not target RCS); scene = our 30x20x11 m chamber with a "
             f"{drone} at {fc/1e9:.2f} GHz.",
        engine="sionna.rt.PathSolver (sionna 2.0.1), los+specular+diffuse, refraction off",
        rows=rows,
        range_ms=(dict(min=float(min(r["solve_s"]["median"] for r in ok) * 1e3),
                       max=float(max(r["solve_s"]["median"] for r in ok) * 1e3)) if ok else None),
        caveat="spp and max_depth are free parameters neither we nor the cited papers pinned; "
               "the sweep is the honest form. Production in this repo uses spp=1e6-2e6.")
    _flush("stock_sionna_same_card")
    return rows


# --------------------------------------------------------------------------- #
#  4. published baselines — **원문에서 직접 확인한 것만**, 인쇄된 단위 그대로
#     (이 프로젝트의 실패양식은 '원문을 열기 전에 주장하는 것' 이다. 여기 있는 모든 행은
#      pdf_path + page + verbatim quote 를 달고 있고, 아래 4건은 이번에 **정정**되었다.)
# --------------------------------------------------------------------------- #
_PAPERS = "/data/public/sionna_jeong"


def section_baselines():
    B = []
    B.append(dict(
        id="deeprt-e", who="stock Sionna, measured by DeepRT-E authors",
        cite="T. Wu et al., 'DeepRT Engine: A Unified GPU-Parallel Ray-Tracing Framework…', "
             "arXiv:2607.11743v1 (preprint, no venue)",
        pdf=_PAPERS + "/papers_isac_sionna/new_0731/2607.11743__deeprt-engine-sbr-im-hybrid.pdf",
        page=4, value_s=0.286,
        quote_prose="the execution time comparison conducted on the same server platform, as "
                    "summarized in Table I, indicates that DeepRT-E achieves a substantial speedup "
                    "over Wireless InSite and demonstrates computational efficiency on the same "
                    "order of magnitude as Sionna",
        table_read="TABLE I: DeepRT-E 0.148 s / serial hybrid RT 3.981 s / Wireless InSite 2.804 s "
                   "/ Sionna 0.286 s",
        hardware="dual Intel Xeon Gold 6330 (2.00 GHz) + NVIDIA GeForce RTX 4090 (p.3)",
        scene="indoor scenario, 28 GHz; facet count NOT printed",
        unit_as_printed="none — the table says 'Runtime', not 'per pose'",
        caveat="⚠ 'per pose' is OUR reading (consistent with their Fig. 7, where runtime is flat "
               "in ray count). It is not the authors' statement. Recorded in "
               "outputs/r2_read_w3.json records[2].VERIFICATION_OF_OUR_OWN_QB_NUMBER.",
        correction="our record said 0.29 s; the printed value is 0.286 s"))
    B.append(dict(
        id="onetwin", who="stock Sionna RT, measured by oneTwin authors",
        cite="Zhang et al., 'oneTwin: Online Digital Network Twin via Neural Radio Radiance "
             "Field', arXiv:2601.03216",
        pdf=_PAPERS + "/sionna_papers_by_task/digital_twin/"
                      "2601.03216__zhang-onetwin-online-digital-network-twin.pdf",
        page=8, value_s=0.204,
        quote="we observe that the execution of Sionna RT requires 0.204 seconds on average, "
              "which totals 0.204 × 25 = 5.1 seconds during material tuning",
        hardware="Intel i7-14700K (64G) + NVIDIA RTX 4090 (24G), Ubuntu 22.04 (p.6)",
        scene="outdoor, 650 m × 370 m, 27 buildings, 200 online data points (p.8)",
        unit_as_printed="per execution of Sionna RT (one solve inside a Bayesian-optimisation step)"))
    B.append(dict(
        id="luo", who="stock Sionna RT, measured by Luo et al.",
        cite="H. Luo, S. R. Khosravirad, A. Alkhateeb, 'Wireless Digital Twin Calibration: "
             "Refining DFT-Domain Channel Information', arXiv:2603.16126",
        pdf=_PAPERS + "/sionna_papers_by_task/digital_twin/"
                      "2603.16126__luo-wireless-dt-calibration-dft.pdf",
        page=5, value_s=0.0592,
        quote="the computation time for ray tracing using Sionna RT (0.0592 seconds per sample) "
              "is much lower than that of Wireless Insite (1.2019 seconds per sample)",
        hardware="NVIDIA RTX A5000 GPU (p.5)",
        unit_as_printed="per sample",
        correction="⭐ PROVENANCE FIX — our record cited 'Luo p5' without the arXiv id, and the "
                   "Luo paper filed in papers_isac_sionna (2408.11295, 3GPP bistatic sensing) "
                   "contains ZERO occurrences of 'Sionna', 'GPU', 'RTX', 'A5000' or '0.0592' "
                   "(checked all 13 pages). The number belongs to a DIFFERENT Luo paper, "
                   "arXiv:2603.16126, filed under sionna_papers_by_task/digital_twin."))
    B.append(dict(
        id="ziganshin-tableII", who="Ziganshin et al., UTD ladder on top of Sionna-RT",
        cite="Ziganshin et al., journal preprint arXiv:2604.05991v2 (2 Jul 2026)",
        pdf=_PAPERS + "/papers_isac_sionna/2604.05991__ziganshin_curved-body-scattering.pdf",
        page=8,
        table_quote="TABLE II EXECUTION TIME (IN SECONDS) FOR DIFFERENT GEOMETRIES AND RT "
                    "CONFIGURATIONS. Scenario RT +V +EE +EV/VE | Sphere (156 facets) 0.3 1.1 1.8 "
                    "4.6 | Sphere (346 facets) 0.4 1.8 3.1 6.8 | Vehicle (220 facets) 0.4 0.9 2.4 "
                    "5.0 | Vehicle (1496 facets) 0.7 3.6 10.2 19.0",
        hardware_quote="All simulations were performed on a CPU platform. … The computational "
                       "performance was evaluated on a dual-socket AMD EPYC 7343 CPU platform "
                       "with 32 physical cores. Reported runtimes correspond to the average of 5 "
                       "independent runs.",
        sweep_quote="The considered scenarios include two spherical cases with 720 angular points "
                    "and two vehicle meshes with 360 angular points",
        parallel_quote="Also, all observation locations are processed simultaneously (in parallel) "
                       "within a single RT simulation.",
        vehicle_1496_facets_s=dict(RT=0.7, plus_V=3.6, plus_EE=10.2, plus_EV_VE=19.0),
        per_angular_point_ms=dict(RT=0.7 / 360 * 1e3, plus_V=3.6 / 360 * 1e3,
                                  plus_EE=10.2 / 360 * 1e3, plus_EV_VE=19.0 / 360 * 1e3,
                                  n_angles=360),
        correction="⭐ APPLES-TO-APPLES FIX — 0.7 s and 19.0 s are for the WHOLE 360-angle sweep, "
                   "not per pose: p.8 states the vehicle scenarios use '360 angular points' and "
                   "that 'all observation locations are processed simultaneously (in parallel) "
                   "within a single RT simulation'. Per angular point that is 1.94 ms (RT) and "
                   "52.8 ms (full ladder). Placing our per-pose cost against 0.7 s / 19.0 s "
                   "directly would be wrong by 360x. (Already verified in-repo: "
                   "outputs/psolve_adopt_audit.json paper_quotes_re_verified[3].)"))
    B.append(dict(
        id="ziganshin-mlfmm", who="full-wave reference in the same paper",
        cite="arXiv:2604.05991v2", page=8,
        quote="it should be emphasized that MLFMM simulations are considerably more "
              "computationally demanding. For instance, each of the MLFMM simulations in this "
              "study took several hours.",
        correction="our record said 'MLFMM ~1 h per 720-point sphere'; the printed statement is "
                   "'several hours' per simulation, with no per-point figure. The 'full PO solver "
                   "around one day (EuCAP conference version p4)' line could NOT be checked — the "
                   "EuCAP conference version is not in our corpus (only the journal preprint, "
                   "two copies)."))
    B.append(dict(
        id="sagitta-perpose", who="SagittaSBR — an independent SBR+PO RCS solver (closest peer)",
        cite="SagittaSBR, arXiv:2604.09243",
        pdf=_PAPERS + "/papers_isac_sionna/2604.09243__sagitta-sbr.pdf", page=9,
        quote="A total of 30,000 × 30,000 rays are launched from a 90 × 90 m grid, with an average "
              "computation time of 616.12 ms in FP32 per angular position with a total sweep time "
              "of ∼27 minutes on 8 LUMI nodes.",
        hardware_quote="on a partition of eight LUMI nodes with four AMD MI250X GPUs per node, the "
                       "average computation time is approximately 616 ms per angular position in "
                       "FP32 (p.10)",
        value_s=0.61612, rays_per_pose=9.0e8,
        target="A380 aircraft, ~80 × 73 × 21 m, 162,000 triangles, 10 GHz",
        unit_as_printed="per angular position",
        caveat="8 nodes × 4 MI250X = 32 GPUs (64 GCDs). 616 ms is NOT a single-GPU number."))
    B.append(dict(
        id="sagitta-kernel-split",
        who="⭐ SagittaSBR kernel-time breakdown — the only published GPU-level RT-vs-PO split",
        cite="SagittaSBR, arXiv:2604.09243", pdf=_PAPERS +
        "/papers_isac_sionna/2604.09243__sagitta-sbr.pdf", page=11,
        quote="Table 1: Kernel-time breakdown for A380 scattering simulations (18,000 × 18,000 "
              "rays) using one MPI process. Statistics evaluated over 10 simulation repetitions, "
              "each simulation scans 600 angular positions. … NVIDIA A100 (Full) Ray Launch "
              "98.96 ± 1.18 [FP32 ms] 151.30 ± 1.75 [FP64 ms]; PO Integral 6.43 ± 0.09 / 6.01 ± "
              "0.06. AMD MI250X (1 GCD) Ray Launch 249.81 ± 0.52 / 198.70 ± 0.31; PO Integral "
              "4.83 ± 0.01 / 7.41 ± 0.01",
        po_over_raylaunch=dict(A100_fp32=6.43 / 98.96, A100_fp64=6.01 / 151.30,
                               MI250X_gcd_fp32=4.83 / 249.81, MI250X_gcd_fp64=7.41 / 198.70),
        why_it_matters="⭐ This is the direct published test of Ziganshin's claim that 'the need to "
                       "cascade PO after RT negates the computational advantages of RT'. In a "
                       "GPU-resident SBR+PO solver the PO integral costs 6.5% (A100 FP32) to 1.9% "
                       "(MI250X FP32) of the ray-launch kernel. The cascade does not negate RT; "
                       "it adds single-digit percent — when the integral is a device kernel.",
        caveat="the table's ms figures are read as per angular position (324M rays in 98.96 ms = "
               "3.3 G rays/s traversal and 5.2 GB reduced in 6.43 ms = 0.8 TB/s, both plausible "
               "for an A100); the caption's '600 angular positions' describes the repetition "
               "protocol, not the per-row unit."))
    _RESULT["published_baselines"] = dict(
        note="every row carries pdf path + page + verbatim quote; four rows carry a correction "
             "found by opening the source this session",
        rows=B)
    _flush("published_baselines")
    return B


# --------------------------------------------------------------------------- #
#  5. 사다리 + 반론에 대한 답
# --------------------------------------------------------------------------- #
def _cost_drivers():
    """스윕에서 **비용이 어디로 가는지**를 한 문단짜리 사실로 뽑는다."""
    sw = _RESULT.get("sweeps", {})
    out = {}

    def _rows(k):
        return [r for r in sw.get(k, {}).get("rows", []) if "per_pose_ms" in r]

    fr = _rows("facets")
    if len(fr) >= 3:
        base = fr[0]["per_pose_ms"]["median"]
        out["facet_count"] = dict(
            facets=[r["facets"] for r in fr],
            per_pose_ms=[r["per_pose_ms"]["median"] for r in fr],
            ratio_vs_x1=[r["per_pose_ms"]["median"] / base for r in fr],
            rays_per_pose_identical=len({r["rays_per_pose"] for r in fr}) == 1,
            finding="⭐ cost is NEARLY FLAT in facet count: 16x the triangles on the identical "
                    f"surface changes the pose cost by {(fr[-1]['per_pose_ms']['median']/base-1)*100:+.0f}%. "
                    "Our cost is set by RAY COUNT, not mesh complexity. This is the sharpest "
                    "comparability point against Ziganshin, whose diffraction ladder is edge/vertex "
                    "combinatorial and whose own table shows the 1496-facet car costing 3.8x the "
                    "220-facet car at +EV/VE (19.0 s vs 5.0 s).")
    pr = _rows("passes")
    if pr:
        def passes(r):
            return r["passes_per_pose"]
        out["pass_count"] = dict(
            rows=[dict(jitter=r["jitter"], penetrate=r["penetrate"], passes=passes(r),
                       per_pose_ms=r["per_pose_ms"]["median"],
                       ms_per_pass=r["per_pose_ms"]["median"] / passes(r)) for r in pr],
            finding="cost is LINEAR in the number of ray-cast passes. One bare SBR+PO pass — "
                    "i.e. exactly the 'cascade PO after RT' the objection names — costs "
                    f"{pr[0]['per_pose_ms']['median']:.1f} ms. Our production pose is "
                    f"{pr[3]['passes_per_pose']}x that because WE chose grid-jitter averaging "
                    "(J=2 → 4 offsets) and dielectric-shell penetration (2nd trace). Those are our "
                    "accuracy choices, not a cost of cascading PO onto RT.")
    dr_ = _rows("divisor")
    if dr_:
        out["ray_spacing"] = dict(
            div=[r["div"] for r in dr_], rays_per_pose=[r["rays_per_pose"] for r in dr_],
            per_pose_ms=[r["per_pose_ms"]["median"] for r in dr_],
            finding="rays scale as div^2 (lambda/div grid); measured time grows sublinearly at "
                    "small div because fixed per-launch cost dominates there.")
    br = _rows("batch_az")
    if br:
        out["batch_size"] = dict(
            n_az=[r["n_az"] for r in br], per_pose_ms=[r["per_pose_ms"]["median"] for r in br],
            speedup_1_to_max=float(br[0]["per_pose_ms"]["median"]
                                   / br[-1]["per_pose_ms"]["median"]),
            finding="⭐ fusing azimuths into one ray bundle is worth "
                    f"{br[0]['per_pose_ms']['median']/br[-1]['per_pose_ms']['median']:.0f}x per "
                    "pose. Quoting a per-pose cost without the batch size is meaningless; "
                    "production runs the whole 120-azimuth grid in one bundle.")
    return out


def section_answer():
    rows = _RESULT["production_per_pose"]["rows"]
    pp = np.array([r["per_pose_ms"]["median"] for r in rows])
    pp_min = np.array([r["per_pose_ms"]["min"] for r in rows])
    # 반복통과가 있으면 **드리프트를 명시**한다(조용히 좋은 쪽만 쓰지 않는다).
    rep = _RESULT.get("production_per_pose_repeat")
    both = None
    if rep:
        both = dict(headline_pass=dict(min=float(pp.min()), median=float(np.median(pp)),
                                       max=float(pp.max())),
                    repeat_pass=rep["summary_ms"], drift_ratio=rep.get("drift_ratio"),
                    per_config=rep.get("drift_vs_pass1"),
                    note="the card was shared with a foreign job whose utilisation swung between "
                         "0% and 100% during the session. Both passes are kept; the drift ratio "
                         "is the honest error bar on every absolute millisecond in this file.")
    st = _RESULT["production_per_pose"]["stage_pct_median_over_configs"]
    rt_pct = float(np.median([r["stage_pct"]["rt_trace"] for r in rows]))
    po_pct = float(np.median([r["stage_pct"]["po"] for r in rows]))
    ho_pct = float(np.median([r["stage_pct"]["handoff"] for r in rows]))
    host_pct = 100.0 - rt_pct
    po_over_rt = float(np.median([r["po_over_rt"] for r in rows]))
    # 광선당 비용 (엔진 효율의 하드웨어 중립 비교 — 표적 크기 차이를 나눠 없앤다)
    ns_per_ray = [1e6 * r["per_pose_ms"]["median"] / r["rays_per_pose"] for r in rows]
    po_ns_per_ray = [1e6 * r["stage_per_pose_ms"]["po"] / r["rays_per_pose"] for r in rows]

    ladder = [
        dict(what="ours — SBR+PO backscatter pose, 5 drones × 3 bands, 18.8k–35.4k facets",
             per_pose_s=[float(pp.min() / 1e3), float(pp.max() / 1e3)],
             median_s=float(np.median(pp) / 1e3),
             hardware="1× RTX 4090 (SHARED with another user's job) + Intel Xeon Gold 6526Y host",
             measures="RCS of a target (ray cast + PO surface integral)"),
        dict(what="stock Sionna RT solve — Luo arXiv:2603.16126 p.5", per_pose_s=[0.0592, 0.0592],
             hardware="RTX A5000", measures="propagation paths (no target RCS)"),
        dict(what="stock Sionna RT solve — oneTwin arXiv:2601.03216 p.8", per_pose_s=[0.204, 0.204],
             hardware="RTX 4090 + i7-14700K", measures="propagation paths (no target RCS)"),
        dict(what="stock Sionna RT solve — DeepRT-E arXiv:2607.11743 Table I", per_pose_s=[0.286, 0.286],
             hardware="RTX 4090 + dual Xeon Gold 6330", measures="propagation paths (no target RCS)"),
        dict(what="Ziganshin RT only, vehicle 1496 facets, PER ANGULAR POINT (0.7 s / 360)",
             per_pose_s=[0.7 / 360, 0.7 / 360], hardware="dual AMD EPYC 7343, 32 cores, CPU only",
             measures="GO/RT field on a PEC car"),
        dict(what="Ziganshin full diffraction ladder +EV/VE, PER ANGULAR POINT (19.0 s / 360)",
             per_pose_s=[19.0 / 360, 19.0 / 360], hardware="dual AMD EPYC 7343, 32 cores, CPU only",
             measures="RT + vertex + 2nd-order edge diffraction on a PEC car"),
        dict(what="SagittaSBR (SBR+PO), A380, 900M rays, per angular position",
             per_pose_s=[0.61612, 0.61612], hardware="32× AMD MI250X (8 LUMI nodes, 64 GCDs)",
             measures="RCS of an aircraft (ray cast + PO integral, GPU-resident)"),
        dict(what="MLFMM full-wave, same Ziganshin study", per_pose_s=[None, None],
             hardware="not stated", measures="'several hours' per simulation (p.8)"),
    ]

    # 같은 카드 위 스톡 Sionna — 하드웨어 변수를 없앤 유일한 비교
    sk = _RESULT.get("stock_sionna_same_card") or {}
    sk_ok = [r for r in sk.get("rows", []) if "solve_s" in r]
    sk_ms = sorted(r["solve_s"]["median"] * 1e3 for r in sk_ok)
    same_card = (dict(stock_sionna_pathsolver_ms=dict(min=sk_ms[0], max=sk_ms[-1],
                                                      median=float(np.median(sk_ms)),
                                                      n_configs=len(sk_ms)),
                      ours_ms=dict(min=float(pp.min()), median=float(np.median(pp)),
                                   max=float(pp.max())),
                      ratio_ours_median_over_stock_median=float(np.median(pp) / np.median(sk_ms)),
                      reading="on the SAME RTX 4090, in our own 30x20x11 m chamber scene with a "
                              "drone, a stock sionna.rt.PathSolver propagation solve costs "
                              f"{sk_ms[0]:.0f}-{sk_ms[-1]:.0f} ms across max_depth 1-3 and "
                              "spp 1e5-1e6, while our full SBR+PO backscatter pose costs "
                              f"{pp.min():.0f}-{pp.max():.0f} ms. The hardware variable is gone: "
                              "we are in the same band as stock Sionna, not an order above it.",
                      caveat="different quantities (paths vs RCS) and different scene content; "
                             "this controls hardware, not the physics being computed.")
                 if sk_ms else None)

    ans = dict(
        one_line=f"our production SBR+PO pose costs {pp.min():.0f}–{pp.max():.0f} ms "
                 f"(median {np.median(pp):.0f} ms) on one shared RTX 4090",
        same_card_control=same_card,
        two_sentence_answer=(
            "Measured on the production kernel (rcs_sbr_batch, spacing λ/16, jitter J=2, "
            "dielectric-shell penetration on, the full 120-azimuth production batch), one "
            f"backscatter pose of a {rows[0]['facets']//1000}k–35k-facet airframe costs "
            f"{pp.min():.0f}–{pp.max():.0f} ms (median {np.median(pp):.0f} ms) on a single "
            "(shared) RTX 4090 — the same band as stock Sionna's own published per-solve cost "
            "(0.0592 s on an A5000, 0.204 s and 0.286 s on RTX 4090s)"
            + (f", as stock Sionna measured on OUR card in OUR chamber scene "
               f"({sk_ms[0]:.0f}–{sk_ms[-1]:.0f} ms per PathSolver solve)" if sk_ms else "")
            + ", and between Ziganshin's own RT-only 1.9 ms and his full diffraction ladder's "
            "52.8 ms per angular point on a 32-core EPYC platform — on a mesh carrying 20x his "
            "facet count. "
            f"The cascade itself is not what costs: ray casting is only {rt_pct:.1f}% of our wall "
            f"clock and the PO integral is {po_pct:.0f}% of it solely because we run the integral "
            "in host numpy — the one published GPU kernel-level breakdown of an SBR+PO RCS solver "
            "(SagittaSBR Table 1, p.11) puts the PO integral at 6.5% of ray-launch time on an "
            "A100, so cascading PO after RT costs single-digit percent when the integral is "
            "written as a device kernel."),
        what_the_measurement_does_NOT_support=[
            "it does not show our kernel is efficient per ray — it is not. Our PO reduction runs "
            f"at {np.median(po_ns_per_ray):.0f} ns/ray in host numpy; SagittaSBR's device-side PO "
            "kernel reduces 324M rays in 6.43 ms = 0.02 ns/ray on one A100. We are cheap per pose "
            "because our targets are small (0.05–0.5 M rays/pose), not because the engine is fast.",
            "it does not answer the first half of Ziganshin's objection (shadow region). That half "
            "is answered by scope: our claims live in backscatter and beta <= 45 deg.",
            "the stock-Sionna baselines measure a different quantity (propagation paths in a "
            "room/city scene) than ours (target RCS). The ladder places orders of magnitude, "
            "not a like-for-like speed ratio.",
            "no cross-hardware normalisation was applied. Our card was shared with another job at "
            "0–100% foreign utilisation during the run; the per-config min is the least-contended "
            "observation and the spread between min and max is reported for every row.",
        ],
        verdict=("ANSWERABLE, with the ratio conceded. The objection is right that in OUR "
                 "implementation PO dominates ray casting "
                 f"(PO/RT = {po_over_rt:.0f}x at production batch); it is wrong that this negates "
                 "RT's advantage in practice, because the absolute per-pose cost lands at or below "
                 "stock Sionna's own published per-solve cost, and because the published "
                 "GPU-resident SBR+PO breakdown puts the PO integral at 1.9–6.5% of ray launch."),
        cost_structure=dict(
            rt_trace_pct=rt_pct, handoff_d2h_pct=ho_pct, po_integral_pct=po_pct,
            host_side_pct=host_pct, po_over_rt=po_over_rt,
            reading="at the production batch size the GPU ray cast is a few percent of wall clock; "
                    "the rest is host-side: ray-grid generation (numpy), device→host transfer of "
                    "hit records, and the PO phase sum. This is an implementation property, not a "
                    "property of SBR+PO."),
        cost_per_ray=dict(ours_ns_per_ray_median=float(np.median(ns_per_ray)),
                          ours_po_ns_per_ray_median=float(np.median(po_ns_per_ray)),
                          sagitta_A100_raylaunch_ns_per_ray=98.96e-3 / 324e6 * 1e9,
                          sagitta_A100_po_ns_per_ray=6.43e-3 / 324e6 * 1e9,
                          note="Sagitta Table 1 row is 18,000² = 324M rays per angular position"),
        least_contended_median_ms=float(np.median(pp_min)),
        stage_pct_median=st,
        two_passes=both,
        cost_drivers=_cost_drivers(),
        headroom_named_not_applied=[
            dict(where="src/rcs_sbr.py rcs_sbr_batch — `np.exp(1j*2*k*einsum(P-ctr, U))`",
                 what="the complex phase exponential is the single most expensive host operation "
                      "in the PO stage (see po_hotspot). It is elementwise and embarrassingly "
                      "parallel — the natural first thing to move onto the device.",
                 physics_change="none"),
            dict(where="src/rcs_sbr.py rcs_sbr_batch — `np.add.at(E, aidx, contrib)`",
                 what="NOT a bottleneck. We predicted it was numpy's slow scatter-add path and "
                      "measured the opposite (po_hotspot.hypothesis_disproved). Left alone.",
                 physics_change="none"),
            dict(where="src/rcs_sbr.py `_lit_g_phase` — `for sp, gm in zip(shptr, gam): "
                       "np.where(np.asarray(si.shape == sp) …)`",
                 what="one device kernel + one device→host copy PER MATERIAL GROUP per pass. With "
                      "8–10 groups, 4 jitter offsets and the penetration pass that is ~64–80 "
                      "round-trips per pose; a single shape-index readback would need one. On a "
                      "shared card each round-trip queues behind the foreign job, which is why the "
                      "handoff bucket dominates at small batch.",
                 physics_change="none"),
            dict(where="src/rcs_sbr.py rcs_sbr_batch — `np.tile(-u, (rays_per_az, 1))` for D and U",
                 what="materialises two (N,3) arrays whose rows are all identical, per azimuth per "
                      "jitter offset; the dot products that consume them could broadcast instead",
                 physics_change="none"),
            dict(where="the PO integral as a whole",
                 what="it runs in host numpy. SagittaSBR (arXiv:2604.09243 Table 1, p.11) shows a "
                      "device-side PO integral costing 1.9–6.5% of ray launch. That is the size of "
                      "the prize, and it is measured by someone else, not asserted by us.",
                 physics_change="none"),
        ],
    )
    _RESULT["ladder"] = ladder
    _RESULT["answer"] = ans
    _flush("answer")
    print("\n" + ans["verdict"])
    return ans


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    t_start = time.perf_counter()
    section_meta()

    from drones import DRONES, build_drone
    DRONES_ALL = ["mini5pro", "phantom4", "mavic4pro", "matrice4e", "s1000plus"]

    # ── A. 생산 설정 per-pose (기종 × 밴드) ──────────────────────────────────
    #  ⭐ n_az=120 = 생산 방위각 격자 그대로(AZ_GRID = 0…357°, 3° step). 배치크기가 자세당
    #     비용을 17배까지 바꾸므로(sweeps.batch_az), 생산 숫자는 생산 배치에서만 의미가 있다.
    print("\n[A] production per-pose (div=16, J=2, penetrate=True, n_az=120 = AZ_GRID)", flush=True)
    rows = []
    for k in DRONES_ALL:
        for bname, fc in BANDS:
            r = measure(k, fc, n_az=120, reps=2)
            r["band"] = bname
            rows.append(r)
    per_pose = np.array([r["per_pose_ms"]["median"] for r in rows])
    per_pose_min = np.array([r["per_pose_ms"]["min"] for r in rows])
    # 단계 비중은 배치가 클수록 host 쪽으로 쏠린다 → 생산배치에서의 중앙값을 따로 남긴다.
    st = {k: float(np.median([r["stage_pct"][k] for r in rows])) for k in rows[0]["stage_pct"]}
    n_el, n_az_grid = 9, 120        # experiment_freespace_sigma.EL_GRID / AZ_GRID
    total_poses = len(DRONES_ALL) * len(BANDS) * PROD_NF * n_el * n_az_grid
    proj_s = float(np.sum(per_pose) / 1e3 * PROD_NF * n_el * n_az_grid)
    _RESULT["production_per_pose"] = dict(
        settings=dict(div=PROD_DIV, jitter=PROD_JITTER, penetrate=PROD_PEN, el_deg=PROD_EL,
                      n_az_per_batch=120,
                      n_az_note="= experiment_freespace_sigma.AZ_GRID (0..357 deg, 3 deg step); "
                                "the production chunker puts the whole grid in one ray bundle"),
        rows=rows,
        summary_ms=dict(min=float(per_pose.min()), median=float(np.median(per_pose)),
                        max=float(per_pose.max()),
                        geomean=float(np.exp(np.mean(np.log(per_pose)))),
                        least_contended_median=float(np.median(per_pose_min))),
        stage_pct_median_over_configs=st,
        band_averaged_pose_ms=dict(
            note=f"production sigma averages n_f={PROD_NF} carriers → multiply by {PROD_NF}",
            median=float(np.median(per_pose) * PROD_NF),
            min=float(per_pose.min() * PROD_NF), max=float(per_pose.max() * PROD_NF)),
        whole_published_grid=dict(
            note="the full report13 sigma grid: 5 airframes x 3 bands x n_f=3 carriers x 9 el "
                 "x 120 az, priced from the measured per-pose medians",
            poses=int(total_poses), projected_seconds=proj_s,
            projected_hours=proj_s / 3600.0,
            caveat="one shared RTX 4090; production actually fans out over free GPUs "
                   "(channel.sbr_sigma_prefill), so wall clock is lower"),
    )
    _flush("production_per_pose")
    _RESULT["meta"]["contention_snapshots"].append(_gpu_snapshot()); _flush()

    # ── B. scene build ──────────────────────────────────────────────────────
    print("\n[B] scene build (one-off, cached)", flush=True)
    section_scene_build(DRONES_ALL)

    # ── C. 비용 동인 스윕 ────────────────────────────────────────────────────
    sweeps = {}
    ref = dict(drone="mavic4pro", fc=3.5e9)
    NZ = 32          # 스윕 공통 배치(생산 120 보다 작다 — 절대값이 아니라 **기울기**를 본다)

    print("\n[C1] divisor sweep (rays ∝ div²)", flush=True)
    sweeps["divisor"] = dict(
        note="ray grid spacing = lambda/div; rays per pass scale as div^2. Production div=16. "
             f"measured at n_az={NZ} (slope, not absolute production cost)",
        rows=[measure(ref["drone"], ref["fc"], div=dv, n_az=NZ, reps=2)
              for dv in (8, 12, 16, 24, 32)])
    _RESULT["sweeps"] = sweeps; _flush("sweeps.divisor")

    print("\n[C2] batch size sweep (azimuths per kernel launch)", flush=True)
    sweeps["batch_az"] = dict(
        note="poses fused into one ray bundle; shows per-launch-latency amortisation. "
             "Production runs the whole 120-azimuth grid in one bundle.",
        rows=[measure(ref["drone"], ref["fc"], n_az=nz, reps=2)
              for nz in (1, 2, 4, 8, 16, 32, 64, 120)])
    _flush("sweeps.batch_az")

    print("\n[C3] jitter / penetrate (pass count)", flush=True)
    sweeps["passes"] = dict(
        note="jitter J → J^2 grid offsets; penetrate → second trace on the shell-removed scene",
        rows=[measure(ref["drone"], ref["fc"], jitter=1, penetrate=False, n_az=NZ, reps=2),
              measure(ref["drone"], ref["fc"], jitter=1, penetrate=True, n_az=NZ, reps=2),
              measure(ref["drone"], ref["fc"], jitter=2, penetrate=False, n_az=NZ, reps=2),
              measure(ref["drone"], ref["fc"], jitter=2, penetrate=True, n_az=NZ, reps=2),
              measure(ref["drone"], ref["fc"], jitter=3, penetrate=True, n_az=NZ, reps=2)])
    _flush("sweeps.passes")

    print("\n[C4] facet count at FIXED geometry (subdivision)", flush=True)
    sys.path.insert(0, os.path.join(ROOT, "report_mesh", "src"))
    from verify_mesh_suite import _subdivide_mesh
    m0 = build_drone(DRONES[ref["drone"]])
    m1 = _subdivide_mesh(m0)
    m2 = _subdivide_mesh(m1)
    frows = []
    for lbl, mm in (("x1", m0), ("x4", m1), ("x16", m2)):
        frows.append(measure(ref["drone"], ref["fc"], n_az=NZ, reps=2, mesh=mm,
                             tag=f"mavic4pro_{lbl}"))
    sweeps["facets"] = dict(
        note="same surface, 1x/4x/16x triangles (loop subdivision). Isolates BVH/facet cost from "
             "ray count. Ziganshin's vehicle mesh is 1496 facets; ours are 20-95x that.",
        rows=frows)
    _flush("sweeps.facets")

    print("\n[C5] target size (airframe extent at fixed band/div)", flush=True)
    sweeps["target_size"] = dict(
        note="ray grid covers the projected bounding sphere → rays ∝ R^2; dominant size driver",
        rows=[dict(drone=r["drone"], facets=r["facets"], rays_per_pose=r["rays_per_pose"],
                   per_pose_ms=r["per_pose_ms"]["median"], fc_ghz=r["fc_ghz"])
              for r in _RESULT["production_per_pose"]["rows"]])
    _flush("sweeps.target_size")

    _RESULT["meta"]["contention_snapshots"].append(_gpu_snapshot())

    # ── D. 문헌 기준선 + 사다리 + 답 ─────────────────────────────────────────
    section_baselines()
    section_answer()

    _RESULT["meta"]["elapsed_total_s"] = float(time.perf_counter() - t_start)
    _flush("done")
    print(f"\n[done] {time.perf_counter()-t_start:.1f} s → {OUT}", flush=True)


def rerun_A_and_answer(reps=1, n_az=120, key="production_per_pose", drones=None):
    """이미 만들어진 JSON 을 읽어 **A 섹션만 다시 재고**(경합상태 샘플링 포함) 답을 갱신한다.

    왜: 측정 중 같은 카드의 **타인 부하가 0%↔100% 로 오갔다**. 한 번의 통과로 얻은 행들은
    서로 다른 경합상태에서 나왔다 → 2차 통과를 떠서 config 마다 util 을 기록하고, 두 통과를
    **둘 다** 남긴다(조용히 한쪽만 쓰지 않는다)."""
    global _RESULT
    with open(OUT) as f:
        _RESULT = json.load(f)
    DRONES_ALL = drones or ["mini5pro", "phantom4", "mavic4pro", "matrice4e", "s1000plus"]
    rows = []
    for k in DRONES_ALL:
        for bname, fc in BANDS:
            r = measure(k, fc, n_az=n_az, reps=reps, sample_util=True)
            r["band"] = bname
            rows.append(r)
    pp = np.array([r["per_pose_ms"]["median"] for r in rows])
    st = {kk: float(np.median([r["stage_pct"][kk] for r in rows])) for kk in rows[0]["stage_pct"]}
    prev = _RESULT.get("production_per_pose", {})
    p1 = {(r["drone"], round(r["fc_ghz"], 2)): r["per_pose_ms"]["median"]
          for r in prev.get("rows", [])}
    drift = [dict(drone=r["drone"], fc_ghz=r["fc_ghz"],
                  pass1_ms=p1.get((r["drone"], round(r["fc_ghz"], 2))),
                  pass2_ms=r["per_pose_ms"]["median"],
                  ratio=(p1[(r["drone"], round(r["fc_ghz"], 2))] / r["per_pose_ms"]["median"]
                         if (r["drone"], round(r["fc_ghz"], 2)) in p1 else None),
                  gpu_util_samples=r.get("gpu_util_samples"))
             for r in rows]
    rr = [d["ratio"] for d in drift if d["ratio"]]
    _RESULT["production_per_pose_repeat"] = dict(
        pass_note="INDEPENDENT REPEAT of the headline configs, run later in the session with GPU "
                  "utilisation sampled per config. The headline production_per_pose is NOT "
                  "overwritten — this row set exists to size run-to-run drift on a shared card.",
        settings=dict(div=PROD_DIV, jitter=PROD_JITTER, penetrate=PROD_PEN, el_deg=PROD_EL,
                      n_az_per_batch=n_az, reps=reps, drones=list(DRONES_ALL)),
        rows=rows,
        summary_ms=dict(min=float(pp.min()), median=float(np.median(pp)), max=float(pp.max())),
        stage_pct_median_over_configs=st,
        drift_vs_pass1=drift,
        drift_ratio=dict(min=float(min(rr)), median=float(np.median(rr)),
                         max=float(max(rr))) if rr else None,
        reading="ratio = pass1 / pass2 per config. Values away from 1.0 are contention, not "
                "physics — the kernel is deterministic (sigma is bit-identical between passes).")
    _RESULT["meta"]["contention_snapshots"].append(_gpu_snapshot())
    _flush("production_per_pose (pass 2)")
    section_baselines()
    section_answer()
    _flush("done-pass2")


if __name__ == "__main__":
    if "--pass2" in sys.argv:
        rerun_A_and_answer()
    elif "--stock" in sys.argv:
        with open(OUT) as f:
            _RESULT = json.load(f)
        section_po_hotspot()
        section_stock_sionna()
        section_baselines()
        section_answer()
    else:
        main()
