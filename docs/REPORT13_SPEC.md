> ⚠ **2026-07-31 재편으로 퇴역한 리포트의 설계서다** — 당시 사양을 그대로 보존한다. 현재 6편 구조는 [`../README.md`](../README.md) 와 [`REPORT_CODE_MAP.md`](REPORT_CODE_MAP.md) 에 있다.

모든 쟁점을 코드·계산으로 판정 완료했습니다. 결정적 확인: **F1**(SSB 50Hz, 저장소 자체 `PILOT_RATE_HZ`가 근거), **R6**(ridge_rel=0가 정답 — 스모크로 1e-6이 오히려 누설 확인), **F2**(equal_psd 장치 실재), **S1/S6**(비단조·국소지수·천장), **F17**(target_extent 크기순서). 이제 최종 구현 스펙을 작성합니다.

> ⚠ 2026-07-30: 표적이 7종이 됐다(비-DJI 2종 추가). **이 문서에 개수를 적지 않는다** — 정본은 `src/drones.py` 의 `DRONES` 이고 코드는 `viz_report13.DRONE_ORDER`(= `drone_order()`) 로 유도한다. 아래 렌더 파일명에 남은 `five` 는 **5종 시절 유래한 이름**일 뿐 내용은 전 기종이다.

---

# report13 최종 구현 스펙 — 자유공간 드론 검지거리 (구현자 유일 지시서)

> 이 문서는 확정 설계 + 적대적 반증 4건(REFUTE 1~4, 총 40여 항)을 **전량 판정·반영**한 최종본이다. 확정 설계와 충돌하는 곳은 **이 문서가 이긴다.** ★ = 이번 조사에서 저장소 코드/JSON/읽기전용 스모크로 직접 확인한 값. 나머지는 선언값이며 그렇게 표기한다.
> **이번 조사에서 뒤집힌 설계 결정 6개**(구현자 필독): ① ECA `ridge_rel=1e-6→0`, ② SSB 반복률 `2000Hz→50Hz`(M 물리유도), ③ 전력정규화 `equal_psd` 정본 추가, ④ solve_range `이분법→최외곽교차`, ⑤ 밴드 인용축 `d→R_eq=√(R1R2)`, ⑥ 크기순서 `target_extent` 정본.

---

## 0. 반증 판정 대장 (전 항목 수용/기각 + 근거)

### REFUTE[1] 자유공간 가정

| # | 판정 | 근거·조치 |
|---|---|---|
| R1 "상한선 거짓, 지면반사 최대 1.94배 증가" | **수용(부분)** | 물리적으로 옳다(저각 다중로브 F⁴∈[−20,+11.5]dB). §8-2/8-3의 **"상한선(upper bound)" 주장 철회**. 자유공간=**기준정규화(reference normalization)**로 재정의. 단 헤드라인은 사용자 원안대로 FS-1(순수 자유공간) 유지(사용자 지시 "반사체 없는 곳 가정"). FS-3(평면지면 2-ray)를 **닫힌형 동반 사다리**로 추가(σ격자 재사용·GPU 0회) — 헤드라인 아님, 정직성 점검용. |
| R2 "바닥유령은 미분해 페이딩으로 형태변경, 광대역은 재출현" | **수용** | FS-3 안에서 ΔR_b(지면경유) vs c/B 표로 처리. G1(SSB)·L1(CRS)=미분해 페이딩(F⁴), W/G3=근거리 분해 유령. `limit`에 `ghost_resolved` 셀 표시(FS-3 전용). |
| R3 "3m RX 프레넬 1존 비어있지 않음, fresnel 게이트" | **수용(FS-3 한정)** | 순수 FS-1에는 지면이 없어 프레넬 차폐 개념 자체가 없다. `fresnel` 게이트는 **FS-3에만** 적용(min clearance/F₁≥0.6). FS-3 그림의 x축 상한을 실질 결정. |
| R4 "지면 없다면서 지면기준 상수(마스트·수평선)" | **수용** | 높이(TX25/RX3/alt60·120)를 **배치 파라미터**로 정직하게 승격 — FS-1에서 역할=el·β 결정, FS-3에서 F⁴ 기여. `radio_horizon`·대기감쇠는 FS-1 meta에서 삭제, FS-3 meta로 이관(지구를 근거로 쓰는 항은 지면반사와 같은 사다리에만). |
| R5 "가장 큰 벽 DPI 잔류(실장 ECA 유한소거) 누락" | **수용** | `limit` enum에 **`dpi_residual`** 추가. `sensitivity.eca_depth_db=[40,60,90,inf]` **필수 스윕축**(닫힌형). 헤드라인에 "이상소거(∞) 기준 {R}, 소거 60dB 기준 {R60}" 병기. §1.6의 `eca_depth_required_db`는 요구량, 이건 달성치 스윕. |
| R6 "eca_numeric은 자초 아티팩트, ridge=0·n_taps 1~4" | **수용(★스모크 확인)** | ★직접 측정: `ridge_rel=0`은 n_taps 1~128·DNR 80~120 전조건 비-0도플러 잔류 ≈0dB. `ridge_rel=1e-6`은 오히려 DNR120 p99 **+25~26dB** 누설(설계 §1.6표 "1e-6=+0.0" 재현실패). **정본=ridge_rel=0**. `eca_numeric` 벽 강등. |
| R7 "supp를 φ 무관 스칼라로 스윕(기하 불가능)" | **수용** | `supp_eff(φ)=min(supp, supp_max(Δθ))`, Δθ=RX에서 본 TX↔표적 각분리. φ≈180°(각분리→0)는 `limit="dpi_unsuppressible"` 회색. |
| R8 "결론이 자명, 헤드라인 정직화·FS0 동일성검정" | **수용(부분)** | FS-0 9모드 SNR90 동일성 검정을 verify #1로. 헤드라인 재배치: 새 정보=σ(음의 el·Δσ(β))+기하(Cassini·비단조·천장)임을 명시. 단 R5·F1 반영 후 "벽 지도"는 물리(실장 소거깊이·물리 PRF)의 함수가 되어 비자명 결론으로 유지. |
| R9 "동일채널 간섭 INR은 반사체 무관, 감도축 승격" | **수용** | `sensitivity.inr_db=[-10,0,20,40]`(닫힌형). §8에 "이 항 하나로 거리 한자릿수 감소" 크기 명기. |

### REFUTE[2] σ→거리 사상 / R1²R2² 비선형

| # | 판정 | 근거·조치 |
|---|---|---|
| S1 "R∝σ^¼는 d축에서 거짓, 지수 0.09~4.00" | **수용(★확인)** | ★국소지수 재현: d=150·L=500 n=1.03, d=1000 n=3.76(d≫L에서만 4). 분산·밴드는 **`R_eq=√(R1R2)`축에서 인용**. dB↔배율 환산은 본문·캡션 **금지**(반드시 `n_local` 병기). `ranges`에 `n_local_at_R90`, n<3.5는 `limit`에 `geometry_nonlinear` 부라벨. |
| S2 "R90_C10 헤드라인 조건서 공집합" | **수용** | b_blind>0.10이면 C10 미정의(확인: L1 v=5m/s b_blind≈27%). 밴드를 **커버리지 천장 C_max(d)=1−b_blind 상대**로 재정의: `R90_C50`(정본)·`R90_C25`. `R90_C10`은 nullable, `coverage_ceiling` 신설. 헤드라인 템플릿에서 p10 제거, "b_blind={}%는 거리무관 미검출" 문장화(§8-14를 caveat→헤드라인). |
| S3 "블라인드 검열이 고정 자세각(±90°)과 완전상관" | **수용** | C(d)=(1−b_blind)·P_ψ[σ≥σ_th|비블라인드]로 **분해**, 두 인자 JSON 별도. `verify`에 비블라인드-조건부 vs 전체 σ의 KS거리. 캡션에 "블라인드=항상 기체 ±90° 자세 검열, 랜덤 아님". |
| S4 "Pd0.9@R90은 실제 검출확률 0.67~0.71" | **수용** | `ranges`에 **`E_psi_Pd_at_R90`**·`R_Epd90_m`(E_ψ[Pd]=0.9 거리) 필수. 헤드라인 두 숫자 병기. F4에 E_ψ[Pd](d) 곡선 겹침. |
| S5 "밴드가 파이프라인이 안 쓸 σ추정량(el+15°,1°격자)로 계산, Jensen 낙관" | **수용** | §0.1 밴드를 **파이프라인 추정량(5pt m² 평균, 음의 el)**으로 재산출. `sensitivity.az_smoothing`(az_span 0/4/8°). `meta.lookup`에 "평활은 수치장치, 하위꼬리 최대 +3.7dB". |
| S6 "SNR(d) φ의 67%서 비단조, 이분법 무효" | **수용(★확인)** | ★φ=0/10/30°서 SNR 내부최대(d=244/235/166m). `solve_range`→**최외곽 하강교차**(`np.diff(sign)` 마지막). `snr_ceiling_db`(★+24.7dB@d452)·`frac_never_detectable`·`monotone_ok`(φ별) 필수. |
| S7 "분산예산에 φ 누락, 근거리서 φ분산>σ분산" | **수용** | `meta.geometry.phi_headline_deg=90` 명시(전 캡션). `sensitivity.var_budget_db={aspect_psi,geometry_phi,altitude,drone}` @d={300,1000,3000}. 부헤드라인2 조건화: "d≳1km서 자세 지배, 그 아래 기하 지배". |
| S8 "el 부호정정 효과 헤드라인서 ~0(el≈−2°)" | **수용(부분)** | 음의 el은 유지(부호는 옳다). el격자를 **유효도메인 조밀 재배치**: `[0,−0.5,−1,−2,−3.5,−5,−8,−12,−20]`. "20~35% 과소평가"를 **"d≲400m 한정"**으로 스코프. `verify.sigma_el_sign`에 `el_at_headline_deg`. |
| S9 "Swerling 이중계상, 밴드≠오차막대" | **수용** | caveat을 "CPI **내부** 비요동"으로 축소, inter-look 요동은 `E_ψ[Pd]`로 이미 정량화됨 명시. Swerling은 KS통계만(손실 dB 인용 금지). F3: 밴드=채운 띠, CI=캡 막대 분리. |
| S10 "sigma_at_R90{p10,p50,p90} 정의 모순" | **수용** | `sigma_at_R90_C50_dbsm`(스칼라, C50 문턱 σ)+`sigma_dist_at_d_of_R90`(분포)로 분리. S3 실효백분위 함께. |

### REFUTE[3] 검출 통계

