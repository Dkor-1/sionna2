# -*- coding: utf-8 -*-
"""
rcs_po.py — (report2) 물리광학(Physical Optics)으로 드론 RCS 계산
==================================================================

왜 광선추적(Sionna RT) 대신 PO 인가? — **Sionna RT 의 기본 path solver 에는 산란적분 단계가 없다**(검증 완료)
  ⚠ 주장의 범위를 정확히: **"레이트레이싱은 RCS 를 못 낸다"는 거짓**이다. SBR(GO+PO)은 기하에서
    RCS 를 계산해 낸다(상용 EM 솔버의 표준 고주파 기법). 참인 명제는 훨씬 좁다 —
    **"산란적분 단계가 없는 전파(propagation)용 레이트레이서에서는 표적 σ 가 창발하지 않는다"**
    (Sionna RT 2.0.1 의 기본 solver 가 여기 해당).
  Sionna RT 의 path solver 가 표적에서 만드는 경로는 두 종류뿐이고 둘 다 σ 의 함수가 아니다:
    · SPECULAR = image-source(무한거울) — 금속 평판의 변을 0.2→4 m 로 키워 σ 를 52 dB 바꿔도
      직접파 대비 진폭비가 −7.91 dB 로 **불변**(산포 0.00 dB).
    · DIFFUSE  = 산란계수 S 의 함수 — 같은 금속구에서 S 만 0.2→1.0 으로 올리면 +15.8 dB 이동(S² 법칙).
      이론값에 맞추려면 S≈0.85 가 필요 → RT 로 PO 를 맞추는 건 **S 를 피팅하는 순환논법**.
    · 게다가 물리적으로 옳은 PEC 금속구(S=0)에서는 RT 가 **경로를 아예 만들지 못한다**(전 조건 0개).
  즉 하이브리드(표적=PO, 환경=RT)는 **기본 solver 를 쓰는 한 필연**이다. 정공법이 없는 건 아니다 —
  custom PathSolver 로 in-Sionna 산란적분을 넣는 길이 존재한다(메인테이너 확인). 우리가 안 하는
  이유는 **부재가 아니라 비용/충실도**다.
  근거·재현: benchmark/verify_rt_no_rcs.py · docs/VERIFY_RT_VS_PO.md

PO 핵심 (모노스태틱 후방산란, **재질 가중**)
  표적 표면을 점들로 잘게 나누고, 레이더를 향한(조명된) 면만 골라
  위상을 맞춰 더합니다. 각 점에는 부위 재질의 진폭 반사계수 |Γ| 를 곱합니다:
      E(û) = Σ (n̂·û>0) |Γ|·(n̂·û) ΔA · exp(j·2k·(r·û))
      σ    = (4π/λ²) · |E|²
  û = 표적→레이더 방향, k=2π/λ, r=표면점 위치, n̂=면 법선.
  |Γ|=1(전부 PEC)이면 고전 PO — 검증 표적(금속 평판·구)이 이 경우입니다.

재질 가중이 필요한 이유
  플라스틱 셸(εr≈2.7)은 RF 에 반투명(|Γ|≈0.3)이라, 실물 드론의 후방산란은 셸이
  아니라 **배터리·모터·PCB·카메라 금속**(drones.build_frame 의 내부 산란체 포함)이
  지배합니다. 전부 PEC 로 두면 셸 기여가 ~10 dB 과대계상됩니다.
  그룹별 |Γ| 는 drones.GROUP_GAMMA / drone_gamma_map() 에 근거와 함께 정의.
  (반투명 셸을 통과해 내부가 보이는 효과는 '셸 |Γ| 축소 + 내부 |Γ|=1 합산'으로
  1차 근사 — 셸 투과손실(왕복 ~0.5 dB)은 무시.)

검증 (이 모듈이 맞다는 근거)
  * **구(반지름 r) ↔ 해석적 PO** — 이것이 유일한 진짜 근거다. 구의 해석적 PO 적분
    E = 2πr²[e^{jb}(1/(jb)+1/b²) − 1/b²], b=2kr 과 비교하면 우리의 이산 PO 가 **±0.015 dB** 로 재현한다.
    (해석적 PO 자신은 GO(πr²) 대비 +0.35/−0.01/−0.06 dB @1.84/3.5/5.21 GHz — 이는 PO 의 O(1/ka) 항이다.)
  * ⚠️ **평판(4πA²/λ²) 검증은 근거로 쓰지 말 것** — 수직입사에서 P·û ≡ 0 이라 위상항이 사라져,
    커널에 버그(위상계수 2k→k, 부호반전, obliquity 제거 등)를 주입해도 여전히 +0.00 dB 가 나온다.
    **진단력 0의 항등식**이다. 구 검증만이 커널을 실제로 시험한다.

정확도 한계(솔직히)
  * 이 PO 는 **자기차폐(self-shadowing)·다중반사(multi-bounce)를 무시**합니다.
    - 자기차폐 무시: 시선을 향한 면(n̂·û>0)이면 앞쪽 구조에 가려지는 뒷면도 그대로 coherent 합산 →
      평균적으로 **과대**계상 방향(코히런트 합이라 각도별 엄밀한 상한은 아님).
    - 다중반사 무시: 암-동체 이면반사·로터-모터 코너 반사 기여가 애초에 합에 들어오지 않음 → **과소**계상 방향.
    두 오차의 부호가 반대라 오목한 드론(암·로터·짐벌)의 **절대 RCS 순 편향은 형상 의존**이며 한 방향으로
    단정할 수 없습니다. 볼록한 평판·구 검증엔 두 오차 모두 없습니다.
    (중복 삼각형에 의한 '이중계산'은 아님 — 메쉬는 거의 manifold. 순수 물리모델 근사 한계.)
  * 법선은 **바깥(outward)** 이어야 조명면 판정이 맞습니다(geom 프리미티브 winding 일관성 필요).
"""
from __future__ import annotations

