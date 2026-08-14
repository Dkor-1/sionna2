# -*- coding: utf-8 -*-
"""
maneuver_bridge.py — PX4 기동 브리지 **CLI**: 세 엔진 × 두 메쉬를 같은 궤적·같은 펄스에서
==========================================================================================

px4_bridge.py(라이브러리)의 CLI 겉옷이다. 물리·좌표·위상 규약은 전부 px4_bridge 가 정하고
(그 모듈 docstring 의 부호 검산·데이터 함정 참조), 여기는 다음만 한다:

  · 인자 → 창 로드(load_window) → 펄스 샤딩(idx = shard, shard+nshards, …)
  · 엔진 하나 실행 → **elev_sweep_shards 와 같은 npz 규약**(idx, E, meta, cfg)로 저장
      meta = [grade, shard, nshards, n_pulses, prf, secs]      (자리 1..5 는 elev 와 동일)
      cfg  = [fc, t_start, R_mean, x1, x2]   x1/x2 는 엔진별(ours: div / sionna: spp,rng_override)
      + meta_json (전체 provenance 문자열) + E_raw(ours) / npaths(sionna)
  · --compare : 같은 grade·같은 펄스의 두 엔진 샤드를 병합해 **블레이드 대역 리듬 비교**
      (파형·스펙트럼·상관·리듬 몫) JSON + PNG 한 판.

■ E 열의 뜻 (엔진마다 다르다 — meta_json.phase_convention 이 진실)
  ours   : 공통 규약 s = E_kernel·e^{−j2kR(t)}  (1/r 확산 없음 — 절대 눈금은 rx_noise 앵커)
  senior : 선배 PO 원신호 (e^{−j2kR}·1/R² 내장)
  sionna : Σ a·e^{−j2πfcτ}  (실기하 — 전확산·절대위상 내장)
  → 절대 레벨은 서로 못 겹친다. 비교는 모양(단위 RMS)·리듬으로만, 절대는 rx_noise 몫.

■ ⚠대규모 생산 실행 금지 (PTD 수리 게이트 전)
  --pulses > 512 는 --allow-production 을 요구한다. sionna 는 추가로 256 초과 시
  --allow-full (px4_bridge.run_sionna_window 의 max_pulses 해제).

    # 우리 커널 × 우리 CAD / × 선배 메쉬 (64 펄스 스모크)
    PYTHONPATH=src:benchmark python benchmark/maneuver_bridge.py \
        --engine ours --mesh matrice4e --grade 2 --pulses 64 --div 8
    PYTHONPATH=src:benchmark python benchmark/maneuver_bridge.py \
        --engine ours --mesh phantom4 --grade 2 --pulses 64 --div 8
    # 선배 PO 참조(같은 펄스)
    ... --engine senior --mesh phantom4 --grade 2 --pulses 64
    # Sionna PathSolver (소규모)
    ... --engine sionna --mesh phantom4 --grade 2 --pulses 16
    # 대조 한 판 (ours vs senior)
    ... --compare --mesh phantom4 --grade 2 --pulses 64
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import px4_bridge as PB                                     # noqa: E402

C0 = PB.C0
DIV_DEFAULT = 12                     # 하우스 격자 규약 λ/12 (elevation_sweep_md.DIV)
DEF_OUT = os.path.join(ROOT, "outputs", "maneuver_shards")   # ⭐기동 전용 폴더


def rule_spp(rng_m: float) -> int:
    """(R/3)² × 1M — elevation_sweep_md 와 같은 광선 규칙."""
    return int(round(1_000_000 * (rng_m / 3.0) ** 2))


def build_poser(mesh: str):
    """--mesh → 포저. phantom4 = 선배 PLY 조립, 그 외는 우리 CAD 키."""
    return PB.SeniorMeshPoser() if mesh == "phantom4" else PB.OursPoser(mesh)


def shard_file(a, poser_key: str, tags: str) -> str:
    return os.path.join(a.outdir,
                        f"{a.engine}_{poser_key}_g{a.grade}_n{a.pulses}"
                        f"{tags}_{a.shard:02d}.npz")


# ═══ 실행 ═══════════════════════════════════════════════════════════════════
def run(a) -> None:
    # ── 생산 가드 — 브리지 검증까지는 소규모(수십~수백 펄스)만 ──────────────
    if a.pulses > 512 and not a.allow_production:
        raise SystemExit(
            f"⛔ --pulses {a.pulses} > 512 — 생산 실행은 PTD 수리 게이트 뒤다. "
            "정말 필요하면 --allow-production 을 명시하라.")
    from gpu import pick
    pick(verbose=False)
    win = PB.load_window(grade=a.grade, t_start=(a.t_start if a.t_start >= 0 else None),
                         n_pulses=a.pulses)
    poser = build_poser(a.mesh)
    idx = np.arange(a.shard, a.pulses, a.nshards)
    os.makedirs(a.outdir, exist_ok=True)

    tags = ""
    extra = {}
    t0 = time.time()
    if a.engine == "ours":
        if a.div != DIV_DEFAULT:
            tags += f"_div{a.div}"
        if a.mat_mode != "ours":
            tags += f"_mat{a.mat_mode}"
        r = PB.run_ours(poser, win, div=a.div, mat_mode=a.mat_mode,
                        blade_mat=a.blade_mat, pulses=idx,
                        progress_every=a.progress)
        extra["E_raw"] = r["E_raw"]
        cfg_x = (float(a.div), np.nan)
    elif a.engine == "senior":
        if not isinstance(poser, PB.SeniorMeshPoser):
            raise SystemExit("⛔ --engine senior 는 --mesh phantom4 전용(선배 PO 는 그 메쉬만 안다)")
        if a.occ != "full":
            tags += f"_occ{a.occ}"
        r = PB.run_senior_po(poser, win, pulses=idx, blade_mat=a.blade_mat, occ=a.occ)
        cfg_x = (np.nan, np.nan)
    elif a.engine == "sionna":
        if a.pulses > 256 and not a.allow_full:
            raise SystemExit("⛔ sionna --pulses > 256 은 --allow-full 필요(px4_bridge 가드)")
        rov = a.rng_override if a.rng_override > 0 else None
        base_r = rov if rov is not None else float(win.R[idx].mean())
        spp = a.spp if a.spp else rule_spp(base_r)
        if a.spp:
            tags += f"_p{a.spp}"
        if rov is not None:
            tags += f"_rov{rov:g}"
        r = PB.run_sionna_window(poser, win, spp=spp, pulses=idx,
                                 rng_override_m=rov,
                                 max_pulses=(None if a.allow_full else 256),
                                 progress_every=a.progress)
        extra["npaths"] = r["npaths"]
        cfg_x = (float(spp), (np.nan if rov is None else float(rov)))
    else:
        raise SystemExit(f"⛔ 모르는 엔진 {a.engine}")
    secs = time.time() - t0

    try:
        g_num = float(a.grade)
    except ValueError:
        g_num = float("nan")
    f = shard_file(a, poser.key, tags)
    rr = PB.rotor_rates_hz(win)
    meta_json = dict(
        engine=r["engine"], mesh=a.mesh, poser_key=poser.key, grade=str(a.grade),
        n_pulses=int(a.pulses), shard=int(a.shard), nshards=int(a.nshards),
        prf=win.prf, fc=win.fc, R_mean_m=round(float(win.R[idx].mean()), 3),
        rotor_rates=rr, seconds=round(secs, 1),
        E_convention=("common s = E_kernel*exp(-j2kR), no 1/r spreading"
                      if a.engine == "ours" else
                      "senior PO raw (exp(-j2kR)/R^2 included)" if a.engine == "senior"
                      else "sionna sum a*exp(-j2pi fc tau) (full spreading)"),
        engine_meta=r.get("meta", {}))          # ⚠펼치면 fc/prf 가 충돌한다 — 중첩으로
    np.savez_compressed(
        f, idx=idx, E=np.asarray(r["s"], complex),
        meta=np.array([g_num, a.shard, a.nshards, a.pulses, win.prf, secs]),
        cfg=np.array([win.fc, float(win.provenance["t_start"]),
                      float(win.R[idx].mean()), *cfg_x]),
        meta_json=np.array([json.dumps(meta_json, ensure_ascii=False, default=str)]),
        **extra)
    lv = 20 * np.log10(np.abs(np.asarray(r["s"])).mean() + 1e-300)
    print(f"  ✅ {os.path.basename(f)} · {idx.size} 펄스 · {secs:.1f}s "
          f"({secs / max(idx.size, 1):.2f}s/펄스) · level {lv:.1f} dB", flush=True)


# ═══ 병합 유틸 ══════════════════════════════════════════════════════════════
def load_arm(outdir: str, engine: str, poser_key: str, grade, n: int) -> dict:
    """엔진 하나의 샤드들을 병합 — 태그가 무엇이든 (grade, n) 이 맞으면 집는다."""
    pat = re.compile(rf"^{re.escape(engine)}_{re.escape(poser_key)}"
                     rf"_g{re.escape(str(grade))}_n{n}(?:_[^_]+)*_(\d\d)\.npz$")
    fs = sorted(f for f in os.listdir(outdir) if pat.match(f))
    if not fs:
        raise FileNotFoundError(
            f"{outdir} 에 {engine}_{poser_key}_g{grade}_n{n} 샤드가 없다")
    E = np.zeros(n, complex)
    got = np.zeros(n, bool)
    metas = []
    for f in fs:
        z = np.load(os.path.join(outdir, f), allow_pickle=False)
        ii = z["idx"].astype(int)
        E[ii] = z["E"]
        got[ii] = True
        if "meta_json" in z:
            metas.append(json.loads(str(z["meta_json"][0])))
    if not got.all():
        raise ValueError(f"{engine}: 펄스 {int((~got).sum())}/{n} 이 비었다 — 샤드 부족")
    return dict(s=E, files=fs, meta=metas[0] if metas else {})


# ═══ 대조 — 블레이드 대역 리듬 한 판 ════════════════════════════════════════
def band_spectrum(s: np.ndarray, prf: float):
    """AC(평균 제거)·해닝 창 전력 스펙트럼 — (fr, P). 단위 RMS 정규화는 호출자 몫."""
    s = np.asarray(s, complex)
    ac = s - s.mean()
    n = s.size
    S = np.fft.fftshift(np.fft.fft(ac * np.hanning(n)))
    fr = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / prf))
    return fr, np.abs(S) ** 2


def flash_period_est(s: np.ndarray, prf: float, ffl: float, ftip: float) -> float | None:
    """블레이드 대역 포락선 자기상관으로 플래시 «박자» 를 직접 잰다.

    양(+)의 블레이드 대역만 남긴 해석 신호의 포락선 AC 자기상관에서 lag ∈ [0.5,1.5]/ffl
    의 최대 → f_flash_est = 1/lag. 창이 플래시 2 주기 미만이거나 대역 빈이 없으면 None —
    (64 펄스 창은 0.3 주기라 원리적으로 못 잰다. 리듬은 수백 펄스 창의 몫이다.)"""
    s = np.asarray(s, complex)
    n = s.size
    if n / prf * ffl < 2.0:
        return None
    S = np.fft.fft(s - s.mean())
    fr = np.fft.fftfreq(n, 1.0 / prf)
    keep = (fr >= 0.35 * ftip) & (fr <= ftip)
    if keep.sum() < 3:
        return None
    env = np.abs(np.fft.ifft(np.where(keep, S, 0)))
    e = env - env.mean()
    r = np.correlate(e, e, "full")[n - 1:]
    lags = np.arange(n) / prf
    m = (lags >= 0.5 / ffl) & (lags <= 1.5 / ffl)
    if not m.any() or np.nanmax(r[m]) <= 0:
        return None
    i = int(np.argmax(np.where(m, r, -np.inf)))
    return float(1.0 / lags[i])


def compare(a) -> None:
    """⭐같은 grade·같은 펄스에서 우리 커널(phantom4 메쉬) vs 선배 PO — 블레이드 대역 리듬.

    물리 차이(가림 방식·1/R²·Γ(θ)·격자 vs facet)가 있으므로 절대 일치를 주장하지 않는다.
    비교는 (i) 단위 RMS 파형 (ii) 블레이드 대역 스펙트럼 모양 (iii) DC 뺀 복소 상관
    (iv) 리듬 몫(펄스 수가 플래시 주기를 덮을 때만)."""
    import rx_noise as RX
    win = PB.load_window(grade=a.grade, t_start=(a.t_start if a.t_start >= 0 else None),
                         n_pulses=a.pulses)
    poser = build_poser(a.mesh)
    arms = {}
    for eng in a.engines.split(","):
        arms[eng] = load_arm(a.outdir, eng, poser.key, a.grade, a.pulses)

    rr = PB.rotor_rates_hz(win)
    ffl = float(rr["f_flash_hz"])                       # 창에서 직접 잰 값 (x500 규약)
    lam = C0 / win.fc
    f_rev = float(np.mean(rr["f_rev_hz"]))
    cos_el = float(np.sqrt(np.clip(1.0 - win.u_body[:, 2] ** 2, 0, 1)).mean())
    ftip = 2.0 * (2 * np.pi * f_rev * poser.prop_radius_m) / lam * cos_el
    n = a.pulses
    dfr = win.prf / n
    flash_cycles = n / win.prf * ffl

    rows = {}
    specs = {}
    for eng, arm in arms.items():
        s = arm["s"]
        fr, P = band_spectrum(s, win.prf)
        specs[eng] = (fr, P)
        band = (np.abs(fr) >= 0.35 * ftip) & (np.abs(fr) <= ftip)
        share = (RX.rhythm_share(s, win.prf, ffl, f_above=ftip)
                 if flash_cycles >= 3.0 else None)      # 플래시 3 주기 미만이면 무의미
        rows[eng] = dict(
            level_db=round(float(20 * np.log10(np.abs(s).mean() + 1e-300)), 2),
            ac_frac_pct=round(float(100 * np.var(s - s.mean()) /
                                    max(np.mean(np.abs(s) ** 2), 1e-300)), 2),
            blade_band_frac_pct=round(float(100 * P[band].sum() / max(P.sum(), 1e-300)), 2),
            rhythm_share_pct=(round(share, 2) if share is not None else None),
            flash_hz_est=(lambda v: round(v, 1) if v else None)(
                flash_period_est(s, win.prf, ffl, ftip)),
            E_convention=arm["meta"].get("E_convention"))

    # DC 뺀 복소 상관 (모양) + 블레이드 대역 로그 스펙트럼 상관
    e0, e1 = list(arms)[:2]
    u = arms[e0]["s"] - arms[e0]["s"].mean()
    v = arms[e1]["s"] - arms[e1]["s"].mean()
    corr = float(np.abs(np.vdot(u, v)) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-300))
    fr = specs[e0][0]
    band = (np.abs(fr) >= 0.35 * ftip) & (np.abs(fr) <= ftip)
    la = 10 * np.log10(specs[e0][1][band] + 1e-300)
    lb = 10 * np.log10(specs[e1][1][band] + 1e-300)
    spec_corr = float(np.corrcoef(la, lb)[0, 1]) if band.sum() >= 3 else None

    out = dict(
        _meta=dict(
            generator="benchmark/maneuver_bridge.py:compare",
            question_ko="같은 PX4 궤적·같은 펄스에서 우리 커널과 선배 PO 의 "
                        "블레이드 대역 리듬이 겹치는가",
            grade=str(a.grade), n_pulses=n, mesh=a.mesh, poser_key=poser.key,
            fc_hz=win.fc, prf_hz=win.prf,
            f_flash_hz=round(ffl, 2), f_tip_hz=round(ftip, 1),
            cos_el=round(cos_el, 4), freq_res_hz=round(dfr, 1),
            flash_cycles_in_window=round(flash_cycles, 2),
            window_s=round(n / win.prf, 5), R_mean_m=round(float(win.R.mean()), 2),
            blade_band_hz=[round(0.35 * ftip, 1), round(ftip, 1)],
            caveats=[
                "절대 눈금 비교 아님 — ours 는 1/r 무확산(σ 앵커 규약), senior 는 1/R² 내장",
                "물리 차이: 가림(BVH facet vs SBR 격자)·Γ(θ) 각도의존·PO facet vs 광선격자",
                f"리듬 몫은 창이 플래시 {flash_cycles:.1f} 주기라 "
                + ("유효" if flash_cycles >= 3 else "무의미(None) — 펄스를 늘려야 잰다"),
                *win.provenance["caveats"]]),
        engines=rows,
        cross=dict(pair=[e0, e1], complex_corr_ac=round(corr, 3),
                   blade_band_logspec_corr=(round(spec_corr, 3)
                                            if spec_corr is not None else None)))
    os.makedirs(a.outdir, exist_ok=True)
    oj = os.path.join(a.outdir, f"compare_{poser.key}_g{a.grade}_n{n}.json")
    json.dump(out, open(oj, "w"), ensure_ascii=False, indent=1)
    png = oj.replace(".json", ".png")
    _compare_figure(arms, specs, win, ffl, ftip, out, png)
    print(json.dumps(out["cross"], ensure_ascii=False))
    print(f"  ✅ {oj}\n  ✅ {png}")


def _compare_figure(arms, specs, win, ffl, ftip, out, png) -> None:
    """비교 한 판 — 그림 텍스트는 영어(하우스 규약).

    색: Okabe–Ito CVD-안전 쌍(파랑=ours, 주황(버밀리언)=senior) — 팔레트 검증기(node)가
    이 환경에 없어 검증된 기성 팔레트를 쓴다. 엔진→색 고정(순환 금지)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    COL = {"ours": "#0072B2", "senior": "#D55E00", "sionna": "#009E73"}
    NAME = {"ours": "our kernel (SBR+PO)", "senior": "senior PO",
            "sionna": "Sionna PathSolver"}
    n = out["_meta"]["n_pulses"]
    t_ms = np.arange(n) / win.prf * 1e3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.8))
    for eng, arm in arms.items():
        s = arm["s"]
        ac = s - s.mean()
        w = ac / max(np.sqrt(np.mean(np.abs(ac) ** 2)), 1e-300)
        ax1.plot(t_ms, np.abs(w), color=COL.get(eng, "0.4"), lw=1.9,
                 label=NAME.get(eng, eng))
    ax1.set_xlabel("slow time [ms]")
    ax1.set_ylabel("|AC component|  (unit-RMS, shape only)")
    ax1.set_title(f"Slow-time waveform — grade {out['_meta']['grade']}, "
                  f"{n} pulses", fontsize=11)
    for eng in arms:
        fr, P = specs[eng]
        Pn = P / max(P.max(), 1e-300)
        ax2.plot(fr / 1e3, 10 * np.log10(Pn + 1e-12), color=COL.get(eng, "0.4"),
                 lw=1.7, label=NAME.get(eng, eng))
    ax2.axvspan(0.35 * ftip / 1e3, ftip / 1e3, color="0.55", alpha=0.14, lw=0,
                label="blade band 0.35–1.0 f_tip")
    ax2.axvspan(-ftip / 1e3, -0.35 * ftip / 1e3, color="0.55", alpha=0.14, lw=0)
    ax2.set_xlabel("slow-time frequency [kHz]")
    ax2.set_ylabel("power [dB rel. peak]")
    ax2.set_ylim(-80, 3)
    ax2.set_title(f"AC spectrum — f_flash≈{ffl:.0f} Hz, f_tip≈{ftip:.0f} Hz "
                  f"(res {out['_meta']['freq_res_hz']:.0f} Hz)", fontsize=11)
    cr = out["cross"]
    ax2.annotate(f"corr(AC) = {cr['complex_corr_ac']:.3f}\n"
                 f"band log-spec corr = {cr['blade_band_logspec_corr']}",
                 xy=(0.02, 0.03), xycoords="axes fraction", fontsize=9.5,
                 color="#333333",
                 bbox=dict(fc="white", ec="0.75", alpha=0.9, boxstyle="round,pad=0.35"))
    for ax in (ax1, ax2):
        ax.grid(True, color="0.9", lw=0.7)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    fig.suptitle("Our kernel vs senior PO on the same PX4 trajectory "
                 "(shape comparison — absolute scales differ by convention)",
                 fontsize=12, y=1.0)
    fig.tight_layout()
    fig.savefig(png, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ═══ CLI ════════════════════════════════════════════════════════════════════
def main() -> None:
    ap = argparse.ArgumentParser(description="PX4 기동 브리지 — 세 엔진 × 두 메쉬")
    ap.add_argument("--engine", default="ours", choices=("ours", "senior", "sionna"),
                    help="ours=우리 커널(sbr_field) · senior=선배 PO 직접 호출(참조) · "
                         "sionna=PathSolver(1 윈도우 한정)")
    ap.add_argument("--mesh", default="matrice4e",
                    help="phantom4=선배 PLY 조립 · 그 외는 우리 CAD 키(matrice4e 등)")
    ap.add_argument("--grade", default="2", help="선배 grade CSV 번들 (0..7)")
    ap.add_argument("--pulses", type=int, default=64,
                    help="창 펄스 수 (>512 는 --allow-production)")
    ap.add_argument("--t-start", type=float, default=-1.0,
                    help="창 시작 시각 [s]. 음수면 선배 규약 t_skip=5 s")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--div", type=int, default=DIV_DEFAULT,
                    help=f"우리 커널 격자 λ/DIV (기본 {DIV_DEFAULT}=하우스 규약)")
    ap.add_argument("--mat-mode", default="ours", choices=("ours", "senior"),
                    help="선배 메쉬 재질: ours=우리 표 근사 매핑 · senior=선배 (εr,σ) 등록")
    ap.add_argument("--blade-mat", default="nylon", choices=("nylon", "cf", "metal"))
    ap.add_argument("--occ", default="full", choices=("none", "body", "full"),
                    help="senior PO 가림 조합 (기본 full=body_occ+blade_occ)")
    ap.add_argument("--spp", type=int, default=0,
                    help="sionna 광선 수. 0=규칙 (R/3)²×1M (R=실거리 또는 override)")
    ap.add_argument("--rng-override", type=float, default=0.0,
                    help="sionna 배관시험용 거리 박기 [m] (0=로그 실거리). "
                         "기하 충실성이 깨진다 — 비교 수치 인용 금지")
    ap.add_argument("--outdir", default=DEF_OUT)
    ap.add_argument("--progress", type=int, default=32)
    ap.add_argument("--allow-production", action="store_true",
                    help="⚠512 펄스 초과 해제 — PTD 수리 게이트 전에는 쓰지 마라")
    ap.add_argument("--allow-full", action="store_true",
                    help="⚠sionna 256 펄스 초과 해제(px4_bridge max_pulses=None)")
    ap.add_argument("--compare", action="store_true",
                    help="⭐같은 grade·펄스의 두 엔진 샤드를 병합해 블레이드 대역 리듬 비교")
    ap.add_argument("--engines", default="ours,senior",
                    help="--compare 대상 (쉼표, 순서=그림 순서)")
    a = ap.parse_args()
    compare(a) if a.compare else run(a)


if __name__ == "__main__":
    main()