| # | 판정 | 근거·조치 |
|---|---|---|
| §0 "코히런트 적분이득·k_mode σ불변·MC측정은 저SNR서 견고" | **수용(설계 방어 확인)** | 반박 아님. §2.5 서사 유지. |
| §1 "전이곡선 도플러위치 무관 재사용, 연성블라인드 18% 미포착" | **수용** | 전이곡선을 **도플러오프셋 축**(`dopoff∈{3,5,8,15,≥30}빈`)으로 다중측정. 커버리지 적분시 헤딩별 실제 dopoff로 곡선 선택. `coverage.soft_blind_frac`. |
| §2 "Pd 정의가 전역 argmax=표적" | **수용(★확인)** | ★Precomputed.di/ri_true=argmax, hit=found&±2. 검출을 **표적근방(±2) 문턱초과**로 재정의(`det[cell근방].any()`). 전역최대는 caveat. |
| §3 "n_range≫n_taps [R3]경보 + FA 상관셀 과다계상" | **수용(부분)** | R6(ridge=0)+free-space(clutter=())로 단일탭 DPI 완전소거→[R3] Pfa폭발 완화(★스모크: n_range256서 ridge=0 잔류≈0). 단 **실제 n_range서 경험 Pfa 측정** 유지. FA는 **분해능셀 클러스터** 단위(F7과 수렴). §1.6 바닥스윕을 최대 n_range서 재실행. |
| §4 "cfar_loss −0.076은 평균문턱오프셋, Marcum 낙관편향" | **수용(★확인)** | ★`0.076=10log10(9.373/9.210)`=평균비. F13 Marcum점선은 **CA-CFAR 인지형** Pd(`(1+α/(N(1+SNR)))^−N`). −0.076을 "평균문턱오프셋"으로 재명명. 1e-7 경험Pfa는 K=20000서 검증불가 명시. |
| §5 "median↔mean 이중계상 위험" | **수용(설계 인지)** | ★`median(rd²)` 확인. k_mode 흡수. 한 셀서 두 규약 R 일치를 `verify.snr_convention_consistency`에 회귀박제. |

### REFUTE[4] 공정성

| # | 판정 | 근거·조치 |
|---|---|---|
| F1 "SSB 반복률 40배 과대(2000 vs 표준 50Hz)" | **수용(★확인, 헤드라인 전복)** | ★`waveforms.py PILOT_RATE_HZ["nr"]["PSS"]=50.0` "SSB 20ms→50Hz", 주석 "5G 이중고". CPI_CFG의 `nr:M=112,b=1`(0.5ms 타일링 2000Hz)는 report12 단순화. **M을 물리 반복률서 유도**: M=round(T_CPI·PRF). SSB PRF=50Hz→T_CPI 100ms서 M≈5. `meta.cpi.ssb_period_ms=20`. 이 결과가 프로젝트 서사(5G 이중고)와 일치. |
| F2 "점유모드 전력정규화 규약 없음(equal total vs per-RE PSD)" | **수용(★확인)** | ★`run_min_cell.power_ref_tx` 실재("per-RE 송신전력 동일→시간희소 G1 저평균전력 물리반영"). `eirp_view` 3개: `equal_total`/`equal_psd`(**점유축 정본**)/`deploy`. 배치현실 NR은 풀로드 gNB 65dBm이므로 유휴 G1에 붙이지 않음(★18.2dB 낮음). |
| F3 "F1+F2 결합→상시3인방 순위 전복" | **수용** | G1 SSB가 꼴찌로. 자기 프로젝트 핵심서사 복원. |
| F4 "CFAR guard 빈고정→NR G1만 자기가림" | **수용(부분)** | ★SSB 오버샘플 fs/B_ref=17.1, 주엽 18빈. 단 R3부록: 2D도플러가 희석(−17dB, Pd0.93 정상). **이중보고**: 고정guard(2,2)/(6,6)(리포트간 비교) + **분해능셀 등가guard**(공정성). `meta.detector.cfar.guard_bins_by_mode`. Pd는 측정이라 자기가림이 SNR90에 흡수됨 — 어느 규약인지가 쟁점. |
| F5 "검증상수 전부 G3측정치를 9모드에 적용" | **수용** | straddle·pilot_frac·η_ref를 **(std,occ) 9행** 재측정. straddle은 `fs/B_ref` 오버샘플서 유도. |
| F6 "ECA n_taps 샘플단위 128 고정→지연커버리지 4배 불균등" | **수용(R6과 통합)** | n_taps **지연스팬 등가**: `n_taps=ceil(eca_tap_span_m/(c/fs))`. `meta.detector.eca.tap_span_m`. |
| F7 "FA/CPI 빈단위→협대역 8배 과징" | **수용(★확인)** | ★분해능셀 기준 W1 15.3/L1 3.6/G1 **2.88**(빈기준 49와 정반대). FA/CPI를 **분해능셀 기준** 보고(빈=참고열). |
| F8 "도플러 나이퀴스트 상한게이트 없음" | **수용** | 3층에 `nyquist_ok=|f_d|<PRF/2`. 가드판정은 **접힌 도플러** `mod(f_d+PRF/2,PRF)−PRF/2`. SSB PRF50→전속도 앨리어싱=유휴5G 무력화(F1과 일관). `v_unambiguous` 세로선. |
| F9 "WiFi 패킷률 1kHz는 답을 정하는 자유파라미터" | **수용** | `wifi_packet_rate_hz∈{10,100,1000,5000}` 1급 감도축. `always_on` boolean **폐기**→`reference_repetition_hz`+`rate_source`. |
| F10 "밴드=표준 1:1 결속, 파형효과 미분리" | **수용** | 공통 3.5GHz **반사실**(W/L/G 구조를 같은 반송파에) + Δ거리 **5항 분해**(λ²σ/기준대역/반복률·듀티/η_ref/도플러블라인드). σ격자 이미 3밴드→GPU 0회. |
| F11 "rank_preserved 항등적 참" | **수용** | 통짜 시프트 폐기→**(드론×밴드) 독립섭동**(div12/24 교차값=셀오차, 부트스트랩). F10 방향성편향도 섭동. |
| F12 "fs를 채널대역에 묶어 ADC결론=수신기설계 산물" | **수용** | `fs`를 독립스윕 or `fs/B_ref` 오버샘플비 고정열 병기. F11캡션 "밴드별 fs선택의 결론" 명기. |
| F13 "EIRP peak/avg 선언없음" | **수용** | `meta.link_budget.eirp_definition="in-burst peak"`. duty 별도. |
| F14 "블라인드 헤딩비율 λ구동인데 파형탓" | **수용** | F10 분해에 (e) λ항. |
| F15 "σ엔진 신뢰도 (기종×밴드)마다 다름, D/λ" | **수용(★확인)** | ★mini5pro@LTE=2.32λ(최악, 헤드라인 하한칸). `meta.sigma_confidence.D_over_lambda` 격자, <3λ 셀 그림 표시. |
| F16 "다중Rx N 개구는 밴드마다 다름" | **수용** | `meta.array.aperture_m_by_band`. |
| F17 "크기 오름차순 오기, target_extent와 모순" | **수용(★확인)** | ★target_extent: mini0.378<**phantom0.471<mavic0.556**<matrice0.587<s1000 1.348. anim_plots:439는 mavic·phantom 오배치. **정본=target_extent 순**. |

---

## 1. 서사·헤드라인 (수정본)

### 1.1 헤드라인 3층 (숫자 전부 JSON 주입)

1. **주 헤드라인.** "EIRP {eirp} dBm(in-burst peak)·전력규약 {norm}·T_CPI {t} ms·Pd 0.9 @ 셀당 Pfa 1e-4·단일 CPI·이상 DPI소거(∞ dB) 기준, 자유공간(FS-1) 검지거리는 **LTE CRS(L1)** 기준 R_eq {Req:.0f} m(중점수평 d {d:.0f} m) [자세 커버리지 C25–C50: {lo:.0f}–{hi:.0f} m], 같은 지점 헤딩평균 검출확률 E_ψ[Pd]={epd:.2f}. **실장 소거 60 dB 기준 {R60:.0f} m.**"
2. **부 헤드라인 (무엇이 새로운가 — R8 정직화).** "report13이 실제로 새로 낸 것은 **σ의 음의 앙각 격자와 이등분선↔멀티스태틱 Δσ(β)**, 그리고 **기하(Cassini 등감도선·SNR 비단조성·검출 천장)**다. 검출 파이프라인은 재파라미터화이며 닫힌형과 ±0.1 dB로 맞는다."
3. **부 헤드라인 (분산이 결론).** "d≳1 km에서는 **자세**가, 그 아래에서는 **기하(φ)**가 분산을 지배한다. 파이프라인 추정량 기준 한 기종의 자세밴드 p10↔p90 = {span:.1f}~{span2:.1f} dB(거리 {r1:.2f}~{r2:.2f}배, R_eq축), 근거리 φ분산은 최대 {phivar:.1f} dB."
4. **부 헤드라인 (5G 이중고 — F1/F3 복원).** "유휴 5G SSB(G1)는 반복률 50 Hz·협대역 7.2 MHz로 **거리도 속도도 나쁘다**: v=5 m/s에서 헤딩의 {blind:.0f}%가 도플러 블라인드, 나머지도 M≈5로 코히런트 이득이 낮아 상시 3인방 중 꼴찌다."
5. **부 헤드라인 (무엇이 벽인가는 조건부).** 벽 목록 = `thermal/adc/dpi_residual/walk/farfield/beta/nonlinear`. 셀마다 `limit` 라벨. 어느 하나를 헤드라인으로 세우지 않는다.

> ⚠ 원안 "12-bit ADC가 벽"·"eca_numeric 벽" 둘 다 **채택 안 함**. 전자는 백오프·억압에 걸린 조건부(감도패널로 강등), 후자는 ★자초 아티팩트(ridge=0로 소멸). 진짜 큰 벽은 **`dpi_residual`(실장 유한소거)**다.

### 1.2 독자 여정 (§0 표) — 확정 설계 표를 계승하되 §6에 벽 목록을 `dpi_residual` 포함으로, §7에 FS-3 정직성 점검 추가.

---

## 2. 가정 사다리 FS-0/1/2/3

| 단계 | 포함 | 배제 | 무엇을 재나 | 헤드라인 |
|---|---|---|---|---|
| **FS-0** | 표적에코+열잡음 | 직접파·ECA·양자화·간섭 | 열잡음 상한. **9모드 SNR90 동일성 검정**(R8) | — |
| **FS-1** | +직접파(기하유도 DNR)+ECA(ridge=0·지연등가 n_taps)+0도플러가드+**실장소거깊이 depth**(∞ 정본, 40/60/90 병기) | 양자화·지면 | **보고하는 R90** | ✅ |
| **FS-2** | +`experiment_x410.adc_quantize` 실통과 | 지면 | 동적범위 벽 조건부 | — |
| **FS-3** | +평면지면 2-ray(σ격자 재사용, F⁴ per-leg)+fresnel게이트+대기감쇠+수평선 | — | **정직성 점검**: 자유공간이 상한 아님(F⁴∈[−20,+11.5]dB). 닫힌형 동반, GPU 0회 | — (동반) |

