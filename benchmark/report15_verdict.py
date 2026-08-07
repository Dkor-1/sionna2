# -*- coding: utf-8 -*-
"""
report15_verdict.py — ⭐⭐ **판정: Sionna 자체로 블레이드 마이크로도플러가 나오는가**
================================================================================

두 갈래를 섞지 않는다
  ① `Paths.doppler` 로 자동으로 나오나 → **아니다(확정)**. 속도가 객체당 강체 1벡터라
     회전을 표현할 자리가 없다. §A 에서 저장된 실측으로 재확인만 한다.
  ② **로터 위상을 스텝하고 매번 재추적**해 h(φ) 를 이어붙이면 나오나 → 이것이 열린 질문.
     (선례: WiFi-JEPA arXiv:2607.11064 — 프레임당 20 패스로 시간축을 만들었다)

판정 규칙 (⛔ 계산 **전에** 코드에 박는다 — 결과를 보고 고르지 않으려고)
  SIONNA_NATIVE_OK : (a) 변조가 잡음바닥보다 ≥6 dB  (b) 플래시 주파수가 f_tip ±20 %
                     (c) 구 널대조가 변조를 안 냄   (d) 삼각형 절반에서 판정 불변
  ARTIFACT         : 변조는 있으나 (b)(c)(d) 중 하나라도 깨짐
  NO_MODULATION    : 변조가 잡음바닥 아래
  MIXED            : 중간 — 어느 조건이 깨졌는지 명시

⭐ 주파수 축 규약 (이 파일 전체에서 하나)
  로터 회전수 f_rev = rpm/60.  2날 프로펠러는 형상 주기가 180° 이므로 한 주기 = 1/(2 f_rev).
  → 한 주기를 N 등분한 φ 격자의 DFT 빈 k 는 **주파수 k·f_flash** 를 뜻한다
    (f_flash = n_blades · f_rev = 블레이드 플래시율).
  → 스펙트럼은 f_flash 의 정수배에만 에너지가 있다. 즉 **분해 단위가 f_flash 로 양자화**된다.
    (b) 판정의 고유 granularity 가 이것이다 — mini2 는 f_tip 이 4.37 빈이라 1 빈 = f_tip 의 22.9 %.

입력 (전부 기존/신규 측정 JSON — 이 파일은 새로 추적하지 않는다)
  outputs/report15_verdict_grid_mini2.json        신규 · mini2 Sionna 격자(matrice4e 와 동일 조건)
  outputs/report15_sionna_sweep_matrice4e.json    기존 · matrice4e Sionna 격자
  outputs/report15_verdict_po_grid.json           신규 · 같은 칸의 우리 PO 커널
  outputs/report15_verdict_nulls_vs_range.json    신규 · 널(구·원판·로터제거)을 거리축으로
  outputs/report15_null_control.json              기존 · R=3 m 널 20팔 + 삼각형 사다리
  outputs/report15_probe.json                     기존 · Paths.doppler 재확인 · 정반사 인구조사

⛔ 숫자 손입력 금지 — 전부 계산해서 outputs/report15_verdict.json 에 담는다.
본문·주석·print 한국어. 그림 텍스트 영어.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_JSON = os.path.join(ROOT, "outputs", "report15_verdict.json")
FIGDIR = "outputs/figures"

#  ⛔ 판정 문턱 — 선언값
TH = dict(
    margin_db_min=6.0,          # (a) 변조 − 잡음바닥
    ftip_tol=0.20,              # (b) f_edge 가 f_tip 의 ±20 % 안
    edge_drop_db=20.0,          # (b) 스펙트럼 가장자리 정의: 최강 AC 조화 대비 −20 dB
    edge_snr_db=10.0,           # (b) 그 조화가 시드잡음보다 10 dB 위여야 '있다'
    null_margin_db_min=6.0,     # (c) 신호가 널보다 이만큼 커야 널이 조용한 것
    ladder_corr_min=0.90,       # (d) 삼각형을 깎아도 h(φ) 곡선이 이만큼 같아야 판정 불변
    ladder_ptp_rel_max=0.25,    # (d) 변조 크기 상대변화 한도
)

KEYS = ("mini2", "matrice4e")
ASPECT_ORDER = ("nose", "oblique", "side", "hot", "disc")


# --------------------------------------------------------------------------- #
#  직렬화
# --------------------------------------------------------------------------- #
def _f(x, nd=6):
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return float(f"%.{nd}g" % v) if math.isfinite(v) else None


def _fl(seq, nd=6):
    return [_f(x, nd) for x in seq]


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        o = o.item()
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (np.bool_, bool)):
        return bool(o)
    if isinstance(o, float):
        return None if not math.isfinite(o) else o
    return o


# --------------------------------------------------------------------------- #
#  ⭐ 조화 분해 — report15_sweep_matrice4e._harm_seeded 의 **축자 이식**
#     (그 모듈은 import 하면 mitsuba/GPU 를 잡는다. 여기선 GPU 를 안 쓰므로 옮겨 오고,
#      §self_check 에서 저장된 matrice4e 값을 재현하는지 대조한다.)
# --------------------------------------------------------------------------- #
def harm_seeded(X: np.ndarray) -> dict:
    """X = [phase, seed] (복소). 한 주기 N 표본 → 빈 k = 주기당 k 사이클 = k·f_flash.

    널은 **시드 재추첨**에서 온다:
        신호 S(k) = |⟨Z_j(k)⟩_j|² ,  잡음 N(k) = Var_j(Z_j(k))/S  (평균의 분산)
    정반사 채널처럼 결정론적이면 분산이 0 이라 SNR 이 무한대가 된다 — 그건 '세다' 가 아니라
    '이 널이 그 채널에 안 맞는다' 는 뜻이므로 noise_degenerate 로 표시하고 SNR 을 버린다.
    """
    X = np.asarray(X)
    N, S = X.shape
    Z = np.fft.fft(X, axis=0) / N
    ny = N // 2
    Zm = Z.mean(axis=1)
    nse = (np.sum(np.abs(Z - Zm[:, None]) ** 2, axis=1) / (S - 1) / S) if S > 1 else np.zeros(N)
    sig = np.abs(Zm) ** 2
    ks = list(range(1, ny + 1))
    ac = float(np.mean(sig[1:ny + 1])) if ks else 0.0
    nmean = float(np.mean(nse[1:ny + 1])) if ks else 0.0
    degen = bool(S < 2 or nmean <= 1e-12 * max(ac, float(sig[0]), 1e-300))
    snr = sig / (nse + 1e-300)
    top = int(ks[int(np.argmax(snr[1:ny + 1]))]) if ks else None
    top_amp = int(ks[int(np.argmax(np.abs(Zm[1:ny + 1])))]) if ks else None
    return dict(
        n_samples=int(N), n_seeds=int(S), dc_abs=float(np.abs(Zm[0])),
        harm_index=ks, harm_abs=[float(np.abs(Zm[k])) for k in ks],
        harm_snr_db=(None if degen else [float(10 * np.log10(snr[k] + 1e-300)) for k in ks]),
        noise_per_bin_abs=float(np.sqrt(nmean)), noise_degenerate=degen,
        blade_flash_bin=1,
        blade_flash_snr_db=(None if degen or ny < 1 else float(10 * np.log10(snr[1] + 1e-300))),
        dominant_bin_by_snr=top, dominant_bin_by_amp=top_amp,
        dominant_snr_db=(None if degen or top is None
                         else float(10 * np.log10(snr[top] + 1e-300))),
        #  ⭐ (a) 판정에 쓰는 양: 변조 전력 총합 / 잡음 전력 총합
        total_ac_over_noise_db=(None if degen else float(10 * np.log10(
            (float(np.sum(sig[1:ny + 1])) + 1e-300)
            / (float(np.sum(nse[1:ny + 1])) + 1e-300)))),
        ac_rms_abs=float(np.sqrt(float(np.sum(sig[1:ny + 1])))),
        noise_rms_abs=float(np.sqrt(float(np.sum(nse[1:ny + 1])))) if not degen else None,
        #  ⭐ 양측 측대역 — |Z(+k)| vs |Z(−k)|. 순수 진폭변조면 0 dB 에 가깝고,
        #    전진날/후퇴날이 갈리는 성분이 있으면 벌어진다. (판정 기준이 아니라 서술 지표다:
        #    단일 로터 점산란자는 왕복위상이 θ 의 우함수라 이론적으로도 대칭이다 — 비대칭은
        #    허브 위치·역회전 로터·바이스태틱 오프셋에서 온다.)
        plus_abs=[float(np.abs(Zm[k])) for k in ks],
        minus_abs=[float(np.abs(Zm[-k])) for k in ks],
        asym_db=[float(20 * np.log10((np.abs(Zm[k]) + 1e-300) / (np.abs(Zm[-k]) + 1e-300)))
                 for k in ks])


def edge_bin(H: dict, drop_db=TH["edge_drop_db"], snr_min=TH["edge_snr_db"]) -> dict:
    """스펙트럼 **가장자리**: 최강 AC 조화 대비 −drop_db 위이고, 시드잡음보다 snr_min 위인
    **가장 높은 빈**. 이것이 관측된 도플러 확산폭이다 — 운동학 예측 f_tip 과 비교한다."""
    a = np.asarray(H["harm_abs"], float)
    ks = np.asarray(H["harm_index"], int)
    if a.size == 0 or a.max() <= 0:
        return dict(edge_bin=None, peak_bin=None, n_bins_used=0, snr_gated=False)
    thr = a.max() * 10.0 ** (-float(drop_db) / 20.0)
    ok = a >= thr
    gated = False
    if H.get("harm_snr_db") is not None:
        ok = ok & (np.asarray(H["harm_snr_db"], float) >= float(snr_min))
        gated = True
    idx = np.where(ok)[0]
    return dict(edge_bin=(int(ks[idx.max()]) if idx.size else None),
                peak_bin=int(ks[int(np.argmax(a))]),
                n_bins_used=int(idx.size), snr_gated=bool(gated),
                drop_db=float(drop_db), snr_min_db=float(snr_min))


def ac_corr(a, b) -> float:
    """DC 를 뺀 복소 파형 두 개의 상관 크기. 상수 복소배에 불변."""
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    a = a - a.mean(); b = b - b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(abs(np.vdot(a, b)) / (na * nb)) if na > 0 and nb > 0 else 0.0


def corr_null_p(a, b, n_mc=4000, seed=20260804) -> dict:
    """⚠ 상관이 '둘 다 k=1 에 몰려 있어서' 자동으로 높은 것은 아닌지 검정한다.
    한쪽 조화의 **위상만** 무작위로 돌리고(크기 보존) 귀무분포를 만든다."""
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    obs = ac_corr(a, b)
    rng = np.random.default_rng(seed)
    B = np.fft.fft(b - b.mean())
    mag = np.abs(B)
    null = np.empty(int(n_mc))
    for i in range(int(n_mc)):
        Bp = mag * np.exp(1j * rng.uniform(0, 2 * np.pi, size=mag.size))
        null[i] = ac_corr(a, np.fft.ifft(Bp))
    return dict(corr=obs, null_mean=float(null.mean()), null_p95=float(np.percentile(null, 95)),
                p_value=float((np.sum(null >= obs) + 1) / (n_mc + 1)),
                n_mc=int(n_mc), significant=bool((np.sum(null >= obs) + 1) / (n_mc + 1) < 0.05))


def db(x):
    return float(20.0 * np.log10(abs(x) + 1e-300))


# --------------------------------------------------------------------------- #
#  ⭐⭐ 해석적 대조 — 이상적 회전 점산란자의 빗 (Jacobi–Anger)
# --------------------------------------------------------------------------- #
def ideal_comb(ph, el_deg) -> dict:
    """블레이드 팁을 **점 산란자**로 본 이상적 마이크로도플러 빗. GPU 도 메쉬도 필요 없다.

    반경 r 의 점이 로터면(수평) 안에서 도는데 시선이 앙각 el 이면, 왕복 위상은
        Φ(θ) = −2k·r·cos(el)·cos(θ − az)                (모노스태틱 평면파)
    Jacobi–Anger 전개 exp(−j x cos ψ) = Σ_m (−j)^m J_m(x) e^{jmψ} 에 의해
    **회전 조화 m 의 진폭이 |J_m(x)|**, x = 2·k·r·cos(el) 이다.
    n_blades 장을 더하면 m 이 n_blades 의 배수인 항만 살아남는다
    → **플래시 빈 k 의 진폭 = |J_{k·n_blades}(x)|**.

    ⭐ 여기서 중요한 항등식이 하나 나온다. J_m(x) 는 m ≲ x 까지만 크므로 빗의 가장자리는
         k_edge ≈ x / n_blades = 4π·r·cos(el) / (n_blades·λ)
       이고, 이것은 **회전수 f_rev 가 소거된 순수 기하량**이다. 즉 판정 (b) 는 사실
       "h(φ) 가 블레이드의 전기적 크기가 요구하는 만큼의 조화를 담고 있는가" 를 묻는다.
       블레이드를 점으로 뭉개는 엔진은 k_edge≈1 밖에 못 낸다 — 그래서 이 시험은 자명하지 않다.
    """
    from scipy.special import jv
    c_el = math.cos(math.radians(float(el_deg)))
    k_wave = 2.0 * np.pi / ph["lambda_m"]
    x = 2.0 * k_wave * ph["prop_radius_m"] * c_el
    nb = int(ph["n_blades"])
    ks = np.arange(1, 33)
    a = np.abs(jv(ks * nb, x))
    peak = a.max() if a.size and a.max() > 0 else 1.0
    ad = 20 * np.log10(a / peak + 1e-300)
    idx = np.where(ad >= -20.0)[0]
    return dict(model="rotating point scatterer at blade tip (Jacobi-Anger, |J_{k·n_b}(x)|)",
                x_argument=_f(x), el_deg=float(el_deg), cos_el=_f(c_el),
                n_blades=nb, harm_index=[int(v) for v in ks], harm_abs=_fl(a),
                harm_freq_hz=_fl(ks * ph["f_flash_hz"]),
                edge_bin=(int(ks[idx.max()]) if idx.size else None),
                f_edge_hz=_f(ks[idx.max()] * ph["f_flash_hz"]) if idx.size else None,
                k_edge_closed_form=_f(x / nb),
                identity_ko=("k_edge = x/n_b = 4π·r·cos(el)/(n_b·λ) — f_rev 가 소거된다. "
                             "판정 (b) 는 '블레이드의 전기적 크기만큼 조화가 나오는가' 다."))


# --------------------------------------------------------------------------- #
#  §0 — 물리 (주파수 축을 여기서 한 번만 정한다)
# --------------------------------------------------------------------------- #
def physics(key) -> dict:
    from drones import DRONES
    sp = DRONES[key]
    C0 = 299792458.0
    fc = 3.5e9
    lam = C0 / fc
    rpm = float(sp.hover_rpm)
    f_rev = rpm / 60.0
    nb = int(sp.prop_blades)
    f_flash = nb * f_rev
    r_tip = float(sp.prop_dia_mm) / 2000.0
    v_tip = 2.0 * np.pi * f_rev * r_tip
    f_tip = 2.0 * v_tip / lam                      # 팁의 왕복 도플러 (모노스태틱 상한)
    return dict(drone=key, name=sp.name, fc_hz=fc, lambda_m=lam,
                hover_rpm=rpm, f_rev_hz=f_rev, n_blades=nb,
                mesh_period_deg=360.0 / nb, f_flash_hz=f_flash,
                prop_radius_m=r_tip, v_tip_ms=v_tip, v_tip_mach=v_tip / 343.0,
                f_tip_hz=f_tip, f_tip_in_flash_bins=f_tip / f_flash,
                bin_width_hz=f_flash,
                bin_granularity_frac_of_ftip=f_flash / f_tip,
                note_ko=("빈 k ↔ 주파수 k·f_flash. 스펙트럼은 f_flash 의 정수배에만 산다 — "
                         "(b) 판정의 고유 분해 단위가 f_flash 다."))


# --------------------------------------------------------------------------- #
#  §1 — 입력 적재
# --------------------------------------------------------------------------- #
def load(name):
    p = os.path.join(ROOT, "outputs", name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def sionna_blocks(J) -> dict:
    """Sionna 격자 JSON → {(R, aspect, mode): block}"""
    if not J or "grid" not in J:
        return {}
    return {k: v for k, v in J["grid"]["blocks"].items()}


def block_wave(B, channel="all"):
    """블록 → (h[phase,seed] 복소, n[phase,seed])"""
    kr, ki = ("hr", "hi") if channel == "all" else ("hpr", "hpi")
    kn = "n" if channel == "all" else "n_prop"
    z = np.asarray(B[kr], float) + 1j * np.asarray(B[ki], float)
    n = np.asarray(B[kn], float)
    return z, n


# --------------------------------------------------------------------------- #
#  §2 — 한 채널 전체 분석
# --------------------------------------------------------------------------- #
def analyse_channel(z, n, ph) -> dict:
    """z=[phase,seed] 복소, n=[phase,seed] 경로수, ph=물리 dict."""
    H = harm_seeded(z)
    E = edge_bin(H)
    zm = z.mean(axis=1)                       # 시드 코히런트 평균 = 최선 추정
    amp = 20 * np.log10(np.abs(zm) + 1e-300)
    finite = np.isfinite(amp) & (np.abs(zm) > 0)
    seed_amp = 20 * np.log10(np.abs(z) + 1e-300)
    f_edge = (E["edge_bin"] * ph["f_flash_hz"]) if E["edge_bin"] else None
    f_peak = (E["peak_bin"] * ph["f_flash_hz"]) if E["peak_bin"] else None
    zero_frac = float(np.mean(n == 0))
    return dict(
        n_phase=int(z.shape[0]), n_seed=int(z.shape[1]),
        level_db=_f(float(np.mean(amp[finite]))) if finite.any() else None,
        modulation_ptp_db=_f(float(np.ptp(amp[finite]))) if finite.sum() > 1 else None,
        modulation_std_db=_f(float(np.std(amp[finite], ddof=1))) if finite.sum() > 1 else None,
        seed_noise_std_db=_f(float(np.nanmean(np.nanstd(
            np.where(np.isfinite(seed_amp), seed_amp, np.nan), axis=1, ddof=1)))),
        #  ⭐ (a) 판정량
        ac_over_noise_db=_f(H["total_ac_over_noise_db"]),
        ac_rms_abs=_f(H["ac_rms_abs"]), noise_rms_abs=_f(H["noise_rms_abs"]),
        noise_degenerate=bool(H["noise_degenerate"]),
        #  ⭐ (c) 판정량 — **무차원 변조지수** = AC 실효 / DC. dB-ptp 끼리 비율을 내면
        #     'dB 의 dB' 가 되어 차원이 어긋난다. 널과의 비교는 이 양으로 한다.
        modulation_index=_f(H["ac_rms_abs"] / (H["dc_abs"] + 1e-300)),
        modulation_index_db=_f(20 * np.log10(
            H["ac_rms_abs"] / (H["dc_abs"] + 1e-300) + 1e-300)),
        #  ⭐ (b) 판정량
        dominant_bin_by_amp=H["dominant_bin_by_amp"],
        dominant_bin_by_snr=H["dominant_bin_by_snr"],
        blade_flash_snr_db=_f(H["blade_flash_snr_db"]),
        edge_bin=E["edge_bin"], peak_bin=E["peak_bin"],
        edge_bins_by_drop=edge_sensitivity(H, ph),
        f_edge_hz=_f(f_edge), f_peak_hz=_f(f_peak),
        f_tip_hz=_f(ph["f_tip_hz"]), f_flash_hz=_f(ph["f_flash_hz"]),
        edge_over_ftip=_f(f_edge / ph["f_tip_hz"]) if f_edge else None,
        peak_over_fflash=_f(f_peak / ph["f_flash_hz"]) if f_peak else None,
        #  경로수 거동 (톱니 판정)
        n_paths_mean=_f(float(n.mean())), n_paths_min=int(n.min()), n_paths_max=int(n.max()),
        n_paths_cv=_f(float(n.std(ddof=1) / n.mean())) if n.mean() > 0 else None,
        zero_path_frac=_f(zero_frac),
        n_paths_behaviour=("모든 칸에서 경로 0" if zero_frac == 1.0 else
                           ("껐다켜짐 (경로수가 0 을 오간다)" if zero_frac > 0
                            else "연속 (모든 칸에 경로 존재)")),
        blade_flash_asym_db=_f(H["asym_db"][0] if H["asym_db"] else None),
        max_abs_asym_db=_f(max((abs(v) for v in H["asym_db"]), default=None)),
        asym_db=_fl(H["asym_db"][:12]),
        harm_abs=_fl(H["harm_abs"]), harm_snr_db=(_fl(H["harm_snr_db"])
                                                  if H["harm_snr_db"] else None),
        harm_freq_hz=_fl([k * ph["f_flash_hz"] for k in H["harm_index"]]),
        dc_abs=_f(H["dc_abs"]),
        wave_amp_db=_fl(amp), wave_phase_deg=_fl(np.degrees(np.angle(zm))),
        n_paths_by_phase=_fl(n.mean(axis=1)))


def analyse_po(E, ph, n_period) -> dict:
    """PO 파형(결정론적) → 같은 잣대. 시드가 없으므로 SNR 게이트 없이 −20 dB 만 쓴다.

    ⭐ 위상을 반드시 남긴다 — 양측 스펙트럼(전진날 +f / 후퇴날 −f)은 복소 파형에서만 나온다.
      진폭만 쓰면 스펙트럼이 강제로 대칭이 되어 비대칭 측대역이 통째로 사라진다."""
    z = np.asarray(E, complex)[:n_period][:, None]      # 한 주기만
    H = harm_seeded(z)                                   # S=1 → degenerate (SNR 없음)
    Eg = edge_bin(H, snr_min=-np.inf)
    zm = z[:, 0]
    amp = 20 * np.log10(np.abs(zm) + 1e-300)
    f_edge = (Eg["edge_bin"] * ph["f_flash_hz"]) if Eg["edge_bin"] else None
    f_peak = (Eg["peak_bin"] * ph["f_flash_hz"]) if Eg["peak_bin"] else None
    return dict(n_phase=int(z.shape[0]), deterministic=True,
                level_db=_f(float(amp.mean())), modulation_ptp_db=_f(float(np.ptp(amp))),
                dominant_bin_by_amp=H["dominant_bin_by_amp"],
                edge_bin=Eg["edge_bin"], peak_bin=Eg["peak_bin"],
                edge_bins_by_drop=edge_sensitivity(H, ph),
                f_edge_hz=_f(f_edge), f_peak_hz=_f(f_peak),
                edge_over_ftip=_f(f_edge / ph["f_tip_hz"]) if f_edge else None,
                harm_abs=_fl(H["harm_abs"]),
                harm_freq_hz=_fl([k * ph["f_flash_hz"] for k in H["harm_index"]]),
                dc_abs=_f(H["dc_abs"]), wave_amp_db=_fl(amp),
                wave_phase_deg=_fl(np.degrees(np.angle(zm))))


def edge_sensitivity(H, ph, drops=(10.0, 20.0, 30.0)) -> dict:
    """⚠ 가장자리는 문턱에 민감하다. −20 dB 를 선언값으로 쓰되, 다른 문턱에서 어떻게
    움직이는지 **함께** 남긴다. 판정이 문턱 하나에 매달려 있으면 그 사실이 보여야 한다."""
    out = {}
    for d in drops:
        e = edge_bin(H, drop_db=d)
        out[f"drop{int(d)}dB"] = dict(
            edge_bin=e["edge_bin"],
            f_edge_hz=_f(e["edge_bin"] * ph["f_flash_hz"]) if e["edge_bin"] else None)
    return out


# --------------------------------------------------------------------------- #
#  §3 — 스펙트로그램 재료
# --------------------------------------------------------------------------- #
def spectrogram(zp, f_flash, n_rev=16, nper_periods=2, overlap=0.9):
    """한 주기 복소 파형 → (t[s], f[Hz], S[dB]) 양측 스펙트로그램.

    ⭐ 복소 신호를 **양측**으로 변환한다 — 전진날(+)과 후퇴날(−)이 갈리는지 보려면 필수다.
    DC(정지 동체 반사)는 뺀다. 안 빼면 색눈금이 DC 에 다 먹혀 변조가 안 보인다."""
    zp = np.asarray(zp, complex)
    N = len(zp)
    fs = N * float(f_flash)                       # 한 주기 = 1/f_flash 초
    x = np.tile(zp, int(n_rev * 2))               # 회전당 두 주기
    x = x - x.mean()
    nper = int(N * nper_periods)
    if nper > len(x):
        nper = len(x)
    step = max(1, int(nper * (1.0 - overlap)))
    win = np.hanning(nper)
    starts = range(0, len(x) - nper + 1, step)
    cols = []
    for s in starts:
        seg = x[s:s + nper] * win
        cols.append(np.fft.fftshift(np.abs(np.fft.fft(seg)) / nper))
    S = np.asarray(cols).T                        # [freq, time]
    f = np.fft.fftshift(np.fft.fftfreq(nper, d=1.0 / fs))
    t = np.asarray([s / fs for s in starts])
    return t, f, S


# --------------------------------------------------------------------------- #
#  §4 — 판정
# --------------------------------------------------------------------------- #
def judge(cell, null_floor_index, ladder, ph) -> dict:
    """한 칸(기체·거리·자세·채널) → 판정. ⛔ 문턱은 TH 에 미리 박아 둔 값만 쓴다."""
    a_val = cell.get("ac_over_noise_db")
    a_ok = (a_val is not None) and (a_val >= TH["margin_db_min"])

    r = cell.get("edge_over_ftip")
    b_ok = (r is not None) and (abs(r - 1.0) <= TH["ftip_tol"])

    #  (c) 널: 신호의 **변조지수**(무차원 = AC실효/DC)가 널의 그것보다 충분히 큰가
    c_margin = None
    if null_floor_index is not None and cell.get("modulation_index") is not None:
        c_margin = 20.0 * math.log10(max(cell["modulation_index"], 1e-30)
                                     / max(null_floor_index, 1e-30))
    c_ok = (c_margin is not None) and (c_margin >= TH["null_margin_db_min"])

    #  (d) 삼각형 사다리
    d_ok = None
    if ladder:
        d_ok = bool(ladder.get("min_pearson_r", 0) >= TH["ladder_corr_min"]
                    and ladder.get("ptp_max_rel_change", 1) <= TH["ladder_ptp_rel_max"])

    checks = dict(a_modulation_above_noise=a_ok, b_flash_freq_matches_ftip=b_ok,
                  c_sphere_null_silent=c_ok, d_survives_half_mesh=d_ok)
    known = [v for v in checks.values() if v is not None]
    if not a_ok:
        verdict = "NO_MODULATION"
    elif all(known):
        verdict = "SIONNA_NATIVE_OK"
    elif not any(v for k, v in checks.items() if k != "a_modulation_above_noise"
                 and v is not None):
        verdict = "ARTIFACT"
    else:
        verdict = "MIXED"
    broken = sorted(k for k, v in checks.items() if v is False)
    return dict(verdict=verdict, checks=checks, broken=broken,
                a_margin_db=_f(a_val), a_threshold_db=TH["margin_db_min"],
                b_edge_over_ftip=_f(r), b_tolerance=TH["ftip_tol"],
                c_null_margin_db=_f(c_margin), c_threshold_db=TH["null_margin_db_min"],
                d_ladder=ladder)


def _main_guard():
    if not os.path.exists(os.path.join(ROOT, "outputs")):
        raise SystemExit("outputs/ 가 없다")


if __name__ == "__main__":
    _main_guard()
    from report15_verdict_build import build          # 본체는 다음 파일
    build()
