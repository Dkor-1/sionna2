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
  [B] 문헌           — 공개 논문/보고서/데이터시트 **그림**에서 읽은 값(판독이 한 겹 낀다)
  [C] 관행           — 저장소·업계 관행값. 출처 문서는 없지만 **범위는 안다**
  [D] 가정           — 순수 선언. 근거 문서가 **없다**

⭐ 규칙 하나: **[D] 가 하나라도 들어간 조합으로 절대 거리를 내려면 `allow_declared=True`
를 명시**해야 하고, 그때 산출물에는 `declared_constants` 목록이 **반드시** 박힌다.
지금까지 «554 m» 가 아무 표시 없이 돌아다닌 이유가 이 게이트가 없었기 때문이다.

⭐⭐ 2026-08-16 개정 — 선언값 세 개가 **데이터시트로 내려왔다**
---------------------------------------------------------------
NI/Ettus 「Ettus USRP X410 Specifications」(문서번호 378493, 2024-02-06 판)을 원문 PDF 로
받아 표는 텍스트로, 그림은 600 dpi 렌더로 직접 읽었다(σ 앵커와 같은 방식). 그 결과:

  · 수신 잡음지수  선언 5 dB[C]  →  **6.5 dB[A]** (3.1~6 GHz 대역 규정값, 우리 3.5 GHz 가 그 안)
  · 송신 출력      선언 «EIRP 30 dBm»[D] → **파형에 따라 세 값**[B] (아래 `X410_HW`)
  · 대역·ADC·표본율                       → 이미 [A] 였고 그대로

⭐ 그리고 이 조사가 **새 사실 두 개**를 데이터시트에서 끌어냈다:

  ① **OFDM 을 쏘면 평균 출력이 17 dB 떨어진다.** CW 최대 22.3 dBm 인 같은 하드웨어가
     5G NR 100 MHz 256QAM 을 EVM 무릎(−44 dB)까지 쓰면 채널전력 **+5 dBm** 이다
     (그림 1, 3.5 GHz 곡선). 파형 선택이 곧 송신전력 선택이다 — 우리 벤치마크의
     중심 질문(«어느 파형이 유리한가»)에 **하드웨어가 미리 매기는 벌점**이다.
  ② **위상잡음이 하필 우리 무늬 자리에 있다.** −91 dBc/Hz @ 1 kHz 오프셋인데
     날개끝은 1102 Hz, 깜빡임은 126.7 Hz 다. 능동 모노스태틱에서 새어 든 송신신호의
     위상잡음 치맛자락이 **열잡음보다 높으면** 우리 링크버짓의 분모가 통째로 바뀐다.
     `phase_noise_floor()` 가 그 문턱(격리 ≈ 89 dB)을 계산한다.

⭐ 왜 EIRP 하나가 그렇게 중요한가
--------------------------------
판독거리는 SNR 의 **네제곱근**으로 움직인다 — 모노스태틱 1/R⁴ 이므로

        R2 / R1 = 10 ** (ΔSNR_dB / 40)

즉 EIRP 를 12 → 63 dBm(저장소에 실제로 병존하는 두 값) 으로 바꾸면 거리가 **18.8 배**
움직인다. 잣대·앵커·막대를 아무리 정교하게 해도 이 한 줄을 안 적으면 «몇 미터» 는 뜻이 없다.
(`sensitivity_table()` 의 EIRP 손잡이 끝까지, 즉 12 → 65 dBm(풀로드 gNB)로 넓히면 21.1 배다.)
⭐그런데 그 18.8 배 폭은 **시나리오를 안 적었기 때문에** 생긴 폭이다. «누가 쏘나» 를 한 문장으로
정하면 EIRP 는 하나로 정해지고, 남는 폭은 안테나 이득(±10 dB)뿐이다 — 18.8 배가 3.2 배로 준다.

⛔ 이 파일이 하지 않는 것
------------------------
· 레이더 방정식·잡음전력을 **다시 구현하지 않는다** — `benchmark/link_budget.py` 를 쓴다.
· 정합필터 이득을 다시 구현하지 않는다 — `src/microdoppler_nearfield.matched_filter_gain_db`.
· 규제 상한(면허·ISM EIRP 한도)을 **지어내지 않는다**. `REGULATORY` 에 UNRESOLVED 로 남는다.

