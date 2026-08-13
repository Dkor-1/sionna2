> ⚠ **2026-07-31 재편으로 퇴역한 리포트의 설계서다** — 당시 사양을 그대로 보존한다. 현재 6편 구조는 [`../README.md`](../README.md) 와 [`REPORT_CODE_MAP.md`](REPORT_CODE_MAP.md) 에 있다.

# report13 확정 설계 — 자유공간 드론 검지거리 (5기종 × 9모드)

> ⚠ 2026-07-30: 표적이 7종이 됐다(비-DJI 2종 추가). **이 문서에 개수를 적지 않는다** — 정본은 `src/drones.py` 의 `DRONES` 이고 코드는 `viz_report13.DRONE_ORDER`(= `drone_order()`) 로 유도한다. 아래 렌더 파일명에 남은 `five` 는 **5종 시절 유래한 이름**일 뿐 내용은 전 기종이다.

> 뼈대 = **visual-first**(σ 3D 격자·k_mode 교정·헤딩 1급 변수·시각화 최대), 여기에 physics-first(가정 사다리·검증 상수·SNR 규약·range-walk)와 story-first(독자 여정·기종별 GIF·오경보 회계·Sionna 커널 유지·바이스태틱 근사 검증)를 전부 접목했다.
> 아래 **★측정** 표시 수치는 이번 조사에서 저장소 코드/JSON 을 읽거나 읽기 전용으로 직접 돌려 얻은 값이다. 나머지는 선언값이며 그렇게 표기했다.

---

## 0. 서사 — 독자가 따라가는 7단계와 헤드라인

### 0.1 헤드라인 (3층, 숫자는 전부 JSON 주입)

1. **주 헤드라인 (거리 밴드).** "EIRP {eirp} dBm 조명원·T_CPI {t} ms·Pd 0.9 @ 셀당 Pfa 1e-4·단일 CPI 에서, 자유공간 검지거리는 5G SSB 기준 {R:.0f} m [자세 커버리지 p10–p90: {lo:.0f}–{hi:.0f} m] 이다."
2. **부 헤드라인 (분산이 결론이다).** 한 기종의 **자세 변동**이 기종 간 차이보다 크다 — ★측정(report2 σ, 3.5 GHz, el=+15°): 기종 간 방위평균 최대차 8.37 dB(s1000plus −13.86 ↔ matrice4e −22.23) = 거리 1.63배인데, 한 기종 안의 p10↔p90 은 9.55(mavic4pro)~17.32 dB(phantom4) = 거리 **1.73~2.71배**다.
3. **부 헤드라인 (무엇이 벽인가는 조건부다).** 열잡음·ADC 동적범위·ECA 수치바닥·range-walk·전방산란(β>90°)·원거리장 — **여섯 개의 벽 중 어느 것이 binding 인지가 기하·조명원·수신기 조건마다 바뀐다.** 어느 하나를 리포트 헤드라인으로 세우지 않고, 셀마다 `limit` 라벨을 붙여 지도로 낸다.

> ⚠ visual-first 의 원안 헤드라인("EIRP 를 올려도 12-bit ADC 가 벽이다")은 **채택하지 않는다.** ★측정으로 재계산하니 그 결론은 PAPR 백오프(선언값)와 DPI 억압(0 dB 가정)에 걸려 있다 — 아래 §1.7 표. ADC 는 헤드라인이 아니라 **감도 패널**로 강등하고, 대신 "무엇이 벽인가는 조건부"라는 정직한 형태로 승격한다.

### 0.2 독자 여정 (story-first §0 이식)

| 절 | 독자의 질문 | 우리가 주는 답 | 그림·GIF |
|---|---|---|---|
| §0 | 왜 챔버를 벗어나나 | 01~12 는 R_b ≤ 22 m 관측창 안이었다. 거리 한계를 물으려면 벽을 지워야 한다. **σ 엔진은 원래 자유공간**(SBR 씬에는 표적 메쉬만 들어간다) — 바뀌는 것은 링크버짓·기하·검출기 형상뿐 | F1, F16, R3 |
| §1 | "거리"가 뭔데 | 패시브엔 거리가 셋이다: R1·R2·R_b=R1+R2−L. 감도는 (R1R2)² 로 떨어지므로 등감도선은 Cassini oval | F1, F2 |
| §2 | 표적이 뭔데 | 5기종 메쉬·재질색·실측 크기. σ 는 숫자가 아니라 (방위, 앙각)의 함수 | R1, R2, F5, F6 |
| §3 | 언제 "보인다"고 하나 | Pd 0.9 @ 경험 Pfa 1e-4, 단일 CPI, 스캔누적 없음 — **문턱을 가정하지 않고 몬테카를로로 측정** | F13 |
| §4 | 그래서 몇 m 인가 | 5기종 × 상시 3모드 R90 막대 + 자세 커버리지 밴드 | F3, F4, F12 |
| §5 | 왜 밴드가 그렇게 넓나 | σ 가 방위·앙각·헤딩에 따라 10~17 dB 숨쉰다 → R ∝ σ^(1/4) | F5, F6, F7, R2 |
| §6 | 무엇이 거리를 정하나 | EIRP^(1/4)·T_CPI^(1/4)(walk 벽까지)·기준신호 점유·λ²·베이스라인·수신기 동적범위 | F8, F9, F10, F11, R5, R7 |
| §7 | 믿어도 되나 / 못 하는 건 | 닫힌형↔측정 잔차, 경험 Pfa 재교정, ECA 수치바닥, 이등분선 근사 검증, 챔버 되돌리기 재현 | F13, F14, F15 |

---

## 1. 실험 설계

### 1.1 자유공간 가정 사다리 FS-0/1/2 (physics-first 이식 · 필수)

"자유공간"이라는 말이 리포트 안에서 흔들리지 않게 **세 단계를 선언하고 전부 계산**한다. 헤드라인은 FS-1.

| 단계 | 포함 | 배제 | 무엇을 재나 |
|---|---|---|---|
| **FS-0** | 표적 에코 + 열잡음 | 직접파·ECA·양자화 | 열잡음 한계 **상한** — 닫힌형의 순수 검증점 |
| **FS-1** (헤드라인) | + 직접파(기하에서 유도한 DNR) + ECA(ridge·탭 명시) + 0-도플러 가드 | 양자화 | 실제로 보고하는 R90 |
| **FS-2** | + `experiment_x410.adc_quantize(bits, full_scale)` 실통과 | — | 동적범위 벽이 **어느 조건에서** 서는가 |

전 단계 공통으로 **없는 것**: 지면·지면반사·바닥유령(report09 주제), 벽·챔버, 정적/동적 클러터(`clutter=()`), 다중경로, 대기·강우 감쇠, 안테나 패턴(스칼라 G_rx), 케이블 손실(`sys_loss_db=0`), 다중표적, 간섭 셀, 스캔 누적.

> 자유공간에는 **정적 클러터가 존재하지 않는다** — 챔버에서 "ECA 삼중차단으로 죽은 파라미터"였던 항이 여기선 애초에 없다. 그 자리를 §1.6(ECA 수치바닥)·§1.7(동적범위)이 대신한다.

### 1.2 기하 — 챔버 상수를 쓰지 않는다

`bistatic_scene.CHAMBER/TX/RX/TGT`·`geometry.RB_WINDOW_M/chamber_window/floor_ghost` 는 **import 하지 않는다**. 새 모듈 `src/freespace_scene.py` 가 자체 상수를 갖되, **부호·정의는 `bistatic_scene.bistatic_params`(src/bistatic_scene.py:37-50)와 완전히 동일**하게 복제한다(멀어지면 f_d<0). `radar_process.py`(모노스태틱, τ=2R/c)는 쓰지 않는다.

```
FS_TX  = (0.0, 0.0, 25.0)     # 조명원 마스트 25 m  — 선언값(근거문서 없음)
FS_RX  = (L,   0.0,  3.0)     # 패시브 수신기 3 m   — 선언값
FS_ALT ∈ {60, 120} m          # 표적 고도          — 선언값
FS_SPEED ∈ {5, 15} m/s        # 표적 속도
O = (TX+RX)/2 ;  P(d,φ) = O + d·(cosφ, sinφ, 0) + (0,0,FS_ALT−O_z)
u1 = (TX−P)/R1, u2 = (RX−P)/R2, Rb = R1+R2−L, τ=Rb/c, f_d = v·(u1+u2)/λ, β=∠(u1,u2)
```

**거리 용어 3개를 절대 섞지 않는다** — 캡션 규약으로 매 그림 반복 (physics-first 이식):
`d`(중점–표적 수평거리, 헤드라인 축) / `R2`(표적–수신기, 문헌 관행) / `R_b=R1+R2−L`(RD 맵 가로축, 실제 관측량) / 부수로 `κ=R1R2`, `R_eq=√κ`(Cassini 상수).

**★측정 — 이 기하가 실제로 방문하는 (β, el)** (L=500 m, TX z=25, RX z=3):

| alt | d=150 m | 300 | 1000 | 3000 | 10000 |
|---|---|---|---|---|---|
| 60 m | β 115.8° / el −17.0° | 79.0 / −8.7 | 28.1 / −2.6 | 9.5 / −0.9 | 2.9 / −0.26 |
| 120 m | β 107.4° / el −35.2° | 76.4 / −19.5 | 27.9 / −6.1 | 9.5 / −2.0 | 2.9 / −0.61 |

두 가지가 여기서 확정된다: **(a) 이등분선 앙각은 전 구간 음수다**(§3.1), **(b) 근거리·큰 L 조합은 β>90° 로 SBR 유효범위 밖이다**(§1.8).

### 1.3 스윕 축과 값

