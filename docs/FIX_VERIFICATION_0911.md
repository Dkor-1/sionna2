# 수정 완료 주장 재검증 — 2026-09-11

기준 커밋 `57edf61b11d0524dc5d8290f1a745cc73296b91c` · 확인 2026-09-11T04:36:28.271054+00:00.

전달받은 여섯 항목의 완료 여부를 실제 실행 경로에서 확인했다. 운영 코드와 기존 원장은 변경하지 않았다. 반례는 임시 자료 또는 메모리 안의 변형으로 실행했으며 GPU 계산은 수행하지 않았다.

[주피터 보고서](FIX_VERIFICATION_0911.ipynb) · [재계산 원장](../outputs/fix_verification_0911.json) · [생성기](../benchmark/review_fix_verification_0911.py)

```bash
cd /workspace/sionna
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_fix_verification_0911.py
```

## 전달된 완료표의 재검증

| 항목 | 현재 판정 | 근거 |
|---|---|---|
| 1 | 확인 | 실제 낙차 main 완료, 표시 True; 중앙값 1.5 |
| 2 | 미완료 — 수정 대상 파일 불일치 | read_0918B_0909는 수정됐으나 elevation_sweep_md.analyse의 저장값 합산은 유지 |
| 3 | 부분 수정 | 협곡 내부 메타데이터·complex128 유한값·기준선 거절은 확인; 대조 쌍 시간축과 낙차 판독기 검사는 남음 |
| 4 | 확인 | 부분 계측의 dip_equals_short=None |
| 5 | 실행 확인 · 보고 내용과 검증 강도는 보완 필요 | mode=regression, 이중 배율 없음=True |
| 6 | 핵심 문구 정정 확인 | make_jobs_0924에 남은 수와 목록의 구분 반영; 반복의 정보 부재와 추가 눈금의 판별력 표현은 보완 필요 |

협곡 10개 조건과 낙차 7개 조건의 발간 수를 원본 샤드 54개에서 재계산했다. 원본의 인덱스·전계 유한값·대조 시간축 검사는 통과했다. 합성 반례의 실패를 이 발간 자료의 손상으로 소급하지 않는다.

## 남은 문제와 추가 발견

### 1. 주 원장 병합기를 다른 판독기로 잘못 대응해 미수정 상태를 완료로 보고했다

**분류:** 남은 기존 문제

**근거와 범위:** 현 elevation_sweep_md.analyse의 진단 블록에 실제 저장 샤드를 넣으면 256표본에서 경고 0개를 합산하고, 저장 상한 2000000으로 재계산하면 256개다. read_0918B_0909.load/measure의 수정은 이 함수에 전달되지 않는다. 현재 주 원장에 해당 재고가 포함됐다는 주장은 하지 않는다. 반환 수의 상한 근접 경고를 후보 잘림의 직접 증거와 구분한다.

**수정 제안:** elevation_sweep_md.analyse의 해당 블록을 대상으로 수정하고, 그 실제 실행 경로에 저장값 영·현재 경고 양수인 샤드를 넣어 확인한다.

원장: `outputs/fix_verification_0911.json` → `findings[0]` 및 `checks`.

