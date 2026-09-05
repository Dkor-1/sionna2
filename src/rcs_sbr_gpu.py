# -*- coding: utf-8 -*-
"""
rcs_sbr_gpu.py — SBR+PO 커널의 **GPU 판** (2026-08-20 저장소 이식)
================================================================================

⭐**옛 커널(`rcs_sbr.py`)을 그대로 둔 채 나란히 둔다.** 둘 다 살려 두므로 기존 샤드
   4,326 개가 그대로 유효하고, 새 계산만 이 판으로 낼 수 있다.
   ⛔산출 파일 이름에 **반드시 꼬리표**가 붙는다(`elevation_sweep_md.py --engine ours_gpu`
   → `oursgpu…`). 이름이 갈리므로 두 원장이 **절대 안 섞인다**.

무엇이 다른가 — 물리는 그대로, 계산 장소만 옮겼다
--------------------------------------------------
  ① PO 적분을 numpy(CPU) → Dr.Jit(GPU)
  ② 자세마다 씬 신축 → 정점만 올리고 `mi.load_dict` **재조립**
  ③ 자세 K 개를 û 에 수직인 평면 격자로 늘어놓고 한 번에 발사
  ④ 그룹별 정점 모으기를 numpy → `dr.gather`
  ⑤ 겉·속 씬이 메쉬 공유
  ⑥ 광선 다발을 방향마다 캐시
지금 판은 **K=1 로 못 박혀 있다**(`K_MAX_ALLOWED=1`, 아래 이유). 그 K=1 판의 mavic4pro 가속은
docs/OPT_STATUS_0820.md:46,90 이 **3.66 배**(σ 최대차 0.0009 dB 로 검증), docs/RESUME_0820.md:119
가 **4.6 배**로 적어 **두 문서의 수가 다르다** — 인용할 때 어느 문서 값인지 밝힐 것.
⛔「118 배(36.4 → 0.309 ms/자세)」는 **K=64** 에서 잰 값이라 지금 판의 생산 설정 값이 아니다.

⛔⛔**적대적 검증에서 드러난 것 — 반드시 읽을 것** (2026-08-20)
------------------------------------------------------------
  · **K≥2 는 쓰면 안 된다.** 자세를 묶으면 값이 «몇 번 슬롯에 앉았나» 에 매여
    **`--nshards` 를 탄다**(s1000plus el−60 에서 0.101 dB — 그 각도 밴드 0.02 dB 의 5 배).
    생산 길이(자세 512)에서 matrice4e 권장 K=8 이 **0.118~0.328 dB** 로 벌어졌다
    (원 README 가 낸 0.000652 의 180~500 배 — `k_scan` 이 자세 32 개만 보아 꼬리를 놓쳤다).
    ⇒ 이 판은 **K=1 로 못 박는다**(`K_MAX_ALLOWED`). 열려면 샤딩을 «K 배수 연속 블록» 으로
      바꾼 뒤 다시 검증해야 한다(그 배선이면 워커 분배를 바꿔도 0/512 비트 차이였다).
  · **원 판정선 0.06 dB 는 근거가 없다.** 인용된 `rcs_sbr.validate()` 에는 자세 루프가
    아예 없다(정지 표적 셋뿐). 이 판은 그 선을 **안 쓴다** — 판정은 하류 잣대로 한다.
  · **가드 둘이 빠져 있었다** → 아래에서 되살렸다(`SHELL_GAMMA_MAX`·`GRID_REF_CHECK`).
  · **안 옮긴 것**: PTD 모서리 프린지 · 바이스태틱 · 다중반사 · 격자 위상 널 ·
    ⭐**`jitter`**(옛 `rcs_sbr_batch(jitter≥2)`). 이 다섯이 필요한 팔은 **옛 커널로 돌린다.**
"""
from __future__ import annotations

import os
import subprocess
from typing import NamedTuple

import numpy as np


