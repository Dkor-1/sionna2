# ⭐지금 상태 — 2026-09-06 (일) 밤

> 세션이 끊기면 이 파일부터. 덱은 `/workspace/team_meeting/teammeeting_0910/RESUME_0910.md`.
> 파이썬은 **/workspace/.venvs/py312/bin/python**. CPU 일은 앞에 `CUDA_VISIBLE_DEVICES=""`.

## 0. 한 줄
전수조사 끝(900/900) · 새 파일 규약 끝 · 09-10 덱 초안 끝(v6) · **GPU 큐 셋이 돌고 넷째가 사슬로 대기**.
지금 도는 사람 일은 없다. 큐 결과가 오면 덱 5 쪽을 «두 팔»→«다섯 팔» 로 올리는 것이 다음 손질.

## 1. 큐 — 감독자 셋 + 사슬 하나
```
  jobs_0906.txt  큐 93/122   jobs_0907.txt  큐 3/118    jobs_0908.txt  큐 2/78   
  jobs_0909.txt  대기 — runners/chain_0909_after_0908.sh 가 0908 이 78/78 된 뒤 30 분 지나 띄운다
```
| 발주 | 물음 |
|---|---|
| 0906 | 정면 겹침 창 — 방위·앙각 사다리 · 기체 · 거리 · 광선 예산 · 깊이 3 · 두꺼운 자세 |
| 0907 | ⓖ축 위 기준점(4e9) · 빈 구간 · 벼랑 좁히기 · **각도냐 가로 거리냐(30·60·120 m)** · 기체 크기 배율 · 재현 · 깊이 3 |
| 0908 | ⭐**굴절 켠 두 팔 근축**(→덱 5 쪽 다섯 팔) · 끊긴 칸 · 0.7° 씨앗 · 0.05°/0.07° 재현 · 예산별 창 폭 |
| 0909 | **실외 클러터 다각도** — 지면 거칠기 S · 남의 씬 · 거리 · 깊이 · 방위 · 넷 팔 되풀이 |

확인:
```bash
cd /workspace/sionna
for f in 0906 0907 0908 0909; do printf "$f "; tail -1 runners/logs/sup_jobs_$f.log 2>/dev/null | grep -oE "큐 [0-9/]+ · 워커 [0-9]+"; echo; done
ps -eo pid,args | grep "[w]orker_supervisor" | grep -v "bash -c"      # 감독자 목록
ps -eo args | grep -c "[e]levation_sweep_md.py"                       # 워커 수 (정상 8~9)
cat runners/logs/chain_0909.log 2>/dev/null                            # 사슬이 0909 를 띄웠나
```
⛔**감독자가 죽었으면** — 잡 파일은 시작 때 한 번만 읽으므로 그냥 다시 띄우면 된다(끝난 샤드는 건너뛴다):
```bash
setsid nohup /workspace/.venvs/py312/bin/python runners/worker_supervisor.py runners/jobs_09XX.txt runners/logs/sup_jobs_09XX.log > runners/logs/sup_jobs_09XX.boot 2>&1 < /dev/null &
```
⛔죽일 때 `pgrep -f` 를 쓰면 같은 명령줄에 그 이름이 있는 순간 제 셸이 죽는다(exit 144) — PID 를 뽑아 숫자로.
⛔워커가 4 로 줄고 감독자 로그에 «⛔대기: CPU 사용률» 이면 **남의 세션** 프로세스가 CPU 를 먹는 것이다 — 건드리지 않고 기다린다.
새 발주는 `runners/filter_jobs.sh` 로 줄마다 NEW·DONE·STALE 을 가른 뒤 넣는다(make_jobs_0907 머리말).

## 2. 목요일(09-10) 덱
`teammeeting_0910/_out_0910_v6.pptx` 9 쪽 — 끝. 자세한 것은 `teammeeting_0910/RESUME_0910.md`.
큐 0908 ⓐ 가 오면 `bake_window.py` 의 `ARMS` 에 두 팔을 더하고 v7. 새 판은 새 번호.

