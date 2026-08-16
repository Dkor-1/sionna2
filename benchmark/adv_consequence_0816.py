# -*- coding: utf-8 -*-
"""
adv_consequence_0816.py — «그래서 결과가 바뀌나» 를 무너뜨리는 라운드 (2026-08-16)
=================================================================================

무엇을 시험하나
---------------
`docs/MESH_AUDIT_0816.md` 의 프롭 형상 지적(시위 분포·c_max/R·팁)이 **맞다고 치고**,
그 형상 오차가 **우리가 실제로 내리는 판정**을 바꾸는지만 잰다. 네 갈래다.

  ⓐ 엔진 비교 (우리 커널 ↔ Sionna PathSolver) — 같은 메쉬라 상쇄되나
  ⓑ 분류 (기체 3종 구분) — 기체 간 **상대** 차이라 공통 오차는 지워지나
       ⚠ `CHORD_MAX_OVER_R` 이 기종마다 다르게 틀렸다면 공통이 아니다 → 그 크기를 잰다
  ⓒ 절대 판독거리 R50 — 형상 오차가 몇 % 를 움직이나
  ⓓ 반대 가능성 — 새 법칙이 우리 σ 앵커(문헌 RCS 정합)를 **더 나쁘게** 만들 수 있나

규약(전부 선언)
---------------
* **CPU 전용.** GPU 0 회. Sionna/Mitsuba import 0 회(그래서 재질 |Γ| 는 아래처럼 직접 계산).
* **코드 무변경.** 이 파일은 새로 추가된 읽기 전용 측정기다. 기존 소스는 import 만 한다.
* **산란 커널 = 순수 PO 점구름**(`src/rcs_po.py`). 가림 없음.
  감사가 C5 에서 쓴 렌즈와 같고, 탐지 사다리에 실제로 들어가는 σ 도 같은 렌즈다
  (`outputs/md_range_sweep_mf.json :: meta.engine = "pure PO point cloud, NO occlusion"`).
  ⚠ 생산 마이크로도플러 팔은 SBR(가림 있음)이다 — 절대 레벨을 이 파일에서 인용하면 안 되고,
    여기서 쓰는 것은 **같은 기하 두 판(legacy ↔ dji_mini2)의 비(比)** 뿐이다.
* **재질 |Γ|**: `src/materials.py` 표를 그대로 읽되 ITU 조회가 필요한 'metal' 만
  ITU-R P.2040 금속(εr=1, σ=1e7 S/m)으로 직접 프레넬 계산한다(코드 주석의 0.99980 재현).
* **각도의존 Γ(θ)**: 끔(rcs_po 의 기본 = 옵트인). 두 판의 비를 보는 데는 공통항이다.

산출: outputs/mesh_adv_refute_consequence_0816.json

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark \
    /workspace/.venvs/py312/bin/python benchmark/adv_consequence_0816.py
"""
from __future__ import annotations

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

#: ⚠ `src/materials.py` 는 **모듈 최상단에서 sionna.rt 를 import** 한다 — 그러면 drjit/mitsuba
#   스레드풀(200 여 개, 바쁜대기)이 뜨고, 다른 사람 작업이 도는 공용 머신에서 시스템 시간이
#   계산 시간의 8 배까지 치솟는다(실측). 그래서 **import 하지 않고 소스를 AST 로 읽는다** —
#   값의 출처는 여전히 그 파일 하나다.
EPS0 = 8.8541878128e-12                                                      # materials.EPS0

OUT = os.path.join(ROOT, "outputs", "mesh_adv_refute_consequence_0816.json")

FC = 3.5e9
LAM = C0 / FC
K = 2 * np.pi / LAM
SPACING = LAM / 7.0            # rcs_po 의 순수 PO 기본 간격
PRF = 19700.0                  # outputs/report07_three_engines.json :: _meta.prf_hz
N_POSES = 8192                 # 원장 팔과 같은 길이(_r15_n8192)
AZ_DEG = 0.0
RPM_LEDGER = [3808.36, 3791.64, 3795.402, 3804.598]
ELS = [0.0, -15.0, -30.0, -60.0]
CLASS_AIRFRAMES = ["mini5pro", "matrice4e", "s1000plus"]
ALL_KEYS = list(DRONES.keys())


