# 선행연구는 Sionna 의 «솔버 스위치» 를 어떻게 뒀다고 밝혔나

> 조사일 2026-08-12 · 대상 = 보관함 PDF 373편 전수 스캔 + 원문 확인
> 기계가 읽는 판: `outputs/survey_sionna_solver_settings.json`

---

## 0. 말 먼저 풀기

이 글에서 **«솔버 스위치»** 라고 부르는 것은, 레이트레이싱(ray tracing, 전파를 광선 다발로 보고
장면 안에서 튕겨 다니게 하는 계산법) 도구에게 **"어떤 물리 현상까지 계산할래?"** 를 켜고 끄는
설정값들이다. Sionna 에서는 이렇게 생겼다.

| 스위치 | 뜻 (쉬운 말) |
|---|---|
| `max_depth` | 광선 하나가 최대 몇 번까지 부딪히게 둘 것인가 (1이면 직진·1회 반사까지) |
| `specular_reflection` | 거울처럼 반듯하게 튕기는 반사를 셀 것인가 |
| `diffuse_reflection` | 거친 면에서 사방으로 흩어지는 반사를 셀 것인가 |
| `refraction` | 물체를 **뚫고 지나가는** 성분을 셀 것인가 (플라스틱 껍데기 투과) |
| `diffraction` | 모서리를 **감돌아 나가는** 성분을 셀 것인가 |
| `edge_diffraction` | 그중에서도 «떠 있는 모서리»(free floating edge)에서의 회절 |
| `samples_per_src` (구버전 `num_samples`) | 송신점에서 광선을 몇 개나 쏠 것인가 |

이 스위치 하나를 바꾸면 결과가 수십 dB 씩 달라진다. 그래서 **논문이 이걸 적어 놓았는가** 가
재현 가능성의 핵심이다. 이 조사는 그걸 세어 본 것이다.

---

## 1. 결론 요약

1. **밝힘 비율은 낮다.** Sionna RT 를 실제로 돌린 논문 **89편 중 17편(19%)** 만이
   깊이·메커니즘·광선수를 **셋 다** 적어 재현이 가능하다. **36편(40%)은 솔버 설정을 하나도 안 적는다.**
2. **가장 많이 빠지는 건 «광선 수».** 깊이는 41편(46%), 메커니즘 on/off 는 41편(46%) 이 적지만,
   광선/샘플 수는 **22편(25%)** 만 적는다. 소형 표적일수록 이게 제일 중요한데도 그렇다.
3. **스위치를 바꿔 가며 «수치로» 비교한 논문은 5편뿐이다.** 그리고 그 5편의 관측량은 전부
   **환경 채널**(경로손실·라디오맵·측위·방향탐지)이지 **표적 산란**이 아니다.
   즉 **«회절/굴절 스위치가 표적 후방산란을 몇 dB 바꾸는가» 를 보고한 선행연구를 우리는 찾지 못했다.**
4. **표적을 다루는 논문일수록 더 안 밝힌다.** 드론·RCS·마이크로도플러 쪽 11편 중 A등급은 1편뿐이다.
   우리 과제와 **가장 가까운 논문**(멀티로터 UAV 마이크로도플러 × Sionna RT)은
   본문에 `diffraction`·`refraction`·`depth` 라는 낱말이 **0회** 나온다.
5. **버전이 함정이다.** Sionna **1.0~1.1 에는 회절 기능이 아예 없었다**(기본값 off 가 아니라 부재).
   1.2.0 에서 되돌아왔다. 따라서 "회절을 안 썼다" 는 서술은 시기에 따라 **선택**일 수도, **불가능**일 수도 있다.
6. **공식 문서도 모범을 보이지 않는다.** Sionna 2.0.1 대표 튜토리얼은 `diffraction` 인자를 아예 안 넘기고
   (→ False), 왜 그렇게 뒀는지·바꾸면 뭐가 달라지는지 **설명하지 않는다.**

---

## 2. Sionna 의 기본값 — 설치본에서 직접 확인

`/workspace/.venvs/py312/lib/python3.12/site-packages/sionna/rt/path_solvers/path_solver.py`
(sionna 2.0.1) 의 `PathSolver.__call__` 서명을 그대로 읽었다. 공식 문서와도 대조해 일치를 확인했다.

