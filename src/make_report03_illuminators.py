# -*- coding: utf-8 -*-
"""make_report03_illuminators.py — `report03_illuminators.ipynb` 생성기

리포트 03 **조명원 — 세 파형이 무는 대가를 dB 원장으로 닫았다**
한 일: *패시브가 빌려 쓰는 상시 기준신호를 세 표준의 자원격자에서 세우고, 조명원 선택이 무는
대가를 dB 원장으로 닫았다.* 원장 항목은 전부 두 양의 비라서 표적 σ 가 상쇄된다.

이 편이 먹이는 논문 절: **III-B. Illuminators** (`docs/PAPER_SPEC.md` §3).

이 파일이 하는 일 (순서대로)
---------------------------------------------------------------------------
1. `outputs/report03_illuminators.json` 을 **계산해서 쓴다** — 상위 JSON 에 스칼라로
   존재하지 않는 파생량(기준신호 에너지, λ² 격차, 점유 대가)만. 항목마다 `from` 에
   어느 상위 JSON/코드에서 왔는지 박는다.
2. 그림 7장을 **게재 규격**으로 그린다(`docs/PAPER_SPEC.md` §4.3) — 벡터 PDF + 400 dpi PNG,
   8 pt 하한, 색+해치/마커 이중부호화. 저장은 `src/paper_kit.py:save_figure` 가 검사까지 한다.
3. `src/report_style.py`(서술 규약) + `src/paper_kit.py`(논문 참고자료 규격)로 노트북을
   조립한다 — 논문 대응 블록은 여는 블록 안에, 방법 문단·방어선·인용은 부록 셀 하나에.

⚠ 노트북은 **생성물**이다. `report03_illuminators.ipynb` 를 직접 고치지 말고 이 파일을 고쳐라.
⚠ 본문 숫자는 **전부** `num()` 을 통과한다 — JSON 과 어긋나면 빌드가 멈춘다. 손으로 친 숫자 0개.
⚠ 이 파일은 다른 편의 빌더·`report_style.py`·`paper_kit.py`·`rcs_sbr.py` 를 건드리지 않는다.
   그림 4장을 `src/viz_report2.py` 에서 빌려 쓰던 것을 끊고 **이 편이 직접 그린다** — 그
   4장은 다른 편이 인용하지 않는다(`report02` 는 `report2_{gallery,occlusion,rcs_polar}` 만 쓴다).

실행:  cd /home/yunjung/workspace/sionna2 && \
       PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report03_illuminators.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#  BLAS 스레드 상한 — numpy import 전에 잡아야 먹는다(같은 박스에서 다른 작업이 동시에 돈다).
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "4")

import numpy as np                                                    # noqa: E402

from report_style import (assert_fig_text, build_notebook, code,       # noqa: E402
                          fetch, header, md, next_steps, num, table)
from paper_kit import (PALETTE, attach, cite, cite_ref, defence,       # noqa: E402
                       figure_md, methods, paper_appendix, paper_map,
                       paper_style, save_figure, series_style)

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
FIG = os.path.join(ROOT, "outputs", "figures")
NB = os.path.join(ROOT, "report03_illuminators.ipynb")

#: 이 편이 인용하는 상위 JSON — 전부 다른 실험이 남긴 것이다.
J_WAVE = "outputs/report2_waveform_rcs.json"     # 파형 제원 + Sionna 교차대조
J_AMB = "outputs/verify_ambiguity.json"          # 모호함수(검출기와 동일 커널)
J_FIX = "outputs/report4_fixups.json"            # 링크버짓 규약 상수(듀티·√(B/fs)·CPI)
J_MTX = "outputs/report5_results.json"           # 점유×EIRP 검출 몬테카를로
J_LED = "outputs/report03_illuminators.json"     # ← 이 파일이 만든다

C0 = 299_792_458.0
STDS = ("wifi", "lte", "nr")
SHORT = {"wifi": "WiFi", "lte": "LTE", "nr": "5G NR"}

#: 게재 규격 계열 순서 — 세 조명원이 이 논문의 기본형이라 팔레트 앞 세 색을 그대로 쓴다
#  (`paper_kit.PALETTE` 는 앞 3색의 흑백 명도차가 최대가 되도록 세워져 있다).
PIDX = {"wifi": 0, "lte": 1, "nr": 2}
#: 막대·채움의 **흑백 이중부호화** — 색을 잃어도 표준이 구분된다.
PHATCH = {"wifi": "", "lte": "///", "nr": "xxx"}
#: IEEE 2단 조판 폭. 이 편의 그림은 전부 2단 통폭이다(패널이 2~6개라서).
W2 = 7.16
#: 논문 캡션(완결 문장)과 노트북 캡션(질문)을 한 곳에서 관리한다.
REPORT_KEY = "report03_illuminators"


# =========================================================================== #
#  1) 파생 원장 — outputs/report03_illuminators.json
# =========================================================================== #
def _pd50_bracket(rows, occ, thr=0.5):
    """Pd = thr 교차점을 **격자로 감싼다** — (lo, hi] 구간과 그 안의 선형보간값.

    ⚠ 이 값은 EIRP 격자에서 **읽은** 수다. 격자 눈금이 유효숫자를 정한다(§2 의 '닫는 방식' 열).
    반환: dict(lo, hi, pd_lo, pd_hi, interp) — lo 는 Pd<thr 인 마지막 격자점, hi 는 첫 Pd≥thr.
    """
    rr = sorted((r for r in rows if r["occ"] == occ), key=lambda r: r["eirp_dbm"])
    i = next((n for n, r in enumerate(rr) if r["pd"] >= thr), None)
    if i is None:
        raise RuntimeError(
            f"점유 {occ} 가 EIRP 격자 안에서 Pd≥{thr} 를 못 넘는다 — "
            f"{J_MTX}:A_occupancy 를 더 넓은 EIRP 로 다시 돌려야 원장을 쓸 수 있다.")
    if i == 0:
        raise RuntimeError(
            f"점유 {occ} 가 격자 첫 점에서 이미 Pd≥{thr} 다 — 교차점이 격자 밖이라 "
            f"구간을 세울 수 없다. {J_MTX}:A_occupancy 의 EIRP 하한을 낮춰라.")
    lo, hi = rr[i - 1], rr[i]
    span = float(hi["pd"] - lo["pd"])
    frac = (thr - float(lo["pd"])) / span if span > 0 else 0.5
    return dict(lo=float(lo["eirp_dbm"]), hi=float(hi["eirp_dbm"]),
                pd_lo=float(lo["pd"]), pd_hi=float(hi["pd"]),
                interp=float(lo["eirp_dbm"] + frac * (hi["eirp_dbm"] - lo["eirp_dbm"])))


def build_ledger(path: str = J_LED) -> dict:
    """상위 JSON 에 **스칼라로 없는** 파생량만 계산해 기록한다.

    원칙: 상위 JSON 에 그대로 있는 값은 여기 복사하지 않는다(리포트가 원본을 직접 인용한다).
          여기 들어오는 것은 ① 격자를 다시 만들어야 나오는 에너지, ② 두 값의 비, ③ 표 스캔뿐.
    """
    from waveforms import all_waveforms                 # CPU 수 초 — 격자를 다시 세운다

    grids: dict[str, dict] = {}
    for occ in ("G1", "G3"):
        wfs = all_waveforms(occ)
        g = {}
        for k in STDS:
            wf = wfs[k]
            e_ref = float(np.sum(np.abs(wf.ref) ** 2))
            e_tx = float(np.sum(np.abs(wf.tx) ** 2))
            g[k] = dict(
                name=wf.name, ref_name=wf.ref_name,
                carrier_hz=float(wf.carrier_hz), bw_hz=float(wf.bw_hz),
                ref_bw_hz=float(wf.ref_bw_hz),
                drb_m=float(wf.range_resolution_m),
                prf_hz=float(wf.pilot_rate_hz),
                occupancy_frac=float(wf.occupancy_frac),
                e_ref_db=float(10 * np.log10(e_ref + 1e-30)),
                e_tx_db=float(10 * np.log10(e_tx + 1e-30)),
                e_ref_over_tx_db=float(10 * np.log10(e_ref / e_tx)))
        grids[occ] = g

    # ── λ² — EIRP 와 수신 이득이 고정일 때 반송파가 무는 대가 -------------------
    car = {k: grids["G1"][k]["carrier_hz"] for k in STDS}
    lam2 = {f"lte_to_{k}_db": float(20 * np.log10(car["lte"] / car[k]))
            for k in ("nr", "wifi")}

    # ── 기준신호 에너지 격차(상시 G1 → 풀로드 G3) ------------------------------
    e_gap = {k: float(grids["G3"][k]["e_ref_db"] - grids["G1"][k]["e_ref_db"]) for k in STDS}

    # ── 상시 체제에서 LTE 대비 5G 가 무는 두 배수 ------------------------------
    #    (§1.1 이 인용한다 — 본문에서 손으로 나누지 않도록 여기서 낸다)
    ref = fetch((J_WAVE, "reference.G1"))
    ratios = dict(
        drb_nr_over_lte=float(ref["nr"]["dR_m"] / ref["lte"]["dR_m"]),
        vmax_lte_over_nr=float(ref["lte"]["vmax_ms"] / ref["nr"]["vmax_ms"]),
        defn="상시 기준신호(LTE CRS · 5G SSB) 기준의 거리눈금 비와 무모호 속도 비",
        from_=f"{J_WAVE}:reference.G1")

    # ── 점유 대가 — 같은 표적·같은 기하에서 Pd 0.5 를 넘기는 EIRP 격차 ---------
    rows = fetch((J_MTX, "A_occupancy.rows"))
    eirps = fetch((J_MTX, "A_occupancy.eirps"))
    b1, b3 = _pd50_bracket(rows, "G1"), _pd50_bracket(rows, "G3")
    t1, t3 = b1["hi"], b3["hi"]
    step = float(min(np.diff(sorted(set(float(e) for e in eirps)))))
    #  이 격차 안에 무엇이 섞여 있나 — 리포트가 "18 dB 는 순수 점유가 아니다"를 말할 수 있게.
    r1 = next(r for r in rows if r["occ"] == "G1")
    r3 = next(r for r in rows if r["occ"] == "G3")

    # ── 모호함수가 검출기 출력과 얼마나 같은가 (6개 중 최악) --------------------
    dv = fetch((J_AMB, "meta.detector_validation"))
    af_err = max(float(r["max_err_db_above_m45"]) for r in dv)

    led = dict(
        _meta=dict(
            purpose="리포트 03 의 파생 원장 — 상위 JSON 에 스칼라로 없는 값만. 손으로 적은 값 0개.",
            made_by="src/make_report03_illuminators.py:build_ledger",
            paper_section="III-B. Illuminators",
            upstream=[J_WAVE, J_AMB, J_FIX, J_MTX],
            note="모든 항목은 두 양의 비이거나 격자에서 잰 에너지다 — 표적 σ 가 상쇄된다.",
            closed_form_note="`closed_form: true` 인 항목은 자원격자·반송파·관측시간에서 닫히므로 "
                             "유효숫자가 계산 정밀도까지 간다. `false` 인 항목은 몬테카를로 "
                             "격자에서 읽은 값이고, 그 옆의 구간·격자 눈금이 유효숫자를 정한다."),
        grids=grids,
        lambda2=dict(
            **lam2, closed_form=True,
            defn="20log10(lam/lam_ref) — EIRP 고정 · 수신 안테나 이득 고정 전제. "
                 "코드: src/freespace_link.py:371 (snr_rd_terms_db 의 lambda2 항)",
            span_db=float(min(lam2.values()))),
        ref_energy_gap_G1_to_G3_db=dict(
            **e_gap, closed_form=True,
            defn="10log10(E_ref(G3)/E_ref(G1)) — 상관에 쓸 수 있는 기준신호 에너지만",
            from_="src/waveforms.py 격자 재생성 (all_waveforms)"),
        ratios=ratios,
        occupancy_cost=dict(
            value_db=float(t1 - t3), pd_threshold=0.5,
            eirp_G1_dbm=float(t1), eirp_G3_dbm=float(t3), eirp_grid_step_db=step,
            #  격자 읽기의 유효숫자 — 교차점은 (lo, hi] 안에 있으므로 격차도 구간이다.
            bracket_lo_db=float(b1["lo"] - b3["hi"]), bracket_hi_db=float(b1["hi"] - b3["lo"]),
            interp_db=float(b1["interp"] - b3["interp"]),
            bracket_G1_dbm=[b1["lo"], b1["hi"]], bracket_G3_dbm=[b3["lo"], b3["hi"]],
            pd_G1=[b1["pd_lo"], b1["pd_hi"]], pd_G3=[b3["pd_lo"], b3["pd_hi"]],
            closed_form=False,
            ref_bw_G1_mhz=float(r1["ref_bw_mhz"]), ref_bw_G3_mhz=float(r3["ref_bw_mhz"]),
            occ_frac_G1=float(r1["occupancy_frac"]), occ_frac_G3=float(r3["occupancy_frac"]),
            n_trials=int(r1["N"]), drone=str(r1["drone"]), scen=str(r1["scen"]),
            defn="5G 100 MHz, 상시(G1=SSB) 가 풀로드(G3=NR-PRS) 와 같은 Pd 를 내려면 "
                 "EIRP 를 얼마나 더 써야 하나. 같은 표적·같은 기하의 차라서 σ 가 상쇄된다. "
                 "⚠ 이 격차에는 기준신호 대역(7.2→98.28 MHz)과 점유율이 함께 들어 있다 — "
                 "'점유만'의 값이 아니다.",
            precision="검출 몬테카를로의 EIRP 격자에서 읽은 값이다 — value_db 는 격자점 차이이고 "
                      "참값은 [bracket_lo_db, bracket_hi_db] 안에 있다. interp_db 는 그 구간 안의 "
                      "Pd 선형보간. 시행 n_trials 회가 각 격자점의 Pd 를 정한다.",
            from_=f"{J_MTX}:A_occupancy.rows"),
        detector_af_max_err_db=dict(
            value=af_err, n_cases=len(dv),
            defn="해석 모호함수 |chi| 와 검출기 거리도플러 출력의 최대 편차(−45 dB 이상 셀)",
            from_=f"{J_AMB}:meta.detector_validation"),
    )
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(led, f, ensure_ascii=False, indent=1)
    print(f"[ledger] {path}")
    return led


# =========================================================================== #
#  2) 그림 — 게재 규격(PAPER_SPEC §4.3)
#     · `paper_style()` 안에서만 그린다(글자·색·선 규격이 그 블록에서만 걸린다)
#     · `save_figure()` 가 벡터 PDF + 400 dpi PNG 를 함께 쓰고 저장 직전에 검사한다
#     · 계열은 **색 + 해치/마커** 이중부호화 — 흑백 인쇄에서 색은 사라진다
# =========================================================================== #
def _pc(k: str) -> str:
    """표준 k 의 계열 색(팔레트 앞 세 색)."""
    return PALETTE[PIDX[k]]


def _emit(fig, stem: str, caption: str, title: str) -> dict:
    """게재 규격으로 저장한다 — 2단 통폭 배치를 전제로 축소 후 글자까지 판정한다."""
    out = save_figure(fig, f"outputs/figures/{stem}", dpi=400, caption=caption,
                      title=title, placed_width_in=W2, strict=True, close=True)
    print(f"[fig] {out['png']}  (min {out['audit']['min_font_pt']} pt · "
          f"vector {out['pdf']})")
    return out


def fig_grid():
    """그림 1 — 유휴 셀(G1)과 풀로드(G3) 의 자원격자에서 '늘 켜진 것'만 골라낸다.

    3단계 지도로 그린다: 빈 RE · 내용을 모르는 RE(데이터) · **상관에 쓸 수 있는 기준신호**.
    세 단계의 흑백 명도가 크게 벌어져 있어 색을 잃어도 읽힌다.
    """
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch
    from waveforms import CH, REF_CH, all_waveforms

    known = np.array(sorted(CH[c] for c in REF_CH))
    labs = {"wifi": "WiFi 802.11ac", "lte": "LTE Rel-9", "nr": "5G NR Rel-16"}

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, axes = st.figure(2, 3, height=3.9, sharex=False)
        for r, mode in enumerate(("G1", "G3")):
            wfs = all_waveforms(mode)
            for c, k in enumerate(STDS):
                wf = wfs[k]
                lv = np.zeros(wf.labels.shape, np.int8)          # 0 = empty
                lv[wf.labels != CH["EMPTY"]] = 1                 # 1 = unknown content
                lv[np.isin(wf.labels, known)] = 2                # 2 = correlatable reference
                cmap = ListedColormap(["#FFFFFF", "#C8CDD2", _pc(k)])
                ax = axes[r, c]
                ax.imshow(lv.T, aspect="auto", origin="lower", cmap=cmap,
                          norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5], 3),
                          interpolation="nearest",
                          extent=(0, lv.shape[0], -wf.fft / 2, wf.fft / 2))
                ax.set_title(f"{labs[k]} {mode} - {wf.ref_name}", fontsize=8.5)
                ax.tick_params(labelsize=8.5)
                if r == 1:
                    ax.set_xlabel("OFDM symbol", fontsize=8.5)
                if c == 0:
                    ax.set_ylabel(("G1 idle cell" if mode == "G1" else "G3 full load")
                                  + "\nsubcarrier", fontsize=8.5)
        hs = [Patch(facecolor="#FFFFFF", edgecolor="#666", label="empty RE"),
              Patch(facecolor="#C8CDD2", edgecolor="#666", label="occupied, unknown")]
        hs += [Patch(facecolor=_pc(k), edgecolor="#666",
                     label=f"{SHORT[k]} reference") for k in STDS]
        fig.legend(handles=hs, loc="lower center", ncol=5, fontsize=8.5, frameon=False,
                   bbox_to_anchor=(0.5, -0.055))
    return _emit(
        fig, "report03_f1_grid",
        "Resource grids of the three illuminators in the idle-cell regime (G1, top) and under "
        "full load (G3, bottom). Only the always-on reference signal carries content the passive "
        "receiver knows in advance and can correlate against; data resource elements add energy "
        "but no correlation template, which is why full load buys no range resolution for WiFi "
        "and LTE.",
        "Illuminator resource grids")


def fig_reference(REF, led):
    """그림 2 — 거리 눈금을 정하는 것은 채널 대역이 아니라 기준신호 대역이다."""
    g1, g2 = REF["G1"], REF["G3"]
    labs = ["WiFi\nVHT-LTF", "LTE\nCRS", "5G NR\nSSB"]
    x = np.arange(3)

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(1, 3, height=2.55)

        chan = [g1[k]["chan_bw_mhz"] for k in STDS]
        bref = [g1[k]["ref_bw_mhz"] for k in STDS]
        ax[0].bar(x - 0.19, chan, 0.36, color="#C8CDD2", edgecolor="#333", linewidth=0.7,
                  hatch="", label="channel bandwidth")
        ax[0].bar(x + 0.19, bref, 0.36, color=[_pc(k) for k in STDS],
                  edgecolor="#333", linewidth=0.7, hatch="///",
                  label="reference bandwidth B_ref")
        for i in range(3):
            ax[0].annotate(f"{bref[i]:.1f}", (i + 0.19, bref[i]), ha="center", va="bottom",
                           fontsize=8.5)
        ax[0].set_ylabel("Bandwidth [MHz]")
        ax[0].set_ylim(0, max(chan) * 1.42)
        ax[0].set_title("(a) What can be correlated", fontsize=9.5)
        ax[0].legend(fontsize=8.5, loc="upper left")

        dR = [g1[k]["dR_m"] for k in STDS]
        dRc = [g1[k]["chan_dR_m"] for k in STDS]
        ax[1].bar(x - 0.19, dRc, 0.36, color="#C8CDD2", edgecolor="#333", linewidth=0.7,
                  label="full channel known")
        ax[1].bar(x + 0.19, dR, 0.36, color=[_pc(k) for k in STDS],
                  edgecolor="#333", linewidth=0.7, hatch="///",
                  label="always-on reference")
        for i in range(3):
            ax[1].annotate(f"{dR[i]:.1f}", (i + 0.19, dR[i]), ha="center", va="bottom",
                           fontsize=8.5)
        ax[1].set_ylabel("Bistatic range resolution [m]")
        ax[1].set_ylim(0, max(dR) * 1.42)
        ax[1].set_title(f"(b) 5G is {led['ratios']['drb_nr_over_lte']:.1f}x coarser",
                        fontsize=9.5)
        ax[1].legend(fontsize=8.5, loc="upper left")

        for i, k in enumerate(STDS):
            sty = series_style(PIDX[k])
            ax[2].plot([g1[k]["dR_m"]], [g1[k]["vmax_ms"]], linestyle="none",
                       marker=sty["marker"], color=sty["color"], markersize=8.0,
                       markeredgecolor="#333", markeredgewidth=0.7,
                       label=f"{SHORT[k]} G1")
            q = REF["G2"][k]
            if abs(q["dR_m"] - g1[k]["dR_m"]) > 0.05:
                ax[2].annotate("", xy=(q["dR_m"], q["vmax_ms"]),
                               xytext=(g1[k]["dR_m"], g1[k]["vmax_ms"]),
                               arrowprops=dict(arrowstyle="->", color=sty["color"],
                                               ls="--", lw=1.0))
                ax[2].plot([q["dR_m"]], [q["vmax_ms"]], linestyle="none",
                           marker=sty["marker"], markerfacecolor="white",
                           markeredgecolor=sty["color"], markeredgewidth=1.2,
                           markersize=6.5, label=f"_{k}_G2")
        ax[2].axhspan(0.1, 2.0, color="#C8CDD2", alpha=0.55, zorder=0)
        ax[2].annotate("slower than a walking drone", (1.15, 0.72), fontsize=8.5, color="#333")
        ax[2].set_xscale("log")
        ax[2].set_yscale("log")
        ax[2].set_xlim(1.0, 60.0)
        ax[2].set_ylim(0.45, 300.0)
        ax[2].set_xticks([2, 5, 10, 20, 40])
        ax[2].set_yticks([1, 3, 10, 30, 100])
        ax[2].set_xticklabels(["2", "5", "10", "20", "40"])
        ax[2].set_yticklabels(["1", "3", "10", "30", "100"])
        ax[2].tick_params(labelsize=8.5)
        ax[2].set_xlabel("Range resolution [m]")
        ax[2].set_ylabel("Unambiguous speed [m/s]")
        ax[2].set_title("(c) The 5G double penalty", fontsize=9.5)
        ax[2].text(0.03, 0.50, "open marker + arrow:\npositioning session (G2)",
                   transform=ax[2].transAxes, fontsize=8.5, color="#333", va="top")
        ax[2].legend(fontsize=8.5, loc="upper left", handletextpad=0.3,
                     borderaxespad=0.2)
        for a in ax[:2]:
            a.set_xticks(x)
            a.set_xticklabels(labs, fontsize=8.5)
        assert_fig_text(*labs)
    return _emit(
        fig, "report03_f2_reference",
        f"Bistatic range resolution follows the reference-signal bandwidth, not the channel "
        f"bandwidth: the 5G SSB occupies {g1['nr']['ref_bw_mhz']:.1f} MHz inside a "
        f"{g1['nr']['chan_bw_mhz']:.1f} MHz channel and therefore resolves "
        f"{g1['nr']['dR_m']:.1f} m, while LTE CRS resolves {g1['lte']['dR_m']:.1f} m. Panel (c) "
        f"shows the two penalties acting together, with the dashed arrows marking what a "
        f"positioning session (PRS) would buy; a receiver borrowing someone else's cell operates "
        f"at the G1 point. G3 values of the same quantity are "
        f"{g2['nr']['dR_m']:.1f} m for 5G.",
        "Reference-signal budget")


def fig_occupancy(REF):
    """그림 3 — 셀이 바빠져도 거리 눈금은 기준신호 대역만 따라간다."""
    modes = ["G1", "G2", "G3"]
    w = 0.26
    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(1, 3, height=2.35)
        for i, k in enumerate(STDS):
            xs = np.arange(3) + (i - 1) * w
            for a, key in ((ax[0], "occ_pct"), (ax[1], "ref_bw_mhz"), (ax[2], "dR_m")):
                a.bar(xs, [REF[m][k][key] for m in modes], w, color=_pc(k),
                      edgecolor="#333", linewidth=0.7, hatch=PHATCH[k],
                      label=SHORT[k] if a is ax[0] else f"_{SHORT[k]}")
        for j, m in enumerate(modes):
            ax[2].annotate(f"{REF[m]['nr']['dR_m']:.0f}", (j + w, REF[m]["nr"]["dR_m"]),
                           ha="center", va="bottom", fontsize=8.5)
        for a, t, yl in ((ax[0], "(a) Grid occupancy", "occupied REs [%]"),
                         (ax[1], "(b) Reference bandwidth", "B_ref [MHz]"),
                         (ax[2], "(c) Range resolution", "Range resolution [m]")):
            a.set_xticks(np.arange(3))
            a.set_xticklabels(modes, fontsize=8.5)
            a.set_title(t, fontsize=9.5)
            a.set_ylabel(yl)
        ax[2].set_ylim(0, max(REF[m]["nr"]["dR_m"] for m in modes) * 1.25)
        ax[0].legend(fontsize=8.5, loc="upper left")
    return _emit(
        fig, "report03_f3_occupancy",
        f"Grid occupancy rises from {REF['G1']['nr']['occ_pct']:.1f}% to "
        f"{REF['G3']['nr']['occ_pct']:.1f}% for 5G between the idle and the fully loaded cell, "
        f"yet the reference bandwidth and the resulting range resolution move only for 5G, and "
        f"only because the positioning reference signal switches on. WiFi and LTE already carry "
        f"a wideband always-on reference, so their range resolution is set in the idle cell.",
        "Occupancy versus usable bandwidth")


def fig_ledger(led):
    """그림 4 — 조명원 대가 원장. 항목마다 값·출처키·닫는 방식을 함께 찍는다."""
    from matplotlib.patches import Patch

    ghz = {k: led["grids"]["G1"][k]["carrier_hz"] / 1e9 for k in STDS}
    cpi = fetch((J_FIX, "F4_linkbudget.cpi_asymmetry.cpi_ms"))
    cpi_hi, cpi_lo = max(cpi.values()), min(cpi.values())
    oc = led["occupancy_cost"]

    #  (라벨, 값, 출처키, 구간|None, 유효숫자). 구간이 있는 항목은 격자에서 **읽은** 값이다.
    items = [
        ("Occupancy: 5G always-on (SSB) vs full load (NR-PRS)",
         -oc["value_db"], "report5_results : A_occupancy",
         (-oc["bracket_hi_db"], -oc["bracket_lo_db"]), 0),
        ("Reference energy of the same pair (resource grid)",
         -led["ref_energy_gap_G1_to_G3_db"]["nr"], "report03_illuminators : ref_energy_gap",
         None, 2),
        ("WiFi packet duty (fraction of time on air)",
         fetch((J_FIX, "F4_linkbudget.wifi_pilot_fraction.packet_duty_db")),
         "report4_fixups : wifi_pilot_fraction", None, 2),
        ("WiFi pilot energy / total transmit energy (G3)",
         fetch((J_FIX, "F4_linkbudget.wifi_pilot_fraction.pilot_over_tx_energy_db")),
         "report4_fixups : wifi_pilot_fraction", None, 2),
        (f"Carrier lambda^2: LTE {ghz['lte']:.2f} -> WiFi {ghz['wifi']:.2f} GHz",
         led["lambda2"]["lte_to_wifi_db"], "report03_illuminators : lambda2", None, 2),
        (f"Carrier lambda^2: LTE {ghz['lte']:.2f} -> 5G {ghz['nr']:.2f} GHz",
         led["lambda2"]["lte_to_nr_db"], "report03_illuminators : lambda2", None, 2),
        (f"CPI convention (same M frames -> {cpi_lo:.0f} vs {cpi_hi:.0f} ms)",
         -fetch((J_FIX, "F4_linkbudget.cpi_asymmetry.span_db")),
         "report4_fixups : cpi_asymmetry", None, 2),
    ]
    assert_fig_text(*[i[0] for i in items], *[i[2] for i in items])

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(height=3.15)
        y = np.arange(len(items))[::-1]
        vals = [i[1] for i in items]
        bars = ax.barh(y, vals, height=0.60, edgecolor="#333", linewidth=0.7,
                       color=[PALETTE[1] if i[3] else PALETTE[0] for i in items],
                       label="_ledger")
        for p, i in zip(bars.patches, items):
            p.set_hatch("xxx" if i[3] else "")
        for yy, (lab, v, src, br, dg) in zip(y, items):
            if br:
                ax.errorbar(v, yy, xerr=[[v - br[0]], [br[1] - v]], fmt="none",
                            ecolor="#111", elinewidth=1.0, capsize=3.0, capthick=1.0,
                            zorder=4, label="_bracket")
                ax.text(br[0] - 0.7, yy, f"{v:+.0f}  [{br[0]:+.0f}, {br[1]:+.0f}]",
                        va="center", ha="right", fontsize=8.5, color="#111")
            else:
                ax.text(v - 0.7, yy, f"{v:+.{dg}f}", va="center", ha="right",
                        fontsize=8.5, color="#111")
            ax.text(0.6, yy + 0.15, lab, va="center", ha="left", fontsize=8.5, color="#111")
            ax.text(0.6, yy - 0.24, src, va="center", ha="left", fontsize=8.5, color="#555")
        ax.set_yticks([])
        ax.set_xlim(min(vals) - 22.0, 15.0)
        ax.axvline(0, color="#333", lw=0.8)
        ax.set_xlabel("Penalty [dB]   (more negative = the illuminator choice costs more)")
        ax.legend(handles=[Patch(facecolor=PALETTE[0], edgecolor="#333",
                                 label="closed form (grid, carrier, observation time)"),
                           Patch(facecolor=PALETTE[1], edgecolor="#333", hatch="xxx",
                                 label="read off a Monte-Carlo EIRP grid")],
                  fontsize=8.5, loc="lower left")
    return _emit(
        fig, "report03_f4_ledger",
        f"Illuminator cost ledger. Every entry is a ratio of two quantities taken on the same "
        f"target and the same geometry, so the target radar cross-section cancels and the entry "
        f"is independent of the scattering model. Six entries close in form on the resource grid, "
        f"the carrier or the observation time; the occupancy entry is read off a detection "
        f"Monte-Carlo on a {oc['eirp_grid_step_db']:.0f} dB EIRP grid with the bracket shown "
        f"({-oc['bracket_hi_db']:+.0f} to {-oc['bracket_lo_db']:+.0f} dB, Pd-interpolated "
        f"{-oc['interp_db']:+.1f} dB over {oc['n_trials']:.0f} trials).",
        "Illuminator cost ledger")


def fig_crosscheck():
    """그림 5 — 자원격자를 신호로 바꾸는 변조 단계를 Sionna PHY 독립 구현으로 채점한다."""
    from waveforms import all_waveforms
    from waveforms_sionna import ofdm_from_grid

    def _corr(a, b):
        n = min(len(a), len(b))
        a, b = np.asarray(a[:n], complex), np.asarray(b[:n], complex)
        a = a / (np.sqrt(np.mean(np.abs(a) ** 2)) + 1e-30)
        b = b / (np.sqrt(np.mean(np.abs(b) ** 2)) + 1e-30)
        return (float(abs(np.vdot(a, b)) / n),
                float(10 * np.log10(np.mean(np.abs(a - b) ** 2) + 1e-30)))

    #  ⚠ 막대와 주석의 숫자는 **기준 대조 실행**(J_WAVE:crosscheck)에서만 온다 — §3.1 표와
    #     같은 출처라야 리포트 안에서 두 값이 갈리지 않는다. 여기서 다시 도는 것은 시간파형
    #     겹쳐 그리기(모양 확인)뿐이고, 그 재계산 NMSE 는 float32 반올림 바닥이라 장치마다 흔들린다.
    C = fetch((J_WAVE, "crosscheck"))
    W = all_waveforms("G3")
    rows = {}
    for k in STDS:
        wf = W[k]
        cps = np.atleast_1d(np.asarray(wf.cp_lens))
        ours = np.asarray(wf.tx, complex)
        sio = ofdm_from_grid(wf.grid, wf.fft, cps)
        if _corr(ours, sio)[0] < 0.999:                              # pragma: no cover
            raise RuntimeError(f"{k}: 재생성 파형이 기준 대조 실행과 다르다 — {J_WAVE} 를 다시 만들어라")
        rows[k] = dict(wf=wf, ours=ours, sio=sio,
                       corr=float(C[k]["corr"]), nmse=float(C[k]["nmse_db"]),
                       corr_bug=float(C[k]["corr_bug"]),
                       cp_uniform=bool(np.all(cps == cps[0])))

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(2, 3, height=3.7)
        for c, k in enumerate(STDS):
            r = rows[k]
            wf = r["wf"]
            n0 = int(wf.fft * 0.5)
            n1 = n0 + 130
            t = np.arange(n0, n1) / wf.fs_hz * 1e6
            a = ax[0, c]
            a.plot(t, np.real(r["ours"][n0:n1]), lw=2.2, color=PALETTE[0], linestyle="-",
                   marker="none", label="ours (waveforms.py)")
            a.plot(t, np.real(r["sio"][n0:n1]), lw=1.0, color=PALETTE[1], linestyle="--",
                   marker="none", label="Sionna OFDMModulator")
            a.set_title(f"{SHORT[k]}: corr {r['corr']:.4f}, NMSE {r['nmse']:.1f} dB",
                        fontsize=8.5)
            a.set_xlabel("time [us]", fontsize=8.5)
            if c == 0:
                a.set_ylabel("Re{x(t)}", fontsize=8.5)
            a.tick_params(labelsize=8.5)
            if c == 0:
                a.legend(fontsize=8.5, loc="lower left")

            a = ax[1, c]
            b = a.bar(["CP array\n(3GPP rule)", "first CP only\n(rule missed)"],
                      [r["corr"], r["corr_bug"]], width=0.55,
                      color=PALETTE[0], edgecolor="#333", linewidth=0.7,
                      label="_control")
            b.patches[1].set_hatch("xxx")
            for p, v in zip(b.patches, [r["corr"], r["corr_bug"]]):
                a.annotate(f"{v:.4f}", (p.get_x() + p.get_width() / 2, v), ha="center",
                           va="bottom", fontsize=8.5)
            a.set_ylim(0, 1.32)
            a.tick_params(labelsize=8.5)
            if c == 0:
                a.set_ylabel("correlation", fontsize=8.5)
            a.set_title("CP uniform" if r["cp_uniform"] else "CP varies per symbol",
                        fontsize=8.5)
    out = _emit(
        fig, "report03_f5_crosscheck",
        f"The modulation stage is scored against an independent implementation: the same resource "
        f"grid is remodulated by sionna.phy.ofdm.OFDMModulator and compared with ours. Correlation "
        f"reaches {rows['nr']['corr']:.4f} and NMSE {rows['nr']['nmse']:.1f} dB for 5G NR, which "
        f"is the float32 rounding floor of the reference run. The bottom row establishes the "
        f"resolving power of the "
        f"test: passing only the first cyclic-prefix length, instead of the per-symbol array that "
        f"3GPP specifies, collapses the LTE and NR correlation to "
        f"{rows['lte']['corr_bug']:.2f} and {rows['nr']['corr_bug']:.2f}, while the uniform-CP "
        f"WiFi waveform stays at {rows['wifi']['corr_bug']:.4f}.",
        "Sionna PHY cross-check")
    return out


def _amb_rows():
    """verify_ambiguity.json 의 6개 (표준 x 점유) 항목을 표시 순서대로."""
    W = fetch((J_AMB, "waveforms"))
    keys = ["wifi_G1", "lte_G1", "nr_G1", "wifi_G3", "lte_G3", "nr_G3"]
    return [(k, W[k]) for k in keys]


def fig_af_mainlobe():
    """그림 6 — 모호함수 주엽. 측정 −3 dB 폭 vs 닫힌형(c/B_ref, 1/T_CPI)."""
    rows = _amb_rows()
    #  라벨은 **표준 + 점유모드**만 — 기준신호 이름까지 넣으면 6칸이 겹친다(캡션이 이름을 진다).
    labs = [f"{SHORT[k.split('_')[0]]}\n{k.split('_')[1]}" for k, _ in rows]
    stds = [k.split("_")[0] for k, _ in rows]
    assert_fig_text(*labs)
    x = np.arange(len(rows))

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(1, 2, height=2.65)

        for j, (a, mk, tk, lab, ttl) in enumerate((
                (ax[0], "dR_meas_m", "dR_theory_m", "Bistatic range mainlobe [m]",
                 "(a) Range: measured -3 dB width vs c/B_ref"),
                (ax[1], "dF_meas_hz", "dF_theory_hz", "Doppler mainlobe [Hz]",
                 "(b) Doppler: measured -3 dB width vs 1/T_CPI"))):
            th = [r[tk] for _, r in rows]
            me = [r[mk] for _, r in rows]
            a.bar(x - 0.2, th, 0.4, color="#C8CDD2", edgecolor="#333", linewidth=0.7,
                  label="closed form")
            a.bar(x + 0.2, me, 0.4, color=[_pc(s) for s in stds], edgecolor="#333",
                  linewidth=0.7, hatch="///", label="measured -3 dB width")
            for xi, (m, t) in enumerate(zip(me, th)):
                a.annotate(f"{m / t * 100:.0f}%" if j == 0 else f"{m / t:.2f}x",
                           (xi, max(m, t)), ha="center", va="bottom", fontsize=8.5)
            a.set_ylabel(lab)
            a.set_title(ttl, fontsize=9.5)
            a.set_ylim(0, max(max(th), max(me)) * 1.62)
            a.set_xticks(x)
            a.set_xticklabels(labs, fontsize=8.5)
            a.tick_params(labelsize=8.5)
            a.legend(fontsize=8.5, loc="upper right" if j == 0 else "upper left",
                     handletextpad=0.3, borderaxespad=0.2)
    return _emit(
        fig, "report03_f6_af_mainlobe",
        "Ambiguity-function mainlobes measured on the detector kernel against their closed-form "
        "predictions, for WiFi VHT-LTF, LTE CRS or PRS and 5G SSB or NR-PRS in the idle (G1) "
        "and fully loaded (G3) regimes. The range mainlobe tracks the convention dR_b = c/B_ref "
        "used "
        "throughout, and the Doppler mainlobe sits at the same multiple of 1/T_CPI for every "
        "waveform because the broadening is set by the slow-time Hann window rather than by the "
        "waveform.",
        "Ambiguity mainlobes")


def fig_af_sidelobe():
    """그림 7 — 부엽·도플러 레플리카. 기준신호가 표적 에너지를 어디에 남기는가."""
    from matplotlib.patches import Patch

    rows = _amb_rows()
    labs = [f"{SHORT[k.split('_')[0]]}\n{k.split('_')[1]}" for k, _ in rows]
    stds = [k.split("_")[0] for k, _ in rows]
    assert_fig_text(*labs)
    x = np.arange(len(rows))

    with paper_style(width=W2, base_pt=9.5) as st:
        fig, ax = st.figure(1, 2, height=2.65)

        psl = [r["psl_2d_db"] for _, r in rows]
        isl = [r["isl_2d_db"] for _, r in rows]
        #  해치는 **양**(PSL vs ISL)만 뜻한다 — 표준은 색과 x 축이 진다.
        ax[0].bar(x - 0.2, psl, 0.4, color=[_pc(s) for s in stds], edgecolor="#333",
                  linewidth=0.7, label="peak sidelobe (2D)")
        ax[0].bar(x + 0.2, isl, 0.4, color=[_pc(s) for s in stds], edgecolor="#333",
                  linewidth=0.7, hatch="xxx", label="integrated sidelobe (2D)")
        ax[0].axhline(0, color="#333", lw=0.8)
        ax[0].set_ylim(min(psl) * 1.12, 13.0)
        ax[0].set_ylabel("Level relative to mainlobe [dB]")
        ax[0].set_title("(a) Energy leaving the mainlobe", fontsize=9.5)
        ax[0].set_xticks(x)
        ax[0].set_xticklabels(labs, fontsize=8.5)
        ax[0].tick_params(labelsize=8.5)
        ax[0].legend(handles=[Patch(facecolor="#8C8C8C", edgecolor="#333",
                                    label="peak sidelobe (2D)"),
                              Patch(facecolor="#8C8C8C", edgecolor="#333", hatch="xxx",
                                    label="integrated sidelobe (2D)")],
                     fontsize=8.5, loc="upper left", ncol=2, handletextpad=0.3,
                     columnspacing=0.8, borderaxespad=0.2)

        #  WiFi 는 G1 과 G3 의 기준신호가 같은 VHT-LTF 라 점이 정확히 겹친다 — 하나로 찍는다.
        seen: dict[tuple, list] = {}
        for (k, r), s in zip(rows, stds):
            key = (round(r["ref_time_spread"], 6), round(r["doppler_replica_db"], 4))
            seen.setdefault(key, [s, []])[1].append(f"{r['ref_name']} {k.split('_')[1]}")
        for i, ((sp, rp), (s, names)) in enumerate(sorted(seen.items())):
            merged = names[0] if len(names) == 1 else \
                names[0].rsplit(" ", 1)[0] + " (" + "=".join(
                    n.rsplit(" ", 1)[1] for n in names) + ")"
            sty = series_style(PIDX[s])
            ax[1].plot([sp], [rp], linestyle="none", marker=sty["marker"], color=sty["color"],
                       markersize=8.0, markeredgecolor="#333", markeredgewidth=0.7,
                       label=f"_{merged}")
            left = bool(i % 2)
            ax[1].annotate(merged, (sp, rp), textcoords="offset points",
                           xytext=(-9 if left else 9, -13 if left else 7),
                           ha="right" if left else "left", fontsize=8.5, color="#333")
        ax[1].axvline(1 / np.sqrt(12), color="#333", ls="--", lw=1.0)
        ax[1].annotate("uniform spread\nover the frame", (1 / np.sqrt(12) * 1.15, 6.0),
                       ha="left", fontsize=8.5, color="#333")
        ax[1].set_xscale("log")
        ax[1].set_xlim(4e-4, 6.0)
        ax[1].set_ylim(-30, 13)
        ax[1].tick_params(labelsize=8.5)
        ax[1].set_xticks([1e-3, 1e-2, 1e-1, 1])
        ax[1].set_xticklabels(["0.001", "0.01", "0.1", "1"])
        ax[1].set_xlabel("RMS spread of reference energy over the frame")
        ax[1].set_yticks([-30, -20, -10, 0, 10])
        ax[1].set_ylabel("Doppler replica at ±PRF [dB]")
        ax[1].set_title("(b) Why some references alias at full strength", fontsize=9.5)
    return _emit(
        fig, "report03_f7_af_sidelobe",
        "Sidelobe budget and Doppler replica of each reference signal, in the idle (G1) and fully "
        "loaded (G3) regimes. A reference whose energy is "
        "bunched at the front of the frame, such as the WiFi VHT-LTF or the 5G SSB, keeps a "
        "full-strength replica at plus or minus the reference repetition rate, so targets beyond "
        "the unambiguous velocity fold back with almost no loss; the LTE CRS is spread over the "
        "whole frame and its replica cancels. The dashed line marks a uniform spread, the largest "
        "value the abscissa can take.",
        "Sidelobes and Doppler replicas")


# =========================================================================== #
#  3) 노트북 조립
# =========================================================================== #
def _figblock(no: int, stem: str, question: str, paper_caption: str):
    """그림 한 장 = 셀 하나 — 노트북 캡션은 **질문**, 논문 캡션은 **완결 문장**."""
    blk = figure_md(f"outputs/figures/{stem}.png", no, question,
                    paper_caption=paper_caption, report=REPORT_KEY)
    return md(str(blk), "",
              f"<sub>논문 캡션 (Fig. {no}) — {paper_caption}</sub>")


#: 논문 캡션은 PDF 메타데이터에도 심겨 있다. 여기서는 **한 곳에서** 관리해 둘이 어긋나지 않게 한다.
def _paper_captions(saved: dict) -> dict:
    return {k: v["caption"] for k, v in saved.items()}


def build_blocks(led, caps):
    """여는 블록(한 일/결과/방법/재현 + 논문 대응) + §0~§4 + 방법·방어선·인용 + 다음 단계.

    본문 숫자는 전부 `num()` 을 통과한다 — 손으로 친 숫자 0개.
    """
    W1 = lambda k, f=None, u="": num(None, (J_WAVE, f"reference.G1.{k}"), f, u)   # noqa: E731
    A = lambda k, f=None, u="": num(None, (J_AMB, f"waveforms.{k}"), f, u)        # noqa: E731
    L = lambda k, f=None, u="": num(None, (J_LED, k), f, u)                       # noqa: E731
    X = lambda k, f=None, u="": num(None, (J_WAVE, f"crosscheck.{k}"), f, u)      # noqa: E731
    F = lambda k, f=None, u="": num(None, (J_FIX, f"F4_linkbudget.{k}"), f, u)    # noqa: E731

    #  §2.2 표는 straddle 행 순서가 (wifi, lte, nr) 라고 가정한다 — 그 가정을 여기서 깬다.
    #  B/f_s 는 격자에서 다시 계산할 수 있으므로, 행이 뒤섞이면 여기서 빌드가 멈춘다.
    for i, k in enumerate(STDS):
        got = fetch((J_FIX, f"F4_linkbudget.straddle.rows[{i}].b_over_fs"))
        want = led["grids"]["G1"][k]["bw_hz"] / (fetch((J_WAVE, f"crosscheck.{k}.fs_mhz")) * 1e6)
        if abs(got - want) > 1e-6 * max(1.0, abs(want)):            # pragma: no cover
            raise RuntimeError(
                f"straddle 행 {i} 가 {k} 가 아니다 — B/fs {got:.6f} vs 격자 {want:.6f}. "
                f"{J_FIX} 의 행 순서를 확인하라.")

    blocks = []

    # ── 여는 블록 + 논문 대응(PAPER_SPEC §4.1) ─────────────────────────────── #
    hdr = header(
        num=3,
        title="조명원: 세 파형이 무는 대가를 dB 원장으로 닫았다",
        did="패시브가 빌려 쓰는 상시 기준신호를 WiFi · LTE · 5G NR 세 표준의 자원격자에서 "
            "세우고, 조명원 선택이 무는 대가를 dB 원장으로 닫았다.",
        results=[
            f"원장 항목마다 분자와 분모가 같은 표적·같은 기하라서 표적 σ 가 상쇄된다 — "
            f"반송파 λ² {L('lambda2.span_db', '{:.2f}', 'dB')}(밴드 양끝) · "
            f"WiFi 패킷 듀티 {F('wifi_pilot_fraction.packet_duty_db', '{:.2f}', 'dB')} · "
            f"CPI 규약 {F('cpi_asymmetry.span_db', '{:.2f}', 'dB')} 는 자원격자 · 반송파 · "
            f"관측시간에서 닫히는 **닫힌형**이다.",
            f"점유 대가는 검출 몬테카를로의 EIRP 격자에서 **읽은** 값이다 — 격자점 차 "
            f"{L('occupancy_cost.value_db', '{:.0f}', 'dB')}, 구간 "
            f"{L('occupancy_cost.bracket_lo_db', '{:.0f}')}~"
            f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')}, Pd 선형보간 "
            f"{L('occupancy_cost.interp_db', '{:.1f}', 'dB')} "
            f"(격자 눈금 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} · 시행 "
            f"{L('occupancy_cost.n_trials', '{:.0f}')}회).",
            f"상시 기준신호를 표준마다 하나씩 격자에 세웠다 — "
            f"LTE=CRS($B_{{ref}}$ {W1('lte.ref_bw_mhz', '{:.2f}', 'MHz')}) · "
            f"5G=SSB({W1('nr.ref_bw_mhz', '{:.2f}', 'MHz')}) · "
            f"WiFi=VHT-LTF({W1('wifi.ref_bw_mhz', '{:.2f}', 'MHz')}).",
            f"5G 는 두 축에서 대가를 낸다 — 거리눈금 $\\Delta R_b$ 가 "
            f"{W1('nr.dR_m', '{:.1f}', 'm')} 로 LTE {W1('lte.dR_m', '{:.1f}', 'm')} 의 "
            f"{L('ratios.drb_nr_over_lte', '{:.1f}')}배이고, SSB 물리 PRF "
            f"{W1('nr.prf_hz', '{:.0f}', 'Hz')} 가 무모호 속도를 "
            f"{W1('nr.vmax_ms', '{:.2f}', 'm/s')} 로 정한다.",
            f"변조 단계는 Sionna PHY 독립 구현과 상관 {X('nr.corr', '{:.4f}')} · NMSE "
            f"{X('nr.nmse_db', '{:.1f}', 'dB')} 로 일치하고(G3 격자, 세 파형), 모호함수는 "
            f"검출기 거리도플러 출력과 최대 "
            f"{L('detector_af_max_err_db.value', '{:.3f}', 'dB')} 안에서 같다"
            f"({L('detector_af_max_err_db.n_cases', '{:.0f}')}개 경우, −45 dB 이상 셀).",
        ],
        method=[
            ("상시 기준신호 제원",
             "`TS 36.211`(CRS) · `TS 38.211`(SSB) · `IEEE 802.11ac`(VHT-LTF) 를 읽어 "
             "자원격자를 세우고 격자에서 직접 쟀다 — `src/waveforms.py:258·313·370`"),
            ("대가 원장",
             f"두 양의 비로 계산했다 — λ² 는 반송파 비, 듀티는 시간 비. 점유는 같은 표적·같은 "
             f"기하에서 $P_d$ {L('occupancy_cost.pd_threshold', '{:.1f}')} 를 넘기는 EIRP 차를 "
             f"{L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} 격자에서 읽는다"),
            ("변조 채점",
             "같은 자원격자를 Sionna PHY `OFDMModulator` 로 독립 변조해 상관·NMSE 로 "
             "대조했다 — `src/make_report03_illuminators.py:fig_crosscheck`"),
            ("모호함수",
             "검출기가 쓰는 커널 그대로 계산하고 검출기 거리도플러 출력과 대조했다 — "
             "`benchmark/verify_ambiguity.py:150`"),
            ("그림 규격",
             "그림 7장 전부 벡터 PDF + 400 dpi PNG 로 저장하고, 2단 통폭 배치 기준 8 pt 하한과 "
             "색+해치/마커 이중부호화를 저장 직전에 검사했다 — `src/paper_kit.py:save_figure`"),
        ],
        prereq=[("02편", "표적 σ 를 어떤 방법으로 냈는지 — 이 편의 수치는 σ 를 곱하기 앞 단계다")],
        repro=dict(
            cmd=["cd /home/yunjung/workspace/sionna2",
                 "# ① 파형 제원 · 자원격자 · Sionna 교차대조 수치",
                 "~/.venvs/py312/bin/python src/viz_report2.py",
                 "# ② 모호함수 — 검출기와 같은 커널",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/verify_ambiguity.py",
                 "# ③ 링크버짓 규약 상수(듀티 · CPI · CFAR)",
                 "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/report4_fixups.py",
                 "# ④ 이 편의 파생 원장 + 게재규격 그림 7장 + 노트북",
                 "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report03_illuminators.py"],
            out=[J_WAVE, J_AMB, J_FIX, J_MTX, J_LED],
            runtime=f"① {num(None, (J_WAVE, 'meta.runtime_s'), '{:.0f}', 's')} "
                    f"(대부분은 같은 스크립트의 RCS 스윕이고 파형 부분은 초 단위) · "
                    f"③ {num(None, (J_FIX, '_meta.runtime_s'), '{:.0f}', 's')} · "
                    f"② GPU 1장 수 분 · ④ CPU 20초 안쪽",
            note=f"{J_MTX} 는 검출 몬테카를로가 이미 남긴 것이다 — 이 편은 그중 "
                 f"`A_occupancy` 만 인용한다(재실행 불필요).",
        ),
    )
    hdr = attach(hdr, paper_map(
        "III-B. Illuminators",
        claim="세 조명원을 가르는 양 — 점유 대가 · 반송파 λ² · 기준신호 대역이 정하는 "
              "$\\Delta R_b = c/B_{ref}$ — 은 모두 같은 표적·같은 기하에서 잰 두 양의 비이거나 "
              "규격이 고정한 상수이고, 표적 σ 는 분자와 분모에 함께 들어가 상쇄된다.",
        evidence=["§1 파형표", "§2 대가 원장", "그림 2", "그림 4",
                  "outputs/report03_illuminators.json:lambda2",
                  "outputs/report03_illuminators.json:occupancy_cost",
                  "outputs/report2_waveform_rcs.json:reference.G1"],
        qualifications=[
            "λ² 항은 EIRP 고정 · 수신 안테나 **이득** 고정 전제에서 선다 "
            "(`src/freespace_link.py:371`)",
            "점유 대가는 EIRP 격자에서 읽은 값이라 참값이 구간 "
            f"[{L('occupancy_cost.bracket_lo_db', '{:.0f}')}, "
            f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')}] 안에 있고, 그 안에 기준신호 "
            "대역 확대가 함께 들어 있다",
        ],
        report=REPORT_KEY))
    blocks.append(hdr)

    # ── §0 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §0. 논문이 이 편에서 가져가는 것 — **σ 와 무관하게 정확한 양**",
        "",
        "이 편의 수치는 표적 산란을 곱하기 **앞** 단계에서 닫힌다. 그래서 σ 절대레벨이 X dB "
        "움직여도 세 조명원의 **순위와 격차는 그대로**이고, 움직이는 것은 절대 검출거리뿐이다.",
        "",
        table(["양", "크기", "지위", "어디서"],
              [["기준신호 대역 → $\\Delta R_b = c/B_{ref}$",
                f"{W1('wifi.dR_m', '{:.1f}')} · {W1('lte.dR_m', '{:.1f}')} · "
                f"{W1('nr.dR_m', '{:.1f}', 'm')}", "규격 자원격자에서 닫힌다", "§1 · 그림 2"],
               ["반송파 λ² (LTE→WiFi)", L("lambda2.lte_to_wifi_db", "{:.2f}", "dB"),
                "반송파 정의에서 닫힌다", "§2 · 그림 4"],
               ["반송파 λ² (LTE→5G)", L("lambda2.lte_to_nr_db", "{:.2f}", "dB"),
                "반송파 정의에서 닫힌다", "§2 · 그림 4"],
               ["CPI 규약 격차", F("cpi_asymmetry.span_db", "{:.2f}", "dB"),
                "관측시간에서 닫힌다", "§2.1"],
               ["점유 대가 (5G 상시 vs 풀로드)", L("occupancy_cost.value_db", "{:.0f}", "dB"),
                f"몬테카를로 격자에서 읽는다 (구간 "
                f"{L('occupancy_cost.bracket_lo_db', '{:.0f}')}~"
                f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')})", "§2.1 · 그림 4"]]),
        "",
        "05편의 $P_d$ 와 절대 검출거리는 여기에 σ 와 기하를 곱해 나온다. 이 편의 다섯 줄은 그 "
        "곱셈 이전에 확정되므로 **σ 논의와 독립으로 인수인계된다**.",
    ))

    # ── §1 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §1. 세 조명원 — 늘 켜져 있는 것",
        "",
        "패시브 수신기는 두 조건을 **동시에** 만족하는 신호에 상관을 건다. "
        "**① 내용을 미리 안다** — 데이터는 매 순간 바뀌므로 규격이 고정한 기준신호가 그 자리를 맡는다. "
        "**② 아무 셀이나 늘 켠다** — 상시 신호라야 표적이 지나가는 그 순간에도 공중에 있다.",
        "",
        "두 조건을 다 만족하는 신호는 표준마다 **하나씩**이다. 격자에서 잰 제원은 아래와 같다.",
        "",
        table(["표준", "상시 기준신호", "반송파", "채널 점유대역", "$B_{ref}$",
               "$\\Delta R_b=c/B_{ref}$"],
              [["WiFi 802.11ac", "VHT-LTF", W1("wifi.carrier_ghz", "{:.2f}", "GHz"),
                W1("wifi.chan_bw_mhz", "{:.1f}", "MHz"), W1("wifi.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("wifi.dR_m", "{:.1f}", "m")],
               ["LTE Rel-9", "CRS", W1("lte.carrier_ghz", "{:.3f}", "GHz"),
                W1("lte.chan_bw_mhz", "{:.1f}", "MHz"), W1("lte.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("lte.dR_m", "{:.1f}", "m")],
               ["5G NR Rel-16", "SSB", W1("nr.carrier_ghz", "{:.2f}", "GHz"),
                W1("nr.chan_bw_mhz", "{:.1f}", "MHz"), W1("nr.ref_bw_mhz", "{:.1f}", "MHz"),
                W1("nr.dR_m", "{:.1f}", "m")]]),
        "",
        "$B_{ref}$ 는 기준신호가 차지한 부반송파의 **양끝 span** 이다(`src/waveforms.py:237`) — "
        "안쪽 널 톤을 포함하므로 WiFi 는 span 이 점유대역보다 넓다. 격자 코드는 "
        "`src/waveforms.py:258`(WiFi) · `:313`(LTE) · `:370`(5G), $\\Delta R_b$ 는 `:144`.",
    ))

    blocks.append(_figblock(1, "report03_f1_grid",
                            "유휴 셀이 실제로 켜는 칸은 어디이고, 그중 패시브가 상관에 쓰는 것은 "
                            "무엇인가?", caps["report03_f1_grid"]))

    blocks.append(md(
        "### §1.1 5G 가 치르는 두 배의 대가 — 좁고, 드물다",
        "",
        "**PRS 는 측위 세션이 설정될 때 켜지는 옵션**이고, 남의 셀을 빌리는 패시브 수신기의 "
        "기본선은 상시 신호인 **SSB** 다. PRS 를 켠 수치는 낙관적 상한으로 읽는다.",
        "",
        table(["축", "정하는 것", "LTE CRS", "5G SSB", "격차"],
              [["거리 $\\Delta R_b$", "$B_{ref}$", W1("lte.dR_m", "{:.1f}", "m"),
                W1("nr.dR_m", "{:.1f}", "m"),
                f"{L('ratios.drb_nr_over_lte', '{:.1f}')}배 거칢"],
               ["속도 $v_{max}$ (물리 PRF)", "PRF", W1("lte.vmax_ms", "{:.1f}", "m/s"),
                W1("nr.vmax_ms", "{:.2f}", "m/s"),
                f"{L('ratios.vmax_lte_over_nr', '{:.0f}')}배 넓음"]]),
        "",
        f"SSB 의 반복률은 {W1('nr.prf_hz', '{:.0f}', 'Hz')} — 걷는 속도의 드론도 도플러가 "
        f"접힌다(§4.3). 여기에 반송파가 λ² "
        f"{L('lambda2.lte_to_nr_db', '{:.2f}', 'dB')} 를 더한다(§2). "
        f"세대가 최신일수록 조명원으로 유리하다는 통념을 이 세 항목이 뒤집는다.",
    ))

    blocks.append(_figblock(2, "report03_f2_reference",
                            "기준신호의 넓이와 반복이 거리·속도 눈금을 각각 얼마로 정하는가?",
                            caps["report03_f2_reference"]))

    # ── §2 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §2. 대가 원장 — 무엇이 각 항목의 유효숫자를 정하나",
        "",
        "조명원 선택이 만드는 dB 격차를 아래 표에 모은다. 오른쪽 열이 그 항목을 **닫는 방식**이다 "
        "— 여섯 항목은 닫힌형이고, 점유 대가는 검출 몬테카를로의 EIRP 격자에서 읽는다.",
        "",
        "부호는 원본 JSON 그대로이고, 그림 4 는 **음수 = 손해**로 부호를 맞춰 다시 그린 것이다.",
        "",
        table(["항목", "값", "무엇의 비인가", "닫는 방식"],
              [["점유 대가 (5G · 상시 vs 풀로드)", L("occupancy_cost.value_db", "{:.0f}", "dB"),
                f"같은 표적·같은 기하에서 $P_d$ "
                f"{L('occupancy_cost.pd_threshold', '{:.1f}')} 를 넘기는 EIRP 차",
                "몬테카를로 격자 읽기 — §2.1"],
               ["기준신호 에너지 격차 (같은 쌍)", L("ref_energy_gap_G1_to_G3_db.nr", "{:.2f}", "dB"),
                "$E_{ref}$(G3) / $E_{ref}$(G1) — 상관에 쓰는 에너지만", "닫힌형 — 자원격자"],
               ["반송파 λ² (LTE→WiFi)", L("lambda2.lte_to_wifi_db", "{:.2f}", "dB"),
                "$20\\log_{10}(\\lambda/\\lambda_{ref})$ — EIRP·수신이득 고정", "닫힌형 — 반송파"],
               ["반송파 λ² (LTE→5G)", L("lambda2.lte_to_nr_db", "{:.2f}", "dB"), "위와 같음",
                "닫힌형 — 반송파"],
               ["WiFi 파일럿 / 총 송신 에너지",
                F("wifi_pilot_fraction.pilot_over_tx_energy_db", "{:.2f}", "dB"),
                "G3 격자에서 상관에 쓰는 몫", "닫힌형 — 자원격자"],
               ["WiFi 패킷 듀티", F("wifi_pilot_fraction.packet_duty_db", "{:.2f}", "dB"),
                "패킷이 공중에 있는 시간 비율", "닫힌형 — 시간"],
               ["CPI 규약 격차", F("cpi_asymmetry.span_db", "{:.2f}", "dB"),
                "같은 프레임 수 M 이 5G 에 주는 관측시간이 절반", "닫힌형 — 관측시간"]]),
    ))

    blocks.append(md(
        "### §2.1 각 항목이 서는 조건",
        "",
        table(["항목", "성립 조건", "크기"],
              [["반송파 λ²", "EIRP 고정 · 수신 안테나 **이득** 고정 (`src/freespace_link.py:371`)",
                "수신 **개구면적**을 고정하면 부호가 뒤집힌다"],
               [f"점유 {L('occupancy_cost.value_db', '{:.0f}', 'dB')} — 격자 읽기",
                f"EIRP 격자 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} · 시행 "
                f"{L('occupancy_cost.n_trials', '{:.0f}')}회 · 표적 "
                f"{L('occupancy_cost.drone')} · {L('occupancy_cost.scen')}; G1→G3 은 기준신호 대역이 "
                f"{L('occupancy_cost.ref_bw_G1_mhz', '{:.1f}', 'MHz')} → "
                f"{L('occupancy_cost.ref_bw_G3_mhz', '{:.2f}', 'MHz')} 로 함께 넓어진 값",
                f"참값 구간 {L('occupancy_cost.bracket_lo_db', '{:.0f}')}~"
                f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')} · $P_d$ 선형보간 "
                f"{L('occupancy_cost.interp_db', '{:.1f}', 'dB')}. "
                f"대역을 고정한 점유 스윕이 두 항을 가른다 (§5)"],
               ["CPI 규약", "같은 M 프레임이 5G 에 주는 관측시간이 절반",
                f"{F('cpi_asymmetry.span_db', '{:.2f}', 'dB')} — 04 · 05편은 관측시간을 맞춘 뒤 비교한다"],
               ["WiFi 두 항목", "에너지 비 · 시간 비 — 서로 다른 양이다",
                f"{F('wifi_pilot_fraction.pilot_over_tx_energy_db', '{:.2f}', 'dB')} · "
                f"{F('wifi_pilot_fraction.packet_duty_db', '{:.2f}', 'dB')}"]]),
    ))

    blocks.append(_figblock(3, "report03_f3_occupancy",
                            "셀이 데이터로 바빠지면 패시브의 거리분해능도 같이 좋아지는가?",
                            caps["report03_f3_occupancy"]))

    blocks.append(_figblock(4, "report03_f4_ledger",
                            "조명원 선택이 무는 대가는 항목별로 몇 dB 인가?",
                            caps["report03_f4_ledger"]))

    blocks.append(md(
        "### §2.2 거리 규약 — 바이스태틱 $c/B$",
        "",
        f"이 프로젝트의 거리축은 **바이스태틱 거리합** $R_b=R_1+R_2-L$ 이라 분해능은 "
        f"$\\Delta R_b=c/B_{{ref}}$ 다. 모노스태틱 교과서 값 $c/2B$ 는 그 절반이고, 비는 "
        f"{num(None, (J_FIX, 'F3_ambiguity.resolution_convention_conflict.rows[0].factor'), '{:.0f}')}"
        f"배다. 두 규약을 섞으면 분해능을 그만큼 낙관하게 된다.",
        "",
        "04편 §4 의 셀 크기 표가 같은 규약을 쓰고 같은 값을 싣는다 — 거기서는 표본율이 정하는 "
        "거리 빈 $c/f_s$ 를 같은 표에 병기해 격자 간격과 분해능을 갈라 놓는다.",
        "",
        "잡음대역 정규화 $\\sqrt{B/f_s}$ 도 같은 성격의 규약이다 — 선언 대역 $B$ 와 표본율 $f_s$ 가 "
        "다르면 주입 진폭을 그만큼 낮춰야 매치드필터 출력 SNR 이 파형 간 공정해진다"
        "(`benchmark/run_min_cell.py:131`).",
        "",
        table(["파형", "$B/f_s$", "$\\Delta R_b=c/B_{ref}$", "모노 등가 $c/2B$"],
              [[fetch((J_FIX, f"F4_linkbudget.straddle.rows[{i}].name")),
                num(None, (J_FIX, f"F4_linkbudget.straddle.rows[{i}].b_over_fs"), "{:.4f}"),
                num(None, (J_AMB, f"waveforms.{k}_G1.dR_theory_m"), "{:.2f}", "m"),
                num(None, (J_AMB, f"waveforms.{k}_G1.dR_mono_theory_m"), "{:.2f}", "m")]
               for i, k in enumerate(STDS)]),
    ))

    blocks.append(code(
        "# §2 원장을 JSON 에서 그대로 읽어 찍는다 — 본문 숫자에 하드코딩이 없음을 확인하는 셀.",
        "import json",
        "L = json.load(open('outputs/report03_illuminators.json'))",
        "print('점유 대가      ', f\"{L['occupancy_cost']['value_db']:+.1f} dB\",",
        "      f\"(G1 {L['occupancy_cost']['eirp_G1_dbm']:+.0f} dBm vs \"",
        "      f\"G3 {L['occupancy_cost']['eirp_G3_dbm']:+.0f} dBm, \"",
        "      f\"격자 {L['occupancy_cost']['eirp_grid_step_db']:.0f} dB)\")",
        "for k in ('wifi', 'lte', 'nr'):",
        "    g1, g3 = L['grids']['G1'][k], L['grids']['G3'][k]",
        "    print(f\"{k:5s} G1 ref={g1['ref_name']:8s} B_ref={g1['ref_bw_hz']/1e6:6.2f} MHz \"",
        "          f\"dRb={g1['drb_m']:6.2f} m  E_ref/E_tx={g1['e_ref_over_tx_db']:+6.2f} dB\"",
        "          f\"   | G1->G3 기준신호 에너지 \"",
        "          f\"{L['ref_energy_gap_G1_to_G3_db'][k]:+5.2f} dB\")",
    ))

    # ── §3 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §3. 파형 검증 — Sionna PHY 로 채점",
        "",
        "격자를 신호로 바꾸는 **변조 단계**를 독립 구현으로 채점한다. 같은 자원격자를 Sionna PHY 의 "
        "`sionna.phy.ofdm.OFDMModulator` 에 넣고, 우리 변조기 출력과 상관·NMSE 를 잰다"
        "(`src/make_report03_illuminators.py:fig_crosscheck`).",
        "",
        table(["이 대조가 확인하는 것", "무엇으로"],
              [["IFFT 규약 — fftshift 방향 · 정규화", "두 구현의 시간파형 상관"],
               ["CP 복사와 심볼별 이어붙이기 순서", "심볼별 CP 배열을 뺀 대조군과 비교"],
               ["두 독립 구현의 시간파형 일치", "NMSE 바닥"]]),
        "",
        "자원격자 자체(파일럿 좌표 · 가드밴드 · DC 널)는 규격서를 읽어 `src/waveforms.py` 에 세웠고, "
        "X410 캡처와 대조해 실측으로 확정한다(§5).",
    ))

    blocks.append(_figblock(5, "report03_f5_crosscheck",
                            "같은 자원격자를 두 변조기에 넣으면 같은 시간파형이 나오는가?",
                            caps["report03_f5_crosscheck"]))

    blocks.append(md(
        "### §3.1 채점 결과",
        "",
        table(["표준", "표본 수", "$f_s$", "상관", "NMSE", "CP 앞머리", "CP 배열을 뺀 대조군"],
              [["WiFi 802.11ac", X("wifi.n", "{:.0f}"), X("wifi.fs_mhz", "{:.2f}", "MHz"),
                X("wifi.corr", "{:.4f}"), X("wifi.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.wifi.cp_head'))}`", X("wifi.corr_bug", "{:.4f}")],
               ["LTE Rel-9", X("lte.n", "{:.0f}"), X("lte.fs_mhz", "{:.2f}", "MHz"),
                X("lte.corr", "{:.4f}"), X("lte.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.lte.cp_head'))}`", X("lte.corr_bug", "{:.4f}")],
               ["5G NR Rel-16", X("nr.n", "{:.0f}"), X("nr.fs_mhz", "{:.2f}", "MHz"),
                X("nr.corr", "{:.4f}"), X("nr.nmse_db", "{:.1f}", "dB"),
                f"`{fetch((J_WAVE, 'crosscheck.nr.cp_head'))}`", X("nr.corr_bug", "{:.4f}")]]),
        "",
        "세 파형 모두 상관이 소수 넷째 자리까지 1 이고, 남은 차이는 float32 반올림 바닥이다. "
        "대조는 **G3(풀로드) 격자**에서 돈다.",
        "",
        "마지막 열은 **대조의 분해력 시험**이다 — 재변조 쪽에 심볼별 CP 배열 대신 첫 CP 스칼라만 "
        "넘기면 두 번째 심볼부터 시간축이 어긋나 상관이 무너진다. CP 가 심볼마다 같은 WiFi 는 "
        "그대로 1 이다.",
    ))

    # ── §4 ────────────────────────────────────────────────────────────────── #
    blocks.append(md(
        "## §4. 모호함수 — 검출기가 실제로 보는 눈",
        "",
        f"모호함수 $\\chi(\\tau,f_d)$ 는 기준신호 하나가 거리-도플러 평면에 만드는 응답이다. "
        f"우리가 그리는 것은 **검출기가 쓰는 것과 같은 커널**이고, 검출기의 거리도플러 출력과 최대 "
        f"{L('detector_af_max_err_db.value', '{:.3f}', 'dB')} "
        f"({L('detector_af_max_err_db.n_cases', '{:.0f}')}개 경우, −45 dB 이상 셀) 안에서 같다. "
        f"코드: `benchmark/verify_ambiguity.py:150`, 검출기는 `src/passive_process.py:133`.",
        "",
        "### §4.1 주엽 — 닫힌형과 대조",
        "",
        f"거리 주엽은 $c/B_{{ref}}$ 예측의 {A('wifi_G1.dR_ratio', '{:.0%}')} ~ "
        f"{A('nr_G1.dR_ratio', '{:.0%}')} 다(G1 세 파형). 도플러 주엽은 여섯 경우 모두 "
        f"$1/T_{{CPI}}$ 의 {A('wifi_G1.dF_ratio', '{:.2f}')}배 근처이고, 이 배수는 파형이 아니라 "
        f"**slow-time Hann 창**이 정한다(`src/passive_process.py:142`).",
    ))

    blocks.append(_figblock(6, "report03_f6_af_mainlobe",
                            "측정한 모호함수 주엽이 닫힌형 예측과 몇 % 안에서 맞는가?",
                            caps["report03_f6_af_mainlobe"]))

    blocks.append(md(
        "### §4.2 부엽과 도플러 레플리카",
        "",
        "주엽 밖으로 새는 에너지는 두 가지로 나타난다. **부엽**은 강한 표적이 평면 다른 곳의 약한 "
        "표적을 덮는 정도이고, **±PRF 레플리카**는 무모호 속도를 넘은 표적이 되접혀 들어오는 세기다. "
        "이 표의 PRF 는 **검출기 프레임률**이고, 물리 주기 기준의 접힘은 §4.3 이 따로 잰다.",
        "",
        table(["기준신호", "2D 부엽 최대", "±PRF 레플리카", "프레임 내 시간점유", "함의"],
              [["WiFi VHT-LTF", A("wifi_G1.psl_2d_db", "{:.1f}", "dB"),
                A("wifi_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("wifi_G1.ref_time_duty", "{:.1%}"), "레플리카가 **무손실** — 접힘이 그대로 산다"],
               ["LTE CRS", A("lte_G1.psl_2d_db", "{:.1f}", "dB"),
                A("lte_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("lte_G1.ref_time_duty", "{:.1%}"), "부엽이 가장 높고 레플리카는 죽는다"],
               ["5G SSB", A("nr_G1.psl_2d_db", "{:.1f}", "dB"),
                A("nr_G1.doppler_replica_db", "{:.2f}", "dB"),
                A("nr_G1.ref_time_duty", "{:.1%}"), "부엽이 가장 낮고 레플리카는 거의 그대로 남는다"]]),
        "",
        "레플리카를 정하는 것은 점유율이 아니라 **에너지가 프레임 안에 얼마나 퍼져 있는가**다 — "
        "CRS 처럼 프레임 전체에 흩어지면 위상이 상쇄되고, LTF·SSB 처럼 앞쪽에 뭉치면 그대로 남는다.",
    ))

    blocks.append(_figblock(7, "report03_f7_af_sidelobe",
                            "각 기준신호는 표적 에너지를 부엽과 도플러 레플리카에 얼마나 남기는가?",
                            caps["report03_f7_af_sidelobe"]))

    blocks.append(md(
        "### §4.3 접힘 — 5G SSB 는 걷는 드론에서 접힌다",
        "",
        f"SSB 의 물리 반복률은 {A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 다. "
        f"무모호 도플러가 ±{A('nr_G1.physical.fd_unamb_phys_hz', '{:.0f}', 'Hz')} 라, 이 프로젝트의 "
        f"기준 표적 속도에서 참 도플러 {A('nr_G1.physical.fd_true_hz', '{:.1f}', 'Hz')} 가 "
        f"{A('nr_G1.physical.fd_aliased_phys_hz', '{:.1f}', 'Hz')} 로 접힌다. 같은 조건에서 "
        f"WiFi·LTE 는 참 도플러를 그대로 유지한다.",
        "",
        table(["기준신호", "물리 PRF", "무모호 속도", "접히는가"],
              [["WiFi VHT-LTF", A("wifi_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("wifi_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                A("wifi_G1.physical.aliased")],
               ["LTE CRS", A("lte_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("lte_G1.physical.v_unamb_phys_ms", "{:.1f}", "m/s"),
                A("lte_G1.physical.aliased")],
               ["5G SSB", A("nr_G1.physical.prf_physical_hz", "{:.0f}", "Hz"),
                A("nr_G1.physical.v_unamb_phys_ms", "{:.2f}", "m/s"),
                A("nr_G1.physical.aliased")]]),
        "",
        f"이것이 §1.1 이 말한 **두 배의 대가**의 나머지 절반이다 — 5G 는 좁아서 거리 눈금이 거칠고, "
        f"드물어서 속도 눈금이 접힌다. 접힘을 정하는 것은 물리 반복률 "
        f"{A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 하나이고, CPI 는 도플러 가드 폭을 "
        f"정한다 — 그 CPI 스윕은 05편이 싣는다.",
    ))

    # ── 논문 참고자료 부록 (PAPER_SPEC §4.2 · §4.4 · §4.5) ─────────────────── #
    blocks.append(paper_appendix(
        methods_block=methods(
            "Three illuminators of opportunity are modelled at the resource-grid level: IEEE "
            "802.11ac at 5.21 GHz with the VHT-LTF preamble as reference, 3GPP LTE Rel-9 at "
            "1.843 GHz with the cell-specific reference signal (CRS), and 3GPP 5G NR Rel-16 at "
            "3.5 GHz with the synchronisation signal block (SSB); the positioning reference "
            "signal is treated as a session-dependent option and reported separately. Grids are "
            "generated by src/waveforms.py following TS 36.211, TS 38.211 and IEEE 802.11ac-2013, "
            "and every waveform quantity is measured on the generated grid: the reference "
            "bandwidth B_ref is the end-to-end subcarrier span of the resource elements whose "
            "content is known a priori, giving B_ref = 76.6 MHz, 17.99 MHz and 7.2 MHz "
            "respectively, and range resolution follows the bistatic convention "
            "dR_b = c/B_ref (the monostatic c/2B is half of it). The modulation stage is scored "
            "against an independent implementation, sionna.phy.ofdm.OFDMModulator from Sionna "
            "2.0.1 on Python 3.12, reaching correlation 1.0000 and NMSE -135.2 dB on the "
            "full-load grid; a control that passes only the first cyclic-prefix length instead "
            "of the per-symbol array collapses the LTE and NR correlation to 0.06 and 0.05 and "
            "so establishes the resolving power of the comparison. Ambiguity functions are "
            "evaluated with the detector kernel itself over M = 48 slow-time frames under a "
            "Hann slow-time window and agree with the detector range-Doppler output to within "
            "0.144 dB over all cells above -45 dB. Every entry of the illuminator cost ledger is "
            "a ratio of two quantities taken on one target and one geometry, so the target radar "
            "cross-section cancels: carrier lambda^2 = -9.03 dB from LTE to WiFi and -5.57 dB "
            "from LTE to 5G, CPI convention = 3.01 dB, WiFi packet duty = -12.84 dB, and the 5G "
            "always-on occupancy cost = 18 dB read on a 6 dB EIRP grid with bracket 12 to 24 dB "
            "over 60 Monte-Carlo trials per grid point.",
            tools=["Sionna 2.0.1", "Python 3.12", "NumPy 2.5.0", "Matplotlib 3.11.0"],
            report=REPORT_KEY, sec="§6."),
        defence_block=defence([
            ("패시브 수신기가 상관에 쓸 수 있는 신호는 표준마다 상시 기준신호 하나다 — "
             "LTE CRS · 5G SSB · WiFi VHT-LTF.",
             "§1 표 · 그림 1 · `outputs/report2_waveform_rcs.json:reference.G1`",
             "PRS 를 켜면 5G 도 전대역을 쓴다. 왜 SSB 로 묶어 비교하나?",
             f"PRS 는 측위 세션이 설정될 때 켜지는 옵션이고, 남의 셀을 빌리는 수신기의 기본선은 "
             f"상시 SSB 다. PRS 체제(G2·G3)는 같은 그림에 함께 싣고 낙관적 상한으로 읽는다 — "
             f"$B_{{ref}}$ 가 {L('occupancy_cost.ref_bw_G1_mhz', '{:.1f}')} → "
             f"{L('occupancy_cost.ref_bw_G3_mhz', '{:.2f}', 'MHz')} 로 움직인다 "
             f"⟨outputs/report03_illuminators.json : occupancy_cost.ref_bw_G3_mhz⟩."),
            ("거리 분해능은 채널 대역이 아니라 기준신호 대역이 정한다 — "
             "$\\Delta R_b = c/B_{ref}$.",
             "§1 표 · 그림 2 · `outputs/report2_waveform_rcs.json:reference.G1.nr.dR_m`",
             f"5G 채널은 {W1('nr.chan_bw_mhz', '{:.1f}', 'MHz')} 인데 "
             f"{W1('nr.dR_m', '{:.1f}', 'm')} 라는 것은 과장이다.",
             f"채널 대역이 주는 {W1('nr.chan_dR_m', '{:.2f}', 'm')} 를 같은 그림에 병기했다 — 그 "
             f"값은 풀캡처 기준신호를 가진 체제의 값이고, 상시 SSB 체제의 값이 "
             f"{W1('nr.dR_m', '{:.1f}', 'm')} 다 "
             f"⟨outputs/report2_waveform_rcs.json : reference.G1.nr.chan_dR_m⟩."),
            ("점유 대가는 같은 표적·같은 기하에서 $P_d$ 0.5 를 넘기는 EIRP 차 "
             f"{L('occupancy_cost.value_db', '{:.0f}', 'dB')} 다.",
             "그림 4 · `outputs/report03_illuminators.json:occupancy_cost`",
             "EIRP 격자에서 읽은 값이라 유효숫자가 없다.",
             f"격자 눈금 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')}, 참값 구간 "
             f"[{L('occupancy_cost.bracket_lo_db', '{:.0f}')}, "
             f"{L('occupancy_cost.bracket_hi_db', '{:.0f}', 'dB')}], $P_d$ 선형보간 "
             f"{L('occupancy_cost.interp_db', '{:.1f}', 'dB')} 를 그림 4 의 구간막대와 표에 함께 "
             f"싣는다 ⟨outputs/report03_illuminators.json : occupancy_cost.interp_db⟩."),
            (f"이 격차에는 점유율과 기준신호 대역이 함께 들어 있고, 대역을 고정한 스윕이 두 항을 "
             f"가른다 (표적 {L('occupancy_cost.drone')} · "
             f"{L('occupancy_cost.scen')} · 시행 {L('occupancy_cost.n_trials', '{:.0f}')}회).",
             "§2.1 · `outputs/report03_illuminators.json:occupancy_cost.defn`",
             "그러면 18 dB 를 '점유 대가'라고 부르는 것이 잘못 아닌가?",
             f"18 dB 는 **상시 체제와 풀로드 체제의 차**이고 그 정의를 JSON 의 `defn` 에 박아 두었다. "
             f"대역만 분리한 값은 05편의 대역고정 스윕이 낸다 "
             f"⟨outputs/report03_illuminators.json : occupancy_cost.defn⟩."),
            (f"반송파 λ² 는 LTE→5G {L('lambda2.lte_to_nr_db', '{:.2f}', 'dB')} · "
             f"LTE→WiFi {L('lambda2.lte_to_wifi_db', '{:.2f}', 'dB')} 이고 반송파 정의에서 닫힌다.",
             "§2 표 · 그림 4 · `outputs/report03_illuminators.json:lambda2`",
             "수신 개구면적을 고정하면 부호가 뒤집힌다.",
             "EIRP 고정 · 수신 안테나 **이득** 고정 전제를 §2.1 에 명시했고 그 전제는 코드 한 줄"
             "(`src/freespace_link.py:371`)이다. 06편 측정 설계가 실제 안테나로 이 전제를 확정한다."),
            (f"모호함수는 검출기의 거리도플러 출력과 최대 "
             f"{L('detector_af_max_err_db.value', '{:.3f}', 'dB')} 안에서 같다.",
             f"그림 6 · 그림 7 · `outputs/verify_ambiguity.json:meta.detector_validation`",
             "모호함수를 따로 계산했다면 검출기와 다른 커널일 수 있다.",
             f"같은 커널로 계산했고, "
             f"{L('detector_af_max_err_db.n_cases', '{:.0f}')}개 (표준×점유) 경우에서 −45 dB 이상 "
             f"셀의 최대 편차를 재 그 값을 실었다 "
             f"⟨outputs/verify_ambiguity.json : meta.detector_validation⟩."),
            (f"SSB 물리 PRF {A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 가 무모호 속도를 "
             f"{A('nr_G1.physical.v_unamb_phys_ms', '{:.2f}', 'm/s')} 로 정한다.",
             "§4.3 표 · `outputs/verify_ambiguity.json:waveforms.nr_G1.physical`",
             "단일 CPI 에서 읽은 한 점이다.",
             f"접힘은 PRF 하나가 정한다 — TS 38.213 의 기본 SSB 주기가 물리 반복률을 "
             f"{A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')} 로 고정하고, 참 도플러 "
             f"{A('nr_G1.physical.fd_true_hz', '{:.1f}', 'Hz')} 가 "
             f"{A('nr_G1.physical.fd_aliased_phys_hz', '{:.1f}', 'Hz')} 로 접힌다. CPI 가 정하는 "
             f"것은 도플러 가드 폭이고 그 스윕은 05편이 싣는다 "
             f"⟨outputs/verify_ambiguity.json : waveforms.nr_G1.physical.fd_aliased_phys_hz⟩."),
            ("변조 단계는 Sionna PHY 독립 구현과 상관 1.0000 · NMSE −135 dB 로 일치한다.",
             f"§3.1 표 · 그림 5 · `outputs/report2_waveform_rcs.json:crosscheck`",
             "두 구현이 같은 오해를 공유하면 대조가 통과해도 의미가 없다.",
             f"심볼별 CP 배열 규칙을 뺀 대조군에서 LTE·5G 상관이 "
             f"{X('lte.corr_bug', '{:.2f}')} · {X('nr.corr_bug', '{:.2f}')} 로 무너진다 — 대조의 "
             f"분해력을 같은 표에 실어 그 반론에 미리 답한다 "
             f"⟨outputs/report2_waveform_rcs.json : crosscheck.nr.corr_bug⟩."),
        ], sec="§6.", report=REPORT_KEY),
        citations=[
            cite("3GPP", "Evolved Universal Terrestrial Radio Access (E-UTRA); Physical channels "
                         "and modulation", "3GPP TS 36.211 V17.1.0", year=2022,
                 status="standard", note="LTE CRS 자원요소 배치 — src/waveforms.py:313"),
            cite("3GPP", "NR; Physical channels and modulation", "3GPP TS 38.211 V17.1.0",
                 year=2022, status="standard",
                 note="SSB(PSS/SSS/PBCH) 및 PRS 배치 — src/waveforms.py:370"),
            cite("3GPP", "NR; Physical layer procedures for control", "3GPP TS 38.213 V17.1.0",
                 year=2022, status="standard", note="SSB 주기 20 ms 기본값"),
            cite("IEEE", "IEEE Standard for Information Technology, Part 11, Amendment 4: "
                         "Enhancements for Very High Throughput for Operation in Bands below "
                         "6 GHz", "IEEE Std 802.11ac-2013", year=2013, status="standard",
                 note="VHT-LTF 프리앰블 — src/waveforms.py:258"),
            cite("Hoydis, Cammerer, Ait Aoudia, Vem, Binder, Marcus, Keller",
                 "Sionna: An Open-Source Library for Next-Generation Physical Layer Research",
                 "arXiv preprint", year=2022, status="preprint", arxiv="2203.11854",
                 note="sionna.phy.ofdm.OFDMModulator — 이 편의 변조 대조 상대"),
            cite_ref("rzewuski",
                     note="WiFi 조명원 패시브 드론 검출의 게재 선례 — 우리는 같은 조명원 축을 "
                          "교정된 Pfa 위에서 세 파형으로 통제 비교한다"),
        ],
        sec="§6."))

    # ── 닫는 블록 ─────────────────────────────────────────────────────────── #
    blocks.append(next_steps([
        ("X410 으로 실제 셀을 캡처해 `src/waveforms.py` 의 격자와 대조한다",
         "CRS · SSB · VHT-LTF 의 격자 좌표가 실측으로 확정된다",
         "06편 측정 설계에 항목 추가"),
        (f"검출기 CPI {A('nr_G1.physical.cpi_model_ms', '{:.0f}', 'ms')} 를 스윕해 SSB 도플러 "
         f"가드 폭을 PRF 대비로 잰다",
         "5G 상시 기준신호의 접힘이 단일 CPI 결과인지 체제인지가 수치로 갈린다",
         "`outputs/cpi_guard_sweep.json` → 05편"),
        (f"`benchmark/run_min_cell.py:74` 의 `frame_len()` 을 물리 SSB 주기"
         f"({A('nr_G1.physical.prf_physical_hz', '{:.0f}', 'Hz')})로 확장한다",
         f"검출기 프레임률({A('nr_G1.physical.prf_model_hz', '{:.0f}', 'Hz')})과 "
         f"{A('nr_G1.physical.ratio', '{:.0f}')}배 벌어진 §4 표 전체가 한 규약 위에 선다",
         "`benchmark/verify_ambiguity.py:108`"),
        (f"EIRP 격자를 {L('occupancy_cost.eirp_grid_step_db', '{:.0f}', 'dB')} 에서 2 dB 로 좁히고 "
         f"기준신호 대역을 고정한 점유 스윕을 돌린다",
         f"{L('occupancy_cost.value_db', '{:.1f}', 'dB')} 안에서 점유 항과 대역 항의 크기가 갈린다",
         "`benchmark/run_matrix.py:300` → 05편"),
        (f"표적 {L('occupancy_cost.drone')} · 시나리오 {L('occupancy_cost.scen')} · 시행 "
         f"{L('occupancy_cost.n_trials', '{:.0f}')}회 한 점에서 읽은 점유 대가를 기체·기하로 넓힌다",
         "점유 대가가 표적·기하에 얼마나 의존하는지가 수치로 확정된다",
         "05편 검출 결과"),
        ("`src/waveforms.py:112` 의 `PILOT_RATE_HZ` 를 트래픽 시나리오 파라미터로 올린다",
         "WiFi PRF 가 유휴 AP ~ 혼잡 AP 범위로 확정되고 §1 표가 시나리오별로 선다",
         "`src/waveforms.py:112` → §1"),
        ("06편 측정 설계에서 수신 안테나를 확정하고 λ² 항의 전제를 다시 잰다",
         f"λ² {L('lambda2.span_db', '{:.2f}', 'dB')} 의 부호가 실제 안테나에서 확정된다",
         "`src/freespace_link.py:371` → 06편"),
    ], sec="§7."))

    return blocks


# =========================================================================== #
def main():
    led = build_ledger()
    REF = fetch((J_WAVE, "reference"))
    saved = {
        "report03_f1_grid": fig_grid(),
        "report03_f2_reference": fig_reference(REF, led),
        "report03_f3_occupancy": fig_occupancy(REF),
        "report03_f4_ledger": fig_ledger(led),
        "report03_f5_crosscheck": fig_crosscheck(),
        "report03_f6_af_mainlobe": fig_af_mainlobe(),
        "report03_f7_af_sidelobe": fig_af_sidelobe(),
    }
    caps = _paper_captions(saved)
    rep = build_notebook(NB, build_blocks(led, caps), strict=True)
    print(f"wrote {os.path.relpath(NB, ROOT)}  "
          f"(md {rep['md_cells']} · code {rep['code_cells']} · fig {rep['figures']})")
    return rep


if __name__ == "__main__":
    main()
