# -*- coding: utf-8 -*-
"""
worker_supervisor.py — GPU 사정에 맞춰 워커 수를 **실시간으로** 조절하는 감독자
================================================================================

규약 (사용자 지정, 2026-08-19) — 기준은 **남이 잡고 있는 VRAM**(우리 몫을 뺀 값)
-----------------------------------------------------------------------------
    남의 점유 < 10,000 MB          →  최대 20 워커   (거의 놀고 있는 카드)
    남의 점유 < 20,000 MB          →  최대 12 워커
    남의 점유 20,000 ~ 70,000 MB   →  최대  7 워커
    남의 점유 > 70,000 MB          →  최대  3 워커
    카드 전체 점유 ≥ 95 %          →  **0 워커** (새로 안 띄운다)
    그 밖에는 어느 카드든 **최소 1 워커**

⭐왜 «남의 점유» 인가 — 우리 워커를 세면 우리가 늘릴수록 스스로를 밀어내는 되먹임이 생긴다.

이 구현이 규약에 **덧붙인 것** (그리고 왜)
------------------------------------------
  ⭐**떨림 방지(hysteresis)** — 남의 점유가 문턱 근처에서 오르내리면 목표가 12↔7 로 계속
     뒤집힌다. 워커 하나를 새로 띄우는 데 커널 컴파일로 1~2 분이 든다. 그래서
     ① 문턱을 넘을 때 **여유(DEADBAND)** 를 두고 ② 목표를 바꾼 뒤 **최소 유지시간**을 둔다.
  ⭐**줄일 땐 안 죽인다** — 저장소 규칙(⛔프로세스 자동 kill 금지, 0811 사고). 목표보다 많으면
     **끝난 자리를 안 채우는** 방식으로만 줄인다. 계산 중인 워커를 죽이지 않는다.
  ⭐**전역 안전선** — RAM 여유 하한(서버가 한 번 OOM 으로 죽은 적 있다)과 전체 워커 상한.
  ⭐**등급 값은 «상한» 이지 «목표» 가 아니다** — 전체 예산을 상한 안에서 **물채우기(water-filling)**
     로 나눠 각 카드의 목표를 정한다. 그래서 사정이 비슷한 카드끼리는 **저절로 균등**해진다.
  ⛔**한 카드가 넘쳤다고 다른 카드를 굶기지 않는다** — 2026-08-19 사고: 전역 상한이 신규 투입을
     통째로 막는 바람에, GPU 2 가 32 개로 넘친 동안 **GPU 0 은 상한 7 인데 2 개**만 돌았다.
     전역 상한은 이제 **목표 배분의 예산**으로만 쓰고, 투입 판정은 카드별 목표로 한다.
     (진짜 안전선인 RAM·CPU 는 그대로 신규 투입을 막는다.)

⛔이 파일은 **감독자 하나만** 돌아야 한다(큐를 혼자 읽어 나눠 준다 — 중복 배정이 없다).

실행: setsid nohup python runners/worker_supervisor.py <jobs.txt> [로그] &
"""
from __future__ import annotations

import collections, json, os, re, signal, subprocess, sys, time

ROOT = "/workspace/sionna"
PY = "/workspace/.venvs/py312/bin/python"
SCRIPT = "benchmark/elevation_sweep_md.py"

