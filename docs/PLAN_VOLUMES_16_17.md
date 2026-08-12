# 권 16·17 편성 계획 — 앙각 커버리지 · 엔진의 물리 스위치

작성 2026-08-12 · 이 문서는 **바닥 다지기**다. 조각(`reports/_parts/NN_slug.ipynb`)은 아직
짓지 않았고, 이 계획이 정하는 것은 **번호·앵커·절 제목·원장 키·소유권** 넷이다.

> ⛔ 이 라운드는 **새 계산을 하지 않는다.** 아래 원장은 전부 디스크에 있고, 그림 7 장도
> 이미 그려져 있다. 새 계산이 필요한 자리는 §7 «필요하다고만 적는다» 에 모았다.

---

## 1. 조각 빌더가 지켜야 할 것 (`src/report_style.py` 계약)

### 1-1. 어기면 **예외가 나는** 것 — 빌드가 멈춘다

| 규약 | 장치 | 정확한 조건 |
|---|---|---|
| 여는 블록 넷 | `header()` | `did` · `results` · `method` · `repro` 가 다 있어야 한다 |
| «한 일» 은 질문이 아니다 | `header(did=)` | 물음표가 **하나라도** 있으면 예외. `…다` 로 끝나는 **한 문장**. 부정 종결 금지 |
| «결과» | `header(results=)` | **3~5 줄**, 숫자가 최소 하나, 부정 종결 문장은 **1 개까지** |
| «방법» 이 범위를 말한다 | `header(method=)` | **2 줄 이상**. `[("무엇을","어떻게 얻었나"), …]` 또는 문자열 목록 |
| «재현» | `header(repro=)` | `dict(cmd=…, out=…, runtime=…)`. `out` 의 파일이 **디스크에 없으면 예외** |
| 숫자는 손으로 안 친다 | `num(값, 출처, fmt, unit)` | JSON 을 열어 **값을 대조**한다. 어긋나면 예외. `num(None, …)` 이 가장 안전 |
| `null` 은 숫자가 아니다 | `num(…, if_null="측정 불가")` | `null` 인데 `if_null` 이 없으면 예외 |
| 인용은 값 **하나** | `num()` | dict·list 를 통째로 인용하면 예외 → `키[0]` 으로 원소를 집거나 `table_from()` |
| 표 안의 숫자도 검증 | `table_from(source, columns, fmt=…)` | JSON 배열/딕셔너리에서 행을 직접 뽑는다. 표 하나에 출처 태그 하나 |
| 그림 1 개 = 질문 1 개 | `caption(n, "…?")` | 물음표로 **끝나야** 하고 물음표가 2 개면 예외 |
| 그림 글자는 영어 | `assert_fig_text()` | 한글이 있으면 예외 (본문·주석은 한국어) |
| 마지막은 «다음 단계» | `next_steps([(할 일, 결정되는 것, 어디서), …])` | 가운데 칸이 비면 예외. 할 일 칸이 부정문이면 예외 |
| 옛 계약 호출 | `header(question=…)` · `limits()` | 부르면 **무엇으로 바꿀지 적어서** 예외 |

### 1-2. `build_notebook(..., strict=True)` 가 **위반**으로 잡는 것

| 검사 | 상한 | 비고 |
|---|---|---|
| 셀 하나의 줄 수 | **12 줄** (빈 줄 제외) | `header`·`next_steps`·`paper`·`sources` 태그 셀은 면제 |
| 그림 수 | **8 장** | 캡션·마크다운 이미지·`savefig`·이미지 출력 중 **최대값**으로 센다 |
| 깨진 그림 링크 | **0** | PNG 가 노트북 기준·루트 기준·`reports/` 기준 셋 중 하나로 열려야 한다 |
| 부정문 | **3 개까지** | 「…않는다 / 못한다 / 아니다 / 없다」로 **끝나는** 문장 |
| 완충어 | **0 건** | 「볼 수 있다 · 대체로 · 어느 정도 · 다소 · 비교적 · 잠정적 · …로 보인다 · 편이다」 등 |
| 마크다운 셀 수 | **상한 없음** (`MAX_MD_CELLS = None`) | ⛔ 분량으로 편을 쪼개지 마라 |
| 구조 순서 | 여는 블록이 맨 앞, «다음 단계» 가 맨 뒤 | |

권고(advisory, 빌드는 통과)는 둘이다 — 출처 태그 없는 숫자, 과정 서사(「원래는 / 수정했다 /
버그」). **과정 서사는 권고로 잡히지만 우리 규약에서는 금지**다. 현재 상태의 신뢰성만 쓰고,
현재의 한계는 «다음 단계» 표로 남긴다.

### 1-3. 조각 빌더의 관용구 (기존 12 개 빌더가 공통으로 하는 것)

```python
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path: sys.path.insert(0, _p)

from report_style import (build_notebook, caption, from_json, header, md,
                          next_steps, table, table_from)

OUT = os.path.join(_ROOT, "reports", "_parts")   # ⭐조각은 여기 산다
FIG = "../outputs/figures"                        # ⭐권(reports/) 기준 상대경로
E  = from_json("outputs/elevation_sweep_md.json")
...
build_notebook(os.path.join(OUT, "78_el-sweep-design.ipynb"), blocks, strict=True)
```

⭐ **그림 경로는 `../outputs/figures/x.png`** 다. 조각 자기 위치에서는 한 층 모자라지만,
조각은 사람이 직접 열지 않고 `reports/` 로 옮겨져 읽히므로 그 경로가 옳다(`check_budget`
가 세 후보를 다 본다).

### 1-4. ⚠ 이번 라운드에 특히 물리는 함정 여섯

1. **절 제목(H1)에 출처 태그·각주를 넣지 마라.** `build_volumes.py` 는 조각의 H1 을
   `_H1_TITLE` 로 **떼어내 절 제목으로 쓰고 본문에서는 그 줄을 지운다.** 그때 각주 재번호가
   제목 사본에는 안 걸려 `[^3]` 이 딴 각주를 가리킨다. ⇒ 제목의 숫자는 손으로 적고,
   **같은 숫자를 그 절 본문 첫 문단에서 `num()` 으로 다시 낸다.**
2. **미완결 행 인용 금지.** `elevation_sweep_md.json:rows[25]`(sionna_phys/el−15,
   `n_missing = 1536`)·`rows[26]`(sionna_phys/el−45, `n_missing = 3072`) 은 부분 병합이라
   시계열에 0 이 박혀 있다. 이 두 행의 `level_db`·`track`·`fixed` 를 **어느 절에서도 쓰지 않는다.**
3. **`null` 칸**이 실제로 있다. `ch1_elevation_figdata.json:cells.*/el-90.share_track_db` 와
   `beat_track_hz` 는 `null`(f_tip = 0 이라 대역 폭이 0). `num(None, …, if_null="측정 불가")`
   로 쓰고 **0 으로 읽으면 거짓**이라고 본문에 적는다.
4. **팔 사이 `level_db` 를 나란히 놓지 마라.** `ours` 와 `sionna` 는 정규화가 달라
   −54 대 −125 dB 로 벌어져 있다. 같은 엔진의 예산 사다리 안에서만 레벨을 비교한다
   (권 17 절 5 가 그 유일한 자리다).
