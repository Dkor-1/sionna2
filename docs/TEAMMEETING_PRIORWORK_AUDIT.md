# 팀미팅 덱 선행연구 주장 감사 — 정정 목록 정본

> 2026-08-03. 팀미팅 덱 5편이 **남의 논문에 대해 한 주장**을 전부 뽑아 원문과 축자 대조한 결과다.
> ⭐ **이 문서는 "무엇을 잘못 적었나" 의 정본이다.** 덱을 새로 만들 때 §3·§4·§8 을 먼저 읽는다.
> 우리 자신의 결과에 대한 철회는 여기가 아니라 [`RETRACTION_LOG.md`](RETRACTION_LOG.md) 가 정본이다.
> 중복되는 항목은 그쪽을 가리켰다(§9).

원자료: `outputs/tm_claims.json`(주장 추출) · `outputs/tm_verify_rest.json` · `outputs/tm_verify_clutter.json` · `outputs/tm_verify_openisac_montaner.json`(검증)

---

## 1. 감사 범위

**덱 5편** (python-pptx 로 모든 도형·표·발표자노트까지 추출)

| 덱 | 파일 | 주장 수 |
|---|---|---|
| 0623 | `teammeeting_0623_v26.pptx` | 71 |
| 0630 | `teammeeting_0630_v36.pptx` | 44 |
| 0714 | `teammeeting_0714_v14.pptx` | 22 |
| 0721 | `teammeeting_0721_v17.pptx` | 18 |
| 0728 | `teammeeting_0728_v30.pptx` | 42 |
| | **합계** | **197** |

우리 자신의 작업에 대한 서술은 제외했다. **남의 논문·도구·표준에 대한 사실 주장만** 셌다.

**주장 유형 197건**

| 유형 | 정의 | 건수 |
|---|---|---|
| `capability` | 선행연구가 **했다/가진다** | 84 |
| `absence` | 선행연구가 **안 했다/없다/우리만** (배타·전칭 포함) | **43** |
| `venue` | 서지 주장(제목·연도·게재지) | 31 |
| `number` | 선행연구·표준에 귀속시킨 수치 | 24 |
| `quote` | 위치자(그림·표·식)와 함께 인용 | 15 |

**논문 34편**(코퍼스 총칭 1건 포함). **그중 33편은 원문 PDF 를 손에 놓고 대조**했다.

- LTE 패시브 7편 · 5G 패시브 7편 · Wi-Fi 패시브 6편 → `/data/public/jeong/papers/`
- Sionna 계열 3편(기술보고서·창설논문 2편) + 0721 랜드스케이프 5편(LAMBDA·Temporal-GNN·Great-X·CISSIR·Ziganshin)
- 0728 신규 2편: Clutter-aware ISAC 서베이(Proc. IEEE) · OpenISAC(IEEE IoT-J)
- Montaner RF-DT(EuCAP 2026 채택 프리프린트)
- 3GPP 38.211 / 38.331 원문 docx

**대조 못 한 논문 1편**: 0714 의 PWC-Diff(ICML 2026 Spotlight). PDF 가 디스크 어디에도 없다 → 그 덱의 20건 전부 판정 불가(§6).

**추가로 검증한 것**: 덱 밖의 우리 내부 기록도 같이 걸었다 — `docs/RESUME.md`, `docs/READING_2607_NOTES.md` 의 수치·인용 25건. 덱에는 없지만 다음 덱으로 흘러들어갈 문장들이라 함께 판정했다.

**총 판정 건수 = 197(덱) + 25(내부 기록) = 222건.**

---

## 2. 판정 요약

| | 덱 주장 197 | 내부 기록 25 |
|---|---|---|
| ✅ 원문 지지 | 149 | 19 |
| ❌ **틀림** | **19** | **6** |
| ⚠ 부정확(방향은 맞으나 표현·수치·귀속이 안 받쳐짐) | 16 | — |
| ❓ 대조 불가 | 27 | 0 |

⭐ **핵심 통계 하나**: 부재주장 43건 중 **12건(27.9%)이 틀렸다.** 나머지 유형 154건 중에서는 7건(4.5%)만 틀렸다.
**부재주장은 다른 주장보다 6배 넘게 틀린다.** (§5)

---

## 3. ⭐ 틀린 것 전부 — 덱 (19건)

> 형식: **어느 덱 몇 번 슬라이드 · 무엇이 적혀 있나 · 옳은 값은 무엇인가.**

### 0623 (7건)

**W1 · 0623 s4 발표자노트** — `"all of the paper did their experiment at outdoor, including 5G and Wi-Fi papers"`
→ **거짓.** Lin 외(5G Spectrum Learning, IEEE/CIC ICCC 2023)는 **실내 장면을 명시**했다: *"Two different scenes are considered: i) indoor scene with an experimental 5G base station, and ii) outdoor scene with a commercial 5G base station"*, *"the UAV is about 5 ~ 10 meters away from USRP-B210"*, 기체는 **DJI Phantom 4**(p.4). Fig. 5 캡션이 *"Outdoor (left) and indoor (right) scenes"* 다.
→ 옳은 문장: **"조사한 논문 중 실내 장면은 Lin 2023 한 건뿐이고, 그마저 실험용 기지국이 있는 실내이지 무향실이 아니다."**

**W2 · 0623 s6 발표자노트** — `"The Wi-Fi papers are again very detection-focused, so the pattern holds across all three signals"`
→ **거짓이고, 같은 덱의 자기 표와 모순된다.** 그 표가 Milani 외 2021 을 `Tracking` 으로 적어놨다. 그 논문은 IMM 필터로 추적한다(*"a modified version of the Interacting Multiple Model (IMM) tracking algorithm"*). Martelli 외 2017 도 3D 측위 + *"a conventional Kalman tracking algorithm"* 이다.
→ 옳은 문장: **"Wi-Fi 논문 6편 중 4편이 검출에서 멈추고, Martelli 2017 과 Milani 2021 은 각각 칼만·IMM 추적까지 간다."**

**W3 · 0623 s7 표 (두 오류)** — `"RTK / DGPS (cm)" — "Only LIPASE & LaSen — the 2 tracking papers"`
→ (a) **LIPASE 는 cm 가 아니다.** 원문(OJ-COMS 2025 p.10): *"the drone is equipped with an additional differential GPS (DGPS) module ... such that **sub-meter** localization accuracy can be achieved"* → **서브미터**.
→ (b) **"2편" 이 아니다.** 덱 자신의 표에 추적 논문이 **세 줄**(LIPASE, LaSen, Milani 2021) 있다.
→ 옳은 문장: **"정밀 GT 는 두 등급이다 — LaSen 은 RTK cm 급, LIPASE 는 DGPS 서브미터급."**