전 단계 공통 배제(FS-3 제외): 벽·챔버·클러터·다중경로·안테나패턴(스칼라 G_rx)·케이블손실·다중표적·스캔누적. **FS-1에는 정적 클러터가 존재하지 않음** — 챔버의 죽은 파라미터가 여기선 애초에 없다. 그 자리를 §8 벽 지도가 대신한다.

> `meta.assumption_ladder=["FS0","FS1","FS2","FS3"]`, `headline_stage="FS1"`. FS-3는 `sensitivity.ground_2ray`와 `verify_freespace.ground_check`에만 산다. `radio_horizon`·`atmos_db_per_km`는 **FS-3 meta로만** (R4).

---

## 3. 실험 설계 — 축·값 (수정본)

`bistatic_scene.CHAMBER/TX/RX`·`geometry.*` **import 금지**. 새 `src/freespace_scene.py`가 자체 상수(부호는 `bistatic_scene.bistatic_params` src/bistatic_scene.py:37-50 복제 — 멀어지면 f_d<0).

```
FS_TX=(0,0,25)   FS_RX=(L,0,3)   FS_ALT∈{60,120}   FS_SPEED∈{5,15}
O=(TX+RX)/2 ; P(d,φ)=O+d(cosφ,sinφ,0)+(0,0,ALT−O_z)
u1=(TX−P)/R1, u2=(RX−P)/R2, Rb=R1+R2−L, τ=Rb/c, f_d=v·(u1+u2)/λ, β=∠(u1,u2)
```
높이는 **배치 파라미터**(선언값, 근거문서 없음): FS-1서 역할=el·β 결정, FS-3서 F⁴ 기여(R4 해소).

| 축 | 값 | 개수 | 비고 |
|---|---|---|---|
| 드론 | **`DRONES` 레지스트리 전수** (앞머리 `mini5pro, phantom4, mavic4pro, matrice4e, s1000plus`) | `len(DRONES)` | ★target_extent 순(F17). 전 그림 이 순서. 개수를 여기 적지 않는다 |
| 모드 | W1 W2 W3·L1 L2 L3·G1 G2 G3 | 9 | 헤드라인 상시 3인방 W1·L1·G1 |
| 반송파 | WiFi5.21/LTE1.843/NR3.5 GHz | 3 | 표준↔반송파 1:1 |
| **공통반송파 반사실** | W/L/G 구조를 3.5 GHz에 | +1세트 | F10 밴드효과 분리(GPU 0회, σ 3밴드 재사용) |
| 기준채널모델 | ①full-waveform(정본)②pilot-only | 2 | 상수는 9모드 재측정(F5) |
| **전력규약** | `equal_total`/**`equal_psd`(점유축 정본)**/`deploy` | 3 | F2 |
| **기준반복률** | LTE 1000·**NR SSB 50**·NR PRS 200·WiFi {10,100,1000,5000} | — | F1·F9. M=round(T_CPI·PRF) |
| 베이스라인 L | 100/**500(헤드라인)**/2000 m | 3 | |
| 고도 | 60/120 m | 2 | el 유도 |
| 수평거리 d | `geomspace(100,20000,240)` 표시격자, R은 이분법 아닌 **최외곽교차 역해**(S6) | — | |
| 헤딩 ψ | 0…359°,1° | 360 | σ자세+도플러 동시구동(1급) |
| 장면방위 φ | 0…355°,5°, **헤드라인 φ=90°(명시)** | 72 | S7 |
| EIRP 등전력 | 63 dBm | 1 | in-burst peak(F13) |
| EIRP 배치 | WiFi30/LTE63/NR(유휴)**≈47**/NR(풀)65 | — | F2: 유휴5G≠풀gNB |
| EIRP 사다리 | 20…90 dBm 9점 | 9 | F8그림 |
| T_CPI | **100 ms(헤드라인)**, [56,100,200,500,1000] | 5 | walk벽 초과 회색 |
| Rx N | 1(헤드라인),2,3,4 | 4 | +10log10N 상한 |
| ADC bits | 12,14,16,∞ | 4 | |
| PAPR백오프 | 0,6,10 dB | 3 | |
| DPI억압 supp | 0,20,30 dB × **φ의존 게이트**(R7) | — | |
| **실장소거깊이** | 40,60,90,∞ dB | 4 | **R5 필수** |
| ECA ridge | **0(정본)**, 1e-6·1e-4(참조) | 3 | R6 |
| **INR(동일채널)** | −10,0,20,40 dB | 4 | R9 |
| Pfa | 셀당1e-4(정본)+1e-7(운용,검증불가표기) | 2 | |
| σ (드론×밴드) 독립섭동 | div12/24 교차 + 부트스트랩 | — | F11(통짜시프트 폐기) |

---

## 4. 기준신호·전력·CPI 규약 (물리 수정 — F1/F2/F5/F9)

### 4.1 반복률·M (F1/F8 — 헤드라인 전복)
- **M을 물리 반복률서 유도**: `M = max(2, round(T_CPI · PRF_mode))`. PRF는 `reference_repetition_hz`:
  - LTE CRS = 1000, WiFi = `wifi_packet_rate_hz`(스윕), **NR SSB = 50**(20 ms 버스트), NR PRS(G2/G3) = 200(측위세션).
- T_CPI 100 ms: LTE M=100, WiFi M=100(@1k), **NR-SSB M=5**, NR-PRS M=20.
- 코히런트 이득 = 정합필터(B_ref·T_ref) × 도플러 FFT(M). SSB의 낮은 M이 물리적 핸디캡(이전 report12 타일링은 M=112를 날조).
- `meta.cpi.reference_repetition_hz`, `.M_by_mode`, `.ssb_period_ms=20`, `.ssb_M_vs_report12_db`(≈−16dB 기록).
- **T_CPI 고정 규약 유지**(report05/12 공정성): 관측시간 동일, M만 물리적으로 다름.