# --------------------------------------------------------------------------- #
#  재질 |Γ| — Sionna 없이 (GPU 금지)
# --------------------------------------------------------------------------- #
def read_materials_table() -> dict:
    """`src/materials.py` 의 MATERIALS 를 **import 없이** AST 로 읽는다(위 주석 참조).
    `dict(...)` 호출의 리터럴 키워드만 뽑는다 — 실행되는 코드는 없다."""
    import ast
    src = open(os.path.join(ROOT, "src", "materials.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        tgt = getattr(node, "targets", [getattr(node, "target", None)])
        names = [t.id for t in tgt if isinstance(t, ast.Name)]
        if "MATERIALS" not in names:
            continue
        out = {}
        for k, v in zip(node.value.keys, node.value.values):
            d = {}
            for kw in v.keywords:
                try:
                    d[kw.arg] = ast.literal_eval(kw.value)
                except ValueError:
                    d[kw.arg] = None
            out[ast.literal_eval(k)] = d
        return out
    raise RuntimeError("materials.py 에서 MATERIALS 를 못 찾았다")


def gamma_map_cpu(fc: float = FC) -> tuple[dict, dict]:
    """그룹 → |Γ|. materials.MATERIALS 의 gamma_po 를 그대로 쓰고, 그것이 없는 ITU 재질은
    (εr, σ) 에서 벌크 프레넬로 계산한다. ITU 'metal' = εr 1, σ 1e7 S/m (ITU-R P.2040)."""
    MATERIALS = read_materials_table()
    itu_bulk = {"metal": (1.0, 1.0e7)}
    per_mat = {}
    for mat in {m for m, _ in DRONE_GROUP_MAT.values()}:
        spec = MATERIALS[mat]
        if "gamma_po" in spec:
            per_mat[mat] = float(spec["gamma_po"])
            continue
        if "itu" in spec:
            er, sg = itu_bulk[spec["itu"]]
        else:
            er, sg = float(spec["eps_r"]), float(spec["sigma"])
        eps_c = er - 1j * sg / (2 * np.pi * fc * EPS0)
        per_mat[mat] = float(abs((1.0 - np.sqrt(eps_c)) / (1.0 + np.sqrt(eps_c))))
    return {g: per_mat[m] for g, (m, _) in DRONE_GROUP_MAT.items()}, per_mat


GAMMA, GAMMA_MAT = gamma_map_cpu()


# --------------------------------------------------------------------------- #
#  배치 PO — 출하 커널과 비트급 일치를 검증하고 쓴다
# --------------------------------------------------------------------------- #
def po_field_batch(P, N, dA, w, V):
    """방향 여러 개(V: m×3)에 대한 복소 PO 장. rcs_po.po_field_dir 의 배치판."""
    out = np.empty(len(V), complex)
    amp = dA if w is None else dA * w
    #: ⚠청크를 작게 잡는다 — 큰 임시배열(수백 MB)을 매 반복 mmap/munmap 하면 공용 머신에서
    #   시스템 시간이 계산 시간을 넘는다(실측: utime 79 s 대 stime 305 s).
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


def verify_batch(P, N, dA, w, seed=7, n=5) -> float:
    rng = np.random.default_rng(seed)
    V = rng.standard_normal((n, 3))
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    ref = np.array([po_field_dir(P, N, dA, FC, v, w=w) for v in V])
    got = po_field_batch(P, N, dA, w, V)
    return float(np.max(np.abs(ref - got) / np.maximum(np.abs(ref), 1e-300)))


def look_dir(az_deg, el_deg):
    az, el = math.radians(az_deg), math.radians(el_deg)
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az),
                     math.sin(el)])


def rotz_T(u, theta_deg):
    """Rz(θ)ᵀ û — 로터 로컬 좌표에서 본 시선. θ 는 도[deg], (m,) 배열 허용."""
    t = np.radians(np.atleast_1d(theta_deg))
    c, s = np.cos(t), np.sin(t)
    return np.stack([c * u[0] + s * u[1], -s * u[0] + c * u[1],
                     np.full_like(c, u[2])], axis=-1)


# --------------------------------------------------------------------------- #
#  A. 평면형 — 형상 오차가 기종 공통인가 (ⓑ 의 전제)
# --------------------------------------------------------------------------- #
def part_A() -> dict:
    rows = {}
    for key in ALL_KEYS:
        spec = DRONES[key]
        R = float(spec.prop_dia_mm) / 2000.0
        rr = np.linspace(0.07, 1.0, 4000)
        out = {}
        for law in ("legacy", "dji_mini2"):
            cm, why = dc.resolve_chord_max_over_r(spec, law)
            frac_rr = dc.CHORD_RR if law == "legacy" else dc.CHORD_RR_DJI_MINI2
            frac = dc.CHORD_FRAC if law == "legacy" else dc.CHORD_FRAC_DJI_MINI2
            c = np.interp(rr, frac_rr, frac) * cm * R
            m = build_propeller(spec, blade_law=law)
            V, F = np.asarray(m.v, float), np.asarray(m.f, np.int64)
            ar = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]],
                                               V[F[:, 2]] - V[F[:, 0]]), axis=1)
            out[law] = dict(
                c_max_over_R=round(cm, 5), c_max_source=why,
                planform_area_m2=round(float(np.trapezoid(c, rr) * R), 8),
                outer_area_m2=round(float(np.trapezoid(
                    c[(rr >= 0.6) & (rr <= 0.96)], rr[(rr >= 0.6) & (rr <= 0.96)]) * R), 8),
                mesh_area_m2=round(float(ar.sum()), 8), n_tri=int(len(F)))
        d_tot = 10 * math.log10(out["dji_mini2"]["planform_area_m2"]
                                / out["legacy"]["planform_area_m2"])
        d_out = 10 * math.log10(out["dji_mini2"]["outer_area_m2"]
                                / out["legacy"]["outer_area_m2"])
        d_mesh = 10 * math.log10(out["dji_mini2"]["mesh_area_m2"]
                                 / out["legacy"]["mesh_area_m2"])
        rows[key] = dict(laws=out,
                         d_planform_area_db=round(d_tot, 3),
                         d_planform_area_pct=round(100 * (10 ** (d_tot / 10) - 1), 2),
                         d_outer_area_db=round(d_out, 3),
                         d_mesh_area_db=round(d_mesh, 3))
    dt = np.array([rows[k]["d_planform_area_db"] for k in ALL_KEYS])
    dc_ = np.array([rows[k]["d_outer_area_db"] for k in ALL_KEYS])
    sub = np.array([rows[k]["d_planform_area_db"] for k in CLASS_AIRFRAMES])
    return dict(
        per_airframe=rows,
        common_mode_test=dict(
            what_ko="법칙을 legacy→dji_mini2 로 갈면 기종마다 날 면적이 몇 dB 움직이나. "
                    "전 기종이 같은 값이면 «공통 오차» 라 상대 비교에서 지워진다.",
            fleet_span_db=round(float(dt.max() - dt.min()), 3),
            fleet_min_db=round(float(dt.min()), 3), fleet_max_db=round(float(dt.max()), 3),
            fleet_std_db=round(float(dt.std()), 3),
            outer_band_span_db=round(float(dc_.max() - dc_.min()), 3),
            classify_trio_span_db=round(float(sub.max() - sub.min()), 3),
            classify_trio=dict(zip(CLASS_AIRFRAMES, [round(float(x), 3) for x in sub]))))


