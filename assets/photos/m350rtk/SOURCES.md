# DJI Matrice 350 RTK (`m350rtk`) — 참조 이미지 출처

`m350rtk` 는 **2026-08-03 에 새로 만든 기체 키**다. 이 저장소에 그 전까지 이 기체는 없었다.
기존 7 기체(`mavic4pro` `mini5pro` `matrice4e` `phantom3` `phantom4` `s1000plus` `typhoonh480`
`x500v2`) 정의는 이 작업에서 **전혀 건드리지 않았다.**

> ⚠ **혼동 금지.** 이 폴더의 기체는 `mini5pro`(DJI Mini 5 Pro) 도 `matrice4e`(DJI Matrice 4E) 도
> **아니다.** 셋 다 별개 기체다. Matrice 350 RTK 는 이륙중량 9.2 kg 급 산업용 쿼드콥터로,
> Matrice 4E(소형 접이식)와 체급이 다르다.

**왜 모았나** — Das 등의 다중대역 RCS 논문 Table I·III 에 이 기체의 계수가 인쇄되어 있다.
우리가 메쉬를 만들어 그 계수에 맞추면 메쉬 방법 검증의 표본이 N=1 에서 N=4 로 늘어난다.
(대조표: `outputs/das_fleet_spec.json`, 공표 제원: `outputs/m350rtk_specs.json`)

---

## 0. 변종 확인 — 이게 정말 M350 RTK 인가 (M300 RTK 아니고)

M350 RTK 는 **M300 RTK 와 기체 외형이 거의 같다.** DJI 가 에어프레임을 그대로 물려받았기
때문이다. 그래서 "이 사진이 M350 이다" 를 **명판으로 증명**했다.

### 1차 증거 (결정적)

`m350rtk_m07_nameplate_label_fccid.png` — FCC 제출 명판 원본. 글자 그대로:

```
DJI MATRICE 350 RTK              型号/Model: M350 RTK
CMIIT ID: 2023AP2330   FCC ID: SS3-M3502301   IC: 11805A-M3502301
Powered by Battery: 44.76V  5880mAh, 263.2Wh
```

이 폴더의 `p05`~`p15`(외부 사진 11장)과 `t01`~`t26`(내부 사진 26장)은 **전부 같은 FCC 출원
`SS3-M3502301` 의 첨부물**이다. 명판이 M350 RTK 를 못박으므로 그 출원의 사진 전체가
M350 RTK 로 확정된다. — 이게 이 폴더에서 가장 강한 근거다.
(External Photographs 6쪽 = 11장 전량, Internal Photographs 43쪽 = 86장 중 26장을 실었다.)

대조군: M300 RTK 의 FCC ID 는 **`SS3-M3001910`** 으로 다르다.

### 2차 증거 (사진에서 눈으로 구별하는 법)

| 단서 | M350 RTK | M300 RTK | 이 폴더에서 보이는 곳 |
|---|---|---|---|
| **프로펠러 팁 색** | **주황/황등색 띠** | 무지 검정 | `c01`, `d07`, `d08`, `p02`, `p03` |
| 동체 회색 톤 | 더 짙은 회색 | 밝은 회색 | `d01`, `p09` |
| 암 접이 잠금 | 한 손 조작, **미체결 감지 센서 있음**(앱에 오류 표시·이륙 차단) | 2단 조작, 감지 없음 | `m02`(펼침 절차도), `p07` |
| FPV 카메라 | 1080p + **야간투시** | 960p, 야간투시 없음 | `p08`(노즈 센서 군집) |
| 배터리 | **TB65** (44.76 V / 5880 mAh / 263.2 Wh) | TB60 | `c02`, `d06`, `p10`, `p11`, 명판 |
| 조종기 | RC Plus | Smart Controller Enterprise | (이 폴더 범위 밖) |

⚠ **주의**: 프로펠러(2110s)와 랜딩기어 모듈은 M300/M350 **호환 부품**이다. 즉 프로펠러 팁 색은
"이 기체에 지금 꽂혀 있는 프롭" 의 단서일 뿐, 기체 세대의 결정적 증거가 아니다.
결정적 증거는 언제나 명판/FCC ID 다.

---

## 1. Das 는 어느 상태로 쟀나 — **펼친 상태(unfolded), 프로펠러 제외 치수**

