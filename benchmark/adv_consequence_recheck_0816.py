# -*- coding: utf-8 -*-
"""
adv_consequence_recheck_0816.py — «그래서 결과가 바뀐다» 반증 2 라운드 (2026-08-16)
==================================================================================

왜 또 하나
----------
같은 날 `benchmark/adv_consequence_0816.py` 가 이미 «형상 오차가 판정을 바꾸나» 를 쟀다.
그런데 그 뒤(13:43~13:44) 저장소에 **세 번째 판** `per_airframe` 이 올라왔다 —
기체마다 **그 기체의 프롭 곡선**을 쓰는 판이다. 앞 라운드는 `dji_mini2`(전 기종 곡선 하나)
까지만 쟀으므로, **지금 유력한 후보로는 아무도 값을 재지 않았다.**
그리고 «기체마다 다른 곡선» 은 ⓑ(분류)에서 앞 판과 성질이 정반대다 — 공통 오차가 아니다.

이 파일이 새로 하는 것 (앞 라운드가 안 한 것만)
-----------------------------------------------
  J1  세 판(legacy / dji_mini2 / per_airframe) 전 기종 날 면적 — 공통 대 차등 분해
  J2  슬로타임 PO 를 **세 판 전부** 로 (분류 3기체 × el 0·−30)
  J3  ⭐ **클래스 간 거리 자체가 바뀌나** — 앞 라운드는 «한 기체가 얼마나 움직이나(z)» 만
      쟀고 «세 기체를 다 새 판으로 지으면 클래스 간 간격이 좁아지나» 는 안 쟀다.
      분류가 사는지 죽는지는 후자가 정한다.
  J4  빗살 정합 분류기(classify_airframe) 를 per_airframe 판으로 뒤집기 시험
  J5  R50 — 앵커 상쇄(c_anchor)가 실제로 공통항을 지우는지 사슬로 확인 + 세 판 값
  J6  엔진 비교 여백 — 판 교체가 우리 쪽을 몇 dB 움직이나 대 원장의 엔진 간격 몇 dB
  J7  σ 앵커 — 방위평균에서 프롭 지분, 판 교체가 총 σ 를 몇 dB 움직이나 (phantom3·mini5pro)

규약
----
* **CPU 전용, GPU 0 회.** Sionna/Mitsuba import 0 회.
* **기존 소스 무변경.** 이 파일은 읽기 전용 측정기다.
* 커널 = 순수 PO 점구름(`src/rcs_po.py`), 가림 없음. 두 판의 **비(比)** 만 쓴다.
* |Γ| 는 `src/materials.py` 표를 AST 로 읽어 계산(모듈 import 하면 drjit 스레드풀이 뜬다).

산출: outputs/mesh_adv_refute_consequence_0816.json 의 **J_* 키에 덧붙임**(기존 키 보존).

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/adv_consequence_recheck_0816.py
"""
from __future__ import annotations

import ast
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from drones import (DRONES, DRONE_GROUP_MAT, build_frame, build_propeller,  # noqa: E402
                    rotor_layout)
import drone_cad as dc                                                      # noqa: E402
from rcs_po import mesh_to_points, po_field_dir, C0                          # noqa: E402

EPS0 = 8.8541878128e-12
OUT = os.path.join(ROOT, "outputs", "mesh_adv_refute_consequence_0816.json")

FC = 3.5e9
LAM = C0 / FC
K = 2 * np.pi / LAM
SPACING = LAM / 7.0
PRF = 19700.0
N_POSES = 8192
AZ_DEG = 0.0
RPM_LEDGER = [3808.36, 3791.64, 3795.402, 3804.598]
ELS = [0.0, -30.0]
LAWS = ["legacy", "dji_mini2", "per_airframe"]
TRIO = ["mini5pro", "matrice4e", "s1000plus"]
ALL_KEYS = list(DRONES.keys())


