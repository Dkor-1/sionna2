# 재개 지점 — 2026-07-23

**이 문서 하나만 읽으면 중단 지점부터 이어갈 수 있다.** 새 대화에서 시작해도 여기서 출발하면 된다.
앞 라운드(메쉬 수정·전수 재생성·기록물 정산)의 상세는 [`RESUME_0722.md`](RESUME_0722.md).

---

## 1. 지금 상태 한 줄

**2026-07-27 최신** — report13 **100% 완성**(R6 실MC RD맵 포함, 스킵 0) + 결함 **C-1~C-8 전건 해소** + 드론제원 마스터 + 2607 논문3편 정독. 전부 커밋·push 완료(최신 0be6920). **다음: report14(리얼 환경 디텍션 — Sionna RT 클러터+STAP+Fig5vs7 SCNR).**

⚠ **백그라운드는 Claude 프로세스와 함께 죽는다.** 재개 시 `ps` 로 실제 실행 여부부터 확인할 것.
⚠ **동시 세션 주의**: 저장소를 두 세션이 볼 수 있다. 문서를 쓰기 전에 `git status` 와 mtime 확인.

### 1a. ⭐report13 완성 (2026-07-24 22:06) — 사용자 원 요청 딜리버러블

"환경 배제(반사체 없음)·드론만·검지거리" 자유공간 시뮬 완성. **그리드 기반 조기 전달**(multistatic는 드론당 ~2.3-4h라 느려서, 검지거리에 불필요한 그걸 백그라운드로 분리).
- **산출:** report13.ipynb(33셀, provenance §0 포함) · 그림 16 PNG · RT 렌더 스틸 22 · GIF 11(viz 3 + 렌더 8: 5기종궤도·자세×5·기하·줌).
- **검지거리 결과(5종×W1/L1/G1):** G1(SSB) **전 드론 E[Pd]=0·blind=1.0**(M=5 도플러 전멸=5G 이중고) · L1(LTE) 헤드라인(mavic4pro E[Pd]=0.65·phantom4 0.43, blind 0.25) · W1(WiFi) blind 최소 0.083 · s1000plus(최대) 최장 ~9.7-10km.
- **핵심 물리:** 검지거리는 방위**평균 아니라 시선방위 σ@look**를 따름 → 단일기하 R 은 로브/널 복권(그래서 커버리지 C 병용). 커버리지는 **험프**(근거리 β>90 전방산란 블라인드 + 원거리 SNR한계). F11 **DPI잔류60이 최단벽**. F2 **대역폭 B 항 없음**(패시브 서사).
- **검증:** verify_freespace **12게이트 PASS**(5종). σ격자 앵커 대조 0.03~0.2dB.
- **refinement 완료(2026-07-25 00:35):** s1000plus multistatic(9.8h!) 완료로 5/5 전부 끝. par 드라이버 자동 재병합 → canonical 5/5 multistatic. **F14 verify 그림 5드론 Δσ(β)** 재생성(β0→90°: 0→−2.15dB). nb 재생성 불필요(경로참조).
- **σ 파이프라인 비효율 메모(차기 최적화):** multistatic_check 가 바이스태틱 σ eval 당 ~15s(모노 0.055s의 270×) — 씬 재빌드 추정. 캐싱하면 큰 절감.

### 1b. 2026-07-24 세션에서 한 일 / 진행 중 (최신)

**완료(GPU-free 결함정정 5건, 전부 재빌드):**
- **C-3 (★결과 반전).** `verify_pyapril.py` 재실행 → 3모드 전부 `detected_at_truth=True`·`n_fired=5`.
  옛 False 는 CFAR 튜플언팩 버그 산물. report12 서술 "CFAR 정답셀 발화(모드당 5셀)"로 정정.
- **C-4.** report05 §2 "전샘플 대조 관행은 드물다"(n=3 부정 일반화) → "이 세 예 모두 …보고하지는 않았다" 사실진술.
- **C-5.** `prior_work.json measured_rcs_anchor.verdict` 를 현재 σ(el0 평균 −16.6·중앙값 −19.7·봉우리 −8.4)로 갱신 + `_verdict_source`. make_notebook08 "낡음" 주석도 갱신.
- **C-6.** `waveforms.py:166 v_unambiguous_ms` docstring 에 모노 등가·바이스태틱 재배율 1/(cos(β/2)cosδ) 명시(반환값 불변, 호출부 보존).
- **C-8 (부분).** report09 클러터 라벨 하드코딩 "M=48" → JSON `meta.M_default` 에서 읽기 + "궤적 실행과 동일 설정". 진짜 해소(ghost M=48 재실행)는 GPU 라운드.
- 상세: [`AUDIT_FINDINGS_0722.md`](AUDIT_FINDINGS_0722.md) §C 표 2026-07-24 갱신본.