| 축 | 값 | 개수 | 근거 |
|---|---|---|---|
| 드론 | `mini5pro, mavic4pro, phantom4, matrice4e, s1000plus` | 5 | 사용자 지시. **크기 오름차순은 이 순서다** — ★확인: `src/anim_plots.py:439 drone_size_compare` 의 실제 order(phantom4 가 3번째) |
| 모드 | W1 W2 W3 · L1 L2 L3 · G1 G2 G3 (`experiment_detection.MODES`) | 9 | 헤드라인은 **상시 3인방 W1·L1·G1**, 나머지는 세션 상한선으로 옅게 |
| 반송파 | WiFi 5.21 / LTE 1.843 / NR 3.5 GHz (표준↔반송파 1:1) | 3 | 전 리포트 규약 |
| 기준채널 모델 | **① full-waveform capture(정본, report12 승계) ② pilot-only(`wf.ref`)** 두 열 병기 | 2 | §1.4 |
| 베이스라인 L | 100 / **500(헤드라인)** / 2000 m | 3 | DNR·β·ADC 벽을 동시에 정하는 유일한 자유도 |
| 고도 | 60 / 120 m | 2 | el 을 정한다(자유축 아님, §3.1) |
| 수평거리 d | 표시 그리드 `geomspace(100, 20000, 240)`, **R 은 격자에서 읽지 않고 이분법 역해** | — | 닫힌형이라 촘촘해도 공짜 |
| 헤딩 ψ (= 드론 yaw = 속도방향) | 0…359°, 1° | 360 | **σ 자세와 도플러를 동시에 구동하는 1급 변수** (visual-first 이식) |
| 장면 방위 φ | 0…355°, 5° | 72 | 커버리지 맵 |
| EIRP (등전력) | 63 dBm 전 모드 공통 | 1 | 파형 효과 분리(report05/12 공정성 규약) |
| EIRP (배치현실) | WiFi 30 / LTE 63 / NR 65 dBm | 3 | 두 관점을 **나란히** 낸다 |
| EIRP 사다리 | 20,30,40,50,60,63,70,80,90 dBm | 9 | F8 |
| T_CPI | **100 ms(헤드라인)**, 감도축 [56, 100, 200, 500, 1000] ms | 5 | M 이 아니라 **T_CPI 고정**(`check_detector_config` [R4]). walk 벽 초과 구간은 회색 |
| Rx 소자수 N | 1(헤드라인), 2, 3, 4 | 4 | report12 규약, +10log10N = 이상적 상한 |
| ADC bits | 12(X410), 14, 16, ∞ | 4 | ∞ = 현재 float 시뮬의 정직한 표기 |
| PAPR 백오프 | **0(기본), 6, 10 dB** | 3 | §1.7 — 기본을 저장소 값(DR=74 dB)으로 |
| DPI 억압 | **0, 20, 30 dB** | 3 | 지향 널·기준채널 격리 |
| ECA ridge_rel | **1e-6(정본)**, 1e-4(report12 값, 참조), 0 | 3 | §1.6 |
| Pfa | 셀당 1e-4(정본) + 1e-7(운용) | 2 | §2.4 |
| σ 통짜 시프트 | −3 / 0 / +3 dB | 3 | 상대결론 robust 확인 |

### 1.4 기준채널·듀티 규약 — 두 경로 불일치를 **두 축으로 분해**해 처리

physics-first 가 잡은 "WiFi 3.30 dB" 는 절반만 맞다. ★측정으로 확인한 두 개의 독립 불일치:

| # | 불일치 | 크기 | 처방 |
|---|---|---|---|
| **A. 듀티(PRF)** | `experiment_detection.CPI_CFG['wifi'] = b=9` 는 패킷 백투백(PRF 2136 Hz), `run_min_cell.frame_len` 은 1 kHz 슬롯 패딩(PRF 1000 Hz) | 고정 T_CPI 에서 **10log10(2136/1000) = 3.30 dB** | **경로 A 채택**: WiFi 프레임 = 1 패킷(52 µs)을 1 ms 로 제로패딩, 듀티 5.2%. LTE 1 ms/PRF 1 kHz, NR 0.5 ms/PRF 2 kHz(★`verify_linkbudget.json` prf_hz 1000/1000/2000 과 일치). `meta.cpi.duty_model` 에 명시하고 report12 대비 3.30 dB 를 기록 |
| **B. 기준신호** | 경로 A 는 `wf.ref`(수신기가 아는 파일럿만), 경로 B 는 `wf.tx`(풀 파형) | ★`verify_linkbudget.json pilot_power_frac_db`: **WiFi −24.11 / LTE −5.80 / NR −5.49 dB** → WiFi 는 거리 **4.0배**, LTE/NR 은 1.4배 | **두 열 병기**. 정본 = full-waveform capture(report12 승계, `meta.reference_model="full_waveform_capture"`), 병기 = pilot-only. 헤드라인 문장에 어느 모델인지 반드시 붙인다 |

★설계시점 앵커(닫힌형, L=500 m, alt 60 m, T_CPI 200 ms, SNR90 16.3 dB(mean 규약), 손실 −2 dB, σ=el+15 p50):

| 모드 | EIRP | full-waveform d | pilot-only d |
|---|---|---|---|
| L1 (LTE CRS) | 47 / 63 dBm | 2.25 km / 5.69 km | 1.60 km / 4.07 km |
| G1 (5G SSB) | 47 / 63 dBm | 1.50 km / 3.82 km | 1.08 km / 2.78 km |
| W1 (WiFi LTF) | 30 / 47 dBm | 452 m / 1.36 km | **β>90° 무효** / 232 m |

WiFi 배치현실(30 dBm) × pilot-only 는 유효범위 밖으로 떨어진다 — 축을 자르지 말고 **회색 처리 + "invalid: β>90°" 라벨**로 그린다(§1.8).

### 1.5 검출기 형상 — 두 형상을 **둘 다** 측정한다

챔버값(`N_RANGE=32, N_TAPS=40`)은 못 쓴다. 그렇다고 한쪽만 고르면 story-first(게이트=탐색 없이 얻은 거리)와 physics-first(전체 창=경험 Pfa 폭발 위험) 중 하나의 결함을 그대로 물려받는다. → **두 형상을 같은 파이프라인에서 재고 표로 낸다.**

| 형상 | n_range | n_taps | 성격 | 역할 |
|---|---|---|---|---|
| **S-G (게이트)** | 64 (표적 진리 R_b 중심) | **128** (≥ n_range) | 표적 위치를 아는 검출기 | 전이곡선·헤드라인 |
| **S-W (전체 창)** | Rb 범위 전체 (NR fs=122.88 MHz, Rb 6 km → 2460빈 등) | 128 | 탐색하는 검출기 | 경험 Pfa·CPI당 오경보 회계 |

공통: CA-CFAR guard (2,2)/train (6,6) 불변(리포트 간 비교가능성), 표적셀 허용 ±2빈, 0-도플러 가드 `doppler_guard_mask(width=3)`.

**훈련셀 배제는 직접 구현한다.** ★확인: `passive_process.py:295` 가 "이 함수는 검출 마스크만 다룬다"고 명시 — `also_exclude_from_training=True` 를 넘겨도 훈련셀은 안 바뀐다. 또 visual-first 의 "가드행을 열 중앙값으로 치환"은 지수분포 median = 0.693·mean 이라 훈련평균을 1.59 dB 낮춰 문턱을 내린다. → **가드행을 제거한 부분맵에 `ca_cfar_2d` 를 적용**하고, 그 행의 검출은 별도로 막는다(`freespace_detect._cfar_excl_rows()`).

**`PFA_CALIBRATION` 표는 쓰지 않는다** — ★코드가 "챔버 거리창 전용"이라 명시(`passive_process.py:254`). 자유공간 두 형상에서 각각 경험 Pfa 를 재측정해 명목 Pfa 를 이분법으로 재교정하고(K_pfa=20000, 0-도플러 ±2행 제외·분모=유효셀), 챔버 표는 **참조로만 병기**한다.

**Sionna PHY 는 정본 에코 생성기로 유지한다** (story-first 이식, 기술적으로 옳음). ★확인: `sionna_chain.channel_taps(a, tau, bandwidth, max_delay_spread=1e-6, ...)` 의 `max_delay_spread` 는 **인자**다 — 기본 1e-6(Rb≈315 m)은 한계가 아니다. `max_delay_spread = 1.3·R_b/c` 로 동적 설정하고(Rb 6 km → 26 µs), 해석적 분수지연(`analytic_echo`)은 대조군으로 두어 상관계수를 JSON 에 남긴다(report12 실측 0.9997~0.99999).

### 1.6 ECA 수치바닥 — ★이번 조사에서 확정한 **가장 중요한 정정**

세 설계안이 모두 "float64 ECA = 무한 동적범위 = 우리 결과는 낙관적"이라고 썼다. **반대다.** ★측정(실제 `passive_process.ECACanceller`, 실제 파형, n_taps=64, M=8):

| 기준신호 | ridge_rel=1e-4 (=report12 `Precomputed` 가 쓰는 값) | ridge_rel=0 |
|---|---|---|
| WiFi (G1) | −79.5 dB | −136.9 dB |
| LTE (G1) | −69.0 dB | −135.8 dB |
| **NR G1(SSB)** | **−50.3 dB** | −134.9 dB |
| NR G3(PRS) | −74.3 dB | −134.7 dB |

그리고 그 유한 깊이가 **RD 맵의 비-0도플러 셀로 새는 지점**(★측정, NR G1, M=32, n_range=256, 잡음전용 대비):

| ridge | DNR 80 dB | DNR 100 dB | DNR 120 dB |
|---|---|---|---|
| 1e-4, n_taps 64 | med +0.0 / p99 +0.0 | med +0.8 / **p99 +5.9** | med +4.6 / **p99 +24.2** |
| 1e-4, n_taps 320 | +0.0 / +0.0 | +0.0 / +0.2 | +0.0 / +0.2 (max +25.6) |
| **1e-6, n_taps 128** | **+0.0 / +0.0** | **+0.0 / +0.0** | **+0.1 / +0.0** |
| 0, n_taps 128 | +0.0 / +0.0 | +0.0 / +0.0 | −0.0 / +0.2 |

자유공간 DNR 은 70~130 dB 구간이므로 report12 의 ridge 1e-4 를 그대로 쓰면 **NR/SSB 결과가 물리가 아니라 대각로딩 잔류를 재게 된다.** 처방:

1. report13 정본은 **`ridge_rel=1e-6`, `n_taps=128`**. `meta.detector.eca` 에 명시.
2. `dnr_sweep`(40~140 dB) × ridge{1e-4,1e-6,0} × n_taps{64,128,320} 로 **ECA 수치바닥 곡선을 먼저 재서** `meta.detector.eca_numerical_floor` 에 남긴다. 잔류 p99 가 잡음 대비 **+0.5 dB** 를 넘는 셀은 `limit="eca_numeric"` 로 라벨하고 그림에서 회색 처리.
3. **caveat 의 부호를 뒤집는다**: "이상화라 낙관적" ❌ → "우리 ECA 는 ridge 1e-6 에서 사실상 이상적이다. 실장 ECA·아날로그 소거의 유한 제거깊이(문헌 통상 40~90 dB)는 **모델에 없다** — 그것이 진짜 낙관 방향이다."

### 1.7 동적범위 — 헤드라인이 아니라 **조건부 감도 패널**

`N0_quant = P_dir · 10^(−(DR + supp)/10) / fs`, `N0_eff = N0_thermal + N0_quant`, `DR = 6.0206·bits + 1.76`(★`experiment_x410.py:79`, 12 bit → 74.0 dB). `P_echo/P_dir = σL²/(4π R1²R2²)` 에서 EIRP·λ 가 약분되므로 `R_adc ∝ (σ L² 10^(DR/10) f_s η T)^(1/4)` — **EIRP 무관·L^(1/2)·f_s^(1/4)** 이고 이 물리는 옳다.

