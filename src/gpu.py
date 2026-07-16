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
  SIONNA2_GPU_MEM=10000  이 워크로드가 쓸 목표 메모리 [MiB] (기본: 여유의 70%, 최대 16 GB)
"""
from __future__ import annotations

import os
import subprocess

_PICKED: str | None = None
_BUDGET_MB: int | None = None

#  사용자 지시(2026-07-14): "점유 가능하면 최대한 점유해서 써버려".
#  → 여유 메모리의 FRACTION 만큼을 이 워크로드의 예산으로 잡는다. 찔끔 쓰지 않는다.
MEM_FRACTION = 0.92                 # 여유 메모리의 92% 를 예산으로 (아끼지 않는다)
MIN_TARGET_MB = 4_000               # 그래도 최소 4 GB 는 확보
MIN_FREE_MB = 2_000                 # 사용자 영구방침(2026-07-14): 2GB 이상 여유면 침투해서 쓴다


def gpu_status() -> list[dict]:
    """nvidia-smi → [{index, name, total_mb, used_mb, free_mb, util_pct}, ...]"""
    try:
        out = subprocess.run(
            ["nvidia-smi",
             "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True).stdout
    except Exception:
        return []
    rows = []
    for ln in out.strip().splitlines():
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 6:
            continue
        rows.append(dict(index=int(p[0]), name=p[1], total_mb=int(p[2]),
                         used_mb=int(p[3]), free_mb=int(p[4]), util_pct=int(p[5])))
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
    cand.sort(key=lambda g: -g["free_mb"])              # **여유 메모리 내림차순**
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
    env = os.environ.get("SIONNA2_GPU_MEM")
    if env:
        return int(env)
    return int(max(MIN_TARGET_MB, free_mb * MEM_FRACTION))


def all_usable(min_free_mb: int = MIN_FREE_MB) -> list[int]:
    """여유 메모리가 충분한 **모든** GPU 인덱스 (여유 많은 순).
    스윕(방위각·파형×드론 등)을 GPU 여러 장에 프로세스로 뿌릴 때 쓴다."""
    st = [g for g in gpu_status() if g["free_mb"] >= min_free_mb]
    st.sort(key=lambda g: -g["free_mb"])
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
