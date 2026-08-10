# 리포트 편성 — 조각 78 편에서 열다섯 권으로

이 문서는 `reports/` 아래가 **왜 이런 모양인가**와 **어떻게 다시 만드나**를 적는다.
사람이 읽는 목차는 [`reports/README.md`](../reports/README.md) 이고, 기계용 색인은
[`outputs/volumes_index.json`](../outputs/volumes_index.json) 이다.

---

## 1. 지금의 모양

```
reports/
  README.md              ← 목차 (생성물)
  01_map.ipynb           ← 사람이 읽는 문서. 한 권 = 한 파일
  02_stock-engine.ipynb
  …
  08_1_scene.ipynb       ← 8 권만 네 편이다 (아래 §4)
  08_2_engines.ipynb
  08_3_pattern.ipynb
  08_4_sampling.ipynb
  …
  15_measurement.ipynb
  _parts/                ← ⛔ 사람이 읽는 문서가 **아니다**
    00_map.ipynb …  77_size-law-differential.ipynb   (조각 78 편)
```

두 층이다.

| 층 | 무엇 | 누가 만드나 | 사람이 읽나 |
|---|---|---|---|
| **조각** `reports/_parts/NN_slug.ipynb` | 주제 하나짜리 짧은 편. 숫자는 전부 원장 JSON 에서 주입된다 | `src/build_partNN_*.py` 12 개 | ❌ 아니다 — 재료다 |
| **권** `reports/NN_slug.ipynb` | 물음 하나에 답하는 문서. 조각을 절로 품는다 | `src/build_volumes.py` | ✅ 이것을 읽는다 |

---

## 2. 왜 이렇게 됐나

편을 «한 편 = 한 메시지» 로 쪼개다 보니 78 편이 됐다. 그 숫자로는 목차가 지도 구실을 못 한다.
사용자 지시는 이랬다.

> *"레포트를 지금 너무 심하게 잘게 쪼갠 거 같은데... 그래도 적당히 **하나의 메시지를 담아서**
> 해주면 좋겠어. … 지금 77 개로 쪼갠 것은 너무 과해"*

그래서 **조각을 다시 쓰지 않고 그 위에 묶는 층을 얹었다.** 조각의 숫자는 원장 JSON 에서
주입된 것이라, 손으로 합치면 «원장이 바뀌면 본문이 따라 바뀐다» 는 사슬이 끊긴다.
묶는 층은 조각을 **읽어서** 순서대로 잇고, 각주와 주소만 손댄다.

⭐ **분량 상한은 두지 않는다.** 예전 규약의 셀 수 상한(`report_style.MAX_MD_CELLS`)은
폐지됐고(`None`), 새 상한도 만들지 않는다. 권의 길이는 그 권이 답하는 물음의 크기가 정한다.

---

## 3. 묶는 층이 하는 일 다섯

`src/build_volumes.py` 가 조각을 이을 때 손대는 것은 이것뿐이다.

| 무엇을 | 왜 |
|---|---|
| **각주 재번호** | 조각마다 `[^1]` 부터 다시 센다. 그냥 이으면 한 편 안에서 번호가 겹친다. 조각을 이을 때 그 앞까지의 최대 번호만큼 밀어 **정의와 인용을 함께** 옮긴다 |
| **상호참조 재배선** | 조각 본문의 `[편 22 «…»](22_po-knee.ipynb)` 는 78 편 시절의 주소다. 조각은 이제 `_parts/` 에 살고 사람이 여는 문서가 아니므로, 배치표에서 찾아 새 주소로 고친다 |
| **지도 권 생성** | 1 권의 절 1 은 조각이 아니라 이 스크립트가 짓는다 (아래 §5) |
| **8 권 후처리** | 다른 빌더가 낸 네 편의 주소를 고치고, 옛 부 7 조각을 `08_3_pattern.ipynb` 뒤에 절로 덧붙인다 (아래 §4) |
| **색인·목차** | `outputs/volumes_index.json` 과 `reports/README.md` |

### 재배선 규칙

| 조각이 들고 있던 옛 주소 | 바뀌는 모양 |
|---|---|
| `[편 22 «…»](22_po-knee.ipynb)` — 다른 편을 가리킴 | `[리포트 5 절 5 «…»](05_kernel.ipynb)` |
| `[편 22 «…»](22_po-knee.ipynb)` — 같은 편 안 | `**절 5** «…»` (자기 파일로 되돌아가는 링크를 안 만든다) |
| `` `reports/37_md-rpm.ipynb` `` (인라인 코드) | `[리포트 8 절 4](08_3_pattern.ipynb)` |
| `[부 4 «산란 커널»](../README.md#부-4-…)` | `[리포트 5 «산란 커널»](05_kernel.ipynb)` |
| 산문의 `부 7 의 표지다` | `리포트 8 의 표지다` |

⚠ **권 파일 이름도 `NN_slug.ipynb` 꼴이다.** 번호만 보고 고치면 이미 새 주소로 적힌 글을
옛 주소로 오인해 망가뜨린다. 그래서 `_is_part_name()` 이 **슬러그까지 조각 파일명과 대조**해서,
실제로 조각을 가리킬 때만 고친다.

---

## 4. 8 권만 네 편인 이유

한 권이 한 파일인 것이 규칙인데 8 권만 예외다. 마이크로도플러는 애니메이션과 스펙트로그램이
노트북 안에 그림으로 박혀 있어(base64) 한 파일에 담으면 **열리지 않는다.**
나누는 축은 분량이 아니라 물음이라, 네 편이 각각 하나씩 답한다.

