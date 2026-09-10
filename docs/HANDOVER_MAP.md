# 규약이 어디에 있나 — 한 장 지도

새로 들어온 사람이 **무엇을 어디서 읽어야 하나**만 적는다. 규약 자체는 여기 안 옮긴다
(옮기면 두 벌이 되고 곧 갈린다). 이 문서는 **목차**다.

만든 날 2026-09-10. ⛔이 문서를 고칠 때는 링크가 살아 있는지 함께 본다.

---

## 0. 처음 30 분

| 순서 | 읽을 것 | 무엇이 있나 |
|---|---|---|
| 1 | [`CLAUDE.md`](../CLAUDE.md) | **상시 규약 전부.** 주장 게이트 · 그림 · 레포트 · 팀미팅 경계 · 그 밖 |
| 2 | [`docs/CLAIM_GATE.md`](CLAIM_GATE.md) | 숫자를 올리기 전에 통과시키는 두 축(사실 뒷받침 · 과잉 결론) |
| 3 | [`docs/QUEUE_RUNBOOK.md`](QUEUE_RUNBOOK.md) | 큐를 돌리는 법. **2 단 구조(지킴이 + 감독자)** 는 1 절 |
| 4 | `work/sweep_0904/RESUME_<가장 최근>.md` | 어제까지 무슨 일이 있었나. **여기가 매일의 인계다** |

---

## 1. 규약 — 어느 문서가 무엇을 맡나

| 문서 | 맡는 것 | ⛔놓치면 사고 나는 것 |
|---|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | 상시 규약의 **본체** | 말을 지어내지 않는다 · 죽는 경로를 소스에 박지 않는다 · CPU 전용은 GPU 숨김 |
| [`docs/CLAIM_GATE.md`](CLAIM_GATE.md) | 주장 게이트 | 머리기사 숫자는 손잡이를 흔들어 보고 낸다 |
| [`docs/NEW_FILE_RULES.md`](NEW_FILE_RULES.md) | 새 파일·원장이 지켜야 할 것 | 관문 `benchmark/check_new_file_rules.py` 가 이걸 강제한다 |
| [`docs/GATES_0902.md`](GATES_0902.md) | 인용을 막아 둔 자리 | el 0° 빈 하늘 기록은 인용이 막혀 있다 |
| [`docs/EQUIVALENCE_GATES.md`](EQUIVALENCE_GATES.md) | 「같다」고 말해도 되는 조건 | |
| [`../team_meeting/DECK_CONVENTION.md`](../../team_meeting/DECK_CONVENTION.md) | 덱 문면 | ⛔우리끼리 쓰는 말 금지(0 순위) · 제목은 이름이지 설명이 아니다 |
| [`../team_meeting/CLAUDE.md`](../../team_meeting/CLAUDE.md) | 덱 작업 전반 | 덱은 **매번 새 버전**으로. 옛 판을 덮어쓰지 않는다 |
| [`docs/RETRACTION_LOG.md`](RETRACTION_LOG.md) | 내린 주장 목록 | 인용 전에 여기 있는지 본다 |

⭐**판독기·빌더의 머리말도 규약이다.** 각 스크립트 첫 30 줄에 「이것이 답하지 않는 것」이
적혀 있고, 그것이 그 원장을 읽는 규칙이다. 원장만 보고 인용하지 않는다.

---

## 2. 큐 — 잡 하나가 도는 데까지

```
① runners/make_jobs_XXXX.py   물음·죽는조건·안답함을 적고 잡 줄을 낸다
② runners/jobs_XXXX.txt        python make_jobs_XXXX.py > jobs_XXXX.txt
③ runners/filter_jobs.sh       ⭐발주 전 반드시 — NEW · DONE · STALE 로 가른다
④ runners/queue_chain_XXXX.txt ⛔파일을 먼저 만든 뒤 여기 적는다
⑤ runners/queue_keeper_0827.sh 감독자가 0 명일 때 사슬의 다음 줄을 띄운다
⑥ runners/worker_supervisor.py 한 큐를 돌린다. GPU 배분·상한을 지킨다
⑦ benchmark/elevation_sweep_md.py  실제 계산 → outputs/elev_sweep_shards/*.npz
```

