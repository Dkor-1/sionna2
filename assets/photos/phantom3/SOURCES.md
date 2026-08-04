# DJI Phantom 3 Professional — 참조 이미지 출처

`phantom3` 기종은 2026-08-03 까지 **사진이 0장**이었다(`assets/photos/` 에 나머지 7기체만 있었다).
아래는 그날 수집한 세트다. 전부 **DJI 공식 제품 페이지 렌더**이고, 접두사 `_d*` 가 그 뜻이다 —
재판매점 사진·팬 렌더·전시장 스냅은 넣지 않았다.

> ⚠ **라이선스는 불명확하다.** DJI 제품 이미지에는 공개 라이선스가 붙어 있지 않다(저작권 DJI).
> **내부 랩 발표·형상 대조용**으로 받았다. 리포트·논문·발표에 실을 때는 출처(DJI 제품 페이지)를
> 표기하고, 파일 자체의 재배포는 하지 않는다.

## 변종 — `outputs/p3_specs.json` 이 고른 것과 같은가

`outputs/p3_specs.json` 은 **Phantom 3 Professional (2015, WM331)** 을 골랐다. 이 폴더도 같다.

* `_d01` · `_d02` · `_d04` · `_d05` 는 **Professional 제품 페이지(`dji.com/phantom-3-pro`) 의 자산**이다.
  `_d01` 의 동체 배지가 **"PHANTOM PROFESSIONAL"** 로 읽히고, 뒷암 스트라이프가 **금색**이다
  (Advanced 는 은색, Standard 는 적색).
* `_d03` · `_d06` 은 **Phantom 3 SE 제품 페이지의 자산**이다. 형상은 같다 —
  `p3_specs.json` `variant.shared_across_all_variants` 가 근거다: DJI 는 Pro/Adv/SE/Standard 에
  **하나의 셸 부품**을 팔고(djioemparts "Upper Shell for Phantom 3 Pro/Adv/SE/Sta"),
  외형 **289.5 × 289 × 185 mm**·모터 대각 **350 mm**·**9450(240 mm)** 프롭이 전 변종 공통이다.
  SE 도 뒷암 스트라이프가 금색이라 렌더의 색까지 Professional 과 같다.
  → **실루엣 대조에 쓰는 한 변종 차이는 없다.** 그래도 파일명·표에 SE 라고 적어 둔다.
* 왜 SE 페이지 것을 썼나:
  1. **톱뷰가 Professional 페이지에 없다.** DJI 공식 문서에도 평면도가 없다
     (`p3_specs.json` `registry_fields.body_lw.note`: User Manual v1.8 의 Aircraft Diagram 은
     front·rear·bottom·side 만 있다). 공식 톱뷰는 SE 페이지의 `s1-img` 가 유일했다.
  2. SE 배너는 **알파 채널**이 있어 실루엣이 분리 임계값에 흔들리지 않는다. Professional 의
     히어로 컷(`_d01`)은 흰 기체 + 거의 흰 배경 JPEG 이라 임계값 민감도가 **51 %** 다(아래 §분리 품질).

## 파일

| 파일 | 시선방향(선언) | 무엇이 보이나 | 원본 URL | sha256(앞16) |
|---|---|---|---|---|
| `phantom3_d01_official_iso34.jpg` | 3/4 앞왼쪽, 위 (az 35 / el 22) | Professional 제품 히어로 렌더 1266×856. 배지 "PHANTOM PROFESSIONAL", 금색 스트라이프, 프롭 4장 정지, 짐벌·카메라 장착 | `https://www5.djicdn.com/assets/images/products/phantom-3-pro/index/phantom-3-pro-v2@2x-011d1bce9f42d76ddb1c4e4ae3332421.jpg` | `b3eb6841344ff66a` |
| `phantom3_d02_official_front.png` | 정면, 살짝 위 (az 0 / el 13) | Professional 페이지 배너 정면 컷 330×208, **알파 배경**. 좌우대칭·다리 스탠스·짐벌 위치가 가장 깨끗하다 | `https://www5.djicdn.com/assets/images/products/phantom-3-pro/banner-front-920740292b6ace5b71805627cc16d9e4.png` | `1b21a387b2f2c2fa` |
| `phantom3_d03_official_top.png` | 위에서 (el 85, 방위 무의미) | ⭐ **공식 톱뷰** 876×884, **알파 배경**. 프롭 4장 정지, 4암 X 배치, 배터리 해치(그림 위쪽=후미), 앞쪽에 짐벌이 살짝 보인다. Phantom 3 **SE** 페이지 자산 | `https://www2.djicdn.com/assets/images/products/phantom-3-se/s1-img-2d6f5280089a6c626f47ba93276da8de.png` | `d98c6e843150ca12` |
| `phantom3_d06_official_se_iso34.png` | 3/4 앞왼쪽, 위 (az 28 / el 16) | 1460×860, **알파 배경**. Phantom 3 **SE** 배너(배지 "PHANTOM SE"). `_d01` 과 같은 자세를 **임계값 없는 실루엣**으로 다시 잰다 | `https://www1.djicdn.com/assets/images/products/phantom-3-se/banner-fa7b98ace0a3510dfed4b4d751137a6a.png` | `3c747f1878e8197f` |
| `phantom3_d04_official_iso34_v1.jpg` | (미등록) | `_d01` 의 **이전 판** 렌더. 자세가 거의 같다 | `https://www2.djicdn.com/assets/images/products/phantom-3-pro/index/phantom-3-pro@2x-f072f5a0e0268a2cd2443b92f5b6f9e7.jpg` | `5f8aa0e4e372d505` |
| `phantom3_d05_official_front34_spinning_props.png` | (미등록) | 정면 3/4, **프롭이 돌고 있다**(모션블러) | `https://www5.djicdn.com/assets/images/products/phantom-3-pro/aircraft/s2-img-f7b0a98536ccd6b5ac86086966e2bf89.png` | `e4140559ccaebbfe` |

**등록 상태** — `src/viz_mesh_photo.py` 의 `PHOTOS["phantom3"]` 에 `_d01`·`_d02`·`_d03`·`_d06` 4장을 등록했다.
`_d04`(자세 중복)와 `_d05`(프롭 모션블러)는 `EXCLUDED` 에 이유와 함께 적어 두었다 — 원장
`outputs/mesh_compare_photo.json` 의 `_meta.excluded` 로 나간다.

## 어떻게 찾았나 (재현 절차)

1. `dji.com/phantom-3-pro` 는 지금 **지원 페이지로 축소**되어 제품 렌더가 없다.
2. Wayback 스냅샷 `web.archive.org/web/20160909044924id_/http://www.dji.com/phantom-3-pro` 의
   HTML 에서 `djicdn.com` 자산 URL 을 뽑았다.
3. 이어서 CDX API 로 `www{1..5}.djicdn.com/assets/images/products/phantom-3*` 를 훑어
   Pro/Adv/Standard/SE 자산 329개의 목록을 만들었다.
4. **자산 자체는 아직 CDN 에서 그대로 서비스된다** — 위 표의 URL 은 (2026-08-03 기준) 살아 있고,
   받은 파일은 Wayback 사본이 아니라 원본 CDN 응답이다.

## 분리 품질 (실측, `viz_mesh_photo.photo_mask`)

| 파일 | 분리 방식 | 임계값 민감도 |
|---|---|---|
| `_d01` | 배경색 거리 (thr 0.055) | **51 %** — 흰 기체 + 거의 흰 배경. phantom4 사진들과 같은 문제이고, 그림에 "Silhouette is threshold-bound" 로 뜬다 |
| `_d02` · `_d03` · `_d06` | **알파 채널** | 해당 없음 (임계값을 안 쓴다) |

→ 헤드라인을 읽을 때 `_d01` 의 IoU 는 메쉬 충실도만이 아니라 **분리 임계값**도 재고 있다.
같은 자세를 알파로 다시 잰 `_d06` 이 그 교차검증이다.

## 선언한 시선방향이 맞나 — 거친 확인 (2026-08-03, 원장 미갱신)

