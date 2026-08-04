# DJI Matrice 4E — 참조 이미지 출처

**실측 캠페인 대상 2기종 중 하나**다(다른 하나는 Mavic 4 Pro). 2026-08-03 이전에는 사진이 **5장**뿐이었고
실루엣 IoU 가 상한 대비 **63 %** 로 우리 메쉬 중 하위권이었다. 그 상태로 실측에 들어가면
**불일치의 원인이 물리인지 메쉬인지 가를 수 없다.** 이 라운드에서 **5 → 56장**으로 늘렸다.

> 이번 라운드는 **수집과 실측까지**다. 메쉬는 건드리지 않았다.

---

## ⚠ 변종 구별 — 이 폴더에서 가장 중요한 주의사항

Matrice 4 시리즈는 **M4E / M4T / M4D / M4TD** 가 있고 **기체(airframe)는 공유**하지만 **짐벌이 다르다.**
이름이 비슷해 섞이기 쉬우니 아래 판별 기준을 반드시 쓸 것.

### 짐벌 렌즈 배치 = 결정적 판별 근거

`matrice4e_m03_gimbal_4T_vs_4E_discriminator.png` 가 **DJI 정비 매뉴얼이 직접 두 기종을 나란히 그린 그림**이다.
이 한 장이 판별의 1차 근거다.

| | Matrice **4E** (우리 대상) | Matrice **4T** |
|---|---|---|
| 개구부 수 | **3개 + 레이저거리계** | **4개 + 레이저거리계** |
| 배치 | 위: 원형 렌즈 + 사각창 / 아래: 흰 LRF 창 + 큰 사각창(원형 렌즈) | 위: 원형 + 사각 / 중: 사각 + 원형 / 아래: 사각 + 작은 원형 |
| 광각 센서 | **4/3 CMOS, 기계식 셔터**, f/2.8–f/11 | 1/1.3" CMOS, 고정 f/1.7 |
| 열화상 | **없음** | **있음**(적외선) + NIR 보조광 |
| 용도 | 측량·매핑 | 공공안전·점검 |

**이 폴더의 기체 사진(d·p)은 전부 위 4E 배치를 육안 확인했다.**
확인 방법: `matrice4e_d01` · `p03` · `p11` 등의 짐벌을 확대하면
`원형렌즈 + 사각창` 위에, `흰 직사각 LRF 창 + 원형렌즈가 든 큰 사각창` 아래 — 즉 **3 렌즈 + LRF**.

### 그 밖의 구별 근거

- **색**: M4E/M4T 기체는 **밝은 회색**. 암 상면에 `Matrice 4` 각인(`t12` 에서 실물 확인).
- **배터리**: M4E/M4T 는 **TB100 (6741 mAh)** — 납작하고 넓은 슬래브, 후방 삽입, 창 2개.
  **M4D/M4TD(도크형)는 다른 팩**(길쭉하고 큰 통풍 그릴, `Pb` 표기). ⚠ 아래 "정정 기록" 참조.
- **프로펠러**: 표준 **1157F**, 저소음 **1154F**, 둘 다 10.8 인치. EU 는 저소음이 기본.

---

## ⚠ 분해(teardown) 사진은 Matrice **4T** 기체다 — 반드시 읽을 것

`t01`~`t16` 은 **Matrice 4T 분해 영상**에서 뽑았다. M4E 분해 자료는 공개된 것이 없다.

- **`t01`~`t14` (셸·메인보드·암·모터·하부구조·배선)**: 기체가 **M4E 와 동일**하므로 그대로 쓸 수 있다.
  RCS 관점에서 중요한 **내부 금속(차폐캔·메인보드·배터리)의 위치와 크기**가 여기서 나온다.
- **`t15`·`t16` (짐벌·카메라 모듈)**: **M4T 전용이다. M4E 짐벌이 아니다.**
  파일명에 `_M4T` 를 붙여 두었다. M4E 짐벌 형상은 `m02`·`m03`·`p03` 을 쓸 것.

