# 현재 상태와 추가 계산·판독 경로 점검

점검 시각: 2026-09-13T10:00:07Z → 2026-09-13T10:13:34Z
커밋: de54f9ee5a2d51d46ffa1d29013446fd2f34415d → de54f9ee5a2d51d46ffa1d29013446fd2f34415d

## 확인된 수정

- 장면 분석 64행의 대조군 오류 0건. 필터 수치도 현재 발간값을 재현했다.
- 비기본 PRF 122칸의 track 재계산 불일치 0건.
- 아틀라스 리듬 몫 2359칸 재계산의 반올림 범위 밖 불일치 0건. 다른 반송파 49칸과 다른 PRF 122칸을 포함한다. 그림을 전부 재렌더링한 검사는 아니다.
- Wi-Fi 292행의 생산 함수 재현 불일치 0건, 독립 누적합 계산 불일치 0건. 프레임 길이는 0.468 ms다.
- 이전 접힘 반례의 예상 450 Hz를 현재 판독기가 450.06 Hz로 찾는다.
- 기준선 수치 추출은 바꾼 사건 필드 20개를 감지한다.

## 조사 범위와 남은 범위

전체 파일 19864개를 열거했다(.git·__pycache__ 제외, ignored 포함). JSON 4110개와 노트북 163개를 파싱했고 각각 오류 0·0건이다.
Python 구문 파싱 성공 809개. 구문 오류 항목은 [{'path': 'outputs/_prop_law_literals_0816.py', 'error': 'IndentationError'}]이며 기존 자료 추출 조각으로 확인했다. 파일 전부의 모든 줄을 의미 검증했다는 뜻은 아니다.
안정된 생산 샤드 7642개는 모든 배열의 CRC·길이·idx 분할·비유한 값을 확인했고 오류 0건, 검사 중 변경 0건이다. ours의 cfg에 명시적으로 저장된 미적용 NaN은 결함에서 제외했다.
그 밖의 NPZ 1077개는 CRC와 NPY 헤더를 검사했다. 객체 배열은 역직렬화하지 않았다. 이미지·PDF·메쉬는 열거했으며 전부의 내용·기하 타당성을 재검증하지 않았다.
감사 종료 시 워커 6개. 실행 상태는 원장 checks.queue_final에 시각과 로그를 함께 남겼다. 조사 중 새로 쓰인 파일은 안정된 샤드 모집단과 분리했다.
검사기는 기준선 이후 새 문제를 검출하는 범위를 가진다. 통과를 전체 과학적 타당성의 인증으로 해석하지 않는다. 검사별 원문은 checks.gates에 있다.

## 보완점

### 1. 주 집계가 다른 기체에도 기본 기체의 날개 통과율을 쓴다

**등급:** 새 확인 · 발간 수치 영향

다른 기체 488칸의 현재 track은 발간값과 0칸 불일치다. 날개 통과율을 기체 제원으로 바꾸면 445칸이 변하며, 완전한 487칸 중 444칸도 변한다. 예: ours_s1000plus_r15_n8192_az67.5 / el-45, h1_over_h2_db가 +46.43 → -4.81 dB다. 기준 날개 통과율은 126.67 → 148.9 Hz다. STFT 창과 배음 측정 위치가 함께 달라진다. 기체 제원에 맞춘 잣대의 보정이며 실측 검증이 아니다.

**수정 권고:** 칸별 날개 통과율을 원장에 기록하고 STFT 창·캐시 키·배음 비교·fixed 지표에 함께 전달한다. 기체가 다른 팔의 track과 fixed를 재생성한다. 아틀라스의 기체별 계산과 주 집계를 함께 대조한다.

근거 원장: `outputs/current_review_0913.json` → `checks.numeric.drone_flash`

