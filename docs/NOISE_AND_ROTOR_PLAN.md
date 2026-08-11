# 잡음 주입 · 로터 랜덤성 — 착수 설계안 (2026-08-10)

> ## ⭐진행 상태 (2026-08-11 02:xx 갱신)
>
> | 항 | 상태 |
> |---|---|
> | §0-1 SNR 규약 둘 | ✅ **반영 완료.** 규약 v2 코드에 못 박힘 · 게이트 `verify_snr_convention.py` **6/6** |
> | §0-2 정합필터 이득 누락 | ✅ **반영 완료.** 게이트 `verify_matched_filter_gain.py` **5/5** + 독립 구현 대조 1.4e-14 dB |
> | §0-2 의 거리 예측 «35~42 m» | ⛔ **실측이 반박했다** — 아래 §0-2 의 정정 상자 |
> | §1-2 상시 기준신호 팔(G_mf = 0 dB) | ⛔ **새 결함.** 44~50 dB 비관적이고 거짓 주장을 만든다 — §0-2 두 번째 정정 상자 · `RETRACTION_LOG` R17 |
> | 사다리의 듀티 항 | ⛔ **없다.** `freespace_link.duty_db_from_cpi` 재사용해서 넣어야 한다 |
> | §0-3 로터 랜덤성 (§2 전체) | 진행 중(형제 에이전트) — `outputs/rotor_jitter_model.json` · `verify_rotor_dynamics.json` |
> | §3-3 G12 (사다리 ↔ 실사슬) | ❌ **미착수. «37 dB 를 실제로 번다» 의 유일한 관문이다** |
>
> 적대검증 기록과 남은 일은 `docs/RESUME.md` 맨 위 블록에 있다.
> 정정 4건은 `docs/RETRACTION_LOG.md` R14~R17.

> **이 문서는 «다음 세션이 그대로 착수하는 지시서» 다.** 코드는 한 줄도 안 고쳤다.
> 각 항목은 «어느 파일의 어느 함수에 어떤 인자를 넣고 어느 원장에 어떤 키를 낸다» 수준으로 쓴다.
>
> **이 문서의 수치 원장**: `outputs/noise_rotor_plan.json` (여기 나오는 모든 수가 들어 있다)
>
> **근거 문서** (먼저 읽어라, 여기서 다시 논증하지 않는다)
> · `prior_work/noise_modeling_survey.md` + `outputs/noise_modeling_survey.json` — 잡음 조사
> · `prior_work/rotor_randomness_survey.md` + `outputs/rotor_randomness_survey.json` — 로터 조사
> · `outputs/rotor_rpm_web_anchor.json` — 실기 로그 3원천 앵커
>
> **⛔ 지금 GPU 를 쓰지 마라**(다른 작업 점유). §4 가 GPU 필요 단계를 따로 표시한다.
> **표기 규약**: `[조사]` = 위 두 조사에서 온 것, `[신규]` = 이 문서에서 처음 계산한 것,
> `[선언]` = 출처 없는 우리 가정.

---

## 0. ⭐이 문서에서 새로 나온 사실 셋 — 조사 두 편에 없던 것

착수 전에 이것부터 읽어야 한다. 셋 다 **설계를 바꾼다**.

### 0-1. 우리 코드에 SNR 규약이 이미 **두 개** 있고 서로 다르다 `[신규]`

| 어디 | 코드 | 기준 |
|---|---|---|
| `src/microdoppler_nearfield.py:369-370` `add_noise()` | `p_sig = mean(abs(E)**2)` | **총전력** (몸체 DC 포함) |
| `benchmark/md_classify_dataset.py:808-809` (`cmd_build`) | `sd = sqrt(mean(abs(E - E.mean())**2))` | **AC 만** (블레이드선) |

두 규약은 `dc_ac_db` 만큼(기체별 **17.3 ~ 37.2 dB**) 다르다. 즉 **«분류가 표본당 0 dB 에서 84 %»**
(`outputs/md_classify.json` `noise["0"]["all"]["RF100"] = 0.8403`)는 **AC 기준**이고,
`experiment_md_range.py` 가 쓰는 `snr_sample_plane_db` 는 **총전력 기준**이다.
지금 두 수를 같은 표에 나란히 놓으면 **최대 37 dB 어긋난다.** §1-2 가 이것을 못 박는다.

### 0-2. ⭐⭐**정합필터 이득 37 dB 가 통째로 빠져 있다** `[신규]`

`echo_over_noise_db()` 는 `P_n = k·T0·F·B`, **B = 100 MHz** 로 잡음을 세운다
(`microdoppler_nearfield.py:330, 349`). 그런데 그 함수가 돌려준 값을 우리는 **슬로타임 표본
E[m] 의 SNR** 로 쓴다(`experiment_md_range.py:124-125` → `add_noise` 에 그대로 투입).

**이건 층위가 틀렸다.** 슬로타임 표본 하나는 «PRI 한 개 분량의 100 MHz 신호를 기준신호와
상관» 해서 나온 **정합필터 출력**이다. 시간·대역폭 곱만큼 이득이 붙는다:

```
G_mf = 10·log10(B / PRF) = 10·log10(100e6 / 19,700) = 37.06 dB
```

즉 우리는 **거리 링크버짓을 37 dB 비관적으로** 쓰고 있었다. 같은 말로,
`P_n` 의 대역은 100 MHz 가 아니라 **슬로타임 표본율 PRF** 여야 한다
(이상적 정합필터 전제에서 두 계산은 동일하다: `kT0F·B / (B/PRF) = kT0F·PRF`).

**수치 확인(오늘 CPU 로 실측)** — 길이 L=5000 의 백색 기준신호에 표본당 −30 dB 에코를 실어
정합필터를 통과시키니 출력 SNR **+6.86 dB**, 예측 `−30 + 10log10(5000) = +6.99 dB`.
차이 0.13 dB(유한 실현). → `G_mf = 10log10(B·T_pri)` 는 맞다.

**파급**: `md_range_sweep.json` 의 «5 m 부터 `fd_edge` 가 NaN(=블레이드선 묻힘)» 은
이 37 dB 를 안 넣은 결과다. 넣으면 같은 문턱(`spec_peak_over_floor_db ≥ 10 dB`)이
~~**R ≈ 35 ~ 42 m** 로 밀린다~~ **⛔이 예측은 2026-08-11 실측이 반박했다 — 아래 상자.**

> ### ⛔ 2026-08-11 정정 — 이 절의 예측 «35~42 m» 는 **틀렸다**
> 새 원장 `outputs/md_range_sweep_mf.json`(잡음 실현 32개, 3.5 GHz·EIRP 12 dBm)의 **실측**:
>
> | 기체 | R90 | R50 | R(첨두 10 dB) |
> |---|---|---|---|
> | mavic4pro | **72.5 m** | 83.7 | 85.9 |
> | s1000plus | 51.2 | 58.8 | 52.8 |
> | **matrice4e** | **22.1 m** | 31.4 | 30.4 |
> | mini5pro | 15.7 | 19.1 | 19.8 |
> | phantom4 | 15.4 | 17.3 | 19.0 |
>
> matrice4e 예측 35~42 m ↔ 실측 R90 22.1 m 는 **8.0 dB** 어긋난다(§3-3 G14 합격선 ±5 dB 초과).
> **원인**: 예측은 사다리 ⑤(맵 조각 nperseg 70, +16.69 dB)로 했고, 측정은 `md_metrics`
> (nperseg 256·평활 주기도·중앙값 바닥 추정)로 했다 — **사슬이 다른 두 수를 비교했다.**
> ⇒ 인용은 위 실측표로만 한다. 방향(«거리가 한 자릿수 밀린다»)은 맞았고 **수는 틀렸다.**

⚠ 단, `G_mf` 는 **풀 웨이브폼 캡처** 전제에서만 성립한다 — PRF 19.7 kHz 로 슬로타임을 뽑으려면
매 PRI(50.8 µs)마다 100 MHz 를 통째로 상관해야 한다. 상시 기준신호(LTE CRS 1 kHz·5G SSB 50 Hz)
로는 그 PRF 가 안 나온다(`experiment_md_range.py:186-189` `prf_feasibility` 가 이미 판정한다).
**그래서 이 이득은 «풀 캡처 팔» 에만 붙인다.** §1-2 의 규약 표에 조건으로 박는다.

