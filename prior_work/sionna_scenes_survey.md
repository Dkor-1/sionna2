# 공개된 Sionna «환경 씬»이 있는가 — 조사 결과

조사일 2026-08-12 · 질문: *"선행 연구들이나 오픈소스? 깃허브 등에서 시오나 환경 mesh 제작해둔 것들 있는지 찾아봐줄래?"*
대상은 **무대**(건물·거리·지면 같은 전파 환경)이지 우리 표적(드론)이 아니다.
조사 조건: GPU 미사용 · git 미사용 · 대용량 내려받기 없음(목록·메타데이터·텍스트 파일만).

---

## 한 문단 답

**있다. 그러나 «Sionna 씬 은행» 같은 것은 없다.** 실제로 씬 파일을 통째로 주는 곳은 넷뿐이고
(Sionna 내장 15개 · USC 캠퍼스 · BostonTwin · WiSegRT 실내), 나머지는 전부 **«씬 만드는 기계»**다.
이 바닥의 표준은 «남의 씬을 받아 쓰는 것»이 아니라 **«OSM 좌표를 넣고 그때그때 굽는 것»**이고,
그 도구가 MIT 라이선스로 여러 개 공개돼 있다(SceneBaker·OpenGERT·sionna_osm_scene).
우리에게 쓸모 있는 것은 **완성 씬이 아니라 생성기**다 — 공개 캠퍼스 씬은 전부 남의 부지이기 때문이다.
그리고 걱정하신 격자 문제는 **사실이지만 방향이 다르다**. 공개 씬 삼각형은 우리 드론 메쉬보다
450~8,800배 크지만(내가 직접 측정), 이건 무대로서는 **결함이 아니다** — 광선 근사는 면이 파장보다
훨씬 커야 성립하기 때문이고, 우리는 이미 σ를 자체 SBR+PO 커널로 내고 Sionna에는 환경만 맡긴다.
공개 씬의 **진짜** 결함은 격자가 아니라 다른 데 있다 — 지면이 «완전 평면 + 콘크리트»이고,
나무·가로등·전선 같은 파장급 클러터가 **0개**다. 하필 그 둘이 우리 바닥유령·클러터 서사의 심장이다.

---

## 1. 표 — 무엇이 실제로 있나

### (A) 완성된 씬 파일을 주는 것

| 무엇 | 어디 | 라이선스 | 규모 | 우리 용도 | 확인 |
|---|---|---|---|---|---|
| **Sionna 2.0.1 내장 15 씬** | 로컬 `site-packages/sionna/rt/scenes/` · github.com/NVlabs/sionna-rt | 코드 **Apache-2.0**. ⭐도시 4종(etoile·munich·florence·san_francisco)의 **데이터는 ODbL** | 355,838 tri / shape 10,345 / 실내용 13.6 MB (`du` 50 MB는 블록 패딩) | **도시 통제군 무대로만.** 우리 부지 아님 | ✅ XML·PLY 직접 파싱 |
| **USC 캠퍼스** (PMNet 부속) | github.com/abman23/pmnet-sionna-rt `Data/USC_3D/` | **MIT** (© 2024 Juhyung Lee) | XML 39.8 KB + PLY 165개 (건물 82동 × 재질슬롯2 + 바닥1) | 무대 후보. 2.0.1에서 **한 줄 패치 필요** | ✅ LICENSE·XML·PLY 확인 |
| **BostonTwin** | github.com/wineslab/boston_twin · 데이터 hdl 2047/D20623157 | 코드 **MIT** (© 2024 WiNES Lab) / ⛔**데이터 라이선스 미확인** (저장소 403) | 논문 Table 1: 31 타일 · 83,086 모델 · 6.18 M tri (타일 1개 = 1524 m 정사각) | **보류** — 라이선스 확인 전엔 안 씀 | ◐ 코드·LICENSE 확인, 데이터 미확인 |
| **WiSegRT 실내 6 씬** | github.com/SunLab-UGA/WiSegRT | 코드 **MIT** / ⛔**씬 자산 라이선스 미확인** (개인 OneDrive 736 MB) | 씬 6개 (아파트·사무실) | 실내라 우리 야외에 직결 안 됨 | ◐ 코드 확인, 자산 미확인 |
| SceneBaker 동봉 캠퍼스 4벌 | github.com/hslyu/sionna-scene-baker `data/` | 코드 MIT / 지오는 **OSM → ODbL** | POSTECH·SNU·UNIST·UT Austin, 전부 **Git LFS** | 예제일 뿐 — 우리 부지 아님 | ✅ `.gitattributes`·LFS 포인터 확인 |
| NYCU 캠퍼스 + UAV | github.com/vivian921207/sionna-uav-blender | ⛔**라이선스 없음** | XML 9 · PLY 146 · .blend 13 | ⛔**못 씀** (무라이선스 = 저작권 기본값) | ✅ 트리에 LICENSE 없음 |