★측정(재계산) — `N0_quant − N0_thermal` [dB], G_rx 10 dBi, NF 5 dB:

| 조건 | LTE (fs 30.72M) | NR (fs 122.88M) | WiFi (fs 80M) |
|---|---|---|---|
| L=100, EIRP 63, DR 74, supp 0 | **+15.4** | **+3.8** | **+2.2** |
| L=500, EIRP 63, DR 74, supp 0 | +1.4 | −10.2 | −11.8 |
| L=500, EIRP 63, DR 64(백오프10), supp 0 | **+11.4** | −0.2 | −1.8 |
| L=500, EIRP 63, DR 74, **supp 20** | −18.6 | −30.2 | −31.8 |
| L=2000, EIRP 63, DR 74, supp 0 | −10.7 | −22.2 | −23.8 |

→ **ADC 가 binding 인 영역은 존재하지만(짧은 L·높은 EIRP·낮은 fs·억압 없음), 백오프 10 dB 나 억압 20 dB 하나로 결론이 뒤집힌다.** 그래서:
- 기본값은 **저장소 값 그대로 DR=74 dB, 백오프 0 dB, supp 0 dB**. 백오프·억압·bits 를 **반드시 스윕**한다.
- 교차점은 **밴드별로 따로** 낸다(N0_quant ∝ P_dir/f_s 이므로 LTE↔NR↔WiFi 가 다르다).
- FS-2 에서 `adc_quantize()` 를 실제로 통과시켜 Pd 저하를 측정하고 예측과 대조(`dynamic_range.fs2_measured_pd_drop_db`).
- 그림 F11 의 결론 문장은 "ADC 가 벽이다"가 아니라 **"이 조건범위에서 벽이 되고 저 조건에선 안 된다"**.

### 1.8 유효범위 게이트 — 축 전체에 건다

세 게이트를 **모든 셀에 적용**하고, 위반 셀은 수치를 인용하지 않고 회색/해칭 처리한다(그림 x축을 자르지 않는다).

| 게이트 | 조건 | 근거 |
|---|---|---|
| **전방산란** | β ≤ 90° 만 인용 | ★`rcs_sbr.py:252-255` — 조명/수신 게이트 상호배타로 β→180° 에서 σ≡0. 이 기하는 근거리에서 β 116°(L=500,d=150)까지 간다 |
| **원거리장** | d ≥ 2D²/λ | ★`radar_scene.farfield_distance(target_extent(k), fc)` 로 통일: @5.21 GHz mini5pro 5.0 / mavic4pro 10.7 / phantom4 7.7 / matrice4e 12.0 / **s1000plus 63.1 m**. (설계안들이 쓴 131 m 는 D 를 대각으로 잡은 값 — 두 D 정의를 `meta.farfield.D_definition` 에 병기) |
| **ECA 수치바닥** | 잔류 p99 ≤ 잡음+0.5 dB | §1.6 |

부수로 `T_walk`(§6 `walk`)·`limit` 라벨(`thermal / adc / eca_numeric / walk / farfield / beta`)을 셀마다 기록한다.

### 1.9 range-walk 상한 (physics-first 이식)

ΔR_b = c/B → `T_max = ΔR_b / v_radial`:

| 기준신호 | ΔR_b | T_max @5 m/s | @15 m/s |
|---|---|---|---|
| 5G NR-PRS 98.28 MHz | 3.05 m | 0.61 s | 0.20 s |
| WiFi VHT-LTF 75.6 MHz | 3.96 m | 0.79 s | 0.26 s |
| LTE CRS/PRS 18 MHz | 16.66 m | 3.33 s | 1.11 s |
| 5G SSB 7.2 MHz | 41.64 m | 8.33 s | 2.78 s |

**광대역일수록 코히런트 적분을 오래 못 한다** — 대역폭 서사의 정확한 반전. 도플러 walk `T < √(Rλ)/v_t` 도 함께 검사해 `walk.doppler_walk_T_max_s` 에 기록. T_CPI 감도축에서 벽을 넘는 구간은 **빨간 해칭 + 수치 인용 금지**("CPI 1 s"는 NR·WiFi 에서 이미 깨진다).

---

## 2. 검지거리의 정의 — 3층 (visual-first 이식, 이름 충돌 해소)

### 2.1 1층 — 잡음에 대한 확률 (측정한다)

> `SNR90(mode, shape, N)` = 검출확률 Pd = 0.90 이 되는 RD 출력 SNR. Pfa 는 **경험적으로 측정한** 셀당 1e-4.

- SNR 축 정의를 **mean 규약**으로 통일한다. ★확인: `experiment_detection.measure_single_snr:232` 는 `median(rd²)` 를 쓰고 잡음셀 전력은 지수분포라 `median = ln2·mean` → **report12 축 = 닫힌형(mean) + 1.59 dB**. 빼먹으면 모든 거리가 `10^(1.59/40) = 9.6%` 낙관된다. `meta.detector.snr_convention` 과 **모든 그림 캡션에 "which SNR"** 을 반복 표기하고 변환값을 JSON 에 남긴다.
- K = 4000(`SIONNA2_DET_K`), snr_grid 1 dB 간격, Pd 마다 Wilson 95% CI, `snr90_lo/hi` 도 보간해 기록.
- `SNR50` 도 낸다(report12 접속점). ★report12 측정 SNR90−SNR50 = W1 2.88 / L1 2.45 / G1 2.76 dB → 거리비 1.15~1.17배. 이 환산표를 본문에 넣는다.
- **왜 Pd 0.9 인가**: 문헌에 통일 규약이 없다(Pd 0.74/0.78/0.8, POD 24~78%). 우리가 정한 기준이라고 쓰고, MathWorks 예제처럼 "최소검출 SNR 12 dB 가정"은 **하지 않는다**(측정한다)는 점을 대비축으로 쓴다.

### 2.2 2층 — 헤딩·기하에 대한 결정론 (도플러 가시성)

> `|f_d(ψ, φ, d)| ≥ f_guard = 2.5/T_CPI` 를 못 넘으면 **SNR 이 아무리 높아도 미검출**로 센다.

`f_d = v·(u1+u2)/λ`, `v = FS_SPEED·(cosψ, sinψ, 0)`. report05 hover-blind 의 자유공간판이고, 헤딩축이 실제로 일을 하게 만든다. 블라인드 헤딩 비율을 모드·속도별로 낸다.

### 2.3 3층 — 헤딩 분포에 대한 커버리지 (최종 헤드라인)

> **`R90_C50` := 헤딩 ψ 가 균등분포일 때 `P_ψ[ Pd(ψ,d) ≥ 0.9 ] ≥ 0.50` 을 만족하는 최대 d.**
> 밴드 = `R90_C10`(헤딩의 90%에서 달성) ~ `R90_C90`(10%에서만 달성).

**이름 규약(충돌 해소)**: 아래첨자 앞 = Pd 기준, `C` = 커버리지 백분위. `R50_C50` 은 Pd 0.5 판. 슬래시 표기(`R90/50`)는 금지 — Pd 축과 헤딩 축이 섞여 보인다.

부수 지표: 커버리지 곡선 `C(d) = P_ψ[검출]`(S 곡선), `R_C80`(C=0.8 지점), `R10_C50`(전이 폭), 그리고 각 R 에서의 `R_b`, `κ`, `β`, `el`, `DNR`.

**단서 3개를 §2 첫 문단에 박는다**: 단일 CPI(스캔누적·M-of-N 없음) / 단일 표적 / CPI 내 σ 고정(비요동).

### 2.4 오경보 회계 (story-first 이식 · 필수)

셀당 Pfa 만으로는 오해된다. **S-W 형상에서 CPI 당 기대 오경보 수**를 반드시 함께 보고한다(예: 2460 거리빈 × 200 도플러 × 1e-4 ≈ 49건/CPI). 그리고 운용 Pfa **1e-7 컬럼을 병기**한다 — ★`verify_linkbudget.json` 의 `alpha_ca = 9.373`(n_train 264, Pfa 1e-4)에서 1e-7 로 조이면 문턱 +2.5 dB → **거리 ×0.87**. "운용 가능한 오경보율로 조여도 거리는 13%만 잃는다"가 §3 의 한 줄이다.

### 2.5 파이프라인 이득은 **측정한다** — k_mode 교정 (visual-first 이식 · 필수)

닫힌형 부기(η_ref·창손실·straddle·median 규약)를 손으로 맞추면 조용히 틀린다(★이번 조사에서 실제로 겪었다 — 기준신호 모델 하나로 절대거리가 4배 어긋난다).

```
k_mode[dB] = SNR_RD_measured(알려진 σ·기하) − 10log10(P_echo/N0)
```
- 잔차 `verify.snr_model_resid_db` 목표 |Δ| < 0.5 dB, 닫힌형 예측과 나란히 기록.
- **σ 불변성 어서션**: σ 를 10 dB 흔들어도 `k_db` 가 불변인지 확인 → `verify.k_sigma_invariance_db`.
- 닫힌형은 이렇게 쓴다(검증용 예측식). ★상수는 전부 `outputs/verify_linkbudget.json` 에서 읽는다(손으로 적지 않는다):

```
SNR_RD[dB] = EIRP−30 + G_rx + 20log10λ + 10log10σ − 30log10(4π) − 20log10R1 − 20log10R2
             + 174 − NF + 10log10η_ref + 10log10T_CPI + L_win + L_straddle + L_CFAR
L_win  = −1.898(WiFi) / −1.730(LTE) / −1.814(NR) dB
L_str  = 도플러 반빈 −1.364/−1.397/−1.371 + 거리 반빈 −3.482/−1.241/−2.292 dB (반빈 최악 기본)
L_CFAR = −0.076 dB (n_train 264)
```
★이 닫힌형이 저장소 측정과 맞는다는 증거: LTE `mf_gain 39.07 + cpi_gain 16.81 − 40(주입) = theory 15.883` vs `meas_rect_ongrid 15.787`(−0.096 dB), WiFi +0.032, NR −0.010 dB. **대역폭 B 는 SNR 항에 없다** — B 는 ΔR_b 와 walk 상한에만 들어간다(F2·F15 가 이를 그림으로 증명).

---

## 3. σ 자세의존 처리 — 단일값 금지

### 3.1 ★가장 중요한 정정: 앙각은 **음수**다

세 설계안 모두 el 격자를 양수(0…+90°)로 잡았다. ★§1.2 측정대로 지상 TX/RX + 공중 표적의 이등분선 el 은 **전 구간 음수**(−0.26°…−35.2°)다. 즉 지상 수신기는 드론의 **배(belly)** 를 올려다본다.

