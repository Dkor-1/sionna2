# DJI Mavic 4 Pro — 참조 이미지 출처

`mavic4pro` 는 **실측 캠페인 대상 2기종** 중 하나인데(→ `sionna2-project-direction`),
2026-08-03 아침까지 사진이 **4장**뿐이었고 실루엣 IoU 가 상한 대비 **57 %** 로 하위권이었다.
비교: `x500v2` 는 사진 16장 + 제조사 STEP 으로 **91 %**.

⚠ 실측이 어긋날 때 **원인이 물리인지 메쉬인지 가르지 못하는** 상태였다. 이번 라운드는
그 근거 부족을 메우는 **수집 라운드**다 — 메쉬(`src/drones.py` · `src/drone_cad.py`)는
이번에 **건드리지 않았다**.

**4 → 52 장.** 그중 **분해 16장**(우리 기체 통틀어 최초의 teardown), **도면·라벨 6장**,
**부품 13장**, **제품 13장**, 기존 렌더 4장.

## ⭐ 이 세트의 핵심: FCC 시험소 사진 23장 (자·눈금 포함)

가장 값어치 있는 건 **FCC ID `SS3-L3AB2410`** 의 공개 exhibit 다.
DJI 가 기밀유예를 걸지 않아 **내부 사진이 그대로 공개**돼 있고, 시험소 관행대로
**전 컷에 금속 자(cm 눈금)가 같이 찍혀 있다**. 즉 사진에서 **직접 치수를 읽을 수 있다** —
우리가 가진 다른 어떤 기체 사진보다 강한 근거다.

- 신청서: <https://fccid.io/SS3-L3AB2410>
- 신청인: SZ DJI TECHNOLOGY CO., LTD / 출원 2024-12-04
- 라이선스: **미국 연방정부 공개 기록**(FCC 공중열람). 연구 인용 자유, 저작권 주장 없음.

## ⚠ 변종·세대 확인 (이름이 비슷한 다른 모델과 섞이지 않았다는 근거)

이 폴더는 **DJI Mavic 4 Pro (2025-05 출시)** 하나만 담는다. 근거는 셋:

1. **명판 직접 증거** — `mavic4pro_m06_fcc_product_label_L3A.png` 에
   `DJI / Mavic 4 Pro / 型号 Model:L3A`, `FCC ID: SS3-L3AB2410`,
   `Powered by battery 14.32V 6654mAh 95.3Wh` 가 인쇄돼 있다.
2. **FCC 첨부 QSG 본문** — `Product name: DJI Mavic 4 Pro / Model Number: L3A, L3B`.
   즉 **L3A·L3B 는 같은 기체의 두 무선 변종**이지 다른 기종이 아니다.
   (참고: Mavic 3 는 `L2A`/`L2P` 계열 — 세대 접두가 다르다.)
3. **형상 배지** — 부품 사진 `c01` 의 우상단 암에 `MAVIC 4 PRO` 각인.

**혼동 위험이 실제로 있는 이름들**(이 폴더에 **없음**을 명시):
Mavic 3 Pro(3렌즈지만 짐벌이 360° 회전 안 함), Mavic 4(비-Pro 미출시),
Mini 4 Pro, Air 3S. Mavic 4 Pro 만의 식별 표지는
**① 360° 회전 "Infinity Gimbal"(원통형 하우징) ② 전방 LiDAR ③ 프롭 팁 주황 ④ 앞다리 2개뿐**.

### ⚠ FCC 개체는 **양산 전 시제(EVT)** 다

FCC 사진의 기체는 2024-12 제출본이라 셸에 마스킹테이프·수작업 흔적이 있고
도색이 양산품과 다르다(밝은 회색). **형상·치수·내부배치 근거로는 쓰되,
표면 마감·색은 양산기 사진(`p08`~`p13`)을 기준으로 삼아라.**
골격 치수는 양산 공표값(아래)과 모순되지 않는다.

## 공표 치수 (형상 근거의 기준선)

DJI 공식 제원 <https://www.dji.com/global/mavic-4-pro/specs> 및 사용설명서 v1.0(2025.05):

