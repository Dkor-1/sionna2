# -*- coding: utf-8 -*-
"""
report15b_microdoppler_recompute.py — **마이크로도플러 재계산** (2026-08-07)
===========================================================================
앞선 report15 의 마이크로도플러에는 세 가지 한계가 있었다. 셋 다 이 라운드에서 푼다.

  ① **네 로터가 위상 하나를 공유했다** (`microdoppler.py:158`).
     그래서 신호가 φ 의 완전한 주기함수가 되고 **스펙트로그램이 시간에 안 변한다.**
     실제 기체는 모터마다 제어 루프가 따로 돌아 rpm 이 몇 % 씩 다르다.
  ② **도플러 분해능이 거칠었다.** 분해능 = f_flash / (창에 든 주기 수) 라
     표본을 늘려도 안 좋아진다 — **창을 늘려야** 좋아진다.
  ③ **헤드라인이 가림 없는 PO 로 계산됐다.** `report15_verdict_po_grid.py` 가
     `microdoppler_nearfield`(가림 없음, 그건 근거리장 A/B 를 위한 의도된 설계)를 썼다.
     가림이 들어간 엔진(`microdoppler_sbr`)은 있었는데 헤드라인이 안 썼다.

무엇을 가능하게 했나
---------------------
`src/articulated_fast.py` — 드론을 한 번 짓고 위상마다 행렬곱만 한다.
실측 **20,000 배**(1,631 ms → 0.08 ms), 정점 차이 0.00e+00 (비트 동일).
⭐ 설계 출처는 선배(홍지혁) `po_mdoppler/po_sim/mesh.py` 다.
조립이 싸지니 «위상 하나짜리 표» 트릭이 필요 없어지고, 로터별 rpm 이 가능해졌다.

실험 팔
--------
  A  sbr_locked    SBR(가림 O) · 네 로터 같은 rpm, 위상 동기   ← 옛 가정
  B  sbr_spread    SBR(가림 O) · ⭐로터별 rpm 흩어짐            ← 현실
  E  sbr_nobody    SBR · 동체를 씬에서 뺌 · 흩어짐              ← 가릴 것이 없다
  C  po_locked     평면파 PO(가림 X) · 같은 rpm
  D  po_spread     평면파 PO(가림 X) · 흩어짐

  ⭐ **B ↔ E 가 이 실험의 핵심**이다. 광선 엔진·재질·기하·운동학이 전부 같고
     **오직 동체의 존재 여부만 다르다** → 차이는 «동체가 블레이드를 가린다» 하나로 귀속된다.
     (선배 코드의 `body_block_mask` 와 같은 축이다.)
  ⚠ A ↔ C 는 가림 말고 다중반사·표본화도 함께 달라진다. 단일축 ablation 이 아니다.

  ⚠ E 는 동체 산란이 통째로 빠지므로 레벨이 다르다. 그래서 판정은 레벨이 아니라
     **변조 깊이·조화 구조** 로 한다(각 팔을 자기 평균으로 정규화한 뒤 비교).

산출
-----
  outputs/report15b_microdoppler.json     수치·판정
  outputs/report15b_series.npz            슬로타임 복소열 (그림 스크립트가 읽는다)

  python benchmark/report15b_microdoppler_recompute.py [--quick]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")          # ⭐사용자 지시: 2번이 비어 있다

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from gpu import pick                                                   # noqa: E402
pick(verbose=True)                                                     # ⚠ mitsuba import 전에

import numpy as np                                                     # noqa: E402
from articulated_fast import FastPoser, rotor_phases                   # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, rotor_layout               # noqa: E402
from rcs_po import C0                                                  # noqa: E402
from rcs_sbr import sbr_field                                          # noqa: E402
from microdoppler import microdoppler_series                           # noqa: E402

OUT_JSON = os.path.join(ROOT, "outputs", "report15b_microdoppler.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report15b_series.npz")

FC = 3.5e9
DRONE_KEYS = ["matrice4e", "mini5pro"]

# ⭐ 자세 선택 — 2026-08-07 에 바꾼 이유
#   옛 헤드라인은 el=+15 만 봤다. 그 자세에서 동체가 프롭을 가리는 양은 **0.00 dB** 다
#   (프롭이 동체 위에 있으니 위에서 보면 가릴 것이 없다). 그래서 «가림이 안 중요하다» 로
#   보였던 것이고, 그건 물리가 아니라 **자세 선택의 결과**였다.
#   ⚠ 지상 레이더는 비행 중인 드론을 **아래에서** 본다 — 기체 좌표계로 el < 0 이다.
#   실측 스윕(2026-08-07, penetrate=False, 위상 6개 중 최악):
#       matrice4e  el=+60 → 0.00 dB · el=−15,az=0  → **−15.96 dB**
#       mini5pro   el=  0 → 0.00 dB · el=−15,az=90 → **−11.22 dB**
ASPECTS = {
    "nose": (0.0, 15.0),        # 옛 헤드라인 자세 — 이어서 볼 수 있게 남긴다
    "belly": (0.0, -15.0),      # ⭐지상 레이더가 실제로 보는 쪽. matrice4e 최악
    "belly_side": (90.0, -15.0),  # ⭐mini5pro 최악
}

# ⚠ 흩어짐 폭은 **선언된 가정**이다 — 우리에게 실측 로그가 아직 없다.
#   선배가 준 PX4 SITL 로그는 모터간 산포가 0.07~0.29 % 뿐이라(내가 쟀다) 이 질문에 못 쓴다.
#   실제 정지비행에서는 무게중심 치우침과 요 토크 균형 때문에 로터마다 추력이 다르고,
#   그만큼 rpm 이 갈린다. 여기서는 ±2 % 를 쓰고, 그 사실을 산출물에 적는다.
# ⭐ 2026-08-10 정정 — ±2 % 는 내 추측이었고 과했다(사용자 지적).
#   선배(홍지혁) PX4 텔레메트리 실측: 모터 간 산포 **0.07~0.29 %**. 중간값을 쓴다.
#   ±2 % 를 쓰면 네 로터의 빗살이 고조파마다 어긋나 맵이 뭉개진다.
RPM_SPREAD_FRAC = 0.0022
RPM_SPREAD_PATTERN = np.array([+1.0, -1.0, -0.55, +0.55])   # 대각쌍이 반대로 (요 균형)

N_FLASH_PERIODS = 64          # ⭐창에 든 블레이드 주기 수 = 도플러 분해능을 정하는 유일한 값
PRF_OVER_FTIP = 4.0           # PRF = 이 배수 × f_tip (나이키스트 2배 + 여유)
MAX_SAMPLES = 6000            # 안전 상한


def _phys(spec, el_deg):
    """이 기체·자세의 운동학 — 여기서 창 길이와 PRF 가 결정된다."""
    rpm = float(getattr(spec, "hover_rpm", 6000.0))
    lam = C0 / FC
    omega = 2 * np.pi * rpm / 60.0
    R = spec.prop_dia_mm / 1000.0 / 2.0
    f_rev = rpm / 60.0
    f_flash = spec.prop_blades * f_rev
    f_tip = 2.0 * (omega * R) / lam * np.cos(np.radians(el_deg))
    prf = float(np.ceil(PRF_OVER_FTIP * f_tip / 100.0) * 100.0)
    dur = N_FLASH_PERIODS / f_flash
    n_t = int(min(MAX_SAMPLES, round(prf * dur)))
    return dict(rpm=rpm, lam=lam, v_tip=omega * R, prop_R=R, f_rev=f_rev,
                f_flash=f_flash, f_tip=f_tip, prf=prf, duration_s=dur, n_t=n_t,
                doppler_resolution_hz=f_flash / N_FLASH_PERIODS,
                bins_to_ftip=f_tip / (f_flash / N_FLASH_PERIODS))


def _rpms(spec, spread):
    n = spec.num_rotors
    base = float(getattr(spec, "hover_rpm", 6000.0))
    pat = np.resize(RPM_SPREAD_PATTERN, n)
    return base * (1.0 + spread * pat)


_GMAT_FULL = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
# 동체를 **완전흡수(Γ=0)** 로 — 광선은 막되 산란은 안 한다. 프롭만 신호가 된다.
_GMAT_BODY_BLACK = {g: (m if g == "prop" else 0.0)
                    for g, (m, _) in DRONE_GROUP_MAT.items()}


def _sbr_series(spec, u, rpms, phys, mode="full"):
    """슬로타임 복소열 E(t) — 시간표본마다 자세를 새로 만들고 광선을 쏜다.

    mode
      "full"       전체 드론, 운영 설정(penetrate=True). 현실 신호.
      "blade_occ"  동체 Γ=0 → **막되 산란 안 함**. penetrate=False 라 첫 충돌이 최종.
                   = 블레이드 신호 + 동체에 의한 가림.
      "blade_free" 동체 **면**을 뺀다. 정점 배열은 그대로 둬서 bbox·광선격자가 같다.
                   = 블레이드 신호, 가릴 것 없음.

    ⭐ blade_occ ↔ blade_free 가 이 실험의 단일축이다 — 광선 엔진·재질·기하·운동학·
      **광선 격자까지** 같고 오직 «동체가 막느냐» 만 다르다.
    ⚠ 정점을 그대로 둔 것이 중요하다. `_mi_scene_from_mesh` 는 면이 참조하는 정점만
      쓰므로 씬은 프롭뿐이지만, `sbr_field` 의 bbox 는 `mesh.v` 전체로 잡혀 두 팔의
      광선 수·간격이 같아진다. 안 그러면 «가림» 과 «표본화» 가 섞인다.
    """
    fp = FastPoser(spec)
    t = np.arange(phys["n_t"]) / phys["prf"]
    ph = rotor_phases(t, rpms, fp.dirs)                    # (n_t, n_rotors)

    gmat = _GMAT_FULL if mode == "full" else (
        _GMAT_BODY_BLACK if mode == "blade_occ" else _GMAT_FULL)
    penetrate = (mode == "full")
    prop_only = (mode == "blade_free")
    if prop_only:
        keep = np.asarray(fp.g) == "prop"
        f_keep, g_keep = fp.f[keep], fp.g[keep]

    E = np.zeros(phys["n_t"], complex)
    t0 = time.time()
    for i in range(phys["n_t"]):
        mv = fp.pose(ph[i])
        if prop_only:
            mv.f, mv.g = f_keep, g_keep                    # 정점(mv.v)은 그대로 — bbox 보존
        E[i] = sbr_field(mv, gmat, FC, u, penetrate=penetrate)
        if i and i % 1000 == 0:
            el = time.time() - t0
            print(f"      {i}/{phys['n_t']}  {el:.0f}s  "
                  f"ETA {(phys['n_t']-i)/i*el/60:.1f}분", flush=True)
    return t, E, time.time() - t0


def _po_series(spec, az, el, rpms, phys):
    """가림 없는 평면파 PO. `microdoppler_series` 가 **로터별 rpm 을 직접** 받는다
    (2026-08-07 에 그 인자를 넣었다). 합성이나 근사가 없다 — 로터 j 가 rpm_j 로 돈다."""
    t, E, _ = microdoppler_series(spec, fc=FC, az=az, el=el,
                                  prf=phys["prf"], n_t=phys["n_t"],
                                  rpm_per_rotor=np.asarray(rpms, float))
    return t, E


def _analyse(E, phys):
    """변조 깊이 · 조화 스펙트럼 · 시간 변동성."""
    E = np.asarray(E)
    a = np.abs(E)
    db = 20 * np.log10(np.maximum(a, 1e-30))
    ac = E - E.mean()

    # 조화 스펙트럼 (전체 창)
    W = np.hanning(len(ac))
    S = np.fft.fftshift(np.fft.fft(ac * W))
    f = np.fft.fftshift(np.fft.fftfreq(len(ac), 1.0 / phys["prf"]))
    P = np.abs(S)
    P = P / (P.max() + 1e-30)

    # 스펙트로그램이 시간에 따라 변하나 — 창을 반으로 나눠 상관을 본다
    h = len(ac) // 2
    S1 = np.abs(np.fft.fft(ac[:h] * np.hanning(h)))
    S2 = np.abs(np.fft.fft(ac[h:2 * h] * np.hanning(h)))
    half_corr = float(np.corrcoef(S1, S2)[0, 1])

    # 팁 주파수 안/밖 에너지
    inside = np.abs(f) <= phys["f_tip"]
    return dict(
        level_db=float(db.mean()),
        modulation_ptp_db=float(db.max() - db.min()),
        modulation_std_db=float(db.std()),
        dc_over_ac=float(np.abs(E.mean()) / (np.std(ac) + 1e-30)),
        half_window_spectrum_corr=half_corr,
        energy_inside_ftip_frac=float((P[inside] ** 2).sum() / ((P ** 2).sum() + 1e-30)),
        spectrum_f_hz=f, spectrum_db=20 * np.log10(P + 1e-12),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="주기 수를 8 로 줄여 빠르게")
    ap.add_argument("--aspects", default="nose,side")
    ap.add_argument("--drones", default=",".join(DRONE_KEYS))
    args = ap.parse_args()

    global N_FLASH_PERIODS
    if args.quick:
        N_FLASH_PERIODS = 8

    aspects = [a for a in args.aspects.split(",") if a in ASPECTS]
    keys = [k for k in args.drones.split(",") if k in DRONES]

    res = {"_meta": {
        "script": "benchmark/report15b_microdoppler_recompute.py",
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fc_hz": FC, "gpu": os.environ.get("SIONNA2_GPU"),
        "n_flash_periods": N_FLASH_PERIODS, "prf_over_ftip": PRF_OVER_FTIP,
        "rpm_spread_frac": RPM_SPREAD_FRAC,
        "rpm_spread_pattern": RPM_SPREAD_PATTERN.tolist(),
        "what_fixed_ko": [
            "① 로터별 rpm — 옛 코드는 네 로터가 위상 하나를 공유했다(microdoppler.py:158)",
            "② 도플러 분해능 — 분해능은 f_flash/(창의 주기 수)라 창을 늘려야 좋아진다",
            "③ 가림 — 헤드라인이 가림 없는 PO 를 썼다. 여기서는 SBR(가림 O) 로 다시 잰다",
        ],
        "enabled_by_ko": "src/articulated_fast.py (20,000배, 정점차 0.00e+00). "
                         "설계 출처는 선배 po_mdoppler/po_sim/mesh.py.",
        "spread_is_declared_ko": (
            f"±{RPM_SPREAD_FRAC*100:.2f}% 는 선배 PX4 텔레메트리 실측(0.07~0.29%)의 중간값이다. "
            "우리 표적(Matrice 4E) 실측 로그가 오면 그 값으로 바꾼다."),
        "clean_axis_ko": "B↔E 가 단일축(동체 유무)이다. A↔C 는 가림 외에 엔진도 달라 단일축이 아니다.",
    }, "cells": {}}
    series = {}

    for key in keys:
        spec = DRONES[key]
        for asp in aspects:
            az, el = ASPECTS[asp]
            phys = _phys(spec, el)
            u = np.array([np.cos(np.radians(el)) * np.cos(np.radians(az)),
                          np.cos(np.radians(el)) * np.sin(np.radians(az)),
                          np.sin(np.radians(el))])
            rl = rotor_layout(spec)
            r_lock = np.full(len(rl), float(getattr(spec, "hover_rpm", 6000.0)))
            r_sprd = _rpms(spec, RPM_SPREAD_FRAC)

            print(f"\n═══ {spec.name} · {asp} (az {az:.0f}, el {el:.0f}) ═══", flush=True)
            print(f"   rpm {phys['rpm']:.0f} · f_flash {phys['f_flash']:.1f} Hz · "
                  f"f_tip {phys['f_tip']:.0f} Hz · PRF {phys['prf']:.0f} Hz", flush=True)
            print(f"   창 {phys['duration_s']*1e3:.0f} ms = {N_FLASH_PERIODS} 주기 · "
                  f"표본 {phys['n_t']} · ⭐분해능 {phys['doppler_resolution_hz']:.2f} Hz "
                  f"({phys['bins_to_ftip']:.0f} 빈/f_tip)", flush=True)
            print(f"   로터별 rpm(흩어짐) {np.round(r_sprd,1).tolist()}", flush=True)

            cell = {"drone": key, "name": spec.name, "aspect": asp,
                    "az_deg": az, "el_deg": el, "physics": {
                        k: v for k, v in phys.items() if not isinstance(v, np.ndarray)},
                    "rpm_locked": r_lock.tolist(), "rpm_spread": r_sprd.tolist(),
                    "arms": {}}

            arms = [("A_sbr_locked", "sbr", r_lock, "full"),
                    ("B_sbr_spread", "sbr", r_sprd, "full"),
                    ("F_blade_occ", "sbr", r_sprd, "blade_occ"),
                    ("G_blade_free", "sbr", r_sprd, "blade_free"),
                    ("C_po_locked", "po", r_lock, None),
                    ("D_po_spread", "po", r_sprd, None)]

            for name, eng, rpms, mode in arms:
                t0 = time.time()
                if eng == "sbr":
                    t, E, secs = _sbr_series(spec, u, rpms, phys, mode=mode)
                else:
                    t, E = _po_series(spec, az, el, rpms, phys)
                    secs = time.time() - t0
                an = _analyse(E, phys)
                spec_f = an.pop("spectrum_f_hz")
                spec_db = an.pop("spectrum_db")
                an["seconds"] = round(secs, 1)
                cell["arms"][name] = an
                series[f"{key}/{asp}/{name}/E"] = E
                series[f"{key}/{asp}/{name}/spec_db"] = spec_db
                series[f"{key}/{asp}/{name}/spec_f"] = spec_f
                print(f"   {name:14s} {secs:6.1f}s  ptp {an['modulation_ptp_db']:6.2f} dB  "
                      f"반창상관 {an['half_window_spectrum_corr']:.4f}  "
                      f"DC/AC {an['dc_over_ac']:8.2f}", flush=True)

            # ── 판정 ──────────────────────────────────────────────────────
            A, B, F, G, C, D = (cell["arms"][k] for k in
                                ("A_sbr_locked", "B_sbr_spread", "F_blade_occ",
                                 "G_blade_free", "C_po_locked", "D_po_spread"))
            cell["findings"] = {
                "occlusion_level_db": round(F["level_db"] - G["level_db"], 3),
                "occlusion_ptp_db": round(F["modulation_ptp_db"]
                                          - G["modulation_ptp_db"], 3),
                "occlusion_axis_ko": (
                    "F−G: 광선 엔진·재질·기하·운동학·**광선 격자**까지 같고 "
                    "오직 «동체가 막느냐» 만 다르다. 단일축이다."),
                "occlusion_sign_note_ko": (
                    "⚠ 합이 코히런트라 가림이 레벨을 **올릴 수도** 있다 — 항이 줄어도 "
                    "남은 항끼리 상쇄가 덜 되면 그렇다. 부호를 물리로 단정하지 말 것."),
                "rpm_spread_makes_it_time_varying": {
                    "locked_half_corr": round(A["half_window_spectrum_corr"], 4),
                    "spread_half_corr": round(B["half_window_spectrum_corr"], 4),
                    "drop": round(A["half_window_spectrum_corr"]
                                  - B["half_window_spectrum_corr"], 4),
                    "note_ko": "잠긴 rpm 은 신호가 완전 주기라 반창 스펙트럼 상관이 1 이어야 한다. "
                               "흩어지면 내려간다 — 그 내려감이 «시간에 따라 변한다» 의 정량이다.",
                },
                "engine_ptp_db": round(B["modulation_ptp_db"] - D["modulation_ptp_db"], 3),
                "engine_axis_caveat_ko": "B−D 는 가림 말고 다중반사·투과·표본화도 함께 다르다. 단일축 아님",
            }
            res["cells"][f"{key}/{asp}"] = cell

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    np.savez_compressed(OUT_NPZ, **series)
    with open(OUT_JSON, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=float)
    print(f"\n✅ {OUT_JSON}")
    print(f"✅ {OUT_NPZ}  ({os.path.getsize(OUT_NPZ)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
