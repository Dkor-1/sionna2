> ⚠ **2026-07-31 재편 이전의 기록이다** — 리포트 13편 구조와 `make_notebook*.py` 빌더를 전제한다. 현재 구조는 [`../README.md`](../README.md) 와 [`REPORT_CODE_MAP.md`](REPORT_CODE_MAP.md) 에 있다.

# 재개 지점 — 2026-07-30 06:40 (작업 일시중단)

**이 문서부터 읽는다.** 누적 세부는 [`RESUME_0729.md`](RESUME_0729.md) 에 있다(그쪽이 훨씬 길다).
여기는 **중단 시점의 상태 + 새로 받은 대전환 지시**만 담는다.

⚠ 전부 미커밋: 변경 **229** 파일 + 미푸시 커밋 **3개**(report14 건). 가장 무방비한 자산이다.

---

## 1. ⭐⭐ 새 지시 — 리포트 전면 재구성 (아직 **착수 전**)

사용자 지시 원문 요지 (2026-07-30):
1. **순수 PO 로만 한 것은 전부 제거** — 코드에서도, 리포트에서도 나타내지 말 것
2. **앞으로 모든 실험은 SBR+PO 또는 선행연구 논문의 방식**만 사용
3. **리포트 1~13 을 전면 재구성** — 쓸모없다고 판단되는 편은 **삭제**하고,
   순서를 **실질적 의존성**에 맞춰 재배열(뒤 리포트에 영향 주는 것을 먼저)
4. 거리별 마이크로도플러는 **메쉬를 Sionna 에 올려 SBR 로** 관측하는 형태를 원한다

### 착수 전 조사로 확인한 실태 (중요 — 삭제 범위가 좁다)
- **기본 엔진은 이미 SBR 이다.** `rcs_po.drone_rcs_pattern(engine=None)` 의 기본이 `"sbr"`
  (Mitsuba 광선 + PO 적분, **가림 포함**). 파일 이름이 `rcs_po.py` 라서 순수 PO 처럼 보였을 뿐,
  리포트 σ 대부분은 이미 SBR+PO 다.
- **진짜 순수 PO(`engine="po"`, 가림 없음)는 네 곳뿐:**

  | 위치 | 용도 | 처리 |
  |---|---|---|
  | `run_matrix.py:369`, `channel.py:478` | SBR 과 나란히 놓는 **대조 팔** | 결과 아님 — 판단 필요 |
  | `viz_verify_po.py` → report06 그림 3장 | PO 커널 검증 | **제거 대상** |
  | `microdoppler_series` / `microdoppler_nearfield` | 회귀잠금 + 거리스윕 | **제거/대체 대상** |
  | `experiment_md_range.py` | 거리별 마이크로도플러 | **SBR 로 재구축** |

- ✅ **순수 PO 마이크로도플러는 리포트에 나간 적이 없다** (빌더에서 참조 0건).
  즉 `outputs/md_range_sweep.json` 과 그림 8장은 미공개 상태 → 삭제해도 리포트 파급 없음.
- 두 마이크로도플러 경로: `microdoppler_sbr`(**Sionna Mitsuba/OptiX + 가림**, report1 정본)
  ↔ `microdoppler_series`(순수 PO, 대조군). **정본은 이미 SBR 이다.**

### ❓ 사용자 확인 대기 중인 질문 (재개 시 가장 먼저)
`report08` 이 구 검증에서 **"해석 PO 대비 편차"** 를 인용한다. 이건 우리가 PO 로 계산한 *결과*가
아니라 **기준해**다(Mie 와 나란히 놓는 정확해). 오늘 kr 스윕이 밝혔듯 커널이 SBR+PO 이므로
**수치 수렴의 과녁은 해석 PO 가 맞고**, 지우면 "우리 오차" 와 "PO 근사의 대가" 를 구분할 수단이 사라진다.
→ **내 판단: 엔진으로서의 PO 는 제거, 기준해로서의 해석 PO 는 유지.** 사용자 확인 필요.