**진행 중:**
- **report13 σ격자** — GPU1/2/3 **3레인 병렬**(드론별 `outputs/report13_sigma_grid.<drone>.json` → 병합기 `scratchpad/merge_sigma_grid.py`).
  드라이버 `scratchpad/r13_sigma_par.sh`. GPU util 0%는 정상(PO=CPU-bound). s1000plus(40k면)가 병목.
  ⚠ 병렬 실행이 canonical 파일에 직접 못 씀(os.replace 경합) → 반드시 드론별 `--out` 후 병합.
- **σ→range 통합 정적검증 완료(end-to-end 이상없음):** 생산자 노드키(az_deg/el_deg/sigma_smooth_dbsm) ↔ range `_sigma_lookup`,
  밴드이름 3곳 일치("5G NR 3.5 GHz"), `assemble_canonical` 이 `ranges[drone]` **누적**(setdefault), stage_solve 출력에 drone 키. **viz 는 5종 전부 `ranges[drone]` 기대.**
- **다음(σ 완료 후):** range 5종 **순차** `--stage all --mode W1,L1,G1 --drone <D> --sigma <canonical> --out report13_freespace.json`
  (누적됨, threshold/verify 는 드론무관 동일). → verify_freespace(GPU-light) → viz_report13(CPU) ∥ render_report13(GPU3 RT) → make_notebook13.
- **팀미팅 논문 1~2편 선정** — 서브에이전트 조사 중(교수님 각도: RCS 단순화+환경 리얼리스틱+디텍션).

**GPU 재생성 라운드로 미룬 결함(report13 이후 배치):** C-1(numerology JSON, viz_report2 SBR/GPU)·C-2(재질분해 그림)·C-7(그림 굽힌문구 3)·C-8-full(ghost M=48 재실행).

### 1c. report13 그림 생산자 갭 메움 (2026-07-24)

viz_report13 은 F1~F16+R5~R8 을 그리는데, `experiment_freespace_range.py` 생산자가 **6개 그림 데이터를 안 채워** 우아하게 skip 되고 있었다(스펙 §9 필수 그림 ↔ 구현 갭). **5개 추가**(add-only, 검증 완료):
- **F2 budget_waterfall** — stage_solve 가 d=1km 에서 `fsl.snr_rd_terms_db()` 호출 → `ranges..budget_terms_db`. **대역폭 B 항 없음**을 눈으로(패시브 서사). total=snr_rd_db(자체검증).
- **F4 coverage_C_of_d** — stage_solve 가 d 로그격자 30점에서 C(d)·E_ψ[Pd](d). **커버리지 험프**(근거리 β>90 전방산란+전헤딩 블라인드→C=0, 1-2km 피크 0.75, 원거리 SNR한계 하락) — 비단조 결과.
- **F7 coverage.polar** — stage_solve 가 헤딩 ψ 72점마다 R90(ψ)+blind+alias(나이퀴스트).
- **F11 sensitivity.baseline** — 신규 `stage_baseline_walls()`(main 에서 호출, 결정적 ref=mini5pro). 밴드×L 스윕, thermal/adc74/dpi60/walk 벽. **DPI잔류60 이 최단벽**(R5 일치), walk 는 협대역 무영향.
- **R8 curves.cassini_by_L** — assemble 가 L 50→3000 스윕 cassini(단일→이엽).
- **미룸: R6 rd_frames**(실 MC RD맵 프레임 — GPU 물리, 별도 과제). viz 는 이것만 skip.
- 검증: mavic4pro σ 스모크로 range→verify(12게이트 통과)→viz(**19산출**, R6만 skip) 전 경로 확인. F2 예산합·F11 벽랭킹 물리 타당성 직접 대조.

---

## 2. 재개하면 바로 할 일 (순서대로)

