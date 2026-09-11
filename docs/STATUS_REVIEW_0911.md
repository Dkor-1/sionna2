# 현재 상태 재점검

기준 `1c82aa5304e82037c0f54f1493a1b6fec6c0caac` · 2026-09-11T16:28:26.354979+00:00

[주피터 보고서](STATUS_REVIEW_0911.ipynb) · [실행 원장](../outputs/status_review_0911.json) · [생성기](../benchmark/review_status_0911.py)

## 현재 실행과 확인된 수정

프로세스 조회 시점에 워커 8개가 있었고, 감독자·지킴이 목록과 최근 로그를 원장에 남겼다. 큐의 분수는 투입 포인터이며 완료 수로 읽지 않는다.

실제 저장 샤드 7467개를 재판독했다. 읽기 오류 0개다. 최근 수정되어 제외한 파일은 2개다. 기존 관측 사건은 원본 80개·협곡 10칸·낙차 7칸·동체 8칸에서 발간값과 일치했다.

영 전계가 일부인 5조건의 현재 레벨과 결측 수를 원본으로 다시 계산했다. 원본 파일 시각을 유지한 현재 재고에서는 세대 선택과 발간 선택 기록이 일치한다. 교정 범위 밖 목표는 거절되고, 표 안 목표는 교정값을 반환한다. 각 확인의 상세 조건은 aggregation·generation_current·pfa에 있다.

## 남은 보완점

### 1. 파일 시각이 바뀌면 세대 선택이 다시 혼합 자료를 고른다

**범위:** 실제 충돌 샤드의 임시 복제 대조

현재 원본에서는 4조건 모두 완결 세대를 선택한다. 하지만 동일 바이트를 임시 복제하고 파일 시각만 같게 두면, 선택 결과에 중복 4096행이 다시 들어간다. 원본 선택과 비교해 바뀐 자세 수는 [3582, 3057, 3981, 3621]다. one_generation은 파일 수정 시각 간격으로 세대를 묶으며 선택 뒤에도 중복 충돌을 재검사하지 않는다. 현재 아틀라스가 이 복제 입력으로 발행됐다는 뜻은 아니다.

**수정 제안:** 실행 식별자와 분할 설정을 저장하고, 선택한 묶음의 idx 중복·충돌을 마지막에 검사한다. 파일 시각을 세대의 확정 근거로 삼는 범위를 줄이고, 확정할 수 없는 충돌은 미확인으로 남긴다.

⟨outputs/status_review_0911.json : findings[0]⟩

