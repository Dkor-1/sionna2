# 시오나 현재 상태 재점검 — 2026-09-11

검토 기준 커밋: `00b8766288ace89559939d3fd263ac844ef4f271`. 실행 시각: 2026-09-11T01:45:28.732774+00:00.

현재 코드·발간 원장·기존 샤드의 읽기 전용 검토다. 운영 코드·기존 원장·작업 큐·발표 자료를 수정하거나 솔버를 실행하지 않았다.

[주피터 보고서](CURRENT_STATE_REVIEW_0911.ipynb) · [재계산 원장](../outputs/current_state_review_0911.json) · [생성기](../benchmark/review_current_state_0911.py)

```bash
cd /workspace/sionna
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_current_state_0911.py
```

## 수정이 확인된 부분

- 아틀라스 전체 1433개 칸에서 변경 34개는 모두 ps 조건이다. 나머지 1399개 칸의 JSON 객체는 수정 전과 같았다. 완전한 ps 조건 33개는 현재 함수와 저장 신호로 리듬 몫·빗살 대비를 재계산해 발간값과 대조했다.
- 생산자 f_tip와 아틀라스 f_tip를 대조한 허용 오차 초과 불일치는 0개였다. 허용 오차는 max(0.2 Hz, 0.1% of producer tip)다. 이는 운동학적 기준 대역의 일치 검사다.
- 협곡 10개 조건·낙차 7개 조건의 발간 수를 원본 샤드 54개에서 재계산했다. 이 원본의 인덱스 완전성·유한값·대조 시간축 검사는 통과했다.
- 협곡의 stored/recomputed 진단 분리, 낙차의 미계측값 제외, 자카드 분모 명시, 0923C의 널 띠 판정 제거를 확인했다.

## 남은 수정점

### 1. 상한 진단 보정이 협곡 판독기에만 적용되고 주 원장 병합에는 남았다

**확인 수준:** 실제 재고로 재현 · 다음 병합의 경고 누락

**근거와 범위:** 저장 n_trunc와 nret가 함께 있는 617개 샤드 중 14개가 현재 문턱 재계산과 달랐고, 12개는 저장값이 영이었다. 이 중 현재 주 원장에 포함된 샤드는 0개다. 완전한 예시 256표본 묶음에서 현 병합기의 진단 블록을 그대로 실행하면 경고 0개, 저장 상한 2000000에 현재 문턱을 적용하면 256개다. 현재 아틀라스가 이 자료를 깨끗한 것으로 발간했다고 주장하는 것은 아니다. 다음 병합 때 옛 진단을 다시 쓰는 경로가 남아 있다는 뜻이다. 경고는 반환 수 기반 상한 근접 진단이며 실제 후보 잘림의 직접 증거와 구분한다. 병합기의 상한 미기록 자료에 대한 기본값 대입도 새 판독기와 정책이 다르다.

**권장 수정:** 저장 진단·당시 상한·현재 문턱의 재계산을 병합기에도 함께 보존한다. 상한 미기록이나 실행 조건 혼합은 미확인으로 표시하고, 다른 샤드의 상한을 근거 없이 빌리지 않는다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[0]` 및 `checks`.

- [elevation_sweep_md.py:1115](../benchmark/elevation_sweep_md.py#L1115)
```python
n_tr += int(_nt[0]); n_seen += int(ii.size)
```

- [elevation_sweep_md.py:1135](../benchmark/elevation_sweep_md.py#L1135)
```python
_cap_for_old = cap_seen if cap_seen else _cap_default
```

- [read_canyonnull_0910.py:109](../benchmark/read_canyonnull_0910.py#L109)
```python
recomputed=int(np.count_nonzero(nr >= 0.99 * cap)),
```

### 2. 비정수 중앙값을 처리한 새 분기가 화면 출력에서 종료된다

**확인 수준:** 수정으로 추가된 실행 오류 · 합성 입력 재현

**근거와 범위:** 완전한 입력에서 n_dup 중앙값을 1.5로 만들면 copies_median이 None이 된다. 실제 main()은 TypeError: unsupported format string passed to NoneType.__format__로 종료했고 원장 생성 여부는 False였다. 현재 발간된 낙차 조건에서는 이 오류가 나타났다고 확인한 것이 아니다. 비정수 처리 분기의 반환값과 출력 형식이 맞지 않는 문제다.

**권장 수정:** 숫자 저장과 표시 문자열을 분리한다. 정수가 아닌 중앙값도 그대로 보존하고, 복제 배수로 해석할 수 없는 경우에는 사유를 출력한다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[1]` 및 `checks`.