# --------------------------------------------------------------------------- #
#  B. 슬로타임 PO — 두 판으로 같은 궤적을 돌려 AC·빗살을 잰다
# --------------------------------------------------------------------------- #
def rotor_phase_table(spec, n_poses: int) -> np.ndarray:
    """elevation_sweep_md.py 와 같은 규약: 원장 rpm 의 상대 산포를 기체 호버 rpm 에 얹는다."""
    from articulated_fast import rotor_phases
    rl = rotor_layout(spec)
    dirs = [r["dir"] for r in rl]
    rpms = np.asarray(RPM_LEDGER, float)
    base = float(spec.hover_rpm)
    rel = np.resize(rpms / np.mean(rpms), len(rl))
    rpms = base * rel
    return rotor_phases(np.arange(n_poses) / PRF, rpms, dirs), rpms


def slowtime(spec, law: str, els, n_poses: int = N_POSES):
    """(el → E(t)) + 부품별 진단. 프레임은 정지 → 상수, 프롭만 위상마다 돈다."""
    frame = build_frame(spec)
    Pf, Nf, dAf, wf = mesh_to_points(frame, SPACING, gamma=GAMMA)
    props = {+1: build_propeller(spec, blade_law=law),
             -1: build_propeller(spec, blade_law=law, mirror=True)}
    pts = {}
    for d, m in props.items():
        Pp, Np_, dAp, wp = mesh_to_points(m, SPACING, gamma=GAMMA)
        pts[d] = (Pp, Np_, dAp, wp)
    rl = rotor_layout(spec)
    ph, rpms = rotor_phase_table(spec, n_poses)
    res = {}
    for el in els:
        u = look_dir(AZ_DEG, el)
        E_frame = po_field_dir(Pf, Nf, dAf, FC, u, w=wf)
        E_prop = np.zeros(n_poses, complex)
        for i, rot in enumerate(rl):
            Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
            theta = rot["base_ang"] + ph[:, i]
            V = rotz_T(u, theta)
            phase_c = np.exp(1j * 2 * K * float(np.dot(rot["center"], u)))
            E_prop += phase_c * po_field_batch(Pp, Np_, dAp, wp, V)
        res[el] = dict(E=E_frame + E_prop, E_prop=E_prop, E_frame=complex(E_frame))
    return res, dict(n_frame_pts=int(len(dAf)),
                     n_prop_pts=int(len(pts[1][2])), n_rotors=len(rl),
                     rpm_per_rotor=[round(float(x), 3) for x in rpms],
                     batch_max_rel_err=round(verify_batch(*pts[1]), 12))


def band_masks(n, f_tip, f_flash, lo=0.35, hw=8.0):
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    band = (np.abs(fr) >= lo * f_tip) & (np.abs(fr) <= f_tip)
    kk = np.round(np.abs(fr) / f_flash)
    comb = band & (np.abs(np.abs(fr) - kk * f_flash) <= hw) & (kk >= 1)
    return band, comb


def series_stats(E, f_tip, f_flash):
    """detection_curves.py 규약 그대로: DC 제거 → hann → FFT → 빗살/대역 에너지."""
    n = E.size
    w = np.hanning(n)
    band, comb = band_masks(n, f_tip, f_flash)
    x = (E - E.mean()) * w
    P = np.abs(np.fft.fft(x)) ** 2
    sig = 4 * np.pi / LAM ** 2 * np.abs(E) ** 2
    return dict(sigma_mean_m2=float(sig.mean()),
                sigma_mean_dbsm=round(float(10 * np.log10(sig.mean())), 3),
                ac_power=float(np.abs(E - E.mean()).__pow__(2).mean()),
                comb_energy=float(P[comb].sum()),
                band_energy=float(P[band].sum()),
                total_ac_energy=float(P[np.abs(np.fft.fftfreq(n, 1 / PRF)) >= 8.0].sum()))