# ── 규약 표 (남의 VRAM MB, 최대 워커) — 위에서부터 처음 맞는 칸 ─────────────
# ⭐2026-08-19 **보수적으로 하향**. 왜 — 셋 다 실측이다:
#   ① 프로세스 하나가 CUDA 문맥 하나를 차지하고, MPS 가 없으면 문맥끼리 **시분할**된다.
#      한 카드에 우리 문맥 30 개면 남의 프로세스 1 개는 시간 몫이 **약 1/31 = 3.2 %** 로 떨어진다.
#      랩 공용 자원이므로 이건 사실상 카드를 독차지하는 것이다.
#   ② 프로세스 하나가 **CPU 코어를 91.7 % 씀**(실측). 워커 79 개면 72 코어를 먹는다.
#   ③ 카드가 빈 동안 워커를 늘리면 이득이 크지만(16 개까지 거의 선형), 남이 100 % 로 쓰는
#      카드에서는 서로 갉아먹기만 한다.
#   ⇒ 상한을 절반 수준으로 내리고, «비었을 때만» 크게 쓴다.
# ⭐2026-08-20 **다시 하향**. 감사에서 밝혀진 것: 워커 하나가 스레드 **68 개**를 띄우는데
#   컨테이너 CPU 는 **12 개**다. MAX_TOTAL 36 × 68 = 스레드 2,448 개가 12 코어에서 싸웠고,
#   그 줄서기가 자세당 시간을 **50~70 배** 부풀렸다(한산한 상자 267 ms ↔ 프로필 6,095 ms).
#   ⇒ 스레드 캡(THREADS_PER_WORKER)을 걸고 워커 수도 CPU 할당에 맞춰 내린다.
TIERS = [(10_000, 3), (20_000, 2), (70_000, 2), (float("inf"), 1)]
FULL_FRAC = 0.90        # 카드 전체가 이만큼 차면 새로 안 띄운다 (0.95 → 0.90 으로 조임)
URGENT_FRAC = 0.70      # ⭐이만큼 차면 떨림 방지를 건너뛰고 즉시 등급을 내린다
MIN_PER_GPU = 1         # 그 밖에는 어느 카드든 최소 1

DEADBAND_MB = 2_000     # ⭐문턱을 이만큼 확실히 넘어야 등급을 바꾼다(떨림 방지)
DWELL_S = 180           # ⭐등급을 바꾼 뒤 최소 이만큼 유지한다
POLL_S = 30

RAM_FLOOR_GB = 6        # ⭐우리 천장이 **32 GiB** 다. 60 은 천장보다 커서 «영구 정지» 지뢰였다
MAX_TOTAL = int(os.environ.get("SIONNA2_MAX_TOTAL", "8"))   # 목표 배분의 **예산** 상한(투입 차단선이 아니다)
#: ⭐전체 상한 8 — 12 CPU 에서 처리량이 6~10 에서 평평하고, 12 에서는 load 16.6 으로
#   할당(12)을 넘었다(2026-08-20 2 회 측정). 8 이면 부하 11~12 로 할당 안에 든다.
#: ⭐워커 하나가 띄울 스레드 수. 무방비면 numpy(BLAS)만으로 64 개가 뜬다(실측).
#   2 로 걸면 sionna 로드 뒤에도 6 개다. 10 워커 × 6 = 60 스레드 ≈ 12 CPU 에 맞는다.
THREADS_PER_WORKER = int(os.environ.get("SIONNA2_THREADS", "2"))
#: ⛔**절대 넘지 않는 선** — 고아 포함 실제 총 워커 수. MAX_TOTAL 은 «배분 예산» 일 뿐이라
#   고아가 있으면 그것을 넘어선다(실측: 고아 30 개 + 신규 6 개 = 36 개, 예산은 8 이었다).
#   0819 «전역 상한이 신규 투입을 통째로 막아 GPU 0 이 굶었다» 사고를 피하려고 둘을 가른다.
HARD_TOTAL = int(os.environ.get("SIONNA2_HARD_TOTAL", "12"))
#: ⛔**절대 안 쓸 카드** — 환경변수 SIONNA2_EXCLUDE_GPUS="0,3" 으로 준다.
#   사용자가 «저 카드는 빼라» 고 하면 여기로 막는다. 규약(남의 점유)과 무관하게 0 이 된다.
EXCLUDE = {int(x) for x in os.environ.get("SIONNA2_EXCLUDE_GPUS", "").replace(" ", "").split(",") if x.isdigit()}
CPU_LOAD_CAP = 0.85     # ⭐**우리** cgroup 사용률이 이보다 크면 새로 안 띄운다
#   (남의 부하가 아니라 우리 것만 본다 — cpu_load_frac 주석 참조)


def nvidia():
    """[(idx, used_MB, total_MB)] — 카드 전체 사용량."""
    o = subprocess.run("nvidia-smi --query-gpu=index,memory.used,memory.total "
                       "--format=csv,noheader,nounits", shell=True,
                       capture_output=True, text=True).stdout
    out = []
    for l in o.splitlines():
        try:
            i, u, t = [int(x.strip()) for x in l.split(",")]
            out.append((i, u, t))
        except Exception:
            pass
    return out