`outputs/das_fleet_spec.json` 의 Table I, M350 RTK 열:

```
"literal": "81.0 cm x 67.0 cm"   →  810 mm x 670 mm
```

DJI 공표 제원(사용자 매뉴얼 v1.2 부록 · enterprise.dji.com/matrice-350-rtk/specs):

```
크기 (펼쳤을 때, 프로펠러 제외) : 810 x 670 x 430 mm (L x W x H)   ← 두 수가 글자 단위로 일치
크기 (접었을 때, 프로펠러 포함) : 430 x 420 x 430 mm (L x W x H)   ← 전혀 다름
```

**판정: `folded_state = "unfolded"`.** Das Table I 의 81×67 은 DJI 의 *펼친·프로펠러 제외* 항목을
그대로 옮긴 값이고, *접힌* 항목(43×42)과는 닮지도 않았다. 그러므로 우리 메쉬도 **펼친 자세**로
만들어야 Table I 과 앞뒤가 맞는다.

⚠ **다만 이 판정의 한계를 정직하게 적어 둔다.**
1. Table I 의 "Dimension" 은 **카탈로그 전재**일 뿐, 측정 자세를 명시한 문장이 아니다.
   두 수가 정확히 일치한다는 것이 근거이지, 원문의 진술이 근거인 것은 아니다.
2. ⭐ **프로펠러가 빠진 치수다.** 대각 축거 895 mm 에 프로펠러 지름 약 533 mm 를 더하면
   블레이드 팁-팁 폭은 **약 1.43 m** 로, 81×67 대각(1.051 m)보다 훨씬 크다.
   21–27 GHz(λ≈11–14 mm)에서 프로펠러는 거대한 산란체다. Table I 치수를 그대로
   전기적 크기로 쓰면 **과소평가**한다. `das_fleet_spec.json` 의 `farfield_check.D_diag_m = 1.0512`
   도 프로펠러를 뺀 값이므로 같은 주의가 필요하다.
3. ⚠ **`das_fleet_spec.json` 은 M350 RTK 열의 출처를 `"data from ref [7] (Wang et al.,
   China Commun. 2026), via Prof. Wei Fan"` 로 기록하고 있다.** 즉 이 기체는 Das 연구진이
   직접 무향실에서 잰 것이 아니라 **인용해 온 데이터**일 가능성이 높다. 이 폴더를 근거로
   "Das 가 M350 을 쟀다" 고 단정하지 말 것. 편파도 `⚠ UNVERIFIED` 로 남아 있다.

---

## 2. 파일 목록 — **총 65장**

접두어 규약: `m350rtk_<종류><번호>_<설명>.<ext>`
**d**=공식 렌더 8 · **p**=제품/실사진 21 · **t**=분해 26 · **m**=도면/문서 7 · **c**=부품 단품 3

> 수집은 두 차례다. **초판(45장)** 이후 **2026-08-03 2차(+20장)** 에서
> FCC 첨부 97장 전수 추출 · DJI CDN 107개 전수 수집 → 상관계수 중복 제거 → 선별 추가했다.
> **초판 45장은 하나도 바꾸지 않았다(append-only).** 번호는 종류별로 이어 붙였다.

### d — DJI 공식 스튜디오 렌더 (8장)

출처: <https://enterprise.dji.com/matrice-350-rtk> 제품 페이지 CDN(`www-cdn.djiits.com`).
전부 검정 배경 스튜디오 렌더라 **배경 분리가 쉽다.**

> ⚠ 아래 해상도는 **2026-08-03 재검증한 실제 픽셀 크기**다. 초판 표에 적혀 있던
> `d01` 1280² · `d02` 2400×1200 · `d04` 2400×1500 은 **틀린 값이어서 고쳤다.**
> (CDN 에 1280² 파일이 있기는 하나 그것은 DJI Cloud API 로고이지 기체 렌더가 아니다.)

