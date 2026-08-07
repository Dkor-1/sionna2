# DJI Mini 2 (`mini2`) — 참조 이미지 출처

`mini2` 는 **새 기체 키**다. 2026-08-03 수집 전까지 저장소에 이 기체는 없었다.

> ⚠ **혼동 금지.** 저장소의 `mini5pro`(DJI Mini 5 Pro) · `matrice4e`(DJI Matrice 4E) 는 **다른 기체다.**
> 이 폴더는 **2020년 11월 출시된 DJI Mini 2** 전용이다. 형제 기종인 **Mini 2 SE**(FCC ID `SS3-MT2SD22`,
> 모델 `MT2SD22`)와도 구별한다 — 구별 근거는 아래 §변종 판정에 적었다.

**왜 모았나** — Das et al. (IEEE WCL 2026) 이 이 기체를 무향실에서 재고 Table III 에 RCS 계수
(a·b·c·d)를 인쇄했다(`outputs/das_fleet_spec.json` 의 `airframes.mini2`). 우리가 메쉬를 만들어 맞추면
**메쉬 방법 검증이 N=1 에서 N=4 로 간다.**

---

## 0. 한눈에

| 항목 | 값 |
|---|---|
| 총 파일 | **86장** (d 32 · p 12 · t 27 · c 7 · m 8) |
| 내부(분해) 보임 | **예** — iFixit 수리가이드 18장 + FCC 내부사진 9장 + DJI 공식 X-ray 컷어웨이 1장 |
| 치수 도면 | **예** — 매뉴얼 Aircraft Diagram + 사양표 3쪽 + QSG 전개도 + FCC 제품 라벨 |
| 접힘/펼침 | **둘 다** — 공식 렌더·공식 CAD 정사영 각각 양쪽 상태 |
| ⭐ 자(ruler) 들어간 사진 | FCC 제출물 23장 중 **약 20장** — 절대 치수를 사진에서 직접 잴 수 있다. 확인된 예외는 `c03`(배터리 단품, 대신 규격 라벨이 읽힌다) · `t21`(하부커버 제거) · `m08`(라벨 도판) 셋이다 |
| ⭐ 공식 3D CAD | DJI 가 제품 페이지에 올린 **GLB 2개**(펼침·접힘) — 치수 충실도 검증됨(§4) |
| 중복 | **0건** — 86장 전부 md5 유일. 폴더 전수 md5 대조로 확인했고, 걸려 나온 중복 1장은 §5 에 기록하고 지웠다 |
| 무결성 | **86/86 디코드 성공** — PIL `verify()` 후 재오픈까지 통과. 잘린 파일·HTML 오류페이지 없음 |

---

## 1. Das 가 어느 상태로 쟀나 — **펼침(unfolded), 프로펠러 제외**

`outputs/das_fleet_spec.json` 의 Table I 판독값은 Mini 2 열에 **`15.9 cm x 20.3 cm`** 다.
DJI 사용자 매뉴얼 v1.0 (2020.11) p.45 사양표는 이렇게 적는다:

```
Dimensions   International version
             Folded:                       138×81×58 mm
             Unfolded:                     159×203×56 mm     ← 여기
             Unfolded (with propellers):   245×289×56 mm
Diagonal Distance                          213 mm
```

**159 × 203 은 DJI 의 "Unfolded" 문자열과 글자단위로 같다.** 접힘(138×81)도, 프롭 포함(245×289)도
아니다. 따라서 Das 의 Mini 2 치수는 **펼친 상태, 프로펠러 제외한 기체 바깥치수 (길이 × 폭)** 이다.
`folded_state = "unfolded (propellers excluded)"`.

### 이 판정을 뒷받침하는 독립 근거 3가지

1. ⭐ **공식 CAD 로 정확히 재현된다.** DJI 공식 GLB(§4)에서 **프로펠러 8장을 빼고** 바운딩박스를
   재면 **159.1 (길이) × 203.4 (폭) × 56.0 (높이) mm** 다. DJI 공표 `159 × 203 × 56` 과
   각각 **0.06 % · 0.2 % · 0.0 %** 차이다. 즉 DJI 의 "Unfolded" 는 문자 그대로
   **펼침·프롭 제외 (길이 × 폭 × 높이)** 이고, Das 의 15.9 × 20.3 cm 는 그 앞 두 수다.
