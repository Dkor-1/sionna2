# 수정 재검증과 0930 큐의 조사 가치

시작 HEAD `ea9638f1f5ee4fb1bcf4565d6e68e225596f5dff` · 종료 HEAD `ea9638f1f5ee4fb1bcf4565d6e68e225596f5dff`.
완료 시각: 2026-09-14T01:07:40Z. 큐 관측 시각: 2026-09-14T01:06:54Z (UTC). 감독자 로그의 로컬 시각은 별도로 그대로 보존했다.

## 판단

주요 수정은 실행과 수치로 확인됐다. 다만 오류 입력의 조기 반환·샤드 진단·텍스트 관문·파생 비교에는 남은 결함이 있어 전체 종료로 묶기는 이르다. 큐는 조사할 가치가 있으며, 완료된 자료의 판독과 비교 조건 정리가 다음 실험 추가보다 먼저다. 실기 정확도의 확인과 이번 소프트웨어 회귀 재현은 구분한다.

## 확인된 수정

- 분류 자가검사: R13 칸 384 개 · 열 1080 개 비교 · 최대 |Δ| = 0.0000 dB (허용 0.02) · 칸이 적은 박자 [120.0, 126.667, 148.9, 183.333] Hz · 표집률 [19700.0, 39400.0, 78800.0] Hz
- 기체별 보조 표: 210행에서 현재 기체별 계산과 발간 열의 불일치 0행. f_flash의 저장 반올림을 적용해 대조했다.
- 파형 원장: 2388 = 505 + 1883. 행 정체성으로도 빠진 것 0, 추가·중복 0.
- 장면 원장: 2388 = 범위 밖 2136 + 71 + 181. 대상 행의 누락 0, 추가·중복 0.
- 직하방의 띠 전용 봉우리 누출: 0행.
- production_merge·atlas_check·저장 중단 시험이 현재 의존성으로 실행된다. 저장 중단은 의도한 OSError를 내며 불완전 파일을 재개 완료로 인정하지 않는다.
- 복소 계수 시험: [{'phase': 0, 'pass': True}, {'phase': 90, 'pass': False}, {'phase': 180, 'pass': False}]. 동일 신호와 위상 회전 신호의 판정이 수정됐다.
- 노트북 거절 반례: 기존 파일 보존 True, 거절본 보존 True, 임시 파일 잔존 0.
- 기존 관문 결과: {'check_new_file_rules': 0, 'check_report_links': 0, 'check_row_pointers': 0, 'check_retracted': 0, 'check_stale_titles': 0}. 이 통과가 아래 합성 반례나 해석 문제까지 검사했다는 뜻은 아니다.

## 남은 보완점

### 1. 장면 판독기의 조기 반환이 실제 main에서 다시 예외를 낸다

**분류:** 재현한 입력 처리 결함

유효한 원장 비교 쌍을 두고 샤드만 비운 임시 실행에서 생산 main은 TypeError: cannot unpack non-iterable NoneType object로 끝났다. series는 자료 없음·표집률 혼합·불완전 커버리지에서 None 하나를 반환하지만 main은 항상 두 값으로 푼다. 정상 자료의 행 수가 닫히는 것과 오류 입력 처리의 완결성은 별개다.

**권고:** series의 모든 반환을 (전계 또는 None, 사유 목록)으로 통일하고 실제 main에서 자료 없음·미완성·표집률 혼합을 각각 재현한다.

원장: `outputs/queue_followup_0914.json` → `checks.scene_main_missing / checks.reader_inputs`

