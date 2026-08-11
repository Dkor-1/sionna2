# -*- coding: utf-8 -*-
"""
probe_ray_ceiling.py — **Sionna PathSolver 가 한 번에 쏠 수 있는 광선 수의 상한**을 실측한다.

사용자(2026-08-10)
> "이론상 시오나 ray 를 한 번에 쏠 수 있는 광선의 수는 어떻게 되는지도 궁금해"

■ 소스가 말하는 것 (설치본 직독)
`sb_candidate_generator.py:285` 가 `spawn_ray_from_sources(fibonacci_lattice,
samples_per_src, src_positions)` 로 **광선을 한 번에 전부 할당**한다. 내부 청킹이 없다.
`sample_data.py:77` 이 `dr.alloc_local(SampleDataFields, max(1, max_depth))` 로
**샘플 하나당 스레드 로컬 버퍼**를 잡는다. 즉 메모리는 `광선 수 x (필드 크기 x max_depth)`
로 선다.
⇒ **알고리즘 상한은 없고 GPU 메모리가 상한이다.** 그래서 «이론상 몇 개» 는 카드마다 다르고,
  정직한 답은 **재보는 것**이다.

■ 어떻게 재나
같은 씬·같은 자세로 `samples_per_src` 를 두 배씩 올리며 부른다. 각 단에서
  · 성공/실패 · 걸린 시간 · **GPU 메모리 최고점**(nvidia-smi 로 표본)
  · 찾은 경로 수
를 기록하고, **처음 실패한 단**을 상한으로 적는다.
⚠ 실패는 예외로도 오지만 **조용히 죽기도** 한다(Dr.Jit 이 메모리 캐시를 flush 하다
  프로세스가 사라진 것을 오늘 봤다). 그래서 각 단을 **자식 프로세스로 격리**해 돌리고
  종료 코드로 판정한다.
⚠ 다른 작업이 같은 카드를 쓰면 상한이 내려간다 — 시작 시점의 여유를 함께 적는다.

    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/probe_ray_ceiling.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = f"{ROOT}/outputs/probe_ray_ceiling.json"
PY = sys.executable

# ⭐2848 M 은 통과하고 5696 M 이 «mitsuba.Sampler, int, int» 타입 오류로 죽었다.
#   5,696,000,000 > 2^32 = 4,294,967,296 이라 **32비트 정수 한계**가 의심된다.
#   메모리 한계가 아니다 — 2848 M 이 1.3 s 에 돌았고 메모리도 안 튀었다.
#   ⇒ 경계를 직접 좁혀 확인한다.
LADDER = [4_000_000_000, 4_294_967_295, 4_294_967_296, 4_400_000_000]


def gpu_free_mib(idx: int) -> tuple[int, int]:
    q = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total",
         "--format=csv,noheader,nounits", f"--id={idx}"],
        capture_output=True, text=True).stdout.strip().split(", ")
    return int(q[0]), int(q[1])


CHILD = r'''
import json, os, sys, time
sys.path.insert(0, os.path.join(r"%s", "src"))
sys.path.insert(0, os.path.join(r"%s", "benchmark"))
from gpu import pick
pick(verbose=False)
import numpy as np
import report15_probe as RP
from articulated_fast import FastPoser
from drones import DRONES, DRONE_GROUP_MAT, drone_colors

spp = int(sys.argv[1])
spec = DRONES["matrice4e"]
fp = FastPoser(spec)
m = fp.pose(np.zeros(len(fp.dirs))).to_mesh()
d = os.path.join(RP.SCRATCH, "ceil_probe")
paths = m.write_obj_per_group(d, spec.key)
cols = drone_colors(spec)
parts = [RP.Part(name=f"{spec.key}_{g}", obj=p, mat_key=DRONE_GROUP_MAT[g][0],
                 color=cols[g]) for g, p in paths.items()]
sc = RP.build_scene(parts, fc=3.5e9)
RP.place(sc, az=0.0, el=-15.0, rng=40.0, baseline=0.0)
t0 = time.time()
p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                       diffuse_reflection=True, refraction=False,
                       samples_per_src=spp,
                       max_num_paths_per_src=RP.MAX_PATHS, seed=1)
try:
    aa, tau, _, O = RP.unpack(p)
    npaths = int(aa.size)
except ValueError:
    npaths = 0
RP.drop_scratch(d)
print(json.dumps({"ok": True, "seconds": time.time() - t0, "n_paths": npaths}))
''' % (ROOT, ROOT)


def main() -> None:
    gpu = int(os.environ.get("SIONNA2_GPU", "2"))
    used0, total = gpu_free_mib(gpu)
    print(f"\n═══ Sionna PathSolver 광선 상한 실측 · GPU {gpu} "
          f"(시작 시점 {used0}/{total} MiB, 여유 {total-used0} MiB) ═══\n", flush=True)

    child = f"{ROOT}/outputs/_ceil_child.py"
    open(child, "w").write(CHILD)
    rows, ceiling = [], None
    for spp in LADDER:
        u0, _ = gpu_free_mib(gpu)
        t0 = time.time()
        r = subprocess.run([PY, child, str(spp)], capture_output=True, text=True,
                           env={**os.environ, "SIONNA2_GPU": str(gpu)})
        secs = time.time() - t0
        ok = r.returncode == 0 and '"ok": true' in r.stdout.lower()
        u1, _ = gpu_free_mib(gpu)
        info = {}
        if ok:
            try:
                info = json.loads([l for l in r.stdout.splitlines()
                                   if l.startswith("{")][-1])
            except Exception:
                ok = False
        err = "" if ok else (r.stderr.strip().splitlines()[-1][:160]
                             if r.stderr.strip() else f"조용히 죽음 rc={r.returncode}")
        rows.append(dict(spp=spp, spp_m=spp / 1e6, ok=bool(ok),
                         seconds=round(info.get("seconds", secs), 1),
                         n_paths=info.get("n_paths"),
                         gpu_used_before_mib=u0, gpu_used_after_mib=u1,
                         error=err))
        print(f"  {spp/1e6:>8.0f} M 발  {'✅' if ok else '❌'}  "
              f"{info.get('seconds', secs):>6.1f} s  경로 {info.get('n_paths', '—')}"
              f"{'' if ok else '   ← ' + err}", flush=True)
        if not ok:
            ceiling = spp
            break
    os.remove(child)

    last_ok = max([r["spp"] for r in rows if r["ok"]], default=0)
    json.dump({"_meta": {
        "generator": "benchmark/probe_ray_ceiling.py",
        "question_ko": "PathSolver 가 한 번에 쏠 수 있는 광선 수의 상한",
        "source_ko": "sb_candidate_generator.py:285 spawn_ray_from_sources 가 광선을 "
                     "한 번에 전부 할당한다(내부 청킹 없음). sample_data.py:77 이 "
                     "샘플당 스레드 로컬 버퍼를 max_depth 만큼 잡는다. "
                     "⇒ 알고리즘 상한이 아니라 GPU 메모리가 상한이다.",
        "caveat_ko": "다른 작업이 같은 카드를 쓰면 상한이 내려간다. 이 값은 "
                     "«이 카드에서 이 여유일 때» 의 상한이다.",
        "gpu": gpu, "gpu_total_mib": total, "gpu_used_at_start_mib": used0,
        "scene": "matrice4e · 40 m · max_depth 1 · 확산 켬",
        "ladder": LADDER},
        "rows": rows,
        "verdict": dict(
            max_ok_spp=last_ok, max_ok_spp_m=last_ok / 1e6,
            first_fail_spp=ceiling, first_fail_spp_m=(ceiling / 1e6) if ceiling else None,
            deck_40m_spp=178_000_000,
            headroom_vs_deck=(last_ok / 178_000_000) if last_ok else None)},
        open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n⭐성공한 최대 {last_ok/1e6:.0f} M 발"
          + (f" · 처음 실패 {ceiling/1e6:.0f} M" if ceiling else " (사다리 끝까지 통과)")
          + f"\n   덱의 40 m 판({178:.0f} M)의 {last_ok/178e6:.1f} 배\n\n✅ {OUT}")


if __name__ == "__main__":
    main()
