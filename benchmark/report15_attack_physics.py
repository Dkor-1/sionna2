# -*- coding: utf-8 -*-
"""
report15_attack_physics.py — **적대검증 렌즈 2 : 물리·공정성**
================================================================================

report15 판정("스톡 Sionna 는 위상 스텝 + 재추적으로 블레이드 마이크로도플러를 낸다,
단 확산 채널에서만")을 물리·공정성 쪽에서 때린다. 다섯 물음이다.

  Q1 ⭐ Sionna 를 부당하게 깎았는가 — **회절·확산 기본값이 꺼져 있는데 켜고도 해봤는가**
      (이 저장소는 "스톡 Sionna 에 회절이 없다" 고 했다가 철회한 이력이 있다 — RETRACTION_LOG R6)
  Q2 근거리 조건이 정말 Sionna 에 유리하게 설정됐나 — 더 유리하게 할 여지(더 가깝게·spp↑·max_depth↑)
  Q3 PO 대조군이 공정한가 — 근거리에서 평면파를 썼다면 PO 가 부당하게 불리하다
  Q4 로터 위상 스텝이 물리적으로 옳은가 — 블레이드 대칭·회전방향·스텝 수(에일리어싱)
  Q5 이 결과가 뒤집을 기존 저장소 서술은 무엇인가

방법: **원래 격자 하네스(report15_sweep_matrice4e)의 함수를 그대로 불러** 솔버 플래그만 바꾼다.
관측량 정의·씬 조립·경로 분류가 한 글자도 갈라지지 않아야 "플래그 하나 때문" 이라고 말할 수 있다.

⛔ src/drones.py · src/drone_cad.py 는 읽기만. 기존 산출물 덮어쓰기 금지(신규 파일만).
⛔ 숫자 손입력 금지 — 전부 계산해서 JSON 에 담는다.
"""
from __future__ import annotations

import ast
import json
import math
import os
import re
import subprocess
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore", category=RuntimeWarning)

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCRATCH_BASE = ("/tmp/claude-1015/-workspace/"
                "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")
os.environ.setdefault("REPORT15_SCRATCH", os.path.join(SCRATCH_BASE, "r15attack"))

OUT_JSON = os.path.join(ROOT, "outputs", "report15_attack_physics.json")

#  GPU 를 안 쓰는 모듈 (분석 헬퍼 · 기하기준)
import report15_verdict as VD                                          # noqa: E402
import report15_verdict_geomref as GR                                  # noqa: E402

#  ⚠ 아래 import 가 gpu.pick() + mitsuba 를 올린다. 반드시 SCRATCH 설정 뒤.
import report15_sweep_matrice4e as SW                                  # noqa: E402
import sionna.rt as rt                                                 # noqa: E402
import inspect                                                         # noqa: E402

from drones import DRONES, rotor_layout                                # noqa: E402
from materials import gamma_bulk, gamma_po                             # noqa: E402

N_PHASE = 64
NY = N_PHASE // 2
SPP_BASE = 2_048_000_000          # 본 격자가 쓴 값(파일에서 읽어 검증한다)
SPP_MAX = 4_096_000_000           # samples_per_src 는 uint32 — 이 위로는 못 간다

#  ⭐ 솔버 구성 사다리. base_prod / base_spec 가 원 격자 재현이고 나머지가 공격이다.
CONFIGS = [
    ("base_prod",   dict(diffuse=True,  diffr=False, edge=False, refr=False, depth=1), (1, 2, 3)),
    ("base_spec",   dict(diffuse=False, diffr=False, edge=False, refr=False, depth=1), (1,)),
    ("spec_diffr",  dict(diffuse=False, diffr=True,  edge=True,  refr=False, depth=1), (1,)),
    ("prod_diffr",  dict(diffuse=True,  diffr=True,  edge=True,  refr=False, depth=1), (1, 2, 3)),
    ("prod_refr",   dict(diffuse=True,  diffr=False, edge=False, refr=True,  depth=1), (1, 2)),
    ("prod_d3",     dict(diffuse=True,  diffr=False, edge=False, refr=False, depth=3), (1, 2)),
    ("prod_sppmax", dict(diffuse=True,  diffr=False, edge=False, refr=False, depth=1,
                         spp=SPP_MAX), (1, 2)),
]
#  근거리 극한(0.5 m)은 부분집합만 — "더 유리하게 할 여지" 를 재는 칸이다
CONFIGS_NEAR = ["base_prod", "base_spec", "spec_diffr", "prod_diffr"]

CELLS = {
    "matrice4e": [("1/hot", 1.0, 0.0, 0.0), ("1/disc", 1.0, 0.0, 75.0),
                  ("0.5/hot", 0.5, 0.0, 0.0)],
    "mini2":     [("1/hot", 1.0, 0.0, 0.0), ("1/disc", 1.0, 0.0, 75.0)],
}
ALIAS_CELL = ("1/hot", 1.0, 0.0, 0.0)      # 에일리어싱 실측(128 위상)을 돌릴 칸