2. **프롭 포함 치수도 같은 CAD 에서 풀린다.** 프롭 반경 59.5 mm 를 최대로 벌리면
   길이 = 64.3+59.5+61.1+59.5 = **244.4 mm** (DJI 245), 폭 = 2×(85.5+59.5) = **290 mm** (DJI 289).
   (GLB 에 모델링된 프롭 회전각 그대로면 211.0 × 265.0 mm 다 — 2날 프롭은 회전각이 자유라
   DJI 의 245×289 는 **최대 벌림** 구성으로 잰 값이다.)
3. **자매 기체가 같은 규약을 쓴다.** Das Table I 의 M350 RTK 열은 `81.0 cm x 67.0 cm` 인데,
   이는 DJI 가 공표한 M350 RTK **펼침·프롭 제외 810 × 670 mm** 와 글자단위로 같다.
   Mini 2 와 M350 RTK 는 Das 본문에서 **둘 다 출처 [7] (Wang et al.)** 로 표시된 기체다 —
   같은 출처가 같은 규약(DJI 공표 "unfolded, props excluded" L×W)을 쓴 것으로 읽힌다.

> ⚠ **Table I 의 "Dimension" 은 기체마다 규약이 다르다.** `das_fleet_spec.json` 은 Phantom 3 열의
> `35 x 20 cm` 를 (수평대각 × 높이)로 읽었고 그 근거(Yuan §II-A)가 확실하다. Mini 2 · M350 RTK 는
> 위와 같이 (길이 × 폭)이다. **Das 원문은 규약을 정의하지 않는다** — 열마다 출처가 다른 탓으로 보인다.
> 이 문단은 그 사실을 기록해 두는 것이지 Das 를 정정하는 게 아니다.

> ⚠ **아직 모르는 것:** Das 가 프롭을 **달고** 쟀는지 **떼고** 쟀는지는 위 판정으로 알 수 없다.
> 위 결론은 "Table I 에 적힌 숫자가 어느 공표치수 문자열인가"까지만 말한다. 측정 시 프롭 장착 여부·
> 프롭 회전각·편파는 Das 본문에 없다(`das_fleet_spec.json` 의 `polarisation` 도 UNVERIFIED 로 남아 있다).

---

## 2. 변종 판정 — 이게 정말 Mini 2 인가

| 근거 | 내용 |
|---|---|
| **FCC 제품 라벨** (`mini2_m08`) | 라벨에 **"DJI Mini 2"**, **`Model: MT2WD`**, `FCC ID: SS3-MT2WD2007` 가 인쇄돼 있다. 결정적 증거다. |
| **라벨의 배터리 규격** | 라벨 `7.7V ⎓ 2250mAh, 17.32Wh` = 매뉴얼 p.47 의 **Intelligent Flight Battery (International Version)** `2250 mAh / 7.7 V / 17.32 Wh` 와 완전 일치. JP 판(1065 mAh / 8.09 Wh)이 아니다. |
| **Mini 2 SE 배제** | Mini 2 SE 는 **별도 FCC ID `SS3-MT2SD22`** 로 등록돼 있고 fccid.io 표제가 `DJI Mini 2 SE` 다. 이 폴더의 자료는 전부 `MT2WD2007` 또는 `MT2PD2007` 에서 왔다. |
| **프로펠러 날 수** | `mini2_c07` 에서 로터 하나에 **날 2장**이다(세 번째로 보이는 것은 회색 **암**이다 — 확대해서 확인함). 매뉴얼 p.20 "The two blades attached to one motor are the same" 와 일치. |
| **DJI 렌더 배지** | `mini2_d01`·`d03`·`d07` 의 암/동체 배지가 **"MINI 2"** 로 읽힌다. |

### 쓰인 FCC 등록 2건 — 둘 다 Mini 2 다

| FCC ID | 모델 | 최종 처분일 | fccid.io 표제 | 시험소 | 이 폴더에서 |
|---|---|---|---|---|---|
| `SS3-MT2PD2007` | MT2PD2007 | **2020-10-06** | Camera Drone | Bay Area Compliance Labs | `p15`, `c01`, `c02` |
| `SS3-MT2WD2007` | MT2WD | **2022-04-01** | **DJI Mini 2** | TUV Rheinland (Shenzhen) | `p10`~`p14`, `t20`~`t28`, `c03`~`c07`, `m08` |

