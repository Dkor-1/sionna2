# -*- coding: utf-8 -*-
"""pw04_data.py — pw04 리포트의 **검증된 선행연구 데이터**.

출처: 3중 워크플로 문헌조사(다각도 웹서치 → 논문별 적대적 검증) + 사용자 제공 타 LLM 조사 대조.
모든 항목은 1차 출처(arXiv/IEEE/DOI) 웹 확인. 타 LLM 이 준 것 중 **검증 실패/오류는 제외·정정**했다:
  · Clutter-Aware(arXiv:2602.10537) — 타 LLM 은 'Sionna 사용'이라 했으나 실제 **Sionna 미사용**(추상 복소계수) → 제외.
  · Integrated Comm&Sensing for Intelligent Transportation(npj) — 6회 검색에도 **웹 미확인**(환각 의심) → 제외.
  · §4 표3 3편(Channel Modeling Framework·Site-Specific SSCR·6G Survey) — 실재하나 '붙일 수 있는 RCS 모델'은 아님
    (SSCR 의 'Sionna CIR 저장' 주장은 환각) → **설계 정당화 인용**으로 정정.

taxonomy(타 LLM 안): A1 외부 EM solver RCS 결합 · A2 Sionna 자체 확장 · B 외생 analytical/statistical RCS
                     · C 3D mesh 반사로 우회 · D RCS 언급하나 구현 미보고.
"""

# ─────────────────────────────────────────────────────────────────────────────
CONCLUSION = dict(
    headline=("**Sionna RT 는 송신기–환경–수신기 사이의 전파경로(propagation path)를 계산하는 도구이지, "
              "임의의 표적 CAD 로부터 RCS·복소 산란계수(complex scattering coefficient)를 내는 전자기 "
              "산란 해석기가 아니다.**"),
    detail=("Sionna 개발진도 공식 논의에서 현재 Sionna RT 가 객체를 RCS 로 모델링하지 않으며 정반사(specular) "
            "는 반사면이 파장보다 충분히 커 무한 평면처럼 취급한다는 가정을 쓴다고 명시했다. 실제로 답이 알려진 "
            "삼면 코너 리플렉터를 Sionna 로 구현했을 때 이론과 반대로 금속판보다 약한 반사가 나온 사례도 보고됐다."),
    nuance=("⚠ **'RCS 가 없으면 센싱을 전혀 못 한다' 는 과장이다.** delay·Doppler·AoA·궤적처럼 표적 경로의 "
            "**위치만** 쓰는 정규화 센싱은 RCS 없이도 된다. 다만 **수신 반사전력·SCNR·탐지거리·P_D·P_FA·"
            "weak/strong target 관계·자세별 탐지성·표적 분류**를 물리적으로 의미 있게 평가하려면 RCS(또는 이에 "
            "준하는 target reflectivity)가 반드시 필요하다. 바이스태틱 표적 수신전력은 "
            "$P_r = P_t G_t G_r \\lambda^2 \\sigma_b / ((4\\pi)^3 R_T^2 R_R^2)$ 로 $\\sigma_b$(bistatic RCS)에 "
            "직접 비례하기 때문이다."),
)

# 다섯 갈래 (A1/A2/B/C/D) + 물리 신뢰도 순서
TAXONOMY = [
    ("A1", "외부 EM solver 의 RCS 를 Sionna 에 결합", "FEKO·openEMS 등 풀웨이브 계산 결과를 Sionna 경로에 주입"),
    ("A2", "Sionna RT 자체 확장", "UTD·vertex diffraction 등을 추가해 표적 reflectivity 를 Sionna 안에서 직접 계산"),
    ("B",  "외생 analytical/statistical RCS", "상수 RCS·point-scatterer·측정기반 확률분포를 경로이득에 삽입"),
    ("C",  "3D mesh 반사로 우회", "표적 메시+material 만 넣고 Sionna 가 낸 반사경로를 그대로 표적 echo 로 사용(명시적 RCS 없음)"),
    ("D",  "RCS 필요성만 언급, 구현 미보고", "수식엔 RCS 가 있으나 Sionna 결과와 결합하는 방법이 불명확"),
]
CREDIBILITY_ORDER = ("외부 EM/측정 기반 복소 reflectivity  >  확장된 Sionna reflectivity  >  "
                     "측정 기반 통계 RCS  >  point-scatterer/상수 RCS  >  단순 mesh 반사")