## 3. 전수조사 — 끝
900/900 찾고 고침 · 재빌드 58/58 · 관문 넷 통과 · `work/sweep_0904/`(STATE.json · findings · specs).
관문:
```bash
for g in check_retracted check_stale_titles check_row_pointers check_new_file_rules; do printf "$g "; CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/$g.py >/dev/null 2>&1 && echo ✅ || echo ⛔; done
```
⛔**CPU 로 못 돈 빌더 둘 — 사용자 몫** (재빌드 58 개 가운데):
- `benchmark/report16_base.py` — CPU 로 돌리면 멈춘다(900s ×2 · 3600s 에서도 CPU 0.2%). GPU 탐침 대기로 보인다.
  `PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/report16_base.py`
- `src/experiment_md_range.py` — 프로세스 11 개로 14 코어를 먹어 큐를 막는다. 독스트링 한 줄 고침이라 급하지 않다.
  `cd /workspace/sionna && PYTHONPATH=src /workspace/.venvs/py312/bin/python src/experiment_md_range.py` (큐가 빈 때)
- `src/make_report02_target.py` — `assert worst < 5e-3` 원장 표류, 전수조사 이전부터.

## 4. 새 파일 규약
`docs/NEW_FILE_RULES.md` (900 건 → 16 가지 + 저장 전 여덟 줄) · 관문 `benchmark/check_new_file_rules.py`(기준선 688, 줄어들기만).

## 5. 이번에 새로 만든 원장 (덱 숫자의 출처)
- `outputs/front_window_0906.json` — 정면 창: 팔마다 «겹친 자세 비율»과 중앙값.
  ⛔**경계는 팔마다 다르다 — 하나로 적지 마라.** 확산만·회절 두 팔은 방위 **0.11↔0.12°** ·
  앙각 **−0.15↔−0.16°**, 굴절 켠 두 팔은 방위 0.10↔0.15° · 앙각 −0.15↔−0.20° 다.
  2026-09-07 까지 이 줄과 덱 v6 결론줄이 굴절 켠 팔의 값을 팔 이름 없이 적어 두었고,
  덱 그림은 확산만·회절 두 팔을 그리고 있었다(팔이 어긋난 채로 나갔다). 덱은 v7 에서 고쳤다.
  ⚠회절 팔의 방위 사다리는 단조가 아니다 — 0.05° 에서 겹친 줄 수가 한 자세에서 107 까지
  튀고 0.07° 에서 1.0 % 로 내렸다가 0.10~0.11° 에서 다시 100 % 다. `edge()` 가 내는
  {last_on 0.11, first_off 0.07} 은 그 때문이고, **경계로 인용할 수 없는 값**이다.
- `outputs/front_repeat_0906.json` — 0°/0.2° 짝: 확산만 팔 0° 에서 되풀이 지우면 폭 9.5402 → 0.0063 dB, 상관 0.999990; 0.2° 는 두 배열 비트 동일.
⛔«정확히 3 배» 금지(최대 2.9992) · «솔버가 틀렸다» 금지 · 리듬 몫 크기 금지(R29) · 챔버 금지.

## 6. 열린 조사 (세션 안에서만 산다)
클러터 실험 설계 조사가 워크플로로 돌고 있었다(run `wf_a265209d-c0e`, 스크립트
`~/.claude/projects/-workspace-sionna/…/workflows/scripts/clutter-experiment-design-wf_a265209d-c0e.js`).
끊겼으면 journal.jsonl 을 보고, 0909 발주(72 줄)에 없는 손잡이만 0909b 로 붙인다. 없으면 그만둔다.
⛔우리 커널은 `--env` 를 거부한다(elevation_sweep_md.py:484) — 실외 «다섯 팔» 은 넷까지.
