# 시오나 현재 상태 전수 점검

조사 시작 2026-09-12T17:17:37.986787+00:00 · 작성 2026-09-13T03:59:11.968615+00:00 · 초기 기준 커밋 `0163234e0ced0e5d7834c45be1500e3b74a469a1`

[주피터 보고서](FULL_REVIEW_0912.ipynb) · [검증 원장](../outputs/full_review_0912.json) · [생성기](../benchmark/review_full_0912.py)

추가 점검 커밋 `5de9a098c4cafa6cabe97e11cee4332201520712`: 조사 중 새로 들어온 장면 판독기의 63행을 별도로 재현했다.

## 먼저 읽을 결과

이전 CRC·배열 길이 반례와 파일 시각 변경 반례는 수정됐다. 현재 원본 발간 사건도 재현됐다. 이번에는 표집률 사다리와 새 파형 분석의 발간 지표, 기준선 검증, 다음 실험의 해석 기준에서 보완점을 확인했다.

## 조사 범위

| 대상 | 검사 | 결과 |
|---|---|---|
| 숨김·보관 포함 파일 19745개 | .git·__pycache__ 제외 열거 | 바이너리 내용의 과학적 타당성과는 별도 |
| Python 806개 | 문법 파싱 | 성공 805개, 코드 조각 파일의 문법 오류 1개 |
| JSON 4108개·노트북 162개 | 실제 파싱 | 오류 0개 |
| 생산 샤드 7588개 | 모든 배열 CRC·shape·유한값·idx 분할·완료 함수 | 오류 0개, 판독 중 변경 0개 |
| 나머지 NPZ 1077개 | CRC·NPY 헤더, 객체 역직렬화 제외 | 오류 0개 |
| 기존 발간 사건 원본 80개 | 협곡·낙차·동체 판독 재계산 | 기존 발간값과 일치 |
| 파형 원장 292행 | 현재 값 재현·평균 길이 대조·독립 누적합 검산 | 아래 지적 참조 |
| 표집률 사다리 122칸 | 생산식·발간값·저장 표집률 비교 | 아래 지적 참조 |

우리 커널 cfg의 NaN 1478파일은 깊이·광선 예산의 미해당 표식으로 코드에 정의돼 있어 결함에서 제외했다. 문법 오류 파일 outputs/_prop_law_literals_0816.py는 실행 스크립트가 아닌 붙여 넣기용 딕셔너리 조각이다. 미완 칸은 계산 진행 상태와 분할 세대 선택을 구분해 읽어야 한다. 메쉬·사진·PDF의 내용 전체 판정이나 GPU 재실험은 이번 범위에 포함되지 않는다.

⟨outputs/full_review_0912.json : checks.additional.wide_artifacts⟩ ⟨outputs/full_review_0912.json : checks.arrays⟩ ⟨outputs/full_review_0912.json : checks.additional.other_arrays⟩

## 실행 상태

2026-09-12T17:29:12.605537+00:00 조회에서 워커 11개, 감독자와 지킴이 실행을 확인했다. 큐 분수는 투입 포인터다.

- `runners/jobs_0927.txt`: [09-13 02:29:03] 상태 G0:3/3(상한3·남0G) G1:2/2(상한2·남45G) G2:1/1(상한1·남71G) G3:2/1(상한2·남51G) G4:3/2(상한2·남48G) · 큐 11/12 · 워커 11 · RAM 7.0G · CPU 0.70

- `runners/logs/sup_jobs_0923.log`: [09-12 00:00:02] == 종료 (14 줄 실행 · 실패 0 · 큐 14/14) ==
- `runners/logs/sup_jobs_0924.log`: [09-12 03:35:58] == 종료 (30 줄 실행 · 실패 0 · 큐 30/30) ==
- `runners/logs/sup_jobs_0925.log`: [09-12 10:57:44] == 종료 (32 줄 실행 · 실패 0 · 큐 32/32) ==
- `runners/logs/sup_jobs_0926.log`: [09-13 01:49:16] == 종료 (72 줄 실행 · 실패 0 · 큐 72/72) ==