```python
max_depth: int = 3
max_num_paths_per_src: int = 1000000
samples_per_src: int = 1000000
synthetic_array: bool = True
los: bool = True
specular_reflection: bool = True
diffuse_reflection: bool = False
refraction: bool = True          # ← 기본이 켜짐
diffraction: bool = False        # ← 기본이 꺼짐
edge_diffraction: bool = False
diffraction_lit_region: bool = True
seed: int = 42
```

### 우리 설정과 무엇이 다른가

| 스위치 | Sionna 기본값 | 우리 앙각 실험 | 차이 |
|---|---|---|---|
| `max_depth` | **3** | **1** | ✅ 다름 |
| `refraction` | **True** | **False** | ✅ 다름 |
| `diffraction` | False | 미전달(False) | 같음 |
| `edge_diffraction` | False | 미전달(False) | 같음 |
| `diffuse_reflection` | False | 미전달(False) | 같음 |
| `los` / `specular_reflection` | True | True | 같음 |

**즉 우리는 기본값에서 두 군데를 벗어나 있다** — 깊이를 3→1 로 줄였고, 굴절을 켬→끔 으로 바꿨다.
나머지는 기본값 그대로다. (특히 `diffraction=False` 는 우리가 «선택» 한 게 아니라
Sionna 가 원래 꺼서 주는 값이다.)

### 공식 튜토리얼이 쓰는 값

`Introduction to Sionna RT` 튜토리얼의 실제 호출은 이렇다.

```python
paths = p_solver(scene=scene, max_depth=5, los=True,
                 specular_reflection=True, diffuse_reflection=False,
                 refraction=True, synthetic_array=False, seed=41)
```

`diffraction` 은 **인자 목록에 아예 없다.** 튜토리얼이 주는 유일한 설명은
"`max_depth` 는 광선과 물체의 최대 상호작용 횟수" 라는 한 줄이고,
**이 값을 바꾸면 무엇이 달라지는지에 대한 논의는 없다.**

### 버전사 — 회절은 한동안 «없었다»

| 버전 | 사건 |
|---|---|
| 0.14 | Sionna RT 최초 공개 |
| **0.15** | **회절·확산반사 추가** |
| 0.17 / 0.18 | 이동성 / RIS |
| **1.0.0 ~ 1.1.x** | 전면 재작성. **회절 기능이 통째로 사라짐** (기본값 off 가 아니라 부재) |
| **1.2.0** | **회절 재도입** |
| 2.0.1 | 우리가 쓰는 버전 |

근거: Sionna RT 기술보고서(arXiv 2504.21719) 원문 + NVlabs/sionna GitHub Discussion #838.
관리자 답변 인용 — *"support for diffraction will be added in a future release"* (faycalaa),
*"diffraction support was added back in version 1.2.0"* (merlinND).

> ⚠ 이건 서베이 읽을 때 반드시 챙겨야 한다. **Sionna 1.0~1.1 을 쓴 논문은 회절을 켜고 싶어도 켤 수 없었다.**
> 그 시기 논문의 «회절 무언급» 을 «게으름» 으로 읽으면 틀린다.
> 또한 v0.x 는 API 자체가 달랐다 — `scene.compute_paths(max_depth, num_samples, los, reflection,
> diffraction, edge_diffraction, scattering, scat_keep_prob, ...)` 이고 **`refraction` 인자가 없다.**
> (v0.x 서명은 공식 문서 예제·GitHub 이슈로 확인했고, 소스 직접 확인은 아니다 — **부분 확인**.)

---

## 3. 밝힘 비율 — 숫자

### 조사 방법과 모집단

```
보관함 PDF 373편  (/data/public/sionna_jeong + prior_work/pdfs)
  └ PyMuPDF(fitz) 로 전문 텍스트 추출
     └ 'sionna' 언급 197건 → 내용 해시로 중복 제거 → 144편
        └ 'Sionna RT / ray tracer / ray tracing 모듈' 강한 신호 → 92개 파일
           └ 논문 아닌 것 1건 + 같은 논문의 중복판 2건 제외 → 조사 대상 89편
```

각 편을 3축으로 채점했고, **정규식 자동 채점 결과를 사람이 원문 문맥을 읽어 오탐·미탐을 고쳤다**
(고친 건 JSON 의 `hand_checked: true` + `note` 로 남겼다).

