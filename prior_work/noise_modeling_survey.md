# 레이더/ISAC 시뮬레이션의 잡음 모델링 — 조사 (2026-08-10)

> 조사 범위: ① Sionna 2.0.1 설치본이 잡음을 넣는 지점(소스 직독) ② 레이더 방정식에서 SNR 을
> 세우는 표준 ③ 드론 마이크로도플러 시뮬에 잡음을 넣은 문헌 사례와 **SNR 정의** ④ 거리에 따른
> 성능 저하를 그림으로 보이는 관례.
> 수치 원장: `outputs/noise_modeling_survey.json`.
> 인용은 전부 1차 자료(설치본 `파일:줄`, arXiv/DOI, 공개 PDF)로 달았다. 확인 못 한 것은 §6 에
> «못 찾았다» 로 남겼다.

---

## TL;DR — 다섯 줄

1. **Sionna 는 잡음을 «넣어 준다»가 아니라 «넣을 자리를 준다».** `sionna.phy` 는 AWGN 블록
   하나(`phy/channel/awgn.py`)로 **복소 백색잡음을 신호에 더할 뿐**이고, 잡음 전력 `no` 는
   **사용자가 계산해 넣는 스칼라**다. 열잡음(kTB)을 자동으로 세워 주는 코드는 `sionna.phy` 에
   **없다**(`BOLTZMANN_CONSTANT` 는 `phy/constants.py:10` 에 정의만 되고 패키지 어디에서도
   쓰이지 않는다).
2. **`sionna.rt` 의 경로 계산에는 잡음이 0 이다.** `rt/path_solvers/` 전체에서 `noise` 문자열이
   **0회**. 잡음은 오직 **라디오맵의 SINR 분모**로만 등장하고, 그것도 난수 실현이 아니라
   **결정론적 상수** N0 = k·T·B (`rt/scene.py:177`) 다. **잡음지수(F)가 없다** — 레이더 관례
   kT0BF 와 다르다.
3. **표준은 «시계열에 복소 가우시안을 더하고 그 다음 변환»이다.** Sionna 자신도
   `ApplyTimeChannel` 이 컨볼루션 **뒤 시간영역**에서 AWGN 을 더한다
   (`phy/channel/apply_time_channel.py:195-197`). 스펙트로그램(맵)에 실수 가우시안을 더하는 것은
   **다른 통계**를 만든다(맵 잡음은 지수분포이고 겹친 프레임끼리 상관되며 신호·잡음 교차항이
   사라진다). 문헌도 raw 신호에 먼저 넣는다 — arXiv:2604.12567 은 초록에 "spectrograms are
   corrupted"라고 써 놓고 본문에서 *"Noise was applied to the raw signals and the resulting
   signals were saved separately before the spectrograms were generated"* 라고 못 박는다.
4. **SNR 정의 차이는 문헌에서도 봉합돼 있지 않다.** 드론 마이크로도플러 논문들은 거의 예외 없이
   **표본당/펄스당(pre-integration)** SNR 을 쓴다 — arXiv:2403.02080 은 *"the **single pulse**
   signal-to-noise ratio, which is defined as 10log₁₀ A_r²/σ_n²"*, Drones 5(4):149 는
   `SNR = 10log10(A_r²/σ₀²)` 로 잡음을 주입해 놓고 같은 논문 §2.1.3 에서 레이더 방정식 SNR 을
   "SNR **Per Pulse** 13.535 dB"로 쓴다(둘은 대역폭 규약이 달라 **같은 수가 아니다**). 반대로
   OFDM 레이더/패시브 레이더 계열은 **처리이득을 명시적으로 분리**한다 — Braun 학위논문
   식 (3.37): `SNR_Per = SNR_F + PG`, `PG = 10log10(NM)`.
   → **우리 «표본당 0 dB에서 84 %»는 문헌 관례와 같은 층위다. 다만 «적분 후 몇 dB인가»를 함께
     써야 비교가 성립한다.**
5. **거리 의존성은 «절대 눈금»으로 보이는 것이 관례다.** Braun Fig. 3.5 는 레인지-도플러
   페리오도그램의 컬러바를 **`Received power (dBm)` −80…−24** 로 절대 표기한다.
   Remote Sens. 14(23):6146 은 CAF 피크를 *"24 dB above noise"* 로 **잡음 위 dB** 로 말한다.
   그리고 «성능 대 거리»는 맵이 아니라 **곡선**으로 보인다(Braun Fig. 5.5–5.6 = RMSE vs 거리의
   threshold effect, RS 14:6146 Fig. 14 = 검출거리 vs 적분시간, Fig. 15–17 = Pd vs 채움률).

---

## 0. 우리 기록과 겹치는 부분 (먼저 확인함)

`prior_work/` 를 먼저 훑었다. 겹치는 것:

| 우리 기록 | 겹치는 내용 |
|---|---|
| `prior_work/isac_standard_scenarios.md:292` | 3GPP ISAC 기지국 **잡음지수 FR1 5 dB / FR2 7 dB** — 본 조사의 «F 값을 뭘 쓰나»에 이미 답이 있다. 재조사 불필요. |
| `prior_work/isac_standard_scenarios.md:334` | 자기간섭 잔여를 *"modelled e.g. by additional AWGN, −94+X dBm in 100 MHz"* — **잡음항으로 흡수시키는 3GPP 관례**. 우리 §2 의 «잡음에 무엇을 합치나»와 직결. |
| `prior_work/sionna_sensing_survey.md:269` | Sionna 계열 센싱 논문 하나가 표적을 자유공간 점산란체로 두고 **"AWGN 만"** 두었다는 기록 — 본 조사에서 arXiv:2506.00497 이 **잡음조차 없다**(명시적으로 omit)로 한 단계 더 극단인 사례를 추가한다. |
| `src/microdoppler_nearfield.py:334-373` | ⭐**이미 있는 것** — `echo_over_noise_db()` 가 `P_n = k·T0·F·B` (T0=290 K, F=5 dB, B=100 MHz)로 **표본당** 에코/잡음비를 세우고, `add_noise()` 가 **시계열에 복소 가우시안**을 더한다. 즉 §2 의 «표준»을 우리는 이미 구현해 두었다. 문제는 **이 경로를 마이크로도플러 맵 생성이 안 쓴다**는 것뿐이다(현재 `experiment_md_range.py:158-162` 만 쓴다). |
| `src/microdoppler_nearfield.py:353-362` | `ac_snr_db()` — 총전력 SNR 에서 DC/AC 비(33~37 dB)를 빼는 우리 고유 보정. **문헌에서 대응물을 못 찾았다**(§6 참조). Drones 5:149 가 `A_r`(블레이드 반사 진폭) 기준으로 SNR 을 정의한 것이 가장 가까운데, 그쪽은 몸체 DC 항이 모델에 아예 없어서 문제가 발생하지 않는다. |
| `src/freespace_link.py:133-197` | 검출 사슬용 `n0_thermal(kT0F·B_noise)` + DPI/양자화 잡음 합성. 검출 쪽 잡음 모델은 이미 문헌 표준 이상이다. |

**결론: 새로 배울 것은 «어떻게 넣나»가 아니라 «어느 층위의 SNR 을 라벨로 쓰나»와 «그림에서 절대
눈금을 어떻게 유지하나»다.**

---

## 1. Sionna 2.0.1 이 잡음을 넣는 곳 — 설치본 소스 직독

설치 경로: `/home/yunjung/.venvs/py312/lib/python3.12/site-packages/sionna` (버전 2.0.1).

### 1.1 `sionna.phy` — AWGN 블록 하나가 전부

**`phy/channel/awgn.py`**

```
:21   The noise has variance ``no/2`` per real dimension.
:35   The noise power ``no`` is per complex dimension.
:77   noise = complex_normal(x.shape, precision=..., device=..., generator=self.torch_rng)
:85   no = expand_to_rank(no, x.dim(), axis=-1)
:89   noise = noise * no.sqrt().to(dtype=self.cdtype)
:92   return x + noise
```

규약 정리:
- `no` = **복소 차원당 잡음 전력**. 실수/허수 각각 `no/2`.
- 기저 난수는 `phy/utils/random.py:158-191` `complex_normal()` — 실·허를 각각 뽑고
  `× sqrt(0.5)` 해서 **복소 분산 1** 로 맞춘다(`random.py:190-191`).
- ⚠ 동명이인 주의: `phy/utils/misc.py:43-93` 에도 `complex_normal(shape, var=1.0)` 이 있고
  이쪽은 `var` 인자를 받아 `stddev = sqrt(var/2)`(`misc.py:86`). AWGN 블록이 쓰는 것은
  `random.py` 쪽(단위분산 고정)이다.

**잡음이 «신호 전력에 대해» 어디에 걸리나** — `phy/utils/misc.py:246-328` `ebnodb2no()`:

```
:310   ebno = 10.0 ** (ebno_db / 10.0)
:312   energy_per_symbol = 1.0            # E_s = 1 이 규약
:319   cp_overhead = resource_grid.cyclic_prefix_length / resource_grid.fft_size
:320-324  num_syms = num_ofdm_symbols * (1 + cp_overhead) * num_effective_subcarriers
:325   energy_per_symbol *= num_syms / resource_grid.num_data_symbols
:327   no = energy_per_symbol / (ebno * coderate * num_bits_per_symbol)
```

즉 **N₀ = (E_b/N₀ · r·M / E_s)⁻¹, E_s=1**. 신호는 **단위 에너지로 정규화**돼 있다고 보고
잡음 쪽을 조정하는 구조다. **절대 와트가 아니라 «심볼당» 상대 규약**이다 — 우리가
`add_noise(E, snr_db)` 에서 `p_n = p_sig/10^(SNR/10)` 로 쓰는 것과 **정확히 같은 층위**다.
OFDM 자원격자를 주면 CP·파일럿 오버헤드까지 반영해 준다는 점만 더 정교하다.

**어디서 호출되나 (= 잡음이 물리적으로 더해지는 지점):**

