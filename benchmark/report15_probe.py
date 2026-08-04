# -*- coding: utf-8 -*-
"""
report15_probe.py — **Sionna PathSolver 로 로터 마이크로도플러가 나오는가** (탐침)
================================================================================

묻는 것은 정확히 두 갈래다. 섞지 않는다.

  ① `Paths.doppler` 로 **자동으로** 나오나
     → 아니다(확정). Sionna 는 SceneObject 당 **강체 속도 벡터 1개**만 받는다.
       회전은 표현할 자리가 없다. 이 파일은 그 사실을 **다시 재기만** 한다(§A).

  ② **로터 위상을 스텝하고 매번 재추적**해서 복소 진폭 a(φ) 를 이어붙이면 나오나
     → **이것이 열린 질문**이다. 선례: WiFi-JEPA(arXiv:2607.11064) 가 프레임당 20 패스로
       시간축을 만들었다("each pass computes the channel for a static scene snapshot …
       Without this, a single pass yields a near-constant time axis").

⭐ **급소는 잡음바닥이다.** Sionna 의 경로탐색은 확률적이다(샘플 방향 격자 + 해시 중복제거,
   확산산란은 몬테카를로). **아무것도 움직이지 않고 같은 씬을 N 번 다시 추적**했을 때 복소
   진폭이 얼마나 흔들리는지를 먼저 재지 않으면, 나중에 나오는 변조가 진짜인지 잡음인지
   **말할 수 없다**. 순서: §A(도플러 재확인) → §B(메쉬가 실제로 바뀌나) → §S(어느 자세에
   경로가 있나) → §C(잡음바닥) → §D(위상 스텝) → 판정.

⚠⚠ **관측량 정의 — 여기서 한 번 틀렸다(기록):**
   `Paths.a` 는 **패스밴드 계수**라 **전파 위상이 들어 있지 않다**(실측: imag 성분이 정확히 0).
   Sionna 문서의 정의는 `a_b = a·exp(−j2πf·τ)` 이고 위상은 **τ 가 나른다**. 로터 변조는
   본질적으로 경로장 변화(≈ mm ~ λ)의 위상 효과이므로, `Σa` 를 보면 **변조가 통째로 사라진다**.
   그래서 이 파일의 관측량은 **베이스밴드 등가 계수의 코히런트 합**이다:

        h = Σ_{p∈표적}  a_p · exp(−j 2π f_c τ_p)

   ⚠ `Paths.cir()` 은 기본이 `normalize_delays=True` 라 첫 경로를 τ=0 으로 밀어 **절대위상
     기준을 지운다** — 쓰지 않고 원시 τ 로 직접 계산한다.
   ⚠ τ 는 float32 다. R=3 m 에서 δτ ≈ 2e−15 s → 경로장 오차 ≈ 0.7 µm ≈ 1e−5 λ 라 무해하지만,
     먼 거리에서는 이 위상이 수치잡음이 된다 — **근거리를 쓰는 또 하나의 이유**다.

⚠ 선입견 금지 — outputs/facet_count.json 은 **정지자세**에서 "정반사 에코가 있는 자세 =
   36 중 1", "정반사 경로 2→1 개 = −6.05 dB, 1→0 개 = −42.97 dB" 를 보였다. 그래서 위상을
   돌리면 블레이드 변조가 아니라 **경로가 껐다 켜지는 톱니**가 나올 것이라는 **의심**이 있다.
   그러나 그것은 고정자세에서 잰 것이고 위상 스텝은 아무도 안 봤다. 여기서는 `n_paths` 의
   위상별 거동을 **그대로 기록**할 뿐 결론을 미리 넣지 않는다.

기체 2종
  · mini2      — Das 실측 4기체 대조 ΔL −0.51 dB 로 1위인 **검증된 기준자**.
  · matrice4e  — 실측 캠페인 표적. 남은 최대 불일치가 하필 **로터 부근**(모터·프롭)이라,
                 이 실험이 정확히 그 부위를 흔든다.
  두 기체는 크기·프롭지름·RPM 이 크게 달라 **잡음바닥이 같을 이유가 없다** → 각각 잰다.

⛔ src/drones.py · src/drone_cad.py 는 **읽기만** 한다(어제 CAD 정정 미커밋).
⛔ 기존 산출물 덮어쓰기 금지 — 출력은 outputs/report15_probe.json 하나뿐이다.
그림 없음(순수 측정). 주석·print 한국어.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick as _pick_gpu                                     # noqa: E402
_pick_gpu(verbose=True)                                               # ⚠ mitsuba import 전에!

import mitsuba as mi                                                  # noqa: E402
import sionna.rt as rt                                                # noqa: E402

from drones import (DRONES, DRONE_GROUP_MAT, build_drone,             # noqa: E402
                    pose_articulated, rotor_layout, drone_colors)
from scene_build import build_scene, Part                             # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
NO_OBJ = 4294967295                    # Sionna 의 '상호작용 없음' 표식 (uint32 -1)

KEYS = ("mini2", "matrice4e")
AZ_DEG, EL_DEG = 0.0, 15.0             # 하우스 기준 시선 (viz_report1.AZ/EL 과 동일)
RANGE_M = 3.0                          # ⭐ 근거리 — Sionna 에게 가장 유리한 조건
BASELINE_M = 0.20                       # 준-모노스태틱 송수신 간격 (facet_count 와 동일 규약)
MAX_PATHS = 2_000_000

SCRATCH = os.path.join(ROOT, "outputs", "meshes", "report15_probe")
OUT_JSON = os.path.join(ROOT, "outputs", "report15_probe.json")

_TWOPI_FC_OVER = 2.0 * math.pi * FC     # exp(-j·2πf·τ) 의 계수


# --------------------------------------------------------------------------- #
#  기하 유틸
# --------------------------------------------------------------------------- #
def look_dir(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def basis_perp(u):
    """û 에 수직인 정규직교 2벡터."""
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, t); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2


def place(scene, center=(0., 0., 0.), az=AZ_DEG, el=EL_DEG, rng=RANGE_M, baseline=BASELINE_M):
    """준-모노스태틱 TX/RX 배치 → dict(tx, rx, tau_expect_s, bistatic_deg)."""
    u = look_dir(az, el)
    e1, _ = basis_perp(u)
    c = np.asarray(center, float)
    tx = c + rng * u + 0.5 * baseline * e1
    rx = c + rng * u - 0.5 * baseline * e1
    for nm in list(scene.transmitters):
        scene.remove(nm)
    for nm in list(scene.receivers):
        scene.remove(nm)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.add(rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in tx])))
    scene.add(rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx])))
    R1 = float(np.linalg.norm(tx - c)); R2 = float(np.linalg.norm(rx - c))
    u1 = (tx - c) / R1; u2 = (rx - c) / R2
    return dict(tx=[float(v) for v in tx], rx=[float(v) for v in rx],
                az_deg=float(az), el_deg=float(el), range_m=float(rng),
                baseline_m=float(baseline),
                bistatic_deg=float(np.degrees(np.arccos(np.clip(float(u1 @ u2), -1.0, 1.0)))),
                tau_expect_ns=float((R1 + R2) / C0 * 1e9))


# --------------------------------------------------------------------------- #
#  로터 위상 → 메쉬 → 씬
# --------------------------------------------------------------------------- #
def posed_mesh(spec, phase_deg: float):
    """로터 위상 φ[deg] 를 넣은 분절 스냅샷 메쉬.
    로터 k 의 스핀 = dir_k·φ (base_ang 은 pose_articulated 가 이미 더한다)
    — microdoppler.microdoppler_sbr 와 **같은 규약**이라 두 엔진의 위상축이 정렬된다."""
    dirs = [r["dir"] for r in rotor_layout(spec)]
    return pose_articulated(spec, rotor_phase_deg=[d * float(phase_deg) for d in dirs])


def mesh_signature(mesh) -> dict:
    """꼭짓점 배열의 해시 + 통계. 위상 스텝이 **정말 씬을 바꾸는지** 확인용."""
    V = np.asarray(mesh.v, float)
    h = hashlib.sha1(np.ascontiguousarray(np.round(V, 9)).tobytes()).hexdigest()
    return dict(sha1=h, n_vertices=int(V.shape[0]), n_tris=int(mesh.n_tris()),
                centroid=[float(x) for x in V.mean(axis=0)])


def build_posed_scene(spec, phase_deg: float, tag: str, fc=FC):
    """위상 φ 의 드론 **한 대만** 있는 자유공간 씬 (원점 배치). Part 별 생산 재질."""
    m = posed_mesh(spec, phase_deg)
    d = os.path.join(SCRATCH, f"{spec.key}_{tag}")
    paths = m.write_obj_per_group(d, spec.key)
    cols = drone_colors(spec)
    parts = [Part(name=f"{spec.key}_{g}_{tag}", obj=p, mat_key=DRONE_GROUP_MAT[g][0],
                  color=cols[g]) for g, p in paths.items()]
    return build_scene(parts, fc=fc), m, d


def drop_scratch(d):
    try:
        shutil.rmtree(d)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
#  경로 → **베이스밴드 등가** 복소 진폭  h = Σ a·exp(−j2πf τ)
# --------------------------------------------------------------------------- #
def unpack(paths):
    """(a[P], tau[P], dop[P], obj[depth,P]) — 1×1 안테나 가정. a 는 **패스밴드** 계수."""
    ar = np.asarray(paths.a[0]); ai = np.asarray(paths.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = a.shape[0]
    tau = np.asarray(paths.tau, dtype=np.float64).reshape(-1, P)[0] if P else np.zeros(0)
    dop = np.asarray(paths.doppler).reshape(-1)
    dop = dop[:P] if dop.shape[0] >= P else np.zeros(P)
    O = np.asarray(paths.objects)[:, 0, 0, :] if P else np.zeros((0, 0), int)
    return a, tau, dop, O


def group_of(name: str, key: str) -> str:
    """SceneObject 이름 `<key>_<group>_<tag>` → 부위 그룹. (build_posed_scene 의 명명 규약)"""
    s = name[len(key) + 1:] if name.startswith(key + "_") else name
    return s.rsplit("_", 1)[0] if "_" in s else s


def id_to_group(scene, key: str) -> dict:
    return {int(o.object_id): group_of(n, key) for n, o in scene.objects.items()}


def rt_echo(scene, spp, seed, max_depth=1, diffuse=True, fc=FC, id2grp=None):
    """표적경유 경로만 골라 **베이스밴드 코히런트 합** h 를 돌려준다.

        h = Σ_p a_p · exp(−j 2π f_c τ_p)        (Sionna 문서의 a_b 정의)

    ⭐ 두 채널을 **따로** 낸다:
      · all  — 표적경유 전 경로 (동체 정반사가 있으면 그것이 지배한다)
      · prop — **프로펠러를 맞은 경로만**. 로터 변조는 여기서만 나올 수 있으므로,
               동체 글린트에 묻히지 않는 형태로 질문하려면 이 채널을 봐야 한다.

    함께 남기는 것:
      · `nophase_db` = 20log10|Σ a_p|  — 위상을 빼먹었을 때의 값(우리가 처음 틀린 그 값).
        두 값의 차이가 곧 "위상이 관측량을 지배한다" 의 증거다.
      · `incoh_db`   = 10log10 Σ|a_p|²  — 위상무관 에너지(경로 발견 자체의 척도).
      · `rel_db`     = 직접파(표적 미상호작용) 대비.
      · `groups`     = 부위별 경로수 — 정반사가 프롭에서 오는지 동체에서 오는지 가른다.
    """
    t0 = time.time()
    p = rt.PathSolver()(scene, max_depth=int(max_depth), los=True,
                        specular_reflection=True, diffuse_reflection=bool(diffuse),
                        refraction=False, samples_per_src=int(spp),
                        max_num_paths_per_src=MAX_PATHS, seed=int(seed))
    a, tau, dop, O = unpack(p)
    dt = time.time() - t0
    base = dict(seed=int(seed), spp=int(spp), max_depth=int(max_depth),
                diffuse=bool(diffuse), sec=float(dt), n_total=int(a.size))
    empty = dict(base, n_paths=0, h_re=0.0, h_im=0.0, amp_db=None, phase_deg=None,
                 incoh_db=None, rel_db=None, nophase_db=None,
                 n_prop=0, hp_re=0.0, hp_im=0.0, prop_amp_db=None, prop_incoh_db=None,
                 groups={})
    if a.size == 0:
        return empty
    hit = (O != NO_OBJ).any(axis=0) if O.size else np.zeros(a.size, bool)
    ph = np.exp(-1j * 2.0 * np.pi * float(fc) * tau)
    hd = complex(np.sum(a[~hit] * ph[~hit])) if (~hit).any() else 0j
    A = abs(hd) + 1e-30                                            # 직접파 진폭

    # 부위별 분해 — 경로가 어느 그룹을 맞았나 (max_depth 안의 어느 단계든)
    groups, prop_mask = {}, np.zeros(a.size, bool)
    if id2grp and O.size:
        gm = np.full(O.shape, "", dtype=object)
        for oid, g in id2grp.items():
            gm[O == oid] = g
        for g in set(id2grp.values()):
            m = (gm == g).any(axis=0)
            if m.any():
                groups[g] = dict(n=int(m.sum()),
                                 incoh_db=float(10 * np.log10(float(np.sum(np.abs(a[m]) ** 2))
                                                              + 1e-300)),
                                 amp_db=float(20 * np.log10(abs(complex(np.sum(a[m] * ph[m])))
                                                            + 1e-300)))
        prop_mask = (gm == "prop").any(axis=0)

    n = int(hit.sum())
    npr = int(prop_mask.sum())
    sp = complex(np.sum(a[prop_mask] * ph[prop_mask])) if npr else 0j
    prop = dict(n_prop=npr, hp_re=float(sp.real), hp_im=float(sp.imag),
                prop_amp_db=(float(20 * np.log10(abs(sp) + 1e-300)) if npr else None),
                prop_incoh_db=(float(10 * np.log10(float(np.sum(np.abs(a[prop_mask]) ** 2))
                                                   + 1e-300)) if npr else None))
    if n == 0:
        return dict(empty, direct_abs=float(A), groups=groups, **prop)
    s = complex(np.sum(a[hit] * ph[hit]))
    return dict(base, n_paths=n, h_re=float(s.real), h_im=float(s.imag),
                amp_db=float(20 * np.log10(abs(s) + 1e-300)),
                phase_deg=float(np.degrees(np.angle(s))),
                nophase_db=float(20 * np.log10(abs(complex(np.sum(a[hit]))) + 1e-300)),
                incoh_db=float(10 * np.log10(float(np.sum(np.abs(a[hit]) ** 2)) + 1e-300)),
                rel_db=float(20 * np.log10(abs(s) / A + 1e-300)),
                direct_abs=float(A), groups=groups,
                tau_min_ns=float(np.min(tau[hit]) * 1e9),
                tau_ptp_ns=float(np.ptp(tau[hit]) * 1e9),
                a_imag_absmax=float(np.abs(np.imag(a)).max()),
                truncated=bool(a.size >= MAX_PATHS), **prop)


# --------------------------------------------------------------------------- #
#  산포 통계 (dB · 위상 · 경로수)
# --------------------------------------------------------------------------- #
def _circ_stats(deg):
    """원형(각도) 통계 — 위상은 ±180° 에서 감기므로 산술 std 를 쓰면 안 된다."""
    r = np.radians(np.asarray(deg, float))
    if r.size == 0:
        return dict(mean_deg=None, circ_std_deg=None, ptp_deg=None, resultant_R=None)
    z = np.exp(1j * r)
    Rbar = float(abs(z.mean()))
    mean = float(np.degrees(np.angle(z.mean())))
    circ_std = float(np.degrees(math.sqrt(max(0.0, -2.0 * math.log(max(Rbar, 1e-12))))))
    dev = np.degrees(np.angle(z * np.exp(-1j * math.radians(mean))))
    return dict(mean_deg=mean, circ_std_deg=circ_std,
                ptp_deg=float(dev.max() - dev.min()), resultant_R=Rbar)


def _stats(runs, k_n, k_amp, k_re, k_im, k_inc) -> dict:
    """한 채널(all 또는 prop)의 재추적 산포 — |h| dB · 위상(도) · 경로수."""
    ok = [r for r in runs if r.get(k_n) and r.get(k_amp) is not None]
    n_all = np.array([r.get(k_n, 0) for r in runs], float)
    out = dict(n_runs=len(runs), n_with_paths=len(ok),
               n_paths_mean=float(n_all.mean()) if n_all.size else 0.0,
               n_paths_std=float(n_all.std(ddof=1)) if n_all.size > 1 else 0.0,
               n_paths_min=int(n_all.min()) if n_all.size else 0,
               n_paths_max=int(n_all.max()) if n_all.size else 0,
               n_paths_zero_frac=float(np.mean(n_all == 0)) if n_all.size else 1.0)
    if not ok:
        return dict(out, amp_db_mean=None, amp_db_std=None, amp_db_ptp=None,
                    complex_mean_abs_db=None, phase=None)
    amp = np.array([r[k_amp] for r in ok], float)
    inc = np.array([r[k_inc] for r in ok], float)
    z = np.array([complex(r[k_re], r[k_im]) for r in ok])
    zm = z.mean()
    cv = float(np.sqrt(np.mean(np.abs(z - zm) ** 2)) / (abs(zm) + 1e-300))
    return dict(out,
                amp_db_mean=float(amp.mean()),
                amp_db_std=float(amp.std(ddof=1)) if amp.size > 1 else 0.0,
                amp_db_ptp=float(amp.max() - amp.min()),
                incoh_db_mean=float(inc.mean()),
                incoh_db_std=float(inc.std(ddof=1)) if inc.size > 1 else 0.0,
                incoh_db_ptp=float(inc.max() - inc.min()),
                complex_mean_abs_db=float(20 * np.log10(abs(zm) + 1e-300)),
                complex_cv=cv, complex_cv_db=float(20 * np.log10(cv + 1e-300)),
                phase=_circ_stats(np.degrees(np.angle(z))))


def spread(runs: list[dict]) -> dict:
    """재추적 묶음 → **두 채널**(all/prop) 산포 + 위상-무시 대조."""
    out = _stats(runs, "n_paths", "amp_db", "h_re", "h_im", "incoh_db")
    out["prop"] = _stats(runs, "n_prop", "prop_amp_db", "hp_re", "hp_im", "prop_incoh_db")
    out["sec_total"] = float(sum(r["sec"] for r in runs))
    ok = [r for r in runs if r.get("n_paths") and r.get("nophase_db") is not None]
    if ok:
        npz = np.array([r["nophase_db"] for r in ok], float)
        rel = np.array([r["rel_db"] for r in ok], float)
        out["nophase_db_mean"] = float(npz.mean())
        out["nophase_db_std"] = float(npz.std(ddof=1)) if npz.size > 1 else 0.0
        out["phase_vs_nophase_db"] = float(out["amp_db_mean"] - npz.mean())
        out["rel_db_mean"] = float(rel.mean())
    # 부위별 경로수 평균 — 정반사가 어디서 오는지
    gsum = {}
    for r in runs:
        for g, v in (r.get("groups") or {}).items():
            gsum.setdefault(g, []).append(v["n"])
    out["groups_n_mean"] = {g: float(np.mean(v)) for g, v in sorted(gsum.items())}
    return out


def _thin(r):
    return {k: v for k, v in r.items()
            if k in ("seed", "n_paths", "amp_db", "phase_deg", "rel_db", "incoh_db",
                     "nophase_db", "n_prop", "prop_amp_db", "prop_incoh_db", "sec")}


# --------------------------------------------------------------------------- #
#  §A — ① 갈래 재확인: Paths.doppler 는 강체 1벡터뿐
# --------------------------------------------------------------------------- #
def sec_A_doppler(spec, spp=32_000_000):
    """SceneObject.velocity 는 **객체당 3성분 벡터 1개**다 → 회전을 넣을 자리가 없다.
    (a) 정지 씬의 doppler, (b) 프롭 그룹에만 '회전 대체' 속도를 준 씬의 doppler 를 재고,
    (c) velocity 속성의 **모양**을 직접 읽어 자유도를 센다. 주장이 아니라 관측이다."""
    scene, _, d = build_posed_scene(spec, 0.0, "A")
    g2 = id_to_group(scene, spec.key)
    place(scene)
    r_static = rt_echo(scene, spp, seed=1, diffuse=True, id2grp=g2)
    p = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                        diffuse_reflection=True, refraction=False,
                        samples_per_src=int(spp), max_num_paths_per_src=MAX_PATHS, seed=1)
    _, _, dop0, _ = unpack(p)

    v_set = 30.0
    shapes = {}
    for nm, o in scene.objects.items():
        if "_prop_" in nm:                       # 프롭 그룹에만 속도를 준다
            o.velocity = mi.Vector3f(0.0, 0.0, v_set)
        shapes[nm] = int(np.asarray(o.velocity).reshape(-1).size)
    p2 = rt.PathSolver()(scene, max_depth=1, los=True, specular_reflection=True,
                         diffuse_reflection=True, refraction=False,
                         samples_per_src=int(spp), max_num_paths_per_src=MAX_PATHS, seed=1)
    a2, _, dop2, O2 = unpack(p2)
    hit2 = (O2 != NO_OBJ).any(axis=0) if O2.size else np.zeros(a2.size, bool)
    d_hit = dop2[hit2] if hit2.any() else np.zeros(0)
    uniq = np.unique(np.round(d_hit, 3))
    drop_scratch(d)
    return dict(
        static=dict(n_paths=int(r_static["n_paths"]),
                    doppler_nonzero=int(np.count_nonzero(dop0)),
                    doppler_max_abs_hz=float(np.max(np.abs(dop0))) if dop0.size else 0.0),
        rigid_prop_velocity=dict(
            v_set_ms=[0.0, 0.0, float(v_set)],
            n_target_paths=int(hit2.sum()), n_distinct_doppler=int(uniq.size),
            doppler_hz_unique_head=[float(x) for x in uniq[:12]],
            doppler_min_hz=float(d_hit.min()) if d_hit.size else None,
            doppler_max_hz=float(d_hit.max()) if d_hit.size else None,
            predicted_rigid_hz=float(2.0 * v_set * math.sin(math.radians(EL_DEG)) / LAM),
            note=("프롭 전체에 강체속도 하나를 주면 프롭경유 경로가 전부 **같은 부호·같은 크기** "
                  "도플러를 받는다 — 블레이드 전진/후퇴가 갈라지지 않는다.")),
        velocity_dof_per_object=dict(sorted(shapes.items())),
        max_dof=int(max(shapes.values())) if shapes else 0,
        verdict=("SceneObject.velocity 는 객체당 3성분(강체 1벡터)뿐 — 회전 자유도가 없다. "
                 "Paths.doppler 만으로는 블레이드 마이크로도플러가 원리적으로 불가."))


# --------------------------------------------------------------------------- #
#  §B — 로터 위상 스텝이 **정말 씬을 바꾸는가**
# --------------------------------------------------------------------------- #
def sec_B_mesh(spec, phases=(0.0, 45.0)):
    """꼭짓점 해시 대조 + 최대 이동량. 프레임(비회전부)은 안 움직여야 한다."""
    sigs, meshes = [], []
    for ph in phases:
        m = posed_mesh(spec, ph)
        meshes.append(m); sigs.append(dict(phase_deg=float(ph), **mesh_signature(m)))
    V0 = np.asarray(meshes[0].v, float); V1 = np.asarray(meshes[1].v, float)
    same_n = V0.shape == V1.shape
    d = np.linalg.norm(V1 - V0, axis=1) if same_n else np.zeros(0)
    # 면별 그룹(.g) → 그 그룹에 쓰인 꼭짓점으로 되돌려 부위별 최대이동을 낸다
    moved = {}
    F = np.asarray(meshes[0].f, int)
    gl = np.asarray(meshes[0].g, dtype=object)
    if same_n and F.size and gl.size == F.shape[0]:
        for grp in sorted(set(gl.tolist())):
            vi = np.unique(F[gl == grp].ravel())
            moved[str(grp)] = float(d[vi].max()) if vi.size else 0.0
    # 주기 확인 — n날 프로펠러는 360/n 회전에 형상이 **집합으로** 불변이어야 한다.
    # ⚠ 원소별 비교는 안 된다: 180° 회전은 정점 i 를 반대편 날의 대응점으로 보내므로
    #   배열 순서가 그대로여도 좌표는 다르다. 최근접점 거리(집합 일치)로 봐야 옳다.
    per = 360.0 / max(1, int(spec.prop_blades))
    Vp = np.asarray(posed_mesh(spec, per).v, float)
    dper = None
    if Vp.shape == V0.shape:
        try:
            from scipy.spatial import cKDTree
            dper = float(cKDTree(V0).query(Vp)[0].max())
        except Exception:
            dper = float(np.abs(Vp - V0).max())

    # ⭐ 그 다음 — Sionna 에 넣었을 때 **h 가 실제로 바뀌는가** (같은 시드로 짝지어)
    rtc = {}
    for spp in (32_000_000, 256_000_000):
        got = []
        for ph, tg in zip(phases, ("B0", "B1")):
            sc, _, dd = build_posed_scene(spec, float(ph), tg)
            g2 = id_to_group(sc, spec.key)
            place(sc)
            got.append(rt_echo(sc, spp, 1, diffuse=True, id2grp=g2))
            drop_scratch(dd)
        r0, r1 = got
        def _d(k):
            return (None if (r0.get(k) is None or r1.get(k) is None)
                    else float(r1[k] - r0[k]))
        rtc[str(spp)] = dict(
            spp=int(spp), phases_deg=[float(x) for x in phases],
            n_paths=[int(r0["n_paths"]), int(r1["n_paths"])],
            amp_db=[r0["amp_db"], r1["amp_db"]], amp_db_delta=_d("amp_db"),
            n_prop=[int(r0["n_prop"]), int(r1["n_prop"])],
            prop_amp_db=[r0["prop_amp_db"], r1["prop_amp_db"]],
            prop_amp_db_delta=_d("prop_amp_db"),
            changed=bool((r0["n_paths"] != r1["n_paths"]) or
                         (r0["amp_db"] is not None and r1["amp_db"] is not None and
                          abs(r1["amp_db"] - r0["amp_db"]) > 1e-6)))
    return dict(signatures=sigs, period_deg=float(per), rt_check=rtc,
                rt_changed=bool(any(v["changed"] for v in rtc.values())),
                period_max_dev_m=dper,
                period_symmetry_ok=bool(dper is not None and dper < 1e-6),
                hash_differs=bool(sigs[0]["sha1"] != sigs[1]["sha1"]),
                same_vertex_count=bool(same_n),
                max_shift_m=float(d.max()) if d.size else None,
                max_shift_lambda=float(d.max() / LAM) if d.size else None,
                max_roundtrip_phase_deg=(float(360.0 * 2.0 * d.max() / LAM) if d.size else None),
                mean_shift_m=float(d.mean()) if d.size else None,
                n_moved_vertices=int(np.count_nonzero(d > 1e-9)) if d.size else None,
                max_shift_by_group_m=moved,
                note=("최대이동을 λ 로 나눈 값이 위상변조의 '있을 수 있는 크기'다. "
                      "왕복 위상 = 360°·2·Δ/λ."))


# --------------------------------------------------------------------------- #
#  §S — 어느 자세에 경로가 있나 (정반사 전용 / 생산재질)
# --------------------------------------------------------------------------- #
def sec_S_aspect(spec, spp=256_000_000, az_list=None, el_list=None, phases=(0.0, 45.0)):
    """자세 격자 × 로터위상 2개로 **경로 존재 여부**를 센다.

    두 채널을 따로 센다:
      · spec 채널 (diffuse_reflection=False) — 결정론적 정반사. facet_count 가 '36 중 1' 이라 한 것.
      · prod 채널 (diffuse_reflection=True)  — 생산 재질(확산 포함). 몬테카를로.
    ⭐ 위상을 2개 쓰는 이유: 정반사 조건은 블레이드 방위에 따라 켜졌다 꺼진다. 위상 하나로
      스캔하면 '이 자세엔 정반사가 없다'가 자세 탓인지 위상 탓인지 갈리지 않는다."""
    az_list = list(az_list if az_list is not None else np.arange(0.0, 360.0, 30.0))
    el_list = list(el_list if el_list is not None else (0.0, 15.0, 30.0, 45.0, 60.0, 90.0))
    rows = []
    for ph in phases:
        scene, _, d = build_posed_scene(spec, float(ph), f"S{int(round(ph)):03d}")
        g2 = id_to_group(scene, spec.key)
        for el in el_list:
            for az in az_list:
                place(scene, az=az, el=el)
                rs = rt_echo(scene, spp, 1, diffuse=False, id2grp=g2)
                rp = rt_echo(scene, spp, 1, diffuse=True, id2grp=g2)
                rows.append(dict(phase_deg=float(ph), az_deg=float(az), el_deg=float(el),
                                 spec_n=int(rs["n_paths"]), spec_amp_db=rs["amp_db"],
                                 spec_incoh_db=rs["incoh_db"],
                                 prod_n=int(rp["n_paths"]), prod_amp_db=rp["amp_db"],
                                 prod_incoh_db=rp["incoh_db"]))
        drop_scratch(d)
    n_asp = len(az_list) * len(el_list)
    spec_hit = [r for r in rows if r["spec_n"] > 0]
    asp_any = {(r["az_deg"], r["el_deg"]) for r in spec_hit}
    best = max(rows, key=lambda r: (r["spec_n"], r["spec_incoh_db"] or -1e9)) if rows else None
    return dict(spp=int(spp), az_deg=az_list, el_deg=el_list, phases_deg=list(phases),
                n_aspects=n_asp, n_rows=len(rows),
                n_aspect_with_specular=len(asp_any),
                frac_aspect_with_specular=float(len(asp_any) / max(1, n_asp)),
                n_rows_with_specular=len(spec_hit),
                n_rows_with_prod=int(sum(1 for r in rows if r["prod_n"] > 0)),
                hot_aspect=(dict(az_deg=best["az_deg"], el_deg=best["el_deg"],
                                 phase_deg=best["phase_deg"], spec_n=best["spec_n"])
                            if best and best["spec_n"] > 0 else None),
                rows=rows,
                note=("spec 채널이 비어 있으면 '정반사 에코 자체가 없다' 는 뜻이고, "
                      "그 경우 위상 스텝이 흔들 수 있는 것은 확산(몬테카를로) 채널뿐이다."))


# --------------------------------------------------------------------------- #
#  §C — ⭐⭐ 재추적 잡음바닥
# --------------------------------------------------------------------------- #
def sec_C_noise(spec, n_repeat=32, spps=(4_000_000, 32_000_000, 256_000_000),
                modes=(("spec", False), ("prod", True)), max_depth=1,
                az=AZ_DEG, el=EL_DEG):
    """**아무것도 움직이지 않고** 같은 씬을 n_repeat 번 다시 추적한다.

    · 시드를 바꿔가며(1..n) — Sionna 경로탐색의 확률성이 그대로 드러난다.
    · spp 를 여러 단계로 — 바닥이 광선예산에 따라 어떻게 변하는지.
    · 추가로 **같은 시드 재실행**(결정성)과 **씬 재조립 후 같은 시드**(재조립 영향)를 잰다.
      이 둘이 0 이 아니면 시드 산포마저 해석이 달라진다."""
    scene, _, dpath = build_posed_scene(spec, 0.0, "C")
    g2 = id_to_group(scene, spec.key)
    geo = place(scene, az=az, el=el)
    out = dict(geometry=geo, n_repeat=int(n_repeat), max_depth=int(max_depth), modes={})
    for mname, diff in modes:
        lv = {}
        for spp in spps:
            runs = [rt_echo(scene, spp, seed=s, max_depth=max_depth, diffuse=diff, id2grp=g2)
                    for s in range(1, n_repeat + 1)]
            sp = spread(runs)
            rep = rt_echo(scene, spp, seed=1, max_depth=max_depth, diffuse=diff, id2grp=g2)
            det = dict(amp_db_delta=(None if (rep["amp_db"] is None or runs[0]["amp_db"] is None)
                                     else float(rep["amp_db"] - runs[0]["amp_db"])),
                       n_paths_delta=int(rep["n_paths"] - runs[0]["n_paths"]),
                       reproducible=bool(rep["n_paths"] == runs[0]["n_paths"] and
                                         (rep["amp_db"] is None or runs[0]["amp_db"] is None or
                                          abs(rep["amp_db"] - runs[0]["amp_db"]) < 1e-4)))
            lv[str(spp)] = dict(spp=int(spp), spread=sp, determinism=det,
                                runs=[_thin(r) for r in runs])
            s_ = sp
            f = lambda k, fmt="%.3f": (fmt % s_[k]) if s_.get(k) is not None else "n/a"   # noqa: E731
            pr = sp["prop"]
            g = lambda k, fmt="%.3f": (fmt % pr[k]) if pr.get(k) is not None else "n/a"   # noqa: E731
            print(f"    [{spec.key}/{mname}] spp={spp:>12,}  paths "
                  f"{s_['n_paths_mean']:7.1f}±{s_['n_paths_std']:6.2f}  |h| "
                  f"{f('amp_db_mean', '%.2f'):>8} dB  σ={f('amp_db_std'):>7}  "
                  f"ptp={f('amp_db_ptp'):>7} dB  φσ="
                  f"{('%.1f' % s_['phase']['circ_std_deg']) if s_.get('phase') else 'n/a':>6}°  "
                  f"Σ|a|² σ={f('incoh_db_std'):>6}  ‖ prop n={pr['n_paths_mean']:6.1f} "
                  f"|h|={g('amp_db_mean', '%.2f'):>8} σ={g('amp_db_std'):>7}"
                  f"  [{s_['sec_total']:.0f}s]", flush=True)
        out["modes"][mname] = dict(diffuse=bool(diff), by_spp=lv)

    spp_ref = int(spps[-1])
    scene2, _, d2 = build_posed_scene(spec, 0.0, "C2")
    g2b = id_to_group(scene2, spec.key)
    place(scene2, az=az, el=el)
    rb = {}
    for mname, diff in modes:
        r1 = rt_echo(scene, spp_ref, seed=1, max_depth=max_depth, diffuse=diff, id2grp=g2)
        r2 = rt_echo(scene2, spp_ref, seed=1, max_depth=max_depth, diffuse=diff, id2grp=g2b)
        rb[mname] = dict(amp_db_a=r1["amp_db"], amp_db_b=r2["amp_db"],
                         amp_db_delta=(None if (r1["amp_db"] is None or r2["amp_db"] is None)
                                       else float(r2["amp_db"] - r1["amp_db"])),
                         n_paths_a=int(r1["n_paths"]), n_paths_b=int(r2["n_paths"]))
    out["scene_rebuild_same_phase"] = dict(
        spp=spp_ref, by_mode=rb,
        note=("같은 위상으로 OBJ 를 다시 쓰고 씬을 다시 조립해도 같은 값인가 — "
              "0 이어야 '위상 스텝의 차이 = 기하의 차이' 라고 말할 수 있다."))
    drop_scratch(dpath); drop_scratch(d2)
    return out


# --------------------------------------------------------------------------- #
#  §D — 로터 위상 스텝 → h(φ)
# --------------------------------------------------------------------------- #
def sec_D_sweep(spec, n_steps=16, seeds=(1, 2, 3), spp=256_000_000,
                modes=(("spec", False), ("prod", True)), max_depth=1,
                az=AZ_DEG, el=EL_DEG, verbose=True):
    """φ ∈ [0, 360/n_blades) 를 n_steps 로 나눠 **매 스텝 씬을 다시 만들고 다시 추적**한다.

    2날 프로펠러는 180° 주기다(형상 불변). 위상마다 seeds 개씩 돌려
      · 위상간 변동(신호 후보)  vs  위상내 시드 변동(잡음)
    을 **같은 축에서** 비교한다. 이 비교 없이는 어떤 변동도 해석할 수 없다.
    시드 목록을 **모든 위상에 똑같이** 쓰므로 짝지은(paired) 분석도 가능하다."""
    period = 360.0 / max(1, int(spec.prop_blades))
    phis = np.linspace(0.0, period, int(n_steps), endpoint=False)
    res = {m: [] for m, _ in modes}
    t0 = time.time()
    for i, ph in enumerate(phis):
        scene, _, d = build_posed_scene(spec, float(ph), f"D{i:03d}")
        g2 = id_to_group(scene, spec.key)
        geo = place(scene, az=az, el=el)
        for mname, diff in modes:
            runs = [rt_echo(scene, spp, seed=s, max_depth=max_depth, diffuse=diff, id2grp=g2)
                    for s in seeds]
            res[mname].append(dict(step=i, phase_deg=float(ph), spread=spread(runs),
                                   runs=[_thin(r) for r in runs]))
        drop_scratch(d)
        if verbose:
            line = f"    [{spec.key}] φ={ph:7.3f}°"
            for mname, _ in modes:
                s_ = res[mname][-1]["spread"]
                pr = s_["prop"]
                line += (f"  {mname}: n={s_['n_paths_mean']:6.1f} |h|="
                         f"{('%.2f' % s_['amp_db_mean']) if s_['amp_db_mean'] is not None else '  n/a':>8}"
                         f" | prop n={pr['n_paths_mean']:6.1f} |h|="
                         f"{('%.2f' % pr['amp_db_mean']) if pr['amp_db_mean'] is not None else '  n/a':>8}")
            print(line, flush=True)
    return dict(period_deg=float(period), n_steps=int(n_steps), spp=int(spp),
                seeds=[int(s) for s in seeds], max_depth=int(max_depth),
                geometry=geo, seconds=float(time.time() - t0),
                by_mode={m: res[m] for m, _ in modes})


def judge(rows, noise_spread, channel="all") -> dict:
    """⭐ 판정 — 위상 변동이 **잡음바닥보다 유의하게 큰가**.

    · 위상별 대표값 = 그 위상의 시드평균 |h| dB
    · 잡음바닥      = §C 의 같은 spp·같은 채널 시드 산포 σ_noise
    · 검정 ①       : 일원분산분석 F = 위상간 분산 / 위상내 분산 (자유도·p 함께)
    · 검정 ②       : ptp(위상평균) > 3 × σ_noise/√S  (S = 위상당 시드 수)
    · 짝지은 관점  : 같은 시드 안에서 위상축의 ptp — 시드 재추첨 없이 기하만 바뀐 경우
    channel="prop" 이면 **프로펠러를 맞은 경로만**으로 같은 계산을 한다."""
    def sub(sp):
        return sp["prop"] if channel == "prop" else sp
    k_amp = "prop_amp_db" if channel == "prop" else "amp_db"

    valid = [r for r in rows if sub(r["spread"]).get("amp_db_mean") is not None]
    n_ph = len(valid)
    npaths = np.array([sub(r["spread"])["n_paths_mean"] for r in rows], float)
    zero_ph = int(np.sum(npaths == 0))
    behaviour = ("모든 위상에서 경로 0 (경로 없음)" if (len(npaths) and zero_ph == len(npaths))
                 else ("껐다켜짐 (경로수가 0 을 오간다)" if zero_ph > 0
                       else "연속 (모든 위상에 경로 존재)"))
    base = dict(channel=channel, n_phase_total=len(rows), n_phase_with_paths=n_ph,
                n_paths_by_phase=[float(x) for x in npaths],
                n_paths_mean=float(npaths.mean()) if npaths.size else 0.0,
                n_paths_ptp=float(npaths.max() - npaths.min()) if npaths.size else 0.0,
                n_paths_cv=(float(npaths.std(ddof=1) / npaths.mean())
                            if npaths.size > 1 and npaths.mean() > 0 else None),
                n_phase_with_zero_paths=zero_ph, n_paths_behaviour=behaviour)
    if n_ph < 3:
        return dict(base, ok=False, modulation_above_noise=False,
                    reason="유효 위상 수 부족 — 변조를 논할 수 없다",
                    verdict="판정 불가(경로 없음)")

    means = np.array([sub(r["spread"])["amp_db_mean"] for r in valid], float)
    cmean = np.array([sub(r["spread"])["complex_mean_abs_db"] for r in valid], float)
    per = [[x[k_amp] for x in r["runs"] if x.get(k_amp) is not None] for r in valid]
    per = [g for g in per if g]
    k = len(per); nn = sum(len(g) for g in per)
    grand = float(np.mean([v for g in per for v in g]))
    ss_b = float(sum(len(g) * (np.mean(g) - grand) ** 2 for g in per))
    ss_w = float(sum(float(np.sum((np.asarray(g) - np.mean(g)) ** 2)) for g in per))
    df_b, df_w = k - 1, nn - k
    if df_w > 0 and ss_w > 0:
        F = (ss_b / df_b) / (ss_w / df_w)
    elif ss_b <= 1e-30:
        F = 0.0                       # 위상간·위상내 둘 다 변동이 없다 → 변조 없음
    else:
        F = float("inf")              # 위상내 변동만 0 → 형식상 무한대
    p = None
    try:
        from scipy.stats import f as _fd
        p = (float(_fd.sf(F, df_b, df_w)) if (np.isfinite(F) and df_w > 0)
             else (1.0 if F == 0.0 else 0.0))
    except Exception:
        pass

    seed_ids = sorted({x["seed"] for r in valid for x in r["runs"]})
    paired = {}
    for sd in seed_ids:
        v = [next((x[k_amp] for x in r["runs"]
                   if x["seed"] == sd and x.get(k_amp) is not None), None) for r in valid]
        v = [x for x in v if x is not None]
        if len(v) >= 3:
            paired[str(sd)] = dict(ptp_db=float(max(v) - min(v)),
                                   std_db=float(np.std(v, ddof=1)))

    S = max(1, int(round(nn / max(1, k))))
    within = float(math.sqrt(ss_w / df_w)) if df_w > 0 else None
    nsp = sub(noise_spread) if noise_spread else None
    n_std = nsp.get("amp_db_std") if nsp else None
    n_ptp = nsp.get("amp_db_ptp") if nsp else None
    ref = n_std if n_std else within
    se = (ref / math.sqrt(S)) if ref else None
    sig_ptp = float(means.max() - means.min())
    ratio_se = (sig_ptp / se) if (se and se > 0) else (0.0 if sig_ptp == 0.0 else None)
    ratio_raw = (sig_ptp / ref) if (ref and ref > 0) else (0.0 if sig_ptp == 0.0 else None)
    ok3 = bool(ratio_se is not None and ratio_se > 3.0)
    okF = bool(p is not None and p < 1e-3 and sig_ptp > 0.0)
    return dict(
        base, ok=True,
        phase_deg=[float(r["phase_deg"]) for r in valid],
        phase_mean_amp_db=[float(x) for x in means],
        phase_cmean_amp_db=[float(x) for x in cmean],
        phase_cmean_ptp_db=float(cmean.max() - cmean.min()),
        modulation_ptp_db=sig_ptp, modulation_std_db=float(means.std(ddof=1)),
        within_phase_std_db=within, seeds_per_phase=S,
        noise_floor_std_db=(float(n_std) if n_std is not None else None),
        noise_floor_ptp_db=(float(n_ptp) if n_ptp is not None else None),
        noise_se_db=(float(se) if se else None),
        ptp_over_noise_std=ratio_raw, ptp_over_noise_se=ratio_se,
        anova=dict(F=float(F), df_between=int(df_b), df_within=int(df_w), p_value=p),
        paired_by_seed=paired,
        modulation_above_noise=bool(ok3 and okF),
        verdict=("유의 — 위상 변동이 잡음바닥을 넘는다" if (ok3 and okF)
                 else ("경계 — 한 검정만 통과" if (ok3 or okF)
                       else "잡음바닥과 구별 안 됨")))


# --------------------------------------------------------------------------- #
#  기체별 물리 파라미터 (⛔ 손입력 금지 — 전부 계산)
# --------------------------------------------------------------------------- #
def airframe_physics(spec, n_steps_used: int) -> dict:
    m = build_drone(spec)
    V = np.asarray(m.v, float)
    b0, b1 = V.min(axis=0), V.max(axis=0)
    D_h = float(max(b1[0] - b0[0], b1[1] - b0[1]))            # 최대 수평 크기(프롭 포함)
    D_3 = float(np.linalg.norm(b1 - b0))                       # 3차원 대각(보수적 D)
    rpm = float(getattr(spec, "hover_rpm", 6000.0))
    omega = 2.0 * math.pi * rpm / 60.0
    prop_R = float(spec.prop_dia_mm) / 1000.0 / 2.0
    v_tip = omega * prop_R
    f_tip = 2.0 * v_tip / LAM                                  # 최대 마이크로도플러 [Hz]
    blades = int(spec.prop_blades)
    flash = blades * rpm / 60.0                                # 블레이드 플래시율 [Hz]
    period_deg = 360.0 / blades
    n_min_exact = 2.0 * f_tip / flash                          # 나이퀴스트 하한(실수)
    prf_eff = float(n_steps_used) * flash
    ff = 2.0 * D_h * D_h / LAM
    #  스텝 수 후보마다 접힘 여부 — 지시받은 16 과 실제로 쓴 값을 **나란히** 남긴다.
    alias_tbl = {}
    for N in sorted({16, 32, int(n_steps_used)}):
        alias_tbl[str(N)] = dict(
            n_steps=int(N), equivalent_prf_hz=float(N) * flash,
            aliased=bool(float(N) * flash < 2.0 * f_tip),
            margin=float(float(N) * flash / (2.0 * f_tip)),
            tip_travel_per_step_lambda=float(prop_R * math.radians(period_deg / N) / LAM))
    return dict(
        drone=spec.key, name=spec.name, fc_hz=FC, lambda_m=LAM,
        D_horizontal_m=D_h, D_diag3d_m=D_3, span_m=[float(x) for x in (b1 - b0)],
        diagonal_spec_mm=float(spec.diagonal_mm),
        farfield_m=ff, farfield_diag3d_m=2.0 * D_3 * D_3 / LAM,
        range_m=RANGE_M, range_over_farfield=RANGE_M / ff,
        in_farfield=bool(RANGE_M >= ff),
        n_rotors=int(spec.num_rotors), prop_blades=blades,
        prop_dia_mm=float(spec.prop_dia_mm), prop_radius_m=prop_R,
        hover_rpm=rpm, omega_rad_s=omega, v_tip_ms=v_tip, v_tip_mach=v_tip / 343.0,
        f_tip_hz=f_tip, f_tip_at_el_hz=f_tip * math.cos(math.radians(EL_DEG)),
        flash_hz=flash, phase_period_deg=period_deg, prf_min_hz=2.0 * f_tip,
        n_steps_used=int(n_steps_used),
        n_steps_min_for_nyquist=int(math.ceil(n_min_exact)),
        n_steps_min_exact=float(n_min_exact),
        equivalent_prf_hz=prf_eff, aliased=bool(prf_eff < 2.0 * f_tip),
        alias_margin=float(prf_eff / (2.0 * f_tip)), alias_by_n_steps=alias_tbl,
        tip_travel_per_step_m=float(prop_R * math.radians(period_deg / max(1, n_steps_used))),
        tip_travel_per_step_lambda=float(prop_R * math.radians(period_deg /
                                                              max(1, n_steps_used)) / LAM),
        note_ko=("위상 N 스텝 = 한 주기(=%.0f°)를 N 등분 → 등가 슬로타임 샘플률 N·f_flash. "
                 "f_tip 을 접지 않으려면 N ≥ 2·f_tip/f_flash = %.1f 이어야 한다." %
                 (period_deg, n_min_exact)))


# --------------------------------------------------------------------------- #
def _verdicts(sweep, noise, sweep_spp, label) -> dict:
    """모드별 판정 + **16 스텝 부분표본** 판정을 한꺼번에. (지시받은 16 스텝과 실제 스텝 수가
    다를 때, 둘 다 인용할 수 있게 남긴다 — 숫자를 손으로 고르지 않기 위해)"""
    out = {}
    for mname, rows in sweep["by_mode"].items():
        byspp = noise["modes"][mname]["by_spp"]
        kk = (str(sweep_spp) if str(sweep_spp) in byspp
              else min(byspp, key=lambda s: abs(int(s) - sweep_spp)))
        nf = byspp[kk]["spread"]
        for ch in ("all", "prop"):
            v = judge(rows, nf, channel=ch)
            v.update(noise_floor_spp=int(kk), matched_spp=bool(int(kk) == sweep_spp),
                     aspect=dict(az_deg=sweep["geometry"]["az_deg"],
                                 el_deg=sweep["geometry"]["el_deg"]), label=label)
            n = len(rows)
            if n >= 32 and n % 16 == 0:            # 32 스텝 → 격간 추출로 16 스텝 판정
                v16 = judge(rows[:: n // 16], nf, channel=ch)
                v["subsample_16step"] = {k: v16[k] for k in
                                         ("modulation_ptp_db", "modulation_above_noise",
                                          "verdict", "n_paths_behaviour", "anova")
                                         if k in v16}
            out[f"{mname}/{ch}"] = v
            f = lambda k: ("%.3f" % v[k]) if v.get(k) is not None else "n/a"   # noqa: E731
            print(f"      [{label}/{mname}/{ch}] n̄={v.get('n_paths_mean', 0):.1f} "
                  f"위상변동 ptp={f('modulation_ptp_db'):>8} dB  "
                  f"잡음 σ={f('noise_floor_std_db'):>7} dB  "
                  f"F={v.get('anova', {}).get('F', float('nan')):.3g}  "
                  f"→ {v.get('verdict')}  | 경로수: {v.get('n_paths_behaviour')}", flush=True)
    return out


def headline(R: dict) -> dict:
    """⭐ 한 기체의 **인용 가능한 요약** — 소비자가 손으로 숫자를 고르지 않게 여기서 정한다.

    규약(자의적 선택을 코드에 박아 둔다):
      · noise_floor_db  = 기준자세 · prod(생산재질) · **최고 spp** · all 채널의 σ(|h| dB)
        (prod 를 쓰는 이유: spec 채널은 대개 경로가 없어 σ 를 정의할 수 없다.)
      · modulation_above_noise = **어느 한 채널이라도** 두 검정을 모두 통과했나
      · n_paths_behaviour = all 채널(기준자세·prod)의 위상별 경로수 거동
    """
    ph = R["physics"]
    prod = R["C_noise"]["modes"]["prod"]["by_spp"]
    top = max(prod, key=lambda s: int(s))
    sp = prod[top]["spread"]
    V = R.get("verdict", {})
    any_sig = sorted([k for k, v in V.items() if v.get("modulation_above_noise")])
    any_sig_hot = sorted([k for k, v in (R.get("verdict_hot") or {}).items()
                          if v.get("modulation_above_noise")])
    return dict(
        drone=ph["drone"], f_tip_hz=ph["f_tip_hz"], farfield_m=ph["farfield_m"],
        in_farfield_at_3m=ph["in_farfield"],
        n_steps_min_for_nyquist=ph["n_steps_min_for_nyquist"],
        aliased_at_16_steps=ph["alias_by_n_steps"]["16"]["aliased"],
        rotor_step_changes_scene=bool(R["B_mesh"]["hash_differs"] and R["B_mesh"]["rt_changed"]),
        mesh_hash_differs=bool(R["B_mesh"]["hash_differs"]),
        rt_h_changes=bool(R["B_mesh"]["rt_changed"]),
        noise_floor_db=sp.get("amp_db_std"), noise_floor_spp=int(top),
        noise_floor_ptp_db=sp.get("amp_db_ptp"),
        noise_floor_phase_std_deg=(sp["phase"] or {}).get("circ_std_deg"),
        noise_floor_n_paths_std=sp.get("n_paths_std"),
        noise_floor_prop_db=sp["prop"].get("amp_db_std"),
        noise_floor_incoh_db=sp.get("incoh_db_std"),
        specular_channel_empty_at_ref=bool(
            R["C_noise"]["modes"]["spec"]["by_spp"][top]["spread"]["n_paths_mean"] == 0),
        frac_aspect_with_specular=(R.get("S_aspect") or {}).get("frac_aspect_with_specular"),
        modulation_above_noise=bool(any_sig or any_sig_hot),
        channels_significant=any_sig, channels_significant_hot=any_sig_hot,
        n_paths_behaviour=(V.get("prod/all") or {}).get("n_paths_behaviour"),
        n_paths_behaviour_prop=(V.get("prod/prop") or {}).get("n_paths_behaviour"),
        modulation_ptp_db=(V.get("prod/all") or {}).get("modulation_ptp_db"),
        modulation_ptp_db_prop=(V.get("prod/prop") or {}).get("modulation_ptp_db"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drones", default=",".join(KEYS))
    ap.add_argument("--repeat", type=int, default=32)
    #  ⭐ 32 스텝을 기본으로 둔다 — matrice4e 는 f_tip/f_flash 비가 커서 16 스텝이 **접힌다**
    #     (physics.alias_by_n_steps 참조). 32 로 돌리고 격간 추출로 16 스텝 판정도 함께 낸다.
    ap.add_argument("--steps", type=int, default=32)
    ap.add_argument("--sweep-seeds", type=int, default=8)
    ap.add_argument("--sweep-spp", type=int, default=256_000_000)
    ap.add_argument("--spps", default="4000000,32000000,256000000")
    ap.add_argument("--aspect-spp", type=int, default=256_000_000)
    ap.add_argument("--no-aspect", action="store_true")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    os.makedirs(SCRATCH, exist_ok=True)
    spps = tuple(int(x) for x in a.spps.split(",") if x.strip())
    if a.quick:
        spps = spps[:2]; a.repeat = min(a.repeat, 6); a.steps = min(a.steps, 4)
        a.sweep_seeds = min(a.sweep_seeds, 2)

    t_all = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_probe.py",
        question=("① Paths.doppler 로 자동으로 나오나(=아니다, 재확인) / "
                  "② 로터 위상 스텝 + 재추적으로 h(t) 를 이어붙이면 나오나(=열린 질문)"),
        observable=("h = Σ_p a_p·exp(−j2πf_c·τ_p)  — Paths.a 는 패스밴드라 위상이 없다. "
                    "Paths.cir() 은 normalize_delays=True 로 절대위상을 지우므로 쓰지 않았다."),
        fc_hz=FC, lambda_m=LAM, az_deg=AZ_DEG, el_deg=EL_DEG,
        range_m=RANGE_M, baseline_m=BASELINE_M, max_paths=MAX_PATHS, max_depth=1,
        n_repeat_noise=int(a.repeat), n_phase_steps=int(a.steps),
        sweep_seeds=int(a.sweep_seeds), sweep_spp=int(a.sweep_spp), spps=list(spps),
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        materials="production per-group (DRONE_GROUP_MAT)",
        prior="WiFi-JEPA arXiv:2607.11064 — frame 당 20 pass 로 시간축 생성",
        related="outputs/facet_count.json (정지자세 정반사 통계)",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")), airframes={})

    def _save():
        with open(OUT_JSON, "w") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)

    for key in [k.strip() for k in a.drones.split(",") if k.strip()]:
        spec = DRONES[key]
        print(f"\n══ {key} ({spec.name}) ══", flush=True)
        R = dict(physics=airframe_physics(spec, a.steps))
        ph = R["physics"]
        print(f"  D={ph['D_horizontal_m']:.3f} m  2D²/λ={ph['farfield_m']:.3f} m "
              f"(R={RANGE_M} m → far-field {'OK' if ph['in_farfield'] else '미달'})"
              f"   f_tip={ph['f_tip_hz']:.0f} Hz  flash={ph['flash_hz']:.1f} Hz  "
              f"N_min={ph['n_steps_min_for_nyquist']} (쓰는 값 {a.steps}"
              f"{' → 접힘!' if ph['aliased'] else ''})", flush=True)

        print("  §A  Paths.doppler 재확인 …", flush=True)
        R["A_doppler"] = sec_A_doppler(spec)
        print(f"      velocity 자유도/객체 = {R['A_doppler']['max_dof']}  "
              f"(정지 씬 doppler≠0 경로 {R['A_doppler']['static']['doppler_nonzero']}개, "
              f"프롭 강체속도 → 서로 다른 도플러 "
              f"{R['A_doppler']['rigid_prop_velocity']['n_distinct_doppler']}종)", flush=True)

        print("  §B  위상 스텝이 메쉬를 바꾸는가 …", flush=True)
        R["B_mesh"] = sec_B_mesh(spec)
        print(f"      해시 다름 = {R['B_mesh']['hash_differs']}  "
              f"최대이동 {R['B_mesh']['max_shift_m']:.4f} m = "
              f"{R['B_mesh']['max_shift_lambda']:.2f} λ  "
              f"(왕복 위상 {R['B_mesh']['max_roundtrip_phase_deg']:.0f}°)  "
              f"주기대칭 {R['B_mesh']['period_symmetry_ok']}  "
              f"→ Sionna h 도 바뀌나 = {R['B_mesh']['rt_changed']}", flush=True)

        if not a.no_aspect:
            print("  §S  자세 스캔 (어디에 정반사가 있나) …", flush=True)
            R["S_aspect"] = sec_S_aspect(spec, spp=a.aspect_spp,
                                         el_list=((0.0, 15.0, 30.0, 45.0, 60.0, 90.0)
                                                  if not a.quick else (0.0, 15.0)),
                                         az_list=(np.arange(0.0, 360.0, 30.0) if not a.quick
                                                  else np.arange(0.0, 360.0, 90.0)))
            s = R["S_aspect"]
            print(f"      정반사 있는 자세 {s['n_aspect_with_specular']}/{s['n_aspects']} "
                  f"({100*s['frac_aspect_with_specular']:.1f}%)  hot={s['hot_aspect']}", flush=True)

        print("  §C  ⭐ 재추적 잡음바닥 …", flush=True)
        R["C_noise"] = sec_C_noise(spec, n_repeat=a.repeat, spps=spps)

        print("  §D  로터 위상 스텝 …", flush=True)
        R["D_sweep"] = sec_D_sweep(spec, n_steps=a.steps,
                                   seeds=tuple(range(1, a.sweep_seeds + 1)),
                                   spp=a.sweep_spp)

        R["verdict"] = _verdicts(R["D_sweep"], R["C_noise"], a.sweep_spp, "기준자세")

        #  ⭐ 정반사가 살아 있는 자세에서도 똑같이 — "Sionna 에게 가장 유리한 조건" 을 한 번 더
        hot = (R.get("S_aspect") or {}).get("hot_aspect")
        if hot:
            print(f"  §C'/§D'  정반사 hot 자세 (az={hot['az_deg']}°, el={hot['el_deg']}°) 반복 …",
                  flush=True)
            R["C_noise_hot"] = sec_C_noise(spec, n_repeat=a.repeat, spps=spps[-1:],
                                           az=hot["az_deg"], el=hot["el_deg"])
            R["D_sweep_hot"] = sec_D_sweep(spec, n_steps=a.steps,
                                           seeds=tuple(range(1, a.sweep_seeds + 1)),
                                           spp=a.sweep_spp, az=hot["az_deg"], el=hot["el_deg"])
            R["verdict_hot"] = _verdicts(R["D_sweep_hot"], R["C_noise_hot"],
                                         a.sweep_spp, "hot 자세")
        R["headline"] = headline(R)
        J["airframes"][key] = R
        _save()

    J["meta"]["seconds_total"] = float(time.time() - t_all)
    _save()
    print(f"\n✅ 저장 → {OUT_JSON}   ({J['meta']['seconds_total']:.0f}s)")
    return J


if __name__ == "__main__":
    main()
