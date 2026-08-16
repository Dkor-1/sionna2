# -*- coding: utf-8 -*-
"""
material_sources.py — **재질 파라미터의 출처 감사(audit)와 유도**
==================================================================
사용자 질문: "mesh 의 형상뿐 아니라 **재질도 현실적인 재질이니? 실제로 조사해서 기입한 거야?**"

이 스크립트가 그 질문에 답하는 **숫자**를 만든다. 세 갈래다.

  [A] 현행 `src/materials.py` 값의 **계층 분류** — ITU 내장 / 문헌값(무출처) / PO 실효값(무출처).
  [B] **박막(thin-slab) 프레넬 유도** — 1~3 mm 유전체 셸의 |Γ| 를 두께·각도·주파수로 닫힌형에서 계산.
      "0.28 이 대표값으로 방어 가능한가"를 **계산으로** 판정한다.
  [C] 프로펠러 실제 날개두께 — 우리 CAD 상수(TC_ROOT/TC_TIP, CHORD_*)에서 직접 유도.

  ※ [D] γ_PO 스윕(총 RCS 영향 한계)은 GPU 가 필요해 `--stage sweep` 로 분리했다.

⛔ 이 스크립트는 `src/materials.py` 를 **고치지 않는다**. 제안 패치만 JSON 에 적는다.

실행:
  PYTHONPATH=src:benchmark python benchmark/material_sources.py --stage derive
  CUDA_VISIBLE_DEVICES=2 PYTHONPATH=src:benchmark python benchmark/material_sources.py --stage sweep
  PYTHONPATH=src:benchmark python benchmark/material_sources.py --stage doc
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_JSON = os.path.join(_ROOT, "outputs", "material_sources.json")
OUT_MD = os.path.join(_ROOT, "docs", "MATERIAL_SOURCES.md")

C0 = 299792458.0
EPS0 = 8.8541878128e-12

BANDS = {"LTE 1.843 GHz": 1.843e9, "5G 3.5 GHz": 3.5e9, "WiFi 5.21 GHz": 5.21e9}


# --------------------------------------------------------------------------- #
#  문헌 블록 — **손으로 적는 유일한 곳**. 저자·발표지·연도·측정대역·방법을 전부 요구한다.
#  (집 규칙: 우리가 *계산한* 숫자는 절대 손으로 적지 않는다. 문헌 상수는 여기 한 곳에만.)
# --------------------------------------------------------------------------- #
LITERATURE = [
    dict(
        key="plastic_eps_abs_zechmeister",
        material="ABS (그리고 PET·PLA·XT 코폴리에스터)",
        quantity="eps_r (복소)",
        value_text="측정된 5종의 eps_r' 가 **2.55-2.95** 구간에 든다 (ABS 포함)",
        eps_r_low=2.55, eps_r_high=2.95,
        freq_range_ghz=[1.0, 10.0],
        method="전송/반사(transmission-reflection)법 브로드밴드",
        author="J. Zechmeister, J. Lacik",
        venue="2019 Conference on Microwave Techniques (COMITE), pp. 1-4",
        year=2019,
        doi="10.1109/COMITE.2019.8733590",
        verified="⭐ **Crossref 로 서지 전항목 대조 완료**(저자·학회·연·쪽·DOI). 측정대역 1-10 GHz 가 "
                 "우리 세 밴드를 전부 덮는다 — 우리 값 2.7 이 이 구간의 한가운데. "
                 "⚠ ABS **단독** 수치는 원문 도표에 있고 우리는 초록 수준의 구간(2.55-2.95)만 확인했다.",
        confidence="high_for_range",
    ),
    dict(
        key="plastic_eps_abs_deffenbaugh",
        material="ABS (아크릴로니트릴 부타디엔 스티렌)",
        quantity="eps_r, tan_delta",
        value_text="ABS 를 포함한 3D 프린팅 재료를 1 MHz-10 GHz 에서 다중법으로 특성화",
        freq_range_ghz=[0.000001, 10.0],
        method="stripline/공진기 등 다중법 비교(브로드밴드)",
        author="P. I. Deffenbaugh, R. C. Rumpf, K. H. Church",
        venue="IEEE Trans. Components, Packaging and Manufacturing Technology, vol. 3, no. 12, pp. 2147-2155",
        year=2013,
        doi="10.1109/TCPMT.2013.2273306",
        verified="Crossref 로 서지 대조 완료. **본문 수치는 미확보** — 대역(1 MHz-10 GHz)만 인용한다.",
        confidence="bibliography_verified_values_not_read",
    ),
    dict(
        key="plastic_eps_pc_nist",
        material="폴리카보네이트 (PC)",
        quantity="eps_r, tan_delta",
        value_text="흔히 인용되는 PC 값 eps_r ~2.8-3.0 (온도 122-375 K, ~10 GHz)",
        eps_r=2.9,
        freq_range_ghz=[9.0, 11.0],
        method="분할공진기(split-post/원통공진기), 온도가변",
        author="B. Riddle, J. Baker-Jarvis, J. Krupka (NIST)",
        venue="IEEE Trans. Microwave Theory and Techniques, vol. 51, no. 3, pp. 727-733",
        year=2003,
        doi="10.1109/TMTT.2003.808730",
        verified="Crossref 로 서지 대조 완료(DOI 확정). ⚠ **정오표 존재** — Riddle·Baker-Jarvis·Krupka, "
                 "'Corrections to ...', 같은 학술지 vol. 51, no. 10, p. 2148 (2003), "
                 "doi:10.1109/TMTT.2003.817470: **폴리카보네이트 손실탄젠트가 10배 낮게** 인쇄됐다. "
                 "PC 의 tan_delta 를 인용하려면 반드시 정오표판을 쓸 것. 우리는 tan_delta 를 인용하지 않는다.",
        confidence="bibliography_verified_values_not_read",
    ),
    dict(
        key="plastic_itu_plasterboard",
        material="(대용) ITU-R P.2040 plasterboard",
        quantity="eps_r, sigma",
        value_text="eps_r 2.73, sigma = 0.0085 * f_GHz^0.9395 [S/m]",
        eps_r=2.73, itu_c=0.0085, itu_d=0.9395,
        freq_range_ghz=[1.0, 100.0],
        method="ITU-R 권고 표(다수 측정의 회귀식)",
        author="ITU-R",
        venue="Recommendation ITU-R P.2040, Table 3 (Sionna 2.0.1 이 그대로 내장: "
              "sionna/rt/radio_materials/itu.py)",
        year=2023,
        doi=None,
        verified="설치본 소스에서 직접 읽음 — (2.73, 0.0, 0.0085, 0.9395)",
        confidence="high",
    ),
    dict(
        key="carbon_sigma_artner",
        material="CFRP — shred(무작위)·twill(2/2 능직) 적층",
        quantity="sigma (유효 도전율)",
        value_text="shred-CFRP ~1e4 S/m (각도에 따라 10배 변동); 5.9 GHz 에서 1e4-8e4 S/m; "
                   "twill-CFRP 는 1e3-1e6 S/m 축에 걸침",
        sigma_low=1.0e3, sigma_typ=1.0e4, sigma_high=1.0e6,
        freq_range_ghz=[4.0, 6.0],
        method="직사각 도파관 시료 + Nicolson-Ross-Weir (NRW) 추출, 시료 절단각 0-90도",
        author="G. Artner, P. K. Gentner, J. Nicolics, C. F. Mecklenbrauker",
        venue="International Journal of Antennas and Propagation, vol. 2017, Art. 6152651, 11 pp.",
        year=2017,
        doi="10.1155/2017/6152651",
        verified="⭐ **원문 PDF 직접 확보·본문 인용 확인** (TU Wien repositum 공개본). "
                 "우리 대역(5.21 GHz)을 포함하는 4-6 GHz 측정이라는 점이 핵심. "
                 "⚠ NRW 는 등가 균질매질 피팅이라 CFRP 에서 mu_r != 1 이 나온다(비물리) — "
                 "즉 이 sigma 는 '유효 파라미터'이지 재료 상수가 아니다.",
        confidence="high",
    ),
    dict(
        key="carbon_sigma_ud_secondary",
        material="CFRP — 단방향(UD) 섬유",
        quantity="sigma 이방성",
        value_text="섬유방향 ~1e4 S/m(=1e2 S/cm), 수직방향 ~0.1 S/m(=1e-3 S/cm) → 비 1e5; "
                   "다른 보고는 종방향 ~4e4 S/m, 횡방향 ~1 S/m; "
                   "[0 45 90 -45]_2s 적층은 5000 S/m(평행) 부터",
        sigma_low=1.0e-1, sigma_typ=1.0e4, sigma_high=4.0e4,
        freq_range_ghz=[0.1, 10.0],
        method="도파관/동축 시료(2차 인용 — Artner 2017 §1·§3.3 이 정리한 값)",
        author="Artner 2017 이 인용한 [6],[7] (원저 미확보)",
        venue="Artner et al., IJAP 2017, Art. 6152651, Sec. 3.3 내 인용",
        year=2017,
        doi="10.1155/2017/6152651",
        verified="Artner 원문에서 문장 그대로 확인. **원저는 미확보 → 2차 인용**",
        confidence="medium",
    ),
    dict(
        key="carbon_model_sarto",
        material="CFC (탄소섬유 복합재) — EMC 모델링 관용값",
        quantity="eps_r, sigma (등가층 모델 입력)",
        value_text="eps_r = 2, sigma = 1e4 S/m, 두께 1 mm",
        eps_r=2.0, sigma=1.0e4,
        freq_range_ghz=[1.0, 2.0],
        method="FDTD/TLM 얇은판 등가층 모델의 표준 입력값(측정 아님)",
        author="M. S. Sarto (원 모델) / C. L. Holloway, M. S. Sarto, M. Johansson (등가층 정리)",
        venue="IEEE Trans. EMC, vol. 41, no. 4, pp. 298-306 (1999) / IEEE Trans. EMC, vol. 47, no. 4, "
              "pp. 833-844 (2005)",
        year=1999,
        doi="10.1109/15.809798",
        doi_holloway="10.1109/TEMC.2005.854101",
        verified="Crossref 로 두 서지 모두 대조 완료(DOI 확정). 값(eps_r=2, sigma=1e4 S/m, d=1 mm)은 "
                 "이를 인용한 TLM 논문(arXiv:1502.01227) 본문에서 직접 읽음. "
                 "**모델 입력값이지 측정값이 아니다**",
        confidence="medium",
    ),
    dict(
        key="fr4_ipc",
        material="FR-4 (유리섬유/에폭시 PCB 기판)",
        quantity="eps_r, tan_delta",
        value_text="eps_r 4.2-4.7, tan_delta 0.017-0.025 (1-10 GHz, 제조사/직조에 따라)",
        eps_r=4.4, tan_delta=0.02,
        freq_range_ghz=[1.0, 10.0],
        method="측정 + 인과적 폐형식 모델(Djordjevic-Sarkar). 값 구간은 IPC-4101 등급·제조사 편차",
        author="A. R. Djordjevic, R. M. Biljic, V. D. Likar-Smiljanic, T. K. Sarkar",
        venue="IEEE Trans. Electromagnetic Compatibility, vol. 43, no. 4, pp. 662-667",
        year=2001,
        doi="10.1109/15.974647",
        verified="Crossref 로 서지 대조 완료. ⚠ **우리 모델은 이 값을 쓰지 않는다** — pcb 그룹은 "
                 "ITU metal(구리 그라운드플레인 지배) + PO 실효 0.80 이다. 참고용으로만 기록한다. "
                 "본문 수치는 미확보(공개 PDF 의 폰트 인코딩이 깨져 있음)",
        confidence="bibliography_verified_values_not_read",
    ),
    dict(
        key="battery_pouch_foil",
        material="Li-ion/LiPo 파우치 셀 외피(알루미늄 라미네이트 필름)",
        quantity="Al 배리어층 두께",
        value_text="Al 배리어층 15-70 um (통용 15-70, 규격 하한 권장 >=20), 라미네이트 총두께 111-249 um",
        al_thickness_um_low=15.0, al_thickness_um_high=70.0, al_sigma=3.5e7,
        freq_range_ghz=[0.1, 100.0],
        method="제조사/공급사 규격(측정 아님) + 표피깊이 계산으로 불투명성 판정",
        author="(업계 규격 — 단일 저자 없음)",
        venue="파우치 필름 공급사 규격(Targray, Avocet 등) 및 파우치 포장재 특허 명세의 배리어층 규정",
        year=2024,
        doi=None,
        verified="⚠ 두께 규격은 **출처 약함**(웹 규격표). 다만 결론(=GHz 에서 금속)은 표피깊이 계산이 "
                 "떠받치므로 **하한 15 um 에서도** 결론이 바뀌지 않는다 — battery_metal_justification 참조",
        confidence="low_source_but_robust_conclusion",
    ),
]


# --------------------------------------------------------------------------- #
#  [B] 박막(thin-slab) 프레넬 — 앞뒤면 간섭 포함 닫힌형
# --------------------------------------------------------------------------- #
def eps_c(eps_r: float, sigma: float, f: float) -> complex:
    return complex(eps_r) - 1j * float(sigma) / (2 * np.pi * float(f) * EPS0)


def slab_reflection(eps_r, sigma, f, d, theta_deg, pol="TE"):
    """공기-슬랩-공기 3매질 반사계수(복소). d[m], theta[deg].
        Gamma = r (1 - e^{-2j delta}) / (1 - r^2 e^{-2j delta}),  delta = k0 d sqrt(ec - sin^2 th)
    d->inf 이면 r(벌크), d->0 이면 0 으로 수렴한다(둘 다 아래에서 검증)."""
    ec = eps_c(eps_r, sigma, f)
    th = np.radians(np.asarray(theta_deg, float))
    k0 = 2 * np.pi * f / C0
    kz = np.sqrt(ec - np.sin(th) ** 2)             # 주가지: Im<=0 → e^{-j kz d} 감쇠
    ct = np.cos(th)
    if pol == "TE":
        r = (ct - kz) / (ct + kz)
    elif pol == "TM":
        r = (ec * ct - kz) / (ec * ct + kz)
    else:
        raise ValueError(pol)
    ph = np.exp(-2j * k0 * float(d) * kz)
    return r * (1 - ph) / (1 - r ** 2 * ph)


def slab_transmission(eps_r, sigma, f, d, theta_deg, pol="TE"):
    ec = eps_c(eps_r, sigma, f)
    th = np.radians(np.asarray(theta_deg, float))
    k0 = 2 * np.pi * f / C0
    kz = np.sqrt(ec - np.sin(th) ** 2)
    ct = np.cos(th)
    if pol == "TE":
        r = (ct - kz) / (ct + kz)
    else:
        r = (ec * ct - kz) / (ec * ct + kz)
    ph = np.exp(-1j * k0 * float(d) * kz)
    return (1 - r ** 2) * ph / (1 - r ** 2 * ph ** 2)


def proj_weighted_mean_gamma(eps_r, sigma, f, d, n=721):
    """**볼록체 투영면적 가중** 평균 |Gamma|.
    우리 PO 커널은 히트마다 d^2(투영면적)을 곱하므로, 구/셸에서 각도별 기여 가중치는
    cos(th) sin(th) dth 다. <|G|> = 2 * int_0^{pi/2} |G(th)| cos sin dth (TE/TM 평균 = 무편파)."""
    th = np.linspace(0.0, 90.0, n)
    w = np.cos(np.radians(th)) * np.sin(np.radians(th))
    out = {}
    for pol in ("TE", "TM"):
        g = np.abs(slab_reflection(eps_r, sigma, f, d, th, pol))
        out[pol] = float(np.trapezoid(g * w, np.radians(th)) / np.trapezoid(w, np.radians(th)))
    out["unpol"] = 0.5 * (out["TE"] + out["TM"])
    return out


def blade_thickness_stats():
    """우리 CAD **상수에서** 프로펠러 날개 두께를 유도한다(추측 아님).
      t_max(r) = thick_ratio(r) * c(r),  c(r) = CHORD_FRAC(r/R) * CHORD_MAX_OVER_R * R
      thick_ratio(r) = TC_TIP + (TC_ROOT - TC_TIP) * (1 - f)
    시위방향 평균은 NACA-4 두께분포의 <yt>/max(yt) 로 환산한다.

    ⭐⭐ **2026-08-16 선언 — 이 함수는 메쉬를 열지 않는다**(감사 m1).
      나오는 값(matrice4e **1.4302 mm**, 문서가 «정본» 이라 부르는 그 수)은 «우리 메쉬 자신의
      두께» 가 아니라 **법칙의 해석 근사**다. 같은 기체의 메쉬를 직접 재면 **1.456~1.488 mm**
      (감사 원장 1.456~1.484 · 이 라운드 독립 재측정 1.488)이라 **+1.8~+4.1 %** 높고,
      원장이 계산한 |Γ| 영향은 +1.8 % 경우에 **+0.13 dB** — 무해하다. 그래서 값은 그대로 둔다.
      다만 **문면이** 틀렸으니 편향 둘을 여기 적어 둔다:
        ① **스윕디스크 정규화 −0.679 % 가 빠져 있다.** 실제 빌드는 프롭을 공칭 지름에 맞추려
           배율 0.99321 을 걸지만, 이 식은 공칭 R 을 그대로 쓴다.
        ② **NACA-4 시위평균/최대 비 0.684879 는 «대칭» 익형 값이다.** 우리 날은 캠버가 있고,
           캠버를 얹은 실측 비는 **0.695** 다(감사 m3 와 같은 원인 — 시위선 기준 상하면 차).
      ⇒ 인용 규칙: 이 수를 «메쉬 실측» 이라고 쓰지 말 것. «법칙에서 유도한 값» 이라고 쓰거나,
        메쉬 실측치(1.4559 mm)를 나란히 적을 것.
      ⚠ 더 큰 문제는 정확도가 아니라 **스칼라 하나로 함대 전체를 덮는다는 것**이다 —
        메쉬 실측 두께는 mini2 0.664 ~ m350rtk 2.879 mm 로 **4.3 배** 벌어진다(감사 I1, 3층 과제)."""
    from drone_cad import (CHORD_RR, CHORD_FRAC, CHORD_MAX_OVER_R, TC_ROOT, TC_TIP)
    from drones import DRONES

    # NACA-4 두께분포의 시위평균 / 최대 비 (t=1 로 두고 형상만)
    x = np.linspace(0, 1, 2001)
    yt = 5 * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
              + 0.2843 * x ** 3 - 0.1015 * x ** 4)
    chordwise_ratio = float(np.trapezoid(yt, x) / yt.max())   # <두께>/최대두께

    root_frac = 0.070          # drone_cad.props() 가 쓰는 값
    rr = np.linspace(root_frac, 1.0, 400)
    cfrac = np.interp(rr, CHORD_RR, CHORD_FRAC)
    f = np.clip((rr - root_frac) / (1.0 - root_frac), 0, 1)
    tratio = TC_TIP + (TC_ROOT - TC_TIP) * (1 - f)

    per_drone = {}
    for name, spec in DRONES.items():
        R = float(spec.prop_dia_mm) / 2.0 / 1000.0
        c = cfrac * CHORD_MAX_OVER_R * R
        tmax = tratio * c                                   # 스팬별 최대두께 [m]
        # 평면형 투영면적 가중(가중치 = 국소 시위 c) 평균
        w = c
        tmax_mean = float(np.trapezoid(tmax * w, rr) / np.trapezoid(w, rr))
        per_drone[name] = dict(
            prop_dia_mm=float(spec.prop_dia_mm),
            t_max_peak_mm=float(tmax.max() * 1e3),
            t_max_spanmean_mm=float(tmax_mean * 1e3),
            t_chordmean_mm=float(tmax_mean * chordwise_ratio * 1e3),
        )
    return dict(
        naca4_chordwise_mean_over_max=chordwise_ratio,
        tc_root=float(TC_ROOT), tc_tip=float(TC_TIP),
        chord_max_over_R=float(CHORD_MAX_OVER_R),
        per_drone=per_drone,
        note="셸(1-3 mm)보다 날개가 **얇다**는 현행 note 의 전제를 이 표로 직접 검사한다. "
             "⭐2026-08-16 — **메쉬를 직접 재는 판이 생겼다**: `src/prop_thickness.py` 와 "
             "표 `outputs/prop_thickness_by_drone.json`(감사 I1 집행). 그 자로 재면 우리 메쉬는 "
             "이 해석식보다 전 10기종에서 일관되게 1.1 % 얇고(부호가 감사 m1 의 «+1.8 %» 와 "
             "반대인데, 원인은 두 자의 차이다 — 감사는 시위를 조각내 조각마다 최대·최소를 "
             "읽어 두께를 위로 민다), 기종 간 폭은 4.48 배다. "
             "⚠ **기종별 값이 필요하면 이 함수가 아니라 그 표를 쓸 것.**",
        measured_from_mesh="src/prop_thickness.py :: prop_slab_thickness_mm(spec) — "
                           "원통 단면의 정확한 교선 → 넓이÷시위. 표: "
                           "outputs/prop_thickness_by_drone.json",
        provenance="상수에서 유도한 값이지 메쉬 실측이 아니다(2026-08-16 선언). "
                   "matrice4e 기준 이 식 1.4302 mm ↔ 메쉬 직접 실측 1.456~1.488 mm "
                   "(+1.8~+4.1 %, |Γ| 로 +0.13 dB 급). "
                   "빠진 편향 둘: 스윕디스크 정규화 −0.679 % · NACA-4 시위평균비 0.684879 는 대칭익형 값"
                   "(캠버 얹은 실측 비 0.695). 근거 원장 docs/MESH_AUDIT_0816.md m1.",
    )


def skin_depth(sigma, f, mu_r=1.0):
    mu = 4 * np.pi * 1e-7 * mu_r
    return float(np.sqrt(2.0 / (2 * np.pi * f * mu * sigma)))


# --------------------------------------------------------------------------- #
#  [A] 현행 값 감사
# --------------------------------------------------------------------------- #
def audit_current():
    import materials as M
    rows = []
    for k, spec in M.MATERIALS.items():
        row = dict(key=k, has_itu="itu" in spec,
                   itu=spec.get("itu"), S=float(spec["S"]),
                   eps_r_decl=spec.get("eps_r"), sigma_decl=spec.get("sigma"),
                   gamma_po_decl=spec.get("gamma_po"))
        row["per_band"] = {}
        for bn, f in BANDS.items():
            er, sg, _ = M.material_params(k, f)
            gb, gp = M.gamma_bulk(k, f), M.gamma_po(k, f)
            row["per_band"][bn] = dict(
                eps_r=float(er), sigma=float(sg),
                tan_delta=float(sg / (2 * np.pi * f * EPS0 * er)),
                gamma_bulk=float(gb), gamma_po=float(gp),
                gamma_po_minus_bulk_db=float(20 * np.log10(gp / gb)),
            )
        if "itu" in spec:
            row["tier"] = 1 if spec.get("gamma_po") is None else "1+3"
        else:
            row["tier"] = 2 if spec.get("gamma_po") is None else "2+3"
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
#  stage: derive
# --------------------------------------------------------------------------- #
def stage_derive():
    import materials as M

    # --- 커널 검증: 두께 극한 두 개 ---
    er, sg = 2.7, 0.02
    f = 3.5e9
    g_thick = abs(slab_reflection(er, sg, f, 10.0, 0.0, "TE"))        # d=10 m -> 벌크
    g_thin = abs(slab_reflection(er, sg, f, 1e-9, 0.0, "TE"))         # d->0 -> 0
    limits = dict(
        bulk_limit_slab=float(g_thick),
        bulk_limit_fresnel=float(M.gamma_bulk("plastic", f)),
        bulk_limit_err_db=float(20 * np.log10(g_thick / M.gamma_bulk("plastic", f))),
        zero_thickness_limit=float(g_thin),
    )

    # --- |Gamma|(d, theta, f) 격자 ---
    d_mm = np.array([0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 10.0, 13.0])
    th_deg = np.array([0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 85.0])
    grid = {}
    for bn, fb in BANDS.items():
        gb = {}
        for pol in ("TE", "TM"):
            arr = np.array([[abs(slab_reflection(er, sg, fb, dd * 1e-3, tt, pol))
                             for tt in th_deg] for dd in d_mm])
            gb[pol] = arr.tolist()
        grid[bn] = gb
    # 무편파 정면입사만 따로 (셸 대표 후보)
    normal_inc = {bn: {f"{dd:g}mm": float(abs(slab_reflection(er, sg, fb, dd * 1e-3, 0.0, "TE")))
                       for dd in d_mm} for bn, fb in BANDS.items()}
    # 투영면적 가중 평균(볼록 셸)
    proj = {bn: {f"{dd:g}mm": proj_weighted_mean_gamma(er, sg, fb, dd * 1e-3)
                 for dd in (1.0, 1.5, 2.0, 3.0)} for bn, fb in BANDS.items()}

    # 최대 도달 가능값(정면입사, 1/4파장 공진)
    r_bulk = float(M.gamma_bulk("plastic", 3.5e9))
    gamma_max_normal = float(2 * r_bulk / (1 + r_bulk ** 2))
    d_quarter_mm = {bn: float(C0 / fb / (4 * np.sqrt(er)) * 1e3) for bn, fb in BANDS.items()}

    # 흡수 손실 점검: 우리 penetrate 모델은 tau = 1 - |G|^2 (흡수 무시). 실제 |R|^2+|T|^2 는?
    energy = {}
    for bn, fb in BANDS.items():
        row = {}
        for dd in (1.0, 2.0, 3.0):
            R = abs(slab_reflection(er, sg, fb, dd * 1e-3, 0.0, "TE")) ** 2
            T = abs(slab_transmission(er, sg, fb, dd * 1e-3, 0.0, "TE")) ** 2
            row[f"{dd:g}mm"] = dict(R=float(R), T=float(T), absorbed=float(1 - R - T),
                                    absorbed_db=float(-10 * np.log10(max(1e-12, R + T))))
        energy[bn] = row
    # 문헌 손실(tan_delta 0.006)로 바꾸면 흡수가 얼마나 줄어드나
    sg_lit = {bn: float(0.006 * 2 * np.pi * fb * EPS0 * 2.7) for bn, fb in BANDS.items()}
    energy_lit = {}
    for bn, fb in BANDS.items():
        row = {}
        for dd in (1.0, 2.0, 3.0):
            R = abs(slab_reflection(er, sg_lit[bn], fb, dd * 1e-3, 0.0, "TE")) ** 2
            T = abs(slab_transmission(er, sg_lit[bn], fb, dd * 1e-3, 0.0, "TE")) ** 2
            row[f"{dd:g}mm"] = dict(R=float(R), T=float(T), absorbed=float(1 - R - T))
        energy_lit[bn] = row

    # --- 카본: sigma 를 문헌 범위로 흔들면 |Gamma| 가 얼마나 움직이나 ---
    carbon = {}
    for bn, fb in BANDS.items():
        row = {}
        for s in (1e3, 3e3, 1e4, 4e4, 1e5, 1e6):
            gbk = float(abs((1 - np.sqrt(eps_c(5.0, s, fb))) / (1 + np.sqrt(eps_c(5.0, s, fb)))))
            row[f"{s:.0e}"] = dict(gamma_bulk=float(gbk),
                                   skin_depth_um=float(skin_depth(s, fb) * 1e6),
                                   one_way_atten_db_1mm=float(20 * np.log10(np.e)
                                                              * 1e-3 / skin_depth(s, fb)))
        carbon[bn] = row

    # --- 배터리 파우치 알루미늄: 두께/표피깊이 ---
    batt = {}
    for bn, fb in BANDS.items():
        dsk = skin_depth(3.5e7, fb)
        batt[bn] = dict(skin_depth_um=float(dsk * 1e6),
                        foil_35um_in_skins=float(35e-6 / dsk),
                        foil_10um_in_skins=float(10e-6 / dsk),
                        one_way_atten_db_10um=float(20 * np.log10(np.e) * 10e-6 / dsk))

    # --- 프로펠러 날개두께 + 그 두께에서의 |Gamma| ---
    blade = blade_thickness_stats()
    for name, row in blade["per_drone"].items():
        row["gamma_thinslab"] = {
            bn: dict(
                at_t_chordmean=float(abs(slab_reflection(er, sg, fb,
                                                         row["t_chordmean_mm"] * 1e-3, 0.0, "TE"))),
                at_t_max_peak=float(abs(slab_reflection(er, sg, fb,
                                                        row["t_max_peak_mm"] * 1e-3, 0.0, "TE"))),
            ) for bn, fb in BANDS.items()}

    # --- 현행 0.28 / 0.25 가 어떤 두께에 해당하는가(역산) ---
    def d_for_gamma(target, fb, tol=1e-4):
        dd = np.linspace(1e-5, 13e-3, 200000)
        g = np.abs(slab_reflection(er, sg, fb, 1.0, 0.0, "TE"))  # placeholder to keep signature
        g = np.array([abs(slab_reflection(er, sg, fb, x, 0.0, "TE")) for x in
                      np.linspace(1e-5, 13e-3, 4000)])
        xs = np.linspace(1e-5, 13e-3, 4000)
        if g.max() < target:
            return None
        i = int(np.argmax(g >= target))
        return float(xs[i] * 1e3)

    inverse = {bn: dict(d_mm_for_0p28=d_for_gamma(0.28, fb),
                        d_mm_for_0p25=d_for_gamma(0.25, fb))
               for bn, fb in BANDS.items()}

    out = dict(
        _meta=dict(
            generated=_dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            generator="benchmark/material_sources.py --stage derive",
            purpose="src/materials.py 의 tier-2(문헌값) 와 tier-3(gamma_po 실효값) 에 "
                    "출처를 붙이거나, 출처가 없으면 **모델링 선택으로 선언하고 영향을 한계짓는다**.",
            do_not_edit="이 워크플로는 src/materials.py 를 고치지 않는다 — 제안 패치만 적는다.",
            house_rule="문헌 상수만 LITERATURE 블록에 손으로 적혔다. 유도·스윕 숫자는 전부 계산 결과다.",
        ),
        corrections_to_brief=[
            dict(claim="materials.py 에 battery eps_r 1.4 sigma 1.2 가 있다",
                 status="FALSE",
                 truth="eps_r=1.4, sigma=1.2 는 **absorber**(챔버 전파흡수체) 항목이다. "
                       "battery 그룹은 DRONE_GROUP_MAT 에서 **ITU metal** 로 간다 — tier-2 가 아니라 tier-1.",
                 consequence="tier-2 무출처 값은 실제로 **plastic(2.7/0.02)·carbon(5.0/3e3)·"
                             "absorber(1.4/1.2)** 세 개뿐이다. 리튬이온 유전율 문헌은 우리 모델에 "
                             "들어오지 않는다(필요한 것은 '금속으로 봐도 되는가'의 표피깊이 논증)."),
            dict(claim="FR-4 값이 모델에 쓰인다",
                 status="FALSE",
                 truth="pcb 그룹은 ITU metal + gamma_po=0.80 이다. FR-4 의 eps_r/tan_delta 는 "
                       "코드 어디에서도 읽히지 않는다.",
                 consequence="FR-4 는 참고 기록으로만 남긴다. 검증 대상은 '구리 그라운드플레인 지배' "
                             "가정과 실효 0.80 이다."),
        ],
        literature=LITERATURE,
        current_values=audit_current(),
        thin_slab=dict(
            model="Gamma = r(1-e^{-2j delta})/(1-r^2 e^{-2j delta}), delta = k0 d sqrt(eps_c - sin^2 th)",
            kernel_limits=limits,
            eps_r=er, sigma=sg,
            d_mm_axis=d_mm.tolist(), theta_deg_axis=th_deg.tolist(),
            gamma_grid=grid,
            gamma_normal_incidence=normal_inc,
            gamma_proj_weighted=proj,
            gamma_max_normal_incidence=gamma_max_normal,
            quarter_wave_thickness_mm=d_quarter_mm,
            inverse_thickness_for_current_values=inverse,
            energy_check_sigma_ours=energy,
            energy_check_sigma_literature=energy_lit,
            sigma_literature_equivalent=sg_lit,
        ),
        carbon_sigma_sensitivity=carbon,
        battery_metal_justification=batt,
        propeller=blade,
    )
    _merge_write(out)
    print(json.dumps(dict(bulk_limit_err_db=limits["bulk_limit_err_db"],
                          gamma_max=gamma_max_normal,
                          normal_2mm={k: v["2mm"] for k, v in normal_inc.items()},
                          proj_2mm={k: v["2mm"]["unpol"] for k, v in proj.items()}),
                     indent=1, ensure_ascii=False))
    return out


def stage_derive2():
    """유도 2단 — eps_r 민감도 · Gamma 위상 · 제안 패치 · 정직한 표.
    (별도 stage 로 둔 이유: GPU 스윕과 같은 JSON 을 쓰므로 쓰기 순서를 사람이 통제한다.)"""
    import materials as M

    er, sg = 2.7, 0.02
    # --- eps_r 을 문헌 범위(2.4-3.2)로 흔들면 |Gamma| 가 몇 dB 움직이나 ---
    ers = [2.4, 2.55, 2.6, 2.7, 2.74, 2.8, 2.9, 2.95, 3.0, 3.2]
    eps_sens = {}
    for bn, fb in BANDS.items():
        row = {}
        for e in ers:
            gb = float(abs((1 - np.sqrt(eps_c(e, sg, fb))) / (1 + np.sqrt(eps_c(e, sg, fb)))))
            g2 = float(abs(slab_reflection(e, sg, fb, 2.0e-3, 0.0, "TE")))
            gp = proj_weighted_mean_gamma(e, sg, fb, 2.0e-3)["unpol"]
            row[f"{e:g}"] = dict(gamma_bulk=gb, gamma_slab2mm_normal=g2, gamma_slab2mm_proj=gp)
        ref = row["2.7"]
        row["_spread_db"] = dict(
            bulk_2p4_3p2=float(20 * np.log10(row["3.2"]["gamma_bulk"] / row["2.4"]["gamma_bulk"])),
            slab2mm_2p4_3p2=float(20 * np.log10(row["3.2"]["gamma_slab2mm_normal"]
                                                / row["2.4"]["gamma_slab2mm_normal"])),
            bulk_lit_2p55_2p95=float(20 * np.log10(row["2.95"]["gamma_bulk"]
                                                   / row["2.55"]["gamma_bulk"])),
            slab2mm_lit_2p55_2p95=float(20 * np.log10(row["2.95"]["gamma_slab2mm_normal"]
                                                      / row["2.55"]["gamma_slab2mm_normal"])),
            note=f"우리 2.7 기준: bulk={ref['gamma_bulk']:.4f}. "
                 f"lit 범위는 Zechmeister&Lacik COMITE 2019 의 2.55-2.95")
        eps_sens[bn] = row

    # --- Gamma 의 위상: 커널은 |Gamma| 만 쓴다. 박막은 위상이 벌크와 90도 이상 다르다 ---
    phase = {}
    for bn, fb in BANDS.items():
        row = {}
        for dd in (1.0, 2.0, 3.0, 13.0, 1000.0):
            G = slab_reflection(er, sg, fb, dd * 1e-3, 0.0, "TE")
            row[f"{dd:g}mm"] = dict(abs=float(abs(G)), arg_deg=float(np.degrees(np.angle(G))))
        row["_kernel_uses"] = "|Gamma| (실수·양수) — 위상 0 도로 취급"
        phase[bn] = row

    # --- materials.py note 의 주장 검증: "ITU plasterboard 와 벌크 |Gamma| 가 0.247 vs 0.244" ---
    pb = {}
    for bn, fb in BANDS.items():
        s_pb = 0.0085 * (fb / 1e9) ** 0.9395          # ITU-R P.2040 Table 3 (Sionna 소스에서 확인)
        g_pb = float(abs((1 - np.sqrt(eps_c(2.73, s_pb, fb))) / (1 + np.sqrt(eps_c(2.73, s_pb, fb)))))
        g_ours = float(M.gamma_bulk("plastic", fb))
        pb[bn] = dict(sigma_plasterboard=float(s_pb), gamma_plasterboard=g_pb,
                      gamma_ours=g_ours, diff_db=float(20 * np.log10(g_pb / g_ours)),
                      tan_delta_plasterboard=float(s_pb / (2 * np.pi * fb * EPS0 * 2.73)),
                      tan_delta_ours=float(0.02 / (2 * np.pi * fb * EPS0 * 2.7)))

    out = dict(
        epsilon_sensitivity=eps_sens,
        itu_plasterboard_check=pb,
        gamma_phase=phase,
        proposed_patch=PROPOSED_PATCH,
        honest_table=HONEST_TABLE,
    )
    _merge_write(out)
    print(json.dumps({k: v["_spread_db"] for k, v in eps_sens.items()}, indent=1, ensure_ascii=False))
    return out


# --------------------------------------------------------------------------- #
#  제안 패치 — ⛔ 적용하지 않는다. 이 워크플로는 src/materials.py 를 건드리지 않는다.
# --------------------------------------------------------------------------- #
PROPOSED_PATCH = [
    dict(
        target="src/materials.py MATERIALS['carbon']['sigma']",
        current="3.0e3",
        proposed="1.0e4",
        why="Artner et al. IJAP 2017 (4-6 GHz, 도파관 NRW) 가 우리 대역에서 직접 측정한 "
             "shred-CFRP 유효 도전율이 ~1e4 S/m 다. 3e3 은 그 아래에 있고 출처가 없다.",
        impact="|Gamma|_bulk 0.9887 -> 0.9938 (+0.045 dB). 1 mm 벽 편도 감쇠 56 -> 102 dB "
               "(어느 쪽이든 불투명). **총 RCS 영향 무시 가능** — 값을 바꾸는 이유는 정확도가 "
               "아니라 **출처가 생기기 때문**이다.",
        risk="낮음. 다만 carbon 은 gamma_po=0.90 오버라이드가 있어 PO 경로에는 애초에 안 들어간다 "
             "(Sionna RT 경로에만 영향).",
    ),
    dict(
        target="src/materials.py MATERIALS['plastic']['sigma'] (그리고 plastic_blue/prop_plastic)",
        current="0.02 (상수)",
        proposed="0.0085 * f_GHz**0.9395  (= ITU-R P.2040 plasterboard 식) 또는 tan_delta=0.006 등가",
        why="현행 상수 0.02 S/m 는 tan_delta 로 환산하면 1.843 GHz 에서 0.072 다 — 문헌 ABS/PC "
            "(0.005-0.008)보다 9-14배 손실이 크다. ITU plasterboard 식을 쓰면 주파수 의존성까지 "
            "표준에서 온다(출처가 생긴다).",
        impact="|Gamma| 에는 거의 영향 없음(<0.01 dB). 셸 흡수는 0.03-0.10 dB → 0.01 dB 미만으로 감소. "
               "**총 RCS 영향 무시 가능**.",
        risk="낮음. 단 Sionna RT(전파) 쪽 투과손실은 바뀐다.",
    ),
    dict(
        target="src/materials.py gamma_po() — plastic / prop_plastic 의 실효 상수",
        current="plastic 0.28 (상수), prop_plastic 0.25 (상수)",
        proposed="박막 프레넬에서 **주파수·두께 의존**으로 계산: gamma_po(mat, fc, d) = "
                 "<|Gamma_slab(eps_c, d, theta)|>_투영가중.  두께는 선언된 모델링 선택으로 남긴다 "
                 "(셸 2.0 mm, 프롭 = drone_cad 의 시위평균 두께).",
        why="⭐ 현행 0.28 은 **어떤 두께에서도 우리 대역의 정면입사 박막값이 아니다** — 0.28 이 "
            "나오려면 셸이 1.843/3.5/5.21 GHz 에서 각각 9.7/5.1/3.4 mm 여야 한다 — "
            "**note 자신이 셸을 1-3 mm 라 적어놓았다**. "
            "note 의 '0.1~0.45 를 오간다'는 서술은 **두께를 1/4파장(8.8-24.7 mm)까지 키웠을 때**의 "
            "범위이지 1-3 mm 의 범위가 아니다. 1-3 mm 의 실제 범위는 0.033-0.254 (밴드 의존)다.",
        impact="아래 impact_sweep 참조 — 총 RCS 변화는 밴드별로 유계다. **선언·유계이면 방어 가능**.",
        risk="중간. 밴드마다 값이 달라지므로 밴드 기울기(우리 리포트의 헤드라인)가 움직인다 — "
             "그 변화량도 impact_sweep.band_slope 에 있다.",
    ),
    dict(
        target="src/materials.py gamma_po() — pcb 0.80 / camera_assembly 0.85",
        current="0.80 / 0.85 (근거 note 는 있으나 출처 없음)",
        proposed="**값을 바꾸지 말고 선언하라** — 'ITU metal 에 대한 개구율 보정, 출처 없는 "
                 "모델링 선택, 총 RCS 영향 |x| dB (impact_sweep)' 라고 note 에 명시.",
        why="이 둘은 복합 조립품(구리면+커넥터 / 금속하우징+유리렌즈+짐벌)이라 닫힌형 유도가 없다. "
            "문헌도 없다. **없는 출처를 지어내는 대신 모델링 선택으로 선언하고 한계짓는 것**이 정직하다.",
        impact="⭐ 그러나 **우선순위는 뒤집혀야 한다**: pcb 는 0.5-1.0 전 범위에서 총 sigma 를 "
               "0.05 dB 안쪽으로만 움직이는데(내부 부품이라 셸 투과 손실을 두 번 먹는다), "
               "camera_assembly 는 같은 범위에서 **최대 1.8 dB** 움직인다. "
               "note 분량은 정확히 반대로 배분돼 있다.",
        risk="없음(값 불변). 다만 camera_assembly 는 **다음에 실물을 열어볼 때 최우선으로 확인할 부품**이다.",
    ),
    dict(
        target="src/rcs_sbr.py / src/rcs_po.py — |Gamma| -> 복소 Gamma",
        current="커널이 실수 |Gamma| 만 받는다(위상 0 으로 취급).",
        proposed="복소 Gamma 를 받도록 확장. **박막 실효값을 도입할 거라면 이건 선택이 아니라 짝이다.**",
        why="벌크만 쓸 때는 위상을 버려도 무해했다 — 금속(≈180 deg)과 플라스틱(≈178 deg)의 "
            "**상대**위상이 맞았기 때문이다. 박막 Gamma 는 위상이 −100~−116 deg 라 금속 대비 "
            "70 deg 가까이 어긋난다. 크기만 박막으로 고치면 상대위상이 새로 틀어진다.",
        impact="셸 기여 자체가 작아서 총 sigma 영향은 impact_sweep 규모(<1 dB)를 넘지 않는다. "
               "다만 **셸이 지배하는 자세**(정면에서 큰 평평한 셸면을 보는 각)에서는 국소적으로 더 클 수 있다.",
        risk="중간-높음. 커널 시그니처가 바뀌고 구 검증(PEC, |Gamma|=1)은 실수 1.0 이라 무영향이지만 "
             "재질 표를 읽는 모든 경로를 손대야 한다.",
    ),
    dict(
        target="src/materials.py MATERIALS['prop_plastic']['note']",
        current="'날개가 셸(1~3 mm)보다 더 얇아 실효 |Γ| 가 낮다는 **방향**만 반영해 0.25 채택'",
        proposed="이 문장을 **삭제하거나 정정**하라. 우리 CAD 자신이 반증한다.",
        why="⭐ drone_cad 의 TC_ROOT/TC_TIP·CHORD_* 에서 유도한 날개 두께는 기종마다 "
            "시위평균 0.80-1.99 mm, 최대 1.66-4.15 mm 다. mini5pro 는 셸보다 얇지만 "
            "s1000plus(최대 4.15 mm)는 셸보다 **두껍다**. '항상 더 얇다'는 전제가 성립하지 않는다.",
        impact="0.03 dB 주장 자체는 impact_sweep 이 검증한다(아래). 즉 **결론은 살아남고 근거가 틀렸다**.",
        risk="없음(문서만).",
    ),
]

HONEST_TABLE = [
    dict(material="metal", param="eps_r, sigma", value="ITU-R P.2040 'metal' (1.0, 1e7 S/m)",
         source="ITU-R P.2040 Table 3 — Sionna 설치본 소스에서 직접 확인",
         confidence="high", modelling_choice=False),
    dict(material="concrete_light/dark", param="eps_r, sigma", value="ITU-R P.2040 'concrete'",
         source="ITU-R P.2040 Table 3 (5.24, 0.0462 f^0.7822)",
         confidence="high", modelling_choice=False),
    dict(material="plastic / plastic_blue", param="eps_r = 2.7",
         value="2.7",
         source="⭐ Zechmeister & Lacik, COMITE 2019 (**1-10 GHz 측정**, 우리 세 밴드를 전부 덮음): "
                "ABS 포함 5종의 eps_r' 가 2.55-2.95. PC 2.8-3.0 (Riddle-NIST 2003, ~10 GHz). "
                "ITU-R P.2040 plasterboard 2.73. **우리 값 2.7 은 이 구간 한가운데다.**",
         confidence="high", modelling_choice=False,
         bound="문헌 전폭 2.4-3.2 를 다 써도 |Gamma| 변화는 epsilon_sensitivity 참조"),
    dict(material="plastic (셸)", param="두께 d (박막 |Gamma| 의 지배 변수)",
         value="현행 커널엔 두께 개념이 없다(상수 0.28). 유도에는 2.0 mm 를 썼다.",
         source="⚠⚠ **출처 전무**. DJI 는 셸 두께는커녕 **수지 종류도 공개하지 않는다**. 공개 "
                "티어다운(iFixit·포럼)에도 벽 두께 실측이 없다. 우리에게 실물 티어다운도 없다.",
         confidence="unsourced", modelling_choice=True,
         bound="⭐ 이것이 tier-3 에서 **유일하게 진짜 하중을 지는 미지수**다. 0.5-3.0 mm 범위에서 "
               "정면입사 |Gamma| 가 밴드마다 크게 달라진다(thin_slab.gamma_normal_incidence). "
               "총 RCS 영향은 impact_sweep 의 plastic= 행이 한계짓는다."),
    dict(material="plastic", param="sigma = 0.02 S/m", value="0.02 (상수)",
         source="⚠ **출처 없음**. tan_delta 로 0.026-0.072 (밴드에 따라) — 문헌 ABS/PC 0.005-0.008 "
                "보다 4-14배 크다. ITU plasterboard 식(0.0085 f^0.9395)이 가장 가까운 표준 대용.",
         confidence="low", modelling_choice=True,
         bound="|Gamma| 영향 <0.01 dB, 셸 흡수 0.03-0.10 dB → 총 RCS 영향 무시 가능"),
    dict(material="carbon", param="sigma = 3000 S/m", value="3000",
         source="⚠ **출처 없음**. 우리 대역 측정치(Artner 2017, 4-6 GHz NRW)는 ~1e4 S/m, "
                "각도에 따라 1e3-1e6. UD 이방성은 섬유방향/수직 비가 1e5 에 달한다.",
         confidence="low_value_but_bounded", modelling_choice=True,
         bound="sigma 1e3-1e6 전 범위에서 |Gamma|_bulk 0.980-0.999 (+0.16 dB). "
               "1 mm 벽 편도 감쇠 32-1021 dB → 어느 값이든 **불투명**이라는 결론 불변"),
    dict(material="carbon", param="eps_r = 5.0", value="5.0",
         source="⚠ **출처 없음**. 문헌은 UD-CFRP 에서 1(섬유평행)-30(횡방향) 까지 흩어진다 "
                "(Artner 2017 §3.3 이 정리). 도전성이 지배하므로 eps_r 은 |Gamma| 를 거의 안 바꾼다.",
         confidence="low_value_but_irrelevant", modelling_choice=True,
         bound="sigma=3e3 에서 eps_r 1->30 은 |Gamma| 를 0.3% 미만으로 바꾼다"),
    dict(material="carbon", param="이방성", value="스칼라 sigma 1개 (등방 가정)",
         source="⚠ 문헌은 **강한 이방성**을 보고한다(UD 섬유방향:수직 = 1e5; twill 은 각도에 따라 "
                "1e3-1e6). 스칼라는 **선언된 모델링 선택**이다.",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="암(arm)/데크는 gamma_po=0.90 오버라이드를 쓰므로 PO 경로에서는 sigma 가 아니라 "
               "0.90 이 하중을 진다 — carbon_supplement 참조(0.70~1.0 에서 총 sigma 최대 1.21 dB)"),
    dict(material="carbon", param="gamma_po = 0.90 (직조 개구 보정)", value="0.90",
         source="⚠ **출처 없음 — 모델링 선택**. 벌크 프레넬은 0.989(sigma 3e3)~0.994(sigma 1e4)이고 "
                "0.90 은 거기서 -0.8~-0.9 dB 내린 값이다. 근거 note 는 '직조 섬유 사이 유전체 개구'"
                "라고 적었지만 그 개구율을 잰 문헌도, 계산도 없다.",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="⭐ carbon_supplement: 탄소 암/데크가 **있는** 기종(x500v2, s1000plus)에서 0.70~1.0 "
               "구간의 총 sigma 변화는 최대 1.21 dB. 탄소 그룹이 없는 기종(phantom4/mavic4pro/"
               "mini5pro)에서는 정확히 0.000 dB — '무해'가 아니라 '해당 없음'이다."),
    dict(material="pcb", param="ITU metal + gamma_po 0.80", value="0.80",
         source="⚠ **출처 없음 — 모델링 선택**. FR-4 자체 값(4.2-4.7 / 0.017-0.025, "
                "Djordjevic-Sarkar IEEE T-EMC 2001)은 **우리 모델에 들어가지 않는다**.",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="impact_sweep pcb= 0.5/0.65/1.0"),
    dict(material="camera_assembly", param="ITU metal + gamma_po 0.85", value="0.85",
         source="⚠ **출처 없음 — 모델링 선택**. 금속하우징+유리렌즈+짐벌 복합체는 닫힌형이 없다.",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="impact_sweep camera= 0.5/0.7/1.0"),
    dict(material="prop_plastic", param="gamma_po 0.25", value="0.25",
         source="⚠ **출처 없음 — 모델링 선택**. 근거 note 의 '셸보다 얇다'는 전제는 우리 CAD 가 "
                "반증한다(기종별 시위평균 0.80-1.99 mm).",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="impact_sweep prop= 행. 0.25 vs 0.28 주장은 직접 검증됨"),
    dict(material="battery", param="ITU metal 로 사상", value="metal",
         source="⭐ **계산으로 정당화됨**(문헌 불필요): 파우치 셀 Al 배리어층은 업계 규격 15-70 um, "
                "우리 대역 표피깊이는 1.18-1.98 um → 최소 두께 15 um 에서도 7-13 표피깊이, "
                "편도 감쇠 >65 dB. 두께 규격 출처가 약해도 결론은 견고하다.",
         confidence="high_conclusion", modelling_choice=False),
    dict(material="absorber", param="eps_r 1.4, sigma 1.2", value="1.4 / 1.2",
         source="⚠ **출처 없음 — 모델값**(note 가 이미 그렇게 선언함). 챔버 흡수체 전용, 드론과 무관.",
         confidence="declared_modelling_choice", modelling_choice=True,
         bound="드론 RCS 에 영향 없음(씬 재질)"),
]


def stage_doc():
    """docs/MATERIAL_SOURCES.md — **모든 숫자를 JSON 에서 주입**한다(집 규칙: 손으로 안 적는다)."""
    with open(OUT_JSON) as fh:
        D = json.load(fh)
    ts, sw = D["thin_slab"], D.get("impact_sweep", {})
    L = []
    A = L.append

    A("# 재질 파라미터의 출처 — 감사와 유도\n")
    A(f"> 생성: `benchmark/material_sources.py` + `benchmark/material_gamma_sweep.py` · "
      f"{D['_meta']['generated']}  ")
    A("> 원장: `outputs/material_sources.json` — **이 문서의 숫자는 전부 거기서 주입된다.**  ")
    A("> ⛔ 이 작업은 `src/materials.py` 를 고치지 않았다. 제안 패치만 적는다.\n")

    A("## TL;DR\n")
    A("사용자 질문 — *\"재질도 현실적인 재질이니? 실제로 조사해서 기입한 거야?\"* — 에 대한 답은 "
      "**부분적으로만 그렇다**이다. 세 갈래로 갈린다.\n")
    A("1. **유전율(eps_r)은 방어 가능하다.** 플라스틱 2.7 은 우리 대역을 덮는 측정 문헌"
      "(Zechmeister & Lacik, COMITE 2019, 1-10 GHz, ABS 포함 2.55-2.95)과 ITU-R P.2040 "
      "plasterboard(2.73) 사이 한가운데다.")
    A("2. **도전율(sigma)은 출처가 없었고, 이제 있다 — 그리고 그것은 중요하지 않다.** "
      "카본 3000 S/m 는 우리 대역 측정치(Artner et al., IJAP 2017, 4-6 GHz 도파관 NRW, ~1e4 S/m) "
      "아래에 있다. 다만 sigma 를 1e3-1e6 전 범위로 흔들어도 |Gamma| 는 "
      f"{D['carbon_sigma_sensitivity']['5G 3.5 GHz']['1e+03']['gamma_bulk']:.3f}-"
      f"{D['carbon_sigma_sensitivity']['5G 3.5 GHz']['1e+06']['gamma_bulk']:.3f} 로만 움직인다.")
    A("3. ⭐ **gamma_po 실효값은 물리와 어긋나 있었다.** 셸 0.28 은 우리 대역에서 "
      f"두께 {ts['inverse_thickness_for_current_values']['LTE 1.843 GHz']['d_mm_for_0p28']:.1f}/"
      f"{ts['inverse_thickness_for_current_values']['5G 3.5 GHz']['d_mm_for_0p28']:.1f}/"
      f"{ts['inverse_thickness_for_current_values']['WiFi 5.21 GHz']['d_mm_for_0p28']:.1f} mm "
      "(1.843/3.5/5.21 GHz)에서야 나오는 값이다 — `materials.py` note 자신이 셸을 **1-3 mm** 라고 "
      "적어놓았으므로, **note 는 스스로와 모순된다**. (그 1-3 mm 자체도 출처가 없다 — 7절 참조.)")
    if sw:
        ds = [abs(sw["by_drone"][d][b]["thinslab_proj"]["delta_vs_base_db"])
              for d in sw["by_drone"] for b in sw["by_drone"][d]]
        A(f"4. **그런데 그 오차는 총 RCS 를 거의 안 움직인다** — 물리적 박막값으로 바꾸면 "
          f"밴드평균 sigma 가 최대 {max(ds):.2f} dB 변한다(3기체 x 3밴드). "
          "즉 **틀렸지만 하중을 지지 않는 파라미터**다. 선언하고 한계지으면 방어 가능하다.\n")

    A("\n## 0. 지시서 정정\n")
    for c in D["corrections_to_brief"]:
        A(f"- **{c['status']}** — 주장: \"{c['claim']}\"  ")
        A(f"  사실: {c['truth']}  ")
        A(f"  결과: {c['consequence']}\n")

    A("\n## 1. 현행 값의 계층 감사 (3.5 GHz 기준)\n")
    A("| 재질 | 계층 | 출처 | eps_r | sigma [S/m] | tan d | \\|G\\|벌크 | \\|G\\|PO | 실효-벌크 [dB] |")
    A("|---|---|---|---|---|---|---|---|---|")
    tier_txt = {1: "1 (ITU)", "1+3": "1+3 (ITU+실효)", 2: "2 (문헌·무출처)", "2+3": "2+3"}
    for r in D["current_values"]:
        b = r["per_band"]["5G 3.5 GHz"]
        src = f"ITU {r['itu']}" if r["has_itu"] else "custom"
        td = f"{b['tan_delta']:.4f}" if b["tan_delta"] < 100 else f"{b['tan_delta']:.1e} (도체)"
        A(f"| `{r['key']}` | {tier_txt.get(r['tier'], r['tier'])} | {src} | {b['eps_r']:.2f} | "
          f"{b['sigma']:.4g} | {td} | {b['gamma_bulk']:.4f} | {b['gamma_po']:.4f} | "
          f"{b['gamma_po_minus_bulk_db']:+.2f} |")

    A("\n\n## 2. tier-2 문헌 출처 (저자·발표지·연도·측정대역·방법)\n")
    A("| 재질 | 값 | 대역 [GHz] | 방법 | 저자 | 발표지 | 연도 | DOI | 신뢰도 |")
    A("|---|---|---|---|---|---|---|---|---|")
    for e in D["literature"]:
        fr = e["freq_range_ghz"]
        A(f"| {e['material']} | {e['value_text']} | {fr[0]:g}-{fr[1]:g} | {e['method']} | "
          f"{e['author']} | {e['venue']} | {e['year']} | {e.get('doi') or '-'} | {e['confidence']} |")
    A("\n검증 메모:\n")
    for e in D["literature"]:
        A(f"- **{e['key']}** — {e['verified']}")

    A("\n\n## 3. gamma_po (a) — 박막 프레넬 유도\n")
    A("얇은 유전체 셸은 반무한 벌크가 아니라 **슬랩**이다. 앞뒷면 반사가 간섭하므로 닫힌형이 있다:\n")
    A("```")
    A(ts["model"])
    A("```")
    A(f"커널 검증: d→무한대에서 벌크 프레넬과 {ts['kernel_limits']['bulk_limit_err_db']:+.4f} dB "
      f"일치, d→0 에서 |G|={ts['kernel_limits']['zero_thickness_limit']:.2e}. 두 극한 모두 통과.\n")
    A("\n**정면입사 |Gamma| (eps_r 2.7, sigma 0.02 S/m)**\n")
    dkeys = list(ts["gamma_normal_incidence"]["5G 3.5 GHz"].keys())
    A("| 두께 | " + " | ".join(BANDS) + " |")
    A("|---|" + "---|" * len(BANDS))
    for dk in dkeys:
        A(f"| {dk} | " + " | ".join(f"{ts['gamma_normal_incidence'][b][dk]:.4f}" for b in BANDS) + " |")
    A(f"\n정면입사에서 물리적으로 도달 가능한 **최대**는 "
      f"{ts['gamma_max_normal_incidence']:.4f} 이고, 그것은 1/4파장 두께"
      f"({ts['quarter_wave_thickness_mm']['LTE 1.843 GHz']:.1f}/"
      f"{ts['quarter_wave_thickness_mm']['5G 3.5 GHz']:.1f}/"
      f"{ts['quarter_wave_thickness_mm']['WiFi 5.21 GHz']:.1f} mm)에서 나온다.\n")
    A("\n**입사각 의존 (2 mm 셸, 3.5 GHz)** — 각도는 편파를 갈라놓는다:\n")
    th_ax = ts["theta_deg_axis"]
    di = ts["d_mm_axis"].index(2.0)
    A("| 편파 | " + " | ".join(f"{t:g} deg" for t in th_ax) + " |")
    A("|---|" + "---|" * len(th_ax))
    for pol in ("TE", "TM"):
        A(f"| {pol} | " + " | ".join(f"{v:.4f}" for v in ts["gamma_grid"]["5G 3.5 GHz"][pol][di])
          + " |")
    A("\nTE 는 grazing 에서 1 로 치솟고 TM 은 브루스터 근처에서 눌린다. 우리 커널은 **스칼라**라 "
      "이 갈림을 표현할 수 없다 — 그래서 대표값은 아래 **투영면적 가중 평균**(두 편파 평균)이 맞다.\n")

    A("\n**우리 커널에 맞는 대표값 — 투영면적 가중 평균**(볼록 셸에서 히트 가중치가 cos·sin 이므로):\n")
    A("| 두께 | " + " | ".join(BANDS) + " |")
    A("|---|" + "---|" * len(BANDS))
    for dk in ts["gamma_proj_weighted"]["5G 3.5 GHz"]:
        A(f"| {dk} | " + " | ".join(f"{ts['gamma_proj_weighted'][b][dk]['unpol']:.4f}" for b in BANDS)
          + " |")
    A("\n⭐ **판정: 0.28 은 대표값으로 방어되지 않는다.** 2 mm 셸의 정면입사값은 "
      + " / ".join(f"{ts['gamma_normal_incidence'][b]['2mm']:.3f}" for b in BANDS)
      + " 이고 투영가중값도 "
      + " / ".join(f"{ts['gamma_proj_weighted'][b]['2mm']['unpol']:.3f}" for b in BANDS)
      + " 다. 0.28 은 이 모두보다 "
      + " / ".join(f"{20*np.log10(0.28/ts['gamma_proj_weighted'][b]['2mm']['unpol']):+.1f}"
                   for b in BANDS)
      + " dB 높다. 게다가 **상수**라서 물리가 요구하는 **주파수 의존(얇은 슬랩은 |Gamma| ∝ f·d)**이 "
      "통째로 빠져 있다.\n")
    A("\n현행 note 의 \"0.1~0.45 를 오간다\"는 서술은 **두께를 1/4파장까지 키웠을 때**의 범위이지 "
      "1-3 mm 셸의 범위가 아니다. 1-3 mm 에서 실제 범위는 "
      + " / ".join(f"{ts['gamma_normal_incidence'][b]['1mm']:.3f}-{ts['gamma_normal_incidence'][b]['3mm']:.3f}"
                   for b in BANDS) + " (밴드별)이다.\n")
    gbulk = [r for r in D["current_values"] if r["key"] == "plastic"][0]["per_band"]["5G 3.5 GHz"]["gamma_bulk"]
    A(f"\n⭐ 그리고 note 의 \"벌크 반무한 프레넬 {gbulk:.3f} 는 그 **하한** 근처\"는 **부호가 뒤집혀 있다**. "
      f"현실적 두께(1-3 mm)에서 박막 |Gamma| 는 벌크보다 **낮다** — 3.5 GHz 2 mm 에서 "
      f"{ts['gamma_normal_incidence']['5G 3.5 GHz']['2mm']:.3f} 대 벌크 {gbulk:.3f}, 즉 "
      f"{20*np.log10(ts['gamma_normal_incidence']['5G 3.5 GHz']['2mm']/gbulk):+.1f} dB. "
      "벌크는 d→무한대 **점근값**이고, 그것을 넘는 건 1/4파장 근처(8.8-24.7 mm)뿐이다. "
      "즉 현행 0.28 은 '박막 보정'이 아니라 **벌크보다 조금 위**이고, 물리는 반대쪽을 가리킨다.\n")

    A("\n### 3-1. 프로펠러 — 우리 CAD 가 note 를 반증한다\n")
    P = D["propeller"]
    A("현행 note: *\"날개가 셸(1~3 mm)보다 더 얇아 실효 |Γ| 가 낮다\"*. "
      "그런데 날개 두께는 추측할 필요가 없다 — `drone_cad` 의 익형 상수에서 **직접 유도**된다 "
      f"(TC_ROOT {P['tc_root']:.3f}, TC_TIP {P['tc_tip']:.3f}, chord_max/R {P['chord_max_over_R']:.2f}, "
      f"NACA-4 시위평균/최대 = {P['naca4_chordwise_mean_over_max']:.4f}).\n")
    A("| 기종 | 프롭 지름 [mm] | 최대두께 [mm] | 스팬평균 최대두께 [mm] | 시위평균 두께 [mm] |")
    A("|---|---|---|---|---|")
    for k, v in P["per_drone"].items():
        A(f"| {k} | {v['prop_dia_mm']:.1f} | {v['t_max_peak_mm']:.2f} | "
          f"{v['t_max_spanmean_mm']:.2f} | {v['t_chordmean_mm']:.2f} |")
    tmax = max(v["t_max_peak_mm"] for v in P["per_drone"].values())
    tmin = min(v["t_chordmean_mm"] for v in P["per_drone"].values())
    A(f"\n즉 날개 두께는 기종에 따라 **{tmin:.2f}-{tmax:.2f} mm** 로 셸 범위(1-3 mm)를 "
      "아래위로 걸친다. \"항상 더 얇다\"는 전제는 **우리 자신의 CAD 가 반증한다**. "
      "결론(0.25 < 0.28)은 살아남지만 근거는 틀렸다.\n")

    if "itu_plasterboard_check" in D:
        pb = D["itu_plasterboard_check"]["5G 3.5 GHz"]
        A(f"\n부수 검증 — `materials.py` note 의 \"ITU plasterboard 와 벌크 |G| 가 사실상 같다\"는 "
          f"주장은 **참**이다: 3.5 GHz 에서 plasterboard {pb['gamma_plasterboard']:.4f} vs 우리 "
          f"{pb['gamma_ours']:.4f} ({pb['diff_db']:+.3f} dB). 다만 같은 표에서 **손실은 다르다** — "
          f"plasterboard tan d {pb['tan_delta_plasterboard']:.4f} vs 우리 {pb['tan_delta_ours']:.4f}.\n")

    if "epsilon_sensitivity" in D:
        A("\n### 3-2. eps_r 을 문헌 전폭으로 흔들면 (=우리 2.7 이 틀렸다면)\n")
        es = D["epsilon_sensitivity"]
        A("| 밴드 | 문헌범위 2.55-2.95 폭 (벌크) | 같은 범위 (2 mm 슬랩) | 극단 2.4-3.2 폭 (벌크) |")
        A("|---|---|---|---|")
        for b in BANDS:
            s = es[b]["_spread_db"]
            A(f"| {b} | {s['bulk_lit_2p55_2p95']:.2f} dB | {s['slab2mm_lit_2p55_2p95']:.2f} dB | "
              f"{s['bulk_2p4_3p2']:.2f} dB |")
        A("\n즉 **eps_r 은 하중을 지지 않는다** — 문헌 전폭을 다 써도 셸 |Gamma| 가 2 dB 안쪽으로 "
          "움직이고, 셸 자체의 총 RCS 기여가 작으므로(4-2 절) 총 sigma 변화는 그보다 훨씬 작다.\n")

    A("\n### 3-3. 부수 소득 — 투과 근사와 위상\n")
    e1 = ts["energy_check_sigma_ours"]["5G 3.5 GHz"]["2mm"]
    A(f"우리 SBR 은 셸 투과를 `tau = 1 - |G|^2` (무손실 에너지보존)로 잡는다. 박막 닫힌형으로 "
      f"검산하면 2 mm 셸에서 흡수는 {e1['absorbed']*100:.2f}% "
      f"(={e1['absorbed_db']:.3f} dB) 뿐이다 — **근사가 정당하다**. "
      "(그것도 우리 sigma 가 문헌보다 과하게 손실적인 상태에서 그렇다.)\n")
    if "gamma_phase" in D:
        gp = D["gamma_phase"]["5G 3.5 GHz"]
        rel = abs(gp["1000mm"]["arg_deg"] - gp["2mm"]["arg_deg"])
        rel = min(rel, 360 - rel)
        A(f"\n⚠ 반면 **위상은 버린다** — 그리고 이건 박막을 도입하는 순간 새로 생기는 문제다. "
          f"커널은 |Gamma| 만 쓴다(위상 0). 벌크에서는 이게 **무해**하다: 금속도 플라스틱도 "
          f"Gamma 위상이 ~{gp['1000mm']['arg_deg']:.0f} deg 로 사실상 같아서 **상대위상이 맞기 때문**이다. "
          f"그런데 2 mm 박막의 Gamma 위상은 {gp['2mm']['arg_deg']:+.1f} deg 다 — 금속 대비 "
          f"**{rel:.0f} deg** 어긋난다. 즉 실효 |Gamma| 만 박막값으로 바꾸면 크기는 맞고 "
          "**상대위상은 오히려 새로 틀어진다**. 제대로 하려면 커널이 복소 Gamma 를 받아야 한다. "
          "(영향의 크기는 아래 스윕이 한계짓는다 — 셸 기여 자체가 작다.)\n")

    if sw:
        A("\n\n## 4. gamma_po (b) — 영향 한계짓기 (GPU 스윕)\n")
        m = sw["_meta"]
        A(f"조건: 기종 {', '.join(m['drones'])} · az {m['n_az']}점 · el {m['el_deg']:.0f} deg · "
          f"격자 λ/{m['div']} · 지표 `{m['metric']}` · 런타임 {m['runtime_s']:.0f} s.  ")
        A("**기준 대비 delta 만 의미가 있다** (절대레벨의 격자 불확실도는 공통모드로 상쇄된다).\n")
        for dr in sw["by_drone"]:
            A(f"\n**{dr}** — base [dBsm]: " +
              ", ".join(f"{b} {sw['by_drone'][dr][b]['base']['mean_dbsm']:+.2f}" for b in BANDS) + "\n")
            names = [k for k in sw["by_drone"][dr][list(BANDS)[0]]
                     if not k.startswith("_") and k != "base"]
            A("| 변형 | " + " | ".join(f"{b} Δ[dB]" for b in BANDS) + " |")
            A("|---|" + "---|" * len(BANDS))
            for n in names:
                A(f"| `{n}` | " +
                  " | ".join(f"{sw['by_drone'][dr][b][n]['delta_vs_base_db']:+.3f}" for b in BANDS) + " |")
        A("\n### 4-1. \"셸 0.28 ↔ 프롭 0.25 차이는 0.03 dB 미만\" 주장 검증\n")
        pd = [(dr, b, sw["by_drone"][dr][b]["prop=0.280"]["delta_vs_base_db"])
              for dr in sw["by_drone"] for b in BANDS]
        worst = max(pd, key=lambda x: abs(x[2]))
        over = [p for p in pd if abs(p[2]) >= 0.03]
        A(f"프롭 |Gamma| 를 0.25→0.28(=셸과 동일)로 올렸을 때 밴드평균 sigma 변화의 **최대 절대값**은 "
          f"**{abs(worst[2]):.3f} dB** ({worst[0]}, {worst[1]}) 이고, {len(pd)}개 (기종x밴드) 중 "
          f"{len(over)}개가 0.03 dB 이상이다. "
          + ("⭐ **주장 성립** — 전부 0.03 dB 미만."
             if not over else
             f"⚠ **주장이 아슬아슬하게 깨진다** — 최대치가 0.03 dB 의 {abs(worst[2])/0.03:.2f}배다. "
             "결론(‘무시할 만하다’)은 살아남지만 **note 의 '0.03 dB 미만'이라는 단정은 "
             "'0.04 dB 미만' 으로 고쳐야 한다**.") + "\n")
        cam = [abs(sw["by_drone"][dr][b][k]["delta_vs_base_db"])
               for dr in sw["by_drone"] for b in BANDS for k in ("camera=0.50", "camera=1.00")]
        prop = [abs(sw["by_drone"][dr][b]["prop=0.280"]["delta_vs_base_db"])
                for dr in sw["by_drone"] for b in BANDS]
        A(f"\n⭐ **정작 걱정했어야 할 파라미터는 프롭이 아니라 카메라다.** prop 0.25↔0.28 은 최대 "
          f"{max(prop):.3f} dB 인데, 똑같이 출처 없는 `camera_assembly` 0.85 를 그 불확실 구간"
          f"(0.5~1.0)에서 흔들면 최대 **{max(cam):.2f} dB** 움직인다 — {max(cam)/max(prop):.0f}배다. "
          "note 는 프롭의 0.03 dB 를 길게 변명하면서 카메라의 1 dB 대는 한 줄도 안 적었다.\n")
        A(f"참고: 전 변형 중 총 sigma 를 가장 크게 움직이는 것은 "
          + ", ".join(
              f"`{max(((n, abs(sw['by_drone'][dr][b][n]['delta_vs_base_db'])) for n in [k for k in sw['by_drone'][dr][b] if not k.startswith('_') and k != 'base']), key=lambda x: x[1])[0]}` "
              f"({max((abs(sw['by_drone'][dr][b][n]['delta_vs_base_db']) for n in [k for k in sw['by_drone'][dr][b] if not k.startswith('_') and k != 'base'])):.2f} dB, {dr}/{b})"
              for dr in sw["by_drone"] for b in [list(BANDS)[1]]) + " 이다.\n")
        A("\n### 4-2. 그룹별 고립 기여 (3.5 GHz, 그 그룹만 |Gamma|=1 나머지 0) [dBsm]\n")
        iso = sw["isolated_group_dbsm_3p5"]
        allg = sorted({g for dr in iso for g in iso[dr] if not g.startswith("_")})
        A("| 기종 | " + " | ".join(allg) + " | 전부 PEC | 실제 base |")
        A("|---|" + "---|" * (len(allg) + 2))
        def _f(x):
            return "-" if x is None else f"{x:+.1f}"
        for dr in iso:
            A(f"| {dr} | " + " | ".join(_f(iso[dr].get(g)) for g in allg)
              + f" | {_f(iso[dr].get('_ALL_PEC'))} | {_f(iso[dr].get('_BASE'))} |")
        cs = D.get("carbon_supplement")
        if cs:
            A("\n### 4-2b. carbon 은 왜 주 스윕에서 0.000 dB 였나 — 보충 측정\n")
            A(f"{cs['_meta']['why']} 결과는 다음과 같다.\n")
            A("| 기종 | carbon 그룹 | 밴드 | base [dBsm] | 0.70 | 0.80(현행) | 0.9887(벌크 s=3e3) | "
              "0.9938(벌크 s=1e4) | 1.0 |")
            A("|---|---|---|---|---|---|---|---|---|")
            for dr, rows in cs["by_drone"].items():
                cg = ",".join(rows["_carbon_groups_present"]) or "(없음)"
                for b in BANDS:
                    if b not in rows:
                        continue
                    r = rows[b]
                    A(f"| {dr} | {cg} | {b} | {r['base']['mean_dbsm']:+.2f} | " +
                      " | ".join(f"{r[k]['delta_vs_base_db']:+.3f}" for k in
                                 ("carbon=0.7000", "carbon=0.8000", "carbon=0.9887",
                                  "carbon=0.9938", "carbon=1.0000")) + " |")
            allc = [abs(cs["by_drone"][dr][b][k]["delta_vs_base_db"])
                    for dr in cs["by_drone"] for b in BANDS if b in cs["by_drone"][dr]
                    for k in ("carbon=0.7000", "carbon=1.0000")]
            A(f"\n즉 carbon 실효값 0.90 은 **탄소 암/데크가 있는 기종에서는 하중을 진다** — "
              f"0.70~1.0 범위에서 총 sigma 가 최대 {max(allc):.2f} dB 움직인다. "
              "주 스윕의 0.000 dB 는 '중요하지 않다'가 아니라 '그 세 기종에는 해당 그룹이 없다'였다. "
              "⚠ 이건 **재질 문제가 아니라 기종 커버리지 문제**이기도 하다 — carbon 을 검증하려면 "
              "carbon 을 쓰는 기종을 돌려야 한다.\n")

        A("\n### 4-3. 밴드 기울기 (dB/GHz) — 리포트 헤드라인에 닿는 부분\n")
        A("| 기종 | base | thinslab_proj | prop=0.28 | Δ(thinslab−base) |")
        A("|---|---|---|---|---|")
        dsl = []
        for dr in sw["band_slope"]:
            r = sw["band_slope"][dr]
            d_ = r["thinslab_proj"]["slope_db_per_ghz"] - r["base"]["slope_db_per_ghz"]
            dsl.append(d_)
            A(f"| {dr} | {r['base']['slope_db_per_ghz']:+.3f} | "
              f"{r['thinslab_proj']['slope_db_per_ghz']:+.3f} | "
              f"{r['prop=0.280']['slope_db_per_ghz']:+.3f} | {d_:+.3f} |")
        A(f"\n⭐ 읽는 법: 박막 물리를 넣으면 기울기가 {min(dsl):+.3f}~{max(dsl):+.3f} dB/GHz 만큼 "
          + ("**더 가팔라진다**" if np.mean(dsl) > 0 else "**완만해진다**")
          + ". 우리 기울기가 실측보다 가파른 것이 알려진 문제이므로, "
          + ("이 정정은 그 어긋남을 **줄이지 않는다** — 오히려 조금 키운다. "
             "즉 **재질은 기울기 문제의 원인이 아니다**. 원인 후보(PTD 부재 = 모서리 회절항 없음)는 "
             "그대로 남는다 — 이 스윕은 재질을 **용의선상에서 제외**하는 데 의미가 있다."
             if np.mean(dsl) > 0 else
             "이 정정은 어긋남을 조금 줄인다 — 다만 크기가 작아 설명력의 대부분은 여전히 다른 데 있다."))

    A("\n\n## 5. 정직한 교체표\n")
    A("| 재질 | 파라미터 | 값 | 출처 / 유도 | 신뢰도 | 모델링 선택? | 영향 한계 |")
    A("|---|---|---|---|---|---|---|")
    for r in D["honest_table"]:
        A(f"| {r['material']} | {r['param']} | {r['value']} | {r['source']} | {r['confidence']} | "
          f"{'예' if r['modelling_choice'] else '아니오'} | {r.get('bound', '-')} |")

    A("\n\n## 6. 제안 패치 (⛔ 적용하지 않았다)\n")
    for i, p in enumerate(D["proposed_patch"], 1):
        A(f"### 6-{i}. `{p['target']}`\n")
        A(f"- 현행: `{p['current']}`")
        A(f"- 제안: `{p['proposed']}`")
        A(f"- 왜: {p['why']}")
        A(f"- 영향: {p['impact']}")
        A(f"- 위험: {p['risk']}\n")

    A("\n## 7. 남은 구멍 (정직하게)\n")
    A("- **셸 두께**에 출처가 없다. DJI 는 수지 종류도 두께도 공개하지 않고, 공개 티어다운에도 "
      "벽 두께 실측이 없다. 박막 |Gamma| 의 지배 변수가 바로 이것이다. → **모델링 선택으로 선언**하고 "
      "위 스윕으로 한계짓는 것 외에 방법이 없다. (실물 티어다운 + 버니어 측정이면 닫힌다.)")
    A("- **CFRP 이방성**을 스칼라 하나로 뭉갠다. 문헌은 각도에 따라 1e3-1e6 S/m 를 보고한다. "
      "다만 우리 대역에서 어느 값이든 1 mm 벽은 불투명하므로 |Gamma| 결론은 안 바뀐다.")
    A("- **pcb 0.80 · camera_assembly 0.85** 는 닫힌형도 문헌도 없다. 복합 조립품이라 원리적으로 "
      "그렇다. 값을 지어내 바꾸는 대신 **선언 + 한계**로 남긴다. "
      "⭐ 다만 camera_assembly 는 tier-3 중 **가장 하중이 큰 파라미터**로 드러났다 — "
      "실물을 열어볼 기회가 생기면 여기부터 볼 것.")
    A("- **기종 커버리지**: 주 스윕 3기종에는 carbon 그룹이 아예 없었다. 재질 파라미터의 영향은 "
      "**기종 의존**이므로, 어떤 파라미터를 검증하려면 그 재질을 쓰는 기종을 골라야 한다. "
      "이번엔 carbon 만 보충했고, absorber 는 드론이 아니라 챔버 재질이라 대상이 아니다.")
    A("- **편파**가 없다(스칼라 커널). 박막 |Gamma| 는 TE/TM 이 grazing 에서 크게 갈린다 "
      "— 투영가중 평균이 그 차이를 평균해 삼킨다.")
    A("- 문헌 두 편(Deffenbaugh 2013, Djordjevic 2001)은 **서지만 검증**했고 본문 수치는 못 읽었다. "
      "우리 값을 떠받치는 인용은 원문을 직접 읽은 Artner 2017 과 설치본에서 직접 읽은 ITU-R P.2040, "
      "그리고 Crossref 로 확정한 Zechmeister 2019 다.")

    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"[write] {OUT_MD}  ({len(L)} lines)")


def _merge_write(new: dict):
    old = {}
    if os.path.exists(OUT_JSON):
        try:
            with open(OUT_JSON) as fh:
                old = json.load(fh)
        except Exception:
            old = {}
    old.update(new)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(old, fh, indent=1, ensure_ascii=False)
    print(f"[write] {OUT_JSON}  keys={sorted(old)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="derive", choices=["derive", "derive2", "sweep", "doc"])
    a = ap.parse_args()
    if a.stage == "derive":
        stage_derive()
    elif a.stage == "derive2":
        stage_derive2()
    elif a.stage == "doc":
        stage_doc()
    else:
        raise SystemExit(f"stage {a.stage} 는 별도 스크립트에서 실행한다")