`MT2PD2007` 은 2020-10-06 처분 — Mini 2 출시(2020-11) 직전이라 **원 인증**이다.
`MT2WD2007` 은 2022-04-01 처분이지만 **라벨이 "DJI Mini 2"** 이고 배터리 규격이 Mini 2 국제판과 같다.
두 등록의 기체 외형은 사진상 동일하다.

> ⚠ **남는 불확실성:** `MT2WD2007` 이 왜 2022년에 별도 ID 로 다시 등록됐는지(무선 모듈 개정 추정)는
> 확인하지 못했다. 형상 목적으로는 무관하다 — 라벨·사진·배터리가 전부 Mini 2 를 가리킨다.

---

## 3. 라이선스 — 파일별로 다르다. **재배포 전 반드시 읽을 것**

| 출처 | 파일 | 라이선스 상태 |
|---|---|---|
| **DJI 제품 CDN** (`_d01`~`_d10`) | 10장 | ⚠ **공개 라이선스 없음(저작권 DJI).** 내부 랩 발표·형상 대조용으로만 받았다. 리포트에 실을 때 출처(DJI 제품 페이지) 표기, **파일 자체 재배포 금지.** |
| **DJI 공식 CAD(GLB) 렌더** (`_d20`~`_d49`) | 20장 | ⚠ 위와 같음. 원본 GLB 는 DJI 저작물이고, 이 20장은 그것을 우리가 렌더한 **2차 산출물**이다. |
| **DJI 문서 PDF** (`_m01`~`_m07`) | 7장 | ⚠ 위와 같음(© 2020 DJI All Rights Reserved). |
| **iFixit 수리가이드** (`_p01`~`_p06`, `_t01`~`_t18`) | 24장 | **CC BY-NC-SA 3.0** (iFixit 가이드 기본 라이선스). 비영리·동일조건변경허락·출처표시면 재배포 가능. 가이드 URL 을 아래 표에 남겼다. |
| **FCC 제출물** (`_p10`~`_p15`, `_t20`~`_t28`, `_c01`~`_c07`, `_m08`) | 22장 | **미국 연방 공개기록.** FCC 인증 신청서의 공개 전시물(Exhibit)이며 누구나 열람·복제 가능하다. 제출자는 SZ DJI Technology. |

---

## 4. ⭐ DJI 공식 3D CAD (GLB) — 치수 충실도 검증

DJI Mini 2 제품 페이지의 3D 뷰어가 **GLB 2개**를 서비스한다. 2026-08-03 기준 **URL 이 살아 있다.**

| 상태 | URL | 크기 |
|---|---|---|
| 펼침 | `https://dji-official-fe.djicdn.com/assets/uploads/p/f2a89648-ce9d-4318-9454-8a1a79cf6db7/WM161_zhankai_1k.glb` | 7.71 MB |
| 접힘 | `https://dji-official-fe.djicdn.com/assets/uploads/p/f2a89648-ce9d-4318-9454-8a1a79cf6db7/wm161_v11_zhedie_1k.glb` | 7.49 MB |

`WM161` 은 **DJI Mini 2 의 내부 기종 코드**이고, `zhankai`(展开)=펼침, `zhedie`(折叠)=접힘이다.

### 치수 검증 — GLB 는 미터 단위이고 공표치수와 맞는다

| 양 | GLB 실측 | DJI 공표 | 오차 |
|---|---|---|---|
| 접힘 바깥치수 | **137.659 × 83.126 × 56.101 mm** | 138 × 81 × 58 mm | **−0.25 %** / +2.62 % / −3.27 % |
| 펼침 높이 | **56.4 mm** | 56 mm | +0.6 % |
| **모터 대각거리**(모터축 기준) | **213.051 mm** | **213 mm** | **+0.024 %** |
| 〃 (블레이드 메쉬 중심 기준) | 213.93 mm | 213 mm | +0.4 % |
| **프로펠러 지름**(모터축 기준) | **119.875 mm** (뒤) / 118.591 mm (앞) | 미공표 | 평균 119.23 — 4.7 in = 119.4 mm 와 0.14 % 차 |
| 〃 (블레이드 메쉬 중심 기준) | 119.11 mm (뒤) / 118.14 mm (앞) | 미공표 | — |

