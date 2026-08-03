# -*- coding: utf-8 -*-
"""
ptd_edges.py — untruncated Michaeli PTD-EEC (first order)
=========================================================

정직한 이름 (outputs/ptd_attack_lit.json q3 판정 · docs/RETRACTION_LOG.md R13)
------------------------------------------------------------------------------
이 모듈이 구현한 것은 **untruncated Michaeli PTD-EEC (first order)** 다.
Michaeli 1986 의 **비절단(untruncated)** 등가모서리전류(EEC)를 직선 모서리 조각을 따라
해석 적분한 1 차 PTD 프린지파 보정이다.

  ⛔ **NOT "TW-ILDC" · NOT "ILDC" · NOT "Gao's method"**
     Gao 2012 의 TW(truncated wedge)는 Johansen 1996 의 절단 보정 EEC 식 (3)(9)(10)(11)(21)(22)
     이고, 우리는 그 절단항을 **하나도** 구현하지 않았다. 우리가 가진 것은 Johansen 식 (4)(5)
     = Michaeli 1986 (4)–(7) = **비절단 절반**뿐이다. Gao·Johansen 은 '안 넣었다' 는 부정
     문맥에서만 인용한다.

무엇인가
--------
PO(물리광학) 면적분은 표면의 **균일전류 J⁰** 만 센다. Ufimtsev 의 **비균일(프린지) 전류
J¹ = J − J⁰** 은 모서리 근방에서만 살아 있고 통째로 빠져 있다. 이 모듈은 그 빠진 항을
**더하는** 형태로 계산한다.

    E_total = E_PO_surface + E_PTD_edge
    σ       = (4π/λ²) |E_total|²

기존 PO/SBR 코드는 **한 줄도 고치지 않는다.** 이 파일은 순수 추가분이다.

정식화 (docs/PTD_ILDC_FORMULATION.md §5 채택안 그대로)
------------------------------------------------------
  * Michaeli 1986 프린지 EEC 를 Öztürk 2002 (3.23)–(3.32) 형태로 구현.
  * 무한(untruncated) 증분 스트립. TW(Johansen 절단)는 **미구현** — §4.4 의 판정대로 1 단계 제외.
  * 모서리 방향 선적분은 해석적: 직선 조각에서 `L·exp(jk q·r_c)·sinc(kL q·t̂/2)`, q = û_i+û_s
    (모노스태틱이면 q=2û → §7.1 의 `L e^{j2kû·r_c} sinc(kL t̂·û)`).
  * 정규화 A_FW = **−½** Σ[ Z (ŝ×(ŝ×t̂))·ê_r I^f + (ŝ×t̂)·ê_r M^f ] · L · phase · sinc

⭐ 정규화 상수의 부호 — 유도와 그 근원 (2026-08-03 수리, D-1)
--------------------------------------------------------------
doc §9.1 은 이 상수를 `½ = λk/(4π)` 로 **크기만** 잡았고 그래서 **부호를 잃었다**. 사슬은 셋이다.

  (A) 우리 A 규약(면적분과 공유)은 실제 원거리장으로 환산하면 **음의** 상수를 갖는다:
        A_PO = Σ_lit (n̂·û) ΔA e^{j2kû·r}   ⇔   E^s·ê = **−(jk/2π)** (e^{−jkr}/r) A_PO
      음부호의 출처는 `d̂ = −û` 다 — 복사적분은 입사 **진행**방향으로 쓰인 H^i = (1/Z₀) d̂×ê 를
      통해 전류에 들어가는데, A 규약은 **바깥쪽** 시선 û 로 쓰여 있다.
      (수치 확인: 벡터 복사적분 E = −jωμ/(4πr) ∫J⊥ 로 직접 계산한 값 / 위 식 = 1.0 ∠1e−14°)
  (B) EEC 복사적분의 문헌 상수는 **+jk/(4π)** 다 — Öztürk 2002 (3.7), Gao 2012 (3) 축자.
        E^FW = **jk** ∫ (e^{−jks}/4πs) [ Z ŝ×(ŝ×t̂) I^f + ŝ×t̂ M^f ] dl
  (C) 따라서 같은 A 단위의 프린지 상수는  (jk/4π) / (−jk/2π) = **−½**.
      j 는 서로 지워지고, 남는 −1 은 (A) 의 음부호다.

  ⇒ 근원은 **Michaeli 계수도, 면 법선 방향도, 적분 방향도 아니다.** (계수는 Johansen 이 옮겨
    적은 Michaeli (4)–(7) 과 6e−12 로 일치하고, 면 순서 교환 불변이며, t̂ 부호는 g_I·I^f 와
    g_M·M^f 가 **둘 다** 홀수여서 곱에서 상쇄된다.) 근원은 doc §9.1 의 **크기만 취한 유도**가
    (A) 의 −jk/2π 와 (B) 의 +jk/4π 사이 **상대부호**를 버린 것 하나다.
  ⇒ 합격 기준(Rung 2): 평판 on-cone 모서리에서 `arg(A_code / A_analytic) = 0°`.
    수리 후 측정: |ratio| − 1 = 1.4e−14, |arg| ≤ 5.8e−13° (θ = 5…84° 24 점, 양 편파).
    이 게이트는 benchmark/smoke_ptd.py (f) 와 benchmark/ptd_plate_validation.py 에 상설이다.

위상·좌표 규약 (outputs/ptd_kernel_anatomy.json q4 와 **동일**해야 한다)
-----------------------------------------------------------------------
  * û = 표적→레이더 (outward). k = 2π/λ. 모노스태틱 위상 exp(+j·2k·(r−origin)·û).
  * origin 은 면적분이 쓴 것과 **같은 것**을 써야 한다:
      - rcs_po.rcs_from_points 계열: origin = (0,0,0) (절대좌표, 중심감산 없음)  ← 이 모듈 기본값
      - rcs_sbr.* 계열: origin = 0.5*(V.max(0)+V.min(0))  ← attach_to_sbr_field() 가 요구
  * E 단위는 m² (면적분과 동일). σ = (4π/λ²)|E|².

모서리 국소 좌표 (Öztürk/UTD 혼합규약 — 원문과 일치하도록 재구성했다)
--------------------------------------------------------------------
  ẑ_loc = t̂ (모서리 접선), x̂_loc = face 1 이 모서리에서 뻗는 방향, ŷ_loc = t̂ × x̂ = face 1 의
  바깥 법선. 외부(공기) 영역은 방위 φ ∈ (0, Nπ), 물질은 (Nπ, 2π). face 2 는 φ = Nπ.
  입사 **진행**방향 d̂ = (−sinβ' cosφ', −sinβ' sinφ', cosβ'),  즉 β' 는 d̂ 가 +ẑ_loc 와 이루는 각이고
  φ' 는 **광원 방향**(=û_i)의 방위각이다. 관측(산란 진행)방향 ŝ = (sinβ cosφ, sinβ sinφ, cosβ).
  → 모노스태틱(ŝ = û_i)에서 β = π−β', φ = φ' 로 떨어진다. 이 규약에서만 문서 (3.35)
    `μ₁ = cos φ − 2cot²β` 가 (3.29)+(3.30) 과 대수적으로 일치한다(코드에서 검증했다).

⚠ 근사·미구현 (반환 메타 `approximations` / `not_implemented` 에 그대로 실린다)
------------------------------------------------------------------------------
  · TW(truncated wedge, Johansen 1996) 절단 보정 — **미구현**. few-λ 표적에서 무한 스트립
    가정이 가장 약한 지점이다(§4.4). 값을 지어내지 않고 항 자체를 넣지 않았다.
  · 2 차 회절, 코너 회절, 크리핑파 — **미구현(0)**.
  · 모서리 가림(다른 부위에 의한 shadow) — **미구현**. 인접면 법선 게이트만 쓴다. 외부에서
    `visible_fn` 훅을 주면 그때 반영된다(기본 None = 가림 없음).
  · PO 항은 여전히 **스칼라**(|Γ| 가중)다. 프린지 항만 편파를 가진다 → 두 항을 코히어런트로
    더할 때 PO 를 두 편파에 **공통**으로 쓴다(§9.2 방침). 이것은 근사이며 pol 별 σ 를 따로 낸다.
  · 프린지 계수는 PEC 유도다 → 기본값 metal_only=True: **양쪽 인접면이 모두 |Γ|≥0.999** 인
    모서리에만 적용한다(§9.3). |Γ| 로 프린지를 스케일하는 휴리스틱은 쓰지 않는다.
  · Ufimtsev 특이점 근방(cos φ' + μ → 0)은 **제거가능 특이점**이라 유한값이 존재하지만, 그
    뺄셈이 이미 수행된 비특이 닫힌형은 **우리가 가진 어느 문헌에도 없다**(Öztürk (3.37)(3.38)
    도 두 발산 분수를 그대로 둔다) → φ' 를 ±δ 로 흔든 대칭평균으로 수치 정규화한다
    (O(δ²) 절단오차). 정규화한 조각 수를 meta 에 센다.
  · sin a → 0 (진짜 Ufimtsev 특이점, 면 스치는 관측) 과 sin β' → 0 (모서리 정면 입사) 은
    **버리고 센다**. 그럴듯한 값을 채우지 않는다.
  · **오목(reentrant) 모서리 N < 1 은 기본적으로 버리고 센다** (D-3). 전체전류 분모
    cos(φ'/N) − cos((π−a)/N) 은 N < 1 에서 PO 분모와 **짝이 맞지 않는 추가 영점**(다중반사
    경계에 해당)을 갖고, 그 자리에서 프린지 EEC 가 진짜로 발산한다(N = 1/(2m) 은 정확한 극).
    1 차 PTD + 단일반사 PO 뺄셈으로는 그 경계를 균일하게 다룰 수 없다 → 범위 밖으로 선언한다.
    `extract_edges(keep_reentrant=True)` 로 진단용으로만 되살릴 수 있고, 버린 길이는
    stats 의 `length_reentrant_m` / `reentrant_length_fraction` 에 실린다.
  · N ≥ 1 에서도 위 전체전류 분모가 PO 분모와 **동시에** 0 이 되지 않는 채로 작아지면
    (제거가능이 아닌 극) 그 조각을 **버리고 센다** — `n_drop_den_pole`.

작성 2026-08-03. 부호·극 수리 2026-08-03 (D-1/D-3).
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from rcs_po import C0, mesh_to_points, rcs_from_points, _look_dirs  # noqa: E402

Z0 = 376.730313668              # 자유공간 임피던스 [Ω] — I^f/M^f 안에서 정확히 상쇄된다

# ── 기본 파라미터와 그 근거 ────────────────────────────────────────────────── #
#  SHARP_DEG_DEFAULT: |외부쐐기각 α − 180°| 가 이 값 이하면 '평평한 가짜 모서리' 로 보고 건너뛴다.
#  근거 — docs/PTD_ILDC_FORMULATION.md §3.7 표: φ=φ₀=60° 에서 이면각 편차 1°→ f¹≈−0.0087,
#  5°→ −0.042, 10°→ −0.082 (진짜 모서리 α=270° 의 −0.394 대비 각각 −33/−19/−13 dB 진폭).
#  즉 5° 문턱은 개당 −19 dB 이하만 버린다. **물리적 필수가 아니라 속도 최적화**이며,
#  촘촘한 테셀레이션 모서리가 코히어런트로 쌓일 수 있으므로(같은 §3.7 경고) 구(Rung 0)
#  스모크로 문턱을 확인해야 한다. 0.0 을 주면 아무것도 안 버린다.
SHARP_DEG_DEFAULT = 5.0
WELD_TOL_DEFAULT = 1e-7         # [m] 정점 용접 격자. cadkit.to_geom 은 부품 경계를 용접하지 않는다
GAMMA_METAL_MIN = 0.999         # §9.3 — 이 이상이면 '금속'
#  N_MIN: 외부 쐐기각이 이보다 작으면(α < 9°) 버린다. 실제 드론 CAD(불리언 유니온 결과)에는
#  두 면이 거의 겹친 α≈0 '틈' 모서리가 존재하고, (3.26)(3.27) 의 1/N · cos(φ'/N) 이 발산한다.
#  물리적으로도 λ 대비 0 두께 틈은 이 정식화의 적용 범위 밖이다 → **버리고 센다**.
N_MIN = 0.05
SING_TOL = 1e-3                 # |cos φ' + μ| 가 이보다 작으면 제거가능 특이점 정규화 발동
SING_DELTA = 5e-3               # [rad] 정규화용 φ' 대칭 오프셋 (절단오차 O(δ²)≈2.5e−5)
SINA_TOL = 1e-3                 # |sin a| 가 이보다 작으면 진짜 특이점 → 버림
SINB_TOL = 1e-3                 # |sin β'| 가 이보다 작으면 모서리 정면 입사 → 버림
#  DEN_TOL: **전체전류** 분모 cos(φ'/N) − cos((π−a)/N) 의 극 감시(D-3). SING_TOL 이 보는 것은
#  PO 분모 cos φ' + μ 이고 **다른 분모**다. 둘이 동시에 0 이면 제거가능(정규화가 처리),
#  전체전류 분모만 0 이면 제거 불가능한 극 → 그 조각은 버리고 센다.
DEN_TOL = 1e-3
#  A_FW_CONST: 프린지 선적분의 전체 복소상수. **−½** 이며 그 부호는 모듈 상단 (A)(B)(C) 유도로
#  고정된다(크기 ½ = λk/4π 는 doc §9.1 그대로, 부호는 A 규약의 −jk/2π 에서 온다).
#  ⚠ 이 값을 바꾸면 Rung 2 위상 게이트 arg(A_code/A_analytic)=0° 가 즉시 깨진다.
A_FW_CONST = -0.5
#  PTD 를 켤 때 요구하는 PO 점구름 간격 상한(D-8). PO 면적분의 중점구적 오차가 λ/7 에서
#  프린지 항 진폭의 3~11 % 나 되어(6λ×40λ 평판 측정) '더하는 것'과 '자기 구적오차를 지우는 것'
#  이 분리되지 않는다. λ/20 이면 2~4 % 로 내려간다.
PTD_SPACING_MAX_DIV = 20.0


# =========================================================================== #
#  1. 모서리 추출
# =========================================================================== #
@dataclass
class EdgeSet:
    """추출된 모서리 목록. 전부 (n,·) 배열이고 인덱스가 서로 대응한다."""
    P0: np.ndarray              # (n,3) 모서리 시작점
    P1: np.ndarray              # (n,3) 모서리 끝점
    T: np.ndarray               # (n,3) 접선 t̂ = ẑ_loc  (face 1 기준으로 방향 고정)
    X: np.ndarray               # (n,3) x̂_loc — face 1 이 모서리에서 뻗는 방향 (φ=0)
    Y: np.ndarray               # (n,3) ŷ_loc = t̂ × x̂ = face 1 바깥 법선
    L: np.ndarray               # (n,)  길이 [m]
    Nw: np.ndarray              # (n,)  N = α/π  (α = 외부 쐐기각). 열린 모서리는 2.0
    boundary: np.ndarray        # (n,)  bool — 인접면 1 개(열린 모서리)
    gmin: np.ndarray            # (n,)  인접면 |Γ| 의 최솟값 (gamma 미지정이면 1.0=PEC)
    n1: np.ndarray              # (n,3) face 1 바깥 법선 (= Y)
    n2: np.ndarray              # (n,3) face 2 바깥 법선 (열린 모서리는 −n1)
    stats: dict = field(default_factory=dict)

    def __len__(self):
        return len(self.L)


def _tri_geometry(V, F):
    """면 법선(정규화)·중심·면적."""
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nr = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(nr, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        nhat = nr / (2.0 * area[:, None])
    ctr = (v0 + v1 + v2) / 3.0
    return nhat, ctr, area


def extract_edges(mesh, sharp_deg=SHARP_DEG_DEFAULT, weld_tol=WELD_TOL_DEFAULT,
                  gamma=None, keep_flat=False, n_min=N_MIN, keep_reentrant=False):
    """geom.Mesh 에서 (a) 경계 모서리 (b) 날카로운 이면각 모서리 를 뽑는다.

    sharp_deg : |α − 180°| 가 이 값 이하인 이면(=거의 평평한 테셀레이션 이음매)은 버린다.
                근거는 모듈 상단 SHARP_DEG_DEFAULT 주석(§3.7 표).
    weld_tol  : [m] 정점 용접 격자. cadkit.Assembly.to_geom 이 부품 경계를 용접하지 않으므로
                (anatomy q6) 위치 기준 용접이 반드시 필요하다.
    gamma     : {그룹이름: |Γ|} dict. 주면 인접면 |Γ| 최솟값을 gmin 에 담는다(§9.3 판정용).
    keep_flat : True 면 sharp_deg 필터를 끈다(진단용).
    keep_reentrant : True 면 오목 모서리(α < 180°, N < 1)도 남긴다. **기본은 버린다**(D-3) —
                모듈 상단 설명대로 N < 1 에서 전체전류 분모가 PO 분모와 짝이 맞지 않는 추가
                영점(다중반사 경계)을 갖고, N = 1/(2m) 은 정확한 극이다. 버린 길이는 stats 에
                `length_reentrant_m` / `reentrant_length_fraction` 로 남는다. 진단 전용.
    """
    V = np.asarray(mesh.v, dtype=np.float64)
    F = np.asarray(mesh.f, dtype=np.int64)
    G = list(mesh.g)
    nhat, fctr, farea = _tri_geometry(V, F)
    ok_face = farea > 1e-14

    # 위치 기준 용접: 좌표를 weld_tol 격자로 반올림한 정수키
    key = np.round(V / weld_tol).astype(np.int64)
    _, first_idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    Vw = V[first_idx]                       # 용접 대표점

    emap = {}
    for fi in range(len(F)):
        if not ok_face[fi]:
            continue
        a, b, c = inv[F[fi, 0]], inv[F[fi, 1]], inv[F[fi, 2]]
        for i, j in ((a, b), (b, c), (c, a)):
            if i == j:
                continue                     # 용접으로 붕괴한 변
            emap.setdefault((min(i, j), max(i, j)), []).append(fi)

    P0, P1, T, X, Y, L, Nw, bnd, gmin, N1, N2 = [], [], [], [], [], [], [], [], [], [], []
    n_nonmanifold = n_flat = n_degen = n_thin = n_reent = 0
    l_reent = l_reent_metal = 0.0
    n_min_seen = None
    frame_dev = 0.0
    alpha_all = []

    sharp_rad = np.radians(float(sharp_deg))
    for (i, j), fl in emap.items():
        if len(fl) > 2:
            n_nonmanifold += 1
            continue
        p0, p1 = Vw[i], Vw[j]
        ev = p1 - p0
        ln = float(np.linalg.norm(ev))
        if ln < 1e-12:
            n_degen += 1
            continue
        t_raw = ev / ln
        pe = 0.5 * (p0 + p1)

        f1 = fl[0]
        n1 = nhat[f1]
        d1 = fctr[f1] - pe
        m1 = d1 - np.dot(d1, t_raw) * t_raw
        if np.linalg.norm(m1) < 1e-12:
            n_degen += 1
            continue
        m1 /= np.linalg.norm(m1)

        if len(fl) == 1:
            # 경계(열린) 모서리 → 반평면. 외부각 α = 2π, N = 2.
            alpha = 2.0 * np.pi
            n2 = -n1
            is_b = True
        else:
            f2 = fl[1]
            n2 = nhat[f2]
            d2 = fctr[f2] - pe
            m2 = d2 - np.dot(d2, t_raw) * t_raw
            if np.linalg.norm(m2) < 1e-12:
                n_degen += 1
                continue
            m2 /= np.linalg.norm(m2)
            raw = float(np.arccos(np.clip(np.dot(m1, m2), -1.0, 1.0)))
            # 볼록/오목 판정: face 1 바깥법선에서 봤을 때 m2 가 안쪽이면 볼록(내부각 = raw)
            th_int = raw if np.dot(n1, m2) < 0.0 else (2.0 * np.pi - raw)
            alpha = 2.0 * np.pi - th_int          # 외부(공기쪽) 쐐기각
            is_b = False
            if (not keep_flat) and abs(alpha - np.pi) <= sharp_rad:
                n_flat += 1
                alpha_all.append(alpha)
                continue
            if alpha / np.pi < n_min:      # 두 면이 거의 겹친 α≈0 '틈' — 정식화 적용범위 밖
                n_thin += 1
                continue
            n_min_seen = alpha / np.pi if n_min_seen is None else min(n_min_seen, alpha / np.pi)
            if (not keep_reentrant) and alpha < np.pi:
                #  오목(reentrant) 모서리: N < 1 — 1 차 PTD 적용범위 밖(D-3). 버리고 길이를 센다.
                n_reent += 1
                l_reent += ln
                if gamma is not None:
                    if min(float(gamma.get(G[fi], 1.0)) for fi in fl) >= GAMMA_METAL_MIN:
                        l_reent_metal += ln
                else:
                    l_reent_metal += ln
                continue
        alpha_all.append(alpha)

        # t̂ 방향 고정: t̂ × x̂ = n̂₁ 이 되도록 (그러면 ŷ_loc = n̂₁, 외부는 φ∈(0,Nπ))
        t = t_raw if np.dot(np.cross(t_raw, m1), n1) > 0 else -t_raw
        y = np.cross(t, m1)
        frame_dev = max(frame_dev, float(np.linalg.norm(y - n1)))

        gm = 1.0
        if gamma is not None:
            gs = [float(gamma.get(G[fi], 1.0)) for fi in fl]
            gm = float(min(gs))

        P0.append(p0); P1.append(p1); T.append(t); X.append(m1); Y.append(y)
        L.append(ln); Nw.append(alpha / np.pi); bnd.append(is_b)
        gmin.append(gm); N1.append(n1); N2.append(n2)

    n = len(L)
    z3 = np.zeros((n, 3))
    es = EdgeSet(
        P0=np.array(P0).reshape(n, 3) if n else z3,
        P1=np.array(P1).reshape(n, 3) if n else z3,
        T=np.array(T).reshape(n, 3) if n else z3,
        X=np.array(X).reshape(n, 3) if n else z3,
        Y=np.array(Y).reshape(n, 3) if n else z3,
        L=np.array(L, float) if n else np.zeros(0),
        Nw=np.array(Nw, float) if n else np.zeros(0),
        boundary=np.array(bnd, bool) if n else np.zeros(0, bool),
        gmin=np.array(gmin, float) if n else np.zeros(0),
        n1=np.array(N1).reshape(n, 3) if n else z3,
        n2=np.array(N2).reshape(n, 3) if n else z3,
    )
    aa = np.degrees(np.array(alpha_all)) if alpha_all else np.zeros(0)
    es.stats = dict(
        n_edges_total=len(emap),
        n_kept=n,
        n_boundary=int(es.boundary.sum()) if n else 0,
        n_wedge=int((~es.boundary).sum()) if n else 0,
        n_dropped_flat=n_flat,
        n_dropped_nonmanifold=n_nonmanifold,
        n_dropped_degenerate=n_degen,
        n_dropped_thin_wedge=n_thin,
        n_dropped_reentrant=n_reent,
        length_reentrant_m=float(l_reent),
        length_reentrant_metal_m=float(l_reent_metal),
        n_wedge_min_before_reentrant_drop=(float(n_min_seen) if n_min_seen is not None else None),
        keep_reentrant=bool(keep_reentrant),
        sharp_deg=float(sharp_deg),
        n_min=float(n_min),
        weld_tol_m=float(weld_tol),
        frame_orthonormality_max_dev=frame_dev,   # ŷ=t̂×x̂ 와 n̂₁ 의 최대 괴리(0 이어야 정상)
        alpha_deg_min=float(aa.min()) if aa.size else None,
        alpha_deg_max=float(aa.max()) if aa.size else None,
        length_total_m=float(es.L.sum()) if n else 0.0,
        length_metal_m=float(es.L[es.gmin >= GAMMA_METAL_MIN].sum()) if n else 0.0,
    )
    #  §9.3 이 리포트에 적으라고 한 값: PTD 가 실제로 붙는 모서리 길이 비율
    es.stats["metal_length_fraction"] = (
        es.stats["length_metal_m"] / es.stats["length_total_m"]
        if es.stats["length_total_m"] > 0 else 0.0)
    #  D-3 이 리포트에 적으라고 한 값: 오목 모서리로 **버린** 길이 비율(분모는 버리기 전 총길이)
    denom = es.stats["length_total_m"] + l_reent
    es.stats["reentrant_length_fraction"] = (l_reent / denom) if denom > 0 else 0.0
    denom_m = es.stats["length_metal_m"] + l_reent_metal
    es.stats["reentrant_metal_length_fraction"] = (l_reent_metal / denom_m) if denom_m > 0 else 0.0
    return es


# =========================================================================== #
#  2. Michaeli 프린지 EEC  (Öztürk 2002 eqs. 3.23–3.32)
# =========================================================================== #
def _arccos_c(mu):
    """(3.28) a = arccos μ = −j ln(μ + j√(1−μ²)). |μ|>1 이면 복소값이 나온다."""
    m = np.asarray(mu, dtype=np.complex128)
    return -1j * np.log(m + 1j * np.sqrt(1.0 - m * m))


def _face_fringe(Nw, bp, pp, b, p, Ez, Hz, k, Z=Z0):
    """face 1 좌표계에서의 프린지 EEC (I^f_1, M^f_1)  — (3.23)=(3.26)−(3.24), (3.27)−(3.25).

    인자는 전부 (n,) 실수 배열. Ez = ẑ·Ē^i_0, Hz = ẑ·H̄^i_0 (복소 허용).
    반환: (I_f, M_f, den_po, sin_a, den_t) — 뒤 셋은 특이점 진단용.
      den_po = cos φ' + μ            (PO 항 분모)
      den_t  = cos(φ'/N) − cos((π−a)/N)  (**전체전류 항 분모** — 다른 분모다, D-3)
    특이점에서 나오는 inf/nan 은 여기서 죽이지 않는다 — 호출자가 sa_ok/isfinite 로 **버리고 센다**.
    """
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        return _face_fringe_raw(Nw, bp, pp, b, p, Ez, Hz, k, Z)


def _face_fringe_raw(Nw, bp, pp, b, p, Ez, Hz, k, Z=Z0):
    sbp, cbp = np.sin(bp), np.cos(bp)
    sb, cb = np.sin(b), np.cos(b)
    ctbp = cbp / sbp
    ctb = cb / sb
    cosg = sbp * sb * np.cos(p) + cbp * cb                       # (3.30) cos γ = û·ŝ
    mu = (cosg - cbp ** 2) / sbp ** 2                            # (3.29)
    a = _arccos_c(mu)                                            # (3.28)
    sa = np.sin(a)
    U = (pp < np.pi).astype(np.float64)                          # U(π−φ') — face 1 조명 여부

    den_po = np.cos(pp) + mu
    # (3.24) I^PO_1
    I_po = (2j * U / (k * sbp * den_po)
            * (np.sin(pp) / (Z * sbp) * Ez
               - (ctbp * np.cos(pp) + ctb * np.cos(p)) * Hz))
    # (3.25) M^PO_1
    M_po = -2j * Z * np.sin(p) * U / (k * sb * sbp * den_po) * Hz

    can = np.cos((np.pi - a) / Nw)
    san = np.sin((np.pi - a) / Nw)
    cpn = np.cos(pp / Nw)
    # (3.26) I_1
    I_t = ((2j / (k * sbp)) * (1.0 / Nw) / (cpn - can)
           * (np.sin(pp / Nw) / (Z * sbp) * Ez
              + (san / sa) * (mu * ctbp - ctb * np.cos(p)) * Hz)
           - (2j * ctbp / (k * Nw * sbp)) * Hz)
    # (3.27) M_1
    M_t = (2j * Z * np.sin(p) / (k * sbp * sb)
           * (1.0 / Nw) * san / sa / (can - cpn) * Hz)

    return I_t - I_po, M_t - M_po, den_po, sa, cpn - can


def _face_fringe_reg(Nw, bp, pp, b, p, Ez, Hz, k, Z=Z0,
                     sing_tol=SING_TOL, sing_delta=SING_DELTA):
    """_face_fringe + 제거가능 특이점(|cos φ' + μ|→0) 수치 정규화.

    왜 필요한가 — I_1 과 I^PO_1 의 분모는 μ = −cos φ' 에서 **동시에** 0 이 되고(그때
    a = π−φ' 이라 cos(φ'/N) − cos((π−a)/N) = 0), 차 I_1−I^PO_1 은 유한하다. 그런데 그 뺄셈이
    해석적으로 이미 수행된 비특이형은 **우리가 가진 어느 문헌에도 없다** — Öztürk (3.37)(3.38)
    도 U(π−φ)/(cos φ + μ₁) 과 (1/N)sin(φ/N)/(cos((π−a₁)/N) − cos(φ/N)) 을 각각 발산하는 두
    분수로 그대로 두고 있다(원문 확인). 그래서 0/0 을 직접 만나고 수치로 정규화한다.
    μ 는 φ' 에 의존하지 않으므로 φ' 만 ±δ 로 흔들면 특이면을 가로지른다 →
    대칭평균이 O(δ²) 오차로 극한값을 준다. (부작용: 절단오차 ~2.5e−5 상대.)
    """
    I_f, M_f, den_po, sa, den_t = _face_fringe(Nw, bp, pp, b, p, Ez, Hz, k, Z)
    bad = np.abs(den_po) < sing_tol
    n_reg = int(bad.sum())
    if n_reg:
        sel = np.where(bad)[0]
        acc_I = np.zeros(len(sel), dtype=np.complex128)
        acc_M = np.zeros(len(sel), dtype=np.complex128)
        Ezs = np.broadcast_to(np.asarray(Ez, np.complex128), pp.shape)[sel]
        Hzs = np.broadcast_to(np.asarray(Hz, np.complex128), pp.shape)[sel]
        for s in (+1.0, -1.0):
            ppd = pp[sel] + s * sing_delta
            Ii, Mi, _, _, _ = _face_fringe(Nw[sel], bp[sel], ppd, b[sel], p[sel],
                                           Ezs, Hzs, k, Z)
            acc_I += Ii
            acc_M += Mi
        I_f = I_f.copy(); M_f = M_f.copy()
        I_f[sel] = 0.5 * acc_I
        M_f[sel] = 0.5 * acc_M
    #  제거 불가능한 극(D-3): 전체전류 분모만 0 에 붙고 PO 분모는 멀쩡한 자리.
    #  ~bad 로 제거가능(정규화 처리) 자리를 제외한다.
    den_ok = ~((np.abs(den_t) < DEN_TOL) & (~bad))
    return I_f, M_f, sa, n_reg, den_ok


def fringe_eec(Nw, beta_p, phi_p, beta, phi, Ez, Hz, k, Z=Z0,
               sing_tol=SING_TOL, sing_delta=SING_DELTA, sina_tol=SINA_TOL):
    """양면(face1 − face2) 합성 프린지 EEC — (3.31)(3.32).

    face 2 는 좌표 치환 `z→−z, β→π−β, β'→π−β', φ→Nπ−φ, φ'→Nπ−φ'` 로 얻는다.
    z 축이 뒤집히므로 Ez, Hz 도 부호가 뒤집힌다 — 이 치환은 반사가 아니라 **회전**이라
    (x̂₂,ŷ₂,ẑ₂) 가 여전히 오른손계이고, 따라서 E 와 H 가 똑같이 벡터 성분으로 바뀐다.

    반환: (I_f, M_f, diag).
      diag['sa_ok']  : 진짜 특이점(|sin a|<sina_tol) 이 아닌 조각 마스크
      diag['den_ok'] : 제거 불가능한 전체전류 극(|cos(φ'/N)−cos((π−a)/N)|<DEN_TOL 인데 PO 분모는
                       안 작음) 이 **양 면 모두** 아닌 조각 마스크 (D-3)
    """
    Nw = np.asarray(Nw, np.float64)
    ones = np.ones_like(Nw)
    Ez = np.asarray(Ez, np.complex128) * ones
    Hz = np.asarray(Hz, np.complex128) * ones

    I1, M1, sa1, r1, d1 = _face_fringe_reg(Nw, beta_p, phi_p, beta, phi, Ez, Hz, k, Z,
                                           sing_tol, sing_delta)
    pp2 = np.mod(Nw * np.pi - phi_p, 2.0 * np.pi)
    p2 = np.mod(Nw * np.pi - phi, 2.0 * np.pi)
    I2, M2, sa2, r2, d2 = _face_fringe_reg(Nw, np.pi - beta_p, pp2, np.pi - beta, p2,
                                           -Ez, -Hz, k, Z, sing_tol, sing_delta)

    sa_ok = (np.abs(sa1) > sina_tol) & (np.abs(sa2) > sina_tol)
    den_ok = d1 & d2
    diag = dict(n_regularized=r1 + r2,
                sa_ok=sa_ok,
                den_ok=den_ok,
                n_den_pole=int((~den_ok).sum()),
                sin_a_min=float(min(np.abs(sa1).min(), np.abs(sa2).min())) if len(Nw) else None)
    return I1 - I2, M1 - M2, diag


# =========================================================================== #
#  3. 편파 기저 (전역 V/H) — PTD 를 붙이는 순간 편파를 정의해야 한다 (§9.2)
# =========================================================================== #
def pol_basis(u):
    """시선 û(표적→레이더)에 대한 (ĥ, v̂). 둘 다 û 에 수직 = 평면파 전기장이 놓일 수 있는 면.
    ĥ = ẑ_global × û 정규화(수평), v̂ = û × ĥ (수직). û ∥ ẑ_global 이면 ŷ_global 로 대체."""
    u = np.asarray(u, np.float64)
    zg = np.array([0.0, 0.0, 1.0])
    h = np.cross(zg, u)
    nh = np.linalg.norm(h)
    if nh < 1e-9:
        h = np.array([0.0, 1.0, 0.0])
    else:
        h = h / nh
    v = np.cross(u, h)
    return h, v / np.linalg.norm(v)


def _inc_fields(u_i, pol):
    """입사 평면파(진폭 1 V/m)의 (ê, ĥ_field, d̂). d̂ = −û_i 는 진행방향, H = (1/Z₀) d̂×ê."""
    h, v = pol_basis(u_i)
    e = v if str(pol).upper().startswith("V") else h
    d = -np.asarray(u_i, np.float64)
    hf = np.cross(d, e) / Z0
    return e, hf, d


# =========================================================================== #
#  4. 모서리 프린지 장 A_FW [m²]
# =========================================================================== #
def edge_field(edges: EdgeSet, fc, u_i, u_s=None, pol="V", origin=None, n_seg=1,
               metal_only=True, gamma_metal_min=GAMMA_METAL_MIN,
               visible_fn=None, sing_tol=SING_TOL, sing_delta=SING_DELTA,
               sina_tol=SINA_TOL, sinb_tol=SINB_TOL):
    """모서리 프린지 장 A_FW(û) [m²] — 면적분 A_PO 와 **같은 단위·같은 위상규약**.

    A_FW = **−½** Σ_seg [ Z (ŝ×(ŝ×t̂))·ê_r I^f + (ŝ×t̂)·ê_r M^f ] · L · e^{jk q·(r_c−origin)}
                                                                  · sinc(k L (q·t̂)/2),  q = û_i+û_s

    상수는 A_FW_CONST = −½ 이고 그 **부호는 유도로 고정**돼 있다(모듈 상단 (A)(B)(C)):
    문헌 EEC 복사적분 +jk/4π 를 우리 A 규약(E^s·ê = −jk/2π · A/…)으로 나눈 값이다.
    Rung 2 위상 게이트: 평판 on-cone 모서리에서 arg(A_code / A_analytic) = 0° (측정 ≤2.6e−14°).

    u_s=None 이면 모노스태틱(û_s = û_i) → q = 2û, sinc(k L t̂·û) 로 §7.1 과 일치.
    visible_fn(pts, u_i, u_s) -> bool (n,) : 조각 중심의 가림 판정 훅. None 이면 가림 없음.
    """
    u_i = np.asarray(u_i, np.float64)
    u_i = u_i / np.linalg.norm(u_i)
    u_s = u_i.copy() if u_s is None else np.asarray(u_s, np.float64) / np.linalg.norm(np.asarray(u_s, np.float64))
    lam = C0 / float(fc)
    k = 2.0 * np.pi / lam
    org = np.zeros(3) if origin is None else np.asarray(origin, np.float64)

    meta = dict(n_seg_total=0, n_seg_used=0, n_both_lit=0, n_one_lit=0, n_none_lit=0,
                n_drop_edge_on=0, n_drop_sin_a=0, n_drop_den_pole=0, n_drop_occluded=0,
                n_drop_material=0, n_regularized=0, sin_a_min=None,
                length_used_m=0.0, length_candidate_m=0.0)
    if len(edges) == 0:
        return 0.0 + 0.0j, meta

    sel = np.ones(len(edges), bool)
    if metal_only:
        sel = edges.gmin >= float(gamma_metal_min)
        meta["n_drop_material"] = int((~sel).sum())
    if not sel.any():
        return 0.0 + 0.0j, meta

    P0, P1 = edges.P0[sel], edges.P1[sel]
    T, Xa, Ya = edges.T[sel], edges.X[sel], edges.Y[sel]
    Lf, Nw = edges.L[sel], edges.Nw[sel]

    # ── 조각 분할 (곡선 모서리 직선근사 + 부분가시 처리 자리) ──
    ns = max(1, int(n_seg))
    fr = (np.arange(ns) + 0.5) / ns
    Rc = (P0[:, None, :] + fr[None, :, None] * (P1 - P0)[:, None, :]).reshape(-1, 3)
    Ls = np.repeat(Lf / ns, ns)
    T = np.repeat(T, ns, axis=0)
    Xa = np.repeat(Xa, ns, axis=0)
    Ya = np.repeat(Ya, ns, axis=0)
    Nw = np.repeat(Nw, ns)
    meta["n_seg_total"] = len(Ls)
    meta["length_candidate_m"] = float(Ls.sum())

    # ── 국소 각도 ──
    ui_t, ui_x, ui_y = T @ u_i, Xa @ u_i, Ya @ u_i
    us_t, us_x, us_y = T @ u_s, Xa @ u_s, Ya @ u_s
    cbp = -ui_t                                   # cos β' (d̂ = −û_i 이므로)
    sbp = np.sqrt(np.maximum(0.0, 1.0 - cbp ** 2))
    good = sbp > sinb_tol
    meta["n_drop_edge_on"] = int((~good).sum())

    beta_p = np.arccos(np.clip(cbp, -1.0, 1.0))
    phi_p = np.mod(np.arctan2(ui_y, ui_x), 2.0 * np.pi)
    beta = np.arccos(np.clip(us_t, -1.0, 1.0))
    phi = np.mod(np.arctan2(us_y, us_x), 2.0 * np.pi)

    # ── 조명 판정 (요구 3) ──
    #  face 1 은 φ' ∈ (0,π), face 2 는 Nπ−φ' ∈ (0,π) 일 때 조명된다. 이는 각각
    #  n̂₁·û_i > 0, n̂₂·û_i > 0 과 **정확히 동치**다(모듈 상단 좌표규약에서 유도).
    #  '하나라도 lit' 이면 후보다. 양쪽 다 lit 인지 한쪽만인지는 (3.24)(3.25) 의 단위계단
    #  U(π−φ') 가 face 별로 자동 처리한다 — Ufimtsev (3.33) 한면/(3.34) 양면 PO 항의
    #  Michaeli 대응물이다. 카운트만 따로 보고한다.
    lit1 = np.sin(phi_p) > 0.0
    lit2 = np.sin(Nw * np.pi - phi_p) > 0.0
    both = lit1 & lit2
    one = (lit1 ^ lit2)
    none = ~(lit1 | lit2)
    meta["n_both_lit"] = int(both.sum())
    meta["n_one_lit"] = int(one.sum())
    meta["n_none_lit"] = int(none.sum())
    good &= (lit1 | lit2)

    # 관측 방향도 외부영역(φ ∈ (0,Nπ))에 있어야 한다 — 쐐기 물질 안쪽은 무의미
    good &= (np.sin(phi) > 0.0) | (np.sin(Nw * np.pi - phi) > 0.0)

    if visible_fn is not None:
        vis = np.asarray(visible_fn(Rc, u_i, u_s), bool)
        meta["n_drop_occluded"] = int((good & ~vis).sum())
        good &= vis

    if not good.any():
        return 0.0 + 0.0j, meta

    idx = np.where(good)[0]
    e_inc, h_inc, _ = _inc_fields(u_i, pol)
    Ez = T[idx] @ e_inc                        # ẑ·Ē^i_0
    Hz = T[idx] @ h_inc                        # ẑ·H̄^i_0
    I_f, M_f, diag = fringe_eec(Nw[idx], beta_p[idx], phi_p[idx], beta[idx], phi[idx],
                                Ez, Hz, k, sing_tol=sing_tol, sing_delta=sing_delta,
                                sina_tol=sina_tol)
    meta["n_regularized"] = diag["n_regularized"]
    meta["sin_a_min"] = diag["sin_a_min"]

    # 진짜 특이점(sin a → 0, 면을 스치는 관측) 은 **버리고 센다** — 값을 지어내지 않는다.
    # 제거 불가능한 전체전류 극(D-3) 도 같이 버린다. 둘을 따로 세어 meta 에 남긴다.
    fin = np.isfinite(I_f) & np.isfinite(M_f)
    sa_only = diag["sa_ok"] & fin
    ok = sa_only & diag["den_ok"]
    meta["n_drop_sin_a"] = int((~sa_only).sum())
    meta["n_drop_den_pole"] = int((sa_only & ~diag["den_ok"]).sum())
    sa_ok = ok
    if not sa_ok.any():
        return 0.0 + 0.0j, meta
    idx = idx[sa_ok]
    I_f, M_f = I_f[sa_ok], M_f[sa_ok]

    # ── 기하 인자 + 해석적 선적분 (§7.1) ──
    e_rx = _inc_fields(u_s, pol)[0]            # 동일편파 수신 기저(co-pol, 전역 V/H)
    t = T[idx]
    s = u_s
    st = np.cross(np.broadcast_to(s, t.shape), t)          # ŝ×t̂
    sst = s[None, :] * (t @ s)[:, None] - t                # ŝ×(ŝ×t̂) = ŝ(ŝ·t̂) − t̂
    g_I = sst @ e_rx
    g_M = st @ e_rx

    q = u_i + u_s
    ph = np.exp(1j * k * ((Rc[idx] - org) @ q))
    xs = 0.5 * k * Ls[idx] * (t @ q)
    sc = np.sinc(xs / np.pi)                               # sin(x)/x

    #  ⭐ 부호 포함 상수. A_FW_CONST = −½ 이며 −1 은 A 규약의 −jk/2π 에서 온다(모듈 상단 (A)(C)).
    #  땜질용 −1 이 아니다: +½ 로 되돌리면 Rung 2 위상 게이트가 정확히 180° 로 깨진다.
    A = A_FW_CONST * np.sum((Z0 * g_I * I_f + g_M * M_f) * Ls[idx] * ph * sc)

    meta["n_seg_used"] = len(idx)
    meta["length_used_m"] = float(Ls[idx].sum())
    return complex(A), meta


# =========================================================================== #
#  5. 표면 PO + 모서리 PTD  (스위치 ptd=True/False, 기본 False)
# =========================================================================== #
def _po_field_dirs(P, Nv, dA, fc, az_deg, el_deg=0.0, w=None):
    """rcs_po.rcs_from_points 의 σ 직전 복소장 E(û). **연산 순서까지 원본과 동일**하게 복제했다
    (원본은 σ 만 돌려주므로 코히어런트 가산에 쓸 수 없다). 비트동일성은 스모크가 검증한다."""
    lam = C0 / fc
    k = 2 * np.pi / lam
    U = _look_dirs(az_deg, el_deg)
    PU = P @ U.T
    NU = Nv @ U.T
    illum = NU > 0
    amp = dA if w is None else dA * w
    integrand = np.where(illum, NU, 0.0) * amp[:, None] * np.exp(1j * 2 * k * PU)
    return integrand.sum(axis=0)


def rcs_po_ptd(mesh, fc, az_deg, el_deg=0.0, spacing=None, gamma=None,
               ptd=False, pol="V", edges=None, allow_coarse_po=False, **edge_kw):
    """PO 면적분(+선택적 PTD 모서리항) 모노스태틱 σ(az) [m²] 와 비용/진단 메타.

    ptd=False (기본) : **rcs_po.rcs_from_points 를 그대로 호출**한다 → 기존 결과 보존.
                       기본 간격도 예전 그대로 λ/7 이다(비트 동일성 유지).
    ptd=True         : σ = (4π/λ²)|E_PO + A_FW|². PO 는 스칼라, 프린지는 편파 pol.
                       ⚠ 이때 PO 점구름 간격은 **λ/20 이하여야 한다**(D-8): 프린지 항은
                       *정확* PO 전류에 대해 정의됐는데 우리가 더하는 상대는 중점구적 PO 다.
                       λ/7 에서 그 구적오차가 프린지 진폭의 3~11 % 라 '보정'과 '자기 오차 상쇄'
                       가 분리되지 않는다. 진단 목적이면 allow_coarse_po=True 로 명시적으로 뚫는다.

    반환 (sigma[(A,)], meta). meta 에 t_surface_s / t_edge_s / t_extract_s 비용 계측.
    """
    lam = C0 / float(fc)
    if spacing is None:
        spacing = lam / (PTD_SPACING_MAX_DIV if ptd else 7.0)
    elif ptd and float(spacing) > lam / PTD_SPACING_MAX_DIV * (1.0 + 1e-9):
        if not allow_coarse_po:
            raise ValueError(
                "ptd=True 인데 PO 간격이 λ/%g 보다 성기다 (spacing=%.4g m, λ/%g=%.4g m). "
                "PO 중점구적 오차가 프린지 항과 섞인다(D-8). λ/%g 이하로 주거나, 진단이면 "
                "allow_coarse_po=True 를 명시하라."
                % (PTD_SPACING_MAX_DIV, float(spacing), PTD_SPACING_MAX_DIV,
                   lam / PTD_SPACING_MAX_DIV, PTD_SPACING_MAX_DIV))
    az = np.atleast_1d(np.asarray(az_deg, float))

    t0 = time.perf_counter()
    if gamma is not None:
        P, Nv, dA, w = mesh_to_points(mesh, spacing, gamma=gamma)
    else:
        P, Nv, dA = mesh_to_points(mesh, spacing)
        w = None
    t_pts = time.perf_counter() - t0

    meta = dict(ptd=bool(ptd), pol=str(pol), fc_hz=float(fc), lam_m=lam,
                spacing_m=float(spacing), n_points=int(len(dA)),
                spacing_lambda_div=float(lam / float(spacing)),
                po_spacing_ok_for_ptd=bool(float(spacing) <= lam / PTD_SPACING_MAX_DIV
                                           * (1.0 + 1e-9)),
                t_pointcloud_s=t_pts, t_extract_s=0.0, t_edge_s=0.0,
                approximations=list(APPROXIMATIONS), not_implemented=list(NOT_IMPLEMENTED),
                open_defects=list(OPEN_DEFECTS),
                normalization_unverified=False,
                sign_convention_verified=dict(SIGN_CONVENTION_VERIFIED))

    if not ptd:
        t0 = time.perf_counter()
        sig = rcs_from_points(P, Nv, dA, fc, az, el_deg, w=w)
        meta["t_surface_s"] = time.perf_counter() - t0
        meta["edge"] = None
        return sig, meta

    t0 = time.perf_counter()
    E = _po_field_dirs(P, Nv, dA, fc, az, el_deg, w=w)
    meta["t_surface_s"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    if edges is None:
        edges = extract_edges(mesh, gamma=gamma,
                              sharp_deg=edge_kw.pop("sharp_deg", SHARP_DEG_DEFAULT),
                              weld_tol=edge_kw.pop("weld_tol", WELD_TOL_DEFAULT))
    meta["t_extract_s"] = time.perf_counter() - t0
    meta["edges"] = dict(edges.stats)

    t0 = time.perf_counter()
    U = _look_dirs(az, el_deg)
    A_edge = np.zeros(len(az), dtype=np.complex128)
    emeta = None
    for i, u in enumerate(U):
        a, m = edge_field(edges, fc, u, pol=pol, origin=None, **edge_kw)
        A_edge[i] = a
        if emeta is None:
            emeta = {kk: (0 if kk.startswith(("n_", "length_")) else vv) for kk, vv in m.items()}
        for kk, vv in m.items():
            if vv is None:
                continue
            if kk.startswith(("n_", "length_")):
                emeta[kk] = emeta.get(kk, 0) + vv
            elif kk == "sin_a_min":
                emeta[kk] = vv if emeta.get(kk) is None else min(emeta[kk], vv)
    meta["t_edge_s"] = time.perf_counter() - t0
    meta["edge"] = emeta
    meta["A_po_abs"] = np.abs(E).tolist()
    meta["A_edge_abs"] = np.abs(A_edge).tolist()

    sig = (4 * np.pi / lam ** 2) * np.abs(E + A_edge) ** 2
    return sig, meta


def sbr_phase_origin(mesh):
    """rcs_sbr 이 쓰는 위상 원점 — bbox 중심 `0.5*(V.max(0)+V.min(0))`. **메쉬에서 직접 만든다.**"""
    V = np.asarray(mesh.v, dtype=np.float64)
    return 0.5 * (V.max(axis=0) + V.min(axis=0))


def attach_to_sbr_field(E_sbr, mesh, fc, u, origin=None, pol="V", edges=None, gamma=None,
                        origin_tol=None, **edge_kw):
    """SBR 복소장(rcs_sbr.sbr_field 반환값, 단위 m²)에 모서리항을 더해 σ 를 낸다.

    origin : 기본 None → **메쉬에서 직접 유도**한다(`sbr_phase_origin`, rcs_sbr 과 같은 식).
             값을 주면 유도값과 대조해서 어긋나면 **예외를 던진다** (D-10). 예전에는 호출자를
             그냥 믿었고, 원점이 어긋나면 코히어런트 합이 조용히 잡음이 됐다.
    origin_tol : [m] 대조 허용오차. 기본 λ/1000 (위상 0.36°).
    ⚠ 이 경로는 Mitsuba/GPU 가 필요해 아직 **실행 검증하지 않았다** — 산술만 순수 함수다.
      가림(occlusion)도 visible_fn 훅을 주지 않으면 여전히 없다.
    """
    lam = C0 / float(fc)
    org = sbr_phase_origin(mesh)
    if origin is not None:
        tol = (lam / 1000.0) if origin_tol is None else float(origin_tol)
        d = float(np.max(np.abs(np.asarray(origin, np.float64) - org)))
        if d > tol:
            raise ValueError(
                "attach_to_sbr_field: 넘겨준 origin 이 메쉬 bbox 중심과 %.4g m 어긋난다 "
                "(허용 %.4g m). SBR 장과 모서리항이 다른 위상원점을 쓰면 코히어런트 합이 "
                "무의미해진다(anatomy q4)." % (d, tol))
    if edges is None:
        edges = extract_edges(mesh, gamma=gamma)
    A, m = edge_field(edges, fc, u, pol=pol, origin=org, **edge_kw)
    Et = complex(E_sbr) + A
    return (4.0 * np.pi / lam ** 2) * abs(Et) ** 2, A, m


# =========================================================================== #
#  6. Ufimtsev 참조 계수 (Rung 1 단위검사 전용 — 본선 계산에는 쓰지 않는다)
# =========================================================================== #
def ufimtsev_fg(phi, phi0, n):
    """(4.08) 전체 쐐기 회절계수. n = α/π. 반환 (f=soft/E, g=hard/H)."""
    s = np.sin(np.pi / n) / n
    A = 1.0 / (np.cos(np.pi / n) - np.cos((phi - phi0) / n))
    B = 1.0 / (np.cos(np.pi / n) - np.cos((phi + phi0) / n))
    return s * (A - B), s * (A + B)


def ufimtsev_fringe(phi, phi0, alpha):
    """(4.07) f¹ = f − f⁰, g¹ = g − g⁰. (3.33) 한면조명 / (3.34) 양면조명 자동 선택."""
    n = alpha / np.pi
    f, g = ufimtsev_fg(phi, phi0, n)
    if 0 < phi0 < alpha - np.pi:
        d = np.cos(phi) + np.cos(phi0)
        f0, g0 = np.sin(phi0) / d, -np.sin(phi) / d
    else:
        d1 = np.cos(phi) + np.cos(phi0)
        d2 = np.cos(alpha - phi) + np.cos(alpha - phi0)
        f0 = np.sin(phi0) / d1 + np.sin(alpha - phi0) / d2
        g0 = -np.sin(phi) / d1 - np.sin(alpha - phi) / d2
    return f - f0, g - g0


# =========================================================================== #
#  메타에 항상 실려 나가는 정직성 목록
# =========================================================================== #
#  ⭐ 부호 규약 검증 기록 — meta['sign_convention_verified'] 로 항상 실려 나간다(D-9).
#  smoke_ptd.py 의 (f) 위상 게이트가 이 숫자를 매번 다시 재고, 어긋나면 FAIL 한다.
SIGN_CONVENTION_VERIFIED = dict(
    constant="A_FW = A_FW_CONST * sum[...] with A_FW_CONST = -0.5",
    derivation="EEC radiation integral +jk/4pi (Oztuerk 2002 eq 3.7, Gao 2012 eq 3) divided by "
               "the far-field constant of OUR m^2 amplitude convention, E^s.e = -(jk/2pi) A_PO "
               "e^{-jkr}/r. The minus of that second constant comes from d_hat = -u_hat in "
               "H^i = (1/Z0) d_hat x e_hat. doc 9.1 kept only the magnitude lam*k/4pi = 1/2 and "
               "lost that relative sign.",
    gate="arg(A_code / A_analytic_Ufimtsev) == 0 deg on the flat-plate on-cone edges "
         "(NOT |ratio|, which passes with a 180 deg error)",
    measured_after_fix=dict(max_abs_ratio_dev=3.3e-15, max_abs_phase_deg=2.6e-14,
                            theta_deg=[10, 25, 40, 65, 80], pol=["H", "V"]),
    fixed="2026-08-03 (defect D-1)",
)

#  ⭐ D-11 의 출처규칙(provenance rule): 어떤 PTD 출력이든 **아직 열려 있는 결함**을 함께 싣는다.
#  블로커가 제기된 뒤에 나온 산출물이 그것을 인용도 반박도 하지 않는 일이 다시 없도록,
#  meta['open_defects'] 로 기계적으로 따라 나가게 만든다. 닫힌 결함은 목록에서 뺀다.
OPEN_DEFECTS = [
    "D-4 OPEN: no claim about PTD and the frequency band slope is supported yet. Any re-fit must "
    "report the paired-difference standard error, the Durbin-Watson statistic (OLS was invalid: "
    "DW = 0.32) or a HAC/block-bootstrap SE, AND the sharp_deg sensitivity band; the fit-window "
    "nuisance measured ~30x the effect.",
    "D-5 OPEN: on mini5pro the near-flat tessellation-seam population alone produces a LARGER "
    "edge amplitude than the whole metal edge set, and the seam class does not converge away "
    "with mesh refinement on a smooth sphere. Report every drone PTD number as a band over "
    "sharp_deg in 5..30 deg. The physical fix (reconstruct N from the underlying CAD surface "
    "instead of triangle normals) is NOT implemented.",
    "D-6 OPEN: the 2-D MoM plate reference is validated only against a closed circular cylinder "
    "(no edge singularity). Its uniform pulse basis converges at O(1/M) on the open strip, so "
    "the Richardson residual at M = 720 is ~0.071 dB, about 1.8x the self-comparison figure "
    "shipped in ptd_plate_validation.reference_convergence. No external published strip datum "
    "has been digitised yet.",
    "D-10 PARTIAL: attach_to_sbr_field now derives and validates the phase origin, but the SBR "
    "path has still never been executed (needs Mitsuba/GPU) and edge occlusion is still absent "
    "unless visible_fn is supplied.",
    "G1 OPEN (literature): the truncated-wedge (Johansen 1996 / Gao 2012) correction EEC is "
    "absent, so part of the second-order edge diffraction is missing. This is the dominant "
    "unquantified systematic for few-lambda drone parts.",
]

APPROXIMATIONS = [
    "polarization: PO surface term stays SCALAR (|Gamma| weighted, no pol); only the fringe "
    "term carries polarization. The same scalar PO field is added to BOTH V and H. (doc 9.2)",
    "receive polarization = transmit polarization in a fixed GLOBAL (h,v) basis (co-pol). "
    "No BSA/FSA sign convention was applied; cross-pol is not computed.",
    "normalization A_FW = -1/2 * [...]: magnitude 1/2 = lam*k/(4pi) as in doc 9.1, sign fixed by "
    "the derivation in SIGN_CONVENTION_VERIFIED. Both magnitude AND sign are now verified against "
    "the analytic Ufimtsev edge wave on the flat plate (|ratio| - 1 = 3.3e-15, |arg| = 2.6e-14 "
    "deg). The old 'UNVERIFIED' warning is retired.",
    "removable Ufimtsev singularity |cos(phi')+mu| < 1e-3 is regularized by a symmetric "
    "phi' +- 5e-3 rad average (O(delta^2) truncation ~2.5e-5 relative), because the analytic "
    "difference is not available in closed non-singular form anywhere in the literature we hold, "
    "including Oztuerk (3.37)/(3.38) where the two fractions still diverge separately.",
    "edge is treated as piecewise straight; curved edges rely on n_seg subdivision.",
    "dihedral threshold sharp_deg=5 deg discards near-flat tessellation seams (amplitude "
    "<= -19 dB per edge, doc 3.7). It is NOT a pure speed optimization: on a smooth tessellated "
    "sphere this seam class does not converge away with refinement (our own measurement: "
    "amplitude floor -32.5 dB at kr=13.1, -40.6 dB at kr=36.7, log-log slope -0.62 instead of "
    "-1), and on mini5pro the |alpha-180|<10 deg seam population alone produces a LARGER edge "
    "amplitude (-15.6 dB) than the whole metal edge set (-17.8 dB). Any drone number must be "
    "reported as a band over sharp_deg, never as a single value.",
    "fringe coefficients are PEC-derived; applied only where BOTH adjacent faces have "
    "|Gamma| >= 0.999 (metal_only=True, doc 9.3). No |Gamma| scaling heuristic is used.",
    "the fringe is defined against the EXACT PO current but is added to a midpoint-quadrature "
    "PO surface integral. rcs_po_ptd therefore requires spacing <= lam/20 when ptd=True; at "
    "lam/7 the PO quadrature error alone is 3-11 % of the fringe amplitude on a 6x40 lambda "
    "plate (2-4 % at lam/20).",
]

NOT_IMPLEMENTED = [
    "TW (truncated wedge, Johansen 1996 / Gao 2012) correction EECs — term is ABSENT (not "
    "approximated by anything). This is the known weakest point for few-lambda targets (doc 4.4).",
    "second-order (edge-to-edge) diffraction — ABSENT (0).",
    "corner / vertex diffraction (Hansen 1991 quarter plane) — ABSENT (0).",
    "creeping waves — ABSENT (0).",
    "edge occlusion by other parts of the target — ABSENT unless a visible_fn hook is supplied; "
    "only the adjacent-face normal gate is applied.",
    "cross-polarized (HV/VH) scattering — not computed.",
    "true Ufimtsev singularity sin(a) -> 0 (observation grazing along a face) — those segments "
    "are DROPPED and counted, no substitute value is invented.",
    "edge-on incidence sin(beta') < 1e-3 — segments DROPPED and counted.",
    "near-zero exterior wedge angle (N < 0.05, i.e. two nearly coincident faces produced by the "
    "CAD boolean union) — DROPPED and counted as n_dropped_thin_wedge. Out of scope for the "
    "wedge formulation; no substitute value is invented.",
    "reentrant (concave) edges, exterior wedge angle alpha < 180 deg i.e. N < 1 — DROPPED by "
    "default and counted (n_dropped_reentrant, length_reentrant_m, reentrant_length_fraction). "
    "For N < 1 the total-current denominator cos(phi'/N) - cos((pi-a)/N) acquires extra zeros "
    "that the single-bounce PO denominator does not share (they are the multiple-reflection "
    "boundaries of a concave corner), and N = 1/(2m) is an exact pole. First-order PTD with a "
    "single-bounce PO subtraction cannot represent that uniformly. Measured before this guard: "
    "on s1000plus 576 metal edges sat at N = 0.169, 6.5 % of the metal edge length, and produced "
    "99.99 % of the edge field (+13.9 dB of a +13.8 dB 'effect'). keep_reentrant=True re-enables "
    "them for diagnostics only.",
    "SBR attachment (attach_to_sbr_field) derives the phase origin from the mesh and validates "
    "any caller-supplied origin, but the path is still NOT exercised end to end (needs "
    "Mitsuba/GPU). Every PTD number in the repo therefore comes from the CPU point-cloud PO "
    "engine WITHOUT occlusion: with visible_fn=None the only gate is lit1|lit2, which passes "
    "~56 % of the metal edge length on a closed airframe including edges behind it.",
]


if __name__ == "__main__":
    from rcs_po import _plate_mesh
    m = _plate_mesh(0.30)
    es = extract_edges(m)
    print("평판 모서리:", es.stats)
