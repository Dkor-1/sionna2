# -*- coding: utf-8 -*-
"""
report07_sionna_range_sweep.py — ⭐Sionna PathSolver 마이크로도플러를 **거리 스윕**으로.

사용자 요청: 3 m 하나뿐이던 Sionna 맵을 **3 / 10 / 20 / 40 m** 로 점점 멀어지며 각각.

이 스윕이 답하는 것 둘
----------------------
① 거리가 멀어지면 맵이 어떻게 변하나 — 원거리장 경계(2D²/λ = 8.0 m)를 **가로지른다**.
   3 m 는 근거리장, 10/20/40 m 는 원거리장이다.
② ⭐광선 예산 — 표적이 차지하는 입체각이 (D/R)² 로 줄어 경로 발견이 성겨진다.
   광선 수를 거리²에 비례해 늘려 보상하고, 자세당 경로 수를 기록한다.
   (reports/42_md-ray-budget 이 묻는 «경로 표본화» 질문의 실측이기도 하다.)

⭐ 기하 정정(2026-08-10, 사용자 지적) — **진짜 모노스태틱**으로 바꾼다.
   지금까지 Sionna 팔은 기선 0.2 m(바이스태틱각 3.8°)의 준-모노였다. 우리 SBR/PO 팔은
   완전 모노스태틱(후방산란)이라 세 팔의 기하가 미묘하게 달랐다.
   시험 결과 TX=RX 완전 동일점이 Sionna 에서 잘 돈다(각 0.000°, 경로 정상) → 기선 0.

측정 모형(파형 아님)
--------------------
   h(t_k) = Σ_p a_p·exp(−j2πf_c·τ_p)   — 3.5 GHz **단일 톤(CW)** 채널 응답.
   5G 파형을 변조해 쏜 것이 아니다. 반송파 주파수만 n78 에서 빌렸다.
   PRF 는 «채널을 얼마나 자주 재느냐»(슬로타임 표본율)다.

    python benchmark/report07_sionna_range_sweep.py
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                   # noqa: E402
pick(verbose=True)

import numpy as np                                                     # noqa: E402
import report15_probe as RP                                            # noqa: E402
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors               # noqa: E402

FC = 3.5e9
AZ, EL = 0.0, -15.0
N_T = int(os.environ.get("SIONNA2_MD_NT", "512"))            # 표본 수(창 = N_T/PRF)
PRF_OVER_FTIP = float(os.environ.get("SIONNA2_MD_PRF_MULT", "4.0"))   # ⭐시간 분해능 레버
RANGES = [3.0, 10.0, 20.0, 40.0]
# ⭐ 광선 수를 (R/3)² 로 늘려 표적 입체각 축소를 보상한다 (상한 32M)
SPP = {3.0: 1_000_000, 10.0: 8_000_000, 20.0: 16_000_000, 40.0: 32_000_000}
STATIC_SPREAD = 0.0022                      # PX4 실측 산포
PATTERN = np.array([+1.0, -1.0, -0.55, +0.55])


def main():
    spec = DRONES["matrice4e"]
    fp = FastPoser(spec)
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    f_rev = rpm0 / 60.0
    f_flash = spec.prop_blades * f_rev
    lam = 3e8 / FC
    R_ = spec.prop_dia_mm / 1000.0 / 2.0
    f_tip = 2.0 * (2 * np.pi * f_rev * R_) / lam * np.cos(np.radians(EL))
    prf = float(np.ceil(PRF_OVER_FTIP * f_tip / 100.0) * 100.0)
    t = np.arange(N_T) / prf
    rpms = rpm0 * (1.0 + STATIC_SPREAD * np.resize(PATTERN, len(fp.dirs)))
    ph = rotor_phases(t, rpms, fp.dirs)

    print(f"\n═══ {spec.name} 호버링 · 진짜 모노스태틱(기선 0) · 거리 스윕 ═══")
    print(f"  f_flash {f_flash:.1f} Hz · f_tip {f_tip:.0f} Hz · PRF {prf:.0f} Hz · "
          f"{N_T} 표본 = {N_T/prf*1e3:.0f} ms")
    print(f"  거리 {RANGES} m · 원거리장 경계 {2*0.587**2/lam:.1f} m", flush=True)

    series, meta = {}, {}
    cols = drone_colors(spec)

    for rng in RANGES:
        spp = SPP[rng]
        E = np.zeros(N_T, complex)
        npaths = np.zeros(N_T, int)
        t0 = time.time()
        for i in range(N_T):
            mv = fp.pose(ph[i])
            m = mv.to_mesh()
            d = os.path.join(RP.SCRATCH, f"{spec.key}_RS{i % 2}")
            paths_obj = m.write_obj_per_group(d, spec.key)
            parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                     for g, p in paths_obj.items()]
            sc = RP.build_scene(parts, fc=FC)
            RP.place(sc, az=AZ, el=EL, rng=rng, baseline=0.0)      # ⭐기선 0 = 모노스태틱
            p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                                   diffuse_reflection=True, refraction=False,
                                   samples_per_src=int(spp),
                                   max_num_paths_per_src=RP.MAX_PATHS, seed=1)
            try:
                aa, tau, _, O = RP.unpack(p)
            except ValueError:            # ⚠원거리에서 경로 0개면 unpack 이 빈 배열에 죽는다
                aa = np.zeros(0)
            if aa.size:
                hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
                E[i] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
                npaths[i] = int(hit.sum())
            RP.drop_scratch(d)
            if i and i % 128 == 0:
                el = time.time() - t0
                print(f"    R={rng:4.0f} m  {i}/{N_T}  {el:.0f}s  "
                      f"ETA {(N_T-i)/i*el/60:.1f}분  경로중앙 {np.median(npaths[:i]):.0f}",
                      flush=True)
        secs = time.time() - t0
        key = f"R{rng:.0f}"
        series[f"{key}/E"] = E
        series[f"{key}/npaths"] = npaths
        db = 20 * np.log10(np.abs(E) + 1e-30)
        meta[key] = {"range_m": rng, "spp": int(spp), "seconds": round(secs, 1),
                     "paths_median": float(np.median(npaths)),
                     "paths_zero_frac": float((npaths == 0).mean()),
                     "level_db": float(db.mean()),
                     "ptp_db": float(db.max() - db.min())}
        print(f"  ✅ R={rng:4.0f} m  {secs/60:.1f}분 · 경로 중앙 {np.median(npaths):.0f} · "
              f"빈 자세 {(npaths==0).mean():.1%} · 레벨 {db.mean():.1f} dB", flush=True)
        np.savez_compressed(f"{ROOT}/outputs/report07_sionna_ranges.npz", **series)  # ⭐체크포인트

    np.savez_compressed(f"{ROOT}/outputs/report07_sionna_ranges.npz", **series)
    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "drone": "matrice4e", "name": spec.name, "fc_hz": FC,
                         "az_deg": AZ, "el_deg": EL, "n": N_T, "prf_hz": prf,
                         "f_flash_hz": f_flash, "f_tip_hz": f_tip,
                         "baseline_m": 0.0,
                         "monostatic_note_ko": "기선 0 — 진짜 모노스태틱(2026-08-10 정정). "
                                               "이전 3.8° 준-모노와 달리 SBR/PO 팔과 같은 기하다.",
                         "farfield_boundary_m": 2 * 0.587**2 / lam,
                         "rpm_spread_frac": STATIC_SPREAD,
                         "waveform_note_ko": "파형 없음 — 3.5 GHz 단일 톤 CW 채널응답. "
                                             "PRF 는 슬로타임 표본율이다.",
                         "spp_scaling_ko": "광선 수를 (R/3)² 로 늘려 표적 입체각 축소를 보상"},
               "ranges": meta},
              open(f"{ROOT}/outputs/report07_sionna_ranges.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ outputs/report07_sionna_ranges.npz / .json")


if __name__ == "__main__":
    main()
