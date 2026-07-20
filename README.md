# sionna2 — 반무향 챔버 패시브 바이스태틱 레이더 드론 탐지 (리포트 12편)

**30×20×11 m 반무향(semi-anechoic) 챔버** 안에서, 남이 켜 주는 통신 신호(WiFi·LTE·5G)를
조명 삼아 **DJI 드론 5종**을 탐지하는 패시브 바이스태틱 레이더를 Sionna RT 위에 시뮬레이션합니다.
설계 철학: **최대한 Sionna 를 그대로 쓰고, Sionna 가 못 하는 부분(표적 산란적분 등)만 부분부분 더한다.**
모든 그림 텍스트는 영어, 본문·주석은 한국어.

> ※ **모든 실험은 챔버 안**입니다(TX·RX 는 양쪽 벽, 베이스라인 L≈15 m, R_b 수~수십 m).
> 벽·천장은 흡수체, **바닥만 반사** — 이 바닥이 report09 의 '유령 표적'을 만듭니다.
> 거리분해능은 **바이스태틱 ΔR_b = c/B** 규약(모노스태틱 등가 c/2B 는 항상 별도 표기).

---

## 리포트 12편 (전부 생성물 — 커널 없이도 그림·GIF 가 보임)

| # | 제목 | 한 줄 |
|---|---|---|
| [report01](report01.ipynb) | 통제 환경 — 반무향 챔버 | 챔버 기하·재질·바닥반사 손계산 대조(0.0005 dB 일치) |
| [report02](report02.ipynb) | 드론 3D 모델 만들기 | 5종 파라메트릭 CAD(재질별 색), NACA 프로펠러, 워터타이트 검증 |
| [report03](report03.ipynb) | 표적 검증 | 실물 제원·실기체 스캔·커뮤니티 모델과 3중 대조 |
| [report04](report04.ipynb) | 조명원 — WiFi/LTE/5G 파형 | 3GPP/IEEE 규격 OFDM 합성, 상시 기준신호 vs 세션 신호(5G 이중고) |
| [report05](report05.ipynb) | 파형 검증 — Sionna 로 대조 | 우리 파형 ↔ Sionna PHY 모듈 NMSE −135 dB 급 일치 |
| [report06](report06.ipynb) | 표적 밝기(RCS)와 Sionna 의 한계 | 기본 PathSolver 에는 산란적분이 없다 — 왜, 그리고 오해 5가지 Q&A |
| [report07](report07.ipynb) | SBR — 표적을 조준해 밝기를 계산 | Mitsuba 광선조준 + PO 적분, 평판/구 이론 대조(−0.01/+0.39 dB) |
| [report08](report08.ipynb) | 드론 RCS·마이크로도플러 결과 | 5종×3밴드 RCS 지도 + 문헌 실측 대조(Li&Ling 등) + 블레이드 플래시 |
| [report09](report09.ipynb) | 챔버 바닥의 함정 — 유령 표적 | 표적경유 바닥경로 +3.5 m 유령 → 광대역 5G(PRS)는 100% 별개 검출 |
| [report10](report10.ipynb) | 검출기 교정 ① — 오경보율 | 명목 Pfa vs 실제 발화(파형별 1.4~2.7배), 원인 2가지와 대조실험 |
| [report11](report11.ipynb) | 검출기 교정 ② — 저속·분해능·관측가능성 | ECA 블라인드 속도, 모호함수, 링크버짓, 단일쌍 위치 불가(FIM 랭크) |
| [report12](report12.ipynb) | 다중 수신기 디텍션 + 9-모드 벤치마크 | **결과편**: Rx 1→4(+10log10N), W/L/G×점유 9모드, X410 실측 설계 |

### 부록 시리즈 — `report_mesh/` (메쉬 제작·신뢰성 심화 가이드 8편)

파이썬 기초만 아는 독자가 따라올 수 있는 **드론 메쉬 심화 가이드**: mesh01(전체 지도) →
mesh02(라이브러리 선택 이유) → mesh03(모든 숫자·모델의 출처와 라이선스) → mesh04(몸체 CAD) →
mesh05(프로펠러 익형) → mesh06(색=재질) → mesh07(기하 검증) → mesh08(실물·물리 검증).
증거는 `report_mesh/outputs/mesh_verify.json`(9섹션 검증 스위트), 생성기는 `report_mesh/src/`.

