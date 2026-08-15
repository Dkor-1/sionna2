# 리포트 편성 — 본편 11권 + 별편 8편 (파일 23)

이 문서는 `reports/` 아래가 **왜 이런 모양인가**와 **어떻게 다시 만드나**를 적는다.
사람이 읽는 목차는 [`reports/README.md`](../reports/README.md) 이고, 기계용 색인은
[`outputs/volumes_index.json`](../outputs/volumes_index.json) 이다. 이 편성으로 오는
옛→새 번호 환산의 정본은 [`RESTRUCT_PLAN.md`](RESTRUCT_PLAN.md) §1 표다.

---

## 1. 지금의 모양

```
reports/
  README.md                      ← 목차 (생성물)
  01_map.ipynb                   ← 본편. 한 권 = 한 파일
  01_2_prior-work.ipynb          ← 별편. 부모번호_K 꼴 (리포트 1-2)
  02_kernel.ipynb
  02_2_stock-engine.ipynb
  02_3_target-mesh.ipynb
  …
  06_1_scene.ipynb … 06_5_bistatic.ipynb   ← 6 권만 다섯 편 **분권** (아래 §5)
  06_6_microdoppler-limits.ipynb           ← 표기만 분권 꼬리, 지위는 **별편**
  …
  11_measurement.ipynb
  _parts/                        ← ⛔ 사람이 읽는 문서가 **아니다**
    NN_slug.ipynb                   (조각 층 — 번호는 권 번호와 무관, 87 편 배치)
```

세 지위가 있고, 파일은 합쳐서 **23개**다 (본편 11권 = 파일 15 + 별편 8편).

| 지위 | 무엇 | 파일명 | 산문 표기 |
|---|---|---|---|
| **본편** (11권) | 전개방향의 독립 서사 박자 하나 | `NN_slug.ipynb` | «리포트 N» |
| **별편** (8편) | 부모 권의 질문에 대한 답 — 심화·지원·변주 | `NN_K_slug.ipynb` (K≥2) | «리포트 N-K» |
| **분권** (6권의 5파일) | 그림 무게 때문에 나눈 **한 권의 장** | `06_1`~`06_5` | «리포트 6 (K편)» |
| 조각 | 주제 하나짜리 재료. 숫자는 원장 JSON 주입 | `_parts/NN_slug.ipynb` | (사람이 안 읽음) |

⭐**분권 ≠ 별편.** `06_1~06_5` 는 base64 그림이 무거워 나눈 한 권의 장이고(나누는 축은
물음, 무게는 사정), `N_K` 류 별편은 «이 권의 결론이 부모 권의 질문에 대한 답인가» 를 통과한
권이다. `06_6` 은 분권 `_1~_5` 와의 번호 충돌을 피해 꼬리만 `_6` 을 쓸 뿐 지위는 별편이다.
**별편의 별편은 없다** — 이 번호 문법은 `build_volumes.py` 의 import 시 assert 가 강제한다
(`_` 든 번호는 전부 COMPANIONS 에 1회 등재 · 접두=부모 키 · 부모 키에 `_` 없음 · 합계 8).

## 2. 편성표

서사 8박자 = 장면(01) → 커널(02) → 검증(03) → 앙각(04) → 스위치(05) → 마이크로도플러(06)
→ 디텍션(07~10) → 실측(11). 디텍션 막만 본편 4권 — 메인 태스크라 박자를 뭉개지 않는다.

| 본편 | 박자 | 딸린 별편 (부모 질문 → 답) |
|---|---|---|
| 01 map | 장면 | 01_2 prior-work — 01 §2 네-관문 판정의 전수 근거 |
| 02 kernel | 커널 | 02_2 stock-engine — 왜 이 커널인가의 대면 · 02_3 target-mesh — 무엇 위에서 적분하나(입력 QC) |
| 03 anchor | 검증 | 03_2 size-law — 절대 크기가 아니라 각도 구조라는 답 |
| 04 elevation-coverage | 앙각 | (04_2 예약 슬롯 — 15 m 재설계판, 미건축) |
| 05 engine-physics | 물리 스위치 | 05_2 switch-grid — 단일축 귀속을 7조합 전수 격자로 완결 |
| 06_1~06_5 (분권) | 마이크로도플러 | 06_6 microdoppler-limits — 무엇이 무늬를 흐리나(06_3 과 쌍대) |
| 07 illuminators | 디텍션·조명원 | — (뒤 본편 두 권이 소비하는 자원 선언이라 본편) |
| 08 detector | 디텍션·사슬 | 08_2 two_channel — 사슬 그대로, 기준신호만 현실화 |
| 09 observability | 디텍션·기하 | — (10 의 전제라 본편) |
| 10 results | 디텍션·결과 | 10_2 robustness — 결론이 무엇에 기대나(감도분석) |
| 11 measurement | 실측 | — |