---

## ⭐ 이번 라운드 최대 수확 — 제조사 공식 CAD

DJI 가 **Matrice 4 시리즈 STEP 파일을 공개**하고 있다(다운로드 페이지의 "3D Model v2").

- 파일: `../../meshes/reference/matrice4-M4T_v2.step` (158 MB, Creo Parametric 로 작성, 어셈블리명 `M4T_ASM`)
- 원본: <https://dl.djicdn.com/downloads/DJI_Matrice_4_Series/M4T_v2.stp>
  (`M4E_v2.stp` · `M4E.stp` 는 **403** — M4E 판은 공개되지 않는다. 기체는 공유이므로 M4T 판을 쓴다.)

### CAD 실측 — 공표 제원과 대조 (2026-08-03, gmsh/OCC 로 임포트)

임포트 결과: **솔리드 125개 · 면 19,465개**. 바운딩박스:

| 축 | CAD 실측 | DJI 공표(펼침) | 차이 |
|---|---|---|---|
| X (횡, 폭) | **387.51 mm** | **387.5 mm** | **+0.01 mm (0.003 %)** ⭐ |
| Y (수직, 높이) | 151.83 mm | 149.5 mm | +2.3 mm |
| Z (종, 길이) | 331.07 mm | 307.0 mm | +24.1 mm |

**폭이 공표값과 0.003 % 로 일치한다** — 이 CAD 가 실제 양산 형상임을 독립적으로 확인해 준다.
길이/높이가 큰 것은 공표 치수의 측정 기준(프로펠러 정지각·돌출물 포함 여부)이 달라서로 보이며,
**아직 검증하지 않았다**. 다음 라운드에서 부품별 바운딩박스로 확정할 것.
산출물: 스크래치의 `m4t_cad_measure.json` (솔리드별 bbox 25개 포함).

> ⚠ gmsh 로 **표면 메쉬 생성은 실패**했다(`Impossible to mesh periodic surface 4456`).
> 임포트와 치수 측정은 성공. 메쉬가 필요하면 솔리드별로 나눠 굽거나 다른 커널을 쓸 것.

### 공표 제원 (출처: <https://enterprise.dji.com/matrice-4-series/specs>)

- 펼침 **307.0 × 387.5 × 149.5 mm** (L×W×H) · 접힘 **260.6 × 113.7 × 138.4 mm**
- 대각 휠베이스 **438.8 mm** · 프로펠러 **1157F(표준) / 1154F(저소음)**, 10.8 인치
- 이륙중량 **1219 g**(표준 프로펠러) / 1229 g(저소음)
- M4E 와 M4T 는 **치수·중량이 동일**하다.

---

## 파일 목록

### 기존 5장 (DJI 공식 렌더로 보임) — ⚠ **이름을 바꾸지 말 것**

수집 이전부터 있던 5장. 원본 URL 은 기록이 남아 있지 않다.
흰 배경 공식 렌더로 보이며, 짐벌은 **4E 배치로 확인**했다.

> 🔴 **이 5장만은 `matrice4e_<종류><번호>_` 규약에서 제외한다.**
> `src/drone_cad.py` 가 **파일명을 그대로 인용해** 치수 실측 근거를 적어 두었기 때문이다
> (`matrice 4E_1.png` 정면컷, `_3` 측면, `_4` 후면, `_5` 상면 — 총 5곳).
> 이번 라운드에서 한 번 규약대로 개명했다가 **그 주석들이 전부 붕 뜨는 것을 확인하고 되돌렸다.**
> 개명하려면 `src/drone_cad.py` 의 주석을 같은 커밋에서 함께 고쳐야 한다.

