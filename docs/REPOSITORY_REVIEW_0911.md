# 시오나 저장소 전체 재고와 주요 실행 경로 점검

기준 `1c82aa5304e82037c0f54f1493a1b6fec6c0caac` · 2026-09-11T16:38:45.660848+00:00

[주피터 보고서](REPOSITORY_REVIEW_0911.ipynb) · [전수 목록·실행 원장](../outputs/repository_review_0911.json) · [재현 생성기](../benchmark/review_repository_0911.py)

## 조사 범위

추적 파일과 작업 트리 파일 19571개를 목록화하고, 파이썬 800개를 구문 검사했다. 열거에 쓴 방법은 os.walk (no ignore rules; .git and __pycache__ excluded)다. outputs 바로 아래 JSON 735개를 구문 확인했다. 저장 샤드 7470개를 실제로 읽어 2301조건의 idx·선언 길이·시간축·전계 유한값·배열 길이를 집계했다.

파일 목록·구문 검사는 모든 코드의 의미를 정독하거나 모든 실험을 재실행한 것과 다르다. 의미와 반례를 깊게 확인한 범위는 주 병합·샤드 저장·재개 조건·협곡/낙차/동체 판독·아틀라스 완전성·검토 보고서 빌더·신호처리 교정이다. refs·prior_work의 논문 근거 재독, GPU 커널 재실행, 모든 보고서의 과학적 결론 검증은 이번 범위 밖이다. 저장소 무시 규칙에 걸리는 미추적 파일은 일반 목록 밖이며 샤드 폴더는 별도로 직접 열거했다.

샤드 읽기 오류 0개·비유한 전계 조건 0개·배열 길이 오류 조건 0개다. 인덱스가 선언 길이를 덮지 않는 조건은 7개로, 진행 중 자료와 구별해 다뤄야 한다. 완전성 부족을 곧바로 솔버 결함으로 부르지 않는다.

## 이전 지적의 현재 상태

- 보류 진단의 분류 합계와 초기화 전 상한 사용은 지정 반례에서 수정됐다. 함수 범위를 유지한 실행으로 확인했다.
- 동체 입력의 NaN·중복·시간축 불일치·절반 자료는 생산 main에서 거절됐다. 회귀 검사의 일부 오집계·행 누락도 정상적으로 구분됐다.
- 보고서 수정은 노트북 형식 관문 실패로 이어졌고, 자카드 근사 명칭은 동체 빌더에 남았다. 아래에 구체적으로 적었다.
- 기존 발간 대조는 원본 80개·협곡 10칸·낙차 7칸·동체 8칸이다. 이 범위의 관측 사건 수는 일치했다.

## 재현한 보완점

### 1. 수집 마스크로 결측을 가르고 저장된 영 전계를 평균에 포함한다

**범위:** 2026-09-11 정정(R31) 뒤 현재 상태

인덱스가 완결된 14칸에 영 전계가 있고, 그중 일부 표본만 영인 칸은 5개다. 이 5칸 모두에서 발간 level_db가 영 표본을 포함한 평균과 같고 n_missing이 실제 빠진 인덱스 수와 같다(일치 5칸). 예: sionna_p4000000000_onlyrefr_mini5pro_r240_n8192, el -30°, 저장 8192표본 중 영 전계 7497개, 실제 빠진 인덱스 0개, n_missing=0, 발간 레벨 -214.72 dB다. 옛 규칙(영 표본 제외)과의 차이는 이 칸에서 21.43 dB였다. 저장된 영 값은 물리적으로 신호가 없다는 증명도 아니며 표본을 저장하지 않았다는 증명도 아니므로, 두 수를 따로 싣는다. 같은 칸들의 아틀라스 incomplete 값은 [False]이며, 이 값은 아틀라스를 다시 구운 뒤에 의미가 있다.

**수정 방향:** 남은 일은 아틀라스 색인을 정정된 원장으로 다시 굽고 incomplete와 zero_field가 갈라져 실리는지 확인하는 것이다. 원장 쪽 규칙은 idx 기반 수집 마스크로 고정됐다.

⟨outputs/repository_review_0911.json : findings[0]⟩

