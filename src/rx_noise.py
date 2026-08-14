# -*- coding: utf-8 -*-
"""
rx_noise.py — 링크버짓 기반 **수신 잡음 모듈** + 탐지 곡선 파이프라인 초안
==========================================================================

역할 하나: 커널이 낸 **모양·위상**(복소 슬로타임 열 E)에 **절대 눈금**과 **열잡음**을 입혀
«거리 R 에서 날개 무늬 리듬 몫이 잡음선(≈13 %)에 닿는 지점» 을 낸다.

■ ⭐절대 눈금 규약 — 커널의 15 m 규약과 정면으로 마주 본다
  우리 커널(sbr_field)은 (i) 구면파 **조명**(range_m)으로 위상 곡률만 넣고
  (ii) **1/r 확산은 넣지 않는다**(rcs_sbr.py "이 배선이 하는 것과 안 하는 것").
  즉 E 의 절대 크기는 «그 거리의 수신 전력» 이 아니다 — E 는 σ = (4π/λ²)|E|² 를 통해
  **RCS 로만** 읽어야 한다. 그래서 이 모듈은:

      σ_kernel(t) = (4π/λ²)|E(t)|²                (커널의 순간 RCS, 모양·리듬 담당)
      c_anchor    = σ_ref / ⟨σ_kernel⟩            (문헌 앵커 → 레벨 담당, 단위 없음)
      P_echo(t,R) = radar_eq(σ_kernel(t)·c_anchor, R)   (1/R⁴ 은 **여기서만** 들어간다)

  σ_ref 는 공개 문헌 RCS 앵커다(sigma_anchor.anchor_mu_dbsm — Das/Yuan, 방위 선형평균
  규약). 우리 σ 절대값이 맞다는 주장이 아니라 **재보정**이다(sigma_anchor.py 서두) —
  JSON 원장에 c_anchor 와 출처를 반드시 남긴다.
  ⚠ 이중계상 금지: E 를 range_m=R 구면파로 계산했어도 그것은 위상 곡률뿐이므로
  1/R⁴ 를 다시 곱하는 것은 이중계상이 **아니다**. 반대로 선배 PO 신호(1/R² 포함)를
  이 모듈에 넣으려면 먼저 눈금을 σ 로 되돌려야 한다(넣기 전 |s|·R² 보정).

■ 잡음 규약 (v2, docs/NOISE_AND_ROTOR_PLAN.md §1-2 · outputs/snr_convention.json)
  풀 웨이브폼 캡처: 슬로타임 표본 = PRI 하나의 정합필터 출력.
  대역 B 는 정합필터 이득에서 약분되어(SNR 항에 B 없음 — freespace_link.snr_rd_db 주석)
      노이즈 전력(표본당) N = k·T0·F·PRF        (= kTB·NF, B←PRF)
      SNR_sample = P_echo / N
  복소 백색가우스: n ~ CN(0, N) → 실·허 각각 분산 N/2.

■ 탐지 잣대 — «구조» 지표 (benchmark/build_deck_maps.structure_bars 규약)
  상한(f_tip·cos 규약은 호출자 소관) 위 에너지 중 f_flash 정수배(±hw)에 붙은 몫 [%].
  백색잡음 ≈13 %, 이상적 로터 100 %. 세기가 아니라 구조라 눈금 무관 — 그래서
  잡음이 이길수록 13 % 로 내려간다. 탐지 곡선 = 몫(R) 이 잡음선에 닿는 R.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))          # = <root>/src
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "benchmark")):          # link_budget 은 benchmark 에 산다
    if _p not in sys.path:
        sys.path.insert(0, _p)

from link_budget import LinkBudget, K_BOLTZ, T0, C0    # noqa: E402  (재구현 금지)


# --------------------------------------------------------------------------- #
#  1. 절대 눈금 — σ 앵커
# --------------------------------------------------------------------------- #
def sigma_kernel_m2(E, fc: float) -> np.ndarray:
    """커널 복소장 E [m²] → 순간 σ(t) [m²].  σ = (4π/λ²)|E|² (rcs_sbr 규약)."""
    lam = C0 / float(fc)
    return 4.0 * np.pi / lam ** 2 * np.abs(np.asarray(E, complex)) ** 2


def sigma_ref_from_literature(fc: float, drone_key: str | None = None) -> dict:
    """공개 문헌 앵커 σ_ref [dBsm] — sigma_anchor(Das/Yuan, 방위 선형평균 규약).

    drone_key 를 주면 크기보정(size_correction_db, L² 법)을 얹는다.
    반환 dict(sigma_ref_dbsm, provenance...). 실패하면 예외 — 조용한 폴백 금지."""
    from sigma_anchor import anchor_mu_dbsm, size_correction_db, DEFAULT_ANCHOR
    f_ghz = float(fc) / 1e9
    mu = float(np.asarray(anchor_mu_dbsm(f_ghz)).reshape(-1)[0])
    corr, prov_c = 0.0, None
    if drone_key:
        sc = size_correction_db(drone_key)
        corr = float(sc["corr_db"]) if isinstance(sc, dict) else float(sc)
        prov_c = sc if isinstance(sc, dict) else {"corr_db": corr}
    return dict(sigma_ref_dbsm=mu + corr,
                provenance=dict(anchor=DEFAULT_ANCHOR, f_ghz=f_ghz,
                                anchor_mu_dbsm=mu, size_corr_db=corr,
                                size_corr=prov_c,
                                convention="azimuth linear-mean (sigma_anchor §규약)",
                                note="재보정(re-levelling)이지 검증이 아니다"))


def anchor_scale(E, fc: float, sigma_ref_dbsm: float) -> dict:
    """앵커 배율 c = σ_ref / ⟨σ_kernel⟩ (창 평균, 선형).  원장용 dict 반환."""
    sk = sigma_kernel_m2(E, fc)
    mean = float(sk.mean())
    if mean <= 0:
        raise ValueError("커널 σ 평균이 0 — E 가 비었거나 전부 0 이다")
    ref = 10.0 ** (float(sigma_ref_dbsm) / 10.0)
    return dict(c_anchor=ref / mean,
                sigma_kernel_mean_dbsm=round(10 * np.log10(mean), 2),
                sigma_ref_dbsm=round(float(sigma_ref_dbsm), 2))


# --------------------------------------------------------------------------- #
#  2. 수신 열 — 레이더 방정식 + 열잡음
# --------------------------------------------------------------------------- #
@dataclass
class RxSpec:
    """수신 예산 — 전부 **선언값**(근거는 호출자가 원장에 적는다)."""
    eirp_dbm: float = 63.0        # link_budget 기본(매크로 셀). 챔버 저출력은 12.
    grx_dbi: float = 10.0
    nf_db: float = 5.0
    sys_loss_db: float = 0.0
    capture: str = "full_waveform"   # 잡음 규약 v2 — 모듈 docstring


def noise_power_w(spec: RxSpec, prf: float) -> float:
    """표본당 잡음 전력 N = k·T0·F·PRF [W]  (풀캡처·정합필터 출력 규약)."""
    return float(LinkBudget(noise_figure_db=spec.nf_db).noise_power_w(float(prf)))


def rx_series(E, R, fc: float, prf: float, spec: RxSpec,
              sigma_ref_dbsm: float, rng: np.random.Generator | None = None,
              noiseless: bool = False) -> dict:
    """커널 열 E(공통 규약 위상) + 거리 R → 수신 슬로타임 열 (잡음 주입).

    · E : (n,) complex — px4_bridge.run_ours 의 `s`(위상 규약 포함) 권장.
    · R : 스칼라(고정 스탠드오프) 또는 (n,)(로그의 실거리) [m]. 모노스태틱 R1=R2=R
      → P_echo ∝ σ/R⁴ (link_budget.echo_power_w 재사용, 재구현 금지).
    반환: x(수신 열), snr_sample_db(창 평균), N_w, scale(anchor 원장)."""
    E = np.asarray(E, complex)
    Rv = np.broadcast_to(np.asarray(R, float), E.shape)
    lam = C0 / float(fc)
    sc = anchor_scale(E, fc, sigma_ref_dbsm)
    sig = sigma_kernel_m2(E, fc) * sc["c_anchor"]
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    P = np.asarray(lb.echo_power_w(lam, sig, Rv, Rv), float)      # [W] per pulse
    phase = np.where(np.abs(E) > 0, E / np.maximum(np.abs(E), 1e-300), 1.0)
    x = np.sqrt(P) * phase                                        # 진폭[√W]·위상 보존
    N = noise_power_w(spec, prf)
    if not noiseless:
        rng = rng or np.random.default_rng()
        x = x + rng.normal(scale=np.sqrt(N / 2), size=(E.size, 2)).view(complex).ravel()
    return dict(x=x, N_w=N, scale=sc,
                snr_sample_db=round(float(10 * np.log10(P.mean() / N)), 2),
                spec=asdict(spec))


# --------------------------------------------------------------------------- #
#  3. 구조 지표 — 날개 리듬 몫 (build_deck_maps.structure_bars 규약)
# --------------------------------------------------------------------------- #
def rhythm_share(x, prf: float, f_flash: float, f_above: float | None = None,
                 hw_hz: float = 8.0) -> float:
    """상한 위 에너지 중 f_flash 정수배(±hw)에 붙은 몫 [%].

    f_above: 이 주파수 이상만 센다(기본 0.35·f_flash·… 대신 **f_tip 규약은 호출자 소관**;
    None 이면 f_flash·1.5 위 — 동체 DC/저주파를 뺀 보수적 기본)."""
    x = np.asarray(x, complex)
    n = x.size
    P = np.abs(np.fft.fft((x - x.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / float(prf))
    fa = 1.5 * float(f_flash) if f_above is None else float(f_above)
    above = np.abs(fr) >= fa
    if not above.any() or P[above].sum() <= 0:
        return float("nan")
    kk = np.round(np.abs(fr) / float(f_flash))
    on = above & (np.abs(np.abs(fr) - kk * float(f_flash)) <= float(hw_hz))
    return float(100.0 * P[on].sum() / P[above].sum())


def noise_line(prf: float, f_flash: float, f_above: float | None = None,
               hw_hz: float = 8.0, n: int = 8192, n_trial: int = 16,
               seed: int = 0) -> dict:
    """백색잡음의 리듬 몫 기준선(≈13 %) — 같은 지표·같은 창으로 직접 잰다(가정 아님)."""
    rng = np.random.default_rng(seed)
    v = [rhythm_share(rng.normal(size=(n, 2)).view(complex).ravel(),
                      prf, f_flash, f_above, hw_hz) for _ in range(n_trial)]
    v = np.asarray(v, float)
    return dict(mean_pct=round(float(v.mean()), 2), std_pct=round(float(v.std()), 2),
                n=n, n_trial=n_trial)


# --------------------------------------------------------------------------- #
#  4. 탐지 곡선 — 몫(R) 이 잡음선에 닿는 R
# --------------------------------------------------------------------------- #
def detection_curve(E, fc: float, prf: float, f_flash: float, *,
                    spec: RxSpec | None = None, sigma_ref_dbsm: float,
                    R_grid=None, n_noise: int = 16, f_above: float | None = None,
                    hw_hz: float = 8.0, seed: int = 0, out_json: str | None = None
                    ) -> dict:
    """⭐탐지 곡선 파이프라인 초안 — 거리 격자에서 리듬 몫을 재고 잡음선 교차 R 을 낸다.

    · E : 무잡음 커널 열(공통 규약). 거리는 **눈금으로만** 들어간다(모양 재계산 없음 —
      A1 팔 규약: experiment_md_range "거리는 잡음 크기만 바꾼다").
      ⚠ 근접장 모양 변화(A2 팔)는 여기 없다 — E 를 그 거리 range_m 으로 다시 계산해
      넣으면 자동으로 합쳐진다(브리지 run_ours(spherical=True) + R 스칼라 대신 실거리).
    · 판정: mean(몫) 이 잡음선 mean+2·std 아래로 **처음** 내려가는 R (로그 보간).
      원(原) 잡음선(mean)에 닿는 R 도 병기한다.
    반환 dict(rows, R_hit_m, noise_line, ...) — out_json 주면 저장."""
    spec = spec or RxSpec()
    R_grid = np.geomspace(5.0, 2000.0, 25) if R_grid is None else np.asarray(R_grid, float)
    nl = noise_line(prf, f_flash, f_above, hw_hz, n=int(np.asarray(E).size),
                    n_trial=max(8, n_noise), seed=seed)
    rng = np.random.default_rng(seed + 1)
    rows = []
    for R in R_grid:
        shares, snrs = [], None
        for _ in range(n_noise):
            r = rx_series(E, float(R), fc, prf, spec, sigma_ref_dbsm, rng=rng)
            shares.append(rhythm_share(r["x"], prf, f_flash, f_above, hw_hz))
            snrs = r["snr_sample_db"]
        sh = np.asarray(shares, float)
        rows.append(dict(R_m=round(float(R), 2), snr_sample_db=snrs,
                         share_mean_pct=round(float(np.nanmean(sh)), 2),
                         share_std_pct=round(float(np.nanstd(sh)), 2)))

    def _cross(th):
        m = np.array([r["share_mean_pct"] for r in rows], float)
        below = m <= th
        if not below.any():
            return None
        if below.all():
            return float(R_grid[0])
        i = int(np.argmax(below))                      # 첫 하강 교차
        x0, x1 = np.log10(R_grid[i - 1]), np.log10(R_grid[i])
        y0, y1 = m[i - 1], m[i]
        w = (y0 - th) / max(y0 - y1, 1e-12)
        return float(10 ** (x0 + w * (x1 - x0)))

    th2 = nl["mean_pct"] + 2 * nl["std_pct"]
    out = dict(
        R_grid_m=[round(float(r), 2) for r in R_grid],
        _meta=dict(
            generator="src/rx_noise.py:detection_curve",
            question_ko="거리 R 에서 날개 리듬 몫이 잡음선(≈13 %)에 닿는 지점",
            convention=dict(
                scale="σ_ref 문헌 앵커 재보정 — 커널 15 m 구면파 조명은 위상 곡률뿐, "
                      "1/R⁴ 은 레이더 방정식에서만(이중계상 아님)",
                noise="N = kT0·F·PRF (풀캡처 v2, B 약분)",
                metric="rhythm share (build_deck_maps.structure_bars 규약, 백색잡음≈13 %)",
                arm="A1(잡음만) — 근접장 모양 변화(A2)는 E 재계산으로 합류"),
            fc_hz=float(fc), prf_hz=float(prf), f_flash_hz=float(f_flash),
            f_above_hz=(1.5 * f_flash if f_above is None else float(f_above)),
            hw_hz=float(hw_hz), n_noise=int(n_noise), spec=asdict(spec),
            sigma_ref_dbsm=float(sigma_ref_dbsm)),
        noise_line=nl,
        R_hit_m=dict(at_noise_mean=_cross(nl["mean_pct"]),
                     at_noise_mean_plus_2std=_cross(th2)),
        rows=rows)
    if out_json:
        os.makedirs(os.path.dirname(out_json), exist_ok=True)
        json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1)
    return out


# --------------------------------------------------------------------------- #
#  5. 데모 — 기존 15 m matrice4e 시계열로 탐지 곡선 1 장
# --------------------------------------------------------------------------- #
def demo(series_key: str = "ours_r15_n8192/el-15", eirp_dbm: float = 30.0,
         out_dir: str | None = None, seed: int = 0) -> dict:
    """⭐데모: **기존** 15 m matrice4e 시계열(outputs/elevation_sweep_md.npz, 읽기 전용)로
    «리듬 몫 vs 거리» 곡선 한 장을 낸다. 산출은 이 체크아웃(워크트리)의
    outputs/rx_noise_demo/ 아래 — 본체 outputs 는 건드리지 않는다.

    · 대역 규약: 잣대는 build_deck_maps.structure_bars 와 같은 «상한 위 구조» —
      f_above = 그 앙각의 f_tip(원장 값), f_flash·hw 도 원장 값.
    · EIRP 30 dBm 은 **선언값**(소형 모노스태틱 센서급 가정) — 원장에 그대로 남는다."""
    npz = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
    z = np.load(npz)
    if series_key not in z.files:
        raise KeyError(f"{series_key} 가 {npz} 에 없다 (있는 키 예: ours_r15_n8192/el-15)")
    E = np.asarray(z[series_key], complex)
    tj = json.load(open(os.path.join(ROOT, "outputs",
                                     "report07_three_engines.json")))["_meta"]
    fc, prf = float(tj["fc_hz"]), float(tj["prf_hz"])
    ffl, ftip = float(tj["f_flash_hz"]), float(tj["f_tip_hz"])   # f_tip = −15° 값
    drone = str(tj.get("drone", "matrice4e"))
    ref = sigma_ref_from_literature(fc, drone)
    od = out_dir or os.path.join(ROOT, "outputs", "rx_noise_demo")
    os.makedirs(od, exist_ok=True)
    out = detection_curve(
        E, fc, prf, ffl, spec=RxSpec(eirp_dbm=float(eirp_dbm)),
        sigma_ref_dbsm=ref["sigma_ref_dbsm"], f_above=ftip,
        R_grid=np.geomspace(10.0, 3000.0, 19), n_noise=12, seed=seed,
        out_json=os.path.join(od, "detection_curve_demo.json"))
    out["_meta"].update(series=series_key, source_npz=npz, drone=drone,
                        sigma_anchor=ref["provenance"],
                        note_ko="기존 15 m matrice4e 시계열(본체 outputs 판) — 데모. "
                                "EIRP 30 dBm 은 선언값.")
    json.dump(out, open(os.path.join(od, "detection_curve_demo.json"), "w"),
              ensure_ascii=False, indent=1)
    _demo_figure(out, os.path.join(od, "detection_curve_demo.png"),
                 series_key, drone)
    return out


def _demo_figure(out: dict, png: str, series_key: str, drone: str) -> None:
    """곡선 1 장 — 그림 텍스트는 영어(하우스 규약), 겹침 금지.

    색은 Okabe–Ito CVD-안전 쌍(파랑 #0072B2 / 회색) — 팔레트 검증기(node)가 이
    환경에 없어, 검증된 기성 팔레트를 그대로 쓴다(자작 색 금지)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    R = np.asarray(out["R_grid_m"], float)
    m = np.array([r["share_mean_pct"] for r in out["rows"]], float)
    s = np.array([r["share_std_pct"] for r in out["rows"]], float)
    snr = np.array([r["snr_sample_db"] for r in out["rows"]], float)
    nl = out["noise_line"]
    th2 = nl["mean_pct"] + 2 * nl["std_pct"]
    hit = out["R_hit_m"]["at_noise_mean_plus_2std"]
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.fill_between(R, m - s, m + s, color="#0072B2", alpha=0.15, lw=0)
    ax.plot(R, m, color="#0072B2", lw=2.2, marker="o", ms=4.5,
            label=f"rotor rhythm share ({drone}, 15 m kernel series)")
    ax.axhline(nl["mean_pct"], color="#666666", lw=1.6, ls="--",
               label=f"white-noise line {nl['mean_pct']:.1f} %")
    ax.axhspan(nl["mean_pct"] - 2 * nl["std_pct"], th2, color="#666666",
               alpha=0.12, lw=0, label="noise line ±2σ")
    if hit:
        ax.axvline(hit, color="#333333", lw=1.4, ls=":")
        ax.annotate(f"R_hit ≈ {hit:.0f} m", xy=(hit, th2),
                    xytext=(hit * 1.12, th2 + 14), fontsize=10, color="#333333",
                    arrowprops=dict(arrowstyle="-", color="#333333", lw=0.9))
    ax.set_xscale("log")
    ax.set_xlabel("range R [m]  (noise-only arm: R scales the budget, not the shape)")
    ax.set_ylabel("flash-comb share above tip ceiling [%]")
    ax.set_title("Detection curve draft — rotor rhythm share vs range", fontsize=12)
    ax.grid(True, which="both", color="0.9", lw=0.7)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    # 보조 축 없이(단일 축 규약) SNR 은 주석 두 개로만 남긴다
    for i in (0, len(R) - 1):
        ax.annotate(f"SNR {snr[i]:+.0f} dB", xy=(R[i], m[i]),
                    xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=8.5, color="#555555")
    fig.tight_layout()
    fig.savefig(png, dpi=150)
    plt.close(fig)
    print(f"  ✅ {png}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="rx_noise 데모 — 기존 15 m matrice4e 시계열")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--series", default="ours_r15_n8192/el-15")
    ap.add_argument("--eirp-dbm", type=float, default=30.0)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.demo:
        o = demo(a.series, a.eirp_dbm, seed=a.seed)
        print(json.dumps(dict(R_hit_m=o["R_hit_m"], noise_line=o["noise_line"]),
                         ensure_ascii=False))
    else:
        print("사용: python src/rx_noise.py --demo [--series KEY] [--eirp-dbm 30]")