1. **커밋** — 아직 미커밋이다. 아래 §3 의 덩어리별로 나눠 커밋하는 게 읽기 좋다.
2. **워크플로 2건 결과 수확·적용** (§4) — 결함 정정본 검토, 논문 정독 노트 반영.
3. **report13 구현** — 지시서는 [`REPORT13_SPEC.md`](REPORT13_SPEC.md) 하나다(63 KB, 반증 40여 항 판정 반영).
   신규 9파일, **기존 파일 무수정** 원칙. 스펙이 뒤집은 헤드라인 2건(SSB 2000→**50 Hz**, ECA ridge 1e-6→**0**) 주의.
4. **논문 소득 반영** (§5) — E²/(Rλ) 이산화 기준, SBR+PO 그림자 한계, 바이스태틱 실측 앵커.
5. **클러터 모델링 확장** — `VERIFY_CLUTTER.md` 가 스스로 짚은 구멍(유한 ADC 동적범위·클러터
   도플러퍼짐·양자화). Clutter-Aware 서베이 정독 결과를 여기 붙인다.

---

## 3. 미커밋 변경 — 덩어리별

### (a) 메쉬 수정 · σ 캐시 지문 — `src/drones.py` `src/drone_cad.py` `benchmark/channel.py`
- Mini 5 Pro 공식 91 mm 가 **프롭 포함**값인데 프레임에 적용돼 총높이 106 mm 였다 → **전체 91.0 mm**.
  독립검증: 강제 안 한 L/W 의 프롭디스크 외곽 **305.0×381.2** vs 공식 304×380 (**+0.3%**).
- 프롭 허브(0.085R)–루트(0.14R) **간극 4.2~10.5 mm** → `root_frac=0.070` 으로 **1솔리드**.
- σ 영향: **mavic4pro −0.01 dB(결론 불변)**, mini5pro −0.9~−1.3 dB.
- ⭐ `sigma_sbr_cache` 키에 **메쉬 지문**(`_mesh_fp`) 추가 — 없으면 CAD 를 고쳐도 옛 σ 를 조용히 재사용한다.

### (b) 기록물 전수정산 — 신규 `benchmark/audit_outputs.py` · `benchmark/regen_mesh_dependents.py`
- **163건 삭제**: 고아 json 4 · 미참조 이미지 153(**153 MB**) · 죽은 report7 고리 4 · 죽은 viz 2.
- ⚠ import 그래프만으로 죽은 코드를 판정하면 **standalone 실행형 생산자를 지운다**
  (`viz_radar.py`·`viz_report2_photo_compare.py`·`verify_server.py` 는 그래서 남겼다).

### (c) md 감사 43건 반영 — README·ARCHIVE·REPORT_CODE_MAP·VERIFY_*·OPENSOURCE·prior_work·refs
- 거리분해능 규약이 c/2B 로 적혀 **전부 절반**이던 것을 프로젝트 규약 **c/B** 로 통일.
- "SBR 은 유전체 투과 못 함 → +2.00 dB 는 불확실도" → **투과 구현됨, +0.31 dB 측정값**.
- "custom PathSolver 로 확장 가능" → **MRO 실측상 확장점 아님**(3곳 정정).
- 문헌 노트의 우리 σ 를 **숫자 대신 JSON 키를 가리키도록** 변경 — 다시 낡지 않는다.

### (d) 전수 재생성 (outputs/ 전부 최신, 🔴 1건만 잔존)
- K=6000 검출 재실행 — 전 모드 ±0.16 dB, **순위 불변**(G1 15.20 최악 ↔ G2 11.14 최선).
- ⭐ 관측성 **stale 캐시 오염 실증**: `obs_scr_cache` 가 메쉬 지문 없는 키라 07-14 σ 를 재사용 →
  삭제 후 재계산하니 `pos_rms` **66.8 → 57.8 m (−13%)**.
- 잔존 🔴 = `rt_env_clutter.json`(RT 잔향 **폴백 캐시**, 클러터는 죽은 파라미터라 어떤 수치도 안 바꾼다).

### (e) 리포트 서술 정정
- report08: 밴드 불일치 peak(WiFi 정반사 −4.0)를 3–6 GHz 문헌과 비교하던 것 → **3.5 GHz 정렬**(−13.1),
  "문헌 범위 안" → **"포락선의 밝은 상단"**.