| 파일:줄 | 지점 |
|---|---|
| `phy/channel/apply_time_channel.py:114, 195-197` | **시간영역**. 채널 컨볼루션 결과 `y` 에 `if no is not None: y = self._awgn(y, no)` |
| `phy/channel/apply_ofdm_channel.py:93, 122` | **주파수영역**(자원격자 심볼에 직접) |
| `phy/channel/flat_fading_channel.py:163, 182` | 평탄페이딩 출력에 |

→ ⭐ **Sionna 자신이 «시계열(또는 그와 유니터리 등가인 자원격자)에 복소 가우시안을 더한다».
스펙트로그램·전력맵 같은 **비선형 산출물에 잡음을 더하는 API 는 없다.**

**열잡음은 `sionna.phy` 에 없다:**
```
phy/constants.py:10   BOLTZMANN_CONSTANT = scipy.constants.Boltzmann  # J/K
```
전 패키지 grep 결과 이 심볼을 **쓰는 곳이 한 군데도 없다**(정의만 있다). kTBF 를 세우는 헬퍼도
없다. **잡음 전력의 물리적 근거는 전적으로 사용자 몫**이다.

### 1.2 `sionna.rt` — 경로 계산엔 잡음이 없고, SINR 분모에만 있다

```
rt/path_solvers/paths.py            : "noise" 0 회
rt/path_solvers/field_calculator.py : "noise" 0 회
rt/path_solvers/path_solver.py      : "noise" 0 회
rt/utils/*.py                       : "noise" 0 회
```
→ **경로/CIR/도플러 산출물은 결정론적**이다. 확인 완료(예상대로).

`rt` 전체에서 `noise` 는 **12회**뿐이고 전부 라디오맵·씬 속성이다:

```
rt/constants.py:36   DEFAULT_BANDWIDTH = 1e6      # Hz
rt/constants.py:39   DEFAULT_TEMPERATURE = 293    # K   ← ⚠ 레이더 관례 T0=290 K 가 아니다
rt/scene.py:172-177  @property thermal_noise_power  →  return self.temperature * Boltzmann * self.bandwidth
rt/radio_map_solvers/radio_map.py:195-199
        # Thermal noise
        noise = self._thermal_noise_power
        sinr_map = rss / (interference + noise)
rt/radio_map_solvers/radio_map_solver.py:61-71
        SINR^k_i = RSS^k_i / (N0 + Σ_{k'≠k} RSS^{k'}_i)
        N0 = B × T × k
```

⭐ 세 가지 함의:
1. **난수가 아니다.** `noise` 는 SINR 분모에 들어가는 **상수**다. 잡음 «실현»을 만들지 않는다.
   그래서 Sionna RT 만으로는 «잡음 때문에 흔들리는 맵»이 절대 나오지 않는다.
2. **잡음지수 F 가 없다.** N0 = kTB 뿐. 레이더 표준(kT0BF)과 다르므로 우리가 F 를 따로 곱해야
   한다. 기본값으로 N0 = k·293·10⁶ = 4.045e-15 W = **−113.93 dBm**.
3. **경로 계산과 잡음이 완전히 분리**돼 있다. 이는 메모의 «σ 는 우리 커널, Sionna 는 환경»
   프레임과 정확히 같은 구조다 — Sionna 는 결정론적 채널까지만 주고, 잡음·검출은 사용자 층이다.

---

## 2. 레이더 방정식에서 SNR 을 세우는 표준

### 2.1 잡음 전력: N = k·Ts·Bn (·F)