| 파일 | 무엇이 보이나 / 무엇을 잴 수 있나 | `drone_cad.py` 인용 |
|---|---|---|
| `matrice 4E_1.png` | 정면 3/4 상방, 프로펠러 펼침 — **짐벌 4E 배치 확인용 대표 사진**, 암 각도·프롭 지름비 | L618, L759 |
| `matrice 4E_2.png` | 후방 3/4 좌 — 동체 측면 실루엣·다리 각도 | L759 |
| `matrice 4E_3.png` | 후방 3/4 우 — 좌우 대칭 검증, 다리 스파이크 높이 0.079 | L247, L255, L759 |
| `matrice 4E_4.png` | **후면 정투영에 가까움** — 배터리·전원버튼·방열구, RTK 돔 지름 44 mm | L255, L663, L759 |
| `matrice 4E_5.png` | **상면 평면** — 암 벌어짐 각·프롭 배치·휠베이스 비율, 돔 중심 | L255, L664 |

### p — 제품 사진 (흰 배경, 재판매점 스튜디오 촬영)

전부 **Matrice 4E** 다(짐벌 육안 확인). 흰 배경이라 **실루엣 분리가 쉽다 — IoU 작업의 주력.**

| 파일 | 각도 | 잴 수 있는 것 | 원본 URL |
|---|---|---|---|
| `p01_side_profile_left.jpg` | **좌측면 프로파일** ⭐ | **기존 5장에 없던 각도.** 동체 높이·다리 길이·짐벌 돌출 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_2_1.png` |
| `p02_front_elevation.jpg` | 정면 | 좌우 폭·전방 센서 위치 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_c391793e-25f1-41ce-b5e8-bce7087ac192.jpg` |
| `p03_front_elevation_gimbal.jpg` | 정면(짐벌 큼) ⭐ | **4E 짐벌 렌즈 배치 판별** | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1_1440x1440_crop_center.png` |
| `p04_front_low_angle.jpg` | 정면 하방 | 다리 벌어짐·지상고 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_2.jpg` |
| `p05_rear_elevation.jpg` | 후면 | 후방 포트·방열구 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_5.jpg` |
| `p06_rear_low_angle.jpg` | 후면 하방 | 동체 하부 곡면 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_4.jpg` |
| `p07_iso_front_left.jpg` | iso 전좌 | 3D 형상 대조 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_1_1.png` |
| `p08_iso_rear_left_low.jpg` | iso 후좌 하방 | 암 뿌리·다리 결합부 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_1_1_1440x1440_crop_center.png` |
| `p09_underside_plan.jpg` | **저면** ⭐⭐ | **기존 5장에 없던 각도.** 배터리 베이·하향 비전·짐벌 상면 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_3_1.png` |
| `p10_underside_plan_alt.jpg` | 저면(프롭 각 다름) | 저면 재확인 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_3_1_1440x1440_crop_center.png` |
| `p11_front_top_iso.jpg` | 정면 상방 iso | 상면 곡면·GNSS 돌출 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1_720x720_crop_center.png` |
| `p12_top_front_iso.jpg` | 정면 상방(고해상) | 상동, 2667² | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1.png` |

출처 페이지: heliguy <https://www.heliguy.com/products/dji-matrice-4e/> ·
dronefly <https://www.dronefly.com/products/dji-matrice-4e-universal-edition-aircraft-only>

### c — 부품 단품

| 파일 | 무엇 | 잴 수 있는 것 | 원본 URL |
|---|---|---|---|
| `c01_prop_low_noise_1154F_pair.jpg` | 저소음 프로펠러 1154F | 블레이드 폭·시위·비틀림(EU 기본) | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/low-noise_props_matrice_4_shopify_720x720_crop_center.png` |
| `c02_prop_standard_1157F_pair.jpg` | 표준 프로펠러 1157F | 상동(표준판, 더 좁음) | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/standard_propellers_matrice_4_shopify_720x720_crop_center.png` |
| `c03_intelligent_flight_battery.jpg` | **M4 시리즈 TB100 배터리** | **내부 금속 덩어리 치수** — RCS 에 직접 기여 | `https://covertdrones.com/cdn/shop/files/4T_Battery_13fc6012-7e08-4ba0-bc3e-12d7821fccf2.png` |
| `c04_xray_internal_layout_render.jpg` | DJI 공식 X-ray 렌더(후상방) | 안테나·센서의 **개략 내부 배치** | `https://www-cdn.djiits.com/dps/cf101574155c556928a8791f3ab8d147.jpg` |