5. **행 인덱스를 하드코딩하지 마라.** `elevation_sweep_md.json:rows[]` 의 순서는 **병합할
   때마다 바뀐다**(§5-3 — 지금 물리 팔 샤드가 계속 들어오고 있다). 조각 빌더는 `(engine,
   el_deg, n_missing == 0)` 으로 행을 **찾아서** 인덱스를 만들고, 그 인덱스로 `num()` 을 부른다.

   ```python
   EL = RS.load_json("outputs/elevation_sweep_md.json")["rows"]
   def row(engine, el_deg):
       hits = [i for i, r in enumerate(EL)
               if r["engine"] == engine and r["el_deg"] == el_deg and r["n_missing"] == 0]
       if not hits:
           raise ContractError(f"완결 행이 없다 — {engine} el {el_deg}")
       return f"rows[{hits[0]}]"
   num(None, (J_EL, f"{row('sionna', 0.0)}.level_db"), "{:.2f}", "dB")
   ```
   ⇒ 각주에는 **그때의 실제 인덱스**가 찍히고, 미완결 행은 애초에 못 고른다.
6. **키에 점·슬래시·괄호·한글이 섞여 있다.** `cells.ours/el-90.ac_over_dc_db` ·
   `cases.전부 켬 (--physics).level_db` 같은 키는 `_walk()` 의 **가장 긴 접두 일치**로
   풀린다. 이 계획이 적은 키 문자열은 **전부 실제로 열어 값까지 확인했다**
   (`outputs/volumes_16_17_plan.json:keymap` 143 개, 실패 0).

---

## 2. `VOLUMES` 항목의 형식 (`src/build_volumes.py`)

`VOLUMES` 는 **권 → 조각 목록** 을 정하는 6 자리 튜플의 목록이다.

```python
VOLUMES = [
    ("05",              # ① 권 번호 — 2 자리 문자열. 파일 이름과 정렬 키가 된다
     "kernel",          # ② 슬러그 — 파일은 reports/05_kernel.ipynb 가 된다. [a-z0-9-] 만
     "우리 커널 — 무엇이고, 무엇이 아닌가",   # ③ 권 제목 = 이 권이 답하는 **물음**
     "SBR + 물리광학이 …",                    # ④ 한 줄 논지(thesis) — 머리말의 인용구
     ["18","19","20","21","22","23"],         # ⑤ 조각 번호 목록 = **절 순서**
     "21"),                                   # ⑥ 결론 조각 — «한 절만 읽는다면» 이 자리
]
```

- ⑤ **조각 번호 목록**: 순서가 곧 절 번호다(1 권만 절 1 이 생성물이라 +1 offset).
  각 번호는 `reports/_parts/` 에 `NN_*.ipynb` 로 **실재해야** 한다 — 없으면
  `_part_file()` 이 `FileNotFoundError` 로 멈춘다.
- ⑥ **결론 조각**(headline): ⑤ 안의 번호 하나. 권 머리말 표에 ⭐ 가 붙고,
  `reports/README.md` 와 1 권 지도의 «한 절만 읽는다면» 칸, 그리고 **읽는 경로 ①(빨리 훑기)**
  사슬이 이 값으로 만들어진다. ⑤ 밖의 번호를 적으면 그 칸이 `—` 로 비어 버린다.

이 스크립트가 조각 위에서 하는 일은 다섯이다 — **각주 재번호 · 그림 번호 재번호 ·
상호참조 재배선(`[편 22 «…»](22_po-knee.ipynb)` → `[리포트 5 절 5 «…»](05_kernel.ipynb)`) ·
권 머리말 생성 · 색인(`outputs/volumes_index.json`)과 `reports/README.md` 생성**.
조각 본문은 **다시 쓰지 않는다.**

### 2-1. 권 16·17 을 넣을 때 함께 고쳐야 하는 자리

새 튜플 둘을 `VOLUMES` 끝에 붙이는 것으로는 부족하다. «열다섯» 이 **글자로 박혀 있는**
자리가 아래와 같고, 안 고치면 지도와 목차가 디스크와 어긋난다.

| 파일:줄 | 지금 | 고칠 값 |
|---|---|---|
| `src/build_volumes.py:3` | 「조각 78 편을 15 권으로 묶는다」 | 조각 88 편을 **17 권**으로 |
| `:32` | 「권 … 15 권」 | 17 권 |
| `:46` | 「열다섯 권의 목차」 | 열일곱 권 |
| `:88` | 1 권 논지 「나머지 열네 권의 지도」 | 나머지 **열여섯 권** |
| `:184` | `MAP_SECTION_TITLE = "열다섯 권의 지도 — …"` | 열일곱 권의 지도 |
| `:457` | `_vol_intro()` 꼬리말 「열다섯 권의 지도는」 | 열일곱 권 |
| `:476` | 지도 절 «한 일» 「열다섯 권에 배치하고」 | 열일곱 권 |
| `:537·555` | 주석 | 열일곱 권 |
| `:569·570` | `"## 열다섯 권 (앞 절반)"` + `nos[:8]` / `nos[8:]` | 「열일곱 권」 + `nos[:9]` / `nos[9:]` |
| `:682` | 「최상단 목차를 15 권 편성으로」 | 17 권 |
| `:793·799·802` | `reports/README.md` 머리 「열다섯 권」 ×3 | 열일곱 권 |

⚠ `src/build_volumes.py` 를 돌리면 **기존 15 권 파일이 전부 다시 쓰인다**(조각에서 재조립).
조각을 안 건드렸으므로 내용은 같지만, 위 문자열 변경 때문에 `01_map.ipynb` 와
`reports/README.md` 는 실제로 달라진다. 돌리기 전에 `cp -a reports reports.bak_0812` 로
사본을 두고 diff 로 확인한다.

### 2-2. 새 조각의 **레지스트리 등록** — 계획 JSON 은 건드리지 않는다

`outputs/restruct_exec_plan.json` 은 여러 갈래가 동시에 읽는 정본이라 **손대지 않는다.**
`src/report_registry.py` 는 계획 밖의 편을 `outputs/reports_index/<anchor>.json` **샤드**에서
주워 온다(`SHARDS`). 그래서 새 조각 10 편은 이렇게 등록한다.

```python
# 조각 빌더 끝에서 — index_shard() 는 계획에 있는 앵커만 받으므로 직접 쓴다
import json, os
sh = dict(no="78", part=12, anchor="el-sweep-design",
          title="…(노트북 H1 과 글자 하나까지 같아야 한다)…",
          file="78_el-sweep-design.ipynb",
          evidence=["outputs/elevation_sweep_md.json", "outputs/ch1_elevation_figdata.json"],
          from_cells=[], builder="src/build_part12_elevation.py")
d = os.path.join(_ROOT, "outputs", "reports_index"); os.makedirs(d, exist_ok=True)
json.dump(sh, open(os.path.join(d, f"{sh['anchor']}.json"), "w"),
          ensure_ascii=False, indent=1)
```

- `part=12` 는 **계획에 없는 부 번호**다. 일부러 그렇게 둔다 — `_bu_to_vol()` 이 옛 부 0~11 의
  귀속을 계산할 때 우리 조각이 그 집계를 흔들지 않는다. ⛔ `ref_part(12)` 는 부르면 예외다.
- 첫 실행 때는 샤드가 아직 없으므로 **형제 새 조각을 가리키는 `ref()` 는 로컬로 만든다**
  (`src/build_part11_measurement.py:53-78` 의 `EXTRA` + 지역 `ref()` 가 그 선례다).
  기존 조각 00~77 을 가리킬 때만 `report_registry.ref(anchor)` 를 쓴다.