**W4 · 0623 s8 표 (선행연구 / Flight 칸)** — `"Single casual pass"`
→ **거짓.** Taylor & Poullin(TAES 2025): *"For flights 2 and 4, the trajectory of the drone is similar to that of flight 1, and flights 3 and 5 also share similar drone trajectories"*. LaSen: *"over 1335 range-velocity estimates across 35 separate trajectories"*. Martelli 2017: *"the drone is remotely piloted to fly specified test trajectories"*.
→ 옳은 문장: **"반복 궤적을 쓰는 논문이 있다(Taylor&Poullin 2025 는 5비행 중 4개를 짝지어 반복). 우리 차별점은 반복 자체가 아니라 반복을 신호 3종에 걸쳐 동일 기하로 건다는 것이다."**

**W5 · 0623 s8 표 (선행연구 / Evaluation 칸)** — `"It shows up (qualitative)"`
→ **거짓.** Abratkiewicz 2022(Rényi)는 CFAR 곡선과 함께 Pd/Pfa 전면 분석(‘probability of detection’ 10회, ‘false alarm’ 11회). LIPASE 는 DGPS 대비 RMSE, LaSen 은 RTK 대비 *"Root Mean Squared Error (RMSE), Composite Error (CE), and Detection Rate (DR)"*, Milani 2021 은 RMSE + 검출확률을 인쇄한다.
→ 옳은 문장: **"정량 평가를 하는 논문이 최소 4편 있다. 없는 것은 정량 평가가 아니라 세 신호를 같은 조건에서 놓고 비교한 표다."**

**W6 · 0623 s10 발표자노트** — 우리가 고른 지표(RD-map visibility, SCR, detection rate, false-alarm rate, RD-peak stability)가 `"the same ones the papers use"`
→ **5개 중 2개가 거짓.** RD/CAF 맵·SNR·Pd/Pfa 는 실제 코퍼스 지표다. 그러나 **SCR 을 보고 지표로 쓴 논문은 21편 중 0편**(3편에 우발적 언급뿐), **RD-peak stability 는 0편**이다.
→ 옳은 문장: **"RD 맵·SNR·Pd/Pfa 는 선행연구 지표를 그대로 쓴다. SCR 과 RD 피크 안정도는 우리가 챔버 비교를 위해 새로 도입한 지표다."**

**W7 · 0623 s13 표(Literature 행)** — `"Phantom 3 / 4 / 4 RTK"`
→ **`4 RTK` 가 거짓.** 조사 코퍼스에 **Phantom 4 RTK 를 쓴 논문은 없다.** 실제는 Phantom 4(Dan 2019, Lin 2023)와 Phantom 3(Taylor&Poullin 2023·2025) 뿐이다.
→ 옳은 문장: **"Phantom 3 / Phantom 4."**

### 0630 (7건)

**W8 · 0630 s2 발표자노트** — `"the literature survey showed that most of the paper focused on detection without ground truth"`
→ **거짓이고, 0623 s7 의 자기 표와 모순된다**(그 표는 `Onboard GPS (~m) — Most LTE & 5G papers` 라고 적었다). GPS GT 를 인쇄한 검출 논문: Dan 2019(비행기록), Taylor&Poullin 2023·2025(GPS GT 곡선), Demissie 2024(GPS 로거), Abratkiewicz 2022(GPS 로거), Maksymiuk IRS 2023(GPS 로거), Maksymiuk Asilomar 2025(*"confirmed by the reference GPS position"*).
→ 옳은 문장: **"대부분은 GT 가 없는 게 아니라 GT 등급이 낮다 — 기체 GPS 로그를 정확도·동기 논의 없이 겹쳐 그린다."**

**W9 · 0630 s2 발표자노트** — `"only two papers that was about the tracking showed GT"`
→ **거짓.** 추적 논문은 셋이고 셋째도 GT 를 보여준다. Milani 2021 p.20: *"Its path (the ground truth) is shown in Figure 15 by the red quadrilateral polygon that was obtained from the drone's GPS data"*.

**W10 · 0630 s10** — `"Tracks low-altitude drones (range + velocity) on the live 5G downlink"`
→ ⭐ **거짓. 이 감사에서 가장 파급이 큰 오류다.** LaSen 의 드론 에코는 상용 다운링크에서 잡은 것이 **아니라 LaSen 자신의 USRP 송신기**에서 온다. §6.1.1: *"During flying, LaSen continually transmits NR signals with full resource allocation while simultaneously activating the receiver for capturing ... the 'full-band' mode"*. 파형은 MATLAB 으로 만든 **PDSCH + DM-RS**(§5). 실제 gNB 는 **점유 마스크 통계로만** 들어온다: *"We capture and demodulate 2200 data frames from two China Mobile N41 band gNBs ... resulting in a binary mask indicating the RE occupation pattern. The final channel frequency response was obtained by performing element-wise multiplication between the full-band drone measurements and the derived occupancy masks"*.
→ 옳은 문장: **"LaSen 은 자기 USRP 로 풀밴드 NR 을 쏴서 에코를 얻고, 실제 gNB 캡처는 RE 점유 마스크를 만드는 데만 쓴다 — 즉 모노스태틱 능동이고 상용 다운링크 패시브가 아니다."**
⚠ 이건 메모 `sionna2-lasen-monostatic` 과 같은 방향이지만, 여기서 **원문 축자로 확정**됐다.

**W11 · 0630 s10** — `"Reuses reference signals (CSI-RS / SSB) and data signals (PDSCH)"`
→ **거짓.** LaSen 추정기가 쓰는 것은 **PDSCH + DM-RS** 다(§5). CSI-RS 와 SSB 는 **동기부여**(200 Hz / 50 Hz 반복률이 느리다)로만 나오고, SSB 는 추가로 마스킹 문턱으로만 쓰인다: *"We use the maximum power within an SSB group as a threshold T_ssb"*. **LaSen 은 CSI-RS 나 SSB 에서 추정하지 않는다.**

**W12 · 0630 s10 그림 캡션** — `"UAV echoes off a live gNB downlink (LaSen Fig. 1)"`
→ **두 겹으로 거짓.** LaSen Fig. 1 의 실제 캡션은 **`"A UAV sensing scenario of LaSen"`** 이고, 내용도 live gNB 다운링크가 아니다(W10).