# ─────────────────────────────────────────────────────────────────────────────
# 표1 — Sionna 를 직접 쓰며 RCS 를 **명시적으로 해결하거나 외생 모델로 보완**한 연구 (A1/A2/B)
#  cols: 연도 | 논문(등급) | Sionna 역할 | Sionna 만으로 부족했던 것 | RCS 해결 방법 | 해결 수준·한계 | 검증
TABLE1 = [
    dict(year="2026", grade="A1", study="LAMBDA (UAV 멀티모달 데이터셋)", arxiv="2607.03826",
         sionna="Sionna RT 로 UAV 환경의 복소 path gain·지연·도플러·AoA/AoD·CSI 생성 → FMCW radar cube·RD/Angle 합성",
         gap="Sionna 복소 CSI 는 환경 전파효과만; UAV 자체의 자세별 radar reflectivity 는 안 줌",
         how="CADFEKO(풀웨이브)로 AirSim UAV 모델의 자세의존 RCS 계산 → 각 경로 CSI 계수에 조회·결합. 즉 Sionna multipath + CADFEKO UAV RCS",
         level="가장 직접적인 선행. 단 FEKO 가 상용·기준파형 77 GHz FMCW. RCS 크기는 결합하나 복소 위상·편파행렬·rotor micro-Doppler 까지인지는 불명확",
         verify="✅ arXiv 본문 확인: \"the RCS term is obtained from CADFEKO simulations\""),
    dict(year="2026", grade="A2", study="Ziganshin — Discretized Curved Bodies (확장판)", arxiv="2604.05991",
         sionna="Sionna RT(v0.19)를 **기반 엔진**으로만 사용(오픈소스·미분가능 path tracing)",
         gap="표준 Sionna 는 faceted 정반사·기본 UTD 만으로 곡면 표적의 그림자·bistatic reflectivity 를 못 살림",
         how="vertex/finite-edge diffraction·edge–vertex·double-bounce 를 **직접 추가**. 곡면을 파장연동 facet 으로 이산화해 산란 복소장 계산. 구·원통 해석해·MLFMM·실측 차량과 대조",
         level="가장 강한 오픈소스 접근. far-field 스칼라 RCS 주입 없이 복소 reflectivity 계산. 단 PEC·투과무시·복합유전체·rotor micro-Doppler 에 제한적. 수정코드 공개",
         verify="✅ 확장판 본문 인용 확인(Sionna-RT v0.19 커스터마이즈)"),
    dict(year="2025", grade="A2", study="Ziganshin — Multistatic Scattering (선행판)", arxiv="EuCAP 2025 (IEEE 10999367)",
         sionna="위 확장판의 선행 버전. Sionna RT 로 multistatic target scattering 계산",
         gap="기본 Sionna 의 edge diffraction 만으론 작은 facet·곡면 산란을 정확히 못 냄",
         how="곡면을 facet 이산화 + vertex diffraction 추가 → multistatic reflectivity",
         level="표적 reflectivity 를 Sionna 내부에서 계산하려는 **최초 단계 중 하나**. 5쪽 학회지라 검증범위·상호작용 차수가 후속보다 제한적",
         verify="✅ IEEE Xplore 등재 확인(동저자군 확장판으로 방법 교차확인)"),
    dict(year="2026", grade="B", study="Temporal-GNN for ISAC (TGNN)", arxiv="2604.08306",
         sionna="Sionna RT 로 static+moving-target 경로의 bistatic CIR 생성 → delay-Doppler map·CFAR·TGNN 다중추적",
         gap="Sionna 가 target 경로의 절대 반사계수를 결정해 주지 않음",
         how="target path gain 에 Tx/Rx 안테나이득·path loss + **외부 point-scatterer bistatic RCS** 삽입(표적별 dBsm 범위 지정). 차량 RCS 통계 문헌 근거",
         level="탐지·추적 알고리즘 평가엔 실용적이나, 표적=점 가정이라 자세·편파·extended target·micro-Doppler 재현 못함",
         verify="✅ arXiv 본문: \"bi-static RCS relies on the assumption that the target is a point scatterer\""),
    dict(year="2025", grade="B", study="CKM Enabled Low-Altitude ISAC", arxiv="2512.02464",
         sionna="Sionna RT(v0.18)로 후보 BS 의 CKM·LoS 생성 → UAV corridor·BS 배치 최적화",
         gap="Sionna CKM 은 통신 path gain 은 주나 monostatic UAV echo power 는 직접 안 줌",
         how="별도 radar equation 에 **고정 UAV RCS(σ=1 m²)를 외생 상수**로 대입, Sionna LoS/path 와 결합",
         level="system-level coverage planning 엔 적합하나 RCS 상수·자세/주파수/편파/드론종류/micro-Doppler 무시. waveform-level 센싱 아님",
         verify="✅ arXiv 본문: \"Sionna RT (v0.18.0)\" · \"σRCS=1 m²\""),
    dict(year="2025", grade="B", study="Graph Learning — Cell-Free ISAC", arxiv="2507.06612 (GLOBECOM 2025)",
         sionna="Sionna-RT 로 도시 multipath·clutter 전파환경 생성(강건성 평가절 V-D)",
         gap="Sionna RT 자체는 target/clutter RCS 를 안 냄",
         how="수식상 target/clutter echo 에 **외생 통계 RCS**($E|\\beta|^2=\\zeta^2$) 사용, Sionna 는 환경 전파(정반사·확산·회절·굴절)만 담당",
         level="분석모델엔 RCS 명확하나 Sionna path 와 수식 RCS echo 의 결합 인터페이스가 충분히 기술 안 됨",
         verify="✅ PDF 원문 추출로 Sionna 4회·ray-tracing 확인(초기 요약은 truncation 으로 놓침)"),
]

