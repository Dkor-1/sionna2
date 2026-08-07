# -*- coding: utf-8 -*-
"""
report15_verdict_po_grid.py — **우리 PO 커널을 Sionna 격자와 같은 칸에서 돌린다**
================================================================================

왜 필요한가
  판정 항목 4 는 "Sionna 와 PO 가 **어디서** 갈리나 — 거리·자세별로. 근거리에서 좁혀지는가"다.
  기존 outputs/report15_po_control.json 은 **R=3 m 한 거리, 자세 2개**(ref·hot)뿐이라
  거리 의존을 볼 수 없다. 여기서 Sionna 격자와 **정확히 같은** (거리 3 × 자세 5) 칸을 채운다.

⭐ 격자 정합
  Sionna 격자: 한 주기 180° 를 64 등분 (φ = 0, 2.8125, …, 177.1875°)
  PO 격자    : 한 바퀴 360° 를 128 등분 → **앞 64 점이 Sionna 와 같은 φ**. 정합을 코드가 검증한다.
  기하       : TX/RX 를 Sionna place() 와 같은 좌표에 놓는다(준-모노스태틱 baseline 0.2 m).

⚠ PO 커널은 **가림이 없다**(설계). SBR 이 가림 있는 팔이지만 평면파·모노스태틱이라
  완전한 대조가 아니다 — 기존 JSON 의 관측(PO 가 Sionna 와 더 잘 맞는다)을 여기서 거리축으로 넓힌다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만. 기존 산출물 덮어쓰기 금지(신규 파일 하나).
⛔ 숫자 손입력 금지. GPU 안 씀(순수 numpy) — Sionna 격자가 GPU 를 쓰는 동안 병행 가능.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  ⭐ mitsuba 를 부르지 않는 모듈만 쓴다 — GPU 컨텍스트를 새로 만들지 않기 위해서다.
import microdoppler_nearfield as mnf                                   # noqa: E402
from drones import DRONES                                              # noqa: E402

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
BASELINE_M = 0.20

RANGES = (1.0, 3.0, 10.0)
ASPECTS = (("nose", 0.0, 15.0), ("oblique", 45.0, 15.0), ("side", 90.0, 15.0),
           ("hot", 0.0, 0.0), ("disc", 0.0, 75.0))
N_PHASE = 128            # 360° 128 등분 → 앞 64 점이 Sionna 의 180°/64 와 동일
N_PHASE_FINE = 512       # 스펙트럼 꼬리(빗이 어디까지 뻗나)를 보기 위한 세밀 격자
KEYS = ("mini2", "matrice4e")

#  Sionna 가 본 메쉬와 **같은 프로펠러 분할**(build_propeller n=10) — po_control 의 PO_MATCHED
PO_MATCHED = dict(blade_n=10, blade_div=11.0, frame_div=6.0)
#  이산화를 바꿔도 결과가 유지되는지 보는 정밀 점구름 — po_control 의 PO_REFINED
PO_REFINED = dict(blade_n=26, blade_div=22.0, frame_div=12.0)

OUT_JSON = os.path.join(ROOT, "outputs", "report15_verdict_po_grid.json")


# --------------------------------------------------------------------------- #
#  기하 — Sionna place() 와 **한 글자도 다르지 않게**
# --------------------------------------------------------------------------- #
def look_dir(az_deg, el_deg):
    a, e = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])


def basis_perp(u):
    t = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = np.cross(u, t); e1 /= np.linalg.norm(e1)
    return e1, np.cross(u, e1)


def antennas(az, el, rng, baseline=BASELINE_M):
    u = look_dir(az, el)
    e1, _ = basis_perp(u)
    return rng * u + 0.5 * baseline * e1, rng * u - 0.5 * baseline * e1


def sph_from_xyz(p):
    p = np.asarray(p, float)
    r = float(np.linalg.norm(p))
    return r, float(np.degrees(np.arctan2(p[1], p[0]))), float(np.degrees(np.arcsin(p[2] / r)))


def _frame_field(spec, A_t, A_s, R_t, R_s, disc):
    """비회전(프레임) 항 — E_prop = E_all − E_frame 의 해석적 분리에 쓴다."""
    k = 2.0 * np.pi / LAM
    (Pf, Nf, wf), _, _ = mnf._build_clouds(spec, LAM, disc["frame_div"],
                                           disc["blade_div"], disc["blade_n"])
    return complex(mnf._field_spherical(Pf, Nf, wf, k, A_t, A_s, R_t, R_s)), int(len(wf))


def arm_po(spec, az, el, rng, *, n_phase, disc, baseline=BASELINE_M):
    """구면파 · 실제 TX/RX 좌표(=Sionna 기하) · 가림 없음. → (phis, E_all, E_prop, info)"""
    tx, rx = antennas(az, el, rng, baseline)
    r_t, az_t, el_t = sph_from_xyz(tx)
    r_r, az_r, el_r = sph_from_xyz(rx)
    t0 = time.time()
    phis, tab, info = mnf.phase_table(
        spec, FC, r_t, az_t, el_t, wavefront="spherical", n_phase=int(n_phase),
        period_deg=360.0, frame_div=disc["frame_div"], blade_div=disc["blade_div"],
        blade_n=disc["blade_n"], rx_range_m=r_r, rx_az_deg=az_r, rx_el_deg=el_r)
    A_t = mnf.antenna_pos(r_t, az_t, el_t); R_t = float(np.linalg.norm(A_t))
    A_s = mnf.antenna_pos(r_r, az_r, el_r); R_s = float(np.linalg.norm(A_s))
    E_frame, n_fp = _frame_field(spec, A_t, A_s, R_t, R_s, disc)
    info = dict(info, seconds=float(time.time() - t0),
                tx_xyz=[float(v) for v in tx], rx_xyz=[float(v) for v in rx],
                E_frame_abs_recomputed=float(abs(E_frame)), n_frame_pts=n_fp,
                disc=dict(disc))
    return (np.asarray(phis, float), np.asarray(tab, complex),
            np.asarray(tab, complex) - E_frame, info)


# --------------------------------------------------------------------------- #
#  ⭐ 자기검증 — 기존 report15_po_control.json 의 저장 파형을 재현하는가
#     (내가 arm_po 를 다시 짰으므로, 같은 커널이라는 것을 **수치로** 보여야 한다)
# --------------------------------------------------------------------------- #
def selfcheck_vs_po_control() -> dict:
    src = os.path.join(ROOT, "outputs", "report15_po_control.json")
    out = dict(source=os.path.relpath(src, ROOT), available=os.path.exists(src), rows={})
    if not out["available"]:
        return out
    with open(src) as f:
        D = json.load(f)
    az0 = float(D["meta"]["az_deg"]); el0 = float(D["meta"]["el_deg"])
    r0 = float(D["meta"]["range_m"]); npz = int(D["meta"]["n_phase"])
    for key in KEYS:
        A = D["airframes"].get(key)
        if not A:
            continue
        arm = A["arms"].get("ref/po_spherical_bistatic")
        if not arm:
            continue
        #  저장물은 **극형식**(amp_db, phase_deg)이다 — 복소로 되돌려 비교한다.
        blk = (arm.get("full128") or {}).get("wave") or {}
        if "amp_db" not in blk or "phase_deg" not in blk:
            out["rows"][key] = dict(skipped="저장 파형 키를 찾지 못함", keys=sorted(blk.keys()))
            continue
        E_ref = (10.0 ** (np.asarray(blk["amp_db"], float) / 20.0)
                 * np.exp(1j * np.radians(np.asarray(blk["phase_deg"], float))))
        _, Ea, _, _ = arm_po(DRONES[key], az0, el0, r0, n_phase=npz, disc=PO_MATCHED)
        n = min(len(E_ref), len(Ea))
        d = np.abs(Ea[:n] - E_ref[:n]) / (np.abs(E_ref[:n]) + 1e-300)
        #  ⚠ 저장물이 dB·deg 로 반올림돼 있으므로 완전한 비트일치는 기대하지 않는다.
        #    같은 커널이면 상대차가 반올림 수준(≲1e-6)에 머물러야 한다.
        out["rows"][key] = dict(n=int(n), max_rel_diff=float(d.max()),
                                median_rel_diff=float(np.median(d)),
                                reproduces=bool(d.max() < 1e-5),
                                stored_format="polar(amp_db, phase_deg) — 반올림 포함",
                                az_deg=az0, el_deg=el0, range_m=r0)
    out["all_reproduce"] = bool(out["rows"]) and all(
        v.get("reproduces") for v in out["rows"].values() if "reproduces" in v)
    return out


# --------------------------------------------------------------------------- #
#  본 격자
# --------------------------------------------------------------------------- #
def run_grid(key, n_phase=N_PHASE, disc=PO_MATCHED, tag="matched") -> dict:
    spec = DRONES[key]
    blocks = {}
    t0 = time.time()
    for R in RANGES:
        for ak, az, el in ASPECTS:
            phis, Ea, Ep, info = arm_po(spec, az, el, R, n_phase=n_phase, disc=disc)
            blocks[f"{R:g}/{ak}"] = dict(
                range_m=float(R), aspect=ak, az_deg=float(az), el_deg=float(el),
                phis_deg=[float(x) for x in phis],
                all_re=[float(x) for x in Ea.real], all_im=[float(x) for x in Ea.imag],
                prop_re=[float(x) for x in Ep.real], prop_im=[float(x) for x in Ep.imag],
                E_frame_abs=float(info["E_frame_abs_recomputed"]),
                n_frame_pts=int(info["n_frame_pts"]),
                n_blade_pts=int(info["n_blade_pts"]),
                blade_spacing_actual_median_m=float(info["blade_spacing_actual_median_m"]),
                tx_xyz=info["tx_xyz"], rx_xyz=info["rx_xyz"],
                seconds=float(info["seconds"]))
            print(f"    {key:10s} R={R:>4g} m  {ak:8s}  |E| ptp="
                  f"{np.ptp(20*np.log10(np.abs(Ea)+1e-300)):7.3f} dB  "
                  f"prop ptp={np.ptp(20*np.log10(np.abs(Ep)+1e-300)):8.3f} dB  "
                  f"({info['seconds']:.1f}s)", flush=True)
    return dict(tag=tag, n_phase=int(n_phase), period_deg=360.0, disc=dict(disc),
                ranges_m=[float(r) for r in RANGES],
                aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
                seconds=float(time.time() - t0), blocks=blocks)


def grid_alignment_check(n_phase, sionna_n_phase=64, period_deg=180.0) -> dict:
    """PO 의 앞 sionna_n_phase 점이 Sionna 격자와 같은 φ 인지 **검증**한다."""
    po = np.linspace(0.0, 360.0, int(n_phase), endpoint=False)
    si = np.arange(sionna_n_phase) * (period_deg / sionna_n_phase)
    k = int(round(n_phase / 360.0 * period_deg / sionna_n_phase))  # 격간추출 간격
    sub = po[:int(sionna_n_phase * k):k] if k >= 1 else po[:sionna_n_phase]
    n = min(len(sub), len(si))
    return dict(po_n_phase=int(n_phase), po_step_deg=float(360.0 / n_phase),
                sionna_n_phase=int(sionna_n_phase),
                sionna_step_deg=float(period_deg / sionna_n_phase),
                subsample_stride=int(k), n_matched=int(n),
                max_phase_diff_deg=float(np.max(np.abs(sub[:n] - si[:n]))),
                aligned=bool(np.max(np.abs(sub[:n] - si[:n])) < 1e-9))


def main():
    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_verdict_po_grid.py",
        role="Sionna 격자와 동일한 (거리×자세) 칸에서 우리 PO 커널을 돌린다 — 판정항목 4",
        engine="src/microdoppler_nearfield.py — 구면파 PO, 실제 TX/RX 좌표, **가림 없음**",
        fc_hz=FC, lambda_m=LAM, baseline_m=BASELINE_M,
        ranges_m=[float(r) for r in RANGES],
        aspects=[dict(name=n, az_deg=a, el_deg=e) for n, a, e in ASPECTS],
        n_phase=N_PHASE, n_phase_fine=N_PHASE_FINE,
        po_matched=dict(PO_MATCHED), po_refined=dict(PO_REFINED),
        gpu="사용 안 함 (순수 numpy)",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")))

    print("§0  격자 정합 검증")
    J["grid_alignment"] = grid_alignment_check(N_PHASE)
    print("   ", json.dumps(J["grid_alignment"], ensure_ascii=False))

    print("\n§1  자기검증 — 기존 po_control 저장 파형 재현")
    J["selfcheck"] = selfcheck_vs_po_control()
    print("   ", json.dumps(J["selfcheck"].get("rows", {}), ensure_ascii=False)[:400])

    J["airframes"] = {}
    for key in KEYS:
        print(f"\n§2  본 격자 — {key} (matched 점구름)")
        g = run_grid(key, N_PHASE, PO_MATCHED, "matched")
        print(f"\n§3  세밀 격자 — {key} (스펙트럼 꼬리)")
        gf = run_grid(key, N_PHASE_FINE, PO_MATCHED, "fine")
        print(f"\n§4  점구름 정밀화 대조 — {key}")
        gr = run_grid(key, N_PHASE, PO_REFINED, "refined")
        J["airframes"][key] = dict(name=DRONES[key].name, matched=g, fine=gf, refined=gr)

    J["meta"]["seconds_total"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