실행:
    PYTHONPATH=src:benchmark python benchmark/link_budget_spec.py            # 자가검사 + 표
    PYTHONPATH=src:benchmark python benchmark/link_budget_spec.py --ledger   # 원장 + 그림
    PYTHONPATH=src:benchmark python benchmark/link_budget_spec.py --ledger --measure
                                          # ↑ 잣대 쪽 게이트(CPI 사다리·PRF 불변성)까지 다시 잰다
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, field, asdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_HERE, os.path.join(_ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from link_budget import LinkBudget, K_BOLTZ, T0, C0                      # noqa: E402

GRADES = ("A", "B", "C", "D")
UNRESOLVED = None

OUT_JSON = os.path.join(_ROOT, "outputs", "link_budget_canon_0816.json")
OUT_PNG = os.path.join(_ROOT, "outputs", "figures", "link_budget_ladder.png")
LEDGER_JSON = os.path.join(_ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(_ROOT, "outputs", "elevation_sweep_md.npz")

#: X410 데이터시트 출처 — 한 곳에만 적고 전부 여기를 가리킨다
DATASHEET = ("NI/Ettus «Ettus USRP X410 Specifications», 문서 378493, 2024-02-06 판. "
             "표는 PDF 텍스트, 그림 1·2 는 600 dpi 렌더 판독 "
             "(https://www.farnell.com/datasheets/4146063.pdf · files.ettus.com/manual/page_zbx.html)")


@dataclass(frozen=True)
class Const:
    """상수 한 개 + 그 상수의 **근거**. 값이 None 이면 «아직 못 구했다» 는 뜻이다."""
    value: float | None
    unit: str
    grade: str                    # A/B/C/D
    source: str                   # 어디서 왔나 (파일·문서·규격)
    note_ko: str = ""
    lo: float | None = None       # 알려진 범위(있으면)
    hi: float | None = None

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
#  2. ⭐USRP X410 — 데이터시트에서 내려온 값들 (2026-08-16 갱신)
# --------------------------------------------------------------------------- #
X410_HW = dict(
    # ── 이미 [A] 였던 것 (src/experiment_x410.X410 과 일치해야 한다: 자가검사 7) ──
    n_rx=Const(4, "ch", "A", "experiment_x410.X410.n_rx · " + DATASHEET),
    n_tx=Const(4, "ch", "A", "experiment_x410.X410.n_tx · " + DATASHEET),
    max_bw_hz=Const(400e6, "Hz", "A", "채널당 순시대역 400 MHz · " + DATASHEET),
    adc_bits=Const(12, "bit", "A", "ADC 12 bit → 동적범위 6.0206·12+1.76 = 74.0 dB · " + DATASHEET),
    dac_bits=Const(14, "bit", "A", "DAC 14 bit · " + DATASHEET),
    max_sample_rate_hz=Const(491.52e6, "S/s", "A", "최대 I/Q 표본율 · " + DATASHEET),

    # ── ⭐새로 확보 — 송신 출력은 **하나가 아니라 파형마다 다르다** ────────────── #
    tx_pmax_cw_dbm_3g5=Const(
        22.3, "dBm", "B", DATASHEET + " 그림 2 (TX Maximum Output Power, 0 dBFS CW, 최대 이득)",
        "⭐3.5 GHz 판독값. 규정값은 «<23 dBm»[A] 이고 그림이 주파수별 곡선을 준다. "
        "80 % 신뢰구간 막대가 그 자리에서 ±0.7 dB. **정포락선(CW·처프) 파형에서만 쓸 수 있다**",
        lo=21.6, hi=23.0),
    tx_pavg_ofdm_evm30_dbm_3g5=Const(
        13.0, "dBm", "B", DATASHEET + " 그림 1 (TX EVM Bathtub, 3.5 GHz 곡선)",
        "⭐OFDM(5G NR 100 MHz) 을 EVM −30 dB 까지 밀어붙인 **평균 채널전력**. "
        "레이더는 256QAM 급 선형성이 필요 없다(기준신호를 캡처해 정합필터를 걸므로) — "
        "그래서 이 점을 헤드라인 canon 으로 고른다. ⚠선택이며 대안이 아래 둘이다",
        lo=11.0, hi=14.0),
    tx_pavg_ofdm_evm_knee_dbm_3g5=Const(
        5.0, "dBm", "B", DATASHEET + " 그림 1 (같은 곡선의 평탄 바닥, EVM ≈ −44 dB)",
        "통신급 선형성을 지키는 운용점. 여기를 쓰면 canon 보다 **8 dB 손해**",
        lo=0.0, hi=5.0),
    tx_pmax_cw_dbm_5g8=Const(
        17.0, "dBm", "B", DATASHEET + " 그림 2, 5.5~6 GHz 구간 판독",
        "⚠ISM 5.8 GHz 는 그림에서 대역 전환 구간이라 판독 폭이 넓다(±1.5 dB). "
        "실측 캠페인이 ISM 에서 송신하므로(docs/MEASUREMENT_PLAN §0-3) 이 값이 필요하다",
        lo=15.5, hi=18.5),

    # ── ⭐수신 잡음지수 — 선언 5 dB 를 대체한다 ─────────────────────────────── #
    rx_nf_db_3g5=Const(
        6.5, "dB", "A", DATASHEET + " Receiver / Noise figure, 3.1 GHz~6 GHz",
        "⭐우리 3.5 GHz 가 이 구간 **안**이다. 다른 구간은 500 MHz~3.1 GHz 8 dB · "
        "6~8 GHz 9 dB. 즉 3.5 GHz 는 이 장비가 가장 조용한 대역이다"),
    rx_gain_range_db=Const(60.0, "dB", "A", DATASHEET + " Receiver / Gain range (>500 MHz)"),
    rx_max_operating_dbm=Const(
        0.0, "dBm", "A", DATASHEET + " Receiver / Maximum operating power",
        "⭐직접파가 이 값을 넘으면 압축된다 — 패시브 팔의 실질 제약(손상 한계는 >3 GHz 에서 +17 dBm)"),
    rx_iip3_dbm=Const(12.0, "dBm", "A", DATASHEET + " Input IP3, 0 dBm input, full scale"),

    # ── ⭐위상잡음 — 우리 무늬가 사는 오프셋 ──────────────────────────────── #
    tx_pn_1k_dbc_hz=Const(
        -91.0, "dBc/Hz", "A", DATASHEET + " Transmitter / 1 kHz offset",
        "⭐⭐날개끝 1102 Hz·깜빡임 126.7 Hz 가 바로 이 오프셋대다. "
        "규정 조건: «0 dBFS 기저대역으로 0 dBm 출력이 되는 TX 이득 설정에서 측정»"),
    tx_pn_10k_dbc_hz=Const(-101.0, "dBc/Hz", "A", DATASHEET + " Transmitter / 10 kHz offset"),
    tx_pn_100k_dbc_hz=Const(-103.0, "dBc/Hz", "A", DATASHEET + " Transmitter / 100 kHz offset"),
    tx_noise_density_dbm_hz=Const(
        -146.0, "dBm/Hz", "A", DATASHEET + " Average noise density (23 °C, 10 MHz~8 GHz)"),

    # ── ⛔여전히 미확보 ──────────────────────────────────────────────────── #
    tx_isolation_db=Const(
        UNRESOLVED, "dB", "D",
        "⛔미확보 — 능동 모노스태틱에서 송신→수신 격리(안테나 배치·차폐가 정한다)",
        "⭐이것이 지금 **가장 비싼 미지수**다. phase_noise_floor() 가 이유를 수로 보인다"),
)

# --------------------------------------------------------------------------- #
#  3. 안테나 · 체인 — 여전히 약한 다리(다만 이제 범위는 적는다)
# --------------------------------------------------------------------------- #
RX_CHAIN = dict(
    grx_dbi=Const(
        10.0, "dBi", "C", "src/rx_noise.RxSpec.grx_dbi (선언값)",
        "⚠실제로 쓸 안테나가 정해지면 [A] 로 승격된다. 3.5 GHz 상용 패널 8~17 dBi 범위 안",
        lo=8.0, hi=17.0),
    nf_db=Const(
        6.5, "dB", "A", DATASHEET + " (3.1~6 GHz 규정 잡음지수)",
        "⭐2026-08-16 개정: 선언 5 dB[C] → 데이터시트 6.5 dB[A]. "
        "⚠외장 LNA 를 앞에 달면 다시 내려간다(그때는 그 LNA 스펙이 정본)"),
    sys_loss_db=Const(
        2.0, "dB", "C", "케이블·정합·창손실 관행값(SMA 케이블 ~1 dB + 정합/커넥터 ~1 dB)",
        "⭐2026-08-16 개정: 이전 판의 0 dB[D] 는 물리적으로 불가능해 **낙관 편향**이었다. "
        "2 dB 도 측정값은 아니지만 «0 은 틀렸다» 는 것은 안다 — 실측 전까지 [C]",
        lo=1.0, hi=4.0),
)
#: 이전 판(방법판·detection_curves.json·noise_distance_frame.json)이 쓴 예산 — 검산용으로 보존
LEGACY_RX_CHAIN = dict(eirp_dbm=30.0, grx_dbi=10.0, nf_db=5.0, sys_loss_db=0.0)

TX_ANTENNA = dict(
    gtx_dbi=Const(
        10.0, "dBi", "C", "수신과 같은 급의 패널을 가정(선언)",
        "능동 모노스태틱에서는 EIRP = P_tx + G_tx 다. 이 값이 안 정해지면 EIRP 도 안 정해진다",
        lo=8.0, hi=17.0),
)

REGULATORY = dict(
    can_transmit_3g5=Const(
        UNRESOLVED, "bool", "D",
        "⛔미확보 — 3.5 GHz(5G n78)는 **면허 대역**이다. 야외 송신 가능 여부·조건",
        "⭐docs/MEASUREMENT_PLAN §0-3 이 이미 «우리가 송신해도 되는 자리는 ISM 뿐» 이라고 "
        "적었다. 그러면 3.5 GHz 능동 팔은 **시뮬 전용**이고, 실측은 ISM 5.8 GHz 다"),
    ism58_eirp_cap_dbm=Const(
        UNRESOLVED, "dBm", "D", "⛔미확보 — 5.725~5.825 GHz ISM 의 국내 EIRP 상한",
        "확보하면 ISM 팔의 EIRP 가 «장비 한계» 가 아니라 «규제 한계» 로 바뀔 수 있다"),
)

# --------------------------------------------------------------------------- #
#  4. ⭐잣대 쪽 규약 — 링크버짓과 **같은 무게로** 거리를 움직인다
# --------------------------------------------------------------------------- #
#  이 절이 새로 생긴 이유: 지금까지 «몇 미터» 의 흔들림을 전부 EIRP·앵커 탓으로 적었는데,
#  실제로 재 보니 **관측시간(CPI)** 이 그만한 크기의 손잡이였다. 아래 두 사다리는
#  measure_metric_gates() 가 원장 시계열로 직접 잰 값이다(신호를 만들지 않는다).
METRIC = dict(
    n_slow=Const(8192, "sample", "A", "outputs/elevation_sweep_md.npz 열 길이"),
    prf_hz=Const(
        19700.0, "Hz", "C", "outputs/elevation_sweep_md.json:_meta.prf_hz",
        "⚠유래는 «로터 자세 표본율»(날개끝 1102 Hz 대비 여유 9배)이다. "
        "⭐그러나 아래 PRF_INVARIANCE 가 보이듯 **CPI 를 고정하면 판독거리는 PRF 에 무관**하다 — "
        "이 상수의 약한 근거가 답을 흔들지 않는다는 뜻이고, 그것을 측정으로 보였다"),
    cpi_s=Const(
        0.41584, "s", "C", "n_slow / prf_hz = 8192 / 19700",
        "⭐**저장소에서 가장 긴 CPI 다.** report13 규약은 0.1 s, "
        "experiment_x410.detection_config 기본은 20 ms — 즉 이 판은 다른 원장보다 "
        "관측시간을 4~21 배 길게 쓴다. 그 대가가 아래 CPI_LADDER 다"),
    f_flash_hz=Const(126.66666666666667, "Hz", "A", "원장 _meta.f_flash_hz (로터 회전수·날개수)"),
    f_tip_hz_el_minus30=Const(1102.4, "Hz", "A", "원장 rows[ours_r15_n8192, el−30].f_tip_hz"),
    comb_halfwidth_hz=Const(8.0, "Hz", "C", "build_md_atlas 표준 레시피 HW_HZ"),
)

#: ⭐측정값 — CPI 를 줄이면 잣대가 얼마나 나빠지나 (measure_metric_gates, 2026-08-16)
#:  cross_snr_db = 빗살 대비 평균이 그 CPI 의 귀무 p99.9 막대를 넘는 표본당 AC SNR.
#:  d_vs_canon_db 가 양수면 «더 센 신호가 있어야 읽힌다» = 그만큼 가까이 와야 한다.
CPI_LADDER = [
    dict(n=8192, cpi_ms=415.8, df_hz=2.40, n_on=86, n_off=94, bar_p999_db=2.760,
         cross_snr_db=-19.853, clean_comb_db=42.93, d_vs_canon_db=0.0, R_mult=1.0,
         label_ko="정본(이 원장)", label_en="canonical, this ledger"),
    dict(n=4096, cpi_ms=207.9, df_hz=4.81, n_on=44, n_off=46, bar_p999_db=3.650,
         cross_snr_db=-18.165, clean_comb_db=43.46, d_vs_canon_db=1.688, R_mult=0.9082,
         label_ko="절반", label_en="half"),
    dict(n=2048, cpi_ms=104.0, df_hz=9.62, n_on=22, n_off=22, bar_p999_db=4.560,
         cross_snr_db=-14.646, clean_comb_db=41.22, d_vs_canon_db=5.207, R_mult=0.7412,
         label_ko="⭐report13 규약 0.1 s 에 해당", label_en="the repo's 0.1 s convention"),
    dict(n=1024, cpi_ms=52.0, df_hz=19.24, n_on=10, n_off=12, bar_p999_db=6.020,
         cross_snr_db=-8.995, clean_comb_db=31.40, d_vs_canon_db=10.858, R_mult=0.5350,
         label_ko="report12 T_CPI(52 ms)에 해당", label_en="the passive-chain T_CPI"),
    dict(n=512, cpi_ms=26.0, df_hz=38.48, n_on=6, n_off=6, bar_p999_db=8.330,
         cross_snr_db=-2.710, clean_comb_db=17.60, d_vs_canon_db=17.143, R_mult=0.3720,
         label_ko="⭐X410 detection_config 기본 20 ms 근처",
         label_en="near the X410 default 20 ms"),
    dict(n=256, cpi_ms=13.0, df_hz=76.95, n_on=2, n_off=4, bar_p999_db=None,
         cross_snr_db=None, clean_comb_db=None, d_vs_canon_db=None, R_mult=None,
         label_ko="⛔마스크 붕괴 — 잣대가 **정의되지 않는다**",
         label_en="mask collapses, metric undefined"),
]

#: ⭐측정값 — 같은 CPI 에서 PRF 만 낮추면(표본 솎기) 표본당 SNR 교차점이 정확히 10log10(dec) 만큼
#:  움직인다. 잡음전력도 PRF 에 정비례하므로 **판독거리는 그대로**다.
PRF_INVARIANCE = [
    dict(dec=1, prf_hz=19700.0, n=8192, cross_snr_db=-19.853, expected_shift_db=0.000,
         measured_shift_db=0.000, residual_db=0.000),
    dict(dec=2, prf_hz=9850.0, n=4096, cross_snr_db=-16.568, expected_shift_db=3.010,
         measured_shift_db=3.285, residual_db=0.275),
    dict(dec=4, prf_hz=4925.0, n=2048, cross_snr_db=-13.944, expected_shift_db=6.021,
         measured_shift_db=5.909, residual_db=-0.112),
    dict(dec=8, prf_hz=2462.5, n=1024, cross_snr_db=-11.098, expected_shift_db=9.031,
         measured_shift_db=8.755, residual_db=-0.276),
]
PRF_INVARIANCE_NOTE_KO = (
    "⭐dec=8 의 PRF 2462.5 Hz 는 도플러 게이트(2·f_tip = 2204.8 Hz) 바로 위다 — "
    "사다리가 물리적 하한에서 정확히 끝난다. 잔차 ≤0.28 dB = 거리 ±0.7 %. "
    "⇒ **PRF 19.7 kHz 의 약한 근거[C]는 «몇 미터» 를 흔들지 않는다.**")

#: ⭐패시브 2채널 — 기준 안테나를 이상적으로 두면 얼마를 공짜로 얻나
#:  출처: outputs/passive_two_channel.json (empirical_law · summary), 챔버 기하 DTR 65.86 dB
REFERENCE_CHANNEL = dict(
    law="loss_dB = 10·log10(1 + 10^((DTR_dB − 2·ρ_ref_dB)/10))",
    design_rule_ko="손실 ≤ 3 dB ⟺ ρ_ref ≥ DTR/2",
    fit_mae_db=dict(W1_L1=0.719, G1=11.339),
    measured_loss_db_by_rho=dict.fromkeys([], None) | {
        "40": 0.633, "30": 6.972, "20": 25.435, "10": 44.899, "0": 57.671},
    dtr_db=65.858,
    ref_antenna_gain_needed_db=14.088,
    scope_ko="⚠W1(WiFi)·L1(LTE) 에서만 평균오차 <1 dB 로 맞는다. G1(5G SSB)는 바닥이 "
             "열잡음이 아니라 직접파 잔류라 이 식이 안 맞는다(오차 최대 20 dB)",
    what_it_means_ko="⭐헤드라인이 쓰는 «이상적 정합필터» 는 ρ_ref = ∞ 다. 현실적인 "
                     "기준채널(ρ_ref 30 dB)만 돼도 **7 dB**, 20 dB 면 **25 dB** 를 잃는다 — "
                     "거리로는 ×0.67 과 ×0.24 다",
)

# --------------------------------------------------------------------------- #
#  5. 조명원 시나리오 — «누가 쏘나» 가 EIRP·PRF·면허를 **동시에** 정한다
# --------------------------------------------------------------------------- #
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
    fc_hz: float = 3.5e9
    tx_source_ko: str = ""          # 누가 쏘나 — 한 문장
    licensing: str = "unresolved"   # "receive_only" | "ism_ok" | "licensed_band_sim_only"
    waveform_class: str = "ofdm"    # "ofdm" | "constant_envelope"

    def unresolved(self) -> list[str]:
        return [n for n, c in (("eirp", self.eirp), ("prf", self.prf), ("b_hz", self.b_hz))
                if not c.resolved]

    def declared(self) -> list[str]:
        out = [f"{n}[{c.grade}]" for n, c in
               (("eirp", self.eirp), ("prf", self.prf), ("b_hz", self.b_hz)) if c.grade == "D"]
        out += [f"rx.{n}[{c.grade}]" for n, c in RX_CHAIN.items() if c.grade == "D"]
        return out

    def range_exponent(self) -> float:
        """거리 배수 지수 — 모노(양다리 같이 움직임) 40, 바이스태틱 한 다리만 20 [dB/decade]."""
        return 40.0 if self.geometry == "monostatic" else 20.0


def _eirp_from_hw(p_tx: Const, note_extra: str = "") -> Const:
    """EIRP = P_tx + G_tx — 등급은 둘 중 **낮은 쪽**을 물려받는다(약한 고리 규칙)."""
    g = TX_ANTENNA["gtx_dbi"]
    grade = max(p_tx.grade, g.grade)          # 문자 순서상 A<B<C<D 이므로 max 가 «더 약한 쪽»
    return Const(p_tx.value + g.value, "dBm", grade,
                 f"P_tx({p_tx.source}) + G_tx({g.source})",
                 f"{p_tx.value:.1f} dBm + {g.value:.0f} dBi. {note_extra} {p_tx.note_ko}".strip(),
                 lo=(None if p_tx.lo is None else p_tx.lo + (g.lo or g.value)),
                 hi=(None if p_tx.hi is None else p_tx.hi + (g.hi or g.value)))


SCENARIOS = {
    # ── ⭐헤드라인 ────────────────────────────────────────────────────────── #
    "active_mono_x410": Scenario(
        key="active_mono_x410",
        label_ko="능동 모노스태틱 — X410 이 자기 파형을 쏜다(풀 웨이브폼 캡처)",
        label_en="Active monostatic, X410 self-transmit, full-waveform capture",
        eirp=_eirp_from_hw(X410_HW["tx_pavg_ofdm_evm30_dbm_3g5"],
                           "⭐OFDM 평균전력 기준."),
        prf=METRIC["prf_hz"],
        b_hz=Const(100e6, "Hz", "C", "src/microdoppler_nearfield.DECLARED_B_HZ (5G NR 100 MHz)",
                   "X410 은 400 MHz 까지 되므로 400 MHz 팔도 감도표에 있다. "
                   "⭐B 는 SNR 식에서 약분되지만 **정합필터 이득 37.1/43.1 dB 라는 가정**으로 남는다"),
        capture="full_waveform", geometry="monostatic",
        tx_source_ko="우리 X410 + 10 dBi 패널. 파형을 우리가 만들고 캡처해 정합필터를 건다",
        licensing="licensed_band_sim_only", waveform_class="ofdm",
        note_ko="⭐덱 헤드라인은 이 팔이다. ⛔그러나 3.5 GHz 는 면허 대역이라 **야외 실측은 "
                "이 팔로 못 한다** — 시뮬 전용이다. 실측 능동은 ISM 5.8 GHz 팔로 간다"),
    # 같은 하드웨어, 파형만 정포락선(처프·CW) — 데이터시트가 주는 17.3 dB 차이
    "active_mono_x410_cw": Scenario(
        key="active_mono_x410_cw",
        label_ko="능동 모노스태틱 — X410, 정포락선 파형(처프/CW)",
        label_en="Active monostatic, X410, constant-envelope waveform",
        eirp=_eirp_from_hw(X410_HW["tx_pmax_cw_dbm_3g5"], "정포락선이라 백오프가 없다."),
        prf=METRIC["prf_hz"], b_hz=Const(100e6, "Hz", "C", "위와 같음"),
        capture="full_waveform", geometry="monostatic",
        tx_source_ko="같은 X410 인데 파형만 정포락선 — 데이터시트상 평균전력이 9.3 dB 높다",
        licensing="licensed_band_sim_only", waveform_class="constant_envelope",
        note_ko="⭐«파형을 고르면 송신전력도 같이 고른 것» 이라는 사실의 상한 팔"),
    # ── 실측으로 갈 수 있는 능동 팔 ──────────────────────────────────────── #
    "active_mono_x410_ism58": Scenario(
        key="active_mono_x410_ism58",
        label_ko="능동 모노스태틱 — ISM 5.8 GHz(실측 캠페인 2층)",
        label_en="Active monostatic, ISM 5.8 GHz (measurement campaign layer 2)",
        eirp=_eirp_from_hw(X410_HW["tx_pmax_cw_dbm_5g8"], "ISM 이라 면허가 필요 없다."),
        prf=METRIC["prf_hz"], b_hz=Const(80e6, "Hz", "C", "ISM span 안에서 쓸 대역(선언)"),
        capture="full_waveform", geometry="monostatic", fc_hz=5.8e9,
        tx_source_ko="우리 X410, ISM 대역. docs/MEASUREMENT_PLAN §0-3 이 정한 실측 자리",
        licensing="ism_ok", waveform_class="constant_envelope",
        note_ko="⛔이 팔로는 **이 원장의 미터를 그대로 못 쓴다** — λ 도 σ(f) 도 다르다. "
                "5.8 GHz 원장이 생기기 전까지 거리 인용 금지(comparable=False)"),
    # ── 통제군(챔버) ─────────────────────────────────────────────────────── #
    "active_mono_chamber": Scenario(
        key="active_mono_chamber",
        label_ko="능동 모노스태틱 — 챔버 저출력",
        label_en="Active monostatic, low-power chamber",
        eirp=Const(12.0, "dBm", "C", "benchmark/run_min_cell.EIRP_DBM · "
                                     "microdoppler_nearfield.DECLARED_EIRP_DBM",
                   "챔버 실험 관행값. 저장소 다른 원장(md_range_sweep_mf)이 이 값을 쓴다"),
        prf=METRIC["prf_hz"], b_hz=Const(100e6, "Hz", "C", "위와 같음"),
        capture="full_waveform", geometry="monostatic",
        tx_source_ko="챔버 저출력 송신기", licensing="ism_ok",
        note_ko="같은 잣대·같은 막대에서 EIRP 만 −11 dB → 거리 ×0.53"),
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
        capture="always_on_pilot", geometry="bistatic", fc_hz=1.843e9,
        tx_source_ko="남의 LTE 기지국. 우리는 받기만 한다", licensing="receive_only",
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
        tx_source_ko="남의 5G 기지국(유휴). 우리는 받기만 한다", licensing="receive_only",
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
        capture="always_on_pilot", geometry="bistatic", fc_hz=5.21e9,
        tx_source_ko="남의 WiFi AP. 우리는 받기만 한다", licensing="receive_only",
        note_ko="반복률은 트래픽 의존이라 범위가 100 배다 — 절대 거리 인용에 가장 부적합"),
}

HEADLINE_SCENARIO = "active_mono_x410"


# --------------------------------------------------------------------------- #
#  6. 계산 — 재구현 금지, 위임만 한다
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


def cpi_feasible(cpi_s: float, f_flash_hz: float | None = None,
                 f_tip_hz: float | None = None, hw_hz: float | None = None) -> dict:
    """⭐«이 관측시간에서 빗살 잣대가 성립하나» — 두 번째 게이트.

    빗살 대비는 «f_flash 정수배 칸» 과 «반정수 칸» 을 가른다. 둘 사이 간격은
    f_flash/2 이고, 주파수 분해능은 Δf = 1/CPI 다. 그래서

        ⓐ 두 칸을 구분하려면        Δf ≤ f_flash / 2
        ⓑ 반폭 ±hw 창에 칸이 들어오려면 Δf ≤ hw  (≈8 Hz)

    ⓑ 가 실질 조건이고, 실제로 재 보면(CPI_LADDER) 그보다 먼저 «on/off 칸 4개» 규칙에서
    막힌다. 정본 CPI 415.8 ms 는 Δf 2.40 Hz 로 여유가 크다."""
    f_flash = METRIC["f_flash_hz"].value if f_flash_hz is None else float(f_flash_hz)
    f_tip = METRIC["f_tip_hz_el_minus30"].value if f_tip_hz is None else float(f_tip_hz)
    hw = METRIC["comb_halfwidth_hz"].value if hw_hz is None else float(hw_hz)
    df = 1.0 / float(cpi_s)
    n_harm = max(0, int(math.floor(f_tip / f_flash)) - 1)      # 2·f_flash ~ f_tip 사이 정수배 수
    return dict(cpi_s=float(cpi_s), df_hz=round(df, 3),
                need_separate_hz=round(f_flash / 2.0, 3), need_inside_window_hz=hw,
                n_harmonics_in_band=n_harm,
                ok=bool(df <= hw and n_harm >= 4),
                why_ko=("성립" if (df <= hw and n_harm >= 4) else
                        f"Δf {df:.1f} Hz 가 빗살 반폭 {hw:.0f} Hz 보다 굵다 — "
                        f"정수배 칸과 중간 칸이 섞인다"))


def phase_noise_floor(scn: Scenario, isolation_db: float, offset_hz: float = 1000.0,
                      nf_db: float | None = None) -> dict:
    """⭐⭐능동 모노스태틱의 **진짜 바닥** — 새어 든 송신신호의 위상잡음.

    모노스태틱에서 송신기와 수신기가 같은 자리에 있으면 직접 누설이 들어온다. 그 누설은
    캐리어가 아니라 **치맛자락**을 끌고 오는데, 우리 무늬(깜빡임 126.7 Hz · 날개끝 1102 Hz)가
    하필 1 kHz 오프셋 근처다. 데이터시트가 그 자리를 −91 dBc/Hz 로 규정한다.

        누설전력밀도 [dBm/Hz] = (P_tx − 격리) + L(offset)
        열잡음밀도   [dBm/Hz] = k·T0·F        = −173.98 + NF

    두 값이 같아지는 격리를 `isolation_for_parity_db` 로 돌려준다. 격리가 그보다 낮으면
    **열잡음 링크버짓 전체가 그 차이만큼 낙관**이다.

    ⚠이 계산은 «거리 상관(range correlation)» 을 **credit 하지 않는다**. 동일 LO 를 쓰는
    구조라면 누설의 위상잡음은 상당 부분 상쇄될 수 있다. 그 상쇄량은 우리 하드웨어에서
    **측정된 적이 없다** — 그래서 이 함수는 상한(비관)이고, 실측 캠페인의 1순위 항목이다."""
    if scn.geometry != "monostatic":
        return dict(applicable=False,
                    why_ko="바이스태틱은 송신기가 남의 것이라 이 항이 이 형태로 안 붙는다")
    nf = RX_CHAIN["nf_db"].value if nf_db is None else float(nf_db)
    p_tx = float(scn.eirp.value) - float(TX_ANTENNA["gtx_dbi"].value)   # 도전전력으로 되돌린다
    pn = {1000.0: X410_HW["tx_pn_1k_dbc_hz"].value,
          10000.0: X410_HW["tx_pn_10k_dbc_hz"].value,
          100000.0: X410_HW["tx_pn_100k_dbc_hz"].value}.get(float(offset_hz))
    if pn is None:
        raise ValueError(f"데이터시트에 {offset_hz} Hz 오프셋 값이 없다 — 1k/10k/100k 만 있다")
    thermal_dbm_hz = -173.98 + nf
    leak_dbm_hz = (p_tx - float(isolation_db)) + pn
    excess = leak_dbm_hz - thermal_dbm_hz
    return dict(applicable=True, offset_hz=float(offset_hz), pn_dbc_hz=pn,
                p_tx_conducted_dbm=round(p_tx, 2), isolation_db=float(isolation_db),
                leakage_noise_dbm_hz=round(leak_dbm_hz, 2),
                thermal_dbm_hz=round(thermal_dbm_hz, 2),
                excess_over_thermal_db=round(max(excess, 0.0), 2),
                isolation_for_parity_db=round(p_tx + pn - thermal_dbm_hz, 2),
                R_multiplier=round(10.0 ** (-max(excess, 0.0) / scn.range_exponent()), 4),
                caveat_ko="거리상관 상쇄를 계산에 넣지 않은 **상한**이다. 우리 하드웨어의 "
                          "상쇄량은 미측정 — 실측 캠페인 1순위")


def r_multiplier(delta_snr_db: float, geometry: str = "monostatic") -> float:
    """ΔSNR [dB] → 거리 배수. 모노스태틱 1/R⁴ 이므로 R ∝ 10^(Δ/40).

    ⚠바이스태틱에서 **한 다리만** 움직이면 1/R² 이라 지수가 20 이다 — 같은 ΔSNR 이
    거리를 두 배(dB 기준) 더 움직인다. 기하를 안 적으면 이 인수를 놓친다."""
    e = 40.0 if geometry == "monostatic" else 20.0
    return float(10.0 ** (float(delta_snr_db) / e))


def restate_distance_m(R_m: float, delta_snr_db: float, geometry: str = "monostatic") -> float:
    """이미 나온 거리를 다른 예산으로 **옮긴다**(재계산 없이). R' = R·10^(Δ/지수)."""
    return float(R_m) * r_multiplier(delta_snr_db, geometry)


def legacy_shift_db(scn: Scenario | None = None) -> dict:
    """⭐이전 판(EIRP 30·NF 5·손실 0)에서 **정본 예산**으로 옮길 때의 총 이동량 [dB].

    지금 저장소에 떠 있는 «554 m» 류의 수는 전부 이전 판 예산 위에서 나온 값이다.
    본판은 이 한 수를 곱해서 그 수들을 옮기고, 옮겼다는 사실을 원장에 적는다."""
    scn = SCENARIOS[HEADLINE_SCENARIO] if scn is None else scn
    d_eirp = float(scn.eirp.value) - LEGACY_RX_CHAIN["eirp_dbm"]
    d_nf = -(RX_CHAIN["nf_db"].value - LEGACY_RX_CHAIN["nf_db"])
    d_loss = -(RX_CHAIN["sys_loss_db"].value - LEGACY_RX_CHAIN["sys_loss_db"])
    tot = d_eirp + d_nf + d_loss
    return dict(scenario=scn.key, d_eirp_db=round(d_eirp, 2), d_nf_db=round(d_nf, 2),
                d_sys_loss_db=round(d_loss, 2), d_total_db=round(tot, 2),
                R_multiplier=round(r_multiplier(tot, scn.geometry), 4),
                legacy=dict(LEGACY_RX_CHAIN),
                canon=dict(eirp_dbm=scn.eirp.value, grx_dbi=RX_CHAIN["grx_dbi"].value,
                           nf_db=RX_CHAIN["nf_db"].value,
                           sys_loss_db=RX_CHAIN["sys_loss_db"].value),
                note_ko="⭐공통모드다 — 모든 팔에 **같은 배수**가 걸린다. 팔 사이 순서·배수는 "
                        "안 바뀌고 절대 미터만 움직인다. 팔마다 다르게 움직이면 코드 버그다")


def snr_shift_db(base: Scenario, other: Scenario, *, nf_db: float | None = None) -> dict:
    """두 시나리오 사이의 표본당 SNR 차이 [dB] 와 그것이 만드는 거리 배수.

    ⚠기하(모노/바이)가 다르거나 반송파가 다르면 단일 «거리» 로 환산할 수 없다 —
    그 경우 `comparable=False` 를 돌려주고 거리 배수를 **주지 않는다**."""
    d_eirp = float(other.eirp.value) - float(base.eirp.value)
    d_noise = -10.0 * math.log10(float(other.prf.value) / float(base.prf.value))
    d_mf = matched_filter_gain_db(other) - matched_filter_gain_db(base)
    d = d_eirp + d_noise + d_mf
    same_geom = (base.geometry == other.geometry)
    same_fc = abs(base.fc_hz - other.fc_hz) < 1.0
    comparable = same_geom and same_fc
    why = []
    if not same_geom:
        why.append("기하가 달라 단일 거리 배수로 못 옮긴다 — 바이스태틱은 R1·R2 가 따로다")
    if not same_fc:
        why.append(f"반송파가 다르다({base.fc_hz/1e9:.2f} ↔ {other.fc_hz/1e9:.2f} GHz) — "
                   f"λ² 도 σ(f) 도 같이 움직이므로 이 원장의 미터를 못 옮긴다")
    return dict(d_eirp_db=round(d_eirp, 2), d_noise_bw_db=round(d_noise, 2),
                d_mf_db=round(d_mf, 2), d_total_db=round(d, 2),
                comparable=comparable,
                R_multiplier=(round(r_multiplier(d, base.geometry), 4) if comparable else None),
                note_ko=" / ".join(why))


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
    grades = dict(eirp=scn.eirp, prf=scn.prf, b=scn.b_hz, **RX_CHAIN,
                  gtx_dbi=TX_ANTENNA["gtx_dbi"], sigma_ref_dbsm=TARGET["sigma_ref_dbsm"])
    return dict(
        scenario=scn.key, label_ko=scn.label_ko, label_en=scn.label_en,
        geometry=scn.geometry, capture=scn.capture, fc_hz=scn.fc_hz,
        licensing=scn.licensing, waveform_class=scn.waveform_class,
        tx_source_ko=scn.tx_source_ko,
        eirp_dbm=scn.eirp.value, prf_hz=scn.prf.value, b_hz=scn.b_hz.value,
        grx_dbi=RX_CHAIN["grx_dbi"].value, nf_db=RX_CHAIN["nf_db"].value,
        sys_loss_db=RX_CHAIN["sys_loss_db"].value,
        cpi_s=METRIC["cpi_s"].value,
        noise_power_w=noise_power_w(scn), mf_gain_db=round(matched_filter_gain_db(scn), 2),
        sigma_ref_dbsm=TARGET["sigma_ref_dbsm"].value,
        range_exponent_db_per_decade=scn.range_exponent(),
        grades={k: v.grade for k, v in grades.items()},
        weakest_grade=max(v.grade for v in grades.values()),
        declared_constants=dec,
        absolute_range_quotable=bool(not dec),
        provenance={k: asdict(v) for k, v in
                    dict(eirp=scn.eirp, prf=scn.prf, b_hz=scn.b_hz, **RX_CHAIN,
                         gtx_dbi=TX_ANTENNA["gtx_dbi"],
                         **{f"target_{k}": v for k, v in TARGET.items()}).items()})


def sensitivity_table(base_key: str = HEADLINE_SCENARIO) -> list[dict]:
    """⭐«규약을 바꾸면 거리가 얼마나 움직이나» — 본판 그림·원장이 그대로 쓰는 표.

    ⭐분류: `side` 가 «budget» 이면 거리→SNR 지도만 옮기므로 **재계산이 필요 없다**.
    «metric» 이면 잣대 곡선 자체가 바뀌므로 그 규약을 바꾸려면 **곡선을 다시 재야** 한다."""
    base = SCENARIOS[base_key]
    rows = []

    def add(what, what_en, delta, grade, note, side="budget", geom=None):
        rows.append(dict(knob_ko=what, knob_en=what_en, d_snr_db=round(delta, 2), side=side,
                         R_multiplier=round(r_multiplier(delta, geom or base.geometry), 4),
                         grade=grade, note_ko=note))

    # ── 예산 쪽 ─────────────────────────────────────────────────────────── #
    add("이전 판 예산으로 되돌리기(EIRP 30·NF 5·손실 0)",
        "revert to the old budget (EIRP 30, NF 5, loss 0)",
        -legacy_shift_db(base)["d_total_db"], "D",
        "⭐저장소에 떠 있는 554/641 m 는 전부 이 예산 위의 수다")
    for k, lab, lab_en in (
            ("tx_pmax_cw_dbm_3g5", "정포락선 파형(처프/CW)",
             "waveform: constant envelope (chirp/CW)"),
            ("tx_pavg_ofdm_evm_knee_dbm_3g5", "통신급 선형성(EVM 무릎)",
             "waveform: OFDM at comms-grade linearity")):
        add(f"송신 파형: {lab}", lab_en, X410_HW[k].value -
            X410_HW["tx_pavg_ofdm_evm30_dbm_3g5"].value, "B",
            "⭐같은 하드웨어인데 파형이 평균 송신전력을 정한다(데이터시트 그림 1·2)")
    for e, g, why, why_en in ((12.0, "C", "챔버 저출력", "low-power chamber"),
                              (47.0, "C", "유휴 gNB", "idle gNB"),
                              (63.0, "C", "매크로 셀", "macro cell"),
                              (65.0, "C", "풀로드 gNB", "fully loaded gNB")):
        add(f"조명원을 바꾼다: EIRP {e:.0f} dBm ({why})",
            f"different illuminator: EIRP {e:.0f} dBm ({why_en})", e - base.eirp.value, g,
            "⛔이 EIRP 들은 **남의 송신기**다 — 능동 모노 팔에 그대로 붙이면 시나리오가 섞인다")
    add("정합필터 이득 없음(상시 기준신호 팔)", "no matched-filter gain (always-on pilot arm)",
        -matched_filter_gain_db(base), "C",
        "capture='always_on_pilot' → G_mf 0 dB. ⭐다만 그 팔은 도플러 게이트에서 먼저 걸린다")
    add("대역 400 MHz(X410 최대)", "bandwidth 400 MHz (X410 maximum)",
        10 * math.log10(400e6 / base.b_hz.value), "A",
        "B 는 SNR 에서 약분되지만 G_mf 가정이 37.1 → 43.1 dB 로 커진다")
    for nf, g in ((3.0, "C"), (8.0, "C")):
        add(f"잡음지수 {nf:.0f} dB", f"noise figure {nf:.0f} dB",
            RX_CHAIN["nf_db"].value - nf, g,
            "정본은 데이터시트 6.5 dB[A]. 3 dB 는 외장 LNA, 8 dB 는 3.1 GHz 아래 대역 값")
    for g_dbi in (8.0, 17.0):
        add(f"수신이득 {g_dbi:.0f} dBi", f"Rx antenna gain {g_dbi:.0f} dBi",
            g_dbi - RX_CHAIN["grx_dbi"].value, "C",
            "3.5 GHz 상용 패널의 실제 범위. 쓸 안테나가 정해지면 [A]")
    for L in (1.0, 4.0):
        add(f"시스템 손실 {L:.0f} dB", f"system loss {L:.0f} dB",
            -(L - RX_CHAIN["sys_loss_db"].value), "C", "정본 2 dB 의 관행 범위")
    add("σ 앵커 +3 dB", "sigma anchor +3 dB", 3.0, "A",
        "앵커 자체는 [A] 지만 ±3 dB 는 자세·기체 산포 폭")
    add("σ 앵커 −3 dB", "sigma anchor -3 dB", -3.0, "A", "같음")
    add("⭐앵커를 움직이는 성분에(S3)", "anchor on the moving part instead (S3)", 31.13, "C",
        "회절 켠 팔이 되돌려받는 양(outputs/noise_distance_frame.json:sensitivity). "
        "⛔팔마다 다른 값이라 공통모드가 아니다 — 여기 수는 그 팔의 것이고 인용 대상이 아니다")
    add("⭐기준채널 현실화 ρ_ref 30 dB", "realistic reference channel, rho_ref 30 dB",
        -REFERENCE_CHANNEL["measured_loss_db_by_rho"]["30"],
        "C", REFERENCE_CHANNEL["what_it_means_ko"], geom="bistatic")
    add("⭐기준채널 현실화 ρ_ref 20 dB", "realistic reference channel, rho_ref 20 dB",
        -REFERENCE_CHANNEL["measured_loss_db_by_rho"]["20"],
        "C", "패시브 팔에만 붙는다(능동 모노는 자기 파형을 안다)", geom="bistatic")
    for iso in (40.0, 60.0, 80.0):
        pn = phase_noise_floor(base, iso)
        add(f"⭐⭐송신 위상잡음 바닥(격리 {iso:.0f} dB)",
            f"Tx phase-noise floor (Tx-Rx isolation {iso:.0f} dB)",
            -pn["excess_over_thermal_db"], "A",
            f"데이터시트 −91 dBc/Hz @1 kHz. 격리 {pn['isolation_for_parity_db']:.0f} dB 아래면 "
            f"열잡음이 아니라 이쪽이 바닥이다. ⚠거리상관 상쇄 미포함(상한)")
    # ── 잣대 쪽(곡선을 다시 재야 하는 규약) ──────────────────────────────── #
    for r in CPI_LADDER:
        if r["d_vs_canon_db"] is None or r["n"] == 8192:
            continue
        add(f"관측시간 CPI {r['cpi_ms']:.0f} ms ({r['label_ko']})",
            f"observation time CPI {r['cpi_ms']:.0f} ms ({r['label_en']})",
            -r["d_vs_canon_db"], "A",
            "⭐측정값 — 잣대 곡선 자체가 바뀐다. 이 원장의 416 ms 는 저장소에서 가장 긴 CPI 다",
            side="metric")
    add("⭐바이스태틱 한 다리만 움직일 때", "bistatic, only one leg moves", 0.0, "A",
        "같은 ΔSNR 이 거리를 **두 배(dB 기준)** 더 움직인다 — 지수 40 → 20. "
        "이 표의 배수는 헤드라인 기하(모노)의 것이다", side="geometry")
    return rows


# --------------------------------------------------------------------------- #
#  7. 잣대 쪽 게이트 실측 — CPI 사다리 · PRF 불변성 (원장 시계열만 읽는다)
# --------------------------------------------------------------------------- #
def measure_metric_gates(arm_key: str = "ours_r15_n8192/el-30", n_trial: int = 300,
                         n_null: int = 4000, seed: int = 7) -> dict:
    """⭐CPI_LADDER · PRF_INVARIANCE 를 **다시 잰다**(모듈 상수는 이 함수의 산물이다).

    ⛔신호를 새로 만들지 않는다 — 저장된 슬로타임 열을 자르거나 솎을 뿐이다.
    CPU 로 3~5 분. 이 값들이 모듈 상수와 어긋나면 자가검사 8 이 잡는다."""
    import numpy as np
    led = json.load(open(LEDGER_JSON))
    z = np.load(LEDGER_NPZ)
    prf0 = float(led["_meta"]["prf_hz"])
    f_flash = float(led["_meta"]["f_flash_hz"])
    eng, el = arm_key.rsplit("/", 1)
    row = [r for r in led["rows"] if r["engine"] == eng
           and (f"el{int(r['el_deg']):+d}".replace("+0", "+0") == el
                or (el == "el+0" and float(r["el_deg"]) == 0.0)
                or f"el{int(r['el_deg']):d}" == el)][-1]
    f_tip = float(row["f_tip_hz"])
    hw = METRIC["comb_halfwidth_hz"].value
    E0 = np.asarray(z[arm_key], complex)

    def _masks(n, prf):
        fr = np.abs(np.fft.fftfreq(n, 1.0 / prf))
        k = fr / f_flash
        band = (fr >= 2.0 * f_flash) & (fr <= f_tip)
        on = band & (np.abs(k - np.round(k)) * f_flash <= hw)
        off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= hw)
        return on, off

    def _comb(X, w, on, off):
        Xc = (X - X.mean(axis=1, keepdims=True)) * w
        P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
        return 10.0 * np.log10(np.maximum(P[:, on].mean(axis=1), 1e-300)
                               / np.maximum(P[:, off].mean(axis=1), 1e-300))

    snrs = np.arange(-40.0, 25.1, 1.0)

    def _one(E, prf):
        n = E.size
        on, off = _masks(n, prf)
        if on.sum() < 4 or off.sum() < 4:
            return dict(ok=False, n=n, cpi_ms=round(n / prf * 1e3, 2),
                        df_hz=round(prf / n, 3), n_on=int(on.sum()), n_off=int(off.sum()))
        w = np.hanning(n)
        Eu = E / math.sqrt(float(np.mean(np.abs(E - E.mean()) ** 2)))
        rng = np.random.default_rng(seed)
        nul, done = [], 0
        while done < n_null:
            m = min(400, n_null - done)
            Z = (rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n))) / math.sqrt(2)
            nul.append(_comb(Z, w, on, off))
            done += m
        bar = float(np.quantile(np.concatenate(nul), 0.999))
        ys = []
        for s in snrs:
            a = 10.0 ** (s / 20.0)
            acc, done = [], 0
            while done < n_trial:
                m = min(200, n_trial - done)
                Z = (rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n))) / math.sqrt(2)
                acc.append(_comb(a * Eu[None, :] + Z, w, on, off))
                done += m
            ys.append(float(np.mean(np.concatenate(acc))))
        ys = np.asarray(ys)
        ok = ys >= bar
        if not ok.any():
            cross = None
        elif ok.all() or int(np.argmax(ok)) == 0:
            cross = float(snrs[0])
        else:
            i = int(np.argmax(ok))
            cross = float(snrs[i - 1] + (bar - ys[i - 1]) / (ys[i] - ys[i - 1])
                          * (snrs[i] - snrs[i - 1]))
        return dict(ok=True, n=n, cpi_ms=round(n / prf * 1e3, 2), df_hz=round(prf / n, 3),
                    n_on=int(on.sum()), n_off=int(off.sum()), bar_p999_db=round(bar, 3),
                    cross_snr_db=(None if cross is None else round(cross, 3)),
                    clean_comb_db=round(float(_comb(Eu[None, :], w, on, off)[0]), 2))

    cpi_rows = [_one(E0[:n], prf0) for n in (8192, 4096, 2048, 1024, 512, 256)]
    base = cpi_rows[0]["cross_snr_db"]
    for r in cpi_rows:
        r["d_vs_canon_db"] = (None if not r.get("ok") or r["cross_snr_db"] is None
                              else round(r["cross_snr_db"] - base, 3))
        r["R_mult"] = (None if r["d_vs_canon_db"] is None
                       else round(10.0 ** (-r["d_vs_canon_db"] / 40.0), 4))
    prf_rows = []
    for dec in (1, 2, 4, 8):
        r = _one(E0[::dec], prf0 / dec)
        if not r.get("ok"):
            continue
        r.update(dec=dec, prf_hz=prf0 / dec,
                 expected_shift_db=round(10 * math.log10(dec), 3),
                 measured_shift_db=round(r["cross_snr_db"] - base, 3))
        r["residual_db"] = round(r["measured_shift_db"] - r["expected_shift_db"], 3)
        prf_rows.append(r)
    return dict(arm=arm_key, f_tip_hz=f_tip, f_flash_hz=f_flash, prf0_hz=prf0,
                n_trial=n_trial, n_null=n_null, seed=seed,
                cpi_ladder=cpi_rows, prf_invariance=prf_rows)


