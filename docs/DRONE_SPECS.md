# DJI 드론 5종 — 제원 마스터 (Drone Specifications Master)

> **한 파일로 보는 표적 드론 5종의 공식 제원·외형/센서 배치·측정 RCS 레퍼런스·출처 링크.**
> sionna2 패시브 바이스태틱 레이더 시뮬의 표적 5종. 생성 2026-07-25.
>
> **데이터 원본(단일 진실):** `src/drones.py`(DroneSpec — CAD/시뮬이 쓰는 값) · `docs/drone_research.json`(리서치+검증+출처 URL) · `docs/SPECS.md`(검증 캐비엇) · `refs/drone_papers/`(측정 RCS 선행) · 메모 `sionna2-drone-sensor-specs`(2026-07-20 실사진 교차검증).
> ⚠ **시뮬 σ 값은 여기 박지 않는다** — 현행값은 `outputs/report2_waveform_rcs.json`(모노) · `outputs/report13_sigma_grid.json`(자유공간 격자)이 단일 출처.

---

## 1. 마스터 제원표

| 필드 | **Mini 5 Pro** | **Mavic 4 Pro** | **Matrice 4E** | **S1000+** | **Phantom 4** |
|---|---|---|---|---|---|
| 분류 | 초소형 접이 쿼드 | 대형 소비자 접이 쿼드 | 엔터프라이즈 측량 쿼드 | 산업용 옥토(8암) | 고정암 쿼드(클래식) |
| 출시 | 2025-09 (released) | 2025 (released) | 2025-01 (released) | 2014 (단종) | 2016 (released) |
| 이륙중량 TOW | **249.9 g** (<250 g) | 1063 g | 1219 g | ~9500 g (기체 4400 g, 권장 6~11 kg) | 1380 g |
| 모터-모터 대각 | 275 mm ⚠추정 | 441 mm ⚠역산 | 438.8 mm | 1045 mm | 350 mm |
| 외형 L×W×H (언폴드·**프롭 제외**) | **H=91 mm만 공식** (L/W 미공개) | 328.7 × 390.5 × 135.2 | 307 × 387.5 × 149.5 | 1016 × 1016 × 380 | H≈196 (고정암) |
| 폴디드 L×W×H | 157 × 95 × 68 | — | — | — | 고정(접이 없음) |
| 프로펠러 지름 | 152.4 mm (6 in) | 266.7 mm (10.5 in) | 274 mm (10.8 in) | 381 mm (15 in) | 240 mm (9.4 in) |
| 프롭 날개수 / 피치 | 2 / 2.8 in | 2 / 5.8 in | 2 / 5.7 in | 2 / 5.2 in | 2 / 5.0 in |
| 로터 수 (배치) | 4 (56.3°/123.7° 접이 스윕) | 4 (32°/148° 접이 스윕) | 4 (45° X) | 8 (옥토, 비동축) | 4 (45° X, 고정) |
| 최고속도 | 19 m/s | 25 m/s | 21 m/s | — | 20 m/s |
| 호버 RPM (대표) | 5500 | 3600 | 3800 ⚠미해결 | 3600 | 5500 |
| 최대 RPM (공식 인증) | 7800 | 6000 | 7500 (C2 인증, 82 dB) | 5600 | 8500 |
| RTK | ✗ | ✗ | **✓ (온보드)** | ✗ | ✗ |
| 프레임 재질 | 플라스틱 | 플라스틱 | 플라스틱 | **카본** | 플라스틱(흰 셸) |

> **대각(diagonal) 주의:** Mini 5 Pro·Mavic 4 Pro 는 DJI 가 대각을 **공개하지 않는다**. Mini=공식 envelope(91 mm 높이)에 프레임을 맞춰 역산한 274.6 mm, Mavic=공식 envelope(328.7×390.5)를 400 mm 대각으로 못 펼쳐 역산한 440.9 mm. **CAD 는 공식 envelope 을 우선**하고 `diagonal_mm` 은 암/모터 두께 스케일로만 쓴다.

---

## 2. 외형·센서·짐벌·랜딩 배치 (2026-07-20 실사진+공식 교차검증, 재조사 금지)