MIT Lincoln Laboratory 공개 강의 *Introduction to Radar Systems*, Lecture 2 "The Radar Equation"
(R. M. O'Donnell, 슬라이드 `361564_P_9Y`/`_P_10Y`):

> "The noise power at the receiver is given by: **N = k Bn Ts**"
> "**S / N = Pt G² λ² σ / ((4π)³ R⁴ k Ts Bn L)**"

여기서 `Bn` 은 **수신기 잡음대역폭**(정합필터 대역 ≈ 1/τ)이고, 그래서 이 S/N 은
**펄스당·정합필터 이후** 값이다. 같은 강의의 예제 계산이 층위를 못 박는다(슬라이드 `_P_29Y`):

> "**S / N = 1.3 dB per pulse (21 pulses integrated) => S / N per dwell = 14.5 dB** (+13.2 dB)"

즉 **«펄스당 SNR»과 «드웰당 SNR»은 다른 수이고, 논문은 둘 다 써야 한다.**

Drones 5(4):149 의 식 (1) 도 같은 형태를 τ 로 쓴다:
`SNR = Pt·Gt·Gr·λ²·σ·τ / ((4π)³ R⁴ Tn kb L)` → Blake chart 로 "**SNR Per Pulse 13.535 dB**".

패시브 바이스태틱 버전 — Remote Sens. 14(23):6146 식 (9)(10):

> `Re < ⁴√( PT·GT·GR·S0·λ²·**Tint** / ((4π)³·L0·**D0**·k·T0) )`,  `T0 = Tref(10^(Nf/10) − 1)`

여기서 **Tint(적분시간)가 분자에 들어간다** = 처리이득이 레이더 방정식 안에 흡수된 형태이고,
`D0` 는 **검출계수(threshold, 표에서 11 dB)** 다. 잡음온도는 잡음지수에서 유도한다(표 2 에서
`T0 = 493 K`, 즉 Nf ≈ 4.4 dB).
⚠ 이 식은 **T0 = Tref(10^(Nf/10) − 1)** (초과 잡음온도)를 쓰므로 우리 `k·T0·F·B` (F 를 그대로
곱함)와 **정의가 미세하게 다르다**: 전자는 안테나 잡음온도를 따로 더하는 규약이고, 후자는
`kT0F·B` 로 한 번에 쓴다. 두 관례 모두 표준이고 값은 F 가 클수록 수렴한다. 우리 문서에서
어느 쪽인지는 명시해야 한다.

### 2.2 처리이득/적분이득: 어디까지가 «코히어런트 N»인가

MIT LL Lecture 5 "Detection of Targets in Noise and Pulse Compression Techniques"
(슬라이드 `Radar Course_12`):

> "**The coherent integration gain is equal to the number of pulses coherently integrated** —
>  2 pulses 3 dB / 10 pulses 10 dB / 20 pulses 13 dB. For this gain to be realized, the noise
>  samples, from pulse to pulse must be independent. The background noise is white Gaussian noise."

비코히어런트는 다르다(같은 강의 `Radar Course_13`): "**SNR Unchanged**, Noise Variance Reduced
after Integration (Allows Lower Threshold)".

OFDM/ISAC 판 정식화 — M. Braun, *OFDM Radar Algorithms in Mobile Communication Networks*,
PhD thesis, KIT, 2014 (공개 PDF, KIT 리포지터리 1000038892):

> 식 (3.35) `SNR_{F_Rx} = P_Rx / (k_B·ϑ·NF · N·Δf)`  ← **처리 전, 자원요소당** SNR. 분모가 kTBF.
> 식 (3.37) `**SNR_Per = SNR_F + PG**`,  `PG = 10 log10(NM)` — 각주 2: *"In [Richards], the
> general term chosen for this is **integration gain**."*
> 식 (3.41) 증명: `SNR_Per = b0²(NM)² / (NM·E[|Z|²]) = NM · SNR_F`
> 식 (3.76) 창 손실 포함: `PG = 10·log10(NM) + SNR_wd + SNR_wv`,
> 식 (3.77) `SNR_wd = |Σ w_k|² / (‖w‖²·N)` — Table 3.3 에 창별 손실(예: −1.35 / −1.81 / −3.02 dB).

⭐ **이것이 우리가 필요한 정확한 문장이다**: 표본당 SNR 과 «맵 위 SNR» 은 `+10log10(NM) + 창손실`
만큼 다르고, **창 함수를 쓰면 이득이 깎인다.**

Braun §3.3.6 는 이어서 CFAR 문턱을 잡음전력으로 직접 준다:
> 식 (3.92) `p_FA,bin = e^(−η/σ_N²)` — 페리오도그램 빈은 |AWGN|² 이라 **지수(χ²₂) 분포**.
> 식 (3.93) `η = −σ_N² ln p_FA,bin`
> 식 (3.150) `d_max,detect = ⁴√( Pmax·GRx·c0²·σRCS·NM / ((4π)³ fC² PN · SNR_min) )`
> — **NM(처리이득)이 최대탐지거리 안에 들어간다.**

### 2.3 «맵에 더하나, 시계열에 더하나» — 답: 시계열

**시계열에 복소 가우시안 → 그 다음 STFT 가 표준이자 물리적으로 옳다.** 근거 셋:

1. **구현 관례.** Sionna `ApplyTimeChannel:195-197`, RadarSimPy `_calculate_noise_amp`
   (아래), arXiv:2604.12567 ("applied to the raw signals ... before the spectrograms were
   generated"), Drones 5:149 식 (8) `ψ_final(t) = detection(ψ(t+ts), pd) + n` **그 다음** STFT.
2. **통계가 다르다.** 시계열에 백색 복소 가우시안을 더하면 스펙트로그램의 잡음 바닥은
   **지수분포**(Braun 식 3.92)이고 **겹친 프레임끼리 상관**되며 창 함수로 **색이 입혀진다**.
   반대로 스펙트로그램 이미지에 실수 가우시안을 더하면 이 세 성질이 전부 틀린다. 무엇보다
   **신호×잡음 교차항** `2Re(s·n*)` 이 사라져서, «약한 블레이드선이 잡음 속에서 흔들리는»
   현상 자체가 재현되지 않는다.
3. **CFAR 와의 정합.** 문턱은 `η = −σ_N² ln p_FA` 처럼 **잡음 전력** 으로 세운다. 맵에 직접
   더한 잡음은 이 σ_N² 과 연결되지 않으므로 검출확률을 말할 수 없게 된다.

**참고 구현(1차 자료, 코드)** — RadarSimPy `radarsimpy/radar.py` `_calculate_noise_amp()`
(공식 문서 `_modules` 자동생성 소스):

```python
input_noise_dbm = 10 * np.log10(BOLTZMANN_CONSTANT * noise_temp * 1000)   # dBm/Hz
receiver_noise_dbm = (input_noise_dbm + rf_gain + noise_figure
                      + 10*np.log10(noise_bandwidth) + baseband_gain)
receiver_noise_watts = MILLIWATTS_TO_WATTS * 10 ** (receiver_noise_dbm/10)
noise_amplitude_mixer = np.sqrt(receiver_noise_watts * load_resistor)
```
→ **kT + RF이득 + 잡음지수 + 10log10(B) + 기저대역이득** 을 dB 로 더해 **기저대역 시간표본에
더할 진폭**을 만든다. 우리 `freespace_link.n0_thermal` 과 같은 계보.

---

## 3. 문헌에서 드론 마이크로도플러에 잡음을 넣은 사례 — SNR 범위와 «정의»

| 논문 | 잡음 주입 지점 | SNR 정의 | SNR 범위 | 비고 |
|---|---|---|---|---|
| **Raval, Hunter, Hudson, Damini, Balaji**, *CNNs for Classification of Drones Using Radars*, **Drones 2021, 5(4), 149**, doi:10.3390/drones5040149 | **시계열**. 식 (8) `ψ_final(t) = detection(ψ(t+t_s), p_d=0.8) + n`, 그 뒤 long-window STFT | 식 (7) `SNR = 10log10(A_r²/σ₀²)` → `σ₀ = √(10^(−SNR/10) A_r²)`. **A_r = 블레이드 반사 진폭**(Martin–Mulgrew) 기준 = **표본당** | **0 ~ 20 dB, 5 dB 간격** | 같은 논문 §2.1.3 은 레이더 방정식으로 "SNR **Per Pulse** 13.535 dB" 를 따로 계산 — **두 SNR 을 잇지 않는다**(문헌의 전형적 구멍). 결과: X-band 2 kHz PRF, 학습 SNR 10 dB 에서 F1 = 0.816±0.011. 시료 길이 0.3 s |
| **Malarvanan**, *Hybrid Quantum NN Advantage for Radar-Based Drone Detection and Classification in Low SNR*, **arXiv:2403.02080** | 시계열(Martin–Mulgrew 복소 반환) | *"the **single pulse** signal-to-noise ratio, which is defined as 10log₁₀ A_r²/σ_n²"* = **펄스당** | 검출 **−5 ~ −20 dB**, 분류 **20 ~ −5 dB** (5 dB 간격) | 표본당 SNR 이 **음수**여도 되는 이유가 곧 처리이득. 논문은 그 이득을 명시하지 않는다 |
| **Mustafa, Liaquat, Abbasi, Hasan**, *Feature-Level Robustness of Physics-Guided Micro-Doppler Descriptors…*, **arXiv:2604.12567** | ⭐**본문이 명시적으로 raw 신호**: *"Noise was applied to the raw signals and the resulting signals were saved separately before the spectrograms were generated"* (초록은 "spectrograms are corrupted"라 오해 소지) | `x_awgn[n] = x[n] + w[n]`, `w ~ N(0, σ²)`, `σ² = 10^(−SNR/10)·P_signal`, **P_signal 은 세그먼트별**로 계산 = **표본당, 총전력 기준** | **−10, −7, −5…+5, +7, +10 dB** | 위상잡음 1°~10° 도 함께 스윕. 데이터: SAAB SIRS 1600 FMCW 77 GHz/160 MHz 실측 스펙트로그램(드론 44·새 56·리플렉터 19) |
| **Vovchuk 외 (Tel Aviv U. + Rafael)**, *Micro-Doppler-Coded Drone Identification*, **arXiv:2402.04368** | **측정 데이터**에 백색 가우시안 주입: *"Gaussian white noise was intentionally added to the measurements… 1000 numerical experiments with different noise realization"* | 명시 안 함(«noise level dB») | LS 법은 **12 dB 아래에서 붕괴**, CNN 은 더 버팀. **20 dB 이상에서 포화**, 저 SNR 에서 4-클래스 랜덤 25 % 바닥 | ⭐Pd-vs-SNR 곡선을 **두 알고리즘 겹쳐** 그린 판이 §4 의 좋은 본보기 |
| **Maksymiuk, Abratkiewicz, Samczyński, Płotka**, *Rényi Entropy-Based Adaptive Integration for 5G-Based Passive Radar Drone Detection*, **Remote Sens. 2022, 14(23), 6146**, doi:10.3390/rs14236146 | 합성 5G NR 신호(40 MHz, 61.44 MSa/s, SCS 30 kHz)에 **백색 가우시안**, 20 ms 구간 | «SNR» 을 **주입 수준**으로 씀(표본당). 처리이득은 레이더 방정식의 `Tint` 로 별도 | **0, 10, 20, 30, 40 dB** | ⭐우리와 가장 가까운 논문(패시브·5G·드론·CAF·CFAR). Pfa = 10⁻⁴ 등에서 **Pd vs 자원 채움률** 곡선. 20 ms×40 MHz → BT = **59.0 dB** |
| **Jopanya, Osorio**, *Utilizing 5G NR SSB Blocks for Passive Detection and Localization of Low-Altitude Drones*, **arXiv:2504.02641** | AWGN, 자원요소 단위 | `SNR_r = ρβg²/(σ_n²M)` — **BsB(기저대역 블록)에서의 표본당** SNR | **SNR_r = −10 dB, −7 dB** 에서 RMSE/CRB 제시 | CRB 식이 `SNR_r·N·L` 형태 → **적분이득이 식 안에 명시적으로 들어간다**. 표본당 −10 dB 에서 정상 동작하는 이유가 곧 N·L |
| **Westerkam, Damkjær, Villadsen, Poulsen, Pedersen**, *Second-Order Characterization of Micro Doppler Radar Signatures of Drone Swarms*, **arXiv:2506.00497** | ❌ **없음** — *"We focus on the micro-Doppler signature of the drones and therefore omit macro-Doppler, **noise**, and clutter in the model."* | — | — | ⭐**로터 랜덤성 앵커**: 각 로터 각속도가 **i.i.d. 𝒩(ω̄, σ²_ω), ω̄ = 523 s⁻¹, σ²_ω = 27 s⁻²** → 상대 산포 **σ/ω̄ = 0.99 %**. 우리 ±0.22 % 보다 **4~5배 크고**, 우리 공개 실기 로그 앵커(0.54 % / 2.4 %)의 사이에 있다 |

### 3.1 이 표에서 읽어야 할 것 (우리 실험에 직결)

- **드론 마이크로도플러 문헌의 «SNR» 은 거의 전부 표본당/펄스당이다.** −20 dB 까지 쓰는 논문이
  있다는 사실 자체가 그 증거다(적분 후라면 −20 dB 에서 아무 일도 안 일어난다).
  → **우리 «표본당 0 dB에서 84 %»는 문헌 대비 오히려 «쉬운» 조건**이다(Drones 5:149 는 학습
  SNR 10 dB, arXiv:2403.02080 은 분류를 −5 dB 까지 내렸다).
- **정의를 안 적으면 아무 비교도 성립 안 한다.** 같은 논문 안에서도 층위가 섞이는 사례를 두 건
  확인했다(Drones 5:149, 그리고 arXiv:2604.12567 의 초록↔본문). 우리는 두 수를 **항상 병기**해야
  한다.
- **우리 «37 dB 적분이득»은 조심해서 써야 한다.** 0.25 s × 20 kHz = 5000 표본 → 10log10(5000)
  = **37.0 dB** 는 «단일 도플러선을 CPI 전체에 걸쳐 코히어런트 적분»했을 때의 수다. 그런데
  스펙트로그램에서 블레이드선이 보이느냐를 좌우하는 것은 **한 STFT 조각의 길이**다
  (Braun 식 3.37 의 NM 은 «한 변환 블록»의 크기다).
  우리 `md_mapstyle.flash_spec` 은 조각 = 0.6 블레이드주기 → PRF 19.7 kHz·플래시 200 Hz 이면
  약 59 표본 → **10log10(59) = 17.7 dB**, Hann 창 손실 −1.8 dB 를 빼면 **≈ 16 dB**.
  `nperseg=256`(`md_metrics` 기본)이면 24.1 − 1.8 = **≈ 22.3 dB**.
  ⚠ 즉 **«37 dB 이득»과 «플래시 그림에서 보이는 이득»은 20 dB 넘게 다르다.** 시간분해능 우선
  정책(메모 `md-time-resolution-first`)이 곧 **감도를 20 dB 버리는 선택**이라는 뜻이고, 이건
  리포트에 반드시 적어야 한다. (이 계산은 **우리 산술**이지 인용이 아니다 — 근거는 Braun 식
  3.37·3.76 뿐이다.)

---

## 4. 거리에 따른 성능 저하를 그림으로 보이는 관례

**핵심: «맵을 자기 최대값으로 정규화»하는 순간 거리 정보가 사라진다는 문제는 문헌이 네 가지
방법으로 피한다.**

### (a) 컬러바를 절대 물리량으로 — 가장 정석
- **Braun, Fig. 3.5** (*"Example of a periodogram caused by five objects and WGN"*):
  컬러바가 **`Received power (dBm)`**, 눈금 **−80 … −24 dBm**. 정규화 없음. 잡음 바닥이 그림
  안에 그대로 보인다.
- 이 방식이면 «40 m 가 3 m 보다 몇 dB 약한가»가 **그림 자체에서 읽힌다**.

### (b) 잡음 위 dB (SNR 눈금) — 패시브 레이더 관례
- **Remote Sens. 14:6146**: CAF 결과를 *"the peak at the place of the object is a few decibels
  above noise level. Only in the last case could the target be clearly seen, **24 dB above
  noise**"* 로 서술. 즉 컬러 스케일의 0 점을 **추정 잡음 바닥**에 고정한다.
- CFAR 와도 자연스럽게 이어진다(문턱이 같은 눈금 위에 그려진다).

### (c) 하나의 연속 스펙트로그램에 거리 구간을 라벨링
- **arXiv:2402.04368, Fig. 4(b)**: 드론이 10 m 에서 레이더로 1.3 m/s 로 접근하는 **한 장의
  스펙트로그램**에 다섯 구간을 표시한다 —
  > "(I) the drone is too far and SNR is insufficient to make the detection, (II) SNR is
  > sufficient to detect the moving target (via Doppler effect), **but SNR is too low to see the
  > micro-Doppler**, (III) both Doppler and micro-Doppler are seen, (IV) … (V) …"
  ⭐ **«검출은 되는데 마이크로도플러는 안 보이는 구간»이 따로 있다**는 것을 그림 한 장으로
  보여주는 판. 우리 `ac_snr_db` 서사(총전력 SNR ↔ 블레이드선 SNR 이 33~37 dB 차이)와 **정확히
  같은 현상**의 실측판이다. 나란히 놓기 좋은 선행자료.

### (d) 맵을 포기하고 «성능 대 거리/SNR» 곡선으로
- **Braun, Fig. 5.5–5.6**: d₀ = 10…400 m 를 1 m 씩, 각 거리마다 10 000 회 몬테카를로.
  *"The attenuation b0 was calculated from the current value of d0 … **This creates a unique
  value of the SNR at every distance**"*, 그리고 *"the threshold effect previously discussed is
  clearly visible. **Beyond a certain distance, SNR becomes too low for the radar system to
  recognize the target reliably.**"* → RMSE vs 거리 곡선의 **문턱 꺾임**이 곧 «거리가 멀어지면
  어려워진다»의 정량적 표현.
- **Remote Sens. 14:6146, Fig. 14**: 검출거리 vs 적분시간(σ = 1/10/50/100 m² 별 곡선).
  Fig. 15–17: **Pd vs 신호 채움률**을 Pfa = 10⁻⁴ 등에서.
- **arXiv:2402.04368, Fig. 5(b)**: **Pd vs SNR** 두 알고리즘 겹쳐 그리기(랜덤 추측 25 % 바닥선
  표시).
- **MIT LL Lecture 5**: "Probability of Detection vs. SNR" — 교과서적 판.

### (e) 우리에게 주는 처방 (조사자 의견, 인용 아님)
1. 마이크로도플러 맵의 컬러바를 **`Echo power [dBm]` 절대 눈금**(또는 **`dB above noise`**)으로
   바꾸고 **모든 거리 패널에 같은 눈금**을 쓴다. 지금의 «각 맵 최대값 정규화» 를 버린다.
2. 각 패널에 **표본당 SNR / 조각당 처리이득 / 조각 후 SNR** 세 수를 라벨로 박는다
   (그림 안에 세팅 블록 금지 규칙이 있으므로 **캡션·리포트 본문**에).
3. 별도로 **«fd_edge 관측성 vs 거리»** 곡선(현재 NaN 반환 규약이 곧 «묻혔다»)을 그린다 —
   이것이 Braun 의 threshold effect 대응물이다.
4. 3 m·10 m·40 m 를 나란히 놓을 때는 **어느 다리(R_t/R_r)가 변하는지 명시**해야 한다.
   양쪽 다 변하면 40 m vs 3 m 는 **40log10(40/3) = 45.0 dB**, Tx 다리 고정이면
   **20log10(40/3) = 22.5 dB** 다.

---

## 5. 요약 권고 (우리 코드에 바로 대입)

| 항목 | 문헌 표준 | 우리 현재 | 할 일 |
|---|---|---|---|
| 잡음 주입 지점 | **시계열 복소 가우시안 → 그 다음 STFT** | `microdoppler_nearfield.add_noise()` 가 **이미 그렇게 한다** | 맵 생성 경로(`md_mapstyle`, `build_part07/08`)가 이 함수를 **거치게** 연결 |
| 잡음 전력 근거 | `kT0·F·B` (F = 3GPP FR1 5 dB) | `echo_over_noise_db()` 에 이미 있음(T0=290, F=5, B=100 MHz) | 그대로 사용. Sionna RT 의 kTB(F 없음, T=293)를 **그대로 믿지 말 것** |
| SNR 라벨 | **표본당과 적분 후를 병기** | 표본당만 | `snr_sample_db` + `pg_db(=10log10(N_seg)+창손실)` + `snr_map_db` 3종 기록 |
| 맵 스케일 | **절대 dBm 또는 dB-above-noise, 패널 공통** | 맵별 최대값 정규화 | 교체 |
| 거리 저하 표현 | **곡선**(RMSE/Pd vs 거리)이 본론, 맵은 예시 | 맵만 | `fd_edge 관측성 vs 거리`, `Pd vs 거리` 추가 |
| 로터 산포 | 문헌 앵커 **σ/ω̄ ≈ 1.0 %** (arXiv:2506.00497), 시간 흔들림은 **문헌에서 못 찾음** | ±0.22 % 상수, 흔들림 없음, t=0 위상 정렬 | 산포를 실기 로그(0.54 %) 또는 문헌(1.0 %)로 올리고 **t=0 위상은 U(0,2π)** 로 |

---

## 6. 못 찾은 것 (지어내지 않음)

1. **Griffiths & Baker, "Passive coherent location radar systems. Part 1: Performance
   prediction", IEE Proc. RSN 152(3):153–159, 2005, doi:10.1049/ip-rsn:20045082** — 서지사항은
   확정했으나 **본문을 못 읽었다**(IET 유료). "처리이득 BT, 패시브 레이더에서 전형적으로
   40–70 dB" 라는 값은 **2차 검색 요약에서만** 봤고 **원문 대조 못 함**. NATO STO
   EN-SET-119(2010)-03 도 **HTTP 403** 으로 접근 실패. → 이 수치는 인용하지 말 것.
2. **STFT(스펙트로그램)의 처리이득을 «10log10(창길이)»로 명시한 1차 문헌**을 못 찾았다.
   Braun 식 (3.37) 은 2D 페리오도그램(NM)에 대한 것이고, 이를 STFT 한 조각에 적용하는 것은
   **우리 유추**다. 마이크로도플러 논문 중 이 이득을 적은 것을 못 봤다.
3. **몸체 DC 대 블레이드 AC 의 SNR 구분(`ac_snr_db`)에 대응하는 문헌 정의**를 못 찾았다.
   arXiv:2402.04368 Fig. 4(b) 의 구간 II/III 구분이 **현상적으로는** 같은 것을 보여주지만
   정량 정의를 주지는 않는다.
4. **Sionna 공식 예제 중 «RT 경로 + 잡음 + 레인지-도플러» 를 잇는 것**이 설치본에 없다
   (설치 패키지에 examples/notebook 이 포함돼 있지 않음). 온라인 튜토리얼 쪽은 이번에 확인 안
   했다.
5. **로터 rpm 의 «시간에 따른 흔들림»(자세제어 미세조정)을 모델링한 마이크로도플러 문헌**을
   못 찾았다. arXiv:2506.00497 조차 로터별 각속도를 **시간에 대해 상수**로 두고 로터 간에만
   랜덤하게 뽑는다. → 우리 WOBBLE 항은 **문헌 선례 없이 실기 로그로만 근거를 대야 한다**
   (`outputs/rotor_rpm_web_anchor.json` 이 그 역할).
6. **arXiv:2504.02641 이 SNR_r 을 절대 링크버짓(거리·EIRP)과 연결하는 부분**은 5쪽 논문이라
   생략돼 있다 — «−10 dB 가 몇 m 인가»는 논문에서 못 읽었다.

---

## 부록 A. 확인한 1차 자료 목록

**코드(설치본/공개 소스)**
- `sionna/phy/channel/awgn.py:21,35,77,85,89,92`
- `sionna/phy/utils/random.py:158-191` · `sionna/phy/utils/misc.py:43-93, 246-328`
- `sionna/phy/channel/apply_time_channel.py:114,195-197` · `apply_ofdm_channel.py:93,122` ·
  `flat_fading_channel.py:163,182`
- `sionna/phy/constants.py:10` (정의만·미사용)
- `sionna/rt/constants.py:33,36,39` · `sionna/rt/scene.py:142-177` ·
  `sionna/rt/radio_map_solvers/radio_map.py:195-199` · `radio_map_solver.py:56-71`
- `sionna/rt/path_solvers/{paths,field_calculator,path_solver}.py` — "noise" **0 회**
- RadarSimPy `radarsimpy/radar.py::_calculate_noise_amp` (radarsimx.github.io `_modules` 소스)

**논문/강의 (전부 PDF 원문 확인)**
- MIT Lincoln Laboratory, *Introduction to Radar Systems*, Lecture 2 (The Radar Equation),
  Lecture 5 (Detection of Targets in Noise…), R. M. O'Donnell.
  https://www.ll.mit.edu/sites/default/files/outreach/doc/2018-07/lecture%202.pdf (및 lecture 5)
- M. Braun, *OFDM Radar Algorithms in Mobile Communication Networks*, PhD thesis, KIT, 2014.
  https://publikationen.bibliothek.kit.edu/1000038892/2987095 (식 3.35–3.41, 3.76–3.78,
  3.90–3.93, 3.147–3.150, Fig. 3.5, §5.2.1)
- D. Raval 외, *Drones* **5**(4):149, 2021. doi:10.3390/drones5040149 (식 1, 7, 8; Table 2)
- R. Maksymiuk 외, *Remote Sens.* **14**(23):6146, 2022. doi:10.3390/rs14236146 (식 9, 10;
  Table 2; §6)
- D. Vovchuk 외, *Micro-Doppler-Coded Drone Identification*, arXiv:2402.04368
- S. Mustafa 외, arXiv:2604.12567
- A. S. Malarvanan, arXiv:2403.02080
- P. Jopanya, D. P. M. Osorio, arXiv:2504.02641
- A. M. Westerkam 외, arXiv:2506.00497

**서지만 확보(본문 미확인)**
- H. D. Griffiths, C. J. Baker, IEE Proc. RSN **152**(3):153–159, 2005,
  doi:10.1049/ip-rsn:20045082