def part_B(els=ELS, n_poses=N_POSES):
    """반환 (원장 dict, 시계열 dict[(key, law, el)] = E)."""
    out, diag, series = {}, {}, {}
    for key in CLASS_AIRFRAMES:
        spec = DRONES[key]
        f_flash = spec.prop_blades * spec.hover_rpm / 60.0
        v_tip = math.pi * (spec.prop_dia_mm / 1000.0) * spec.hover_rpm / 60.0
        out[key] = {}
        for law in ("legacy", "dji_mini2"):
            t0 = time.time()
            res, dg = slowtime(spec, law, els, n_poses)
            diag[f"{key}/{law}"] = dg | {"secs": round(time.time() - t0, 1)}
            out[key][law] = {}
            for el in els:
                f_tip = 2.0 * v_tip / LAM * math.cos(math.radians(el))
                E, Ep = res[el]["E"], res[el]["E_prop"]
                series[(key, law, el)] = E
                st = series_stats(E, max(f_tip, 1e-6), f_flash)
                stp = series_stats(Ep, max(f_tip, 1e-6), f_flash)
                sig_prop = 4 * np.pi / LAM ** 2 * np.abs(Ep) ** 2
                sig_frame = 4 * np.pi / LAM ** 2 * abs(res[el]["E_frame"]) ** 2
                out[key][law][f"{el:+.0f}"] = dict(
                    f_tip_hz=round(f_tip, 2), f_flash_hz=round(f_flash, 3),
                    sigma_total_mean_dbsm=st["sigma_mean_dbsm"],
                    sigma_prop_mean_dbsm=round(float(10 * np.log10(sig_prop.mean())), 3),
                    sigma_frame_dbsm=round(float(10 * np.log10(sig_frame)), 3),
                    prop_share_of_total_db=round(float(
                        10 * np.log10(sig_prop.mean() / st["sigma_mean_m2"])), 3),
                    comb_energy=st["comb_energy"], band_energy=st["band_energy"],
                    total_ac_energy=st["total_ac_energy"],
                    comb_share=round(st["comb_energy"] / st["total_ac_energy"], 6),
                    prop_only_comb_energy=stp["comb_energy"])
            print(f"  B {key}/{law} {time.time()-t0:.1f}s", flush=True)
    # 판 간 차이표
    delta = {}
    for key in CLASS_AIRFRAMES:
        delta[key] = {}
        for el in els:
            a = out[key]["legacy"][f"{el:+.0f}"]
            b = out[key]["dji_mini2"][f"{el:+.0f}"]
            delta[key][f"{el:+.0f}"] = dict(
                d_sigma_total_db=round(b["sigma_total_mean_dbsm"] - a["sigma_total_mean_dbsm"], 3),
                d_sigma_prop_db=round(b["sigma_prop_mean_dbsm"] - a["sigma_prop_mean_dbsm"], 3),
                d_comb_energy_db=round(10 * math.log10(b["comb_energy"] / a["comb_energy"]), 3),
                d_band_energy_db=round(10 * math.log10(b["band_energy"] / a["band_energy"]), 3),
                d_total_ac_db=round(10 * math.log10(b["total_ac_energy"] / a["total_ac_energy"]), 3),
                d_comb_share_db=round(10 * math.log10(b["comb_share"] / a["comb_share"]), 3))
    return dict(rows=out, delta=delta, diag=diag), series


# --------------------------------------------------------------------------- #
#  C. 분류 — 저장소 자신의 분류기 함수를 그대로 쓴다
# --------------------------------------------------------------------------- #
def part_C(series, els=ELS) -> dict:
    import classify_airframe as CA
    lam = LAM
    cand = {a: DRONES[a].prop_blades * DRONES[a].hover_rpm / 60.0 for a in CA.AIRFRAMES}

    # (0) 자가검사 — 원장 팔로 저장소 발표값(정확도 1.0 / 여백 0.1312)을 재현하는가
    led = json.load(open(os.path.join(ROOT, "outputs", "elevation_sweep_md.json")))
    z = np.load(os.path.join(ROOT, "outputs", "elevation_sweep_md.npz"))
    self_check = {}
    for eng in ("ours", "sionna"):
        conf = np.zeros((3, 3), int); margins = []
        for i, a in enumerate(CA.AIRFRAMES):
            arm = CA.CHOSEN_ARM[eng][a]
            for el in (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0):
                key = f"{arm}/{CA.elkey_of(el)}"
                if key not in z.files:
                    continue
                E = np.asarray(z[key], complex)
                if E.size != CA.N_WIN * CA.WIN_LEN:
                    continue
                sc = CA.window_scores(E, PRF, cand)
                for w in range(sc.shape[0]):
                    j = int(np.argmax(sc[w]))
                    conf[i, j] += 1
                    s = np.sort(sc[w])[::-1]
                    margins.append(float((s[0] - s[1]) / max(s[0], 1e-30)))
        self_check[eng] = dict(confusion=conf.tolist(),
                               accuracy=round(float(np.trace(conf) / max(conf.sum(), 1)), 4),
                               n_windows=int(conf.sum()),
                               decision_margin_median=round(float(np.median(margins)), 4))

    # (1) 우리 PO 팔 — 판별로 분류
    per_law = {}
    for law in ("legacy", "dji_mini2"):
        conf = np.zeros((3, 3), int); margins = []; per_el = {}
        for el in els:
            c_el = np.zeros((3, 3), int)
            for i, a in enumerate(CA.AIRFRAMES):
                E = series[(a, law, el)]
                sc = CA.window_scores(E, PRF, cand)
                for w in range(sc.shape[0]):
                    j = int(np.argmax(sc[w]))
                    conf[i, j] += 1; c_el[i, j] += 1
                    s = np.sort(sc[w])[::-1]
                    margins.append(float((s[0] - s[1]) / max(s[0], 1e-30)))
            per_el[f"{el:+.0f}"] = dict(confusion=c_el.tolist(),
                                        accuracy=round(float(np.trace(c_el) / c_el.sum()), 4))
        per_law[law] = dict(confusion=conf.tolist(),
                            accuracy=round(float(np.trace(conf) / conf.sum()), 4),
                            n_windows=int(conf.sum()),
                            decision_margin_median=round(float(np.median(margins)), 4),
                            per_elevation=per_el)

    # (2) 창 단위로 «판을 갈면 결정이 뒤집히는가»
    flips, n_win = 0, 0
    score_shift = []
    for el in els:
        for a in CA.AIRFRAMES:
            s1 = CA.window_scores(series[(a, "legacy", el)], PRF, cand)
            s2 = CA.window_scores(series[(a, "dji_mini2", el)], PRF, cand)
            d1 = np.argmax(s1, axis=1); d2 = np.argmax(s2, axis=1)
            flips += int((d1 != d2).sum()); n_win += len(d1)
            score_shift.append(np.abs(s2 - s1).max())
    return dict(self_check_vs_repo_ledger=self_check, ours_po_arm=per_law,
                decision_flip=dict(n_windows=n_win, n_flipped=flips,
                                   flip_rate=round(flips / max(n_win, 1), 4),
                                   max_abs_score_shift=round(float(max(score_shift)), 4)))