### (B) 씬을 «굽는» 생성기 — 우리에게 진짜 쓸모 있는 쪽

| 무엇 | 어디 | 라이선스 | 규모/성격 | 우리 용도 | 확인 |
|---|---|---|---|---|---|
| ⭐**SceneBaker** | github.com/hslyu/sionna-scene-baker · arXiv 2608.04546 | **MIT** (© 2026 Hyeonsu Lyu) — 코드만 | 순수 파이썬. **Blender 불필요**. 지형(SRTM ~30 m) 포함. bbox 4개만 주면 XML+PLY | ⭐**부지 굽기 1순위 후보** | ✅ LICENSE·소스 직접 확인 |
| **OpenGERT** | github.com/serhatadik/OpenGERT | **MIT** (코드) + 의존 Blosm은 **GPL** | OSM + MS 건물 풋프린트 + (미국)USGS DEM → Blender → XML. 지오메트리 섭동 민감도 포함 | **추출기 반쪽만.** 민감도 절반은 우리 스택에서 안 돎 | ✅ LICENSE·`setup.py` 핀 확인 |
| **sionna_osm_scene** | github.com/manoj-kumar-joshi/sionna_osm_scene | **MIT** | 노트북 2개, **씬 0개**. 2024-01-11 하루 커밋 후 정지 | **레시피 참고만** — 지금 실행 불가 | ✅ 파일 7개 전수 |
| **gazebo-sionna-pipeline** | github.com/Teleinfrastructure-Research-Lab/gazebo-sionna-pipeline | **MIT** (© 2026) | Gazebo SDF 월드 → Mitsuba/Sionna XML. 동적 객체 처리 | ⭐PX4/Gazebo와 기하 공유 — 관심 | ✅ LICENSE 확인 |
| ⛔**Geo2SigMap** | github.com/functions-lab/geo2sigmap · arXiv 2312.14303 | ⛔**CC BY-NC 4.0** (`package/LICENSE` 원문 확인) | OSM + USGS LiDAR/DEM → 씬 + U-Net. LTE 실측 대조(RMSE 6.04 dB) | **코드 흡수 금지.** 패턴만 참고 | ✅ LICENSE 원문 |
| Blender 사슬 | mitsuba-blender · vvoovv/blosm | **BSD-3** / **GPL** | NVIDIA가 내장 도시 씬을 만든 바로 그 경로 | 대안 경로 | ✅ Sionna 공식 문서 명시 |

> **NVIDIA 공식 Blender 애드온은 없다.** Sionna 문서가 가리키는 것은 위 제3자 애드온 두 개다.

### (C) 이름만 씬이고 자산이 없는 것 (열어서 확인함)

| 저장소 | 라이선스 | 실제 내용 |
|---|---|---|
| NVlabs/diff-rt | NVIDIA License | 노트북 2개 |
| SimART | 없음 | ROS/AirSim 코드, 메쉬 0 |
| SEAM | Apache-2.0 | glb 3개 + **64 B 빈 XML** |
| SkySense-ISAC | MIT | obj 1 + 노트북 |
| Digital-Twin-Dataset | Apache-2.0 | py 4개 |
| SIONNA-Scene-Builder | 없음 | py 15개 |
| SionnaRTStudio | Apache-2.0 | 브라우저 GUI, 즉석 생성만 |

---

## 2. ⭐무대와 표적 — 이 답의 뼈대

**내가 직접 잰 값** (3.5 GHz, λ = 8.566 cm. XML이 참조하는 PLY 전수 파싱, 표본 아님):

