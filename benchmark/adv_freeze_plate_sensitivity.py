# -*- coding: utf-8 -*-
"""
adv_freeze_plate_sensitivity.py — ⭐**얼린 판 «한 장» 에 절대 레벨이 걸리는 값을 잰다**
=========================================================================================

적대적 감사(렌즈 B) 의 질문
---------------------------
격자를 얼리면 자세마다 새로 뽑히던 서브셀 오프셋이 사라진다. 생산 팔에서 그 무작위 오프셋은
사실상 **몬테카를로 디더 평균**이었고, 얼리면 레벨이 «오프셋 한 판» 에 걸린다.
`outputs/verify_frozen_grid.json::field_level.froz_vs_prod_level_db_ptp` 이 그 크기를
**3.35 dB p-p**(8 자세)로 이미 적어 두었다. 남은 질문은 하나다:

    ⭐ 그 편향이 **리포트가 인용하는 수치** 중 무엇을 삼키나?

리포트 7 계열이 얼린 복소장에서 읽는 절대 dB 는 셋이다.
    ① `arms.*.level_db`              — 팔의 절대 레벨
    ② `findings.occlusion_level_db`  = F_blade_occ.level_db − G_blade_free.level_db
    ③ `findings.occlusion_ptp_db`    = 두 팔의 변조 깊이 차
②③ 은 **같은 판 위의 두 팔의 차**라 판 편향이 공통모드로 빠질 «수도» 있다 — 그러나 두 팔은
기하가 다르므로(F 는 동체가 막고 G 는 동체 면이 없다) 공통모드라는 보장이 없다. 그것이
가정인지 사실인지는 재 봐야 안다. 이 파일이 잰다.

방법 — 같은 자세열을 판만 바꿔 다시 태운다
-------------------------------------------
    P0        생산이 쓰는 판                     (`grid_ref_for_slowtime`)
    P_e1      P0 의 중심을 격자 **반 칸** e1 이동
    P_e1e2    P0 의 중심을 반 칸씩 e1·e2 동시 이동
(e1, e2) 는 커널이 û 하나로 정하는 격자 가로축 규약이다(`rcs_sbr._grid_basis`).
셋 다 같은 `spacing`·같은 `n` 이라 **광선 수가 같고**, 바뀌는 것은 격자가 표적을 어디서
찍느냐(=서브셀 오프셋) 하나뿐이다. 판 사이의 흩어짐이 곧 «판 한 장에 걸린 값» 이다.

자세는 생산 열을 **일정 간격으로 솎아** 쓴다(`--stride`). 판끼리 같은 자세 집합을 쓰므로
비교는 성립하고, 절대 ptp 는 생산 원장(6000 자세)보다 작게 나온다 — 이 파일의 숫자는
**판 사이 흩어짐**을 읽는 것이지 생산 원장의 ptp 를 대체하지 않는다.

⛔ 원장을 하나도 안 덮어쓴다. 산출은 `outputs/freeze_plate_sensitivity.json` 하나다.

    PYTHONPATH=src SIONNA2_GPU=1 python benchmark/adv_freeze_plate_sensitivity.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ.setdefault("SIONNA2_GPU", "1")

from gpu import pick                                                   # noqa: E402
pick(verbose=True)                                                     # ⚠ mitsuba import 전에

import numpy as np                                                     # noqa: E402
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                             # noqa: E402
from rcs_sbr import (GridRef, _grid_basis, grid_ref_for_slowtime,      # noqa: E402
                     sbr_field)

OUTJ = os.path.join(ROOT, "outputs", "freeze_plate_sensitivity.json")
MDB = os.path.join(ROOT, "outputs", "report15b_microdoppler.json")
VFG = os.path.join(ROOT, "outputs", "verify_frozen_grid.json")

FC = 3.5e9
#  ⭐ 재질 표는 report15b 와 **한 글자도 다르지 않게** 만든다(같은 물리를 재는 것이 요건이다).
_GMAT_FULL = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
_GMAT_BODY_BLACK = {g: (m if g == "prop" else 0.0)
                    for g, (m, _) in DRONE_GROUP_MAT.items()}


def _u(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def shifted(ref: GridRef, u, frac_e1=0.0, frac_e2=0.0) -> GridRef:
    """판의 중심만 격자 가로축으로 `frac`×칸 옮긴 **같은 크기** 판."""
    e1, e2 = _grid_basis(np.asarray(u, float) / np.linalg.norm(u))
    ctr = np.asarray(ref.ctr, float) + ref.spacing * (frac_e1 * e1 + frac_e2 * e2)
    return GridRef(ctr=ctr, Rout=ref.Rout, n=ref.n, spacing=ref.spacing,
                   fc=ref.fc, pad=ref.pad, n_mesh=ref.n_mesh)


def series(spec, u, rpms, prf, idx, mode, gref):
    """생산과 **같은 식**의 슬로타임 열 — 자세만 idx 로 솎는다."""
    fp = FastPoser(spec)
    t = np.asarray(idx, float) / prf
    ph = rotor_phases(t, rpms, fp.dirs)
    gmat = _GMAT_BODY_BLACK if mode == "blade_occ" else _GMAT_FULL
    penetrate = (mode == "full")
    prop_only = (mode == "blade_free")
    if prop_only:
        keep = np.asarray(fp.g) == "prop"
        f_keep, g_keep = fp.f[keep], fp.g[keep]
    E = np.zeros(len(idx), complex)
    for i in range(len(idx)):
        mv = fp.pose(ph[i])
        if prop_only:
            mv.f, mv.g = f_keep, g_keep
        E[i] = sbr_field(mv, gmat, FC, u, penetrate=penetrate, grid_ref=gref)
    return E


def metrics(E):
    a = np.abs(E)
    db = 20 * np.log10(np.maximum(a, 1e-30))
    return dict(level_db=float(db.mean()), ptp_db=float(db.max() - db.min()),
                dc_over_ac=float(np.abs(E.mean()) / (np.std(E - E.mean()) + 1e-30)))


def spread(vals):
    v = np.asarray(vals, float)
    return dict(values=[float(x) for x in v], ptp=float(v.max() - v.min()),
                std=float(v.std(ddof=0)), mean=float(v.mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", default="matrice4e/belly,matrice4e/nose")
    ap.add_argument("--stride", type=int, default=24,
                    help="생산 자세열을 몇 칸마다 뽑을지 (6000/24 = 250 자세)")
    args = ap.parse_args()

    mdb = json.load(open(MDB, encoding="utf-8"))
    plates = [("P0", 0.0, 0.0), ("P_e1_half", 0.5, 0.0), ("P_e1e2_half", 0.5, 0.5)]

    res = {"_meta": {
        "script": "benchmark/adv_freeze_plate_sensitivity.py",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gpu": os.environ.get("SIONNA2_GPU"),
        "fc_hz": FC, "stride": args.stride,
        "role_ko": "적대적 감사 — 얼린 판 «한 장» 에 절대 레벨이 얼마나 걸리나",
        "plates_ko": "P0 = 생산 판 · 나머지는 중심을 격자 반 칸씩 옮긴 같은 크기 판. "
                     "광선 수·간격이 같고 서브셀 오프셋만 다르다.",
        "reads": ["outputs/report15b_microdoppler.json (자세·rpm·PRF 규약)"],
        "writes": ["outputs/freeze_plate_sensitivity.json"],
        "does_not_touch_ko": "원장 재계산 0 건. 이 파일은 자기 산출물만 쓴다.",
        "known_anchor": {
            "froz_vs_prod_level_db_ptp": float(json.load(open(VFG, encoding="utf-8"))
                                               ["field_level"]["froz_vs_prod_level_db_ptp"]),
            "what_ko": "이미 원장에 있던 값 — 얼린 장과 생산 장의 자세별 레벨 차 p-p",
        },
    }, "cells": {}}

    for cellkey in [c for c in args.cells.split(",") if c in mdb["cells"]]:
        cd = mdb["cells"][cellkey]
        spec = DRONES[cd["drone"]]
        ph = cd["physics"]
        u = _u(cd["az_deg"], cd["el_deg"])
        rpms = np.asarray(cd["rpm_locked"], float)      # A·F·G 는 전부 잠근 rpm 규약
        idx = np.arange(0, int(ph["n_t"]), args.stride)
        fp = FastPoser(spec)
        ref0 = grid_ref_for_slowtime(fp.pose, fp.dirs, FC)
        if ref0 is None:
            raise SystemExit("❌ SIONNA2_FREEZE_GRID 가 꺼져 있다 — 판 비교를 할 수 없다.")

        print(f"\n═══ {cellkey} · 자세 {len(idx)} · 판 {len(plates)} ═══", flush=True)
        cell = {"drone": cd["drone"], "az_deg": cd["az_deg"], "el_deg": cd["el_deg"],
                "n_pose": int(len(idx)), "n_grid": int(ref0.n),
                "spacing_m": float(ref0.spacing), "arms": {}, "plates": {}}

        per_plate = {}
        for pname, f1, f2 in plates:
            gref = shifted(ref0, u, f1, f2)
            t0 = time.time()
            m = {}
            for arm, mode in (("A_sbr_locked", "full"), ("F_blade_occ", "blade_occ"),
                              ("G_blade_free", "blade_free")):
                E = series(spec, u, rpms, ph["prf"], idx, mode, gref)
                m[arm] = metrics(E)
            m["occlusion_level_db"] = round(m["F_blade_occ"]["level_db"]
                                            - m["G_blade_free"]["level_db"], 3)
            m["occlusion_ptp_db"] = round(m["F_blade_occ"]["ptp_db"]
                                          - m["G_blade_free"]["ptp_db"], 3)
            m["seconds"] = round(time.time() - t0, 1)
            m["ctr"] = [float(x) for x in shifted(ref0, u, f1, f2).ctr]
            per_plate[pname] = m
            print(f"   {pname:12s} A {m['A_sbr_locked']['level_db']:8.2f} dB · "
                  f"F−G lvl {m['occlusion_level_db']:+7.3f} dB · "
                  f"F−G ptp {m['occlusion_ptp_db']:+8.3f} dB   ({m['seconds']:.0f}s)",
                  flush=True)

        cell["plates"] = per_plate
        #  ⭐타당성 게이트 — P0 는 생산이 쓰는 바로 그 판이다. 자세를 솎았으니 값이 딱 같을
        #  이유는 없지만, 여기서 크게 벌어지면 이 실험이 **다른 물리**를 잰 것이다.
        cell["p0_vs_production"] = {
            arm: {"here_db": round(per_plate["P0"][arm]["level_db"], 3),
                  "ledger_db": round(float(cd["arms"][arm]["level_db"]), 3),
                  "diff_db": round(per_plate["P0"][arm]["level_db"]
                                   - float(cd["arms"][arm]["level_db"]), 3)}
            for arm in ("A_sbr_locked", "F_blade_occ", "G_blade_free")}
        cell["p0_vs_production"]["note_ko"] = (
            "P0 는 생산 판과 같은 판이고 자세만 솎았다 — 레벨이 붙어야 이 실험이 같은 물리를 "
            "잰 것이다. 벌어지면 판 비교 이전에 배선을 의심하라.")
        for arm in ("A_sbr_locked", "F_blade_occ", "G_blade_free"):
            cell["arms"][arm] = dict(
                level_db=spread([per_plate[p][arm]["level_db"] for p, _, _ in plates]),
                ptp_db=spread([per_plate[p][arm]["ptp_db"] for p, _, _ in plates]))
        cell["findings"] = {
            "occlusion_level_db": spread([per_plate[p]["occlusion_level_db"]
                                          for p, _, _ in plates]),
            "occlusion_ptp_db": spread([per_plate[p]["occlusion_ptp_db"]
                                        for p, _, _ in plates]),
            "ledger_occlusion_level_db": float(cd["findings"]["occlusion_level_db"]),
            "ledger_occlusion_ptp_db": float(cd["findings"]["occlusion_ptp_db"]),
        }
        res["cells"][cellkey] = cell

    # ── 판정 ────────────────────────────────────────────────────────────────
    lvl = [c["arms"]["A_sbr_locked"]["level_db"]["ptp"] for c in res["cells"].values()]
    occl = [c["findings"]["occlusion_level_db"]["ptp"] for c in res["cells"].values()]
    occp = [c["findings"]["occlusion_ptp_db"]["ptp"] for c in res["cells"].values()]
    eff = [abs(c["findings"]["ledger_occlusion_level_db"]) for c in res["cells"].values()]
    res["verdict"] = {
        "abs_level_plate_ptp_db": round(float(max(lvl)), 3),
        "occlusion_level_plate_ptp_db": round(float(max(occl)), 3),
        "occlusion_ptp_plate_ptp_db": round(float(max(occp)), 3),
        "ledger_occlusion_level_abs_db": round(float(max(eff)), 3),
        "occlusion_level_survives_plate_choice": bool(max(eff) > max(occl)),
        "common_mode_ko": (
            "F−G 가 판 편향을 공통모드로 뺀다면 `occlusion_level_plate_ptp_db` 가 "
            "`abs_level_plate_ptp_db` 보다 작아야 한다. 두 팔의 기하가 다르므로 그것은 "
            "가정이지 정리가 아니다 — 이 표가 그 가정을 검사한다."),
        "how_to_read_ko": (
            "판 셋의 흩어짐(p-p)이 곧 «판 한 장을 골랐을 때 절대 dB 에 붙는 값» 이다. "
            "리포트가 인용하는 dB 가 이 흩어짐보다 작으면 그 dB 는 물리가 아니라 판 선택을 "
            "읽은 것이다."),
    }

    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUTJ, ROOT)}")
    print(json.dumps(res["verdict"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
