# benchmark/ — 공정 벤치마크 레이어 (Wi-Fi / LTE / 5G 패시브레이더 드론 탐지)

`report1~4`(설명용 튜토리얼) 위에, **EXPERIMENT_SPEC 의 공정 벤치마크**를 실제로 돌리는 얇은 하네스.
핵심 수정 한 가지: **표적 SNR/SCR 을 손잡이로 주입하지 않고, 고정 예산(EIRP·잡음) + RCS·기하·대역폭에서 물리로 유도**한다.
(이전 `report4` 는 표적 SNR 을 직접 sweep → 공정성 위배. 여기서 바로잡음.)

## 로컬(맥) vs 서버 분업  ← 중요

| | 로컬 (이 맥, M1) | 서버 (RTX 4090 Docker) |
|---|---|---|
| Sionna RT | ❌ 미설치·OptiX 없음 | ✅ sionna-rt 2.0.1 / OptiX |
| 채널 백엔드 | `AnalyticChannel` (닫힌형) | `SionnaRTChannel` (RT CIR) |
| 용도 | 하네스·물리·DSP **개발/검증** | RT **검증 실행** |

두 백엔드가 **같은 `ChannelState`** 를 주므로 상위 하네스는 엔진과 무관하게 동일하다 → **서버에선 채널만 스왑**.

```python
# 로컬 개발
res = run_cell(wf, drone, pos, vel, lb, channel=AnalyticChannel(...))
# 서버 검증 — 이 한 줄만 바꾼다
res = run_cell(wf, drone, pos, vel, lb, channel=SionnaRTChannel())
```

## 파일
| 파일 | 역할 |
|---|---|
| `link_budget.py` | **핵심**: 고정 EIRP·kTB(B) + RCS·기하 → 에코SNR·SCR·a_tgt·dpi_amp **물리 유도** |
| `channel.py` | `AnalyticChannel`(로컬) + `SionnaRTChannel`(서버). RT=환경 멀티패스 CIR, 표적σ=PO 하이브리드 |
| `scenarios.py` | 통제 모션축: hover / radial / tangential / waypoint (한 번 정의·전 신호 재사용) |
| `run_min_cell.py` | 최소셀: 1 config × 1 드론 × radial × N → 측정 SCR·Pd + RD맵 + 3신호 SNR 비교 |
| `verify_server.py` | **서버 전용**: 환경진단 → RT CIR 추출 → RT↔Analytic 교차검증 → RT 최소셀 |

## 실행

### 로컬 (개발·sanity)
```bash
cd sionna2/benchmark
python3 run_min_cell.py        # AnalyticChannel 로 최소셀 → outputs/figures/bench_min_cell.png
```

### 서버 (RT 검증)
```bash
source /workspace/jeong/miniforge3/etc/profile.d/conda.sh && conda activate sionna
cd sionna2/benchmark
CUDA_VISIBLE_DEVICES=0 python verify_server.py    # → outputs/figures/bench_rt_cell.png
```
- **OptiX 블로커**(SESSION_HANDOFF): `libnvoptix.so.1` 미로딩 → `rt.load_scene` 실패 시,
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
→ 신호를 가르는 물리(λ·σ·B)가 **SNR 으로 저절로 나온다**. 이게 EXPERIMENT_SPEC 의 "SCR is measured, not swept".

## 설계 메모
- **RT 하이브리드**: RT 는 iso 안테나로 **환경 멀티패스(클러터) 기하**만 뽑고(직접파 대비 비율),
  직접파 절대크기·잡음은 link_budget, 표적 σ 는 PO(report2: 작은 드론 RT 산란 불안정). RT 절대보정 의존 없음.
- **RCS 는 단일-자세(glint)** 라 값이 출렁 → 공정성 위해 추후 자세 소구간 평균/스윕 권장.
- **매크로 조명원이면 근거리 드론은 SCR 40dB+ 로 너무 쉬움** → 변별 구간은 소형셀/AP·원거리·어려운 모션.

## 다음 (grow)
- **A. 점유 공정성**: 정합필터 기준을 G1/G2/G3 별로 → 5G SSB 이중고를 Pd 로 정량화 (프로젝트 핵심)
- **B. 3축 매트릭스**: spec×drone×scenario×N → 셀별 SCR·Pd·FAR(±CI) → CSV + "Pd vs spec, 시나리오 facet"
- **C. 어려운 시나리오**: hover/tangential 추가 → bulk-only 의 예상된 blind 확인
- **D. 서버 RT**: OptiX 해결 → `verify_server.py` → RT vs Analytic 교차검증 통과 확인