import numpy as np

C0 = 299792458.0


# --------------------------------------------------------------------------- #
#  메쉬 → 표면 점구름(point cloud): 위치 r, 법선 n̂, 면적요소 ΔA
# --------------------------------------------------------------------------- #
def mesh_to_points(mesh, spacing, gamma=None):
    """삼각형들을 spacing[m] 간격 점으로 잘게 나눠 (P, N, dA[, w]) 를 돌려준다.
    gamma : 그룹→진폭 반사계수 |Γ| dict. 주면 점별 가중 w 를 **네 번째 값으로 추가 반환**
            (없는 그룹은 1.0=PEC). None(기본)이면 기존과 동일한 3-튜플."""
    V = np.array(mesh.v)
    Ps, Ns, dAs, Ws = [], [], [], []
    for fi, (ia, ib, ic) in enumerate(mesh.f):
        v0, v1, v2 = V[ia], V[ib], V[ic]
        e1, e2 = v1 - v0, v2 - v0
        nrm = np.cross(e1, e2)
        area = 0.5 * np.linalg.norm(nrm)
        if area < 1e-12:
            continue
        nhat = nrm / (2 * area)
        emax = max(np.linalg.norm(e1), np.linalg.norm(e2), np.linalg.norm(v2 - v1))
        N = max(1, int(np.ceil(emax / spacing)))
        # 바리센트릭 격자 (u,v)=(i+.5)/N, 삼각형 내부(u+v<=1)만
        ij = [(i, j) for i in range(N) for j in range(N) if (i + 0.5) + (j + 0.5) <= N]
        if not ij:
            ij = [(0, 0)]
        uv = (np.array(ij) + 0.5) / N
        pts = v0 + uv[:, :1] * e1 + uv[:, 1:] * e2
        Ps.append(pts)
        Ns.append(np.tile(nhat, (len(pts), 1)))
        dAs.append(np.full(len(pts), area / len(pts)))
        if gamma is not None:
            Ws.append(np.full(len(pts), float(gamma.get(mesh.g[fi], 1.0))))
    out = (np.vstack(Ps), np.vstack(Ns), np.concatenate(dAs))
    return out + (np.concatenate(Ws),) if gamma is not None else out


