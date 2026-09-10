# 시오나 해석 후속 검토

현재 로컬 소스·기존 원장의 재검산과 조건부 코드 검토를 기록했다. 전체 저장소 전수조사나 GPU 재실험으로 읽지 않는다.

**적용 상태:** 아래 문장은 수정 제안이다. 기존 실험 원장·하네스·설치 솔버를 변경하지 않았다.

[검토 노트북](INTERPRETATION_FOLLOWUP_0909.ipynb) · [재계산 원장](../outputs/interpretation_followup_0909.json) · [생성기](../benchmark/review_interpretation_followup_0909.py)

```bash
cd /workspace/sionna
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_interpretation_followup_0909.py
```

**앞선 피드백의 보정:** 경로 상한과 해시 배열의 관계는 기존 해시 실험 문서에도 명시돼 있었다. 이번에는 설치본의 해당 구현을 확인했다. 저장소가 이 관계를 전혀 인지하지 못했다고 해석하면 부정확하다.

## 1. 최빈값 이탈률과 기준 조건 대비 변화율이 다르다

**검토 구분:** 새로 재계산한 지표 해석 차이

**확인한 문제:** 합성 평판 576 장(삼각형 1152) · 산란 0.7 · 회절 끔 · 깊이 2 · 씨앗 고정의 스레드 대조에서 단일 스레드 최빈 경로 수는 8059, 다중 스레드 중 해당 행의 최빈값은 8058다. 자체 최빈값 이탈률은 2.5%지만 단일 스레드 최빈값과 다른 판은 39/40 (97.5%)다. 어느 수가 물리적으로 옳은지는 별도 문제다.

**유지할 관측:** 조건 내부의 반복 변동과 조건 사이의 최빈 경로 수 변화가 관측됐다.

**수정 제안:** 각 설정의 최빈 경로 수와 그 값에서 벗어난 비율을 함께 보고한다. 단일 스레드 기준과의 차이는 별도 열로 둔다. 물리적 오류율 판정은 미확정이다.

**다음 확인:** 원시 반복별 경로 수·복소 전계와 공통 기준을 보존하고 조건별 최빈값을 함께 표시한다.

**원문 위치:**