현재 사슬의 후속 차례는 0929 → 0928이다. 작업 중 수치는 변하므로 위 조회 시각을 함께 읽는다.

## 확인된 보완점

### 1. 새 장면 분석이 다른 조건의 빈 하늘을 대조군으로 선택한다

**영향:** 최신 발간 수치와 위·아래 판정에 영향

**검증 범위:** Latest commit added during audit. Published values reproduced; only the free-space engine identity was changed for comparison.

조사 중 추가된 장면 원장 63행을 재현했다. 그중 43행은 장면 꼬리표만 제거한 동일 조건의 빈 하늘과 다른 engine을 선택했다. 올바른 짝의 누락은 0행이며, 대조군만 맞추면 표의 0 dB 초과 표시가 11행에서 바뀐다. 최대 변화 52.68 dB는 bldg / R0D0E0F1 / el+0에서 +1.10 → -51.58 dB다. free 사전이 스위치·앙각만 키로 사용해 다른 기체·로터 설정·표집률의 후보가 덮어쓴다. 발간값의 재현만으로는 대조군 선택의 타당성을 검증할 수 없다. 최대 차이가 난 el 0 값은 대조군 오류의 산술적 영향이며 물리 결과의 인용값으로 쓰지 않는다. 이 새 판독기의 ARMS 설명에도 회절을 굴절로, 굴절을 반사로 적은 이름 혼동이 반복된다.

**수정 제안:** 장면 요소만 다른 동일 조건의 대조군을 유일하게 선택하고, 기체·PRF·로터 설정·자세 수를 쌍으로 검사한다. 중복 후보는 거절하고 선택 근거를 남긴 뒤 장면 표를 재발간한다. 스위치 이름도 실제 옵션과 맞춘다.

⟨outputs/full_review_0912.json : checks.additional.late_scene⟩

