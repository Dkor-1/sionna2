# 전수조사 2026-09-04 — 끊겨도 여기서 이어간다

> ⭐**새 세션이면 이 파일부터 읽는다.** 샤드는 `/tmp` 세션 스크래치패드에만 있었어서
> 세션이 끊기면 사라진다. 아래 ①만 돌리면 **같은 샤드가 그대로 다시 나온다.**

## 왜 하고 있나

사용자 요청(2026-09-04): *「진짜 모든 문서 파일 레포트 코드 한 줄 한 줄 다 전수 조사해달라는
의미야. 오래걸리더라도 수행해줘」*

⛔**그 앞에 있던 「전수조사」는 전수가 아니었다.** 2026-09-04 오전 판(워크플로 `w70eyfnmb`)은
여섯 영역을 **표본**으로 훑어 74 건을 30 건으로 추린 것이고, 그 보고서 자신이 「전수가
아니다」라고 적었다. `prior_work/ · report_mesh/ · jihyuck/ · refs/ · work/` 는 **한 번도**
들여다보지 않았다. 그 30 건은 이미 고쳐 커밋했다(아래 «이미 고친 것»).

## 무엇을 찾나 — 여덟 가지

① 판정형·최상급 ② 범위 없는 절대수 ③ 부재증명 ④ 철회값 재인용 ⑤ 추론을 관측처럼
⑥ 지어낸 말 ⑦ 자기모순 ⑧ 표본·범위 누락

규약 원문: `docs/CLAIM_GATE.md` · `CLAUDE.md` · `docs/REBUILD_2026-07-30.md` §5

## ① 샤드를 다시 만든다 (2 분)

```bash
cd /workspace/sionna
CUDA_VISIBLE_DEVICES="" python3 work/sweep_0904/make_shards.py
#   → work/sweep_0904/shards/  ·  work/sweep_0904/SHARDS.json
```

⭐마지막 줄이 **「✅ 손실 없음」** 이어야 한다. 그리고 id 범위가 아래와 같아야 한다 —
다르면 저장소가 그 뒤로 바뀐 것이니 STATE 를 새로 적고 물결을 처음부터 돌린다.

| 묶음 | 샤드 id | 개수 | 무엇 |
|---|---|---|---|
| A 발행면 | `0~63` | 64 | docs · reports · atlas · 루트 md |
| B 코드 | `64~147` | 84 | src · benchmark · runners |
| C 원장 | `148~250` | 103 | outputs |
| D 미조사 | `251~270` | 20 | prior_work · report_mesh · jihyuck · archive · refs · work |
| E 영문 | `271~307` | 37 | 한국어가 없는 영문 산문 전부 |

## ② 물결을 돌린다

⚠**워크플로 스크립트 안의 `DIR` 이 `/tmp/.../scratchpad/shards` 를 가리킨다.**
새 세션에서는 `work/sweep_0904/shards` 로 고친 뒤 돌린다.

```
Workflow({ scriptPath: "work/sweep_0904/sweep_workflow.js",
           args: { ranges: [[0,63],[251,270]] } })      # 물결 1 — 발행면 + 미조사
Workflow({ scriptPath: "work/sweep_0904/sweep_workflow.js",
           args: { ranges: [[64,147],[148,250]] } })    # 물결 2 — 코드 + 원장
Workflow({ scriptPath: "work/sweep_0904/sweep_workflow.js",
           args: { ranges: [[271,307]] } })             # 물결 3 — 영문
```

샤드마다 **읽기 → 적대적 재검증** 두 단이다. 확인자는 «깎아내는 쪽» 이고 원본을 직접 열어
인용 대조·⛔표시 확인·원장 재계산을 하며 **의심스러우면 기각**한다.

## ③ 결과가 나오면

1. ⭐**에이전트 말을 그대로 믿지 않는다.** 건마다 `grep` 으로 원문을 다시 뜨고, 「틀렸다」고
   적힌 수는 원장을 열어 직접 다시 계산한다. 지난 라운드에 에이전트 지적 일곱 건이 근거
   부족으로 떨어졌다.