# --------------------------------------------------------------------------- #
#  C2. 진짜 분류기(27 특징 RF) 의 특징이 판을 갈면 얼마나 움직이나
# --------------------------------------------------------------------------- #
def part_C2(series, els=ELS, win=4925) -> dict:
    """`benchmark/md_classify_dataset.features()` 를 **그대로 불러** 두 판의 특징을 잰다.
    잣대는 저장소가 발표한 클래스 내 표준편차(`outputs/md_classify.json :: feature_stats`).
    win=4925 표본 ≈ 0.25 s (원장 window_s 와 같은 길이, PRF 만 19.7 kHz)."""
    from md_classify_dataset import features, FEATURE_NAMES as FEATS
    stats = json.load(open(os.path.join(ROOT, "outputs", "md_classify.json")))["feature_stats"]
    names = list(FEATS)
    out = {}
    for key in CLASS_AIRFRAMES:
        per_el = {}
        for el in els:
            v = {}
            for law in ("legacy", "dji_mini2"):
                E = series[(key, law, el)][:win]
                vec, _ = features(E, PRF)
                v[law] = np.asarray(vec, float)
            d = v["dji_mini2"] - v["legacy"]
            rows = {}
            for i, nm in enumerate(names):
                sd = stats.get(nm, {}).get(key, {}).get("std")
                rows[nm] = dict(legacy=round(float(v["legacy"][i]), 4),
                                dji=round(float(v["dji_mini2"][i]), 4),
                                delta=round(float(d[i]), 4),
                                within_class_std=None if sd is None else round(float(sd), 4),
                                z=None if not sd else round(float(abs(d[i]) / sd), 3))
            zs = [r["z"] for r in rows.values() if r["z"] is not None]
            per_el[f"{el:+.0f}"] = dict(features=rows,
                                        z_max=round(max(zs), 3) if zs else None,
                                        z_median=round(float(np.median(zs)), 3) if zs else None,
                                        n_features_with_ruler=len(zs))
        out[key] = per_el
    # 클래스 간 거리(같은 잣대로) — z 를 읽을 기준
    sep = {}
    for nm in names:
        st = stats.get(nm)
        if not st:
            continue
        ks = [k for k in CLASS_AIRFRAMES if k in st]
        if len(ks) < 2:
            continue
        best = []
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, b = st[ks[i]], st[ks[j]]
                pool = math.sqrt(0.5 * (a["std"] ** 2 + b["std"] ** 2)) + 1e-30
                best.append(abs(a["mean"] - b["mean"]) / pool)
        sep[nm] = round(float(min(best)), 3)
    return dict(per_airframe=out, min_between_class_z=sep,
                ruler_ko="z = |Δ(판 교체)| / 클래스내 표준편차. min_between_class_z 는 "
                         "같은 잣대로 잰 **클래스 간** 최소 거리 — z 가 그보다 훨씬 작으면 "
                         "판 교체는 분류기가 못 느낀다.")


# --------------------------------------------------------------------------- #
#  D. R50 — detection_curves.py 의 사슬을 그대로 따라간다
# --------------------------------------------------------------------------- #
def part_D(B, series) -> dict:
    """SNR_comb ∝ c_anchor · (빗살 에너지),  c_anchor = σ_ref/⟨σ(el=−30)⟩ ⇒
       ΔSNR = Δ빗살(el) − Δ⟨σ⟩(el=−30),  R50 ∝ SNR^(1/4)."""
    rows = B["rows"]; out = {}
    for key in CLASS_AIRFRAMES:
        d30 = (rows[key]["dji_mini2"]["-30"]["sigma_total_mean_dbsm"]
               - rows[key]["legacy"]["-30"]["sigma_total_mean_dbsm"])
        per_el = {}
        for el in ELS:
            k = f"{el:+.0f}"
            dcomb = 10 * math.log10(rows[key]["dji_mini2"][k]["comb_energy"]
                                    / rows[key]["legacy"][k]["comb_energy"])
            dsnr = dcomb - d30
            per_el[k] = dict(d_comb_db=round(dcomb, 3), d_anchor_db=round(d30, 3),
                             d_snr_db=round(dsnr, 3),
                             d_R50_pct=round(100 * (10 ** (dsnr / 40) - 1), 2))
        out[key] = per_el
    # 원장 팔로 수치 검증 (AC 를 g 만큼 키워 실제 Pd 사슬을 다시 돌린다)
    out["numeric_check_on_repo_arm"] = r50_numeric_check(
        g_db=out["matrice4e"]["-30"]["d_snr_db"])
    return out