- 자세한 것은 [`docs/QUEUE_RUNBOOK.md`](QUEUE_RUNBOOK.md) 1~9 절.
- ⛔`pgrep -f` 를 쓰지 마라 — 같은 명령줄에 그 이름이 있으면 **제 셸이 죽는다**(exit 144).
  런북 4 절의 `sup()`·`wrk()` 를 쓴다.
- 감독자는 큐를 **시작할 때 읽는다** — 도는 중에 잡 파일을 고쳐도 안 읽는다.
- 사슬이 마르면 지킴이가 **스스로 종료**한다. 마르기 전에 다음 잡 파일을 만들어 둔다.

---

## 3. 자료 — 어디에 무엇이 쌓이나

| 자리 | 무엇 | 읽는 법 |
|---|---|---|
| `outputs/elev_sweep_shards/*.npz` | 앙각 훑기 **샤드**(자세별 복소 전계) | 여러 장이 `idx` 로 엇갈려 채워진다 — **idx 로 정렬해야** 시간열이 된다 |
| `outputs/elevation_sweep_md.{json,npz}` | 그 샤드를 병합한 **원장** | 행마다 `fc_hz`·`f_tip_hz` 가 다르다. 기본값으로 일괄 계산하지 않는다 |
| `outputs/*.json` | 판독기·빌더가 낸 원장 | `_meta.generator` 에 **다시 굽는 법**이 적혀 있다 |
| `outputs/figures/` · `atlas/` | 그림·도감 | ⛔손으로 고치지 않는다 — 빌더를 고치고 다시 굽는다 |
| `reports/*.ipynb` | 레포트 | ⛔레포트는 **주피터 노트북**이다. 웹 페이지로 내지 않는다 |

⭐샤드 한 장의 키: `idx` · `E` · `meta`(앙각·샤드·나눔·자세수·PRF·초) · `cfg`,
Sionna 팔은 `npaths`·`nret`·`E_dedup`·`n_dup`·`n_trunc` 가 더 붙는다.
⚠`n_trunc` 는 [상한 근접 자세 수, 그때 쓴 상한] 두 칸이고 **구울 때의 문턱**으로 센 값이다 —
문턱이 0.999 → 0.99 로 내려간 적이 있어 세대가 섞여 있다. 그대로 인용하지 말고
저장된 `nret` 과 저장된 상한으로 다시 센다(`benchmark/read_canyonnull_0910.py` 참고).

---

## 4. ⛔지금 살아 있는 한계 — 인용 전에 반드시

- **실기 계측 대조는 0 건이다.** 어떤 결과도 「검증됐다」로 읽히게 쓰지 않는다.
- 「우리 커널이 맞고 Sionna 가 틀렸다」로 결론짓지 않는다 — 둘 다 근사다.
- 광선 예산 ±5 % 는 **널이 아니다.** 초기 광선이 씨앗 없는 결정적 격자라 되풀이는 재현성이고,
  예산 변경은 「격자를 갈았을 때의 민감도」다. 신뢰구간도 판정 문턱도 아니다.
- 상한이 결과를 정하면 그 축은 접는다(경로 수가 상한을 따라가면 못 잰다).
- σ(dBsm) 인용 금지 · 두 엔진의 절대 레벨 비교 금지.

---

## 5. 매일 하는 것

1. 큐 상태를 본다 — 런북 4 절 `sup()`·`wrk()` 와 감독자 로그 꼬리.
2. 새로 떨어진 샤드를 **`np.load` 로 열어 확인한 뒤** 커밋한다(2 분 안에 쓰인 것은 뺀다).
3. 사슬이 얼마나 남았나 본다. 마르기 전에 다음 잡 파일을 만든다.
4. 그날 한 일을 `work/sweep_0904/RESUME_<날짜>.md` 에 적는다 — **다음 사람이 여기부터 읽는다**.
5. 팀미팅 산출물은 그 자리에서 commit + push(`/workspace/team_meeting`).
