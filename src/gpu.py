# -*- coding: utf-8 -*-
"""
gpu.py — **여유 메모리를 보고 GPU 를 잡고, 그 메모리를 실제로 쓴다**
=====================================================================
정책 (2026-07-14, 사용자 지시):
  1. **메모리 여유가 판단 기준**이다. 사용률(util%)은 참고만 한다
     — 다른 사람이 계산을 돌리고 있어도 **메모리만 충분하면 같이 쓴다**.
  2. 여유 메모리가 가장 많은 GPU 를 고른다 (min_free_mb 미만이면 후보에서 제외).
  3. 워크로드는 **잡은 메모리를 실제로 채우도록** 크기를 키운다 (budget_mb / batch_for).
     찔끔찔끔 쓰지 말 것.

⚠ **반드시 mitsuba/sionna/torch import 전에** 불러야 한다 — CUDA_VISIBLE_DEVICES 는
  CUDA 컨텍스트가 만들어지는 순간 고정된다.

    from gpu import pick, budget_mb      # 맨 먼저!
    pick()                                # 여유 메모리가 가장 많은 1장
    import mitsuba as mi                  # ← 그 다음

환경변수:
  SIONNA2_GPU=1        특정 GPU 강제
  SIONNA2_GPU_MEM=10000  이 워크로드가 쓸 목표 메모리 [MiB] (기본: 여유의 92%; **여유를 넘지 않는다**)
"""
from __future__ import annotations

import os
import subprocess

_PICKED: str | None = None
_BUDGET_MB: int | None = None

#  사용자 지시(2026-07-14): "점유 가능하면 최대한 점유해서 써버려".
#  → 여유 메모리의 FRACTION 만큼을 이 워크로드의 예산으로 잡는다. 찔끔 쓰지 않는다.
#
#  ⭐ 2026-07-28 방침 갱신 (사용자 지시): **"여유가 1~2 GB 여도 계속 조금씩이라도 써라.
#     지금 쓸 수 있는 한도에 맞춰서 계속 사용해."**
#     → 문턱을 2 GB → **0.8 GB** 로 내리고, MIN_TARGET_MB 를 **하한 강제에서 제거**한다.
#       예전 `max(MIN_TARGET_MB, free*0.92)` 는 여유가 1 GB 인데도 예산을 4 GB 라고 답해
#       배치가 과대 산정되어 **OOM 으로 죽는** 원인이었다(공용 GPU 경합에서 실제로 발생).
#       이제 예산은 **여유를 절대 넘지 않는다**. 대신 OOM 이 나면 죽지 말고
#       `oom_backoff()` 가 배치를 반으로 줄여 재시도한다 — 느려질지언정 멈추지 않는다.
MEM_FRACTION = 0.92                 # 여유 메모리의 92% 를 예산으로 (아끼지 않는다)
MIN_TARGET_MB = 512                 # 최소 목표(강제 아님) — 이보다 적으면 그만큼만 쓴다
MIN_FREE_MB = 800                   # 0.8 GB 이상 여유면 침투해서 쓴다 (옛 2000)
ABS_MIN_MB = 256                    # 이보다도 적으면 GPU 를 쓰는 의미가 없다

# ⭐ 카드 선호 (2026-07-30 사용자 지시, 별도 지시가 있을 때까지 유효)
#   "동적 할당을 하되, 비슷한 수준의 여유가 있다면 2·3 번을 우선시 사용"
#   → 여유가 뚜렷하게 큰 카드가 있으면 그쪽을 쓰고(큰 작업은 여유 많은 곳으로),
#     엇비슷하면 선호 카드가 이긴다. SIONNA2_PREFER_GPUS 로 덮을 수 있다(예: "0,1" 또는 "" 로 해제).
PREFER_GPUS = tuple(int(x) for x in os.environ.get("SIONNA2_PREFER_GPUS", "2,3").split(",") if x.strip())
PREFER_TOL_MB = int(os.environ.get("SIONNA2_PREFER_TOL_MB", "3000"))     # 절대 허용차
PREFER_TOL_FRAC = float(os.environ.get("SIONNA2_PREFER_TOL_FRAC", "0.25"))  # 상대 허용차