### m — 도면·도해 (DJI 공식 매뉴얼의 벡터 일러스트, 400 dpi 렌더 후 크롭)

DJI 는 **치수 기입 3면도를 공표하지 않는다.** 대신 아래 도해들과 **공식 CAD**(위 참조)가 근거다.
전부 벡터라 확대해도 깨지지 않는다.

| 파일 | 출처 문서·쪽 | 무엇을 잴 수 있나 |
|---|---|---|
| `m01_iso_callouts_m4t_gimbal.png` | User Manual p.9 | 부품 21개 번호 도해 ⚠ **짐벌은 4T** 로 그려져 있음(기체는 공유) |
| `m02_gimbal_4E_lens_layout.png` | User Manual p.9 인셋 | **4E 짐벌 렌즈 배치**(판별 근거) |
| `m03_gimbal_4T_vs_4E_discriminator.png` | Maintenance Manual p.13 | ⭐ **4T vs 4E 나란히 비교 — 이 폴더 판별의 1차 근거** |
| `m04_rear_detail_callouts.png` | User Manual p.9 인셋 | GNSS 안테나·비콘·배터리 버클·E-Port·microSD 위치 |
| `m05_sensing_system_placement.png` | Maintenance Manual p.14 | ⭐ **전방위/하향 비전 센서 위치**(레이더 산란체 배치) |
| `m06_rear_omni_vision_detail.png` | Maintenance Manual p.14 | 후방 전방위 비전·GNSS 돌출부 확대 |
| `m07_top_plan_prop_rotation_AB.png` | User Manual p.20 | **상면 평면 + 프롭 A/B 회전 방향** — 마이크로도플러 부호에 필요 |
| `m08_folded_aircraft_line.png` | In the Box p.1 | **접힘 상태 선도** |
| `m09_folded_top_arm_unfold.png` | User Manual p.20 | 접힘 상면 → 전방 암 펼침 |
| `m10_side_rear_arm_unfold.png` | User Manual p.20 | 측면 → 후방 암 펼침 |
| `m11_arm_fold_unfold_sequence.png` | Maintenance Manual p.10 | 암 접힘/펼침 2단 도해 |
| `m12_iso_appearance_line.png` | Maintenance Manual p.10 | 펼침 기체 iso 선도(외형 대조) |
| `m13_battery_bay_bottom.png` | Maintenance Manual p.10 | **저면 배터리 베이** |
| `m14_battery_install_iso.png` | User Manual p.20 | 배터리 삽입 방향·위치 |
| `m15_arm_led_landing_gear.png` | Maintenance Manual p.10 | 암 LED·다리(내장 안테나) 형상 |
| `m16_aux_light_underside.png` | Maintenance Manual p.14 | 하면 보조등 |
| `m17_beacon_topside.png` | Maintenance Manual p.14 | 상면 비콘 |
| `m18_rear_ports_panel.png` | Maintenance Manual p.11 | 후면 포트 패널 |
| `m19_cellular_dongle_bay.png` | Maintenance Manual p.11 | 셀룰러 동글 함(내부 공동) |

문서 원본:
- User Manual v1.2 — <https://dl.djicdn.com/downloads/DJI_Matrice_4_Series/20250415/DJI_Matrice_4_Series_User_Manual_en.pdf>
- Maintenance Manual v1.0 — <https://dl.djicdn.com/downloads/DJI_Matrice_4_Series/20250227/DJI_Matrice_4_Series_Maintenance_Manual_en.pdf>
- In the Box — <https://dl.djicdn.com/downloads/DJI_Matrice_4_Series/20260331/DJI_Matrice_4_Series_In_the_Box.pdf>
- 다운로드 허브 — <https://enterprise.dji.com/matrice-4-series/downloads>