| 항목 | 값 |
|---|---|
| 펼침(프롭 제외) | **328.7 × 390.5 × 135.2 mm** (L×W×H) |
| 접힘(프롭 제외) | **257.6 × 124.8 × 103.4 mm** |
| 접힘(프롭 포함) | 257.6 × 124.8 × 106.6 mm |
| 이륙중량 | 1063 g (MTOM 1085 g, UAS Class C2) |
| 최대 프롭 회전수 | 8400 RPM (설명서 p.88 C2 표) |
| 배터리 | 14.32 V · 6654 mAh · 95.3 Wh |

> **우리 메쉬는 "펼침" 상태다**(`envelope_mm=(None,None,135.2)`).
> 접힘 상태 근거가 필요하면 `m03` 과 `p01`(자 포함 톱뷰)을 써라.

---

## 파일 — p: 제품 사진 (13장)

`p01`~`p07` 은 **FCC 외부 사진**(전 컷 자 포함, 시험소 촬영, 공개기록).
`p08`~`p13` 은 **Wikimedia Commons 양산기 실사** — 촬영자 표기 필요.

| 파일 | 촬영각 / 무엇이 보이나 | ⭐ 무엇을 잴 수 있나 | 출처·라이선스 |
|---|---|---|---|
| `mavic4pro_p01_fcc_top_plan_ruler.jpg` | **톱 평면**, 펼침·프롭 접힘, 직각자 2변 | ⭐⭐ **로터 4개 좌표·암 각도·동체 L/W** — `rotor_deg=51.4°` 를 직접 반증/확증할 수 있는 유일한 컷 | FCC ext.1 / 공개기록 |
| `mavic4pro_p02_fcc_front_elev_battery_in_ruler.jpg` | 정면 입면, 배터리 장착, 자 | 전폭·다리 높이·모터 포드 높이 | FCC ext.2 |
| `mavic4pro_p03_fcc_front_elev_battery_out_ruler.jpg` | 정면 입면, **배터리 제거** | 배터리 베이 개구 치수, 동체 두께 | FCC ext.3 |
| `mavic4pro_p04_fcc_left_side_iso_ruler.jpg` | 좌측 아이소, 자 | 동체 측면 실루엣·짐벌 전방 돌출량·다리 | FCC ext.4 |
| `mavic4pro_p05_fcc_front_elev_gimbal_ruler.jpg` | **정면 정투영에 가까움**, 짐벌 정면 | ⭐ 짐벌 외경·전폭·다리 스팬 | FCC ext.5 |
| `mavic4pro_p06_fcc_right_side_elev_ruler.jpg` | **우측 입면**, 자 | ⭐ 전고(135.2 mm) 검증·동체 측면 프로파일 | FCC ext.6 |
| `mavic4pro_p07_fcc_bottom_plan_ruler.jpg` | **저면 평면**, 자 | ⭐⭐ 하향 비전센서·보조등 위치, 배터리 베이, **다리 4개 여부 판정** | FCC ext.7 |
| `mavic4pro_p08_rear34_ground_unfolded.jpg` | 후방 3/4, 지면, 양산기 | 후면 배기구·배터리 후면·프롭 팁 주황 | Commons `DJI Mavic 4 Pro (rear).jpg`, **CC BY-SA 4.0**, User:Benlisquare |
| `mavic4pro_p09_front34_ground_unfolded.jpg` | 전방 3/4, 지면, 양산기 | 짐벌 3렌즈 배치·전방 LiDAR·앞다리 | Commons `DJI Mavic 4 Pro.jpg`, **CC BY-SA 4.0**, User:Benlisquare |
| `mavic4pro_p10_belly34_inflight.jpg` | ⭐ **비행 중 하부 3/4**(깨끗한 하늘 배경) | 저면 실루엣·짐벌 회전 자세·다리 형상 — **실루엣 IoU 에 바로 쓸 수 있는 배경분리 쉬운 컷** | Commons `DJI - Drohne Mavic 4 Pro (b).JPG`, **CC BY-SA 4.0**, C.Stadler/Bwag |
| `mavic4pro_p11_side_inflight.jpg` | 비행 중 측면 | 프롭 회전 블러·자세 | Commons `DJI - Drohne Mavic 4 Pro.JPG`, **CC BY-SA 4.0**, C.Stadler/Bwag |
| `mavic4pro_p12_front34_inflight.jpg` | 비행 중 전방 3/4 | 전면 형상 | Commons, **CC BY 4.0**, User:Hayden Soloviev |
| `mavic4pro_p13_top34_inflight.jpg` | 비행 중 상부 3/4 | 상면 실루엣 | Commons, **CC BY-SA 4.0**, User:Benlisquare |

