# -*- coding: utf-8 -*-
"""
r12_azimuth_harvest.py — **R12 · 방위 45° 팔 수확** (설계서 `docs/NEXT_EXPERIMENTS.md` 3 위)

묻는 것
    「0° 에서 프로펠러가 익사한다」가 **앙각의 성질**인가, **정면(방위 0°) 한정**인가.

왜 이 스크립트가 필요한가
    원장 `outputs/elevation_sweep_md.{json,npz}` 안에 방위 45° 로 돈 팔이 12 계열 있는데
    (엔진 3 × 앙각 4) 지금까지 **어떤 코드도 읽지 않았다**. 계산은 이미 끝나 있다.

⛔GPU 를 쓰지 않는다 — `sionna.rt` · `mitsuba` 를 임포트하지 않는다. 저장된 원장만 읽는다.

⭐사전 등록 (설계서 §② 3 행 · §3-1 «R12» 절을 그대로 옮긴 것)
    1. **절대레벨 게이트가 먼저다.** az45 팔의 **DC(정지성분) 제거 AC** 가 같은 (엔진, 앙각)의
       az0 팔 대비 **−20 dB 밖**이면 리듬 몫 비교를 **인정하지 않고** «az45 는 에코 부재» 로
       판정한다. 그 칸의 몫은 계산하더라도 **JSON 에 싣지 않는다**(`null`) — 몫 단독 인용이
       물리적으로 불가능해야 한다.
    2. 채점 앙각은 **0 · −30 · −60** 셋. el −90 은 방위가 퇴화한다(`los(az,−90)=[0,0,−1]`)
       — 죽은 축임을 **자가검사로 재확인**만 하고 채점에서 뺀다.
    3. az45 에 없는 앙각(−15 · −45 · −75)은 나란히 놓지 않는다.

리듬(구조) 잣대 — 집 표준 레시피 (`benchmark/build_switch_grid_figs.py:rhythm_share` 와 동일)
    P = |FFT((E − mean(E)) · hanning)|² · above = |f_r| ≥ f_tip(el)
    리듬 몫[%] = above 대역 전력 중 f_flash 정수배 ±8 Hz 에 붙은 몫. 백색잡음 ≈ 12.6, 이상 로터 100.

굽는 것
    outputs/r12_azimuth_harvest.json
    outputs/figures/r12_gate_levels.png       게이트 판 — 절대 AC·DC 레벨과 −20 dB 문턱
    outputs/figures/r12_rhythm_admissible.png 게이트 통과 칸의 리듬 몫만 az0 ↔ az45
    outputs/figures/r12_el0_stft.png          el 0 STFT 네 판 — 게이트가 무엇을 막는지

    cd /workspace/sionna && PYTHONPATH=src:benchmark \
        /workspace/.venvs/py312/bin/python benchmark/r12_azimuth_harvest.py
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
import numpy as np                                                     # noqa: E402
from numpy.lib.stride_tricks import sliding_window_view                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from md_mapstyle import auto_periods, flash_spec, draw                  # noqa: E402

LEDGER_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_Z = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
SWITCH_J = os.path.join(ROOT, "outputs", "switch_grid.json")
OUT_J = os.path.join(ROOT, "outputs", "r12_azimuth_harvest.json")
FIG = os.path.join(ROOT, "outputs", "figures")

HALF_WIDTH_HZ = 8.0        # 박자 창 반폭 — 집 표준
GATE_DB = -20.0            # ⭐사전 등록 절대레벨 게이트
SCORE_ELS = (0.0, -30.0, -60.0)     # 채점 앙각 (−90 은 방위 퇴화라 제외)
ALL_ELS = (0.0, -30.0, -60.0, -90.0)

#: (az0 팔, az45 팔, 표시 이름[영어], 짧은 한국어 이름)
PAIRS = [
    ("ours_r15_n8192", "ours_r15_n8192_az45",
     "Our kernel (SBR+PO)", "우리 커널"),
    ("sionna_p4000000000_r15_n8192_d1", "sionna_p4000000000_r15_n8192_az45_d1",
     "PathSolver, physics off", "PathSolver 물리 끔"),
    ("sionna_p4000000000_phys_r15_n8192_d1", "sionna_p4000000000_phys_r15_n8192_az45_d1",
     "PathSolver, physics on", "PathSolver 물리 켬"),
]


# =========================================================================== #
#  원장 읽기
# =========================================================================== #
J = json.load(open(LEDGER_J))
Z = np.load(LEDGER_Z, allow_pickle=True)
META = J["_meta"]
PRF = float(META["prf_hz"])
FFL = float(META["f_flash_hz"])

ROW_IDX = {}
for i, r in enumerate(J["rows"]):
    ROW_IDX[(r["engine"], float(r["el_deg"]))] = i


def row(engine: str, el: float) -> dict:
    return J["rows"][ROW_IDX[(engine, el)]]


def key(engine: str, el: float) -> str:
    return f"{engine}/el{el:+.0f}"


def series(engine: str, el: float) -> np.ndarray:
    return np.asarray(Z[key(engine, el)], complex)


# =========================================================================== #
#  잣대
# =========================================================================== #
def levels_db(E: np.ndarray) -> dict:
    """세 레벨 [dB] — 전체 · DC(정지성분) · AC(DC 제거). ⭐비교는 전부 AC 로 한다."""
    dc = complex(E.mean())
    ac = E - dc
    return {
        "total_db": round(float(10 * np.log10(np.mean(np.abs(E) ** 2))), 2),
        "dc_db": round(float(20 * np.log10(abs(dc))), 2),
        "ac_db": round(float(10 * np.log10(np.mean(np.abs(ac) ** 2))), 2),
    }


def spectrum(E: np.ndarray):
    """DC 제거 + 한나 창 느린시간 스펙트럼 — 리듬 잣대의 유일한 원천."""
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    return fr, P


def rhythm_and_above(E: np.ndarray, f_tip: float, hw: float = HALF_WIDTH_HZ):
    """리듬 몫[%] · 상한 위 몫[%] · 상한 위 절대 AC 전력[dB]."""
    fr, P = spectrum(E)
    above = np.abs(fr) >= f_tip
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= hw
    rhythm = 100.0 * P[above & on].sum() / P[above].sum()
    above_frac = 100.0 * P[above].sum() / P.sum()
    # 절대 전력: 스펙트럼 합을 시간영역 AC 전력으로 되돌려 준다(파스발 · 창 손실 보정).
    n = E.size
    w = np.hanning(n)
    scale = float(np.sum(w ** 2)) * n
    above_pow_db = 10 * np.log10(max(P[above].sum() / scale, 1e-300))
    return float(rhythm), float(above_frac), float(above_pow_db)


def modspec(E: np.ndarray, f_tip: float):
    """블레이드 대역(0.35~1.0 × f_tip) 전력의 변조 스펙트럼 — STFT 로만 만든다.

    `benchmark/build_switch_grid_figs.py:modspec` 과 같은 규약(0.45 주기 · hop 2 · 8× 패딩).
    """
    nper = max(8, int(round(0.45 * PRF / FFL)))
    nfft = 8 * nper
    w = np.hanning(nper + 1)[:-1]
    frm = sliding_window_view(E, nper)[::2]
    S = np.abs(np.fft.fft(frm * w, n=nfft, axis=1)).T / w.sum()
    f = np.fft.fftshift(np.fft.fftfreq(nfft, 1.0 / PRF))
    S = np.fft.fftshift(S, axes=0)
    m = (np.abs(f) >= 0.35 * f_tip) & (np.abs(f) <= f_tip)
    g = (S ** 2)[m, :].sum(axis=0)
    n = g.size
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1.0 / (PRF / 2.0))
    return fr, Y


def beat(E: np.ndarray, f_tip: float):
    """박자 위치 [Hz] 와 국소 바닥 위 높이 [dB] — 60~300 Hz 안의 첫 봉우리."""
    fr, Y = modspec(E, f_tip)
    sel = (fr > 60.0) & (fr < 300.0)
    i = int(np.argmax(Y[sel]))
    pk = float(fr[sel][i])
    floor = (fr > 30.0) & (fr < 400.0) & (np.abs(fr - pk) > 30.0)
    h = float(10 * np.log10(Y[sel][i] / np.median(Y[floor])))
    return round(pk, 2), round(h, 2)


def white_neutral(f_tip: float, n: int = 8192, reps: int = 200, seed: int = 20260815):
    """같은 잣대가 **백색잡음**에 주는 점수 — 리듬 몫의 중립선."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(reps):
        E = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2.0)
        vals.append(rhythm_and_above(E, f_tip)[0])
    return round(float(np.mean(vals)), 2), round(float(np.std(vals)), 2)


