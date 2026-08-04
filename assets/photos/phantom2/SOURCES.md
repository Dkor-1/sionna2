# DJI Phantom 2 (`phantom2`) — 참조 이미지 출처

`phantom2` 는 **새 기체 키**다. 2026-08-03 수집 전까지 저장소에 이 기체는 없었다.

> ⚠ **혼동 금지.** 저장소의 `mini5pro`(DJI Mini 5 Pro) · `matrice4e`(DJI Matrice 4E) 는 **다른 기체다.**
> 이 폴더는 **2013년 12월 출시된 DJI Phantom 2** 와 그 파생형(Vision · Vision+) 전용이다.
> 같은 폴더 안에서 어느 파일이 어느 파생형인지는 아래 §2 변종 판정과 파일별 표에 전부 적었다.

**왜 모았나** — Das et al. (IEEE WCL 2026) 이 이 기체를 재고 Table III 에 RCS 계수(a·b·c·d)를 인쇄했다
(`outputs/das_fleet_spec.json` 의 `airframes.phantom2`). 우리가 메쉬를 만들어 맞추면
**메쉬 방법 검증이 N=1 에서 N=4 로 간다.**

---

## 0. 한눈에

| 항목 | 값 |
|---|---|
| 총 파일 | **104장** (d 17 · p 14 · t 33 · c 27 · m 13) |
| 내부(분해) 보임 | **예** — iFixit 정식 티어다운 16장 + iFixit 수리가이드 12장 + FCC 내부사진 5장(셸 제거 전체) |
| 치수 도면 | **예** — DJI 매뉴얼 기체 도해·사양표 3종 + 보도자료 Fact Sheet + 프로펠러 도해 |
| 접힘/펼침 | **해당 없음 — 비접이식 강체 기체** (§1) |
| ⭐ 자(줄자) 들어간 사진 | **29장** — FCC 외부 6면 + 내부 23장 전부에 줄자가 함께 찍혀 있다. 사진에서 절대 치수를 직접 잴 수 있다 |
| ⭐ 6면 정사 사진 | **있다** — FCC 외부사진이 상·하·전·후·좌·우 6면을 전부 담았고 전부 줄자 동반 |
| ⚠ 미해결 구멍 | Das Fig.1 사진의 기체 외형이 Phantom 2 와 어긋나 보인다 (§3). 단정하지 않고 기록만 남긴다 |

---

## 1. 접힘 상태 — **해당 없음. Phantom 2 는 접히지 않는다**

Phantom 2 계열은 사출 셸에 암이 일체로 붙은 **비접이식 강체 기체**다. 접히는 관절이 없다.
탈착되는 것은 프로펠러(자동조임 9450/9450R) · 배터리 · 짐벌뿐이다.
따라서 Mini 2·Mavic 류처럼 "펼침/접힘 두 상태"를 나눠 모을 대상이 아니다.

대신 이 기체에서 의미 있는 상태 구분은 **프로펠러 장착 / 미장착**이고, 그 구분이 Das 대조에 직접 걸린다.

### Das 는 어느 상태로 쟀나 — **프로펠러 장착, 치수는 프롭 제외 대각**

`outputs/das_fleet_spec.json` 의 Table I 판독값은 Phantom 2 열에 **`35.0 cm x 20.0 cm`** 다.

- **35.0 cm** 는 DJI 공표값과 글자단위로 같다. DJI Phantom 2 매뉴얼 v1.4 p.35 사양표는
  `Wheelbase 350mm`, Vision+ 매뉴얼 v1.8 p.48 은 `Motor Diagonal Length 350mm` 라고 적는다.
  → **Das 의 첫 수는 프로펠러를 뺀 모터축-모터축 대각이다.**
  프로펠러(9450, 지름 238.8 mm)를 대각으로 최대한 벌리면 팁-팁이 **588.8 mm** 가 되므로,
  35.0 cm 가 프롭 포함일 가능성은 없다.
- **20.0 cm** 는 DJI 공표 높이와 어긋난다. DJI 보도자료 Fact Sheet 는 `29cm x 29cm x 18cm` 로
  높이 **180 mm** 를 적는다. 20 mm 차이의 설명 후보는 (a) 짐벌·카메라 부착 상태 높이,
  (b) 다리 끝~프롭 상면 포함, (c) Das 가 인용한 2차 출처의 반올림. **미해결로 남긴다.**
- **측정 시 프로펠러는 달려 있었다.** Das Fig.1(p.3732) 우측 사진 인셋에서 최소 3개 모터에
  2날 프로펠러가 달린 것이 보인다.

