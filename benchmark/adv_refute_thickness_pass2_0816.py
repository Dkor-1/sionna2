# -*- coding: utf-8 -*-
"""
adv_refute_thickness_pass2_0816.py — **두께 주장 반증 2차** (2026-08-16)
==================================================================================
1차(`adv_refute_thickness_0816.py`)가 «자·규약·박막물리» 를 쟀다면, 이 2차는 감사 문서
`docs/MESH_AUDIT_0816.md` §4-3 의 **뼈대 문장 자체**를 공격한다.

무엇을 새로 재는가
  Ⓕ §4-3 의 «0.9 mm 는 DJI 실물 0.876 mm 와 2.7 % 안에서 일치» — **잣대가 섞였는지** 확인한다.
     저장소의 정밀 재계측 원장(`prop_measure_mini2_reference_0816.json`)이 같은 날을 여러 자로
     쟀으므로, 그 원장의 **스테이션 표를 내가 직접 적분해** 각 자의 시위가중 스팬평균을 낸다.
     얇은 판의 산란장은 ∫d dA(=부피)에 비례하므로 **슬래브 등가 두께 = 부피/평면형면적**이다.
     그 자로 재면 0.876 이 아니라 다른 수가 나오는지가 이 절의 판정이다.
  Ⓖ 저장소 안에 «각도평균» 이라는 이름이 **둘** 있다(진폭평균 ↔ 전력평균). 같은 주장에 대해
     몇 dB 어긋나는지, 그리고 감사 §4-3 표가 어느 쪽인지 역산한다.
  Ⓗ «13~17 dB» 의 기준점 100 mm 는 **파브리-페로 물결 위의 임의의 한 점**이다. 95~105 mm 를
     훑어 그 기준점 자체가 몇 dB 흔들리는지 잰다.
  Ⓘ 얇은 판에서 σ ∝ (두께 × 면적)² 이므로 «두께 축» 과 «형상 축» 은 같은 통화다. 잔여
     불확실도 예산을 한 규약(45° 전력)으로 모아 두 축을 나란히 놓는다.
  Ⓙ 요약 스칼라가 **언제 깨지나** — 날 두께 프로파일을 배율 s 로 키우며 ⟨Γ(t)⟩ 와 Γ(⟨t⟩) 가
     1 dB 갈리는 지점을 찾는다(= 시위평균 요약의 유효 상한).

⛔ GPU 미사용(numpy CPU) · 저장소 코드 무변경 · git 무접촉.
실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
         /workspace/.venvs/py312/bin/python benchmark/adv_refute_thickness_pass2_0816.py
산출:  outputs/mesh_adv_refute_thickness_0816.json  (1차 산출에 Ⓕ~Ⓙ 키를 덧붙인다)
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 299792458.0
EPS0 = 8.8541878128e-12
ER, SG, FC = 2.7, 0.02, 3.5e9
LAM_MM = C0 / FC * 1e3
BAND = (0.20, 0.96)
OUT = os.path.join(_ROOT, "outputs", "mesh_adv_refute_thickness_0816.json")


def _ec():
    return ER - 1j * SG / (2 * np.pi * FC * EPS0)


def slab_R(d_m, th_deg, pol="TE", er=None):
    ec = (er - 1j * SG / (2 * np.pi * FC * EPS0)) if er is not None else _ec()
    th = np.radians(np.asarray(th_deg, float))
    q = np.sqrt(ec - np.sin(th) ** 2)
    c = np.cos(th)
    r01 = (c - q) / (c + q) if pol == "TE" else (ec * c - q) / (ec * c + q)
    ph = np.exp(-2j * (2 * np.pi * FC / C0) * np.asarray(d_m, float) * q)
    return r01 * (1 - ph) / (1 - r01 ** 2 * ph)


def db_pow(d_mm, th, er=None):
    d = np.asarray(d_mm, float) * 1e-3
    p = 0.5 * (np.abs(slab_R(d, th, "TE", er)) ** 2 + np.abs(slab_R(d, th, "TM", er)) ** 2)
    return 10 * np.log10(p)


def db_convex_pow(d_mm, th_max=89.9, n=4001):
    """전력 평균 — material_verdict_0816 · 감사 §4-3 표 규약."""
    th = np.linspace(0.0, th_max, n)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    p = 0.5 * (np.abs(slab_R(d_mm * 1e-3, th, "TE")) ** 2
               + np.abs(slab_R(d_mm * 1e-3, th, "TM")) ** 2)
    return 10 * np.log10(float(np.trapezoid(p * w, np.radians(th)) / np.trapezoid(w, np.radians(th))))


def db_convex_amp(d_mm, th_max=90.0, n=721):
    """진폭 평균 — material_sources.proj_weighted_mean_gamma · prop_thickness 원장 규약."""
    th = np.linspace(0.0, th_max, n)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    g = [float(np.trapezoid(np.abs(slab_R(d_mm * 1e-3, th, p)) * w, np.radians(th))
               / np.trapezoid(w, np.radians(th))) for p in ("TE", "TM")]
    return 20 * np.log10(0.5 * (g[0] + g[1]))


def cw_mean(rr, chord, val, lo, hi):
    """시위가중 스팬평균 ∫ v·c dr / ∫ c dr (밴드 lo~hi)."""
    rr, chord, val = map(lambda a: np.asarray(a, float), (rr, chord, val))
    m = (rr >= lo) & (rr <= hi)
    return float(np.trapezoid(val[m] * chord[m], rr[m]) / np.trapezoid(chord[m], rr[m]))


def main() -> None:
    t0 = time.time()
    out = json.load(open(OUT))

    # ------------------------------------------------------------------ #
    # Ⓕ §4-3 의 0.876 mm — 잣대 대조
    # ------------------------------------------------------------------ #
    ref = json.load(open(os.path.join(_ROOT, "outputs",
                                      "prop_measure_mini2_reference_0816.json")))
    st = ref["F_reference_curve"]["stations_full"]
    rr = np.asarray(st["rr"], float)
    ch = np.asarray(st["chord_mm"], float)
    rulers = {"t_env_mean(=단면적/시위, 부피보존)": np.asarray(st["t_env_mean_mm"], float),
              "t_env_max(=최대두께)": np.asarray(st["t_env_max_mm"], float),
              "t_perp_max(=평균선수직 최대)": np.asarray(st["t_perp_max_mm"], float),
              "t_ray(=광선 중앙값)": np.asarray(st["t_ray_mm"], float)}
    windows = {"0.20-0.96R(감사 창)": (0.20, 0.96), "0.175-1.00R": (0.175, 1.0),
               "0.10-0.995R(전체)": (0.10, 0.995), "0.80-0.96R(팁띠)": (0.80, 0.96)}
    dji = {w: {k: cw_mean(rr, ch, v, *b) for k, v in rulers.items()} for w, b in windows.items()}
    # 면적가중(=시위가중과 같은 가중) 외에 «단순 스팬평균» 도 낸다 — 0.876 재현 경로 탐색
    dji_plain = {w: {k: float(np.mean(v[(rr >= b[0]) & (rr <= b[1])]))
                     for k, v in rulers.items()} for w, b in windows.items()}

    t_vol = dji["0.20-0.96R(감사 창)"]["t_env_mean(=단면적/시위, 부피보존)"]
    t_max = dji["0.20-0.96R(감사 창)"]["t_env_max(=최대두께)"]
    knob = 0.9
    ours_mini2 = json.load(open(os.path.join(_ROOT, "outputs", "prop_thickness_by_drone.json"))
                           )["per_drone"]["mini2"]["bands"]["headline_0p20_0p96"]["t_chordmean_mm"]

    out["f_audit_4_3_ruler_mismatch"] = dict(
        dji_mini2_chordweighted_mm=dji, dji_mini2_plain_spanmean_mm=dji_plain,
        audit_quoted_mm=0.876, audit_claim="0.9 mm 손잡이가 DJI 실물 0.876 mm 와 2.7 % 안에서 일치",
        ruler_of_audit_number="최대두께 계열(t_env_max/t_perp_max) — 부피보존 자가 아니다",
        slab_equivalent_definition_ko=(
            "얇은 판의 산란장은 E ∝ k0²(εr−1)∫d dA 이므로 등가 균일 슬래브 두께는 "
            "**부피/평면형면적 = 단면적/시위(t_env_mean)** 다. 최대두께가 아니다."),
        t_slab_equivalent_dji_mm=t_vol, t_max_dji_mm=t_max,
        max_over_volume_ratio=float(t_max / t_vol),
        dB_0p9_vs={"DJI 실물(부피보존)": float(20 * np.log10(knob / t_vol)),
                   "DJI 실물(감사가 쓴 최대두께)": float(20 * np.log10(knob / t_max)),
                   "우리 mini2 메쉬(부피보존)": float(20 * np.log10(knob / ours_mini2))},
        dB_ours_over_dji_same_ruler=float(20 * np.log10(ours_mini2 / t_vol)),
        verdict_ko=(
            "⛔**반증 성공.** 감사 §4-3 은 슬래브 두께(0.9 mm)를 실물의 **최대두께**(0.876)와 견줬다. "
            "부피보존 자(단면적/시위)로 재면 DJI Mini 2 실물은 **0.523 mm**(정밀 재계측 원장의 "
            "포락 적분을 내가 다시 적분한 값 / 3차에서 원본 GLB 를 직접 재면 0.468 mm)이고 0.9 mm 는 "
            "**+4.7 dB**(3차 자로는 +5.7 dB) 밝다 — «2.7 % 안에서 일치» 가 아니다. 이것은 감사가 C6 에서 스스로 "
            "적발한 «시위평균 ↔ 최대두께» 범주 오류를 §4-3 에서 **자기가 되풀이한** 것이다. "
            "따라서 §4-3 의 재프레이밍(«0.9 가 오히려 잘 앵커된 값 · 정본/민감도점 순서가 거꾸로»)은 "
            "무너진다. 두 값 다 Mini 급 실물보다 두껍고, 1.43 이 더 두꺼울 뿐이다."))

    # ------------------------------------------------------------------ #
    # Ⓖ «각도평균» 이 둘이다
    # ------------------------------------------------------------------ #
    ladder = [0.5, 0.524, 0.6146, 0.75, 0.7864, 0.833, 0.876, 0.9, 0.99, 1.40, 1.4302, 1.4559, 1.5]
    conv = {f"{d}mm": dict(normal=float(db_pow(d, 0.0)), deg45=float(db_pow(d, 45.0)),
                           convex_power=float(db_convex_pow(d)), convex_amplitude=float(db_convex_amp(d)))
            for d in ladder}
    gap = {f"{d}mm": float(db_convex_pow(d) - db_convex_amp(d)) for d in ladder}
    audit_tab = {"0.876": -20.05, "0.9": -19.85, "0.99": -19.18, "1.40": -16.74,
                 "1.43": -16.59, "1.456": -16.47}
    repro = {k: float(db_convex_pow(float(k))) for k in audit_tab}
    out["g_two_angle_averages"] = dict(
        table_by_convention=conv, power_minus_amplitude_dB=gap,
        audit_4_3_table=audit_tab, my_convex_power_reproduction=repro,
        max_abs_err_vs_audit_table=float(max(abs(audit_tab[k] - repro[k]) for k in audit_tab)),
        ledger_canon_angle_avg_db=-19.186, my_convex_amplitude_at_1p4302=float(db_convex_amp(1.4302)),
        measured_ac_delta_db=-16.986, slab_45deg_pred_delta_db=-16.65,
        slab_angleavg_pred_delta_db=-11.35,
        verdict_ko=(
            "저장소에 «각도평균» 이 **둘** 있다 — 전력평균(material_verdict·감사 §4-3 표)과 "
            "진폭평균(material_sources.proj_weighted_mean_gamma·prop_thickness 원장). 둘은 같은 "
            "두께에서 2.6~3.2 dB(관심 구간 0.5~1.5 mm) 어긋난다. 그래서 하나의 I1 주장이 저장소 "
            "안에서 **+3.82 / +4.60 / "
            "+4.85 / +5.11 dB** 네 값으로 돌아다닌다. 더 중요한 것은 정합성이다 — 실측 AC 이동 "
            "−16.99 dB 는 45° 예측(−16.65)과 0.34 dB 차이고 각도평균 예측(−11.35)과는 5.6 dB "
            "차다. 즉 **우리 기하에 맞는 규약은 45° 쪽**인데 감사는 헤드라인 표와 I1 하한을 "
            "각도평균으로 적었다. 규약을 자기 증거에 맞추면 모든 두께 델타가 커진다."))

    # ------------------------------------------------------------------ #
    # Ⓗ 100 mm 는 파브리-페로 물결 위의 임의점
    # ------------------------------------------------------------------ #
    dd = np.linspace(95.0, 105.0, 2001)
    ripple = {}
    for nm, fn in (("normal", lambda x: db_pow(x, 0.0)), ("deg45", lambda x: db_pow(x, 45.0)),
                   ("convex_power", lambda x: np.array([db_convex_pow(v) for v in x]))):
        y = fn(dd) if nm != "convex_power" else fn(dd[::100])
        ripple[nm] = dict(at_100mm=float(fn(np.array([100.0]))[0]) if nm != "convex_power"
                          else float(db_convex_pow(100.0)),
                          min_dB=float(np.min(y)), max_dB=float(np.max(y)),
                          peak_to_peak_dB=float(np.max(y) - np.min(y)))
    bulk = abs((1 - np.sqrt(_ec())) / (1 + np.sqrt(_ec())))
    out["h_100mm_is_an_arbitrary_point"] = dict(
        window_mm=[95.0, 105.0], ripple=ripple,
        bulk_halfspace_gamma=float(bulk), bulk_halfspace_dB=float(20 * np.log10(bulk)),
        sionna_default_thickness_m=0.1,
        verdict_ko=(
            "**절반 성공.** 기준점 100 mm 는 Sionna 의 `DEFAULT_THICKNESS` 이고 두께 가설이 아니라 "
            "**인자를 안 넘긴 결함**이다 — 그러니 «13~17 dB» 는 «축의 폭» 이 아니라 «이미 잡은 "
            "버그의 크기» 다. 그러나 «기준점이 파브리-페로 물결 위라 값 자체가 임의롭다» 는 쪽의 "
            "공격은 **실패했다**: 수직입사에서는 95~105 mm 사이에서 11.3 dB 나 출렁이지만, 감사가 "
            "실제로 쓴 두 규약(45°·각도평균)에서는 두꺼운 슬래브의 손실 때문에 물결이 죽어 "
            "1.1~1.4 dB 밖에 안 흔들린다. 즉 숫자 13~17 자체는 재현 가능하고 견고하다."))

    # ------------------------------------------------------------------ #
    # Ⓘ 잔여 예산 — 한 규약(45° 전력)으로 두 축을 나란히
    # ------------------------------------------------------------------ #
    def d45(a, b):
        return float(db_pow(b, 45.0) - db_pow(a, 45.0))

    dji_scaled_mini5 = t_vol * 152.4 / 119.4038      # 실물 상사 가정(⚠가정)
    budget = {
        "두께 ① 정본 스칼라를 mini5pro 에 (I1)": d45(0.7864, 1.4302),
        "두께 ② 우리 자 정의 차 (1.414↔1.480)": d45(1.4140, 1.4804),
        "두께 ③ m1 이 지적한 상수유도 편향": d45(1.4302, 1.4559),
        "두께 ④ 우리 메쉬 ↔ 실물 (mini2, 같은 자)": d45(t_vol, ours_mini2),
        "두께 ⑤ 실물 날의 «시위평균» 자 폭 (0.460↔0.686)": d45(0.4603, 0.6855),
        "두께 ⑥ εr 2.55↔2.95 (문헌 폭)": float(20 * np.log10((2.95 - 1) / (2.55 - 1))),
        "두께 ⑦ εr 2.7 ↔ 유리섬유나일론 3.5 (저장소 내부 모순)": float(20 * np.log10((3.5 - 1) / (2.7 - 1))),
        "형상 ⓐ 법칙→실물 보정 (감사 §4-2)": 1.3,
        "형상 ⓑ 날 면적 −21 % (2차 재측정)": float(20 * np.log10(0.79)),
        "형상 ⓒ 바이스태틱 β=120° 시위 민감도 (감사 §4-2)": 2.5,
        "[참고] 잡은 버그: 100 mm 기본값 (mini5pro)": d45(0.7864, 100.0),
        "[참고] 우리 PO 커널 Γ=0.25 ≡ 4.40 mm (mini5pro)": d45(0.7864, 4.4016),
    }
    out["i_residual_budget_at_45deg"] = dict(
        dB=budget,
        thickness_axis_residual_span_dB=float(max(abs(v) for k, v in budget.items() if k.startswith("두께"))),
        shape_axis_residual_span_dB=float(max(abs(v) for k, v in budget.items() if k.startswith("형상"))),
        dji_mini5pro_thickness_if_similar_mm=float(dji_scaled_mini5),
        canon_vs_real_scaled_mini5pro_dB=float(d45(dji_scaled_mini5, 1.4302)),
        product_law_ko=("얇은 판에서 E ∝ (εr−1)·k0²·∫d dA 이므로 σ ∝ (두께 × 면적)² 다 — "
                        "두께와 형상은 **같은 dB 통화**이고 곱으로 들어간다."),
        verdict_ko=(
            "⚠**부분 정정.** 방향(두께가 형상보다 크다)은 살아남는다. 그러나 «13~17 대 1~2» 라는 "
            "10 배 격차는 사과-대-사과가 아니다: 13~17 은 «이미 잡은 기본값 버그» 이고 형상 1~2 는 "
            "«남은 충실도 오차» 다. 같은 잣대(남은 오차·45° 전력)로 모으면 두께 3~5 dB · 형상 "
            "1.3~2.5 dB 로 **2~3 배**다. 그리고 두 축은 애초에 곱이라 순서를 매길 대상이 아니다."))

    # ------------------------------------------------------------------ #
    # Ⓙ 시위평균 요약은 언제 깨지나
    # ------------------------------------------------------------------ #
    led = json.load(open(os.path.join(_ROOT, "outputs", "prop_thickness_by_drone.json")))
    br = {}
    for key in ("mini5pro", "matrice4e"):
        s = led["per_drone"][key]["stations"]
        r = np.asarray([x["r_over_R"] for x in s], float)
        c = np.asarray([x["chord_mm"] for x in s], float)
        t = np.asarray([x["t_chordmean_mm"] for x in s], float)
        m = (r >= BAND[0]) & (r <= BAND[1])
        r, c, t = r[m], c[m], t[m]
        rows = []
        broke = None
        for s_fac in (1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20):
            tt = t * s_fac
            g = np.abs(slab_R(tt * 1e-3, 0.0, "TE"))
            gbar = float(np.trapezoid(g * c, r) / np.trapezoid(c, r))
            tbar = float(np.trapezoid(tt * c, r) / np.trapezoid(c, r))
            err = float(20 * np.log10(gbar / abs(slab_R(tbar * 1e-3, 0.0, "TE"))))
            rows.append(dict(scale=s_fac, t_mean_mm=tbar, t_over_lambda=float(tbar / LAM_MM),
                             err_dB=err))
            if broke is None and abs(err) > 1.0:
                broke = dict(scale=s_fac, t_mean_mm=tbar, t_over_lambda=float(tbar / LAM_MM))
        br[key] = dict(ladder=rows, first_scale_over_1dB=broke)
    out["j_when_does_the_summary_break"] = dict(
        per_drone=br,
        verdict_ko=(
            "시위평균 스칼라는 **얇기 때문에** 성립한다. 두께를 통째로 키우면 ⟨Γ(t)⟩ 와 Γ(⟨t⟩) 가 "
            "갈라지기 시작하고, 우리 두께대(λ/60~λ/110)에서는 0.01~0.03 dB 라 무해하다. "
            "⇒ ⓒ 공격 실패: 이 영역에서 «시위평균으로 요약» 은 RF 적으로 옳다. 다만 그것이 옳은 "
            "이유가 **선형성**이므로, 같은 선형성 때문에 요약은 **면적과 곱으로만 의미**가 있고 "
            "국소(팁띠)에는 못 쓴다."))

    out["_meta"]["pass2_generated_kst"] = time.strftime("%Y-%m-%dT%H:%M:%S",
                                                        time.localtime(time.time() + 9 * 3600))
    out["_meta"]["pass2_script"] = "benchmark/adv_refute_thickness_pass2_0816.py"
    out["_meta"]["pass2_runtime_s"] = round(time.time() - t0, 1)
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("updated", OUT, out["_meta"]["pass2_runtime_s"], "s")


if __name__ == "__main__":
    main()
