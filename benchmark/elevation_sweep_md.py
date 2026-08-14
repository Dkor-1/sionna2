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
import re
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

    drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))
    spec = DRONES[drone_key]
    fp = FastPoser(spec)
    prf = float(TJ["prf_hz"])
    # ⭐자세 수는 인자로 덮어쓸 수 있다. 기본은 원장값이라 기존 동작과 같다.
    n = int(getattr(a, "n_poses", 0) or TJ["n"])
    #: ⭐방위는 인자로 덮어쓸 수 있다. 안 주면 원장값이라 기존 동작과 같다.
    _az_arg = float(getattr(a, "az_deg", float("nan")))
    az = float(TJ.get("az_deg", 0.0)) if np.isnan(_az_arg) else _az_arg
    # ⭐덱과 **같은** 로터 설정 — 축 하나만 바꾼다
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    # ⚠기체를 바꾸면 로터 수가 달라진다(s1000plus 는 8 개, 원장 배열은 4 개다).
    #   그때는 그 기체의 호버 회전수에 원장과 **같은 상대 산포**를 얹어 만든다 —
    #   산포를 버리면 네 로터가 완전 동기라 빗살이 인위로 깨끗해진다.
    n_rot = len(fp.dirs)
    if (getattr(a, "drone", "") and drone_key != TJ.get("drone", "matrice4e")) \
            or rpms.size != n_rot:
        base = float(getattr(spec, "hover_rpm", float(np.mean(rpms))))
        rel = rpms / np.mean(rpms)                       # 원장의 상대 산포
        rel = np.resize(rel, n_rot)                      # 로터 수에 맞춰 되풀이
        rpms = base * rel
        print(f"  ⚠로터 {n_rot} 개 — 원장 배열({rpms.size if rpms.size!=n_rot else 4} 개)과 달라 "
              f"{spec.key} 호버 {base:.0f} rpm 에 원장 산포를 얹어 만든다", flush=True)
    ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    els = tuple(float(x) for x in a.els.split(',') if x.strip()) or ELS
    idx = np.arange(a.shard, n, a.nshards)
    os.makedirs(SHD, exist_ok=True)
    # ⭐거리·깊이는 인자로 받는다. 기본값이면 꼬리표가 안 붙어 기존 샤드 이름과 같다.
    rng_m = float(getattr(a, "range_m", RANGE_M) or RANGE_M)
    # ⭐평면파는 range_m=None 으로 넘긴다(rcs_sbr:1090 «None 이면 평면파»).
    #   PathSolver 는 실제 기하를 쓰므로 이 스위치가 없다 — 우리 팔 전용이다.
    plane = bool(getattr(a, "plane_wave", False))
    tagr = ("" if not getattr(a, "drone", "") else f"_{drone_key}") \
        + ("" if abs(rng_m - RANGE_M) < 1e-9 else f"_r{rng_m:g}") \
        + ("" if not getattr(a, "n_poses", 0) else f"_n{n}") \
        + ("_pw" if plane else "") \
        + ("" if np.isnan(_az_arg) else f"_az{_az_arg:g}")

    if a.engine in ("ours", "ours_free"):
        from rcs_sbr import sbr_field, grid_ref_from
        gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
        #: ⭐격자 간격 λ/div. div 를 안 주면 규약값 12 라 기존 샤드와 비트동일하다.
        div = int(getattr(a, "div", 0) or DIV)
        d = (2.998e8 / FC) / div
        gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                             FC, spacing=d)
        # ⭐가림 대조군 — 동체의 **면만** 뺀다. 정점(mv.v)은 그대로 둬서 bbox·광선격자가
        #   같으므로 «동체가 막느냐» 하나만 다른 단일축이 된다(report15b 의 blade_free 규약).
        prop_only = (a.engine == "ours_free")
        if prop_only:
            keep = np.asarray(fp.g) == "prop"
            f_keep, g_keep = fp.f[keep], fp.g[keep]
        for el in els:
            tagd = ("_ptd" if a.ptd else "") + tagr \
                + ("" if not getattr(a, "div", 0) else f"_div{div}")
            f = f"{SHD}/{a.engine}{tagd}_el{el:+.0f}_{a.shard:02d}.npz"
            if os.path.exists(f) and not a.overwrite:
                print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
            u = los(az, el)
            E = np.zeros(idx.size, complex); t0 = time.time()
            for j, i in enumerate(idx):
                mv = fp.pose(ph[int(i)])
                if prop_only:
                    mv.f, mv.g = f_keep, g_keep          # 정점은 그대로 — bbox 보존
                E[j] = sbr_field(mv, gm, FC, u, spacing=d, grid_ref=gref,
                                 range_m=(None if plane else rng_m), ptd=bool(a.ptd))
                if j and j % 128 == 0:
                    e = time.time() - t0
                    print(f"    el{el:+.0f} sh{a.shard}: {j}/{idx.size} "
                          f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)
            np.savez_compressed(f, idx=idx, E=E,
                                meta=np.array([el, a.shard, a.nshards, n, prf,
                                               time.time() - t0]),
                                # ⭐출처 — 우리 팔은 광선 예산·깊이가 없으므로 NaN 으로 둔다.
                                #   평면파는 range_m 을 NaN 으로 적어 «무한거리» 를 표시한다.
                                cfg=np.array([np.nan if plane else rng_m,
                                              np.nan, np.nan, 0.0]))
            print(f"  ✅ {a.engine} el{el:+.0f} sh{a.shard} · {idx.size} 자세 · "
                  f"{(time.time()-t0)/60:.1f}분", flush=True)
        return

    # ── Sionna PathSolver ───────────────────────────────────────────────────
    import report15_probe as RP
    from drones import drone_colors
    spp = int(a.spp) if a.spp else rule_spp(rng_m)
    # ⭐깊이는 물리 스위치와 분리한다. --max-depth 를 안 주면 옛 규칙 그대로다.
    mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else (3 if a.physics else 1)
    # ⭐--only 는 스위치 하나만 켠다(단일축 귀속). --physics 와 배타적이다.
    only = str(getattr(a, "only", "") or "")
    #: 확산 반사 — 스윕의 상수였다(켬). 순정 기본값·--sw 팔만 바꾼다.
    diffuse = True
    swbits = str(getattr(a, "sw", "") or "").upper()
    if swbits:
        import re as _re
        m = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)
        if not m:
            raise SystemExit(f"⛔ --sw 형식: R<0|1>D<0|1>E<0|1>F<0|1> (받은 값 {swbits!r})")
        r_, d_, e_, f_ = (bool(int(x)) for x in m.groups())
        sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
        diffuse = f_
        mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1
    elif getattr(a, "stock", False):
        sw = dict(refraction=True, diffraction=False, edge_diffraction=False)
        mdep = 3
        diffuse = False
    elif only:
        sw = dict(refraction=(only == "refr"), diffraction=(only == "diffr"),
                  edge_diffraction=(only == "edge"))
        mdep = 3 if only == "depth3" else 1
    else:
        sw = dict(refraction=bool(a.physics), diffraction=bool(a.physics),
                  edge_diffraction=bool(a.physics))
    cols = drone_colors(spec)
    for el in els:
        tagp = (("" if not a.spp else f"_p{a.spp}") + ("_phys" if a.physics else "")
                + (f"_sw{swbits}" if swbits else "")
                + ("_stockdef" if getattr(a, "stock", False) else "")
                + (f"_only{only}" if only else "")
                + tagr + ("" if not getattr(a, "max_depth", 0) else f"_d{mdep}"))
        f = f"{SHD}/sionna{tagp}_el{el:+.0f}_{a.shard:02d}.npz"
        if os.path.exists(f) and not a.overwrite:
            print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
        E = np.zeros(idx.size, complex); npaths = np.zeros(idx.size, int)
        t0 = time.time()
        for j, i in enumerate(idx):
            i = int(i)
            m = fp.pose(ph[i]).to_mesh()
            # ⭐프로세스마다 다른 폴더를 쓴다 (2026-08-11 결함 정정).
            #   전에는 이름에 앙각·샤드만 들어 있어서, **광선 예산이 다른 두 실행**을
            #   동시에 띄우면 같은 폴더를 썼다. 자세마다 drop_scratch 로 지우므로
            #   한쪽이 읽는 중에 다른 쪽이 지워 «OBJ file not found» 로 터졌다
            #   (el 0 사다리에서 샤드 7 개 손실). PID 를 넣으면 어떤 동시 실행과도 안 겹친다.
            dd = os.path.join(RP.SCRATCH,
                              f"elev_{spec.key}_e{el:+.0f}s{a.shard}"
                              f"_p{spp}_pid{os.getpid()}_{i%2}")
            paths_obj = m.write_obj_per_group(dd, spec.key)
            parts = [RP.Part(name=f"{spec.key}_{g}_{i%2}", obj=p,
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
                     for g, p in paths_obj.items()]
            sc = RP.build_scene(parts, fc=FC)
            RP.place(sc, az=az, el=el, rng=rng_m, baseline=0.0)
            p = RP.rt.PathSolver()(
                sc, los=True, specular_reflection=True, diffuse_reflection=diffuse,
                # ⭐--physics 면 굴절·회절·모서리회절을 전부 켠다.
                #   깊이는 --max-depth 로 따로 준다(안 주면 옛 규칙 3/1).
                max_depth=mdep, **sw,
                samples_per_src=spp, max_num_paths_per_src=RP.MAX_PATHS, seed=1)
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
                                           time.time() - t0, spp]),
                            # ⭐출처 — meta 모양은 안 바꾼다(기존 병합 코드 보호)
                            cfg=np.array([rng_m, mdep, spp,
                                          float(bool(a.physics)),
                                          float(sw["refraction"]),
                                          float(sw["diffraction"]),
                                          float(sw["edge_diffraction"])]))
        print(f"  ✅ sionna el{el:+.0f} sh{a.shard} · {idx.size} 자세 · "
              f"{(time.time()-t0)/60:.1f}분", flush=True)


