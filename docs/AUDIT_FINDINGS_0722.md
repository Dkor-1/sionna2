# 리포트 1~12 적대감사 findings (2026-07-22, wf w4gurtd2o)

12에이전트 적대감사. report07은 스키마 실패로 미감사(이번 세션에 이미 대폭 수정됨). **18개 high/med** — 적용 대기.

## 🔴 HIGH (반드시 수정)
- **report01** `make_notebook01.py:116,188,214,239,292` [overclaim] — "벽·천장 흡수·바닥만 유일 반사" 척추 서사가 자기 RT 데이터와 모순: 천장 흡수체 −9.82dB > 바닥 −14.68dB, absorber_front 2bounce −11.63dB가 같은 지연빈서 3dB 강함. **실제 통제는 물리적 단일반사 아니라 ECA 정적클러터 제거(report09).** 서사 정정.
- **report12** `make_notebook12.py:276` [stale] — 방위평균 σ "−19.7 dBsm" 하드코딩=구엔진값. report2_waveform_rcs.json 현행 −18.4(밴드3.5) or 밴드평균 −17.1로 갱신(JSON 동적주입 권장).
- **report12** `make_notebook12.py:412` [contradiction] — M['sigma_dbsm']=−28.0(이 자세=널)을 "밝은 상단"에 대입=포락선 최하단인데 상단이라 모순. "밝은 상단"엔 방위평균(−17.1/−18.4) 쓰고, 자세값(−28)은 "이 자세는 널=하단"으로 분리.

## 🟠 MEDIUM
- **report01** `:315-325` [overclaim] — 세기 0.0005dB 일치=항등식(같은 프레넬)이라 독립검증 아님 → "일관성 확인"으로 격하, 진짜 독립증거는 지연(기하).
- **report01** `:209,309` [physics] — Γ≈0.26은 TM전용, TE는 0.52(수직입사 0.39보다 큼) → 편파조건 명시.
- **report02** `:247-248` [contradiction] — "광선 맨앞서 멈춤" 정당화가 penetrate=True(셸투과)와 모순 → "불투명면만 멈추고 반투명셸 투과, 면기반 적분이라 부피중복 없음"으로 재서술. + F_overlap 0.6~35%→0.66~37.4%(상한).
- **report03** `:74,139` [overclaim] — "네 기체 ±1dB 이내"가 Phantom4 −1.25로 자기위반 → "약 ±1dB"로 헤지. + :356 "보수적" 제거(밝은상단과 상충).
- **report05** `:77-79,158,385` [overclaim] — "규격 일치" 과대(교차검증은 우리OFDM↔SionnaOFDM 정합만, 규격정확성 아님) → "OFDM 변조수학·뉴머롤로지 정합"으로 축소(§3 caveats와 통일).
- **report06** `make_notebook06.py:85-92,404-416` [stale] — 재질별 σ분해가 구엔진(report3_rt.json 07-14)=금속<전체, report08 신엔진=금속>전체로 **부호 뒤집힘**. C_metal 분해를 report2_waveform_rcs.json materials 블록에서 재주입.
- **report08** `:280` [physics] — 7.1dB를 "십배"라 함(=5.1배). "약 5배"로 정정.
- **report08** `:285 vs 529` [contradiction] — §2 "광학영역·파장둔감" vs §6 "few-λ 공진영역·저주파12dB하강" 모순 → §2를 "측정 좁은대역서 스윙 3.2dB 작음"으로 한정.
- **report08** `:529` [overclaim] — 외삽 진값 −25~−28 vs 우리 −18 격차(7~11dB)를 "수 dB 낙관적"으로 축소 → "최대 ~7~10dB"로.
- **report09** `:268` [overclaim] — 기준클러터 −26dB를 "보수적으로 낮춤"이라나 실은 RT실측(−14.7)보다 11~16dB 과소 → "과소평가지만 +40dB 스윕이 실측 덮어 결론 무관"으로.
- **report09** `:217-220` [overclaim] — "지연·세기 눈금까지 겹침" 단정이나 같은 19.3ns에 탭 2개(−11.6,−14.7); 닫힌형은 −14.7과만 일치, −11.6 미규명 → 명시.
- **report10** `:150,186,302,495` [stale] — "파형당 8,000장"이 실제 10,000 → 4곳 교정(C['meta']['n_maps_chain'] 동적).
- **report11** `:416-448` [stale] — §3/§4 σ·SCR·Pd 전량 구엔진(9f26cee 이전) 스냅샷 → 재생성 or caveat.
- **report11** `:405-407,20x` [overclaim] — "pyAPRiL 3/3 모드 검출→검증된 체인"이나 detected_at_truth=false(CFAR 표적셀 미발화) → "CAF 봉우리 거리빈만 정답일치, CFAR 검출선언 아님"으로.
- **report12** `:196` [contradiction] — "SSB 20ms→무모호 1m/s"인데 "표적 느려서 어느 PRF서도 안 접힘" 자기모순(표적 3m/s>1) → "이 실험의 높은 PRF서는"으로 한정, 실 SSB선 접혀 G1 더 불리(헤드라인 강화).

## 적용 분류
- **narrative-only(재실행 불필요)**: r01·r02(서술)·r03·r05·r08·r09·r10·r11(overclaim)·r12 — 대부분 여기.
- **재실행 필요(stale σ)**: r06(재질σ 재주입)·r11(σ/SCR/Pd 재생성)·r12(σ라벨) + sbr_field 미관측(이미 코드반영) → **ONE 배치 재실행**.
- **mesh fix**: mini5 높이(별건).