- `benchmark/check_report_links.py` 의 `title-mismatch` 검사가 **노트북 H1 과 샤드 제목**을
  맞춰 본다. 제목을 고치면 샤드도 같이 고친다.
- `orphan` 권고를 피하려고 **새 조각끼리 최소 한 번씩 서로를 가리킨다**(§4 의 링크 계획).

---

## 3. 비어 있는 조각 번호와 새 조각 10 편

`reports/_parts/` 에 있는 번호는 **00~77 연속**(78 편)이고 `restruct_exec_plan.json` 의
`reports` 는 00~76(77 편)이다 — 77 은 `size-law-differential` 샤드로 등록된 계획 밖 편이다.
⇒ **비어 있는 첫 번호는 78** 이고, 이번에 78~87 을 쓴다.

| 조각 | 앵커 | 제목(= 그 절의 결론 한 문장) | 이 조각이 답하는 한 줄 질문 | 권·절 | 그림 |
|---|---|---|---|---|---|
| **78** | `el-sweep-design` | 앙각 7 점을 10 m 한 자리에서 재고, 28 행 중 26 행만 판정에 쓴다 | 이 스윕이 무엇을 어떤 잣대로 쟀고, 어느 행을 인용해도 되나? | 16 · 1 | `ch1_f1_maps.png` |
| **79** | `el-band-tracking` | 대역을 f_tip 따라 옮기면 −75° 에서도 프로펠러 대역이 대역외 띠보다 44.6 dB 높고, 고정 대역은 같은 자리에서 0.95 dB 다 | 앙각이 내려가면 프로펠러 대역 에너지가 정말 주나? | 16 · 2 ⭐ | `ch1_f4_bandenergy.png` |
| **80** | `el-prediction-gap` | 기하 겹침 예측은 채점된 5 점에서 최대 15.6 dB 빗나가고 그중 −15° 는 기준점 자신이다 | «대역이 겹치는 만큼 에너지가 준다» 는 예측이 맞나? | 16 · 3 | `ch1_f3_prediction.png` |
| **81** | `el-beat-vs-tip` | 126.67 Hz 박자는 세 팔이 다 맞추고, 팔을 가르는 것은 f_tip 위 굴러떨어짐 24.0 dB 대 9.9 dB 다 | 무엇이 엔진을 가르는 잣대인가? | 16 · 4 | `ch1_f2_spectra.png` |
| **82** | `el-nadir-floor` | −90° 의 변조는 −38.31 dB 로 남지만 그 전력의 64 % 는 광선 격자 표본화 잡음이다 | 머리 위 드론은 정말 안 보이나? | 16 · 5 | — |
| **83** | `physics-single-axis` | 나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다 | `--physics` 가 켜는 넷 중 무엇이 결과를 만들었나? | 17 · 1 ⭐ | — |
| **84** | `physics-denominator` | AC/DC 가 +0.89 dB 에서 −68.13 dB 로 내려간 것은 분모가 66.55 dB 커진 결과다 | 물리를 켜니 나딧 도플러가 이론대로 0 이 된 것인가? | 17 · 2 | — |
| **85** | `physics-above-limit` | 물리를 켜면 날개끝 상한 위 에너지 몫이 0.290 에서 0.831 로 커진다 | 물리를 켜면 운동학 상한을 지키게 되나? | 17 · 3 | `wideband_energy.png` |
| **86** | `physics-deck-match` | 우리 팔은 8/11 덱 15 m 판과 0.9877 로 겹치고 물리 팔의 같은 칸은 아직 미완결이다 | 물리를 켠 PathSolver 가 덱 무늬에 더 가까워지나? | 17 · 4 | `physics_vs_deck_el-15.png` |
| **87** | `budget-not-physics` | 광선을 360 배 늘려도 레벨은 0.03 dB 안에 모이고 박자는 58.15 Hz 로 헤맨다 | 광선을 더 쏘면 고쳐지는 것과 안 고쳐지는 것은 무엇인가? | 17 · 5 | `ch1_f5_raybudget.png` |

제목의 숫자는 **전부 §5 지도의 키에서 왔다.** 파생값(뺄셈)인 44.6 · 0.95 · 66.55 · 0.03 은
본문에서 **두 키를 각각 `num()` 으로 낸 뒤** 차이를 말한다.

---

## 4. 권 둘의 편성

### 4-1. `VOLUMES` 에 붙일 튜플

```python
("16", "elevation-coverage", "앙각 커버리지 — 어느 각도까지 유효한가",
 "관측 앙각을 0° 에서 −90° 까지 내리며 같은 표적을 재면, 커버리지를 정하는 것은 "
 "표적이 아니라 **우리가 고른 분석 대역**이다. 대역을 날개끝 주파수를 따라 옮기면 −75° 까지 "
 "프로펠러 대역이 살아 있고, 고정하면 −60° 아래에서 바닥에 닿는다.",
 ["78", "79", "80", "81", "82"], "79"),

("17", "physics-switches", "엔진의 물리 스위치 — 켜면 무엇이 달라지나",
 "스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 **하나씩** 켜서 무엇이 결과를 만들었는지 "
 "귀속한다. 나딧에서 66.55 dB 를 올리는 것은 회절 하나이고, 그 상승은 분자가 아니라 "
 "**분모**를 키운다.",
 ["83", "84", "85", "86", "87"], "83"),
```

파일은 `reports/16_elevation-coverage.ipynb` · `reports/17_physics-switches.ipynb` 다.

### 4-2. 권 16 「앙각 커버리지 — 어느 각도까지 유효한가」 · 절 5

| 절 | 결론이 곧 제목 | 무엇으로 서나 |
|---|---|---|
| 1 | 앙각 7 점을 10 m 한 자리에서 재고, 28 행 중 26 행만 판정에 쓴다 | 규약(10 m 구면·az 0°·PRF 19,700 Hz·4,096 자세·matrice4e)과 완결성 표. **10 m 는 원거리장 경계 14.08 m 안쪽**이라 근접장 판이라고 먼저 못 박는다 |
| 2 ⭐ | 대역을 f_tip 따라 옮기면 −75° 에서도 프로펠러 대역이 대역외 띠보다 44.6 dB 높고, 고정 대역은 같은 자리에서 0.95 dB 다 | 추적 대역 대 고정 대역 · 팔마다 같은 폭 대역외 기준띠 · 추적 대역 몫의 앙각 산포 15.9 dB |
| 3 | 기하 겹침 예측은 채점된 5 점에서 최대 15.6 dB 빗나가고 그중 −15° 는 기준점 자신이다 | G3 게이트 5 칸. **채점된 점이 7 이 아니라 5** 이고 −75·−90 은 «적중» 이 아니라 빠진 점이라고 적는다 |
| 4 | 126.67 Hz 박자는 세 팔이 다 맞추고, 팔을 가르는 것은 f_tip 위 굴러떨어짐 24.0 dB 대 9.9 dB 다 | G1(박자)·G2(굴러떨어짐)·`above_f_tip_frac`. **f_flash 는 입력값**이라 박자 일치는 산란 커널을 재지 않는다 |
| 5 | −90° 의 변조는 −38.31 dB 로 남지만 그 전력의 64 % 는 광선 격자 표본화 잡음이다 | 나딧 잔여 삼분할(격자 64 % · 근접장 31 % · 가림 5 %) · 격자 λ/12 의 거리 지수 2.589 · 10 m~1 km 에서 −48.5 ~ −50.3 dB |

