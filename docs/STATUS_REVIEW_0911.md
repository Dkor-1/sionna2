# 현재 상태 재점검

기준 `c3959114126609b98a1f1b625d928b9bd7a6b0fd` · 2026-09-11T17:11:34.455617+00:00

[주피터 보고서](STATUS_REVIEW_0911.ipynb) · [실행 원장](../outputs/status_review_0911.json) · [생성기](../benchmark/review_status_0911.py)

## 현재 실행과 확인된 수정

프로세스 조회 시점에 워커 10개가 있었고, 감독자·지킴이 목록과 최근 로그를 원장에 남겼다. 큐의 분수는 투입 포인터이며 완료 수로 읽지 않는다.

실제 저장 샤드 7472개를 재판독했다. 읽기 오류 0개다. 최근 수정되어 제외한 파일은 0개다. 기존 관측 사건은 원본 80개·협곡 10칸·낙차 7칸·동체 8칸에서 발간값과 일치했다.

영 전계가 일부인 5조건의 현재 레벨과 결측 수를 원본으로 다시 계산했다. 원본 파일 시각을 유지한 현재 재고에서는 세대 선택과 발간 선택 기록이 일치한다. 교정 범위 밖 목표는 거절되고, 표 안 목표는 교정값을 반환한다. 각 확인의 상세 조건은 aggregation·generation_current·pfa에 있다.

## 남은 보완점

### 1. 세대 선택이 파일 시각과 무관하다

**범위:** 2026-09-12 정정 뒤 현재 상태 · 실제 충돌 샤드의 임시 복제 대조

현재 원본에서는 4조건 모두 완결 세대를 선택한다. 동일 바이트를 임시 복제하고 파일 시각만 같게 둔 대조에서 선택 결과의 중복은 0행이고 원본 선택과 비교해 바뀐 자세 수는 [0, 0, 0, 0]다. 세대는 파일 시각이 아니라 샤드에 적힌 조각 수(meta[2])로 가른다. 덮는 자세와 중복이 같아 내용으로 못 고르는 경우에는 파일 이름으로 결정적으로 고르고 그 사실을 tie_unresolved로 싣는다. 고른 뒤에는 묶음 안 중복과 값 충돌을 다시 세어 원장에 적는다. 현재 아틀라스가 이 복제 입력으로 발행됐다는 뜻은 아니다.

**수정 제안:** 남은 일은 샤드에 굽기 식별자를 함께 적는 것이다. 지금은 조각 수가 같은 두 굽기를 내용만으로 가르지 못하고 이름으로 고른다.

⟨outputs/status_review_0911.json : findings[0]⟩