- [benchmark/read_scenephysics_0913.py:92](../benchmark/read_scenephysics_0913.py#L92) — `def series(esm, arm, el, n_poses_ledger=None):`
- [benchmark/read_scenephysics_0913.py:283](../benchmark/read_scenephysics_0913.py#L283) — `Es, why_s = series(esm, r["engine"], el, r.get("n_poses"))`

### 2. 두 raw 판독기가 세대 충돌과 샤드 메타데이터 이상을 여전히 통과시킨다

**분류:** 기존 지적 잔존 · 임시 반례

세대 선택 결과 kept_conflicting_poses=8인데 두 판독기 모두 뒤쪽 파일의 전계로 덮고 통과했다. 두 번째 샤드의 NaN 표집률, 음수 idx, 서로 다른 meta 표본수도 통과했다. 이유는 선택 진단을 버리고, 첫 파일에서만 크기·표집률을 취하며, idx를 배열에 대입한 뒤 유한성만 확인하기 때문이다. 음수 idx는 NumPy에서 끝 기준 인덱스이므로 예외 없이 잘못된 저장을 허용한다. 현재 실제 창고에서 이 합성 오류가 발생했다고 판정한 것은 아니다.

**권고:** one_generation의 남은 충돌 진단을 확인하고 모든 샤드의 idx 범위·정수성·중복·meta 표본수·유한 양수 표집률을 대입 전에 대조한다. 명시적으로 해결된 세대 선택까지 일괄 거절하는 처방은 피한다.

원장: `outputs/queue_followup_0914.json` → `checks.reader_inputs`

- [benchmark/read_wfsurvive_0912.py:116](../benchmark/read_wfsurvive_0912.py#L116) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_scenephysics_0913.py:97](../benchmark/read_scenephysics_0913.py#L97) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_wfsurvive_0912.py:128](../benchmark/read_wfsurvive_0912.py#L128) — `E[ii] = z["E"]`
- [benchmark/read_scenephysics_0913.py:113](../benchmark/read_scenephysics_0913.py#L113) — `elif abs(_p - prf0) > 1.0:`

### 3. 발간 텍스트 관문은 정상 문장을 거절하고 다른 표기 값은 통과시킨다

**분류:** 새 관문의 양방향 반례

실제 publish가 “NaN 감지”와 “NaN 때문에 제외했다”를 거절했다. 반대로 표 칸의 “h1 nan”, 굵게 표시한 nan, 코드 서식의 nan은 발간했다. 사용자가 보고한 혼합 칸 “띠 안 nan · -6.0 dB”는 올바르게 거절한다. 그 수정의 성공과 모든 표기에서의 판정 완결성은 구분해야 한다.

**권고:** 숫자는 구조화된 원장에서 유한성을 검증하고, 표 렌더러가 숫자·없음·사유를 구분해 출력하게 한다. 텍스트 검사는 보조 검사로 두고 숫자 꼬리표와 Markdown 서식 처리, 정상 사유 문장의 허용을 명시한다.

원장: `outputs/queue_followup_0914.json` → `checks.text_publish`

- [src/reader_gate.py:121](../src/reader_gate.py#L121) — `if any(c.isdigit() for c in pre) or len(pre.strip()) > _LABEL_MAX:`
- [src/reader_gate.py:123](../src/reader_gate.py#L123) — `if len(post) > 8:`
- [src/reader_gate.py:151](../src/reader_gate.py#L151) — `for part in _PART_SPLIT.split(cell):`

### 4. 공통 입력 관문의 예외 없는 반환 약속에도 경계 누락이 있다

**분류:** 잠재 입력 처리 결함

n_poses=무한대는 OverflowError, prf_seen에 문자가 있으면 ValueError를 낸다. 원장 PRF와 유일한 prf_seen 값이 서로 달라도 통과하며, 소수인 표본수는 int로 잘려 실제 정수 길이와 같으면 통과한다. 정상 자료의 결과가 틀렸다는 뜻은 아니지만 입력 관문 자체의 계약을 좁히거나 구현을 보완해야 한다.

**권고:** 정수 표본수와 유한 양수 표집률을 변환 전후로 검증하고, prf_seen 전체를 원장의 prf와 대조한다. 변환 실패는 사유로 반환한다.

원장: `outputs/queue_followup_0914.json` → `checks.series_gate_boundary`

- [src/reader_gate.py:64](../src/reader_gate.py#L64) — `want = int(n_poses)`
- [src/reader_gate.py:82](../src/reader_gate.py#L82) — `seen = sorted({float(x) for x in prf_seen})`

### 5. 추출 경계 검사가 서로 다른 함수의 지역변수를 합쳐 누락을 가린다

**분류:** 잠재 감사 결함 · 합성 소스로 재현

f()가 미제공 전역 missing을 읽고 g(missing)는 같은 이름의 인자를 받을 때 새 functions 경계 검사는 통과한다. 그 후 f() 실행에서 NameError가 난다. 현재 atlas_check와 production_merge의 원래 누락은 고쳐져 실행되지만, 새 검사가 향후 같은 유형의 누락을 전부 잡는다는 보장은 없다.

**권고:** 함수별 스코프를 구분해 전역·자유 이름을 검사하고, 다른 함수의 매개변수나 지역 대입이 의존성을 제공한 것으로 집계되지 않게 한다.

원장: `outputs/queue_followup_0914.json` → `checks.extract_scope_boundary`

- [benchmark/review_latest_readers_0910.py:70](../benchmark/review_latest_readers_0910.py#L70) — `assigned, readn = set(), set()`
- [benchmark/review_latest_readers_0910.py:74](../benchmark/review_latest_readers_0910.py#L74) — `elif isinstance(n,ast.arg): assigned.add(n.arg)`

### 6. 조건 혼합 관문이 깊이 비교에 전파되지 않았다

**분류:** 현재 발간 비교의 해석에 영향

depth_pairs 63쌍 중 21쌍은 mesh_fix 또는 blade_law가 다르지만 혼합 표시 없이 깊이 판정으로 들어간다. 계측 불가인 리듬 값 None을 실패 False로 집계한 행도 4개다. 예를 들어 직하방은 해당 띠가 퇴화하므로 물리적 깊이 민감도 실패와 계측 불가를 구분해야 한다. 새 스위치 조건 관문은 적용됐지만 이 별도 루프에는 적용되지 않았다.

**권고:** 깊이 외 조건이 같은 쌍을 구성하고 비교 부적격·계측 불가·기준 초과를 분리한다. G 큐가 채우는 정본 깊이 자료로 해당 쌍을 다시 구성한다.

원장: `outputs/queue_followup_0914.json` → `checks.depth_comparisons`

- [benchmark/switch_factorial.py:590](../benchmark/switch_factorial.py#L590) — `a, b = cells[k1], cells[k3]`
- [benchmark/switch_factorial.py:610](../benchmark/switch_factorial.py#L610) — `row["rhythm_within_3pp"] = bool(row["d_rhythm_pp"] is not None`

### 7. 수정된 판정과 옛 확정 문장이 현재 완전요인 원장에 공존한다

**분류:** 현재 발간 문면의 잔존 오류

복소 거리와 같은 조건 쌍을 쓰는 새 판정은 확인됐다. 현재 주판정에 쓰는 유효 쌍은 2개다. 그러나 A_headline_ko는 제외된 옛 기본 비교의 계수 0.92(±0.04), 잔차 11.8%(백색)를 계속 머리기사로 쓴다. E_axis_mechanism의 항목별 reads_ko는 바꾼다고 쓰면서 E_axis_mechanism_ko는 D·E·F가 얹는 축이라고 단정한다. 현재 원문의 전체 값은 checks.factorial에 보존했다.

**권고:** 머리기사·기작 설명·적용 범위를 현재 사용한 비교 쌍과 판정에서 함께 생성한다. 가정 척도 통과와 물리적 기작 입증을 구분하고, 백색잡음 단정도 동일한 규칙으로 정정한다.

원장: `outputs/queue_followup_0914.json` → `checks.factorial.verdict / checks.factorial.headline`

- [benchmark/switch_factorial.py:840](../benchmark/switch_factorial.py#L840) — `verdict["A_headline_ko"] = (`
- [benchmark/switch_factorial.py:831](../benchmark/switch_factorial.py#L831) — `E_axis_mechanism=mech, E_axis_mechanism_ko=mech_note,`

### 8. 아틀라스의 기본 기체 명시 태그 검사가 여전히 오경보를 낸다

**분류:** 검사 문면 보완

팔별 반송파·프로펠러 배율 검사와 최신 색인 규모는 맞는다. 다만 기본 기체 matrice4e를 이름에 명시한 팔까지 기본 박자와 달라야 한다는 검사가 남아 실패한다. 원장 박자 정수배 검사의 불일치와 이 검사식 자체의 오경보는 서로 다른 문제다.

**권고:** 기체별 명세 값과 직접 비교하고 기본 기체와 달라야 한다는 조건은 실제로 다른 박자를 가진 기체에만 적용한다.

원장: `outputs/queue_followup_0914.json` → `checks.atlas_toc`

- [benchmark/build_atlas_toc.py:523](../benchmark/build_atlas_toc.py#L523) — `out.append(("기체 태그 팔의 박자가 원장 기본값과 **다르다**(그대로 썼으면 틀렸을 자리)",`

### 9. 대역 판독기가 중심 주파수 레벨 민감도를 대역 모양의 판정 문턱으로 쓴다

**분류:** 현재 판정 설계와 큐 C 활용의 결함

현행 main은 중심 반송파만 ray_spread_db에 넘기고 대역 퍼짐이 그 값의 두 배를 넘는지로 크다/묻힌다를 나눈다. 주파수별 곡선이 동일하고 예산 변경이 공통 레벨만 1 dB 이동시키는 합성 반례에서 주파수 대비 변화는 0 dB인데 생산 판정은 크다=False다. 이는 현재 자료의 물리적 정확도를 증명하는 반례가 아니라, 중심 레벨 변화로 대역 모양의 식별 가능성을 판정하는 일반 논리의 반례다. C가 새로 사는 비중심 주파수 예산 쌍도 현재 대조 통계에는 들어가지 않는다.

**권고:** 각 예산의 동일 주파수 쌍으로 대역 대비 곡선과 그 변화량을 계산한다. 민감도 기술 통계와 판정 문턱을 구분하고 가정 없는 두 배 기준의 확정 표현을 제거한다.

원장: `outputs/queue_followup_0914.json` → `checks.ray_control`

- [benchmark/read_bandflat_0913.py:635](../benchmark/read_bandflat_0913.py#L635) — `ray_spread, ray_n = ray_spread_db(_ctr["engine"], el, J["rows"], Z, 0.05)`
- [benchmark/read_bandflat_0913.py:703](../benchmark/read_bandflat_0913.py#L703) — `if mv_band > 2.0 * ray_spread else`

## 큐 현황

[09-14 04:14:57] == 종료 (18 줄 실행 · 실패 0 · 큐 18/18) ==

0930은 88줄 중 시작 45, 종료 35, 종료코드 실패 0다. 실제 워커 프로세스 10개. 회절·모서리회절 활성 줄은 0개다.
queue_chain_done은 완료 증명이 아니라 시작 확인 또는 포기 처리 표식이다. 이 파일에 0930이 있어도 진행 중일 수 있다. 실제 상태는 감독자 종료 기록·프로세스·샤드 내용을 대조했다.

| 묶음 | 전체 줄 | 상태 | 완료 자료의 일꾼시간 |
|---|---:|---|---:|
| A | 20 | {'complete': 20} | 30.93 |
| B | 14 | {'complete': 14} | 15.46 |
| C | 10 | {'running': 9, 'complete': 1} | 1.18 |
| D | 8 | {'running': 1, 'pending': 7} | 0.00 |
| E | 20 | {'pending': 20} | 0.00 |
| F | 12 | {'pending': 12} | 0.00 |
| G | 4 | {'pending': 4} | 0.00 |

완료 안정 샤드 35개에서 CRC·배열 길이·idx 분할·유한 전계·meta·예산을 확인했다. 품질 오류 0개, 현재 규칙으로 상한 근접한 자세 0개. 이 상한 근접 진단이 후보 생성의 무손실 증명은 아니다.
141 일꾼시간은 발주 당시 장면별 단가에 따른 계획값이며 현재 남은 시간이 아니다. 실제 처리시간은 표에 별도로 기록했다. 병렬 자원·장면별 시간 차이 때문에 나눗셈만으로 완료 시각을 확정하지 않는다.

## 큐를 어떻게 읽을 것인가

### A. 조각 장면·굴절 — 유용 · 완료 자료부터 판독

건물만 둔 굴절 팔 5칸의 빈 하늘 대비 평균 진폭 dB 차이는 절댓값 최대 0.0001171 dB다. 두 자리 반올림 영과 정확한 영을 구분한다. 건물 단독 효과가 작다는 사실로 전체 장면에서 건물의 역할까지 영이라고 단정하면 지면·건물 상호작용을 놓친다.

### B. 고도 — 유용 · 판정 문장 수정

생산 구현은 드론만 올리는 대신 환경 부품 전체를 수직 이동한다. 상대기하 실험으로 읽어야 한다. 실외 el -60°·고도 80 대 기본 20 m에서 DC 전력 -19.840 dB, AC 전력 -20.209 dB인데 리듬 몫은 13.06 → 12.26%다. 비율이 비슷해도 절대 바닥은 크게 변한다. ‘리듬 몫이 널 근처면 지면 탓이 아니다’는 판정은 성립하지 않는다.

### C. 광선 예산·대역 — 우선 판독 가치 높음

실제 새 예산은 [3900000000], 앙각은 [-60.0]°뿐이다. 기준 4000000000에서 한쪽으로 줄인 비교로, ± 변동이나 다른 앙각까지의 사다리는 아니다. 각 예산의 주파수 대비 D(f)=L(f)−L(f중심)를 먼저 만들고 D새−D기준을 비교한다. 개별 칸의 공통 레벨 이동으로 대역 기울기를 곧바로 거절하지 않는다. 이 비교는 결정적 격자 민감도이며 신뢰구간이 아니다.

### D. 직하방 끝점 — 범위 확장에 유용

직하방의 레벨을 읽고 날개끝 띠 지표는 계측 불가로 둔다. 끝점에서 값이 다시 증가해도 기존 내부 국소 최대의 존재가 사라지는 것은 아니다. 곡선 형상 관측으로 쓴다.

### E. 촘촘한 반송파·위상 — 필요하지만 판독 설계가 선행돼야 함

자료가 오기 전에도 알려진 단일 지연·복수 지연·상쇄점을 합성해 지연 제거와 감김 복원의 조건을 시험할 수 있다. 알려진 공통 지연을 먼저 제거하고, 작은 전계에서 불안정한 위상·경로 집합 변화·잔여 지연 범위를 구분한다. 간격이 촘촘하다는 사실만으로 복원 가능성이 보장되지 않는다. C와 새 주파수 조건이 같은지도 확인한다.

### F. 표집률 — 가치 있음 · 동일 시간 구간 비교 필수

표본수는 8192로 고정이다. PRF를 19700 → 157600 Hz로 바꾸면 관측 시간 0.415838 → 0.051980 s, DFT 간격 2.404785 → 19.238281 Hz, 날개 통과 주기 52.673 → 6.584개가 된다. 시간 길이·분해능이 함께 변한다. 공통 시간 구간과 일치하는 자세 시각을 비교하고 넓은 스펙트럼만으로 독립 잡음을 판정하지 않는다.

### G. 굴절 깊이 1 — 비용 대비 우선 가치 높음

현재 깊이 비교의 메쉬 혼합 21/63 문제와 연결된다. 정본 깊이 1 자료를 채운 뒤 같은 조건 쌍으로 바꿔 읽는다. 깊이 차이가 ‘같은 자릿수’라는 것만으로 수렴했다고 판정하지 말고 실제 잔차와 사용 목적에 필요한 오차를 함께 제시한다.

## 완료된 새 자료의 관측

아래는 저장 전계를 idx로 합친 기술 통계다. 외부 계측, 경로 기여의 인과 분해, 공식 발간 갱신을 대신하지 않는다. 평균 크기의 dB와 평균 제거 전력의 dB를 구분했다.

| 묶음 | 팔 | 앙각 | 기준 대비 평균 크기 dB | 기준 대비 DC 전력 dB | 기준 대비 AC 전력 dB | 리듬 몫 기준→새 % |
|---|---|---:|---:|---:|---:|---|
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2` | -75 | +50.554629 | +50.650610 | +35.342125 | 52.39 → 13.16 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2` | -60 | +55.717101 | +56.385026 | +39.263052 | 62.69 → 12.63 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2` | -45 | +60.238216 | +64.968748 | +37.943562 | 63.95 → 13.05 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2` | -30 | +61.200837 | +70.474428 | +36.717361 | 58.67 → 12.96 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_ground_mfixbatteryi5_blperairframe_d2` | -15 | +44.261201 | +44.277047 | +42.352472 | 58.58 → 12.05 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_bldg_mfixbatteryi5_blperairframe_d2` | -75 | -0.000101 | -0.000083 | -0.000135 | 52.39 → 52.39 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_bldg_mfixbatteryi5_blperairframe_d2` | -60 | +0.000083 | -0.000076 | +0.000470 | 62.69 → 62.68 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_bldg_mfixbatteryi5_blperairframe_d2` | -45 | -0.000024 | +0.000338 | +0.000201 | 63.95 → 63.94 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_bldg_mfixbatteryi5_blperairframe_d2` | -30 | +0.000117 | -0.000184 | -0.000058 | 58.67 → 58.69 |
| A | `sionna_p4000000000_swR1D0E0F1_r15_n8192_envoutdoor01_bldg_mfixbatteryi5_blperairframe_d2` | -15 | -0.000056 | -0.000054 | -0.000207 | 58.58 → 58.59 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_alt40_mfixbatteryi5_blperairframe_d2` | -30 | -8.299408 | -8.299667 | -9.895120 | 12.48 → 12.34 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_alt80_mfixbatteryi5_blperairframe_d2` | -30 | -15.318056 | -15.319302 | -16.422685 | 12.48 → 12.2 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_alt40_mfixbatteryi5_blperairframe_d2` | -60 | -11.774626 | -11.776612 | -12.245827 | 13.06 → 11.61 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_alt80_mfixbatteryi5_blperairframe_d2` | -60 | -19.832556 | -19.839583 | -20.209235 | 13.06 → 12.26 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_alt80_mfixbatteryi5_blperairframe_d2` | -30 | -15.318039 | -15.319309 | -16.404450 | 12.47 → 12.2 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_alt40_mfixbatteryi5_blperairframe_d2` | -60 | -11.781963 | -11.784172 | -11.861954 | 12.45 → 11.58 |
| B | `sionna_p4000000000_swR0D0E0F1_r15_n8192_envoutdoor01_ground_alt80_mfixbatteryi5_blperairframe_d2` | -60 | -19.833656 | -19.840629 | -20.163147 | 12.45 → 12.64 |

기준 팔과 원정밀도는 checks.fresh_descriptive에 있다. 고도 비교의 기준은 같은 환경의 기본 고도이며, A 비교의 기준은 같은 스위치의 빈 하늘이다.

## 여러 파일의 발간과 실기 대조에 대한 의견

파일별 원자성과 여러 파일을 묶은 일관성을 구분한 설명은 맞다. 다만 디렉터리 통째 교체만이 해법은 아니다. 세대별 불변 파일과 마지막에 원자적으로 바꾸는 manifest 포인터를 쓰면 독자가 한 세대만 읽게 할 수 있다. 가벼운 보완은 JSON·문서에 같은 build_id와 입력 해시를 남겨 혼합을 검출하는 것이다. 후자는 감지책이며 여러 파일의 원자성을 제공하지 않는다.
실기 계측 부재는 현실 정확도와 기작 입증의 한계다. 입력 관문 통과·특정 반례 재현·생산 함수와의 수치 일치까지 모두 같은 말로 지우기보다, 무엇을 확인했는지 범위를 붙여 적는 편이 정확하다.

## 재현 범위와 산출물

인용 20개를 줄·문자로 확인했다. 입력 해시 변경: [].
이번 범위는 최신 수정·명시된 생산 함수·임시 반례·현재 큐의 안정 완료 샤드다. 전체 과거 샤드 재검사나 실기 시험은 하지 않았다. 분류 전체 학습을 다시 실행한 것이 아니라 저장된 결과를 대상으로 현재 selftest를 실제 실행했다. 전체 보고서 묶음의 바이트 동일 재빌드는 별도로 실행하지 않았다.
생산 코드·기존 발간물·큐 순서는 바꾸지 않았다. 새 감사 생성기·JSON·Markdown·Jupyter와 검사 캐시를 남겼다. 작업 중 늘어난 큐 로그와 샤드는 다른 실행 작업의 산출물이다.

```bash
/workspace/.venvs/py312/bin/python benchmark/review_queue_followup_0914.py
```

캐시에서 문서만 생성하려면 `--publish`를 붙인다. 큐 스냅샷은 매 실행 시점의 값이다.
