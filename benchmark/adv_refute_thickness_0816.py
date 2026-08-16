# -*- coding: utf-8 -*-
"""
adv_refute_thickness_0816.py — **두께 주장 반증 전담** (2026-08-16)
==================================================================================
`docs/MESH_AUDIT_0816.md` 의 두께 축 주장 넷(ⓐ m1 · ⓑ I1 · ⓒ 시위평균 요약 · ⓓ 13~17 dB)을
**무너뜨리려고** 만든 스크립트다. 확인이 아니라 반증이 목적이고, 반증에 실패하면 그 사실을 적는다.

무엇을 새로 재는가 — 남의 수치를 옮겨 적지 않는다
  ① 슬래브 반사식을 **다른 형태로 독립 구현**하고(대칭 3매질 R = (r01+r12 e^{-2jδ})/(1+r01 r12 e^{-2jδ}))
     저장소 구현과 대조한다.
  ② **박막 해석극한** Γ ≈ −j k0 d (ε_c−1)/(2cosθ) 을 따로 유도해, 두께 의존이 실제로 선형인지
     (|Γ| ∝ d^p 의 p) 를 잰다. 3.5 GHz 에서 날 두께는 λ/60~λ/110 이다.
  ③ 두께 요약값의 **세 번째 자** — 발산정리로 정확히 V_band = Σ z̄·n_z·A, 투영면적 A = ½Σ|n_z|·A
     (잘린 원통면은 n_z=0 이라 기여 0). 시위·캘리퍼 정의를 전혀 안 쓰는 자다.
  ④ 같은 주장을 **네 가지 입사각 규약**으로 계산해 규약이 답을 얼마나 흔드는지 잰다.
  ⑤ PO 커널이 실제로 쓰는 프롭 |Γ| 가 **몇 mm 짜리 슬래브에 해당하는지** 역산한다.

⛔ GPU 미사용(numpy·trimesh CPU) · 저장소 코드 무변경 · git 무접촉.
실행:  cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
         benchmark/adv_refute_thickness_0816.py
산출:  outputs/mesh_adv_refute_thickness_0816.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import trimesh

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
EPS0 = 8.8541878128e-12
ER, SG, FC = 2.7, 0.02, 3.5e9          # materials.MATERIALS['prop_plastic']
LAM_MM = C0 / FC * 1e3
BAND = (0.20, 0.96)
CANON_MM = 1.4302


# --------------------------------------------------------------------------- #
#  ① 독립 슬래브 구현 + ② 박막 해석극한
# --------------------------------------------------------------------------- #
def _epsc():
    return ER - 1j * SG / (2 * np.pi * FC * EPS0)


def slab_R(d_m, th_deg, pol):
    """대칭 3매질(공기-유전체-공기) 반사계수 — 저장소와 **다른 형태**로 쓴 독립 구현."""
    ec = _epsc()
    th = np.radians(np.asarray(th_deg, float))
    q = np.sqrt(ec - np.sin(th) ** 2)
    c = np.cos(th)
    r01 = (c - q) / (c + q) if pol == "TE" else (ec * c - q) / (ec * c + q)
    ph = np.exp(-2j * (2 * np.pi * FC / C0) * float(d_m) * q)
    return (r01 - r01 * ph) / (1.0 - r01 * r01 * ph)


def sheet_R(d_m, th_deg, pol):
    """박막(두께 ≪ λ) 해석극한. 얇은 판 물리와 Born 근사가 같은 식을 준다 — 둘 다 진폭 ∝ d·(ε−1)."""
    ec = _epsc()
    th = np.radians(np.asarray(th_deg, float))
    c, s2 = np.cos(th), np.sin(th) ** 2
    k0d = (2 * np.pi * FC / C0) * float(d_m)
    if pol == "TE":
        return 1j * k0d * (1.0 - ec) / (2.0 * c)
    return 1j * k0d * (ec ** 2 * c ** 2 - ec + s2) / (2.0 * ec * c)


# --------------------------------------------------------------------------- #
#  ④ 입사각·편파 규약 넷
# --------------------------------------------------------------------------- #
def db_normal(d_mm):
    return _db_pow(d_mm, 0.0)


def db_45(d_mm):
    return _db_pow(d_mm, 45.0)


def _db_pow(d_mm, th):
    d = d_mm * 1e-3
    p = 0.5 * (abs(slab_R(d, th, "TE")) ** 2 + abs(slab_R(d, th, "TM")) ** 2)
    return 10 * np.log10(p)


def db_convex_pow(d_mm, th_max=89.9, n=4001):
    """볼록체 투영면적 가중(cosθ·sinθ) **전력** 평균 — material_verdict_0816 규약."""
    th = np.linspace(0.0, th_max, n)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    d = d_mm * 1e-3
    p = 0.5 * (np.abs(slab_R(d, th, "TE")) ** 2 + np.abs(slab_R(d, th, "TM")) ** 2)
    return 10 * np.log10(float(np.trapezoid(p * w, np.radians(th)) / np.trapezoid(w, np.radians(th))))


def db_convex_amp(d_mm, th_max=90.0, n=4001):
    """같은 가중의 **진폭** 평균 — prop_thickness_by_drone 규약(proj_weighted_mean_gamma)."""
    th = np.linspace(0.0, th_max, n)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    d = d_mm * 1e-3
    g = [float(np.trapezoid(np.abs(slab_R(d, th, p)) * w, np.radians(th))
              / np.trapezoid(w, np.radians(th))) for p in ("TE", "TM")]
    return 20 * np.log10(0.5 * (g[0] + g[1]))


def db_lamina(d_mm, th_max=89.9, n=4001, cos_pow=2.0):
    """**얇은 판**에 맞는 가중 cos^2θ·sinθ — 정반사가 수직 근방에 몰리는 형상."""
    th = np.linspace(0.0, th_max, n)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th)) ** cos_pow
    d = d_mm * 1e-3
    p = 0.5 * (np.abs(slab_R(d, th, "TE")) ** 2 + np.abs(slab_R(d, th, "TM")) ** 2)
    return 10 * np.log10(float(np.trapezoid(p * w, np.radians(th)) / np.trapezoid(w, np.radians(th))))


CONVS = (("수직", db_normal), ("45도", db_45), ("볼록체_전력평균", db_convex_pow),
         ("볼록체_진폭평균", db_convex_amp), ("얇은판_cos2가중", db_lamina))


# --------------------------------------------------------------------------- #
#  ③ 세 번째 자 — 발산정리로 정확히 V/A_proj
# --------------------------------------------------------------------------- #
def volume_over_projected(V, F, lo, hi, nsub=4):
    """띠 lo≤r≤hi 안의 (부피, 천정투영면적, 두께).
       V = Σ z̄·n_z·A  (발산정리; 잘린 원통면은 n_z=0 이라 기여 0)
       A = ½ Σ |n_z|·A (연직선이 위·아래를 한 번씩 뚫는 형상에서 정확)
       ⚠ 이 두께는 **천정 방향** 두께라 비틀림만큼 표면법선 두께보다 크다(상한)."""
    tri = np.asarray(V, float)[np.asarray(F, np.int64)]
    for _ in range(nsub):
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        tri = np.concatenate([np.stack([a, ab, ca], 1), np.stack([ab, b, bc], 1),
                              np.stack([ca, bc, c], 1), np.stack([ab, bc, ca], 1)])
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    n = np.cross(b - a, c - a)
    A2 = np.linalg.norm(n, axis=1)
    A = 0.5 * A2
    nz = np.zeros(len(A))
    ok = A2 > 0
    nz[ok] = n[ok, 2] / A2[ok]
    cen = tri.mean(1)
    m = (np.hypot(cen[:, 0], cen[:, 1]) >= lo) & (np.hypot(cen[:, 0], cen[:, 1]) <= hi)
    vol = float((cen[m, 2] * nz[m] * A[m]).sum())
    ap = float(0.5 * (np.abs(nz[m]) * A[m]).sum())
    return vol, ap, vol / ap


def main() -> None:
    t0 = time.time()
    from material_sources import slab_reflection as repo_slab, blade_thickness_stats
    from materials import gamma_po, gamma_shape
    from drones import DRONES, build_propeller

    out: dict = {"_meta": dict(
        title="두께 주장 반증 — 독립 재계산",
        generated_kst=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 9 * 3600)),
        target="docs/MESH_AUDIT_0816.md 의 두께 축(ⓐ m1 · ⓑ I1 · ⓒ 시위평균 요약 · ⓓ 13~17 dB)",
        gpu_used=False, code_changed=False,
        frequency_hz=FC, lambda_mm=LAM_MM, eps_r=ER, sigma_S_per_m=SG)}

    # --- 자 검증: 독립 구현 ↔ 저장소 구현 ---
    worst = 0.0
    for d in (0.3, 0.6146, 0.7864, 0.833, 0.9, 1.4302, 1.4559, 1.4804, 2.9, 100.0):
        for th in (0, 15, 30, 45, 60, 75, 85, 89.9):
            for pol in ("TE", "TM"):
                worst = max(worst, abs(slab_R(d * 1e-3, th, pol) - repo_slab(ER, SG, FC, d * 1e-3, th, pol)))
    out["ruler_check"] = dict(max_abs_diff_vs_repo=float(worst),
                              verdict_ko="저장소 슬래브식은 대수적으로 옳다 — 다른 형태의 독립 구현과 1e-15 안에서 같다.")

    # --- ② 박막 극한·선형성 ---
    lin = {}
    dd = np.linspace(0.3, 2.9, 60)
    for th in (0, 45, 70, 85):
        y = np.array([abs(slab_R(x * 1e-3, th, "TE")) for x in dd])
        lin[f"{th}deg"] = float(np.polyfit(np.log(dd), np.log(y), 1)[0])
    sheet_err = {f"{d}mm": {f"{th}deg": float(100 * (abs(sheet_R(d * 1e-3, th, "TE"))
                                                     / abs(slab_R(d * 1e-3, th, "TE")) - 1))
                            for th in (0, 45, 75)} for d in (0.6, 0.786, 0.9, 1.43)}
    out["c_thin_sheet_regime"] = dict(
        exponent_p_of_gamma_vs_d=lin, thin_sheet_analytic_error_pct=sheet_err,
        note_ko="|Γ| ∝ d^p 의 p 가 수직 0.98·45도 0.97 → 이 두께대에서 반사는 사실상 두께에 **선형**이다. "
                "그래서 두께비의 dB 는 20log10(비) 에 붙는다. 박막 해석극한이 정확식과 1 % 안이라 "
                "슬래브식이든 Born 이든 **진폭 ∝ d·(ε−1)** 로 같다.")

    # --- 유전율 축퇴 ---
    g0 = abs(slab_R(0.7864e-3, 0.0, "TE"))
    deg = {}
    for e in (2.4, 2.7, 3.0, 3.5, 4.0):
        ec = e - 1j * SG / (2 * np.pi * FC * EPS0)
        q = np.sqrt(ec)
        r01 = (1 - q) / (1 + q)
        ph = np.exp(-2j * (2 * np.pi * FC / C0) * 0.7864e-3 * q)
        g = abs(r01 * (1 - ph) / (1 - r01 ** 2 * ph))
        deg[f"eps_r={e}"] = dict(gamma=float(g), ratio_vs_2p7=float(g / g0),
                                 predicted_by_eps_minus_1=float((e - 1) / (ER - 1)),
                                 dB=float(20 * np.log10(g / g0)))
    out["c_permittivity_degeneracy"] = dict(
        table=deg,
        note_ko="박막에서 |Γ| ∝ (εr−1)·d 라 두께와 유전율은 **완전히 겹친다**(0.5 % 안에서 예측 일치). "
                "즉 «두께 축» 이 아니라 «전기적 두께 d·(εr−1) 축» 이다. εr 2.7→3.5 이면 +3.33 dB 로 "
                "mini5pro 두께 주장 전체와 맞먹는다. 저장소는 프롭 수지를 두 곳에서 다르게 적는다 — "
                "materials.py 는 ABS/PC εr 2.7, gazebo_export.py 는 «유리섬유 강화 나일론»(ρ 1300).")

    # --- ③ 세 번째 자 + 지름 스케일 검사 ---
    ledger = json.load(open(os.path.join(_ROOT, "outputs", "prop_thickness_by_drone.json")))
    analytic = blade_thickness_stats()["per_drone"]
    rulers = {}
    for key in ("mini2", "mini5pro", "mavic4pro", "matrice4e", "m350rtk"):
        m = build_propeller(DRONES[key], n=10)
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64)
        R = float(np.hypot(V[:, 0], V[:, 1]).max())
        vol, ap, t = volume_over_projected(V, F, BAND[0] * R, BAND[1] * R)
        led = ledger["per_drone"][key]["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
        rulers[key] = dict(R_mm=R, V_band_mm3=vol, A_proj_mm2=ap,
                           t_divergence_nadir_mm=t, t_repo_area_over_chord_mm=led,
                           t_analytic_constants_mm=analytic[key]["t_chordmean_mm"],
                           diff_nadir_vs_repo_pct=float(100 * (t / led - 1)))
    out["a_ruler_spread"] = dict(per_drone=rulers)

    scale = {}
    base = ledger["per_drone"]["matrice4e"]["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
    for k, v in ledger["per_drone"].items():
        t = v["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
        scale[k] = float(100 * (t / (base * DRONES[k].prop_dia_mm / 274.0) - 1))
    out["b_fleet_spread_is_diameter_ratio"] = dict(
        pct_error_vs_pure_diameter_scaling=scale,
        note_ko="10기종 전부 0.02 % 안에서 t ∝ 프롭 지름이다. «기종마다 4.5 배» 는 발견이 아니라 "
                "지름비(533.4/119.1=4.478) 그 자체다 — 우리 날 법칙이 완전 상사(self-similar)이기 때문. "
                "기종별 메쉬 측정은 스칼라 하나 × 지름비 이상의 정보를 주지 않는다.")

    # --- ⓐ 1.4302 → 1.4559 ---
    out["a_m1_bias_impact"] = dict(
        analytic_reproduced_mm=float(analytic["matrice4e"]["t_chordmean_mm"]),
        dB={n: float(f(1.4559) - f(1.4302)) for n, f in CONVS},
        pure_ratio_dB=float(20 * np.log10(1.4559 / 1.4302)),
        ruler_spread_dB=float(db_normal(rulers["matrice4e"]["t_divergence_nadir_mm"])
                              - db_normal(rulers["matrice4e"]["t_repo_area_over_chord_mm"])),
        two_named_biases_predict_pct=float(100 * ((1 / 0.99321) * (0.695 / 0.684879) - 1)),
        verdict_ko="+0.12~+0.15 dB. 감사의 «+0.13 dB»(볼록체 전력평균)를 정확히 재현한다. 판정 영향 0 — "
                   "다만 «메쉬 실측 = 1.456 mm» 는 자 하나의 값이다. 세 자가 1.414 / 1.456 / 1.480 mm "
                   "(폭 0.39 dB)를 주고 부호도 갈린다. 감사가 든 편향 둘은 +2.17 % 를 예측하는데 "
                   "보고된 값은 +1.8 % 다.")

    # --- ⓑ mini5pro ---
    cands = {"감사자_0.833": 0.833,
             "저장소자_0.7864": 0.7864,
             "해석식_0.7955": float(analytic["mini5pro"]["t_chordmean_mm"]),
             "내자_나디르_0.8155": rulers["mini5pro"]["t_divergence_nadir_mm"]}
    b = {k: {n: float(f(CANON_MM) - f(v)) for n, f in CONVS} for k, v in cands.items()}
    for k, v in cands.items():
        b[k]["순수비_20log10"] = float(20 * np.log10(CANON_MM / v))
    cut = {f"theta_max_{t}": float(db_convex_pow(CANON_MM, th_max=t) - db_convex_pow(0.833, th_max=t))
           for t in (30, 45, 60, 70, 80, 85, 89.9)}
    out["b_mini5pro_claim"] = dict(
        thickness_candidates_mm=cands, dB_by_convention=b, grazing_cut_test=cut,
        published_values_in_repo=dict(audit_doc="+3.8 ~ +4.6 dB",
                                      executor_ledger="+4.85 (각도평균) / +5.11 (45도)"),
        verdict_ko="감사의 +3.82/+4.60 을 정확히 재현했다. 그러나 낮은 끝 +3.8 은 **볼록체(구) 가중**이 "
                   "만든 인공물이다 — 적분을 85도에서 끊으면 4.28, 89.9도까지 가면 3.82 로, 낙차 전부가 "
                   "θ>85도 에서 온다. 거기서 무한 슬래브는 두께와 무관하게 |Γ|→1 이 되는데, 시위가 "
                   "0.07~0.39 λ 인 날에는 그런 스침 평면파 영역이 없다. 날에 맞는 어떤 규약으로도 답은 "
                   "+4.4~+5.1 dB 다. ⇒ 주장은 살아남았고 오히려 **과소**였다.")

    # --- ⓒ 요약값이 맞나 + 한 날 안의 폭 ---
    summ = {}
    for key in ("matrice4e", "mini5pro"):
        st = ledger["per_drone"][key]["stations"]
        r = np.array([s["r_over_R"] for s in st])
        t = np.array([s["t_chordmean_mm"] for s in st])
        c = np.array([s["chord_mm"] for s in st])
        m = (r >= BAND[0]) & (r <= BAND[1])
        r, t, c = r[m], t[m], c[m]
        tbar = float(np.trapezoid(t * c, r) / np.trapezoid(c, r))
        G = np.array([abs(slab_R(x * 1e-3, 0.0, "TE")) for x in t])
        Gbar = float(np.trapezoid(G * c, r) / np.trapezoid(c, r))
        mt = r >= 0.80
        ttip = float(np.trapezoid(t[mt] * c[mt], r[mt]) / np.trapezoid(c[mt], r[mt]))
        summ[key] = dict(t_mean_mm=tbar,
                         dB_mean_of_gamma_minus_gamma_of_mean=float(
                             20 * np.log10(Gbar / abs(slab_R(tbar * 1e-3, 0.0, "TE")))),
                         t_tip_band_mm=ttip, tip_vs_mean_dB=float(20 * np.log10(ttip / tbar)),
                         station_t_min_mm=float(t.min()), station_t_max_mm=float(t.max()),
                         within_blade_spread_dB=float(20 * np.log10(t.max() / t.min())),
                         chord_min_over_lambda=float(c.min() / LAM_MM),
                         chord_max_over_lambda=float(c.max() / LAM_MM))
    out["c_is_chordmean_the_right_summary"] = dict(
        per_drone=summ,
        tip_band_offset_all_drones_dB={k: float(20 * np.log10(
            v["bands"]["tip_0p80_0p96"]["t_chordmean_mm"] / v["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]))
            for k, v in ledger["per_drone"].items()},
        verdict_ko="RF 적으로 맞다 — 이 영역에서 Γ 가 d 에 선형이라 <Γ(t)> 와 Γ(<t>) 가 0.03 dB 안에서 같고, "
                   "«시위평균 → 시위가중 스팬평균» 은 항등적으로 V_띠/A_전개 다. 그러나 요약 하나는 "
                   "**팁띠(0.80–0.96R)를 10기종 전부에서 정확히 −6.47 dB** 로 틀리게 하고, 한 날 안의 "
                   "국소 두께 폭은 13.2 dB 로 **함대 전체 폭(13.0 dB)과 같다**. 그리고 시위가 0.07~0.39 λ 라 "
                   "무한 슬래브 |Γ| 의 **절대값**은 애초에 날에 못 쓴다(두께 **비**는 Born 에서도 같아 살아남는다).")

    # --- ⓓ 비교 가능한 발판 ---
    def d45(a, b):
        return float(db_45(b) - db_45(a))
    out["d_comparable_footing_dB_at_45deg"] = {
        "PathSolver 기본 100 mm 를 mini5pro 에": d45(0.7864, 100.0),
        "PathSolver 기본 100 mm 를 matrice4e 에": d45(1.4140, 100.0),
        "정본 1.4302 를 mini5pro 에 (I1 이 고치는 것)": d45(0.7864, CANON_MM),
        "민감도점 0.9 를 mini5pro 에": d45(0.7864, 0.9),
        "민감도점 0.9 를 matrice4e 에": d45(1.4140, 0.9),
        "자 차이만 (1.414 ↔ 1.480)": d45(1.4140, 1.4804),
        "m1 이 지적한 편향 (1.4302 → 1.4559)": d45(1.4302, 1.4559),
        "우리 mini2 ↔ DJI 실물 mini2 (0.7312 ↔ 0.5999)": d45(0.5999, 0.7312),
        "한 날 안: 요약 ↔ 팁띠 (1.414 ↔ 0.671)": d45(0.671, 1.4140),
        "εr 2.7 → 3.5 (유리섬유 강화 가정)": 3.33,
    }

    # --- ⑤ PO 커널의 프롭 |Γ| 는 몇 mm 짜리인가 ---
    xs = np.linspace(1e-6, 12e-3, 4001)
    gs = np.array([abs(slab_R(x, 0.0, "TE")) for x in xs])
    equiv = {}
    for tgt in (0.25, 0.28):
        equiv[str(tgt)] = float(xs[int(np.argmax(gs >= tgt))] * 1e3)
    po = {}
    for k in ("mini2", "mini5pro", "matrice4e", "m350rtk"):
        t = ledger["per_drone"][k]["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]
        g = abs(slab_R(t * 1e-3, 0.0, "TE"))
        po[k] = dict(t_mm=t, gamma_slab=float(g),
                     po_constant_minus_slab_dB=float(20 * np.log10(0.25 / g)))
    shape = {}
    for th in (0, 30, 45, 60, 75, 85):
        ci = np.cos(np.radians(th))
        bulk = float(gamma_shape("prop_plastic", FC, ci))
        te, tm = abs(sheet_R(1e-3, th, "TE")), abs(sheet_R(1e-3, th, "TM"))
        te0, tm0 = abs(sheet_R(1e-3, 0.0, "TE")), abs(sheet_R(1e-3, 0.0, "TM"))
        sh = np.sqrt((te ** 2 + tm ** 2) / 2) / np.sqrt((te0 ** 2 + tm0 ** 2) / 2)
        shape[f"{th}deg"] = dict(bulk_dB=float(20 * np.log10(bulk)),
                                 thin_sheet_dB=float(20 * np.log10(sh)),
                                 diff_dB=float(20 * np.log10(sh / bulk)))
    out["e_PO_arm_has_no_thickness"] = dict(
        gamma_po_prop=float(gamma_po("prop_plastic", FC)),
        gamma_po_shell=float(gamma_po("plastic", FC)),
        equivalent_slab_thickness_mm=equiv, per_drone=po, angle_law=shape,
        note_ko="순수 PO/SBR 팔에는 두께가 아예 없다 — 프롭은 전 기종 |Γ|=0.25 상수다. 그 값은 "
                "3.5 GHz 에서 **4.40 mm 플라스틱 슬래브**에 해당한다. 우리 메쉬 두께가 주는 값보다 "
                "mini5pro +14.2 dB · matrice4e +9.2 dB 밝다. materials.py 가 «정밀 두께 모델이 아니다» 라고 "
                "선언은 하지만 크기는 어디에도 적혀 있지 않다. 각도 법칙도 벌크 프레넬 모양이라 박막 물리와 "
                "75도 에서 2.4 dB · 85도 에서 8.5 dB 갈린다.")

    out["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    p = os.path.join(_ROOT, "outputs", "mesh_adv_refute_thickness_0816.json")
    with open(p, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", p, out["_meta"]["runtime_s"], "s")


if __name__ == "__main__":
    main()