**모터 대각 213.051 vs 공표 213 mm 가 0.024 % 안에서 맞는 것**이 핵심 검증이다.
GLB 를 형상 소스로 써도 된다는 뜻이다.

> ⭐ **2026-08-07 정정.** 이 표의 세 줄이 GLB 를 실제보다 **약하게** 적고 있었다.
> · 대각 213.9 는 **프로펠러 블레이드 메쉬의 중심**끼리 잰 값이다. DJI 가 공표하는
>   'Diagonal Distance' 는 **모터 축 사이 거리**(휠베이스)이고, 모터 벨 파트
>   (polySurface76/96/90/53) 축으로 재면 **213.051 mm**(좌우 두 대각의 차 0.0004 mm)다.
>   오차가 +0.4 % 가 아니라 **+0.024 %** — 17 배 더 잘 맞는다. 두 값이 갈리는 이유는
>   뒤 블레이드 메쉬가 자기 모터축에서 1.121 mm 벗어나 있기 때문이다(앞은 0.368 mm).
> · 프로펠러 지름도 같은 이유로 갈린다. 도는 축은 모터축이므로 물리적으로 옳은 지름은
>   모터축 기준이다. ⚠ 등록 상수 `prop_dia_mm=119.1` 은 **그대로 둔다**(0.1 % 차이).
> · 접힘 길이는 **공표보다 작다**(137.659 < 138) — 부호가 반대로 적혀 있었다.
> 근거: `outputs/meshdef_mini2_glb.json` (C2·C3·C4) — 공식 GLB 를 다시 열어 잰 값.

### GLB 에서 실측한 로터 배치 (기체 중심 원점, mm)

| 로터 | x (우+) | z (기수+) | y (상+) |
|---|---|---|---|
| 앞 좌/우 | ∓87.8 | +64.3 | **+24.7** |
| 뒤 좌/우 | ∓85.5 | −61.1 | **+3.2** |

* 앞 트랙 175.6 mm, 뒤 트랙 171.1 mm, 앞뒤 125.4 mm → **완전한 정사각형이 아니라 살짝 사다리꼴**이다.
* **앞 로터가 뒤 로터보다 21.5 mm 높다.** Mini 2 는 앞 암이 동체 위쪽, 뒤 암이 아래쪽에 붙는 구조라
  그렇다(그래서 앞 다리가 더 길다 — GLB 최저점도 앞다리다).

### 정사영 렌더 20장 (`_d20`~`_d49`) 의 좌표 규약

pyrender·OpenGL 이 없는 환경이라 numpy z-버퍼 래스터라이저를 직접 써서
(`scratchpad .../mini2/render_glb.py`) **원근 없는 정사영**으로 렌더했다. 배경은 알파다.

* glTF 축: **+y = 위**, **+z = 기수(앞)**, 카메라는 정사영.
* `front` = +z 쪽에서 본 것(기수를 마주봄), `rear` = −z 쪽, `top` = 위에서(이미지 위쪽이 기수),
  `bottom` = 아래에서(**이미지 아래쪽이 기수**).
* ⚠ `left`/`right` 는 **카메라가 −x / +x 쪽에 있다는 뜻**일 뿐, 기체의 좌현/우현 라벨은
  독립 확인하지 않았다. 기체가 좌우대칭이라 실루엣·RCS 목적에서는 차이가 없다.
* **+z 가 기수라는 근거 3가지**: (a) 짐벌 돌출부가 +z 끝에 있다, (b) 앞 로터가 높다는 구조가
  Mini 2 의 실제 접이 방식과 맞는다, (c) 가장 긴 다리가 +z 쪽이다.
* 각 렌더의 **mm/px 배율**은 `scratchpad .../mini2/glb_render_scale.json` 에 있다
  (예: `unfolded_top` 0.2006 mm/px). 픽셀에서 치수를 되잴 수 있다.

---

## 5. 파일 목록

### d — 공식 렌더

