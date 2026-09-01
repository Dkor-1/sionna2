# -*- coding: utf-8 -*-
"""outdoor_scene_0901.py — 실외 장면이 날개 박자에 하는 일 (리포트 12 원장).

무엇을 묻나
-----------
지금까지 스윕은 **자유공간**이었다 — `rt.load_scene()` 빈 씬에 드론 부품만 넣는다.
그래서 우리가 «클러터» 라고 부르며 걷어낸 것은 전부 **드론 자신의 동체**였다.
지면·건물을 넣으면 박자가 살아남나, 그리고 정지 클러터 제거로 되돌릴 수 있나.

잣대 — ⭐포락 자기상관 ρ (1 지연)
----------------------------------
⛔dB 잣대(봉우리÷바닥)는 **몇 자세짜리 낙차 임펄스열**에도 큰 값을 준다. 2026-08-31
적대 검증에서 실제로 그 함정이 드러났다 — el 0 기록의 변동 100 % 가 8,192 자세 중
19~52 개의 낙차인데 dB 는 9.5 를 줬다. 대체 잣대 넷 중 **살아남은 것은 ρ 하나**다.
  잡음 −0.06~+0.07 · 박자 +0.92~+0.99

⛔우리 커널은 이 비교에 못 들어간다 — `--env` 는 PathSolver 씬에만 붙고 `sbr_field` 는
   드론 메쉬만 받는다. 격자가 표적 bbox 로 정해지므로 지면 120 m 를 통째로 넣으면
   격자점이 79,483 배가 된다. 그 수도 여기서 낸다.

⛔GPU 를 쓰지 않는다. CUDA_VISIBLE_DEVICES="" 로 돌린다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/outdoor_scene_0901.py
"""
import json
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
OUT = f"{ROOT}/outputs/outdoor_scene_0901.json"
MESH = "mfixbatteryi5_blperairframe"
ELS = [0.0, -30.0, -60.0]
CUTS = [5.0, 20.0, 60.0, 100.0, 120.0]


def arm(el, env=False):
    tag = "_envoutdoor01" if env else ""
    return f"sionna_p4000000000_swR0D0E0F1_r15_n8192{tag}_{MESH}_d2/el{el:+.0f}"


def rho(E):
    """포락 자기상관(1 지연)."""
    a = np.abs(np.asarray(E))
    ac = a - a.mean()
    d = float(np.dot(ac, ac))
    return float(np.dot(ac[:-1], ac[1:]) / d) if d > 0 else float("nan")


def corr(a, b):
    a = np.asarray(a) - np.mean(a)
    b = np.asarray(b) - np.mean(b)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(abs(np.vdot(a, b)) / d) if d > 0 else float("nan")


def lvl(E):
    return float(20 * np.log10(np.abs(np.asarray(E)).mean()))


