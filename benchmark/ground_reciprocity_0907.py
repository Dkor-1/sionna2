#!/usr/bin/env python
"""지면 커널이 쓰는 **상호성 가정**을 실제 드론 메쉬에서 잰다.

무엇이 문제인가 — `src/rcs_sbr.py:1496` 의 독스트링이 이렇게 적는다:

    「상호성 E(a,b)=E(b,a) 로 계산은 **셋**이다:
       E = E(û,û) + 2Γ·E(û′,û) + Γ²·E(û′,û′)」

그래서 `sbr_field_ground` 는 지면 한 번 튀는 항을 **한쪽 순서로만** 계산하고 2 를 곱한다.
그런데 이 커널은 상호적일 수 없다 — 광선 격자가 **입사 방향 û_i 로 깔리고**
(`:1364` `_ray_grid(ctr, Rout, n, d, u_i)`), 조명 패스가 û_i 에만 의존한다(`:1369`).
인자 순서를 바꾸면 **어느 삼각형이 조명되는지**가 달라진다. 게이트 자신도 주석에서
「정확히 성립할 수 없다」고 적어, 한 파일 안에서 정면으로 모순돼 있었다.

⚠그리고 `benchmark/verify_ground_kernel.py` 의 게이트들은 **드론 메쉬를 안 쓴다** —
  그 파일의 `try: from drones import build_drone ... mesh, gm = None, None` 은 두 갈래가
  같은 값을 넣어 메쉬를 만들지 않고, 모든 게이트가 3 cm 껍질 위에서 돈다.
  3 cm 껍질은 파장(λ≈8.6 cm)보다 작아 방향 쏠림이 거의 없으니 상호성이 잘 맞는 것이
  당연하다. 드론은 λ 의 여러 배라 그 시험이 **드론을 안 덮는다.**

무엇을 재나 — 자세마다 두 순서를 **둘 다** 계산해 견준다.

    E_dg(û′,û)  vs  E_dg(û,û′)      ← 지면 한 번 튀는 항
    상대차 = |E_ab − E_ba| / (|E_ab|+|E_ba|)/2
    그리고 그 차가 **합친 장**을 얼마나 움직이나 — 2·E_ab 를 쓴 판과
    (E_ab + E_ba) 를 쓴 판의 |E| 차이를 dB 로 낸다. 그것이 실제로 걸리는 값이다.

⛔판정하지 않는다 — 수를 낸다. 「우리 커널이 틀렸다」도 「맞다」도 적지 않는다.
⛔이 값은 σ(dBsm) 가 아니다.

⛔⛔**이 원장은 CPU 를 많이 쓴다 — 코어를 묶어서 돌려라.**
  2026-09-07 에 `OMP_NUM_THREADS=1` 만 주고 돌렸다가 **1,484 % (14 코어)** 를 먹었고,
  GPU 큐의 감독자 셋이 전부 「⛔대기: CPU 사용률 1.00 > 0.85」로 멈춰 20 분을 굶었다.
  SBR 커널의 병렬은 OMP 환경변수를 안 탄다 — 그래서 이 파일이 **스스로**
  `--max-cores` 만큼 `os.sched_setaffinity` 로 묶는다(기본 2).

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 nice -n 19 \
      PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
      benchmark/ground_reciprocity_0907.py --n-az 8
    → outputs/ground_reciprocity_0907.json
"""
from __future__ import annotations

import argparse, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drones import DRONES, build_drone, DRONE_GROUP_MAT                # noqa: E402
from freespace_link import fresnel_gamma                                # noqa: E402
from rcs_sbr import (DEFAULT_DIV, sbr_field_bistatic, ground_combine,  # noqa: E402
                     ground_eps_sigma)

OUT = os.path.join(ROOT, "outputs", "ground_reciprocity_0907.json")
C0 = 299792458.0


