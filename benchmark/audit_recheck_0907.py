#!/usr/bin/env python
"""실외 되찾기 원장(outputs/outdoor_recover_0907.json)의 다투는 수를 **독립으로 다시 잰다**.

2026-09-07 감사가 그 원장에 셋을 걸었다. 여기서는 감사의 수를 믿지 않고 샤드에서 다시 센다.

  ① **자유공간 기준값이 「같은 경로가 여러 줄로 적힌」 판 위에서 재어졌나.**
     원장의 `load()` 는 `z["E"]` 를 쓴다 — 되풀이가 든 배열이다. 겹침을 걷은
     `z["E_dedup"]` 로 다시 재면 값이 얼마나 움직이나, 그래서 「무너짐」 판정이 뒤집히나.
     ⚠샤드마다 `E_dedup` 가 있는 것이 아니다(옛 세대에는 없다). 어느 칸이 그런지 적는다.

  ② **머리기사가 자유 파라미터 하나에 매달렸나.**
     원장 :146 의 `fill(O, bright=1.05)` 에서 1.05 는 원장 `_meta` 에 없다.
     문턱을 흔들어 「되찾음」 판정이 바뀌는 자리를 찾는다.
     ⭐이 저장소 규약: 자유 파라미터를 흔들어 결론이 바뀌면 그 결론은 머리기사로 안 쓴다.

  ③ **«보임» 문턱(치환 널)을 안 걸었나.**
     `comb_snr.py:204` 에 `comb_visible` 이 이미 있는데(치환 널의 최댓값보다 큰가),
     두 실외 원장은 맨 `comb_snr` 만 부른다. 널을 걸면 어느 칸이 「안 보임」이 되나.
     널 아래의 값은 **값이 아니라 하한**이라 두 값의 차(drop_db)를 그대로 못 쓴다.

⛔이 스크립트는 판정을 내리지 않는다 — 수를 나란히 놓는다. 판정은 원장을 고친 뒤에 한다.
⛔`--slow` 가 기본이다(널 60 회는 무겁다). CPU 를 아껴야 하면 --n-null 로 줄인다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 nice -n 19 \
      /workspace/.venvs/py312/bin/python benchmark/audit_recheck_0907.py
    → outputs/audit_recheck_0907.json
"""
from __future__ import annotations

import argparse, glob, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import comb_snr as CS                                                  # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "audit_recheck_0907.json")
MESH = "mfixbatteryi5_blperairframe"
ARMS = ("R0D0E0F1", "R1D0E0F1", "R0D1E1F1", "R1D1E1F1")
ELS = (0, -15, -30, -45, -60, -75)
#: ⭐원장(benchmark/outdoor_recover_0907.py:47)과 **같은 값이어야 한다** —
#  다르면 비교가 뜻이 없다. 2026-09-07 에 여기를 4000/0.30 으로 잘못 적어
#  자유공간 값이 59.62 → 4.74 로 나왔고, 하마터면 원장이 틀렸다고 적을 뻔했다.
PRF, DIP = 19700.0, 0.1
BRIGHTS = (1.02, 1.03, 1.04, 1.05, 1.06, 1.08, 1.10, 1.15)