★스모크 측정(실제 `rcs_sbr_batch`, 3.5 GHz, az 12점, div=12):

| 드론 | el=+15° | el=−15° | el=−40° |
|---|---|---|---|
| mavic4pro | −20.11 dBsm | **−16.93** | −18.07 |
| s1000plus | −17.46 dBsm | **−11.67** | −12.75 |

부호를 틀리면 σ 를 3.2~5.8 dB 어둡게 잡아 거리를 20~35% 과소평가한다. 처방:

1. **el 격자 = [0, −2, −5, −10, −15, −20, −30, −45, −60]° (9점)**. 그 사이는 **선형 m² 보간**(dB 보간 금지 — 널을 과도하게 깊게 만든다).
2. **el 은 스윕축이 아니다.** `el = look_angles(u1,u2)` 로 기하에서 유도하고 R 해와 함께 푼다. (physics-first 의 독립 el 축은 `el=60°·R=2 km` 처럼 고도 1.7 km 를 함의하는 불가능한 셀을 만든다 — 폐기.)
3. physics-first 의 **"머리 위 σ 급증(overhead spike)" 서사는 삭제**한다. 대신 F9 를 **"저고도 근거리에서 배를 크게 본다"**로 반전시키고, `el>0`(공중 조명원·수신기) 은 이 리포트 범위 밖이라고 명시한다.
4. `el ≤ −45°` 구간은 β>90° 게이트와 겹치므로 보간 신뢰도가 낮다고 표기.

### 3.2 σ 격자 생산 규약

```
producer: src/experiment_freespace_sigma.py → outputs/report13_sigma_grid.json
엔진 : rcs_sbr.rcs_sbr_batch(penetrate=True, jitter=2, div=16, cache_key=(drone, round(fc/1e6)))
az   : 0…357°, 3° (120점)      el : 위 9점(전부 ≤0)
fc   : 각 반송파 ±1.5% 3점(n_f=3)   각도평활 3°
규모 : 5 × 3밴드 × 3주파 × 9 el × 120 az = 48,600 az-eval
```

- **div=16 으로 report2 와 맞춘다**(★report2 meta: `sbr_div=16, az_step=1.0, n_f=5, el_deg=15`). div 12 로 낮추면 report02/08/12 와 σ 비교가능성이 조용히 깨진다. 대신 `n_f` 를 5→3, az 를 1°→3° 로 줄여 비용을 상쇄하고, 한 슬라이스(mavic4pro @3.5 GHz, el=−15°)를 div=12/24 로 재계산해 `grid_check.delta_db` 에 남긴다.
- **`rcs_sbr()`(다중반사)는 쓰지 않는다** — `penetrate`·`jitter` 인자가 없어 같은 조건에서 −3 dB 낮게 나온다. 다중반사 실익은 −0.32~+0.18 dB(`report6_sbr.json`).
- **캐시**: ★`rcs_sbr._scene_for` 의 `_SCENE_CACHE` 키는 이미 `(key, fc_MHz, exclude)` 이고 씬은 el 무관이다 — visual-first 의 "cache_key 에 el 을 넣어라"는 **오진이며, 넣으면 같은 씬을 9배로 만들어 GPU 메모리만 낭비한다.** σ 값 캐시는 `channel._sig_key`(az·el·fc·메쉬지문 포함)가 이미 유일화한다.
- **프리필**: 새 워커를 짜지 말고 **`channel.sbr_sigma_prefill()` / `channel._prefill_worker` 를 그대로 재사용**한다 — ★그 함수 안에 `gpu.pick`/`budget_mb` NameError 우회가 이미 들어 있다(`benchmark/channel.py:167-173`). mitsuba import **전에** 호출.
- **조회 규약(정본 단일화)**: `channel.look_angles(u1, u2, az_span_deg=8.0, n_az=5)` 이등분선 + ±4°/5점 **선형 m² 평균**. report12 관례(감시배열→표적 방위·el=0 단일자세, σ=−27.96 dBsm=널 근처, `docs/AUDIT_FINDINGS_0722.md` 지적항목)는 **쓰지 않고**, 같은 기하에서 두 규약의 σ 차이를 표로 낸다(`verify.sigma_convention_delta_db`).
- **드론 yaw(헤딩) 결합**: σ 조회 방위는 `az_look − ψ`. 즉 **헤딩 하나가 σ 자세와 도플러를 동시에 움직인다.**

### 3.3 분포를 제시하는 6가지 형태 (전부 그림이 있다)

| 형태 | 정의 | 그림 |
|---|---|---|
| 커버리지 밴드 | `R90_C10 / C50 / C90` | F3, F12 오차막대 |
| 커버리지 곡선 | `C(d) = P_ψ[검출]` | F4 |
| 헤딩 극좌표 발자국 | θ=헤딩 ψ, r=R90 [m], **블라인드 섹터는 r=0 으로 함몰** | F7, R2 |
| σ (az,el) 히트맵 | 5기종 × 밴드 | F5 |
| σ CDF ↔ R CDF 대응 | σ^(1/4) 매핑 화살표 | F6 |
| Swerling-1 대조 | 지수분포 KS 적합 + 요동손실 dB·m **나란히**(겹쳐 쓰지 않는다) | F6 삽입 |

**절대 하지 않는 것**: 널 최소값(σ_min) 인용, 절대 dBsm 점값 단정, aspect-peak 로 최대거리 자랑, 단일 "검지거리 N m" 헤드라인 (`rcs_po.py:184-194` 규약).

### 3.4 바이스태틱 근사 검증 (story-first 이식 · 필수)

세 안이 공유하는 **최대 미검증 가정** = "이등분선 등가 모노스태틱 σ 를 바이스태틱 기하에 쓴다". ★`src/rcs_sbr.py:239 rcs_sbr_multistatic` 가 저장소에 실재하므로 실제로 잰다:

- β ∈ {0,15,30,45,60,75,90}° × az 24점 × 전 기종 × 3밴드 → `Δσ(β) = σ_multistatic − σ_bisector` 의 mean/rms/p95.
- 조명(광선추적)은 û_i 로 한 번만 쏘고 û_s 만 바꾸므로 비용이 싸다.
- 결과가 β 유효범위(≤90°)를 정당화하거나, 못 하면 그 사실을 그대로 남긴다. 상반성 rms(깊은 널에서 5~9 dB 깨짐)도 함께 기록.
- 사용자 상시 지시("모노/바이/멀티스태틱 일반형 필수")와 직결되는 항목이다.

### 3.5 절대값 민감도

σ 통짜 −3/0/+3 dB → R 재계산, **기종 순서·모드 순서가 유지되는지** 확인해 `sensitivity.sigma_shift.rank_preserved` 에 기록. 근거: 격자 불확실성 ±1.5 dB(jitter=2 로 ~0.2 dB 억제), few-λ 공진영역 PO 낙관 가능성.

---

## 4. 그림 목록 (16개)

전부 `outputs/figures/report13_*.png`, `viz_report2._save(fig, name, caption)` 규약(dpi 130, tight, 흰 배경, 회색 supxlabel 캡션). **그림 안 텍스트는 전부 영어**, 캡션은 한국어. 모든 캡션에 (a) which SNR, (b) 어느 거리축(d/R2/R_b), (c) 어느 기준채널 모델, (d) EIRP·T_CPI 를 반복 표기.

| # | 파일 / 제목(영문) | 축 | 무엇을 말하는가 | JSON 키 |
|---|---|---|---|---|
| **F1** | `report13_geometry` — "Passive bistatic geometry in free space — three ranges, one measurement" | x,y [m] 평면 + z 삽입 | R1/R2/R_b/β, iso-R_b 타원 + 등감도 Cassini oval 중첩. 챔버 이탈 선언 | `geometry.*` |
| **F2** | `report13_budget_waterfall` — "SNR budget at d = 1 km (bandwidth term is absent)" | x=예산 항목, y=누적 dB, 9모드 | 어느 항이 거리를 지배하나. **B 항이 없음을 눈으로** | `range.cells[*].budget_terms_db` |
| **F3** | `report13_range_bars` — "Free-space detection range, Pd 0.9 @ Pfa 1e-4 (5 airframes × always-on trio)" | y=5기종, x=R90 [m] | **헤드라인.** 막대=`R90_C50`, 오차막대=[C10,C90], 패널 중앙에 **메쉬 실루엣 인셋**(재질색) | `ranges[drone][mode]` |
| **F4** | `report13_coverage_curves` — "Detection coverage C(d) — fraction of headings with Pd ≥ 0.9" | x=d [m,log], y=0~1, 5드론 5색 × 3모드 패널 | 단일 거리 대신 커버리지. C=0.8 마커 | `curves.coverage_C_of_d` |
| **F5** | `report13_sigma_grid_5` — "RCS σ(az, el ≤ 0) — 5 airframes @3.5 GHz" | 5패널 **직교 히트맵** (x=az, y=el [deg], color=dBsm, turbo DR 25 dB) | σ 는 (방위, 앙각)의 함수. **극좌표 아님** — 같은 리포트 안에서 극좌표 반경 의미 충돌을 피한다 | `sigma.grid` |
| **F6** | `report13_sigma_to_range` — "From an RCS distribution to a range distribution" | 상 σ CDF, 하 R90 CDF + Swerling-1 QQ 삽입 | σ 10~17 dB 폭 → 거리 1.7~2.7배. σ^(1/4) 매핑 화살표 | `sigma.stats`, `sigma.swerling_fit` |
| **F7** | `report13_heading_footprint` — "Range vs target heading — aspect and Doppler act on the same axis" | 극좌표 θ=헤딩 ψ, r=R90 [m], 5드론 | σ 자세 + 0-도플러 블라인드가 **한 축에서** 동시에 작동, 블라인드 섹터 r=0 함몰 | `coverage.polar` |
| **F8** | `report13_eirp_ladder` — "Range scales as the fourth root of illuminator power" | x=EIRP 20~90 dBm, y=R [m] log-log | 열잡음 곡선(기울기 1/4) + ADC 곡선(EIRP 무관, 조건별 4선) + 교차점. 12 dBm 챔버 등가 마커 | `sensitivity.eirp` |
| **F9** | `report13_elevation` — "Looking up at the belly — σ vs (negative) bisector elevation" | x=el 0…−60°, y=σ[dBsm] & R90 [m], 보조축=고도 60 m 기준 d | **부호 반전 서사.** 근거리일수록 배를 크게 본다 | `sigma.stats`, `range.cells` |
| **F10** | `report13_cpi_walk` — "Longer CPI buys R ∝ T^(1/4) — until the target walks out of the cell" | x=T_CPI [s,log], y=R90 [m] | T^(1/4) + 파형별 walk 벽(수직 파선), 벽 오른쪽 빨간 해칭 | `sensitivity.cpi`, `walk` |
| **F11** | `report13_two_walls` — "Which wall binds? thermal / ADC / ECA-numeric, by band and baseline" | x=베이스라인 L [m,log], y=R [m], 밴드 3패널 | **조건부 결론.** DR{74,68,64}×supp{0,20,30} 밴드로 표시, binding 라벨 색 | `dynamic_range`, `sensitivity.baseline` |
| **F12** | `report13_matrix` — "R90 matrix — 5 airframes × 9 modes (equal-EIRP | deployment-EIRP)" | 2패널 히트맵, 셀에 [m] | 등전력(파형 효과 분리) ↔ 배치현실. WiFi 가 배치현실에서 무너지는 것을 정직하게 | `ranges[*][*].equal/.deploy` |
| **F13** | `report13_detector` — "Measured Pd(SNR) in the free-space detector + empirical Pfa" | (a) Pd 곡선 9모드 + Wilson CI + Marcum-Q 점선 (b) 경험 Pfa vs 명목 (c) 두 형상(S-G/S-W) 비교 | 문턱을 **가정하지 않고 측정**했다. Pd 0.9 수평선 | `detector_transfer.*` |
| **F14** | `report13_verify` — "Verification — closed form vs measured pipeline, ECA numerical floor" | (a) k_mode 잔차 산점 (b) ECA 잔류 vs DNR × ridge (c) 이등분선 vs 멀티스태틱 Δσ(β) | 숫자를 믿어도 되는 이유와 그 경계 | `verify.*` |
| **F15** | `report13_resolution_vs_range` — "Bandwidth buys location, not detection" | x=ΔR_b=c/B [m], y=R90 [m], 9모드 점 | report05 결론의 자유공간판 | `waveforms[*].d_rb_m`, `ranges` |
| **F16** | `report13_chamber_vs_freespace` — "Where reports 01–12 sit on this axis" | R_b 단일 로그축 | 챔버 관측창(≈22 m) ↔ 자유공간 R90(수백 m~km). **이 편이 13편 중 어디에 서 있나** | `meta.chamber_reference`, `ranges` |

