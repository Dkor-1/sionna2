# -*- coding: utf-8 -*-
"""
report15_specular_range_law.py — 정반사 채널이 **레이다 법칙을 따르는가**
===========================================================================

본 스윕의 격자를 거리축으로 회귀해 보면 두 채널이 **다른 거리 법칙**을 따른다:

    확산(prod, 표적 전체)   :  −40.2 ~ −41.2 dB/decade  →  1/R⁴   (교과서 레이다식)
    정반사(spec, 카메라 글린트):  −21.4 dB/decade        →  1/R²   (거울 법칙)

1/R² 는 **무한 평면 거울**의 법칙이다. 유한한 반사체라면 그 원거리장(2D²/λ) 너머에서는
반드시 1/R⁴ 여야 한다. 카메라 렌즈면은 몇 cm 라 2D²/λ ≈ 수 cm 이고, 1~10 m 는 전부
그 너머다 — 즉 **정반사 채널의 거리 법칙이 유한 산란체에 대해 틀렸다**.

이 파일은 그것을 드론이 아니라 **크기를 아는 금속 평판**으로 통제 실험한다. 두 시험 모두
"산란적분(유한 개구 보정)이 있는가" 라는 하나의 질문을 다른 각도에서 찌른다.

  §A 크기 시험 (⭐ 결정적) — 거리를 고정하고 평판 한 변을 300→3 mm 로 줄인다.
      · 진실(PO 원거리장): σ = 4πA²/λ² → 진폭[dB] 이 한 변의 **10배당 40 dB** 떨어져야 한다.
      · 거울 법칙       : 정반사점만 평판 위에 있으면 **크기와 무관**하다(0 dB).
      본 스윕 `mechanism.a_plate_size` 는 경로 **개수**만 셌다(전부 1개) — 진폭은 안 쟀다.
      여기서 진폭을 잰다.

  §B 거리 시험 — 평판 크기를 고정하고 R 을 0.5→30 m 로 옮긴다.
      · 진실(원거리장): −40 dB/decade.   · 거울: −20 dB/decade.

  §C 드론 격자 회귀 (RT 재실행 없음) — 위 두 법칙 사이 어디에 앉는지 채널별로 적는다.

⛔ src/drones.py · src/drone_cad.py 를 건드리지 않는다(스윕 모듈 경유 읽기만).
⛔ 새 산출물 파일을 만들지 않고 이 실험의 자기 JSON 에 `specular_range_law` 키만 더한다.

실행:  ~/.venvs/py312/bin/python benchmark/report15_specular_range_law.py
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

import report15_sweep_matrice4e as M                                  # noqa: E402
import sionna.rt as rt                                                # noqa: E402

LAM, FC = M.LAM, M.FC
AZ, EL = 0.0, 15.0           # 평판 법선 = 이 방향의 이등분선 (본 스윕 §6 과 같은 규약)
SPP = 256_000_000            # 정반사는 결정론적이라 예산을 크게 쓸 이유가 없다
SIZES_MM = (300.0, 100.0, 30.0, 10.0, 3.0)
RANGES_A = (1.0, 3.0, 10.0)
RANGES_B = (0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 30.0)
SIZES_B_MM = (300.0, 100.0)


# --------------------------------------------------------------------------- #
def plate_scene(side_m: float, tag: str):
    """법선을 TX/RX 이등분선(=look_dir(AZ,EL))에 정확히 맞춘 금속 평판.
    ⭐ 본 스윕 §6(mechanism.a_plate_size)의 `_plate`·`_one_obj_scene` 을 그대로 쓴다 —
      같은 표적이어야 '개수는 셌고 진폭은 안 쟀다' 는 빈칸을 메우는 것이 된다."""
    u = M.look_dir(AZ, EL)
    return M._one_obj_scene(M._plate(side_m, u), tag, mat="metal")


def spec_amp(scene, R: float) -> dict:
    """정반사 경로의 위상무관 에너지 Σ|a|² [dB]. LoS 는 뺀다(표적경유 경로만)."""
    M.place(scene, AZ, EL, R)
    p = rt.PathSolver()(scene, max_depth=1, los=False, specular_reflection=True,
                        diffuse_reflection=False, refraction=False,
                        samples_per_src=int(SPP), max_num_paths_per_src=M.MAX_PATHS, seed=1)
    ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
    #  ⚠ 경로가 0 개면 마지막 축이 0 이라 reshape(-1, 0) 이 터진다 — 먼저 빠져나간다.
    if ar.size == 0 or ar.shape[-1] == 0:
        return dict(n=0, inc_db=None, tau_ns=None)
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    tau = np.asarray(p.tau, dtype=np.float64).reshape(-1, a.shape[0])[0]
    O = np.asarray(p.objects)[:, 0, 0, :]
    hit = (O != M.NO_OBJ).any(axis=0)
    P = int(hit.sum())
    e = float(np.sum(np.abs(a[hit]) ** 2)) if P else 0.0
    return dict(n=P, inc_db=(float(10 * np.log10(e + 1e-300)) if P else None),
                tau_ns=(float(tau[hit].min() * 1e9) if P else None))


def legs(R: float, baseline: float = None) -> tuple:
    """준-모노스태틱 배치의 두 다리 길이 (원점 표적)."""
    b = M.BASELINE_M if baseline is None else baseline
    r = math.hypot(R, b / 2.0)
    return r, r


def mirror_db(R: float) -> float:
    """무한 평면 거울: 펼친 경로 R1+R2 에 대한 Friis. |Γ|=1 가정."""
    r1, r2 = legs(R)
    return float(20 * math.log10(LAM / (4 * math.pi * (r1 + r2))))


def po_plate_db(side_m: float, R: float) -> float:
    """유한 평판의 진실(원거리장 PO): σ=4πA²/λ² 를 레이다식에 넣으면 A²/((4π)²R1²R2²)."""
    r1, r2 = legs(R)
    A = side_m ** 2
    return float(20 * math.log10(A / (4 * math.pi * r1 * r2)))


def crossover_side_m(R: float) -> float:
    """Sionna 의 거울 답과 PO 진실이 **우연히 같아지는** 평판 크기.
    A/(4πR1R2) = λ/(4π(R1+R2)) → A = λ·R1R2/(R1+R2).  ⭐ R 에 비례하므로 고정 보정계수로
    고칠 수 없다는 것이 이 수의 요점이다."""
    r1, r2 = legs(R)
    return float(math.sqrt(LAM * r1 * r2 / (r1 + r2)))


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    with open(M.OUT_JSON, "r", encoding="utf-8") as f:
        J = json.load(f)

    #  §A — 크기 시험
    print("§A 평판 크기 시험 (거리 고정)  — 진실 40 dB/decade-of-size vs 거울 0")
    A = {}
    for s_mm in SIZES_MM:
        sc, dd = plate_scene(s_mm / 1000.0, f"PLA{int(s_mm*10):06d}")
        for R in RANGES_A:
            r = spec_amp(sc, R)
            po, mi_ = po_plate_db(s_mm / 1000.0, R), mirror_db(R)
            A[f"{s_mm:g}mm/{R:g}m"] = dict(
                side_mm=s_mm, range_m=R, **r,
                farfield_2D2_lam_m=2 * (s_mm / 1000.0) ** 2 / LAM,
                in_farfield=bool(R > 2 * (s_mm / 1000.0) ** 2 / LAM),
                mirror_predict_db=mi_, po_truth_db=po,
                err_vs_po_db=(None if r["inc_db"] is None else float(r["inc_db"] - po)),
                err_vs_mirror_db=(None if r["inc_db"] is None else float(r["inc_db"] - mi_)))
            e = A[f"{s_mm:g}mm/{R:g}m"]
            print(f"    한변 {s_mm:6.1f} mm  R={R:5.1f} m  경로 {r['n']}  "
                  f"E={r['inc_db'] if r['inc_db'] is None else round(r['inc_db'],2)} dB  "
                  f"거울예측 {mi_:7.2f}  PO진실 {po:8.2f}  "
                  f"오차 {'--' if e['err_vs_po_db'] is None else format(e['err_vs_po_db'],'+8.2f')} dB")
        M.drop(dd)

    size_fit = {}
    for R in RANGES_A:
        xs, ys = [], []
        for s_mm in SIZES_MM:
            v = A[f"{s_mm:g}mm/{R:g}m"]
            if v["inc_db"] is not None:
                xs.append(math.log10(s_mm)); ys.append(v["inc_db"])
        slope = float(np.polyfit(xs, ys, 1)[0]) if len(xs) > 1 else None
        size_fit[f"{R:g}"] = dict(
            range_m=R, n_points=len(xs), slope_db_per_decade_of_size=slope,
            swing_db=(float(max(ys) - min(ys)) if ys else None),
            truth_po_slope=40.0, mirror_slope=0.0,
            follows=("PO(면적²)" if slope is not None and slope > 20.0 else
                     ("거울(크기 무관)" if slope is not None and abs(slope) < 10.0 else "중간")))
        print(f"    → R={R:g} m: 기울기 {slope:.2f} dB/decade-of-size  "
              f"(진실 40, 거울 0)  판정 {size_fit[f'{R:g}']['follows']}")

    #  §B — 거리 시험
    print("\n§B 평판 거리 시험 (크기 고정)  — 진실 −40 dB/decade vs 거울 −20")
    Bd, range_fit = {}, {}
    for s_mm in SIZES_B_MM:
        sc, dd = plate_scene(s_mm / 1000.0, f"PLB{int(s_mm*10):06d}")
        xs, ys = [], []
        for R in RANGES_B:
            r = spec_amp(sc, R)
            Bd[f"{s_mm:g}mm/{R:g}m"] = dict(side_mm=s_mm, range_m=R, **r)
            if r["inc_db"] is not None:
                xs.append(math.log10(R)); ys.append(r["inc_db"])
            print(f"    한변 {s_mm:6.1f} mm  R={R:5.1f} m  경로 {r['n']}  "
                  f"E={r['inc_db'] if r['inc_db'] is None else round(r['inc_db'],2)} dB")
        M.drop(dd)
        slope = float(np.polyfit(xs, ys, 1)[0]) if len(xs) > 1 else None
        ff = 2 * (s_mm / 1000.0) ** 2 / LAM
        range_fit[f"{s_mm:g}mm"] = dict(
            side_mm=s_mm, farfield_2D2_lam_m=ff, n_points=len(xs),
            slope_db_per_decade=slope, truth_farfield_slope=-40.0, mirror_slope=-20.0,
            all_points_in_farfield=bool(min(RANGES_B) > ff),
            follows=("거울(1/R²)" if slope is not None and slope > -30.0 else "레이다(1/R⁴)"))
        print(f"    → 한변 {s_mm:g} mm (원거리장 {ff*1000:.1f} mm): 기울기 {slope:.2f} dB/decade  "
              f"판정 {range_fit[f'{s_mm:g}mm']['follows']}")

    #  §C — 드론 격자 회귀 (RT 없음)
    GA = J["grid_analysis"]["by_block"]
    x = np.log10(np.array([1.0, 3.0, 10.0]))
    drone_fit = {}
    for mode in ("spec", "prod"):
        for asp in [a for a, _, _ in M.ASPECTS]:
            y = []
            for r in ("1", "3", "10"):
                v = GA.get(f"{r}/{asp}/{mode}/all")
                y.append(v["inc_db_mean"] if v and v.get("ok") else np.nan)
            y = np.array(y, float)
            if np.isnan(y).any():
                continue
            sl = float(np.polyfit(x, y, 1)[0])
            drone_fit[f"{mode}/{asp}"] = dict(
                mode=mode, aspect=asp, inc_db_by_range={r: float(v) for r, v in zip(("1", "3", "10"), y)},
                slope_db_per_decade=sl, exponent=float(-sl / 10.0),
                follows=("거울(1/R²)" if sl > -30.0 else "레이다(1/R⁴)"))

    mirror_size_blind = bool(all(v["slope_db_per_decade_of_size"] is not None
                                 and abs(v["slope_db_per_decade_of_size"]) < 10.0
                                 for v in size_fit.values()))
    mirror_range = bool(all(v["slope_db_per_decade"] is not None
                            and v["slope_db_per_decade"] > -30.0 for v in range_fit.values()))
    J["specular_range_law"] = dict(
        question=("스톡 Sionna 의 **정반사 경로**가 유한 산란체의 레이다 법칙(크기²·1/R⁴)을 "
                  "따르는가, 아니면 무한 거울 법칙(크기 무관·1/R²)을 따르는가"),
        spp=int(SPP), baseline_m=float(M.BASELINE_M), fc_hz=float(FC), lambda_m=float(LAM),
        A_size_test=dict(
            rows=A, fit=size_fit,
            analytic=dict(
                mirror_law_db="20log10(λ / (4π(R1+R2)))  — 무한 거울, 크기 무관",
                po_truth_db="20log10(A / (4π R1 R2))  — σ=4πA²/λ² 를 레이다식에 넣은 유한 평판",
                max_abs_err_vs_mirror_db=float(max(
                    abs(v["err_vs_mirror_db"]) for v in A.values()
                    if v["err_vs_mirror_db"] is not None)),
                max_abs_err_vs_po_db=float(max(
                    abs(v["err_vs_po_db"]) for v in A.values()
                    if v["err_vs_po_db"] is not None)),
                crossover_side_m={f"{R:g}": crossover_side_m(R) for R in RANGES_A},
                crossover_note_ko=(
                    "Sionna 의 거울 답이 PO 진실과 우연히 일치하는 평판 크기 A=λ·R1R2/(R1+R2). "
                    "⭐ 이 크기가 **거리에 비례**하므로, 이보다 작은 부품은 과대평가되고 큰 부품은 "
                    "과소평가되며 그 경계가 거리마다 움직인다 — 즉 **고정 보정계수로 못 고친다**."))),
        B_range_test=dict(rows=Bd, fit=range_fit),
        C_drone_grid_fit=drone_fit,
        verdict=dict(
            specular_is_size_blind=mirror_size_blind,
            specular_follows_mirror_range_law=mirror_range,
            verdict_ko=(
                "스톡 Sionna 의 정반사 경로는 **무한 거울**의 답을 준다 — 반사체 크기에 거의 "
                "무관하고 거리에 1/R² 로 떨어진다. 유한 산란체의 진실(σ=4πA²/λ², 1/R⁴)이 아니다. "
                "그래서 이 채널의 값은 **RCS 로 환산하면 안 된다**. 확산 채널은 반대로 1/R⁴ 를 "
                "정확히 지킨다."
                if (mirror_size_blind and mirror_range) else
                "정반사 채널이 거울 법칙을 벗어난다 — 위 수치를 직접 읽을 것.")),
        why_it_matters_ko=(
            "이 격자에서 정반사를 내는 부위는 짐벌 카메라의 평평한 렌즈면뿐이고, 그 글린트가 "
            "정면 자세(hot)에서 프롭 확산 에코보다 1 m 에서 57.8 dB 크다. 두 채널의 거리 법칙이 "
            "20 dB/decade 다르므로 **거리가 멀어질수록 글린트의 지배가 커진다** — 10 m 에서 77.5 dB. "
            "즉 '자세에 따라 마이크로도플러가 죽는다' 는 관측은 거리가 늘수록 악화되는 방향이고, "
            "그 악화분은 물리가 아니라 정반사 채널의 틀린 거리 법칙이 만든다."),
        note_ko=("평판은 법선이 TX/RX 이등분선과 정확히 맞도록 놓았다(정반사 최적). metal 재질. "
                 "los=False 로 직접파를 뺐다. 원거리장 경계 2D²/λ 를 각 평판마다 적어 두었으니 "
                 "'근거리장이라 그렇다' 는 반론이 성립하는지 바로 확인할 수 있다."),
        seconds=float(time.time() - t0))

    #  헤드라인에 한 줄
    J["headline"]["specular_range_law"] = dict(
        specular_is_size_blind=mirror_size_blind,
        specular_slope_db_per_decade={k: v["slope_db_per_decade"] for k, v in range_fit.items()},
        specular_size_slope_db_per_decade={k: v["slope_db_per_decade_of_size"]
                                           for k, v in size_fit.items()},
        diffuse_slope_db_per_decade={k: v["slope_db_per_decade"]
                                     for k, v in drone_fit.items() if v["mode"] == "prod"},
        truth_size_slope=40.0, truth_range_slope=-40.0,
        mirror_size_slope=0.0, mirror_range_slope=-20.0)

    J.setdefault("meta", {}).setdefault("addendum3", {}).update(
        script="benchmark/report15_specular_range_law.py",
        stamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        added=["specular_range_law(신규 RT 통제실험 — 금속 평판 크기·거리 시험)"])

    tmp = M.OUT_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    os.replace(tmp, M.OUT_JSON)
    print(f"\n■ 저장: {M.OUT_JSON}   ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
