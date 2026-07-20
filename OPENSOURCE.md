# 오픈소스 대체·검증 지도 (open-source reliance map)

목표(2026-07-20 사용자 방침): **직접 만든 것을 최대한 오픈소스로 대체**해 신뢰성을 높이고 반복 수작업을
줄인다. 단 원칙은 **"검증 후 대체"** — 이미 이론(평판/구)으로 검증된 코드를 검증 없이 통째로 갈아끼우면
신뢰성이 오히려 **떨어진다**. 그래서 각 조각은 ① 오픈소스로 **교차검증** → ② 허용오차 내 일치하면
**권위 소스를 오픈소스로 이관**하는 2단계로 대체한다.

근거 조사: `prior_work/`(pw01 논문·pw02 도구·pw03 포지셔닝) · `prior_work/outputs/prior_work.json`.

## 조각별 대체 판정

| 우리 구현 | 대체/검증 오픈소스 | 라이선스 | 지금 대체? | 계획 |
|---|---|---|---|---|
| **SBR+PO 드론 RCS** (`rcs_sbr.py`·`rcs_po.py`) | **RadarSimPy** (3D STL 메쉬 RCS, 광선추적) | GPLv3 | ⏳ 검증 먼저 | ① 우리 메쉬를 RadarSimPy 에 넣어 σ 재계산 → report08 값과 대조 ② ±2 dB 내 일치 시 RadarSimPy 를 **권위 σ 소스로 이관**, SBR 은 바이스태틱·내부산란체 특수케이스만 유지 |
| **프로펠러 마이크로도플러** (`microdoppler.py`) | **RadarSimPy** (turbine/rotating micro-Doppler) | GPLv3 | ⏳ 검증 먼저 | RadarSimPy turbine 예제로 블레이드 플래시 주파수 교차검증 → 일치 시 대체 |
| **파형 합성** (`waveforms.py`) | **Sionna PHY** (`sionna.phy.nr`, OFDM) | Apache-2.0 | ✅ 이미 검증 | report05 에서 NMSE −135 dB 일치 확인됨. Sionna PHY 를 파형 진리원으로 계속 사용 |
| **지연 채널** (`sionna_chain.py`) | **Sionna PHY** (`cir_to_time_channel`) | Apache-2.0 | ✅ 이미 사용 | 표적 지연커널은 이미 Sionna PHY. 유지 |
| **검출체인** (ECA·CAF·CFAR, `passive_process.py`) | NIST 5GNRad(구조)·RadarSimPy(range-Doppler·CFAR) | Gov / GPLv3 | ✖ 직접 대체 불가 | 패시브 **바이스태틱** ECA 는 드롭인 오픈소스가 없다(5GNRad=능동/MATLAB, RadarSimPy=모노). **아키텍처는 5GNRad(h=h_bg+h_target)와 동일함을 확인**, range-Doppler 결과만 RadarSimPy 로 교차검증 |
| **실측 (X410 OTA 바이스태틱)** | **OpenISAC** (USRP B200~X400, OTA 동기) | 오픈소스 | ✅ 실측단계 채택 | sim→real 골격으로 OpenISAC 채택 — 바이스태틱 OTA 동기가 X410 하드웨어 계획과 직결 |
| **드론 메쉬 CAD** (`drone_cad.py`) | (대체 없음 — DJI 공식 CAD 미공개) | — | ✖ | 파라메트릭 유지. 검증은 실기체 스캔·RadarSimPy RCS |

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