> ⚠ **또 하나의 정정.** "Das 가 이 기체를 무향실에서 쟀다"는 서술은 Phantom 2 에는 맞지 않는다.
> Das Table I 의 Phantom 2 열 환경은 **`Controlled non-anechoic, indoor`** 이고, 본문은
> *"Phantom 2 is the only platform measured in a controlled indoor non-anechoic near-field setting"*
> 이라고 못박는다. TX-RX 거리는 **2.6 m**, 근거리장이다(`das_fleet_spec.json` 의 `farfield_check` 참조).
> 무향 원거리장으로 잰 것은 나머지 세 기체(Mini 2 · Phantom 3 · M350 RTK, 출처 [7])다.
> Phantom 2 만 이 논문에서 신규 측정됐다.

---

## 2. 변종·세대 판정 — 어느 파일이 무엇인가

Phantom 2 는 한 몸체에서 세 갈래로 갈린다. **동체·암·다리·모터·프로펠러는 셋이 사실상 같고,
아래에 무엇이 매달리느냐가 다르다.** RCS 메쉬 관점에서 중요한 차이는 **배 밑 페이로드**뿐이다.

| 변종 | 출시 | 페이로드 | 외형 식별 근거 |
|---|---|---|---|
| **Phantom 2** (P330) | 2013-12 | 카메라 없음. Zenmuse H3-2D/H3-3D + GoPro 를 옵션 장착 | 배 밑이 비어 있거나 GoPro 가 달린 짐벌. 암에 **붉은 스트라이프** |
| **Phantom 2 Vision** | 2013-10 | 내장 14 MP 카메라, 1축 틸트(0~60°), 짐벌 안정화 없음 | 배 밑에 각진 카메라 박스가 셸에 고정 |
| **Phantom 2 Vision+** (PV331) | 2014-04 | 3축 안정화 짐벌 + 내장 14 MP 카메라 | 배 밑에 **은색 3축 짐벌 암**과 원통 렌즈 |

**이 폴더의 구성:**
- `d01·d02` = 순수 **Phantom 2**(페이로드 없음) 공식 정면 정사영. 메쉬 기본 실루엣은 여기서 딴다.
- `d03~d11` = **Phantom 2 + Zenmuse H3-3D + GoPro** 공식 렌더.
- `d12·d13·d16·d17` = **Vision+ · Vision** 공식 렌더.
- `p01~p06`, `t17~t21`, `c01~c18` = **Vision+**(FCC ID SS3-PV3311402, 제품코드 PV3311402).
- `t01~t16` = **Phantom 2 + H3-3D** (iFixit 티어다운 33365 가 이 구성이다).
- `t22~t33`, `c23~c27` = **Vision+** (iFixit 수리가이드).
- `p07~p14` = **Vision+** 실기 사진.

**세대 혼동 방지 근거:**
- Phantom(1세대)·Phantom FC40 과의 구별 — FC40 은 **파란 스트라이프**, Phantom 2 계열은 **붉은 스트라이프**다.
  이 기준으로 커먼즈의 `File:DJI Phantom 2 onground.jpg`(4000x2248)는 **파란 스트라이프**여서
  FC40 계열일 가능성을 배제할 수 없어 **의도적으로 제외**했다. 제목만 믿고 넣지 않았다.
- Phantom 3 과의 구별 — Phantom 3 는 암에 **금색 스트라이프**, 다리가 가는 관형이고 셸이 더 납작하다.
- Phantom 4 와의 구별 — Phantom 4 는 암이 동체와 이어진 **후퇴익 형태**, 다리가 두껍고 뿌리가 높으며 스트라이프가 없다.

---

## 3. ⚠ 미해결 — Das Fig.1 의 기체가 Phantom 2 로 안 보인다

논문 Fig.1(p.3732) 우측 사진 인셋을 원본 래스터에서 잘라(유효 약 130x90 px) 11배 확대해 봤다
(재현물: `scratchpad/p2/das_fig1_drone_only.png`). 관측한 것:

1. 암이 동체와 매끄럽게 이어진 **후퇴익 형태**다.
2. 다리가 **두껍고 뿌리가 높다.**
3. 암에 **붉은 스트라이프가 보이지 않는다.**
4. 코 아래 짐벌·카메라가 달려 있다.

이 넷은 **Phantom 4 계열 외형**에 더 가깝고, Phantom 2(원통형 암 + 붉은 스트라이프 + 가는 관형 다리)와는
어긋나 보인다. 저장소의 `assets/photos/phantom4/` · `assets/photos/phantom3/` 공식 사진과 나란히 놓고 비교한 결과다.

**반증 쪽:** 판독 해상도가 극히 낮고, 각도·노출·저해상 보간의 영향이 크다.
논문 본문과 Table I·III 은 일관되게 `DJI Phantom 2` 라고 적는다.

**결론: 단정하지 않는다. 확신 중간(약 70 %).** 지금은 Phantom 2 기하로 진행하되 이 구멍을 기록해 둔다.
해소 방법은 (a) 저자에게 문의, (b) 논문 고해상 원본/보충자료 확보, (c) 같은 그룹의 후속 논문에서 설비 사진 재확인.

---

