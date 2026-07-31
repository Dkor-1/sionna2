# -*- coding: utf-8 -*-
"""make_notebook06.py — report06.ipynb 생성기

report06: **표적 밝기(RCS)와 Sionna 광선추적의 한계**
질문: **"드론의 레이더 밝기(RCS)는 왜 Sionna 광선추적만으로 안 나오나?"**

이 리포트는 **한 주제만** 다룬다:
  · 표적의 밝기(σ)를 왜 Sionna RT `PathSolver` 로는 계산할 수 없는가 — 다섯 가지 방식으로 확인.
  · 그 밝기를 **어떻게 계산하는가(SBR)** 는 → report07 소관 (여기선 안 다룬다).
  · 실제 RCS 결과값(밴드별·자세별) 은 → report08 소관.

⚠ 노트북은 **생성물**이다. report06.ipynb 를 직접 고치지 말고 이 파일을 고쳐 다시 실행할 것.
⚠ 본문 수치는 전부 측정 JSON 에서 읽어 주입한다 — 그림(report3_f6_no_sigma.png)과 글이 어긋날 수 없다.
   · outputs/report3_rt.json          — 5-패널 그림의 원장 (benchmark/rt_experiments.py)
   · outputs/rt_no_rcs_verify.json    — 평판 52 dB 스윕 · PEC 구 검증 (benchmark/verify_rt_no_rcs.py)
   · outputs/rt_ray_budget.json       — 광선 예산 25M→400M · S 스윕 (benchmark/verify_rt_rays.py)
"""
from __future__ import annotations

import json
import math
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# ⚠ 이 파일은 **스크립트**다 (main() 없이 최상위에서 전부 실행된다).
#   임포트하면 그 자리에서 리포트 노트북을 **덮어쓴다**. 2026-07-29 실제로 검증 에이전트가
#   "임포트 되는지" 점검하다가 report07/08/13 을 덮어썼고 복구해야 했다. linter·문서도구·
#   테스트수집기도 같은 사고를 낸다 — 게다가 계산이 도는 중이면 **중간 숫자**가 박힌다.
#   → 실행은 `python src/make_notebook06.py` 로만.
if __name__ != "__main__":
    raise RuntimeError(
        "make_notebook06.py 는 스크립트다 — 임포트하면 리포트를 덮어쓴다. "
        "`python src/make_notebook06.py` 로 실행할 것. (2026-07-29 실사고)")
# ─────────────────────────────────────────────────────────────────────────────

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from provenance import provenance_cells   # noqa: E402

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
NB = os.path.join(ROOT, "report06.ipynb")
J_FIG = os.path.join(ROOT, "outputs", "report3_rt.json")       # 그림 원장
J_VER = os.path.join(ROOT, "outputs", "rt_no_rcs_verify.json")  # 평판·구 검증
J_RAY = os.path.join(ROOT, "outputs", "rt_ray_budget.json")     # 광선 예산·S 스윕


def _s(lines):
    out = "\n".join(lines).splitlines(keepends=True)
    return out if out else [""]


def md(*l):
    return {"cell_type": "markdown", "metadata": {}, "source": _s(list(l))}


def code(*l):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": _s(list(l))}


# --------------------------------------------------------------------------- #
#  측정값 로드 — 손으로 적는 숫자는 하나도 없다
# --------------------------------------------------------------------------- #
F = json.load(open(J_FIG))
V = json.load(open(J_VER))
RB = json.load(open(J_RAY))

#  씬 형상 (rt_ray_budget.json)
fc = RB["fc"]                                   # 3.5 GHz
lam = F["E_sphere"]["lam"]                       # 파장 [m]
G = RB["geometry"]
L, R1, R2, beta = G["L"], G["R1"], G["R2"], G["beta"]
tau_ns = RB["tau_echo_ns"]
drone = RB["drone"]

#  [A] 광선 예산 (report3_rt.json A_rays) — 그림과 일치
A = F["A_rays"]["rows"]
ray_lo, ray_hi = A[0]["spp"] / 1e6, A[-1]["spp"] / 1e6         # 25M, 400M
coh_lo, coh_hi = A[0]["coh_db"], A[-1]["coh_db"]               # -68.6, -54.4
coh_climb = coh_hi - coh_lo                                    # +14.2 dB
incoh_mean = sum(r["incoh_db"] for r in A) / len(A)            # ~ -73.7
np_lo, np_hi = A[0]["n_paths"], A[-1]["n_paths"]               # 5, 94

#  SBR 표적이 필요로 하는 값 (레이더 방정식이 요구하는 σ 비) = C_metal.ratio_db_truth
sbr_target = F["C_metal"]["ratio_db_truth"]                    # 현재 -56.88 dB (그림 [A][B] 빨간 점선)

#  [B] 산란계수 S — ⚠ **두 원장은 서로 다른 스윕이다. 섞어 쓰지 않는다.**
#    (1) 그림 [B] 원장 = report3_rt.json B_scatter — 재질 표의 S 에 **배수**를 곱한다
#        (rt_experiments.py:225-230). ITU metal 은 0×배수 = 0 이라 그대로 0, 플라스틱만 움직인다. 시드 3개.
#    (2) rt_ray_budget.json B_S_sweep — **전 부품의 S 를 한 값으로 덮어쓴다**(verify_rt_rays.py:93-100,
#        "전 부품의 S 를 그 값으로 덮어쓴다"). 즉 금속도 S>0 이 된다. 시드 5개, S=0.1~0.8.
#        기록된 B_fit(slope·S_to_match_truth)은 **인코히런트** 곡선의 최소제곱 적합이다
#        (verify_rt_rays.py:239-244: ys = incoh_db). 코히런트 기울기는 같은 방식으로 여기서 따로 낸다.
Bsc = F["B_scatter"]["rows"]
S_seeds_fig = F["B_scatter"]["seeds"]
S_mult_lo, S_mult_hi = Bsc[0]["mult"], Bsc[-1]["mult"]         # 0.5, 2.0
S_pl_lo, S_pl_hi = Bsc[0]["S_plastic"], Bsc[-1]["S_plastic"]   # 0.10, 0.40
S_half_coh, S_2x_coh = Bsc[0]["coh_db"], Bsc[-1]["coh_db"]     # -74.84, -48.13
S_x4_delta = S_2x_coh - S_half_coh                             # +26.7 dB (코히런트 합)

_RBS = sorted([r for r in RB["B_S_sweep"] if r["n_paths"]], key=lambda r: r["S"])
S_ov_lo, S_ov_hi = _RBS[0]["S"], _RBS[-1]["S"]                 # 0.1 -> 0.8
S_ov_seeds = RB["seeds"]                                       # 5


def _slope_db_per_dec(key):
    """log10(S) 대비 최소제곱 기울기 — B_fit 과 같은 방식(np.polyfit 1차)."""
    xs = [math.log10(r["S"]) for r in _RBS]
    ys = [r[key] for r in _RBS]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            / sum((x - mx) ** 2 for x in xs))


slope_incoh = _slope_db_per_dec("incoh_db")                    # 20.34 == B_fit
slope_coh = _slope_db_per_dec("coh_db")                        # 41.64
slope_dec = RB["B_fit"]["slope_db_per_decade"]                 # 기록값(인코히런트)
S_match = RB["B_fit"]["S_to_match_truth"]                      # 0.704 (인코히런트 보간)

