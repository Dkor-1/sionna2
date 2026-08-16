# 메쉬 봉인 — 골든 스냅샷 · 게이트 배선 · 갱신 절차 (2026-08-16)

> **봉인자 라운드**의 산출물이다. 형상은 한 글자도 안 바꿨다 — 만든 것은 **검사·대조·봉인·인증서**뿐이다
> (⛔GPU 미사용 · ⛔git 미접촉 · ⛔형상 상수 무변경).
>
> - 코드: `benchmark/mesh_certify.py` (한 줄 진입점) · `benchmark/adv_mesh_certify_faults.py` (봉인기 적대 시험 21건)
> - 봉인: `outputs/mesh_golden_0816.json` (309 KB · 형상지문 `a5a71500c3283b12` · 2026-08-17 03:27 KST)

---

## 0. 한 줄

메쉬 인증은 이제 **명령 하나**로 다시 돈다.

```bash
cd /workspace/sionna
PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/mesh_certify.py          # 봉인 대조   9 초
PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/mesh_certify.py --full   # 전부 다시   295 초
```

봉인이 하는 일은 **«옳음» 이 아니라 «안 바뀜» 의 증명**이다. 옳음은 인증서 4종(위상·치수·대칭·배치)과
적대 대조 6스위트(184건)가 맡는다. 봉인은 그 인증서들이 **아직 이 메쉬에 대한 것인가**를 지킨다.

---

## 1. 골든이 지키는 것 — 아홉 축

| 축 | 무엇을 굳혔나 | 규모 | 바뀌면 |
|---|---|---|---|
| ① 형상 | 메쉬 지문 4종(전체·정점·삼각형·라벨) + **그룹별** 면수·부품수·경계모서리·비다양체·감김뒤집힘·면적·부호부피·상자·중심·해시 | 기체 10 · 그룹칸 88 | 🔴 |
| ② 치수 | `mesh_dimref` 의 잣대 **49종** 실측값[mm] | 490칸 | 🔴 |
| ③ 예산·잣대 | 검사기 7모듈의 예산표(값째로). 이름이 예산꼴이면 **자동으로** 딸려 들어간다 | 69개 | 🟠 완화 / 🟡 강화 |
| ④ 바깥 참값 | `mesh_dimref.REFS`(참값·등급·순환성·출처) | 77행 | 🟠 |
| ⑤ 형상 상수 | `drone_cad` 40 + `drones` 3 표(값째로) + 기체별 `DroneSpec` 전 필드 | 43표 | 🟠 |
| ⑥ 문(door) | 메쉬가 **파일로 나가는** 호출 전수 + 정본 자산을 **읽는** 자리 + 인메모리 소비자 census | 39 · 18(직접 8) · 144파일 410곳 | 🔴 새 문 |
| ⑦ 매트릭스 판정 | 인증 매트릭스 450칸의 **판정과 잰 값** — 검사기가 조용히 무뎌지면 여기서 걸린다 | 45검사 × 10기체 | 🔴 통과→실패 |
| ⑧ 인증서 | 인증서 6종 파일 해시 + 안에 박힌 기체별 지문. ⭐**지금 메쉬와 대조**까지 한다 | 6종 | 🔴 무효 / 🟡 변경 |
| ⑨ 코드 | 형상·검사·**적대 대조** 코드 20개 파일 지문 | 20 | 🟡 |
| ⑩ 디스크 자산 | `assets/meshes/drones/<key>/*.obj` ↔ 지금 빌더 출력 **바이트 대조** | 8기체 | 🟠 |

`🔴/🟠` 가 하나라도 있으면 나가는 값 **2**, `🟡` 만이면 **1**, 전부 같으면 **0**.

### «무엇이 얼마나» 를 말한다

봉인이 «다르다» 만 말하면 쓸모없다. 실제 출력(적대 시험 E1 — 프롭 지름을 2 % 흔들어 **다시 빌드**한 결과):

```
🔴 [형상] mini2 — 형상이 바뀌었다
     지문 08829834431f5c2f → 3f1c…   삼각형 25823 → 25823 (+0) · 정점 …
       그룹 prop: 면 9856→9856 · 면적 +4.04 % · x상자 -1.19/+1.19 mm
       치수 prop_dia: 119.100 → 121.482 mm (+2.382 mm, +2.00 %)
```

---

## 2. 게이트 배선 감사 — 문은 하나만 잠겨 있다

`mesh_certify.py --gates` 가 저장소를 AST 로 훑어 **메쉬가 파일로 나가는 자리**를 전수로 찾는다
(2026-08-16 실측 **39곳**).

