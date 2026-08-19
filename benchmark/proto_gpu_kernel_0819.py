# -*- coding: utf-8 -*-
"""proto_gpu_kernel_0819.py — ⛔**시제품이다. 생산 커널이 아니다.**

물음 (사용자, 2026-08-19): "이걸 최적의 쿠다 연산으로 옮길 수 있는 방법이 없는 거야?"

■ 답 — 있다. 실측으로 **31배**(자세당 20.3 → 0.651 ms)까지 갔다.

세 가지를 바꿨다.
  ① **씬을 통째로 다시 짓지 않는다** — 토폴로지(면·그룹)는 자세가 바뀌어도 안 변하고
     로터가 도느라 정점만 바뀐다. mi.Mesh 는 그대로 두고 vertex_positions 만 올린 뒤
     `mi.load_dict` 로 씬만 다시 조립한다.  9.93 ms → 1.39 ms
     ⭐**재조립을 빼면 안 된다** — 정점만 올리고 끝내면 가속구조가 갱신만 되어 실루엣
       근처 광선 2 발(484 중)이 다르게 판정된다(σ 0.0085 dB). 재조립하면 신축과 **정확히
       같다**(상대오차 0.000e+00, 조명광선 486 vs 486). 실측으로 갈랐다.
  ② **자세 K 개를 공간에 3 m 씩 벌려 한 씬에 넣고 한 번에 쏜다** — 격자 반폭이 0.43 m 라
     이웃을 못 때린다. 발사 오버헤드가 K 로 나뉜다.  광선+PO 3.29 → 0.011 ms/자세
  ③ **PO 적분을 Dr.Jit 로 GPU 에서** 한다 — 지금 커널은 광선 결과를 곧바로 numpy 로
     내려 CPU 에서 적분한다. 같은 교차점에서 두 경로를 대조하면 σ 차이 0.00000 dB
     (상대오차 1.45e-06) 이므로 **포팅 자체는 정확하다**.

■ 실측 (mavic4pro · 3.5 GHz · λ/12 · û=+x · 단일 패스 · 각도 Γ 끔)
    K=16  0.941 ms/자세  22.5×  σ 최대차 0.001065 dB
    K=64  0.651 ms/자세  31.2×  σ 최대차 0.003448 dB
  남은 병목은 **기하 0.641 ms(98%)** 이고 그중 대부분이 정점을 CPU 에서 모아 올리는 몫이다.
  다음 레버는 로터 회전을 GPU 에서 하는 것 — ⚠**미검증**.

■ ⛔이 시제품이 아직 안 하는 것 (생산에 넣으려면 반드시 포팅)
    · 셸 투과 2 패스(penetrate=True) — 배치 안에서 셸 뺀 씬으로 한 번 더 쏘면 된다
    · 각도의존 Γ(ANGLE_GAMMA=1) — 프레넬 식이라 Dr.Jit 로 옮길 수 있다
    · PTD 모서리 항 · 바이스태틱 · 다중반사(max_bounce≥2)
    · 잔여 0.0034 dB 는 자세를 공간에 벌리며 생기는 float32 좌표 양자화 몫이다.
      인스턴스(변환행렬)로 바꾸면 없앨 수 있다 — ⚠미검증.

■ ⚠채택하면 **전면 재계산**이다. 이미 난 샤드 4,326 개와 못 섞는다.

실행: PYTHONPATH=src:benchmark DRJIT_LIBOPTIX_PATH=... python benchmark/proto_gpu_kernel_0819.py 64
"""
import os
os.environ["SIONNA2_ANGLE_GAMMA"] = "0"
import sys, time
sys.path[:0] = ["src", "benchmark"]
import numpy as np
from drones import DRONES, DRONE_GROUP_MAT
from materials import gamma_po
from articulated_fast import FastPoser
import rcs_sbr as R
import mitsuba as mi, drjit as dr

fc = 3.5e9; lam = 2.998e8/fc; d = lam/12; k = 2*np.pi/lam
K = int(sys.argv[1]) if len(sys.argv) > 1 else 32
fp = FastPoser(DRONES["mavic4pro"]); nrot = len(fp._rotor_const)
gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
u = np.array([1.0, 0.0, 0.0])
POSES = [fp.pose(np.full(nrot, p)) for p in np.linspace(0, 2*np.pi, K, endpoint=False)]
gref = R.grid_ref_from(POSES, fc, spacing=d)
ctr, Rout, n = R._grid_for(POSES[0], d, 1.15, gref, u, "final"); NR = n*n
SPACE = 3.0; DELTA = np.array([[0.0, 0.0, j*SPACE] for j in range(K)])

