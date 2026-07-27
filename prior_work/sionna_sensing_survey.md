# Sionna-for-Sensing 선행연구 서베이 (자율 누적)

> 목적: **NVIDIA Sionna(RT 또는 PHY)를 센싱 태스크에 쓴 논문**을 계속 모아 우리
> 패시브 바이스태틱 드론탐지의 선행연구 후보로 삼는다. 6시간+ 자율 반복(cron)으로 누적한다.
>
> 대상 센싱 태스크: ISAC(joint comm-sensing) · 레이더/RCS · 패시브 센싱 · CSI/WiFi 센싱 ·
> 측위/로컬라이제이션 · 디지털트윈 센싱 · RIS 센싱 · UAV/드론 센싱 · 채널기반 감지.
> 각 논문마다 특히 **RCS/표적 산란 공백을 어떻게 다뤘는지**(A1 외부EM · A2 Sionna확장 ·
> B 외부통계 · C 메쉬반사우회 · D 미보고 — pw04 분류와 정합)를 기록한다.
>
> **진행 카운터**: rounds=19 · papers=16(직접 Sionna 실사용) + 맥락 13편 + **덱 v6 대조 추가 2편**(Great-X=Sionna RT 재구현·LAMBDA=Sionna 미확인) · last_updated=2026-07-20 · **탐색 100% 소진(5연속 dry)→종합 섹션 완비**
>
> **🔴 정정(2026-07-20, 원문 전문검증):** Ziganshin(arXiv:2604.05991)은 서베이가 '커스텀 UTD·비-Sionna'로 **오분류**했으나, 원문에 *"Sionna-RT (v0.19) was used as a basic RT framework"* + code(AinurZiga/sionna-RT-reflectivity) — 실제로 **Sionna-RT 확장(A2)**. 즉 **우리와 가장 가까운 선행연구**(둘 다 Sionna-RT+커스텀 산란; 차이=SBR+PO vs UTD·소형드론 vs 대형표적). 27편 전문 정독 워크플로 진행 중 — 완료 시 전체 재분류·deep_read_notes 반영.
>
> **📖 전문검증 정정본:** 이 서베이 분류는 초록 기반 초안. **27편 원문 전문 정독 정정본 → `/data/public/sionna_jeong/papers_isac_sionna/deep_read_notes.md`** (아카이브) (8건 정정). 핵심: **Ziganshin=Sionna-RT 확장(A2)**, **LAMBDA=Sionna RT 확정(미확인 아님, 표적 A1)**, **CellSense=Sionna RT(‘PHY 링크레벨’ 아님, 표적 C)**, 무표적 논문 RCS라벨 D→NA 정밀화(BostonTwin·S-ICDF·Saribekyan·Kang).
>
> **📌 덱(teammeeting_0721) 대조 보정**: 팀미팅 덱 선행연구 표가 서베이보다 UAV 논문 2편을 더 잡고 있어 정식 추가(아래 '덱 대조 추가' 절). 둘 다 실재 확인. Great-X 는 Sionna RT 를 Unreal 에 재구현(직접 사용 아님), LAMBDA 는 Sionna 사용·EM 툴(덱의 CADFEKO 주장) 초록 미확인.
>
> **🎯 Novelty 확인(R14)**: "Sionna + SBR/PO 로 **드론 표적 RCS**를 계산해 패시브 바이스태틱 탐지"를 한 **출판물은 발견되지 않음**.
> 드론 RCS 는 전부 딴 EM 툴(MLFMA-PO 하이브리드·WIPL-D·무향실 측정·NATO STO UHF 바이스태틱 모델)로,
> Sionna-센싱 15편은 표적 RCS 를 Sionna 로 안 냄. → **우리 조합(Sionna PHY 링크레벨 + 커스텀 SBR+PO 표적 RCS +
> 5종 드론 + 패시브 바이스태틱)은 문헌상 미점유 니치**로 보인다(14라운드 근거). ⚠계속 탐색해 반증 시 갱신.
>
> **📉 포화 신호(R10)**: R5·R8·R9·R10 의 genuine Sionna 신규 수확이 0~1편으로 급감. Sionna 로 **센싱**을 한
> 주요 공개연구는 대체로 R1~R8 에서 포착됨(공식 Made-with-Sionna 센싱 항목 전부 커버). 남은 각도는 대부분
> (a) Sionna 를 전파/채널모델에만 쓰고 센싱은 딴 툴, (b) 센싱 태스크지만 비-Sionna(커스텀 RT·실측·해석) 로 갈림.
>
> **⭐ Sionna 2.x 능력 점검(R9, 우리 핵심주장 검증)**: Sionna 2.0.1 문서·기술보고서(arXiv:2504.21719) 확인 결과 —
> PathSolver 는 image method + **SBR(shooting-and-bouncing-rays)** 로 다중경로를 열거하고, 상호작용마다
> **정반사·확산반사(diffuse scattering, S 계수)·1차 회절·(2.x 신규)굴절** 계수를 적용한다. 그러나 **표적을 향한
> PO 표면산란적분(coherent RCS)·native RCS 계산 API 는 여전히 없다**. 즉 "Sionna 기본 solver 에 산란적분 없음,
> RCS 는 외부 경로 필요"라는 우리 report06/07 주장은 **Sionna 2.x 에서도 정확**하다(SBR 은 경로탐색용이지 RCS 적분 아님).
> ⚠주의: "RT 가 RCS 못 낸다"가 아니라 "**Sionna 기본 PathSolver 에 PO 표면적분이 없다**"가 정확한 표현([[sionna2-rt-rcs-claim-scope]]).
>
> **⭐ (R13 보강) Sionna 는 확장을 설계로 지원**: Sionna RT 문서는 (i) **Custom Scattering Patterns API**(확산산란 각분포 함수를 등록·미분가능하게)와 (ii) 하부 **Mitsuba 광선엔진 노출**(그 위에 자작 solver 를 얹음). ⚠2026-07-21 실측 정정: `ScatteringPattern`/`RadioMaterialBase` 는 추상베이스라 **커스텀 산란패턴·재질이 공식 확장점**이 맞으나, **`PathSolver` 는 subclass 확장점이 아니다**(MRO=[PathSolver,object]) — 정확히는 Mitsuba 광선엔진 위에 직접 짠다(우리 rcs_sbr.py). 즉 **RCS/표적 산란은 Sionna 가 사용자에게 얹으라고 열어둔 A2 경로**이고 우리 SBR+PO 가 그 확장이다. 정직 프레이밍: *"Sionna 기본 solver 는 코히런트 PO/RCS 를 안 낸다(확산산란 S 계수·SBR 경로탐색만). 재질/산란패턴 확장점은 공식 제공하며, 우리는 광선엔진 위에 PO 를 얹었다."*
>
> ⭐**개발사 공식 확인 (GitHub Discussion #844, report06 핵심 인용):** 사용자가 "Sionna RT 로 금속체를 대량 광선 샘플링해 RCS 를 낼 수 있나" 묻자 메인테이너 **Jakob Hoydis 가 "This is currently not supported" 라고 답**했다 — 상세 mesh 표적 RCS 가 Sionna RT **기본 기능이 아니며 커스텀 구현이 필요**함을 NVIDIA 가 직접 확인. 2026-07-21 타깃 검색(별도 에이전트): **등재(비-arXiv) 논문 중 Sionna-내-mesh-표적-RCS 계산은 발견 못 함**(mesh 환경은 흔하나 표적 RCS 는 3GPP/실측/해석모델 주입이 표준). 감시대상 1건=Ziganshin(2604.05991, IEEE OJAP 심사정황·차량·UTD). ⚠Sagitta(2604.09243)는 실은 **Sionna 미사용** 독립 BVH SBR 로 재확인(과거 표기 정정).
>
> 규칙: 사이클마다 (1) 이 파일에서 이미 커버된 각도/논문 확인 → (2) 아직 안 본 각도/venue 로
> 새 논문 검색 → (3) 중복 제거 → (4) 아래에 항목 추가 · 카운터 갱신. URL 은 실재만.

---

## 커버된 검색 각도 (중복 방지 체크리스트)
<!-- 사이클마다 새로 훑은 각도를 여기에 append: 예) [2026-xx] IEEE JSAC ISAC + Sionna -->
- **[R1] Sionna ISAC / radar·RCS / monostatic OFDM range-Doppler** — arXiv eess.SP 2025~2026 상당수 소진; "Sionna UAV 저고도 센싱", "Sionna 패시브 바이스태틱/마이크로도플러", "Sionna DoA 데이터셋", "Sionna WiFi-CSI 인간센싱", "Sionna RCS 확장/PathSolver 산란적분", 공식 "Made with Sionna" 페이지(센싱계열 3개: CISSIR·BostonTwin·"Learning radio environments") 확인.
- **[R1] 미커버(다음 라운드 후보)**: IEEE Xplore 본문(ICASSP/GLOBECOM/ICC/WCNC/VTC/EuCAP/RadarConf 프로시딩 — 유료본문 미접근), Sionna **측위/포지셔닝** 전용 테마(BostonTwin·Geo2SigMap·"Learning radio environments"), **채널차팅/핑거프린팅**, **차량/자동차 ISAC+Sionna**, 비영어·학위논문, Sionna RT 테크리포트(arXiv:2504.21719)/1.x 문서가 네이티브 RCS·scattering primitive 를 노출하는지 타깃 조사.
- **[R2] Sionna 측위/로컬라이제이션 + 디지털트윈 + sim-to-real 핑거프린팅** — "Sionna RT 로컬라이제이션 뉴럴넷", "Sionna 디지털트윈 CSI 핑거프린팅", "Sionna sim-to-real RF positioning" 검색. 핵심 소견: **측위류는 표적이 능동 송신원(측위 대상)이라 후방산란 RCS 개념 자체가 없다**(우리 패시브 백스캐터 탐지와 다른 문제). Sionna 는 합성 핑거프린트/RSSI 생성·sim-to-real 격차 연구에 폭넓게 쓰임.
- **[R2] 미커버(다음 라운드 후보)**: 채널차팅/뉴럴레이트레이싱(F4-CKM·GSpaRC·radiance field), RIS/IRS 센싱+Sionna, 인간활동·제스처 WiFi 센싱, 차량 ISAC, 6G ISAC 표준화(3GPP TR 38.901 확장), Sionna SYS 시스템레벨 센싱, EuRAD/RadarConf 실측.
- **[R3] RIS/IRS 센싱 + Sionna** — **정직 소견: 자격 있는 Sionna-센싱 RIS 논문 0**. (a) Sionna+RIS 논문은 대부분 **커버리지 최적화**(센싱 아님) — 예 "RIS Optimization Algorithms for Urban Wireless Scenarios in Sionna RT"(Güneşer 외, VTC2025-Spring, arXiv:2501.05817)는 Sionna RT 확정이나 태스크가 RIS 커버리지맵이라 제외. (b) RIS+레이더센싱 논문은 대부분 **해석적**(비-Sionna) — Buzzi 2021(arXiv:2104.00768)·Colone 2026 저-RCS(아래 맥락).
- **[R3b] 인간활동·제스처 WiFi 센싱 + 채널차팅** — 제스처 ISAC(Zhang 외, arXiv:2507.06588)는 **실측 기반=비-Sionna**로 제외. 채널차팅에서 **MOCSID**(Sionna RT 생성 CSI) 발견 → 아래 등재.
- **[R3] 미커버(다음 라운드 후보)**: 3D 라디오맵/뉴럴레이트레이싱(Gaussian splatting RF·radiance field), Sionna SYS 시스템레벨, 차량/V2X ISAC+Sionna, 6G ISAC 표준화(3GPP TR 38.901 산란 확장), 위성/NTN 센싱, EuRAD/RadarConf 실측 vs Sionna 대조, Sionna 로 **드론 마이크로도플러** 특정 검색.
- **[R4] 차량/V2X ISAC + Sionna** — **자격 있는 Sionna-표적센싱 논문 0**. Sionna+차량은 디지털네트워크트윈(ns-3 연동, arXiv:2501.00372)=통신이지 센싱 아님. 곡면체 산란 ISAC 논문(arXiv:2604.05991)은 **커스텀 UTD**(비-Sionna) → 맥락 등재.
- **[R4b] 뉴럴 레이트레이싱/Gaussian splatting RF + 미분가능 RT 재질추정** — Gaussian-RT(arXiv:2605.07781)는 전파+뷰합성(센싱 아님)·비-Sionna → 제외. 그러나 **Sionna 미분가능 RT 로 씬 재질·산란계수를 측정에서 역추정**하는 Hoydis 계열이 genuine Sionna-센싱(환경 역문제) → 아래 등재. VLM-guided 재질추정(arXiv:2601.18242)은 Sionna 사용 미검증 → 다음 라운드 확인.
- **[R4] 미커버(다음 라운드 후보)**: Sionna SYS 시스템레벨 센싱, 위성/NTN·해양 ISAC, 6G ISAC 표준화(TR 38.901 산란), Sionna **드론/UAV 마이크로도플러** 특정, 실측(X410/USRP) vs Sionna 대조, 스펙트럼센싱/인지라디오, 특정 저널 IEEE TWC/JSAC/AES 본문.
- **[R5] 드론/UAV 마이크로도플러 + Sionna** — **자격 있는 Sionna 논문 0**. 드론 마이크로도플러 문헌은 **PO EM 시뮬**(로터 RCS를 물리광학으로, 예 "Extraction of Micro-Doppler Features from UAVs Based on EM Simulation")·전용 레이더 시뮬·테스트베드(arXiv:2408.16415)·드론군 신호(arXiv:2506.00497)로 전부 비-Sionna. 우리 PO+마이크로도플러 접근과 방법론 일치(A1 계열)이나 Sionna 아님.
- **[R5b] 6G ISAC 표준화(3GPP TR 38.901 산란 확장) + Sionna** — **자격 있는 Sionna 논문 0**. 표준화 라인은 전부 **GBSM/E-GBSM + 측정/주입 RCS**(비-Sionna): 표적채널을 h_target 로, 배경을 h_background 로 분해(우리 메모 '주류 h=h_bg+h_target' 확증). 바이스태틱 프레임(2408.11295)·TR 38.901 시뮬레이터(2606.07328)·RCS 통일모델(2505.20673, 이미 R1 DJI M350)·Rel-19 서베이(2512.03506) → 핵심 2편 아래 맥락 등재. **우리 포지셔닝의 정면 비교군**(주류=GBSM+주입RCS ↔ 우리=SBR+PO 산란 직접계산).
- **[R5] 미커버(다음 라운드 후보)**: Sionna SYS 시스템레벨, 위성/NTN 센싱, 스펙트럼센싱/인지라디오+Sionna, VLM-guided 재질추정(2601.18242) Sionna 검증, Sionna 로 **실측(USRP/X410) 캘리브레이션** 사례, 특정 저널 IEEE JSAC/AES 본문, 중국어/학위논문.
- **[R6] 패시브 레이더 CAF/클러터 억제 + VLM 재질추정** — 패시브 레이더 CAF/클러터 검색: 우리 도메인 정통이나 대부분 비-Sionna(커스텀 MC/실측). **VLM-guided 재질추정(arXiv:2601.18242)은 Sionna 확정**(R5 남긴 숙제 해결) → 아래 등재. 패시브 CAF 클러터억제(2512.24889)·셀룰러 UAV 궤적 실측(2602.08203)은 비-Sionna지만 **우리 파이프라인/응용의 실세계 대응**이라 맥락 등재.
- **[R6] 미커버(다음 라운드 후보)**: Sionna SYS 시스템레벨 센싱, 위성/NTN·해양 ISAC, EuRAD/RadarConf/ICASSP 실측 vs Sionna, Sionna 기반 **강화학습/능동센싱 빔포밍**, 생성모델(디퓨전) 채널+센싱, 의료/실내 fall detection, 특정 저널 IEEE GRS/TAP 본문.
- **[R7] ML/RL 능동센싱 + Sionna SYS 시스템레벨** — DRL ISAC 다수 검색되나 대부분 비-Sionna(해석/커스텀): 저고도 UAV 감시 DRL(Ye 외, arXiv:2412.04074)·전력할당 DRL(2606.12078)·DT-DRL 빔선택(2506.18560)은 Sionna 미표기. 그러나 **CellSense(arXiv:2606.07900)는 Sionna 링크레벨 확정** — sub-6GHz 셀룰러 패시브 센싱, USRP 실측 → 아래 등재(우리 니치 최직결). SimART(R1)도 Sionna SYS 사용 재확인.
- **[R7] 미커버(다음 라운드 후보)**: 위성/NTN·해양 ISAC+Sionna, 생성모델(디퓨전) 채널·센싱, 실내 fall detection/헬스케어 WiFi, EuRAD/RadarConf 실측 대조, 6G ISAC 프로토타입(OAI+Sionna) 더, 특정 저널 IEEE TAP/GRS/OJCOMS 본문, 비영어(중국어 CJK) 문헌.
- **[R8] 위성/NTN ISAC + 공식 "Made with Sionna" 교차확인** — NTN 센싱은 비-Sionna: LEO 잔해탐지 ISAC(Nkwewo 외, arXiv:2507.13526, SSK+chirp, 해석적)·Ka-band 우주기상 VTEC 센싱(arXiv:2601.00820)·ISAC 이미징 CSI(arXiv:2509.06672=NYURay). **공식 Made-with-Sionna 페이지의 센싱계열 재점검**: CISSIR(R1 등재)·BostonTwin(R2 등재)·Learning radio environments(R4 등재)에 더해 **Spectrum Anomaly Detection(Schösser 외, Sionna v0.15.1)** 미등재 발견 → 아래 등재. 공식 목록 센싱 항목 이제 전부 커버.
- **[R8] 미커버(다음 라운드 후보)**: 생성모델(디퓨전/GAN) 채널+센싱+Sionna, 실내 fall detection/호흡·심박 WiFi 센싱, Sionna 로 **적대적 재밍/스푸핑 탐지**, mmWave 이미징+Sionna, 특정 학회 GLOBECOM/ICC 2025 센싱세션 본문, 드론 detection 데이터셋(비-Sionna) 교차, Sionna 2.x 신기능(scattering/RIS API) 문서.
- **[R9] Sionna 2.x RCS/scattering 능력 점검 + 헬스케어 WiFi 센싱** — (a) Sionna 2.0.1 문서·기술보고서 확인: native RCS/PO 표면적분 **여전히 없음**(위 ⭐능력점검 참조) → 우리 주장 2.x 유효. (b) 헬스케어/생체신호(호흡·심박·낙상) WiFi 센싱은 **Sionna dry** — 전부 실측 소비자 WiFi CSI 기반(VitalCSI·ActiveVital 등), Sionna 합성 없음. **genuine Sionna 신규 0**.
- **[R9] 미커버(다음 라운드 후보)**: 생성모델(디퓨전/GAN)+Sionna 센싱, mmWave 이미징/SAR+Sionna, 강화학습 능동센싱+Sionna, 특정 저널 IEEE OJCOMS/WCL/TAP 본문, GLOBECOM/ICC/EuCAP 2025 센싱세션, Sionna Research Kit(sionna-rk, AI-RAN) 센싱 활용, 비영어(중국어) UAV ISAC.
- **[R10] 생성모델(디퓨전)+Sionna 센싱 & mmWave 이미징/SAR+Sionna — 둘 다 dry(신규 0)**: (a) diffusion CSI 데이터증강 ISAC 센싱(Wang 외, arXiv:2502.12622, 표적 수 검출 +70%)은 **데이터원 미명시(수집 CSI=실측 추정)**, Sionna 미확인. (b) mmWave/근거리 SAR 이미징은 대부분 커스텀 시뮬. **Sim2Radar(arXiv:2602.13314)**는 RGB→레이더 sim-to-real 인데 **커스텀 물리 레이트레이서(Fresnel+ITU-R)+VLM 재질**(비-Sionna, R6 VLM 재질과 유사 발상, ITU-R 앵커 공유)이라 제외.
- **[R10] 미커버(다음 라운드 후보)**: sionna-rk(Research Kit/AI-RAN)로 센싱 프로토타입, 비영어(중국어) UAV ISAC+Sionna, 특정 학회 EuCAP/EuRAD 2025 Sionna 세션, Sionna 로 **다중스태틱/셀프리 ISAC** 센싱, 광학·라이다 융합+Sionna, Sionna 기반 **적대적/보안 센싱**(스푸핑 탐지).
- **[R11] 셀프리/분산 ISAC + Sionna Research Kit — genuine Sionna 신규 0**: (a) 셀프리 다중스태틱 ISAC 표적검출은 대부분 해석/최적화(비-Sionna): 협력 다중스태틱 능동·수동(arXiv:2510.06654)·CF-mMIMO 검출(2404.17263·2410.16140) 등. (b) **Sionna Research Kit(Cammerer 외, ICMLCN 2025, arXiv:2505.15848)**는 Sionna+OAI AI-RAN 플랫폼이나 **센싱 데모 없음**(실시간 뉴럴 리시버=통신) — ISAC '가능'하나 미시연 → 제외. (c) **OpenISAC(arXiv:2601.03535)**는 비-Sionna(USRP/UHD)지만 우리 실측의 직접 아날로그 → 아래 맥락 등재.
- **[R11] 미커버(다음 라운드 후보)**: 비영어(중국어) UAV ISAC+Sionna, 광학/라이다-RF 융합 센싱+Sionna, Sionna 기반 스푸핑/보안 센싱, EuCAP/EuRAD 2025 Sionna 세션, Sionna 로 OTFS 센싱, 특정 저널 IEEE TWC/TSP 본문, Sionna 튜토리얼/벤치마크 재현연구.
- **[R12] OTFS ISAC + 멀티모달(카메라/라이다-RF) 융합 센싱** — (a) OTFS-ISAC(지연-도플러 추정·환경센싱, 2504.20659·2507.01427)은 대부분 커스텀/해석(Sionna 미확인) → dry. (b) 멀티모달에서 **Multimodal-Wireless 데이터셋(CARLA+Sionna)** genuine → 아래 등재. **카메라-협조 비협조 UAV 센싱(Wu 외, arXiv:2605.22090)**은 우리 도메인(비협조 드론)이나 **DeepSense 6G(실측)=비-Sionna** → 제외.
- **[R12] 미커버(다음 라운드 후보)**: 비영어(중국어) UAV ISAC+Sionna, Sionna 스푸핑/보안·GNSS 센싱, EuRAD/RadarConf 2025 Sionna, Sionna 로 humanmesh/motion 센싱, 특정 저널 IEEE TSP/TAP 본문, DeepSense 6G/DeepVerse vs Sionna 대조, Sionna 벤치마크 재현.
- **[R13] Sionna 로 표적 RCS 실제 계산 시도(A2 정면 탐색) + EuRAD/RadarConf** — **genuine 신규 논문 0**, 그러나 **능력점검 큰 보강**(위 ⭐R13): Sionna 는 **커스텀 산란패턴/재질**(`ScatteringPattern`·`RadioMaterialBase` 추상베이스)을 공식 확장점으로 제공 → RCS 는 사용자가 얹는 A2 경로로 설계됨(=우리 SBR+PO). ⚠ `PathSolver` 는 확장점이 **아니다**(MRO 실측 확인) — 자작 적분은 노출된 Mitsuba 광선엔진 위에 얹는다. GitHub Discussion #844(대량 광선샘플 RCS)는 미출판 커뮤니티. EuRAD/RadarConf 2024·25 에서 Sionna 표적센싱 특정 논문은 미발견(레이더 전용 venue 는 커스텀 EM 시뮬 위주).
- **[R13] 미커버(다음 라운드 후보)**: 비영어(중국어/한국어) UAV ISAC+Sionna 학위·저널, Sionna GNSS 재밍/스푸핑, 해양/수중 센싱, Sionna 로 material-aware imaging, 특정 저널 IEEE TAP/GRS 본문, 2026 신규 arXiv 재점검(포화 확인용), Sionna 2.x 로 RCS 얹은 후속연구(우리 방식 유사) 탐색.
- **[R14] 우리 방식 novelty 정면 탐색 + 비영어(중국어) UAV ISAC** — **genuine Sionna 신규 0**. (a) "Sionna+SBR/PO 드론 RCS 패시브 바이스태틱" 출판물 **없음**(위 🎯 novelty). 드론 RCS 는 MLFMA-PO·WIPL-D·측정·NATO STO 등 딴 툴. (b) 중국어권 UAV ISAC 도 대부분 비-Sionna(측정·해석): 저고도 UAV 추적(MDPI Electronics)·바이스태틱 UAV 스웜 RL(2501.06454)·모노스태틱 UAV 검출 540m 실측(2605.23561)·다중센서 ISAC 드론 사운딩(2402.16591, Thomä)은 아래 맥락.
- **[R14] 미커버(다음 라운드 후보)**: Sionna GNSS 스푸핑/재밍, 해양/수중·NTN 센싱, Sionna 2.x custom-solver 로 RCS 얹은 **우리-유사 후속** 재탐색(반증용), DeepSense/DeepVerse vs Sionna, 특정 저널 IEEE TAP/GRS/TGRS, 2026 하반기 신규 arXiv, **서베이 종합(pw05 포지셔닝)** 검토.
- **[R15] GNSS 보안 센싱 + 2026 신규 스윕** — **genuine Sionna +1**: **Active Sensing Meta-RL 에미터 측위(Khan·Wielenberg·Ott 외, arXiv:2605.12569)** = Sionna RT 데이터+RL 로 GNSS 간섭원 측위(S-ICDF R1 의 자매작, Fraunhofer IIS) → 아래 등재. 2026 스윕은 대부분 기존 항목(CellSense·TGNN·S-ICDF·NYURay 이미징). 신규 **mmWave 표적 형상재구성(Xing 외, arXiv:2602.05581, GLOBECOM 2023)**은 **Lambertian 산란·비-Sionna**라 제외(표적 형상/산란 센싱이라 주제는 근접).
- **[R15] 미커버(다음 라운드 후보)**: 해양/수중 ISAC, Sionna 로 material-aware mmWave imaging, 특정 저널 IEEE TGRS/TAP 본문, 한국어 UAV ISAC 학위, Sionna 2.x RCS 후속(반증용) 지속, **이제 서베이 종합(pw05) 단계 권고**(genuine 수확 급감·주요작 포착 완료).
- **[R16] 해양/수상 ISAC + Sionna custom-solver RCS 후속(novelty 반증)** — **genuine Sionna 신규 0**. (a) 해양 선박탐지는 항공/음향/위성·AIS/비전 위주로 **Sionna dry**. (b) novelty 재확인: Sionna custom PathSolver 로 드론/차량 RCS 낸 **출판물 여전히 없음**(Discussion #844 커뮤니티만). 단 **정준산란체 PO/SPM 모델**(Remote Sensing 2025, rs17172999) 발견 — 우리 report07 정준검증(평판·구)에 직결되는 PO 레퍼런스 → 아래 맥락 등재.
- **[R16] 미커버(다음 라운드 후보)**: 한국어/일본어 UAV ISAC 학위·저널, Sionna GNSS·수중음향, IEEE TGRS/TAP/TAES 본문, Sionna 2.x RCS 후속 지속 반증, **pw05 종합 강력 권고**(16라운드·genuine 16편+맥락 13편으로 포화).
- **[R17] CSI/WiFi 센싱(전용) + ICASSP/WCNC/EuCAP ISAC 스윕 — genuine 신규 0**: (a) WiFi CSI 센싱은 **실측 CSI 지배**(CSI-Bench·RFBoost·HAR 다수) → Sionna dry(합성은 MOCSID R3 뿐). (b) 동적 ISAC 채널 디지털트윈(Montaner·Cardona 외, EuCAP 2026, arXiv:2603.28736)·셀프리 ISAC 그래프학습(Jiang 외, GLOBECOM 2025, arXiv:2507.06612) 둘 다 **Sionna 미확인**(초록에 미언급, 채널모델/추정 위주) → 제외. 검색요약이 'Sionna 사용' 시사했으나 초록 확인 결과 미확증(정직 표기).
- **[R17] 미커버(다음 라운드 후보)**: 사실상 소진 — 남은 건 특정 저널 유료본문(IEEE TGRS/TAP/TAES)·비영어 학위·2026 하반기 신규뿐. **강력 권고: 새 논문 탐색 종료하고 pw05 종합 + 커밋 단계로**(17라운드 genuine 16 수렴, 반복 dry).
- **[R18] 패시브 바이스태틱 OFDM(우리 셋업 정통) 재확인 — genuine 신규 0, 소진 확정**: OFDM WiFi/LTE 패시브 바이스태틱 레이더(모호함수·직접파 제거) 문헌은 전부 **고전 PBR·비-Sionna**(IEEE Xplore 구작·ResearchGate). Sionna 계열은 S-ICDF(R1)·OpenISAC(R11, 비-Sionna) 외 신규 없음. 관련 비-Sionna: SISO 바이스태틱 ISAC(2508.12614)·셀룰러 협력 패시브센싱(2405.09179). → **탐색 종료·맨 아래 종합 섹션으로 대체**.
- **[R19] SAR/원격탐사(IEEE TGRS/GRSL) + Sionna — genuine 신규 0**: SAR 표적인식은 자체 EM 산란모델(산란센터·EMWaveNet·PASTE 등)·실측 SAR 영상 위주로 **Sionna 안 씀**(Sionna=전파채널이지 SAR 이미징 툴 아님). → 마지막 미탐색 저널각도까지 dry. **전 facet 소진 확정(13+ 각도 커버, 5연속 dry). 새 논문 탐색 종료가 옳음** — cron 은 이후 dry 확실.

## 논문 항목
<!-- 형식:
### <제목> (<저자 대표>, <venue> <year>)
- **센싱 태스크**: …
- **Sionna 사용**: RT? PHY? 무엇을 계산에 썼나
- **RCS/표적 산란 공백 처리**: A1/A2/B/C/D + 한 줄
- **우리 관련성**: 패시브 바이스태틱 드론탐지에 참고할 점
- **출처**: <URL / DOI / arXiv>
-->

### [R1] Temporal Graph Neural Network for ISAC Target Detection and Tracking (S. Maboud Sanaie 외, arXiv 2026)
- **센싱 태스크**: **바이스태틱 ISAC** 다중표적 탐지+추적을 delay-Doppler 그래프의 시계열 노드분류로. OFDM→FFT→delay-Doppler→CFAR.
- **Sionna 사용**: **Sionna RT** 로 CIR/전파경로(ground truth) 생성 → CFR FFT 로 delay-Doppler 맵. 파형·CFAR 는 Sionna 밖.
- **RCS 공백 처리**: **D(미보고)** — 표적을 점산란체로, RCS 는 경로이득 파라미터로만 등장(값·계산법 미명시).
- **우리 관련성**: **높음** — 바이스태틱 기하 + delay-Doppler+CFAR 파이프라인 + 점산란체, UAV 탐지를 동기로 명시.
- **출처**: https://arxiv.org/abs/2604.08306

### [R1] CISSIR: Beam Codebooks with Self-Interference Reduction Guarantees for ISAC (R. Hernangómez 외, IEEE TWC 2025)
- **센싱 태스크**: 모노스태틱형 ISAC 트랜시버의 OFDM **레이더 센싱**; 센싱 SNR 보호 위해 자기간섭 상한 두는 빔코드북 설계.
- **Sionna 사용**: Sionna 기반(공식 "Made with Sionna" 확인) — RT + 링크레벨로 ISAC 채널/SI 평가. (모듈·RCS 진입 방식은 접근 가능한 본문에선 미확인 — 정직 유보.)
- **RCS 공백 처리**: **D(미상세)** — 외부솔버·확장·명시 RCS 모델 안 보임, 표적 미명시.
- **우리 관련성**: **중간** — Sionna OFDM 센싱 체인이나 초점은 모노스태틱 자기간섭/빔포밍(패시브 바이스태틱 에코 아님).
- **출처**: https://arxiv.org/abs/2502.10371 (code: github.com/rodrihgh/cissir)

### [R1] AI-Empowered Low-Altitude Economy: Cooperative Sensing with Fixed Wireless Access (J. Zhang 외, IEEE ICC Workshops 2026)
- **센싱 태스크**: 저고도 **UAV 탐지+측위**를 다중 BS–CPE(FWA) 쌍의 **상향 CSI** 로 — 협력/멀티스태틱 기하.
- **Sionna 사용**: **OpenStreetMap + Blender + Sionna RT** 로 데이터셋 생성(LoS + 1차 정반사/확산반사).
- **RCS 공백 처리**: **C(메쉬반사우회)** — **UAV 를 금속 큐브 메쉬**로 두고 Sionna RT 내장 반사물리에 의존(RCS 모델·EM솔버 없음).
- **우리 관련성**: **높음** — 가장 근접 유사연구: 드론 표적·CSI 멀티스태틱 탐지·Sionna RT, 그리고 드론=큐브 우회가 RCS 공백을 구체적으로 예시.
- **출처**: https://arxiv.org/abs/2605.07623

### [R1] SimART: Unified Open Real-world Multimodal Simulation Platform for 6G ISAC (K. Yan 외, arXiv 2026)
- **센싱 태스크**: 멀티모달 ISAC 플랫폼; 사례연구=RGB카메라+GPS 로 **UAV 감지**해 64빔 코드북 선택(비전기반 빔예측).
- **Sionna 사용**: **Sionna RT**(전파경로) + **Sionna SYS**(링크/시스템레벨), RT용 메쉬 데시메이션.
- **RCS 공백 처리**: **D(미처리)** — UAV=기하 메쉬, EM산란/RCS 없음. 시연 센싱이 **RF 에코 아닌 카메라** — 레이더/RCS엔 곁다리.
- **우리 관련성**: **중간** — Sionna RT+SYS+UAV 표적이나 센싱 modality 가 카메라(RF 후방산란 아님).
- **출처**: https://arxiv.org/abs/2605.13309

### [R1] CAVIAR: Co-simulation of 6G Communications, 3D Scenarios and AI for Digital Twins (J. Borges 외, arXiv 2024)
- **센싱 태스크**: UAV 수색구조 디지털트윈; **YOLOv8 로 인간형 표적 탐지**(UAV 카메라), Sionna 는 통신링크 모델.
- **Sionna 사용**: **Sionna** 통신모듈 — RT(5바운스, 회절+산란 on, Fibonacci)로 UAV 링크 채널.
- **RCS 공백 처리**: **D/해당없음** — RCS·표적산란 모델 없음(Sionna 는 링크만).
- **우리 관련성**: **낮음~중간(곁다리)** — Sionna=통신용, "센싱"은 컴퓨터비전(표적에 대한 RF/레이더 사용 아님).
- **출처**: https://arxiv.org/abs/2401.03310

### [R1] The S-ICDF Dataset: Sionna-Simulated Dynamic Interference Characterization and Direction Finding (C. Wielenberg 외, arXiv 2026)
- **센싱 태스크**: 동적 GNSS 간섭원의 간섭특성화 + **방향탐지/DoA**.
- **Sionna 사용**: **Sionna RT** 로 데이터셋 합성(복잡환경 간섭의 수동 전파).
- **RCS 공백 처리**: **D/해당없음** — 표적에코/RCS 모델 없음(에미터 방향 센싱, 수동표적 후방산란 아님).
- **우리 관련성**: **낮음~중간** — Sionna RT 가 수동 DoA 센싱 데이터셋/파이프라인 구동하나 기하가 에미터 측위(표적에코 아님).
- **출처**: https://arxiv.org/abs/2607.03411

### [R2] Bridging the Sim-to-real Gap in RF Localization with Large-Scale Synthetic Pretraining (A. Manukyan 외, Information Fusion 2025)
- **센싱 태스크**: RF **핑거프린팅 측위**(로마 실측 vs 합성). 합성 데이터로 사전학습해 미측정 구역 일반화 향상.
- **Sionna 사용**: **Sionna RT** 로 합성 RF 핑거프린트 생성(사실성 단계별 데이터셋 + GP 로 기지국 파라미터 보정).
- **RCS 공백 처리**: **D/해당없음** — 표적이 **능동 송신원**(측위 대상)이라 후방산란 RCS 개념이 없음(환경=반사체, 표적=에미터).
- **우리 관련성**: **중간(방법론)** — sim-to-real 격차(합성 25 m→실측 184 m; 사전학습이 실측오차 절반↓)가 우리 시뮬↔X410 실측 대조에도 직결. 단 측위(에미터)이지 패시브 백스캐터 탐지 아님.
- **출처**: https://openreview.net/forum?id=VzDCtHKr8w · https://www.sciencedirect.com/science/article/pii/S1566253525011662

### [R2] On the Physical Plausibility and Distribution Alignment for Sim-to-Real RF Positioning (A. Saribekyan·A. Manukyan 외, IEEE CITS 2026)
- **센싱 태스크**: 셀룰러 측정 기반 **RF 측위**의 sim-to-real 전이(미관측 거리 일반화).
- **Sionna 사용**: **Sionna** 로 로마 배치 재구성, 기지국(위치·높이·방위·송신전력)을 보정해 합성 RSSI 생성.
- **RCS 공백 처리**: **D/해당없음** — 능동 송신원 측위(후방산란 없음).
- **우리 관련성**: **중간** — 핵심 결론 "RSSI **분포 정렬**이 물리적 사실성·데이터양보다 전이에 더 중요" 은 우리 시뮬 캘리브레이션에 시사점. (측위이지 표적탐지 아님.)
- **출처**: https://arxiv.org/abs/2607.04400

### [R2] BostonTwin: the Boston Digital Twin for Ray-Tracing in 6G Networks (P. Testolina 외, ACM MMSys 2024)
- **센싱 태스크**: 도시규모 **디지털트윈**(보스턴 3D+기지국)을 RT-ready 로 만들어 6G 전파 프로파일링·측위/커버리지 지원.
- **Sionna 사용**: **Sionna RT** — PLY 메쉬를 Sionna EM 레이트레이서에 직접 먹여 타일별 전파 프로파일. 공식 "Made with Sionna" 등재.
- **RCS 공백 처리**: **D/해당없음** — 환경 전파 트윈(표적 후방산란·RCS 모델 없음).
- **우리 관련성**: **낮음~중간** — RT 기반 측위 데이터셋 인프라의 대표 예. 표적탐지 아님이나 "Sionna 로 site-specific 트윈 구축" 방법 참고.
- **출처**: https://arxiv.org/abs/2403.12289

### [R3] MOCSID: Multi-cell Outdoor Channel State Information Dataset (Nguyen Quang Hieu 외, HAL 2025)
- **센싱 태스크**: **채널차팅**(CSI 기하로 사용자 위치 자기지도학습). 야외 캠퍼스·10 기지국(625×535 m)·보행자 이동·LoS/NLoS 혼합, 사용자 위치·속도·다중경로(지연·경로계수) 포함.
- **Sionna 사용**: **Sionna RT** 로 합성 CSI 생성. 공식 "Made with Sionna" 등재.
- **RCS 공백 처리**: **D/해당없음** — 사용자(능동 단말) 위치 추정, 후방산란 표적 아님.
- **우리 관련성**: **낮음~중간** — R2 측위와 동일 구도(Sionna=합성 CSI, 표적=에미터). 채널차팅 벤치마크 데이터 관행 참고이나 패시브 백스캐터 탐지 아님.
- **출처**: https://hal.science/hal-05037063/

### [R4] Learning Radio Environments by Differentiable Ray Tracing (J. Hoydis 외, IEEE TMLCN 2024)
- **센싱 태스크**: **환경 역문제 센싱** — CSI 측정에서 씬의 **재질 특성·확산 산란계수·안테나 패턴**을 경사기반으로 역추정(캘리브레이션). 합성+실측 실내(분산 MIMO 채널사운더) 검증.
- **Sionna 사용**: **Sionna 미분가능 RT** — 채널응답 CIR 의 파라미터 미분을 계산해 재질/산란/안테나를 신경망 가중치처럼 학습(전체 필드계산=계산그래프).
- **RCS/표적 산란 공백 처리**: **A2(Sionna확장)** 성격 — 표적 RCS 는 아니고 **환경 재질·확산 산란계수 S 를 캘리브레이션**(우리 report06 [B] "S 는 손잡이" 서사와 직결: 여기선 S 를 측정에서 학습). 이산 표적 후방산란은 다루지 않음(그 의미론 D).
- **우리 관련성**: **중간** — Sionna 산란모델(S·εr)이 **캘리브레이션 대상**임을 보여, 우리가 report06 에서 "S 는 물리 RCS 아닌 손잡이"라 한 주장을 정면 뒷받침. 다만 표적 RCS 를 산란적분으로 내지는 않음.
- **출처**: https://arxiv.org/abs/2311.18558 (IEEE TMLCN v2, pp.1527–1539)

### [R12] Multimodal-Wireless: A Large-Scale Dataset for Sensing and Communication (T. Mao·L. Liang·S. Jin·G.Y. Li 외, arXiv 2025)
- **센싱 태스크**: **멀티모달 센싱**(LiDAR·RGB+depth 카메라·IMU·radar @100Hz + 동기 CSI) — 사례로 멀티모달 LLM 빔예측. 16만 프레임·4 town·16 시나리오·3 날씨.
- **Sionna 사용**: **CARLA + Sionna** 파이프라인 — Sionna(RT)가 고해상 CSI/채널 생성, CARLA 가 센서 스트림.
- **RCS/표적 산란 공백 처리**: **D(미보고)** — 표적=CARLA 씬(차량 등), Sionna 는 CSI/전파 생성(표적 산란모델 아님).
- **우리 관련성**: **낮음~중간** — Sionna 역할이 다시 **CSI/전파 생성**(표적 산란 아님)임을 재확인. 멀티모달 데이터셋 관행(차량 맥락) 참고이나 패시브 백스캐터 드론 아님. SimART/BostonTwin 과 같은 인프라 계열.
- **출처**: https://arxiv.org/abs/2511.03220

### [R15] Active Sensing with Meta-Reinforcement Learning for Emitter Localization from RF Observations (M.S.J. Khan·C. Wielenberg·F. Ott 외, arXiv 2026)
- **센싱 태스크**: **GNSS 간섭원(에미터) 측위를 능동센싱**으로 — RL 에이전트(DQN/PPO, recurrent)가 2×2 패치 안테나로 순차 탐색해 단일스냅샷·다중경로 하에서 에미터 위치 추정.
- **Sionna 사용**: **Sionna RT** 모듈로 시뮬 데이터셋 생성(현실적 전파·다양 환경).
- **RCS/표적 산란 공백 처리**: **D/해당없음** — 능동 송신원 측위(후방산란 표적 아님). [[R1 S-ICDF]] 자매작(Fraunhofer IIS, Ott/Mutschler 그룹).
- **우리 관련성**: **낮음~중간** — Sionna RT 로 RF 데이터 만들어 **능동센싱(에이전트 이동 탐색)** 하는 패러다임 참고. 우리 패시브 백스캐터 탐지와는 표적 성격(에미터 vs 후방산란)·전략(능동 vs 수동)이 다름.
- **출처**: https://arxiv.org/abs/2605.12569

### [R8] Advancing Spectrum Anomaly Detection through Digital Twins (A. Schösser·F. Burmeister·P. Schulz·G. Fettweis 외, 2024)
- **센싱 태스크**: **스펙트럼 이상탐지**(재밍·간섭 등) — 디지털트윈이 만든 기대 무선환경과 관측 스펙트럼의 편차로 이상 탐지.
- **Sionna 사용**: **Sionna RT**(v0.15.1) — 레이트레이싱으로 라디오환경 디지털트윈 생성. 공식 "Made with Sionna" 등재.
- **RCS/표적 산란 공백 처리**: **D/해당없음** — 에미터/스펙트럼 이상(재머) 탐지이지 수동표적 후방산란 아님(환경 트윈).
- **우리 관련성**: **낮음~중간** — 디지털트윈 기반 이상탐지 방법론. 드론 탑재 재머 탐지엔 느슨히 연결되나 우리 백스캐터 탐지와는 태스크가 다름. (TU Dresden Fettweis 그룹.)
- **출처**: https://github.com/akdd11/advancing-spectrum-anomaly-detection (techrxiv 883996)

### [R7] CellSense: A Sub-6 GHz Cellular ISAC System for Clutter-Robust Passive Sensing (B. Kumar·I.K. Jain·V.K. Shah, MILCOM 2026)
- **센싱 태스크**: **패시브 셀룰러 ISAC** 표적 추적·측위(바이스태틱, 5G 스택에 native 통합, **클러터 강건**). 실내 1.43 m·검출 74% → 실외 0.33 m·94%.
- **Sionna 사용**: **Sionna RT**(전문검증: RT 라이브러리가 CIR 생성; 5G OFDM 트랜시버는 별도 구현). + **USRP/OAI 실측**.
- **RCS/표적 산란 공백 처리**: **C** — 조잡 표적, RT 반사경로 의존(코히런트 산란적분 없음; 전문검증).
- **우리 관련성**: **높음** — **우리 구도와 최근접**: 패시브 셀룰러·클러터 강건·**Sionna 링크레벨(우리 report12 에코와 동일 계열) + USRP 실측(우리 X410 계획과 동일)**. 추적은 우리 future work. 강력한 선행 앵커(특히 Sionna PHY-레벨 센싱 + 실측 결합 사례).
- **출처**: https://arxiv.org/abs/2606.07900

### [R6] Vision-Language-Model-Guided Differentiable Ray Tracing for Fast and Accurate Multi-Material RF Parameter Estimation (Z. Kang 외, arXiv 2026)
- **센싱 태스크**: **환경 재질 역문제 센싱** — 6G EM 디지털트윈용 다중재질 RF 파라미터(전도율 등) 추정. VLM 이 씬 이미지를 파싱해 ITU-R 재질표로 전도율 사전값 초기화 + 재질 구별력 높은 TX/RX 배치 선택.
- **Sionna 사용**: **Sionna 미분가능 RT** 확정("Experiments in NVIDIA Sionna on indoor scenes show 2–4× faster convergence") — VLM 사전값으로 경사기반 재질 최적화 가속.
- **RCS/표적 산란 공백 처리**: **A2(Sionna확장)** — 표적 RCS 아님, **환경 재질을 Sionna RT 로 역추정**([[R4 Hoydis]] 계열, ITU-R 재질표=우리 report06/08 와 동일 출처).
- **우리 관련성**: **중간** — 재질캘리브레이션(전도율·ITU-R)이 Sionna 산란모델의 조정 대상임을 재확인. 우리 재질가중 PO 와 같은 ITU-R 앵커. 표적 후방산란은 여전히 다루지 않음.
- **출처**: https://arxiv.org/abs/2601.18242

---

## RCS-공백 맥락 (비-Sionna, 인용 맥락용 — Sionna 실사용 아님)
- **Sounding-Based Evaluation of Multi-Sensor ISAC Networks for Drone Applications** — J. Beuster·C. Schneider·R.S. Thomä 외(TU Ilmenau), IEEE JC&S 2024(arXiv:2402.16591). 분산 다중센서 ISAC 로 **드론 탐지·측위**: **바이스태틱 후방산란** 서명 + **마이크로도플러**로 식별, 시뮬 모델 + **무향실 바이스태틱 반사도 측정** + 실비행 채널사운딩 3중, **공개 데이터셋**. ⚠ 비-Sionna(사운딩/자체시뮬). **우리와 최직결(표적산란 측)**: 드론 바이스태틱 반사도·마이크로도플러가 정확히 우리 관심량이고, **측정 반사도**가 우리 SBR+PO 검증의 외부 앵커 후보(공개데이터). https://arxiv.org/abs/2402.16591
- **OpenISAC: An Open-Source Real-Time Experimentation Platform for OFDM-ISAC** — Z. Zhou·X. Xu·Y. Zeng 외, IEEE IoT-J 2026(arXiv:2601.03535). **모노+바이스태틱 지연-도플러 OFDM-ISAC** 실시간 플랫폼, **USRP X400 시리즈**(우리 X410 계열) 지원, **유선 없이 바이스태틱 되는 OTA 동기** 메커니즘, C++(PHY)+Python(센싱). ⚠ 비-Sionna(USRP/UHD). **우리와 직결(실측 측)**: 우리 X410 필드테스트의 **직접 아날로그** — 바이스태틱 지연-도플러(우리 처리와 동일)·X400·OTA 동기(우리가 겪을 동기 문제 해법). [[sionna2-prior-work]] OPENSOURCE.md 의 OpenISAC 참조 확증. https://arxiv.org/abs/2601.03535
- **An Experimental Study on Fine-Grained Bistatic Sensing of UAV Trajectory via Cellular Downlink Signals** — C. Ji·J. Liu·R. Wang 외, IEEE WCL 2026(arXiv:2602.08203). **실측** 패시브 바이스태틱: **LTE 하향링크** 조명, 2 기지국 TX + 2 패시브 RX, 도플러로 **UAV 궤적** 복원(RX 30 m 내 90%에서 <50 cm; UAV·RX 는 기지국서 ~200 m). ⚠ 실험(비-Sionna). **우리와 최직결**: 정확히 우리가 시뮬하는 **셀룰러 패시브 바이스태틱 드론 탐지의 실세계 검증판**(추적은 우리 future work). 강력한 선행 앵커. https://arxiv.org/abs/2602.08203
- **Adaptive Clutter Suppression via Convex Optimization** — Y. He·G. Kearney·M. Fardad, arXiv:2512.24889(2025). 패시브/바이스태틱 레이더에서 **CAF 를 보존하며** 셀별 지연-도플러 필터로 클러터 억제(별도 소거단 불필요), 통신파형 MC 로 CFAR 교정·검출률 향상. ⚠ 커스텀 MC(Sionna 미표기). **우리와 직결**: 우리 report09/10 의 **ECA 클러터억제+CAF+CFAR 파이프라인의 방법론적 대안**(ECA 대신 convex QP). https://arxiv.org/abs/2512.24889
- **Channel Modeling Framework for Both Communications and Bistatic Sensing Under 3GPP Standard** — C. Luo·A. Tang 외, IEEE J. Sel. Areas Sensors 2024(arXiv:2408.11295). 3GPP GBSM 을 확장한 **바이스태틱 ISAC 채널 모델**(Tx-Rx 분리 기하), 표적을 **결정적 또는 통계적**으로 둘 수 있음. ⚠ 커스텀 GBSM(비-Sionna, 검증에 RT 시뮬 사용). **우리와 직결**: 정확히 우리 바이스태틱 기하이고, **주류는 표적을 주입 RCS(결정/통계)로 두는** 반면 우리는 SBR+PO 로 직접 계산 — 포지셔닝 비교군. https://arxiv.org/abs/2408.11295
- **Implementation and Calibration of 3GPP-Compliant ISAC Channel Simulator** — C.-H. Wu·M.-C. Lee·T.-S. Lee, arXiv:2606.07328(2026). TR 38.901 ISAC 채널모델 구현·캘리브레이션, **오픈소스 GitHub 공개**. ⚠ 비-Sionna(3GPP GBSM 준거). **우리와 직결**: 표준 준거 ISAC 시뮬의 레퍼런스 구현 — 우리 파이프라인을 표준과 대조할 잣대(주류 h=h_target+h_background 접근). https://arxiv.org/abs/2606.07328
- **Novel Extension of Full-Polarimetric Bistatic Scattering Modeling of Canonical Scatterers for Radar Recognition** — MDPI Remote Sensing 2025(doi:10.3390/rs17172999, 저자 미확인). PO + 정상위상법(SPM)으로 6 정준산란체(평판·다이헤드럴·트라이헤드럴·실린더·콘·구)의 **풀-편파 바이스태틱 산란** 해석확장, RCS 오차 0.3/2/2.6/3/6/7%. ⚠ 비-Sionna(해석 PO). **우리와 직결**: report07 이 SBR+PO 를 **평판(+16.42 dBsm)·구(−1.05 dBsm) 정준표적**으로 검증하는 것과 같은 계열 — PO 가 정준형상에서 정확함을 뒷받침하는 외부 레퍼런스(바이스태틱·편파까지). https://doi.org/10.3390/rs17172999
- **Ray-Based Simulation of Scattering from Discretized Curved Bodies for Vehicular and ISAC Applications** — R. Ziganshin·E.M. Vitucci·V. Degli-Esposti 외, arXiv:2604.05991(2026). **곡면체를 평면 패싯으로 이산화**해 UTD(+정점회절·이중반사)로 산란 계산, 차량/ISAC 채널모델링. **바이스태틱 후방산란역 + 그림자역 full-wave** 검증(구·실린더 canonical 대조). ✅ **Sionna-RT v0.19 확장(A2, 전문검증)** — *"Sionna-RT (v0.19) was used as a basic RT framework"* 위에 UTD·정점회절 얹음(code AinurZiga/sionna-RT-reflectivity). **우리와 가장 가까운 선행연구**: 둘 다 **Sionna-RT+커스텀 산란 확장**. 차이=SBR+PO vs UTD · 소형드론 vs 대형표적(구·차). https://arxiv.org/abs/2604.05991
- **RIS-aided Radar Detection Architectures with Application to Low-RCS Targets** — F. Colone·F. Costa·D. Orlando 외, arXiv:2601.10846(2026). **저관측(low-RCS) 표적** 레이더 검출을 RIS 로 보조: 표적이 무관한 방향으로 산란한 에너지를 RIS 가 레이더로 재지향해 **모노스태틱+바이스태틱 결합**으로 잡음(멀티스태틱 동기화 문제 회피). ⚠ 해석적 설계(Sionna·특정 RT 시뮬 미사용). **우리와 직결**: 저-RCS·바이스태틱·표적 산란 재활용이라는 정확히 같은 레짐이고, 저자 Colone 은 패시브 레이더 권위자(Sapienza Roma). 우리 SBR 산란 재지향 논의의 참고. https://arxiv.org/abs/2601.10846
- **Localization in Digital Twin MIMO Networks: A Case for Massive Fingerprinting** — J. Morais·A. Alkhateeb, ICC 2024(arXiv:2403.09614). RT-생성 디지털트윈 RF맵으로 대량 핑거프린팅 측위(서브미터, NLoS 95%). ⚠ 레이트레이서를 명시 안 하나 저자 그룹이 **DeepMIMO/DeepVerse**(Wireless InSite 기반) 운영 → **Sionna 아닐 가능성 큼**. 측위(에미터)라 RCS 공백도 해당없음. 참고: RT-트윈 핑거프린팅이 측위의 주류 접근임을 보여줌. https://arxiv.org/abs/2403.09614
- **BVH-Accelerated Ray Tracing for High-Frequency EM Backscattering ("Sagitta SBR")** — M. Pasquale 외, arXiv:2604.09243(2026). 독립형 **GPU SBR+물리광학 RCS 솔버**(BVH가속·오픈소스), Sionna 기반 아님. 우리 SBR+PO 가 Sionna 산란공백을 메우는 바로 그 **A1 외부 EM/SBR** 부류 — 교차검증 후보 도구. https://arxiv.org/abs/2604.09243
- **A Unified RCS Modeling of Typical Targets for 3GPP ISAC Channel Standardization** — Y. Zhang 외, arXiv:2505.20673(2025). **측정** 모노스태틱 RCS(무향실 10–36 GHz)로 **DJI M350 UAV**·차량·인간; RCS 를 대규모/각도/랜덤 성분 분해. 순수 **B(측정/통계)** — DJI 드론의 **직접 인용가능 RCS 앵커**. https://arxiv.org/abs/2505.20673
- **RayLoc: Wireless Indoor Localization via Fully Differentiable Ray-tracing** — X. Han 외, arXiv:2501.17881(2025). 표적을 반사메쉬로 두고 **커스텀(비-Sionna) 미분가능 레이트레이서** 사용; 저자들이 **Sionna 는 표적위치에 미분불가**라 자체제작 — 표적센싱 연구가 왜 Sionna 를 떠나는지 근거. https://arxiv.org/abs/2501.17881
- **커뮤니티**: NVlabs/sionna GitHub **Discussion #844**("RCS Calculation using Sionna RT by sampling objects with a huge number of rays")·커스텀 PathSolver 로 지정방향 레이 발사해 RCS — 메쉬샘플링(C)/Sionna확장(A2) 우회가 커뮤니티에서 논의됨(미출판).

> **R1 교차소견(RCS 공백)**: 발견된 모든 Sionna-센싱 논문 중 **Sionna 안에서 산란적분을 계산한 것은 하나도 없음**. (C) 조잡한 메쉬(UAV=금속큐브)+RT 반사경로, 또는 (D) 미명시 RCS 의 점산란체, 또는 RF 센싱 회피(비전). → "Sionna PathSolver 에 산란적분 없음, 표적에코 충실도는 외부경로(A1 SBR+PO·B 측정 RCS·A2 커스텀확장) 필요"라는 프로젝트 전제를 뒷받침.

---

## 덱 대조 추가 (Sionna-파생·미확인 — teammeeting_0721 선행연구 표에서 역수집)

### Unreal is all you need: Multimodal ISAC Data Simulation with Only One Engine ("Great-X"/Great-MSD) (K. Huang·S. Xu 외, arXiv 2025)
- **센싱 태스크**: **CSI 기반 UAV 3D 측위**. Great-MSD(저고도 UAV 멀티모달 데이터셋: CSI·RGB·Radar·LiDAR) 구축.
- **Sionna 사용**: ⚠ **Sionna RT 계산을 Unreal Engine 에 재구현**(reconstruct) — Sionna 라이브러리 직접 사용 아님, Sionna-파생/등가. 확산산란(S) 모델 상속 추정(초록 미명시).
- **RCS/표적 산란 공백 처리**: **C/A2 경계** — Sionna-식 RT 반사·확산(S)으로 UAV 처리(코히런트 PO 아님).
- **우리 관련성**: **낮음~중간** — Sionna RT 를 엔진 이식해 UAV 데이터 대량생성. 표적=능동단말 측위(후방산란 아님). 덱 12p '재질 산란 손잡이(S)' 행.
- **출처**: https://arxiv.org/abs/2507.08716 (code: hkw-xg/Great-MCD)

### LAMBDA: A Low-Altitude Multimodal Base Dataset for UAV Sensing and Communication (L. Zhou·M. Tao 외, arXiv 2026)
- **센싱 태스크**: 저고도 UAV **멀티모달**(RGB·depth·LiDAR·IMU·pose·CSI·radar-synthesis) 데이터셋. 사례: RGB 빔예측·RGB-LiDAR UAV 측위.
- **Sionna 사용**: **Sionna RT 확정**(전문검증: material-aware RT + CSI 생성). ⚠단, 표적 EM 툴 구체명(덱 'CADFEKO')은 원문에 미명시.
- **RCS/표적 산란 공백 처리**: **A1** — UAV 를 외부 EM 으로 모델해 주입(전문검증). Sionna(RT)는 전파/CSI 담당, 표적 RCS는 밖에서.
- **우리 관련성**: **낮음~중간** — 저고도 UAV 멀티모달 벤치마크. 표적 RCS 를 밖에서 구해 주입하는 구조는 우리와 같은 계열(방법은 다름). Sionna 사용 확인 필요.
- **출처**: https://arxiv.org/abs/2607.03826

---

## 🧭 종합 — 우리 포지셔닝 (R18, 18라운드 기준; pw05 초안)

### 1) Sionna-센싱 16편은 Sionna 를 무엇에 쓰나 (표적 산란은 아무도 안 냄)
- **ISAC 채널/검출**(RT 로 CIR ground-truth): TGNN(2604.08306)·CISSIR(2502.10371)
- **측위/포지셔닝**(RT 합성 핑거프린트): Manukyan 사전학습·Saribekyan(2607.04400)·BostonTwin(2403.12289)
- **채널차팅**: MOCSID(hal-05037063)
- **환경 재질/산란계수 캘리브레이션**(미분가능 RT): Hoydis(2311.18558)·VLM-재질(2601.18242)
- **멀티모달 센싱 데이터셋**(CARLA/Blender+Sionna): SimART(2605.13309)·Multimodal-Wireless(2511.03220)
- **패시브 셀룰러 클러터강건 센싱**(Sionna PHY 링크레벨+USRP): **CellSense(2606.07900)** ← 우리와 가장 근접
- **에미터/간섭 측위·DoA·이상탐지**: S-ICDF(2607.03411)·Active-Sensing-MetaRL(2605.12569)·Spectrum-Anomaly(Schösser)·CAVIAR(2401.03310)
- **공통점**: Sionna = **CSI/전파/채널 생성 또는 재질 캘리브레이션**. **표적 RCS/후방산란을 Sionna 안에서 코히런트 산란적분으로 낸 논문은 0/16.**

### 2) 우리 니치 = 문헌상 미점유 (R14·R16 근거)
**Sionna PHY 링크레벨 + 커스텀 SBR+PO 표적 RCS + 5종 드론(곡면·재질·회전) + 패시브 바이스태틱**. 이 조합의 출판물 없음.
- 표적 RCS '값'을 내는 진영은 대부분 **Sionna 밖**: A1 SBR(Sagitta 2604.09243)·MLFMA-PO·정준 PO/SPM(rs17172999)·측정(DJI M350 2505.20673)·GBSM 주입(3GPP 2408.11295/2606.07328). **예외=Ziganshin(2604.05991)**: 유일하게 **Sionna-RT 안**에서(A2 확장) 커스텀 산란(UTD)을 얹은 사례 — 우리와 같은 계열(차이=SBR+PO vs UTD · 소형 드론 vs 대형 표적).
- Sionna 는 **RCS 를 사용자가 얹으라고 확장(custom scattering pattern·custom radio material)을 설계로 제공**(⭐R13). ⚠ `PathSolver` subclassing 은 확장점이 아니다 — 자작 적분은 Mitsuba 광선엔진 위에 얹는다. — 우리 SBR+PO 가 정확히 그 A2 경로. 정직 프레이밍: *"기본 solver 는 코히런트 PO/RCS 안 냄; Sionna 가 연 확장에 우리가 SBR+PO 를 얹음."*

### 3) 비교군·검증 앵커 (report 인용 지도)
- **가장 근접(방법)**: CellSense(Sionna PHY+USRP 패시브 셀룰러) — report12/실측 비교군.
- **실측 대응(응용)**: 셀룰러 UAV 궤적 바이스태틱 실측(2602.08203)·OpenISAC(X400·바이스태틱 OTA, 2601.03535)·Beuster/Thomä 드론 바이스태틱 반사도+마이크로도플러+**공개데이터**(2402.16591).
- **RCS 절대 앵커**: DJI M350 측정(2505.20673) → report08.
- **PO 검증 레퍼런스**: 정준산란체 PO/SPM(rs17172999) → report07 평판·구 검증.
- **교차검증 엔진**: Sagitta SBR(2604.09243)·Ziganshin UTD(2604.05991) → report07 대안 대조.
- **클러터 억제 대안**: CAF보존 convex(2512.24889) → report09/10 ECA 대안.
- **주류 대비**: 표준화 GBSM+주입RCS(2408.11295/2606.07328) ↔ 우리 SBR+PO 직접계산.

### 4) 다음 액션(사용자 확인 후)
(a) 이 종합을 독립 **pw05 노트/노트북**으로 승격 + prior_work README 반영, (b) `sionna_sensing_survey.md` **git 커밋**, (c) ⭐R13 A2-확장 프레이밍을 **report06/07 '왜' 절**에 반영("한계 우회"가 아니라 "Sionna 확장 경로 사용").