> ### ⛔ 2026-08-11 정정 — 상시 기준신호 팔에 «G_mf = 0 dB» 를 쓰면 **거짓 주장**이 된다
> 현행 `matched_filter_gain_db(capture="always_on_pilot")` 은 0 dB 를 돌려준다. 그 값을 그대로
> 읽으면 «상시 기준신호는 풀캡처보다 37 dB 손해» 가 되는데 **반대다.**
> 옳은 값은 반복 1회당 **실제 조명시간** τ_on 으로 `G = 10log10(B·τ_on)` 이고,
> 반복률이 낮을수록 표본당 적분시간이 길어 **SNR 로는 유리하다**.
>
> | 팔 | 코드 | 옳은 값 | 차이 |
> |---|---|---|---|
> | LTE CRS 1 kHz (연속, τ = 1 ms) | 0 dB | **+50.0 dB** | 50.0 |
> | 5G SSB 50 Hz (버스트 τ = 4×71.4 µs, 듀티 −18.45 dB) | 0 dB | **+44.6 dB** | 44.6 |
>
> 그 팔의 진짜 대가는 **도플러 모호**(f_tip 1,229 Hz 가 PRF 1 kHz 에서 접힌다)와 **듀티**다.
> ⇒ 고치기 전까지 그 팔의 수치를 원장·리포트·덱에 **싣지 않는다**(`docs/RETRACTION_LOG.md` R17).
> ⇒ 그리고 사다리에는 **듀티 항이 아예 없다.** 구현은 `src/freespace_link.py::duty_db_from_cpi`
>   를 재사용한다(재구현 금지). 측정: LTE 연속 0.00 · 5G SSB 버스트 −18.45 · WiFi 1 kHz −10.00 dB.

### 0-3. 0.25 s 창에서는 제어루프 흔들림의 **71.6 % 가 «정적 오프셋»으로 보인다** `[신규]`

OU 과정(시상수 T = 1/(2π·0.7 Hz) = **0.2274 s**)을 길이 T_w 인 창으로 보면, 분산이 두 몫으로
갈린다 — «창 평균의 흔들림»(= 사실상 정적 산포)과 «창 안에서의 변화»(= 진짜 비정상성):

```
창평균 몫 = (2T/T_w)·[1 − (T/T_w)(1 − e^(−T_w/T))]
```

| 창 T_w | 창평균 몫 | 창 안 변화 몫 |
|---|---|---|
| 0.05 s | 0.931 | 0.069 |
| **0.25 s** (분류 헤드라인) | **0.716** | 0.284 |
| 1.00 s | 0.353 | 0.647 |
| **2.00 s** (호버 맵) | 0.202 | **0.798** |

**함의 둘**
1. **분류 실험(0.25 s)에서 흔들림을 넣어도 «정적 산포가 커진 것»과 거의 구별되지 않는다.**
   그러니 분류 쪽에서 먼저 고쳐야 할 것은 흔들림이 아니라 **정적 산포 값 자체**다 —
   지금 `RPM_SPREAD_LO/HI = 0.0007/0.0029`(0.07~0.29 %, PX4 **SITL**)인데, 야외 실측 앵커에서
   유도한 **실효 정적 산포는 3.13 %** 다(σ_s 2.35 % 와 σ_w 2.45 % 의 창평균 몫을 합성).
   **10 배 차이**다.
2. 흔들림의 «모양»이 실제로 보이는 곳은 **2 s 호버 맵**과 **T=1.0 s 분류 팔**이다.
   검증 게이트를 그쪽에 걸어야 한다(§3-4).

---

# 1. 잡음 주입 설계

## 1-1. 어디에 무엇을 더하나 — 결론

> **슬로타임 복소열 E(t) 에 복소 백색 가우시안을 더하고, 그 다음 STFT 한다.**
> 스펙트로그램(맵)·전력·dB 이미지에는 **절대 더하지 않는다.**

근거는 조사에 다 있다(`prior_work/noise_modeling_survey.md` §2.3). 요약만:
- Sionna 자신이 그렇게 한다 — `sionna/phy/channel/apply_time_channel.py:195-197` 이 채널
  컨볼루션 **뒤 시간영역**에서 AWGN 을 더한다. 비선형 산출물에 잡음을 더하는 API 는 없다. `[조사]`
- 문헌도 그렇다 — arXiv:2604.12567 본문 *"Noise was applied to the **raw signals** … **before**
  the spectrograms were generated"*, Drones 5(4):149 식 (8) `ψ_final = detection(ψ(t+t_s), p_d) + n`
  **그 다음** STFT. `[조사]`
- 통계가 다르다 — 시계열에 넣으면 맵 잡음 바닥이 **지수분포(χ²₂)**(Braun 식 3.92)가 되고 겹친
  프레임끼리 상관되며 창으로 색이 입혀지고 **신호×잡음 교차항 2Re(s·n\*)** 이 산다. 맵에 실수
  가우시안을 더하면 넷 다 틀린다. `[조사]`
- CFAR 문턱 `η = −σ_N² ln p_FA` 가 σ_N² 과 연결돼 있어야 Pd 를 말할 수 있다. `[조사]`

**우리는 이미 옳은 함수를 갖고 있다** — `src/microdoppler_nearfield.py:365-373` `add_noise()`.
문제는 **맵을 그리는 경로가 그 함수를 안 거친다**는 것뿐이다:
`benchmark/build_deck0811_range_figs.py:88-91 _map()` 은 `.npz` 의 무잡음 E 를 바로
`flash_spec()` 에 넣는다. **여기가 배선 지점이다.**

⚠ 두 가지를 이 층에서 **하지 않는다**(§1-8 참조):
- 클러터·DPI 잔류·ECA 노치 — 그건 `src/passive_process.py` / `benchmark/passive_two_channel_md.py`
  의 일이다. 마이크로도플러 맵 팔은 «열잡음만» 이라고 **명시**한다.
- 위상잡음·양자화 — 지금은 넣지 않는다.

## 1-2. ⭐⭐SNR 규약 — 한 이름으로 못 박는다

**정본 정의(이것 하나만 «SNR» 이라고 부른다):**

> **`snr_slow_ac_db` = 슬로타임 표본 하나에서, 블레이드(AC) 성분 전력 대 잡음 전력의 비 [dB].**

왜 이것인가: (a) 문헌 관례가 «표본당/펄스당» 이다 — arXiv:2403.02080 *"the **single pulse**
SNR … 10log₁₀ A_r²/σ_n²"*, Drones 5:149 식 (7) 도 **블레이드 반사 진폭 A_r 기준** `[조사]`;
(b) 우리 분류 실험이 이미 이 규약이다(§0-1); (c) 검출성을 지배하는 것이 AC 다
(`ac_snr_db()` docstring 이 이미 그렇게 선언).

**그리고 «항상 네 수를 함께 보고한다».** 하나만 쓰면 비교가 성립하지 않는다(조사 §3.1).

| # | 이름 | 정의 | 우리 값의 예 (matrice4e·3.5 GHz·EIRP 12 dBm·R = 10 m) |
|---|---|---|---|
| ① | `snr_band_db` | `P_echo / (k·T0·F·B)`, B = 수신 순시대역 100 MHz. **정합필터 전, 수신 표본당** | **−2.23 dB** |
| ② | `g_mf_db` | `10log10(B / PRF)` — PRI 한 개 상관의 처리이득. **풀 캡처 팔에서만** | **+37.06 dB** |
| ③ | `snr_slow_db` = ①+② | 슬로타임 표본 E[m] 의 **총전력** SNR | **+34.83 dB** |
| ③′| **`snr_slow_ac_db`** = ③ − `dc_ac_off_db` | ⭐**정본.** 블레이드선 SNR | **+17.45 dB** |
| ④ | `g_stft_db` | `10log10(N_seg) + L_win` — STFT 한 조각의 코히어런트 이득 | **+16.69 dB** (N_seg = 70, Hann −1.76) |
| ⑤ | `snr_map_ac_db` = ③′+④ | 맵 위 블레이드선의 첨두 SNR | **+34.14 dB** |

- `dc_ac_off_db = 10log10(1 + 10^(dc_ac_db/10))` — 총전력→AC 변환의 **정확식**.
  ⚠ 현행 `ac_snr_db()` (`microdoppler_nearfield.py:362`)는 `dc_ac_db` 를 **그냥 뺀다**.
  `dc_ac_db ≥ 10 dB` 면 오차 ≤ 0.41 dB(무해)이지만 `dc_ac_db ≈ 0` 이면 **3.0 dB 틀린다**.
  → 정확식을 opt-in 으로 넣고 기본값은 현행 유지(원장 비트 보존).
- `L_win` (창 코히어런트 이득 손실) 근거: Braun 식 (3.76)(3.77), Table 3.3 `[조사]`.
  Hann 은 `|Σw|²/(‖w‖²N) = −1.76 dB`.
- ② 는 **CPI 전체 코히어런트 이득(45.95 dB @2 s·19.7 kHz)과 다른 것**이다. 섞지 마라.
  ④ 가 맵에서 실제로 얻는 이득이고, 이 둘의 차이가 조사 §3.1 의 «20 dB 넘게 다르다» 다. `[조사]`