# 표2 — RCS 를 명시적으로 계산하지 않고 **Sionna 메시 반사로 우회**한 연구 (C/D)
#  cols: 연도 | 논문 | 센싱 태스크 | RCS 처리 | 가능한 주장 | 남는 문제 | 검증
TABLE2 = [
    dict(year="2025", grade="C", study="Great-X / Great-MSD (Unreal 재구현)", arxiv="2507.08716",
         task="Sionna RT 식 RT 를 Unreal 에 재구현해 CSI·Radar·LiDAR·RGB 동시 생성. 저고도 UAV 3D 측위",
         how="표적 RCS 별도계산 없이 Sionna 정반사(R=√(1−S²))+확산(S) 에너지분할 산란식을 UAV 메시 재질에 적용. RCS 값 미보고",
         claim="멀티모달 데이터 대량 생성·CSI 측위 베이스라인",
         problem="UAV 코히어런트 RCS·각도패턴·rotor 미세산란 부재",
         verify="✅ 본문: \"referenced from SionnaRT\" + 재구현 명시"),
    dict(year="2026", grade="C", study="Deterministic Modeling ISAC (Montaner)", arxiv="2603.28736 (EuCAP 2026)",
         task="Sionna RT 로 79 GHz mono/bistatic 차량 ISAC 디지털트윈, 사운더 측정 보정",
         how="명시적 표적 RCS 없음. 차량=씬 메시, 산란은 Sionna 정반사/확산 분할(R²+S²=1)+재질 확산계수 S(측정보정)",
         claim="측정보정된 동적 ISAC 채널 signature(멀티패스·도플러)",
         problem="표적 backscatter 가 실제 RCS 아님 — 정량 RCS 충실도 주장 불가",
         verify="✅ arXiv 본문: \"diffuse scattering abstraction ... in Sionna RT\""),
    dict(year="2026", grade="C", study="CellSense (Sub-6 GHz Cellular ISAC)", arxiv="2606.07900 (MILCOM 2026)",
         task="5G OFDM passive/bistatic **사람** 탐지·측위·추적. Sionna 시뮬 + OAI/USRP 실측 병행",
         how="사람을 1.8×0.5×0.25 m **cuboid 메시**로, Sionna RT 가 그 반사경로 생성. baseline 차분(background subtraction)으로 동적반사만 분리. RCS 언급 자체가 없음",
         claim="차분 지연·AoA·궤적 등 상대특성·알고리즘 실용성(USRP 실측이 보완)",
         problem="cuboid+Sionna 반사가 실제 human RCS 와 정량 일치 보장 없음 → 절대 P_D·거리·SCNR 은 RCS-보정 결과 아님",
         verify="✅ arXiv 확인(표적=사람, differential detection). 타 LLM 의 'PHY link-level'은 실제 RT-CIR 이 핵심"),
    dict(year="2025", grade="C/D", study="Micro-Doppler of Multirotor UAVs (Ray Tracing)", arxiv="IEEE ICCT 2025 (DOI 10.1109/ICCT67417.2025.11374154)",
         task="Sionna RT 로 multirotor **UAV** micro-Doppler feasibility 검토",
         how="Sionna RT 로 rotor 유도 micro-Doppler·dynamic RCS 시뮬 주장, 그러나 RCS 산출·보정 알고리즘 세부는 확인 제한",
         claim="Sionna 회전 기하가 시간변화 도플러 생성 가능(feasibility)",
         problem="RCS 가 surface-current 기반인지 mesh 반사 상대변화인지 판별 어려움 → **보조 문헌**으로 취급",
         verify="✅ 실재(Semantic Scholar DOI 확인). 방법 세부는 초록 수준"),
    dict(year="2026", grade="D", study="SimART (멀티모달 6G ISAC 플랫폼)", arxiv="2605.13309",
         task="Sionna RT 를 back end 로 한 통합 시뮬 플랫폼",
         how="Sionna RT 로 채널 생성하나 표적 RCS 처리 세부 미보고",
         claim="오픈 멀티모달 시뮬 플랫폼",
         problem="RCS 구현 세부 불명 — 구현 미보고(D)",
         verify="✅ arXiv 확인: \"ray tracing module built on Sionna RT\""),
]

