# benchmark/ — 공정 벤치마크 레이어 (Wi-Fi / LTE / 5G 패시브레이더 드론 탐지)

리포트 위에 얹는 **공정 벤치마크** 하네스 — 현재는 `report09`~`report12`(바닥유령·CFAR 교정·관측성·검출 결과)를 먹인다.
⚠ `run_matrix.py` → `report5_results.json` 은 리포트 재편(4편→12편) **이전** 산물이라 레거시다.
핵심 수정 한 가지: **표적 SNR/SCR 을 손잡이로 주입하지 않고, 고정 예산(EIRP·잡음) + RCS·기하·대역폭에서 물리로 유도**한다.
(이전 `report4` 는 표적 SNR 을 직접 sweep → 공정성 위배. 여기서 바로잡음.)

## 환경·백엔드 분업  ← 중요

환경은 리눅스 단일 env: `/home/yunjung/.venvs/py312/bin/python` (Sionna RT 2.0.1 설치됨 — 이 서버에서 Analytic/RT 모두 실행).
GPU 는 `src/gpu.py` 가 여유 큰 카드를 자동 선택한다(고정하려면 `SIONNA2_GPU=N`).

| | Analytic (개발·sanity) | Sionna RT (검증) |
|---|---|---|
| 채널 백엔드 | `AnalyticChannel` (닫힌형) | `SionnaRTChannel` (RT CIR, GPU/OptiX) |
| 용도 | 하네스·물리·DSP **개발/검증** | RT **검증 실행** |

두 백엔드가 **같은 `ChannelState`** 를 주므로 상위 하네스는 엔진과 무관하게 동일하다 → **검증 땐 채널만 스왑**.

```python
# 개발·sanity (빠름)
res = run_cell(wf, drone, pos, vel, lb, channel=AnalyticChannel(...))
# RT 검증 — 이 한 줄만 바꾼다
res = run_cell(wf, drone, pos, vel, lb, channel=SionnaRTChannel())
```

## 파일
| 파일 | 역할 |
|---|---|
| `link_budget.py` | **핵심**: 고정 EIRP·kTB(B) + RCS·기하 → 에코SNR·SCR·a_tgt·dpi_amp **물리 유도** |
| `channel.py` | `AnalyticChannel`(CPU) + `SionnaRTChannel`(GPU). RT=환경 멀티패스 CIR, 표적σ=PO 하이브리드 |
| `scenarios.py` | 통제 모션축: hover / radial / tangential / waypoint (한 번 정의·전 신호 재사용) |
| `geometry.py` | 통제 기하: 30×20×11 m **반무향(semi-anechoic)** 챔버(흡수체 벽4면+천장, 바닥은 반사성 콘크리트) TX/RX/CENTER + SPEED/SPAN + 챔버 Rb 창 |
| `run_min_cell.py` | 최소셀(5G NR 100MHz G3 · EIRP 12dBm): 1 config × 1 드론 × radial × N → 측정 SCR·Pd + RD맵 + 3신호 SNR 비교 |
| `run_matrix.py` | **본 실험(report5)**: A 점유×EIRP · B 신호×드론(CSV) · C 시나리오/블라인드 · D RT 교차검증 → `report5_*.png`, `bench_matrix.csv`, `report5_results.json` |
| `verify_server.py` | **RT 검증**: 환경진단 → RT CIR 추출 → RT↔Analytic 교차검증 → RT 최소셀 |
| `rename_outputs.py` | 은퇴한 13편 번호 산출물 이름 이전. **예행이 기본** — 옮길 파일과 바꿀 참조를 찍기만 한다. 지도는 `docs/OUTPUT_NAMING.md` |

## 실행

### 개발·sanity (Analytic)
```bash
cd sionna2/benchmark
/home/yunjung/.venvs/py312/bin/python run_min_cell.py   # 최소셀 → outputs/figures/report5_min_cell.png
```

### RT 검증
```bash
cd sionna2/benchmark
CUDA_VISIBLE_DEVICES=2 /home/yunjung/.venvs/py312/bin/python verify_server.py    # → outputs/figures/bench_rt_cell.png
```
- **OptiX**: `libnvoptix.so.1` 미로딩 → `rt.load_scene` 실패 시,
  `libnvoptix.so.1` 경로 찾아 `DRJIT_LIBOPTIX_PATH` 지정, 또는 관리자에게
  `NVIDIA_DRIVER_CAPABILITIES=all` 로 컨테이너 재기동 요청.
- 교차검증 통과 기준: 자유공간에서 **ΔRb≈0, Δfd≈0** (기하 일치) + RT 클러터≈0 → RT ≈ Analytic.

## 물리 (link_budget)
```
P_echo = EIRP·G_rx·λ²·σ / [(4π)³·R1²·R2²]     (바이스태틱 레이더 방정식)
P_dir  = EIRP·G_rx·λ² / [(4π)²·L²]            (Friis 직접파)
P_n    = k·T0·F·B                             (열잡음, B=대역폭 → 공정성의 핵심)
에코SNR = P_echo/P_n,   a_tgt = √(P_echo/P_n),   dpi_amp = √(P_dir/P_n)   (잡음=1 정규화)
```
→ 신호를 가르는 물리(λ·σ·B)가 **SNR 으로 저절로 나온다**. 이게 이 벤치마크의 원칙 — "SCR is measured, not swept".

## 설계 메모 (공정성 규약)
- **RT 하이브리드**: RT 는 iso 안테나로 **환경 멀티패스(클러터) 기하**만 뽑고(직접파 대비 비율),
  직접파 절대크기·잡음은 link_budget, 표적 σ 는 PO(RT 의 표적 경로는 σ 의 함수가 아니다 —
  docs/VERIFY_RT_VS_PO.md). RT 절대보정 의존 없음.
- **RCS 자세평균**: 단일-자세 PO 는 글린트로 출렁 → `channel.bistatic_rcs_m2` 가 시선 방위 ±4°×5점
  선형 평균(기대 RCS)을 기본 적용.
- **기준신호 정규화 = 송신 전체파형 전력 기준** → 희소 파일럿(G1)의 에너지 핸디캡이 처리이득에 그대로 반영.
- **WiFi 듀티**: 패킷(CSMA/CA) 신호라 백투백 타일링은 비물리적 → 패킷률(~1 kHz, `PILOT_RATE_HZ`)로
  무음 구간을 채워 코히어런트 이득을 실제 패킷률로 제한(`run_min_cell.frame_len`).
- **잡음대역 보정**: P_n 은 점유대역 B 기준, 시뮬 잡음은 fs 레이트 → 주입 진폭에 √(B/fs) 적용
  (안 하면 fs/B 가 큰 협대역이 최대 ~2 dB 유리해지는 계통 편향).
- **CPI 시간 고정(30 ms)**: 프레임률이 다른 파형끼리 도플러분해능을 맞춰 비교.

## 로드맵 A~D — report5 에서 전부 구현됨 (`run_matrix.py`)
- **A. 점유 공정성** ✅ G1/G2/G3 × EIRP 스윕 → 'G1 은 ~18 dB 더 비싸다'로 정량화
- **B. 3축 매트릭스** ✅ 신호×드론(radial) → Pd/SCR/위치오차 히트맵 + `bench_matrix.csv`
- **C. 어려운 시나리오** ✅ hover=완전 블라인드(ECA 부분공간), tangential=마진이 흡수함을 측정
- **D. RT 검증** ✅ 자유공간 클러터≈0 + 챔버 잔향 실측 vs 가정 + RT 채널 셀 재실행