| 부류 | 곳 | 게이트 | 뜻 |
|---|---|---|---|
| 정본 자산 | 1 | **있음** | `python src/drones.py` → `mesh_check.assert_ok()` 가 돌고, 실패하면 OBJ 가 안 나간다 |
| 장면 임시 | 2 | 없음 | `scene_build.drone_parts()` 가 `<key>/_scene/` 에 렌더·RT 용 OBJ 를 그때 새로 쓴다 |
| 실험 장면 임시 | 26 | 없음 | 실험 스크립트가 Sionna/Mitsuba 에 먹일 장면 OBJ 를 그때그때 쓴다 |
| 다른 빌더 | 4 | 없음 | ⭐Gazebo STL 은 `drone_cad.build_frame_cad` 산출물 — 저장소의 **어떤 메쉬 검사도 본 적이 없다** |
| 드론 아님 | 3 | — | 차폐시설 · 스튜디오 바닥판 |
| 문 자체 | 1 | — | `geom.Mesh.write_obj`(문의 몸통) |
| 비교 산출 | 2 | — | 실물 스캔 대조용 PLY |

### ⭐못 막는 것 — 인메모리 경로

RCS·SBR·마이크로도플러·렌더는 **파일을 안 쓴다.** `build_drone()` 을 불러 배열을 그대로 쓴다.
그런 파일이 지금 **144개(호출 410곳)** 다. 문이 아니므로 **어떤 게이트도 막을 수 없다.**
막으려면 import 시점에 검사를 걸어야 하는데 전 기종 검사가 ~35 초라 안 건다
(`src/drones.py` 의 게이트 주석이 선언한 것과 같은 이유).

→ 그래서 방벽은 배선이 아니라 **규율**이다: **라운드가 끝나면 `mesh_certify.py` 를 돌린다.**

### 들어오는 쪽도 본다 — 디스크 자산은 지금 낡았다

봉인은 나가는 문만이 아니라 **정본 OBJ 를 참조하는 자리**(18곳, 그중 «파일 직접 읽기» 8곳)도 센다.
2026-08-16 실측:

- 정본 OBJ 가 있는 기체는 **5대뿐**(mini5pro · mavic4pro · matrice4e · s1000plus · phantom4)이고
  전부 **2026-07-20 판**이라 지금 빌더 출력과 다르다(예: `mini5pro__body` 면 7608 ↔ 8028 ·
  `mini5pro__prop` 12192 ↔ 12752 · `mini5pro__gear` 는 아예 없음).
- phantom3 · typhoonh480 · x500v2 는 `_scene/` 만 있고 정본 파일이 없다. m350rtk · mini2 는 디렉터리 자체가 없다.
- ⚠ 다만 렌더·RT 경로(`render_rt` · `radar_scene` · `benchmark/channel`)는 자산 **디렉터리**만 넘기고
  `drone_parts()` 가 `_scene/` 에 **그때 새로 쓴다** — 그 경로가 쓰는 형상은 낡지 않았다.
  위험한 것은 `<key>__<group>.obj` 를 직접 읽는 자리다(`adv_multiref_planform_0816` ·
  `measure_prop_matrice4e_recheck_0816` — 전자는 이미 스스로 «mtime 2026-07-20» 이라고 적어 뒀다).
- 고치는 법: `PYTHONPATH=src python src/drones.py` (게이트가 여기서 돈다).

---

## 3. 한 줄 재현 — 단계와 실측 시간

```bash
PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --list          # 단계 목록
PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --full --jobs 6 # 전부(certs 제외)
PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --stage raw,fleet --jobs 8
PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --gates         # 문 감사만
PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --how           # 갱신 절차
```

| 단계 | 하는 일 | 실측(초) · 2026-08-16 · 192코어 공용기 · `--jobs 6` |
|---|---|---|
| `map` | 범주 지도 20칸 ↔ 매트릭스 45행 덮임 확인 | 0.05 |
| `raw` | 기체별 전 검사 원자료 10개(`mesh_cert_matrix_run_one`) | 126 |
| `fleet` | 함대 검사 + 위상·재질 봉인 대조(`mesh_cert_matrix_fleet`) | 121 |
| `controls` | 적대 대조 6스위트(184건) | 34 |
| `matrix` | 매트릭스 표 생성 — json·md 0.1 + html 약 5 | 5 |
| `golden` | 골든 봉인 대조(이 라운드) | 9 |
| `certs` | ⚠인증서 5종 재발급 — **형상이 바뀐 뒤에만**(기본 꺼짐) | 미측정 |

**합계 약 295 초**(html 포함). 봉인 대조만이면 **9초**, 봉인기 적대 시험은 **3초**.

재현성 확인 두 가지 — ⓐ 메쉬 지문은 독립된 빌드 4회에서 전부 같았다.
ⓑ `--full` 로 다시 찍은 매트릭스는 저장소의 정본과 **데이터 전 구획이 동일**했다
(matrix 450칸 · summary · seal · controls · checks · grade_matrix · failures — 시각만 다름).

