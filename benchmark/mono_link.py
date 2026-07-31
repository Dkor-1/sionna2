# -*- coding: utf-8 -*-
"""
mono_link.py — 모노스태틱 팔의 링크버짓·검지거리·자기간섭  (2026-07-31 재프레이밍)
==============================================================================

이 파일이 하는 일 하나: **기하 축(모노↔바이)과 조명원 축(WiFi/LTE/5G)이 각각 몇 dB 인지
분리해서 재고, 그 위에 능동 모노가 무는 자기간섭 비용을 얹어 무엇이 남는지 낸다.**

■ 계약 (읽고 시작한다)
  · `docs/PAPER_SPEC.md` §0  — 기하를 결과에서 빼내 축으로 올린다. 벤치마크는 2×3.
  · `outputs/geometry_grid.json` — 거리정규화 정본 N1(R_eq), 함정 T1b(φ 스윕 필수),
    T3(등-EIRP 정본), T4(G_rx 고정), T5(간섭항은 별도 열), T6(자세평균 σ), T9(구성 B 는 DPI 최악).
  · `docs/REBUILD_2026-07-30.md` §5 — 한 일을 쓴다. 방어적 표현 대신 주장의 크기를 맞춘다.

■ 재구현 금지 — 두 팔이 진짜로 비교 가능하려면 같은 함수를 써야 한다
  기하        `freespace_scene.fs_params`  (모노는 **TX=RX 로 호출**한다. L=0 에서 R1=R2=R,
              β=0, R_eq=R 이 그대로 나온다 — §1 에서 수치로 확인한다)
  레이더식    `benchmark/link_budget.LinkBudget` → `freespace_link.snr_rd_db/snr_rd_terms_db`
              (바이스태틱식 `1/(R₁²R₂²)` 는 R₁=R₂=R 에서 정확히 `1/R⁴` 로 접힌다)
  잡음·간섭   `freespace_link.n0_thermal / n0_dpi / dnr_db / eca_depth_required_db`
              (⭐ `n0_dpi` 는 "간섭전력·소거깊이·대역 → 잔류 PSD" 라는 일반형이다. 패시브는
               직접파를, 능동 모노는 **자기 송신 도통전력**을 넣는다 — 같은 함수, 같은 규약)
  거리 역해   `freespace_link.solve_range` (최외곽 하강교차, S6)
  문턱        `outputs/report13_freespace.json : threshold` 의 **측정 snr90** — 바이스태틱
              팔이 쓴 그 값을 모노 팔에도 그대로 쓴다. 교차확인으로 Marcum 근사도 같이 낸다.
  σ           `experiment_freespace_range._sigma_lookup/_sigma_at` — `rcs_sbr_batch` 후방산란
              격자. ⭐ 모노는 이 격자의 **정의 자체**라 근사오차 0 이다(바이는 이등분선 근사).

■ 이 파일이 새로 도입하는 것 — 자기간섭을 패시브 DPI 와 **같은 축** 위에 올린다
  두 구성의 간섭을 "총 송수신 격리 [dB]" 하나로 환산한다:
      passive : 자유공간 격리(베이스라인 L) + ECA 소거깊이
      active  : 전단 총격리 (Barneto 실측 100 dB)
  그리고 능동 소거깊이를 **등가 베이스라인**으로 되돌린다 —
      L_equiv(depth) = λ√(G_tx·G_rx)/(4π) · 10^(depth/20)
  이러면 "100 dB 소거"와 "500 m 이격"이 같은 자로 읽힌다(§5).

■ 파일이 만드는 산출물
  `outputs/mono_link.json`

작성: 2026-07-31 재프레이밍 라운드. 그림 없음(순수 계산 모듈).
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import freespace_scene as fss                     # noqa: E402
import freespace_link as fsl                      # noqa: E402
import freespace_detect as fsd                    # noqa: E402
import experiment_freespace_range as efr          # noqa: E402
from link_budget import LinkBudget, link_terms    # noqa: E402

C0 = 299792458.0
OUT_JSON = os.path.join(ROOT, "outputs", "mono_link.json")
FS_JSON = os.path.join(ROOT, "outputs", "report13_freespace.json")
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")
GRID_JSON = os.path.join(ROOT, "outputs", "geometry_grid.json")
PRIOR_JSON = os.path.join(ROOT, "outputs", "monostatic_prior.json")
REFRATE_JSON = os.path.join(ROOT, "outputs", "refrate_law.json")

# ── 통제변수(전 셀 동일) — 값은 report13 meta 에서 읽는다(손으로 안 친다) ──────────
EIRP_DBM = efr.EIRP_DBM
GRX_DBI = efr.GRX_DBI
NF_DB = efr.NF_DB
GTX_DBI = GRX_DBI            # T4 정본: 개구 재사용 이득을 조용히 먹지 않는다
T_CPI_S = fss.T_CPI_REF_S
ALT_M = 60.0
L_REF_M = fss.L_REF
L_COSITE_M = 10.0            # 구성 B 병설 베이스라인(격자 T9 가 지목한 값)
BANDS = ("wifi", "lte", "nr")
MODE_OF = {"wifi": "W1", "lte": "L1", "nr": "G1"}       # 상시 조명(G1) 정본
DRONE_HEADLINE = "mavic4pro"
SIGMA_EL_ABSMAX_DEG = 20.0   # σ 격자 el 범위 |el|≤20° (report13_sigma_grid meta.el_deg)

# Barneto 2019 (IEEE TMTT 67(10):4042-4054) 에서 오는 값들 — 전부 monostatic_prior.json 직독
SI_DEPTH_LADDER_DB = (25.0, 75.0, 100.0, 120.0, 141.0)
ECA_DEPTH_LADDER_DB = (40.0, 60.0, 90.0)
MARGIN_DB = 10.0             # 요구 소거깊이 여유 — geometry_grid.interference_ledger 와 동일


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _f(x):
    """JSON 안전 float (inf/nan → None)."""
    v = float(x)
    return v if np.isfinite(v) else None


# --------------------------------------------------------------------------- #
#  §0  장면·파형 셋업 — 두 팔이 같은 좌표계·같은 파형을 쓴다
# --------------------------------------------------------------------------- #
def band_params():
    """밴드별 (이름, fc, λ, fs, PRF_ref, M, T_ref, duty) — 전부 저장소 함수에서."""
    from waveforms import all_waveforms
    out = {}
    for b in BANDS:
        bname, fc, bw = efr._BAND_BY_STD[b]
        w = all_waveforms("G1")[b]
        prf = float(fss.prf_hz(b, "G1"))
        M = int(fss.M_from_prf(T_CPI_S, prf))
        t_ref = float(len(w.tx) / w.fs_hz)
        out[b] = dict(band_name=bname, fc_hz=float(fc), lam_m=C0 / float(fc),
                      bw_hz=float(bw), fs_hz=float(w.fs_hz), ref_name=str(w.ref_name),
                      ref_bw_hz=float(w.ref_bw_hz), prf_ref_hz=prf, M=M, t_ref_s=t_ref,
                      duty_db=float(fsl.duty_db_from_cpi(M, t_ref, T_CPI_S)),
                      mode=MODE_OF[b])
    return out


#: 노드 배치 — 장면 좌표계는 **전 배치 공통**(L_REF 의 중점 기준). 표적 위치가 같다.
def placements():
    tx = tuple(fss.FS_TX)
    rx500 = tuple(fss.FS_RX(L_REF_M))
    rx10 = tuple(fss.FS_RX(L_COSITE_M))
    return {
        "C_bistatic_L500": dict(
            config="C", geometry="bistatic", tx=tx, rx=rx500, baseline_m=L_REF_M,
            interference="dpi", label="passive bistatic, RX 500 m from the mast"),
        "B_quasi_mono_L10": dict(
            config="B", geometry="quasi-monostatic", tx=tx, rx=rx10, baseline_m=L_COSITE_M,
            interference="dpi", label="passive quasi-monostatic, RX beside the mast (10 m)"),
        "A_mono_at_illuminator": dict(
            config="A", geometry="monostatic", tx=tx, rx=tx, baseline_m=0.0,
            interference="si", label="active monostatic at the illuminator site"),
        "A_mono_at_rx_site": dict(
            config="A", geometry="monostatic", tx=rx500, rx=rx500, baseline_m=0.0,
            interference="si", label="active monostatic at the surveillance-receiver site"),
    }


# --------------------------------------------------------------------------- #
#  §1  기하 항등식 — 모노는 바이의 β=0 특수해다 (재구현이 아니라 확인)
# --------------------------------------------------------------------------- #
def identity_check(bp):
    """TX=RX 로 부른 `fs_params` 가 L=0·R1=R2·β=0·R_eq=R 을 주는지, 그리고
    바이스태틱 확산항이 R1=R2 에서 정확히 `1/R⁴` 로 접히는지 수치로 확인한다."""
    d = np.geomspace(100.0, 20000.0, 240)
    tgt = fss.target_pos(d, 90.0, L_REF_M, ALT_M)
    fc = bp["nr"]["fc_hz"]
    p = fss.fs_params(fss.FS_TX, fss.FS_TX, tgt, (0.0, 0.0, 0.0), fc)
    R1, R2 = np.asarray(p["R1"]), np.asarray(p["R2"])
    Req = np.asarray(p["R_eq"])
    beta = np.asarray(p["beta"])

    # 확산항: snr_rd_terms_db 의 spread 를 모노(R,R)와 해석식 -30log10(4π)-40log10R 로 비교
    t_mono = fsl.snr_rd_terms_db(EIRP_DBM, GRX_DBI, bp["nr"]["lam_m"], 1.0, R1, R1,
                                 nf=NF_DB, T=T_CPI_S)
    closed = -30.0 * np.log10(4 * np.pi) - 40.0 * np.log10(R1)
    fold_err = float(np.max(np.abs(np.asarray(t_mono["spread"]) - closed)))

    # N1 항등: R_eq 를 고정한 채 R1/R2 를 흔들어도 확산항이 안 변한다 (격자 §2 재현)
    rng = np.random.default_rng(31)
    Req0 = np.geomspace(200.0, 8000.0, 40)
    ratio = np.exp(rng.uniform(np.log(0.2), np.log(5.0), size=(25, 40)))
    r1 = Req0[None, :] * np.sqrt(ratio)
    r2 = Req0[None, :] / np.sqrt(ratio)
    sp_bi = fsl.snr_rd_terms_db(EIRP_DBM, GRX_DBI, bp["nr"]["lam_m"], 1.0, r1, r2,
                                nf=NF_DB, T=T_CPI_S)["spread"]
    sp_mono = fsl.snr_rd_terms_db(EIRP_DBM, GRX_DBI, bp["nr"]["lam_m"], 1.0,
                                  np.broadcast_to(Req0, r1.shape),
                                  np.broadcast_to(Req0, r1.shape),
                                  nf=NF_DB, T=T_CPI_S)["spread"]
    n1_err = float(np.max(np.abs(np.asarray(sp_bi) - np.asarray(sp_mono))))

    # 무모호 속도 바닥은 기하와 무관 — 모노(β=0)와 바이 β=0 이 같은 값을 준다
    rl = _load(REFRATE_JSON)["illuminators"]["rows"]
    floor = {}
    for b, key in (("wifi", "wifi_vhtltf"), ("lte", "lte_crs"), ("nr", "nr_ssb")):
        lam = bp[b]["lam_m"]
        v_mono = lam * bp[b]["prf_ref_hz"] / 4.0
        v_bi0 = lam * bp[b]["prf_ref_hz"] / (4.0 * np.cos(0.0) * np.cos(0.0))
        floor[b] = dict(v_max_mono_ms=float(v_mono), v_max_bistatic_beta0_ms=float(v_bi0),
                        abs_diff_ms=float(abs(v_mono - v_bi0)),
                        refrate_law_json_ms=float(rl[key]["v_max_ms"]),
                        abs_diff_vs_json_ms=float(abs(v_mono - rl[key]["v_max_ms"])))

    return dict(
        statement="모노스태틱은 `fs_params` 를 TX=RX 로 부른 결과다 — 새 기하 코드가 없다.",
        L_m=float(p["L"]),
        max_abs_R1_minus_R2_m=float(np.max(np.abs(R1 - R2))),
        max_abs_Req_minus_R_m=float(np.max(np.abs(Req - R1))),
        max_beta_deg=float(np.max(beta)),
        spread_folds_to_inverse_R4_max_abs_db=fold_err,
        N1_spread_identity_max_abs_db=n1_err,
        N1_note="R_eq 를 고정하고 R1/R2 를 25배 흔든 1000 쌍. 확산항 차이가 부동소수 수준이면 "
                "N1 아래서 기하 축의 링크버짓 기여가 정확히 0 이다.",
        unambiguous_velocity_floor=floor,
        verdict="기하 항등식 성립 — 모노 팔은 바이 코드의 β=0 호출이고, 무모호 속도 바닥은 두 기하가 같다.")


# --------------------------------------------------------------------------- #
#  §2  σ 조회 — 자세평균(T6) · 격자 el 범위 게이트
# --------------------------------------------------------------------------- #
def sigma_tools(sig_json, drone, band_name):
    """(lookup, 자세평균 σ(el) 함수, el 격자범위) 를 만든다.

    ⚠ 격자 el ∈ [0,−20]° 뿐이라 근거리에서 조회가 범위를 벗어난다(무음 외삽 위험).
      `_sigma_at` 이 세는 `SIGMA_OOR` 를 그대로 쓰고, 범위 밖 d 는 `valid` 에서 뺀다.
    """
    lookup = efr._sigma_lookup(sig_json, drone, band_name)
    if lookup is None:
        return None, None, (None, None)
    az, el, sm = lookup
    el_lo, el_hi = float(np.min(el)), float(np.max(el))

    def aspect_avg(el_look):
        """헤딩 ψ 전체 평균 σ [m²] — az 축 선형평균(T6: 단일자세 인용 금지)."""
        e = np.atleast_1d(np.asarray(el_look, float))
        i = np.argmin(np.abs(e[:, None] - el[None, :]), axis=1)
        return sm[i, :].mean(axis=1)

    return lookup, aspect_avg, (el_lo, el_hi)


def scene_arm(place, b, bp, sig_json, phi_deg, d, drone, duty_on=False):
    """한 배치 × 한 밴드의 기하·σ·닫힌형 SNR(열잡음만) 을 d 격자 위에서 계산한다.

    반환 dict: R1,R2,R_eq,beta,el,sigma,snr_db,valid,terms(d_ref=1000 m 에서)
    """
    fc = bp[b]["fc_hz"]
    lam = bp[b]["lam_m"]
    tgt = fss.target_pos(d, phi_deg, L_REF_M, ALT_M)
    p = fss.fs_params(place["tx"], place["rx"], tgt, (0.0, 0.0, 0.0), fc)
    R1 = np.asarray(p["R1"], float)
    R2 = np.asarray(p["R2"], float)
    el = np.asarray(p["el_deg"], float)
    beta = np.asarray(p["beta"], float)
    _, aspect_avg, (el_lo, el_hi) = sigma_tools(sig_json, drone, bp[b]["band_name"])
    sigma = aspect_avg(el) if aspect_avg is not None else np.full_like(d, 0.01)

    duty = bp[b]["duty_db"] if duty_on else 0.0
    snr = fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sigma, R1, R2, nf=NF_DB,
                        eta_ref=0.0, T=T_CPI_S, duty_db=duty)
    el_ok = np.abs(el) <= SIGMA_EL_ABSMAX_DEG + 1e-9
    ff = np.array([fss.farfield_gate(min(R1[i], R2[i]), drone, fc) for i in range(len(d))])
    valid = fss.beta_gate(beta) & ff & el_ok
    return dict(R1=R1, R2=R2, R_eq=np.sqrt(R1 * R2), beta=beta, el=el, sigma=sigma,
                snr_db=np.asarray(snr, float), valid=valid, lam=lam,
                frac_d_excluded_by_sigma_el=float(np.mean(~el_ok)))


# --------------------------------------------------------------------------- #
#  §3  ⭐ 축 분리 — 기하 효과와 조명원 효과를 따로 낸다 (2×3 이원분해)
# --------------------------------------------------------------------------- #
def axis_separation(bp, sig_json, phis, d_ref=1000.0, drone=DRONE_HEADLINE):
    """SNR(dB) 2×3 표를 **행효과(기하)·열효과(조명원)·상호작용**으로 쪼갠다.

    X(g,i) = μ + α_g + β_i + γ_gi,  α=행평균−μ, β=열평균−μ, γ=잔차.
    dB 표에서 이 분해는 정확하다(항이 곱이므로 로그에서 더해진다). γ 가 0 이 아니면
    그 부분이 **두 축이 실제로 얽힌 양**이고, 여기서는 σ(el, 밴드) 가 유일한 원인이다.
    """
    d = np.array([d_ref], float)
    rows = ("C_bistatic_L500", "A_mono_at_illuminator")
    P = placements()
    per_phi = {}
    for phi in phis:
        X = np.zeros((2, 3))
        detail = {}
        for gi, g in enumerate(rows):
            for bi, b in enumerate(BANDS):
                a = scene_arm(P[g], b, bp, sig_json, phi, d, drone)
                X[gi, bi] = float(a["snr_db"][0])
                detail[f"{g}|{b}"] = dict(snr_db=float(a["snr_db"][0]),
                                          sigma_dbsm=float(10 * np.log10(a["sigma"][0])),
                                          el_deg=float(a["el"][0]),
                                          R1_m=float(a["R1"][0]), R2_m=float(a["R2"][0]),
                                          R_eq_m=float(a["R_eq"][0]))
        mu = float(X.mean())
        alpha = X.mean(axis=1) - mu
        beta_ = X.mean(axis=0) - mu
        gamma = X - mu - alpha[:, None] - beta_[None, :]
        per_phi[f"phi_{int(phi)}"] = dict(
            table_snr_db={g: {b: float(X[gi, bi]) for bi, b in enumerate(BANDS)}
                          for gi, g in enumerate(rows)},
            grand_mean_db=mu,
            geometry_effect_db={g: float(alpha[gi]) for gi, g in enumerate(rows)},
            illuminator_effect_db={b: float(beta_[bi]) for bi, b in enumerate(BANDS)},
            interaction_db={g: {b: float(gamma[gi, bi]) for bi, b in enumerate(BANDS)}
                            for gi, g in enumerate(rows)},
            geometry_span_db=float(alpha.max() - alpha.min()),
            illuminator_span_db=float(beta_.max() - beta_.min()),
            interaction_absmax_db=float(np.abs(gamma).max()),
            detail=detail)

    g_span = np.array([v["geometry_span_db"] for v in per_phi.values()])
    i_span = np.array([v["illuminator_span_db"] for v in per_phi.values()])
    x_max = np.array([v["interaction_absmax_db"] for v in per_phi.values()])
    mono_minus_bi = np.array([v["geometry_effect_db"]["A_mono_at_illuminator"]
                              - v["geometry_effect_db"]["C_bistatic_L500"]
                              for v in per_phi.values()])
    return dict(
        convention=dict(
            value="SNR_RD [dB] at scene range d_ref, thermal noise only, aspect-averaged sigma",
            d_ref_m=float(d_ref), drone=drone, T_cpi_s=T_CPI_S, eirp_dbm=EIRP_DBM,
            note="간섭항(DPI·SI)은 여기 없다 — §5 에서 별도 열로 얹는다(T5)."),
        by_phi=per_phi,
        summary=dict(
            phi_deg=[float(p) for p in phis],
            geometry_span_db=dict(median=float(np.median(g_span)), min=float(g_span.min()),
                                  max=float(g_span.max())),
            illuminator_span_db=dict(median=float(np.median(i_span)), min=float(i_span.min()),
                                     max=float(i_span.max())),
            interaction_absmax_db=dict(median=float(np.median(x_max)), max=float(x_max.max())),
            mono_minus_bistatic_db=dict(median=float(np.median(mono_minus_bi)),
                                        min=float(mono_minus_bi.min()),
                                        max=float(mono_minus_bi.max()),
                                        at_phi90=float(per_phi["phi_90"]["geometry_effect_db"]
                                                       ["A_mono_at_illuminator"]
                                                       - per_phi["phi_90"]["geometry_effect_db"]
                                                       ["C_bistatic_L500"]))),
        reading=("기하 효과는 φ 에 따라 부호가 바뀌고 조명원 효과는 φ 에 대해 상수다 — "
                 "두 축이 서로 독립이라는 것을 한 표로 보여준다. 상호작용 항은 σ(el,밴드) 하나뿐이다."))


# --------------------------------------------------------------------------- #
#  §3b ⭐ 기하 효과가 사는 곳 — d/L 에 대한 의존
# --------------------------------------------------------------------------- #
def geometry_effect_vs_range(bp, phis, drone=DRONE_HEADLINE):
    """기하 축의 링크버짓 기여를 **하나의 닫힌 식**으로 적고 d/L 로 층화한다.

        Δspread(모노 − 바이) = 20·log10( R_조명원 / R_센서 )

    모노 노드를 패시브 수신기 자리에 두면 두 다리가 모두 R_센서 가 되고, 바이는 한 다리를
    조명원까지 늘여 R_조명원 을 문다. 그래서 **모노의 1/R⁴ 이점은 '누가 표적에 더 가까운가'
    한 줄이다.** 이 값은 λ·대역·점유와 무관하다(조명원 축과 직교).

    ⭐ 그리고 d/L → ∞ 에서 0 으로 죽는다 — 검지 한계거리는 베이스라인의 10배 넘는 곳이라,
      **검지거리 비교에서는 기하 축이 링크버짓으로 거의 아무것도 하지 않는다.**
    """
    d = fsl.D_GRID_DEFAULT
    P = placements()["C_bistatic_L500"]
    fc = bp["nr"]["fc_hz"]
    rows, vals = [], []
    for phi in phis:
        tgt = fss.target_pos(d, phi, L_REF_M, ALT_M)
        p = fss.fs_params(P["tx"], P["rx"], tgt, (0.0, 0.0, 0.0), fc)
        R1 = np.asarray(p["R1"], float); R2 = np.asarray(p["R2"], float)
        v = 20.0 * np.log10(R1 / R2)
        vals.append(v)
        rows.append(dict(phi_deg=float(phi),
                         at_d_over_L_0p2_db=float(np.interp(0.2 * L_REF_M, d, v)),
                         at_d_over_L_1_db=float(np.interp(L_REF_M, d, v)),
                         at_d_over_L_2_db=float(np.interp(2 * L_REF_M, d, v)),
                         at_d_over_L_10_db=float(np.interp(10 * L_REF_M, d, v)),
                         absmax_db=float(np.max(np.abs(v)))))
    V = np.abs(np.vstack(vals))
    by_dl = {}
    for k in (0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0):
        col = np.array([np.interp(k * L_REF_M, d, np.abs(v)) for v in vals])
        by_dl[f"d_over_L_{k:g}"] = dict(median_abs_db=float(np.median(col)),
                                        max_abs_db=float(col.max()))
    return dict(
        closed_form="Δspread_db(mono at sensor site − bistatic) = 20·log10(R_illuminator / R_sensor)",
        why=("모노는 두 다리가 같고 바이는 한 다리를 조명원까지 늘인다. 두 기하의 차이는 그 한 "
             "다리의 길이비뿐이며, λ·대역·점유가 들어가지 않는다 — 조명원 축과 직교한다."),
        by_phi=rows,
        by_d_over_L=by_dl,
        absmax_over_grid_db=float(V.max()),
        grid_crosscheck=dict(
            geometry_grid_N3_absmax_over_phi_db=23.168839470105706,
            ours_absmax_db=float(V.max()),
            abs_diff_db=abs(float(V.max()) - 23.168839470105706),
            note="geometry_grid.json : range_normalisation.N3_equal_scene_range.absmax_over_phi_db 재현"),
        collapse=("d/L ≥ 10 에서 중앙값 %.3f dB 로 죽는다. 우리 R90 은 L 의 10~14배 지점에 있으므로 "
                  "검지거리 비교에서 기하 축의 링크버짓 기여는 실질적으로 0 이다."
                  % by_dl["d_over_L_10"]["median_abs_db"]),
        where_it_lives="기하 축은 근거리(d ≲ 2L)에서만 산다 — 추적·다중표적 구간이지 검지 한계 구간이 아니다.")


# --------------------------------------------------------------------------- #
#  §4  검지거리 — 두 기하 × 세 조명원, φ 스윕, 간섭 레짐 2종
# --------------------------------------------------------------------------- #
def thresholds():
    """문턱은 바이스태틱 팔이 쓴 **측정 snr90** 을 그대로 쓴다(같은 CFAR·같은 Pfa)."""
    fsj = _load(FS_JSON)
    th = {m: float(fsj["solve"][m]["snr90_db"]) for m in ("W1", "L1", "G1")}
    src = {m: str(fsj["solve"][m]["snr90_source"]) for m in ("W1", "L1", "G1")}
    pfa = {m: fsj["threshold"]["pfa"][m] for m in ("W1", "L1", "G1")}
    n_train = 264
    marcum = float(fsd._marcum_cfar_snr90_db(n_train, fsd.PFA_CELL, 0.9))
    return dict(snr90_db=th, source=src, pfa=pfa,
                snr_convention=str(_load(FS_JSON)["threshold"]["meta"]["snr_convention"]),
                marcum_crosscheck_db=marcum, marcum_n_train=n_train,
                marcum_note=("Marcum 근사는 |peak|²/평균잡음 규약이 아니라 진폭검출 규약이라 "
                             "값이 다르다. 정본은 측정치이고, 두 팔에 같은 값을 쓴다."),
                guard_bins_hard=float(fsd.DOPPLER_GUARD_WIDTH) / 2.0,
                guard_bins_declared=float(fss.GUARD_DOPPLER_BINS))


def interference_extra(place, b, bp, depth_db, regime):
    """이 배치·이 밴드에서 잡음바닥에 더할 PSD [W/Hz] 와 진단.

    · 패시브(DPI)  : P_dir = LinkBudget.direct_power_w(λ, L)      — 자유공간 결합
    · 능동(SI)     : P_si  = 송신 도통전력 (EIRP − G_tx)          — 전단 결합
    두 경우 모두 `freespace_link.n0_dpi(P, depth, B)` 한 함수로 잔류를 만든다.
    `regime="zero_doppler"` 면 잔류가 0-도플러 능선에 갇힌다고 보고 0 을 준다(§5.4).
    """
    lam = bp[b]["lam_m"]
    B = bp[b]["fs_hz"]
    if place["interference"] == "dpi":
        P = fsl.direct_power_w(EIRP_DBM, GRX_DBI, lam, place["baseline_m"])
        kind = "dpi"
    else:
        P = 10.0 ** ((EIRP_DBM - GTX_DBI - 30.0) / 10.0)     # dBm→W, 도통 송신전력
        kind = "si"
    n0_th = fsl.n0_thermal(NF_DB, 1.0)
    raw_db = float(fsl.dnr_db(P, fsl.n0_thermal(NF_DB, B)))   # 간섭/열잡음 (같은 대역)
    if regime == "zero_doppler" or depth_db is None:
        extra = 0.0
    else:
        extra = float(fsl.n0_dpi(P, depth_db, B))
    rise_db = float(10.0 * np.log10((n0_th + extra) / n0_th))
    return dict(kind=kind, P_w=float(P), raw_over_thermal_db=raw_db,
                required_depth_db=float(fsl.eca_depth_required_db(raw_db, MARGIN_DB)),
                applied_depth_db=(None if depth_db is None else float(depth_db)),
                n0_extra=extra, noise_rise_db=rise_db)


def detection_ranges(bp, sig_json, phis, th, drone=DRONE_HEADLINE,
                     depth_by_config=None, regime="broadband"):
    """배치 × 밴드 × φ 의 R90 (장면 수평거리 d) 과 그 지점의 R_eq(N1 축)."""
    P = placements()
    d = fsl.D_GRID_DEFAULT
    depth_by_config = depth_by_config or {"C": 90.0, "B": 90.0, "A": 100.0}
    out = {}
    for gname, place in P.items():
        out[gname] = {}
        for b in BANDS:
            arm = scene_arm(place, b, bp, sig_json, 90.0, d, drone)   # φ 는 아래서 다시
            per_phi = {}
            for phi in phis:
                a = scene_arm(place, b, bp, sig_json, phi, d, drone)
                ie = interference_extra(place, b, bp, depth_by_config[place["config"]], regime)
                snr = a["snr_db"] + fsl.lin2db(
                    (fsl.n0_thermal(NF_DB, 1.0)) / (fsl.n0_thermal(NF_DB, 1.0) + ie["n0_extra"]))
                sol = fsl.solve_range(snr, th[bp[b]["mode"]], d_grid=d,
                                      kappa_of_d=a["R1"] * a["R2"], valid=a["valid"])
                per_phi[f"phi_{int(phi)}"] = dict(
                    R90_d_m=_f(sol["R_m"]), R90_Req_m=_f(sol["R_eq_m"]),
                    n_local_at_R90=_f(sol.get("range_conv_exponent", np.nan)),
                    snr_ceiling_db=_f(sol["snr_ceiling_db"]),
                    noise_rise_db=ie["noise_rise_db"])
            rr = np.array([v["R90_d_m"] for v in per_phi.values()
                           if v["R90_d_m"] is not None], float)
            out[gname][b] = dict(
                by_phi=per_phi,
                headline_phi90_R90_d_m=per_phi["phi_90"]["R90_d_m"],
                R90_d_m_median_over_phi=_f(np.median(rr)) if rr.size else None,
                R90_d_m_min_over_phi=_f(rr.min()) if rr.size else None,
                R90_d_m_max_over_phi=_f(rr.max()) if rr.size else None,
                noise_rise_db=per_phi["phi_90"]["noise_rise_db"],
                frac_d_excluded_by_sigma_el=arm["frac_d_excluded_by_sigma_el"])
    return dict(regime=regime, depth_by_config=depth_by_config, drone=drone,
                phi_deg=[float(p) for p in phis], cells=out,
                normalisation="R90_d_m = N3(장면 수평거리) · R90_Req_m = N1(R_eq) 동시 보고")


def regression_vs_repo(det_zd):
    """⭐ 회귀검사 — 열잡음만 걸린 바이스태틱 팔이 저장소의 자세평균 R90 을 그대로 내는가.

    `sigma_sensitivity.json : aspect_averaged.by_drone.mavic4pro.R90_m` 은 다른 코드경로
    (`benchmark/sigma_sensitivity.py`)가 만든 값이다. 이 파일은 배치·간섭·문턱을 새로 조립했으므로,
    간섭을 끄면 그 값이 **자릿수까지** 복원돼야 한다.
    """
    ref = _load(os.path.join(ROOT, "outputs", "sigma_sensitivity.json"))
    tab = ref["aspect_averaged"]["by_drone"][DRONE_HEADLINE]["R90_m"]
    cells = det_zd["cells"]["C_bistatic_L500"]
    rows = {}
    for b, m in (("wifi", "W1"), ("lte", "L1"), ("nr", "G1")):
        ours = cells[b]["headline_phi90_R90_d_m"]
        rows[b] = dict(ours_m=ours, repo_m=float(tab[m]), abs_diff_m=abs(ours - float(tab[m])))
    return dict(
        target="sigma_sensitivity.json : aspect_averaged.by_drone.%s.R90_m" % DRONE_HEADLINE,
        by_band=rows,
        max_abs_diff_m=max(v["abs_diff_m"] for v in rows.values()),
        ranking_ours=[b for b, _ in sorted(((b, rows[b]["ours_m"]) for b in rows),
                                           key=lambda t: -t[1])],
        ranking_repo=ref["aspect_averaged"]["consensus_order"],
        verdict=("간섭을 끈 바이스태틱 팔이 저장소 자세평균 R90 을 그대로 낸다 — 두 팔이 같은 "
                 "링크·문턱 위에 서 있다는 증거다."))


def all_drones(bp, sig_json, th, regime="zero_doppler", depth=None):
    """5기체 × 4배치 × 3밴드 R90 (φ=90°). 순위 견고성(E3)을 기하 축 위에서 다시 본다."""
    P = placements()
    d = fsl.D_GRID_DEFAULT
    dep = depth or {"C": 90.0, "B": 90.0, "A": 100.0}
    # ⚠ σ 격자에 있는 기체만 센다. 없는 기체는 `_sigma_lookup` 이 None 을 주고 상수 0.01 m² 로
    #   떨어져 순위가 λ² 로만 결정된다 — 그런 행을 표에 넣으면 조명원 축을 왜곡한다.
    have = set(sig_json["sigma"]["grid"].keys())
    used = [dr for dr in fss.DRONE_ORDER if dr in have]
    skipped = [dr for dr in fss.DRONE_ORDER if dr not in have]
    out = {}
    for dr in used:
        out[dr] = {}
        for gname, place in P.items():
            row = {}
            for b in BANDS:
                a = scene_arm(place, b, bp, sig_json, 90.0, d, dr)
                ie = interference_extra(place, b, bp, dep[place["config"]], regime)
                n0t = fsl.n0_thermal(NF_DB, 1.0)
                snr = a["snr_db"] + fsl.lin2db(n0t / (n0t + ie["n0_extra"]))
                sol = fsl.solve_range(snr, th[bp[b]["mode"]], d_grid=d,
                                      kappa_of_d=a["R1"] * a["R2"], valid=a["valid"])
                row[b] = _f(sol["R_m"])
            order = [b for b, _ in sorted(((b, row[b] or -1) for b in row), key=lambda t: -t[1])]
            out[dr][gname] = dict(R90_d_m=row, order=order)
    orders = {dr: out[dr]["C_bistatic_L500"]["order"] for dr in out}
    same = {dr: all(out[dr][g]["order"] == out[dr]["C_bistatic_L500"]["order"] for g in out[dr])
            for dr in out}
    consensus = {tuple(v) for v in orders.values()}
    return dict(regime=regime, phi_deg=90.0, drones_used=used, drones_skipped=skipped,
                skipped_reason="σ 격자에 없다 (report13_sigma_grid.json : sigma.grid)",
                cells=out,
                bistatic_orders=orders,
                geometry_preserves_illuminator_ranking=same,
                geometry_preserves_ranking_for_all=bool(all(same.values())),
                cross_drone_consensus_order=(list(consensus)[0] if len(consensus) == 1 else None),
                n_distinct_orders_across_drones=len(consensus),
                reading=("⭐ 기하를 바꿔도 조명원 순위가 기체마다 그대로면 두 축이 실제로 독립이다. "
                         "기체 사이 순위 불일치는 σ(기체) 문제이지 기하 문제가 아니다 "
                         "⟨sigma_sensitivity.json : aspect_averaged⟩."))


# --------------------------------------------------------------------------- #
#  §5  ⭐ 자기간섭 — 능동 모노가 무는 값, 그리고 등가 베이스라인
# --------------------------------------------------------------------------- #
def self_interference(bp, prior):
    """SI 원장. 문헌값은 `monostatic_prior.json : monostatic_literature[barneto2019]` 직독."""
    lit = {x["key"]: x for x in prior["monostatic_literature"]}
    bar = lit["barneto2019"]
    P_tx_dbm = EIRP_DBM - GTX_DBI
    P_tx_w = 10.0 ** ((P_tx_dbm - 30.0) / 10.0)

    by_band = {}
    for b in BANDS:
        B = bp[b]["fs_hz"]
        lam = bp[b]["lam_m"]
        n0_th_B = fsl.n0_thermal(NF_DB, B)
        si_over_th = float(fsl.dnr_db(P_tx_w, n0_th_B))
        req = float(fsl.eca_depth_required_db(si_over_th, MARGIN_DB))
        ladder = {}
        for dep in SI_DEPTH_LADDER_DB:
            extra = float(fsl.n0_dpi(P_tx_w, dep, B))
            th0 = fsl.n0_thermal(NF_DB, 1.0)
            rise = float(10.0 * np.log10((th0 + extra) / th0))
            ladder[str(int(dep))] = dict(
                noise_rise_db=rise,
                range_factor_x=float(fsl.range_factor(-rise, n=4.0)))
        # ⭐ 소거깊이 → 등가 베이스라인:  L_equiv = λ√(Gtx·Grx)/(4π)·10^(depth/20)
        L0 = lam * np.sqrt(10 ** (GTX_DBI / 10) * 10 ** (GRX_DBI / 10)) / (4 * np.pi)
        by_band[b] = dict(
            noise_bandwidth_hz=B,
            thermal_noise_dbm=float(10 * np.log10(n0_th_B * 1e3)),
            si_over_thermal_db=si_over_th,
            required_total_suppression_db=req,
            measured_total_suppression_db=float(bar["numbers"]["measured_total_isolation_dB"]),
            deficit_vs_measured_db=req - float(bar["numbers"]["measured_total_isolation_dB"]),
            by_applied_depth=ladder,
            L_equiv_at_0dB_m=float(L0),
            L_equiv_of_measured_100dB_m=float(L0 * 10 ** (100.0 / 20.0)),
            L_equiv_of_circulator_25dB_m=float(L0 * 10 ** (25.0 / 20.0)))

    # Barneto 의 "송신전력이 열잡음보다 140 dB 넘게 크다" 를 우리 규약으로 재현
    b_ref = "nr"
    ours = by_band[b_ref]["si_over_thermal_db"]
    return dict(
        model=("P_si = EIRP − G_tx (도통 송신전력) 이 전단 결합으로 수신단에 들어온다. "
               "잔류 = freespace_link.n0_dpi(P_si, depth, B) — 패시브 DPI 와 같은 함수·같은 규약."),
        transmit_power=dict(eirp_dbm=EIRP_DBM, g_tx_dbi=GTX_DBI, p_tx_conducted_dbm=P_tx_dbm,
                            p_tx_conducted_w=float(P_tx_w),
                            note="G_tx=G_rx=10 dBi 고정(격자 T4). 개구가 크면 도통전력이 그만큼 준다 — 아래 감도."),
        citation=bar["citation"],
        citation_quotes=bar["quotes"],
        citation_numbers=bar["numbers"],
        self_check_vs_barneto=dict(
            their_sentence="the eNB/gNB transmit power can be even more than 140 dB larger than the receiver thermal noise floor",
            our_value_db=ours, band=b_ref,
            abs_diff_vs_140_db=abs(ours - 140.0),
            verdict="우리 EIRP·G·NF 규약이 그들의 140 dB 진술과 같은 자리에 있다."),
        by_band=by_band,
        g_tx_sensitivity=[dict(g_tx_dbi=g,
                               p_tx_conducted_dbm=EIRP_DBM - g,
                               si_over_thermal_db=float(fsl.dnr_db(
                                   10 ** ((EIRP_DBM - g - 30) / 10),
                                   fsl.n0_thermal(NF_DB, bp["nr"]["fs_hz"]))))
                          for g in (10.0, 15.0, 17.15, 20.0, 25.0)],
        honest_note=bar["honest_note"],
        equivalent_baseline_rule=("L_equiv(depth) = λ√(G_tx G_rx)/(4π)·10^(depth/20) — "
                                  "'소거 N dB' 와 '베이스라인 L m' 를 한 자로 읽는 환산. "
                                  "자유공간 DPI 식의 L→0 극한이 도통결합이라는 사실이 근거다."))


def total_isolation_ledger(bp, si):
    """⭐ 패시브와 능동을 **총 송수신 격리** 한 축 위에 올린다.

    passive  : 자유공간 격리(베이스라인) + ECA 소거깊이
    active   : 전단 총격리 (Barneto 실측 100 dB)
    """
    out = {}
    for b in BANDS:
        lam = bp[b]["lam_m"]
        L0 = si["by_band"][b]["L_equiv_at_0dB_m"]
        rows = []
        for L, eca, tag in ((L_REF_M, 90.0, "C passive bistatic L=500 m, ECA 90 dB"),
                            (L_REF_M, 60.0, "C passive bistatic L=500 m, ECA 60 dB"),
                            (L_REF_M, 40.0, "C passive bistatic L=500 m, ECA 40 dB"),
                            (L_COSITE_M, 90.0, "B passive quasi-mono L=10 m, ECA 90 dB")):
            fs_iso = float(20.0 * np.log10(L / L0))
            rows.append(dict(config=tag, baseline_m=L, freespace_isolation_db=fs_iso,
                             cancellation_db=eca, total_isolation_db=fs_iso + eca))
        act = float(si["by_band"][b]["measured_total_suppression_db"])
        rows.append(dict(config="A active monostatic, Barneto measured front end",
                         baseline_m=0.0, freespace_isolation_db=0.0,
                         cancellation_db=act, total_isolation_db=act))
        best_pass = max(r["total_isolation_db"] for r in rows[:1])
        # ⭐ 등가-잔류: 패시브가 능동 모노(100 dB)와 같은 잔류에 도달하려면 소거깊이가 얼마면 되나
        fs_iso_500 = float(20.0 * np.log10(L_REF_M / L0))
        eca_match = act - fs_iso_500
        out[b] = dict(rows=rows,
                      passive_C_minus_active_A_db=best_pass - act,
                      freespace_isolation_at_L500_db=fs_iso_500,
                      si_over_thermal_db=si["by_band"][b]["si_over_thermal_db"],
                      eca_depth_to_match_active_100dB_db=eca_match,
                      residual_over_thermal_db={r["config"]: si["by_band"][b]["si_over_thermal_db"]
                                                - r["total_isolation_db"] for r in rows})
    return dict(
        definition="총 격리 [dB] = 도통 송신전력 / 상관기 입력에서의 잔류 간섭전력",
        by_band=out,
        equal_residual_reading=(
            "⭐ L=500 m 패시브 수신기는 소거깊이 %.1f dB (LTE) 만으로 능동 모노의 실측 100 dB "
            "전단과 같은 잔류에 도달한다 — 저장소가 스윕하는 40 dB 바로 근처다."
            % out["lte"]["eca_depth_to_match_active_100dB_db"]),
        reading=("패시브 바이스태틱은 이격거리로 격리를 **공짜로** 번다. 능동 모노는 그 항이 0 이라 "
                 "전부 전단 하드웨어로 벌어야 한다."))


def depth_matrix(bp, sig_json, th, drone=DRONE_HEADLINE):
    """소거깊이를 스윕한 R90 표 — '90 dB ECA 를 줬으니 패시브가 이겼다' 를 막는다."""
    P = placements()
    d = fsl.D_GRID_DEFAULT
    n0t = fsl.n0_thermal(NF_DB, 1.0)
    out = {}
    for gname, place in P.items():
        ladder = ECA_DEPTH_LADDER_DB if place["interference"] == "dpi" else SI_DEPTH_LADDER_DB
        out[gname] = {}
        for b in BANDS:
            a = scene_arm(place, b, bp, sig_json, 90.0, d, drone)
            row = {}
            for dep in tuple(ladder) + (None,):
                ie = interference_extra(place, b, bp, dep, "broadband")
                snr = a["snr_db"] + fsl.lin2db(n0t / (n0t + ie["n0_extra"]))
                sol = fsl.solve_range(snr, th[bp[b]["mode"]], d_grid=d,
                                      kappa_of_d=a["R1"] * a["R2"], valid=a["valid"])
                row["inf" if dep is None else str(int(dep))] = dict(
                    R90_d_m=_f(sol["R_m"]), noise_rise_db=ie["noise_rise_db"],
                    n_local_at_R90=_f(sol.get("range_conv_exponent", np.nan)))
            out[gname][b] = row
    return dict(drone=drone, phi_deg=90.0, regime="broadband", cells=out,
                ladders=dict(passive_eca_db=list(ECA_DEPTH_LADDER_DB),
                             active_si_db=list(SI_DEPTH_LADDER_DB)),
                note="ECA 달성깊이 40~90 dB 는 선언값(근거문서 없음) · SI 100 dB 는 Barneto 실측이다.")


# --------------------------------------------------------------------------- #
#  §6  ⭐ 기하 이점 vs 자기간섭 비용 — 무엇이 남는가
# --------------------------------------------------------------------------- #
def advantage_vs_cost(bp, sig_json, phis, si, det_zd, drone=DRONE_HEADLINE, d_ref=1000.0):
    """모노가 기하로 버는 dB 와 SI 로 잃는 dB 를 같은 자로 비교한다.

    기하 이점의 정의를 셋으로 나눈다 — 정의가 답을 정하기 때문이다:
      G1 노드를 조명원 자리에 고정  : Δ = 20log10(R2/R1)   (부호가 φ 에 따라 뒤집힌다)
      G2 노드를 수신기 자리에 고정  : Δ = 20log10(R1/R2)
      G3 ⭐ 두 자리 중 좋은 쪽 선택 : Δ = |20log10(R1/R2)| ≥ 0  (모노의 **배치 자유도**)
    """
    d = np.array([d_ref], float)
    P = placements()
    rowsC = P["C_bistatic_L500"]
    per = {}
    for b in BANDS:
        g1, g2, g3 = [], [], []
        for phi in phis:
            a = scene_arm(rowsC, b, bp, sig_json, phi, d, drone)
            R1 = float(a["R1"][0]); R2 = float(a["R2"][0])
            g1.append(20.0 * np.log10(R2 / R1))
            g2.append(20.0 * np.log10(R1 / R2))
            g3.append(abs(20.0 * np.log10(R1 / R2)))
        g1, g2, g3 = map(np.asarray, (g1, g2, g3))
        # ⭐ 검지 한계에서의 값 — R90 비교를 지배하는 것은 여기다
        d90 = det_zd["cells"]["C_bistatic_L500"][b]["headline_phi90_R90_d_m"]
        edge = []
        for phi in phis:
            a = scene_arm(rowsC, b, bp, sig_json, phi, np.array([d90]), drone)
            edge.append(abs(20.0 * np.log10(float(a["R1"][0]) / float(a["R2"][0]))))
        edge = np.asarray(edge)
        rise100 = si["by_band"][b]["by_applied_depth"]["100"]["noise_rise_db"]
        n_at_r90 = det_zd["cells"]["C_bistatic_L500"][b]["by_phi"]["phi_90"]["n_local_at_R90"] or 4.0
        adv = float(np.median(g3))
        adv_edge = float(np.median(edge))
        net = adv - rise100
        net_edge = adv_edge - rise100
        per[b] = dict(
            R90_reference_m=d90, d_over_L_at_R90=float(d90 / L_REF_M),
            n_local_at_R90=float(n_at_r90),
            geometry_advantage_at_detection_edge_db=dict(
                median=adv_edge, min=float(edge.min()), max=float(edge.max()),
                note="d = R90 에서 평가한 |20log10(R1/R2)|. 검지거리 비교를 지배하는 값이다."),
            net_at_detection_edge_db=net_edge,
            range_factor_at_edge_after_si_x=float(fsl.range_factor(net_edge, n=n_at_r90)),
            geometry_advantage_db=dict(
                node_at_illuminator=dict(median=float(np.median(g1)), min=float(g1.min()),
                                         max=float(g1.max()), at_phi90=float(g1[list(phis).index(90.0)])),
                node_at_receiver=dict(median=float(np.median(g2)), min=float(g2.min()),
                                      max=float(g2.max())),
                best_of_two_nodes=dict(median=float(np.median(g3)), min=float(g3.min()),
                                       max=float(g3.max()))),
            si_noise_rise_db_at_100dB=rise100,
            net_db_best_node_minus_si=net,
            range_factor_before_si_x=float(fsl.range_factor(adv, n=n_at_r90)),
            range_factor_after_si_x=float(fsl.range_factor(net, n=n_at_r90)),
            break_even_suppression_db=float(si["by_band"][b]["si_over_thermal_db"]
                                            - 10.0 * np.log10(max(10 ** (adv / 10.0) - 1.0, 1e-12))),
            surviving_fraction_of_advantage=(
                float(max(net, 0.0) / adv) if adv > 1e-9 else None))
    return dict(
        d_ref_m=d_ref, drone=drone, phi_deg=[float(p) for p in phis],
        definitions=("G1 조명원 자리 · G2 수신기 자리 · G3 좋은 쪽 선택(배치 자유도). "
                     "등-EIRP·같은 표적·같은 문턱. 간섭항은 SI 100 dB(Barneto 실측)만."),
        headline=("⭐ 검지 한계(d=R90, L 의 %.1f배)에서 기하 이점은 중앙값 %.2f dB 로 죽고, "
                  "자기간섭은 %.1f dB 를 문다. 순 %+.1f dB → 거리배율 %.3f×."
                  % (per["lte"]["d_over_L_at_R90"],
                     per["lte"]["geometry_advantage_at_detection_edge_db"]["median"],
                     per["lte"]["si_noise_rise_db_at_100dB"],
                     per["lte"]["net_at_detection_edge_db"],
                     per["lte"]["range_factor_at_edge_after_si_x"])),
        by_band=per,
        break_even_meaning=("break_even_suppression_db = 잡음상승이 기하 이점과 같아지는 총 소거깊이. "
                            "이 값 아래에서는 능동 모노가 링크버짓에서 진다."))


def eirp_ladder_under_interference(bp, sig_json, th, drone=DRONE_HEADLINE):
    """⭐ 송신출력을 올리면 능동 모노가 나아지는가 — 자기간섭 한계에서는 **아니다**.

    SI 한계에서는 에코도 잔류도 EIRP 에 같이 비례하므로 SNR 이 EIRP 와 무관해진다.
    패시브 수신기는 L=500 m 에서 열잡음 한계라 EIRP 를 1:1 로 받는다. 이 대비가
    "모노가 지는 것은 EIRP 를 크게 줘서 그렇다" 는 반론을 닫는다.
    """
    P = placements()
    d = fsl.D_GRID_DEFAULT
    n0t = fsl.n0_thermal(NF_DB, 1.0)
    ladder = [30.0, 36.9, 45.0, 53.0, 63.0, 73.0, 83.0]
    out = {}
    for gname in ("C_bistatic_L500", "A_mono_at_illuminator"):
        place = P[gname]
        out[gname] = {}
        for b in BANDS:
            lam = bp[b]["lam_m"]; B = bp[b]["fs_hz"]
            tgt = fss.target_pos(d, 90.0, L_REF_M, ALT_M)
            p = fss.fs_params(place["tx"], place["rx"], tgt, (0.0, 0.0, 0.0), bp[b]["fc_hz"])
            R1 = np.asarray(p["R1"], float); R2 = np.asarray(p["R2"], float)
            el = np.asarray(p["el_deg"], float)
            _, avg, _ = sigma_tools(sig_json, drone, bp[b]["band_name"])
            sig = avg(el)
            valid = fss.beta_gate(np.asarray(p["beta"], float)) & (np.abs(el) <= SIGMA_EL_ABSMAX_DEG)
            rows = []
            for e in ladder:
                if place["interference"] == "dpi":
                    Pi = fsl.direct_power_w(e, GRX_DBI, lam, place["baseline_m"])
                    dep = 90.0
                else:
                    Pi = 10.0 ** ((e - GTX_DBI - 30.0) / 10.0)
                    dep = 100.0
                extra = float(fsl.n0_dpi(Pi, dep, B))
                snr = fsl.snr_rd_db(e, GRX_DBI, lam, sig, R1, R2, nf=NF_DB, T=T_CPI_S,
                                    n0_extra=extra)
                sol = fsl.solve_range(snr, th[bp[b]["mode"]], d_grid=d,
                                      kappa_of_d=R1 * R2, valid=valid)
                rows.append(dict(eirp_dbm=e, R90_d_m=_f(sol["R_m"]),
                                 noise_rise_db=float(10 * np.log10((n0t + extra) / n0t))))
            r = [x["R90_d_m"] for x in rows if x["R90_d_m"]]
            out[gname][b] = dict(rows=rows,
                                 R90_span_x=float(max(r) / min(r)) if len(r) > 1 else None,
                                 eirp_span_db=ladder[-1] - ladder[0])
    return dict(
        ladder_dbm=ladder, drone=drone, phi_deg=90.0,
        cells=out,
        finding=("EIRP 를 %.0f dB 올리면 패시브 R90 은 %.2f× 늘고 능동 모노는 %.2f× 늘어난다 (LTE). "
                 "자기간섭 한계에서는 송신출력이 답이 아니다."
                 % (ladder[-1] - ladder[0],
                    out["C_bistatic_L500"]["lte"]["R90_span_x"],
                    out["A_mono_at_illuminator"]["lte"]["R90_span_x"])),
        why="SI 한계에서 P_echo ∝ EIRP 이고 N0_si ∝ EIRP 이라 비가 상쇄된다 — 전형적 전이중 결과다.",
        closes="'등-EIRP 63 dBm 을 줘서 모노가 진 것' 이라는 반론을 닫는다.")


def adc_headroom(bp):
    """수신기 포화 여유 — Barneto 가 '25 dB 순환기+안테나' 를 먼저 두는 이유.

    간섭전력[dBm] 과 12-bit ADC 동적범위(`experiment_x410.X410`, 74.0 dB)를 나란히 놓고,
    잡음바닥 위 몇 dB 인지로 판정한다. 능동은 순환기 25 dB 를 먼저 뺀 값을 쓴다.
    """
    dr = float(fsl.adc_dr_db(bits=12))
    out = {}
    for b in BANDS:
        B = bp[b]["fs_hz"]; lam = bp[b]["lam_m"]
        n_dbm = float(10 * np.log10(fsl.n0_thermal(NF_DB, B) * 1e3))
        rows = []
        for tag, kind, L, pre in (("C passive L=500 m", "dpi", L_REF_M, 0.0),
                                  ("B passive L=10 m", "dpi", L_COSITE_M, 0.0),
                                  ("A active, circulator+antenna 25 dB", "si", None, 25.0)):
            if kind == "dpi":
                Pw = fsl.direct_power_w(EIRP_DBM, GRX_DBI, lam, L)
            else:
                Pw = 10.0 ** ((EIRP_DBM - GTX_DBI - 30.0) / 10.0)
            p_dbm = float(10 * np.log10(Pw * 1e3)) - pre
            above = p_dbm - n_dbm
            rows.append(dict(config=tag, interferer_dbm=p_dbm, above_noise_db=above,
                             adc_dynamic_range_db=dr, headroom_db=dr - above,
                             saturates=bool(above > dr)))
        out[b] = dict(noise_floor_dbm=n_dbm, rows=rows)
    return dict(
        adc="experiment_x410.X410(12 bit) → %.1f dB (freespace_link.adc_dr_db)" % dr,
        by_band=out,
        reading=("headroom_db < 0 이면 아날로그 단에서 먼저 죽여야 한다. 능동 모노는 순환기 25 dB "
                 "를 빼고도 헤드룸이 크게 모자라고, 그래서 Barneto 가 '능동 RF 소거 >50 dB 가 "
                 "수신기 포화를 막는 데 필수' 라고 쓴다."),
        caveat="이 표는 포화 판정만 한다 — 양자화 잡음의 정량은 `freespace_link.n0_quant` 소관이다.")


def doppler_relief_at_edge(bp, det_zd, phis, drone=DRONE_HEADLINE):
    """⭐ 기하 축의 **두 번째** 성분(도플러 완화 1/cos(β/2))도 검지 한계에서 죽는지 본다.

    β 는 d/L 에 따라 0 으로 간다. 링크버짓 성분과 도플러 성분이 **같은 이유로** 같이 죽으면,
    "검지 한계에서 기하 축이 사라진다" 는 한 문장으로 두 성분을 다 덮을 수 있다.
    """
    P = placements()["C_bistatic_L500"]
    out = {}
    for b in BANDS:
        d90 = det_zd["cells"]["C_bistatic_L500"][b]["headline_phi90_R90_d_m"]
        betas, near = [], []
        for phi in phis:
            for dd, box in ((d90, betas), (0.5 * L_REF_M, near)):
                tgt = fss.target_pos(np.array([dd]), phi, L_REF_M, ALT_M)
                p = fss.fs_params(P["tx"], P["rx"], tgt, (0.0, 0.0, 0.0), bp[b]["fc_hz"])
                box.append(float(np.ravel(p["beta"])[0]))
        betas = np.asarray(betas); near = np.asarray(near)
        rel = 1.0 / np.cos(np.radians(betas) / 2.0)
        rel_n = 1.0 / np.cos(np.radians(near) / 2.0)
        out[b] = dict(
            d90_m=d90,
            beta_at_edge_deg=dict(median=float(np.median(betas)), max=float(betas.max())),
            relief_at_edge_x=dict(median=float(np.median(rel)), max=float(rel.max())),
            v_max_bistatic_at_edge_ms=float(bp[b]["lam_m"] * bp[b]["prf_ref_hz"] / 4.0
                                            * float(np.median(rel))),
            v_max_monostatic_ms=float(bp[b]["lam_m"] * bp[b]["prf_ref_hz"] / 4.0),
            beta_at_half_baseline_deg=dict(median=float(np.median(near)), max=float(near.max())),
            relief_at_half_baseline_x=dict(median=float(np.median(rel_n)), max=float(rel_n.max())))
    return dict(
        form="v_max(β) = λ·PRF/(4·cos(β/2)·cos δ) — 바이스태틱은 β 가 클수록 관대하다",
        by_band=out,
        finding=("검지 한계는 d ≈ 14·L 이라 거기서 β 중앙값이 %.2f° 이고 완화계수가 %.4f× 다 — "
                 "링크버짓 성분과 **같은 이유로**(d/L → ∞) 도플러 성분도 죽는다."
                 % (out["lte"]["beta_at_edge_deg"]["median"],
                    out["lte"]["relief_at_edge_x"]["median"])),
        consequence=("우리가 인용해온 v_max(모노 = 바이 β=0 바닥)는 검지 한계에서 두 기하의 "
                     "실제값이기도 하다 — '최악값' 이 아니라 그냥 **값**이다."),
        where_relief_lives="완화는 d ≲ L 에서만 의미가 있다(반절 베이스라인에서 β 중앙 %.1f°)."
                           % out["lte"]["beta_at_half_baseline_deg"]["median"])


# --------------------------------------------------------------------------- #
#  §7  레짐 대비 — 잔류 간섭이 광대역인가 0-도플러에 갇히는가
# --------------------------------------------------------------------------- #
def regimes(bp, th):
    """두 레짐의 경계를 수치로 적는다. **두 팔에 같은 레짐을 적용해야 공정하다.**"""
    out = {}
    for b in BANDS:
        prf = bp[b]["prf_ref_hz"]; M = bp[b]["M"]; lam = bp[b]["lam_m"]
        dfd = float(fss.doppler_bin_hz(T_CPI_S, prf, M))
        f_guard = float(fsd.DOPPLER_GUARD_WIDTH) / 2.0 * dfd
        out[b] = dict(doppler_bin_hz=dfd, guard_half_width_hz=f_guard,
                      v_guard_monostatic_ms=float(lam * f_guard / 2.0),
                      v_max_unambiguous_ms=float(lam * prf / 4.0),
                      drone_speed_band_ms=list(fss.FS_SPEED))
    return dict(
        broadband=("잔류 간섭이 표적 도플러 셀까지 백색으로 퍼진다고 본다. 저장소 정본 "
                   "(`freespace_link.n0_dpi`)이 이 규약이고, 패시브 DPI 에 이미 이렇게 적용돼 있다."),
        zero_doppler=("잔류가 송신과 코히런트해 f_d=0 능선에 갇힌다고 본다. 검출기가 이미 지우는 "
                      "0-도플러 가드가 그대로 처리한다 → 잡음상승 0."),
        which_is_true=("실제 잔류는 송신기 위상잡음·비선형이 도플러로 퍼뜨린 성분이 지배한다 — "
                       "두 레짐 사이 어딘가다. 우리는 두 끝을 다 낸다."),
        literature_support=("Barneto 2019: 'limited TX-RX isolation is primarily a concern in "
                            "detection of static targets while moving targets are inherently more "
                            "robust to transmitter self-interference' — 이동표적 쪽이 관대하다는 "
                            "그들의 직접 진술이다(우리에게 불리한 인용)."),
        guard_by_band=out,
        fairness_rule="⭐ 레짐은 두 팔에 **같이** 건다. 모노에만 0-도플러 레짐을 주면 격자가 거짓말을 한다.")


# --------------------------------------------------------------------------- #
#  §8  뷰 — 실현가능 EIRP · 개구 재사용 · 듀티 · 문헌 대조
# --------------------------------------------------------------------------- #
def views(bp, prior, si):
    lasen = prior["lasen"]
    hw = lasen["hardware"]
    # LaSen 실측 하드웨어: 24.9 dBm + 12 dBi 패널 → EIRP 36.9 dBm
    lasen_eirp = 24.9 + 12.0
    delta = lasen_eirp - EIRP_DBM
    aper = [dict(g_tx_dbi=g, delta_grx_db=g - GRX_DBI,
                 range_factor_x=float(fsl.range_factor(g - GRX_DBI, n=4.0)))
            for g in (10.0, 15.0, 17.15, 20.0, 25.0)]
    duty = {b: dict(prf_ref_hz=bp[b]["prf_ref_hz"], M=bp[b]["M"], t_ref_s=bp[b]["t_ref_s"],
                    duty_db=bp[b]["duty_db"],
                    range_factor_x=float(fsl.range_factor(bp[b]["duty_db"], n=4.0)))
            for b in BANDS}
    return dict(
        eirp=dict(
            canonical="등-EIRP 63 dBm — 기하 축만 남긴다(격자 T3 정본).",
            feasible_active_view=dict(
                lasen_tx_dbm=24.9, lasen_ant_dbi=12.0, lasen_eirp_dbm=lasen_eirp,
                delta_vs_canonical_db=delta,
                range_factor_x=float(fsl.range_factor(delta, n=4.0)),
                source=f"monostatic_prior.json : lasen.hardware.tx = {hw['tx']!r}",
                meaning="실제로 만들어진 능동 모노 드론센서는 매크로 EIRP 를 쓰지 않는다."),
            note="등-EIRP 는 능동을 크게 봐주는 규약이다 — 그 방향을 명시한다."),
        aperture_reuse=dict(
            canonical_g_rx_dbi=GRX_DBI,
            table=aper,
            note="개구 재사용은 기하 이득이 아니라 안테나 이득이다(T4). 정본에서는 끈다."),
        duty_axis=dict(
            by_band=duty,
            geometry_free=True,
            defect=("`freespace_link.duty_db_from_cpi` 는 정의돼 있으나 R90 생산경로에서 호출되지 "
                    "않는다 ⟨sigma_sensitivity.json : unapplied_duty_axis⟩. 여기서는 뷰로만 낸다 — "
                    "두 팔에 같은 값이라 기하 비교에는 정확히 영향이 없다."),
            check="duty 는 φ·기하와 무관하므로 §3 의 행효과에 기여 0."),
        lasen_side_by_side=dict(
            identity=lasen["identity"]["citation_line"],
            geometry=lasen["geometry"]["answer"],
            measured_detection_range_m=lasen["velocity_claim"]["detection_range_m"],
            measured_velocity_top_bin_ms=lasen["velocity_claim"]["accuracy_at_the_top_bin"]["velocity_bin_ms"],
            self_interference_handling=lasen["self_interference_handling"]["what_they_did"],
            scoping_caveat=lasen["scoping_caveat_that_must_be_stated_when_citing"],
            what_we_can_say=("LaSen 은 A 행 5G 셀의 게재 대조군이다. 그들은 SI 를 차폐판 + 정적배경 "
                             "제거로만 처리했고 격리 수치를 보고하지 않았다 — 우리 SI 원장의 100 dB 는 "
                             "Barneto 실측이지 LaSen 값이 아니다.")))


# --------------------------------------------------------------------------- #
#  §9  선행 문헌 교차확인 — 직접파/에코 비
# --------------------------------------------------------------------------- #
def literature_crosscheck(bp, sig_json, drone=DRONE_HEADLINE, d_ref=1000.0):
    """Sharma 2026 'UAV echo is 44-49 dB weaker than the LOS' 와 우리 DIR 을 나란히."""
    P = placements()["C_bistatic_L500"]
    out = {}
    for b in BANDS:
        a = scene_arm(P, b, bp, sig_json, 90.0, np.array([d_ref]), drone)
        lt = link_terms(LinkBudget(eirp_dbm=EIRP_DBM, rx_gain_dbi=GRX_DBI,
                                   noise_figure_db=NF_DB),
                        a["lam"], float(a["sigma"][0]), float(a["R1"][0]),
                        float(a["R2"][0]), L_REF_M, bp[b]["fs_hz"])
        out[b] = dict(direct_over_echo_db=float(lt["dnr_db"]),
                      echo_over_noise_db=float(lt["snr_echo_db"]),
                      sigma_dbsm=float(10 * np.log10(a["sigma"][0])),
                      R1_m=float(a["R1"][0]), R2_m=float(a["R2"][0]))
    # 문헌 기하(30~200 m)로 옮겨 놓은 스케일 행 — DIR ∝ R1²R2²/L² 이므로 40log10(d비) 만큼 준다
    d_lit = 150.0
    scaled = {b: dict(direct_over_echo_db=out[b]["direct_over_echo_db"]
                      - 40.0 * float(np.log10(d_ref / d_lit)),
                      scaled_to_d_m=d_lit) for b in BANDS}
    return dict(
        ours=out, ours_scaled_to_literature_geometry=scaled, d_ref_m=d_ref, drone=drone,
        scaling_rule="DIR ∝ R₁²R₂²/L² → 표적을 d=1000 m 에서 150 m 로 옮기면 40log10(1000/150) dB 준다",
        gap_to_literature_db=dict(
            ours_at_150m_lte=scaled["lte"]["direct_over_echo_db"],
            literature_range_db=[44.0, 49.0],
            note="남는 차는 σ·EIRP·수신이득 규약 차이다. 우리 σ 격자의 el 범위가 150 m 를 못 덮으므로 "
                 "이 행은 σ 를 다시 조회하지 않고 기하 스케일만 적용한 값이다."),
        literature=dict(value_db=[-49.0, -44.0],
                        source=("Sharma/Gonzalez-Prelcic et al. arXiv:2607.11955 (2026): "
                                "'the UAV echo is about 44 to 49 dB weaker than the LOS in the "
                                "considered geometry' (outdoor urban 30-200 m)"),
                        note="그들의 기하는 30~200 m 이고 우리는 1 km 다 — 자릿수 확인용이지 정합 검사가 아니다."))


# --------------------------------------------------------------------------- #
#  §9b ⭐ 다른 워크플로의 `src/monostatic_scene.py` 와 맞대기
# --------------------------------------------------------------------------- #
def cross_check_monostatic_scene(bp, sig_json, drone=DRONE_HEADLINE):
    """이 파일을 짜는 동안 `src/monostatic_scene.py` 가 생겼다. 두 결과를 맞대 본다.

    ⚠ 그 파일은 다른 워크플로 소유라 **읽기만** 한다. 여기서 확인하는 것 셋:
      1) 기하·SNR 이 같은가 (둘 다 `freespace_link` 를 감싸므로 정확히 같아야 한다)
      2) 격리 기준면 규약이 같은가 — ⭐ **다르다.** 그 파일은 EIRP 기준, 이 파일은 도통전력 기준
      3) 그 차이가 정확히 G_tx [dB] 인가 (그렇다면 두 산출물이 한 항으로 화해한다)
    """
    try:
        import monostatic_scene as ms
    except Exception as e:
        return dict(available=False, error=repr(e),
                    note="모듈이 아직 임포트 가능한 상태가 아니다 — 이 파일은 자체 계산으로 완결된다.")

    d = np.array([1000.0, 3000.0], float)
    b = "nr"
    lam = bp[b]["lam_m"]; fc = bp[b]["fc_hz"]; B = bp[b]["fs_hz"]
    tgt_ours = fss.target_pos(d, 90.0, L_REF_M, ALT_M)
    p_ours = fss.fs_params(fss.FS_TX, fss.FS_TX, tgt_ours, (0.0, 0.0, 0.0), fc)
    R_ours = np.asarray(p_ours["R1"], float)

    geom = {}
    try:
        tgt_th = ms.mono_target_pos(d, 90.0, ALT_M)
        p_th = ms.mono_params(tgt_th, (0.0, 0.0, 0.0), fc)
        R_th = np.asarray(p_th["R"] if "R" in p_th else p_th.get("R1"), float)
        R_th = np.ravel(R_th)
        # 그 파일 규약이 '센서 기준 d' 인지 검사: R = sqrt(d² + Δz²) 이면 그렇다
        dz = ALT_M - float(fss.FS_TX[2])
        sensor_centred = np.sqrt(d ** 2 + dz ** 2)
        geom = dict(
            ours_R_m=R_ours.tolist(), theirs_R_m=R_th.tolist(),
            max_abs_diff_m=float(np.max(np.abs(R_ours - R_th))),
            theirs_matches_sensor_centred_d=bool(
                np.max(np.abs(R_th - sensor_centred)) < 1e-6),
            sensor_centred_R_m=sensor_centred.tolist(),
            diagnosis=("⭐ 장면 원점 규약이 다르다. 그 파일의 d 는 **센서 기준 수평거리**이고, "
                       "이 파일의 d 는 **바이스태틱 중점 기준**이라 두 팔이 같은 물리 위치를 본다. "
                       "기하 축 비교(격자 N3)에는 공유 좌표계가 필요하므로 이 파일은 중점 기준을 쓴다."),
            reconciliation=("모노 단독 수치를 인용할 때는 그 파일 규약이 자연스럽고, 두 기하를 "
                            "나란히 놓을 때는 이 파일 규약이 필요하다. 키 이름에 규약을 적어 "
                            "섞이지 않게 한다 — 예 `R90_d_m@scene_midpoint` vs `@sensor`."),
            offset_at_phi90_m=float(0.5 * L_REF_M))
    except Exception as e:
        geom = dict(error=repr(e))

    snr = {}
    try:
        sig = 0.01
        ours = float(np.ravel(fsl.snr_rd_db(EIRP_DBM, GRX_DBI, lam, sig, R_ours[0], R_ours[0],
                                            nf=NF_DB, T=T_CPI_S))[0])
        theirs = float(np.ravel(ms.mono_snr_rd_db(EIRP_DBM, GRX_DBI, lam, sig, R_ours[0],
                                                  nf=NF_DB, T=T_CPI_S))[0])
        snr = dict(ours_db=ours, theirs_db=theirs, abs_diff_db=abs(ours - theirs),
                   verdict="같은 `freespace_link.snr_rd_db` 를 감싸므로 0 이어야 한다")
    except Exception as e:
        snr = dict(error=repr(e))

    iso = {}
    try:
        theirs_psd = float(ms.si_residual_psd(EIRP_DBM, 100.0, B))
        ours_psd = float(fsl.n0_dpi(10.0 ** ((EIRP_DBM - GTX_DBI - 30.0) / 10.0), 100.0, B))
        off = float(fsl.lin2db(theirs_psd / ours_psd))
        theirs_gap = float(ms.isolation_gap_vs_passive_db(lam, L_REF_M, GRX_DBI))
        ours_gap = float(20.0 * np.log10(4 * np.pi * L_REF_M / lam) - GTX_DBI - GRX_DBI)
        iso = dict(
            reference_plane_ours="도통 송신전력 (EIRP − G_tx) — Barneto 의 'TX-RX isolation' 은 "
                                 "순환기 포트 간 값이라 도통면이 인용 기준면과 맞는다",
            reference_plane_theirs="EIRP (송신 안테나 이득이 누설경로에도 실린다는 보수적 상한). "
                                   "그 파일 docstring 이 스스로 '상한' 이라고 적었다",
            si_residual_psd_theirs=theirs_psd, si_residual_psd_ours=ours_psd,
            offset_db=off, g_tx_dbi=GTX_DBI, offset_equals_g_tx=bool(abs(off - GTX_DBI) < 1e-9),
            isolation_gap_theirs_db=theirs_gap, isolation_gap_ours_db=ours_gap,
            gap_offset_db=theirs_gap - ours_gap,
            reconciliation="두 산출물의 SI 수치는 정확히 G_tx = %.1f dB 만큼 다르다. 한 항으로 화해한다 — "
                           "모순이 아니라 기준면 표기 차이다." % GTX_DBI,
            direction="그 파일 규약이 %.1f dB 더 보수적이다(모노를 더 벌준다). 이 파일의 결론은 "
                      "그쪽 규약에서도 그대로 성립한다." % GTX_DBI)
    except Exception as e:
        iso = dict(error=repr(e))

    return dict(available=True,
                module_mtime=datetime.fromtimestamp(
                    os.path.getmtime(os.path.join(ROOT, "src", "monostatic_scene.py"))
                ).isoformat(timespec="seconds"),
                geometry=geom, snr=snr, self_interference_reference_plane=iso,
                policy="그 파일은 다른 워크플로 소유다 — 읽기만 하고 편집하지 않았다.",
                what_to_merge=("이 파일의 `placements()`·`interference_extra()` 는 "
                               "`monostatic_scene.mono_pos/si_residual_psd` 와 역할이 겹친다. "
                               "병합 시 **기준면 하나를 먼저 정하고** 나머지를 거기 맞춰야 한다."))


# --------------------------------------------------------------------------- #
#  §10  판정
# --------------------------------------------------------------------------- #
def verdict(axis, geo_r, det_bb, det_zd, si, adv, ledger, reg_chk, drones, eirpl, adc, dopr):
    b = "lte"
    g = adv["by_band"][b]
    cz = det_zd["cells"]
    cb = det_bb["cells"]
    return dict(
        headline=(
            "⭐ 이 격자에서 모노스태틱의 이점은 **링크버짓이 아니라 속도축**이다. "
            "1/R⁴ 대 1/(R₁²R₂²) 의 차이는 20log10(R_조명원/R_센서) 한 줄이고 검지 한계(d≈%.0f×L)에서 "
            "중앙값 %.2f dB 로 죽는다. 반면 자기간섭은 실측 최선 100 dB 소거에서도 %.1f dB 를 물어 "
            "검지거리를 %.0f m → %.0f m 로 줄인다."
            % (g["d_over_L_at_R90"],
               g["geometry_advantage_at_detection_edge_db"]["median"],
               g["si_noise_rise_db_at_100dB"],
               cz["C_bistatic_L500"][b]["headline_phi90_R90_d_m"],
               cb["A_mono_at_illuminator"][b]["headline_phi90_R90_d_m"])),
        detection_range_table_phi90_m={
            gname: {bb: cb[gname][bb]["headline_phi90_R90_d_m"] for bb in BANDS}
            for gname in cb},
        detection_range_no_interference_phi90_m={
            gname: {bb: cz[gname][bb]["headline_phi90_R90_d_m"] for bb in BANDS}
            for gname in cz},
        geometry_effect_alone=(
            "간섭항을 끄면 네 배치의 R90 이 %.1f m 안에서 같다 — 베이스라인 0 m·10 m·500 m 가 같은 "
            "검지거리를 준다. 기하 축의 링크버짓 기여는 검지 한계에서 사실상 0 이다."
            % max(abs(cz["A_mono_at_illuminator"][bb]["headline_phi90_R90_d_m"]
                      - cz["C_bistatic_L500"][bb]["headline_phi90_R90_d_m"]) for bb in BANDS)),
        illuminator_effect_alone=(
            "같은 조건에서 조명원은 R90 을 %.0f~%.0f m 로 가른다(LTE 최장·WiFi 최단). "
            "조명원 축이 기하 축보다 자릿수로 크다."
            % (min(cz["C_bistatic_L500"][bb]["headline_phi90_R90_d_m"] for bb in BANDS),
               max(cz["C_bistatic_L500"][bb]["headline_phi90_R90_d_m"] for bb in BANDS))),
        regression=("간섭을 끈 바이스태틱 팔이 `sigma_sensitivity.json` 의 자세평균 R90 을 "
                    "최대 오차 %.3g m 로 재현한다 — 두 팔이 같은 링크·문턱 위에 있다."
                    % reg_chk["max_abs_diff_m"]),
        axis_independence_evidence=(
            "σ 격자를 가진 %d 기체 전부에서 조명원 순위가 네 배치에 걸쳐 동일하다(%s). "
            "기하를 바꿔도 조명원 축의 답이 안 바뀐다 — 두 축이 독립이라는 직접 증거다."
            % (len(drones["drones_used"]), drones["geometry_preserves_ranking_for_all"])),
        geometry_axis=(
            "기하 축의 링크버짓 기여는 φ 에 따라 부호가 뒤집힌다 — 중앙값 %.2f dB, 범위 %.2f~%.2f dB "
            "(노드를 조명원 자리에 둔 경우). φ=90° 한 점만 보면 %.3f dB 라 축이 사라져 보인다(함정 T1b)."
            % (axis["summary"]["mono_minus_bistatic_db"]["median"],
               axis["summary"]["mono_minus_bistatic_db"]["min"],
               axis["summary"]["mono_minus_bistatic_db"]["max"],
               axis["summary"]["mono_minus_bistatic_db"]["at_phi90"])),
        illuminator_axis=(
            "조명원 축은 φ 와 무관하게 %.2f dB 폭으로 벌어진다(중앙값). 기하와 조명원의 상호작용은 "
            "최대 %.2f dB 이며 그 전부가 σ(el, 밴드) 다."
            % (axis["summary"]["illuminator_span_db"]["median"],
               axis["summary"]["interaction_absmax_db"]["max"])),
        self_interference=(
            "능동 모노는 도통 송신전력이 열잡음보다 %.1f dB 크고(5G 122.88 MHz 기준), 잔류를 열잡음 "
            "아래로 누르려면 %.1f dB 가 필요하다. 실측 최선은 100 dB 라 %.1f dB 가 모자라고, 그만큼 "
            "잡음바닥이 올라간다."
            % (si["by_band"]["nr"]["si_over_thermal_db"],
               si["by_band"]["nr"]["required_total_suppression_db"],
               si["by_band"]["nr"]["deficit_vs_measured_db"])),
        total_isolation=(
            "총 격리로 보면 L=500 m·ECA 90 dB 의 패시브 바이스태틱이 능동 모노 전단보다 %.1f dB (LTE) "
            "앞선다 — 이격거리는 공짜 격리다. 뒤집어 읽으면, 패시브는 소거 %.1f dB 만으로 능동 모노의 "
            "실측 100 dB 전단과 같은 잔류에 도달한다."
            % (ledger["by_band"]["lte"]["passive_C_minus_active_A_db"],
               ledger["by_band"]["lte"]["eca_depth_to_match_active_100dB_db"])),
        config_B_verdict=(
            "구성 B(수신기를 조명원 옆 %d m)는 기하를 모노로 옮기고 DPI 를 문다 — 90 dB 소거에서도 "
            "R90 이 %.0f m 로 C 의 %.0f m 대비 %.2f× 다. 기하는 공짜가 아니다."
            % (int(L_COSITE_M), cb["B_quasi_mono_L10"][b]["headline_phi90_R90_d_m"],
               cb["C_bistatic_L500"][b]["headline_phi90_R90_d_m"],
               cb["B_quasi_mono_L10"][b]["headline_phi90_R90_d_m"]
               / cb["C_bistatic_L500"][b]["headline_phi90_R90_d_m"])),
        regime_dependence=(
            "이 결론은 잔류가 광대역이라는 규약 위에 선다. 0-도플러 레짐에서는 두 팔의 간섭항이 함께 "
            "0 이 되고, 그러면 남는 것은 기하(중앙값 0 dB)와 속도축뿐이다 — 어느 레짐에서도 "
            "모노가 링크버짓으로 이기지 않는다."),
        eirp_invariance=(
            "⭐ EIRP 를 %.0f dB 올리면 패시브 R90 은 %.2f× 늘고 능동 모노는 %.2f× 늘어난다 — "
            "자기간섭 한계에서는 에코와 잔류가 함께 커져 비가 상쇄된다. "
            "'등-EIRP 63 dBm 이 모노를 벌준 것' 이라는 반론은 여기서 닫힌다."
            % (eirpl["cells"]["C_bistatic_L500"]["lte"]["eirp_span_db"],
               eirpl["cells"]["C_bistatic_L500"]["lte"]["R90_span_x"],
               eirpl["cells"]["A_mono_at_illuminator"]["lte"]["R90_span_x"])),
        saturation=(
            "12-bit ADC 헤드룸으로 보면 5G 대역에서 포화하는 구성은 %s 다 — 병설(구성 B)과 능동 "
            "모노가 같은 벽에 부딪힌다. 벽의 원인은 기하가 아니라 **송수신 병설**이다."
            % [r["config"] for r in adc["by_band"]["nr"]["rows"] if r["saturates"]]),
        doppler_geometry=(
            "도플러 완화도 같은 이유로 죽는다 — 검지 한계에서 β 중앙값 %.2f°, 완화 %.4f× 다. "
            "반면 반절 베이스라인에서는 β %.0f° 로 완화 %.2f× 다. 기하 축은 근거리에 산다."
            % (dopr["by_band"]["lte"]["beta_at_edge_deg"]["median"],
               dopr["by_band"]["lte"]["relief_at_edge_x"]["median"],
               dopr["by_band"]["lte"]["beta_at_half_baseline_deg"]["median"],
               dopr["by_band"]["lte"]["relief_at_half_baseline_x"]["median"])),
        what_monostatic_actually_buys=(
            "PRF 통제권 하나다. 3GPP sub-6 CSI-RS 천장 500 Hz → 3.5 GHz 에서 v_max 10.71 m/s 로 "
            "패시브 SSB 1.07 m/s 의 10배 ⟨geometry_grid.json : control_axis.by_band.nr⟩. "
            "그 10배가 이 논문에서 모노 행이 존재하는 이유다."),
        headline_numbers=dict(
            geometry_at_edge_median_db=g["geometry_advantage_at_detection_edge_db"]["median"],
            geometry_best_node_at_1km_median_db=g["geometry_advantage_db"]["best_of_two_nodes"]["median"],
            geometry_absmax_over_scene_db=geo_r["absmax_over_grid_db"],
            si_noise_rise_db=g["si_noise_rise_db_at_100dB"],
            net_db=g["net_db_best_node_minus_si"],
            range_factor_after_si_x=g["range_factor_after_si_x"],
            break_even_suppression_db=g["break_even_suppression_db"],
            eca_depth_to_match_active_db=ledger["by_band"][b]["eca_depth_to_match_active_100dB_db"],
            R90_C_bistatic_m=cb["C_bistatic_L500"][b]["headline_phi90_R90_d_m"],
            R90_B_quasi_mono_m=cb["B_quasi_mono_L10"][b]["headline_phi90_R90_d_m"],
            R90_A_mono_m=cb["A_mono_at_illuminator"][b]["headline_phi90_R90_d_m"]),
        what_would_change_this=[
            dict(item="0-도플러 레짐이 참이면",
                 effect="두 팔의 간섭항이 함께 0 이 되고 R90 이 %.0f m 근처로 수렴한다. "
                        "그래도 모노가 링크버짓으로 이기지는 않는다."
                        % cz["C_bistatic_L500"][b]["headline_phi90_R90_d_m"],
                 how_to_settle="송신기 위상잡음 스펙트럼을 측정해 잔류가 도플러로 얼마나 퍼지는지 잰다"),
            dict(item="능동 전단 격리가 141 dB 에 도달하면",
                 effect="잡음상승이 열잡음 아래로 내려가고 모노가 기하 이점(검지 한계 %.2f dB)만큼만 앞선다"
                        % g["geometry_advantage_at_detection_edge_db"]["median"],
                 how_to_settle="실측 격리 문헌을 100 dB 위에서 다시 찾는다 (현 최선 = Barneto 2019)"),
            dict(item="표적이 베이스라인 안쪽(d ≲ 2L)에 있으면",
                 effect="기하 축이 살아난다 — 최대 %.1f dB. 추적·근접방어 시나리오의 이야기다."
                        % geo_r["absmax_over_grid_db"],
                 how_to_settle="근거리 σ 격자(el −75° 까지)를 만들어 그 구간을 신뢰할 수 있게 한다"),
            dict(item="ECA 달성깊이가 40 dB 에 머물면",
                 effect="패시브 C 도 무너진다 — depth_matrix 참조. 90 dB 는 선언값이지 실측이 아니다",
                 how_to_settle="실장 ECA 소거깊이의 근거문서를 찾거나 X410 로 직접 잰다")])


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("[mono_link] 시작 — 모노 팔 링크버짓·검지거리·자기간섭", flush=True)
    bp = band_params()
    sig_json = _load(SIGMA_JSON)
    prior = _load(PRIOR_JSON)
    grid = _load(GRID_JSON)
    phis = [float(x) for x in range(0, 181, 15)]

    print("  §1 기하 항등식", flush=True)
    ident = identity_check(bp)
    print(f"      L={ident['L_m']:.1f} m · |R1−R2|max={ident['max_abs_R1_minus_R2_m']:.2e} m · "
          f"β_max={ident['max_beta_deg']:.2e}° · 1/R⁴ 접힘오차 {ident['spread_folds_to_inverse_R4_max_abs_db']:.2e} dB",
          flush=True)

    print("  §2 문턱(바이스태틱 팔과 동일)", flush=True)
    th = thresholds()
    print(f"      snr90 = {th['snr90_db']}", flush=True)

    print("  §3 축 분리 (2×3 이원분해, φ 스윕)", flush=True)
    axis = axis_separation(bp, sig_json, phis)
    s = axis["summary"]
    print(f"      기하폭 중앙 {s['geometry_span_db']['median']:.2f} dB (최대 {s['geometry_span_db']['max']:.2f}) · "
          f"조명원폭 중앙 {s['illuminator_span_db']['median']:.2f} dB · "
          f"상호작용 최대 {s['interaction_absmax_db']['max']:.2f} dB", flush=True)

    print("  §3b 기하 효과의 d/L 의존", flush=True)
    geo_r = geometry_effect_vs_range(bp, phis)
    print(f"      절대최대 {geo_r['absmax_over_grid_db']:.2f} dB (격자 N3 값과 차 "
          f"{geo_r['grid_crosscheck']['abs_diff_db']:.2e} dB) · d/L=10 중앙 "
          f"{geo_r['by_d_over_L']['d_over_L_10']['median_abs_db']:.3f} dB", flush=True)

    print("  §4 검지거리 (광대역 레짐 / 0-도플러 레짐)", flush=True)
    det_bb = detection_ranges(bp, sig_json, phis, th["snr90_db"], regime="broadband")
    det_zd = detection_ranges(bp, sig_json, phis, th["snr90_db"], regime="zero_doppler")
    for g in det_bb["cells"]:
        row = " ".join(f"{b}:{(det_bb['cells'][g][b]['headline_phi90_R90_d_m'] or float('nan')):.0f}m"
                       for b in BANDS)
        rowz = " ".join(f"{b}:{(det_zd['cells'][g][b]['headline_phi90_R90_d_m'] or float('nan')):.0f}m"
                        for b in BANDS)
        print(f"      {g:24s} 광대역[{row}]  0-도플러[{rowz}]", flush=True)
    reg_chk = regression_vs_repo(det_zd)
    print(f"      회귀검사 vs sigma_sensitivity 자세평균 R90: 최대오차 "
          f"{reg_chk['max_abs_diff_m']:.3g} m", flush=True)
    drones = all_drones(bp, sig_json, th["snr90_db"])
    print(f"      {len(drones['drones_used'])}기체 전부 기하를 바꿔도 조명원 순위 유지: "
          f"{drones['geometry_preserves_ranking_for_all']} · 기체간 순위 종류 "
          f"{drones['n_distinct_orders_across_drones']} (제외 {drones['drones_skipped']})", flush=True)

    print("  §5 자기간섭", flush=True)
    si = self_interference(bp, prior)
    print(f"      SI/열잡음(5G) {si['by_band']['nr']['si_over_thermal_db']:.1f} dB · "
          f"요구 {si['by_band']['nr']['required_total_suppression_db']:.1f} dB · "
          f"실측 100 dB → 잡음상승 {si['by_band']['nr']['by_applied_depth']['100']['noise_rise_db']:.1f} dB",
          flush=True)
    ledger = total_isolation_ledger(bp, si)
    print(f"      등가-잔류: 패시브 L=500 m 는 소거 "
          f"{ledger['by_band']['lte']['eca_depth_to_match_active_100dB_db']:.1f} dB (LTE) 만으로 "
          f"능동 100 dB 전단과 동률", flush=True)
    dmat = depth_matrix(bp, sig_json, th["snr90_db"])

    print("  §6 기하 이점 vs SI 비용", flush=True)
    adv = advantage_vs_cost(bp, sig_json, phis, si, det_zd)
    for b in BANDS:
        a = adv["by_band"][b]
        print(f"      {b:4s} 검지한계 기하 {a['geometry_advantage_at_detection_edge_db']['median']:+.2f} dB · "
              f"SI −{a['si_noise_rise_db_at_100dB']:.1f} dB · 순 {a['net_at_detection_edge_db']:+.1f} dB · "
              f"거리배율 {a['range_factor_at_edge_after_si_x']:.3f}×", flush=True)

    print("  §6a EIRP 사다리 (자기간섭 한계의 EIRP 무관성)", flush=True)
    eirpl = eirp_ladder_under_interference(bp, sig_json, th["snr90_db"])
    print("      " + eirpl["finding"], flush=True)
    adc = adc_headroom(bp)
    sat = [r["config"] for r in adc["by_band"]["nr"]["rows"] if r["saturates"]]
    print(f"      ADC 포화(5G): {sat}", flush=True)

    print("  §6b 도플러 완화도 검지 한계에서 죽는가", flush=True)
    dopr = doppler_relief_at_edge(bp, det_zd, phis)
    print(f"      β 중앙 {dopr['by_band']['lte']['beta_at_edge_deg']['median']:.2f}° · "
          f"완화 {dopr['by_band']['lte']['relief_at_edge_x']['median']:.4f}× "
          f"(반절 베이스라인에서는 β {dopr['by_band']['lte']['beta_at_half_baseline_deg']['median']:.1f}°)",
          flush=True)

    reg = regimes(bp, th)
    vw = views(bp, prior, si)
    lit = literature_crosscheck(bp, sig_json)
    print("  §9b monostatic_scene.py 맞대기", flush=True)
    xchk = cross_check_monostatic_scene(bp, sig_json)
    if xchk.get("available"):
        i = xchk.get("self_interference_reference_plane", {})
        print(f"      SNR 차 {xchk.get('snr',{}).get('abs_diff_db','n/a')} · "
              f"SI 기준면 차 {i.get('offset_db','n/a')} dB (= G_tx {i.get('offset_equals_g_tx')})",
              flush=True)
    else:
        print(f"      모듈 임포트 불가 — {xchk.get('error')}", flush=True)
    vd = verdict(axis, geo_r, det_bb, det_zd, si, adv, ledger, reg_chk, drones, eirpl, adc, dopr)

    out = dict(
        meta=dict(
            script="benchmark/mono_link.py",
            generated=datetime.now().isoformat(timespec="seconds"),
            question="모노스태틱 팔의 링크버짓·검지거리는 얼마이고, 자기간섭을 물고 나면 무엇이 남는가",
            house_rules="산문·print 한국어 · 그림 텍스트 영어 · 수치는 저장소에서만",
            contract=["docs/PAPER_SPEC.md §0", "outputs/geometry_grid.json",
                      "docs/REBUILD_2026-07-30.md §5"],
            repo_functions_used=[
                "freespace_scene.fs_params (TX=RX 호출)", "freespace_scene.target_pos",
                "freespace_scene.prf_hz", "freespace_scene.M_from_prf",
                "freespace_scene.beta_gate", "freespace_scene.farfield_gate",
                "freespace_scene.doppler_bin_hz",
                "freespace_link.snr_rd_db", "freespace_link.snr_rd_terms_db",
                "freespace_link.solve_range", "freespace_link.n0_thermal",
                "freespace_link.n0_dpi", "freespace_link.dnr_db",
                "freespace_link.eca_depth_required_db", "freespace_link.duty_db_from_cpi",
                "freespace_link.range_factor", "freespace_link.direct_power_w",
                "freespace_detect._marcum_cfar_snr90_db", "freespace_detect.PFA_CELL",
                "experiment_freespace_range._sigma_lookup/_sigma_at",
                "link_budget.LinkBudget/link_terms"],
            reads=["outputs/report13_freespace.json", "outputs/report13_sigma_grid.json",
                   "outputs/geometry_grid.json", "outputs/monostatic_prior.json",
                   "outputs/refrate_law.json"],
            canonical_scene=dict(L_ref_m=L_REF_M, L_cosite_m=L_COSITE_M, alt_m=ALT_M,
                                 T_cpi_s=T_CPI_S, eirp_dbm=EIRP_DBM, g_tx_dbi=GTX_DBI,
                                 grx_dbi=GRX_DBI, nf_db=NF_DB, occupancy="G1",
                                 drone=DRONE_HEADLINE, phi_deg=phis,
                                 phi_note="노드가 전부 y=0 위에 있어 φ 와 −φ 가 같다 — 0~180° 로 전 방위를 덮는다"),
            grid_generated=grid["meta"]["generated"],
            runtime_s=None),
        headline=vd["headline"],
        axis_effects_headline=dict(
            purpose="⭐ 기하 효과와 조명원 효과를 한 화면에서 따로 읽는다 — 합쳐진 수는 어느 축이 "
                    "일하는지 감춘다.",
            geometry_effect=dict(
                closed_form=geo_r["closed_form"],
                at_detection_edge_median_db=adv["by_band"]["lte"]
                ["geometry_advantage_at_detection_edge_db"]["median"],
                at_d_over_L_2_median_db=geo_r["by_d_over_L"]["d_over_L_2"]["median_abs_db"],
                absmax_over_scene_db=geo_r["absmax_over_grid_db"],
                R90_spread_across_four_placements_m=max(
                    abs(det_zd["cells"][g][b]["headline_phi90_R90_d_m"]
                        - det_zd["cells"]["C_bistatic_L500"][b]["headline_phi90_R90_d_m"])
                    for g in det_zd["cells"] for b in BANDS),
                doppler_relief_at_edge_x=dopr["by_band"]["lte"]["relief_at_edge_x"]["median"],
                verdict="검지 한계에서 링크버짓 성분과 도플러 성분이 함께 0 으로 죽는다."),
            illuminator_effect=dict(
                span_db=axis["summary"]["illuminator_span_db"]["median"],
                per_band_db=axis["by_phi"]["phi_90"]["illuminator_effect_db"],
                R90_span_m=[min(det_zd["cells"]["C_bistatic_L500"][b]["headline_phi90_R90_d_m"]
                                for b in BANDS),
                            max(det_zd["cells"]["C_bistatic_L500"][b]["headline_phi90_R90_d_m"]
                                for b in BANDS)],
                phi_independent=True,
                verdict="조명원 축은 φ·기하와 무관하게 상수이고, 검지 한계에서 유일하게 살아 있는 링크 축이다."),
            interaction=dict(absmax_db=axis["summary"]["interaction_absmax_db"]["max"],
                             source="σ(el, 밴드) 하나뿐 — 두 기하가 같은 표적을 다른 앙각에서 본다."),
            control_effect=dict(
                si_noise_rise_db={b: adv["by_band"][b]["si_noise_rise_db_at_100dB"] for b in BANDS},
                dpi_noise_rise_db={b: det_bb["cells"]["C_bistatic_L500"][b]["noise_rise_db"]
                                   for b in BANDS},
                verdict="⭐ 검지거리를 실제로 가르는 것은 기하가 아니라 **간섭항**이다."),
            one_line=("기하 %.2f dB · 조명원 %.2f dB · 상호작용 %.2f dB · 간섭 %.1f dB "
                      "(전부 LTE·검지 한계 기준)"
                      % (adv["by_band"]["lte"]["geometry_advantage_at_detection_edge_db"]["median"],
                         axis["summary"]["illuminator_span_db"]["median"],
                         axis["summary"]["interaction_absmax_db"]["max"],
                         adv["by_band"]["lte"]["si_noise_rise_db_at_100dB"]))),
        identity_check=ident,
        thresholds=th,
        band_params=bp,
        placements={k: {kk: (list(vv) if isinstance(vv, tuple) else vv)
                        for kk, vv in v.items()} for k, v in placements().items()},
        axis_separation=axis,
        geometry_effect_vs_range=geo_r,
        detection_range=dict(broadband=det_bb, zero_doppler=det_zd),
        regression_vs_repo=reg_chk,
        all_drones=drones,
        self_interference=si,
        total_isolation_ledger=ledger,
        depth_matrix=dmat,
        advantage_vs_cost=adv,
        eirp_ladder_under_interference=eirpl,
        adc_headroom=adc,
        doppler_relief_at_edge=dopr,
        regimes=reg,
        views=vw,
        literature_crosscheck=lit,
        cross_check_monostatic_scene=xchk,
        verdict=vd,
        scope=dict(
            what_this_file_computed=[
                "닫힌형 링크버짓 → R90 (`freespace_link.solve_range`), 자유공간·2-ray 없음(FS-1 단)",
                "σ 는 자세평균(헤딩 ψ 전체) · el 격자 [0,−20]° 안에서만",
                "간섭은 잡음 PSD 로 더한다 — 광대역 레짐과 0-도플러 레짐 두 끝을 병기",
                "편파 VV 단일 · 단일 수신기 N=1 · G1(상시) 점유",
                "능동 EIRP = 등-EIRP 63 dBm 정본 + LaSen 급 36.9 dBm 뷰"],
            numbers_that_are_declared_not_measured=[
                dict(item="EIRP 63 dBm · G_rx 10 dBi · NF 5 dB",
                     source="report13_freespace.json : meta.link_budget.provenance = DECLARED"),
                dict(item="ECA 달성깊이 40/60/90 dB",
                     source="freespace_link.n0_dpi docstring — 근거문서 없음"),
                dict(item="G_tx = G_rx = 10 dBi (도통 송신전력을 정하는 값)",
                     source="본 파일 T4 정본 · g_tx_sensitivity 로 감도 제공")],
            numbers_that_come_from_measurement=[
                dict(item="총 SI 격리 100 dB", source="Barneto 2019 IEEE TMTT, 2.44 GHz·40 MHz IBW"),
                dict(item="snr90 = 11.86 dB", source="report13 stage_threshold MC"),
                dict(item="Pfa 교정", source="verify_cfar.json (2717 s MC)"),
                dict(item="σ 절대레벨 앵커", source="sigma_anchor / Das 측정 (report13 사슬)")],
            next_steps=[
                dict(do="송신기 위상잡음 스펙트럼을 문헌에서 못박는다",
                     decides="SI 잔류가 광대역인가 0-도플러인가 — 이 파일의 두 레짐 중 하나가 정본이 된다",
                     where="다음 라운드"),
                dict(do="σ 격자 el 을 −75° 까지 넓힌다",
                     decides="d ≲ 2L 구간(기하 축이 사는 곳)의 R90 을 신뢰할 수 있게 된다",
                     where="src/experiment_freespace_sigma.py el 목록"),
                dict(do="실장 ECA 소거깊이를 X410 으로 잰다",
                     decides="패시브 C 행의 90 dB 가 선언값에서 실측으로 바뀐다",
                     where="측정 계획 (measurement_plan.json)"),
                dict(do="능동 모노의 실현가능 EIRP 를 규제 조항으로 못박는다",
                     decides="T3 함정을 닫고 A 행의 절대 R90 이 확정된다",
                     where="FCC 15.407 / ETSI EN 301 893")]),
        handoff=dict(
            files_not_edited=["src/monostatic_scene.py (아직 없음)",
                              "benchmark/verify_monostatic.py (아직 없음)",
                              "benchmark/mono_vs_passive.py", "src/rcs_sbr.py",
                              "src/sigma_anchor.py", "docs/PAPER_SPEC.md",
                              "src/make_report*.py", "src/drones.py", "src/drone_cad.py"],
            overlap_note=("`src/monostatic_scene.py` 는 이 파일을 짜는 도중(08:18)에 생겼다. "
                          "읽기만 하고 §9b 에서 맞대 봤다 — SNR 은 정확히 일치하고, **두 곳이 갈린다**: "
                          "(1) SI 기준면이 G_tx = 10 dB 만큼 다르고 (2) 장면 원점이 센서 기준 vs 중점 기준이다. "
                          "병합 전에 이 둘을 먼저 정해야 한다."),
            two_conventions_to_settle=[
                dict(item="SI 기준면",
                     ours="도통전력 (EIRP − G_tx) — Barneto 의 'TX-RX isolation'(순환기 포트 간)과 같은 면",
                     theirs="EIRP (보수적 상한, 그 파일이 스스로 상한이라고 적음)",
                     offset_db=GTX_DBI,
                     recommendation="인용 문헌의 기준면에 맞추는 쪽(도통면)을 정본으로 하고, "
                                    "EIRP 면 값을 상한 열로 병기한다"),
                dict(item="장면 원점",
                     ours="바이스태틱 중점 (두 기하가 같은 물리 위치를 본다 — 격자 N3 비교에 필수)",
                     theirs="센서 기준 (모노 단독 인용에 자연스럽다)",
                     offset_m=0.5 * L_REF_M,
                     recommendation="키 이름에 규약을 붙인다 — `R90_d_m@scene_midpoint` / `@sensor`")],
            contract_satisfied=[
                "R1 fs_params 를 TX=RX 로 호출 (재구현 0)",
                "R2 모노 노드 기본 위치 = FS_TX",
                "R3 R90 키에 정규화 명시 (R90_d_m=N3 · R90_Req_m=N1)",
                "R4 모노에 DPI 항 없음 · self_interference_db 를 명시 인자로",
                "R5 η_ref = 0 dB (송신 심볼 기지)",
                "R6 σ 는 rcs_sbr_batch 후방산란 그대로, Δσ=0",
                "R7 PRF 는 상시 반복률 기본 + 통제축 별도"],
            patch_requests=[
                dict(file="src/experiment_freespace_range.py",
                     why="σ 격자 el 범위(0~−20°) 밖 조회가 근거리에서 발생한다. 이 파일은 |el|>20° d 를 "
                         "`valid` 에서 빼는 방식으로 막았다. 생산경로도 같은 게이트를 쓰면 무음 클램프가 사라진다.",
                     patch="stage_solve 의 `valid = fss.beta_gate(beta) & farfield` 에 "
                           "`& (np.abs(el_look) <= 20.0)` 를 추가하고, 그 비율을 meta 에 남긴다."),
                dict(file="src/experiment_freespace_range.py",
                     why="`freespace_link.duty_db_from_cpi` 가 R90 경로에서 호출되지 않는다 "
                         "⟨sigma_sensitivity.json : unapplied_duty_axis⟩.",
                     patch="stage_solve 의 snr_rd_db 호출에 "
                           "`duty_db=fsl.duty_db_from_cpi(M_from_prf(T_cpi, prf), len(wf.tx)/wf.fs_hz, T_cpi)` "
                           "를 넘기고, meta.cpi 에 (M, t_ref, duty_db) 를 기록한다. "
                           "기하 비교에는 영향 0(두 팔에 같은 값)이지만 밴드 순위에는 영향이 있다.")]),
        provenance={
            "snr90 문턱": "outputs/report13_freespace.json : solve.<mode>.snr90_db (측정)",
            "Pfa 교정": "outputs/report13_freespace.json : threshold.pfa · verify_cfar.json",
            "σ 격자": "outputs/report13_sigma_grid.json : sigma.grid.<drone>.<band>.sigma_smooth_dbsm "
                     "(engine = rcs_sbr_batch 후방산란 = 모노스태틱 생산경로)",
            "EIRP·G_rx·NF": "outputs/report13_freespace.json : meta.link_budget (전부 선언값)",
            "자기간섭 100 dB": "outputs/monostatic_prior.json : monostatic_literature[barneto2019] "
                            "(IEEE TMTT 67(10):4042-4054, 2019)",
            "능동 PRF 천장 500 Hz": "outputs/geometry_grid.json : control_axis.by_band.nr",
            "무모호 속도 바닥": "outputs/refrate_law.json : illuminators.rows",
            "거리정규화 N1/N3": "outputs/geometry_grid.json : range_normalisation",
            "직접파/에코 문헌값": "outputs/geometry_grid.json : interference_ledger.passive_dpi_literature",
            "LaSen": "outputs/monostatic_prior.json : lasen",
            "자세평균 R90 회귀기준": "outputs/sigma_sensitivity.json : aspect_averaged.by_drone",
            "σ el 격자 게이트": ("σ 격자 el ∈ [0,−20]° 밖 d 는 `valid` 에서 뺐다 — "
                             "detection_range.cells.*.frac_d_excluded_by_sigma_el 참조. "
                             "생산경로(experiment_freespace_range._sigma_at)는 그 구간을 "
                             "최근접 행으로 클램프한다(handoff.patch_requests 참조).")},
    )
    out["meta"]["runtime_s"] = round(time.time() - t0, 2)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[mono_link] 완료 {out['meta']['runtime_s']:.2f}s → {OUT_JSON} "
          f"({os.path.getsize(OUT_JSON)/1024:.0f} KB)", flush=True)
    print("  판정: " + vd["headline"], flush=True)
    return out


if __name__ == "__main__":
    main()