**W13 · 0630 s15** — `"The limit — earlier 5G sensing: Only the sparse pilots → too few samples (sub-Nyquist) → the track keeps breaking up"`
→ **우리 코퍼스에 대해 거짓.** 우리가 조사한 5G 패시브 논문들은 파일럿만 쓰지 않는다 — **레퍼런스 채널 전체를 서베일런스와 상호상관(CAF)** 한다. Abratkiewicz 2022(CAF 22회 언급, 레퍼런스/서베일런스 채널 모델), Maksymiuk IRS 2023(CAF 12회, *"xref — baseband digitized reference signal"*), Maksymiuk Asilomar 2025(*"the radar receives the direct wave through a reference channel"*). 그들이 말하는 한계는 **파일럿 희소성이 아니라 유휴·저점유 시간**이다.
→ 옳은 문장: **"파일럿만 쓴다는 한계는 LaSen 자신의 모노스태틱 비교군(CSI-RS/DM-RS/PRS 기반 연구들)의 성질이지, 패시브 5G 코퍼스의 성질이 아니다. 패시브 쪽 한계는 다운링크 점유율이다."**

**W14 · 0630 s15 발표자노트** — `"...gets continuous tracking on a live 5G downlink with no extra spectrum"`
→ 앞 절반(*"LaSen formulates the tracking of UAVs as a sparse recovery problem"*)은 **축자 정확**. `on a live 5G downlink` 는 W10 과 같은 거짓.

### 0721 (4건)

**W15 · 0721 s12 본문** — `"Sionna returns only a path gain for the drone — it never integrates the scattering over the target surface"`
→ **앞 절반 거짓.** Sionna RT 는 경로이득만 주지 않는다. 복소 전계/채널 계수를 준다. 기술보고서 **식 (168)**: *"the diffusely scattered field Es(r) at the observation point r can be modeled as Es(r) = E_s,θ·θ̂(k̂s) + E_s,φ·φ̂(k̂s)"* — 위상 `e^{jχ1}`, `e^{jχ2}` 를 가진 복소 성분이다.
→ **뒤 절반은 참**: 결맞은 표면적분이 없다. 기술보고서 59쪽에 `physical optics` 0회, `Kirchhoff` 0회이고, 확산 모델은 패치별 산란계수/산란패턴(Lambertian·directive·backscattering) + 랜덤위상의 현상론 모델이다.

**W16 · 0721 s12 부제** — `"Even where rays hit, Sionna gives only a path gain, never a scattering integral — so no RCS, at any distance"`
→ W15 와 같은 결함. `never a scattering integral → no RCS` 부분은 살아남는다.

**W17 · 0721 s13 CISSIR 행** — `"CISSIR (NVIDIA) — sensed = no target · No target RCS at all · family = None"`
→ ⭐ **네 겹으로 거짓. 셀 세 개가 다 틀렸고 저자 귀속까지 틀렸다.**
 (a) **표적이 있다.** Table I.D: `Target azimuth −39°`, `Target distance 40 m`, **`Target radar cross section 1 m²`**, `Target RX power −81.0 dBm`. §V: *"we simulate a backscatter channel H(t) = S(t) + Hr(t) in a **single-target scenario**"*.
 (b) 따라서 **표적 RCS 가 있다** — 주입된 상수 1 m².
 (c) 계열은 `None` 이 아니라 **`Injected`(점표적)**. 광선추적은 **자기간섭 채널**에 쓰지 표적에 쓰지 않는다.
 (d) **`(NVIDIA)` 는 잘못된 귀속이다.** 저자는 Hernangómez, Fink, Cavalcante, Stanczak(Fraunhofer HHI / TU Berlin 계열)이고, 논문 안 NVIDIA 언급은 *"Sionna™, a Python library by Nvidia"* 한 줄뿐이다.
→ 옳은 행: **`CISSIR (Hernangómez 외, Fraunhofer HHI/TUB) — 표적 1개 @ 40 m · RCS = 주입 상수 1 m² · 계열 Injected · RT 는 자기간섭 채널용`**

**W18 · 0721 s13 테이크어웨이** — `"A few families — inject a number, tweak a material setting, no target, or extend Sionna-RT. We're the last: the only SBR+PO, and the only small drone"`
→ (a) **`no target` 계열은 비어 있다**(W17).
 (b) **`the only small drone` 은 덱 자신의 표와 모순된다** — 같은 표에서 LAMBDA 와 Great-X 가 둘 다 `low-alt UAV` 를 표적으로 적고 있다. LAMBDA 는 CADFEKO 로 UAV RCS 를 모델링하고, Great-X 는 *"realistic 3D UAV models"* 와 저고도 UAV 데이터셋을 배포한다.
 (c) ⭐ **`the only SBR+PO` 는 살아남는다** — LAMBDA=외부 솔버, Temporal-GNN=점표적, Great-X=재질 노브, CISSIR=주입 점표적, Ziganshin=UTD/정점회절. **PO 표면적분을 쓴 곳은 없다.**
→ 옳은 문장: **"이 표에서 SBR+PO 표면적분을 쓰는 것은 우리뿐이다. 소형 드론 자체는 LAMBDA·Great-X 도 다루므로 '유일'이 아니다."**

### 0728 (1건)

**W19 · 0728 s20 발표자노트(v30)** — `"the paper's expression is y = H_t x + H_c x + H_h x + z"`
→ **거짓.** 서베이 식 (8) (p.56):
 `y_n[l] = H^t_{n,l} x_n[l] + H^c_{n,l} x_n[l] + H^h_{n,l} s^ext_n[l] + z_n[l]`
 **핫클러터 항을 구동하는 것은 x 가 아니라 외부 방사원 신호 `s^ext`** 다. 그게 콜드/핫 구분의 전부이므로, `H_h x` 라고 쓰면 두 슬라이드 앞에서 가르친 분류를 스스로 지운다.
⚠ **v24 s25 의 노트는 맞게 적혀 있었다**(`s external`). **짧게 자른 v29/v30 에서 생긴 퇴행이다.**

---

## 4. ⭐ 틀린 것 전부 — 내부 기록 (6건)

> 덱에는 아직 안 들어갔지만 다음 덱으로 흘러가던 문장들이다. **0804 덱 서사에 이미 물려 있었다.**

