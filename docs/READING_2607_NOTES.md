# 2607 논문 3편 정독 노트 — 교수님 각도(RCS 단순화·환경 리얼리스틱·디텍션)로 정리

> 정독 대상: `team_meeting/2607/` 3편 (Clutter-Aware 서베이 41p·OpenISAC 15p·Montaner 5p). 2026-07-25 정독.
> **핵심 결론(먼저):** 3편 모두 교수님 방향(RCS 단순화 + 환경 리얼리스틱 + 디텍션)에 놓여 있고, **셋 다 "디텍션 판정(CFAR/Pd)"에서 멈추거나 우리와 다른 세팅**이다 → **우리 wedge = 리얼리스틱 RT 환경 + 단순화 RCS 위에서 "패시브 바이스태틱 디텍션(CFAR/Pd)"**. 이게 셋의 공백을 정확히 메운다.

## 0. 한 눈에 (교수님 3요소 × 3편)

| 논문 | 베뉴 | RCS 처리 | 환경 리얼리즘 | 디텍션 판정 | 기하 | 우리와의 관계 |
|---|---|---|---|---|---|---|
| **Clutter-Aware 서베이** | Proc. IEEE Jan 2026 | 스칼라 반사계수(σ²c), 산란적분 없음 | ★강(통계 + **Sionna RT** 케이스) | **GLRT+CFAR(이론O·공개코드X)** | **모노**(바이스태틱은 Remark만) | 우리 클러터 모델·죽은파라미터의 **이론 원장** |
| **Montaner RF-DT** | EuCAP 2026 | **RCS 모델 아예 없음**(메쉬+재질산란) | ★강(**Sionna RT** 디지털트윈) | **없음**(delay-Doppler 맵 매칭만) | 모노+바이 | RT 환경 **템플릿**, 디텍션은 우리 몫 |
| **OpenISAC** | IEEE IoT-J 2026 | (실측이라 N/A) | 실외 실측(USRP) | **없음**(peak-pick, CFAR無) | 모노+바이(**협조**) | X410 실측 **엔지니어링** 이식원 |

> 교수님 각도를 완주하는 논문은 없다. Clutter 서베이=모노·단일파형, Montaner=디텍션無·차량·79GHz, OpenISAC=능동협조·CFAR無. **패시브 바이스태틱 + 디텍션 + 리얼 RT 환경**은 셋의 교집합 공백이다.

---

## 1. Clutter-Aware ISAC 서베이 (Proc. IEEE 114(1):52-89, 2026, Liu/Li/Li/Swindlehurst)

**무엇:** 모노스태틱 MIMO-OFDM ISAC 클러터 서베이. 공개코드 MATLAB `github.com/LS-Wireless/Clutter-Aware-ISAC-Tutorial`(RDM·MTI·MVDR·STAP·co-design; **GLRT/CFAR/Sionna씬 코드는 미포함**).

**택소노미(핵심):** cold vs hot — 판별자 = "조명파형이 수신단에서 제어·기지인가".
- **cold**(self-echo·slow-time·coherent·준정상·derandomizable): *"It can nevertheless exhibit Doppler spread when the receiver and scatterers are in relative motion."* ← **우리 도플러퍼짐 발견의 직접 훅.**
- **hot**(외부 방출체 산란간섭·fast-time·비협조·비정상): 표적경유 바닥유령이 정확히 이것.

**모델:** 진폭분포(Rayleigh/LogN/Weibull/K), 가우시안 공분산, GIT 지면반사, SIRV/복합가우시안, 구조화공분산(Kronecker/Toeplitz/저계수/STAR), **파형독립 내부커널 Vᶜᶜ=Σ σ²c·v(θ,f_D)v(·)ᴴ**(씬만 학습→어떤 파형이든 예측), **Sionna RT 케이스**(BS 13.5m·표적 10-15m·max_depth=3·단순화 Blender 메쉬).

**방법:** AoA→angle gating→derandomization→2D-DFT RDM→**GLRT→CFAR**. slow-time(MTI/RMA ρ≈0.99/CSD — 전부 f_D≈0만 노치), 공간(**subspace projection ≈ ECA**), **STAP/SFTAP**, KA+ML(CKM 프리널링).

**검증된 수치:** SCNR Fig.4 **cold-only −45.9 dB** · Fig.5 mixed −47.4 · Fig.7 **Sionna RT mixed −63.5** · Fig.2 −47.4. ⚠**"16 dB RT 페널티"는 Fig.5−Fig.7 유도값**(축자 아님) — "리얼 RT 다중경로가 통계모델보다 SCNR ~16 dB 낮춤".

