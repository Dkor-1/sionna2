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
| `1345_prop_cw.stl` | **Holybro 1345 프로펠러** (13.45인치 실물) | [PX4/PX4-gazebo-models](https://github.com/PX4/PX4-gazebo-models) `models/x500_base` | BSD-3-Clause |
| `5010Bell.dae` | **5010 아웃러너 모터 벨** (실물) | 같은 저장소 | BSD-3-Clause |
| `NXP-HGD-CF.dae` | **Holybro X500 카본 프레임** (실물) | 같은 저장소 | BSD-3-Clause |

**단위**: STL 은 mm 단위(Gazebo SDF 가 `<scale>0.001</scale>` 로 m 변환).
→ Typhoon H480 실제 크기 **455 × 520 × 158 mm**, 1345 프롭 **346 mm** 스팬.

**이 파일들은 비교·검증 전용입니다.** 우리 표적 모델(DJI 5종)은 여전히
`src/drone_cad.py` 가 **DJI 공식 스펙시트에서** 생성합니다.
