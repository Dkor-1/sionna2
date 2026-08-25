# 큐 직접 돌리기 — 터미널 런북

> 감독자(`runners/worker_supervisor.py`)와 워커(`benchmark/elevation_sweep_md.py`)를
> **직접** 짜고 돌리고 멈추는 법. 2026-08-25 기준, 지금 돌고 있는 그 코드 기준으로 썼다.

```bash
# 어디서든 이 두 줄로 시작
cd /workspace/sionna
PY=/workspace/.venvs/py312/bin/python
```

---

## 1. 구조 — 누가 무엇을 하나

```
jobs.txt  ──►  worker_supervisor.py  ──►  elevation_sweep_md.py  ──►  outputs/elev_sweep_shards/*.npz
 (한 줄 =        (큐를 혼자 읽고            (실제 계산. GPU 하나                (샤드 파일)
  잡 하나)        워커를 띄운다)             를 잡고 돈다)
```

- **감독자는 하나만** 돈다. 큐를 혼자 읽어 나눠 주므로 둘 띄우면 **같은 잡이 중복 배정**된다.
- 감독자는 **워커를 죽이지 않는다**(저장소 규칙, 0811 사고). 줄일 때는 «끝난 자리를 안 채우는»
  방식으로만 줄인다.

---

## 2. 잡 파일 쓰기

한 줄이 잡 하나이고, 그 줄이 그대로 `elevation_sweep_md.py` 의 인자가 된다.
`#` 로 시작하는 줄과 빈 줄은 건너뛴다.

```bash
cat > runners/jobs_mine.txt <<'EOF'
# 내 큐 — 2026-08-25
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro \
  --range-m 15 --n-poses 8192 --els=0,-30 --shard 0 --nshards 2 --inmem
--engine sionna --spp 4000000000 --sw R0D1E1F1 --max-depth 2 --drone mini5pro \
  --range-m 15 --n-poses 8192 --els=0,-30 --shard 1 --nshards 2 --inmem
EOF
```

⚠**한 줄은 반드시 한 줄로.** 위 예시의 `\` 줄바꿈은 셸 히어독에서만 이어지지, 감독자는
파일을 **줄 단위**로 읽는다. 안전하게 하려면 그냥 길게 한 줄로 쓴다.

### 자주 쓰는 인자

| 인자 | 뜻 |
|---|---|
| `--sw R?D?E?F?` | 물리 스위치. **R**=굴절 **D**=회절 **E**=모서리회절 **F**=확산. `R0D1E1F1` = 굴절만 끔 |
| `--els=0,-30` | 앙각 목록. **잡 하나가 여기 적힌 앙각을 전부 돈다** → 파일도 그만큼 나온다 |
| `--shard k --nshards n` | 자세를 n 등분해 k 번째만. **자세를 건너뛰며** 나눠 가진다 |
| `--n-poses 8192` | 자세 수 |
| `--range-m 15` · `--drone mini5pro` | 거리 · 기체 |
| `--spp 4000000000` | 광선 수 |
| `--max-depth 2` | 반사 깊이. ⛔회절 켠 조합에서 3 을 빼면 안 된다(R13) |
| `--inmem` | 중간 파일 없이 메모리에서. 지금 큐가 쓰는 방식 |
| `--overwrite` | 이미 있는 샤드도 **다시** 계산 |
| `--dry-run` | 계산 없이 «있음/없음»만 출력 |

### ⭐돌리기 전에 반드시 — 무엇이 이미 있는지 본다

워커는 **이미 있는 샤드를 건너뛴다**(`--overwrite` 없으면). 그래서 큐를 다시 짜도
끝난 일은 다시 안 한다. 미리 확인하려면:

```bash
while read -r line; do
  [ -z "$line" ] && continue; case "$line" in \#*) continue;; esac
  $PY benchmark/elevation_sweep_md.py $line --dry-run
done < runners/jobs_mine.txt
```

---

## 3. 띄우기

```bash
setsid nohup $PY runners/worker_supervisor.py \
  runners/jobs_mine.txt \
  /workspace/sionna/runners/logs/sup_mine.log \
  >/dev/null 2>&1 &