def _look_dirs(az_deg, el_deg=0.0):
    """방위각/고각[deg] → 표적→레이더 단위벡터 û (…,3)."""
    az = np.radians(np.atleast_1d(az_deg)); el = np.radians(el_deg)
    return np.stack([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def rcs_from_points(P, N, dA, fc, az_deg, el_deg=0.0, w=None):
    """점구름에서 PO 모노스태틱 RCS σ(az)[m²] 를 계산(벡터화).
    w : 점별 진폭 반사계수 |Γ| (mesh_to_points(gamma=…) 의 4번째 반환). None=PEC."""
    lam = C0 / fc; k = 2 * np.pi / lam
    U = _look_dirs(az_deg, el_deg)                 # (A,3)
    PU = P @ U.T                                   # (Np,A) 위상거리
    NU = N @ U.T                                   # (Np,A) 면법선·시선
    illum = NU > 0
    amp = dA if w is None else dA * w              # 재질 가중 진폭
    integrand = np.where(illum, NU, 0.0) * amp[:, None] * np.exp(1j * 2 * k * PU)
    E = integrand.sum(axis=0)                      # (A,)
    return (4 * np.pi / lam**2) * np.abs(E)**2     # (A,) σ [m²]


def po_field_dir(P, N, dA, fc, u, w=None):
    """단일 시선 단위벡터 û 의 **복소 산란장** E = Σ(n̂·û>0)|Γ|(n̂·û)·ΔA·exp(j2k·P·û).
    (rcs_from_points 의 σ 직전 값. 마이크로도플러용 — 위상이 필요하므로 σ 가 아닌 E.)"""
    k = 2 * np.pi * fc / C0
    NU = N @ np.asarray(u); PU = P @ np.asarray(u)
    amp = dA if w is None else dA * w
    return np.sum(np.where(NU > 0, NU, 0.0) * amp * np.exp(1j * 2 * k * PU))


# --------------------------------------------------------------------------- #
#  드론 RCS (메쉬에서 바로)
# --------------------------------------------------------------------------- #
#  ⚠ 2026-07-14 — **기본 엔진이 SBR 로 바뀌었다**
#
#  기존 순수 PO(`engine="po"`)에는 **가림(self-occlusion)이 없다** — 광선이 앞면에 막혀
#  실제로는 안 보이는 뒷면·내부면까지 전부 적분에 넣는다. 측정 결과 드론 RCS 를 **+5.3 dB
#  과대평가**했다(mavic4pro, el=15°, 방위평균: PO −16.83 → SBR −22.11 dBsm).
#
#  SBR(`engine="sbr"`, 기본)은 Mitsuba 광선이 "실제로 맞은 첫 지점"만 적분하므로 가림이 공짜다.
#  기준해 검증: 평판 −0.01 dB(정확 PO 4πA²/λ² 대비), 금속구 +0.39 dB — ⚠ 이 구 값은
#  **πr² 점근 기준으로 잰 옛 숫자**다. 지금 rcs_sbr.validate() 는 해석 PO(커널의 과녁)와
#  정확 Mie 두 기준으로 나란히 적는다(3.5 GHz·r=0.5 m 에서 둘은 0.152 dB 떨어져 있다).
#  → 오목부 다중반사가 필요하면 rcs_sbr.rcs_sbr(max_bounce=3) 을 직접 부를 것(−0.23 dB 추가).
#
#  engine="po" 는 **비교·검증용으로만** 남긴다 (report6 이 두 엔진을 대조한다).
RCS_ENGINE_DEFAULT = "sbr"


def drone_rcs_pattern(drone_key, fc, az_deg, el_deg=0.0, spacing=None, materials=True,
                      engine=None):
    """드론 1종의 RCS(az)[m²].

      engine="sbr" (기본) : Mitsuba 광선 + PO 적분. **가림 포함**. GPU.
      engine="po"         : 옛 순수 PO(점구름). **가림 없음** — 비교용으로만.
      materials=False     : 전부 PEC(고전 PO) — 재질 민감도 비교용.

    반환: (sigma[m²], n_points)  — n_points 는 SBR 에선 방위당 광선 수."""
    from drones import DRONES, build_drone, drone_gamma_map, DRONE_GROUP_MAT
    lam = C0 / fc
    spec = DRONES[drone_key]
    mesh = build_drone(spec)
    eng = engine or RCS_ENGINE_DEFAULT

    if eng == "sbr":
        from rcs_sbr import rcs_sbr_batch, DEFAULT_DIV
        gm = ({g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()} if materials
              else {g: 1.0 for g in DRONE_GROUP_MAT})           # PEC 비교모드
        d = spacing or lam / DEFAULT_DIV
        sig = rcs_sbr_batch(mesh, gm, fc, az_deg=az_deg, el_deg=el_deg, spacing=d,
                            cache_key=(drone_key, round(fc / 1e6), bool(materials)))
        n = int(np.ceil(2 * (np.linalg.norm(np.asarray(mesh.v) -
                                            np.asarray(mesh.v).mean(0), axis=1).max() * 1.15 + 3 * d) / d)) ** 2
        return np.atleast_1d(sig) if np.ndim(az_deg) else sig, n

    spacing = spacing or lam / 7.0
    if materials:
        P, N, dA, w = mesh_to_points(mesh, spacing, gamma=drone_gamma_map(spec))
    else:
        P, N, dA = mesh_to_points(mesh, spacing)
        w = None
    return rcs_from_points(P, N, dA, fc, az_deg, el_deg, w=w), len(dA)


def drone_rcs_pattern_bw(drone_key, fc, bw_hz, az_deg, el_deg=0.0, n_f=9, **kw):
    """**대역폭 평균 RCS** — 실제 레이더(대역 B)가 관측하는 값.

    왜 필요한가: 단일 주파수 코히런트 PO 는 위상이 무작위로 더해져 |E|² 가 지수분포(레일리)를
    따르므로, 방위 패턴에 **깊은 널**이 생긴다.
    그런데 그 널들은
      · **개별적으로는 수치 아티팩트**다 — 메쉬 이산화를 λ/7→λ/12 로 바꾸면 방위평균은 0.03 dB
        밖에 안 변하는데(패턴 상관 0.995), **널의 깊이가 6~17 dB 씩 요동**한다
        (az 0.5° 샘플링, mavic4pro @3.5 GHz: el=0° 최저 −59.2→같은 방위에서 −51.1 dBsm,
         el=22° −62.5→−45.4 dBsm). 널의 **위치**(상위 10개 방위)는 오히려 안정적이므로
        — 널이 '어디' 인지가 아니라 '얼마나 깊은지' 가 신뢰 불가다. (거친 2° 샘플링에서는
         깊이가 서로 몇 dB 이내인 널들 사이로 argmin 이 점프해 위치까지 변한 것처럼 보인다.)
      · **실제로 관측되지도 않는다** — 유한 대역폭이 널을 메운다. 5G 100 MHz 로 평균하면 최저값이
        −59.2 → −45.0 dBsm 로 **+14 dB** 올라오고, 여기에 3° 각도창까지 주면 −41.0 dBsm 이 된다
        (el=0°, λ/7, az 0.5° 샘플링). 이 대역+각도 평균 패턴은 이산화에 안정적이다(λ/7 vs λ/12:
         상관 0.998, RMS 0.31 dB, 최저점 방위 328.0° 로 동일).
    따라서 방위 패턴 그림은 **대역 평균**(비코히런트)으로 그리는 것이 정직하다. 방위평균 RCS 는
    대역평균 여부와 무관하게 같으므로(−20.8 dBsm), 앵커링·막대그래프 수치에는 영향이 없다.
    """
    freqs = np.linspace(fc - bw_hz / 2, fc + bw_hz / 2, n_f) if n_f > 1 else [fc]
    acc, npts = None, 0
    for f in freqs:
        s, npts = drone_rcs_pattern(drone_key, f, az_deg, el_deg, **kw)
        acc = s if acc is None else acc + s
    return acc / len(freqs), npts


def angular_smooth(sigma, win_deg, az_step_deg):
    """방위 패턴을 win_deg 창으로 **전력 평균**(비코히런트) — 실측이 자연히 하는 평활.
    근거: 실제 관측은 (a) 안테나 빔폭, (b) 표적의 요(yaw) 지터·진동, (c) 유한 각도 샘플링 때문에
    수 도(度) 창에서 평균된 값을 본다. 3° 창이면 로브 피크(−11.5→−11.7 dBsm)와 방위평균(−20.8)은
    사실상 그대로인데, 로브 사이 골의 최저값은 −45 → −41 dBsm 로 올라온다(needle 소멸).
    """
    n = max(1, int(round(win_deg / az_step_deg)))
    if n <= 1:
        return sigma
    k = np.ones(n) / n
    pad = np.r_[sigma[-n:], sigma, sigma[:n]]          # 방위는 순환축
    return np.convolve(pad, k, "same")[n:-n]


def dbsm(sigma):
    """m² → dBsm."""
    return 10 * np.log10(np.maximum(sigma, 1e-30))


# --------------------------------------------------------------------------- #
#  검증용 표준 표적 (구 / 평판)
# --------------------------------------------------------------------------- #
def _sphere_mesh(r, seg=60, rings=30):
    from geom import uv_sphere
    return uv_sphere(r, seg=seg, rings=rings)


def _plate_mesh(a):
    """xy 평면(법선 +z) 한 변 a 정사각 평판."""
    from geom import Mesh
    m = Mesh("plate"); h = a/2
    i = [m.add_vertex(*p) for p in [(-h,-h,0),(h,-h,0),(h,h,0),(-h,h,0)]]
    m.add_quad(*i)
    return m


def validate(fc=3.5e9):
    lam = C0/fc
    print(f"== PO 검증 @ {fc/1e9:.1f} GHz (λ={lam*100:.1f} cm) ==")
    # 평판: 수직입사 4πA²/λ² — 점근이 아니라 **PO 의 정확한 답**이다 (법선 +z → 시선 el=90°)
    a = 0.30; A = a*a
    mp = _plate_mesh(a); P,N,dA = mesh_to_points(mp, lam/10)
    s = rcs_from_points(P,N,dA, fc, az_deg=[0.0], el_deg=90.0)[0]
    th = 4*np.pi*A**2/lam**2
    print(f"  평판 {a}m: PO={dbsm(s):6.2f} dBsm  정확PO={dbsm(th):6.2f} dBsm  Δ={dbsm(s)-dbsm(th):+.2f}")
    #  구: 기준해가 **둘**이다 — 이 커널은 PO 이므로 과녁은 해석적 PO 이고, 정확 Mie 와의
    #  잔차는 PO 근사를 쓴 대가다. πr² 은 ka→∞ 점근값이라 **과녁이 아니다**(라벨만 남긴다).
    import os
    import sys
    _bench = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "benchmark"))
    if _bench not in sys.path:
        sys.path.insert(0, _bench)
    from mie_pec_sphere import sphere_reference_set
    for r in (0.30, 0.50):
        ms = _sphere_mesh(r, seg=90, rings=46); P,N,dA = mesh_to_points(ms, lam/8)
        s = rcs_from_points(P,N,dA, fc, az_deg=[0.0], el_deg=0.0)[0]
        ref = sphere_reference_set(r, fc)
        print(f"  구 r={r}m ({r/lam:.1f}λ, kr={ref['kr']:.2f}): PO={dbsm(s):6.2f} dBsm  "
              f"해석PO={ref['po_dbsm']:6.2f} Δ={dbsm(s)-ref['po_dbsm']:+.2f}  "
              f"정확Mie={ref['mie_dbsm']:6.2f} Δ={dbsm(s)-ref['mie_dbsm']:+.2f}  "
              f"(점근 πr²={ref['go_dbsm']:6.2f}, 과녁 아님)")


if __name__ == "__main__":
    validate(3.5e9)
    print()
    from drones import DRONES
    fc = 3.5e9
    az = np.arange(0, 360, 2.0)
    print(f"== 드론별 RCS @ {fc/1e9:.1f} GHz (방위 평균 dBsm: 재질 가중 vs 전부 PEC) ==")
    for k in DRONES:
        sw, npts = drone_rcs_pattern(k, fc, az, materials=True)
        sp, _ = drone_rcs_pattern(k, fc, az, materials=False)
        print(f"  {k:10s} 점{npts:6d}  재질가중 평균={dbsm(sw.mean()):6.2f} 최대={dbsm(sw.max()):6.2f}"
              f"   PEC 평균={dbsm(sp.mean()):6.2f}  (Δ평균={dbsm(sw.mean())-dbsm(sp.mean()):+.1f} dB)")
