# 오픈소스 대체·검증 지도 (open-source reliance map)

목표(2026-07-20 사용자 방침): **직접 만든 것을 최대한 오픈소스로 대체**해 신뢰성을 높이고 반복 수작업을
줄인다. 단 원칙은 **"검증 후 대체"** — 이미 이론(평판/구)으로 검증된 코드를 검증 없이 통째로 갈아끼우면
신뢰성이 오히려 **떨어진다**. 그래서 각 조각은 ① 오픈소스로 **교차검증** → ② 허용오차 내 일치하면
**권위 소스를 오픈소스로 이관**하는 2단계로 대체한다.

근거 조사: `prior_work/`(pw01 논문·pw02 도구·pw03 포지셔닝) · `prior_work/outputs/prior_work.json`.

## 조각별 대체 판정

| 우리 구현 | 대체/검증 오픈소스 | 라이선스 | 지금 대체? | 계획 |
|---|---|---|---|---|
| **검출체인 ECA·CAF·CFAR** (`passive_process.py`) | ⭐ **pyAPRiL** (GPLv3, ECA/ECA-S·CAF·CA-CFAR·DoA) | GPLv3 | ✅ **실검증됨** | `benchmark/verify_pyapril.py`: NR/WiFi/LTE 3모드 모두 표적 정답 거리빈 검출. ECA/CAF/CFAR 는 파형 무관(reference I/Q 만). 대량 MC 만 `detection_gpu.py`(GPU) 유지·pyAPRiL 로 정합검증 |
| **SBR+PO 드론 RCS** (`rcs_sbr.py`·`rcs_po.py`) | (라이브러리 대체 안 함) | — | ✖ 자작 유지 | 선행이 쓰는 세 갈래(상용 full-wave·자작 SBR+PO·점산란체) 중 **자작 SBR+PO**(BVH SBR+PO arXiv:2604.09243 와 동일 방법)를 따른다. RadarSimPy 는 비공개 C++ 엔진(게이트)이라 불채택, RaytrAMP 는 모노·PEC 전용이라 부족. 검증: 이론(평판/구)+**실측 문헌 RCS 앵커**(report08) |
| **프로펠러 마이크로도플러** (`microdoppler.py`) | (자작 유지) | — | ✖ | 선행(Costa & Thomä, IEEE J-STEAP 2025)이 프로펠러를 thin-wire 점산란체+PO 로 모델링한 방식과 동종. 측정 마이크로도플러와 대조 가능 |
| **파형 합성** (`waveforms.py`) | **Sionna PHY** (`sionna.phy.nr`, OFDM) | Apache-2.0 | ✅ 이미 검증 | report05 에서 NMSE −135 dB 일치. Sionna PHY 를 파형 진리원으로 유지 |
| **지연 채널** (`sionna_chain.py`) | **Sionna PHY** (`cir_to_time_channel`) | Apache-2.0 | ✅ 이미 사용 | 유지 |
| **추적** (future work, 미구현) | **Stone Soup** (EKF/UKF·파티클·JPDA, MIT) | MIT | ✅ 도입(직접 안 짬) | 바이스태틱 custom nonlinear 측정모델(ρ_b=R_T+R_R−L, f_D=(û_T+û_R)·v/λ)만 작성 |
| **실측 (X410 OTA 바이스태틱)** | **OpenISAC** + **GNU Radio**(SigMF I/Q) | 오픈소스 / GPLv3 | ✅ 실측단계 채택 | OTA 바이스태틱 동기가 X410 계획과 직결. 시뮬(Sionna) I/Q 와 실측(X410) I/Q 를 **동일 SigMF 포맷**으로 통일 → 같은 처리코드 |
| **드론 메쉬 CAD** (`drone_cad.py`) | (대체 없음 — DJI 공식 CAD 미공개) | — | ✖ | 파라메트릭 유지. 검증은 실기체 스캔·실측 문헌 RCS 앵커 |

**참조(코드 이식 아님):** NIST 5GNRad(usnistgov/5GNRad, h=h_bg+h_target 아키텍처) · NIST ISAC-PLM(WiFi 802.11bf 센싱, 단 60GHz) · MATLAB(1차 baseline) · OAI(실 5G NR, 최종단계) · openEMS(full-wave RCS).

## ⚠ 1차 조사 정정
이전 판에서 "패시브 바이스태틱 ECA 는 드롭인 오픈소스 없음"이라 적었으나 **틀렸다** — **pyAPRiL** 이
정확히 그 드롭인이다(GPLv3, DVB-T/FM 실측 검증). 사용자 심화 서베이가 지목, GitHub 로 직접 확인.

## 5단계 대체 로드맵
1. 최소동작: Sionna RT+PHY 채널 → **pyAPRiL** ECA/CAF/CFAR (← 지금 여기)
2. 추적: +**Stone Soup**(바이스태틱 EKF/UKF)
3. 드론 물리: 멀티산란체(1 body+4 motor+8~16 blade-tip) — 우리는 SBR+PO 로 이미 여기
4. AI·sim-to-real: +PyTorch(분류·domain randomization)
5. 실측: +**OpenISAC**+**GNU Radio**+**X410**(SigMF 로 sim↔real 통일)

## 왜 "검증 후 대체"인가 (신뢰성 논리)

- **검출체인**은 pyAPRiL(오픈소스)로 실제 대체·검증했다(파형무관 실증).
- **RCS** 는 라이브러리 대체가 마찰이 크다(RadarSimPy=비공개 엔진, RaytrAMP=모노·PEC). 그래서 선행이 쓰는
  **자작 SBR+PO** 방식을 따르되, 신뢰성은 **실측 문헌 RCS 앵커**로 세운다(시뮬 vs 시뮬보다 강함).
- 원칙: 대체가 이득이고 재현가능한 곳(검출=pyAPRiL, 실측=OpenISAC, 추적=Stone Soup)은 라이브러리로,
  대체 마찰이 크고 이미 검증된 곳(RCS=SBR+PO)은 선행 방식 준수+실측 앵커로.

## 반영 위치(리포트)

- report06 §7 — RCS 한계 주장이 선행(Deterministic-Modeling EuCAP·Sionna-RT 창설논문)에 의해 지지됨 + 우회 3분류.
- report07 — SBR+PO 가 선행(BVH SBR+PO)이 쓰는 방식임을 명시, 검증은 이론+실측 앵커.
- report08 — 문헌 대조에 선행 방법론(확산S vs RCS주입 vs SBR/PO) 위치 표기.
- report08 — **실측 문헌 드론 RCS 표로 절대값 앵커**(교차검증). report12 §2c — pyAPRiL 실검증·아키텍처 정합.
- prior_work/ 3편 — 전체 근거·출처.