## 4. 무엇을 잴 수 있나 (사진별 측정 가능 항목)

| 재고 싶은 것 | 쓸 파일 | 방법 |
|---|---|---|
| 모터-모터 대각 350 mm 검증 | `p01`(상면, 줄자) | 줄자 눈금으로 픽셀-mm 환산 후 대각 모터축 간 거리 |
| 동체 외곽 상자 290x290 | `p01`·`p03`·`p05` | 상면에서 폭, 정면·측면에서 높이 |
| 높이 180 mm 검증 (Das 200 mm 와의 20 mm 차이) | `p03`(정면)·`p05`(좌측면) | 다리 끝~셸 상면. 짐벌 포함/제외를 나눠 재라 |
| 다리 형상·간격 | `p02`(저면)·`t30`·`t31` | 저면 정사에서 다리 발자국 |
| 프로펠러 지름 238.8 mm·2날 | `p01`·`m03`·`c24`·`c25` | 상면 줄자 + 매뉴얼 9450 도해 |
| 모터 지름(2212 = 스테이터 22 mm) | `t01`·`t02`·`t27` | 분해 사진 |
| 셸 두께·내부 공동 | `t17~t21`(줄자)·`t23`·`t24` | 셸 제거 상태 |
| 내부 금속 덩어리 위치(RCS 기여) | `t17~t21`·`c01~c06` | 메인보드·ESC 보드·차폐캔 위치와 크기 |
| 배터리 팩 치수(금속·전해질 덩어리) | `c14~c18`(줄자) | 5200 mAh 3S 팩 외곽 |
| 짐벌·카메라 형상 | `t14`·`t16`·`t32`·`t33`·`c19~c22`·`c10~c13` | H3-3D(Phantom 2) vs Vision+ 3축 짐벌 |
| GPS 보드·컴퍼스 위치 | `t13`·`c08`·`c09`·`t25` | 상부 셸 안쪽 |

---

## 5. 라이선스

| 출처군 | 라이선스 | 재배포 조건 |
|---|---|---|
| **FCC 제출물** (`p01~p06`, `t17~t21`, `c01~c18`) | 미국 연방정부 공개기록 — 저작권 주장 없음(공개 심사 문서) | 자유. 출처 FCC ID 표기 권장 |
| **DJI 공식 렌더·매뉴얼·보도자료** (`d01~d14`, `m01~m13`) | © SZ DJI Technology. **내부 연구 참조용으로만** 사용 | ⚠ 리포트·덱에 그대로 싣지 마라. 치수 판독·메쉬 대조용 내부 자료로 한정 |
| **위키미디어 커먼즈** (`d15~d17`, `p07~p14`) | CC BY-SA 3.0 (`d15~d17`) / CC BY-SA 4.0 (`p07~p10`, `p12`) / CC BY 2.0 (`p13`) / CC BY-SA 2.0 (`p11`, `p14`) | 저자 표시 + 동일조건. 아래 표에 저자 적어 뒀다 |
| **iFixit** (`t01~t16`, `t22~t33`, `c23~c27`) | CC BY-NC-SA 3.0 | 비상업·저자표시·동일조건. 상업 배포 금지 |

**커먼즈 저자 표시(CC BY 조건 충족용):**

| 파일 | 저자 | 라이선스 | 원본 |
|---|---|---|---|
| `phantom2_d15_official_p2_commons_small.png` | DJI technologies (커먼즈 업로더 표기) | CC BY-SA 3.0 | `File:DJI-Phantom2.png` |
| `phantom2_d16_official_pvplus_commons_small.png` | DJI technologies | CC BY-SA 3.0 | `File:DJI-Phantom2-Vision-plus.png` |
| `phantom2_d17_official_pv_commons_small.png` | DJI technologies | CC BY-SA 3.0 | `File:DJI-Phantom2-Vision.png` |
| `phantom2_p07~p10_commons_pvplus_phoenix_*` | User:ZLEA | CC BY-SA 4.0 | `File:DJI PV331 Phantom 2 Vision+ V2.0 'Phoenix' (FA3P33LP4K, cn PH645349295) (...)` |
| `phantom2_p11_commons_pvplus_studio.jpg` | 플리커 유래 업로드 | CC BY-SA 2.0 | `File:DJI Phantom Vision Plus Quadcopter.jpg` |
| `phantom2_p12_commons_pvplus_v3_outdoor.jpg` | User:Capricorn4049 | CC BY-SA 4.0 | `File:DJI Phantom 2 Vision+ V3 (2).jpg` |
| `phantom2_p13_commons_pvplus_davidj.jpg` | 플리커 David J | CC BY 2.0 | `File:DJI Phantom 2 Vision+ Quadcopter (by David J).jpg` |
| `phantom2_p14_commons_pvplus_hovering.jpg` | 플리커 유래 업로드 | CC BY-SA 2.0 | `File:DJI Phantom 2 Vision+ hovering over grass (14539721843).jpg` |

