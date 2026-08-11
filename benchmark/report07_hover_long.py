# -*- coding: utf-8 -*-
"""
report07_hover_long.py — 문헌 형태의 **호버링 마이크로도플러 맵** (긴 창 + 흔들리는 rpm)

왜 다시 만드나
--------------
사용자가 문헌 그림(호버링 드론 마이크로도플러, Doppler ±2 kHz · Time 0~2 s · −40 dB)을
보여주며 «저런 형태로» 라고 했다. 우리 그림과 셋이 달랐다.

  ① **창이 짧았다** — 205 ms. 문헌은 2 s 다. 능선이 시간에 따라 어떻게 변하는지 보려면 길어야 한다.
  ② ⭐⭐ **rpm 을 고정값으로 뒀다** — 그래서 능선이 자로 그은 듯 곧다.
     ⚠ 실제 호버링은 비행제어기가 자세를 잡느라 **rpm 이 끊임없이 미세하게 흔들린다.**
       문헌 그림의 능선이 물결치는 것이 바로 그것이다. 우리는 그 물리를 아예 안 넣고 있었다.
  ③ 색·축 규약이 달랐다 — jet · −40 dB · ±2 kHz.

무엇을 넣나 — 호버 rpm 의 시간 변동
-----------------------------------
    rpm_k(t) = rpm0 · (1 + s_k + ε_k(t))

  s_k     로터별 정적 치우침 (무게중심·요 토크 균형·프롭 개체차)
  ε_k(t)  제어루프가 만드는 흔들림. 로터마다 **독립**이다.

⭐ 2026-08-11 — 이 파일이 직접 갖고 있던 로터 모델을 `src/rotor_dynamics.py` 로 옮겼다.
  옮기면서 셋을 고쳤다(설계서 `docs/NOISE_AND_ROTOR_PLAN.md` §2):
    ① 정적 치우침을 **결정론적 패턴**(±1, ∓0.55)에서 **가우시안 추출 + 시드**로
    ② 흔들림을 **정현파 한 톤**에서 **OU(저역통과 잡음)** 로 — 랜덤 과정은 선을 넓히고
       정현파는 빗살로 가른다. 물리는 앞쪽이다(조사 §3-4)
    ③ t=0 회전위상을 **정렬**에서 𝒰(0, 360/blades) 로

⛔ **기본값 `--preset legacy` 는 옛 식 그대로**다 — `outputs/report07_hover_long.npz` 의
  `rpm_t` 와 비트동일이고 게이트가 그것을 지킨다(`benchmark/verify_rotor_dynamics.py` G4).

⚠ σ 값은 **다른 기체의 실기 로그**에서 왔다(NeuroBEM 실내 · CODEV 야외 · DJI P3 명령).
  우리 표적(Mavic 4 Pro · Matrice 4E)의 로그를 받으면 그 값이 프리셋을 대체한다.

    python benchmark/report07_hover_long.py [--sec 2.0]                # legacy(기본)
    python benchmark/report07_hover_long.py --preset outdoor --tag _outdoor_ou
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
import rotor_dynamics as rd                                            # noqa: E402
from articulated_fast import FastPoser                                 # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                             # noqa: E402
from rcs_sbr import sbr_field, grid_ref_for_slowtime                   # noqa: E402

FC = 3.5e9
GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
SEED = 20260811

# ⭐ 2026-08-07 정정 — 흩어짐을 ±2 % 로 뒀던 것은 **내 추측**이었고 틀렸다.
#   선배(홍지혁)의 PX4 텔레메트리를 내가 직접 재니 모터 간 산포가 **0.07~0.29 %** 였다.
#   그때 나는 그것을 «너무 작아 비현실적» 이라고 치부했는데, 그것이 실측이다.
#   ⚠ ±2 % 를 쓰면 네 로터의 빗살이 고조파마다 어긋나 맵이 뭉개진다 —
#     문헌 그림의 능선이 가늘고 선명한 이유가 여기 있다.
#
# ⭐ 2026-08-10 프리셋 이원화 — 웹 실측 앵커(outputs/rotor_rpm_web_anchor.json)가
#   그림을 완성했다: SITL 값은 **실내·이상 조건의 하한**이고, 실기체 야외는 더 벌어진다.
#     실내  NeuroBEM  정지비행  산포 ~0.54 % · 흔들림 0.74 % @ 0.7~2.2 Hz
#     야외  CODEV     정지비행  산포 ~2.4 %  · 흔들림 2.5 %  @ ~0.74 Hz
#     실기체 DJI P3 DAT(PWM 환산)  ~2~6 %
#   실증이 야외이므로([[실측=외부]]) 야외 프리셋이 헤드라인 후보다. SITL 프리셋은
#   대칭-이상 통제군으로 유지한다. 실측 로그가 오면 그 값이 프리셋을 대체한다.
# ⭐ 2026-08-11 — 프리셋은 이제 `src/rotor_dynamics.PRESETS` 한 자리에 있다.
#   옛 이름 대응:  옛 "sitl"(정현파 0.15%@2.7Hz) → **"legacy"**(기본, 비트동일)
#                  옛 "outdoor"(정현파 2.5%@1Hz) → **"legacy_outdoor"**
#   새 이름 "sitl"/"indoor"/"outdoor" 는 **OU 판**이다 — 같은 이름이라도 모양이 다르다.
PRESETS = rd.PRESETS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="matrice4e")
    ap.add_argument("--sec", type=float, default=2.0)
    ap.add_argument("--az", type=float, default=0.0)
    ap.add_argument("--el", type=float, default=-15.0)
    ap.add_argument("--preset", default=rd.DEFAULT_PRESET, choices=list(PRESETS),
                    help="로터 랜덤성 프리셋 — legacy(기본, 옛 식 비트동일) / "
                         "legacy_outdoor(옛 outdoor) / sitl·indoor·outdoor(OU 판) / lit_iid")
    ap.add_argument("--seed", type=int, default=SEED,
                    help="난수 시드 — 정적 산포·흔들림·초기위상 추첨. legacy 는 결정론이라 무관")
    ap.add_argument("--tau-motor", type=float, default=None,
                    help="2극(로터 관성) 시상수 [s]. 기본 끔. 켤 값의 문헌 범위 0.0125~0.025")
    ap.add_argument("--tag", default=None,
                    help="출력 접미사(기본: legacy 는 없음=기존 경로, 그 외 프리셋명)")
    ap.add_argument("--overwrite", action="store_true",
                    help="같은 이름의 원장이 이미 있으면 덮어쓴다(기본은 중단)")
    a = ap.parse_args()

    jit = rd.get(a.preset)
    if a.tau_motor is not None:
        jit = jit.with_(tau_motor_s=float(a.tau_motor))
    preset_why = jit.source
    tag = a.tag if a.tag is not None else ("" if a.preset == rd.DEFAULT_PRESET
                                           else f"_{a.preset}")
    npz_path = f"{ROOT}/outputs/report07_hover_long{tag}.npz"
    #  ⛔ 원장 보호 — 이름이 겹치면 조용히 덮지 않는다. 특히 새 OU `outdoor` 는
    #     옛 정현파 판이 이미 쓴 `_outdoor` 와 이름이 겹친다.
    if os.path.exists(npz_path) and not a.overwrite:
        raise SystemExit(f"⛔ 이미 있다: {npz_path}\n"
                         f"   --tag 로 새 이름을 주거나 --overwrite 를 붙여라.")

    spec = DRONES[a.drone]
    fp = FastPoser(spec)
    n_rot = len(fp.dirs)
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    lam = 3e8 / FC
    R = spec.prop_dia_mm / 1000.0 / 2.0
    f_rev = rpm0 / 60.0
    f_flash = spec.prop_blades * f_rev
    f_tip = 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(a.el))
    # ⭐PRF 배수 — 시간 분해능의 유일한 레버(2026-08-10). 표시 조각의 시간 길이는
    #   (비율 × 블레이드 주기)라 PRF 와 무관하지만, 비율을 0.6→0.2 로 내리려면 그 짧은
    #   조각에도 표본이 남아야 하므로 PRF 를 함께 올린다. 16 이면 4.7 ms → 1.6 ms.
    prf_mult = float(os.environ.get("SIONNA2_MD_PRF_MULT", "4.0"))
    prf = float(np.ceil(prf_mult * f_tip / 100.0) * 100.0)
    n = int(round(a.sec * prf))
    t = np.arange(n) / prf

    # ⭐ 흔들리는 rpm → 위상은 그 적분이다. 로터마다 **독립**으로 흔든다.
    #    ⛔ legacy 프리셋이면 아래 두 줄이 옛 식과 글자 그대로 같다(게이트 G4).
    rng = np.random.default_rng(a.seed)
    rpm_t, rpm_diag = rd.rpm_series(rpm0, n_rot, n, prf, jit, rng)
    period_deg = 360.0 / float(spec.prop_blades)
    base_deg = rd.initial_phase_deg(n_rot, jit, rng, period_deg=period_deg)
    ph = rd.phases(rpm_t, prf, fp.dirs, base_deg=base_deg)
    rpm_stats = rd.summary(rpm_t, prf, jit)

    print(f"\n═══ {spec.name} 호버링 · az {a.az:.0f} el {a.el:.0f} · {FC/1e9:.2f} GHz ═══")
    print(f"  f_flash {f_flash:.1f} Hz · f_tip {f_tip:.0f} Hz · PRF {prf:.0f} Hz")
    print(f"  {a.sec:.1f} s = {n} 표본 = {a.sec*f_flash:.0f} 블레이드 주기")
    print(f"  로터 프리셋 «{jit.name}» seed {a.seed} · {rpm_diag['mode']}")
    print(f"    정적 산포 σ_s {jit.static_sigma:.4f} (실측 {rpm_stats['static_spread_std_rel']:.5f}) · "
          f"흔들림 σ_w {jit.wobble_sigma:.4f} (실측 {rpm_stats['wobble_std_rel']:.5f})")
    print(f"    T {jit.tau_ctl_s:.4f} s (f_ctl {jit.f_ctl_hz:.2f} Hz) · τ_m {jit.tau_motor_s} · "
          f"초기위상 {'𝒰(0,%.0f°)' % period_deg if jit.random_phase else '정렬(0)'} "
          f"{np.round(base_deg, 1).tolist()}", flush=True)

    u = np.array([np.cos(np.radians(a.el)) * np.cos(np.radians(a.az)),
                  np.cos(np.radians(a.el)) * np.sin(np.radians(a.az)),
                  np.sin(np.radians(a.el))])

    # ⭐ 광선 격자를 **얼린다**(2026-08-10). 격자는 자세의 bbox 에서 나오는데 프로펠러가 돌면
    #   bbox 가 숨을 쉬어 위상 원점(ctr)과 표본 집합(Rout·n)이 프레임마다 바뀐다. 이 파일은
    #   2 초짜리 긴 창을 보므로 그 «자의 흔들림» 이 능선의 물결로 오독되기 딱 좋다.
    #   판은 로터 한 바퀴의 합집합 bbox 다 — rpm 이 흔들려도 각 로터가 그 봉투 안에 든다.
    #   SIONNA2_FREEZE_GRID=0 이면 None → 옛 동작(전후 비교 스위치).
    gref = grid_ref_for_slowtime(fp.pose, fp.dirs, FC)
    print("  격자(얼림) " + (f"n={gref.n} ({gref.n**2}발) · Rout={gref.Rout:.4f} m"
                            if gref is not None else "OFF — SIONNA2_FREEZE_GRID=0"), flush=True)

    E = np.zeros(n, complex)
    t0 = time.time()
    for i in range(n):
        E[i] = sbr_field(fp.pose(ph[i]), GM, FC, u, grid_ref=gref)
        if i and i % 1000 == 0:
            el = time.time() - t0
            print(f"    {i}/{n}  {el:.0f}s  ETA {(n-i)/i*el/60:.1f}분", flush=True)
    secs = time.time() - t0

    np.savez_compressed(npz_path, E=E, t=t, rpm_t=rpm_t, base_phase_deg=base_deg)
    json.dump({"_meta": {"generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "drone": a.drone, "name": spec.name, "fc_hz": FC,
                         "az_deg": a.az, "el_deg": a.el,
                         "seconds": a.sec, "n": n, "prf_hz": prf,
                         "f_flash_hz": f_flash, "f_tip_hz": f_tip,
                         "blade_periods": a.sec * f_flash,
                         "rpm0": rpm0,
                         # ⭐ 로터 랜덤성 — 프리셋·시드·실측 진단을 통째로 박는다
                         "preset": a.preset, "preset_why_ko": preset_why,
                         "rotor_seed": int(a.seed),
                         "rotor_jitter": jit.asjson(),
                         "rotor_diag": rpm_diag,
                         "rotor_measured": {k: v for k, v in rpm_stats.items()
                                            if k != "jitter"},
                         "initial_phase_deg": base_deg.tolist(),
                         "phase_period_deg": period_deg,
                         "rotor_model_ko": (
                             "rpm_k(t) = rpm0·(1 + s_k + ε_k(t)); s_k ~ N(0,σ_s) 평균제거, "
                             "ε_k(t) = OU(σ_w, T) 로터별 독립, θ_k(0) ~ U(0,360/blades). "
                             "legacy 프리셋만 옛 결정론 패턴 + 정현파 한 톤이다."),
                         "compute_seconds": secs,
                         "grid_frozen": bool(gref is not None),
                         "grid_ref": (gref.asjson() if gref is not None else None),
                         "declared_ko": ("⚠ σ_s·σ_w·T 는 **다른 기체**의 실기 로그에서 왔다"
                                         "(NeuroBEM 실내·CODEV 야외·DJI P3 명령, "
                                         "outputs/rotor_rpm_web_anchor.json). 우리 표적의 "
                                         "실측 비행 로그가 이 값들을 대체한다. 시간 흔들림에는 "
                                         "마이크로도플러 문헌 선례가 없다.")}},
              open(f"{ROOT}/outputs/report07_hover_long{tag}.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"\n  ✅ {secs/60:.1f}분 · outputs/report07_hover_long{tag}.npz")


if __name__ == "__main__":
    main()