**V1 · `docs/RESUME.md` L27, L184** — *"클러터 서베이가 16 dB 로 값어치를 증명"*, *"광선추적은 16 dB 짜리다(Proc. IEEE)"*
→ **서베이는 `16 dB` 를 인쇄하지 않는다.** 41쪽 전수 조사 결과 인쇄된 dB 값은 넷뿐이다: −47.4(Fig. 2, p.61), −45.9(Fig. 4, pp.73/74), −47.4(Fig. 5, pp.73/74), −63.5(Fig. 7, p.76). 논문 자신의 표현은 정성적이다 — *"the detection task is more challenging due to the much lower SCNR"*.
→ **16.1 dB 는 우리 뺄셈**(−47.4 −(−63.5))이다. `READING_2607_NOTES.md` L32 는 이걸 *유도값(축자 아님)* 으로 옳게 표시했는데, `RESUME.md` 가 단서 없이 헤드라인으로 승격시켰다.
⚠ 덤: **−47.4 dB 는 Fig. 2 와 Fig. 5 가 같은 값**이다. 어느 그림인지 안 밝히면 독립 데이터 2점으로 오독된다.

**V2 · 같은 자리** — 16.1 dB 를 *"통계모델 → 실제 RT 다중경로 페널티"* 라는 **인과**로 읽은 것
→ **거짓.** 두 장면 사이에 고정된 것은 **Table 3 의 배열·파형 설정뿐**이다. 통계 장면은 표적 거리를 사이에 둔 **4개 등거리 링 위 C=100 산란체**(p.73)에 Table 3 거리(ToI 41.8 m, UAV-1 53.2 m, UAV-2 55.4 m, 방사원 122.4 m), RT 장면은 **높이만 지정된 도시 3D 씬**(BS 13.5 m, 표적 10~15 m, 방사원 5 m)에 건물 후방산란 + 메시 표적이다. 즉 **씬·기하·표적모델이 한꺼번에 바뀐 델타**이고, 논문은 통제비교를 주장한 적이 없다.

**V3 · `docs/READING_2607_NOTES.md` L36, L81** — *"식 (112) 가 우리 ECA 죽은 파라미터 발견을 일반화한다"*
→ **방향이 반대다.** p.79 축자: *"Thus, f_D disappears from the **target** covariance in (109), and Doppler discrimination cannot be achieved using second-order statistics alone."* 잃는 쪽이 **표적**이고, 원인은 수신단이 심볼 대신 `R_X,n` 만 받았기 때문이다. 우리 발견은 정적 **클러터**가 안 보이게 된 것이고, 그 기전은 `VERIFY_CLUTTER.md` L180 에서 이미 **영도플러 노치**로 정정됐다. **다른 양, 다른 기전.**
→ 방어 가능한 축소형: **"서베이도 슬로타임 구조가 백색이면 2차 통계 처리에서 도플러가 판별자로 못 쓰인다고 독립적으로 적는다(p.79) — 우리 영도플러 노치 하네스가 정적 클러터를 못 본 것과 질적으로 같은 이유다."** 일반화·증명이라고 부르지 않는다.

**V4 · `docs/READING_2607_NOTES.md` L12, L74** — *"서베이는 모노스태틱이고 바이스태틱은 Remark 에만 나온다"*
→ **모노 절반만 참.** 시스템 모델과 **모든 시뮬레이션**은 모노스태틱이 맞다(p.54, p.74). 그러나 바이/멀티스태틱은 Remark 에 갇혀 있지 않다 — **Remark 1**(p.58), **Remark 3**(p.60), 그리고 **번호 붙은 소절 `4) Extension to Bistatic/Multistatic STAP`(pp.78–79)** 가 바이스태틱 공간-시간 조향벡터 식 (103) 을 정의하고 식 (104)~(114) 까지 전개한다. 멀티스태틱도 p.80 에 있다.
→ ⚠ **"패시브를 무시한다" 도 쓰면 안 된다.** Remark 3 이 명시한다: *"In non-cooperative or passive settings, coherent processing may rely on a reference branch that captures a strong direct-path copy of the illuminator signal, as commonly done in passive radar"*(p.60).
→ 옳은 문장: **"시스템 모델과 모든 시뮬레이션이 모노스태틱이다. 바이/멀티스태틱은 해석적으로만 다뤄지고(Remark 2건 + STAP 소절), 한 번도 시뮬레이션되거나 광선추적되지 않는다."** 우리 쐐기는 *"패시브 바이스태틱 RT 클러터 케이스스터디가 없다"* 이지 *"언급조차 없다"* 가 아니다.

**V5 · `docs/READING_2607_NOTES.md` L20, `docs/RESUME.md` L66** — *"Proc. IEEE 114(1):52–89, 2026"*
→ **쪽수 범위가 틀렸다. 52–92 다.** p.89 는 참고문헌이 시작되는 쪽이지 본문이 끝나는 쪽이 아니다(마지막 쪽 각주 `92 / PROCEEDINGS OF THE IEEE | Vol. 114, No. 1, January 2026`, `ABOUT THE AUTHORS` 가 p.92).
→ 같이 고정할 것: DOI **10.1109/JPROC.2026.3675476**, 접수 2025-11-07 / 게재 2026-03-27, arXiv 프리프린트 2602.10537.

**V6 · OpenISAC 실시간 한계 기록** — *"100~200 MHz 에서 host-only 실시간 붕괴"*
→ **거짓. 붕괴는 200 MHz 단독이다.** 축자(IoT-J §V-B, pp.12–13): *"the proportionally scaled 50 MHz and 100 MHz configurations are **stable operating points**, whereas the 200 MHz/4096-FFT configuration exceeds the real-time capacity of the current host-only demodulator path."*

| 샘플레이트 | 변조 시간/부하 | 복조 시간/부하 | RX 큐 드롭 |
|---|---|---|---|
| 50 MHz | 0.21 ms / 8.9 % | 0.81 ms / 35.3 % | **0** |
| 100 MHz | 0.42 ms / 18.1 % | 1.95 ms / **84.7 %** | **0** |
| 200 MHz | 1.1 ms / 47.8 % | 3.95 ms / **171.5 %** | **> 1600** |