#  [C] 재질별 σ — **그림 [C] 와 같은 원장**(report3_rt.json C_metal)에서 읽는다.
#      그림·본문·코드셀이 한 원장을 보게 통일한 것이다(el 15°, 방위 36점 평균).
Cm = F["C_metal"]
sig_full = Cm["sigma"]["full_dbsm"]                            # -18.60
sig_metal = Cm["sigma"]["metal_only_dbsm"]                     # -19.12
sig_diel = Cm["sigma"]["dielectric_only_dbsm"]                 # -25.79
metal_share = Cm["metal_share_pct"]                            # 88.74 % = 10^((금속-전체)/10)
diel_share = 100.0 * 10 ** ((sig_diel - sig_full) / 10.0)      # 19.11 %
d_metal_db = sig_metal - sig_full                              # -0.52 dB
d_diel_db = sig_diel - sig_full                                # -7.19 dB
metal_groups = Cm["metal_groups"]                              # battery,camera,motor,pcb
itu_metal_S = Cm["itu_metal_S"]                                # 0.0
el_C, n_az_C = Cm["el_deg"], Cm["n_az"]                        # 15°, 36 방위

#  report08 이 쓰는 조밀 원장(방위 121점) — **레벨 대조용으로만** 읽는다(캡션 각주).
_J2 = json.load(open(os.path.join(ROOT, "outputs", "report2_waveform_rcs.json"), encoding="utf-8"))


def _mrow(key):
    for r in _J2["materials"]["rows"]:
        if key in r["label"]:
            return r
    raise KeyError(key)


#  구 검증의 기준해 — ⚠ πr² 은 ka→∞ **점근값**이라 과녁이 아니다(report07 §4 · benchmark/mie_pec_sphere).
#  예전엔 여기에 report07 의 πr² 기준 구 잔차(+0.39/−0.58 dB)를 **손으로 적어** 두었다 → 이제 주입한다.
_SV = _J2["sbr_validation"]
if "sphere_err_po" not in _SV:
    raise RuntimeError(
        "outputs/report2_waveform_rcs.json 이 기준해 정정(πr² → 정확 Mie + 해석 PO) 이전 판이다 "
        "— `python src/viz_report2.py` 로 재생성한 뒤 이 노트북을 빌드할 것.")
_sv_i16 = _SV["divs"].index(16)                                 # 우리가 실제로 쓰는 격자 λ/16
_sph_po_16 = _SV["sphere_err_po"][_sv_i16]                      # 구, 해석 PO 기준(커널의 과녁)
_sph_mie_16 = _SV["sphere_err_mie"][_sv_i16]                    # 구, 정확 Mie 기준(참값)
_plate_16 = _SV["plate_err"][_sv_i16]                           # 평판, 정확 PO 기준

n_az_dense = _J2["materials"]["n_az"]                           # 121
n_faces_full = _mrow("Full drone")["n_faces"]                   # 28,548 면
d2_full = _mrow("Full drone")["mean_dbsm"]                      # -18.41
d2_metal = _mrow("metal core only")["mean_dbsm"]                # -18.02
d2_diel = _mrow("dielectric only")["mean_dbsm"]                 # -25.27
d2_metal_delta = _mrow("metal core only")["delta_db"]           # +0.393 (전체보다 밝다 — 미해결)

#  [D] 평판 스윕 (report3_rt.json D_plate == rt_no_rcs_verify A_plate)
D = F["D_plate"]
plate_sides = [r["side_m"] for r in D["rows"]]                # 0.2 .. 4.0
plate_sig = [r["sigma_dbsm"] for r in D["rows"]]             # 4.4 .. 56.4
plate_span = D["sigma_span_db"]                             # 52.0 dB
rt_flat = D["rt_mean_db"]                                   # -7.913
rt_span = D["rt_span_db"]                                   # ~6e-6 dB
img_db = D["image_db"]                                      # -7.882
img_formula = 20 * math.log10(L / (R1 + R2))                # == img_db

#  [E] PEC 구 (report3_rt.json E_sphere == rt_no_rcs_verify C_pec_sphere)
E = F["E_sphere"]
sph_radii = sorted({r["radius_m"] for r in E["rows"]})       # 0.3, 1.0
sph_maxspp = max(r["spp"] for r in E["rows"]) / 1e6          # 400 M
sph_npaths = {r["n_paths"] for r in E["rows"]}              # {0}
ctrl_paths = E["control_plate"]["n_paths"]                   # 1
ctrl_db = E["control_plate"]["rt_db"]                        # -7.913

#  §5-F 반례 판정용 문헌값 — 스톡 Sionna 로 UAV 표적 반환을 낸 선행이 실제로 보고한 것.
#  재유도하지 않는다(PDF 렌더로 검증됨 → docs/DRONE_ISAC_PRIOR_READING.md §1·§5-F·§7-1).
MD_RT_DOPPLER_HZ = 1562        # md-rt(Li 외, IEEE ICCT 2025) §IV-A Fig.4e 로터 마이크로도플러 주파수
MD_RT_PERIOD_S = 0.04          #   같은 절 회전주기 T [s] — 검증한 것은 주파수(운동학)이지 진폭 σ 가 아니다

cells = []