| 파일 | 촬영각 | 무엇을 잴 수 있나 |
|---|---|---|
| `d01_front_elevation_unfolded.png` (720²) | 정면 정투영에 가까움, 펼침, 프롭 장착 | ⭐ 암 하각(dihedral), 다리 벌림각, 프롭 팁 궤적 폭, 동체 폭 대 축거 비 |
| `d02_iso34_unfolded.jpg` (1200×600) | 전방 좌 3/4 아이소, 펼침 | 암 배치(X형 4암), 짐벌 마운트 위치, 다리 형상 |
| `d03_belly_downward_vision_auxlight.jpg` (982²) | 하면 근접 | 하향 비전 카메라 2개·보조등·짐벌 커넥터 배치, 배 밑 판 형상 |
| `d04_rear34_heat_vents.jpg` (982²) | 후방 3/4 근접 | 배터리부 방열 슬릿 피치, 후미 셸 곡률 |
| `d05_battery_bay_switch_panel.jpg` (2400×1500) | 배터리 베이 상면 패널 근접 | 전원 버튼·상태등·D 마킹, 패널 평면 |
| `d06_dual_tb65_installed.jpg` (2400×1200) | 후방, TB65 2개 장착 | 배터리 2개가 동체 후면에 **나란히 외부 노출**됨 — RCS 에 중요 |
| `d07_arm_tip_motor_prop_hub.jpg` (982²) | 암 끝·모터·프롭 허브 근접 | 카본 튜브 지름 대 모터 캔 지름, 폴딩 허브 형상, **주황 팁** |
| `d08_top_deck_gnss_csm_radar.jpg` (982²) | 상면 근접 | 상판 방열 그릴, GNSS 안테나 2개 위치, 상부 원통 모듈 |

### c — 부품 단품 (3장)

| 파일 | 무엇 | 비고 |
|---|---|---|
| `c01_prop_2110s_pair.png` | **2110s 프로펠러 1쌍**(CW+CCW), 접힌 상태 | 2枚翼(2-blade). 주황 팁. 접이식 |
| `c02_tb65_battery.png` | **TB65 인텔리전트 플라이트 배터리** 단품 | 측면 방열 리브가 그대로 외부 표면 |
| `c03_csm_radar_module.png` | 상부 장착 원통 모듈 = **DJI CSM Radar**(옵션 액세서리) | ⚠ **기본 기체 구성이 아니다.** 메쉬에 넣지 말 것. `d08`·`p05` 에 장착 모습이 보임 |

### p — 실사진 (21장)

#### p01–p04 : DJI 마케팅 현장 촬영

| 파일 | 상황 |
|---|---|
| `p01_flight_field_4k.jpg` (3840×2160) | 야외 비행, 측하방. 최고 해상도 실사진 |
| `p02_flight_fog_side.jpg` | 안개 속 측면 실루엣 — **윤곽선 추출에 좋다** |
| `p03_flight_fog_top34.jpg` | 상방 3/4, 회전 중 프롭 디스크 |
| `p04_flight_substation_gear_down.jpg` | 변전소, 다리 내림 — 다리 전개 자세 |

#### p05–p13 : ⭐ FCC 외부 사진 (실기체 + **강철 자가 프레임 안에 있음**)

전부 FCC 출원 `SS3-M3502301` 첨부 "External Photographs". **자(ruler)가 같이 찍혀 있어
픽셀→mm 스케일을 세울 수 있다.** 이 폴더에서 치수 실측이 가능한 유일한 실사진 묶음이다.

| 파일 | 자세 | 무엇을 잴 수 있나 |
|---|---|---|
| `p05_folded_top_ruler.png` | ⭐ **접힌 상태**, 상면, 자 포함 | 접힘 포장 치수(430×420 대조), 접힌 암이 동체에 붙는 각, 프롭 스토우 방향 |
| `p06_folded_top_props_stowed_ruler.png` | **접힌 상태**, 상면, 프롭 완전 접음, 자 포함 | 접힌 프롭 길이, 동체 상판 평면도 |
| `p07_folded_side_ruler.png` | **접힌 상태**, 측면, 자 포함 | 접힘 높이, 다리 접힘, 암 적층 순서 |
| `p08_nose_sensor_array_closeup.png` | 노즈 정면 근접 | FPV 카메라 + 전방 비전 2안 + 적외선 ToF 배치·직경 |
| `p09_front_elevation_gear_deployed.png` | 정면, 다리 전개 | 다리 벌림폭, 지상고, 동체 폭 |
| `p10_front_view_with_batteries.png` | 정면, 배터리 장착 | 배터리가 만드는 정면 투영 면적 |
| `p11_rear_view_dual_battery.png` | 후면, TB65 2개 | 후면 투영 실루엣(평면 2개 = 강한 후방 반사면) |
| `p12_rear_heat_vents_serial.png` | 후면 상부 근접 | 방열 슬릿 형상, 상면 센서 2안, 일련번호 라벨 |
| `p13_usbc_ports_closeup.png` | USB-C 포트 근접 | 포트 개구부(작은 산란 구조) |