| 항목 | Mini 5 Pro | Mavic 4 Pro | Matrice 4E | Phantom 4 (Pro V2 기준) | S1000+ |
|---|---|---|---|---|---|
| 어안(비전) 센서 | 4 (전방2·후방/상2) + 벨리2 | **6** (전방2 짐벌옆·후방/상2·벨리2) | **6** (전방코너2·후방숄더2·벨리2) | 전후하 각2 (5방향) | — |
| **전방 LiDAR** | **✓ (Mini 최초 탑재)** | **✓ (기수 고정창)** | **✗** (레이저거리계만) | ✗ | ✗ |
| 짐벌 | 전면중앙 낮음, 1인치 단일렌즈 | **볼형 3렌즈 스택** (Hasselblad광각+텔레2), 360° 무한회전 | 3렌즈(광각/텔레)+**레이저거리계** 박스 | 벨리 전면중앙 매달림(함몰), 단일렌즈 | **벨리** 매달림 |
| 하방 감지 | 벨리 IR-ToF | 벨리 3D-IR + 보조광 | 벨리 IR ToF | 하방 초음파2 + 측면 IR2 | — |
| RTK/GNSS 돔 | — | — | 상단후방 실린더/돔 + 비콘 | 상단전방 내장(작음) | — |
| 착륙장치 | 없음(후방암 짧은 발) | 전방2다리(안테나 내장)+후방암 발 | 암베이스 4 짧은 아치발 | **inverted-U 아치다리 2**(안테나 내장, 흰색) | 접이식 tall gear (460×511×305) |
| 셸 색 | 다크그레이 | 실버 | 오프화이트 | 흰색 원형 | 블랙 카본 |

> ⚠ **Phantom 4 센서 캐비엇:** CAD/제원표의 `phantom4`는 **원조 Phantom 4(2016)** — 전방+하방 비전만(5방향은 Pro). 위 표의 5방향 센서는 **Phantom 4 Pro V2** 기준이니 혼동 주의.
> ⚠ Mini 5 Pro 전면 세로 그릴 = 방열구지 센서 아님. Mini5Pro=LiDAR YES, Mini4Pro=NO.

---

## 3. 공식 제원 출처 링크 (per drone)

**DJI Mini 5 Pro** (released 2025-09-17)
- 공식: https://www.dji.com/mini-5-pro/specs (TOW 249.9 g±4 g; 언폴드 304×380×91 프롭포함; 폴디드 157×95×68; 대각 미기재)
- 프롭: https://support.dji.com/help/content?customId=en-us03400006559 (프롭 6028F, 15.2×7.1 cm ⇒ 152 mm)
- 독립: https://drdrone.com/pages/dji-mini-5-pro-technical-specifications · https://reboot-hub.com/pages/wiki-dji-mini-5-pro · https://www.dpreview.com/news/8842533468/ (sub-250g, US 미판매)

**DJI Mavic 4 Pro** (released 2025)
- 스펙시트(PDF): https://www.cliftoncameras.co.uk/uploads/specifications/DJI%20Mavic%204%20Pro%20Specification.pdf · https://www.marcotec-shop.com/media/download/Mavic-4-Pro_Specifications.pdf
- 독립: https://drdrone.ca/pages/dji-mavic-4-pro-technical-specifications

**DJI Matrice 4E** (released 2025-01)
- 공식: https://enterprise.dji.com/matrice-4-series/specs · https://enterprise.dji.com/news/detail/matrice-4-series-release
- 프롭/독립: https://www.heliguy.com/products/dji-matrice-4-series-propellers/ · https://drdrone.ca/pages/dji-matrice-4-series-technical-specifications · https://dronelife.com/2025/01/08/dji-introduces-matrice-4-series-advanced-tools-for-enterprise-drone-operations/

**DJI Spreading Wings S1000+** (2014, 단종)
- 공식: https://www.dji.com/spreading-wings-s1000-plus/info · https://www.dji.com/spreading-wings-s1000-plus/spec · https://www.dji.com/newsroom/news/dji-released-its-new-spreading-wings-s1000-octocopter-platform
- 독립: https://dronespec.dronedesk.io/dji-spreading-wings-s1000-plus

**DJI Phantom 4** (original, 2016)
- 스펙시트(PDF): https://www.fullcompass.com/common/files/27734-DJIPhantom4SpecSheet.pdf
- 공식/독립: https://www.dji.com/phantom-4/info · https://en.wikipedia.org/wiki/DJI_Phantom · https://dronespec.dronedesk.io/dji-phantom-4

---

## 4. 측정 RCS 레퍼런스 (선행 실측 — 우리 절대 σ 앵커; 절대값은 report08 §6 이 단일 판정)