# 제외(검증 실패/오류) — 정직성 기록
EXCLUDED = [
    "**Clutter-Aware ISAC**(arXiv:2602.10537, Swindlehurst 등, Proc. IEEE 튜토리얼): 타 LLM 은 'Sionna 도시 scene 사용'이라 했으나, 원문 검증 결과 **Sionna·ray-tracing·mesh 를 전혀 쓰지 않음**(표적을 추상 복소계수로 표현). Sionna 표에서 제외.",
    "**Integrated Comm & Sensing for Intelligent Transportation**(npj Wireless Technology 주장): 정확 제목·arXiv·저널·검색 **6회 모두 1차 출처 미확인**(환각 의심) → 제외.",
]

# 표3 — Sionna 가 못 내는 표적 산란을 **채워줄 후보/설계 근거** 문헌 (Sionna 미사용, 드론 관련 또는 인용가치)
#  ⚠ aux 검증: 아래 셋(Channel Modeling Framework·SSCR·6G Survey)은 '바로 붙일 RCS 모델'이 아니라 **설계 정당화 인용**.
TABLE3 = [
    dict(year="2025", study="Unified RCS Modeling of Typical Targets (3GPP ISAC)", arxiv="BUPT/CMCC (Zhang 그룹)",
         model="UAV·사람·차량 RCS 를 ①large-scale power ②각도의존 small-scale ③random 성분으로 분해. 5밴드 monostatic 측정 검증",
         attach="Sionna 가 낸 경로마다 주파수·aspect angle 로 σ 샘플링해 path gain 반영",
         value="풀웨이브보다 가볍고 system/link-level 에 적합. 단 주 검증이 monostatic → passive bistatic 엔 추가확장 필요",
         kind="측정기반 통계 RCS 모델(드론 포함)"),
    dict(year="2025", study="Statistical & Deterministic RCS Characterization for ISAC", arxiv="NYU/NYUAD (Azim 등)",
         model="25–28 GHz 에서 UAV·AMR·robot arm 의 monostatic + 20/40/60° bistatic RCS 측정, Lognormal/Gamma 적합",
         attach="Tx–target–Rx 기하에서 bistatic angle 계산해 해당 조건 RCS 분포 샘플링",
         value="Sionna 결합이 가장 쉬운 **측정기반 bistatic 통계 RCS** 중 하나. 단 mmWave 실내공장 조건이라 sub-6 GHz 직접전이 어려움",
         kind="측정기반 통계 RCS(UAV 포함)"),
    dict(year="2025", study="Micro-Doppler of Multi-Propeller Drones (Distributed ISAC)", arxiv="2504.05168 (IEEE J-STEAP)",
         model="thin-wire 모델을 bistatic OFDM 으로 확장, multi-propeller + 드론 정적동체 reflectivity 통합. 실측 검증",
         attach="Sionna 가 동체 병진·환경 멀티패스 생성, 이 모델이 시간가변 rotor 산란계수 $s_{rotor}(t)$ 생성",
         value="사용자 드론 passive OFDM 센싱에 **가장 직접적**. 대규모 AI 데이터 생성에도 적합, 풀웨이브보다 가벼움",
         kind="드론 rotor micro-Doppler 모델(핵심)"),
    dict(year="2024", study="Channel Modeling Framework for Comms & Bistatic Sensing (3GPP)", arxiv="2408.11295 (IEEE Sensors)",
         model="3GPP 채널에 target-cluster 를 배경과 분리 생성(h=h_target+h_background), det/stat 선택",
         attach="배경 통신채널과 별도로 target channel 생성 후 합산 — **우리 h=h_dir+h_bg+h_target 분해와 일치**",
         value="⚠ RCS 를 **클러스터 파워 가이드(사람 0·차 20 dBsm)로만** 씀 — 소형 드론 RCS 모델은 제공 안 함. **아키텍처 근거 인용**용",
         kind="설계 근거(RCS 모델 아님)"),
    dict(year="2024", study="Site-Specific Radio Channel Representation for 5G/6G", arxiv="2406.09025 (IEEE ComMag)",
         model="mono/bistatic 센싱 path loss 에 RCS·normalized reflectivity σ 가 **별도로 필요**함을 명시(공식에 −10log σ)",
         attach="⚠ 타 LLM 의 'Sionna CIR 에 저장(SSCR)' 주장은 **환각** — 논문은 Sionna 를 언급하지 않음",
         value="'Sionna 경로만으로 sensing channel 이 완성되지 않는다' 는 **구조적 근거 인용**(Zemen·Molisch·Valenzuela). RCS 수치·모델은 없음",
         kind="설계 근거(RCS 모델 아님)"),
    dict(year="2023", study="6G Channel Modeling Survey/Tutorial (BUPT)", arxiv="2305.16616 (v4 2025)",
         model="통신 채널을 ISAC 으로 확장 시 RCS 를 large-scale parameter 에 편입, Doppler 를 sensing geometry 로 확장해야 함을 정리",
         attach="Sionna 통신 RT 출력에 RCS·target-induced Doppler 를 별도 계층으로 추가하는 설계 원칙",
         value="⚠ 서베이라 **구체 RCS 수치·데이터 없음**. 방법론 정당화 인용용(제목·연도는 버전마다 다름)",
         kind="설계 근거(RCS 모델 아님)"),
]