## 3. 누가 만드나 — 두 층 + 외부 빌더

| 층 | 무엇 | 누가 만드나 | 사람이 읽나 |
|---|---|---|---|
| **조각** `reports/_parts/NN_slug.ipynb` | 주제 하나짜리 짧은 편. 숫자는 전부 원장 JSON 에서 주입 | `src/build_partNN_*.py` **14개** | ❌ 재료다 |
| **권** `reports/NN[_K]_slug.ipynb` | 물음 하나에 답하는 문서. 조각을 절로 품는다 | `src/build_volumes.py` (+외부 빌더 4개) | ✅ 이것을 읽는다 |

`build_volumes.py` 안의 편성 데이터는 셋이다.

| 데이터 | 내용 |
|---|---|
| `VOLUMES` | 조각을 조립하는 16권 — 본편 10 (01·02·03·04·05·07·08·09·10·11) + **조립 별편 6** (01_2·02_2·02_3·03_2·06_6·10_2) |
| `EXTERNAL` | 6 권 분권 5파일 — 다른 빌더가 만들고, 여기서는 주소 후처리만 |
| `COMPANIONS` | 별편 8편의 {부모: [별편…]} 등재 — 조립 별편 6은 VOLUMES 포인터, 외부 별편 2(05_2·08_2)는 빌더 명시 |

외부 빌더 4개 (⭐스크립트 이름의 숫자는 **역사 층**이라 개명하지 않는다 — 산출물 번호가 정본):

| 빌더 | 산출 |
|---|---|
| `src/make_report08_microdoppler.py` | `06_1_scene` ~ `06_4_sampling` |
| `src/make_report07b_bistatic.py` | `06_5_bistatic` |
| `src/make_report11_2_two_channel.py` | `08_2_two_channel` (별편 8-2) |
| `src/build_report18_switch_grid.py` | `05_2_switch-grid` (별편 5-2) |

⭐ **분량 상한은 두지 않는다.** 옛 셀 수 상한(`report_style.MAX_MD_CELLS`)은 폐지됐고(`None`),
새 상한도 만들지 않는다. 권의 길이는 그 권이 답하는 물음의 크기가 정한다.

## 4. 묶는 층이 하는 일

`build_volumes.py` 가 조각을 이을 때 손대는 것은 이것뿐이다.

| 무엇을 | 왜 |
|---|---|
| **각주 재번호** | 조각마다 `[^1]` 부터 다시 센다. 이을 때 앞까지의 최대 번호만큼 밀어 정의와 인용을 함께 옮긴다 |
| **상호참조 재배선** | 조각 본문의 «편 NN» 주소를 배치표에서 찾아 권 주소로 고친다 (아래 규칙) |
| **머리말** | 부모 권 머리에는 딸린 별편 안내를, 별편 머리에는 «이 편은 리포트 P 의 **별편**이다» 부모 선언을 쓴다 |
| **지도 권 생성** | 1 권의 절 1(열한 권의 지도·환산표·읽기 경로)은 조각이 아니라 이 스크립트가 짓는다 |
| **6 권 후처리** | 외부 빌더가 낸 분권 주소를 고치고, 옛 부 7 조각(34~39)을 `06_3_pattern.ipynb` 뒤에 절로 덧붙인다 |
| **색인·목차** | `outputs/volumes_index.json` 과 `reports/README.md`. 색인 권 항목에 `kind`("trunk"/"companion")·`parent`·`no_disp` |

### 재배선 규칙

| 조각이 들고 있던 옛 주소 | 바뀌는 모양 |
|---|---|
| `[편 22 «…»](22_po-knee.ipynb)` — 다른 편을 가리킴 | `[리포트 2 절 N «…»](02_kernel.ipynb)` |
| `[편 22 «…»](22_po-knee.ipynb)` — 같은 편 안 | `**절 N** «…»` (자기 파일로 되돌아가는 링크를 안 만든다) |
| `` `reports/37_md-rpm.ipynb` `` (인라인 코드) | `[리포트 6 절 4](06_3_pattern.ipynb)` |

⚠ **권 파일 이름도 `NN_slug` 꼴이고 조각 번호는 권 번호와 무관하다.** 번호만 보고 고치면
이미 새 주소로 적힌 글을 옛 주소로 오인해 망가뜨린다. 그래서 `_is_part_name()` 이 **슬러그까지
조각 파일명과 대조**해서 실제로 조각을 가리킬 때만 고친다. 별편 파일명(`01_2_prior-work`)은
이 정규식에 걸리지 않는다(두 자리 머리 필수 + 슬러그 문자클래스에 `_` 없음).

⭐ 6 권에 덧붙인 셀에는 `metadata.tags = ["from_parts"]` 표식이 붙는다. 다시 돌리면 그 표식이
붙은 셀을 먼저 걷어내고 새로 붙이므로, 몇 번을 돌려도 겹쳐 쌓이지 않는다.

