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
import json
import glob
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
    # ⭐ 2026-07-29 추가 — SBR+PO 커널의 **유효 kr 구간 선언**. 66초밖에 안 걸리는데
    #   "하겠다"고 적어두고 3개월 미뤄져 있었다. 커널·메쉬를 고치면 반드시 다시 재야 한다.
    (2, "SBR 유효 kr 구간(Mie+해석PO)", ["benchmark/verify_sbr_kr_sweep.py"], "sbr_kr_sweep.json"),
    # ⚠ rt_pipeline.py → report7_rt.json 은 2026-07-22 제거했다 — 리포트 재편 후 **소비자가 없는
    #   닫힌 고리**(rt_pipeline → report7_rt.json → viz_report7.py → 아무도 안 읽는 그림)였다.

    # 3) 마이크로도플러 — 프롭 형상에 직접 의존(무겁다, GPU)
    (3, "마이크로도플러 전 기종", ["src/viz_report1.py", "--only", "md"], "report1.json(microdoppler)"),

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
    # ⭐ 2026-07-29 추가 — 이 둘이 파이프라인에서 **빠져 있었다**. 메쉬를 고쳐도 조용히 낡아서
    #   손으로 기억해 돌려야 했고, 실제로 두 번 잊혀 낡은 채 리포트에 실렸다.
    (4, "RCS 절대앵커·분포적합", ["benchmark/rcs_anchor.py"], "rcs_anchor.json"),
    (4, "자유공간 σ 격자(무겁다)", ["src/experiment_freespace_sigma.py"], "report13_sigma_grid.json"),

    # 5) 리포트 재조립 — 위 json 을 읽어 마크다운으로 굳힌다
    (5, "리포트 01~13 재빌드", ["--notebooks--"], "report01..13.ipynb"),
]

# 재실행 필요 판정의 기준이 되는 **메쉬 소스** — 이보다 낡은 산출물은 다시 만들어야 한다.
MESH_SOURCES = ["src/drone_cad.py", "src/drones.py", "src/materials.py"]

PY = sys.executable