def r50_numeric_check(g_db: float, n_cal=20000, n_mc=400, seed=20260815) -> dict:
    """원장 «ours el−30» 팔의 AC 를 g_db 만큼 키워 R50 이 실제로 몇 % 움직이는지 잰다.
    detection_curves.py 와 같은 규약(잡음 N=kT0F·PRF, EIRP 30 dBm, Pfa 1e-3, 빗살 통계량)."""
    from rx_noise import RxSpec, anchor_scale, noise_power_w, sigma_kernel_m2, \
        sigma_ref_from_literature
    from link_budget import LinkBudget
    led = json.load(open(os.path.join(ROOT, "outputs", "elevation_sweep_md.json")))
    z = np.load(os.path.join(ROOT, "outputs", "elevation_sweep_md.npz"))
    E = np.asarray(z["ours_r15_n8192/el-30"], complex)
    row = [r for r in led["rows"]
           if r["engine"] == "ours_r15_n8192" and float(r["el_deg"]) == -30.0][-1]
    f_tip = float(row["f_tip_hz"]); f_flash = float(led["_meta"]["f_flash_hz"])
    n = E.size; w = np.hanning(n)
    band, comb = band_masks(n, f_tip, f_flash)
    spec = RxSpec(eirp_dbm=30.0)
    N_w = noise_power_w(spec, PRF)
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    ref = sigma_ref_from_literature(FC, "matrice4e")
    rng = np.random.default_rng(seed)
    # 문턱 — 잡음 전용
    T = []
    done = 0
    while done < n_cal:
        m = min(1500, n_cal - done)
        Z = (rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n))) * np.sqrt(N_w / 2)
        Zc = (Z - Z.mean(axis=1, keepdims=True)) * w
        P = np.abs(np.fft.fft(Zc, axis=1)) ** 2
        T.append(P[:, comb].sum(axis=1)); done += m
    thr = float(np.quantile(np.concatenate(T), 1 - 1e-3))
    Rg = np.geomspace(100.0, 10000.0, 41)
    res = {}
    for tag, g in (("base", 0.0), ("shifted", g_db)):
        amp = 10 ** (g / 20.0)
        Ex = E.mean() + amp * (E - E.mean())
        c = anchor_scale(Ex, FC, ref["sigma_ref_dbsm"])["c_anchor"]
        sig = sigma_kernel_m2(Ex, FC) * c
        phase = np.where(np.abs(Ex) > 0, Ex / np.maximum(np.abs(Ex), 1e-300), 1.0)
        pd = []
        for R in Rg:
            P_echo = lb.echo_power_w(LAM, sig, R, R)
            x0 = np.sqrt(P_echo) * phase
            X = x0[None, :] + (rng.standard_normal((n_mc, n))
                               + 1j * rng.standard_normal((n_mc, n))) * np.sqrt(N_w / 2)
            Xc = (X - X.mean(axis=1, keepdims=True)) * w
            P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
            pd.append(float((P[:, comb].sum(axis=1) > thr).mean()))
        pd = np.array(pd)
        i = np.argmax(pd < 0.5)
        if i == 0:
            r50 = None
        else:
            x0_, x1_ = math.log(Rg[i - 1]), math.log(Rg[i])
            y0_, y1_ = pd[i - 1], pd[i]
            r50 = float(math.exp(x0_ + (0.5 - y0_) * (x1_ - x0_) / (y1_ - y0_)))
        res[tag] = dict(R50_m=None if r50 is None else round(r50, 2))
    a, b = res["base"]["R50_m"], res["shifted"]["R50_m"]
    return dict(applied_db=round(g_db, 3), **res,
                measured_pct=None if not (a and b) else round(100 * (b / a - 1), 2),
                predicted_pct=round(100 * (10 ** (g_db / 40) - 1), 2),
                n_cal=n_cal, n_mc=n_mc, arm="ours_r15_n8192/el-30 (원장 SBR 팔)",
                method_ko="원장 팔의 AC 성분만 g dB 키우고 detection_curves 규약으로 Pd(R) 재계산")


