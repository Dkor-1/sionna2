> ⚠ **2026-07-31 재편 이전의 기록이다** — 리포트 13편 구조와 `make_notebook*.py` 빌더를 전제한다. 현재 구조는 [`../README.md`](../README.md) 와 [`REPORT_CODE_MAP.md`](REPORT_CODE_MAP.md) 에 있다.

# 재개 지점 — 2026-07-22 (메쉬 수정 + 전수 재생성 + 기록물 정산 라운드)

이 문서 하나만 읽으면 중단 지점부터 이어갈 수 있게 쓴다. 새 대화에서 시작해도 여기서 출발하면 된다.

---

## 1. 지금 상태 한 줄

**재생성은 전부 끝났다.** 하위 파급 산출물 재생성이 완료됐고(아래 §3 진행표 전 항목 ✅),
리포트 01~12 + 부록 mesh 8편도 재빌드했다. **커밋만 안 된 상태**다.
report13 은 **설계 스펙까지 확정**됐다(`docs/REPORT13_SPEC.md` 63 KB) — 구현이 다음 차례.
선행연구 방법론·비교 워크플로는 Write 단계 직전에 세션이 끊겨 **재개 필요**(캐시 재생 가능).

⚠ **동시 세션 주의**: 이 저장소를 두 세션이 동시에 볼 수 있다. 문서를 쓰기 전에 `git status` 와
파일 mtime 을 확인하고, 남의 진행 중 작업을 "정지됨"으로 단정하지 말 것.

⚠ **백그라운드는 Claude 프로세스와 함께 죽는다.** 세션이 끊기면 재생성·워크플로가 모두 정지한다 —
재개 시 `ps` 로 실제 실행 여부부터 확인할 것(로그가 있다고 도는 게 아니다).

---

## 2. 미커밋 변경 (git status: 수정 80 · 삭제 164 · 신규 8)

커밋 전에 `git status` 로 직접 확인할 것. 큰 덩어리는 셋이다.

### (a) 메쉬 수정 — `src/drones.py` · `src/drone_cad.py`
- `DroneSpec.env_props_included` 신설. DJI Mini 5 Pro 의 공식 언폴드 **91 mm 는 프롭 포함**값인데
  프롭 제외 프레임에 적용돼 실제 총높이가 **106 mm(+16.5%)** 였다 → 이제 **전체 드론 91.0 mm**.
  - 독립 검증: 강제하지 않은 L/W 의 **프롭 디스크 외곽 305.0 × 381.2 mm** vs 공식 304 × 380 (**+0.3%**).
- 프로펠러 허브(0.085R)–블레이드 루트(0.14R) 사이 **간극 4.2~10.5 mm**(3.5 GHz 에서 λ/20~λ/8) 때문에
  프롭 1개가 **3개 분리바디**였다 → `root_frac=0.070` 으로 **1솔리드**(전 기종 watertight 유지).
- **σ 영향**: mavic4pro(헤드라인) **−0.01 dB** → 결론 불변. mini5pro **−0.9~−1.3 dB**(높이 축소분).
  프롭 단독은 +1.1~1.3 dB.

### (b) 조용한 stale 경로 차단 3건
1. `benchmark/channel.py` — σ 디스크캐시 키가 `(드론,fc,az,el)` 뿐이라 **CAD 를 고쳐도 옛 σ 를 재사용**했다.
   키에 `_mesh_fp()`(메쉬 정점 md5 8자)를 넣어 **자동 무효화**.
2. `outputs/report3_microdoppler.json` 은 **생산자 없는 고아**인데 `viz_verify_sbr.fig_sbr` 이 계속 읽었다
   → 살아있는 출처(`report1.json["microdoppler"]`)로 교체하고 옛 파일 삭제.
3. **같은 "프레임 vs 전체 드론" 버그가 검증기 3곳**에 각각 있었다 —
   `viz_report1.py` · `viz_verify_sbr.py` · `report_mesh/src/verify_mesh_suite.py`.
   셋 다 `frame_envelope_mm()` 이 주는 `lwh_compare_mm` 를 보게 통일했다.

### (c) 기록물 정산 + 삭제 163건 (전부 git 추적중 → 이력 복구 가능)
- 신설 도구 **`benchmark/audit_outputs.py`** — `outputs/*.json` 마다 생산자·σ의존·세대를 자동 판정.
- 신설 도구 **`benchmark/regen_mesh_dependents.py`** — 메쉬/엔진 변경 시 재생성 5단계 고정.
- 삭제: 고아 json 4 · 미참조 이미지 **153개(153 MB)** · 죽은 report7 고리 4(`rt_pipeline.py` →
  `report7_rt.json` → `viz_report7.py`, 소비자 없음) · 죽은 그림 생산자 2(`viz_articulation.py`·`viz_montage.py`).