# ═══ 병합·분석 ══════════════════════════════════════════════════════════════
def f_tip_at(el_deg: float, arm: str = "") -> float:
    import sys as _s; _s.path.insert(0, f"{ROOT}/src")
    from drones import DRONES
    # ⚠병합·분석 경로 — 팔 이름에 기체 태그(_mini5pro 등)가 있으면 **그 기체**의 제원을
    #   쓴다. 전에는 원장 기본 기체(matrice4e)로 일괄 계산해 기체 팔의 f_tip 이 틀렸다.
    key = TJ.get("drone", "matrice4e")
    for k in DRONES:
        if f"_{k}_" in arm or arm.endswith(f"_{k}"):
            key = k
            break
    spec = DRONES[key]
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
    # ⭐샤드 폴더에 실제로 있는 팔을 전부 집는다 — --spp 로 낸 것은
    #   sionna_p250000000_... 처럼 예산 꼬리표가 붙어 이름이 고정되지 않는다.
    engines = sorted({os.path.basename(f).rsplit("_el", 1)[0]
                      for f in glob.glob(f"{SHD}/*_el*.npz")},
                     key=lambda e: (not e.startswith("ours"), e))
    for eng in engines:
        for el in ELS:
            fs = sorted(glob.glob(f"{SHD}/{eng}_el{el:+.0f}_*.npz"))
            if not fs:
                continue
            E = None; secs = 0.0; npa = []; cfg = None
            for f in fs:
                z = np.load(f); ii = z["idx"].astype(int)
                if E is None:
                    E = np.zeros(int(np.asarray(z["meta"], float)[3]), complex)
                E[ii] = z["E"]; secs += float(np.asarray(z["meta"], float)[5])
                if "npaths" in z: npa.append(z["npaths"])
                # ⭐행마다 자기 판을 싣는다 — 한 원장에 10 m 와 15 m 가 함께 살기 때문.
                #   옛 샤드에는 cfg 가 없으므로 모듈 기본값으로 채운다.
                if cfg is None and "cfg" in z:
                    cfg = np.asarray(z["cfg"], float)
            miss = int((E == 0).sum())
            ft = f_tip_at(el, eng)
            series[f"{eng}/el{el:+.0f}"] = E
            if cfg is not None:
                # ⚠우리 팔은 깊이·광선 예산 개념이 없어 NaN 으로 적는다 → None 으로 읽는다.
                #   평면파 팔은 range_m 도 NaN 이다(무한거리).
                def _f(v):
                    return None if (v is None or np.isnan(v)) else float(v)

                def _i(v):
                    return None if (v is None or np.isnan(v)) else int(v)

                prov = dict(range_m=_f(cfg[0]), max_depth=_i(cfg[1]),
                            spp=_i(cfg[2]), physics=bool(cfg[3]))
                if prov["range_m"] is None:      # 평면파 — 이름의 _r 꼬리표를 쓴다
                    mr = re.search(r"_r(\d+(?:\.\d+)?)", eng)
                    prov["range_m"] = float(mr.group(1)) if mr else RANGE_M
                    prov["illumination"] = "plane wave (infinite range)"
            else:
                # cfg 가 없는 샤드 — **이름에서 읽는다.** 우리 팔 분기는 cfg 를 안 남기고,
                # 2026-08-12 이전 샤드도 없다. 거리는 _r<N> 꼬리표가 진실이다.
                m_spp = re.search(r"_p(\d+)", eng)
                m_rng = re.search(r"_r(\d+(?:\.\d+)?)", eng)
                rng = float(m_rng.group(1)) if m_rng else RANGE_M
                prov = dict(range_m=rng,
                            max_depth=(3 if eng.endswith("_phys") else 1),
                            spp=(int(m_spp.group(1)) if m_spp else rule_spp(rng)),
                            physics=eng.endswith("_phys"))
                if eng.startswith("ours"):
                    # 우리 커널은 광선 예산·반사 깊이 개념이 없다 — 격자로 푼다
                    prov.update(max_depth=None, spp=None, physics=None)
            #: ⭐방위·격자 축은 cfg 에 자리가 없다(옛 샤드와 호환을 지킨다) — 이름에서 읽는다.
            m_sw = re.search(r"_sw(R[01]D[01]E[01]F[01])", eng)
            if m_sw:
                b = m_sw.group(1)
                prov["switches"] = dict(refraction=b[1] == "1", diffraction=b[3] == "1",
                                        edge_diffraction=b[5] == "1", diffuse=b[7] == "1")
            m_az = re.search(r"_az(-?\d+(?:\.\d+)?)", eng)
            m_div = re.search(r"_div(\d+)", eng)
            prov["az_deg"] = float(m_az.group(1)) if m_az else float(TJ.get("az_deg", 0.0))
            prov["grid_div"] = int(m_div.group(1)) if m_div else (
                DIV if eng.startswith("ours") else None)
            rows.append(dict(
                engine=eng, el_deg=el, cos_el=round(float(np.cos(np.radians(el))), 4),
                f_tip_hz=round(ft, 1), n_poses=len(E), n_missing=miss,
                seconds=round(secs, 1), **prov,
                npaths_median=int(np.median(np.concatenate(npa))) if npa else None,
                level_db=round(float(20 * np.log10(np.mean(np.abs(E)) + 1e-300)), 2),
                # ⭐(a) 앙각마다 대역을 다시 잡는다 — 정본
                track=band_metrics(E, 0.35 * ft, max(ft, 1e-6)),
                # (b) 덱의 −15° 대역 고정 — 어디서 무너지나
                fixed=band_metrics(E, 0.35 * ft_deck, ft_deck)))

    if not rows:
        raise SystemExit(f"⛔ {SHD} 에 샤드가 없다")
    # ⭐부호 표식 — 샤드가 이미 정정본(R28)이므로 정정기가 다시 손대면 안 된다.
    np.savez_compressed(OUTN, phase_sign_v2=np.array([1], np.int8), **series)
    json.dump({"_meta": {
        "generator": "benchmark/elevation_sweep_md.py",
        "question_ko": "거리 대신 앙각을 바꾸면 마이크로도플러가 어떻게 변하나",
        # ⛔이 원장은 **거리가 하나가 아니다.** 행마다 range_m 을 실어 두었으니
        #   그 열을 읽어라. 아래 두 키는 옛 판(10 m)의 기본값일 뿐이다.
        "range_m_legacy_default": RANGE_M,
        "range_note_ko": ("⭐이 원장에는 **여러 거리·설정의 팔이 함께** 산다. 거리·깊이·"
                          "광선수·물리 여부는 **행마다** `range_m · max_depth · spp · "
                          "physics` 열에 실려 있다 — 그 열을 읽어라. "
                          "10 m 는 원거리장 경계 2D²/λ ≈ 14.08 m 의 **안쪽**(근거리장)이고, "
                          "15 m 는 **밖**이다. 두 거리의 값을 나란히 놓을 때는 그 사실을 "
                          "반드시 적는다."),
        "ranges_present_m": sorted({r["range_m"] for r in rows}),
        # ⭐재설계판(2026-08-13)의 **머리 판** — 리포트 16 이 이 값을 쓴다.
        #   원장에 10 m 옛 팔이 함께 살지만, 이 권이 서술하는 실험은 15 m 다.
        "range_m_primary": 15.0,
        "primary_note_ko": ("리포트 16 이 서술하는 판은 **15 m** 다 — 원거리장 경계 "
                            "2D²/λ ≈ 14.08 m 의 **밖**이다. 같은 원장에 10 m 옛 팔이 "
                            "함께 있으니 행의 `range_m` 열로 갈라 읽는다."),
        "ours_illumination": "spherical wave at 15 m",
        # ⭐리포트 16 이 «왜 이 거리인가» 를 인용하는 자리. 재설계판 기준으로 다시 쓴다.
        "range_why_ko": ("⭐2026-08-13 재설계 — 거리를 **15 m** 로 옮겼다. 원거리장 경계 "
                         "2D²/λ ≈ 14.08 m(메쉬 3D 대각 0.78 m 기준)의 **밖**이라, 옛 10 m 판이 "
                         "받던 «근거리장 판» 이라는 단서가 필요 없다. 우리 커널은 그 거리의 "
                         "구면파로 조명하고 PathSolver 는 실제 기하를 쓴다. ⚠같은 원장에 "
                         "10 m 옛 팔이 함께 사니 행의 `range_m` 열로 갈라 읽는다."),
        "sionna_spp_primary": 4_000_000_000,
        "fc_hz": FC, "prf_hz": prf, "f_flash_hz": ffl,
        "elevations_deg": list(ELS), "drone": TJ.get("drone"),
        "rotor_ko": "덱과 같은 결정론 패턴(OU 프리셋 아님) — 축을 하나만 바꾼다",
        "rpm_per_rotor": TJ.get("rpm_per_rotor"),
        "grid_ko": "얼린 격자(자세 합집합 bbox), λ/12",
        "ours_illumination_ko": "우리 팔은 행의 range_m 으로 구면파 조명 — 행마다 다르다",
        "spp_note_ko": "광선 수는 행의 spp 열에 있다 — 규칙값 (R/3)²×1M 을 --spp 로 덮은 팔이 많다",
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
    ap.add_argument("--physics", action="store_true",
                    help="⭐PathSolver 의 물리를 **전부 켠다** — 굴절·회절·모서리회절·다중반사. "
                         "기본 실행은 refraction=False·diffraction=False·max_depth=1 이라 "
                         "«PathSolver 가 굴절/회절을 더 잘 담는다» 를 시험한 적이 없었다. "
                         "같은 광선 예산에서 물리만 켜고 끄는 단일축 대조가 된다.")
    ap.add_argument("--ptd", action="store_true",
                    help="⭐우리 팔의 **모서리 회절(PTD 프린지)** 을 켠다. 기본은 ptd=False 라 "
                         "두 팔 다 모서리 회절이 없었다.")
    ap.add_argument("--engine", default="ours",
                    choices=("ours", "ours_free", "sionna"),
                    help="ours=동체 포함(가림 있음) · ours_free=⭐동체 **면만** 빼서 "
                         "가림을 없앤 대조군(정점은 그대로라 bbox·광선격자 동일) · sionna")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--els", default="",
                    help="쉼표로 앙각을 골라 돈다. 비면 7 점 전부. 예: --els 0")
    ap.add_argument("--spp", type=int, default=0,
                    help="0 이면 규칙값 (R/3)^2 x 1M. ⭐경로 수를 100 개 이상으로 "
                         "올리려면 직접 준다 — 규칙값은 10 m 에서 경로 6~13 개뿐이라 "
                         "«계단 잡음이 가장 심한 구간» 이다(2026-08-11 실측).")
    ap.add_argument("--range-m", type=float, default=RANGE_M,
                    help="⭐구면 반경 [m]. 기본 10 m 는 2D²/λ = 14.076 m 경계 **안쪽**이라 "
                         "근거리장이다(audit_po_trust.json:nearfield_verdict). 15 를 주면 "
                         "경계 밖이라 원거리장 가정이 선다. 10 이 아니면 파일명에 _r<R> 이 "
                         "붙어 기존 샤드와 섞이지 않는다.")
    ap.add_argument("--drone", default="",
                    help="⭐표적 기체를 바꾼다(기본은 원장의 matrice4e). 프롭 지름이 다르면 "
                         "f_flash·f_tip 이 함께 바뀐다 — 분류 축의 첫 재료다. "
                         "파일명에 _<기체> 가 붙는다.")
    ap.add_argument("--sw", default="",
                    help="⭐스위치를 **비트로 직접** 준다: R<0|1>D<0|1>E<0|1>F<0|1> — "
                         "굴절·회절·모서리회절·확산반사. 예: --sw R1D0E0F1. "
                         "--physics·--only·--stock 과 배타적이고, 깊이는 --max-depth 로. "
                         "⚠소스 실측: E 는 D=1 일 때만 뜻이 있다(sb_candidate_generator:338). "
                         "파일명에 _sw<비트> 가 붙는다.")
    ap.add_argument("--stock", action="store_true",
                    help="⭐PathSolver 를 **순정 기본값 그대로** 돌린다 — refraction=True · "
                         "diffraction=False · edge=False · max_depth=3 · diffuse=False. "
                         "우리 «물리 끔» 판(셋 다 끔·깊이 1·확산 켬)과도, «켬» 판과도 다른 "
                         "제3의 조합이다. 파일명에 _stockdef 가 붙는다.")
    ap.add_argument("--only", default="",
                    help="⭐물리 스위치를 **하나씩** 켠다 — refr | diffr | edge | depth3. "
                         "--physics 는 넷을 한꺼번에 켜서 귀속이 불가능하다. "
                         "파일명에 _only<이름> 이 붙는다.")
    ap.add_argument("--plane-wave", action="store_true",
                    help="⭐우리 팔을 **평면파**(range_m=None · 무한거리 등가)로 돌린다. "
                         "구면파와의 차이가 근접장 곡률의 몫이므로, 나딧 잔여가 «근접장 탓이냐 "
                         "격자 churn 탓이냐» 를 가르는 단일축이 된다(RESUME 미해결 4번). "
                         "파일명에 _pw 가 붙는다.")
    ap.add_argument("--n-poses", type=int, default=0,
                    help="⭐슬로타임 자세 수. 0 이면 원장값(report07_three_engines:_meta.n = 4096). "
                         "박자 FFT 분해능 = prf/n 이라 4096 은 4.89 Hz 이고, h1/h2 판별창(±18 Hz)에 "
                         "3.7 빈이 들어간다. 원래 리포트 16 은 8192 를 썼다(2.45 Hz). "
                         "⛔줄이면 안 된다 — 2048 이면 판별창이 1.8 빈이라 고조파비가 안 나온다. "
                         "0 이 아니면 파일명에 _n<N> 이 붙는다.")
    ap.add_argument("--max-depth", type=int, default=0,
                    help="⭐PathSolver 의 반사 깊이를 직접 준다. 0 이면 기존 규칙 "
                         "(--physics 면 3, 아니면 1). 물리 스위치와 깊이를 **가르는** 인자다 — "
                         "전에는 --physics 하나에 묶여 있어 귀속이 불가능했다. "
                         "0 이 아니면 파일명에 _d<N> 이 붙는다.")
    ap.add_argument("--az-deg", type=float, default=float("nan"),
                    help="⭐방위각 [°]. 비우면 원장값(report07_three_engines:_meta.az_deg). "
                         "지금까지 모든 판이 방위 한 자리에서만 잰 것이라 «다른 방위에서도 "
                         "같은 결론이 서는가» 를 시험한 적이 없다. 파일명에 _az<N> 이 붙는다.")
    ap.add_argument("--div", type=int, default=0,
                    help="⭐우리 커널의 표면 격자 간격을 λ/DIV 로 정한다. 0 이면 규약값 12. "
                         "상한 위 누설이 격자 표본화에서 오는지 가르는 축이다 — 촘촘하게 "
                         "하면 내려가야 한다. 계산량은 대략 DIV² 로 는다. "
                         "0 이 아니면 파일명에 _div<N> 이 붙는다. (PathSolver 에는 없는 축)")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    analyse() if a.merge else run(a)


if __name__ == "__main__":
    main()