# --------------------------------------------------------------------------- #
#  E. σ 앵커 — 새 법칙이 문헌 정합을 좋게 하나 나쁘게 하나
# --------------------------------------------------------------------------- #
def part_E(keys=("phantom3", "mini2", "m350rtk", "matrice4e", "mavic4pro"),
           els=(0.0, -15.0, -30.0), n_az=360) -> dict:
    az = np.arange(n_az) * (360.0 / n_az)
    out = {}
    for key in keys:
        spec = DRONES[key]
        rl = rotor_layout(spec)
        per = {}
        for law in ("legacy", "dji_mini2"):
            frame = build_frame(spec)
            Pf, Nf, dAf, wf = mesh_to_points(frame, SPACING, gamma=GAMMA)
            props = {+1: build_propeller(spec, blade_law=law),
                     -1: build_propeller(spec, blade_law=law, mirror=True)}
            pts = {d: mesh_to_points(m, SPACING, gamma=GAMMA) for d, m in props.items()}
            per[law] = {}
            for el in els:
                U = np.stack([look_dir(a, el) for a in az])
                E = po_field_batch(Pf, Nf, dAf, wf, U)
                Eprop = np.zeros(len(az), complex)
                for rot in rl:
                    Pp, Np_, dAp, wp = pts[1 if rot["dir"] > 0 else -1]
                    V = np.stack([rotz_T(u, rot["base_ang"])[0] for u in U])
                    ph = np.exp(1j * 2 * K * (U @ np.asarray(rot["center"], float)))
                    Eprop += ph * po_field_batch(Pp, Np_, dAp, wp, V)
                sig = 4 * np.pi / LAM ** 2 * np.abs(E + Eprop) ** 2
                sig_np = 4 * np.pi / LAM ** 2 * np.abs(E) ** 2
                sig_p = 4 * np.pi / LAM ** 2 * np.abs(Eprop) ** 2
                per[law][f"{el:+.0f}"] = dict(
                    sigma_lin_mean_dbsm=round(float(10 * np.log10(sig.mean())), 3),
                    sigma_db_mean_dbsm=round(float(np.mean(10 * np.log10(sig + 1e-300))), 3),
                    prop_only_dbsm=round(float(10 * np.log10(sig_p.mean())), 3),
                    frame_only_dbsm=round(float(10 * np.log10(sig_np.mean())), 3),
                    prop_minus_total_db=round(float(
                        10 * np.log10(sig_p.mean() / sig.mean())), 3))
        d = {}
        for el in els:
            k = f"{el:+.0f}"
            d[k] = dict(
                d_sigma_lin_db=round(per["dji_mini2"][k]["sigma_lin_mean_dbsm"]
                                     - per["legacy"][k]["sigma_lin_mean_dbsm"], 3),
                d_sigma_dbmean_db=round(per["dji_mini2"][k]["sigma_db_mean_dbsm"]
                                        - per["legacy"][k]["sigma_db_mean_dbsm"], 3),
                d_prop_only_db=round(per["dji_mini2"][k]["prop_only_dbsm"]
                                     - per["legacy"][k]["prop_only_dbsm"], 3),
                prop_share_db=per["legacy"][k]["prop_minus_total_db"])
        out[key] = dict(per_law=per, delta=d)
        print(f"  E {key} done", flush=True)
    return out


# --------------------------------------------------------------------------- #
#  F. 엔진 상쇄 — 같은 메쉬면 지워지나
# --------------------------------------------------------------------------- #
def part_F(series) -> dict:
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
    els_common = sorted(set.intersection(*[set(v) for v in gap.values()]))
    spread = {el: round(max(gap[a][el] for a in gap) - min(gap[a][el] for a in gap), 3)
              for el in els_common}

    # 우리 커널 안에서: 두 판의 시계열이 얼마나 다른가(모양 축)
    shape = {}
    for key in CLASS_AIRFRAMES:
        for el in (-30.0,):
            a = series[(key, "legacy", el)]; b = series[(key, "dji_mini2", el)]
            aa = a - a.mean(); bb = b - b.mean()
            coh = abs(np.vdot(aa, bb)) / (np.linalg.norm(aa) * np.linalg.norm(bb))
            Pa = np.abs(np.fft.fft(aa * np.hanning(a.size))) ** 2
            Pb = np.abs(np.fft.fft(bb * np.hanning(b.size))) ** 2
            cos_spec = float(np.dot(Pa, Pb) / (np.linalg.norm(Pa) * np.linalg.norm(Pb)))
            shape[f"{key}/el{el:+.0f}"] = dict(
                complex_coherence=round(float(coh), 4),
                spectrum_cosine=round(cos_spec, 4),
                d_ac_power_db=round(float(10 * np.log10((np.abs(bb) ** 2).mean()
                                                        / (np.abs(aa) ** 2).mean())), 3))
    return dict(ledger_engine_gap_db=gap, gap_spread_across_airframes_db=spread,
                our_two_laws_shape=shape)