등록할 때 적은 `expect` 가 엉뚱한 자리를 가리키면 헤드라인 IoU 가 형상이 아니라 내 오독을 잰다.
그래서 **메모리 상에서만**(파일 출력 없음) `fit_pose` 를 거친 격자(`quick`, 340 px)로 한 번 돌렸다.
아래 숫자는 **거칠다 — 원장(`outputs/mesh_compare_photo.json`)의 값이 아니다.** 판정용일 뿐이다.

| 파일 | 선언 (az/el) | 정합 결과 | 선언과의 차 | 자유 카메라 이득 |
|---|---|---|---|---|
| `_d02` 정면 | 0 / 13 | 0 / 16 | **3°** | 0 (없음) |
| `_d03` 톱 | 0 / 85 | 180 / 80 | 15° (el 80 에서 방위는 롤과 겹친다) | 0 |
| `_d01` 3/4 | 35 / 22 | 45 / 12 | 13.8° (창 26° 안) | **0** — 자유 카메라도 같은 자리 |
| `_d06` 3/4(SE) | 28 / 16 | 28 / 14 | **2°** | 0 |

네 장 모두 선언한 창 안에서 정합됐고 `free_iou_gain` 이 0 이다 — **틀린 각도에 더 잘 맞는 장은 없다.**
`_d01` 은 정합이 선언보다 고각을 낮게 잡는데, 그 장의 마스크가 흰 배경에서 동체 윗면을 놓치기
때문으로 보인다(§분리 품질). **선언값은 정합 결과에 맞춰 고치지 않았다** — `expect` 는 사람이
사진을 보고 적는 독립 관측이어야 검사 구실을 한다.

## 🔴 받았다가 **뺀** 후보들 (반증 보존)

* **FCC 인증 사진** — FCC ID `SS3-WM3231503`, Exhibit B "EUT External Photographs"
  (`https://fccid.io/SS3-WM3231503/External-Photos/Ext-Photos-2588737.pdf`, 2015-10-14 공개, 640×480 4장:
  All/Top/Bottom/Side View). 실루엣용으로 **부적합**하다: (1) **짐벌·카메라가 없고 프롭도 안 달린**
  기체라 우리 메쉬 구성과 다르다, (2) 같은 프레임에 자·전원어댑터·프롭이 함께 놓여 있다,
  (3) 파란 천 배경에 기체 그림자가 짙게 깔린다. 게다가 이 필링의 기체에는 스트라이프가 없어
  **어느 변종인지 사진만으로 못 정한다**(`p3_specs.json` 은 이 FCC ID 를 Professional 로 적어 두었다 —
  이 폴더는 그 주장을 **확인해 주지 못한다**).
* **Wikimedia Commons** — `Category:DJI Phantom 3 Professional` 15장, `...Advanced` 14장,
  `...4K` 5장, `...Standard` 9장을 전수 확인했다. 스튜디오 컷이 **한 장도 없다**:
  대부분 **드론이 찍은 항공사진**(기체가 안 보인다)이거나 **비행 중 사진**(프롭 모션블러).
  예: `A Quadcopter 03~05.jpg`(Zimin.V.G., CC BY-SA 4.0) = 하늘 배경 비행 컷,
  `DJI Phantom 3 4K.jpg`·`DJI Phantom 3 Standard.jpg` = 나무·들판 배경 비행 컷,
  `DJI Phantom 3 Advanced in its box (6439).jpg` = 골판지 폼 속 톱뷰(배경 분리 불가).
* **`WMCH Drone - Face.jpg`** (Commons, CC BY-SA 3.0) — 깨끗한 스튜디오 정면 컷이지만
  **Phantom 3 이 아니다**: 짐벌·카메라가 없고 동체에 `www.dji-innovations.com` 이 인쇄된
  **Phantom 2 세대** 기체다.
* **DJI Phantom 3 SE `s4-img` / Standard `aircraft/s2-img`** 등 — 열어 보니 **조종기·앱 화면**이다.

## 이 폴더가 근거로 쓰이는 곳

* `src/viz_mesh_photo.py` — 사진 실루엣 vs 메쉬 실루엣 IoU (`outputs/mesh_compare_photo.json`).
* `src/drone_cad.py` 의 `_ARM_SECTION["phantom3"]`·`_ARM_WIDTH["phantom3"]` 는 2026-08-03 현재
  **phantom4 값을 상속**하고 있고 소스에 "⚠ 상속 — P3 사진 없음" 이라고 적혀 있다.
  이 폴더가 생겼으니 그 상속은 이제 **검증 가능한 가정**이다(아직 검증하지는 않았다).

---

# 2차 수집 (2026-08-03) — 6장 → 58장

1차(위)는 **DJI 공식 렌더 6장뿐**이었고 **내부가 한 장도 안 보였다.** 그래서 `drone_cad.py` 의
phantom3 내부 부품 상수(배터리·PCB·카메라 모듈 등 18개)가 전부 phantom4 에서 빌린 값이었다.
2차 수집은 **분해 사진**을 최우선으로 잡았고, 52장을 더해 **58장**이 됐다. 1차 6장은 그대로 뒀다.

## 무엇이 풀렸나

* **내부가 보인다.** FCC 인증 서류의 **Internal Photos** 전시물 — 규제기관 제출용이라
  **모든 부품이 자·줄자 위에 놓인 채** 촬영돼 있다. 배터리·메인 PCB·중앙 X보드·GPS 모듈·
  모터·카메라 모듈의 **치수를 직접 잴 수 있다.**
* **정투영 4면도가 생겼다.** 공식 매뉴얼 p.8 의 Aircraft Diagram 은 **원근이 없는 선도**라
  실루엣 대조에 렌더보다 낫다(`m02`).
* **저면(bottom)이 생겼다.** 1차에는 없던 각도다(`p02`·`p03`·`p04`·`d11`).

## ⚠ 1차에서 FCC 를 뺐던 것과 모순 아닌가

모순이 아니다. 1차에서 뺀 것은 FCC ID `SS3-WM3231503` 의 **External Photos**(외부 사진)였고,
이유는 "**실루엣 대조에 부적합**"이었다(짐벌·프롭 없는 기체, 프레임에 자가 같이 놓임, 짙은 그림자).
그 판단은 지금도 유효하다 — 그 전시물은 여전히 안 받았다.

이번에 받은 것은 **다른 전시물(Internal Photos)** 이고 **용도가 다르다**: 실루엣이 아니라
**내부 부품 치수**를 재려는 것이다. 부품 옆에 자가 같이 놓인 것은 1차에서는 단점이었지만
여기서는 **바로 그것이 목적**이다.

## 변종 — 어느 FCC ID 가 무엇인가

| FCC ID | 변종 | 이 폴더에서 쓴 접두 | 우리 `p3_specs.json` 변종과 같은가 |
|---|---|---|---|
| `SS3-WM3231507` | Phantom 3 **Professional** | `t01`–`t16`, `t27`, `t28` (`fccpro`) | ⭐ **같다** — 내부 보드까지 우리 변종 그대로 |
| `SS3-W3281705` | Phantom 3 **SE** | `t17`–`t22` (`fccse`) | 셸 공유. **금속 mm 자**라 치수 정밀도가 더 높다 |
| `SS3-WM3221503` | Phantom 3 **Advanced** | `t23`–`t26` (`fccadv`) | 셸 공유. Pro 값 교차확인용 |
| (FCC 아님) | Phantom 3 **Standard** | `c01`–`c03` (`pemnet`) | 셸 공유. 형상 참고만 |

⚠ **셸·암·다리·프롭은 4변종 공통**이므로 형상용으로는 전부 쓸 수 있다(1차 §변종 참조).
그러나 **내부 보드는 변종마다 다를 수 있다** — 그래서 Pro(`fccpro`) 를 기준으로 삼고
SE·Adv 는 교차확인으로만 쓴다. 배터리는 세 변종 모두 `4480 mAh 15.2 V` 로 같게 찍혔다.

## ⚠ 라이선스

* **FCC 전시물** (`t01`–`t28`) — 미국 FCC 에 제출된 **공개 규제 서류**다. 누구나 열람·다운로드할 수
  있고 fccid.io 가 미러한다. 저작권 표시는 없지만 **DJI 가 작성한 문서**다. 내부 참조용으로 받았다.