> ⚠ `p05`~`p07` 의 기체에는 **상부 모듈과 흰색 보호캡 4개**가 붙어 있다.
> 시험용 구성이므로 표준 형상으로 착각하지 말 것.

#### p14–p15 : FCC 외부 사진 잔여분 (2026-08-03 추가)

| 파일 | 자세 | 무엇을 잴 수 있나 |
|---|---|---|
| `p14_rear_top_vision_ir_vents_closeup.png` | 후상부 근접(실기체) | 후방 비전 2안 + 적외선 ToF 2개 + GNSS 마운트 + 방열 슬릿 피치 |
| `p15_gimbal_connector_usbc_underside.png` | 하면 짐벌 커넥터 근접 | DGC2.0 커넥터 개구부·핀 배치 |

#### p16–p21 : DJI 공식 마케팅 실사진, 각도 보강 (2026-08-03 추가)

초판에 없던 **측면 정투영·정면 비행·상방 아이소**를 채우려고 제품 페이지 CDN 107개를
전수 내려받아 중복 13개를 걸러낸 뒤 고른 것들이다.

| 파일 | 촬영각 | 쓸모 |
|---|---|---|
| `p16_side_elevation_on_case_gear_down.jpg` (770×462) | ⭐ **좌측면 정투영에 가까움**, 지상, 다리 전개, 짐벌 장착 | 이 폴더에서 가장 측면다운 컷 — 측면 실루엣·다리 높이·짐벌 돌출 |
| `p17_front_elevation_flight_dusk.jpg` (770×462) | 정면, 비행 중 | 정면 실루엣, 프롭 회전 디스크 폭 |
| `p18_front_left34_flight_payload.jpg` (770×462) | 전방 좌 3/4, 페이로드 장착 | 페이로드가 붙은 형상 |
| `p19_left_side_flight_gimbal.jpg` (770×462) | 좌측면, 비행 중 | 비행 자세(피치)에서의 측면 |
| `p20_iso_from_above_solar.jpg` (770×462) | 상방 아이소 | 위에서 본 암 배치 |
| `p21_front_right34_sky.jpg` (2400×1200) | 전방 우 3/4, 고해상 | 우측 3/4 (좌우 대칭 확인용) |

> ⚠ CDN 수집분 중 **DJI 농업용 기체(Agras)** 컷 2장이 섞여 있었다 — M350 이 아니므로 버렸다.
> 조종기(RC Plus)·Zenmuse 짐벌 단품·운반 케이스 컷도 기체 형상과 무관해 버렸다.

### t — ⭐⭐ 분해(teardown) 26장 — 전부 자 포함

출처: 같은 FCC 출원의 "Internal Photographs"(43쪽). **DJI 가 인증기관에 제출한 공식 분해
사진**이라 iFixit 이나 유튜브 캡처보다 신뢰도·해상도가 낫고, **거의 모든 컷에 금속 자가
같이 찍혀 있어 각 부품의 실치수를 직접 읽을 수 있다.**

