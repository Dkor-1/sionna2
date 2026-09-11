# 후속 수정 재확인과 남은 보완점

기준 커밋 `b7717d1deb61d523e2519a1af91d33d6de319fa6` · 2026-09-11T05:01:30.084713+00:00

[주피터 보고서](POSTFIX_REVIEW_0911.ipynb) · [재계산 원장](../outputs/postfix_review_0911.json) · [생성기](../benchmark/review_postfix_0911.py)

## 확인된 수정

- 실제 주 원장 병합 진단 블록: 옛 샤드 묶음 저장 0 → 현재 규칙 256로 재계산됐다.
- complex64 NaN 검출 1, idx_ok=False; 서로 다른 PRF의 장면/빈하늘 쌍 채택 0칸이다.
- 전부 n_dup 미계측 입력의 skipped는 1건이다. 부분 미계측의 일치 판정은 None다.
- 옛 short 식을 복원한 main의 오류를 탐지했다. main 예외 때 n_unknown=1으로 남긴다.
- 협곡 10칸·낙차 7칸을 원본 샤드 54개에서 재계산했고 발간값과 일치했다.

위 수의 조건·파일 목록은 원장의 checks에 있다. 원본 샤드의 인덱스·유한값·비교 시간축을 대조했다. 이 확인은 지정한 경로와 자료의 범위이며, GPU 워커의 과거 생존 상태나 물리적 정확성까지 확인한 뜻은 아니다.

## 추가 수정 제안

### 1. 회귀 검사에서 결과 행 누락과 일부 오집계를 통과시킨다

**범위:** 새 합성 반례 · 검사 판정

실제 main을 메모리에서 옛 식으로 되돌리면 n_short=4096로 잡힌다. 하지만 일부 미계측만 잘못 세는 변형은 n_short=1인데 결함 판정이 False다. main이 빈 rows를 쓰고 정상 종료하는 변형도 n_short=None인데 동일하게 통과한다. 이는 실제 운영 자료의 오집계 발견이 아니라 검사 자체의 탐지 범위 반례다.

**권장 수정:** 정상 종료와 목표 행 존재·유일성·필드 유효성을 따로 확인한다. 이 합성 입력의 기대값과 결과값을 직접 비교하고, 행 누락은 미확인으로 남긴다. 검사에는 생산식과 별도로 정한 기대 결과를 둔다.

원장: `outputs/postfix_review_0911.json` → `findings[0]`.

