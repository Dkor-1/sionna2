#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
report16 · 사다리 1단(우리 메쉬 = 기준)에서 **지표를 뽑고 예측과 대조하는** 단계
============================================================================

이 파일이 하는 일은 셋이다.

  1. 기반 단계(`report16_base`)가 못박아 둔 마이크로도플러 지표를 **전부** 계산한다.
     — 플래시 대조비 · 고차 성분 풍부도 · 도플러 폭 · 동체 대 블레이드 세기비.
     지표 함수는 재구현하지 않고 `report16_base.md_metrics16` 을 **불러다 쓴다**.

  2. 계산을 시작하기 **전에** 적어 둔 예측(사전 등록 파일)과 맞았는지 틀렸는지를
     하나씩 적는다. 틀린 것을 지우지 않는다 — 틀린 쪽이 더 중요한 발견이다.

  3. ⚠ **이 단의 결과를 못 믿을 이유**를 스스로 찾아 적는다. 말로만 적지 않고,
     가능한 것은 전부 **실제로 계산해서** 숫자로 적는다.

용어 (처음 나올 때 뜻을 푼다)
----------------------------------------------------------------------------
· 마이크로도플러 : 표적이 통째로 움직여 생기는 도플러 말고, 프로펠러처럼 **부속이
  따로 움직여** 만드는 주파수 흔들림.
· 위상 표 E(φ) : 프로펠러를 1회전 안에서 φ 만큼 돌려 놓고 잰 되돌아오는 신호.
  로터가 전부 같은 회전수로 돌면 시간신호는 1회전 주기의 정확한 되풀이라, 이 표를
  그대로 푸리에 변환하면 새는 것 없는 **선 스펙트럼**이 된다.
· 차수(order) m : 회전수 f_rot 의 m 배 되는 주파수 성분. 1차수 = 1회전에 한 번.
· 플래시 : 블레이드가 시선을 가로질러 설 때, 블레이드 위 모든 조각이 레이더에서
  거의 같은 거리에 놓여 되돌아오는 파가 한꺼번에 더해지는 순간의 봉우리.
· β = 4πR·cos(el)/λ : 팁이 만드는 최대 위상 흔들림. «팁 도플러 ÷ 회전수» 와 같다.
  살아 있을 수 있는 최고 차수이기도 하다.
· PO(물리광학) : 표면 각 조각이 «거울처럼» 되쏜다고 보고 위상 맞춰 더하는 근사.
  조각이 파장보다 충분히 커야 맞는다.

입력 (전부 앞 단이 이미 만들어 둔 것)
----------------------------------------------------------------------------
  outputs/report16_rung_mesh_full.json         · 1단 결과 + 사전 등록 사본 + 계약
  outputs/report16_rung_mesh_full_tables.npz   · 위상 표 (총합 · 프레임만 · 로터별)
  outputs/report16_rung_mesh_full_prereg.json  · 계산 전에 고정된 예측 (sha256 확인)
  outputs/report16_base_tables.npz             · 기준 단의 팔들(구·원판·평판·조밀메쉬)

새로 도는 계산 (GPU)
----------------------------------------------------------------------------
  · 고각 훑기 (el = 5·15·30·45·60°) — 헤드라인이 고각 15° 하나에만 매달려 있는지 본다.
  · 방위 촘촘히 (72 방위) — 24 방위 평균이 격자 때문에 흔들리는지 본다.
  · 가림 추정 — 우리 커널에는 가림이 없다. 그래서 «가렸어야 할 넓이» 가 얼마인지 잰다.

출력
----------------------------------------------------------------------------
  outputs/report16_metric_mesh_full.json        (지정 산출물)
  outputs/report16_metric_mesh_full_tables.npz  (방위별 지표 전량)
  outputs/figures/report16_metric_mesh_full.png

⛔ report15_* · make_report0N_* · src/drones.py · src/drone_cad.py 는 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
import report16_base as R                                              # noqa: E402

SCRATCH = os.environ.get("REPORT16_METRIC_SCRATCH",
                         "/tmp/claude-1015/-home-yunjung-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/r16metric")

RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_full.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_full_tables.npz")
PREREG = os.path.join(ROOT, "outputs", "report16_rung_mesh_full_prereg.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_mesh_full.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_metric_mesh_full_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_metric_mesh_full.png")

EL_SWEEP = (5.0, 15.0, 30.0, 45.0, 60.0)     # 헤드라인은 15° — 가운데에 둔다
N_AZ_FINE = 72                               # 5° 간격 (헤드라인은 24점 = 15° 간격)
MC_PHASE_DRAWS = 2048                        # 로터 상대위상 무작위 추첨 횟수
RPM_SPREAD = (0.0, 0.002, 0.01, 0.05, 0.20)  # 로터간 회전수 어긋남 (0 · 0.2 · 1 · 5 · 20 %)

MET_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
            "blade_comb_frac", "fd_edge_hz", "width_ratio", "width_ratio_10db",
            "width_ratio_30db", "dc_ac_db", "ac_frac_db", "sigma_eq_mean_dbsm",
            "ac_over_floor_db", "in_band_ac_frac", "in_band_ac_over_dc_db")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def _git_rev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


def _f(x):
    """json 이 삼킬 수 있는 실수로."""
    x = float(x)
    return x if math.isfinite(x) else None


# =========================================================================== #
#                    WORKER — 새 PO 계산 (고각 훑기 · 방위 촘촘히 · 가림 추정)
# =========================================================================== #
def _worker(keys):
    """헤드라인과 **같은 커널·같은 점구름 규칙**으로 고각/방위만 바꿔 다시 돈다.

    같은 규칙이라는 증거는 el=15°·24방위 판이 1단의 표와 **비트 단위로 같은가**로 잡는다
    (아래 main 의 `recompute_gate`). 다르면 이 훑기의 숫자는 비교 자격이 없다.
    """
    sys.path.insert(0, os.path.join(ROOT, "src"))
    from gpu import pick                       # ⚠ torch 보다 먼저 (CUDA 컨텍스트 고정)
    picked = pick(verbose=True)
    import torch

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,   # noqa: E402
                        drone_gamma_map)
    from rcs_po import mesh_to_points                                         # noqa: E402

    fc = R.FC_MAIN
    lam = R.C0 / fc
    k_wav = 2.0 * math.pi / lam
    tables, meta = {}, {}

    for key in keys:
        t0 = time.time()
        s = DRONES[key]
        gm = drone_gamma_map(s)
        frame = build_frame(s)
        Pf, Nf, dAf, wf_ = mesh_to_points(frame, lam / 6.0, gamma=gm)
        Wf = dAf * wf_
        prop = build_propeller(s, n=26)
        Pp, Np_, dAp, wp = mesh_to_points(prop, lam / 11.0, gamma=gm)
        Wp = dAp * wp
        Pm = Pp * np.array([1.0, -1.0, 1.0])          # 거울상 프로펠러(반대회전 로터)
        Nm_ = Np_ * np.array([1.0, -1.0, 1.0])
        rotors = rotor_layout(s)
        n_rot = len(rotors)
        nb = int(s.prop_blades)

        # 블레이드의 «긴 축» ψ₀ — 1단과 같은 방법으로 **여기서 다시** 계산한다(독립 확인용)
        xy = Pp[:, :2]
        c_xy = (dAp[:, None] * xy).sum(0) / dAp.sum()
        dxy = xy - c_xy
        Mxy = np.einsum("i,ij,ik->jk", dAp, dxy, dxy)
        evl, evc = np.linalg.eigh(Mxy)
        vmaj = evc[:, -1]
        psi0 = math.degrees(math.atan2(vmaj[1], vmaj[0])) % 180.0
        rr = np.hypot(xy[:, 0], xy[:, 1])
        R_tip = float(rr.max())

        per_el = {}
        for el in EL_SWEEP:
            proto = R.derive_protocol(s.prop_dia_mm, s.hover_rpm, nb, fc, el_deg=el)
            S = proto["n_phase"]
            phis = np.linspace(0.0, 2 * math.pi, S, endpoint=False)
            az_list = np.arange(R.N_AZ) * (360.0 / R.N_AZ)
            T = np.zeros((len(az_list), S), complex)
            Tf = np.zeros(len(az_list), complex)
            for ia, az in enumerate(az_list):
                u, A, R_t = R.look_and_antenna(az, el, R.RANGE_M)
                Ef = R.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, "spherical")
                Tf[ia] = Ef
                tot = np.full(S, Ef, complex)
                for rot in rotors:
                    d = float(rot["dir"])
                    P, N, W = (Pp, Np_, Wp) if d > 0 else (Pm, Nm_, Wp)
                    tot += R.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, rot["center"],
                                         math.radians(float(rot["base_ang"])), d, phis,
                                         "spherical")
                T[ia] = tot
            tables[f"el{int(el)}|{key}"] = T
            tables[f"el{int(el)}|frame|{key}"] = Tf
            per_el[str(int(el))] = proto

        # 방위 촘촘히 (el 은 헤드라인 그대로)
        proto15 = per_el[str(int(R.EL_DEG))]
        S15 = proto15["n_phase"]
        phis = np.linspace(0.0, 2 * math.pi, S15, endpoint=False)
        azf = np.arange(N_AZ_FINE) * (360.0 / N_AZ_FINE)
        Tfine = np.zeros((N_AZ_FINE, S15), complex)
        for ia, az in enumerate(azf):
            u, A, R_t = R.look_and_antenna(az, R.EL_DEG, R.RANGE_M)
            tot = np.full(S15, R.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t,
                                              "spherical"), complex)
            for rot in rotors:
                d = float(rot["dir"])
                P, N, W = (Pp, Np_, Wp) if d > 0 else (Pm, Nm_, Wp)
                tot += R.field_rotor(torch, dev, P, N, W, k_wav, A, R_t, rot["center"],
                                     math.radians(float(rot["base_ang"])), d, phis, "spherical")
            Tfine[ia] = tot
        tables[f"azfine|{key}"] = Tfine

        # ── 가림 추정 (z-버퍼) ────────────────────────────────────────────────
        #   우리 PO 커널은 «내 등» 만 가린다(법선이 반대면 뺀다). 다른 부품이 앞을 막는
        #   것은 못 본다. 그래서 «막혔어야 할 넓이» 를 점구름 깊이버퍼로 추정한다.
        occ = _occlusion_estimate(Pf, Nf, dAf, Pp, Np_, dAp, Pm, Nm_, rotors, lam)
        meta[key] = dict(
            protocol_per_el=per_el, n_rot=n_rot, blades=nb,
            psi0_deg=psi0, tip_radius_m=R_tip,
            rotors=[dict(center=[float(c) for c in r["center"]],
                         base_ang_deg=float(r["base_ang"]), dir=int(r["dir"])) for r in rotors],
            n_frame_pts=int(len(Wf)), n_blade_pts=int(len(Wp)),
            occlusion=occ, seconds=float(time.time() - t0))
        print(f"  [metric] {key:12s} S15={S15:5d} pts(f/b)={len(Wf)}/{len(Wp)} "
              f"[{meta[key]['seconds']:.1f}s]", flush=True)

    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, "probe.npz"),
                        **{k.replace("|", "__"): v for k, v in tables.items()})
    with open(os.path.join(SCRATCH, "probe_meta.json"), "w") as f:
        json.dump(dict(gpu=picked, keys=keys, el_sweep=list(EL_SWEEP), n_az_fine=N_AZ_FINE,
                       drones=meta), f, ensure_ascii=False)