### 재개 시 진행 계획 (합의 전 초안)
1. 순수 PO 결과 제거(`viz_verify_po` 산출물 · report06 PO 검증 절 · 순수 PO 마이크로도플러 경로)
2. **거리별 마이크로도플러를 SBR 경로로 재구축** — 위상각마다 씬을 다시 지어야 해서 비싸다.
   먼저 **한 기종·한 거리로 시간을 재고** 격자 규모를 정할 것.
3. 리포트 13편 의존성 재배열 + 불요 편 삭제

⚠ **재구성을 시작하면 지금 돌던 계산 일부가 버려질 수 있다** — 구조가 바뀌면 필요한 산출물도 바뀐다.
그래서 "지금 멈추고 설계부터" 를 권고했고, 사용자가 중단을 선택했다.

---

## 2. 🔴 중단 시점에 **실패**한 것 — 내가 만든 회귀

### report2 재생성 OOM — **내 "화끈하게" 변경이 원인**
```
RuntimeError: jit_malloc(): out of memory! Could not allocate 1073741824 bytes
  at src/rcs_sbr.py:227 _lit_g_phase → mi.Point3f(si.p)
```
경위: `viz_report2.py:45` 에 `SIONNA2_GPU_MEM=4000` 하드코딩이 있었다. 24.5 GB 여유에서 4 GB 만
쓰는 게 아까워 **여유 비례 적응식**으로 바꿨고(GPU3 → 19.5 GB 예산), 그러자 Mitsuba 가 거대한
광선 배치를 잡다 죽었다.
**그 4000 이 바로 이걸 막던 값이었다.** 파일 주석이 정확히 경고하고 있었다 —
*"20 GB 짜리 광선 배치를 한 번에 올리면 그 사이 남이 잡은 만큼 모자라 Mitsuba 가 **트레이스백 없이
죽는다**(실측: §4.4 진입 직후 사망)"*. 실제로 §4.4 에서 죽었다. **같은 자리, 같은 원인.**

→ **재개 시 반드시 할 것**: `_adaptive_gpu_mem()` 의 `SIONNA2_R2_MEM_FRAC`(현재 0.70)을 크게 낮출 것.
  Mitsuba JIT 은 예산 밖에서 별도로 1 GB 단위 할당을 하므로, **PyTorch 기준의 여유 비례가 그대로
  적용되지 않는다**. 안전한 출발점은 6000~8000 MiB 고정, 또는 frac 0.25 이하.
  ⭐ 교훈: **하드코딩 상한을 걷어낼 때는 그 값이 왜 거기 있었는지부터 읽어야 한다.**

### 그래서 차단 요소가 **아직 안 풀렸다**
`outputs/report2_waveform_rcs.json` 은 여전히 **07-29 04:00** 판이고 `dither` 키가
`[avg_err, div, hi, lo, spread]` — 재배선된 `viz_report2.fig_sbr_validation` 이 요구하는
`lo_prod · spread_prod · jitter · avg_err_prod` 가 **없다**. 즉 **리포트 재빌드는 여전히 불가**다.
(다만 §1 재구성으로 이 그림 자체가 바뀔 수 있으니, 재구성 설계를 먼저 하는 게 맞다.)

---

## 3. 중단 시점 실행 상태

| 작업 | 카드 | 경과 | 상태 |
|---|---|---|---|
| `rcs_anchor` 7종 큐 | 2 | 1h12m | s1000plus 진행 중, 큐로그 비어 있음(아직 1종도 완료 안 됨) |
| `experiment_freespace_sigma` 7종 큐 (`--backend direct`) | 2 | 58m | **s1000plus 완료(exit=0)**, 다음 기종 10분째 |
| `verify_cfar` | 3 | 42m | 진행 중 (q3 드라이버가 report2 사망 후 자동 기동) |
| `viz_report2` | 3 | — | 🔴 **OOM 사망**(위 §2) |
| 검출 헤드라인 | 3 | — | q3 큐에서 cfar 다음 순서, 아직 시작 안 함 |

로그: `scratchpad/` 아래 `p4_report2.log` `p4_cfar.log` `a7_*.log` `s7_*.log`
큐: `anchor7_queue.log` `sigma7_queue.log` `q3.log`
⚠ 전부 `nohup … & disown` 이라 **세션이 죽어도 계속 돈다**. 재개 시 `ps` 로 먼저 확인.
⚠ 재개 시 **고아 프로세스**도 확인(`ps -eo cmd | grep venvs/py312`) — 워크플로 에이전트가 남긴
  것이 GPU 를 물고 다른 작업을 죽인 전례가 있다.