#### d01–d10 : DJI 제품 CDN 원본

| 파일 | 상태 | 시선 | 무엇이 보이나 | 원본 URL |
|---|---|---|---|---|
| `mini2_d01_official_folded_iso_white.jpg` | 접힘 | 앞왼쪽 위 iso | 1890×1514. "MINI 2" 배지, 접힌 암·다리, 짐벌 | `.../dps/8a055532d4861d898e4231bd3f266ee1.jpg` |
| `mini2_d02_official_folded_iso_black.png` | 접힘 | 앞왼쪽 위 iso | 1350×900, 검은 배경. d01 과 같은 자세 | `.../dps/72669a179fea876f7f245a7fc10d3724.png` |
| `mini2_d03_official_folded_front34_white.jpg` | 접힘 | 앞왼쪽 3/4 | 1280×640. 짐벌·전방 흡기구 | `.../cms/uploads/0fdff7fab9f96f0db0d70fbf71dab93c.jpg` |
| `mini2_d05_official_unfolded_iso_black.png` | 펼침 | 앞왼쪽 위 iso | 1600×1202, 검은 배경. 프롭 4장 정지 | `.../dps/38ee492a39d81bac34f38264541a9fcb.png` |
| `mini2_d06_official_unfolded_front_alpha.png` | 펼침 | 정면 살짝 위 | ⭐ 640×640, **알파 배경**. 좌우대칭·다리 스탠스·짐벌이 가장 깨끗하다 | `.../cms/uploads/fc92116ae9082f8239b53730685ea68d.png` |
| `mini2_d07_official_unfolded_front34_flight.jpg` | 펼침 | 앞왼쪽 | 1200×700, 산 배경. "MINI 2" 배지 | `.../dps/0f6cfcc18197c6ece06ae3250e8ed8ca.jpg` |
| `mini2_d08_official_unfolded_side_flight_white.jpg` | 펼침 | 측면 | 2696×1124, 흰 배경. 프롭 회전 블러 | `.../dps/ce6fe7bdc09c110b100401d1d3790a85.jpg` |
| `mini2_d09_official_xray_cutaway_internals.jpg` | 접힘 | 앞왼쪽 위 iso | ⭐⭐ 1890×1514 **공식 X-ray 컷어웨이**. 셸 투명 처리 — **배터리 팩·메인 PCB·GPS 패치 안테나(금색)·모터 4개 고정자 권선·방열핀**이 그대로 보인다 | `.../dps/08b684c39b960cbadfd5086b03d85f6b.jpg` |
| `mini2_d10_official_propguard_360_installed.jpg` | 펼침 | 위 3/4 | 992×992. 360° 프롭가드 장착 상태 | `.../dps/8e9fcdf6b61af6baf00e00bdbb9223e0.jpg` |
| `mini2_d11_official_unfolded_side_elevation_249g.jpg` | 펼침 | ⭐ **측면 정입면** | 2696×1124, 흰 배경. 동체 측면 실루엣·다리 높이·짐벌 돌출·암 두께가 가장 곧게 읽힌다. "ULTRA LIGHT 249g" 배지 | `.../dps/e0307f8b9e91f0376024487da235c729.jpg` |
| `mini2_d12_official_unfolded_front_elevation_flight.jpg` | 펼침 | ⭐ **정면 정입면** | 1200×480. 좌우대칭·전방 암 스팬·짐벌 정면·다리 스탠스. "MINI 2" 배지 | `.../dps/22fd7e6752f30daa8f462a5168be8012.jpg` |
| `mini2_d13_official_folded_top_rear_iso_4k.jpg` | 접힘 | 위-뒤 iso | ⭐ 3840×2160 — **접힘 상태 최고해상도**. 상면 셸 곡률·접힌 암 적층·DJI 로고. "MINI 2" 배지 | `.../dps/6eec4c506a4b9d89c830aa9267916749.jpg` |

호스트는 전부 `https://dji-official-fe.djicdn.com`. 2026-08-03 기준 살아 있는 원본 CDN 응답이고
Wayback 사본이 아니다. **자산 URL 은** 제품 페이지가 지원 페이지로 축소돼서
Wayback 스냅샷(`web.archive.org/web/2021100100000id_/https://www.dji.com/mini-2`) 의 HTML 에서 뽑았다.