- ⭐**2026-08-11 정정: «37 dB 짜리 수» 는 셋이 아니라 다섯이다.** `outputs/snr_convention.json`
  의 `do_not_confuse` 는 셋만 적는다. 원장에 실제로 도는 것은 이렇다.

  | 이름 | 값 | 어디 |
  |---|---|---|
  | ② 정합필터 이득 `10log10(B/PRF)` | **36.99 dB** | 사다리 |
  | CPI 코히어런트 적분, 5000 표본 | 36.99 dB | 이 문서 §0-2 (**우연히 같다**) |
  | CPI 코히어런트 적분, **6144 표본 Hann** | **36.12 dB** | `md_range_sweep_mf.json` 이 싣는 값 |
  | CPI 코히어런트 적분, 2 s·19.7 kHz | 45.95 dB | 부록 A |
  | ④ STFT 한 조각, 70 표본 Hann | **16.69 dB** | 맵에서 눈으로 보는 유일한 이득 |

  ⇒ **CPI 이득은 단일 수가 아니라 기록 길이의 함수다.** 그렇게 적지 않으면 이 규약이 고친 것과
    **같은 종류의 사고**가 다시 난다.
  ⚠ 그리고 지금 `g_stft_db` · `snr_map_ac_db` 라는 **같은 키 이름**이 두 원장에서 다른 값을 싣는다
    (`md_range_sweep_mf.json` nperseg 6144 → 36.12 dB · `md_snr_vs_range.json` nperseg 70 → 16.69 dB,
    **19.4 dB 차이**). meta 가 각각 설명은 하지만 키는 같다.
    ⇒ 권고: `g_frame_db`(조각) / `g_cpi_db`(전창) 으로 **이름을 갈라라**. 값 재계산은 필요 없다.

**⚠ 조건 배지 — 규약에 반드시 함께 적는다**
```
capture   : "full_waveform"  (② 를 붙임)  /  "always_on_pilot"  (② 를 붙이지 않고 PRF 를 실제 반복률로)
noise     : "thermal_only"   (kT0·F·B, F = 5 dB, T0 = 290 K)
geometry  : "monostatic_equivalent" (R_t = R_r = R)  /  "bistatic" (R_t, R_r 별도)
```
`sionna.rt` 의 기본 잡음(`rt/scene.py:172-177`)은 **kTB, T = 293 K, F 없음** 이라 우리 규약과
다르다 — 그대로 믿지 마라. `[조사]`

## 1-3. 현행 코드와의 대조 — 무엇이 얼마나 바뀌나

| 파일:줄 | 지금 쓰는 규약 | 사다리 어디 | 갈아야 하나 |
|---|---|---|---|
| `microdoppler_nearfield.py:334-350` `echo_over_noise_db` | `P_echo/(kT0F·B)` | ① | **함수는 그대로.** ② 를 붙이는 것은 새 함수가 한다 |
| `microdoppler_nearfield.py:353-362` `ac_snr_db` | ③ − dc_ac(근사) | ③→③′ | 정확식 opt-in 추가 |
| `microdoppler_nearfield.py:365-373` `add_noise` | **총전력** 기준 | ③ | `ref="ac"` opt-in 추가(기본 `"total"` = 비트동일) |
| `experiment_md_range.py:124-125` | ① 을 ③ 처럼 씀 | **결함** | ② 를 붙이도록 갈아야 한다 → 원장 재생성 |
| `md_classify_dataset.py:806-811` | **AC** 기준, 절대 링크 없음 | ③′ | `add_noise(ref="ac")` 로 대체(비트동일 확인 후) + 거리 매핑 추가 |
| `benchmark/passive_two_channel_md.py:334-378` `calibrate_sigma` | σ 를 역산해 출력 SINR 20 dB 고정 | — | **여기엔 거리가 아예 없다.** 링크버짓 팔을 하나 더 다는 것이 남은 일 |
| `benchmark/link_budget.py:69-89` `link_terms` | `snr_echo_db` = ① | ① | ⭐**이미 있다. 재구현 금지** — 새 함수가 이걸 부른다 |

## 1-4. ⭐거리 → SNR — 식과 재사용할 원장

```
P_echo(R_t, R_r) = EIRP · G_rx · λ² · σ / ( (4π)³ · R_t² · R_r² )        [W]
P_n              = k · T0 · F · B_eff                                     [W]
   B_eff = B        (capture = "always_on_pilot", ② 없음)
   B_eff = PRF      (capture = "full_waveform",   ② 를 이미 흡수한 형태)
```

**전부 이미 우리 원장·상수에 있다. 새로 만들지 마라.**

| 필요한 것 | 어디서 | 값 |
|---|---|---|
| σ (**방위평균**, 36 방위) | `outputs/md_range_sweep.json` → `cells[].rows[].sigma_eq_aspect_mean_plane_dbsm` | matrice4e **−18.88 dBsm** · mavic4pro −15.93 · mini5pro −20.00 · s1000plus −15.90 · phantom4 −16.92 (3.5 GHz). ⚠**단일자세 `sigma_eq_plane_dbsm` 을 쓰지 마라** — 그 파일 자신이 «비인용» 이라 선언한다 |
| dc_ac (기체별) | 같은 파일 `rows[].arms.A0_reference.dc_ac_db` | matrice4e **17.3** · s1000plus 18.9 · mini5pro 26.5 · phantom4 32.5 · mavic4pro **37.2 dB** |
| EIRP·G·F·B | `microdoppler_nearfield.py:327-331` (챔버 12 dBm) / `benchmark/link_budget.py:46-50` (매크로 63 dBm) | 12 또는 63 dBm · 10 dBi · 5 dB · 100 MHz |
| 바이스태틱 기하 | `benchmark/geometry.py` TX/RX/CENTER → `bistatic_scene.bistatic_params` | R1·R2·L·β |
| DTR | `benchmark/passive_two_channel_md.py:108-124` `scene_numbers()` | `4π R1²R2²/(L²σ)` |
| 처리이득 | 이 문서 §1-2 ②④ | `10log10(B/PRF)`, `10log10(N_seg)−1.76` |

**⚠ 어느 다리가 변하나를 반드시 명시한다** `[조사]`:
- 양쪽 다 변함(모노스태틱 등가, 우리 맵 원장이 이것): 40 m vs 3 m = **40log10(40/3) = 45.0 dB**
- Tx 다리 고정(바이스태틱, 수신국만 이동): **20log10(40/3) = 22.5 dB**

**계산 결과 (matrice4e·σ = −18.88 dBsm·PRF 19,700·N_seg 70·dc_ac 17.3 dB·모노 등가)** `[신규]`

| R [m] | ① snr_band | ③ snr_slow | ③′ snr_slow_ac | ⑤ snr_map_ac |
|---|---|---|---|---|
| 3 | +18.69 | +55.74 | +38.36 | +55.06 |
| 10 | −2.23 | +34.83 | +17.45 | +34.14 |
| 15 | −9.27 | +27.79 | +10.41 | +27.10 |
| 20 | −14.27 | +22.79 | +5.41 | +22.10 |
| **40** | −26.31 | +10.75 | **−6.63** | +10.06 |
| 60 | −33.35 | +3.70 | −13.68 | +3.01 |
| 100 | −42.23 | −5.17 | −22.55 | −5.86 |

(`snr_band(R=1 m) = +37.77 dB`. 사다리 전부가 이 한 수에서 `−40log10(R)` 로 내려간다.)

**⭐그리고 이것이 «분류 정확도 대 거리»를 준다.** `outputs/md_classify.json` 의 잡음 팔이
**정확히 ③′ 축** 이므로(§0-1), 거리로 바로 옮겨진다:

| ③′ AC SNR | 분류 정확도(RF100) | R (EIRP 12 dBm, 챔버) | R (EIRP 63 dBm, 매크로 gNB) |
|---|---|---|---|
| +10 dB | 0.879 | **15.4 m** | **289 m** |
| 0 dB | 0.840 | **27.3 m** | **514 m** |
| −10 dB | 0.434 | **48.6 m** | **915 m** |
| −15 dB | 0.286 | 64.7 m | 1,220 m |
| −20 dB | 0.242 (≈우연 0.167) | 86.3 m | 1,626 m |

이 표 한 장이 «멀면 어려워진다» 를 **수로** 말한다. 8/18 덱의 헤드라인 후보다.
⚠ 전제: 풀 캡처 · 열잡음만 · 모노스태틱 등가 · σ 는 방위평균 · matrice4e 의 dc_ac.
기체마다 dc_ac 가 17.3~37.2 dB 로 달라 **기체별로 따로 내야 한다.**

## 1-5. API 설계 — 파일·함수·인자

### (a) `src/microdoppler_nearfield.py` 에 추가 (기존 함수는 **안 건드린다**)

