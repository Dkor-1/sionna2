# 리포트 재편 계획 (2026-08-16 심사 완료, 실행 대기)

⚠실행 게이트: 큐 소진 + 재병합 완료 후(원장 안정). 실행은 세션 안에서 단계 검증하며.
심사: 18/18 KEEP (각 권 수정 목록은 워크플로 기록 wf_39e96f63 참조).

# /workspace/sionna 리포트 재편 계획 (심사 18/18 KEEP 반영)

전제 사실 (디스크 실측): 권 층은 `src/build_volumes.py`의 `VOLUMES`(16개) + `EXTERNAL`(8권 5편) + `COMPANIONS`(11-2)가 정본이고, 18권(스위치 격자)은 자기 빌더 docstring이 "17권 체계 밖 작업 보고서"라 선언한 채 색인·README 밖에 있다(volumes_index n_volumes=17, README에 18 없음, reports/*.ipynb 23개=색인 22+18권 1). 조각(00~88)·REG(`report_registry.py`+`outputs/restruct_exec_plan.json`)·색인 샤드(`outputs/reports_index/`)·`docs/REPRODUCE.md`는 전부 **조각 번호 층**이라 권 번호와 무관하다. 조각 안의 권 참조는 대부분 `ref()`→`build_volumes._relink()`가 배치표에서 자동 재유도하므로, 손으로 고칠 것은 빌더에 하드코딩된 문자열뿐이다(전수 목록 아래 2-B).

---

## 1. 최종 편성표

DEMOTE 권 없음(18/18 KEEP) → 파츠 강등·각주 이관 대상 없음. 재편 = 순번 재배열 + 18권의 체계 편입 + 색인·목차 재생성. 슬러그는 전부 유지, 번호만 바꾼다. **01~07은 번호 불변**(편집 반경 절반).

| 새 | 서사 박자 | 권 | 옛 | 파일 (새 이름) |
|---|---|---|---|---|
| 01 | 장면 | map | 01 | 01_map.ipynb (불변) |
| 02 | 장면 | stock-engine | 02 | 불변 |
| 03 | 장면 | prior-work | 03 | 불변 |
| 04 | 장면 | target-mesh | 04 | 불변 |
| 05 | 커널 | kernel | 05 | 불변 |
| 06 | 검증 | anchor | 06 | 불변 |
| 07 | 검증 | size-law | 07 | 불변 |
| 08 | 앙각 | elevation-coverage | 16 | 08_elevation-coverage.ipynb |
| 09 | 스위치 | engine-physics | 17 | 09_engine-physics.ipynb |
| 10 | 스위치 | switch-grid | 18 | 10_switch-grid.ipynb (체계 신규 편입) |
| 11 | 기동/잡음 | 마이크로도플러 5편 | 08 | 11_1_scene … 11_5_bistatic.ipynb |
| 12 | 기동/잡음 | microdoppler-limits | 09 | 12_microdoppler-limits.ipynb |
| 13 | 기동/잡음 | illuminators | 10 | 13_illuminators.ipynb |
| 14 | 기동/잡음 | detector (+별편 14-2) | 11, 11-2 | 14_detector.ipynb, 14_2_two_channel.ipynb |
| 15 | 기동/잡음 | observability | 12 | 15_observability.ipynb |
| 16 | 결과 | results | 13 | 16_results.ipynb |
| 17 | 결과 | robustness | 14 | 17_robustness.ipynb |
| 18 | 실측 | measurement | 15 | 18_measurement.ipynb |

- 치환은 **11-순환**이다: 08→11→14→17→09→12→15→18→10→13→16→08 (01~07 고정). 순차 sed 가 불가능한 구조 — 반드시 자리표시자 2단 치환(아래 2-C).
- 파일 23개 중 16개 개명, 이름 충돌 0건(슬러그가 달라 old/new 동명 없음). 재조립 후 옛 이름 16개 git rm. 파일 수 23 불변이 검증 불변량.
- 앞당김의 대가: 새 08~10이 마이크로도플러 낱말을 11권보다 먼저 쓴다. 완화 — (a) 새 08·09 머리말 논지에 "무늬 축의 정의는 리포트 11" 한 줄(VOLUMES thesis 문자열 수정으로 충분), (b) 05권이 이미 격자얼림·무늬 개념을 도입함. 대안(앙각·스위치를 md 뒤에 두는 안)은 지시된 서사와 어긋나고 편집 반경도 같아서 기각.
- 예약 슬롯: EXPERIMENT_MAP D.4의 "리포트 16-2 본문"(15 m 재설계판) → 새 체계에서 **08의 별편 08_2**(COMPANIONS)로 예약. 조각 81(el-beat-vs-tip) 미건축·조각 00 superseded는 현행 유지.

## 2. 실행 절차

### 2-A. 게이트 (실행 전)
1. `ps -eo pid,etimes,cmd | grep -E '[b]uild_|[m]ake_report|[e]levation_sweep'` — 좀비 세션·병행 빌더 확인(감시만, kill은 수동).
2. **원장 안정 게이트**: EXPERIMENT_MAP D.1(elevation_sweep_md.json 재병합)·D.2(mini5pro RPM 재실행)가 도는 동안 조각 재빌드 금지 — 반쯤 병합된 원장이 조각에 주입된다. 재편은 원장을 안 읽지만 재조립이 조각 빌더 재실행을 포함하므로 같은 게이트에 걸린다.
3. 심사 KEEP-수정 중 같은 빌더 파일을 고치는 건(16권 "광선 40억발" 4곳=build_part12_elevation.py, 17권 [^65] 4e9 오기=build_part13, 18권 "같은 광선 예산"·"45~62%"=build_report18)은 **재편과 같은 라운드에 태우는 것을 권장** — 상류(내용) 정정 후 한 번의 재조립으로 둘 다 반영.

### 2-B. 상호참조가 끊기는 지점 — 전수 (여기 없는 것은 재조립이 자동 복구)
자동 복구(손대지 않음): 조각 간 "편 NN" 링크(placement 재배선), 01_map 지도·배치표·읽기 경로, reports/README.md, 루트 README.md(make_readme, 지금도 "열다섯 권"으로 낡음—이번에 자동 회복), volumes_index.json. **불변 확인 대상**: report_registry.py, restruct_exec_plan.json, outputs/reports_index{,.json}, docs/REPRODUCE.md, docs/paper/ — 전부 조각 층, diff 0이어야 정상.

수동 편집 필요(하드코딩, 파일:행은 2026-08-14 스냅샷 — 실행 시 아래 grep으로 재채굴):
1. `src/build_volumes.py` — VOLUMES 16개 튜플 번호, EXTERNAL no="08"→"11"+files 08_K→11_K+append_to→11_3_pattern.ipynb, COMPANIONS 키 "11"→"14"·label "11-2"→"14-2"·file→14_2_two_channel.ipynb. **코드 확장 1건**: 10권(switch-grid)용 STANDALONE 목록(단일파일·조각 없음·headline 수동) 추가, N_VOLUMES·_ordered_nos·_vol_entry·_write_readme·_map_cells에 반영(약 20줄). 재현 블록의 스크립트명 문자열은 스크립트 개명 안 하면 불변.
2. `src/make_report08_microdoppler.py` — H1 "리포트 8-1~8-4"(654,880,1122,1371), NAV·파일명 08_K(601~604,649,766~772,1089~1090,1124,1250,1505), "8 권" 산문(601,716,772,1455,1603), 리포트 15/15_measurement(132,707)→18, 09_microdoppler-limits(1091,1251)→12, 10_illuminators(1252)→13, 리포트 11-2(774)→14-2. 리포트 5/05_kernel(226,287,290)은 **불변**.
3. `src/make_report07b_bistatic.py` — OUT(32)→11_5_bistatic, H1 8-5(196), "8 권" 약 30곳, 08_2_engines(104,409)→11_2_engines, 리포트 11-2(628,839)→14-2, 15 권(30)→18. 05_kernel(473) 불변.
4. `src/make_report11_2_two_channel.py` — OUT(29)→14_2_two_channel, H1 11-2(253), "11 권" 약 10곳→14, "13 권"(295,320,322,357,370,832)→16, "15 권"(594,877)→18, "8 권"(314,815,869)→11, "10 권"(783)→13.
5. `src/build_report18_switch_grid.py` — out(153)→10_switch-grid, H1(65)·docstring(3) 18→10, 리포트 16(13)→8, 리포트 17(150)→9, "17 권 체계"(12)→"18권 체계" 문구 갱신.
6. 조각 빌더 6+2개 — build_part04_kernel.py(리포트 8: 115,122,130,137→11; 8 권 121; 리포트 8-2+08_2_engines 139,524→11-2/11_2_engines), build_part07_microdoppler.py(8 권 118; 리포트 11-2 1572,1583→14-2), build_part08_illuminators.py(648,774), build_part09_detector.py(283,474), build_part10_results.py(608,839), build_part11_measurement.py(184) — 전부 리포트 11-2→14-2. docstring만: build_part12_elevation.py(22), build_part13_engine_physics.py(18, 슬러그도 이미 오기).
7. 옛 권 파일 16개 잔존 — 재조립은 새 이름으로 쓰므로 옛 파일을 지우지 않으면 이중 문서가 남는다(git rm 필수).
8. 위험한 함정 둘: (a) 순환 치환 — "리포트 8-2"→11-2와 기존 "리포트 11-2"→14-2가 겹친다. 반드시 자리표시자(예: 리포트 8-2→⟪V11-2⟫, 리포트 11-2→⟪V14-2⟫ 전부 찍은 뒤 일괄 해소) 2단으로. (b) sed 오폭 — 16권 본문의 "8/11 덱"은 날짜 표기, "리포트 07"(make_report08 docstring)은 legacy 이력 — 자동 일괄치환 금지, 행 단위 확인.

인벤토리 재채굴 명령: `cd src && grep -nE "리포트 ?[0-9]+(-[0-9])?|[0-9]{2}(_[0-9])?_[a-z0-9-]+\.ipynb|[0-9]+ ?권" build_part*.py make_report08_microdoppler.py make_report07b_bistatic.py make_report11_2_two_channel.py build_report18_switch_grid.py` (조각 파일명 NN_slug 매치는 제외하고 판독).

### 2-C. 재조립 순서 (기존 ①→④ 규약 유지)
1. 조각 빌더 14개 전부 재실행 → `_parts/` 갱신 (조각 번호·REG·샤드 불변 확인: `git diff --stat outputs/reports_index* outputs/restruct_exec_plan.json` = 0).
2. make_report08_microdoppler.py → 11_1~11_4 / make_report07b_bistatic.py → 11_5 / make_report11_2_two_channel.py → 14_2 / build_report18_switch_grid.py → 10.
3. build_volumes.py (반드시 2 다음 — 11_3 뒤에 조각 34~39 덧붙임) → 권 조립+색인+reports/README.md.
4. 옛 파일 16개 git rm → `ls reports/*.ipynb | wc -l` = 23 확인.
5. make_readme.py → 루트 README.md.
6. 검증: `benchmark/check_report_links.py` 위반 0 + 옛 파일명 16종 전수 grep(`grep -rlE "08_[1-5]_(scene|engines|pattern|sampling|bistatic)|11_2_two_channel|16_elevation|17_engine-physics|18_switch-grid|09_microdoppler-limits|10_illuminators|11_detector|12_observability|13_results|14_robustness|15_measurement" reports/*.ipynb src/`) = 0건 + volumes_index n_volumes=18·n_parts_placed=87 확인.
7. docs 갱신(아래 3) 후 경로 지정 커밋·푸시 1회.

## 3. 위험 목록 — 옛 번호를 가리키는 바깥 문서

| 위험도 | 위치 | 내용 → 조치 |
|---|---|---|
| 상 | `/workspace/teammeeting_0818/ROADMAP.md` :14,106,109,176,192 | reports/08_1~08_5·08_2_engines·08_3_pattern·08_5 — 다음 덱 작업이 옛 주소로 진행될 위험 최상 → 11_K로 갱신 |
| 상 | 메모리 `acdc-metric-artifact.md`(:3,:41) + MEMORY.md 색인줄 | "리포트 17 헤드라인 재검토" — 안 고치면 다음 세션이 새 17(robustness)을 때린다 → "리포트 9"로 갱신 + **옛↔새 환산표 메모리 노트 신설** |
| 상 | `docs/EXPERIMENT_MAP.md` :31 | "리포트 16 정정, 리포트 16-2 본문" → "리포트 8 정정, 별편 8-2" |
| 중 | `docs/RESUME.md` :196 등 | "리포트 08_3 자기모순" 및 0812 판정표 문맥 → 재편 라운드 기록과 함께 갱신(work-log 규율) |
| 중 | `docs/REPORTS_VOLUMES.md` | 수기 구조 문서, 이미 "열다섯 권·78조각"으로 낡음 → 18권 체계로 재작성 |
| 중 | 루트 legacy 스텁(report00~07*.ipynb)+`src/make_legacy_stubs.py`(:101 reports/00_map, 조각 링크가 reports/NN로) | 이미 죽은 링크(재편 무관 기존 결함) → 같은 라운드에 01_map·_parts/ 경로로 수리 권장 |
| 하 | 역사 문서: PLAN_VOLUMES_16_17.md, outputs/volumes_16_17_plan.json, AUDIT_VOL8_ENGINES.md, PLAN_FIX_VOL8.md, RESUME_07xx, REPORTS_ADVERSARIAL_0810.md 등 | 옛 번호 기준 기록 — 고치지 말고 머리에 "2026-08-1x 재편 전 번호" 배너 1줄 |
| 하 | 메모리 sionna2-* 다수의 reportNN | 더 옛날 12편 체계의 역사 기록 — 액션 없음(환산표 노트가 방어) |
| 없음 | decks/*.pptx·teammeeting_0811 빌더·figs 스크립트 | 리포트 번호 참조 0건 실측(그림 캡션에도 "report 17" 없음) — 동결 |

## 4. 본체가 정할 결정점
1. **10권 처리**: 기본안=STANDALONE 편입(위 계획). 대안=원설계대로 새 09에 절로 흡수(18 빌더 docstring이 예고) — 24조합 격자 병합 후 규약화 시점에 하는 것이 자연스러워 이번 라운드에서는 비권장.
2. **스크립트 개명 여부**: 기본안=유지(make_report07b가 8-5를 내는 기존 선례; docstring에 "산출은 11권" 주석만). git mv 하면 build_volumes 3곳+make_readme STEP_LEAD+docs 추가 편집 필요.
3. KEEP-수정(내용 정정) 동승 범위 — 2-A-3 참조.
4. 커밋 단위: 빌더 편집+재조립+옛 파일 삭제를 한 커밋으로(중간 상태가 이중 문서라 쪼개면 위험), docs·메모리는 후속 커밋 가능.