# §5 — 해결 방식별 비교
#  cols: 방식 | 대표 | 물리정확도 | 계산효율 | Bistatic | Micro-Doppler | 장점 | 핵심 약점
COMPARISON = [
    ("외부 full-wave/PO RCS LUT", "LAMBDA", "높음", "LUT 생성 무거움·사용 빠름", "설정에 따라 가능", "회전각별 가능하나 매우 무거움", "표적 형상·재료·자세 반영", "상용 solver 또는 막대한 EM 계산 필요"),
    ("확장 Sionna reflectivity", "Ziganshin 2025/2026", "중상", "중상", "강함", "현재 제한적", "환경 RT 와 동일 프레임워크·오픈소스", "PEC·복합재료·micro-Doppler 한계"),
    ("측정기반 통계 RCS", "Azim·Unified RCS", "중간", "매우 높음", "측정 있으면 가능", "별도 모델 필요", "Monte Carlo·system-level 비교 적합", "복소 위상·세부 signature 상실"),
    ("Analytical point-scatterer RCS", "TGNN·CKM", "낮음~중간", "매우 높음", "가능", "불가능", "구현 가장 쉬움", "자세·extended target·분류 특성 없음"),
    ("Sionna mesh reflection 만", "CellSense·Great-X", "정량 신뢰도 낮음", "높음", "가능", "단순 움직임만", "빠른 feasibility", "실제 RCS·echo power 연결 어려움"),
    ("RCS 필요성만 언급", "SimART·(설계논문)", "평가 불가", "—", "—", "—", "개념적으로 올바름", "구현 재현성·정량 검증 부족"),
]