#: 본판이 쓸 팔·거리 패턴 (docs/STANDARD_FRAME.md 2026-08-16 세 팔 + 보존된 반례 둘)
ARM_PATTERNS = {
    "ours": "ours_r{R}_n8192",
    "ps_off": "sionna_p4000000000_r{R}_n8192_d1",
    "ps_refr": "sionna_p4000000000_onlyrefr_r{R}_n8192",
    "ours_ptd": "ours_ptd_r{R}_n8192",
    "ps_phys": "sionna_p4000000000_phys_r{R}_n8192_d1",
}


def audit_panels(ranges=(15, 30, 60, 120, 240, 480),
                 els=((-30.0, "el-30"), (0.0, "el+0"), (-60.0, "el-60"))) -> dict:
    """⭐거리 팔 재고 조사 — «어느 칸이 미터를 낼 자격이 있나» 와 «A1 을 믿어도 되나».

    두 가지를 잰다. 둘 다 링크버짓의 **입력 자격**이라 여기서 잰다(판정 규약 자체는
    benchmark/noise_distance_judge.py 소관 — 이 함수는 그쪽이 쓸 **사실**만 만든다).

    ⓐ **칸 자격** — `n_missing` 만으로는 부족하다는 것이 이번에 드러났다. 실제로
       `n_missing=0` 인데 8192 표본이 **전부 같은 값**인 칸이 있다(얼어붙은 칸). 그런 칸의
       빗살 대비는 물리가 아니라 반올림이다. 그래서 네 조건을 다 본다:
       n_missing=0 · 0 표본 없음 · 서로 다른 값 ≥90 % · AC/총 > −100 dB.

    ⓑ **A1 을 믿어도 되나** — A1 은 «15 m 모양을 얼리고 거리로 잡음만 바꾼다» 는 축이다.
       그 전제가 참인지 재려면 엔진이 그 거리에서 **실제로 다시 계산한** 열과 15 m 열의
       모양을 대 보면 된다. 여기서는 정지 성분을 뺀 뒤의 복소 상관 |ρ_AC| 를 쓴다."""
    import numpy as np
    led = json.load(open(LEDGER_JSON))
    z = np.load(LEDGER_NPZ)
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}
    cells, drift = [], {}
    for arm, pat in ARM_PATTERNS.items():
        base = {}
        for el, ek in els:
            for R in ranges:
                eng, key = pat.format(R=R), f"{pat.format(R=R)}/{ek}"
                if key not in z.files or (eng, el) not in rows:
                    continue
                x = np.asarray(z[key], complex)
                n_missing = int(rows[(eng, el)].get("n_missing") or 0)
                n_zero = int((x == 0).sum())
                uniq = float(len(np.unique(x)) / x.size)
                tot = float(np.mean(np.abs(x) ** 2))
                ac = float(np.mean(np.abs(x - x.mean()) ** 2))
                ac_db = 10.0 * math.log10(max(ac, 1e-300) / max(tot, 1e-300))
                fails = []
                if n_missing:
                    fails.append(f"n_missing={n_missing}")
                if n_zero:
                    fails.append(f"zeros={n_zero}")
                if uniq < 0.90:
                    fails.append(f"frozen(uniq={uniq:.0%})")
                if ac_db < -100.0:
                    fails.append(f"numeric_floor(AC/total={ac_db:.0f}dB)")
                cells.append(dict(arm=arm, range_m=R, el=ek, engine=eng,
                                  n_missing=n_missing, unique_frac=round(uniq, 4),
                                  ac_over_total_db=round(ac_db, 2),
                                  eligible=not fails, fails=fails))
                if R == 15:
                    base[ek] = x
                elif ek in base and not fails:
                    a, b = base[ek] - base[ek].mean(), x - x.mean()
                    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
                    drift.setdefault(f"{arm}_{ek}", []).append(
                        dict(range_m=R, rho_ac=round(float(abs(np.vdot(a, b)) / (na * nb)), 4)))
    return dict(
        cells=cells,
        n_ineligible=sum(1 for c in cells if not c["eligible"]),
        ineligible=[c for c in cells if not c["eligible"]],
        a1_shape_drift=drift,
        a1_verdict={k: dict(
            rho_ac_at_farthest=v[-1]["rho_ac"], farthest_m=v[-1]["range_m"],
            trust_A1=bool(v[-1]["rho_ac"] >= 0.9),
            note_ko=("A1 연장선을 그대로 써도 된다" if v[-1]["rho_ac"] >= 0.9 else
                     "⛔A1 은 «기울기» 로만 읽어라 — 엔진이 그 거리에서 계산한 모양이 "
                     "15 m 모양과 다르다. 헤드라인 거리는 A2 사다리에서 내야 한다"))
                    for k, v in drift.items() if v},
        rule_ko="⭐n_missing 만으로는 부족하다 — 얼어붙은 칸(전 표본 동일)이 그 검사를 통과한다. "
                "네 조건을 다 본다: n_missing=0 · 0 표본 없음 · 서로 다른 값 ≥90 % · "
                "AC/총 > −100 dB(canon near_numeric_floor 규칙)")