2. 고치는 자리는 **빌더**다 — `src/build_part*.py` · `benchmark/*.py`. ⛔노트북을 손으로
   고치지 않는다(`reports/*.ipynb` 은 `src/build_volumes.py` 가 조립한다).
3. 치환은 **하나하나 따로 확인**한다. 파일 전체로 `s != o` 만 보면 두 치환 중 하나가 조용히
   실패한 것을 놓친다(2026-09-04 에 실제로 그랬다).
4. 재빌드 → 관문 셋 → commit + push.

```bash
export CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark
PY=/workspace/.venvs/py312/bin/python          # ⚠ ~/.venvs 아니다. trimesh 는 여기만 있다
for f in src/build_part*.py; do $PY "$f"; done
$PY src/build_volumes.py && $PY src/make_readme.py && $PY src/make_reports_index.py
$PY benchmark/check_report_links.py            # 링크·그림·출처
$PY benchmark/check_row_pointers.py            # 각주가 제 행을 가리키나
$PY benchmark/check_retracted.py               # ⭐철회한 수가 발행면에 다시 인용됐나
```

## 이미 고친 것 — 다시 보고하지 않는다

커밋 `d5568807` 「전수조사 정정 — 철회한 수가 발행면에 남아 있던 자리 40 건 + 관문 하나」.
목록은 `sweep_workflow.js` 의 `ALREADY_FIXED` 상수에 그대로 있다(에이전트에게 넘긴다).

## ⛔밟으면 안 되는 지뢰 — 2026-09-04 에 실제로 밟았다

| 지뢰 | 무슨 일이 났나 |
|---|---|
| `src/make_report11_2_two_channel.py` 를 그냥 돌림 | 아카이브로 내린 **챔버 편이 되살아났다.** 지금은 `SIONNA_ALLOW_CHAMBER=1` 없이 멈춘다 |
| `benchmark/geometry_grid.py` 재실행 | 입력 `report13_sigma_grid.json` 이 `multistatic` 블록을 잃어(8/10 라운드) **원장이 비었다.** 되돌렸다. 이 빌더와 `geometry_benchmark.py` 는 지금 **못 돈다** |
| `git checkout -- <파일>` 로 시험 되돌리기 | 같은 파일에 있던 **내 정정까지 날아갔다**(`docs/GATES_0902.md`). 시험은 사본으로 한다 |
| 에이전트에게 «빌더를 돌려라» 라고 시킴 | 빌더가 노트북을 쓴다 → 작업 트리 317 경로가 더러워졌다. **조사자는 읽기만** 시킨다 |
| `~/.venvs/py312/bin/python` | 없는 경로다. `/workspace/.venvs/py312/bin/python` 이다 |

## 상시 규약 (CLAUDE.md 요약 — 어기면 발표에서 사고난다)

- 확산(F 비트)은 **모든 팔에서 항상 켠다**. F0 계열은 발주하지 않는다
- 프로펠러 단독(`--parts prop`)은 더 이상 만들지 않는다(있는 데이터 인용은 별개)
- 「우리 커널이 맞고 PathSolver 가 틀렸다」로 **결론짓지 않는다** — 둘 다 근사, 실측 대조 0 건
- 환경은 **실외만**. ⛔챔버는 슬라이드·그림·각주 어디에도 넣지 않는다
- ⛔우리끼리 쓰는 말을 덱에 넣지 않는다 · ⛔⛔**말을 지어내지 않는다**(모든 자리에서)
- el 0 「레벨·폭」은 인용 금지(`docs/GATES_0902.md`)
- 리듬 몫 절대값은 자유 파라미터를 타므로 **크기를 인용하지 않는다**(RETRACTION_LOG R29)
- CPU 전용 작업은 `CUDA_VISIBLE_DEVICES=""` 로 띄운다
- 팀미팅 산출물은 즉시 commit + push