def _bucket(free_mb: int) -> int:
    """여유 메모리를 **허용차 폭의 계단**으로 양자화한다.
    같은 계단에 있으면 '비슷한 수준' 이므로 선호 카드가 이긴다."""
    step = max(1, PREFER_TOL_MB)
    return int(free_mb) // step


# ⭐ 카드별 **타인 사용분 예비** (2026-07-30 사용자 지시)
#   "0·1 번은 누군가 13000~14000 MB 정도는 사용한다는 가정으로 넣고, 2·3 번을 우선시"
#   → 비선호 카드(0·1)는 지금 비어 보여도 그만큼을 **미리 뺀 예산**으로 잡는다. 그래야 남이
#     들어와도 우리가 OOM 으로 죽지 않는다(오늘 CFAR 이 정확히 그렇게 죽었다).
#   선호 카드(2·3)는 한동안 우리 것이라는 정보가 있으니 예비를 작게 둔다.
FOREIGN_RESERVE_MB = int(os.environ.get("SIONNA2_FOREIGN_RESERVE_MB", "14000"))
PREFER_RESERVE_MB = int(os.environ.get("SIONNA2_PREFER_RESERVE_MB", "2000"))
# ⭐ 2026-07-30 (지시 정정) — 선정기준은 **순위**이지 배제·상한이 아니다:
#     0순위 GPU 2·3 선호   1순위 메모리 여유   2순위 util·temp 낮은 것
#   0·1 도 필요하면 **제대로** 올린다(예전에 여기 3 GB 소액상한을 뒀는데, 그건 "쓰지 마라" 에
#   가까워 지시와 달랐다 — 폐기).


def _reserve_for(idx) -> int:
    """이 카드에서 **남에게 남겨 둘 메모리**[MiB]."""
    try:
        first = int(str(idx).split(",")[0])
    except Exception:
        return FOREIGN_RESERVE_MB
    return PREFER_RESERVE_MB if first in PREFER_GPUS else FOREIGN_RESERVE_MB


def _is_preferred(idx) -> bool:
    try:
        return int(str(idx).split(",")[0]) in PREFER_GPUS
    except Exception:
        return False


def gpu_status() -> list[dict]:
    """nvidia-smi → [{index, name, total_mb, used_mb, free_mb, util_pct, temp_c}, ...]

    ⭐ 2026-07-30: `temp_c` 추가 — 사용자 선정기준 2순위가 "util 및 temp 가 낮은 경우" 다.
      온도는 그 카드가 이미 오래 달리고 있다는 신호이므로, 여유·선호가 같을 때 식은 카드를 고른다."""
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True).stdout
    except Exception:
        return []
    rows = []
    for ln in out.strip().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 6:
            continue

        def _i(x, d=0):
            try:
                return int(float(x))
            except Exception:
                return d
        rows.append(dict(index=_i(p[0]), name=p[1], total_mb=_i(p[2]),
                         used_mb=_i(p[3]), free_mb=_i(p[4]), util_pct=_i(p[5]),
                         # temp 가 없거나 '[N/A]' 인 카드도 있다 → 0 으로 떨어뜨려 정렬만 무해하게
                         temp_c=_i(p[6]) if len(p) > 6 else 0))
    return rows