# §6 — 조심할 점
CAUTION_DOUBLE = ("**이중 계산 금지.** '드론 메시를 Sionna scene 에 넣어 반사경로 생성 **+** 같은 경로에 외부 RCS 를 "
                  "또 곱함' 은 Sionna material reflection 과 외부 RCS 가 같은 산란을 **중복** 반영한다. 올바른 구조는 "
                  "**표적 없는 배경(direct+clutter)** 과 **표적경유 채널**을 분리해 더하는 것:")
CAUTION_DOUBLE_EQ = ("h_{surv} = h_{direct} + h_{background} + h_{target}, \\quad "
                     "h_{target}(t,\\tau)=\\sum_{p,q} h^{(p)}_{T\\to D}(t)\\, s_D(f,\\Omega_i,\\Omega_s,R_D(t))\\, "
                     "h^{(q)}_{D\\to R}(t)\\, \\delta(\\tau-\\tau^{(p)}_{TD}-\\tau^{(q)}_{DR})")
CAUTION_SCALAR = ("**스칼라 RCS 만으론 위상이 없다.** 일반 RCS $\\sigma_b$ 는 전력 크기라, coherent 센싱(Range-Doppler·"
                  "Cross-Ambiguity 는 여러 경로가 복소수로 합쳐짐)에 필요한 산란 **위상**을 못 준다. 가장 좋은 데이터는 "
                  "단순 RCS 가 아니라 **복소 바이스태틱 산란행렬** $S_b=[[S_{\\theta\\theta},S_{\\theta\\phi}],"
                  "[S_{\\phi\\theta},S_{\\phi\\phi}]]$ 로, 산란위상·편파(co/cross)·aspect 의존 간섭·다중 산란중심의 "
                  "보강/상쇄 간섭을 보존한다. **⭐ 우리 SBR+PO 는 스칼라 RCS 가 아니라 복소장 $E$ 를 직접 내므로 이 지점에서 "
                  "LAMBDA(CADFEKO 크기 중심 설명)보다 앞선다.**")

# §7 — 문헌에서 드러난 패턴
PATTERNS = [
    ("패턴 1 — Sionna=환경, RCS=외부 모듈", "가장 일반적·타당. Sionna=environment propagation, RCS/reflectivity=target scattering, OFDM/radar=sensing signal 엔진. LAMBDA·TGNN·CKM·Graph Learning 이 정도차만 있을 뿐 이 구조."),
    ("패턴 2 — 단순 tracking 이면 point RCS 로 충분", "delay-Doppler peak 위치·연속성만 쓰는 추적은 표적을 점으로 봐도 알고리즘 비교 가능(TGNN). 단 결과는 지연/도플러·CFAR·데이터연관·추적비교로 **한정**되고, 실제 탐지거리·드론종류별 detectability·aspect fluctuation·micro-Doppler 분류·Wi-Fi/LTE/5G 절대성능 비교는 **불가**."),
    ("패턴 3 — Sionna mesh 만 쓴 연구는 정량 RCS 근거가 약함", "CellSense 는 USRP 실측으로 시스템 실용성은 강하나 target echo power 가 human RCS 로 보정됐다 보기 어렵고, Great-X·Montaner 도 clutter/채널 평가엔 적합하나 표적 절대 reflectivity 로 해석하면 안 됨."),
]

# §8 — 사용자(우리) 드론 패시브 센싱 권장 구조 (= sionna2 프로젝트와 일치)
RECOMMENDED_ARCH = [
    "Wi-Fi/LTE/5G waveform",
    "  ├─ Reference channel : Sionna RT",
    "  └─ Surveillance channel",
    "        ├─ Background : Sionna RT (direct + clutter)",
    "        └─ Drone target module",
    "              ├─ body RCS LUT       (자작 SBR+PO 복소장 → LUT)",
    "              ├─ bistatic geometry",
    "              ├─ attitude (roll/pitch/yaw)",
    "              └─ rotor micro-Doppler",
    "  → Complex surveillance I/Q",
    "  → ECA → CAF → CFAR → Tracking        (pyAPRiL)",
    "  → X410 calibration                    (sim-to-real)",
]
BODY_MODEL = ("동체: $s_{body}(f,\\theta_i,\\phi_i,\\theta_s,\\phi_s,\\text{roll,pitch,yaw})$ — 초기: 측정/문헌 기반 "
              "statistical bistatic RCS · 중기: openEMS/FEKO 제한 각도·주파수 LUT · 최종: X410 실측 amplitude scale 보정.")