# =========================================================================== #
#  앞머리 (provenance)
# =========================================================================== #
_prov = provenance_cells(
    report="report06",
    what="표적 밝기(RCS)와 **Sionna 광선추적의 한계**",
    question="드론의 레이더 밝기(RCS)는 왜 Sionna 광선추적만으로 안 나오나?",

    spine=dict(
        core=(f"탐지는 표적의 되비침 밝기(RCS)에서 출발하는데, **Sionna RT `PathSolver` 는 절대 σ 를 "
              f"주지 않는다** — 설계상 표면 산란적분 단계가 없기 때문이다. 우리 구현의 문제가 아니라 "
              f"**기본 경로 솔버(`PathSolver`)의 범위**다(산란패턴·재질 확장점은 별개로 존재)."),
        gap=(f"`PathSolver` 는 경로별 **지연 τ·도플러·복소이득·반사점**만 반환한다"
             f"(Sionna RT 창설논문 arXiv:2303.11103 이 'per-path gain' 으로 문서화). 표적 밝기 σ 는 "
             f"그 목록에 없다 — 평판을 {plate_sides[0]:.1f}→{plate_sides[-1]:.0f} m 로 키워 참 RCS 가 "
             f"{plate_span:.0f} dB 넓어져도 RT 값은 {rt_flat:.2f} dB 에서 불변(§2)."),
        prior=("스톡 Sionna 로 UAV **표적 반환(에코·마이크로도플러)** 을 낸 선행은 있으나"
               "(clutter·md-rt), **형상·기종·자세별 절대 σ(dBsm)** 를 낸 선행은 우리가 확인한 "
               "범위에서 **없다** — 두 편 모두 σ 를 dBsm 으로 보고하지 않는다(§1). 표준 우회 세 갈래 — "
               "**(b)** 재질 확산계수 S 가정[Great-X], **(c)** 외부에서 RCS 계산·주입 "
               "$h=h_{bg}+h_{target}$[LAMBDA=Sionna+CADFEKO, Temporal-GNN=점산란체, 3GPP Rel-19], "
               "**(d)** 커스텀 산란 add-on[Ziganshin UTD] (§3)."),
        lib=("**(d)** 를 택했다 — Sionna 가 쓰는 **Mitsuba 3 / OptiX 광선엔진을 그대로** 얹고 그 위에 "
             "표준 PO 산란적분을 수행한다(새 광선엔진을 만들지 않아 중복계산이 없다). GPU BVH SBR+PO"
             "(arXiv:2604.09243)와 **같은 계열**(GO 광선 전송 + 광선튜브 위 PO 표면적분)이되 적용범위가 "
             "다르다 — 그들은 PEC·모노스태틱 후방산란 전용, 우리는 다중재질·바이스태틱(§4) → 계산 "
             "절차는 report07."),
        verify=(f"정준 표적 **기준해**로 교정한다 — 평판은 정면입사 σ=4πA²/λ²(점근이 아니라 PO 의 "
                f"**정확한** 답) 대비 {_plate_16:+.2f} dB, 구는 기준해가 **둘**이라 둘 다 적는다: "
                f"**해석 PO 대비 {_sph_po_16:+.2f} dB · 정확 Mie 대비 {_sph_mie_16:+.2f} dB**"
                f"(우리가 쓰는 λ/16. 값은 **격자마다 달라지고 단조수렴이 아니다**). ⚠ πr² 은 ka→∞ "
                "점근값이라 과녁이 아니다 — 커널이 PO 라 수치 수렴의 과녁은 해석 PO 이고, Mie 잔차는 "
                "PO 근사를 쓴 대가다(report07 §4) + **문헌 실측 드론 RCS 와의 대조**(report08 — 크기 짝 "
                "peak↔peak 로 보면 우리가 위로 치우친다). 절대값 결과는 report08."),
    ),

    sources=[
        dict(item="드론 형상·재질 (mavic4pro)",
             src="DJI 공식 스펙 → `src/drones.py` (report01·02 에서 만든 메쉬)",
             kind="🔴 우리 모델"),
        dict(item="재질 산란계수 S (금속=0 등)",
             src="ITU-R P.2040 재질 표 → `src/materials.py`",
             kind="🟢 표준 (ITU-R)"),
        dict(item="평판·구의 **참 RCS** (기준해)",
             src="4πA²/λ² (평판 — 정면입사에서 PO 의 정확한 답) · **정확 Mie 급수 + 해석적 PO** (구) "
                 "— `benchmark/mie_pec_sphere.py`. ⚠ πr² 은 ka→∞ 점근값이라 과녁이 아니다",
             kind="🟢 기준해 (검증 기준)"),
        dict(item="[A]~[E] 다섯 측정 원장",
             src="`benchmark/rt_experiments.py` → `outputs/report3_rt.json`; "
                 "`benchmark/verify_rt_no_rcs.py` · `verify_rt_rays.py`",
             kind="🔴 우리 측정 (Sionna RT 호출)"),
    ],

    engines=["sionna-rt", "sbr", "matplotlib"],
    libs=["sionna", "mitsuba", "drjit", "numpy", "matplotlib"],

    reproduce=[
        "cd /home/yunjung/workspace/sionna2",
        "",
        "# 5-패널 그림의 원장 [A]~[E] (드론 광선예산 · S · 재질 · 평판 · 구)",
        "~/.venvs/py312/bin/python benchmark/rt_experiments.py   # -> outputs/report3_rt.json",
        "",
        "# 평판 52 dB 스윕 + PEC 구 0-경로 독립 검증",
        "~/.venvs/py312/bin/python benchmark/verify_rt_no_rcs.py  # -> outputs/rt_no_rcs_verify.json",
        "",
        "# 광선 예산 25M -> 400M + 산란계수 S 스윕",
        "~/.venvs/py312/bin/python benchmark/verify_rt_rays.py    # -> outputs/rt_ray_budget.json",
        "",
        "# JSON -> report06.ipynb (이 노트북)",
        "~/.venvs/py312/bin/python src/make_notebook06.py",
    ],

    artifacts=[
        dict(file="outputs/report3_rt.json",
             what="**이 리포트의 그림 숫자 원장.** [A] 광선예산 [B] S스윕 [C] 재질 [D] 평판 [E] 구"),
        dict(file="outputs/rt_no_rcs_verify.json",
             what="§2 평판 52 dB 스윕 · §2 PEC 구 0-경로 (독립 재현)"),
        dict(file="outputs/rt_ray_budget.json",
             what="§2 광선 25M→400M · §2 S 스윕 (독립 재현)"),
        dict(file="outputs/figures/report3_f6_no_sigma.png",
             what="**핵심 그림** — [A]~[E] 5 패널 (4억 발 그림)"),
        dict(file="outputs/figures/report3_f7_hybrid.png",
             what="§4 역할 분담 그림 (환경=RT, 표적=SBR)"),
    ],

    caveats=[
        "**'Sionna 가 RCS 를 못 낸다' 가 아니라, 'Sionna 의 기본 경로 솔버(`PathSolver`)에 "
        "산란적분 단계가 없다' 는 것입니다.** 광선추적 그 자체는 RCS 를 정확히 계산할 수 있습니다 — "
        "SBR(광선으로 조명면을 찾고 그 위에서 PO 적분)이 바로 광선추적이고, 다음 리포트가 그걸 씁니다.",

        "**'RCS 가 없으면 센싱을 전혀 못 한다' 는 과장입니다.** 지연·도플러·도래각·궤적처럼 표적 "
        "경로의 **위치만** 쓰는 정규화 센싱은 RCS 없이도 됩니다(예: 추적 알고리즘 비교). 다만 수신 "
        "반사전력·SCNR·탐지거리·P_D·자세별 탐지성·표적 분류를 **물리적으로 의미 있게** 평가하려면 "
        "RCS(또는 그에 준하는 target reflectivity)가 반드시 필요합니다 — 그래서 우리는 그 값을 SBR+PO "
        "로 계산합니다(선행연구 조사·근거: `prior_work/pw04`).",

        f"**RT 가 표적 위치에 내놓는 -7.9 dB 는 '표적 크기와 무관한 거울 경로 값'입니다** "
        f"(image-source, 20·log₁₀(L/(R₁+R₂)) = {img_formula:.2f} dB). 이것을 RCS 로 오해하면 안 "
        f"됩니다 — §2 에서 평판을 {plate_span:.0f} dB 키워도 이 값이 안 움직이는 것으로 증명합니다.",

        f"**산란계수 S 를 켜면 RT 도 어떤 '에코' 를 내놓지만, 그건 물리적 σ 가 아니라 재질 표의 "
        f"손잡이입니다.** 표의 S 에 배수를 곱해 ×{S_mult_lo:g}→×{S_mult_hi:g} 로 바꾸면 코히런트 "
        f"에코가 {S_x4_delta:+.1f} dB 움직이고(§2), 게다가 ITU 표에서 금속의 S=0 이라 "
        f"**금속부만 남겨도 σ 가 전체의 {metal_share:.0f}% 로 유지될 만큼** 지배적인 금속부"
        f"(모터·배터리·PCB·카메라)는 이 확산 채널에 **전혀 기여하지 못합니다.**",

        "**이 리포트는 '왜 못 계산하나' 만 다룹니다.** 그 밝기를 실제로 계산하는 SBR 의 방법(report07)과 "
        "밴드별·자세별 RCS 결과값(report08)은 다루지 않습니다 — 여기서 못을 박는 것은 도구의 성질뿐입니다.",
    ],

    cost=(f"측정은 GPU 1장, Sionna RT `PathSolver`(Mitsuba/OptiX). 한 조건이 **초 단위**로 끝나고 "
          f"(광선 {ray_hi:.0f}M 발도 1초 안팎), 5 실험 전체가 분 단위입니다. 이 리포트는 기존 측정 "
          f"JSON·그림을 **재사용**하며 재측정·재렌더하지 않습니다."),

    related=[
        dict(rep="[report05](report05.ipynb) — 파형 검증",
             rel="**앞 리포트.** 표적을 비추는 신호(WiFi/LTE/5G)가 규격과 맞음을 못박았다. "
                 "이제 그 신호에 표적이 **얼마나 밝게 되비추는가**로 넘어온다"),
        dict(rep="**report06 (여기)** — RCS 와 Sionna 광선추적의 한계",
             rel="표적 밝기(σ)를 왜 `PathSolver` 로는 못 만드나 — 다섯 방식으로 확인"),
        dict(rep="[report07](report07.ipynb) — SBR 로 밝기 계산",
             rel="**다음 리포트.** 여기서 '못 한다' 고 한 그 계산을 SBR(광선 + PO 적분)이 **한다**"),
    ],

    glossary=[
        ("RCS (σ)", "레이더 되비침 밝기 [m²]. '이 표적이 레이더에 얼마나 밝게 보이나'. dBsm = 10·log₁₀(σ/1 m²)"),
        ("산란적분", "표면의 모든 조각이 되쏘는 파동을 **위상까지 맞춰 다 더하는** 계산. σ 는 이 합에서 나온다"),
        ("PO (물리광학)", "표면에 유도된 전류를 적분해 되쏘는 장을 구하는 방법 — 산란적분을 실제로 수행하는 도구"),
        ("GO (기하광학)", "표면을 '국소 거울' 로 보는 근사. 벽·바닥 반사엔 정확하지만 **면적 항이 없어 σ 를 못 준다**"),
        ("SBR", "Shooting-and-Bouncing Rays. 광선(GO)으로 조명면을 찾고 그 위에서 PO 적분. σ 를 내는 표준 방법 (report07)"),
        ("경로 솔버(PathSolver)", "Sionna RT 가 전파 경로를 찾는 엔진. 지연 τ·도플러·복소이득·반사점을 준다 — 산란적분은 없다"),
        ("코히런트 합", "여러 경로를 **위상까지 맞춰** 더한 값. 랜덤 확산 경로에선 이 합이 광선 수에 따라 계속 커진다"),
        ("인코히런트 합", "경로들의 세기(전력)만 더한 값. 위상 정보를 버린 거친 요약"),
        ("산란계수 S", "재질이 입사파를 **거울반사 대신 사방으로 흩뿌리는 비율**. 재질 표의 손잡이 — σ 자체가 아니다"),
        ("image-source (거울상)", "평평한 면의 거울 반사를 '반대편에 놓인 가상의 송신원' 으로 계산하는 방법. 값이 **표적 크기와 무관**하다"),
        ("PEC", "완전도체(Perfect Electric Conductor). 모든 전파를 되쏘는 이상적 금속 — 구의 σ 는 Mie 급수로 정확히 알려져 있다(πr² 은 그 ka→∞ 점근값)"),
        ("dBsm", "10·log₁₀(σ / 1 m²). RCS 를 dB 로 적은 것. 0 dBsm = 1 m²"),
    ],
)

