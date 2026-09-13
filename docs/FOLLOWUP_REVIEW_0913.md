# 후속 수정 재검증과 파생 비교 점검

점검 시작 커밋 `25fc2f4db5d4ec93fd6386450cf1af711977ffa4` → 최신 확인 `d32fcf44fe01095828297c55c0e576ac4a10bc84`.
완료 시각 2026-09-13T15:18:03Z. 조사 도중 변경된 대역 판독기는 최신 커밋에서도 main을 다시 실행했다.

## 기존 아홉 항목에 대한 판정

| 기존 항목 | 이번 확인 | 남은 범위 |
|---|---|---|
| 기체별 날개 통과율 | 주 집계 488행 중 445행 변경, 현재 함수 불일치 0 | 완전요인 보조 표로 전파 필요 |
| 대역 퍼짐 대조 | 최신판에서 되풀이 실행으로 변경 | 중심 주파수 반복 범위와 판 수 표시 보완 |
| 띠 생존 지표 | 안/밖 분리 열과 누출 한계 설명 확인 | 입력 마스크에 따른 분리 지표이며 성분 생존의 단독 증거가 아님 |
| 위상 해석 | 코드 머리글의 범위 정정 확인 | 독자용 제목·도입 보완 |
| 구조 문턱 해석 | 문서의 잡음 검정 단정 철회 확인 | 코드 머리글에 옛 단정 잔존 |
| 입력 검증 | 짧은 STFT helper 수정 확인 | raw loader와 main의 검증 누락 |
| 파형 행 선택·표시 | 실제 main 재실행 505행·건너뜀 866행, 수치 변화 0 | 이번 정상 입력 재현은 일치 |
| 감사 어댑터 | 세대 선택·raw merge 경로 재현 | 저장 중단 시험은 실행 준비 오류 |
| 선행연구 안내 | 현재 통계와 과거 통계 구분 확인 | 이번 범위에서 기존 지적을 반복하지 않음 |

## 재현된 수정과 숫자 차이의 해석

날개 통과율의 이전 감사 예측과 현재 주 집계가 다른 행은 0이다. 대표 ours_s1000plus_r15_n8192_az67.5 / el -45°는 scipy를 사용하지 않은 NumPy STFT로도 아래 값을 재현했다.

| 배음 창 반폭 Hz | 옛 통과율의 H1/H2 dB | 기체별 통과율의 H1/H2 dB |
|---|---|---|
| 6 | 13.05 | -4.81 |
| 12 | 13.35 | -4.81 |
| 18 | 46.43 | -4.81 |
| 30 | 41.96 | -4.81 |
| 45 | -3.92 | -4.81 |
| 60 | -3.92 | -4.81 |

이 창 변화 시험은 해당 대표 신호의 민감도 확인이다. 모든 신호에서 창 선택과 무관하다는 주장으로 확대하지 않는다.

파형 반례의 두 보고 숫자는 실험 조건이 달랐다. 같은 입력 조건으로 다시 계산하면 각각 다음과 같다.

| PRF Hz | 표본수 | 띠 밖 진폭 | 옛 합계 비율 dB | 새 from_inband dB |
|---|---|---|---|---|
| 20000 | 8000 | 0 | -0.58 | -0.58 |
| 20000 | 8000 | 0.1 | 8.10 | -0.58 |
| 20000 | 8000 | 1 | 27.47 | -0.58 |
| 19700 | 8192 | 0 | -0.59 | -0.59 |
| 19700 | 8192 | 0.1 | 7.45 | -0.61 |
| 19700 | 8192 | 1 | 24.26 | -1.24 |

공통 조건: 입력 관심 톤 400 Hz·진폭 0.01, 띠 밖 톤 1600 Hz, 출력 NR 프레임률 2000 Hz. 서로 다른 표집 조건의 숫자 차이를 수정 실패로 보거나 ‘동일 조건의 자릿수까지 독립 재현’이라고 쓰는 것은 피한다.

## 추가 보완점