```python
SNR_CONVENTION = "v2_2026-08"   # 원장 meta 에 그대로 박는 문자열

def snr_ladder(sigma_eq_m2, range_m, fc, *,
               rx_range_m=None,          # None 이면 모노스태틱 등가
               prf=20000.0,              # 슬로타임 표본율
               nperseg=None,             # STFT 조각 표본 수. None 이면 ④를 안 낸다
               window="hann",            # 창 손실표 조회 키
               dc_ac_db=None,            # 주면 ③′·⑤ 를 낸다
               capture="full_waveform",  # or "always_on_pilot"
               eirp_dbm=DECLARED_EIRP_DBM, rx_gain_dbi=DECLARED_RX_GAIN_DBI,
               nf_db=DECLARED_NF_DB, b_hz=DECLARED_B_HZ,
               exact_ac=True) -> dict:
    """§1-2 의 사다리 전부를 dict 로. 키 이름은 §1-7 의 원장 키와 **글자 그대로 같다**."""
```
- 반환 키: `snr_band_db, g_mf_db, snr_slow_db, dc_ac_off_db, snr_slow_ac_db, g_stft_db,
  snr_map_ac_db, p_echo_w, p_noise_w, b_eff_hz, capture, convention`
- ① 은 **기존 `echo_over_noise_db()` 를 호출해서** 얻는다(재구현 금지 규약).
- `capture="always_on_pilot"` 이면 `g_mf_db = 0.0` 이고 `b_eff_hz = b_hz`.
- 창 손실표 `WINDOW_COH_LOSS_DB = {"hann": -1.76, "hamming": -1.35, "boxcar": 0.0, ...}`
  — 값의 근거는 Braun 식 (3.77) `[조사]`. 표에 없는 창은 배열에서 직접 계산한다.

```python
def ac_snr_db(E, snr_total_db, *, exact=False):    # exact=True 면 10log10(1+10^(dc_ac/10))
def add_noise(E, snr_db, rng, *, ref="total"):     # ref="ac" 면 p_sig = mean|E-mean(E)|²
```
⚠ **기본값은 둘 다 현행 그대로다.** 기존 원장이 안 깨진다.

```python
def noisy_series(E, snr_slow_ac_db, rng, n_real=1):
    """③′ 를 받아 잡음 실현 n_real 개를 만든다. 맵·지표가 공통으로 쓰는 입구."""
```

### (b) `src/md_mapstyle.py` — 절대 눈금 지원

```python
draw(ax, t, f, S, f_tip, *, t_scale=1e3, ref=None,
     mode="peak",          # ⭐기본값 = 지금 동작(맵 최대값 정규화). 비트동일
     noise_rms=None)       # mode="over_noise" 일 때 STFT 잡음 바닥의 rms 크기
```
- `mode="peak"` — 현행. `20log10(S/ref)`, `VMIN/VMAX = −40/0`.
- `mode="over_noise"` — `20log10(S/noise_rms)`, 눈금 `NOISE_VMIN, NOISE_VMAX = -6, +40` dB.
  0 점이 **추정 잡음 바닥**이다. 패시브 레이더 관례(Remote Sens. 14:6146 *"24 dB above noise"*) `[조사]`
- `mode="abs_dbm"` — `10log10(P/1mW)`. Braun Fig. 3.5 관례 `[조사]`. 절대 전력을 알 때만.
- ⭐**`ref`·`noise_rms` 는 한 그림의 모든 패널에 같은 값을 넣는다.** §3-3 에 게이트를 건다.
- `caption()` 에 사다리 세 수를 문자열로 붙이는 `caption_snr(ladder)` 를 추가한다
  (그림 안이 아니라 **캡션·본문**에 — 그림 안 세팅 블록 금지 규약).

### (c) 호출부 배선 (전부 opt-in, 기본 동작 불변)

| 파일 | 지금 | 넣을 것 |
|---|---|---|
| `benchmark/build_deck0811_range_figs.py:88-91` `_map()` | 무잡음 E → `flash_spec` | `noisy_series()` 를 통과시키고 `draw(mode="over_noise", noise_rms=...)` |
| `benchmark/build_report07_figs.py:135-139` | `ref = max(...)` 공통 기준(**이건 잘 하고 있다**) | 유지 + 사다리 라벨 |
| `src/experiment_md_range.py:124-125` | ① 을 ③ 으로 오용 | `snr_ladder()` 로 교체 → **원장 재생성** |
| `benchmark/md_classify_dataset.py:806-811` | 인라인 AC 잡음 | `add_noise(..., ref="ac")` + `snr_convention` meta |

## 1-6. 그림에서 «멀면 어려워진다» 를 보이는 법 — 셋 다 쓴다

조사가 네 관례를 정리했다(`noise_modeling_survey.md` §4). 우리는 **(b)+(d)+(c)** 를 쓴다.

1. **맵**(`build_deck0811_range_figs.py` 3×2 판) — **(b) 잡음 위 dB**.
   컬러바 `dB above noise`, **세 거리 패널이 같은 눈금**. 지금은 `_map()` 이 `draw(...)` 를
   `ref=None` 으로 불러 **패널마다 자기 최대값으로 정규화**한다 — 그래서 40 m 가 3 m 보다
   45 dB 약하다는 사실이 그림에서 사라진다. 이 한 줄이 문제의 핵심이다.
   ⚠ 절대 dBm 눈금(a)은 EIRP 가 `[선언]` 값이라 «절대» 라는 말이 과하다. **잡음 위 dB 를 쓴다.**
2. **곡선**(새 그림) — **(d) 성능 대 거리**. 두 장:
   - `fd_edge` 관측성 vs 거리 (NaN 반환률 = «묻혔다»). Braun 의 threshold effect 대응물 `[조사]`
   - **분류 정확도 vs 거리** (§1-4 표). EIRP 두 팔(12 / 63 dBm)을 겹쳐 그린다.
     우연선 16.7 % 를 점선으로(arXiv:2402.04368 Fig. 5(b) 관례) `[조사]`
3. **한 장의 연속 스펙트로그램에 구간 라벨** — **(c)**. arXiv:2402.04368 Fig. 4(b) 가
   «(II) 검출은 되는데 마이크로도플러는 안 보임 / (III) 둘 다 보임» 을 한 장에 표시한다 `[조사]`.
   우리 사다리로 그 구간 경계가 **계산된다**: ③ > 0 dB 인데 ③′ < 0 dB 인 구간이 정확히 (II) 다.
   matrice4e·EIRP 12 dBm 에서 그 구간은 **R = 27.3 ~ 74.3 m** (폭 **17.4 dB** = `dc_ac_off_db`). `[신규]`
   → 선행연구와 나란히 놓을 수 있는 그림이다(상시규칙 `sionna2-priorwork-methodology`).

## 1-7. 원장 설계 — 파일과 키

### `outputs/snr_convention.json` (새로, 작다·불변)
```json
{"_meta": {"convention": "v2_2026-08", "doc": "docs/NOISE_AND_ROTOR_PLAN.md#1-2"},
 "rungs": [{"id":"snr_band_db","def":"P_echo/(k T0 F B)","ref":"pre-matched-filter, per Rx sample"},
           {"id":"g_mf_db","def":"10log10(B/PRF)","condition":"capture=full_waveform"},
           {"id":"snr_slow_db"}, {"id":"snr_slow_ac_db","canonical":true},
           {"id":"g_stft_db","def":"10log10(N_seg)+L_win"}, {"id":"snr_map_ac_db"}],
 "constants": {"T0_K":290.0,"nf_db":5.0,"b_hz":1.0e8,"window_coh_loss_db":{"hann":-1.76}},
 "verification": {"mf_gain_measured_db": 6.86, "mf_gain_predicted_db": 6.99,
                  "test": "L=5000 white ref, per-sample SNR -30 dB"}}
```

### `outputs/md_snr_vs_range.json` (새로) — §1-4 표의 원장
`cells[]`: `drone, band, fc_hz, capture, eirp_dbm, sigma_dbsm_source, dc_ac_db`
`rows[]`: `R_m, R_t_m, R_r_m, snr_band_db, g_mf_db, snr_slow_db, snr_slow_ac_db,
g_stft_db, snr_map_ac_db, fd_edge_hz, fd_edge_n_valid, pd_est`

### `outputs/md_classify_vs_range.json` (새로) — 정확도 대 거리
`snr_slow_ac_db → accuracy` 를 `outputs/md_classify.json` 에서 읽고, `R` 을 붙인다.
**정확도 수치를 다시 계산하지 않는다**(원장 재사용). 붙이는 것은 `R` 뿐이다.

