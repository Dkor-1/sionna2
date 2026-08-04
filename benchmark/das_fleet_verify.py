# -*- coding: utf-8 -*-
"""
das_fleet_verify.py — 기하·규약 검산 4 종 → outputs/partial/das_fleet_0803/verify.json

무엇을 확인하나 (전부 "틀리면 대조 자체가 무효" 인 항목들)
  V1  θb=0 이 정말 모노스태틱인가 — rcs_sbr_multistatic(û_s=û_i) 와 rcs_sbr_batch 가 같은 수인가.
  V2  θb 가 정말 **낀각**인가 — arccos(û_i·û_s) 가 θb 와 같은가.
  V3  ⭐ **이등분선 고정 방식과 얼마나 다른가** — spec 이 금지한 그 계산을 일부러 해 보고
      우리 값과의 차이를 남긴다. "정의가 다르면 대조가 무효" 라는 경고가 실제로 몇 dB 인지.
  V4  exit_vis 가 θb=0 에서 정말 no-op 인가.

⚠ 이 스크립트는 outputs/partial/das_fleet_0803/verify.json 한 파일만 쓴다.
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                   # noqa: E402
from gpu import pick                                                 # noqa: E402

pick()

from rcs_sbr import rcs_sbr_multistatic, rcs_sbr_batch, _look        # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT              # noqa: E402

C0 = 299792458.0
THETA_B = [0, 15, 30, 45, 60, 75, 90]
GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
KEY = "mini2"
OUT = os.path.join(ROOT, "outputs", "partial", "das_fleet_0803", "verify.json")


def db(x):
    return 10.0 * np.log10(np.maximum(np.asarray(x, float), 1e-30))


def main():
    t0 = time.time()
    mesh = build_drone(DRONES[KEY])
    res = {}

    # ── V2 : θb 가 낀각인가 (기하 — 계산 없이 확인된다) ────────────────────────
    ang = []
    for phi in (0.0, 33.0, 117.0, 251.0):
        u_i = _look(phi, 0.0)
        for tb in THETA_B:
            u_s = _look(phi + tb, 0.0)
            ang.append(abs(float(np.degrees(np.arccos(np.clip(u_i @ u_s, -1, 1)))) - tb))
    res["V2_included_angle"] = dict(
        max_abs_error_deg=float(np.max(ang)),
        pass_=bool(np.max(ang) < 1e-6),
        what="arccos(û_i·û_s) 가 θb 와 같은가. Das §II-1 의 θb = TX–표적–RX 낀각 정의.")

    # ── V1 : θb=0 = 모노스태틱 ───────────────────────────────────────────────
    rows = []
    for fghz in (21.0, 24.0, 27.0):
        fc, lam = fghz * 1e9, C0 / (fghz * 1e9)
        az = np.array([0.0, 33.0, 117.0, 251.0])
        mono = np.atleast_1d(np.asarray(rcs_sbr_batch(
            mesh, GM, fc, az_deg=az, el_deg=0.0, spacing=lam / 16,
            cache_key=(KEY, round(fc / 1e6), "verify_mono"), penetrate=True, jitter=2), float))
        for j, phi in enumerate(az):
            m = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, GM, fc, _look(phi, 0.0), [_look(phi, 0.0)], spacing=lam / 16,
                cache_key=(KEY, round(fc / 1e6), "dasfleet"), penetrate=True, jitter=2,
                exit_vis=True), float))[0])
            rows.append(dict(f_ghz=fghz, az_deg=float(phi),
                             mono_batch_dbsm=float(db(mono[j])),
                             multistatic_tb0_dbsm=float(db(m)),
                             diff_db=float(db(m) - db(mono[j]))))
    d = np.array([r["diff_db"] for r in rows])
    res["V1_theta_b0_is_monostatic"] = dict(
        rows=rows, absmax_db=float(np.abs(d).max()), rms_db=float(np.sqrt((d ** 2).mean())),
        pass_=bool(np.abs(d).max() < 0.05),
        what=("θb=0 열은 rcs_sbr_batch(모노 전용 경로)와 같은 수여야 한다 — 다르면 함대 모노 "
              "대조가 기존 앵커(p3_ours)와 다른 커널을 쓴 것이 된다."))

    # ── V3 : 이등분선 고정 방식과의 차 (spec 이 금지한 계산 — 일부러 재 본다) ──
    #   금지된 방식: 이등분선을 φ 에 고정하고 TX·RX 를 ±θb/2 로 대칭으로 벌린다.
    #   spec 의 방식: 입사 az=φ, 산란 az=φ+θb (표적이 도는 것이고 TX 는 고정이므로).
    fghz = 24.0
    fc, lam = fghz * 1e9, C0 / (fghz * 1e9)
    AZ = np.linspace(0.0, 360.0, 72, endpoint=False)
    ours = np.empty((AZ.size, len(THETA_B)))
    bis = np.empty((AZ.size, len(THETA_B)))
    for j, phi in enumerate(AZ):
        ours[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            mesh, GM, fc, _look(phi, 0.0), [_look(phi + t, 0.0) for t in THETA_B],
            spacing=lam / 16, cache_key=(KEY, round(fc / 1e6), "dasfleet"),
            penetrate=True, jitter=2, exit_vis=True), float))
        for i, t in enumerate(THETA_B):
            bis[j, i] = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, GM, fc, _look(phi - t / 2.0, 0.0), [_look(phi + t / 2.0, 0.0)],
                spacing=lam / 16, cache_key=(KEY, round(fc / 1e6), "dasfleet"),
                penetrate=True, jitter=2, exit_vis=True), float))[0])
    res["V3_bisector_fixed_is_a_different_experiment"] = dict(
        f_ghz=fghz, n_az=int(AZ.size), theta_b=THETA_B,
        mu_lin_ours_dbsm=[float(db(ours[:, i].mean())) for i in range(len(THETA_B))],
        mu_lin_bisector_dbsm=[float(db(bis[:, i].mean())) for i in range(len(THETA_B))],
        delta_mu_db=[float(db(ours[:, i].mean()) - db(bis[:, i].mean()))
                     for i in range(len(THETA_B))],
        per_aspect_rms_db=[float(np.sqrt(((db(ours[:, i]) - db(bis[:, i])) ** 2).mean()))
                           for i in range(len(THETA_B))],
        what=("spec 의 do_not 목록이 금지한 '이등분선 고정' 계산을 일부러 같이 돌려 차이를 잰다. "
              "**방위 전주기 평균에서는** 두 방식이 같은 (û_i,û_s) 쌍 모음을 φ 만 다르게 훑으므로 "
              "μ 는 거의 같아야 한다(회전 대칭). 그러나 자세별(per-aspect) σ 는 완전히 다른 물건이다 "
              "— per_aspect_rms_db 가 그 크기다. 방위창이 반주기뿐인 기체(phantom3 −90:2:90)나 "
              "자세별 대조에서는 두 방식이 갈린다."))

    # ── V4 : exit_vis 가 θb=0 에서 no-op 인가 ────────────────────────────────
    rows = []
    for phi in (0.0, 33.0, 117.0, 251.0):
        kw = dict(spacing=lam / 16, cache_key=(KEY, round(fc / 1e6), "dasfleet"),
                  penetrate=True, jitter=2)
        on = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            mesh, GM, fc, _look(phi, 0.0), [_look(phi + t, 0.0) for t in THETA_B],
            exit_vis=True, **kw), float))
        off = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            mesh, GM, fc, _look(phi, 0.0), [_look(phi + t, 0.0) for t in THETA_B],
            exit_vis=False, **kw), float))
        rows.append(dict(az_deg=float(phi),
                         delta_db={str(t): float(db(on[i]) - db(off[i]))
                                   for i, t in enumerate(THETA_B)}))
    res["V4_exit_vis_is_noop_at_theta_b0"] = dict(
        f_ghz=fghz, rows=rows,
        absmax_at_tb0_db=float(max(abs(r["delta_db"]["0"]) for r in rows)),
        pass_=bool(max(abs(r["delta_db"]["0"]) for r in rows) < 1e-9),
        what=("모노에서는 first-hit 이 이미 그 가림을 뺐으므로 출사 가시성 검사는 아무 면도 "
              "깎으면 안 된다. θb>0 열의 값이 exit_vis 가 실제로 하는 일의 크기다."))

    res["_meta"] = dict(generated=time.strftime("%Y-%m-%d %H:%M:%S"), airframe=KEY,
                        runtime_s=round(time.time() - t0, 1),
                        kernel=dict(div=16, jitter=2, penetrate=True, max_bounce=1, ptd=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: (v.get("pass_", "—"), v.get("absmax_db", v.get("absmax_at_tb0_db", "")))
                      for k, v in res.items() if k != "_meta"}, ensure_ascii=False))
    print(f"wrote {OUT}  {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