---

## 6. 출처 URL

| 키 | URL | 비고 |
|---|---|---|
| DJI Phantom 2 매뉴얼 v1.4 | `https://dl.djicdn.com/downloads/phantom_2/en/PHANTOM2_User_Manual_v1.4_en.pdf` | 36쪽. 기체 도해 p.5, 프로펠러 p.13, 사양표 p.35 |
| DJI Vision+ 매뉴얼 v1.8 | `https://dl.djicdn.com/downloads/phantom_2_vision_plus/en/Phantom_2_Vision_Plus_User_Manual_v1.8_en.pdf` | 52쪽. 사양표 p.48 |
| DJI Vision 매뉴얼 v1.8 | `https://dl.djicdn.com/downloads/phantom-2-vision/en/Phantom_2_Vision_User_Manual_v1.8_en.pdf` | 71쪽. 사양표 p.70 |
| DJI Phantom 2 Fact Sheet | `http://download.dji-innovations.com/downloads/press/Phantom_2_Fact_Sheet.pdf` | 보도자료 1쪽. **유일한 높이 공표값 18 cm** 출처 |
| FCC ID SS3-PV3311402 | `https://fccid.io/SS3-PV3311402` | 외부사진 `.../External-Photos/Ext-Photos-2214430.pdf`, 내부사진 `.../Internal-Photos/Int-Photos-2214432.pdf` |
| iFixit 티어다운 33365 | `https://www.ifixit.com/Teardown/DJI+Phantom+2+Teardown/33365` | Phantom 2 + H3-3D. API: `https://www.ifixit.com/api/2.0/guides/33365` |
| iFixit 가이드 35983 / 35984 / 67775 / 35981 / 35973 | `https://www.ifixit.com/Guide/.../35983` 등 | 상부 셸 / 모터 / 짐벌 요암 / 프로펠러 / 배터리 |
| DJI 공식 360 렌더(폐기된 CDN) | `http://d333gi46xmu1md.cloudfront.net/images/360/phantom-2/...` | 라이브에서 403. **웹아카이브 경유**로만 받힌다: `https://web.archive.org/web/<ts>im_/<원본URL>` |
| DJI 뉴스룸 보도이미지 | `https://www.dji.com/wp-content/uploads/2013/12/phantom2_release.jpg` | 라이브 |
| Das et al. IEEE WCL 2026 | `doi:10.1109/LWC.2026.3705634` | `/data/public/sionna_jeong/papers_isac_sionna/paper_sionna_Ray_0723/` 에 원문 PDF |

**촬영각 규약** — 파일명의 설명 토큰이 각도를 담는다: `front`(정면) `rear`(후면) `left`/`right`(측면)
`top`(상면) `bottom`(저면) `iso`(등각) `elevation`(정사영). 스핀 프레임은 `spinNN` 으로 프레임 번호를 남겼다
(아카이브에 남은 프레임이 좁은 방위 구간만 덮어서, 실제 방위차는 프레임 번호에 비례하지 않는다).

---

## 7. 공표 스펙

전량은 `outputs/phantom2_specs.json` 에 출처 키와 원문 문자열까지 붙여 넣었다. 요지만:

| 항목 | Phantom 2 | Vision | Vision+ |
|---|---|---|---|
| 모터-모터 대각 | **350 mm** | 350 mm | 350 mm |
| 외곽 상자 | **290 x 290 x 180 mm** (Fact Sheet) | — | — |
| 중량 | **1000 g** (배터리 포함) | 1160 g | 1242 g (배터리·프롭 포함) |
| 최대 이륙중량 | ≤1300 g | 1350 g | 1350 g |
| 프로펠러 | 9450 / 9450R, **2날**, 지름 **238.8 mm** (9.4 in), 자동조임 | 동일 | 동일 |
| 모터 | **DJI 2212**, KV920 @12 V, 4개 | 동일 | 동일 |
| 배터리 | **3S LiPo 5200 mAh / 11.1 V** | 동일 | 동일 |
| 비행제어 | Naza-M V2 | — | — |
| 무선 | RC 2.4 GHz ISM, 1000 m | RC 5.728-5.85 GHz + 2.4 GHz 확장기 | RC 5.728-5.85 GHz + 2.4 GHz 확장기 20 dBm |

파생값: 프로펠러 팁-팁 대각 **588.8 mm**, 암 반경 **175 mm**,
가우시안 클러스터 sigma_s = D/4.3 = **0.0814 m** (D = 0.350 m 수평 대각 기준).

---

## 8. 파일 목록

### d — DJI 공식 렌더 (17장)