* **iFixit** (`t29`–`t33`, `p01`–`p08`) — iFixit 수리 가이드 이미지. iFixit 가이드 콘텐츠는
  **CC BY-NC-SA 3.0** 이 기본이다. 내부 랩 사용은 문제없고, **외부 배포 시 저자·라이선스 표기 필요**.
* **DJI CDN 렌더** (`d08`–`d14`) · **DJI 매뉴얼** (`m01`–`m04`) — 저작권 DJI, 공개 라이선스 없음.
  1차와 같은 취급(내부 발표용, 출처 표기, 파일 재배포 금지).
* **pemnet 분해 문서** (`c01`–`c03`) — Josh Parmet, 2016, PennEngineering 배포 PDF.

## 파일 (52장 추가분)

접두: `d`=공식 렌더 · `p`=제품 사진 · `t`=분해 · `m`=도면 · `c`=부품 단품

| 파일 | 시선/촬영각 | ⭐ 무엇을 잴 수 있나 | 출처 | 해상도 | sha256(앞16) |
|---|---|---|---|---|---|
| `phantom3_c01_pemnet_motor_stator.jpg` | 모터 로터 근접 | 스테이터 슬롯 수·권선 | pemnet P3 Standard teardown · p33 | 496×490 | `40175f77d7c5ea16` |
| `phantom3_c02_pemnet_gimbal_damper_plate.jpg` | 짐벌 댐퍼 플레이트 | 짐벌 방진판 형상 | pemnet P3 Standard teardown · p26 | 662×617 | `89dac6b6eaff18c0` |
| `phantom3_c03_pemnet_arm_motor_wiring.jpg` | 암 내부 배선 | 암 내부 케이블 경로 | pemnet P3 Standard teardown · p45 | 485×581 | `1dc3ba449852735b` |
| `phantom3_d08_official_rear_low_green_led.jpg` | 후방 저각 (녹색 상태 LED) | 후미 LED 위치. **측면도 아님** — 이름 정정함 | DJI CDN official render | 950×431 | `289c4c56be7f234f` |
| `phantom3_d11_official_underside_vision_sensors.jpg` | 저면 근접 | 비전 포지셔닝 센서 2 + 초음파 2 의 **저면 배치** | DJI CDN official render | 1776×1052 | `226834a5155e5f09` |
| `phantom3_d12_official_gimbal_camera_closeup.jpg` | 짐벌·카메라 근접 렌더 | 카메라 모듈 외형 비율 | DJI CDN official render | 483×413 | `af0a30f2106fee33` |
| `phantom3_d13_official_battery_render.jpg` | 배터리 단품 렌더 | 배터리 외형 프로파일(치수 없음 — 치수는 t15/t19/t26) | DJI CDN official render | 720×534 | `f96b849d913d67c8` |
| `phantom3_d14_official_front34_black.png` | 정면 3/4, 검은 배경 | 알파/검은 배경이라 실루엣 분리 쉬움 | DJI CDN official render | 330×208 | `05a70f83822db4c6` |
| `phantom3_m01_manual_pro_v18_aircraft_diagram_page.png` | 공식 매뉴얼 p.8 전체 | Aircraft Diagram 페이지 + 부품 번호표 | manual render / pre-existing | 1630×2422 | `8a7f8d0ec8b5e0b3` |
| `phantom3_m02_manual_pro_v18_ortho_4views.png` | ⭐⭐ **정투영 4면도** 크롭 | front·rear·좌측·우측 **원근 없는 선도** — 실루엣 대조에 최적 | manual render / pre-existing | 710×1380 | `cfd73ec63f4afcb6` |
| `phantom3_m03_manual_pro_v18_specifications.png` | 공식 매뉴얼 p.54 | Specifications — 대각 350 mm 등 공식 수치 | manual render / pre-existing | 1630×2422 | `a76dd9e544ee1051` |
| `phantom3_m04_manual_se_aircraft_diagram_page.png` | SE 매뉴얼 p.8 | SE 판 4면도 — m02 와 교차확인(셸 공유 검증) | manual render / pre-existing | 1630×2422 | `86456a184d1ce5e5` |
| `phantom3_p01_ifixit_front34_studio.jpg` | 정면 3/4, 흰 배경 | 고해상 스튜디오 3/4 — 실루엣 대조 후보 | iFixit guide 72122 · step 01 | 3736×2802 | `ef730e7ddfb0a60b` |
| `phantom3_p02_ifixit_bottom_view.jpg` | ⭐ **저면(bottom)**, 흰 배경 | **우리 세트에 없던 저면** — 다리 스탠스·배터리실·비전센서 배치 | iFixit guide 72122 · step 03 | 3424×2568 | `d7f2395f42d4abb9` |
| `phantom3_p03_ifixit_bottom_screws_annot.jpg` | 저면, 나사 주석 | 저면 + 암 끝 나사 위치(암 4개 대칭 확인) | iFixit guide 72122 · step 04 | 3272×2454 | `82944e01463717f5` |
| `phantom3_p04_ifixit_bottom_gimbal.jpg` | 저면, 짐벌 포함 | 저면 + 짐벌 돌출량 | iFixit guide 72010 · step 03 | 3564×2673 | `7e9d5247923ab50c` |
| `phantom3_p06_ifixit_front_low_gimbal.jpg` | 정면 하방, 짐벌 포함 | 정면에서 본 짐벌·다리 관계 | iFixit guide 71928 · step 09 | 4604×3453 | `4a13174dd9eba129` |
| `phantom3_p07_ifixit_rear34_battery_out.jpg` | 후방 3/4, 배터리 분리 | 후미 + 배터리 슬롯 개방 | iFixit guide 72122 · step 02 | 4088×3066 | `e8c921feea900e07` |
| `phantom3_p08_ifixit_landing_gear_detail.jpg` | 착륙다리 근접 | 다리 프로파일·두께 | iFixit guide 72010 · step 05 | 3792×2844 | `67fc52c094f82f93` |
| `phantom3_t01_fccpro_shell_gimbal_battery.jpg` | 탑다운, 청색 천 + 줄자 | 상부셸 외곽 + 짐벌 + 배터리를 **한 프레임에 줄자와 함께**. 배터리↔동체 상대 크기 | FCC Pro WM3231507 · p01 | 640×480 | `63c7e8f0f01c2f9e` |
| `phantom3_t02_fccpro_airframe_arms_centerboard.jpg` | 탑다운(하부에서), 줄자 | 암 4개 + 중앙 X보드 + 모터 배선. **암 길이·모터 간 대각** 스케일 | FCC Pro WM3231507 · p02 | 640×480 | `c040ef0327bf8b85` |
| `phantom3_t03_fccpro_lower_shell_landing_gear.jpg` | 탑다운, 줄자 | 하부셸 + 착륙다리 뿌리. 다리 간격·셸 두께 | FCC Pro WM3231507 · p02 | 640×480 | `322302ed2976f632` |
| `phantom3_t04_fccpro_upper_shell_inner_frame.jpg` | 탑다운, 줄자 | 상부셸 + 내부 프레임 조립체. 셸 내벽↔보드 간격 | FCC Pro WM3231507 · p03 | 640×480 | `640644c2f26d7ec3` |
| `phantom3_t05_fccpro_center_x_board_top.jpg` | 정면 평면, 줄자 | ⭐ 중앙 X자 전원/ESC 보드 **윗면** — X 대각 span | FCC Pro WM3231507 · p04 | 640×480 | `b5f1d4bd6b8cb8d0` |
| `phantom3_t06_fccpro_center_x_board_bottom.jpg` | 정면 평면, 줄자 | ⭐ 같은 보드 **아랫면** — 두께·커넥터 배치 | FCC Pro WM3231507 · p04 | 640×480 | `a701265af1fae918` |
| `phantom3_t07_fccpro_gps_m2_module.jpg` | 정면 평면, 줄자 | GPS-M2 모듈 원형 보드 **지름** | FCC Pro WM3231507 · p05 | 640×480 | `433f220a62ad316d` |
| `phantom3_t08_fccpro_gps_patch_antenna.jpg` | 정면 평면, 줄자 | GPS 패치 안테나 **한 변** (세라믹 패치 정사각) | FCC Pro WM3231507 · p06 | 640×480 | `ffca55b9ee3a3f6b` |
| `phantom3_t09_fccpro_gimbal_camera_mount.jpg` | 사선, 줄자 | 짐벌+카메라 조립체 + 마운트. **카메라 모듈 외형 3축** | FCC Pro WM3231507 · p07 | 640×480 | `a72a365e775246b9` |
| `phantom3_t10_fccpro_main_pcb_top.jpg` | 정면 평면, 줄자 | ⭐⭐ 메인 PCB **윗면** — 가로·세로 | FCC Pro WM3231507 · p09 | 640×480 | `64153a3bdc771152` |
| `phantom3_t11_fccpro_main_pcb_bottom.jpg` | 정면 평면, 줄자 | ⭐⭐ 메인 PCB **아랫면** — 같은 판의 반대면 | FCC Pro WM3231507 · p09 | 640×480 | `40fbede0ac060ec0` |
| `phantom3_t12_fccpro_image_sensor_board.jpg` | 정면 평면, 줄자 | 이미지 센서 보드(FF1520) + 센서 다이 크기 | FCC Pro WM3231507 · p11 | 640×480 | `18e60b6d9f90b50e` |
| `phantom3_t13_fccpro_flight_controller_board.jpg` | 정면 평면, 줄자 | 비행 컨트롤러 보드 가로·세로 | FCC Pro WM3231507 · p12 | 640×480 | `08d89f80338fd89c` |
| `phantom3_t14_fccpro_arm_led_board_ruler.jpg` | 측면, 줄자 | 암 LED 보드 **길이** (줄자 198–201 cm 구간에 걸침) | FCC Adv WM3221503 · p06 | 640×480 | `a3c85dea45a57c74` |
| `phantom3_t15_fccpro_battery_side.jpg` | 측면, 줄자 | ⭐⭐ 인텔리전트 플라이트 배터리 **길이·높이** | FCC Pro WM3231507 · p17 | 640×480 | `9a7cb2478923d5e8` |
| `phantom3_t16_fccpro_battery_label_4480mah.jpg` | 정면, 줄자 | ⭐⭐ 같은 배터리 라벨면 — `4480 mAh 15.2 V` 확인 + 폭 | FCC Pro WM3231507 · p17 | 640×480 | `25eb14d4fe1e0a42` |
| `phantom3_t17_fccse_exploded_aircraft_mm.jpg` | 탑다운, **금속 mm 자** | ⭐ 기체 분해 전개 — 셸·프레임·짐벌·배터리 한 장에 | FCC SE W3281705 · p01 | 1048×697 | `c17daf37fa47c5c0` |
| `phantom3_t18_fccse_brushless_motor_mm.jpg` | 사선, **금속 mm 자** | ⭐⭐ 브러시리스 모터 **외경·높이** (스테이터 슬롯도 보임) | FCC SE W3281705 · p03 | 503×335 | `161f091feb3f3288` |
| `phantom3_t19_fccse_battery_mm.jpg` | 측면, **금속 mm 자** | ⭐⭐ 배터리 — mm 눈금이라 줄자보다 정밀 | FCC SE W3281705 · p18 | 503×335 | `6dc74b85e60c179c` |
| `phantom3_t20_fccse_vision_ultrasonic_board_mm.jpg` | 정면 평면, **금속 mm 자** | 비전 포지셔닝 + 초음파 보드(TCB-M), 트랜스듀서 2개 간격 | FCC SE W3281705 · p08 | 1048×697 | `74306e08469a24b4` |
| `phantom3_t21_fccse_center_x_board_top_mm.jpg` | 정면 평면, **금속 mm 자** | 중앙 X보드 윗면 (SE 판) — Pro 판과 교차확인용 | FCC SE W3281705 · p01 | 1048×697 | `4fc015e14e8773e3` |
| `phantom3_t22_fccse_gps_patch_antenna.jpg` | 정면 평면 (자 없음) | GPS 패치 안테나 색·형상만. **치수는 t08 로 재라** | FCC SE W3281705 · p05 | 503×335 | `434a79bed0148dd9` |
| `phantom3_t23_fccadv_airframe_top_ruler.jpg` | 탑다운, 줄자 | ⭐ 조립된 흰 기체를 줄자 위에 — **외형 대각** 직접 측정 | FCC Adv WM3221503 · p03 | 640×480 | `cd8b5b2326540bef` |
| `phantom3_t24_fccadv_shell_open_centerboard.jpg` | 탑다운, 줄자 | 하부셸 + 중앙보드 + 상부셸 분리 배치 | FCC Adv WM3221503 · p01 | 640×480 | `95a5a5b7c49ef100` |
| `phantom3_t25_fccadv_arm_led_board_ruler.jpg` | 측면, 줄자 | 암 LED 보드 (Adv 판) — t14 교차확인 | FCC Adv WM3221503 · p05 | 640×480 | `01758339c6492eb1` |
| `phantom3_t26_fccadv_battery_ruler.jpg` | 측면, 줄자 | 배터리 (Adv 판) — t15/t19 교차확인 | FCC Adv WM3221503 · p12 | 640×480 | `a22e323a502d28cc` |
| `phantom3_t27_fccpro_camera_module_housing.jpg` | 탑다운, 줄자 | 카메라 하우징 + 내부 보드 분리 | FCC Pro WM3231507 · p08 | 640×480 | `87427c940080b40a` |
| `phantom3_t28_fccpro_gimbal_roll_yaw_assy.jpg` | 사선, 줄자 | 짐벌 롤/요 암 조립체 — 짐벌 팔 길이 | FCC Pro WM3231507 · p10 | 640×480 | `710d93c459bfd02c` |
| `phantom3_t29_ifixit_internal_top_shell_off.jpg` | 탑다운 (스튜디오) | ⭐⭐ 셸 벗긴 내부 — X보드·암·모터선 배치가 **고해상도(3544 px)** | iFixit guide 72122 · step 08 | 3544×2658 | `c4e09e864163a37d` |
| `phantom3_t30_ifixit_arm_interior_motor_wiring.jpg` | 사선 근접 | 암 내부 단면 + 모터 배선 — **암 속 빈 공간** | iFixit guide 71928 · step 11 | 4604×3453 | `52f3824a01e03288` |
| `phantom3_t31_ifixit_mainboard_in_situ_annot.jpg` | 탑다운, 주석 있음 | 메인보드 장착 상태 + 커넥터 위치 주석 | iFixit guide 72122 · step 09 | 2396×1797 | `65bbca5222add155` |
| `phantom3_t32_ifixit_landing_gear_led_board.jpg` | 사선 근접 | 착륙다리 + 다리 속 LED 보드 — 다리 단면 | iFixit guide 72010 · step 06 | 4604×3453 | `7198d917b8f7f791` |
| `phantom3_t33_ifixit_battery_bay_open.jpg` | 사선 | 배터리 베이 개방 — 배터리실 내벽 | iFixit guide 72122 · step 08 | 3720×2790 | `229f4cd2d8c97f1f` |
## 어떻게 찾았나 (재현 절차, 2차)