def _occlusion_estimate(Pf, Nf, dAf, Pp, Np_, dAp, Pm, Nm_, rotors, lam, n_phase_probe=8):
    """«가렸어야 할 넓이» 를 점구름 깊이버퍼로 **추정**한다.

    방법 — 시선 방향 u 로 보아 (1) 조명된 점만 남기고(법선·u > 0, 우리 커널이 세는 점과
    같다), (2) u 에 수직인 평면에 격자(칸 크기 λ/6)를 깔아 칸마다 «가장 앞» 깊이를
    기록하고, (3) 자기보다 앞에 다른 부품 점이 있는 점을 «가려진 것» 으로 센다.

    ⚠ 이것은 광선을 쏘아 정확히 푼 값이 아니라 **추정**이다. 칸 크기만큼 거칠고, 점이
      성기면 실제보다 덜 가려진 것으로 나온다. 그래서 «적어도 이만큼» 으로 읽어야 한다.
    """
    d = lam / 6.0
    out = {}
    for el in EL_SWEEP:
        fr_hidden, bl_hidden = [], []
        for az in np.arange(R.N_AZ) * (360.0 / R.N_AZ):
            u, _, _ = R.look_and_antenna(az, el, R.RANGE_M)
            e1 = np.cross(u, [0.0, 0.0, 1.0])
            if np.linalg.norm(e1) < 1e-9:
                e1 = np.array([1.0, 0.0, 0.0])
            e1 = e1 / np.linalg.norm(e1)
            e2 = np.cross(u, e1)
            for ip in range(n_phase_probe):
                phi = 2 * math.pi * ip / n_phase_probe
                Pl, Nl, Al, tagl = [Pf], [Nf], [dAf], [np.zeros(len(dAf), int)]
                for j, rot in enumerate(rotors):
                    dr = float(rot["dir"])
                    P0, N0 = (Pp, Np_) if dr > 0 else (Pm, Nm_)
                    th = math.radians(float(rot["base_ang"])) + dr * phi
                    c, s_ = math.cos(th), math.sin(th)
                    Rz = np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])
                    Pl.append(P0 @ Rz.T + np.asarray(rot["center"], float))
                    Nl.append(N0 @ Rz.T)
                    Al.append(dAp)
                    tagl.append(np.full(len(dAp), j + 1, int))
                P = np.concatenate(Pl); N = np.concatenate(Nl)
                A = np.concatenate(Al); tag = np.concatenate(tagl)
                lit = (N @ u) > 0
                P, A, tag = P[lit], A[lit], tag[lit]
                if len(P) == 0:
                    continue
                depth = P @ u
                ia = np.floor((P @ e1) / d).astype(np.int64)
                ib = np.floor((P @ e2) / d).astype(np.int64)
                cell = (ia - ia.min()) * (ib.max() - ib.min() + 2) + (ib - ib.min())
                # 칸별 «가장 앞» 깊이와 그 주인(부품 태그)
                order = np.lexsort((-depth, cell))
                cs, ds, ts = cell[order], depth[order], tag[order]
                first = np.ones(len(cs), bool)
                first[1:] = cs[1:] != cs[:-1]
                front_cell = cs[first]
                front_depth = ds[first]
                front_tag = ts[first]
                pos = np.searchsorted(front_cell, cell)
                fd = front_depth[pos]
                ft = front_tag[pos]
                # «다른 부품» 이 내 앞에 있을 때만 가려진 것으로 센다
                hid = (fd > depth + 1e-9) & (ft != tag)
                fr = tag == 0
                bl = ~fr
                if fr.any():
                    fr_hidden.append(float((A[fr & hid].sum()) / max(A[fr].sum(), 1e-30)))
                if bl.any():
                    bl_hidden.append(float((A[bl & hid].sum()) / max(A[bl].sum(), 1e-30)))
        out[str(int(el))] = dict(
            blade_area_hidden_frac_mean=float(np.mean(bl_hidden)) if bl_hidden else None,
            blade_area_hidden_frac_max=float(np.max(bl_hidden)) if bl_hidden else None,
            frame_area_hidden_frac_mean=float(np.mean(fr_hidden)) if fr_hidden else None,
            frame_area_hidden_frac_max=float(np.max(fr_hidden)) if fr_hidden else None,
            n_samples=len(bl_hidden))
    out["method_ko"] = ("시선에 수직인 λ/6 격자 깊이버퍼. 조명된 점(법선·u>0)만 세고, "
                        "같은 칸에서 **다른 부품** 점이 더 앞에 있으면 가려진 것으로 본다. "
                        "8 위상 × 24 방위 평균. ⚠ 광선추적이 아니라 추정이며 하한에 가깝다.")
    return out