### t — 분해 (teardown) ⭐⭐ 우리 기체 중 최초

**출처: JANGYAO(疆尧科技) "10-Min DJI Matrice 4T Disassembly: Full Guide for Repair"**
<https://www.youtube.com/watch?v=IlNhGO2of1k> (10분 00초, 1280×720@60, 2026-08-03 취득)
프레임 추출 — 각 시점 ±0.35 s 중 **라플라시안 분산이 최대**인 프레임을 골랐다.
파일명 앞의 시각(초)은 아래 표 참조. 화면에 업로더 워터마크가 있다.

⚠ **기체는 M4T. `t15`·`t16` 만 M4T 전용 짐벌이고 나머지는 M4E 와 동일한 구조다.**

| 파일 | 시각 | 무엇이 보이나 / 무엇을 잴 수 있나 |
|---|---|---|
| `t01_top_shell_lifted.jpg` | 63 s | 상부 셸 분리 순간 — 셸 두께·내부 첫 노출 |
| `t02_internals_blower_and_board.jpg` | 84 s | **송풍기 + 차폐된 메인보드 + 배선** 전체 배치 |
| `t03_internals_top_view_no_hands.jpg` | 108 s | ⭐ **손 가림 없는 내부 상면 전경** — 내부 금속 배치 실측용 최적 |
| `t04_cooling_blower_module.jpg` | 126 s | 냉각 송풍기·히트싱크 모듈 단품 |
| `t05_mainboard_in_shield_frame.jpg` | 138 s | 메인보드(차폐 프레임 장착) 분리 직후 |
| `t06_mainboard_top_shields_on.jpg` | 144 s | ⭐ **메인보드 상면, 차폐캔 장착** — 보드 외곽 치수 |
| `t07_mainboard_shields_off_chips.jpg` | 190 s | ⭐⭐ **차폐캔 제거, 칩 노출** — 금속 면적 산정 |
| `t08_mainboard_reverse_side.jpg` | 171 s | 메인보드 이면 |
| `t09_lower_body_arms_harness.jpg` | 193 s | ⭐ **하부 동체 + 암 + 배선 하네스**(손 가림 적음) |
| `t10_lower_body_wiring_wide.jpg` | 211 s | 하부 배선 광각 |
| `t11_motor_and_arm_closeup.jpg` | 294 s | **모터 + 암** 근접 — 모터 캔 지름·암 단면 |
| `t12_arm_badge_matrice4.jpg` | 344 s | 암 상면 `Matrice 4` 각인(**변종 근거**) |
| `t13_bottom_shell_internals.jpg` | 390 s | 하부 셸 내부 차폐·구조 |
| `t14_lower_shell_bare_structure.jpg` | 450 s | ⭐ **부품 제거된 하부 셸 골격** — 동체 두께·리브 |
| `t15_gimbal_lens_cluster_M4T.jpg` | 468 s | ⚠ **M4T 짐벌** 렌즈 클러스터(4E 아님) |
| `t16_camera_lens_modules_M4T.jpg` | 555 s | ⚠ **M4T 카메라 모듈** 분해(4E 아님) |

---

## 라이선스 / 취급

- **DJI 매뉴얼 PDF·공식 CAD·공식 렌더**: DJI 저작물. 매뉴얼 첫 장에 "This document is copyrighted by DJI
  with all rights reserved" 명시. **사내 연구 참조용으로만** 쓰고 재배포·출판물 게재는 하지 말 것.
- **재판매점 제품 사진**(heliguy · dronefly · covertdrones): 상점이 게시한 DJI 제품 이미지.
  마찬가지로 **내부 형상 대조용**으로만.