### 4-3. 권 17 「엔진의 물리 스위치 — 켜면 무엇이 달라지나」 · 절 5

| 절 | 결론이 곧 제목 | 무엇으로 서나 |
|---|---|---|
| 1 ⭐ | 나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다 | 6 케이스 단일축 분해(기준·굴절·회절·모서리회절·다중반사·전부). 모서리회절만 켠 판은 기준과 **소수점까지 같다** |
| 2 | AC/DC 가 +0.89 dB 에서 −68.13 dB 로 내려간 것은 분모가 66.55 dB 커진 결과다 | 같은 표의 두 열을 나란히. 「물리를 켜니 도플러가 0 이 됐다」는 **분모 상승**의 다른 이름이다 |
| 3 | 물리를 켜면 날개끝 상한 위 에너지 몫이 0.290 에서 0.831 로 커진다 | `wideband_energy` 의 물리 팔 두 칸(el 0 · el −90). 물리 상한 위는 블레이드 도플러일 수 없는 자리다 |
| 4 | 우리 팔은 8/11 덱 15 m 판과 0.9877 로 겹치고 물리 팔의 같은 칸은 아직 미완결이다 | 덱 3/15/40 m 대조 · PathSolver 0.6961 · `_meta.missing_arms` 가 `sionna_phys/el-15` 와 `ours_ptd/el-15` 를 비었다고 적는다 |
| 5 | 광선을 360 배 늘려도 레벨은 0.03 dB 안에 모이고 박자는 58.15 Hz 로 헤맨다 | el 0 예산 사다리 4 계단 · 40 m 시드 사다리(sd 4.156 → 1.833 dB) · 예산 축과 물리 축은 다른 축이다 |

### 4-4. 조각 사이 링크 계획 (orphan 권고 0 을 만든다)

```
78 → 79(헤드라인) · 81(잣대)          82 → 84(같은 나딧 자리)
79 → 80(예측 대조) · 82(나딧)          83 → 84 · 85
80 → 79                                84 → 82(우리 팔의 나딧)
81 → 85(상한 위 누설) · 87(예산 축)    85 → 81      86 → 83      87 → 81
기존 권으로: 78·81 → 조각 36(권 08 «두 엔진이 f_tip 아래에서 겹치고 위에서 갈린다»),
             87 → 조각 42(권 09 «광선예산»), 82 → 조각 22(권 05 «PO 무릎»)
```

---

## 5. 원장 재고표

### 5-1. 파일 단위 (a) 있는가 (b) 어떤 키 (c) 완결성

| 원장 | 있나 | 쓰는 키(대표) | 완결성 |
|---|---|---|---|
| `outputs/elevation_sweep_md.json` | ✅ 13.7 KB | `_meta.{range_m,prf_hz,f_flash_hz,drone,elevations_deg,rpm_per_rotor,grid_ko,range_why_ko}` · `rows[i].{engine,el_deg,f_tip_hz,n_poses,n_missing,seconds,npaths_median,level_db,track.*,fixed.*}` | 28 행 중 **26 행 완결**, 2 행 부분 병합(§5-2) |
| `outputs/elevation_sweep_md.npz` | ✅ 1.5 MB | 키 = `engine/el±NN` 시계열 | 그림 빌더 입력. **조각은 직접 안 연다** |
| `outputs/ch1_elevation_figdata.json` | ✅ 20.3 KB | `cells."<arm>/el±NN".{share_track_db,share_track_oob_db,share_fixed_db,share_fixed_oob_db,carrier_share_db,share_*_rel_carrier_db,ac_over_dc_db,comb_snr_db[],beat_track_hz,beat_fixed_hz,npaths_median,ledger_level_db}` · `prediction.{fixed_band_overlap_frac,f_tip_hz}.<el>` · `gates.G1~G6*` | **21 칸**(ours·sionna·sionna_p250000000 × 7). `sionna_phys` 없음. el−90 의 `share_track_db`·`beat_track_hz` 는 `null` |
| `outputs/wideband_energy.json` | ✅ 5.8 KB | `cells."<arm>/el±NN".{"0-500 Hz","500-f_tip","f_tip-2f_tip","2-4 f_tip","4f_tip-Nyquist",above_f_tip_frac,above_f_tip_db,f_tip_hz}` · `_meta.{nyquist_hz,physical_limit_ko,incomplete_excluded_ko}` | **23 칸** — ours·sionna·p250M 각 7 + **`sionna_phys` 는 el+0·el−90 두 칸뿐**. el−75·el−90 의 `500-f_tip` 은 `null`, el−90 의 `f_tip-2f_tip` 은 −3000(빈 대역 표식) |
| `outputs/diag_physics_paths_el-90.json` | ✅ 1.7 KB | `_meta.{el_deg,n_poses,spp,range_m,fc_hz}` · `cases."<케이스>".{npaths_median,npaths_mean,level_db,ac_over_dc_db,sec_per_pose,max_depth,refraction,diffraction,edge_diffraction}` | **6 케이스 완결**. ⚠ `n_poses = 20` 뿐이다(스윕은 4,096) — 레벨 비교용이지 스펙트럼용이 아니다 |
| `outputs/physics_vs_deck.json` | ✅ 2.2 KB | `cells."<arm>".{comb_spacing_hz,comb_spacing_err_hz,line_snr_db."1x"~"8x",ac_over_dc_db,corr_with_ours_db_map}` · `_meta.missing_arms[]` | **5 칸**(ours·sionna·덱 R3/R15/R40). ⚠ `missing_arms = ["ours_ptd/el-15","sionna_phys/el-15"]` — **물리 팔의 덱 대조는 아직 없다** |
| `outputs/verify_nadir_flash.json` | ✅ 12.3 KB | `A_instrument_audit.{nperseg,bin_hz,hann_mainlobe_halfwidth_hz,band_lo_hz,band_hi_hz,synthetic_tests.*}` · `B_decomposition."<arm>/el±NN".{level_db,ac_over_dc_db,am_rms,pm_rms_deg,pm_over_am_db,fixed_band_*}` · `C_D_geometry.*` · `E_blade_line_power.rows.*` | B 는 **9 칸**만(ours 5 · sionna 2 · p250M 2). ⚠ `C_D_geometry` 의 1/r⁴·나딧 기전은 **§6 에서 반증된 대리모형** — 인용 금지 |
| `outputs/refute_nadir_mechanism_final.json` | ✅ 33.3 KB | `R1_range_law_ledger.*` · `R4b_cpu_kernel_replica.{measured,emulated,corr_ac_sph10_vs_measured,range_sweep_ac_over_dc_db.*,nearfield_only_*,pm_am.*,shift_null.*}` · `R4c_grid_ladder.rows."lambda/NN".*` · `R4f_comb_attribution.*` · `R5_detection.nadir_ac_split.*` · `VERDICTS.claim1~5.*` | 완결. **이 파일이 `verify_nadir_flash` 의 상위 판정**이다 — 둘이 다르면 이쪽이 이긴다 |
| `outputs/verify_phase_sign.json` | ✅ 0.7 KB | `G1_abs_invariant.pass` · `G2_farfield_converges.{rho_real,rho_abs}` · `G3_approach_positive.*` · `asymmetry_db.*` · `verdict` | 게이트 **3/3 PASS**. 완결 |
| `outputs/verify_po_elev_unit.json` | ✅ 80.5 KB | `meta.*` · `cases[i].*`(25 케이스) · `gates[i].{name,pass_,detail,why_ko}`(18 게이트) · `real_sweep_recheck.{rows[],monotonic_check}` | 완결. **18 게이트 중 7 개 불합격**(전부 λ/12 생산 격자, λ/48 에서 합격) — 합격/불합격을 섞어 쓰지 마라 |
| `outputs/verify_po_elev_unit_rebuttal.json` | ⛔ **없음** | — | 지시문의 이름이다. **실재하는 파일은 `outputs/verify_po_elev_rebuttal.json`** |
| `outputs/verify_po_elev_rebuttal.json` | ✅ | `재현된_것.표.<el>.*` · `깨진_것.0~9.*` · `확증된_것_판정이_옳았던_곳.*` · `내가_시도했다가_반증당한_내_가설.*` | 완결. 키가 **한글**이다 |
| `outputs/rt_no_rcs_verify.json` | ✅ 3.2 KB | `geometry.*` · `A_plate[i].*` · `B_sphere_S[i].*` · `C_pec_sphere[i].{r,spp,n_paths}` · `D_chamber_paths.{tau_expect_ns,rows[],n_near,n_true}` | 완결 |
| `outputs/raybudget_seed_ladder.json` | ✅ 5.5 KB | `_meta.{range_m,drone,f_flash_hz,f_tip_hz,band_hz}` · `cells[i].{spp,n_seeds,n_poses,npaths_median,level_db_mean,sd_level_db,ptp_level_db,sd_h1_over_h2_db,sd_beat_hz,beats_hz[]}` · `verdict.*` | **2 계단**(178 M · 4,000 M). ⚠ 40 m·el −15° 한 자리에서만 잰 값이다 |
| `outputs/report07_range40_raybudget.json` | ✅ 3.8 KB | `_meta.*` · `rows[i].{arm,spp,label,seed,n_poses,gaps,shards[]}` · `verdict.{beat_spread_hz,level_spread_db,h1_over_h2_spread_db,path_scaling_ko,caveat_ko}` | **시드가 판마다 2 개뿐** — 「폭이 줄었다」는 통계적 주장이 아니라고 원장이 스스로 적는다 |
| `docs/CH1_ELEVATION_FINDINGS.md` | ✅ 294 줄 | 서술 | ⚠ **§2-2 의 「오차 0.00 Hz」·§4-③ 의 「1/r⁴ 라 실전 거리에서 사라진다」는 반증됐다**(§6) |
| `docs/RESUME.md` | ✅ 160 줄 | 서술 | §2 «오늘 반증된 것» 6 줄이 이 계획의 §6 과 같은 목록이다 |
| 그림 7 장 | ✅ | `outputs/figures/ch1_f1_maps.png` · `ch1_f2_spectra.png` · `ch1_f3_prediction.png` · `ch1_f4_bandenergy.png` · `ch1_f5_raybudget.png` · `wideband_energy.png` · `physics_vs_deck_el-15.png` | 전부 실재. **다시 그릴 필요 없다** |