> ⚠️ **`reportNN.ipynb` 는 전부 생성물이다.** 서술 수정은 `src/make_notebookNN.py` 에서 하고 재실행한다
> (`.ipynb` 직접 수정은 다음 빌드에서 사라진다). 본문 수치는 전부 `outputs/*.json` 에서 f-string 으로
> 주입한다 — **손으로 적은 숫자 금지** 가 하우스 규약.

```bash
PY=~/.venvs/py312/bin/python
cd sionna2
for n in 01 02 03 04 05 06 07 08 09 10 11 12; do $PY src/make_notebook$n.py; done
```

---

## 실험·렌더 파이프라인

```bash
# 디텍션 스윕(9모드 × Rx 1..4 × SNR 그리드, GPU 몬테카를로; K는 env로)
SIONNA2_DET_K=2000 $PY src/experiment_detection.py        # → outputs/detection_rx_sweep.json
# 검증 하네스(benchmark/) — 리포트가 읽는 verify_*.json 생성
cd benchmark && $PY verify_cfar.py && $PY verify_eca.py && $PY verify_ambiguity.py \
             && $PY verify_linkbudget.py && $PY verify_observability.py && $PY verify_floor_ghost.py
# 그림(6패널 CFAR 등)
$PY src/viz_report4.py                                    # → outputs/figures/report4_e1_cfar.png 등
# RT 렌더 GIF(고품질; ANIM_SPP 로 품질, SIONNA2_GPU 로 카드 지정)
SIONNA2_GPU=3 ANIM_SPP=512 $PY src/render_anim.py --which orbit_chamber   # spin/paths_build/radiomap_scan/rx_array/obs_ring
$PY src/render_rt.py                                      # 정지 렌더 + rt_40_flight.gif
$PY src/build_animations.py                               # matplotlib GIF(RCS 글린트·점유·마이크로도플러)
```

- **GPU**: `src/gpu.py` 가 여유 큰 카드를 자동 선택(`SIONNA2_GPU=N` 으로 고정). 배치 크기는
  `SIONNA2_DET_BATCH`, 실험 반복수는 `SIONNA2_DET_K` — **nvidia-smi 를 보며 동적으로 키운다**.
- 생성물: `outputs/figures/`(그래프), `outputs/renders/`+`outputs/renders/anim/`(RT 렌더·GIF),
  `outputs/*.json`(리포트가 읽는 측정치 — 재현성의 원본).

---

## 드론 5종 — 실측 제원 기반

| 드론 | 출시상태 | 로터 | 대각거리 | 무게 | 프로펠러 |
|---|---|---|---|---|---|
| **Mini 5 Pro** | 출시(2025) | 4 | ~250 mm* | 249.9 g | Ø152 mm ×2 |
| **Mavic 4 Pro** | 출시(2025) | 4 | ~400 mm* | 1063 g | Ø267 mm ×2 |
| **Matrice 4E** | 출시(2025) | 4 | 438.8 mm | 1219 g | Ø274 mm ×2 |
| **S1000+** | 단종(2014) | **8** | 1045 mm | 4400 g† | Ø381 mm ×2 |
| **Phantom 4** | 출시(2016) | 4 | 350 mm | 1380 g | Ø239 mm ×2 |

\* 대각거리는 DJI 비공개라 외형에서 추정. † S1000+ 는 기체 자중(권장 이륙중량 6~11 kg). 나머지는 TOW.
(원자료: `docs/drone_research.json`, `docs/SPECS.md` · 문헌 대조: `refs/drone_papers/`)

메쉬 원칙: **OBJ 1개 = 부위 1개 = Sionna 재질 1개** — 부위별 전파재질(ITU-R P.2040 기본 + 커스텀)과
재질별 색을 그대로 RT 에 쓴다. 분절(articulated): 몸체 RPY ⟂ 로터별 스핀.

---

## 코드 구조 (`src/`, 전부 한글 주석)