# --------------------------------------------------------------------------- #
#  GPU 고르기 — mitsuba 보다 **먼저** 해야 한다 (CUDA 문맥이 생기면 못 바꾼다)
# --------------------------------------------------------------------------- #
def pick_gpu(verbose: bool = False) -> str | None:
    """여유 메모리가 가장 많은 카드를 잡는다. 이미 정해져 있으면 그대로 둔다."""
    if os.environ.get("CUDA_VISIBLE_DEVICES"):
        return os.environ["CUDA_VISIBLE_DEVICES"]
    try:
        out = subprocess.run(
            "nvidia-smi --query-gpu=index,memory.total,memory.used "
            "--format=csv,noheader,nounits", shell=True, capture_output=True, text=True).stdout
        best, free_best = None, -1
        for line in out.strip().splitlines():
            i, tot, used = (int(x) for x in line.split(","))
            if tot - used > free_best:
                best, free_best = i, tot - used
        if best is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(best)
            if verbose:
                print(f"  GPU {best} 선택 (여유 {free_best} MiB)")
            return str(best)
    except Exception:                                        # noqa: BLE001
        pass
    return None


pick_gpu()

import mitsuba as mi                                          # noqa: E402
import drjit as dr                                            # noqa: E402

try:                       # 있으면 Sionna 와 **같은 변종**을 쓴다 (값이 갈리지 않게)
    import sionna.rt as _rt                                   # noqa: F401,E402
except Exception:                                             # noqa: BLE001
    if mi.variant() is None:
        try:
            mi.set_variant("cuda_ad_mono_polarized", "llvm_ad_mono_polarized")
        except ImportError:                                   # pragma: no cover
            mi.set_variant("llvm_ad_mono_polarized")

# ⭐저장소 정본 재질을 쓴다 — 동결본(materials_frozen.json)은 저장소 밖에서 돌 때만 필요했다.
#   여기서는 옛 커널과 **같은 표**를 봐야 값이 갈리지 않는다.
from materials import gamma_po, gamma_shape, material_params      # noqa: E402

C0 = 299792458.0
DEFAULT_DIV = 12                    # 격자 간격 = λ/DEFAULT_DIV (원본 규약)
DIELECTRIC_SHELLS = frozenset({"body", "canopy"})     # 투과시킬 유전체 셸 그룹


class Mesh(NamedTuple):
    """정점 v(N,3) · 면 f(M,3) · 면마다의 그룹 이름 g(M,). 저장소의 `geom.Mesh` 와 같은 꼴."""
    v: np.ndarray
    f: np.ndarray
    g: np.ndarray


# --------------------------------------------------------------------------- #
#  규약 함수 — `src/rcs_sbr.py` 의 `_grid_basis` · `_ray_grid` · `_grid_for` ·
#  `grid_ref_from` 과 **같은 식**이다. 베낀 것이므로 원본이 바뀌면 여기도 바꿔야 한다.
#  (verify.py 가 저장소를 볼 수 있을 때 두 판의 격자가 같은지 대조한다.)
# --------------------------------------------------------------------------- #
class GridRef(NamedTuple):
    ctr: np.ndarray
    Rout: float
    n: int
    spacing: float


def grid_basis(u):
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2


def ray_grid(ctr, Rout, n, d, u):
    """(ctr, Rout, n, d) 와 û 에서 **평행 광선 다발**(n² 발)."""
    t = (np.arange(n) - (n - 1) / 2.0) * d
    A, B = np.meshgrid(t, t, indexing="ij")
    e1, e2 = grid_basis(u)
    O = (ctr + Rout * u)[None, :] + A.ravel()[:, None] * e1 + B.ravel()[:, None] * e2
    D = np.tile(-u, (O.shape[0], 1))
    return mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                    d=mi.Vector3f(*D.T.astype(np.float32)))


def grid_for(mesh, d, pad=1.15, grid_ref=None):
    """이 호출이 쓸 격자 (ctr, Rout, n)."""
    if grid_ref is None:
        V = np.asarray(mesh.v, float)
        ctr = 0.5 * (V.max(0) + V.min(0))
        Rout = float(np.linalg.norm(V - ctr, axis=1).max()) * pad + 3 * d
        return ctr, Rout, int(np.ceil(2 * Rout / d))
    r = grid_ref
    if r.spacing is not None and abs(d - r.spacing) > 1e-9 * max(d, r.spacing):
        raise ValueError(f"grid_ref 의 격자 간격이 이 호출과 다르다 "
                         f"(ref {r.spacing*1e3:.6f} mm ↔ 지금 {d*1e3:.6f} mm) — "
                         f"n·Rout 은 d 에 매인 값이라 섞어 쓰면 덮개가 깨진다.")
    return np.asarray(r.ctr, float), float(r.Rout), int(r.n)