⭐ **남는 진실은 다른 축에 있다** — **센싱 스레드**는 100 MHz/FFT1024 에서 stride `M_D=1` 이면 4개 모드 중 3개가 드롭하고, FFT+MTI 전처리 모드는 `M_D=2` 에서도 드롭한다. `M_D ≥ 5` 는 전부 무드롭(Table IV, p.13). **복조 경로는 100 MHz 에서 안정, 센싱 경로는 stride 로 산다.** 기록이 이 둘을 뭉갰다.
→ 옳은 문장: **"50/100 MHz 는 드롭 0 의 안정 동작점이고, 200 MHz/4096-FFT 에서 복조 부하 171.5 % · 드롭 1600+ 로 무너진다. 별도로 센싱 스레드는 100 MHz 에서 stride M_D ≤ 2 이면 드롭한다."**
⚠ **우리 X410 계획에 직결**: X410 은 400 MHz 급인데 OpenISAC 호스트 복조는 200 MHz 에서 이미 무너진다. 대역을 100 MHz 이하로 낮추거나 복조 경로를 손봐야 하고, X400 계열은 그 논문이 한 번도 안 돌려봤으므로 우리가 돌리면 **그 조합의 첫 실증**이다.

---

## 5. ⭐ 부재주장 판정 결과 — 가장 위험한 유형

부재주장 = *"안 했다 / 없다 / 우리만 / 전부 …다"*. 덱 5편에 **43건**.

| 판정 | 건수 | 비율 |
|---|---|---|
| ✅ 원문 지지 | 28 | 65.1 % |
| ❌ **틀림** | **12** | **27.9 %** |
| ⚠ 부정확 | 2 | 4.7 % |
| ❓ 대조 불가 | 1 | 2.3 % |

**대조군**: 부재 아닌 주장 154건 중 틀린 것 7건 = **4.5 %**.
→ ⭐ **부재주장의 오류율이 6.2배 높다.** 이건 우연이 아니라 구조다 — 부재주장은 **모든 논문을 다 확인해야** 참이 되는데, 실제로는 **몇 편만 보고 나머지를 추정**해서 쓴다.

**틀린 12건의 실패 패턴 세 가지**

| 패턴 | 건수 | 예 |
|---|---|---|
| **A. 코퍼스 전칭을 몇 편만 보고 씀** | 7 | W1(전부 실외), W2(Wi-Fi 전부 검출), W4(전부 1회 통과), W5(전부 정성), W8(대부분 GT 없음), W13(전부 파일럿만), W9(추적 GT 2편) |
| **B. 자기 덱의 자기 표와 모순** | 4 | W2·W8·W9·W18 — **표를 만든 다음 노트를 쓰면서 표를 안 봤다** |
| **C. "우리만" 배타주장** | 3 | W3(2편뿐), W17+W18(no target 계열·유일한 소형드론) |

⚠ **B 는 기계로 잡을 수 있다.** 노트에 전칭 부사(`all`, `most`, `only`, `never`, `none`)가 있으면 같은 덱의 표를 자동 대조하는 검사를 넣을 것.

⭐ **살아남은 부재주장은 하나같이 범위를 밝힌 것들이다.** 예: 0721 s13 노트 *"this is just what we found, not a claim that nothing else exists"*, 0630 s10 *"Only 5G paper **in my survey** that reaches tracking"*, 0721 s12 *"Sionna 는 SBR 은 있고 PO 적분이 없다"*. **범위구가 붙은 부재주장은 12건 중 0건이 틀렸다.**

---

## 6. 원문을 못 찾아 대조 불가한 주장 (27건)

### 6.1 논문 자체가 디스크에 없음 — 20건 (0714 덱 전부)

**PWC-Diff / "From Denoising to De-Channeling"** (Liu 외, ICML 2026 Spotlight, BUPT & Pengcheng Lab, `github.com/BUPT-GAMMA/FoundWSR`).
`/data/public/sionna_jeong`(371 PDF) · `/data/public/jeong` · `/data/public/OpenISAC` · `/home/yunjung/workspace` 전체를 훑어도 없다.

**따라서 다음 20건은 지금 아무 등급도 못 준다** — 0714 s14 서지 3건, s15 배경 2건, s16 방법 3건, s17 구조 4건, s18 수치 8건. 여기엔 **인용하면 곧바로 검증 대상이 되는 구체 숫자들**이 포함된다: RML2016 63.60 vs IQFormer 63.54 · TechRec 91.0 vs 88.8 · FusedFormer 무사전학습 57.77 · Gaussian-only 62.86 · RML2022 +5.7점 · TechRec 89.21 vs 90.25 · CFO 제거 시 63.6→61.5.

⚠ **규칙: PDF 를 구하기 전에는 이 숫자들을 어느 덱에도 다시 쓰지 않는다.** 쓰려면 `[미검증 — 원문 미확보]` 를 문장 안에 넣는다.

### 6.2 게재지 문자열이 PDF 에 안 찍혀 있음 — 7건

제목·저자·내용은 다 일치하지만 **PDF 자체에 게재지가 없어** 덱의 venue 셀을 원문으로 확인할 수 없는 경우(프리프린트/기관 레이아웃).

| 덱·슬라이드 | 덱이 적은 게재지 | 상태 |
|---|---|---|
| 0623 s4 | `IEEE RADAR` (Experimental UAV detection using 4G-LTE…, 2023) | ONERA 프리프린트 레이아웃 |
| 0623 s4 | `IEEE RADAR` (Protection of Critical Infrastructure … LTE450, 2024) | Fraunhofer FKIE 레이아웃 |
| 0623 s5 | `IEEE/CIC ICCC` (5G Spectrum Learning…, 2023) | 줄번호 붙은 투고본 |
| 0623 s5 | `IEEE SPAWC` (Utilizing 5G NR SSB Blocks…, 2025) | Linköping 프리프린트 |
| 0623 s6 | `Int. Conf. Radar Syst.` (Detection and 3D localization…, 2017) | 게재지 문자열 없음 |
| 0623 s6 | `IRS` (Human and Drone Surveillance via RpF…, 2022) | 게재지 문자열 없음 |
| 0623 s6 | `IEEE RadarConf` (OFDM based WiFi Passive Sensing…, 2023) | 게재지 문자열 없음 |

→ **틀렸다는 뜻이 아니다.** 다만 *"원문 확인"* 등급을 줄 수 없으므로, 서지가 쟁점이 되면 DOI/Xplore 로 따로 확인해야 한다.

### 6.3 준-대조불가: 게재지 근거가 PDF 밖에 있는 경우