| 편 | 무엇에 답하나 |
|---|---|
| `08_1_scene.ipynb` | 무엇을 보고 있나 — 시나리오와 신호의 정체 |
| `08_2_engines.ipynb` | 어떻게 계산하나 — 세 엔진과 거리 |
| `08_3_pattern.ipynb` | 무엇이 무늬를 정하나 — 회전수·가림·산포 |
| `08_4_sampling.ipynb` | 무엇을 잴 수 있나 — 광선 비용과 반복률 |

이 네 편은 **`src/make_report08_microdoppler.py`** 가 만든다. `build_volumes.py` 는 그 파일들을
만들지 않고, **주소만 고치고** 옛 부 7 조각(34~39)을 `08_3_pattern.ipynb` 뒤에 절로 덧붙인다 —
«무엇이 무늬를 정하나» 라는 같은 물음에 답하기 때문이다.

⭐ 덧붙인 셀에는 `metadata.tags = ["from_parts"]` 표식이 붙는다. 다시 돌리면 그 표식이 붙은
셀을 **먼저 걷어내고** 새로 붙이므로, 몇 번을 돌려도 겹쳐 쌓이지 않는다.

---

## 5. 1 권 절 1 «지도» 는 왜 생성물인가

옛 조각 `_parts/00_map.ipynb` 는 «편 78 개 · 부 12 개» 라는 **폐지된 편성 자체를 설명하는 글**
이다. 번호만 고쳐서는 말이 서지 않으므로 권에 넣지 않았다. 그 자리는 `build_volumes.py` 가
편성과 디스크에서 다시 지은 지도가 대신한다 — 열다섯 권 목차, 조각→절 환산표, 읽는 경로,
규약 다섯.

그 조각의 빌더(`src/build_part00_map.py`)는 지우지 않았다. 지우는 판단은 조각 빌더의 소관이다.

---

## 6. ⭐규약 — 조각을 손으로 고치지 마라, 빌더를 고쳐라

이 편성이 서 있는 조건은 하나다. **본문의 숫자가 원장 JSON 에서 온다는 사슬이 안 끊기는 것.**

| 고치고 싶은 것 | 고칠 곳 | 안 되는 곳 |
|---|---|---|
| 절의 본문·숫자·각주 | 그 조각을 만든 `src/build_partNN_*.py` | ⛔ `reports/_parts/*.ipynb` · ⛔ `reports/NN_*.ipynb` |
| 권 구성·순서·제목·논지 | `src/build_volumes.py` 의 `VOLUMES` | ⛔ 권 노트북 |
| 8 권 네 편의 본문 | `src/make_report08_microdoppler.py` | ⛔ `reports/08_*.ipynb` |
| 목차·색인 | `src/build_volumes.py` | ⛔ `reports/README.md` · ⛔ `outputs/volumes_index.json` |

조각이나 권을 손으로 고치면 **다음 빌드에서 조용히 사라진다.** 사라지지 않더라도 더 나쁘다 —
본문 숫자와 원장이 갈라져도 아무도 모른다.

---

## 7. 다시 만드는 절차

순서가 중요하다. ③ 이 ② 의 산출물 뒤에 절을 덧붙이기 때문이다.

```bash
# ① 조각 빌더 12 개  → reports/_parts/NN_slug.ipynb
PYTHONPATH=src python src/build_part00_map.py
PYTHONPATH=src python src/build_part01_stock_engine.py
#  … build_part02_prior_work.py … build_part11_measurement.py

# ② 8 권 네 편        → reports/08_1_scene.ipynb … 08_4_sampling.ipynb
PYTHONPATH=src python src/make_report08_microdoppler.py

# ③ 조각 → 권         → reports/NN_slug.ipynb + 08 권 후처리 + 색인 + reports/README.md
PYTHONPATH=src python src/build_volumes.py

# ④ 검사
PYTHONPATH=src python benchmark/check_report_links.py
```

②가 아직 없으면 ③ 은 8 권 후처리를 **조용히 건너뛰고 경고만** 찍는다 — 빌드가 죽지 않는다.

---

## 8. 검사에서 무엇을 보나

`benchmark/check_report_links.py` 가 끊긴 링크·그림·출처를 센다. 그 밖에 편성 자체를 볼 때는
색인을 읽으면 된다.

| 봐야 하는 것 | 어디서 |
|---|---|
| 권마다 셀·각주·그림 수 | `outputs/volumes_index.json` → `volumes[].cells/footnotes/figures` |
| 어느 조각이 어느 권 몇 절인가 | `outputs/volumes_index.json` → `parts` (또는 1 권 절 1 의 환산표) |
| 권에 안 들어간 조각과 그 사유 | `outputs/volumes_index.json` → `superseded_parts` |
| 각주가 권 안에서 유일한가 | 정의(`[^n]:` · 출처 표 행)와 인용을 세어 중복·미정의·미인용이 0 인지 |

### ⚠ 알려진 검사 도구 결함 (2026-08-10 · 이 문서의 소관 밖)

`benchmark/check_report_links.py` 의 그림 정규식이 base64 그림을 못 알아본다.

```python
_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+?)[^)]*\)")   # ← 게으른 +? 가 'd' 만 잡는다
```

`![x](data:image/png;base64,…)` 에서 `data:` 대신 `d` 를 캡처하고, `d` 는 `data:` 로 시작하지
않으므로 **없는 그림**으로 신고한다. 8 권 네 편의 그림이 전부 base64 라 14 건이 그렇게 잡힌다.
고칠 곳은 한 줄이다.

```python
_IMG = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
```