- [elevation_sweep_md.py:1130](../benchmark/elevation_sweep_md.py#L1130)
```python
def _nsh(f):
```

- [elevation_sweep_md.py:1193](../benchmark/elevation_sweep_md.py#L1193)
```python
tie_unresolved = len(tied) > 1
```

- [elevation_sweep_md.py:1194](../benchmark/elevation_sweep_md.py#L1194)
```python
keep = sorted(gens[k])
```

### 2. 샤드 완료 검사가 배열을 실제로 읽어 손상과 불일치를 거른다

**범위:** 2026-09-12 정정 뒤 현재 상태 · 합성 입력

ZIP가 잘린 입력, E 데이터의 CRC가 깨진 입력(shard_done=False, 실제 읽기 BadZipFile), E와 idx 길이가 다른 입력(shard_done=False) 모두 거절된다. 거절된 합성 입력은 3종이다. 함수는 이름 확인에 그치지 않고 모든 배열의 압축을 풀어 차원·길이·형식·인덱스 범위·유한성을 본다. 이번 실제 재고 판독 7472개에서 읽기 오류는 0개이고, 전수에서 잘못 거절된 파일도 없다.

**수정 제안:** 남은 일은 저장 쪽이다. 임시 파일에 쓴 후 검사를 통과한 결과를 최종 이름으로 교체하면 끊긴 파일이 창고에 남지 않는다.

⟨outputs/status_review_0911.json : findings[1]⟩

- [elevation_sweep_md.py:1026](../benchmark/elevation_sweep_md.py#L1026)
```python
arrs = {k: z[k] for k in names}     # ⭐여기서 전부 CRC 를 지난다
```

- [elevation_sweep_md.py:1047](../benchmark/elevation_sweep_md.py#L1047)
```python
if np.unique(ii).size != ii.size:
```

### 3. 교정 API의 정상 거절을 감사 빌더가 시험 성공으로 기록한다

**범위:** 2026-09-12 정정 뒤 현재 상태

교정 범위 밖 입력은 PfaOutOfRange로 거절된다. review_repository.main은 그 거절을 예상 결과로 받아 완료=True, 오류 종류=None로 끝나고, 임시 출력에서 JSON 작성=True, 노트북 작성=True다. 이전 ContractError가 나던 review_latest_readers 빌더의 완료=True도 확인했다. 거절된 입력에는 옛 동작이 돌려줬을 경계값을 함께 적어, 포화가 보이지 않게 되지는 않는다.

**수정 제안:** 남은 일은 교정표를 넓혀 더 엄격한 목표까지 실제로 교정하는 것이다. 그전까지 범위 밖이 필요하면 strict=False로 부르고 source를 결과에 함께 싣는다.

⟨outputs/status_review_0911.json : findings[2]⟩

- [review_repository_0911.py:246](../benchmark/review_repository_0911.py#L246)
```python
calls=[_probe(name,x) for x in values]))
```

- [passive_process.py:402](../src/passive_process.py#L402)
```python
if strict:
```

## 기존 보고서의 참조 검사

아래는 저장소 검사기의 실제 출력이다. 행 포인터 불일치 수는 권과 조각에 반복 실린 각주를 포함하므로 독립 주장 수로 해석하지 않는다. 링크가 열리는 것과 해당 링크의 행이 맞는 것은 별도 검사다. 불일치한 각주는 조각 빌더와 권 빌더로 다시 생성하고, 장기적으로는 배열 위치 대신 조건 식별자로 원장 행을 찾도록 바꾼다. 이번 포인터 검사는 문장 속 수치의 참·거짓까지 판정하지 않는다.

- `check_new_file_rules.py`: exit 0
```text
✅ 새로 생긴 것 없음  (기준선에 남은 빚 690 자리)
```

- `check_report_links.py`: exit 0
```text
── 편 사이 참조 검사 ──
  노트북 33개 / 계획 88편  (전부 지어졌다)
  링크 603개 · 그림 1035개 · 출처 2409개

✅ 위반 0건 — 끊긴 링크·그림·출처가 없다

⚠ 권고 19건 — old-section 19
   [old-section] reports/06_2_engines.ipynb:c2 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§1»
   [old-section] reports/06_4_sampling.ipynb:c4 — 옛 절 번호 «§2»
   … 외 7건 (`--all` 로 전부)
```

- `check_row_pointers.py`: exit 0
```text
═══ 각주 행 포인터 — 맞음 82 · ⛔어긋남 0 · 판정 불가 0 ═══
    («→ 팔/el» 꼬리 있는 것만 이름까지 대조한다. 꼬리 없는 24 개는 자리가 있는지만 봤다 — 맞음 24 · 어긋남 0)
  ✅ 각주가 전부 제 행을 가리킨다
```

⟨outputs/status_review_0911.json : checks.repository_checks⟩

## 실행 범위

기존 원장·소스·GPU 프로세스를 변경하지 않았다. 파일 시각과 CRC 변경은 임시 복제본에만 적용했다. 기존 전체 감사 main을 실행할 때 재고 열거 두 단계는 바로 앞에서 읽은 동일 스냅샷을 주입해 중복 판독을 줄였다. 생산 진단·API·판정 코드는 그대로 실행했다. 기존 수정의 완료와 새 반례의 범위를 구분한다.

```bash
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_status_0911.py
```