> CC BY(-SA) 는 **저작자 표시 의무**가 있다. 리포트·덱에 실을 때 위 표의 촬영자와
> 라이선스를 캡션에 적어라. FCC 컷(`p01`~`p07`)은 그 의무가 없다.

## 파일 — t: ⭐⭐ 분해 (16장, 전부 FCC internal photos)

**우리 기체 통틀어 최초의 teardown 세트다.** 전 컷 자 포함.
RCS 쪽으로 특히 중요하다 — 우리 PO 모델은 내부 금속(배터리·PCB·히트싱크)을
`GROUP_GAMMA` 로 가중하는데(→ `sionna2-rcs-materials`), 그 **내부 금속의 실제 크기·위치**를
지금까지는 추정으로만 넣고 있었다. 이제 실물 근거가 있다.

| 파일 | 무엇이 보이나 | ⭐ 무엇을 잴 수 있나 |
|---|---|---|
| `t01_bottomshell_off_battery_out_ruler` | 하부 셸 제거, 배터리 분리, 메인보드 노출 | ⭐ **배터리 팩 외형 치수**, 동체 내부 공동 크기 |
| `t02_topshell_off_gnss_module_ruler` | 상부 셸 제거, GNSS 모듈 분리, 히트싱크·팬·짐벌 | ⭐ GNSS 패치 안테나 크기, 내부 적층 순서 |
| `t03_fan_heatsink_coax_closeup` | 원심팬 + **대형 알루미늄 히트싱크(핀 구조)** + 동축 배선 | ⭐⭐ **히트싱크 판 치수** — 동체 내 최대 금속면, 산란 기여 지배적 |
| `t04_chassis_stripped_board_fan_ruler` | 골격만 남은 섀시 + 메인보드·팬을 옆에 분리 | ⭐ 섀시 폭·길이, 보드 실장 위치 |
| `t05_shield_frame_and_board_ruler` | 금속 실드 프레임 + 보드 나란히 | ⭐ 실드 프레임 외형(금속 면적) |
| `t06_mainboard_top_ant0_ant5_ruler` | 메인보드 상면, **`ANT0`~`ANT5` 커넥터 6개** 실크 | ⭐⭐ **안테나 급전점 6개 위치** — 패시브/통신 모델링 직결 |
| `t07_mainboard_bottom_shields_ruler` | 메인보드 하면 실드캔 | ⭐ 보드 외형 치수(≈ 12 × 5 cm 급) |
| `t08_battery_bay_coax_routing` | 배터리 베이 내부 + **동축이 앞다리 쪽으로 빠지는 배선** | ⭐⭐ **다리 내장 안테나**로 가는 급전 경로 실물 확인 |
| `t09_mainboard_shields_removed_ruler` | 실드캔 벗긴 메인보드 + 캔 조각들 | ⭐ 실드캔 개별 치수 |
| `t10_wifi_antennas_pair_ruler` | ⭐ **Wi-Fi 안테나 2개 단품**(`RX-KE79 WIFI`, 2411) | ⭐⭐ **안테나 실물 크기·형상** |
| `t11_powerboard_and_shieldcans_ruler` | 전원보드 + 실드캔 | 보드 치수 |
| `t12_mainboard_soc_dram_ruler` | 메인보드 SoC·SK hynix DRAM | 부품 배치 |
| `t13_powerboard_reverse_ruler` | 전원보드 뒷면 | 보드 치수 |
| `t14_storage_flash_closeup` | SanDisk `SDIN8DG4-16G` 플래시 | 부품 식별 |
| `t15_soc_dram_closeup` | SoC + SK hynix `HN8T274EJK` 근접 | 부품 식별 |
| `t16_flight_battery_standalone_ruler` | ⭐ **배터리 단품**, 자 | ⭐⭐ **배터리 3변 치수** — 내부 최대 금속체 |

## 파일 — m: 도면·라벨 (6장)

