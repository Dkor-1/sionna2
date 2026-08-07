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

> 🔴 **2026-08-07 이 표를 전부 다시 쟀다.** 아래 «각도» 는 이제 **파일 이름이 아니라 측정**이다.
> 옛 표는 절반이 틀렸다(정정 기록 3 참조). **파일 이름은 안 바꿨다** — 저장소 여러 곳이 이름을 인용하기
> 때문이다. **이름을 믿지 말고 이 표를 믿을 것.**

판정 방법(두 가지를 다 씀):
1. **눈으로** — 짐벌이 보이면 앞, 배터리·전원버튼·잔량 LED·후방 어안 2개가 보이면 뒤, 벨리 스파인
   (어안-캡슐창-보조등-어안)이 보이면 아래, RTK 돔·비콘이 보이면 위.
2. **실루엣 IoU** — 흰 배경을 지우고 bbox 를 256² 로 정규화해 짝짝이 IoU 를 계산. 같은 시선이면 0.95↑.
   좌우 반전판과의 IoU 도 같이 계산해 «거울 관계»를 잡았다.

| 파일 | ⭐측정한 시선 | 같은 시선 묶음 | 잴 수 있는 것 | 원본 URL |
|---|---|---|---|---|
| `p01_side_profile_left.jpg` | 🔴 **후면 3/4** (좌측면 아님) | B: `4E_2`(IoU .989) · `p05`(.991) | 동체 높이·다리 길이. ⚠ 짐벌은 **안 보인다** | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_2_1.png` |
| `p02_front_elevation.jpg` | 정면, 위 ~20° ✓ | A: `4E_1`(.970) · `p03`(.978) · `p12`(.989) | 좌우 폭·전방 어안 2개·짐벌 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_c391793e-25f1-41ce-b5e8-bce7087ac192.jpg` |
| `p03_front_elevation_gimbal.jpg` | 정면, 위 ~20°(클로즈업) ✓ | A | **4E 짐벌 렌즈 배치 판별** | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1_1440x1440_crop_center.png` |
| `p04_front_low_angle.jpg` | 🔴 **후면, 정투영에 가까움** (정면 아님) | D: `4E_4`(.955) | 배터리·전원버튼·잔량 LED 4칸·다리 벌어짐 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_2.jpg` |
| `p05_rear_elevation.jpg` | 후면 **3/4** (정투영 아님) | B | 후방 어안 2개·RTK 돔·방열구 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_5.jpg` |
| `p06_rear_low_angle.jpg` | 후면 3/4, **p05 의 좌우 반전** | C: `4E_3`(.982), B 와 거울(.988) | 반대쪽 대칭 검증 | `https://www.dronefly.com/cdn/shop/files/DJI_Matrice_4E_-_4.jpg` |
| `p07_iso_front_left.jpg` | 전방-좌, 위 ~21° ✓ | G: `p08`(.988) | 3D 형상 대조 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_1_1.png` |
| `p08_iso_rear_left_low.jpg` | 🔴 **p07 과 같은 사진**(저해상 판). 후방도 하방도 아니다 | G | p07 의 축소판 — 새 정보 없음 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_1_1_1440x1440_crop_center.png` |
| `p09_underside_plan.jpg` | 🔴 **저면 오블리크** — 나디르에서 **43.8° 기울어짐**(앞에서 올려봄). plan(정투영) 아님 | F: `p10`(.989) | ⭐⭐ **벨리 스파인 4종**(하방비전 2·3D적외선 1·보조등 1)·짐벌 웰·댐퍼 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_3_1.png` |
| `p10_underside_plan_alt.jpg` | 🔴 **p09 와 같은 사진**(저해상 판). 프롭 각도도 같다 | F | p09 의 축소판 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image_3_1_1440x1440_crop_center.png` |
| `p11_front_top_iso.jpg` | 정면, 위 ~20°(iso 아님) | A: `p03`(.969) | 상면 곡면·GNSS 돌출 | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1_720x720_crop_center.png` |
| `p12_top_front_iso.jpg` | 정면, 위 ~20°(고해상) | A | 상동, 2667² — **A 묶음의 대표** | `https://cdn.shopify.com/s/files/1/0480/3146/5632/files/M4E_Product_Image__1.png` |