# --------------------------------------------------------------------------- #
#  8. 자가검사
# --------------------------------------------------------------------------- #
def selftest(measured: dict | None = None) -> dict:
    st = {}
    base = SCENARIOS[HEADLINE_SCENARIO]
    # 1. 잡음전력 — 이전 판(NF 5)은 원장과 비트 수준으로 같고, 정본(NF 6.5)은 1.5 dB 높다
    n_legacy = noise_power_w(base, nf_db=LEGACY_RX_CHAIN["nf_db"])
    n_canon = noise_power_w(base)
    st["1_noise_matches_ledger"] = dict(
        ok=(abs(n_legacy - 2.4942932229992773e-16) < 1e-28
            and abs(10 * math.log10(n_canon / n_legacy) - 1.5) < 0.01),
        legacy_w=n_legacy, canon_w=n_canon,
        canon_minus_legacy_db=round(10 * math.log10(n_canon / n_legacy), 3),
        note_ko="이전 판 값은 detection_curves.json·noise_distance_frame.json 과 비트동일, "
                "정본은 데이터시트 NF 6.5 dB 라 정확히 +1.5 dB")
    # 2. 정합필터 이득 — 풀캡처 37.06 dB, 상시 기준신호 0 dB
    g_full = matched_filter_gain_db(base)
    g_pilot = matched_filter_gain_db(SCENARIOS["passive_lte_crs"])
    st["2_mf_gain"] = dict(ok=abs(g_full - 37.06) < 0.01 and g_pilot == 0.0,
                           full_waveform_db=round(g_full, 3), always_on_pilot_db=g_pilot)
    # 3. 거리 배수가 1/R⁴ 과 맞나 + 바이스태틱 지수
    st["3_r_multiplier"] = dict(
        ok=(abs(r_multiplier(40.0) - 10.0) < 1e-12
            and abs(r_multiplier(20.0, "bistatic") - 10.0) < 1e-12),
        mono_40db=r_multiplier(40.0), bistatic_20db=r_multiplier(20.0, "bistatic"),
        note_ko="모노 +40 dB = 거리 10 배 · 바이스태틱 한 다리 +20 dB = 10 배")
    # 4. ⭐선언값 게이트가 실제로 막나 (헤드라인은 이제 [D] 가 없어야 한다)
    dec_head = base.declared()
    blocked_wifi = False
    try:
        budget_report(SCENARIOS["passive_wifi"])
    except ValueError:
        blocked_wifi = True
    st["4_declared_gate"] = dict(
        ok=(dec_head == []), headline_declared=dec_head,
        headline_quotable=budget_report(base)["absolute_range_quotable"],
        note_ko="⭐2026-08-16 개정으로 헤드라인의 [D] 가 0 개가 됐다(EIRP·NF·손실이 전부 "
                "데이터시트/관행으로 내려왔다). 게이트는 그대로 살아 있다",
        other_arm_blocked_without_flag=blocked_wifi)
    # 5. 미확보 상수는 예외로 막힌다
    bad = Scenario("bad", "", "", Const(None, "dBm", "D", "미확보"),
                   base.prf, base.b_hz, "full_waveform", "monostatic")
    raised = False
    try:
        budget_report(bad, allow_declared=True)
    except ValueError:
        raised = True
    st["5_unresolved_raises"] = dict(ok=raised,
                                     still_unresolved=[k for k, v in
                                                       {**X410_HW, **REGULATORY}.items()
                                                       if not v.resolved])
    # 6. ⭐도플러 게이트 — 상시 기준신호 팔은 잣대가 성립하지 않는다
    ft = METRIC["f_tip_hz_el_minus30"].value
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
            and X410_HW["adc_bits"].value == hw.adc_bits
            and X410_HW["n_rx"].value == hw.n_rx),
        dynamic_range_db=round(hw.dynamic_range_db, 1),
        unresolved=[k for k, v in X410_HW.items() if not v.resolved],
        note_ko="⭐송신전력·잡음지수·위상잡음이 이제 데이터시트에서 왔다. 남은 미확보는 "
                "송신→수신 격리 하나이고, 그것이 위상잡음 게이트의 입력이다")
    # 8. ⭐CPI 게이트 — 정본은 통과, 13 ms 는 붕괴
    g_canon = cpi_feasible(METRIC["cpi_s"].value)
    g_20ms = cpi_feasible(0.020)
    st["8_cpi_gate"] = dict(ok=(g_canon["ok"] and not g_20ms["ok"]),
                            canon=g_canon, x410_default_20ms=g_20ms,
                            ladder_collapse_at_ms=13.0,
                            note_ko="⭐experiment_x410.detection_config 기본 T_CPI 20 ms 로는 "
                                    "빗살 잣대가 성립하지 않는다 — 이 원장의 416 ms 는 그 규약과 "
                                    "**다른 규약**이고, 그 사실을 본판이 적어야 한다")
    # 9. ⭐PRF 불변성 — 잔차가 작아야 한다
    res = [abs(r["residual_db"]) for r in PRF_INVARIANCE]
    st["9_prf_invariance"] = dict(
        ok=max(res) < 0.5, max_residual_db=round(max(res), 3),
        R_error_pct=round(100 * (10 ** (max(res) / 40.0) - 1), 2), rows=PRF_INVARIANCE,
        note_ko=PRF_INVARIANCE_NOTE_KO)
    # 10. ⭐위상잡음 게이트 — 필요한 격리가 실제로 큰가
    pn = phase_noise_floor(base, isolation_db=60.0)
    st["10_phase_noise_gate"] = dict(
        ok=pn["isolation_for_parity_db"] > 60.0, at_isolation_60db=pn,
        note_ko="⭐격리 60 dB(현실적인 별도 안테나 배치)에서도 위상잡음이 열잡음보다 "
                "높다면, 능동 모노 팔의 «몇 미터» 는 열잡음 예산이 말하는 값보다 짧다")
    # 12. ⭐칸 자격 — n_missing 만으로 못 잡는 «얼어붙은 칸» 이 실제로 있나
    pa = audit_panels()
    frozen = [c for c in pa["ineligible"]
              if any(f.startswith("frozen") for f in c["fails"]) and c["n_missing"] == 0]
    st["12_panel_eligibility"] = dict(
        ok=bool(frozen), n_ineligible=pa["n_ineligible"],
        frozen_but_n_missing_zero=[f"{c['arm']}_r{c['range_m']}_{c['el']}" for c in frozen],
        a1_verdict={k: v["trust_A1"] for k, v in pa["a1_verdict"].items()},
        note_ko="⭐ok=True 는 «결함을 찾았다» 는 뜻이다 — n_missing=0 인데 얼어붙은 칸이 "
                "실재하므로 본판의 자격 게이트가 그 조건을 반드시 포함해야 한다")
    # 11. 측정을 다시 했다면 모듈 상수와 맞나
    if measured:
        d = []
        for got, want in zip(measured["cpi_ladder"], CPI_LADDER):
            if got.get("cross_snr_db") is None or want["cross_snr_db"] is None:
                continue
            d.append(abs(got["cross_snr_db"] - want["cross_snr_db"]))
        st["11_measured_matches_constants"] = dict(
            ok=bool(d and max(d) < 1.0), max_dev_db=round(max(d), 3) if d else None)
    st["ok"] = all(v.get("ok") for v in st.values() if isinstance(v, dict))
    return st