| | 삼각형 변 중앙값 | 면적가중 | λ보다 작은 변 |
|---|---|---|---|
| simple_street_canyon | 31.12 m = **363 λ** | 552 λ | 0.00 % |
| etoile | 13.85 m = **162 λ** | 410 λ | 0.04 % |
| florence | 11.43 m = **134 λ** | 302 λ | 0.23 % |
| munich | 7.52 m = **88 λ** | 502 λ | 1.96 % |
| san_francisco | 3.92 m = **46 λ** | 116 λ | 0.01 % |
| — | | | |
| 우리 드론 mini5pro | 3.55 mm = **0.042 λ** | | 99.97 % |
| 우리 드론 s1000plus | 8.68 mm = **0.101 λ** | | 99.00 % |

**격자비 450배 ~ 8,800배** (면적가중이면 1,100배 ~ 13,300배).

이 숫자가 말하는 것은 둘이다.

**(1) 무대로는 정상이다.** 광선추적(기하광학)은 면이 파장보다 훨씬 커야 맞는 근사다.
건물 벽은 실제로 큰 평판이니 삼각형이 수십~수백 λ인 게 옳다. 성긴 게 흠이 아니다.
평면 정반사체는 애초에 삼각형 수와 무관하다 — simple_reflector는 1×1 m 평판을 삼각형 **2개**로
표현하는데 PO 적분이 해석적이라 그걸로 «정확»하다.

**(2) 표적으로는 절대 못 쓴다.** 그리고 이건 «다시 잘게 쪼개면 되지» 로 해결되지 않는다.
munich 표면적 4.08 e6 m²를 λ/10로 재메쉬하면 **1.1 e11 삼각형**(현재의 290만 배)이고,
정점만 f32로 잡아도 ~0.7 TB다. 24 GB 카드를 4~5자릿수 초과한다.
물리가 막는 게 아니라 메모리가 막는다.

> ⚠단 이 계산이 증명하는 것은 «환경 **전체**를 못 쪼갠다»뿐이고, 유일성이 아니다.
> 표적 바로 아래 정반사 패치만 국소로 λ/10로 까는 것은 100 m²에 270만 삼각형이라 가볍고,
> 실제로 살아남는 대안이다. 우리가 «환경은 성기게, σ는 자체 커널»을 고른 근거는
> «유일해서»가 아니라 «전역 고해상은 배제되고, 국소 패치는 사이트 전체의 일반해가 아니며,
> 애초에 표적 자체의 σ를 대신해 주지 않아서»다.

**우리 구조에서는 이 문제가 이미 풀려 있다.** 소스를 읽어 확인했다 —
`sbr_field(mesh, group_mat, fc, u, …)`의 **인자에 무대가 없다**. 광선을 쏘는 씬은 표적 메쉬 하나로
만들어지고, 광선 격자(d = λ/12 = 7.14 mm)도 그 메쉬의 bounding box만 보고 정해진다.
무대 삼각형은 PO 커널에 들어올 길이 없다. 둘을 잇는 것은 σ 주입이고,
`src/report14_scene.py`가 이미 «환경만 RT로 짓는다»는 규약으로 스톡 실외 씬을 로드하고 있다.

**⚠그 대가**: 이 분리는 «표적 경유 바닥 유령»(Tx → 바닥 → 표적 → Rx)을 공짜로 주지 않는다.
표적이 무대 씬에 없으니 PathSolver가 못 만들고, 무대가 SBR 커널에 없으니 PO도 못 만든다.
그 항은 손으로 배선해야 한다. 무대를 붙이는 일의 진짜 비용은 씬 확보가 아니라 여기다.

---

## 3. 못 쓰는 것과 그 이유 — 우리가 직접 만들어야 하는 근거

내장 씬을 실제로 열어 보고 확인한 것들이다. 전부 «격자» 문제가 아니라는 점이 중요하다.

1. **야외 개활지 씬이 하나도 없다.** 현실 씬 6개가 전부 조밀 도심이다. 우리 실증은 야외 필드테스트다.
2. **지면이 «완전 평면 + 콘크리트»다.** munich 1475×1206 m를 삼각형 **2개**로 덮고 재질은 ITU concrete.
   etoile·florence·simple_street_canyon도 같다. 진짜 지형이 있는 것은 san_francisco 하나뿐이다
   (Terrain.ply, 192,000 삼각형, 표고 0~104 m).
   ⭐하필 우리 report09 «바닥 유령»의 진폭을 정하는 게 지면 반사계수다. 완벽한 거울 + 콘크리트를
   그대로 쓰면 우리 헤드라인(5G 100 % 오검출)이 부풀려진다.