- report11: 1RX 조건수 `2e+296`(배정밀도 반올림 잡음) → **"> 1e+12 (수치적 특이)"**.
- `report_mesh/src/verify_mesh_suite.py` 도 프롭포함 비교로 수정 + 부록 8편 재빌드.

### (f) 신규 문서
| 파일 | 내용 |
|---|---|
| `docs/REPORT13_SPEC.md` (63 KB) | ⭐report13 **구현 지시서**(18에이전트 설계 + 반증 40여 항 전량 판정) |
| `docs/REPORT13_DESIGN.md` (64 KB) | 확정 설계(스펙과 충돌하면 **스펙이 이긴다**) |
| `docs/PRIOR_WORK_COMPARISON.md` (118 KB) | 선행 방법론 차용 + 결과 비교(30에이전트, 1,117줄·292표행) |
| `~/workspace/team_meeting/isac_sionna_topvenue/` | ISAC×**Sionna RT**×탑베뉴 논문 베뉴별 정리 |

---

## 3-bis. ⭐report13 **핵심 3파일 구현 완료** (신규, 커밋 대상)

`wf_e9e8583b-c2e` (8에이전트) 가 스펙대로 구현 + 4렌즈 적대감사 + 판정·수정까지 마쳤다.
**기존 파일 0건 수정 · `outputs/` 0건 기록** 확인됨.

| 파일 | 크기 | 공개심볼 |
|---|---|---|
| `src/freespace_scene.py` | 30 KB | 37 (순수함수, I/O 없음) |
| `src/freespace_link.py` | 51 KB | 45 (닫힌형 링크버짓·solver) |
| `src/freespace_detect.py` | 73 KB | 32 (검출기 형상·ECA·CFAR) |

**회귀잠금 통과**: `freespace_scene.selfcheck_vs_repo()` 가 저장소 `bistatic_params`/`look_angles` 와
2000점 대조해 `max|Δ| = 1.8e-12`(el 1.1e-13) — 기하 규약이 기존 파이프라인과 **비트 수준으로 일치**한다.

**감사가 잡아낸 것 중 특히 중요한 것 (전부 수정됨)**
- `n0_thermal` 등의 **기본 대역 1.0 Hz** → 무경보로 **+74.9 dB** 어긋남. 필수인자화 + 유한 depth·b=1 이면 raise.
- `solve_range` 의 `elif np.all(det)` → `grid_limited` 영구 도달불가 + `frac_never` 역전. `det[-1]` 로 교정.
- ⭐**R6(ridge=0)이 데이터 경로에 미도달**이었다 — `experiment_detection.py:189` 에 리터럴 `1e-4` 가 박혀 있어
  스펙이 정한 `ridge_rel=0` 이 실제로 안 쓰였다. `rebuild_residuals()` + `check_eca_provenance()` 로 배선.
  재확인: ridge 0 → 잔류 **−175.5 dB** ↔ 1e-4 → **−70.4 dB**(DNR120 에서 **+60 dB 누설**).
- ⭐**F1 물리 PRF 가 검출기층에 미전달**이었다 — G1 은 커널 2000 Hz vs 물리 **50 Hz(40×)**.
  이제 경고 + `meta.cpi.doppler_axis_physical=False` 로 표시된다.
- `_dev_of` 가 `cuda:0`(타 사용자 카드)를 잡던 것 → `gpu.pick()` 을 torch import 전에 호출.

**기각한 지적 6건**도 근거와 함께 기록됐다(스펙 내부 모순 2건 포함 — `n_taps` ceil↔round, `solve_range` 시그니처).

⚠ **다음 단계**: 스펙 §9 의 나머지 6파일 — `experiment_freespace_sigma.py` · `experiment_freespace_range.py` ·
`benchmark/verify_freespace.py` · `viz_report13.py` · `render_report13.py` · `make_notebook13.py`.

---

## 4. 중단 시점에 돌던 워크플로

| 워크플로 | Run ID | 무엇 |
|---|---|---|
| report13 핵심 3파일 | `wf_e9e8583b-c2e` | ✅**완료** — §3-bis 참고 |
| 리포트 결함 정정 | `wf_f30f0f9c-22f` | ✅**완료**(16에이전트). 리포트 12/12 재빌드·nbformat 검증 통과. 상세는 `docs/AUDIT_FINDINGS_0722.md` §2026-07-23 |
| 논문 8편 정독 | `wf_e3e8c3ad-df0` | ✅**완료**(12에이전트) → **`docs/DRONE_ISAC_PRIOR_READING.md`** (594줄·63 KB, 13편 통합 노트) |