# --------------------------------------------------------------------------- #
#  9. 원장 + 그림
# --------------------------------------------------------------------------- #
#: 현행(이전 판 예산) 판독거리 — 본판이 덮어쓸 «잠정» 수. 여기 두는 이유는 예산 배수를
#: 곱해서 «옮긴 값» 을 원장에 같이 남기기 위해서다. 출처: outputs/noise_distance_frame.json
#: ⭐`quotable` 은 docs/STANDARD_FRAME.md(2026-08-16 사용자 확정)의 인용 규칙이다.
#: 세 팔(ours · ps_off · ps_refr)만 앞으로 계산·인용하고, 나머지 둘은 **보존된 반례**다.
PROVISIONAL_R_M = {
    "ours": dict(read=554.0, pd90=640.0, quotable=True,
                 why_ko="표준 프레임 세 팔 중 하나"),
    "ps_off": dict(read=641.0, pd90=700.0, quotable=True,
                   why_ko="표준 프레임 세 팔 중 하나(PathSolver 상한)"),
    "ps_refr": dict(read=556.0, pd90=620.0, quotable=True,
                    why_ko="표준 프레임 세 팔 중 하나(공장 기본값 + 확산)"),
    "ours_ptd": dict(read=656.0, pd90=753.0, quotable=False,
                     why_ko="⛔새 축에 안 태운다(자세당 1.3 s = 순정의 10 배, 확장 7 칸 "
                            "|Δ| ≤ 0.02 dB). 이미 낸 15 m 판만 «모서리 회절 무시 안 했다» 의 답으로"),
    "ps_phys": dict(read=47.0, pd90=63.0, quotable=False,
                    why_ko="⛔⛔**절대 수치 인용 금지**(STANDARD_FRAME 2026-08-16). 날개끝 위 "
                           "바닥이 광선 수에 매여 있어(광선 4배에 +6.2~6.9 dB) 정본이 될 수 없다. "
                           "쓸 수 있는 것은 정성적 사실 하나뿐 — «회절을 켜면 무늬가 잠긴다». "
                           "⭐즉 «47 m» 는 본판에서 **미터로 나오지 않는다**"),
}