> ⚠ **삭제된 `d04` 기록.** 처음엔 `cms/uploads/cc16780956a45dce97a3201eb3add333.jpg` 를
> `mini2_d04_official_folded_rear34_white.jpg`("접힘 뒤오른쪽 3/4")로 받아뒀다. **틀렸다.**
> 그 URL 을 다시 받아 md5 를 대조하니 `d03`(`0fdff7fab9...`)과 **바이트 단위로 동일**하다
> (`e7c6cc96c4c707e0c5fa7fa7bcf006bf`, 26964 B, 둘 다 200 응답). DJI CDN 이 서로 다른 해시
> 경로에 같은 이미지를 얹어놨고, 뒤(rear) 시선은 애초에 존재하지 않았다. 중복 1장을 지우고
> 그 자리에 진짜로 새로운 뷰 3장(`d11`·`d12`·`d13`)을 넣었다. 현재 폴더에 md5 중복은 **0건**이다.
>
> **뒤(rear) 시선은 다른 데서 이미 충분하다** — CAD 정사영 `d21`(펼침 rear)·`d41`(접힘 rear),
> 그리고 ⭐자가 들어간 실물 FCC 사진 `p13`·`p14`(후면, 배터리 삽입/분리). 공식 렌더에 rear 가
> 빠진 것은 손실이 아니다.

`d11`~`d13` 도 같은 Wayback HTML 에서 나온 같은 CDN 호스트다. **Mavic Mini(1세대)가 아니라는 근거**:
`d12`·`d13` 은 동체에 **"MINI 2" 각인**이 직접 보인다. `d11` 은 배지가 "ULTRA LIGHT 249g" 뿐이라
각인으로는 못 가르지만, 상면 앞쪽의 **메시 흡기 그릴**이 있다 — 이 그릴은 Mini 2 에만 있고
(`d01`·`d03`·`c042` 등 "MINI 2" 각인이 확인된 컷과 동일 형상) 1세대 Mavic Mini 에는 없다.
셋 다 Mini 2 전용 제품 페이지 HTML 에서 나왔다는 점도 같이 본다.

#### d20–d49 : DJI 공식 CAD(GLB) 정사영 렌더 (§4 참조)

| 번호 | 상태 | 뷰 |
|---|---|---|
| `d20`~`d29` | **펼침** | front · rear · left · right · top · bottom · iso_fl · iso_fr · iso_rl · iso_rr |
| `d40`~`d49` | **접힘** | 같은 10뷰 |

### p — 실물 제품 사진

| 파일 | 출처 | 무엇이 보이나 |
|---|---|---|
| `mini2_p01_ifixit_unfolded_front.jpg` | iFixit Battery Replacement step1 | 펼침 정면, 실기체 |
| `mini2_p02_ifixit_unfolded_top34.jpg` | iFixit Drone Body step1 | 펼침 위 3/4, 흰 바닥 |
| `mini2_p03_ifixit_unfolded_iso_above.jpg` | iFixit Drone Body step1 | 펼침 위 iso |
| `mini2_p04_ifixit_top_shell_screws_annot.jpg` | iFixit Drone Body step2 | ⭐ 평면도 + 상부셸 나사 4곳 표시 |
| `mini2_p05_ifixit_belly_bottom.jpg` | iFixit Drone Body step5 | ⭐ **배면(벨리)** — 하방 비전센서·적외선·통풍구 |
| `mini2_p06_ifixit_battery_in_hand_scale.jpg` | iFixit Battery step2 | 손에 든 상태 — 크기 감각 |
| `mini2_p10_fcc_mt2wd_ext_top_ruler.jpg` | FCC MT2WD Ext Fig.1 | ⭐ **평면도 + cm 자** |
| `mini2_p11_fcc_mt2wd_ext_bottom_ruler.jpg` | FCC MT2WD Ext Fig.2 | ⭐ **배면도 + cm 자** |
| `mini2_p12_fcc_mt2wd_ext_front_ruler.jpg` | FCC MT2WD Ext Fig.3 | ⭐ **정면도 + cm 자**, 짐벌 정면 |
| `mini2_p13_fcc_mt2wd_ext_rear_battery_in.jpg` | FCC MT2WD Ext Fig.4 | 후면, 배터리 장착 |
| `mini2_p14_fcc_mt2wd_ext_rear_battery_out.jpg` | FCC MT2WD Ext Fig.5 | 후면, 배터리 제거 — 전지실 내부 |
| `mini2_p15_fcc_mt2pd_ext_unfolded_ruler_grid.jpg` | FCC MT2PD Exhibit B | ⭐ 펼친 기체 + **직교 2축 자 격자**(파란 배경) |