- **깊이**: 자기 실행의 `max_depth`(=반사 차수·상호작용 깊이) **값을 숫자로** 적었나
- **메커니즘**: 회절·굴절·확산반사·정반사 중 무엇을 켜고 껐는지 **자기 실행에 대해** 적었나
  (— "레이트레이싱은 반사·회절·산란을 모델링한다" 같은 **도구 일반 소개는 제외**했다)
- **광선 수**: `num_samples`/`samples_per_src`/발사 광선 수를 **숫자로** 적었나

### 결과

| 등급 | 뜻 | 편수 | 비율 |
|---|---|---|---|
| **A** | 3축 모두 — 재현 가능 | **17** | **19.1 %** |
| **B** | 1~2축만 — 부분 | 36 | 40.4 % |
| **C** | 하나도 안 밝힘 | **36** | **40.4 %** |

축별로 보면:

| 축 | 밝힌 편수 | 비율 |
|---|---|---|
| 깊이(`max_depth`) | 41 | 46 % |
| 메커니즘 on/off | 41 | 46 % |
| **광선/샘플 수** | **22** | **25 %** |

> **읽는 법**: A 17편 안에는 NVIDIA 자신의 문서 2편(Sionna RT 창설 논문, 기술보고서)이 들어 있다.
> 그걸 빼면 **제3자 논문 중 A 는 15편(17%)** 이다.

---

## 4. 표 — 논문별

### 4.1 A등급 (깊이 + 메커니즘 + 광선수, 전부 밝힘) — 17편

| # | 논문 | Sionna 버전 | 밝힌 것 | 원문확인 |
|---|---|---|---|---|
| 1 | **Sionna RT 창설 논문** (arXiv 2303.11103) | (무기재) | 코드 리스팅 `compute_paths(max_depth=3, diffraction=True)`, Fibonacci 격자 광선 | ✅ |
| 2 | **Sionna RT 기술보고서** (arXiv 2504.21719) | 0.19.2 / 1.x | 실험별로 "확산·정반사·굴절·회절 모두 켜고 L=5", "N_S=1e6, 확산반사 끔, 회절 켬" 등 | ✅ |
| 3 | Manukyan et al., *Limitations of RT for Learning-Based RF Tasks* (2507.19653) | **1.0.2** | **표 I 에 Sionna 기본값과 자기 값을 나란히** (아래 §5.1) | ✅ |
| 4 | Saribekyan et al., sim2real positioning (2607.04400) | 1.2 | 깊이 5, 정반사+확산반사+굴절+LoS 전부 켬, 광선 1e6/소스, 경로 1e4/소스, TR 38.901 패턴 | ✅ |
| 5 | Tadik et al., OpenGERT (2501.06945) | (무기재) | "LOS, 반사 5회까지, 회절 + 모서리회절, **산란 없음**, 100만 샘플" — 한 줄에 전부 | ✅ |
| 6 | Geo2SigMap (2312.14303) | 0.15.1 | 표: Reflection Enabled / Diffraction Enabled / 최대 8 bounces / 총 광선 7,000,000 | ✅ |
| 7 | BostonTwin (2403.12289) | (무기재) | 표: Reflection ✓ / Refl. Order 3 / **Diffraction ✓ / Scattering ✗** / Launch Rays 1e6 / Fibonacci | ✅ |
| 8 | WiSegRT 실내 데이터셋 (2312.11245) | (무기재) | 표: Maximum Interaction 4 / Num. of Ray Launched 100,000 + **산란을 왜 뺐는지 Rayleigh 기준으로 정당화** | ✅ |
| 9 | Open Wireless DT (OAI+Sionna RT) (2503.12177) | 0.18.0 | `max_depth = 5`, `diffraction=True` 이며 **"회절은 경로당 1회, 반사와 겸하지 않는다"** 는 동작까지 서술 | ✅ |
| 10 | Beyraghi, Reconfig. Intelligent BS (2507.08611) | (무기재) | 표: Fibonacci SBR / **Activated ray types: LOS, specular-reflection, diffraction** / 광선 16×1e6 / 4 bounces | ✅ |
| 11 | Beyraghi, site-specific RIS deployment (2510.09478) | (무기재) | 1e7 광선/셀, 4 bounces, 정반사+회절+산란 | ✅ |
| 12 | Beyraghi, data-driven RIS deployment (2510.10190) | (무기재) | 표: Ray types = 정반사·회절·산란 / 1e7 광선/셀 / 최대 4 bounces | ✅ |
| 13 | Beyraghi, site-specific MIMO diffusion (2606.20098) | (무기재) | 5×1e6 광선, 3 bounces, LoS+정반사+회절 | ✅ |
| 14 | Zhou et al., fidelity of site-specific DT (2605.08772) | (무기재) | 표: Samples per Tx 1e6 / Max interaction depth 3 / **Enabled propagation effects: LoS, specular reflection** | ✅ |
| 15 | Makvandi et al., AdaPTwin 다중충실도 DT (2605.21897) | **2.0.1** | **스위치를 «충실도 손잡이» 로 대놓고 다룸**: 깊이 3/6/10, 광선 1e3/1e4/1e10, 회절·확산반사 불리언 | ✅ |
| 16 | Shabanpour et al., physically consistent RIS (2409.17738) | (무기재) | "6 bounces, 1e7 random rays, LoS+반사+산란+회절" | ✅ |
| 17 | Wang et al., Neural ISAC MIMO-OFDM (2509.21118) | (무기재) | 경로샘플 1e5, 최대깊이 5, 반사·산란·회절 모두 고려 — **ISAC 쪽에서 유일한 A** | ✅ |

