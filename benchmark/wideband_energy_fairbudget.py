# -*- coding: utf-8 -*-
"""wideband_energy_fairbudget.py — ⭐**공정 예산** 물리 팔의 «상한 위 누설» 을 낸다.

■ 무엇을 푸는가
    `outputs/wideband_energy.json` 은 물리 팔(`sionna_phys`)을 **기본 광선 예산 11.1M** 에서만
    담고 있다. 그 팔은 같은 광선을 더 많은 상호작용(굴절·회절·모서리회절·depth 3)에 나눠 쓰므로
    자세당 경로 수가 9 → 5 로 굶는다. 그래서 «물리를 켰더니 달라졌다» 가 **스위치 때문인지
    표본이 얇아졌기 때문인지** 갈리지 않는다.
    그 축을 가르는 팔(`sionna_p250000000_phys`, 광선 250M + 물리 전부)은 샤드로 이미
    디스크에 있고 병합판 원장에는 아직 없다.

■ 이 스크립트가 하는 일 (⛔GPU 를 쓰지 않는다 · ⛔기존 원장을 덮어쓰지 않는다)
    ① `outputs/elev_sweep_shards/` 의 샤드를 `idx` 로 제자리에 꽂아 시계열을 복원한다
       — `benchmark/elevation_sweep_md.py:analyse()` 와 **같은 조립 규칙**이다.
    ② `benchmark/build_wideband_energy_fig.py` 와 **같은 규약**으로 대역 몫을 낸다
       (한나 창 · 평균 제거 · 양쪽 FFT · |f| ≥ f_tip 을 상한 위로 셈).
    ③ ⭐**자기시험** — 이미 병합된 팔(ours · sionna · sionna_p250000000 · sionna_phys)을
       같은 코드로 다시 내고 `outputs/wideband_energy.json` 값과 대조한다. 그 최대 차이가
       게이트다. 게이트를 통과해야 새 팔의 값이 같은 자격을 얻는다.
    ④ 결과를 **새 파일** `outputs/wideband_energy_fairbudget.json` 에 쓴다.

■ 완결성 규칙 — 병합판과 같다
    복원한 시계열에 0 이 남으면(`n_missing > 0`) **그 행은 값을 내지 않는다.**

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/wideband_energy_fairbudget.py
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHD = f"{ROOT}/outputs/elev_sweep_shards"
REF = f"{ROOT}/outputs/wideband_energy.json"          # 읽기 전용 대조본
OUTJ = f"{ROOT}/outputs/wideband_energy_fairbudget.json"

ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
#: 병합판과 같은 팔 이름. 새 팔은 마지막 하나다.
ARMS = ("ours", "sionna", "sionna_p250000000", "sionna_phys",
        "sionna_p250000000_phys")
NEW_ARM = "sionna_p250000000_phys"


def spectrum(E: np.ndarray, prf: float):
    """0 Hz(정지 동체)를 뺀 양쪽 스펙트럼 — build_wideband_energy_fig.py 와 같은 코드."""
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    S = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1 / prf)
    o = np.argsort(fr)
    return fr[o], S[o], float(S.sum())


def assemble(arm: str, el: float):
    """샤드를 `idx` 로 제자리에 꽂는다 — analyse() 와 같은 조립 규칙."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None
    E = None
    secs = 0.0
    npa = []
    for f in fs:
        z = np.load(f)
        ii = z["idx"].astype(int)
        if E is None:
            E = np.zeros(int(np.asarray(z["meta"], float)[3]), complex)
        E[ii] = z["E"]
        secs += float(np.asarray(z["meta"], float)[5])
        if "npaths" in z:
            npa.append(z["npaths"])
    return dict(E=E, n_shards=len(fs), seconds=round(secs, 1),
                n_poses=int(E.size), n_missing=int((E == 0).sum()),
                npaths_median=(int(np.median(np.concatenate(npa))) if npa else None),
                level_db=round(float(20 * np.log10(np.mean(np.abs(E)) + 1e-300)), 2))


def bands(E: np.ndarray, prf: float, nyq: float, ft: float) -> dict:
    fr, S, tot = spectrum(E, prf)
    edges = [(0, 500, "0-500 Hz"), (500, ft, "500-f_tip"),
             (ft, 2 * ft, "f_tip-2f_tip"), (2 * ft, 4 * ft, "2-4 f_tip"),
             (4 * ft, nyq, "4f_tip-Nyquist")]
    cell = {}
    for lo, hi, nm in edges:
        if hi <= lo:
            cell[nm] = None
            continue
        w = (np.abs(fr) >= lo) & (np.abs(fr) < hi)
        cell[nm] = round(float(10 * np.log10(S[w].sum() / tot + 1e-300)), 2)
    if ft > 1:
        above = float(S[np.abs(fr) >= ft].sum() / tot)
        cell["above_f_tip_frac"] = round(above, 5)
        cell["above_f_tip_db"] = round(float(10 * np.log10(above + 1e-300)), 2)
    cell["f_tip_hz"] = round(ft, 1)
    return cell


