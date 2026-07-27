#!/usr/bin/env python
"""메쉬가 바뀌었을 때 **되살려야 하는 산출물 전부**를 의존성 순서로 다시 만든다.

왜 이 스크립트가 있나
---------------------
드론 CAD 를 한 줄만 고쳐도 σ 가 바뀌고, σ 는 링크버짓·SCR·Pd·리포트 표까지 줄줄이 타고 내려간다.
어떤 json 이 메쉬에 의존하는지는 `build_drone`/`build_propeller`/`pose_articulated` 를 import 하는
생산 스크립트를 훑으면 나오는데, 그걸 매번 손으로 세면 하나씩 빠진다 — 그래서 여기 고정해 둔다.

목록의 근거(2026-07-22 전수조사):
  grep -rln "build_drone|pose_articulated|build_propeller|build_frame" src benchmark
  → 각 파일이 쓰는 outputs/*.json 을 모아 아래 STAGES 로 정리.

⚠ σ 디스크캐시(`outputs/sigma_sbr_cache.json`)는 키에 **메쉬 지문**이 들어가므로(benchmark/channel.py
  `_mesh_fp`) 메쉬가 바뀌면 저절로 미스가 난다 — 손으로 지울 필요 없다.

사용
----
  python benchmark/regen_mesh_dependents.py --list        # 무엇이 돌지만 본다
  python benchmark/regen_mesh_dependents.py --stage 1     # 한 단계만
  python benchmark/regen_mesh_dependents.py               # 전부 (오래 걸린다)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# (스테이지, 라벨, 커맨드, 산출물) — 스테이지 안은 서로 독립이라 병렬 가능, 스테이지 사이는 순서 의존
STAGES: list[tuple[int, str, list[str], str]] = [
    # 1) 메쉬 자체의 기하·품질 — 뒤 단계가 전부 이걸 전제로 한다
    (1, "report1 메쉬/외형/불리언", ["src/viz_report1.py", "--only", "mesh,cad"], "report1.json"),
    (1, "phantom4 실물스캔 대조", ["src/compare_phantom_scan.py"], "phantom4_scan_compare.json"),
    (1, "커뮤니티 CAD 대조", ["benchmark/compare_community.py"], "community_compare.json"),
    (1, "실물 CAD 대조", ["benchmark/compare_real_cad.py"], "real_cad_compare.json"),

    # 2) RCS — 모든 링크버짓·검출의 입력
    (2, "report2 파형·RCS 표", ["src/viz_report2.py"], "report2_waveform_rcs.json"),
    (2, "SBR 검증(커널·투과·지터)", ["src/viz_verify_sbr.py", "--force"], "report6_sbr.json"),
    (2, "RT 광선예산", ["benchmark/verify_rt_rays.py"], "rt_ray_budget.json"),
    (2, "RT 실험(스톡 solver 한계)", ["benchmark/rt_experiments.py"], "report3_rt.json"),
    # ⚠ rt_pipeline.py → report7_rt.json 은 2026-07-22 제거했다 — 리포트 재편 후 **소비자가 없는
    #   닫힌 고리**(rt_pipeline → report7_rt.json → viz_report7.py → 아무도 안 읽는 그림)였다.

    # 3) 마이크로도플러 — 프롭 형상에 직접 의존(무겁다, GPU)
    (3, "마이크로도플러 5종", ["src/viz_report1.py", "--only", "md"], "report1.json(microdoppler)"),

    # 4) 링크버짓·클러터·검출 — σ 를 소비한다
    (4, "링크버짓", ["benchmark/verify_linkbudget.py"], "verify_linkbudget.json"),
    (4, "바닥유령", ["benchmark/verify_floor_ghost.py"], "floor_ghost_verify.json"),
    (4, "RT 표적 검증", ["benchmark/verify_target_rt.py"], "rt_target_verify.json"),
    (4, "RT 표적 σ 부재 실증", ["benchmark/verify_rt_no_rcs.py"], "rt_no_rcs_verify.json"),
    (4, "모호도(속도·거리)", ["benchmark/verify_ambiguity.py"], "verify_ambiguity.json"),
    (4, "ECA 검증", ["benchmark/verify_eca.py"], "verify_eca.json"),
    (4, "관측성", ["benchmark/verify_observability.py"], "verify_observability.json"),
    (4, "유령 영향", ["benchmark/verify_ghost_impact.py"], "verify_ghost_impact.json"),
    (4, "report4 보정", ["benchmark/report4_fixups.py"], "report4_fixups.json"),
    (4, "CFAR 대량 MC(무겁다)", ["benchmark/verify_cfar.py"], "verify_cfar.json"),
    (4, "벤치 매트릭스(무겁다)", ["benchmark/run_matrix.py"], "report5_results.json"),
    (4, "유령 검출 실험", ["src/experiment_ghost.py"], "detection_ghost.json"),
    (4, "검출 Rx 스윕(헤드라인)", ["src/experiment_detection.py"], "detection_rx_sweep.json"),

    # 5) 리포트 재조립 — 위 json 을 읽어 마크다운으로 굳힌다
    (5, "리포트 01~12 재빌드", ["--notebooks--"], "report01..12.ipynb"),
]

PY = sys.executable


def _run(cmd: list[str], env: dict) -> tuple[bool, float]:
    t0 = time.time()
    if cmd == ["--notebooks--"]:
        ok = True
        for n in [f"{i:02d}" for i in range(1, 13)]:
            r = subprocess.run([PY, os.path.join(ROOT, "src", f"make_notebook{n}.py")],
                               cwd=ROOT, env=env, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"    ✗ report{n}: {r.stderr.strip().splitlines()[-1][:160]}")
                ok = False
        return ok, time.time() - t0
    r = subprocess.run([PY] + [os.path.join(ROOT, c) if c.endswith(".py") else c for c in cmd],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        print(f"    ✗ {tail[:200]}")
    return r.returncode == 0, time.time() - t0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, default=None, help="이 스테이지만 실행")
    ap.add_argument("--list", action="store_true", help="실행 계획만 출력")
    a = ap.parse_args()

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark"), env.get("PYTHONPATH", "")])

    todo = [s for s in STAGES if a.stage is None or s[0] == a.stage]
    if a.list:
        for st, label, cmd, out in todo:
            print(f"  [{st}] {label:28s} → {out:34s}  ({' '.join(cmd)})")
        return 0

    fails = []
    for st, label, cmd, out in todo:
        print(f"\n[{st}] {label} …", flush=True)
        ok, dt = _run(cmd, env)
        print(f"    {'✅' if ok else '❌'} {out}  [{dt:.0f}s]", flush=True)
        if not ok:
            fails.append(label)
    print(f"\n{'✅ 전부 성공' if not fails else '❌ 실패: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