```
─ 장면·표적 ─────────────────────────────────────────────
geom.py / cadkit.py     삼각형 3D 미니 도구 · CAD 로프트/불리언(trimesh+manifold3d)
chamber.py              반무향 챔버 모델(흡수체 벽·반사 바닥)
drones.py / drone_cad.py 5종 제원+파라메트릭 생성기 · NACA 프로펠러 로프트(피치·테이퍼·스큐)
materials.py            Sionna 전파재질 단일 원본(ITU 기본+커스텀; PO 도 여기 Γ 를 읽음)
scene_build.py          부위 OBJ → Sionna 장면 조립 + 렌더
─ 신호·RCS ─────────────────────────────────────────────
waveforms.py            OFDM 합성 + 점유 G1/G2/G3 (CRS·SSB·PRS·프리앰블) — ΔR_b=c/B 규약
waveforms_sionna.py     Sionna PHY 모듈로 같은 파형 재구성(report05 대조용)
rcs_po.py / rcs_sbr.py  물리광학 PO · SBR(Mitsuba 조준+PO 적분, 가림 포함)
microdoppler.py         회전 블레이드 마이크로도플러(PO 복소장)
─ 탐지 ──────────────────────────────────────────────────
bistatic_scene.py       바이스태틱 기하(R_b·τ·f_d·β)
passive_process.py / radar_process.py  ECA → CAF 거리-도플러 → CA-CFAR
sionna_chain.py         Sionna RT 경로 → cir_to_time_channel 지연커널 에코
experiment_detection.py 9모드×Rx1..4 GPU 몬테카를로 스윕(결과편 report12 의 원본)
detection_gpu.py        torch 배치 RD/CFAR/피크 커널
experiment_x410.py      USRP X410 실측 시나리오 기하
─ 시각화·렌더 ───────────────────────────────────────────
viz_*.py                matplotlib 그림(리포트별) · vizstyle.py 공통 스타일
render_rt.py / render_anim.py / render_drones.py   Sionna/Mitsuba 렌더(정지·GIF)
anim_plots.py / viz_animations.py / build_animations.py  matplotlib GIF
─ 리포트 ────────────────────────────────────────────────
make_notebook01..12.py  리포트 생성기(서술 원본; 수치는 outputs/*.json 주입)
provenance.py           리포트 앞머리 provenance 블록(용어풀이·재현 명령·산출물 표)
gpu.py                  GPU 자동선택(여유 최대 카드)·예산
```

### 검증 하네스 (`benchmark/`)

```
geometry.py / link_budget.py / channel.py   챔버 배치 · 바이스태틱 레이더방정식+Friis+kTB · 채널 백엔드
verify_cfar.py          오경보율 교정(report10 의 원본 JSON)
verify_eca.py           ECA 노치·블라인드 속도(report11)
verify_ambiguity.py     모호함수 거리·도플러 분해능(report11)
verify_linkbudget.py    3독립 계산 대조 + σ→SCR→Pd(report11)
verify_observability.py 단일쌍 FIM 랭크·CRLB·처방(report11 §5)
verify_floor_ghost.py / verify_ghost_impact.py  바닥 유령 기하·검출 영향(report09)
verify_rt_*.py / verify_target_rt.py            Sionna RT 광선예산·표적경로 진단(report06/07)
compare_real_cad.py / compare_community.py      실기체 스캔·커뮤니티 모델 형상 대조(report03)
```

---

## 환경 (단일 env: py312)
- Python `~/.venvs/py312/bin/python` — 3.12.13. numpy·scipy·matplotlib·torch +
  **Sionna RT 2.0.1 / mitsuba 3.8.0 / drjit 1.3.1** (OptiX GPU 광선추적 확인). 이 한 env 로 전부 실행.
- VSCode 노트북 커널 **py312**.

## 방향
- **디텍션 집중** (트래킹은 future work 1줄) — 시뮬 5종 전부 + 실측 2종(Mavic 4 Pro·Matrice 4E).
- 실측: USRP X410(4RX·400 MHz·12bit), 시뮬=통제 챔버 / 실측=외부.
- 다음 후보: 기준안테나 없는 상시-신호-만 모드의 열화 정량화, 마이크로도플러 결합 탐지(저속 블라인드 메우기),
  2-Rx 위치확정(report11 §5 처방의 실측판).
