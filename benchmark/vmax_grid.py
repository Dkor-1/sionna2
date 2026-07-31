# -*- coding: utf-8 -*-
"""vmax_grid.py — **무모호 속도 층을 두 기하 위에 올린다** (기하 × 조명원 2×3 격자)
====================================================================================================

■ 이 스크립트가 확정하는 것

    ⑴ 무모호 속도의 **바닥은 기하와 무관하다**. 모노스태틱은 바이스태틱 β=0 의 특수경우이고,
       두 값의 차이를 `fs_params` 로 직접 계산하면 0 이다. 바이스태틱은 β 가 커질수록
       완화계수 1/cos(β/2) 만큼 **관대해진다** → 우리가 발표해온 1.07 / 14.39 / 40.67 m/s 는
       **두 기하의 최악값**이다.
    ⑵ 반대로 **PRF 통제권**은 기하가 아니라 구성(A 능동 / B·C 패시브)이 정한다. 능동은
       v_max 가 **구간**이고 패시브는 **점**이다. 그 구간의 천장은 두 단이다 —
       ⓵ 3GPP 기준신호 재활용(sub-6 CSI-RS 500 Hz), ⓶ 자체 파형 설계(거리모호 맞바꿈 v·R=cλ/8).
    ⑶ 게재 대조군 LaSen(SenSys '26)을 같은 축에 올린다. 우리 법칙이 LaSen 의 베이스라인
       2.6 m/s 를 0.6 % 안에서 재현하고, LaSen 의 20.2 m/s 는 **균일표본 법칙의 전제를 바꿔서**
       얻은 값이다(비균일 압축센싱). 반증이 아니라 전제 변경이다.
    ⑷ 실기체 게재 최고속도를 9 셀 전부에 겹쳐 **무모호로 관측 가능한 속도**를 판정한다.

■ ⚠ 브리핑 문구 한 줄을 정정한다 — "이 한계는 패시브만 구속하고 능동은 자유롭다"
    절반만 참이다. **기준신호 정합필터에 머무는 한 벽은 두 구성 공통**이다
    ⟨monostatic_prior.json : priority_check.verdict_for_our_paper.must_stop_claiming[2]⟩.
    능동이 사는 것은 ⓐ 그 벽의 **위치를 고를 권리**(3.5 GHz 에서 10.7 m/s 천장, 패시브 1.07 의 10배)와
    ⓑ **전 파형 레인**(데이터 심볼)의 무료 이용권이다. 그리고 ⓑ 는 트래픽에 종속된다.
    §5 `corrections_to_the_brief` 가 이 정정을 수치와 함께 싣는다.

■ 계산하지 않고 **저장소 함수를 부른다**(재구현 금지)
    freespace_scene.fs_params / target_pos / heading_velocity / folded_doppler / nyquist_gate
    freespace_scene.prf_hz / M_from_prf / doppler_bin_hz / cpi_feasibility / blind_fractions
    waveforms.{wifi_80211ac, lte_downlink, nr_downlink}         (λ·대역·기준신호 길이 단일 진리원)
    drones.DRONES                                               (기체 최고속도 단일 진리원)
    outputs/{refrate_law, vmax_hardening, monostatic_prior, geometry_grid, report13_freespace}.json

■ 산출
    outputs/vmax_grid.json
    outputs/figures/vmax_grid_f{1,2,3}_*.{png,pdf}              (그림 텍스트 전부 영어)

실행:  cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/vmax_grid.py
       빠른 확인:  --smoke   (그림 생략)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                              # noqa: E402

import freespace_scene as FS                                    # noqa: E402
import waveforms as WF                                          # noqa: E402
import drones as DR                                             # noqa: E402

C0 = FS.C0
OUT_JSON = os.path.join(_ROOT, "outputs", "vmax_grid.json")
OUT_FIG = os.path.join(_ROOT, "outputs", "figures")

# --------------------------------------------------------------------------- #
#  0. 규약 상수 — 전부 저장소에서 읽는다 (geometry_grid.py 와 같은 값을 쓴다)
# --------------------------------------------------------------------------- #
BANDS = ("wifi", "lte", "nr")
BAND_LABEL = {"wifi": "WiFi 802.11ac", "lte": "LTE Rel-9", "nr": "5G NR Rel-16"}
MODE_G1 = "G1"                                    # 상시(always-on) 점유 모드 = 정본

ALT = FS.FS_ALT[0]                                # 60 m
TX_NODE = FS.FS_TX                                # (0,0,25) 조명원 마스트
MONO_NODE = TX_NODE                               # 구성 A 의 송수신 공용 노드
L_B, L_C = 10.0, FS.L_REF                         # 병설(10 m) · 헤드라인 바이스태틱(500 m)
D_REF = 1000.0                                    # 기준 셀(모든 리포트가 인용해온 거리)
PHI_HEAD = FS.PHI_HEADLINE_DEG                    # 90° — ⚠ 특이 방위(함정 T1b)

D_GRID = np.geomspace(150.0, 20000.0, 48)         # 장면 거리격자
PHI_GRID = np.arange(0.0, 360.0, 15.0)            # ⭐ φ 를 쓴다 — φ=90° 한 점에 머물지 않는다
PSI_GRID = np.linspace(0.0, 360.0, 721)[:-1]      # 헤딩격자(720)
T_CPI = (FS.T_CPI_REF_S, 1.0)                     # 0.1 s(헤드라인) · 1.0 s(긴 CPI)

#: 구성 정의 — geometry_grid.json 의 A/B/C 와 같은 뜻이고 같은 cell_id 를 쓴다.
CFG = {
    "A": dict(name="능동 모노스태틱", geometry_row="monostatic", L=0.0,
              tx=MONO_NODE, rx=MONO_NODE, prf_control="설계변수(천장 두 단 안에서)"),
    "B": dict(name="패시브 준모노스태틱", geometry_row="monostatic", L=L_B,
              tx=TX_NODE, rx=FS.FS_RX(L_B), prf_control="없음 — 망이 정한 상시 반복률"),
    "C": dict(name="패시브 바이스태틱", geometry_row="bistatic", L=L_C,
              tx=TX_NODE, rx=FS.FS_RX(L_C), prf_control="없음 — 망이 정한 상시 반복률"),
}


def _wf(std):
    """표준 → G1(상시) 파형 객체. 반송파·대역·기준신호 길이의 단일 진리원."""
    return {"wifi": WF.wifi_80211ac, "lte": WF.lte_downlink,
            "nr": WF.nr_downlink}[std](occupancy=MODE_G1)


def _read(rel, *keys, default=None):
    """outputs/<rel> 에서 점표기 키를 읽는다. 없으면 default (제자리 날조 금지)."""
    p = os.path.join(_ROOT, "outputs", rel)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    for k in keys:
        cur = d
        try:
            for part in k.split("."):
                cur = cur[part] if isinstance(cur, dict) else cur[int(part)]
            return cur
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return default


def _sane(o):
    """numpy 스칼라/배열을 JSON 직렬화 가능한 파이썬 값으로."""
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return [_sane(x) for x in o.tolist()]
    if isinstance(o, dict):
        return {str(k): _sane(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_sane(x) for x in o]
    return o


# =========================================================================== #
#  1. 바닥의 기하 무관성 — 주장하지 않고 **계산한다**
# =========================================================================== #
def floor_and_relief():
    """P1 모노 = 바이(β=0) · P2 완화계수 1/cos(β/2) · P3 장면 완화(φ 스윕 포함).

    ⭐ P1 을 두 방식으로 닫는다.
      (a) **항등**: `fs_params(TX=RX)` 로 얻은 모노 기하와 β=0 바이스태틱 닫힌형의 차 = 0.
      (b) **극한**: 베이스라인 L 을 500 → 0 m 로 줄이며 v_max 가 모노값으로 수렴함을 보인다.
          L=0 은 깨끗한 극한이다(R1=R2=R, β=0).
    ⚠ 앙각 완화 1/cos δ_el 는 **두 기하 모두** 갖는다. 두 기하의 차이는 앙각을 맞췄을 때
      정확히 1/cos(β/2) 뿐이다 — 그래서 (c) 에서 δ=0 을 강제한 β 스윕을 따로 만든다.
    """
    lam = {b: C0 / _wf(b).carrier_hz for b in BANDS}
    prf = {b: FS.prf_hz(b, MODE_G1) for b in BANDS}
    v_floor = {b: lam[b] * prf[b] / 4.0 for b in BANDS}

    # ---- (a) 항등: 같은 표적 위치에서 모노 v_max 와 바이 β=0 닫힌형 -------------- #
    tgt_ref = FS.target_pos(D_REF, PHI_HEAD, 0.0, ALT)
    identity = {}
    for b in BANDS:
        p = FS.fs_params(MONO_NODE, MONO_NODE, tgt_ref, np.zeros(3), _wf(b).carrier_hz)
        beta_m = float(p["beta"])
        A_h = float(np.hypot(*(np.asarray(p["u1"]) + np.asarray(p["u2"]))[:2]))
        v_mono_inplane = lam[b] * prf[b] / 2.0 / (2.0 * math.cos(math.radians(beta_m) / 2.0))
        v_bi_beta0 = lam[b] * prf[b] / (4.0 * math.cos(0.0) * math.cos(0.0))
        identity[b] = dict(
            beta_mono_deg=beta_m,
            v_max_mono_inplane_ms=v_mono_inplane,
            v_max_bistatic_beta0_ms=v_bi_beta0,
            abs_diff_ms=abs(v_mono_inplane - v_bi_beta0),
            el_mono_deg=float(p["el_deg"]),
            A_h_mono=A_h,
            v_max_mono_at_scene_elevation_ms=float(lam[b] * prf[b] / 2.0 / A_h),
            note="β_mono = 0 (u1 ≡ u2). 앙각을 0 으로 맞추면 두 기하의 바닥이 정확히 같다.")

    # ---- (b) 극한: L → 0 사다리 (수신기 높이 두 규약) -------------------------- #
    def _ladder(rx_of_L, tag):
        rows = []
        for L in (2000.0, 500.0, 100.0, 10.0, 1.0, 0.0):
            tgt = FS.target_pos(D_REF, PHI_HEAD, L, ALT)
            p = FS.fs_params(TX_NODE, rx_of_L(L), tgt, np.zeros(3), _wf("nr").carrier_hz)
            A_h = float(np.hypot(*(np.asarray(p["u1"]) + np.asarray(p["u2"]))[:2]))
            v_bi = lam["nr"] * prf["nr"] / 2.0 / A_h
            rows.append(dict(convention=tag, baseline_m=L, beta_deg=float(p["beta"]),
                             rx_height_m=float(np.asarray(rx_of_L(L), float)[2]),
                             el_deg=float(p["el_deg"]), v_max_nr_ms=v_bi,
                             excess_over_mono_ms=(
                                 v_bi - identity["nr"]["v_max_mono_at_scene_elevation_ms"])))
        return rows

    ladder_deployed = _ladder(lambda L: (FS.FS_RX(L) if L > 0 else MONO_NODE), "deployed_rx_3m")
    ladder_equal_h = _ladder(lambda L: (float(L), 0.0, float(MONO_NODE[2])), "equal_height_rx_25m")
    ladder_note = ("두 규약을 함께 낸다. **equal_height**(RX 를 TX 와 같은 25 m 에 둔다)는 β 가 "
                   "L→0 에서 단조로 0 에 수렴하고 v_max 가 모노값에 정확히 닿는 깨끗한 극한이다. "
                   "**deployed**(RX 3 m, 저장소 배치)는 L=1 m 에서도 β=1.26° 가 남는다 — "
                   "TX(25 m)·RX(3 m) 의 **높이차 22 m** 가 수직 베이스라인으로 남기 때문이다. "
                   "⭐ 구성 B 를 '모노와 같다'고 쓰면 안 되는 이유가 이 한 줄이다.")

    # ---- (c) δ=0 강제 β 스윕: 완화계수가 정확히 1/cos(β/2) 임을 수치로 --------- #
    beta_sweep = []
    for bdeg in (0.0, 5.0, 15.0, 30.0, 45.0, 60.0, 90.0, 120.0, 150.0):
        h = math.radians(bdeg) / 2.0
        u1 = np.array([math.cos(h), +math.sin(h), 0.0])
        u2 = np.array([math.cos(h), -math.sin(h), 0.0])
        P = np.array([0.0, 0.0, ALT])
        tx, rx = P + 1000.0 * u1, P + 1500.0 * u2          # R1≠R2 로 두어 대칭가정을 안 쓴다
        p = FS.fs_params(tx, rx, P, np.zeros(3), _wf("nr").carrier_hz)
        A_h = float(np.hypot(*(np.asarray(p["u1"]) + np.asarray(p["u2"]))[:2]))
        relief_num = 2.0 / A_h
        relief_cls = 1.0 / math.cos(math.radians(bdeg) / 2.0)
        beta_sweep.append(dict(
            beta_deg_requested=bdeg, beta_deg_from_fs_params=float(p["beta"]),
            el_deg=float(p["el_deg"]),
            relief_numeric=relief_num, relief_closed_form=relief_cls,
            rel_err=abs(relief_num - relief_cls) / relief_cls,
            v_max_nr_ms=v_floor["nr"] * relief_num,
            v_max_lte_ms=v_floor["lte"] * relief_num,
            v_max_wifi_ms=v_floor["wifi"] * relief_num))
    max_rel_err = max(r["rel_err"] for r in beta_sweep)

    # ---- (d) 장면 완화 — φ 스윕 포함(함정 T1b) ------------------------------- #
    scene = {}
    for cfg, spec in CFG.items():
        tgt = FS.target_pos(D_GRID[:, None], PHI_GRID[None, :], spec["L"], ALT)
        p = FS.fs_params(spec["tx"], spec["rx"], tgt, np.zeros(3), _wf("nr").carrier_hz)
        beta = np.asarray(p["beta"], float)
        el = np.asarray(p["el_deg"], float)
        u = np.asarray(p["u1"], float) + np.asarray(p["u2"], float)
        A_h = np.hypot(u[..., 0], u[..., 1])
        relief = 2.0 / np.maximum(A_h, 1e-12)
        rel_beta = 1.0 / np.cos(np.radians(beta) / 2.0)
        rel_el = 1.0 / np.cos(np.radians(el))
        # 닫힌형 A_h = 2cos(β/2)cos(el) 검증
        A_cls = 2.0 * np.cos(np.radians(beta) / 2.0) * np.cos(np.radians(el))
        j90 = int(np.argmin(np.abs(PHI_GRID - PHI_HEAD)))
        ok = FS.beta_gate(beta)                      # β ≤ 90° — σ 인용이 허용되는 창
        scene[cfg] = dict(
            baseline_m=spec["L"],
            beta_deg=dict(med=float(np.median(beta)), max=float(np.max(beta)),
                          p90=float(np.percentile(beta, 90))),
            el_deg=dict(med=float(np.median(el)), min=float(np.min(el))),
            relief_total=dict(med=float(np.median(relief)), max=float(np.max(relief)),
                              min=float(np.min(relief))),
            relief_beta_only=dict(med=float(np.median(rel_beta)), max=float(np.max(rel_beta))),
            relief_el_only=dict(med=float(np.median(rel_el)), max=float(np.max(rel_el))),
            relief_total_within_beta_gate=dict(
                med=float(np.median(relief[ok])), max=float(np.max(relief[ok])),
                frac_of_grid=float(np.mean(ok)),
                note=("⭐ 완화계수의 전역 최대는 표적이 거의 머리 위인 퇴화 기하에서 나온다. "
                      "인용은 β ≤ 90° 창(freespace_scene.beta_gate) 안 값으로 한다 — "
                      "그 밖은 SBR 유효범위 밖이라 σ 를 인용하지 않는 구역이다.")),
            phi90_slice=dict(relief_med=float(np.median(relief[:, j90])),
                             beta_med=float(np.median(beta[:, j90])),
                             beta_max=float(np.max(beta[:, j90]))),
            phi_sensitivity=dict(
                relief_med_phi90=float(np.median(relief[:, j90])),
                relief_med_all_phi=float(np.median(relief)),
                ratio=float(np.median(relief) / max(np.median(relief[:, j90]), 1e-12)),
                note=("⭐ 완화계수는 φ 에 약하게만 매달린다(비 %.4f). 링크버짓이 φ 에 23 dB 매달리는 것과 "
                      "대조된다 ⟨geometry_grid.json : headline⟩ — 이 층에서는 T1b 함정이 작다."
                      % float(np.median(relief) / max(np.median(relief[:, j90]), 1e-12)))),
            closed_form_check=dict(
                max_abs_err_A_h=float(np.max(np.abs(A_h - A_cls))),
                statement="|u1+u2|_h = 2 cos(β/2) cos(δ_el) — 저장소 기하와 닫힌형이 같다"),
            frac_beta_gt_45=float(np.mean(beta > 45.0)),
            frac_beta_gt_90=float(np.mean(beta > 90.0)))

    return dict(
        P1_floor_identity=dict(
            statement="모노스태틱 v_max 는 바이스태틱 β=0 의 특수경우다. 계산한 차이는 0 이다.",
            by_band=identity,
            v_floor_ms={b: float(v_floor[b]) for b in BANDS},
            lam_m={b: float(lam[b]) for b in BANDS},
            prf_ambient_hz={b: float(prf[b]) for b in BANDS},
            max_abs_diff_ms=float(max(identity[b]["abs_diff_ms"] for b in BANDS)),
            verdict="바닥은 기하와 무관하다 — 발표해온 1.07 / 14.39 / 40.67 m/s 는 **두 기하의 최악값**이다."),
        P1b_baseline_limit=dict(
            statement="L → 0 극한에서 바이스태틱 v_max 가 모노값으로 수렴한다(5G NR).",
            ladder_equal_height_rx=ladder_equal_h,
            ladder_deployed_rx=ladder_deployed,
            residual_beta_at_L1m_deg=dict(
                equal_height=ladder_equal_h[-2]["beta_deg"],
                deployed=ladder_deployed[-2]["beta_deg"]),
            note=ladder_note),
        P2_relief_curve=dict(
            statement="δ_el=0 을 강제한 β 스윕에서 완화계수는 정확히 1/cos(β/2) 다.",
            sweep=beta_sweep, max_rel_err=float(max_rel_err),
            construction=("표적을 원점에 두고 u1·u2 를 β/2 씩 벌린 뒤 R1=1000 m·R2=1500 m 로 "
                          "TX/RX 를 세웠다. R1≠R2 라 대칭가정을 쓰지 않는다."),
            verdict="바이스태틱은 β 가 커질수록 관대해진다 — 90° 에서 1.414배, 150° 에서 3.86배."),
        P3_scene_relief=dict(
            statement="장면 완화는 구성마다 다르고, φ 를 쓸어도 이 층에서는 크게 흔들리지 않는다.",
            by_configuration=scene,
            grid=dict(d_m=[float(D_GRID[0]), float(D_GRID[-1])], n_d=len(D_GRID),
                      phi_deg_step=float(PHI_GRID[1] - PHI_GRID[0]), n_phi=len(PHI_GRID),
                      alt_m=float(ALT))),
    )


# =========================================================================== #
#  2. 능동(A)의 PRF 사다리 — v_max 가 **점이 아니라 구간**이 되는 지점
# =========================================================================== #
def active_prf_tiers():
    """구성 A 가 고를 수 있는 PRF 의 두 단 천장을 밴드마다 못박는다.

    Tier 1 — 3GPP/802.11 **기준신호 재활용**. 천장은 규격이 정한다.
        nr   : sub-6 CSI-RS 500 Hz ⟨monostatic_prior.json : prf_ladder_at_3p5GHz[csirs_spec_max]⟩
        lte  : CRS 심볼단위 4000 Hz ⟨refrate_law.json : illuminators.rows.lte_crs_sym⟩
        wifi : 패킷률을 **송신자가 고른다** → 듀티 100 % 산술 상한 1/t_ref (저장소 파형 길이)
    Tier 2 — **자체 파형 설계**. 천장은 거리모호다: v_unamb·R_unamb = c·λ/8 (Skolnik).

    ⚠ Tier 1 의 **접근권**은 두 구성이 공유한다 — CSI-RS 는 패시브도 잠글 수 있다
      ⟨monostatic_prior.json : prf_ladder_at_3p5GHz[*].who_can_use = 'passive + monostatic'⟩.
      다른 것은 **값을 누가 정하느냐**다. 패시브는 망이 준 상시 기본값을 받는다.
    """
    ladder = _read("monostatic_prior.json", "prf_ladder_at_3p5GHz", default=[]) or []
    csirs = next((r for r in ladder if r.get("key") == "csirs_spec_max"), None)
    lte_sym = _read("refrate_law.json", "illuminators.rows.lte_crs_sym", default=None)
    beacon_prf = _read("refrate_law.json", "illuminators.rows.wifi_beacon.prf_hz", default=None)
    r90_key = {"wifi": "W1", "lte": "L1", "nr": "G1"}

    out = {}
    for b in BANDS:
        w = _wf(b)
        lam = C0 / w.carrier_hz
        prf_amb = FS.prf_hz(b, MODE_G1)
        t_ref = len(w.tx) / w.fs_hz                       # 기준신호 1회 길이 [s]
        prf_duty_ceiling = 1.0 / t_ref                    # 듀티 100 % 산술 상한

        if b == "nr":
            t1_prf, t1_src, t1_ver = (float(csirs["prf_hz"]) if csirs else None,
                                      "monostatic_prior.json : prf_ladder_at_3p5GHz[csirs_spec_max]",
                                      "pdf_quote (LaSen p.732 §1 citing TS 38.331)")
            t1_kind = "spec_ceiling — 3GPP 가 정한 값이지 설계자가 정하는 값이 아니다"
        elif b == "lte":
            t1_prf, t1_src, t1_ver = (float(lte_sym["prf_hz"]) if lte_sym else None,
                                      "refrate_law.json : illuminators.rows.lte_crs_sym.prf_hz",
                                      "spec_derived (TS 36.211 §6.10.1, CRS 4 symbols/subframe)")
            t1_kind = ("spec_ceiling — ⚠ 이 레버는 **수신기 쪽**이라 패시브도 그대로 쓴다"
                       "(CRS 를 서브프레임이 아니라 심볼 단위로 표본화). 능동 고유 이득 = ×1")
        else:
            t1_prf, t1_src, t1_ver = (prf_duty_ceiling,
                                      "repo arithmetic: 1 / (len(waveform.tx)/fs)",
                                      "repo_derived — ⚠ 규제 듀티/DFS 제약 UNVERIFIED")
            t1_kind = ("self_scheduled_duty_bound — WiFi 능동 센서는 자기가 AP 라 패킷률을 스스로 "
                       "정한다. 규격 천장이 아니라 **듀티 100 % 산술 한계**이고, 성격상 tier-2 에 "
                       "가깝다. 이 값을 '규격 천장'으로 인용하지 말 것")

        r90 = _read("report13_freespace.json",
                    f"ranges.mavic4pro.{r90_key[b]}.equal_psd.full_waveform_capture.by_N.1.R90_C50_m")
        prod = C0 * lam / 8.0
        out[b] = dict(
            band=b, label=BAND_LABEL[b], carrier_hz=float(w.carrier_hz), lam_m=float(lam),
            t_ref_s=float(t_ref),
            passive_point=dict(
                prf_hz=float(prf_amb), v_max_ms=float(lam * prf_amb / 4.0),
                what_sets_it=("망이 정한 상시 반복률" if b != "wifi"
                              else "AP 트래픽(패킷률) — 규격이 보장하는 값은 비콘 9.77 Hz"),
                caveat=(None if b != "wifi" else
                        "⚠ X4 — 1000 Hz 는 혼잡 AP **가정**이다. 규격 보장 상시는 비콘 9.77 Hz "
                        "→ 0.140 m/s 로 5G SSB 보다 나쁘다 ⟨refrate_law.json : illuminators.rows.wifi_beacon⟩")),
            tier1_reference_signal_reuse=dict(
                prf_hz=t1_prf, v_max_ms=(float(lam * t1_prf / 4.0) if t1_prf else None),
                gain_over_passive_x=(float(t1_prf / prf_amb) if t1_prf else None),
                gain_over_spec_guaranteed_ambient_x=(
                    float(t1_prf / float(beacon_prf)) if (b == "wifi" and t1_prf and beacon_prf)
                    else None),
                kind=t1_kind,
                source=t1_src, verification=t1_ver,
                exclusive_to_active=False,
                exclusivity_note=("접근권은 공유된다 — 다른 것은 **값을 누가 정하느냐**다. "
                                  "능동은 고르고 패시브는 받는다.")),
            tier2_free_waveform_design=dict(
                identity="v_unamb · R_unamb = c·λ/8  (거리모호 맞바꿈, Skolnik — 신규성 주장 없음)",
                v_times_R_m2_per_s=float(prod),
                v_max_at_R=dict([(f"R={int(R)}m", float(prod / R))
                                 for R in (108.0, 300.0, 1000.0, 3000.0)]),
                r90_reference_m=(float(r90) if r90 else None),
                v_max_at_r90_ms=(float(prod / r90) if r90 else None),
                prf_at_r90_hz=(float(C0 / (2.0 * r90)) if r90 else None),
                r90_source=("report13_freespace.json : ranges.mavic4pro.<mode>.equal_psd."
                            "full_waveform_capture.by_N.1.R90_C50_m"),
                r90_caveat=("⚠ 이 R90 은 **바이스태틱** 팔에서 계산된 값이다. 모노 팔 R90 은 "
                            "src/monostatic_scene.py 가 나온 뒤 재계산 대상이다 "
                            "⟨geometry_grid.json : readjudication.needs_recomputation[0]⟩"),
                scope="자체 파형을 설계하는 능동 레이더에만 해당. 3GPP 신호 재활용에는 쓸 수 없다."),
            span=dict(
                passive_to_tier1_x=(float(t1_prf / prf_amb) if t1_prf else None),
                passive_to_tier2_x=(float((prod / r90) / (lam * prf_amb / 4.0)) if r90 else None)),
            duty_ceiling_prf_hz=float(prf_duty_ceiling))
    return out


def active_sweep_curves(tiers):
    """그림용 — PRF 격자 위의 v_max 곡선과 각 구성이 실제로 서 있는 점/구간."""
    prf_grid = np.geomspace(1.0, 1e5, 400)
    curves = {}
    for b in BANDS:
        lam = tiers[b]["lam_m"]
        curves[b] = dict(prf_hz=[float(x) for x in prf_grid],
                         v_max_ms=[float(lam * x / 4.0) for x in prf_grid])
    lam_lasen = C0 / 5.8e9
    curves["lasen_5p8GHz"] = dict(
        prf_hz=[float(x) for x in prf_grid],
        v_max_ms=[float(lam_lasen * x / 4.0) for x in prf_grid],
        note="LaSen 실험 반송파 5.8 GHz — 우리 3밴드가 아니라 대조군 전용 보조선")
    return curves


# =========================================================================== #
#  3. 9 셀 — 2 기하행(모노/바이) × 3 조명원, 모노행은 A·B 로 쪼갠다
# =========================================================================== #
def build_cells(fr, tiers):
    gg = {c["cell_id"]: c for c in
          (_read("geometry_grid.json", "configurations_and_grid.cells", default=[]) or [])}
    beacon = _read("refrate_law.json", "illuminators.rows.wifi_beacon", default=None)

    cells = []
    for cfg in ("A", "B", "C"):
        spec = CFG[cfg]
        sc = fr["P3_scene_relief"]["by_configuration"][cfg]
        for b in BANDS:
            w = _wf(b)
            lam = C0 / w.carrier_hz
            prf_amb = FS.prf_hz(b, MODE_G1)
            v_floor = lam * prf_amb / 4.0
            rel_med, rel_max = sc["relief_total"]["med"], sc["relief_total"]["max"]
            cid = f"{cfg}-{b}"
            g = gg.get(cid, {})

            cell = dict(
                cell_id=cid, configuration=cfg, configuration_name=spec["name"],
                geometry_row=spec["geometry_row"], baseline_m=spec["L"],
                illuminator=BAND_LABEL[b], band=b,
                carrier_hz=float(w.carrier_hz), lam_m=float(lam),
                prf_control=spec["prf_control"],
                actor=g.get("actor"), realizable_by_us=g.get("realizable_by_us"),
                prior_occupant=g.get("prior_occupant"),
                scene_relief=dict(med=float(rel_med), max=float(rel_max),
                                  beta_deg_med=sc["beta_deg"]["med"],
                                  beta_deg_max=sc["beta_deg"]["max"]))

            if cfg == "A":                                   # 능동 — v_max 는 **구간**
                t1 = tiers[b]["tier1_reference_signal_reuse"]
                t2 = tiers[b]["tier2_free_waveform_design"]
                cell.update(
                    v_max_kind="range",
                    v_max_floor_ms=float(v_floor),
                    v_max_range_ms=dict(
                        lo_ambient_reuse=float(v_floor),
                        mid_tier1_spec_ceiling=t1["v_max_ms"],
                        hi_tier2_free_waveform_at_r90=t2["v_max_at_r90_ms"],
                        span_x_tier1=(float(t1["v_max_ms"] / v_floor) if t1["v_max_ms"] else None),
                        span_x_tier2=(float(t2["v_max_at_r90_ms"] / v_floor)
                                      if t2["v_max_at_r90_ms"] else None)),
                    v_max_basis=("PRF 가 설계변수다 — ⓵ 규격 기준신호 재활용 천장, "
                                 "⓶ 자체 파형이면 거리모호 맞바꿈 v·R = %.3g m²/s"
                                 % t2["v_times_R_m2_per_s"]),
                    prf_ref_hz=t1["prf_hz"],
                    reference_signal_at_ceiling=("sub-6 CSI-RS 500 Hz" if b == "nr" else
                                                 "LTE CRS per-symbol 4000 Hz" if b == "lte" else
                                                 "자체 패킷률(듀티 100 % 산술 상한)"),
                    interference_cost="자기간섭(SI) — 인밴드 전이중 ≳100 dB "
                                      "⟨monostatic_prior.json : monostatic_literature[barneto2019]⟩")
            else:                                            # 패시브 — v_max 는 **점**
                cell.update(
                    v_max_kind="point",
                    prf_ref_hz=float(prf_amb),
                    v_max_floor_ms=float(v_floor),
                    v_max_scene_median_ms=float(v_floor * rel_med),
                    v_max_scene_best_ms=float(v_floor * rel_max),
                    v_max_basis="망이 정한 상시 반복률 — 선택권 없음",
                    reference_signal=("5G NR SSB(기본 20 ms)" if b == "nr" else
                                      "LTE CRS(서브프레임당)" if b == "lte" else
                                      "WiFi VHT-LTF(패킷당 1회)"),
                    interference_cost=("직접파 간섭(DPI) — L=10 m 에서 요구 소거깊이가 폭발한다 "
                                       "⟨geometry_grid.json : interference_ledger⟩" if cfg == "B"
                                       else "직접파 간섭(DPI)"))
                if b == "wifi" and beacon:
                    cell["spec_guaranteed_variant"] = dict(
                        reference_signal="WiFi 비콘(유휴 AP, 100 TU)",
                        prf_hz=float(beacon["prf_hz"]), v_max_ms=float(beacon["v_max_ms"]),
                        note=("⭐ X4 — 규격이 보장하는 상시 기준으로 바꾸면 WiFi 가 5G SSB 보다 "
                              "나빠진다(0.140 vs 1.071 m/s). 1000 Hz 는 트래픽 가정이다."),
                        source="refrate_law.json : illuminators.rows.wifi_beacon")

            # geometry_grid 와의 교차검증
            if g:
                gv, cv = g.get("v_max_ms"), cell.get("v_max_floor_ms")
                if cfg != "A" and gv is not None and cv is not None:
                    cell["consistency_with_geometry_grid"] = dict(
                        their_v_max_ms=float(gv), our_v_max_floor_ms=float(cv),
                        abs_diff_ms=float(abs(gv - cv)))
                elif cfg == "A" and gv is not None:
                    cell["consistency_with_geometry_grid"] = dict(
                        their_v_max_ms=float(gv),
                        our_tier1_ms=cell["v_max_range_ms"]["mid_tier1_spec_ceiling"],
                        abs_diff_ms=(float(abs(gv - cell["v_max_range_ms"]["mid_tier1_spec_ceiling"]))
                                     if cell["v_max_range_ms"]["mid_tier1_spec_ceiling"] else None))
            cells.append(cell)
    return cells


# =========================================================================== #
#  4. 헤딩 판정 — 무모호 · 검출가능 · **둘 다**(observable)
# =========================================================================== #
def _geom_arrays(cfg, fc, d_grid=None, phi_grid=None):
    """(구성, 반송파) → 장면격자의 (u1+u2) 수평성분과 β·el."""
    spec = CFG[cfg]
    d = D_GRID if d_grid is None else np.asarray(d_grid, float)
    ph = PHI_GRID if phi_grid is None else np.asarray(phi_grid, float)
    tgt = FS.target_pos(d[:, None], ph[None, :], spec["L"], ALT)
    p = FS.fs_params(spec["tx"], spec["rx"], tgt, np.zeros(3), fc)
    u = np.asarray(p["u1"], float) + np.asarray(p["u2"], float)
    return dict(ux=u[..., 0], uy=u[..., 1], beta=np.asarray(p["beta"], float),
                el=np.asarray(p["el_deg"], float),
                A_h=np.hypot(u[..., 0], u[..., 1]))


def heading_fractions(cfg, band, speed, T_cpi, d_grid=None, phi_grid=None, prf_override=None):
    """장면격자 × 헤딩격자에서 **무모호 / 검출가능 / 둘 다**의 비율을 센다.

    · 무모호   : `nyquist_gate(f_d, PRF)`      → |f_d| < PRF/2
    · 검출가능 : |folded_doppler(f_d)| ≥ 1.5·Δf_d   (검출기가 실제로 지우는 폭)
    · observable = 둘 다 — X2/X3 정정의 실현: 접힘 ≠ 미검출, 그러나 접힌 속도는 못 믿는다.
    · `prf_override` 는 구성 A 가 **PRF 를 고른 경우**를 같은 판정기로 돌리기 위한 인자다.
    """
    w = _wf(band)
    lam = C0 / w.carrier_hz
    prf = float(prf_override) if prf_override else FS.prf_hz(band, MODE_G1)
    M = FS.M_from_prf(T_cpi, prf)
    bin_hz = FS.doppler_bin_hz(T_cpi, prf, M)
    guard = FS.DOPPLER_GUARD_HARD_BINS * bin_hz

    G = _geom_arrays(cfg, w.carrier_hz, d_grid, phi_grid)
    ps = np.radians(PSI_GRID)
    proj = G["ux"][..., None] * np.cos(ps) + G["uy"][..., None] * np.sin(ps)   # (nd,nphi,npsi)
    fd = float(speed) / lam * proj
    unamb = FS.nyquist_gate(fd, prf)
    fb = FS.folded_doppler(fd, prf)
    blind = np.abs(fb) < guard
    usable = unamb & (~blind)

    # 닫힌형 대조: frac_unamb(점) = 1 − (2/π)·arccos(min(1, v_max_pt/v))
    v_max_pt = lam * prf / 2.0 / np.maximum(G["A_h"], 1e-12)
    if float(speed) > 0:
        x = np.minimum(1.0, v_max_pt / float(speed))
        frac_cls = 1.0 - (2.0 / np.pi) * np.arccos(x)
    else:
        frac_cls = np.ones_like(v_max_pt)
    frac_num = unamb.mean(axis=-1)

    return dict(
        prf_hz=float(prf), M=int(M), doppler_bin_hz=float(bin_hz), guard_hz=float(guard),
        unambiguous_frac=float(unamb.mean()),
        detectable_frac=float(1.0 - blind.mean()),
        observable_frac=float(usable.mean()),
        blind_hard_frac=float(blind.mean()),
        v_max_point_ms=dict(med=float(np.median(v_max_pt)), min=float(np.min(v_max_pt)),
                            max=float(np.max(v_max_pt))),
        closed_form_max_abs_err=float(np.max(np.abs(frac_num - frac_cls))),
        cpi_feasible=bool(FS.cpi_feasibility(T_cpi, prf)["feasible"]))


def drone_overlay(cells, tiers):
    """⭐ 실기체 속도를 9 셀에 겹친다 — 어느 셀이 어느 속도를 무모호로 보는가."""
    # 기체 최고속도의 단일 진리원 = src/drones.py
    drones = {k: dict(max_speed_ms=v.max_speed_ms, label=getattr(v, "label", k))
              for k, v in DR.DRONES.items()}
    # docs/DRONE_SPECS.md §1 과의 대조(문서가 코드에서 갈라졌는지 확인)
    doc_row, doc_check = None, {}
    try:
        with open(os.path.join(_ROOT, "docs", "DRONE_SPECS.md"), encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("| 최고속도"):
                    doc_row = [c.strip() for c in line.strip().strip("|").split("|")][1:]
                    break
    except OSError:
        pass
    if doc_row:
        order = ("mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4")
        for name, cellstr in zip(order, doc_row):
            m = re.search(r"(\d+(?:\.\d+)?)", cellstr)
            doc_v = float(m.group(1)) if m else None
            code_v = drones.get(name, {}).get("max_speed_ms")
            doc_check[name] = dict(doc_ms=doc_v, code_ms=(float(code_v) if code_v else None),
                                   agree=bool((doc_v is None and code_v is None) or
                                              (doc_v is not None and code_v is not None
                                               and abs(doc_v - float(code_v)) < 1e-9)))

    speeds = {"hover": 0.0, "scene_slow": 5.0, "scene_fast": 15.0}
    for k, v in drones.items():
        if v["max_speed_ms"]:
            speeds[f"{k}_max"] = float(v["max_speed_ms"])
    speed_items = sorted(speeds.items(), key=lambda kv: kv[1])

    rows = {}
    for c in cells:
        cid, cfg, b = c["cell_id"], c["configuration"], c["band"]
        per_speed = {}
        for name, v in speed_items:
            entry, entry_ref = {}, {}
            for T in T_CPI:
                entry[f"T{T:g}s"] = heading_fractions(cfg, b, v, T)
                entry_ref[f"T{T:g}s"] = heading_fractions(cfg, b, v, T,
                                                          d_grid=[D_REF], phi_grid=[PHI_HEAD])
            f01 = entry[f"T{T_CPI[0]:g}s"]
            # 판정 — 무모호 상한과 비교
            if cfg == "A":
                ceil = c["v_max_range_ms"]["mid_tier1_spec_ceiling"] or c["v_max_floor_ms"]
                ceil_hi = c["v_max_range_ms"]["hi_tier2_free_waveform_at_r90"]
            else:
                ceil, ceil_hi = c["v_max_scene_median_ms"], None
            if v == 0.0:
                verdict = "무모호(자명) · 그러나 f_d=0 이라 0-도플러 가드가 지운다 — 검출 없음"
            elif f01["unambiguous_frac"] >= 0.999:
                verdict = "전 헤딩 무모호"
            elif f01["unambiguous_frac"] <= 0.001:
                verdict = "전 헤딩 접힘 — 속도를 믿을 수 없다"
            else:
                verdict = "일부 헤딩만 무모호 (%.1f %%)" % (100.0 * f01["unambiguous_frac"])
            per_speed[name] = dict(
                speed_ms=v, verdict=verdict,
                unambiguous_frac_T0p1=f01["unambiguous_frac"],
                observable_frac_T0p1=f01["observable_frac"],
                observable_frac_T1p0=entry[f"T{T_CPI[1]:g}s"]["observable_frac"],
                reference_point_unambiguous_frac_T0p1=entry_ref[f"T{T_CPI[0]:g}s"]["unambiguous_frac"],
                reference_point_observable_frac_T0p1=entry_ref[f"T{T_CPI[0]:g}s"]["observable_frac"],
                detail=dict(scene_grid=entry, reference_point=entry_ref),
                vs_ceiling=dict(cell_v_max_ms=(float(ceil) if ceil else None),
                                ratio_speed_over_vmax=(float(v / ceil) if ceil else None),
                                tier2_v_max_ms=(float(ceil_hi) if ceil_hi else None)))
        # 셀 요약: 전 헤딩 무모호인 최대 속도(장면 최악점 기준)
        v_all_head = min(heading_fractions(cfg, b, 1.0, T_CPI[0])["v_max_point_ms"]["min"], 1e9)
        rows[cid] = dict(
            cell_id=cid, configuration=cfg, band=b, geometry_row=c["geometry_row"],
            v_max_all_headings_ms=float(v_all_head),
            by_speed=per_speed,
            drones_fully_unambiguous=[n for n, v in speed_items
                                      if n.endswith("_max") and v <= v_all_head],
            drones_aliasing=[n for n, v in speed_items
                             if n.endswith("_max") and v > v_all_head])
    # ---- ⭐ 구성 A 가 **PRF 를 고른 경우** — 같은 판정기, 반복률만 tier-1 로 --------- #
    a_ceiling = {}
    for b in BANDS:
        t1 = tiers[b]["tier1_reference_signal_reuse"]
        if not t1["prf_hz"]:
            continue
        per = {}
        for name, v in speed_items:
            f01 = heading_fractions("A", b, v, T_CPI[0], prf_override=t1["prf_hz"])
            f10 = heading_fractions("A", b, v, T_CPI[1], prf_override=t1["prf_hz"])
            amb = rows[f"A-{b}"]["by_speed"][name]
            per[name] = dict(speed_ms=v,
                             unambiguous_frac_T0p1=f01["unambiguous_frac"],
                             observable_frac_T0p1=f01["observable_frac"],
                             observable_frac_T1p0=f10["observable_frac"],
                             gain_over_ambient_observable_x=(
                                 float(f01["observable_frac"] / amb["observable_frac_T0p1"])
                                 if amb["observable_frac_T0p1"] > 0 else None))
        a_ceiling[f"A-{b}@tier1"] = dict(
            cell_id=f"A-{b}@tier1", configuration="A", band=b, geometry_row="monostatic",
            prf_hz=t1["prf_hz"], v_max_ms=t1["v_max_ms"], kind=t1["kind"], by_speed=per)

    # ---- 게재값 대조: vmax_hardening E5 는 C 구성의 기준점(d=1000·φ=90)에서 계산됐다 ---- #
    e5 = _read("vmax_hardening.json", "E_long_cpi.E5_usable_heading_fraction", default={}) or {}
    mode_of = {"wifi": "W1", "lte": "L1", "nr": "G1"}
    xcheck, worst = [], 0.0
    for b in BANDS:
        for T, tag in ((0.1, "T0.1"), (1.0, "T1")):
            blk = e5.get(f"{mode_of[b]}_{tag}")
            if not blk:
                continue
            for row in blk["by_speed"]:
                v = float(row["v_ms"])
                ours = heading_fractions("C", b, v, T, d_grid=[D_REF], phi_grid=[PHI_HEAD])
                du = abs(ours["unambiguous_frac"] - row["unambiguous_frac"])
                do = abs(ours["observable_frac"] - row["detectable_and_unambiguous_frac"])
                worst = max(worst, du, do)
                xcheck.append(dict(cell=f"C-{b}", T_cpi_s=T, v_ms=v,
                                   theirs_unambiguous=row["unambiguous_frac"],
                                   ours_unambiguous=ours["unambiguous_frac"],
                                   theirs_observable=row["detectable_and_unambiguous_frac"],
                                   ours_observable=ours["observable_frac"],
                                   max_abs_diff=float(max(du, do))))

    return dict(
        speed_axis=dict(items=dict(speed_items),
                        source=("src/drones.py : DRONES[*].max_speed_ms (단일 진리원) · "
                                "src/freespace_scene.py : FS_SPEED (장면속도 5/15 m/s)")),
        cross_check_vs_vmax_hardening_E5=dict(
            what=("E5 는 구성 C 의 기준점(L=500 · d=1000 · φ=90 · alt=60)에서 계산된 게재값이다. "
                  "같은 점에서 우리 일반화 판정기가 같은 답을 내는지 전수 대조했다."),
            n_rows=len(xcheck), max_abs_diff=float(worst), rows=xcheck,
            source="vmax_hardening.json : E_long_cpi.E5_usable_heading_fraction"),
        drone_specs_md_parity=dict(
            checked=doc_check,
            all_agree=bool(doc_check) and all(v["agree"] for v in doc_check.values()),
            note="docs/DRONE_SPECS.md §1 '최고속도' 행과 src/drones.py 를 대조했다."),
        airframes=drones,
        by_cell=rows,
        configuration_A_at_its_ceiling=dict(
            what=("⭐ 같은 기하·같은 판정기에서 **반복률만** tier-1 천장으로 올린 결과. "
                  "기하가 아니라 통제가 무엇을 사는지 이 표가 직접 보여준다."),
            by_cell=a_ceiling),
        convention=("무모호 = |f_d| < PRF/2 · 검출가능 = |folded f_d| ≥ 1.5·Δf_d(검출기 실효 가드) · "
                    "observable = 둘 다. 격자는 d 48 × φ 24 × ψ 720."))


# =========================================================================== #
#  5. LaSen 을 같은 축에 올린다 (게재 대조군)
# =========================================================================== #
def lasen_on_our_axis():
    """LaSen(SenSys '26)의 반복률과 v_max 를 우리 축 v_max = λ·PRF/4 위에 놓는다.

    ⚠ 논문이 보고하지 않은 값은 **UNVERIFIED** 로 표시하고 만들어내지 않는다.
    """
    mp_id = _read("monostatic_prior.json", "lasen.identity", default={}) or {}
    ver = _read("monostatic_prior.json",
                "verification_of_our_law_against_prior_measurements", default={}) or {}
    vel = _read("monostatic_prior.json", "lasen.velocity_claim", default={}) or {}
    rates = _read("monostatic_prior.json", "lasen.repetition_rates_the_paper_states",
                  default={}) or {}
    traffic = _read("monostatic_prior.json", "lasen.traffic_statistics_measured", default={}) or {}
    scope = _read("monostatic_prior.json", "lasen.scoping_caveat_that_must_be_stated_when_citing")

    fc_lasen = 5.8e9                                   # 논문 실험 반송파(비면허 5.8 GHz)
    lam_lasen = C0 / fc_lasen
    lam_nr = C0 / _wf("nr").carrier_hz

    lanes = []
    # ⓵ 기준신호 전용 베이스라인 — 논문이 스스로 이긴다고 적은 값
    prf_base = float(ver.get("lasen_csirs_baseline", {}).get("inputs", {}).get("prf_hz", 200.0))
    v_base = lam_lasen * prf_base / 4.0
    lanes.append(dict(
        lane="reference-signal only (CSI-RS) — the baseline LaSen beats",
        prf_ref_hz=prf_base, carrier_hz=fc_lasen, lam_m=float(lam_lasen),
        our_law_v_max_ms=float(v_base),
        paper_states_ms=ver.get("lasen_csirs_baseline", {}).get("paper_states_ms"),
        rel_err=ver.get("lasen_csirs_baseline", {}).get("rel_err"),
        status="VERIFIED — 우리 법칙이 논문 숫자를 0.6 % 안에서 재현한다",
        source="monostatic_prior.json : verification_of_our_law_against_prior_measurements"
               ".lasen_csirs_baseline"))
    # ⓶ 데이터심볼 만재 이상치
    full = ver.get("lasen_full_load_ceiling", {})
    lanes.append(dict(
        lane="data-symbol aided, full-buffer ideal",
        prf_ref_hz=full.get("slow_time_rate_hz"), carrier_hz=fc_lasen, lam_m=float(lam_lasen),
        our_law_v_max_ms=full.get("vmax_at_5p8GHz_ms"),
        paper_states_hz=full.get("paper_states_hz"),
        status="VERIFIED (논문 §3.1.2 의 ±14 kHz 와 산술 일치)",
        caveat="만재 가정. 실제 상용망 트래픽에서는 성립하지 않는다 — 아래 measured 레인 참조.",
        source="monostatic_prior.json : ...lasen_full_load_ceiling"))
    # ⓷ 실제로 시연한 값 — 여기서 등가 균일 PRF 를 역산한다
    v_demo = float(vel.get("headline_ms", 20.2))
    prf_equiv = 4.0 * v_demo / lam_lasen
    lanes.append(dict(
        lane="data-symbol aided, as demonstrated (non-uniform sub-Nyquist)",
        prf_ref_hz=None,
        equivalent_uniform_prf_hz=float(prf_equiv),
        equivalent_prf_derivation="PRF_equiv = 4·v/λ 를 시연 속도 20.2 m/s·5.8 GHz 에 적용",
        carrier_hz=fc_lasen, lam_m=float(lam_lasen),
        demonstrated_v_ms=v_demo,
        status=("⚠ 20.2 m/s 는 **무모호 상한이 아니다** — 기체(Matrice 4E, 21 m/s)가 만든 실험 경계다. "
                "논문 자신이 '최대 속도 감지범위를 측정하지 않았다'고 적는다."),
        unverified=["LaSen 의 실제 무모호 속도 상한 (측정되지 않음)",
                    "비균일 표본에서의 등가 반복률 (논문이 PRF 를 정의하지 않는다)"],
        why_it_does_not_falsify_our_law=vel.get("why_this_matters_to_us"),
        accuracy_at_top_bin=vel.get("accuracy_at_the_top_bin"),
        source="monostatic_prior.json : lasen.velocity_claim"))

    # 우리 격자(A-nr, 3.5 GHz)로 옮겨 놓기
    on_our_grid = dict(
        cell_id="A-nr",
        carrier_hz=float(_wf("nr").carrier_hz), lam_m=float(lam_nr),
        csirs_measured_N41=dict(prf_hz=rates.get("nr_csirs_measured_hz"),
                                v_max_ms=(float(lam_nr * rates["nr_csirs_measured_hz"] / 4.0)
                                          if rates.get("nr_csirs_measured_hz") else None),
                                note="LaSen 이 상용 China Mobile N41 에서 실측한 CSI-RS 반복률"),
        csirs_spec_max=dict(prf_hz=rates.get("nr_csirs_max_configurable_hz"),
                            v_max_ms=(float(lam_nr * rates["nr_csirs_max_configurable_hz"] / 4.0)
                                      if rates.get("nr_csirs_max_configurable_hz") else None),
                            note="규격 천장 — A-nr 셀의 tier-1 값과 같아야 한다"),
        ssb=dict(prf_hz=rates.get("nr_ssb_hz"),
                 v_max_ms=(float(lam_nr * rates["nr_ssb_hz"] / 4.0)
                           if rates.get("nr_ssb_hz") else None),
                 note="LaSen 도 우리와 같은 50 Hz 를 인용한다 — 독립 확인"),
        carrier_mismatch=("⚠ LaSen 실험은 5.8 GHz 비면허대역의 자체 USRP 송신이다. 상용 gNB(3.5 GHz)로 "
                          "드론을 잰 적이 없다 — 같은 축에 올릴 때 λ 를 반드시 밝힌다."))

    return dict(
        identity=dict(title=mp_id.get("title"), venue=mp_id.get("venue"),
                      pages=mp_id.get("pages"), doi=mp_id.get("doi"),
                      year=mp_id.get("year"), status=mp_id.get("publication_status"),
                      citation=mp_id.get("citation_line")),
        geometry="MONOSTATIC ⟨monostatic_prior.json : lasen.geometry.answer⟩",
        signal_reused="PDSCH 데이터 심볼 + 기준신호(CSI-RS·DMRS 계열) — 송신자라 X[m,n] 를 안다",
        grid_cell="A-nr (능동 모노스태틱 × 5G NR)",
        lanes=lanes,
        on_our_grid=on_our_grid,
        traffic_dependence=dict(
            dense_segment_fraction=traffic.get("dense_segment_fraction"),
            quote=traffic.get("quote_2"),
            why_it_matters=("⭐ 데이터심볼 탈출구는 트래픽에 종속된다 — 실측 상용 gNB 는 시간의 95 % 를 "
                            "RE 점유율 7.1 % 아래에서 보낸다. 우리 X4 정정(WiFi 1 kHz 는 트래픽 가정)의 "
                            "셀룰러 대응물이고 방향이 같다.")),
        scoping_caveat=scope,
        unverified_ledger=[
            "LaSen 의 무모호 속도 상한 — 측정하지 않았다고 논문이 명시",
            "LaSen 의 TX-RX 격리도 — 측정치 없음(>50 dB 는 Barneto 인용)",
            "상용 gNB 신호로 드론을 잰 결과 — 없음(자체 USRP 5.8 GHz 만재 송신)",
            "3GPP TS 38.331 의 CSI-RS 최소주기 원문 확인 — 2차 인용뿐 "
            "⟨monostatic_prior.json : gaps_this_round_did_not_close[2]⟩"],
        what_this_cell_gives_us=("게재된 대조군이 격자의 한 칸에 앉는다. 우리 법칙이 그 논문의 "
                                 "베이스라인을 재현하고, 그 논문이 벽을 넘은 방법(비균일 압축센싱)이 "
                                 "**법칙의 전제를 바꾼 것**임을 같은 축 위에서 보여준다."))


# =========================================================================== #
#  6. 검증 · 브리핑 정정 · 함정
# =========================================================================== #
def verifications():
    """저장소 함수와의 패리티 — 우리가 새로 쓴 판정 코드가 정본과 같은 답을 내는가."""
    band, cfg, T, v = "nr", "C", T_CPI[0], 15.0
    lam = C0 / _wf(band).carrier_hz
    prf = FS.prf_hz(band, MODE_G1)
    M = FS.M_from_prf(T, prf)
    ref = FS.blind_fractions(PSI_GRID, PHI_HEAD, D_REF, L_C, ALT, T, prf, v, lam, M=M)
    ours = heading_fractions(cfg, band, v, T, d_grid=[D_REF], phi_grid=[PHI_HEAD])
    parity = dict(
        case=f"cfg=C · band=nr · d={D_REF} m · phi={PHI_HEAD}° · v={v} m/s · T={T} s",
        repo_blind_hard=float(ref["blind_hard"]), ours_blind_hard=float(ours["blind_hard_frac"]),
        repo_alias_frac=float(ref["alias_frac"]),
        ours_alias_frac=float(1.0 - ours["unambiguous_frac"]),
        max_abs_diff=float(max(abs(ref["blind_hard"] - ours["blind_hard_frac"]),
                               abs(ref["alias_frac"] - (1.0 - ours["unambiguous_frac"])))),
        note=("freespace_scene.blind_fractions 는 TX/RX 가 하드코딩(FS_TX·FS_RX(L))이라 "
              "**모노 팔을 표현할 수 없다**. 그래서 일반화한 판정기를 여기 두고 바이스태틱 "
              "기준셀에서 정본과 대조했다."))

    # 닫힌형 대조(전 셀)
    cf = []
    for cfg2 in CFG:
        for b in BANDS:
            r = heading_fractions(cfg2, b, 15.0, T_CPI[0])
            cf.append(dict(cell=f"{cfg2}-{b}", closed_form_max_abs_err=r["closed_form_max_abs_err"]))
    return dict(
        V1_repo_parity=parity,
        V2_closed_form_heading_fraction=dict(
            form="frac_unambiguous(ψ) = 1 − (2/π)·arccos(min(1, v_max_pt / v))",
            by_cell=cf,
            max_over_cells=float(max(x["closed_form_max_abs_err"] for x in cf)),
            note="잔차는 ψ 격자(720점) 양자화다 — 1/720 = 1.39e-03 규모."),
    )


def corrections_and_traps(tiers, cells):
    lam_nr = C0 / _wf("nr").carrier_hz
    t1_nr = tiers["nr"]["tier1_reference_signal_reuse"]
    v_pass_nr = tiers["nr"]["passive_point"]["v_max_ms"]
    fastest = max(v.max_speed_ms for v in DR.DRONES.values() if v.max_speed_ms)
    slowest = min(v.max_speed_ms for v in DR.DRONES.values() if v.max_speed_ms)

    corrections = [
        dict(
            brief_sentence="이 한계는 패시브에만 구속으로 작용하고 능동은 자유롭다",
            status="절반만 참 — 정정 필요",
            correct_sentence=("기준신호 정합필터에 머무는 한 v_max = λ·PRF_ref/4 는 **두 구성 공통**이다. "
                              "능동이 사는 것은 그 벽의 **위치를 고를 권리**이고, 그 권리에도 규격 천장이 있다."),
            numbers=dict(passive_nr_ms=float(v_pass_nr), active_tier1_nr_ms=t1_nr["v_max_ms"],
                         gain_x=t1_nr["gain_over_passive_x"],
                         covers_slowest_airframe=bool((t1_nr["v_max_ms"] or 0) >= slowest),
                         covers_scene_slow_5ms=bool((t1_nr["v_max_ms"] or 0) >= 5.0)),
            evidence="monostatic_prior.json : priority_check.verdict_for_our_paper.must_stop_claiming[2]",
            consequence=("⭐ 3.5 GHz 에서 능동의 규격 천장 10.71 m/s 는 장면속도 5 m/s 를 덮지만 "
                         "15 m/s 도, 어떤 기체의 게재 최고속도(13.5~25 m/s)도 못 덮는다. "
                         "벽을 진짜로 넘는 것은 반복률이 아니라 **전 파형(데이터 심볼)** 이다.")),
        dict(
            brief_sentence="'13.7 dB 상반성 위반' 때문에 바이스태틱이 β≤45° 로 제한된다",
            status="이미 geometry_grid 가 정정했다 — 여기서는 인용만 한다",
            correct_sentence=("13.719 dB 는 한 셀의 **이등분선 근사** p95 다. 상반성 rms 최대는 5.80 dB"
                              "(β=90° 최악 8.24 dB)이고 근사오차 p95 최대는 20.04 dB 다."),
            evidence="geometry_grid.json : readjudication.established_for_one_geometry_only[0]"),
        dict(
            brief_sentence="WiFi 는 1 kHz 라 14.4 m/s 를 준다",
            status="조건절 필수(X4)",
            correct_sentence=("1000 Hz 는 혼잡 AP **트래픽 가정**이다. 규격이 보장하는 상시 기준은 "
                              "비콘 9.77 Hz 이고 그때 0.140 m/s 로 5G SSB(1.071)보다 나쁘다."),
            evidence="vmax_hardening.json : H_symmetry · refrate_law.json : illuminators.rows.wifi_beacon"),
    ]

    traps = [
        dict(id="T-v1", trap="모노스태틱 행을 하나로 그린다",
             why_wrong="A(능동)와 B(패시브 준모노)는 기하가 같고 **통제 자유도가 다르다**. "
                       "그 차이가 이 층의 전부다 — A 는 구간, B 는 점이다.",
             guard="cell_id 를 A-/B-/C- 로 유지하고 v_max_kind(range/point)를 항상 함께 쓴다"),
        dict(id="T-v2", trap="'바이스태틱이라서 v_max 가 낮다'",
             why_wrong="반대다. 바이스태틱은 β 가 커질수록 **관대**하다(β=90° 에서 1.414배). "
                       "우리가 인용해온 값은 두 기하의 최악값이다.",
             guard="P1/P2 의 계산값을 인용한다"),
        dict(id="T-v3", trap="완화계수를 링크버짓 이득처럼 읽는다",
             why_wrong="완화가 큰 곳은 이등분선이 수직에 가까운 곳이고, 같은 곳에서 |f_d| 가 줄어 "
                       "0-도플러 가드에 더 잘 걸린다 — 공짜가 아니다.",
             guard="observable_frac(무모호 ∧ 검출가능)을 함께 보고한다 "
                   "⟨vmax_hardening.json : A_formula.coupling_warning⟩"),
        dict(id="T-v4", trap="접힘을 미검출로 읽는다(X3)",
             why_wrong="접힌 표적도 **틀린 도플러 셀에서 검출된다**. 잃는 것은 속도의 신뢰성이다.",
             guard="unambiguous_frac 과 detectable_frac 을 절대 합치지 않는다"),
        dict(id="T-v5", trap="호버를 '무모호라서 좋다'고 읽는다",
             why_wrong="v=0 은 모호가 없지만 f_d=0 이라 0-도플러 가드가 지운다 — 모든 조명원에서 블라인드다.",
             guard="by_speed.hover 의 verdict 문장을 그대로 쓴다"),
        dict(id="T-v6", trap="tier-2(자체 파형) 값을 셀 값처럼 인용한다",
             why_wrong="v·R=cλ/8 은 **자체 파형 설계자**의 것이다. 3GPP 신호를 재활용하는 주체에게는 "
                       "그 레인이 없다. 그리고 그 값은 R_unamb 를 함께 적어야 뜻이 있다.",
             guard="tier2 는 항상 (v_max, R_unamb) 쌍으로 인용한다"),
        dict(id="T-v7", trap="LaSen 의 20.2 m/s 를 '모노스태틱 무모호 상한'으로 인용한다",
             why_wrong="논문 자신이 상한을 측정하지 않았다고 적는다. 20.2 는 기체 최고속도(21 m/s)가 "
                       "만든 실험 경계다. 게다가 5.8 GHz 실험이라 λ 가 우리 5G 셀과 다르다.",
             guard="lasen.lanes[2].status 와 unverified 를 함께 인용한다"),
        dict(id="T-v8", trap="φ=90° 결과를 기하 비교에 그대로 쓴다(T1b 상속)",
             why_wrong="φ=90° 는 R₁≈R₂ 인 특이 방위다. 링크버짓은 φ 에 23 dB 매달린다.",
             guard="이 층은 φ 를 24 방위로 쓸었다 — P3_scene_relief.phi_sensitivity 가 그 크기를 준다"),
    ]

    return dict(corrections_to_the_brief=corrections, traps=traps,
                qualifications_carried_forward=_read(
                    "vmax_hardening.json", "verdict.corrections_required", default=[]))


# =========================================================================== #
#  7. 그림 — 텍스트 전부 영어
# =========================================================================== #
def make_figures(fr, tiers, curves, cells, overlay, lasen):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10.5, "axes.labelsize": 9.5,
                         "legend.fontsize": 8, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                         "figure.dpi": 110, "savefig.dpi": 300, "pdf.fonttype": 42,
                         "axes.grid": True, "grid.alpha": 0.22, "grid.linewidth": 0.5,
                         "axes.spines.top": False, "axes.spines.right": False})
    os.makedirs(OUT_FIG, exist_ok=True)
    figs = {}

    def save(fig, stem, caption):
        png, pdf = os.path.join(OUT_FIG, stem + ".png"), os.path.join(OUT_FIG, stem + ".pdf")
        fig.savefig(png, bbox_inches="tight", facecolor="white")
        fig.savefig(pdf, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        figs[stem] = dict(png=os.path.relpath(png, _ROOT), pdf=os.path.relpath(pdf, _ROOT),
                          caption=caption)

    COL = {"wifi": "#eb6834", "lte": "#2a78d6", "nr": "#1baf7a"}
    MK = {"wifi": "s", "lte": "o", "nr": "^"}
    INK, INK2 = "#0b0b0b", "#52514e"
    BL = {"wifi": "WiFi 5.21 GHz", "lte": "LTE 1.843 GHz", "nr": "5G NR 3.5 GHz"}

    # ------------------------------------------------------------------ #
    #  F1  ⭐ 핵심 그림 — 능동은 구간, 패시브는 점
    # ------------------------------------------------------------------ #
    fig, ax = plt.subplots(figsize=(8.2, 5.6))
    v_fast = max(v.max_speed_ms for v in DR.DRONES.values() if v.max_speed_ms)
    v_slow = min(v.max_speed_ms for v in DR.DRONES.values() if v.max_speed_ms)
    ax.axhspan(v_slow, v_fast, color="#2a78d6", alpha=0.07, lw=0, zorder=0)
    ax.text(1.3, math.sqrt(v_slow * v_fast),
            "published airframe maxima\n%.1f - %.0f m/s" % (v_slow, v_fast),
            fontsize=7.6, color="#1a4f8f", va="center")

    #: 겹침을 피하려고 밴드마다 라벨 위치를 손으로 고정한다(로그-로그에서 선이 평행하다)
    OFF_P = {"nr": ((10, -18), "left"), "lte": ((-8, 12), "right"), "wifi": ((0, -46), "center")}
    OFF_T = {"nr": ((-8, 16), "right"), "lte": ((-10, -22), "right"), "wifi": ((-10, 9), "right")}
    for b in BANDS:
        c = curves[b]
        ax.plot(c["prf_hz"], c["v_max_ms"], "-", color=COL[b], lw=1.3, alpha=0.85, zorder=2)
        t = tiers[b]
        p_prf, p_v = t["passive_point"]["prf_hz"], t["passive_point"]["v_max_ms"]
        ax.plot(p_prf, p_v, MK[b], ms=9, mfc=COL[b], mec="white", mew=1.2, zorder=5)
        xy, ha = OFF_P[b]
        ax.annotate("%s\n%.2f m/s" % ("passive point" if b != "wifi" else "passive (traffic)", p_v),
                    (p_prf, p_v), textcoords="offset points", xytext=xy,
                    fontsize=7.2, color=COL[b], ha=ha)
        t1 = t["tier1_reference_signal_reuse"]
        if t1["prf_hz"]:
            spec = str(t1.get("kind", "")).startswith("spec_ceiling")
            ax.annotate("", xy=(t1["prf_hz"], t1["v_max_ms"]), xytext=(p_prf, p_v),
                        arrowprops=dict(arrowstyle="-|>", color=COL[b], lw=2.4, alpha=0.9,
                                        ls=("-" if spec else (0, (4, 2)))), zorder=4)
            ax.plot(t1["prf_hz"], t1["v_max_ms"], MK[b], ms=9, mfc="white", mec=COL[b],
                    mew=1.8, zorder=5)
            xy, ha = OFF_T[b]
            ax.annotate(("tier-1 spec ceiling\n%.1f m/s" if spec else
                         "self-scheduled duty bound\n%.1f m/s (not a spec ceiling)")
                        % t1["v_max_ms"],
                        (t1["prf_hz"], t1["v_max_ms"]), textcoords="offset points",
                        xytext=xy, fontsize=7.2, color=COL[b], ha=ha)
    # 규격 보장 WiFi 비콘
    bcn = next((c for c in cells if c["cell_id"] == "C-wifi"), {}).get("spec_guaranteed_variant")
    if bcn:
        ax.plot(bcn["prf_hz"], bcn["v_max_ms"], "x", ms=8, mew=2, color=COL["wifi"], zorder=5)
        ax.annotate("WiFi beacon (spec-guaranteed)\n%.3f m/s" % bcn["v_max_ms"],
                    (bcn["prf_hz"], bcn["v_max_ms"]), textcoords="offset points",
                    xytext=(8, -4), fontsize=7.2, color=COL["wifi"])
    # LaSen
    lz = {l["lane"]: l for l in lasen["lanes"]}
    lb = lz.get("reference-signal only (CSI-RS) — the baseline LaSen beats")
    ld = lz.get("data-symbol aided, as demonstrated (non-uniform sub-Nyquist)")
    ax.plot(curves["lasen_5p8GHz"]["prf_hz"], curves["lasen_5p8GHz"]["v_max_ms"],
            "--", color=INK2, lw=1.0, alpha=0.7, zorder=1)
    if lb:
        ax.plot(lb["prf_ref_hz"], lb["our_law_v_max_ms"], "D", ms=7, mfc=INK, mec="white",
                mew=1.0, zorder=6)
        ax.annotate("LaSen baseline (CSI-RS, 5.8 GHz)\n%.2f m/s  [paper: %.1f]"
                    % (lb["our_law_v_max_ms"], lb["paper_states_ms"]),
                    (lb["prf_ref_hz"], lb["our_law_v_max_ms"]), textcoords="offset points",
                    xytext=(10, -20), fontsize=7.2, color=INK, ha="left")
    if ld:
        ax.plot(ld["equivalent_uniform_prf_hz"], ld["demonstrated_v_ms"], "*", ms=15,
                mfc="#c2185b", mec="white", mew=0.8, zorder=6)
        ax.annotate("LaSen demonstrated 20.2 m/s\n(non-uniform sub-Nyquist; equivalent\n"
                    "PRF %.0f Hz - NOT a measured ceiling)" % ld["equivalent_uniform_prf_hz"],
                    (ld["equivalent_uniform_prf_hz"], ld["demonstrated_v_ms"]),
                    textcoords="offset points", xytext=(22, -44), fontsize=7.2,
                    color="#c2185b", ha="left")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1.0, 2e5)
    ax.set_ylim(0.05, 3000.0)
    ax.set_xlabel("Reference repetition rate  PRF$_{ref}$  [Hz]")
    ax.set_ylabel("Max unambiguous radial speed  $v_{max}=\\lambda\\,$PRF$_{ref}/4$   [m/s]")
    ax.set_title("Passive gets a point, active monostatic gets a range - and the range has a ceiling")
    ax.legend(handles=[Line2D([], [], color=COL[b], marker=MK[b], ls="-", ms=8,
                              label=BL[b]) for b in BANDS]
                     + [Line2D([], [], color=INK2, ls="--", label="LaSen testbed 5.8 GHz"),
                        Line2D([], [], ls="none", marker="o", mfc="#666", mec="white",
                               ms=8, label="filled: ambient value the network gives you"),
                        Line2D([], [], ls="none", marker="o", mfc="white", mec="#666", mew=1.8,
                               ms=8, label="hollow: spec ceiling an active sensor may choose")],
              loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3, frameon=False,
              handletextpad=0.4, columnspacing=1.4)
    save(fig, "vmax_grid_f1_active_range",
         "The unambiguous-speed law on the repetition-rate axis. Filled markers are the ambient "
         "repetition rate a passive receiver is given; hollow markers are the specification ceiling "
         "an active monostatic sensor may configure; the arrow between them is the entire benefit of "
         "owning the transmitter while staying inside reference-signal processing. The shaded band "
         "is the published maximum speed of the seven airframes in the registry.")

    # ------------------------------------------------------------------ #
    #  F2  기하 무관성 + 완화곡선
    # ------------------------------------------------------------------ #
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
    sw = fr["P2_relief_curve"]["sweep"]
    bx = np.linspace(0, 155, 400)
    axes[0].plot(bx, 1.0 / np.cos(np.radians(bx) / 2.0), "-", color=INK2, lw=1.4, zorder=2)
    axes[0].plot([r["beta_deg_from_fs_params"] for r in sw],
                 [r["relief_numeric"] for r in sw], "o", ms=7, mfc="white", mec="#c2185b",
                 mew=1.8, zorder=3)
    axes[0].plot(0, 1, "*", ms=16, mfc="#c2185b", mec="white", mew=0.8, zorder=4)
    axes[0].annotate("monostatic = bistatic at $\\beta$=0\n(computed difference: 0 m/s)",
                     (0, 1), textcoords="offset points", xytext=(18, 34), fontsize=7.6, color="#c2185b")
    for cfg, col in (("B", "#2a78d6"), ("C", "#1baf7a")):
        s = fr["P3_scene_relief"]["by_configuration"][cfg]
        axes[0].axvline(s["beta_deg"]["med"], color=col, ls=":", lw=1.2)
        axes[0].text(s["beta_deg"]["med"] + 1.5, 3.3,
                     "cfg %s median $\\beta$ = %.1f$\\degree$" % (cfg, s["beta_deg"]["med"]),
                     fontsize=7.2, color=col, rotation=90, va="top")
    axes[0].set_xlabel("Bistatic angle  $\\beta$  [deg]")
    axes[0].set_ylabel("Relief factor  $1/\\cos(\\beta/2)$")
    axes[0].set_title("The floor is geometry-free; bistatic only relaxes it")
    axes[0].set_ylim(0.9, 4.0)
    axes[0].legend(handles=[Line2D([], [], color=INK2, ls="-", label="closed form"),
                            Line2D([], [], ls="none", marker="o", mfc="white", mec="#c2185b",
                                   mew=1.8, ms=7, label="from fs_params (max rel. err %.1e)"
                                   % fr["P2_relief_curve"]["max_rel_err"])],
                   loc="upper left", frameon=False)

    for b in BANDS:
        v0 = fr["P1_floor_identity"]["v_floor_ms"][b]
        axes[1].plot(bx, v0 / np.cos(np.radians(bx) / 2.0), "-", color=COL[b], lw=1.5)
        axes[1].text(152, v0 / np.cos(np.radians(152) / 2.0), " " + BL[b],
                     fontsize=7.4, color=COL[b], va="center")
    axes[1].axhspan(v_slow, v_fast, color="#2a78d6", alpha=0.07, lw=0)
    axes[1].axhline(5.0, color=INK2, ls=":", lw=1.0)
    axes[1].text(3, 5.4, "scene speed 5 m/s", fontsize=7.2, color=INK2)
    axes[1].set_yscale("log")
    axes[1].set_xlim(0, 200)
    axes[1].set_xlabel("Bistatic angle  $\\beta$  [deg]")
    axes[1].set_ylabel("$v_{max}$  [m/s]")
    axes[1].set_title("Same relief applied to the three ambient illuminators")
    save(fig, "vmax_grid_f2_geometry_independence",
         "Left: the geometric relief factor computed from the repository geometry function against "
         "its closed form, with the monostatic case sitting exactly at beta=0. Right: the same "
         "relief applied to the three ambient repetition rates - the published values are the "
         "beta=0 worst case of both geometries, and the shaded band is the airframe speed range.")

    # ------------------------------------------------------------------ #
    #  F3  9 셀 × 속도 — 무모호로 관측 가능한 헤딩 비율
    # ------------------------------------------------------------------ #
    ace = overlay["configuration_A_at_its_ceiling"]["by_cell"]
    order = [c["cell_id"] for c in cells] + list(ace.keys())
    sp = overlay["speed_axis"]["items"]
    sp_items = sorted(sp.items(), key=lambda kv: kv[1])
    Mx = np.zeros((len(order), len(sp_items)))
    for i, cid in enumerate(order):
        src = (overlay["by_cell"][cid] if cid in overlay["by_cell"] else ace[cid])
        for j, (nm, _v) in enumerate(sp_items):
            Mx[i, j] = src["by_speed"][nm]["observable_frac_T0p1"]
    order_lab = [cid + ("" if cid in overlay["by_cell"]
                        else "  (%g Hz)" % ace[cid]["prf_hz"]) for cid in order]
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    im = ax.imshow(Mx, cmap="viridis", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(sp_items)))
    ax.set_xticklabels(["%s\n%.1f m/s" % (nm.replace("_max", "").replace("_", " "), v)
                        for nm, v in sp_items], fontsize=7.2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order_lab, fontsize=8)
    ax.axhline(len(cells) - 0.5, color="white", lw=2.5)
    for i in range(len(order)):
        for j in range(len(sp_items)):
            ax.text(j, i, "%.2f" % Mx[i, j], ha="center", va="center", fontsize=6.8,
                    color=("white" if Mx[i, j] < 0.55 else "black"))
    ax.set_title("Fraction of headings that are BOTH unambiguous and detectable   (CPI 0.1 s)")
    ax.grid(False)
    fig.colorbar(im, ax=ax, fraction=0.026, pad=0.02, label="observable heading fraction")
    ax.text(0.0, -1.90, "top 9 rows: ambient repetition rate (what the network gives you).  "
            "bottom 3: same geometry, configuration A having chosen its tier-1 rate",
            fontsize=7.4, color=INK2, transform=ax.get_yaxis_transform(), ha="left")
    ax.text(0.0, -1.58, "hover column is zero by definition: f_d = 0 falls inside the "
            "zero-Doppler guard, so it is unambiguous and invisible at once",
            fontsize=7.2, color=INK2, transform=ax.get_yaxis_transform(), ha="left")
    save(fig, "vmax_grid_f3_cell_speed_matrix",
         "Per-cell verdict on the speed axis: the fraction of headings at which a target of that "
         "speed is simultaneously unambiguous (|f_d| < PRF/2) and detectable (folded |f_d| outside "
         "the 1.5-bin zero-Doppler guard), computed over 48 ranges x 24 scene azimuths x 720 "
         "headings. The top nine rows use each illuminator's ambient repetition rate; the bottom "
         "three repeat configuration A with the repetition rate it is allowed to choose, which is "
         "the only thing that moves the 5G row.")
    return figs


# =========================================================================== #
#  8. main
# =========================================================================== #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="그림 생략(빠른 확인)")
    args = ap.parse_args()
    t0 = time.time()

    print("① 바닥의 기하 무관성 · 완화곡선 …")
    fr = floor_and_relief()
    print("   모노 = 바이(β=0) 최대차 %.3e m/s · 완화 닫힌형 최대상대오차 %.2e"
          % (fr["P1_floor_identity"]["max_abs_diff_ms"], fr["P2_relief_curve"]["max_rel_err"]))

    print("② 능동 PRF 천장 두 단 …")
    tiers = active_prf_tiers()
    curves = active_sweep_curves(tiers)
    for b in BANDS:
        t1 = tiers[b]["tier1_reference_signal_reuse"]
        print("   %-4s 패시브 %7.3f m/s → tier1 %8.3f m/s (×%s)"
              % (b, tiers[b]["passive_point"]["v_max_ms"], t1["v_max_ms"] or float("nan"),
                 ("%.1f" % t1["gain_over_passive_x"]) if t1["gain_over_passive_x"] else "—"))

    print("③ 9 셀 구성 …")
    cells = build_cells(fr, tiers)

    print("④ LaSen 을 같은 축에 …")
    lasen = lasen_on_our_axis()

    print("⑤ 실기체 속도 겹치기(격자 d48×φ24×ψ720, CPI 2종) …")
    overlay = drone_overlay(cells, tiers)

    print("⑥ 검증 · 정정 · 함정 …")
    ver = verifications()
    _x = overlay["cross_check_vs_vmax_hardening_E5"]
    ver["V3_published_E5_parity"] = dict(
        what=_x["what"], n_rows=_x["n_rows"], max_abs_diff=_x["max_abs_diff"],
        where="drone_overlay.cross_check_vs_vmax_hardening_E5.rows",
        verdict=("게재된 E5 표 %d 행을 기준점에서 전수 재현했다(최대차 %.1e). 이 층의 판정기가 "
                 "기존 결과와 같은 답을 낸다." % (_x["n_rows"], _x["max_abs_diff"])))
    ct = corrections_and_traps(tiers, cells)
    print("   저장소 패리티 최대차 %.3e · E5 %d행 재현 최대차 %.3e"
          % (ver["V1_repo_parity"]["max_abs_diff"], _x["n_rows"], _x["max_abs_diff"]))

    figs = {}
    if not args.smoke:
        print("⑦ 그림 3장 …")
        figs = make_figures(fr, tiers, curves, cells, overlay, lasen)

    runtime = time.time() - t0
    _ac = overlay["configuration_A_at_its_ceiling"]["by_cell"]
    doc = dict(
        meta=dict(
            script="benchmark/vmax_grid.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            question=("무모호 속도 층을 모노스태틱·바이스태틱 두 기하 위에 동시에 올리면 무엇이 "
                      "바뀌고 무엇이 그대로인가 — 그리고 능동이 사는 자유는 정확히 얼마인가"),
            smoke=bool(args.smoke), runtime_s=runtime,
            house_rules="figure text English; prose Korean; every number carries a source",
            convention=("v_max 는 **반쪽 구간**(±) 값이다: v_max = λ·PRF/4 (β=0, δ_el=0). "
                        "일반형은 λ·PRF/(4 cos(β/2) cos δ_el) 이고 λ·PRF/4 는 그 하한이다."),
            grid=dict(
                shape="2 기하행(모노/바이) × 3 조명원 = 6 · 모노행이 A(능동)·B(패시브 준모노)로 "
                      "쪼개져 셀은 9 개다",
                geometry_rows={"monostatic": ["A", "B"], "bistatic": ["C"]},
                illuminators=list(BANDS),
                d_grid_m=[float(D_GRID[0]), float(D_GRID[-1])], n_d=len(D_GRID),
                phi_grid_deg_step=15.0, n_phi=len(PHI_GRID), n_psi=len(PSI_GRID),
                alt_m=float(ALT), T_cpi_s=list(T_CPI),
                baselines_m={k: v["L"] for k, v in CFG.items()}),
            repo_functions_used=[
                "freespace_scene.fs_params", "freespace_scene.target_pos",
                "freespace_scene.prf_hz", "freespace_scene.M_from_prf",
                "freespace_scene.doppler_bin_hz", "freespace_scene.folded_doppler",
                "freespace_scene.nyquist_gate", "freespace_scene.blind_fractions",
                "freespace_scene.cpi_feasibility", "waveforms.{wifi_80211ac,lte_downlink,nr_downlink}",
                "drones.DRONES"],
            inputs_read=["outputs/refrate_law.json", "outputs/vmax_hardening.json",
                         "outputs/monostatic_prior.json", "outputs/geometry_grid.json",
                         "outputs/report13_freespace.json", "docs/DRONE_SPECS.md"]),
        headline=dict(
            one_line=("무모호 속도의 **바닥은 기하와 무관**하고(모노 = 바이 β=0, 차이 0), "
                      "**통제권은 구성이 정한다** — 패시브는 점 하나, 능동은 구간이며 그 구간의 "
                      "규격 천장은 3.5 GHz 에서 10.71 m/s 로 어떤 기체의 최고속도도 못 덮는다."),
            floor_ms={b: fr["P1_floor_identity"]["v_floor_ms"][b] for b in BANDS},
            active_tier1_ms={b: tiers[b]["tier1_reference_signal_reuse"]["v_max_ms"] for b in BANDS},
            active_gain_x={b: tiers[b]["tier1_reference_signal_reuse"]["gain_over_passive_x"]
                           for b in BANDS},
            active_tier1_kind={b: tiers[b]["tier1_reference_signal_reuse"]["kind"] for b in BANDS},
            active_tier1_quoting_rule=("⚠ 규격 천장으로 인용 가능한 것은 nr(500 Hz)·lte(4000 Hz) 뿐이다. "
                                       "wifi 값은 자기 스케줄링 듀티 산술한계이지 규격 천장이 아니다."),
            geometry_relief_at_beta={"45deg": 1.0 / math.cos(math.radians(45) / 2.0),
                                     "90deg": 1.0 / math.cos(math.radians(90) / 2.0)},
            active_ceiling_does_not_close_the_gap=dict(
                cell="A-nr@tier1 (CSI-RS 500 Hz, CPI 0.1 s)",
                observable_frac_at_scene_slow_5ms=_ac["A-nr@tier1"]["by_speed"]["scene_slow"][
                    "observable_frac_T0p1"],
                observable_frac_at_scene_fast_15ms=_ac["A-nr@tier1"]["by_speed"]["scene_fast"][
                    "observable_frac_T0p1"],
                observable_frac_at_mavic4pro_max_25ms=_ac["A-nr@tier1"]["by_speed"][
                    "mavic4pro_max"]["observable_frac_T0p1"],
                ambient_counterpart_at_15ms=overlay["by_cell"]["A-nr"]["by_speed"]["scene_fast"][
                    "observable_frac_T0p1"],
                statement=("규격 천장까지 올려도 5G 능동 모노는 15 m/s 에서 헤딩의 %.0f %% 만 "
                           "무모호·검출 동시성립이다(상시값 %.0f %% 대비 %.1f배). 천장은 격차를 "
                           "줄이지 닫지 않는다."
                           % (100 * _ac["A-nr@tier1"]["by_speed"]["scene_fast"]["observable_frac_T0p1"],
                              100 * overlay["by_cell"]["A-nr"]["by_speed"]["scene_fast"]["observable_frac_T0p1"],
                              _ac["A-nr@tier1"]["by_speed"]["scene_fast"][
                                  "gain_over_ambient_observable_x"] or float("nan")))),
            what_is_new_here=("기하를 축으로 올린 뒤에도 이 층의 결론이 **그대로 서고 오히려 강해진다**는 것 — "
                              "발표해온 값이 두 기하의 최악값이기 때문이다."),
            what_changed=("'패시브만 구속된다'는 문장은 폐기한다. 벽은 공통이고, 능동이 사는 것은 "
                          "그 벽의 위치를 고를 권리(5G 에서 10배)와 전 파형 레인의 무료 이용권이다.")),
        floor_and_relief=fr,
        active_prf_tiers=tiers,
        active_sweep_curves=curves,
        cells=cells,
        lasen=lasen,
        drone_overlay=overlay,
        verifications=ver,
        **ct,
        provenance={
            "v_max = λ·PRF/4": "outputs/refrate_law.json : law.forms (본 파일 P1 이 두 기하에서 재검증)",
            "모노 = 바이 β=0": "outputs/vmax_grid.json : floor_and_relief.P1_floor_identity.max_abs_diff_ms",
            "완화계수 1/cos(β/2)": "outputs/vmax_grid.json : floor_and_relief.P2_relief_curve",
            "5G 패시브 1.07 m/s": "outputs/refrate_law.json : illuminators.rows.nr_ssb.v_max_ms",
            "WiFi 비콘 0.140 m/s": "outputs/refrate_law.json : illuminators.rows.wifi_beacon.v_max_ms",
            "LTE CRS 40.67 m/s": "outputs/refrate_law.json : illuminators.rows.lte_crs.v_max_ms",
            "능동 5G 천장 500 Hz / 10.71 m/s":
                "outputs/monostatic_prior.json : prf_ladder_at_3p5GHz[csirs_spec_max]",
            "LTE CRS 심볼단위 4000 Hz": "outputs/refrate_law.json : illuminators.rows.lte_crs_sym",
            "v·R = c·λ/8": "Skolnik(고전) — outputs/geometry_grid.json : control_axis 와 같은 항등식",
            "LaSen 신원·인용": "outputs/monostatic_prior.json : lasen.identity",
            "LaSen 베이스라인 2.6 m/s":
                "outputs/monostatic_prior.json : verification_of_our_law_against_prior_measurements"
                ".lasen_csirs_baseline",
            "기체 최고속도": "src/drones.py : DRONES[*].max_speed_ms (docs/DRONE_SPECS.md §1 과 대조)",
            "장면속도 5/15 m/s": "src/freespace_scene.py : FS_SPEED",
            "가드 1.5빈 규약": "src/freespace_scene.py : DOPPLER_GUARD_HARD_BINS",
            "X1~X6 조건절": "outputs/vmax_hardening.json : verdict.corrections_required",
            "9 셀 정의·구성 A/B/C": "outputs/geometry_grid.json : configurations_and_grid",
        },
        figures=figs,
        next_steps=[
            dict(item="모노 팔 R90 재계산 후 tier-2 값 갱신",
                 decides="A 행의 자체파형 상한이 실제 검출거리와 맞물리는 지점",
                 where="src/monostatic_scene.py (다른 워크플로) → 본 파일 tier2.r90_reference_m"),
            dict(item="상용 셀 SSB 주기 분포 실측",
                 decides="1.07 m/s 가 기본설정의 귀결인지 배치의 현실인지",
                 where="X410 실측 캠페인 1순위 관측항목"),
            dict(item="비균일 표본(SSB+TRS·CSI-RS 다중세트)의 등가 반복률 정식화",
                 decides="LaSen 레인을 우리 축에 정량적으로 얹을 수 있는지",
                 where="benchmark/vmax_hardening.py : B_unfolding 확장"),
        ],
        handoff=dict(
            to="freespace_scene 담당 워크플로",
            finding=("`blind_fractions`·`blind_sector` 는 TX/RX 를 FS_TX·FS_RX(L) 로 하드코딩해 "
                     "**모노스태틱 팔(TX=RX)을 표현할 수 없다**. 본 파일은 같은 판정을 일반화한 "
                     "`heading_fractions()` 로 하고 바이스태틱 기준셀에서 정본과 대조했다 "
                     "(최대차 %.3e)." % ver["V1_repo_parity"]["max_abs_diff"]),
            exact_patch_if_wanted=("def blind_fractions(..., tx=None, rx=None): "
                                   "tx = FS_TX if tx is None else tx; "
                                   "rx = FS_RX(L) if rx is None else rx  — 기본값이 현행과 같으므로 "
                                   "기존 호출부는 비트 단위로 불변이다."),
            status="본 파일은 그 파일을 편집하지 않았다"),
    )

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(_sane(doc), f, ensure_ascii=False, indent=1)
    print("\n✔ %s  (%.1f KB, %.1f s)"
          % (os.path.relpath(OUT_JSON, _ROOT), os.path.getsize(OUT_JSON) / 1024.0, runtime))


if __name__ == "__main__":
    main()
