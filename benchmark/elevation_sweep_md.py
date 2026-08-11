# -*- coding: utf-8 -*-
"""
elevation_sweep_md.py — **거리 대신 앙각을 바꿔가며 마이크로도플러를 그린다.**

사용자(2026-08-11)
> "이번 주 팀미팅 준비하면서 같은 각도에서 거리만 멀어지게 해서 STFT 했잖아.
>  그걸 **엘리베이션을 바꿔가며** 그려보는 것부터 우선적으로 해볼 수 있을까?"

■ 왜 이 축인가
거리 축에서는 우리 커널의 맵이 거의 안 변했다(상관 0.983 / 0.999 / 0.983). 산란 진폭은
표적의 성질이고 거리는 링크버짓의 몫이라 그게 맞다. **앙각은 다르다** — 표적이 실제로
다르게 보이는 축이고, 그래서 **우리 커널만 답할 수 있는 자리**다(PathSolver 에는 산란적분이
없어 각도별 로브를 못 낸다).

■ ⭐예측 — 재기 전에 못 박는다
    f_flash = 날개 수 × 회전수 = 126.67 Hz  ← **앙각과 무관**
    f_tip   = 2·(2π f_rev R)/λ · cos(el)    ← **cos(el) 로 줄어든다**

| el | cos | f_tip [Hz] |
|---|---|---|
| 0° | 1.000 | 1272 |
| −15° (덱) | 0.966 | 1229 |
| −30° | 0.866 | 1102 |
| −45° | 0.707 | 900 |
| −60° | 0.500 | 636 |
| −75° | 0.259 | 329 |
| −90° (직하방) | 0.000 | **0** |

⇒ **플래시 박자는 그대로, 도플러 폭만 좁아진다.** 직하방에서는 날개 속도가 시선에 수직이라
  **마이크로도플러가 원리적으로 사라진다.** 실전 함의가 크다 — 머리 위 드론은 안 보인다.

■ ⚠대역을 앙각마다 다시 잡아야 한다
덱의 대역은 `0.35~1.0 × f_tip` 인데 f_tip 이 앙각에 걸리므로 **고정 대역을 쓰면 안 된다.**
이 스크립트는 두 가지를 다 낸다 —
  (a) `band=track`  앙각마다 그 앙각의 f_tip 으로 대역을 다시 잡는다 ⭐정본
  (b) `band=fixed`  덱의 −15° 대역(430~1229 Hz)을 그대로 쓴다 → 앙각이 내려가면 **비어 간다**
(b) 를 함께 내는 이유는 «고정 대역을 쓰면 어디서 무너지나» 가 그 자체로 결과이기 때문이다.

■ 축 하나만 바꾼다
로터는 **덱과 같은 결정론 패턴**을 쓴다(OU 프리셋이 아니다). 로터와 앙각을 같이 바꾸면
무엇이 무엇을 바꿨는지 못 가른다. 거리는 **10 m 구면**으로 고정한다 — 앙각이 바뀌어도 표적까지의 거리가 일정하다
  (`place()` 가 `tx = c + R·û` 이고 baseline 0 이라 |tx−c| = R 로 항상 같다).
  ⚠10 m 는 원거리장 경계 2D²/λ ≈ 14.08 m **안쪽**이다. 우리 커널은 `range_m` 구면파로
  처리하고 PathSolver 는 실제 기하라 원래 문제없다 — 다만 «근거리장 판» 이라고 적어야 한다.

    # 우리 커널
    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py \
        --engine ours --shard 0 --nshards 8
    # Sionna PathSolver
    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py \
        --engine sionna --shard 0 --nshards 8
    # 병합·분석
    PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py --merge
"""
from __future__ import annotations

import argparse
import glob
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

import numpy as np                                                      # noqa: E402

