# -*- coding: utf-8 -*-
"""
report15_verdict_build.py — 판정 조립 + 그림 3장 (본체는 report15_verdict.py 의 도구를 쓴다)
================================================================================
⛔ 숫자 손입력 금지. 그림 텍스트는 영어, 본문·print 는 한국어.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report15_verdict import (ASPECT_ORDER, FIGDIR, KEYS, OUT_JSON, TH,   # noqa: E402
                              _f, _fl, _jsonable, ac_corr, analyse_channel,
                              analyse_po, block_wave, corr_null_p, edge_bin,
                              harm_seeded, ideal_comb, judge, load, physics)
from paper_kit import paper_style, save_figure                            # noqa: E402

SIONNA_SRC = dict(mini2="report15_verdict_grid_mini2.json",
                  matrice4e="report15_sionna_sweep_matrice4e.json")


# --------------------------------------------------------------------------- #
#  자세별 팁 도플러 — ⭐ (b) 판정의 예측값은 **자세에 따라 달라진다**
# --------------------------------------------------------------------------- #
def ftip_for_aspect(ph, el_deg, bistatic_deg=0.0) -> dict:
    """블레이드 팁 속도는 로터면 안(수평)에 있다. 시선이 앙각 el 이면 시선방향 성분의
    최대값은 v_tip·cos(el) 이다 → 관측 가능한 도플러 확산폭은 그만큼 줄어든다.

    ⚠ 이걸 안 하면 disc 자세(el 75°)를 '실패' 로 잘못 찍는다 — 거기선 팁 속도가 시선에
      거의 수직이라 원래 도플러가 안 나온다. 반대로 블레이드 정반사(글린트)는 거기서 최대다.
      즉 **플래시가 세게 보이는 자세와 도플러가 넓게 퍼지는 자세는 서로 반대**다.
    """
    c_el = math.cos(math.radians(float(el_deg)))
    c_bi = math.cos(math.radians(float(bistatic_deg)) / 2.0)
    f_mono = ph["f_tip_hz"] * c_el
    return dict(el_deg=float(el_deg), cos_el=_f(c_el), bistatic_deg=_f(bistatic_deg),
                cos_half_bistatic=_f(c_bi),
                f_tip_aspect_hz=_f(f_mono), f_tip_aspect_bistatic_hz=_f(f_mono * c_bi),
                f_tip_broadside_hz=_f(ph["f_tip_hz"]),
                in_flash_bins=_f(f_mono / ph["f_flash_hz"]),
                note_ko="예측 = 2·v_tip·cos(el)/λ. 준-모노스태틱 보정은 cos(β/2) 로 따로 남긴다.")


def judge_b(cell, ft, ideal=None) -> dict:
    """(b) 판정 — 자세별 f_tip 예측 대비 관측 가장자리.

    ⭐ 교정 먼저: **이상적 회전 점산란자**를 같은 측정법에 통과시켜 본다. 이상 모형조차
      ±20 % 안에 못 들어오는 칸이면(빈 폭이 예측보다 크거나 비슷한 칸에서 실제로 일어난다)
      그 칸의 (b) 는 **시험이 성립하지 않는 것**이지 Sionna 가 실패한 것이 아니다.
      그런 칸은 ok=None 으로 두고 이유를 남긴다 — False 로 찍으면 거짓 유죄가 된다."""
    fe = cell.get("f_edge_hz")
    pred = ft["f_tip_aspect_hz"]
    if fe is None or not pred:
        return dict(ok=None, reason="가장자리 또는 예측이 없다", f_edge_hz=fe,
                    f_tip_pred_hz=pred)
    cal = None
    if ideal is not None:
        ife = ideal.get("f_edge_hz")
        cal = dict(ideal_f_edge_hz=ife,
                   ideal_ratio=_f(ife / pred) if ife else None,
                   test_calibrated=(bool(abs(ife / pred - 1.0) <= TH["ftip_tol"])
                                    if ife else None))
        if cal["test_calibrated"] is False:
            return dict(ok=None, reason=("이 칸은 시험이 교정되지 않는다 — 이상 점산란자조차 "
                                         "같은 측정법에서 ±20 % 를 벗어난다"),
                        f_edge_hz=_f(fe), f_tip_pred_hz=_f(pred), ratio=_f(fe / pred),
                        calibration=cal, tol=TH["ftip_tol"],
                        edge_bin=cell.get("edge_bin"))
    r = fe / pred
    #  분해 단위가 f_flash 이므로 ±20 % 안에 **정수 빈이 하나라도** 들어가는지 함께 남긴다
    lo, hi = pred * (1 - TH["ftip_tol"]), pred * (1 + TH["ftip_tol"])
    #  빈 폭 = f_flash. Sionna 쪽 dict 에는 직접 들어 있고, PO 쪽은 harm_freq_hz 첫 항이 그 값이다.
    fb = cell.get("f_flash_hz") or (cell.get("harm_freq_hz") or [None])[0]
    if not fb:
        return dict(ok=None, reason="빈 폭(f_flash)을 못 찾음", f_edge_hz=fe,
                    f_tip_pred_hz=pred)
    reachable = [k for k in range(1, 200) if lo <= k * fb <= hi]
    #  ⚠ 문턱 민감도 — −20 dB 는 선언값이다. 다른 문턱에서 판정이 뒤집히는지 함께 남긴다.
    sens = {}
    for tag, e in (cell.get("edge_bins_by_drop") or {}).items():
        fh = e.get("f_edge_hz")
        sens[tag] = dict(f_edge_hz=fh, ratio=_f(fh / pred) if fh else None,
                         ok=(bool(abs(fh / pred - 1.0) <= TH["ftip_tol"]) if fh else None))
    return dict(ok=bool(abs(r - 1.0) <= TH["ftip_tol"]), f_edge_hz=_f(fe),
                f_tip_pred_hz=_f(pred), ratio=_f(r), tol=TH["ftip_tol"],
                edge_bin=cell.get("edge_bin"), threshold_sensitivity=sens,
                calibration=cal,
                robust_to_threshold=bool(sens and len({v["ok"] for v in sens.values()
                                                       if v["ok"] is not None}) == 1),
                window_hz=[_f(lo), _f(hi)], bins_inside_window=reachable,
                test_resolvable=bool(reachable),
                granularity_frac=_f(fb / pred),
                note_ko=("스펙트럼은 f_flash 정수배에만 산다. bins_inside_window 가 비면 "
                         "±20 % 창 안에 놓일 수 있는 빈이 아예 없다는 뜻 — 그 칸에서 (b) 는 "
                         "원리적으로 통과 불가능하고, 그 사실 자체를 결과로 읽어야 한다."))


def ideal_reference(phys) -> dict:
    """⭐ 해석적 이상 모형(회전 점산란자)을 **같은 잣대**로 통과시킨다.

    이것이 판정 (b) 의 **교정**이다: 참인 마이크로도플러를 넣었을 때 우리의 −20 dB
    가장자리 측정법이 예측 f_tip 을 몇 배로 되돌려 주는가. 그 값이 1 근처가 아니면
    측정법이 편향된 것이고, Sionna 를 그 잣대로 재는 것 자체가 무의미해진다."""
    out = {}
    for key in KEYS:
        ph = phys[key]
        for ak, el in ((a, e) for a, _, e in
                       (("nose", 0.0, 15.0), ("oblique", 45.0, 15.0), ("side", 90.0, 15.0),
                        ("hot", 0.0, 0.0), ("disc", 0.0, 75.0))):
            ic = ideal_comb(ph, el)
            ft = ftip_for_aspect(ph, el)
            fe = ic["f_edge_hz"]
            pred = ft["f_tip_aspect_hz"]
            ic["calibration"] = dict(
                f_tip_pred_hz=pred, ratio=_f(fe / pred) if fe and pred else None,
                passes_same_test=(bool(abs(fe / pred - 1.0) <= TH["ftip_tol"])
                                  if fe and pred else None))
            out[f"{key}/{ak}"] = ic
    ok = [v["calibration"]["passes_same_test"] for v in out.values()
          if v["calibration"]["passes_same_test"] is not None]
    return dict(by_cell=out, n=len(ok), n_pass=int(sum(ok)),
                test_is_calibrated=bool(ok and all(ok)),
                note_ko=("이상 모형이 같은 시험을 통과하지 못하면 시험이 틀린 것이다. "
                         "통과하면, Sionna 의 실패는 Sionna 의 성질이다."))


# --------------------------------------------------------------------------- #
#  §1 — Sionna 격자 분석
# --------------------------------------------------------------------------- #
def analyse_sionna(J, ph) -> dict:
    """⚠ 격자가 **다 안 돌았으면** 분석하지 않는다. 중간저장본은 위상축이 잘려 있어
    DFT 빈이 다른 주파수를 뜻하게 된다 — 조용히 섞이면 안 되는 종류의 오류다."""
    out = {}
    if not J or "grid" not in J:
        return out
    G = J["grid"]
    if not G.get("complete") or "blocks" not in G:
        return out
    #  자세 목록은 grid 에 있고, 없으면 meta 에서 (중간저장 형식 대비)
    asp = G.get("aspects") or (J.get("meta") or {}).get("aspects") or []
    geo = G.get("geometry", {})
    for bk, B in G["blocks"].items():
        R, ak, mode = bk.split("/")
        el = float(next((a["el_deg"] for a in asp if a["name"] == ak), 15.0))
        bi = float(geo.get(f"{R}/{ak}", {}).get("bistatic_deg", 0.0))
        ft = ftip_for_aspect(ph, el, bi)
        ic = ideal_comb(ph, el)
        for ch in ("all", "prop"):
            z, n = block_wave(B, ch)
            if n.max() == 0:                          # 경로가 아예 없다
                out[f"{bk}/{ch}"] = dict(
                    range_m=float(R), aspect=ak, mode=mode, channel=ch, el_deg=el,
                    empty=True, n_paths_max=0, ftip=ft,
                    n_paths_behaviour="모든 칸에서 경로 0")
                continue
            c = analyse_channel(z, n, ph)
            c.update(range_m=float(R), aspect=ak, mode=mode, channel=ch, el_deg=el,
                     empty=False, ftip=ft, judge_b=judge_b(c, ft, ic))
            out[f"{bk}/{ch}"] = c
    return out


def analyse_po_grid(J, key, ph, n_period) -> dict:
    out = {}
    if not J:
        return out
    A = (J.get("airframes") or {}).get(key)
    if not A:
        return out
    for tag in ("matched", "fine"):
        G = A.get(tag)
        if not G:
            continue
        per = n_period if tag == "matched" else int(G["n_phase"] // 2)
        for bk, B in G["blocks"].items():
            el = float(B["el_deg"])
            ft = ftip_for_aspect(ph, el)
            ic = ideal_comb(ph, el)
            for ch, (kr, ki) in (("all", ("all_re", "all_im")),
                                 ("prop", ("prop_re", "prop_im"))):
                E = np.asarray(B[kr], float) + 1j * np.asarray(B[ki], float)
                c = analyse_po(E, ph, per)
                c.update(range_m=float(B["range_m"]), aspect=B["aspect"], channel=ch,
                         el_deg=el, ftip=ft, grid=tag, judge_b=judge_b(c, ft, ic))
                out[f"{tag}/{bk}/{ch}"] = c
    return out


# --------------------------------------------------------------------------- #
#  §2 — 널 (거리축)
# --------------------------------------------------------------------------- #
def analyse_nulls(J, phys) -> dict:
    out = dict(available=bool(J), arms={})
    if not J:
        return out
    for akey, A in J.get("arms", {}).items():
        drone = "matrice4e" if "matrice4e" in akey else "mini2"
        ph = phys[drone]
        rows = {}
        for rk, B in A["by_range"].items():
            for ch in ("all", "prop"):
                kr, ki = ("hr", "hi") if ch == "all" else ("hpr", "hpi")
                kn = "n" if ch == "all" else "n_prop"
                z = np.asarray(B[kr], float) + 1j * np.asarray(B[ki], float)
                n = np.asarray(B[kn], float)
                if n.max() == 0:
                    rows[f"{rk}/{ch}"] = dict(range_m=float(rk), channel=ch, empty=True)
                    continue
                c = analyse_channel(z, n, ph)
                c.update(range_m=float(rk), channel=ch, empty=False)
                rows[f"{rk}/{ch}"] = c
            sp = [v for v in B.get("spec_n", []) if v is not None]
            rows[f"{rk}/spec_paths"] = dict(
                range_m=float(rk), n_phase=len(sp),
                spec_paths_total=int(sum(sp)) if sp else 0,
                spec_paths_max=int(max(sp)) if sp else 0,
                specular_channel_empty=bool(sp and max(sp) == 0))
        out["arms"][akey] = dict(
            drone=drone, role=A.get("role"), label_ko=A.get("label_ko"),
            expect_modulation=A.get("expect_modulation"),
            mesh_n_tris=(A.get("mesh") or {}).get("n_tris"), by=rows)
    return out


def ladder_from_null_control(J) -> dict:
    """(d) 삼각형 절반 — 기존 R=3 m 널대조의 해상도 사다리를 그대로 판정에 쓴다."""
    if not J:
        return dict(available=False)
    L = J.get("resolution_ladder") or {}
    return dict(available=bool(L),
                n_levels=L.get("n_levels"), all_significant=L.get("all_significant"),
                ptp_span_db=L.get("modulation_ptp_span_db"),
                ptp_max_rel_change=L.get("modulation_ptp_max_rel_change"),
                level_span_db=L.get("level_span_db"),
                min_pearson_r=L.get("min_pearson_r_vs_full"),
                rows=L.get("rows"),
                scope_ko="mini2 · R=3 m · az 0/el 15 에서만 측정됐다(거리축으로는 확장 안 됨).",
                source="outputs/report15_null_control.json:resolution_ladder")


# --------------------------------------------------------------------------- #
#  §3 — Sionna ↔ PO 대조
# --------------------------------------------------------------------------- #
def compare_engines(S, PO, key, n_period, nulls_p=True) -> dict:
    """같은 (거리·자세·채널)에서 Sionna 확산채널과 PO 를 겹친다."""
    rows = {}
    for R in ("1", "3", "10"):
        for ak in ASPECT_ORDER:
            for ch in ("all", "prop"):
                sc = S.get(f"{R}/{ak}/prod/{ch}")
                pc = PO.get(f"matched/{R}/{ak}/{ch}")
                if not sc or sc.get("empty") or not pc:
                    continue
                #  복소 파형 복원 (둘 다 진폭 dB + 위상 deg 로 저장했다)
                zs = _wave_from(sc)
                zp = _wave_from(pc)
                n = min(len(zs), len(zp))
                zs, zp = zs[:n], zp[:n]
                #  ⭐ 두 지표를 따로 낸다:
                #    complex — 절대위상·상수복소배에 불변인 정식 파형 상관
                #    amp     — 위상 규약 차이를 아예 배제한 보수적 하한
                c_cplx = ac_corr(zs, zp)
                c_amp = ac_corr(np.abs(zs).astype(complex), np.abs(zp).astype(complex))
                # 조화 스펙트럼 상관 (모양 비교 — 절대 레벨에 불변)
                hs = np.asarray(sc["harm_abs"], float)
                hp = np.asarray(pc["harm_abs"], float)
                m = min(len(hs), len(hp))
                hs_, hp_ = hs[:m], hp[:m]
                spec_c = float(np.dot(hs_, hp_) / (np.linalg.norm(hs_) * np.linalg.norm(hp_))
                               ) if hs_.any() and hp_.any() else None
                row = dict(range_m=float(R), aspect=ak, channel=ch,
                           complex_corr=_f(c_cplx), amp_corr=_f(c_amp),
                           spectrum_cosine=_f(spec_c),
                           sionna_edge_bin=sc.get("edge_bin"), po_edge_bin=pc.get("edge_bin"),
                           sionna_dominant_bin=sc.get("dominant_bin_by_amp"),
                           po_dominant_bin=pc.get("dominant_bin_by_amp"),
                           sionna_ptp_db=sc.get("modulation_ptp_db"),
                           po_ptp_db=pc.get("modulation_ptp_db"),
                           ptp_ratio_db=(_f(sc["modulation_ptp_db"] - pc["modulation_ptp_db"])
                                         if sc.get("modulation_ptp_db") is not None
                                         and pc.get("modulation_ptp_db") is not None else None))
                if nulls_p:
                    #  ⚠ 상관이 '둘 다 k=1 에 몰려 있어서' 자동으로 나오는 값은 아닌지 검정
                    row["complex_corr_null"] = {
                        k: _f(v) if isinstance(v, float) else v
                        for k, v in corr_null_p(zs, zp, n_mc=2000).items()}
                rows[f"{R}/{ak}/{ch}"] = row
    #  ⭐ 근거리에서 좁혀지는가 — 거리별 요약
    by_range = {}
    for R in ("1", "3", "10"):
        sel = [r for r in rows.values()
               if r["range_m"] == float(R) and r["channel"] == "prop"]
        v = [r["complex_corr"] for r in sel if r["complex_corr"] is not None]
        va = [r["amp_corr"] for r in sel if r["amp_corr"] is not None]
        s = [r["spectrum_cosine"] for r in sel if r["spectrum_cosine"] is not None]
        by_range[R] = dict(n=len(v),
                           complex_corr_mean=_f(np.mean(v)) if v else None,
                           complex_corr_median=_f(np.median(v)) if v else None,
                           amp_corr_mean=_f(np.mean(va)) if va else None,
                           spectrum_cosine_mean=_f(np.mean(s)) if s else None)
    ords = [by_range[R]["complex_corr_mean"] for R in ("1", "3", "10")]
    return dict(rows=rows, by_range=by_range,
                improves_at_near_range=(None if any(o is None for o in ords)
                                        else bool(ords[0] >= ords[1] >= ords[2])),
                corr_near_minus_far=(None if any(o is None for o in ords) else
                                     _f(ords[0] - ords[2])),
                note_ko=("PO 는 결정론적이고 위상이 우리 규약이라, 비교는 **AC 진폭 파형**과 "
                         "**조화 스펙트럼 모양**으로 한다(상수 복소배·절대위상에 불변)."))


# --------------------------------------------------------------------------- #
#  §4 — 그림
# --------------------------------------------------------------------------- #
#  ⭐ 표시 규약은 **src/md_mapstyle.py 한 자리**가 정한다 — 여기서 다시 정하지 않는다.
#     (0.45 블레이드 주기 조각 · hop 2 · 8배 제로패딩 · jet · 0~−40 dB · gouraud · rasterized)
import md_mapstyle as MS                                                  # noqa: E402

N_PERIOD_TILES = 12          # 위상 격자 한 주기를 이만큼 이어 붙여 슬로타임을 만든다(= 6 회전)


def _spec_data(zp, f_flash, n_tiles=N_PERIOD_TILES):
    """⭐ 한 주기 위상 파형 → **md_mapstyle 규약** 스펙트로그램 + DC 기준값.

    ⚠ 위상 격자는 **블레이드 한 주기**만 돈다. 슬로타임 기록을 만들려면 이어 붙일 수밖에
      없고, 그래서 이 맵은 **구성상 정확히 주기적**이다 — 시간축의 되풀이는 자료가 아니라
      이어 붙이기다. 그 사실을 캡션에 적는다.

    ⚠ 패널마다 제 최대값으로 정규화하면 구 널이 신호만큼 밝게 보인다 — 실제로는 1000 배
      약한데도. 그건 그림이 거짓말을 하는 것이다. DC(정지 반사)로 정규화하면 모든 패널이
      '정지 반사 대비 변조 깊이' 라는 같은 물리량이 되고, 널은 있는 그대로 캄캄해진다.
      ⭐ 0 도플러는 **지우지 않는다**(규약) — 동체 선이 0 dB 로 남아 읽기의 기준이 된다.

    반환: dict(t, f, S, nper, prf, dc, peak_sideband_db) 또는 None.
    """
    zp = np.asarray(zp, complex)
    n = zp.size
    dc = float(np.abs(zp.mean()))
    ac = zp - zp.mean()
    if n < 8 or not np.isfinite(ac).all() or np.abs(ac).max() <= 0 or dc <= 0:
        return None
    prf = n * float(f_flash)                     # 한 주기 = 1/f_flash 초 → 등가 표본율
    per = MS.auto_periods(prf, f_flash)
    x = np.tile(zp, int(n_tiles))
    f, t, S, nper = MS.flash_spec(x, prf, f_flash, per)
    #  ⭐ 인용용 수치는 **DC 를 뺀** 같은 STFT 에서 잰다 — 옛 판의 «변조 깊이» 와 직접 비교된다.
    _f2, _t2, S_ac, _n2 = MS.flash_spec(np.tile(ac, int(n_tiles)), prf, f_flash, per)
    peak = 20.0 * math.log10(float(np.nanmax(S_ac)) / dc + 1e-14)
    return dict(t=t, f=f, S=S, nper=int(nper), prf=prf, dc=dc, periods=float(per),
                peak_sideband_db=float(peak))


def _spec_panel(ax, data, f_tip_pred, title):
    """한 패널 = 한 소스의 양측 스펙트로그램. 색은 **DC 대비 변조 깊이**(0 ~ −40 dB)."""
    if data is None:
        ax.text(0.5, 0.5, "no modulation\nAC = 0 exactly", ha="center", va="center",
                transform=ax.transAxes, fontsize=8)
        ax.set_title(title, fontsize=8)
        ax.set_axis_off()
        return None
    m = MS.draw(ax, data["t"], data["f"], data["S"], f_tip_pred, ref=data["dc"])
    ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=8)
    _spec_panel.last_mesh = m
    return data["peak_sideband_db"]


def _wave_from(cell):
    """분석 dict → 복소 φ 파형 (Sionna 는 진폭+위상, PO 는 진폭만)."""
    a = np.asarray(cell["wave_amp_db"], float)
    if cell.get("wave_phase_deg") is not None:
        return 10 ** (a / 20.0) * np.exp(1j * np.radians(np.asarray(cell["wave_phase_deg"], float)))
    return (10 ** (a / 20.0)).astype(complex)


NULL_ARMS = [("mini2 · sphere null (z-spin)", "mini2", "sphere_mini2_plastic"),
             ("mini2 · disc null (rot.-symm.)", "mini2", "disc_mini2"),
             ("mini2 · rotor removed", "mini2", "norotor_mini2"),
             ("matrice4e · sphere null (z-spin)", "matrice4e", "sphere_matrice4e_plastic")]


def fig1_spectrograms(J, phys, S, PO, NU, path):
    """그림 1 — 신호 팔 네 줄 + **대표 널 한 줄**, 거리 3 열 (자세 nose).

    ⭐ 2026-08-10 다시 그렸다. 바뀐 것은 둘이다.

    (1) **표시 규약을 md_mapstyle 로 통일**했다. 옛 판은 조각이 **블레이드 2 주기**여서
        플래시가 한 조각 안에서 시간평균되어 지워지고 가로 줄무늬만 남았다. 규약값
        0.45 주기로 내리면 시간 분해능이 4.4 배 좋아진다(예: mini2 6.52 → 1.48 ms).
        ⚠ 대가는 주파수 분해능이다 — mini2 는 빗살 간격(f_flash 306.7 Hz)보다 빈이 넓어져
          **조화 빗살이 뭉친다**. 빗살을 읽는 그림은 f2 가 따로 있고, 여기서 답하는 질문은
          «널에서도 무늬가 보이는가» 이지 «빗살이 몇 개인가» 가 아니다.

    (2) **패널을 24 → 15 로 줄였다.** 널 네 줄은 세 거리 전부에서 «아무것도 없다» 는
        **한 가지**만 말한다. 널을 네 줄 그리면 그림의 절반이 검은 칸이 되고, 정작 봐야 할
        신호 줄이 작아진다. 그래서 **가장 시끄러운 널**(자료가 고른다) 한 줄만 그리고
        나머지는 수치로 접는다 — 가장 시끄러운 것이 조용하면 나머지는 자동으로 조용하다.
        접은 값은 반환 JSON 의 `null_rows_folded` 에 전부 남는다(숨기는 것이 아니다).
    """
    import matplotlib.pyplot as plt
    import textwrap
    ranges = ("1", "3", "10")

    def _cell_data(c, key):
        """한 칸 → (스펙트로그램 dict, 예측 f_tip) 또는 (None, None)."""
        if not c or c.get("empty"):
            return None, None
        ph = phys[key]
        fp = (c["ftip"]["f_tip_aspect_hz"] if c.get("ftip")
              else ph["f_tip_hz"] * math.cos(math.radians(15.0)))
        return _spec_data(_wave_from(c), ph["f_flash_hz"]), fp

    #  ── 널 팔 전량을 **먼저 재어** 대표를 자료가 고르게 한다 ──────────────────
    folded = {}
    for lab, key, arm in NULL_ARMS:
        by = ((NU.get("arms") or {}).get(arm) or {}).get("by", {})
        row = {}
        for R in ranges:
            d, _fp = _cell_data(by.get(f"{R}/all"), key)
            row[R] = _f(d["peak_sideband_db"]) if d else None
        vals = [v for v in row.values() if v is not None]
        folded[arm] = dict(label=lab, airframe=key, peak_sideband_db_re_dc=row,
                           worst_db=_f(max(vals)) if vals else None)
    ranked = sorted((v for v in folded.values() if v["worst_db"] is not None),
                    key=lambda v: -v["worst_db"])
    rep = ranked[0] if ranked else None
    rep_arm = next((a for a, v in folded.items() if v is rep), None)

    #  ── 그리는 줄 = 신호 4 + 대표 널 1 ───────────────────────────────────────
    rows = []
    for key in KEYS:
        rows.append((f"{key}\nSionna (prop ch.)", key,
                     lambda R, k=key: S[k].get(f"{R}/nose/prod/prop"), "signal"))
        rows.append((f"{key}\nPO kernel (prop ch.)", key,
                     lambda R, k=key: PO[k].get(f"matched/{R}/nose/prop"), "signal"))
    if rep_arm is not None:
        rows.append((rep["label"].replace(" · ", "\n") + "\n(loudest null)",
                     rep["airframe"],
                     lambda R, a=rep_arm: ((NU.get("arms") or {}).get(a) or {})
                     .get("by", {}).get(f"{R}/all"), "null"))
    nrows = len(rows)

    grid, levels = {}, {}
    for i, (lab, key, getter, kind) in enumerate(rows):
        for j, R in enumerate(ranges):
            d, fp = _cell_data(getter(R), key)
            grid[(i, j)] = (d, fp, None if d is not None else
                            ("no paths" if kind == "signal" else "not measured"))
            if d is not None:
                levels[f"{lab}|{R}"] = _f(d["peak_sideband_db"])

    with paper_style(width=7.16, base_pt=8.5) as st:
        fig, axes = plt.subplots(nrows, len(ranges), figsize=(7.16, 1.42 * nrows),
                                 constrained_layout=True, squeeze=False)
        for i, (lab, key, _g, _kind) in enumerate(rows):
            for j, R in enumerate(ranges):
                ax = axes[i][j]
                d, fp, msg = grid[(i, j)]
                if msg is not None:
                    ax.text(0.5, 0.5, msg, ha="center", va="center",
                            transform=ax.transAxes, fontsize=8)
                    ax.set_axis_off()
                    continue
                lv = _spec_panel(ax, d, fp, f"R = {R} m" if i == 0 else "")
                #  ⭐ 판마다 «DC 대비 최대 변조 깊이» 를 뱃지로 — 널 줄이 왜 널인지가
                #     색이 아니라 **수치**로 읽힌다. (설정값이 아니라 결과이므로 그림에 둔다.)
                ax.text(0.985, 0.955, f"sideband {lv:.0f} dB", transform=ax.transAxes,
                        ha="right", va="top", color="w", fontsize=8,
                        bbox=dict(fc="#000000b0", ec="none", pad=1.4))
                if j == 0:
                    ax.set_ylabel(lab, fontsize=8)
                #  ⚠ 줄마다 기체가 다르면 **시간축 눈금이 다르다**(플래시 주기가 다르므로).
                #    그래서 눈금을 숨기지 않는다 — 숨기면 다른 축을 같은 축처럼 읽게 된다.
        for j in range(len(ranges)):
            axes[-1][j].set_xlabel("slow time [ms]", fontsize=8)
        pm = getattr(_spec_panel, "last_mesh", None)
        if pm is not None:
            cb = fig.colorbar(pm, ax=axes.ravel().tolist(), fraction=0.02, pad=0.01)
            cb.set_label("magnitude [dB re each panel's static return]", fontsize=8)
            cb.ax.tick_params(labelsize=8)
        #  ⭐ 그림 안에는 설정값을 적지 않는다(하우스 규약) — 한 줄 제목만.
        fig.suptitle("Two-sided micro-Doppler, aspect az 0 / el 15.  "
                     "White dashed = kinematic tip Doppler.", fontsize=9)

    one = grid[(0, 0)][0] or next((d for d, _f2, _m in grid.values() if d), None)
    cap = textwrap.fill(
        "Two-sided micro-Doppler spectrograms built by stepping the rotor phase and "
        "re-tracing the whole scene. Rows one to four are the signal arms - the stock "
        "Sionna PathSolver and our PO kernel, for both airframes; the bottom row is the "
        "loudest of the four rotationally symmetric null controls, chosen by the "
        "measurement itself. Columns are target range. Colour is modulation depth "
        "relative to each panel's own static return, so the null row is directly "
        "comparable with the signal rows and the static return itself sits at 0 dB. "
        "The badge in each panel is the peak of the same spectrogram computed after the "
        "static component is removed, so it states in numbers what the colour cannot: the "
        "signal arms modulate within a few dB of their own static return, the null control "
        "sixty to eighty dB below it. Time axes differ between airframes because the blade "
        "flash rates differ. The rotor-phase sweep covers one blade period, so the "
        "slow-time record is that period tiled and the map is exactly periodic by "
        "construction; the repetition along time is the tiling, not new data.", 96)
    save_figure(fig, path, caption=cap, close=True)
    return dict(peak_sideband_db_re_dc=levels,
                colour_scale_db=[MS.VMIN, MS.VMAX],
                colour_reference="each panel's own static (DC) return",
                n_panels=int(nrows * len(ranges)),
                n_panels_before=24,
                rows_drawn=[r[0].replace("\n", " ") for r in rows],
                representative_null=rep_arm,
                null_rows_folded=folded,
                null_selection_rule_ko=(
                    "널 네 줄은 «아무것도 없다» 는 한 가지만 말하므로 **가장 시끄러운 널** "
                    "한 줄만 그린다. 대표는 자료가 고른다(세 거리 최대 변조 깊이 최댓값). "
                    "가장 시끄러운 널이 조용하면 나머지 널은 자동으로 조용하다 — 나머지 "
                    "세 줄의 값은 null_rows_folded 에 그대로 남는다."),
                null_ranking_db=[[v["label"], v["worst_db"]] for v in ranked],
                display=dict(module="src/md_mapstyle.py", call="flash_spec(auto_periods)",
                             periods=(one or {}).get("periods"),
                             nperseg=(one or {}).get("nper"),
                             hop=MS.FLASH_HOP, zero_pad=MS.FLASH_PAD,
                             cmap=MS.CMAP, shading=MS.SHADING,
                             zero_doppler_kept=True,
                             tiles_of_one_blade_period=N_PERIOD_TILES))


_ASPECT_EL = dict(nose=15.0, oblique=15.0, side=15.0, hot=0.0, disc=75.0)


def _geom_overlay(ax, GR, key, R, aspects):
    """같은 메쉬로 위상만 더한 기하 기준을 회색 참조선으로 겹친다 — (b) 의 참기준."""
    A = ((GR or {}).get("airframes") or {}).get(key)
    if not A:
        return False
    drew = False
    for ak in aspects:
        g = A["by_cell"].get(f"{R}/{ak}")
        if not g:
            continue
        a = np.asarray(g["harm_abs"], float)
        if a.max() <= 0:
            continue
        ax.plot(np.asarray(g["harm_freq_hz"], float), 20 * np.log10(a / a.max() + 1e-12),
                color="0.5", lw=0.9, ls=(0, (1, 1.2)), marker="None", zorder=0,
                label="geometry-only phase ref." if not drew else None)
        drew = True
    return drew


def _ideal_overlay(ax, ph, aspects):
    """이상 회전 점산란자 빗을 회색 참조선으로 겹친다 — 판정 (b) 의 교정선이다."""
    for ak in aspects:
        ic = ideal_comb(ph, _ASPECT_EL[ak])
        a = np.asarray(ic["harm_abs"], float)
        if a.max() <= 0:
            continue
        ax.plot(np.asarray(ic["harm_freq_hz"], float), 20 * np.log10(a / a.max() + 1e-12),
                color="0.55", lw=0.9, ls=(0, (1, 1.2)), marker="None", zorder=0,
                label="ideal point scatterer" if ak == aspects[0] else None)


def fig2_flash_vs_ftip(J, phys, S, PO, GR, path):
    """그림 2 — 조화 스펙트럼과 f_tip. (b) 판정선이 이 그림이다."""
    import matplotlib.pyplot as plt
    aspects = ("nose", "hot", "disc")
    with paper_style(width=7.16, base_pt=8.5) as st:
        fig, axes = plt.subplots(3, len(KEYS), figsize=(7.16, 7.4),
                                 constrained_layout=True, squeeze=False)
        #  (1~2행) 조화 스펙트럼 — 자세별, R=1 m
        for c_i, key in enumerate(KEYS):
            ph = phys[key]
            ax = axes[0][c_i]
            for i, ak in enumerate(aspects):
                c = S[key].get(f"1/{ak}/prod/prop")
                if not c or c.get("empty"):
                    continue
                fq = np.asarray(c["harm_freq_hz"], float)
                a = np.asarray(c["harm_abs"], float)
                a = 20 * np.log10(a / a.max() + 1e-12)
                ax.plot(fq, a, label=f"{ak} (el {c['el_deg']:.0f})",
                        **st.series(i), markersize=3)
                ax.axvline(c["ftip"]["f_tip_aspect_hz"], color=st.color(i),
                           ls=":", lw=1.0)
            _geom_overlay(ax, GR, key, "1", aspects)
            ax.set_xlim(0, 2.2 * ph["f_tip_hz"]); ax.set_ylim(-45, 3)
            ax.set_title(f"{key} — Sionna, R = 1 m, prop channel", fontsize=9)
            ax.set_ylabel("harmonic amp [dB re peak]")
            ax.legend(fontsize=8, ncol=1)
            ax.grid(alpha=0.25)

            ax = axes[1][c_i]
            for i, ak in enumerate(aspects):
                c = PO[key].get(f"matched/1/{ak}/prop")
                if not c:
                    continue
                fq = np.asarray(c["harm_freq_hz"], float)
                a = np.asarray(c["harm_abs"], float)
                a = 20 * np.log10(a / a.max() + 1e-12)
                ax.plot(fq, a, label=f"{ak} (el {c['el_deg']:.0f})",
                        **st.series(i), markersize=3)
                ax.axvline(c["ftip"]["f_tip_aspect_hz"], color=st.color(i), ls=":", lw=1.0)
            _geom_overlay(ax, GR, key, "1", aspects)
            ax.set_xlim(0, 2.2 * ph["f_tip_hz"]); ax.set_ylim(-45, 3)
            ax.set_title(f"{key} — PO kernel, R = 1 m, prop channel", fontsize=9)
            ax.set_ylabel("harmonic amp [dB re peak]")
            ax.set_xlabel("frequency [Hz]  (bin = blade-flash rate)")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.25)

        #  (3행) 관측 가장자리 vs 예측 — 판정선
        for c_i, key in enumerate(KEYS):
            ax = axes[2][c_i]
            xs, ys, cs, mk = [], [], [], []
            for i, (src, D, tag) in enumerate((("Sionna", S[key], "prod"),
                                               ("PO", PO[key], "matched"),
                                               ("geometry-only", None, "geom"))):
                px, py = [], []
                if src == "geometry-only":
                    A = ((GR or {}).get("airframes") or {}).get(key) or {}
                    for ck, g in (A.get("by_cell") or {}).items():
                        if g.get("f_edge_hz") is None:
                            continue
                        px.append(g["f_tip_pred_hz"]); py.append(g["f_edge_hz"])
                else:
                    for R in ("1", "3", "10"):
                        for ak in ASPECT_ORDER:
                            k = (f"{R}/{ak}/prod/prop" if src == "Sionna"
                                 else f"matched/{R}/{ak}/prop")
                            c = D.get(k)
                            if not c or c.get("empty") or c.get("f_edge_hz") is None:
                                continue
                            px.append(c["ftip"]["f_tip_aspect_hz"])
                            py.append(c["f_edge_hz"])
                sty = dict(st.series(i)); sty["linestyle"] = "none"
                ax.plot(px, py, label=src, **sty, markersize=5, alpha=0.85)
            ph = phys[key]
            lim = 1.35 * ph["f_tip_hz"]
            xx = np.linspace(0, lim, 50)
            ax.plot(xx, xx, color="0.35", lw=1.0, ls="-", marker="None", zorder=0)
            ax.fill_between(xx, xx * (1 - TH["ftip_tol"]), xx * (1 + TH["ftip_tol"]),
                            color="0.75", alpha=0.45, zorder=0,
                            label=f"±{TH['ftip_tol']*100:.0f} % pass band")
            ax.set_xlim(0, lim); ax.set_ylim(0, lim)
            ax.set_xlabel("predicted tip Doppler  2·v_tip·cos(el)/λ  [Hz]")
            ax.set_ylabel("measured spectral edge [Hz]")
            ax.set_title(f"{key} — criterion (b)", fontsize=9)
            ax.legend(fontsize=8)
            ax.grid(alpha=0.25)
        fig.suptitle("Criterion (b): does the modulation spectrum reach the blade-tip "
                     "Doppler?", fontsize=9)
    save_figure(fig, path, caption=(
        "Harmonic spectra of the rotor-phase modulation and the resulting test of "
        "criterion (b). Energy exists only at integer multiples of the blade-flash rate, "
        "so the measured spectral edge is quantised; the pass band is the kinematic tip "
        "Doppler projected on the line of sight, ±20 %."), close=True)


def fig3_paths_and_divergence(J, phys, S, PO, CMP, path):
    """그림 3 — 경로수 시계열(톱니 판정) + Sionna↔PO 갈림(거리·자세별)."""
    import matplotlib.pyplot as plt
    with paper_style(width=7.16, base_pt=8.5) as st:
        fig, axes = plt.subplots(3, len(KEYS), figsize=(7.16, 7.0),
                                 constrained_layout=True, squeeze=False)
        for c_i, key in enumerate(KEYS):
            ph = phys[key]
            #  (1행) 확산 채널 경로수 vs 위상
            ax = axes[0][c_i]
            for i, R in enumerate(("1", "3", "10")):
                c = S[key].get(f"{R}/nose/prod/prop")
                if not c or c.get("empty"):
                    continue
                y = np.asarray(c["n_paths_by_phase"], float)
                ax.plot(np.linspace(0, 180, len(y), endpoint=False), y / y.mean(),
                        label=f"R = {R} m (mean {y.mean():.0f})", **st.series(i),
                        markersize=2.5)
            ax.set_ylabel("path count / mean")
            ax.set_title(f"{key} — diffuse channel, prop paths", fontsize=9)
            ax.legend(fontsize=8); ax.grid(alpha=0.25)
            ax.set_ylim(0, None)

            #  (2행) 정반사 채널 경로수 — 켜지는가
            ax = axes[1][c_i]
            drew = False
            for i, R in enumerate(("1", "3", "10")):
                for jj, ak in enumerate(("nose", "hot", "disc")):
                    c = S[key].get(f"{R}/{ak}/spec/prop")
                    if not c:
                        continue
                    y = (np.asarray(c["n_paths_by_phase"], float)
                         if not c.get("empty") else np.zeros(64))
                    if y.max() > 0:
                        ax.plot(np.linspace(0, 180, len(y), endpoint=False), y,
                                label=f"{ak}, R={R} m", **st.series(i * 3 + jj),
                                markersize=2.5)
                        drew = True
            if not drew:
                ax.text(0.5, 0.5, "specular channel: 0 propeller paths\n"
                                  "in every cell of the grid",
                        ha="center", va="center", transform=ax.transAxes, fontsize=9)
                ax.set_ylim(0, 1)
            ax.set_ylabel("specular path count")
            ax.set_title(f"{key} — specular channel, prop paths", fontsize=9)
            ax.grid(alpha=0.25)
            if drew:
                ax.legend(fontsize=8)

            #  (3행) Sionna ↔ PO 상관 vs 거리
            ax = axes[2][c_i]
            for i, ak in enumerate(ASPECT_ORDER):
                xs, ys = [], []
                for R in ("1", "3", "10"):
                    r = CMP[key]["rows"].get(f"{R}/{ak}/prop")
                    if r and r.get("complex_corr") is not None:
                        xs.append(float(R)); ys.append(r["complex_corr"])
                if xs:
                    ax.plot(xs, ys, label=ak, **st.series(i), markersize=4)
            ax.set_xscale("log"); ax.set_xticks([1, 3, 10])
            ax.set_xticklabels(["1", "3", "10"])
            ax.set_ylim(-0.05, 1.05)
            ax.set_xlabel("range [m]")
            ax.set_ylabel("|AC corr|  Sionna vs PO")
            ax.set_title(f"{key} — where the engines diverge", fontsize=9)
            ax.legend(fontsize=8, ncol=2); ax.grid(alpha=0.25)
        fig.suptitle("Path-count continuity (is there a sawtooth?) and Sionna-vs-PO "
                     "agreement across range", fontsize=9)
    save_figure(fig, path, caption=(
        "Top: propeller path count versus rotor phase in the diffuse channel, normalised "
        "to its own mean - continuous, with no switching on and off. Middle: the specular "
        "channel over the same grid. Bottom: amplitude-waveform correlation between the "
        "stock Sionna PathSolver and our PO kernel as a function of range."), close=True)


# --------------------------------------------------------------------------- #
#  §5 — 조립
# --------------------------------------------------------------------------- #
def build():
    t0 = time.time()
    print("§0  물리")
    phys = {k: physics(k) for k in KEYS}
    for k in KEYS:
        p = phys[k]
        print(f"   {k:10s} f_rev={p['f_rev_hz']:7.2f} Hz  f_flash={p['f_flash_hz']:8.2f} Hz  "
              f"v_tip={p['v_tip_ms']:6.2f} m/s  f_tip={p['f_tip_hz']:8.2f} Hz "
              f"(= {p['f_tip_in_flash_bins']:.2f} bins)")

    print("\n§1  입력 적재")
    src = {}
    SJ = {}
    for k in KEYS:
        SJ[k] = load(SIONNA_SRC[k])
        src[f"sionna_{k}"] = dict(file=SIONNA_SRC[k], present=bool(SJ[k]),
                                  complete=bool(SJ[k] and SJ[k].get("grid", {}).get("complete")))
    POJ = load("report15_verdict_po_grid.json")
    GRJ = load("report15_verdict_geomref.json")
    NUJ = load("report15_verdict_nulls_vs_range.json")
    NCJ = load("report15_null_control.json")
    PRJ = load("report15_probe.json")
    src.update(po_grid=dict(file="report15_verdict_po_grid.json", present=bool(POJ)),
               geom_reference=dict(file="report15_verdict_geomref.json", present=bool(GRJ)),
               nulls_vs_range=dict(file="report15_verdict_nulls_vs_range.json", present=bool(NUJ)),
               null_control_R3=dict(file="report15_null_control.json", present=bool(NCJ)),
               probe=dict(file="report15_probe.json", present=bool(PRJ)))
    for k, v in src.items():
        print(f"   {k:22s} {'OK' if v['present'] else '없음'}")

    print("\n§2  Sionna 격자 분석")
    S = {k: analyse_sionna(SJ[k], phys[k]) for k in KEYS}
    for k in KEYS:
        print(f"   {k:10s} 채널 {len(S[k])} 개")

    print("\n§3  PO 격자 분석")
    n_period = 64
    PO = {k: analyse_po_grid(POJ, k, phys[k], n_period) for k in KEYS}

    print("\n§4  널 분석")
    NU = analyse_nulls(NUJ, phys)
    LAD = ladder_from_null_control(NCJ)

    print("\n§5  Sionna ↔ PO 대조")
    CMP = {k: compare_engines(S[k], PO[k], k, n_period) for k in KEYS}
    for k in KEYS:
        print(f"   {k:10s} 거리별 prop 상관 평균 "
              + "  ".join(f"{R}m={CMP[k]['by_range'][R]['amp_corr_mean']}"
                          for R in ('1', '3', '10')))

    print("\n§5b 판정 잣대 교정")
    CAL_A = criterion_a_calibration(NU)
    print(f"   (a) 널 팔 {CAL_A['n_null_cells']} 칸 중 점화 {CAL_A['n_null_firing']} · "
          f"널 최대 {CAL_A['max_null_ac_over_noise_db']} dB (문턱 {CAL_A['threshold_db']}) "
          f"→ {'교정 OK' if CAL_A['criterion_a_is_calibrated'] else '⚠ 거짓양성 있음'}")
    IDEAL = ideal_reference(phys)
    print(f"   이상 점산란자 {IDEAL['n_pass']}/{IDEAL['n']} 칸이 같은 시험을 통과 "
          f"→ 시험 교정 {'OK' if IDEAL['test_is_calibrated'] else '실패'}")

    print("\n§6  판정")
    SHAPE = shape_reliability(SJ)
    GEOM = geometric_reference(GRJ, S, phys)
    TAIL = tail_excess(GRJ, S, PO)
    for k in KEYS:
        tb = TAIL.get("by_airframe", {}).get(k)
        if tb:
            print(f"   {k:10s} 기하 절벽 너머 꼬리 최대(중앙값): Sionna "
                  f"{tb['sionna_tail_max_db_median']} dB · PO {tb['po_tail_max_db_median']} dB "
                  f"· 기하 {tb['geometry_tail_max_db_median']} dB · "
                  f"−20 dB 위 칸 {tb['n_cells_sionna_tail_above_minus20']}/{tb['n_cells']}")
    for k in KEYS:
        g = GEOM["by_airframe"].get(k)
        if g:
            print(f"   {k:10s} 기하기준 대조: ±1 조화 일치 {g['n_within_1_bin']}/{g['n_cells']} "
                  f"(근거리 {g['n_near_within_1_bin']}/{g['n_near_cells']}) · "
                  f"빗 모양 코사인 중앙값 {g['comb_shape_cosine_median']}")
    verdicts = assemble_verdicts(S, NU, NCJ, LAD, phys, SHAPE)

    print("\n§7  그림")
    figs = {}
    try:
        lv = fig1_spectrograms(SJ, phys, S, PO, NU, f"{FIGDIR}/report15_f1")
        figs["f1"] = dict(path=f"{FIGDIR}/report15_f1", **_jsonable(lv))
        print("   f1 ✅")
    except Exception as e:
        figs["f1"] = dict(error=str(e)); print("   f1 ❌", e)
    try:
        fig2_flash_vs_ftip(SJ, phys, S, PO, GRJ, f"{FIGDIR}/report15_f2")
        figs["f2"] = dict(path=f"{FIGDIR}/report15_f2"); print("   f2 ✅")
    except Exception as e:
        figs["f2"] = dict(error=str(e)); print("   f2 ❌", e)
    try:
        fig3_paths_and_divergence(SJ, phys, S, PO, CMP, f"{FIGDIR}/report15_f3")
        figs["f3"] = dict(path=f"{FIGDIR}/report15_f3"); print("   f3 ✅")
    except Exception as e:
        figs["f3"] = dict(error=str(e)); print("   f3 ❌", e)

    J = dict(
        meta=dict(script="benchmark/report15_verdict.py + report15_verdict_build.py",
                  question=("Sionna 의 PathSolver 가, 로터를 돌려가며 다시 추적했을 때, "
                            "블레이드 마이크로도플러를 내는가"),
                  thresholds=dict(TH), inputs=src,
                  frequency_convention_ko=(
                      "한 주기(180°, 2날) N 등분 φ 격자의 DFT 빈 k = 주파수 k·f_flash. "
                      "f_flash = n_blades·f_rev. 스펙트럼은 f_flash 정수배에만 존재한다."),
                  ftip_convention_ko=(
                      "(b) 예측은 자세별 투영 f_tip = 2·v_tip·cos(el)/λ 다. 팁 속도는 로터면 "
                      "안에 있으므로 앙각이 크면 시선방향 성분이 줄어든다."),
                  stamp=time.strftime("%Y-%m-%d %H:%M:%S")),
        physics=phys,
        branch1_paths_doppler=branch1(PRJ, SJ),
        sionna=S, po=PO, nulls_vs_range=NU, resolution_ladder=LAD,
        ideal_reference=IDEAL,
        criterion_a_calibration=criterion_a_calibration(NU),
        spectrum_shape_reliability=SHAPE,
        geometric_phase_reference=GEOM,
        tail_excess=TAIL,
        flash_frequency_table=flash_frequency_table(S, PO, phys, IDEAL),
        path_count_census=path_count_census(S),
        engine_comparison=CMP, verdict=verdicts, figures=figs,
        self_check=self_check(SJ, S))
    J["conclusion"] = conclusion(J)
    print("\n§8  결론")
    print("  ", J["conclusion"]["text_ko"][:600])
    J["meta"]["seconds_total"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(_jsonable(J), f, ensure_ascii=False)
    print(f"\n✅ 저장 → {OUT_JSON}  ({J['meta']['seconds_total']:.0f}s)")
    return J


def branch1(PRJ, SJ) -> dict:
    """① Paths.doppler — 저장된 실측으로 재확인만."""
    out = dict(question="Paths.doppler 로 블레이드 마이크로도플러가 자동으로 나오나",
               answer="아니다", evidence={})
    m = (SJ.get("mini2") or {})
    A = m.get("A_doppler") if m else None
    if A is None:
        A = (load("report15_sionna_sweep_mini2.json") or {}).get("A_doppler")
    if A:
        out["evidence"]["velocity_dof_per_object"] = A.get("velocity_dof_per_object")
        out["evidence"]["max_dof"] = A.get("max_dof")
        out["evidence"]["doppler_nonzero_paths_static_scene"] = A.get("doppler_nonzero")
        out["evidence"]["n_paths"] = A.get("n_paths")
        out["evidence"]["verdict_text"] = A.get("verdict")
    if PRJ:
        for k in ("mini2", "matrice4e"):
            a = (PRJ.get("airframes") or {}).get(k, {})
            if "A_doppler" in a:
                out["evidence"][f"probe_{k}"] = a["A_doppler"]
    out["why_ko"] = ("SceneObject.velocity 는 객체당 성분 3개(강체 1벡터)뿐이다. 회전을 표현할 "
                     "자리가 없어, 프롭 그룹에 속도를 주면 프롭 경유 경로가 전부 같은 부호·같은 "
                     "크기의 도플러를 받는다 — 전진날/후퇴날이 갈리지 않는다.")
    return out


def assemble_verdicts(S, NU, NCJ, LAD, phys, SHAPE=None) -> dict:
    """기체별 판정 — ⛔ 칸 선택 규칙을 먼저 선언한다."""
    SHAPE = SHAPE or {}
    out = dict(rule_ko=(
        "칸 선택 규칙은 결과를 보기 전에 정한다. 네 가지를 낸다. "
        "① apriori_flash = 1 m / disc(el 75°) / prop — 블레이드 **정반사 글린트**가 물리적으로 "
        "가장 강해야 하는 자세(시선이 블레이드 면법선에 가깝다). "
        "② apriori_doppler = 1 m / hot(el 0°) / prop — **팁 도플러 확산**이 최대인 자세 "
        "(팁 속도가 시선 안에 온전히 들어온다). 이 둘은 서로 반대 자세이고, 그 사실 자체가 결과다. "
        "③ best_case = (a) 여유가 최대인 칸 — 변조가 가장 센 칸. "
        "④ best_overall = 통과한 기준 수가 최대인 칸(동률이면 (a) 여유로) — Sionna 에게 "
        "가장 유리한 최선조건 시험이다. 어느 것도 대표값이 아니며, 전 격자 표를 함께 남긴다."),
        by_airframe={}, by_cell={})

    #  ⭐ 널 바닥 = **같은 거리·같은 자세**의 널 팔이 내는 변조지수(무차원).
    #    널 팔이 여럿이면 가장 큰 것(=가장 보수적인 바닥)을 쓴다. 구 널과 원판 널을 다 본다.
    def null_floor(key, R):
        best, src = None, None
        for arm, A in (NU.get("arms") or {}).items():
            if A.get("role") not in ("null",):
                continue
            if A.get("drone") != key and not arm.endswith(key):
                #  mini2 널은 mini2 에만 쓴다(기하가 다르다)
                if A.get("drone") != key:
                    continue
            for ch in ("all", "prop"):
                c = A["by"].get(f"{R}/{ch}")
                if not c or c.get("empty") or c.get("modulation_index") is None:
                    continue
                if best is None or c["modulation_index"] > best:
                    best, src = float(c["modulation_index"]), f"{arm}/{ch}@R={R}m"
        if best is not None:
            return best, src
        return None, None

    lad = dict(min_pearson_r=LAD.get("min_pearson_r"),
               ptp_max_rel_change=LAD.get("ptp_max_rel_change"),
               scope_ko=LAD.get("scope_ko")) if LAD.get("available") else None

    for key in KEYS:
        cells = {}
        for ck, c in S[key].items():
            if c.get("empty") or c.get("mode") != "prod":
                continue
            nf, nsrc = null_floor(key, f"{c['range_m']:g}")
            v = judge(c, nf, lad, phys[key])
            v["b"] = c.get("judge_b")
            v["checks"]["b_flash_freq_matches_ftip"] = (c.get("judge_b") or {}).get("ok")
            #  재판정 (b 를 자세투영 예측으로 갈아끼웠으므로)
            ch = v["checks"]
            known = [x for x in ch.values() if x is not None]
            if not ch["a_modulation_above_noise"]:
                v["verdict"] = "NO_MODULATION"
            elif all(known):
                v["verdict"] = "SIONNA_NATIVE_OK"
            elif not any(x for k2, x in ch.items()
                         if k2 != "a_modulation_above_noise" and x is not None):
                v["verdict"] = "ARTIFACT"
            else:
                v["verdict"] = "MIXED"
            v["broken"] = sorted(k2 for k2, x in ch.items() if x is False)
            v["b_shape_invariant_at_this_range"] = (
                ((SHAPE.get("by_airframe", {}).get(key) or {})
                 .get("invariant_by_range") or {}).get(f"{c['range_m']:g}"))
            v.update(range_m=c["range_m"], aspect=c["aspect"], channel=c["channel"],
                     null_floor_modulation_index=_f(nf), null_floor_source=nsrc,
                     modulation_index=c.get("modulation_index"),
                     modulation_ptp_db=c.get("modulation_ptp_db"),
                     ac_over_noise_db=c.get("ac_over_noise_db"),
                     n_paths_behaviour=c.get("n_paths_behaviour"))
            cells[ck] = v
        out["by_cell"][key] = cells

        prop = {k: v for k, v in cells.items() if v["channel"] == "prop"}

        def _n_pass(v):
            return sum(1 for x in v["checks"].values() if x is True)

        best = max((v for v in prop.values() if v.get("ac_over_noise_db") is not None),
                   key=lambda v: v["ac_over_noise_db"], default=None)
        best_all = max((v for v in prop.values() if v.get("ac_over_noise_db") is not None),
                       key=lambda v: (_n_pass(v), v["ac_over_noise_db"]), default=None)
        tally = {}
        for v in prop.values():
            tally[v["verdict"]] = tally.get(v["verdict"], 0) + 1

        def _wrap(ck, v):
            return dict(key=ck, verdict=v, n_checks_passed=_n_pass(v)) if v else None

        out["by_airframe"][key] = dict(
            apriori_flash_cell=_wrap("1/disc/prod/prop", prop.get("1/disc/prod/prop")),
            apriori_doppler_cell=_wrap("1/hot/prod/prop", prop.get("1/hot/prod/prop")),
            best_case_cell=(_wrap(next(k for k, v in prop.items() if v is best), best)
                            if best else None),
            best_overall_cell=(_wrap(next(k for k, v in prop.items() if v is best_all),
                                     best_all) if best_all else None),
            prop_channel_tally=tally, n_cells=len(prop),
            n_cells_all_four_pass=sum(1 for v in prop.values()
                                      if all(x is True for x in v["checks"].values())),
            any_native_ok=bool(any(v["verdict"] == "SIONNA_NATIVE_OK" for v in prop.values())),
            headline_verdict=(best_all or {}).get("verdict"))
    return out


def geometric_reference(GR, S, phys) -> dict:
    """⭐⭐ **결정적 대조** — 같은 메쉬로 위상만 더한 기준(report15_verdict_geomref.py)과
    Sionna 의 빗을 겹친다.

    기하 기준은 산란 물리를 전부 뺀 것이다(진폭·재질·법선·가림 없음, 가중치 균일).
    남은 것은 '움직이는 기하가 만드는 왕복 위상' 뿐이다. Sionna 의 빗이 여기에 맞으면
    Sionna 는 회전하는 기하의 위상을 제대로 따라가고 있는 것이고, 그 빗은 몬테카를로
    표본 잡음의 산물이 아니다. 어긋나면 그 반대다.

    ⭐ 운동학 f_tip(=팁 점 하나) 보다 **이쪽이 더 옳은 기준**이다 — 실제 블레이드는 점이
      아니라 코드·피치·허브를 가진 면이라, 요구되는 조화 수가 점 모형과 조금 다르다."""
    out = dict(available=bool(GR), by_cell={}, by_airframe={})
    if not GR:
        return out
    for key in KEYS:
        A = (GR.get("airframes") or {}).get(key)
        if not A:
            continue
        rows, diffs = {}, []
        for ck, g in A["by_cell"].items():
            R, ak = ck.split("/")
            c = S[key].get(f"{R}/{ak}/prod/prop")
            if not c or c.get("empty"):
                continue
            sb, gb = c.get("edge_bin"), g.get("edge_bin")
            d = (int(sb) - int(gb)) if (sb and gb) else None
            if d is not None:
                diffs.append(abs(d))
            #  빗 **모양** 전체도 비교한다(가장자리 한 점보다 정보가 많다)
            hs = np.asarray(c["harm_abs"], float)
            hg = np.asarray(g["harm_abs"], float)
            m = min(len(hs), len(hg))
            cos = (float(np.dot(hs[:m], hg[:m])
                         / (np.linalg.norm(hs[:m]) * np.linalg.norm(hg[:m])))
                   if hs[:m].any() and hg[:m].any() else None)
            rows[f"{key}/{ck}"] = dict(
                drone=key, range_m=g["range_m"], aspect=ak,
                sionna_edge_bin=sb, geometry_edge_bin=gb, edge_bin_diff=d,
                sionna_f_edge_hz=c.get("f_edge_hz"), geometry_f_edge_hz=g.get("f_edge_hz"),
                geometry_edge_over_kinematic=g.get("edge_over_pred"),
                sionna_over_geometry=(_f(c["f_edge_hz"] / g["f_edge_hz"])
                                      if c.get("f_edge_hz") and g.get("f_edge_hz") else None),
                comb_shape_cosine=_f(cos),
                agrees_within_1_bin=(bool(abs(d) <= 1) if d is not None else None))
        out["by_cell"].update(rows)
        ok = [r for r in rows.values() if r["agrees_within_1_bin"] is not None]
        near = [r for r in rows.values()
                if r["range_m"] in (1.0, 3.0) and r["agrees_within_1_bin"] is not None]
        cs = [r["comb_shape_cosine"] for r in rows.values()
              if r["comb_shape_cosine"] is not None]
        out["by_airframe"][key] = dict(
            n_cells=len(ok),
            n_within_1_bin=sum(1 for r in ok if r["agrees_within_1_bin"]),
            median_abs_edge_diff=_f(np.median([abs(r["edge_bin_diff"]) for r in ok]))
            if ok else None,
            n_near_cells=len(near),
            n_near_within_1_bin=sum(1 for r in near if r["agrees_within_1_bin"]),
            comb_shape_cosine_median=_f(np.median(cs)) if cs else None)
    out["note_ko"] = (
        "Sionna 의 빗이 기하 기준과 ±1 조화 안에서 맞으면, 스톡 PathSolver 는 회전하는 "
        "기하의 왕복 위상을 제대로 따라간다는 뜻이다. 근거리(1·3 m)에서 특히 그렇고, "
        "R=10 m 에서 벌어지는 것은 광선예산이 줄어 빗의 꼬리가 잡음에 먹히기 때문이다.")
    return out


def tail_excess(GR, S, PO) -> dict:
    """⚠ **기하가 요구하지 않는 꼬리**가 있는가 — 있다면 그것이 (b) 를 오염시킨다.

    기하 기준의 가장자리 빈 너머(k > edge_geom)에서 각 엔진의 조화가 첨두 대비 몇 dB 인지 잰다.
      · 기하 기준     : 정의상 거기서 절벽이다(참조점)
      · 우리 PO       : 몬테카를로도 가림도 없다 → 꼬리가 없어야 한다
      · Sionna        : 꼬리가 있으면, 그 꼬리는 **움직이는 기하가 아닌 것**에서 온다
                        (확산 표본추출·면 가시성 전환 등)
    ⭐ 이것이 mini2 의 (b) 실패를 설명하는 자리다. 꼬리가 −20 dB 문턱 위로 올라오면
      가장자리 판정이 물리적 절벽이 아니라 그 꼬리를 집는다."""
    out = dict(by_cell={}, by_airframe={})
    if not GR:
        return dict(out, available=False)
    for key in KEYS:
        A = (GR.get("airframes") or {}).get(key)
        if not A:
            continue
        rows = {}
        for ck, g in A["by_cell"].items():
            R, ak = ck.split("/")
            ge = g.get("edge_bin")
            if not ge:
                continue

            def tail(c):
                if not c or c.get("empty"):
                    return None
                a = np.asarray(c["harm_abs"], float)
                if a.max() <= 0 or len(a) <= ge:
                    return None
                t = 20 * np.log10(a[ge:] / a.max() + 1e-12)
                return dict(mean_db=_f(float(np.mean(t))), max_db=_f(float(np.max(t))),
                            n_bins=int(t.size),
                            n_above_minus20=int(np.sum(t >= -20.0)))

            sc = S[key].get(f"{R}/{ak}/prod/prop")
            pc = PO[key].get(f"matched/{R}/{ak}/prop")
            gt = tail(dict(harm_abs=g["harm_abs"]))
            rows[f"{key}/{ck}"] = dict(
                drone=key, range_m=g["range_m"], aspect=ak,
                geometry_edge_bin=ge,
                sionna_tail=tail(sc), po_tail=tail(pc), geometry_tail=gt,
                sionna_n_paths=(sc or {}).get("n_paths_mean"),
                sionna_tail_contaminates_edge=(
                    bool(tail(sc)["n_above_minus20"] > 0) if tail(sc) else None))
        out["by_cell"].update(rows)
        st_ = [r["sionna_tail"]["max_db"] for r in rows.values()
               if r.get("sionna_tail") and r["sionna_tail"]["max_db"] is not None]
        pt = [r["po_tail"]["max_db"] for r in rows.values()
              if r.get("po_tail") and r["po_tail"]["max_db"] is not None]
        gtl = [r["geometry_tail"]["max_db"] for r in rows.values()
               if r.get("geometry_tail") and r["geometry_tail"]["max_db"] is not None]
        out["by_airframe"][key] = dict(
            sionna_tail_max_db_median=_f(np.median(st_)) if st_ else None,
            po_tail_max_db_median=_f(np.median(pt)) if pt else None,
            geometry_tail_max_db_median=_f(np.median(gtl)) if gtl else None,
            n_cells_sionna_tail_above_minus20=sum(
                1 for r in rows.values() if r.get("sionna_tail_contaminates_edge")),
            n_cells=len(rows))
    out["available"] = True
    out["note_ko"] = (
        "Sionna 의 꼬리가 PO·기하 기준보다 뚜렷하게 높으면, (b) 의 '가장자리' 는 물리적 "
        "절벽이 아니라 그 꼬리를 집은 것이다. 경로수가 적은 기체·거리에서 더 심하다 — "
        "즉 (b) 실패는 '메쉬가 나쁘다' 가 아니라 '광선예산 대비 표적이 작다' 는 뜻이다.")
    return out


def shape_reliability(SJ) -> dict:
    """⚠ (b) 의 '가장자리' 가 물리적 절벽이 아니라 **몬테카를로 잡음이 삼킨 지점**일 수 있다.

    그 구별은 광선예산을 바꿔 보면 된다: 예산을 16 배 늘려도 스펙트럼 **모양**이 그대로면
    가장자리는 물리다. 이미 matrice4e 스윕이 그것을 쟀으므로(shape_invariance) 여기로
    끌어와 거리별 신뢰도 표식으로 붙인다. 이 측정이 없는 거리·기체는 그렇다고 적는다."""
    out = dict(by_airframe={}, note_ko=(
        "coherent_shape_cosine 이 1 에 가까우면 예산을 바꿔도 조화 모양이 안 바뀐다 "
        "= 그 거리에서 상대 도플러 스펙트럼을 읽어도 된다(절대 레벨은 여전히 불가). "
        "낮으면 그 거리의 (b) 판정은 잡음에 물든 것으로 읽어야 한다."))
    for key in KEYS:
        J = SJ.get(key) or {}
        h = J.get("headline") or {}
        si = J.get("shape_invariance") or {}
        out["by_airframe"][key] = dict(
            measured=bool(h.get("coherent_shape_cosine_by_range")),
            cosine_by_range=h.get("coherent_shape_cosine_by_range"),
            invariant_by_range=h.get("coherent_shape_invariant_by_range"),
            ranges_where_invariant=h.get("ranges_where_coherent_shape_invariant"),
            spp_ladder=si.get("spps"), spp_span=si.get("spp_span"),
            source=f"outputs/{SIONNA_SRC[key]}:shape_invariance")
    return out


def criterion_a_calibration(NU) -> dict:
    """⭐ (b) 를 이상 모형으로 교정했듯이, (a) 도 **널 팔로 교정**한다.

    널 팔(구·원판·로터제거)에 판정 (a) 를 그대로 걸어 본다. 널에서 (a) 가 켜지면
    문턱이 느슨한 것이고, 그 문턱으로 얻은 '통과' 는 아무 뜻이 없다.
    반대로 널이 전부 조용하면 (a) 는 이 실험에서 거짓양성을 내지 않는다는 실측 증거가 된다."""
    rows = {}
    for arm, A in (NU.get("arms") or {}).items():
        for rk, c in A.get("by", {}).items():
            if not isinstance(c, dict) or c.get("empty") or "ac_over_noise_db" not in c:
                continue
            v = c.get("ac_over_noise_db")
            rows[f"{arm}/{rk}"] = dict(
                arm=arm, role=A.get("role"), expect_modulation=A.get("expect_modulation"),
                ac_over_noise_db=v, modulation_index=c.get("modulation_index"),
                modulation_ptp_db=c.get("modulation_ptp_db"),
                fires=(bool(v >= TH["margin_db_min"]) if v is not None else None))
    nulls = [r for r in rows.values() if r["role"] == "null"]
    sigs = [r for r in rows.values() if r["role"] == "signal"]
    n_fire = sum(1 for r in nulls if r["fires"])
    return dict(rows=rows, n_null_cells=len(nulls), n_null_firing=n_fire,
                n_signal_cells=len(sigs),
                n_signal_firing=sum(1 for r in sigs if r["fires"]),
                max_null_ac_over_noise_db=_f(max((r["ac_over_noise_db"] for r in nulls
                                                  if r["ac_over_noise_db"] is not None),
                                                 default=None)),
                threshold_db=TH["margin_db_min"],
                criterion_a_is_calibrated=bool(nulls and n_fire == 0),
                note_ko=("널 팔에서 (a) 가 한 번도 안 켜지면 이 문턱은 이 실험에서 거짓양성을 "
                         "내지 않는다. 켜지면 그 아래 '통과' 는 전부 무효다."))


def flash_frequency_table(S, PO, phys, IDEAL) -> dict:
    """⭐ 내야 할 것 ② — 플래시 주파수 vs f_tip 표. (b) 판정선이 이 표다."""
    rows = []
    for key in KEYS:
        ph = phys[key]
        for R in ("1", "3", "10"):
            for ak in ASPECT_ORDER:
                el = _ASPECT_EL[ak]
                ic = IDEAL["by_cell"].get(f"{key}/{ak}", {})
                for src, c in (("sionna", S[key].get(f"{R}/{ak}/prod/prop")),
                               ("po", PO[key].get(f"matched/{R}/{ak}/prop"))):
                    if not c or c.get("empty"):
                        continue
                    jb = c.get("judge_b") or {}
                    rows.append(dict(
                        drone=key, range_m=float(R), aspect=ak, el_deg=el, source=src,
                        channel="prop",
                        f_rev_hz=_f(ph["f_rev_hz"]), f_flash_hz=_f(ph["f_flash_hz"]),
                        f_tip_broadside_hz=_f(ph["f_tip_hz"]),
                        f_tip_predicted_hz=_f(c["ftip"]["f_tip_aspect_hz"]),
                        predicted_bins=_f(c["ftip"]["in_flash_bins"]),
                        measured_peak_bin=c.get("peak_bin"),
                        measured_peak_hz=c.get("f_peak_hz"),
                        measured_edge_bin=c.get("edge_bin"),
                        measured_edge_hz=c.get("f_edge_hz"),
                        edge_over_predicted=jb.get("ratio"),
                        b_pass=jb.get("ok"),
                        b_reason=jb.get("reason"),
                        ideal_edge_hz=ic.get("f_edge_hz"),
                        ideal_edge_over_predicted=(ic.get("calibration") or {}).get("ratio"),
                        test_calibrated=(ic.get("calibration") or {}).get("passes_same_test")))
    ok = [r for r in rows if r["b_pass"] is True]
    bad = [r for r in rows if r["b_pass"] is False]
    unk = [r for r in rows if r["b_pass"] is None]
    def _agg(src):
        v = [r["edge_over_predicted"] for r in rows
             if r["source"] == src and r["edge_over_predicted"] is not None
             and r["b_pass"] is not None]
        return dict(n=len(v), median_ratio=_f(np.median(v)) if v else None,
                    mean_ratio=_f(np.mean(v)) if v else None)
    return dict(columns_ko=("drone·range·aspect·source 마다: 운동학 예측 f_tip(자세투영) 대비 "
                            "실측 스펙트럼 가장자리. b_pass 가 (b) 판정."),
                rows=rows, n_rows=len(rows), n_pass=len(ok), n_fail=len(bad),
                n_uncalibrated=len(unk),
                by_source=dict(sionna=_agg("sionna"), po=_agg("po")),
                by_airframe={k: dict(
                    n=sum(1 for r in rows if r["drone"] == k),
                    n_pass=sum(1 for r in rows if r["drone"] == k and r["b_pass"] is True),
                    sionna_median_ratio=_f(np.median(
                        [r["edge_over_predicted"] for r in rows
                         if r["drone"] == k and r["source"] == "sionna"
                         and r["edge_over_predicted"] is not None] or [np.nan])))
                    for k in KEYS})


def path_count_census(S) -> dict:
    """⭐ 내야 할 것 ③ — 경로수가 위상에 따라 연속인가 껐다 켜지나(톱니 판정)."""
    out = dict(diffuse={}, specular={}, summary={})
    for key in KEYS:
        for ck, c in S[key].items():
            if c.get("mode") not in ("prod", "spec"):
                continue
            tgt = out["diffuse"] if c["mode"] == "prod" else out["specular"]
            if c.get("empty"):
                tgt[f"{key}/{ck}"] = dict(drone=key, empty=True, n_paths_max=0,
                                          behaviour="모든 칸에서 경로 0",
                                          toggles=0, zero_frac=1.0)
                continue
            y = np.asarray(c["n_paths_by_phase"], float)
            on = y > 0
            toggles = int(np.sum(on[1:] != on[:-1]))
            tgt[f"{key}/{ck}"] = dict(
                drone=key, range_m=c["range_m"], aspect=c["aspect"], channel=c["channel"],
                empty=False, n_paths_mean=c.get("n_paths_mean"),
                n_paths_min=c.get("n_paths_min"), n_paths_max=c.get("n_paths_max"),
                n_paths_cv=c.get("n_paths_cv"), zero_frac=c.get("zero_path_frac"),
                behaviour=c.get("n_paths_behaviour"),
                toggles=toggles,
                relative_swing=_f((y.max() - y.min()) / y.mean()) if y.mean() > 0 else None)
    for nm, D in (("diffuse", out["diffuse"]), ("specular", out["specular"])):
        live = [v for v in D.values() if not v.get("empty")]
        out["summary"][nm] = dict(
            n_cells=len(D), n_empty=sum(1 for v in D.values() if v.get("empty")),
            n_continuous=sum(1 for v in live if v.get("zero_frac") == 0),
            n_toggling=sum(1 for v in live if (v.get("zero_frac") or 0) > 0),
            max_toggles=max([v["toggles"] for v in live], default=0),
            max_relative_swing=_f(max([v["relative_swing"] for v in live
                                       if v.get("relative_swing") is not None], default=0)))
    out["verdict_ko"] = (
        "확산 채널: " + ("껐다켜짐 없음(연속)" if out["summary"]["diffuse"]["n_toggling"] == 0
                       else f"{out['summary']['diffuse']['n_toggling']} 칸에서 껐다켜짐")
        + " / 정반사 채널: "
        + (f"{out['summary']['specular']['n_empty']}/{out['summary']['specular']['n_cells']} 칸이 "
           f"통째로 비어 있고, {out['summary']['specular']['n_toggling']} 칸이 껐다켜진다"))
    return out


def conclusion(J) -> dict:
    """⭐ 내야 할 것 ⑤ — 결론 한 문단. ⛔ 숫자는 전부 J 에서 꺼내 쓴다(손입력 금지)."""
    V = J["verdict"]["by_airframe"]
    FT = J["flash_frequency_table"]
    PC = J["path_count_census"]
    CMP = J["engine_comparison"]
    parts = []
    for key in KEYS:
        v = V.get(key) or {}
        bo = (v.get("best_overall_cell") or {}).get("verdict") or {}
        af = (v.get("apriori_flash_cell") or {}).get("verdict") or {}
        ad = (v.get("apriori_doppler_cell") or {}).get("verdict") or {}
        parts.append(
            f"[{key}] 최선조건 칸 {(v.get('best_overall_cell') or {}).get('key')} 판정 "
            f"{bo.get('verdict')} (a 여유 {bo.get('a_margin_db')} dB, "
            f"b 가장자리/예측 {(bo.get('b') or {}).get('ratio')}, "
            f"c 널대비 {bo.get('c_null_margin_db')} dB) · "
            f"선험 글린트칸 1/disc {af.get('verdict')} · "
            f"선험 도플러칸 1/hot {ad.get('verdict')} · "
            f"prop 채널 {v.get('n_cells')} 칸 집계 {v.get('prop_channel_tally')} · "
            f"네 기준 전부 통과 {v.get('n_cells_all_four_pass')} 칸")
    corr = {k: CMP[k]["by_range"] for k in KEYS}
    GEO = J.get("geometric_phase_reference") or {}
    TL = J.get("tail_excess") or {}
    CA = J.get("criterion_a_calibration") or {}
    gb = GEO.get("by_airframe") or {}
    tb = TL.get("by_airframe") or {}
    text = (
        "① `Paths.doppler` 로는 안 나온다 — SceneObject.velocity 가 객체당 강체 1벡터라 "
        "회전을 표현할 자리 자체가 없다. 프롭에 속도를 주면 프롭 경유 경로가 전부 같은 부호·"
        "같은 크기의 도플러를 받는다(전진날/후퇴날이 안 갈린다). 이건 재확인으로 끝났다. "
        "② 로터 위상을 스텝하고 매번 재추적하면 — **나온다, 단 확산 채널에서만.** "
        f"경로수 거동은 {PC['verdict_ko']} — 우려했던 '삼각형 배치가 만드는 톱니' 는 "
        "확산 채널에 없다. "
        "가장 강한 증거는 운동학 f_tip 이 아니라 **기하 위상 기준**이다: 같은 메쉬로 "
        "산란 물리를 전부 빼고 왕복 위상만 더한 빗과 Sionna 의 빗을 겹치면, 근거리(1·3 m)에서 "
        + " / ".join(f"{k} {gb[k]['n_near_within_1_bin']}/{gb[k]['n_near_cells']} 칸이 ±1 조화 "
                     f"안에서 일치(빗 모양 코사인 중앙값 {gb[k]['comb_shape_cosine_median']})"
                     for k in KEYS if k in gb)
        + ". 즉 스톡 PathSolver 는 **회전하는 기하의 왕복 위상을 제대로 따라간다**. "
        "그 빗은 몬테카를로 잡음의 산물이 아니다. "
        "반면 블레이드 정반사(글린트)는 사실상 없다 — 정반사 채널은 "
        f"{PC['summary']['specular']['n_empty']}/{PC['summary']['specular']['n_cells']} 칸이 "
        "통째로 비어 있고, 켜지는 몇 칸은 연속 변조가 아니라 껐다켜짐이다. "
        f"판정 잣대는 교정했다: 널 팔 {CA.get('n_null_cells')} 칸에서 (a) 가 한 번도 안 켜지고"
        f"(최대 {CA.get('max_null_ac_over_noise_db')} dB < 문턱 {CA.get('threshold_db')}), "
        f"이상 점산란자는 {(J.get('ideal_reference') or {}).get('n_pass')}/"
        f"{(J.get('ideal_reference') or {}).get('n')} 칸에서 (b) 를 통과한다. "
        + " · ".join(parts) + ". "
        "⭐ 두 기체가 갈리는 이유는 **메쉬 품질이 아니라 표적 크기 대비 광선예산**이다: "
        "기하 절벽 너머 꼬리의 최대값(중앙값)이 "
        + " / ".join(f"{k} Sionna {tb[k]['sionna_tail_max_db_median']} dB vs PO "
                     f"{tb[k]['po_tail_max_db_median']} dB (−20 dB 문턱 위 "
                     f"{tb[k]['n_cells_sionna_tail_above_minus20']}/{tb[k]['n_cells']} 칸)"
                     for k in KEYS if k in tb)
        + " 이고, mini2 는 프롭 경로가 matrice4e 의 6분의 1 수준이라 그 꼬리가 −20 dB 가장자리 "
        "판정을 오염시킨다. mini2 는 Das 실측으로 검증된 기준자이므로, 이 차이를 '메쉬 탓' 으로 "
        "읽으면 안 된다. "
        f"두 엔진 일치도(prop 채널, 복소 AC 상관)는 거리별로 "
        + " / ".join(f"{k}: " + ", ".join(f"{R}m={corr[k][R]['complex_corr_mean']}"
                                          for R in ('1', '3', '10')) for k in KEYS)
        + " — 근거리에서 좁혀지는가는 "
        + " / ".join(f"{k} {CMP[k]['improves_at_near_range']}" for k in KEYS) + ".")
    return dict(text_ko=text, per_airframe=parts,
                caveats_ko=[
                    "이 결론의 변조는 전부 **확산 채널**에서 나온다. 그 코히런트 합은 Sionna "
                    "확산모델의 몬테카를로 표본합이므로, 절대값을 물리적 산란장으로 읽는 데는 "
                    "여전히 유보가 필요하다(시드 재추첨만으로 흔들린다).",
                    "max_depth=1 이라 블레이드↔동체 다중산란이 없다.",
                    "네 로터를 같은 위상으로 돌린다(위상 잠금). 실제 기체는 그렇지 않다 — "
                    "실측과 맞추려면 로터별 위상·회전수 분산을 넣어야 한다.",
                    "matrice4e 는 R=1·3 m 에서 원거리장 미달이다(2D²/λ = 8.26 m). RT 는 구면파를 "
                    "추적하므로 계산은 유효하지만 이 |h| 를 σ(RCS) 로 환산해 인용하면 안 된다.",
                    "matrice4e 는 실물 대조에서 남은 최대 불일치 1·2위가 모터·프롭 근처다 "
                    "(모터는 실물이 더 크고 프롭은 메쉬가 더 크다). 이번 실험이 흔든 부위가 "
                    "정확히 거기이므로, 이 기체의 수치를 실측 검증 근거로 쓰려면 그 불일치를 "
                    "먼저 닫아야 한다.",
                    "mini2 는 Das 실측 4기체 대조에서 1위(ΔL −0.51 dB)인 검증된 기준자이고 "
                    "matrice4e 는 실측 σ 로 검증된 적이 없다 — 두 기체가 갈리면 그 방향이 "
                    "'메쉬 품질'인지 '기체 크기'인지를 가른다.",
                    "기하 위상 기준은 산란 물리를 뺀 **위상만의** 기준이다. Sionna 가 그것과 "
                    "맞는다는 것은 '위상을 옳게 추적한다' 는 뜻이지 '산란 진폭이 옳다' 는 "
                    "뜻이 아니다. 절대 σ 는 여전히 우리 PO 커널이 담당한다.",
                    "R=10 m 에서는 광선예산이 줄어 빗의 꼬리가 잡음에 먹힌다 — 그 거리의 (b) "
                    "판정은 물리가 아니라 예산을 잰 것이다(스펙트럼 모양 불변성도 그 거리에서 "
                    "깨진다).",
                    "정반사 채널에서 프롭 경로가 켜지는 몇 칸은 위상축에서 **껐다켜진다** — "
                    "연속 변조가 아니다. 교과서적 블레이드 플래시를 원하면 스톡 PathSolver "
                    "로는 안 되고, 그것이 우리가 PO/SBR 커널을 따로 두는 이유다."])


def self_check(SJ, S) -> dict:
    """⭐ 이식한 harm_seeded 가 matrice4e 스크립트(_harm_seeded)의 저장값을 재현하는가.

    저장물의 `two_sided_complex.blade_flash` 는 복소 h 의 ±1 조화 크기다 — 내 FFT 정규화와
    시드 평균 규약이 원본과 같은지 **직접** 재는 자리다. 여기가 어긋나면 이 판정의
    주파수 해석이 전부 어긋난다."""
    out = dict(what="이식한 harm_seeded 가 원본 _harm_seeded 의 저장값(two_sided_complex)을 "
                    "재현하는가", rows={})
    J = SJ.get("matrice4e")
    if not J or "modulation_depth" not in J or "grid" not in J:
        return dict(out, available=False)
    md = J["modulation_depth"].get("by_block", {})
    G = J["grid"]["blocks"]
    n, worst = 0, 0.0
    for bk, ref in md.items():
        ts = (ref or {}).get("two_sided_complex") or {}
        bf = ts.get("blade_flash") or {}
        if "plus_abs" not in bf or "minus_abs" not in bf:
            continue
        blk, ch = bk.rsplit("/", 1)
        if blk not in G:
            continue
        z, npth = block_wave(G[blk], ch)
        if npth.max() == 0:
            continue
        H = harm_seeded(z)
        got_p, got_m = H["plus_abs"][0], H["minus_abs"][0]
        exp_p, exp_m = float(bf["plus_abs"]), float(bf["minus_abs"])
        d = max(abs(got_p - exp_p) / max(exp_p, 1e-300),
                abs(got_m - exp_m) / max(exp_m, 1e-300))
        worst = max(worst, d)
        n += 1
        if n <= 4:
            out["rows"][bk] = dict(stored_plus=_f(exp_p), recomputed_plus=_f(got_p),
                                   stored_minus=_f(exp_m), recomputed_minus=_f(got_m),
                                   max_rel_diff=_f(d))
    out.update(available=bool(n), n_compared=int(n), max_rel_diff=_f(worst),
               reproduces=bool(n and worst < 1e-9),
               note_ko=("상대차가 1e−9 미만이면 두 구현이 같은 함수다. 어긋나면 그 아래 "
                        "모든 주파수 해석을 의심해야 한다."))
    return out


def figures_only() -> dict:
    """⭐ **그림만** 다시 그린다 — outputs/report15_verdict.json 은 건드리지 않는다.

    왜 따로 두나: 표시 규약을 고칠 때마다 판정 JSON 을 다시 쓰면, 그림 손질과 숫자 갱신이
    한 커밋에 섞여 «무엇 때문에 숫자가 움직였나» 를 못 가린다. 그림은 그림만 바꾼다.
    """
    phys = {k: physics(k) for k in KEYS}
    SJ = {k: load(SIONNA_SRC[k]) for k in KEYS}
    POJ = load("report15_verdict_po_grid.json")
    NUJ = load("report15_verdict_nulls_vs_range.json")
    GRJ = load("report15_verdict_geomref.json")
    S = {k: analyse_sionna(SJ[k], phys[k]) for k in KEYS}
    PO = {k: analyse_po_grid(POJ, k, phys[k], 64) for k in KEYS}
    NU = analyse_nulls(NUJ, phys)
    CMP = {k: compare_engines(S[k], PO[k], k, 64) for k in KEYS}
    out = {}
    lv = fig1_spectrograms(SJ, phys, S, PO, NU, f"{FIGDIR}/report15_f1")
    out["f1"] = _jsonable(lv)
    print("   f1 ✅  패널", lv["n_panels"], "(옛 판", lv["n_panels_before"], ")",
          "· 대표 널", lv["representative_null"])
    fig2_flash_vs_ftip(SJ, phys, S, PO, GRJ, f"{FIGDIR}/report15_f2")
    print("   f2 ✅ (스펙트로그램 아님 — 조화 스펙트럼)")
    fig3_paths_and_divergence(SJ, phys, S, PO, CMP, f"{FIGDIR}/report15_f3")
    print("   f3 ✅ (스펙트로그램 아님 — 경로수·상관 꺾은선)")
    return out


if __name__ == "__main__":
    if "--figs" in sys.argv:
        figures_only()
    else:
        build()