### 5-2. ⚠ `elevation_sweep_md.json:rows[]` 완결성 표 (28 행 전수)

| i | engine | el | n_poses | **n_missing** | npaths_median | level_db | 인용 |
|---|---|---|---|---|---|---|---|
| 0 | ours | 0 | 4096 | **0** | null | −54.37 | ✅ |
| 1 | ours | −15 | 4096 | **0** | null | −51.16 | ✅ |
| 2 | ours | −30 | 4096 | **0** | null | −63.37 | ✅ |
| 3 | ours | −45 | 4096 | **0** | null | −58.67 | ✅ |
| 4 | ours | −60 | 4096 | **0** | null | −65.76 | ✅ |
| 5 | ours | −75 | 4096 | **0** | null | −47.28 | ✅ |
| 6 | ours | −90 | 4096 | **0** | null | −41.66 | ✅ |
| 7 | sionna | 0 | 4096 | **0** | 9 | −59.65 | ✅ |
| 8 | sionna | −15 | 4096 | **0** | 7 | −124.80 | ✅ |
| 9 | sionna | −30 | 4096 | **0** | 6 | −135.45 | ✅ |
| 10 | sionna | −45 | 4096 | **0** | 12 | −125.92 | ✅ |
| 11 | sionna | −60 | 4096 | **0** | 13 | −127.86 | ✅ |
| 12 | sionna | −75 | 4096 | **0** | 13 | −127.60 | ✅ |
| 13 | sionna | −90 | 4096 | **0** | 12 | −130.29 | ✅ |
| 14 | sionna_p1000000000 | 0 | 4096 | **0** | 471 | −59.67 | ✅ |
| 15 | sionna_p1000000000 | −30 | 4096 | **0** | 809 | −131.20 | ✅ |
| 16 | sionna_p250000000 | 0 | 4096 | **0** | 127 | −59.66 | ✅ |
| 17 | sionna_p250000000 | −15 | 4096 | **0** | 159 | −118.93 | ✅ |
| 18 | sionna_p250000000 | −30 | 4096 | **0** | 211 | −133.82 | ✅ |
| 19 | sionna_p250000000 | −45 | 4096 | **0** | 268 | −124.43 | ✅ |
| 20 | sionna_p250000000 | −60 | 4096 | **0** | 287 | −119.79 | ✅ |
| 21 | sionna_p250000000 | −75 | 4096 | **0** | 323 | −115.05 | ✅ |
| 22 | sionna_p250000000 | −90 | 4096 | **0** | 352 | −118.27 | ✅ |
| 23 | sionna_p4000000000 | 0 | 4096 | **0** | 2008 | −59.68 | ✅ |
| 24 | sionna_phys | 0 | 4096 | **0** | 5 | −59.66 | ✅ |
| 25 | sionna_phys | −15 | 4096 | **1536** | 2 | −111.27 | ⛔ **인용 금지** |
| 26 | sionna_phys | −45 | 4096 | **3072** | 8 | −108.92 | ⛔ **인용 금지** |
| 27 | sionna_phys | −90 | 4096 | **0** | 6 | −64.23 | ✅ |

⇒ **이 병합판(03:50)에서** 물리 팔에 쓸 수 있는 것은 el 0 과 el −90 두 점뿐이다.
다만 아래 §5-3 을 먼저 읽어라 — 이 표는 **오늘 오후에 바뀐다.**

### 5-3. ⚠ 원장이 지금 자라고 있다 — 이 표는 2026-08-12 04:35 스냅샷이다(기계판은 `outputs/volumes_16_17_plan.json:shard_status`)

GPU 3 에서 앙각 스윕이 계속 돌고 있고, `outputs/elev_sweep_shards/` 의 물리 팔 샤드가
**병합판보다 앞서 있다.**