(부수: 기존 `outputs/figures/drone_size_compare.png` 를 §2 에 재인용 — 재생성 불필요)

---

## 5. 렌더 · GIF 목록 (RT GIF 3 + 기종별 RT GIF 5 + matplotlib GIF 4, 스틸 22장)

**렌더 규약**: `scene_build.build_scene(드론 parts만)` / `render_rt.make_scene(with_chamber=False)`, `clip=None`, **`render_rt.CAMS` 사용 금지**(챔버 하드코딩), 드론 프레이밍 `span·r=span×1.12·fov=35°`. PNG 는 `viz_report1._whiten()`, GIF 는 프레임마다 흰 합성 후 조립(신규 `_gif_white()`; **`render_rt.make_gif` 는 수정 금지**). 프레임 디렉토리는 `render_anim._framedir()` 로 **반드시 먼저 비운다**. `gpu.pick()` 은 mitsuba import 전에.

> ★**자유공간 렌더의 근본 문제**: 진공에는 바닥·벽이 없어 **시차(parallax) 단서가 0** 이다. 카메라가 표적을 따라가면 프레임이 전부 같아 보이고, 고정 광각이면 km 거리에서 표적이 1픽셀 미만이 된다. → **모든 RT 프레임에 (a) 1 m 스케일바 또는 기준판, (b) 스케일 브레이크가 있는 장면은 프레임 안에 영문 "scale break" 표기**를 공통 오버레이로 강제한다. physics-first 의 `flyout_pd`(100 m→2 km 트래킹)와 story-first 의 `range_flythrough`(5→200 m) 는 이 대책 없이는 성립하지 않으므로 **R4 의 스케일줌 형태로 대체**한다.

**해상도 상한(검증된 범위 밖으로 나가지 않는다)**: ≤1920×1280 @ spp 512, ≤1600×1200 @ spp 1536. 2560×1600×spp4096 은 OOM 이력이 있다. GIF 편당 용량은 기존 최대(orbit_chamber 8.2 MB) 이하 유지.

| # | 이름 | 장면 / 카메라 | 프레임·해상도·spp | 보여주는 것 |
|---|---|---|---|---|
| **R1** | `r13_five_lineup_orbit.gif` | **전 기종을 같은 축척으로 1열**(간격=각 span×1.4), 궤도 카메라 r=전체span×1.3, fov 40°, 1 m 스케일바 | 48f · 1600×900 · spp 512 · ms 90 | 전 기종 메쉬 동시 + 재질색 + **실제 크기 대비**(기종별 GIF 로는 절대 못 보여주는 정보) |
| **R2** | `r13_aspect_<key>.gif` **×기종수** | 좌: RT — 드론 yaw 0→360° 회전(프롭 위상 포함), 시선 고정(el=el_look, 음수). 우: σ(ψ) 극좌표 다이얼 + **R90(ψ) 지침 + 블라인드 섹터 음영** | 기종당 24f · 좌 900×900 spp 256 · fps 10 | **전 기종 메쉬 각각 전용.** "자세가 바뀌면 검지거리가 숨쉰다"를 기종 수만큼 반복 학습 |
| **R3** | `r13_geometry_orbit.gif` | 자유공간 바이스태틱 기하 — TX 마스트/RX/표적, L=500 m, 바닥·벽 없음, 1 m 기준판 + 스케일바 | 48f · 1600×1100 · spp 512 · ms 90 | 챔버가 사라진 순간 |
| **R4** | `r13_scale_zoom.gif` | "powers of ten": 20 km 평면(Cassini) → 500 m 베이스라인 → 60 m 고도 → 1 m 메쉬. 마지막 8프레임만 RT. **매 프레임 스케일바 + 프레임 내 영문 "scale break"** | 40f · fps 6 (RT 8f · 1280×860 spp 256) | 렌더 스케일 문제를 숨기지 않고 정면으로 |
| **R5** | `r13_coverage_grow.gif` | matplotlib — EIRP 20→90 dBm 커버리지 등고선 성장, 벽에 닿으면 정지 + 조건 배지("ADC-limited @DR 64, supp 0") | 32f · 1200×900 · fps 5 | F8/F11 의 동영상판. **배지에 조건을 반드시 적는다** |
| **R6** | `r13_rd_recede.gif` | matplotlib — 실제 MC 트라이얼의 RD 맵(turbo, DR 45 dB)을 d=200 m→5 km, CFAR 히트 소멸 | 30f · 1100×700 · fps 8 | 검출이 실패하는 장면 그 자체 |
| **R7** | `r13_cpi_walk.gif` | matplotlib — T_CPI 56 ms→1 s, 피크가 솟다가 walk 벽에서 **거리축으로 번짐** | 24f · 1100×700 · fps 5 | "적분 늘리면 된다"가 왜 틀리는가 |
| **R8** | `r13_cassini_baseline.gif` | matplotlib — L 50→3000 m 스윕, 등감도 Cassini 변형(단일→이엽) + β>90° 해칭 | 36f · 1100×900 · fps 8 | 기하가 커버리지 모양을 접는다 |

**스틸 3·N + 7 장** (N = `len(DRONES)`; `outputs/renders/r13_*.png`, 1600×1200 @ spp 1536)
- `r13_10_<drone>_aspect_{best,median,worst}.png` — **3·N 장**. 자세각은 손으로 고르지 않고 **σ 격자 JSON 의 p90/p50/p10 az 를 읽어** 결정(F3·F6 삽입도로 재사용)
- `r13_20_five_row.png` — 전 기종 동일 축척 갤러리 (파일명의 `five` 는 5종 시절 유래)
- `r13_30_geometry_schematic.png` — TX 마스트·RX·표적 배치 개념도(스케일 브레이크 명시)
- `r13_40_<drone>_material.png` ×3 — 재질색 클로즈업(mini5pro / matrice4e / s1000plus = σ 최소·중간·최대)
- `r13_50_belly_vs_top.png` ×2 — **같은 기체를 el=+15° 와 el=−15° 에서** (F9 서사의 시각적 근거)

**기존 자산 재사용**(재생성 금지): `outputs/renders/anim/spin_{5종}.gif`, `drone_gallery_row.gif`, `outputs/figures/drone_size_compare.png`.

---

## 6. 산출 JSON 스키마

세 파일. σ 원장이 크므로 분리한다.

### 6.1 `outputs/report13_sigma_grid.json` (σ 원장)
```jsonc
{
 "meta": {"generated":"", "engine":"sbr", "div":16, "jitter":2, "penetrate":true,
   "az_deg":[0,3,...,357], "el_deg":[0,-2,-5,-10,-15,-20,-30,-45,-60],
   "el_sign_note":"ground TX/RX + airborne target → bisector elevation is NEGATIVE (measured -0.3…-35 deg)",
   "bands":{"lte":{"fc_hz":1.843e9,"fc_samples_hz":[...3...]},"nr":{...},"wifi":{...}},
   "n_f":3, "smooth_win_deg":3.0, "mesh_fingerprint":{...},
   "lookup":"look_angles bisector, az_span 8deg / 5pt linear-m2 mean; el linear-m2 interp",
   "quote_policy":"percentiles only — nulls/peaks/min not quotable",
   "farfield":{"D_definition":"radar_scene.target_extent (bbox max)","alt_D":"diagonal",
               "d_min_m":{"s1000plus":{"wifi":63.1,"nr":42.4,"lte":22.3}, "...":{}}},
   "runtime_s":0.0,"gpus":[]},
 "grid": {"<drone>":{"<band>":{"sigma_m2":[[/*el 9*/][/*az 120*/]]}}},
 "grid_check": {"drone":"mavic4pro","band":"nr","el_deg":-15.0,
                "div_ref":[12,24],"mean_delta_db":0.0,"max_delta_db":0.0},
 "stats": {"<drone>":{"<band>":{"<el>":{"mean_dbsm":0,"p10":0,"p50":0,"p90":0,
                                        "span_p10p90_db":0,"peak_dbsm":0}}}},
 "bistatic_check": {"beta_deg":[0,15,30,45,60,75,90],
   "delta_db_mean":{"<drone>":{"<band>":[...]}},"delta_db_rms":{...},
   "reciprocity_rms_db":{...}}
}
```