DJI 공식 문서에서 **벡터 선도**를 200~220 dpi 로 렌더한 것이다(스캔 아님).
원본: 사용설명서 <https://dl.djicdn.com/downloads/mavic-4-pro/20250513/DJI_Mavic_4_Pro_User_Manual_v1.0_en.pdf>
및 FCC 첨부 QSG <https://fccid.io/SS3-L3AB2410/User-Manual/User-Manual-7873601>.
라이선스: © 2025 DJI, **연구 참조용 인용**. 재배포 덱에 실을 땐 출처 표기.

| 파일 | 무엇이 보이나 | ⭐ 무엇을 잴 수 있나 |
|---|---|---|
| `m01_qsg_aircraft_lineart_callouts` | ⭐ QSG 대형 **선도 2뷰**(전방 아이소 + 후방 아이소), 콜아웃 16 | ⭐⭐ 가장 큰 공식 라인아트 — 형상 대조 기준판 |
| `m02_manual_overview_front_rear_iso` | 설명서 §1.2 개요, 전·후 아이소 + 콜아웃 | ⭐ **`8. Landing Gears (Built-in antennas)`** — 다리에 안테나 내장 |
| `m03_manual_fold_unfold_sequence_topplan` | ⭐ **접힘 톱뷰 + 접힘 측면 + 펼침 톱 평면**(3단 시퀀스) | ⭐⭐ **접힘/펼침 두 상태 모두**, 펼침 평면도에서 암 각도 |
| `m04_manual_sensing_system_positions` | §5.4 센싱계 — 전방·후방 아이소에 센서 위치 | 옴니 비전 6방향·보조등·적외선·LiDAR 위치 |
| `m05_manual_battery_removal_and_pack` | 배터리 탈착도 + 배터리 단품 선도 | 배터리 장착 방향·버클 위치 |
| `m06_fcc_product_label_L3A` | ⭐ **명판**(Model:L3A, FCC ID, 배터리 제원) | 변종 확정 근거(위 §변종 참조) |

> ⚠ **3면도(정투영 치수 기입 도면)는 DJI 가 공표하지 않는다.** x500v2 처럼 제조사 STEP 도 없다.
> 그래서 이 기종의 치수 1차 근거는 **공표 제원 표 + FCC 자 포함 사진(`p01`·`p05`·`p06`·`p07`)** 이다.
> `m*` 는 **형상·부품 배치**의 근거이지 치수의 근거가 아니다.

## 파일 — c: 부품 단품 (13장)

출처: djioemparts.com (DJI OEM 부품 재판매), 흰 배경 스튜디오.
`https://djioemparts.com/collections/mavic-4-pro` · 이미지 CDN `cdn.shopify.com/s/files/1/0243/4705/0080/files/…`
라이선스: 판매점 상품 사진, **연구 참조용**. ⚠ 워터마크 있음 — 덱에 그대로 싣지 말 것.

| 파일 | 무엇이 보이나 | ⭐ 무엇을 잴 수 있나 |
|---|---|---|
| `c01_four_motor_arms_laid_out` | ⭐ **암 4개 전부** 나란히, 배선 포함, `MAVIC 4 PRO` 각인 | ⭐⭐ **앞암 2개에만 다리** — 뒷암 2개는 매끈 |
| `c02_arm_positions_topview_labelled` | 톱뷰에 FL/FR/RL/RR 라벨(제조사 렌더 기반) | 암 4개 방위 대응 |
| `c03_arm_front_left_top` / `c04_arm_front_left_motor_end` | 앞좌 암 단품 2각 | ⭐ **암 길이·단면·모터벨 외경**, 다리 부착 위치 |
| `c05_arm_front_right` | 앞우 암 | 좌우 대칭성 |
| `c06_arm_rear_left_no_leg` / `c07_arm_rear_right_no_leg` | ⭐ 뒷암 2개 — **다리 없음이 명확** | 앞/뒤 암 형상 차이 |
| `c08_esc_module_iso` / `c09_esc_module_reverse` | ESC 보드 단품 양면 | ESC 보드 치수(암 내부 금속) |
| `c10_propeller_pair_1158F` / `c11_propeller_hub_detail` | ⭐ 프롭 1쌍(2엽, 팁 주황) + 허브 | ⭐ **블레이드 평면형·현 분포** — 마이크로도플러 모델 입력 |
| `c12_flight_battery_product` | 배터리 제품 사진 | `t16` 과 교차확인 |
| `c13_gimbal_bracket_caps` | 짐벌 브래킷·캡 소품 | 짐벌 하우징 구성 |