- [hash_bucket_stat_0903.py:74](../benchmark/hash_bucket_stat_0903.py#L74)
> mode_n = collections.Counter(ns).most_common(1)[0][0]

- [thread_ladder_0903.json:28](../outputs/thread_ladder_0903.json#L28)
> "mode_paths": 8058,

## 2. 영 진폭이 편차 집계에서 제외된다

**검토 구분:** 새로 확인한 조건부 통계 누락

**확인한 문제:** 실제 stat 함수를 분리 실행한 합성 입력에서 영 진폭을 넣어도 max_dev_db=0.0와 n_dev_over_0p1db=0가 나온다. h>0 조건이 해당 표본을 제외한다. 기존 요약 원장에는 반복별 hs가 없어 과거 실행에 이 경우가 실제 포함됐는지는 미확인이다.

**유지할 관측:** 양의 진폭 표본에 대해 계산된 기존 편차는 남는다.

**수정 제안:** 양의 진폭 표본의 편차와 영 진폭·비유한 값의 개수를 분리 기록한다. 과거 실행의 제외 표본 유무는 원시 기록 확인이 필요하다.

**다음 확인:** 통계 함수에 제외 사유별 개수와 유효 분모를 추가하고 원시 hs를 저장한다.

**원문 위치:**

- [hash_bucket_stat_0903.py:77](../benchmark/hash_bucket_stat_0903.py#L77)
> dev = [abs(20 * np.log10(h / ref)) for h in hs if h > 0 and ref > 0]

## 3. CPU 재현과 스레드 의존성으로 특정 내부 원인을 확정한다

**검토 구분:** 철회·한정 후 남은 원인 단정

**확인한 문제:** CPU에서도 변한다는 사실은 GPU에만 있는 현상이라는 설명을 제한한다. 스레드 수 대조는 병렬 실행과의 관련성을 지지하지만 후보 선택, 해시 접근, 부동소수점 합산 중 어느 연산인지까지 분리하지 못한다. 생성기 서문에는 이 한정이 있지만 JSON 메타데이터에 원인이 순서가 아니라는 옛 문구가 남아 있다.

**유지할 관측:** 검사한 합성 장면에서 스레드 설정에 따라 반복 결과가 달라졌다.

**수정 제안:** CPU 합성 장면에서 스레드 설정에 따른 변화를 관측했다. 원인이 되는 내부 연산의 특정과 드론 장면으로의 적용은 후속 계측 대상이다.

**다음 확인:** 후보 선택·해시 판정·저장 상한·전계 합산 단계의 출력을 따로 기록한다. 서문·메타데이터·요약 제목을 함께 정정한다.

**원문 위치:**

- [hash_bucket_stat_0903.py:137](../benchmark/hash_bucket_stat_0903.py#L137)
> "여기서도 흔들리면 원인이 «순서» 가 아니라는 뜻이다."),

- [thread_ladder_0903.json:5](../outputs/thread_ladder_0903.json#L5)
> "reads_ko": "스레드 1 에서 발생률이 0 이면 원인은 **병렬 축약 순서**다. 1 에서도 흔들리면 순서가 아니다. ⛔판정은 여기 적지 않는다.",

- [DEEP_DROP_0902.md:425](../docs/DEEP_DROP_0902.md#L425)
> ## ⭐⭐기전이 갈렸다 — **병렬 축약 순서**다 (2026-09-03)

## 4. 경로 상한과 해시 배열을 바꾸는 실험의 적용 범위

**검토 구분:** 앞선 피드백 보정과 설치본 확인

**확인한 문제:** 설치본에서도 해시 배열 크기가 max(경로 상한, 최소 배열 크기)로 계산된다. 기존 해시 실험은 이 관계와 최소값을 이미 인지하고 있었다. 앞선 피드백을 새로 발견한 미인지 설계처럼 읽히게 했다면 정정해야 한다. 다만 저장 상한과 배열 크기는 그 대조에서 함께 바뀌며, 최종 반환 수만으로 후보 단계의 포화를 배제할 수 없다.

**유지할 관측:** 설치본과 기존 대조 코드에서 두 설정의 결합을 확인했다.

**수정 제안:** 이 대조는 경로 저장 상한과 해시 배열 크기를 함께 바꾼 결과다. 각 단계의 유실 원인 분리는 추가 계측 대상이다.

**다음 확인:** 먼저 후보 단계별 개수를 계측하고 필요한 경우 두 설정을 독립적으로 바꾸는 대조를 설계한다.

**원문 위치:**

- [hash_bucket_sweep_0903.py:13](../benchmark/hash_bucket_sweep_0903.py#L13)
> 통 수는 `spec_counter_size = max(max_num_paths_per_src, MIN_SPEC_COUNT_SIZE)` 다.

- [hash_bucket_stat_0903.py:112](../benchmark/hash_bucket_stat_0903.py#L112)
> ns, hs = probe(sc, a.reps, samples_per_src=a.samples, max_num_paths_per_src=B)

- [sb_candidate_generator.py:312](/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/sb_candidate_generator.py#L312)
> spec_counter_size = dr.maximum(max_num_paths_per_src,

- [path_solver.py:246](/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/path_solver.py#L246)
> paths_buffer.discard_invalid()

## 5. 반사 깊이 비교의 포함관계를 사건 집합 불변으로 요약한다

**검토 구분:** 새로 재계산한 요약의 범위 초과

**확인한 문제:** 원장의 깊이 대조에서는 얕은 설정의 사건들이 깊은 설정에 포함되지만 추가 사건도 존재한다. 포함관계만으로 깊이가 사건 위치나 탐색에 영향을 주지 않는다고 할 수 없다. 각 설정에서 복소 잔차와 문턱이 함께 달라지는지도 확인해야 한다.

**유지할 관측:** 깊이 대조의 교집합과 설정별 추가 사건 수를 기존 원장에서 재계산했다.

**수정 제안:** 검사한 깊이 대조에서 얕은 설정의 사건 집합이 깊은 설정에 포함됐으며 추가 사건이 관측됐다. 경로별 변화와 문턱 변화의 기여는 미분리다.

**다음 확인:** 공통 사건과 각 설정의 추가 사건을 나누고 해당 자세의 경로 목록과 복소 잔차를 비교한다.

**원문 위치:**

- [RESUME_0908.md:112](../work/sweep_0904/RESUME_0908.md#L112)
> · ⭐**되돌림 깊이는 걸리는 자세를 안 옮긴다** (0914 C 묶음, 09-08 밤).

- [read_0914_0908.json:56](../outputs/read_0914_0908.json#L56)
> "cross_cell_overlap": {

## 6. 교집합 기댓값은 선언한 귀무모형 아래의 값이다

**검토 구분:** 새로 확인한 귀무모형 설명 누락

**확인한 문제:** n_a*n_b/N은 각 위치의 선택 확률이 균일한 독립 집합 모형의 기대 교집합이다. 가까운 값 하나만으로 무상관을 입증할 수 없다. 회전 위상, 군집, 반복 구조를 보존할지에 따라 적절한 대조 분포가 달라진다. 회전수 일치는 비교 가능성의 일부 조건이며 초기 위상과 로터 배치까지 확인해야 한다.

**유지할 관측:** 동일한 인덱스로 정렬된 두 사건 집합의 교집합은 기술 통계로 쓸 수 있다.

**수정 제안:** 균일·독립 위치 선택 모형의 기대 교집합을 참고값으로 함께 제시했다. 회전 위상과 군집을 반영한 대조 및 유의성 판정은 후속 분석 대상이다.

**다음 확인:** 검정하려는 가설을 먼저 정하고 위상 정렬, 순환 이동 또는 블록 대조 중 보존할 구조를 명시한다.

**원문 위치:**

- [read_0914_0908.py:184](../benchmark/read_0914_0908.py#L184)
> #:    ⭐우연히 겹칠 기댓값 = n_a·n_b / N — 관측이 그 언저리면 «상관 없다» 는 뜻이다.

- [read_0914_0908.py:214](../benchmark/read_0914_0908.py#L214)
> "comparable": ra == rb,

## 7. 기본 장면의 환경 산란계수 변경이 드론 재질까지 선택한다

**검토 구분:** 기존 지적의 잔존 재확인

**확인한 문제:** 현재 조건문은 장면 이름이 sionna:로 시작하면 sc.objects의 모든 항목을 선택한다. 드론을 추가한 뒤 실행되므로 드론 부품도 대상이다. 재질 객체 공유 여부와 예외 무시까지 고려하면 실제 변경 범위는 재질별 기록이 필요하다. 기존 자체 장면의 실험 전체가 이 분기에 해당하는 것은 아니다.

**유지할 관측:** 특정 옵션 조합에서 환경만 바꾸는 대조라는 설명과 선택 코드가 어긋난다.

**수정 제안:** 기본 장면에서 환경 산란계수를 지정하는 현재 분기는 드론 부품도 선택한다. 환경만 변경한 대조로 해석하려면 물체·재질별 적용 범위를 확인해야 한다.

**다음 확인:** 드론 추가 전 환경 객체 집합을 보존하고 재질 공유를 점검한 뒤 변경 전후 값을 기록한다.

**원문 위치:**

- [elevation_sweep_md.py:862](../benchmark/elevation_sweep_md.py#L862)
> if _envn.startswith("sionna:") or str(_nm).startswith("env_"):

## 8. 정렬 옵션과 중복 제거를 함께 쓰는 조건부 인덱스 오류

**검토 구분:** 기존 지적의 잔존 재확인

**확인한 문제:** 현재 코드는 _t를 정렬한 뒤 정렬 전 열에서 구한 _first를 적용한다. 최소 배열 재현에서 기대 중복 제거 합 6에 대해 7가 나왔다. 전체 합 9는 유지되므로 전체 합 검사로 놓칠 수 있다. 이 확인은 최소 연산 재현이며 GPU 실행 결과가 아니다.

**유지할 관측:** 정렬 옵션이 활성화되는 경우의 중복 제거 합을 별도로 재검토해야 한다.

**수정 제안:** 정렬된 전계 항과 중복 판정 인덱스의 순서를 맞춰야 한다. 해당 옵션을 사용한 결과의 영향 범위는 실행 설정별로 추적한다.

**다음 확인:** 정렬 전 배열로 중복 제거 합을 계산하거나 중복 판정 열에도 같은 순열을 적용한다.

**원문 위치:**

- [elevation_sweep_md.py:892](../benchmark/elevation_sweep_md.py#L892)
> _t = _t[_ord]

- [elevation_sweep_md.py:910](../benchmark/elevation_sweep_md.py#L910)
> E_dedup[j] = complex(np.sum(_t[np.sort(_first)]))

## 9. 상한 근접과 실패를 물리적 경로 결과와 구분해야 한다

**검토 구분:** 기존 지적의 잔존 재확인

**확인한 문제:** n_trunc는 최종 반환 수가 경로 상한에 근접한 자세의 수다. 실제 버린 후보 수와 다르다. unpack의 ValueError를 빈 aa로 바꾸면 초기 영 배열이 남아 정상적인 영 전계와 구분하기 어렵다. 모든 예외가 같은 의미인지도 확인해야 한다.

**유지할 관측:** 상한 근접 경고는 해당 출력의 해석을 보류하는 보수적인 신호로 남긴다.

**수정 제안:** 최종 반환 수의 상한 근접 여부를 기록했다. 후보 단계의 유실 개수는 별도 계측 대상이며 처리 실패와 정상 영 전계는 상태값으로 구분해야 한다.

**다음 확인:** 실패·미완료·정상 영 전계를 구분하는 상태를 저장하고 유효 표본 마스크로 대조 쌍을 맞춘다.

**원문 위치:**

- [elevation_sweep_md.py:927](../benchmark/elevation_sweep_md.py#L927)
> _ntr = int(np.count_nonzero(np.asarray(nret) >= 0.99 * RP.MAX_PATHS))

- [elevation_sweep_md.py:880](../benchmark/elevation_sweep_md.py#L880)
> aa = np.zeros(0)

## 10. 모든 물리 옵션과 물리 성분의 독립 분해는 다르다

**검토 구분:** 설치본에서 적용 범위 확인

**확인한 문제:** 설치된 후보 생성기는 회절 횟수와 확산 반사·회절의 혼합 경로를 제한한다. 전계 계산에서는 샘플 수와 샘플링 확률이 가중치에 들어간다. 옵션 대조 차이를 해당 물리의 독립 기여도, 반환 경로 수 일치를 동등 정밀도라고 해석하려면 추가 조건이 필요하다.

**유지할 관측:** 지원되는 상호작용 조합 안에서 옵션별 출력을 비교할 수 있다.

**수정 제안:** 설치 구현이 지원하는 상호작용 조합과 지정 깊이에서 옵션별 출력을 비교했다. 후보 집합과 계산 가중치 변화의 기여는 후속 분석 대상이다.

**다음 확인:** 경로 종류별 후보·가중치와 공통 경로를 대조한 뒤 차분의 의미를 정한다.

**원문 위치:**

- [sb_candidate_generator.py:396](/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/sb_candidate_generator.py#L396)
> # Only first order diffraction is supported.

- [sb_candidate_generator.py:407](/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/sb_candidate_generator.py#L407)
> loc_en_inter[diffuse] &= ~mi.UInt(InteractionType.DIFFRACTION)

- [field_calculator.py:448](/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/field_calculator.py#L448)
> solid_angle[active] *= dr.rcp(probs)

## 깊이 비교 재계산

| 대조 | A 사건 | B 사건 | 공통 | A에만 | B에만 |
|---|---:|---:|---:|---:|---:|
| 기준/기본 (matrice4e · 4e9 · 깊이 2) ∩ C 깊이/깊이 1 | 82 | 51 | 51 | 31 | 0 |
| 기준/기본 (matrice4e · 4e9 · 깊이 2) ∩ C 깊이/깊이 3 | 82 | 91 | 82 | 0 | 9 |

**계산 범위:** Stored ledger arithmetic, extracted pure function, minimal array operations, and static source review. GPU and field measurements excluded.

설치본 버전 표기와 파일 해시는 검산 원장의 checks 및 _meta.source_sha256에 기록했다. 이는 현재 읽은 파일을 식별하며 과거 모든 실험이 같은 파일로 실행됐다는 증거는 아니다.