def restated_provisional() -> dict:
    """⭐이전 판 예산의 잠정 거리를 정본 예산으로 옮긴 값(재계산 전 예측)."""
    sh = legacy_shift_db()
    m = sh["R_multiplier"]
    return dict(shift=sh,
                rows={k: dict(read_m_legacy=v["read"], pd90_m_legacy=v["pd90"],
                              read_m_canon=(round(v["read"] * m, 1) if v["quotable"] else None),
                              pd90_m_canon=(round(v["pd90"] * m, 1) if v["quotable"] else None),
                              quotable=v["quotable"], why_ko=v["why_ko"])
                      for k, v in PROVISIONAL_R_M.items()},
                quoting_rule_ko="⛔인용 가능한 팔은 표준 프레임 세 팔(ours·ps_off·ps_refr)뿐이다 "
                                "— docs/STANDARD_FRAME.md 2026-08-16 사용자 확정. 회절 켠 팔은 "
                                "**미터를 내지 않는다**",
                caveat_ko="⛔이 표는 **예산만** 옮긴 값이다. 재질 정본·판정 막대·자격 게이트가 "
                          "따로 움직이므로 본판의 최종 수와 다르다 — 예산 축의 예측치일 뿐이다")


def write_ledger(measure: bool = False, path: str = OUT_JSON) -> dict:
    t0 = time.time()
    meas = measure_metric_gates() if measure else None
    base = SCENARIOS[HEADLINE_SCENARIO]
    out = dict(
        _meta=dict(
            generator="benchmark/link_budget_spec.py",
            generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
            role_ko="«몇 미터에서 보이나» 의 **분모**를 정본으로 만든다 — 상수마다 근거 등급, "
                    "규약마다 거리 배수, 그리고 답을 낼 자격이 있는지의 게이트",
            gpu_used=False,
            gpu_note_ko="⛔GPU·솔버 임포트 없음. 데이터시트 판독과 저장된 원장 읽기뿐",
            datasheet=DATASHEET,
            inputs=["outputs/elevation_sweep_md.{json,npz} (잣대 게이트 실측용)",
                    "outputs/noise_distance_frame.json (옮길 잠정 거리)",
                    "outputs/passive_two_channel.json (기준채널 손실 법칙)",
                    "src/sigma_anchor.py (σ 앵커)"],
            grades_ko={"A": "규격서·물리상수", "B": "문헌·데이터시트 그림 판독",
                       "C": "관행(범위는 안다)", "D": "순수 선언"},
            headline_scenario=HEADLINE_SCENARIO),
        constants=dict(
            physics={k: asdict(v) for k, v in PHYSICS.items()},
            target={k: asdict(v) for k, v in TARGET.items()},
            x410={k: asdict(v) for k, v in X410_HW.items()},
            rx_chain={k: asdict(v) for k, v in RX_CHAIN.items()},
            tx_antenna={k: asdict(v) for k, v in TX_ANTENNA.items()},
            regulatory={k: asdict(v) for k, v in REGULATORY.items()},
            metric={k: asdict(v) for k, v in METRIC.items()},
            legacy_rx_chain=dict(LEGACY_RX_CHAIN)),
        grade_census={g: sorted(
            [f"{grp}.{k}" for grp, d in (("x410", X410_HW), ("rx", RX_CHAIN),
                                         ("tx_ant", TX_ANTENNA), ("target", TARGET),
                                         ("metric", METRIC), ("reg", REGULATORY))
             for k, v in d.items() if v.grade == g]) for g in GRADES},
        scenarios={k: dict(
            budget_report(s, allow_declared=True),
            doppler_gate=doppler_feasible(s, METRIC["f_tip_hz_el_minus30"].value),
            note_ko=s.note_ko) for k, s in SCENARIOS.items()},
        scenario_shifts={k: snr_shift_db(base, s) for k, s in SCENARIOS.items()},
        legacy_shift=legacy_shift_db(),
        restated_provisional=restated_provisional(),
        sensitivity=sensitivity_table(),
        metric_side=dict(cpi_ladder=CPI_LADDER, prf_invariance=PRF_INVARIANCE,
                         prf_note_ko=PRF_INVARIANCE_NOTE_KO,
                         cpi_gate_canon=cpi_feasible(METRIC["cpi_s"].value),
                         cpi_gate_x410_default=cpi_feasible(0.020)),
        reference_channel=REFERENCE_CHANNEL,
        phase_noise=dict(
            rows={f"iso{int(i)}": phase_noise_floor(base, i) for i in (40, 50, 60, 70, 80, 90)},
            headline_ko="⭐능동 모노스태틱의 바닥은 열잡음이 아닐 수 있다 — 데이터시트 "
                        "−91 dBc/Hz @1 kHz 가 우리 무늬 자리에 있다"),
        panel_audit=audit_panels(),
        measured=meas,
        selftest=selftest(meas))
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1, default=str)
    print(f"  ✅ {path}")
    make_figure(out)
    return out