**우리와의 정합(강함):**
- 우리 stochastic 클러터(C=100 iso-Rb 링 ±1 m/s)가 **그들의 정확히 같은 모델**(독립 도달) = 우리 verify 모듈 설계의 외부 검증.
- 우리 ECA **"죽은 파라미터=0-도플러 항등식"**을 그들 **Eq.112**가 일반화: slow-time 백색이면 *"Doppler discrimination cannot be achieved using second-order statistics alone"*. → 상대운동 도플러퍼짐 없으면 도플러 소거기가 작용할 대상이 없다(이론 원장).

---

## 2. Montaner RF-DT (EuCAP 2026, arXiv:2603.28736, UPV iTEAM)

**무엇:** 능동 **FMCW 79GHz** 채널사운더 실측 vs **Sionna RT 디지털트윈** 비교. 센싱 태스크 = delay-Doppler/PDP 맵 **재현**(디텍션 아님). 표적=**차량**(Nissan Micra/KIA Xceed).

**우리 사전판단 4개 전부 CONFIRMED(원문):** delay-Doppler 매칭 · 능동 FMCW(12dBm·79GHz·4GHz BW) · 비패시브("passive"/"opportunity" 0회) · 디텍션 판정 없음("detection"/"CFAR"/"Pd" 0회). **추가:** RCS 모델 아예 없음("RCS"/"PO"/"SBR" 0회) — 표적=메쉬+재질산란(R²+S²=1, 방향성 diffuse lobe).

**핵심 이식점:**
- **Sionna RT는 delay·power만, Doppler 안 줌** → 광선 시선속도로 도플러를 후처리 합성(§II.F). ← 우리 정적 RT 경로 → 이동 드론 delay-Doppler 큐브의 다리(파형무관).
- 재질별 diffuse S(glass/concrete/metal/brick), specular+1차 diffuse만(깊은 다중반사 없음).

**한계:** 정량검증 빈약(맞춘 봉우리 **단 1개**: 2.1 m/s·62 ns), 나머지 눈대중. 차량·79GHz(many-λ) → **드론 few-λ 미검증**(우리 메모: 스톡 Sionna는 소형표적 RCS 부족). "표적=메쉬·RCS엔진無" 단순화는 드론에 자동 이전 안 됨.

---

## 3. OpenISAC (IEEE IoT-J 2026, DOI 10.1109/JIOT.2026.3710751, SEU/PML)

**무엇:** **능동 협조** OFDM-ISAC 실시간 테스트베드(BS가 자기 파형 송신). 공개 `github.com/zhouzhiwen2000/OpenISAC`(라이선스 미명시—repo 확인 필요). Host C++/UHD, FPGA無.

**하드웨어:** *"from the cost-effective USRP B200 series to the high-performance X400 series"* → **X410 지원 주장(단 UHD 호환 주장, 실증은 X310/B210)**. 실증: 3.1GHz·50MHz·Mavic Air 3S 실외. **>100-200MHz서 host-only 실시간 붕괴**(X410 400MHz 경고).

**중요 차이:** 능동 협조(파형 기지/재구성) ≠ 우리 패시브(비협조 조명·CAF). 클러터=**IIR-MTI**(ECA 아님). **디텍션=peak-pick, CFAR/Pd 없음**. Sionna(우리)를 *"communication-system simulation... rather than a complete end-to-end ISAC sensing pipeline"*로 인용 = 우리 디텍션 작업이 메우는 공백을 정확히 지적.

**X410 실측 이식 리스트:** ① **OTA 동기 파이프라인**(Quinn 소수지연+LS SIO회귀+재귀추적) — 분리된 ref/surv 노드의 클록 비동기(우리 실측이 겪을 실패모드) 정면 대응 ② **MSR 지표**(MTI 전후 에너지, 클록오차 스윕 ±0.25ppm→10-14dB) — 우리 ECA 소거품질 정량보고 ③ **demod-and-reconstruct 레퍼런스**(복호가능 5G/WiFi에 raw-CAF 상위호환) ④ IIR-MTI 저비용 실시간 노치 ⑤ 마이크로도플러 STFT 템플릿(Mw=256/MH=64) ⑥ 실시간 벤치마킹 계측 ⑦ 시작 파라미터셋.

---

## 4. 교차 종합 — 우리 wedge (교수님 각도 완주)

세 논문이 각자 남긴 공백을 우리가 정확히 메운다:

| 공백(그들이 안 한 것) | 우리가 메움 |
|---|---|
| Montaner: 디텍션 판정 없음(맵 매칭만) | **검증된 RT 트윈 위에 CFAR/Pd 디텍션** |
| OpenISAC: CFAR/Pd 없음(peak-pick)·능동협조 | **CFAR + 검출확률** · **패시브(더 어려움)** |
| Clutter 서베이: 모노·단일파형·바이스태틱은 sketch만 | **패시브 바이스태틱** 클러터 케이스(Sionna, 미개척) |