- [read_dropladder_0910.py:129](../benchmark/read_dropladder_0910.py#L129)
```python
_copies = (int(_dmed) + 1) if (_dmed is not None and float(_dmed).is_integer()) else None
```

- [read_dropladder_0910.py:149](../benchmark/read_dropladder_0910.py#L149)
```python
f"{r['n_both']:>6}{r['copies_median']:>9}"
```

### 3. 입력 검증에 기준선·메타데이터·유한값의 빈틈이 남았다

**확인 수준:** 수정 미완료 · 합성 입력 재현

**근거와 범위:** 중복 인덱스 반례는 새 검사에서 idx_ok=False로 거절되어 수정 효과가 있다. 그러나 샤드별 선언 표본 수와 PRF가 다른 입력은 idx_ok=True로 통과한다. 메타데이터 없는 4096행 입력도 idx_ok=True이며, 비유한 전계를 포함한 입력도 idx_ok=True다. Hampel 표는 비교 대상의 idx_ok를 보지만 기준선의 idx_ok를 확인하기 전에 마스크를 만든다. 기준선에 idx_ok=False를 전달해도 비교 대상 행이 출력되는 것을 실제 Hampel 함수로 재현했다. 이들은 현재 원본이 오염되었다는 발견이 아니라 판독기의 검증 범위 문제다.

**권장 수정:** 기준선과 비교 대상에 같은 검증을 적용한다. 예상 표본 수는 실행 조건으로 확인하고, 각 샤드의 선언·시간축·전계 유한성을 함께 검사한다. 온전한 이전 실행을 최신 부분 실행으로 덮어 고르는 방식은 사용하지 않는다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[2]` 및 `checks`.

- [read_canyonnull_0910.py:136](../benchmark/read_canyonnull_0910.py#L136)
```python
n_expected = int(_m[3])          # 이 칸이 원래 몇 자세짜리인가
```

- [read_canyonnull_0910.py:142](../benchmark/read_canyonnull_0910.py#L142)
```python
and (n_expected is None or idx.size == n_expected)
```

- [read_canyonnull_0910.py:172](../benchmark/read_canyonnull_0910.py#L172)
```python
if base is None:
```

- [read_dropladder_0910.py:84](../benchmark/read_dropladder_0910.py#L84)
```python
and (n_expected is None or idx.size == n_expected)
```

### 4. 부분 계측에서도 전체 사건 집합이 일치했다는 표지가 붙는다

**확인 수준:** 해석 범위 누락 · 합성 입력 재현

**근거와 범위:** n_dup 계측 4096개·미계측 4096개인 입력에서 n_short=0, n_dip=0, dip_equals_short=True가 나온다. 저장된 두 마스크의 동일성 자체는 맞다. 그러나 미계측 자세가 실제로 복제 부족이었는지는 알 수 없어 전체 자세의 관계를 확인한 뜻으로 쓰면 과하다. 현재 발간된 낙차 조건은 중복 계측이 모두 있어 이 제한으로 기존 숫자를 철회할 이유는 확인하지 못했다.

**권장 수정:** 계측된 공통 모집단에서의 일치와 전체 모집단 판정 가능 여부를 별도 필드로 둔다. 미계측이 있으면 전체 일치는 미확인으로 표시하되 전체 진폭 낙차 수는 유지한다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[3]` 및 `checks`.

- [read_dropladder_0910.py:123](../benchmark/read_dropladder_0910.py#L123)
```python
short = have & (D < 2)              # 같은 줄이 세 번 안 적힌 자세(계측된 것만)
```

- [read_dropladder_0910.py:124](../benchmark/read_dropladder_0910.py#L124)
```python
dip = (a / med) < DIP               # 덱 2 쪽 규칙
```

- [read_dropladder_0910.py:143](../benchmark/read_dropladder_0910.py#L143)
```python
dip_equals_short=bool(int(short.sum()) == int(dip.sum())
```

### 5. 이전 검토의 재현 코드도 현재 소스 변경을 따라가지 못한다

**확인 수준:** 검토 산출물 자체의 재현성 결함

**근거와 범위:** 제가 작성한 이전 검토 빌더의 atlas_check()를 현재 환경에서 호출하면 NameError: name 'prop_scale_tag' is not defined가 발생했다. 원인은 새 arm_rates가 호출하는 보조 함수가 AST 추출 목록에 빠진 것이다. 그 함수만 추가해도 해결은 끝나지 않는다. 이전 검토는 보정 전 대역에 배율을 추가하는 계산이므로, 이미 보정된 현재 함수에 그대로 적용하면 이중 보정이 된다. 기존 검토 결과는 당시 상태의 기록으로 유지하고, 현재 상태와 혼동해서 다시 생성하면 안 된다.

**권장 수정:** 역사 재현용 입력·소스 커밋과 현재 회귀 검사용 계산을 구분한다. 이번 보고서는 현재 보정된 대역을 그대로 사용하여 발간값을 재계산한다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[4]` 및 `checks`.

- [review_latest_readers_0910.py:170](../benchmark/review_latest_readers_0910.py#L170)
```python
['airframe_tag','arm_rates','f_tip_at','comb_contrast_db','rhythm_share'],ns)
```

- [review_latest_readers_0910.py:179](../benchmark/review_latest_readers_0910.py#L179)
```python
ft=ns['f_tip_at'](rates,float(el));correct=ft*ps
```

- [build_md_atlas.py:295](../benchmark/build_md_atlas.py#L295)
```python
ps = prop_scale_tag(arm)
```

### 6. 수정된 해석과 예전 판정 문구가 작업 문서에 함께 남았다

**확인 수준:** 남아 있는 문서 간 불일치

**근거와 범위:** 0923C의 널 띠 판정과 최신 재개 문서의 해당 문구는 수정됐다. 하지만 make_jobs_0924.py에는 잔존 개수가 같아서 격자 변경과 구별되지 않는다는 문장이 남아 있다. jobs_0920.txt의 유사 판정은 재개 문서에서 사용 제한을 붙인 상태이며 원문만 읽으면 그 제한을 놓칠 수 있다. 사건 목록의 차이와 통계적 효과의 구분 가능성은 다른 주장이다. 두 배율의 집합이 같다는 사실만으로 독립성을 판정하지 않는다.

**권장 수정:** 잔존 개수는 같고 사건 목록은 달랐다는 관찰로 통일한다. 이미 실행된 작업 줄은 보존하면서 결과 판독에 적용할 최신 규칙을 원문 가까이에 연결한다.

근거 원장: `outputs/current_state_review_0911.json` → `findings[5]` 및 `checks`.

- [make_jobs_0924.py:13](../runners/make_jobs_0924.py#L13)
```python
⇒ 줄이는 쪽은 2.5 배를 훑어도 **전부 80** 이라 격자를 갈았을 때와 구별되지 않는다.
```

- [RESUME_0911.md:152](../work/sweep_0904/RESUME_0911.md#L152)
```python
⚠같은 뿌리가 이미 구운 `runners/jobs_0920.txt` 의 죽는조건 다섯 곳에도 있다(:15·20·29·30·55).
```

- [jobs_0920.txt:15](../runners/jobs_0920.txt#L15)
```python
#      죽는 조건  둘째 벌의 3.8e9↔4.2e9 자카드가 첫 벌의 0.9222 에서 0.03 넘게 떨어져 있으면 «널 띠 0.889~0.922» 라는 말을 쓰지 않는다 — 그때는 널이 한 점짜리이므로 목요일 덱에서 자카드 수를 통째로 뺀다(runners/jobs_0919.txt:10 의 규약 그대로). 두 벌이 0.03 안에서 붙으면 그 띠를 잣대로 세우고 ③④⑥ 의 사다리를 그 위에서 읽는다.
```

## 우선순위와 한정

먼저 낙차 판독기의 출력 예외를 고치고, 기준선과 비교 대상의 입력 검증을 일치시킨다. 주 원장을 다음에 병합하기 전에는 상한 진단의 세대 처리를 통일한다. 이어 부분 계측의 일치 표지와 작업 문서의 표현을 정리한다.

이번 합성 입력의 실패를 현재 발간 데이터의 손상으로 소급하지 않는다. 원본 인덱스 검사를 통과했다고 저장 이전의 후보 누락이나 물리적 정확성까지 확인한 것도 아니다. 덱 전체의 안전성은 이번 검토의 판정 대상에 포함하지 않았다. 과거 보완 메모의 계단/불연속 지적을 새 실증 문제로 재사용하지 않았다.

이전 검토 기록은 당시 소스에 대한 자료다. 현재 상태는 이 보고서의 확인 시각·소스 해시·파일 목록으로 구분한다. 큐가 추가 샤드를 생성하므로 재실행 시 재고 총수는 달라질 수 있다.