# --------------------------------------------------------------------------- #
#  |Γ| — materials.py 표를 AST 로
# --------------------------------------------------------------------------- #
def gamma_map(fc: float = FC):
    src = open(os.path.join(ROOT, "src", "materials.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    table = None
    for node in tree.body:
        tgt = getattr(node, "targets", [getattr(node, "target", None)])
        if "MATERIALS" not in [t.id for t in tgt if isinstance(t, ast.Name)]:
            continue
        table = {}
        for k, v in zip(node.value.keys, node.value.values):
            d = {}
            for kw in v.keywords:
                try:
                    d[kw.arg] = ast.literal_eval(kw.value)
                except ValueError:
                    d[kw.arg] = None
            table[ast.literal_eval(k)] = d
        break
    if table is None:
        raise RuntimeError("materials.py 에서 MATERIALS 를 못 찾았다")
    itu_bulk = {"metal": (1.0, 1.0e7)}
    per_mat = {}
    for mat in {m for m, _ in DRONE_GROUP_MAT.values()}:
        spec = table[mat]
        if "gamma_po" in spec:
            per_mat[mat] = float(spec["gamma_po"])
            continue
        er, sg = itu_bulk[spec["itu"]] if "itu" in spec else (float(spec["eps_r"]),
                                                             float(spec["sigma"]))
        eps_c = er - 1j * sg / (2 * np.pi * fc * EPS0)
        per_mat[mat] = float(abs((1 - np.sqrt(eps_c)) / (1 + np.sqrt(eps_c))))
    return {g: per_mat[m] for g, (m, _) in DRONE_GROUP_MAT.items()}, per_mat


GAMMA, GAMMA_MAT = gamma_map()


# --------------------------------------------------------------------------- #
#  PO 배치
# --------------------------------------------------------------------------- #
def po_batch(P, N, dA, w, V):
    out = np.empty(len(V), complex)
    amp = dA if w is None else dA * w
    chunk = max(1, int(5e5 // max(1, len(dA))))
    for s in range(0, len(V), chunk):
        Vs = V[s:s + chunk]
        NU = N @ Vs.T
        PU = P @ Vs.T
        PU *= 2 * K
        Z = np.exp(1j * PU)
        Z *= np.where(NU > 0, NU, 0.0) * amp[:, None]
        out[s:s + chunk] = Z.sum(axis=0)
    return out


def verify_batch(P, N, dA, w, seed=11, n=4) -> float:
    """출하 커널 `po_field_dir` 과 내 배치판이 같은 값을 내는지."""
    rng = np.random.default_rng(seed)
    V = rng.standard_normal((n, 3))
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    ref = np.array([po_field_dir(P, N, dA, FC, v, w=w) for v in V])
    got = po_batch(P, N, dA, w, V)
    return float(np.max(np.abs(ref - got) / np.maximum(np.abs(ref), 1e-300)))


def look_dir(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


def rotz_T(u, theta_deg):
    t = np.radians(np.atleast_1d(theta_deg))
    c, s = np.cos(t), np.sin(t)
    return np.stack([c * u[0] + s * u[1], -s * u[0] + c * u[1], np.full_like(c, u[2])], axis=-1)


# --------------------------------------------------------------------------- #
#  J1. 평면형 — 공통 대 차등
# --------------------------------------------------------------------------- #
def part_J1() -> dict:
    rows = {}
    rr = np.linspace(0.07, 1.0, 4001)
    for key in ALL_KEYS:
        spec = DRONES[key]
        R = float(spec.prop_dia_mm) / 2000.0
        out = {}
        for law in LAWS:
            cm, why = dc.resolve_chord_max_over_r(spec, law)
            p_rr, p_fr, psrc = dc.resolve_chord_profile(spec, law)
            if p_rr is None:
                p_rr = dc.CHORD_RR if law == "legacy" else dc.CHORD_RR_DJI_MINI2
                p_fr = dc.CHORD_FRAC if law == "legacy" else dc.CHORD_FRAC_DJI_MINI2
            c = np.interp(rr, p_rr, p_fr) * cm * R
            m = build_propeller(spec, blade_law=law)
            V, F = np.asarray(m.v, float), np.asarray(m.f, np.int64)
            ar = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]],
                                               V[F[:, 2]] - V[F[:, 0]]), axis=1)
            sel_o = (rr >= 0.6) & (rr <= 0.96)
            out[law] = dict(
                c_max_over_R=round(float(cm), 5), c_max_src=why[:70], profile_src=psrc[:70],
                planform_area_m2=float(np.trapezoid(c, rr) * R),
                outer_area_m2=float(np.trapezoid(c[sel_o], rr[sel_o]) * R),
                mesh_area_m2=float(ar.sum()), n_tri=int(len(F)))
        base = out["legacy"]
        rows[key] = dict(
            laws={k: {kk: (round(vv, 8) if isinstance(vv, float) else vv)
                      for kk, vv in v.items()} for k, v in out.items()},
            d_planform_db={law: round(10 * math.log10(out[law]["planform_area_m2"]
                                                      / base["planform_area_m2"]), 3)
                           for law in LAWS},
            d_outer_db={law: round(10 * math.log10(out[law]["outer_area_m2"]
                                                   / base["outer_area_m2"]), 3)
                        for law in LAWS},
            d_mesh_db={law: round(10 * math.log10(out[law]["mesh_area_m2"]
                                                  / base["mesh_area_m2"]), 3)
                       for law in LAWS})
        print(f"  J1 {key} ok", flush=True)
    summ = {}
    for law in LAWS[1:]:
        allv = np.array([rows[k]["d_planform_db"][law] for k in ALL_KEYS])
        trio = np.array([rows[k]["d_planform_db"][law] for k in TRIO])
        outr = np.array([rows[k]["d_outer_db"][law] for k in ALL_KEYS])
        summ[law] = dict(
            fleet_min_db=round(float(allv.min()), 3), fleet_max_db=round(float(allv.max()), 3),
            fleet_span_db=round(float(allv.max() - allv.min()), 3),
            fleet_std_db=round(float(allv.std()), 3),
            outer_band_span_db=round(float(outr.max() - outr.min()), 3),
            classify_trio_db={k: rows[k]["d_planform_db"][law] for k in TRIO},
            classify_trio_span_db=round(float(trio.max() - trio.min()), 3))
    return dict(per_airframe=rows, common_mode=summ,
                what_ko="판을 갈면 기종마다 날 면적이 몇 dB 움직이나. 전 기종이 같은 값이면 "
                        "«공통 오차» 라 기체 간 상대 비교에서 지워진다. 산포가 크면 차등이다.")


# --------------------------------------------------------------------------- #
#  J2. 슬로타임 PO — 세 판
# --------------------------------------------------------------------------- #
def rotor_phase_table(spec, n_poses):
    from articulated_fast import rotor_phases
    rl = rotor_layout(spec)
    dirs = [r["dir"] for r in rl]
    rel = np.resize(np.asarray(RPM_LEDGER, float) / np.mean(RPM_LEDGER), len(rl))
    rpms = float(spec.hover_rpm) * rel
    return rotor_phases(np.arange(n_poses) / PRF, rpms, dirs), rpms


def slowtime(spec, law, els, n_poses=N_POSES):
    frame = build_frame(spec)
    Pf, Nf, dAf, wf = mesh_to_points(frame, SPACING, gamma=GAMMA)
    props = {+1: build_propeller(spec, blade_law=law),
             -1: build_propeller(spec, blade_law=law, mirror=True)}
    pts = {d: mesh_to_points(m, SPACING, gamma=GAMMA) for d, m in props.items()}
    rl = rotor_layout(spec)
    ph, rpms = rotor_phase_table(spec, n_poses)
    res = {}
    for el in els:
        u = look_dir(AZ_DEG, el)
        E_frame = po_field_dir(Pf, Nf, dAf, FC, u, w=wf)
        E_prop = np.zeros(n_poses, complex)
        for i, rot in enumerate(rl):
            Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
            V = rotz_T(u, rot["base_ang"] + ph[:, i])
            E_prop += np.exp(1j * 2 * K * float(np.dot(rot["center"], u))) \
                * po_batch(Pp, Np_, dAp, wp, V)
        res[el] = dict(E=E_frame + E_prop, E_prop=E_prop, E_frame=complex(E_frame))
    return res, dict(n_frame_pts=int(len(dAf)), n_prop_pts=int(len(pts[1][2])),
                     n_rotors=len(rl), batch_max_rel_err=round(verify_batch(*pts[1]), 12))


def masks_of(n, f_tip, f_flash, lo=0.35, hw=8.0):
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    band = (np.abs(fr) >= lo * f_tip) & (np.abs(fr) <= f_tip)
    kk = np.round(np.abs(fr) / f_flash)
    comb = band & (np.abs(np.abs(fr) - kk * f_flash) <= hw) & (kk >= 1)
    return band, comb


def part_J2(els=ELS, n_poses=N_POSES):
    rows, diag, series = {}, {}, {}
    for key in TRIO:
        spec = DRONES[key]
        f_flash = spec.prop_blades * spec.hover_rpm / 60.0
        v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
        rows[key] = {}
        for law in LAWS:
            t0 = time.time()
            res, dg = slowtime(spec, law, els, n_poses)
            diag[f"{key}/{law}"] = dg | {"secs": round(time.time() - t0, 1)}
            rows[key][law] = {}
            for el in els:
                f_tip = 2.0 * v_tip / LAM * math.cos(math.radians(el))
                E, Ep = res[el]["E"], res[el]["E_prop"]
                series[(key, law, el)] = E
                n = E.size
                band, comb = masks_of(n, max(f_tip, 1e-6), f_flash)
                x = (E - E.mean()) * np.hanning(n)
                P = np.abs(np.fft.fft(x)) ** 2
                sig = 4 * np.pi / LAM ** 2 * np.abs(E) ** 2
                sig_p = 4 * np.pi / LAM ** 2 * np.abs(Ep) ** 2
                rows[key][law][f"{el:+.0f}"] = dict(
                    f_tip_hz=round(f_tip, 2), f_flash_hz=round(f_flash, 3),
                    sigma_total_mean_dbsm=round(float(10 * np.log10(sig.mean())), 3),
                    sigma_prop_mean_dbsm=round(float(10 * np.log10(sig_p.mean())), 3),
                    prop_share_db=round(float(10 * np.log10(sig_p.mean() / sig.mean())), 3),
                    ac_power=float((np.abs(E - E.mean()) ** 2).mean()),
                    comb_energy=float(P[comb].sum()), band_energy=float(P[band].sum()),
                    total_ac_energy=float(
                        P[np.abs(np.fft.fftfreq(n, 1 / PRF)) >= 8.0].sum()))
            print(f"  J2 {key}/{law} {time.time()-t0:.1f}s", flush=True)
    delta = {}
    for key in TRIO:
        delta[key] = {}
        for law in LAWS[1:]:
            delta[key][law] = {}
            for el in els:
                k = f"{el:+.0f}"
                a, b = rows[key]["legacy"][k], rows[key][law][k]
                delta[key][law][k] = dict(
                    d_sigma_total_db=round(b["sigma_total_mean_dbsm"]
                                           - a["sigma_total_mean_dbsm"], 3),
                    d_sigma_prop_db=round(b["sigma_prop_mean_dbsm"]
                                          - a["sigma_prop_mean_dbsm"], 3),
                    d_ac_power_db=round(10 * math.log10(b["ac_power"] / a["ac_power"]), 3),
                    d_comb_db=round(10 * math.log10(b["comb_energy"] / a["comb_energy"]), 3),
                    d_band_db=round(10 * math.log10(b["band_energy"] / a["band_energy"]), 3))
    return dict(rows=rows, delta=delta, diag=diag), series


# --------------------------------------------------------------------------- #
#  J3. ⭐ 클래스 간 거리 — 세 기체를 다 새 판으로 지으면 간격이 좁아지나
# --------------------------------------------------------------------------- #
def part_J3(series, els=ELS, win=4925) -> dict:
    from md_classify_dataset import features, FEATURE_NAMES as FEATS
    stats = json.load(open(os.path.join(ROOT, "outputs", "md_classify.json")))["feature_stats"]
    names = list(FEATS)

    #: 잣대 — 저장소가 발표한 클래스내 표준편차(판과 무관한 자). 새 판의 클래스내 산포는
    #  측정된 적이 없으므로 **같은 자**를 두 판에 대고 «간격이 몇 자냐» 만 비교한다.
    pooled = {}
    for nm in names:
        st = stats.get(nm)
        if not st:
            continue
        p = {}
        for i in range(len(TRIO)):
            for j in range(i + 1, len(TRIO)):
                a, b = st.get(TRIO[i]), st.get(TRIO[j])
                if not a or not b:
                    continue
                p[f"{TRIO[i]}|{TRIO[j]}"] = math.sqrt(0.5 * (a["std"] ** 2 + b["std"] ** 2))
        if p:
            pooled[nm] = p

    vec = {}
    for key in TRIO:
        for law in LAWS:
            for el in els:
                v, _ = features(series[(key, law, el)][:win], PRF)
                vec[(key, law, el)] = np.asarray(v, float)

    out = {}
    for el in els:
        per_law = {}
        for law in LAWS:
            pairs = {}
            for i in range(len(TRIO)):
                for j in range(i + 1, len(TRIO)):
                    pk = f"{TRIO[i]}|{TRIO[j]}"
                    va, vb = vec[(TRIO[i], law, el)], vec[(TRIO[j], law, el)]
                    per_feat, sq = {}, 0.0
                    for fi, nm in enumerate(names):
                        sd = pooled.get(nm, {}).get(pk)
                        if not sd:
                            continue
                        z = abs(va[fi] - vb[fi]) / sd
                        per_feat[nm] = round(float(z), 3)
                        sq += z * z
                    pairs[pk] = dict(per_feature_sep_z=per_feat,
                                     euclid_sep_z=round(float(math.sqrt(sq)), 3),
                                     max_feature_sep_z=round(float(max(per_feat.values())), 3),
                                     n_features=len(per_feat))
            per_law[law] = dict(
                pairs=pairs,
                min_pair_euclid_z=round(float(min(p["euclid_sep_z"] for p in pairs.values())), 3),
                min_pair_best_feature_z=round(
                    float(min(p["max_feature_sep_z"] for p in pairs.values())), 3))
        out[f"{el:+.0f}"] = dict(
            per_law=per_law,
            change_vs_legacy={
                law: dict(
                    d_min_pair_euclid_z=round(per_law[law]["min_pair_euclid_z"]
                                              - per_law["legacy"]["min_pair_euclid_z"], 3),
                    ratio_min_pair_euclid=round(per_law[law]["min_pair_euclid_z"]
                                                / max(per_law["legacy"]["min_pair_euclid_z"],
                                                      1e-9), 4),
                    d_min_pair_best_feature_z=round(per_law[law]["min_pair_best_feature_z"]
                                                    - per_law["legacy"]["min_pair_best_feature_z"],
                                                    3))
                for law in LAWS[1:]})

    #: 한 기체가 얼마나 움직이나(앞 라운드의 z) 를 «그 특징이 애초에 클래스를 가르나» 와 나란히
    move = {}
    for key in TRIO:
        move[key] = {}
        for el in els:
            m = {}
            for law in LAWS[1:]:
                per_feat = {}
                for fi, nm in enumerate(names):
                    st = stats.get(nm, {}).get(key)
                    if not st or not st.get("std"):
                        continue
                    dz = abs(vec[(key, law, el)][fi] - vec[(key, "legacy", el)][fi]) / st["std"]
                    #: 같은 잣대로 잰 «이 특징의 클래스 간 최소 거리»
                    seps = []
                    for pk, sd in pooled.get(nm, {}).items():
                        a, b = pk.split("|")
                        seps.append(abs(vec[(a, "legacy", el)][fi]
                                        - vec[(b, "legacy", el)][fi]) / sd)
                    per_feat[nm] = dict(
                        move_z=round(float(dz), 3),
                        class_gap_z=round(float(min(seps)), 3) if seps else None,
                        move_over_gap=round(float(dz / min(seps)), 3)
                        if seps and min(seps) > 1e-9 else None)
                m[law] = per_feat
            move[key][f"{el:+.0f}"] = m
    return dict(between_class=out, per_airframe_move=move,
                ruler_ko="클래스 간 거리 = |특징(A) − 특징(B)| / 클래스내 표준편차(저장소 발표). "
                         "같은 자를 세 판에 똑같이 대고, **판마다 다시 지은 세 기체 사이의 "
                         "간격**을 비교한다. 간격이 안 좁아지면 분류는 판 교체를 견딘다.")


# --------------------------------------------------------------------------- #
#  J4. 빗살 정합 분류기 — per_airframe 판으로 뒤집히나
# --------------------------------------------------------------------------- #
def part_J4(series, els=ELS) -> dict:
    import classify_airframe as CA
    cand = {a: DRONES[a].prop_blades * DRONES[a].hover_rpm / 60.0 for a in CA.AIRFRAMES}
    out = {}
    for law in LAWS:
        conf = np.zeros((3, 3), int)
        margins = []
        for el in els:
            for i, a in enumerate(CA.AIRFRAMES):
                sc = CA.window_scores(series[(a, law, el)], PRF, cand)
                for w in range(sc.shape[0]):
                    j = int(np.argmax(sc[w]))
                    conf[i, j] += 1
                    s = np.sort(sc[w])[::-1]
                    margins.append(float((s[0] - s[1]) / max(s[0], 1e-30)))
        out[law] = dict(confusion=conf.tolist(),
                        accuracy=round(float(np.trace(conf) / conf.sum()), 4),
                        n_windows=int(conf.sum()),
                        decision_margin_median=round(float(np.median(margins)), 4))
    flips = {}
    for law in LAWS[1:]:
        nf, nw, shift = 0, 0, []
        for el in els:
            for a in CA.AIRFRAMES:
                s1 = CA.window_scores(series[(a, "legacy", el)], PRF, cand)
                s2 = CA.window_scores(series[(a, law, el)], PRF, cand)
                nf += int((np.argmax(s1, axis=1) != np.argmax(s2, axis=1)).sum())
                nw += s1.shape[0]
                shift.append(float(np.abs(s2 - s1).max()))
        flips[law] = dict(n_windows=nw, n_flipped=nf,
                          max_abs_score_shift=round(max(shift), 4))
    return dict(per_law=out, flips_vs_legacy=flips)


# --------------------------------------------------------------------------- #
#  J5. R50 — 앵커 상쇄가 실제로 일어나는지 사슬로 확인
# --------------------------------------------------------------------------- #
def part_J5(J2) -> dict:
    rows = J2["rows"]
    out = {}
    for key in TRIO:
        out[key] = {}
        for law in LAWS[1:]:
            d_anchor = (rows[key][law]["-30"]["sigma_total_mean_dbsm"]
                        - rows[key]["legacy"]["-30"]["sigma_total_mean_dbsm"])
            per_el = {}
            for el in ELS:
                k = f"{el:+.0f}"
                d_comb = 10 * math.log10(rows[key][law][k]["comb_energy"]
                                         / rows[key]["legacy"][k]["comb_energy"])
                d_snr = d_comb - d_anchor
                per_el[k] = dict(d_comb_db=round(d_comb, 3),
                                 d_anchor_db=round(d_anchor, 3),
                                 d_snr_db=round(d_snr, 3),
                                 d_R50_pct=round(100 * (10 ** (d_snr / 40) - 1), 2))
            out[key][law] = per_el
    return out


def anchor_cancellation_probe(seed=20260816, n=4096) -> dict:
    """`detection_curves.py` 의 사슬을 합성열로 재현해 «총 σ 를 g dB 올리면 R50 이
    안 움직인다» 를 실증한다. 사슬: c_anchor = σ_ref/⟨σ⟩ → sig_t = σ(t)·c → P_echo ∝ σ/R⁴."""
    from rx_noise import anchor_scale, sigma_kernel_m2
    rng = np.random.default_rng(seed)
    E = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) * 0.1 + (3.0 + 0.5j)
    res = {}
    for g_db in (0.0, 1.0, 3.0):
        Eg = E * 10 ** (g_db / 20)                     # 총 장 진폭을 g dB
        c = anchor_scale(Eg, FC, -20.0)["c_anchor"]
        sig_t = sigma_kernel_m2(Eg, FC) * c
        res[f"{g_db:+.1f}dB"] = dict(
            c_anchor_db=round(float(10 * np.log10(c)), 6),
            anchored_sigma_mean_dbsm=round(float(10 * np.log10(sig_t.mean())), 6),
            anchored_ac_energy_db=round(float(
                10 * np.log10((np.abs(sig_t - sig_t.mean()) ** 2).mean())), 6))
    base = res["+0.0dB"]
    return dict(probe=res,
                sigma_mean_is_pinned=all(
                    abs(v["anchored_sigma_mean_dbsm"] - base["anchored_sigma_mean_dbsm"]) < 1e-6
                    for v in res.values()),
                reading_ko="c_anchor 가 ⟨σ⟩ 를 문헌값에 고정하므로 **총 σ 의 공통 이동은 "
                           "R50 에서 정확히 지워진다**. 남는 것은 빗살/총σ 의 비뿐이다.")