def our_vram():
    """{gpu: 우리 프로세스가 잡은 MB} — nvidia-smi 의 compute-apps 는 **우리 컨테이너 것만** 보인다."""
    u2i = {}
    for l in subprocess.run("nvidia-smi --query-gpu=index,uuid --format=csv,noheader",
                            shell=True, capture_output=True, text=True).stdout.splitlines():
        try:
            i, u = [x.strip() for x in l.split(",")]
            u2i[u] = int(i)
        except Exception:
            pass
    d = collections.Counter()
    for l in subprocess.run("nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory "
                            "--format=csv,noheader,nounits", shell=True,
                            capture_output=True, text=True).stdout.splitlines():
        try:
            p, u, m = [x.strip() for x in l.split(",")]
            d[u2i.get(u, -1)] += int(m)
        except Exception:
            pass
    return d


def tier_cap(ext_mb: float) -> int:
    for thr, cap in TIERS:
        if ext_mb < thr:
            return cap
    return TIERS[-1][1]


def _reclaimable_bytes() -> int:
    """⭐`memory.current` 안에서 **압력이 오면 돌려줄 수 있는** 몫 [B].

    cgroup v2 의 `memory.current` 는 익명 메모리(anon)뿐 아니라 **파일 캐시(file)** 도 센다.
    파일 캐시는 커널이 필요할 때 버리므로 «남이 잡고 있는 메모리» 가 아니다.
    ⛔이걸 안 빼면 캐시가 찰수록 여유가 0 으로 수렴해 감독자가 **영구 정지**한다
      (2026-09-02 에 실제로 2.5 시간 멈췄다 — anon 1.38 GiB 인데 여유를 3.5 GiB 로 읽었다).

    ⚠보수적으로 **inactive_file 만** 뺀다. active_file 은 최근에 쓰인 캐시라 회수하면
      느려질 수 있고, 여기서 한 번에 다 빼면 브레이크가 헐거워진다.
    """
    try:
        for ln in open("/sys/fs/cgroup/memory.stat"):
            k, v = ln.split()
            if k == "inactive_file":
                return int(v)
    except Exception:
        pass
    return 0


def ram_free_gb() -> float:
    """⭐**우리 cgroup** 의 여유 [GiB]. `/proc/meminfo` 는 **호스트** 라 32 GiB 천장을 못 본다.

    ⛔실측(2026-08-20): cgroup 이 32 GiB 중 30.7 GiB 를 써도 meminfo 는 «182 GB 여유» 라
      답했다 — 브레이크가 절대 안 걸린다. 버그 ②③ 과 같은 «호스트를 재는» 실수다.
    """
    try:
        mx = open("/sys/fs/cgroup/memory.max").read().strip()
        cur = int(open("/sys/fs/cgroup/memory.current").read())
        # ⛔**`memory.current` 는 파일 캐시를 포함한다** — 그것을 «쓰는 중» 으로 세면
        #   캐시가 찰수록 여유가 0 으로 수렴해 감독자가 영원히 멈춘다.
        #   실측(2026-09-02 10:37): current 20.50 GiB 중 anon 1.38 · file 17.87 GiB 였고,
        #   감독자는 여유 3.5 GiB 로 읽어 **2.5 시간 동안 워커를 하나도 안 띄웠다.**
        #   파일 캐시는 메모리 압력이 오면 회수되므로 여유로 친다 — 회수 못 하는 것만 뺀다.
        cur = cur - _reclaimable_bytes()
        if mx != "max":
            return (int(mx) - cur) / 2 ** 30
        # ⭐천장이 «max» 로 풀린 상자 — 2026-08-24 컨테이너 재시작 뒤 그렇게 되었다.
        #   그러면 아래 fail-closed 0.0 이 걸려 감독자가 **영구 정지**한다(실측).
        #   호스트 meminfo 로 물러서면 브레이크가 사라지므로(위 주석의 버그 ②③),
        #   운영자가 SIONNA2_RAM_GB 로 «우리 몫» 을 명시하게 한다.
        budget = os.environ.get("SIONNA2_RAM_GB", "").strip()
        if re.fullmatch(r"\d+(\.\d+)?", budget or ""):
            return float(budget) - cur / 2 ** 30
    except Exception:                                          # noqa: BLE001
        pass
    return 0.0            # ⛔못 재면 막는 쪽