def main() -> None:
    ref = json.load(open(REF, encoding="utf-8"))
    prf = float(ref["_meta"]["prf_hz"])
    nyq = float(ref["_meta"]["nyquist_hz"])
    ftip0 = float(ref["_meta"]["f_tip_el0_hz"])

    cells, meta_rows, skipped = {}, {}, []
    for arm in ARMS:
        for el in ELS:
            a = assemble(arm, el)
            if a is None:
                continue
            key = f"{arm}/el{el:+.0f}"
            meta_rows[key] = {k: v for k, v in a.items() if k != "E"}
            if a["n_missing"]:
                skipped.append(key)
                continue
            cells[key] = bands(a["E"], prf, nyq,
                               ftip0 * float(np.cos(np.radians(el))))

    # ── ③ 자기시험 — 이미 병합된 칸을 같은 코드로 다시 내고 대조한다 ──────────
    diffs, pairs = [], []
    for key, cell in cells.items():
        r = ref["cells"].get(key)
        if not r or "above_f_tip_frac" not in cell or "above_f_tip_frac" not in r:
            continue
        d = abs(float(cell["above_f_tip_frac"]) - float(r["above_f_tip_frac"]))
        diffs.append(d)
        pairs.append(dict(cell=key, mine=cell["above_f_tip_frac"],
                          ledger=r["above_f_tip_frac"], abs_diff=round(d, 8)))

    # 조립 자체도 대조한다 — 초·경로중앙값·레벨·미완결 수가 병합판 행과 같아야 한다.
    swp = json.load(open(f"{ROOT}/outputs/elevation_sweep_md.json", encoding="utf-8"))
    rdiff, stale, n_rows_cmp = [], [], 0
    for r in swp["rows"]:
        key = f"{r['engine']}/el{r['el_deg']:+.0f}"
        m = meta_rows.get(key)
        if not m:
            continue
        if m["n_missing"] != r["n_missing"]:
            # 병합 뒤에 샤드가 더 내려앉은 행 — 대조 대상이 아니라 **병합판의 나이**다.
            stale.append(dict(cell=key, n_missing_now=m["n_missing"],
                              n_missing_in_merge=r["n_missing"]))
            continue
        n_rows_cmp += 1
        for fld in ("seconds", "n_poses", "n_missing", "npaths_median", "level_db"):
            a, b = m.get(fld), r.get(fld)
            if a is None and b is None:
                continue
            if a != b:
                rdiff.append(dict(cell=key, field=fld, mine=a, ledger=b))

    gate = dict(
        n_cells_compared=len(diffs),
        max_abs_diff_frac=round(max(diffs), 8) if diffs else None,
        tol=1e-05,
        n_rows_compared=n_rows_cmp,
        row_mismatches=rdiff,
        n_row_mismatches=len(rdiff),
        stale_merge_rows=stale,
        verdict=("PASS" if diffs and max(diffs) <= 1e-05 and not rdiff else "FAIL"),
        what_ko=("이미 병합된 칸을 이 스크립트로 다시 내고 outputs/wideband_energy.json · "
                 "outputs/elevation_sweep_md.json 과 대조한다. 통과해야 새 팔의 값이 "
                 "같은 자격을 얻는다."),
        pairs=pairs)

    out = {"_meta": {
        "generator": "benchmark/wideband_energy_fairbudget.py",
        "question_ko": "광선 예산을 맞춘 뒤에도 물리 스위치가 상한 위 누설을 만드나",
        "snapshot_local": time.strftime("%Y-%m-%dT%H:%M"),
        "snapshot_ko": ("샤드 폴더는 계산이 도는 동안 계속 자란다 — 이 파일은 그 시각의 "
                        "사진이다. 다시 돌리면 늦게 내려앉은 샤드가 더 들어온다."),
        "n_shard_files": len(glob.glob(f"{SHD}/*_el*.npz")),
        "reads_ko": "outputs/elev_sweep_shards/*.npz (읽기 전용) + outputs/wideband_energy.json",
        "writes_ko": "이 파일 하나. 기존 원장과 그림은 손대지 않는다.",
        "gpu_ko": "GPU 를 쓰지 않는다 — 샤드를 읽어 CPU 로 FFT 만 한다.",
        "prf_hz": prf, "nyquist_hz": nyq, "f_tip_el0_hz": ftip0,
        "assembly_ko": ("샤드의 idx 로 제자리에 꽂는다 — elevation_sweep_md.py:analyse() 와 "
                        "같은 조립 규칙이라 자세 순서가 결정된다."),
        "band_rule_ko": ("build_wideband_energy_fig.py 와 같은 규약 — 한나 창 · 평균 제거 · "
                         "양쪽 FFT · |f| ≥ f_tip 을 상한 위로 센다."),
        "incomplete_excluded_ko": "n_missing > 0 인 칸은 값을 내지 않는다.",
        "new_arm_ko": ("sionna_p250000000_phys = 광선 250M + 물리 전부(굴절·회절·모서리회절·"
                       "depth 3). 병합판 원장에는 아직 행이 없는 팔이다."),
        "skipped_incomplete": skipped,
    }, "selftest": gate, "rows": meta_rows, "cells": cells}

    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"  자기시험 {gate['verdict']} — 칸 {gate['n_cells_compared']} 개, "
          f"최대 차이 {gate['max_abs_diff_frac']}")
    print(f"\n  {'팔/앙각':<32}{'경로중앙':>9}{'초':>10}{'상한위[%]':>11}{'미완결':>7}")
    for key, m in meta_rows.items():
        c = cells.get(key, {})
        av = c.get("above_f_tip_frac")
        print(f"  {key:<32}{str(m['npaths_median']):>9}{m['seconds']:>10.1f}"
              f"{(100*av if av is not None else float('nan')):>11.2f}"
              f"{m['n_missing']:>7}")
    print(f"\n  → {OUTJ}")


if __name__ == "__main__":
    main()
