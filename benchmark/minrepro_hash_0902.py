# -*- coding: utf-8 -*-
"""minrepro_hash_0902.py — «회절을 꺼도 경로가 사라진다» 의 **최소 재현기** (2026-09-02).

⭐**우리 저장소에 하나도 안 기댄다** — `numpy` · `mitsuba` · `sionna.rt` 뿐이다.
   남이 그대로 복사해 돌릴 수 있어야 뜻이 있다.

무엇을 보이나
-------------
같은 씬 객체 · 같은 솔버 객체 · **같은 씨앗** · 연속 호출인데
`PathSolver` 가 돌려주는 **경로 수가 흔들린다.** 회절은 꺼져 있다.

실측 (2026-09-02 · sionna 2.0.1 · 10 판씩):

    평판   삼각형  산란S   경로 수 종류                |h| 폭
      64    128   0.7   [454]                      0.0000 dB
     256    512   0.7   [1755, 1756]               1.0954 dB
     576   1152   0.7   [3997, 3998, 3999, 4000]   4.7089 dB   ⭐
    1024   2048   0.7   [7101]                     0.0000 dB
     576   1152   0.3   [758, 759, 760]            2.2585 dB
     576   1152   1.0   [8200]                     0.0000 dB

⚠흔들리는 칸과 안 흔들리는 칸이 있다 — 454·7101·8200 은 안 흔들리고 1755·3997·758 은
   흔들린다(경로가 **가장 많은** 7101·8200 이 0.0000 dB 인 것에 주의).
⛔**«해시 통이 겹쳐서» 로 읽지 않는다**(2026-09-03 반증). 통 수를 1M → 32M 로 **32 배**
   키워도 발생률이 0.367 → 0.533 으로 **안 줄고**, 최대 편차는 통 수와 무관하게 3.08419 dB
   로 **전부 같다**⟨outputs/hash_bucket_stat_0903.json⟩.
⭐손잡이는 **병렬 스레드 수**다 — 스레드 1 이면 40 판 전부 같은 값(발생률 0.0 · 경로 수도
   8059 하나)이고, 2 에서 0.025, 192 에서 0.35 로 오른다⟨outputs/thread_ladder_0903.json⟩.
⛔순정 씬(`simple_street_canyon`)으로는 재현이 안 된다 — 경로가 6 개뿐이고 재질
   산란계수가 0 이라 확산을 켜도 안 는다. 그때 |h| 폭은 **0.0008 dB**(부동소수점 수준)다.
   이 재현기의 4.7089 dB 는 그보다 **약 5,900 배**(dB 를 그대로 나눈 값) 크다.
   ⚠«2,700 배» 는 어느 읽기로도 안 나와 2026-09-04 에 고쳤다. ⚠대조군 0.0008 dB 는
   `outputs/` 에 원장이 없다 — 다시 돌려 원장을 남기기 전까지 **이 배수는 참고값**이다.

어디를 보나
-----------
`sionna/rt/path_solvers/sb_candidate_generator.py:480-500` — 정반사 사슬을 해시 통으로
중복제거하는데, `dr.scatter_inc` 로 통을 **먼저 올린 스레드만** 그 경로를 남긴다.
⛔**«그 자리에 race condition 이 주석으로 적혀 있다» 는 오독이었다**(2026-09-04). 원문은
   “**To avoid race conditions** where 2 threads increment first one of the counters …,
   it is important to use `new_specular` as the active mask.” — race 를 **인정하는** 글이
   아니라 **피하는 방법**을 적은 글이다. 업스트림이 스스로 인정한 유실 원인은 같은 파일
   43~45 행의 “loss of candidates due to **hash collisions**” 다.

⚠공개 논의 #1175 은 **회절 wedge**(RadioMapSolver) 이야기이고 `diffraction=False` 로
   사라진다. **이것은 회절을 꺼도 난다** — 자리가 다르다.

    CUDA_VISIBLE_DEVICES=3 DRJIT_LIBOPTIX_PATH=... LD_LIBRARY_PATH=... \
      ~/.venvs/py312/bin/python benchmark/minrepro_hash_0902.py
"""
import numpy as np

import mitsuba as mi                                          # noqa: E402
import sionna.rt as rt                                        # noqa: E402

FC = 3.5e9
SEED = 42


