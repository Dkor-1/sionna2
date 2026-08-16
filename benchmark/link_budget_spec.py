# -*- coding: utf-8 -*-
"""
link_budget_spec.py — ⭐«몇 미터에서 보이나» 의 **분모 정본**
==============================================================

무엇을 하는 파일인가
--------------------
잡음 본판(`benchmark/noise_distance_frame.py` 다음 판)이 내놓는 «판독거리 몇 m» 는
잣대(빗살 대비)와 **링크버짓** 두 다리로 선다. 잣대 쪽은 원장이 이미 단단하다.
이 파일은 **나머지 다리**를 한 곳에 모아, 상수마다 **근거 등급**을 붙이고,
근거 없는 상수로 절대 거리가 **조용히** 나가는 것을 코드로 막는다.

근거 등급 (사용자 지시, 2026-08-16)
-----------------------------------
  [A] 규격서·물리상수 — 원문에서 직접 읽은 값
  [B] 문헌           — 공개 논문/보고서의 측정값(환산·가정이 한 겹 낀다)
  [C] 관행           — 저장소·업계 관행값. 출처 문서는 없지만 **범위는 안다**
  [D] 가정           — 순수 선언. 근거 문서가 **없다**

⭐ 규칙 하나: **[D] 가 하나라도 들어간 조합으로 절대 거리를 내려면 `allow_declared=True`
를 명시**해야 하고, 그때 산출물에는 `declared_constants` 목록이 **반드시** 박힌다.
지금까지 «554 m» 가 아무 표시 없이 돌아다닌 이유가 이 게이트가 없었기 때문이다.

⭐ 왜 EIRP 하나가 그렇게 중요한가
--------------------------------
판독거리는 SNR 의 **네제곱근**으로 움직인다 — 모노스태틱 1/R⁴ 이므로

        R2 / R1 = 10 ** (ΔSNR_dB / 40)

즉 EIRP 를 12 → 63 dBm(저장소에 실제로 병존하는 두 값) 으로 바꾸면 거리가 **18.8 배**
움직인다. 잣대·앵커·막대를 아무리 정교하게 해도 이 한 줄을 안 적으면 «몇 미터» 는 뜻이 없다.

⛔ 이 파일이 하지 않는 것
------------------------
· 레이더 방정식·잡음전력을 **다시 구현하지 않는다** — `benchmark/link_budget.py` 를 쓴다.
· 정합필터 이득을 다시 구현하지 않는다 — `src/microdoppler_nearfield.matched_filter_gain_db`.
· X410 의 송신전력·안테나 이득·체인 잡음지수를 **지어내지 않는다**. 그 셋은 아래에서
  `UNRESOLVED` 로 남아 있고, 스펙시트를 확보하면 이 파일 한 곳만 고치면 된다.

실행(자가검사):  PYTHONPATH=src:benchmark python benchmark/link_budget_spec.py
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field, asdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from link_budget import LinkBudget, K_BOLTZ, T0, C0                      # noqa: E402

GRADES = ("A", "B", "C", "D")
UNRESOLVED = None


@dataclass(frozen=True)
class Const:
    """상수 한 개 + 그 상수의 **근거**. 값이 None 이면 «아직 못 구했다» 는 뜻이다."""
    value: float | None
    unit: str
    grade: str                    # A/B/C/D
    source: str                   # 어디서 왔나 (파일·문서·규격)
    note_ko: str = ""

    def __post_init__(self):
        if self.grade not in GRADES:
            raise ValueError(f"모르는 등급 {self.grade!r} — {GRADES} 중 하나여야 한다")

    @property
    def resolved(self) -> bool:
        return self.value is not None


# --------------------------------------------------------------------------- #
#  1. 물리상수 · 표적 앵커 — 저장소에서 가장 단단한 자리
# --------------------------------------------------------------------------- #
PHYSICS = dict(
    k_boltz=Const(K_BOLTZ, "J/K", "A", "CODATA (benchmark/link_budget.K_BOLTZ)"),
    T0=Const(T0, "K", "A", "IEEE 기준 잡음온도 290 K (link_budget.T0)"),
    c0=Const(C0, "m/s", "A", "정의값"),
)

TARGET = dict(
    sigma_ref_dbsm=Const(
        -13.984212727603522, "dBsm", "A",
        "src/sigma_anchor.py — Das et al. Table III 원문 PDF 직접 판독",
        "anchor_mu −15.948 dBsm(phantom3, 방위 선형평균) + 크기보정 +1.964 dB. "
        "⭐fc 3.5 GHz 가 측정 밴드 1.8~18.2 GHz **안**이라 외삽이 아니다"),
    size_corr_db=Const(
        1.9639714910479582, "dB", "B",
        "src/sigma_anchor.size_correction_db — phantom3 → matrice4e",
        "L² 크기법 가정이 한 겹 낀다(측정이 아니다)"),
)

# --------------------------------------------------------------------------- #
#  2. 수신 체인 — ⚠여기가 약한 다리다
# --------------------------------------------------------------------------- #
RX_CHAIN = dict(
    grx_dbi=Const(
        10.0, "dBi", "C", "src/rx_noise.RxSpec.grx_dbi (선언값)",
        "⚠실제로 쓸 안테나가 정해지면 [A] 로 승격된다. 3.5 GHz 상용 패널 8~17 dBi 범위 안"),
    nf_db=Const(
        5.0, "dB", "C", "src/rx_noise.RxSpec.nf_db (선언값)",
        "⚠X410+ZBX 실제 체인 NF 미확보. 상용 SDR 프런트엔드 관행 4~8 dB 범위 안"),
    sys_loss_db=Const(
        0.0, "dB", "D", "src/rx_noise.RxSpec.sys_loss_db (선언값)",
        "⛔0 dB 는 물리적으로 불가능하다 — 케이블·정합·창손실이 반드시 있다. **낙관 쪽 편향**"),
)

X410_HW = dict(   # 확보된 것 — src/experiment_x410.X410 (ni.com/ettus.com 공식 스펙)
    n_rx=Const(4, "ch", "A", "experiment_x410.X410.n_rx"),
    max_bw_hz=Const(400e6, "Hz", "A", "experiment_x410.X410.max_bw_hz"),
    adc_bits=Const(12, "bit", "A", "experiment_x410.X410.adc_bits",
                   "동적범위 6.0206·12+1.76 = 74.0 dB"),
    max_sample_rate_hz=Const(491.52e6, "S/s", "A", "experiment_x410.X410.max_sample_rate_hz"),
    # ⛔ 링크버짓에 필요한 셋이 스펙 파일에 **없다** — 지어내지 않고 비워 둔다
    tx_power_dbm=Const(UNRESOLVED, "dBm", "D",
                       "⛔미확보 — X410+ZBX 데이터시트의 3.5 GHz 대역 정격 출력",
                       "확보 전까지 이 값으로 절대 거리를 내면 안 된다"),
    tx_gain_dbi=Const(UNRESOLVED, "dBi", "D",
                      "⛔미확보 — 실제로 쓸 송신 안테나 이득"),
    chain_nf_db=Const(UNRESOLVED, "dB", "D",
                      "⛔미확보 — LNA 포함 수신 체인 잡음지수"),
)

# --------------------------------------------------------------------------- #
#  3. 조명원 시나리오 — «누가 쏘나» 가 EIRP 와 PRF 를 **동시에** 정한다
# --------------------------------------------------------------------------- #
#  ⭐PRF 는 잡음전력(N = kT0·F·PRF)에도, 관측 가능한 도플러 폭(±PRF/2)에도 들어간다.
#  그래서 «조명원을 바꾼다» 는 것은 잡음만 바꾸는 것이 아니라 **볼 수 있는 것 자체**를 바꾼다.
@dataclass(frozen=True)
class Scenario:
    key: str
    label_ko: str
    label_en: str
    eirp: Const
    prf: Const                      # 슬로타임 표본율 [Hz]
    b_hz: Const                     # 수신 순시대역 [Hz]
    capture: str                    # "full_waveform" | "always_on_pilot"
    geometry: str                   # "monostatic" | "bistatic"
    note_ko: str = ""

    def unresolved(self) -> list[str]:
        return [n for n, c in (("eirp", self.eirp), ("prf", self.prf), ("b_hz", self.b_hz))
                if not c.resolved]

    def declared(self) -> list[str]:
        out = [f"{n}[{c.grade}]" for n, c in
               (("eirp", self.eirp), ("prf", self.prf), ("b_hz", self.b_hz)) if c.grade == "D"]
        out += [f"rx.{n}[{c.grade}]" for n, c in RX_CHAIN.items() if c.grade == "D"]
        return out


SCENARIOS = {
    # ── 헤드라인 ─────────────────────────────────────────────────────────── #
    "active_mono_x410": Scenario(
        key="active_mono_x410",
        label_ko="능동 모노스태틱 — X410 이 자기 파형을 쏜다(풀 웨이브폼 캡처)",
        label_en="Active monostatic, X410 self-transmit, full-waveform capture",
        eirp=Const(30.0, "dBm", "D", "src/rx_noise.RxSpec 기본·detection_curves 와 동일",
                   "⛔순수 선언 — «소형 센서급» 이라는 말뿐이고 근거 문서가 없다. "
                   "X410 정격 출력을 확보하면 [A] 로 바뀐다"),
        prf=Const(19700.0, "Hz", "C", "outputs/elevation_sweep_md.json:_meta.prf_hz",
                  "⚠이 값의 유래는 «로터 자세 표본율»(f_tip 1102 Hz 대비 여유 9배)이다. "
                  "본판에서는 «센서 설계값»으로 선언한다 — 날개끝 1102 Hz 를 접지 않으려면 "
                  "최소 2205 Hz 가 필요하고, 19.7 kHz 는 그 위에서 고른 값이다"),
        b_hz=Const(100e6, "Hz", "C", "src/microdoppler_nearfield.DECLARED_B_HZ (5G NR 100 MHz)",
                   "X410 은 400 MHz 까지 되므로 400 MHz 팔도 함께 낸다. "
                   "⭐B 는 SNR 식에서 약분되지만 **정합필터 이득 37.1/43.1 dB 라는 가정**으로 남는다"),
        capture="full_waveform", geometry="monostatic",
        note_ko="⭐덱 헤드라인은 이 팔이다. 파형을 우리가 알고 매 PRI 마다 대역을 통째로 "
                "상관한다는 전제 — 그 전제가 10log10(B/PRF) = 37.1 dB 를 품고 있다"),
    # ── 통제군(챔버) ─────────────────────────────────────────────────────── #
    "active_mono_chamber": Scenario(
        key="active_mono_chamber",
        label_ko="능동 모노스태틱 — 챔버 저출력",
        label_en="Active monostatic, low-power chamber",
        eirp=Const(12.0, "dBm", "C", "benchmark/run_min_cell.EIRP_DBM · "
                                     "microdoppler_nearfield.DECLARED_EIRP_DBM",
                   "챔버 실험 관행값. 저장소 다른 원장(md_range_sweep_mf)이 이 값을 쓴다"),
        prf=Const(19700.0, "Hz", "C", "위와 같음"),
        b_hz=Const(100e6, "Hz", "C", "위와 같음"),
        capture="full_waveform", geometry="monostatic",
        note_ko="같은 잣대·같은 막대에서 EIRP 만 −18 dB → 거리 ×0.355"),
    # ── 패시브 ───────────────────────────────────────────────────────────── #
    "passive_lte_crs": Scenario(
        key="passive_lte_crs",
        label_ko="패시브 바이스태틱 — LTE 기지국 CRS(상시 기준신호)",
        label_en="Passive bistatic, LTE CRS always-on pilot",
        eirp=Const(63.0, "dBm", "C", "benchmark/link_budget.LinkBudget 기본 · "
                                     "docs/REPORT13_SPEC eirp_deploy.lte",
                   "매크로 셀 대표값 ≈2 kW. in-burst peak 규약(REPORT13_SPEC F13)"),
        prf=Const(1000.0, "Hz", "B", "src/waveforms.PILOT_RATE_HZ['lte']['CRS']",
                  "CRS 가 매 서브프레임 전대역 송신 → 1 kHz. 3GPP 자원격자에서 나온 값"),
        b_hz=Const(20e6, "Hz", "B", "src/waveforms.lte_downlink 기본 대역"),
        capture="always_on_pilot", geometry="bistatic",
        note_ko="⛔이 팔에서는 정합필터 이득이 **0 dB** 다(matched_filter_gain_db 규약). "
                "⭐⭐그리고 더 중요한 것 — 슬로타임 표본율이 1 kHz 라 날개끝 1102 Hz 가 "
                "**접힌다**. 즉 이 팔은 «멀어서 안 보인다» 가 아니라 «잣대 자체가 성립 안 한다»"),
    "passive_nr_ssb": Scenario(
        key="passive_nr_ssb",
        label_ko="패시브 바이스태틱 — 5G SSB(상시 기준신호)",
        label_en="Passive bistatic, 5G SSB always-on pilot",
        eirp=Const(47.0, "dBm", "C", "docs/REPORT13_SPEC eirp_deploy.nr_idle",
                   "유휴 gNB. 풀로드 65 dBm 은 유휴 G1 에 붙이지 않는다(F2)"),
        prf=Const(50.0, "Hz", "B", "src/waveforms.PILOT_RATE_HZ['nr']['PSS'] — SSB 20 ms 버스트"),
        b_hz=Const(7.2e6, "Hz", "B", "SSB 240 부반송파 × 30 kHz SCS ≈ 7.2 MHz(협대역)"),
        capture="always_on_pilot", geometry="bistatic",
        note_ko="⭐5G 의 이중고가 그대로 나온다 — 협대역(거리분해능 나쁨) + 50 Hz(속도 접힘). "
                "날개끝 1102 Hz 를 보려면 2205 Hz 가 필요한데 50 Hz 다(44 배 부족)"),
    "passive_wifi": Scenario(
        key="passive_wifi",
        label_ko="패시브 바이스태틱 — WiFi VHT-LTF(혼잡 AP)",
        label_en="Passive bistatic, WiFi VHT-LTF (busy AP)",
        eirp=Const(30.0, "dBm", "C", "docs/REPORT13_SPEC eirp_deploy.wifi",
                   "실내 AP 대표값(규제 상한 근처)"),
        prf=Const(1000.0, "Hz", "C", "src/waveforms.PILOT_RATE_HZ['wifi']['LLTF']",
                  "⚠«혼잡 AP» 대표값이다. 트래픽이 없으면 비콘 9.77 Hz 까지 떨어진다"),
        b_hz=Const(80e6, "Hz", "B", "802.11ac 80 MHz"),
        capture="always_on_pilot", geometry="bistatic",
        note_ko="반복률은 트래픽 의존이라 범위가 100 배다 — 절대 거리 인용에 가장 부적합"),
}

HEADLINE_SCENARIO = "active_mono_x410"


# --------------------------------------------------------------------------- #
#  4. 계산 — 재구현 금지, 위임만 한다
# --------------------------------------------------------------------------- #
def noise_power_w(scn: Scenario, nf_db: float | None = None) -> float:
    """표본당 잡음전력 N = k·T0·F·PRF [W] — link_budget 에 위임(재구현 금지)."""
    f = RX_CHAIN["nf_db"].value if nf_db is None else float(nf_db)
    return float(LinkBudget(noise_figure_db=f).noise_power_w(float(scn.prf.value)))


def matched_filter_gain_db(scn: Scenario) -> float:
    """정합필터 이득 10log10(B/PRF) — src/microdoppler_nearfield 에 위임(재구현 금지).

    ⭐`capture="always_on_pilot"` 이면 **0 dB** 를 돌려준다."""
    from microdoppler_nearfield import matched_filter_gain_db as _g
    return float(_g(scn.b_hz.value, scn.prf.value, capture=scn.capture))


def doppler_feasible(scn: Scenario, f_tip_hz: float) -> dict:
    """⭐«이 조명원으로 날개끝을 접지 않고 볼 수 있나» — 잣대가 성립하는지의 게이트.

    슬로타임 표본율이 PRF 이므로 관측 가능한 도플러는 ±PRF/2 다. 날개끝 f_tip 을
    접지 않으려면 PRF ≥ 2·f_tip 이어야 한다. ⛔이 게이트가 실패하면 그 팔에서
    «몇 미터까지 무늬가 읽히나» 는 **애초에 물을 수 없는 질문**이다(거리 문제가 아니다)."""
    need = 2.0 * float(f_tip_hz)
    prf = float(scn.prf.value)
    return dict(prf_hz=prf, need_hz=need, ok=bool(prf >= need),
                fold_factor=round(need / prf, 2),
                why_ko=("접힘 없음" if prf >= need else
                        f"날개끝 {f_tip_hz:.0f} Hz 가 ±{prf/2:.0f} Hz 안으로 접힌다 — "
                        f"빗살 대비 잣대가 성립하지 않는다"))


def r_multiplier(delta_snr_db: float) -> float:
    """ΔSNR [dB] → 거리 배수. 모노스태틱 1/R⁴ 이므로 R ∝ 10^(Δ/40)."""
    return float(10.0 ** (float(delta_snr_db) / 40.0))


def snr_shift_db(base: Scenario, other: Scenario, *, nf_db: float | None = None) -> dict:
    """두 시나리오 사이의 표본당 SNR 차이 [dB] 와 그것이 만드는 거리 배수.

    ⚠기하(모노/바이)가 다르면 R1·R2 가 따로 놀아 단일 «거리» 로 환산할 수 없다 —
    그 경우 `comparable=False` 를 돌려주고 거리 배수를 **주지 않는다**."""
    d_eirp = float(other.eirp.value) - float(base.eirp.value)
    d_noise = -10.0 * math.log10(float(other.prf.value) / float(base.prf.value))
    d_mf = matched_filter_gain_db(other) - matched_filter_gain_db(base)
    d = d_eirp + d_noise + d_mf
    comparable = (base.geometry == other.geometry)
    return dict(d_eirp_db=round(d_eirp, 2), d_noise_bw_db=round(d_noise, 2),
                d_mf_db=round(d_mf, 2), d_total_db=round(d, 2),
                comparable=comparable,
                R_multiplier=(round(r_multiplier(d), 4) if comparable else None),
                note_ko=("" if comparable else
                         "기하가 달라 단일 거리 배수로 못 옮긴다 — 바이스태틱은 R1·R2 가 따로다"))


def budget_report(scn: Scenario, *, allow_declared: bool = False) -> dict:
    """⭐이 시나리오로 절대 거리를 낼 자격이 있는지 판정하고, 근거 목록을 만든다.

    미확보(UNRESOLVED) 상수가 있으면 **무조건 예외**. [D] 등급만 있으면
    `allow_declared=True` 일 때만 통과하고, 산출물에 `declared_constants` 가 박힌다."""
    miss = scn.unresolved()
    if miss:
        raise ValueError(f"{scn.key}: 미확보 상수 {miss} — 절대 거리를 낼 수 없다")
    dec = scn.declared()
    if dec and not allow_declared:
        raise ValueError(
            f"{scn.key}: 선언값[D] {dec} 위에서 절대 거리를 내려면 allow_declared=True 를 "
            f"명시해야 한다. 상대 비교(팔 사이·앙각 사이)는 이 게이트 없이 쓸 수 있다")
    return dict(
        scenario=scn.key, label_ko=scn.label_ko, label_en=scn.label_en,
        geometry=scn.geometry, capture=scn.capture,
        eirp_dbm=scn.eirp.value, prf_hz=scn.prf.value, b_hz=scn.b_hz.value,
        grx_dbi=RX_CHAIN["grx_dbi"].value, nf_db=RX_CHAIN["nf_db"].value,
        sys_loss_db=RX_CHAIN["sys_loss_db"].value,
        noise_power_w=noise_power_w(scn), mf_gain_db=round(matched_filter_gain_db(scn), 2),
        sigma_ref_dbsm=TARGET["sigma_ref_dbsm"].value,
        grades={k: v.grade for k, v in
                dict(eirp=scn.eirp, prf=scn.prf, b=scn.b_hz, **RX_CHAIN,
                     sigma_ref_dbsm=TARGET["sigma_ref_dbsm"]).items()},
        declared_constants=dec,
        absolute_range_quotable=bool(not dec),
        provenance={k: asdict(v) for k, v in
                    dict(eirp=scn.eirp, prf=scn.prf, b_hz=scn.b_hz, **RX_CHAIN,
                         **{f"target_{k}": v for k, v in TARGET.items()}).items()})


def sensitivity_table(base_key: str = HEADLINE_SCENARIO) -> list[dict]:
    """⭐«규약을 바꾸면 거리가 얼마나 움직이나» — 본판 그림·원장이 그대로 쓰는 표."""
    base = SCENARIOS[base_key]
    rows = []

    def add(what, delta, grade, note):
        rows.append(dict(knob_ko=what, d_snr_db=round(delta, 2),
                         R_multiplier=round(r_multiplier(delta), 4),
                         grade=grade, note_ko=note))

    for e in (12.0, 30.0, 47.0, 63.0, 65.0):
        add(f"EIRP {e:.0f} dBm", e - base.eirp.value, "C" if e != 30.0 else "D",
            "저장소에 12·30·47·63 dBm 이 동시에 산다 — 어느 송신기인지 문장으로 선언해야 한다")
    add("정합필터 이득 없음(상시 기준신호 팔)", -matched_filter_gain_db(base), "C",
        "capture='always_on_pilot' → G_mf 0 dB. ⭐다만 그 팔은 도플러 게이트에서 먼저 걸린다")
    add("대역 400 MHz(X410 최대)", 10 * math.log10(400e6 / base.b_hz.value), "A",
        "B 는 SNR 에서 약분되지만 G_mf 가정이 37.1 → 43.1 dB 로 커진다")
    for nf in (3.0, 8.0):
        add(f"잡음지수 {nf:.0f} dB", RX_CHAIN["nf_db"].value - nf, "C", "상용 SDR 체인 범위")
    for g in (0.0, 20.0):
        add(f"수신이득 {g:.0f} dBi", g - RX_CHAIN["grx_dbi"].value, "C", "쓸 안테나가 정해지면 [A]")
    for L in (3.0, 6.0):
        add(f"시스템 손실 {L:.0f} dB", -L, "D", "⛔현행 0 dB 는 낙관 — 실제로 0 은 불가능")
    add("σ 앵커 +3 dB", 3.0, "A", "앵커 자체는 [A] 지만 ±3 dB 는 자세·기체 산포 폭")
    add("σ 앵커 −3 dB", -3.0, "A", "같음")
    return rows


# --------------------------------------------------------------------------- #
#  5. 자가검사
# --------------------------------------------------------------------------- #
def selftest() -> dict:
    st = {}
    base = SCENARIOS[HEADLINE_SCENARIO]
    # 1. 잡음전력이 기존 원장과 비트 수준으로 같나(재구현 안 했다는 증거)
    n = noise_power_w(base)
    st["1_noise_matches_ledger"] = dict(
        ok=abs(n - 2.4942932229992773e-16) < 1e-28, measured=n,
        expected=2.4942932229992773e-16,
        note_ko="detection_curves.json·noise_distance_frame.json 의 noise_power_w 와 같은 수")
    # 2. 정합필터 이득 — 풀캡처 37.06 dB, 상시 기준신호 0 dB
    g_full = matched_filter_gain_db(base)
    g_pilot = matched_filter_gain_db(SCENARIOS["passive_lte_crs"])
    st["2_mf_gain"] = dict(ok=abs(g_full - 37.06) < 0.01 and g_pilot == 0.0,
                           full_waveform_db=round(g_full, 3), always_on_pilot_db=g_pilot)
    # 3. 거리 배수가 1/R⁴ 과 맞나
    st["3_r_multiplier"] = dict(ok=abs(r_multiplier(40.0) - 10.0) < 1e-12,
                                measured=r_multiplier(40.0), expected=10.0,
                                note_ko="+40 dB = 거리 10 배 (1/R⁴)")
    # 4. ⭐선언값 게이트가 실제로 막나
    blocked = False
    try:
        budget_report(base)
    except ValueError:
        blocked = True
    ok4 = blocked and budget_report(base, allow_declared=True)["declared_constants"]
    st["4_declared_gate_blocks"] = dict(
        ok=bool(ok4), blocked_without_flag=blocked,
        declared=budget_report(base, allow_declared=True)["declared_constants"])
    # 5. 미확보 상수는 예외로 막힌다
    bad = Scenario("bad", "", "", Const(None, "dBm", "D", "미확보"),
                   base.prf, base.b_hz, "full_waveform", "monostatic")
    raised = False
    try:
        budget_report(bad, allow_declared=True)
    except ValueError:
        raised = True
    st["5_unresolved_raises"] = dict(ok=raised)
    # 6. ⭐도플러 게이트 — 상시 기준신호 팔은 잣대가 성립하지 않는다
    ft = 1102.4      # matrice4e el −30 (원장 f_tip)
    rows = {k: doppler_feasible(s, ft) for k, s in SCENARIOS.items()}
    st["6_doppler_gate"] = dict(
        ok=(rows["active_mono_x410"]["ok"] and not rows["passive_lte_crs"]["ok"]
            and not rows["passive_nr_ssb"]["ok"]),
        rows=rows,
        note_ko="⭐패시브 상시 기준신호 팔은 «멀어서 안 보이는» 것이 아니라 "
                "날개끝이 접혀 **빗살 잣대 자체가 성립하지 않는다**")
    # 7. X410 스펙 파일과 어긋나지 않나
    from experiment_x410 import X410
    hw = X410()
    st["7_x410_consistent"] = dict(
        ok=(X410_HW["max_bw_hz"].value == hw.max_bw_hz
            and X410_HW["adc_bits"].value == hw.adc_bits),
        dynamic_range_db=round(hw.dynamic_range_db, 1),
        unresolved=[k for k, v in X410_HW.items() if not v.resolved],
        note_ko="⛔송신전력·안테나이득·체인 NF 셋이 스펙 파일에 없다 — 확보 전까지 "
                "절대 거리는 «선언한 예산 아래의 거리» 다")
    st["ok"] = all(v.get("ok") for v in st.values() if isinstance(v, dict))
    return st


if __name__ == "__main__":
    import json
    st = selftest()
    print(json.dumps(st, ensure_ascii=False, indent=1, default=str))
    print("\n=== 감도표 (헤드라인 시나리오 기준) ===")
    for r in sensitivity_table():
        print(f"  [{r['grade']}] {r['knob_ko']:34s} Δ={r['d_snr_db']:+7.2f} dB  ×R={r['R_multiplier']:.4f}")
    print("\n=== 시나리오 사다리 ===")
    for k, s in SCENARIOS.items():
        g = doppler_feasible(s, 1102.4)
        tip = "볼 수 있음" if g["ok"] else f"접힘 ×{g['fold_factor']}"
        print(f"  {k:20s} EIRP {s.eirp.value:5.1f} dBm[{s.eirp.grade}] · PRF {s.prf.value:8.1f} Hz"
              f"[{s.prf.grade}] · G_mf {matched_filter_gain_db(s):5.2f} dB · 날개끝 {tip}")