### t — 분해

`t01`~`t18` = iFixit 수리가이드(고해상 원본을 긴변 2200 px 로 축소).
`t20`~`t28` = FCC MT2WD2007 내부사진(전부 자 포함).

| 파일 | 무엇이 보이나 |
|---|---|
| `t01` `t02` | 상부셸 제거 — **메인보드 + GPS 패치 안테나** 전체 배치 |
| `t03` `t04` `t05` | **검은 핀 방열판**(메인보드 위) 나사 위치 → 근접 → 들어냄 |
| `t06` | ⭐ 메인보드 베이 **탑다운**, 파란 서멀패드 위치 표시 |
| `t07`~`t10` | 메인보드 앞/뒤면, 서멀패드, 커넥터 |
| `t11` | ⭐⭐ **GPS 패치 안테나** (세라믹 패치) 근접 |
| `t12` `t13` | 짐벌 베이 · 짐벌 카메라 블록 |
| `t14` `t15` `t16` | 암 제거 — GPS 패치·모터 배선·**암 분리** 상태 |
| `t17` `t18` | 전지실 내부 · 차폐 포일 |
| `t20` | ⭐ 상부커버 제거 + 자 (FCC Fig.1) |
| `t21` | 하부커버 제거 — 방열판·비전센서 (FCC Fig.2) |
| `t22`~`t26` | 메인보드 view 1~4 (FCC Fig.3·5·6·7·8) |
| `t27` | ESC("Motivation") 보드 (FCC Fig.9) |
| `t28` | **프로펠러 모터** 내부 (FCC Fig.14) |

### c — 부품 단품

| 파일 | 무엇이 보이나 |
|---|---|
| `mini2_c01_fcc_mt2pd_gps_patch_antenna_ruler.jpg` | ⭐⭐ **GPS 패치 안테나 + mm 자** — 패치 변길이를 사진에서 직접 잴 수 있다 |
| `mini2_c02_..._ruler_b.jpg` | 같은 부품, 다른 각도 |
| `mini2_c03_fcc_mt2wd_battery.jpg` | 지능형 비행 배터리 단품 (FCC Fig.15) |
| `mini2_c04`~`c06_..._gimbal_board_1..3.jpg` | 짐벌 보드 3면 (FCC Fig.11·12·13) |
| `mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg` | ⭐ **2날 프로펠러 + cm 자** (`p10` 에서 잘라냄) |

### m — 도면·문서

| 파일 | 출처 | 무엇이 있나 |
|---|---|---|
| `mini2_m01_manual_v10_aircraft_diagram.png` | User Manual v1.0 p.8 | **Aircraft Diagram** — 13개 부품 번호(짐벌·모터·프롭·안테나·하방비전·적외선·전지실·USB-C·microSD) |
| `mini2_m02_manual_v10_specs_dimensions.png` | 〃 p.45 | ⭐ **치수·중량·속도** — 접힘/펼침/프롭포함, 대각 213 mm |
| `mini2_m03_manual_v10_specs_gimbal_camera.png` | 〃 p.46 | 짐벌 가동범위·센싱·카메라 |
| `mini2_m04_manual_v10_specs_battery_rc.png` | 〃 p.47 | 배터리·조종기·충전기 |
| `mini2_m05_qsg_v14_unfold_sequence.png` | Quick Start Guide v1.4 p.3 | **암 전개 순서** 그림 |
| `mini2_m06_propeller_guide_v10_illustration.png` | Propellers User Guide v1.0 | 프로펠러 장착 그림 |
| `mini2_m07_propguard_guide_v10_install.png` | 360° Propeller Guard UG v1.0 | 가드 장착 — 암·다리 형상이 선화로 |
| `mini2_m08_fcc_mt2wd_product_label.png` | FCC MT2WD2007 Label | ⭐ **"DJI Mini 2" / Model MT2WD / 7.7V 2250mAh 17.32Wh** — 변종 판정 근거 |