ROTOR_MODEL = ("프로펠러: $h_{drone}(t)=h_{body}(t)+\\sum_{i=1}^{N_{blade}} h_{blade,i}(t)$ — Costa 등의 bistatic "
               "thin-wire multi-propeller 모델 적용이 가장 현실적.")

# §9 — 연구 공백 + 가장 가까운 문헌
GAP_TARGET = ("Sionna RT + open-source EM-derived UAV complex bistatic reflectivity + passive reference/surveillance "
              "channels + Wi-Fi/LTE/5G multi-illuminator 비교 + rotor micro-Doppler + SDR/USRP 실측 calibration — "
              "**이 모두를 만족하는 완전한 연구는 아직 없다.**")
GAP_NEAREST = [
    ("LAMBDA", "Sionna + CADFEKO UAV RCS", "상용 FEKO·능동 FMCW·passive reference channel 없음"),
    ("Sionna-RT Reflectivity (Ziganshin)", "오픈소스 Sionna 표적 reflectivity 확장", "차량·PEC 중심, rotor micro-Doppler 없음"),
    ("CellSense", "실제 passive cellular sensing + USRP", "explicit/calibrated RCS 모델 없음"),
    ("Costa et al.", "측정 검증된 bistatic drone micro-Doppler", "site-specific Sionna 환경과 직접 결합 안 함"),
    ("TGNN", "Sionna + point bistatic RCS + tracking", "실제 UAV extended scattering 없음"),
]
OUR_POSITION = ("우리(sionna2)는 **Sionna 기반 site-specific passive 채널** + **자작 SBR+PO 로 계산한 UAV bistatic "
                "복소 reflectivity**(스칼라 아님)를 (c) 방식으로 주입하고, **동일 조건에서 Wi-Fi/LTE/5G 탐지·추적을 "
                "비교**한 뒤 **X410 실측으로 calibration** 한다. 표적 RCS 계산은 (d) 자작 SBR+PO, 채널결합은 (c) — "
                "위 §9 공백을 정면으로 겨냥한다. 특히 §6 의 복소 산란행렬 요구를 우리 SBR+PO 복소장이 충족한다는 점이 "
                "LAMBDA(CADFEKO 크기 중심) 대비 차별점이다.")

# §10 — 우선순위 읽기 + 한 문장 요약
PRIORITY = [
    ("LAMBDA", "Sionna + 외부 UAV RCS 결합의 가장 직접적인 예"),
    ("Ziganshin — Discretized Curved Bodies", "Sionna 자체 산란 모델 확장의 핵심(A2)"),
    ("TGNN", "point-scatterer RCS 를 Sionna CIR 에 삽입한 구조(B)"),
    ("Statistical & Deterministic RCS Characterization", "측정 기반 bistatic UAV RCS 모델"),
    ("Micro-Doppler of Multi-Propeller Drones", "드론 프로펠러의 bistatic OFDM micro-Doppler"),
    ("CellSense", "explicit RCS 없이 상대·차분 센싱과 실측으로 우회한 사례(C)"),
]
ONE_LINER = ("Sionna 기반 센싱 문헌은 RCS 문제를 **외부 EM solver · 측정/통계 RCS · point-scatterer 모델 · Sionna "
             "자체 diffraction 확장 · 상대적 mesh-reflection 처리** 중 하나로 해결해 왔으며, **실제 물리적 탐지성능을 "
             "주장하려면 앞의 세 방식(A1·A2·B) 중 적어도 하나가 필요하다.**")

METHOD = ("3중 워크플로(다각도 웹서치 → 논문별 적대적 검증, 총 60여 에이전트) + 사용자 제공 타 LLM 조사 대조. "
          "모든 논문 1차 출처(arXiv/IEEE/DOI) 확인. 타 LLM 항목 중 검증 실패 2건·과장 3건은 제외·정정(위 기록).")