- **분해 영상 프레임**: JANGYAO 채널 저작물, 워터마크 포함. **내부 참조용**으로만.
- 리포트·발표 자료에 넣을 때는 **우리가 만든 렌더/도면으로 대체**하고, 이 폴더는 근거로만 인용할 것.

---

## 🔴 정정 기록 — 배터리 사진을 한 번 잘못 골랐다 (2026-08-03, 같은 세션)

처음에 `c03` 으로 dronenerds 의 `DJI_Matrice_4D_Series_Flight_Battery_...webp` 를 넣었다.
**틀렸다.** 확인해 보니 **M4D/M4TD(도크형)는 M4E/M4T 와 배터리 팩이 다르다**:

- M4E/M4T = **TB100, 6741 mAh** — 납작하고 넓은 슬래브, 창 2개, 측면 버클
- M4D/M4TD = 도크 전용의 다른 팩 — 길쭉하고 큰 통풍 그릴, `Pb` 표기

두 이미지를 나란히 비교하면 **형상이 명백히 다르다**. 매뉴얼의 배터리 삽입 도해(`m14`)와
대조한 결과 **납작한 슬래브 쪽이 M4 시리즈**임이 확인되어 covertdrones 의
`4T_Battery_...png` 로 교체했다.

**교훈: 재판매점 파일명의 모델 표기를 그대로 믿지 말 것.** 형상을 매뉴얼 도해와 대조해야 한다.
(`Matrice 4D` 와 `Matrice 4` 는 한 글자 차이다.)

---

## 🔴 정정 기록 2 — 기존 5장을 개명했다가 되돌렸다 (2026-08-03, 같은 세션)

규약대로 `matrice4e_d01_…` ~ `d05_…` 로 개명했으나, `src/drone_cad.py` 가
**옛 파일명을 그대로 인용해** 치수 근거를 적어 둔 곳이 5군데 있었다(위 표의 줄번호).
이번 라운드는 `src/drone_cad.py` 를 건드릴 수 없으므로(다른 워크플로가 phantom3 작업 중)
**개명을 전부 되돌렸다.** 규약 통일은 두 파일을 함께 고칠 수 있는 라운드로 미룬다.

**교훈: 사진 파일명은 코드 주석의 참조 대상이다.** 개명 전에 `grep` 부터 할 것.

## ⚠ 이 폴더와 무관하지만 발견한 기존 결함

`src/viz_report2_photo_compare.py:38` 의 `_photo()` 는
`sorted(glob(assets/photos/<key>/*))[0]` 을 그대로 `Image.open()` 에 넘긴다.
확장자를 거르지 않아 **`SOURCES.md` 가 항상 첫 번째로 뽑힌다** —
`x500v2` · `mavic4pro` · `phantom3` 도 **이미 같은 상태**다(이번 수집 이전부터).
이 폴더가 원인이 아니고 이번 라운드 범위 밖이라 **고치지 않았다**. 별도로 처리할 것.
(고칠 때는 이미지 확장자 필터 + 대표 사진 명시 지정이 맞다.)

## 아직 못 구한 것 / 다음 라운드 과제

1. **치수 기입 3면도** — DJI 는 공표하지 않는다. 공식 CAD 가 대체재이며 이미 확보했다.
2. **M4E 전용 분해 자료** — 공개된 것이 없다. 짐벌 내부만 미상이고 기체는 M4T 로 충분하다.
3. **CAD 길이/높이 불일치**(Z +24.1 mm, Y +2.3 mm) 미해명 — 부품별 bbox 로 확정할 것.
4. **CAD → 메쉬 변환 실패**(periodic surface) — 솔리드 단위 분할 등 재시도 필요.
5. **접힘 상태 실사진** — 지금은 선도(`m08`)뿐. 실사진이 있으면 접힘 치수 검증에 좋다.