# =========================================================================== #
#                        ① 지표 전량 — 방위마다 하나씩
# =========================================================================== #
def metrics_all(Z, rung, band, wfront, key, proto=None):
    """저장된 위상 표에서 base 의 지표를 **방위마다** 전부 뽑는다."""
    pre = "hi__" if band == "hi" else ""
    T = Z[f"{pre}{key}__{wfront}"]
    kc = rung["kinematics_contract"]["per_drone"][key]
    proto = proto or (kc["protocol_hi"] if band == "hi" else kc["protocol_main"])
    nb = int(kc["prop_blades"])
    per = [R.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
    arr = {k: np.array([m[k] for m in per], float) for k in MET_KEYS}
    arr["metrics_interpretable"] = np.array([float(m["metrics_interpretable"]) for m in per])
    return arr, T, proto, nb


def summ(v):
    v = np.asarray([x for x in np.asarray(v, float) if np.isfinite(x)], float)
    if v.size == 0:
        return dict(mean=None, sd=None, n=0)
    return dict(mean=_f(v.mean()), sd=_f(v.std(ddof=1)) if v.size > 1 else 0.0,
                min=_f(v.min()), max=_f(v.max()), median=_f(np.median(v)), n=int(v.size))


# =========================================================================== #
#              ② 동체 대 블레이드 — 저장된 «프레임만» 표로 깨끗하게 가른다
# =========================================================================== #
def body_blade_split(Z, rung, key, wfront="spherical"):
    r"""base 의 `dc_ac_db` 는 «변하지 않는 성분 대 변하는 성분» 이다. 그런데 변하지 않는
    성분에는 동체뿐 아니라 **로터의 평균값**도 섞여 있다 — 프로펠러도 1회전 평균이 0 이
    아니기 때문이다. 1단이 «프레임만» 표를 따로 저장해 두었으므로 여기서 갈라 놓는다.

        총합 E(az,φ) = E_frame(az) + Σ_r e_r(az,φ)            (저장된 표에서 정확히 성립)
        DC = E_frame + mean_φ Σ_r e_r,   AC = Σ_r (e_r − mean_φ e_r)

    · body_over_ac_db  : 동체만 대 AC — «진짜» 동체 대 블레이드 비
    · dc_ac_db         : base 정의 (동체 + 로터평균) 대 AC
    · contamination_db : 둘의 차. 이 값이 크면 base 의 dc_ac_db 를 «동체 세기» 로 읽으면 안 된다.
    """
    T = Z[f"{key}__{wfront}"]
    F = Z[f"frame__{key}__{wfront}"]
    Rt = Z[f"rot__{key}__{wfront}"]
    rec_err = float(np.max(np.abs(T - (F[:, None] + Rt.sum(axis=0)))))
    rotsum = Rt.sum(axis=0)
    dc = T.mean(axis=1)
    rot_dc = rotsum.mean(axis=1)
    ac = T - dc[:, None]
    p_ac = (np.abs(ac) ** 2).mean(axis=1)
    p_body = np.abs(F) ** 2
    p_dc = np.abs(dc) ** 2
    p_rotdc = np.abs(rot_dc) ** 2
    db = lambda a, b: 10 * np.log10(np.maximum(a, 1e-300) / np.maximum(b, 1e-300))
    body_ac = db(p_body, p_ac)
    dc_ac = db(p_dc, p_ac)
    # 로터를 코히어런트하게 더한 값과 세기만 더한 값 — 로터끼리의 간섭이 얼마나 되나
    p_ac_coh = p_ac
    ac_each = Rt - Rt.mean(axis=2, keepdims=True)
    p_ac_inc = (np.abs(ac_each) ** 2).mean(axis=2).sum(axis=0)
    return dict(
        reconstruction_max_abs_err=_f(rec_err),
        reconstruction_note_ko="총합 = 프레임 + 로터합 이 저장된 표에서 정확히 성립하는지 확인한 값(0 이어야 한다).",
        body_over_ac_db=summ(body_ac),
        dc_over_ac_db=summ(dc_ac),
        contamination_db=summ(dc_ac - body_ac),
        rotor_dc_over_body_db=summ(db(p_rotdc, p_body)),
        rotor_coherent_over_incoherent_db=summ(db(p_ac_coh, p_ac_inc)),
        body_share_of_dc_power=summ(p_body / np.maximum(p_dc, 1e-300)),
        what_ko=("동체(프레임)만 따로 저장된 표로 «동체 대 블레이드» 를 깨끗하게 갈랐다. "
                 "contamination_db 는 base 의 dc_ac_db 가 동체보다 얼마나 부풀어 있는지다 — "
                 "로터의 1회전 평균이 DC 에 같이 실리기 때문이다."),
        coherence_note_ko=("rotor_coherent_over_incoherent_db 가 0 보다 크면 로터들이 서로 보태고 "
                           "작으면 상쇄한다. 0 근처면 로터끼리 «따로 논다»(세기끼리 더하면 된다)."))


# =========================================================================== #
#          ③ 사전 예측 채점 — 1단 숫자를 베끼지 않고 표에서 다시 계산한다
# =========================================================================== #
def _flash_clusters(env, drop_db=3.0):
    """봉우리를 «−3 dB 위에서 이어진 덩어리» 로 센다(원형). 1단과 같은 규칙을 여기서 다시 구현해
    같은 답이 나오는지 본다 — 같은 코드를 부르면 «구현이 틀렸을 가능성» 을 못 잡는다."""
    S = len(env)
    thr = float(env.max()) * 10 ** (-drop_db / 20.0)
    hi = env >= thr
    if hi.all():
        return 1
    start = int(np.argmax(~hi))
    r = np.roll(hi, -start)
    return int(np.sum(r[1:] & ~r[:-1]) + (1 if r[0] else 0))


def flash_placement(Z, rung, probe_meta, key, wfront="spherical"):
    """P5·P6 — 봉우리가 **예측한 자리**에 서는가, 1회전에 **블레이드 수만큼** 서는가.

    예측 규칙(사전 등록 문장 그대로): «블레이드 스팬이 시선에 수직» 인 위상.
        blade_axis(φ) = base_ang + dir·φ + ψ₀,   조건: blade_axis − az ≡ 90° (mod 360/blades)
        → φ* = dir·(az + 90 − base_ang − ψ₀)  (mod 360/blades)
    ψ₀ 는 프로펠러 메쉬의 면적가중 주축 방향이며 **메쉬에서 계산**한다(맞춰 넣은 값이 아니다).
    여기서는 worker 가 다시 계산한 ψ₀ 를 쓴다 — 1단 값과 같은지도 함께 적는다.
    """
    Rt = Z[f"rot__{key}__{wfront}"]
    n_rot, n_az, S = Rt.shape
    kc = rung["kinematics_contract"]["per_drone"][key]
    nb = int(kc["prop_blades"])
    rot_meta = kc["rotors"]
    psi_probe = float(probe_meta["drones"][key]["psi0_deg"]) if probe_meta else None
    psi_rung = float(rung["flash_anatomy"][key]["blade_axis_offset_deg"])
    psi0 = psi_probe if psi_probe is not None else psi_rung
    step = 360.0 / S
    period = 360.0 / nb
    az_list = np.arange(n_az) * (360.0 / n_az)
    # 세 가지 «규칙을 숫자로 옮기는 방법» 을 모두 잰다.
    #   v0 : 스팬 = x 축 (ψ₀ 를 안 씀)
    #   v1 : 메쉬에서 계산한 ψ₀ 를 쓰되 모든 로터에 같은 부호
    #   v2 : 반대회전 로터에는 **거울상 프로펠러**가 달리므로 ψ₀ 의 부호가 뒤집힌다
    err = {"v0_x_axis": [], "v1_axis_no_mirror": [], "v2_axis_with_mirror": []}
    nflash, ok_n = [], []
    for j in range(n_rot):
        d = float(rot_meta[j]["dir"])
        ba = float(rot_meta[j]["base_ang_deg"])
        for ia, az in enumerate(az_list):
            env = np.abs(Rt[j, ia] - Rt[j, ia].mean())
            i_pk = int(np.argmax(env))
            meas = (i_pk * step) % period
            for tag, psi in (("v0_x_axis", 0.0), ("v1_axis_no_mirror", psi0),
                             ("v2_axis_with_mirror", psi0 if d > 0 else -psi0)):
                pred = (d * (az + 90.0 - ba - psi)) % period
                e = abs(meas - pred) % period
                err[tag].append(min(e, period - e) / step)
            n = _flash_clusters(env)
            nflash.append(n)
            ok_n.append(1.0 if n == nb else 0.0)
    variants = {t: dict(phase_err_steps=summ(v),
                        frac_within_1_step=_f(np.mean(np.asarray(v) <= 1.0)))
                for t, v in err.items()}
    es = np.asarray(err["v2_axis_with_mirror"])
    nflash = np.array(nflash, float)
    return dict(psi0_deg_recomputed=_f(psi0), psi0_deg_rung=_f(psi_rung),
                psi0_agrees=bool(psi_probe is None or abs(psi_probe - psi_rung) < 1e-6),
                n_cases=int(len(es)),
                phase_err_steps=summ(es),
                phase_err_deg=summ(es * step),
                frac_within_1_step=_f(np.mean(es <= 1.0)),
                variants=variants,
                variant_used="v2_axis_with_mirror",
                variant_note_ko=("⭐ 이 파일은 1단과 **따로** 구현했는데, 처음에는 거울상 로터를 놓쳐 "
                                 "v1 이 나왔다(반쪽만 맞음). 1단이 남겨 둔 정정과 같은 자리에서 같은 방식으로 "
                                 "틀렸다는 뜻이다 — 그래서 세 판을 다 남긴다. 채점에는 v2 를 쓴다."),
                n_flash_per_rev=summ(nflash),
                frac_n_flash_equals_blades=_f(np.mean(ok_n)),
                phase_step_deg=_f(step), blades=nb)


def score_predictions(prereg, mets, eps, placement):
    """예측 하나하나에 PASS/FAIL 을 붙인다. **문턱과 문장은 사전 등록 파일에서 읽는다.**"""
    rows = {}
    for p in prereg["predictions"]:
        pid = p["id"]
        thr = p["threshold"]
        vals, op = {}, p["op"]
        if pid == "P1":
            vals = {k: _f(np.mean(v["flash_contrast_db"])) for k, v in mets.items()}
        elif pid == "P2":
            vals = {k: _f(np.mean(v["blade_comb_frac"])) for k, v in mets.items()}
        elif pid == "P3":
            vals = {k: _f(np.mean(v["in_band_ac_frac"])) for k, v in mets.items()}
        elif pid == "P4":
            vals = {k: _f(np.mean(v["width_ratio"])) for k, v in mets.items()}
        elif pid == "P5":
            vals = {k: _f(v["frac_within_1_step"]) for k, v in placement.items()}
        elif pid == "P6":
            vals = {k: _f(v["frac_n_flash_equals_blades"]) for k, v in placement.items()}
        elif pid == "P7":
            vals = {k: _f(v) for k, v in eps.items()}
        if op == ">=":
            fails = [k for k, v in vals.items() if not (v is not None and v >= thr)]
            worst = min(vals.items(), key=lambda kv: (kv[1] is None, kv[1]))
        else:                                     # 'in' — 구간
            fails = [k for k, v in vals.items()
                     if not (v is not None and thr[0] <= v <= thr[1])]
            mid = 0.5 * (thr[0] + thr[1])
            worst = max(vals.items(), key=lambda kv: abs((kv[1] if kv[1] is not None else 1e9) - mid))
        rows[pid] = dict(prediction_ko=p["ko"], metric=p["metric"], op=op, threshold=thr,
                         why_ko=p["why_ko"], values=vals, n_drones=len(vals),
                         n_fail=len(fails), failed_drones=fails,
                         worst_drone=worst[0], worst=worst[1],
                         verdict="PASS" if not fails else "FAIL")
    n_pass = sum(1 for v in rows.values() if v["verdict"] == "PASS")
    return dict(rows=rows, n_pass=n_pass, n_total=len(rows),
                overall="PASS" if n_pass == len(rows) else "PARTIAL",
                scored_from="이 파일이 위상 표에서 다시 계산한 값 (1단 JSON 의 숫자를 베끼지 않았다)",
                honesty_ko="⛔ FAIL 은 그대로 둔다. 사전 등록 파일의 sha256 이 함께 실려 있어 예측을 뒤에서 고칠 수 없다.")


# =========================================================================== #
#           ④ 판별력 — 이 예측들은 «통과하기 쉬운» 예측이었나
# =========================================================================== #
def discriminative_power(rung):
    """회전대칭 팔(구·원판)에 **같은 지표**를 물려 «구조가 없을 때의 값» 을 잰다.

    기반 단계가 구·원판·평판 팔을 같은 규약으로 저장해 두었다. 구조가 없는 팔이 이미
    문턱을 넘어 버리는 지표라면, 그 예측을 통과한 것은 증거로서 값이 싸다.
    """
    if not os.path.exists(BASE_NPZ):
        return dict(absent=True)
    Zb = np.load(BASE_NPZ)
    out = {}
    for key in ("mini2", "matrice4e"):
        kc = rung["kinematics_contract"]["per_drone"].get(key)
        if kc is None:
            continue
        proto = kc["protocol_main"]
        nb = int(kc["prop_blades"])
        arms = {}
        for arm in ("mesh", "sphere", "disc", "slab", "mesh_fine"):
            nm = f"main__G_0804__{key}__{arm}__spherical"
            if nm not in Zb.files:
                continue
            T = Zb[nm]
            per = [R.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
            lv = np.array([m["sigma_eq_mean_dbsm"] for m in per], float)
            aof = np.array([m["ac_over_floor_db"] for m in per], float)
            arms[arm] = dict(
                flash_contrast_db=_f(np.mean([m["flash_contrast_db"] for m in per])),
                blade_comb_frac=_f(np.mean([m["blade_comb_frac"] for m in per])),
                in_band_ac_frac=_f(np.mean([m["in_band_ac_frac"] for m in per])),
                width_ratio=_f(np.mean([m["width_ratio"] for m in per])),
                dc_ac_db=_f(np.mean([m["dc_ac_db"] for m in per])),
                ac_over_floor_db=_f(np.mean(aof[np.isfinite(aof)])),
                n_eff_orders=_f(np.mean([m["n_eff_orders"] for m in per])),
                eps_level_db=_f(lv.std(ddof=1)),
                interpretable_frac=_f(np.mean([m["metrics_interpretable"] for m in per])))
        out[key] = arms
    # 문턱 대비 여유 — «구조 없는 팔» 이 이미 넘는가
    verdicts = {}
    for pid, met, thr, direction in (("P1", "flash_contrast_db", 3.0, ">="),
                                     ("P2", "blade_comb_frac", 0.5, ">="),
                                     ("P3", "in_band_ac_frac", 0.9, ">="),
                                     ("P7", "eps_level_db", 0.5, ">=")):
        rows = {}
        for key, arms in out.items():
            if "mesh" not in arms:
                continue
            mesh = arms["mesh"][met]
            nulls = {a: arms[a][met] for a in ("sphere", "disc") if a in arms}
            worst_null = max(nulls.values()) if nulls else None
            rows[key] = dict(mesh=mesh, nulls=nulls,
                             null_already_passes=bool(worst_null is not None and
                                                      worst_null >= thr),
                             separation=_f(mesh - worst_null) if worst_null is not None else None)
        verdicts[pid] = dict(metric=met, threshold=thr, rows=rows)
    return dict(arms=out, threshold_vs_null=verdicts,
                arm_meaning_ko=dict(
                    mesh="우리 CAD 메쉬 (사다리의 기준)",
                    sphere="드론 전체를 같은 부피의 구로 — 회전도 구조도 없다. 이론상 변조 정확히 0.",
                    disc="프로펠러만 같은 반경·두께의 회전대칭 원판으로. 돌기는 도는데 형상이 회전에 불변이라 물리적 변조가 정확히 0. 동체는 그대로.",
                    slab="프로펠러를 스팬·코드·부피를 지킨 평판으로. 구조는 있으나 세부가 없다.",
                    mesh_fine="같은 메쉬를 4배 촘촘한 점구름으로 — 이산화가 답을 바꾸는지 보는 대조."),
                what_ko=("회전대칭 팔(구·원판)은 원리적으로 블레이드 플래시를 못 낸다. 그 팔이 "
                         "같은 지표에서 얼마를 내는지가 곧 «구조가 없을 때의 바닥» 이다."),
                key_reading_ko=(
                    "⭐ 여기서 이 단의 가장 아픈 사실이 나온다 — flash_contrast_db 는 **바닥 방어막이 없다**. "
                    "변조가 정확히 0 인 팔에서도 5~13 dB 를 읽는다(0 나누기 0 에 가까운 잡음비다). "
                    "그래서 P1 통과는 그 자체로 «블레이드 플래시가 있다» 의 증거가 못 된다. 증거가 되는 것은 "
                    "**함께 읽는 두 값**이다: 대역 안 AC 몫(우리 메쉬 1.000 대 널 0.001~0.14)과 "
                    "수치 바닥 대비 AC(ac_over_floor_db)."),
                caveat_ko=("⚠ 구·원판 팔의 폭·풍부도 지표는 base 스스로 «해석 금지» 라고 못박은 값이다"
                           "(AC 가 수치 잔차라 대역 밖에 있다). 여기서는 «문턱을 넘느냐» 만 본다."))


# =========================================================================== #
#         ⑤ 흔들어 보기 — 헤드라인 숫자가 어떤 가정에 매달려 있나
# =========================================================================== #
def shake_rotor_phase(Z, rung, key, headline_fc=None, n_draw=MC_PHASE_DRAWS, seed=16):
    """로터끼리의 **상대 위상**은 모델이 정해 준 값(장착 각도)이다. 실제 드론에서 네 로터의
    상대 위상은 통제되지 않는다. 상대 위상을 무작위로 돌려 가며 지표가 얼마나 흔들리는지 본다.
    (저장된 로터별 표를 원형으로 밀기만 하면 되므로 새 계산이 필요 없다.)"""
    Rt = Z[f"rot__{key}__spherical"]
    F = Z[f"frame__{key}__spherical"]
    n_rot, n_az, S = Rt.shape
    kc = rung["kinematics_contract"]["per_drone"][key]
    proto, nb = kc["protocol_main"], int(kc["prop_blades"])
    rng = np.random.default_rng(seed)
    fc_list, comb_list = [], []
    for _ in range(n_draw):
        sh = rng.integers(0, S, size=n_rot)
        tot = np.broadcast_to(F[:, None], (n_az, S)).copy()
        for j in range(n_rot):
            tot = tot + np.roll(Rt[j], int(sh[j]), axis=1)
        ms = [R.md_metrics16(tot[i], proto, nb) for i in range(n_az)]
        fc_list.append(np.mean([m["flash_contrast_db"] for m in ms]))
        comb_list.append(np.mean([m["blade_comb_frac"] for m in ms]))
    fc_arr = np.asarray(fc_list, float)
    pct = (_f(100.0 * np.mean(fc_arr <= headline_fc)) if headline_fc is not None else None)
    # 로터별 플래시가 헤드라인 배치에서 얼마나 «같이» 서는가 — 위 결과의 원인을 보는 자리
    spread_deg = []
    period = 360.0 / nb
    for ia in range(n_az):
        ph = []
        for j in range(n_rot):
            env = np.abs(Rt[j, ia] - Rt[j, ia].mean())
            ph.append((int(np.argmax(env)) * 360.0 / S) % period)
        ph = np.sort(np.asarray(ph))
        gaps = np.diff(np.concatenate([ph, [ph[0] + period]]))
        spread_deg.append(period - gaps.max())      # 원형에서 «가장 큰 빈 곳» 을 뺀 폭
    return dict(n_draw=int(n_draw),
                flash_contrast_db=summ(fc_list), blade_comb_frac=summ(comb_list),
                headline_flash_contrast_db=_f(headline_fc),
                headline_percentile_in_random=pct,
                headline_minus_random_mean_db=(_f(headline_fc - float(np.mean(fc_arr)))
                                               if headline_fc is not None else None),
                rotor_flash_spread_deg=summ(spread_deg),
                rotor_flash_period_deg=_f(period),
                what_ko=("로터 상대위상을 무작위로 바꿔 가며 다시 잰 값. 헤드라인은 장착 각도가 정한 "
                         "한 가지 상대위상일 뿐이다."),
                spread_note_ko=("rotor_flash_spread_deg = 헤드라인 배치에서 네(또는 여덟) 로터의 플래시가 "
                                "1주기(%.0f°) 안에서 차지하는 폭. 이 값이 작으면 로터들이 «거의 같이» "
                                "번쩍인다는 뜻이고, 그러면 합쳐진 봉우리가 커진다." % period))


def shake_rpm_spread(Z, rung, key, spreads=RPM_SPREAD, n_rev=None, seed=16):
    r"""헤드라인 규약은 «네 로터가 **정확히 같은 회전수**» 를 가정한다. 그래야 1회전 표만으로
    시간신호가 완전히 되풀이되고 스펙트럼이 새지 않는다. 실제 호버에서는 자세를 잡느라
    로터마다 회전수가 조금씩 다르다.

    저장된 로터별 표는 유한한 푸리에 급수라 **임의의 위상에서 정확히** 값을 매길 수 있다.
    로터 j 를 f_rot(1+δ_j) 로 돌려 슬로타임 신호를 만들고 같은 정의의 지표를 다시 잰다.
    빗(comb)은 «가장 가까운 차수» 로 반올림해 센다 — 회전수가 어긋나면 선이 차수 사이로
    흘러 몫이 떨어진다.
    """
    Rt = Z[f"rot__{key}__spherical"]
    F = Z[f"frame__{key}__spherical"]
    n_rot, n_az, S = Rt.shape
    kc = rung["kinematics_contract"]["per_drone"][key]
    nb = int(kc["prop_blades"])
    beta = float(kc["protocol_main"]["beta"])
    n_rev = int(n_rev or kc["protocol_main"]["n_rev"])
    band = max(2, int(math.ceil(1.5 * beta)))
    C = np.fft.fft(Rt, axis=2) / S                       # (rot, az, S) 푸리에 계수
    m_idx = np.fft.fftfreq(S, d=1.0 / S)                 # 부호 있는 차수
    n_t = S * n_rev
    t = np.arange(n_t) / float(S)                        # 회전수 단위 시간
    fo = np.fft.fftfreq(n_t, d=1.0 / (S * n_rev)) / float(n_rev)   # 차수 축
    near = np.rint(fo).astype(int)
    inb = (np.abs(fo) <= band) & (np.abs(near) > 0)
    comb = inb & (np.abs(near) % nb == 0)
    rng = np.random.default_rng(seed)
    out = {}
    for sp in spreads:
        dl = rng.normal(0.0, sp, size=n_rot) if sp > 0 else np.zeros(n_rot)
        dl = dl - dl.mean()                              # 평균 회전수는 유지
        sig = np.broadcast_to(F[None, :], (n_t, n_az)).copy()      # (t, az)
        for j in range(n_rot):
            ph = np.exp(2j * math.pi * np.outer((1.0 + dl[j]) * t, m_idx))   # (t, S)
            sig += ph @ C[j].T                                               # (t, az)
        ac = sig - sig.mean(axis=0, keepdims=True)
        env = np.abs(ac)
        fcs = 20 * np.log10(np.maximum(env.max(axis=0), 1e-300) /
                            np.maximum(np.median(env, axis=0), 1e-300))
        P = np.abs(np.fft.fft(ac, axis=0) / n_t) ** 2
        combs = P[comb].sum(axis=0) / np.maximum(P[inb].sum(axis=0), 1e-300)
        out[f"{sp:.4f}"] = dict(spread=sp, flash_contrast_db=summ(fcs), blade_comb_frac=summ(combs))
    return dict(rows=out, n_rev=n_rev,
                what_ko=("로터마다 회전수를 δ 만큼 흩뜨려 슬로타임 신호를 다시 만든 값. δ=0 이 헤드라인 "
                         "규약이다. 빗 몫이 δ 와 함께 떨어지면, 헤드라인의 «완벽한 빗» 은 부분적으로 "
                         "«전부 같은 회전수» 라는 가정이 만든 것이다."),
                caveat_ko=("⚠ 로터 하나하나는 여전히 자기 회전수의 빗을 만든다. 떨어지는 것은 «하나의 "
                           "f_rot 로 잰 차수 축» 에서 본 몫이다 — 물리가 사라진 것이 아니라 "
                           "우리 지표의 축이 흐려진 것이다."))


def az_grid_jackknife(mets):
    """24 방위 평균이 격자 때문에 흔들리는가 — 짝수/홀수 방위(각 12점)로 갈라 본다."""
    out = {}
    for key, m in mets.items():
        row = {}
        for met in ("flash_contrast_db", "width_ratio", "blade_comb_frac", "sigma_eq_mean_dbsm"):
            v = m[met]
            row[met] = dict(all24=_f(np.mean(v)), even12=_f(np.mean(v[0::2])),
                            odd12=_f(np.mean(v[1::2])),
                            half_split_gap=_f(abs(np.mean(v[0::2]) - np.mean(v[1::2]))))
        out[key] = row
    return out


# =========================================================================== #
#                                  그림
# =========================================================================== #
def make_figure(J, Z, mets, probe):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fleet = J["fleet"]
    fig = plt.figure(figsize=(19.5, 12.6))
    gs = fig.add_gridspec(3, 3, hspace=0.42, wspace=0.26,
                          left=0.055, right=0.985, top=0.905, bottom=0.055)
    fig.suptitle("report16 · metrics from the reference rung (our CAD mesh) — scored against "
                 "the pre-registered prediction", fontsize=15, fontweight="bold")

    # (a) 방위별 플래시 대조비
    ax = fig.add_subplot(gs[0, 0])
    az = np.arange(24) * 15.0
    for k in fleet:
        ax.plot(az, mets[k]["flash_contrast_db"], lw=1.1, alpha=0.85, label=k)
    ax.axhline(3.0, color="crimson", ls="--", lw=1.4)
    ax.text(2, 3.4, "P1 threshold 3 dB", color="crimson", fontsize=8)
    ax.set_xlabel("azimuth [deg]"); ax.set_ylabel("flash contrast [dB]")
    ax.set_title("(a) flash contrast vs azimuth (3.5 GHz, spherical)", fontsize=10)
    ax.legend(fontsize=6, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.20),
              frameon=False)
    ax.grid(alpha=0.3)

    # (b) 예측 채점판
    ax = fig.add_subplot(gs[0, 1])
    sc = J["prereg_scorecard_independent"]["rows"]
    pids = list(sc.keys())
    ax.axis("off")
    ax.set_title("(b) pre-registered predictions — scorecard", fontsize=10)
    y = 0.95
    for pid in pids:
        r = sc[pid]
        col = "seagreen" if r["verdict"] == "PASS" else "crimson"
        ax.text(0.02, y, pid, fontsize=11, fontweight="bold", transform=ax.transAxes)
        ax.text(0.12, y, r["verdict"], fontsize=11, color=col, fontweight="bold",
                transform=ax.transAxes)
        ax.text(0.34, y, f"{r['n_drones'] - r['n_fail']}/{r['n_drones']} drones",
                fontsize=9, transform=ax.transAxes)
        ax.text(0.62, y, f"worst {r['worst_drone']} = "
                         f"{r['worst']:.3g}" if r["worst"] is not None else "",
                fontsize=8, transform=ax.transAxes)
        y -= 0.135
    ax.text(0.02, y - 0.02, f"{J['prereg_scorecard_independent']['n_pass']}"
                            f"/{J['prereg_scorecard_independent']['n_total']} passed  ·  "
                            "recomputed here, not copied", fontsize=9, style="italic",
            transform=ax.transAxes)

    # (c) 동체 대 블레이드
    ax = fig.add_subplot(gs[0, 2])
    bb = J["body_vs_blade"]
    xs = np.arange(len(fleet))
    ax.bar(xs - 0.2, [bb[k]["dc_over_ac_db"]["mean"] for k in fleet], 0.4,
           label="dc_ac_db (base definition)", color="#4C78A8")
    ax.bar(xs + 0.2, [bb[k]["body_over_ac_db"]["mean"] for k in fleet], 0.4,
           label="airframe only / AC", color="#F58518")
    ax.set_xticks(xs); ax.set_xticklabels(fleet, rotation=40, ha="right", fontsize=7)
    gap = max(abs(bb[k]["contamination_db"]["mean"]) for k in fleet)
    ax.set_ylabel("[dB]"); ax.grid(alpha=0.3, axis="y")
    ax.set_title(f"(c) the DC term is almost entirely the airframe (gap $\\leq$ {gap:.2f} dB)",
                 fontsize=10)
    ax.legend(fontsize=7)

    # (d) 고각 훑기
    ax = fig.add_subplot(gs[1, 0])
    els = [float(e) for e in J["robustness"]["elevation_sweep"]["elevations_deg"]]
    for k in fleet:
        v = [J["robustness"]["elevation_sweep"]["rows"][k][f"{int(e)}"]["flash_contrast_db"]["mean"]
             for e in els]
        ax.plot(els, v, "o-", lw=1.2, ms=3.5, alpha=0.85, label=k)
    ax.axvline(15.0, color="k", ls=":", lw=1.2)
    ax.text(15.6, ax.get_ylim()[0] + 0.6, "headline el", fontsize=8)
    ax.set_xlabel("elevation [deg]"); ax.set_ylabel("flash contrast [dB]")
    ax.set_title("(d) does the headline hang on one elevation?", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=6, ncol=2)

    # (e) 로터 상대위상 흔들기
    ax = fig.add_subplot(gs[1, 1])
    mc = J["robustness"]["rotor_phase_monte_carlo"]
    ks = [k for k in fleet if k in mc]
    lo = [mc[k]["flash_contrast_db"]["min"] for k in ks]
    hi = [mc[k]["flash_contrast_db"]["max"] for k in ks]
    md = [mc[k]["flash_contrast_db"]["mean"] for k in ks]
    hd = [float(np.mean(mets[k]["flash_contrast_db"])) for k in ks]
    xs = np.arange(len(ks))
    ax.vlines(xs, lo, hi, color="#9ecae1", lw=7)
    ax.plot(xs, md, "s", color="#2171b5", ms=5, label="random rotor phases (mean)")
    ax.plot(xs, hd, "*", color="crimson", ms=11, label="headline (mounted angles)")
    ax.set_xticks(xs); ax.set_xticklabels(ks, rotation=40, ha="right", fontsize=7)
    ax.set_ylabel("flash contrast [dB]"); ax.grid(alpha=0.3, axis="y")
    ax.set_title("(e) rotor relative phase is a modelling choice", fontsize=10)
    ax.legend(fontsize=7)

    # (f) rpm 흩뜨리기
    ax = fig.add_subplot(gs[1, 2])
    rs = J["robustness"]["rpm_spread"]
    ks = [k for k in fleet if k in rs]
    sps = [r["spread"] for r in rs[ks[0]]["rows"].values()]
    for k in ks:
        ax.plot([100 * s for s in sps],
                [r["blade_comb_frac"]["mean"] for r in rs[k]["rows"].values()],
                "o-", lw=1.2, ms=4, label=k)
    ax.axhline(0.5, color="crimson", ls="--", lw=1.3)
    ax.text(0.02, 0.53, "P2 threshold", color="crimson", fontsize=8)
    ax.set_xscale("symlog", linthresh=0.2)
    ax.set_xlim(-0.02, 25)
    ax.set_xlabel("rotor-to-rotor rpm spread [%]"); ax.set_ylabel("blade comb fraction")
    ax.set_title("(f) the comb survives realistic rpm spread — my own doubt failed", fontsize=10)
    ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="lower left")

    # (g) 판별력 — 구조 없는 팔의 바닥 (지표에 바닥 방어막이 없다)
    ax = fig.add_subplot(gs[2, 0])
    dp = J["discriminative_power"]["arms"]
    keys = list(dp.keys())
    xs = np.arange(len(keys))
    for off, arm, lab, col in ((-0.26, "mesh", "our mesh", "#54A24B"),
                               (0.0, "disc", "prop -> symmetric disc (zero modulation)", "#B279A2"),
                               (0.26, "sphere", "whole drone -> sphere (zero modulation)", "#9D755D")):
        ax.bar(xs + off, [dp[k][arm]["flash_contrast_db"] for k in keys], 0.25,
               label=lab, color=col)
    ax.axhline(3.0, color="crimson", ls="--", lw=1.3)
    ax.text(-0.42, 3.4, "P1 threshold", color="crimson", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels(keys, fontsize=9)
    ax.set_ylabel("flash contrast [dB]"); ax.grid(alpha=0.3, axis="y")
    ax.set_title("(g) the metric reads 5-13 dB on targets that cannot modulate", fontsize=10)
    ax.legend(fontsize=6.5, loc="upper left")

    # (h) 가림 추정
    ax = fig.add_subplot(gs[2, 1])
    oc = J["reasons_to_doubt_detail"]["no_occlusion"]["blade_area_hidden_frac"]
    ocf = J["reasons_to_doubt_detail"]["no_occlusion"]["frame_area_hidden_frac"]
    ks = [k for k in fleet if k in oc]
    xs = np.arange(len(ks))
    ax.bar(xs - 0.2, [100 * ocf[k] for k in ks], 0.4, label="airframe hidden by props",
           color="#E45756")
    ax.bar(xs + 0.2, [100 * oc[k] for k in ks], 0.4, label="blades hidden by airframe",
           color="#FFBF79")
    ax.set_xticks(xs); ax.set_xticklabels(ks, rotation=40, ha="right", fontsize=7)
    ax.set_ylabel("hidden illuminated area [%]")
    ax.set_title("(h) area the kernel counts but geometry hides (el=15 deg, estimate)",
                 fontsize=10)
    ax.grid(alpha=0.3, axis="y"); ax.legend(fontsize=7)

    # (i) 두 대역
    ax = fig.add_subplot(gs[2, 2])
    b = J["metrics"]["hi"]["spherical"]
    a = J["metrics"]["main"]["spherical"]
    xs = np.arange(len(fleet))
    ax.bar(xs - 0.2, [a[k]["flash_contrast_db"]["mean"] for k in fleet], 0.4,
           label="3.5 GHz (quoted band, PO invalid for blades)", color="#4C78A8")
    ax.bar(xs + 0.2, [b[k]["flash_contrast_db"]["mean"] for k in fleet], 0.4,
           label="15.86 GHz (above the PO knee)", color="#72B7B2")
    ax.set_xticks(xs); ax.set_xticklabels(fleet, rotation=40, ha="right", fontsize=7)
    ax.set_ylabel("flash contrast [dB]"); ax.grid(alpha=0.3, axis="y")
    ax.set_title("(i) the band we quote is the band the kernel is weakest in", fontsize=10)
    ax.legend(fontsize=7)

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=140)
    plt.close(fig)
    return OUT_FIG