**시선 묶음 요약 — 전기체 사진 17장에 서로 다른 시선은 7개뿐이다.**

| 묶음 | 시선 | 파일 |
|---|---|---|
| A | 정면, 위 ~20° | `4E_1` · p02 · p03 · p11 · p12 |
| B | 후면 3/4 (한쪽) | `4E_2` · p01 · p05 |
| C | 후면 3/4 (B 의 거울) | `4E_3` · p06 |
| D | 후면, 정투영 근접 | `4E_4` · p04 |
| E | 상면, 정투영 근접 | `4E_5` |
| F | 저면 오블리크(나디르 47°) | p09 · p10 |
| G | 전방-좌, 위 ~21° | p07 · p08 |

⭐ p09 의 축척(2026-08-07 측정, 이 폴더에서 유일하게 mm 를 잴 수 있는 저면 사진).
전체 수치와 재현 코드는 `outputs/meshgate_fisheye.json` 의 `photo_scale_basis` 에 있다.

- **전후 방향**(이미지 세로) — 두 갈래로 따로 구했고 **1.3 % 안에서 일치**한다.
  (ⅰ) CAD 하부커버(#119)의 벨리 4개 특징 x 좌표(+41.80 / +22.05 / −9.41 / −35.14 mm)에
  이미지 y 픽셀을 1차 맞춤 → **0.3758 mm/px**(잔차 −1.8 / +3.9 / −3.4 / +1.2 mm).
  (ⅱ) 앞·뒤 모터축 전후 간격(CAD 279.02 mm) → **0.3807 mm/px**.
  ⚠ (ⅰ)은 CAD 를 앵커로 쓰므로 **CAD 를 검증하지 못한다.** 검증하는 쪽은 (ⅱ)다.
- **가로 방향** 은 **다르다: 0.275 mm/px** (앞 모터쌍 0.2602 · 뒤 모터쌍 0.2897 의 중간).
  ⛔ **가로 치수를 전후 축척으로 재면 38 % 부풀려진다.** 축척비 1.38 = 나디르에서 **43.8° 기울어짐**.
- 앞·뒤 모터쌍의 가로 축척이 **10.7 % 다른 것은 원근**이다(앞이 카메라에 가깝다) — 정투영이 아니다.
  카메라 거리 ≈ 1.9 m 로 역산된다.
- 좌우 대칭축 x = 1333.0 px (210행 표본, 표준편차 0.79 px) → 카메라는 기체 중심면 위에 있다.
- 교차검사: 두 하방 비전의 전후 기선을 사진에서 재면 **81.0 mm**, CAD 는 **76.94 mm**(5.3 % 차).
  잔차 대부분은 어두운 얼룩의 무게중심이 창 경계에 잘린 탓이다 — 자릿수·순서를 확인하는 용도로만 쓸 것.

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
| `m05_sensing_system_placement.png` | Maintenance Manual p.14 «Sensing System» | ⭐ **전방위/하향 비전 센서 위치**(레이더 산란체 배치). ⚠ 배 가운데 항목을 «Omnidirectional Vision System» 이라 적었으나 User Manual §4.10 은 같은 자리를 «3D Infrared Sensing System» 이라 적는다 — 사양표(«기체 하단 3D 적외선 센서»)와 맞는 쪽은 User Manual 이다. **User Manual §4.10(p.45) 그림을 1차 근거로 쓸 것** |
| `m06_rear_omni_vision_detail.png` | Maintenance Manual p.14 «Omnidirectional Vision System» | **후방 어안 2개**(GNSS 돔 좌우) 확대 — 후방쌍이 2개임을 확정 |
| `m07_top_plan_prop_rotation_AB.png` | User Manual p.20 | **상면 평면 + 프롭 A/B 회전 방향** — 마이크로도플러 부호에 필요 |
| `m08_folded_aircraft_line.png` | In the Box p.1 | **접힘 상태 선도** |
| `m09_folded_top_arm_unfold.png` | User Manual p.20 | 접힘 상면 → 전방 암 펼침 |
| `m10_side_rear_arm_unfold.png` | User Manual p.20 | 측면 → 후방 암 펼침 |
| `m11_arm_fold_unfold_sequence.png` | Maintenance Manual p.10 | 암 접힘/펼침 2단 도해 |
| `m12_iso_appearance_line.png` | Maintenance Manual p.10 | 펼침 기체 iso 선도(외형 대조) |
| `m13_battery_bay_bottom.png` | Maintenance Manual p.10 «Battery Compartment» | 🔴 **저면이 아니라 후면**이다 — 배터리를 뺀 상태로 **뒤에서** 본 배터리실. 위쪽 좌우 원 2개는 후방 어안, 아래 그릴 2개와 E-Port 는 꼬리 하단이다. 파일 이름의 `bottom` 을 믿지 말 것 |
| `m14_battery_install_iso.png` | User Manual p.20 | 배터리 삽입 방향·위치 |
| `m15_arm_led_landing_gear.png` | Maintenance Manual p.10 | 암 LED·다리(내장 안테나) 형상 |
| `m16_aux_light_underside.png` | Maintenance Manual p.14 «Auxiliary Light» | 하면 보조등(벨리 스파인 **3번째** 항목). ⚠ 크롭 아래에 보이는 «Beacon» 글자는 **다음 그림의 캡션**이지 이 그림의 것이 아니다 — 잘라 쓸 때 이 항목을 비콘으로 오독하기 쉽다 |
| `m17_beacon_topside.png` | Maintenance Manual p.14 «Beacon» | 비콘 — **후방 갑판 위 중심선**(상면 전체가 아니라 꼬리쪽). CAD 로는 (x −50, y 0, z +55) 의 지름 6.2 mm 구 |
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

---

## 🔴 정정 기록 3 — 시선방향 표를 통째로 다시 쟀다 (2026-08-07)

**계기.** `p01` 이 «좌측면 프로파일» 로 적혀 있었는데 열어 보니 **후면**이었다. 한 줄만 고치는 대신
폴더 전체를 다시 훑었다. 표가 «파일 이름이 말하는 각도» 를 그대로 옮겨 적은 것이었기 때문이다.

**고친 것 6줄** (자세한 근거는 위 p 표):

| 파일 | 옛 라벨 | 실제 |
|---|---|---|
| `p01` | 좌측면 프로파일 ⭐«기존 5장에 없던 각도» | **후면 3/4** — `4E_2`·`p05` 와 같은 시선(이미 있던 각도) |
| `p04` | 정면 하방 | **후면**, 정투영 근접 |
| `p08` | iso 후좌 하방 | **`p07` 과 같은 사진**의 저해상 판 |
| `p10` | 저면(프롭 각 다름) | **`p09` 와 같은 사진**의 저해상 판, 프롭 각도도 같다 |
| `p09` | 저면 | 저면 **오블리크**(나디르 47°) — 정투영 plan 아님 |
| `m13` | 저면 배터리 베이 | **후면** 배터리실(정비매뉴얼 «Battery Compartment») |

**옛 표를 믿고 잰 값 — 어디에 얹혀 있나.**

1. `outputs/meshdef_prop_gap.json` → `ground_truth.photo` : `p01` 을 **측면**으로 알고 모터 캔 높이
   (12.22 mm 앵커, 6.3011 px/mm)와 블레이드 중립면 z 를 쟀다.
   - **살아남는 것**: 세로(z) 값과 세로 앵커. 방위 회전으로 안 변한다.
   - **흔들리는 것 (a)**: 후면뷰에서 가까이 잡히는 벨은 **뒤 모터**인데 CAD 비교 대상은 **앞 로터
     스택**(x,y = 139.49, 179.28)이었다. `benchmark/meshdef_attack_verdict.py` A10 이 이미 지적했다.
   - **흔들리는 것 (b) — 아직 아무 데도 안 적힌 것**: `blade_neutral_plane_z_mm` 의 `r20`…`r50`
     라벨은 **가로 거리**라 요(yaw)만큼 단축된다. 즉 «r=20 mm 에서의 z» 는 실제로는 더 바깥
     반경의 z 다. 블레이드면이 r 에 따라 오르므로(15.18 → 18.2) **z 가 과대평가되는 방향**이다.
     결론(블레이드면 +15.2~15.7 vs CAD +15.31)은 낮은 r 구간이라 뒤집히진 않지만
     **«0.4 mm 안에서 일치» 는 낙관적**이다.
2. `outputs/matrice4e_photo_measure.json` → `photo_inventory.distinct_directions` : `p01`·`p05`·`4E_2`
   묶음을 «기수 판독 불가» 로 IoU 등록에서 **뺐다**. 이제 판독된다(후면) — 다시 넣을 수 있다.
   같은 파일이 «p09 는 오블리크(elev −64)» 라고 적은 것은 **맞다**(이번 측정 −47°, 같은 결론).
3. `src/drone_cad.py:2189-2208` 주석 : 「하방쌍 = CAD 렌즈 하우징 43/45」 — **이게 최대 오염**이고
   이번 게이트(`outputs/meshgate_fisheye.json`)가 뒤집는다. 아래 절 참조.

**교훈: 파일 이름은 측정값이 아니다.** 이 폴더의 이름은 수집 당시 판매점 캡션·추측에서 왔다.
이름을 인용한 곳이 많아 개명은 못 하니, **표를 1차 근거로 삼고 이름은 식별자로만 쓴다.**

---

## ⭐⭐ 배(belly)에 실제로 무엇이 붙어 있나 — 2026-08-07 게이트 결론

세 출처가 **같은 답**을 낸다. 전부 **동체 중앙선(y = 0) 위, 앞뒤 한 줄**이다.

| 앞→뒤 | 부품 (DJI 공식 명칭) | CAD 좌표(우리 축) | CAD 치수 | 사진 `p09` |
|---|---|---|---|---|
| 1 | **Downward Vision System** (하방 비전 1) | x **+41.80**, y 0, z −24.4 | 안착 원 **Ø14.44 mm** | 어안 렌즈(유리 보임) |
| 2 | **3D Infrared Sensing System** (3D 적외선) | x **+22.05**, y 0, z −26.2 | 캡슐창 **11.9 × 20.1 mm**(가로가 김) | 검은 타원창 |
| 3 | **Auxiliary Light** (보조등) | x **−9.41**, y 0, z −25.1 | Ø **10.79 mm** | 노란 LED |
| 4 | **Downward Vision System** (하방 비전 2) | x **−35.14**, y 0, z −27.4 | 안착 원 **Ø14.44 mm** — 1번과 **면적까지 동일** | 어안 렌즈 |

- 두 하방 비전의 **전후 기선(baseline) = 76.94 mm**(CAD). 사진에서 잰 값 78.4 mm(1.9 % 차).
- 근거 셋: ① User Manual §4.10(p.45) 도해 콜아웃 ③④②③ · ② User Manual p.9 부품도 ④⑤⑥④ ·
  ③ 공식 STEP 의 하부커버 솔리드 #119 안에 파인 **자리(seat) 형상**(같은 면적의 원·토러스·콘이
  두 자리에서 소수점 둘째 자리까지 같다).
- 전방위 비전(어안)은 **위쪽에만 4개**다: 기수 상단 (x +146.0, y ±30.2, z +48.6) · 꼬리 상단
  (x −53.6, y ±30.3, z +49.5). CAD 에서 이 4개만 **구면(Sphere) 면**을 갖고 부피가 556 mm³ 로 같다.
- ⛔ **CAD 솔리드 #44/#46(x +84.4, y ±17.74, z −13.6)은 어안이 아니다.** 같은 부품이 **4벌**
  있고(#44·#45·#46·#47, 부피 173.67 mm³ 로 동일), 나머지 두 벌은 **기수 상단**(x +132.2, z +46.6)에
  있다. 하방 카메라가 기수 위에 쌍둥이를 가질 수는 없다. 사진 `p09` 의 짐벌 웰을 확대하면
  그 자리에 **유리 없는 고무 방진(damper)** 두 개가 좌우로 보인다 — 짐벌 4점 방진의 아래 두 점이다.

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