**Montaner RF-DT (EuCAP 2026)** — 채택은 사실이나 **PDF 본문 어디에도 그 정보가 없다.** 손에 있는 파일은 arXiv:2603.28736v1(2026-03-30) 프리프린트로, DOI 없음·학회명 진술 없음·IEEE 저작권 각주 없음. 논문 안 `EuCAP` 문자열 1회는 **참고문헌 [4]**(Pascual-García 외, EuCAP 2015)이지 자기 게재지가 아니다. 실제 근거는 **arXiv abstract 페이지의 comments 필드**뿐이다: *"Accepted for publication at the 2026 20th European Conference on Antennas and Propagation (EuCAP)"*.
⚠ 팀미팅 파일명 `Montaner_EuCAP2026_...` 은 **PDF 로 검증되지 않는다.** 최종 EuCAP 판이 나오면 쪽수도 달라진다(현 쪽수는 arXiv v1 기준).
⭐ **대조군**: OpenISAC 은 정반대다 — 손에 있는 사본이 **IEEE Xplore 저널판**이고 15쪽 전면 각주에 `DOI 10.1109/JIOT.2026.3710751` 이 박혀 있다. **두 논문의 인용 신뢰도가 같지 않다.**

⚠ **판본 함정(OpenISAC)**: `team_meeting/2607/` 사본(IoT-J, 15쪽, DOI 있음)과 `/data/public/sionna_jeong` 아카이브 사본(arXiv:2601.03535v2, 16쪽, DOI 없음)은 **다른 파일**이다(md5 다름). 확인한 모든 항목에서 내용은 일치하지만 **쪽수를 섞으면 안 된다.** 인용 정본은 **IoT-J 판**으로 고정한다.

---

## 7. 틀리진 않았지만 문구를 고쳐야 하는 것 (16건 요약)

> 방향은 맞는데 **표현·수치·귀속이 원문에 안 받쳐진다.** 발표 중 질문 한 번이면 무너지는 자리들이다.

| # | 자리 | 문제 | 고칠 값 |
|---|---|---|---|
| I1 | 0623 s4 | LIPASE 드론을 `custom-built` 로 적음 | 원문은 모델명을 안 쓴다. 축자는 *"a drone with four rotary wings and a wheelbase of 2 meters ... hung with a steel sphere of radius 25 cm"* — **강구는 정확, `custom` 은 우리 추론** |
| I2 | 0623 s4 | *"top-tier venues 나 인용수 많은 논문 위주로 골랐다"* | IRS 2023·IRS 2022·PIERS 2021·NATO STO·**ACM WiSec 포스터(2~3쪽)** 가 섞여 있다 |
| I3 | 0623 s5 | LaSen 게재지 `ACM/IEEE SenSys` | 러닝헤더는 `SenSys '26, May 11–14, 2026, Saint Malo, France`. **ACM SenSys** 다. `ACM/IEEE` 는 IPSN 표기 |
| I4 | 0630 s4 | *"LaSen 이 쓴 바로 그 드론 = Matrice 4E"* | **두 대다** — *"We evaluate LaSen using two drones: DJI Matrice 4E ... and DJI Mini 4 Pro"*. RTK cm 급 GT 부분은 정확 |
| I5 | 0630 s11 | *"slot ≈ 0.5–1 ms"* | μ=0,1 만 덮는다. 38.211 Table 4.3.2-1 은 0.25 / 0.125 / 0.0625 ms 도 준다 |
| I6 | 0630 s12·s14 | *"CSI-RS ≤ 200 Hz"* | 4~640 슬롯 범위는 **축자 정확**(38.331). 그러나 **200 Hz 는 3GPP 성질이 아니다** — 30 kHz SCS 4슬롯 = 2 ms = **500 Hz**. 200 Hz 는 LaSen 의 2세트 예시이고, LaSen 서론 자신이 최대 500 Hz 라고 적는다. `SSB ≤ 50 Hz` 는 축자 정확 |
| I7 | 0630 s17 | *"…and the highest detection rate"* | 51.84 % / 82.84 % 는 **축자**. `highest detection rate` 는 본문에 없다(본문은 *"HiSAC achieves a higher detection rate than Lerp"* 뿐). Fig. 9(c) 에서 읽는 수준 |
| I8 | 0721 s13 노트 | *"one has no target at all"* | W17 참조 — 그 계열은 비어 있다 |
| I9 | 0728 s2 | *"a stock ray tracer cannot hand a small drone its RCS"* | **Sionna 로 한정하면 참, 일반 광선추적기로 넓히면 거짓**(SBR 계열 EM 솔버는 RCS 를 계산한다). → 메모 `sionna2-rt-rcs-claim-scope` 와 동일 |
| I10 | 0728 s8 | 뉴머롤로지 표 μ=0…4 를 `Release 15+` 로 라벨 | 현행 38.211 은 **μ=0…6**(480/960 kHz, FR2-2, Rel-17). `Rel-15` 로 라벨하거나 두 줄을 더 넣을 것 |
| I11 | 0728 s8 노트 | *"FR1 uses μ = 15/30/60 kHz"* | **μ(0/1/2)와 SCS(kHz)를 뒤섞었다.** 또 FR2 는 SSB 에 240 kHz 도 쓴다 |
| I12 | 0728 s15 | 서베이를 `survey and tutorial` 로 소개 | 논문은 자기를 tutorial 이라 부른 적이 없다(그 낱말은 코드 저장소 URL 과 참고문헌 제목에만). **리뷰 + 신규 기여**(통합 광대역 모델·송수신 공동설계·자체 시뮬)다. `review-only` 도 과소평가 |
| I13 | 0728 s17 | 절 구조를 `I–VI` 로 소개 | **여덟 절이다** — `VII. FUTURE DIRECTIONS`(p.87), `VIII. CONCLUSION`(p.89) 누락 |
| I14 | 0728 s18 | 노이즈/클러터 정의를 서베이 인용처럼 제시 | 서베이엔 그런 불릿 정의가 없다. `z` 는 **열잡음 + 잔여 자기간섭**이고, 클러터 예시는 서베이 어휘로 **건물·차량·사람**(옥내는 금속 정반사)이지 **`walls, floor` 는 우리 챔버 어휘**다 → **우리 의역으로 제시할 것** |
| I15 | 0728 s18 | 핫클러터 = *"scattered external interference from a non-cooperative emitter"* | (a) 핫클러터는 **직접경로도 포함**한다(*"reach the sensing receiver both directly and after scattering"*). (b) 논문은 *"may not"* 으로 완화한다 — 비협조를 정의 요소로 못 박지 않는다 |
| I16 | OpenISAC 기록 | *"no FPGA"* / *"stable at low bandwidth"* | 축자는 *"without relying on proprietary software or specialized FPGA development"* → **`no custom FPGA development`**. 그리고 100 MHz 를 `low bandwidth` 라 부르면 플랫폼을 깎는다 → **`stable up to 100 MHz, breaks at 200 MHz`** |