- [review_latest_readers_0910.py:266](../benchmark/review_latest_readers_0910.py#L266)
```python
short_fixed = _row['n_short'] if _row else None
```

- [review_latest_readers_0910.py:307](../benchmark/review_latest_readers_0910.py#L307)
```python
bool(result['mixed_dup_counted_short_fixed']==unknown
```

### 2. 시간축·표본수 검사가 낙차 판독과 Hampel 비교에는 덜 연결됐다

**범위:** 남은 입력 검증 · 합성 입력

서로 다른 선언 표본수·PRF를 섞은 낙차 입력이 1행으로 발행됐다. 파일명은 n=8192인데 메타데이터 없이 앞쪽 4096개 표본만 넣은 입력도 1행으로 발행됐다. Hampel 표는 기준 PRF=19700 Hz, 비교 PRF=10000 Hz인데 candidate 행을 냈다. 장면과 빈하늘 쌍의 PRF 불일치 거절은 이번 수정으로 통과했다. 같은 인덱스가 같은 시각을 뜻한다는 해석은 별도 조건이다.

**권장 수정:** 샤드별 선언 N·PRF와 파일명/요청 N을 대조하고, 메타데이터가 없으면 검증 불가 사유를 남긴다. Hampel 쌍도 시간축을 확인한다. 세대 선택은 인덱스와 선언 길이의 완전성을 확인한 뒤 수행한다.

원장: `outputs/postfix_review_0911.json` → `findings[1]`.

- [read_dropladder_0910.py:78](../benchmark/read_dropladder_0910.py#L78)
```python
n_expected = int(_m[3])          # 이 칸이 원래 몇 자세짜리인가
```

- [read_canyonnull_0910.py:205](../benchmark/read_canyonnull_0910.py#L205)
```python
if c is None or n < 2 or c["E"].size != mb.size or not c["idx_ok"]:
```

### 3. 주 원장 상한 진단의 예외 분기와 설명이 어긋난다

**범위:** 남은 예외 처리·해석

실제 옛 샤드 묶음은 저장 0에서 현재 규칙 256으로 수정됐다. 그러나 nret이 빠진 합성 입력은 저장값 0을 현재 n_trunc=0으로 사용하고 n_seen=4으로 센다. 상한이 없는 동일 입력은 실행 환경 상한 [2000000, 6000000]에서 경고 수 [4, 0]로 달라진다. 상한 가정은 max_paths_cap_assumed로 표시되므로 숨겼다고 하지는 않는다. 다만 모든 n_trunc가 저장 상한 재계산이라는 설명과는 다르다. 저장값과 재계산값이 다르다는 사실은 판정 규칙 차이로도 생기므로, 한 칸 내부의 세대 혼합을 증명하지 않는다.

**권장 수정:** 확정 재계산·옛 저장값·상한 가정 계산을 분리하고 각 범위와 미확인 표본수를 기록한다. nret/저장 상한이 빠진 경우에는 현재 규칙의 확정값을 미확인으로 둔다. 차이는 우선 저장 당시 규칙과 현재 규칙의 차이로 설명한다.

원장: `outputs/postfix_review_0911.json` → `findings[2]`.

- [elevation_sweep_md.py:1129](../benchmark/elevation_sweep_md.py#L1129)
```python
n_tr += int(_nt[0])
```

- [elevation_sweep_md.py:1147](../benchmark/elevation_sweep_md.py#L1147)
```python
_cap_default = int(os.environ.get("SIONNA2_MAX_PATHS", 2_000_000))
```

- [elevation_sweep_md.py:1196](../benchmark/elevation_sweep_md.py#L1196)
```python
"있다). 둘이 다르면 그 칸은 세대가 섞였다는 뜻이다. "
```

### 4. 유한한 전계라도 중앙값이 영이면 낙차 판정이 정의되지 않는다

**범위:** 새 합성 반례 · 분모 검사

전계가 모두 영인 합성 입력 n=8192에서 n_dip=0, dip_equals_short=True가 발행됐다. 이 입력의 전계는 유한하지만 중앙값으로 나눈 비율은 정의되지 않는다. 이 결과를 정상 판정으로 읽으면 무응답과 낙차 부재가 섞인다. 실제 발간 칸에서 이 상황을 발견했다는 뜻은 아니다.

**권장 수정:** 비율 계산 전 중앙값의 양수·유한 여부를 확인하고, 실패하면 원장에 사유와 미정 판정을 남긴다. 임의의 작은 상수를 더하려면 그에 따른 낙차 정의 변경을 별도로 정해야 한다.

원장: `outputs/postfix_review_0911.json` → `findings[3]`.

- [read_dropladder_0910.py:142](../benchmark/read_dropladder_0910.py#L142)
```python
a = np.abs(E); med = float(np.median(a))
```

- [read_dropladder_0910.py:150](../benchmark/read_dropladder_0910.py#L150)
```python
dip = (a / med) < DIP               # 덱 2 쪽 규칙
```

### 5. 고쳐짐 제목 아래의 수정 제안과 마지막 작업 순서는 과거 상태다

**범위:** 현재 생성 보고서 문면

검토 빌더는 mode=regression로 끝났고 기준 대역 891.0400671279016와 891.0400671279016가 같다. 제목은 [고쳐짐] 별도 분석기에서 고친 프로펠러 대역이 발간 아틀라스에는 반영되지 않았다로 바뀌었다. 하지만 노트북의 옛 replacement 문장 재출력=True, 옛 아틀라스 정정 작업 재출력=True다. 마크다운 마지막 수정 순서도 아틀라스를 먼저 고치고 다시 굽으라고 지시한다.

**권장 수정:** fixed 상태에서 replacement와 최종 작업 목록도 함께 분기한다. 완료 항목은 정정 기록과 유지할 검사로 안내하고, 과거 제안에는 과거 기록임을 명시한다. 아틀라스는 완료 기록으로 안내하고 문면을 정정한다.

원장: `outputs/postfix_review_0911.json` → `findings[4]`.

- [review_latest_readers_0910.py:347](../benchmark/review_latest_readers_0910.py#L347)
```python
replacement=replacement,followup=followup,
```

- [review_latest_readers_0910.py:487](../benchmark/review_latest_readers_0910.py#L487)
```python
'발간 숫자에 영향이 확인된 아틀라스의 대역 정의를 먼저 고치고 관련 산출물을 다시 굽는다. '
```

## 실행 범위

운영 코드·기존 원장·발표 파일을 바꾸지 않았다. 실제 판독 main은 임시 샤드를 읽고 임시 원장을 쓰게 실행했다. 주 병합기는 GPU 의존부를 실행하지 않고 해당 함수의 진단 블록을 AST로 추출해 실제 저장 샤드에 적용했다. 회귀 반례는 importlib.reload 직후 메모리에서만 main을 바꾸었으며 각 시험 뒤 원래 모듈로 복구했다. 과거 감사의 시험 도우미를 재사용하되 옛 방식의 mutation 결과는 이번 근거에서 제외했다.

상한 진단 설명과 보고서 수정 제안은 현재 코드의 문제다. 나머지 추가 오동작은 합성 입력으로 재현한 것이며, 이번에 대조한 발간 칸이 손상됐다고 소급하지 않는다.

```bash
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_postfix_0911.py
```