- [elevation_sweep_md.py:1383](../benchmark/elevation_sweep_md.py#L1383)
```python
miss = int((~seen).sum())
```

- [elevation_sweep_md.py:1502](../benchmark/elevation_sweep_md.py#L1502)
```python
(np.abs(E[seen]).mean() if seen.any() else 0.0) + 1e-300)), 2),
```

- [build_md_atlas.py:904](../benchmark/build_md_atlas.py#L904)
```python
incomplete = (not empty) and (0 < n_miss < n_pose)
```

### 2. 한 칸에 두 세대가 있으면 한 세대를 골라 파일 순서에서 결과를 떼어 놓는다

**범위:** 2026-09-11 정정(R32) 뒤 현재 상태

중복 인덱스가 있는 15칸 중 4칸은 겹친 전계가 달랐고, 나머지 11칸은 겹친 값이 같았다. 병합 고리만 놓고 보면 이 4칸은 파일 순서를 뒤집을 때 [3582, 3057, 3981, 3621]개의 자세가 바뀐다. 고리 앞에서 세대를 고르는 생산 함수를 정·역 두 순서로 돌린 결과 선택이 같은 칸은 4/4이고, 고른 세대가 덮는 자세는 ['8192/8192', '8192/8192', '8192/8192', '8192/8192']다. 무엇을 버렸는지 원장 행이 적은 칸은 4/4다. 겹친 자세 중 값이 다른 수는 [3582, 3057, 3981, 3621]이고 그중 상대차 5e-6을 넘는 수는 [1, 1, 6, 8], 최대 상대차는 [0.4995, 0.4999, 0.0075, 0.0242]다. 충돌한 조건 중 현재 발간 주 원장에 들어 있는 수는 4칸이다.

**수정 방향:** 남은 일은 겹친 파일을 창고에서 정리할지 그대로 둘지 정하는 것이다. 선택 규칙은 최신 파일 우선이 아니라 자세를 가장 많이 덮는 세대이며, 고른 세대가 부분 자료면 그 칸은 미완으로 남는다.

⟨outputs/repository_review_0911.json : findings[1]⟩

- [elevation_sweep_md.py:1038](../benchmark/elevation_sweep_md.py#L1038)
```python
def one_generation(fs, tag, gap_s=3600.0):
```

- [elevation_sweep_md.py:1284](../benchmark/elevation_sweep_md.py#L1284)
```python
fs, mixed_gen = one_generation(fs, f"{eng}/el{el:+g}")
```

- [elevation_sweep_md.py:1042](../benchmark/elevation_sweep_md.py#L1042)
```python
⛔⛔2026-09-11(5) 정정 — 전에는 병합 고리가 `E[ii] = z["E"]` 로 **덮어쓰기만** 했다.
```

### 3. 재개가 파일 이름 대신 내용으로 완료를 판정한다

**범위:** 2026-09-11 정정 뒤 현재 상태 · 합성 장애 시험

실제 저장 호출에서 E를 쓰는 중 예외를 주입했다. 파일 잔존=True, E 배열 유효=False, 재개 조건 원문은 «shard_done(f) and (not a.overwrite)»이고 그 조건이 이 파일을 건너뛸지는 False다. 조건이 부르는 생산 함수 ['shard_done']를 원본 그대로 실행해 판정했다. 이번 전수 판독 7470개에서 읽기 실패는 0개이므로, 현재 재고가 손상됐다는 주장이 아니라 저장 중단에 대한 내성을 잰 것이다.

**수정 방향:** 남은 일은 저장 자체를 같은 디렉토리의 임시 파일에 쓰고 최종 이름으로 교체하는 것이다. 지금은 재개 쪽만 내용을 확인하므로, 끊긴 파일은 남아 있다가 다시 구워질 때 덮인다.

⟨outputs/repository_review_0911.json : findings[2]⟩

- [elevation_sweep_md.py:965](../benchmark/elevation_sweep_md.py#L965)
```python
np.savez_compressed(f, idx=idx, E=E, npaths=npaths, nret=nret,
```

- [elevation_sweep_md.py:988](../benchmark/elevation_sweep_md.py#L988)
```python
def shard_done(f):
```

- [elevation_sweep_md.py:650](../benchmark/elevation_sweep_md.py#L650)
```python
if shard_done(f) and not a.overwrite:
```

### 4. 검토 빌더가 형식 관문까지 통과해 끝난다

**범위:** 2026-09-11 정정 뒤 현재 상태

직전 라운드 빌더의 main을 임시 출력 경로에서 실행하면 완료=True, 오류 종류=None로 끝난다. JSON 작성=True, 마크다운 작성=True, 노트북 작성=True다. 아틀라스 점검 방식은 regression이고 첫 소견의 처방줄은 «⭐이미 했다 — build_md_atlas.py 가 _ps 를 곱하고 아틀라스·목차·HTML·리포트를 다시 …»로 끝난다. 전에는 내용 수정이 노트북의 부정문 개수 제한을 넘겨 strict 관문이 거절했다. 원장 계산 성공과 보고서 생성 완료는 여전히 따로 센다. 실행 전문은 checks.previous.builder에 보존했다.

**수정 방향:** 남은 일은 산출물 묶음을 검사까지 통과한 뒤 공개하는 순서를 지키는 것이다. 관문을 통과하려면 처방줄을 긍정형의 구체적인 상태 설명으로 쓴다.

⟨outputs/repository_review_0911.json : findings[3]⟩

- [review_latest_readers_0910.py:586](../benchmark/review_latest_readers_0910.py#L586)
```python
build_notebook(str(NB),blocks,strict=True)
```

- [report_style.py:218](../src/report_style.py#L218)
```python
raise ContractError(
```

### 5. 교정 범위 밖 목표 오경보율을 거절하고 범위 안에서만 교정값을 준다

**범위:** 2026-09-11 정정 뒤 현재 상태

wifi 교정 범위 1e-05~0.01에서 네 값을 넣었다. 범위 밖 2개는 거절됐고([1.0000000000000002e-06, 0.1]), 범위 안 2개는 교정값을 돌려줬다. 거절된 값이 옛 동작에서 돌려줬을 수는 [4.509196605305932e-06, 0.008764288638535718]인데, 이는 경계값이지 그 목표의 값이 아니다. 옛 코드는 np.interp가 구간 밖에서 외삽한다고 주석에 적었으나 실제로는 끝점에 붙는다. 세 파형 모두 같다. 범위 밖 설정으로 생성된 발간 결과를 특정한 것은 아니다.

**수정 방향:** 남은 일은 표를 넓혀 더 엄격한 목표까지 교정하는 것이다. 그전까지 범위 밖이 필요하면 strict=False로 부르고 pfa_nominal_detail의 source를 결과에 함께 적는다.

⟨outputs/repository_review_0911.json : findings[4]⟩

- [passive_process.py:342](../src/passive_process.py#L342)
```python
def pfa_nominal_detail(std: str, pfa_target: float) -> dict:
```

- [passive_process.py:404](../src/passive_process.py#L404)
```python
raise PfaOutOfRange(
```

- [passive_process.py:382](../src/passive_process.py#L382)
```python
val = float(10 ** np.interp(np.log10(pfa_target), lx, ly))
```

### 6. 두 판독 빌더가 근사 자카드를 근사라고 이름 붙인다

**범위:** 2026-09-11 정정 뒤 현재 상태

협곡의 approx_jaccard 명칭 반영=True이고, 동체 생산 빌더에 남아 있던 expected_jaccard 명칭 잔존=False다. 두 빌더 모두 기대 교집합을 비율식에 넣은 값을 근사로 이름 붙이므로, 정확한 기대 자카드와 이름이 갈린다. 이전 감사의 수치적 차이 설명은 그대로 유지한다.

**수정 방향:** 남은 일은 옛 키를 읽던 소비자가 있으면 함께 갱신하는 것이다. 두 원장은 새 이름으로 다시 구웠다.

⟨outputs/repository_review_0911.json : findings[5]⟩

- [read_bodyladder_0910.py:115](../benchmark/read_bodyladder_0910.py#L115)
```python
row["approx_jaccard_if_unrelated"] = round(e / max(int(fa.sum()) + nb - e, 1e-9), 5)
```

- [read_canyonnull_0910.py:300](../benchmark/read_canyonnull_0910.py#L300)
```python
approx_jaccard_if_unrelated=round(e / max(na + nb - e, 1e-9), 5))
```

## 추가 관찰과 미확정 범위

microdoppler_proc.periodogram_spec는 min_periods=8 요청을 입력 길이 제한으로 줄인다. N=512·PRF=19700.0·f_flash=126.7에서 실제 seg_periods=1.0934다. 정보에는 실제 주기가 기록되지만 함수 설명의 최소 주기 보장은 성립하지 않는다. 짧은 입력을 거절할지 요청 미충족 상태로 내보낼지 정해야 한다. 외부 호출 경로의 발간 영향을 이번에 특정하지 못했으므로 주요 결함 수에는 넣지 않았다.

구문 검사에서 outputs의 코드 발췌 파일이 들여쓰기로 걸렸다. 실행 엔트리의 오류로 분류하지 않았다. 정적 패턴 후보는 checks.inventory.static_candidate_files에 목록으로 보존했고, 자동 검색 결과만으로 결함 판정을 내리지 않았다.

운영 코드·기존 원장·GPU 큐를 변경하지 않았다. 저장 장애는 임시 파일에만 주입했다. 권장 순서는 수집 마스크 정의와 혼합 세대 선택을 정한 뒤 병합·아틀라스 정정 범위를 계산하고, 저장/재개 및 보고서 생성 경로를 보강하는 것이다.

```bash
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_repository_0911.py
```