## 5. 6 권만 다섯 편(분권)인 이유

한 권이 한 파일인 것이 규칙인데 6 권만 예외다. 마이크로도플러는 애니메이션과 스펙트로그램이
노트북 안에 그림으로 박혀 있어(base64) 한 파일에 담으면 **열리지 않는다.**
나누는 축은 분량이 아니라 물음이라, 다섯 편이 각각 하나씩 답한다.

| 편 | 무엇에 답하나 |
|---|---|
| `06_1_scene` | 무엇을 보고 있나 — 시나리오와 신호의 정체 |
| `06_2_engines` | 어떻게 계산하나 — 세 엔진과 거리 |
| `06_3_pattern` | 무엇이 무늬를 정하나 — 회전수·가림·산포 |
| `06_4_sampling` | 무엇을 잴 수 있나 — 광선 비용과 반복률 |
| `06_5_bistatic` | 송신·수신이 갈라지면 — 바이스태틱 기하 |

별편 `06_6_microdoppler-limits`(무엇이 무늬를 **흐리나**)는 이 다섯과 지위가 다르다 — §1.

## 6. ⭐규약 — 조각을 손으로 고치지 마라, 빌더를 고쳐라

이 편성이 서 있는 조건은 하나다. **본문의 숫자가 원장 JSON 에서 온다는 사슬이 안 끊기는 것.**

| 고치고 싶은 것 | 고칠 곳 | 안 되는 곳 |
|---|---|---|
| 절의 본문·숫자·각주 | 그 조각을 만든 `src/build_partNN_*.py` | ⛔ `reports/_parts/*.ipynb` · ⛔ `reports/*.ipynb` |
| 권 구성·순서·제목·논지·별편 배속 | `src/build_volumes.py` 의 `VOLUMES`·`COMPANIONS` | ⛔ 권 노트북 |
| 6 권 분권·별편 8-2·5-2 의 본문 | 위 §3 외부 빌더 4개 | ⛔ 해당 `reports/*.ipynb` |
| 목차·색인 | `src/build_volumes.py` (루트 README 는 `src/make_readme.py`) | ⛔ `reports/README.md` · ⛔ `outputs/volumes_index.json` |

조각이나 권을 손으로 고치면 **다음 빌드에서 조용히 사라진다.** 사라지지 않더라도 더 나쁘다 —
본문 숫자와 원장이 갈라져도 아무도 모른다.

## 7. 다시 만드는 절차

순서가 중요하다. ③ 이 ② 의 산출물 뒤에 절을 덧붙이기 때문이다.

```bash
# ① 조각 빌더 14 개  → reports/_parts/NN_slug.ipynb
PYTHONPATH=src python src/build_part00_map.py
#  … build_part01_stock_engine.py … build_part13_engine_physics.py

# ② 외부 빌더 4 개    → 06_1~06_4 / 06_5 / 08_2 / 05_2
PYTHONPATH=src python src/make_report08_microdoppler.py
PYTHONPATH=src python src/make_report07b_bistatic.py
PYTHONPATH=src python src/make_report11_2_two_channel.py
PYTHONPATH=src python src/build_report18_switch_grid.py

# ③ 조각 → 권         → 본편 10 + 조립 별편 6 + 6 권 후처리 + 색인 + reports/README.md
PYTHONPATH=src python src/build_volumes.py

# ④ 루트 README
PYTHONPATH=src python src/make_readme.py

# ⑤ 검사
PYTHONPATH=src python benchmark/check_report_links.py
```

②가 아직 없으면 ③ 은 후처리를 **조용히 건너뛰고 경고만** 찍는다 — 빌드가 죽지 않는다.

## 8. 검사에서 무엇을 보나

`benchmark/check_report_links.py` 가 끊긴 링크·그림·출처를 센다. 편성 자체의 불변량은
색인 `_meta` 로 본다.

| 봐야 하는 것 | 어디서 / 기대값 |
|---|---|
| 편성 불변량 | `_meta`: n_volumes=**11**(본편) · n_companions=**8** · n_notebooks=**23** · n_parts_placed=**87** |
| 파일 수 | `ls reports/*.ipynb \| wc -l` = **23** |
| 권의 지위·부모 | `volumes[].kind`("trunk"/"companion")·`parent`·`no_disp` |
| 권마다 셀·각주·그림 수 | `volumes[].cells/footnotes/figures` |
| 어느 조각이 어느 권 몇 절인가 | `parts` (또는 1 권 절 1 의 환산표) |
| 권에 안 들어간 조각과 그 사유 | `superseded_parts` (조각 00 superseded·조각 81 미건축은 현행 유지) |
| 각주가 권 안에서 유일한가 | 정의(`[^n]:` · 출처 표 행)와 인용을 세어 중복·미정의·미인용이 0 인지 |