cells += _prov  # 척추 리드가 헤더에 있으므로 별도 5분요약은 싣지 않는다

# =========================================================================== #
#  §0
# =========================================================================== #
cells.append(md(
    "## §1. Sionna `PathSolver` — 주는 것과 안 주는 것",
    "",
    "레이더는 밝은 표적만 잡는다. 표적의 되비침 밝기가 **RCS(σ, dBsm = 10·log₁₀(σ/1 m²))** 이고, "
    "이 값은 표면의 **모든 조각이 되쏘는 파동을 위상까지 맞춰 다 더한(산란적분)** 결과다 — 물리광학"
    "(PO)이 표면 전류를 적분해 구한다:",
    "",
    "$$\\sigma \\;=\\; \\lim_{R\\to\\infty} 4\\pi R^2 "
    "\\frac{|E_{\\text{scat}}|^2}{|E_{\\text{inc}}|^2}, \\qquad "
    "E_{\\text{scat}} \\;\\propto\\; \\underbrace{\\int_{S} J(\\mathbf r)\\, "
    "e^{-jk\\,\\hat{\\mathbf s}\\cdot\\mathbf r}\\, dS}_{\\text{표면 조각들의 위상 맞춘 합}}$$",
    "",
    f"Sionna RT `PathSolver` 는 전파가 방 안을 어떻게 도는지를 광선으로 추적한다. 우리 씬은 "
    f"{L:.1f} m 떨어진 송·수신기(바이스태틱 각 β={beta:.0f}°)와 그 사이를 나는 드론이고, 드론 경유 "
    f"에코는 τ≈{tau_ns:.0f} ns 에 도착한다. 경로별로 이 솔버가 반환하는 것은:",
    "",
    "| `PathSolver` 가 반환하는 것 | 표적 밝기 σ 는? |",
    "|---|---|",
    "| 지연 τ · 도플러 f_d · 반사점 · 경로별 복소이득 | ❌ 목록에 **없음** |",
    "",
    "이 값들은 **환경(방)에 대해서는 물리적으로 옳다** — 벽·바닥 반사는 국소적으로 거울(GO)로 보면 "
    "정확하다. 하지만 표적을 만나면 솔버는 그것도 **거울로 취급**(GO)해 광선을 튕겨 보낼 뿐, 위 적분의 "
    "**∫ 단계가 없다.** 거울반사에는 표면적 항이 없어(거울은 클수록 밝아지지 않는다) σ 가 나오지 "
    "않는다.",
    "",
    "이건 우리가 관찰한 특이현상이 아니라 **선행 문헌이 명시한 설계 사실**이다. Sionna RT 창설논문"
    "(arXiv:2303.11103)은 이 솔버가 경면(이미지법)·확산(계수)·1차 회절로 **경로별 복소이득(per-path "
    "gain)을 반환**한다고 문서화하고, 기술 보고서(arXiv:2504.21719, Sionna 1.0)는 솔버 내부의 'SBR' "
    "이 **경로 탐색용 광선 발사**(어느 면이 조명되나)일 뿐 PO 표면전류 적분이 아님을 분명히 한다. "
    "그래서 소형 표적의 **절대 σ(dBsm)** 를 스톡 Sionna 로 메쉬에서 직접 낸 선행 연구는 우리가 "
    "확인한 범위에서 **없다** — 스톡 Sionna 로 표적 반환·마이크로도플러를 만든 선행은 있지만(바로 "
    "아래에서 그 경계를 정확히 긋는다) 어느 편도 σ 를 dBsm 으로 보고하지 않는다. 아래 §2 는 이 "
    "문서화된 공백을 우리 챔버에서 다섯 방식으로 재확인한다.",
))