### 4.2 B등급 대표 (부분만 밝힘) — 36편 중 발췌

| 논문 | Sionna | 밝힌 것 | **안 밝힌 것** | 원문확인 |
|---|---|---|---|---|
| Clutter-Aware ISAC (Proc. IEEE, 2602.10537) | (무기재) | 상호작용 깊이 3 | 회절·굴절·확산반사·광선수 | ✅ |
| S-ICDF 간섭 데이터셋 (2607.03411) | (무기재) | Reflection depth 5(2/5/7 스윕), Refraction True/False 스윕 | 광선수, 확산반사, 회절 | ✅ |
| AirMap (2511.05522) | **1.2.1** | 깊이 2~20 스윕, 회절 켬/끔 | 광선수, 굴절, 확산반사 | ✅ |
| Schepens et al., sub-THz radiostripe (2604.14869) | 1.2.1 | 깊이 5, LoS 켬, 정반사+굴절 켬, **확산산란 끔** | 광선수, 회절 | ✅ |
| Yao et al., RF-DT RGB+LiDAR 28 GHz (2606.01261) | (무기재) | 깊이 8, 모서리회절+산란 켬, 경로종류 LOS/정반사/확산/굴절 | 광선수 | ✅ |
| Pegurri et al., VaN3Twin V2X (2505.14184) | **1.2.0** | 표: Reflections Specular+Diffused / **Refractions Yes** / Max Interactions 5(→3) | 광선수, 회절 | ✅ |
| Zhang et al., OneTwin (2601.03216) | 0.18.0 | 깊이 2, **"반사는 켜고 회절·산란은 끈다"** 고 명시 + 이유(정확도/비용 절충) | 광선수, 굴절 | ✅ |
| Hoydis et al., Learning Radio Environments (2311.18558) | (무기재) | 정반사 5차까지 + 1차 회절, **"굴절은 완전히 무시했다"** 고 한계로 자백 | 광선수 | ✅ |
| Ziganshin et al., 곡면체 산란 (2604.05991) | 0.19 | 회절 기법(UTD·정점회절·이중에지회절)을 상술 | — 단 이건 **스톡 스위치가 아니라 자기들이 커널을 고친 것** | ✅ |
| Ropitault et al., site-specific ns-3 (2508.04004) | (무기재) | "회절 포함 + 정반사 4차까지" | 광선수, 굴절, 확산반사 | ✅ |
| RadarTwin (2606.28396) | (무기재) | "up to four bounces" (경험적으로 정했다고 밝힘) | 회절·굴절·산란·광선수 | ✅ |
| Luo et al., DT calibration (2603.16126) | 0.19.2 | 반사 6 / 회절 1, 확산산란 켬 | 광선수 | ✅ |
| Ali et al., GenAI DT interference (2607.08141) | (무기재) | "LoS, 반사 5 bounces, 회절, 확산산란" | 광선수 | ✅ |
| Amatare et al., DT radar robot nav (2411.12284) | (무기재) | `max-depth = 5`, `num-samples = 200` ← **광선 200개** | 회절·굴절·산란 | ✅ |
| Mao et al. / Multimodal (2603.15093, 2511.03220) | (무기재) | 표: Ray Samples Launched 1e6, **Maximum Reflection Order 1** | 회절·굴절·산란 | ✅ |
| Kang et al., VLM material estimation (2601.18242) | (무기재) | 광선 5000개, RT 깊이 D=4, **깊이 어블레이션 표 있음** | 회절·굴절·산란 | ✅ |
| Ceresoli et al., AoA services 5G (2510.17342) | (무기재) | 반사 차수 1/3/5 를 쓸어가며 비교 | 회절·굴절·산란·광선수 | ✅ |
| DeepTelecom 데이터셋 (2508.14507) | (무기재) | "최대 상호작용 깊이 N_max 를 둔다" — **기호만, 값 없음** | 값 전부 | ✅ |
| Ray-Based Multistatic Scattering in ISAC | (무기재) | UTD 쐐기회절 구현을 언급 | 자기 실행의 스위치값 | ✅ |
| dt-channel-gen toolchain (2606.14114) | (무기재) | `synthetic_array=False`(근거리)/`True`(원거리) 를 명시 | 깊이·회절·굴절·광선수 | ✅ |