- md 감사 **43건 전부 반영**(HIGH 5 / MEDIUM 20 / LOW 18). 리포트 01~12 + 부록 mesh01~08 재빌드 성공.

### (d) 정직성 정정 1건 — report08
전 밴드 peak(**−4.0 dBsm**, WiFi 5.2 GHz 정반사 플래시)를 **3–6 GHz** 문헌(Li & Ling)과 견주며
"실측 문헌 범위 안"이라 주장하고 있었다 = **밴드 불일치 비교**.
→ 밴드 정렬(3.5 GHz peak **−13.1 dBsm**) + 문장을 **"포락선의 밝은 상단, Inspire 1(−13.7)과 어깨를 나란히"**
로 정정. 하드코딩을 JSON 주입으로 바꾸는 순간 드러난 문제다.

---

## 3. 재생성 진행표 (기준: RCS 엔진 대공사 `9f26cee` 07-21 · 메쉬 수정 07-22)

| 산출물 | 상태 |
|---|---|
| `report1.json`(메쉬·CAD) | ✅ 재생성 |
| `report1.json`(microdoppler) | ✅ 재생성 — |DC|/AC 가 최대 −15 dB 이동 |
| `report2_waveform_rcs.json` | ✅ 재생성 (65분) |
| `report6_sbr.json` | ✅ 재생성 |
| `phantom4_scan_compare.json` · `community_compare.json` · `real_cad_compare.json` | ✅ 재생성 |
| `report_mesh/outputs/mesh_verify.json` | ✅ 재생성 (mini5pro 오차 0.00%) |
| `rt_ray_budget.json` · `report3_rt.json` · `rt_target_verify.json` | ✅ 재생성 |
| `verify_linkbudget.json` | ✅ 재생성 — 단일자세 σ 최대 **+12 dB** 이동 |
| `floor_ghost_verify.json` · `verify_ambiguity.json` | ✅ 재생성 |
| `verify_ghost_impact.json` · `detection_ghost.json` | ✅ 재생성 |
| **`detection_rx_sweep.json`** (report12 헤드라인) | ✅ 재생성 (08:05) |
| `verify_eca.json` · `report4_fixups.json` | ✅ 재생성 |
| `verify_observability.json` · `obs_scr_cache.json` | ✅ 재생성 — ⭐**stale 캐시 오염 실증**: `pos_rms` 66.8 → **57.8 m**(−13%) |
| `rt_no_rcs_verify.json` | ✅ 재생성 |
| `verify_cfar.json` (대량 MC, 10,000맵) | ✅ 재생성 (21분) |
| `report5_results.json` (run_matrix) | ✅ 재생성 |
| `detection_rx_sweep.json` **K=6000 재실행** | ✅ 재생성 — 전 모드 ±0.16 dB, **순위 불변**(G1 15.20 최악 ↔ G2 11.14 최선) |
| `rt_env_clutter.json` | ⚪ 미재생성 — RT 잔향 **폴백 캐시**이고 클러터는 죽은 파라미터라 어떤 수치도 안 바꾼다 |

⚠ **재생성 후 반드시 리포트를 다시 빌드할 것**: `for n in 01 ... 12; do python src/make_notebook$n.py; done`

---

## 4. 재개 시 할 일 (순서)

1. **커밋** — 아직 한 번도 커밋 안 했다. §2 의 (a)~(d) 를 나눠 커밋하는 게 읽기 좋다.
2. **선행연구 워크플로 재개**(§5) → `docs/PRIOR_WORK_COMPARISON.md` 수확 + 리포트별 삽입 지시서 적용.
3. **report13 구현** — 지시서는 **`docs/REPORT13_SPEC.md`** 하나다(63 KB, 반증 40여 항 전량 판정 반영).
   신규 9파일: `freespace_scene/link/detect` → `experiment_freespace_sigma/range` →
   `verify_freespace` → `viz_report13` · `render_report13` · `make_notebook13`.
   **기존 파일은 하나도 안 고친다**(report01~12 재현성 보호).
   ⚠ 스펙이 뒤집은 헤드라인 2건: **SSB 반복률 2000 → 50 Hz**(저장소 자체 `PILOT_RATE_HZ` 가 근거,
   → G1 이 꼴찌가 되어 '5G 이중고' 서사 복원), **ECA `ridge_rel` 1e-6 → 0**(스모크로 1e-6 이 누설 확인).