| 파일 | 해상도 | 출처 | 내용 |
|---|---|---|---|
| `phantom2_d01_official_p2_front_elevation.jpg` | 960x480 | DJI 공식 360 뷰어 정지프레임(웹아카이브) | Phantom 2 정면 정사영 렌더(프로펠러 장착, 짐벌 없음) — 흰 배경 |
| `phantom2_d02_official_p2_front_elevation_v1.jpg` | 960x480 | DJI 공식 360 뷰어 정지프레임(초기판, 웹아카이브) | Phantom 2 정면 정사영 렌더(초기판) |
| `phantom2_d03_official_p2_h33d_spin00.png` | 960x370 | DJI 공식 360 스핀 시퀀스(웹아카이브) | Phantom 2 + Zenmuse H3-3D + GoPro, 360 스핀 프레임 0 |
| `phantom2_d04_official_p2_h33d_spin12.png` | 960x370 | DJI 공식 360 스핀 시퀀스(웹아카이브) | 같은 스핀 프레임 12 (방위 약간 회전) |
| `phantom2_d05_official_p2_h33d_spin24.png` | 960x370 | DJI 공식 360 스핀 시퀀스(웹아카이브) | 같은 스핀 프레임 24 |
| `phantom2_d06_official_p2_h33d_spin36.png` | 960x370 | DJI 공식 360 스핀 시퀀스(웹아카이브) | 같은 스핀 프레임 36 |
| `phantom2_d07_official_p2_h33d_spin44.png` | 960x370 | DJI 공식 360 스핀 시퀀스(웹아카이브) | 같은 스핀 프레임 44 |
| `phantom2_d08_official_p2_h33d_iso0.png` | 640x512 | DJI 공식 비행 렌더 시퀀스(웹아카이브) | Phantom 2 + H3-3D + GoPro 비행 iso 렌더 0 (프롭 회전 블러) |
| `phantom2_d09_official_p2_h33d_iso1.png` | 640x512 | DJI 공식 비행 렌더 시퀀스(웹아카이브) | 비행 iso 렌더 1 |
| `phantom2_d10_official_p2_h33d_iso2.png` | 640x512 | DJI 공식 비행 렌더 시퀀스(웹아카이브) | 비행 iso 렌더 2 |
| `phantom2_d11_official_p2_h33d_iso3.png` | 640x512 | DJI 공식 비행 렌더 시퀀스(웹아카이브) | 비행 iso 렌더 3 |
| `phantom2_d12_official_pvplus_front_elevation.jpg` | 960x480 | DJI 공식 360 뷰어 정지프레임(웹아카이브) | Phantom 2 Vision+ 정면 정사영 렌더(짐벌·카메라 포함) |
| `phantom2_d13_official_pv_front_elevation.jpg` | 960x480 | DJI 공식 360 뷰어 정지프레임(웹아카이브) | Phantom 2 Vision(무플러스) 정면 정사영 렌더 |
| `phantom2_d14_official_press_release.jpg` | 709x510 | DJI 뉴스룸 보도이미지 | DJI 뉴스룸 Phantom 2 출시 보도용 이미지 |
| `phantom2_d15_official_p2_commons_small.png` | 320x320 | 위키미디어 커먼즈(DJI 공식 이미지 재수록) | DJI 공식 제품 이미지(커먼즈 재수록, 320px) |
| `phantom2_d16_official_pvplus_commons_small.png` | 640x640 | 위키미디어 커먼즈(DJI 공식 이미지 재수록) | DJI 공식 Vision+ 제품 이미지(커먼즈 재수록, 640px) |
| `phantom2_d17_official_pv_commons_small.png` | 320x320 | 위키미디어 커먼즈(DJI 공식 이미지 재수록) | DJI 공식 Vision 제품 이미지(커먼즈 재수록, 320px) |

### p — 제품·스튜디오 사진 (14장)