---

## 4. ✅ 이 라운드에서 끝난 것 (되돌릴 필요 없음)

### 7종 통합 완료 — 기존 5종 **비트단위 동일**
- `typhoonh480`(헥사, 대각 480, 프롭 230.2) · `x500v2`(쿼드, 대각 500, 프롭 254.0) 등록
- ⭐ 검증: 4종 메쉬(프레임·드론·프롭CW·프롭CCW) × 5기종 = **20개 메쉬 전부 float64 원비트 sha256 동일**.
  s1000plus 는 원형판이 신규 `_body_plate_stack` 을 통과하는데도 비트동일.
- **가드 13/13 발동**(plate_mm 누락·오타, 열린프레임 arm_style, gear 치수 누락, 카본 데크를 셸로
  선언 → ValueError, gazebo DENSITY 누락 → KeyError)
- ⭐ **대각비례 탈출 실증**: X500 암이 16.00 mm 등단면 튜브(실물 16). 옛 코드면 **폭 55 mm**.
- 신규 그룹 `deck`→carbon · `gear_cf`→carbon · `fc`→pcb, **7종 재질 매핑 누락 0**
- ⚠ `DRONE_GROUP_MAT` 은 `materials.py` 가 아니라 **`drones.py:233`** 에 있다(내 지시문이 틀렸었다)

### GPU 방침 3단 기준 구현 (사용자 지시)
**0순위 GPU 2·3 선호 → 1순위 메모리 여유 → 2순위 util+temp 낮은 것.**
`pick()` · `all_usable()` 양쪽 적용, 4가지 상황으로 시험 통과. 자세한 함정은
[`memory/sionna2-gpu-policy.md`](../../.claude/projects/-home-yunjung-workspace/memory/sionna2-gpu-policy.md).
- ⚠ `SIONNA2_GPU` 핀을 `all_usable()` 이 무시해 `BrokenProcessPool` 이 났다 → 핀 존중 추가
- ⚠ σ격자는 **`--backend direct`** 필수(파일 자신이 prefill 을 GPU 제한 상황에서 쓰지 말라고 적어놨다)
- ⛔ **`pkill -f` 금지** — 오늘 2회 내 셸이 죽었다(exit 144). PID 수집 후 `kill`.

### 그밖에 오늘 끝난 것
- `PFA_CALIBRATION` 을 **측정 JSON 우선 + 리터럴 폴백 + 낡음 경고**로 구조 전환(경고 발동 확인).
  실측 대비 LTE 1e−4 −11.4% · 1e−5 −13.1% 어긋나 있었다.
- 원장 이중화 3건 화해(가림 3값 = 같은 양의 세 집계, 유령 100%↔0% = 스냅샷 vs 궤적평균,
  블라인드속도 = 이름이 같은 셋). ⚠ 내 결함기록 2건이 틀렸었다(§RESUME_0729 참조).
- 리포트 빌더 5개(06·07·08·12·13)에 **임포트 거부 가드** — 임포트만으로 리포트를 덮어쓰던 것
- `provenance.py` 빈문자열 함정, `verify_cfar` 생성시각 누락 수정
- kr 스윕 최초 실행 — 광학영역 해석PO 대비 **0.47%**(λ/16). 기록된 "Sagitta 대비 6배" 재현 안 됨

---

## 5. 재개 절차

1. `ps -eo pid,etime,cmd | grep venvs/py312` — 살아있는 것과 고아 확인
2. `cat scratchpad/{anchor7,sigma7,q3}_queue.log` — 큐 진행 확인
3. **§1 의 확인 질문**(해석 PO 기준해 유지 여부)을 사용자에게 먼저 묻는다
4. 리포트 재구성 설계 → 그 설계가 요구하는 산출물만 다시 계산
5. `_adaptive_gpu_mem()` frac 을 낮춘 뒤에야 report2 재시도(§2)