def plate_grid(n_side: int, pitch: float = 0.06, size: float = 0.045,
               jitter: float = 0.004, seed: int = 0):
    """작은 평판 n_side² 장을 격자로 깐 **하나의 mi.Mesh**.

    ⭐평판을 조금씩 어긋내는(jitter) 이유 — 완전히 같으면 경로가 «진짜로» 같아져
      중복제거가 맞는 일을 한다. 조금 다르면 **해시는 겹칠 수 있는데 경로는 다른**
      상황이 만들어진다. 그것이 우리가 재현하려는 자리다.
    """
    rng = np.random.default_rng(seed)
    V, F = [], []
    h = size / 2
    for i in range(n_side):
        for j in range(n_side):
            c = np.array([(i - n_side / 2) * pitch, (j - n_side / 2) * pitch, 0.0])
            c += rng.normal(0.0, jitter, 3)
            k = len(V)
            V += [c + [-h, -h, 0], c + [h, -h, 0], c + [h, h, 0], c + [-h, h, 0]]
            F += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
    V = np.asarray(V, np.float32); F = np.asarray(F, np.uint32)
    m = mi.Mesh("plates", vertex_count=V.shape[0], face_count=F.shape[0],
                has_vertex_normals=False, has_vertex_texcoords=False)
    p = mi.traverse(m)
    p["vertex_positions"] = mi.Float(V.ravel())
    p["faces"] = mi.UInt(F.ravel())
    p.update()
    return m, V.shape[0], F.shape[0]


def build(n_side, scat):
    """⭐**우리 저장소 모듈을 안 쓴다** — 순정 `sionna.rt` API 만으로 씬을 짓는다.
    그래야 남이 그대로 돌릴 수 있다."""
    m, nv, nf = plate_grid(n_side)
    sc = rt.load_scene()
    sc.frequency = FC
    mat = rt.RadioMaterial("plate_mat", relative_permittivity=3.0,
                           conductivity=0.01, scattering_coefficient=float(scat))
    sc.edit(add=[rt.SceneObject(name="plates", mi_mesh=m, radio_material=mat)])
    sc.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    sc.add(rt.Transmitter("tx", position=[0.0, 0.0, 15.0]))
    sc.add(rt.Receiver("rx", position=[0.0, 0.0, 15.0]))
    return sc, nf


def probe(sc, reps, **kw):
    solver = rt.PathSolver()
    KW = dict(max_depth=2, los=False, specular_reflection=True,
              diffuse_reflection=True, refraction=False,
              diffraction=False, edge_diffraction=False,
              samples_per_src=20_000_000, max_num_paths_per_src=1_000_000, seed=SEED)
    KW.update(kw)
    ns, hs = [], []
    for _ in range(reps):
        p = solver(sc, **KW)
        ar = np.array(p.a[0], copy=True).astype(np.float64)
        ai = np.array(p.a[1], copy=True).astype(np.float64)
        a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
        tau = np.array(p.tau, copy=True).astype(np.float64).reshape(-1, a.size)[0] \
            if a.size else np.zeros(0)
        ns.append(int(a.size))
        hs.append(abs(complex(np.sum(a * np.exp(-2j * np.pi * FC * tau)))) if a.size else 0.0)
    return ns, hs


def main():
    print("⭐최소 재현기 — 합성 평판 격자 · 회절 OFF · 씨앗 고정 · 같은 씬 객체 연속 호출\n")
    print(f"{'평판':>6}{'삼각형':>8}{'산란S':>7}{'판':>4}{'경로 수 종류':>28}{'|h| 폭 dB':>11}  판정")
    print("─" * 78)
    for n_side, scat in ((8, 0.7), (16, 0.7), (24, 0.7), (32, 0.7), (24, 0.3), (24, 1.0)):
        try:
            sc, nf = build(n_side, scat)
            ns, hs = probe(sc, 10)
        except Exception as e:                                 # noqa: BLE001
            print(f"{n_side**2:>6}{'—':>8}{scat:>7.1f}   ⛔{type(e).__name__}: {e}"[:110])
            continue
        u = sorted(set(ns))
        sp = 20 * np.log10(max(hs) / min(hs)) if min(hs) > 0 else float("nan")
        v = "⭐⭐경로 수가 흔들린다" if len(u) > 1 else ""
        print(f"{n_side**2:>6}{nf:>8}{scat:>7.1f}{len(ns):>4}{str(u):>28}{sp:>11.4f}  {v}")


if __name__ == "__main__":
    main()
