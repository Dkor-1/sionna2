# 현재 수정 상태와 인접 경로 추가 점검

기준 `011b9a771ce7b607f66e2c28ccdbe26a53081606` · 2026-09-11T06:40:31.970848+00:00

[주피터 보고서](EXTENDED_REVIEW_0911.ipynb) · [실행 원장](../outputs/extended_review_0911.json) · [재현 생성기](../benchmark/review_extended_0911.py)

## 확인된 수정

- 기존 회귀 반례: 일부 오집계 탐지=True, 결과 행 누락은 미확인 1건으로 분류했다.
- 낙차 판독기의 기존 메타데이터 누락·불일치·영 중앙값 반례와 Hampel의 서로 다른 PRF 반례를 거절했다.
- 협곡 10칸·낙차 7칸과 동체 8칸을 원본에서 재계산했다. 합친 원본 파일은 80개다.

이전 반례의 수정과 추가 입력의 거절 범위를 따로 판단했다. 운영 코드·GPU 큐·기존 발간물은 변경하지 않았다. 주 병합기는 현재 함수의 진단 블록을 추출해 함수 범위와 칸 반복을 유지하며 실행했다. 물리적 정확성이나 GPU 재현성을 새로 판정한 보고서는 아니다.

## 남은 문제와 추가 발견

### 1. 상한 없는 n_trunc 분기에서 초기화 전 변수 또는 앞 칸의 상한을 쓴다

**범위:** 이번 수정에서 생긴 실행 오류 · 합성 반례

nret과 길이 하나의 n_trunc를 가진 합성 입력이 첫 칸이면 UnboundLocalError가 난다. 앞 칸 상한을 [6000000, 2000000]으로 바꾸자, 동일한 다음 칸의 경고 수가 4와 8로 달라졌다. 다음 칸에는 자체 저장 상한이 있는 샤드도 함께 넣었다. 재고 7412개 파일 중 이 길이 하나 형식은 0개였다. 최근 파일 0개와 읽기 오류 0개는 범위 밖이다. 현재 큐에서 이 예외가 발생했다는 주장은 아니다.

**권장 수정:** 상한 없는 진단은 같은 칸의 보류 목록에 넣고, 그 칸의 상한·가정 정책을 결정한 뒤 처리한다. 첫 칸과 뒤 칸, 앞 칸 상한을 바꾼 순서 시험을 함께 둔다.

⟨outputs/extended_review_0911.json : findings[0]⟩