def load(arm, el, env):
    """원장과 **같은 방식**으로 읽는다 — 그래야 비교가 뜻이 있다.

    돌려주는 것은 (E, E_dedup 또는 None). 옛 세대 샤드에는 `E_dedup` 가 없다.
    """
    tag = "envoutdoor01_" if env else ""
    fs = sorted(glob.glob(
        f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}{MESH}_d2_el{el:+g}_*.npz"))
    if not fs:
        return None, None
    E, D, I = [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
        D.append(z["E_dedup"] if "E_dedup" in z.files else None)
    o = np.argsort(np.concatenate(I))
    Ec = np.concatenate(E)[o]
    Dc = None if any(d is None for d in D) else np.concatenate(D)[o]
    return Ec, Dc


def fill(E, thr=DIP, bright=None):
    """원장 :68-81 과 같은 메움 — 옮겨 적지 않고 뜻만 같게 다시 썼다."""
    a = np.abs(E)
    med = float(np.median(a))
    bad = set(np.where(a / med < thr)[0].tolist())
    if bright is not None:
        bad |= set(np.where(a / med > bright)[0].tolist())
    bad = np.array(sorted(bad), int)
    if not bad.size:
        return E, 0
    good = np.setdiff1d(np.arange(E.size), bad)
    R = E.copy()
    R[bad] = (np.interp(bad, good, E[good].real)
              + 1j * np.interp(bad, good, E[good].imag))
    return R, int(bad.size)


def snr(E, el, nm):
    v = CS.comb_snr(np.asarray(E), PRF, el, arm=nm)
    return None if v is None else round(float(v), 2)


def null_max(E, el, nm, n_null, seed=0):
    """치환 널의 **최댓값** — `comb_snr.py:190-204` 와 같은 뜻.

    시간축을 뒤섞으면 주기성이 사라진다. 그래도 나오는 값이 잣대의 바닥이다.
    """
    rng = np.random.default_rng(seed)
    E = np.asarray(E)
    vs = []
    for _ in range(n_null):
        v = CS.comb_snr(E[rng.permutation(E.size)], PRF, el, arm=nm)
        if v is not None:
            vs.append(float(v))
    return (round(max(vs), 2), len(vs)) if vs else (None, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-null", type=int, default=CS.N_NULL,
                    help=f"치환 널 횟수 (기본 {CS.N_NULL} — 잣대 파일과 같다)")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    t0 = time.time()
    cells = {}
    for arm in ARMS:
        for el in ELS:
            nm = f"sionna_p4000000000_sw{arm}_r15_n8192_envoutdoor01_{MESH}_d2"
            F, Fd = load(arm, el, False)
            O, Od = load(arm, el, True)
            if F is None or O is None or F.size != O.size:
                continue
            c = {"arm": arm, "el_deg": el, "n_poses": int(O.size),
                 "has_dedup_free": Fd is not None, "has_dedup_out": Od is not None}

            #: ── ③ 널 ──────────────────────────────────────────────────
            c["comb_free_db"] = snr(F, el, nm)
            c["comb_out_db"] = snr(O, el, nm)
            c["null_max_free_db"], nf = null_max(F, el, nm, a.n_null, seed=1)
            c["null_max_out_db"], no = null_max(O, el, nm, a.n_null, seed=2)
            c["n_null_used"] = int(min(nf, no))
            for side in ("free", "out"):
                v, n = c[f"comb_{side}_db"], c[f"null_max_{side}_db"]
                c[f"visible_{side}"] = None if (v is None or n is None) else bool(v > n)
            if c["comb_free_db"] is not None and c["comb_out_db"] is not None:
                c["drop_db"] = round(c["comb_out_db"] - c["comb_free_db"], 2)
                c["is_broken"] = bool(c["drop_db"] <= -10.0)
            #: ⭐한쪽이라도 널 아래면 그 차는 **값이 아니라 하한**이다.
            c["drop_is_lower_bound_only"] = bool(
                c.get("visible_out") is False or c.get("visible_free") is False)

            #: ── ① 겹침을 걷으면 ──────────────────────────────────────
            if Fd is not None:
                c["comb_free_dedup_db"] = snr(Fd, el, nm)
                c["free_dedup_shift_db"] = (
                    None if (c["comb_free_db"] is None or c["comb_free_dedup_db"] is None)
                    else round(c["comb_free_dedup_db"] - c["comb_free_db"], 2))
                c["n_pose_E_ne_Ededup"] = int(np.count_nonzero(np.abs(F) != np.abs(Fd)))
                c["level_span_E_db"] = round(float(
                    20 * np.log10(np.abs(F).max() / max(np.abs(F).min(), 1e-300))), 4)
                c["level_span_Ededup_db"] = round(float(
                    20 * np.log10(np.abs(Fd).max() / max(np.abs(Fd).min(), 1e-300))), 4)
                if c["comb_free_dedup_db"] is not None and c["comb_out_db"] is not None:
                    c["drop_db_if_dedup"] = round(
                        c["comb_out_db"] - c["comb_free_dedup_db"], 2)
                    c["is_broken_if_dedup"] = bool(c["drop_db_if_dedup"] <= -10.0)
                    c["broken_flips"] = bool(
                        c.get("is_broken") != c["is_broken_if_dedup"])

            #: ── ② 밝은 자세 문턱을 흔든다 ────────────────────────────
            #  원장은 「안 돌아온 칸」에서만 이 갈래를 탄다. 여기서는 모든 칸에서 잰다 —
            #  문턱이 결과를 정하는지 보려면 판정 밖에서도 봐야 한다.
            if c.get("is_broken"):
                o_fill, n_fill = fill(O)
                c["n_dips"] = n_fill
                c["comb_fill_db"] = snr(o_fill, el, nm)
                if c["comb_fill_db"] is not None and c["comb_free_db"] is not None:
                    c["recover_gap_db"] = round(c["comb_fill_db"] - c["comb_free_db"], 2)
                    c["is_recovered"] = bool(abs(c["recover_gap_db"]) <= 3.0)
                lad = {}
                for b in BRIGHTS:
                    o2, n2 = fill(O, bright=b)
                    v = snr(o2, el, nm)
                    lad[f"{b:g}"] = {
                        "n_filled": n2, "comb_db": v,
                        "gap_db": (None if (v is None or c["comb_free_db"] is None)
                                   else round(v - c["comb_free_db"], 2)),
                    }
                c["bright_ladder"] = lad
                gaps = [x["gap_db"] for x in lad.values() if x["gap_db"] is not None]
                c["bright_recovered_at"] = [k for k, x in lad.items()
                                            if x["gap_db"] is not None
                                            and abs(x["gap_db"]) <= 3.0]
                c["bright_verdict_flips"] = bool(
                    0 < len(c["bright_recovered_at"]) < len(lad))
                c["bright_gap_span_db"] = (round(max(gaps) - min(gaps), 2)
                                           if gaps else None)
            cells[f"{arm}/el{el:+.0f}"] = c
            print(f"  {arm}/el{el:+.0f}  자유 {c['comb_free_db']} (널 "
                  f"{c['null_max_free_db']}) · 실외 {c['comb_out_db']} (널 "
                  f"{c['null_max_out_db']})", flush=True)

    n = len(cells)
    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "what_ko": "outdoor_recover_0907 원장의 다투는 수를 독립으로 다시 잰 판",
            "n_null": int(a.n_null),
            "dip_threshold": DIP,
            "bright_thresholds": list(BRIGHTS),
            "recover_gap_db_criterion": 3.0,
            "broken_drop_db_criterion": -10.0,
            "elapsed_s": round(time.time() - t0, 1),
            "limits_ko": [
                "⛔판정을 내리지 않는다 — 수를 나란히 놓을 뿐이다.",
                "⚠E_dedup 는 옛 세대 샤드에 없다. has_dedup_free/out 이 그것을 적는다.",
                "⚠자유·실외 한쪽만 겹침을 걷으면 두 판의 세대가 달라진다 — "
                "drop_db_if_dedup 은 그 한계를 안고 있는 수다.",
                "⛔이 저장소에 실기 계측 대조는 0 건이다 — 「검증됐다」로 읽지 않는다.",
            ],
        },
        "summary": {
            "n_cells": n,
            "n_broken": sum(1 for c in cells.values() if c.get("is_broken")),
            "n_free_below_null": sum(1 for c in cells.values()
                                     if c.get("visible_free") is False),
            "n_out_below_null": sum(1 for c in cells.values()
                                    if c.get("visible_out") is False),
            "n_drop_lower_bound_only": sum(1 for c in cells.values()
                                           if c.get("drop_is_lower_bound_only")),
            "n_cells_with_dedup": sum(1 for c in cells.values()
                                      if c.get("has_dedup_free")),
            "n_broken_flips_on_dedup": sum(1 for c in cells.values()
                                           if c.get("broken_flips")),
            "n_bright_verdict_flips": sum(1 for c in cells.values()
                                          if c.get("bright_verdict_flips")),
        },
        "cells": cells,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n⭐{a.out}  칸 {n} · {doc['_meta']['elapsed_s']}s")
    for k, v in doc["summary"].items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