### 4.3 C등급 (솔버 설정을 하나도 안 밝힘) — 36편

> **이 행들이 결론의 일부다.** 아래는 전부 원문을 열어 확인했다.

**표적·센싱 쪽 (우리와 가까운 것들)**

| 논문 | 왜 C 인가 | 원문확인 |
|---|---|---|
| **Li et al., *Micro-Doppler Signature Simulation of Multirotor UAVs Using Ray Tracing*** (IEEE) | ⭐**우리 과제와 가장 가까운 논문.** 전문에 `diffraction` 0회, `refraction` 0회, `depth` 0회. 표 I "**RT Parameters**" 에 적힌 건 파형(OFDM)·심볼수 2048·심볼길이 50 µs·로터 1개·블레이드 2장·반경 10.55 cm·재질 Wood 뿐 | ✅ |
| LAMBDA 저고도 UAV 멀티모달 데이터셋 (2607.03826) | Sionna RT 로 CSI 를 뽑는다고만 함 | ✅ |
| 저고도 협력 큐브 CSI (2605.07623) | "PathSolver 로 경로를 얻는다" 한 줄 | ✅ |
| Great-X Unreal ISAC (2507.08716) | 반사·굴절·산란 **수식**은 길게 유도하는데 **자기 실행의 스위치값은 없음** | ✅ |
| SimART (2605.13309) | 메쉬 단순화가 "정반사·모서리회절 경로에 영향이 적다" 고 **정성적으로만** 논함 | ✅ |
| DMSNet 교차대역 ISAC (2607.17655) | 무기재 | ✅ |
| CellSense (2606.07900) | 무기재 | ✅ |
| RayLoc (2501.17881) | SBR 개념 설명만("깊이 t_max 안에서"), 값 없음 | ✅ |
| Qiao et al., WiSER scene encoder (2606.04770) | ⚠ "켠 전파 메커니즘·최대 상호작용 깊이는 **데이터셋 메타데이터에 저장된다**" 고 적고 **본문엔 값을 안 씀** | ✅ |
| Xu et al., fingerprint positioning (2509.01197) | 도구 소개 상용구뿐 | ✅ |
| Delmoro et al., site geometry calibration (2607.09334) | 도구 소개 상용구뿐 | ✅ |

**그 밖 (통신·수신기·데이터셋 쪽)** — Sionna 라이브러리 창설 논문(2203.11854), DUIDD(2212.07816),
Yassine mbDL(2312.02239), PyJama(2407.15473), Wiesmayr NRX(2409.02912), Güneşer RIS(2501.05817),
Karakoca neural OFDM(2503.20500), Zhu real-time LoS(2505.15478), Wang codebook CKM(2505.16132),
Jia LEO(2601.15557), Iudice SIM(2601.20795), Amorosa GNN(2603.13094), Barker AtlasRAN(2603.14661),
Stenhammar NDT(2604.12888), Aboushehada WiFi8(2604.13500), Karakelle RIS DT(2604.17929),
MARL PRB(2605.02149), ARIADNE(2605.29772), Mefgouda LLM DT(2606.12293), Jiang CSI-CLIP(2606.25714),
Kim WiFi-JEPA(2607.11064), Tarazona SetGAN(2607.11429), Giovannini URLLC(2607.13692),
ns3-meets-Sionna(2412.20524), Chege beam selection(2504.05035), Zhu in-vehicular DT(2511.07789) 등.

