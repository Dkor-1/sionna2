# -*- coding: utf-8 -*-
"""
report15_po_control_merge_audit.py — 감사 결과를 대조군 A 산출물에 **덧붙인다**.

`outputs/report15_po_control_audit.json` 의 요약을 `outputs/report15_po_control.json` 의
새 최상위 키 `audit_recheck` 로 넣는다. **기존 키는 하나도 건드리지 않는다**(덮어쓰기 아님).
원자적 교체(tmp → os.replace)라 읽는 쪽이 반쪽 파일을 보지 않는다.
"""
from __future__ import annotations

import json
import os
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PC = os.path.join(ROOT, "outputs", "report15_po_control.json")
AU = os.path.join(ROOT, "outputs", "report15_po_control_audit.json")

J = json.load(open(PC, encoding="utf-8"))
A = json.load(open(AU, encoding="utf-8"))

before = set(J.keys())
per = {}
for key, R in A["airframes"].items():
    per[key] = dict(
        rerun_max_rel_diff=max(v["max_rel_diff"] for v in R["rerun"].values()),
        rerun_arms={k: v["verdict"] for k, v in R["rerun"].items()},
        by_aspect={lab: dict(
            observed_ac_corr=t["observed_ac_corr"],
            null_mean=t["null_mean"], null_p95=t["null_p95"], p_value=t["p_value"],
            ceiling_phase_aligned=t["ceiling_phase_aligned"],
            dominant_harmonic_ours=t["dominant_harmonic_ours"],
            dominant_power_frac_ours=t["dominant_power_frac_ours"],
            residual_ac_corr=t["residual_ac_corr"],
            residual_null_mean=t["residual_null_mean"],
            residual_p_value=t["residual_p_value"],
            phi_shift_deg=(t["harmonic_phase_fit"] or {}).get("phi_shift_deg"),
            phase_fit_rms_resid_deg=(t["harmonic_phase_fit"] or {}).get("weighted_rms_resid_deg"),
            phase_fit_n_harmonics=(t["harmonic_phase_fit"] or {}).get("n_harmonics_used"),
            corr_per_seed_mean=R["per_seed"][lab]["mean"],
            corr_per_seed_min=R["per_seed"][lab]["min"],
        ) for lab, t in R["triviality"].items()})

J["audit_recheck"] = dict(
    source=os.path.relpath(AU, ROOT),
    script="benchmark/report15_po_control_audit.py",
    audited_stamp=A["meta"].get("audited_stamp"),
    stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
    what_ko=("① 저장된 PO 파형을 같은 인자로 재실행해 대조(결정론적이라 Δ=0 이어야 한다). "
             "② 헤드라인 AC 상관이 '같은 하모닉에 전력이 몰려 있어서 자동으로 높은 값' 인지 "
             "위상무작위 귀무검정으로 판정. ③ 기체·자세를 어긋나게 짝지은 특이성 대조."),
    per_airframe=per,
    cross_control={k: v for k, v in A["cross_control"].items() if k != "pairs"},
    verdict=A["verdict"])

tmp = PC + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(J, f, ensure_ascii=False, indent=1)
os.replace(tmp, PC)
print("추가된 최상위 키:", sorted(set(J.keys()) - before))
print("기존 키 보존:", sorted(before) == sorted(set(J.keys()) - {"audit_recheck"}))
print("저장:", PC, os.path.getsize(PC), "bytes")