3. **Sionna에 지면 재질 3종(very_dry/medium_dry/wet_ground, 1–10 GHz)이 있는데 쓰는 씬이 하나도 없다.**
   아스팔트·초목은 ITU 목록에 아예 없어서 우리가 직접 만들어야 하고, 그러려면 출처 문헌이 필요하다(현재 없음).
4. **파장급 클러터가 0개다.** munich·florence·etoile·san_francisco의 shape 이름을 전수 검색한 결과
   나무·가로등·기둥·울타리·전선 **0건**. 차량이 있는 씬은 simple_street_canyon_with_cars 하나뿐이고
   그 차량도 21 λ다. 따라서 «클러터 통계가 현실적»이라는 주장은 이 씬들로 절대 못 한다.
5. **파사드가 자리표시자다.** munich 메쉬 2367개 중 1152개가 marble(벽) + 1144개가 metal(지붕)이다.
   실측 근거로 고른 재질이 아니다.
6. **NYCU UAV 씬은 라이선스가 없어서 못 쓴다.** 내용상 «Sionna 씬 + UAV»에 가장 가까워서 가장 아깝다.
7. **Geo2SigMap은 CC BY-NC라 코드를 흡수하면 안 된다.** 지형(DEM)을 넣는 몇 안 되는 파이프라인이고
   실측 대조까지 한 좋은 물건이지만, 비상업 조항이 우리 저장소로 번질 소지가 있다.
8. **AODT는 OpenUSD라 Sionna가 못 읽는다** (`scene.py:915` "Only triangle meshes are supported").
9. **Mitsuba 3 갤러리 씬(실내 32개)은 BSDF가 광학 재질이라 로드가 거부된다** — 전 재질 재지정 필요.

---

## 4. 그대로 / 손봐서 / 직접

**그대로 쓸 수 있는 것 (사실상 없음)**
- 내장 15 씬은 «도시 통제군 무대»로만 그대로 쓸 수 있다. ODbL 출처표기 조건.
  우리 사이트 트윈으로도, 클러터 비교용으로도 그대로는 못 쓴다.

**손봐서 쓸 것**
- **USC 캠퍼스 (MIT)** — Sionna 0.x 내보내기라 `mat-itu_concrete.002` 가 있다. 2.0.1의 하위호환 변환이
  `itu_type="concrete.002"` 로 해석해 ITU 표에 없어서 실패한다.
  ⚠**«.002를 떼는» 수정은 실패한다** — bsdf id가 중복돼 Mitsuba가 `duplicate ID` 로 죽는다(재현 확인).
  옳은 수정은 id는 그대로 두고 `<string name="type" value="concrete"/>` 한 줄을 넣는 것이다.
- **SceneBaker (MIT)** — 우리 부지 bbox로 구우면 된다. 단 아래 조건이 붙는다.

**직접 만들 것 (우리가 이미 할 수 있음)**
- `src/scene_build.py:138 ground_part()` 가 이미 크기·높이·재질이 전부 인자인 바닥판을 만든다.
  스톡 `floor.ply`(309 B, 186×121 m 고정, concrete 하드코딩)보다 **우리 것이 낫다**.
- `src/geom.py` 에 box/quad/cylinder/uv_sphere가 있고, `src/chamber.py` 는 225줄로 31×21 m 무대를
  세운 실적이 있다. Sionna 씬 XML은 2 KB짜리 한 장이라 손으로 써도 된다.
- 부족한 것은 여섯이고 그중 다섯이 싸다 — 야외 재질 키 / 지형 높이맵 / 건물 압출기 / XML 라이터 /
  규모 검사 / ⭐**좌표 원점 규약**(위경도→ENU, RTK GT와 같은 계). 마지막 것이 현재 막혀 있다
  (`docs/MEASUREMENT_PLAN.md` Q1 — 레인지 부지가 아직 안 정해졌다).

---

## 5. ⚠SceneBaker를 쓸 때 알아야 할 것 (원문 확인)

우리가 가장 유력하게 보는 도구라 별도로 적는다.