def shuffle_null(E: np.ndarray, f_tip: float, reps: int = 40, seed: int = 4242):
    """시간축을 뒤섞은 널 — 이 팔 자신의 진폭 분포를 유지한 채 리듬만 부순다."""
    rng = np.random.default_rng(seed)
    vals = [rhythm_and_above(rng.permutation(E), f_tip)[0] for _ in range(reps)]
    return round(float(np.mean(vals)), 2), round(float(np.max(vals)), 2)


# =========================================================================== #
#  ① 방위 태그 팔 전수 조사
# =========================================================================== #
def survey() -> dict:
    az_rows = [r for r in J["rows"] if float(r.get("az_deg", 0.0)) != 0.0]
    engines = sorted({r["engine"] for r in az_rows})
    per_engine = {}
    for e in engines:
        rs = sorted((r for r in az_rows if r["engine"] == e), key=lambda r: -float(r["el_deg"]))
        per_engine[e] = {
            "az_deg": float(rs[0]["az_deg"]),
            "elevations_deg": [float(r["el_deg"]) for r in rs],
            "range_m": float(rs[0]["range_m"]),
            "n_poses": int(rs[0]["n_poses"]),
            "n_missing_total": int(sum(int(r["n_missing"]) for r in rs)),
            "max_depth": rs[0]["max_depth"],
            "spp": rs[0]["spp"],
            "physics": rs[0]["physics"],
            "grid_div": rs[0]["grid_div"],
            "seconds_total": round(float(sum(float(r["seconds"]) for r in rs)), 1),
            "npz_keys": [key(e, float(r["el_deg"])) for r in rs],
            "row_indices": [ROW_IDX[(e, float(r["el_deg"]))] for r in rs],
        }
    secs = sum(v["seconds_total"] for v in per_engine.values())
    return {
        "n_az_tagged_series": len(az_rows),
        "engines": per_engine,
        "elevations_present_deg": sorted({float(r["el_deg"]) for r in az_rows}, reverse=True),
        "elevations_absent_vs_az0_deg": [-15.0, -45.0, -75.0],
        "compute_seconds_total": round(secs, 1),
        "compute_hours_total": round(secs / 3600.0, 2),
        "note_ko": (
            "방위 태그는 `_az45` 하나뿐이다 — 원장에 다른 방위는 없다. 세 엔진 모두 15 m · "
            "자세 8,192 · 결측 0 이고, PathSolver 두 팔은 광선 40 억 발 · 깊이 1 이다. "
            "az0 팔에는 있는 −15 · −45 · −75 가 az45 에는 없으므로 그 앙각은 나란히 놓지 않는다."),
    }