### 4.2 전력정규화 (F2)
- 3뷰 병기. `equal_psd`(정본, 점유축): `run_min_cell` 규약 승계 — per-RE 송신전력 동일, G1의 낮은 평균방사전력 물리반영. `power_normalization`에 뷰별 방사전력차 기록(★mean|tx|² G3기준: wifi G1 −8.0/lte −10.3/nr −18.2 dB).
- `equal_total`: 총 EIRP 동일(파형효과 분리용, report05).
- `deploy`: WiFi30/LTE63/**NR유휴≈47**(풀gNB 65 아님)/드론.

### 4.3 상수 9모드 재측정 (F5)
- `losses_db.straddle`·`pilot_power_frac_db`·`eta_ref_db`를 **(std,occ) 9행** 재측정. straddle_rng는 `fs/B_ref` 오버샘플서 유도(SSB 오버샘플 17.1→반빈 straddle≈0). G3 3행 브로드캐스트 금지. `benchmark/verify_freespace.py`가 산출.

---

## 5. 검출기 형상·ECA·CFAR (R6/F4/F6/F7/R3)

### 5.1 ECA (정본 확정, ★스모크 검증)
```
ridge_rel = 0                                  # ★R6: 1e-6·1e-4보다 잔류 낮음
n_taps    = ceil(eca_tap_span_m / (c/fs))      # F6: 지연등가, tap_span_m=60(선언)
                                               #  → LTE 7, WiFi 16, NR 25 탭
```
- 자유공간 DPI=단일탭(0지연·0도플러, `passive_process.py:65`). clutter=(). 60 m 스팬은 DPI 주엽+여유를 덮고, 표적 R_b(수백m~km)≫60 m이라 표적 자기소거 없음.
- `eca_numeric` 벽 **삭제**. 대신 `dpi_residual`(실장 유한소거, §8).
- `meta.detector.eca={ridge_rel:0, n_taps_by_mode:{...}, tap_span_m:60}`.

### 5.2 두 형상 (확정 설계 계승, 수정)
| 형상 | n_range | n_taps | 역할 |
|---|---|---|---|
| **S-G** | 64(표적 Rb 중심) | 지연등가(§5.1) | 전이곡선·헤드라인 |
| **S-W** | Rb 전체(NR fs122.88M·Rb6km→2460 등) | 지연등가 | 경험 Pfa·FA회계 |

- **[R3] Pfa폭발 완화(R3§3)**: ridge=0+free-space(clutter=())서 단일탭 DPI 완전소거→n_range≫n_taps라도 누설≈0(★스모크 확인). 단 **실제 n_range서 경험 Pfa 측정 유지**, §1.6 바닥스윕 최대 n_range 재실행.
- **검출 정의(S4/R3§2)**: `hit = det[표적근방±2].any() & 문턱초과`. 전역 argmax **아님**. 전역최대 규약은 caveat.
- **훈련셀 배제(A5, ★확인)**: `doppler_guard_mask`의 `also_exclude_from_training`는 검출마스크만(`passive_process.py:295`). 가드행 제거 부분맵에 `ca_cfar_2d` 적용하는 `_cfar_excl_rows()` 직접 구현. 중앙값 치환 금지(훈련평균 1.59dB 하락).
- **CFAR guard 이중(F4)**: `fixed`(2,2)/(6,6) 리포트간 비교 + `rescell`(분해능셀 등가, `guard_r=ceil(0.5·fs/B_ref)+2`). `meta.detector.cfar.guard_bins_by_mode`. Pd는 측정이라 자기가림 SNR90에 흡수 — 두 규약 SNR90 병기.
- **전이곡선 도플러오프셋 축(R3§1)**: `dopoff∈{3,5,8,15,≥30}빈`. `soft_blind_frac`(f_guard<|fd|<f_guard+3·dfd) 별도라벨.
- **FA/CPI 분해능셀(F7/R3§3)**: 인접초과 클러스터 후 blob 수. `false_alarms_per_cpi_bins`(참고)+`_rescell`(정본).

### 5.3 SNR 규약 (A8/R3§5, ★확인)
- `measure_single_snr`=`peak²/median(rd²)`(★`experiment_detection.py:232`). mean규약 정본, +1.59dB 변환 JSON·전캡션. k_mode가 실전파서 흡수(이중계상 방지). `verify.snr_convention_consistency`에 한 셀 두 규약 R 일치 박제.

### 5.4 Sionna PHY 커널 (A20, ★확인)
- 정본 에코생성기 유지. `sionna_chain.channel_taps(..., max_delay_spread=1.3·Rb/c)` 동적설정(★인자임, 기본 1e-6 아님). 해석적 분수지연 대조군, 상관계수 JSON(report12 0.9997~0.99999).

### 5.5 CFAR 손실 (R3§4/F4, ★확인)
- ★`cfar_loss_db=0.076=10log10(9.373/9.210)`=**평균문턱오프셋**(분산 무시). F13 Marcum점선은 **CA-CFAR 인지형** `Pd=(1+α/(N(1+SNR)))^−N`. −0.076을 "mean threshold offset"으로 재명명. 1e-7 경험Pfa는 K=20000·소형맵서 검증불가 명시.

---

## 6. σ 처리 (음의 el·파이프라인 추정량·멀티스태틱·F15/F17)

### 6.1 격자 생산
```
producer: src/experiment_freespace_sigma.py → outputs/report13_sigma_grid.json
엔진: rcs_sbr.rcs_sbr_batch(penetrate=True, jitter=2, div=16)   # ★report2와 div=16 일치(A17)
az: 0…357°,3°(120)   el: [0,−0.5,−1,−2,−3.5,−5,−8,−12,−20]°(9, ★음수·유효도메인 조밀 S8/A2)
fc: 각 반송파 ±1.5% 3점   각도평활 3°
+공통3.5GHz 반사실 세트(F10)
규모: 5×3밴드×3주파×9el×120az = 48,600 az-eval + 반사실
```
- **el 음수 확정(★A2)**: 지상TX/RX+공중표적 이등분선 el 전구간 음수. report2는 el=+15°(★meta 확인)이라 §0.1 원값은 부호 반대. m² 선형보간(dB보간 금지).
- **el은 스윕축 아님**: `el=look_angles(u1,u2)`로 기하유도. R 해와 함께 암시적 방정식(§7.4).
- **"overhead spike" 서사 삭제** → "저고도 근거리서 배(belly)를 크게 본다". `el>0`은 범위 밖.
- **캐시(★A18)**: `_SCENE_CACHE` 키=`(drone,fc_MHz,exclude)`, 씬은 el 무관 — cache_key에 el 넣지 않음(넣으면 씬 9배 낭비). σ값 캐시는 `channel._sig_key`(az·el·fc·지문)가 유일화.
- **프리필(★A19)**: `channel.sbr_sigma_prefill`/`_prefill_worker` 재사용(budget NameError 우회 내장 `benchmark/channel.py:167-173`). mitsuba import 전 `gpu.pick()`.
- **조회 정본**: `channel.look_angles(u1,u2,az_span_deg=8,n_az=5)` 이등분선+±4°/5pt 선형 m² 평균. az_look−ψ로 헤딩결합(σ자세·도플러 동시).

### 6.2 밴드 산출 (S5 — 파이프라인 추정량)
- §0.1·§5 밴드는 **파이프라인과 동일 추정량**(5pt m² 평균, 음의 el)으로 재산출. 평활 후 폭(★설계추정 5.63~13.43 dB / R_eq축 1.38~2.17배). `sensitivity.az_smoothing`(az_span 0/4/8°). `meta.lookup`에 "평활=수치장치, 하위꼬리 최대+3.7dB 상승, m²평균 Jensen 낙관".

### 6.3 멀티스태틱 검증 (§3.4, ★rcs_sbr_multistatic 실재 L239)
- β∈{0,15,30,45,60,75,90}°×az24×5기종×3밴드 → `Δσ(β)=σ_multi−σ_bisector` mean/rms/p95. 조명 û_i 1회, û_s만 변경(싸다). 상반성 rms(★깊은널 5~9dB) 기록. β>90° 유효범위 정당화.

### 6.4 신뢰도 지도 (F15) + 순서 (F17) + 섭동 (F11)
- `meta.sigma_confidence.D_over_lambda`(★mini5pro@LTE 2.32λ=최악). <3λ 셀 그림 세로선. `target_extent` 순서(★F17). **(드론×밴드) 독립섭동**(div12/24 교차=셀오차 + 부트스트랩), 통짜 −3/0/+3 시프트 폐기(항등 순위보존).

### 6.5 인용 정책 (변경 없음)
- 백분위(p10/p50/p90)·커버리지만. 널최소값·σ_min·aspect-peak·절대점값·단일"검지거리 N m" **금지**(`rcs_po.py:184-194`).

---

## 7. 검지거리 정의 3층 + solver (S1/S2/S4/S6/S7)

### 7.1 1층 — Pd(SNR) 측정
- `SNR90(mode,shape,N,dopoff)`=Pd0.9 되는 RD출력 SNR. Pfa=경험측정 셀당1e-4. mean규약(+1.59). K=4000, Wilson95%CI, snr90_lo/hi. SNR50 병기(★report12 SNR90−SNR50: W1 2.88/L1 2.45/G1 2.76). Pd0.9 근거="우리가 정한 기준"(문헌 통일없음, MathWorks식 "12dB 가정"은 안 함 — 측정).

### 7.2 2층 — 도플러 가시성 (F8 상한 추가)
- 하한: `|f_d_folded|≥f_guard=2.5/T_CPI`. **상한(F8)**: `nyquist_ok=|f_d|<PRF/2`. 가드판정은 **접힌 도플러** `f_d_folded=mod(f_d+PRF/2,PRF)−PRF/2`. SSB PRF50→전속도 접힘=유휴5G 무력화. `blind_heading_frac`·`alias_heading_frac` 모드·속도별.

### 7.3 3층 — 커버리지 (S2/S3/S4)
- `R90_C50`=P_ψ[Pd≥0.9]≥0.50 최대 d(**최외곽교차**). 밴드=`R90_C25`~`R90_C50`(★C10 공집합 회피, 커버리지천장 C_max=1−b_blind 상대). 
- **분해(S3)**: `C(d)=(1−b_blind(d))·P_ψ[σ≥σ_th|비블라인드]`, 두 인자 별도.
- **E_ψ[Pd](S4)**: `E_psi_Pd_at_R90`·`R_Epd90_m`(E_ψ[Pd]=0.9 거리) 필수. 헤드라인 두 숫자.
- 이름규약: `R{Pd}_C{cov}`. 슬래시 금지. 단서 3개(단일CPI·단일표적·CPI내 σ고정).

### 7.4 solver (S1/S6 — 이분법 폐기)
```
solve_range(mode,drone,φ,ψ,N,view,ref,eirp,T,L,alt,eca_depth,...):
  # SNR(d,σ(az_look−ψ, el_look(d))) = th_from_Pd(shape,N,dopoff(d))  암시적
  # el_look(d)는 d의존 → d격자서 el 사전계산 후 σ를 d의 함수로 평탄화
  # SNR(d)를 d격자 위 평가 → 최외곽 하강교차(np.diff(sign) 마지막)
  return dict(R_m, R_eq_m, Rb, kappa, beta, el_look, n_local,
              monotone_ok, snr_peak_d, snr_ceiling_db, frac_never_detectable)
```
- **비단조(★S6)**: φ 0/10/30°서 내부최대. 이분법 무효. `snr_ceiling_db`(★+24.7dB@d452)보다 어두운 헤딩=`frac_never_detectable`(거리무관 미검출). `monotone_ok` φ별.
- **비선형(★S1)**: 분산·밴드는 `R_eq=√(R1R2)`축 인용(^¼ 정확). `n_local_at_R90`(★d150·L500=1.03). dB↔배율 환산 금지(n_local 병기). n<3.5는 `limit`에 `geometry_nonlinear`.

### 7.5 오경보 회계 (§2.4, F7)
- S-W서 **분해능셀 기준** CPI당 기대 FA(★G1 2.88, W1 15.3). Pfa 1e-7 병기(★α비 → +2.5dB → 거리×0.87, 단 경험검증 불가 표기).

### 7.6 k_mode 교정 (§2.5 — 변경없음, S1 유보 추가)
```
k_mode[dB] = SNR_RD_measured − 10log10(P_echo/N0)
```
- 잔차 |Δ|<0.5, σ불변 어서션. 닫힌형(★검증: LTE theory15.883 vs meas15.787 −0.096, WiFi+0.032, NR−0.010). **B는 SNR항에 없음**(★verify_linkbudget). 상수 전부 JSON서 읽음. ⚠k_mode는 **곱셈상수**라 S1·S6 기하 비선형 흡수 못 함 — §2.5에 명기.

---

## 8. 벽 지도 (thermal/adc/dpi_residual/walk/farfield/beta/nonlinear)

`limit` enum = `thermal | adc | dpi_residual | eca(참조) | walk | farfield | beta | geometry_nonlinear | dpi_unsuppressible`. FS-3서 `ghost_resolved` 추가.

### 8.1 열잡음: `N0_thermal = kT₀F·B_noise`.

### 8.2 ADC (감도패널, §1.7 계승): `N0_quant=P_dir·10^(−(DR+supp)/10)/fs`, `DR=6.0206·bits+1.76`(★`experiment_x410.py:79`, 12bit→74dB). `R_adc∝(σL²·10^(DR/10)·fs·ηT)^¼`(EIRP무관·L^½). 기본 DR74·백오프0·supp0. 백오프{0,6,10}·bits·**supp φ의존**(R7) 스윕. FS-2 실통과 대조.

### 8.3 **dpi_residual (R5 — 최대 벽, 신규)**
```
N0_dpi = P_dir · 10^(−eca_depth_db/10) / B_noise      # 실장 유한소거 잔류
N0_eff = N0_thermal + N0_quant + N0_dpi + N0_inr
```
- `eca_depth_db∈{40,60,90,∞}` 필수스윕. ★L=500 헤드라인: DNR75dB, 소거60→열잡음대비 +15.4dB(거리×0.41). 이상소거 vs 60dB 헤드라인 병기. `eca_depth_required_db`(요구량)와 구분.

### 8.4 **supp φ의존 (R7)**: `supp_eff(φ)=min(supp, supp_max(Δθ(φ)))`. Δθ=RX서 TX↔표적 각분리. Δθ<빔폭/2면 supp=0. φ≈180°(★각분리 0.09°)=`limit="dpi_unsuppressible"` 회색. `meta`에 빔폭·문턱 선언.

### 8.5 **INR (R9)**: `N0_inr=10^(INR/10)·N0_thermal` (코히런트이득 동일수신). `inr_db∈{−10,0,20,40}`. §8에 "20dB 이웃셀 하나로 거리 한자릿수".

### 8.6 유효범위 게이트 (모든 셀, 축 안 자름)
| 게이트 | 조건 | 근거 |
|---|---|---|
| 전방산란 | β≤90° | ★`rcs_sbr.py:252-255` β→180° σ≡0 |
| 원거리장 | d≥2D²/λ | ★`farfield_distance(target_extent)`: s1000plus@5.21G **63.1m** 최악, mini5pro@LTE 1.75m. D정의 병기(`meta.farfield.D_definition`) |
| 나이퀴스트 | |f_d|<PRF/2 | F8 |
| **fresnel (FS-3만)** | min clear/F₁≥0.6 | R3 |
| dpi_unsuppressible | Δθ≥빔폭/2 | R7 |

### 8.7 range-walk (§1.9 계승): ΔR_b=c/B → T_max=ΔR_b/v_r. 광대역일수록 walk 벽 이르다(★PRS 98MHz T_max@5m/s 0.61s ↔ SSB 7.2MHz 8.33s). 도플러 walk `T<√(Rλ)/v_t` 병검. T_CPI 벽 초과 빨간해칭·수치금지.

### 8.8 **FS-3 지면 (R1/R2, 동반)**
- per-leg `F_i=|1+Γ(ψ_i)·e^{−jkΔ_i}|`, 에코 `×F₁²F₂²`. ε_r=15·σ=0.005·수직/수평편파. ★4경로 el차≤1.37°·β차≤1°→σ격자 재사용. 산출=**F⁴ 분포**(프린지평균·p10·p90), 헤드라인 밴드에 σ자세밴드와 나란히. ΔR_b(지면경유) vs c/B 표(G1/L1=페이딩, W/G3=근거리 유령). **"상한선" 철회**, "F⁴∈[−20,+11.5]dB, 거리 0.32~1.94배" 명기.

---

## 9. 새 파일 + 함수 시그니처

**기존 파일 하나도 안 고침**(report01~12 재현성 보호). 전역상수(`N_RANGE/N_TAPS/DPI_AMP`)는 **인스턴스 생성 전 속성 교체**, `DPI_AMP`는 기하유도 DNR로(A36).

### `src/freespace_scene.py` (순수함수, I/O 없음)
```python
FS_TX=(0.,0.,25.); FS_RX=lambda L:(L,0.,3.); FS_ALT=(60.,120.); FS_SPEED=(5.,15.)
BASELINES=(100.,500.,2000.); L_REF=500.; PHI_HEADLINE_DEG=90.
def fs_params(tx, rx, tgt, vel, fc) -> dict           # 부호=bistatic_params 복제. R1,R2,Rb,tau,fd,beta,u1,u2,lam
def target_pos(d, phi_deg, L, alt) -> np.ndarray       # (3,)
def heading_velocity(psi_deg, speed) -> np.ndarray
def look_el_deg(u1, u2) -> float                       # 이등분선 el (음수)
def doppler_guard_hz(T_cpi) -> float                   # 2.5/T
def prf_hz(std, mode, wifi_packet_rate=1000.) -> float # F1: SSB 50 등
def M_from_prf(T_cpi, prf) -> int                      # max(2,round(T*prf))
def folded_doppler(fd, prf) -> float                   # F8
def blind_sector(psi_grid, phi, d, L, alt, T, prf, speed, lam) -> np.ndarray[bool]
def beta_gate(beta_deg) -> bool                        # <=90
def farfield_gate(d, drone, fc) -> bool                # radar_scene 호출
def nyquist_gate(fd, prf) -> bool
def angular_sep_tx_target_deg(rx, tx, P) -> float      # R7 supp
def fresnel_clearance_ratio(rx_h, R2, lam) -> float    # FS-3
```

### `src/freespace_link.py` (닫힌형 — 레이더식 재구현 금지, `benchmark/link_budget` 호출)
```python
def n0_thermal(nf_db, B_noise) -> float
def n0_quant(P_dir, dr_db, supp_db, fs) -> float
def n0_dpi(P_dir, eca_depth_db, B_noise) -> float       # R5
def n0_inr(inr_db, n0_thermal) -> float                 # R9
def snr_rd_db(eirp,grx,lam,sigma,R1,R2,nf,eta_ref,T,losses,k_mode,n0_extra) -> float
def solve_range(snr_of_d, th_db) -> dict                # 최외곽교차, ceiling, n_local, monotone (S6/S1)
def dnr_db(P_dir, n0) -> float
def coverage_fraction(pd_of_psi, blind_mask) -> tuple   # (C, factor_blind, factor_sigma) (S3)
def e_psi_pd(pd_of_psi) -> float                        # S4
def cassini_contour(kappa, TX, RX) -> np.ndarray
def two_ray_F(psi_i, dR, gamma) -> float                # FS-3
def n_local(kappa_of_d, d) -> float                     # S1
```

### `src/freespace_detect.py` (CFAR/RD 커널 재구현 금지)
```python
def fs_shapes(wf, Rb_span, fs) -> dict                  # S-G/S-W, n_range·n_taps(지연등가 F6)
def eca_canceller(ref_cpi, fs, tap_span_m=60.) -> ECACanceller  # ridge_rel=0 (R6)
def cfar_guard_bins(wf, fs, mode="fixed"|"rescell") -> tuple    # F4
def _cfar_excl_rows(rd, f_d, width=3) -> mask           # A5 부분맵 CFAR
def detect_target_neighborhood(rd, th, di_true, ri_true, tol=2) -> bool  # S4/R3§2 (argmax 아님)
def calibrate_pfa(pre, shape, K_pfa=20000) -> dict      # 경험 Pfa 재교정
def eca_floor_sweep(ref, dnr_grid, ridge_list, ntaps_list) -> dict
def false_alarms_per_cpi(shape, mode, pfa) -> dict       # bins + rescell (F7)
def transfer_by_dopoff(pre, dopoff_bins, K) -> dict      # R3§1
```

### `src/experiment_freespace_sigma.py` (`rcs_sbr()` 다중반사 금지, 새 워커 금지)
```python
def build_sigma_grid(drones, bands, az, el, n_f) -> dict   # sbr_sigma_prefill 재사용
def multistatic_check(drones, bands, beta_grid, n_az) -> dict  # rcs_sbr_multistatic
def sigma_confidence(drones, bands) -> dict                # D/λ (F15)
def counterfactual_common_carrier(drones, fc=3.5e9) -> dict # F10
def perturbation_grid(div_list=(12,24)) -> dict            # F11
# main: --drone 증분저장(재시작), div=16, → outputs/report13_sigma_grid.json
```

### `src/experiment_freespace_range.py` (`experiment_detection.py` 수정 금지, import만)
```python
# --stage=threshold|calib|solve|verify|all
def stage_threshold(...) -> dict    # 두 형상×9모드×N×dopoff Pd(SNR)MC + 경험Pfa (FS-0/1/2)
def stage_calib(...) -> dict        # k_mode + σ불변
def stage_solve(...) -> dict        # 닫힌형전파·최외곽역해·커버리지·감도·FS-3·벽지도
def stage_verify(...) -> dict       # 스팟체크
# 전역상수 인스턴스 전 교체, DPI_AMP=기하유도 DNR
# → outputs/report13_freespace.json
```

### `benchmark/verify_freespace.py` → `outputs/verify_freespace.json`
### `src/viz_report13.py` (물리계산 금지, JSON만): F1~F16 + matplotlib GIF R5~R8
### `src/render_report13.py` (`render_rt.CAMS`·`make_gif` 수정금지, 챔버금지): RT GIF R1~R4 + 스틸 22
### `src/make_notebook13.py` (숫자 손기입 금지): `report13.ipynb`

`provenance`: `engines=["sbr","sionna-phy","sionna-render","radar-dsp","matplotlib"]` — ★`ENGINE_DESC`에 없는 태그는 조용히 누락(report12 함정), 필요시 먼저 등록.

---

## 10. `outputs/report13_freespace.json` 완전 스키마 (예시값 포함)

```jsonc
{
 "meta": {
  "report":"report13","generated":"2026-07-22T..","git_rev":"","runtime_s":0.0,"gpus":[0,2],
  "K":4000,"K_pfa":20000,"sigma_file":"outputs/report13_sigma_grid.json",
  "assumption_ladder":["FS0","FS1","FS2","FS3"],"headline_stage":"FS1",
  "assumptions":{"ground":false,"walls":false,"clutter":false,"multipath":false,
    "antenna_pattern":false,"fluctuation_intra_cpi":false,"cochannel_interf":false,
    "direct_path":true,"eca":true,"scan_integration":false,"multi_target":false},
  "geometry":{"TX":[0,0,25],"RX":["L",0,3],"heights_note":"DEPLOYMENT params (declared, no source doc); FS1 role=set el/beta only",
    "alt_m":[60,120],"baseline_m":[100,500,2000],"baseline_ref_m":500,"speed_ms":[5,15],
    "heading_deg":"0..359/1","phi_deg":"0..355/5","phi_headline_deg":90,
    "d_grid_m":"geomspace(100,20000,240)","beta_valid_max_deg":90.0},
  "link_budget":{"rx_gain_dbi":10.0,"noise_figure_db":5.0,"sys_loss_db":0.0,
    "eirp_definition":"in-burst peak","eirp_equal_dbm":63.0,
    "eirp_deploy_dbm":{"wifi":30,"lte":63,"nr_idle":47,"nr_full":65},
    "eirp_ladder_dbm":[20,30,40,50,60,63,70,80,90],
    "power_normalization":{"views":["equal_total","equal_psd","deploy"],"canonical_occupancy":"equal_psd",
      "radiated_power_frac_db_vs_g3":{"wifi":{"G1":-8.0,"G2":-6.28},"lte":{"G1":-10.34,"G2":-3.86},"nr":{"G1":-18.18,"G2":-4.61}}},
    "provenance":"eirp/rx_gain/nf/heights DECLARED — no source doc (docs/EIRP_CLASSES.md TODO)"},
  "reference_model":{"canonical":"full_waveform_capture","secondary":"pilot_only",
    "pilot_power_frac_db_by_mode":{"W1":-3.27,"L1":0.0,"G1":0.0,"W3":-24.11,"L3":-5.80,"G3":-5.49}},
  "cpi":{"model":"M = round(T_cpi * reference_repetition_hz)",
    "reference_repetition_hz":{"W1":1000,"L1":1000,"G1":50,"L2":6.25,"L3":6.25,"G2":200,"G3":200},
    "wifi_packet_rate_hz_sweep":[10,100,1000,5000],
    "ssb_period_ms":20,"ssb_M_vs_report12_db":-16.0,
    "T_cpi_s":[0.056,0.1,0.2,0.5,1.0],"T_cpi_ref_s":0.1,
    "M_by_mode":{"W1":100,"L1":100,"G1":5,"G3":20},"rate_source":{"W1":"traffic_dependent","L1":"standard_fixed","G1":"standard_fixed"}},
  "detector":{
    "shapes":{"S_G":{"n_range":64,"gate":"truth Rb"},"S_W":{"n_range":{"nr":2460,"lte":615,"wifi":1600}}},
    "eca":{"ridge_rel":0.0,"tap_span_m":60.0,"n_taps_by_mode":{"nr":25,"lte":7,"wifi":16},
      "note":"ridge_rel=0 canonical (measured cleanest; 1e-6 leaks +25dB @DNR120)"},
    "cfar":{"guard_fixed":[2,2],"train_fixed":[6,6],"n_train":264,
      "guard_bins_by_mode":{"W1":[2,2],"L1":[2,2],"G1_rescell":[11,2]},
      "cfar_loss_db":0.076,"cfar_loss_note":"mean threshold offset, NOT variance-inclusive detection loss"},
    "doppler_guard_width":3,"training_exclusion":"submap CFAR (_cfar_excl_rows)",
    "detection_def":"target-neighborhood +-2 threshold crossing (NOT global argmax)",
    "dopoff_bins":[3,5,8,15,30],
    "snr_convention":"peak^2 / MEAN noise-cell power","snr_median_offset_db":1.594,
    "sionna_kernel":{"max_delay_spread_model":"1.3*Rb/c","corr_vs_analytic":0.99995},
    "pfa_cell":1e-4,"pfa_operational":1e-7,"pfa_op_verifiable":false,
    "pfa_calibration_fs":{"S_G":{"G1":{"nominal":6.3e-5,"empirical":1e-4}}},
    "false_alarms_per_cpi_bins":{"S_W":{"W1":16.0,"L1":6.1,"G1":49.2}},
    "false_alarms_per_cpi_rescell":{"S_W":{"W1":15.3,"L1":3.6,"G1":2.88}},
    "losses_db_9mode":{"straddle_rng_half":{"W1":-3.48,"L1":-1.24,"G1":-0.02,"G3":-2.29}}},
  "sigma_confidence":{"D_over_lambda":{"mini5pro":{"lte":2.32,"nr":4.41,"wifi":6.56},"s1000plus":{"lte":8.29}}},
  "array":{"aperture_m_by_band":{"lte":0.244,"nr":0.129,"wifi":0.086}},
  "farfield":{"D_definition":"radar_scene.target_extent (bbox max)","alt_D":"diagonal",
    "d_min_m":{"s1000plus":{"wifi":63.13,"nr":42.41,"lte":22.33},"mini5pro":{"lte":1.75}}},
  "drone_order":["mini5pro","phantom4","mavic4pro","matrice4e","s1000plus"],
  "chamber_reference":{"Rb_max_m":22.0,"eirp_dbm":12.0,"snr50_report12_mean_db":13.50,
    "snr90_minus_snr50_db":{"W1":2.88,"L1":2.45,"G1":2.76}}},

 "waveforms":{"G1":{"std":"nr","occ":"G1","ref_name":"SSB","fc_hz":3.5e9,"lam_m":0.0857,
   "bw_hz":1e8,"ref_bw_hz":7.2e6,"fs_hz":1.2288e8,"M":5,"prf_hz":50,"d_rb_m":41.64,
   "v_min_ms":1.07,"f_guard_hz":25,"blind_heading_frac":{"5":0.143,"15":0.046},
   "alias_heading_frac":{"5":0.99},"eta_ref_db":0,"oversample_fs_over_bref":17.1}},

 "calib":{"G1":{"k_db":0,"closed_form_pred_db":0,"resid_db":0,"k_sigma_invariance_db":0,
   "note":"k_mode is multiplicative; does NOT absorb S1/S6 geometry nonlinearity"}},

 "detector_transfer":{"S_G":{"G1":{"N":{"1":{"dopoff":{"8":{
   "snr_grid_db":[],"Pd":[],"wilson_lo":[],"wilson_hi":[],"Pfa_emp":[],
   "snr50_db":0,"snr90_db":0,"snr90_lo_db":0,"snr90_hi_db":0,
   "marcum_cfar_snr90_db":0,"marcum_dev_db":0}}}}}}},

 "ranges":{"mini5pro":{"L1":{"equal_psd":{"full_waveform_capture":{"by_N":{"1":{
   "R90_C50_m":0,"R90_C25_m":0,"R90_C10_m":null,"coverage_ceiling":0.72,
   "R50_C50_m":0,"R_C80_m":0,"R90_C50_pfa1e7_m":0,
   "R_eq_at_R90_m":0,"R2_at_R90_m":0,"Rb_at_R90_m":0,"kappa_at_R90":0,
   "beta_at_R90_deg":0,"el_look_at_R90_deg":-2.0,"n_local_at_R90":3.76,
   "E_psi_Pd_at_R90":0.70,"R_Epd90_m":0,"snr_ceiling_db":24.7,"frac_never_detectable":0.0,
   "monotone_ok":true,"snr_peak_d_m":0,
   "sigma_at_R90_C50_dbsm":0,"sigma_dist_at_d_of_R90":{"p10":0,"p50":0,"p90":0},
   "dnr_at_R90_db":0,"snr_at_R90_db":0,
   "R_thermal_m":0,"R_adc_m":0,"R_dpi_resid_m":{"40":0,"60":0,"90":0,"inf":0},"R_total_m":0,
   "limit":"thermal","farfield_ok":true,"beta_ok":true,"nyquist_ok":true,
   "blind_heading_frac":0.276,"soft_blind_frac":0.18,
   "budget_terms_db":{"eirp":0,"grx":0,"lambda2":0,"sigma":0,"spread":0,"n0":0,"eta_ref":0,"t_cpi":0,"losses":0},
   "R90_ci95_m":[0,0]}}}}}}},

 "curves":{"snr_vs_d":{"G1":{"mini5pro":{"d_m":[],"snr_thermal_db":[],"snr_total_db":[]}}},
   "coverage_C_of_d":{"mini5pro":{"G1":{"d_m":[],"C":[],"factor_blind":[],"factor_sigma":[],"E_psi_pd":[]}}},
   "rb_ellipses":{},"cassini":{}},

 "coverage":{"map":{"500":{"x_m":[],"y_m":[],"beta_masked":[[]],"pd":{}}},
   "polar":{"mini5pro":{"G1":{"psi_deg":[],"R90_m":[],"blind":[],"alias":[]}}},
   "blind_sectors":{},"soft_blind_frac":{}},

 "walk":{"G1":{"d_rb_m":41.64,"T_max_s":{"5":8.33,"15":2.78},"T_cpi_used_s":0.1,"ok":true,"doppler_walk_T_max_s":0}},

 "dynamic_range":{"adc_bits":[12,14,16,null],"dr_db":{"12":74.0},
   "papr_backoff_db":[0,6,10],"dpi_supp_db":[0,20,30],"supp_phi_gated":true,
   "n0_quant_minus_thermal_db":{},"crossover_eirp_dbm":{},"fs2_measured_pd_drop_db":{}},

 "sensitivity":{"eirp":{},"cpi":{},"baseline":{},"nrx":{},
   "eca_depth_db":{"grid":[40,60,90,null],"R90_m":{"L1":{"500":{"60":0,"inf":0}}}},   // R5
   "inr_db":{"grid":[-10,0,20,40],"R90_m":{}},                                          // R9
   "wifi_packet_rate_hz":{"grid":[10,100,1000,5000],"R90_m":{}},                        // F9
   "az_smoothing_deg":{"grid":[0,4,8],"span_p10p90_db":{}},                             // S5
   "fs_oversample":{},"nf_db":[3,5,7],"rx_gain_dbi":[6,10,14],"pfa":[1e-3,1e-4,1e-7],
   "sigma_perturb":{"method":"drone_band_independent (div12/24 + bootstrap)","rank_flip_by_band":{}}, // F11
   "var_budget_db":{"300":{"aspect_psi":0,"geometry_phi":11.4,"altitude":0,"drone":8.37},
                    "1000":{"aspect_psi":0,"geometry_phi":1.08,"drone":8.37}},           // S7
   "common_carrier_decomp":{"lte_to_wifi":{"lambda2_sigma":0,"ref_bw":0,"rep_duty":0,"eta_ref":0,"doppler_blind":0}}, // F10/F14
   "ground_2ray":{"F4_db":{"p10":-8,"p50":2.2,"p90":9.6},"R90_m":{},                     // FS-3/R1
     "delta_rb_ground_m":{},"resolved_ghost_modes":["W1","G3"],"fresnel_limited_d_m":{}}},

 "prior_compare":[{"source":"","range_m":0,"range_kind":"","illuminator":"","tx_power_w":null,
   "eirp_dbm_est":null,"cpi_s":null,"target":"","ground_included":true,"note":"","url":""}],

 "figures":[],"gifs":[],"stills":[]
}
```

`report13_sigma_grid.json`(6.1)·`verify_freespace.json`(6.3)은 확정 설계 스키마 계승 + 추가: sigma_grid.meta.el_deg=음수9점, `counterfactual_common_carrier`, `perturbation`, `sigma_confidence`; verify에 `fs0_mode_snr90_spread_db`(R8), `snr_convention_consistency`(R3§5), `ground_2ray_check`(R1), `nyquist_fold_check`(F8), `supp_phi_gate`(R7).

---

## 11. 그림 사양 (16개)

전부 `outputs/figures/report13_*.png`, `viz_report2._save(fig,name,caption)`(dpi130·tight·흰배경·회색캡션). **그림 텍스트 전부 영어**, 캡션 한국어. 모든 캡션 반복표기: (a) which SNR (b) 거리축(d/R2/R_b/**R_eq**) (c) 기준채널모델 (d) EIRP·T_CPI (e) **φ=90°** (f) **소거깊이**. 5드론 축=target_extent 순.

| # | 파일 / 영문제목 | 축·색 | 무엇을 | JSON키 |
|---|---|---|---|---|
| F1 | `report13_geometry` — **"Passive bistatic geometry in free space — three ranges, one measurement"** | x,y[m]+z삽입, R1/R2/R_b/β, iso-R_b타원+Cassini oval | 챔버이탈 선언 | `curves.rb_ellipses,cassini` |
| F2 | `report13_budget_waterfall` — **"SNR budget at d = 1 km (bandwidth term is absent)"** | x=예산항목 y=누적dB, 9모드 | B항 없음을 눈으로 | `ranges..budget_terms_db` |
| F3 | `report13_range_bars` — **"Free-space detection range, Pd 0.9 @ Pfa 1e-4 — ideal cancellation (5 airframes × always-on trio)"** | y=5기종 x=**R_eq**[m], 막대=R90_C50, **채운 띠**=[C25,C50], **캡막대**=CI95(S9 분리), 메쉬 실루엣 인셋(재질색) | 헤드라인 | `ranges[*][*].R90_C50_m,R90_C25_m,R90_ci95_m` |
| F4 | `report13_coverage_curves` — **"Detection coverage C(d) and mean Pd — fraction of headings vs heading-averaged"** | x=d[log] y=0~1, `C(d)`실선+`E_ψ[Pd](d)`파선(S4), 5드론5색×3모드, C=0.8마커 | 단일거리 대신 커버리지+평균 | `curves.coverage_C_of_d` |
| F5 | `report13_sigma_grid_5` — **"RCS σ(az, el ≤ 0) — 5 airframes @3.5 GHz (looking up at the belly)"** | 5패널 **직교히트맵**(x=az,y=el[deg]음수,color=dBsm turbo DR25), <3λ 회색표시 | σ=(방위,앙각)함수, 극좌표 아님 | `sigma.grid` |
| F6 | `report13_sigma_to_range` — **"From an RCS distribution to a range distribution (pipeline estimator)"** | 상 σ CDF, 하 R_eq CDF + Swerling-1 QQ삽입(KS만), σ^¼ 화살표 | 파이프라인 추정량 밴드(S5) | `sigma.stats,swerling_fit` |
| F7 | `report13_heading_footprint` — **"Range vs target heading — aspect, Doppler blind and alias act on one axis"** | 극좌표 θ=ψ, r=R90[m], 5드론, 블라인드 r=0함몰, **앨리어싱 섹터 해칭**(F8) | 자세+도플러 하한·상한 동시 | `coverage.polar` |
| F8 | `report13_eirp_ladder` — **"Range scales as the fourth root of illuminator power; ADC & DPI-residual floors do not"** | x=EIRP20~90 y=R[log-log], 열잡음(기울기¼)+ADC(EIRP무관)+**DPI잔류 4선(40/60/90/∞)**(R5), 교차점 | 무엇이 벽인가 | `sensitivity.eirp,eca_depth_db` |
| F9 | `report13_elevation` — **"Looking up at the belly — σ vs (negative) bisector elevation, and where the headline sits"** | x=el 0…−20° y=σ[dBsm]&R90, **헤드라인 el≈−2° 마커**(S8), 보조축=d | 부호반전, 헤드라인 효과 작음 정직표기 | `sigma.stats,ranges..el_look` |
| F10 | `report13_cpi_walk` — **"Longer CPI buys R ∝ T^(1/4) — until range-walk (narrowest wall for widest band)"** | x=T_CPI[log] y=R90, T^¼+파형별 walk벽(수직파선), 벽오른쪽 빨간해칭 | 대역폭 서사 반전 | `sensitivity.cpi,walk` |
| F11 | `report13_walls` — **"Which wall binds? thermal / ADC / DPI-residual / walk, by band and baseline"** | x=L[log] y=R, 밴드3패널, thermal·ADC(DR{74,64})·**DPI잔류(60dB)**·walk 곡선, binding 색라벨 | **조건부 결론**(dpi_residual 포함) | `dynamic_range,sensitivity.baseline,eca_depth_db` |
| F12 | `report13_matrix` — **"R90 matrix — 5 airframes × 9 modes (equal-PSD | deploy-EIRP)"** | 2패널 히트맵, 셀[m], G1이 배치서 무너짐 정직 | 점유·배치, F1/F2 반영 | `ranges[*][*].equal_psd/.deploy` |
| F13 | `report13_detector` — **"Measured Pd(SNR) + empirical Pfa + doppler-offset dependence"** | (a)Pd 9모드+Wilson CI+**CA-CFAR Marcum점선**(R3§4) (b)경험Pfa vs 명목 (c)dopoff별 곡선(R3§1) | 문턱 측정, 도플러위치 의존 | `detector_transfer` |
| F14 | `report13_verify` — **"Verification — closed form vs measured, ECA floor (ridge=0), bisector vs multistatic"** | (a)k_mode잔차 (b)**ECA잔류 vs DNR × ridge{0,1e-6,1e-4}**(R6 증거) (c)Δσ(β) | 믿는 이유와 경계 | `verify.*` |
| F15 | `report13_resolution_vs_range` — **"Bandwidth buys location, not detection"** | x=ΔR_b=c/B y=R90, 9모드 | report05 자유공간판 | `waveforms[*].d_rb_m,ranges` |
| F16 | `report13_chamber_vs_freespace_and_ground` — **"Where reports 01–12 sit, and what a flat ground would do"** | R_b 단일로그축, 챔버창(≈22m)↔FS-1 R90↔**FS-3 F⁴밴드**(R1) | 13편 중 위치 + 정직성 | `meta.chamber_reference,ranges,sensitivity.ground_2ray` |

(부수: `drone_size_compare.png` 재인용 시 target_extent 순서 주의 — 기존자산은 mavic·phantom 오배치, 캡션에 정정.)

---

## 12. 렌더·GIF 사양

**규약**: `scene_build.build_scene(드론parts만)`/`render_rt.make_scene(with_chamber=False)`, `clip=None`, **`render_rt.CAMS` 금지**(챔버 하드코딩), 프레이밍 `span·r=span×1.12·fov35°`. PNG=`viz_report1._whiten()`, GIF=신규 `render_report13._gif_white()`(프레임별 흰합성 후 조립, `render_rt.make_gif` **수정금지**). 프레임디렉토리 `render_anim._framedir()`로 먼저 비움. `gpu.pick()` mitsuba import 전. **모든 RT 프레임에 (a) 1 m 스케일바 (b) 스케일브레이크 장면은 프레임 내 영문 "scale break"** 강제(`_scalebar()`). 해상도상한 ≤1920×1280@spp512·≤1600×1200@spp1536(★2560×1600×4096 OOM). GIF ≤8.2 MB.

| # | 파일 | 장면/카메라 | 프레임·해상도·spp·ms | 보여주는것 |
|---|---|---|---|---|
| R1 | `r13_five_lineup_orbit.gif` | 전 기종 동일축척 1열(간격=span×1.4, **target_extent 순**), 궤도 r=전체span×1.3 fov40°, 1m스케일바 | 48f·1600×900·spp512·ms90 | 전 기종 메쉬+재질색+실제크기대비 |
| R2 | `r13_aspect_<key>.gif` ×기종수 | 좌:RT 드론yaw0→360°(프롭위상), 시선고정 el=el_look(음수). 우:σ(ψ)극좌표다이얼+R90(ψ)지침+블라인드섹터음영 | 기종당24f·좌900×900 spp256·fps10 | **전 기종 메쉬 각각 전용** |
| R3 | `r13_geometry_orbit.gif` | 자유공간 바이스태틱(TX마스트25/RX3/표적, L500, 바닥·벽 없음), 1m기준판+스케일바 | 48f·1600×1100·spp512·ms90 | 챔버 사라진 순간 |
| R4 | `r13_scale_zoom.gif` | powers of ten: 20km평면(Cassini)→500m베이스라인→60m고도→1m메쉬, 마지막8f만 RT, 매프레임 스케일바+"scale break" | 40f·fps6(RT8f·1280×860 spp256) | 렌더 스케일문제 정면 |
| R5 | `r13_coverage_grow.gif` | matplotlib EIRP20→90 커버리지등고선 성장, 벽닿으면 정지+조건배지("DPI-limited @depth 60dB") | 32f·1200×900·fps5 | F8/F11 동영상판, **배지에 조건** |
| R6 | `r13_rd_recede.gif` | matplotlib 실MC RD맵(turbo DR45), d=200m→5km, CFAR히트 소멸 | 30f·1100×700·fps8 | 검출 실패 장면 |
| R7 | `r13_cpi_walk.gif` | matplotlib T_CPI56ms→1s, 피크가 walk벽서 거리축 번짐 | 24f·1100×700·fps5 | 적분 늘리면 틀림 |
| R8 | `r13_cassini_baseline.gif` | matplotlib L50→3000 스윕, Cassini 단일→이엽 + β>90°해칭 | 36f·1100×900·fps8 | 기하가 커버리지 접음 |

**스틸 = 3·N + 7 장**(N = `len(DRONES)`; `outputs/renders/r13_*.png`, 1600×1200@spp1536):
- `r13_10_<drone>_aspect_{best,median,worst}.png` **3·N 장** — 자세각은 σ격자 JSON p90/p50/p10 az서 읽어 결정
- `r13_20_five_row.png` — 전 기종 동일축척(target_extent 순). 파일명의 `five` 는 5종 시절 유래
- `r13_30_geometry_schematic.png` — TX마스트·RX·표적(스케일브레이크 명시)
- `r13_40_<drone>_material.png` ×3(mini5pro/matrice4e/s1000plus=σ최소/중/최대)
- `r13_50_belly_vs_top.png` ×2 — 같은기체 el=+15° vs −15°(F9 시각근거)

**기존자산 재사용(재생성금지)**: `outputs/renders/anim/spin_{전 기종}.gif`, `drone_gallery_row.gif`, `drone_size_compare.png`.

---

## 13. make_notebook13.py 절 구성 (각 절이 읽는 JSON키)

`provenance_cells(report="report13", spine="visual-first + physics/story/fairness 접목", caveats=[§15])`. 숫자 전부 f-string 주입.

| 절 | 내용 | 읽는 키 | 그림/GIF |
|---|---|---|---|
| §0 왜 챔버 벗어나나 | FS 사다리, 상한선 철회 | `meta.assumption_ladder,chamber_reference` | F1,F16,R3 |
| §1 거리가 셋 | R1/R2/R_b/R_eq, Cassini | `curves.rb_ellipses,cassini` | F1,R8 |
| §2 표적 | 5기종 target_extent순, σ=함수 | `meta.drone_order,sigma.grid` | R1,R2,F5 |
| §3 언제 보이나 | Pd0.9 측정, dopoff, argmax아님 | `detector_transfer` | F13 |
| §4 몇 m | R90_C50 + E_ψ[Pd] 병기, 5G꼴찌 | `ranges` | F3,F12 |
| §5 왜 밴드 넓나 | σ 파이프라인추정량, R_eq축 | `sigma.stats,sensitivity.az_smoothing` | F5,F6,F7 |
| §6 무엇이 거리정하나 | EIRP¼·T¼·점유·λ²·L·N·**소거깊이·INR** | `sensitivity.*,walk` | F8,F9,F10,F11,F15 |
| §7 믿어도 되나 | 잔차·경험Pfa·ECA바닥·멀티스태틱·FS-3·챔버되돌리기 | `verify.*,sensitivity.ground_2ray` | F13,F14,F16 |
| §8 말할수없는것 | §15 전량 | `meta.assumptions` | — |

각 절 상단 headline 문장(§1.1) f-string. 5G 이중고·소거깊이·φ=90°·which SNR 반복.

---

## 14. 계산량·GPU 배치

| 단계 | 규모 | 카드 | 시간 |
|---|---|---|---|
| σ격자 | 48,600 az-eval @div16 + 공통반송파 반사실 | ★0.30~0.45 s/az-eval(div16) → 1장 4~6h | **3~4장 ~1.5h** |
| 멀티스태틱 | 5×3밴드×7β×24az(조명재사용) | 1장 | ~15min |
| 문턱 MC | 2형상×9모드×N{1,4}×5 dopoff×25 SNR×K4000 + Pfa K20000 | ★1.5~2.3ms/trial(NR6.88M CPI, batch16~32, peak3.5~7GB) | **1~2장 2~4h**(SSB M=5는 훨씬 쌈) |
| ECA바닥 스윕 | DNR11×ridge3×ntaps3×3파형(최대 n_range) | CPU | ~15min |
| 거리역해·감도·FS-3·INR·소거깊이 | 5×9×3뷰×2ref×4N×72φ×360ψ 최외곽교차 | CPU numpy | ~15min |
| 그림16+matplotlib GIF4 | — | CPU | ~15min |
| RT스틸22+GIF4(≈290프레임) | 1600×1200@1536 / 1600×900@512 | 1장 | ~60min |

**GPU 방침**(메모리 [[sionna2-gpu-policy]] 준수): `gpu.pick()`/`parallel_over_gpus`로 여유2GB↑ 카드 전부 침투(현재 GPU0·GPU2 유휴, GPU3 사용중 — SIONNA2_GPU 고정 안 함, pick이 회피). `nvidia-smi` 보며 `SIONNA2_DET_BATCH`로 배치 실시간 조절(유휴카드 90% 목표). 렌더 개당~1GB이라 큰배치실험 병행. σ격자·MC는 기종/모드 증분저장(재시작 가능). ⚠2560×1600×spp4096 OOM 회피.

---

## 15. 말할 수 없는 것 (살아남은 한계 — 전량 보존)

`caveats=[...]`와 본문 `> ⚠️` 양쪽.

1. **"실제 검지거리 N m"라고 말할 수 없다.** EIRP·G_rx(10dBi)·NF(5dB)·마스트25m·RX3m·고도·속도 **전부 선언값**, 근거문서 없음(코드주석이 유일). 결과는 "선언한 예산 아래의 거리".
2. **이 편만 FS-1이다 — 챔버 상한선 아니라 기준정규화.** ★R1로 정정: 자유공간은 상한도 하한도 아니다. 평면지면만으로 F⁴∈[−20,+11.5]dB(거리 0.32~1.94배) 변조(FS-3). 실외는 클러터·다중경로·간섭까지 더해 이보다 **다를** 뿐 반드시 나쁘진 않다.
3. **낙관 방향(정정판)**: (a) 무클러터·무지면(FS-1)은 상한 아님 — FS-3가 방향 보임. (b) 기준채널=무잡음 full-waveform(현실 2채널 CAF 아님). (c) 비요동은 **CPI 내부**만 — inter-look 요동은 `E_ψ[Pd]`로 정량화되어 이미 포함(S9). (d) SBR+PO few-λ 낙관.
4. **σ 절대값 ±수 dB 앵커.** 격자불확실성±1.5(jitter2 ~0.2 억제), 편파 없음(스칼라|Γ|), PTD·크리핑파 없음. **Mavic4Pro·Matrice4E 실측RCS 문헌 없음.** ★신뢰도가 (기종×밴드)마다 다름(mini5pro@LTE 2.32λ 최악) — 균일±3dB 못 덮음, D/λ 지도로(F15). (드론×밴드) 독립섭동으로 순위안정 검사.
5. **널깊이·σ_min·aspect-peak 인용 금지.**
6. **바이스태틱 σ는 β≲90°만 유효**(전방산란 σ≡0). 근거리·큰L(★L500·d150→β115.8°) 걸림 — 해칭·수치금지. 상반성 깊은널 rms5~9dB.
7. **ECA는 무한이상화 아니다 — ★방향 정정판.** report13 정본 `ridge_rel=0`은 ★측정상 사실상 이상적(잔류≈0). 설계 원안 1e-6은 **오히려 나빴다**(누설). **진짜 낙관**: 실장ECA·아날로그소거 유한소거깊이(통상40~90dB)·위상잡음·상호변조는 모델에 없다 → `dpi_residual` 감도축으로 정량화(★소거60dB서 헤드라인 LTE×0.41). `eca_depth_required_db`는 요구량이지 달성치 아님.
8. **ADC는 1차근사.** 균일양자화+백색. AGC·SFDR·상호변조 미모델. PAPR백오프·억압은 선택값이라 스윕. **"12-bit가 벽"이라 단정 안 하는 이유** — 조건부(백오프·억압·밴드·fs선택에 걸림, F12).
9. **검출기 형상 둘·성격 다름.** S-G(게이트)=탐색없는 거리, S-W(전체창)=탐색하나 CPI당 오경보 수(분해능셀 기준 ★G1 2.88). 헤드라인 S-G+S-W 병기. 검출정의=표적근방 문턱초과(전역argmax 아님, S4/R3§2).
10. **N^¼ 이득은 이상적 상한**(완전코히런트·완벽조향·무상관·무상호결합). 개구는 밴드마다 다름(F16).
11. **기준=full-waveform capture 정본** — 패시브인데 상시신호만은 아니라는 유보 승계. pilot-only 병기(★W3 24dB 거리4배, W1은 거의 같음 −3.27dB).
12. **CAF 2채널 승격 안 함** — 이상적 레퍼런스 정합필터 SNR(report12 동일 열린과제).
13. **문헌 실적치와 우열비교 안 함.** `prior_compare` 조건열 강제.
14. **호버·저속·앨리어싱 미검출은 거리무관.** ★유휴5G SSB(PRF50Hz)는 v=5m/s 전헤딩 접힘 — 거리이전에 도플러로 죽는다(F1/F8). 하한 hover-blind + **상한 나이퀴스트** 둘 다.
15. **자세=수평(roll=pitch=0)·yaw만.** 실전진비행 pitch10~30° 미모델 — **모른다.**
16. **el 격자 보간**: el≤−15°는 β>90° 겹쳐 표본적음·신뢰낮음. ★헤드라인 el≈−2°라 부호정정 효과는 헤드라인서 작다(d≲400m 한정, S8). `el>0`(공중조명원) 범위 밖.
17. **원거리장**: ★s1000plus@5.21G 63.1m 최악. D정의(bbox vs 대각) JSON 명기. 그 아래 σ 인용안함.
18. **"5기종×9모드 한 규약 선행사례 확인못함"까지만** — 부재증명 아님, "최초" 안 씀.
19. **단일CPI·단일표적.** 스캔누적·M-of-N·트래킹 없음(future work 1줄). 상호그림자 없음.
20. **대기감쇠·전파수평선은 숫자와 함께 무시**(FS-1에선 항 자체 없음, FS-3서만): 1.8~5.2GHz 산소흡수≈0.01dB/km→5km<0.1dB, RX3m+표적60m 수평선≈39km≫20km. "이만큼이라 무시".
21. **비단조·천장(★신규, S6).** SNR(d)는 φ의 다수서 내부최대 — 이분법 무효, 최외곽교차로 해결. `snr_ceiling_db`보다 어두운 헤딩은 **어떤 거리서도 미검출**(`frac_never_detectable`) — 거리문제 아니라 해 없음.
22. **비선형(★신규, S1).** R∝σ^¼는 `R_eq`축서만 정확. `d`축 국소지수 1.03~4.00 — dB↔배율 환산 금지. k_mode(곱셈상수)는 이 기하 비선형 흡수 못함.
23. **동일채널 간섭(R9)** 한 항으로 거리 한자릿수 감소 가능(★INR20dB 이웃셀) — 감도축으로만 냈고 정본엔 미포함.
24. **파형↔반송파 결속(F10).** 등전력만으론 파형효과 미분리 — 공통3.5GHz 반사실로 5항 분해했으나, "어느 파형이 멀리 보나"는 밴드·σ(f)·반복률·fs선택의 합성임.

---

## 16. 구현 순서 (의존성)

1. **`src/freespace_scene.py`** (순수함수, 의존 0). → 단위테스트: β/el/f_d 부호가 `bistatic_scene`와 일치, ★표(L500: alt60·d150→β115.8°/el−17°) 재현.
2. **`src/freespace_link.py`** (1 의존). → `solve_range` 최외곽교차·천장·n_local 단위테스트(★φ0/10/30 비단조, ceiling+24.7dB@d452).
3. **`src/freespace_detect.py`** (1 의존, `passive_process`/`detection_gpu` import). → ECA ridge=0 잔류 스모크(★≈0dB), `_cfar_excl_rows`, dopoff 전이곡선.
4. **`src/experiment_freespace_sigma.py`** (1 의존, `channel.sbr_sigma_prefill` 재사용) → `report13_sigma_grid.json`. **먼저 실행**(GPU 3~4장 ~1.5h). el 음수9점, div16, 멀티스태틱, D/λ, 공통반송파, 섭동.
5. **`src/experiment_freespace_range.py --stage=all`** (1·2·3·4 + `experiment_detection` import, 전역상수 인스턴스 전 교체) → `report13_freespace.json`. FS-0(9모드 SNR90 동일성)→FS-1→FS-2→FS-3. (GPU 1~2장 ~2~4h)
6. **`benchmark/verify_freespace.py`** (2·3·4·5 의존) → `verify_freespace.json`. 상수 9모드 재측정·닫힌형대조·ECA바닥·멀티스태틱·나이퀴스트폴드·FS-0검정·챔버되돌리기.
7. **`src/viz_report13.py`** (5·6 JSON만) → F1~F16 + GIF R5~R8. (CPU ~30min)
8. **`src/render_report13.py`** (4 JSON서 자세각 읽음, mitsuba) → RT GIF R1~R4 + 스틸22. (1장 ~60min, 5·7과 병행가능)
9. **`src/make_notebook13.py`** (5·6·7·8 산출물) → `report13.ipynb`. 숫자 전량 f-string.

**문서수정(별도승인·이번범위 밖)**: `README.md`(12→13편, "모든실험 챔버안" 인용블록에 **FS-1 예외 한 줄**, 표 report13행, 빌드루프 01..13), `docs/REPORT_CODE_MAP.md`(13행·새모듈·JSON3개 등재), `docs/EIRP_CLASSES.md` 신설(선언값 provenance).

**게이트(통과조건)**: FS-0 9모드 SNR90이 CI 안에서 동일(R8) · ECA ridge=0 잔류 p99≤noise+0.5dB(R6) · 닫힌형↔측정 |Δ|<0.5dB(§2.5) · solve_range 비단조 φ에서 최외곽교차 검증(S6) · SSB M=5·PRF50 반영(F1) · 전력 3뷰 산출(F2). 하나라도 실패시 해당 stage JSON에 실패 기록하고 회색 처리(축 안 자름).