1. **FCC** — `fccid.io` 에서 DJI Grantee Code `SS3` 의 Phantom 3 필링을 찾고, 각 ID 의
   **Internal Photos** 전시물 PDF 를 직접 받았다(`https://fccid.io/<ID>/<Exhibit>/<Doc>.pdf`).
   PyMuPDF 로 **삽입 이미지를 원본 해상도 그대로** 추출했다(페이지 렌더가 아니다 — 재압축 없음).
   Pro 33장 · SE 35장 · Adv 24장이 나왔고 그중 28장을 골랐다.
2. **iFixit** — 공개 API `https://www.ifixit.com/api/2.0/guides/<id>` 로 가이드 5편
   (71927 Cover · 71928 Motor · 72010 Landing Gear · 72117 LED · 72122 Flight Controller)의
   JSON 을 받아 스텝 이미지 URL 106개를 뽑고 `.full` 해상도로 받았다(3400–4600 px).
3. **매뉴얼** — `dl.djicdn.com` 의 Pro v1.8 · SE v1.0 PDF. `Aircraft Diagram` 은 네 매뉴얼 모두
   **p.8** 이었다. 300 dpi 로 렌더하고 4면도만 크롭했다.
4. **DJI CDN** — 1차와 같은 Wayback CDX 훑기. 197개 후보를 받아 크기 필터 후 180개,
   그중 **1차 6장과 sha256 중복이 아닌** 것만 골라 5장을 더했다.