FC, RANGE_M = 3.5e9, 10.0          # ⭐사용자 지시(2026-08-11) — 구면 반경 10 m 고정
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
DIV = 12                            # 격자 간격 λ/12 — 덱과 같은 규약
SHD = f"{ROOT}/outputs/elev_sweep_shards"
OUT = f"{ROOT}/outputs/elevation_sweep_md.json"
OUTN = f"{ROOT}/outputs/elevation_sweep_md.npz"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]


def los(az_deg: float, el_deg: float) -> np.ndarray:
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def rule_spp(rng_m: float) -> int:
    """(R/3)² × 1M — 덱과 같은 광선 규칙."""
    return int(round(1_000_000 * (rng_m / 3.0) ** 2))


# ═══ 계산 ═══════════════════════════════════════════════════════════════════
def run(a) -> None:
    from gpu import pick
    pick(verbose=False)
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fp = FastPoser(spec)
    prf, n = float(TJ["prf_hz"]), int(TJ["n"])
    az = float(TJ.get("az_deg", 0.0))
    # ⭐덱과 **같은** 로터 설정 — 축 하나만 바꾼다
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    idx = np.arange(a.shard, n, a.nshards)
    os.makedirs(SHD, exist_ok=True)

    if a.engine in ("ours", "ours_free"):
        from rcs_sbr import sbr_field, grid_ref_from
        gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
        d = (2.998e8 / FC) / DIV
        gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                             FC, spacing=d)
        # ⭐가림 대조군 — 동체의 **면만** 뺀다. 정점(mv.v)은 그대로 둬서 bbox·광선격자가
        #   같으므로 «동체가 막느냐» 하나만 다른 단일축이 된다(report15b 의 blade_free 규약).
        prop_only = (a.engine == "ours_free")
        if prop_only:
            keep = np.asarray(fp.g) == "prop"
            f_keep, g_keep = fp.f[keep], fp.g[keep]
        for el in ELS:
            f = f"{SHD}/{a.engine}_el{el:+.0f}_{a.shard:02d}.npz"
            if os.path.exists(f) and not a.overwrite:
                print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
            u = los(az, el)
            E = np.zeros(idx.size, complex); t0 = time.time()
            for j, i in enumerate(idx):
                mv = fp.pose(ph[int(i)])
                if prop_only:
                    mv.f, mv.g = f_keep, g_keep          # 정점은 그대로 — bbox 보존
                E[j] = sbr_field(mv, gm, FC, u,
                                 spacing=d, grid_ref=gref, range_m=RANGE_M)
                if j and j % 128 == 0:
                    e = time.time() - t0
                    print(f"    el{el:+.0f} sh{a.shard}: {j}/{idx.size} "
                          f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)
            np.savez_compressed(f, idx=idx, E=E,
                                meta=np.array([el, a.shard, a.nshards, n, prf,
                                               time.time() - t0]))
            print(f"  ✅ {a.engine} el{el:+.0f} sh{a.shard} · {idx.size} 자세 · "
                  f"{(time.time()-t0)/60:.1f}분", flush=True)
        return

    # ── Sionna PathSolver ───────────────────────────────────────────────────
    import report15_probe as RP
    from drones import drone_colors
    spp = rule_spp(RANGE_M)
    cols = drone_colors(spec)
    for el in ELS:
        f = f"{SHD}/sionna_el{el:+.0f}_{a.shard:02d}.npz"
        if os.path.exists(f) and not a.overwrite:
            print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
        E = np.zeros(idx.size, complex); npaths = np.zeros(idx.size, int)
        t0 = time.time()
        for j, i in enumerate(idx):
            i = int(i)
            m = fp.pose(ph[i]).to_mesh()
            dd = os.path.join(RP.SCRATCH, f"elev_{spec.key}_e{el:+.0f}s{a.shard}_{i%2}")
            paths_obj = m.write_obj_per_group(dd, spec.key)
            parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                     for g, p in paths_obj.items()]
            sc = RP.build_scene(parts, fc=FC)
            RP.place(sc, az=az, el=el, rng=RANGE_M, baseline=0.0)
            p = RP.rt.PathSolver()(sc, max_depth=1, los=True,
                                   specular_reflection=True, diffuse_reflection=True,
                                   refraction=False, samples_per_src=spp,
                                   max_num_paths_per_src=RP.MAX_PATHS, seed=1)
            try:
                aa, tau, _, O = RP.unpack(p)
            except ValueError:
                aa = np.zeros(0)
            if aa.size:
                hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
                E[j] = complex(np.sum(aa[hit] * np.exp(-1j * 2 * np.pi * FC * tau[hit])))
                npaths[j] = int(hit.sum())
            RP.drop_scratch(dd)
            if j and j % 128 == 0:
                e = time.time() - t0
                print(f"    el{el:+.0f} sh{a.shard}: {j}/{idx.size} "
                      f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)
        np.savez_compressed(f, idx=idx, E=E, npaths=npaths,
                            meta=np.array([el, a.shard, a.nshards, n, prf,
                                           time.time() - t0, spp]))
        print(f"  ✅ sionna el{el:+.0f} sh{a.shard} · {idx.size} 자세 · "
              f"{(time.time()-t0)/60:.1f}분", flush=True)


