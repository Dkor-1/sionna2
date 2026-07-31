> ⚠ **2026-07-31 재편으로 퇴역한 리포트의 설계서다** — 당시 사양을 그대로 보존한다. 현재 6편 구조는 [`../README.md`](../README.md) 와 [`REPORT_CODE_MAP.md`](REPORT_CODE_MAP.md) 에 있다.

# report14 SPEC — 리얼 환경 디텍션 (Sionna RT 클러터 + MVDR-STAP)

> **한 줄:** 무향실을 벗어나 **실외 다중경로(Sionna RT 디지털트윈)** 속에서, RCS 는 스칼라로 단순화하고
> **환경을 리얼하게** 만든 뒤 **패시브 바이스태틱 드론 검지**를 한다. 통계 클러터 vs RT 클러터 SCNR 낙차를
> Proc.IEEE Clutter-Aware 서베이(Fig5 vs Fig7)와 사과-대-사과로 재현하고, 검출기를 ECA→**MVDR-STAP**으로
> 올려 묻힌 표적을 복원한다. (사용자 확정: ①실외 풀 씬 ②STAP 완전구현. 2026-07-27)

## 0. 서사 (교수님 각도 정면 실행)
교수님 제안 = **RCS 단순화 + 환경 리얼리스틱 + 디텍션**. report13(자유공간)은 RCS 상세(SBR+PO)를 유지했다.
report14 는 그 반대축: **σ 를 스칼라 반사계수로 접고**(σ 격자 재사용해 표적 밝기만), **환경을 Sionna RT 실외
다중경로로 리치하게** 만들고, **STAP 로 실제 검출 판정**을 한다. 2607 논문 3편이 전부 이 방향을 가리키고
셋 다 "패시브 바이스태틱 디텍션"에서 멈춘다 — 그 공백이 우리 기여다([[READING_2607_NOTES]]).

## 1. 신호 모델 (Clutter 서베이 Eq.8·60 차용)
3항 분해: **y = 표적에코 + cold 클러터 + hot 클러터 + 잡음**.
- **표적**: 스칼라 σ(report13 격자에서 조회) · 지연 τ_t · 도플러 f_d,t · 조향 v(θ_t).
- **cold**(자기에코, 조명파형 기지): 정적 다중경로 → 0-도플러 능선 + 상대운동 도플러퍼짐.
- **hot**(외부 방출체 산란): 표적경유 바닥유령/건물 다중반사, 비영 지연·도플러.
- **내부커널** `Vᶜᶜ = Σ σ²c·v(θc,f_D,c)v(·)ᴴ` (파형독립) — 씬에서 한 번 학습, 파형별 예측.

## 2. 두 개의 클러터 원장 (SCNR 비교의 핵심)
| 원장 | 방법 | 상태 |
|---|---|---|
| **A. 통계(stochastic)** | C=100 산란체 4 iso-Rb 링 ±1 m/s (`cold_clutter_scatterers`) | ✅ 존재 |
| **B. Sionna RT(site-specific)** | 내장 실외 씬(`simple_street_canyon_with_cars` 또는 `munich`) + 확산산란(R²+S²=1, 재질별 S) + max_depth=3 | 🔨 신규 |
- **핵심 실험 E1**: 같은 기하(TX/RX/드론)를 A·B 두 방식으로 클러터 생성 → **SCNR(A) vs SCNR(B)**.
  서베이 Fig5(−47.4 dB stochastic) vs Fig7(−63.5 dB RT) = **−16.1 dB 낙차** 를 우리 패시브 바이스태틱 케이스로 재현.
  ~10-16 dB 재현이면 Proc.IEEE 벤치와 apples-to-apples; 아니면 그 자체가 발견(바이스태틱·반무향·조명원).

## 3. RT 실외 씬 (Montaner식, §II.C-F 차용)
- **씬**: `sionna.rt.load_scene(sionna.rt.scene.simple_street_canyon_with_cars)` (또는 munich). TX 마스트·RX·드론 배치.
- **확산산란**: `RadioMaterial` 에 재질별 산란계수 S(glass/concrete/metal/brick, 서베이 GIT/Montaner 값) → specular+1차 diffuse (`diffuse_reflection=True`).
- **Doppler 합성**(Sionna RT 는 지연·전력만): 광선 시선속도에서 f_D 합성(Montaner §II.F) → cold(정적 0) + 이동 표적 도플러.
- **CIR → 클러터 공분산**: PathSolver 경로(지연·전력·각도)를 (θ,τ,f_D) 로 → `Vᶜᶜ`.
- ⚠ 스칼라 σ 단순화: Montaner 처럼 표적을 메쉬+재질로 둘 수도 있으나 **few-λ 드론은 스톡 Sionna 부정확**(우리 메모) → 표적 밝기는 report13 σ 격자(SBR+PO)로 주입하고 **환경만** RT.

