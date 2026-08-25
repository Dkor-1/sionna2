# -*- coding: utf-8 -*-
"""교차항 «뾰족함» 을 앙각 전체로 — 0° 만의 병인가, 전 각도에 걸친 성질인가.

사용자 관찰(2026-08-25): "30, 60 도 결과는 그래도 괜찮아 보이던데".
⇒ 눈으로 본 그 인상이 수치로도 나오는지 본다.

⛔동체 단독 팔은 el 0 에만 있다 — 분해(①+②≠③)는 0° 에서만 낼 수 있다.
  통짜 세 엔진은 7 앙각 전부 있으므로 «모양» 지표는 전 각도로 낸다.
산출: outputs/crossterm_elev_sweep_0825.json
"""
import sys, json, os
import numpy as np
sys.path.insert(0, "/workspace/sionna/benchmark"); sys.path.insert(0, "/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, cs_eca, PRF, FFL

ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]
ARMS = [("PathSolver phy off", "sionna_p4000000000_r15_n8192_d1"),
        ("PathSolver phy on",  "sionna_p4000000000_phys_r15_n8192_d1"),
        ("SBR + PO (ours)",    "ours_r15_n8192")]
POSES_PER_PASS = PRF / FFL          # 블레이드 통과 1 회당 자세 수 = 155.5

ac = lambda x: np.asarray(x) - np.asarray(x).mean()

def shape(E):
    a = np.abs(ac(E))
    if a.std() == 0: return None
    e = a ** 2; e = e / e.sum(); top = np.sort(e)[::-1]
    m = a > (a.mean() + 3 * a.std())
    runs, c = [], 0
    for v in m:
        if v: c += 1
        elif c: runs.append(c); c = 0
    if c: runs.append(c)
    # ⛔사건이 0 개일 때 [0] 으로 바꾸면 «1 개» 로 세어진다(옛 판의 버그).
    #   0 개는 0 개로 보고하고 폭·비율은 None 으로 둔다.
    runs = np.array(runs)
    if runs.size == 0:
        return dict(kurtosis=round(float((a**4).mean() / (a**2).mean()**2), 2),
                    top1pct_energy_share=round(float(100 * top[:max(1, len(top)//100)].sum()), 1),
                    n_events=0, median_event_width_poses=None, single_pose_event_pct=None,
                    ac_db=round(float(20 * np.log10(a.std() + 1e-300)), 2))
    return dict(
        kurtosis=round(float((a**4).mean() / (a**2).mean()**2), 2),
        top1pct_energy_share=round(float(100 * top[:max(1, len(top)//100)].sum()), 1),
        n_events=int(len(runs)),
        median_event_width_poses=float(np.median(runs)),
        single_pose_event_pct=round(float(100 * np.mean(runs == 1)), 1),
        ac_db=round(float(20 * np.log10(a.std() + 1e-300)), 2))

out = {"_meta": {"작성": "2026-08-25", "PRF": PRF, "f_flash": FFL,
                 "poses_per_blade_pass": round(POSES_PER_PASS, 1),
                 "물음": "교차항의 뾰족함이 0° 만의 병인가",
                 "⛔한계": "동체 단독 팔은 el 0 에만 있어 분해는 0° 에서만 가능"},
       "cells": {}}
print(f"블레이드 통과 1 회당 자세 {POSES_PER_PASS:.1f}  ← 물리적 스윕이면 섬광이 이 폭이어야 한다\n")
hdr = f"{'앙각':>6} {'엔진':20}{'첨도':>9}{'상위1%':>9}{'사건수':>8}{'섬광폭':>9}{'1자세':>10}{'AC dB':>10}"
print(hdr); print("-" * len(hdr))
for el in ELS:
    for nm, arm in ARMS:
        E, _ = load(arm, el)
        if E is None: continue
        s = shape(E)
        if s is None: continue
        out["cells"][f"{el:+.0f}|{nm}"] = s
        w = "  —" if s['median_event_width_poses'] is None else f"{s['median_event_width_poses']:.1f}"
        sp = "  —" if s['single_pose_event_pct'] is None else f"{s['single_pose_event_pct']:.0f}%"
        print(f"{el:+6.0f} {nm:20}{s['kurtosis']:9.1f}{s['top1pct_energy_share']:8.1f}%"
              f"{s['n_events']:8d}{w:>9}{sp:>10}{s['ac_db']:10.2f}")
    print()
json.dump(out, open("/workspace/sionna/outputs/crossterm_elev_sweep_0825.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=2)
print("→ outputs/crossterm_elev_sweep_0825.json")