| 팔 | 앙각 | 샤드 | 마지막 파일 | 병합판(03:50) 에 반영됐나 |
|---|---|---|---|---|
| `sionna_phys` | el+0 | 8/8 | 03:29 | ✅ `rows[24]` 완결 |
| `sionna_phys` | el−15 | **8/8** | **03:53** | ⛔ 아니다 — `rows[25].n_missing = 1536` |
| `sionna_phys` | el−30 | **8/8** | **04:32** | ⛔ 행 자체가 없다 |
| `sionna_phys` | el−45 | **8/8** | **04:23** | ⛔ 아니다 — `rows[26].n_missing = 3072` |
| `sionna_phys` | el−60 | **8/8** | **04:34** | ⛔ 행 자체가 없다 |
| `sionna_phys` | el−75 | 4/8 | 04:28 | 도는 중 |
| `sionna_phys` | el−90 | 8/8 | 03:07 | ✅ `rows[27]` 완결 |
| `sionna_p250000000_phys` ⭐**새 팔** | el+0 · el−15 · el−90 | 8/8 · 8/8 · 8/8 | 04:18 | ⛔ 행 자체가 없다 |

⇒ 결론 셋.
1. 권 17 절 4 의 «물리 팔의 덱 대조가 없다» 는 **`--merge` 한 번(CPU)** 이면 닫힐 수 있다.
   새 GPU 계산이 아니다. ⛔ 다만 그 병합은 **기존 원장을 덮어쓰므로** 이 라운드에서 하지
   않는다 — 상위 판단으로 올린다.
2. 병합하면 **행이 늘고 인덱스가 밀린다.** 그래서 §1-4 함정 5 의 `row()` 헬퍼가 필수다.
   이 계획의 `rows[25]`·`rows[26]` 같은 번호는 **스냅샷 기록**이지 빌더가 쓸 주소가 아니다.
3. `sionna_p250000000_phys`(물리 + 250 M 광선)는 **이 계획에 없던 팔**이다. 병합되면
   권 17 절 1·3 이 «예산 축과 물리 축을 함께 켠 판» 을 한 줄 더 얻는다 — 그때 절 3 의
   표에 열 하나를 붙인다.

---

## 6. ⛔ 되살리면 안 되는 여섯 — 조각 빌더가 문장으로 쓰기 전에 읽는다

| # | 쓰면 안 되는 말 | 대신 쓰는 말 | 근거 키 |
|---|---|---|---|
| 1 | 「나딧 잔여는 1/r⁴ 로 죽으니 실전 거리에서 사라진다」 | 1/r⁴ 는 재질·가림·격자 없는 대리모형의 성질이다. 생산 격자 λ/12 의 거리 지수는 **2.589** 이고 총 AC/DC 는 10 m~1 km 에서 **−48.46 → −50.31 dB** 로 거의 평평하다 | `refute_nadir_mechanism_final.json:R4c_grid_ladder.rows.lambda/12.nearfield_only_fit_exponent` · `R4b_cpu_kernel_replica.range_sweep_ac_over_dc_db.{10,1000}` |
| 2 | 「나딧에 남는 것은 진짜 신호」 | 나딧 AC 전력의 **63.68 %** 가 광선 격자 표본화 잡음, 31.12 % 근접장 곡률, 5.2 % 가림이다 | `…:R5_detection.nadir_ac_split.{grid_sampling_noise_fraction,nearfield_fraction,occlusion_fraction}` |
| 3 | 「우리 커널만 −75° 에서 박자를 맞춘다」 · 「오차 0.00 Hz」 | −75° 에서 우리 팔 126.67 · PathSolver **126.45** · 250 M **126.41** Hz 다. `f_flash` 는 **입력값**이라 이 잣대는 산란 커널을 재지 않는다 | `ch1_elevation_figdata.json:cells.{sionna,sionna_p250000000}/el-75.beat_track_hz` |
| 4 | 「물리를 켜니 나딧 도플러가 이론대로 0 이 됐다」 | 분모가 커졌다 — 레벨이 −130.78 → −64.23 dB(+66.55) 로 오르고 AC/DC 가 +0.89 → −68.13 dB 로 내려갔다. 올린 것은 **회절**이다 | `diag_physics_paths_el-90.json:cases.{기준(지금까지의 실행),회절만 켬}.{level_db,ac_over_dc_db}` |
| 5 | 「계획서 G3 가 7 점에서 맞았다/틀렸다」 | 채점된 점은 **5** 이고 −15° 는 기준점 자신(0.0)이다. −75·−90 은 «예측 적중» 이 아니라 **채점에서 빠진 점**이다 | `ch1_elevation_figdata.json:gates.G3_ours_fixed_minus_prediction_db`(5 칸) |
| 6 | 「1/r⁴ 이면 2.5 배 거리에 −7.96 dB」 | `40·log10(2.5) = 15.92 dB` 다 | `refute_nadir_mechanism_final.json:R1_range_law_ledger.orchestrator_arithmetic_check_ko` |

그리고 **검증됨과 그럴듯함을 섞지 않는다.**
검증됨(게이트가 있다): 부호 규약 3/3 · PO 운동학 ρ ≥ 0.9956 · 나딧 잔여 삼분할 ·
`shift_null` 대조(관측 0.998 vs 널 p99 0.4618).
그럴듯함(게이트 없음): 「PathSolver 빗살은 경로 집합 깜빡임이다」 ·
「−90° 패널의 ±600 Hz 띠는 창 치맛자락이다」. 뒤엣것은 **그렇게 적는다**.

---

## 7. 절 → 원장 키 지도

표기: `파일 : 키`. 별표(`*`)는 그 축을 훑는다는 뜻이고, 조각 빌더는 `table_from()` 으로 뽑는다.

### 권 16