| 파일 | 무엇이 보이나 | RCS 관점 |
|---|---|---|
| `t01_airframe_shell_removed_iso_ruler.png` | ⭐ **상부 셸을 벗긴 기체 전체**, 아이소, 자 | 내부 골격·전장품이 동체 어디에 얼마나 차는지 |
| `t02_airframe_shell_removed_top_ruler.png` | ⭐ 같은 상태 상면, 자 | 메인 보드 스택의 평면 배치·면적 |
| `t03_body_bay_thermal_pads.png` | 동체 베이 내부, 분홍 열패드 | 금속 히트싱크 면 위치 |
| `t04_nose_bay_inside_vision_mount.png` | 노즈 내부, 비전 모듈 마운트 | 전방 센서 개구부 뒤의 금속 |
| `t05_mainboard_shielded_ruler.png` | ⭐ **메인 보드**(대형), 실드캔·열패드, 자 | 동체 중앙의 큰 금속 평면 — 주 산란원 후보 |
| `t06_all_modules_layout.png` | ⭐ **모든 내부 모듈을 한 판에 늘어놓은 컷** | 내부 금속 총량 감 잡기 |
| `t07_power_board_side_a_ruler.png` | 전원/배전 보드 A 면, 자 | 대면적 구리, 대형 인덕터·커패시터 |
| `t08_power_board_side_b_ruler.png` | 같은 보드 B 면, 자 | 〃 |
| `t09_large_board_ruler.png` | 대형 보드(비행제어/영상), 자 | 〃 |
| `t10_copper_shield_board_ruler.png` | **구리 실드 전면 도포** 보드, 자 | 사실상 금속 평판 — 강반사 |
| `t11_adsb_antenna_flex_ruler.png` | ADS-B 수신 안테나(플렉스 PCB, `PM430 ADS-B ZTX`), 자 | 얇은 평면 도체 |
| `t12_sdr_patch_antenna.png` | O3 Enterprise SDR 패치 안테나(동축 리드) | 2T4R 전송 안테나 4개 중 하나 |
| `t13_sdr_patch_antenna_labelled.png` | 같은 계열, 부품번호 `PM431 LS.DZ.AA000182_03` 판독 가능 | 〃 |
| `t14_front_vision_auxlight_module.png` | 전방 비전 + 보조등 모듈 조립체, 자 | 렌즈·LED 개구부 |

#### t15–t26 : 2차 수집분 (2026-08-03 추가) — 같은 FCC 출원, 전부 자 포함

초판은 43쪽 중 14장만 골랐다. 2차에서 **86장을 전수 추출**해 기존 보유분과 상관계수로
중복을 걸러낸 뒤, 금속 면적이 크거나 RF 에 직결되는 12장을 더 넣었다.

| 파일 | 무엇이 보이나 | RCS 관점 |
|---|---|---|
| `t15_large_board_copper_film_ruler.png` | 대형 보드, 구리박 + 검은 절연 필름 | 큰 도체 평면 |
| `t16_copper_plane_board_side_a_ruler.png` | ⭐ **구리 전면 도포 보드**(t10 과 다른 개체·다른 면) | 사실상 금속 평판 |
| `t17_compute_board_component_side_ruler.png` | ⭐ 대형 연산 보드 부품면(대형 SoC 다이 2개 보임) | 동체 중앙 금속 스택 |
| `t18_compute_board_shield_frame_ruler.png` | 같은 보드 반대면, 실드 프레임 | 〃 |
| `t19_sdr_ant0_3_feed_board_ruler.png` | ⭐ **ANT0–ANT3 표기 안테나 급전 보드**(4포트) | O3 2T4R 급전점 위치 |
| `t20_rf_module_side_a_ruler.png` | ⭐ **RF 모듈**(원문 캡션 'RF module') A 면 | 송수신 회로 실물 크기 |
| `t21_rf_module_side_b_ruler.png` | 같은 RF 모듈 B 면 | 〃 |
| `t22_metal_can_shielded_module_ruler.png` | 전면 금속 캔 실드 모듈 | 닫힌 금속 상자 = 강반사체 |
| `t23_vision_pair_on_bracket_ruler.png` | 비전 카메라 2안 + 금속 브래킷 조립체 | 센서 개구부 뒤 금속 |
| `t24_auxlight_led_board_ruler.png` | 보조등 LED 보드(대형 LED 2 + 중앙 1) | 하면 개구부 |
| `t25_front_vision_auxlight_assembly_ruler.png` | 전방 비전 + 보조등 **조립 상태** 광폭 컷 | 노즈 내부 배치 |
| `t26_adsb_ant0_3_board_in_situ_coax.png` | ⭐ ANT0–ANT3 라벨 보드가 **기체에 장착된 상태** + 동축 리드 | 안테나 실제 장착 위치·배선 |

### m — 도면·문서 (7장)