# --------------------------------------------------------------------------- #
#  J6. 엔진 비교 여백
# --------------------------------------------------------------------------- #
def part_J6(J2) -> dict:
    led = json.load(open(os.path.join(ROOT, "outputs", "elevation_sweep_md.json")))
    arms = {"mini5pro": ("ours_mini5pro_r15_n8192",
                         "sionna_p4000000000_mini5pro_r15_n8192_d1"),
            "matrice4e": ("ours_r15_n8192", "sionna_p4000000000_r15_n8192_d1"),
            "s1000plus": ("ours_s1000plus_r15_n8192",
                          "sionna_p4000000000_s1000plus_r15_n8192_d1")}
    gap = {}
    for a, (o, s) in arms.items():
        g = {}
        for el in (0.0, -15.0, -30.0, -45.0, -60.0, -75.0):
            ro = [r for r in led["rows"] if r["engine"] == o and float(r["el_deg"]) == el]
            rs = [r for r in led["rows"] if r["engine"] == s and float(r["el_deg"]) == el]
            if ro and rs:
                g[f"{el:+.0f}"] = round(float(ro[-1]["level_db"]) - float(rs[-1]["level_db"]), 3)
        gap[a] = g
    move = {}
    for key in TRIO:
        move[key] = {law: max(abs(J2["delta"][key][law][f"{el:+.0f}"]["d_ac_power_db"])
                              for el in ELS) for law in LAWS[1:]}
    worst_move = max(max(v.values()) for v in move.values())
    gaps = [v for g in gap.values() for v in g.values()]
    return dict(ledger_engine_gap_db=gap,
                our_max_ac_move_db=move,
                worst_move_db=round(float(worst_move), 3),
                min_engine_gap_db=round(float(min(gaps)), 3),
                move_over_min_gap_pct=round(float(100 * worst_move / min(gaps)), 2),
                reading_ko="판 교체가 우리 쪽 AC 레벨을 움직이는 최대치 대 원장이 발표한 "
                           "엔진 간 레벨차. 후자가 훨씬 크면 «엔진 판정» 은 판 교체에 안 흔들린다.")