# =========================================================================== #
#  ② 게이트 → ③ 채점
# =========================================================================== #
def build_cells() -> tuple[dict, dict]:
    cells, gate = {}, {}
    for a0, a45, name_en, name_ko in PAIRS:
        for el in ALL_ELS:
            f_tip = float(row(a0, el)["f_tip_hz"])
            E0, E45 = series(a0, el), series(a45, el)
            L0, L45 = levels_db(E0), levels_db(E45)
            d_ac = round(L45["ac_db"] - L0["ac_db"], 2)
            passed = (el in SCORE_ELS) and (d_ac >= GATE_DB)
            cell = {
                "engine_pair_ko": name_ko,
                "engine_pair_en": name_en,
                "el_deg": el,
                "f_tip_hz": f_tip,
                "arm_az0": a0,
                "arm_az45": a45,
                "npz_keys": [key(a0, el), key(a45, el)],
                "row_indices": [ROW_IDX[(a0, el)], ROW_IDX[(a45, el)]],
                "levels_az0_db": L0,
                "levels_az45_db": L45,
                "delta_ac_db": d_ac,
                "gate_threshold_db": GATE_DB,
                "scored": el in SCORE_ELS,
            }
            if el not in SCORE_ELS:
                cell["gate"] = "제외 — 나딧에서 방위는 죽은 축"
                cell["rhythm_share_pct_az0"] = None
                cell["rhythm_share_pct_az45"] = None
                cell["withheld_reason_ko"] = (
                    "el −90 은 시선이 [0,0,−1] 이라 방위가 기하에서 사라진다(f_tip = 0 이라 "
                    "«상한 위» 잣대 자체가 퇴화한다). 사전 등록대로 채점에서 뺐다.")
            elif not passed:
                cell["gate"] = "불통과 — az45 에코 부재"
                cell["rhythm_share_pct_az0"] = None
                cell["rhythm_share_pct_az45"] = None
                cell["above_f_tip_pct_az0"] = None
                cell["above_f_tip_pct_az45"] = None
                cell["beat_hz_az0"] = None
                cell["beat_hz_az45"] = None
                cell["withheld_reason_ko"] = (
                    f"az45 팔의 DC 제거 AC 가 az0 대비 {d_ac:+.2f} dB 로 사전 등록 문턱 "
                    f"{GATE_DB:.0f} dB 밖이다. 몫(비율)은 분모가 사라진 자리에서 아무 뜻이 없으므로 "
                    "**계산은 했으나 값을 싣지 않는다** — 이 칸의 리듬 몫은 인용 불가다.")
            else:
                cell["gate"] = "통과"
                for tag, E in (("az0", E0), ("az45", E45)):
                    rh, af, apw = rhythm_and_above(E, f_tip)
                    bt, bh = beat(E, f_tip)
                    cell[f"rhythm_share_pct_{tag}"] = round(rh, 1)
                    cell[f"above_f_tip_pct_{tag}"] = round(af, 2)
                    cell[f"above_f_tip_power_db_{tag}"] = round(apw, 2)
                    cell[f"beat_hz_{tag}"] = bt
                    cell[f"beat_over_floor_db_{tag}"] = bh
                    cell[f"ledger_beat_hz_{tag}"] = row(a0 if tag == "az0" else a45, el)["track"]["beat_hz"]
                cell["d_rhythm_pp"] = round(cell["rhythm_share_pct_az45"]
                                            - cell["rhythm_share_pct_az0"], 1)
                cell["d_beat_hz"] = round(cell["beat_hz_az45"] - cell["beat_hz_az0"], 2)
            # 상한 위 절대 전력은 «레벨» 이라 게이트와 무관하게 싣는다(비율이 아니다).
            for tag, E in (("az0", E0), ("az45", E45)):
                cell.setdefault(f"above_f_tip_power_db_{tag}",
                                round(rhythm_and_above(E, f_tip)[2], 2) if f_tip > 0 else None)
            cells[f"{a0}|el{el:+.0f}"] = cell
            gate[f"{name_ko}|el{el:+.0f}"] = cell["gate"]
    return cells, gate


# =========================================================================== #
#  그림
# =========================================================================== #
plt.rcParams.update({
    "font.size": 12, "axes.titlesize": 13, "axes.labelsize": 12,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 11,
    "figure.facecolor": "white", "savefig.facecolor": "white",
})
C0, C45 = "#1f77b4", "#d62728"