## 4. MVDR-STAP 검출기 (신규, 서베이 §V-C 차용)
- **차원**: 공간 N=4 (X410 4RX, `steering_vector`) × 슬로우타임 M (CPI 프레임). 공간-시간 스냅샷 x ∈ C^{NM}.
- **공분산** R = E{ηηᴴ} (클러터+잡음, 표적 제외 훈련셀). **RMB 규칙 Ntr≥2·NM** 훈련셀.
- **MVDR-STAP 가중** w = R⁻¹v / (vᴴR⁻¹v), 조향 v = d(f_D)⊗a(θ). **출력 SCNR = vᴴR⁻¹v**.
- **감축계수**(스냅샷 부족 대비): 저계수+대각로딩 or Kronecker 구조(서베이 Eq.67·102). 반무향 챔버는 스냅샷 적으니 필수.
- **핵심 실험 E2**: cold+hot 로 묻힌 표적(SCNR ~−45 dB)을 STAP 가 복원 → 검출 가능 SNR 로. ECA(1D slow-time) vs STAP(2D) 비교(서베이 중심 메시지: 1D 불충분).

## 5. 실험 (E1~E4)
| # | 실험 | 산출 |
|---|---|---|
| E1 | SCNR: 통계 vs RT 클러터 (3 조명 W/L/G) | Δ dB (Fig5vs7 재현) |
| E2 | ECA(1D) vs MVDR-STAP(2D) 표적 복원 | RD맵 before/after, SCNR 이득 |
| E3 | STAP 각도-도플러 응답 + 클러터 능선 | angle-Doppler 스펙트럼 |
| E4 | 감축계수 vs 훈련셀 수(RMB) | SCNR vs Ntr |

## 6. 그림 (F1~F8 + GIF)
| F | 내용 | 데이터 |
|---|---|---|
| F1 | 씬 개요 — 실외 다중경로(TX/RX/드론/건물) RT 렌더 | render |
| F2 | 두 클러터 원장 비교(통계 링 vs RT 경로) 평면도 | scene |
| F3 | **SCNR 통계 vs RT (3 조명)** — 헤드라인 낙차 | E1 |
| F4 | RD맵 before/after STAP (표적 복원) | E2 |
| F5 | STAP 각도-도플러 응답(클러터 능선 널) | E3 |
| F6 | ECA vs STAP SCNR 이득 | E2 |
| F7 | SCNR vs 훈련셀(RMB Ntr≥2NM) | E4 |
| F8 | 택소노미 — 챔버(sparse) vs 실외(hybrid), 서베이 Table 2 | 서베이 |
| GIF | 표적이 클러터 능선 통과 → STAP 널 추종 | E3 |

## 7. 헤드라인
"실외 다중경로 Sionna RT 디지털트윈에서, 스칼라 σ 표적을 패시브 바이스태틱으로 검지한다. RT 클러터는
통계 모델보다 SCNR 을 **{ΔdB} dB** 낮추고(Proc.IEEE 서베이 −16 dB 와 {대조}), 1D slow-time(ECA)로는
복원 불가하나 **MVDR-STAP(공간 N=4 × 시간 M)**이 표적을 {gain} dB 끌어올려 검출 가능하게 한다."

## 8. 정직성 (팀 공유용)
- **패시브 바이스태틱**은 서베이(모노)·OpenISAC(협조)보다 **어렵다** — 명기.
- **SCNR 정의**를 서베이(입력·단일RD셀·전처리전)와 맞춰야 "≈"·낙차 인용 가능. 우리 정의 병기.
- **표적 σ 는 SBR+PO(report13), 환경만 RT** — Montaner 처럼 표적도 RT 로 두면 few-λ 부정확(우리 메모).
- STAP 스냅샷은 반무향 챔버서 적다 → 감축계수·대각로딩 명시.
- 챔버(report01~13) vs 실외(report14) = 우리 시뮬 두 극단. 실측(X410)은 실외.

## 9. 신규 파일 (기존 무수정 원칙)
- `src/report14_scene.py` — RT 실외 씬 로드·확산산란·CIR→클러터 공분산·Doppler 합성.
- `src/report14_stap.py` — 공간-시간 공분산·MVDR-STAP·RMB·감축계수·SCNR.
- `src/experiment_report14.py` — E1~E4 실행 → `outputs/report14_clutter_stap.json`.
- `src/viz_report14.py` — F1~F8 + GIF (JSON→그림, 물리 재계산 금지).
- `src/render_report14.py` — RT 실외 씬 렌더(스틸+GIF).
- `src/make_notebook14.py` — report14.ipynb (provenance §0, 손 숫자 없음).

## 10. 구현 순서 (검증 겹겹이)
1. scene 모듈 → RT 실외 씬 로드·경로추출 스모크(경로 수·지연·각도 sane).
2. stap 모듈 → 공분산·MVDR 단위테스트(클레어보이언트 R 로 SCNR=vᴴR⁻¹v 검증).
3. experiment E1(SCNR 비교) → 통계 원장은 기존, RT 원장 신규. 낙차 물리 대조.
4. E2~E4 → STAP 복원·감축계수.
5. viz+render+nb. 적대검증(SCNR 정의·apples-to-apples·STAP 클레어보이언트 상한).
