#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""2.1.0 의 결정 모드가 무엇을 바꾸나 — 「같은 줄이 몇 번 적히나」 (2026-09-14).

    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/det_mode_dedup_0914.py

왜 있나
-------
사용자 점검 메모(`docs/UPGRADE_REVIEW_0914.md`)가 새 `PathSolver(deterministic=…)` 두 모드에서
합산 전계 크기가 **−0.760857 dB** 갈린다고 냈다. 그 수는 자릿수까지 재현된다.
이 스크립트는 **그 다음 물음**의 답이다 — 무엇이 달라져서 그 차이가 나나.

⛔⛔**2026-09-14 정정 — 첫 판이 틀렸다.** 처음에 나는 그 −0.760857 dB 를 「결정 모드를 켠
효과」로 적었다. **아니다.** 같은 설정에서 **스레드만 4 로 올리면 기본 모드 혼자서**
경로 8057~8059 를 내고 |E| 폭이 **1.59 dB** 다(5 판 실측). 결정 모드는 같은 조건 5 판이
**0.000 dB** 다. ⇒ −0.76 dB 는 **이미 있던 실행별 흔들림에서 한 번 뽑은 값**이지 모드가
만든 양이 아니다. 이 저장소는 그 흔들림을 2026-09-03 에 이미 적었다
(`outputs/thread_ladder_0903.json` — 스레드 2 에서 경로 수 [8058, 8059]).

⇒ **제대로 말하면 이렇다**: 결정 모드가 하는 일은 **실행별 폭을 0 으로 만드는 것**이다.
  한 판과 한 판을 견준 −0.76 dB 는 그 폭 안의 한 점이다.

그럼 한 판끼리는 무엇이 다른가 — 지연으로 짝지어 보면 **개수가 다른 지연이 하나**뿐이고,
그 자리에서 **같은 복소값이 9 벌 → 8 벌**로 준다. 개수가 같은데 값이 바뀐 지연은 0 개다.
⇒ **중복(같은 줄이 몇 번 적히나)만 다르다.** 중복을 빼면 두 모드의 경로 집합과 결맞음 합이
**비트까지 같다**(상대차 0.0e+00).

⭐기구는 `docs/DEEP_DROP_0902.md` 의 「깊은 낙차」와 같다 — 같은 경로 N 벌 중 하나가 빠진다
(거기 N=2/3/4, 여기 N=9).
⛔⛔**다만 전체 |E| 비는 (N−1)/N 이 아니다.** 8/9 는 **그 사본 무리 안에서만** 성립한다
(무리 합 비 0.888897). 나머지 8,050 줄이 다른 위상으로 함께 들어 있어 **전체** 비는
0.9161(−0.7609 dB)이고 8/9(−1.0231 dB)가 아니다. 첫 판은 이 둘을 뭉뚱그렸다.

⭐상류 소스가 말하는 것(`sionna/rt/path_solvers/sb_deterministic.py`): 결정 모드는 같은
해시 통 중복제거를 쓰되 「먼저 올린 스레드」 대신 **가장 작은 스레드 번호**를 승자로 못 박는다.
곧 **덜 찾는 것도 중복을 지우는 것도 아니고, 누가 이기나만 결정적으로** 만든다.

⛔말하지 않는 것
  · ⛔어느 모드가 물리적으로 옳은지 판정하지 않는다. ⛔「2.1.0 이 깊은 낙차를 고쳤다」도 아니다.
  · ⛔CPU·합성 평판에서 잰 것이다 — 드론 코퍼스도 GPU 도 아니다.
  · ⛔아래 설정은 우리가 고른 것이지 전수가 아니다.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

#: 메모가 쓴 설정 그대로 — outputs/upgrade_review_0914.json 의 checks.cpu_modes.settings
KW = dict(max_depth=2, los=False, specular_reflection=True, diffuse_reflection=True,
          refraction=False, diffraction=False, edge_diffraction=False,
          samples_per_src=40_000_000, max_num_paths_per_src=2_000_000, seed=42)

#: 흔들어 볼 손잡이 — (평판 한 변, 산란, 씨앗, 광선, 깊이, 이름)
LADDER = [
    (24, 0.7, 42, 40_000_000, 2, "메모 설정 그대로"),
    (24, 0.7, 7, 40_000_000, 2, "씨앗 7"),
    (24, 0.7, 1981, 40_000_000, 2, "씨앗 1981 (#1142 재현 씨앗)"),
    (16, 0.7, 42, 40_000_000, 2, "평판 256 장"),
    (24, 0.3, 42, 40_000_000, 2, "산란 0.3"),
    (24, 0.7, 42, 10_000_000, 2, "광선 1e7"),
    (24, 0.7, 42, 40_000_000, 1, "깊이 1"),
]