- [benchmark/elevation_sweep_md.py:1376](../benchmark/elevation_sweep_md.py#L1376) — `prf, ffl = float(TJ["prf_hz"]), float(TJ["f_flash_hz"])`
- [benchmark/elevation_sweep_md.py:1422](../benchmark/elevation_sweep_md.py#L1422) — `h1_over_h2_db=round(float(pkdb(ffl) - pkdb(2 * ffl)), 2),`
- [benchmark/build_md_atlas.py:347](../benchmark/build_md_atlas.py#L347) — `f_flash_hz=int(s.prop_blades) * f_rev,`

### 2. 움직이는 전력의 대역 퍼짐을 전체 전력의 짝·홀 차이와 비교한다

**등급:** 새 확인 · 발간 해석 영향

대역 퍼짐은 E의 평균을 뺀 전력인데 half_spread는 평균을 포함한 전력이다. 실외 el-30: 움직이는 몫의 대역 퍼짐 0.235 dB, 발간 짝·홀 차이 0.015 dB, 같은 AC 전력으로 계산한 차이 1.647 dB. 실외 el-60: 움직이는 몫의 대역 퍼짐 0.239 dB, 발간 짝·홀 차이 0.008 dB, 같은 AC 전력으로 계산한 차이 0.833 dB. 두 실외 줄 모두 기존의 «흔들림보다 크다» 문장이 같은 통계로 맞추면 성립하지 않는다. AC 계산은 전체 자세 평균을 한 번 제거한 뒤 같은 짝·홀 분할을 적용했다. 이 분할 차이는 결정적 표본 분할의 민감도이며 신뢰구간이 아니다.

**수정 권고:** 전체 전력과 AC 전력 각각에 대응하는 짝·홀 차이를 계산한다. 표 제목은 «짝·홀 분할 차이»로 쓰고, 재실행 산포·광선 격자 민감도와 별도로 기록한다. 비교 문장은 동일한 통계끼리 만든다.

근거 원장: `outputs/current_review_0913.json` → `checks.numeric.band_half_summary`

- [benchmark/read_bandflat_0913.py:334](../benchmark/read_bandflat_0913.py#L334) — `a, b = halves_level_db(E)`
- [benchmark/read_bandflat_0913.py:412](../benchmark/read_bandflat_0913.py#L412) — `"기울기를 가르지 못한다" % half if mv_band < 2.0 * half else`
- [benchmark/read_bandflat_0913.py:377](../benchmark/read_bandflat_0913.py#L377) — `half = float(np.median([g[1]["half_spread_db"] for g in got]))`

### 3. 새 띠 생존 지표도 띠 밖에서 접혀 온 성분을 센다

**등급:** 새 확인 · 합성 반례

입력 400 Hz 성분의 진폭을 0.01로 고정했다. 띠 밖 1600 Hz 성분의 진폭만 0.0 → 0.1 → 1.0로 키우면 rms_keep_tipband_db는 -0.58 → +8.10 → +27.47 dB로 오른다. 접힌 띠는 200~600 Hz이며, 세 경우 모두 tipband_discriminates=true다. 현재의 좁은 띠 허용 조건도 통과한다. 입력의 관심 성분은 불변인데 출력 분자는 다른 성분까지 받아들인다.

**수정 권고:** 관심 띠와 그 밖을 입력에서 분리하고 같은 평균·표본화 연산을 각각 적용해 출력 기여를 나란히 낸다. 전체 혼합 신호에서 잰 값은 «접힌 띠의 총 RMS / 입력 관심 띠 RMS»로 정의한다. 이를 회전자 성분의 생존율로 단독 인용하는 문구를 고친다.

근거 원장: `outputs/current_review_0913.json` → `checks.numeric.offband_survival`

- [benchmark/read_wfsurvive_0912.py:221](../benchmark/read_wfsurvive_0912.py#L221) — `_ref_tb = bandpow(x, prf, lo0, hi0)          # 우리 격자의 날개끝 띠`
- [benchmark/read_wfsurvive_0912.py:222](../benchmark/read_wfsurvive_0912.py#L222) — `_post_tb = bandpow(y2, fr, lo, hi)           # 접힌 상 안`
- [benchmark/read_wfsurvive_0912.py:308](../benchmark/read_wfsurvive_0912.py#L308) — `"그쪽은 rms_keep_tipband_db(우리 격자의 날개끝 띠를 기준으로 한 것)를 본다.",`

### 4. 대역 판독 결과가 복소 반사율의 위상 평탄성을 다루지 않는다

**등급:** 설계 질문의 미해결 부분

실제 판독기 main을 임시 입력·출력으로 실행했다. 반송파 사이 위상을 1.1 rad씩, 전체 4.4 rad 범위로 바꿔도 출력 수치 변화는 0건이다. 레벨·변동 전력·스펙트럼 전력은 반송파별 상수 위상 회전에 불변이다. 현재 표가 재는 크기와 전력 구조의 변화는 유효하지만, 발주서가 요구한 «크기·위상 모두»에는 답하지 않는다.

**수정 권고:** 현 판독의 제목과 질문을 «대역 내 전력·변조 구조의 변화»로 맞춘다. 복소 평탄성은 알려진 전파 지연을 제거하고 같은 자세의 복소 응답을 비교하는 별도 항목으로 둔다. 성긴 반송파 표본 사이의 지연 모호성과 미관측 구간도 함께 기록한다.

근거 원장: `outputs/current_review_0913.json` → `checks.readers.band_runs`

- [runners/make_jobs_0929.py:35](../runners/make_jobs_0929.py#L35) — `· 네 점의 복소 반사율이 크기·위상 모두 좁은 폭 안에 모이면, 「이 대역에서 표적은`
- [benchmark/read_bandflat_0913.py:335](../benchmark/read_bandflat_0913.py#L335) — `p = float(np.mean(np.abs(E) ** 2))`
- [benchmark/read_bandflat_0913.py:180](../benchmark/read_bandflat_0913.py#L180) — `Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2`

### 5. 구조 문턱 미통과를 백색잡음과 구별 불가로 확정한다

**등급:** 새 확인 · 판정 문구 과잉

판정은 리듬 몫 초과와 빗살 대비의 고정 문턱을 AND로 묶는다. 잡음을 넣지 않은 501 Hz 단일 복소 정현파에서도 리듬 몫 15.38 %, 빈 수 비율 12.65 %, 빗살 대비 86.08 dB가 나오지만 관문은 false다. 이때 출력 문장은 «백색잡음 널과 구별되지 않는다»가 된다. 단일 선의 통계와 백색잡음의 동등성을 검정한 결과가 아니다. 실외 원장에 실제 백색잡음이 있다는 판정도 이 두 요약치만으로는 성립하지 않는다.

**수정 권고:** false 문장을 «설정한 두 구조 지표의 공동 문턱 미충족»으로 바꾼다. 두 지표를 개별적으로 보여주고, 잡음 모형과의 구별을 주장할 때는 명시한 널 분포·오류율·검정력을 별도 검사한다. 관문 미통과를 날개 신호의 부재로 해석하는 문장도 관찰 수준으로 고친다.

근거 원장: `outputs/current_review_0913.json` → `checks.numeric.structure_counterexample`

- [benchmark/read_bandflat_0913.py:515](../benchmark/read_bandflat_0913.py#L515) — `has = bool(over_null is not None and over_null > 5.0`
- [benchmark/read_bandflat_0913.py:535](../benchmark/read_bandflat_0913.py#L535) — `"움직이는 몫이 백색잡음 널과 구별되지 않는다 — ⛔이 줄의 대역 평탄성을 "`

### 6. 공통 입력 검증이 새 판독 경로에 전파되지 않았다

**등급:** 기존 미해결 + 새 경로 · 잠재 결함

파형·장면 두 판독기는 서로 다른 PRF의 샤드, 선택 후에도 값이 충돌하는 중복 세대, complex64 NaN을 각각 통과시켰다. one_generation의 진단을 버리고 전계·seen만 조립한다. 새 대역 판독기에 NaN을 넣으면 사유를 적고 거절하는 대신 TypeError: '<' not supported between instances of 'float' and 'NoneType'로 중단됐다. 대역 판독기의 빈 띠 분기는 반환값 2개인데 호출자는 3개를 받는다. 현재 검사한 안정된 샤드의 비정상 전계는 없으며, 이 항목은 합성 입력에서 확인한 실패 처리 결함이다.

**수정 권고:** 공통 로더가 E·N·PRF·idx·비유한 값과 세대 선택 진단을 함께 반환하게 한다. 미완 입력과 미해결 충돌은 사유와 함께 기록한다. 세대는 완전성을 우선하고 저장 진단은 현재 규칙과 구분하며, 빈 띠의 반환 형식도 호출부와 맞춘다.

근거 원장: `outputs/current_review_0913.json` → `checks.readers.reader_input_probes`

- [benchmark/read_wfsurvive_0912.py:112](../benchmark/read_wfsurvive_0912.py#L112) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_scenephysics_0913.py:95](../benchmark/read_scenephysics_0913.py#L95) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_bandflat_0913.py:176](../benchmark/read_bandflat_0913.py#L176) — `return None, None`

### 7. 파형 표의 조건 선택과 표시가 여전히 다른 팔들을 한 이름으로 묶는다

**등급:** 기존 미해결 · 발간 식별 문제

현재 292행에 음의 방위 태그 8행, 로터 변경 31행, PRF 변경 56행이 들어 있다. 이 집단은 서로 겹칠 수 있다. 표에 쓰는 장면·앙각·스위치 이름 조합 중 21개는 서로 다른 engine을 같은 이름으로 표시한다. 새 문법은 scene 이름에 적용됐지만 want의 옛 정규식과 표 라벨은 남아 있다. 원장에는 전체 engine이 있어 숫자 자체가 사라진 것은 아니다.

**수정 권고:** 연구 범위를 허용할 필드 목록으로 명시하고, 포함한 변화축은 표에 열로 표시한다. 전체 engine을 각 행의 근거로 연결하고 제외·미완 칸의 사유를 기록한다.

근거 원장: `outputs/current_review_0913.json` → `checks.numeric.waveform_scope`

- [benchmark/read_wfsurvive_0912.py:267](../benchmark/read_wfsurvive_0912.py#L267) — `and not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt|fc)[\d._]",`
- [benchmark/read_wfsurvive_0912.py:343](../benchmark/read_wfsurvive_0912.py#L343) — `lines.append(f"| {r['scene']} | {r['el_deg']:+g} | {r['arm']} | "`

### 8. 기존 감사 생성기가 현재 생산 의존성을 따라가지 못한다

**등급:** 기존 미해결 + 새 실행 오류

저장 중단 반례는 AssertionError: NameError로 중단된다. 추출한 저장 호출이 요구하는 bake_stamp를 시험 입력이 제공하지 않는다. 세대 재현 검사는 NameError: name '_prfs' is not defined로 중단된다. 새 _prfs 수집이 추출 병합 코드에 들어왔지만 시험 namespace에는 빠졌다. 이들은 생산 워커 장애의 증거가 아니라 감사의 재현성 결함이다.

**수정 권고:** 감사 어댑터에 생산 함수가 요구하는 의존성을 명시하고 추출 경계도 검사한다. 각 반례 결과를 성공·실패·실행 불가로 기록해 한 검사 실패가 나머지 검사의 저장을 막는 경로를 고친다. 기존 결함을 되돌린 변이 시험도 함께 확인한다.

근거 원장: `outputs/current_review_0913.json` → `checks.boundaries.old_audit_failure`

- [benchmark/review_repository_0911.py:208](../benchmark/review_repository_0911.py#L208) — `assert failure=='OSError',failure`
- [benchmark/review_repository_0911.py:133](../benchmark/review_repository_0911.py#L133) — `exec(compile(ast.Module(body=code,type_ignores=[]),'production merge block','exec'),ns)`
- [benchmark/elevation_sweep_md.py:1492](../benchmark/elevation_sweep_md.py#L1492) — `_prfs.add(float(_m4[4]))`

### 9. 선행연구 안내의 수집량과 재현율 분모가 현재 원장과 다르다

**등급:** 기존 미해결 · 안내 문면

로컬 소장 원장은 970행, 초록 802행이다. README의 수집량·닻 분모가 이 원장과 다르다. 현재 재현율은 DOI와 구간 조건으로 셀 수 있는 4개 중 4개이며, 전체 닻 목록의 수와 구분해야 한다. 이번에는 로컬 메타데이터와 닻 조회를 검산했고 논문 전체 본문을 재독하지 않았다.

**수정 권고:** 안내의 수집량과 재현율을 현재 원장 키에서 생성한다. 전체 닻 수와 확인 가능한 분모, 초록 읽기와 본문 읽기 범위를 각각 표시한다.

근거 원장: `outputs/current_review_0913.json` → `checks.readers.literature`

- [prior_work/README.md:66](../prior_work/README.md#L66) — `**학회 11 종**, 2025-01 이후 **275 편**(정본 123 · 일반 152)`
- [prior_work/README.md:74](../prior_work/README.md#L74) — `| 재현율(아는 6 편) | 3/6 | 3/6 | 4/6 | **4/6** |`

## 별도 주의: 이름 왕복 검사의 범위

현재 문법 검사에서는 원장과 창고의 이름이 통과했다. 다만 합성 이름 `sionna_p4000000000_swR0D0E0F1_r15_n8192_envnewcity_bldg`는 env=newcity, blade_law=dg로 나뉘고도 왕복 일치한다. 새 환경의 뜻까지 왕복 검사 하나로 보증하는 표현은 좁혀야 한다. 현재 알려진 환경에서 발생한 오류로 분류하지 않았다.

## 재현과 변경 범위

검증한 코드 인용 24개. 해시 확인 중 달라진 입력: [].
생산 코드·발간 원장·워커·큐는 수정하지 않았다. 이번 감사 생성기와 새 감사 JSON·Markdown·Jupyter 노트북을 작성했고 work에는 검사 캐시를 남겼다.

```bash
/workspace/.venvs/py312/bin/python benchmark/review_current_0913.py
```