**중복 제거** — 최종 복사 시 기존 6장을 포함한 전체와 sha256 을 대조했다. 6장이 중복으로 걸렸다
(예: DJI 가 SE 톱뷰 자산을 Pro 페이지에서 재사용해 `d03` 과 바이트 동일). 중복은 복사하지 않았다.

## 🔴 이번에도 확인만 하고 안 받은 것

* **YouTube 분해 영상** 2편(`Jslh6GJCZ4k`·`3pkNNT3vaoo`) — 프레임 캡처는 화질·라이선스 모두
  FCC 사진보다 나쁘다. FCC 로 충분해서 받지 않았다.
* **djioemparts 부품 사진** — 셸·프롭 단품 컷이 있으나 **자가 같이 놓이지 않아** 치수를 못 잰다.
  FCC 사진이 상위 호환이라 생략했다.
* **`phantompilots.com` 나사 목록 스레드** — 나사 규격표는 있으나 우리 형상 상수와 무관.

## ⚠ 아직 안 한 것 (정직하게)

* **실제로 치수를 재지는 않았다.** 이 라운드는 **사진 확보**까지다. `drone_cad.py` 의 phantom3
  내부 상수 18개는 **아직 phantom4 상속 그대로**다. 사진이 생겨서 이제 **잴 수 있게** 됐을 뿐이다.
* **`viz_mesh_photo.py` 의 `PHOTOS["phantom3"]` 에 신규 52장을 등록하지 않았다.** 1차 4장만
  등록된 상태다. 실루엣용 후보는 `m02`(정투영 4면도) · `p02`(저면) · `d14`(검은 배경 3/4) 가
  유력하고, 등록 전에 1차와 같은 `expect` 각도 선언·`fit_pose` 확인을 거쳐야 한다.
* **줄자 눈금의 실제 판독**을 하지 않았다. FCC Pro 는 **인치/cm 혼합 줄자**라 어느 눈금을 읽는지
  주의해야 한다(SE 의 금속 mm 자가 더 안전하다).

---
# 3차 수집 (2026-08-03, 같은 날 오후)
2차까지 58장이었다. 3차에서 **87장을 더해 145장**이 됐다. 2차가 "확인만 하고 안 받은 것"으로
남겨 둔 두 갈래를 실제로 받은 것이 이번 수확의 대부분이다.

1. **FCC External Photos 를 되살렸다.** 1차는 이 전시물을 "실루엣용으로 부적합"이라며 통째로
   버렸다(§🔴 받았다가 뺀 후보들). 그 판단은 **실루엣 한정으로는 옳지만 치수용으로는 틀렸다** —
   같은 프레임의 자·줄자가 1차에서는 단점이었으나 여기서는 목적이다. 4개 FCC ID 의 External
   전시물에서 **기체 전체를 자와 함께 찍은 20장**(`p09`–`p28`)을 받았다. 정면·측면·저면·톱·사선이
   모두 있고, SE 필링(`p09`–`p14`)은 **강철자**라 줄자보다 정밀하다.
2. **iFixit 가이드를 5편 → 17편으로 넓혔다.** 2차는 Advanced/Pro 5편만 봤다. 검색 API 로
   Phantom 3 가이드를 전수(17편) 훑어 **Standard 6편 · Pro 짐벌암 1편**을 새로 찾았고,
   스텝 이미지 245장에서 34장을 골랐다. 셸은 4변종 공통이라 Standard 가이드도 형상용으로 쓴다.

2차의 FCC Internal 도 **28장만 골랐던 것을 다시 훑어 33장을 더** 가져왔다(자 포함 부품 위주).

⚠ **중복 제거** — 기존 58장 전체와 sha256 + 16×16 지각해시(해밍 ≤12)로 대조했다. 후보 336장 중
55장이 중복이라 버렸고, 남은 281장에서 87장을 골랐다.

## 이번에 새로 쓴 출처

| 출처 | 무엇 | 라이선스 |
|---|---|---|
| FCC **External Photos** 4개 ID | 기체 전체 + 자, 다각도 | 미국 FCC 공개 규제 서류 (작성자 DJI) |
| iFixit Standard 가이드 6편 (201290·201866·201940·201944·201946 등) | Standard 기체 분해 | CC BY-NC-SA 3.0 — 외부 배포 시 표기 필요 |
| iFixit Pro 가이드 112297 (Camera Gimbal Arm) | 짐벌 암·댐퍼·카메라 보드 | 동일 |
| DJI **Advanced** User Manual (FCC User-Manual 전시물) | Aircraft Diagram 4면도 | 저작권 DJI |
| DJI **SE Quick Start Guide** (FCC 전시물) | 6520 px 폴드아웃 선도 | 저작권 DJI |

## 파일 (87장 추가분)

접두: `d`=공식 렌더 · `p`=제품/규제 전신 사진 · `t`=분해 · `m`=도면 · `c`=부품 단품