def grid_ref_from(meshes, fc: float, spacing=None, pad: float = 1.15) -> GridRef:
    """자세들의 **합집합 경계상자**로 얼린 격자 한 판을 만든다."""
    d = float(spacing) if spacing else (C0 / float(fc)) / DEFAULT_DIV
    items = [np.asarray(m.v, float) for m in (meshes if isinstance(meshes, (list, tuple))
                                              else [meshes])]
    lo = np.full(3, np.inf); hi = np.full(3, -np.inf)
    for V in items:
        lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
    ctr = 0.5 * (lo + hi)
    Rmax = max(float(np.linalg.norm(V - ctr, axis=1).max()) for V in items)
    Rout = Rmax * pad + 3 * d
    return GridRef(ctr=ctr, Rout=float(Rout), n=int(np.ceil(2 * Rout / d)), spacing=float(d))


#: ⭐옛 커널에서 되살린 가드 — 셸로 선언 가능한 |Γ| 상한 (플라스틱 0.28 ✓ / 카본 0.90 ✗)
#   ⛔이게 없으면 카본을 셸로 선언해도 **조용히 틀린 값**(−13.6 dB)을 낸다.
#: ⛔K 상한의 **모듈 상수** — 클래스 속성만 보면 밖에서 두 줄로 뚫린다
_K_HARD_LIMIT = 1
SHELL_GAMMA_MAX = 0.5
#: ⭐격자 덮개 검사 — 얼린 격자가 이 자세를 못 덮으면 예외를 던진다(조용히 안 틀리게)
GRID_REF_CHECK = bool(int(os.environ.get("SIONNA2_GRID_REF_CHECK", "1")))


def grid_cover(V, ctr, Rout, n, d, u) -> dict:
    """격자가 이 자세를 덮나 — 옛 커널 `rcs_sbr._grid_cover` 와 **같은 식**."""
    e1, e2 = grid_basis(u)
    W = np.asarray(V, float) - np.asarray(ctr, float)
    half = (n - 1) / 2.0 * d
    m1 = float(half - np.abs(W @ e1).max())
    m2 = float(half - np.abs(W @ e2).max())
    mu = float(Rout - (W @ np.asarray(u, float)).max())
    return dict(margin_e1_m=m1, margin_e2_m=m2, margin_u_m=mu,
                margin_min_m=float(min(m1, m2, mu)),
                covered=bool(min(m1, m2, mu) >= 0.0))


def resolve_shells(group_names, group_mat, shell_groups=None) -> frozenset:
    """투과시킬 셸 그룹. ⚠ 이름으로 정한다 — 카본 데크를 'body' 에 넣으면 조용히 뚫린다.

    ⭐**가드**(옛 커널 `rcs_sbr.py:132` 에서 되살림) — 셸로 선언된 그룹이 실제로 «투과되는»
      재질인지 본다. 없으면 카본(|Γ|=0.90)을 셸로 선언해도 **조용히 틀린 값**이 나온다
      (실측 1.10 dB). 옛 커널은 예외를 던진다 — 같은 자리에서 같이 던져야 한다.
    """
    want = DIELECTRIC_SHELLS if shell_groups is None else frozenset(shell_groups)
    got = frozenset(g for g in dict.fromkeys(group_names) if g in want)
    for g in got:
        mat = (group_mat or {}).get(g)
        if mat is None:
            continue
        try:
            gm = float(gamma_po(mat)) if isinstance(mat, str) else float(mat)
        except Exception:                                       # noqa: BLE001
            continue
        if gm >= SHELL_GAMMA_MAX:
            raise ValueError(
                f"rcs_sbr_gpu: 그룹 {g!r} 이 '유전체 셸'로 선언됐는데 재질 {mat!r} 의 "
                f"|Γ|={gm:.3f} 로 불투명하다(상한 {SHELL_GAMMA_MAX}). 그대로 두면 왕복 투과를 "
                f"과대평가하고 가림도 사라진다 — shell_groups 에서 뺄 것.")
    return got