| 절 | 키 | 무엇에 쓰나 |
|---|---|---|
| 1 | `elevation_sweep_md.json : _meta.range_m` = 10.0 · `_meta.prf_hz` = 19700.0 · `_meta.f_flash_hz` = 126.667 · `_meta.drone` = matrice4e · `rows[0].n_poses` = 4096 · `rows[0].seconds` = 1686.2 | 규약 표 |
| 1 | `elevation_sweep_md.json : rows[*].{engine,el_deg,n_missing,npaths_median}` | **완결성 표**(`table_from`) — 26/28 |
| 1 | `elevation_sweep_md.json : _meta.range_why_ko` · `_meta.grid_ko` · `_meta.band_track_ko` · `_meta.band_fixed_ko` | 근접장 판·얼린 격자·두 대역 정의를 원장 말 그대로 |
| 1 | `ch1_elevation_figdata.json : gates.G5_sionna_npaths_min_max[0]`·`[1]` · `gates.G5_sionna_p250000000_npaths_min_max[0]`·`[1]` | 경로 수는 **결과가 아니라 교란**(광선 규칙이 거리만 본다) |
| 2 | `ch1_elevation_figdata.json : cells.ours/el-15.share_track_db` = −21.46 · `.share_track_oob_db` = −36.42 | 추적 대역이 바닥보다 가장 적게 뜬 자리(15.0 dB) |
| 2 | `… : cells.ours/el-75.share_track_db` = −10.88 · `.share_track_oob_db` = −55.48 | **44.6 dB** — 절 제목의 숫자 |
| 2 | `… : cells.ours/el-75.share_fixed_db` = −49.60 · `.share_fixed_oob_db` = −50.55 | 고정 대역은 같은 자리에서 **0.95 dB** |
| 2 | `… : cells.ours/el-90.share_fixed_db` = −51.64 · `.share_fixed_oob_db` = −51.47 | −90° 는 −0.17 dB(구별 불가) |
| 2 | `… : cells.ours/el-90.share_track_db`(**null**) · `.beat_track_hz`(**null**) | `if_null="측정 불가"` — 폭 0 이라 잴 수 없다 |
| 2 | `… : gates.G6_ours_track_share_span_db` = 15.9 · `cells.ours/el-60.carrier_share_db` = −14.05 · `cells.ours/el-60.share_track_rel_carrier_db` = 8.46 | 추세 없음 · 분모가 널이 되는 자리를 두 정규화로 함께 |
| 3 | `… : gates.G3_ours_fixed_minus_prediction_db.{+0,-15,-30,-45,-60}` = 6.0 / 0.0 / 15.6 / 12.9 / 12.0 | 예측 대 실측 표(5 칸) |
| 3 | `… : gates.G3_worst_db` = 15.6 | 최악 어긋남 |
| 3 | `… : prediction.fixed_band_overlap_frac.{+0…-90}` · `prediction.f_tip_hz.{+0…-90}` | 예측이 무엇이었나 |
| 4 | `… : gates.G1_ours_worst_dev_hz` = 0.51 · `G1_ours_n_within_2hz` = 6 · `G1_sionna_worst_dev_hz` = 250.06 · `G1_sionna_n_within_2hz` = 4 · `G1_sionna_p250000000_worst_dev_hz` = 76.4 · `…_n_within_2hz` = 5 | 박자 게이트 |
| 4 | `… : cells.{ours,sionna,sionna_p250000000}/el-75.beat_track_hz` = 126.67 / 126.45 / 126.41 | ⛔ 반증 3 의 정정이 서는 자리 |
| 4 | `… : gates.G2_{ours,sionna,sionna_p250000000}_rolloff_db_{mean,min}` = 24.0/12.3 · 9.9/5.2 · 12.3/−0.1 | 굴러떨어짐이 팔을 가른다 |
| 4 | `wideband_energy.json : cells.{ours,sionna,sionna_p250000000}/el±NN.above_f_tip_frac` · `.above_f_tip_db` | 물리 상한 위 누설(세 팔 21 칸) |
| 4 | `wideband_energy.json : _meta.physical_limit_ko` · `_meta.nyquist_hz` = 9850 | 상한의 정의 |
| 5 | `ch1_elevation_figdata.json : cells.ours/el-90.ac_over_dc_db` = −38.31 | 모든 앙각 중 최저 변조 |
| 5 | `refute_nadir_mechanism_final.json : R5_detection.nadir_ac_split.{grid_sampling_noise_fraction,nearfield_fraction,occlusion_fraction}` = 0.6368 / 0.3112 / 0.052 | 삼분할 |
| 5 | `… : R4c_grid_ladder.rows."lambda/NN".{n_rays,spacing_mm,sph10_ac_over_dc_db,nearfield_only_fit_exponent}` (λ/8·12·24·48) | 격자 사다리 — 조이면 지수가 4 로 간다 |
| 5 | `… : R4b_cpu_kernel_replica.{corr_ac_sph10_vs_measured,range_sweep_ac_over_dc_db.10,…1000,shift_null.observed,shift_null.null_p99}` | 재현기 ρ = 0.998, 널 대조 |
| 5 | `… : R4f_comb_attribution.{white_noise_baseline_db,grid_noise_share_of_comb_power}` | 빗살은 물리, 격자 잡음은 빗살 밖 |
| 5 | `verify_nadir_flash.json : B_decomposition.ours/el-90.fixed_band_true_over_leakage_db` = 0.01 · `A_instrument_audit.hann_mainlobe_halfwidth_hz` = 562.9 | 고정 대역 값이 누설인 이유 |

### 권 17

| 절 | 키 | 무엇에 쓰나 |
|---|---|---|
| 1 | `diag_physics_paths_el-90.json : cases.*.{npaths_median,level_db,ac_over_dc_db,sec_per_pose,max_depth,refraction,diffraction,edge_diffraction}` (6 케이스) | 단일축 분해 표 전체(`table_from`) |
| 1 | `… : cases.기준(지금까지의 실행).level_db` = −130.78 · `cases.회절만 켬.level_db` = −64.23 · `cases.전부 켬 (--physics).level_db` = −64.23 | 회절 하나가 전부다 |
| 1 | `… : cases.모서리회절만 켬.{npaths_median,level_db}` = 11 / −130.78 | 기준과 소수점까지 같다 |
| 1 | `… : cases.굴절만 켬.npaths_median` = 2 · `cases.다중반사만 (depth 3).level_db` = −130.76 | 나머지 스위치는 레벨을 안 움직인다 |
| 1 | `… : _meta.{n_poses,spp,range_m,fc_hz}` = 20 / 11111111 / 10.0 / 3.5e9 | ⚠ 20 자세 판이라 스펙트럼 주장은 못 한다 |
| 2 | `… : cases.기준(지금까지의 실행).ac_over_dc_db` = 0.89 · `cases.회절만 켬.ac_over_dc_db` = −68.13 | 분모가 커진 것이다 |
| 2 | `elevation_sweep_md.json : rows[27].{level_db,n_missing}` = −64.23 / 0 · `rows[24].level_db` = −59.66 | 4,096 자세 판이 같은 레벨을 준다 |
| 2 | `ch1_elevation_figdata.json : cells.ours/el-90.ac_over_dc_db` = −38.31 (**권 16 절 5 소유 — 링크만**) | 우리 팔과의 대조 |
| 3 | `wideband_energy.json : cells.sionna_phys/el+0.{above_f_tip_frac,above_f_tip_db}` = 0.83078 / −0.81 | 물리를 켠 팔 |
| 3 | `… : cells.sionna/el+0.above_f_tip_frac` = 0.29027 · `cells.ours/el+0.above_f_tip_frac` = 0.02285 | 대조 두 칸(권 16 절 4 의 표를 링크) |
| 3 | `… : cells.sionna_phys/el-90.{"0-500 Hz","4f_tip-Nyquist"}` = −11.8 / −0.0 | f_tip = 0 자리의 대역 분포 |
| 4 | `physics_vs_deck.json : cells.{sionna/el-15,deck:R3/E,deck:R15/E,deck:R40/E}.corr_with_ours_db_map` = 0.6961 / 0.9141 / 0.9877 / 0.9774 | 덱 대조 표 |
| 4 | `… : cells.*.{comb_spacing_hz,comb_spacing_err_hz,ac_over_dc_db}` | 빗살 간격은 다섯 칸 모두 125.05 Hz |
| 4 | `… : _meta.missing_arms[0]`·`[1]` = `ours_ptd/el-15` · `sionna_phys/el-15` | **미완결을 이름으로 적는다** |
| 4 | `… : _meta.geometry_ko` · `_meta.stft_ko` · `_meta.normalisation_ko` | 덱과 다른 것은 거리뿐 · STFT 만 · 패널별 정규화 |
| 5 | `elevation_sweep_md.json : rows[{7,16,14,23}].{level_db,npaths_median,track.beat_hz}` = −59.65/9/376.73 · −59.66/127/50.27 · −59.67/471/122.12 · −59.68/2008/58.15 | el 0 예산 사다리 — 레벨 수렴, 박자 헤맴 |
| 5 | `elevation_sweep_md.json : rows[9].track.beat_hz` = 252.32 · `rows[18].track.beat_hz` = 126.61 | −30° 는 예산으로 **고쳐졌다**(대조군) |
| 5 | `raybudget_seed_ladder.json : cells[{0,1}].{spp,n_seeds,npaths_median,sd_level_db,sd_beat_hz}` · `verdict.structure_ko` · `verdict.caveat_ko` | 시드 산포 4.156 → 1.833 dB, 한 자리에서만 잰 값이라는 경고까지 |
| 5 | `report07_range40_raybudget.json : verdict.{level_spread_db,beat_spread_hz,h1_over_h2_spread_db,path_scaling_ko,caveat_ko}` | 40 m 판 · 시드 2 개뿐이라는 원장 자신의 경고 |
| 1·5 | `rt_no_rcs_verify.json : D_chamber_paths.{n_near,n_true}` = 12 / 1 · `C_pec_sphere[0].n_paths` = 0 | 경로 수를 산란 세기로 읽으면 안 되는 이유 |
| 재현 | `verify_phase_sign.json : verdict` = PASS · `G2_farfield_converges.rho_real` = 0.999999 | 두 권의 시계열이 부호 정정본이라는 근거 |
| 재현 | `verify_po_elev_unit.json : gates[0].detail.rho_min` = 0.9956 · `gates[2].detail.ac_below_dc_db` = −21.75 | PO 운동학이 해석해와 맞는다 · 단위시험의 나딧 바닥 |

