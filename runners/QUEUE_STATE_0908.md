# 큐 갈아끼움 — 2026-09-08

사용자 요청: 「실외 씬 조사를 큐 앞에 올려줘」.
⇒ `jobs_0914.txt`(30 줄) 를 띄우고, 돌던 감독자 둘을 **배수**시켰다(돌던 워커는 마치고 멈춘다).

## 되살리는 법 (0914 가 끝난 뒤)

감독자는 큐를 **시작할 때 메모리로 읽고** 커서(`self.i`)로 진행한다. 그래서 다시 띄우면
**처음부터** 돈다 — 남은 줄만 남긴 새 파일을 만들어 띄워야 한다.

```bash
cd /workspace/sionna
# ① 남은 줄만 남긴다 (아래 «멈춘 자리» 의 수를 쓴다)
python - <<'PY'
def rest(src, done, dst):
    J=[l.strip() for l in open(src,encoding="utf-8")
       if l.strip() and not l.strip().startswith("#") and not l.strip().startswith("--help")]
    open(dst,"w",encoding="utf-8").write("\n".join(J[done:])+"\n")
    print(dst, len(J)-done, "줄")
rest("runners/jobs_0907.txt", 72, "runners/jobs_0907b.txt")
rest("runners/jobs_0913.txt", 40, "runners/jobs_0913c.txt")
PY
# ② 띄운다
nohup python runners/worker_supervisor.py runners/jobs_0907b.txt \
      runners/logs/sup_jobs_0907b.log > runners/logs/sup_jobs_0907b.nohup 2>&1 &
nohup python runners/worker_supervisor.py runners/jobs_0913c.txt \
      runners/logs/sup_jobs_0913c.log > runners/logs/sup_jobs_0913c.nohup 2>&1 &
```

⚠**띄우기 전에 `runners/filter_jobs.sh` 로 다시 거른다** — 0914 를 도는 동안 돌던 워커가
몇 줄을 마쳤을 수 있다. 안 거르면 같은 샤드를 두 번 산다.

## 멈춘 자리 (2026-09-08 배수 시점)

| 큐 | 전체 | 띄운 줄 | 남은 줄 | 남은 것이 무엇인가 |
|---|---|---|---|---|
| jobs_0907 | 118 | **72** | 46 | 대부분 r15 자유공간(싸다) · r120 자유공간 셋(느리다) |
| jobs_0913 | 55 | **40** | 15 | 실외·자유공간 섞임 |
| jobs_0912 | 28 | 28 | 0 | ✅끝남 |

⛔이 표의 «띄운 줄» 은 감독자 로그의 `큐 N/전체` 에서 읽은 값이다. 되살릴 때 그 수를
그대로 쓰지 말고 **로그를 다시 읽어라** — 배수 중에 몇 줄이 더 떴을 수 있다.