# --------------------------------------------------------------------------- #
#  프레넬 각도 모양 — `materials_min.gamma_shape` 를 Dr.Jit 로 옮긴 것
# --------------------------------------------------------------------------- #
def _csqrt(x, y):
    """복소수 (x + jy) 의 제곱근을 (re, im) 으로."""
    m = dr.sqrt(x * x + y * y)
    re = dr.sqrt(dr.maximum((m + x) * 0.5, 0.0))
    im = dr.sqrt(dr.maximum((m - x) * 0.5, 0.0))
    return re, dr.select(y < 0.0, -im, im)


def _cdiv(ar, ai, br, bi):
    den = br * br + bi * bi
    return (ar * br + ai * bi) / den, (ai * br - ar * bi) / den


def _gamma_shape_gpu(mat_key: str, fc: float, cos_i):
    """|Γ(θ)|/|Γ(0)| — CPU 판과 같은 식, GPU 에서. εr·σ 는 재질마다 상수라 CPU 에서 읽는다."""
    er, sg, _ = material_params(mat_key, fc)
    EPS0 = 8.8541878128e-12
    a = float(er)
    b = -float(sg) / (2 * np.pi * float(fc) * EPS0)
    ci = dr.clip(cos_i, 0.0, 1.0)
    sr, si_ = _csqrt(a - (1.0 - ci * ci), mi.Float(b))
    te_r, te_i = _cdiv(ci - sr, -si_, ci + sr, si_)
    cr, cim = a * ci, b * ci
    tm_r, tm_i = _cdiv(cr - sr, cim - si_, cr + sr, cim + si_)
    g = dr.sqrt(((te_r**2 + te_i**2) + (tm_r**2 + tm_i**2)) * 0.5)
    erc = a + 1j * b
    sq0 = np.sqrt(erc)
    te0 = (1.0 - sq0) / (1.0 + sq0)
    tm0 = (erc - sq0) / (erc + sq0)
    g0 = float(np.sqrt((abs(te0) ** 2 + abs(tm0) ** 2) / 2.0))
    return g / max(g0, 1e-12)