def pick(n: int = 1, min_free_mb: int = MIN_FREE_MB, verbose: bool = True) -> str:
    """**여유 메모리가 가장 많은** GPU n장을 잡고 CUDA_VISIBLE_DEVICES 를 세팅한다.

    사용률은 **탈락 기준이 아니다** — 100% 로 돌고 있어도 메모리가 남으면 같이 쓴다.
    (커널은 시분할되므로 조금 느려질 뿐이고, 우리 작업이 멈추는 것보다 낫다.)"""
    global _PICKED, _BUDGET_MB
    if _PICKED is not None:
        return _PICKED

    forced = os.environ.get("SIONNA2_GPU")
    if forced:
        os.environ["CUDA_VISIBLE_DEVICES"] = forced
        _PICKED = forced
        if verbose:
            print(f"[gpu] SIONNA2_GPU 강제 → GPU {forced}")
        return forced
    if "CUDA_VISIBLE_DEVICES" in os.environ:
        _PICKED = os.environ["CUDA_VISIBLE_DEVICES"]
        if verbose:
            print(f"[gpu] 이미 지정됨 → GPU {_PICKED}")
        return _PICKED

    st = gpu_status()
    if not st:
        _PICKED = "0"
        os.environ["CUDA_VISIBLE_DEVICES"] = _PICKED
        return _PICKED

    cand = [g for g in st if g["free_mb"] >= min_free_mb] or st
    # ⭐ 2026-07-30 사용자 방침: **GPU 2·3 을 0·1 보다 우선**한다(별도 지시가 있을 때까지).
    #   동적 할당은 유지하되, 여유가 **비슷한 수준**이면 선호 카드가 이긴다.
    #   "비슷한 수준" = 절대차 PREFER_TOL_MB 이내 **또는** 상대차 PREFER_TOL_FRAC 이내.
    #   여유가 뚜렷하게 큰 카드가 있으면 그쪽이 이긴다 — 그래야 "여유 많은 곳에 큰 작업" 방침과
    #   충돌하지 않는다.
    def _rank(g):
        # 0순위 선호 → 1순위 여유(계단) → 2순위 util+temp 낮은 것 → 3순위 여유 실값
        return (0 if g["index"] in PREFER_GPUS else 1,
                -_bucket(g["free_mb"]),
                g.get("util_pct", 0) + g.get("temp_c", 0),
                -g["free_mb"])
    cand.sort(key=_rank)
    chosen = cand[:max(1, int(n))]
    _PICKED = ",".join(str(g["index"]) for g in chosen)
    os.environ["CUDA_VISIBLE_DEVICES"] = _PICKED
    _BUDGET_MB = _compute_budget(min(g["free_mb"] for g in chosen))

    if verbose:
        print("[gpu] 현재 상태 (메모리 여유 기준으로 선택):")
        for g in st:
            mark = "  ← 선택" if g in chosen else ("  (여유 부족)" if g["free_mb"] < min_free_mb else "")
            print(f"       GPU {g['index']}  여유 {g['free_mb']:>6,} / {g['total_mb']:,} MiB"
                  f"   사용률 {g['util_pct']:>3d}%{mark}")
        print(f"[gpu] → CUDA_VISIBLE_DEVICES={_PICKED}   목표 사용량 ≈ {_BUDGET_MB:,} MiB")
    return _PICKED


def _compute_budget(free_mb: int) -> int:
    """예산[MiB]. ⚠ **여유를 절대 넘지 않는다**(2026-07-28 정정).

    옛 코드는 `max(MIN_TARGET_MB, free*0.92)` 라, 여유 1 GB 인 카드에서도 4 GB 를 예산이라
    답했다. 그 값으로 배치를 잡으면 당연히 OOM 이다 — 저여유 카드에 침투하려면 예산이
    여유를 따라 내려가야 한다."""
    # ⭐ 2026-07-30 카드 방침 적용: 남에게 남길 예비를 빼고, 비선호 카드(0·1)는 작은 배치 상한.
    idx = _PICKED if _PICKED is not None else os.environ.get("CUDA_VISIBLE_DEVICES", "0")
    cap = float(free_mb) * MEM_FRACTION
    if _is_preferred(idx):
        # 선호 카드(2·3): 한동안 우리 것이라는 정보가 있다 → 예비만 조금 남기고 화끈하게.
        cap = min(cap, max(ABS_MIN_MB, float(free_mb) - PREFER_RESERVE_MB))
    else:
        # 비선호 카드(0·1): 타 사용자가 13~14 GB 를 쓴다는 관측이 있으므로 그만큼 예비를 남긴다.
        # 단 **하한을 두지 않는다** — 필요하면 남은 만큼 제대로 쓴다.
        cap = min(cap, max(ABS_MIN_MB, float(free_mb) - FOREIGN_RESERVE_MB))
    env = os.environ.get("SIONNA2_GPU_MEM")
    if env:
        return int(max(ABS_MIN_MB, min(int(env), cap)))
    return int(max(ABS_MIN_MB, min(cap, max(MIN_TARGET_MB, cap))))