echo "감독자 pid $!"
```

- `setsid` 가 핵심이다 — 터미널이나 SSH 가 끊겨도 계속 돈다.
- 로그 경로를 생략하면 `runners/logs/supervisor.log` 로 간다.

### 자원 규율 — 환경변수로 조인다

기본값은 이 컨테이너에 맞춰 이미 보수적이지만, **더 조이고 싶으면** 앞에 붙인다:

```bash
SIONNA2_CPUS=8 SIONNA2_RAM_GB=24 SIONNA2_MAX_TOTAL=4 SIONNA2_HARD_TOTAL=6 \
SIONNA2_THREADS=2 \
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &
```

| 변수 | 기본 | 뜻 |
|---|---|---|
| `SIONNA2_MAX_TOTAL` | 8 | 목표 배분의 **예산** 상한(투입 차단선이 아니다) |
| `SIONNA2_HARD_TOTAL` | 12 | **절대선**. 이걸 넘겨선 안 띄운다 |
| `SIONNA2_THREADS` | 2 | 워커당 스레드. ⛔올리지 말 것 — 스레드 폭주의 원인 |
| `SIONNA2_CPUS` | 자동 | 우리 몫 CPU 코어 수. CPU 브레이크의 분모 |
| `SIONNA2_RAM_GB` | 자동 | 우리 몫 RAM. 컨테이너 천장은 32 GiB |
| `SIONNA2_EXCLUDE_GPUS` | 없음 | `"0,3"` 처럼. 절대 안 쓸 카드 |

**안전선**(코드 상수, 환경변수 아님): RAM 여유 `6 GB` 아래거나 우리 CPU 사용률이
`0.85` 를 넘으면 **새로 안 띄운다**(돌던 것은 계속 돈다).

---

## 4. 지켜보기

```bash
# 지금 상태 한 줄
tail -1 runners/logs/sup_mine.log

# 흐르는 대로
tail -f runners/logs/sup_mine.log

# 워커가 뱉는 진행률
tail -f runners/logs/sup_mine.log.workerout
# 워커 오류
tail -f runners/logs/sup_mine.log.workererr
```

로그 한 줄은 이렇게 생겼다:

```
[08-25 13:40] 상태 G0:2/2(상한3·남0G) ... · 큐 25/48 · 워커 4 · RAM 16.9G · CPU 0.88 · ⛔대기: ...
                    └ 카드별 현재/목표      └ ⚠«투입 포인터» 지 완료 수가 아니다
```

### ⛔진척은 «샤드» 로 읽는다 — 이게 제일 헷갈린다

- `큐 25/48` 은 감독자가 **몇 번째 잡을 꺼내 갔나**(투입 포인터)다. 완료 수가 **아니다**.
- 잡 하나가 `--els=a,b` 로 앙각 둘을 돌면 **파일이 2 개** 나온다.
  그래서 48 잡짜리 큐의 총량은 샤드 **96** 개다.
- `outputs/elev_sweep_shards/` 에는 **옛 실행분이 잔뜩 섞여 있다**(지금 4,300 개 넘는다).
  내 큐 몫만 세려면 **감독자 시작 시각 이후 mtime** 으로 거른다:

```bash
SUP=$(pgrep -f 'runners/worker_supervisor.py' | head -1)
T0=$(( $(date +%s) - $(ps -o etimes= -p $SUP | tr -d ' ') ))
echo "내 큐가 낸 샤드: $(find outputs/elev_sweep_shards -name '*.npz' -newermt "@$T0" | wc -l)"
```

⚠`find -newermt '2026-08-25 16:40'` 처럼 **사람이 읽는 시각**을 쓰면 함정이다 —
컨테이너 시계는 UTC 인데 머릿속은 KST 라 9 시간이 어긋난다. 위처럼 `@epoch` 를 쓰거나
`touch -d` 로 기준 파일을 만들어 `-newer` 를 쓴다.

### 건강 확인 (좀비·고아)

```bash
echo "감독자 $(pgrep -fc 'runners/worker_supervisor.py') · 워커 $(pgrep -fc 'benchmark/elevation_sweep_md.py') · 좀비 $(ps -eo stat= | grep -c '^Z')"
# 워커의 부모가 전부 감독자인지 (고아 검사)
for p in $(pgrep -f 'benchmark/elevation_sweep_md.py'); do
  echo "  $p ← ppid $(ps -o ppid= -p $p | tr -d ' ')"