| 파일 | 무엇 | 출처 |
|---|---|---|
| `m01_qsg_aircraft_callouts_three_views.png` | ⭐⭐ **아이소 도해 + Bottom / Rear / Top 3면 정투영 + 18개 부품 콜아웃(영문)** — 이 폴더의 **형상 기준판** | Quick Start Guide p.2 (300 dpi 렌더) |
| `m02_qsg_unfold_and_landinggear_sequence.png` | ⭐ **접힘→펼침 절차도**(전방 암 → 후방 암 → 잠금 → 프롭 전개) + 랜딩기어 장착 + 짐벌 장착 | Quick Start Guide p.5 |
| `m03_maint_vision_system_top_bottom_views.png` | 적외선/비전 시스템·보조등·비콘의 **Top View / Bottom View 라인아트** | Maintenance Manual p.13 |
| `m04_maint_aircraft_structure_arms_gear.png` | 기체 구조 점검표 — 외관·나사·**랜딩기어 베이스·프레임 암·암 LED** 도해 | Maintenance Manual p.11 |
| `m05_maint_propulsion_motor_arm.png` | 추진계 — **모터 회전·모터↔암 연결부·모터 상부 커버·모터 에어필터·프로펠러·프롭 어댑터** 도해 | Maintenance Manual p.9 |
| `m06_maint_battery_bay_ports_vents.png` | **배터리 컴파트먼트·데이터 포트·방열구**(상/하면 도해) | Maintenance Manual p.12 |
| `m07_nameplate_label_fccid.png` | ⭐ **명판 원본** — 변종 확정 근거(§0) | FCC `SS3-M3502301` / ID Label and Location |

> ⚠ **DJI 는 M350 RTK 의 치수 기입 3면도(dimensioned drawing)를 공표하지 않는다.**
> `m01` 의 3면도에는 **치수선이 없다.** 스케일은 공표 수치(대각 축거 895 mm,
> 펼침 810×670×430 mm)로 외부에서 넣어야 한다. 치수가 실제로 들어간 근거는
> `p05`~`p07`·`t*` 의 **자(ruler)** 뿐이다.

---

## 3. 출처 URL 전체

### DJI 공식

- 제품/제원 페이지: <https://enterprise.dji.com/matrice-350-rtk> · <https://enterprise.dji.com/matrice-350-rtk/specs>
- 다운로드 센터: <https://www.dji.com/downloads/products/matrice-350-rtk>
- 사용자 매뉴얼 v1.2 (2025-03-26, 129쪽, 부록에 전체 제원):
  <https://dl.djicdn.com/downloads/matrice_350_rtk/20250326UM/Matrice_350_RTK_User_Manual_v1.2_kr3.pdf>
- Quick Start Guide (75쪽, 다국어. `m01`·`m02` 의 원본):
  <https://dl.djicdn.com/downloads/matrice_350_rtk/Matrice_350_RTK_Quick_Start_Guide_I.pdf>
- Maintenance Manual v1.0 (2025-08-13, 22쪽. `m03`~`m06` 의 원본):
  <https://dl.djicdn.com/downloads/matrice_350_rtk/202508MM/Matrice_350_RTK_Maintenance_Manual_v1.0_en08.pdf>
- In the Box: <https://dl.djicdn.com/downloads/matrice_350_rtk/Matrice_350_RTK_In_the_Box_I.pdf>
- 렌더/사진 CDN 원본: `https://www-cdn.djiits.com/dps/<32자hex>.{jpg,png}` (제품 페이지 HTML 에서 추출)

### FCC 공개기록 — FCC ID `SS3-M3502301`

- 출원 색인: <https://fcc.report/FCC-ID/SS3-M3502301> · <https://fccid.io/SS3-M3502301>
- Internal Photos (43쪽): <https://fccid.io/SS3-M3502301/Internal-Photos/x-6525819.pdf>
- External Photos (6쪽): <https://fccid.io/SS3-M3502301/Internal-Photos/x-6525818.pdf>
- ID Label and Location: <https://fccid.io/SS3-M3502301/Internal-Photos/x-6526103.pdf>
- (참고) M300 RTK 대조군: <https://fccid.io/SS3-M3001910>

### 2차 출처 (부품 치수 — DJI 미공표분)

- 2110 프로펠러 지름/피치/무게: <https://www.terrestrialimaging.com/products/dji-2110-propeller-pair-for-matrice-300-and-matrice-350>
- M350 vs M300 차이: <https://advexure.com/blogs/news/dji-matrice-350-rtk-vs-dji-matrice-300-rtk-a-detailed-comparison> ·
  <https://www.ferntech.co.nz/blog/news-case-studies/dji-matrice-350-rtk-vs-dji-300-rtk>
