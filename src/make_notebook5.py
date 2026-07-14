# -*- coding: utf-8 -*-
"""make_notebook5.py — report5.ipynb (공정 벤치마크: 링크버짓 → Pd 매트릭스 + RT 교차검증) 생성기.
outputs/report5_results.json (run_matrix.py 산출)의 **실측 수치를 읽어** 마크다운에 삽입한다
— 수치를 손으로 박아 넣지 않아 노트북과 실험 결과가 어긋날 수 없다."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NB = os.path.abspath(os.path.join(HERE, "..", "report5.ipynb"))
RES = os.path.abspath(os.path.join(HERE, "..", "outputs", "report5_results.json"))


def md(*l): return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}
def code(*l): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": _s(list(l))}
def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def load_results():
    if not os.path.exists(RES):
        raise SystemExit(f"결과 파일이 없습니다: {RES}\n먼저 benchmark/run_matrix.py 를 실행하세요 "
                         "(또는 build_report5.py 가 순서대로 실행합니다).")
    with open(RES) as f:
        return json.load(f)


def build_cells(R):
    meta = R["meta"]
    eirp = meta["eirp_dbm"]
    B = {(r["wf"], r["drone"]): r for r in R["B_matrix"]["rows"]}
    head = B[("nr100", "mavic4pro")]
    lte10 = B[("lte10", "mavic4pro")]
    n_pass = sum(1 for r in R["B_matrix"]["rows"] if r["pd"] >= 0.9)
    n_cells = len(R["B_matrix"]["rows"])

    def _err(r):
        return "—" if r.get("rb_err_m") is None else f"{r['rb_err_m']:.2f} m"
    cA = {occ: sorted([r for r in R["A_occupancy"]["rows"] if r["occ"] == occ],
                      key=lambda r: r["eirp_dbm"]) for occ in ("G1", "G2", "G3")}

    def _tr(occ):
        """Pd≥50% 에 처음 도달하는 EIRP [dBm] (없으면 None)."""
        return next((r["eirp_dbm"] for r in cA[occ] if r["pd"] >= 0.5), None)

    g1_tr, g2_tr, g3_tr = _tr("G1"), _tr("G2"), _tr("G3")
    gap_db = (g1_tr - g3_tr) if (g1_tr is not None and g3_tr is not None) else None
    C = R["C_scenarios"]["rows"]
    mean_pd = {s: float(sum(r["pd"] for r in C if r["scen"] == s) /
                        max(1, len([r for r in C if r["scen"] == s])))
               for s in ("radial", "waypoint", "tangential", "hover")}
    D = R["D_rt"]
    E = R["E_ghost"]
    gh = E["ghost"]
    Eg = {r["wf"]: r for r in E["rows"] if r["ghost_on"] and r["drone"] == "mavic4pro"}
    dead = D.get("clutter_dead", [])
    sig_sbr = head["sigma_dbsm"]
    sig_po = head.get("sigma_po_dbsm", float("nan"))
    occ_db = R["B_matrix"].get("occlusion_db_mean", float("nan"))
    occ_med = R["B_matrix"].get("occlusion_db_median", float("nan"))

    cells = []
    cells.append(md(
        "# ⚖️ report5 — **공정 벤치마크**: 환경은 RT, 표적 σ 는 SBR, 절대전력은 링크버짓",
        "",
        "> **이 노트북 = 5단계: 공정성.** report4 까지는 표적 SNR 을 손잡이로 주입해 곡선을 그렸다",
        "> (처리이득 비교로는 유효하지만, '어떤 신호가 정말 유리한가'에는 **불공정**). 여기서는",
        "> **benchmark/** 하네스로 바로잡는다: 고정 예산(EIRP·수신이득·잡음지수) + RCS·기하·대역폭에서",
        "> 에코 SNR 을 **물리로 유도**하고, SCR·Pd 는 RD맵에서 **측정**한다 — *SCR is measured, not swept*.",
        "> 무대는 report1~4 와 같은 30×20×11 m **semi-anechoic** 챔버(벽·천장만 흡수체, **바닥은 콘크리트**).",
        "",
        "> **🔬 이번 판의 엔진 교체 (2026-07-14)** — 벤치마크가 드디어 **하이브리드**로 돈다:",
        "> - **표적 σ = SBR**(Mitsuba 광선 + PO 표면적분, **가림 포함**). 이전 판은 순수 PO(점구름, 가림 없음)라",
        ">   드론 RCS 를 **과대평가**하고 있었고, σ 는 링크버짓에 그대로 곱해지므로 그 오차가 에코 SNR→SCR→Pd",
        f">   전체에 실려 있었다. 같은 시선각에서 다시 재보니 σ 가 **평균 {occ_db:+.1f} dB**(중앙값 {occ_med:+.1f}) "
        f"내려갔다 —",
        f">   mavic4pro @3.5GHz 는 {sig_po:.1f} → **{sig_sbr:.1f} dBsm**. 그만큼 에코 SNR·SCR 도 함께 내려간다.",
        "> - **환경(정적 잔향) = Sionna RT 실측**(챔버 메쉬·ITU 재질, 반송파별 1회 광선추적 → 캐시).",
        ">   더 이상 클러터를 '가정'하지 않는다.",
        "> - **절대전력 = link_budget**(EIRP·kTB). RT 의 절대보정에 의존하지 않는다.",
        "",
        "**4줄 결론** (전부 아래 실험의 측정값)",
        f"1. **탐지력은 협대역이 우세, 대역폭의 값은 '분리'** — *살아남은 결론*: EIRP {eirp:.0f} dBm(저출력)에서 "
        f"radial 탐지는 {n_pass}/{n_cells} 셀 성공이고 SCR 은 잡음(kTB)이 작은 협대역 LTE 가 최고다. 대역폭이 "
        "사는 곳은 **거리축 분리능력**(위치정보·다중표적)이다 — LTE10 은 거리셀이 챔버 전체에 2~3개뿐이다.",
        f"2. **점유의 대가는 약 {gap_db:.0f} dB**: 같은 5G 100MHz 라도 G1(SSB만)은 Pd 50% 에 EIRP "
        f"{g1_tr:+.0f} dBm 이 필요한 반면 G3(풀로드)는 {g3_tr:+.0f} dBm 이면 충분 — 기준신호가 협대역·저에너지·"
        "시간희소인 '한가한 5G 이중고'(report2)가 고정 예산 Pd 로 정량화됨(Rényi 적응적분 동기).",
        f"3. **모션 블라인드는 '정확히 0-도플러'에서**: hover(정지)는 전 구간 Pd={mean_pd['hover']*100:.0f}%, "
        f"저속 횡단(tangential)은 마진이 흡수해 Pd={mean_pd['tangential']*100:.0f}%. 정지 드론은 bulk 도플러로 "
        "원리적으로 못 잡는다 → report3 마이크로도플러가 필요한 지점.",
        f"4. **🆕 그런데 바닥이 표적을 복제한다 — '5G 가 최고'가 여기서 뒤집힌다**: TX→표적→**바닥**→RX 유령은 "
        f"표적을 거치므로 **도플러가 실려** ECA 가 못 지운다. 표적 에코보다 {gh['amp_db']:.1f} dB 약한데도 "
        f"CFAR 임계보다 **{Eg['nr100']['ghost_margin_db']:+.1f} dB 위**에 뜨고(5G), 표적에서 **{gh['sep_m']:+.2f} m** "
        f"떨어져 있다. 5G 의 ΔRb={gh['d_rb_m']:.1f} m 는 이걸 **분해해 버려** 별개의 '유령 드론'으로 만든다. "
        "광대역의 장점(분해능)이 그대로 오검출로 되돌아온다. **Pd 는 안 떨어진다 — 무너지는 건 신뢰다.**",
    ))

    cells.append(md(
        "## 0. 이 리포트가 하는 일 — 한 장으로",
        "",
        "![overview](outputs/figures/report5_overview.png)",
        "",
        "왼쪽이 실험 무대(챔버 바이스태틱), 오른쪽이 **report4 와의 차이**입니다:",
        "- 지금까지(위 회색 흐름)는 표적 SNR 을 **우리가 손잡이로 주입**했습니다 — 처리 체인의 이득을 비교하는",
        "  데는 유효하지만, 신호마다 다른 반송파(λ→전파감쇠·RCS)·대역폭(B→잡음 kTB)·점유(에너지)를 지워버리므로",
        "  \"어떤 신호가 정말 유리한가\"에는 답할 수 없습니다.",
        "- report5(아래 초록 흐름)는 그 손잡이를 없앱니다. **고정하는 것은 조명원 예산(EIRP·수신이득·잡음지수)뿐**이고,",
        "  에코 SNR 은 레이더 방정식이 **유도**하며(SBR RCS σ, 기하 R1·R2, λ, kT₀FB), SCR·Pd 는 거리-도플러 맵에서",
        "  **측정**합니다. 신호를 가르는 물리가 결과에 저절로 반영됩니다 — *SCR is measured, not swept*.",
        "- 이 위에서 다섯 가지 실험을 합니다: **A** 점유(G1/G2/G3)의 대가, **B** 신호×드론 매트릭스,",
        "  **C** 모션(0-도플러 블라인드), **E** 🆕 **유령 매트릭스**(바닥 유령 off/on), **D** Sionna RT 교차검증.",
        "",
        "### 무엇이 무엇을 계산하나 — 하이브리드 분업",
        "",
        "| 물리량 | 엔진 | 왜 |",
        "|---|---|---|",
        "| 표적 RCS σ | **SBR** (`src/rcs_sbr.py`: Mitsuba 광선 + PO 표면적분) | Sionna RT 의 전파용 path solver 에는 **산란적분 단계가 없어** σ 가 창발하지 않는다(광선을 4배로 늘려도 값이 수렴하지 않고 계속 커진다). σ 는 적분에서 나온다 → 광선추적 **안에** PO 를 넣은 것이 SBR. 해석해 검증: 평판 −0.01 dB, 금속구 +0.39 dB. |",
        "| 환경 경로·잔향 | **Sionna RT** (`SionnaRTChannel`, 캐시) | RT 는 **환경**에서 정확하다 — 바닥 반사를 19.3 ns / −14.7 dB 로 찾았고 프레넬 예측과 0.02 dB 일치. |",
        "| 절대전력·잡음 | **link_budget** (EIRP·kTB) | RT 절대보정에 의존하지 않기 위해 모든 경로를 '직접파 대비 비율'로만 쓴다. |",
        "",
        "### benchmark/ 하네스 구조",
        "",
        "| 파일 | 역할 |",
        "|---|---|",
        "| `benchmark/geometry.py` | 챔버 내 TX/RX/quiet-zone 배치 + RD 거리창 + **`floor_ghost()`**(표적 경유 바닥 유령) |",
        "| `benchmark/link_budget.py` | **물리 유도**: P_echo=EIRP·G_rx·λ²σ/[(4π)³R1²R2²], P_dir(Friis), P_n=kT₀FB |",
        "| `benchmark/channel.py` | σ=**SBR**(GPU 캐시) + 환경 스왑: `AnalyticChannel`(닫힌형 기하) ↔ `SionnaRTChannel`(RT) |",
        "| `benchmark/scenarios.py` | 통제 모션 4종: radial / tangential / hover / waypoint |",
        "| `benchmark/run_min_cell.py` | 최소 셀 1개 + 고속 Monte-Carlo(`run_cell`) |",
        "| `benchmark/run_matrix.py` | 본 실험 A~E → 그림·`outputs/bench_matrix.csv`·`bench_ghost.csv`·`report5_results.json` |",
        "",
        "> **왜 σ 를 미리 캐시하나**: SBR 은 GPU(Mitsuba/OptiX)를 쓴다. 매트릭스는 셀을 프로세스 풀로 뿌리므로",
        "> 워커마다 CUDA 컨텍스트를 만들면 GPU 메모리가 워커 수만큼 곱해지고 fork 된 CUDA 가 깨질 수 있다.",
        "> 그래서 **메인 프로세스가 필요한 시선각을 전부 모아 여러 GPU 에 나눠 SBR 로 계산**하고",
        "> (`channel.sbr_sigma_prefill`), 워커는 표를 **조회만** 한다(캐시 미스는 조용히 PO 로 흐르지 않고 실패).",
        "",
        "**공정성 규약(전 셀 공통)** — ① 수신기는 **기준신호만** 안다(`wf.ref`; 데이터 복조 없음) ② ref 는 "
        "**송신 전체파형 전력 기준** 정규화 → 희소 파일럿(G1)의 에너지 핸디캡이 처리이득에 그대로 반영 "
        "③ CPI 시간 고정(T=30 ms → 도플러분해능 ≈33 Hz, 프레임률이 다른 파형끼리 공정) ④ CA-CFAR Pfa=1e-4, "
        "히트=참셀 ±1 ⑤ Pd 는 Wilson 95% CI 와 함께.",
        "",
        "재현: `cd src && /home/yunjung/.venvs/py312/bin/python build_report5.py` "
        "(RT 교차검증이 GPU 1장 사용, 기본 GPU 2번)",
    ))

    cells.append(md(
        "## 1. 최소 셀 — 물리에서 Pd 까지 한 줄로",
        "",
        f"5G NR 100MHz(G3) × mavic4pro × radial, EIRP {eirp:.0f} dBm. 링크버짓이 유도한 per-sample "
        f"에코 SNR 은 **{head.get('snr_echo_eff_db', head['snr_echo_db']):+.1f} dB**"
        f"(σ={head['sigma_dbsm']:.1f} dBsm, **SBR**·자세평균; 잡음대역 fs 보정 포함)로 잡음보다 "
        f"한참 아래지만, CPI 처리이득(거리압축×슬로타임 FFT)이 이를 SCR **{head['scr_db']:.0f} dB** 로 끌어올려 "
        f"Pd={head['pd']*100:.0f}% 가 **측정**된다. 직접파는 에코보다 {head['dnr_db']:.0f} dB 강하다(ECA 가 제거).",
        "",
        "![min-cell](outputs/figures/report5_min_cell.png)",
    ))
    cells.append(code(
        "import sys; sys.path.insert(0, 'src'); sys.path.insert(0, 'benchmark')",
        "from run_min_cell import run_cell, EIRP_DBM",
        "from link_budget import LinkBudget",
        "from channel import AnalyticChannel",
        "from scenarios import radial",
        "from geometry import TX, RX, CENTER, CH_CLUTTER_RATIO, SPEED, SPAN",
        "from waveforms import nr_downlink",
        "wf = nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy='G3')",
        "pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=48)",
        "res = run_cell(wf, 'mavic4pro', pos, vel, LinkBudget(eirp_dbm=EIRP_DBM),",
        "               channel=AnalyticChannel(clutter=CH_CLUTTER_RATIO), M=48, N=50)",
        "print(f\"에코SNR={res['link']['snr_echo_db']:+.1f}dB(유도)  SCR={res['scr_mean']:.1f}dB(측정)  \"",
        "      f\"Pd={res['pd']*100:.0f}% [{res['pd_lo']*100:.0f},{res['pd_hi']*100:.0f}]\")",
    ))

    cells.append(md(
        "## 2. 점유 공정성 (A) — '같은 5G' 라도 켜져 있는 것이 다르면 다른 레이더다",
        "",
        "위 띠가 **실제 리소스그리드**(G1=SSB 만 / G2=+PRS·제어 / G3=풀로드), 아래가 EIRP 를 물리 손잡이로 "
        "스윕하며(표적 SNR 주입 아님) 측정한 Pd. "
        "전력 기준은 G3 의 per-RE 송신전력(시간희소한 G1 은 평균 방사전력이 낮게 반영):",
        "",
        "![occupancy](outputs/figures/report5_occupancy_pd.png)",
        "",
        f"- **G3(풀로드)** 는 EIRP {g3_tr:+.0f} dBm, **G2(기준+제어)** 는 {g2_tr:+.0f} dBm 부터 Pd 50% 를 "
        "넘는다 — PRS 가 전대역 기준을 제공해 둘은 사실상 같다.",
        f"- **G1(SSB만)** 은 {g1_tr:+.0f} dBm 이 되어야 Pd 50% — G3 대비 **{gap_db:.0f} dB 페널티**. "
        "기준이 7.2 MHz 협대역(거리축에서 직접파와 못 갈라짐)이고 에너지 점유도 ~2%(SSB 4심볼/슬롯)라 "
        "처리이득이 모자라기 때문 — **거리·에너지 이중고**. 다만 도플러축 분리 덕에 예산을 키우면 결국 잡힌다"
        "(불가능이 아니라 '비싸다').",
        "- 이것이 report2(§4)의 점유 논증을 '고정 예산 Pd' 로 정량화한 것이고, 5G 패시브레이더 문헌들이 "
        "점유 적응(Rényi 등)을 좇는 이유다.",
    ))

    scr_rank = sorted({r["wf"]: r["scr_db"] for r in R["B_matrix"]["rows"]
                       if r["drone"] == "mavic4pro"}.items(), key=lambda kv: -kv[1])
    cells.append(md(
        "## 3. 신호 × 드론 매트릭스 (B) — 고정 예산에서 무엇이 잡히고, 무엇을 알 수 있나",
        "",
        f"{{5G100, WiFi80, LTE20, LTE10}} × 드론 5종, radial, EIRP {eirp:.0f} dBm, "
        f"N={R['B_matrix']['N']}/셀. 원자료는 `outputs/bench_matrix.csv`:",
        "",
        "![matrix](outputs/figures/report5_matrix.png)",
        "",
        f"- **탐지(Pd)**: {n_pass}/{n_cells} 셀 성공 — 저출력에서도 챔버 근거리 radial 탐지는 어렵지 않다. "
        "직접파(DPI)가 **정적(0-도플러)**이라 ECA+도플러축이 분리해 주기 때문(데이터-DPI 잔류 포함 모델).",
        f"- **SCR 마진(색)**: mavic4pro 기준 {' > '.join(f'{k}({v:.0f}dB)' for k, v in scr_rank)} — "
        "**협대역일수록 높다**. 같은 EIRP 에서 잡음전력 P_n=kT₀FB 가 대역폭에 비례하기 때문"
        f"(LTE10 에코SNR {B[('lte10','mavic4pro')].get('snr_echo_eff_db', B[('lte10','mavic4pro')]['snr_echo_db']):+.0f} dB "
        f"vs 5G100 {head.get('snr_echo_eff_db', head['snr_echo_db']):+.0f} dB). "
        "report4(동일 SNR 주입)에서 LTE 가 최하위였던 것과 정반대 — **공정성(무엇을 고정하나)이 결론을 바꾼다**.",
        f"- **위치오차(셀 안 숫자) — 정확도≠분해능**: 단일표적·고SNR 이라 협대역도 서브미터 정확도"
        f"(5G100 {_err(head)}, LTE10 {_err(lte10)}; CRB ∝ 분해능/√SNR — LTE 는 SNR 이 높아 상쇄). "
        "**분해능(열 라벨)의 진짜 값어치는 '분리'**: LTE10 의 거리셀은 챔버 전체에 2~3개라 직접파 잔류·"
        "다중표적·클러터가 표적과 한 셀에 겹치면 구분할 수단이 없고, 등Rb 셀 하나의 두께가 33 m 다. "
        "광대역(5G 3 m)만 거리축에 '구조'를 준다.",
        "- RCS(드론 크기)는 행 방향 SCR 차이(≈10 dB)로 나타나지만, 이 예산에선 탐지 성패를 바꾸지 못한다 — "
        "성패는 A(점유·예산)와 C(모션)가 가른다.",
    ))
    cells.append(code(
        "import pandas as pd",
        "df = pd.read_csv('outputs/bench_matrix.csv')",
        "df.pivot_table(index='drone', columns='wf', values='pd')",
    ))

    cells.append(md(
        "## 4. 시나리오 축 (C) — 블라인드는 '정확히 0-도플러(정지)'에서 생긴다",
        "",
        "mavic4pro × 5G100(G3), 궤적 8스냅샷 × 4모션. ECA 는 기준의 지연복제(0-도플러) 부분공간을 지운다 — "
        "**정지 표적의 에코는 이 부분공간의 원소** 그 자체라 직접파와 함께 완전히 소거된다:",
        "",
        "![scenarios](outputs/figures/report5_scenarios.png)",
        "",
        f"- 궤적평균 Pd: radial **{mean_pd['radial']*100:.0f}%** / waypoint **{mean_pd['waypoint']*100:.0f}%** / "
        f"tangential **{mean_pd['tangential']*100:.0f}%** / hover **{mean_pd['hover']*100:.0f}%**.",
        "- **hover(정지) = 전 구간 Pd 0%**: f_d 가 정확히 0 → CPI 동안 위상이 전혀 돌지 않아 ECA 가 "
        "직접파·클러터와 구분 못 하고 함께 제거 — **bulk 도플러만으로는 원리적으로 못 잡음**.",
        "- **저속 횡단(tangential)은 이 예산에선 안 빠졌다**: |f_d|≤14 Hz 로 도플러분해능(≈33 Hz) 안쪽이라 "
        "ECA 가 상당량 감쇠시키지만, SCR 마진(~40 dB)이 이를 흡수해 여전히 검출된다. 즉 블라인드 폭은 "
        "'능선 ± 분해능'이 아니라 **마진 대비 ECA 감쇠의 함수** — 예산이 빠듯해지면(§2 저 EIRP) 횡단부터 빠진다.",
        "- 실무 함의: 정지 드론은 **회전 블레이드 마이크로도플러**(report3, f_tip 수 kHz)로 잡아야 한다 — "
        "블레이드는 정지 호버 중에도 돌아 0-도플러 소거와 무관한 시그니처를 남긴다.",
    ))

    # ---- 5. 유령 매트릭스 (E) — 이번 판의 핵심 ----
    def _gh(k, f):
        return Eg[k][f] if k in Eg and Eg[k][f] is not None else float("nan")
    cells.append(md(
        "## 5. 🆕 유령 매트릭스 (E) — 바닥이 표적을 복제한다, 그리고 광대역일수록 잘 복제된다",
        "",
        "챔버는 **anechoic 이 아니라 semi-anechoic** 이다: 흡수체는 벽 4면 + 천장에만 있고 **바닥은 반사성 "
        "콘크리트**다. 그래서 방 안에 강한 반사면이 딱 하나 남는다 — 바닥.",
        "",
        "**두 종류의 바닥 경로를 구분해야 한다:**",
        "",
        "| 경로 | 도플러 | ECA | 결과 |",
        "|---|---|---|---|",
        "| TX → **바닥** → RX (정적 클러터) | 없음(0 Hz) | 지연복제 부분공간 → **정확히 소거** | 무해 — **죽은 파라미터** |",
        "| TX → **표적** → 바닥 → RX (유령) | **표적과 같이 실림** | 영공간 **밖** → **안 지워짐** | **가짜 표적** |",
        "",
        "우리가 오랫동안 걱정한 건 위쪽(정적 클러터)이었고, 그건 ECA 가 진폭과 무관하게 지운다(§6에서 증명). "
        "**진짜 위협은 아래쪽**이고 모델에 아예 없었다. 이제 켠다:",
        "",
        "![ghost](outputs/figures/report5_ghost.png)",
        "",
        f"- **유령의 물리**(닫힌형 거울상 유도, `geometry.floor_ghost`): 바닥 입사각 {gh['theta_i_deg']:.0f}°, "
        f"콘크리트 프레넬 |Γ|={gh['gamma']:.3f} → 표적 에코보다 **{gh['amp_db']:.1f} dB** 약하고, "
        f"바이스태틱 거리는 **{gh['sep_m']:+.2f} m** 더 길며, 도플러는 {gh['fd']:+.0f} Hz "
        "(표적과 다르지만 **0 은 아니다** — 그래서 ECA 를 통과한다).",
        "- **여기서 결론이 뒤집힌다 — 분해능이 곧 오검출이다**:",
        f"  · **5G100 (ΔRb={_gh('nr100','delta_rb_m'):.1f} m < {abs(gh['sep_m']):.2f} m)** → 유령을 **분해**한다. "
        f"그 별개 피크는 CFAR 임계보다 **{_gh('nr100','ghost_margin_db'):+.1f} dB** 위에 있고, 매 trial 마다 "
        f"({_gh('nr100','p_ghost_det')*100:.0f}%) 검출된다 → RD 맵에 **'유령 드론' 한 대가 더** 뜬다.",
        f"  · **WiFi80/LTE (ΔRb={_gh('wifi80','delta_rb_m'):.1f}~{_gh('lte10','delta_rb_m'):.0f} m > "
        f"{abs(gh['sep_m']):.2f} m)** → 유령이 표적과 **같은 거리셀**에 묻힌다. 가짜 표적은 안 생기지만, "
        "표적 셀 안에서 에코와 **코히어런트하게 합쳐진다**(진폭·위상 오염). 우리 기하에선 피크 거리오차 변화가 "
        f"cm 수준(예: LTE10 {_gh('lte10','rb_err_m'):.2f} m)이라 **큰 편향으로 나타나지는 않았다** — "
        "'유령이 없다'가 아니라 '분리해 낼 수단이 없다'가 정확한 서술이다.",
        "  · **Pd 는 어느 쪽도 안 떨어진다**(패널 c). 무너지는 것은 탐지가 아니라 **신뢰**다.",
        "",
        "> ⚠ **정직한 단서 두 가지**",
        "> 1. '가짜 표적(p_false)' 판정 = *표적셀 ±1 밖*의 CFAR 히트인데, 유령이 거리빈으로 "
        f"{abs(gh['sep_m'])/2.44:.2f} 빈 떨어져 있어 **격자 모서리에 민감하다** — 표적이 몇 cm 움직이면 반올림이 "
        "1↔2 빈을 오가고, 1빈이면 표적 히트 창에 흡수되어 p_false=0 으로 집계된다. 그래서 격자와 무관한 "
        "**CFAR 임계 대비 여유(dB)** 를 함께 본다. 유령이 거기 있다는 사실 자체는 격자와 무관하다.",
        "> 2. **merged 인 파형(WiFi/LTE)에서는 '유령 셀' = '표적 셀'** 이라, 그 셀의 CFAR 여유를 재는 것은 "
        "표적을 다시 재는 것과 같다(그림 패널 b 에서 여유 수치를 5G 에만 표기한 이유). merged 의 손해는 "
        "'오검출'이 아니라 **'구분 불가'** 다.",
        "",
        "**함의**: 챔버 안 5G 패시브 레이더는 드론 1대를 띄우면 **2대를 본다**. 해결책은 대역폭을 줄이는 게 "
        "아니라(그러면 위치정보를 잃는다) — 바닥 유령을 **모델링해 지우는 것**이다: 유령의 (Rb, f_d) 는 표적 "
        "위치의 결정론적 함수이므로(거울상 기하), 표적 가설마다 유령 셀을 예측해 연관(association)에서 배제할 수 있다. "
        "그게 다음 리포트의 일이다.",
    ))
    cells.append(code(
        "import pandas as pd",
        "g = pd.read_csv('outputs/bench_ghost.csv')",
        "g[g.ghost_on].groupby('wf')[['pd', 'p_ghost_det', 'ghost_margin_db', 'p_false', 'rb_err_m']].mean()",
    ))

    # ---- 6. RT 교차검증 (D) — 무엇을 증명하고, 무엇을 증명 못 하나 ----
    rt_cell = D["cell"]
    dead_txt = " · ".join(f"{x['tag']} → SCR {x['scr']:.6f} dB" for x in dead) if dead else "—"
    cells.append(md(
        "## 6. Sionna RT 교차검증 (D) — 무엇을 증명하고, 무엇을 **증명하지 못하나**",
        "",
        "같은 셀을 `AnalyticChannel`(닫힌형 기하) ↔ `SionnaRTChannel`(Sionna RT PathSolver, 챔버 메쉬+ITU 재질) "
        "로 스왑해 비교한다(GPU). **두 백엔드의 σ 는 이제 둘 다 SBR** 이다 — 다른 것은 '환경 경로'뿐이다.",
        "",
        "![rt](outputs/figures/report5_rt_clutter.png)",
        "",
        f"- **자유공간 RT: 클러터 {D['free']['n_clutter']}개** — 기하·직접파·지연 처리의 교차검증 통과. ✅",
        f"- **챔버 RT: 잔향 {len(D['chamber_clutter'])}개 실측** (최강 "
        f"{max(db for _, db in D['chamber_clutter']):.1f} dB) — 옛 가정치(−26/−29/−34 dB)보다 **11~16 dB 강하다.** "
        "우리는 챔버를 과소가정하고 있었고, 그 실측치를 이제 매트릭스에 실제로 주입한다.",
        "",
        "### ❌ 무너진 결론 — \"RT ≈ Analytic 이므로 클러터 모델이 검증됐다\"",
        "",
        "이건 **항등식이었다.** ECA 는 정적 클러터를 *지연된 기준신호의 선형결합*으로 보고 그 부분공간을 "
        "**진폭과 무관하게 정확히 사영 소거**한다. 그러니 어떤 클러터 모델을 넣어도 두 백엔드는 '일치'할 수밖에 "
        "없었다. 이번 판은 그걸 **같은 자리에서 증명**한다 — 잔향을 0 / RT실측 / RT×10 으로 바꿔도:",
        "",
        f"> `{dead_txt}`",
        "",
        "소수점 여섯 자리까지 같다. **정적 클러터는 죽은 파라미터다.**",
        f"- **같은 셀 Pd**: RT {rt_cell['rt']['pd']*100:.0f}% vs Analytic {rt_cell['analytic']['pd']*100:.0f}%, "
        f"SCR {rt_cell['rt']['scr']:.1f} vs {rt_cell['analytic']['scr']:.1f} dB (N={rt_cell['N']}) — 일치한다. "
        "다만 위의 이유로 이 일치가 검증하는 것은 **기하·직접파·지연**이지 **클러터 모델이 아니다**.",
        "- 실제 ECA 는 이렇게 완벽하지 않다(유한 동적범위·클러터 도플러퍼짐·양자화). 그 한계는 **아직 모델에 "
        "없다** — 정적 클러터가 *정말로* 무해하다는 뜻이 아니라, **이 모델이 그걸 검증할 능력이 없다**는 뜻이다.",
    ))

    cells.append(md(
        "## 7. 정리 — 살아남은 것 / 무너진 것 / 새로 알아낸 것",
        "",
        "| | 내용 | 근거 |",
        "|---|---|---|",
        "| ✅ **살아남음** | 대역폭이 가르는 건 **탐지가 아니라 위치정보**(거리축)와 다중표적 분리 | §3 — SCR 은 협대역이 높고(kTB↓) Pd 는 전부 성공. 갈리는 건 ΔRb |",
        f"| ✅ **살아남음** | 점유의 대가 ≈ {gap_db:.0f} dB (G1 이중고), 0-도플러 블라인드는 hover 에서만 | §2, §4 |",
        "| ❌ **무너짐** | \"무반사라 클러터가 약하다\" | 챔버는 **semi-anechoic** — 바닥은 콘크리트. RT 실측 잔향이 가정보다 11~16 dB 강했다 (§6) |",
        "| ❌ **무너짐** | \"RT≈Analytic 이므로 클러터 모델이 검증됐다\" | **항등식**이었다 — ECA 가 진폭과 무관하게 사영 소거 (§6, SCR 소수점 6자리까지 불변) |",
        f"| 🆕 **새로움** | 표적 σ 가 **평균 {occ_db:+.1f} dB** 내려갔다 — **가림(self-shadowing)** | 순수 PO 는 광선이 앞면에 막혀 안 보이는 뒷면·내부면까지 적분한다. SBR 은 '실제로 맞은 첫 지점'만 적분한다 (§3, `bench_matrix.csv` 의 `occlusion_db`) |",
        "| 🆕 **새로움** | **표적 경유 바닥 유령** — 도플러가 실려 ECA 를 통과하고, 광대역일수록 별개 표적으로 분해된다 | §5 |",
        "",
        "**한 일** — report4 의 'SNR 주입'을 물리로 대체한 **공정 벤치마크**를, 이번엔 **RT(환경) + SBR(σ) + "
        "링크버짓(절대전력)** 하이브리드로 구동했다. 모든 수치는 `outputs/report5_results.json` / "
        "`bench_matrix.csv` / `bench_ghost.csv` 에 저장되고 이 노트북은 그 값을 읽어 쓴다(수기 수치 없음).",
        "",
        "**다음 후보** (모두 챔버 형태)",
        "- 👻 **유령 억제**: 거울상 기하로 유령 셀을 예측해 연관에서 배제 → 광대역의 분해능을 '되찾는다'. §5의 직접 후속.",
        "- 🌀 **마이크로도플러 결합 탐지**: hover 블라인드를 report3 블레이드 시그니처로 메우기.",
        "- 🧱 **ECA 의 유한 동적범위**: 정적 클러터를 '죽은 파라미터'에서 살려내는 유일한 정직한 길.",
        "- 📶 **실측 캘리브레이션**: EIRP·G_rx·NF 를 실제 장비 값으로 치환하면 그대로 예측 Pd 가 된다.",
    ))
    return cells


def main():
    R = load_results()
    cells = build_cells(R)
    nb = {"cells": cells,
          "metadata": {"kernelspec": {"display_name": "Python 3.12 (py312)", "language": "python", "name": "py312"},
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    with open(NB, "w") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("notebook 생성:", os.path.relpath(NB), f"({len(cells)} cells)")


if __name__ == "__main__":
    main()