# --------------------------------------------------------------------------- #
#  G. PathSolver 쪽이 형상에 반응하는 유일한 통로 — «거울점이 날 위에 있나»
# --------------------------------------------------------------------------- #
def part_G(keys=("matrice4e",), el=-30.0, n_poses=2048, tol_deg=(0.5, 1.0, 2.0)) -> dict:
    """PathSolver 의 정반사 진폭은 image-source 라 **면적과 무관**하다(저장소 실측:
    평판 변 0.2→4 m 에서 σ +52.04 dB 인데 RT 진폭은 1.8e-06 dB — outputs/rt_no_rcs_verify.json).
    그래서 그 팔이 날 형상에 반응할 수 있는 통로는 «거울점(법선∥시선)이 날 위에 있느냐»
    하나뿐이다. 그것이 판을 갈 때 바뀌는지 잰다."""
    out = {}
    for key in keys:
        spec = DRONES[key]
        rl = rotor_layout(spec)
        ph, _ = rotor_phase_table(spec, n_poses)
        u = look_dir(AZ_DEG, el)
        res = {}
        for law in ("legacy", "dji_mini2"):
            props = {+1: build_propeller(spec, blade_law=law),
                     -1: build_propeller(spec, blade_law=law, mirror=True)}
            geo = {}
            for d, m in props.items():
                V, F = np.asarray(m.v, float), np.asarray(m.f, np.int64)
                cr = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
                A = 0.5 * np.linalg.norm(cr, axis=1)
                n = cr / np.maximum(2 * A[:, None], 1e-300)
                #: 허브는 두 판이 같으므로 «날» 만 본다 — 중심에서 0.3R 밖 삼각형.
                cen = V[F].mean(axis=1)
                keep = np.hypot(cen[:, 0], cen[:, 1]) > 0.30 * (spec.prop_dia_mm / 2000.0)
                geo[d] = (n[keep], A[keep])
            best = np.zeros(n_poses); area = {t: np.zeros(n_poses) for t in tol_deg}
            for i, rot in enumerate(rl):
                n, A = geo[1 if rot["dir"] > 0 else -1]
                V = rotz_T(u, rot["base_ang"] + ph[:, i])          # (n_poses,3)
                NU = n @ V.T                                        # (F, n_poses)
                best = np.maximum(best, NU.max(axis=0))
                for t in tol_deg:
                    area[t] += (A[:, None] * (NU >= math.cos(math.radians(t)))).sum(axis=0)
            res[law] = dict(
                max_cos_median=round(float(np.median(best)), 6),
                specular_angle_median_deg=round(float(np.degrees(np.arccos(
                    np.clip(np.median(best), -1, 1)))), 4),
                pose_frac_with_specular={f"{t}deg": round(float((area[t] > 0).mean()), 4)
                                         for t in tol_deg},
                mean_specular_area_mm2={f"{t}deg": round(float(area[t].mean() * 1e6), 3)
                                        for t in tol_deg})
        d_area = {}
        for t in tol_deg:
            a = res["legacy"]["mean_specular_area_mm2"][f"{t}deg"]
            b = res["dji_mini2"]["mean_specular_area_mm2"][f"{t}deg"]
            d_area[f"{t}deg"] = (None if a <= 0 else round(10 * math.log10(b / a), 3))
        out[key] = dict(el_deg=el, n_poses=n_poses, per_law=res,
                        d_specular_area_db=d_area,
                        d_pose_frac={f"{t}deg": round(
                            res["dji_mini2"]["pose_frac_with_specular"][f"{t}deg"]
                            - res["legacy"]["pose_frac_with_specular"][f"{t}deg"], 4)
                            for t in tol_deg})
    return out


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def main():
    """인자를 주면 그 절만 다시 재고 기존 JSON 에 **덮어쓰기 병합**한다.
       예: `python benchmark/adv_consequence_0816.py C2 G`  (공용 머신에서 부분 재계산용)"""
    want = set(a.upper() for a in sys.argv[1:])
    if want:
        return partial(want)
    t0 = time.time()
    payload = {"_meta": dict(
        generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        generator="benchmark/adv_consequence_0816.py",
        gpu="사용 안 함 — numpy 전용, sionna/mitsuba import 0 회",
        kernel="rcs_po 순수 PO 점구름(가림 없음), spacing=λ/7, ANGLE_GAMMA off",
        fc_hz=FC, prf_hz=PRF, n_poses=N_POSES, az_deg=AZ_DEG,
        gamma_used=GAMMA, gamma_per_material=GAMMA_MAT)}
    payload["A_planform_common_mode"] = part_A()
    print("A 끝", round(time.time() - t0, 1), "s", flush=True)
    B, series = part_B()
    payload["B_slowtime_po"] = B
    print("B 끝", round(time.time() - t0, 1), "s", flush=True)
    payload["C_classification"] = part_C(series)
    payload["C2_md_classify_features"] = part_C2(series)
    print("C 끝", round(time.time() - t0, 1), "s", flush=True)
    payload["D_r50"] = part_D(B, series)
    print("D 끝", round(time.time() - t0, 1), "s", flush=True)
    payload["E_sigma_anchor"] = part_E()
    print("E 끝", round(time.time() - t0, 1), "s", flush=True)
    payload["F_engine_cancellation"] = part_F(series)
    print("F 끝", round(time.time() - t0, 1), "s", flush=True)
    payload["G_pathsolver_specular_channel"] = part_G()
    payload["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(payload, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("saved", OUT, round(time.time() - t0, 1), "s")


def partial(want: set):
    """부분 재계산 — 필요한 절만. 시계열은 필요한 길이·앙각만 만든다."""
    t0 = time.time()
    payload = json.load(open(OUT)) if os.path.exists(OUT) else {"_meta": {}}
    series = {}
    if want & {"C", "C2", "D", "F"}:
        els = [0.0, -30.0] if want & {"C2"} and not (want & {"C", "D", "F"}) else ELS
        n = 4925 if els == [0.0, -30.0] else N_POSES
        for key in CLASS_AIRFRAMES:
            for law in ("legacy", "dji_mini2"):
                res, dg = slowtime(DRONES[key], law, els, n)
                for el in els:
                    series[(key, law, el)] = res[el]["E"]
                print(f"  시계열 {key}/{law} n={n} {time.time()-t0:.0f}s", flush=True)
    if "C2" in want:
        payload["C2_md_classify_features"] = part_C2(series, els=els)
    if "G" in want:
        payload["G_pathsolver_specular_channel"] = part_G()
    if "E" in want:
        payload["E_sigma_anchor"] = part_E()
    payload["_meta"]["partial_rerun"] = dict(parts=sorted(want),
                                             at=time.strftime("%Y-%m-%d %H:%M:%S"),
                                             elapsed_s=round(time.time() - t0, 1))
    json.dump(payload, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("merged", sorted(want), "→", OUT, round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