---

## 4. 골든이 «바뀌어야 마땅한» 경우 — 갱신 절차

형상을 **의도적으로** 고쳤으면 골든이 달라지는 것이 정상이다. 그때는 이 순서를 따른다
(`mesh_certify.py --how` 가 같은 내용을 찍는다).

1. **왜 바뀌는지 한 줄로 적을 수 있어야 한다.** 못 적으면 그 변경은 사고다 — 먼저 원인을 찾는다.
2. 인증서 4종 재발급: `make_mesh_cert_topology_0816.py` · `mesh_cert_dimension_external_0816.py` ·
   `mesh_cert_placement_0816.py` · `mesh_cert_symmetry_derived_0816.py`
   (재질을 건드렸으면 `mesh_cert_material_provenance_0816.py` 도).
3. 적대 대조 6스위트를 다시 돌려 **여전히 잡히는지** 확인.
4. 매트릭스 재생성 — `mesh_certify.py --full` 한 줄이 2~4를 대신한다(certs 단계는 `--stage certs` 로 따로).
5. 정본 OBJ 재내보내기: `PYTHONPATH=src python src/drones.py` (게이트가 여기서 돈다).
6. 마지막에 재봉인:
   ```bash
   PYTHONPATH=src:benchmark python benchmark/mesh_certify.py --update --reason "짐벌 폭을 공식 CAD 로 정정(2층 수리)"
   ```
   **이유 없이는 갱신을 거부한다**(`--reason` 필수). 일부 기체만 돌린 결과(`--keys`)로도 거부한다.
7. 갱신본은 `history` 에 **이전 지문 · 이유 · 무엇이 바뀌었는지 목록**을 남기고,
   `last_update_diff_ko` 에 사람이 읽는 대조문을 통째로 싣는다. 골든 파일 하나만 열면
   «언제 무엇이 왜 바뀌었나» 를 따라갈 수 있다.

---

## 5. 봉인기 자신을 시험한다 — 적대 대조 21건

봉인이 «걸린다» 고 주장하려면 **일부러 흔들어 걸리는지** 보여야 한다.

```bash
PYTHONPATH=src:benchmark python benchmark/adv_mesh_certify_faults.py     # 3초 · 21/21 통과
```

- **양성 17건** — 형상(면 수 / 정점만 이동) · 치수 · 예산 완화 · 예산 강화 · 바깥 참값 · 형상 상수 ·
  새 문 · 판정 없는 문 · 디스크 자산 · 인증서 파일 · 코드 지문 · 인증서↔메쉬 불일치 · 자산 독자 ·
  매트릭스 판정 뒤집힘 · 매트릭스 값 이동 · ⭐**끝에서 끝까지**(스펙을 인메모리로 흔들어 **다시 빌드**).
- **음성 4건** — 안 바꾸면 조용한가 · 봉인 시각/이유만 바뀌면 · 이력만 늘면 · 지금 인증서가 유효한가.
- 흔드는 것은 전부 **인메모리 복제본**이다. 저장소의 골든·소스·형상 상수는 안 건드린다.

---

## 6. 못 하는 것 (봉인의 경계)

- 봉인은 «옳음» 이 아니라 «안 바뀜» 을 증명한다. **처음부터 틀린 형상은 골든이 틀린 채로 지켜 준다.**
- 게이트가 실제로 걸린 문은 `python src/drones.py` **하나**다. 나머지 문은 안 지난다.
- ⭐인메모리 경로(`build_drone` 직접 호출)는 문이 아니라 **막을 수 없다**. RCS·SBR·마이크로도플러·
  렌더가 전부 이 경로다.
- Gazebo STL 은 **다른 빌더**(`drone_cad.build_frame_cad`)에서 나와 저장소의 메쉬 검사가 한 번도 본 적이 없다.
- 치수 49종은 `mesh_dimref` 의 자다 — 그 자가 못 재는 부위(내부 배선·안테나 등)는 골든에도 없다.
- 형상 상수 봉인은 **표에 담긴 상수**만 본다. 함수 안에 숫자로 박힌 값은 파일 sha 로만 잡히고
  «어디가» 바뀌었는지는 못 말한다.
- 위상 인증서 지문(32자)은 봉인 대조에서 **다시 계산하지 않는다**(기체당 ~12초). 그 축은
  `--full` 의 `fleet` 단계(`mesh_topo_check.check_seal`)가 맡는다.
- 매트릭스 판정 축(⑦)은 **파일에 적힌 판정**을 굳힌 것이다. 판정이 지금도 맞는지는
  `--full` 로 다시 찍어야 안다.
- 골든은 **한 기계·한 파이썬**에서 재현된다는 전제다(같은 컨테이너 4회 재현 확인).
