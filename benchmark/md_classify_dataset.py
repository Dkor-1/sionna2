# -*- coding: utf-8 -*-
"""
md_classify_dataset.py — **마이크로도플러로 기종을 가를 수 있나** · 특징 데이터셋 (2026-08-10)
================================================================================================
메인 태스크의 나머지 절반. 지금까지는 «보이나»(탐지)만 쟀다. 여기서는 «무엇이 보이나»
(분류)를 묻는다.

물음
-----
정지비행하는 드론을 **마이크로도플러만으로** 기종을 가를 수 있나.

무엇이 비싼가 — 그리고 어떻게 푸는가
------------------------------------
SBR 한 자세가 **250~630 ms** 다(2026-08-10 실측, GPU 3 경합 상태). 시간표본마다 광선을 쏘면
시행 하나(PRF 20 kHz · 0.25 s = 5,000 표본)에 25 분이 걸린다. 기체당 20 시행은 불가능하다.

⭐ **로터별 위상표(per-rotor phase table)** 로 푼다.
    E(φ₁..φ_N) = E_ref + Σ_k ΔE_k(φ_k),   ΔE_k(φ) = E(로터 k 만 φ, 나머지 기준) − E_ref
  비용: (드론·자세) 하나당 n_rotors × n_phase + 1 회. 표를 한 번 만들면
  **rpm·초기위상·PRF·창길이를 아무렇게나 바꿔도 공짜**다 — 그래서 시행을 많이 벌 수 있다.

  ⭐ 이 식은 **근사가 아니라 항등식**이다 — 단, 광선 격자를 고정했을 때만. SBR 은 1-bounce
    라 광선 하나가 면 하나만 맞히고, 로터는 공간적으로 겹치지 않는다. 그래서 광선 격자가
    같으면 기여가 정확히 더해진다. 실측 잔차 **1e−19**(아래 PinnedPoser 주석의 표).
  ⚠ 격자를 고정하지 않으면 이 식은 **깨진다**. 프로펠러가 돌면 bbox 가 움직여 격자가
    표적을 따라 재등록되기 때문이다 — 그때 잔차는 신호의 0.75~3.2 배였다.
    그 결함과 크기는 `PinnedPoser` 주석에 숫자로 적었다.

⭐ 왜 base rpm 을 흩뜨리나 — 이 축의 정직성이 여기 걸려 있다
--------------------------------------------------------------
`drones.py` 의 `hover_rpm` 은 기체마다 **상수 하나**다. 그대로 쓰면 f_flash 가 곧 정답표라
분류기가 «회전수를 읽는» 것으로 100% 를 맞춘다 — 그건 분류가 아니다.
그래서 시행마다 base rpm 을 ±6% 흩뜨린다(배터리 전압·탑재중량·공기밀도·자세유지). 그 결과
mini5pro(5500) 와 phantom4(5500) 는 f_flash 가 **완전히 겹치고**, typhoonh480(5600) 도 겹친다.
남는 것은 기하다:  f_tip / f_flash = 2πR/λ — **rpm 이 약분되어 프롭 반지름만 남는다.**

산출
-----
  outputs/md_classify_tables/*.npz     (드론·자세)별 위상표      [중간산물]
  outputs/md_classify_verify.json      분해 근사 검증 · 주기성 검증
  outputs/md_classify_features.npz     시행별 특징 행렬          [md_classify_run.py 입력]

    python benchmark/md_classify_dataset.py tables --shard 0 --nshards 9 --gpu 3
    python benchmark/md_classify_dataset.py verify --gpu 3
    python benchmark/md_classify_dataset.py build          # CPU
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

OUT_DIR = os.path.join(ROOT, "outputs")
TAB_DIR = os.path.join(OUT_DIR, "md_classify_tables")
VERIFY_JSON = os.path.join(OUT_DIR, "md_classify_verify.json")
FEAT_NPZ = os.path.join(OUT_DIR, "md_classify_features.npz")

FC = 3.5e9

# ── 기체 6종 — 크기·로터수·회전수가 갈리게. ⚠ drones.py 의 9종은 **전부 2블레이드**라
#    블레이드 수는 갈리지 않는다(그 축은 우리 등록부에 없다). 갈리는 축은
#    프롭 지름(119~381 mm) · 로터 수(4·6·8) · 호버 rpm(3800~9200) 이다.
DRONE_KEYS = ["mini2", "mini5pro", "phantom4", "matrice4e", "typhoonh480", "s1000plus"]

# ── 자세: 방위 6 × 앙각 3. el<0 = 배 쪽 = 지상 레이더가 실제로 보는 쪽.
AZ_LIST = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]
EL_LIST = [-30.0, -15.0, 0.0]
ASPECTS = [(az, el) for el in EL_LIST for az in AZ_LIST]

N_PHASE = 100            # 위상표 표본 수 (0~180°, 1.8° 간격)
PHASE_PERIOD_DEG = 180.0  # 2블레이드 프롭의 회전 주기

# ── 시행 무작위화 (선언된 가정) ────────────────────────────────────────────────
RPM_BASE_FRAC = 0.06      # base rpm ±6%
RPM_SPREAD_LO = 0.0007    # 로터간 산포 σ 하한 (선배 PX4 텔레메트리 실측 0.07%)
RPM_SPREAD_HI = 0.0029    # 상한 (0.29%)
N_DRAW_PER_ASPECT = 8     # 자세당 rpm·위상 추첨 수 → 기체당 18×8 = 144 시행

# ── 관측 설정 ─────────────────────────────────────────────────────────────────
PRF_MAIN = 20000.0        # 헤드라인 PRF [Hz] — 표를 쓰므로 표본은 공짜다
T_MAIN = 0.25             # 헤드라인 창 [s]
PRF_SWEEP = [20000.0, 5000.0, 2000.0, 1000.0]
T_SWEEP = [1.00, 0.25, 0.10, 0.05]   # ⭐긴 창은 로터간 간섭무늬를 평균한다
#  ⭐ 왜 이렇게 낮은 SNR 까지 내려가나 — 0.25 s × 20 kHz = 5,000 표본이라 **전창 FFT**
#     (features() ①)의 코히런트 적분 이득이 10log₁₀(5000) − 1.76(Hann) = 35.2 dB 다.
#     표본당 SNR 0 dB 는 스펙트럼에서 35 dB 선으로 서므로 분류가 끄떡없다.
#     무너지는 자리를 보려면 −30 dB 까지 내려야 한다.
#  ⚠⚠ **혼동 금지 — 「37 dB」짜리 양이 셋이고 서로 다르다**(outputs/snr_convention.json):
#       · 정합필터 이득(빠른시간, PRI 안)   10log10(B/PRF) = 10log10(1e8/2e4) = 36.99 dB
#       · 전창 코히런트 적분(슬로타임 5,000 표본, Hann)   10log10(5000)−1.76 = 35.23 dB ← 여기
#       · STFT 한 조각(맵, 70 표본·Hann)                  10log10(70)−1.76   = 16.69 dB
#     ⭐ 그리고 아래 SNR 축은 **AC(블레이드선) 기준**이다 — 총전력 기준과 기체별 17.3~37.2 dB
#       어긋난다. 변환은 npz 의 `dc_ac_db` 로 한다.
SNR_SWEEP_DB = [1e9, 10.0, 0.0, -10.0, -15.0, -20.0, -25.0, -30.0]   # 1e9 = 잡음 없음

SEED = 20260810


# ═══════════════════════════════════════════════════════════════════════════════
#  GPU 단계 — 위상표
# ═══════════════════════════════════════════════════════════════════════════════
def _gpu_boot(gpu):
    os.environ["SIONNA2_GPU"] = str(gpu)
    from gpu import pick
    pick(verbose=False)


def _look(az_deg, el_deg):
    import numpy as np
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], float)


def _worklist():
    return [(k, ai) for k in DRONE_KEYS for ai in range(len(ASPECTS))]


# ═══════════════════════════════════════════════════════════════════════════════
#  ⭐⭐ 광선 격자를 자세에 **못 박는다** — 2026-08-10 에 찾은 정확성 결함
# ═══════════════════════════════════════════════════════════════════════════════
#  무엇이 문제였나
#    `rcs_sbr.sbr_field` 는 광선 격자를 **메쉬 bbox 에서** 만든다:
#        ctr = bbox 중심,  Rout = max|V−ctr|·pad + 3d,  n = ceil(2·Rout/d)
#    프로펠러가 돌면 정점이 움직이니 bbox 도 움직인다. mini2·el−30 실측:
#        위상 [0,0,0,0] → ctr_y +0.00413 · Rout 0.2239 · n 63
#        위상 [36,0,0,0] → ctr_y +0.00125 · Rout 0.2124 · n 62
#        위상 [90,54,0,0] → ctr_y −0.01751 · Rout 0.2023 · n 57
#    격자가 **표적을 따라 재등록**되면서 자세마다 다른 표본화 오차가 들어간다.
#
#  얼마나 큰가 — 같은 두 자세의 |E(φ)−E(0)|
#        격자 고정 안 함  7.43e−04      ← 진짜 블레이드 변조 + 격자 흔들림
#        격자 고정        2.34e−04      ← 진짜 블레이드 변조
#    ⇒ 허위 변조가 진짜의 **3.0 배**(+9.6 dB). 슬로타임 열이 격자잡음에 지배된다.
#
#  왜 고정이 «옳은» 쪽인가 — 이건 수치 편의가 아니라 물리다.
#    광선 격자는 **입사 평면파의 표본화**다. 실제 레이더의 입사파는 표적이 프로펠러를
#    돌린다고 해서 따라 움직이지 않는다. 격자는 공간에 고정돼 있어야 한다.
#
#  어떻게 고정하나
#    어느 면도 참조하지 않는 **핀 정점 6 개**를 c ± R·ê 에 얹는다. `_mi_scene_from_mesh`
#    는 면이 참조하는 정점만 씬에 넣으므로(`used = np.unique(f)`) 산란에는 영향이 없고,
#    `sbr_field` 의 bbox 만 상수로 못 박힌다. 비용은 사실상 0 이다(n 63 → 64).
#
#  ⭐ 2026-08-10 — 이 결함은 이 파일 밖에도 있었고, 이제 커널이 직접 받는다.
#    `rcs_sbr.sbr_field(..., grid_ref=...)` + `grid_ref_for_slowtime()` 이 그것이다.
#    `microdoppler.microdoppler_sbr` · `report15b_microdoppler_recompute._sbr_series` ·
#    `report07_three_engine_maps` · `report07_hover_long` · `report07b_bistatic_md` ·
#    `report15_po_control.arm_sbr` · `report15_sweep_mini2.secS_sbr` 가 전부 그 배선을 쓴다
#    (스위치 SIONNA2_FREEZE_GRID=0 이면 옛 동작).
#    ⚠ 이 파일은 **핀 정점** 방식을 그대로 둔다 — 이미 얼려져 있고(ctr·Rout·n 이 상수),
#      이미 낸 위상표(TAB_DIR)와 규약을 바꾸면 그 원장이 통째로 무효가 되기 때문이다.
#      두 방식은 «격자를 자세와 무관하게 만든다» 는 같은 물리를 다른 손잡이로 잡은 것이다.
class PinnedPoser:
    """`FastPoser` 를 감싸 광선 격자를 자세와 무관하게 고정한다."""

    def __init__(self, spec, n_probe=16, margin=1.02, seed=0):
        import numpy as np
        from articulated_fast import FastPoser
        self.fp = FastPoser(spec)
        self.n_rotors = self.fp.n_rotors
        self.dirs = self.fp.dirs
        self.f, self.g = self.fp.f, self.fp.g
        V0 = self.fp.pose([0.0] * self.n_rotors).v
        c = 0.5 * (V0.max(0) + V0.min(0))
        rng = np.random.default_rng(seed)
        R = 0.0
        for p in np.linspace(0.0, 180.0, n_probe, endpoint=False):
            R = max(R, float(np.linalg.norm(
                self.fp.pose([float(p)] * self.n_rotors).v - c, axis=1).max()))
        for _ in range(n_probe):
            R = max(R, float(np.linalg.norm(
                self.fp.pose(list(rng.uniform(0, 180, self.n_rotors))).v - c,
                axis=1).max()))
        self.c, self.R = c, R * float(margin)
        self._pins = c + self.R * np.array(
            [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)

    def pose(self, rotor_phase_deg):
        import numpy as np
        mv = self.fp.pose(rotor_phase_deg)
        return _PinnedView(np.vstack([mv.v, self._pins]), mv.f, mv.g)


class _PinnedView:
    __slots__ = ("v", "f", "g")

    def __init__(self, v, f, g):
        self.v, self.f, self.g = v, f, g


def cmd_tables(args):
    _gpu_boot(args.gpu)
    import numpy as np
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field

    gmat = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    os.makedirs(TAB_DIR, exist_ok=True)
    jobs = _worklist()[args.shard::args.nshards]
    phis = np.linspace(0.0, PHASE_PERIOD_DEG, N_PHASE, endpoint=False)

    posers = {}
    t_start = time.time()
    for ji, (key, ai) in enumerate(jobs):
        az, el = ASPECTS[ai]
        path = os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz")
        if os.path.exists(path) and not args.force:
            continue
        spec = DRONES[key]
        if key not in posers:
            posers[key] = PinnedPoser(spec)
        fp = posers[key]
        u = _look(az, el)
        n_r = fp.n_rotors

        t0 = time.time()
        E_ref = sbr_field(fp.pose([0.0] * n_r), gmat, FC, u)
        dE = np.zeros((n_r, N_PHASE), complex)
        for k in range(n_r):
            ph = [0.0] * n_r
            for j, p in enumerate(phis):
                ph[k] = float(p)
                dE[k, j] = sbr_field(fp.pose(ph), gmat, FC, u) - E_ref
        secs = time.time() - t0

        np.savez_compressed(path, E_ref=np.array([E_ref]), dE=dE, phis=phis,
                            az=az, el=el, n_rotors=n_r, drone=key,
                            dirs=np.asarray(fp.dirs, float), seconds=secs,
                            grid_pinned=True, pin_radius_m=fp.R, pin_center=fp.c)
        done = ji + 1
        el_s = time.time() - t_start
        print(f"[s{args.shard}] {done}/{len(jobs)} {key} a{ai:02d} "
              f"(az{az:.0f} el{el:.0f}) {secs:.0f}s  경과 {el_s/60:.1f}분  "
              f"ETA {(len(jobs)-done)/max(done,1)*el_s/60:.1f}분", flush=True)
    print(f"[s{args.shard}] ✅ 완료 {len(jobs)} 작업", flush=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  GPU 단계 — 검증 (근사가 얼마나 맞나)
# ═══════════════════════════════════════════════════════════════════════════════
def cmd_verify(args):
    _gpu_boot(args.gpu)
    import numpy as np
    from articulated_fast import rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT
    from rcs_sbr import sbr_field

    rng = np.random.default_rng(SEED + 7)
    keys = [k for k in args.drones.split(",") if k in DRONE_KEYS] or DRONE_KEYS
    out_path = (VERIFY_JSON if args.tag == "" else
                VERIFY_JSON.replace(".json", f"_{args.tag}.json"))
    gmat = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    out = {"_meta": {"script": "benchmark/md_classify_dataset.py verify",
                     "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "fc_hz": FC, "n_phase": N_PHASE,
                     "phase_period_deg": PHASE_PERIOD_DEG},
           "periodicity": {}, "decomposition": {}, "grid_pinning": {},
           "exact_series": {}}

    # ── (a) 프롭이 정말 180° 주기인가 (2블레이드 가정의 근거) ────────────────
    for key in keys:
        spec = DRONES[key]
        fp = PinnedPoser(spec)
        u = _look(30.0, -15.0)
        errs = []
        for p in rng.uniform(0, 180, 6):
            ph = list(rng.uniform(0, 180, fp.n_rotors))
            E1 = sbr_field(fp.pose(ph), gmat, FC, u)
            ph2 = [x + 180.0 for x in ph]
            E2 = sbr_field(fp.pose(ph2), gmat, FC, u)
            errs.append(abs(E1 - E2) / (abs(E1) + 1e-30))
        out["periodicity"][key] = {
            "rel_err_max": float(np.max(errs)), "rel_err_mean": float(np.mean(errs)),
            "n_pairs": len(errs), "blades": int(spec.prop_blades)}
        print(f"주기성 {key:12s} 최대 상대오차 {np.max(errs):.3e}", flush=True)

    # ── (b) 분해 근사 오차 — 무작위 전체자세 vs 표 합성 ──────────────────────
    check_aspects = [0, len(ASPECTS) // 2, len(ASPECTS) - 1]
    for key in keys:
        spec = DRONES[key]
        fp = PinnedPoser(spec)
        for ai in check_aspects:
            path = os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz")
            if not os.path.exists(path):
                continue
            z = np.load(path, allow_pickle=True)
            E_ref, dE, phis = complex(z["E_ref"][0]), z["dE"], z["phis"]
            az, el = float(z["az"]), float(z["el"])
            u = _look(az, el)
            ex, ap = [], []
            for _ in range(args.n_check):
                ph = rng.uniform(0, 180, fp.n_rotors)
                ex.append(sbr_field(fp.pose(list(ph)), gmat, FC, u))
                ap.append(E_ref + sum(np.interp(ph[k] % 180.0, phis, dE[k].real,
                                                period=180.0)
                                      + 1j * np.interp(ph[k] % 180.0, phis, dE[k].imag,
                                                       period=180.0)
                                      for k in range(fp.n_rotors)))
            ex, ap = np.asarray(ex), np.asarray(ap)
            ac_e = ex - ex.mean()
            err = ap - ex
            out["decomposition"][f"{key}/a{ai:02d}"] = {
                "az_deg": az, "el_deg": el, "n": int(len(ex)),
                "rms_err_over_rms_ac": float(np.sqrt((np.abs(err) ** 2).mean())
                                             / (np.sqrt((np.abs(ac_e) ** 2).mean()) + 1e-30)),
                "rms_err_over_rms_total": float(np.sqrt((np.abs(err) ** 2).mean())
                                                / (np.sqrt((np.abs(ex) ** 2).mean()) + 1e-30)),
                "corr_ac": float(np.abs(np.vdot(ac_e, ap - ap.mean()))
                                 / (np.linalg.norm(ac_e) * np.linalg.norm(ap - ap.mean()) + 1e-30)),
            }
            d = out["decomposition"][f"{key}/a{ai:02d}"]
            print(f"분해 {key:12s} a{ai:02d} RMS오차/AC {d['rms_err_over_rms_ac']:.3f} "
                  f"AC상관 {d['corr_ac']:.4f}", flush=True)

    # ── (c) ⭐ 광선 격자 고정의 효과 — 이 라운드에서 찾은 정확성 결함의 원장 ──
    #    두 가지를 잰다.
    #      ① 변조 크기  RMS|E(φ)−E(0)|      — 격자가 흔들리면 허위 변조가 얹힌다
    #      ② 덧셈 잔차  |E₀+Δ₀+Δ₁−E(φ₀,φ₁)| — 격자가 같으면 0 이어야 한다(1-bounce)
    from articulated_fast import FastPoser as _FP
    for key in keys:
        spec = DRONES[key]
        u = _look(0.0, -30.0)
        cell = {}
        for tag, poser in (("pinned", PinnedPoser(spec)), ("moving", _FP(spec))):
            n = poser.n_rotors
            E0 = sbr_field(poser.pose([0.0] * n), gmat, FC, u)
            mods, resid = [], []
            for _ in range(6):
                p0, p1 = rng.uniform(0, 180, 2)
                a = [0.0] * n; a[0] = float(p0)
                b = [0.0] * n; b[1] = float(p1)
                c = [0.0] * n; c[0], c[1] = float(p0), float(p1)
                d0 = sbr_field(poser.pose(a), gmat, FC, u) - E0
                d1 = sbr_field(poser.pose(b), gmat, FC, u) - E0
                Ex = sbr_field(poser.pose(c), gmat, FC, u)
                mods.append(abs(Ex - E0))
                resid.append(abs(E0 + d0 + d1 - Ex) / (abs(Ex - E0) + 1e-30))
            cell[tag] = {"E0_abs": float(abs(E0)),
                         "modulation_rms": float(np.sqrt(np.mean(np.square(mods)))),
                         "additivity_residual_median": float(np.median(resid)),
                         "additivity_residual_max": float(np.max(resid))}
        cell["spurious_modulation_ratio"] = float(
            cell["moving"]["modulation_rms"] / (cell["pinned"]["modulation_rms"] + 1e-30))
        cell["spurious_modulation_db"] = float(
            20 * np.log10(cell["spurious_modulation_ratio"] + 1e-30))
        out["grid_pinning"][key] = cell
        print(f"격자 {key:12s} 허위변조 배수 {cell['spurious_modulation_ratio']:5.2f}x  "
              f"덧셈잔차 고정 {cell['pinned']['additivity_residual_median']:.2e} / "
              f"흔들림 {cell['moving']['additivity_residual_median']:.3f}", flush=True)

    # ── (d) 정확한 시계열 한 벌 — 특징까지 대조한다 ─────────────────────────
    series = {}
    for key in keys:
        spec = DRONES[key]
        fp = PinnedPoser(spec)
        ai = args.series_aspect
        az, el = ASPECTS[ai]
        u = _look(az, el)
        base = float(spec.hover_rpm)
        rpms = base * (1.0 + rng.normal(0, 0.0018, fp.n_rotors))
        rpms -= rpms.mean() - base
        p0 = rng.uniform(0, 180, fp.n_rotors)
        prf, n_t = args.series_prf, args.series_n
        t = np.arange(n_t) / prf
        ph = rotor_phases(t, rpms, fp.dirs, base_deg=p0)
        E = np.zeros(n_t, complex)
        t0 = time.time()
        for i in range(n_t):
            E[i] = sbr_field(fp.pose(ph[i]), gmat, FC, u)
        series[f"{key}/E"] = E
        series[f"{key}/rpms"] = rpms
        series[f"{key}/p0"] = p0
        out["exact_series"][key] = {"aspect": int(ai), "az_deg": az, "el_deg": el,
                                    "prf_hz": prf, "n_t": int(n_t),
                                    "seconds": round(time.time() - t0, 1)}
        print(f"정확시계열 {key:12s} {time.time()-t0:.0f}s", flush=True)
    np.savez_compressed(os.path.join(
        OUT_DIR, f"md_classify_exact_series{'' if args.tag == '' else '_' + args.tag}.npz"),
        **series)

    with open(out_path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=float)
    print(f"✅ {out_path}")


# ═══════════════════════════════════════════════════════════════════════════════
#  CPU 단계 — 시행 합성 + 특징
# ═══════════════════════════════════════════════════════════════════════════════
def _fine_tables(dE, phis, n_fine=4096):
    """위상표를 촘촘한 격자로 올린다 — 주기 큐빅 스플라인(대역제한 보간).
    이후 시행 합성은 정수 인덱싱뿐이라 CPU 로 공짜다."""
    import numpy as np
    from scipy.interpolate import CubicSpline
    xs = np.concatenate([phis, [PHASE_PERIOD_DEG]])
    fine = np.linspace(0.0, PHASE_PERIOD_DEG, n_fine, endpoint=False)
    out = np.zeros((dE.shape[0], n_fine), complex)
    for k in range(dE.shape[0]):
        yr = np.concatenate([dE[k].real, [dE[k].real[0]]])
        yi = np.concatenate([dE[k].imag, [dE[k].imag[0]]])
        out[k] = (CubicSpline(xs, yr, bc_type="periodic")(fine)
                  + 1j * CubicSpline(xs, yi, bc_type="periodic")(fine))
    return out


def synth(E_ref, fine, dirs, rpms, p0, prf, n_t):
    """표에서 슬로타임 복소열 E(t) 를 뽑는다.

    ⭐ `rpms` 는 **1차원**(로터별 상수, 현행) 또는 **2차원 (n_t, n_rotors)**(시간에 따라
      흔들리는 rpm, `rotor_dynamics.rpm_series()` 산출)이다. 2차원이면 위상이 적분이 된다.
      ⭐⭐ 위상표는 **각도의 함수** ΔE_k(φ_k) 라 rpm 이 시간에 따라 변해도 표를 다시 만들
        필요가 없다 — 그래서 로터 랜덤성 개선에 GPU 가 한 톨도 안 든다.
    ⛔ 1차원 경로는 이 확장 전과 비트동일이다(게이트 verify_rotor_dynamics.py G6)."""
    import numpy as np
    from articulated_fast import rotor_phases        # 위상 계산은 커널 하나만 쓴다
    n_fine = fine.shape[1]
    t = np.arange(n_t) / prf
    E = np.full(n_t, E_ref, complex)
    ph_all = rotor_phases(t, rpms, dirs, p0, dt=1.0 / prf)
    for k in range(fine.shape[0]):
        ph = ph_all[:, k]
        idx = np.mod(ph / PHASE_PERIOD_DEG * n_fine, n_fine)
        i0 = np.floor(idx).astype(np.int64) % n_fine
        i1 = (i0 + 1) % n_fine
        w = idx - np.floor(idx)
        E += fine[k, i0] * (1 - w) + fine[k, i1] * w
    return E


# ─────────────────────────────────────────────────────────────────────────────
#  특징 — 전부 **물리적으로 뜻이 있는 양**. 블랙박스 임베딩은 쓰지 않는다.
# ─────────────────────────────────────────────────────────────────────────────
#  ⭐ 왜 «플래시 고조파 빗살» 로 재는가 (2026-08-10 실측이 설계를 바꿨다)
#    처음엔 도플러 에너지 백분위로 날개끝 f_tip 을 재려 했다. 안 된다 —
#    SBR 은 광선 격자가 이산이라 블레이드가 돌 때 히트가 들락날락해서
#    **−33~−35 dB 광대역 각도잡음 바닥**이 깔린다(원장: md_classify_verify.json).
#    그래서 98% 백분위가 f_tip 1,341 Hz 대신 2,152 Hz 를 준다.
#    빗살로 재면 바닥을 **기준선으로 삼아** 그 위로 솟은 고조파만 세면 된다.
#
#  ⭐⭐ 그리고 이 눈금이 물리적으로 옳다.  로터 위상 φ 의 주기함수라
#    도플러 성분은 m·f_flash 에만 선다. 마지막으로 서는 고조파는
#        m_edge = f_tip / f_flash = 2πR/λ        ← **rpm 이 약분된다**
#    즉 m_edge 는 «파장 단위 프롭 반지름» 을 바로 읽는다.
#    (mini2 4.37 · mini5pro 5.59 · typhoonh480 8.44 · phantom4 8.80 ·
#     matrice4e 10.05 · s1000plus 13.97)
N_HARM = 12          # 특징으로 쓰는 고조파 수
M_CAP = 24           # 빗살을 세는 상한
NHARM_NAMES = [f"h{m}" for m in range(1, N_HARM + 1)]
FEATURE_NAMES = (
    ["f_flash_hat",       # [Hz] 블레이드 플래시율 — 회전수 그 자체 (rate)
     "f_edge",            # [Hz] 도플러 확산 규모 = m_cent·f_flash — rpm×R 에 비례 (abs)
     "m_cent", "m_rms",   # ⭐ 빗살 고조파 모멘트, rpm 무관 — 2πR/λ 의 단조함수
     "dc_over_ac_db",     # 동체/블레이드 산란비 — 동체 크기 대리
     "flash_contrast_db",  # STFT 날개끝 띠의 시간변조 깊이 — 플래시 또렷함
     "env_kurtosis",      # 포락선 첨도 — 플래시가 뾰족한가
     "half_corr",         # 반창 스펙트럼 상관 — 비정상성(로터 산포)
     "asym"]              # ± 도플러 비대칭
    + NHARM_NAMES         # 빗살 고조파 세기 분포 — 베셀 포락선 = 프롭 반지름 지문
    + [f"fold_h{m}" for m in range(1, 7)]   # 한 주기 안 하위플래시 구조 — 로터 엇갈림
)
# 특징 무리 — 대조 실험용
G_RATE = ["f_flash_hat"]                      # 회전수 읽기
G_ABS = ["f_edge"]                            # 절대 도플러 규모 (rpm×R)
G_FREE = [n for n in FEATURE_NAMES if n not in G_RATE + G_ABS]   # 규모 자유


F_FLASH_MIN, F_FLASH_MAX = 50.0, 600.0    # 등록부 9종의 f_flash 범위(80~307 Hz)를 감싼다


def flash_rate(Eac, prf, fmin=F_FLASH_MIN, fmax=F_FLASH_MAX, n_harm=8):
    """포락선 전력의 **고조파 합** 으로 플래시율을 찾는다.

    ⚠ 2026-08-10 실측 — 자기상관 첫 봉우리는 **부고조파로 샌다.** mini2(참값 307 Hz)에서
      자기상관이 주기의 2·3 배 지연에 같은 높이의 봉우리를 만들어 추정치가 235±77 Hz 로
      무너졌다(mini5pro 는 184±6 으로 멀쩡했다 — 기체마다 다르게 틀려서 더 나쁘다).
    ⭐ 고조파 합은 부고조파를 스스로 벌한다: f₀/2 를 후보로 놓으면 f₀/2·3f₀/2… 자리에
      에너지가 없어 점수가 반토막 난다. 그 다음 미세격자로 다듬는다."""
    import numpy as np
    n = len(Eac)
    env = np.abs(Eac) ** 2
    env = env - env.mean()
    S = np.abs(np.fft.rfft(env * np.hanning(n)))
    df = prf / n
    if df <= 0 or len(S) < 4:
        return float("nan")

    #  ⭐ 합이 아니라 **로그 합**(= 조화적 곱) 이다. 단순 합은 부고조파를 못 막았다:
    #    f₀/2 를 후보로 놓으면 빈 자리 절반 + 참 고조파 절반인데, 참 고조파의 높은 차수가
    #    약하면 점수가 거의 같아진다(mini5pro 시행의 ~4% 가 90 Hz·570 Hz 로 샜다).
    #    로그 합은 **빈 자리 하나당 큰 벌점**을 물려 부고조파를 확실히 떨어뜨린다.
    ref = float(S.max()) + 1e-300
    logS = np.log(S / ref + 1e-3)

    def score(f0):
        f0 = np.atleast_1d(np.asarray(f0, float))
        idx = np.round(np.outer(f0, np.arange(1, n_harm + 1)) / df).astype(int)
        ok = (idx >= 1) & (idx < len(S))
        v = np.where(ok, logS[np.clip(idx, 0, len(S) - 1)], np.log(1e-3))
        return v.mean(1)

    coarse = np.arange(fmin, fmax, max(df / 3.0, 0.05))
    if len(coarse) == 0:
        return float("nan")

    def _refine(f0):
        fine = np.linspace(max(fmin, f0 - df), min(fmax, f0 + df), 81)
        j = int(np.argmax(score(fine)))
        return float(fine[j]), float(score(fine)[j])

    f_best, s_best = _refine(float(coarse[int(np.argmax(score(coarse)))]))
    #  ⭐ 옥타브 정정. 로그 합은 부고조파를 막았지만 이번엔 **배고조파로 샜다** —
    #    m=1 선이 널에 빠진 자세에서 2·f₀·3·f₀ 후보가 더 높은 점수를 받는다
    #    (실측: 전체 시행의 3.1% 가 100%·200% 오차). 아래로 나눠 보고 점수가
    #    MARGIN 안에서 버티면 **더 낮은 쪽**을 택한다. 빠진 선이 절반인 진짜
    #    부고조파는 벌점이 3 이상이라 MARGIN 1.5 를 못 넘는다.
    #    MARGIN 실측 (318 시행 · 잡음 없음 · 참값 대조):
    #      0.6·0.8·1.0 → 총오차(>5%) 0.00% ,  1.2 → 0.29% ,  1.5 → 1.17%
    #    평평한 구간 가운데를 잡는다. ⚠ 잡음이 있으면 이 여유는 다시 좁아진다.
    MARGIN = 0.8
    for k in (3.0, 2.0):
        if f_best / k >= fmin:
            fk, sk = _refine(f_best / k)
            if sk >= s_best - MARGIN:
                return fk
    return f_best


def features(E, prf):
    """복소 슬로타임 열 → 특징 벡터. 반환 (vec, aux)."""
    import numpy as np
    import md_mapstyle as ms

    E = np.asarray(E, complex)
    n = len(E)
    dc = E.mean()
    Eac = E - dc
    sd = float(np.sqrt((np.abs(Eac) ** 2).mean())) + 1e-300

    # ① 전체창 도플러 스펙트럼
    w = np.hanning(n)
    S = np.fft.fftshift(np.fft.fft(Eac * w))
    f = np.fft.fftshift(np.fft.fftfreq(n, 1.0 / prf))
    P = np.abs(S) ** 2
    P = P / (P.sum() + 1e-300)

    # ② 플래시율 — 포락선 전력의 고조파 합
    f_flash = flash_rate(Eac, prf)
    ff = f_flash if np.isfinite(f_flash) and f_flash > 0 else prf / 64.0

    # ③ ⭐ 플래시 고조파 빗살 — 도플러는 m·f_flash 에만 선다
    #    바닥(광선격자 각도잡음)을 기준선으로 삼아 그 위로 솟은 고조파만 센다.
    m_max = int(np.floor(0.95 * (prf / 2.0) / ff))
    m_use = int(min(M_CAP, max(1, m_max)))
    half = 0.20 * ff
    hp = np.zeros(m_use + 1)
    for m in range(1, m_use + 1):
        sel = np.abs(np.abs(f) - m * ff) <= half
        hp[m] = float(P[sel].sum())
    if m_use >= 18:
        floor = float(np.median(hp[16:m_use + 1]))
    else:
        floor = float(np.median(hp[max(1, m_use // 2 + 1):m_use + 1]))
    #  ⭐ 문턱 교차(m_edge) 대신 **연속 모멘트**를 쓴다 — 문턱은 정수로 양자화되고
    #    같은 기체의 시행끼리도 7↔8 로 튄다(2026-08-10 실측). 모멘트는 매끈하고,
    #    베셀 포락선의 폭이 곧 2kR 이므로 여전히 rpm 이 약분된다.
    #  ⚠ 모멘트는 m ≤ 18 에서만 센다. 그 위는 물리 성분이 없고(최대 2πR/λ = 14.0,
    #    s1000plus) 광선격자 잡음뿐인데, m 가 크면 모멘트에 m 배로 실려 꼬리가 답을 정한다
    #    (m ≤ 24 로 세면 같은 기체 안 변동계수가 0.22 → 0.34 로 나빠진다).
    m_mom = min(m_use, 18)
    hc = np.maximum(hp[1:m_mom + 1] - 3.0 * floor, 0.0)
    ms_ = np.arange(1, m_mom + 1, dtype=float)
    tot = hc.sum() + 1e-300
    m_cent = float((ms_ * hc).sum() / tot)
    m_rms = float(np.sqrt((ms_ ** 2 * hc).sum() / tot))
    f_edge = m_cent * ff
    hraw = np.maximum(hp[1:m_use + 1] - 3.0 * floor, 0.0)
    hs = (hraw[:N_HARM] if m_use >= N_HARM
          else np.concatenate([hraw, np.zeros(N_HARM - m_use)]))
    hfrac = (hs / (hs.sum() + 1e-300)).tolist()

    # ④ STFT — 하우스 규약(md_mapstyle). f_flash 는 **데이터에서 추정한 값**을 쓴다
    per = ms.auto_periods(prf, ff)
    fq, tt, Sxx, nper = ms.flash_spec(E - dc, prf, ff, periods=per)
    band = (np.abs(fq) >= 0.35 * max(f_edge, 1.0)) & (np.abs(fq) <= 1.10 * max(f_edge, 1.0))
    if band.sum() >= 1 and Sxx.shape[1] >= 8:
        tr = Sxx[band].mean(axis=0)
        trdb = 20 * np.log10(tr / (tr.max() + 1e-30) + 1e-12)
        flash_contrast = float(np.percentile(trdb, 95) - np.percentile(trdb, 5))
    else:
        flash_contrast = 0.0

    # ⑤ 비정상성 — 반창 스펙트럼 상관
    h = n // 2
    S1 = np.abs(np.fft.fft(Eac[:h] * np.hanning(h)))
    S2 = np.abs(np.fft.fft(Eac[h:2 * h] * np.hanning(h)))
    half_corr = float(np.corrcoef(S1, S2)[0, 1])

    # ⑥ 모양
    a = np.abs(Eac) / sd
    env_kurt = float(((a - a.mean()) ** 4).mean() / (a.var() ** 2 + 1e-30))
    pos, neg = P[f > 0].sum(), P[f < 0].sum()
    asym = float((pos - neg) / (pos + neg + 1e-300))

    # ⑦ 접은 주기 프로파일 — 한 플래시 주기 안의 **하위 플래시 구조**
    #    (로터마다 base_ang 이 달라 플래시가 엇갈린다 → 로터 수의 대리 지표)
    NB = 64
    if np.isfinite(f_flash) and f_flash > 0:
        ph = np.mod(np.arange(n) / prf * f_flash, 1.0)
        b = np.minimum((ph * NB).astype(int), NB - 1)
        prof = np.bincount(b, weights=np.abs(Eac) ** 2, minlength=NB)
        cnt = np.maximum(np.bincount(b, minlength=NB), 1)
        prof = prof / cnt
        prof = prof - prof.mean()
        H = np.abs(np.fft.rfft(prof))
        ref = float(np.sqrt((prof ** 2).mean())) + 1e-300
        fold = [float(H[m] / (NB * ref)) for m in range(1, 7)]
    else:
        fold = [0.0] * 6

    vec = ([f_flash, f_edge, m_cent, m_rms, 20 * np.log10(np.abs(dc) / sd + 1e-30),
            flash_contrast, env_kurt, half_corr, asym] + hfrac + fold)
    aux = dict(nper=int(nper), periods=float(per), m_use=int(m_use),
               floor_over_h1=float(floor / (hp[1] + 1e-300)))
    return np.asarray(vec, float), aux


def _draw_trials(rng, spec, n_rotors, jit=None):
    """시행 하나의 로터 상태를 뽑는다 — (로터별 rpm, 초기위상, base rpm, σ_s).

    jit=None 이면 **현행 그대로**다: σ_s 를 U(0.07 %, 0.29 %) 에서 뽑고 N(0,σ) 산포 +
    초기위상 U(0,180°). ⭐이 팔은 이미 초기위상을 무작위화하고 있었다.
    jit 를 주면 `rotor_dynamics` 의 프리셋 σ_s 를 쓴다(시간 흔들림은 여기가 아니라
    조건 루프에서 붙는다 — 창 길이·PRF 마다 열이 달라지기 때문이다).
    ⛔ jit=None 경로는 난수 소모 순서까지 현행과 같다(게이트 G6)."""
    base = float(spec.hover_rpm) * float(rng.uniform(1 - RPM_BASE_FRAC, 1 + RPM_BASE_FRAC))
    import numpy as np
    if jit is None:
        sig = float(rng.uniform(RPM_SPREAD_LO, RPM_SPREAD_HI))
        d = rng.normal(0.0, sig, n_rotors)
        d = d - d.mean()                  # 평균 rpm 은 base 로 유지
        return base * (1.0 + d), rng.uniform(0.0, PHASE_PERIOD_DEG, n_rotors), base, sig
    import rotor_dynamics as rd
    d = rd.static_offsets(n_rotors, jit, rng)
    p0 = rd.initial_phase_deg(n_rotors, jit, rng, period_deg=PHASE_PERIOD_DEG)
    return base * (1.0 + d), p0, base, float(jit.static_sigma)


def cmd_mergeverify(args):
    """샤드별 검증 결과를 합치고, ⭐**정확한 SBR 시계열 vs 표 합성**의 특징을 대조한다.

    이것이 위상표 근사의 최종 관문이다 — 오차를 «복소장이 얼마나 다른가» 가 아니라
    **«우리가 실제로 쓰는 특징이 얼마나 다른가»** 로 잰다."""
    import glob
    import numpy as np

    merged = {"_meta": {"script": "benchmark/md_classify_dataset.py mergeverify",
                        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "fc_hz": FC, "n_phase": N_PHASE},
              "periodicity": {}, "decomposition": {}, "grid_pinning": {},
              "exact_series": {}, "feature_fidelity": {}}
    for p in sorted(glob.glob(VERIFY_JSON.replace(".json", "_*.json"))):
        with open(p) as f:
            d = json.load(f)
        for sec in ("periodicity", "decomposition", "grid_pinning", "exact_series"):
            merged[sec].update(d.get(sec, {}))

    series = {}
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "md_classify_exact_series_*.npz"))):
        z = np.load(p, allow_pickle=True)
        for k in z.files:
            series[k] = z[k]

    #  ── 특징 충실도 ─────────────────────────────────────────────────────────
    for key in DRONE_KEYS:
        if f"{key}/E" not in series or key not in merged["exact_series"]:
            continue
        info = merged["exact_series"][key]
        ai, prf = int(info["aspect"]), float(info["prf_hz"])
        tp = os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz")
        if not os.path.exists(tp):
            continue
        z = np.load(tp, allow_pickle=True)
        fine = _fine_tables(z["dE"], z["phis"])
        Ex = np.asarray(series[f"{key}/E"])
        Et = synth(complex(z["E_ref"][0]), fine, np.asarray(z["dirs"], float),
                   np.asarray(series[f"{key}/rpms"], float),
                   np.asarray(series[f"{key}/p0"], float), prf, len(Ex))
        vx, _ = features(Ex, prf)
        vt, _ = features(Et, prf)
        ax_, at = Ex - Ex.mean(), Et - Et.mean()
        merged["feature_fidelity"][key] = {
            "n_t": int(len(Ex)), "prf_hz": prf, "aspect": ai,
            "series_rms_err_over_rms_ac": float(
                np.sqrt((np.abs(Et - Ex) ** 2).mean())
                / (np.sqrt((np.abs(ax_) ** 2).mean()) + 1e-30)),
            "series_ac_corr": float(np.abs(np.vdot(ax_, at))
                                    / (np.linalg.norm(ax_) * np.linalg.norm(at) + 1e-30)),
            "features": {n: {"exact": round(float(a), 4), "table": round(float(b), 4),
                             "abs_rel_diff": round(float(abs(b - a) / (abs(a) + 1e-9)), 4)}
                         for n, a, b in zip(FEATURE_NAMES, vx, vt)},
        }
        ff = merged["feature_fidelity"][key]["features"]
        print(f"{key:12s} AC상관 {merged['feature_fidelity'][key]['series_ac_corr']:.4f}  "
              f"f_flash {ff['f_flash_hat']['exact']:.1f}→{ff['f_flash_hat']['table']:.1f}  "
              f"m_cent {ff['m_cent']['exact']:.2f}→{ff['m_cent']['table']:.2f}", flush=True)

    #  ── ⭐ 물리 교차검사: 각도 고조파 포락선의 무릎이 2πR/λ 인가 ────────────
    #     로터 위상 φ 의 주기함수라 도플러는 m·f_flash 에만 서고, 마지막 고조파는
    #     m ≈ 2πR/λ 다(날개끝 위상 편이 2kR 의 베셀 전개). 표에서 직접 확인한다.
    #     ⚠ 격자를 안 박은 옛 표는 이 포락선이 단조롭지 않았다(−2.8·−16.0·−20.1·
    #       −18.0·−29.7·−14.8 dB 처럼 튀었다). 이 검사는 그것을 잡아낸다.
    from drones import DRONES as _DR
    lam = 299792458.0 / FC
    for key in DRONE_KEYS:
        fps = sorted(glob.glob(os.path.join(TAB_DIR, f"{key}_a*.npz")))
        if not fps:
            continue
        prof = []
        for p in fps:
            zz = np.load(p, allow_pickle=True)
            for k in range(zz["dE"].shape[0]):
                H = np.abs(np.fft.fft(zz["dE"][k]))
                prof.append(H[1:16] / (H[1:16].max() + 1e-300))
        P = (np.asarray(prof) ** 2).mean(0)
        P = P / (P.sum() + 1e-300)
        floor = float(np.median(P[11:]))          # m=12..15 는 물리 성분이 거의 없다
        Pc = np.maximum(P - 3.0 * floor, 0.0)
        cdf = np.cumsum(Pc) / (Pc.sum() + 1e-300)
        mm = np.arange(1, len(P) + 1, dtype=float)
        R = _DR[key].prop_dia_mm / 2000.0
        merged.setdefault("harmonic_envelope", {})[key] = {
            "profile_db_m1_to_m15": [round(float(x), 2)
                                     for x in 10 * np.log10(P / P.max() + 1e-30)],
            "m50": round(float(mm[int(np.searchsorted(cdf, 0.5))]), 2),
            "m90": round(float(mm[min(int(np.searchsorted(cdf, 0.9)), len(mm) - 1)]), 2),
            "m_centroid": round(float((mm * Pc).sum() / (Pc.sum() + 1e-300)), 3),
            "two_pi_R_over_lambda": round(float(2 * np.pi * R / lam), 2),
            "n_tables": len(fps),
        }
        e = merged["harmonic_envelope"][key]
        print(f"포락선 {key:12s} m90={e['m90']:5.1f}  m̄={e['m_centroid']:5.2f}  "
              f"2πR/λ={e['two_pi_R_over_lambda']:5.2f}", flush=True)

    he = merged.get("harmonic_envelope", {})
    ks = [k for k in he if not k.startswith("_")]
    if len(ks) >= 3:
        x = np.array([he[k]["two_pi_R_over_lambda"] for k in ks])
        corr = {stat: round(float(np.corrcoef(
            x, np.array([he[k][stat] for k in ks]))[0, 1]), 4)
            for stat in ("m50", "m90", "m_centroid")}
        he["_correlation_with_2piR_over_lambda"] = corr
        he["_note_ko"] = ("빗살 포락선의 폭이 프롭 반지름(파장 단위)을 따라가는가. "
                          "이 상관이 높다는 것이 «m̄ 은 rpm 이 아니라 기하를 읽는다» 의 근거다.")
        print(f"포락선 폭 ↔ 2πR/λ 상관: {corr}", flush=True)

    key_feats = ["f_flash_hat", "m_cent", "m_rms", "f_edge", "flash_contrast_db"]
    diffs = [merged["feature_fidelity"][k]["features"][fn]["abs_rel_diff"]
             for k in merged["feature_fidelity"] for fn in key_feats]
    merged["_meta"]["which_number_is_production_ko"] = (
        "⭐ 표 근사의 충실도는 **feature_fidelity** 를 봐라. decomposition 절은 보간을 "
        "np.interp(100점 선형)로 하므로 생산 경로(_fine_tables: 주기 큐빅 스플라인 → 4096점 "
        "격자)보다 거칠고, 그래서 오차를 과대평가한다. 생산 경로의 잔차는 대부분 위상표 "
        "보간이 아니라 SBR 광선격자의 각도 이산화 잡음(고조파 바닥 −36 dB)이고, 그 잡음은 "
        "특징을 거의 움직이지 않는다(핵심 특징 상대차 중앙값 0.008).")
    merged["_meta"]["headline_ko"] = (
        f"위상표 합성 vs 정확 SBR: 핵심 특징 {len(key_feats)}개 × 기체 "
        f"{len(merged['feature_fidelity'])}종의 상대차 중앙값 "
        f"{float(np.median(diffs)) if diffs else float('nan'):.3f}")
    if series:
        np.savez_compressed(os.path.join(OUT_DIR, "md_classify_exact_series.npz"), **series)
    with open(VERIFY_JSON, "w") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1, default=float)
    print(f"✅ {VERIFY_JSON}")
    print(f"   {merged['_meta']['headline_ko']}")


def cmd_build(args):
    import numpy as np
    from drones import DRONES
    import microdoppler_nearfield as nf          # ⭐ 잡음 주입은 공용 헬퍼 하나만 쓴다
    import rotor_dynamics as rd                  # ⭐ 로터 랜덤성도 공용 커널 하나만 쓴다

    #  ⭐ 로터 랜덤성 — **opt-in**. 기본(빈 문자열)이면 난수 소모 순서까지 현행 그대로다.
    #     ⚠ 프리셋을 주면 산출 이름에 접미사가 붙는다 — 기존 원장을 덮지 않는다.
    preset = str(getattr(args, "rotor_preset", "") or "")
    jit = rd.get(preset) if preset else None
    tag = getattr(args, "tag", "") or ("" if not preset else f"_{preset}")
    feat_npz = FEAT_NPZ if not tag else FEAT_NPZ.replace(".npz", f"{tag}.npz")
    if preset and os.path.exists(feat_npz) and not getattr(args, "overwrite", False):
        raise SystemExit(f"⛔ 이미 있다: {feat_npz} — --tag 나 --overwrite 를 써라.")
    rot_seed0 = int(getattr(args, "rotor_seed", SEED))

    rng = np.random.default_rng(SEED)
    rows, meta_rows = [], []
    tabs = {}
    missing = []
    for key in DRONE_KEYS:
        for ai in range(len(ASPECTS)):
            p = os.path.join(TAB_DIR, f"{key}_a{ai:02d}.npz")
            if not os.path.exists(p):
                missing.append(f"{key}/a{ai:02d}")
                continue
            z = np.load(p, allow_pickle=True)
            tabs[(key, ai)] = (complex(z["E_ref"][0]),
                               _fine_tables(z["dE"], z["phis"]),
                               np.asarray(z["dirs"], float))
    print(f"표 {len(tabs)} 개 적재, 결측 {len(missing)}", flush=True)

    conds = []
    for prf in PRF_SWEEP:
        conds.append(("prf", prf, T_MAIN, 1e9))
    for T in T_SWEEP:
        conds.append(("T", PRF_MAIN, T, 1e9))
    for s in SNR_SWEEP_DB:
        conds.append(("snr", PRF_MAIN, T_MAIN, s))
    seen, uniq = set(), []
    for c in conds:
        k = c[1:]
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    print(f"조건 {len(uniq)} 개: {[(c[1], c[2], c[3]) for c in uniq]}", flush=True)

    ex_series = {}
    t0 = time.time()
    for key in DRONE_KEYS:
        spec = DRONES[key]
        for ai in range(len(ASPECTS)):
            if (key, ai) not in tabs:
                continue
            E_ref, fine, dirs = tabs[(key, ai)]
            az, el = ASPECTS[ai]
            for di in range(N_DRAW_PER_ASPECT):
                rpms, p0, base, sig = _draw_trials(rng, spec, len(dirs), jit)
                nz_seed = int(rng.integers(0, 2 ** 31 - 1))
                #  ⭐ 흔들림 시드는 시행마다 하나. 조건(PRF·창)이 달라도 **같은 물리 실현**을
                #     쓰도록 성근 격자(200 Hz)에서 만든다 — 스윕 비교가 성립한다.
                rot_seed = (int(rng.integers(0, 2 ** 31 - 1))
                            if (jit is not None and jit.wobble_sigma > 0) else None)
                for cond_tag, prf, T, snr_db in uniq:
                    n_t = int(round(prf * T))
                    rp = rpms
                    if rot_seed is not None:
                        rp, _ = rd.rpm_series(base, len(dirs), n_t, prf,
                                              jit.with_(static_sigma=0.0),
                                              np.random.default_rng(rot_seed))
                        rp = rp + (rpms - base)[None, :]      # 정적 산포는 그대로 얹는다
                    E = synth(E_ref, fine, dirs, rp, p0, prf, n_t)
                    #  ⭐⭐ SNR 규약 v2 (2026-08-10): 이 팔의 눈금은 **AC 기준**
                    #     (③′ snr_slow_ac_db — 블레이드선 전력 대 잡음). 예전에는 같은 식이
                    #     여기 인라인으로 있었고 `microdoppler_nearfield.add_noise()` 는
                    #     **총전력** 기준이라, 두 실험의 SNR 축이 기체별 17.3~37.2 dB
                    #     어긋난 채 같은 표에 놓였다. 이제 둘 다 같은 헬퍼를 거치고
                    #     `ref` 로 눈금을 선언한다(게이트: benchmark/verify_snr_convention.py SC3).
                    #     ⭐ dc_ac 를 함께 적어 두면 총전력 눈금(③)으로 언제든 되돌릴 수 있다:
                    #        snr_slow_db = snr_db + 10log10(1 + 10^(dc_ac_db/10))
                    dc_ac = float(20.0 * np.log10(max(abs(E.mean()), 1e-300)
                                                  / max(float(np.std(E)), 1e-300)))
                    if np.isfinite(snr_db) and snr_db < 500:
                        r = np.random.default_rng(nz_seed)
                        E, _sn = nf.add_noise(E, snr_db, r, ref="ac")
                    v, aux = features(E, prf)
                    rows.append(v)
                    meta_rows.append((key, ai, az, el, di, prf, T, snr_db, base, sig,
                                      len(dirs), spec.prop_dia_mm, spec.prop_blades, dc_ac))
                    if (di == 0 and prf == PRF_MAIN and T == T_MAIN
                            and snr_db > 500 and ai in (1, 7, 13)):
                        ex_series[f"{key}/a{ai:02d}"] = E.astype(np.complex64)
        print(f"  {key} 누적 {len(rows)} 행 ({time.time()-t0:.0f}s)", flush=True)

    X = np.asarray(rows, float)
    np.savez_compressed(
        feat_npz, X=X, feature_names=np.array(FEATURE_NAMES),
        drone=np.array([r[0] for r in meta_rows]),
        aspect=np.array([r[1] for r in meta_rows], int),
        az=np.array([r[2] for r in meta_rows], float),
        el=np.array([r[3] for r in meta_rows], float),
        draw=np.array([r[4] for r in meta_rows], int),
        prf=np.array([r[5] for r in meta_rows], float),
        Twin=np.array([r[6] for r in meta_rows], float),
        snr_db=np.array([r[7] for r in meta_rows], float),
        base_rpm=np.array([r[8] for r in meta_rows], float),
        rpm_sigma=np.array([r[9] for r in meta_rows], float),
        n_rotors=np.array([r[10] for r in meta_rows], int),
        prop_dia_mm=np.array([r[11] for r in meta_rows], float),
        blades=np.array([r[12] for r in meta_rows], int),
        #  ⭐ 규약 v2: 어느 눈금인지 원장 자신이 말한다. dc_ac_db 가 있으면 AC↔총전력 변환이 된다.
        dc_ac_db=np.array([r[13] for r in meta_rows], float),
        snr_convention=nf.SNR_CONVENTION, snr_reference="ac",
        snr_rung=nf.CANONICAL_SNR_KEY, capture="full_waveform",
        snr_note=("snr_db is AC-referenced (blade line only): p_sig = mean|E-mean(E)|^2. "
                  "To convert to the TOTAL-power rung used by experiment_md_range: "
                  "snr_slow_db = snr_db + 10*log10(1 + 10**(dc_ac_db/10)). "
                  "See outputs/snr_convention.json"),
        group_rate=np.array(G_RATE), group_abs=np.array(G_ABS), group_free=np.array(G_FREE),
        prf_main=PRF_MAIN, t_main=T_MAIN, n_aspects=len(ASPECTS),
        missing_tables=np.array(missing),
        #  ⭐ 로터 랜덤성 규약 — 원장 자신이 어느 모델로 만들어졌는지 말한다.
        #     빈 문자열이면 «현행»(σ_s ~ U(0.07,0.29 %) · 흔들림 없음 · 초기위상 U(0,180°)).
        rotor_preset=preset, rotor_seed=rot_seed0,
        rotor_jitter=json.dumps(jit.asjson(), ensure_ascii=False) if jit else "",
        rotor_note=("rotor_preset='' means the historical model: per-trial sigma_s ~ "
                    "U(0.0007,0.0029), NO time-varying wobble, initial phase U(0,180 deg). "
                    "A named preset uses src/rotor_dynamics.py (Gaussian spread + OU wobble). "
                    "See docs/NOISE_AND_ROTOR_PLAN.md section 2."),
        **{f"ex/{k}": v for k, v in ex_series.items()})
    print(f"✅ {feat_npz}  X={X.shape}  ({os.path.getsize(feat_npz)/1e6:.1f} MB)"
          f"  로터 «{preset or '현행'}»")
    print(f"   NaN 행 {int(np.isnan(X).any(axis=1).sum())}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("tables"); a.set_defaults(fn=cmd_tables)
    a.add_argument("--shard", type=int, default=0)
    a.add_argument("--nshards", type=int, default=1)
    a.add_argument("--gpu", default="3")
    a.add_argument("--force", action="store_true")
    b = sub.add_parser("verify"); b.set_defaults(fn=cmd_verify)
    b.add_argument("--gpu", default="3")
    b.add_argument("--n-check", type=int, default=24)
    b.add_argument("--series-aspect", type=int, default=7)
    b.add_argument("--series-prf", type=float, default=6000.0)
    b.add_argument("--series-n", type=int, default=1024)
    b.add_argument("--drones", default=",".join(DRONE_KEYS))
    b.add_argument("--tag", default="")
    d = sub.add_parser("mergeverify"); d.set_defaults(fn=cmd_mergeverify)
    c = sub.add_parser("build"); c.set_defaults(fn=cmd_build)
    #  ⭐ 로터 랜덤성 — opt-in. 기본(빈 문자열)이면 현행과 비트동일이다.
    c.add_argument("--rotor-preset", default="",
                   help="src/rotor_dynamics.PRESETS 이름(legacy/sitl/indoor/outdoor/lit_iid/"
                        "⭐outdoor_v2/outdoor_v2_eff). 기본 '' = 현행 모델 그대로(비트동일)")
    c.add_argument("--rotor-seed", type=int, default=SEED)
    c.add_argument("--tag", default="", help="산출 접미사(기본: 프리셋명)")
    c.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
