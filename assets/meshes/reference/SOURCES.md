# 참조용 **실물 3D CAD** — 출처와 라이선스

우리 파라메트릭 메쉬(`src/drone_cad.py`)가 **실물과 얼마나 다른가**를 정량화하기 위해 받아온
**실제 상용/오픈소스 드론의 3D 모델**입니다. 전부 **공개 저장소 + 허용적 라이선스**입니다.

⚠️ **DJI 는 공식 CAD 를 공개하지 않습니다.** 인터넷의 DJI 3D 모델들은
  · 시각용(껍데기만 — 내부 금속 산란체 없음)
  · 치수 검증 안 됨
  · 라이선스 제약
이라 RCS 에 쓸 수 없습니다. 그래서 **CAD 가 공개된 실물 드론**으로 우리 방법을 검증합니다.

| 파일 | 실물 | 출처 | 라이선스 |
|---|---|---|---|
| `main_body_remeshed_v3.stl` 외 | **Yuneec Typhoon H480** (실제 헥사콥터) — 동체·다리·프롭·CGO3 짐벌 | [ethz-asl/rotors_simulator](https://github.com/ethz-asl/rotors_simulator) `rotors_gazebo/models/typhoon_h480` | Apache-2.0 |
| `solo.stl`, `solo_prop_*.stl` | **3DR Solo** (실제 소비자용 쿼드) | 같은 저장소 `models/solo` | Apache-2.0 |
| `1345_prop_cw.stl` | **1345 프로펠러** (13×4.5 공칭, 실측 디스크 **346.7 mm = 13.65 in, 공칭 대비 +5.1%**) | [PX4/PX4-gazebo-models](https://github.com/PX4/PX4-gazebo-models) `models/x500_base` | BSD-3-Clause |

> ⚠ **이 프롭은 Holybro X500 V2 의 프롭이 아니다.** X500 V2 킷은 **1045**(10×4.5 in = 254 mm)를 싣는다
> (docs.holybro.com X500 V2 페이지: "1045 Propellers (6 pcs)"). 이 메쉬는 공칭 13 in 대비 +5.1% 크고,
> 소비하는 SDF 가 11/13 로 축소해 쓴다 → **블레이드 형상 참조 전용**이다.
> `prop_guard_jybhz.stl` 도 X500 부품이 아니라 **Typhoon 액세서리**(상류에서 주석처리됨)다.
| `5010Bell.dae` | **5010 아웃러너 모터 벨** (실물) | 같은 저장소 | BSD-3-Clause |
| `NXP-HGD-CF.dae` | ⚠ **Holybro X500 이 아니다** — NXP HoverGames 킷(KIT-HGDRONEK66)의 **ReadytoSky LJI X4 500** 프레임. PX4 가 `x500_base` 의 **시각용 대역**으로 재사용한다. | 같은 저장소 | BSD-3-Clause |

> ⚠ **2026-07-28 정정 — 이 DAE 를 "Holybro X500 실물" 로 부르던 것은 오식별이었다.**
> 결정적 증거: 파일 안에 **`FMUK66-mesh`**(47,424면) 서브메쉬가 있다 — NXP **RDDRONE-FMUK66**
> 비행제어보드이고, Holybro 킷은 이 부품을 **한 번도 실은 적이 없다**(Holybro 는 Pixhawk 계열).
> 치수도 어긋난다: 판 **148.0 mm**(X500 공표 144), 모터원 **493.32 mm**(공표 500),
> 판 간격 26.36 mm(공표 28). 게다가 순수 파라메트릭 CAD 다 — 암 길이 정확히 200.000 mm,
> 튜브 OD/ID 16.000/14.000, 벽 1.000, 판 2.000, 다리 벌림 19.99°. 전부 반올림 수 →
> 측정 잡음이 아니라 **다른 기체를 의도적으로 그린 것**이다.
> → **사촌급 레이아웃 참조**로만 쓸 것(판 스택·튜브 프레임·다리 위상·레일, 그리고 이 저장소에서
>   유일한 **진짜 재질별 분할**). BOM 참조도 아니고 동일기체 정답도 아니다.
>   휠베이스·판 크기·프롭·모터는 **공표값**으로 채점해야 편향이 없다.
> ⭐ 이 DAE 의 9개 부위는 재질명으로 갈라져 있다: `CarbonFiber` `Metal` `FMUK66`
>   `LandingFoam` `LandingRubber` `LandingPlastic` `RailsRubber` `RailsAntennaHolder` `FMURubber`.

## ⭐ 2026-07-30 추가 — Holybro **1차(제조사) CAD**

| 파일 | 실물 | 출처 | 라이선스 |
|---|---|---|---|
| `x500v2-frame.step` (24.6 MB) | **Holybro X500 V2 프레임 전체 어셈블리** — 부품 57종·인스턴스 244, STEP AP214, 원본 타임스탬프 2022-07-19 | Holybro 공식 다운로드 페이지 <https://docs.holybro.com/drone-development-kit/px4-development-kit-x500v2/download> | 제조사 배포물(재배포 조건 미표기) — **내부 참조용** |
| `AIR2216II_Motor_3D.STEP` (0.8 MB) | **Holybro AIR2216II 모터 단품** (SolidWorks 2022) | 같은 페이지 | 같음 |

> ⭐ **이것이 `x500v2` 형상의 1차 근거다.** 앞으로 X500 V2 치수는 사진 픽셀이 아니라
> 이 STEP 에서 읽는다. 측정기 `benchmark/measure_x500v2_cad.py` → `outputs/x500v2_cad.json`
> (51항목 전부 VERIFIED). 파서는 OCC 없이 STEP 어셈블리 변환을 합성한다.
>
> ⚠ **받는 법**(다시 필요할 때): GitBook 의 `docs.holybro.com/files/<id>` 경로는 소문자로
> 리다이렉트되며 **404** 다. 진짜 링크는 다운로드 **페이지 HTML 안에 서명된 URL**
> (`2367252986-files.gitbook.io/~/files/v0/…?alt=media&token=…`) 로 박혀 있다.
> 즉 "404 니까 CAD 는 못 구한다" 는 **틀린 결론**이었다.
>
> ✅ **이 CAD 는 `NXP-HGD-CF.dae` 오식별을 독립적으로 확증한다.** 진짜 X500 V2 는
> 판 **143.72 mm**(DAE 148.0) · 모터원 **502.8 mm**(DAE 493.32) · 판 간격 **28.00**(DAE 26.36) ·
> 암 튜브 OD **15.4**(DAE 16.000) 이다 — 세 수치 모두 DAE 와 다르다.
> 위 2026-07-28 정정을 되돌리지 말 것.
>
> ⚠ **BOM 상 차이 하나**: 이 CAD 의 모터는 `DJ-2216-KV880`, 전원모듈은 **PM06** 이다.
> 현재 판매 킷은 **2216 KV920 + PM02**(PX4 조립 가이드)라 **CAD 는 초기 구성**이다.
> 구조 치수(판·암·다리·레일)는 바뀐 흔적이 없지만, 전장품은 CAD 를 BOM 으로 믿지 말 것.

**단위**: STL 은 mm 단위(Gazebo SDF 가 `<scale>0.001</scale>` 로 m 변환).
→ ⚠ **정정**: 455 × 520 × 158 mm 는 `main_body_remeshed_v3.stl` 의 **bbox** 이지 기체 크기가 아니다.
  Yuneec 공표 기체 크기는 **520 × 457 × 310 mm**(폭 우선 표기 — CAD 가 520 이 좌우, 457 이 전후임을 확정).

**단위는 파일마다 다르다** — `src/mesh_compare.py` 의 `UNIT_SCALE` 이 유일한 권위이고 이미 옳다:
  · **mm**: Typhoon STL 9종 + `prop_guard_jybhz.stl`
  · **m**: `solo.stl` · `solo_prop_*.stl` · `1345_prop_cw.stl` · `5010Bell.dae` · `NXP-HGD-CF.dae`

**⚠ 2026-07-28 이후 이 문장은 더 이상 참이 아니다.** Yuneec Typhoon H(H480)과 Holybro X500 V2 는
**표적 모델로 승격**됐다 — 즉 이 CAD 들은 이제 **표적이자 동시에 자기 채점 기준**이다.
표적 메쉬 자체는 여전히 `src/drone_cad.py` 가 **공표 제원에서 파라메트릭으로** 생성한다
(다운로드 메쉬는 부위별 재질이 없어 RCS 엔진에 못 쓴다 — X500 DAE 만 예외적으로 재질 분할이 있다).
⚠ **라이선스 의무가 내부 점검이 아니라 배포되는 표적 모델에 붙는다**:
Typhoon H480 = Apache-2.0(ethz-asl/rotors_simulator), X500 참조 = BSD-3(PX4/PX4-gazebo-models).

---

## `matrice4-M4T_v2.step` — DJI Matrice 4 시리즈 공식 CAD (2026-08-03 추가)

- 원본: <https://dl.djicdn.com/downloads/DJI_Matrice_4_Series/M4T_v2.stp> (158 MB)
  DJI 다운로드 허브의 "3D Model v2" — <https://enterprise.dji.com/matrice-4-series/downloads>
- 어셈블리명 `M4T_ASM`, Creo Parametric 작성, 스키마 `CONFIG_CONTROL_DESIGN`, **단위 mm**
- ⚠ **M4T 판이다.** `M4E_v2.stp` · `M4E.stp` 는 403 으로 공개되지 않는다.
  **기체(airframe)는 M4E 와 공유**하고 **짐벌만 다르다** — 짐벌 형상에는 쓰지 말 것.
  (변종 판별 근거는 `../../photos/matrice4e/SOURCES.md` 참조)

**실측(gmsh/OCC 임포트, 메쉬 생성 없이 bbox)**: 솔리드 125개 · 면 19,465개

| 축 | CAD | DJI 공표(펼침) | 차이 |
|---|---|---|---|
| X(폭) | **387.51 mm** | **387.5 mm** | **+0.003 %** ⭐ |
| Y(높이) | 151.83 mm | 149.5 mm | +2.3 mm |
| Z(길이) | 331.07 mm | 307.0 mm | +24.1 mm |

폭이 공표값과 사실상 일치 → **양산 형상으로 신뢰할 수 있다.**
길이·높이 차이는 측정 기준 차이로 보이나 **아직 미검증**이다.

> ⚠ gmsh 표면 메쉬 생성은 **실패**한다 — `Impossible to mesh periodic surface 4456`.
> 임포트·치수 측정은 정상. 메쉬가 필요하면 솔리드 단위로 나눠 굽거나 다른 커널을 쓸 것.

**라이선스**: DJI 저작물. 사내 형상 대조·치수 근거용으로만 쓰고 재배포하지 말 것.
