# -*- coding: utf-8 -*-
"""verify_grid_shift.py — ⭐`--grid-shift`(격자 위상 널) **배선 게이트**. ⛔GPU 0.

무엇을 지키나 — 계약 넷
  G1 **안 주면 비트 동일**  `--grid-shift` 를 안 주거나 0 이면 판을 아예 안 옮기고 꼬리표도
     안 붙는다 → 파일 이름이 옛 샤드와 **글자 그대로** 같아 이미 계산한 것을 그대로 쓴다.
  G2 **옮기기만 한다**      격자 간격 d · 칸 수 n · 광선 수 n² · Rout 이 하나도 안 변하고,
     이동은 **광선 평면 안**(û 에 수직)에서만 일어난다. 크기가 같이 변하면 «촘촘함» 과
     «찍는 자리» 가 다시 섞여 실험이 무의미해진다.
  G3 **덮개가 남는다**      반 칸(그리고 한 칸) 옮겨도 표적이 격자 안에 든다. 여유가 몇 칸
     남는지 수로 남긴다(모자라면 커널이 첫 자세에서 예외를 던지지만, 사전에 알아야 발주한다).
  G4 **불순물이 작다**      구면파 판에서는 송신점 p_tx = ctr + R·û 가 같이 옮겨진다. 그게
     만드는 위상차가 «표본이 옮겨져서» 생기는 위상차보다 훨씬 작아야 순수 대조다.

왜 GPU 를 안 쓰나 — 이 게이트가 보는 것은 **격자를 정하는 산수**뿐이고, 그 산수는 순수
numpy 다. `rcs_sbr.py` 에서 격자 함수만 소스로 떼어 실행하므로 mitsuba·sionna.rt 를
임포트하지 않는다(카드는 큐가 쓴다). 광선을 실제로 쏘는 회귀는 `verify_frozen_grid.py` 다.

    cd /workspace/sionna && PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/verify_grid_shift.py

산출  outputs/verify_grid_shift.json      (읽는 법은 docs/GRID_PHASE_NULL.md)
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import tempfile
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = f"{ROOT}/outputs/verify_grid_shift.json"
FC, LAM = 3.5e9, 2.998e8 / 3.5e9
N_POSES, RANGE_M = 8192, 15.0            # 큐가 실제로 쓰는 판
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
DIVS = (12, 24, 48)

RESULT = []


def ok(name, cond, extra=""):
    RESULT.append(dict(check=name, passed=bool(cond), detail=str(extra)))
    print(f"  {'✅' if cond else '⛔'} {name} {extra}")
    return bool(cond)


# ═══ 0. rcs_sbr 의 격자 함수만 떼어 온다 (mitsuba 없이) ══════════════════════
def grid_funcs() -> dict:
    """`src/rcs_sbr.py` 에서 격자 관련 함수/클래스만 **소스 그대로** 실행한다.

    복사가 아니라 발췌라서 원본이 바뀌면 이 게이트도 같이 바뀐다(장부가 안 갈린다)."""
    src = open(f"{ROOT}/src/rcs_sbr.py", encoding="utf-8").read()
    want = ["GridRef", "as_grid_ref", "_verts_of", "grid_ref_from", "grid_ref_shift",
            "_grid_basis", "_grid_cover", "grid_ref_margin"]
    segs = {n.name: ast.get_source_segment(src, n)
            for n in ast.parse(src).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in want}
    miss = [w for w in want if w not in segs]
    if miss:
        raise SystemExit(f"⛔ rcs_sbr.py 에서 못 찾은 것: {miss}")
    from typing import NamedTuple
    ns = {"np": np, "NamedTuple": NamedTuple, "C0": 299792458.0, "DEFAULT_DIV": 12}
    exec("\n\n".join(segs[w] for w in want), ns)          # noqa: S102
    return ns


def los(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main() -> int:
    G = grid_funcs()
    grid_ref_from, grid_ref_shift = G["grid_ref_from"], G["grid_ref_shift"]
    grid_ref_margin, _grid_basis = G["grid_ref_margin"], G["_grid_basis"]

    from articulated_fast import FastPoser, rotor_phases      # numpy 전용
    from drones import DRONES
    TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
    fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
    ph = rotor_phases(np.arange(N_POSES) / float(TJ["prf_hz"]),
                      np.asarray(TJ["rpm_per_rotor"], float), fp.dirs)
    #: run() 이 얼린 판을 만들 때 쓰는 바로 그 표본(자세 64 개)
    probes = [fp.pose(ph[i]) for i in range(0, N_POSES, max(1, N_POSES // 64))]

    # ── G2 옮기기만 한다 ────────────────────────────────────────────────────
    print("\n═══ G2 · 옮기기만 한다 (크기 불변 · û 성분 0) ═══")
    dots, dists, comps, same_size = [], [], [], True
    for div in DIVS:
        d = LAM / div
        g = grid_ref_from(probes, FC, spacing=d)
        for el in ELS:
            u = los(0.0, el)
            e1, e2 = _grid_basis(u)
            for s in (0.5, 1.0, (0.5, 0.25), (0.37, -0.19)):
                gs = grid_ref_shift(g, s, u)
                s1, s2 = (s, s) if np.isscalar(s) else s
                dc = np.asarray(gs.ctr, float) - np.asarray(g.ctr, float)
                same_size &= (gs.n == g.n and gs.Rout == g.Rout and gs.spacing == g.spacing)
                dots.append(abs(float(dc @ u)))
                dists.append(abs(float(np.linalg.norm(dc)) - np.hypot(s1, s2) * d))
                comps.append(max(abs(float(dc @ e1) - s1 * d), abs(float(dc @ e2) - s2 * d)))
    ok("격자 간격 d · 칸 수 n · 광선 수 n² · Rout 이 안 변한다", same_size)
    ok("이동은 광선 평면 안에서만 (û 성분 = 0)", max(dots) < 1e-15,
       f"최대 |Δctr·û| = {max(dots):.2e} m")
    ok("이동 거리 = √(s1²+s2²)·d", max(dists) < 1e-15, f"최대 오차 {max(dists):.2e} m")
    ok("이동량이 (e1, e2) 성분 그대로", max(comps) < 1e-15)

    # ── G3 덮개 ─────────────────────────────────────────────────────────────
    print("\n═══ G3 · 반 칸 옮기고도 표적이 격자 안에 드나 ═══")
    cover = []
    for div in DIVS:
        d = LAM / div
        g = grid_ref_from(probes, FC, spacing=d)
        for el in ELS:
            u = los(0.0, el)
            row = dict(div=div, el_deg=el, spacing_mm=round(d * 1e3, 4), n=int(g.n))
            for s, key in ((0.0, "margin0_mm"), (0.5, "margin_half_mm"), (1.0, "margin_one_mm")):
                gs = grid_ref_shift(g, s, u) if s else g
                m = min(grid_ref_margin(p, u, gs, spacing=d)["margin_min_m"] for p in probes)
                row[key] = round(m * 1e3, 3)
                row[key.replace("_mm", "_cells")] = round(m / d, 2)
            cover.append(row)
    worst = min(r["margin_half_cells"] for r in cover)
    ok("반 칸 이동판이 모든 앙각·모든 격자에서 표적을 덮는다", worst > 0,
       f"가장 빠듯한 자리도 여유 {worst:.1f} 칸")
    print(f"    (λ/12 여유 {cover[0]['margin_half_mm']:.1f} mm = "
          f"{cover[0]['margin_half_cells']:.1f} 칸 — 얼린 판이 pad 1.15+3d 로 넉넉하다)")

    # ── G4 불순물: 구면파 송신점이 같이 옮겨지는 몫 ─────────────────────────
    print("\n═══ G4 · 순수한가 — 송신점 이동이 만드는 위상차 ═══")
    k = 2 * np.pi / LAM
    V = np.vstack([np.asarray(p.v, float) for p in probes[:8]])
    imp = []
    for div in DIVS:
        d = LAM / div
        g = grid_ref_from(probes, FC, spacing=d)
        for el in ELS:
            u = los(0.0, el)
            gs = grid_ref_shift(g, 0.5, u)
            c0, c1 = np.asarray(g.ctr, float), np.asarray(gs.ctr, float)
            f0 = 2 * k * (RANGE_M - np.linalg.norm(V - (c0 + RANGE_M * u), axis=1))
            f1 = 2 * k * (RANGE_M - np.linalg.norm(V - (c1 + RANGE_M * u), axis=1))
            tx = float(np.degrees(np.ptp(f1 - f0)))
            # 표본이 반 칸 옮겨질 때 표본 하나가 겪는 위상 변화(수직입사 기준, 경사입사면
            # 1/cosθ 로 더 커진다) — 이것이 «재려는 것» 의 크기다
            smp = float(np.degrees(2 * k * np.hypot(0.5, 0.5) * d))
            imp.append(dict(div=div, el_deg=el, tx_move_phase_pp_deg=round(tx, 4),
                            sample_move_phase_deg=round(smp, 4),
                            ratio=round(smp / tx, 1)))
    worst = min(r["ratio"] for r in imp)
    ok("송신점 이동(불순물) ≪ 표본 이동(재려는 것)", worst > 5.0,
       f"가장 나쁜 자리도 {worst:.0f} 배 (불순물 최대 "
       f"{max(r['tx_move_phase_pp_deg'] for r in imp):.2f}°)")

    # ── G1 비트 동일 + 파일 이름 (가짜 커널로 run() 을 통째 돌린다) ──────────
    print("\n═══ G1 · 안 주면 비트 동일 · 이름도 그대로 ═══")
    from elevation_sweep_md import parse_grid_shift
    tags = {t: parse_grid_shift(t) for t in ("", None, "0", "0,0", "0.5", "1.0",
                                             "0.5,0.25", "0.5x0.25", "0.37,-0.19")}
    ok("빈 값·0 은 꼬리표가 없다", all(tags[t][2] == "" for t in ("", None, "0", "0,0")))
    ok("값을 주면 _shift 꼬리표", tags["0.5"] == (0.5, 0.5, "_shift0.5")
       and tags["0.5,0.25"] == (0.5, 0.25, "_shift0.5x0.25"), str(tags["0.5,0.25"]))
    try:
        parse_grid_shift("반칸")
        ok("형식이 틀리면 죽는다", False)
    except SystemExit:
        ok("형식이 틀리면 죽는다(SystemExit)", True)

    import elevation_sweep_md as ESM
    calls, tmp = [], tempfile.mkdtemp(prefix="gridshift_gate_")
    real_shd = ESM.SHD
    ESM.SHD = tmp                                   # ⛔원장 폴더는 절대 안 건드린다

    def fake_sbr_field(mv, gm, fc, u, spacing=None, grid_ref=None, **kw):
        calls.append(dict(ctr=np.asarray(grid_ref.ctr, float).copy(), n=int(grid_ref.n),
                          Rout=float(grid_ref.Rout), d=float(spacing),
                          u=np.asarray(u, float).copy()))
        return complex(float(np.asarray(mv.v).sum()), 0.0)

    fake_gpu = types.ModuleType("gpu"); fake_gpu.pick = lambda **kw: None
    fake_rcs = types.ModuleType("rcs_sbr")
    fake_rcs.grid_ref_from, fake_rcs.grid_ref_shift = grid_ref_from, grid_ref_shift
    fake_rcs.grid_ref_margin, fake_rcs.sbr_field = grid_ref_margin, fake_sbr_field
    saved = {k: sys.modules.get(k) for k in ("gpu", "rcs_sbr")}
    sys.modules["gpu"], sys.modules["rcs_sbr"] = fake_gpu, fake_rcs

    class A:                                         # argparse 기본값과 같은 자리
        engine, shard, nshards, els = "ours", 0, 16, "-15"
        physics = ptd = stock = plane_wave = overwrite = merge = False
        spp = n_poses = max_depth = div = 0
        range_m = RANGE_M
        drone = sw = only = parts = grid_shift = ""
        az_deg = float("nan")
        fc_ghz = FC / 1e9

    def run_once(shift):
        calls.clear()
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        a = A(); a.grid_shift = shift; a.n_poses = N_POSES
        ESM.run(a)
        return sorted(os.listdir(tmp)), [dict(c) for c in calls]

    try:
        f0, c0 = run_once("")
        f0b, c0b = run_once("0")
        fh, ch = run_once("0.5")
        base = f"ours_r{RANGE_M:g}_n{N_POSES}_el-15_00.npz"
        ok("인자 없음 → 이름이 옛 샤드와 글자 그대로 같다", f0 == [base], str(f0))
        ok("그 이름의 샤드가 원장에 실제로 있다",
           os.path.exists(f"{real_shd}/{base}"))
        ok("--grid-shift 0 → 이름·격자 모두 인자 없음과 동일",
           f0b == f0 and np.array_equal(c0[0]["ctr"], c0b[0]["ctr"]))
        ok("--grid-shift 0.5 → _shift0.5 꼬리표(옛 샤드와 안 섞인다)",
           fh == [base.replace("_el-15", "_shift0.5_el-15")], str(fh))
        ok("이동판이 커널에 넘긴 격자: 칸 수·Rout 동일",
           ch[0]["n"] == c0[0]["n"] and ch[0]["Rout"] == c0[0]["Rout"])
        dc = ch[0]["ctr"] - c0[0]["ctr"]
        ok("이동판이 커널에 넘긴 격자: 원점만 반 칸 대각 이동",
           abs(np.linalg.norm(dc) - np.hypot(0.5, 0.5) * c0[0]["d"]) < 1e-15
           and abs(float(dc @ c0[0]["u"])) < 1e-15,
           f"|Δctr| = {np.linalg.norm(dc) * 1e3:.3f} mm")
        ok("자세가 바뀌어도 판은 그대로다(얼림이 안 풀렸다)",
           all(np.array_equal(c["ctr"], ch[0]["ctr"]) for c in ch))
        try:
            a = A(); a.engine = "sionna"; a.grid_shift = "0.5"
            ESM.run(a)
            ok("PathSolver 팔에서는 거부한다", False)
        except SystemExit:
            ok("PathSolver 팔에서는 거부한다(격자가 없다)", True)
    finally:
        ESM.SHD = real_shd
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 이미 있는 dither 실측과의 정합 ──────────────────────────────────────
    dith = json.load(open(f"{ROOT}/outputs/report2_waveform_rcs.json"))["sbr_validation"]["dither"]
    passed = all(r["passed"] for r in RESULT)
    doc = dict(_meta=dict(
        generator="benchmark/verify_grid_shift.py",
        question_ko="--grid-shift(격자 위상 널) 배선이 «안 주면 비트동일 · 주면 옮기기만» 을 지키나",
        gpu_used=False, fc_hz=FC, range_m=RANGE_M, n_poses=N_POSES,
        drone=TJ.get("drone"), elevations_deg=list(ELS), divs=list(DIVS),
        how_to_read_ko="docs/GRID_PHASE_NULL.md",
        purity_ko=("구면파 판에서는 송신점 p_tx=ctr+R·û 도 같이 옮겨진다. 그 몫(tx_move_phase_pp_deg)이 "
                   "표본 이동이 만드는 위상(sample_move_phase_deg)보다 훨씬 작아야 «표본 자리만 "
                   "바꾼 판» 이라고 말할 수 있다 — 이 게이트가 그 비를 잰다."),
        dither_xref_ko=("outputs/report2_waveform_rcs.json 의 sbr_validation.dither 는 같은 «격자 "
                        "정렬이 값을 흔든다» 를 PEC 구에서 잰 것이다. 다만 그 판은 pad 를 흔들어 "
                        "Rout·n 이 같이 바뀐 것이고(정렬은 덤으로 바뀐다), --grid-shift 는 n 을 "
                        "고정하고 원점만 옮긴다 — 더 순수한 같은 축이다.")),
        checks=RESULT, coverage=cover, purity=imp,
        dither_reference=[dict(div=r["div"], spread_db=round(r["spread"], 3)) for r in dith],
        passed=passed)
    with open(OUT, "w", encoding="utf-8") as fh_:
        json.dump(doc, fh_, ensure_ascii=False, indent=1)
    print(f"\n→ {OUT}   전체 {'PASS' if passed else 'FAIL'} "
          f"({sum(r['passed'] for r in RESULT)}/{len(RESULT)})")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