⚠ 추가 정직성 항목: 우리 통계 클러터(C=100·등바이스태틱거리 4링·v∈[−1,1] m/s)는 서베이 레시피와 **같지만 기하가 다르다** — 그들은 **등거리 링(모노 원)**, 우리는 **등바이스태틱거리 등고선(타원)**. `identical` 이 아니라 **`transplanted`** 라고 쓴다. 또 논문(4링)과 공개 저장소 README(*"Distributed in two range rings"*)가 **링 개수에서 서로 어긋난다** — 인용하려면 **논문 쪽(4링)** 을 쓰고 불일치를 밝힌다.

---

## 8. ⭐ 앞으로 쓰면 안 되는 문장 ↔ 대신 쓸 문장

> 왼쪽은 **실제로 덱·기록에 있던 문장**이다. 오른쪽은 같은 요지를 **원문이 받쳐주는 형태**로 옮긴 것이다.

### 8.1 코퍼스 전칭

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "All of the papers did their experiment outdoors." | "조사한 21편 중 실내 장면은 Lin 2023 한 건뿐이고, 그마저 실험용 기지국이 있는 실내이지 무향실이 아니다." |
| "The Wi-Fi papers are all detection-focused." | "Wi-Fi 6편 중 4편이 검출에서 멈추고, Martelli 2017 과 Milani 2021 은 칼만·IMM 추적까지 간다." |
| "Most prior work has no ground truth." | "대부분은 GT 가 없는 게 아니라 GT 등급이 낮다 — 기체 GPS 로그를 정확도·동기 논의 없이 겹쳐 그린다." |
| "Prior work evaluates only qualitatively — it just shows up." | "정량 평가를 하는 논문이 최소 4편이다(Pd/Pfa·RMSE·검출률). 없는 것은 정량 평가가 아니라 **세 신호를 같은 기하에서 비교한 표**다." |
| "Prior work flies a single casual pass." | "반복 궤적을 쓰는 논문이 있다(Taylor&Poullin 2025 는 5비행 중 4개를 짝지어 반복). 우리 차별점은 반복 자체가 아니라 반복을 신호 3종에 **같은 기하로** 거는 것이다." |

### 8.2 배타·유일 주장

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "We're the only SBR+PO, and the only small drone." | "이 표에서 **SBR+PO 표면적분을 쓰는 것은 우리뿐**이다. 소형 드론 자체는 LAMBDA·Great-X 도 다루므로 유일이 아니다." |
| "Only LIPASE & LaSen — the 2 tracking papers — have precise GT." | "정밀 GT 는 두 등급이다 — LaSen 은 RTK cm 급, LIPASE 는 **DGPS 서브미터**급. 그리고 추적 논문은 **셋**이다(Milani 2021 포함, GPS 폴리곤 GT)." |
| "One of them has no target at all." | "CISSIR 도 표적이 있다 — 40 m 에 **RCS 1 m² 를 주입한 점표적**이다. `표적 없음` 계열은 비어 있다." |
| "There is no prior work on X." (무단서) | "**우리 보유 아카이브 안에서** X 를 찾지 못했다 — 없다는 주장이 아니다." |

### 8.3 도구 능력 (Sionna)

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "Sionna returns only a path gain." | "Sionna RT 는 **복소 산란장 성분**을 돌려준다(기술보고서 식 168). 없는 것은 **결맞은 PO/Kirchhoff 표면적분과 RCS 출력**이다." |
| "A stock ray tracer cannot give a small drone its RCS." | "**Sionna 기본 PathSolver** 에는 산란적분이 없고 RCS 개념 자체가 노출되지 않는다(기술보고서·창설논문 2편에서 `RCS` 0회). SBR 계열 EM 솔버 일반은 RCS 를 계산한다." |
| "Montaner shows Sionna RT cannot produce Doppler." | "Montaner 는 RT 에서 **지연·전력만 받아 쓰고**, 도플러는 광선의 순간 반경속도로부터 따로 계산해 체프 축으로 위상변조해 합성한다(§II-F). 이건 **그 논문이 그렇게 했다**는 사실이지 도구 능력 주장이 아니다." |

### 8.4 남의 논문의 실험 성격

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "LaSen tracks drones on the live 5G downlink." | "LaSen 은 **자기 USRP 로 풀밴드 NR 을 쏴서** 에코를 얻고, 실제 gNB 캡처는 **RE 점유 마스크**를 만드는 데만 쓴다 — 모노스태틱 능동이지 상용 다운링크 패시브가 아니다." |
| "LaSen reuses CSI-RS / SSB." | "LaSen 추정기는 **PDSCH + DM-RS** 를 쓴다. CSI-RS·SSB 는 동기부여로만 등장하고, SSB 는 점유 마스킹 문턱 `T_ssb` 로만 쓰인다." |
| "Earlier 5G sensing used only the sparse pilots." | "파일럿만 쓴다는 한계는 **LaSen 자신의 모노스태틱 비교군**의 성질이다. **패시브 5G 코퍼스는 레퍼런스 채널 전체를 CAF 로 상관**하며, 그들의 한계는 파일럿 희소성이 아니라 **다운링크 점유율**이다." |
| "OpenISAC collapses at 100–200 MHz." | "50/100 MHz 는 드롭 0 의 안정 동작점이고, **200 MHz/4096-FFT** 에서 복조 부하 171.5 % · 드롭 1600+ 로 무너진다. 별도로 **센싱 스레드는 100 MHz 에서 stride M_D ≤ 2 이면 드롭**한다." |
| "OpenISAC runs with no FPGA." | "**custom FPGA 개발 없이** 호스트 CPU 에서 돈다(USRP 기본 FPGA 이미지는 경로에 그대로 있다)." |
| "OpenISAC has no quantitative evaluation." | "**검출 통계가 없다** — CFAR·Pfa·Pd·ROC 가 두 판본 모두 **0회**다. 대신 BER/BLER/EVM, MTI 억압비(±0.5 ppm 부근 17~22 dB), CPU 부하는 인쇄한다." |