def _run(cmd: list[str], env: dict) -> tuple[bool, float]:
    t0 = time.time()
    if cmd == ["--notebooks--"]:
        # ⚠ 2026-07-31 재편 — 구 `make_notebook01~13.py` 는 삭제됐다(리포트 13편 → 6편,
        #   docs/REBUILD_2026-07-30.md). 옛 코드는 1..13 을 **하드코딩**해서 편수가 바뀌자
        #   존재하지 않는 파일을 부르고 있었다. 이제 디스크를 훑어 실제 빌더만 부른다 —
        #   편수가 또 바뀌어도 여기는 고칠 필요가 없다.
        builders = sorted(glob.glob(os.path.join(ROOT, "src", "make_report*.py")))
        if not builders:
            print("    ✗ 리포트 빌더를 찾지 못했다 (src/make_report*.py)")
            return False, time.time() - t0
        ok = True
        for path in builders:
            name = os.path.basename(path)[:-3]          # make_report02_target
            r = subprocess.run([PY, path], cwd=ROOT, env=env, capture_output=True, text=True)
            if r.returncode != 0:
                tail = r.stderr.strip().splitlines()
                print(f"    ✗ {name}: {tail[-1][:160] if tail else '(stderr 없음)'}")
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
    # ⭐ 2026-07-29 추가 — 재개 수단이 없어서, stage4 가 CFAR 에서 조용히 죽었을 때
    #   되살릴 방법이 "처음부터 2시간 중복 계산" 뿐이었다.
    ap.add_argument("--skip-done", action="store_true",
                    help="산출물이 메쉬 소스보다 새로우면 건너뛴다 (죽은 실행 재개용). "
                         "⚠ mtime 비교라 **과보수적**이다 — 주석만 고쳐도 전부 낡은 것으로 본다. "
                         "안전한 방향으로 틀리므로(덜 돌리는 게 아니라 더 돌린다) 기본값으로 둔다.")
    ap.add_argument("--baseline", default=None, metavar="MM-DD_HH:MM",
                    help="기준 시각을 손으로 준다. 메쉬 소스 편집이 주석뿐이었음을 **확인했을 때만** 쓸 것. "
                         "예: --baseline 07-29_06:40")
    ap.add_argument("--from", dest="from_label", default=None,
                    help="이 라벨(부분일치)부터 실행")
    ap.add_argument("--dry-run", action="store_true", help="무엇을 돌리고 무엇을 건너뛸지만 출력")
    a = ap.parse_args()

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark"), env.get("PYTHONPATH", "")])

    todo = [s for s in STAGES if a.stage is None or s[0] == a.stage]

    if a.from_label:
        idx = next((i for i, s in enumerate(todo) if a.from_label in s[1]), None)
        if idx is None:
            print(f"❌ --from '{a.from_label}' 에 맞는 라벨이 없다. --list 로 확인할 것.")
            return 2
        todo = todo[idx:]

    # 메쉬 소스보다 새로운 산출물은 최신이다 (--skip-done)
    if a.baseline:
        src_mtime = time.mktime(time.strptime(
            f"{time.strftime('%Y')}-{a.baseline}", "%Y-%m-%d_%H:%M"))
        print(f"⚠ 기준 시각을 손으로 받았다: {a.baseline} — 메쉬 소스 편집이 계산에 무관함을 "
              f"확인했을 때만 유효하다.")
    else:
        src_mtime = max((os.path.getmtime(os.path.join(ROOT, p))
                         for p in MESH_SOURCES if os.path.exists(os.path.join(ROOT, p))), default=0.0)

    def _is_fresh(out: str) -> bool:
        """산출물이 메쉬 소스보다 새로운가. 파일명이 'a.json(주석)' 형태면 앞부분만 쓴다."""
        name = out.split("(")[0].strip()
        if not name.endswith(".json"):
            return False                      # 노트북 단계 등은 항상 다시 만든다 (싸다)
        p = os.path.join(ROOT, "outputs", name)
        return os.path.exists(p) and os.path.getmtime(p) >= src_mtime

    if a.list or a.dry_run:
        for st, label, cmd, out in todo:
            mark = "건너뜀" if (a.skip_done and _is_fresh(out)) else "실행 "
            print(f"  [{st}] {mark} {label:26s} → {out:34s}  ({' '.join(cmd)})")
        print(f"\n  기준 메쉬 소스 시각: {time.strftime('%m-%d %H:%M', time.localtime(src_mtime))}"
              f"  ({', '.join(MESH_SOURCES)})")
        return 0

    fails, skipped, times = [], [], {}
    for st, label, cmd, out in todo:
        if a.skip_done and _is_fresh(out):
            print(f"\n[{st}] {label} … ⏭ 건너뜀(산출물이 메쉬보다 새롭다)", flush=True)
            skipped.append(label)
            continue
        print(f"\n[{st}] {label} …", flush=True)
        ok, dt = _run(cmd, env)
        times[label] = round(dt, 1)
        print(f"    {'✅' if ok else '❌'} {out}  [{dt:.0f}s]", flush=True)
        if not ok:
            fails.append(label)
    if skipped:
        print(f"\n⏭ 건너뛴 {len(skipped)}건: {', '.join(skipped)}")
    # ⭐ 실측 소요를 남긴다 — 7종 확장 등 앞으로의 시간 추정 근거가 된다(RESUME 문서의 소요 원장).
    if times:
        tp = os.path.join(ROOT, "outputs", "regen_timings.json")
        try:
            old = json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else {}
        except Exception:
            old = {}
        old[time.strftime("%Y-%m-%dT%H:%M")] = times
        with open(tp, "w", encoding="utf-8") as f:
            json.dump(old, f, indent=2, ensure_ascii=False)
        print(f"⏱ 실측 소요 기록 → outputs/regen_timings.json")
    print(f"\n{'✅ 전부 성공' if not fails else '❌ 실패: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