### 기존 원장 갱신
- `outputs/md_range_sweep.json` — ⚠⚠**이미 두 겹으로 낡았다** (오늘 실측으로 확인) `[신규]`:
  ① 현행 `experiment_md_range.py:139-140` 이 `snr_ac_plane_db`/`snr_ac_sph_db` 를 쓰는데
     원장에는 그 키가 **0 개**다(생성 2026-07-28T06:13).
  ② 원장의 `snr_sample_plane_db`(R=1 m 에서 36.673)는 **단일자세 σ**(`sigma_eq_plane_dbsm`
     = −19.981)로 계산된 값이다. 현행 코드(`:124`)는 **방위평균 σ**(−18.879)를 쓰므로
     같은 입력에서 **37.775** 가 나온다 — **1.10 dB 차이**. 즉 원장은 코드가 «비인용» 이라고
     선언한 단일자세 σ 로 만들어져 있다(코드 `:119-123` 의 정정 주석보다 앞선 실행).
  ⇒ 사다리 도입과 함께 **반드시 재생성**한다(CPU, §4 #6). 그 전까지 이 원장의 SNR 열을 인용 금지.
- `outputs/md_classify.json` `_meta` 에 `"snr_convention": "v2_2026-08",
  "snr_reference": "ac", "capture": "full_waveform"` 를 박는다.

## 1-8. ⚠이 설계가 **하지 않는** 것 (정직성)

- **클러터·DPI·ECA 노치를 안 넣는다.** 마이크로도플러 맵 팔은 «열잡음만» 이다.
  진짜 사슬은 `benchmark/passive_two_channel_md.py` 에 있고, 거기서는 σ 를 역산해 출력 SINR 을
  20 dB 로 고정한다 — **거리가 아예 없다**. 두 팔을 잇는 것이 다음 라운드 과제다.
- **ECA 0-도플러 노치가 호버링 동체선(DC)을 지운다.** 그러면 `dc_ac_off_db` 가 0 이 되어
  ③ = ③′ 가 된다. 즉 **패시브 실사슬에서는 AC 보정이 필요 없을 수 있다.** 이건 열린 문제이고,
  §3-3 의 게이트 하나가 그걸 잰다.
- **위상잡음·양자화·안테나 패턴을 안 넣는다.** arXiv:2604.12567 이 위상잡음 1~10° 를 함께
  스윕한다 `[조사]` — 나중 축이다.
- **`g_mf_db` 는 이상적 정합필터·완벽한 기준신호를 전제한다.** 기준채널이 더러우면
  그만큼 깎인다(`passive_two_channel_md.py` 가 잰 절벽: 기준채널 SNR 30↔20 dB).
- **`g_stft_db` 를 «STFT 한 조각의 처리이득 = 10log10(창길이)» 로 쓰는 1차 문헌을 못 찾았다.**
  Braun 식 (3.37) 은 2D 페리오도그램(NM)에 대한 것이고 STFT 조각에 옮기는 것은 **우리 유추**다
  (`noise_modeling_survey.md` §6-2). 원장 meta 에 그렇게 적는다.

---

# 2. 로터 랜덤성 설계

## 2-1. 결론 — 무엇으로 바꾸나

```
현재 (benchmark/report07_hover_long.py:113-120)
    stat  = STATIC_SPREAD * PATTERN[k]                      # 결정론적 패턴 ±0.22 %
    phi0  = 2π k / n                                        # 흔들림의 «위상», 결정론적
    rpm_t = rpm0 * (1 + stat + WOBBLE_AMP·sin(2π·2.7·t + phi0))   # 정현파 한 톤 ±0.15 %
    ang   = cumsum(360·rpm_t/60 · dt)                       # ✅ 이건 옳다 — 유지

바꾼 뒤
    s_k   ~ N(0, σ_s),  Σs_k = 0                            # 정적 산포: 난수 + 평균 보존
    ε_k(t) : OU(σ_w, T),  로터마다 독립                      # 흔들림: 저역통과 잡음
    θ_k(0) ~ U(0, 360/blades)                               # ⭐t=0 회전위상 무작위화
    rpm_k(t) = rpm0 · (1 + s_k + ε_k(t))
    ang   = θ_k(0) + cumsum(360·rpm_k/60 · dt)              # 그대로
```

**세 가지 판단과 근거**

1. **백색 가우시안으로는 안 된다. 저역통과(1극 OU)가 필요하다.** `[조사]`
   근거 세 겹(`rotor_randomness_survey.md` §3): 자세각 루프 교차 **0.64 Hz**(PX4 `MC_ROLL_P=4.0`)
   / **0.72 Hz**(ArduPilot `ATC_ANG_*_P=4.5`) · 자이로 저역통과 20~40 Hz · 로터 1차 시상수
   τ = 5~72 ms(코너 2.2~32 Hz). 백색이면 PRF 19.7 kHz 까지 평평한 흔들림을 넣게 되는데
   그건 물리에 없다. 게다가 백색 rpm 잡음을 적분하면 위상이 **랜덤워크**가 되어 선폭이
   무한히 넓어진다 — 명백히 틀린 모양이다. `[신규]`
2. **정현파 한 톤도 틀린 모양이다.** `[조사]` 랜덤과정은 선을 **넓히고**, 정현파는 ±f_m 간격
   **빗살로 가른다**. Physics of Fluids 33:127107 (2021) 이 음향 쪽에서 같은 말을 한다 —
   *"a **random process** was applied to reflect the RPM fluctuation effects … the **collapse of
   the phase effect** due to the RPM fluctuation of each rotor"*.
   ⇒ 우리 그림의 «가늘고 선명한 빗살» 은 **값이 작아서** 생긴 것이다.
3. **초기 위상은 무작위화한다.** `[조사]` Costa (arXiv:2504.05168) *"propellers usually have
   **random initial azimuth angles (φ₀ₚ = 𝒰(0, 2π))**"*, Cai (RADAR 2019) *"random angle shift"*.
   우리 내부 기록(`docs/PRIOR_WORK_JIHYUCK.md:378-382`)도 이미 같은 권고를 했다.
   ⭐**분류 팔은 이미 하고 있다** — `md_classify_dataset.py:624` `rng.uniform(0, 180, n_rotors)`.
   **안 하고 있는 곳은 `report07_hover_long.py` 뿐이다.**

**2극(로터 관성)은 옵션으로만 둔다.** `[조사]` 8~20 dB 짜리 세부이고
(`rotor_randomness_survey.md` §3-3 감쇠표), τ_motor 는 우리 표적 기체 값을 **못 찾았다**.

## 2-2. 파라미터 — 몇 개로, 어떤 값으로

**네 개다.** (정적 산포 σ_s · 흔들림 σ_w · 시상수 T · 선택적 로터 시상수 τ_m)

### σ_w 보정 산술 — 원장 값을 그대로 못 쓴다 `[신규]`

`outputs/rotor_rpm_web_anchor.json` 의 `wobble_*_amp_pct` 는 **«등가 사인 진폭»** 이다
(method_note: *"대역 성분 rms × √2"*). OU 의 파라미터는 진폭이 아니라 **σ** 이므로 두 번 고친다:

```
rms_band = amp_equiv_sine / √2
σ_w      = rms_band / √(F(T, f1, f2)),   F = (2/π)[arctan(2πf₂T) − arctan(2πf₁T)]
```
(F 는 OU 의 총분산 중 측정대역 [f1,f2] 에 든 몫. OU PSD `S(f)=4σ²T/(1+(2πfT)²)` 적분.)

| 원천 | 측정대역 | 원장 amp | F(T=0.2274) | **σ_w** |
|---|---|---|---|---|
| NeuroBEM (실내·무풍) | 0.3–5 Hz | 0.74 % | 0.654 | **0.65 %** |
| CODEV AQUILA V3 (야외) | 0.3–2 Hz | 2.52 % | 0.528 | **2.45 %** |
| DJI P3 DAT (명령 PWM) | 0.3–5 Hz | 5.3 % | 0.654 | 4.64 % → rpm 환산 **2.3~4.6 %** |

⚠ 이 값들은 `rotor_randomness_survey.md` §6 의 권고(실내 0.8 % / 야외 2.5 %)와 **조금 다르다**.
그 권고는 «사인 진폭» 그대로였고, 여기서는 **대역 몫 보정**을 넣었다. 둘 다 원장에 적는다.

### 프리셋 (`src/rotor_dynamics.py` 의 `PRESETS`)

| 이름 | σ_s (정적) | σ_w (흔들림) | T | 초기위상 | 근거 |
|---|---|---|---|---|---|
| **`legacy`** (⭐기본값) | 0.0022 · PATTERN | 0.0015 sine @2.7 Hz | — | 정렬(0) | **현행 그대로. 비트동일 보장** |
| `sitl` | 0.0022 (난수) | 0.0 | — | U | PX4 SITL 실측 0.07~0.29 % — 대칭·이상 하한 |
| `indoor` | **0.0054** | **0.0065** | 0.2274 s | U | NeuroBEM 중앙(정적 0.54 %) + 보정 σ_w |
| `outdoor` | **0.0235** | **0.0245** | 0.2274 s | U | CODEV 중앙(정적 2.35 %) + 보정 σ_w. ⭐실증이 야외이므로 **헤드라인 후보** |

- `T = 1/(2π·0.7 Hz) = 0.2274 s` — 자세각 루프 교차. PX4 4.0 1/s → 0.64 Hz,
  ArduPilot 4.5 1/s → 0.72 Hz 의 중간 `[조사]`. **레짐에 무관하게 같은 값**(제어기가 정한다).
- `τ_m` (2극, 기본 `None`=끔): 켜면 0.0125~0.025 s(RotorS/PX4 기본값) `[조사]`.
- **`WOBBLE_HZ` 는 폐기한다** — OU 에는 «주파수» 파라미터가 없다. 서술도 «2.7 Hz 로 흔든다» →
  «자세 루프 대역(≈0.7 Hz)까지의 붉은 잡음» 으로 바꾼다.

### ⚠ 정적 산포는 «패턴» 이 아니라 «난수» 로

지금 `PATTERN = [+1,-1,-0.55,+0.55]`(`report07_hover_long.py:76`)는 **결정론적**이라 시행을
아무리 반복해도 같은 배치가 나온다. `md_classify_dataset.py:622-623` 방식(`N(0,σ)` 뽑고 평균
제거)으로 통일한다. `legacy` 프리셋만 PATTERN 을 유지한다.

## 2-3. API — 새 모듈 `src/rotor_dynamics.py`

```python
"""로터 회전 랜덤성 한 자리. report07_hover_long · md_classify_dataset · microdoppler 가
   같은 구현을 쓴다(재구현 금지 규약)."""

@dataclass(frozen=True)
class RotorJitter:
    static_sigma: float          # σ_s, 상대
    wobble_sigma: float          # σ_w, 상대 (0 이면 흔들림 없음)
    tau_ctl_s:    float = 0.2274 # OU 시상수
    tau_motor_s:  float | None = None   # 2극(옵션)
    random_phase: bool = True
    legacy_sine:  tuple | None = None   # (amp, hz) — legacy 프리셋 전용
    static_pattern: tuple | None = None # legacy 전용
    source: str = ""             # 원장에 그대로 실을 근거 문자열

PRESETS: dict[str, RotorJitter]   # 위 표

def rpm_series(rpm0, n_rotors, n_t, dt, jitter, rng, *, coarse_hz=200.0):
    """반환 (n_t, n_rotors) rpm [rpm], 그리고 진단 dict.
       coarse_hz: OU 를 이 표본율로 만들고 3차 스플라인으로 올린다(대역폭 200 Hz ≫ 13 Hz
       두 번째 극이라 손실 없음). n_t 가 커도 난수 뽑기가 4,000 배 싸다."""

def phases(t_or_dt, rpm_t, dirs, rng, jitter, *, period_deg=360.0):
    """θ_k(t) = θ_k(0) + dir_k · cumsum(360·rpm_k/60 · dt) [deg], (n_t, n_rotors).
       θ_k(0) ~ U(0, period_deg/blades) if jitter.random_phase."""

def summary(rpm_t, dt, jitter) -> dict:
    """검증·원장용 진단: 실측 σ_s · σ_w · 대역별 rms · PSD 기울기 · 지배 주파수."""
```

**OU 이산화(정확 이산화, 근사 아님)**
```
a = exp(-dt/T);   ε[n+1] = a·ε[n] + σ_w·sqrt(1 - a²)·N(0,1)
```
2극이면 같은 식을 τ_motor 로 한 번 더 통과시키고 σ 를 다시 정규화한다.
⚠ 정상상태에서 시작해야 한다 — `ε[0] ~ N(0, σ_w)`. 0 에서 시작하면 앞 1 초가 «워밍업» 이 된다.

## 2-4. 호출부 배선 — 세 곳, 전부 opt-in

| 파일:줄 | 지금 | 넣을 것 | 비용 |
|---|---|---|---|
| `benchmark/report07_hover_long.py:70-76, 112-120` | `PRESETS` 3-튜플 + 정현파 | `rotor_dynamics.PRESETS` 로 교체, `--preset legacy` 가 **기본**. `ang` 계산은 이미 cumsum 이라 **그대로** | **0** (SBR 호출 수 불변) |
| `benchmark/md_classify_dataset.py:405-419 `synth()`, `618-624 _draw_trials()` | 선형 위상 `p0 + dir·360·rpm/60·t` | `rotor_dynamics.phases()` 로 교체 — **위상표 조회는 그대로 동작한다**(표는 각도의 함수일 뿐) | **거의 0** — cumsum + 성근 OU. ⭐**SBR 재계산 불필요** |
| `src/articulated_fast.py:171-186 `rotor_phases()`` | 상수 rpm 만 | `rpm_per_rotor` 가 2차원(n_t, n_rotors)이면 cumsum 경로를 타도록 확장(1차원이면 현행과 **비트동일**) | 0 |

⭐ **가장 중요한 설계 판단**: `md_classify_dataset` 의 **위상표 분해가 흔들림과 호환된다.**
표는 `ΔE_k(φ_k)` — **각도의 함수**다. rpm 이 시간에 따라 변해도 «어떤 각도인가» 만 바뀌므로
표를 다시 만들 필요가 **없다**. 즉 **로터 랜덤성 개선에 GPU 가 한 톨도 안 든다.**

## 2-5. 파급 예측 — 반증 가능한 형태로 `[신규]`

matrice4e (f_flash 126.67 Hz · f_tip 1,228.7 Hz):

| σ_w | f_tip 순시편이 | 10차 조화 편이 | Carson 대역 @10차 |
|---|---|---|---|
| 현행 정현파 0.15 % (σ 0.106 %) | ±1.30 Hz | ±1.34 Hz | 4.1 Hz |
| `indoor` 0.65 % | ±7.99 Hz | ±8.23 Hz | 17.9 Hz |
| `outdoor` 2.45 % | ±30.1 Hz | ±31.0 Hz | 63.4 Hz |

**이 셋을 어디서 볼 수 있고 어디서 못 보나** — 계측기 분해능과 나란히 놓아야 정직하다:

| 계측기 | Δf | `outdoor` 63 Hz 를 보나 |
|---|---|---|
| 2 s CPI 호버 맵(`ridge_spec`) | 0.5 Hz | ✅ **127 빈** — 능선이 뱀처럼 굵어진다 |
| 분류 특징 전창 FFT (T = 0.25 s) | 4.0 Hz | ✅ 16 빈 |
| 분류 빗살 창 `half = 0.20·f_flash` (`md_classify_dataset.py:544`) | ±25.3 Hz | ⚠**넘친다** — 고조파 에너지가 빗살 밖으로 샌다 → `h1..h12` 특징이 깎인다 |
| `flash_spec` 맵 (N_seg 70) | 281 Hz | ❌ **안 보인다** — 시간분해능 우선의 대가 |

**⇒ 예측(=검증 게이트)**: `outdoor` 를 켜면
① 2 s 호버 맵의 고차 능선이 눈에 띄게 굵어진다,
② 분류 정확도가 **떨어진다**(빗살 누설 + 접은 프로파일 흐림),
③ 특징 `half_corr`(반창 스펙트럼 상관, 비정상성 지표)가 **내려간다**,
④ `flash_spec` 플래시 맵은 **거의 안 변한다**.
넷 중 하나라도 안 나오면 **배선이 안 된 것**이다(§3-4).

⚠ 그리고 §0-3 — **0.25 s 창에서는 흔들림의 71.6 % 가 정적 오프셋으로 보인다.**
그러므로 ②③ 은 **T = 1.0 s 팔에서 더 크게** 나와야 한다. 이것도 게이트다.

## 2-6. ⚠못 하는 것 / 안 하는 것

- **블레이드 플렉싱·피치 변화는 안 넣는다.** 원문 확인 범위에서 사례 **0 건**
  (`rotor_randomness_survey.md` §2-4). Moore IET RSN 2024 는 전문을 **못 읽었다**.
- **산란 진폭의 요동은 여전히 미모델**이다. White TRS 2024 자신이 자백한다 —
  *"sidebands fluctuated … The simulation model presented in this paper **does not attempt to
  model such fluctuations**"* `[조사]`. 우리도 못 한다. 리포트에 그렇게 적는다.
- **σ_w 의 «시간 흔들림» 을 넣은 마이크로도플러 문헌 선례가 없다** — arXiv:2506.00497 조차
  로터별 각속도를 시간에 대해 상수로 둔다 `[조사]`. 근거는 **실기 로그뿐**이다
  (`outputs/rotor_rpm_web_anchor.json`). 리포트에서 «문헌이 한다» 라고 쓰면 안 된다.
- **우리 표적 기체(Mavic 4 Pro · Matrice 4E)의 로터 τ 와 rpm 통계는 못 찾았다.** DJI 가 최신
  DAT 를 암호화한다. **자체 실측이 유일한 경로다** — 실측 계획(`docs/MEASUREMENT_PLAN.md`)에 건다.

---

# 3. 검증 계획 — «제대로 들어갔다» 를 무엇으로 아나

전부 **스크립트 하나로 자동**이어야 한다: `benchmark/verify_noise_rotor.py`,
원장 `outputs/verify_noise_rotor.json`, 모든 게이트가 `pass/fail` + 측정값.

## 3-1. 회귀 게이트 — 기존 원장이 안 깨졌나 (**가장 먼저**)

| G | 무엇 | 합격선 |
|---|---|---|
| G1 | `add_noise(ref="total")` 기본 경로 | 같은 seed 에서 **비트동일** |
| G2 | `ac_snr_db(exact=False)` | **비트동일** |
| G3 | `md_mapstyle.draw(mode="peak")` | 같은 입력 → 픽셀 **비트동일** |
| G4 | `rotor_dynamics` `legacy` 프리셋 | `outputs/report07_hover_long.npz` 의 `rpm_t` 와 **max abs diff ≤ 1e-12** |
| G5 | `articulated_fast.rotor_phases()` 1차원 경로 | **비트동일** |
| G6 | `md_classify_dataset` 를 `add_noise(ref="ac")` 로 갈아끼운 뒤 | 같은 seed 에서 특징행렬 `X` **max rel diff ≤ 1e-12** (RNG 소모 순서가 같은지가 관건) |

## 3-2. 잡음 통계 게이트 — 넣은 잡음이 진짜 그 잡음인가

| G | 무엇 | 합격선 |
|---|---|---|
| G7 | 순수 잡음(E=0)의 스펙트로그램 빈 분포 | 지수분포(χ²₂) KS 검정 p > 0.01. Braun 식 3.92 `[조사]` |
| G8 | 평활 안 한 주기도의 max/median | **11.0 ~ 11.4 dB**(`md_metrics` docstring 의 기존 실측값 재현) |
| G9 | W=33 평활 뒤 max/median | **≈2 dB**(같은 docstring) |
| G10 | 실현 간 `snr_map_ac_db` 표준편차 | 예측 ±(적분 자유도) 안 |

## 3-3. 물리 게이트 — 사다리가 맞나

| G | 무엇 | 합격선 |
|---|---|---|
| G11 | 정합필터 이득 | 측정 vs `10log10(B/PRF)` **≤ 0.3 dB** ✅**통과**(`verify_matched_filter_gain.py` MF1 +0.026 · MF2 −0.019 · MF3 끝에서 끝까지 +0.105 dB) |
| G11b | ⭐**독립 구현 대조**(2026-08-11 신설) | 사다리 ③ vs `freespace_link.snr_rd_db(T=1/PRF)` ✅**통과, max 1.4e-14 dB**. report12·13 이 원래 쓰던 팔과 같은 수라는 것이 이 정정의 결정적 확증이다 |
| G12 | ⭐**교차검증**: `passive_two_channel_md.py` 의 실사슬(ECA→CAF→CFAR) `sinr_ideal_db` vs 사다리 예측 | **≤ 1 dB**. 안 맞으면 사다리가 틀렸거나 사슬에 추가 손실이 있다 — 어느 쪽인지 밝힐 것. ⚠**아직 안 했다. 이것이 «37 dB 를 실제로 번다» 의 유일한 관문이다** |
| G13 | `snr_slow_ac_db` vs R 기울기 | 모노 등가에서 **−40.0 dB/decade ± 0.1** ✅**통과**(SC6, 측정 −40.000 / 바이스태틱 한 다리 −20.000) |
| G14 | `fd_edge` 가 NaN 이 되는 거리 | ⛔**판정 불가 — 정의부터 못 박아라.** 2026-08-11 실측: matrice4e **R90 22.1 m** · R50 31.4 · R(첨두 10 dB) **30.4 m**. 이 문서의 옛 예측 35~42 m 는 R90 기준 **8.0 dB 초과(불합격)**, R(첨두 10 dB) 기준 2.4 dB(합격). 예측은 ⑤(nperseg 70)로, 측정은 `md_metrics`(nperseg 256·평활)로 했다 — **사슬이 다르다** |
| G15 | 컬러바 공통성 | 한 그림 안 모든 패널의 `ref`/`noise_rms`/`vmin`/`vmax` 가 **동일** (assert) |
| G16 | ⚠**ECA 노치가 DC 를 지우면 `dc_ac_off_db` → 0** | `passive_two_channel_md` 산출에서 실측. 0 이면 §1-8 대로 AC 보정이 불필요해진다 — **결과를 그대로 기록**(어느 쪽이든 발견이다) |

## 3-4. 로터 게이트 — 흔들림이 진짜 들어갔나

| G | 무엇 | 합격선 |
|---|---|---|
| G17 | OU 정상상태 std | 긴 실행(≥ 100 T)에서 `std(ε)` = σ_w **± 5 %** |
| G18 | lag-1 자기상관 | `exp(-dt/T)` **± 1e-4** |
| G19 | PSD 기울기 | 1/(2πT) 위에서 **−20 dB/decade ± 2** |
| G20 | ⭐**대역 rms 역보정** | 생성된 ε 의 0.3–5 Hz 대역 rms 가 원장 앵커(`amp/√2`)를 **± 10 %** 로 되돌려주나 |
| G21 | 위상 무결성 | `diff(θ)/dt · 60/360` 이 `rpm_t` 와 **rel err ≤ 1e-12** (적분이 맞나) |
| G22 | 초기위상 분포 | 1,000 회 추첨의 KS 검정 vs U(0, 360/blades), p > 0.01 |
| G23 | **선폭 예측** | 2 s CPI 에서 m 차 조화의 −3 dB 폭이 `2·m·f_flash·σ_w` 에 **비례**(상관 ≥ 0.95) |
| G24 | **반증 게이트 ②③④** | §2-5 의 넷이 예측 방향대로 움직이나. **④(플래시 맵 불변)가 깨지면 조각 길이 규약과 충돌**한 것이므로 멈추고 조사 |
| G25 | **창 길이 의존성** | T = 1.0 s 팔의 정확도 하락 폭 > T = 0.25 s 팔 (§0-3 의 예측) |

## 3-5. 게이트가 실패했을 때의 행동 규칙

- G1~G6 실패 → **즉시 되돌린다.** opt-in 설계가 깨진 것이다.
- G11~G14 실패 → 사다리를 고친다. **원장을 고치지 말고 사다리를 고친다.**
- G24 실패 → 배선이 안 된 것. 잡음/흔들림이 실제로 신호에 닿는지 추적한다.
- G16 은 **합격/불합격이 아니라 측정**이다. 어느 쪽이 나오든 리포트에 적는다.

---

# 4. 순서와 비용 — 8/18 까지

오늘 8/10. 남은 8 일. **상류부터**(`upstream-first-ordering`). ⛔ 현재 GPU 점유 중이므로
GPU 단계는 **표시해 두고 뒤로 민다**.

| # | 층 | 할 일 | GPU | 예상 |
|---|---|---|---|---|
| **1** | 규약 | `outputs/snr_convention.json` + `microdoppler_nearfield.snr_ladder()` + 창 손실표 | ❌ | **2 h** |
| **2** | 규약 | `ac_snr_db(exact=)` · `add_noise(ref=)` · `noisy_series()` opt-in. **G1·G2 게이트** | ❌ | **1 h** |
| **3** | 커널 | `src/rotor_dynamics.py` 신설 (OU·프리셋·`summary()`). **G17~G22 게이트** | ❌ | **3 h** |
| **4** | 커널 | `articulated_fast.rotor_phases()` 2차원 확장 + `report07_hover_long` 배선(기본 `legacy`). **G4·G5** | ❌ | **1.5 h** |
| **5** | 검증 | `benchmark/verify_noise_rotor.py` — G1~G14 · G17~G23 자동화 | ❌ | **3 h** |
| **6** | 재계산 | `experiment_md_range.py` 사다리 반영 → `md_range_sweep.json` 재생성 (⚠지금 원장은 낡았다) | ❌ CPU 10 workers | **40 min** |
| **7** | 재계산 | `outputs/md_snr_vs_range.json` + `md_classify_vs_range.json` 생성 | ❌ | **1 h** |
| **8** | 재계산 | `md_classify_dataset.py build` — 로터 프리셋 `outdoor` + AC 잡음 규약. ⭐**위상표 재사용, GPU 불필요** | ❌ CPU | **1.5 h** |
| **9** | 재계산 | `md_classify_run.py` 재실행 → `md_classify.json` 갱신. **G24·G25 판정** | ❌ | **30 min** |
| **10** | 재계산 | `report07_hover_long.py --preset outdoor`(OU) — 2 s 맵 | ⚠**GPU** | **~5 min** (이전 outdoor 런 4.9 분) |
| **11** | 그림 | `build_deck0811_range_figs.py` 잡음 배선 + `mode="over_noise"` 공통 눈금. **G15** | ❌ | **2 h** |
| **12** | 그림 | 새 그림 2 장 — `fd_edge` 관측성 vs 거리 · 분류 정확도 vs 거리(EIRP 2 팔) | ❌ | **2 h** |
| **13** | 그림 | 구간 라벨 스펙트로그램 (§1-6 (c), 선행연구 대응물) | ❌ | **1.5 h** |
| **14** | 서술 | 리포트 갱신 — 8권(맵 규약·사다리), 9권(한계), 12권(관측성), 13권(결과) | ❌ | **3 h** |
| **15** | 서술 | `docs/RETRACTION_LOG.md` 정정 3 건: «5 m 부터 묻힘» · «WOBBLE_HZ 2.7» · «SNR» 단일 이름 | ❌ | **1 h** |
| **16** | 발표 | 8/18 덱에 «거리 사다리» 부 + «로터 랜덤성» 부 | ❌ | **3 h** |

**합계 ≈ 26 h + GPU 5 분.** GPU 의존이 **한 칸(#10)뿐**이라는 것이 이 계획의 핵심이다.

### 권장 일정
- **8/11 (팀미팅 당일, 저녁)** — #1·#2 (3 h). 규약 문서 하나 + 게이트.
- **8/12** — #3·#4·#5 (7.5 h). 로터 커널 + 검증 하네스. **여기서 멈추면 아무것도 안 깨진다.**
- **8/13** — #6·#7 (1.7 h) + #8 시작. GPU 가 비면 #10 을 끼워 넣는다.
- **8/14** — #8·#9 (2 h) → **G24·G25 판정.** 여기가 «정직성의 관문» 이다.
  ⚠ 정확도가 87.8 % 에서 떨어질 것이다. **떨어지는 것이 정답이다** — 지금 값이 상한이었다.
- **8/15** — #11·#12·#13 (5.5 h). 그림 셋.
- **8/16~17** — #14·#15·#16 (7 h).
- **8/18** — 예비.

### ⛔ 순서를 바꾸면 안 되는 자리
- **#1·#2 가 #6 보다 먼저다.** 규약을 정하기 전에 원장을 다시 내면 두 번 낸다.
- **#3 이 #8 보다 먼저다.** 로터 모델이 바뀌면 분류 데이터셋이 통째로 무효다.
- **#5(검증 하네스)가 #6 이후 모든 재계산보다 먼저다.** 게이트 없이 돌린 결과는 못 믿는다.
- **#9 의 판정 전에 #16(덱)에 수치를 넣지 마라.**

---

# 5. ⚠미해결 선언 — 이 설계가 답하지 못하는 것

1. **`g_stft_db` 의 1차 문헌 근거가 없다.** Braun 식 (3.37) 은 2D 페리오도그램 것이고 STFT
   조각으로 옮긴 것은 우리 유추다. 리포트에 «우리 유추» 라고 적는다.
2. **`g_mf_db` 를 실사슬로 검증하기 전엔 «37 dB 를 얻는다» 고 단정하지 마라.** G12 가 그 관문이다.
   기준채널이 더럽거나 ECA 가 신호를 깎으면 줄어든다.
3. **ECA 노치와 `dc_ac_off_db` 의 관계를 모른다** (G16). 호버링 동체선이 지워지면 AC 보정이
   불필요해지고, 그러면 §1-4 의 거리표가 **17 dB 낙관 쪽으로** 움직인다.
4. **σ 자체의 불확실성이 사다리에 안 들어가 있다.** 우리 σ 는 Das 실측의 2.39 배다(열린 문제,
   `docs/RESUME.md`). 3.78 dB 는 거리로 **×0.79** 다. 거리 곡선에 이 불확실 띠를 그려야 한다.
5. **로터 시간흔들림에 문헌 선례가 없다** (§2-6). 실기 로그 3원천이 유일한 근거이고,
   셋 다 우리 표적 기체가 아니다.
6. **σ_w 보정에서 OU 를 «참» 이라고 가정했다.** 실제 스펙트럼이 OU 가 아니면 대역 몫 F 가
   달라진다. 우리가 가진 유일한 측정 스펙트럼이 우리 원장뿐이다(`rotor_randomness_survey.md` §7-6).
7. **바이스태틱 기하에서 σ 가 달라진다** — 사다리는 R_t·R_r 을 받지만 σ 는 모노 값을 쓴다.
   `sbr_field_bistatic` 팔과 잇는 것은 다음 라운드다.
8. **`prf_feasibility` 와 사다리의 결합을 아직 안 짰다.** 상시 기준신호 팔(LTE CRS 1 kHz ·
   5G SSB 50 Hz)에서는 ② 가 다르고 f_tip 이 접힌다. 그 팔의 거리 곡선은 별도 계산이다.

---

## 부록 A. 이 문서가 계산한 값 — 재현 방법

전부 CPU·수 초. 재현 스크립트를 `benchmark/verify_noise_rotor.py` 의 `--selftest` 로 넣는다.

| 값 | 계산 |
|---|---|
| `g_mf_db` = 37.06 dB | `10*log10(100e6/19700)` |
| `g_stft_db` = 16.69 dB | `nperseg = round(auto_periods(19700,126.667)*19700/126.667) = 70`; `10*log10(70) - 1.76` |
| CPI 2 s 코히어런트 이득 45.95 dB | `10*log10(2.0*19700)` — **④ 와 혼동 금지** |
| `snr_band(1 m)` = 37.77 dB | `nf.echo_over_noise_db(10**(-18.879/10), 1.0, 3.5e9)` — σ 는 **방위평균** |
| §1-4 거리표 | `37.77 − 40log10(R)` (+37.06 → ③) (−17.38 → ③′) (+16.69 → ⑤) |
| `dc_ac_off_db`(17.3 dB) = 17.38 | `10*log10(1+10**(17.3/10))` |
| 구간 (II) 27.3~74.3 m | ③′=0 → `10**(57.45/40)`; ③=0 → `10**(74.83/40)` |
| 분류 SNR→거리 | `R = 10**((C - s)/40)`, `C = 57.45`(12 dBm) / `108.45`(63 dBm) |
| σ_w 보정 F | `(2/π)*(arctan(2π·f2·T) - arctan(2π·f1·T))`, T = 0.2274 |
| 창평균 몫 | `(2T/Tw)*(1 - (T/Tw)*(1-exp(-Tw/T)))` |
| 정합필터 이득 실측 6.86 dB | L=5000 백색 기준, 표본당 −30 dB, 2,000 실현 |
| 40 m vs 3 m = 45.0 dB | `40*log10(40/3)` |
| 열잡음 −88.98 dBm | `kT0·F(5 dB)·100 MHz` / Sionna RT 기본 −113.93 dBm(`kTB`, 293 K, F 없음) |

## 부록 B. 손대는 파일 목록 (착수 체크리스트)

**이미 만들었다 (이 설계 라운드의 산출물)**
- `docs/NOISE_AND_ROTOR_PLAN.md` (이 문서) · `outputs/noise_rotor_plan.json` (수치 원장)

**새로 만든다 (착수 시)**
- `src/rotor_dynamics.py`
- `benchmark/verify_noise_rotor.py`
- `outputs/snr_convention.json` · `outputs/md_snr_vs_range.json` · `outputs/md_classify_vs_range.json` ·
  `outputs/verify_noise_rotor.json` · `outputs/rotor_jitter_model.json`

**고친다 (전부 opt-in, 기본 동작 불변)**
- `src/microdoppler_nearfield.py` — `snr_ladder()` 추가 · `ac_snr_db(exact=)` · `add_noise(ref=)` · `noisy_series()`
- `src/md_mapstyle.py` — `draw(mode=, noise_rms=)` · `caption_snr()`
- `src/articulated_fast.py:171-186` — `rotor_phases()` 2차원 rpm 허용
- `benchmark/report07_hover_long.py:70-76, 112-120` — 프리셋을 `rotor_dynamics` 로
- `benchmark/md_classify_dataset.py:405-419, 618-624, 806-811` — 위상·산포·잡음
- `src/experiment_md_range.py:124-125, 230-260` — 사다리 + meta
- `benchmark/build_deck0811_range_figs.py:88-91` — 잡음 배선 + 공통 눈금

**절대 안 건드린다**
- `src/passive_process.py` (읽기전용 규약) · `benchmark/link_budget.py`(재사용만) ·
  `team_meeting/` 전부 · `groupmeeting_*`