def make_figure(out: dict, png: str = OUT_PNG) -> None:
    """규약 사다리 한 장 — «같은 물리, 다른 규약이면 거리가 어디로 가나».

    색은 검증된 기성 팔레트(dataviz references/palette.md 고정 슬롯)를 그대로 쓴다."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
    MUTED, SURFACE, INK, INK2 = "#52514e", "#fcfcfb", "#0b0b0b", "#52514e"
    side_color = {"budget": SLOT[0], "metric": SLOT[1], "geometry": MUTED}

    rows = [r for r in out["sensitivity"] if r["side"] != "geometry" and r["d_snr_db"] != 0.0]
    rows.sort(key=lambda r: r["R_multiplier"])
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(13.2, 0.36 * len(rows) + 3.0), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for i, r in enumerate(rows):
        ax.plot([1.0, r["R_multiplier"]], [i, i], color=side_color[r["side"]], lw=2.0,
                alpha=0.85, solid_capstyle="round")
        ax.plot([r["R_multiplier"]], [i], marker="o", ms=6.5, color=side_color[r["side"]],
                mec=SURFACE, mew=1.1)
        ax.text(r["R_multiplier"] * (1.09 if r["R_multiplier"] >= 1 else 0.92), i,
                f"×{r['R_multiplier']:.2f}", va="center",
                ha="left" if r["R_multiplier"] >= 1 else "right",
                fontsize=8.2, color=INK2)
    ax.axvline(1.0, color=INK, lw=1.3)
    ax.set_ylim(-1.6, len(rows) - 0.4)
    ax.set_yticks(y)
    ax.set_yticklabels([f"[{r['grade']}]  {r['knob_en']}" for r in rows],
                       fontsize=8.8, color=INK)
    ax.set_xscale("log")
    ax.set_xlabel("Reading-distance multiplier vs the canonical budget   "
                  "(monostatic, R ∝ 10^(ΔSNR/40))", color=INK)
    ax.set_xlim(0.03, 20)
    ax.grid(True, axis="x", which="both", color="0.92", lw=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=8.8)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.text(1.0, len(rows) - 0.55, "canonical budget", rotation=90, fontsize=8.2,
            color=INK2, ha="right", va="top")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color=side_color["budget"], lw=2.4,
                              label="budget knob — moves the range→SNR map only"),
                       Line2D([], [], color=side_color["metric"], lw=2.4,
                              label="metric knob — the readability curve itself changes")],
              loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=8.8,
              frameon=True, framealpha=0.95, edgecolor="0.85")
    sc = out["scenarios"][HEADLINE_SCENARIO]
    fig.suptitle("How far can we read it? — what the answer's denominator is made of",
                 fontsize=13.5, color=INK)
    foot = (f"Canonical budget: EIRP {sc['eirp_dbm']:.1f} dBm "
            f"(X410 OFDM avg {X410_HW['tx_pavg_ofdm_evm30_dbm_3g5'].value:.0f} dBm + "
            f"{TX_ANTENNA['gtx_dbi'].value:.0f} dBi antenna) · G_rx {sc['grx_dbi']:.0f} dBi · "
            f"NF {sc['nf_db']:.1f} dB (datasheet) · loss {sc['sys_loss_db']:.0f} dB · "
            f"CPI {sc['cpi_s']*1e3:.0f} ms · monostatic 1/R⁴ · σ anchor "
            f"{sc['sigma_ref_dbsm']:.2f} dBsm\n"
            "Evidence grades — [A] spec sheet or physical constant · [B] literature or "
            "datasheet figure · [C] common practice, range known · [D] pure declaration\n"
            "⚠ No measured cross-check exists yet: the arms' relative order is verified, "
            "the absolute metres are not")
    fig.text(0.5, 0.008, foot, ha="center", va="bottom", fontsize=8.2, color=INK2,
             linespacing=1.6)
    fig.tight_layout(rect=(0, 0.105, 1, 0.955))
    os.makedirs(os.path.dirname(png), exist_ok=True)
    fig.savefig(png, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"  ✅ {png}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="링크버짓 정본 — 상수 등급·규약 감도·게이트")
    ap.add_argument("--ledger", action="store_true", help="원장 JSON + 그림을 쓴다")
    ap.add_argument("--measure", action="store_true", help="잣대 게이트를 다시 잰다(CPU 3~5분)")
    a = ap.parse_args()
    if a.ledger:
        o = write_ledger(measure=a.measure)
        print(json.dumps(dict(selftest_ok=o["selftest"]["ok"],
                              legacy_shift_db=o["legacy_shift"]["d_total_db"],
                              R_multiplier=o["legacy_shift"]["R_multiplier"]),
                         ensure_ascii=False, indent=1))
    else:
        st = selftest()
        print(json.dumps(st, ensure_ascii=False, indent=1, default=str))
    print("\n=== 감도표 (헤드라인 시나리오 기준) ===")
    for r in sensitivity_table():
        print(f"  [{r['grade']}] {r['side']:8s} {r['knob_ko'][:44]:46s} "
              f"Δ={r['d_snr_db']:+7.2f} dB  ×R={r['R_multiplier']:.4f}")
    print("\n=== 시나리오 사다리 ===")
    for k, s in SCENARIOS.items():
        g = doppler_feasible(s, METRIC["f_tip_hz_el_minus30"].value)
        tip = "볼 수 있음" if g["ok"] else f"접힘 ×{g['fold_factor']}"
        print(f"  {k:26s} EIRP {s.eirp.value:5.1f} dBm[{s.eirp.grade}] · "
              f"PRF {s.prf.value:8.1f} Hz[{s.prf.grade}] · G_mf {matched_filter_gain_db(s):5.2f} dB "
              f"· 날개끝 {tip} · {s.licensing}")
    print("\n=== 이전 판 → 정본 예산 ===")
    rp = restated_provisional()
    print(f"  총 이동 {rp['shift']['d_total_db']:+.2f} dB → 거리 ×{rp['shift']['R_multiplier']:.4f}")
    for k, v in rp["rows"].items():
        if not v["quotable"]:
            print(f"    {k:10s} ⛔인용 금지 — {v['why_ko'][:60]}")
            continue
        print(f"    {k:10s} 판독 {v['read_m_legacy']:6.0f} → {v['read_m_canon']:6.1f} m "
              f"· Pd90 {v['pd90_m_legacy']:6.0f} → {v['pd90_m_canon']:6.1f} m")
