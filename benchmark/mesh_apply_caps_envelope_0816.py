# -*- coding: utf-8 -*-
"""
mesh_apply_caps_envelope_0816.py — 값 적용 라운드 (셸 계열 2건) 측정기
======================================================================

무엇을 넣나 (정본: outputs/mesh_inspect_body_arms_0816.json)
  ③ B3 로프트 끝단 캡 — `_SHELL_SHAPE[key]['smooth_iters']` 를 기종별로 정한다.
  ⑥ B6 phantom4 L/W 강제 해제 — `envelope_mm` 세 축 강제 → 높이만.

규약
----
* CPU 전용(CUDA_VISIBLE_DEVICES="") · git 미사용 · 남의 라운드 자리 무편집.
* **한 번에 하나씩** 넣고 매번 잰다. 「전」과 「후」를 **같은 프로세스 안에서** 잰다
  (다른 라운드가 소스를 동시에 고치고 있으므로, 파일을 다시 읽는 방식은 귀속이 깨진다).
  적용 전 상수는 메모리에서만 바꾸고, 뒤에 소스 편집이 그 값을 그대로 박았는지
  **지문으로 확인**한다.
* σ 는 **우리 커널 PO**(src/rcs_po.py, 가림 없음·재질 가중) 로 잰다.
    fc 3.5 GHz · 점 간격 λ/7 · 대역평균 5주파(±50 MHz, 5G 100 MHz 규약) ·
    방위 1.0° 격자 · el 0° 와 15°.
    · 방위평균 = 10log10(mean_az σ)
    · 최악방위 = 3° 각도평활 뒤 **최저** σ (단일주파 코히런트 널은 수치 아티팩트라
      대역평균+각도평활로 안정화한다 — rcs_po.drone_rcs_pattern_bw docstring 규약).
  ⚠ 점구름은 중심주파수의 λ/7 로 한 번만 깔고 5주파에 재사용한다(대역 안에서 간격
    변화는 1.4 % 라 무시). 이것은 «절대 σ» 가 아니라 «전후 차» 를 재는 잣대다.

산출: outputs/mesh_apply_caps_envelope_0816.json
실행:
  cd /workspace/sionna && CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/mesh_apply_caps_envelope_0816.py --step all
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings
from multiprocessing import Pool

import numpy as np

warnings.filterwarnings("ignore")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drone_cad as dc                                          # noqa: E402
import drones as dr                                             # noqa: E402
from rcs_po import mesh_to_points, rcs_from_points, C0, angular_smooth   # noqa: E402

FC = 3.5e9
BW = 100e6
NF = 5
DIV = 7.0
AZ = np.arange(0.0, 360.0, 1.0)
ELS = (0.0, 15.0)
SHELL_KEYS = ["matrice4e", "mavic4pro", "mini5pro", "phantom4", "phantom3", "mini2"]
ALL_KEYS = list(dr.DRONES.keys())
NPROC = 40                      # 기계를 다른 라운드와 나눠 쓴다 — 192 코어 중 40
_CLOUDS: dict = {}              # fork 로 워커에 물려주는 점구름


# --------------------------------------------------------------------------- #
#  지문 · 기하 잣대
# --------------------------------------------------------------------------- #
def fingerprint(m) -> str:
    v = np.asarray(m.v, np.float32).tobytes()
    f = np.asarray(m.f, np.int32).tobytes()
    return hashlib.sha256(v + f).hexdigest()[:16]


def all_fingerprints() -> dict:
    dr._FIT_CACHE.clear()
    return {k: fingerprint(dr.build_drone(dr.DRONES[k])) for k in ALL_KEYS}


def shell_stations(key, spec=None):
    """셸만 따로 지어 6 스테이션 반폭·반높이[mm] 와 표 대비 오차[%] 를 잰다."""
    import trimesh                                             # noqa: F401
    spec = spec or dr.DRONES[key]
    sh = dc._SHELL_SHAPE.get(key, dc._SHELL_DEFAULT)
    bl = spec.body_l_mm / 1000 * sh["fl"]
    bw = spec.body_w_mm / 1000 * sh["fw"]
    bh = spec.body_h_mm / 1000 * sh["fh"]
    m = dc._body_folding(bl, bw, bh, nose_drop=sh["ndrop"], n_pow=sh["npow"],
                         hw_f=sh["hw"], hh_f=sh["hh"], zo_f=sh["zo"],
                         smooth_iters=sh.get("smooth_iters", 4))
    hw_f = sh["hw"] if sh["hw"] is not None else (0.30, 0.46, 0.50, 0.44, 0.28, 0.10)
    hh_f = sh["hh"] if sh["hh"] is not None else (0.30, 0.46, 0.50, 0.46, 0.34, 0.16)
    out = {}
    for i, st in enumerate((-0.50, -0.30, -0.05, 0.18, 0.38, 0.50)):
        x0 = st * bl + (1e-6 if st == -0.50 else (-1e-6 if st == 0.50 else 0.0))
        try:
            s = m.section(plane_origin=[x0, 0, 0], plane_normal=[1, 0, 0])
            P3 = np.asarray(s.vertices, float)
            w, h = float(np.ptp(P3[:, 1]) / 2 * 1000), float(np.ptp(P3[:, 2]) / 2 * 1000)
        except Exception:
            w = h = float("nan")
        tw, th = hw_f[i] * bw * 0.95 * 1000, hh_f[i] * bh * 1000
        out[f"{st:+.2f}"] = dict(half_w_mm=round(w, 3), half_h_mm=round(h, 3),
                                 target_w_mm=round(tw, 3), target_h_mm=round(th, 3),
                                 err_w_pct=round(100 * (w / tw - 1), 2),
                                 err_h_pct=round(100 * (h / th - 1), 2))
    out["shell_len_mm"] = round(float(np.ptp(m.vertices[:, 0])) * 1000, 3)
    out["shell_vol_mm3"] = round(float(m.volume) * 1e9, 1)
    out["n_tri"] = int(len(m.faces))
    return out


def frame_facts(spec):
    dr._FIT_CACHE.clear()
    env = dr.frame_envelope_mm(spec)
    V = np.asarray(dr.build_drone(spec).v, float) * 1000
    return dict(fit_scale=[round(x, 6) for x in dr.frame_fit_scale(spec)],
                frame_bbox_mm=[round(float(x), 3) for x in
                               (np.ptp(np.asarray(dr.build_frame(spec).v, float), axis=0) * 1000)],
                drone_bbox_mm=[round(float(x), 3) for x in np.ptp(V, axis=0)],
                wheelbase_mm=round(float(env["wheelbase_opposite_mm"]), 3),
                diag_eff_mm=round(float(env["diagonal_effective_mm"]), 3),
                lwh_mm=[round(float(x), 3) for x in env["lwh_mm"]],
                n_tri=int(len(dr.build_drone(spec).f)))


# --------------------------------------------------------------------------- #
#  σ (PO, CPU, 병렬)
# --------------------------------------------------------------------------- #
def make_cloud(spec):
    m = dr.build_drone(spec)
    P, N, dA, w = mesh_to_points(m, C0 / FC / DIV, gamma=dr.drone_gamma_map(spec))
    return dict(P=P, N=N, dA=dA, w=w, npts=int(len(dA)))


def _job(args):
    tag, fi, el, i0, i1 = args
    c = _CLOUDS[tag]
    f = (FC - BW / 2) + BW * fi / max(1, NF - 1)
    s = rcs_from_points(c["P"], c["N"], c["dA"], f, AZ[i0:i1], el, w=c["w"])
    return tag, fi, el, i0, i1, s


def sigma_all(tags, chunk=20):
    """tags 별 (el → 대역평균 σ(az)) 를 병렬로 잰다."""
    jobs = [(t, fi, el, i, min(i + chunk, len(AZ)))
            for t in tags for fi in range(NF) for el in ELS
            for i in range(0, len(AZ), chunk)]
    acc = {t: {el: np.zeros(len(AZ)) for el in ELS} for t in tags}
    t0 = time.time()
    with Pool(NPROC) as pool:
        for n, (tag, fi, el, i0, i1, s) in enumerate(pool.imap_unordered(_job, jobs, chunksize=1)):
            acc[tag][el][i0:i1] += s / NF
            if n % 200 == 0:
                print(f"    …{n}/{len(jobs)}  {time.time()-t0:.0f}s", flush=True)
    return acc


def sigma_stats(sig):
    out = {}
    for el, s in sig.items():
        sm = angular_smooth(s, 3.0, float(AZ[1] - AZ[0]))
        out[f"el{int(el)}"] = dict(
            az_mean_dbsm=round(float(10 * np.log10(s.mean())), 3),
            worst_dbsm=round(float(10 * np.log10(sm.min())), 3),
            worst_az_deg=float(AZ[int(np.argmin(sm))]),
            best_dbsm=round(float(10 * np.log10(sm.max())), 3),
            best_az_deg=float(AZ[int(np.argmax(sm))]),
            #  기수/꼬리/옆구리 컷 — 끝단 캡은 «기수 정면 정반사» 결함이라 이 방위가 핵심이다
            cuts_dbsm={f"az{int(a)}": round(float(10 * np.log10(
                sm[int(np.argmin(np.abs(AZ - a)))])), 3) for a in (0, 90, 180, 270)})
    return out


def ddb(after, before):
    return {el: dict(d_az_mean_db=round(after[el]["az_mean_dbsm"] - before[el]["az_mean_dbsm"], 3),
                     d_worst_db=round(after[el]["worst_dbsm"] - before[el]["worst_dbsm"], 3),
                     d_best_db=round(after[el]["best_dbsm"] - before[el]["best_dbsm"], 3),
                     d_cuts_db={c: round(after[el]["cuts_dbsm"][c] - before[el]["cuts_dbsm"][c], 3)
                                for c in after[el]["cuts_dbsm"]})
            for el in after}


# --------------------------------------------------------------------------- #
#  단계
# --------------------------------------------------------------------------- #
def step_caps(res):
    """③ 끝단 캡 — smooth_iters 를 기종별로 넣는다(이 라운드 결정: 6종 전부 0)."""
    global _CLOUDS
    #  ⚠ 파일 상태와 무관하게 「전」(옛 리터럴 4)과 「후」(0)를 **명시적으로** 세운다 —
    #    소스 편집이 끝난 뒤 다시 돌려도 같은 대조가 나와야 한다.
    OLD = {k: 4 for k in SHELL_KEYS}
    for k, v in OLD.items():
        dc._SHELL_SHAPE[k]["smooth_iters"] = v
    #  ⑥ 은 아직 안 들어간 세계에서 ③ 만 잰다(상류부터 순서 · 귀속 분리).
    import dataclasses
    dr.DRONES["phantom4"] = dataclasses.replace(dr.DRONES["phantom4"],
                                                envelope_mm=(289.5, 289.5, 196.0))
    dr._FIT_CACHE.clear()
    print("[③] 전 상태 측정", flush=True)
    fp0 = all_fingerprints()
    before_geo = {k: shell_stations(k) for k in SHELL_KEYS}
    before_frame = {k: frame_facts(dr.DRONES[k]) for k in SHELL_KEYS}
    _CLOUDS = {}
    dr._FIT_CACHE.clear()
    for k in SHELL_KEYS:
        _CLOUDS[f"{k}|before"] = make_cloud(dr.DRONES[k])

    NEW = {k: 0 for k in SHELL_KEYS}
    old = dict(OLD)
    for k, v in NEW.items():                       # ⭐ 메모리에서만 적용
        dc._SHELL_SHAPE[k]["smooth_iters"] = v
    dr._FIT_CACHE.clear()

    print("[③] 후 상태 측정", flush=True)
    after_geo = {k: shell_stations(k) for k in SHELL_KEYS}
    after_frame = {k: frame_facts(dr.DRONES[k]) for k in SHELL_KEYS}
    for k in SHELL_KEYS:
        _CLOUDS[f"{k}|after"] = make_cloud(dr.DRONES[k])
    fp1 = all_fingerprints()

    sig = sigma_all(list(_CLOUDS.keys()))
    per = {}
    for k in SHELL_KEYS:
        b, a = sigma_stats(sig[f"{k}|before"]), sigma_stats(sig[f"{k}|after"])
        # 형상 이동량 [mm]: 셸 정점 대응이 1:1 이므로 직접 잰다
        sh = dc._SHELL_SHAPE[k]
        sp = dr.DRONES[k]
        bl, bw, bh = (sp.body_l_mm / 1000 * sh["fl"], sp.body_w_mm / 1000 * sh["fw"],
                      sp.body_h_mm / 1000 * sh["fh"])
        kw = dict(nose_drop=sh["ndrop"], n_pow=sh["npow"], hw_f=sh["hw"],
                  hh_f=sh["hh"], zo_f=sh["zo"])
        A = dc._body_folding(bl, bw, bh, smooth_iters=old[k], **kw).vertices
        B = dc._body_folding(bl, bw, bh, smooth_iters=NEW[k], **kw).vertices
        d = np.linalg.norm(A - B, axis=1) * 1000
        xr = np.abs(A[:, 0]) / bl
        per[k] = dict(
            smooth_iters=[old[k], NEW[k]],
            geom_before=before_geo[k], geom_after=after_geo[k],
            shell_move_mm=dict(max_all=round(float(d.max()), 3),
                               max_middle_le045bl=round(float(d[xr <= 0.45].max()), 3),
                               mean_middle=round(float(d[xr <= 0.45].mean()), 4)),
            frame_before=before_frame[k], frame_after=after_frame[k],
            sigma_before=b, sigma_after=a, sigma_delta_db=ddb(a, b),
            n_po_points=[_CLOUDS[f"{k}|before"]["npts"], _CLOUDS[f"{k}|after"]["npts"]],
            fingerprint=[fp0[k], fp1[k]])
    untouched = [k for k in ALL_KEYS if k not in SHELL_KEYS]
    res["step3_loft_end_caps"] = dict(
        applied={k: dict(smooth_iters_old=old[k], smooth_iters_new=NEW[k]) for k in SHELL_KEYS},
        per_drone=per,
        untouched_bit_identical={k: dict(same=bool(fp0[k] == fp1[k]), fp=fp0[k]) for k in untouched},
        touched_changed={k: bool(fp0[k] != fp1[k]) for k in SHELL_KEYS})
    return res


def step_envelope(res):
    """⑥ phantom4 L/W 강제 해제 — ③ 이 이미 들어간 상태 위에서 잰다."""
    global _CLOUDS
    import dataclasses
    for k in SHELL_KEYS:                        # ③ 적용 상태를 재현
        dc._SHELL_SHAPE[k]["smooth_iters"] = 0
    dr._FIT_CACHE.clear()
    #  ⚠ 파일 상태와 무관하게 「전」과 「후」를 **명시적으로** 짓는다 — 소스 편집이 끝난 뒤
    #    다시 돌려도 같은 대조가 나와야 한다(다른 라운드가 같은 파일을 만지고 있다).
    sp0 = dataclasses.replace(dr.DRONES["phantom4"], envelope_mm=(289.5, 289.5, 196.0))
    sp1 = dataclasses.replace(dr.DRONES["phantom4"], envelope_mm=(None, None, 196.0))
    before = frame_facts(sp0)
    after = frame_facts(sp1)
    fp_b, fp_a = fingerprint(dr.build_drone(sp0)), fingerprint(dr.build_drone(sp1))
    _CLOUDS = {"phantom4|before": make_cloud(sp0), "phantom4|after": make_cloud(sp1)}
    sig = sigma_all(list(_CLOUDS.keys()))
    b, a = sigma_stats(sig["phantom4|before"]), sigma_stats(sig["phantom4|after"])
    #  로터 배치 — 공표 대각 350 mm 재현 여부
    lay_b = [r["center"] for r in dr.rotor_layout(sp0)]
    dr._FIT_CACHE.clear()
    lay_a = [r["center"] for r in dr.rotor_layout(sp1)]
    res["step6_phantom4_envelope"] = dict(
        applied=dict(envelope_mm_old=list(sp0.envelope_mm), envelope_mm_new=[None, None, 196.0]),
        frame_before=before, frame_after=after,
        wheelbase_mm=dict(official=350.0, before=before["wheelbase_mm"], after=after["wheelbase_mm"],
                          err_pct_before=round(100 * (before["wheelbase_mm"] / 350 - 1), 3),
                          err_pct_after=round(100 * (after["wheelbase_mm"] / 350 - 1), 3)),
        rotor_center_mm=dict(before=[[round(v * 1000, 3) for v in c] for c in lay_b],
                             after=[[round(v * 1000, 3) for v in c] for c in lay_a]),
        sigma_before=b, sigma_after=a, sigma_delta_db=ddb(a, b),
        fingerprint=[fp_b, fp_a])
    return res


def step_verify(res):
    """소스 편집이 «측정한 후 상태» 를 그대로 만들었는지 — 그리고 안 건드린 기체가 여전히
    비트동일인지 — 파일에서 다시 지어 확인한다. 측정 직후에 돌려야 의미가 있다
    (다른 라운드가 같은 파일을 동시에 고치고 있어서 기준선이 움직인다)."""
    #  ⚠ **새 프로세스**에서 짓는다 — 이 프로세스는 상수를 메모리에서 바꿔 놨으므로
    #    같은 인터프리터로 재확인하면 자기 자신을 확인하는 셈이 된다.
    import subprocess
    code = (
        "import warnings,hashlib,json;warnings.filterwarnings('ignore')\n"
        "import numpy as np, drones as dr, drone_cad as dc\n"
        "f=lambda m: hashlib.sha256(np.asarray(m.v,np.float32).tobytes()+"
        "np.asarray(m.f,np.int32).tobytes()).hexdigest()[:16]\n"
        "print(json.dumps({'fp':{k:f(dr.build_drone(dr.DRONES[k])) for k in dr.DRONES},"
        "'si':{k:dc._SHELL_SHAPE[k].get('smooth_iters',4) for k in "
        f"{SHELL_KEYS!r}" "},'env':list(dr.DRONES['phantom4'].envelope_mm or (None,None,None))}))\n")
    env = dict(os.environ, PYTHONPATH=f"{os.path.join(ROOT, 'src')}:{HERE}",
               CUDA_VISIBLE_DEVICES="")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       cwd=ROOT, env=env)
    fresh = json.loads(r.stdout.strip().splitlines()[-1])
    now = fresh["fp"]
    d3 = res.get("step3_loft_end_caps", {})
    d6 = res.get("step6_phantom4_envelope", {})
    out = {"constants_in_file": {"smooth_iters": fresh["si"],
                                 "phantom4_envelope_mm": fresh["env"]},
           "per_drone": {}}
    for k in SHELL_KEYS:
        want = (d6.get("fingerprint", [None, None])[1] if k == "phantom4"
                else d3.get("per_drone", {}).get(k, {}).get("fingerprint", [None, None])[1])
        out["per_drone"][k] = dict(file=now[k], measured_after=want, match=bool(now[k] == want))
    for k, v in d3.get("untouched_bit_identical", {}).items():
        out["per_drone"][k] = dict(file=now[k], baseline=v["fp"], match=bool(now[k] == v["fp"]))
    out["all_match"] = all(v["match"] for v in out["per_drone"].values())
    out["source_md5_at_verify"] = {
        p: hashlib.md5(open(os.path.join(ROOT, "src", p), "rb").read()).hexdigest()
        for p in ("drone_cad.py", "drones.py", "cadkit.py", "geom.py")}
    out["note"] = ("⚠ match=False 는 **이 라운드의 값이 안 들어갔다는 뜻이 아니다** — "
                   "병행 중인 2층 수리 라운드가 같은 파일의 다른 상수(INTERNALS·캐노피 등)를 "
                   "고치면 그 기체 지문이 같이 움직인다. 이 라운드의 Δ 는 한 프로세스 안에서 "
                   "「전(4/강제) → 후(0/해제)」 로 재므로 그 드리프트와 무관하다.")
    res["step9_verify_from_file"] = out
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", default="all", choices=["3", "6", "verify", "all"])
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs",
                                                  "mesh_apply_caps_envelope_0816.json"))
    a = ap.parse_args()
    res = {}
    if os.path.exists(a.out):
        res = json.load(open(a.out))
    res.setdefault("_meta", {})["measured_at"] = time.strftime("%Y-%m-%d %H:%M:%S KST",
                                                               time.localtime(time.time() + 9 * 3600))
    #  ⚠ 이 라운드와 **병행하는 다른 라운드**가 같은 파일을 고치고 있다. 어떤 소스 위에서
    #    잰 숫자인지 남긴다(md5). 「전 → 후」 대조는 한 프로세스 안에서 하므로 귀속은 안전하다.
    res["_meta"]["source_md5"] = {
        p: hashlib.md5(open(os.path.join(ROOT, "src", p), "rb").read()).hexdigest()
        for p in ("drone_cad.py", "drones.py", "cadkit.py", "geom.py")}
    if a.step in ("3", "all"):
        res = step_caps(res)
    if a.step in ("6", "all"):
        res = step_envelope(res)
    if a.step in ("verify", "all"):
        res = step_verify(res)
    with open(a.out, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
