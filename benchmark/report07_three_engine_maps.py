# -*- coding: utf-8 -*-
"""
report07_three_engine_maps.py — ⭐**세 엔진의 마이크로도플러 맵을 같은 격자에서** 만든다.

왜
--
사용자 지적(2026-08-07): *"레포트7에서 그린 마이크로 도플러맵은 뭔가 근본적으로 잘못된거같고,
PO랑 시오나 자체(wifi-jepa 에서 쓴 방식)의 비교도 전혀 안 이뤄지고 있는데?"*

맞는 지적이다. 지금까지의 맵은 **양쪽 다 우리 SBR** 이었고, Sionna 와의 비교는 1차원 빗살뿐이었다.
⭐ **대조군이 없으면 우리 맵이 틀렸는지 알 방법이 없다.** 이 스크립트가 그 대조군을 만든다.

세 팔 — 같은 기체·자세·주파수·슬로타임 격자·로터 회전수
  ① sionna   Sionna PathSolver 로 경로를 풀고 h = Σ a_p·exp(−j2πf_c·τ_p)
             ⚠ `Paths.a` 는 패스밴드라 위상이 없다. 반드시 τ 로 위상을 얹어야 한다.
             (WiFi-JEPA 류가 Sionna 로 채널을 뽑는 방식과 같은 자리다.)
  ② sbr      우리 SBR 커널 — 광선 격자 + 가림 + 각도의존 Γ
  ③ po       우리 순수 PO — 가림 없음, 점구름 면적분

⚠ 비용 실측(matrice4e, GPU2)
    Sionna  자세당 **1.75 s** — 그 중 씬 빌드가 1.70 s (경로해는 0.05 s)
            ⭐ 우리 `pose_articulated` 가 그랬듯 병목이 기하 재생성이다.
    SBR     자세당 0.073 s
    PO      자세당 ~0.01 s
  → Sionna 가 표본 수를 정한다. 1024 표본 ≈ 30 분.

격자 설계
  PRF 를 2·f_tip 위로 잡되 낮게 둔다 — Sionna 가 비싸므로 같은 표본 수로 **더 긴 창**을 산다.
  matrice4e: f_tip 1230 Hz → PRF 2600 Hz, 1024 표본 = 394 ms = **50 블레이드 주기**.

    python benchmark/report07_three_engine_maps.py [--n 1024] [--drone matrice4e]
"""
from __future__ import annotations

import argparse
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
import report15_probe as RP                                            # noqa: E402  (Sionna 경로)
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                             # noqa: E402
from microdoppler import microdoppler_series                           # noqa: E402
from rcs_sbr import sbr_field                                          # noqa: E402

FC = 3.5e9
OUT = os.path.join(ROOT, "outputs", "report07_three_engines.npz")
OUTJ = os.path.join(ROOT, "outputs", "report07_three_engines.json")
GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}