def los(az_deg, el_deg):
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], float)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default="matrice4e")
    ap.add_argument("--fc", type=float, default=3.5e9)
    ap.add_argument("--range-m", type=float, default=15.0)
    ap.add_argument("--alt-m", type=float, default=20.0)
    ap.add_argument("--els", default="-15,-30,-45,-60")
    ap.add_argument("--n-az", type=int, default=8, help="방위 표본 수(0~360 균등)")
    ap.add_argument("--div", type=int, default=0,
                    help=f"격자 간격 λ/div (0 = 생산값 {'{}'} 을 쓴다)")
    ap.add_argument("--div-ladder", default="8,12,16,24",
                    help="격자 촘촘함 사다리 λ/div — 상호성 오차가 «이산화 탓» 인지 본다. "
                         "빈 문자열이면 사다리를 안 돈다.")
    ap.add_argument("--ladder-els", default="-30",
                    help="사다리를 돌 앙각(쉼표) — 촘촘한 격자는 비싸니 좁게 잡는다")
    ap.add_argument("--ladder-n-az", type=int, default=4)
    ap.add_argument("--max-cores", type=int, default=2,
                    help="이 프로세스를 묶을 코어 수 (기본 2). "
                         "⛔0 을 주면 안 묶는다 — GPU 큐가 안 돌 때만.")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    #: ⛔⛔**코어를 묶는다.** OMP/OPENBLAS/MKL 환경변수로는 이 커널의 병렬이 안 잡힌다
    #  (2026-09-07 실측: 다 1 로 주고도 1,484 %). 감독자의 CPU 문턱은 0.85 이고
    #  넘으면 GPU 워커를 아예 안 띄우므로, 이 계산이 큐를 굶긴다.
    if a.max_cores > 0 and hasattr(os, "sched_setaffinity"):
        _all = sorted(os.sched_getaffinity(0))
        _use = set(_all[:max(1, min(a.max_cores, len(_all)))])
        os.sched_setaffinity(0, _use)
        print(f"  ⭐코어 {len(_use)} 개로 묶었다 ({sorted(_use)}) — GPU 큐를 굶기지 않으려고",
              flush=True)

    spec = DRONES[a.drone]
    mesh = build_drone(spec)
    gm = {g: DRONE_GROUP_MAT[g][0] for g in DRONE_GROUP_MAT}
    lam = C0 / a.fc
    #: ⭐**생산과 같은 간격으로 잰다 — λ/DEFAULT_DIV.** 2026-09-07 첫 판은 CPU 를 아끼려고
    #  λ/8 로 쟀는데, 그것은 생산(λ/12)보다 **성기고** 상호성 오차는 간격에 민감하다
    #  (아래 사다리: λ/8 에서 0.355, λ/12 에서 0.144). 성긴 판의 수를 실으면 근사의
    #  어긋남을 **과장**하게 된다. 그래서 기본을 생산값에 맞춘다.
    d = lam / float(a.div if a.div else DEFAULT_DIV)
    eps_r, sig = ground_eps_sigma(a.fc)

    els = [float(x) for x in a.els.split(",") if x.strip()]
    azs = list(np.linspace(0.0, 360.0, a.n_az, endpoint=False))

    t0 = time.time()
    rows = []
    for el in els:
        #: 거울상 기하 — 지면 아래로 뜬 레이다에서 오는 방향
        R = float(a.range_m)
        h_r = float(a.alt_m) + R * np.sin(np.radians(el))     # 레이다 높이
        h_t = float(a.alt_m)                                  # 표적(드론) 높이
        for az in azs:
            u = los(az, el)
            #: 거울상 방향 — 수직 성분 부호를 뒤집는다
            u_img = np.array([u[0], u[1], -u[2]], float)
            R_img = float(np.hypot(np.hypot(R * np.cos(np.radians(el)), 0.0),
                                   h_r + h_t)) if False else R
            #: ⚠경로 길이는 이 잣대에 안 들어온다 — 두 순서의 **장**만 견준다.
            #  (조합식의 위상 인자는 두 순서에 똑같이 곱해지므로 상쇄된다.)
            kw = dict(spacing=d, penetrate=True)
            E_ab = sbr_field_bistatic(mesh, gm, a.fc, u_img, u,
                                      range_i=R, range_s=R, **kw)
            E_ba = sbr_field_bistatic(mesh, gm, a.fc, u, u_img,
                                      range_i=R, range_s=R, **kw)
            m = 0.5 * (abs(E_ab) + abs(E_ba))
            rel = float(abs(E_ab - E_ba) / max(m, 1e-300))

            #: 이 차가 «합친 장» 을 얼마나 움직이나 — 그것이 실제로 걸리는 값이다.
            E_dd = sbr_field_bistatic(mesh, gm, a.fc, u, u,
                                      range_i=R, range_s=R, **kw)
            E_gg = sbr_field_bistatic(mesh, gm, a.fc, u_img, u_img,
                                      range_i=R, range_s=R, **kw)
            psi = abs(float(el))
            Gam = complex(fresnel_gamma(psi, eps_r=eps_r, cond=sig, pol="v", fc=a.fc))
            dR = 2.0 * h_r * np.sin(np.radians(psi))
            #: 커널이 쓰는 판 — 한쪽 순서 × 2
            E_used = ground_combine(E_dd, E_ab, E_gg, Gam, dR, a.fc)
            #: 두 순서를 실제로 더한 판
            E_true = ground_combine(E_dd, 0.5 * (E_ab + E_ba), E_gg, Gam, dR, a.fc)
            shift_db = float(20 * np.log10(abs(E_used) / max(abs(E_true), 1e-300)))

            #: ⚠**dB 비는 상쇄 자리에서 부푼다.** 합친 장이 직접 항보다 훨씬 작으면
            #  아무리 작은 차도 dB 로는 크게 나온다. 그것을 가릴 수 있게 합친 장과
            #  직접 항의 비를 **그대로** 싣는다.
            #  ⛔여기에 「거의 널이다」 문턱을 두지 않는다 — 문턱을 하나 정하면 그것이
            #    결과를 정해 버린다(2026-09-07 에 실외 원장에서 잡힌 바로 그 병이다).
            #    대신 아래 summary 가 |shift| 와 이 비의 **순위 상관**을 낸다.
            null_ratio = float(abs(E_true) / max(abs(E_dd), 1e-300))
            rows.append({"el_deg": el, "az_deg": round(az, 2),
                         "abs_E_ab": float(abs(E_ab)), "abs_E_ba": float(abs(E_ba)),
                         "abs_E_used": float(abs(E_used)),
                         "abs_E_true": float(abs(E_true)),
                         "abs_E_direct": float(abs(E_dd)),
                         "total_over_direct": round(null_ratio, 6),
                         "rel_diff": round(rel, 6),
                         "total_shift_db": round(shift_db, 4)})
            print(f"  el{el:+.0f}° az{az:6.1f}°  상대차 {rel:8.4f}  "
                  f"합친 장 {shift_db:+7.4f} dB", flush=True)

    #: ── ⭐이 어긋남이 «이산화 탓» 인가 ─────────────────────────────────────
    #  게이트(verify_ground_kernel.py G6)는 3 cm 껍질에서 격자를 촘촘히 하면 오차가
    #  준다고 보인다(λ/12→λ/24→λ/48 에서 0.186→0.105→0.026). 그렇다면 드론 메쉬에서도
    #  줄어야 한다 — 줄면 「촘촘히 하면 사라지는 수치 오차」이고, 안 줄면 **구조적**이다.
    #  ⛔이 물음에 답하지 않고 「근사가 얼마나 틀렸다」만 적으면 반쪽이다.
    ladder = {}
    _divs = [int(x) for x in a.div_ladder.split(",") if x.strip()]
    if _divs:
        _lels = [float(x) for x in a.ladder_els.split(",") if x.strip()]
        _lazs = list(np.linspace(0.0, 360.0, a.ladder_n_az, endpoint=False))
        for dv in _divs:
            dd = lam / float(dv)
            vs = []
            for el in _lels:
                for az in _lazs:
                    u = los(az, el)
                    u_img = np.array([u[0], u[1], -u[2]], float)
                    kw2 = dict(spacing=dd, penetrate=True)
                    A = sbr_field_bistatic(mesh, gm, a.fc, u_img, u,
                                           range_i=a.range_m, range_s=a.range_m, **kw2)
                    B = sbr_field_bistatic(mesh, gm, a.fc, u, u_img,
                                           range_i=a.range_m, range_s=a.range_m, **kw2)
                    m2 = 0.5 * (abs(A) + abs(B))
                    vs.append(float(abs(A - B) / max(m2, 1e-300)))
            ladder[f"lam/{dv}"] = {
                "spacing_m": round(dd, 6), "n_rows": len(vs),
                "rel_diff_median": round(float(np.median(vs)), 4),
                "rel_diff_max": round(float(max(vs)), 4),
            }
            print(f"  [사다리] λ/{dv:<3} 간격 {dd*1e3:6.2f} mm  "
                  f"상대차 중앙 {np.median(vs):.4f} · 최대 {max(vs):.4f}", flush=True)

    rel = np.array([r["rel_diff"] for r in rows])
    sh = np.abs(np.array([r["total_shift_db"] for r in rows]))
    _tod = np.array([r["total_over_direct"] for r in rows])

    def _rank(v):
        o = np.argsort(np.argsort(v)).astype(float)
        return (o - o.mean()) / max(o.std(), 1e-30)

    _spear = float(np.mean(_rank(sh) * _rank(_tod)))
    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "benchmark/ground_reciprocity_0907.py",
            "question_ko": "지면 커널이 쓰는 상호성 가정 E(a,b)=E(b,a) 가 실제 드론 메쉬에서"
                           " 얼마나 성립하나",
            "why_ko": "rcs_sbr.py:1496 이 상호성을 근거로 지면 한 번 튀는 항을 한쪽 순서로만"
                      " 계산하고 2 를 곱한다. 그런데 광선 격자가 û_i 로 깔려(:1364)"
                      " 인자 순서를 바꾸면 조명되는 삼각형이 달라진다.",
            "gate_gap_ko": "⚠benchmark/verify_ground_kernel.py 의 게이트는 드론 메쉬를 안 쓴다"
                           " — 3 cm 껍질(λ≈8.6 cm 보다 작다)에서만 잰다. 그 시험은 드론을"
                           " 안 덮는다.",
            "drone": a.drone, "fc_hz": a.fc, "range_m": a.range_m, "alt_m": a.alt_m,
            "grid_spacing_m": round(d, 6),
            "grid_div": int(a.div if a.div else DEFAULT_DIV),
            "grid_div_is_production": bool(not a.div or a.div == DEFAULT_DIV), "n_rows": len(rows),
            "elapsed_s": round(time.time() - t0, 1),
            "limits_ko": [
                "⛔이 원장은 「커널이 틀렸다」를 말하지 않는다 — 가정이 얼마나 어긋나는지만 잰다.",
                "⛔이 값은 σ(dBsm) 가 아니다. 두 엔진의 절대 레벨을 견주지 않는다.",
                "⚠자세(로터 위상)는 고정이다 — 방위·앙각만 훑는다.",
                "⚠큰 dB 값을 «상쇄 자리라서» 로 설명하지 마라 — 순위 상관이"
                " spearman_shift_vs_total_over_direct 에 있고, 2026-09-07 판에서는"
                " −0.07 로 사실상 관계가 없다. 가장 큰 줄(el−60·az225, +9.48 dB)이"
                " 마침 비가 가장 작은 줄이기도 하지만 32 줄로는 우연과 구별되지 않는다.",
            ],
        },
        "summary": {
            "rel_diff_median": round(float(np.median(rel)), 4),
            "rel_diff_max": round(float(rel.max()), 4),
            "rel_diff_p90": round(float(np.percentile(rel, 90)), 4),
            "total_shift_db_median": round(float(np.median(sh)), 4),
            "total_shift_db_max": round(float(sh.max()), 4),
            "n_rows_over_1pct": int(np.count_nonzero(rel > 0.01)),
            "n_rows_shift_over_0p5db": int(np.count_nonzero(sh > 0.5)),
            "n_rows_shift_over_1db": int(np.count_nonzero(sh > 1.0)),
            "total_over_direct_min": round(float(min(_tod)), 4),
            "total_over_direct_median": round(float(np.median(_tod)), 4),
            #: ⭐|shift| 가 큰 줄이 정말 «합친 장이 작은» 줄인가 — 순위 상관으로 본다.
            #  −1 에 가까우면 큰 dB 는 가정이 틀린 크기가 아니라 상쇄 때문이다.
            "spearman_shift_vs_total_over_direct": round(float(_spear), 4),
            "spearman_note_ko": "|shift| 의 순위와 (합친 장 ÷ 직접 항) 의 순위 사이 상관."
                                " 음수이고 크면 큰 dB 값은 그 자리가 상쇄에 가까워서다",
            "ladder_shrinks": (None if len(ladder) < 2 else bool(
                list(ladder.values())[-1]["rel_diff_median"]
                < 0.5 * list(ladder.values())[0]["rel_diff_median"])),
            "ladder_note_ko": "격자를 촘촘히 할 때 상대차가 절반 아래로 주나."
                              " False 면 이 어긋남은 이산화 탓이 아니라 구조적이다"
                              "(격자가 û_i 로 깔리는 한 남는다)",
        },
        "discretisation_ladder": ladder,
        "rows": rows,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n⭐{a.out}  줄 {len(rows)} · {doc['_meta']['elapsed_s']}s")
    for k, v in doc["summary"].items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