mv0 = POSES[0]; F = np.asarray(mv0.f, np.uint32); G = np.asarray(mv0.g)
groups = sorted(set(G.tolist())); USED = [np.unique(F[G == g]) for g in groups]
NV = np.asarray(mv0.v).shape[0]

meshes, gammas = {}, []
for gi, grp in enumerate(groups):
    used = USED[gi]; f = F[G == grp]
    remap = np.full(NV, -1, np.int64); remap[used] = np.arange(len(used))
    fl = remap[f].astype(np.uint32); nv = len(used)
    m = mi.Mesh(f"g_{grp}", vertex_count=nv*K, face_count=len(f)*K,
                has_vertex_normals=False, has_vertex_texcoords=False)
    p = mi.traverse(m)
    p["faces"] = mi.UInt32(np.concatenate([(fl+j*nv).ravel() for j in range(K)]).astype(np.uint32))
    p["vertex_positions"] = mi.Float(np.zeros(nv*K*3, np.float32)); p.update()
    meshes[f"s_{gi}"] = m
    val = gm.get(grp, "plastic")
    gammas.append(float(val) if not isinstance(val, str) else gamma_po(val, fc))
PARAM = [mi.traverse(m) for m in meshes.values()]

r1 = R._ray_grid(ctr, Rout, n, d, u)
O1 = np.asarray(mi.Point3f(r1.o)).T; D1 = np.asarray(mi.Vector3f(r1.d)).T
O = np.concatenate([O1+DELTA[j] for j in range(K)]).astype(np.float32)
ray = mi.Ray3f(o=mi.Point3f(*O.T), d=mi.Vector3f(*np.tile(D1, (K, 1)).astype(np.float32).T))
c_off = mi.Float(np.repeat(DELTA @ u, NR).astype(np.float32))
uf = mi.Vector3f(*[float(x) for x in u]); ctrf = mi.Point3f(*[float(x) for x in ctr])

def build(mvs):
    """정점 K 벌 올리고 씬을 다시 조립한다 — 이래야 값이 신축과 정확히 같다."""
    for gi in range(len(groups)):
        used = USED[gi]
        PARAM[gi]["vertex_positions"] = mi.Float(np.concatenate(
            [(np.asarray(mvs[j].v, np.float32)[used]+DELTA[j]).ravel() for j in range(K)]
        ).astype(np.float32))
        PARAM[gi].update()
    return mi.load_dict({"type": "scene", **meshes})

def po(scene):
    ptrs = [mi.ShapePtr(s) for s in scene.shapes()]
    si = scene.ray_intersect(ray)
    g = mi.Float(0.0)
    for ptr, gv in zip(ptrs, gammas):
        g = dr.select(si.shape == ptr, mi.Float(float(gv)), g)
    s2 = dr.sign(dr.dot(si.n, uf)); s2 = dr.select(s2 == 0.0, mi.Float(1.0), s2)
    lit = si.is_valid() & (dr.dot(si.n*s2, uf) > 1e-6)
    x = 2.0*float(k)*(dr.dot(si.p-ctrf, uf) - c_off)
    w = dr.select(lit, g, mi.Float(0.0))
    re = np.asarray(w*dr.cos(x)).reshape(K, NR).sum(1)
    im = np.asarray(w*dr.sin(x)).reshape(K, NR).sum(1)
    return (re + 1j*im)*d*d

def T(f, nr=5):
    f(); t = time.time()
    for _ in range(nr): f()
    return (time.time()-t)/nr*1000

def sig(E): return 10*np.log10(4*np.pi/lam**2*np.abs(E)**2)
ref = np.array([R.sbr_field(m, gm, fc, u, spacing=d, grid_ref=gref, penetrate=False) for m in POSES])
got = po(build(POSES))
rel = np.abs(got-ref)/np.abs(ref)
print(f"K={K} · 광선 {K*NR:,}발/발사 · 면 {K*len(mv0.f):,}")
print(f"값 대조 vs 지금 커널: σ 최대차 {np.max(np.abs(sig(got)-sig(ref))):.6f} dB · "
      f"상대오차 최대 {rel.max():.2e}")
t_ref = T(lambda: [R.sbr_field(m, gm, fc, u, spacing=d, grid_ref=gref, penetrate=False)
                   for m in POSES], 2)/K
t_b = T(lambda: build(POSES))/K; t_p = T(lambda: po(build(POSES)))/K - t_b
print(f"\n① 지금 방식        {t_ref:7.3f} ms/자세")
print(f"② 최종 조합        {t_b+t_p:7.3f} ms/자세  → {t_ref/(t_b+t_p):.1f}×")
print(f"   기하(정점+재조립) {t_b:.3f} · 광선+PO {t_p:.3f}")