---

## 5. 스위치를 «수치로» 비교한 5편 — 우리가 실제로 비교할 수 있는 유일한 것들

### 5.1 Manukyan et al. (arXiv 2507.19653) — 가장 중요한 대조군

Sionna **v1.0.2**, 로마 도시 시나리오, 실측 RSSI 대비 상관 + kNN 측위 오차.
**표 I 을 통째로 옮기면** (이 표가 Sionna 기본값을 명시한 유일한 제3자 논문이다):

| 변수 | 파라미터명 | Sionna 기본값 | 그들이 쓴 값 |
|---|---|---|---|
| 소스당 최대 경로 | `max_num_paths_per_src` | 1e6 | 1e4 |
| 소스당 샘플 | `samples_per_src` | 1e6 | 1e6 |
| 최대 깊이 | `max_depth` | **3** | 3 |
| 합성 배열 | `synthetic_array` | True | False |
| 정반사 | `specular_reflection` | True | **False** |
| 확산반사 | `diffuse_reflection` | False | **True** |
| 굴절 | `refraction` | **True** | True |

**그들의 결론 (원문 인용)**:
- *"Surprisingly, the results were absolutely insensitive to the `max_depth` parameter."*
- *"We tried both boolean values for all four configuration variables ... **The results were identical.**"*
- 반면 `samples_per_src` 에는 민감했다 — 1e3 은 1e6 과 유의하게 달랐다.

> ⚠ **이 표가 우리 설치본에서 읽은 기본값과 정확히 일치한다** (max_depth 3, refraction True,
> diffraction 기본 off, diffuse_reflection False, specular True, samples 1e6).
> 즉 §2 의 기본값은 **독립적으로 두 번 확인**되었다.

### 5.2 S-ICDF (arXiv 2607.03411) — 굴절 on/off 를 실제로 재봄

실내 산업홀, GPS-L1 대역, MUSIC/ESPRIT/CAPON 방향탐지 오차(도).

| 설정 | 방위오차 (MUSIC) | 앙각오차 (MUSIC) |
|---|---|---|
| 기본 (Reflection depth 5, Refraction False) | 0.84° | 2.26° |
| Reflection depth **2** | **2.35°** (악화) | 3.53° |
| Refraction **True** | **0.75°** (개선) | **1.98°** |

원문: *"A higher reflection depth leads to a more robust DF, while enabling refraction slightly
improves all methods."*

> ⚠ **이 논문은 내부가 어긋난다.** 표 II 는 Refraction 의 기본값을 **True** 로 적고,
> 표 III 는 "Default parameter setting ... **Refraction = False**" 로 적는다.
> 인용할 때 이 점을 밝혀야 한다.

### 5.3 AirMap (arXiv 2511.05522) — 회절 on/off × 깊이 2~20

Sionna **v1.2.1**, 실측 대비 라디오맵 경로이득 RMSE.
"회절 켜고 깊이 20" 을 **기준진리(ground truth)** 로 삼는다.
*"when diffraction is enabled, the RMSE levels off beyond a path depth of 14"* — 즉 깊이는 포화하고,
회절은 켜는 편이 실측에 가깝다.

### 5.4 Saribekyan et al. (2607.04400) — 두 설정의 «불일치» 를 스스로 한계로 적음

데이터 생성은 깊이 5 + 정반사 켬, 안테나 보정은 깊이 3 + 정반사 끔.
*"antennas are calibrated under somewhat lighter propagation than ..."* — **설정 차이를 한계로 명시한
드문 사례.**

### 5.5 Makvandi et al., AdaPTwin (2605.21897) — 스위치 = 충실도 손잡이

Sionna **2.0.1**. `max_depth`(3/6/10), 소스당 광선(1e3/1e4/1e10), 회절 불리언, 확산반사 불리언을
**저·중·고 충실도 등급으로 묶어** 비용-정확도 절충을 설계한다. 스위치를 «연구 대상» 으로 다룬 사례.