done
```

⚠**자기 셸이 같이 잡힌다.** `pgrep -f` 는 명령줄 문자열을 보므로 위 명령을 담은 셸도
매칭된다. 개수가 하나 많게 나오면 대개 그것이다 — `ps -o args=` 로 확인한다.

---

## 5. 멈추기 — ⛔여기가 제일 위험하다

```bash
SUP=$(pgrep -f 'runners/worker_supervisor.py' | head -1)
kill -TERM $SUP          # ⭐한 번만
```

| 신호 | 무슨 일이 일어나나 |
|---|---|
| **1 번** | 새로 안 띄우고 **돌던 워커가 끝나기를 기다린다.** 이게 정상 종료다 |
| **2 번** | ⛔**배수를 끊고 나간다. 워커는 계속 돈다 → 고아가 된다.** 정말 급할 때만 |

두 번 보내면 감독자가 `runners/logs/orphans_handoff.txt` 에 pid↔잡 대응을 남긴다.
그 파일로 나중에 추적해 정리할 수 있지만, **애초에 두 번 보내지 않는 게 맞다.**

워커 하나가 앙각 2 개면 **몇 시간** 돈다. 정상 종료가 오래 걸리는 건 정상이다.

⛔**워커를 직접 `kill` 하지 않는다.** 저장소 규칙이다(0811 사고). 중간에 죽이면 샤드가
안 써지고, 다음 실행이 «없음» 으로 보고 처음부터 다시 한다.

---

## 6. 잡을 더 넣고 싶을 때

⛔**잡 파일은 감독자가 뜰 때 한 번만 읽는다.** 돌아가는 중에 파일에 줄을 추가해도
**안 읽는다.** 방법은 하나다:

```bash
kill -TERM $SUP                      # 1) 한 번만. 워커가 끝날 때까지 기다린다
# ... 워커가 다 끝날 때까지 기다린 뒤 ...
vi runners/jobs_mine.txt             # 2) 줄 추가
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &   # 3) 다시 띄운다
```

**끝난 잡은 다시 안 한다** — 워커가 샤드 존재를 보고 건너뛴다. 그러니 옛 줄을 지울 필요 없이
**그대로 두고 새 줄만 붙이면** 된다.

---

## 7. 결과 합치기

샤드는 흩어져 있다. 하나로 합칠 때:

```bash
$PY benchmark/elevation_sweep_md.py --merge ...   # 인자는 합칠 대상과 같게
```

⛔⛔**샤드를 직접 이어붙이지 말 것.** 샤드는 자세를 **건너뛰며** 나눠 갖는다 —
각 파일의 `idx` 가 자세 번호이고 `meta[3]` 이 전체 자세 수다. 그냥 `concatenate` 하면
① 시간 순서가 깨져 리듬이 사라지고 ② 팔끼리 자세 정렬이 어긋난다.
(2026-08-24 실측: 이어붙인 판이 el −30 을 2.47 % 로 냈는데 정본은 80.5 % 였다.)

올바른 재조립은 **제자리에 흩뿌리기**다:
```python
E = np.zeros(int(np.asarray(d["meta"], float)[3]), complex)
E[np.asarray(d["idx"]).astype(int)] = np.asarray(d["E"]).ravel()
```

---

## 8. 알려진 함정 모음

| 함정 | 증상 | 대응 |
|---|---|---|
| 감독자 둘 | 같은 잡이 두 번 돈다 | 띄우기 전에 `pgrep -fc` 로 0 인지 확인 |
| TERM 두 번 | 고아 워커 | 한 번만. 오래 걸려도 기다린다 |
| 잡 파일 추가 | 아무 일도 안 일어남 | 재시작해야 읽는다 |
| `큐 i/N` 오독 | 진척을 과대평가 | 샤드 수로 읽는다 |
| 샤드 이어붙이기 | 리듬이 사라진 값 | `idx` 로 흩뿌린다 |
| KST/UTC | `find -newermt` 가 0 개 | `@epoch` 를 쓴다 |
| `pgrep` 자기매칭 | 개수가 하나 많다 | `ps -o args=` 로 확인 |
| `--help` 가 죽는다 | argparse 예외 | 알려진 버그. 인자는 이 문서나 소스에서 본다 |

---

## 9. 한 장 요약

```bash
cd /workspace/sionna; PY=/workspace/.venvs/py312/bin/python
pgrep -fc 'worker_supervisor.py'                                   # 0 이어야 띄운다
setsid nohup $PY runners/worker_supervisor.py runners/jobs_mine.txt \
  runners/logs/sup_mine.log >/dev/null 2>&1 &                      # 띄우기
tail -f runners/logs/sup_mine.log                                  # 보기
kill -TERM $(pgrep -f 'worker_supervisor.py' | head -1)            # 멈추기(한 번만)
```