def cgroup_cpus() -> float:
    """⭐**컨테이너가 실제로 준 CPU 수.** os.cpu_count() 는 호스트 전체(192)를 본다.

    이걸 안 쓰면 브레이크가 16 배 헐거워진다 — CPU_LOAD_CAP 0.60 이 실제로는
    «load 가 115 를 넘어야 멈춤» 이 되어 사실상 브레이크가 없다(2026-08-20 감사).
    """
    try:
        q, per = open("/sys/fs/cgroup/cpu.max").read().split()
        if q != "max":
            return float(q) / float(per)
    except Exception:                                          # noqa: BLE001
        pass
    try:
        q = int(open("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read())
        per = int(open("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read())
        if q > 0:
            return q / per
    except Exception:                                          # noqa: BLE001
        pass
    # ⛔못 읽으면 os.cpu_count()(192)가 아니라 **작게** 물러선다 — 크게 잡으면 브레이크가 헐거워진다
    return 2.0


#: ⭐cgroup 제한이 «max» 로 풀린 상자에서 운영자가 «우리가 쓸 CPU» 를 직접 준다.
#   2026-08-24: 컨테이너 재시작 뒤 cpu.max·memory.max 가 둘 다 «max» 가 되었다.
#   그러면 cgroup_cpus() 가 fail-small 로 2.0 을 내는데, 그 값이면 브레이크가 너무
#   조여 워커 1~2 개에서 영구 정지한다. 그렇다고 호스트 64 를 쓰면 공유 서버를
#   잡아먹는다. ⇒ 환경변수 SIONNA2_CPUS 로 «우리 몫» 을 명시한다.
#   ⛔안 주면 예전과 **똑같이** cgroup_cpus() 로 물러선다 — 기본 동작 불변.
_CPUS_ENV = os.environ.get("SIONNA2_CPUS", "").strip()
CPUS = float(_CPUS_ENV) if re.fullmatch(r"\d+(\.\d+)?", _CPUS_ENV or "") else cgroup_cpus()


_CPU_PREV = {"t": 0.0, "usec": 0}


def cpu_load_frac() -> float:
    """⭐**우리 컨테이너가 실제로 쓰는 CPU** 비율 (0~1).

    ⛔`os.getloadavg()` 를 쓰면 안 된다 — 그것은 **호스트 전체(192 코어)** 의 부하다.
      우리 cgroup 할당(12)으로 나누면 «남이 바쁘면 우리가 못 뜬다» 가 되어버린다
      (2026-08-20 실측: 우리 워커 0 개인데 load 8.29 라 브레이크가 걸려 큐가 안 돌았다).
      대신 cgroup 의 누적 CPU 시간을 두 시점에 읽어 **우리 사용량만** 잰다.
    """
    try:
        usec = 0
        for ln in open("/sys/fs/cgroup/cpu.stat"):
            if ln.startswith("usage_usec"):
                usec = int(ln.split()[1])
                break
        now = time.time()
        prev_t, prev_u = _CPU_PREV["t"], _CPU_PREV["usec"]
        _CPU_PREV["t"], _CPU_PREV["usec"] = now, usec
        if prev_t <= 0 or now <= prev_t:
            return 0.0
        return (usec - prev_u) / 1e6 / (now - prev_t) / max(1.0, CPUS)
    except Exception:                                          # noqa: BLE001
        # ⛔**못 재면 «꽉 찼다» 로 본다(fail-closed).** 호스트 load 로 물러서면 브레이크가
        #   **조용히 영구 해제**된다 — 그게 오늘 버그 ② 와 글자 그대로 같은 실수다
        #   (실측: fallback 이 0.073 을 내서 상한 0.85 에 절대 안 걸렸다).
        return 1.0


class Sup:
    def __init__(self, jobs_path, log_path):
        self.log_path = log_path
        self.jobs = [l.strip() for l in open(jobs_path, encoding="utf-8")
                     if l.strip() and not l.strip().startswith("#")
                     and not l.strip().startswith("--help")]
        self.i = 0
        self.procs = {}                    # pid -> (gpu, line, t_start)
        self.grade = {}                    # gpu -> (cap, t_since)
        self.n_launched = 0
        self.n_failed = 0
        self._filling_up = False
        self.err_path = log_path + ".workererr"
        self.out_path = log_path + ".workerout"      # ⭐진행률이 여기로 온다
        if EXCLUDE:
            self.log(f"⛔제외 카드: {sorted(EXCLUDE)}")
        self.log(f"큐 {len(self.jobs)} 줄 · 규약 {TIERS} · 여유 {DEADBAND_MB} MB · 유지 {DWELL_S}s "
                 f"· ⭐CPU 할당 {CPUS:.0f} · 워커당 스레드 {THREADS_PER_WORKER} "
                 f"· 전체 상한 {MAX_TOTAL}")

    def log(self, msg):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%m-%d %H:%M:%S', time.gmtime(time.time()+9*3600))}] {msg}\n")

    # ── 지금 각 카드에 우리 워커가 몇 개인가 ────────────────────────────
    def running_by_gpu(self):
        """⛔**자식 프로세스만 세면 안 된다.** 감독자가 뜨기 전부터 돌던 워커(고아)나 다른
        런처가 띄운 워커도 같은 카드를 쓴다. 그걸 빼먹으면 규약 상한을 조용히 넘는다
        (2026-08-19 실측: 감독자는 «53 개» 라 했는데 실제는 **80 개**, GPU 2 에 32 개).
        그래서 **프로세스 목록 전체**를 훑어 CUDA_VISIBLE_DEVICES 로 카드를 읽는다."""
        d = collections.Counter()
        out = subprocess.run("ps -eo pid,args", shell=True,
                             capture_output=True, text=True).stdout
        for l in out.splitlines():
            if SCRIPT not in l:
                continue
            try:
                pid = int(l.split()[0])
                env = open(f"/proc/{pid}/environ").read().split("\0")
                cvd = [x.split("=", 1)[1] for x in env
                       if x.startswith("CUDA_VISIBLE_DEVICES=")]
                if cvd and cvd[0].strip().isdigit():
                    d[int(cvd[0].strip())] += 1
            except Exception:
                pass
        return d

    def total_running(self):
        """전역 상한 판정도 **고아 포함** 전체로 센다."""
        return sum(self.running_by_gpu().values())

    def reap(self):
        """⭐Popen.poll() 로 거둔다 — os.waitpid 를 쓰면 subprocess 내부 청소기와 경합해
        rc 가 사라진다(실측: 띄움 35 · «끝 rc=» 7 줄뿐이었다)."""
        for pid, tup in list(self.procs.items()):
            g, line, t0 = tup[0], tup[1], tup[2]
            p = tup[3] if len(tup) > 3 else None
            rc = None
            if p is not None:
                rc = p.poll()
                if rc is None:
                    continue
            else:                                              # 옛 항목(호환)
                try:
                    q, st = os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    self.procs.pop(pid, None); continue
                if q != pid:
                    continue
                rc = os.waitstatus_to_exitcode(st)
            mark = "" if rc == 0 else "  ⛔"
            self.log(f"  끝 pid={pid} gpu={g} rc={rc} {(time.time()-t0)/60:.1f}분{mark}")
            if rc != 0:
                self.n_failed += 1
                self.log(f"     실패한 줄: {line[:120]}")
            self.procs.pop(pid, None)

    def target(self, gpu, used, total, ours):
        """규약 + 떨림 방지 → 이 카드의 목표 워커 수."""
        ext = max(0, used - ours)
        if used >= FULL_FRAC * total:
            return 0, ext
        raw = tier_cap(ext)
        prev, t_since = self.grade.get(gpu, (None, 0.0))
        if prev is None:
            self.grade[gpu] = (raw, time.time())
            return max(raw, MIN_PER_GPU), ext
        # ⭐등급을 **낮출 때만** 여유·유지시간을 요구한다(늘리는 건 즉시 — 손해가 없다)
        if raw < prev:
            near = tier_cap(max(0.0, ext - DEADBAND_MB))
            if near >= prev or (time.time() - t_since) < DWELL_S:
                return max(prev, MIN_PER_GPU), ext
        if raw != prev:
            self.grade[gpu] = (raw, time.time())
            self.log(f"  등급 변경 gpu={gpu} {prev} → {raw} (남의 점유 {ext:,} MB)")
        return max(raw, MIN_PER_GPU), ext

    def plan(self, cards, ours):
        """⭐상한(등급) 안에서 전체 예산을 **균등하게** 나눠 카드별 목표를 낸다.

        한 개씩 «지금 가장 적게 받은 카드» 에 얹는 물채우기다. 사정이 같으면 개수가 같아지고,
        상한이 큰 카드(=남이 안 쓰는 카드)만 뒤에 더 받는다.
        동점이면 **남의 점유가 적은 카드**를 먼저 채운다.
        """
        caps, ext = {}, {}
        for g, used, total in cards:
            e = max(0, used - ours.get(g, 0))
            ext[g] = e
            # ⭐카드가 URGENT_FRAC 넘게 찼으면 떨림 방지를 건너뛰고 **즉시** 등급을 내린다
            self._filling_up = used >= URGENT_FRAC * total
            if g in EXCLUDE:
                caps[g] = 0                                    # ⛔사용자가 뺀 카드
            else:
                caps[g] = 0 if used >= FULL_FRAC * total else max(self.capped(g, e), MIN_PER_GPU)
        budget = min(MAX_TOTAL, sum(caps.values()))
        # ── ① 어느 카드든 최소 1 (저장소 규약) ─────────────────────────
        tgt = {g: (MIN_PER_GPU if caps[g] > 0 else 0) for g in caps}
        while sum(tgt.values()) > budget:                       # 예산이 모자라면 붐비는 카드부터 뺀다
            g = max((g for g in tgt if tgt[g] > 0), key=lambda g: (ext[g], g))
            tgt[g] -= 1
        # ── ② ⭐남는 자리는 **널널한 카드부터**, 그 안에서는 균등하게 ──
        #   (2026-08-20 사용자 지시: «널널한 것 위주로 균등하게»)
        #   순수 균등이면 남이 40 GB 쓰는 카드에도 똑같이 얹혀 서로 갉아먹는다.
        #   그래서 «남의 점유가 적은 순» 을 1 순위, «지금 적게 받은 순» 을 2 순위로 둔다.
        while sum(tgt.values()) < budget:
            free = [g for g in caps if tgt[g] < caps[g]]
            if not free:
                break
            g = min(free, key=lambda g: (ext[g] // 5_000, tgt[g], ext[g], g))
            tgt[g] += 1
        return tgt, ext, caps

    def capped(self, gpu, ext_mb):
        """등급(상한) — 떨림 방지를 여기서 건다."""
        raw = tier_cap(ext_mb)
        prev, t_since = self.grade.get(gpu, (None, 0.0))
        if prev is None:
            self.grade[gpu] = (raw, time.time())
            return raw
        if raw < prev:                       # ⭐내릴 때만 여유·유지시간을 요구
            # ⛔단, **카드가 실제로 차오르는 중이면 즉시 내린다.** 떨림 방지 때문에 3 분을 버티면
            #   그 사이 우리 워커 20 개(약 26 GB)와 남의 75 GB 가 겹쳐 카드가 터진다.
            #   (2026-08-19 시험에서 드러난 구멍 — 여유는 «흔들림» 을 막으려는 것이지
            #    «진짜 급증» 을 무시하라는 뜻이 아니다.)
            if not self._filling_up:
                if tier_cap(max(0.0, ext_mb - DEADBAND_MB)) >= prev or (time.time() - t_since) < DWELL_S:
                    return prev
        if raw != prev:
            self.grade[gpu] = (raw, time.time())
            self.log(f"  등급 변경 gpu={gpu} 상한 {prev} → {raw} (남의 점유 {ext_mb:,.0f} MB)")
        return raw

    def launch(self, gpu, line) -> bool:
        # ⭐⭐**스레드 캡** — 이게 없으면 numpy(BLAS)만으로 워커당 64 스레드가 뜬다(실측).
        #   컨테이너 CPU 는 12 개인데 os.cpu_count() 가 192 를 보고해서 생기는 일이다.
        #   ⛔2026-08-20 이전 판에는 이 블록이 통째로 없었고, 그 결과 스레드 2,448 개가
        #     12 코어를 두고 싸워 자세당 시간이 50~70 배로 부풀었다(랩 서버 과부하의 원인).
        t = str(THREADS_PER_WORKER)
        env = dict(os.environ,
                   CUDA_VISIBLE_DEVICES=str(gpu), PYTHONPATH="src:benchmark",
                   DRJIT_LIBOPTIX_PATH="/workspace/.venvs/optix/libnvoptix.so.1",
                   LD_LIBRARY_PATH="/workspace/.venvs/optix:" + os.environ.get("LD_LIBRARY_PATH", ""),
                   OMP_NUM_THREADS=t, OPENBLAS_NUM_THREADS=t, MKL_NUM_THREADS=t,
                   NUMEXPR_NUM_THREADS=t, VECLIB_MAXIMUM_THREADS=t,
                   DRJIT_NUM_THREADS=t, MI_NUM_THREADS=t, RAYON_NUM_THREADS=t,
                   OMP_WAIT_POLICY="PASSIVE", KMP_BLOCKTIME="0",
                   TOKENIZERS_PARALLELISM="false")
        # ⛔**fork 실패를 잡는다** — 자원이 마르는 바로 그 순간 감독자가 죽으면서
        #   워커를 고아로 남긴다(start_new_session=True 라 살아남는다). 오늘 버그 ④ 의 자가 재생산.
        try:
            # ⭐**stdout 을 버리지 않는다** — 워커가 128 자세마다 진행률을 찍는데 DEVNULL 로
            #   보내면 «도는지 멈췄는지» 를 알 길이 없다(2026-08-20: 22 분 동안 샤드가 0 이라
            #   고장인 줄 알았는데 그냥 느린 것이었다. 진행률이 보였으면 바로 알았다).
            p = subprocess.Popen([PY, SCRIPT] + line.split(), cwd=ROOT, env=env,
                                 stdout=open(self.out_path, "ab", buffering=0),
                                 stderr=open(self.err_path, "ab", buffering=0),
                                 start_new_session=True)
        except OSError as e:
            self.log(f"  ⛔띄우기 실패({type(e).__name__}: {e}) — 이 줄은 큐에 되돌린다")
            return False
        # ⭐**Popen 객체를 붙잡는다.** pid 만 저장하면 subprocess 내부 _cleanup 이 먼저 거둬
        #   os.waitpid 가 ChildProcessError 로 죽고 «끝 rc=» 줄이 아예 안 남는다(실측 재현).
        self.procs[p.pid] = (gpu, line, time.time(), p)
        self.n_launched += 1
        self.log(f"  띄움 #{self.n_launched} pid={p.pid} gpu={gpu} {line[:88]}")
        return True

    def _tick(self):
        """한 바퀴 — 재고, 계획하고, 모자란 만큼 띄운다."""
        self.reap()
        cards, ours = nvidia(), our_vram()
        run = self.running_by_gpu()
        tgt, ext, caps = self.plan(cards, ours)
        rf, cl = ram_free_gb(), cpu_load_frac()

        hold = []
        if rf < RAM_FLOOR_GB:
            hold.append(f"RAM 여유 {rf:.1f}G < {RAM_FLOOR_GB}")
        if cl > CPU_LOAD_CAP:
            hold.append(f"CPU 사용률 {cl:.2f} > {CPU_LOAD_CAP}")

        # ⭐고아 포함 **실제** 총 워커 수 — MAX_TOTAL 은 배분 예산일 뿐이라 이걸 따로 본다
        live = sum(run.values())
        if live >= HARD_TOTAL:
            hold.append(f"총 워커 {live} ≥ 절대선 {HARD_TOTAL}")

        state = []
        for g, _u, _t in cards:
            cur = run.get(g, 0)
            state.append(f"G{g}:{cur}/{tgt[g]}(상한{caps[g]}·남{ext[g]//1000}G)")
            if hold or self.i >= len(self.jobs):
                continue
            while cur < tgt[g] and self.i < len(self.jobs) and live < HARD_TOTAL:
                if self.launch(g, self.jobs[self.i]):
                    self.i += 1; cur += 1; live += 1
                else:
                    break                                      # fork 실패 — 이번 바퀴는 그만
        self.log(f"상태 {' '.join(state)} · 큐 {self.i}/{len(self.jobs)} · "
                 f"워커 {sum(run.values())} · RAM {rf:.1f}G · CPU {cl:.2f}"
                 + (f" · 실패 {self.n_failed}" if self.n_failed else "")
                 + (f" · ⛔대기: {'; '.join(hold)}" if hold else ""))

    def loop(self):
        # ⭐종료 신호를 받으면 **워커를 두고 가지 않는다** — 오늘 고아 사고의 직접 원인이다.
        stop = {"v": 0}          # ⭐계수기 — 두 번째 신호가 배수의 탈출구다

        def _bye(sig, frm):                                    # noqa: ARG001
            stop["v"] += 1
            if stop["v"] == 1:
                self.log(f"  신호 {sig} 받음 — 새로 안 띄우고 돌던 워커를 기다린다")
            else:
                self.log(f"  ⛔신호 {sig} 두 번째 — 배수를 끊고 나간다(워커는 계속 돈다)")
        for _sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(_sig, _bye)
            except Exception:                                  # noqa: BLE001
                pass

        while (self.i < len(self.jobs) or self.procs) and not stop["v"]:
            # ⛔한 바퀴가 터져도 감독자는 안 죽는다 — 죽으면 워커가 고아가 된다
            try:
                self._tick()
            except Exception as e:                             # noqa: BLE001
                self.log(f"  ⛔폴 실패({type(e).__name__}: {e}) — 이번 바퀴는 아무것도 안 띄운다")
            time.sleep(POLL_S)

        if stop["v"] and self.procs:
            # ⛔⛔**여기가 고아를 만들던 자리다** (2026-08-24 감사).
            #   옛 판은 자식마다 `p.wait(timeout=3600)` 을 **순차로** 걸고 TimeoutExpired 를
            #   통째로 삼켰다. 워커 하나가 149 분(앙각 2 개면 약 5 시간) 도는 이 저장소에서
            #   그 상한은 **항상 워커보다 짧다** — 자식 3 개면 3 시간 뒤 감독자가 먼저 나가고
            #   워커는 ppid=1 로 남는다. 실측(2026-08-24): 17:20 배수 시작 → 20:20 감독자 종료
            #   → 워커는 21:42 종료. **82 분간 고아.** 바로 위 주석이 «워커를 두고 가지
            #   않는다» 고 선언한 그 함수가 두고 갔다.
            # ⇒ 시계가 아니라 **워커가 끝나는 것**을 기다린다. 스스로 포기하지 않는다.
            #   ⛔무한 대기는 아니다 — **두 번째 종료 신호**가 탈출구다(운영자가 정말 급할 때).
            #   그 경로로 나갈 때는 버리고 가는 pid↔잡 대응을 파일로 남겨 입양 가능하게 한다.
            self.log(f"  종료 중 — 워커 {len(self.procs)} 개가 끝나기를 기다린다 "
                     f"(⛔kill 안 한다. 정말 급하면 종료 신호를 한 번 더 준다)")
            while self.procs and stop["v"] < 2:
                self.reap()
                if not self.procs:
                    break
                time.sleep(POLL_S)
            if self.procs:
                orph = os.path.join(os.path.dirname(self.log_path or "."),
                                    "orphans_handoff.txt")
                try:
                    with open(orph, "a", encoding="utf-8") as fh:
                        fh.write(f"# {time.strftime('%m-%d %H:%M:%S')} 두 번째 신호로 배수를 "
                                 f"끊었다 — 아래 워커는 관리자 없이 남는다\n")
                        for pid, tup in self.procs.items():
                            fh.write(f"pid={pid} job={tup[1] if len(tup) > 1 else '?'}\n")
                    self.log(f"  ⛔워커 {len(self.procs)} 개를 두고 나간다 — 대응표 {orph}")
                except Exception as e:                         # noqa: BLE001
                    self.log(f"  ⛔대응표를 못 남겼다: {type(e).__name__}")
            self.reap()
        self.log(f"== 종료 ({self.n_launched} 줄 실행 · 실패 {self.n_failed} · "
                 f"큐 {self.i}/{len(self.jobs)}) ==")


if __name__ == "__main__":
    jobs = sys.argv[1]
    log = sys.argv[2] if len(sys.argv) > 2 else f"{ROOT}/runners/logs/supervisor.log"
    os.makedirs(os.path.dirname(log), exist_ok=True)
    Sup(jobs, log).loop()