> **다섯 편 모두, 관측량이 «환경 채널» 이다.** 라디오맵 RMSE, RSSI 상관, 측위 오차, 방향탐지 오차.
> **표적 후방산란(RCS)·마이크로도플러를 관측량으로 놓고 스위치를 재본 논문은 이 조사에서 나오지 않았다.**

---

## 6. 우리 결과와 나란히 놓기

`outputs/diag_physics_paths_el-90.json` (el = −90°, 거리 10 m, 3.5 GHz, spp 1.1e7, 20 자세):

| 설정 | 경로 수 (중앙값) | 레벨 (dB) | AC/DC (dB) |
|---|---|---|---|
| 기준 (depth 1, 굴절·회절 끔) | 11 | −130.78 | +0.89 |
| **굴절만 켬** | **2** | −132.48 | +4.60 |
| **회절만 켬** | 14 | **−64.23** | **−68.13** |
| 모서리회절만 켬 | 11 | −130.78 | +0.89 |
| 다중반사 (depth 3) | 12 | −130.76 | +0.88 |
| 전부 켬 | 6 | −64.23 | −68.11 |

**선행연구와 비교하면**:

| | Manukyan (도시 RSSI) | 우리 (소형 표적 후방산란) |
|---|---|---|
| `max_depth` 민감도 | **무감** (절대적으로 둔감) | **거의 무감** (−130.78 → −130.76) ✅ 일치 |
| 불리언 스위치 민감도 | **결과 동일** | **회절이 66 dB 를 바꾼다** ❌ 정반대 |

**이건 모순이 아니다.** 두 실험의 **관측량이 다르다**. Manukyan 은 도시 규모 경로손실(수많은
경로의 합)을 보고, 우리는 파장 수준 크기의 단일 표적에서 돌아오는 약한 후방산란을 본다.
전자는 스위치를 켜도 지배적 성분이 안 바뀌고, 후자는 스위치가 **지배적 성분 자체를 만들어 낸다.**
깊이에 둔감한 점은 오히려 두 실험이 **일치**한다.

---

## 7. 리포트 권 17 에 넣을 문단 (과장 없이)

> **솔버 설정의 보고 관행에 대하여.**
> Sionna 의 경로 솔버는 어떤 전파 현상까지 계산할지를 몇 개의 스위치로 정한다 —
> 최대 상호작용 깊이(`max_depth`), 정반사·확산반사·굴절·회절의 on/off, 그리고 송신점당 발사 광선 수.
> 우리 보관함에서 Sionna RT 를 실제로 돌린 논문 89편을 전수로 열어 확인한 결과,
> 이 셋을 모두 적어 재현이 가능한 논문은 17편(19%)이었고, 36편(40%)은 솔버 설정을 하나도 적지 않았다.
> 가장 자주 빠지는 항목은 광선 수로, 밝힌 논문이 22편(25%)에 그쳤다.
> 스위치를 바꿔 가며 결과 변화를 수치로 보고한 논문은 5편이며, 그 관측량은 모두
> 라디오맵 오차·수신세기 상관·측위/방향탐지 오차와 같은 **환경 채널** 지표였다.
> 표적 후방산란이나 마이크로도플러를 관측량으로 두고 스위치 민감도를 보고한 선행연구는 찾지 못했다.
>
> **이것이 왜 문제인가.** 우리 앙각 실험에서 스위치 하나는 결과를 수십 dB 씩 움직인다.
> 앙각 −90°에서 회절만 켜면 수신 레벨이 −130.8 dB 에서 −64.2 dB 로 66 dB 올라가고
> 회전 성분 대 직류 성분의 비(AC/DC)는 부호가 뒤집힌다. 굴절을 켜면 광선이 기체의 플라스틱 껍데기를
> 통과해 버려 되돌아오는 경로가 11개에서 2개로 줄어든다. 반면 다중반사(깊이 1→3)와 모서리회절은
> 소수점까지 아무 영향이 없다. 즉 **어떤 스위치는 결과를 지배하고 어떤 스위치는 무해한데,
> 어느 쪽인지는 관측량에 따라 달라진다.** 도시 규모 수신세기를 본 Manukyan 등(2026)은
> 같은 불리언 스위치들을 양쪽으로 다 돌려 봐도 "결과가 동일했다" 고 보고했고 깊이에도 무감했다.
> 우리 역시 깊이에는 무감했지만 회절에는 무감하지 않았다. 두 결과는 충돌하지 않는다 —
> 관측량이 다르면 민감도가 다르다는 것을 함께 보여줄 뿐이다. 그렇기 때문에
> **설정을 적어 두지 않은 논문의 절대 레벨은 다른 연구와 비교할 수 없다.**
>
> **덧붙여 버전 함정이 있다.** Sionna 는 0.15 에서 회절을 도입했다가 1.0 의 전면 재작성에서
> 회절 기능을 통째로 들어냈고, 1.2.0 에서 되돌렸다. 따라서 1.0~1.1 을 쓴 연구의 "회절 무언급"은
> 선택이 아니라 불가능이었을 수 있다. 우리는 2.0.1 을 쓰며, 기본값 대비
> `max_depth` 를 3→1 로, `refraction` 을 True→False 로 바꾸었고 나머지는 기본값을 따랐다.
> (`diffraction=False` 는 우리의 선택이 아니라 Sionna 의 기본값이다.)
> 이 문서에 그 값과 각 스위치를 켰을 때의 변화량을 함께 남겨 둔다.

