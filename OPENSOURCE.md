# 오픈소스 대체·검증 지도 (open-source reliance map)

목표(2026-07-20 사용자 방침): **직접 만든 것을 최대한 오픈소스로 대체**해 신뢰성을 높이고 반복 수작업을
줄인다. 단 원칙은 **"검증 후 대체"** — 이미 이론(평판/구)으로 검증된 코드를 검증 없이 통째로 갈아끼우면
신뢰성이 오히려 **떨어진다**. 그래서 각 조각은 ① 오픈소스로 **교차검증** → ② 허용오차 내 일치하면
**권위 소스를 오픈소스로 이관**하는 2단계로 대체한다.

근거 조사: `prior_work/`(pw01 논문·pw02 도구·pw03 포지셔닝) · `prior_work/outputs/prior_work.json`.

## 조각별 대체 판정

| 우리 구현 | 대체/검증 오픈소스 | 라이선스 | 지금 대체? | 계획 |
|---|---|---|---|---|
| **검출체인 ECA·CAF·CFAR** (`passive_process.py`) | ⭐ **pyAPRiL** (Advanced Passive Radar Library — ECA/ECA-B/ECA-S·CAF·CA-CFAR·DoA) | GPLv3 | ⏳ 검증 먼저 | ① Sionna 가 만든 r_ref/r_surv 를 pyAPRiL 에 넣어 우리 결과와 대조 ② 일치 시 **단일실현 검출을 pyAPRiL 로 이관**(DVB-T/FM 실측 검증된 코드). **대량 MC(K=6000)는 GPU 배치가 필요해 우리 `detection_gpu.py` 유지**하되 pyAPRiL 로 정합성 검증 |
| **SBR+PO 드론 RCS** (`rcs_sbr.py`·`rcs_po.py`) | **RadarSimPy** (3D STL 메쉬 RCS) + **openEMS** (full-wave 앵커) | GPLv3 | ⏳ 검증 먼저 | ① 우리 메쉬를 RadarSimPy 에 넣어 σ 재계산 → report08 값과 대조 ② openEMS 로 오프라인 full-wave 룩업 1점 앵커 ③ ±2 dB 내 일치 시 권위 σ 소스 이관 |
| **프로펠러 마이크로도플러** (`microdoppler.py`) | **RadarSimPy** (turbine/rotating micro-Doppler) | GPLv3 | ⏳ 검증 먼저 | RadarSimPy turbine 예제로 블레이드 플래시 주파수 교차검증 → 일치 시 대체 |
| **파형 합성** (`waveforms.py`) | **Sionna PHY** (`sionna.phy.nr`, OFDM) | Apache-2.0 | ✅ 이미 검증 | report05 에서 NMSE −135 dB 일치. Sionna PHY 를 파형 진리원으로 유지 |
| **지연 채널** (`sionna_chain.py`) | **Sionna PHY** (`cir_to_time_channel`) | Apache-2.0 | ✅ 이미 사용 | 유지 |
| **추적** (future work, 미구현) | **Stone Soup** (EKF/UKF·파티클·JPDA, MIT) | MIT | ✅ 도입(직접 안 짬) | 바이스태틱 custom nonlinear 측정모델(ρ_b=R_T+R_R−L, f_D=(û_T+û_R)·v/λ)만 작성 |
| **실측 (X410 OTA 바이스태틱)** | **OpenISAC** + **GNU Radio**(SigMF I/Q) | 오픈소스 / GPLv3 | ✅ 실측단계 채택 | OTA 바이스태틱 동기가 X410 계획과 직결. 시뮬(Sionna) I/Q 와 실측(X410) I/Q 를 **동일 SigMF 포맷**으로 통일 → 같은 처리코드 |
| **드론 메쉬 CAD** (`drone_cad.py`) | (대체 없음 — DJI 공식 CAD 미공개) | — | ✖ | 파라메트릭 유지. 검증은 실기체 스캔·RadarSimPy RCS |

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

- 우리 SBR+PO 는 **평판(−0.01 dB)·금속구(+0.39 dB) 이론 대조로 이미 검증**됐다(report07). 이걸
  검증 없이 RadarSimPy 로 갈면, RadarSimPy 자체의 가정(모노스태틱·기본 재질)이 우리 요구(바이스태틱·
  내부 배터리/PCB 산란체·재질 가중)와 어긋날 때 **조용히 틀린 값**을 신뢰하게 된다.
- 그래서 순서는 **교차검증이 먼저**다. 두 독립 도구가 일치하면 그때 권위 소스를 오픈소스로 넘긴다 —
  그러면 "우리 코드가 맞다"는 부담을 외부 검증된 도구가 대신 져 주어 **신뢰성이 실제로 오른다**.

## 반영 위치(리포트)

- report06 §7 — RCS 한계 주장이 선행(Deterministic-Modeling EuCAP·Sionna-RT 창설논문)에 의해 지지됨 + 우회 3분류.
- report07 — SBR σ 를 RadarSimPy 로 교차검증하는 계획(future work).
- report08 — 문헌 대조에 선행 방법론(확산S vs RCS주입 vs SBR/PO) 위치 표기.
- report12 §2b — 우리 아키텍처 = NIST 5GNRad/3GPP 주류(h=h_bg+h_target), 채택 계획(OpenISAC·RadarSimPy).
- prior_work/ 3편 — 전체 근거·출처.