# =========================================================================== #
#  §1-보 — §5-F: 주장의 경계를 정확히 (스톡 Sionna 로 표적을 다룬 선행 두 편)
# =========================================================================== #
cells.append(md(
    "### 어디까지가 참인가 — 스톡 Sionna 로 '표적' 을 다룬 선행 두 편",
    "",
    "이 주장은 좁게 말해야 참이다. **스톡 Sionna RT 로 UAV 표적 반환을 만들어 낸 선행은 실재한다** — "
    "다만 어느 편도 표적의 **절대 σ(dBsm)를 보고하지 않는다.** 두 사례로 경계를 긋는다:",
    "",
    "- **clutter** (Liu 외, *Proc. IEEE* 114:52–91, 2026) 는 드론 메쉬를 Sionna 씬에 그대로 넣는다: "
    "*\"The ToI and UAVs are modeled as simplified 3-D mesh objects imported into Sionna ... for "
    "monostatic sensing, the target echoes appear as reflected and scattered paths that interact "
    "with the target object.\"* 그러나 이 튜토리얼이 필요로 하는 것은 **'강한 UAV 대 약한 관심표적' "
    "이라는 상대적 세기**뿐이고, 표적 σ 를 dBsm 으로 한 번도 적지 않으며 Pd/Pfa 도 없다.",
    "",
    f"- **md-rt** (Li 외, *IEEE ICCT 2025*, pp.359–364) 는 스톡 Sionna RT + Blender 블레이드 메쉬로 "
    f"로터 마이크로도플러를 만든다. 회전은 `Paths.doppler` 가 아니라 **타임스텝마다 표적을 갱신하고 "
    f"RT 를 재실행**하는 방식이다: *\"(4) Emit rays toward the target and calculate the channel "
    f"frequency response; (5) Update the target's velocity and position, then repeat step 4.\"* "
    f"그러나 이들이 검증한 것은 도플러 **주파수**({MD_RT_DOPPLER_HZ} Hz, T={MD_RT_PERIOD_S:.2f} s)이지 "
    f"**진폭(σ)이 아니고**, 재질은 Sionna 내장 기본값이다. 도플러 주파수는 표적의 **기하·운동학**"
    f"(반경속도 2v/λ)에서 나오지 재질 산란의 세기와 무관하다 — §2 [B] 의 산란계수 S 손잡이는 에코 "
    f"**전력**만 흔들 뿐 도플러 주파수는 건드리지 않는다 — 그래서 산란적분 없이도 옳게 나온다. "
    f"이 성공은 우리 주장과 충돌하지 않는다.",
    "",
    f"> ⚠️ **md-rt 를 정량 앵커로 쓰지 않는다 (2026-07-29 원문 재검증).** 이 논문의 수치 보고는 "
    f"자체 모순이다. (a) 프로펠러 반경이 Table I 은 `10.55 cm`, §IV-B 본문은 *\"blade length of "
    f"1.055 meters\"* 로 **10배 어긋난다**. (b) 우리가 재계산하면 T={MD_RT_PERIOD_S:.2f} s → "
    f"ω=2π/T=157.08 rad/s 이고 5 GHz(λ=59.96 mm)에서 f=2ωr/λ 이므로 r=0.1055 m → **553 Hz**, "
    f"r=1.055 m → **5527 Hz** 다. 논문이 *\"matches perfectly\"* 라 적은 {MD_RT_DOPPLER_HZ} Hz 는 "
    f"**어느 반경과도 맞지 않는다**(그 값이 나오려면 r=0.298 m). (c) 같은 절의 "
    f"*\"the minimum spatial resolution in Sionna is 0.01 m\"* 는 **Sionna 문서·소스 어디에도 근거가 "
    f"없다** — Sionna RT 는 부동소수 삼각망 위의 기하광학 솔버이고 그런 파라미터가 없다. "
    f"따라서 위 인용은 **'스톡 Sionna 로 마이크로도플러를 낸 선행이 있다'는 사실**의 근거로만 쓰고, "
    f"주파수 값·해상도 주장은 인용하지 않는다.",
    "",
    "두 편을 합치면 참으로 주장할 수 있는 좁은 명제는 하나다: **기본 경로 솔버는 형상·기종·자세별 "
    "절대 σ(dBsm)를 못 낸다.** '스톡 Sionna 로는 표적을 아예 못 다룬다' 는 과장이고, 위 두 편이 실제로 "
    "반증한다. 같은 맥락에서, 협력형 FWA 드론 감지를 다룬 최근 선행(arXiv:2605.07623)조차 표적을 "
    "**금속 정육면체(metallic cube)** 로 두고 경면·확산 반사(*\"specular and diffuse\"*)만으로 링크를 "
    "만들어 σ 를 우회한다(전문에 RCS·radar cross section 0회). 이는 *Sionna 로 σ 를 못 낸다*가 아니라 "
    "**아무도 절대 σ 로 내지는 않았다**는 공백을 가리킨다 — 우리가 SBR+PO(§4)를 얹는 이유가 바로 이 "
    "공백이다.",
))

# =========================================================================== #
#  §1
# =========================================================================== #
cells.append(md(
    "---",
    "## §2. 공백을 다섯 측정으로 확인",
    "",
    "'경로 솔버에 산란적분이 없다' 는 주장을 말이 아니라 측정으로 못박는다. 같은 챔버·같은 드론에서 "
    "`PathSolver` 를 돌려 다섯 패널 [A]~[E] 를 얻었다 — 광선을 4억 발 쏘고([A]), 답을 아는 금속 "
    "구·평판을 넣고([E][D]), 표적 크기를 키우고([D]), 재질 손잡이를 돌린다([B][C]).",
    "",
    "![no_sigma](outputs/figures/report3_f6_no_sigma.png)",
    "",
    "<sub>다섯 패널 모두 Sionna RT `PathSolver` 결과. 아래에서 [A]·[E] → [D] → [B][C] 순으로 "
    "읽는다. 결론: 산란적분 단계가 없는 경로 솔버만으로는 σ 가 나오지 않는다.</sub>",
))

# =========================================================================== #
#  §1.5 — ISAC 서사 (통신 vs 센싱)
# =========================================================================== #
cells.append(md(
    "### [A]·[E] — 빛줄기를 더 쏴도 값이 안 멈춘다",
    "",
    "'광선을 더 쏘면 되지 않나?' 안 된다. 근본 이유는 광선이 표적을 적게 맞혀서가 아니라 "
    "**되돌아온 확산 경로를 위상 맞춰 더한 합에는 수렴할 대상(산란적분)이 없기 때문**이다 — "
    "광선을 늘리면 임의의 확산 경로를 더 셀 뿐이라, 복권을 더 사도 '당첨금 평균' 이 안정되지 않는 것과 "
    f"같다. (작고 먼 표적일수록 {R1:.0f} m 처럼 맞는 광선이 적은 건 사실이나 부차적 — [E] 의 "
    "금속 구는 400M 발에도 경로 0개다.)",
))

# =========================================================================== #
#  §2
# =========================================================================== #
cells.append(md(
    f"**[A] 광선 예산 — 늘려도 안 수렴.** 드론에 쏘는 광선을 **{ray_lo:.0f}M → {ray_hi:.0f}M 발**로 "
    f"16배 늘리면 되돌아온 경로 수는 {np_lo}→{np_hi}개로 늘지만, 위상 맞춰 더한 **코히런트 합은 "
    f"{coh_lo:.1f}→{coh_hi:.1f} dB, {coh_climb:+.1f} dB 계속 커지기만** 하고 한 값에 수렴하지 않는다. "
    f"랜덤 확산 경로를 몬테카를로로 세는 중이기 때문 — **'값이 안 멈춘다' 는 것 자체가 σ 가 아니라는 "
    f"신호**다(진짜 σ 라면 광선을 늘릴수록 안착해야 한다). 참 RCS 비 {sbr_target:.1f} dB(빨간 점선)를 "
    "가로질러 올라갈 뿐 그 값을 '재는' 게 아니다.",
    "",
    f"**[E] 정확한 금속 구 — 경로 0개, 영원히.** 완전도체(PEC) 구는 σ 를 정확히 안다(Mie 급수. "
    f"ka≫1 에서 πr² 로 수렴). 반지름 "
    f"{sph_radii[0]}·{sph_radii[-1]:.0f} m 구에 광선을 **{sph_maxspp:.0f}M 발**까지 쏴도 되돌아온 "
    f"경로는 **{sorted(sph_npaths)[0]}개**다(곡면은 이미지법이 반사점을 못 찾고, 금속 S=0 이라 확산 "
    f"채널도 안 열린다). 대조군인 평평한 금속판은 광선 1M 발에 경로 {ctrl_paths}개({ctrl_db:.2f} dB)를 "
    "정확히 낸다 — 문제는 광선 부족이 아니라 **곡면의 되비침을 만드는 적분 단계가 없어서**다.",
))

