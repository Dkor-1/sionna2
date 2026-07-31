# -*- coding: utf-8 -*-
"""
freespace_scene.py — (report13) 자유공간 패시브 바이스태틱 **기하**(순수함수)
==============================================================================

report01~12 는 전부 무향실(30×20×11 m) 안이었다. report13 만 챔버를 벗어나
**자유공간(FS-1)** 에서 "이 드론이 몇 m 까지 보이나"를 묻는다. 이 파일은 그 질문의
**기하 계층**만 담당한다 — 링크버짓(`freespace_link`)·검출기(`freespace_detect`)는
별도 모듈이고, 여기에는 **I/O 도 전역상태도 없다**(전부 순수함수).

배치(전부 **선언값** — 근거문서 없음, REPORT13_SPEC §2/R4):

    FS_TX = (0, 0, 25)      조명원 마스트 25 m
    FS_RX = (L, 0, 3)       패시브 수신기 3 m
    O = (TX+RX)/2 ;  P(d,φ) = O + d·(cosφ, sinφ, 0) + (0, 0, alt−O_z)
    u1 = (TX−P)/R1,  u2 = (RX−P)/R2,  Rb = R1+R2−L,  τ = Rb/c
    f_d = v·(u1+u2)/λ,   β = ∠(u1,u2),   κ = R1R2,   R_eq = √κ

높이는 자유공간에서 '지면 기준'이 아니라 **배치 파라미터**다(R4): FS-1 에서는
el·β 를 정하는 역할만 하고, 지면반사(F⁴)는 FS-3 동반사다리에서만 산다.

부호 규약 — `bistatic_scene.bistatic_params`(src/bistatic_scene.py:37-50) **복제**
    챔버 상수(CHAMBER/TX/RX/TGT)를 import 하지 말라는 스펙 §3 지시에 따라 이 모듈은
    `bistatic_scene` 을 **import 하지 않고** 식을 그대로 옮겼다. 옮긴 식이 원본과
    비트 단위로 같은지는 스모크(무작위 기하 2000 케이스, 최대편차 0.0)로 확인했다.
    핵심: u1·u2 는 **표적→TX / 표적→RX** 이고, 그래서 **멀어지면 f_d < 0** 이다.

⚠ F1 (헤드라인 전복) — SSB 반복률은 2000 Hz 가 아니라 **50 Hz**
    report12 의 `CPI_CFG`(nr: M=112)는 SSB 를 0.5 ms 로 타일링한 **단순화**였다.
    저장소 자체의 단일 진리원 `waveforms.PILOT_RATE_HZ["nr"]["PSS"] = 50.0`
    ("SSB 20ms 버스트 → 50Hz")이 물리값이다. 그래서 여기서는 M 을 자유파라미터로
    두지 않고 **물리 반복률에서 유도**한다: `M = max(2, round(T_CPI·PRF))`.
    T_CPI=100 ms 면 LTE CRS M=100, WiFi M=100(@1 kHz), **NR SSB M=5**, NR PRS M=20.
    `prf_hz()` 는 값을 하드코딩하지 않고 `PILOT_RATE_HZ` 를 직접 읽는다.

⚠ F8 — 도플러 가드 판정은 **접힌(folded) 도플러**로
    반복률 PRF 로 샘플하는 slow-time 축은 [−PRF/2, +PRF/2) 밖의 도플러를 **접는다**.
    실제 검출기는 접힌 위치의 셀만 보므로, 0-도플러 가드(±2.5/T_CPI)에 걸리는지는
    반드시 `folded_doppler()` 로 판정해야 한다. 결과가 서사를 확정한다:
    T_CPI=100 ms·SSB(PRF 50 Hz)면 가드 반폭 25 Hz = PRF/2 라 **도플러 축 전체가
    가드**(M=5 → 축이 ±2.5 빈뿐) → 유휴 5G 는 거리 이전에 도플러로 죽는다.
    (스펙 §10 스키마의 예시값 `blind_heading_frac{G1}=0.143` 은 **접지 않은** 규약의
     잔재다. 접은 규약에서는 1.0 이 나온다 — 스펙 §7.2/§15-14 의 "전헤딩 접힘"과 일치.)

★ 이 모듈이 재현해야 하는 검증표 (L=500, φ=90°, TX z=25, RX z=3 — 설계문서 §1.2)

    | alt  | d=150            | 300        | 1000       | 3000      | 10000       |
    | 60 m | β115.8° el−17.0° | 79.0/−8.7  | 28.1/−2.6  | 9.5/−0.9  | 2.9/−0.26   |
    | 120 m| β107.4° el−35.2° | 76.4/−19.5 | 27.9/−6.1  | 9.5/−2.0  | 2.9/−0.61   |

    → (a) 이등분선 앙각은 전 구간 **음수**(σ 격자를 음의 el 로 떠야 하는 이유),
      (b) 근거리·큰 L 은 β>90° 로 SBR 유효범위 밖(해칭 대상).

거리 용어를 절대 섞지 않는다: `d`(중점–표적 수평거리, 헤드라인 축) / `R2`(표적–수신기)
/ `R_b=R1+R2−L`(RD 맵 가로축, 실제 관측량) / `κ=R1R2` / `R_eq=√κ`(Cassini 상수,
분산·밴드를 인용하는 축 — d 축에서는 R∝σ^¼ 가 성립하지 않는다, S1).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

# 반복률의 단일 진리원(F1). waveforms 는 numpy/dataclass 만 쓰는 가벼운 모듈이다.
from waveforms import PILOT_RATE_HZ

C0 = 299792458.0

# --------------------------------------------------------------------------- #
#  배치 상수 — 전부 **선언값**(근거문서 없음). 결과는 "선언한 예산 아래의 거리"다.
# --------------------------------------------------------------------------- #
FS_TX = (0.0, 0.0, 25.0)          # 조명원(illuminator) 마스트 — 원점
FS_RX_H = 3.0                     # 패시브 수신기 높이 [m]
FS_ALT = (60.0, 120.0)            # 표적 고도 [m]
FS_SPEED = (5.0, 15.0)            # 표적 속도 [m/s]
BASELINES = (100.0, 500.0, 2000.0)
L_REF = 500.0                     # 헤드라인 베이스라인
PHI_HEADLINE_DEG = 90.0           # 헤드라인 장면방위(전 캡션에 명시, S7)
T_CPI_REF_S = 0.1                 # 헤드라인 CPI

BETA_VALID_MAX_DEG = 90.0         # SBR 유효범위(β→180° 에서 σ≡0, rcs_sbr.py:252-255)
GUARD_DOPPLER_BINS = 2.5          # 0-도플러 가드 반폭 [빈] — **스펙 §7.2 선언값**
FRESNEL_MIN_RATIO = 0.6           # FS-3 프레넬 게이트(1존의 60% 이상 비어야 함)

# ⚠ 감사 지적(B1) 반영 — **선언 가드(2.5빈)와 검출기가 실제로 지우는 가드(1.5빈)는 다르다.**
#   `freespace_detect.DOPPLER_GUARD_WIDTH = 3` 은 zd±1 행(=3행)을 물리적으로 제거한다.
#   3행 = 중심빈 ±1빈 = **반폭 1.5빈**이다. 즉
#     · hard blind  : |f_d_folded| < 1.5·Δf_d   ← 검출기가 정말로 못 보는 구간(측정 가능)
#     · soft blind  : 1.5·Δf_d ≤ |f_d_folded| < 2.5·Δf_d  ← 가드 밖이지만 능선 어깨(Hann ±2빈
#                     −42.5 dB)와 CFAR 훈련오염이 남는 구간. 스펙 §5.2 `soft_blind_frac`.
#   스펙 §10 의 ★f_guard_hz = 2.5/T 는 **선언값**이라 기본값은 2.5 로 유지하되,
#   `blind_fractions()` 가 두 규약을 **동시에** 내놓는다. 어느 쪽을 인용했는지 JSON 에 박을 것.
#   ⚠ 스펙 §5.2 의 dopoff 격자 최소값이 3빈이라 **1.5~3빈 구간에는 측정 전이곡선이 없다**
#     (=soft blind 는 보간·외삽으로만 다룰 수 있다). 이 구멍은 아직 못 메운다.
DOPPLER_GUARD_HARD_BINS = 1.5     # = freespace_detect.DOPPLER_GUARD_WIDTH / 2

# ★F17 — 크기 오름차순 정본은 `radar_scene.target_extent`(bbox 최대 수평치수):
#   mini5pro 0.378 < phantom4 0.471 < mavic4pro 0.556 < matrice4e 0.587 < s1000plus 1.348
#   (`anim_plots.drone_size_compare` 는 mavic·phantom 이 뒤바뀌어 있다 — 쓰지 않는다.)
# ⭐ 2026-07-30 (Phase 3): 5종 하드코딩이라 신규 기종이 이 순서 목록을 통과하지 못하고
#   **에러 없이 자유공간 스윕 전체에서 빠졌다.** 앞머리는 위 실측 순서를 유지하고, 레지스트리의
#   나머지 기종은 등록 순서로 뒤에 붙인다(신규 기종의 target_extent 는 아직 재지 않았다).
#   ⚠ 개수를 세야 하면 `len(DRONE_ORDER)`. 상수 5 를 쓰지 말 것.
from drones import drone_order as _drone_order            # noqa: E402
DRONE_ORDER = tuple(_drone_order(("mini5pro", "phantom4", "mavic4pro",
                                  "matrice4e", "s1000plus")))


def FS_RX(L):
    """베이스라인 L[m] → 수신기 위치 (L, 0, 3).  (스펙 §9 의 `FS_RX=lambda L:(L,0.,3.)`)"""
    return (float(L), 0.0, FS_RX_H)


# --------------------------------------------------------------------------- #
#  ① 기하 — 부호는 bistatic_params 복제
# --------------------------------------------------------------------------- #
def fs_params(tx, rx, tgt, vel, fc) -> dict:
    """TX/RX/표적 위치[m]·표적속도[m/s]·반송파[Hz] → 바이스태틱 파라미터 dict.

    `bistatic_scene.bistatic_params` 와 **수식·부호가 완전히 동일**하다(챔버 상수만
    안 쓴다). 반환키: L,R1,R2,Rb,tau,fd,beta,lam,u1,u2 + report13 전용 파생
    kappa(=R1R2), R_eq(=√κ, 분산 인용축), el_deg(이등분선 앙각).

      u1 = (TX−P)/R1, u2 = (RX−P)/R2   (표적→TX, 표적→RX)
      Rb = R1+R2−L                      직접파 대비 추가경로 → τ = Rb/c
      f_d = v·(u1+u2)/λ                 **멀어지면 f_d < 0**
      β  = ∠(u1,u2)                     β>90° 는 SBR 유효범위 밖

    **배열을 받는다**(감사 C4/⑫ 반영): `tgt`/`vel` 에 (...,3) 을 주면 R1·R2·Rb·τ·f_d·β·κ·R_eq·
    el_deg 는 (...) 모양으로, u1·u2 는 (...,3) 으로 나온다. 스칼라 입력이면 예전처럼 float 이다.
    (예전 구현은 `np.linalg.norm(d1)` 에 axis 가 없어 (N,3) 을 프로베니우스 노름으로 뭉갠 뒤
     `vel @ (u1+u2)` 에서 죽었다 — 240×360×72 격자를 파이썬 루프 없이 돌리려면 이게 필요하다.)
    """
    tx, rx, tgt, vel = (np.asarray(v, float) for v in (tx, rx, tgt, vel))
    lam = C0 / float(fc)
    L = float(np.linalg.norm(np.ravel(tx)[:3] - np.ravel(rx)[:3]))
    d1 = tx - tgt                                           # (...,3)
    d2 = rx - tgt
    R1 = np.linalg.norm(d1, axis=-1)
    R2 = np.linalg.norm(d2, axis=-1)
    u1 = d1 / np.maximum(R1, 1e-9)[..., None]               # 표적→TX
    u2 = d2 / np.maximum(R2, 1e-9)[..., None]               # 표적→RX
    Rb = R1 + R2 - L                                        # 바이스태틱(추가) 거리
    tau = Rb / C0
    fd = np.sum(vel * (u1 + u2), axis=-1) / lam             # 멀어지면 <0
    beta = np.degrees(np.arccos(np.clip(np.sum(u1 * u2, axis=-1), -1.0, 1.0)))
    kap = R1 * R2

    def _s(x):
        a = np.asarray(x, float)
        return float(a) if a.ndim == 0 else a

    return dict(L=L, R1=_s(R1), R2=_s(R2), Rb=_s(Rb), tau=_s(tau), fd=_s(fd),
                beta=_s(beta), lam=lam, u1=u1, u2=u2,
                kappa=_s(kap), R_eq=_s(np.sqrt(kap)),
                el_deg=look_el_deg(u1, u2))


def target_pos(d, phi_deg, L, alt) -> np.ndarray:
    """중점기준 (수평거리 d[m], 장면방위 φ[deg], 베이스라인 L[m], 고도 alt[m]) → 표적 위치 (3,).

    O=(TX+RX)/2 이므로 x=L/2+d·cosφ, y=d·sinφ, z=alt (O_z 는 고도로 덮어쓴다 —
    설계식 `O + d(cosφ,sinφ,0) + (0,0,alt−O_z)` 과 동일).
    d/φ/alt 에 배열을 주면 (...,3) 으로 브로드캐스트한다(격자 역해용).
    """
    d = np.asarray(d, float)
    ph = np.radians(np.asarray(phi_deg, float))
    x = 0.5 * float(L) + d * np.cos(ph)
    y = d * np.sin(ph)
    z = np.broadcast_to(np.asarray(alt, float), np.broadcast(x, y).shape) \
        if np.ndim(alt) == 0 else np.asarray(alt, float)
    x, y, z = np.broadcast_arrays(x, y, z)
    return np.stack([x, y, z], axis=-1)


def heading_velocity(psi_deg, speed) -> np.ndarray:
    """헤딩 ψ[deg](= 드론 yaw = 속도방향)·속력[m/s] → 속도벡터 (3,) 또는 (...,3).

    수평비행만 모형화한다(roll=pitch=0, §15-15 "실전진 pitch 10~30° 는 모른다").
    ψ 는 σ(자세)와 도플러를 **동시에** 구동하는 1급 변수다 — σ 조회 방위는 az_look−ψ.
    """
    ps = np.radians(np.asarray(psi_deg, float))
    sp = np.asarray(speed, float)
    vx, vy, vz = np.broadcast_arrays(sp * np.cos(ps), sp * np.sin(ps),
                                     np.zeros_like(sp * ps))
    return np.stack([vx, vy, vz], axis=-1)


def look_el_deg(u1, u2) -> float:
    """이등반선(bisector) 앙각 el[deg]. 지상 TX/RX + 공중 표적이면 **항상 음수**.

    `benchmark/channel.look_angles`(σ 조회의 단일 진리원)와 **같은 식**을 쓴다:
    û_look=(u1+u2)/|u1+u2| 의 z 성분 arcsin. 표적이 아래를 내려다보는 게 아니라
    표적에서 '등가 모노스태틱 레이더'를 내려다보는 방향 → 우리는 드론의 **배(belly)**
    를 본다("overhead spike" 서사는 부호가 반대였다, 스펙 §6.1).
    """
    b = np.asarray(u1, float) + np.asarray(u2, float)
    n = np.linalg.norm(b, axis=-1, keepdims=True)
    look = np.where(n > 1e-9, b / np.maximum(n, 1e-12), np.asarray(u1, float))
    el = np.degrees(np.arcsin(np.clip(look[..., 2], -1.0, 1.0)))
    return float(el) if np.ndim(el) == 0 else el


# --------------------------------------------------------------------------- #
#  ② 시간축 — 반복률·M·가드·접힘  (F1/F8)
# --------------------------------------------------------------------------- #
def doppler_bin_hz(T_cpi, prf=None, M=None) -> float:
    """도플러 **빈폭** Δf_d [Hz].

    · `prf`·`M` 둘 다 주면 **실현값** `PRF/M` (정확). 이게 검출기가 실제로 갖는 빈폭이다.
    · 없으면 명목 `1/T_CPI` — `M = T_CPI·PRF` 가 정확히 성립할 때만 둘이 같다.

    ⚠ 감사 B2 — `M_from_prf` 의 `max(2,·)` 클램프가 걸리는 조합(예 LTE PRS 6.25 Hz·T=0.1 s)에서
      명목과 실현이 **3.2배**까지 벌어진다(nom 25 Hz vs real 7.81 Hz). 그런 셀은
      `cpi_feasibility()` 가 `feasible=False` 로 잡아 회색 처리해야 한다.
    """
    if prf is not None and M is not None and float(prf) > 0 and int(M) > 0:
        return float(prf) / float(int(M))
    return 1.0 / float(T_cpi)


def doppler_guard_hz(T_cpi, prf=None, M=None, guard_bins=GUARD_DOPPLER_BINS) -> float:
    """0-도플러 가드 반폭 [Hz] = `guard_bins × Δf_d`.

    기본 `guard_bins=2.5` 는 **스펙 §7.2 선언값**(★f_guard_hz=25 @T=0.1 s 재현). 검출기가
    실제로 지우는 폭은 `DOPPLER_GUARD_HARD_BINS=1.5` 다 — 두 규약 차이는 `blind_fractions()`
    가 `hard`/`declared` 로 분리해 낸다(감사 B1).
    `prf`·`M` 을 주면 빈폭을 **실현값 PRF/M** 으로 잡는다(감사 B2).
    """
    return float(guard_bins) * doppler_bin_hz(T_cpi, prf, M)


def prf_hz(std, mode, wifi_packet_rate=1000.) -> float:
    """(표준, 점유모드) → **기준신호 반복률 PRF [Hz]**. 값은 `waveforms.PILOT_RATE_HZ` 에서 읽는다.

    정합필터가 실제로 잠그는 기준신호(=`Waveform.ref_name` 규칙)의 반복률이다:
      wifi(W1~W3) : VHT-LTF = 패킷당 1회 → `wifi_packet_rate`(F9: 답을 정하는
                    자유파라미터라 1급 감도축 {10,100,1000,5000}, 기본 1000=혼잡 AP)
      lte  G1(L1) : CRS  1000 Hz
      lte  G2/G3  : PRS  6.25 Hz  (PRS 가 켜지면 전대역 기준이 PRS 로 **교체**된다)
      nr   G1     : SSB    50 Hz  ★F1 — 2000 Hz 가 아니다
      nr   G2/G3  : NR-PRS 200 Hz (측위 세션 설정값)

    ⚠ `Waveform.pilot_rate_hz` 는 존재하는 파일럿의 **max** 라 L2/L3 에서 1000(CRS)을
      준다. report13 정본은 '기준으로 쓰는 신호 하나'의 반복률이므로 6.25 를 쓴다
      (스펙 §10 `meta.cpi.reference_repetition_hz`). 충돌 시 스펙이 이긴다.
    ⚠ 정정(감사 §10) — wifi 분기는 `PILOT_RATE_HZ["wifi"]["LLTF"]` 를 **읽지 않는다.** 패킷률은
      트래픽 의존이라 저장소 상수(1000=혼잡 AP 대표값)가 진리원이 될 수 없고, 스펙 F9 가
      `wifi_packet_rate_hz∈{10,100,1000,5000}` 를 1급 감도축으로 올렸기 때문이다. 그래서
      **인자를 그대로 돌려준다**(기본값만 저장소 값과 같다). lte/nr 만 `PILOT_RATE_HZ` 직독이다.
    """
    std = str(std).lower()
    m = str(mode).upper()
    if m in ("W1", "W2", "W3", "L1", "L2", "L3"):           # 라벨로 줘도 받는다
        m = "G" + m[1]
    if std == "wifi":
        return float(wifi_packet_rate)
    if std == "lte":
        return float(PILOT_RATE_HZ["lte"]["CRS" if m == "G1" else "PRS"])
    if std == "nr":
        return float(PILOT_RATE_HZ["nr"]["PSS" if m == "G1" else "PRS"])
    raise ValueError(f"알 수 없는 표준: {std}")


def M_from_prf(T_cpi, prf) -> int:
    """slow-time 펄스수 M = max(2, round(T_CPI·PRF)) — **물리 반복률에서 유도**(F1).

    T_CPI=100 ms: LTE CRS 100 / WiFi 100(@1 kHz) / **NR SSB 5** / NR PRS 20.
    (report12 의 nr M=112 는 0.5 ms 타일링 단순화였다 — SSB 기준 ≈−16 dB 과대.)
    T_CPI 는 리포트 간 공정성 규약상 **고정**이고, M 만 표준마다 물리적으로 다르다.

    ⚠ `max(2,·)` 는 **실현 불가능한 값을 만들어낼 수 있다**(감사 B2/⑦): LTE PRS(PRF 6.25 Hz)는
      2 펄스를 모으는 데 320 ms 가 필요한데 T_CPI=0.1 s 면 `M=2` 가 나온다. 그 셀은 물리적으로
      존재하지 않는다 — 반드시 `cpi_feasibility()` 로 걸러 회색 라벨(`cpi_too_short`)을 달 것.
      이 함수 자체는 스펙 §9 시그니처(`-> int`)를 지키느라 int 만 돌려준다.
    """
    return int(max(2, int(np.rint(float(T_cpi) * float(prf)))))


def cpi_feasibility(T_cpi, prf, guard_width=3) -> dict:
    """(감사 B2/⑦) `M_from_prf` 가 실현 가능한 CPI 인지 판정한다. **스펙 §9 밖 보조함수.**

    반환 dict:
      M                   : `M_from_prf` 결과(클램프 포함)
      M_exact             : T_CPI·PRF (클램프 전 실수값)
      T_eff_s             : 실제로 걸리는 시간 M/PRF — `T_cpi` 와 다르면 링크(10log10 T)와
                            검출기(도플러 빈폭)가 서로 다른 시간을 쓰게 된다
      feasible            : `T_cpi·PRF ≥ 2` (2펄스가 T_CPI 안에 들어오나)
      doppler_rows_left   : 0-도플러 가드행(`guard_width`)을 뺀 뒤 남는 도플러행 수
      doppler_axis_ok     : 남는 행이 1개 이상인가 (0이면 CFAR 부분맵이 비어 **검출 자체가 불가**)
      reason              : 실패 사유 문자열 또는 None → 스펙 §8.6 게이트 라벨로 그대로 쓸 것

    ★실측: T=0.1 s 에서 L2/L3(PRF 6.25)는 `feasible=False`, G1(PRF 50, M=5)은 feasible 이지만
      `doppler_rows_left=2` 뿐이다(9모드 중 2개가 정본 T_CPI 에서 미정의/퇴화)."""
    T = float(T_cpi)
    p = float(prf)
    m_exact = T * p
    M = M_from_prf(T, p)
    h = int(guard_width) // 2
    zd = M // 2
    lo, hi = max(0, zd - h), min(M, zd + h + 1)
    rows = M - (hi - lo)
    feasible = bool(m_exact >= 2.0)
    reason = None
    if not feasible:
        reason = "cpi_too_short"                 # T_CPI 안에 2 펄스가 안 들어온다
    elif rows <= 0:
        reason = "doppler_axis_degenerate"       # 가드 빼면 남는 행이 없다
    return dict(M=int(M), M_exact=float(m_exact), T_eff_s=float(M / p) if p > 0 else float("inf"),
                feasible=feasible, doppler_rows_left=int(rows),
                doppler_axis_ok=bool(rows > 0), guard_width=int(guard_width),
                doppler_bin_hz=doppler_bin_hz(T, p, M), reason=reason)


def folded_doppler(fd, prf):
    """도플러를 [−PRF/2, +PRF/2) 로 **접는다**: mod(f_d+PRF/2, PRF)−PRF/2  (F8).

    slow-time 샘플링률이 PRF 라 검출기는 접힌 위치의 셀만 본다. 0-도플러 가드 판정은
    반드시 이 값으로 해야 한다(접기 전 값으로 하면 SSB 가 부당하게 살아난다).
    PRF≤0 **또는 PRF=inf**(=반복률 미정/연속조명) 이면 접지 않고 그대로 돌려준다
    — `nyquist_gate` 도 같은 입력에 "앨리어싱 없음(True)"을 준다(감사 ⑩: 두 함수가 퇴화입력에서
    정반대 결론을 내던 것을 통일했다).
    """
    fd = np.asarray(fd, float)
    prf = float(prf)
    if not np.isfinite(prf) or prf <= 0:
        return float(fd) if np.ndim(fd) == 0 else fd
    out = np.mod(fd + prf / 2.0, prf) - prf / 2.0
    return float(out) if np.ndim(out) == 0 else out


def _fd_of_heading(psi_grid, phi, d, L, alt, speed, lam):
    """(내부) 헤딩격자 ψ 각각의 도플러 f_d[Hz] 와 그 지점의 기하 dict."""
    tgt = target_pos(d, phi, L, alt)
    p = fs_params(FS_TX, FS_RX(L), tgt, (0.0, 0.0, 0.0), C0 / float(lam))
    V = heading_velocity(np.asarray(psi_grid, float), float(speed))     # (N,3)
    fd = (V @ (p["u1"] + p["u2"])) / float(lam)                         # (N,)
    return fd, p


def blind_sector(psi_grid, phi, d, L, alt, T, prf, speed, lam,
                 guard_bins=GUARD_DOPPLER_BINS, M=None) -> np.ndarray:
    """헤딩격자 ψ[deg] 각각에 대해 **도플러 블라인드인가**(True) 를 판정한다.

    blind ⇔ `|folded_doppler(f_d(ψ), PRF)| < guard_bins·Δf_d`.
    f_d(ψ)=v(ψ)·(u1+u2)/λ 는 ψ 의 코사인이라 블라인드는 두 개의 대칭 섹터가 된다
    (호버·저속·기하 수직교차가 여기 걸린다 — **거리와 무관한** 미검출이다).

    · `guard_bins` 기본 2.5 = **스펙 §7.2 선언값**. 검출기가 실제로 지우는 폭은 1.5빈이다
      (`DOPPLER_GUARD_HARD_BINS`) — 두 규약을 함께 보려면 `blind_fractions()` 를 써라(감사 B1).
    · `M` 을 주면 빈폭을 실현값 `PRF/M` 으로 잡는다(감사 B2). 안 주면 명목 `1/T`.

    ⚠ 접기(F8) 때문에 SSB 처럼 PRF 가 작은 모드는 전 헤딩이 블라인드가 될 수 있다.
      T=100 ms·PRF=50 Hz 면 가드 반폭 25 Hz = PRF/2 → 도플러 축(±2.5빈)이 통째로 가드다.
    """
    fd, _ = _fd_of_heading(psi_grid, phi, d, L, alt, speed, lam)
    return np.abs(folded_doppler(fd, prf)) < doppler_guard_hz(T, prf, M, guard_bins)


def blind_fractions(psi_grid, phi, d, L, alt, T, prf, speed, lam, M=None,
                    hard_bins=DOPPLER_GUARD_HARD_BINS,
                    declared_bins=GUARD_DOPPLER_BINS) -> dict:
    """(감사 B1 — 스펙 §9 밖 보조) 블라인드 비율을 **두 가드 규약 + 앨리어싱**으로 한 번에.

    왜 필요한가: scene 은 2.5빈(선언), 검출기(`freespace_detect.DOPPLER_GUARD_WIDTH=3`)는
    1.5빈을 지운다. 한 숫자만 인용하면 헤드라인 4번("헤딩의 {blind}%가 도플러 블라인드")이
    ★1.7배까지 편향된다(실측 L1: 0.272 vs 0.161). 그래서 둘 다 낸다.

    반환 dict:
      blind_hard      : |f_d_folded| < 1.5·Δf_d — **검출기가 실제로 못 보는** 헤딩 비율(정본 인용)
      blind_declared  : |f_d_folded| < 2.5·Δf_d — 스펙 §7.2 선언 규약(리포트 간 비교용)
      soft_blind_frac : 그 사이 구간(1.5~2.5빈) — 스펙 §5.2 `soft_blind_frac`
      alias_frac      : |f_d| ≥ PRF/2 (F8 나이퀴스트 상한 위반)
      bin_hz          : 쓰인 빈폭 Δf_d, `f_guard_hard_hz`/`f_guard_declared_hz`
      fd_hz, fd_folded_hz : 진단용 배열
    ⚠ soft 구간은 `transfer_by_dopoff` 의 dopoff 격자 최소값(3빈)보다 안쪽이라 **측정 전이곡선이
      없다** — 커버리지 적분에서 이 구간은 외삽이며, 그 사실을 캡션·JSON 에 적어야 한다."""
    fd, _ = _fd_of_heading(psi_grid, phi, d, L, alt, speed, lam)
    fb = folded_doppler(fd, prf)
    bw = doppler_bin_hz(T, prf, M)
    g_hard = float(hard_bins) * bw
    g_decl = float(declared_bins) * bw
    hard = np.abs(fb) < g_hard
    decl = np.abs(fb) < g_decl
    return dict(blind_hard=float(np.mean(hard)), blind_declared=float(np.mean(decl)),
                soft_blind_frac=float(np.mean(decl & ~hard)),
                alias_frac=float(np.mean(~nyquist_gate(fd, prf))),
                bin_hz=float(bw), f_guard_hard_hz=g_hard, f_guard_declared_hz=g_decl,
                guard_bins_hard=float(hard_bins), guard_bins_declared=float(declared_bins),
                prf_hz=float(prf), M=(int(M) if M else None),
                fd_hz=fd, fd_folded_hz=fb,
                canonical="blind_hard (detector actually removes zd+-1 = 1.5 bins)")


# --------------------------------------------------------------------------- #
#  ③ 유효범위 게이트 (스펙 §8.6 — 축을 자르지 않고 라벨만 단다)
# --------------------------------------------------------------------------- #
def beta_gate(beta_deg) -> bool:
    """바이스태틱각 게이트: β ≤ 90° 에서만 σ 를 인용한다.

    근거: `rcs_sbr.py:252-255` — β→180°(전방산란)에서 σ≡0 이라 SBR+PO 가 Babinet
    로브를 못 낸다. ★L=500·d=150·alt=60 은 β=115.8° 로 여기 걸린다(해칭·수치금지).
    """
    b = np.asarray(beta_deg, float) <= BETA_VALID_MAX_DEG
    return bool(b) if np.ndim(b) == 0 else b


@lru_cache(maxsize=None)
def _extent_m(drone: str) -> float:
    """드론 최대 수평치수 D[m] — `radar_scene.target_extent` 그대로(메쉬 bbox). 캐시."""
    from radar_scene import target_extent                  # 지연 import(가벼운 경로 유지)
    return float(target_extent(drone))


def farfield_gate(d, drone, fc) -> bool:
    """원거리장 게이트: d ≥ 2D²/λ  (`radar_scene.farfield_distance(target_extent)`).

    ★최악은 s1000plus@5.21 GHz 의 63.1 m, 최선은 mini5pro@LTE 의 1.75 m.
    D 정의는 bbox 최대 수평치수(대각 아님) — 스펙 §10 `meta.farfield.D_definition`.
    ⚠ 엄밀하게는 **min(R1,R2) ≥ 2D²/λ** 여야 한다(φ≈180° 처럼 표적이 TX 바로 위면
      d 는 커도 R1 이 고도만큼밖에 안 된다). 스펙 §8.6 표기가 d 라 인자는 d 로 두되,
      호출부에서 min(R1,R2) 를 넣으면 그대로 엄밀판정이 된다.
    """
    from radar_scene import farfield_distance
    dmin = farfield_distance(_extent_m(drone), float(fc))
    g = np.asarray(d, float) >= dmin
    return bool(g) if np.ndim(g) == 0 else g


def nyquist_gate(fd, prf) -> bool:
    """나이퀴스트 게이트(F8): |f_d| < PRF/2 여야 도플러가 접히지 않는다.

    False = 앨리어싱(alias_heading_frac). SSB(PRF 50 Hz)는 v=5 m/s·3.5 GHz 에서
    |f_d| 가 최대 ~113 Hz 라 사실상 전 헤딩이 접힌다 — '유휴 5G 이중고'의 시간축 절반.

    퇴화 입력 규약(감사 ⑩ 정정): `PRF=inf`(반복률 미정/연속조명) → **True(앨리어싱 없음)**,
    `PRF≤0`(무의미) → False. 예전에는 둘을 한 덩어리로 묶어 `folded_doppler`(접지 않음)와
    정반대 결론을 냈고, PRF 미정 모드의 `alias_heading_frac` 이 1.0 으로 나갔다.
    """
    prf = float(prf)
    fda = np.asarray(fd, float)
    if np.isinf(prf) and prf > 0:
        g = np.ones_like(fda, dtype=bool)                 # 접힘 없음
    elif not np.isfinite(prf) or prf <= 0:
        g = np.zeros_like(fda, dtype=bool)
    else:
        g = np.abs(fda) < prf / 2.0
    return bool(g) if np.ndim(g) == 0 else g


def angular_sep_tx_target_deg(rx, tx, P) -> float:
    """수신기에서 본 **TX ↔ 표적 각분리** Δθ[deg] (R7 — DPI 억압의 기하 게이트).

    빔/널 조향으로 직접파를 억압하려면 표적이 TX 와 각으로 떨어져 있어야 한다.
    Δθ < 빔폭/2 면 표적도 같이 눌리므로 supp_eff=0 (`limit="dpi_unsuppressible"`).
    ★L=500·alt=60·d=1000·φ=180°(표적이 TX 너머 일직선)에서 Δθ=0.09° — 억압 불가.
    """
    rx = np.asarray(rx, float)
    a = np.asarray(tx, float) - rx
    b = np.asarray(P, float) - rx
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    c = float(np.dot(a, b)) / max(na * nb, 1e-12)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def fresnel_clearance_ratio(rx_h, R2, lam) -> float:
    """**FS-3 전용** 프레넬 여유비 = rx_h / F₁ ,  F₁ = ½·√(λ·R2)  (경로 중점의 1존 반경).

    FS-1(순수 자유공간)에는 지면이 없으므로 이 게이트는 **적용되지 않는다**(R3).
    지면을 넣는 FS-3 에서만 "3 m 수신기의 1존이 비어 있는가"를 묻고, 통상 기준인
    0.6(=`FRESNEL_MIN_RATIO`) 미만이면 자유공간식이 성립하지 않는다고 라벨한다.
    → FS-3 그림의 x축 상한을 실질적으로 이 값이 정한다.

    ⚠ 선언적 단순화: 낮은 쪽 안테나 높이를 여유(clearance)로, 경로 중점(=1존 반경
      최대)을 임계점으로 잡은 **보수적** 근사다. 표적 고도까지 쓰는 엄밀식
      (2√(h·s/λ), s=(h_t−h_rx)/R2)은 이 인자만으로는 계산할 수 없다 — 인자를
      늘리지 않는다는 스펙 §9 시그니처를 따르고 근사임을 여기 적는다.
    """
    f1 = 0.5 * np.sqrt(float(lam) * np.asarray(R2, float))
    r = np.asarray(rx_h, float) / np.maximum(f1, 1e-12)
    return float(r) if np.ndim(r) == 0 else r


# --------------------------------------------------------------------------- #
#  ④ 회귀 잠금 — "복제한 식이 원본과 같다" 를 저장소 안에 박아둔다 (감사 [9])
# --------------------------------------------------------------------------- #
def selfcheck_vs_repo(n=2000, seed=13, tol=1e-9) -> dict:
    """`fs_params` ↔ `bistatic_scene.bistatic_params`, `look_el_deg` ↔ `channel.look_angles` 동치검정.

    스펙 §3 이 금지한 것은 **챔버 상수**(`CHAMBER/TX/RX`) import 이지 순수함수가 아니다. 그래서
    이 함수만 원본을 지연 import 해 무작위 기하 n 케이스로 비교한다. 동치성이 `/tmp` 스모크에만
    있으면 다음 사람이 식을 고칠 때 아무도 못 잡는다 — `benchmark/verify_freespace.py` 가
    이 함수를 불러 `verify.geometry_equivalence` 에 실어야 한다(감사 [9] 조치).

    반환 dict: max_abs_diff(키별), n, ok."""
    from bistatic_scene import bistatic_params            # 순수함수만(상수 import 아님)
    from channel import look_angles

    rng = np.random.default_rng(int(seed))
    keys = ("R1", "R2", "Rb", "tau", "fd", "beta", "lam")
    worst = {k: 0.0 for k in keys}
    worst_el = 0.0
    for _ in range(int(n)):
        tx = rng.uniform(-50, 50, 3) + np.array([0, 0, 25.0])
        rx = rng.uniform(-50, 50, 3) + np.array([500.0, 0, 3.0])
        tgt = rng.uniform(-3000, 3000, 3) + np.array([0, 0, 100.0])
        vel = rng.uniform(-20, 20, 3)
        fc = float(rng.choice([1.843e9, 3.5e9, 5.21e9]))
        a = fs_params(tx, rx, tgt, vel, fc)
        b = bistatic_params(tx, rx, tgt, vel, fc)
        for k in keys:
            worst[k] = max(worst[k], abs(float(a[k]) - float(b[k])))
        _az, el_ref = look_angles(a["u1"], a["u2"], az_span_deg=0.0, n_az=1)
        worst_el = max(worst_el, abs(float(a["el_deg"]) - float(el_ref)))
    ok = bool(max(worst.values()) <= tol and worst_el <= 1e-9)
    return dict(n=int(n), max_abs_diff=worst, max_abs_diff_el_deg=float(worst_el),
                ok=ok, tol=float(tol),
                note="fs_params is a verbatim copy of bistatic_params (chamber constants excluded); "
                     "look_el_deg is the el branch of channel.look_angles")