| 파일 | ⭐ 무엇을 잴 수 있나 | 출처 | 해상도 | sha256(앞16) |
|---|---|---|---|---|
| `phantom3_p09_fccse_all_items_props_steelruler.jpg` | 기체+프롭4+어댑터 한 프레임, 강철자. 프롭 9450 실물 길이 | FCC SE W3281705 · External Photos · p01 | 1048×697 | `954b58989d2401f7` |
| `phantom3_p10_fccse_front34_high_steelruler.jpg` | ⭐ 고각 3/4 앞 + 직교 강철자 2개. 톱뷰가 아니다 — 모터축 배치는 보이나 대각은 투영보정 필요 | FCC SE W3281705 · External Photos · p01 | 1048×697 | `c45a8359e854e512` |
| `phantom3_p11_fccse_front_steelruler.jpg` | ⭐ 정면 + 강철자. 다리 스탠스 폭·전고 | FCC SE W3281705 · External Photos · p02 | 1048×697 | `d93bbd3acb00e2de` |
| `phantom3_p12_fccse_bottom_gimbal_steelruler.jpg` | ⭐ 저면(짐벌 장착) + 강철자. 짐벌 돌출·다리 발 간격 | FCC SE W3281705 · External Photos · p02 | 1048×697 | `d20e134324b04e87` |
| `phantom3_p13_fccse_side_steelruler.jpg` | ⭐ 측면 + 강철자. 전고·다리 높이 | FCC SE W3281705 · External Photos · p03 | 1048×697 | `048bfe4da437b9e7` |
| `phantom3_p14_fccse_side_gimbal_steelruler.jpg` | 측면(짐벌쪽) + 강철자 | FCC SE W3281705 · External Photos · p03 | 1048×697 | `379f07d70496dee0` |
| `phantom3_p15_fccadv_top_tape.jpg` | 톱뷰 + 줄자. 대각 교차확인 | FCC Adv WM3221503 · External Photos · p01 | 640×480 | `c13d5eaf9df7fafd` |
| `phantom3_p16_fccadv_inner_frame_gimbal_tape.jpg` | 저면, 하부셸 제거 → 내부 프레임 + 짐벌 + 줄자 | FCC Adv WM3221503 · External Photos · p02 | 640×480 | `b559c04f9109d11e` |
| `phantom3_p17_fccadv_front_tape.jpg` | 정면 + 줄자 | FCC Adv WM3221503 · External Photos · p02 | 640×480 | `408a4b6861dc4ecf` |
| `phantom3_p18_fccadv_side_gimbal_tape.jpg` | 측면(짐벌 장착) + 줄자 | FCC Adv WM3221503 · External Photos · p03 | 640×480 | `df46e6e0c5ae5ffd` |
| `phantom3_p19_fccadv_side_gimbal_tape2.jpg` | 측면 다른 각 + 줄자 | FCC Adv WM3221503 · External Photos · p03 | 640×480 | `978d753daa5b5048` |
| `phantom3_p20_fccadv_front_low_tape.jpg` | 정면 저각 + 줄자 | FCC Adv WM3221503 · External Photos · p04 | 640×480 | `3ea4939050f6eaee` |
| `phantom3_p21_fccpro03_top_tape.jpg` | 톱뷰 + 줄자 (WM3231503) | FCC Pro WM3231503 · External Photos · p01 | 640×480 | `f5048530d8e1b0a2` |
| `phantom3_p22_fccpro03_bottom_iso_tape.jpg` | 저면 사선 + 줄자 | FCC Pro WM3231503 · External Photos · p02 | 640×480 | `3cb5c205ebe90777` |
| `phantom3_p23_fccpro03_iso_tape.jpg` | 사선 전경 + 줄자 | FCC Pro WM3231503 · External Photos · p03 | 640×480 | `356615f726ae0649` |
| `phantom3_p24_fccpro07_top_tape.jpg` | 톱뷰(깨끗) + 줄자 | FCC Pro WM3231507 · External Photos · p01 | 640×480 | `67a6ff3a2190b43d` |
| `phantom3_p25_fccpro07_top_props_laid_tape.jpg` | 톱뷰 + 프롭 4장 나란히 + 줄자. 프롭↔동체 상대 크기 | FCC Pro WM3231507 · External Photos · p01 | 640×480 | `6e891510eef715bb` |
| `phantom3_p26_fccpro07_iso_top_tape.jpg` | 사선 위 + 줄자 | FCC Pro WM3231507 · External Photos · p02 | 640×480 | `dceb43c35afbc0cb` |
| `phantom3_p27_fccpro07_bottom_gimbal_tape.jpg` | ⭐ 저면(짐벌) + 줄자 | FCC Pro WM3231507 · External Photos · p02 | 640×480 | `bff7699683eea16c` |
| `phantom3_p28_fccpro07_bottom_rear_iso_tape.jpg` | 저면 후방 사선 + 줄자 | FCC Pro WM3231507 · External Photos · p03 | 640×480 | `0629aa882976ae22` |
| `phantom3_p29_ifixit_std_bottom_gear_screws.jpg` | 저면 전경, 다리 나사 주석 (Standard) | iFixit `DJI Phantom 3 Standard Gimbal Replacement` step 2 | 4500×3375 | `c663362ac1bee84e` |
| `phantom3_p30_ifixit_std_bottom_annot.jpg` | 저면 전경, 셸 나사 주석 | iFixit `DJI Phantom 3 Standard Cover Replacement` step 3 | 4500×3375 | `afb1d27be6170d4f` |
| `phantom3_p31_ifixit_std_bottom_motor_screws.jpg` | 저면 전경, 모터 나사 4개 주석 | iFixit `DJI Phantom 3 Standard Propeller Motors Replacement` step 8 | 4500×3375 | `2b23df2f5a53f1ed` |
| `phantom3_p32_ifixit_std_bottom_landing_gear.jpg` | 저면 + 착륙다리 나사 위치 | iFixit `DJI Phantom 3 Standard Landing Gear Replacement` step 2 | 4500×3375 | `70fe0a0cf5683041` |
| `phantom3_p33_ifixit_std_bottom_gear_removed.jpg` | 저면, 다리 제거 상태 → 하부셸 윤곽 | iFixit `DJI Phantom 3 Standard Landing Gear Replacement` step 2 | 4500×3375 | `98eb1f27018d4bd3` |
| `phantom3_p34_ifixit_std_front_battery.jpg` | 정면, 배터리 장착. 배터리 돌출량 | iFixit `DJI Phantom 3 Standard Battery Replacement` step 1 | 4500×3375 | `5f66cced822022de` |
| `phantom3_p35_ifixit_adv_iso_arms_motors.jpg` | 사선 전경, 암·모터 노출 | iFixit `DJI Phantom 3 Advanced Cover Replacement` step 7 | 3640×2730 | `fb03bed7171de054` |
| `phantom3_p36_ifixit_adv_rear_battery_bay.jpg` | 후방, 배터리실 | iFixit `DJI Phantom 3 Advanced Cover Replacement` step 1 | 2948×2211 | `01cccc7683296bcb` |
| `phantom3_t34_fccadv_inner_frame_gear_top.jpg` | ⭐⭐ 흰 내부 프레임(X)+착륙다리 톱뷰. 프레임 대각·암 폭 | FCC Adv WM3221503 · Internal Photos · p01 | 640×480 | `34d4ee2b54bb9d20` |
| `phantom3_t35_fccadv_inner_frame_centerboard_tape.jpg` | ⭐⭐ 내부 프레임 + 중앙보드 톱뷰 + 줄자. 프레임 대각 | FCC Adv WM3221503 · Internal Photos · p06 | 640×480 | `40c1ff3298c6293e` |
| `phantom3_t36_fccpro07_inner_frame_gear_tape.jpg` | ⭐⭐ 내부 프레임+다리 + 줄자 | FCC Pro WM3231507 · Internal Photos · p01 | 640×480 | `e65e5217240c54fd` |
| `phantom3_t37_fccpro07_inner_frame_bottom_tape.jpg` | ⭐⭐ 내부 프레임 아랫면 + 줄자 | FCC Pro WM3231507 · Internal Photos · p03 | 640×480 | `8167b7d8ecabce0f` |
| `phantom3_t38_fccadv_center_x_board_wired_top.jpg` | 중앙 X보드(배선 포함) 윗면 + 줄자. X 대각 span | FCC Adv WM3221503 · Internal Photos · p02 | 640×480 | `5e566412b00473ad` |
| `phantom3_t39_fccadv_center_x_board_wired_bottom.jpg` | 중앙 X보드 아랫면 + 줄자 | FCC Adv WM3221503 · Internal Photos · p03 | 640×480 | `a2b80ab8405db99f` |
| `phantom3_t40_fccadv_center_x_board_with_camera.jpg` | 중앙 X보드 + 카메라 모듈 동봉 + 줄자 | FCC Adv WM3221503 · Internal Photos · p02 | 640×480 | `ed000d8c470e9de3` |
| `phantom3_t41_fccse_pcb_antenna_strip_mm.jpg` | ⭐ 기판 안테나 스트립 + mm 자. 안테나 길이(전기적 크기) | FCC SE W3281705 · Internal Photos · p04 | 503×335 | `cdb45afc044c94e1` |
| `phantom3_t42_fccpro07_antenna_strip_tape.jpg` | 안테나 스트립 + 줄자. t41 교차확인 | FCC Pro WM3231507 · Internal Photos · p07 | 640×480 | `08fa20b70ff7ec9d` |
| `phantom3_t43_fccadv_vision_ultrasonic_board.jpg` | ⭐ 비전+초음파 보드, 트랜스듀서 2개 간격 | FCC Adv WM3221503 · Internal Photos · p08 | 640×480 | `14e8ad5d0e92a605` |
| `phantom3_t44_fccpro07_vision_ultrasonic_tape.jpg` | ⭐ 비전+초음파 보드 + 줄자 | FCC Pro WM3231507 · Internal Photos · p16 | 640×480 | `9996f0adcd8abba1` |
| `phantom3_t45_fccse_main_pcb_bottom_mm.jpg` | 메인 PCB 아랫면 + mm 자 | FCC SE W3281705 · Internal Photos · p07 | 1048×697 | `610a0422d7beb5b1` |
| `phantom3_t46_fccadv_main_pcb_green_top_tape.jpg` | ⭐ 메인 PCB(녹색) 윗면 + 줄자 | FCC Adv WM3221503 · Internal Photos · p10 | 640×480 | `abb5ecedf3ce25e5` |
| `phantom3_t47_fccadv_main_pcb_green_bottom_tape.jpg` | ⭐ 메인 PCB(녹색) 아랫면 + 줄자 | FCC Adv WM3221503 · Internal Photos · p10 | 640×480 | `135ce44e22878034` |
| `phantom3_t48_fccadv_gimbal_camera_exploded_tape.jpg` | ⭐⭐ 짐벌+카메라 모듈 분해 + 줄자 | FCC Adv WM3221503 · Internal Photos · p09 | 640×480 | `192380161a088908` |
| `phantom3_t49_fccpro07_gimbal_camera_assy_tape.jpg` | ⭐⭐ 짐벌+카메라 조립체 + 보드 + 줄자 | FCC Pro WM3231507 · Internal Photos · p08 | 640×480 | `00ff4c77664b7f6d` |
| `phantom3_t50_fccpro07_gimbal_camera_lens_tape.jpg` | ⭐ 짐벌 조립체(렌즈 정면) + 줄자 | FCC Pro WM3231507 · Internal Photos · p11 | 640×480 | `e717a9aaa0599474` |
| `phantom3_t51_fccpro07_gimbal_boards_exploded_tape.jpg` | 짐벌 마운트+보드 분해 + 줄자 | FCC Pro WM3231503 · Internal Photos · p07 | 640×480 | `6c7a9577fa430ad3` |
| `phantom3_t52_fccse_image_sensor_board_mm.jpg` | 이미지 센서 보드 + mm 자. 센서 다이 | FCC SE W3281705 · Internal Photos · p17 | 1048×697 | `20d8fdd8e374c559` |
| `phantom3_t53_fccadv_image_sensor_board_tape.jpg` | 이미지 센서 보드 + 줄자 | FCC Adv WM3221503 · Internal Photos · p11 | 640×480 | `3859a380fe5dc6ad` |
| `phantom3_t54_fccadv_gimbal_board_hole_tape.jpg` | 짐벌 보드(중앙 개구) + 줄자 | FCC SE W3281705 · Internal Photos · p14 | 1048×697 | `93d65decae9217b0` |
| `phantom3_t55_fccadv_gimbal_board_shield_tape.jpg` | 짐벌 보드 + 곡면 실드 + 줄자 | FCC SE W3281705 · Internal Photos · p14 | 1048×697 | `89fed5653bb4f717` |
| `phantom3_t56_fccse_gps_module_round.jpg` | GPS 모듈 원형 보드. **자 없음** — 지름은 t07 로 재라 | FCC SE W3281705 · Internal Photos · p06 | 1048×697 | `6f2b1c5348250ada` |
| `phantom3_t57_fccadv_gps_patch_antenna_tape.jpg` | GPS 패치 안테나 + 줄자 | FCC Adv WM3221503 · Internal Photos · p04 | 640×480 | `161aba3fe7cbb2d4` |
| `phantom3_t58_fccse_arm_led_board.jpg` | 암 LED 보드. **자 없음** — 길이는 t14/t25/t59 로 재라 | FCC SE W3281705 · Internal Photos · p11 | 1048×697 | `805d12cc4d593db7` |
| `phantom3_t59_fccadv_arm_led_board_tape.jpg` | 암 LED 보드 + 줄자 | FCC Adv WM3221503 · Internal Photos · p05 | 640×480 | `d4b049762bf8df15` |
| `phantom3_t60_fccse_led_board_in_gear.jpg` | 착륙다리 속 LED 보드 장착 상태. **자 없음** | FCC SE W3281705 · Internal Photos · p10 | 503×335 | `3f44e11043588d79` |
| `phantom3_t61_fccse_battery_side_mm.jpg` | ⭐ 배터리 측면 + mm 자 | FCC SE W3281705 · Internal Photos · p18 | 503×335 | `229fd970a0ba4a99` |
| `phantom3_t62_fccadv_battery_label_tape.jpg` | ⭐ 배터리 라벨면(4480mAh 15.2V) + 줄자 | FCC Adv WM3221503 · Internal Photos · p12 | 640×480 | `6a781a7c26613387` |
| `phantom3_t63_fccadv_battery_contacts.jpg` | 배터리 접점면·경고라벨 | FCC Adv WM3221503 · Internal Photos · p13 | 640×480 | `df86b40a802908c4` |
| `phantom3_t64_fccse_flight_ctrl_board_mm.jpg` | 비행 컨트롤러/IMU 소형 보드 + mm 자 | FCC SE W3281705 · Internal Photos · p02 | 1048×697 | `56763894acaf8fa9` |
| `phantom3_t65_fccse_camera_board_shield_mm.jpg` | 카메라 보드(금속 실드) + mm 자 | FCC SE W3281705 · Internal Photos · p03 | 1048×697 | `7ac0329ed8ad4137` |
| `phantom3_t66_fccse_vision_ultrasonic_mm.jpg` | 비전+초음파 보드 + mm 자 | FCC SE W3281705 · Internal Photos · p08 | 1048×697 | `6ccbaafe64056191` |
| `phantom3_t67_ifixit_adv_airframe_shell_off_top.jpg` | ⭐⭐ 셸 벗긴 기체 톱다운 4236px. X보드·암·모터 배치 | iFixit `DJI Phantom 3 Advanced LED Replacement` step 0 | 4236×3177 | `6cf7b26e68ffba76` |
| `phantom3_t68_ifixit_std_internals_iso.jpg` | ⭐⭐ 셸 벗긴 기체 사선 전경 | iFixit `DJI Phantom 3 Standard Cover Replacement` step 0 | 4500×3375 | `71199d641bf88882` |
| `phantom3_t69_ifixit_std_mainboard_in_situ.jpg` | 메인보드 장착 상태 톱다운 | iFixit `DJI Phantom 3 Standard Propeller Motors Replacement` step 9 | 4500×3375 | `52fdeaa2952a0b30` |
| `phantom3_t70_ifixit_adv_mainboard_arm_wiring.jpg` | 메인보드 + 암 배선 | iFixit `DJI Phantom 3 Advanced Motor Replacement` step 10 | 4604×3453 | `66bbb2b8afd44e78` |
| `phantom3_t71_ifixit_std_arm_interior_wiring.jpg` | ⭐ 암 내부 배선(암 절개) | iFixit `DJI Phantom 3 Standard Propeller Motors Replacement` step 10 | 4500×3375 | `a10b5e45703b2c85` |
| `phantom3_t72_ifixit_adv_motor_in_arm.jpg` | ⭐ 모터가 암에 장착된 상태 + 암 내부 공동 | iFixit `DJI Phantom 3 Advanced LED Replacement` step 11 | 4604×3453 | `15712d3d7a72d49d` |
| `phantom3_t73_ifixit_adv_motor_arm_led_wiring.jpg` | 모터 + 암 LED 보드 + 배선 | iFixit `DJI Phantom 3 Advanced LED Replacement` step 11 | 4604×3453 | `61c104625198907e` |
| `phantom3_t74_ifixit_adv_arm_led_strip_seated.jpg` | 암 LED 스트립 장착 상태 | iFixit `DJI Phantom 3 Advanced Landing Gear Replacement` step 5 | 4016×3012 | `085150bd52bcba15` |
| `phantom3_t75_ifixit_adv_arm_interior_led.jpg` | 암 내부 + LED 보드 | iFixit `DJI Phantom 3 Advanced Landing Gear Replacement` step 5 | 3860×2895 | `fd57d9e49461869b` |
| `phantom3_t76_ifixit_adv_bottom_gimbal_vision.jpg` | ⭐ 저면 짐벌+비전센서 나사 주석 | iFixit `DJI Phantom 3 Advanced Landing Gear Replacement` step 3 | 3168×2376 | `1ea51ced38ff712b` |
| `phantom3_t77_ifixit_adv_bottom_gear_off.jpg` | ⭐ 저면, 다리 제거 → 짐벌·비전모듈 노출 | iFixit `DJI Phantom 3 Advanced Cover Replacement` step 6 | 3352×2514 | `1c121dc52b6352d1` |
| `phantom3_t78_ifixit_std_gimbal_mount_vision.jpg` | 짐벌 마운트 + 비전 플레이트 | iFixit `DJI Phantom 3 Standard Gimbal Replacement` step 6 | 4500×3375 | `a4b98432483f10ee` |
| `phantom3_t79_ifixit_pro_camera_board_in_housing.jpg` | ⭐ 카메라 보드 하우징 내부(주석) | iFixit `DJI Phantom 3 Pro Camera Gimbal Arm and Cable Replacement` step 3 | 960×720 | `daa6b2cbdf927b55` |
| `phantom3_t80_ifixit_std_shell_open_gear.jpg` | 셸 개방 + 다리 분리 | iFixit `DJI Phantom 3 Standard Landing Gear Replacement` step 0 | 3892×2919 | `a11cc04ed8e9d519` |
| `phantom3_t81_ifixit_std_internals_under_shell.jpg` | 셸 아래 보드·배선 | iFixit `DJI Phantom 3 Standard Cover Replacement` step 6 | 4500×3375 | `a041809bbcd5ca44` |
| `phantom3_t82_ifixit_pro_gimbal_mount_on_airframe.jpg` | 짐벌 마운트가 기체에 붙은 상태 | iFixit `DJI Phantom 3 Pro Camera Gimbal Arm and Cable Replacement` step 0 | 1744×1308 | `f2561f040f22c4a4` |
| `phantom3_c04_ifixit_pro_gimbal_damper_plate.jpg` | ⭐ 짐벌 댐퍼 플레이트 단품 평면. 4점 마운트 간격 | iFixit `DJI Phantom 3 Pro Camera Gimbal Arm and Cable Replacement` step 2 | 960×720 | `b02980b5cd0861e3` |
| `phantom3_c05_ifixit_pro_gimbal_yaw_bracket.jpg` | ⭐ 짐벌 요 브래킷 단품 평면 | iFixit `DJI Phantom 3 Pro Camera Gimbal Arm and Cable Replacement` step 4 | 1192×894 | `cdb5b6acf203f63f` |
| `phantom3_c06_ifixit_std_landing_gear_pair.jpg` | ⭐ 착륙다리 한 쌍 단품. 다리 프로파일 | iFixit `DJI Phantom 3 Standard Landing Gear Replacement` step 3 | 4500×3375 | `629fa51ab48d1a8a` |
| `phantom3_m05_manual_adv_aircraft_diagram_page.png` | ⭐⭐ Advanced 매뉴얼 Aircraft Diagram (4면도+번호표). m02 교차확인 | man_SS3-WM3221503__User-Manual__Users-Manual_p008.png | 1630×2422 | `28cd3711ae49b4aa` |
| `phantom3_m06_qsg_se_foldout_p1.png` | ⭐ SE 퀵스타트 폴드아웃 1면 6520px. 기체 선도 다수 | man_SS3-W3281705__User-Manual__User-Manual-3_p001.png | 6520×2422 | `52d1949986ae9d5a` |
| `phantom3_m07_qsg_se_foldout_p2.png` | ⭐ SE 퀵스타트 폴드아웃 2면 6520px | man_SS3-W3281705__User-Manual__User-Manual-3_p002.png | 6520×2422 | `ec8c5f217dd6ad9f` |
| `phantom3_m08_manual_adv_specifications.png` | Advanced Specifications (대각 350mm 등) | man_SS3-WM3221503__User-Manual__User-Manual-_p039.png | 1630×2422 | `ea38a9d4df0fc0f1` |
| `phantom3_m09_manual_se_specifications.png` | SE Specifications | man_Phantom_3_SE_User_Manual_v1.0_en_p046.png | 1630×2422 | `66ec9c9005dcede1` |
| `phantom3_m10_manual_se_flight_limits.png` | SE 매뉴얼 비행제한/No-Fly Zone 표. 형상 정보 없음 — 참고용 | man_Phantom_3_SE_User_Manual_v1.0_en_p039.png | 1630×2422 | `2a397c139d8c1f87` |
| `phantom3_m11_manual_se_aircraft_section.png` | SE 매뉴얼 Aircraft 절 도해 | man_Phantom_3_SE_User_Manual_v1.0_en_p010.png | 1630×2422 | `a6147f85cde5e03f` |