cells.append(code(
    "# §2 재현 — 광선 예산: 늘려도 표적 에코가 한 값에 안 멈춘다 (그림 [A])",
    "import json",
    "F = json.load(open('outputs/report3_rt.json'))",
    "print('광선[M]   경로수   코히런트합[dB]   인코히런트[dB]')",
    "for r in F['A_rays']['rows']:",
    "    print(f\"{r['spp']/1e6:6.0f}   {r['n_paths']:5d}     {r['coh_db']:8.1f}       {r['incoh_db']:8.1f}\")",
    "a = F['A_rays']['rows']",
    "print(f\"\\n코히런트 합 25M->400M: {a[-1]['coh_db']-a[0]['coh_db']:+.1f} dB  (수렴 안 함)\")",
    "",
    "# PEC 구: 16M 발까지 쏴도 경로 0개 (독립 재현; 그림 [E] 는 400M 까지 쏜다)",
    "V = json.load(open('outputs/rt_no_rcs_verify.json'))",
    "for row in V['C_pec_sphere']:",
    "    print(f\"구 r={row['r']}m  광선={row['spp']/1e6:.0f}M  ->  경로 {row['n_paths']}개\")",
))

# =========================================================================== #
#  §3
# =========================================================================== #
_plate_rows = [f"| {s:.1f} m | {sg:.1f} dBsm | {rt_flat:.2f} dB |"
               for s, sg in zip(plate_sides, plate_sig)]

cells.append(md(
    "### [D] 결정적 증거 — 평판을 키워도 RT 값이 꼼짝 안 한다",
    "",
    "밝기(σ)의 본질은 크기다. 평판의 참 RCS 는 σ=4πA²/λ² 이라, 한 변을 "
    f"{plate_sides[0]:.1f}→{plate_sides[-1]:.0f} m 로 키우면 참 σ 가 "
    f"**{plate_sig[0]:.1f}→{plate_sig[-1]:.1f} dBsm**, 즉 **{plate_span:.0f} dB(십수만 배)** "
    "넓어져야 한다.",
    "",
    "| 판 한 변 | 참 RCS (σ=4πA²/λ²) | **Sionna RT 값** |",
    "|---|---|---|",
    *_plate_rows,
    "",
    f"참 σ 가 **{plate_span:.0f} dB** 넓어지는 동안 RT 값은 **{rt_flat:.2f} dB 에서 시드 편차 "
    f"~{rt_span*1e6:.0f}×10⁻⁶ dB** 로 완전히 평평하다 — 판 크기가 RT 값에 **전혀** 안 들어간다. "
    "RT 가 재는 것은 판의 밝기가 아니라 '거울에 튕긴 경로 하나' 이고, 그 값은 거울상(image-source) "
    "공식으로 정확히 예측된다:",
    "",
    "$$\\text{RT 값} \\;=\\; 20\\log_{10}\\!\\frac{L}{R_1+R_2} "
    f"\\;=\\; 20\\log_{{10}}\\!\\frac{{{L:.1f}}}{{{R1:.1f}+{R2:.1f}}} \\;=\\; {img_formula:.2f}\\ \\text{{dB}}$$",
    "",
    f"이 식에는 **판의 크기가 없다** — 거리만 있다. 측정값 {rt_flat:.2f} dB 가 공식값 {img_db:.2f} dB "
    "와 정확히 일치한다는 것은, RT 가 크기와 무관한 거울 경로를 재고 있다는 결정적 증거다. 여기엔 "
    "몬테카를로 잡음도 확산도 없는데(경로 딱 1개) 그 안정된 값에 표적 크기 정보가 담겨 있지 않다.",
))

cells.append(code(
    "# §2 재현 — 평판을 키워도 RT 값은 불변 (그림 [D])",
    "import json, math",
    "V = json.load(open('outputs/rt_no_rcs_verify.json'))",
    "g = V['geometry']; L, R1, R2 = g['L'], g['R1'], g['R2']",
    "print('판 한변   참 RCS[dBsm]   RT 값[dB]')",
    "for r in V['A_plate']:",
    "    print(f\"{r['side']:5.1f}    {r['sigma_dbsm']:9.1f}     {r['ratio_db']:8.2f}\")",
    "sig = [r['sigma_dbsm'] for r in V['A_plate']]",
    "rt  = [r['ratio_db']  for r in V['A_plate']]",
    "print(f\"\\n참 σ 범위: {max(sig)-min(sig):.0f} dB 넓어짐\")",
    "print(f\"RT 값 범위: {max(rt)-min(rt):.6f} dB  (사실상 불변)\")",
    "print(f\"거울상 공식 20log10(L/(R1+R2)) = {20*math.log10(L/(R1+R2)):.2f} dB\")",
))

# =========================================================================== #
#  §4
# =========================================================================== #
cells.append(md(
    "### [B]·[C] 산란계수 S 는 표적이 아니라 손잡이",
    "",
    "경로 솔버도 재질에 **산란계수 S**(입사파를 거울반사 대신 사방으로 흩뿌리는 비율)를 주면 확산 "
    "경로로 어떤 값을 낸다. 하지만 S 는 표적의 성질이 아니라 우리가 표에 적어 넣는 손잡이다.",
    "",
    f"**[B]** 재질 표의 S 에 배수를 곱해 **×{S_mult_lo:g}→×{S_mult_hi:g}"
    f"({S_mult_hi / S_mult_lo:.0f}배)** 로 바꾸면 표적 에코가 **{S_x4_delta:+.1f} dB** 움직인다"
    f"(코히런트 합 {S_half_coh:.1f}→{S_2x_coh:.1f} dB, 시드 {len(S_seeds_fig)}개 평균). 배수는 "
    f"표의 값에 곱해지므로 ITU 금속(S=0)은 0 그대로이고 플라스틱만 {S_pl_lo:.2f}→{S_pl_hi:.2f} 로 "
    "움직인다. **표적은 하나도 안 바꿨는데** 재질 숫자 하나로 '에코' 를 원하는 만큼 끌 수 있다 — "
    "물리적 σ 라면 이래서는 안 된다.",
    "",
    f"별도 원장(`rt_ray_budget.json`, 시드 {len(S_ov_seeds)}개)은 같은 손잡이를 더 넓게, 이번엔 "
    f"**전 부품의 S 를 한 값으로 덮어써서**(금속 포함) S={S_ov_lo:g}→{S_ov_hi:g} 로 훑는다. 로그 "
    f"기울기는 **인코히런트 합 {slope_dec:.1f} dB/decade · 코히런트 합 {slope_coh:.1f} dB/decade** 로 "
    "두 배 넘게 다르다 — 두 합은 정의가 다르므로(위상 맞춘 합 vs 전력 합) 한 문장에 섞어 인용하면 "
    f"안 된다. 그리고 참 σ 비 {sbr_target:.1f} dB 를 재현하는 값은 S≈{S_match:.2f} 인데"
    f"(인코히런트 곡선 보간), 그건 예측이 아니라 **피팅**이다.",
    "",
    f"**[C]** 게다가 ITU-R P.2040 표에서 **금속의 S={itu_metal_S:.0f}**(금속은 흩뿌리지 않고 튕긴다). "
    f"그런데 드론의 참 밝기를 만드는 것이 바로 그 금속부(모터·배터리·PCB·카메라)다 — "
    f"금속만 남겨도 σ 가 전체의 **{metal_share:.1f}%**({d_metal_db:+.2f} dB)로 거의 그대로이고, "
    f"거꾸로 금속을 빼면 **{diel_share:.1f}%**({d_diel_db:+.2f} dB)로 내려앉는다:",
    "",
    "| 부분 | 참 RCS (SBR) | 전체 대비 | 확산 채널(S>0) 기여 |",
    "|---|---|---|---|",
    f"| 전체 | {sig_full:.2f} dBsm | — | — |",
    f"| **금속부** (모터·배터리·PCB·카메라) | {sig_metal:.2f} dBsm | {d_metal_db:+.2f} dB "
    f"({metal_share:.1f}%) | **S=0 → 기여 0** |",
    f"| 유전체부 (플라스틱 바디·프로펠러) | {sig_diel:.2f} dBsm | {d_diel_db:+.2f} dB "
    f"({diel_share:.1f}%) | S>0 |",
    "",
    f"<sub>이 σ 분해는 그림 [C] 와 같은 원장이다(`report3_rt.json C_metal`, el {el_C:.0f}°·방위 "
    f"{n_az_C}점 평균). report08 이 쓰는 조밀 원장(같은 el, 방위 {n_az_dense}점, "
    f"`report2_waveform_rcs.json`)에서는 같은 분해가 전체 {d2_full:.2f} / 금속 {d2_metal:.2f} / "
    f"유전체 {d2_diel:.2f} dBsm 이고, 거기서는 금속만 남긴 값이 전체보다 오히려 "
    f"{d2_metal_delta:+.2f} dB 높다. 부분들이 코히런트하게 간섭하고 유전체 셸 투과·가림이 겹치므로 "
    "'전력 몇 %' 분해는 두 원장 모두에서 근사이며, 100% 를 넘는 이 초과분은 아직 닫히지 않은 항목이다. "
    "어느 원장에서도 이 절의 결론(밝기를 만드는 것은 금속부인데 ITU 표의 금속 S=0)은 바뀌지 "
    "않는다.</sub>",
    "",
    f"경로 솔버의 확산 '에코' 는 손잡이로 {S_x4_delta:+.0f} dB 움직이는 임의값이고, 정작 혼자서도 "
    f"밝기의 {metal_share:.0f}% 를 내는 금속엔 S=0 이라 그 부분이 통째로 빠져 있다 — 어느 쪽으로 "
    "봐도 물리적 RCS 가 아니다.",
))