→ **우리 포지션 = "리얼리스틱 Sionna-RT 환경 + 단순화 스칼라 RCS + 패시브 바이스태틱 + 실제 CFAR/Pd 디텍션."** 교수님 3요소를 전부 완주하는 유일 조합이고, 3편 어디도 안 한 지점이다.

## 5. 우리 결과 대조 (apples-to-apples + 회의적 caveat)

- **SCNR:** 우리 hot-clutter cold-only **−45.67 dB ≈ 서베이 Fig.4 −45.9 dB**. ⚠**"같은 레짐"이지 정밀 교차검증 아님** — 서베이는 28GHz·16×16·C=100·N·L≈131k 셀, **입력·단일RD셀·전처리전** SCNR 정의. **우리 SCNR 정의가 그것과 같은지 확인 후에만 "≈" 인용**(우리가 후처리/바이스태틱이면 우연).
- **죽은 파라미터:** 우리 경험발견 = 서베이 Eq.112 이론(2차통계로 도플러 판별 불가)의 특수사례 → **이론 원장으로 인용 가능**.
- **per-illuminator SCR span(5G 6.7·WiFi 44.8·LTE 17.3 dB):** 서베이에 대응물 없음(단일파형 MIMO) → **우리 고유 기여**, 서베이 지지 주장 금지.
- **16 dB stochastic→RT 페널티:** 우리의 최강 이식 벤치마크. report13(자유공간) → 미래 Sionna-클러터 리포트가 유사 두자릿수 SCNR 낙차 보이면 **Proc.IEEE 벤치마크와 apples-to-apples 대조**(둘 다 Sionna RT·UAV).

## 6. 다음 단계 차용 리스트 (report13 이후 "리얼 환경 디텍션")

1. **3항 신호모델 + 내부커널 채택**: `y=표적+cold+hot+noise`(서베이 Eq.8), 씬 커널 `Vᶜᶜ` 한 번 학습→파형별 예측. **RCS는 스칼라 σ²c로 단순화**하고 환경을 리치하게 = 교수님 각도 정확.
2. **헤드라인 검출기를 ref-only 정합필터 → STAP(최소 MVDR+slow-time)로**, SCNR 이득 보고. 서베이 중심 메시지 = 1D slow-time(우리 ECA 계열)은 도플러퍼짐 cold+hot에 불충분, 2D STAP이 복원(RMB `Ntr≥2D`·감축계수).
3. **stochastic-vs-RT SCNR 대조를 다음 리포트에**(서베이 Fig.5 vs Fig.7 미러): 같은 씬을 (a) C≈100 링 ±1m/s (우리 보유) (b) Sionna RT max_depth=3 로 두 번 → SCNR 델타. ~10-16 dB 재현이면 Proc.IEEE 벤치 검증, 아니면 그 자체가 발견(바이스태틱·반무향·조명원 선택).
4. **hot clutter를 표적경유/방출체 다중경로로 명시 모델**(서베이 Eq.71-72): 우리 "바닥유령→5G 100% 오검출"의 형식 동반.
5. **Montaner의 Doppler-from-ray-velocity 합성 + CIR→STFT 형식**(Eqs.3-8): Sionna RT 정적경로 → 이동 드론 delay-Doppler 큐브. 파형무관(chirp→통신프레임).
6. **X410 실측: OpenISAC OTA 동기·MSR 지표·demod-reconstruct 레퍼런스**(§3 이식리스트).
7. **택소노미로 챔버/필드 프레이밍**(서베이 Table 2): 챔버≈Indoor(sparse/parametric), 필드≈UAV/Aerial(hybrid geometric-statistical).

## 7. 회의적 caveat (팀 공유용)
- 모든 SCNR "≈"·"16 dB"는 **씬·정의 민감** — 정의·파라미터 병기 필수.
- 서베이 공개코드에 GLRT/CFAR/Sionna씬 **없음** → 그 부분은 식(Eq.34 GLRT·ref[49] CFAR)에서 재유도.
- Montaner 정량검증 빈약(봉우리 1개), 차량·79GHz — 드론·우리밴드로 **방법만** 차용.
- OpenISAC 바이스태틱은 **협조**(기지파형) → "OpenISAC 바이스태틱 UAV 검출 대등" 주장 시 우리는 더 어려운 **패시브**임 명기.

---
*원문 캐시: OpenISAC/Montaner/Clutter 전문 추출본은 세션 scratchpad·tool-results 에 있음. 파일: `team_meeting/2607/*.pdf`.*