def _repro():
    spec = importlib.util.spec_from_file_location(
        "minrepro_hash_0902", os.path.join(HERE, "minrepro_hash_0902.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def dedup(a, tau):
    """같은 (지연·복소진폭) 줄을 한 번만 센다 — 샤드의 `E_dedup` 과 같은 정의."""
    k = np.stack([np.round(tau, 15), np.round(a.real, 18), np.round(a.imag, 18)], 1)
    _, idx = np.unique(k, axis=0, return_index=True)
    return a[idx], tau[idx]


def solve(rt, sc, fc, mode, kw):
    p = rt.PathSolver(deterministic=mode)(sc, **kw)
    ar = np.array(p.a[0], copy=True).astype(np.float64)
    ai = np.array(p.a[1], copy=True).astype(np.float64)
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    tau = np.array(p.tau, copy=True).astype(np.float64).reshape(-1, a.size)[0]
    return a, tau


def main() -> int:
    import drjit as dr
    import mitsuba as mi
    import sionna.rt as rt
    dr.set_thread_count(1)                 # ⛔한 스레드 — 여러 스레드는 다른 물음이다
    repro = _repro()
    print(f"═══ 결정 모드 ↔ 중복 ═══  변종 {mi.variant()} · 스레드 {dr.thread_count()}")
    print(f"{'설정':<30}{'경로 기본→결정':>16}{'그대로 dB':>11}"
          f"{'중복뺀 경로':>13}{'중복뺀 dB':>13}{'상대차':>10}  비트동일")
    bad = 0
    for n_side, scat, seed, spp, depth, lab in LADDER:
        sc, _nf = repro.build(n_side, scat)
        kw = dict(KW, seed=seed, samples_per_src=spp, max_depth=depth)
        out = []
        for mode in (False, True):
            a, tau = solve(rt, sc, repro.FC, mode, kw)
            da, dt = dedup(a, tau)
            h = np.sum(a * np.exp(-2j * np.pi * repro.FC * tau))
            hd = np.sum(da * np.exp(-2j * np.pi * repro.FC * dt))
            out.append((len(a), h, da, dt, hd))
        (nF, hF, aFd, tFd, hFd), (nT, hT, aTd, tTd, hTd) = out
        same = (len(aFd) == len(aTd)
                and np.array_equal(np.sort_complex(aFd), np.sort_complex(aTd))
                and np.array_equal(np.sort(tFd), np.sort(tTd)))
        rel = abs(hTd - hFd) / abs(hFd) if abs(hFd) > 0 else float("nan")
        bad += not same
        print(f"{lab:<30}{f'{nF} → {nT}':>16}{20*np.log10(abs(hT)/abs(hF)):>+11.4f}"
              f"{f'{len(aFd)} = {len(aTd)}':>13}"
              f"{20*np.log10(abs(hTd)/abs(hFd)):>+13.9f}{rel:>10.1e}"
              f"  {'✅' if same else '⛔'}")
    #: ⭐⭐**스레드 축** — 여기가 첫 판이 놓친 자리다. 한 스레드에서는 두 모드가 각각
    #  되풀이 가능해서 「모드가 −0.76 dB 를 만든다」로 읽힌다. 스레드를 올리면 **기본 모드
    #  혼자** 그만큼(더) 흔들리고, 결정 모드는 0 이 된다.
    print(f"\n── ⭐스레드를 올리면 (같은 설정 · 5 판씩) ──")
    sc, _nf = repro.build(24, 0.7)
    for nthr in (1, 4):
        dr.set_thread_count(nthr)
        line = []
        for mode in (False, True):
            hs, ns = [], []
            for _ in range(5):
                a, tau = solve(rt, sc, repro.FC, mode, dict(KW))
                ns.append(len(a))
                hs.append(abs(np.sum(a * np.exp(-2j * np.pi * repro.FC * tau))))
            span = 20 * np.log10(max(hs) / min(hs)) if min(hs) > 0 else 0.0
            line.append(f"det={str(mode):<5} 경로 {min(ns)}~{max(ns)} · |E| 폭 {span:8.4f} dB")
        print(f"  스레드 {nthr:>3}   {line[0]}   |   {line[1]}")
    dr.set_thread_count(1)
    if bad:
        print(f"\n⛔중복을 뺐는데도 갈리는 설정이 {bad} 개다 — 그때는 판이 정말 다른 것을 낸다.")
        return 1
    print("\n✅ 흔든 설정 전부에서 **중복만** 다르다 — 중복을 빼면 경로 집합과 결맞음 합이 비트까지 같다.")
    print("⭐결정 모드가 하는 일은 **실행별 폭을 0 으로 만드는 것**이다 — 한 판끼리의 dB 차가 아니다.")
    print("⛔어느 모드가 물리적으로 옳은지는 이 관측으로 못 고른다. ⛔CPU·합성 평판 범위다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