- [benchmark/read_scenephysics_0913.py:124](../benchmark/read_scenephysics_0913.py#L124)
```python
free[(a.group(1), r["el_deg"])] = r["engine"]
```

- [benchmark/read_scenephysics_0913.py:134](../benchmark/read_scenephysics_0913.py#L134)
```python
fengine = free.get((arm, el))
```

- [benchmark/read_scenephysics_0913.py:52](../benchmark/read_scenephysics_0913.py#L52)
```python
ARMS = {"R0D0E0F1": "확산만", "R0D1E0F1": "+굴절", "R0D1E1F1": "+굴절+모서리",
```

### 2. 주 집계와 아틀라스가 표집률 사다리를 기본 시간축으로 읽는다

**영향:** 발간 지표·그림 축에 영향

**검증 범위:** 원본 샤드와 현재 발간 원장을 대조하고, 생산 band_metrics에서 표집률만 바꿔 재계산했다.

저장 표집률이 기본 19700 Hz와 다른 122칸이 있고, 122칸이 아틀라스에도 있다. 현재 생산식은 발간값과 0칸 불일치였으며, 저장 표집률을 적용하면 107칸의 track 지표가 바뀐다. 예: ours_mavic4pro_r15_n8192_prf39400_mfixbatteryi5_blperairframe / el+0에서 beat_hz는 59.79 → 119.52 Hz다. 저장 표집률에 비해 주파수축이 줄고 시간축이 늘어난다. 이 재계산은 표집률 효과만 분리했으며 다른 기체별 잣대의 타당성까지 인증하지 않는다.

**수정 제안:** 샤드 meta[4]를 칸별 prf_hz로 발행하고 일치 여부를 검사한다. STFT 창·시간축·리듬 지표·아틀라스에 그 값을 전달한 뒤 영향받는 원장과 그림을 재생성한다.

⟨outputs/full_review_0912.json : checks.additional.timeaxis⟩

- [benchmark/elevation_sweep_md.py:1376](../benchmark/elevation_sweep_md.py#L1376)
```python
prf, ffl = float(TJ["prf_hz"]), float(TJ["f_flash_hz"])
```

- [benchmark/build_md_atlas.py:127](../benchmark/build_md_atlas.py#L127)
```python
PRF = float(M["prf_hz"])
```

### 3. Wi-Fi 프레임 평균 길이에 블록 수가 빠졌다

**영향:** 신규 발간값에 영향

**검증 범위:** 현재 파형 원장의 모든 행을 원본 E로 재현하고, 평균 길이만 바꿨다. 누적합 구현으로 별도 검산했다.

CPI_CFG의 Wi-Fi 프레임은 b=9개 블록이다. 판독기는 주석의 블록 길이 0.052 ms만 읽어 프레임 길이 0.468 ms 대신 쓴다. 292행의 현재 Wi-Fi 값은 모두 재현됐다. 평균 길이 보정 시 rms_keep_db 변화의 중앙값은 -6.05 dB이고, 양·음 변화가 모두 있다. 실외 el−30/−60 31칸에서는 -12.81~-0.26 dB다. 전체 최댓값 하나를 대표 효과로 인용하면 표본 선택과 조건 차이를 숨기게 된다.

**수정 제안:** 주석 대신 실제 블록 길이·블록 수·표집률에서 프레임 길이와 반복률을 함께 유도한다. 현재의 이산 평균 모형 안에서 보정한 뒤 파형 표를 다시 생성한다.

⟨outputs/full_review_0912.json : checks.additional.waveform⟩

- [benchmark/read_wfsurvive_0912.py:69](../benchmark/read_wfsurvive_0912.py#L69)
```python
blk_ms = float(bl.group(1)) * (1.0 if bl.group(2) == "ms" else 1e-3)
```

- [src/experiment_detection.py:100](../src/experiment_detection.py#L100)
```python
"wifi": dict(M=112, b=9),    # 블록 4160(52µs)×9 → PRF 2136Hz, T_CPI 52ms, Ns 4.19M
```

### 4. 접힌 주파수 띠를 잘라서 실제 주성분을 제외한다

**영향:** 분석 방법 결함 · 합성 반례

**검증 범위:** 기존 survive()에 단일 복소 정현파를 넣었다.

입력 1550 Hz는 날개끝 기준 1102 Hz의 원래 띠 안에 있다. 프레임율 2000 Hz에서 실제 접힘은 450 Hz지만, 판독 띠는 551~1000 Hz다. 전체 FFT는 450.06 Hz를 찾고, 띠 안 최강선은 750.90 Hz를 반환한다. 예상한 선을 스스로 제외한 뒤 다른 성분을 고른 것이다.

**수정 제안:** 입력 띠 전체를 접힘 사상으로 옮겨 구간의 합집합을 만든다. 입력 피크와 접힌 피크의 대응도 따로 확인한다. 단순한 상한 자르기나 접힌 중심 주변의 임의 비율 띠를 대체한다.

⟨outputs/full_review_0912.json : checks.additional.waveform.tone⟩

- [benchmark/read_wfsurvive_0912.py:148](../benchmark/read_wfsurvive_0912.py#L148)
```python
if lo >= ny:                       # 띠 전체가 창 밖 — 접어서 어디로 가는지 본다
```

- [benchmark/read_wfsurvive_0912.py:153](../benchmark/read_wfsurvive_0912.py#L153)
```python
return lo, min(hi, ny)
```

### 5. 파형 표가 서로 다른 조건을 같은 행 이름으로 표시한다

**영향:** 현재 문면 영향 · 입력 검증의 잠재 결함

**검증 범위:** 발간 행의 engine과 사람이 읽는 표의 장면·앙각·팔 열을 대조했다. 시간축·세대 충돌은 임시 샤드로 시험했다.

선택 목록에 음수 방위 8행, 표집률 변경 56행, 로터 설정 꼬리표 31행이 들어간다. 장면·앙각·팔 표시가 같은 묶음은 21개다. JSON의 engine으로는 구별되지만 Markdown 표에서는 생략된다. 별도 합성 시험에서는 서로 다른 PRF의 두 샤드도 반환=True, 세대 선택 뒤 충돌 8자세가 남아도 반환=True였다. 후자의 손상이 현재 발간 입력에서 발견됐다는 뜻은 아니다.

**수정 제안:** 기체·방위·표집률·로터 설정을 명시적 조건으로 선택하고 표에도 표시한다. 공통 로더에서 PRF·N·idx·유한값과 선택 후 충돌 상태를 검사하고 제외 사유를 기록한다.

⟨outputs/full_review_0912.json : checks.additional.waveform.display_identity⟩

- [benchmark/read_wfsurvive_0912.py:199](../benchmark/read_wfsurvive_0912.py#L199)
```python
and not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt|fc)[\d._]",
```

- [benchmark/read_wfsurvive_0912.py:95](../benchmark/read_wfsurvive_0912.py#L95)
```python
fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")
```

### 6. 기준선 검사가 사건 수의 변화를 놓친다

**영향:** 기준선 검증 기능에 영향

**검증 범위:** 원장을 메모리에 복제해 사건 수를 바꿨고, 실제 measure()를 실행했다. 별도 검사기의 반환은 동일하게 유지했다.

협곡의 사건 수·Hampel 마스크 수 20필드를 바꿔도 measure 변경=False였다. 해당 원장은 사건 수를 구조적으로 보존하지 않고 문자열 안에 특정 숫자가 있는지만 검사한다. 낙차 사다리 측정 키 포함=False다. 저장된 보고서의 숫자를 읽는 방식이므로 원본 샤드가 바뀌고 상류 보고서가 낡으면 그것도 직접 재계산하지 않는다. 새 파일 관문은 이 기준선 원장의 _meta.generator 누락도 보고했다.

**수정 제안:** 조건별 실제 사건 수·집합 식별자·선택 파일 해시를 저장한다. 낙차 원장도 포함하고, 샤드 재계산 또는 상류 최신성 확인을 구분해 검사한다. generator를 정해진 메타 위치로 옮긴다.

⟨outputs/full_review_0912.json : checks.additional.freeze⟩

- [benchmark/freeze_0912.py:83](../benchmark/freeze_0912.py#L83)
```python
m["canyon_events"]["has_96"] = ": 96" in txt or " 96," in txt or "96]" in txt
```

- [benchmark/freeze_0912.py:84](../benchmark/freeze_0912.py#L84)
```python
m["canyon_events"]["has_339"] = "339" in txt
```

### 7. 실외 발주서의 물리 이름과 필터 판정 기준을 고쳐야 한다

**영향:** 실험 설계·해석 문면

**검증 범위:** 발주서의 팔 이름을 실제 스위치 해석과 대조했고, 기존 Hampel 함수로 인과 반례를 계산했다.

발주서는 R0D1E1F1을 «굴절+모서리»로 설명하지만 실제 설정은 굴절 꺼짐·회절 켜짐·모서리회절 켜짐이다. 또 «여러 앙각에서 계속 위로 뜨면 필터가 만든 구조»라는 판정은 대조가 부족하다. 합성 입력에서는 필터 마스크 0개, 필터 변화 0인데 빈 하늘보다 높은 자세가 8192/8192개다. 필터 후 차이만으로 필터가 만든 효과를 판정할 수 없다.

**수정 제안:** R=굴절·D=회절·E=모서리회절을 정확히 적고 정반사는 별도 상시 설정임을 구분한다. 동일 입력의 필터 전후 변화와 장면·빈 하늘 양쪽의 동일 처리 결과를 함께 비교한다. 지면·건물 기여 해석에는 차폐와 경로 상호작용도 남긴다.

⟨outputs/full_review_0912.json : checks.additional.filter_design⟩

- [runners/make_jobs_0928.py:29](../runners/make_jobs_0928.py#L29)
```python
A 지면만·건물만 +굴절+모서리 {−15,−45,−75} 씩 · 건물만 확산만 {−75}   ← 싸고 비어 있다
```

- [runners/make_jobs_0928.py:49](../runners/make_jobs_0928.py#L49)
```python
· 여러 앙각에서 계속 위로 뜨면 그것은 **필터가 만든 구조**이므로, 회절 팔에는 이 필터를
```

- [benchmark/elevation_sweep_md.py:745](../benchmark/elevation_sweep_md.py#L745)
```python
sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
```

### 8. 0929의 복소 평탄성에는 전파 지연 기준이 먼저 필요하다

**영향:** 대기 중인 실험의 해석 설계

**검증 범위:** 생산 E의 위상 정의를 확인하고, 산란계수가 일정한 점 표적을 해석식으로 계산했다.

거리 15 m 점 표적의 산란계수를 일정하게 둬도 지정한 주파수 격자에서 위상은 [1.25, -179.38, 0.0, 179.38, -1.25]도로 움직인다. 중앙과의 복소 차이는 최대 1.999970이고, 알려진 전파 지연을 제거하면 오차가 3.4e-19다. 원본 E는 경로 전파 위상을 포함하므로 이를 그대로 반사율의 주파수 의존성이라고 읽으면 혼동된다. 대기 중인 실험의 결과를 미리 판정한 것은 아니다.

**수정 제안:** 원시 채널 응답과 공통 지연을 제거한 표적 응답을 나란히 정의한다. 대역 안 성긴 점검이 부반송파 전부의 평탄성을 보증하는 범위도 구분한다. 동일 자세·솔버 설정·수치 민감도를 맞춘 뒤 해석한다.

⟨outputs/full_review_0912.json : checks.additional.design_literature.frequency_design⟩

- [runners/make_jobs_0929.py:35](../runners/make_jobs_0929.py#L35)
```python
· 네 점의 복소 반사율이 크기·위상 모두 좁은 폭 안에 모이면, 「이 대역에서 표적은
```

- [benchmark/elevation_sweep_md.py:902](../benchmark/elevation_sweep_md.py#L902)
```python
_t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])
```

### 9. 기존 전체 감사 생성기는 다른 의존성 누락으로 멈춘다

**영향:** 점검 도구의 실행 실패

**검증 범위:** 기존 main을 임시 출력으로 실행하고 실패 함수를 별도로 재현했다.

Pfa 예외 처리는 수정됐지만, 저장 중단 시험에서 현재 AssertionError(NameError)가 발생한다. 생산 저장 호출에 bake_stamp(t0)가 추가됐는데 AST로 호출을 떼어 실행하는 시험 환경에는 그 함수가 없다. 따라서 저장 중단을 주입하기 전에 실패하며 기존 보고서를 다시 생성하지 못한다. 이는 생산 워커의 실패와 구분된다.

**수정 제안:** 생산 저장 함수와 의존성을 함께 불러 실행한다. 장기적으로는 저장 경로를 작은 함수로 분리해, AST 내부 줄을 떼어내는 시험의 의존성 누락을 줄인다.

⟨outputs/full_review_0912.json : checks.additional.boundary.old_audit_failure⟩

- [benchmark/review_repository_0911.py:208](../benchmark/review_repository_0911.py#L208)
```python
assert failure=='OSError',failure
```

- [benchmark/elevation_sweep_md.py:689](../benchmark/elevation_sweep_md.py#L689)
```python
**bake_stamp(t0),
```

### 10. 선행연구 README가 갱신 전 조사와 옛 원인 설명을 유지한다

**영향:** 현재 안내 문서의 불일치

**검증 범위:** 로컬 외부 저장 원장과 README를 대조했다. 개별 논문 전체나 외부 색인은 재검토 범위 밖이다.

저장 원장은 970편·초록 802편이며, 점검 가능한 기준 논문의 DOI 발견은 4/4이다. README는 이전 편 수와 다른 분모의 재현율을 «지금»으로 표시하고, 이미 수정한 제목 검색 실패의 원인도 예전 설명으로 남긴다. 기준 논문 몇 편의 발견률을 전체 관련 논문의 검색 재현율로 넓혀 읽을 수도 있다.

**수정 제안:** README 요약을 현재 원장에서 생성하고 이전 표에는 기준 날짜를 붙인다. DOI가 확인되는 범위 내 기준 논문의 발견률이라는 이름과 분모를 유지하며 전체 문헌의 망라율과 구분한다.

⟨outputs/full_review_0912.json : checks.additional.design_literature.literature⟩

- [prior_work/README.md:66](../prior_work/README.md#L66)
```python
**학회 11 종**, 2025-01 이후 **275 편**(정본 123 · 일반 152)
```

- [prior_work/README.md:74](../prior_work/README.md#L74)
```python
| 재현율(아는 6 편) | 3/6 | 3/6 | 4/6 | **4/6** |
```

## 관문 결과와 해석 한계

관문 통과는 해당 검사기가 다루는 범위의 결과다. 링크 존재·조건 선택의 일치가 문장 속 수치나 인과 설명까지 인증하지 않는다.

- `check_new_file_rules`: exit 1
```text
⛔새로 생긴 것 1 곳  (기준선에 남은 빚 690 자리)

  ⓔ못 굽는 원장  outputs/freeze_0912.json:1
      _meta.generator 없음
      → 이 원장을 다시 구울 스크립트 경로를 _meta.generator 에 적어라
```

- `check_report_links`: exit 0
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

- `check_row_pointers`: exit 0
```text
═══ 각주 행 포인터 — 맞음 82 · ⛔어긋남 0 · 판정 불가 0 ═══
    («→ 팔/el» 꼬리 있는 것만 이름까지 대조한다. 꼬리 없는 24 개는 자리가 있는지만 봤다 — 맞음 24 · 어긋남 0)
  ✅ 각주가 전부 제 행을 가리킨다
```

- `check_retracted`: exit 0
```text
── 철회한 수가 다시 인용되고 있는가 ──
  철회 항목 14개 · 표시 없이 인용된 자리 0건

✅ 철회한 수가 표시 없이 인용된 자리가 없다
```

- `check_stale_titles`: exit 0
```text
── 편 제목이 바뀌었는데 이름표가 안 따라왔나 ──
  계획 편 88 · 어긋난 이름표 0 · 어긋난 색인 0

✅ 이름표와 색인이 모두 현행 제목과 맞는다
```

## 수정 순서

1. 새 장면 판독기의 대조군을 맞추고, 표집률과 Wi-Fi 프레임 길이를 고쳐 영향받는 수치·그림·표를 재생성한다.
2. 파형의 접힘 띠와 조건 선택·공통 입력 검증을 고친다.
3. 기준선 비교가 사건 수 변경을 감지하도록 만들고 감사 생성기를 현재 저장 경로에 맞춘다.
4. 대기 실험의 해석 기준과 선행연구 안내 문서를 수정한다.

기존 원장·생산 코드·GPU 워커를 변경하지 않았다. 새 점검 생성기·원장·메모·노트북만 작성했다. 합성 반례가 현재 실험에서 발생했다고 일반화하지 않았으며, 모든 이진 자산의 내용까지 읽었다고 주장하지 않는다.

```bash
/workspace/.venvs/py312/bin/python benchmark/review_full_0912.py
```