---

## 8. ⚠ 두 권이 겹치는 숫자 — 주인을 정한다

| 겹치는 양 | 주인 | 다른 쪽은 |
|---|---|---|
| 우리 팔 el −90 의 AC/DC **−38.31 dB** | **권 16 절 5** | 권 17 절 2 는 인용하지 않고 «권 16 절 5» 로 링크한다 |
| 나딧 잔여 삼분할(격자 64 % 등) · 격자 지수 2.589 | **권 16 절 5** | 권 17 은 «분해는 권 16 절 5» 라고만 적는다 |
| `above_f_tip_frac` — ours·sionna·p250M 21 칸 | **권 16 절 4** | 권 17 절 3 은 **`sionna_phys` 두 칸**과 대조용 `sionna/el+0`(0.290) 한 칸만 |
| `above_f_tip_frac` — `sionna_phys` 2 칸 | **권 17 절 3** | 권 16 은 물리 팔을 아예 안 든다 |
| 박자(beat) — 앙각축 7 점 | **권 16 절 4** | |
| 박자(beat) — el 0 예산 사다리 4 계단 | **권 17 절 5** | 권 16 은 예산 사다리 박자를 안 쓴다 |
| `level_db` 절대값 | **권 17 절 5**(같은 엔진 안에서만) | 권 16 은 `level_db` 를 쓰지 않는다 — 팔 사이 정규화가 다르다 |
| `npaths_median` — 앙각축 | **권 16 절 1**(교란 축임을 밝히는 용도) | |
| `npaths_median` — 스위치축 | **권 17 절 1** | |
| `npaths_median` — 예산축 | **권 17 절 5** | 세 곳 모두 **어느 축인지 이름을 함께** 적는다 |
| `elevation_sweep_md.json : rows[27]`(sionna_phys/el−90) | **권 17 절 2** | 권 16 절 5 는 우리 팔만 다룬다 |
| f_flash = 126.67 Hz 가 **입력값**이라는 정정 | **권 16 절 4** | 권 17 절 5 는 그 문장을 다시 쓰지 않고 링크한다 |

### 기존 권과 겹치는 것

| 겹치는 주장 | 기존 주인 | 새 권이 하는 일 |
|---|---|---|
| 「두 엔진이 f_tip 아래에서 겹치고 위에서 갈린다」(대역 밖 5.06 % 대 0.18 %) | 조각 36 = 권 08 | **권 16 절 4** 는 같은 주장을 **앙각 7 점**으로 확장한다. 36 의 숫자를 다시 쓰지 않고 링크만 한다 |
| 광선예산이 교란이라는 것 | 조각 42 = 권 09 | **권 17 절 5** 는 «앙각·거리 사다리» 축이고 42 는 «기체 크기 대비 예산» 축이다. 축 이름을 서로 적어 준다 |
| 자세(attitude)와 가림 | 조각 40 = 권 09 | 권 16 은 **관측 앙각**(수신 기하)이고 40 은 **기체 자세**다. 첫 절에서 낱말을 갈라 준다 |
| 스톡 엔진이 σ 를 안 낸다 | 권 02 | 권 17 절 1 은 `rt_no_rcs_verify.json` 을 **경로 수 해석의 주의**로만 쓰고, σ 주장은 권 02 로 링크한다 |

⚠ 위 원장들(`elevation_sweep_md` · `ch1_elevation_figdata` · `wideband_energy` ·
`diag_physics_paths_el-90` 등 §5-1 의 17 행)은 **기존 조각 78 편·빌더 12 개 어디에서도
인용된 적이 없다**(파일 이름 전수 grep 결과 0 건). 즉 권 16·17 은 이 원장들의 **첫 소비자**다.

---

## 9. 필요하다고만 적는 것 (⛔ 이번 라운드에서 계산하지 않는다)

| 무엇 | 그러면 결정되는 것 | 어디서 |
|---|---|---|
| ⭐**샤드 병합 한 번**(GPU 아님, CPU) — `sionna_phys` el−15·−30·−45 와 새 팔 `sionna_p250000000_phys` 는 **이미 8/8 로 디스크에 있다** | 권 17 절 3·4 가 물리 팔 두 점이 아니라 **다섯 점 이상**에서 서고, 덱 대조의 빈칸이 닫힌다 | `benchmark/elevation_sweep_md.py --merge` ⛔ 기존 원장을 덮어쓰므로 상위 판단 필요 |
| `sionna_phys` el−75 의 남은 샤드(4/8, el−60 은 04:34 에 8/8 로 참) | 물리 팔의 앙각 곡선이 우리 팔과 같은 7 점에서 비교된다 | 지금 GPU 3 에서 도는 중 |
| `ours --els -90 --range` 평면파 한 판 | 나딧 잔여의 근접장 몫과 격자 몫이 직접 갈린다 | 권 16 절 5 |
| 앙각 −60 ~ −75° 사이 5 점 | 고정 대역이 바닥에 닿는 앙각이 15° 격자 안에서 특정된다 | 권 16 절 2 |
| `ours_free`(동체 가림 없는 대조군) | 커버리지 감소가 cos(el) 때문인지 가림 때문인지 갈린다 | 권 16 절 1 |
| 시드를 판마다 8 개 이상 | 40 m 예산 사다리의 «폭이 줄었다» 가 통계적 주장이 된다 | 권 17 절 5 |

---

## 10. 다음 단계

| 다음에 할 일 | 그러면 결정되는 것 | 어디서 |
|---|---|---|
| 조각 빌더 `src/build_part12_elevation.py`(78~82)·`src/build_part13_physics.py`(83~87) 를 짓는다 | 권 16·17 의 본문 숫자가 원장에 묶인다 | 이 문서 §5·§7 |
| 각 빌더 끝에서 샤드 10 개를 `outputs/reports_index/` 에 쓴다 | `ref()` 와 링크 검사가 새 앵커를 안다 | §2-2 |
| `src/build_volumes.py` 에 튜플 둘을 붙이고 «열다섯» 12 자리를 고친다 | `reports/16_*.ipynb` · `17_*.ipynb` 와 지도·목차가 선다 | §2-1 |
| `PYTHONPATH=src python benchmark/check_report_links.py` 를 돌린다 | 끊긴 링크·모르는 앵커·안 열리는 출처가 0 인지 정해진다 | 마지막 단계 |