- [elevation_sweep_md.py:1061](../benchmark/elevation_sweep_md.py#L1061)
```python
for f in sorted(fs, key=os.path.getmtime):
```

- [elevation_sweep_md.py:1075](../benchmark/elevation_sweep_md.py#L1075)
```python
keep = sorted(gens[k])
```

### 2. 샤드 완료 검사는 배열 내용 손상과 길이 불일치를 통과시킨다

**범위:** 수정된 완료 함수의 남은 범위 · 합성 입력

ZIP가 잘린 입력은 거절한다. 그러나 E 데이터의 CRC가 깨진 입력은 shard_done=True인데 실제 읽기는 BadZipFile다. E와 idx 길이가 다른 입력도 shard_done=True다. 현재 함수는 idx·E·meta라는 이름의 존재만 확인한다. 이번 실제 재고 판독 7467개에서 읽기 오류는 0개였다.

**수정 제안:** 완료 판정에서 필수 배열을 읽어 길이·형식·인덱스 범위를 확인한다. 임시 파일에 쓴 후 검사를 통과한 결과를 최종 이름으로 교체하는 저장 방식도 함께 적용한다.

⟨outputs/status_review_0911.json : findings[1]⟩

- [elevation_sweep_md.py:1006](../benchmark/elevation_sweep_md.py#L1006)
```python
names = set(z.files)
```

- [elevation_sweep_md.py:1007](../benchmark/elevation_sweep_md.py#L1007)
```python
return {"idx", "E", "meta"} <= names
```

### 3. 교정 API의 정상 거절을 기존 전체 감사 빌더가 처리하지 못한다

**범위:** 이번 API 수정 뒤의 감사 실행 실패

교정 범위 밖 입력은 현재 PfaOutOfRange로 올바르게 거절된다. 하지만 review_repository.main은 그 입력의 거절을 시험 성공으로 처리하지 않아 PfaOutOfRange로 멈춘다. 임시 출력에서 JSON 작성=False, 노트북 작성=False다. 반면 이전 ContractError가 나던 review_latest_readers 빌더의 완료=True는 확인했다.

**수정 제안:** 범위 밖 입력은 예상 예외를 잡아 거절 여부로 기록하고, 표 안 입력은 반환값과 출처를 대조한다. API 수정과 이를 부르는 감사 생성기를 함께 갱신한다.

⟨outputs/status_review_0911.json : findings[2]⟩

- [review_repository_0911.py:233](../benchmark/review_repository_0911.py#L233)
```python
calls=[dict(target=x,nominal=pp.pfa_nominal_for(name,x)) for x in values]))
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

- `check_row_pointers.py`: exit 1
```text
═══ 각주 행 포인터 — 맞음 2 · ⛔어긋남 80 · 판정 불가 0 ═══

  ⛔reports/04_elevation-coverage.ipynb  (25 건)
      [^206] rows[424] 라고 적혀 있으나 — 적힌 것 «sionna/el+0» · 실제 ours_r240_n8192 / el+0
      [^207] rows[460] 라고 적혀 있으나 — 적힌 것 «sionna_p4000000000/el+0» · 실제 ours_r60_n8192_mfixbatteryi5_blperairframe / el+0
      [^209] rows[429] 라고 적혀 있으나 — 적힌 것 «sionna/el-75» · 실제 ours_r30_n8192 / el-60
      [^210] rows[451] 라고 적혀 있으나 — 적힌 것 «sionna_p250000000/el-75» · 실제 ours_r480_n8192_mfixbatteryi5_blperairframe / el-30
      [^211] rows[424] 라고 적혀 있으나 — 적힌 것 «sionna/el+0» · 실제 ours_r240_n8192 / el+0
      … 외 20 건

  ⛔reports/05_engine-physics.ipynb  (15 건)
      [^27] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^28] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^29] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^50] rows[430] 라고 적혀 있으나 — 적힌 것 «sionna/el-90» · 실제 ours_r30_n8192_az45_mfixbatteryi5_blperairframe / el+0
      [^51] rows[430] 라고 적혀 있으나 — 적힌 것 «sionna/el-90» · 실제 ours_r30_n8192_az45_mfixbatteryi5_blperairframe / el+0
      … 외 10 건

  ⛔reports/_parts/84_physics-denominator.ipynb  (6 건)
      [^11] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^12] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^13] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^34] rows[430] 라고 적혀 있으나 — 적힌 것 «sionna/el-90» · 실제 ours_r30_n8192_az45_mfixbatteryi5_blperairframe / el+0
      [^35] rows[430] 라고 적혀 있으나 — 적힌 것 «sionna/el-90» · 실제 ours_r30_n8192_az45_mfixbatteryi5_blperairframe / el+0
      … 외 1 건

  ⛔reports/_parts/85_physics-above-limit.ipynb  (2 건)
      [^7] rows[424] 라고 적혀 있으나 — 적힌 것 «sionna/el+0» · 실제 ours_r240_n8192 / el+0
      [^8] rows[446] 라고 적혀 있으나 — 적힌 것 «sionna_p250000000/el+0» · 실제 ours_r45_n8192_mfixbatteryi5_blperairframe / el-60

  ⛔reports/_parts/86_physics-deck-match.ipynb  (4 건)
      [^10] rows[1424] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-15» · 실제 sionna_p4000000000_swR0D0E0F1_r30_n8192_mfixbatteryi5_blperairframe_d2 / el-75
      [^11] rows[1424] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-15» · 실제 sionna_p4000000000_swR0D0E0F1_r30_n8192_mfixbatteryi5_blperairframe_d2 / el-75
      [^12] rows[454] 라고 적혀 있으나 — 적힌 것 «sionna_p250000000_phys/el-15» · 실제 ours_r60_n8192 / el-60
      [^38] rows[447] 라고 적혀 있으나 — 적힌 것 «sionna_p250000000/el-15» · 실제 ours_r45_n8192_mfixbatteryi5_blperairframe / el-75

  ⛔reports/_parts/87_budget-not-physics.ipynb  (25 건)
      [^1] rows[424] 라고 적혀 있으나 — 적힌 것 «sionna/el+0» · 실제 ours_r240_n8192 / el+0
      [^2] rows[460] 라고 적혀 있으나 — 적힌 것 «sionna_p4000000000/el+0» · 실제 ours_r60_n8192_mfixbatteryi5_blperairframe / el+0
      [^4] rows[429] 라고 적혀 있으나 — 적힌 것 «sionna/el-75» · 실제 ours_r30_n8192 / el-60
      [^5] rows[451] 라고 적혀 있으나 — 적힌 것 «sionna_p250000000/el-75» · 실제 ours_r480_n8192_mfixbatteryi5_blperairframe / el-30
      [^6] rows[424] 라고 적혀 있으나 — 적힌 것 «sionna/el+0» · 실제 ours_r240_n8192 / el+0
      … 외 20 건

  ⛔reports/_parts/88_engine-claim-scope.ipynb  (3 건)
      [^6] rows[1423] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el+0» · 실제 sionna_p4000000000_swR0D0E0F1_r30_n8192_mfixbatteryi5_blperairframe_d2 / el-60
      [^7] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15
      [^34] rows[1429] 라고 적혀 있으나 — 적힌 것 «sionna_phys/el-90» · 실제 sionna_p4000000000_swR0D0E0F1_r45_n8192_mfixbatteryi5_blperairframe_d2 / el-15

  ⭐고치는 법: 손으로 번호를 고치지 마라. 그 조각의 빌더(src/build_part*.py)를 다시 돌리고 src/build_volumes.py 로 권을 다시 짠다.
```

⟨outputs/status_review_0911.json : checks.repository_checks⟩

## 실행 범위

기존 원장·소스·GPU 프로세스를 변경하지 않았다. 파일 시각과 CRC 변경은 임시 복제본에만 적용했다. 기존 전체 감사 main을 실행할 때 재고 열거 두 단계는 바로 앞에서 읽은 동일 스냅샷을 주입해 중복 판독을 줄였다. 생산 진단·API·판정 코드는 그대로 실행했다. 기존 수정의 완료와 새 반례의 범위를 구분한다.

```bash
CUDA_VISIBLE_DEVICES='' /workspace/.venvs/py312/bin/python benchmark/review_status_0911.py
```