def main():
    from clutter_parts_ladder_0824 import cs_eca, PRF, FFL, FCUT
    from rcs_sbr import DEFAULT_DIV
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")

    cells = {}
    print(f"═══ 실외 장면 · ECA 노치 {FCUT:g} Hz · f_flash {FFL:.2f} Hz ═══\n")
    hdr = (f"{'앙각':>5}{'자유공간 ρ':>12}{'실외 ρ':>10}{'제거 후 ρ':>11}"
           f"{'레벨 변화':>11}{'|상관| 잔차↔자유':>17}{'AC 남은몫':>10}")
    print(hdr)
    print("-" * len(hdr))
    for el in ELS:
        F = np.asarray(Z[arm(el, False)])
        O = np.asarray(Z[arm(el, True)])
        R = cs_eca(O)
        ac0 = float(np.sum(np.abs(O - O.mean()) ** 2))
        ac1 = float(np.sum(np.abs(R - R.mean()) ** 2))
        c = dict(el_deg=el,
                 rho_free=round(rho(F), 4), rho_outdoor=round(rho(O), 4),
                 rho_removed=round(rho(R), 4),
                 level_free_db=round(lvl(F), 2), level_outdoor_db=round(lvl(O), 2),
                 d_level_db=round(lvl(O) - lvl(F), 2),
                 corr_removed_vs_free=round(corr(R, F), 4),
                 ac_left_pct=round(100 * ac1 / ac0, 1),
                 rho_free_removed=round(rho(cs_eca(F)), 4))
        cells[f"el{el:+.0f}"] = c
        print(f"{el:>+5.0f}{c['rho_free']:>+12.3f}{c['rho_outdoor']:>+10.3f}"
              f"{c['rho_removed']:>+11.3f}{c['d_level_db']:>+10.1f} dB"
              f"{c['corr_removed_vs_free']:>17.4f}{c['ac_left_pct']:>9.1f}%")

    # ── 노치 폭 사다리
    print(f"\n═══ 노치 폭을 흔들어도 같은가 ═══")
    notch = {}
    for el in (-30.0, -60.0):
        F = np.asarray(Z[arm(el, False)])
        O = np.asarray(Z[arm(el, True)])
        row = {}
        line = f"  el{el:>+4.0f}  "
        for fc in CUTS:
            R = cs_eca(O, fcut=fc)
            row[f"fcut{fc:g}"] = dict(rho=round(rho(R), 4),
                                      corr_vs_free=round(corr(R, F), 4))
            line += f"fcut{fc:>5.0f}: ρ {rho(R):+.3f} |r| {corr(R, F):.3f}   "
        notch[f"el{el:+.0f}"] = row
        print(line)

    # ── 격자 비용 — 왜 우리 커널이 못 들어가나
    lam = 2.998e8 / 3.5e9
    d = lam / DEFAULT_DIV
    pad = 1.15

    def grid(Rmax):
        Rout = Rmax * pad + 3 * d
        n = int(np.ceil(2 * Rout / d))
        return dict(R_max_m=round(Rmax, 3), R_out_m=round(Rout, 3), n=n, points=n * n)

    G = {"drone_only": grid(0.28), "ground_120m": grid(float(np.hypot(60, 60))),
         "patch_2m": grid(float(np.hypot(1.0, 1.0))),
         "patch_5m": grid(float(np.hypot(2.5, 2.5)))}
    base = G["drone_only"]["points"]
    for k in G:
        G[k]["vs_drone"] = round(G[k]["points"] / base, 1)
    print(f"\n═══ 광선 격자 비용 (λ/{DEFAULT_DIV} = {d*1000:.2f} mm) ═══")
    for k, v in G.items():
        print(f"  {k:<14} R_max {v['R_max_m']:>7.2f} m · n {v['n']:>7,} · "
              f"격자점 {v['points']:>15,} · {v['vs_drone']:>10,.0f} 배")

    # ── 제1 프레넬 존 — 실제로 필요한 지면 넓이
    r_m = 15.0
    R1 = float(np.sqrt(lam * r_m * r_m / (2 * r_m)))
    print(f"\n  제1 프레넬 반경 (15 m·3.5 GHz) = {R1*100:.0f} cm · 지름 {2*R1:.2f} m")

    doc = dict(_meta=dict(
        generator="benchmark/outdoor_scene_0901.py", gpu_used=False,
        generated_ko="2026-09-01",
        question_ko=("실외 장면(지면·건물)을 넣으면 날개 박자가 살아남나, "
                     "그리고 정지 클러터 제거로 되돌릴 수 있나"),
        metric_ko=("포락 자기상관 ρ(1 지연). 잡음 −0.06~+0.07 · 박자 +0.92~+0.99. "
                   "⛔dB(봉우리÷바닥)는 몇 자세짜리 낙차 임펄스열에도 큰 값을 주므로 쓰지 않는다."),
        arm_ko=("스톡 엔진 ①다끔(R0D0E0F1) · matrice4e · 15 m · 자세 8,192 · "
                "광선 4e9 · 깊이 2. 실외 팔은 파일명에 _envoutdoor01 이 붙는다."),
        env_ko=("assets/meshes/outdoor01 — 지면 120×120 m 콘크리트 · 건물 넷 9~24 m · "
                "금속 기둥 둘. 드론 고도 20 m(레이다가 rng·sin(el) 깊이에 오므로 "
                "15 m·el −90 의 −15 m 보다 지면이 아래여야 한다)."),
        ours_absent_ko=("⛔우리 커널은 이 비교에 없다 — --env 는 build_scene(PathSolver 씬)에만 "
                        "붙고 sbr_field 는 자세 잡힌 드론 메쉬만 받는다. 그 상태로 난 샤드 6 개는 "
                        "자유공간과 상대차 1e−16 이라 2026-09-01 에 지웠고, "
                        "--engine ours 에 --env 를 주면 이제 거부한다."),
        removal_ko=f"benchmark/clutter_parts_ladder_0824.cs_eca — DFT 격자에서 |f| ≤ fcut 투영 소거. 정본 {FCUT:g} Hz",
        prf_hz=float(PRF), f_flash_hz=float(FFL), fcut_hz=float(FCUT),
        lam_m=round(lam, 6), grid_spacing_m=round(d, 6), grid_div=int(DEFAULT_DIV),
        fresnel_r1_m=round(R1, 3), range_m=r_m),
        cells=cells, notch_ladder=notch, grid_cost=G)
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