- [elevation_sweep_md.py:1115](../benchmark/elevation_sweep_md.py#L1115)
```python
n_tr += int(_nt[0]); n_seen += int(ii.size)
```

- [read_0918B_0909.py:45](../benchmark/read_0918B_0909.py#L45)
```python
_rec = int(np.count_nonzero(_nr >= 0.99 * _cap))
```

### 2. 장면·자유공간 사이의 시간축과 낙차 판독기 검증은 아직 빠져 있다

**분류:** 부분 수정의 잔여 범위

**근거와 범위:** 각 기록 안에서는 정상인 자유공간 19700 Hz와 장면 10000 Hz를 실제 협곡 main이 1개 조건으로 발간했다. 서로 다른 시각의 값을 같은 인덱스로 빼는 셈이다. 낙차 main은 비유한 전계 입력에서도 1개 행을 내고, 낙차 0개·일치 True를 기록했다. 메타데이터 불일치만 넣은 낙차 입력도 통과했다. 메타데이터 없는 연속 반쪽 입력을 온전하다고 처리하는 협곡 분기도 남아 있다. 이 결과들은 합성 반례이며 현재 발간 자료의 손상으로 소급하지 않는다.

**수정 제안:** 한 기록 내부뿐 아니라 비교 쌍 사이의 N·PRF·인덱스와 실행 조건을 확인한다. 낙차와 동체 판독 경로에도 같은 입력 검증을 적용하고, 미기재 메타데이터는 근거 없이 정상으로 간주하지 않는다.

원장: `outputs/fix_verification_0911.json` → `findings[1]` 및 `checks`.

- [read_canyonnull_0910.py:244](../benchmark/read_canyonnull_0910.py#L244)
```python
if sc["E"].size != fr["E"].size:
```

- [read_dropladder_0910.py:78](../benchmark/read_dropladder_0910.py#L78)
```python
n_expected = int(_m[3])          # 이 칸이 원래 몇 자세짜리인가
```

- [read_canyonnull_0910.py:155](../benchmark/read_canyonnull_0910.py#L155)
```python
and (n_expected is None or idx.size == n_expected)
```

### 3. 새 비유한값 검사가 complex64 전계에서는 NaN을 놓친다

**분류:** 추가 발견 · 자료형 경계 반례

**근거와 범위:** complex64 전계에 실제 비유한 표본 1개를 넣었지만 검사 결과는 n_nonfinite=0, idx_ok=True였다. Ecat.view(float)는 값을 변환하는 대신 메모리의 비트를 float64로 재해석한다. 현재 발간 샤드가 이 자료형으로 오염됐다는 발견은 아니다.

**수정 제안:** 복소 배열 자체에 np.isfinite를 적용해 표본 단위로 센다. 지원하지 않는 자료형이면 명시적으로 거절한다. 허용된 정밀도마다 같은 비유한값 검사를 검증한다.

원장: `outputs/fix_verification_0911.json` → `findings[2]` 및 `checks`.

- [read_canyonnull_0910.py:153](../benchmark/read_canyonnull_0910.py#L153)
```python
n_bad = int(np.count_nonzero(~np.isfinite(Ecat.view(float))))
```

### 4. 네 결함이 고쳐졌다는 반례 검증 중 하나는 생산 코드를 실행하지 않는다

**분류:** 추가 발견 · 검증의 거짓 통과 재현

**근거와 범위:** unknown_dup_counted_as_short 판정은 낙차 main을 부르지 않고 검토 빌더 안에서 have & (D<2)를 직접 다시 계산한다. 메모리에서 생산 main의 short를 옛 식으로 되돌리면 실제 오집계는 0 → 4096개가 되는데, 같은 변경 소스를 읽힌 검토 반례는 여전히 “네 결함이 모두 고쳐졌다(합성 입력 기준)”라고 썼다. 실제 생산 파일을 되돌린 것은 아니며 회귀 검사의 오류 탐지 능력을 별도로 시험한 결과다.

**수정 제안:** 실제 main 또는 main이 호출하는 순수 집계 함수를 반례로 실행한다. 입력만 교체하고, 기대 계산을 검증 대상 대신 실행하지 않는다. 검사마다 대상 함수와 통과 조건을 기록한다.

원장: `outputs/fix_verification_0911.json` → `findings[3]` 및 `checks`.

- [review_latest_readers_0910.py:251](../benchmark/review_latest_readers_0910.py#L251)
```python
_have=D>=0; short_fixed=int((_have&(D<2)).sum())
```

- [review_latest_readers_0910.py:279](../benchmark/review_latest_readers_0910.py#L279)
```python
unknown_dup_counted_as_short=bool(result['mixed_dup_counted_short_fixed']==unknown
```

### 5. regression으로 실행되지만 보고서는 여전히 미수정 결함이라고 서술한다

**분류:** 추가 발견 · 현재 발간 검토 문서의 불일치

**근거와 범위:** 빌더는 정상 완료했고 mode=regression, 대역은 891.040067와 891.040067 Hz로 같다. 그러나 새로 생성한 제목은 “별도 분석기에서 고친 프로펠러 대역이 발간 아틀라스에는 반영되지 않았다”였다. n_trunc를 버린다는 과거 설명도 현재 문제로 재출력한다. 계산의 회귀 모드가 판정·제목·수정 순서에는 전달되지 않은 상태다. 철회한 보완 문구도 재생성된다.

**수정 제안:** 검토 항목에 발견 당시 상태와 현재 재검증 상태를 분리해 둔다. 본문·제목·권장 작업을 현재 상태에서 생성하고, 역사적 수치와 당시 소스는 별도 기록으로 보존한다.

원장: `outputs/fix_verification_0911.json` → `findings[4]` 및 `checks`.

- [review_latest_readers_0910.py:209](../benchmark/review_latest_readers_0910.py#L209)
```python
mode=('regression' if _ps_applied else 'pre_fix_audit'),
```

- [review_latest_readers_0910.py:305](../benchmark/review_latest_readers_0910.py#L305)
```python
add('별도 분석기에서 고친 프로펠러 대역이 발간 아틀라스에는 반영되지 않았다','현재 발간값의 수치 영향 확인',
```

- [review_latest_readers_0910.py:354](../benchmark/review_latest_readers_0910.py#L354)
```python
'새 load는 n_trunc를 읽지 않고 trunc=[]를 반환한다. 이어 호출한 measure의 at_path_cap는 npaths의 중앙값으로 계산되므로 드문 자세의 상한 근접을 감지하는 대체 장치도 아니다.',
```

### 6. 미계측을 표시하는 분기에도 기록이 사라지는 경로가 남아 있다

**분류:** 추가 발견 · 미수집 상태 보고 누락

**근거와 범위:** 전 자세의 n_dup가 미계측인 온전한 입력은 낙차 결과 0행·skipped 0건으로 끝났다. 오류 없이 종료된 것은 맞지만, 요청한 조건이 없어진 이유가 원장에 남지 않는다. 또 measure에 유효한 상한 재계산 1건을 주어도 npaths가 미기록이면 진단 요약 필드 존재 여부는 False다. 원시 trunc 기록은 보존되므로 완전 유실이라고 하지는 않는다.

**수정 제안:** 전부 미계측인 조건도 상태와 사유를 남긴다. 상한 진단 집계는 npaths의 유무와 독립적으로 수행하고, 요약 불능과 영 경고를 분리한다.

원장: `outputs/fix_verification_0911.json` → `findings[5]` 및 `checks`.

- [read_dropladder_0910.py:116](../benchmark/read_dropladder_0910.py#L116)
```python
if (D < 0).all():
```

- [read_0918B_0909.py:89](../benchmark/read_0918B_0909.py#L89)
```python
if (npa >= 0).any():
```

## 문면 보완

0924의 핵심 문장은 잔존 수와 사건 목록을 구분하도록 바뀌었다. 다만 되풀이에서 “정보가 안 나온다”는 설명은 “확률적 독립 표본을 추가하는 대조가 아니며 실행 재현성을 확인한다”로 한정하는 편이 정확하다. 새 배율 눈금만 추가한다고 두 원인을 분리할 수 있는 것도 아니므로, 분리하려는 효과와 비교 조건을 별도로 정해야 한다.

실행 성공, 지정 반례 통과, 실제 발간값 유지, 결함의 전체 해결은 각각 다른 확인이다. 이번 검증은 추가 반례를 통해 적용 범위를 확인했으며, 물리적 정확성이나 실측 일치를 판정한 보고서가 아니다.