4. **클러터 모델링 확장** — `docs/VERIFY_CLUTTER.md` 가 스스로 짚은 구멍: 실제 ECA 는
   **유한 ADC 동적범위·클러터 도플러퍼짐·양자화** 때문에 완벽하지 않은데 *"그 한계는 아직 모델에 없다"*.
   그걸 넣어야 `CH_CLUTTER_RATIO` 가 죽은 파라미터에서 살아난다.

---

## 5. 실행중이던 워크플로 2건 (Claude 프로세스와 함께 죽는다 — 재개 필요)

같은 대화 세션이면 `resumeFromRunId` 로 이어붙고, 완료된 에이전트는 캐시가 재사용된다.
새 대화면 스크립트 파일을 그대로 다시 돌리면 된다.

| 워크플로 | Run ID | 스크립트 |
|---|---|---|
| ~~report13 설계~~ **✅ 완료**(18에이전트·2.36M토큰) → `docs/REPORT13_SPEC.md`·`REPORT13_DESIGN.md` | `wf_ad438803-855` | `~/.claude/projects/-workspace-sionna2/ffa746a7-*/workflows/scripts/report13-freespace-detection-range-wf_ad438803-855.js` |
| 선행연구 방법론 차용+결과 정량비교(13편 병렬) | `wf_24618712-c19` | `~/.claude/projects/-workspace/ffa746a7-*/workflows/scripts/priorwork-methodology-and-comparison-wf_24618712-c19.js` |

두 번째 워크플로의 산출물은 **`docs/PRIOR_WORK_COMPARISON.md`** 와 리포트별 삽입 지시서다.
이건 2026-07-22 사용자 지시(선행 방법론 최대한 차용 + 우리 결과와 선행 결과 정량 비교)를 이행하는 작업이다.

---

## 6. 이 라운드에서 배운 것 (다음에 또 안 밟으려고 적는다)

- **생산자 추적은 `src/` 만 훑으면 안 된다** — `benchmark/` 와 부록 `report_mesh/` 까지 봐야 한다.
  이걸 몰라서 감사 플래그 2건을 오탐으로 올렸었다.
- **고아 판별법**: `grep -rn "<name>.json" --include=*.py .` 결과에 `json.dump`/`open(...,"w")` 가
  하나도 없으면 고아다. 고아는 코드를 고쳐도 숫자가 안 변해서 조용히 거짓말한다.
- **숫자를 산문에 하드코딩하면 그게 stale 의 온상**이다. JSON 키에서 주입하게 바꾸는 순간
  report08 의 밴드 불일치 과장이 스스로 드러났다. 문헌 노트(`refs/drone_papers/*.md`)의 우리쪽 σ 도
  전부 숫자를 빼고 **JSON 키를 가리키게** 바꿔 두었다.
- **import 그래프만으로 죽은 코드를 판정하면 살아있는 생산자를 지운다** — `viz_radar.py`·
  `viz_report2_photo_compare.py` 는 아무도 import 하지 않지만 standalone 으로 돌려 리포트 그림을 만든다.
- **nohup 셸 작업은 세션 재시작을 견디고, 워크플로는 못 견딘다.** 오래 걸리는 계산은 셸로 띄울 것.
- **캐시는 무엇으로 키를 잡았는지가 전부다.** `sigma_sbr_cache` 와 `obs_scr_cache` 둘 다 메쉬·엔진
  세대를 키에 안 넣어서, 코드를 고쳐도 옛 값을 조용히 재사용했다. `channel._mesh_fp` 처럼
  **지문을 키에 넣거나**, 최소한 세대가 바뀌면 캐시를 지워야 한다.
- **하드코딩된 숫자는 과장을 숨긴다.** report08 의 "문헌 범위 안" 주장은 σ 를 JSON 주입으로 바꾸자마자
  밴드 불일치(WiFi 정반사 peak 를 3–6 GHz 문헌과 비교)가 드러났다. 손으로 적은 숫자는 검증을 회피한다.
- **완료 알림을 놓치면 GPU 가 논다.** 긴 작업은 `Monitor` 로 완료 감시를 걸어라 —
  한 번은 65분짜리가 끝난 걸 35분간 못 알아채고 GPU 4장을 놀렸다.