> ⚠ **공식 "치수 기입 3면도"는 없다.** Phantom 3 매뉴얼과 달리 DJI Mini 2 문서에는 치수선이 그려진
> 정투상도가 없다. `m01` 은 부품 지시도이고 치수선이 없으며, `m02` 는 숫자 표다.
> **치수선이 있는 도면이 필요하면** `_d20`~`_d49` 정사영 렌더 + `glb_render_scale.json` 의 mm/px 배율,
> 또는 자가 들어간 FCC 사진(`p10`~`p12`, `p15`)을 쓰면 된다.

---

## 6. 원본 문서 URL (전부 2026-08-03 확인, 살아 있음)

| 문서 | URL |
|---|---|
| User Manual v1.0 EN | `https://dl.djicdn.com/downloads/DJI_Mini_2/DJI_Mini_2_User_Manual_EN.pdf` |
| User Manual EN (날짜판) | `https://dl.djicdn.com/downloads/DJI_Mini_2/20210222/DJI_Mini_2_User_Manual_EN.pdf` |
| Quick Start Guide v1.4 | `https://dl.djicdn.com/downloads/DJI_Mini_2/20210129/DJI_Mini_2_Quick_Start_Guide.pdf` |
| Propellers User Guide v1.0 | `https://dl.djicdn.com/downloads/DJI_Mini_2/Accessories/DJI_Mini_2_Propellers_User_Guide.pdf` |
| 360° Propeller Guard UG v1.0 | `https://dl.djicdn.com/downloads/DJI_Mini_2/Accessories/DJI_Mini_2_360%C2%B0_Propeller_Guard_User_Guide.pdf` |
| FCC `SS3-MT2WD2007` | `https://fccid.io/SS3-MT2WD2007` |
| FCC `SS3-MT2PD2007` | `https://fccid.io/SS3-MT2PD2007` |
| iFixit Device | `https://www.ifixit.com/Device/DJI_Mini_2` |
| iFixit 가이드 (7편) | Battery `/Guide/.../149601` · Drone Body `/149681` · Main Board `/149748` · Gimbal Camera `/149750` · Drone Arm `/149759` · Ribbon Cable `/153752` · Gimbal Calibration `/153754` |

**DJI 제품 페이지는 없어졌다** — `dji.com/mini-2` 는 `dji.com/support/product/mini-2` 로 302 된다.
제품 렌더·GLB 자산 URL 은 Wayback 스냅샷 HTML 에서 뽑았고, 파일은 CDN 원본에서 직접 받았다.

---

## 7. 재현 절차

1. `dji.com/mini-2` → 지원 페이지로 302. Wayback `20211001000000id_` 스냅샷 HTML 을 받는다.
2. HTML 에서 `djicdn.com` 자산 URL 89개를 뽑아 전부 받고, 크기·내용으로 Mini 2 것만 고른다
   (사이트 공통 내비/푸터에 다른 기종 썸네일이 섞여 있다 — Phantom·Osmo·Agras 등).
3. 같은 HTML 에 **GLB 2개** URL 이 들어 있다(`WM161_zhankai_1k.glb` / `wm161_v11_zhedie_1k.glb`).
4. iFixit `api/2.0/search` → 가이드 7편 → `api/2.0/guides/<id>` 의 `steps[].media.data[].original` 로
   4000~5328 px 원본 45장. (가이드끼리 선행 가이드를 인용해 중복이 많다 — 유니크만 추린다.)
5. FCC: fccid.io 문서 페이지의 `data-pdf-url` 속성이 `/m/<sha256>.pdf` 를 가리킨다.
   그 PDF 를 받아 PyMuPDF `get_images(full=True)` + `extract_image` 로 **원본 해상도** JPEG 를 꺼낸다.
   (페이지 렌더가 아니라 임베드 이미지를 그대로 꺼내는 쪽이 훨씬 선명하다.)
6. 공표 스펙은 `outputs/mini2_specs.json` 에 정리했다.