재개: `Workflow({scriptPath, resumeFromRunId})` — 완료된 에이전트는 캐시 재사용.
스크립트 경로는 `~/.claude/projects/*/workflows/scripts/` 아래.

⚠ **결함 정정 워크플로가 무엇을 고쳤는지 반드시 확인할 것** — `git diff src/make_notebook*.py`.
지시서가 지적한 것 중 특히 검증이 필요한 항목:
- report02 "대각거리는 넣은 적이 없는데 저절로 맞는다" → `drones.py:228` 이 대각을 **모터 반경 입력**으로 쓴다.
- report03 "±1 dB 이내" 8회 → 실제 최대 **1.79 dB**. 프롭 대조는 **90° 회전 불일치**, Typhoon 은 bbox 주입이라 **순환논증**.
- report05 crosscheck 가 **G3 하나에서만** 도는데 "세 신호 모두"라 표기.
- 코드 버그: `src/waveforms_sionna.py:61-62` 가 **초 단위를 int 로 절단** → `cp_length_samples: 0`.

---

## 3-ter. ⭐report13 **나머지 6파일 구현 완료** (대량 실행 대기)

`wf_8d103d2e-c28`(7에이전트) 가 스펙 §9~§12 대로 구현 + 3렌즈 감사(spec-conformance HIGH 4건·no-reimpl·headline-flips) 판정·수정.
**기존 파일 0건 변경**(잠금 커널 전부 CLEAN), 6파일 전부 신규(untracked), 1×1 스모크로 end-to-end 검증(그림 0→14/16·verify gates_pass·헤드라인 주입).

| 파일 | 크기 | 역할 |
|---|---|---|
| `src/experiment_freespace_sigma.py` | 28 KB | σ 격자(sbr_sigma_prefill 재사용) → report13_sigma_grid.json |
| `src/experiment_freespace_range.py` | 36 KB | 검지거리 3층 solver → report13_freespace.json |
| `benchmark/verify_freespace.py` | 32 KB | FS-0 동일성검정·비단조·근사검증 → verify_freespace.json |
| `src/viz_report13.py` | 51 KB | 그림 16 + GIF 4 |
| `src/render_report13.py` | 29 KB | RT 렌더/GIF(챔버 없는 자유공간 씬) |
| `src/make_notebook13.py` | 31 KB | report13.ipynb(JSON 주입, 부재 시 graceful) |

**⚠ 대량 실행 규칙**: σ 는 반드시 `--backend direct`(GPU2/3 전용, 기본 prefill 은 GPU0/1 침투). 순서 §16: σ격자→검지거리(드론루프)→verify→viz→render→notebook. 예상 **총 6~10h**(GPU2+3).
**잔여**: 2차 스윕그림 6개(F2/F4/F7/F11/R6/R8)용 `stage_solve` 스윕 산출 추가(budget_terms_db·coverage_C_of_d·coverage.polar·sensitivity.baseline·cassini_by_L·rd_frames).

---

## 4-bis. 결함 정정 결과 — ⭐**진짜 코드 버그 2건**이 나왔다

**코드 버그(수정 완료, 산출물 재생성은 미실행)**
| 파일 | 버그 | 영향 |
|---|---|---|
| `src/waveforms_sionna.py` | CP 길이를 **초 단위 스칼라로 int 절단** → `cp_length_samples` 3행 전부 **0** | 리포트 인용 없음. 수정 후 15 kHz→**160**, 30 kHz→**352** 로 같은 파일의 독립 원장과 일치 |
| `benchmark/verify_pyapril.py` | `CA_CFAR.__call__` 이 **튜플**을 반환하는데 언팩 누락 → `det.shape=(2,7,64)`, 거리축 슬라이스가 **빈 배열** | ⭐`detected_at_truth` 가 **구조적으로 항상 false** 였다. `n_fired` 21k 는 448셀 맵에서 물리적으로 불가능. 네 리포트에서 이 필드 인용을 전부 제거 |