def _f(o):
    """NaN/inf → None (JSON 안전)."""
    if isinstance(o, dict):
        return {k: _f(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_f(v) for v in o]
    if isinstance(o, (np.floating, float)):
        o = float(o)
        return None if not math.isfinite(o) else o
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def switch_airframe(key: str):
    """SW 모듈의 기체를 갈아끼운다 (report15_verdict_grid_mini2.py 와 같은 방식)."""
    SW.KEY = key
    SW._SPEC = DRONES[key]
    SW._DIRS = [r["dir"] for r in rotor_layout(SW._SPEC)]
    return SW._SPEC


# --------------------------------------------------------------------------- #
#  §0  솔버 플래그 감사 — report15 가 실제로 무엇을 켜고 껐나 (소스를 AST 로 판독)
# --------------------------------------------------------------------------- #
def sec0_flag_census() -> dict:
    """PathSolver 호출을 소스에서 찾아 **넘긴 키워드**를 그대로 뽑는다. 주장이 아니라 판독이다."""
    sig = inspect.signature(rt.PathSolver.__call__)
    defaults = {k: (None if v.default is inspect._empty else v.default)
                for k, v in sig.parameters.items() if k not in ("self", "scene")}
    files = []
    for sub in ("benchmark", "src"):
        d = os.path.join(ROOT, sub)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py") and (fn.startswith("report15_") or sub == "src"):
                files.append(os.path.join(sub, fn))
    calls = []
    for rel in files:
        p = os.path.join(ROOT, rel)
        try:
            src = open(p, encoding="utf-8").read()
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            #  rt.PathSolver()(...) 는 Call(func=Call(func=Attribute(PathSolver)))
            inner = f if isinstance(f, ast.Call) else None
            nm = None
            if inner is not None:
                g = inner.func
                nm = g.attr if isinstance(g, ast.Attribute) else getattr(g, "id", None)
            if nm != "PathSolver":
                continue
            kw = {}
            for k in node.keywords:
                try:
                    kw[k.arg] = ast.literal_eval(k.value)
                except Exception:
                    kw[k.arg] = ast.unparse(k.value)
            calls.append(dict(file=rel, line=int(node.lineno), kwargs=kw))
    #  ⚠ 이 공격 스크립트 자신은 세지 않는다 — 감사 대상은 **판정을 낸 코드**다.
    SELF = "benchmark/" + os.path.basename(__file__)
    r15 = [c for c in calls
           if c["file"].startswith("benchmark/report15_") and c["file"] != SELF]
    def _off(c, k):
        return (k not in c["kwargs"]) or (c["kwargs"][k] in (False, "False"))
    return dict(
        signature_defaults={k: (v if isinstance(v, (int, float, bool, str, type(None)))
                                else str(v)) for k, v in defaults.items()},
        n_pathsolver_calls_total=len(calls),
        n_pathsolver_calls_report15=len(r15),
        calls=calls,
        report15_diffraction_never_enabled=bool(all(_off(c, "diffraction") for c in r15)),
        report15_edge_diffraction_never_enabled=bool(
            all(_off(c, "edge_diffraction") for c in r15)),
        report15_diffuse_enabled_somewhere=bool(any(
            c["kwargs"].get("diffuse_reflection") not in (None, False, "False") for c in r15)),
        report15_refraction_explicitly_off=bool(all(
            c["kwargs"].get("refraction") in (False, "False") for c in r15)),
        report15_max_depth_values=sorted({str(c["kwargs"].get("max_depth")) for c in r15}),
        note_ko=("Sionna 2.0.1 PathSolver 기본값은 diffraction=False·edge_diffraction=False 다. "
                 "report15 의 어느 호출도 이 둘을 켜지 않았다 — 즉 판정은 UTD 회절이 꺼진 "
                 "상태에서 나왔다. 확산(diffuse_reflection)은 'prod' 채널에서 켜져 있었다."))


# --------------------------------------------------------------------------- #
#  §1  구성 사다리 — 같은 하네스, 플래그만 바꿔서 재추적
# --------------------------------------------------------------------------- #
def trace_cfg(scene, cfg, spp, seed, id2grp):
    """SW.trace 와 같은 관측량을 내되 솔버 플래그를 사다리에서 받는다."""
    t0 = time.time()
    p = rt.PathSolver()(scene, max_depth=int(cfg["depth"]), los=True,
                        specular_reflection=True,
                        diffuse_reflection=bool(cfg["diffuse"]),
                        diffraction=bool(cfg["diffr"]),
                        edge_diffraction=bool(cfg["edge"]),
                        refraction=bool(cfg["refr"]),
                        samples_per_src=int(spp),
                        max_num_paths_per_src=SW.MAX_PATHS, seed=int(seed))
    ar = np.asarray(p.a[0]); ai = np.asarray(p.a[1])
    a = (ar + 1j * ai).reshape(-1, ar.shape[-1])[0]
    P = int(a.shape[0])
    out = dict(n=0, n_prop=0, hr=0.0, hi=0.0, hpr=0.0, hpi=0.0,
               inc=None, inc_prop=None, sec=0.0, n_raw=P)
    if P == 0:
        out["sec"] = float(time.time() - t0)
        return out
    tau = np.asarray(p.tau, dtype=np.float64).reshape(-1, P)[0]
    O = np.asarray(p.objects)[:, 0, 0, :]
    hit = (O != SW.NO_OBJ).any(axis=0)
    ph = np.exp(-1j * 2.0 * np.pi * SW.FC * tau)
    prop_ids = np.array([oid for oid, g in id2grp.items() if g == "prop"], dtype=np.int64)
    pm = np.isin(O, prop_ids).any(axis=0) if prop_ids.size else np.zeros(P, bool)
    s = complex(np.sum(a[hit] * ph[hit])) if hit.any() else 0j
    sp = complex(np.sum(a[pm] * ph[pm])) if pm.any() else 0j
    out.update(n=int(hit.sum()), n_prop=int(pm.sum()),
               hr=float(s.real), hi=float(s.imag),
               hpr=float(sp.real), hpi=float(sp.imag),
               inc=(float(10 * np.log10(float(np.sum(np.abs(a[hit]) ** 2)) + 1e-300))
                    if hit.any() else None),
               inc_prop=(float(10 * np.log10(float(np.sum(np.abs(a[pm]) ** 2)) + 1e-300))
                         if pm.any() else None),
               sec=float(time.time() - t0))
    return out


def run_ladder(key, cells, n_phase=N_PHASE, configs=CONFIGS, progress=None) -> dict:
    """위상 바깥 루프(씬 조립이 가장 비싸다) → 칸 → 구성 → 시드."""
    spec = switch_airframe(key)
    period = 360.0 / int(spec.prop_blades)
    phis = np.arange(n_phase) * (period / n_phase)
    store = {}
    for cname, ck, az, el in [(c[0], c[1], c[2], c[3]) for c in cells]:
        for cfgname, cfg, seeds in configs:
            if ck < 1.0 and cfgname not in CONFIGS_NEAR:
                continue
            store[f"{cname}|{cfgname}"] = dict(
                cell=cname, range_m=float(ck), az_deg=float(az), el_deg=float(el),
                config=cfgname, cfg=dict(cfg), seeds=list(seeds),
                spp=int(cfg.get("spp", SPP_BASE)),
                hpr=[[0.0] * len(seeds) for _ in range(n_phase)],
                hpi=[[0.0] * len(seeds) for _ in range(n_phase)],
                hr=[[0.0] * len(seeds) for _ in range(n_phase)],
                hi=[[0.0] * len(seeds) for _ in range(n_phase)],
                n=[[0] * len(seeds) for _ in range(n_phase)],
                n_prop=[[0] * len(seeds) for _ in range(n_phase)],
                inc_prop=[[None] * len(seeds) for _ in range(n_phase)],
                sec=[[0.0] * len(seeds) for _ in range(n_phase)])
    t0 = time.time()
    ntr = 0
    for i, phd in enumerate(phis):
        scene, dd = SW.build_posed_scene(float(phd), f"A{i:03d}")
        g2 = SW.id_to_group(scene)
        for cname, ck, az, el in cells:
            SW.place(scene, az, el, ck)
            for cfgname, cfg, seeds in configs:
                if ck < 1.0 and cfgname not in CONFIGS_NEAR:
                    continue
                B = store[f"{cname}|{cfgname}"]
                for j, sd in enumerate(seeds):
                    r = trace_cfg(scene, cfg, cfg.get("spp", SPP_BASE), sd, g2)
                    ntr += 1
                    for k in ("hr", "hi", "hpr", "hpi", "n", "n_prop", "inc_prop", "sec"):
                        B[k][i][j] = r[k]
        SW.drop(dd)
        if progress and (i % 8 == 0 or i == n_phase - 1):
            print(f"   [{key}] 위상 {i+1}/{n_phase}  추적 {ntr}  "
                  f"{time.time()-t0:.0f}s", flush=True)
    return dict(airframe=key, name=spec.name, n_phase=int(n_phase),
                phases_deg=[float(x) for x in phis], period_deg=float(period),
                n_traces=int(ntr), seconds=float(time.time() - t0), blocks=store)


# --------------------------------------------------------------------------- #
#  §2  분석 — 조화 빗 · 연속성 · 기하기준 대조
# --------------------------------------------------------------------------- #
#  ⚠ 자세를 다시 만드는 데 기체당 2~3 초/포즈가 든다. 칸마다 다시 만들면 (칸수×64) 번이라
#    분석이 추적보다 몇 배 오래 걸린다 — 포즈 목록은 **기체당 한 번만** 만들어 재사용한다.
_POSE_CACHE: dict = {}


def _poses(key, n_phase=N_PHASE):
    if key not in _POSE_CACHE:
        spec = DRONES[key]
        period = 360.0 / int(spec.prop_blades)
        phis = np.arange(n_phase) * (period / n_phase)
        t0 = time.time()
        _POSE_CACHE[key] = [GR.prop_vertices(spec, float(p)) for p in phis]
        print(f"   [{key}] 기하기준용 프롭 자세 {n_phase} 개 생성 {time.time()-t0:.0f}s",
              flush=True)
    return _POSE_CACHE[key]


def geom_comb(key, az, el, rng, n_phase=N_PHASE) -> dict:
    """같은 메쉬로 왕복 위상만 더한 기준 빗 (report15_verdict_geomref 의 함수 재사용)."""
    P = _poses(key, n_phase)
    tx, rx = GR.antennas(az, el, rng)
    z = GR.geom_wave(P, tx, rx)
    a, edge, peak = GR.comb(z)
    return dict(harm_abs=[float(x) for x in a], edge_bin=edge, peak_bin=peak,
                n_prop_vertices=int(P[0].shape[0]))


def comb_cos(a, b) -> float:
    """두 빗(조화 크기)의 코사인 유사도 — 규모에 불변."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    n = min(a.size, b.size)
    a, b = a[:n], b[:n]
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else 0.0


def _flash_hz(phys) -> float:
    """⚠ SW.sec0_physics 는 키를 `flash_hz` 로 쓴다(판정 JSON 쪽은 `f_flash_hz`).
    두 이름을 다 받는다 — 이름 하나 때문에 실험이 죽지 않도록."""
    for k in ("f_flash_hz", "flash_hz"):
        if k in phys:
            return float(phys[k])
    raise KeyError("f_flash_hz/flash_hz 둘 다 없다")


def analyse_block(B, phys, geo) -> dict:
    """한 블록(칸×구성) → 판정 재료. 채널은 prop 과 all 둘 다."""
    out = dict(cell=B["cell"], config=B["config"], range_m=B["range_m"],
               el_deg=B["el_deg"], spp=B["spp"], cfg=B["cfg"], seeds=B["seeds"],
               sec_per_trace=float(np.mean(B["sec"])))
    n_arr = np.asarray(B["n"], float)
    np_arr = np.asarray(B["n_prop"], float)
    out["n_paths_mean"] = float(np.mean(n_arr))
    out["n_prop_mean"] = float(np.mean(np_arr))
    out["frac_phase_with_any_path"] = float(np.mean(n_arr.min(axis=1) > 0))
    out["frac_phase_with_prop_path"] = float(np.mean(np_arr.min(axis=1) > 0))
    for ch, (re_k, im_k) in (("prop", ("hpr", "hpi")), ("all", ("hr", "hi"))):
        z = np.asarray(B[re_k], float) + 1j * np.asarray(B[im_k], float)
        A = np.abs(z)
        zm = z.mean(axis=1)
        d = dict(level_db=float(20 * np.log10(np.mean(A) + 1e-300)),
                 nonzero_phase_frac=float(np.mean(np.abs(zm) > 0)))
        if np.all(np.abs(zm) == 0):
            out[ch] = d | dict(empty=True)
            continue
        H = VD.harm_seeded(z)
        E = VD.edge_bin(H)
        ptp = float(np.ptp(20 * np.log10(np.abs(zm) + 1e-300)))
        fflash = _flash_hz(phys)
        ftip_bins = float(phys["f_tip_hz"] * math.cos(math.radians(B["el_deg"])) / fflash)
        d.update(empty=False,
                 modulation_ptp_db=ptp,
                 ac_over_noise_db=H["total_ac_over_noise_db"],
                 noise_degenerate=bool(H["noise_degenerate"]),
                 harm_abs=[float(x) for x in H["harm_abs"]],
                 peak_bin=E["peak_bin"], edge_bin=E["edge_bin"],
                 f_edge_hz=(float(E["edge_bin"] * fflash) if E["edge_bin"] else None),
                 f_tip_pred_hz=float(phys["f_tip_hz"] * math.cos(math.radians(B["el_deg"]))),
                 ftip_in_bins=ftip_bins,
                 edge_over_ftip=(float(E["edge_bin"] / ftip_bins)
                                 if E["edge_bin"] and ftip_bins > 0 else None),
                 comb_cos_vs_geom=comb_cos(H["harm_abs"], geo["harm_abs"]),
                 nyquist_bin=int(NY),
                 edge_at_nyquist=bool(E["edge_bin"] == NY) if E["edge_bin"] else False,
                 z_mean_re=[float(x) for x in zm.real],
                 z_mean_im=[float(x) for x in zm.imag])
        out[ch] = d
    return out


def compare_to_base(blocks_an, cellname, base="base_prod") -> dict:
    """구성 사다리를 기준(base_prod) 대비로 정리 — 무엇이 얼마나 바뀌었나."""
    b = blocks_an.get(f"{cellname}|{base}")
    if b is None:
        return {}
    rows = {}
    for k, a in blocks_an.items():
        if not k.startswith(cellname + "|"):
            continue
        cfg = k.split("|", 1)[1]
        r = dict(config=cfg)
        for ch in ("prop", "all"):
            A, Bs = a.get(ch, {}), b.get(ch, {})
            if A.get("empty", True) or Bs.get("empty", True):
                r[ch] = dict(empty_self=bool(A.get("empty", True)),
                             empty_base=bool(Bs.get("empty", True)))
                continue
            za = np.asarray(A["z_mean_re"]) + 1j * np.asarray(A["z_mean_im"])
            zb = np.asarray(Bs["z_mean_re"]) + 1j * np.asarray(Bs["z_mean_im"])
            r[ch] = dict(
                d_level_db=float(A["level_db"] - Bs["level_db"]),
                d_ptp_db=float(A["modulation_ptp_db"] - Bs["modulation_ptp_db"]),
                waveform_ac_corr=VD.ac_corr(za, zb),
                comb_cos_vs_base=comb_cos(A["harm_abs"], Bs["harm_abs"]),
                edge_bin=A["edge_bin"], edge_bin_base=Bs["edge_bin"],
                comb_cos_vs_geom=A["comb_cos_vs_geom"],
                comb_cos_vs_geom_base=Bs["comb_cos_vs_geom"],
                ac_over_noise_db=A["ac_over_noise_db"],
                ac_over_noise_db_base=Bs["ac_over_noise_db"],
                edge_over_ftip=A["edge_over_ftip"],
                edge_over_ftip_base=Bs["edge_over_ftip"])
        r["d_n_paths_frac"] = float((a["n_paths_mean"] - b["n_paths_mean"])
                                    / (b["n_paths_mean"] + 1e-300))
        r["frac_phase_with_prop_path"] = a["frac_phase_with_prop_path"]
        r["frac_phase_with_prop_path_base"] = b["frac_phase_with_prop_path"]
        rows[cfg] = r
    return rows


# --------------------------------------------------------------------------- #
#  §3  에일리어싱 실측 — 128 위상으로 돌려 64 위상 빗과 대조
# --------------------------------------------------------------------------- #
def run_alias(key, cell, n_hi=128) -> dict:
    """같은 칸을 128 위상(= 회전당 256 스텝)으로 돌린다. 64 격자는 그 부분집합이므로
    **간추린 빗**과 원래 빗이 같으면 접힘(aliasing)이 없다는 직접 증거다."""
    spec = switch_airframe(key)
    cname, ck, az, el = cell
    period = 360.0 / int(spec.prop_blades)
    phis = np.arange(n_hi) * (period / n_hi)
    seeds = (1, 2)
    cfg = dict(diffuse=True, diffr=False, edge=False, refr=False, depth=1)
    Z = np.zeros((n_hi, len(seeds)), complex)
    ZA = np.zeros((n_hi, len(seeds)), complex)
    t0 = time.time()
    for i, phd in enumerate(phis):
        scene, dd = SW.build_posed_scene(float(phd), f"L{i:03d}")
        g2 = SW.id_to_group(scene)
        SW.place(scene, az, el, ck)
        for j, sd in enumerate(seeds):
            r = trace_cfg(scene, cfg, SPP_BASE, sd, g2)
            Z[i, j] = complex(r["hpr"], r["hpi"])
            ZA[i, j] = complex(r["hr"], r["hi"])
        SW.drop(dd)
        if i % 16 == 0:
            print(f"   [alias {key}] {i+1}/{n_hi}  {time.time()-t0:.0f}s", flush=True)
    out = dict(airframe=key, cell=cname, n_phase_hi=int(n_hi), seeds=list(seeds),
               seconds=float(time.time() - t0))
    for ch, X in (("prop", Z), ("all", ZA)):
        H_hi = VD.harm_seeded(X)
        H_lo = VD.harm_seeded(X[::2])          # 64 격자 = 128 격자의 격간추출
        a_hi = np.asarray(H_hi["harm_abs"], float)[:NY]
        a_lo = np.asarray(H_lo["harm_abs"], float)[:NY]
        E_hi, E_lo = VD.edge_bin(H_hi), VD.edge_bin(H_lo)
        #  접힘이 있으면 64 격자 빈이 128 격자 대비 부풀어 오른다
        rel = np.abs(a_lo - a_hi) / (a_hi + 1e-300)
        tot_hi = float(np.sum(np.asarray(H_hi["harm_abs"], float) ** 2))
        above = float(np.sum(np.asarray(H_hi["harm_abs"], float)[NY:] ** 2))
        out[ch] = dict(
            comb_cos_64_vs_128=comb_cos(a_lo, a_hi),
            max_rel_diff_first32=float(np.max(rel)),
            median_rel_diff_first32=float(np.median(rel)),
            edge_bin_128=E_hi["edge_bin"], edge_bin_64=E_lo["edge_bin"],
            energy_frac_above_bin32=float(above / (tot_hi + 1e-300)),
            harm_abs_128=[float(x) for x in H_hi["harm_abs"]],
            harm_abs_64=[float(x) for x in H_lo["harm_abs"]])
    return out


# --------------------------------------------------------------------------- #
#  §4  Q4 운동학 — 대칭·회전방향·스텝 수
# --------------------------------------------------------------------------- #
def sec4_kinematics() -> dict:
    r = {}
    for key in ("mini2", "matrice4e"):
        spec = DRONES[key]
        lay = rotor_layout(spec)
        dirs = [int(x["dir"]) for x in lay]
        f_rev = float(spec.hover_rpm) / 60.0
        nb = int(spec.prop_blades)
        f_flash = nb * f_rev
        r_tip = float(spec.prop_dia_mm) / 2000.0
        lam = SW.LAM
        f_tip = 2.0 * (2.0 * math.pi * f_rev * r_tip) / lam
        #  ⭐ 스텝수 조건: 한 주기 N 표본의 나이키스트 빈 = N/2. f_tip 이 그 안에 들어야 한다.
        ftip_bins = f_tip / f_flash
        n_min = int(math.ceil(2.0 * ftip_bins))
        #  정반사 글린트의 각폭 — 블레이드(길이 L)의 회절한계 ≈ λ/(2L) [rad]
        L = r_tip
        flash_rad = lam / (2.0 * L)
        step_deg = (360.0 / nb) / N_PHASE
        r[key] = dict(
            name=spec.name, n_blades=nb, rotor_dirs=dirs,
            n_rotors=len(dirs), n_cw=int(sum(1 for d in dirs if d > 0)),
            n_ccw=int(sum(1 for d in dirs if d < 0)),
            all_same_magnitude_phase=True,
            geometric_period_deg=360.0 / nb,
            f_rev_hz=f_rev, f_flash_hz=f_flash, f_tip_hz=f_tip,
            ftip_in_flash_bins=ftip_bins,
            n_phase_used=int(N_PHASE), nyquist_bin=int(NY),
            n_steps_min_for_ftip=n_min,
            alias_margin=float(NY / ftip_bins),
            aliased=bool(ftip_bins > NY),
            bin_granularity_frac_of_ftip=float(1.0 / ftip_bins),
            ftip_tolerance_frac=float(VD.TH["ftip_tol"]),
            granularity_exceeds_tolerance=bool(1.0 / ftip_bins > VD.TH["ftip_tol"]),
            specular_flash_halfwidth_rad=float(flash_rad),
            specular_flash_halfwidth_deg=float(math.degrees(flash_rad)),
            phase_step_deg=float(step_deg),
            samples_across_specular_flash=float(math.degrees(flash_rad) / step_deg),
            v_tip_ms=float(2.0 * math.pi * f_rev * r_tip),
            note_ko=("회전당 스텝 = 2×N_PHASE (한 주기 180° 를 N 등분하므로). "
                     "f_tip 은 왕복 도플러의 상한이고, 진폭변조(글린트)는 그보다 넓게 퍼질 수 "
                     "있으므로 나이키스트 여유와 글린트 각폭을 함께 본다."))
    return r


# --------------------------------------------------------------------------- #
#  §5  Q3 PO 공정성 — 평면파 vs 구면파, 재질, 가림
# --------------------------------------------------------------------------- #
def sec5_po_fairness() -> dict:
    out = dict(note_ko=("PO 대조군이 근거리에서 평면파를 썼는지 **파일에서** 확인하고, "
                        "평면파 팔이 실제로 얼마나 다른지 수치로 잰다."))
    #  (1) 격자 PO 가 무엇을 썼나 — 파일 판독
    pg = os.path.join(ROOT, "outputs", "report15_verdict_po_grid.json")
    if os.path.exists(pg):
        D = json.load(open(pg))
        src = open(os.path.join(ROOT, "benchmark", "report15_verdict_po_grid.py"),
                   encoding="utf-8").read()
        out["grid_po"] = dict(
            engine=D["meta"]["engine"],
            wavefront_kwarg_in_source=sorted(set(re.findall(r'wavefront="(\w+)"', src))),
            uses_true_txrx_coords=bool("tx_xyz" in json.dumps(
                D["airframes"][list(D["airframes"])[0]]["matched"]["blocks"]
                [list(D["airframes"][list(D["airframes"])[0]]["matched"]["blocks"])[0]])),
            ranges_m=D["meta"]["ranges_m"],
            selfcheck_all_reproduce=D.get("selfcheck", {}).get("all_reproduce"),
            plane_wave_used=bool("plane" in re.findall(r'wavefront="(\w+)"', src)))
    #  (2) 평면파 팔이 실제로 얼마나 다른가 — 기존 po_control 저장 파형에서 직접 계산
    pc = os.path.join(ROOT, "outputs", "report15_po_control.json")
    if os.path.exists(pc):
        D = json.load(open(pc))
        rows = {}
        for key, A in D["airframes"].items():
            def wav(name):
                blk = (A["arms"].get(name) or {}).get("full128") or {}
                w = blk.get("wave") or {}
                if "amp_db" not in w:
                    return None
                return (10.0 ** (np.asarray(w["amp_db"], float) / 20.0)
                        * np.exp(1j * np.radians(np.asarray(w["phase_deg"], float))))
            for stem in ("ref", "hot"):
                pl, sp, sb = (wav(f"{stem}/po_plane_mono"),
                              wav(f"{stem}/po_spherical_mono"),
                              wav(f"{stem}/po_spherical_bistatic"))
                if pl is None or sb is None:
                    continue
                rows[f"{key}/{stem}"] = dict(
                    range_m=float(D["meta"]["range_m"]),
                    plane_vs_spherical_ac_corr=VD.ac_corr(pl, sb),
                    plane_ptp_db=float(np.ptp(20 * np.log10(np.abs(pl) + 1e-300))),
                    spherical_ptp_db=float(np.ptp(20 * np.log10(np.abs(sb) + 1e-300))),
                    ptp_diff_db=float(np.ptp(20 * np.log10(np.abs(pl) + 1e-300))
                                      - np.ptp(20 * np.log10(np.abs(sb) + 1e-300))),
                    mono_vs_bistatic_ac_corr=(VD.ac_corr(sp, sb) if sp is not None else None),
                    comb_cos_plane_vs_spherical=comb_cos(
                        np.abs(np.fft.fft(pl - pl.mean()))[1:65],
                        np.abs(np.fft.fft(sb - sb.mean()))[1:65]))
            #  가림 있는 팔(SBR)과의 대조
            for stem in ("ref", "hot"):
                sb = wav(f"{stem}/po_spherical_bistatic")
                for dv in ("sbr_div12", "sbr_div24", "sbr_div48"):
                    s = wav(f"{stem}/{dv}")
                    if s is None or sb is None:
                        continue
                    rows.setdefault(f"{key}/{stem}", {})[f"po_vs_{dv}_ac_corr"] = \
                        VD.ac_corr(sb, s)
        out["plane_vs_spherical"] = rows
    #  (3) 재질 비대칭 — Sionna 는 벌크 프레넬, PO 는 얇은날개 실효 Γ
    mats = {}
    for mk in ("prop_plastic", "plastic", "metal", "carbon"):
        try:
            mats[mk] = dict(gamma_bulk=float(gamma_bulk(mk, SW.FC)),
                            gamma_po=float(gamma_po(mk, SW.FC)))
        except Exception as e:
            mats[mk] = dict(error=str(e))
    out["material_gamma"] = mats
    return out


# --------------------------------------------------------------------------- #
#  §6  Q5 — 이 결과가 건드리는 저장소 서술을 실제로 찾는다
# --------------------------------------------------------------------------- #
def sec6_repo_claims() -> dict:
    pats = [
        ("정반사_없음", r"정반사(가|는)?\s*(원리적으로\s*)?(없|안 )"),
        ("글린트_없음", r"글린트.{0,20}(없|불가|안 )"),
        ("스톡_불가", r"스톡.{0,30}(못|불가|없)"),
        ("회절", r"회절"),
        ("확산채널만", r"확산.{0,10}채널"),
    ]
    hits = {}
    for nm, pat in pats:
        try:
            r = subprocess.run(["grep", "-rInE", pat, "--include=*.md", "--include=*.py",
                                "docs", "benchmark", "README.md"],
                               cwd=ROOT, capture_output=True, text=True, timeout=120)
            lines = [l for l in r.stdout.splitlines() if l.strip()]
        except Exception as e:
            lines = [f"grep 실패: {e}"]
        hits[nm] = dict(pattern=pat, n=len(lines), sample=lines[:25])
    return hits


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    J = dict(meta=dict(
        script="benchmark/report15_attack_physics.py",
        role="report15 판정에 대한 적대검증 렌즈 2 — 물리·공정성",
        questions_ko=["Q1 회절·확산 켜고도 해봤는가", "Q2 근거리가 정말 유리하게 설정됐나",
                      "Q3 PO 대조군이 공정한가(평면파?)", "Q4 위상 스텝이 물리적으로 옳은가",
                      "Q5 뒤집을 저장소 서술"],
        target_outputs=["outputs/report15_verdict.json",
                        "outputs/report15_sionna_sweep_matrice4e.json",
                        "outputs/report15_verdict_grid_mini2.json"],
        fc_hz=SW.FC, lambda_m=SW.LAM, baseline_m=SW.BASELINE_M,
        n_phase=int(N_PHASE), spp_base=int(SPP_BASE), spp_max=int(SPP_MAX),
        sionna_version=__import__("sionna").__version__,
        gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
        gpu_status_at_start=SW.gpu_status(),
        stamp=time.strftime("%Y-%m-%d %H:%M:%S")))

    #  ⭐ 이어하기 — 앞선 실행이 남긴 사다리(GPU 로 15 분씩 걸린다)는 다시 돌지 않는다.
    PREV = {}
    if os.path.exists(OUT_JSON):
        try:
            PREV = json.load(open(OUT_JSON))
            print(f"   (이어하기) 기존 산출물에서 사다리 재사용: "
                  f"{sorted(PREV.get('q1q2_ladder', {}).keys())}")
        except Exception as e:
            print("   (이어하기 실패, 처음부터)", e)
            PREV = {}

    def save():
        J["meta"]["seconds_so_far"] = float(time.time() - t0)
        with open(OUT_JSON, "w") as f:
            json.dump(_f(J), f, ensure_ascii=False)

    print("§0  솔버 플래그 감사")
    J["q1_flag_census"] = sec0_flag_census()
    J["meta"]["resumed_from_previous_run"] = bool(PREV.get("q1q2_ladder"))
    print("   diffraction 한 번도 안 켬:",
          J["q1_flag_census"]["report15_diffraction_never_enabled"],
          "| report15 PathSolver 호출", J["q1_flag_census"]["n_pathsolver_calls_report15"])
    save()

    print("\n§4  운동학 (대칭·회전방향·스텝수·에일리어싱 해석)")
    J["q4_kinematics"] = sec4_kinematics()
    save()

    print("\n§3  PO 공정성 (파일 판독 + 수치)")
    J["q3_po_fairness"] = sec5_po_fairness()
    save()

    print("\n§5  저장소 서술 수색")
    J["q5_repo_claims"] = sec6_repo_claims()
    save()

    #  ⭐ 본 실험
    J["q1q2_ladder"] = {}
    J["q1q2_analysis"] = {}
    J["q1q2_vs_base"] = {}
    for key in ("matrice4e", "mini2"):
        prev_L = (PREV.get("q1q2_ladder") or {}).get(key)
        if prev_L and prev_L.get("n_traces"):
            print(f"\n§1  구성 사다리 — {key}  (기존 {prev_L['n_traces']} 추적 재사용)")
            L = prev_L
        else:
            print(f"\n§1  구성 사다리 — {key}")
            L = run_ladder(key, CELLS[key], progress=True)
        J["q1q2_ladder"][key] = L
        save()                       # ⭐ 추적 자료를 **분석 전에** 먼저 굳힌다
        #  physics 는 기체 전환 뒤 다시 계산해야 한다
        try:
            phys = SW.sec0_physics(N_PHASE)
            an = {}
            for k, B in L["blocks"].items():
                geo = geom_comb(key, B["az_deg"], B["el_deg"], B["range_m"])
                an[k] = analyse_block(B, phys, geo)
                an[k]["geom_reference"] = dict(edge_bin=geo["edge_bin"], peak_bin=geo["peak_bin"],
                                               n_prop_vertices=geo["n_prop_vertices"])
            J["q1q2_analysis"][key] = dict(physics=phys, blocks=an)
            J["q1q2_vs_base"][key] = {c[0]: compare_to_base(an, c[0]) for c in CELLS[key]}
        except Exception as e:
            J["q1q2_analysis"][key] = dict(error=f"{type(e).__name__}: {e}")
            print("   ⚠ 분석 실패(추적 자료는 저장됨):", e, flush=True)
        save()

    print("\n§2  에일리어싱 실측 (128 위상)")
    J["q4_alias_measured"] = {}
    for key in ("matrice4e", "mini2"):
        J["q4_alias_measured"][key] = run_alias(key, ALIAS_CELL)
        save()

    J["meta"]["gpu_status_at_end"] = SW.gpu_status()
    J["meta"]["seconds_total"] = float(time.time() - t0)
    save()
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")


if __name__ == "__main__":
    main()