# ⭐ 2026-08-10 정정 — 이 값이 0.02 였다. 그것은 2026-08-07 이전의 **내 추측**이고,
#   선배 PX4 텔레메트리 실측(0.07~0.29 %)의 9배다. 다른 헤드라인 그림(1·5·6·7)은 이미
#   실측 중간값 ±0.22 % 로 재계산됐는데 이 그림만 뒤처져 있었다.
#   ⚠ 산포가 크면 네 로터의 빗살이 고조파마다 어긋나 맵이 뭉개진다 — 사용자가 «가운데 패널이
#     왜 이렇게 안 좋냐» 고 물은 것의 실제 원인이 이것이다(근거리장 아님 — 우리 팔은 평면파다).
#   야외 산포(±2 %)의 효과는 그림 11(프리셋 비교)이 따로 담당한다.
RPM_SPREAD = float(os.environ.get("SIONNA2_MD_SPREAD", "0.0022"))
PATTERN = np.array([+1.0, -1.0, -0.55, +0.55])
PRF_OVER_FTIP = float(os.environ.get("SIONNA2_MD_PRF_MULT", "4.0"))   # ⭐16 이면 시간분해능 4배


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="matrice4e")
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--az", type=float, default=0.0)
    ap.add_argument("--el", type=float, default=-15.0)
    ap.add_argument("--range", type=float, default=3.0)
    ap.add_argument("--spp", type=int, default=1_000_000)
    a = ap.parse_args()

    spec = DRONES[a.drone]
    fp = FastPoser(spec)
    n_rot = len(fp.dirs)

    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    lam = 3e8 / FC
    R = spec.prop_dia_mm / 1000.0 / 2.0
    f_rev = rpm0 / 60.0
    f_flash = spec.prop_blades * f_rev
    f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))
    # ⭐ PRF = 4·f_tip. 나이퀴스트 최소(2·f_tip)의 두 배 여유다.
    #   ⚠ 2.2배(여유 10 %)로 잡았다가 되돌렸다 — 세 가지가 그 여유를 갉아먹는다:
    #     ① 블레이드 스펙트럼이 f_tip 에서 딱 끊기지 않는다. 우리 실측에서 Sionna 꼬리가
    #        f_tip 밖에 20~30 dB 위로 남는데, 그 꼬리가 **접혀 되돌아와 가짜 능선**이 된다.
    #     ② 로터별 rpm 흩어짐(+2 %)이 f_tip 자체를 올린다.
    #     ③ 날개 두께·비틀림이 f_tip 을 조금 넘는 성분을 만든다.
    #   ⭐ 표본 수는 Sionna 비용이 정하므로, PRF 를 올려도 **비용이 안 늘고 창만 짧아진다**.
    #     1024 표본 @ 5000 Hz = 205 ms = 26 블레이드 주기 — 조각당 8주기를 넉넉히 넘는다.
    # ⭐ 2026-08-10 — PRF 배수를 열었다(사용자: 시간 해상도를 더, 계산량을 더 쓰더라도).
    #   표시 조각을 «블레이드 0.6주기 → 0.2주기» 로 줄이려면 그 짧은 조각에도 표본이 남아야 한다.
    #   PRF 4배 + 표본 수 4배 = **같은 관측 창**에 시간 분해능만 3배 좋아진다(4.7 → 1.6 ms).
    prf = float(np.ceil(PRF_OVER_FTIP * f_tip / 100.0) * 100.0)
    t = np.arange(a.n) / prf
    rpms = rpm0 * (1.0 + RPM_SPREAD * np.resize(PATTERN, n_rot))
    ph = rotor_phases(t, rpms, fp.dirs)                        # (n, n_rot) [deg]

    print(f"\n═══ {spec.name} · az {a.az:.0f} el {a.el:.0f} · {FC/1e9:.2f} GHz ═══")
    print(f"  f_flash {f_flash:.1f} Hz · f_tip {f_tip:.0f} Hz · PRF {prf:.0f} Hz")
    print(f"  표본 {a.n} = {a.n/prf*1e3:.0f} ms = {a.n/prf*f_flash:.0f} 블레이드 주기")
    print(f"  로터별 rpm {np.round(rpms,1).tolist()}", flush=True)

    u = np.array([np.cos(np.radians(a.el)) * np.cos(np.radians(a.az)),
                  np.cos(np.radians(a.el)) * np.sin(np.radians(a.az)),
                  np.sin(np.radians(a.el))])

    series, meta = {}, {}

    # ── ② SBR (싸다 — 먼저) ────────────────────────────────────────────────
    t0 = time.time()
    E = np.array([sbr_field(fp.pose(ph[i]), GM, FC, u) for i in range(a.n)])
    series["sbr"] = E
    meta["sbr"] = {"seconds": time.time() - t0, "engine": "우리 SBR (가림 + 각도의존 Γ)"}
    print(f"  ② sbr    {meta['sbr']['seconds']:6.1f}s", flush=True)

    # ── ③ 순수 PO ─────────────────────────────────────────────────────────
    t0 = time.time()
    _, Ep, _ = microdoppler_series(spec, fc=FC, az=a.az, el=a.el, prf=prf, n_t=a.n,
                                   rpm_per_rotor=rpms)
    series["po"] = Ep
    meta["po"] = {"seconds": time.time() - t0, "engine": "우리 순수 PO (가림 없음)"}
    print(f"  ③ po     {meta['po']['seconds']:6.1f}s", flush=True)

    # ── ① Sionna 자체 (비싸다) ────────────────────────────────────────────
    #   ⚠ 자세마다 씬을 새로 짓는다. 로터 위상이 로터마다 다르므로 `pose_articulated`
    #     대신 우리 FastPoser 로 메쉬를 만들고, 그것을 OBJ 로 써서 Sionna 씬을 짓는다.
    t0 = time.time()
    Es = np.zeros(a.n, complex)
    for i in range(a.n):
        mv = fp.pose(ph[i])
        m = mv.to_mesh()                                        # Sionna 는 진짜 Mesh 가 필요
        d = os.path.join(RP.SCRATCH, f"{spec.key}_TE{i % 2}")
        paths = m.write_obj_per_group(d, spec.key)
        from drones import drone_colors
        cols = drone_colors(spec)
        parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                         mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                 for g, p in paths.items()]
        sc = RP.build_scene(parts, fc=FC)
        RP.place(sc, az=a.az, el=a.el, rng=a.range)
        p = RP.rt.PathSolver()(sc, max_depth=1, los=True, specular_reflection=True,
                               diffuse_reflection=True, refraction=False,
                               samples_per_src=int(a.spp),
                               max_num_paths_per_src=RP.MAX_PATHS, seed=1)
        aa, tau, _, O = RP.unpack(p)
        if aa.size:
            hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
            Es[i] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
        RP.drop_scratch(d)
        if i and i % 100 == 0:
            el_ = time.time() - t0
            print(f"      sionna {i}/{a.n}  {el_:.0f}s  ETA {(a.n-i)/i*el_/60:.1f}분", flush=True)
    series["sionna"] = Es
    meta["sionna"] = {"seconds": time.time() - t0, "spp": int(a.spp),
                      "engine": "Sionna PathSolver, h = Σ a·exp(−j2πf·τ)"}
    print(f"  ① sionna {meta['sionna']['seconds']:6.1f}s", flush=True)

    np.savez_compressed(OUT, **series)
    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "drone": a.drone, "name": spec.name, "fc_hz": FC,
                         "az_deg": a.az, "el_deg": a.el, "range_m": a.range,
                         "n": a.n, "prf_hz": prf, "f_flash_hz": f_flash, "f_tip_hz": f_tip,
                         "blade_periods": a.n / prf * f_flash,
                         "rpm_per_rotor": rpms.tolist(), "rpm_spread_frac": RPM_SPREAD,
                         "why_ko": "세 엔진을 같은 슬로타임 격자에 태워 우리 맵을 검증한다"},
               "engines": meta,
               "levels_db": {k: float(20 * np.log10(np.abs(v).mean() + 1e-30))
                             for k, v in series.items()},
               "ptp_db": {k: float((20 * np.log10(np.abs(v) + 1e-30)).max()
                                   - (20 * np.log10(np.abs(v) + 1e-30)).min())
                          for k, v in series.items()}},
              open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}\n✅ {OUTJ}")


if __name__ == "__main__":
    main()