# --------------------------------------------------------------------------- #
#  배치 커널
# --------------------------------------------------------------------------- #
class BatchSBR:
    """자세 K 개를 한 번에 처리하는 SBR+PO 커널.

        gref = grid_ref_from(poses, fc, spacing=d)       # ⭐얼린 격자 필수(자세 여럿일 때)
        k    = BatchSBR(poses[0], group_mat, fc, K=32, spacing=d, grid_ref=gref)
        E    = k.field(poses, u, range_m=15.0)           # 복소 산란장 [m²], 자세마다 하나

    `group_mat` 값은 재질 키(str) 또는 |Γ| 숫자(float)다. float 은 각도 의존이 없다
    (PEC 는 1.0 으로 준다 — 'pec' 라는 재질 이름은 없다).
    """

    #: ⭐적대적 검증 결과 K≥2 는 값이 샤드 분할을 탄다 — 1 로 못 박는다(위 머리말 참조)
    K_MAX_ALLOWED = 1

    def __init__(self, proto_mesh, group_mat: dict, fc: float, K: int = 1,
                 spacing=None, pad: float = 1.15, grid_ref=None,
                 penetrate: bool = True, shell_groups=None,
                 angle_gamma: bool = True, space_m=None, u_ref=None):
        self.fc = float(fc)
        self.lam = C0 / self.fc
        self.k = 2 * np.pi / self.lam
        self.d = float(spacing) if spacing else self.lam / DEFAULT_DIV
        self.K = int(K)
        # ⛔적대적 검증(2026-08-20): K≥2 면 자세 값이 «배치 안 슬롯 번호» 에 매여
        #   --nshards 를 탄다. 생산 길이에서 0.118~0.328 dB 까지 벌어졌다.
        # ⛔클래스 속성을 보면 `BatchSBR.K_MAX_ALLOWED = 99` 두 줄로 뚫린다 —
        #   **모듈 상수**를 본다(같이 고치려면 파일을 고쳐야 한다).
        if self.K > _K_HARD_LIMIT or self.K > self.K_MAX_ALLOWED:
            raise ValueError(
                f"rcs_sbr_gpu: K={self.K} 는 막혀 있다(상한 {self.K_MAX_ALLOWED}). "
                f"자세를 묶으면 값이 샤드 분할을 타서 원장이 «어떻게 나눠 돌렸나» 에 좌우된다 "
                f"(실측 s1000plus el−60 0.101 dB · 그 각도 밴드 0.02 dB 의 5 배). "
                f"열려면 샤딩을 «K 배수 연속 블록» 으로 바꾸고 다시 검증할 것.")
        self.angle_gamma = bool(angle_gamma)
        self.group_mat = group_mat

        F = np.asarray(proto_mesh.f, np.uint32)
        G = np.asarray(proto_mesh.g)
        self._nv = np.asarray(proto_mesh.v).shape[0]
        self._fsig = (F.shape, int(F.sum()))                 # 토폴로지 지문
        self.groups = sorted(set(G.tolist()))
        self._used = [np.unique(F[G == g]) for g in self.groups]
        self._faces = [F[G == g] for g in self.groups]

        self.ctr, self.Rout, self.n = grid_for(proto_mesh, self.d, pad, grid_ref)
        self.NR = self.n * self.n
        #  ⭐배치는 자세 K 개가 **한 격자**를 나눠 쓴다 → 얼린 격자가 있어야 한다.
        self._frozen = grid_ref is not None
        #  자세 사이 간격 — 안 주면 광선 다발 너비(2·Rout)에 25 % 여유
        self.space_m = float(space_m) if space_m else 2.5 * self.Rout
        if self.K > 1 and self.space_m <= 2 * self.Rout:
            raise ValueError(f"자세 간격 {self.space_m:.3f} m 가 광선 다발 너비 "
                             f"{2*self.Rout:.3f} m 보다 좁다 — 이웃 자세를 때린다.")
        side = int(np.ceil(np.sqrt(self.K)))
        ij = np.array([(i % side, i // side) for i in range(self.K)], float)
        self._lat = (ij - ij.mean(0)) * self.space_m          # (K,2) — e1·e2 성분

        self._shells = resolve_shells(self.groups, group_mat, shell_groups)
        self._shell_pos = [i for i, g in enumerate(self.groups) if g in self._shells]
        self.penetrate = bool(penetrate) and len(self._shell_pos) > 0

        self._mk, self._gam = [], []
        for grp in self.groups:
            val = group_mat.get(grp, "plastic")
            self._gam.append(float(val) if not isinstance(val, str) else gamma_po(val, self.fc))
            self._mk.append(val if isinstance(val, str) else None)

        #  ⭐메쉬는 **한 벌만** 만든다. 겉 씬과 속 씬(셸 뺀 것)은 같은 객체를 공유하므로
        #    정점을 **한 번만** 올리면 된다(예전엔 두 벌을 따로 올렸다 — 그 몫이 절반이었다).
        self._mesh_all, self._par_all = self._make_meshes(range(len(self.groups)))
        self._keep = [i for i in range(len(self.groups)) if i not in self._shell_pos]
        #  ⛔⛔**여기 있던 «씬을 한 번만 만든다» 코드와 주석을 지웠다** (2026-08-20).
        #
        #    지운 주석은 «정점을 올린 뒤 `parameters_changed()` 를 부르면 통째로 다시 지은
        #    것과 **정확히 같아진다**» 고 적혀 있었는데 **거짓이다.** 적대적 검증 실측:
        #      · 겉 씬과 속 씬이 **같은 메쉬 객체**를 쓰면, 갱신 신호를 **먼저 받은 씬 하나만**
        #        가속구조가 다시 서고 나머지는 **낡은 채 남는다** → el 0 에서 **7.97 dB** 어긋난다.
        #      · 갱신 **방법**은 무관하다 — `traverse(scene).update()` 든 `parameters_changed()`
        #        든, 순서를 바꿔도 둘 다 불러도 안 낫는다.
        #      ⇒ 고치는 길은 **메쉬를 분리**하는 것뿐이다(그러면 90/90 비트동일).
        #
        #    게다가 그 두 객체(`self._sc`·`self._sc_in`)는 **아무도 안 읽었다**(저장소 전체
        #    grep 0 건). 실제로 도는 것은 `_upload()` 가 자세마다 `mi.load_dict` 로 **재조립**
        #    하는 길이다. 죽은 코드 옆에 거짓 주석이 붙어 있으면, 다음 사람이 그 주석을 믿고
        #    «씬 재사용» 을 켜서 원장을 조용히 오염시킨다. 그래서 **둘 다 지웠다.**
        #
        #    ⭐되살리려면(11.3 → 8.5 ms 를 노린다면) 순서가 있다:
        #      ① 겉·속이 **서로 다른 메쉬 객체**를 쓰게 `_make_meshes` 를 고친다
        #      ② 두 씬의 메쉬 `id()` 가 서로소인지 **어서션**으로 못 박는다
        #      ③ 앙각당 1 회 **자기시험**(새로 지은 씬과 비트대조)을 넣는다
        #      ④ 그런 뒤에야 재사용을 켠다

        #  ⭐정점 모으기를 GPU 로 넘기기 위한 색인 — 자세가 바뀌어도 안 변하므로 여기서 한 번만.
        #    예전에는 자세마다 numpy 로 그룹별 gather + concatenate 를 했고, 그게 남은 시간의
        #    77 % 였다(실측 0.709 ms/자세). 이제 원본 정점을 통째로 한 번 올리고 GPU 가 모은다.
        self._idx, self._pid, self._nent = [], [], []
        for gi in range(len(self.groups)):
            used = self._used[gi]
            self._idx.append(mi.UInt32(np.concatenate(
                [used + j * self._nv for j in range(self.K)]).astype(np.uint32)))
            self._pid.append(mi.UInt32(np.repeat(np.arange(self.K),
                                                 len(used)).astype(np.uint32)))
            self._nent.append(len(used) * self.K)
        self._vbuf = np.empty((self.K, self._nv, 3), np.float32)   # 자리를 다시 안 잡는다

    # ── 준비 ────────────────────────────────────────────────────────────
    def _make_meshes(self, group_idx):
        meshes, params = {}, []
        for gi in group_idx:
            used, f = self._used[gi], self._faces[gi]
            remap = np.full(self._nv, -1, np.int64); remap[used] = np.arange(len(used))
            fl = remap[f].astype(np.uint32); nv, nf = len(used), len(f)
            m = mi.Mesh(f"g_{self.groups[gi]}", vertex_count=nv * self.K,
                        face_count=nf * self.K, has_vertex_normals=False,
                        has_vertex_texcoords=False)
            p = mi.traverse(m)
            p["faces"] = mi.UInt32(np.concatenate(
                [(fl + j * nv).ravel() for j in range(self.K)]).astype(np.uint32))
            p["vertex_positions"] = mi.Float(np.zeros(nv * self.K * 3, np.float32))
            p.update()
            meshes[f"s_{gi}"] = m
            params.append(p)
        return meshes, params

    def _delta(self, u):
        """자세 K 개의 자리 (K,3) — û 에 수직인 평면 위, 원점 중앙정렬."""
        e1, e2 = grid_basis(np.asarray(u, float))
        return self._lat[:, 0:1] * e1[None, :] + self._lat[:, 1:2] * e2[None, :]

    def _look(self, u):
        """⭐방향이 그대로면 광선 다발과 자리를 **다시 안 만든다**.

        생산 루프는 앙각 하나를 고정하고 자세만 갈아 넣는다(자세 4096 개 ÷ K = 수십 번 호출).
        광선 다발은 방향에만 매이므로 첫 호출 한 번이면 된다 — 실측으로 이게 남은 시간의
        32 % 였다(0.201 ms/자세). 방향이 바뀌면 그때만 다시 만든다."""
        key = tuple(np.asarray(u, float))
        if getattr(self, "_look_key", None) != key:
            delta = self._delta(u)
            self._look_key = key
            self._look_val = (delta, self._rays_for(u, delta),
                              mi.Vector3f(*[float(x) for x in u]),
                              mi.Vector3f(*[mi.Float(np.repeat(delta[:, i], self.NR)
                                                     .astype(np.float32)) for i in range(3)]))
        return self._look_val

    def _rays_for(self, u, delta):
        r1 = ray_grid(self.ctr, self.Rout, self.n, self.d, u)
        O1 = np.asarray(mi.Point3f(r1.o)).T
        D1 = np.asarray(mi.Vector3f(r1.d)).T
        O = np.concatenate([O1 + delta[j] for j in range(self.K)]).astype(np.float32)
        D = np.tile(D1, (self.K, 1)).astype(np.float32)
        return mi.Ray3f(o=mi.Point3f(*O.T), d=mi.Vector3f(*D.T))

    def _upload(self, mvs, delta):
        """자세 K 벌의 정점을 올리고 씬(겉·속)을 다시 조립한다.

        ⭐CPU 는 원본 정점을 **한 덩어리로 옮겨 담기만** 한다. 그룹별로 골라 모으고 자리를
          옮기는 일은 GPU 가 한다(dr.gather → dr.scatter). 예전 numpy 판과 비교해 값 차이는
          자리 이동을 float32 로 더하는 데서 오는 1 ulp 뿐이다.
        """
        for j in range(self.K):
            np.copyto(self._vbuf[j], mvs[j].v)
        Vall = mi.Float(self._vbuf.ravel())
        dflat = mi.Float(np.asarray(delta, np.float32).ravel())
        for gi in range(len(self.groups)):
            pos = (dr.gather(mi.Point3f, Vall, self._idx[gi])
                   + dr.gather(mi.Point3f, dflat, self._pid[gi]))
            n = self._nent[gi]
            out = dr.zeros(mi.Float, 3 * n)
            dr.scatter(out, pos, dr.arange(mi.UInt32, n))
            self._par_all[gi]["vertex_positions"] = out
            self._par_all[gi].update()
        sc = mi.load_dict({"type": "scene", **self._mesh_all})
        sc_i = (mi.load_dict({"type": "scene", **{f"s_{gi}": self._mesh_all[f"s_{gi}"]
                                                  for gi in self._keep}})
                if self.penetrate else None)
        return sc, sc_i

    # ── 본체 ────────────────────────────────────────────────────────────
    def _hit_terms(self, scene, gidx, ray, uf, angle_gamma):
        si = scene.ray_intersect(ray)
        #  ⭐교차 결과를 여기서 **확정**시킨다. 안 하면 Dr.Jit 이 광선추적과 아래 PO 연산을
        #    한 덩어리 커널로 융합하는데, 그때 잘못된 PTX 가 나와 컴파일이 통째로 죽는다
        #    (실측: 재질 색인 select 사슬이 섞이면 재현). 커널이 둘로 갈릴 뿐이라 비용은 무시할 만하다.
        dr.eval(si.p, si.n, si.t, si.shape)
        ptrs = [mi.ShapePtr(s) for s in scene.shapes()]
        g = mi.Float(0.0); which = mi.Int32(-1)
        for j, gi in enumerate(gidx):
            hit = si.shape == ptrs[j]
            g = dr.select(hit, mi.Float(float(self._gam[gi])), g)
            which = dr.select(hit, mi.Int32(j), which)
        sgn = dr.sign(dr.dot(si.n, uf))
        sgn = dr.select(sgn == 0.0, mi.Float(1.0), sgn)
        cos_i = dr.dot(si.n * sgn, uf)
        lit = si.is_valid() & (cos_i > 1e-6)
        if angle_gamma:
            for j, gi in enumerate(gidx):
                if self._mk[gi] is None:
                    continue
                sel = (which == j) & lit
                g = dr.select(sel, g * _gamma_shape_gpu(self._mk[gi], self.fc, cos_i), g)
        return lit, g, si

    def _phase(self, si, off, cent, uf, range_m):
        p_local = si.p - off                                  # 자세를 제자리로 되돌린다
        if range_m is None:                                   # 평면파
            return 2.0 * float(self.k) * dr.dot(p_local - cent, uf)
        R = float(range_m)                                    # 구면파 — 실제 왕복 거리
        return 2.0 * float(self.k) * (R - dr.norm(p_local - (cent + uf * R)))

    def field(self, poses, u, range_m=None) -> np.ndarray:
        """복소 산란장 E(û) [m²] — 자세마다 하나. σ = (4π/λ²)|E|²."""
        mvs = list(poses)
        n_in = len(mvs)
        if n_in == 0:
            return np.zeros(0, complex)
        if n_in > 1 and not self._frozen:
            raise ValueError("자세를 여럿 넣으려면 grid_ref(얼린 격자)가 있어야 한다 — "
                             "`grid_ref_from(poses, fc, spacing=d)` 를 넘길 것.")
        # ⭐⭐**격자 덮개 검사** (옛 커널 `rcs_sbr.py:1052 GRID_REF_CHECK` 에서 되살림).
        #   얼린 격자가 이 자세를 못 덮으면 **광선이 표적 일부를 아예 안 맞는다** — 그러면
        #   예외 없이 **조용히 작은 σ** 가 나온다(실측 4.68 dB). 옛 커널은 던진다.
        #   ⛔이 검사가 «정의만 되고 호출이 0 건» 이던 판이 있었다(2026-08-20) — 반드시 여기서 건다.
        if GRID_REF_CHECK and self._frozen:
            for _q, _mv in enumerate(mvs):
                _cov = grid_cover(np.asarray(_mv.v, float), self.ctr, self.Rout,
                                  self.n, self.d, np.asarray(u, float))
                if not _cov["covered"]:
                    raise ValueError(
                        f"rcs_sbr_gpu: 얼린 격자가 자세 {_q} 를 못 덮는다 — 여유 "
                        f"e1 {_cov['margin_e1_m']*1e3:+.2f} · e2 {_cov['margin_e2_m']*1e3:+.2f} · "
                        f"û {_cov['margin_u_m']*1e3:+.2f} mm (음수 = 밖으로 삐져나옴). "
                        f"grid_ref_from 에 이 자세를 포함시켜 판을 다시 만들라 "
                        f"(검사를 끄려면 SIONNA2_GRID_REF_CHECK=0 — 권하지 않는다).")
        if n_in > self.K:
            raise ValueError(f"자세 {n_in} 개는 K={self.K} 보다 많다 — K 를 키우거나 나눠 부를 것")
        for m in mvs:
            Fm = np.asarray(m.f, np.uint32)
            if (Fm.shape, int(Fm.sum())) != self._fsig:
                raise ValueError("토폴로지가 원형과 다르다 — 같은 기체의 자세만 넣을 것")
        mvs = mvs + [mvs[-1]] * (self.K - n_in)               # 빈 자리는 마지막 자세로

        u = np.asarray(u, float); u = u / np.linalg.norm(u)
        delta, ray, uf, off = self._look(u)                   # ⭐방향이 같으면 재사용
        cent = mi.Point3f(*[float(x) for x in self.ctr])

        gidx = list(range(len(self.groups)))
        sc, sc_i = self._upload(mvs, delta)
        lit, g, si = self._hit_terms(sc, gidx, ray, uf, self.angle_gamma)
        x = self._phase(si, off, cent, uf, range_m)
        w = dr.select(lit, g, mi.Float(0.0))
        re = np.asarray(w * dr.cos(x)).reshape(self.K, self.NR).sum(1)
        im = np.asarray(w * dr.sin(x)).reshape(self.K, self.NR).sum(1)

        #  ── 유전체 셸 투과: 셸 맞은 광선만 내부 금속을 τ=1−|Γ|² 로 코히런트 가산 ──
        if self.penetrate:
            ptrs_f = [mi.ShapePtr(s) for s in sc.shapes()]
            tau = mi.Float(0.0)
            for i in self._shell_pos:
                tau = dr.select(si.shape == ptrs_f[i], mi.Float(1.0 - self._gam[i] ** 2), tau)
            lit2, g2, si2 = self._hit_terms(sc_i, self._keep, ray, uf, self.angle_gamma)
            x2 = self._phase(si2, off, cent, uf, range_m)
            w2 = dr.select(lit2 & (tau > 0.0), tau * g2, mi.Float(0.0))
            re = re + np.asarray(w2 * dr.cos(x2)).reshape(self.K, self.NR).sum(1)
            im = im + np.asarray(w2 * dr.sin(x2)).reshape(self.K, self.NR).sum(1)

        return ((re + 1j * im) * self.d * self.d)[:n_in]

    def sigma_dbsm(self, poses, u, range_m=None) -> np.ndarray:
        E = self.field(poses, u, range_m=range_m)
        return 10 * np.log10(4 * np.pi / self.lam ** 2 * np.abs(E) ** 2)