### 6.2 `outputs/report13_freespace.json` (헤드라인 — 노트북이 읽는 것)
```jsonc
{
 "meta": {"report":"report13","generated":"","git_rev":"","runtime_s":0.0,"gpus":[],
  "K":4000,"K_pfa":20000,"sigma_file":"outputs/report13_sigma_grid.json",
  "assumption_ladder":["FS0_noise_only","FS1_dpi_eca","FS2_dpi_eca_adc"],
  "headline_stage":"FS1",
  "assumptions":{"ground":false,"walls":false,"clutter":false,"multipath":false,
    "atmospheric_loss":false,"antenna_pattern":false,"fluctuation":false,
    "direct_path":true,"eca":true,
    "atmos_db_per_km":0.01,"radio_horizon_km":54.0},
  "link_budget":{"rx_gain_dbi":10.0,"noise_figure_db":5.0,"sys_loss_db":0.0,
    "eirp_equal_dbm":63.0,"eirp_deploy_dbm":{"wifi":30,"lte":63,"nr":65},
    "eirp_ladder_dbm":[20,30,40,50,60,63,70,80,90],
    "provenance":"eirp / rx_gain / noise_figure / mast height / target altitude are DECLARED — no source document in this repository (docs/EIRP_CLASSES.md TODO)"},
  "geometry":{"TX":[0,0,25],"RX":["L",0,3],"alt_m":[60,120],"baseline_m":[100,500,2000],
    "baseline_ref_m":500,"speed_ms":[5,15],"heading_deg":[0,1,...,359],
    "phi_deg":[0,5,...,355],"d_grid_m":[100,...,20000],"beta_valid_max_deg":90.0},
  "reference_model":{"canonical":"full_waveform_capture",
    "secondary":"pilot_only","pilot_power_frac_db":{"wifi":-24.106,"lte":-5.804,"nr":-5.487}},
  "cpi":{"model":"frame_len (path A) — WiFi packet padded to 1 ms slot, duty 5.2%",
    "prf_hz":{"wifi":1000,"lte":1000,"nr":2000},
    "wifi_duty_vs_report12_db":3.30,
    "T_cpi_s":[0.056,0.1,0.2,0.5,1.0],"T_cpi_ref_s":0.1,"M_by_mode":{}},
  "detector":{"shapes":{"S_G":{"n_range":64,"n_taps":128,"gate":"truth Rb centered"},
                        "S_W":{"n_range":{"nr":2460,"lte":615,"wifi":1600},"n_taps":128}},
    "cfar":{"guard":[2,2],"train":[6,6],"n_train":264},
    "doppler_guard_width":3,"training_exclusion":"submap CFAR (implemented here; the
      also_exclude_from_training flag of passive_process.doppler_guard_mask is detection-only)",
    "eca":{"ridge_rel":1e-6,"n_taps":128,
           "eca_numerical_floor":{"dnr_db":[40,...,140],"ridge":[1e-4,1e-6,0],
                                  "resid_p99_over_noise_db":[[...]]},
           "measured_full_cpi_depth_db":{"1e-4":{"wifi":-79.5,"lte":-69.0,"nr_G1":-50.3,"nr_G3":-74.3},
                                         "0":{"wifi":-136.9,"lte":-135.8,"nr_G1":-134.9}}},
    "pfa_cell":1e-4,"pfa_operational":1e-7,
    "pfa_calibration_fs":{"<shape>":{"<mode>":{"nominal":0,"empirical":0}}},
    "pfa_calibration_chamber_ref":{"wifi":6.79e-5,"lte":3.28e-5,"nr":6.30e-5},
    "false_alarms_per_cpi":{"<shape>":{"<mode>":0.0}},
    "snr_convention":"peak^2 / MEAN noise-cell power",
    "snr_median_offset_db":1.594,
    "losses_db":{"hann":{"wifi":-1.898,"lte":-1.730,"nr":-1.814},
                 "straddle_rng_half":{"wifi":-3.482,"lte":-1.241,"nr":-2.292},
                 "straddle_dopp_half":{"wifi":-1.364,"lte":-1.397,"nr":-1.371},
                 "cfar":-0.076}},
  "chamber_reference":{"Rb_max_m":22.0,"eirp_dbm":12.0,"snr50_report12_median_db":15.09,
                       "snr50_report12_mean_db":13.50,
                       "snr90_minus_snr50_db":{"W1":2.88,"L1":2.45,"G1":2.76}}},

 "waveforms": {"<mode>":{"std":"","occ":"","always_on":true,"ref_name":"","fc_hz":0,"lam_m":0,
   "bw_hz":0,"ref_bw_hz":0,"fs_hz":0,"M":0,"Lf":0,"Ns":0,"T_cpi_s":0,"prf_hz":0,"dfd_hz":0,
   "d_rb_m":0,"v_min_ms":0,"f_guard_hz":0,"blind_heading_frac":0,"eta_ref_db":0}},

 "calib": {"<mode>":{"k_db":0,"closed_form_pred_db":0,"resid_db":0,
                     "k_sigma_invariance_db":0}},

 "detector_transfer": {"<shape>":{"<mode>":{"N":{"1":{
   "snr_grid_db":[],"Pd":[],"wilson_lo":[],"wilson_hi":[],"Pfa_emp":[],
   "snr50_db":0,"snr90_db":0,"snr90_lo_db":0,"snr90_hi_db":0,
   "marcum_snr90_db":0,"marcum_dev_db":0,
   "sionna_kernel":{"max_delay_spread_s":0,"taps":0,"corr_vs_analytic":0},
   "M_scaling_dev_db":0}}}}},

 "ranges": {"<drone>":{"<mode>":{"<eirp_view>":{"<ref_model>":{"by_N":{"1":{
   "R90_C50_m":0,"R90_C10_m":0,"R90_C90_m":0,"R50_C50_m":0,"R10_C50_m":0,
   "R_C80_m":0,"R90_C50_pfa1e7_m":0,
   "R2_at_R90_m":0,"Rb_at_R90_m":0,"kappa_at_R90":0,"beta_at_R90_deg":0,
   "el_look_at_R90_deg":0,"sigma_at_R90_dbsm":{"p10":0,"p50":0,"p90":0},
   "dnr_at_R90_db":0,"snr_at_R90_db":0,
   "R_thermal_m":0,"R_adc_m":0,"R_eca_numeric_m":0,"R_total_m":0,
   "limit":"thermal|adc|eca_numeric|walk|farfield|beta",
   "blind_heading_frac":0,"farfield_ok":true,"beta_ok":true,
   "budget_terms_db":{"eirp":0,"grx":0,"lambda2":0,"sigma":0,"spread":0,"n0":0,
                      "eta_ref":0,"t_cpi":0,"losses":0},
   "R90_ci95_m":[0,0]}}}}}},

 "curves": {"snr_vs_d":{"<mode>":{"<drone>":{"d_m":[],"snr_thermal_db":[],"snr_total_db":[]}}},
            "coverage_C_of_d":{"<drone>":{"<mode>":{"d_m":[],"C":[]}}},
            "rb_ellipses":{"rb_m":[],"xy":[]},"cassini":{"kappa":[],"xy":[]}},

 "coverage": {"map":{"<L>":{"x_m":[],"y_m":[],"beta_deg":[[]],"beta_masked":[[]],
                            "pd":{"<drone>":{"<mode>":[[]]}}}},
   "polar":{"<drone>":{"<mode>":{"psi_deg":[],"R90_m":[],"blind":[]}}},
   "blind_sectors":{"<mode>":{"psi_lo_deg":[],"psi_hi_deg":[]}}},

 "walk": {"<mode>":{"d_rb_m":0,"T_max_s":{"5":0,"15":0},"T_cpi_used_s":0,"ok":true,
                    "doppler_walk_T_max_s":0}},

 "dynamic_range": {"adc_bits":[12,14,16,null],"dr_db":{"12":74.0},
   "papr_backoff_db":[0,6,10],"dpi_supp_db":[0,20,30],
   "n0_quant_minus_thermal_db":{"<band>":{"<L>":{"<eirp>":{"<dr>":{"<supp>":0}}}}},
   "crossover_eirp_dbm":{"<band>":{"<L>":0}},
   "eca_depth_required_db":{"<band>":{"<L>":0}},
   "fs2_measured_pd_drop_db":{"<mode>":0}},

 "sensitivity": {"eirp":{},"cpi":{},"baseline":{},"nrx":{},"dpi_supp":{},"adc_bits":{},
   "sigma_shift":{"delta_db":[-3,0,3],"R90_m":{},"rank_preserved":true},
   "nf_db":[3,5,7],"rx_gain_dbi":[6,10,14],"pfa":[1e-3,1e-4,1e-7]},

 "prior_compare": [{"source":"","range_m":0,"range_kind":"","illuminator":"","tx_power_w":null,
   "eirp_dbm_est":null,"cpi_s":null,"target":"","ground_included":true,"note":"","url":""}],

 "figures": [], "gifs": [], "stills": []
}
```

### 6.3 `outputs/verify_freespace.json` (`benchmark/verify_freespace.py` 산출)
```jsonc
{"closed_form_vs_measured":{"rows":[],"max_dev_db":0},
 "k_sigma_invariance":{"rows":[],"max_dev_db":0},
 "eca_floor_sweep":{"dnr_db":[],"ridge":[],"n_taps":[],"resid_med_db":[[]],"resid_p99_db":[[]]},
 "pfa_emp_vs_nominal":{"<shape>":{"<mode>":{"nominal":0,"empirical":0,"ratio":0}}},
 "false_alarms_per_cpi":{},
 "shape_compare":{"S_G_vs_S_W":{"<mode>":{"snr90_dev_db":0,"pfa_ratio":0}}},
 "sigma_convention_delta_db":{"report12_style":0,"look_angles":0,"delta":0},
 "sigma_el_sign":{"drone":"","el_plus15_dbsm":0,"el_minus15_dbsm":0,"delta_db":0},
 "bisector_vs_multistatic":{"beta_deg":[],"delta_db_mean":{},"delta_db_rms":{},"valid_beta_max_deg":90},
 "sionna_vs_analytic":{"<mode>":{"max_delay_spread_s":0,"taps":0,"corr":0}},
 "M_scaling":{"M":[28,56,112],"dev_db":{}},
 "chamber_reproduce":{"note":"챔버 기하·EIRP 12 dBm 로 되돌려 report05/12 재현","max_dev_db":0},
 "cfar_gpu_vs_numpy":{"det_match":true,"rd_rel_err":0},
 "linkbudget_two_path_max_dev_db":0}
```

---

## 7. 파일 분할

**새로 만든다** — 기존 파일은 하나도 고치지 않는다(report01~12 재현성 보호).