## ⚠ 3차에서 고친 내 오독 (반증 보존)

컨택트시트로 전수 확인하다가 **내가 붙인 이름이 사진과 다른 것 7건**을 잡아 고쳤다.
고치기 전 이름을 남겨 둔다 — 자동 수집은 이런 식으로 틀린다.

| 처음 붙인 이름 | 실제 | 고친 이름 |
|---|---|---|
| `p10_fccse_top_steelruler` | 톱뷰가 아니라 **고각 3/4** | `p10_fccse_front34_high_steelruler` |
| `p16_fccadv_bottom_frame_tape` | 하부셸 제거된 **내부 프레임** | `p16_fccadv_inner_frame_gimbal_tape` |
| `t35_fccadv_airframe_top_tape` | 조립 기체가 아니라 **내부 프레임+중앙보드** | `t35_fccadv_inner_frame_centerboard_tape` |
| `t56_..._gps_module_round_mm` | **자가 없다** | `t56_fccse_gps_module_round` |
| `t58_..._arm_led_board_mm` | **자가 없다** | `t58_fccse_arm_led_board` |
| `t60_..._led_board_in_gear_mm` | **자가 없다** | `t60_fccse_led_board_in_gear` |
| `m10_manual_se_gimbal_diagram` | 짐벌 도해가 아니라 **비행제한 표** | `m10_manual_se_flight_limits` |