## 파일 — d: 기존 렌더 4장 (이름 그대로 유지)

| 파일 | 상태 |
|---|---|
| `mavic 4 pro_1.png` ~ `mavic 4 pro_4.png` | 2026-07-20 부터 있던 것. **삭제하지 않았고 이름도 바꾸지 않았다.** |

⚠ **이름을 규약대로 못 고친 이유**: `src/drones.py` 의 `mavic4pro` 노트와
`src/drone_cad.py` 의 프로비넌스가 이 파일들을 **파일명으로 인용**하고 있다
(예: "mavic 4 pro_2.png 와 _4.png 는 앞 모터 포드 밑의 2갈래 다리를 보여준다",
`gear_h_mm=48.0` 은 `_2.png` 에서 실측). 지금 다른 워크플로가 그 파일들을 편집 중이라
이름을 바꾸면 **프로비넌스 포인터가 끊긴다.** 규약보다 근거 추적성이 우선이라 유지했다.
나중에 메쉬 담당이 개명할 때 노트도 같이 고치면 된다.

⚠ **출처 불명**: 이 4장은 URL 기록이 없다. 형상은 실물과 대체로 맞지만(3렌즈 짐벌·주황 팁·앞다리),
**1차 근거로 쓰지 말라** — 이제 같은 각도를 자까지 포함해 커버하는 FCC 컷이 있다.
`_1`/`_2` 정면, `_3` 후상방, `_4` 전방 아이소.

---

## 이번 수집이 밝힌 것 (메쉬 담당에게)

메쉬는 이번 라운드에서 **건드리지 않았다.** 아래는 관측 기록이지 수정 지시가 아니다.

1. ✅ **다리는 앞 2개뿐, 모터 포드 바로 안쪽에 붙는다.** `c01`·`c06`·`c07` 에서
   뒷암이 매끈함이 명확하고, `p10`·`p09` 에서 앞다리 위치가 보인다.
   현재 `gear="motor_legs"` 와 **모순 없음**. 다만 "앞 2개뿐"이 코드에 명시돼 있는지는 확인 필요.
2. ⭐ **다리에 안테나가 들어 있다** — 설명서가 `Landing Gears (Built-in antennas)` 라고 못박고,
   `t08` 이 동축이 앞다리로 빠지는 걸 실물로 보여준다. 다리를 순수 플라스틱으로 두면
   RCS 가 과소평가될 수 있다. **열린 질문**으로 남긴다.
3. ⭐⭐ **`rotor_deg=51.4°` 를 이제 반증 가능하다.** `p01`(자 포함 톱 평면)에서 로터 4개
   좌표를 직접 읽으면 된다. 지금까지 51.4° 는 공표 envelope 에서 **역산한 값**이었지
   측정값이 아니었다(`drones.py` 노트 참조). 사진이 그 역산을 검증한다.
4. **내부 금속의 실물 근거가 처음 생겼다** — 히트싱크(`t03`), 실드캔(`t09`),
   배터리(`t16`), 안테나(`t10`). `GROUP_GAMMA` 가중을 추정에서 실측으로 올릴 수 있다.

## 재수집 방법 (스크립트 없이 손으로)

```
FCC exhibit PDF  : https://fccid.io/SS3-L3AB2410/<Exhibit-Path>.pdf
  (Internal-Photos-1-of-2-7873588 / -2-of-2-7873589 / External-Photos-7873553 /
   User-Manual-7873601 / Product-Label-and-Location-7873597)
  → PyMuPDF 로 page.get_images() 하면 원본 해상도 그대로 나온다(재압축 없음).
설명서 PDF       : https://dl.djicdn.com/downloads/mavic-4-pro/20250513/DJI_Mavic_4_Pro_User_Manual_v1.0_en.pdf
  → 도면은 벡터라 embedded image 가 0 이다. page.get_pixmap(dpi=200) 으로 **렌더**해야 한다.
Commons 목록     : commons.wikimedia.org/w/api.php?action=query&generator=categorymembers
                   &gcmtitle=Category:DJI%20Mavic%204%20Pro&prop=imageinfo&iiprop=url|extmetadata
부품 목록        : https://djioemparts.com/collections/mavic-4-pro/products.json?limit=250
```

수집일 2026-08-03. 이전 4장은 2026-07-20.