| 새 파일 | 책임 | 절대 안 하는 것 |
|---|---|---|
| `src/freespace_scene.py` | 자유공간 상수(FS_TX/FS_RX/FS_ALT/FS_SPEED/L 목록)·`fs_params(tx,rx,tgt,vel,fc)`(부호규약은 `bistatic_params` 복제)·`target_pos(d,φ)`·`heading_velocity(ψ)`·`doppler_guard_hz(T)`·`blind_sector()`·`beta_gate()`·`farfield_gate()`. 순수 함수, I/O 없음 | `bistatic_scene`/`geometry` 의 **챔버 상수 import 금지** |
| `src/freespace_link.py` | 닫힌형 계층: `n0_thermal()`·`n0_quant(P_dir,DR,supp,fs)`·`snr_rd_db(..., k_mode)`·`solve_range()`(log 이분법)·`dnr_db()`·`coverage_fraction()`·`cassini_contour()` | 레이더 방정식 재구현 금지 — `benchmark/link_budget` 을 호출 |
| `src/freespace_detect.py` | 자유공간 검출기 형상: `fs_shapes(wf, Rb_span)`(S-G/S-W)·`_cfar_excl_rows()`(가드행 제거 부분맵 CFAR)·`calibrate_pfa()`·`eca_floor_sweep()` | CFAR/RD 커널 재구현 금지 — `passive_process`/`detection_gpu` 그대로 |
| `src/experiment_freespace_sigma.py` | σ 격자(az 120 × el 9(음수) × fc 3 × band 3 × drone 5) + 멀티스태틱 대조 → `report13_sigma_grid.json`. **`channel.sbr_sigma_prefill` 재사용**, 기종별 증분 저장(재시작 가능) | `rcs_sbr()`(다중반사) 사용 금지, 새 GPU 워커 작성 금지 |
| `src/experiment_freespace_range.py` | `--stage=threshold\|calib\|solve\|verify\|all`. ① 두 형상 Pd(SNR) MC + 경험 Pfa ② k_mode 교정 ③ 닫힌형 전파·R 역해·커버리지·감도 ④ 스팟체크 → `report13_freespace.json` | `src/experiment_detection.py` **수정 금지** — 필요한 것은 import 하고, 모듈 전역(`N_RANGE`/`N_TAPS`/`DPI_AMP`)은 **인스턴스 생성 전에 속성을 갈아끼운다**(DPI_AMP 는 반드시 기하에서 유도한 DNR 로) |
| `benchmark/verify_freespace.py` | 독립 검산 전부 → `verify_freespace.json` | — |
| `src/viz_report13.py` | F1~F16 + matplotlib GIF R5~R8. `vizstyle.use_korean()`, `_save(fig,name,caption)` | 물리 계산 금지 — JSON 만 읽는다 |
| `src/render_report13.py` | RT GIF R1~R4 + 스틸 22장. 신규 `_gif_white()`·`_scalebar()` 오버레이 | `render_rt.CAMS`·`render_rt.make_gif` 수정 금지, 챔버 씬 금지 |
| `src/make_notebook13.py` | `report13.ipynb` 생성. `provenance_cells(report="report13", spine=..., caveats=...)` + 전 수치 f-string 주입 | **숫자 손으로 적기 금지** |

**provenance 인자**: `engines=["sbr","sionna-phy","sionna-render","radar-dsp","matplotlib"]` — ★`ENGINE_DESC` 에 없는 태그(`"torch-gpu"` 등)는 조용히 누락된다(report12 가 밟은 함정). 필요하면 `ENGINE_DESC` 에 먼저 등록.

**문서 수정(별도 승인 필요, 이번 작업 범위 밖)**: `README.md`(12편→13편, "모든 실험은 챔버 안" 인용블록에 **예외 한 줄**, 표에 report13 행, 빌드 루프 `01..13`, 파이프라인·트리), `docs/REPORT_CODE_MAP.md`(`01~13`, 지도 표 13행, 새 모듈·새 JSON 3개 등재 — 고아 json 오탐 방지), `docs/EIRP_CLASSES.md` 신설.

**실행 순서**
```bash
cd /workspace/sionna
PY="PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python"
$PY src/experiment_freespace_sigma.py            # GPU 3~4장, ~1.5 h → report13_sigma_grid.json
$PY src/experiment_freespace_range.py --stage=all # GPU 1~2장, ~2~3 h → report13_freespace.json
$PY benchmark/verify_freespace.py                 # GPU 1장, ~30 min → verify_freespace.json
$PY src/viz_report13.py && $PY src/render_report13.py
$PY src/make_notebook13.py                        # → report13.ipynb
```

---

## 8. 정직성 한계 — 말할 수 없는 것

`caveats=[...]` 와 본문 `> ⚠️` 양쪽에 그대로 들어간다.

1. **"우리 시스템의 실제 검지거리는 N m 다"라고 말할 수 없다.** EIRP·G_rx(10 dBi)·NF(5 dB)·마스트 높이(25 m)·수신기 높이(3 m)·표적 고도·속도가 **전부 선언값**이고 저장소에 근거 문서가 없다(코드 주석이 유일한 출처). 결과는 "선언한 예산 아래의 거리"다.
2. **이 리포트만 자유공간이다 — report01~12(챔버)의 상한선이지 실외 예측이 아니다.** 실제 실외는 지면반사(report09 의 바닥유령이 여기선 정의상 없다)·다중경로·클러터·간섭으로 **이보다 나쁘다**. 얼마나 나쁜지는 이 설계로 **모른다**.
3. **낙관 방향이 4중으로 쌓여 있다**: (a) 무클러터·무지면, (b) 기준채널 = 무잡음 full-waveform capture(현실 패시브는 2채널 CAF), (c) 비요동 표적(문헌은 median σ 사용 시 5~8 dB 요동손실을 더 보라고 한다 — 우리는 **미포함**이고 Swerling-1 오버레이로만 나란히 제시), (d) SBR+PO 는 few-λ 부품에서 σ 를 **밝게** 잡는 경향. → **report13 의 모든 거리는 상한선(upper bound)이다.**
4. **σ 절대값은 ±수 dB 앵커다.** 격자 불확실성 ±1.5 dB(jitter=2 로 ~0.2 dB 억제), 편파 없음(스칼라 |Γ|), 에지회절(PTD)·크리핑파 없음. **Mavic 4 Pro·Matrice 4E 의 실측 RCS 는 문헌에 없다.** σ±3 dB 민감도를 함께 낸다.
5. **널 깊이·σ_min·aspect-peak 인용 금지.** 백분위(p10/p50/p90)와 커버리지만 쓴다.
6. **바이스태틱 σ 는 β ≲ 90° 에서만 유효**(전방산란 σ≡0, Babinet 로브 못 냄). 근거리·큰 베이스라인 조합(★L=500 m·d=150 m → β 115.8°)이 여기 걸린다 — 해칭하고 수치를 인용하지 않는다. 실제 패시브 레이더가 그 영역에서 오히려 유리할 수 있다는 점도 한 줄 인정한다. 상반성은 깊은 널에서 rms 5~9 dB 깨진다.
7. **ECA 는 무한 이상화가 아니다 — 방향이 반대다.** ★측정: `ridge_rel=1e-4`(report12 값)에서 제거깊이는 NR/SSB −50.3 dB 로 **유한**하고, DNR ≳ 100 dB 에서 비-0도플러 셀로 샌다(p99 +5.9 dB @100 dB, +24.2 dB @120 dB). report13 은 `ridge_rel=1e-6`·`n_taps=128` 로 이 아티팩트를 제거했고(≤+0.1 dB @DNR 120), 그 결과 우리 ECA 는 **사실상 이상적**이다. **진짜 낙관은 여기다**: 실장 ECA·아날로그 소거의 유한 제거깊이(통상 40~90 dB)·위상잡음·상호변조는 모델에 없다. `eca_depth_required_db`(최대 130 dB 급)는 **요구량이지 달성치가 아니다.**
8. **ADC 모델은 1차 근사다.** 균일 양자화 + 백색 양자화잡음. AGC 동작·SFDR·상호변조·수신단 NF 와의 상호작용은 미모델. PAPR 백오프는 **선택한 값**이지 측정값이 아니라서 0/6/10 dB 를 스윕했고, DPI 억압 0/20/30 dB 도 함께 스윕했다 — **"12-bit 가 벽이다"라는 단정을 하지 않는 이유가 이것이다**(★L=500 m·EIRP 63 dBm 에서 LTE 는 백오프 10 dB·억압 0 이면 양자화 지배(+11.4 dB), 백오프 0 이면 거의 대등(+1.4), 억압 20 dB 면 열잡음 지배(−18.6)).
9. **검출기 형상 두 가지를 냈고 성격이 다르다.** S-G(게이트)는 표적 R_b 를 아는 검출기라 "탐색 없이 얻은 거리"이고, S-W(전체 창)는 탐색하지만 CPI 당 오경보가 수십 건이다. 헤드라인은 S-G 이고 S-W 의 경험 Pfa·오경보 수를 반드시 병기한다.
10. **다중 Rx 의 N^(1/4) 이득은 이상적 상한**(완전 코히런트 결합·완벽 조향·무상관 잡음·무상호결합). report12 와 같은 유보 유지.
11. **"기준 안테나 = full-waveform capture"** 를 정본으로 썼다 — 패시브인데 상시신호만은 아니라는 유보를 승계한다. pilot-only 열을 병기했고 WiFi 에서 그 차이는 ★24.1 dB(거리 4배)다.
12. **CAF(레퍼런스×서베일런스 2채널) 승격은 하지 않았다.** 이상적 레퍼런스 정합필터 SNR 이다(report12 와 동일한 열린 과제).
13. **문헌 실적치와 우열을 비교하지 않는다.** 조명원 전력·CPI·표적·지면 포함 여부가 다르다. F14 아닌 `prior_compare` 표에 **조건열을 강제**하고 나란히 놓기만 한다.
14. **호버링 드론은 거리와 무관하게 못 본다.** `|v_r| < 2.5λ/(2·T_CPI)` 면 0-도플러 능선에 묻힌다. report05 hover-blind 는 자유공간에서도 유효.
15. **자세는 수평(roll=pitch=0)·yaw 만** 변화로 단순화했다. 실제 전진비행은 pitch 10~30° 로 기울고 σ(el) 스윙이 큰 것을 감안하면 무시할 수 없는 단순화다 — **모른다고 쓴다.**
16. **앙각 격자 보간**: el ≤ −45° 구간은 β>90° 게이트와 겹쳐 표본이 적고 보간 신뢰도가 낮다. `el > 0`(공중 조명원/수신기) 은 이 리포트 범위 밖이다.
17. **원거리장**: ★`radar_scene.farfield_distance(target_extent)` 기준 s1000plus @5.21 GHz 63.1 m 가 최악. D 를 대각으로 잡으면 값이 2배가 되므로 **어느 D 정의를 썼는지 JSON 에 명기**했다. 그 아래 구간의 σ 는 인용하지 않는다(그림에 세로 점선 + 회색).
18. **"5기종 × 9모드를 한 규약으로 낸 선행 사례를 확인하지 못했다"** 까지만 쓴다 — 부재의 증명이 아니고, "최초"라고 쓰지 않는다.
19. **단일 CPI·단일 표적.** 스캔 누적·M-of-N·트래킹 없음(트래킹은 future work 한 줄). 다중표적·상호 그림자 없음.
20. **대기감쇠·전파수평선은 숫자와 함께 무시했다**: 1.8~5.2 GHz 산소흡수 ≈0.01 dB/km → 5 km 왕복 <0.1 dB, RX 3 m + 표적 60 m 의 전파수평선 ≈ 39 km ≫ 그리드 최대 20 km. **"무시했다"가 아니라 "이만큼이라 무시했다"로 쓴다.**

