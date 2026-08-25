# -*- coding: utf-8 -*-
"""클러터 제거는 어느 엔진·어느 앙각에서 «성공» 하나.

사용자 질문(2026-08-25): phy off 버전에서도 클러터 제거가 실패하나?

⭐«실패» 의 정의를 분명히 한다. 필터의 임무는 «정지 동체를 걷어내 약한 날개
  신호를 드러내는 것» 이다. 그러니 성공 판정은 두 가지다:
    ① 잔차가 «프로펠러 단독» 과 닮았나  (닮으면 날개를 드러낸 것)
    ② 흔들림이 얼마나 줄었나           (안 줄면 필터가 아무것도 안 한 것)
  ⛔①이 본질이다. ②만 보면 «분모가 줄어 몫이 오른 것» 을 성공으로 오독한다.

⛔프로펠러 단독 팔은 el 0·−30·−60·−90 에만 있다 — ①은 그 네 칸에서만 낼 수 있다.
산출: outputs/clutter_removal_verdict_0825.json
"""
import sys, json
import numpy as np
sys.path.insert(0, "/workspace/sionna/benchmark"); sys.path.insert(0, "/workspace/sionna/src")
from clutter_parts_ladder_0824 import load, cs_eca, PRF, FFL

ELS = [0.0, -30.0, -60.0, -90.0]
WHOLE = [("PathSolver phy off", "sionna_p4000000000_r15_n8192_d1",
          "sionna_p4000000000_partsprop_r15_n8192_d1"),
         ("PathSolver phy on",  "sionna_p4000000000_phys_r15_n8192_d1",
          "sionna_p4000000000_phys_partsprop_r15_n8192_d1"),
         ("SBR + PO (ours)",    "ours_r15_n8192", "ours_free_r15_n8192")]
ac = lambda x: np.asarray(x) - np.asarray(x).mean()
def cor(a, b):
    a, b = ac(a), ac(b)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.abs(np.vdot(a, b)) / d) if d > 0 else float("nan")

out = {"_meta": {"작성": "2026-08-25",
                 "성공판정": "잔차가 프로펠러 단독과 닮아야 성공(|상관|). 흔들림 감소는 보조 지표",
                 "⛔한계": "프로펠러 단독 팔은 el 0·−30·−60·−90 에만 있다"}, "cells": {}}
hdr = f"{'앙각':>6} {'엔진':20}{'제거전 AC':>11}{'제거후 AC':>11}{'남은 몫':>9}{'|상관| 잔차↔프로펠러':>22}"
print(hdr); print("-" * 84)
for el in ELS:
    for nm, aw, ap in WHOLE:
        W, _ = load(aw, el); P, _ = load(ap, el)
        if W is None: continue
        R = cs_eca(W)
        b, a_ = np.abs(ac(W)).std(), np.abs(ac(R)).std()
        c = cor(R, P) if P is not None else float("nan")
        out["cells"][f"{el:+.0f}|{nm}"] = dict(
            ac_before_db=round(float(20*np.log10(b+1e-300)), 2),
            ac_after_db=round(float(20*np.log10(a_+1e-300)), 2),
            fluctuation_kept_pct=round(float(100*a_/b), 1),
            corr_residual_vs_propellers=None if np.isnan(c) else round(c, 4))
        cs = "  (프로펠러 팔 없음)" if np.isnan(c) else f"{c:22.4f}"
        print(f"{el:+6.0f} {nm:20}{20*np.log10(b+1e-300):11.2f}{20*np.log10(a_+1e-300):11.2f}"
              f"{100*a_/b:8.1f}%{cs}")
    print()
json.dump(out, open("/workspace/sionna/outputs/clutter_removal_verdict_0825.json", "w",
                    encoding="utf-8"), ensure_ascii=False, indent=2)
print("→ outputs/clutter_removal_verdict_0825.json")
print("\n⭐읽는 법: |상관| 이 1 에 가까우면 «날개를 드러냈다» = 성공,")
print("           0 에 가까우면 «걷어냈더니 날개가 아닌 것이 남았다» = 실패.")