---

## 8. 모르는 것 (억지로 결론 내지 않음)

- **v0.x 의 정확한 기본 인자값**은 소스로 직접 확인하지 못했다. 공식 문서 예제와 GitHub 이슈에
  나오는 호출 서명(`max_depth, num_samples, los, reflection, diffraction, edge_diffraction,
  scattering, scat_keep_prob, scat_random_phases, check_scene`)으로 미루어 **`refraction` 인자가
  없었다**고 보지만 — **부분 확인**이다.
- 우리 보관함은 **무작위 표본이 아니다.** 이 프로젝트가 ISAC·센싱·디지털트윈 위주로 모은 것이라,
  "Sionna 논문 일반" 의 밝힘 비율이라고 일반화하면 안 된다. **"우리가 실제로 읽는 문헌 안에서" 의 비율**이다.
- **그림 안에만** 설정을 적어 둔 논문, **코드 저장소에만** 적어 둔 논문은 «안 밝힘» 으로 잡혔을 수 있다.
  (Qiao et al. 처럼 "메타데이터에 있다" 고 쓴 사례를 실제로 발견했다.)
- 밝힘 비율이 **시간이 지나며 좋아지는지 나빠지는지**는 세지 않았다. 표본이 2026년 arXiv 에
  크게 치우쳐 있어 추세를 말할 근거가 없다.
- **왜** 많은 논문이 안 밝히는지(지면 제약인지, 중요하지 않다고 봐서인지, 기본값을 그냥 썼기 때문인지)는
  본문만으로 알 수 없다. 추측하지 않는다.

---

## 부록: 재현 방법

이 조사에 쓴 스크립트는 스크래치패드에 있다(세션 한정). 핵심 절차만 남긴다.

1. `fitz.open(pdf)` → 전 페이지 `get_text()` 로 캐시
2. 텍스트 정규화 — **합자(ﬁ ﬂ ﬀ) 를 풀고, 줄바꿈 하이픈을 잇는다**
   ← 이걸 안 하면 `reﬂections` 가 `reflections` 로 안 잡혀 **미탐이 대량 발생**한다 (실제로 겪었다)
3. 3축 값-동반 정규식으로 채점 → **사람이 문맥을 읽고 오탐(도구 일반 소개)·미탐(표 안의 값) 을 덮어씀**
4. 덮어쓴 내역은 `outputs/survey_sionna_solver_settings.json` 의 `hand_checked` / `note` 에 보존

**참고 링크**
- [Sionna 2.0.1 PathSolver API](https://nvlabs.github.io/sionna/rt/api/paths_solvers.html)
- [Introduction to Sionna RT 튜토리얼](https://nvlabs.github.io/sionna/rt/tutorials/Introduction.html)
- [NVlabs/sionna Discussion #838 — 1.0.2 에서 회절이 사라진 건](https://github.com/NVlabs/sionna/discussions/838)
- [Sionna RT 기술보고서 (arXiv 2504.21719)](https://arxiv.org/pdf/2504.21719)
- [Manukyan et al. (arXiv 2507.19653)](https://arxiv.org/pdf/2507.19653)