---

## 부록 A — 심사가 지적한 치명적 결함 전수 해소 대장

| # | 결함 (출처) | 해소 |
|---|---|---|
| A1 | **el 이 독립 스윕축** → el 60°·R 2 km 같은 불가능한 셀 (physics-first, 방어/명료) | el 을 폐기하고 `el = look_angles(u1,u2)` 로 기하에서 유도(§3.1-2). range.cells 에 `el_look_at_R90_deg` 만 기록 |
| A2 | **el 부호 반전** — 세 안 모두 양수 격자 (feasibility) | ★측정으로 확정(전 구간 음수, −0.26…−35.2°). 격자를 9점 음수로, "overhead spike" 서사 삭제·"배를 본다"로 반전(§3.1). ★σ 차이 +3.2~+5.8 dB 검증 스모크를 `verify.sigma_el_sign` 에 정식 기록 |
| A3 | **el=0 고정이 저EIRP·근거리에서 깨짐** (story-first) | 위와 동일 — el 을 2D 격자 + 기하유도로 대체 |
| A4 | **n_range ≫ n_taps → 경험 Pfa 폭발** (physics-first, visual-first) | 두 형상 병행(§1.5). S-G 는 n_taps 128 ≥ n_range 64 로 [R3] 자체를 성립시키지 않고, S-W 는 경험 Pfa 를 **측정해서** 보고. 폴백(창 축소)을 선언하고 실패해도 JSON 에 남긴다 |
| A5 | **`also_exclude_from_training` 는 동작하지 않는 인자** (방어/명료/타당성) | ★코드 확인(`passive_process.py:295`). 가드행 제거 부분맵에 `ca_cfar_2d` 적용하는 `_cfar_excl_rows()` 를 직접 구현 |
| A6 | **가드행 중앙값 치환은 훈련평균을 1.59 dB 낮춘다** (visual-first) | 치환 방식 폐기, A5 로 대체 |
| A7 | **오경보 회계 없음**(전체 창인데 셀당 Pfa 만) (physics-first) | S-W 에서 **CPI 당 기대 오경보 수** 보고 + Pfa 1e-7 병기(거리 ×0.87) (§2.4) |
| A8 | **SNR 축 median↔mean +1.59 dB** (physics-first 발견, story-first 미처리) | mean 규약을 정본으로 못박고 변환값을 JSON·전 캡션에 표기. 단, 실제 전파는 **k_mode 경험교정**이 흡수하고 그 사실을 JSON 에 남긴다(이중계상 방지) (§2.1, §2.5) |
| A9 | **k_mode 없음 → η 부기로 거리 2배 오차** (story-first) | k_mode 교정 + σ 불변성 어서션 채택(§2.5) |
| A10 | **WiFi 듀티 3.30 dB** (physics-first 발견) | 경로 A 듀티 채택, `meta.cpi.duty_model` 명시(§1.4-A) |
| A11 | **3.30 dB 는 절반 — 진짜 차이는 기준신호 24 dB** (feasibility) | ★`pilot_power_frac_db` 로 확인. 기준채널 모델 **두 열 병기**, 정본 명시(§1.4-B) |
| A12 | **ECA 를 무한 이상화로 오인(방향 반대)** (feasibility, 세 안 공통) | ★측정으로 확정. ridge 1e-6·n_taps 128 정본, ECA 수치바닥 사전측정·셀 라벨·caveat 부호 반전(§1.6, §8-7) |
| A13 | **ADC 헤드라인이 백오프 10 dB·억압 0 dB 에 걸림** (방어/명료) | 기본값을 저장소 값(DR 74, 백오프 0, 억압 0)으로, 백오프·억압·bits 스윕, ADC 를 감도 패널로 강등, 헤드라인 교체(§0.1, §1.7, F11) |
| A14 | **ADC 결론을 한 밴드에서 일반화** (story-first) | ★밴드별 재계산 표(§1.7). 교차점을 밴드별로 산출 |
| A15 | **β>90° 마스크가 축 전체에 안 걸림** (세 안 공통) | 유효범위 게이트를 모든 셀에 적용, `beta_ok` 라벨, 그림 해칭(§1.8) |
| A16 | **far-field 상수 불일치(131 vs 63 m)** (방어) | `radar_scene.farfield_distance(target_extent)` 로 통일하고 두 D 정의 병기(§1.8) |
| A17 | **σ div=12 로 report2(16)와 비교불가** (명료) | div=16 유지, n_f·az 로 비용 상쇄, div 12/24 교차검증(§3.2) |
| A18 | **cache_key 에 el 을 넣으라는 오진** (feasibility) | ★`_SCENE_CACHE` 키 구조 확인 — 씬은 el 무관. 저장소 규약 그대로 `(drone, fc_MHz)`, σ 값 캐시는 `_sig_key` 가 처리(§3.2) |
| A19 | **새 GPU 워커가 budget NameError 로 죽음** (feasibility) | 새 워커를 짜지 않고 `channel.sbr_sigma_prefill` 재사용(우회 내장)(§3.2) |
| A20 | **Sionna PHY 를 커널 한계로 오해해 강등** (feasibility/story-first) | ★`max_delay_spread` 는 인자 — `1.3·R_b/c` 동적 설정으로 정본 유지, 해석적 분수지연은 대조군(§1.5) |
| A21 | **드론 크기 오름차순 오기** (feasibility) | ★`anim_plots.py:439` 확인 → mini5pro, mavic4pro, **phantom4**, matrice4e, s1000plus (§1.3) |
| A22 | **σ 20 dB→3.2배 주장이 자기 인용정책 위반** (명료) | ★p10↔p90 = 9.55~17.32 dB → 1.73~2.71배로 통일(§0.1) |
| A23 | **63k 셀·수백 MB JSON, 헤드라인 부재** (명료) | 축 축소(el 자유축 제거·EIRP 관점 3개·T_CPI 5점) + `curves`/`coverage` 다운샘플 저장 + **헤드라인 문장 템플릿 고정**(§0.1) |
| A24 | **스틸 렌더 목록 없음 / 5기종 개별화 약함** (풍부성) | 스틸 22장 열거 + 기종별 RT GIF 5편(R2) + 동일축척 1열(R1) (§5) |
| A25 | **자유공간 진공에 시차 단서 0 → 검은 프레임 몇 픽셀** (풍부성) | 트래킹 flythrough 폐기, R4 스케일줌으로 대체, **모든 RT 프레임에 1 m 스케일바 + 프레임 내 "scale break" 표기** (§5) |
| A26 | **σ 벌룬을 RT 로 표기(불가능·report2 중복)** (풍부성) | 삭제. σ 는 F5 직교 히트맵 + R2 극좌표 다이얼로 |
| A27 | **극좌표 반경 의미 충돌(el vs R90)** (풍부성) | F5 를 직교 히트맵으로 변경, 극좌표는 R90 [m] 하나만(§4) |
| A28 | **R2 가 180 RT 프레임(비용 붕괴)** (풍부성) | 기종당 24프레임·900×900·spp 256 = 120 프레임으로 축소(§5) |
| A29 | **RT+matplotlib 합성 헬퍼 미명세** (풍부성) | `render_report13._gif_white()` + PIL paste 합성기를 명세(§5, §7) |
| A30 | **비용표 낙관(σ 42k 오산·MC 3배)** (feasibility) | ★실측 처리량으로 재선언(부록 B) |
| A31 | **`R90/50` 표기가 R50 과 충돌** (명료) | `R90_C50` 표기로 교체, Pd 축과 커버리지 축을 이름에서 분리(§2.3) |
| A32 | **WiFi 배치현실 답이 축·유효범위 밖** (명료/풍부성) | 축을 자르지 않고 회색 + "invalid: β>90° / near-field" 라벨로 표시(§1.4, §1.8) |
| A33 | **이등분선 근사 자체가 미검증** (방어, 세 안 공통) | `rcs_sbr_multistatic` 으로 Δσ(β) 측정(§3.4) |
| A34 | **헤딩과 방위를 독립축으로 두어 상관 상실** (방어/명료) | 헤딩 ψ = 드론 yaw = 속도방향 하나로 결합(§1.3, §3.2, F7) |
| A35 | **3층 정의 부재(불확실성 뭉개기)** (방어) | 3층 정의 채택(§2.1~2.3) |
| A36 | **DPI_AMP=40 등 챔버 전역상수 재사용 위험** (feasibility) | 인스턴스 생성 전 모듈 속성 교체 + DPI_AMP 는 기하유도 DNR 로(§7) |

---

## 부록 B — 실행 비용 (★실측 처리량 기반 재선언)

| 단계 | 규모 | 카드 | 시간 |
|---|---|---|---|
| σ 격자 | 48,600 az-eval (5×3밴드×3주파×9 el×120 az) @div=16 | ★0.17~0.25 s/az-eval(div 12) × 1.78(div 16) ≈ 0.30~0.45 s → 1장 4~6 h | **3~4장 분산 ~1.5 h** |
| 멀티스태틱 대조 | 5×3밴드×7β×24az (조명 재사용) | 1장 | ~15 min |
| 문턱 MC | 2형상 × 9모드 × N{1,4} × 25 SNR × K=4000 + Pfa K=20000 | ★1.5~2.3 ms/trial(NR 6.88M CPI, batch 16~32, peak 3.5~7 GB) | **1~2장 2~3 h** (`SIONNA2_DET_BATCH` 로 조절) |
| ECA 바닥 스윕 | DNR 11점 × ridge 3 × n_taps 3 × 3파형 | CPU | ~10 min |
| 거리 역해·감도 | 5×9×2EIRP뷰×2ref×4N×72φ×360ψ 이분법 | CPU(numpy) | ~10 min |
| 그림 16 + matplotlib GIF 4 | — | CPU | ~15 min |
| RT 스틸 22 + GIF 4(≈290 프레임) | 1600×1200@1536 / 1600×900@512 | 1장 | ~60 min |

GPU 방침: `gpu.pick()`/`parallel_over_gpus` 로 여유 2 GB↑ 카드 전부 침투, `nvidia-smi` 를 보며 `SIONNA2_DET_BATCH` 로 배치 실시간 조절(유휴 카드 메모리 90% 목표). 렌더는 개당 ~1 GB 뿐이므로 큰 배치 실험과 병행.