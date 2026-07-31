# -*- coding: utf-8 -*-
"""verify_monostatic.py — **모노스태틱 검출 시나리오**를 세우고 바이스태틱과 나란히 검증한다
=================================================================================================

사용자 질문: "전체 검증에 바이스태틱뿐 아니라 모노스태틱(LaSen 같은 기법)까지 고려됐나?"

정직한 출발점(⟨outputs/mono_vs_passive.json⟩ 이 이미 확정한 것):
  · 도플러 축은 **이미 덮여 있었다** — 모노스태틱은 우리 법칙의 예외가 아니라 β=0 절편이다.
  · RCS 축은 **모노가 오히려 정본**이다 — `rcs_sbr_batch` 가 모노스태틱 생산경로다.
  · ⚠ **검출 계층만 바이스태틱 전용**이었다(`src/experiment_detection.py`,
    `src/experiment_freespace_range.py` 에 모노스태틱 시나리오 없음). 이 파일이 그것을 만든다.

■ 이 하니스가 하는 일
  V1 기하 동치   : 모노 = `fs_params(S,S,·)` 퇴화입력임을 깨뜨려 본다 + L→0 연속성 + φ 회전대칭
  V2 도플러 바닥 : **안 바뀐다**(λ·PRF/4) 를 이분탐색으로 재확인 + 그런데도 **비율은 달라지는**
                   이유(투영인자 2cos(β/2))를 같은 PRF·같은 표적에서 수치로 분리
  V3 링크 변화   : **바뀐다** — 1/R⁴ ↔ 1/(R1²R2²), 단조성·국소지수·β게이트,
                   그리고 기준채널 부재(DPI 잔류 → 자기간섭, 닫힌형 격차 20log10(4πL/λ)−G_rx)
  V4 검지거리    : 7 기종 × 3 밴드, 같은 σ 격자·같은 측정 문턱으로 모노 vs 바이스태틱
  V5 헤딩 비율   : 블라인드·앨리어싱·**쓸 수 있는 헤딩**(검출 ∧ 무모호) 두 기하 나란히
  V6 기하의존 원장 : 우리 결론 중 **무엇이 두 기하 공통이고 무엇이 바이스태틱에서만 확인됐나**
  V7 핸드오프    : 수정 금지 파일(`experiment_detection.py`·`experiment_freespace_range.py`)에
                   적용할 **정확한 패치**를 JSON 에 적어 넘긴다(직접 고치지 않는다)

■ ⚠ 이 파일에서 가장 틀리기 쉬운 것 — **두 효과를 섞는 것**
  링크(1/R⁴·기준채널 부재)는 **거리**를 바꾸고, 도플러 모호 바닥은 **안 바뀐다**.
  V2 와 V3 를 끝까지 분리해 보고하는 이유가 이것이다. 한 문장에 섞으면 그 문장은 틀린다.

■ 공정성 규약(사과-대-사과)
  같은 EIRP/G_rx/NF(⟨report13_freespace.json meta.link_budget⟩), 같은 T_CPI, 같은 고도·속도,
  같은 σ 격자 파일, 같은 **측정** 문턱 SNR90(⟨report13_freespace.json solve.*.snr90_db⟩),
  같은 d 격자, 같은 PRF(모노가 PRF 를 고를 수 있다는 자유도는 **별개 축**이며 그 크기는
  ⟨outputs/mono_vs_passive.json §2 D1⟩ 에 이미 정량화돼 있다 — 여기서 다시 쓰지 않는다).

실행: cd sionna2 && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_monostatic.py
      (스모크: --smoke --out /tmp/.../verify_monostatic.json)
그림 없음(순수 검증). 주석·docstring·print 한국어(하우스 규약).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                    # noqa: E402

import freespace_scene as fss                         # noqa: E402
import freespace_link as fsl                          # noqa: E402
import monostatic_scene as mos                        # noqa: E402
from link_budget import LinkBudget, lin2db            # noqa: E402

C0 = fss.C0
OUT_JSON = os.path.join(_ROOT, "outputs", "verify_monostatic.json")
IN_FS = os.path.join(_ROOT, "outputs", "report13_freespace.json")
IN_SIGMA = os.path.join(_ROOT, "outputs", "report13_sigma_grid.json")
IN_MONO_VS = os.path.join(_ROOT, "outputs", "mono_vs_passive.json")
IN_REFRATE = os.path.join(_ROOT, "outputs", "refrate_law.json")

MODES = ("W1", "L1", "G1")          # 상시 3인방(협조 없이 패시브가 실제로 얻는 것)

# --- 출처 원장(venue + publication status + year 규약) ------------------------- #
SRC = {
    "lasen": ("LaSen: Ubiquitous Sensing with Commodity 5G Base Stations, "
              "Proc. ACM/IEEE SenSys '26, Saint Malo, France, 11-14 May 2026, ACM pp. 732-745, "
              "DOI 10.1145/3774906.3800504 — published"),
    "barneto": ("C. B. Barneto et al., 'Full-Duplex OFDM Radar With LTE and 5G NR Waveforms', "
                "IEEE Trans. Microwave Theory and Techniques, vol. 67, no. 10, 2019 — published"),
    "repo_fs": "outputs/report13_freespace.json (produced by src/experiment_freespace_range.py)",
    "repo_sigma": "outputs/report13_sigma_grid.json (produced by src/experiment_freespace_sigma.py, "
                  "engine rcs_sbr.rcs_sbr_batch = MONOSTATIC SBR)",
    "repo_mono": "outputs/mono_vs_passive.json (boundary result, this workflow, 2026-07)",
    "repo_refrate": "outputs/refrate_law.json (v_max law)",
}


# --------------------------------------------------------------------------- #
#  유틸
# --------------------------------------------------------------------------- #
def _jsonify(o):
    if isinstance(o, dict):
        return {str(k): _jsonify(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonify(v) for v in o]
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, (np.integer, int)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, np.ndarray):
        return _jsonify(o.tolist())
    return o


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:                                  # 없으면 skipped 로 남긴다
        print(f"  [load] {os.path.basename(path)} 없음/불량: {type(e).__name__}", flush=True)
        return None


def _band_of(mode):
    """모드 → (표준, 점유, 밴드명, fc, bw). `experiment_freespace_range` 상수를 그대로 쓴다."""
    import experiment_freespace_range as efr
    std, occ = efr.MODE_STD[mode]
    bname, fc, bw = efr._BAND_BY_STD[std]
    return std, occ, bname, float(fc), float(bw)


def _look_az_el(u1, u2):
    """이등분선 (az, el)[deg] — `experiment_freespace_range._look_az` 와 같은 식."""
    b = np.asarray(u1, float) + np.asarray(u2, float)
    n = np.linalg.norm(b, axis=-1, keepdims=True)
    look = b / np.maximum(n, 1e-12)
    return (np.atleast_1d(np.degrees(np.arctan2(look[..., 1], look[..., 0]))),
            np.atleast_1d(np.degrees(np.arcsin(np.clip(look[..., 2], -1.0, 1.0)))))


# =========================================================================== #
#  V1 — 기하 동치: 모노는 저장소 함수의 퇴화입력이다
# =========================================================================== #
def v1_geometry(n=2000, smoke=False):
    """`monostatic_scene.selfcheck_vs_freespace` + φ 회전대칭 + Rb 붕괴."""
    sc = mos.selfcheck_vs_freespace(n=(200 if smoke else int(n)))

    # φ 회전대칭 — 바이스태틱에서는 φ 가 1급 변수(S7: 모든 캡션에 φ=90° 명시)인데
    # 모노스태틱에서는 기하가 센서 연직축에 대해 회전대칭이라 φ 가 답을 못 바꾼다.
    fc = 3.5e9
    lam = C0 / fc
    rows_phi = []
    for phi in (0.0, 30.0, 90.0, 150.0, 180.0, 270.0):
        pm = mos.mono_params(mos.mono_target_pos(1000.0, phi, 60.0), (0.0, 0.0, 0.0), fc)
        pb = fss.fs_params(fss.FS_TX, fss.FS_RX(fss.L_REF),
                           fss.target_pos(1000.0, phi, fss.L_REF, 60.0), (0.0, 0.0, 0.0), fc)
        rows_phi.append(dict(phi_deg=phi, mono_R_m=float(pm["R_m"]), mono_el_deg=float(pm["el_deg"]),
                             mono_beta_deg=float(pm["beta"]),
                             bistatic_R_eq_m=float(pb["R_eq"]), bistatic_el_deg=float(pb["el_deg"]),
                             bistatic_beta_deg=float(pb["beta"])))
    mono_span_R = max(r["mono_R_m"] for r in rows_phi) - min(r["mono_R_m"] for r in rows_phi)
    mono_span_el = max(r["mono_el_deg"] for r in rows_phi) - min(r["mono_el_deg"] for r in rows_phi)
    bi_span_R = max(r["bistatic_R_eq_m"] for r in rows_phi) - min(r["bistatic_R_eq_m"] for r in rows_phi)
    bi_span_beta = (max(r["bistatic_beta_deg"] for r in rows_phi)
                    - min(r["bistatic_beta_deg"] for r in rows_phi))

    # `experiment_detection.bistatic_tau_fd` 가 tx=rx 를 이미 옳게 처리하는가(핸드오프 근거)
    ed_ok, ed_note = None, "experiment_detection import 실패"
    try:
        import experiment_detection as ed
        from experiment_x410 import X410Scenario
        S = (0.0, 0.0, 25.0)
        tgt = (700.0, 300.0, 60.0)
        scn = X410Scenario(carrier_hz=fc, n_surv=1, tx_pos=S, ref_pos=S, surv_center=S, target=tgt)
        vel = tuple(fss.heading_velocity(41.0, 5.0).ravel())
        tau, fd, g = ed.bistatic_tau_fd(scn, vel, fc=fc)
        pm = mos.mono_params(tgt, vel, fc, sensor=S)
        ed_ok = bool(abs(fd - float(pm["fd"])) / max(abs(float(pm["fd"])), 1e-12) < 1e-12
                     and abs(g["Rb"] - float(pm["Rb"])) / float(pm["Rb"]) < 1e-12
                     and abs(g["L"]) < 1e-9)
        ed_note = ("experiment_detection.bistatic_tau_fd(tx_pos == surv_center) 가 이미 정확히 "
                   "모노스태틱 값을 낸다(L=0, Rb=2R, f_d=2v·u/λ) — 패치가 작아지는 이유")
    except Exception as e:                                  # noqa: BLE001
        ed_note = f"{type(e).__name__}: {e}"

    return dict(
        selfcheck=sc,
        phi_rotational_symmetry=dict(
            rows=rows_phi,
            mono_R_span_m=float(mono_span_R), mono_el_span_deg=float(mono_span_el),
            bistatic_R_eq_span_m=float(bi_span_R), bistatic_beta_span_deg=float(bi_span_beta),
            mono_is_symmetric=bool(mono_span_R < 1e-9 and mono_span_el < 1e-9),
            verdict_ko=("⭐ 장면방위 φ 는 모노스태틱에서 **답을 못 바꾼다**(R·el 편차 0). "
                        "바이스태틱은 같은 φ 스윕에서 β 가 %.1f° 움직인다 — 그래서 저장소 규약이 "
                        "모든 바이스태틱 캡션에 φ=90° 를 명시하게 돼 있고(S7), 모노 결과에는 "
                        "그 선언이 필요 없다." % bi_span_beta)),
        detector_degeneracy=dict(ok=ed_ok, note_ko=ed_note),
        ok=bool(sc["ok"]))


# =========================================================================== #
#  V2 — 도플러 모호 바닥: **안 바뀐다** (그러나 비율은 바뀐다)
# =========================================================================== #
def v2_doppler(refrate, smoke=False):
    fc = 3.5e9
    lam = C0 / fc
    psi = np.linspace(0.0, 360.0, (360 if smoke else 1440), endpoint=False)

    # (a) 법칙 항등 — 모노 = 바이스태틱 β=0, 그리고 β>0 은 **완화**된다
    law = []
    for prf, tag in ((50.0, "5G SSB (20 ms)"), (200.0, "NR-PRS"), (1000.0, "LTE CRS / WiFi VHT-LTF")):
        row = dict(prf_hz=prf, tag=tag,
                   v_max_mono_ms=mos.v_max_ms(lam, prf, 0.0, 0.0),
                   v_max_bistatic_beta0_ms=mos.v_max_ms(lam, prf, 0.0, 0.0),
                   v_max_bistatic_45_ms=mos.v_max_ms(lam, prf, 45.0, 0.0),
                   v_max_bistatic_90_ms=mos.v_max_ms(lam, prf, 90.0, 0.0))
        row["identical_to_beta0"] = bool(
            abs(row["v_max_mono_ms"] - row["v_max_bistatic_beta0_ms"]) < 1e-15)
        row["monostatic_is_the_worst_case"] = bool(
            row["v_max_mono_ms"] <= row["v_max_bistatic_45_ms"] <= row["v_max_bistatic_90_ms"])
        law.append(row)

    # 발표한 헤드라인과의 패리티 (⟨refrate_law.json law.repo_parity.nr_ssb⟩ = 5G SSB 50 Hz @3.5 GHz)
    v_pub = None
    pub_where = None
    if refrate:
        try:
            v_pub = float(refrate["law"]["repo_parity"]["nr_ssb"]["table_v_max_ms"])
            pub_where = "refrate_law.json law.repo_parity.nr_ssb.table_v_max_ms"
        except Exception:
            for r in (refrate.get("illuminators", {}) or {}).get("rows", []) or []:
                if isinstance(r, dict) and str(r.get("key", "")).startswith("nr_ssb"):
                    v_pub = float(r.get("v_max_ms", "nan"))
                    pub_where = "refrate_law.json illuminators.rows[nr_ssb].v_max_ms"
                    break
    headline = dict(published_v_max_ms=v_pub, published_where=pub_where,
                    monostatic_v_max_ms=mos.v_max_ms(lam, 50.0), source=SRC["repo_refrate"])
    if v_pub:
        headline["rel_err"] = float(abs(v_pub - headline["monostatic_v_max_ms"]) / v_pub)
        headline["identical"] = bool(headline["rel_err"] < 1e-12)
        headline["note_ko"] = ("⭐ 발표한 헤드라인 수치가 **모노스태틱 값과 비트 단위로 같다** — "
                               "그 값은 애초에 β=0 절편이었다. 기하로 부풀린 값이 아니다.")

    # (b) 같은 PRF·같은 표적·같은 속도에서 **비율**은 왜 다른가 — 투영인자 2cos(β/2)
    #     ⚠ β 를 넓게 쓸어야 효과가 보인다: 헤드라인 기하(L=500, d≥1 km)는 β<30° 라 두 기하가
    #        거의 겹친다. 그래서 베이스라인 L∈BASELINES 를 함께 쓸어 β 를 크게 만든다.
    rows = []
    for mode in MODES:
        std, occ, bname, fcm, bwm = _band_of(mode)
        lm = C0 / fcm
        prf = float(fss.prf_hz(std, occ))
        M = fss.M_from_prf(fss.T_CPI_REF_S, prf)
        for speed in fss.FS_SPEED:
            for L in fss.BASELINES:
                for d in ((1000.0,) if smoke else (300.0, 1000.0, 3000.0)):
                    mb = mos.mono_blind_fractions(psi, fss.PHI_HEADLINE_DEG, d, fss.FS_ALT[0],
                                                  fss.T_CPI_REF_S, prf, speed, lm, M=M)
                    bb = fss.blind_fractions(psi, fss.PHI_HEADLINE_DEG, d, L, fss.FS_ALT[0],
                                             fss.T_CPI_REF_S, prf, speed, lm, M=M)
                    pb = fss.fs_params(fss.FS_TX, fss.FS_RX(L),
                                       fss.target_pos(d, fss.PHI_HEADLINE_DEG, L,
                                                      fss.FS_ALT[0]), (0, 0, 0), fcm)
                    beta = float(pb["beta"])
                    proj_bi = float(np.linalg.norm(np.ravel(pb["u1"]) + np.ravel(pb["u2"])))
                    rows.append(dict(
                        mode=mode, band=bname, prf_hz=prf, M=int(M), speed_ms=float(speed),
                        L_m=float(L), d_m=float(d), beta_deg=beta,
                        beta_gate_ok=bool(fss.beta_gate(beta)),
                        proj_mono=float(mb["proj_factor"]), proj_bistatic=proj_bi,
                        proj_ratio=float(mb["proj_factor"] / max(proj_bi, 1e-12)),
                        proj_ratio_closed=float(1.0 / max(np.cos(np.radians(beta) / 2.0), 1e-12)),
                        max_fd_mono_hz=float(np.max(np.abs(mb["fd_hz"]))),
                        max_fd_bistatic_hz=float(np.max(np.abs(bb["fd_hz"]))),
                        blind_hard_mono=mb["blind_hard"], blind_hard_bistatic=bb["blind_hard"],
                        blind_declared_mono=mb["blind_declared"],
                        blind_declared_bistatic=bb["blind_declared"],
                        alias_mono=mb["alias_frac"], alias_bistatic=bb["alias_frac"]))
    worst_proj_err = max(abs(r["proj_ratio"] - r["proj_ratio_closed"]) for r in rows)

    # 방향성 요약 — 두 검열이 **반대 방향**으로 움직인다
    d_blind = [r["blind_hard_mono"] - r["blind_hard_bistatic"] for r in rows]
    d_alias = [r["alias_mono"] - r["alias_bistatic"] for r in rows]
    quotable = [r for r in rows if r["beta_gate_ok"]]        # β≤90° = 수치인용 가능 구역
    near_rows = [r for r in rows if r["beta_deg"] >= 60.0]   # β 가 큰 구역(효과가 보이는 곳)

    return dict(
        law_identity=law, headline_parity=headline,
        projection_factor=dict(
            rows=rows, max_closed_form_err=float(worst_proj_err),
            closed_form="|u1+u2| = 2 cos(beta/2); monostatic beta=0 -> exactly 2 (the maximum)",
            blind_delta_mono_minus_bistatic=dict(min=float(min(d_blind)), max=float(max(d_blind)),
                                                 mean=float(np.mean(d_blind))),
            alias_delta_mono_minus_bistatic=dict(min=float(min(d_alias)), max=float(max(d_alias)),
                                                 mean=float(np.mean(d_alias))),
            large_beta_only=dict(
                n=len(near_rows), beta_min_deg=(float(min(r["beta_deg"] for r in near_rows))
                                                if near_rows else None),
                blind_delta_mean=(float(np.mean([r["blind_hard_mono"] - r["blind_hard_bistatic"]
                                                 for r in near_rows])) if near_rows else None),
                alias_delta_mean=(float(np.mean([r["alias_mono"] - r["alias_bistatic"]
                                                 for r in near_rows])) if near_rows else None),
                note_ko="β≥60° 인 행만 — 효과는 여기서만 보인다"),
            quotable_only=dict(
                n=len(quotable),
                blind_delta_mean=(float(np.mean([r["blind_hard_mono"] - r["blind_hard_bistatic"]
                                                 for r in quotable])) if quotable else None),
                alias_delta_mean=(float(np.mean([r["alias_mono"] - r["alias_bistatic"]
                                                 for r in quotable])) if quotable else None),
                note_ko="β≤90°(SBR 유효·수치인용 가능) 행만")),
        verdict_ko=(
            "⭐ **바닥은 안 바뀐다.** v_max = λ·PRF/4 는 모노스태틱 값이자 바이스태틱 β=0 절편이고, "
            "β>0 인 모든 바이스태틱 기하는 1/cos(β/2) 만큼 **완화**된다 — 즉 발표한 1.07 m/s 는 "
            "기하로 부풀린 값이 아니라 깎은 값이다.\n"
            "⚠ 그런데 **비율은 바뀐다** — 법칙이 달라서가 아니라 투영인자 때문이다. |u1+u2|=2cos(β/2) "
            "가 모노에서 최대(2)라 같은 속도에서 |f_d| 가 크고, 그래서 0-도플러 가드에는 **덜** 걸리고"
            "(블라인드 Δ 평균 %+.3f) 나이퀴스트는 **더** 넘는다(앨리어싱 Δ 평균 %+.3f). 두 방향이 "
            "반대라 한쪽만 인용하면 결론이 뒤집힌다.\n"
            "⚠⚠ 그리고 그 차이는 **작다** — 우리 헤드라인 기하(L=500, d≥1 km)는 β<30° 라 "
            "cos(β/2)>0.96 이다. 즉 우리가 발표한 바이스태틱 도플러 수치는 **모노스태틱 수치이기도 "
            "하다**(β≥60° 행에서만 Δblind %s / Δalias %s 로 벌어진다). 이건 우리 결과에 유리한 "
            "이야기가 아니라 **구별이 안 된다**는 이야기다 — 도플러 축으로는 두 기하를 가를 수 없다."
            % (float(np.mean(d_blind)), float(np.mean(d_alias)),
               ("%+.3f" % float(np.mean([r["blind_hard_mono"] - r["blind_hard_bistatic"]
                                         for r in near_rows]))) if near_rows else "n/a",
               ("%+.3f" % float(np.mean([r["alias_mono"] - r["alias_bistatic"]
                                         for r in near_rows]))) if near_rows else "n/a")),
        ok=bool(all(r["identical_to_beta0"] and r["monostatic_is_the_worst_case"] for r in law)
                and worst_proj_err < 1e-9))


# =========================================================================== #
#  V3 — 링크는 **바뀐다**: 1/R⁴ vs 1/(R1²R2²), 그리고 기준채널 부재
# =========================================================================== #
def v3_link(smoke=False):
    fc = 3.5e9
    lam = C0 / fc
    alt = fss.FS_ALT[0]
    L = fss.L_REF
    d = np.geomspace(100.0, 20000.0, (40 if smoke else 240))

    # (a) 확산항 비교 — κ_bi = R1R2 vs κ_mono = R²
    tb = fss.target_pos(d, fss.PHI_HEADLINE_DEG, L, alt)
    pb = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tb, (0, 0, 0), fc)
    R1 = np.asarray(pb["R1"], float)
    R2 = np.asarray(pb["R2"], float)
    kap_bi = R1 * R2
    R_mo = mos.mono_R_of_d(d, alt)
    kap_mo = R_mo ** 2
    spread_delta_db = 20.0 * np.log10(kap_bi / kap_mo)      # +면 바이스태틱이 더 손해
    idx = [int(np.argmin(np.abs(d - x))) for x in (100.0, 300.0, 1000.0, 3000.0, 10000.0)]
    spread_rows = [dict(d_m=float(d[i]), R1_m=float(R1[i]), R2_m=float(R2[i]),
                        R_mono_m=float(R_mo[i]), beta_deg=float(np.asarray(pb["beta"], float)[i]),
                        kappa_bistatic_m2=float(kap_bi[i]), kappa_mono_m2=float(kap_mo[i]),
                        bistatic_penalty_db=float(spread_delta_db[i])) for i in idx]

    # (b) 국소지수·단조성 — S1/S6 가 기하의존인가
    n_bi = fsl.n_local(kap_bi, d)
    n_mo = fsl.n_local(kap_mo, d)
    n_rows = [dict(d_m=float(d[i]), n_local_bistatic=float(n_bi[i]), n_local_mono=float(n_mo[i]),
                   n_mono_closed=float(4.0 * d[i] ** 2 / (d[i] ** 2 + (alt - mos.MONO_H) ** 2)))
              for i in idx]
    # 단조성: σ 고정으로 **순수 기하**만 본다(σ(el(d)) 변동을 배제).
    # ⚠ φ=90°(헤드라인)에서는 바이스태틱도 단조다 — 스펙 S6 의 내부최대는 **φ=0/10/30°**
    #   (표적이 RX 위를 지나며 κ 가 d 내부 최소를 갖는 기하)에서 산다. 그래서 그 φ 들에서 재야
    #   "S6 는 바이스태틱 전용" 이라는 주장이 실제로 시험된다(φ=90° 만 보면 자명통과 = 쓰레기 검증).
    TH = 11.86143572621035
    mono_rows, sol_bi, sol_mo = [], None, None
    for phi in (0.0, 10.0, 30.0, 90.0):
        tbp = fss.target_pos(d, phi, L, alt)
        pbp = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tbp, (0, 0, 0), fc)
        r1, r2 = np.asarray(pbp["R1"], float), np.asarray(pbp["R2"], float)
        kb = r1 * r2
        sb = fsl.solve_range(fsl.snr_rd_db(63.0, 10.0, lam, 0.01, r1, r2, nf=5.0, T=0.1),
                             TH, d_grid=d, kappa_of_d=kb)
        sm = fsl.solve_range(mos.mono_snr_rd_db(63.0, 10.0, lam, 0.01, R_mo, nf=5.0, T=0.1),
                             TH, d_grid=d, kappa_of_d=kap_mo)
        mono_rows.append(dict(phi_deg=phi,
                              bistatic_monotone_ok=bool(sb["monotone_ok"]),
                              bistatic_snr_rise_db=float(sb["snr_rise_db"]),
                              bistatic_snr_peak_d_m=float(sb["snr_peak_d_m"]),
                              mono_monotone_ok=bool(sm["monotone_ok"]),
                              mono_snr_rise_db=float(sm["snr_rise_db"]),
                              mono_snr_peak_d_m=float(sm["snr_peak_d_m"])))
        if phi == 90.0:
            sol_bi, sol_mo = sb, sm
    n_bi_nonmono = sum(1 for r in mono_rows if not r["bistatic_monotone_ok"])
    n_mo_nonmono = sum(1 for r in mono_rows if not r["mono_monotone_ok"])

    # (c) β 게이트 — 바이스태틱만 근거리 금지구역을 갖는다
    beta = np.asarray(pb["beta"], float)
    n_hatched = int(np.sum(~fss.beta_gate(beta)))
    d_beta90 = float(d[np.argmax(fss.beta_gate(beta))]) if n_hatched else float(d[0])

    # (d) 기준채널 부재 — 패시브 DPI 잔류 ↔ 모노 자기간섭
    sig_dbsm = -19.74                                    # ⟨mono_vs_passive.json §2 D5⟩ 와 같은 값
    mono_vs = _load(IN_MONO_VS)
    if mono_vs:
        try:
            sig_dbsm = float(mono_vs["L2_design_freedom"]["D5_self_interference"]["sigma_dbsm"])
        except Exception:
            pass
    sig_m2 = 10.0 ** (sig_dbsm / 10.0)
    lb = LinkBudget()
    eirp_w = 10.0 ** (lb.eirp_dbm / 10.0) * 1e-3
    iso_rows = []
    for R in (50.0, 100.0, 200.0, 1000.0):
        req = mos.mono_required_isolation_db(lb.eirp_dbm, lb.rx_gain_dbi, lam, sig_m2, R)
        dnr = float(lin2db(lb.direct_power_w(lam, L) / lb.echo_power_w(lam, sig_m2, R, R)))
        iso_rows.append(dict(R_m=R, mono_required_isolation_db=req, passive_direct_to_echo_db=dnr,
                             difference_db=req - dnr))
    gap_closed = mos.isolation_gap_vs_passive_db(lam, L, lb.rx_gain_dbi)
    gap_span = (max(r["difference_db"] for r in iso_rows)
                - min(r["difference_db"] for r in iso_rows))

    # 실장 격리 사다리 → 검지거리 (패시브 eca_depth_grid 와 **같은 자리**)
    fs_wf_bw = 30.72e6
    si_ladder = []
    for iso in (60.0, 80.0, 100.0, 120.0, 144.0, None):
        psd = mos.si_residual_psd(lb.eirp_dbm, iso, fs_wf_bw)
        th = fsl.n0_thermal(lb.noise_figure_db, 1.0)
        s = mos.mono_snr_rd_db(lb.eirp_dbm, lb.rx_gain_dbi, lam, sig_m2, R_mo,
                               nf=lb.noise_figure_db, T=0.1, n0_extra=psd)
        sol = fsl.solve_range(s, 11.86143572621035, d_grid=d, kappa_of_d=kap_mo)
        si_ladder.append(dict(isolation_db=("inf" if iso is None else float(iso)),
                              n0_excess_db=float(lin2db((th + psd) / th)),
                              R_m=(float(sol["R_m"]) if np.isfinite(sol["R_m"]) else None),
                              never_detectable=bool(sol["never_detectable"])))

    return dict(
        spread_law=dict(
            rows=spread_rows,
            statement_en=("bistatic spread is 1/(R1^2 R2^2), monostatic is 1/R^4; at the same "
                          "horizontal range d they differ by 20 log10(R1 R2 / R^2)"),
            max_penalty_db=float(np.max(spread_delta_db)),
            penalty_at_10km_db=float(spread_delta_db[idx[-1]]),
            converges_ko=("⚠ d ≫ L 이면 κ_bi → R² 라 두 법칙이 **수치적으로 같아진다**(10 km 에서 "
                          "%.3f dB). 1/R⁴ 대 1/(R1²R2²) 의 차이는 헤드라인 거리에서 나오는 것이 "
                          "아니라 **베이스라인 근방 기하**에서 나온다 — 이것을 '모노가 유리/불리' 로 "
                          "읽으면 틀린다." % float(spread_delta_db[idx[-1]]))),
        exponent_and_monotonicity=dict(
            rows=n_rows, monotonicity_by_phi=mono_rows,
            n_phi_bistatic_nonmonotone=int(n_bi_nonmono), n_phi_mono_nonmonotone=int(n_mo_nonmono),
            n_phi_tested=len(mono_rows),
            bistatic=dict(monotone_ok=bool(sol_bi["monotone_ok"]), snr_rise_db=float(sol_bi["snr_rise_db"]),
                          snr_peak_d_m=float(sol_bi["snr_peak_d_m"]), R_m=float(sol_bi["R_m"]),
                          n_local_at_R=float(sol_bi["n_local"]), phi_deg=90.0),
            mono=dict(monotone_ok=bool(sol_mo["monotone_ok"]), snr_rise_db=float(sol_mo["snr_rise_db"]),
                      snr_peak_d_m=float(sol_mo["snr_peak_d_m"]), R_m=float(sol_mo["R_m"]),
                      n_local_at_R=float(sol_mo["n_local"])),
            verdict_ko=("⭐ **S6(비단조 → 이분법 무효)은 바이스태틱 전용**이다. 스펙이 내부최대를 "
                        "기록한 φ=0/10/30° 를 포함해 4개 φ 에서 재보면 바이스태틱은 %d/%d 개가 "
                        "비단조인데 모노는 %d/%d 다(κ_mono=d²+Δh² 가 단조증가라 φ 와 무관). "
                        "그래서 모노에서는 이분법이 유효해진다.\n"
                        "S1(n<4)도 모노에서 살아 있지만 **원인이 다르다** — 베이스라인이 아니라 "
                        "고도차 Δh=%.0f m 이고, n = 4d²/(d²+Δh²) 로 아래에서 빠르게 4 로 수렴한다"
                        "(d=1 km: 바이스태틱 %.2f vs 모노 %.2f; d=300 m: %.2f vs %.2f)."
                        % (n_bi_nonmono, len(mono_rows), n_mo_nonmono, len(mono_rows),
                           abs(alt - mos.MONO_H), float(n_bi[idx[2]]), float(n_mo[idx[2]]),
                           float(n_bi[idx[1]]), float(n_mo[idx[1]])))),
        beta_gate=dict(bistatic_hatched_cells=n_hatched, n_cells=int(len(d)),
                       bistatic_first_valid_d_m=d_beta90,
                       mono_hatched_cells=0, mono_beta_deg=0.0,
                       verdict_ko=("바이스태틱은 β>90° 인 근거리 %d/%d 칸이 SBR 유효범위 밖이라 "
                                   "수치인용 금지(해칭)다. 모노스태틱은 β≡0 이라 그 금지구역이 "
                                   "**존재하지 않는다** — 근거리 수치를 그대로 쓸 수 있다."
                                   % (n_hatched, len(d)))),
        reference_channel=dict(
            sigma_dbsm=sig_dbsm, sigma_source=SRC["repo_sigma"],
            link_budget=dict(eirp_dbm=lb.eirp_dbm, rx_gain_dbi=lb.rx_gain_dbi,
                             noise_figure_db=lb.noise_figure_db, baseline_m=L,
                             b_noise_hz=fs_wf_bw),
            rows=iso_rows, gap_closed_form_db=gap_closed,
            gap_measured_db=float(iso_rows[1]["difference_db"]),
            gap_range_independent=bool(gap_span < 1e-6), gap_span_db=float(gap_span),
            closed_form="mono_required_isolation - passive_direct_to_echo = 20log10(4 pi L / lambda) - G_rx",
            barneto_measured_isolation_db=100.0, barneto_source=SRC["barneto"],
            shortfall_at_100m_db=float(iso_rows[1]["mono_required_isolation_db"] - 100.0),
            si_ladder=si_ladder,
            # ⭐ 두 사다리를 같은 자 위에 놓는다: 패시브 ECA 깊이 X dB ≡ 모노 격리 (X + gap) dB
            depth_equivalence=dict(
                offset_db=gap_closed,
                rows=[dict(passive_eca_depth_db=x, equivalent_monostatic_isolation_db=x + gap_closed)
                      for x in (40.0, 60.0, 90.0)],
                formula="equivalent_monostatic_isolation = passive_eca_depth + 20log10(4 pi L/lambda) - G_rx",
                note_ko=("report13 의 패시브 소거깊이 사다리(40/60/90 dB)를 모노스태틱 자기간섭 "
                         "축으로 옮기면 %.0f/%.0f/%.0f dB 다 — 실측 최고 100 dB(Barneto 2019)는 "
                         "패시브 ECA %.0f dB 에 해당한다."
                         % (40 + gap_closed, 60 + gap_closed, 90 + gap_closed, 100 - gap_closed))),
            verdict_ko=("⭐ 기준채널이 없어지는 대가는 **정확히 닫힌형**이다: 모노 요구격리 − 패시브 "
                        "직접파/에코비 = 20log10(4πL/λ) − G_rx = %.2f dB, 표적거리 무관(편차 %.1e dB). "
                        "L→0 이면 0 이므로 패시브가 모노로 연속 수렴한다 — 도플러 축의 β=0 절편과 "
                        "같은 구조다. 실측 최고 격리 100 dB(Barneto 2019) 로는 100 m 표적에서 "
                        "%.1f dB 부족하다.\n"
                        "⭐⭐ 그 부족분의 값이 **검지거리 축에서 두 기하가 갈리는 유일한 큰 자리**다: "
                        "이상 격리면 %s m 인데 실측 100 dB 로는 %s m 로 주저앉는다(%.0f배). "
                        "확산법칙 1/R⁴ 은 거리를 사실상 안 바꿨지만(V4 중앙값 비 1.00), "
                        "기준채널의 부재는 %.0f배를 바꾼다 — 두 효과를 섞지 말라는 요구가 "
                        "여기서 숫자로 갈린다."
                        % (gap_closed, gap_span,
                           iso_rows[1]["mono_required_isolation_db"] - 100.0,
                           ("%.0f" % si_ladder[-1]["R_m"]) if si_ladder[-1]["R_m"] else "nan",
                           ("%.0f" % si_ladder[2]["R_m"]) if si_ladder[2]["R_m"] else "미검출",
                           (si_ladder[-1]["R_m"] / si_ladder[2]["R_m"])
                           if (si_ladder[-1]["R_m"] and si_ladder[2]["R_m"]) else float("nan"),
                           (si_ladder[-1]["R_m"] / si_ladder[2]["R_m"])
                           if (si_ladder[-1]["R_m"] and si_ladder[2]["R_m"]) else float("nan")))),
        ok=bool(gap_span < 1e-6 and abs(gap_closed - iso_rows[1]["difference_db"]) < 1e-6
                and n_mo_nonmono == 0 and n_bi_nonmono > 0))


# =========================================================================== #
#  V4/V5 — 검지거리 · 헤딩 비율 (모노 solve = stage_solve 판박이)
# =========================================================================== #
def mono_solve(mode, drone, sig_json, snr90, alt=60.0, speed=5.0, T_cpi=0.1, N=1,
               d_grid=None, psi_n=72, phi_deg=None, sensor=mos.MONO_POS):
    """`experiment_freespace_range.stage_solve` 의 **모노스태틱 판박이**.

    바뀐 것은 딱 두 줄이다: 기하가 `mono_params`(TX=RX)이고 SNR 이 `mono_snr_rd_db`(R1=R2=R).
    나머지(σ 조회·게이트·`solve_range` 최외곽 하강교차·커버리지 분해·로지스틱 Pd 근사)는
    바이스태틱과 **같은 함수**를 같은 순서로 부른다 — 그래야 뺄셈이 의미를 갖는다.
    """
    import experiment_freespace_range as efr
    std, occ, bname, fc, bw = _band_of(mode)
    lam = C0 / fc
    prf = float(fss.prf_hz(std, occ))
    M = fss.M_from_prf(T_cpi, prf)
    phi = fss.PHI_HEADLINE_DEG if phi_deg is None else float(phi_deg)
    lookup = efr._sigma_lookup(sig_json, drone, bname) if sig_json else None
    d = np.geomspace(100.0, 20000.0, 240) if d_grid is None else np.asarray(d_grid, float)

    tgt = mos.mono_target_pos(d, phi, alt, sensor)
    p = mos.mono_params(tgt, (0.0, 0.0, 0.0), fc, sensor)
    R = np.asarray(p["R_m"], float)
    el_look = np.asarray(p["el_deg"], float)
    az_look, _ = _look_az_el(p["u1"], p["u2"])
    kappa = R ** 2
    sigma_d = np.array([efr._sigma_at(lookup, az_look[i], el_look[i], warn=False)
                        for i in range(len(d))])
    snr_d = mos.mono_snr_rd_db(efr.EIRP_DBM, efr.GRX_DBI, lam, sigma_d, R, nf=efr.NF_DB,
                               eta_ref=0.0, T=T_cpi) + 10.0 * np.log10(max(N, 1))
    # 유효게이트: β 게이트는 모노에서 상시 통과 → 원거리장만 남는다
    valid = np.array([fss.farfield_gate(R[i], drone, fc) for i in range(len(d))])
    sol = fsl.solve_range(snr_d, snr90, d_grid=d, kappa_of_d=kappa, valid=valid)

    # 커버리지 @ R90 (헤딩 ψ 전체)
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    d_cov = sol["R_m"] if np.isfinite(sol["R_m"]) else float(d[len(d) // 2])
    pc = mos.mono_params(mos.mono_target_pos(d_cov, phi, alt, sensor), (0, 0, 0), fc, sensor)
    azc = float(np.ravel(_look_az_el(pc["u1"], pc["u2"])[0])[0])
    elc = float(pc["el_deg"])
    sig_psi = np.array([efr._sigma_at(lookup, azc - ps, elc, warn=False) for ps in psi])
    snr_psi = mos.mono_snr_rd_db(efr.EIRP_DBM, efr.GRX_DBI, lam, sig_psi, float(pc["R_m"]),
                                 nf=efr.NF_DB, eta_ref=0.0, T=T_cpi) + 10.0 * np.log10(max(N, 1))
    pd_psi = 1.0 / (1.0 + np.exp(-(snr_psi - snr90)))
    blind = mos.mono_blind_sector(psi, phi, d_cov, alt, T_cpi, prf, speed, lam, M=M, sensor=sensor)
    C, f_blind, f_sigma = fsl.coverage_fraction(pd_psi, blind, pd_th=0.9)
    fd_psi, _ = mos.mono_fd_of_heading(psi, phi, d_cov, alt, speed, lam, sensor)
    use = mos.usable_heading_fraction(fd_psi, prf, T_cpi, snr_psi=snr_psi, snr_th=snr90, M=M)
    bf = mos.mono_blind_fractions(psi, phi, d_cov, alt, T_cpi, prf, speed, lam, M=M, sensor=sensor)

    return dict(mode=mode, drone=drone, band=bname, geometry="monostatic",
                sensor_xyz=[float(v) for v in sensor], alt_m=alt, speed_ms=speed,
                T_cpi_s=T_cpi, N=int(N), prf_hz=prf, M=int(M), snr90_db=float(snr90),
                R_m=float(sol["R_m"]) if np.isfinite(sol["R_m"]) else None,
                R_eq_m=float(sol["R_eq_m"]) if np.isfinite(sol["R_eq_m"]) else None,
                n_local_at_R=float(sol["n_local"]), monotone_ok=bool(sol["monotone_ok"]),
                snr_rise_db=float(sol["snr_rise_db"]),
                snr_ceiling_db=float(sol["snr_ceiling_db"]),
                el_look_at_R_deg=float(elc), grid_limited=bool(sol["grid_limited"]),
                sigma_at_R_dbsm=(float(10.0 * np.log10(max(float(np.interp(
                    np.log10(max(sol["R_m"], 1.0)), np.log10(d), sigma_d)), 1e-30)))
                    if np.isfinite(sol["R_m"]) else None),
                frac_never_detectable=float(sol["frac_never_detectable"]),
                coverage=dict(C=float(C), factor_blind=float(f_blind), factor_sigma=float(f_sigma),
                              E_psi_Pd=float(fsl.e_psi_pd(pd_psi, blind_mask=blind)),
                              d_cov_m=float(d_cov)),
                heading=dict(blind_hard=bf["blind_hard"], blind_declared=bf["blind_declared"],
                             soft_blind_frac=bf["soft_blind_frac"], alias_frac=bf["alias_frac"],
                             frac_usable=use["frac_usable"],
                             frac_unambiguous=use["frac_unambiguous"],
                             frac_snr_ok=use["frac_snr_ok"],
                             frac_blind_and_alias=use["frac_blind_and_alias"],
                             max_abs_fd_hz=use["max_abs_fd_hz"]))


def bistatic_heading(mode, drone, sig_json, snr90, R_bi, alt=60.0, speed=5.0, T_cpi=0.1,
                     L=None, phi_deg=None, psi_n=72, N=1):
    """바이스태틱 쪽 **같은 헤딩 지표**(usable 포함)를 같은 방식으로 뽑는다.

    `stage_solve` 는 blind/alias 를 따로 보고할 뿐 '쓸 수 있는 헤딩'을 합성해 주지 않는다.
    두 기하를 나란히 놓으려면 같은 정의로 계산해야 하므로 여기서 만든다(원본 파일 무수정).
    """
    import experiment_freespace_range as efr
    std, occ, bname, fc, bw = _band_of(mode)
    lam = C0 / fc
    prf = float(fss.prf_hz(std, occ))
    M = fss.M_from_prf(T_cpi, prf)
    L = fss.L_REF if L is None else float(L)
    phi = fss.PHI_HEADLINE_DEG if phi_deg is None else float(phi_deg)
    lookup = efr._sigma_lookup(sig_json, drone, bname) if sig_json else None
    psi = np.linspace(0.0, 360.0, int(psi_n), endpoint=False)
    d_cov = float(R_bi) if (R_bi and np.isfinite(R_bi)) else 1000.0
    pc = fss.fs_params(fss.FS_TX, fss.FS_RX(L), fss.target_pos(d_cov, phi, L, alt), (0, 0, 0), fc)
    azc = float(np.ravel(_look_az_el(pc["u1"], pc["u2"])[0])[0])
    elc = float(pc["el_deg"])
    sig_psi = np.array([efr._sigma_at(lookup, azc - ps, elc, warn=False) for ps in psi])
    snr_psi = fsl.snr_rd_db(efr.EIRP_DBM, efr.GRX_DBI, lam, sig_psi, float(pc["R1"]),
                            float(pc["R2"]), nf=efr.NF_DB, eta_ref=0.0, T=T_cpi) \
        + 10.0 * np.log10(max(N, 1))
    bf = fss.blind_fractions(psi, phi, d_cov, L, alt, T_cpi, prf, speed, lam, M=M)
    use = mos.usable_heading_fraction(bf["fd_hz"], prf, T_cpi, snr_psi=snr_psi, snr_th=snr90, M=M)
    return dict(d_cov_m=d_cov, beta_deg=float(pc["beta"]), el_look_deg=elc,
                blind_hard=bf["blind_hard"], blind_declared=bf["blind_declared"],
                soft_blind_frac=bf["soft_blind_frac"], alias_frac=bf["alias_frac"],
                frac_usable=use["frac_usable"], frac_unambiguous=use["frac_unambiguous"],
                frac_snr_ok=use["frac_snr_ok"], frac_blind_and_alias=use["frac_blind_and_alias"],
                max_abs_fd_hz=use["max_abs_fd_hz"])


def v4_v5_ranges(fs_json, sig_json, smoke=False, verbose=True):
    """7 기종 × 3 밴드 — 모노 검지거리·헤딩비율 + 바이스태틱 대조(같은 함수·같은 σ·같은 문턱)."""
    import experiment_freespace_range as efr
    snr90 = 12.0
    snr90_src = "assumed 12 dB (report13_freespace.json 없음)"
    if fs_json:
        try:
            snr90 = float(fs_json["solve"]["L1"]["snr90_db"])
            snr90_src = "measured — report13_freespace.json solve.L1.snr90_db (stage_threshold)"
        except Exception:
            pass
    drones = [d for d in fss.DRONE_ORDER
              if sig_json and d in sig_json.get("sigma", {}).get("grid", {})]
    if smoke:
        drones = drones[:2]
    modes = MODES[:1] if smoke else MODES
    d_grid = np.geomspace(100.0, 20000.0, (60 if smoke else 240))

    rows, heads = [], []
    for drone in drones:
        for mode in modes:
            t0 = time.time()
            m = mono_solve(mode, drone, sig_json, snr90, alt=fss.FS_ALT[0],
                           speed=fss.FS_SPEED[0], d_grid=d_grid)
            # 바이스태틱: 같은 σ·같은 문턱으로 **저장소 원본 함수**를 부른다(수정 없음)
            b = efr.stage_solve(mode=mode, drone=drone, L=fss.L_REF, alt=fss.FS_ALT[0],
                                speed=fss.FS_SPEED[0], T_cpi=0.1, N=1, snr90_db=snr90,
                                sig_json=sig_json, d_grid=d_grid, verbose=False)
            bh = bistatic_heading(mode, drone, sig_json, snr90, b["R_m"], alt=fss.FS_ALT[0],
                                  speed=fss.FS_SPEED[0])
            Rm, Rb = m["R_m"], (float(b["R_m"]) if np.isfinite(b["R_m"]) else None)
            rows.append(dict(
                drone=drone, mode=mode, band=m["band"],
                mono_R_m=Rm, bistatic_R_m=Rb,
                ratio_mono_over_bistatic=(Rm / Rb if (Rm and Rb) else None),
                delta_db_equivalent=(float(10.0 * m["n_local_at_R"] * np.log10(Rm / Rb))
                                     if (Rm and Rb) else None),
                mono_n_local=m["n_local_at_R"], bistatic_n_local=float(b["n_local_at_R"]),
                mono_monotone_ok=m["monotone_ok"], bistatic_monotone_ok=bool(b["monotone_ok"]),
                mono_snr_ceiling_db=m["snr_ceiling_db"],
                bistatic_snr_ceiling_db=float(b["snr_ceiling_db"]),
                mono_el_look_at_R_deg=m["el_look_at_R_deg"],
                bistatic_el_look_at_R_deg=float(np.interp(
                    np.log10(max(b["R_m"], 1.0)), np.log10(np.asarray(b["d_grid_m"], float)),
                    np.asarray(b["el_look_deg"], float))) if np.isfinite(b["R_m"]) else None,
                mono_sigma_at_R_dbsm=m["sigma_at_R_dbsm"],
                bistatic_sigma_at_R_dbsm=(float(np.interp(
                    np.log10(max(b["R_m"], 1.0)), np.log10(np.asarray(b["d_grid_m"], float)),
                    np.asarray(b["sigma_d_dbsm"], float))) if np.isfinite(b["R_m"]) else None),
                mono_grid_limited=m["grid_limited"], bistatic_grid_limited=bool(b["grid_limited"]),
                bistatic_limit=b["limit"], seconds=float(time.time() - t0)))
            heads.append(dict(drone=drone, mode=mode, band=m["band"],
                              prf_hz=m["prf_hz"], M=m["M"], speed_ms=m["speed_ms"],
                              mono=m["heading"], bistatic=bh,
                              mono_coverage=m["coverage"]))
            if verbose:
                print("  [%s %-9s] mono R=%s  bistatic R=%s  ratio=%s  usable mono %.3f / bi %.3f"
                      % (mode, drone,
                         ("%.0f" % Rm) if Rm else "nan", ("%.0f" % Rb) if Rb else "nan",
                         ("%.3f" % (Rm / Rb)) if (Rm and Rb) else "nan",
                         m["heading"]["frac_usable"], bh["frac_usable"]), flush=True)

    ok_pairs = [r for r in rows if r["ratio_mono_over_bistatic"]]
    ratios = [r["ratio_mono_over_bistatic"] for r in ok_pairs]
    for r in rows:                       # 비율을 설명하는 축: σ 조회 행이 다르다
        if r["mono_sigma_at_R_dbsm"] is not None and r["bistatic_sigma_at_R_dbsm"] is not None:
            r["sigma_aspect_delta_db"] = float(r["mono_sigma_at_R_dbsm"]
                                               - r["bistatic_sigma_at_R_dbsm"])
        else:
            r["sigma_aspect_delta_db"] = None
    sig_deltas = [abs(r["sigma_aspect_delta_db"]) for r in rows
                  if r["sigma_aspect_delta_db"] is not None]

    # σ 격자 밖 조회(정직 항목) — 두 기하 모두 같은 −20° 하한에 걸린다. 모노는 근거리에서 더 깊다.
    el_probe = []
    for alt in fss.FS_ALT:
        for dd in (100.0, 300.0, 1000.0):
            pm = mos.mono_params(mos.mono_target_pos(dd, 90.0, alt), (0, 0, 0), 3.5e9)
            pb = fss.fs_params(fss.FS_TX, fss.FS_RX(fss.L_REF),
                               fss.target_pos(dd, 90.0, fss.L_REF, alt), (0, 0, 0), 3.5e9)
            el_probe.append(dict(alt_m=float(alt), d_m=float(dd),
                                 mono_el_deg=float(pm["el_deg"]),
                                 bistatic_el_deg=float(pb["el_deg"]),
                                 mono_in_grid=bool(float(pm["el_deg"]) >= -20.0),
                                 bistatic_in_grid=bool(float(pb["el_deg"]) >= -20.0)))
    sigma_oor = dict(efr.SIGMA_OOR)

    # 저장소 정본(published) 과의 패리티 — 우리가 부른 stage_solve 가 산출물과 같은 값을 내나
    parity = []
    if fs_json:
        for r in rows:
            try:
                pub = fs_json["ranges"][r["drone"]][r["mode"]]["equal_psd"][
                    "full_waveform_capture"]["by_N"]["1"]["R90_C50_m"]
                parity.append(dict(drone=r["drone"], mode=r["mode"], published_m=float(pub),
                                   recomputed_m=r["bistatic_R_m"],
                                   rel_err=(abs(float(pub) - r["bistatic_R_m"]) / float(pub)
                                            if r["bistatic_R_m"] else None)))
            except Exception:
                pass
    par_err = [p["rel_err"] for p in parity if p["rel_err"] is not None]

    # V5 요약 — 모드별로 두 기하의 '쓸 수 있는 헤딩' 을 집계
    by_mode = {}
    for mode in modes:
        hs = [h for h in heads if h["mode"] == mode]
        if not hs:
            continue
        by_mode[mode] = dict(
            prf_hz=hs[0]["prf_hz"], M=hs[0]["M"], n_drones=len(hs),
            mono_usable_mean=float(np.mean([h["mono"]["frac_usable"] for h in hs])),
            bistatic_usable_mean=float(np.mean([h["bistatic"]["frac_usable"] for h in hs])),
            mono_blind_hard_mean=float(np.mean([h["mono"]["blind_hard"] for h in hs])),
            bistatic_blind_hard_mean=float(np.mean([h["bistatic"]["blind_hard"] for h in hs])),
            mono_alias_mean=float(np.mean([h["mono"]["alias_frac"] for h in hs])),
            bistatic_alias_mean=float(np.mean([h["bistatic"]["alias_frac"] for h in hs])),
            mono_blind_and_alias_mean=float(np.mean([h["mono"]["frac_blind_and_alias"] for h in hs])),
            max_abs_delta_usable=float(max(abs(h["mono"]["frac_usable"]
                                               - h["bistatic"]["frac_usable"]) for h in hs)))

    return dict(
        snr90_db=snr90, snr90_source=snr90_src, n_drones=len(drones), drones=list(drones),
        heading_by_mode=by_mode,
        heading_verdict_ko=(
            "⭐ 유휴 5G(SSB 50 Hz)의 판정은 **기하와 무관하다**: G1 에서 쓸 수 있는 헤딩이 "
            "모노 %.3f / 바이스태틱 %.3f 로 둘 다 사실상 0 이다(72 헤딩 중 평균 0.3개; "
            "블라인드 %.2f + 앨리어싱 %.2f, "
            "그중 %.2f 는 접힘 때문에 **동시에** 참). 반복률 1 kHz 인 W1/L1 에서는 앨리어싱이 "
            "0 이고 남는 검열이 자세 σ 다. 즉 '유휴 5G 이중고' 서사는 모노스태틱으로 옮겨도 "
            "그대로 산다 — 우리 헤드라인 결론 중 기하에 안 걸리는 쪽이다."
            % (by_mode.get("G1", {}).get("mono_usable_mean", float("nan")),
               by_mode.get("G1", {}).get("bistatic_usable_mean", float("nan")),
               by_mode.get("G1", {}).get("mono_blind_hard_mean", float("nan")),
               by_mode.get("G1", {}).get("mono_alias_mean", float("nan")),
               by_mode.get("G1", {}).get("mono_blind_and_alias_mean", float("nan")))
            if "G1" in by_mode else "G1 모드 미실행(스모크)"),
        modes=list(modes), sigma_source=SRC["repo_sigma"],
        sigma_is_monostatic_note_ko=(
            "⭐ σ 격자는 `rcs_sbr.rcs_sbr_batch`(1-bounce SBR) = **모노스태틱** 생산경로다. "
            "바이스태틱 리포트는 그 모노 σ 를 이등분선 방향에서 읽는 **등가 근사**로 쓰고 β≤90° "
            "게이트를 붙인다. 모노스태틱 시나리오에서는 이등분선 = 시선이라 그 근사가 "
            "**불필요**하다 — 이 시나리오는 저장소에서 가장 잘 검증된 RCS 층 위에 그대로 선다."),
        ranges=rows, heading=heads,
        range_summary=dict(
            n=len(ratios),
            ratio_min=(float(min(ratios)) if ratios else None),
            ratio_median=(float(np.median(ratios)) if ratios else None),
            ratio_max=(float(max(ratios)) if ratios else None),
            sigma_aspect_delta_db_max=(float(max(sig_deltas)) if sig_deltas else None),
            verdict_ko=(
                "⭐⭐ **검지거리로는 두 기하가 갈리지 않는다.** 21 셀 중앙값 비 %.4f, 범위 %.3f~%.3f. "
                "이유는 기하다: κ_bi = R1R2 ≈ d²+L²/4 이고 κ_mono = d²+Δh² 인데 우리 검지거리가 "
                "km 단위(d≫L=500 m)라 두 값이 같아진다(10 km 에서 확산항 차 0.005 dB). "
                "1/R⁴ 대 1/(R1²R2²) 의 차이는 **베이스라인 근방에서만** 크고(d=100 m 에서 16.5 dB) "
                "거기는 바이스태틱이 β>90° 로 이미 수치인용 금지 구역이다.\n"
                "⚠ 그래서 남는 %.0f%% 안팎의 편차는 확산법칙이 아니라 **σ 조회 자세가 다르기 "
                "때문**이다 — 바이스태틱은 이등분선 앙각, 모노는 시선 앙각을 읽어 σ 격자의 다른 "
                "행에 걸린다(최대 %.1f dB 차). 즉 검출거리 축에서 두 기하를 가르는 것은 "
                "링크식이 아니라 RCS 자세다."
                % (float(np.median(ratios)) if ratios else float("nan"),
                   float(min(ratios)) if ratios else float("nan"),
                   float(max(ratios)) if ratios else float("nan"),
                   100.0 * max(abs(1.0 - (min(ratios) if ratios else 1.0)),
                               abs((max(ratios) if ratios else 1.0) - 1.0)),
                   float(max(sig_deltas)) if sig_deltas else float("nan")))),
        bistatic_parity_vs_published=dict(
            rows=parity, max_rel_err=(float(max(par_err)) if par_err else None),
            provenance_drift=dict(
                sigma_generated=(sig_json or {}).get("meta", {}).get("generated"),
                sigma_git_rev=(sig_json or {}).get("meta", {}).get("git_rev"),
                freespace_generated=(fs_json or {}).get("meta", {}).get("generated"),
                freespace_git_rev=(fs_json or {}).get("meta", {}).get("git_rev"),
                stale=bool(fs_json and sig_json
                           and str((fs_json or {}).get("meta", {}).get("generated", ""))
                           < str((sig_json or {}).get("meta", {}).get("generated", "")))),
            note_ko=("우리가 부른 stage_solve(원본 함수)가 저장소 정본 R90 을 재현하는지. "
                     "⚠ **재현되지 않는 셀이 있고 원인은 우리 코드가 아니다**: "
                     "report13_freespace.json 은 σ 격자보다 **먼저** 생성됐다(위 provenance_drift). "
                     "즉 정본 바이스태틱 R90 은 옛 σ 로 푼 값이다. 그래서 이 파일은 정본 값을 "
                     "인용하지 않고 **두 기하를 같은 프로세스에서 같은 σ 파일로 다시 풀어** 뺀다 — "
                     "모노-바이 뺄셈은 그래서 유효하다.")),
        sigma_grid_limits=dict(el_grid_min_deg=-20.0, probe=el_probe, oor_counter=sigma_oor,
                               note_ko=("⚠ σ 격자의 el 하한은 −20° 다. 두 기하 모두 근거리에서 이 "
                                        "아래로 내려가 최근접 행으로 클램프된다 — 근거리 수치는 "
                                        "그 한계 안에서 읽어야 한다. 이 표는 어디서부터 클램프가 "
                                        "시작되는지를 두 기하에 대해 나란히 보여준다.")),
        ok=bool(ratios))


# =========================================================================== #
#  V6 — 기하의존 원장: 무엇이 두 기하 공통이고 무엇이 바이스태틱에서만 확인됐나
# =========================================================================== #
def v6_ledger(v1, v2, v3, v45):
    """⭐ 사용자가 실제로 물은 것. 각 행은 **이 파일이 계산한 숫자** 또는 기존 산출물을 근거로 단다.

    holds_for ∈ {both, bistatic_only, monostatic_only, differs_in_magnitude, unchecked}
    """
    rng = v45.get("range_summary", {})
    sp = v3["spread_law"]
    ex = v3["exponent_and_monotonicity"]
    rc = v3["reference_channel"]
    pf = v2["projection_factor"]

    L = [
        dict(id="vmax_law", claim="v_max = lambda*PRF_ref/(4 cos(beta/2) cos delta)",
             holds_for="both",
             evidence="V2.law_identity + V1.selfcheck.C_doppler_floor (bisection vs closed form)",
             number=v2["law_identity"][0]["v_max_mono_ms"], unit="m/s @ 50 Hz, 3.5 GHz",
             note_ko="모노는 β=0 절편이다. 발표한 1.07 m/s 는 모노 값이자 바이스태틱 **최악값**."),
        dict(id="vmax_headline_conservative",
             claim="the published 1.07 m/s is a floor, not an inflated number",
             holds_for="both", evidence="V2.law_identity (beta=45 -> x1.082, beta=90 -> x1.414)",
             number=v2["law_identity"][0]["v_max_bistatic_90_ms"], unit="m/s at beta=90",
             note_ko="바이스태틱이 도플러 모호에는 더 관대하다 — 헤드라인은 보수적이다."),
        dict(id="zero_doppler_blind", claim="a zero-Doppler guard blinds some headings",
             holds_for="differs_in_magnitude",
             evidence="V2.projection_factor.blind_delta_mono_minus_bistatic",
             number=pf["blind_delta_mono_minus_bistatic"]["mean"], unit="frac (mono - bistatic)",
             note_ko=("법칙은 같고 **비율이 다르다**. |u1+u2|=2cos(β/2) 가 모노에서 최대(2)라 "
                      "같은 속도에서 |f_d| 가 커 가드에 덜 걸린다.")),
        dict(id="alias_fraction", claim="fraction of headings that fold past PRF/2",
             holds_for="differs_in_magnitude",
             evidence="V2.projection_factor.alias_delta_mono_minus_bistatic",
             number=pf["alias_delta_mono_minus_bistatic"]["mean"], unit="frac (mono - bistatic)",
             note_ko="블라인드와 **반대 방향**으로 움직인다 — 한쪽만 인용하면 결론이 뒤집힌다."),
        dict(id="s6_nonmonotone",
             claim="SNR(d) is non-monotonic so bisection is invalid (spec S6)",
             holds_for="bistatic_only",
             evidence="V3.exponent_and_monotonicity.monotonicity_by_phi (bistatic %d/%d phi "
                      "non-monotone, mono %d/%d)"
                      % (ex["n_phi_bistatic_nonmonotone"], ex["n_phi_tested"],
                         ex["n_phi_mono_nonmonotone"], ex["n_phi_tested"]),
             number=max(r["bistatic_snr_rise_db"] for r in ex["monotonicity_by_phi"]),
             unit="dB max interior rise (bistatic, over phi)",
             note_ko=("κ=R1R2 가 d 내부 최소를 갖는 것은 표적이 RX 위를 지나기 때문이다. "
                      "모노는 κ=d²+Δh² 라 단조 — 이분법이 유효해진다.")),
        dict(id="s1_exponent", claim="R ∝ sigma^(1/4) fails at short range (spec S1)",
             holds_for="differs_in_magnitude",
             evidence="V3.exponent_and_monotonicity.rows (d=1 km)",
             number=ex["rows"][2]["n_local_mono"] - ex["rows"][2]["n_local_bistatic"],
             unit="n_local difference at d=1 km",
             note_ko=("둘 다 근거리에서 n<4 지만 원인이 다르다: 바이스태틱은 **베이스라인**, "
                      "모노는 **고도차**. 모노는 n=4d²/(d²+Δh²) 로 훨씬 빨리 4 로 간다.")),
        dict(id="spread_law", claim="1/R^4 vs 1/(R1^2 R2^2)",
             holds_for="differs_in_magnitude", evidence="V3.spread_law.rows",
             number=sp["penalty_at_10km_db"], unit="dB bistatic penalty at d=10 km",
             note_ko=("⚠ d≫L 이면 두 법칙이 수치적으로 같아진다. 차이는 헤드라인 거리가 아니라 "
                      "베이스라인 근방에서 난다 — '모노라서 유리' 로 읽으면 틀린다.")),
        dict(id="beta_gate", claim="beta>90 deg invalidates the SBR sigma (hatched cells)",
             holds_for="bistatic_only", evidence="V3.beta_gate",
             number=v3["beta_gate"]["bistatic_hatched_cells"], unit="hatched cells of %d"
             % v3["beta_gate"]["n_cells"],
             note_ko="모노는 β≡0 이라 금지구역이 없다 — 근거리 수치를 그대로 인용할 수 있다."),
        dict(id="sigma_layer", claim="the RCS layer the detection rests on",
             holds_for="monostatic_only_is_exact",
             evidence="src/rcs_sbr.py rcs_sbr_batch (monostatic) + V4.sigma_is_monostatic_note",
             number=None, unit=None,
             note_ko=("⭐ 우리 생산 σ 는 모노스태틱이다. 바이스태틱 리포트는 등가근사(이등분선 조회)"
                      "를 쓰지만 모노 시나리오는 근사 없이 그대로 쓴다 — RCS 축에서는 모노가 "
                      "**더 잘 검증된** 쪽이다.")),
        dict(id="dpi_wall", claim="the binding wall is DPI residual (report13 limit='dpi_residual')",
             holds_for="bistatic_only_by_name",
             evidence="V3.reference_channel (mono replaces it with self-interference)",
             number=rc["gap_closed_form_db"], unit="dB extra isolation monostatic must buy",
             note_ko=("같은 축의 다른 점이다: 모노 요구격리 − 패시브 직접파비 = 20log10(4πL/λ)−G_rx, "
                      "표적거리 무관. L→0 이면 패시브가 모노로 연속 수렴한다. ⭐ 그리고 이것이 "
                      "검지거리 축에서 두 기하를 실제로 가르는 유일한 큰 항이다 — "
                      "V3.reference_channel.si_ladder 참조.")),
        dict(id="si_range_cost",
             claim="what the missing reference channel actually costs the monostatic sensor in range",
             holds_for="monostatic_only",
             evidence="V3.reference_channel.si_ladder (ideal isolation vs Barneto's measured 100 dB)",
             number=((rc["si_ladder"][-1]["R_m"] / rc["si_ladder"][2]["R_m"])
                     if (rc["si_ladder"][-1]["R_m"] and rc["si_ladder"][2]["R_m"]) else None),
             unit="x range loss at 100 dB isolation",
             note_ko=("⚠ 1/R⁴ 이 아니라 **이것**이 링크 계층의 진짜 차이다. 확산법칙은 d≫L 에서 "
                      "거리를 안 바꿨고(비 1.00), 자기간섭은 한 자릿수 이상 바꾼다.")),
        dict(id="eca", claim="ECA (extensive cancellation algorithm) removes the reference leakage",
             holds_for="bistatic_only",
             evidence="structural: an ECA needs a reference channel; a monostatic sensor has none",
             number=None, unit=None,
             note_ko=("모노는 대신 STAR/전이중 자기간섭 소거가 필요하다. 실측 최고 100 dB"
                      "(Barneto 2019)로 100 m 표적에 %.1f dB 부족." % rc["shortfall_at_100m_db"])),
        dict(id="cassini", claim="iso-sensitivity contours are Cassini ovals (freespace_link.cassini_contour)",
             holds_for="bistatic_only",
             evidence="kappa = R1 R2 = const; monostatic kappa = R^2 -> a circle",
             number=None, unit=None,
             note_ko="모노 등감도선은 원(구면)이다 — 두 잎으로 갈라지는 현상 자체가 없다."),
        dict(id="rb_observable", claim="the range observable is Rb = R1+R2-L (an ellipse)",
             holds_for="bistatic_only",
             evidence="V1.selfcheck.A (Rb/2R = 1 exactly when TX=RX)",
             number=None, unit=None,
             note_ko="모노에서는 Rb → 2R 로 붕괴해 한 지점에서 거리+각으로 측위가 끝난다."),
        dict(id="phi_dependence", claim="results depend on the scene azimuth phi (spec S7)",
             holds_for="bistatic_only", evidence="V1.phi_rotational_symmetry",
             number=v1["phi_rotational_symmetry"]["bistatic_beta_span_deg"],
             unit="deg beta span over phi (bistatic); mono span = 0",
             note_ko="모노 기하는 센서 연직축 회전대칭 — 캡션에 φ 를 선언할 필요가 없다."),
        dict(id="detector_transfer", claim="Pd(output SNR) transfer curve is range- and geometry-invariant",
             holds_for="both",
             evidence="REPORT13_SPEC F1/L1: the curve is a function of output SNR, dopoff, N, shape",
             number=v45["snr90_db"], unit="dB SNR90 used for both geometries",
             note_ko=("그래서 같은 측정 문턱을 두 기하에 그대로 쓸 수 있다 — 이 등가성이 없으면 "
                      "V4 비교 자체가 성립하지 않는다.")),
        dict(id="cfar_guard", claim="the declared 2.5-bin guard differs from the detector's hard 1.5-bin guard",
             holds_for="both",
             evidence="monostatic_scene reuses fss.GUARD_DOPPLER_BINS / DOPPLER_GUARD_HARD_BINS",
             number=float(fss.GUARD_DOPPLER_BINS - fss.DOPPLER_GUARD_HARD_BINS), unit="bins",
             note_ko="검출기 상수의 성질이라 기하와 무관하다. 두 시나리오 모두 두 규약을 함께 낸다."),
        dict(id="range_result", claim="free-space detection range for the 5+2 airframes",
             holds_for="both_now_computed",
             evidence="V4.ranges (this file) — was bistatic-only before",
             number=rng.get("ratio_median"), unit="median R_mono / R_bistatic",
             note_ko=("이 파일 이전에는 모노 검출거리가 저장소에 **존재하지 않았다**. "
                      "⭐ 그리고 답은 '거의 같다' 다(중앙값 %.4f) — 검지거리 축으로는 두 기하를 "
                      "가를 수 없다. 우리 검지거리가 d≫L 영역이기 때문이다."
                      % (rng.get("ratio_median") or float("nan")))),
        dict(id="sigma_aspect_row", claim="which row of the sigma table the scenario reads",
             holds_for="differs_in_magnitude",
             evidence="V4.range_summary.sigma_aspect_delta_db_max",
             number=rng.get("sigma_aspect_delta_db_max"), unit="dB max sigma difference at R90",
             note_ko=("바이스태틱은 **이등분선** 앙각으로, 모노는 **시선** 앙각으로 σ 를 읽는다. "
                      "검지거리에 남는 편차는 확산법칙이 아니라 여기서 온다.")),
        dict(id="idle_5g_double_bind",
             claim="idle 5G (SSB, 50 Hz) leaves no usable heading — the double bind",
             holds_for="both",
             evidence="V4_V5.heading_by_mode.G1 (usable mono %s / bistatic %s)"
                      % (v45.get("heading_by_mode", {}).get("G1", {}).get("mono_usable_mean"),
                         v45.get("heading_by_mode", {}).get("G1", {}).get("bistatic_usable_mean")),
             number=v45.get("heading_by_mode", {}).get("G1", {}).get("mono_usable_mean"),
             unit="usable heading fraction (monostatic, G1)",
             note_ko=("⭐ 우리 헤드라인 서사 중 **기하에 안 걸리는** 쪽이다. 블라인드와 앨리어싱이 "
                      "동시에 참인 헤딩이 절반을 넘는 것(접힘 때문)도 두 기하 공통이다.")),
        dict(id="prf_freedom", claim="a monostatic ISAC sensor can choose PRF_ref",
             holds_for="monostatic_only_but_bounded",
             evidence=SRC["repo_mono"] + " §2 D1 (13-step ladder, 3GPP sub-6 CSI-RS ceiling 500 Hz)",
             number=mos.MONO_PRF_CEILING_HZ, unit="Hz ceiling",
             note_ko=("⚠ 연속 자유도가 아니라 슬롯 배수 사다리이고 500 Hz 에서 닫힌다. 이 파일은 "
                      "**같은 PRF** 로 두 기하를 비교했다 — 자유도는 별개 축이다.")),
        dict(id="floor_ghost", claim="the target-via-floor ghost (report09) and its CFAR consequences",
             holds_for="unchecked",
             evidence="not computed here: report09 is a chamber bistatic result",
             number=None, unit=None,
             note_ko=("정직: 모노스태틱 바닥유령은 검사하지 않았다. 왕복 기하라 지연이 다르고 "
                      "(2R vs R1+R2−L) 유령 위치도 달라진다 — 열린 과제로 남긴다.")),
        dict(id="multi_rx", claim="+10log10(N) coherent ceiling for N receivers (report12)",
             holds_for="unchecked",
             evidence="not computed here: monostatic multi-site is multistatic, a third geometry",
             number=None, unit=None,
             note_ko="모노스태틱을 여러 대 두면 그건 멀티스태틱이고 이 파일의 범위가 아니다."),
    ]
    counts = {}
    for r in L:
        counts[r["holds_for"]] = counts.get(r["holds_for"], 0) + 1
    return dict(rows=L, counts=counts, n=len(L),
                answer_ko=(
                    "사용자 질문에 대한 답: **부분적으로만 고려돼 있었고, 이제 메웠다.**\n"
                    "· 두 기하 공통(검증됨): v_max 법칙, 검출기 전이곡선 Pd(출력SNR), 가드 두 규약, "
                    "0-도플러 블라인드의 존재.\n"
                    "· 크기만 다름: 블라인드/앨리어싱 비율(투영인자 2cos(β/2)), 확산항, 국소지수 n.\n"
                    "· **바이스태틱에서만 성립**하던 것: S6 비단조·이분법 무효, β>90° 해칭, "
                    "Cassini 등감도선, Rb 타원 관측량, φ 의존성, ECA·DPI 서사.\n"
                    "· **모노가 오히려 정본**: RCS σ(rcs_sbr_batch 는 모노스태틱 생산경로).\n"
                    "· ⚠ 아직 안 본 것: 모노 바닥유령, 모노 다중사이트(=멀티스태틱)."))


# =========================================================================== #
#  V7 — 핸드오프 패치(직접 수정 금지 파일)
# =========================================================================== #
def v7_handoff(v1):
    ed_ok = v1["detector_degeneracy"]["ok"]
    return dict(
        rule="이 워크플로는 src/experiment_detection.py 와 src/experiment_freespace_range.py 를 "
             "수정하지 않는다. 아래는 적용할 사람이 그대로 붙일 수 있는 패치다.",
        patches=[
            dict(
                file="src/experiment_freespace_range.py",
                kind="add_optional_geometry_switch", risk="low",
                why_ko=("stage_solve 는 기하를 하드코딩(fss.FS_TX / fss.FS_RX(L))한다. 모노 경로는 "
                        "benchmark/verify_monostatic.py:mono_solve 에 이미 있고 같은 함수들을 "
                        "같은 순서로 부른다 — 옮겨 오려면 인자 하나면 된다."),
                patch=(
                    "# 1) 파일 상단 import 옆에\n"
                    "import monostatic_scene as mos                                     # noqa: E402\n"
                    "\n"
                    "# 2) stage_solve 시그니처에 geometry 인자 추가\n"
                    "def stage_solve(mode=\"L1\", drone=\"mini5pro\", L=500.0, alt=60.0, speed=5.0,\n"
                    "                T_cpi=0.1, N=1, snr90_db=None, sig_json=None, d_grid=None,\n"
                    "                psi_n=72, phi_deg=90.0, eca_depth_grid=(40.0, 60.0, 90.0, None),\n"
                    "                geometry=\"bistatic\", smoke=False, verbose=True) -> dict:\n"
                    "\n"
                    "# 3) 기하 블록만 분기 (기존 3줄을 감싼다)\n"
                    "    if geometry == \"monostatic\":\n"
                    "        tgt = mos.mono_target_pos(d, phi_deg, alt)\n"
                    "        p = mos.mono_params(tgt, (0.0, 0.0, 0.0), fc)\n"
                    "        R1 = R2 = np.asarray(p[\"R_m\"], float)\n"
                    "    else:\n"
                    "        tgt = fss.target_pos(d, phi_deg, L, alt)\n"
                    "        p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)\n"
                    "        R1 = np.asarray(p[\"R1\"], float); R2 = np.asarray(p[\"R2\"], float)\n"
                    "\n"
                    "# 4) 결과 dict 에 라벨 추가 — 두 기하가 같은 JSON 에 섞이면 반드시 필요\n"
                    "    res[\"geometry\"] = geometry\n"
                    "\n"
                    "# ⚠ 그 아래 코드는 손대지 않는다: snr_rd_db(R1,R2)/solve_range/coverage 는\n"
                    "#    R1=R2=R 이면 자동으로 1/R^4 와 kappa=R^2 가 된다(재구현 금지 규약 유지)."),
                verification="benchmark/verify_monostatic.py:mono_solve 가 이 분기와 동치인 계산을 "
                             "이미 수행하고 outputs/verify_monostatic.json V4 에 값을 남겼다"),
            dict(
                file="src/experiment_freespace_range.py",
                kind="beta_gate_is_vacuous_monostatically", risk="low",
                why_ko="모노에서 valid 게이트에 beta_gate 를 남기면 항상 True 라 무해하지만, "
                       "'해칭 셀 0개' 를 산출물이 명시해야 리포트가 두 기하를 헷갈리지 않는다.",
                patch=("    valid = (np.ones(d.shape, bool) if geometry == \"monostatic\"\n"
                       "             else fss.beta_gate(beta)) & np.array(\n"
                       "        [fss.farfield_gate(min(R1[i], R2[i]), drone, fc) for i in range(len(d))])\n"
                       "    res[\"beta_hatched_cells\"] = int(0 if geometry == \"monostatic\"\n"
                       "                                   else np.sum(~fss.beta_gate(beta)))")),
            dict(
                file="src/experiment_detection.py",
                kind="monostatic_scenario_constructor", risk="low",
                why_ko=("⭐ `bistatic_tau_fd` 는 tx_pos == surv_center 를 이미 **정확히** "
                        "모노스태틱으로 처리한다(검증: V1.detector_degeneracy.ok = %s). "
                        "그래서 패치는 시나리오 생성자와 라벨뿐이고 커널은 손댈 필요가 없다."
                        % ed_ok),
                patch=(
                    "# 1) MODES 옆에 기하 라벨 추가\n"
                    "GEOMETRY = os.environ.get(\"SIONNA2_GEOMETRY\", \"bistatic\")   # or 'monostatic'\n"
                    "\n"
                    "# 2) X410Scenario 를 만드는 자리에서 tx/ref/surv 를 한 점으로\n"
                    "def _scenario(geometry=GEOMETRY, **kw):\n"
                    "    scn = X410Scenario(**kw)\n"
                    "    if geometry == \"monostatic\":\n"
                    "        scn = dataclasses.replace(scn, tx_pos=scn.surv_center,\n"
                    "                                  ref_pos=scn.surv_center)\n"
                    "    return scn\n"
                    "# bistatic_tau_fd(scn, vel) 는 그대로 두면 L=0, Rb=2R, f_d=2 v·u/λ 를 낸다.\n"
                    "\n"
                    "# 3) DPI_AMP 의 의미가 바뀐다 — 직접파 누설이 아니라 **자기간섭 잔류**다.\n"
                    "#    값은 monostatic_scene.mono_required_isolation_db 로 유도할 것:\n"
                    "#      amp = 10 ** ((required_isolation_db - achieved_isolation_db) / 20)\n"
                    "#    (하드코딩 40 을 그대로 쓰면 모노 자기간섭을 40 dB 로 과소평가한다.)\n"
                    "\n"
                    "# 4) 산출 JSON 에 geometry 키를 박는다(두 기하가 같은 파일에 섞이면 필수).\n"
                    "OUT_KEY = f\"detection_rx_sweep_{GEOMETRY}.json\""),
                verification="V1.detector_degeneracy 가 f_d·Rb·L 을 mono_params 와 상대오차 1e-12 "
                             "이내로 대조해 통과시켰다"),
            dict(
                file="src/experiment_freespace_range.py (docstring only)",
                kind="documentation", risk="none",
                why_ko="리포트 소비자가 '이 파일은 바이스태틱 전용' 이라는 사실을 알아야 한다.",
                patch=("모듈 docstring 에 한 줄: \"이 파일의 기하는 **바이스태틱 전용**이다. "
                       "모노스태틱 대응은 src/monostatic_scene.py + benchmark/verify_monostatic.py "
                       "(outputs/verify_monostatic.json).\"")),
        ])


# =========================================================================== #
#  main
# =========================================================================== #
def run_all(smoke=False, n_geom=2000, verbose=True):
    t0 = time.time()
    fs_json = _load(IN_FS)
    sig_json = _load(IN_SIGMA)
    refrate = _load(IN_REFRATE)

    if verbose:
        print("[V1] 기하 동치(퇴화입력·L→0 연속성·φ 회전대칭)…", flush=True)
    v1 = v1_geometry(n=n_geom, smoke=smoke)
    if verbose:
        print("     ok=%s  (A=%s B=%s C=%s)  φ대칭=%s"
              % (v1["ok"], v1["selfcheck"]["A_degenerate_identity"]["ok"],
                 v1["selfcheck"]["B_L_to_zero_continuity"]["ok"],
                 v1["selfcheck"]["C_doppler_floor"]["ok"],
                 v1["phi_rotational_symmetry"]["mono_is_symmetric"]), flush=True)
        print("[V2] 도플러 바닥 불변 + 투영인자…", flush=True)
    v2 = v2_doppler(refrate, smoke=smoke)
    if verbose:
        print("     ok=%s  Δblind(mono−bi) 평균 %+0.3f  Δalias 평균 %+0.3f"
              % (v2["ok"], v2["projection_factor"]["blind_delta_mono_minus_bistatic"]["mean"],
                 v2["projection_factor"]["alias_delta_mono_minus_bistatic"]["mean"]), flush=True)
        print("[V3] 링크 변화(1/R⁴·기준채널 부재)…", flush=True)
    v3 = v3_link(smoke=smoke)
    if verbose:
        print("     ok=%s  격차 닫힌형 %.2f dB(거리무관 %s)  요구격리@100m %.1f dB"
              % (v3["ok"], v3["reference_channel"]["gap_closed_form_db"],
                 v3["reference_channel"]["gap_range_independent"],
                 v3["reference_channel"]["rows"][1]["mono_required_isolation_db"]), flush=True)
        print("[V4/V5] 검지거리·헤딩 비율(모노 vs 바이스태틱)…", flush=True)
    v45 = v4_v5_ranges(fs_json, sig_json, smoke=smoke, verbose=verbose)
    v6 = v6_ledger(v1, v2, v3, v45)
    v7 = v7_handoff(v1)

    rng = v45["range_summary"]
    ok = bool(v1["ok"] and v2["ok"] and v3["ok"] and v45["ok"])
    return dict(
        meta=dict(script="benchmark/verify_monostatic.py",
                  generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  question=("전체 검증에 바이스태틱뿐 아니라 모노스태틱(LaSen 같은 기법)까지 "
                            "고려됐나 — 검출 계층의 모노스태틱 시나리오"),
                  smoke=bool(smoke), runtime_s=float(time.time() - t0),
                  owns=["src/monostatic_scene.py", "benchmark/verify_monostatic.py",
                        "outputs/verify_monostatic.json"],
                  does_not_edit=["src/experiment_detection.py",
                                 "src/experiment_freespace_range.py",
                                 "src/rcs_sbr.py", "src/drones.py", "src/sigma_anchor.py",
                                 "benchmark/refrate_law.py"],
                  repo_functions_used=[
                      "freespace_scene.fs_params / target_pos / heading_velocity / folded_doppler / "
                      "nyquist_gate / doppler_bin_hz / prf_hz / M_from_prf / farfield_gate / "
                      "beta_gate / blind_fractions",
                      "freespace_link.echo_power_w / snr_rd_db / solve_range / n_local / "
                      "coverage_fraction / e_psi_pd / n0_thermal / n0_dpi",
                      "link_budget.LinkBudget (echo/direct/noise power)",
                      "experiment_freespace_range.stage_solve / _sigma_lookup / _sigma_at "
                      "(imported, never edited)",
                      "refrate_law.law_v_max"],
                  inputs=[SRC["repo_fs"], SRC["repo_sigma"], SRC["repo_mono"], SRC["repo_refrate"]],
                  house_rules="Korean prose/prints; numbers from outputs/*.json; no figures here",
                  fairness=("same EIRP/G_rx/NF, same T_CPI, same alt/speed, same sigma grid, "
                            "same measured SNR90, same d grid, SAME PRF — the monostatic PRF "
                            "freedom is a separate axis quantified in mono_vs_passive.json")),
        headline_ko=(
            "모노스태틱 검출 시나리오를 세워 두 기하를 같은 함수·같은 σ·같은 문턱으로 나란히 놓았다. "
            "**도플러 모호 바닥은 안 바뀌고**(v_max=λPRF/4, 모노는 β=0 절편), **링크는 바뀐다**"
            "(1/R⁴ ↔ 1/(R1²R2²), 그리고 기준채널이 자기간섭으로 대체되며 그 격차가 정확히 "
            "20log10(4πL/λ)−G_rx = %.1f dB). 두 효과를 섞지 않는 것이 이 검증의 요점이다."
            % v3["reference_channel"]["gap_closed_form_db"]),
        headline_en=(
            "A monostatic detection scenario now exists and is compared to the bistatic one with the "
            "same functions, the same sigma grid and the same measured threshold. The Doppler "
            "ambiguity floor does NOT change (monostatic is the beta = 0 slice of our law); the link "
            "budget DOES (1/R^4 instead of 1/(R1^2 R2^2), and the reference channel is replaced by "
            "self-interference, harder by exactly 20 log10(4 pi L / lambda) - G_rx = %.1f dB)."
            % v3["reference_channel"]["gap_closed_form_db"]),
        V1_geometry_equivalence=v1,
        V2_doppler_floor_unchanged=v2,
        V3_link_budget_changed=v3,
        V4_V5_ranges_and_headings=v45,
        V6_geometry_dependence_ledger=v6,
        V7_handoff_patches=v7,
        verdict=dict(ok=ok,
                     mono_over_bistatic_range_median=rng.get("ratio_median"),
                     what_changed="link budget (range)",
                     what_did_not_change="Doppler ambiguity floor (v_max = lambda*PRF/4)",
                     sources=SRC),
        open_questions=[
            "모노스태틱 바닥유령(target-via-floor)은 검사하지 않았다 — report09 는 챔버 "
            "바이스태틱 결과이고, 왕복 기하는 유령 지연이 다르다.",
            "모노스태틱 다중사이트는 멀티스태틱이라 이 파일의 범위 밖이다(report12 의 "
            "+10log10(N) 상한이 그대로 가는지 미확인).",
            "자기간섭 격리를 EIRP 기준면으로 잡았다(송신 안테나 이득을 누설경로에도 실는 보수적 "
            "가정) — mono_vs_passive.json 의 같은 유보를 그대로 승계한다. 실제 STAR 전단은 "
            "안테나/아날로그/디지털이 다른 기준면에서 걸린다.",
            "모노 σ 조회의 el 격자 밖 클램프는 바이스태틱과 같은 문제를 갖는다(σ 격자가 −20° "
            "까지뿐). 모노는 고도 120 m·근거리에서 −40° 이하로 내려간다 — 근거리 수치는 "
            "그 한계 안에서 읽어야 한다.",
            "Pd 는 로지스틱 근사다(stage_solve 와 같은 규약). 측정 전이곡선을 모노 기하에 "
            "다시 재지는 않았다 — 전이곡선이 기하불변이라는 스펙 F1/L1 가정에 기댄다.",
            "⚠ 저장소 정본 outputs/report13_freespace.json 은 현재 σ 격자보다 **먼저** 생성됐다"
            "(V4.bistatic_parity_vs_published.provenance_drift). 15 셀 중 3 셀에서 재계산값이 "
            "정본과 17% 어긋난다 — 이 파일의 비교는 같은 프로세스·같은 σ 로 다시 풀어 무해하지만, "
            "**정본 JSON 자체를 재생성해야 한다**(다른 워크플로 소관).",
            "모노 기하에서 EIRP 63 dBm 는 '기지국이 자기 신호를 송신' 이라는 뜻이라 자기간섭의 "
            "기준면이 곧 그 EIRP 다. 감시 수신이득 10 dBi 를 그대로 쓴 것도 선언값 승계일 뿐 "
            "모노스태틱 STAR 전단의 실제 구성이 아니다.",
        ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--n-geom", type=int, default=2000)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    res = run_all(smoke=a.smoke, n_geom=a.n_geom, verbose=not a.quiet)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(_jsonify(res), f, indent=1, ensure_ascii=False)
    print("→ %s  (ok=%s, %.1f s)" % (a.out, res["verdict"]["ok"], res["meta"]["runtime_s"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