- [elevation_sweep_md.py:1138](../benchmark/elevation_sweep_md.py#L1138)
```python
n_tr += int(np.count_nonzero(_nr >= 0.99 * _cap_for_old))
```

- [elevation_sweep_md.py:1161](../benchmark/elevation_sweep_md.py#L1161)
```python
_cap_for_old = cap_seen if cap_seen else _cap_default
```

### 2. 보류한 진단은 경고 수에 들어가지만 분류별 표본수에서 빠진다

**범위:** 이번 수정의 집계 누락 · 실제 저장 샤드 재현

실제 S0.3·el −30·n8192 묶음의 현재 병합 블록은 n_trunc=8192, n_seen=8192인데 n_trunc_by={'recomputed': 0, 'from_stored': 0, 'assumed_cap': 0}다. 진단 분류의 표본수 합이 0라 처리된 표본수를 설명하지 못한다. 재고에서 nret만 있고 n_trunc가 없는 파일은 760개다. 현재 발간 주 원장 1433행의 n_trunc_by 필드 보유는 0행이므로, 이 새 필드가 이미 발간됐다고 하지는 않는다.

**권장 수정:** 보류 목록을 처리하는 루프에서도 실제 적용한 정책의 분류를 올린다. 다른 샤드의 상한을 빌린 경우와 실행 환경 기본값을 쓴 경우의 출처를 기록하고, 분류 합계와 진단 대상 표본수를 대조한다.

⟨outputs/extended_review_0911.json : findings[1]⟩

- [elevation_sweep_md.py:1162](../benchmark/elevation_sweep_md.py#L1162)
```python
for _nr, _n in _pend:
```

- [elevation_sweep_md.py:1206](../benchmark/elevation_sweep_md.py#L1206)
```python
prov["n_trunc_by"] = dict(recomputed=int(n_tr_recomputed),
```

### 3. 동체 사다리의 생산 로더에는 입력 검증이 연결되지 않았다

**범위:** 추가 조사 범위 · 합성 입력 거절 실패

read_bodyladder.main에 실제 파일을 넣었다. 중복 장면 인덱스는 고유 4096/행 8192인데 결과 1행을 발행했다. 장면·빈하늘 PRF 불일치도 1행, 선언 길이보다 짧은 입력도 n_poses=4096로 발행됐다. 정상 대조의 기준 사건은 1인데, 별도 자세에 NaN을 넣자 기준 사건 0으로 발행됐다. 현재 발간 동체 칸은 별도 엄격 로더로 재계산해 일치했으므로 합성 반례를 발간 자료 손상으로 소급하지 않는다.

**권장 수정:** 동체 판독기가 실제로 가져오는 read_0918B.load/measure에 인덱스·길이·샤드 메타데이터·유한값·비교 시간축 검사를 연결한다. 각 입력 거절 사유를 원장에 남기고, 기준선 실패 때 전체 결과의 상태를 명시한다.

⟨outputs/extended_review_0911.json : findings[2]⟩

- [read_bodyladder_0910.py:52](../benchmark/read_bodyladder_0910.py#L52)
```python
from read_0918B_0909 import load, stem, measure, DEV, EL     # noqa: E402
```

- [read_0918B_0909.py:49](../benchmark/read_0918B_0909.py#L49)
```python
o = np.argsort(np.concatenate(I))
```

- [read_0918B_0909.py:71](../benchmark/read_0918B_0909.py#L71)
```python
if F.size != O.size:
```

### 4. 기대 자카드는 기대 교집합을 대입한 근삿값이다

**범위:** 추가 발견 · 현재 발간 참고값의 이름과 계산

균일·독립이며 집합 크기를 고정한 가정에서도 E[I]/(a+b−E[I])와 E[I/(a+b−I)]는 다르다. 작은 전수 계산 N=4, a=b=2에서 각각 0.333333와 0.388889다. 현재 동체·협곡 참고값 18행 중 소수점 표시가 달라지는 것은 18행이며, 발간값과 정확한 기대값의 최대 절대 차이는 0.00003441다. 관측 자카드·사건 수는 이 지적의 변경 대상이 아니다. 정확한 기댓값으로 바꾸어도 물리적 널이나 유의성 검정이 생기는 것은 아니다.

**권장 수정:** 현 식을 유지하면 기대 교집합을 대입한 자카드 근사라고 이름과 식을 함께 적는다. 정확한 기대값이 필요하면 고정 크기 집합의 교집합 분포에 대해 비율 자체를 평균한다.

⟨outputs/extended_review_0911.json : findings[3]⟩

- [read_bodyladder_0910.py:113](../benchmark/read_bodyladder_0910.py#L113)
```python
row["expected_jaccard_if_unrelated"] = round(e / max(int(fa.sum()) + nb - e, 1e-9), 5)
```

- [read_canyonnull_0910.py:300](../benchmark/read_canyonnull_0910.py#L300)
```python
expected_jaccard_if_unrelated=round(e / max(na + nb - e, 1e-9), 5))
```

### 5. 마크다운 정정이 노트북 작업 지시까지 전달되지 않았다

**범위:** 남은 이전 지적 · 실제 재생성 결과

검토 빌더는 regression로 정상 완료한다. 마크다운 마지막 순서는 아틀라스가 이미 고쳐졌다고 수정됐다. 하지만 노트북은 옛 replacement 문장 포함=True, 아틀라스 정정 작업 포함=True다. 확인 범위는 이번에 임시 경로로 실제 재생성한 문서와 노트북이다.

**권장 수정:** 노트북의 항목별 replacement와 next_steps도 fixed 상태에서 생성한다. 마크다운과 노트북이 같은 현재 권고 필드를 읽도록 묶는다.

⟨outputs/extended_review_0911.json : findings[4]⟩

- [review_latest_readers_0910.py:534](../benchmark/review_latest_readers_0910.py#L534)
```python
blocks.append(md(f"## {i+1}. {f['title']}",'',f['replacement'],'',
```

- [review_latest_readers_0910.py:537](../benchmark/review_latest_readers_0910.py#L537)
```python
('아틀라스 대역과 관련 산출물을 정정한다','같은 신호에서 발생한 지표 정의의 차이','LATEST_READERS_REVIEW_0910.md'),
```

## 해석 범위와 순서

먼저 새 병합 분기의 변수 범위와 분류 합계를 고친다. 이어 동체 판독기의 실제 진입점까지 입력 검증을 연결한다. 참고 기댓값의 명칭과 보고서 지시는 그다음 문면에서 정리한다. 분류 필드의 발간은 병합 검사를 통과한 산출물로 진행한다.

추가 확인 범위에 있는 진단 요약도 주의가 필요하다. read_0918B.measure는 npaths가 없는 경우 상한 근접 요약 필드를 생략한다. 원시 trunc 기록은 보존하므로 진단 전체 유실로 부르지 않는다. 이 항목은 이전 감사에서 확인한 잔여 범위이며 새 발견 수에 합치지 않았다.

```bash
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_extended_0911.py
```