- **라이선스는 코드만 MIT다.** 산출물은 OSM 파생이라 **ODbL**(표시 + 동일조건)이 따라붙는다.
  지형은 SRTM(퍼블릭 도메인)이라 무관.
- ⭐**논문과 코드가 다르다.** 논문은 "GPT-5.5 API가 OSM 요소를 해석해 재질 배정" + "RAG로 건물 높이 보강"
  이라 쓰는데, **배포 코드에는 둘 다 없다** — `src/materials.py` 는 7항목 하드코딩 딕셔너리이고
  `requirements.txt` 에 openai가 없다. 우리에겐 오히려 이득(결정론적)이지만,
  논문 헤드라인 "agentic semantic scene setup"을 받은 것으로 **인용하면 안 된다**.
- ⭐**지형 모드의 편차가 우리 마진과 같은 급이다.** 논문의 Blender 기준선 대조에서
  평지는 path-gain 중앙값 0.276 dB로 좋지만 **지형은 중앙값 4.25 dB, 최악 13.95 dB**다.
  우리 디텍션 헤드라인이 G1 15.0 dB / G3 11.1 dB니까, **무대 생성 도구 선택만으로 우리 결론 폭만큼
  움직인다**. 지형 모드를 dB 주장 밑에 깔려면 자체 민감도 검사가 선행이어야 한다.
  (두 파이프라인 사이의 «불일치»이지 «오차»가 아니다 — 어느 쪽도 실측 기준이 아니다.)
- **식생이 0.5 m 카펫이다.** 나무가 수관이 아니라 바닥 슬래브다. 드론이 20~100 m로 날면 나무 가림이
  아예 안 잡힌다. `--vegetation-height` 로 올릴 수 있으나 우리가 손봐야 하는 항목이다.
- **재질 미보정** — 저자도 한계로 명시("uncalibrated material parameters").
- **바닥유령과 상충** — 지형이 SRTM ≈30 m → 삼각형 14.7 m ≈ 172 λ. 논문 한계에
  "SRTM cannot represent small local ground discontinuities" 라 적혀 있다. 부지의 국소 평탄도·노면
  재질은 이 도구가 못 준다.
- **성숙도** — 별 3개, 커밋 29개, 2026-05 시작. 채택하면 우리가 첫 검증자가 된다.
- 좋은 점 — Blender 기준선 XML을 **같이 배포**하고, `bounds/height/occupied` 질의 API가
  순수 numpy라 GPU 없이 돈다. 그리고 XML을 `<scene version="3.0.0">` + `itu-radio-material` 로
  직접 뱉어서 Sionna 2.x 네이티브다(USC 같은 하위호환 손질 불필요).

---

## 6. 미확인 — «모른다»고 적는 것들

- **DeepMIMO v4가 3D 기하(Mitsuba XML/메쉬)를 배포하는지** — deepmimo.net 시나리오 페이지 확인 실패.
  기하를 준다면 최대 공급원이 될 수 있어 다음 라운드 1순위.
- **BostonTwin 데이터 라이선스** — 노스이스턴 저장소·bostonplans.org 둘 다 403. 상류 Analyze Boston의
  3D 빌딩 레이어는 PDDL로 표시돼 있으나 **같은 배포물인지 확인 안 됨**.
- **WiSegRT 씬 자산 라이선스** — MIT는 코드 저장소만 덮고, 정작 씬은 개인 OneDrive 736 MB에 있으며
  라이선스 문구가 어디에도 없다. 가구·텍스처의 제3자 출처도 미명시.
- **한국 공개 3D 도시모델**(V-World·국토지리정보원·국가공간정보포털)이 일본 PLATEAU(CC BY 4.0로
  Sionna에 실제 투입된 사례 있음)에 대응하는 형태로 있는지 — **이번 조사 범위 밖**.
  우리 실증이 국내면 여기가 무대 문제의 진짜 해법일 수 있다.
- **어떤 씬도 Sionna 2.0.1로 실제 로드해 보지 않았다** — GPU 금지 라운드였다. 호환성 판정은 전부
  XML 스키마와 소스 코드 독해에 근거한 추론이다(재질 해석 경로는 CPU로 정적 재현한 것까지 있음).
- **무향실/RCS 검증용 공개 Sionna 씬** — 찾지 못했다. «없다»가 아니라 «찾지 못했다».
- 이 조사는 NVIDIA 공식 «Made with Sionna» 목록 + GitHub API 검색 + topic:sionna 30개 전수를 훑었다.
  **목록에 없는 개인 저장소는 놓쳤을 수 있다.**