| 논문 | 베뉴/연도 | 밴드 | 대상 드론 · 측정 RCS | 우리 대조 | 링크 |
|---|---|---|---|---|---|
| **Das et al.** ⭐바이스태틱 | IEEE WCL Vol.15, 2026 (DOI 10.1109/LWC.2026.3705634) | **1.8~27 GHz × 바이스태틱 0°/15°/90°** | DJI 4기종 실측 바이스태틱 RCS | **우리 `rcs_sbr_multistatic` 을 처음으로 외부 실측과 대조 가능한 앵커** | (DOI) |
| **Li & Ling** ⭐밴드일치 | IEEE AWPL, 2017 (~99 cites) | **3–6 GHz** (VNA, 구 보정) | Phantom 2 −27.5 · 3DR Solo −24.2 · Inspire 1 −13.7 dBsm(peak) | 우리 Mavic4Pro 방위평균@3.5GHz 가 Solo~Inspire 사이 = aspect-peak 범위 내. Aspect spread ~14 dB | https://ieeexplore.ieee.org/ (AWPL 2017) |
| **Ezuma et al.** | arXiv:1911.05926, 2019 | 15 & 25 GHz (compact-range) | Phantom 4 Pro −15.03/−12.40 · Inspire 1 −14.24/−11.09 dBsm | RCS 주파수 단조증가 방향 일치(+2.6 dB), 절대값은 밴드갭 커 참고 | https://arxiv.org/abs/1911.05926 |
| **Semkin et al.** | IEEE Access vol.8, 2020 (DOI 10.1109/ACCESS.2020.2979339) | 26–40 GHz (무반향, 준모노) | Mavic Pro −16.8~−15.0 · Phantom4Pro −16.4~−12.3 · **M100(카본) −10.5~−6.6** dBsm | **카본이 플라스틱보다 mean +7 dB** — 우리 재질차 방향 일치. STATIC(로터정지) | https://ieeexplore.ieee.org/document/9032332/ |
| **Quevedo et al.** | IET RSN, 2019 | X-band 8.75 GHz FMCW | Phantom 4: −20~−4.6 dBsm(프롭/편파/앙각 의존), 대표 −10, 3 km 추적 | 프롭 회전이 RCS 크게 흔듦(마이크로도플러 서사 일치) | (IET RSN 2019) |
| **DTMB 패시브** ⭐패러다임 | passive bistatic | DTMB 조명 | **Mavic 3** 로터 마이크로도플러 실측(협조표적) | 패시브+마이크로도플러+Mavic계열 = 우리 패러다임 최근접 | `refs/drone_papers/DTMB_*` |

---

## 5. 캐비엇·불확실성 (기록)

- **대각선(diagonal_mm)**: Mini 5 Pro·Mavic 4 Pro 는 DJI 미공개 → envelope 역산값. CAD 는 envelope 우선.
- **Matrice 4E 호버 RPM 미해결**: C_T 법 3950~4410 vs 최대(7500)·T/W 앵커 4740~5300. 현행 3800(C_T=0.108) 채택. 마이크로도플러 플래시/팁이 이 값에 선형 비례 → 텔레메트리/음향 측정 필요.
- **Mini 5 Pro L/W 미공개**: 폴디드(프롭제외) 157×95×68·언폴드(프롭포함) 304×380×91 만 공식. 우리가 쓰던 255×181 은 방향(x>y)이 공식(380>304)과 반대 → 폐기, **높이 91 mm 만 강제**, L/W 는 로터배치가 결정.
- **Mavic 4 Pro envelope**: 328.7×390.5 는 400 mm 대각으로 불가 → 대각 440.9 mm 역산(envelope 승).
- **S1000+ 무게**: 4400 g = 기체 자중. TOW 6~11 kg, 대표 ~9.5 kg.
- **Phantom 4 원조 vs Pro**: CAD 는 원조 P4(2016). 5방향 센서·측면IR 은 Pro V2 사양.
- **측정 RCS 절대값**: 선행은 전부 밴드/기하/재질이 우리와 어긋난다 → **방향성 대조**만. 절대 σ 판정은 report08 §6 이 단일 출처. 시뮬 현행값은 outputs JSON 이 진실.

---

*원본 데이터: `src/drones.py` · `docs/drone_research.json` · `docs/SPECS.md` · `refs/drone_papers/` · 메모 `sionna2-drone-sensor-specs`(2026-07-20). 갱신 시 원본을 고치고 이 파일을 재생성할 것.*