| 파일 | 해상도 | 출처 | 내용 |
|---|---|---|---|
| `phantom2_p01_fcc_ext_top_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 상면(줄자 있음) |
| `phantom2_p02_fcc_ext_bottom_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 저면(줄자 있음) |
| `phantom2_p03_fcc_ext_front_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 정면(줄자 있음) |
| `phantom2_p04_fcc_ext_rear_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 후면(줄자 있음) |
| `phantom2_p05_fcc_ext_left_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 좌측면(줄자 있음) |
| `phantom2_p06_fcc_ext_right_tape.png` | 944x708 | FCC SS3-PV3311402 외부사진 PDF | FCC 외부사진 우측면(줄자 있음) |
| `phantom2_p07_commons_pvplus_phoenix_iso_a.jpg` | 5184x3456 | 커먼즈 ZLEA 촬영(전시체) | Vision+ V2.0 실기(전시체) iso — 5184x3456 |
| `phantom2_p08_commons_pvplus_phoenix_iso_b.jpg` | 6000x4000 | 커먼즈 ZLEA 촬영(전시체) | 같은 실기 다른 각도 — 6000x4000 |
| `phantom2_p09_commons_pvplus_phoenix_iso_c.jpg` | 6000x4000 | 커먼즈 ZLEA 촬영(전시체) | 같은 실기 다른 각도 — 6000x4000 |
| `phantom2_p10_commons_pvplus_phoenix_iso_d.jpg` | 4032x3024 | 커먼즈 ZLEA 촬영(전시체) | 같은 실기 다른 각도 — 4032x3024 |
| `phantom2_p11_commons_pvplus_studio.jpg` | 5976x3450 | 커먼즈(플리커 유래) | Vision+ 스튜디오 촬영(배경 분리 쉬움) — 5976x3450 |
| `phantom2_p12_commons_pvplus_v3_outdoor.jpg` | 3960x2376 | 커먼즈 Capricorn4049 | Vision+ V3 야외 — 3960x2376 |
| `phantom2_p13_commons_pvplus_davidj.jpg` | 2592x1944 | 커먼즈(플리커 David J) | Vision+ 실기 — 2592x1944 |
| `phantom2_p14_commons_pvplus_hovering.jpg` | 6000x4000 | 커먼즈(플리커) | Vision+ 호버링(프롭 회전) — 6000x4000 |

### t — 분해(teardown) (33장)

| 파일 | 해상도 | 출처 | 내용 |
|---|---|---|---|
| `phantom2_t01_ifixit_td_motor_2212_a.jpg` | 1400x1050 | iFixit 티어다운 33365 | 브러시리스 모터 DJI 2212 (DJIPV-06) |
| `phantom2_t02_ifixit_td_motor_2212_b.jpg` | 1400x1050 | iFixit 티어다운 33365 | 모터/암 분해 2 |
| `phantom2_t03_ifixit_td_bottom_leds.jpg` | 1400x1050 | iFixit 티어다운 33365 | 저면 3색 LED, 하부 나사 |
| `phantom2_t04_ifixit_td_esc_a.jpg` | 1400x1050 | iFixit 티어다운 33365 | ESC(전자변속기) 1 |
| `phantom2_t05_ifixit_td_esc_b.jpg` | 1400x1050 | iFixit 티어다운 33365 | ESC 2 |
| `phantom2_t06_ifixit_td_esc_c.jpg` | 1400x1050 | iFixit 티어다운 33365 | ESC 3 |
| `phantom2_t07_ifixit_td_mainboard_a.jpg` | 1400x1050 | iFixit 티어다운 33365 | 수신기·메인 제어보드 1 |
| `phantom2_t08_ifixit_td_mainboard_b.jpg` | 1400x1050 | iFixit 티어다운 33365 | 메인 제어보드 2 |
| `phantom2_t09_ifixit_td_mainboard_c.jpg` | 1400x1050 | iFixit 티어다운 33365 | 메인 제어보드 3 |
| `phantom2_t10_ifixit_td_battery_a.jpg` | 932x699 | iFixit 티어다운 33365 | 인텔리전트 배터리 LiPo 11.1 V 5200 mAh 1 |
| `phantom2_t11_ifixit_td_battery_b.jpg` | 1048x786 | iFixit 티어다운 33365 | 배터리 2 |
| `phantom2_t12_ifixit_td_battery_c.jpg` | 1400x1050 | iFixit 티어다운 33365 | 배터리 3 |
| `phantom2_t13_ifixit_td_gps_board.jpg` | 1400x1050 | iFixit 티어다운 33365 | GPS 보드·케이블 |
| `phantom2_t14_ifixit_td_bottom_h33d_a.jpg` | 1400x1050 | iFixit 티어다운 33365 | 저면: Zenmuse H3-3D 짐벌 + FPV 송신기 |
| `phantom2_t15_ifixit_td_bottom_h33d_b.jpg` | 1400x1050 | iFixit 티어다운 33365 | FPV 송신기 |
| `phantom2_t16_ifixit_td_gimbal_micromotor.jpg` | 1400x1050 | iFixit 티어다운 33365 | 짐벌 브러시리스 마이크로 모터 |
| `phantom2_t17_fcc_coveroff_1_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | FCC 내부사진: 상부 셸 제거, 기체 전체 배선·암 ESC (줄자) |
| `phantom2_t18_fcc_coveroff_2_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 셸 제거 2 (줄자) |
| `phantom2_t19_fcc_coveroff_3_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 셸 제거 3 (줄자) |
| `phantom2_t20_fcc_coveroff_4_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 셸 제거 4 (줄자) |
| `phantom2_t21_fcc_coveroff_5_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 셸 제거 5 (줄자) |
| `phantom2_t22_ifixit_shell_bottom_screws.jpg` | 5661x4246 | iFixit 가이드 35983 (상부 셸) | 하부 나사 위치(2.0 mm 육각 12 + 필립스 #00 4) |
| `phantom2_t23_ifixit_shell_lift_a.jpg` | 4974x3731 | iFixit 가이드 35983 (상부 셸) | 상부 셸 들어올림 1 |
| `phantom2_t24_ifixit_shell_lift_b.jpg` | 4974x3731 | iFixit 가이드 35983 (상부 셸) | 상부 셸 들어올림 2 (내부 노출) |
| `phantom2_t25_ifixit_gps_connector.jpg` | 4141x3106 | iFixit 가이드 35983 (상부 셸) | 메인보드 뒤 GPS 몰렉스 커넥터 |
| `phantom2_t26_ifixit_motor_desolder.jpg` | 5041x3781 | iFixit 가이드 35984 (모터) | 모터 3선 디솔더 |
| `phantom2_t27_ifixit_motor_bolts.jpg` | 5333x4000 | iFixit 가이드 35984 (모터) | 모터 고정 2 mm 육각 볼트 4개 |
| `phantom2_t28_ifixit_motor_off_mount_a.jpg` | 3658x2744 | iFixit 가이드 35984 (모터) | 모터 마운트 분리 1 |
| `phantom2_t29_ifixit_motor_off_mount_b.jpg` | 3658x2744 | iFixit 가이드 35984 (모터) | 모터 마운트 분리 2 |
| `phantom2_t30_ifixit_gimbal_underside_a.jpg` | 3264x2448 | iFixit 가이드 67775 (짐벌 요암) | 뒤집은 기체 저면, 짐벌 고정 클립 |
| `phantom2_t31_ifixit_gimbal_underside_b.jpg` | 3264x2448 | iFixit 가이드 67775 (짐벌 요암) | 짐벌 고정 클립 2 |
| `phantom2_t32_ifixit_gimbal_damper_out.jpg` | 3264x2448 | iFixit 가이드 67775 (짐벌 요암) | 고무 댐퍼에서 짐벌 분리 |
| `phantom2_t33_ifixit_gimbal_free.jpg` | 2448x1836 | iFixit 가이드 67775 (짐벌 요암) | 짐벌·카메라 분리 상태 |

### c — 부품 단품 (27장)

> `c01`~`c18` 은 FCC 제출 내부사진이고 **전부 줄자와 함께 찍혔다**(파일명에 `_tape` 가 없는 `c07`~`c13` 도 포함).
> 즉 보드·모듈·카메라·배터리의 절대 치수를 사진에서 바로 잴 수 있다.

| 파일 | 해상도 | 출처 | 내용 |
|---|---|---|---|
| `phantom2_c01_fcc_mainboard_top_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 메인보드 상면 (줄자) |
| `phantom2_c02_fcc_mainboard_bottom_tape.png` | 942x707 | FCC SS3-PV3311402 내부사진 PDF | 메인보드 하면 (줄자) |
| `phantom2_c03_fcc_connboard_top_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 커넥션 보드 상면 (줄자) |
| `phantom2_c04_fcc_connboard_bottom_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 커넥션 보드 하면 (줄자) |
| `phantom2_c05_fcc_motorboard_top_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 모터(ESC) 보드 상면 (줄자) |
| `phantom2_c06_fcc_motorboard_bottom_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 모터(ESC) 보드 하면 (줄자) |
| `phantom2_c07_fcc_58g_module.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 5.8 GHz 영상송신 모듈 외형 |
| `phantom2_c08_fcc_gps_board_top.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | GPS 보드 상면 |
| `phantom2_c09_fcc_gps_board_bottom.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | GPS 보드 하면 |
| `phantom2_c10_fcc_camera_front.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 카메라 모듈 정면 |
| `phantom2_c11_fcc_camera_rear.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 카메라 모듈 후면 |
| `phantom2_c12_fcc_camera_side.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 카메라 모듈 측면 |
| `phantom2_c13_fcc_camera_coveroff.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 카메라 커버 제거 |
| `phantom2_c14_fcc_battery_v1_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 배터리 팩 뷰1 (줄자) |
| `phantom2_c15_fcc_battery_v2_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 배터리 팩 뷰2 (줄자) |
| `phantom2_c16_fcc_battery_v3_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 배터리 팩 뷰3 (줄자) |
| `phantom2_c17_fcc_battery_v4_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 배터리 팩 뷰4 (줄자) |
| `phantom2_c18_fcc_battery_v5_tape.png` | 944x708 | FCC SS3-PV3311402 내부사진 PDF | 배터리 팩 뷰5 (줄자) |
| `phantom2_c19_official_pvplus_gimbal_cam_a.jpg` | 960x420 | DJI 공식 카메라 360 시퀀스(웹아카이브) | Vision+ 짐벌·카메라 공식 렌더 A |
| `phantom2_c20_official_pvplus_gimbal_cam_b.jpg` | 960x420 | DJI 공식 카메라 360 시퀀스(웹아카이브) | Vision+ 짐벌·카메라 공식 렌더 B |
| `phantom2_c21_official_pvplus_gimbal_cam_c.jpg` | 960x420 | DJI 공식 카메라 360 시퀀스(웹아카이브) | Vision+ 짐벌·카메라 공식 렌더 C |
| `phantom2_c22_official_pvplus_gimbal_cam_d.jpg` | 960x420 | DJI 공식 카메라 360 시퀀스(웹아카이브) | Vision+ 짐벌·카메라 공식 렌더 D |
| `phantom2_c23_ifixit_prop_rotation_mark.jpg` | 1688x1266 | iFixit 가이드 35981 (프로펠러) | 암의 회전방향 표시(CW/CCW) — 9450 vs 9450R 구분 |
| `phantom2_c24_ifixit_prop_cw_removal.jpg` | 5733x4300 | iFixit 가이드 35981 (프로펠러) | CW 프로펠러 탈거 |
| `phantom2_c25_ifixit_prop_ccw_removal.jpg` | 5910x4433 | iFixit 가이드 35981 (프로펠러) | CCW 프로펠러 탈거 |
| `phantom2_c26_ifixit_battery_bay_a.jpg` | 4996x3747 | iFixit 가이드 35973 (배터리) | 배터리 베이·슬롯 A |
| `phantom2_c27_ifixit_battery_bay_b.jpg` | 4996x3747 | iFixit 가이드 35973 (배터리) | 배터리 베이·슬롯 B |

### m — 도면·매뉴얼·사양 (13장)

| 파일 | 해상도 | 출처 | 내용 |
|---|---|---|---|
| `phantom2_m01_manual_p2_v14_aircraft_diagram.png` | 1457x2068 | DJI Phantom 2 매뉴얼 v1.4 | Phantom 2 매뉴얼 v1.4 p.5 — 기체 도해 Figure 1-1/1-2 (부품 11개 라벨) |
| `phantom2_m02_manual_p2_v14_specifications.png` | 1457x2068 | DJI Phantom 2 매뉴얼 v1.4 | Phantom 2 매뉴얼 v1.4 p.35 — 사양표 (Wheelbase 350 mm, 1000 g) |
| `phantom2_m03_manual_p2_v14_propeller_9450.png` | 1457x2068 | DJI Phantom 2 매뉴얼 v1.4 | Phantom 2 매뉴얼 v1.4 p.13 — 9인치 프로펠러 9450/9450R 도해 |
| `phantom2_m04_manual_p2_v14_in_the_box.png` | 1457x2068 | DJI Phantom 2 매뉴얼 v1.4 | Phantom 2 매뉴얼 v1.4 p.4 — 구성품 도해 |
| `phantom2_m05_manual_p2_v14_gimbal_ports.png` | 1457x2068 | DJI Phantom 2 매뉴얼 v1.4 | Phantom 2 매뉴얼 v1.4 p.8 — H3-2D/H3-3D 짐벌·AVL58 장착 도해 |
| `phantom2_m06_manual_pvplus_v18_aircraft_p11.png` | 1359x2018 | DJI Vision+ 매뉴얼 v1.8 | Vision+ 매뉴얼 v1.8 p.11 — 기체 소개·도해 |
| `phantom2_m07_manual_pvplus_v18_aircraft_p12.png` | 1359x2018 | DJI Vision+ 매뉴얼 v1.8 | Vision+ 매뉴얼 v1.8 p.12 — 기체 도해 Figure 11/12 |
| `phantom2_m08_manual_pvplus_v18_gimbal_spec.png` | 1359x2018 | DJI Vision+ 매뉴얼 v1.8 | Vision+ 매뉴얼 v1.8 p.13 — 짐벌 사양 |
| `phantom2_m09_manual_pvplus_v18_propellers.png` | 1359x2018 | DJI Vision+ 매뉴얼 v1.8 | Vision+ 매뉴얼 v1.8 p.16 — 프로펠러 장착 도해 |
| `phantom2_m10_manual_pvplus_v18_specifications.png` | 1359x2018 | DJI Vision+ 매뉴얼 v1.8 | Vision+ 매뉴얼 v1.8 p.48 — 사양표 (Motor Diagonal Length 350 mm, 1242 g) |
| `phantom2_m11_manual_pv_v18_specifications.png` | 1457x2068 | DJI Vision 매뉴얼 v1.8 | Vision 매뉴얼 v1.8 p.70 — 사양표 |
| `phantom2_m12_manual_pv_v18_camera_diagram.png` | 1457x2068 | DJI Vision 매뉴얼 v1.8 | Vision 매뉴얼 v1.8 p.18 — 내장 카메라 도해 |
| `phantom2_m13_dji_press_fact_sheet.png` | 2068x2924 | DJI Phantom 2 Fact Sheet | DJI 보도자료 Fact Sheet — 치수 29x29x18 cm, 1000 g, 9인치 프롭 |
---

_수집 2026-08-03. 수집 스크립트: `scratchpad/p2/assemble.py` · `scratchpad/p2/build_specs.py`._