cells.append(code(
    "# §2 재현 — S 는 손잡이: 돌리면 값이 따라 움직인다",
    "# (1) 그림 [B] 원장: 재질 표의 S 에 '배수' 를 곱한다 -> ITU 금속(S=0)은 0 그대로",
    "import json, math",
    "F = json.load(open('outputs/report3_rt.json'))",
    "print('S 배수   플라스틱 S   코히런트 에코[dB]   인코히런트[dB]')",
    "for r in F['B_scatter']['rows']:",
    "    print(f\"  x{r['mult']:.1f}        {r['S_plastic']:.2f}      {r['coh_db']:8.2f}       {r['incoh_db']:8.2f}\")",
    "",
    "# (2) 별도 원장: 전 부품의 S 를 한 값으로 '덮어쓴' 스윕 (시드 5개, S = 0.1 ~ 0.8).",
    "#     두 합은 정의가 다르므로 기울기를 따로 낸다.",
    "RB = json.load(open('outputs/rt_ray_budget.json'))",
    "rows = sorted([r for r in RB['B_S_sweep'] if r['n_paths']], key=lambda r: r['S'])",
    "def slope(key):",
    "    xs = [math.log10(r['S']) for r in rows]; ys = [r[key] for r in rows]",
    "    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)",
    "    return sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sum((x-mx)**2 for x in xs)",
    "print(f\"\\n인코히런트 {slope('incoh_db'):5.1f} dB/decade   (기록값 B_fit = {RB['B_fit']['slope_db_per_decade']:.1f})\")",
    "print(f\"코히런트   {slope('coh_db'):5.1f} dB/decade   <- 같은 손잡이인데 기울기가 두 배 넘게 다르다\")",
    "print(f\"참 σ 비 {RB['truth']['ratio_db_truth']:+.2f} dB 를 재현하는 S = {RB['B_fit']['S_to_match_truth']:.2f}  (인코히런트 곡선 보간 = 피팅)\")",
    "",
    "# (3) 금속의 산란계수 S=0 -> 밝기를 만드는 금속이 확산 채널에서 통째로 빠진다 (그림 [C])",
    "C = F['C_metal']; s = C['sigma']",
    "print(f\"\\n금속 S = {C['itu_metal_S']:.0f}   전체 {s['full_dbsm']:+.2f} / 금속만 {s['metal_only_dbsm']:+.2f} / 유전체만 {s['dielectric_only_dbsm']:+.2f} dBsm\")",
    "print(f\"금속만 남겨도 σ 는 전체의 {C['metal_share_pct']:.1f}% — 그런데 그 금속의 확산 채널 기여는 0\")",
))

# =========================================================================== #
#  §5
# =========================================================================== #
cells.append(md(
    "---",
    "## §3. 선행 연구는 이 공백을 어떻게 채웠나 — 우회 세 갈래",
    "",
    "이 한계는 우리만의 주장이 아니라 §1 에서 인용한 Sionna 자체 문서가 규정한 **범위**다. 그래서 "
    "소형 표적의 **절대 σ(dBsm)** 를 스톡 Sionna 로 메쉬에서 직접 낸 선행은 우리가 확인한 범위에서 "
    "없고(§1 에서 본 대로 표적 반환·마이크로도플러 자체는 스톡 Sionna 로도 나온다), Sionna 를 센싱에 "
    "쓰는 연구들은 표적 밝기를 **외부에서 구해 채널에 주입**하되 그 '외부' 를 세 갈래로 채운다:",
    "",
    "| 갈래 | 방식 | 대표 선행 |",
    "|---|---|---|",
    "| **(a)** | 스톡 Sionna 직접 (산란적분 없음) | 표적 반환·마이크로도플러는 나오나 **절대 σ 는 안 나옴** — clutter·md-rt |",
    "| **(b)** | 재질 **확산계수 S** 가정 | Great-X (arXiv:2507.08716) · Deterministic-Modeling ISAC (arXiv:2603.28736, 79 GHz 차량) |",
    "| **(c)** | 외부에서 RCS 계산·가정 후 주입 $h=h_{bg}+h_{target}$ | LAMBDA=Sionna+CADFEKO(arXiv:2607.03826) · Temporal-GNN=점산란체(arXiv:2604.08306) · 3GPP Rel-19 |",
    "| **(d)** | 커스텀 **산란 add-on**(SBR+PO·UTD) | Ziganshin UTD(arXiv:2604.05991) · GPU BVH SBR+PO(arXiv:2604.09243) |",
    "",
    f"<sub>⚠ (b) 의 Deterministic-Modeling ISAC 이 확산 S 로 간 **이유는 우리와 다르다.** 원문은 "
    f"*\"Purely specular RT on low-polygon meshes underestimates power **at mmWave/sub-THz** due to "
    f"**electromagnetic roughness**; direct meshing at O(λ/10) is infeasible **at E-band**\"* 로, "
    f"79 GHz 대역의 **표면 거칠기**를 이유로 들며 그 문장 자체도 자기 발견이 아니라 인용이다. "
    f"우리 {fc / 1e9:.1f} GHz 에서 λ/10 = {lam * 100:.2f} mm 이고 우리 기체 메쉬는 "
    f"{n_faces_full:,}면이라 그 메싱이 계산상 불가능한 영역이 아니다. 우리가 말하는 공백의 원인도 "
    f"거칠기가 아니라 **PO 적분 단계의 부재**다 — 그래서 이 논문은 (b) 갈래의 사례로만 인용하고 "
    f"§2 진단의 근거로는 쓰지 않는다.</sub>",
    "",
    "공통 아키텍처는 $h_{surv}=h_{direct}+h_{background}+h_{target}$ — 환경 전파는 Sionna 가 주고, "
    "표적 산란만 외부 물리로 계산해 두 전파 구간 사이에 끼워 넣는다. 우리는 **(d)로 값을 계산해 "
    "(c)로 주입**하는 길을 택한다(§4). "
    "그 (d) 중에서도 **Ziganshin(arXiv:2604.05991)이 우리와 가장 가까운 선행**이다 — 둘 다 Sionna "
    "생태계 안에서 표적 산란만 얹지만 **붙이는 층이 다르다.** 그들은 Sionna-RT(v0.19) **솔버 자체를 "
    "확장해** UTD 회절(모서리·꼭짓점)을 그 안에 넣고, 우리는 Sionna 가 쓰는 **Mitsuba 광선엔진 위에 "
    "PO 표면적분을 따로 얹는다**(`PathSolver` 는 상속으로 확장하는 지점이 아니다 — MRO 실측). "
    "표적도 다르다: 그들은 큰 물체(차량·표준 구/원기둥), 우리는 작은 다중재질 드론이다.",
))