---

## 7. ⭐그래서 무엇을 할까 (상류부터)

1. **원점부터 막혔다** — 실증 부지가 안 정해져 있다(`docs/MEASUREMENT_PLAN.md` Q1). 위경도→ENU 원점을
   RTK GT와 같은 계로 선언하는 것이 모든 무대 작업의 상류다. 이게 정해지기 전엔 어떤 씬도 못 굽는다.
2. **부지가 뭐로 정해지든 안 버려지는 반나절 작업을 먼저 한다** — `src/materials.py` 에 야외 재질 키
   (medium_dry_ground·아스팔트·초목) 추가 + `src/geom.py` 에 «발자국 → 압출» 함수 추가.
3. **SceneBaker를 우리 부지 bbox로 실제로 구워 Sionna 2.0.1로 열어 본다** — 지금은 스키마 대조까지만
   했다. 평지 모드부터 쓰고, 지형 모드는 자체 민감도 검사(4.25 dB 편차)를 통과한 뒤에 쓴다.
4. **내장 도시 씬은 «도시 통제군»으로만 남긴다** — 우리 사이트 트윈이 아니고, 지면 재질과 클러터 부재
   때문에 클러터 비교에도 못 쓴다. 논문·발표 그림에 쓰면 OSM contributors / ODbL 출처를 밝힌다.
5. **진짜 부채는 씬이 아니라 결합항이다** — «표적 경유 바닥 유령»은 두 엔진 어디에도 없어 손으로
   배선해야 한다. 무대를 붙이는 일정은 «씬 확보»가 아니라 이 배선 + σ의 바이스태틱화로 잡아야 한다.

---

## 부록 — 이 문서의 측정 방법과 신뢰 경계

- **격자 수치는 내가 직접 쟀다.** 각 씬의 Mitsuba XML을 파싱해 «참조된» PLY만 전수 로드하고,
  자체 이진 PLY 리더로 정점·면을 읽어 변 길이·면적을 계산했다. 표본이 아니라 전수다.
  스크립트: `/tmp/claude-1015/-home-yunjung-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/mygrid.py`
- ⚠**병렬 조사에서 munich 중앙값이 0.354 m(4.1 λ)로 나온 판이 있는데, 그건 «파일 200개 무작위 표본»
  방식 때문이다.** munich는 메쉬 파일이 2367개인데 크기 편차가 커서, 파일 단위 균등 표본은 작은
  디테일 메쉬 쪽으로 치우친다. **전수로는 7.52 m(87.8 λ)** 이고 이 문서는 전수 값을 쓴다.
- **드론 메쉬 통계에서 `studio_ground.obj`(4×4 m 렌더 배경판, 삼각형 2개)는 제외했다.** 이걸 포함하면
  최댓값이 오염된다(과거 계측 판에서 실제로 그랬다).
- **라이선스는 원문 파일을 직접 읽은 것만 «확인»으로 적었다.**
  Geo2SigMap은 루트 LICENSE가 404라 «충돌»로 보고된 적이 있는데, 실제 파일은 `package/LICENSE` 에
  있고 CC BY-NC 4.0이다. 루트 배지의 "Apache_2.0"은 존재하지 않는 파일을 가리키는 낡은 배지다.
- ⚠**원장 사고 보고**: 형제 에이전트가 `outputs/survey_sionna_builtin_scenes.json` 을 쓸 때 같은 경로의
  기존 파일을 덮어썼다(2026-08-12 05:45 UTC, 백업 없음, 이전 내용 불명). 그 JSON 자신의
  `_meta.provenance_warning` 에 기록돼 있다. 이 문서의 수치는 내가 독립 재측정했으므로 영향받지
  않지만, 그 경로는 «오염된 경로»로 취급하는 것이 맞다.
- 관련 원장: `outputs/survey_sionna_builtin_scenes.json` · `outputs/survey_scene_build_paths.json` ·
  `outputs/survey_sionna_scenes_github.json` · `outputs/survey_sionna_scenes_papers.json` ·
  `docs/SCENE_BUILD_OPTIONS.md` · `docs/PRIOR_WORK_COMPARISON.md`