def fig_gate(cells: dict) -> str:
    """게이트 판 — 레벨은 «크기» 라 막대가 아니라 **점과 띠**로 그린다.

    ⚠막대는 0 dB 에서 자라 나오는 것처럼 읽히는데, dB 축에는 0 이 없다.
    """
    fig, axs = plt.subplots(1, 3, figsize=(16.5, 5.6), sharey=True)
    x = np.arange(len(ALL_ELS), dtype=float)
    for ax, (a0, _a45, name_en, _ko) in zip(axs, PAIRS):
        c = [cells[f"{a0}|el{el:+.0f}"] for el in ALL_ELS]
        v0 = np.array([k["levels_az0_db"]["ac_db"] for k in c])
        v45 = np.array([k["levels_az45_db"]["ac_db"] for k in c])
        ax.fill_between(x, v0, v0 + GATE_DB, color="#9ad19a", alpha=0.30,
                        label="admissible band (az0 to az0 minus 20 dB)")
        ax.plot(x, v0 + GATE_DB, color="#217a21", ls="--", lw=1.8)
        ax.plot(x, v0, "-o", color=C0, ms=10, lw=2.0, label="azimuth 0 deg")
        ax.plot(x, v45, "-s", color=C45, ms=10, lw=2.0, label="azimuth 45 deg")
        for i, k in enumerate(c):
            ok = k["gate"].startswith("통과")
            dead = not k["scored"]
            col = "#217a21" if ok else ("#777777" if dead else "#c00000")
            ax.annotate(f"{k['delta_ac_db']:+.1f} dB",
                        (i, max(v0[i], v45[i]) + 7.0), ha="center", fontsize=11.5,
                        color=col, fontweight="bold")
            if not ok:
                ax.annotate("dead axis" if dead else "GATED",
                            (i, min(v0[i], v45[i]) - 11.0), ha="center", fontsize=11,
                            color=col, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{e:+.0f}" for e in ALL_ELS])
        ax.set_xlim(-0.45, len(ALL_ELS) - 0.55)
        ax.set_xlabel("Elevation [deg]")
        ax.set_title(name_en)
        ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel("DC-removed AC level [dB]")
    axs[0].set_ylim(-168, -28)
    # ⚠범례는 **점이 없는 판**에 둔다 — 가운데 판 왼쪽 아래에는 −145 dB 짜리 az45 점이 산다.
    axs[0].legend(loc="lower center", framealpha=0.95, fontsize=10.5)
    fig.suptitle("R12 absolute-level gate: does the 45 deg arm have an echo at all?",
                 fontsize=15, y=0.985)
    p = os.path.join(FIG, "r12_gate_levels.png")
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_rhythm(cells: dict, neutral: dict) -> str:
    fig, axs = plt.subplots(1, 3, figsize=(16.5, 5.4), sharey=True)
    x = np.arange(len(SCORE_ELS))
    for ax, (a0, _a45, name_en, _ko) in zip(axs, PAIRS):
        c = [cells[f"{a0}|el{el:+.0f}"] for el in SCORE_ELS]
        for i, k in enumerate(c):
            if k["gate"].startswith("통과"):
                ax.bar(i - 0.19, k["rhythm_share_pct_az0"], 0.36, color=C0)
                ax.bar(i + 0.19, k["rhythm_share_pct_az45"], 0.36, color=C45)
                ax.annotate(f"{k['rhythm_share_pct_az0']:.0f}", (i - 0.19,
                            k["rhythm_share_pct_az0"] + 2), ha="center", fontsize=10.5)
                ax.annotate(f"{k['rhythm_share_pct_az45']:.0f}", (i + 0.19,
                            k["rhythm_share_pct_az45"] + 2), ha="center", fontsize=10.5)
            else:
                ax.add_patch(plt.Rectangle((i - 0.42, 0), 0.84, 100.0, facecolor="#eeeeee",
                                           edgecolor="#c00000", hatch="//", lw=1.6))
                ax.annotate("GATED\nno echo at 45 deg\nratio withheld", (i, 50),
                            ha="center", va="center", fontsize=11, color="#c00000",
                            fontweight="bold")
        nl = neutral[f"el{SCORE_ELS[0]:+.0f}"]["mean_pct"]
        ax.axhline(nl, color="#444444", ls=":", lw=1.8)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{e:+.0f}" for e in SCORE_ELS])
        ax.set_xlabel("Elevation [deg]")
        ax.set_title(name_en)
        ax.set_ylim(0, 108)
        ax.grid(axis="y", alpha=0.3)
    axs[0].set_ylabel("Rhythm share above f_tip [%]")
    h = [plt.Rectangle((0, 0), 1, 1, color=C0), plt.Rectangle((0, 0), 1, 1, color=C45),
         plt.Line2D([0], [0], color="#444444", ls=":", lw=1.8)]
    axs[2].legend(h, ["azimuth 0 deg", "azimuth 45 deg",
                      f"white noise {neutral['el+0']['mean_pct']:.1f} %"],
                  loc="upper right", framealpha=0.95, fontsize=10.5)
    fig.suptitle("R12 rhythm share, admissible cells only (gate passed)", fontsize=15, y=0.99)
    p = os.path.join(FIG, "r12_rhythm_admissible.png")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_el0(cells: dict) -> tuple[str, dict]:
    """el 0 STFT 네 판 — «몫만 보면 뒤집히는 자리» 를 눈으로 보여 준다."""
    periods = auto_periods(PRF, FFL)
    f_tip = float(row("ours_r15_n8192", 0.0)["f_tip_hz"])
    t0, tspan = 0.020, 0.060
    n0, nz = int(round(t0 * PRF)), int(round(tspan * PRF))
    panels = [
        ("ours_r15_n8192", "Our kernel, azimuth 0"),
        ("ours_r15_n8192_az45", "Our kernel, azimuth 45"),
        ("sionna_p4000000000_r15_n8192_d1", "PathSolver physics off, azimuth 0"),
        ("sionna_p4000000000_r15_n8192_az45_d1", "PathSolver physics off, azimuth 45"),
    ]
    gated = {"sionna_p4000000000_r15_n8192_az45_d1"}
    fig, axs = plt.subplots(2, 2, figsize=(14.4, 9.0), sharex=True, sharey=True)
    setting = {}
    m = None
    for ax, (arm, lab) in zip(axs.ravel(), panels):
        E = series(arm, 0.0)[n0:n0 + nz]
        f, t, S, nper = flash_spec(E, PRF, FFL, periods=periods)
        # ⭐그리는 도플러 범위 밖을 미리 자른다 — md_mapstyle 의 «패딩을 키우면 그리는 범위를
        #   좁혀라» 규약이고, gouraud 음영이 폴리곤을 칸마다 찍어 안 자르면 렌더가 분 단위다.
        band = np.abs(f) <= 2.0 * f_tip
        f, S = f[band], S[band]
        m = draw(ax, t, f, S, f_tip)
        ac = levels_db(series(arm, 0.0))["ac_db"]
        ax.set_title(f"{lab}   (AC {ac:.1f} dB)", fontsize=12.5)
        if arm in gated:
            ax.annotate("GATED  ratio withheld", (0.5, 0.06), xycoords="axes fraction",
                        ha="center", fontsize=13, color="white", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.3", fc="#c00000", ec="none"))
        setting = {"stft_periods_of_blade_cycle": round(float(periods), 3),
                   "nperseg_samples": int(nper), "hop_samples": 2, "zero_pad": 8,
                   "window": "hann", "t_start_s": t0, "t_span_s": tspan,
                   "prf_hz": PRF, "f_tip_hz": f_tip}
    for ax in axs[1]:
        ax.set_xlabel("Time [ms]")
    for ax in axs[:, 0]:
        ax.set_ylabel("Doppler [Hz]")
    cb = fig.colorbar(m, ax=axs, fraction=0.033, pad=0.02)
    cb.set_label("Per-panel normalised power [dB]")
    fig.suptitle("R12 at elevation 0: each panel self-normalised, so only the titles carry level",
                 fontsize=14.5, y=0.985)
    fig.text(0.5, 0.945, "Bottom right shows the cleanest blade flashes of the four, and it is "
                         "also 51 dB weaker than the panel to its left",
             ha="center", fontsize=12.5, color="#c00000")
    p = os.path.join(FIG, "r12_el0_stft.png")
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p, setting


# =========================================================================== #
#  자가검사
# =========================================================================== #
def selftests(cells: dict, neutral: dict, figs: list[str]) -> list[dict]:
    T = []

    def add(name, ok, detail):
        T.append({"test": name, "pass": bool(ok), "detail_ko": detail})

    # 1) 원장 완결성
    az_rows = [r for r in J["rows"] if float(r.get("az_deg", 0.0)) != 0.0]
    miss = sum(int(r["n_missing"]) for r in az_rows)
    keys_ok = all(key(r["engine"], float(r["el_deg"])) in Z.files for r in az_rows)
    add("az45 팔 12 계열 · 결측 0 · npz 키 존재",
        len(az_rows) == 12 and miss == 0 and keys_ok,
        f"행 {len(az_rows)} 개 · 결측 합 {miss} · npz 키 모두 존재 {keys_ok}")

    # 2) az0 짝이 네 앙각 모두 있다
    ok = all(key(a0, el) in Z.files for a0, _a, _n, _k in PAIRS for el in ALL_ELS)
    add("az0 짝 팔 12 계열 존재", ok, "세 엔진 × 네 앙각의 az0 키가 모두 npz 에 있다")

    # 3) 나딧 퇴화 — 방위는 죽은 축
    nad = {}
    for a0, a45, _n, ko in PAIRS:
        E0, E45 = series(a0, -90.0), series(a45, -90.0)
        rel = float(np.mean(np.abs(E45 - E0) ** 2) / np.mean(np.abs(E0) ** 2))
        nad[ko] = {"rel_power_diff": rel,
                   "rel_power_diff_db": round(float(10 * np.log10(max(rel, 1e-300))), 1),
                   "d_ac_db": round(levels_db(E45)["ac_db"] - levels_db(E0)["ac_db"], 3)}
    add("나딧(el −90)에서 방위는 죽은 축 — |ΔAC| ≤ 0.05 dB",
        all(abs(v["d_ac_db"]) <= 0.05 for v in nad.values()),
        json.dumps(nad, ensure_ascii=False))

    # 4) 백색 중립선이 규약값(≈13) 근처
    add("리듬 잣대의 백색 중립선 12.6 ± 1 %",
        all(abs(v["mean_pct"] - 12.6) < 1.0 for v in neutral.values()),
        json.dumps(neutral, ensure_ascii=False))

    # 5) 섞기 널 — 통과 칸에서 az45 리듬이 자기 널보다 높은가
    sh = {}
    for a0, a45, _n, ko in PAIRS:
        for el in SCORE_ELS:
            c = cells[f"{a0}|el{el:+.0f}"]
            if not c["gate"].startswith("통과"):
                continue
            mu, mx = shuffle_null(series(a45, el), c["f_tip_hz"])
            sh[f"{ko}|el{el:+.0f}"] = {"null_mean": mu, "null_max": mx,
                                       "measured": c["rhythm_share_pct_az45"],
                                       "above_null": c["rhythm_share_pct_az45"] > mx}
    add("섞기 널 — 통과 칸 az45 리듬 몫이 널 최댓값 위",
        all(v["above_null"] for v in sh.values()) if sh else False,
        json.dumps(sh, ensure_ascii=False))

    # 6) 박자 재계산이 원장 track.beat_hz 와 2 Hz 안
    bt = {}
    for a0, a45, _n, ko in PAIRS:
        for el in SCORE_ELS:
            c = cells[f"{a0}|el{el:+.0f}"]
            if not c["gate"].startswith("통과"):
                continue
            for tag, arm in (("az0", a0), ("az45", a45)):
                d = abs(c[f"beat_hz_{tag}"] - float(row(arm, el)["track"]["beat_hz"]))
                bt[f"{ko}|el{el:+.0f}|{tag}"] = round(d, 2)
    add("박자 재계산 ↔ 원장 track.beat_hz 차 ≤ 2 Hz",
        all(v <= 2.0 for v in bt.values()), json.dumps(bt, ensure_ascii=False))

    # 7) 기존 산출물 교차검증 — switch_grid.json 의 우리 커널 el −30 리듬 몫
    sg = json.load(open(SWITCH_J))["cells"]["Our kernel"]["rhythm_share_pct"]
    mine = cells["ours_r15_n8192|el-30.0".replace("-30.0", "-30")]["rhythm_share_pct_az0"]
    add("기존 원장 switch_grid.json 과 리듬 몫 재현 (≤1.0 %p)",
        abs(mine - float(sg)) <= 1.0,
        f"switch_grid {sg} % ↔ 이번 재계산 {mine} % (f_tip 규약 차 0.8 Hz 만큼만 다르다)")

    # 8) 게이트 규약이 실제로 강제되었나 — 불통과 칸에 수가 없어야 한다
    bad = [k for k, c in cells.items()
           if not c["gate"].startswith("통과") and c.get("rhythm_share_pct_az45") is not None]
    add("불통과·제외 칸에 리듬 몫이 실려 있지 않다", not bad, f"위반 칸 {bad}")

    # 9) 그림 파일이 실제로 생겼다
    fs = {os.path.basename(p): (os.path.exists(p) and os.path.getsize(p) > 20000) for p in figs}
    add("그림 3 장이 생성되고 20 kB 이상", all(fs.values()), json.dumps(fs, ensure_ascii=False))

    return T


# =========================================================================== #
#  본체
# =========================================================================== #
def main() -> int:
    os.makedirs(FIG, exist_ok=True)
    sv = survey()
    cells, gate = build_cells()
    neutral = {}
    for el in SCORE_ELS:
        mu, sd = white_neutral(float(row("ours_r15_n8192", el)["f_tip_hz"]))
        neutral[f"el{el:+.0f}"] = {"mean_pct": mu, "sd_pct": sd}

    figs = [fig_gate(cells), fig_rhythm(cells, neutral)]
    p3, stft_setting = fig_el0(cells)
    figs.append(p3)

    tests = selftests(cells, neutral, figs)

    passed = [k for k, v in gate.items() if v.startswith("통과")]
    failed = [k for k, v in gate.items() if v.startswith("불통과")]
    dead = [k for k, v in gate.items() if v.startswith("제외")]

    def c(a0, el):
        return cells[f"{a0}|el{el:+.0f}"]

    ours = "ours_r15_n8192"
    off = "sionna_p4000000000_r15_n8192_d1"
    on = "sionna_p4000000000_phys_r15_n8192_d1"

    out = {
        "_meta": {
            "generator": "benchmark/r12_azimuth_harvest.py",
            "design_doc": "docs/NEXT_EXPERIMENTS.md §② 3 행 · §3-1 R12",
            "question_ko": "「0° 에서 프로펠러가 익사한다」가 앙각의 성질인가 정면(방위 0°) 한정인가",
            "gpu_ko": "⛔GPU 를 쓰지 않았다. sionna.rt · mitsuba 를 임포트하지 않고 저장된 원장만 읽었다.",
            "inputs": ["outputs/elevation_sweep_md.json", "outputs/elevation_sweep_md.npz",
                       "outputs/switch_grid.json"],
            "prf_hz": PRF, "f_flash_hz": FFL,
            "range_m": 15.0,
            "range_note_ko": "az45 팔은 전부 15 m — 원거리장 경계 2D²/λ ≈ 14.08 m 의 밖이다. 10 m 옛 팔과 섞지 않았다.",
            "drone": META["drone"],
            "level_rule_ko": "⭐모든 레벨 비교는 정지성분(DC = 시계열 평균) 제거 후의 AC 다.",
            "rhythm_recipe_ko": ("P = |FFT((E − mean)·hanning)|² · above = |f_r| ≥ f_tip(el) · "
                                 "리듬 몫[%] = above 전력 중 f_flash 정수배 ±8 Hz 몫. "
                                 "백색 ≈ 12.6, 이상 로터 100."),
            "md_representation_ko": "마이크로도플러 그림은 STFT 만 썼다(md_mapstyle.flash_spec).",
            "stft_setting": stft_setting,
            "prereg_gate_ko": (f"az45 팔의 DC 제거 AC 가 같은 (엔진,앙각) az0 팔 대비 {GATE_DB:.0f} dB "
                               "밖이면 «az45 는 에코 부재» 로 판정하고 비율(리듬 몫)을 인정하지 않는다. "
                               "그 칸의 몫은 계산하더라도 JSON 에 싣지 않는다."),
            "prereg_changes_ko": "사전 등록 기준을 바꾸지 않았다. 설계서 문구를 그대로 강제했다.",
            "figures": figs,
        },

        "survey_az_arms": sv,

        "gate_table": gate,
        "gate_summary": {
            "passed": passed, "failed_no_echo": failed, "excluded_dead_axis": dead,
            "n_passed": len(passed), "n_failed": len(failed), "n_excluded": len(dead),
        },

        "cells": cells,
        "white_noise_neutral_pct": neutral,

        "headline_ko": [
            (f"⭐게이트가 먼저 답을 바꾼다 — 채점 대상 9 칸 중 **{len(passed)} 칸만 통과**하고 "
             f"**{len(failed)} 칸(PathSolver 두 팔의 el 0)** 은 az45 에서 에코가 사라져 "
             f"«비율 비교 불가» 다. 정면을 벗어나면 PathSolver 의 el 0 AC 가 물리 끔 "
             f"{c(off, 0.0)['delta_ac_db']:+.1f} dB · 물리 켬 {c(on, 0.0)['delta_ac_db']:+.1f} dB 로 무너진다."),
            (f"⭐그래서 「0° 익사」는 **방위 불변이 아니다.** 다만 az45 에서 익사가 «풀린다» 고 말할 수 "
             f"없다 — 그 자리에서는 익사시킬 에코 자체가 없어진다. 정확한 문장은 "
             f"«정면에서 동체 정반사가 지배할 때만 익사한다» 다."),
            (f"우리 커널은 방위에 둔감하다 — 통과한 세 앙각에서 리듬 몫이 "
             f"{c(ours, 0.0)['rhythm_share_pct_az0']:.0f}→{c(ours, 0.0)['rhythm_share_pct_az45']:.0f} % (el 0) · "
             f"{c(ours, -30.0)['rhythm_share_pct_az0']:.0f}→{c(ours, -30.0)['rhythm_share_pct_az45']:.0f} % (el −30) · "
             f"{c(ours, -60.0)['rhythm_share_pct_az0']:.0f}→{c(ours, -60.0)['rhythm_share_pct_az45']:.0f} % (el −60) 이고, "
             f"AC 레벨차도 {c(ours, 0.0)['delta_ac_db']:+.1f} ~ {c(ours, -60.0)['delta_ac_db']:+.1f} dB 안이다. "
             f"우리 커널은 el 0 에서 애초에 익사하지 않는다(az0 {c(ours, 0.0)['rhythm_share_pct_az0']:.0f} % ≫ 백색 12.6)."),
            (f"회절(물리 켬)이 리듬을 지우는 것은 **방위와 무관**하다 — el −30 에서 az0 "
             f"{c(on, -30.0)['rhythm_share_pct_az0']:.0f} % · az45 {c(on, -30.0)['rhythm_share_pct_az45']:.0f} % 로 "
             f"둘 다 백색 수준이다. 방위를 돌려도 안 살아난다."),
            (f"⚠별도 조사 항목 — 물리 켬 el −60 만 az45 에서 "
             f"{c(on, -60.0)['rhythm_share_pct_az0']:.0f} → {c(on, -60.0)['rhythm_share_pct_az45']:.0f} % 로 튄다. "
             f"같은 칸의 상한 위 몫이 {c(on, -60.0)['above_f_tip_pct_az0']:.0f} → "
             f"{c(on, -60.0)['above_f_tip_pct_az45']:.0f} % 로 함께 내려간 것이라 «잡음 바닥이 걷혀 "
             f"드러난 것» 과 «구조가 생긴 것» 이 아직 안 갈린다."),
            (f"나딧(el −90)에서 방위는 죽은 축이다 — 세 엔진 모두 |ΔAC| ≤ 0.01 dB. "
             f"앞으로 큐에서 나딧 × 방위 조합을 만들지 마라."),
        ],

        "verdict_ko": (
            "«0° 붕괴는 앙각의 성질» 도 «정면 한정» 도 둘 다 그대로는 못 쓴다. 사전 등록 게이트가 "
            "정면 밖 el 0 칸을 전부 «에코 부재» 로 잘라내기 때문이다. 남는 참인 문장은 두 개다 — "
            "① **방위 불변이 아니다**(정면을 45° 벗어나면 PathSolver 의 el 0 에코가 25~51 dB 사라진다) "
            "② **정면에서 동체 정반사가 지배할 때만 익사한다**(익사시키는 그 에코 자체가 정면의 산물이다). "
            "그리고 이 익사는 **엔진의 성질**이다 — 우리 커널은 같은 기하에서 두 방위 모두 리듬을 지킨다."),

        "open_items_ko": [
            ("⚠PathSolver 의 el 0 · az45 칸은 이번 판으로는 못 읽는다. 읽으려면 **절대 기준이 붙은 "
             "판**이 필요하다 — 같은 팔을 잡음 전용 팔(표적 없음)과 나란히 돌려서 «−145 dB 가 "
             "MC 바닥인가 진짜 약한 에코인가» 를 가르는 실험. GPU 가 비면 그때."),
            ("⚠물리 켬 el −60 az45 의 리듬 상승은 R13(스위치 완전요인)의 «바닥 vs 빗살 선» 분해와 "
             "같은 잣대로 다시 읽어야 한다. 지금 잣대로는 원인 귀속이 안 된다."),
            ("방위 축은 45° 한 점뿐이다. 쿼드콥터는 45° 가 «팔 사이» 라 대칭을 가장 크게 깨는 각이지만, "
             "22.5° 같은 중간 각이 없어 방위 의존이 단조인지 주기적인지 모른다."),
        ],

        "ledger_meta_patch_proposal": {
            "target_file": "outputs/elevation_sweep_md.json",
            "path": "_meta.nadir_azimuth_dead_axis_ko",
            "value_ko": ("⭐el −90 에서 시선은 los(az,−90) = [0,0,−1] 이라 방위가 기하에서 사라진다. "
                         "실측으로 세 엔진 모두 az0 ↔ az45 의 AC 레벨차가 |ΔAC| ≤ 0.01 dB 다. "
                         "앞으로 큐에 나딧 × 방위 조합을 넣지 마라 — 계산이 낭비다."),
            "applied": False,
            "why_not_applied_ko": "이 라운드는 기존 파일 수정 금지 규약이라 제안만 남긴다.",
            "evidence": {t["test"]: t["detail_ko"] for t in tests if "나딧" in t["test"]},
        },

        "corrections": [],       # main 끝에서 채운다
        "selftest": tests,
        "selftest_all_pass": all(t["pass"] for t in tests),
    }

    # ── 정정 항목 ────────────────────────────────────────────────────────── #
    out["corrections"] = [
        {
            "where": "8/18 팀미팅 덱 · 슬라이드 «The drowned blades» "
                     "(/workspace/team_meeting/teammeeting_0818/make_0818_v14.py:554 부근)",
            "old_ko": "«Same engine, same rays, and the same 8,192 spinning poses, all at 0 degrees» "
                      "— 판을 «0 도» 로만 적어 앙각만 밝히고 방위를 안 밝힌다.",
            "new_ko": "«all at 0 degrees elevation, nose-on (azimuth 0)» 로 방위를 함께 못 박는다. "
                      "이 실험이 방위 축을 실제로 읽었고, 방위가 결과를 바꾸기 때문이다.",
            "evidence": f"cells.{off}|el+0.delta_ac_db = {c(off, 0.0)['delta_ac_db']} dB",
        },
        {
            "where": "8/18 덱 · 같은 슬라이드의 결론띠",
            "old_ko": "«Alone the propellers beat at NN percent, but their echo sits NN dB below "
                      "the body echo and drowns» — 익사를 앙각(0°)의 성질처럼 읽히게 둔다.",
            "new_ko": "결론띠 뒤에 한 줄을 덧붙인다 — «and that body echo is itself nose-on: "
                      "turning 45 degrees off the nose drops it by 25 to 51 dB». 즉 익사는 "
                      "**정면에서 동체 정반사가 지배할 때만** 일어난다. ⛔«방위를 돌리면 "
                      "익사가 풀린다» 로는 쓰지 마라 — 그 자리에서는 에코 자체가 사라져 "
                      "사전 등록 게이트에 걸린다(리듬 몫 인용 불가).",
            "evidence": (f"gate_summary.failed_no_echo = {failed} · "
                         f"cells.{on}|el+0.delta_ac_db = {c(on, 0.0)['delta_ac_db']} dB"),
        },
        {
            "where": "docs/RESUME.md §1 표 1 행 «0° 붕괴 기전 해부»",
            "old_ko": "«0° 에서 박자가 사라지는 것은 소멸이 아니라 익사다»",
            "new_ko": "«**정면(방위 0°) 의** 0° 에서 박자가 사라지는 것은 소멸이 아니라 익사다. "
                      "그 익사를 만드는 동체 에코는 정면의 산물이라 방위를 45° 돌리면 "
                      "25~51 dB 사라진다 — 방위 불변이 아니다.»",
            "evidence": "outputs/r12_azimuth_harvest.json · gate_table",
        },
        {
            "where": "docs/NEXT_EXPERIMENTS.md §① TL;DR 3 행 · §3-1 R12 절",
            "old_ko": "«21 GPU-h 어치가 계산돼 있는데»",
            "new_ko": f"az45 팔 12 계열의 실측 합계는 **{sv['compute_hours_total']:.1f} 워커-시간**이다"
                      f"(원장 `seconds` 열 합 {sv['compute_seconds_total']:.0f} s). 21 은 과대 계상이다.",
            "evidence": "survey_az_arms.compute_seconds_total",
        },
        {
            "where": "docs/NEXT_EXPERIMENTS.md §3-1 R12 절 «두 계열 차 1.96e-17»",
            "old_ko": "el −90 에서 az0 과 az45 두 계열의 차가 1.96e-17",
            "new_ko": ("계열 차의 크기는 엔진마다 다르다. **차 전력 / 원 전력**으로 재면 우리 커널 "
                       "−299 dB · PathSolver 물리 끔 −316 dB(둘 다 부동소수 반올림 수준) 인데 "
                       "**물리 켬만 −54 dB** 다 — 회절 항이 광선을 확률적으로 표집해 두 팔의 "
                       "잡음 실현이 다르기 때문이다. ⭐그래도 **레벨로는 셋 다 |ΔAC| ≤ 0.01 dB** 라 "
                       "결론(나딧에서 방위는 죽은 축)은 그대로다. 1.96e-17 은 한 팔의 수이지 "
                       "세 팔의 수가 아니고, 진폭 눈금이라 전력 눈금과 섞어 인용하면 안 된다."),
            "evidence": "selftest[2].detail_ko",
        },
    ]

    with open(OUT_J, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ── 콘솔 요약 ────────────────────────────────────────────────────────── #
    print(f"■ az45 팔 전수: {sv['n_az_tagged_series']} 계열 · "
          f"{sv['compute_hours_total']:.2f} 워커-시간 · 결측 0")
    print("■ 게이트")
    for k, v in gate.items():
        print(f"   {k:34s} {v}")
    print("■ 통과 칸 리듬 몫 (az0 → az45)")
    for a0, _a45, _en, ko in PAIRS:
        for el in SCORE_ELS:
            k = c(a0, el)
            if k["gate"].startswith("통과"):
                print(f"   {ko:16s} el{el:+.0f}  "
                      f"{k['rhythm_share_pct_az0']:5.1f} → {k['rhythm_share_pct_az45']:5.1f} %  "
                      f"(Δ{k['d_rhythm_pp']:+.1f} %p) · 박자 {k['beat_hz_az0']:.1f} → "
                      f"{k['beat_hz_az45']:.1f} Hz · 상한 위 {k['above_f_tip_pct_az0']:.1f} → "
                      f"{k['above_f_tip_pct_az45']:.1f} %")
    print("■ 자가검사")
    for t in tests:
        print(f"   [{'PASS' if t['pass'] else 'FAIL'}] {t['test']}")
    print(f"■ 산출 {OUT_J}")
    for p in figs:
        print(f"■ 그림 {p}")
    return 0 if out["selftest_all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