- 부품 판매(형상 참고): <https://cloudcitydrones.com/collections/dji-matrice-series-parts>

---

## 4. 라이선스 · 취급

| 묶음 | 권리 | 이 저장소에서의 취급 |
|---|---|---|
| `d*`, `c*`, `p01`–`p04` | © SZ DJI Technology Co., Ltd. 마케팅 저작물 | **내부 연구 참조용만.** 리포트에 실을 때는 출처 표기 필수, 재배포 금지 |
| `m01`–`m06` | © DJI. 공개 배포되는 사용자 문서에서 렌더 | 〃 (인용 범위로만) |
| `p05`–`p13`, `t01`–`t14`, `m07` | **FCC 공개기록.** DJI 가 제출하고 비밀유지 청구 없이(또는 단기 비밀유지 만료 후) 공개된 첨부물 | 공개기록이므로 참조 가능. 그래도 출처(FCC ID) 를 반드시 같이 적는다 |

⚠ 어느 것도 **CC 라이선스가 아니다.** 논문/발표에 넣을 때는 인용 표기를 하고,
가능하면 **우리가 만든 메쉬 렌더로 대체**하라.

---

## 5. 알려진 구멍 (다음 사람이 채울 것)

1. **치수 기입 3면도가 없다.** DJI 미공표 — 2026-08-03 재확인. 사용자 매뉴얼 v1.2 는 p.111 부록에
   숫자(`810×670×430`, `430×420×430`, 대각 축거 `895 mm`)만 주고 도면은 주지 않는다.
   Quick Start Guide p.2 의 3면 정투영에는 치수선이 없다.
   PSDK(Payload SDK) 개발자 문서의 짐벌 인터페이스 기구 도면은 아직 안 뒤졌다.
2. **CAD/STEP 없음.** `x500v2` 처럼 제조사 CAD 로 치수를 확정하는 길이 M350 에는 없다.
   (DJI 는 산업용 기체 CAD 를 공개하지 않는다.)
3. **모터 단품·암 튜브 단품 사진이 여전히 없다.** 2026-08-03 재시도 결과
   `cloudcitydrones.com` 은 상품 페이지·Shopify JSON·컬렉션 JSON 모두 **`404`** 를 돌려준다
   (검색엔진 색인만 남은 상태로 보인다). 다른 부품몰(volatusdrones, huitean)은 아직 안 뒤졌다.
   FCC 내부 사진 86장에도 **모터·암 튜브 단품 컷은 없다** — 전자 모듈 위주다.
4. ~~프로펠러 지름 교차검증 미실시~~ → **2026-08-03 실시, 확증 실패.**
   `p05`/`p06` 하단 자의 cm 숫자로 스케일을 세웠다(12.9~13.1 px/cm, 눈금 간격 편차 3%).
   - 접힘 외곽 치수 실측 **449 × 457 mm** vs 공표 430 × 420 mm → **+5~9%**.
     기체가 자보다 카메라에 가까운 것으로 설명되며 모순은 없다. 이 사진의 스케일 신뢰도가
     5~9% 라는 뜻이기도 하다.
   - 프롭 1매 허브–팁 실측 **295~345 mm** vs 소매점 지름 533 mm 의 반지름 266 mm → **+11~30%**.
     ⚠ 접힌 상태에서 앞·뒤 프롭 날이 겹쳐 허브와 팁의 대응을 눈으로 확정할 수 없다.
     **533 mm 는 SECONDARY 로 유지한다.** 확정하려면 프롭 단품 + 자 사진이나 DJI 도면이 필요하다.
     (전 과정 기록: `outputs/m350rtk_specs.json` 의 `photo_scale_crosscheck`)
5. `c03` 의 원통 모듈을 **CSM Radar 로 본 것은 정황 판정**이다(상부 장착·원통형·M300/M350
   액세서리 목록에 존재). DJI 제품 페이지의 i18n 키가 해석되지 않아 캡션으로 확정하지 못했다.
6. **초판 표의 해상도 기재 3건이 틀렸었다**(`d01`·`d02`·`d04`). 2026-08-03 실제 픽셀로 고쳤다.
   같은 종류의 오류가 더 있을 수 있으니, 수치를 인용하기 전에 파일을 직접 열어 볼 것.
