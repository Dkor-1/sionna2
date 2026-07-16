# PX4 / Gazebo 드론 모델 조사 — "우리 드론을 바로 올릴 수 있나?"

*2026-07-14 조사. 결론부터: **Mavic 4 Pro·Matrice 4E 는 어디에도 없다**(2025년 신형이라 너무 새롭다).
DJI 소비자/엔터프라이즈 기체는 애초에 **PX4 가 아니라 DJI 자체 비행스택**을 쓰므로 공식 PX4 airframe 이 없다.
그래서 우리 `src/gazebo_export.py` (스펙 → SDF 자동생성)가 **이 빈틈을 메운다.***

---

## 1. 공식 PX4 / Gazebo airframe (SITL 에서 **날릴 수 있는** 것)

| 모델 | 실물 | 형식 | 비고 |
|---|---|---|---|
| **x500** | Holybro X500 | 쿼드 | 신형 Gazebo(gz-sim) 표준. 우리가 프롭·모터·프레임 CAD 를 이미 비교에 씀 |
| **typhoon_h480** | **Yuneec Typhoon H480** | **헥사(상용 카메라 드론)** | ★ 실제 상용 카메라 드론 중 PX4 지원 최근접. **우리가 실물 CAD 비교 기준으로 이미 사용** |
| iris | 제네릭 | 쿼드 | 연구 표준 |
| solo | 3DR Solo | 쿼드 | gazebo-classic |
| **DJI F450** | **DJI Flame Wheel F450** | 쿼드(DIY 프레임) | DJI 가 판 **DIY 프레임** — PX4 지원. 소비자 완제품 아님 |
| standard_vtol / tailsitter / plane | — | VTOL/고정익 | 우리와 무관 |

→ **DJI Mavic / Matrice / Phantom 완제품은 공식 PX4 에 없다.** (출처: [PX4-SITL_gazebo-classic](https://github.com/PX4/PX4-SITL_gazebo-classic), [PX4-gazebo-models](https://github.com/PX4/PX4-gazebo-models), [PX4 Gazebo 문서](https://docs.px4.io/main/en/sim_gazebo_gz/))

## 2. 커뮤니티 DJI 모델 (있긴 하나 **PX4 SITL 이 아니라 DJI SDK HITL 용**, 그리고 구형)

| 저장소 | 기종 | 성격 |
|---|---|---|
| [TareqAlqutami/dji_ros_simulator](https://github.com/TareqAlqutami/dji_ros_simulator) | DJI **M100·M600** | ROS/Gazebo HITL (DJI Onboard SDK) |
| [caochao39/hku_m100_gazebo](https://github.com/caochao39/hku_m100_gazebo) | DJI **Matrice 100** | ROS/Gazebo |
| [dji-m100-ros/dji_m100_gazebo](https://github.com/dji-m100-ros/dji_m100_gazebo) | DJI **M100** | ROS Melodic |
| [TIERS/tello-ros2-gazebo](https://github.com/TIERS/tello-ros2-gazebo) | DJI **Tello** | ROS2 (초소형) |
| (researchgate) Phantom 4 realistic sim | DJI **Phantom 4** | ROS/Gazebo + 짐벌 |

→ 전부 **구형**(M100/M600/Phantom4/Tello)이고, **PX4 가 아니라 DJI 자체 SDK 시뮬**이다.
  **Mavic 4 Pro·Matrice 4E(2025 신형)는 하나도 없다.**

## 3. 그래서 우리 `gazebo_export.py` 가 채우는 빈틈

우리 5종(mini5pro·mavic4pro·matrice4e·s1000plus·phantom4)을 **스펙시트 → SDF** 로 자동 생성:
- base_link(동체) + rotor 링크 + revolute 관절 + gz-sim MulticopterMotorModel 플러그인
- **관성텐서를 메쉬에서 계산**(부위별 밀도 → trimesh → 평행축, 총질량은 공식 TOW 로 스케일)
- 충돌메쉬(볼록껍질), 추력계수 k_T 호버조건 유도 → `outputs/gazebo/<key>/model.sdf`

이게 **Mavic 4 Pro·Matrice 4E 로는 세상에 없는 모델**을 만든다.

## 4. ⚠ 판단: 그런데 우리 목적(패시브 드론 **디텍션**)에 PX4/Gazebo 비행시뮬이 **필요한가?**

**핵심 구분**: 레이더가 보는 것은 드론의 **전파 신호(RCS·마이크로도플러)** 이고, 그건 **Sionna RT + SBR**
가 담당한다(이미 있다). PX4/Gazebo 가 줄 수 있는 건 **현실적인 비행 궤적**(호버·웨이포인트·회피기동)이다.

| 목적 | 담당 | PX4/Gazebo 필요? |
|---|---|---|
| 드론의 레이더 반사(RCS) | Sionna RT + SBR | ❌ (이미 함) |
| 회전 블레이드 마이크로도플러 | pose_articulated + SBR | ❌ (이미 함) |
| **현실적 비행 궤적**(표적 운동) | PX4/Gazebo SITL | 🟡 **선택** — 있으면 궤적이 현실적, 없어도 직선/원 궤적으로 충분 |

→ **권고**: 디텍션 벤치마크에는 **직선/저속 궤적이면 충분**하다(문헌도 대부분 그렇다). PX4/Gazebo 비행시뮬은
  "현실적 궤적으로 마이크로도플러/추적을 보이고 싶을 때"의 **선택 확장**이다. `gazebo_export.py` 가
  그 문을 열어두되(SDF 생성 완료), **디텍션에 집중하는 현 단계에선 우선순위 낮음**.

*단, 날려서 궤적을 뽑으려면 SDF 만으론 부족하고 PX4 airframe 등록(질량·관성·k_T 매칭 — 우리가 계산한 값)이
 추가로 필요하다. 지금은 거기까지 안 간다.*