**서술 정정 주요 건**
- report08 "크기 짝" 이 실제로는 짝이 아니었다(s1000plus 1045 mm ↔ Inspire 1 560 mm, **비 1.87**).
  같은 절이 Semkin 을 "비 1.94 라서" 거부하고 있었다 — 자기 규칙 위반. 대각비 ±10% 3행으로 한정.
- σ 결론이 **report07/12 ↔ report08 정반대**였다("포락선 안" vs "+8~16 dB 밖") → report08 기준으로 동기화.
- "편파 보존" 이 거짓이었다 — `rcs_sbr.py:436` 이 `E = 0.0+0.0j` **복소 스칼라**이고 코드에 `polari` 문자열이 0회.
  → "위상 보존(⚠ **편파 미보존**)" 으로 정정.
- "바닥만 반사" 잔존분 → 천장 −9.82 > 바닥 −14.68(4.86 dB)이므로 "설계상 남긴 반사면" 으로 한정.

**⚠ 미해결 8건(C-1~C-8)** — `AUDIT_FINDINGS_0722.md` 에 기록. 특히:
- **C-6** `src/waveforms.py:166` `v_unambiguous_ms` 가 여전히 **모노 등가**(PRF·λ/4). 고치면 viz·experiment·굳은 JSON·그림이 전부 어긋난다.
- **C-2** 재질 분해 원장 이원화(36 az ↔ 121 az, 금속 > 전체 +0.39 dB) — 그림 재생성 필요.
- **C-7** 그림에 **구워진** 문구 3건 — 본문 ⚠ 로 봉합만 해둠.

---

## 5. 논문 정독 소득 (paper_sionna_Ray/ 13편)

### 이미 정독한 5편
| 논문 | 핵심 |
|---|---|
| **Ziganshin** 저널판 (곡면 이산화) | ⭐**Sionna-RT v0.19 를 UTD 정점회절로 확장** — 우리와 같은 자리의 유일한 선행. **E²/(Rλ) 이산화 기준**(후방산란 ≲0.5). **SBR+PO 는 조명영역 한정, 그림자 부적합**이라 명시 |
| **Ziganshin** 학회판 (다중정적) | RT+UTD+VD vs **PO 솔버 vs MLFMM** 속도·정확도. MLFMM ~1시간 / PO ~1일 / RT ~2초. 차량 RCS 최대 **10 dB** 오프셋 |
| **Montaner** (EuCAP 2026) | ⭐**검증 프로토콜** — 실측↔시뮬 **동일 처리**(동일 windowing·DFT·축), 지연-도플러 맵의 ①지배성분 지연 ②ν≈0 능선 안정성 ③이동체 피크. *"λ/10 직접 메쉬는 E-band 에서 불가능"* |
| **Hoydis** (TMLCN) | 미분가능 RT 로 **재질을 실측 보정**. 우리 고정 \|Γ\| 를 학습시킬 정공법 |
| **Li** (상하이대) | Sionna RT 로 **UAV 마이크로도플러**. 단 프롭 1개·재질 "Wood"·**운동학만** 검증. **원뿔 제한 광선 샘플링**으로 원거리 광선희소 문제 해결 |

### ⭐ 새로 발견한 최대 앵커
**Das et al., IEEE Wireless Communications Letters Vol.15 2026** (DOI 10.1109/LWC.2026.3705634)
*Multiband Monostatic and Bistatic RCS Characterization of AAVs* —
DJI **Phantom 2·Phantom 3·Mini 2·M350 RTK**, **1.8~27 GHz**(우리 세 밴드 전부 포함),
**바이스태틱 각 0°:15°:90°**, 무향실 원거리장 + 통제 실내 근거리장, 수직편파, PNA-X N5242B.
→ **우리 `rcs_sbr_multistatic` 을 처음으로 외부 실측과 대조할 수 있다.**
→ log-normal/Gamma/Rician 적합 + **Gaussian-cluster 모델**은 σ 를 "분포로 보고"하는 우리 규약에 차용 가능.
→ 기존 3GPP 관행이 *"−20 dBsm 일정"* 인데 우리 mavic4pro 방위평균 −16.8/−18.4/−16.0 은 같은 자릿수.