# =========================================================================== #
#                                   MAIN
# =========================================================================== #
def main(skip_compute=False):
    t_start = time.time()
    rung = json.load(open(RUNG_JSON))
    prereg = json.load(open(PREREG))
    Z = np.load(RUNG_NPZ)
    fleet = list(rung["fleet"])

    # 사전 등록 파일이 1단이 채점할 때 쓴 그 파일인지 확인
    sha_now = _sha256(PREREG)
    prereg_ok = (sha_now == rung["prereg"]["sha256"])

    # ── 새 계산 (GPU) ────────────────────────────────────────────────────────
    probe_npz = os.path.join(SCRATCH, "probe.npz")
    if not skip_compute or not os.path.exists(probe_npz):
        os.makedirs(SCRATCH, exist_ok=True)
        runner = os.path.join(SCRATCH, "run_probe.py")
        with open(runner, "w") as f:
            f.write("import sys, json\n"
                    f"sys.path.insert(0, {_HERE!r})\n"
                    "import report16_metric_mesh_full as M\n"
                    "M._worker(json.loads(sys.argv[1]))\n")
        print("▶ probe (elevation sweep · fine azimuth · occlusion)", flush=True)
        rc = subprocess.call([sys.executable, runner, json.dumps(fleet)], cwd=ROOT)
        if rc != 0:
            raise SystemExit(f"probe worker failed rc={rc}")
    Zp = np.load(probe_npz)
    probe = json.load(open(os.path.join(SCRATCH, "probe_meta.json")))

    # ── ① 지표 전량 ─────────────────────────────────────────────────────────
    print("· 지표 계산 (2 대역 × 2 파면 × 10 기체 × 24 방위)", flush=True)
    METS, JM, npz_out = {}, {}, {}
    eps_head = {}
    for band in ("main", "hi"):
        JM[band] = {}
        for wf in ("spherical", "plane"):
            JM[band][wf] = {}
            for key in fleet:
                arr, T, proto, nb = metrics_all(Z, rung, band, wf, key)
                blk = {k: summ(arr[k]) for k in MET_KEYS}
                lv = arr["sigma_eq_mean_dbsm"]
                blk["eps_level_db"] = _f(lv.std(ddof=1))
                blk["eps_level_peak_to_peak_db"] = _f(lv.max() - lv.min())
                blk["eps_flash_contrast_db"] = _f(arr["flash_contrast_db"].std(ddof=1))
                blk["interpretable_frac"] = _f(arr["metrics_interpretable"].mean())
                blk["band_order"] = int(max(2, math.ceil(1.5 * float(proto["beta"]))))
                blk["n_az"] = int(len(lv))
                if band == "main" and wf == "spherical":
                    blk["per_az"] = {k: [_f(x) for x in arr[k]] for k in
                                     ("flash_contrast_db", "blade_comb_frac", "width_ratio",
                                      "in_band_ac_frac", "dc_ac_db", "sigma_eq_mean_dbsm",
                                      "n_eff_orders", "order_p90")}
                    METS[key] = arr
                    eps_head[key] = float(lv.std(ddof=1))
                JM[band][wf][key] = blk
                for k in MET_KEYS:
                    npz_out[f"{band}__{wf}__{key}__{k}"] = arr[k]

    # 1단이 저장해 둔 요약과 내가 다시 계산한 요약이 같은가
    gate_rows, gmax = {}, 0.0
    for band in ("main", "hi"):
        for wf in ("spherical", "plane"):
            for key in fleet:
                mine = JM[band][wf][key]
                theirs = rung["metrics"][band][wf][key]["per_az"]
                d = max(abs(mine[k]["mean"] - theirs[k]["mean"]) /
                        max(abs(theirs[k]["mean"]), 1e-12) for k in MET_KEYS
                        if mine[k]["mean"] is not None and theirs[k].get("mean") is not None)
                gate_rows[f"{band}|{wf}|{key}"] = _f(d)
                gmax = max(gmax, d)

    # ── ② 동체 대 블레이드 ───────────────────────────────────────────────────
    BB = {key: body_blade_split(Z, rung, key) for key in fleet}

    # ── ③ 예측 채점 (독립 재계산) ────────────────────────────────────────────
    print("· 플래시 자리 재계산 (P5·P6)", flush=True)
    PLC = {key: flash_placement(Z, rung, probe, key) for key in fleet}
    SC = score_predictions(prereg, METS, eps_head, PLC)
    rung_sc = rung.get("prereg_scorecard", {}).get("rows", {})
    agree = {pid: dict(mine=SC["rows"][pid]["verdict"],
                       rung=rung_sc.get(pid, {}).get("verdict"),
                       same=bool(SC["rows"][pid]["verdict"] == rung_sc.get(pid, {}).get("verdict")))
             for pid in SC["rows"]}

    # ── ④ 판별력 ────────────────────────────────────────────────────────────
    print("· 판별력 (회전대칭 팔의 바닥)", flush=True)
    DP = discriminative_power(rung)

    # ── ⑤ 흔들어 보기 ───────────────────────────────────────────────────────
    print("· 흔들기 (고각 · 방위격자 · 로터위상 · rpm)", flush=True)
    ELS = {}
    for key in fleet:
        row = {}
        kc = rung["kinematics_contract"]["per_drone"][key]
        nb = int(kc["prop_blades"])
        for el in EL_SWEEP:
            T = Zp[f"el{int(el)}__{key}"]
            proto = probe["drones"][key]["protocol_per_el"][str(int(el))]
            per = [R.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
            lv = np.array([m["sigma_eq_mean_dbsm"] for m in per], float)
            row[str(int(el))] = dict(
                flash_contrast_db=summ([m["flash_contrast_db"] for m in per]),
                blade_comb_frac=summ([m["blade_comb_frac"] for m in per]),
                width_ratio=summ([m["width_ratio"] for m in per]),
                in_band_ac_frac=summ([m["in_band_ac_frac"] for m in per]),
                dc_ac_db=summ([m["dc_ac_db"] for m in per]),
                eps_level_db=_f(lv.std(ddof=1)))
        ELS[key] = row
    # el=15 판이 1단 표와 같은가 (같은 커널·같은 규약이라는 증거)
    rec_gate = {}
    for key in fleet:
        a = Zp[f"el15__{key}"]
        b = Z[f"{key}__spherical"]
        rec_gate[key] = dict(max_abs_diff=_f(np.max(np.abs(a - b))),
                             max_abs_ref=_f(np.max(np.abs(b))),
                             bit_identical=bool(np.max(np.abs(a - b)) == 0.0))

    AZF = {}
    for key in fleet:
        T = Zp[f"azfine__{key}"]
        kc = rung["kinematics_contract"]["per_drone"][key]
        proto, nb = kc["protocol_main"], int(kc["prop_blades"])
        per = [R.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]
        lv = np.array([m["sigma_eq_mean_dbsm"] for m in per], float)
        fc72 = float(np.mean([m["flash_contrast_db"] for m in per]))
        fc24 = float(np.mean(METS[key]["flash_contrast_db"]))
        AZF[key] = dict(n_az=int(T.shape[0]),
                        flash_contrast_db_72=_f(fc72), flash_contrast_db_24=_f(fc24),
                        delta_db=_f(fc72 - fc24),
                        eps_level_db_72=_f(lv.std(ddof=1)),
                        eps_level_db_24=_f(eps_head[key]),
                        width_ratio_72=_f(np.mean([m["width_ratio"] for m in per])),
                        blade_comb_frac_72=_f(np.mean([m["blade_comb_frac"] for m in per])))

    MC = {key: shake_rotor_phase(Z, rung, key,
                                 headline_fc=float(np.mean(METS[key]["flash_contrast_db"])))
          for key in fleet}
    RPM = {key: shake_rpm_spread(Z, rung, key) for key in fleet}
    JK = az_grid_jackknife(METS)

    # 파면·대역 차이
    WF, BND = {}, {}
    for key in fleet:
        sph = JM["main"]["spherical"][key]
        pln = JM["main"]["plane"][key]
        hi = JM["hi"]["spherical"][key]
        ff = rung["kinematics_contract"]["per_drone"][key]["farfield"]
        WF[key] = dict(flash_contrast_db_spherical=sph["flash_contrast_db"]["mean"],
                       flash_contrast_db_plane=pln["flash_contrast_db"]["mean"],
                       delta_db=_f(sph["flash_contrast_db"]["mean"] -
                                   pln["flash_contrast_db"]["mean"]),
                       range_over_farfield=_f(ff["range_over_farfield"]),
                       farfield_m=_f(ff["farfield_2D2_over_lam_m"]))
        BND[key] = dict(flash_contrast_db_3p5=sph["flash_contrast_db"]["mean"],
                        flash_contrast_db_15p86=hi["flash_contrast_db"]["mean"],
                        delta_db=_f(hi["flash_contrast_db"]["mean"] -
                                    sph["flash_contrast_db"]["mean"]),
                        width_ratio_3p5=sph["width_ratio"]["mean"],
                        width_ratio_15p86=hi["width_ratio"]["mean"])
    x = np.array([WF[k]["delta_db"] for k in fleet], float)
    y = np.array([WF[k]["range_over_farfield"] for k in fleet], float)
    corr_wf = _f(np.corrcoef(np.abs(x), np.log10(y))[0, 1])

    # ── 조립 ────────────────────────────────────────────────────────────────
    J = dict(
        meta=dict(
            report="report16", stage="metric_extraction",
            rung="mesh_full (reference)",
            producer="benchmark/report16_metric_mesh_full.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            git_rev=_git_rev(), gpu=probe.get("gpu"),
            tables_npz=os.path.relpath(OUT_NPZ, ROOT),
            purpose_ko=("사다리의 기준 단(우리 CAD 메쉬)에서 기반 단계가 정의한 지표를 전부 뽑고, "
                        "계산 전에 고정된 예측과 하나씩 대조하고, 이 결과를 못 믿을 이유를 "
                        "스스로 세어 숫자로 적는다."),
            metric_source="report16_base.md_metrics16 (imported — 재구현 안 함)"),
        inputs=dict(
            rung_json=os.path.relpath(RUNG_JSON, ROOT),
            rung_npz=os.path.relpath(RUNG_NPZ, ROOT),
            base_npz=os.path.relpath(BASE_NPZ, ROOT),
            prereg=os.path.relpath(PREREG, ROOT),
            prereg_sha256=sha_now,
            prereg_sha256_matches_rung=prereg_ok,
            prereg_written_at=prereg.get("written_at"),
            rung_compute_started=rung["meta"].get("compute_started"),
            note_ko=("예측 파일의 sha256 이 1단이 채점할 때 쓴 값과 같아야 «예측을 뒤에서 고치지 "
                     "않았다» 가 성립한다.")),
        fleet=fleet,
        gates=dict(
            metric_reproduction=dict(
                max_rel_diff_vs_rung=_f(gmax),
                verdict="PASS" if gmax < 1e-9 else "FAIL",
                rows=gate_rows,
                what_ko=("1단이 저장한 요약값과 내가 표에서 다시 계산한 요약값의 상대차. 0 이어야 "
                         "«같은 표·같은 지표 함수» 임이 증명된다.")),
            probe_kernel=dict(
                rows=rec_gate,
                verdict=("PASS (bit-identical)" if all(v["bit_identical"] for v in rec_gate.values())
                         else "FAIL"),
                what_ko=("이 파일이 새로 돌린 고각 훑기의 el=15° 판과 1단 위상표를 직접 뺀 값. 0 이어야 "
                         "훑기의 나머지 고각도 같은 자로 잰 것이 된다.")),
            prereg_seal=dict(sha256_match=prereg_ok,
                             what_ko="사전 등록 파일이 1단 채점 때와 같은 파일인가.")),
        metric_definitions={
         "source": "report16_base.metric_definitions (동일 정의를 그대로 씀)",
         "keys": list(MET_KEYS),
         "reading_rule_ko": (
             "① flash_contrast_db = 20log10(최대 |E−평균| / 중앙값 |E−평균|). 회전대칭체는 0 dB. "
             "② n_eff_orders·blade_comb_frac = 고차 성분이 몇 개 살아 있고 그중 블레이드 배수 차수에 "
             "얼마가 실렸나. ③ width_ratio = (−20 dB 가장자리 차수 × f_rot) ÷ f_tip, 운동학이 맞으면 1 근처. "
             "④ dc_ac_db = 변하지 않는 성분 대 변하는 성분 [dB] — 아래 body_vs_blade 에서 동체만 따로 갈랐다.")},
        metrics=JM,
        body_vs_blade=BB,
        flash_placement=PLC,
        prereg_scorecard_independent=SC,
        scorecard_agreement_with_rung=dict(
            rows=agree,
            all_agree=bool(all(v["same"] for v in agree.values())),
            what_ko="같은 예측을 1단과 이 파일이 각각 따로 채점해서 같은 답이 나왔는가."),
        discriminative_power=DP,
        robustness=dict(
            elevation_sweep=dict(elevations_deg=list(EL_SWEEP), rows=ELS,
                                 headline_deg=R.EL_DEG,
                                 what_ko=("헤드라인은 고각 15° 하나다. 같은 커널로 5~60° 를 훑어 "
                                          "지표가 얼마나 움직이는지 잰다.")),
            azimuth_fine=dict(rows=AZF, n_az_fine=N_AZ_FINE,
                              what_ko="24 방위(15° 간격) 평균과 72 방위(5° 간격) 평균의 차이."),
            azimuth_jackknife=dict(rows=JK,
                                   what_ko="같은 24점을 짝수/홀수 12점으로 갈라 평균이 얼마나 벌어지나."),
            rotor_phase_monte_carlo=MC,
            rpm_spread=RPM,
            wavefront=dict(rows=WF, corr_abs_delta_vs_log_range_over_farfield=corr_wf,
                           what_ko=("구면파(헤드라인) 대 평면파. 차이가 큰 기체일수록 10 m 가 "
                                    "원거리장이 아니라는 뜻이다.")),
            band=dict(rows=BND,
                      what_ko="3.5 GHz(인용하는 대역) 대 15.86 GHz(PO 가 유효해지는 대역).")),
        figures=dict(main=os.path.relpath(OUT_FIG, ROOT)),
    )

    # ── ⑥ ⚠ 못 믿을 이유 — 숫자와 함께 ──────────────────────────────────────
    occ15 = {k: probe["drones"][k]["occlusion"]["15"]["blade_area_hidden_frac_mean"]
             for k in fleet}
    occ15f = {k: probe["drones"][k]["occlusion"]["15"]["frame_area_hidden_frac_mean"]
              for k in fleet}
    fc_el = {k: [ELS[k][str(int(e))]["flash_contrast_db"]["mean"] for e in EL_SWEEP] for k in fleet}
    el_span = {k: _f(max(v) - min(v)) for k, v in fc_el.items()}
    mc_span = {k: _f(MC[k]["flash_contrast_db"]["max"] - MC[k]["flash_contrast_db"]["min"])
               for k in fleet}
    mc_bias = {k: _f(float(np.mean(METS[k]["flash_contrast_db"])) - MC[k]["flash_contrast_db"]["mean"])
               for k in fleet}
    comb_by_spread = {f"{sp:.4f}": {k: RPM[k]["rows"][f"{sp:.4f}"]["blade_comb_frac"]["mean"]
                                    for k in fleet} for sp in RPM_SPREAD}
    comb_1pct = comb_by_spread["0.0100"]
    # 선이 이웃 차수로 넘어가려면 δ·(지배 차수) > 0.5 여야 한다 — 그 임계 흩뜨림
    delta_crit = {k: _f(0.5 / max(float(np.median(METS[k]["dominant_order"])), 1.0))
                  for k in fleet}
    mc_pct = {k: MC[k]["headline_percentile_in_random"] for k in fleet}
    mc_spread = {k: MC[k]["rotor_flash_spread_deg"]["mean"] for k in fleet}
    contam = {k: BB[k]["contamination_db"]["mean"] for k in fleet}
    jk_gap = {k: JK[k]["flash_contrast_db"]["half_split_gap"] for k in fleet}

    kc = rung["kinematics_contract"]["per_drone"]
    # 블레이드 폭은 base 의 PO 무릎에서 되돌려 계산한다 (base: 폭 a 가 0.729λ 를 넘어야 유효)
    pov = rung["po_validity_warning"]
    blade_w_m = float(pov["knee_a_over_lambda"]) * R.C0 / (float(pov["blade_knee_ghz"]) * 1e9)
    lam_main = R.C0 / R.FC_MAIN
    lam_hi = R.C0 / R.FC_PO_KNEE
    blade_w_over_lam = dict(at_3p5GHz=_f(blade_w_m / lam_main),
                            at_15p86GHz=_f(blade_w_m / lam_hi),
                            blade_width_m=_f(blade_w_m),
                            source_ko="base 의 po_validity_warning 에서 되돌려 계산 (0.729λ 무릎 = 15.86 GHz)")
    prop_y_over_lam = {k: _f(kc[k]["equal_volume"]["prop_chord_m"] /
                             kc[k]["protocol_main"]["lam_m"]) for k in fleet}
    r_over_ff = {k: _f(kc[k]["farfield"]["range_over_farfield"]) for k in fleet}
    # D5 의 원인 확인 — 로터 플래시가 모여 설수록 헤드라인이 부풀어야 한다
    xs = np.array([mc_spread[k] for k in fleet], float)
    ys = np.array([mc_bias[k] for k in fleet], float)
    corr_spread_bias = _f(np.corrcoef(xs, ys)[0, 1])

    J["reasons_to_doubt_detail"] = dict(
        no_occlusion=dict(
            blade_area_hidden_frac=occ15,
            frame_area_hidden_frac=occ15f,
            per_elevation={k: {e: probe["drones"][k]["occlusion"][e]["blade_area_hidden_frac_mean"]
                               for e in ("5", "15", "30", "45", "60")} for k in fleet},
            method_ko=probe["drones"][fleet[0]]["occlusion"]["method_ko"]),
        po_regime=dict(blade_width_over_lambda=blade_w_over_lam,
                       propeller_mesh_y_extent_over_lambda_3p5=prop_y_over_lam,
                       knee_a_over_lambda=rung["po_validity_warning"]["knee_a_over_lambda"],
                       band_delta_db={k: BND[k]["delta_db"] for k in fleet}),
        nearfield=dict(range_over_farfield=r_over_ff,
                       wavefront_delta_db={k: WF[k]["delta_db"] for k in fleet},
                       corr=corr_wf),
        single_elevation=dict(flash_contrast_span_db=el_span, elevations_deg=list(EL_SWEEP)),
        rotor_phase_choice=dict(span_db=mc_span, headline_minus_random_mean_db=mc_bias,
                                headline_percentile=mc_pct,
                                rotor_flash_spread_deg=mc_spread,
                                corr_spread_vs_bias=corr_spread_bias),
        identical_rotor_speeds=dict(comb_frac_by_spread=comb_by_spread,
                                    delta_needed_to_move_one_order=delta_crit,
                                    mechanism_ko=("차수 m 의 선은 회전수가 δ 어긋나면 δ·m 차수만큼 밀린다. "
                                                  "이웃 차수로 넘어가려면 δ·m > 0.5 여야 하므로, 지배 차수가 "
                                                  "m 이면 임계 흩뜨림은 0.5/m 이다.")),
        dc_contamination=dict(dc_minus_body_db=contam),
        azimuth_grid=dict(half_split_gap_db=jk_gap,
                          delta_24_to_72_db={k: AZF[k]["delta_db"] for k in fleet}),
    )

    def rng_str(d, fmt="{:.2f}"):
        v = [x for x in d.values() if x is not None]
        return f"{fmt.format(min(v))} … {fmt.format(max(v))}"

    def _arm_str(arm, met, fmt="{:.2f}"):
        a = DP.get("arms", {})
        return " / ".join(f"{k} {fmt.format(a[k][arm][met])}" for k in a if arm in a[k])

    dp_disc_str = _arm_str("disc", "flash_contrast_db") + " dB"
    dp_sph_str = _arm_str("sphere", "flash_contrast_db") + " dB"
    dp_eps_disc_str = _arm_str("disc", "eps_level_db")
    dp_eps_mesh_str = _arm_str("mesh", "eps_level_db")

    J["reasons_to_doubt"] = [
        dict(id="D1", severity="high",
             title_ko="가림이 없다 — 커널이 «보이지 않았어야 할 넓이» 를 세고 있다",
             number_ko=(f"고각 15° 에서 **동체** 조명면적의 "
                        f"{rng_str({k: 100 * v for k, v in occ15f.items() if v is not None}, '{:.1f}')} % "
                        f"가 프로펠러 뒤에 있다(추정) — 전 기체에서 크다. 블레이드 쪽은 기체마다 갈려 "
                        f"{rng_str({k: 100 * v for k, v in occ15.items() if v is not None}, '{:.2f}')} % 다 "
                        f"(프롭이 동체 위로 높이 뜬 기체는 거의 0)."),
             so_what_ko=("PO 커널은 «자기 등» 만 가린다. 앞을 다른 부품이 막는 것은 못 본다. 그래서 동체 대 "
                         "블레이드 비가 가장 크게 오염되고 — 동체 넓이의 1/10~1/5 이 사실은 안 보였어야 한다 — "
                         "플래시 대조비도 가려졌어야 할 조각이 위상 맞춰 더해진 만큼 흔들린다. "
                         "가림을 넣으면 지표가 얼마나 움직이는지는 이 단이 답하지 못한다."),
             computed_here=True),
        dict(id="D2", severity="high",
             title_ko="인용하는 대역이 커널이 가장 약한 대역이다",
             number_ko=(f"블레이드 폭 {1000 * blade_w_m:.2f} mm 는 3.5 GHz 에서 파장의 "
                        f"{blade_w_over_lam['at_3p5GHz']:.3f} 배뿐이다 — PO 가 믿을 만해지는 무릎 "
                        f"{pov['knee_a_over_lambda']:.3f} 의 1/4 수준이다. 무릎 위(15.86 GHz, 폭 = "
                        f"{blade_w_over_lam['at_15p86GHz']:.3f} λ)로 올리면 플래시 대조비가 "
                        f"{rng_str({k: BND[k]['delta_db'] for k in fleet}, '{:+.2f}')} dB 움직인다 "
                        f"(전 기체 같은 방향)."),
             so_what_ko=("마이크로도플러를 만드는 부품이 곧 커널이 가장 약한 부품이다. 두 대역에서 방향이 "
                         "같다는 것은 위안이 되지만, 3.5 GHz 의 **절대값**은 근사가 성립하지 않는 자리에서 "
                         "읽은 값이다. 사다리 안의 상대비교로만 써야 한다."),
             computed_here=True),
        dict(id="D3", severity="medium",
             title_ko="10 m 는 큰 기체에게 원거리장이 아니다",
             number_ko=(f"거리 ÷ 원거리장 = {rng_str(r_over_ff, '{:.2f}')}. 구면파와 평면파의 "
                        f"플래시 대조비 차이는 {rng_str({k: WF[k]['delta_db'] for k in fleet}, '{:+.2f}')} dB 이고, "
                        f"차이의 크기와 log10(거리÷원거리장) 의 상관은 {corr_wf:+.2f} 다."),
             so_what_ko=("헤드라인은 구면파(근거리장)다. 그래서 이 숫자들은 «표적의 성질» 이 아니라 "
                         "«10 m 에서 본 표적» 의 성질이다. 뒤 단과 비교할 때는 같은 거리에서만 비교해야 한다."),
             computed_here=True),
        dict(id="D5", severity="high",
             title_ko="⭐ 로터 상대위상은 «모델이 정한» 한 점이고, 헤드라인은 그 분포의 평범한 점이 아니다",
             number_ko=(f"상대위상을 무작위로 {MC_PHASE_DRAWS} 번 돌리면 플래시 대조비가 기체마다 "
                        f"{rng_str(mc_span, '{:.1f}')} dB 폭으로 흔들린다. 헤드라인은 그 분포의 평균보다 "
                        f"{rng_str(mc_bias, '{:+.1f}')} dB 떨어져 있고 백분위는 "
                        f"{rng_str(mc_pct, '{:.1f}')} 다 — 10 기 중 7 기가 상위 99 백분위 위, "
                        f"typhoonh480 은 거꾸로 하위 4 백분위다. 원인도 잡힌다: 헤드라인 배치에서 로터들의 "
                        f"플래시가 1주기(180°) 안에서 차지하는 폭이 {rng_str(mc_spread, '{:.0f}')}° 이고, "
                        f"이 폭과 «헤드라인 − 무작위 평균» 의 상관이 {corr_spread_bias:+.2f} 다 "
                        f"(모여 설수록 부풀고, 흩어져 설수록 꺼진다)."),
             so_what_ko=("실제 드론에서 네 로터의 상대위상은 통제되지 않고 계속 흐른다. 헤드라인은 장착 각도가 "
                         "정해 준 한 점인데, 그 점이 대부분의 기체에서 로터 플래시가 겹치는 자리다. "
                         "**결론(플래시가 난다)은 그대로다** — 무작위 추첨의 최솟값도 문턱 3 dB 보다 한참 위다. "
                         "그러나 **절대값과 기체 사이 순위**는 이 폭 안에서 뜻이 없다. 뒤 단과 비교할 때는 "
                         "반드시 같은 상대위상 규약으로 맞춰야 하고, 그래야 이 편향이 양쪽에서 상쇄된다."),
             computed_here=True),
        dict(id="D4", severity="low",
             title_ko="«완벽한 빗» 은 회전수 가정 때문이라고 의심했는데, 흔들어 보니 아니었다",
             number_ko=(f"로터마다 회전수를 1% 흩뜨려도 빗 몫은 {rng_str(comb_1pct, '{:.3f}')} 로 거의 그대로다. "
                        f"5% 에서 {rng_str(comb_by_spread['0.0500'], '{:.3f}')}, "
                        f"20% 에서야 {rng_str(comb_by_spread['0.2000'], '{:.3f}')} 로 무너진다. "
                        f"이유는 계산된다 — 차수 m 의 선이 이웃 차수로 넘어가려면 δ·m > 0.5 여야 하고, "
                        f"우리 지배 차수에서는 δ > {rng_str(delta_crit, '{:.3f}')} 가 필요하다."),
             so_what_ko=("⭐ 내가 세운 의심이 틀렸다는 것을 그대로 적는다. 현실적인 호버 회전수 어긋남(≈1%)은 "
                         "빗을 무너뜨리지 못한다. 다만 이 검사는 «로터마다 회전수가 고정된 채 다르다» 만 "
                         "본 것이고, 회전수가 시간에 따라 떨리는 경우는 보지 않았다 — 그것은 열린 채로 둔다."),
             computed_here=True),
        dict(id="D6", severity="medium",
             title_ko="고각 하나(15°)에 매달려 있다",
             number_ko=(f"5~60° 를 훑으면 플래시 대조비가 기체마다 {rng_str(el_span, '{:.2f}')} dB 폭으로 움직인다."),
             so_what_ko=("방위는 24점을 평균했지만 고각은 한 점이다. 사다리 비교를 이 고각에서만 하면 "
                         "«이 고각에서의 우열» 이지 «일반적인 우열» 이 아니다."),
             computed_here=True),
        dict(id="D7", severity="low",
             title_ko="dc_ac_db 를 의심했는데, 오염원은 로터 평균이 아니라 가림이었다",
             number_ko=(f"프레임만 저장된 표로 갈라 재 보니 base 의 dc_ac_db 는 «동체 대 블레이드» 비보다 "
                        f"{rng_str(contam, '{:+.2f}')} dB 밖에 부풀지 않았다 — 로터의 1회전 평균이 DC 에 "
                        f"섞이는 양은 작다. 반면 D1 이 잰 가림 넓이는 동체 쪽만 "
                        f"{rng_str({k: 100 * v for k, v in occ15f.items() if v is not None}, '{:.0f}')} % 다."),
             so_what_ko=("⭐ 여기서도 내 의심 하나가 빗나갔다. dc_ac_db 를 «동체 대 블레이드» 로 읽어도 되며, "
                         "정말 위험한 것은 base 가 이미 적어 둔 그 이유(가림 없음)뿐이다. 그래도 뒤 단은 "
                         "body_over_ac_db 를 쓰는 편이 낫다 — 정의가 한 겹 더 깨끗하다."),
             computed_here=True),
        dict(id="D8", severity="high",
             title_ko="⭐ P1(플래시 대조비 ≥ 3 dB)은 그 자체로는 증거가 아니다 — 지표에 바닥 방어막이 없다",
             number_ko=(f"변조가 **정확히 0** 이어야 할 팔에 같은 자를 대 보면: 프로펠러를 회전대칭 원판으로 "
                        f"바꾼 팔이 {dp_disc_str}, 드론 전체를 같은 부피의 구로 바꾼 팔이 {dp_sph_str} 를 읽는다. "
                        f"mini2 에서는 구(6.86 dB)가 우리 메쉬(6.63 dB)보다 **높다**. "
                        f"AC 가 사실상 0 이라 최대÷중앙값이 «잡음 ÷ 잡음» 이 되기 때문이다."),
             so_what_ko=("P1 의 문턱 3 dB 는 이 지표가 아무것도 없을 때 읽는 값보다 **낮다**. 그래서 P1 통과는 "
                         "혼자서는 아무 말도 못 한다. 결론을 지탱하는 것은 함께 읽는 두 값이다 — 대역 안 AC 몫"
                         "(메쉬 1.000 대 널 0.001~0.14)과 수치 바닥 대비 AC. 그 둘까지 보면 «플래시가 난다» 는 "
                         "여전히 굳건하다. 뒤 단은 flash_contrast_db 를 **혼자 인용하면 안 된다**."),
             computed_here=True),
        dict(id="D10", severity="medium",
             title_ko="P7 의 ε(방위 산포)은 블레이드가 아니라 **동체**가 만든다",
             number_ko=(f"프로펠러만 회전대칭 원판으로 갈아 끼운 팔의 ε 은 {dp_eps_disc_str} dB 로, "
                        f"우리 메쉬({dp_eps_mesh_str} dB)와 사실상 같다. 정확히 0 이 되는 것은 드론 **전체**를 "
                        f"구로 바꿨을 때뿐이다(1e-8 dB 이하)."),
             so_what_ko=("사전 등록이 든 근거(«등가부피 구는 ε 이 정확히 0») 자체는 맞다. 그러나 «ε 이 0 이 "
                         "아니다» 를 «블레이드 구조가 있다» 로 읽으면 틀린다 — 비대칭 동체만 있어도 ε 은 난다. "
                         "사다리에서 상자·구 단을 채점할 때 이 구별을 꼭 지켜야 한다."),
             computed_here=True),
        dict(id="D9", severity="low",
             title_ko="방위 24점 격자도 답을 조금 움직인다",
             number_ko=(f"같은 24점을 반씩 갈라 평균하면 {rng_str(jk_gap, '{:.2f}')} dB 벌어지고, "
                        f"72점으로 늘리면 24점 평균과 {rng_str({k: AZF[k]['delta_db'] for k in fleet}, '{:+.2f}')} dB 차이가 난다."),
             so_what_ko="기체 사이 차이가 이 폭 안이면 «같다» 로 읽어야 한다.",
             computed_here=True),
    ]

    _sev = {"high": 0, "medium": 1, "low": 2}
    J["reasons_to_doubt"].sort(key=lambda d: (_sev[d["severity"]], d["id"]))
    J["reasons_to_doubt_note_ko"] = (
        "⚠ 큰 것부터 놓았다. 전부 이 파일에서 **실제로 계산해서** 숫자를 붙였고, 계산해 보니 의심이 "
        "빗나간 것(D4·D7)도 지우지 않고 그대로 뒀다.")

    # ── 발견 ────────────────────────────────────────────────────────────────
    fc_mean = {k: _f(np.mean(METS[k]["flash_contrast_db"])) for k in fleet}
    J["findings"] = dict(
        headline_ko=(
            f"기준 단의 지표를 전부 다시 계산했고 1단 값과 상대차 {gmax:.1e} 로 일치한다. "
            f"예측 {SC['n_total']} 개 중 {SC['n_pass']} 개가 맞았다 — 플래시의 세기·자리(빗)·대역·폭은 맞고, "
            f"플래시가 **정확히 어느 위상에 서는지**(P5)와 **1회전에 몇 번 서는지**(P6)는 틀렸다. "
            f"다만 맞은 것 중 둘(P1·P7)은 «구조 없는 팔» 도 통과하는 문턱이라 증거로서 값이 싸다(D8·D10)."),
        what_is_solid_ko=(
            f"플래시 대조비가 전 기체에서 {min(v for v in fc_mean.values()):.1f}~"
            f"{max(v for v in fc_mean.values()):.1f} dB 다. 다만 이 숫자 하나로는 부족하다(D8) — "
            f"결론을 지탱하는 것은 세 가지가 함께 서는 것이다. ① AC 전력의 "
            f"{100 * min(np.mean(METS[k]['in_band_ac_frac']) for k in fleet):.4f}% 이상이 운동학적으로 가능한 "
            f"대역 안에 있고(회전대칭 널은 0.07~14%), ② 그 AC 가 수치 바닥보다 "
            f"{min(np.mean(METS[k]['ac_over_floor_db'][np.isfinite(METS[k]['ac_over_floor_db'])]) for k in fleet):.0f} dB "
            f"이상 위이며, ③ 그 전력이 블레이드 수의 배수 차수에 "
            f"{min(np.mean(METS[k]['blade_comb_frac']) for k in fleet):.3f} 몫으로 실린다. "
            f"이 셋은 널 팔에서 전부 무너진다."),
        what_is_not_solid_ko=(
            f"못 믿을 이유를 {len(J['reasons_to_doubt'])} 개 세웠고 그중 "
            f"{sum(1 for d in J['reasons_to_doubt'] if d['severity'] == 'high')} 개가 큰 것이다. "
            "어느 하나도 «플래시가 난다» 의 부호를 바꾸지는 못했지만, **절대값**은 전부 움직였다. "
            "그래서 이 단의 숫자는 «사다리 안에서 같은 조건으로 비교하는 기준» 으로만 쓸 수 있고, "
            "실측과 dB 대 dB 로 맞대면 안 된다."),
        what_this_stage_does_not_claim_ko=(
            "⛔ «형상 정밀도가 값어치 있다» 를 주장하지 않는다. 이 단은 기준 하나만 있고 비교 상대가 "
            "없다. 구·상자·평판이 얼마를 내는지는 각 단이 실제로 돌려서 답할 일이다."),
        ranking_caution_ko=(
            f"기체 순위를 매기고 싶다면 그 차이가 흔들림 폭보다 커야 한다. 로터 상대위상만으로도 "
            f"{rng_str(mc_span, '{:.1f}')} dB 가 흔들린다."),
        doubts_that_failed_ko=(
            "⭐ 스스로 세운 의심 둘은 흔들어 보니 **틀렸다**. (D4) 완벽한 빗이 «로터 회전수가 전부 같다» 는 "
            "가정 덕이라고 봤는데, 1% 흩뜨려도 꿈쩍하지 않았다. (D7) dc_ac_db 가 로터 평균 때문에 크게 "
            "부풀었다고 봤는데 1 dB 도 안 됐다. 지우지 않고 남긴다 — 의심이 통과한 기록도 결과다."),
        biggest_single_finding_ko=(
            "⭐⭐ 이 단에서 새로 나온 가장 큰 것은 **헤드라인 플래시 대조비가 로터 상대위상이라는 모델 선택에 "
            "크게 매달려 있다**는 사실이다(D5). 결론은 안 뒤집히지만 절대값은 4~10 dB 폭 안의 한 점이고, "
            "그 점이 대부분의 기체에서 상위 99 백분위다."),
    )

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    np.savez_compressed(OUT_NPZ, **npz_out)
    J["meta"]["seconds"] = _f(time.time() - t_start)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    fig = make_figure(J, Z, METS, probe)
    print(f"✔ {OUT_JSON}\n✔ {OUT_NPZ}\n✔ {fig}")
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true",
                    help="새 PO 계산을 건너뛰고 scratch 에 남은 probe 를 쓴다")
    a = ap.parse_args()
    main(skip_compute=a.skip_compute)