### 8.5 수치·서지 인용

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "The Proc. IEEE survey shows a 16 dB ray-tracing penalty." | "서베이는 확률 혼합클러터 씬에 **SCNR −47.4 dB**(Fig. 5), Sionna RT 씬에 **−63.5 dB**(Fig. 7)를 인쇄한다. **약 16 dB 차이는 그 두 캡션에 대한 우리 뺄셈**이고, 논문이 인쇄하거나 주장한 값이 아니다." |
| "…so ray tracing costs 16 dB." (인과) | "**통제되지 않은 두 그림 비교**다 — 같은 처리사슬을 확률 링 모델에서 사이트 특정 RT 도시 씬으로 옮기면 SCNR 이 ~16 dB 떨어진다. 씬·기하·표적모델이 함께 바뀌었다." |
| "SCNR = −47.4 dB (서베이)" | "**어느 그림인지 반드시 붙인다.** −47.4 는 Fig. 2 와 Fig. 5 **둘 다**의 값이므로, 그림 이름 없이 쓰면 독립 데이터 2점으로 오독된다." |
| "Eq. (112) generalizes our ECA dead-parameter finding." | "서베이도 슬로타임 구조가 백색이면 2차 통계만으로는 도플러 판별이 불가능하다고 적는다(p.79). **다만 그쪽이 잃는 것은 표적이고 우리 쪽은 클러터**다 — 같은 결과가 아니라 **질적으로 같은 이유**다." |
| "The survey is monostatic; bistatic appears only in a Remark." | "시스템 모델과 **모든 시뮬레이션**이 모노스태틱이다. 바이/멀티스태틱은 해석적으로만 다뤄지고(Remark 1·3 + 번호 붙은 STAP 소절 pp.78–80), **한 번도 시뮬레이션되거나 광선추적되지 않는다.**" |
| "The survey ignores passive." | "Remark 3(p.60)이 패시브를 명시한다. 우리 쐐기는 **`패시브 바이스태틱 RT 클러터 케이스스터디가 없다`** 이지 `언급이 없다` 가 아니다." |
| "Proc. IEEE 114(1):52–89" | "**Proc. IEEE 114(1):52–92**, DOI 10.1109/JPROC.2026.3675476." |
| "y = H_t x + H_c x + H_h x + z" | "`y_n[l] = H^t x_n[l] + H^c x_n[l] + **H^h s^ext_n[l]** + z_n[l]` (식 8, p.56) — **핫클러터를 구동하는 것은 외부 방사원 신호**다." |
| "CISSIR (NVIDIA)" | "**CISSIR (Hernangómez 외, Fraunhofer HHI / TU Berlin)** — 논문 안 NVIDIA 언급은 *Sionna™, a Python library by Nvidia* 한 줄뿐이다." |
| "PWC-Diff gets 63.60 on RML2016 vs 63.54." | **원문 확보 전까지 인용 금지.** 굳이 쓰려면 `[미검증 — 원문 미확보]` 를 문장 안에 넣는다. |
| "The metrics are the same ones the papers use." | "RD 맵·SNR·Pd/Pfa 는 선행연구 지표 그대로다. **SCR 과 RD 피크 안정도는 우리가 새로 도입**했다." |

### 8.6 판본·출처 규율

| ❌ 쓰지 말 것 | ✅ 대신 |
|---|---|
| "OpenISAC p.13 에 따르면…" (판본 미표기) | "OpenISAC **IoT-J 판**(DOI 10.1109/JIOT.2026.3710751, 15쪽) p.13 — 아카이브의 arXiv v2(16쪽)와 쪽수를 섞지 않는다." |
| "Montaner, EuCAP 2026." (근거 미표기) | "Montaner 외, arXiv:2603.28736v1 — **EuCAP 2026 채택은 arXiv comments 필드가 근거이고 PDF 본문에는 없다**. 최종판이 나오면 쪽수가 바뀐다." |
| "우리 클러터 모델은 서베이와 동일하다." | "서베이 레시피를 **이식**했다 — 그들은 등거리 링(모노 원), 우리는 등바이스태틱거리 등고선(타원). 링 개수는 **논문 4링**을 쓰고 저장소 README(2링)와의 불일치를 밝힌다." |

---

## 9. `RETRACTION_LOG.md` 와의 관계

**이 문서는 남의 논문에 대한 우리 서술의 정정 목록이고, `RETRACTION_LOG.md` 는 우리 자신의 결과에 대한 철회 목록이다.** 겹치는 자리는 아래뿐이며, 전부 **그쪽이 정본**이다.

| 여기 | 정본 |
|---|---|
| I9 `stock ray tracer cannot give RCS` 의 범위 문제 | **R12** (+ 메모 `sionna2-rt-rcs-claim-scope`). R12 의 살아남는 문장 *"보유 218편 아카이브 안에서 …찾지 못했다"* 를 그대로 쓴다 |
| W15·W16 Sionna 능력 서술 | **R6** 과 같은 계열(우리가 Sionna 기능을 원문 확인 전에 단정) — 회절은 R6, 산란장은 여기 W15 |
| 0721 s13 Ziganshin 행 인용 | **A5 · A10** — 회의판/저널판을 절대 섞지 않는다. 이번 감사에서 해당 **행 자체는 원문 일치 확인됨**(`Sionna-RT (v0.19)` + UTD·정점회절·이중반사, PEC 가정) |
| Ziganshin 런타임 초 단위 | **A10(a)** — 0.7 s / 19.0 s 는 360 각도점 전체이지 per-pose 가 아니다 |

**새로 이 문서에서 처음 확정된 것**(RETRACTION_LOG 에 없음): V1·V2 의 16 dB, V3 의 식 (112) 방향, V4 의 바이스태틱 범위, V5 쪽수, V6 OpenISAC 붕괴 지점, 그리고 §3 의 덱 오류 19건 전부.

---

## 10. 재발 방지 — 이번 감사가 추가하는 세 줄

1. ⭐ **전칭 부사 검사.** 덱 노트·본문에 `all / most / only / never / none / 전부 / 유일` 이 나오면, **같은 덱의 표를 자동 대조**한다. 이번에 틀린 12건 중 4건이 자기 표와 모순이었다.
2. ⭐ **부재주장에는 범위구를 강제한다.** *"우리 코퍼스 N편 안에서"*, *"이 표에서"*, *"내 서베이에서"*. 범위구가 붙은 부재주장은 이번에 **0건** 틀렸다.
3. ⭐ **유도값 표시.** 우리가 뺀·나눈·환산한 수는 `(유도값)` 을 달고 원본 두 값을 함께 적는다. 16 dB 는 노트에선 유도값으로 옳게 적혔다가 **RESUME 로 옮겨가며 단서를 잃었다** — 손실 지점은 계산이 아니라 **문서 간 이동**이다.