# =========================================================================== #
#  §6 자주 하는 오해 — 실제로 청중이 헷갈리는 지점 (Q&A)
# =========================================================================== #
cells.append(md(
    "---",
    "## §4. 우리가 쓴 방식 — (d) 자작 SBR+PO 를 (c) 로 주입",
    "",
    "우리는 **(d)** 갈래를 택한다 — 표적 밝기를 자작 **SBR+PO** 로 계산해 **(c)** 방식으로 채널에 "
    "주입한다. 핵심은 **새 광선엔진을 만들지 않는다**는 것이다: SBR 의 광선추적은 Sionna 가 이미 쓰는 "
    "**Mitsuba 3 / OptiX 엔진을 그대로** 재사용하고(중복계산 없음), 그 위에 표준 PO 표면적분만 얹는다. "
    "이는 GPU BVH SBR+PO(arXiv:2604.09243)와 **같은 계열**이다(기하광학 광선 전송 + 광선튜브 위 "
    "물리광학 표면적분).",
    "",
    "다만 **동일하지는 않다.** 그들의 SBR 합(식 7)은 비스듬함 계수 $2(\\hat{n}_i\\cdot-\\hat{k}_{inc})$ "
    "를 면적소 $\\Delta A$ 에 명시적으로 곱하고 적용범위를 **PEC·모노스태틱 후방산란 전용**으로 "
    "선언한다. 우리는 조명 방향에 수직인 균일 광선격자를 써서 같은 계수를 투영면적 $d^2$ 안에 "
    "흡수하고(변수변환), 거기에 다중재질 $|\\Gamma|$ · 유전체 셸 투과 · 바이스태틱을 얹는다. "
    "바이스태틱에서는 조명면 가중 $(\\hat n\\cdot\\hat u_i)$ 만 유지하므로 대가가 따른다 — 전방산란"
    "(β→180°)은 못 내고, 비볼록 표적의 깊은 널에서 상반성이 부분적으로만 성립한다"
    "(`src/rcs_sbr.py` 독스트링에 적용범위로 기록).",
    "",
    "역할 분담은 선행(LAMBDA·Temporal-GNN·3GPP Rel-19)이 공통으로 쓰는 그 구조 그대로다:",
    "",
    "- **환경(τ·도플러·반사·바닥)** = 🟢 **Sionna RT** — 산란적분이 필요 없는(거울반사만으로 옳은) "
    "부분이라 그대로 신뢰. 파형·지연 채널도 **Sionna PHY** (report05 검증).",
    "- **표적 밝기 σ** = 🟡 **SBR+PO** — Mitsuba 광선으로 조명면을 찾고 그 위에서 PO 적분. 스칼라 σ "
    "를 통째로 주입하는 대신 면 조각별 기여를 **복소장 E** 로 더해 **위상을 보존**한다"
    "(⚠ 편파는 보존하지 않는다 — `src/rcs_sbr.py` 의 E 는 복소 **스칼라**이고 재질 반사도 스칼라 |Γ| 다).",
    "",
    "![hybrid](outputs/figures/report3_f7_hybrid.png)",
    "",
    "<sub>파란 선(환경: 지연·도플러·기하)은 Sionna 가, 주황 선(표적 산란 σ(방위,고각))은 SBR+PO 가 "
    "담당한다. 두 엔진은 대체재가 아니라 잘하는 것이 다르다 — RT 는 방을 알고 표적 밝기를 모르며, "
    "SBR 은 표적 밝기를 알고 방을 모른다.</sub>",
    "",
    "![.](outputs/renders/anim/rcs_azimuth_mavic4pro.gif)",
    "",
    "<sub>SBR 이 계산한 되비침 밝기(RCS)를 방위각으로 스윕 — 각도마다 크게 출렁인다. 이 값이 위 "
    "하이브리드의 주황 항으로 채널에 들어간다.</sub>",
    "",
    "상용 툴(CADFEKO)로 대체하지 않은 이유는 **재현성**이다 — 유료라 재현이 막히고, 비공개 바이너리"
    "(RadarSimPy)나 모노스태틱·PEC 전용(RaytrAMP) 오픈 도구도 바이스태틱+다중재질 요구를 못 채운다. "
    "검증은 라이브러리 대조가 아니라 **기준해(평판 σ=4πA²/λ² · 구 정확 Mie + 해석 PO)와 실측 문헌 드론 RCS "
    "앵커**로 세운다 — 계산 절차는 **report07**, 절대값 결과는 **report08**.",
))

# =========================================================================== #
#  정리 + 다음 리포트
# =========================================================================== #
cells.append(md(
    "---",
    "## 정리",
    "",
    "1. **RCS(되비침 밝기)는 탐지에 필수** 다 — 표적이 밝아야 잡힌다. 그 밝기는 표면 조각들의 "
    "되쏨을 **위상 맞춰 다 더한(산란적분)** 값인데, Sionna `PathSolver` 는 이 ∫ 단계가 없어 "
    "경로별 지연·도플러·복소이득만 준다(§1).",
    f"2. **다섯 측정으로 확인했다:** 광선을 {ray_lo:.0f}M→{ray_hi:.0f}M 발로 늘려도 에코가 "
    f"{coh_climb:+.1f} dB 계속 커지고, 정확한 금속 구는 {sph_maxspp:.0f}M 발에도 경로 0개, 평판을 "
    f"{plate_span:.0f} dB 키워도 RT 값은 {rt_flat:.2f} dB 불변, 산란계수 S 를 돌리면 값이 "
    f"{S_x4_delta:+.0f} dB 따라 움직이며 금속엔 S=0(§2).",
    "3. **이것은 '못 한다' 가 아니라 역할 분담이다.** 선행(LAMBDA·Temporal-GNN·3GPP)이 쓰는 우회 "
    "세 갈래 중 (d)+(c) 를 따라(§3), 환경은 Sionna RT/PHY 가 주고 표적 밝기 σ 는 **자작 SBR+PO** 가 "
    "Mitsuba 엔진을 재사용해 계산한다(§4). Sionna 는 틀린 게 아니라 **전파 도구**다.",
    "",
    "> **다음 리포트**: [report07](report07.ipynb) — 여기서 '경로 솔버로는 못 만든다' 고 못박은 그 "
    "밝기를, **SBR 이 어떻게 계산하는가**(광선으로 조명면을 찾고 그 위에서 PO 적분). "
    "평판·금속 구 해석해로 검증하는 과정까지.",
))

# =========================================================================== #
#  노트북 저장
# =========================================================================== #
nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

with open(NB, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"✅ {NB}  ({len(cells)} cells)")
#  자기검사 — 우리가 낸 인코히런트 기울기가 기록된 B_fit 과 같은지(같은 원장·같은 적합)
print(f"   ↳ S 기울기 자기검사: 인코히런트 {slope_incoh:.3f} vs B_fit {slope_dec:.3f} "
      f"(Δ={abs(slope_incoh - slope_dec):.2e}) · 코히런트 {slope_coh:.3f} dB/decade")
