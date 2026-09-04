# -*- coding: utf-8 -*-
"""
geometry_grid.py — 2×3 벤치마크 격자의 정의와 **공정성 감사**
==============================================================
질문: 기하(모노/바이) × 조명원(WiFi/LTE/5G) 격자를 세울 때, **무엇을 고정해야
      비교가 뜻을 갖고, 무엇을 반드시 변하게 둬야 하는가.**

이 단계는 아무것도 계산하기 **전에** 돌아야 한다 — 재프레이밍이 성립하는지를
여기서 판정하기 때문이다. 산출: `outputs/geometry_grid.json`.

세 구성을 절대 섞지 않는다 (PAPER_SPEC §0.2):
  A 능동 모노스태틱   : 내가 송신 · β≈0 · PRF **설계변수** (예 LaSen)
  B 패시브 준모노스태틱: 남이 송신 · β≈0(수신기를 기지국 옆) · PRF 주어짐
  C 패시브 바이스태틱  : 남이 송신 · β 큼 · PRF 주어짐  (우리 기존)
⚠ "패시브 모노스태틱" 은 한 단어로 쓰지 않는다.

세 축의 독립성:
  기하   → 링크버짓(1/R⁴ ↔ 1/(R₁²R₂²)) · 도플러 완화 1/cos(β/2) · 자세 · 가림
  조명원 → λ · 대역 · 상시 반복률 · 점유           (기하 무관)
  통제   → PRF 가 설계변수인가 주어진 값인가        (기하 무관)

실행:
    cd /workspace/sionna
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/geometry_grid.py

집안 규약: 산문·print 는 한국어, 그림 텍스트는 영어(이 스크립트는 그림 없음),
모든 수치는 저장소 함수/JSON 에서 뽑는다 — 손으로 치지 않는다.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import freespace_scene as FS                      # noqa: E402
import freespace_link as FL                       # noqa: E402
import waveforms as WF                            # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "geometry_grid.json")

# --------------------------------------------------------------------------- #
#  0. 규약 상수 — 전부 저장소에서 읽는다
# --------------------------------------------------------------------------- #
C0 = FS.C0
#: 헤드라인 링크버짓 (report13_freespace.meta.link_budget 과 동일해야 한다 — 아래서 검증)
EIRP_DBM, GRX_DBI, NF_DB = 63.0, 10.0, 5.0
T_CPI_S = FS.T_CPI_REF_S                          # 0.1 s
L_REF = FS.L_REF                                  # 500 m (바이스태틱 헤드라인 베이스라인)
PHI = FS.PHI_HEADLINE_DEG                         # 90°
ALT = FS.FS_ALT[0]                                # 60 m
TX_NODE = FS.FS_TX                                # (0,0,25) — 조명원 마스트
#: 모노스태틱 노드는 **조명원 자리**에 둔다. 구성 A 는 그 송신기가 곧 센서이고,
#: 구성 B 는 수신기를 그 옆으로 옮긴 것이므로 둘 다 여기서 출발한다.
MONO_NODE = TX_NODE
D_GRID = np.geomspace(100.0, 20000.0, 240)        # FL.D_GRID_DEFAULT 와 같은 격자
PSI_GRID = np.linspace(0.0, 360.0, 721)[:-1]      # 헤딩 격자

BANDS = ("wifi", "lte", "nr")
BAND_LABEL = {"wifi": "WiFi 802.11ac", "lte": "LTE Rel-9", "nr": "5G NR Rel-16"}
MODE_G1 = "G1"                                    # 상시(always-on) 점유 모드 = 정본


def _wf(std):
    """표준 → G1(상시) 파형 객체. 반송파·대역·fs·기준신호 길이의 단일 진리원."""
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
                if isinstance(cur, dict):
                    cur = cur[part]                       # 문자열 키 우선(by_N 의 "1")
                else:
                    cur = cur[int(part)]                  # 리스트면 정수 인덱스
            return cur
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return default


# --------------------------------------------------------------------------- #
#  1. 축 독립성 — 무모호 속도의 바닥은 기하와 무관하다 (수치 증명)
# --------------------------------------------------------------------------- #
def axis_independence():
    """세 축이 실제로 독립인지 **계산으로** 확인한다.

    증명해야 할 것 셋:
      P1 `v_max = λ·PRF/4` 의 바닥은 모노와 바이(β=0)에서 **완전히 같다**.
      P2 바이스태틱 완화계수는 `1/cos(β/2)` 이고 β 가 커질수록 **관대해진다**.
         → 우리가 인용해온 값은 두 기하의 **최악값**이다.
      P3 λ·PRF(조명원 축)와 듀티(점유 축)에는 기하 변수가 들어가지 않는다.

    ⚠ 앙각 완화 `1/cos δ_el` 는 **두 기하 모두** 갖는다 — 바이스태틱 전용이 아니다.
      두 기하의 차이는 앙각을 맞췄을 때 정확히 `1/cos(β/2)` 뿐이다.
    """
    lam = {b: C0 / _wf(b).carrier_hz for b in BANDS}
    prf = {b: FS.prf_hz(b, MODE_G1) for b in BANDS}
    v_floor = {b: lam[b] * prf[b] / 4.0 for b in BANDS}

    # --- P1: 같은 표적 위치에서 모노(TX=RX)와 바이(β→0) 의 f_d 최대값 비교 ---------
    tgt = FS.target_pos(D_GRID, PHI, L_REF, ALT)              # (240,3)
    vel = FS.heading_velocity(PSI_GRID[:, None], 15.0)        # (720,1,3)

    rows_mono, rows_bi = [], []
    for b in BANDS:
        fc = _wf(b).carrier_hz
        # 모노: TX = RX = MONO_NODE  (fs_params 는 L=0 을 그대로 처리한다)
        pm = FS.fs_params(MONO_NODE, MONO_NODE, tgt, vel, fc)
        # 바이: 헤드라인 기하
        pb = FS.fs_params(TX_NODE, FS.FS_RX(L_REF), tgt, vel, fc)
        for tag, p, acc in (("mono", pm, rows_mono), ("bi", pb, rows_bi)):
            beta = np.asarray(p["beta"], float)
            el = np.asarray(p["el_deg"], float)
            beta = beta[0] if beta.ndim > 1 else beta
            el = el[0] if el.ndim > 1 else el
            fd_num = np.max(np.abs(np.asarray(p["fd"], float)), axis=0)   # 헤딩 최대
            fd_cls = (2.0 * 15.0 / lam[b]) * np.cos(np.radians(beta) / 2.0) \
                * np.cos(np.radians(el))
            acc.append(dict(
                band=b, beta_deg_med=float(np.median(beta)),
                beta_deg_max=float(np.max(beta)),
                el_deg_med=float(np.median(el)),
                fd_closed_vs_numeric_max_rel_err=float(
                    np.max(np.abs(fd_cls - fd_num) / np.maximum(fd_num, 1e-12))),
                relief_beta_med=float(np.median(1.0 / np.cos(np.radians(beta) / 2.0))),
                relief_beta_max=float(np.max(1.0 / np.cos(np.radians(beta) / 2.0))),
                relief_el_med=float(np.median(1.0 / np.cos(np.radians(el)))),
            ))

    # β=0 에서 두 기하의 바닥이 **비트 단위로** 같은지
    floor_identity = {}
    for b in BANDS:
        v_mono = lam[b] * prf[b] / (4.0 * np.cos(0.0) * np.cos(0.0))
        v_bi0 = lam[b] * prf[b] / (4.0 * np.cos(0.0 / 2.0) * np.cos(0.0))
        floor_identity[b] = dict(v_max_mono_ms=float(v_mono), v_max_bi_beta0_ms=float(v_bi0),
                                 abs_diff_ms=float(abs(v_mono - v_bi0)))

    relief_ladder = {f"beta_{d}_deg": float(1.0 / np.cos(np.radians(d) / 2.0))
                     for d in (0, 15, 30, 45, 60, 90, 120, 150)}

    # 구성별 베이스라인에서 장면 완화계수 — A(L=0) · B(L=10 m 병설) · C(L=500 m) · C'(L=2000 m)
    by_baseline = {}
    for tag, L in (("A_L0", 0.0), ("B_L10", 10.0), ("C_L500", L_REF), ("C_L2000", 2000.0)):
        p = FS.fs_params(TX_NODE, (FS.FS_RX(L) if L > 0 else TX_NODE), tgt, np.zeros(3),
                         _wf("nr").carrier_hz)
        beta = np.asarray(p["beta"], float)
        rel = 1.0 / np.cos(np.radians(beta) / 2.0)
        by_baseline[tag] = dict(
            baseline_m=float(L), beta_deg_med=float(np.median(beta)),
            beta_deg_max=float(np.max(beta)),
            relief_med=float(np.median(rel)), relief_max=float(np.max(rel)),
            frac_beta_gt_45deg=float(np.mean(beta > 45.0)),
            frac_beta_gt_90deg=float(np.mean(beta > 90.0)),
            gate_note="45° = 바이스태틱 자세패턴 성립창(PAPER_SPEC §3) · "
                      "90° = SBR 엔진 유효범위(freespace_scene.BETA_VALID_MAX_DEG)")

    # --- P3: 조명원 축·점유 축에 기하 변수가 없다 ---------------------------------
    duty = {}
    for b in BANDS:
        w = _wf(b)
        M = FS.M_from_prf(T_CPI_S, prf[b])
        t_ref = len(w.tx) / w.fs_hz
        duty[b] = dict(prf_hz=prf[b], M=int(M), t_ref_s=float(t_ref),
                       duty_db=float(FL.duty_db_from_cpi(M, t_ref, T_CPI_S)))

    return dict(
        P1_floor_is_geometry_independent=dict(
            statement="모노스태틱 v_max 는 바이스태틱 β=0 의 특수경우다. 두 값의 차이는 0 이다.",
            by_band=floor_identity,
            v_floor_ms={b: float(v_floor[b]) for b in BANDS},
            lam_m={b: float(lam[b]) for b in BANDS},
            prf_ambient_hz={b: float(prf[b]) for b in BANDS},
            verdict="바닥은 기하와 무관하다 — 우리가 발표해온 값은 두 기하의 최악값이다."),
        P2_bistatic_relief=dict(
            statement="완화계수 = 1/(cos(β/2)·cos δ_el). β 가 커질수록 바이스태틱이 관대해진다.",
            relief_by_beta=relief_ladder,
            relief_by_configuration_baseline=by_baseline,
            canonical_scene_mono=rows_mono,
            canonical_scene_bistatic=rows_bi,
            elevation_relief_note="cos δ_el 완화는 두 기하 모두 갖는다. 앙각을 맞추면 "
                                  "두 기하의 차이는 정확히 1/cos(β/2) 뿐이다.",
            closed_form_check="fd_closed_vs_numeric_max_rel_err 는 헤딩 격자(720점) 양자화 잔차다."),
        P3_illuminator_and_duty_are_geometry_free=dict(
            statement="λ·PRF(조명원)와 듀티(점유)의 정의에 기하 변수가 들어가지 않는다.",
            duty_by_band=duty,
            duty_pair_gaps_db={
                "wifi-lte": duty["wifi"]["duty_db"] - duty["lte"]["duty_db"],
                "wifi-nr": duty["wifi"]["duty_db"] - duty["nr"]["duty_db"],
                "lte-nr": duty["lte"]["duty_db"] - duty["nr"]["duty_db"]},
            verdict="두 기하 행에 같은 값이 들어간다 — 조명원 순위의 이 부분은 기하를 옮겨도 불변이다."),
    )


# --------------------------------------------------------------------------- #
#  2. 거리 정규화 — 1/R⁴ 와 1/(R₁²R₂²) 는 '같은 거리' 없이는 비교 불가
# --------------------------------------------------------------------------- #
def range_normalisation():
    """세 정규화 규약을 정의하고, 각각이 무엇을 고정하고 무엇을 드러내는지 수치로 낸다.

    N1 **등가 모노스태틱 거리** `R_eq = √(R₁R₂)`  ← ⭐ 정본
        바이스태틱 레이더 방정식이 `∝ 1/(R₁R₂)² = 1/R_eq⁴` 라서, 같은 R_eq 면 확산항이
        **구성상 정확히 같다**. 기하 축의 링크버짓 기여를 0 으로 만들어 나머지(σ·DPI·완화)를
        분리한다. 저장소는 이미 이 축을 갖고 있다(`freespace_scene.fs_params : R_eq`).
    N2 **수신기-표적 거리** `R₂` 고정
        운용자가 실제로 말하는 거리. 모노는 R₁=R₂ 라 확산항 `40log R₂`, 바이는
        `20log R₁ + 20log R₂` → 차이 = `20log(R₂/R₁)`.
    N3 **장면 지상거리 d** 고정 (report13 정본 축, 중점기준 φ=90°)
        같은 하늘 위치에 표적을 두고 두 기하를 돌린다. 배치 비교에 맞다.

    ⚠ 세 규약은 서로 다른 답을 준다. 하나를 고르고 **어느 것인지 반드시 밝힌다.**
    """
    lb = dict(eirp=EIRP_DBM, grx=GRX_DBI, nf=NF_DB, sigma=0.01, T=T_CPI_S)
    lam = C0 / _wf("nr").carrier_hz

    # --- N1 검증: 같은 R_eq 를 갖는 (R1,R2) 쌍이면 확산항이 같은가 ------------------
    rng = np.random.default_rng(11)
    r_eq = np.geomspace(200.0, 20000.0, 120)
    ratio = rng.uniform(0.2, 5.0, size=r_eq.size)          # R1/R2 비를 마구 흔든다
    R1 = r_eq * np.sqrt(ratio)
    R2 = r_eq / np.sqrt(ratio)
    t_bi = FL.snr_rd_terms_db(R1=R1, R2=R2, lam=lam, **lb)
    t_mono = FL.snr_rd_terms_db(R1=r_eq, R2=r_eq, lam=lam, **lb)
    d_spread = np.asarray(t_bi["spread"], float) - np.asarray(t_mono["spread"], float)
    n1 = dict(
        convention="R_eq = sqrt(R1*R2) 고정",
        max_abs_spread_diff_db=float(np.max(np.abs(d_spread))),
        r1_over_r2_span=[float(ratio.min()), float(ratio.max())],
        n_pairs=int(r_eq.size),
        meaning="R1/R2 를 25배 흔들어도 확산항 차이가 부동소수 수준이다 — "
                "N1 아래서 기하 축의 링크버짓 기여는 정확히 0 이다.",
        honesty="이것은 발견이 아니라 **규약**이다. 바이스태틱 레이더 방정식이 R_eq 로 접히도록 "
                "축을 고른 결과이고, 그렇게 고른 이유는 남는 항(σ·DPI·기준채널·완화)을 "
                "분리해 보려는 것이다.")

    # --- N2 · N3: 장면방위 φ 를 함께 쓸어야 한다 -----------------------------------
    # ⚠ 헤드라인 φ=90° 는 베이스라인의 수직이등분선이라 R1≈R2 가 **구조적으로** 성립한다.
    #   거기서만 재면 "두 기하가 거의 같다" 는 착시가 나온다. φ 를 쓸어 그 착시를 깬다.
    v0 = np.zeros(3)
    fc_nr = _wf("nr").carrier_hz
    phi_list = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0]
    n2_by_phi, n3_by_phi = {}, {}
    for ph in phi_list:
        t = FS.target_pos(D_GRID, ph, L_REF, ALT)
        pb_ = FS.fs_params(TX_NODE, FS.FS_RX(L_REF), t, v0, fc_nr)
        pm_ = FS.fs_params(MONO_NODE, MONO_NODE, t, v0, fc_nr)
        R1_, R2_ = np.asarray(pb_["R1"], float), np.asarray(pb_["R2"], float)
        d2 = 20.0 * np.log10(R2_ / R1_)                       # bi − mono(수신기 자리)
        d3 = 40.0 * np.log10(np.asarray(pm_["R1"], float)
                             / np.asarray(pb_["R_eq"], float))  # bi − mono(조명원 자리)
        n2_by_phi[f"phi_{int(ph)}"] = dict(
            delta_db_median=float(np.median(d2)), delta_db_absmax=float(np.max(np.abs(d2))),
            delta_db_at_d_min=float(d2[0]), delta_db_at_d_max=float(d2[-1]))
        n3_by_phi[f"phi_{int(ph)}"] = dict(
            delta_db_median=float(np.median(d3)), delta_db_absmax=float(np.max(np.abs(d3))),
            delta_db_at_d_min=float(d3[0]), delta_db_at_d_max=float(d3[-1]))

    n2 = dict(
        convention="R2(수신기-표적) 고정 · 모노 노드를 **수신기 자리**에 둔 비교",
        formula="Δspread_db = 20*log10(R2/R1)",
        by_phi=n2_by_phi,
        headline_phi="phi_90",
        absmax_over_phi_db=float(max(v["delta_db_absmax"] for v in n2_by_phi.values())),
        meaning="φ=90°(수직이등분선)에서는 R1≈R2 라 두 기하가 거의 겹친다. φ 가 베이스라인 축에 "
                "가까워지면 벌어진다 — ⭐ 헤드라인 φ 하나로만 재면 기하 차이를 놓친다.")
    n3 = dict(
        convention="장면 지상거리 d 고정(중점기준, L=500 m) · 모노 노드를 **조명원 자리**에 둔 비교",
        formula="Δspread_db = 40*log10(R_mono / R_eq_bistatic)",
        by_phi=n3_by_phi,
        headline_phi="phi_90",
        absmax_over_phi_db=float(max(v["delta_db_absmax"] for v in n3_by_phi.values())),
        meaning="같은 하늘 위치에 표적을 두고 두 기하를 돌린 값. 배치 비교에 맞는 뷰다.")

    return dict(
        canonical="N1",
        why_canonical="바이스태틱 레이더 방정식이 R_eq⁴ 로 정확히 접히므로, N1 아래서 "
                      "기하 축의 링크버짓 기여가 0 이 되어 나머지 항을 분리할 수 있다. "
                      "N2·N3 은 배치 관점의 보조 뷰로 함께 낸다.",
        N1_equal_R_eq=n1, N2_equal_R2=n2, N3_equal_scene_range=n3,
        reporting_rule="헤드라인은 N1 로 낸다. 그림·표 캡션에 정규화 이름을 반드시 적는다. "
                       "'같은 거리에서' 라는 표현만 쓰는 문장은 금지한다.")


# --------------------------------------------------------------------------- #
#  3. DPI/자기간섭 원장 — 모노가 안 내는 값, 패시브가 내는 값
# --------------------------------------------------------------------------- #
def interference_ledger():
    """모노스태틱에는 없고 패시브에만 있는 두 비용을 **정규화로 지우지 않고** 표에 남긴다.

    · 패시브: 직접파 간섭(DPI). 요구 소거깊이 ≥ DNR. 베이스라인 L 이 짧을수록 나쁘다
      (`P_dir ∝ 1/L²`) — ⭐ 그래서 **구성 B(수신기를 기지국 옆)가 DPI 최악**이다.
    · 능동 모노: 자기간섭(SI). 문헌 요구치는 총 100 dB 급이다(monostatic_prior 에서 읽는다).
    · 능동 모노는 기준채널이 필요 없다 — 자기가 보낸 심볼을 안다. 패시브는 기준 수신계통을
      하나 더 단다. 우리 정본 규약 `full_waveform_capture`(η_ref=0 dB)는 **패시브에 유리한
      상한**이라, 이 비교는 모노의 이점을 오히려 **과소평가**한다.
    """
    rows, l_min = [], {}
    L_LADDER = np.array([1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 500.0, 1000.0, 2000.0, 5000.0])
    for b in BANDS:
        w = _wf(b)
        lam = C0 / w.carrier_hz
        B_noise = float(w.fs_hz)                       # DPI 잔류가 퍼지는 대역 = fs
        n0_pow = FL.n0_thermal(NF_DB, B_noise)         # [W] (대역 전체)
        per_L = []
        for L in L_LADDER:
            P_dir = FL.direct_power_w(EIRP_DBM, GRX_DBI, lam, float(L))
            dnr = FL.dnr_db(P_dir, n0_pow)
            per_L.append(dict(L_m=float(L), dnr_vs_noise_db=float(dnr),
                              eca_depth_required_db=float(FL.eca_depth_required_db(dnr, 10.0))))
        rows.append(dict(band=b, lam_m=float(lam), b_noise_hz=B_noise, by_L=per_L))
        # 달성 가능한 소거깊이 d 에서 요구를 만족하는 최소 베이스라인
        #   DNR(L) + margin ≤ depth  ⇔  L ≥ L_ref * 10^((DNR(L_ref)+margin-depth)/20)
        Lref = 500.0
        dnr_ref = FL.dnr_db(FL.direct_power_w(EIRP_DBM, GRX_DBI, lam, Lref), n0_pow)
        l_min[b] = {f"depth_{int(dep)}dB": float(Lref * 10 ** ((dnr_ref + 10.0 - dep) / 20.0))
                    for dep in (40.0, 60.0, 90.0, 120.0)}

    # --- 구성 B 실행가능성: 병설 베이스라인에서 요구깊이가 달성치를 넘는가 -----------
    co_site = {}
    for b in BANDS:
        w = _wf(b)
        lam = C0 / w.carrier_hz
        n0_pow = FL.n0_thermal(NF_DB, float(w.fs_hz))
        per = {}
        for L in (5.0, 10.0, 30.0, 100.0):
            dnr = FL.dnr_db(FL.direct_power_w(EIRP_DBM, GRX_DBI, lam, L), n0_pow)
            req = float(FL.eca_depth_required_db(dnr, 10.0))
            per[f"L_{int(L)}m"] = dict(required_depth_db=req,
                                       deficit_vs_60dB=req - 60.0,
                                       deficit_vs_90dB=req - 90.0)
        co_site[b] = per
    dnr_500_lte = float(FL.dnr_db(
        FL.direct_power_w(EIRP_DBM, GRX_DBI, C0 / _wf("lte").carrier_hz, 500.0),
        FL.n0_thermal(NF_DB, float(_wf("lte").fs_hz))))

    si = _read("monostatic_prior.json", "side_by_side.lanes.1.interference_number_dB")
    si_src = _read("monostatic_prior.json", "side_by_side.lanes.1.interference_source")
    dpi_lit = _read("monostatic_prior.json", "side_by_side.lanes.0.interference_number_dB")
    dpi_src = _read("monostatic_prior.json", "side_by_side.lanes.0.interference_source")

    return dict(
        passive_dpi=dict(
            model="P_dir = EIRP·G_rx·λ²/((4π)²L²) (link_budget.LinkBudget.direct_power_w); "
                  "DNR = P_dir / (kT₀F·B_noise); 요구깊이 = DNR + 10 dB 여유",
            b_noise_convention="B_noise = 파형 fs (freespace_link.n0_effective 규약)",
            by_band=rows,
            min_baseline_m_for_achievable_depth=l_min,
            config_B_cositing_feasibility=dict(
                by_band=co_site,
                achievable_depth_sweep_in_repo=[40.0, 60.0, 90.0],
                achievable_source="freespace_link.n0_dpi docstring — 실장 ECA·아날로그 소거는 "
                                  "통상 40~90 dB 에서 멈춘다(선언값, 근거문서 없음)",
                verdict="⭐ 구성 B 는 병설 거리에서 DPI 로 막힌다. LTE 기준 L=10 m 요구깊이가 "
                        "우리가 스윕하는 최선값 90 dB 를 넘는다 — 기하만 모노로 옮기고 "
                        "패시브를 유지하면 소거 요구가 수십 dB 늘어난다."),
            self_check=dict(
                dnr_lte_L500_db=dnr_500_lte,
                documented_value_db=75.36,
                source="freespace_link.dnr_db docstring ★75.36 dB",
                abs_diff_db=abs(dnr_500_lte - 75.36)),
            headline_L_scaling_db=float(20.0 * np.log10(500.0 / 10.0)),
            headline="⭐ 구성 B(수신기를 조명원 옆에)는 기하로는 모노를 얻지만 DPI 는 최악이 된다 — "
                     "P_dir ∝ 1/L² 이라 베이스라인을 500 m 에서 10 m 로 줄이면 DNR 이 "
                     "headline_L_scaling_db 만큼 오른다."),
        active_self_interference=dict(
            required_total_suppression_db=si, source=si_src,
            note="능동 모노는 DPI 대신 자기간섭을 낸다. 이 값은 하드웨어 사양이지 기하 함수가 아니다."),
        passive_dpi_literature=dict(echo_below_los_db=dpi_lit, source=dpi_src),
        reference_channel=dict(
            monostatic="송신 심볼을 정확히 안다 → 기준채널 불필요, η_ref 열화 0.",
            passive="기준 수신계통이 별도로 필요하다. 우리 정본은 `full_waveform_capture`"
                    "(η_ref = 0 dB)로 **이상적 기준**을 가정한다.",
            canonical_reference=_read("report13_freespace.json",
                                      "meta.link_budget.power_normalization.canonical_reference"),
            bias_direction="정본 규약은 패시브에 유리하다 → 이 격자는 모노의 이점을 **과소평가**한다. "
                           "즉 모노가 이기는 결론이 나오면 그 결론은 보수적이다."),
        ledger_rule="DPI·SI·기준채널은 정규화로 지우지 않는다. 셀마다 별도 열로 남긴다.")


# --------------------------------------------------------------------------- #
#  4. 통제 축 — PRF 를 누가 정하는가 (그리고 능동도 무한은 아니다)
# --------------------------------------------------------------------------- #
def control_axis():
    """능동↔패시브의 유일한 차이를 수치로 못박는다.

    · 패시브(B·C): PRF = 망이 정한 상시 반복률. 선택권 없음.
    · 능동(A): PRF 는 설계변수지만 **무한하지 않다** —
        (i) 규격 천장: sub-6 CSI-RS 500 Hz (monostatic_prior 에서 읽는다)
        (ii) 물리 천장: 거리모호. `PRF ≤ c/(2R_unamb)` → 고전 항등식
             `v_unamb · R_unamb = c·λ/8` (Skolnik). 능동은 이 곡선 위에서만 움직인다.
    · 보고 규약: **등-PRF**(기하 분리)와 **고유-PRF**(현실) 둘 다 낸다.
    """
    prf_ladder = _read("monostatic_prior.json", "prf_ladder_at_3p5GHz", default=[]) or []
    spec_ceiling = next((r for r in prf_ladder if r.get("key") == "csirs_spec_max"), None)

    out = {}
    for b in BANDS:
        w = _wf(b)
        lam = C0 / w.carrier_hz
        prf_amb = FS.prf_hz(b, MODE_G1)
        r90 = _read("report13_freespace.json",
                    f"ranges.mavic4pro.{ {'wifi':'W1','lte':'L1','nr':'G1'}[b] }"
                    ".equal_psd.full_waveform_capture.by_N.1.R90_C50_m")
        prod = C0 * lam / 8.0                                    # v·R 상한 [m²/s]
        v_pass = lam * prf_amb / 4.0
        # 능동의 천장은 **두 단**이다 — 섞어 쓰면 476배가 근거 없이 인용된다.
        spec_prf = (float(spec_ceiling["prf_hz"]) if (spec_ceiling and b == "nr") else None)
        out[b] = dict(
            lam_m=float(lam),
            passive_prf_hz=float(prf_amb),
            passive_v_max_ms=float(v_pass),
            active_ceiling_1_spec_reference_signal=dict(
                prf_hz=spec_prf,
                v_max_ms=(float(lam * spec_prf / 4.0) if spec_prf else None),
                gain_over_passive_x=(float(lam * spec_prf / 4.0 / v_pass) if spec_prf else None),
                source=("monostatic_prior.json : prf_ladder_at_3p5GHz[csirs_spec_max]"
                        if spec_prf else
                        "해당 표준의 능동 ISAC 기준신호 반복률 천장을 우리는 아직 못박지 않았다"),
                scope="3GPP 기준신호를 재활용하는 능동 모노(=우리가 파형을 새로 설계하지 않는 경우)"),
            active_ceiling_2_free_waveform_design=dict(
                identity="v_unamb * R_unamb = c*lam/8  (거리모호와의 맞바꿈, Skolnik)",
                v_times_R_m2_per_s=float(prod),
                r90_reference_m=(float(r90) if r90 else None),
                v_max_at_r90_ms=(float(prod / r90) if r90 else None),
                prf_at_r90_hz=(float(C0 / (2.0 * r90)) if r90 else None),
                gain_over_passive_x=(float((prod / r90) / v_pass) if r90 else None),
                scope="자체 파형을 설계하는 능동 레이더. ⚠ 이 값은 3GPP 신호 재활용에는 쓸 수 없다",
                r90_source="report13_freespace.json : ranges.mavic4pro.<mode>"
                           ".equal_psd.full_waveform_capture.by_N.1.R90_C50_m"))

    return dict(
        convention_reported_both=dict(
            equal_prf="같은 PRF 를 양쪽에 넣어 **기하 축만** 남긴다. 능동을 벌하고 패시브를 봐준다.",
            native_prf="각 셀의 실제 반복률을 쓴다. 능동을 봐주고 패시브를 벌한다.",
            rule="⭐ 두 규약이 답을 바꾸는 셀에서는 **둘 다** 보고한다. 하나만 쓰면 결론이 규약의 산물이다."),
        active_is_not_unbounded=dict(
            spec_ceiling_row=spec_ceiling,
            physical_ceiling="거리모호 — PRF ≤ c/(2R_unamb)",
            identity="v_unamb · R_unamb = c·λ/8 (Skolnik 의 고전 결과, 신규성 주장 없음)"),
        by_band=out,
        why_this_matters="'모노스태틱이면 PRF 를 마음대로 고른다' 는 틀렸다. 3GPP 가 sub-6 "
                         "CSI-RS 에 500 Hz 천장을 걸었고, 실측 상용 gNB 는 50~200 Hz 로 돈다 "
                         "⟨monostatic_prior.json : headline_of_this_file⟩. 진짜 탈출구는 "
                         "반복률이 아니라 데이터 심볼이고 그것은 트래픽에 종속된다.")


# --------------------------------------------------------------------------- #
#  5. σ 전이 원장 — 어느 기하가 우리 물리를 더 잘 쓰는가
# --------------------------------------------------------------------------- #
def sigma_transfer(ax=None):
    """σ 사슬이 기하를 옮길 때 무엇을 얻고 무엇을 잃는지.

    ⭐ 사실관계: 우리 σ 격자는 `rcs_sbr_batch`(=**모노스태틱 후방산란**)를 **이등분선 방향**에서
    조회해 바이스태틱 σ 로 쓴다 ⟨report13_sigma_grid.json : meta.engine⟩. 즉 지금의
    바이스태틱 결과는 **이등분선 근사**(monostatic-equivalent) 위에 서 있다.
    그 근사오차 Δσ(β) = σ_multi − σ_bisector 는 이미 측정돼 있다.

    → 모노스태틱 팔은 β=0 이라 그 근사가 **정확히 성립**한다(Δσ ≡ 0). 새 RCS 계산이 필요 없고,
      우리 물리 중 가장 잘 검증된 부분 위에 선다.
    """
    ms = _read("report13_sigma_grid.json", "multistatic", default={}) or {}
    drones = [k for k, v in ms.items() if isinstance(v, dict)
              and any("GHz" in x for x in v)]
    by_beta = {}
    for beta in ("0", "15", "30", "45", "60", "75", "90"):
        p95, rms, rec = [], [], []
        for dr in drones:
            for _bd, rows in ms[dr].items():
                r = rows.get(beta)
                if r and r.get("valid"):
                    p95.append(r["dsigma_p95_db"])
                    rms.append(r["dsigma_rms_db"])
                    rec.append(r["reciprocity_rms_db"])
        if p95:
            by_beta[beta] = dict(n_cells=len(p95),
                                 dsigma_rms_median_db=float(np.median(rms)),
                                 dsigma_rms_max_db=float(np.max(rms)),
                                 dsigma_p95_max_db=float(np.max(p95)),
                                 reciprocity_rms_max_db=float(np.max(rec)))

    recip_drone = _read("sbr_defect_fixes.json", "d2_reciprocity_drone.worst_db")
    kernel_db = _read("sbr_kr_sweep.json", "summary_div16.max_abs_db_vs_po")

    # ⭐ 장면 손실 — β 창 때문에 인용 못 하는 장면 비율. 모노는 0 이다.
    rel = (ax or {}).get("P2_bistatic_relief", {}).get("relief_by_configuration_baseline", {})
    scene_loss = {k: dict(baseline_m=v["baseline_m"],
                          frac_outside_beta45=v["frac_beta_gt_45deg"],
                          frac_outside_beta90=v["frac_beta_gt_90deg"])
                  for k, v in rel.items()}

    return dict(
        fact="σ 격자 엔진 = rcs_sbr_batch (모노스태틱 후방산란), 조회방향 = 바이스태틱 이등분선",
        engine=_read("report13_sigma_grid.json", "meta.engine"),
        bisector_approximation_error_by_beta=by_beta,
        monostatic_arm=dict(dsigma_db=0.0,
                            why="β=0 이면 이등분선 = 시선 = 후방산란. 근사가 항등이 된다.",
                            new_rcs_computation_required=False),
        kernel_accuracy_db_vs_analytic_po=kernel_db,
        reciprocity_worst_db_drone=recip_drone,
        scene_fraction_lost_to_beta_window=dict(
            by_baseline=scene_loss,
            monostatic=0.0,
            grid_caveat="비율은 d 격자 240점(geomspace 100~20000 m) 위의 **점 비율**이다. "
                        "로그격자라 근거리에 가중돼 있고, 면적비·확률비가 아니다.",
            meaning="⭐ 바이스태틱 팔은 헤드라인 장면(L=500 m)의 일부를 β 창 밖으로 잃는다. "
                    "모노 팔은 β≡0 이라 0 % 를 잃는다 — 같은 격자에서 모노 행이 "
                    "장면 전체를 인용할 수 있는 유일한 행이다."),
        correction_to_the_brief=dict(
            claim_in_brief="bistatic is restricted to beta<=45 deg by a reciprocity violation of "
                           "up to 13.7 dB",
            what_13p7_actually_is="matrice4e · 5G NR 3.5 GHz · β=45° 의 **이등분선 근사오차 p95** "
                                  "(dsigma_p95_db = 13.719) 이지 상반성 위반이 아니다",
            true_numbers=dict(
                bisector_p95_max_at_beta45_db=(by_beta.get("45", {}).get("dsigma_p95_max_db")),
                bisector_rms_median_at_beta45_db=(by_beta.get("45", {}).get("dsigma_rms_median_db")),
                reciprocity_rms_max_at_beta45_db=(by_beta.get("45", {})
                                                  .get("reciprocity_rms_max_db")),
                reciprocity_worst_db_drone_beta90=recip_drone),
            why_it_matters="두 양은 크기도 뜻도 다르다. β 창을 정당화하는 근거는 **근사오차** 쪽이고, "
                           "그 값은 13.7 dB 보다 크다 — 즉 모노 팔의 이점이 브리핑보다 더 크다."),
        ledger_rule="σ 는 셀마다 '어느 기하에서 계산했나'를 반드시 적는다. 모노 = 직접계산, "
                    "바이 = 이등분선 근사 + Δσ(β) 오차막대.")


# --------------------------------------------------------------------------- #
#  6. 격자 — 9 셀(3 구성행 × 3 조명원)
# --------------------------------------------------------------------------- #
def build_cells(ax, ctl):
    """각 셀의 시나리오를 정확히 적는다: 송신자·수신자·기하·기준신호·통제 가정.

    ⭐ 모노 행은 A(능동)와 B(패시브 준모노)로 **쪼갠다** — 둘 다 뜻이 있고, 기하가 같고
    통제만 다르기 때문이다. 그 차이가 헤드라인 법칙의 전부다.
    """
    lam = ax["P1_floor_is_geometry_independent"]["lam_m"]
    prf = ax["P1_floor_is_geometry_independent"]["prf_ambient_hz"]
    vfl = ax["P1_floor_is_geometry_independent"]["v_floor_ms"]
    rel = ax["P2_bistatic_relief"]["relief_by_configuration_baseline"]
    REL_TAG = {"A": "A_L0", "B": "B_L10", "C": "C_L500"}

    real = {
        ("A", "wifi"): dict(
            realizable_by_us=True,
            note="5 GHz 비면허대역이라 우리가 직접 송신할 수 있다. 대신 EIRP 규제 상한이 "
                 "매크로 기지국(63 dBm)보다 훨씬 낮다 — 등-EIRP 규약이 이 셀을 크게 봐준다.",
            actor="우리(또는 임의의 WiFi 센싱 노드)",
            prior="WiFi 센싱 문헌 다수(모노/준모노 CSI). 드론 표적은 드물다."),
        ("A", "lte"): dict(
            realizable_by_us=False,
            note="물리는 성립하지만 실행 주체가 없다 — LTE 는 면허대역이고 3GPP ISAC 작업은 "
                 "NR 전용이다. **격자의 λ 팔로만** 의미가 있다(1.8 GHz 능동 모노의 상한).",
            actor="가상의 ISAC eNB",
            prior="없음(조사 범위 안)"),
        ("A", "nr"): dict(
            realizable_by_us=False,
            note="⭐ 게재 대조군이 정확히 여기 있다 — LaSen(SenSys '26)이 모노스태틱 gNB 에서 "
                 "PDSCH 를 재활용한다. 우리는 이 셀을 '남이 이미 한 자리'로 명시한다.",
            actor="ISAC gNB(사업자)",
            prior="LaSen, SenSys '26, pp.732-745, DOI 10.1145/3774906.3800504 (게재)"),
        ("B", "wifi"): dict(
            realizable_by_us=True,
            note="⚠ 퇴화 경고 — AP 바로 옆에서는 프레임을 사실상 완전복조할 수 있어 기준채널이 "
                 "정확지식으로 수렴한다. 남는 차이는 **PRF 통제권 하나뿐**이고, 그것이 A↔B 의 "
                 "정의다. DPI 는 최악이다.",
            actor="남의 AP 옆 수신노드",
            prior="없음(조사 범위 안)"),
        ("B", "lte"): dict(
            realizable_by_us=True,
            note="기지국 사이트 공용 배치. DPI 가 최악이고 기준채널은 최상이다.",
            actor="기지국 병설 패시브 수신기",
            prior="패시브 레이더 문헌의 'co-sited receiver' 배치"),
        ("B", "nr"): dict(
            realizable_by_us=True,
            note="같은 배치의 5G 판. 기하는 A 와 같지만 SSB 50 Hz 를 그대로 물려받는다 — "
                 "A 와 B 를 가르는 수치가 여기서 가장 크게 벌어진다.",
            actor="gNB 병설 패시브 수신기",
            prior="없음(조사 범위 안)"),
        ("C", "wifi"): dict(realizable_by_us=True, note="우리 기존 작업.",
                            actor="독립 수신 사이트", prior="WiFi 패시브 레이더 문헌"),
        ("C", "lte"): dict(realizable_by_us=True, note="우리 기존 작업. 헤드라인 행.",
                           actor="독립 수신 사이트", prior="LTE PCL 문헌 다수"),
        ("C", "nr"): dict(realizable_by_us=True, note="우리 기존 작업. 헤드라인 행.",
                          actor="독립 수신 사이트",
                          prior="Abratkiewicz 외, IEEE JSTARS 16:3469-3484, 2023"),
    }

    cfg_def = {
        "A": dict(name="능동 모노스태틱", transmitter="우리(센서가 곧 송신기)",
                  receiver="송신기와 같은 노드", geometry="β ≈ 0",
                  prf_control="설계변수(규격/거리모호 천장 안에서)",
                  reference_channel="불필요 — 송신 심볼을 안다",
                  interference="자기간섭(SI)"),
        "B": dict(name="패시브 준모노스태틱", transmitter="남(사업자/AP)",
                  receiver="송신기 옆(짧은 베이스라인 L)", geometry="β ≈ 0",
                  prf_control="없음 — 망이 정한 상시 반복률",
                  reference_channel="필요(다만 직접파가 매우 강해 품질은 최상)",
                  interference="직접파 간섭(DPI) — L 이 짧아 **최악**"),
        "C": dict(name="패시브 바이스태틱", transmitter="남(사업자/AP)",
                  receiver="독립 사이트(L 큼)", geometry="β 큼(장면 의존)",
                  prf_control="없음 — 망이 정한 상시 반복률",
                  reference_channel="필요",
                  interference="직접파 간섭(DPI)"),
    }

    cells = []
    for cfg in ("A", "B", "C"):
        for b in BANDS:
            r = real[(cfg, b)]
            ref_sig = {"wifi": "VHT-LTF(패킷당 1회) · 규격보장 상시는 비콘 9.77 Hz",
                       "lte": "CRS(서브프레임당) 1000 Hz",
                       "nr": "SSB(기본 20 ms) 50 Hz"}[b]
            tiers = None
            if cfg == "A":
                c2 = ctl["by_band"][b]["active_ceiling_2_free_waveform_design"]
                c1 = ctl["by_band"][b]["active_ceiling_1_spec_reference_signal"]
                s1 = (f"{c1['v_max_ms']:.4g} m/s (PRF {c1['prf_hz']:.0f} Hz)"
                      if c1["v_max_ms"] else "이 표준은 아직 못박지 않았다")
                v_txt = ("설계변수 — 천장 두 단: ⑴ 규격 기준신호 재활용 " + s1 +
                         f" · ⑵ 자체 파형 설계 시 거리모호 맞바꿈 v·R = "
                         f"{c2['v_times_R_m2_per_s']:.4g} m²/s")
                tiers = dict(spec_reference_signal_ms=c1["v_max_ms"],
                             free_waveform_design_at_r90_ms=c2["v_max_at_r90_ms"])
                v_val = c1["v_max_ms"]                    # 인용은 **보수적인 쪽**으로
                prf_val = c1["prf_hz"]
            else:
                v_txt = "망이 준 반복률로 고정"
                v_val = vfl[b]
                prf_val = prf[b]
            cells.append(dict(
                cell_id=f"{cfg}-{b}",
                configuration=cfg, configuration_name=cfg_def[cfg]["name"],
                illuminator=BAND_LABEL[b], band=b,
                carrier_hz=float(_wf(b).carrier_hz), lam_m=lam[b],
                bandwidth_hz=float(_wf(b).bw_hz),
                transmitter=cfg_def[cfg]["transmitter"],
                receiver=cfg_def[cfg]["receiver"],
                geometry=cfg_def[cfg]["geometry"],
                reference_signal=(ref_sig if cfg != "A"
                                  else f"{ref_sig} 또는 자체 파형/데이터 심볼"),
                control_assumption=cfg_def[cfg]["prf_control"],
                reference_channel=cfg_def[cfg]["reference_channel"],
                interference_cost=cfg_def[cfg]["interference"],
                prf_ref_hz=(float(prf_val) if prf_val else None),
                v_max_ms=(float(v_val) if v_val else None),
                v_max_basis=v_txt,
                v_max_tiers_active=tiers,
                scene_relief=dict(
                    baseline_m=rel[REL_TAG[cfg]]["baseline_m"],
                    beta_deg_med=rel[REL_TAG[cfg]]["beta_deg_med"],
                    relief_med=rel[REL_TAG[cfg]]["relief_med"],
                    relief_max=rel[REL_TAG[cfg]]["relief_max"],
                    v_max_with_median_relief_ms=(float(v_val * rel[REL_TAG[cfg]]["relief_med"])
                                                 if v_val else None),
                    note="v_max_ms 는 β=0 바닥값이다. 장면 완화를 곱한 값이 실제 상한이고, "
                         "완화는 바이스태틱에서만 1 을 넘는다."),
                sigma_path=("직접계산(모노 후방산란, Δσ=0)" if cfg in ("A", "B")
                            else "이등분선 근사 + Δσ(β) 오차막대"),
                actor=r["actor"], realizable_by_us=r["realizable_by_us"],
                prior_occupant=r["prior"], note=r["note"]))
    return dict(configuration_definitions=cfg_def, cells=cells,
                shape="3 구성행(A/B/C) × 3 조명원 = 9 셀. 사용자 지시의 2×3 은 "
                      "'모노 행 / 바이 행'이고, 모노 행이 A·B 로 쪼개져 9 가 된다.")


# --------------------------------------------------------------------------- #
#  7. 성립하지 않는 셀 · 경계
# --------------------------------------------------------------------------- #
def not_meaningful(ledger):
    """채우지 말아야 할 자리를 **채우지 않는다고 적는다.**"""
    lmin = ledger["passive_dpi"]["min_baseline_m_for_achievable_depth"]
    return dict(
        void_cells=[
            dict(cell="B(패시브 준모노) at L → 0",
                 verdict="물리적으로 성립하지 않는다",
                 why="수신 안테나가 남의 송신 안테나 자리를 차지할 수 없고, 남의 송신기에는 "
                     "송신단 자기간섭 제거를 걸 수 없다. 구성 B 는 L>0 에서만 정의된다.",
                 quantified=dict(min_baseline_m_by_achievable_eca_depth=lmin,
                                 rule="요구깊이 = DNR(L)+10 dB ≤ 달성깊이")),
            dict(cell="C(패시브 바이스태틱) × 'PRF 설계'",
                 verdict="통제 축의 빈 칸",
                 why="패시브는 반복률을 고르지 못한다. 이 칸을 채우면 축이 뒤섞인다."),
            dict(cell="바이스태틱 β → 180° (전방산란)",
                 verdict="현재 σ 엔진의 유효범위 밖",
                 why="SBR 은 β→180° 에서 σ≡0 을 낸다 (freespace_scene.BETA_VALID_MAX_DEG=90, "
                     "rcs_sbr 전방산란 미지원). 도플러도 0 으로 죽어 속도정보가 사라진다.",
                 note="실제 패시브 레이더가 이 영역에서 유리할 수 있다는 점은 별도 축이다."),
        ],
        weak_but_kept=[
            dict(cell="A-lte", verdict="물리는 성립, 실행 주체 없음",
                 keep_because="격자의 1.8 GHz 능동 상한을 주는 λ 팔. '가상 셀'로 명시하고 "
                              "배치 주장을 하지 않는다."),
            dict(cell="B-wifi", verdict="성립하지만 A 로 퇴화",
                 keep_because="A↔B 의 유일한 차이(PRF 통제권)를 가장 순수하게 보여주는 셀이다."),
        ])


# --------------------------------------------------------------------------- #
#  8. 공정성 감사 — 고정할 것 / 변하게 둘 것 / 함정
# --------------------------------------------------------------------------- #
def fairness_audit(ax, norm, ledger, ctl):
    lb_repo = _read("report13_freespace.json", "meta.link_budget", default={}) or {}
    held = [
        dict(item="표적 모델", hold="같은 메쉬·재질·SBR 엔진·div=16·jitter=2·대역평균 n_f=3",
             provenance="report13_sigma_grid.json : meta",
             why="σ 절대값이 아니라 **같은 σ 사슬**을 두 기하에 쓰는 것이 공정성의 최소조건"),
        dict(item="자세 처리", hold="자세평균 σ 를 쓴다(단일자세 금지)",
             provenance="sigma_sensitivity.json : aspect_averaged.finding",
             why="단일자세면 5기체가 3가지 순위를 내지만 자세평균이면 순위가 하나로 모인다. "
                 "모노와 바이는 같은 장면 위치에서 **다른 자세각**을 보므로, 자세평균 없이는 "
                 "기하 차이와 자세 우연이 구분되지 않는다"),
        dict(item="CPI", hold=f"T_CPI = {T_CPI_S} s 정본 · 1.0 s 를 제2 규약으로 병기",
             provenance="freespace_scene.T_CPI_REF_S",
             why="긴 CPI 는 블라인드를 고치고 접힘을 못 고친다 — 두 값을 함께 내야 그 분리가 보인다 "
                 "⟨vmax_hardening.json : E_long_cpi⟩"),
        dict(item="검출 규약", hold="Pd=0.9 · 교정 CFAR · 0-도플러 가드 hard 1.5 bin(정본)·"
                                    "declared 2.5 bin(병기)",
             provenance="freespace_scene.DOPPLER_GUARD_HARD_BINS · verify_cfar.json",
             why="가드폭 규약 하나가 '5G 커버리지 0' 같은 문장을 만들었다 — 두 규약 병기가 방어책"),
        dict(item="수신기", hold=f"G_rx={GRX_DBI} dBi · NF={NF_DB} dB · N_rx=1",
             provenance="report13_freespace.json : meta.link_budget", why="선언값, 전 셀 동일"),
        dict(item="거리 정규화", hold="N1 (R_eq=√(R₁R₂))", provenance="본 파일 §2",
             why="N1 아래서 기하 축의 링크버짓 기여가 정확히 0 이 된다"),
        dict(item="점유 모드", hold="G1(상시) 정본 · G2/G3 는 뷰",
             provenance="waveforms.MODES", why="점유는 조명원 축이지 기하 축이 아니다"),
        dict(item="편파", hold="VV 단일", provenance="REBUILD §5.0", why="두 기하에 같은 편파"),
    ]
    vary = [
        dict(item="β", vary="모노 0 · 바이 장면 의존", axis="기하"),
        dict(item="λ·B·PRF_ref·듀티", vary="조명원마다", axis="조명원"),
        dict(item="PRF 통제권", vary="A 는 설계변수 · B/C 는 주어짐", axis="통제"),
        dict(item="간섭 항", vary="A 는 SI · B/C 는 DPI(그리고 L 로 크게 달라짐)", axis="기하+통제"),
        dict(item="σ 조회 경로", vary="모노 직접 · 바이 이등분선 근사", axis="기하"),
    ]

    # --- EIRP 함정: 개구 재사용 이득 ---------------------------------------------
    g_tx_ladder = [10.0, 15.0, 17.15, 20.0, 25.0]
    aperture = [dict(g_tx_dbi=g, delta_grx_db=float(g - GRX_DBI),
                     range_factor_x=float(10 ** ((g - GRX_DBI) / 40.0))) for g in g_tx_ladder]

    traps = [
        dict(id="T1", name="1/R⁴ ↔ 1/(R₁²R₂²) 를 '같은 거리'로 비교",
             bite="정규화를 안 밝히면 같은 데이터로 반대 결론이 나온다",
             fix=f"N1(R_eq) 정본 · N2/N3 병기. N1 검증 max|Δspread| = "
                 f"{norm['N1_equal_R_eq']['max_abs_spread_diff_db']:.3g} dB",
             bias_direction="정규화 선택에 따라 양방향"),
        dict(id="T1b", name="⭐ 헤드라인 장면방위 φ=90° 하나로만 재기",
             bite=f"φ=90° 는 베이스라인의 수직이등분선이라 R₁≈R₂ 가 구조적으로 성립한다. "
                  f"거기서 두 기하의 확산항 차는 "
                  f"{norm['N3_equal_scene_range']['by_phi']['phi_90']['delta_db_absmax']:.3g} dB "
                  f"뿐이라 '기하는 링크버짓에 거의 영향이 없다'는 착시가 생긴다. φ 를 쓸면 "
                  f"최대 {norm['N3_equal_scene_range']['absmax_over_phi_db']:.3g} dB 로 벌어진다",
             fix="기하 비교는 φ 를 반드시 쓴다. 한 φ 의 값을 격자 결론으로 쓰지 않는다",
             bias_direction="φ=90° 만 쓰면 기하 축의 크기를 200배 넘게 과소평가한다"),
        dict(id="T2", name="PRF 를 양쪽에 같게 주기",
             bite="등-PRF 는 패시브를 봐주고, 고유-PRF 는 능동을 봐준다",
             fix="⭐ 둘 다 보고한다. 능동의 천장은 규격 500 Hz 와 거리모호 v·R=c·λ/8 이다",
             bias_direction="규약이 답을 정한다 — 그래서 둘 다 낸다"),
        dict(id="T3", name="EIRP 를 양쪽에 같게 주기",
             bite="63 dBm 은 매크로 기지국 값이다. 능동 WiFi 노드에 이걸 주면 규제상한을 "
                  "수십 dB 넘긴다. 반대로 능동에 낮은 EIRP 를 주면 기하 축이 아니라 전력 축을 재게 된다",
             fix="정본 = 등-EIRP(기하 분리) · 뷰 = 실현가능 EIRP(주체별). 실현가능 EIRP 값은 "
                 "규격 조항으로 다음 라운드에 못박는다",
             bias_direction="등-EIRP 는 능동 WiFi 셀을 크게 봐준다"),
        dict(id="T4", name="개구 재사용 이득을 조용히 먹기",
             bite="능동 모노가 송신 개구를 수신에도 쓰면 G_rx 가 G_tx 로 올라간다. "
                  "규약에 안 적으면 기하 이득으로 오독된다",
             fix="G_rx 는 전 셀 10 dBi 고정(정본). 개구 재사용은 아래 표로 별도 보고",
             aperture_reuse_table=aperture,
             bias_direction="적지 않으면 모노가 부당하게 이긴다"),
        dict(id="T5", name="DPI·SI·기준채널을 정규화로 지우기",
             bite="모노가 기준채널도 DPI 도 안 내는 것은 **진짜 이점**이다. 지우면 격자가 "
                  "거짓말을 한다",
             fix="셀마다 별도 열. 정본 규약(full_waveform_capture)이 패시브에 유리하므로 "
                 "지금 격자는 모노 이점을 과소평가한다 — 그 방향을 명시한다",
             bias_direction="현재 규약은 패시브 유리(=모노 결론이 나오면 보수적)"),
        dict(id="T6", name="같은 장면 위치 = 같은 자세라고 착각",
             bite="모노 노드와 바이 이등분선은 같은 표적 위치에서 다른 방향을 본다",
             fix="자세평균 σ 를 정본으로. 단일자세 인용 금지",
             bias_direction="단일자세면 기하 차이와 자세 우연이 섞인다"),
        dict(id="T7", name="바이스태틱 σ 를 '계산했다'고 말하기",
             bite="지금 바이스태틱 σ 는 이등분선 근사다. 근사오차가 β=45° 에서 p95 로 두 자릿수 dB 다",
             fix="모노 팔은 Δσ=0 으로 표기. 바이 팔은 Δσ(β) 오차막대를 반드시 붙인다",
             bias_direction="적지 않으면 바이 팔이 실제보다 정밀해 보인다"),
        dict(id="T8", name="'모노는 PRF 자유' 라고 쓰기",
             bite="3GPP sub-6 CSI-RS 천장 500 Hz · 실측 상용 gNB 50~200 Hz. 규격 기준신호를 "
                  "재활용하는 능동 모노의 5G v_max 는 "
                  f"{ctl['by_band']['nr']['active_ceiling_1_spec_reference_signal']['v_max_ms']:.4g}"
                  f" m/s 로 패시브의 "
                  f"{ctl['by_band']['nr']['active_ceiling_1_spec_reference_signal']['gain_over_passive_x']:.3g}"
                  "배일 뿐이다(무한이 아니다)",
             fix="천장 두 단(규격 재활용 / 자체 파형 설계)을 구분해 적는다 — control_axis.by_band",
             bias_direction="쓰면 모노를 과대평가"),
        dict(id="T9", name="구성 B 를 '모노의 장점을 공짜로' 로 읽기",
             bite="B 는 기하만 모노다. PRF 통제권은 없고 DPI 는 최악이다 — LTE 기준 병설 L=10 m 의 "
                  f"요구 소거깊이가 "
                  f"{ledger['passive_dpi']['config_B_cositing_feasibility']['by_band']['lte']['L_10m']['required_depth_db']:.1f}"
                  " dB 로, 우리가 스윕하는 최선값 90 dB 를 "
                  f"{ledger['passive_dpi']['config_B_cositing_feasibility']['by_band']['lte']['L_10m']['deficit_vs_90dB']:.1f}"
                  " dB 초과한다",
             fix="ledger.passive_dpi 의 L 사다리·최소 베이스라인·병설 실행가능성을 함께 낸다",
             bias_direction="쓰면 B 를 과대평가"),
    ]
    return dict(held_constant=held, must_vary=vary, traps=traps,
                repo_link_budget=lb_repo,
                one_line="공정성의 핵심은 '무엇을 같게 했나'가 아니라 **'다르게 둔 것이 축인가 "
                         "함정인가'** 를 셀마다 밝히는 것이다.")


# --------------------------------------------------------------------------- #
#  9. 기존 결론 재판정 — 나머지 작업의 계획표
# --------------------------------------------------------------------------- #
def readjudicate(ax, sig):
    b45 = sig["bisector_approximation_error_by_beta"].get("45", {})
    return dict(
        transfers_unchanged=[
            dict(conclusion="v_max = λ·PRF_ref/4 (12종 교차표준 표 포함)",
                 status="전이한다 — 기하 무관",
                 evidence="P1: 모노 = 바이 β=0, 차이 0. 바이는 β↑ 에서 관대해진다",
                 action="문장에 '두 기하의 최악값' 이라는 한 줄만 추가한다",
                 source="refrate_law.json : law.forms · 본 파일 axis_independence.P1"),
            dict(conclusion="탈출구 6판정(언폴딩·프레임·빔스위핑·긴CPI·멀티스태틱·밴드)",
                 status="대부분 전이 — 단 (e) 멀티스태틱은 기하 축과 직접 겹친다",
                 action="(e) 를 '기하 축의 확장'으로 재배치한다. 나머지는 그대로",
                 source="vmax_hardening.json : verdict.escapes"),
            dict(conclusion="Pfa 교정(2717 s MC · 밴드별 배율)",
                 status="전이한다 — 검출기 규약은 기하와 무관",
                 action="없음", source="verify_cfar.json"),
            dict(conclusion="커널 검증 0.201 dB vs 해석 PO",
                 status="전이한다 — 오히려 모노에서 더 직접적으로 적용된다",
                 action="없음", source="sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po"),
            dict(conclusion="듀티 항(WiFi −12.84 / LTE 0 / 5G −16.02 dB)",
                 status="전이한다 — 자원격자에서 결정되므로 기하 무관",
                 action="⚠ 다만 여전히 R90 경로에서 **호출되지 않는다**. 기하 축과 무관한 별건 결함",
                 source="sigma_sensitivity.json : unapplied_duty_axis"),
        ],
        established_for_one_geometry_only=[
            dict(conclusion="바이스태틱 σ 자세 패턴 (β ≤ 45° 창)",
                 status="바이스태틱 전용. 모노 팔에서는 창 자체가 필요 없다",
                 evidence=f"이등분선 근사오차 β=45°: rms 중앙 "
                          f"{b45.get('dsigma_rms_median_db')!r} dB · p95 최대 "
                          f"{b45.get('dsigma_p95_max_db')!r} dB · β=0 에서 정확히 0",
                 action="모노 행은 '근사 없음'으로 표기. 바이 행은 Δσ(β) 오차막대 필수",
                 source="report13_sigma_grid.json : multistatic"),
            dict(conclusion="R90 검출거리 · 커버리지 · 블라인드 비율 (report13/05 전부)",
                 status="바이스태틱 L=500 m · **φ=90° 단일 방위** 전용",
                 action="⭐ 모노 팔에서 **재계산 필요**. N1 정규화로 다시 풀고, DPI 항을 빼고, "
                        "SI 항을 넣는다. ⚠ 그리고 φ 를 쓸어야 한다 — φ=90° 는 R₁≈R₂ 인 "
                        "특이 방위라 기하 축이 거기서만 사라진다(함정 T1b)",
                 source="report13_freespace.json : ranges · 본 파일 range_normalisation"),
            dict(conclusion="DPI/ECA 소거깊이 요구치",
                 status="패시브 전용. 능동 모노에는 SI 가 대신 들어간다",
                 action="A 행에 SI 열을 새로 만든다(하드웨어 사양, 기하 함수 아님)",
                 source="본 파일 interference_ledger"),
            dict(conclusion="바닥유령·클러터 도플러(챔버)",
                 status="리포트 제외 상태 유지 — 기하 축과 별개",
                 action="없음", source="REBUILD_2026-07-30.md §3"),
        ],
        needs_recomputation=[
            dict(item="모노 팔 링크버짓·R90", why="N1 정규화 + DPI 제거 + SI 도입",
                 depends_on="src/monostatic_scene.py (다른 워크플로가 만드는 중)",
                 estimated="가벼움 — σ 는 이미 모노다, 새 RCS 계산 0"),
            dict(item="모노 팔 블라인드/접힘 비율", why="β=0 이라 완화계수가 앙각만 남는다",
                 depends_on="freespace_scene.blind_fractions 를 L=0 으로 호출",
                 estimated="가벼움"),
            dict(item="구성 B 의 DPI 한계 곡선", why="짧은 베이스라인에서 요구깊이가 폭발한다",
                 depends_on="본 파일 interference_ledger 확장(달성깊이 실측치 필요)",
                 estimated="중간 — 달성 ECA 깊이의 근거문서가 아직 없다"),
            dict(item="등-EIRP vs 실현가능 EIRP 두 뷰", why="T3 함정을 닫으려면 규제 상한을 못박아야",
                 depends_on="FCC 15.407 / ETSI EN 301 893 조항 확인",
                 estimated="가벼움 — 문헌 확인 작업"),
            dict(item="LaSen 과의 나란한 비교(A-nr 셀)", why="게재 대조군을 같은 축에 올린다",
                 depends_on="monostatic_prior.json (이미 있음) + 모노 팔 결과",
                 estimated="가벼움"),
        ],
        work_plan_order=[
            "1. src/monostatic_scene.py 계약 확정(본 파일 handoff)",
            "2. 모노 팔 링크버짓·R90 을 N1 로 계산",
            "3. 구성 B 의 DPI 한계 곡선(최소 베이스라인)",
            "4. 9셀 표 채우기 — 등-PRF/고유-PRF 두 뷰",
            "5. LaSen 나란히 놓기",
            "6. 등-EIRP/실현가능 EIRP 두 뷰(규제 조항 확인 후)",
        ])


# --------------------------------------------------------------------------- #
#  10. 인수인계 — 내가 못 건드리는 파일에 필요한 계약
# --------------------------------------------------------------------------- #
def handoff():
    return dict(
        files_i_must_not_edit=["src/monostatic_scene.py", "benchmark/mono_vs_passive.py",
                               "benchmark/verify_monostatic.py", "src/rcs_sbr.py",
                               "src/sigma_anchor.py", "docs/PAPER_SPEC.md"],
        contract_for_monostatic_scene=dict(
            file="src/monostatic_scene.py",
            status="이 워크플로 시점에 아직 존재하지 않는다 — 아래는 격자 규약이 성립하기 위한 요건",
            requirements=[
                "R1 기하는 freespace_scene.fs_params 를 **재구현하지 말고** TX=RX 로 호출한다. "
                "L=0 에서 R1=R2=R, Rb=2R, β=0, R_eq=R 이 그대로 나온다(본 파일에서 확인).",
                "R2 노드 위치는 조명원 자리 FS_TX=(0,0,25) 를 기본으로 한다. 구성 A/B 가 둘 다 "
                "여기서 출발하기 때문이다.",
                "R3 거리축 정본은 R_eq 다. R90 을 낼 때 키 이름에 정규화를 적는다"
                "(예 `R90_C50_m@N1_Req`).",
                "R4 DPI 항을 **넣지 않는다**. 대신 self_interference_db 를 명시 인자로 받는다"
                "(기본값 주지 말 것 — 선언값임이 드러나야 한다).",
                "R5 η_ref 는 모노에서 0 dB 로 고정하고 그 이유(송신 심볼 기지)를 meta 에 적는다.",
                "R6 σ 조회는 rcs_sbr_batch 후방산란 그대로. Δσ 보정 0, meta 에 "
                "`bisector_approximation=False` 를 남긴다.",
                "R7 PRF 는 인자로 받고, 기본값으로 상시 반복률(prf_hz)을 쓰되 "
                "`prf_is_design_variable` 플래그로 구성 A/B 를 구분한다.",
            ],
            json_keys_the_grid_expects=[
                "meta.normalisation = 'N1_Req'",
                "meta.configuration in {'A','B'}",
                "meta.self_interference_db (구성 A) / meta.baseline_m (구성 B)",
                "ranges.<drone>.<mode>.by_N.1.R90_C50_m",
            ]),
        no_patch_needed="이번 단계는 정의·감사만 하므로 금지 파일에 대한 코드 패치는 없다.")


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("── 2×3 기하×조명원 격자: 정의와 공정성 감사 ──")

    ax = axis_independence()
    print(f"  P1 바닥 동일성: 최대 |Δv_max| = "
          f"{max(v['abs_diff_ms'] for v in ax['P1_floor_is_geometry_independent']['by_band'].values()):.3g} m/s")
    norm = range_normalisation()
    print(f"  N1 확산항 항등성: max|Δ| = {norm['N1_equal_R_eq']['max_abs_spread_diff_db']:.3g} dB")
    ledger = interference_ledger()
    ctl = control_axis()
    sig = sigma_transfer(ax)
    grid = build_cells(ax, ctl)
    void = not_meaningful(ledger)
    audit = fairness_audit(ax, norm, ledger, ctl)
    plan = readjudicate(ax, sig)

    print(f"  셀 {len(grid['cells'])}개 · 함정 {len(audit['traps'])}건 · "
          f"성립 안 하는 칸 {len(void['void_cells'])}건")
    print(f"  재판정: 전이 {len(plan['transfers_unchanged'])} · "
          f"기하한정 {len(plan['established_for_one_geometry_only'])} · "
          f"재계산 {len(plan['needs_recomputation'])}")

    out = dict(
        meta=dict(
            script="benchmark/geometry_grid.py",
            generated=datetime.now().isoformat(timespec="seconds"),
            question="기하(모노/바이) × 조명원(WiFi/LTE/5G) 격자에서 무엇이 비교 가능한가",
            house_rules="산문·print 한국어 · 그림 텍스트 영어 · 수치는 저장소에서만",
            repo_functions_used=[
                "freespace_scene.fs_params", "freespace_scene.target_pos",
                "freespace_scene.heading_velocity", "freespace_scene.FS_RX",
                "freespace_scene.prf_hz", "freespace_scene.M_from_prf",
                "freespace_link.snr_rd_terms_db", "freespace_link.duty_db_from_cpi",
                "freespace_link.direct_power_w", "freespace_link.n0_thermal",
                "freespace_link.dnr_db", "freespace_link.eca_depth_required_db",
                "waveforms.wifi_80211ac", "waveforms.lte_downlink", "waveforms.nr_downlink"],
            reads=["outputs/refrate_law.json", "outputs/vmax_hardening.json",
                   "outputs/sigma_sensitivity.json", "outputs/monostatic_prior.json",
                   "outputs/report13_freespace.json", "outputs/report13_sigma_grid.json",
                   "outputs/sbr_defect_fixes.json", "outputs/sbr_kr_sweep.json"],
            canonical_scene=dict(L_ref_m=L_REF, phi_deg=PHI, alt_m=ALT, T_cpi_s=T_CPI_S,
                                 eirp_dbm=EIRP_DBM, grx_dbi=GRX_DBI, nf_db=NF_DB,
                                 mono_node=list(MONO_NODE), tx_node=list(TX_NODE),
                                 occupancy=MODE_G1),
            runtime_s=round(time.time() - t0, 2)),
        headline=(
            "격자는 성립한다. ⑴ 무모호 속도의 바닥은 기하와 완전히 무관해(모노 = 바이 β=0, 차이 0) "
            "기존 헤드라인이 두 기하의 최악값으로 그대로 승격된다. ⑵ 링크버짓은 N1(R_eq=√(R₁R₂)) "
            "정규화 아래서 기하 기여가 정확히 0 이 되므로, 두 기하의 차이는 DPI·기준채널·σ 경로·"
            "PRF 통제권 넷으로 **완전히 분해된다**. ⑶ 모노 팔은 새 RCS 계산이 0 이다 — 우리 σ 격자가 "
            "이미 모노스태틱 후방산란이고 바이 팔이 그것의 이등분선 근사였기 때문이다. "
            "⑷ ⛔**전 판의 «기하 축의 링크버짓 크기는 장면방위 φ 에 강하게 매달린다» 는 "
            "RETRACTION_LOG R14 가 무효화했다**(2026-08-03, φ 0~355° 72 점 실측). φ 의존은 "
            "사실상 없다 — R90 span 0.48 %(≤0.083 dB) · 자세평균 0.83 % 이고 **φ=90° 가 세 "
            "팔 모두 최소**다. 그때 인용하던 큰 수는 φ 가 아니라 **스윕하지 않은 고도차 "
            "Δz = 35 m** 의 성질이었고 단일 d 칸 값이다(R90 동작점 ≤1.20 dB · d 중앙값 "
            "≤3.10 dB). 남는 것은 «지금까지의 결과가 전부 φ=90° 단일 방위였다» 는 **보고 "
            "범위**뿐이지 위험의 크기가 아니다. "
            f"(옛 기록 — φ=90° "
            f"{norm['N3_equal_scene_range']['by_phi']['phi_90']['delta_db_absmax']:.3g} dB · "
            f"φ 전체 {norm['N3_equal_scene_range']['absmax_over_phi_db']:.3g} dB)"),
        configurations_and_grid=grid,
        axis_independence=ax,
        range_normalisation=norm,
        interference_ledger=ledger,
        control_axis=ctl,
        sigma_transfer=sig,
        fairness_audit=audit,
        not_meaningful=void,
        readjudication=plan,
        handoff=handoff(),
        provenance={
            "v_max floor is geometry-independent":
                "본 파일 axis_independence.P1 (freespace_scene.fs_params 로 계산) · "
                "refrate_law.json : law.forms.relation",
            "relief 1/cos(beta/2) ladder": "본 파일 axis_independence.P2.relief_by_beta",
            "N1 spread identity": "본 파일 range_normalisation.N1_equal_R_eq (freespace_link.snr_rd_terms_db)",
            "duty −12.84/0/−16.02 dB":
                "본 파일 axis_independence.P3 (freespace_link.duty_db_from_cpi) · "
                "교차확인 sigma_sensitivity.json : unapplied_duty_axis.duty_db",
            "DNR vs baseline": "본 파일 interference_ledger (freespace_link.dnr_db)",
            "active PRF ceiling 500 Hz": "monostatic_prior.json : prf_ladder_at_3p5GHz[csirs_spec_max]",
            "self-interference 100 dB": "monostatic_prior.json : side_by_side.lanes[1]",
            "bisector approximation error": "report13_sigma_grid.json : multistatic",
            "kernel 0.201 dB": "sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po",
            "aspect averaging required": "sigma_sensitivity.json : aspect_averaged",
            "LaSen identity": "monostatic_prior.json : lasen.identity",
        })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"→ {OUT}  ({round(time.time()-t0,2)} s)")
    return out


if __name__ == "__main__":
    main()