def refresh_budget() -> int:
    """예산을 **지금 다시 읽는다**. 공용 GPU 는 여유가 계속 변하므로, 긴 루프 중간에
    호출해 배치를 재조정하면 남는 메모리를 계속 따라가며 쓸 수 있다."""
    global _BUDGET_MB
    try:
        idx = int(str(_PICKED).split(",")[0]) if _PICKED is not None else 0
    except Exception:
        idx = 0
    st = {g["index"]: g for g in gpu_status()}
    free = st[idx]["free_mb"] if idx in st else ABS_MIN_MB
    _BUDGET_MB = _compute_budget(int(free))
    return _BUDGET_MB


def oom_backoff(fn, *args, batch: int = None, min_batch: int = 1, tries: int = 8, **kw):
    """⭐ **죽지 말고 줄여서 계속 돌려라** (2026-07-28 사용자 방침).

    `fn(batch=..., *args, **kw)` 를 부르되, CUDA OOM 이 나면 배치를 **반으로** 줄여 재시도한다.
    공용 GPU 에서 타 사용자가 갑자기 메모리를 잡아도 작업이 멈추지 않는다.
    batch=None 이면 fn 을 그대로 부르고, OOM 시 캐시만 비우고 재시도한다."""
    import torch                                    # 지연 import (CUDA 컨텍스트 보호)
    b = batch
    for k in range(tries):
        try:
            return fn(*args, **({"batch": b} if b is not None else {}), **kw)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            if b is None or b <= min_batch:
                if k == tries - 1:
                    raise
                continue
            b = max(min_batch, b // 2)
            print(f"[gpu] OOM → 배치 {b} 로 줄여 재시도 ({k+1}/{tries})", flush=True)
    raise RuntimeError("oom_backoff: 재시도 소진")


def all_usable(min_free_mb: int = MIN_FREE_MB) -> list[int]:
    """여유 메모리가 충분한 **모든** GPU 인덱스 (여유 많은 순).
    스윕(방위각·파형×드론 등)을 GPU 여러 장에 프로세스로 뿌릴 때 쓴다.

    ⭐ 2026-07-30: **카드 선호를 여기서도 적용한다.**
      ⚠ 이걸 안 해서 실제로 깨졌다 — `pick()` 에만 선호를 넣고 이 경로를 빼놓으니
        `parallel_over_gpus` 가 워커를 0·1 에도 뿌렸고, 그 카드 예산이 3 GB 로 줄어 있어
        워커가 **조용히 죽어 `BrokenProcessPool`** 이 났다(σ 격자, 2026-07-30 실측).
      선호 카드가 하나라도 쓸 만하면 **선호 카드만** 쓴다. 전부 부족하면 그때 비선호로 내려간다
      (0·1 에서는 예산이 작은 배치로 제한되므로 자연히 얌전하게 돈다).
      `SIONNA2_PREFER_ONLY=0` 으로 이 배타 동작을 끌 수 있다."""
    # ⭐⭐ 핀을 **존중한다** (2026-07-30, 두 번째 실패로 규명).
    #   ⚠ `SIONNA2_GPU=2` 로 카드를 박아 띄운 작업인데도 이 함수가 카드 3 까지 워커를 뿌렸다.
    #     그때 카드 3 은 report2 가 19.5 GB 를 쥐고 있어 워커가 즉사 → `BrokenProcessPool`.
    #     "카드당 무거운 작업 1개" 규칙은 **핀이 실제로 지켜져야** 성립한다.
    pin = os.environ.get("SIONNA2_GPU")
    if pin:
        want = {int(x) for x in str(pin).split(",") if x.strip().isdigit()}
        st = [g for g in gpu_status() if g["index"] in want]
        return [g["index"] for g in st]        # 여유가 적어도 핀은 지킨다(배치가 알아서 줄어든다)

    st = [g for g in gpu_status() if g["free_mb"] >= min_free_mb]
    st.sort(key=lambda g: (0 if g["index"] in PREFER_GPUS else 1,
                           -_bucket(g["free_mb"]),
                           g.get("util_pct", 0) + g.get("temp_c", 0),
                           -g["free_mb"]))
    return [g["index"] for g in st]


def parallel_over_gpus(items, worker, min_free_mb: int = MIN_FREE_MB, verbose: bool = True):
    """items 를 사용 가능한 GPU 들에 **프로세스로 나눠** 돌린다 (Mitsuba 는 프로세스당 1 GPU).
      worker : (gpu_index, sub_items) -> 결과 리스트   ※ 반드시 **모듈 최상위 함수**여야 한다
    반환: 원래 순서대로 합친 결과 리스트."""
    from concurrent.futures import ProcessPoolExecutor
    gpus = all_usable(min_free_mb) or [0]
    if verbose:
        print(f"[gpu] {len(items)}개 작업을 GPU {gpus} 에 분배")
    chunks = [(g, items[i::len(gpus)]) for i, g in enumerate(gpus)]
    order = [list(range(len(items)))[i::len(gpus)] for i in range(len(gpus))]
    with ProcessPoolExecutor(max_workers=len(gpus)) as ex:
        parts = list(ex.map(worker, [c[0] for c in chunks], [c[1] for c in chunks]))
    out = [None] * len(items)
    for idxs, res in zip(order, parts):
        for i, r in zip(idxs, res):
            out[i] = r
    return out


def budget_mb() -> int:
    """이 워크로드가 **써도 되는 GPU 메모리** [MiB]. 배치 크기를 여기에 맞춰 키울 것.

    ⚠ 2026-07-14 버그 수정: CUDA_VISIBLE_DEVICES / SIONNA2_GPU 가 **이미 설정돼 있으면**
      pick() 이 조기 return 하면서 _BUDGET_MB 를 세팅하지 않는다. 그때 예전 코드는 존재하지 않는
      DEFAULT_TARGET_MB 를 참조해 **NameError 로 죽었다** — 즉 `CUDA_VISIBLE_DEVICES=2 python ...`
      처럼 GPU 를 손으로 고정하면 rcs_sbr 의 배치 스윕이 즉사했다(report1 에이전트가 발견).
      이제 그 경우 **실제 여유 메모리를 다시 읽어** 예산을 잡는다."""
    global _BUDGET_MB
    if _BUDGET_MB is None:
        pick(verbose=False)
    if _BUDGET_MB is None:                       # 손으로 고정한 GPU → 그 GPU 의 여유를 읽는다
        try:
            idx = int(str(_PICKED).split(",")[0])
        except Exception:
            idx = 0
        st = {g["index"]: g for g in gpu_status()}
        free = st[idx]["free_mb"] if idx in st else MIN_TARGET_MB
        _BUDGET_MB = _compute_budget(int(free))
    return _BUDGET_MB


def batch_for(bytes_per_item: int, safety: float = 0.85, cap: int | None = None) -> int:
    """항목 1개가 bytes_per_item 바이트를 쓸 때, 예산 안에서 **한 번에 몇 개** 돌릴지.
    찔끔 쓰지 말고 예산을 채우는 것이 목적이다."""
    n = int(budget_mb() * 1024 * 1024 * safety / max(1, bytes_per_item))
    return max(1, min(n, cap) if cap else max(1, n))


def report() -> str:
    lines = []
    for g in gpu_status():
        lines.append(f"GPU {g['index']}  {g['name']:22s} 여유 {g['free_mb']:>6,}/{g['total_mb']:,} MiB "
                     f"사용률 {g['util_pct']:>3d}%")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(), "\n")
    pick(n=1)
    print(f"\n이 워크로드의 메모리 예산: {budget_mb():,} MiB")
    print(f"예: 항목당 1 KB 면 한 배치에 {batch_for(1024):,} 개")