### 1. 입력 검증이 새 판독기의 실제 실행 경로에 여전히 빠져 있다

**등급:** 우선 수정 · 임시 반례에서 발간 실패와 오염 재현

파형·장면 판독기 모두 표집률 불일치, 세대 선택 뒤 남은 전계 충돌, complex64 NaN 입력을 받아들였다. 최신 대역 main에 NaN을 넣으면 비유한 수 21개를 포함한 JSON을 먼저 저장한 다음 TypeError: '<' not supported between instances of 'float' and 'NoneType'로 중단한다. 기대 길이와 다른 짧은 입력도 exit 0, 건너뜀 0개로 통과하고 숫자 63개가 바뀐다. 현재 정상 자료가 오염됐다는 판정이 아니라, 임시 입력으로 재현한 오류 처리 결함이다.

**권고:** 모든 판독기가 같은 입력 관문을 사용하게 한다. 저장된 표본수·표집률·idx 완전성·유한성·세대 충돌 진단을 확인하고 거절 사유를 남긴다. 계산과 문서 생성이 모두 성공한 뒤 검증된 임시 산출물로 교체한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.reader_inputs / checks.latest_repeat.band_main_runs`

- [benchmark/read_wfsurvive_0912.py:112](../benchmark/read_wfsurvive_0912.py#L112) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_scenephysics_0913.py:95](../benchmark/read_scenephysics_0913.py#L95) — `fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")`
- [benchmark/read_bandflat_0913.py:725](../benchmark/read_bandflat_0913.py#L725) — `json.dump(out, open(OUT_J, "w"), ensure_ascii=False, indent=1)`

### 2. 완전요인 분석의 보조 표에 기본 기체 날개 통과율이 남아 있다

**등급:** 발간 수치에 영향 · 새로 확인

other_drone_switch_arms와 reference_arms의 210행을 현재 함수로 재계산한 발간값 불일치는 0행이다. 그 함수에 기체별 날개 통과율을 넣으면 210행의 한 개 이상 열이 달라진다. 영역별 행 수는 {'other_drone_switch_arms': 180, 'reference_arms': 30}이다. ours_mini5pro_r15_n8192_mfixbatteryi5_blperairframe/el-30: 리듬 몫 4.14 → 86.97% / ours_mavic4pro_r15_n8192_mfixbatteryi5_blperairframe/el-30: 리듬 몫 10.77 → 87.41%. 이 범위는 다른 기체 보조 표이며 기본 기체의 완전요인 전체가 바뀐다는 뜻은 아니다.

**권고:** 행별 기체에서 날개 통과율을 구해 columns와 rhythm_share_ref에 전달하고, 사용한 값을 행에 기록한다. 영향받는 보조 표와 파생 설명을 다시 생성한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.factorial.other_drone`

- [benchmark/switch_factorial.py:234](../benchmark/switch_factorial.py#L234) — `PRF, FFL = float(M["prf_hz"]), float(M["f_flash_hz"])`
- [benchmark/switch_factorial.py:285](../benchmark/switch_factorial.py#L285) — `col = columns(Z[key_np], prf_cell, FFL, ft)`
- [benchmark/switch_factorial.py:291](../benchmark/switch_factorial.py#L291) — `col["rhythm_share_ref_pct"] = rhythm_share_ref(Z[key_np], prf_cell, FFL, ft)`

### 3. 메쉬가 다른 비교가 주판정용 회절 비교에도 들어간다

**등급:** 발간 비교의 해석에 영향 · 범위 추가 확인

axis_diffs 145쌍 중 30쌍은 mesh_fix 또는 blade_law가 다르다. 주판정용 el −30° 회절 비교 6쌍 중에도 2쌍이 들어간다. 조합별 대표 행 선택이 명시적이어도 on/off 쌍이 같은 메쉬가 되는 것은 보장되지 않는다.

**권고:** 변경하려는 스위치 외의 조건이 같은 쌍만 주판정에 사용한다. 짝이 없는 조건은 비교 보류와 이유를 기록하고, 기존 혼합 쌍은 조건 차이를 표시한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.factorial.axis_pairs`

- [benchmark/switch_factorial.py:394](../benchmark/switch_factorial.py#L394) — `o, n = c, cells[k1]`
- [benchmark/switch_factorial.py:452](../benchmark/switch_factorial.py#L452) — `a_cover = bool(dpairs and all(r.get("contains_unit_within_3sigma") for r in dpairs))`

### 4. 계수 1 포함 판정이 복소 위상을 버리고 불확도 가정을 확정적으로 쓴다

**등급:** 계산·해석 결함 · 실제 비교와 반례로 재현

생산식은 bool(sig > 0 and abs(abs(a) - 1.0) <= 3 * sig)이다. 실제 R0D0E0F1_d1/el-30 → R0D1E0F1_d1/el-30에서 |a|=0.921291, 위상 -73.45153°인데 통과한다. 합성 동일 신호의 판정은 False, 위상 90°와 180° 회전 신호는 각각 True, True다. 같은 시간 구간의 같은 연속 함수를 표본화한 반례에서도 N=[64, 256, 1024, 8192]에 따라 판정은 [True, True, False, False]로 바뀐다. 코드가 밝힌 무상관 가정은 이 결정적 자세열에 대해 검증된 불확도 모형이 아니다.

**권고:** 복소 계수의 크기와 위상을 따로 보여주고 계수 1과의 복소 거리를 검사한다. 동일 신호·잔차 영의 경계도 처리한다. 현재 sigma를 그대로 신뢰구간으로 재사용하지 말고, 시간 의존성과 실제 반복 설계에 맞는 불확도 근거를 먼저 마련한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.factorial.containment / checks.factorial.axis_pairs.phase_false_accepts`

- [benchmark/switch_factorial.py:414](../benchmark/switch_factorial.py#L414) — `sig = float(np.linalg.norm(res) / (np.linalg.norm(e0) * np.sqrt(e0.size)))`
- [benchmark/switch_factorial.py:421](../benchmark/switch_factorial.py#L421) — `contains_unit_within_3sigma=bool(sig > 0 and abs(abs(a) - 1.0) <= 3 * sig),`

### 5. 보류 판정과 계수·위상 확정 설명이 같은 발간물에 공존한다

**등급:** 현재 발간 문면에 영향

현재 A_cover_pass=False인데 A_cover_why_ko는 계수 1·위상 약 0°로 그대로 품는다고 단정한다. headline에도 판정 보류와 얹는 축이라는 단정이 공존한다. 앞의 혼합 메쉬·복소 계수 문제를 고치기 전에도 이 조건 없는 설명은 현재 판정값과 모순된다. 실제 headline 원문은 연결 원장에 보존했다.

**권고:** 설명과 제목을 판정 상태에 따라 생성한다. 보류·실패·입력 부적격 각각의 이유를 쓰고, 잔차 분해나 높은 상관만으로 물리적 원인을 단정하지 않는다.

근거 원장: `outputs/followup_review_0913.json` → `checks.factorial.verdict / checks.factorial.headline`

- [benchmark/switch_factorial.py:672](../benchmark/switch_factorial.py#L672) — `A_cover_why_ko="회절을 켠 시계열은 끈 시계열을 **계수 1 (3σ 안) · 위상 ≈0°** 로 그대로 "`

### 6. 직하방에서 존재하지 않는 날개끝 띠의 봉우리 값이 발간된다

**등급:** 발간 열 정의와 값 불일치 · 새로 확인

has_tipband=false인 20행 모두에 띠 내부 봉우리 값이 남아 있다. 예: sionna_p4000000000_swR0D0E0F1_r15_n8192_mfixbatteryi5_blperairframe_d2 / el -90°, f_tip=0 Hz인데 기준 띠 봉우리는 127.453613 Hz다. 경계가 None이면 peak가 전체 스펙트럼을 탐색하는 것이 원인이다. ‘띠 값이 전부 null’이라는 메타 설명과도 어긋난다.

**권고:** 띠가 없는 경우 띠 전용 peak 열을 명시적으로 null로 둔다. 전체 스펙트럼 봉우리를 유지하려면 기존 전체 봉우리 열로 분리해 표시한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.nadir_band`

- [benchmark/read_wfsurvive_0912.py:160](../benchmark/read_wfsurvive_0912.py#L160) — `def peak(v, fs_, lo=None, hi=None):`
- [benchmark/read_wfsurvive_0912.py:196](../benchmark/read_wfsurvive_0912.py#L196) — `ref_peak_hz=peak(x, prf), ref_peak_in_tipband_hz=peak(x, prf, lo0, hi0),`
- [benchmark/read_wfsurvive_0912.py:408](../benchmark/read_wfsurvive_0912.py#L408) — `"⛔f_tip 이 0 인 칸(직하방)은 띠가 없다 — has_tipband=false 이고 띠 값이 전부 null 이다.",`

### 7. 아틀라스 안내 노트북뿐 아니라 자체 검사식도 낡았다

**등급:** 문면과 검사 오경보 · 새 원인 확인

기존 안내의 검사 문장: | ⭐원장이 **스스로 잰** 박자(`track.beat_hz`)가 우리가 세운 예측 박자의 정수배 ±3 % 안에 든다 — 색인과 무관한 독립 증거 | ❌ | 맞음 1014 칸 · 어긋남 260 칸 (가장 먼 칸 sionna_p4000000000_swR1D1E1F1_r15_n8192_prf78800_mfixbatteryi5_blperairframe_d2@-60 63.34 Hz = 0.50x) |. 현재 같은 검사 결과: 맞음 1671 칸 · 어긋남 583 칸 (가장 먼 칸 sionna_p4000000000_swR0D1E1F1_r120_n8192_az0.017_mfixbatteryi5_blperairframe_d2@+0 63.33 Hz = 0.50x). 날개끝 도플러 검사에서 지적한 72팔은 전역 반송파를 쓰고 프로펠러 배율을 빠뜨린 검사식 때문이다. 행별 반송파와 프로펠러 배율을 적용하면 72팔 모두 현재 색인과 맞는다. 기본 기체를 이름에 명시한 팔의 박자가 기본값과 다르다고 요구하는 별도 검사도 수정 대상이다.

**권고:** 행별 반송파·프로펠러 배율·기체를 반영하도록 검사기를 먼저 고친 뒤 안내 노트북을 재생성한다. 이번에 재계산과 일치한 색인 값은 유지한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.toc`

- [benchmark/build_atlas_toc.py:451](../benchmark/build_atlas_toc.py#L451) — `fc = float(META["fc_hz"])`
- [benchmark/build_atlas_toc.py:459](../benchmark/build_atlas_toc.py#L459) — `tip0 = 2.0 * (2 * math.pi * f_rev * (s.prop_dia_mm / 2000.0)) / (C_LIGHT / fc)`

### 8. 저장 중단 시험의 생산 의존성 누락이 남았다

**등급:** 감사 재현 경로 결함

현재 review_repository_0911.save_interruption() 재실행은 AssertionError: NameError로 끝난다. 추출한 생산 저장 코드가 bake_stamp를 호출하지만 시험의 실행 namespace에 해당 의존성이 없다. raw_merge 어댑터를 고친 것과 별개의 경로다. 실제 워커의 저장 실패로 분류하지 않는다.

**권고:** 시험에 현재 생산 의존성을 명시적으로 제공하고, 의도한 저장 예외와 시험 자체의 준비 오류를 구분한다. 실행 준비 오류는 검증 보류로 집계한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.boundaries.old_audit_failure`

- [benchmark/review_repository_0911.py:233](../benchmark/review_repository_0911.py#L233) — `assert failure=='OSError',failure`

### 9. 현재 생성기와 JSON에 옛 중복 선택의 잘못된 이력이 남아 있다

**등급:** 현재 발간 이력 설명 오류

옛 마지막 행 우선 선택을 재현한 28칸에서 현재와 팔이 다른 칸 0, AC가 다른 칸 0이다. 따라서 사용자가 전달한 정정은 맞는다. 그러나 현재 _meta.collisions_ko는 여전히 ‘먼저 온 것’이 정본 메쉬를 버렸다고 적는다. 원문: 칸 열쇠 `{조합}_d{깊이}/el{앙각}` 이 팔을 안 담는다. 같은 열쇠를 내는 팔이 여럿이면 **정본 메쉬 → 물리모드 아님 → 이름순**으로 골라 하나만 표에 서고 나머지는 collisions 에 적힌다. ⛔옛 판은 조용히 덮었고, 그 규칙(먼저 온 것)은 28 건 전부에서 정본 메쉬 팔을 버렸다(차 최대 12.65 dB).

**권고:** 생성기와 JSON의 이력 설명을 ‘값의 정정이 아니라 선택 규칙의 명시화’로 고친다. 되돌린 중간 구현과 그 이전 발간 구현의 이력을 구분한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.factorial.old_selection`

- [benchmark/switch_factorial.py:752](../benchmark/switch_factorial.py#L752) — `"⛔옛 판은 조용히 덮었고, 그 규칙(먼저 온 것)은 28 건 전부에서 "`

### 10. 최신 되풀이 대조의 주파수 범위와 판 수·정밀도를 명시해야 한다

**등급:** 최신 변경의 해석 범위 보완

d32fcf44에서 짝·홀을 판정 대조로 쓰던 코드는 제거됐다. 같은 조건 되풀이가 있는 주파수는 각 그룹의 [3500] MHz뿐이다. 표의 판 수 [10, 12, 8, 8]에는 각기 다른 주파수의 단독 실행이 섞여 있고, 실제 반복 그룹의 판 수는 [6, 8, 4, 4]이다. 반올림 전 AC 퍼짐은 [2.7551547589155234e-05, 2.070023043643232e-06, 2.968315016005363e-08, 5.302323557998534e-07] dB로, 표시된 영은 정확한 영이 아니다. 현재 관측 대역 퍼짐이 이 중심 주파수 되풀이 퍼짐보다 크다는 수치 비교는 재현되지만 전 대역의 격자 민감도나 물리적 정확도의 검증으로 확장할 수 없다.

**권고:** 반복이 있는 주파수, 그 조건의 반복 수, 다른 주파수의 단독 실행 수를 나누어 적는다. 재현성은 원정밀도로 저장하고 작은 값은 과학적 표기로 표시한다. 중심 주파수 반복과 대역 전체 수렴성의 범위를 구분한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.latest_repeat.groups`

- [benchmark/read_bandflat_0913.py:524](../benchmark/read_bandflat_0913.py#L524) — `rep_n = sum(x[1] for x in _rs)`
- [benchmark/read_bandflat_0913.py:575](../benchmark/read_bandflat_0913.py#L575) — `(f"되풀이 재현성 {rep_spread:.3f} dB 보다 크다"`

### 11. 위상·백색잡음 설명이 문서와 코드 머리글에서 서로 다르다

**등급:** 문면 정정 부분 완료

생성 문서는 구조 문턱이 잡음 모형 검정이 아니라는 제한을 추가했다. 반면 코드 머리글에는 실외 값은 백색잡음 널과 구별되지 않는다는 문장과 날개가 아니라는 단정이 남아 있다. 위상을 다루지 않는다는 제한은 코드 머리글에는 있지만 발간 문서 제목·도입의 평탄성 질문에는 충분히 드러나지 않는다. 반송파마다 상수 위상을 회전시킨 최신 main 시험에서도 수치가 그대로다.

**권고:** 정정된 해석 하나로 코드 머리글·문서 제목·소개·자동 설명을 맞춘다. 크기와 변조구조에 대한 관측이며 위상 평탄성은 별도 분석임을 독자용 문서에도 명시한다.

근거 원장: `outputs/followup_review_0913.json` → `checks.latest_repeat.band_main_runs`

- [benchmark/read_bandflat_0913.py:81](../benchmark/read_bandflat_0913.py#L81) — `실외 값은 **백색잡음 널과 구별되지 않는다.** 게다가 그 바닥은 정지 성분의 −20.4 dB(el −30)`
- [benchmark/read_bandflat_0913.py:6](../benchmark/read_bandflat_0913.py#L6) — `평평한가」로 적었는데 **이 판독기는 위상을 못 본다.** 여기 지표는 전부 |E| 나`
- [docs/BANDFLAT_0913.md:32](../docs/BANDFLAT_0913.md#L32) — `⛔이 관문을 통과 못 한 줄의 대역 수는 **표적 이야기가 아니다.** ⛔그렇다고 «백색잡음이다» 로도 읽지 않는다 — 두 문턱은 우리가 정한 값이고 잡음 모형과의 검정이 아니다. 반례: 잡음을 하나도 안 섞은 **501 Hz 단일 정현파**가 리듬 몫 15.38 %(널 12.65 %, 초과 2.73 %p) · 빗살 대비 **86.08 dB** 인데 AND 라서 관문은 미통과다.`

## 대조군 논의에서 더 정확히 표현할 점

진폭을 공통 배율로 바꿔도 짝·홀 dB 차이가 유지된다는 사실만으로 대조군이 부적절하거나 계통 오차라고 증명되지는 않는다. 전력비 10 log10(c²P짝 / c²P홀)에서는 공통 배율이 정의상 소거된다. 질문에 대응하는 차이와 그 불확도를 비교해야 한다.
실외 el -30°의 짝·홀 절대 레벨 차이가 크더라도, 각 집합을 중심 주파수에 맞춰 비교하면 주파수 변화 대비의 최대 차이는 0.00325364 dB다. 짝수만·홀수만으로 잰 대역 퍼짐은 각각 0.235944, 0.234217 dB다. 이 관측은 옛 ‘대역 변화가 절대 짝·홀 차이에 묻힌다’의 비교가 부적절했음을 구체화한다. 새 신뢰구간이나 물리적 원인의 확정은 아니다. 최신 커밋은 이미 그 판정 대조를 제거했다.

## 검사 범위와 재현

이전 전수 감사의 샤드 목록을 이어받았다. 현재 안정된 샤드 7647개 중 새로 생기거나 mtime이 바뀐 5개를 전체 배열 검사했고 오류 0개, 읽는 중 변경 0개였다. 그대로인 샤드를 전부 재검사한 것으로 집계하지 않는다. GPU·솔버 실행과 아틀라스 전체 그림 재렌더링은 이번 범위에 포함하지 않았다.
최신 freeze 검사 exit 0. 최초 freeze 차이는 작업 중 늘어난 창고 샤드 수였으며, 이후 생산측 기준선 갱신 후 통과했다. 기준선 통과는 여기서 재현한 계산·입력 결함을 반증하지 않는다. 이름·의미·각주 등의 검사 원문은 checks.gates에 저장했다. 기존 규약 검사 누적 부채와 링크 경고까지 없다는 뜻으로 ‘관문 통과’를 쓰지 않는다.
인용 23개를 줄·문자 대조했다. 저장한 입력 해시와 종료 시점이 다른 파일: []. 변경된 커밋의 초기 해시는 checks.snapshot_transition에 따로 보존했다.
생산 코드·발간 원장·워커·큐는 수정하지 않았다. 이번 감사 생성기와 감사 JSON·Markdown·Jupyter 노트북, work 캐시만 작성했다. 저장소에 추가된 최신 생산 커밋은 다른 작업자의 변경이다.

```bash
/workspace/.venvs/py312/bin/python benchmark/review_followup_0913.py
```

기존 캐시로 보고서만 다시 만들려면 같은 명령에 `--publish`를 붙인다. 보고서 생성은 생산 산출물을 갱신하지 않는다.
