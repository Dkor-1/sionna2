# -*- coding: utf-8 -*-
"""
px4_bridge.py — **기동 브리지**: PX4 비행 로그(선배 grade CSV) 하나로 세 엔진을 같은 궤적에서
================================================================================================

    (a) 우리 커널  src/rcs_sbr.py:sbr_field   — 우리 CAD(FastPoser) / 선배 Phantom4 메쉬 둘 다
    (b) 선배 PO    jihyuck/po_mdoppler        — 이미 돈다. 여기서는 **읽기 전용 참조**만.
    (c) Sionna PathSolver                     — 1 윈도우 한정, per-pulse OBJ 내보내기
                                                 (benchmark/elevation_sweep_md.py sionna 분기 규약)

■ 데이터 함정 — 선배 데이터 정독 기록을 코드에 박는다 (지우지 말 것)
  · ⭐ESC RPM 은 **Phantom 4 것이 아니라 PX4 SITL x500 것**이다(라벨만 Phantom4).
    grade CSV 의 esc[0..3].esc_rpm 에 cfg.rpm_scale(기본 6.0)을 곱해 호버 ~4500 rpm 으로
    올린 것이 선배 규약(po_sim/kinematics.py:62). 우리도 같은 규약을 그대로 탄다 —
    회전수의 절대값을 **기체 고증으로 인용하면 안 된다**.
  · 자세 부호 반전 이력이 있다(선배 파이프라인 정독 기록). 여기서는 clean_attitude.csv 의
    쿼터니언을 kinematics.load_flight 가 읽는 그대로(scipy [x,y,z,w] 재배열) 쓴다 —
    부호를 다시 손대지 않는다. 병합·비교 때 스펙트로그램 상하 반전이 보이면 이 항을 먼저 의심.
  · 350 Hz 인공물: 선배 데이터의 슬로타임 열에 350 Hz 대 인공물이 관측된 이력이 있다.
    브리지는 신호를 안 고친다 — 결과 해석 때 f_flash 정수배가 아닌 350 Hz 근방 선은
    데이터 유래 인공물 후보로 따로 표기하라.
  · ESC 열은 **esc[0..3].esc_rpm 네 열만** 쓴다(po_sim/kinematics.py:24 ESC_COLS).

■ 좌표·위상 규약 (세 엔진을 한 줄에 세우는 핵심)
  · 선배 PO: 월드프레임 조립 + S = Σ Γ·A·cosθ/R² · e^{−j2kR}  (구면파 + 1/R² 확산 포함,
    벌크 거리 위상 포함, 부호 e^{−jkR}).
  · 우리 커널: **몸체프레임** 메쉬 + 조명방향을 몸체프레임으로 돌린다:
        u_body(t) = R_body(t)ᵀ · u_world(t),   R(t) = |radar_pos − pos(t)|
    모노스태틱 RCS 는 상대 자세만의 함수이므로 이것이 월드프레임 회전과 등가다.
    sbr_field 는 (i) 위상원점을 bbox 중심(ctr)에 두고 (ii) 1/r 확산을 넣지 않는다.
    ⭐부호 검산 (conj 를 **안 하는** 이유 — 처음 구현은 conj 였고 틀렸다):
        선배  e^{−j2kR_i} = e^{−j2kR_ctr} · e^{+j2k(R_ctr−R_i)}
        우리(구면파) E ∝ Σ e^{+j2k(R−|p−p_tx|)}  (rcs_sbr:1053, R−R_i 형)
      → 상대 위상의 부호가 **같다**. 벌크만 되붙이면 된다:
        s_ours(t) = E(t) · e^{−j·2k·R(t)}
    ⚠ 1/R² 확산·절대 눈금은 **여기서 넣지 않는다** — rx_noise.py 가 문헌 σ 앵커 +
    레이더 방정식으로 절대 눈금을 잡는 것이 우리 규약이다(15 m 구면파 조명 규약 참조).
  · Sionna PathSolver: 실제 기하(τ)로 e^{−j2πfcτ} 합 — 부호·벌크 위상이 선배와 같아
    conj 불필요. OBJ 는 몸체프레임으로 쓰고 place(az,el,rng) 를 u_body 에서 만든다.

■ 대규모 생산 실행 금지
  우리 커널의 생산 투입은 PTD 수리 게이트 뒤다. 이 모듈은 브리지 구현 + 소규모 시험
  (펄스 수십~수백)용이고, run_* 는 n_pulses 를 그대로 받으므로 **호출자가 지킨다**.
  run_sionna_window 는 max_pulses 기본 256 으로 스스로 막는다(생산 5000 은 명시 해제 필요).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PO_ROOT = os.path.join(ROOT, "jihyuck", "po_mdoppler")
for _p in (os.path.join(ROOT, "src"), HERE, PO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 선배 파이프라인 — **참조만**(읽기). po_sim 은 패키지라 상대 import 가 산다.
from po_sim.kinematics import (load_flight, radar_position, window_poses)   # noqa: E402
from po_sim.mesh import DroneMesh, spin_matrix                              # noqa: E402
from configs.default import (SimConfig, BLADE_OFFSETS, BLADE_DIRS,          # noqa: E402
                             MESH_DIR, DATA_BASE, BODY_MAT, BLADE_MATS)

C0 = 2.998e8


# --------------------------------------------------------------------------- #
#  0. 재질 매핑 — 선배 (εr, σ) → 우리 materials.MATERIALS
# --------------------------------------------------------------------------- #
#  두 가지 모드를 다 제공한다:
#   (A) "senior"  선배의 (εr,σ) 를 **그대로** 우리 표에 런타임 등록(jh_* 키) — 사과 대 사과.
#       벌크 프레넬로 |Γ| 를 유도하므로 선배 fresnel_te_vec 의 수직입사값과 일치한다.
#   (B) "ours"    우리 재질 사전의 **가장 가까운 기존 키**로 매핑 — 우리 헤드라인 규약.
#       수직입사 |Γ| 차이(9.85 GHz):
#         body  metal(εr1,σ1e6)  → "metal"        1.000 ↔ 0.9998   (0.0 dB)
#         blade nylon(εr4,σ0)    → "prop_plastic" 0.333 ↔ 0.25     (−2.5 dB, 실효 박막값)
#         blade cf(εr8,σ12)      → "carbon"       0.713 ↔ 0.90    (+2.0 dB, 우리 실효값)
#         blade metal            → "metal"
#       ⚠ cf 가 가장 벌어진다 — 선배 σ=12 S/m 는 «저도전 CF», 우리 0.90 은 직조 CF 실효.
#       비교 그림에는 어느 모드인지 반드시 적을 것.
SENIOR_MAT_TO_OURS = {"body": "metal", "nylon": "prop_plastic",
                      "cf": "carbon", "metal": "metal"}


def register_senior_materials(fc_note: float = 9.85e9) -> dict:
    """선배 (εr,σ) 재질을 우리 materials.MATERIALS 에 **런타임 등록**(jh_* 키).

    표 파일을 편집하지 않는다 — 이 함수를 부른 프로세스 안에서만 산다.
    반환: {선배키: 우리표키} (blade_mats 3종 + body)."""
    from materials import MATERIALS
    reg = {}
    er, sg = BODY_MAT
    MATERIALS.setdefault("jh_body_metal", dict(
        eps_r=float(er), sigma=float(sg), S=0.0,
        note="브리지 등록 — 선배 po_sim BODY_MAT(metal εr=1, σ=1e6). 벌크 프레넬 |Γ|≈1."))
    reg["body"] = "jh_body_metal"
    for k, (er, sg) in BLADE_MATS.items():
        key = f"jh_blade_{k}"
        MATERIALS.setdefault(key, dict(
            eps_r=float(er), sigma=float(sg), S=0.0,
            note=f"브리지 등록 — 선배 po_sim BLADE_MATS[{k!r}]=(εr={er}, σ={sg}). "
                 "gamma_po 미지정 → 벌크 프레넬로 유도(선배 수직입사와 일치)."))
        reg[k] = key
    return reg


def group_mat_for(poser, mode: str = "ours", blade_mat: str = "nylon") -> dict:
    """포저 → sbr_field 용 group_mat.  mode = "ours" | "senior".

    · OursPoser(우리 CAD): 항상 우리 DRONE_GROUP_MAT (mode 무시 — 우리 기체엔 선배 재질 없음).
    · SeniorMeshPoser: mode="senior" 면 jh_* 등록키(선배 εr,σ 그대로),
                       mode="ours" 면 SENIOR_MAT_TO_OURS 의 근사 매핑."""
    if isinstance(poser, OursPoser):
        from drones import DRONE_GROUP_MAT
        return {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    if mode == "senior":
        reg = register_senior_materials()
        return {"body": reg["body"], "prop": reg[blade_mat]}
    return {"body": SENIOR_MAT_TO_OURS["body"],
            "prop": SENIOR_MAT_TO_OURS[blade_mat]}


# --------------------------------------------------------------------------- #
#  1. 비행 창 로더 — grade CSV → 펄스별 상태
# --------------------------------------------------------------------------- #
@dataclass
class FlightWindow:
    """한 윈도우의 펄스별 상태 (세 엔진이 전부 이것 하나만 읽는다)."""
    t: np.ndarray            # (n,)  절대시각 [s]
    pos: np.ndarray          # (n,3) 기체 위치 [Z-up]
    rot: np.ndarray          # (n,3,3) 몸체 자세 행렬 (body→world)
    blade_ang: np.ndarray    # (n,4) 누적 날개각 [rad, 부호 없음 — dirs 는 따로]
    radar_pos: np.ndarray    # (3,)
    R: np.ndarray            # (n,)  radar↔기체 거리 [m]
    u_world: np.ndarray      # (n,3) 표적→레이더 단위벡터 (월드)
    u_body: np.ndarray       # (n,3) 〃 (몸체프레임) = R_bodyᵀ u_world
    fc: float
    prf: float
    grade: str
    provenance: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.t)

    def az_el_deg(self, i: int) -> tuple[float, float]:
        """u_body[i] → (az, el) [deg] — elevation_sweep_md.los() 와 같은 규약."""
        u = self.u_body[i]
        return (float(np.degrees(np.arctan2(u[1], u[0]))),
                float(np.degrees(np.arcsin(np.clip(u[2], -1, 1)))))


def load_window(grade: int | str = 2, t_start: float | None = None,
                n_pulses: int = 5000, prf: float | None = None,
                fc: float | None = None, data_base: str | None = None,
                cfg: SimConfig | None = None) -> FlightWindow:
    """grade CSV 하나 → FlightWindow.  선배 kinematics 를 **그대로 호출**한다(재구현 금지).

    · t_start=None → cfg.t_skip(기본 5 s).
    · prf/fc=None → 선배 기본(35 kHz / 9.85 GHz). n_pulses 는 인자가 진리.
    · rpm_scale 등 나머지는 cfg 로 덮는다."""
    cfg = cfg or SimConfig()
    if prf is not None:
        cfg.prf = int(prf)
    if fc is not None:
        cfg.f_c = float(fc)
    cfg.n_pulses = int(n_pulses)
    base = data_base or DATA_BASE
    ddir = os.path.join(base, f"grade_{grade}")
    if not os.path.isdir(ddir):
        raise FileNotFoundError(f"grade 폴더가 없다: {ddir}")
    fl = load_flight(ddir, cfg)
    rp = radar_position(fl.flight_center, cfg)
    t0 = float(cfg.t_skip if t_start is None else t_start)
    if t0 + cfg.window_duration > fl.t_max:
        raise ValueError(f"창이 비행을 벗어난다: t0={t0} + {cfg.window_duration:.3f}s "
                         f"> t_max={fl.t_max:.3f}s")
    pos, rot, ang = window_poses(fl, t0, cfg)
    t = t0 + np.arange(cfg.n_pulses) * cfg.dt_radar
    to_r = rp[None, :] - pos
    R = np.linalg.norm(to_r, axis=1)
    u_w = to_r / R[:, None]
    u_b = np.einsum("nij,nj->ni", rot.transpose(0, 2, 1), u_w)   # R_bodyᵀ u_world
    return FlightWindow(
        t=t, pos=pos, rot=rot, blade_ang=ang, radar_pos=rp, R=R,
        u_world=u_w, u_body=u_b, fc=float(cfg.f_c), prf=float(cfg.prf),
        grade=str(grade),
        provenance=dict(
            data_dir=ddir, t_start=t0, n_pulses=int(cfg.n_pulses),
            rpm_scale=float(cfg.rpm_scale),
            esc_cols="esc[0..3].esc_rpm (po_sim/kinematics.py:24)",
            caveats=[
                "RPM 은 Phantom4 실측이 아니라 PX4 SITL x500 ESC × rpm_scale — 절대 회전수 인용 금지",
                "자세 부호 반전 이력 — 쿼터니언을 선배 규약 그대로 씀(재반전 안 함)",
                "350 Hz 인공물 이력 — f_flash 정수배 아닌 350 Hz 근방 선은 데이터 유래 후보",
            ]))


# --------------------------------------------------------------------------- #
#  2. 포저 — 임의 메쉬를 sbr_field 에 먹이는 공통 인터페이스
# --------------------------------------------------------------------------- #
class _BridgeMeshView:
    """sbr_field 가 요구하는 최소 인터페이스(v/f/g) — articulated_fast._MeshView 와 동형."""
    __slots__ = ("v", "f", "g")

    def __init__(self, v, f, g):
        self.v, self.f, self.g = v, f, g

    def to_mesh(self):
        """geom.Mesh 로 — Sionna 분기의 write_obj_per_group 용."""
        from geom import Mesh
        m = Mesh()
        m.v = [tuple(map(float, p)) for p in self.v]
        m.f = [tuple(map(int, t)) for t in self.f]
        m.g = list(self.g)
        return m


class SeniorMeshPoser:
    """선배 Phantom4 PLY 메쉬(po_sim.mesh 조립 규약) → 몸체프레임 _BridgeMeshView.

    · 그룹: body → "body", blade_1..4 → "prop" (우리 group_mat 규약과 맞춤).
    · 조립은 po_sim 과 같은 식: blade_i 정점 = spin(angle·dirs[i]) @ v + offset[i].
      (몸체 회전·평행이동은 **안 넣는다** — 그건 u_body/R 로 갔다.)
    · 날개 수 2 (DJI 9450S 계열), 프롭 반경은 메쉬에서 실측한다."""

    n_rotors = 4
    blades_per_rotor = 2

    def __init__(self, mesh_dir: str = MESH_DIR):
        dm = DroneMesh.load(mesh_dir)
        self._dm = dm
        self.dirs = np.asarray(BLADE_DIRS, float)
        self.offsets = np.asarray(BLADE_OFFSETS, float)
        v_blocks = [dm.body_v]
        f_blocks = [dm.body_f.astype(np.int64)]
        g_blocks = [np.full(len(dm.body_f), "body", dtype=object)]
        base = len(dm.body_v)
        self._slices = []
        for bv, bf in zip(dm.blade_v_list, dm.blade_f_list):
            self._slices.append((base, base + len(bv)))
            v_blocks.append(np.zeros((len(bv), 3)))
            f_blocks.append(bf.astype(np.int64) + base)
            g_blocks.append(np.full(len(bf), "prop", dtype=object))
            base += len(bv)
        self._v0 = np.concatenate(v_blocks, 0)
        self.f = np.concatenate(f_blocks, 0)
        self.g = np.concatenate(g_blocks, 0)
        # 프롭 반경 실측(허브 중심에서 최대 xy 거리) — f_tip 계산용
        r = [float(np.linalg.norm(bv[:, :2], axis=1).max()) for bv in dm.blade_v_list]
        self.prop_radius_m = float(np.mean(r))
        self.key = "phantom4_senior"

    def pose(self, blade_ang_4) -> _BridgeMeshView:
        """누적 날개각 (4,) [rad, 부호 없음] → 몸체프레임 스냅샷.

        부호는 선배 engine 과 같은 자리에서 붙인다: angle_signed = ang·dirs (po_sim engine:83)."""
        v = self._v0.copy()
        for i, (a, b) in enumerate(self._slices):
            M = spin_matrix(float(blade_ang_4[i]) * self.dirs[i])
            v[a:b] = (M @ self._dm.blade_v_list[i].T).T + self.offsets[i]
        return _BridgeMeshView(v, self.f, self.g)


class OursPoser:
    """우리 CAD (drones.DRONES + articulated_fast.FastPoser) — 같은 인터페이스.

    · PX4 blade_ang(부호 없음, rad)을 FastPoser 규약(로터별 부호 포함 위상[deg])으로:
        phase_deg[i] = dirs_ours[i] · degrees(blade_ang[i])
    · ⚠ 로터 순서 대응(선배 FR/BL/FL/BR ↔ 우리 rotor_layout)은 **임의**다 — 4 로터가
      독립 rpm 을 갖는 통계적 성질만 보존된다. 로터별 궤적 추적 주장에는 쓰지 말 것.
    · 로터 수가 4 가 아닌 기체(s1000plus 등)는 blade_ang 4 열을 되풀이해 채운다."""

    def __init__(self, drone_key: str = "matrice4e"):
        from drones import DRONES
        from articulated_fast import FastPoser
        self.spec = DRONES[drone_key]
        self.fp = FastPoser(self.spec)
        self.dirs = np.asarray(self.fp.dirs, float)
        self.n_rotors = len(self.dirs)
        self.blades_per_rotor = 2
        self.prop_radius_m = float(self.spec.prop_dia_mm) / 2000.0
        self.key = drone_key

    def pose(self, blade_ang_4) -> object:
        ang = np.resize(np.asarray(blade_ang_4, float), self.n_rotors)
        ph = [float(d * np.degrees(a)) for d, a in zip(self.dirs, ang)]
        return self.fp.pose(ph)


# --------------------------------------------------------------------------- #
#  3. (a) 우리 커널 팔
# --------------------------------------------------------------------------- #
def grid_ref_for_window(poser, win: FlightWindow, spacing: float, n_sample: int = 33):
    """윈도우 전 구간을 덮는 얼린 광선 격자 — rcs_sbr.grid_ref_from 규약."""
    from rcs_sbr import grid_ref_from
    idx = np.linspace(0, win.n - 1, min(n_sample, win.n)).astype(int)
    return grid_ref_from([poser.pose(win.blade_ang[i]) for i in idx],
                         win.fc, spacing=spacing)


def run_ours(poser, win: FlightWindow, *, div: int = 12, mat_mode: str = "ours",
             blade_mat: str = "nylon", spherical: bool = True, ptd: bool = False,
             pulses: slice | np.ndarray | None = None, attach_bulk_phase: bool = True,
             shell_groups=None, progress_every: int = 128) -> dict:
    """우리 커널로 한 윈도우(또는 부분)를 돈다 → 공통 규약 슬로타임 열.

    반환 dict:
      s        (m,) complex — **공통 규약** E·e^{−j2kR(t)} (attach_bulk_phase=True; 부호 검산은
               모듈 docstring — 상대 위상 부호가 선배와 같아 conj 하지 않는다)
      E_raw    (m,) complex — sbr_field 원본(몸체프레임, ctr 원점)
      idx, R, meta(provenance)
    ⚠ 소규모 시험 전용 — 생산 투입은 PTD 수리 게이트 뒤(모듈 docstring).
    ⚠ spherical=True 면 range_m=R(t) 실제 거리를 준다(15 m 고정 규약이 아니라 **로그의 거리**).
      1/r 확산은 커널 규약대로 안 들어간다 — 절대 눈금은 rx_noise 가 앵커로 잡는다."""
    import time
    from rcs_sbr import sbr_field
    gm = group_mat_for(poser, mat_mode, blade_mat)
    # ⚠유전체 셸 규약 — 선배 메쉬는 body 가 **금속**이라 셸이 될 수 없다(rcs_sbr 가드가
    #   |Γ|>0.5 에서 예외를 던진다). 열린 프레임 규약대로 shell_groups=() 로 끈다.
    #   우리 CAD(플라스틱 셸)는 생산 규약(None=기본 셸 해석)을 그대로 둔다.
    if shell_groups is None and isinstance(poser, SeniorMeshPoser):
        shell_groups = ()
    d = (C0 / win.fc) / div
    idx = (np.arange(win.n) if pulses is None
           else (np.arange(win.n)[pulses] if isinstance(pulses, slice)
                 else np.asarray(pulses, int)))
    gref = grid_ref_for_window(poser, win, d)
    k = 2.0 * np.pi * win.fc / C0
    E = np.zeros(idx.size, complex)
    t0 = time.time()
    for j, i in enumerate(idx):
        i = int(i)
        E[j] = sbr_field(poser.pose(win.blade_ang[i]), gm, win.fc, win.u_body[i],
                         spacing=d, grid_ref=gref,
                         range_m=(float(win.R[i]) if spherical else None),
                         ptd=ptd, shell_groups=shell_groups)
        if progress_every and j and j % progress_every == 0:
            e = time.time() - t0
            print(f"    ours[{poser.key}] {j}/{idx.size} {e:.0f}s "
                  f"ETA {(idx.size - j) / j * e:.0f}s", flush=True)
    s = (E * np.exp(-1j * 2.0 * k * win.R[idx])) if attach_bulk_phase else E.copy()
    return dict(s=s, E_raw=E, idx=idx, R=win.R[idx], engine=f"ours/{poser.key}",
                meta=dict(div=div, mat_mode=mat_mode, blade_mat=blade_mat,
                          spherical=spherical, ptd=ptd, fc=win.fc, prf=win.prf,
                          phase_convention="s = E·exp(-j2kR) — 상대위상 부호는 선배와 동일"
                                           "(모듈 docstring 부호 검산)",
                          spreading="none (1/r 미포함 — rx_noise 앵커 규약)",
                          seconds=round(time.time() - t0, 1), **win.provenance))


# --------------------------------------------------------------------------- #
#  4. (b) 선배 PO 팔 — 참조 로더 (계산 안 함)
# --------------------------------------------------------------------------- #
def load_senior_window(out_dir: str, w_idx: int, occ: str = "full",
                       blade_mat: str = "nylon") -> dict:
    """선배 생산물 window_XXXXX.npz → 재구성 신호 (MANIFEST 규약).

        occ=none: body_none + blade_none_X · occ=body: body_occ + blade_none_X
        occ=full: body_occ + blade_occ_X
    선배 신호는 이미 e^{−j2kR}·1/R² 포함 — 공통 규약과 부호 동일, **눈금은 다르다**
    (1/R² 포함 vs 우리 무확산). 모양 비교는 그대로, 절대 비교는 rx_noise 앵커를 거칠 것."""
    z = np.load(os.path.join(out_dir, f"window_{w_idx:05d}.npz"))
    if occ == "none":
        s = z["body_none"] + z[f"blade_none_{blade_mat}"]
    elif occ == "body":
        s = z["body_occ"] + z[f"blade_none_{blade_mat}"]
    else:
        s = z["body_occ"] + z[f"blade_occ_{blade_mat}"]
    return dict(s=np.asarray(s, complex), engine="senior_po",
                meta=dict(occ=occ, blade_mat=blade_mat, src=out_dir, w_idx=w_idx))


def run_senior_po(poser: SeniorMeshPoser, win: FlightWindow,
                  pulses: slice | np.ndarray | None = None,
                  blade_mat: str = "nylon", occ: str = "full") -> dict:
    """선배 PO 엔진을 **그대로 호출**해 같은 펄스를 계산한다(참조·교차검증용).

    재구현이 아니다 — po_sim.engine.compute_pulse_decomposed 를 부른다.
    선배 신호는 e^{−j2kR}·1/R² 포함 월드프레임 조립이라 공통 규약과 부호가 같다."""
    from po_sim.engine import compute_pulse_decomposed, SceneSpec
    from po_sim.occlusion import build_body_bvh
    cfg = SimConfig(f_c=win.fc, prf=int(win.prf))
    spec = SceneSpec(body_mat=BODY_MAT, blade_mats=BLADE_MATS,
                     blade_mat_keys=[blade_mat], blade_offsets=self_offsets(),
                     blade_dirs=np.asarray(BLADE_DIRS))
    idx = (np.arange(win.n) if pulses is None
           else (np.arange(win.n)[pulses] if isinstance(pulses, slice)
                 else np.asarray(pulses, int)))
    s = np.zeros(idx.size, complex)
    bvh = None
    for j, i in enumerate(idx):
        i = int(i)
        if j % 100 == 0:
            bvh = build_body_bvh(poser._dm, win.rot[i], win.pos[i])
        d = compute_pulse_decomposed(poser._dm, cfg, spec, win.rot[i], win.pos[i],
                                     win.blade_ang[i], win.radar_pos, bvh)
        if occ == "none":
            s[j] = d["body_none"] + d[f"blade_none_{blade_mat}"]
        elif occ == "body":
            s[j] = d["body_occ"] + d[f"blade_none_{blade_mat}"]
        else:
            s[j] = d["body_occ"] + d[f"blade_occ_{blade_mat}"]
    return dict(s=s, idx=idx, engine="senior_po/direct",
                meta=dict(blade_mat=blade_mat, occ=occ, fc=win.fc, prf=win.prf))


def self_offsets() -> np.ndarray:
    """선배 configs.default.BLADE_OFFSETS — 별칭(가독성)."""
    return np.asarray(BLADE_OFFSETS, float)


# --------------------------------------------------------------------------- #
#  5. (c) Sionna PathSolver 팔 — 1 윈도우 한정
# --------------------------------------------------------------------------- #
def run_sionna_window(poser, win: FlightWindow, *, spp: int = 1_000_000,
                      max_depth: int = 1, pulses=None, max_pulses: int = 256,
                      rng_override_m: float | None = None,
                      progress_every: int = 32) -> dict:
    """Sionna PathSolver 로 한 윈도우 — elevation_sweep_md.py sionna 분기 규약.

    per-pulse: 몸체프레임 OBJ 내보내기 → build_scene → place(az,el from u_body, rng=R)
    → PathSolver → E = Σ a·e^{−j2πfcτ} (표적 경유 경로만, NO_OBJ 게이트).
    부호·벌크 위상은 실제 τ 에서 나오므로 이미 공통 규약이다(conj 불필요).

    ⚠ max_pulses 기본 256 — 생산(5000)은 max_pulses=None 로 **명시** 해제해야 한다
      (대규모 생산 실행 금지 규약).
    ⚠ rng_override_m: 배관 시험 전용 — 거리를 로그값 대신 이 값으로 박아 광선 예산을
      아낀다(경로 수 ∝ (표적크기/R)² 이라 원거리 스모크는 예산이 폭발한다). 기하 충실성이
      깨지므로 **생산·비교 수치에 쓰면 안 된다** — meta 에 그대로 남는다."""
    import time
    import report15_probe as RP
    from drones import DRONES, DRONE_GROUP_MAT, drone_colors
    idx = (np.arange(win.n) if pulses is None
           else (np.arange(win.n)[pulses] if isinstance(pulses, slice)
                 else np.asarray(pulses, int)))
    if max_pulses is not None and idx.size > max_pulses:
        raise ValueError(
            f"run_sionna_window: {idx.size} 펄스 > max_pulses={max_pulses}. "
            "생산 실행은 게이트 뒤다 — 정말 필요하면 max_pulses=None 을 명시하라.")
    # 재질/색 — 우리 CAD 는 우리 표, 선배 메쉬는 매핑(§0)
    if isinstance(poser, OursPoser):
        gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
        cols = drone_colors(poser.spec)
    else:
        gm = group_mat_for(poser, "ours")            # Sionna 는 우리 표 키만 안전
        cols = {"body": (0.5, 0.5, 0.5), "prop": (0.3, 0.3, 0.3)}
    E = np.zeros(idx.size, complex)
    npaths = np.zeros(idx.size, int)
    t0 = time.time()
    for j, i in enumerate(idx):
        i = int(i)
        mv = poser.pose(win.blade_ang[i])
        m = mv.to_mesh()
        az, el = win.az_el_deg(i)
        dd = os.path.join(RP.SCRATCH,
                          f"px4_{poser.key}_g{win.grade}_pid{os.getpid()}_{i % 2}")
        paths_obj = m.write_obj_per_group(dd, poser.key)
        parts = [RP.Part(name=f"{poser.key}_{g}_{i % 2}", obj=p, mat_key=gm[g],
                         color=cols.get(g, (0.5, 0.5, 0.5)))
                 for g, p in paths_obj.items()]
        sc = RP.build_scene(parts, fc=win.fc)
        rng_i = float(win.R[i]) if rng_override_m is None else float(rng_override_m)
        RP.place(sc, az=az, el=el, rng=rng_i, baseline=0.0)
        p = RP.rt.PathSolver()(
            sc, los=True, specular_reflection=True, diffuse_reflection=True,
            refraction=False, diffraction=False, edge_diffraction=False,
            max_depth=max_depth, samples_per_src=spp,
            max_num_paths_per_src=RP.MAX_PATHS, seed=1)
        try:
            aa, tau, _, O = RP.unpack(p)
        except ValueError:
            aa = np.zeros(0)
        if aa.size:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            E[j] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * win.fc * tau[hit])))
            npaths[j] = int(hit.sum())
        RP.drop_scratch(dd)
        if progress_every and j and j % progress_every == 0:
            e = time.time() - t0
            print(f"    sionna[{poser.key}] {j}/{idx.size} {e:.0f}s "
                  f"ETA {(idx.size - j) / j * e:.0f}s", flush=True)
    return dict(s=E, idx=idx, R=win.R[idx], npaths=npaths,
                engine=f"sionna/{poser.key}",
                meta=dict(spp=spp, max_depth=max_depth, fc=win.fc, prf=win.prf,
                          rng_override_m=rng_override_m,
                          phase_convention="Σ a·e^{-j2πfcτ} (실기하 — 공통 규약)",
                          seconds=round(time.time() - t0, 1), **win.provenance))


# --------------------------------------------------------------------------- #
#  6. 회전수 진단 — f_flash 를 로그에서 직접 잰다
# --------------------------------------------------------------------------- #
def rotor_rates_hz(win: FlightWindow) -> dict:
    """창 안 평균 회전수 [rev/s] (로터별) + f_flash 후보.

    ⚠ 이 값은 x500 SITL RPM × rpm_scale 이다 — 기체 고증 인용 금지(모듈 docstring)."""
    dt = np.diff(win.t)
    f_rev = np.abs(np.diff(win.blade_ang, axis=0)) / (2 * np.pi) / dt[:, None]
    mean = f_rev.mean(axis=0)
    return dict(f_rev_hz=[round(float(x), 2) for x in mean],
                f_flash_hz=round(float(2.0 * mean.mean()), 2),   # 2날개 규약
                caveat="x500 SITL RPM × rpm_scale — 절대 회전수 인용 금지")