### ⭐ 정독 통합 노트 — `docs/DRONE_ISAC_PRIOR_READING.md` (594줄)
13편 전체를 한 문서로. §1 목록 · §2 **σ 외부 앵커** · §3 마이크로도플러 대조 · §4 차용할 방법론 ·
§5 **우리 주장과의 충돌**(검증 통과분만) · §6 클러터 다음 단계 · §7 우리 틈새 · §8 출처.

**σ 앵커의 결론(자세축을 문헌에 맞춘 뒤)**
문헌은 **수평면 el=0**, 우리 JSON 은 **el=15°** 라 그대로 비교하면 안 된다. el=0 으로 재실행해 맞추면:
| 밴드 | multiband(Phantom 3, 모노) | mono3d(Phantom 3, CATR VV) | 우리 phantom4 el=0 | 판정 |
|---|---|---|---|---|
| 3.5 GHz | −18.46 | −15.05 | **−17.72** | **문헌 두 값 사이** |
| 5.2 GHz | −18.10 | −14.51 | **−15.42** | **문헌 두 값 사이** |
| 1.843 GHz | −18.80 | −15.57 | **−21.10** | ⚠ **2.3~5.5 dB 어둡다** |
- 1.8 GHz 미달의 원인은 **우리 저역이 눌렸거나 / 문헌 광대역 단일회귀가 저역에서 낙관적이거나 둘 다**.
  multiband Fig.3(b) 원자료가 1.8–2 GHz 에서 적합선 아래로 내려가므로 **후자도 실재**한다 — 미결.
- ⚠ 같은 캠페인의 두 논문(multiband ↔ mono3d)이 **같은 기체·같은 조건에서 3.2~3.6 dB 다르다**.
  문헌 자체의 재현성 폭이 그 정도라는 뜻이니, 우리 편차를 그 폭 안에서 읽어야 한다.

**바이스태틱 penalty(우리 파이프라인 가정 검증)**: Table III 절편이 θb 0°→90° 에서
Phantom 3 **0.63** · Mini 2 **0.62** · M350 RTK **0.63 dB** — 세 기체 모두 기울기 동일, **각도 무관 상수**.
→ 우리 모노스태틱 등가 조회(`look_angles` 이등분선)의 낙관 편향은 **약 0.6 dB**. 헤드라인 모드격차 3.9 dB 대비 작다.

### 우리 메쉬에 E²/(Rλ) 적용 결과 (이미 계산함)
보정계수 K=1.744(논문과 같은 7λ 구로 교정) 적용, @3.5 GHz:
| 드론 | 중앙값 | p90 | >0.5 비율 |
|---|---|---|---|
| mini5pro | 0.0020 | 0.019 | 0.11% |
| mavic4pro | 0.0041 | 0.030 | 0.11% |
| s1000plus | 0.0026 | 0.065 | 1.27% |
→ **우리 메쉬는 기준보다 2자릿수 곱다**(그들 차량메쉬 0.4~0.6 대비). 기하 이산화는 병목이 아니다.
→ 대신 **PO 적분격자(λ/12=7.14 mm)가 면 모서리(4.0~10.7 mm)와 같은 자릿수** — 병목은 격자 쪽이다.

---

## 6. 이 라운드에서 배운 것

- **캐시는 무엇으로 키를 잡았는지가 전부다.** `sigma_sbr_cache`·`obs_scr_cache` 둘 다 세대를 키에 안 넣어
  코드를 고쳐도 옛 값을 재사용했다. 지문을 키에 넣거나, 최소한 세대가 바뀌면 캐시를 지워야 한다.
- **하드코딩된 숫자는 과장을 숨긴다.** report08 의 "문헌 범위 안" 주장은 σ 를 JSON 주입으로 바꾸자마자
  밴드 불일치가 드러났다.
- **인덱스를 믿지 마라.** 아카이브 `INDEX.md` 의 DUP 표는 **ISAC 컬렉션의 태스크 분류**이지
  Sionna 사용 목록이 아니다. 그걸 믿고 넘겼다가 **비-Sionna 논문 5편**을 후보에 넣었다(사용자가 잡아냄).
  판정은 **PDF 전문에서 직접** — `REFERENCES` 이후를 잘라낸 본문에서 세는 것이 규약.
- **완료 알림을 놓치면 GPU 가 논다.** 긴 작업은 `Monitor` 로 완료 감시를 걸 것.