⚠ 나머지 80장의 이름은 **썸네일 수준(260 px)에서만** 확인했다. 원본을 열어 한 장씩 검증하지는
않았으므로, 실제로 치수를 잴 때는 그 장의 이름을 믿지 말고 사진을 먼저 봐라.

## ⚠ 아직 안 한 것 (3차에서도 정직하게)

* **치수를 재지 않았다.** 3차도 사진 확보까지다. `drone_cad.py` 의 phantom3 내부 상수 18개는
  여전히 **phantom4 상속 그대로**다. 달라진 것은 이제 잴 근거가 145장 있다는 것뿐이다.
* **`viz_mesh_photo.py` 의 `PHOTOS["phantom3"]` 은 여전히 1차 4장만** 등록돼 있다.
  3차에서 실루엣 후보가 크게 늘었다 — `p11`(정면 강철자) · `p13`(측면 강철자) ·
  `p12`/`p27`(저면) · `p24`(톱, 줄자) 는 배경이 균일한 청색 천이라 **흰 기체와 대비가 크다**.
  1차 `_d01` 의 51 % 임계값 민감도 문제를 이 장들이 풀어 줄 가능성이 높다. 등록 전에
  1차와 같은 `expect` 선언 + `fit_pose` 확인을 거쳐야 한다.
* **DJI CDN 3차 훑기는 실패했다.** Wayback CDX 가 이번에는 connection refused 로 막혔다
  (1·2차에는 됐다). 공식 렌더는 11장에서 늘지 않았다.
* **줄자 눈금 판독은 여전히 안 했다.** FCC Pro/Adv 는 **인치/cm 혼합 줄자**이고 SE 는 금속 mm 자다.
  SE 장(`p09`–`p14`, `t41`, `t45`, `t52`, `t61`, `t64`–`t66`)이 판독에 가장 안전하다.


---

# 4차 — **실제로 쟀다** (2026-08-03, 같은 날 저녁)

1·2·3차는 전부 "사진 확보까지"였고 세 번 다 "치수를 재지 않았다"고 적어 두었다.
이번 라운드가 그 빚을 갚았다. `drone_cad.py` 의 phantom3 형상표는 이제 phantom4 상속이 아니라
**이 폴더의 픽셀 실측**이다.

* 측정 원장 — `outputs/p3_mesh_v2_measurements.json` (축척 앵커·등급·못 잰 것 목록)
* 렌더 — `outputs/figs/p3_mesh_v2.png` (신판 위, 구판 아래, 같은 카메라·같은 축척)
* ⭐⭐ **가장 크게 뒤집힌 것**: 공표 185 mm 는 "모터 위→발"이 아니라 **"셸 crown→발"** 이다.
  정면도(184.1)·후면도(185.4) 두 장이 독립으로 말한다. 모터 위→발은 175.0 mm 뿐이다.
  이 오독 때문에 `p3_specs.json` 의 셸 63.9 / 다리 120.5 가 나왔고, 실제는 **78.6 / 111.6** 이다.
* ⭐ **줄자 눈금 판독은 이번에도 안 했다.** 대신 더 정확한 길을 썼다 — 분해 부품은 기체 자체를
  자로 쓴다(`p33`·`t67` 에서 모터 대각 350 mm 로 축척을 잡고 그 안의 부품을 잰다).
  FCC 줄자 사진(`t15`·`t19`·`t61` 등)은 원근이 커서 이 방식보다 나쁘다.
* 못 잰 것은 위 JSON 의 `cannot_measure` 에 그대로 적어 두었다(암이 가리는 두 스테이션의
  동체 반폭·반높이, 단면 초타원 지수, 짐벌 깊이, 9450 익형 단면 등).