# ═══ 병합·분석 ══════════════════════════════════════════════════════════════
def f_tip_at(el_deg: float) -> float:
    import sys as _s; _s.path.insert(0, f"{ROOT}/src")
    from drones import DRONES
    spec = DRONES[TJ.get("drone", "matrice4e")]
    lam = 2.998e8 / FC
    R = spec.prop_dia_mm / 2000.0
    f_rev = float(getattr(spec, "hover_rpm", 6000.0)) / 60.0
    return 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(el_deg))


def analyse() -> None:
    from md_mapstyle import auto_periods, flash_spec
    prf, ffl = float(TJ["prf_hz"]), float(TJ["f_flash_hz"])
    per = auto_periods(prf, ffl)
    ft_deck = float(TJ["f_tip_hz"])                 # −15° 의 f_tip (덱 대역의 기준)

    def band_metrics(E, lo, hi):
        f, t, S, _ = flash_spec(np.asarray(E, complex), prf, ffl, per)
        b = (np.abs(f) >= lo) & (np.abs(f) <= hi)
        if b.sum() < 2:
            return dict(n_bins=int(b.sum()), beat_hz=None, h1_over_h2_db=None,
                        band_power_db=None)
        g = (S[b, :] ** 2).sum(axis=0)
        pw = 10 * np.log10(g.mean())
        g = g - g.mean()
        dt = float(t[1] - t[0]); m = len(g)
        A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
        fr = np.fft.rfftfreq(64 * m, dt)
        if A.max() <= 0:
            return dict(n_bins=int(b.sum()), beat_hz=None, h1_over_h2_db=None,
                        band_power_db=round(pw, 2))
        A = A / A.max()
        sel = (fr >= 40) & (fr <= 400)
        i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
        y0, y1, y2 = A[i - 1], A[i], A[i + 1]
        den = y0 - 2 * y1 + y2
        pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])

        def pkdb(f0, h=18.0):
            w = (fr >= f0 - h) & (fr <= f0 + h)
            return 20 * np.log10(A[w].max()) if w.any() else np.nan
        return dict(n_bins=int(b.sum()), beat_hz=round(float(pk), 2),
                    h1_over_h2_db=round(float(pkdb(ffl) - pkdb(2 * ffl)), 2),
                    band_power_db=round(pw, 2))

    rows, series = [], {}
    for eng in ("ours", "ours_free", "sionna"):
        for el in ELS:
            fs = sorted(glob.glob(f"{SHD}/{eng}_el{el:+.0f}_*.npz"))
            if not fs:
                continue
            E = None; secs = 0.0; npa = []
            for f in fs:
                z = np.load(f); ii = z["idx"].astype(int)
                if E is None:
                    E = np.zeros(int(np.asarray(z["meta"], float)[3]), complex)
                E[ii] = z["E"]; secs += float(np.asarray(z["meta"], float)[5])
                if "npaths" in z: npa.append(z["npaths"])
            miss = int((E == 0).sum())
            ft = f_tip_at(el)
            series[f"{eng}/el{el:+.0f}"] = E
            rows.append(dict(
                engine=eng, el_deg=el, cos_el=round(float(np.cos(np.radians(el))), 4),
                f_tip_hz=round(ft, 1), n_poses=len(E), n_missing=miss,
                seconds=round(secs, 1),
                npaths_median=int(np.median(np.concatenate(npa))) if npa else None,
                level_db=round(float(20 * np.log10(np.mean(np.abs(E)) + 1e-300)), 2),
                # ⭐(a) 앙각마다 대역을 다시 잡는다 — 정본
                track=band_metrics(E, 0.35 * ft, max(ft, 1e-6)),
                # (b) 덱의 −15° 대역 고정 — 어디서 무너지나
                fixed=band_metrics(E, 0.35 * ft_deck, ft_deck)))

    if not rows:
        raise SystemExit(f"⛔ {SHD} 에 샤드가 없다")
    np.savez_compressed(OUTN, **series)
    json.dump({"_meta": {
        "generator": "benchmark/elevation_sweep_md.py",
        "question_ko": "거리 대신 앙각을 바꾸면 마이크로도플러가 어떻게 변하나",
        "range_m": RANGE_M, "range_why_ko": "원거리장 경계 2D²/λ = 14.08 m 바로 위로 고정",
        "fc_hz": FC, "prf_hz": prf, "f_flash_hz": ffl,
        "elevations_deg": list(ELS), "drone": TJ.get("drone"),
        "rotor_ko": "덱과 같은 결정론 패턴(OU 프리셋 아님) — 축을 하나만 바꾼다",
        "rpm_per_rotor": TJ.get("rpm_per_rotor"),
        "grid_ko": "얼린 격자(자세 합집합 bbox), λ/12",
        "ours_illumination": "spherical wave at 15 m",
        "sionna_spp": rule_spp(RANGE_M),
        "band_track_ko": "⭐정본 — 앙각마다 그 앙각의 f_tip 으로 0.35~1.0 배",
        "band_fixed_ko": "덱의 −15° 대역(430~1229 Hz) 고정 — 앙각이 내려가면 비어 간다",
        "prediction_ko": "f_flash 는 앙각과 무관(126.67 Hz), f_tip 만 cos(el) 로 줄어든다. "
                         "직하방(−90°)에서는 날개 속도가 시선에 수직이라 마이크로도플러가 "
                         "원리적으로 사라진다."},
        "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"\n═══ 앙각 스윕 · R = {RANGE_M:.0f} m · 예측 f_flash {ffl:.2f} Hz ═══\n")
    print(f"{'엔진':>7} {'el':>5} {'f_tip':>7} | {'박자(추적대역)':>13} {'1x−2x':>7} "
          f"{'레벨':>8} | {'박자(고정대역)':>13} {'빈수':>5}")
    for r in rows:
        t, x = r["track"], r["fixed"]
        bt = f"{t['beat_hz']:.2f}" if t["beat_hz"] else "  —"
        bx = f"{x['beat_hz']:.2f}" if x["beat_hz"] else "  —"
        h = f"{t['h1_over_h2_db']:+.2f}" if t["h1_over_h2_db"] is not None else "  —"
        print(f"{r['engine']:>7} {r['el_deg']:>5.0f} {r['f_tip_hz']:>7.0f} | "
              f"{bt:>13} {h:>7} {r['level_db']:>8.2f} | {bx:>13} {x['n_bins']:>5}")
    print(f"\n✅ {OUT}\n✅ {OUTN}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="ours",
                    choices=("ours", "ours_free", "sionna"),
                    help="ours=동체 포함(가림 있음) · ours_free=⭐동체 **면만** 빼서 "
                         "가림을 없앤 대조군(정점은 그대로라 bbox·광선격자 동일) · sionna")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    analyse() if a.merge else run(a)


if __name__ == "__main__":
    main()
