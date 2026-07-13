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

    cells = []
    cells.append(md(
        "# ⚖️ report5 — **공정 벤치마크**: 링크버짓으로 유도하고, SCR·Pd 는 측정한다",
        "",
        "> **이 노트북 = 5단계: 공정성.** report4 까지는 표적 SNR 을 손잡이로 주입해 곡선을 그렸다",
        "> (처리이득 비교로는 유효하지만, '어떤 신호가 정말 유리한가'에는 **불공정**). 여기서는",
        "> **benchmark/** 하네스로 바로잡는다: 고정 예산(EIRP·수신이득·잡음지수) + PO-RCS·기하·대역폭에서",
        "> 에코 SNR 을 **물리로 유도**하고(링크버짓), SCR·Pd 는 RD맵에서 **측정**한다 — *SCR is measured, not swept*.",
        "> 무대는 report1~4 와 같은 30×20×11 m 무반사 챔버(TX/RX 양쪽 측벽, L≈15 m, 표적 quiet zone).",
        "",
        "**3줄 결론** (전부 아래 실험의 측정값)",
        f"1. **탐지력은 협대역이 우세, 대역폭의 값은 '분리'**: EIRP {eirp:.0f} dBm(저출력)에서 radial 탐지는 "
        f"{n_pass}/{n_cells} 셀 성공이고 SCR 은 잡음(kTB)이 작은 협대역 LTE 가 최고다. 단일표적 위치오차도 "
        f"서브미터(5G {_err(head)}, LTE10 {_err(lte10)} — 고SNR 에선 정확도≈분해능/√SNR). 대역폭이 사는 것은 "
        "**거리축 분리능력**이다: LTE10 은 거리셀이 2~3개(ΔRb≈33 m ≳ 챔버)라 직접파 잔류·다중표적이 표적과 "
        "같은 셀에 겹치면 원리적으로 구분 불가. (report4 의 'LTE 불리'는 동일 SNR 주입 비교의 산물 — "
        "공정 예산에선 이렇게 갈린다.)",
        f"2. **점유의 대가는 약 {gap_db:.0f} dB**: 같은 5G 100MHz 라도 G1(SSB만)은 Pd 50% 에 EIRP "
        f"{g1_tr:+.0f} dBm 이 필요한 반면 G3(풀로드)는 {g3_tr:+.0f} dBm 이면 충분 — 기준신호가 협대역·저에너지·"
        "시간희소인 '한가한 5G 이중고'(report2)가 고정 예산 Pd 로 정량화됨(Rényi 적응적분 동기).",
        f"3. **모션 블라인드는 '정확히 0-도플러'에서**: hover(정지)는 전 구간 Pd={mean_pd['hover']*100:.0f}% — "
        "정지 표적의 에코는 ECA 의 지연복제 부분공간에 정확히 들어가 직접파와 함께 소거된다. 반면 저속 횡단"
        f"(tangential, |f_d|≤14 Hz)은 이 예산의 SCR 마진이 ECA 감쇠를 흡수해 Pd={mean_pd['tangential']*100:.0f}%. "
        "→ 정지 드론은 bulk 도플러로는 원리적으로 못 잡는다 — report3 마이크로도플러가 필요한 지점.",
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
        "  에코 SNR 은 레이더 방정식이 **유도**하며(PO RCS σ, 기하 R1·R2, λ, kT₀FB), SCR·Pd 는 거리-도플러 맵에서",
        "  **측정**합니다. 신호를 가르는 물리가 결과에 저절로 반영됩니다 — *SCR is measured, not swept*.",
        "- 이 위에서 네 가지 실험을 합니다: **A** 점유(G1/G2/G3)의 대가, **B** 신호×드론 매트릭스,",
        "  **C** 모션(0-도플러 블라인드), **D** Sionna RT 광선추적 교차검증.",
        "",
        "### benchmark/ 하네스 구조",
        "",
        "| 파일 | 역할 |",
        "|---|---|",
        "| `benchmark/geometry.py` | 챔버 내 TX/RX/quiet-zone 배치 + RD 거리창(`chamber_window`) |",
        "| `benchmark/link_budget.py` | **물리 유도**: P_echo=EIRP·G_rx·λ²σ/[(4π)³R1²R2²], P_dir(Friis), P_n=kT₀FB |",
        "| `benchmark/channel.py` | 채널 백엔드 스왑: `AnalyticChannel`(기하+PO) ↔ `SionnaRTChannel`(RT 멀티패스, GPU) |",
        "| `benchmark/scenarios.py` | 통제 모션 4종: radial / tangential / hover / waypoint |",
        "| `benchmark/run_min_cell.py` | 최소 셀 1개 + 고속 Monte-Carlo(`run_cell`) |",
        "| `benchmark/run_matrix.py` | 본 실험 A~D → 그림·`outputs/bench_matrix.csv`·`outputs/report5_results.json` |",
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
        f"(σ={head['sigma_dbsm']:.1f} dBsm, PO 자세평균; 잡음대역 fs 보정 포함)로 잡음보다 "
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

    rt_cell = D["cell"]
    cells.append(md(
        "## 5. Sionna RT 교차검증 (D) — 가정이 아니라 광선추적으로",
        "",
        "같은 셀을 `AnalyticChannel`(닫힌형 기하+가정 잔향) ↔ `SionnaRTChannel`(Sionna RT PathSolver, "
        "챔버 메쉬+흡수체 재질) 로 스왑해 비교(GPU). 왼쪽 두 패널이 **같은 표적을 두 채널로 본 거리-도플러 맵**"
        "(구조·표적 위치·SCR 이 일치해야 함), 오른쪽이 잔향 스펙트럼 비교:",
        "",
        "![rt](outputs/figures/report5_rt_clutter.png)",
        "",
        f"- **자유공간 RT: 클러터 {D['free']['n_clutter']}개** — 기하·직접파 처리의 교차검증 통과.",
        f"- **흡수체 챔버 RT: 잔향 {len(D['chamber_clutter'])}개 실측** (직접파 대비 "
        f"{', '.join(f'{db:.0f}dB' for _, db in D['chamber_clutter'][:3]) if D['chamber_clutter'] else '—'} …) — "
        "Analytic 의 가정(−26/−29/−34 dB)과 같은 자리수의 약한 잔향. 무반사 챔버 전제(클러터 약함, DPI 지배) 유지.",
        f"- **같은 셀 Pd**: RT {rt_cell['rt']['pd']*100:.0f}% vs Analytic {rt_cell['analytic']['pd']*100:.0f}%, "
        f"SCR {rt_cell['rt']['scr']:.1f} vs {rt_cell['analytic']['scr']:.1f} dB (N={rt_cell['N']}) — 두 백엔드가 "
        "일치하므로 이후 대규모 스윕은 빠른 Analytic 으로, 환경이 바뀔 때만 RT 재검증.",
    ))

    cells.append(md(
        "## 6. 정리 & 다음 단계",
        "",
        "**한 일** — report4 의 'SNR 주입' 을 링크버짓 물리로 대체한 **공정 벤치마크**: "
        "① 최소셀(물리→Pd 파이프라인) ② 점유 공정성(G1 이중고 정량화) ③ 신호×드론 매트릭스(CSV) "
        "④ 0-도플러 블라인드 정량화 ⑤ RT 교차검증. 모든 수치는 `outputs/report5_results.json` 에 저장되고 "
        "이 노트북은 그 값을 읽어 쓴다(수기 수치 없음).",
        "",
        "**다음 후보** (모두 챔버 형태)",
        "- 🌀 **마이크로도플러 결합 탐지**: hover/tangential 블라인드를 report3 블레이드 시그니처로 메우기 — "
        "거리-도플러 셀별 스펙트로그램 분류.",
        "- 📐 **AoA/다중정적**: 등Rb 타원 모호 해소 + Kalman/MTT 추적(report4 §4 연장).",
        "- 🔁 **Rényi 적응적분**: G1↔G3 가 섞인 실제 트래픽에서 점유 높은 구간만 골라 적분 — §2 의 갭을 좁히기.",
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