# --------------------------------------------------------------------------- #
#  J7. σ 앵커 — 방위평균에서 프롭 지분·총 σ 이동
# --------------------------------------------------------------------------- #
def part_J7(keys=("phantom3", "mini5pro"), els=(0.0, -30.0), n_az=180) -> dict:
    az = np.arange(n_az) * (360.0 / n_az)
    out = {}
    for key in keys:
        spec = DRONES[key]
        rl = rotor_layout(spec)
        per = {}
        for law in LAWS:
            t0 = time.time()
            frame = build_frame(spec)
            Pf, Nf, dAf, wf = mesh_to_points(frame, SPACING, gamma=GAMMA)
            props = {+1: build_propeller(spec, blade_law=law),
                     -1: build_propeller(spec, blade_law=law, mirror=True)}
            pts = {d: mesh_to_points(m, SPACING, gamma=GAMMA) for d, m in props.items()}
            per[law] = {}
            for el in els:
                U = np.stack([look_dir(a, el) for a in az])
                E = po_batch(Pf, Nf, dAf, wf, U)
                Ep = np.zeros(len(az), complex)
                for rot in rl:
                    Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
                    V = np.stack([rotz_T(u, rot["base_ang"])[0] for u in U])
                    Ep += np.exp(1j * 2 * K * (U @ np.asarray(rot["center"], float))) \
                        * po_batch(Pp, Np_, dAp, wp, V)
                sig = 4 * np.pi / LAM ** 2 * np.abs(E + Ep) ** 2
                sig_p = 4 * np.pi / LAM ** 2 * np.abs(Ep) ** 2
                sig_f = 4 * np.pi / LAM ** 2 * np.abs(E) ** 2
                per[law][f"{el:+.0f}"] = dict(
                    sigma_lin_mean_dbsm=round(float(10 * np.log10(sig.mean())), 4),
                    sigma_db_mean_dbsm=round(float(np.mean(10 * np.log10(sig + 1e-300))), 4),
                    prop_only_dbsm=round(float(10 * np.log10(sig_p.mean())), 4),
                    frame_only_dbsm=round(float(10 * np.log10(sig_f.mean())), 4),
                    prop_minus_total_db=round(float(10 * np.log10(sig_p.mean()
                                                                  / sig.mean())), 4))
            print(f"  J7 {key}/{law} {time.time()-t0:.1f}s", flush=True)
        d = {}
        for law in LAWS[1:]:
            d[law] = {f"{el:+.0f}": dict(
                d_sigma_lin_db=round(per[law][f"{el:+.0f}"]["sigma_lin_mean_dbsm"]
                                     - per["legacy"][f"{el:+.0f}"]["sigma_lin_mean_dbsm"], 4),
                d_sigma_dbmean_db=round(per[law][f"{el:+.0f}"]["sigma_db_mean_dbsm"]
                                        - per["legacy"][f"{el:+.0f}"]["sigma_db_mean_dbsm"], 4),
                d_prop_only_db=round(per[law][f"{el:+.0f}"]["prop_only_dbsm"]
                                     - per["legacy"][f"{el:+.0f}"]["prop_only_dbsm"], 4),
                prop_share_db=per["legacy"][f"{el:+.0f}"]["prop_minus_total_db"])
                for el in els}
        out[key] = dict(per_law=per, delta=d)
    #: 지금 앵커가 얼마나 맞는가 — 저장소 원장 그대로 읽는다
    anc = json.load(open(os.path.join(ROOT, "outputs", "audit_rcs_anchors.json")))
    q1 = anc["Q1_absolute_anchor"]
    state = dict(
        source="outputs/audit_rcs_anchors.json :: Q1_absolute_anchor",
        self_measurement_count=q1["self_measurement_count"],
        our_band_level_err_db=q1["distance_to_ledger_now"]["our_operating_band_1p8_6p0"][
            "level_err_mean_db"],
        per_band_err_db=q1["distance_to_ledger_now"]["per_band_ours_minus_yuan_curve_db"],
        production_anchor_mode=q1["what_the_anchor_moves"]["production_mode"],
        anchor_moves=q1["what_the_anchor_moves"]["moves"])
    try:
        das = json.load(open(os.path.join(ROOT, "outputs", "das_fleet_validation.json")))
        state["das_fleet"] = das.get("verdict") or das.get("summary") or list(das.keys())
    except Exception as e:                                          # noqa: BLE001
        state["das_fleet"] = f"읽기 실패: {e}"
    return dict(per_airframe=out, anchor_state_now=state)


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    res = {}
    print("J1 …", flush=True)
    res["J1_planform_three_laws"] = part_J1()
    print("J2 …", flush=True)
    J2, series = part_J2()
    res["J2_slowtime_three_laws"] = J2
    print("J3 …", flush=True)
    res["J3_between_class_separation"] = part_J3(series)
    print("J4 …", flush=True)
    res["J4_comb_classifier"] = part_J4(series)
    print("J5 …", flush=True)
    res["J5_r50"] = part_J5(J2) | {"anchor_cancellation": anchor_cancellation_probe()}
    print("J6 …", flush=True)
    res["J6_engine_margin"] = part_J6(J2)
    print("J7 …", flush=True)
    res["J7_sigma_anchor"] = part_J7()

    res["_meta_J"] = dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/adv_consequence_recheck_0816.py",
        gpu="사용 안 함(CPU 전용) — Sionna/Mitsuba import 0 회",
        kernel="pure PO point cloud (src/rcs_po.py), spacing λ/7, 가림 없음",
        fc_hz=FC, prf_hz=PRF, n_poses=N_POSES, az_deg=AZ_DEG, els=ELS, laws=LAWS,
        gamma_per_material={k: float(v) for k, v in GAMMA_MAT.items()},
        elapsed_s=round(time.time() - t0, 1))

    old = {}
    if os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8"))
    old.update(res)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=1)
    print(f"wrote {OUT}  ({time.time()-t0:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
