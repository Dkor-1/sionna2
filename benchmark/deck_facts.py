#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
deck_facts.py — 0804 팀미팅 덱이 인용해도 되는 **검증된 사실 기반**을 조립한다.

규칙(이 워크플로의 존재 이유):
  한 주장은 (a) 내가 직접 연 PDF 의 축자 문장이거나, (b) 디스크의 JSON 에서 우리가
  계산했고 재현 가능하거나, 둘 중 하나다. 나머지는 전부 UNVERIFIED 로 라벨하거나 뺀다.

이 스크립트가 하는 일:
  1. 상류 JSON 을 열어 **숫자를 매 실행마다 다시 계산**한다(하드코딩 금지).
  2. 각 사실에 self-check 를 붙여 소스와 어긋나면 build 가 실패를 보고한다.
  3. 인용문은 해당 PDF 페이지 텍스트에 실제로 있는지 재대조한다.
  4. outputs/deck_facts.json · docs/DECK_FACTS.md 를 쓴다.

실행:
  cd /workspace/sionna && \
  PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/deck_facts.py
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime

ROOT = "/workspace/sionna"
OUT_JSON = os.path.join(ROOT, "outputs", "deck_facts.json")
OUT_MD = os.path.join(ROOT, "docs", "DECK_FACTS.md")

C_EXACT = 299792458.0
C_ROUND = 3.0e8

# ────────────────────────────────────────────────────────────────────────────
# 0. 로딩 유틸
# ────────────────────────────────────────────────────────────────────────────
_cache: dict = {}


def J(name: str) -> dict:
    """outputs/<name>.json 을 읽는다."""
    if name not in _cache:
        p = os.path.join(ROOT, "outputs", f"{name}.json")
        with open(p, encoding="utf-8") as fh:
            _cache[name] = json.load(fh)
    return _cache[name]


def raw(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


PROBLEMS: list[str] = []
CHECKS: list[dict] = []


def check(cid: str, ok: bool, detail: str) -> bool:
    CHECKS.append({"id": cid, "passed": bool(ok), "detail": detail})
    if not ok:
        PROBLEMS.append(f"{cid}: {detail}")
    return bool(ok)


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(float(a) - float(b)) <= tol


# ────────────────────────────────────────────────────────────────────────────
# 1. 재계산 — 모든 헤드라인 숫자는 여기서 매번 다시 나온다
# ────────────────────────────────────────────────────────────────────────────
def vmax_half(lam: float, prf: float) -> float:
    """반쪽 구간 무모호 속도. Abratkiewicz 2023 eq.(16) 과 같은 규약."""
    return lam * prf / 4.0


def recompute() -> dict:
    R: dict = {}

    # ── V1 교차표준 표 (c = 3e8 규약, 선행과 같은 규약) ──────────────────
    stds = [
        ("LTE CRS", 1000.0, 1.843e9),
        ("WiFi VHT-LTF", 1000.0, 5.21e9),
        ("5G SSB", 50.0, 3.5e9),
        # 802.11 비컨 기본 주기 = 100 TU = 100 x 1024 us = 102.4 ms -> 9.765625 Hz
        ("WiFi beacon", 1.0 / 0.1024, 5.21e9),
    ]
    tbl = []
    for name, prf, fc in stds:
        tbl.append(
            {
                "waveform": name,
                "prf_hz": round(prf, 6),
                "fc_ghz": fc / 1e9,
                "v_max_half_ms_c3e8": vmax_half(C_ROUND / fc, prf),
                "v_max_half_ms_cexact": vmax_half(C_EXACT / fc, prf),
            }
        )
    R["vmax_table"] = tbl
    # 상류 기록(verify_chen)의 같은 표와 대조
    vc = J("verify_chen")
    up = {r["waveform"]: r for r in vc["reproductions_by_us"]["our_v1_table_recheck"]["rows"]}
    for row in tbl:
        u = up.get(row["waveform"])
        if u is None:
            check("V1.rowmatch", False, f"verify_chen 에 {row['waveform']} 행이 없다")
            continue
        check(
            f"V1.{row['waveform']}",
            approx(row["v_max_half_ms_c3e8"], u["vmax_half_ms_c_3e8"], 2e-3),
            f"{row['waveform']} c3e8 우리={row['v_max_half_ms_c3e8']:.6f} 상류={u['vmax_half_ms_c_3e8']:.6f}",
        )

    # ── Abratkiewicz eq.(16) 재현 ──────────────────────────────────────
    ab = []
    for T_ms, stated in ((20.0, 1.0901), (5.0, 4.3605)):
        prf = 1000.0 / T_ms
        ab.append(
            {
                "T_SSB_ms": T_ms,
                "prf_hz": prf,
                "fc_ghz": 3.44,
                "paper_states_ms": stated,
                "ours_c3e8_ms": vmax_half(C_ROUND / 3.44e9, prf),
                "ours_cexact_ms": vmax_half(C_EXACT / 3.44e9, prf),
            }
        )
    for r in ab:
        check(
            f"A16.{r['T_SSB_ms']}ms",
            round(r["ours_c3e8_ms"], 4) == r["paper_states_ms"],
            f"T={r['T_SSB_ms']} ms 논문={r['paper_states_ms']} 우리(c=3e8)={r['ours_c3e8_ms']:.4f}",
        )
    R["abratkiewicz_eq16"] = ab

    # ── 3GPP CSI-RS 천장 vs 실기체 최고속도 ─────────────────────────────
    ceiling_prf = 500.0
    fc = 3.5e9
    v_ceiling = vmax_half(C_EXACT / fc, ceiling_prf)
    speeds = J("vmax_grid")["drone_overlay"]["speed_axis"]["items"]
    airframes = {k: v for k, v in speeds.items() if k.endswith("_max")}
    covered = [k for k, v in airframes.items() if v <= v_ceiling]
    R["monostatic_ceiling"] = {
        "prf_hz": ceiling_prf,
        "fc_ghz": 3.5,
        "v_max_half_ms": v_ceiling,
        "airframe_max_speeds_ms": airframes,
        "n_airframes": len(airframes),
        "n_covered": len(covered),
        "slowest": min(airframes.items(), key=lambda kv: kv[1]),
    }
    check(
        "V4.coverage",
        len(covered) == 0 and len(airframes) == 5,
        f"천장 {v_ceiling:.3f} m/s 가 커버하는 기체 {len(covered)}/{len(airframes)}",
    )
    check(
        "V4.slowest",
        approx(min(airframes.values()), 13.5),
        f"가장 느린 기체 {min(airframes.items(), key=lambda kv: kv[1])}",
    )

    # ── 기하 무관성 (모노 == 바이 β=0) ────────────────────────────────
    p1 = J("geometry_grid")["axis_independence"]["P1_floor_is_geometry_independent"]
    diffs = {b: p1["by_band"][b]["abs_diff_ms"] for b in p1["by_band"]}
    R["geometry_independence"] = {
        "by_band": p1["by_band"],
        "max_abs_diff_ms": max(diffs.values()),
    }
    check("V5.zero", max(diffs.values()) == 0.0, f"밴드별 |모노-바이β0| = {diffs}")

    # ── 커널 정확도 ─────────────────────────────────────────────────
    kr = J("sbr_kr_sweep")
    R["kernel_accuracy"] = {
        "max_abs_db_vs_po": kr["summary_div16"]["max_abs_db_vs_po"],
        "max_abs_db_vs_mie": kr["summary_div16"]["max_abs_db_vs_mie"],
        "std_pct_vs_po_kr_ge30": kr["summary_div16"]["std_sbr_over_po_pct_kr_ge30"],
        "std_pct_vs_mie_kr_ge30": kr["summary_div16"]["std_sbr_over_mie_pct_kr_ge30"],
        "n_incidence": kr["meta"]["n_incidence"],
        "kr_min": kr["summary_div16"]["kr_min"],
        "kr_max": kr["summary_div16"]["kr_max"],
        "div": 16,
    }
    check(
        "V2.po",
        approx(R["kernel_accuracy"]["max_abs_db_vs_po"], 0.2005726178588444, 1e-9),
        f"max|dB| vs 해석 PO = {R['kernel_accuracy']['max_abs_db_vs_po']:.6f}",
    )

    # ── 앵커는 기울기만 옮긴다 (레벨 이동 0.00 dB) ─────────────────────
    sa = J("sigma_anchor")
    shifts, slopes_before, slopes_after = [], [], []
    for name, v in sa["drones"].items():
        so = v["modes"]["slope_only"]
        bef, aft = so["mu_before_dbsm"], so["mu_after_dbsm"]
        shifts.append((name, statistics.mean(aft[k] - bef[k] for k in bef)))
        slopes_before.append(so["slope_before_db_per_ghz"])
        slopes_after.append(so["slope_after_db_per_ghz"])
    R["anchor_slope_only"] = {
        "n_airframes": len(shifts),
        "mean_level_shift_db": statistics.mean(s for _, s in shifts),
        "max_abs_level_shift_db": max(abs(s) for _, s in shifts),
        "per_airframe_level_shift_db": {n: s for n, s in shifts},
        "slope_before_db_per_ghz_range": [min(slopes_before), max(slopes_before)],
        "slope_after_db_per_ghz": sorted(set(round(s, 6) for s in slopes_after)),
    }
    check(
        "V3.level",
        R["anchor_slope_only"]["max_abs_level_shift_db"] < 1e-9
        and R["anchor_slope_only"]["n_airframes"] == 7,
        f"7기체 레벨 이동 최대 |{R['anchor_slope_only']['max_abs_level_shift_db']:.2e}| dB",
    )

    # ── 밴드 기울기: 두 개의 서로 다른 적합 (규약을 밝혀야 한다) ─────────
    r02 = J("report02_derived")["band_slope"]
    # ⚠ 이 dict 에는 요약키(ours_min, ratio_max 등)가 섞여 있다. 기체별 값만 쓴다.
    band3 = dict(r02["ours_db_per_ghz"])
    check(
        "F24.band3_keys",
        len(band3) == 7
        and approx(min(band3.values()), r02["ours_min"])
        and approx(max(band3.values()), r02["ours_max"]),
        f"3밴드 적합 기체 {len(band3)}종, 범위 {min(band3.values()):.4f}~{max(band3.values()):.4f} "
        f"(기록값 {r02['ours_min']:.4f}~{r02['ours_max']:.4f})",
    )
    rca = J("rcs_anchor")["drones"]
    el0 = {k: v["regression"]["el0"]["a"] for k, v in rca.items()}
    n_pts = sorted(set(v["regression"]["el0"]["n_points"] for v in rca.values()))
    lit = {
        "das_phantom3_mono": sa["sources"]["das_phantom3_mono"]["slope_db_per_ghz"]
        if "sources" in sa and "das_phantom3_mono" in sa.get("sources", {})
        else J("psolve_diffraction")["our_p4_state_verified"]["band_slope"]["lit_das_db_per_ghz"],
        "yuan_azplane": J("psolve_diffraction")["our_p4_state_verified"]["band_slope"][
            "lit_mono3d_db_per_ghz"
        ],
    }
    census = J("psolve_diffraction")["our_p4_state_verified"]["measured_slope_census"][
        "values_db_per_ghz"
    ]
    R["band_slope"] = {
        "fit_A_3band_7airframes_db_per_ghz": band3,
        "fit_A_range": [min(band3.values()), max(band3.values())],
        "fit_B_22point_el0_7airframes_db_per_ghz": el0,
        "fit_B_range": [min(el0.values()), max(el0.values())],
        "fit_B_n_points": n_pts,
        "measured_anchor_db_per_ghz": lit,
        "measured_slope_census_db_per_ghz": census,
        "measured_census_range": [min(census), max(census)],
        "pure_f2_plate_limit_db_per_ghz": J("psolve_diffraction")["our_p4_state_verified"][
            "band_slope"
        ]["pure_f2_slope_over_this_band_db_per_ghz"],
        "ratio_fitA_over_das": [
            min(band3.values()) / lit["das_phantom3_mono"],
            max(band3.values()) / lit["das_phantom3_mono"],
        ],
    }
    check(
        "F24.two_fits",
        min(band3.values()) < min(el0.values()) and max(band3.values()) > max(el0.values()),
        f"3밴드 적합 {R['band_slope']['fit_A_range']} vs 22점 el0 적합 {R['band_slope']['fit_B_range']}",
    )

    # ── CFAR 몬테카를로 ────────────────────────────────────────────────
    cf = J("verify_cfar")["meta"]
    R["cfar"] = {
        "runtime_s": cf["runtime_s"],
        "n_maps_white": cf["n_maps_white"],
        "n_maps_chain": cf["n_maps_chain"],
        "M_cpi": cf["M_cpi"],
        "dtype": cf["dtype"],
        "pfa_nominal": cf["pfa_nominal"],
        "guard_train": cf["guard_train"],
    }
    aud = J("verify_cfar")["alpha_audit"]
    R["cfar"]["alpha_max_rel_err"] = max(v["rel_err"] for v in aud.values())
    R["cfar"]["alpha_configs"] = len(aud)
    check("V6.runtime", cf["runtime_s"] > 2700, f"몬테카를로 런타임 {cf['runtime_s']:.1f} s")

    # ── 아카이브 sweep ────────────────────────────────────────────────
    sc = J("reflib_sweep_sionna")["counts"]
    R["sionna_sweep"] = {
        "pdfs_unique": sc["pdfs_scanned_unique"],
        "mention_sionna": sc["mention_sionna"],
        "sionna_used": sc["sionna_used"],
        "target_in_scene_unique_works": sc["role_TARGET_IN_SCENE_unique_works"],
        "prints_dbsm_from_sionna": sc["prints_dbsm_from_sionna"],
        "state_a_sionna_version": sc["state_a_sionna_version"],
        "state_no_sionna_version": sc["state_no_sionna_version"],
        "published_verified_in_pdf": sc["published_verified_in_pdf"],
        "preprint": sc["preprint"],
    }
    check(
        "V7.dbsm",
        sc["prints_dbsm_from_sionna"] == 1,
        f"Sionna 로 dBsm 을 인쇄한 논문 {sc['prints_dbsm_from_sionna']}편",
    )
    check(
        "V7.target",
        sc["role_TARGET_IN_SCENE_unique_works"] == 6,
        f"씬에 표적을 세운 고유 저작 {sc['role_TARGET_IN_SCENE_unique_works']}편",
    )

    # ── H8 4관문 ─────────────────────────────────────────────────────
    h8 = J("report01_paper")["h8"]
    corp = J("report01_paper")["corpus"]
    R["h8"] = {
        "claim_en": h8["claim_ko"],
        "n_adjudicated": h8["n_adjudicated"],
        "n_passing_all_prongs": h8["n_passing_all_prongs"],
        "blocked_at_counts": h8["blocked_at_counts"],
        "corpus_documents": corp["documents"],
        "corpus_distinct_works": corp["distinct_works"],
        "corpus_swept_pdfs": corp["corpus_swept_pdfs"],
    }
    check(
        "F16.zero",
        h8["n_passing_all_prongs"] == 0 and h8["n_adjudicated"] == 12,
        f"H8 판정 {h8['n_adjudicated']}편 중 4관문 통과 {h8['n_passing_all_prongs']}편",
    )

    # ── 능력 매트릭스 ─────────────────────────────────────────────────
    cm = J("capability_matrix")
    lv = lambda r, c: r["cells"][c]["level"]
    cols = [c["id"] for c in cm["columns"]]
    scores = sorted(
        ((sum(1 for c in cols if lv(r, c) == 2), r["short"]) for r in cm["rows"]), reverse=True
    )
    six_full = ["engine", "mesh", "material", "aspect", "geometry", "vmax"]
    uniq = [r["short"] for r in cm["rows"] if all(lv(r, c) == 2 for c in six_full)]
    four = [
        r["short"]
        for r in cm["rows"]
        if all(lv(r, c) == 2 for c in ["engine", "mesh", "material", "aspect"])
    ]
    vmax_and_mesh = [
        (r["short"], lv(r, "vmax"), lv(r, "mesh"), lv(r, "validation"))
        for r in cm["rows"]
        if lv(r, "vmax") >= 1 and lv(r, "mesh") >= 1
    ]
    R["matrix"] = {
        "rows": cm["counts"]["rows"],
        "columns": cm["counts"]["columns"],
        "cells": cm["counts"]["cells"],
        "by_grade": cm["counts"]["by_grade"],
        "unverified_fraction": cm["counts"]["unverified_fraction"],
        "quote_selfcheck": cm["counts"]["quote_selfcheck"],
        "max_full_score": scores[0][0],
        "top_rows": [{"full": s, "row": n} for s, n in scores[:4]],
        "rows_with_9of9": [n for s, n in scores if s == 9],
        "diffraction_full_rows": cm["column_findings"]["diffraction"]["rows_full"],
        "diffraction_n_full": cm["column_findings"]["diffraction"]["n_full"],
        "rows_full_on_six": uniq,
        "rows_full_on_engine_mesh_material_aspect": four,
        "rows_with_vmax_and_mesh": vmax_and_mesh,
        "our_row": {c: cm["rows"][-1]["cells"][c]["mark"] for c in cols}
        if cm["rows"][-1]["short"].startswith("OURS")
        else None,
        "figures": cm["figures"],
    }
    check(
        "F13.no9",
        len(R["matrix"]["rows_with_9of9"]) == 0 and R["matrix"]["max_full_score"] == 6,
        f"9/9 채운 행 {len(R['matrix']['rows_with_9of9'])}개, 최다 {R['matrix']['max_full_score']}/9",
    )
    check(
        "F15.unique",
        uniq == ["OURS (sionna2)"],
        f"engine+mesh+material+aspect+geometry+vmax 6열 FULL 인 행: {uniq}",
    )
    check(
        "F14.diffraction",
        cm["column_findings"]["diffraction"]["n_full"] == 3,
        f"diffraction FULL {cm['column_findings']['diffraction']['n_full']}/26",
    )
    check(
        "F12.unverified",
        cm["counts"]["by_grade"]["UNVERIFIED"] == 0
        and cm["counts"]["quote_selfcheck"]["passed"] == cm["counts"]["quote_selfcheck"]["checked"],
        f"UNVERIFIED {cm['counts']['by_grade']['UNVERIFIED']}/{cm['counts']['cells']}, "
        f"인용 재대조 {cm['counts']['quote_selfcheck']['passed']}/{cm['counts']['quote_selfcheck']['checked']}",
    )

    # ── 접힘·CPI ─────────────────────────────────────────────────────
    cgv = J("cpi_guard_sweep")["verdict"]
    s2 = cgv["structural"]["s2_alias_floor"]
    s1 = cgv["structural"]["s1_equal_cpi_penalty"]
    R["alias"] = {
        "alias_frac_G1_5G": s2["alias_frac_G1"],
        "alias_frac_W1_wifi": s2["alias_frac_W1"],
        "alias_frac_L1_lte": s2["alias_frac_L1"],
        "blind_hard_by_cpi": s1["by_cpi"],
        "ratio_G1_over_W1_range": [
            min(r["ratio_G1_over_W1"] for r in s1["by_cpi"]),
            max(r["ratio_G1_over_W1"] for r in s1["by_cpi"]),
        ],
        "artifact": cgv["artifact"],
    }
    check(
        "F11.alias",
        s2["alias_frac_W1"] == 0.0 and s2["alias_frac_L1"] == 0.0,
        f"접힘비율 5G {s2['alias_frac_G1']:.3f} / WiFi 0 / LTE 0",
    )

    # ── φ 방위 민감도 (G5) ────────────────────────────────────────────
    gg = raw(os.path.join(ROOT, "outputs", "geometry_grid.json"))
    m = re.search(r'"absmax_over_phi_db":\s*([0-9.]+)', gg)
    R["phi_sensitivity"] = {
        "absmax_over_phi_db": float(m.group(1)) if m else None,
        "at_headline_phi90_db": 0.118,
        "headline_phi": "phi_90",
        "file": "src/experiment_freespace_range.py",
        "default_arg_lines": [322, 773],
    }
    check(
        "G5.phi",
        R["phi_sensitivity"]["absmax_over_phi_db"] is not None
        and R["phi_sensitivity"]["absmax_over_phi_db"] > 23.0,
        f"φ 최대 확산차 {R['phi_sensitivity']['absmax_over_phi_db']}",
    )

    # ── Sionna 설치본 실측 (한 줄로 재현되는 사실) ─────────────────────
    try:
        import sionna  # noqa
        import sionna.rt as srt

        rtdir = os.path.dirname(srt.__file__)
        ver = sionna.__version__
        n_rcs = int(
            subprocess.run(
                f"grep -rio '\\brcs\\b' {rtdir} --include=*.py | wc -l",
                shell=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            or 0
        )
        n_rcs_fn = int(
            subprocess.run(
                f"grep -rc 'radar_cross_section' {rtdir} --include=*.py | "
                f"awk -F: '{{s+=$2}} END {{print s+0}}'",
                shell=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            or 0
        )
        n_diff = int(
            subprocess.run(
                f"grep -rio 'diffract[a-z]*' {rtdir} --include=*.py | wc -l",
                shell=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            or 0
        )
        R["sionna_installed"] = {
            "version": ver,
            "rt_dir": rtdir,
            "rcs_word_hits": n_rcs,
            "radar_cross_section_hits": n_rcs_fn,
            "diffract_hits": n_diff,
        }
        check(
            "F21.no_rcs",
            n_rcs == 0 and n_rcs_fn == 0,
            f"sionna.rt {ver}: 'rcs' {n_rcs}회 · 'radar_cross_section' {n_rcs_fn}회",
        )
        check(
            "F22.has_diffraction",
            n_diff > 0,
            f"sionna.rt {ver}: 'diffract*' {n_diff}회 (있다 — 회절이 없다고 말하면 안 된다)",
        )
    except Exception as exc:  # pragma: no cover
        R["sionna_installed"] = {"error": str(exc)}
        check("F21.no_rcs", False, f"sionna import 실패: {exc}")

    # ── 우리 커널의 회절항 부재 ───────────────────────────────────────
    kern_hits = {}
    for f in ("src/rcs_sbr.py", "src/rcs_po.py"):
        s = raw(os.path.join(ROOT, f))
        kern_hits[f] = len(re.findall(r"diffract|\bPTD\b|\bUTD\b|creeping|fringe", s, re.I))
    R["our_kernel_diffraction"] = {
        "hits_by_file": kern_hits,
        "total_hits": sum(kern_hits.values()),
    }
    check(
        "F23.kernel",
        sum(kern_hits.values()) == 0,
        f"우리 RCS 커널의 회절/PTD/UTD/creeping/fringe 출현 {sum(kern_hits.values())}회",
    )

    # ── 회절 문헌 센서스 (코퍼스를 반드시 밝힌다) ───────────────────────
    mc = J("psolve_diffraction")["machine_census"]
    reflib = raw(os.path.join(ROOT, "outputs", "reference_library.json"))
    R["diffraction_census"] = {
        "corpus_A_217_pdfs": {
            "corpus": mc["corpus"],
            "by_term_papers_and_hits": mc["by_term_papers_and_hits"],
            "implement_beyond_stock_flag": mc["the_headline_count"],
            "sionna_using_and_mention_PTD": mc["sionna_using_and_mention_PTD"],
        },
        "corpus_B_reference_library_json_text": {
            "diffraction": len(re.findall(r"diffraction", reflib)),
            "diffract_star": len(re.findall(r"[Dd]iffract\w*", reflib)),
            "UTD": len(re.findall(r"\bUTD\b", reflib)),
            "PTD": len(re.findall(r"\bPTD\b", reflib)),
            "wedge": len(re.findall(r"[Ww]edge", reflib)),
        },
        "warning_ko": "두 코퍼스의 수를 한 문장에 섞으면 안 된다. 브리핑의 "
        "'diffraction 11회 · UTD 13회 · PTD 1회 · wedge 0회' 는 코퍼스 B(reference_library.json 텍스트)의 "
        "수이고, 그중 13 은 UTD 가 아니라 diffract* 였다. 코퍼스 A(217편 PDF)에서는 전혀 다른 수가 나온다.",
    }
    check(
        "F14b.census",
        R["diffraction_census"]["corpus_B_reference_library_json_text"]["wedge"] == 0,
        "reference_library.json 텍스트의 'wedge' 0회는 유지된다",
    )

    # ── 크기지수(우리 앵커의 가장 약한 고리) ────────────────────────────
    ke = sa["our_kernel_size_exponent"]
    R["size_exponent"] = {
        "by_band": ke["by_band"],
        "exponent_range": [
            min(v["exponent"] for v in ke["by_band"].values()),
            max(v["exponent"] for v in ke["by_band"].values()),
        ],
        "pearson_r_range": [
            min(v["pearson_r"] for v in ke["by_band"].values()),
            max(v["pearson_r"] for v in ke["by_band"].values()),
        ],
        "n_drones": ke["n_drones"],
        "note_ko": ke["note"],
    }

    # ── 81 엔트리 인용 상태 (G3) ───────────────────────────────────────
    vn = J("reflib_sweep_venues")["counts"]
    R["venue_entries"] = {
        "entries_total": vn["entries_total"],
        "entries_with_pdf_on_disk": vn["entries_with_pdf_on_disk"],
        "entries_with_verbatim_quote": vn["entries_with_verbatim_quote"],
        "by_grade": vn["by_grade"],
    }

    # UNVERIFIED 마커 총수(현재 상태를 정직하게)
    # ⚠ 자기 자신(deck_facts.json)은 제외한다 — 넣으면 자기참조로 수가 부풀어 오른다.
    tot, nfiles = 0, 0
    for fn in sorted(os.listdir(os.path.join(ROOT, "outputs"))):
        if not fn.endswith(".json") or fn == "deck_facts.json":
            continue
        try:
            tot += raw(os.path.join(ROOT, "outputs", fn)).count("UNVERIFIED")
            nfiles += 1
        except Exception:
            pass
    R["unverified_markers_in_outputs"] = tot
    R["unverified_marker_files_scanned"] = nfiles

    return R


# ────────────────────────────────────────────────────────────────────────────
# 2. 인용 재대조 — PDF 페이지 텍스트에 실제로 있는지
# ────────────────────────────────────────────────────────────────────────────
def norm(s: str) -> str:
    s = s.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("–", "-").replace("—", "-")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


_pdf_cache: dict = {}


def pdf_text(path: str) -> str:
    if path not in _pdf_cache:
        try:
            import fitz

            d = fitz.open(path)
            _pdf_cache[path] = norm("".join(p.get_text() for p in d))
            d.close()
        except Exception as exc:
            _pdf_cache[path] = f"__ERR__{exc}"
    return _pdf_cache[path]


def verify_quote(qid: str, pdf: str, fragment: str) -> bool:
    if not os.path.exists(pdf):
        return check(f"Q.{qid}", False, f"PDF 없음: {pdf}")
    txt = pdf_text(pdf)
    if txt.startswith("__ERR__"):
        return check(f"Q.{qid}", False, f"PDF 추출 실패: {txt[:120]}")
    return check(f"Q.{qid}", norm(fragment) in txt, f"{qid} 조각 대조: {fragment[:60]}...")


PDF_ABRAT = "/data/public/sionna_jeong/reference_library/g1g2/abratkiewicz2023_jstars.pdf"
PDF_CHEN = "/data/public/sionna_jeong/reference_library/g1g2/chen2024_applsci_14_4282.pdf"
PDF_SIONNA_TR = (
    "/data/public/sionna_jeong/sionna_papers_by_task/channel_modeling_raytracing/"
    "2504.21719__sionna-rt-technical-report-v1.pdf"
)
PDF_TAYLOR = (
    "/data/public/jeong/papers/LTE/25_Drone_Detection_Using_4G-LTE-Based_Passive_Radar.pdf"
)


# ────────────────────────────────────────────────────────────────────────────
# 3. 사실 기반 조립
# ────────────────────────────────────────────────────────────────────────────
def build_facts(R: dict) -> list[dict]:
    vt = {r["waveform"]: r for r in R["vmax_table"]}
    mc = R["monostatic_ceiling"]
    F: list[dict] = []

    def add(**kw):
        F.append(kw)

    # ── TIER 1 : 속도 이야기와 우선권 ───────────────────────────────────
    add(
        id="F01",
        rank=1,
        tier="속도·우선권",
        claim_ko="우리가 쓰는 무모호 속도 법칙 v_max = λ·PRF/4 는 우리 것이 아니다 — "
        "Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023, 게재) eq.(16) 이 반쪽 구간 규약까지 문자 그대로 같다.",
        claim_en="Our unambiguous-velocity law is Abratkiewicz et al., IEEE JSTARS 16:3469-3484 "
        "(2023, PUBLISHED) eq.(16), verbatim, half-window convention included.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_ABRAT,
            "loc": "Sec. IV, eq. (16), p.3476",
            "quote": "The Doppler range is limited by T^SSB_dist so that Vb in "
            "[-lambda/(4 T^SSB_dist), lambda/(4 T^SSB_dist)] (16)",
            "quote_fragment_checked": "The Doppler range is limited by T",
            "citation": "K. Abratkiewicz, A. Ksiezyk, M. Plotka, P. Samczynski, J. Wszolek, "
            "T. P. Zielinski, IEEE J. Sel. Topics Appl. Earth Observ. Remote Sens., "
            "vol. 16, pp. 3469-3484, 2023 (PUBLISHED, CC BY 4.0), doi:10.1109/JSTARS.2023.3262291",
            "json": "outputs/verify_chen.json : quotes_abratkiewicz2023[A2]",
        },
        attack="그럼 이 발표의 이론적 기여는 무엇인가. 남의 식을 표로 만든 것뿐 아닌가.",
        answer="맞다, 식은 선행이다. 우리가 새로 놓는 것은 식이 아니라 **평가**다 — 하나의 명시된 규약 아래 "
        "네 표준을 같은 표에 올리고(F02), 그 표를 실기체 최고속도와 겹치고(F03), 그 한계를 검출성능까지 "
        "잇는다(F26). 두 선행은 각자 자기 표준 한 줄만 갖고 있고, 둘 다 드론을 쓰지 않았다(F05).",
    )
    add(
        id="F02",
        rank=2,
        tier="속도·우선권",
        claim_ko=f"하나의 규약(반쪽 구간, c=3e8) 아래 네 조명원의 무모호 속도는 "
        f"LTE CRS {vt['LTE CRS']['v_max_half_ms_c3e8']:.3f} · "
        f"WiFi VHT-LTF {vt['WiFi VHT-LTF']['v_max_half_ms_c3e8']:.3f} · "
        f"5G SSB {vt['5G SSB']['v_max_half_ms_c3e8']:.3f} · "
        f"WiFi beacon {vt['WiFi beacon']['v_max_half_ms_c3e8']:.3f} m/s 로 289배 벌어진다.",
        claim_en="Under one stated convention the four ambient illuminators span 289x in "
        "unambiguous velocity: LTE CRS 40.695, WiFi VHT-LTF 14.395, 5G SSB 1.071, WiFi beacon 0.141 m/s.",
        grade="computed-by-us",
        source={
            "json": "outputs/deck_facts.json : recomputed.vmax_table "
            "(cross-checked against outputs/verify_chen.json : reproductions_by_us.our_v1_table_recheck)",
            "formula": "v_max_half = lambda * PRF_ref / 4",
            "convention": "반쪽 구간(±). c = 3e8 — Abratkiewicz 도 c=3e8 을 썼음이 재현으로 확인됨.",
        },
        numbers={r["waveform"]: round(r["v_max_half_ms_c3e8"], 4) for r in R["vmax_table"]},
        attack="반복률 값(LTE CRS 1 kHz, WiFi VHT-LTF 1 kHz)의 출처는 무엇인가.",
        answer="정직하게: 이번 라운드에서 **5G SSB 행만** 외부 1차 문헌으로 앵커되었다"
        "(Abratkiewicz A7 이 SSB 주기 집합 {5,10,20,40,80,160} ms 와 기본 20 ms 를 명시). "
        "LTE·WiFi 반복률은 우리 waveform 모듈의 가정이고 1차 규격으로 재확인하지 않았다 — 열린 항목이다.",
        caveat="⚠ c 규약을 반드시 밝힌다. c 정확값을 쓰면 넷째 자리에서 갈린다(LTE 40.666 vs 40.695).",
    )
    add(
        id="F03",
        rank=3,
        tier="속도·우선권",
        claim_ko=f"3GPP sub-6 CSI-RS 최대 설정률 500 Hz 로 올려도 3.5 GHz 에서 무모호 속도는 "
        f"{mc['v_max_half_ms']:.2f} m/s 이고, 이는 우리가 모형화한 공개 최고속도 5기체 중 "
        f"{mc['n_covered']}기를 커버한다 — 가장 느린 {mc['slowest'][0].replace('_max','')} 조차 {mc['slowest'][1]} m/s 다.",
        claim_en=f"Even at the 3GPP sub-6 CSI-RS ceiling of 500 Hz the unambiguous velocity at "
        f"3.5 GHz is {mc['v_max_half_ms']:.2f} m/s, which covers {mc['n_covered']} of "
        f"{mc['n_airframes']} published airframe maxima.",
        grade="computed-by-us",
        source={
            "json": "outputs/vmax_grid.json : drone_overlay.speed_axis.items "
            "(단일 진리원 src/drones.py : DRONES[*].max_speed_ms)",
            "ceiling_source": "outputs/monostatic_prior.json : prf_ladder_at_3p5GHz['csirs_spec_max'] "
            "(LaSen p.732 §1 이 3GPP TS 38.331 Rel-19 를 인용; Chen 2024 §3 의 슬롯 목록과 산술 정합)",
        },
        numbers=mc["airframe_max_speeds_ms"],
        attack="500 Hz 는 규격 상한이지 실제 값이 아니다. 그리고 3GPP 원문을 직접 봤는가.",
        answer="둘 다 인정한다. 우리가 인용하는 500 Hz 는 **2차 인용**이다 — LaSen 이 TS 38.331 을 인용한 문장과 "
        "Chen §3 의 슬롯 목록(4~640 슬롯)이 30 kHz SCS 에서 2 ms=500 Hz 로 산술 정합한다는 것까지가 우리가 확인한 전부다. "
        "TS 38.331 원문은 열지 않았다. ⭐ 다만 방향을 보라 — PRF 가 높을수록 무모호 속도가 커져 우리 주장이 "
        "약해지므로, 500 Hz 는 **우리 주장에 가장 불리한 쪽으로 잡은 값**이다. 실측 상용망은 훨씬 낮다"
        "(Chen 의 상용 gNB 40 슬롯=20 ms=50 Hz → 1.07 m/s, C7). 즉 규격 확인이 어긋나더라도 "
        "현실 쪽으로 어긋날 가능성이 크고, 그러면 결론은 더 세진다.",
    )
    add(
        id="F04",
        rank=4,
        tier="속도·우선권",
        claim_ko="Abratkiewicz 가 논문에 적은 두 숫자(20 ms → ±1.0901 m/s, 5 ms → ±4.3605 m/s @ 3.44 GHz)를 "
        "우리 법칙으로 소수 4자리까지 재현했다 — 단, 그들이 c=3e8 을 썼다는 것을 알아채야 맞는다.",
        claim_en="We reproduce both of Abratkiewicz's stated numbers to 4 decimals, once you notice "
        "they used c = 3e8.",
        grade="computed-by-us",
        source={
            "json": "outputs/deck_facts.json : recomputed.abratkiewicz_eq16",
            "pdf": PDF_ABRAT,
            "loc": "Sec. IV, p.3476",
            "quote": "assuming the default value of T^SSB_dist = 20 ms and for the given carrier "
            "frequency, one can obtain the maximum unambiguous bistatic velocity of +-1.0901 m/s",
            "quote_fragment_checked": "one can obtain the maximum unambiguous bistatic velocity of",
        },
        numbers={f"T={r['T_SSB_ms']}ms": {"paper": r["paper_states_ms"], "ours_c3e8": round(r["ours_c3e8_ms"], 4), "ours_cexact": round(r["ours_cexact_ms"], 4)} for r in R["abratkiewicz_eq16"]},
        attack="소수 4자리 일치는 자명하다. 같은 식이니 당연한 것 아닌가.",
        answer="그렇다 — 그리고 그게 요점이다. 이 재현은 novelty 주장이 아니라 **우리 구현이 선행과 같은 양을 "
        "계산한다는 감사**다. 규약 불일치(c, 반쪽/전체 구간)는 이 분야에서 실제로 자주 어긋나는 지점이고, "
        "우리는 그 어긋남을 이번에 잡아냈다(F08).",
    )
    add(
        id="F05",
        rank=5,
        tier="속도·우선권",
        claim_ko="⭐ 이 식을 소유한 두 논문 모두 드론을 쓰지 않았다 — Abratkiewicz 의 표적은 Volvo XC90 승용차이고, "
        "Chen 의 표적은 스테퍼 모터로 돌리는 회전 모형이다.",
        claim_en="Neither owner of the equation used a drone: Abratkiewicz's target was a Volvo XC90 "
        "car, Chen's was a stepper-motor rotating model.",
        grade="quoted-from-PDF",
        source={
            "pdf_a": PDF_ABRAT,
            "loc_a": "Sec. VI, p.3478",
            "quote_a": "The cooperative target was a car (Volvo XC90) moving in a parking lot "
            "illuminated by the BTS",
            "pdf_c": PDF_CHEN,
            "loc_c": "Sec. 1, p.1-2",
            "quote_c": "a rotating target experimental model employing a stepper motor is constructed "
            "to accurately simulate target movement scenarios",
            "json": "outputs/verify_chen.json : quotes_abratkiewicz2023[A9] · quotes_chen2024[C11]",
        },
        attack="드론을 안 썼다는 것이 그들의 결론을 무효화하지는 않는다. 왜 이것이 우리 자리인가.",
        answer="무효화하지 않는다 — 우리는 그렇게 주장하지 않는다. 주장은 **적용 범위**다. 승용차는 드론보다 "
        "반사도가 훨씬 크고, 이 차이를 저자들 스스로 적었다(F06). 우리가 계산하는 것은 정확히 그 빠진 항, "
        "즉 드론 기체의 산란이다. 그리고 두 논문 다 EM 산란 계산이 없다.",
    )
    add(
        id="F06",
        rank=6,
        tier="속도·우선권",
        claim_ko="⭐⭐ 식의 주인이 직접 결론에 적어 놓았다: '다음으로 고려할 만한 문제는 소형 표적 검출, 예컨대 "
        "실험에 쓴 자동차보다 반사도가 훨씬 낮은 드론이다.'",
        claim_en="The owners of the equation left drones as explicit future work, naming the "
        "reflectivity gap themselves.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_ABRAT,
            "loc": "Conclusion / future work, p.3482",
            "quote": "The subsequent problem worth considering is small target detection, for "
            "instance, drones whose reflectivity is significantly lower than the car used in the "
            "experiment.",
            "quote_fragment_checked": "drones whose reflectivity is significantly lower than the car",
            "json": "outputs/verify_chen.json : quotes_abratkiewicz2023[A10]",
        },
        attack="2023년 future work 는 2026년까지 누가 이미 했을 수 있다.",
        answer="그래서 세었다. 능력 매트릭스 26행 어디에도 '드론 기체 메시 + 산란적분 + 진폭 검증 + 게재' 를 "
        "동시에 만족한 행이 없다 — H8 판정 12편 중 4관문 통과 0편이다(F16). 다만 이것은 '우리가 본 코퍼스 안에서' 이고, "
        "dblp 가 IEEE TAP/AWPL/EuCAP/IET RSN/TMTT 를 색인하지 않는다는 구조적 사각지대가 있다(G4).",
    )
    add(
        id="F07",
        rank=7,
        tier="속도·우선권",
        claim_ko="⚠ 우리 이전 기록이 우선권을 돌렸던 Chen 2024 는 **닫힌 식을 표시하지 않는다** — 20 ms → 50 Hz → "
        "[-25,25] Hz → 0.56 rps 라는 수치 대입만 있고, λ·PRF/4 도 cos(β/2)cos(δ) 합성형도 표시 식으로 없다.",
        claim_en="Chen 2024 displays no closed-form unambiguous-velocity equation — only a numeric "
        "instantiation. Our earlier attribution to Chen was itself wrong.",
        grade="quoted-from-PDF (검증된 부재 — PDF 20쪽 전문을 열어 확인)",
        source={
            "pdf": PDF_CHEN,
            "loc": "Sec. 5, p.13 of 20",
            "quote": "In experiments, the CSI-RS signal period is 20 ms, and the maximum unambiguous "
            "Doppler frequency is 50 Hz. The measurable Doppler frequency shift range is [-25 Hz, 25 Hz].",
            "quote_fragment_checked": "the maximum unambiguous Doppler frequency is 50 Hz",
            "json": "outputs/verify_chen.json : what_they_did_and_did_not.chen2024_DID_NOT[0]",
        },
        attack="'식이 없다'는 부재 증명이다. 못 찾은 것과 없는 것을 어떻게 구분하는가.",
        answer="구분하지 못한다 — 그래서 범위를 좁혀 말한다. 확인한 것은 '20쪽 전문에서 우리가 찾지 못했다' 이고, "
        "확인한 것은 Chen 의 표시 식 eq.(4)가 바이스태틱 도플러이며 그것조차 [16] Samczynski 외 TGRS 를 인용한다는 "
        "것이다(C1,C2). 그러니 우리가 하는 주장은 '이 식의 계보는 바르샤바 학파로 수렴한다' 까지다.",
    )
    add(
        id="F08",
        rank=8,
        tier="속도·우선권",
        claim_ko="⚠ 같은 논문 안에서 규약이 갈린다 — eq.(16) 은 반쪽 구간 ±λ/4T 인데 eq.(18) 은 전체 폭 λ/2T 를 "
        "Vmax 라 부른다. 규약을 밝히지 않으면 2배가 조용히 어긋난다.",
        claim_en="One paper, two conventions: eq.(16) is the half-window +-lambda/4T while eq.(18) "
        "calls the full span lambda/2T 'Vmax'. A factor of 2 hides here.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_ABRAT,
            "loc": "Sec. IV, eq. (17)-(18), p.3476",
            "quote": "Vi = V~i + N Vmax (17) ... and Vmax = lambda/(4 T) - (-lambda/(4 T)) = "
            "lambda/(2 T) (18)",
            "quote_fragment_checked": "describes how many times the velocity is aliased",
            "json": "outputs/verify_chen.json : quotes_abratkiewicz2023[A6]",
        },
        attack="사소한 표기 문제 아닌가.",
        answer="사소하지 않다. 이 워크플로가 잡은 실제 오류 다섯 건 중 두 건이 규약 혼선이었다. "
        "선행과 우리 숫자를 나란히 놓는 슬라이드는 규약 줄(반쪽 구간·c 값)을 반드시 캡션에 넣는다.",
    )
    add(
        id="F09",
        rank=9,
        tier="속도·우선권",
        claim_ko="Chen 의 Table 6 이 접힘 문턱을 (0.625, 0.75] rps 로 실측으로 가두고, 이는 우리 β=0 예측 0.560 rps 와 "
        "정합한다 — 그들이 문장으로만 말한 '바이스태틱 각 때문에 조금 더 크다' 가 수치로 뒷받침된다.",
        claim_en="Chen's Table 6 brackets the aliasing threshold in (0.625, 0.75] rps by measurement, "
        "consistent with our beta=0 prediction of 0.560 rps plus their stated bistatic relief.",
        grade="computed-by-us",
        source={
            "json": "outputs/verify_chen.json : reproductions_by_us.chen_table6_threshold_bracket",
            "pdf": PDF_CHEN,
            "loc": "Sec. 5.2, Tables 6-7, p.16-17",
            "quote": "the reason for the error of 100% is that the Doppler frequency exceeds the "
            "measurement range, resulting in Doppler blur",
            "quote_fragment_checked": "resulting in Doppler blur",
        },
        numbers={
            "our_beta0_prediction_rps": 0.5600170374691247,
            "table6_ok_up_to_rps": 0.625,
            "table6_first_failure_rps": 0.75,
            "implied_beta_deg_if_delta_0": [52.72, 83.39],
        },
        attack="β 와 δ 를 논문이 안 줬으면 그 역산은 자유도가 남는다.",
        answer="맞다 — 그래서 **구간으로만** 냈다. 단일 β 값을 주장하지 않는다. 그리고 독립 교차검사가 있다: "
        "같은 0.75 rps 를 반경 0.15 m 로 줄이면 선속도가 한계 아래로 내려가고 논문의 Table 7 은 오차 0.9% 로 정상 측정한다. "
        "부호가 우리 법칙을 따른다.",
    )
    add(
        id="F10",
        rank=10,
        tier="속도·우선권",
        claim_ko="무모호 속도의 바닥은 기하와 무관하다 — 모노스태틱 값과 바이스태틱 β=0 값의 차이가 세 밴드 모두 "
        "정확히 0 m/s 다. 즉 우리가 발표하는 숫자는 두 기하의 최악값이다.",
        claim_en="The unambiguous-velocity floor is geometry-independent: monostatic equals bistatic "
        "at beta=0, |diff| = 0 m/s in all three bands.",
        grade="computed-by-us",
        source={
            "json": "outputs/geometry_grid.json : axis_independence.P1_floor_is_geometry_independent",
        },
        numbers=R["geometry_independence"]["by_band"],
        attack="β=0 에서 같은 건 정의상 당연하다. 왜 결과로 내세우는가.",
        answer="결과로 내세우는 것이 아니라 **방어선**으로 쓴다. '그건 패시브 바이스태틱이라 불리한 것 아니냐' 는 "
        "질문에 대한 답이다 — 아니다, 능동 모노스태틱으로 바꿔도 이 바닥은 그대로다. 기하를 바꿔서 벗어날 수 없다.",
    )
    add(
        id="F11",
        rank=11,
        tier="속도·우선권",
        claim_ko="접힘 비율은 CPI 와 무관한 상수다 — 5G 상시기준(SSB)에서 0.861, WiFi 0, LTE 0. "
        "적분시간을 늘려도 표본화율의 한계는 사라지지 않는다.",
        claim_en="The alias fraction is a CPI-independent constant: 0.861 for 5G SSB, 0 for WiFi, "
        "0 for LTE. Longer integration cannot fix a sampling-rate limit.",
        grade="computed-by-us",
        source={"json": "outputs/cpi_guard_sweep.json : structural.s2_alias_floor"},
        numbers={
            "5G_G1": R["alias"]["alias_frac_G1_5G"],
            "WiFi_W1": R["alias"]["alias_frac_W1_wifi"],
            "LTE_L1": R["alias"]["alias_frac_L1_lte"],
        },
        attack="접힌다고 못 보는 것은 아니다. 접힌 속도도 검출은 된다.",
        answer="정확한 지적이고 우리도 그렇게 구분해 쓴다 — 접힘(alias)과 블라인드(blind)는 다른 양이다. "
        "표에서 둘을 따로 낸다. 그리고 접힘 해제 대책은 우리가 제안하지 않는다 — Abratkiewicz eq.(17)-(20)이 "
        "두 RD 맵 방식을 이미 냈다. 우리 몫은 '한계를 정량화한다' 까지다.",
    )

    # ── TIER 2 : 매트릭스와 포지셔닝 ───────────────────────────────────
    add(
        id="F12",
        rank=12,
        tier="포지셔닝",
        claim_ko=f"능력 매트릭스는 {R['matrix']['rows']}행 × {R['matrix']['columns']}열 = "
        f"{R['matrix']['cells']}칸이고, UNVERIFIED 칸이 0개다 — "
        f"{R['matrix']['by_grade']['QUOTED']}칸은 축자 인용이며 빌드가 매 실행 PDF 원문과 재대조해 "
        f"{R['matrix']['quote_selfcheck']['passed']}/{R['matrix']['quote_selfcheck']['checked']} 통과했다.",
        claim_en=f"The capability matrix is {R['matrix']['rows']}x{R['matrix']['columns']} = "
        f"{R['matrix']['cells']} cells with zero UNVERIFIED, "
        f"{R['matrix']['by_grade']['QUOTED']} of them verbatim quotes re-checked against the PDFs on "
        f"every build ({R['matrix']['quote_selfcheck']['passed']}/{R['matrix']['quote_selfcheck']['checked']} pass).",
        grade="computed-by-us",
        source={
            "json": "outputs/capability_matrix.json : counts",
            "generator": "benchmark/capability_matrix.py",
            "figures": R["matrix"]["figures"],
        },
        numbers=R["matrix"]["by_grade"],
        attack="칸을 채운 판정 자체가 주관적이다. 'PARTIAL' 의 경계는 누가 정하는가.",
        answer="우리가 정했고, 그래서 각 칸에 **판정 근거를 같이 실었다** — 인용문이면 문장과 위치, 계산이면 "
        "JSON 키와 스크립트. 판정에 동의하지 않아도 근거를 보고 스스로 다시 판정할 수 있다. "
        "그것이 산문 대신 매트릭스를 쓰는 이유다.",
    )
    add(
        id="F13",
        rank=13,
        tier="포지셔닝",
        claim_ko=f"아홉 열을 모두 채운 행은 0개다. 최다는 {R['matrix']['max_full_score']}/9 이고 "
        f"거기 해당하는 행은 Ziganshin EuCAP'25, Ziganshin arXiv'26, 그리고 우리다.",
        claim_en=f"No row fills all nine columns. The maximum is {R['matrix']['max_full_score']}/9, "
        f"tied between Ziganshin (EuCAP'25), Ziganshin (arXiv'26) and us.",
        grade="computed-by-us",
        source={"json": "outputs/capability_matrix.json : rows[*].cells[*].level"},
        numbers={r["row"]: r["full"] for r in R["matrix"]["top_rows"]},
        attack="우리를 남의 논문과 같은 표에 올린 것 자체가 자기평가다. 우리 행만 후하게 준 것 아닌가.",
        answer="그 위험을 알기 때문에 우리 행에 **NONE 두 개(rotor, diffraction)와 PARTIAL 한 개(진폭 검증)를 "
        "그대로 뒀다**. 6/9 는 Ziganshin 과 동점이지 최고가 아니고, 우리가 비는 열은 슬라이드에 인쇄된다.",
    )
    add(
        id="F14",
        rank=14,
        tier="포지셔닝",
        claim_ko=f"⭐ Diffraction 이 가장 빈 열이다 — 26행 중 회절을 실제로 모형에 넣은 것은 "
        f"{R['matrix']['diffraction_n_full']}편(Ziganshin EuCAP'25·arXiv'26 은 UTD+정점회절, "
        f"Kirik Sigma'19 은 SBR 에 PTD)뿐이고, **우리 행도 그 빈칸 중 하나다**.",
        claim_en=f"Diffraction is the emptiest column: only {R['matrix']['diffraction_n_full']} of 26 "
        "rows model it, and our row is one of the blanks.",
        grade="quoted-from-PDF + computed-by-us",
        source={
            "json": "outputs/capability_matrix.json : column_findings.diffraction",
            "quote": "We show that more comprehensive diffraction methods are required to achieve "
            "realistic results: one of them is vertex diffraction",
            "quote_source": "Ziganshin et al., Proc. EuCAP 2025 (PUBLISHED), Abstract, "
            "doi:10.23919/EuCAP63536.2025.10999367",
        },
        numbers={"rows_full": R["matrix"]["diffraction_full_rows"]},
        attack="Sionna 에는 회절이 있다. 왜 그냥 켜지 않는가.",
        answer="Sionna 2.0.1 에 회절이 있는 것은 맞다(F22) — 1차 UTD **쐐기** 회절이고, 전파 경로의 그림자 경계 "
        "불연속을 고치는 물건이다. 그런데 그것이 먹일 **산란적분이 Sionna 에 없다**(F21). "
        "게다가 테셀레이션된 드론 셸에서 쐐기 각도는 드론의 성질이 아니라 우리 메싱의 성질이 된다. "
        "구조적으로 우리 커널에 더할 수 있는 것은 PTD/PTD-EEC 쪽이고, 그것이 밴드 기울기를 고칠지는 **미검증**이다.",
    )
    add(
        id="F15",
        rank=15,
        tier="포지셔닝",
        claim_ko="26행 중 engine·mesh·material·aspect·geometry·vmax 여섯 열을 동시에 FULL 로 채운 행은 우리뿐이다. "
        "앞 네 열을 채운 다른 행은 RadarTwin(arXiv'26) 하나이고 그 행은 vmax·geometry 가 비어 있다.",
        claim_en="Ours is the only row FULL on engine+mesh+material+aspect+geometry+vmax "
        "simultaneously; the only other row full on the first four (RadarTwin, arXiv'26) is empty on "
        "vmax and geometry.",
        grade="computed-by-us",
        source={"json": "outputs/capability_matrix.json : rows[*].cells[*].level (교집합 계산)"},
        numbers={
            "rows_full_on_six": R["matrix"]["rows_full_on_six"],
            "rows_full_on_first_four": R["matrix"]["rows_full_on_engine_mesh_material_aspect"],
            "rows_with_vmax_and_mesh": R["matrix"]["rows_with_vmax_and_mesh"],
        },
        attack="열을 우리가 골랐으니 우리가 이기는 조합이 나오는 것은 당연하다.",
        answer="열은 사용자 추적표에서 왔다(Sionna RT · mesh · material · aspect/RCS · rotor · diffraction), "
        "우리가 발명한 것이 아니다. 우리가 더한 세 열(진폭 검증·기하·무모호 속도) 중 두 열에서 우리는 "
        "각각 PARTIAL 과 동점이다. 그리고 우리가 고른 열에서도 우리는 9/9 가 아니다.",
    )
    add(
        id="F16",
        rank=16,
        tier="포지셔닝",
        claim_ko=f"H8('드론 메시의 산란 시그니처를 Sionna 급 엔진에서 계산하고 진폭까지 검증한 게재 논문은 없다') 를 "
        f"4관문으로 판정한 결과, 후보 {R['h8']['n_adjudicated']}편 중 네 관문을 모두 통과한 것은 "
        f"{R['h8']['n_passing_all_prongs']}편이다. 막힌 곳: 게재 {R['h8']['blocked_at_counts']['P1']} · "
        f"드론메시 {R['h8']['blocked_at_counts']['P2']} · 엔진내부 {R['h8']['blocked_at_counts']['P3']} · "
        f"진폭검증 {R['h8']['blocked_at_counts']['P4']}.",
        claim_en=f"Of {R['h8']['n_adjudicated']} adjudicated candidates, "
        f"{R['h8']['n_passing_all_prongs']} pass all four prongs.",
        grade="computed-by-us",
        source={
            "json": "outputs/report01_paper.json : h8 (n_adjudicated, n_passing_all_prongs, blocked_at_counts)",
            "corpus": f"판정 문서 {R['h8']['corpus_documents']}건 / 저작 {R['h8']['corpus_distinct_works']}편, "
            f"스윕 PDF {R['h8']['corpus_swept_pdfs']}편",
        },
        numbers=R["h8"]["blocked_at_counts"],
        attack="'없다' 는 세상 전체에 대한 주장이다. 못 본 논문이 있을 것이다.",
        answer="있다. 그래서 문장을 **코퍼스에 한정해서** 쓴다. 그리고 사각지대를 스스로 명시한다 — "
        "dblp 가 IEEE TAP·AWPL·EuCAP·IET RSN·TMTT 를 색인하지 않아 그 지면들은 자동 스윕에 구조적으로 "
        "보이지 않았다. 거기서 '안 나왔다' 는 '안 봤다' 라는 뜻이고, 그렇게 말해야 한다.",
        caveat="⚠ 슬라이드 문구는 'ZERO papers' 가 아니라 'ZERO in our corpus of N, and here is what "
        "the corpus cannot see' 로 쓴다.",
    )
    add(
        id="F17",
        rank=17,
        tier="포지셔닝",
        claim_ko=f"아카이브 고유 PDF {R['sionna_sweep']['pdfs_unique']}편 중 Sionna 를 언급한 것 "
        f"{R['sionna_sweep']['mention_sionna']}편, 실제로 돌린 것 {R['sionna_sweep']['sionna_used']}편인데, "
        f"광선추적 씬 **안에 표적을 세운** 고유 저작은 {R['sionna_sweep']['target_in_scene_unique_works']}편뿐이고, "
        f"Sionna 로 dBsm 을 인쇄한 논문은 {R['sionna_sweep']['prints_dbsm_from_sionna']}편"
        f"(Ziganshin, EuCAP 2025, 게재)뿐이며 그 표적은 **자동차**다.",
        claim_en=f"Of {R['sionna_sweep']['pdfs_unique']} unique PDFs, "
        f"{R['sionna_sweep']['sionna_used']} actually run Sionna, only "
        f"{R['sionna_sweep']['target_in_scene_unique_works']} put a target inside the scene, and "
        f"exactly {R['sionna_sweep']['prints_dbsm_from_sionna']} prints dBsm from Sionna - a car.",
        grade="computed-by-us",
        source={"json": "outputs/reflib_sweep_sionna.json : counts"},
        numbers=R["sionna_sweep"],
        attack="'6편' 과 '19편' 을 예전에 섞어 말한 적이 있다. 어느 쪽인가.",
        answer="섞어 말한 것이 맞고, 그래서 이번에 분리했다. 6편 = **Sionna 씬 안에 표적을 세운 고유 저작** "
        "(reflib_sweep_sionna.json). 19편 = **전문 판정 코퍼스의 고유 저작 수**(report01_paper.json, 문서 21건). "
        "서로 다른 두 코퍼스이고, 한 문장에 같이 넣으면 안 된다.",
    )
    add(
        id="F18",
        rank=18,
        tier="포지셔닝",
        claim_ko=f"Sionna 를 쓴 논문 {R['sionna_sweep']['mention_sionna']}편 중 버전을 적은 것은 "
        f"{R['sionna_sweep']['state_a_sionna_version']}편뿐이다 — 스택이 0.8.0 에서 2.0.1 까지 두 번 갈아엎였는데도 그렇다.",
        claim_en=f"Only {R['sionna_sweep']['state_a_sionna_version']} of "
        f"{R['sionna_sweep']['mention_sionna']} papers state a Sionna version, across a stack that "
        "was rewritten twice between 0.8.0 and 2.0.1.",
        grade="computed-by-us",
        source={"json": "outputs/reflib_sweep_sionna.json : counts.state_a_sionna_version"},
        attack="버전 미기재가 결과를 틀리게 만들지는 않는다.",
        answer="틀리게 만들지는 않는다. 재현 불가능하게 만든다. 우리가 이것을 드는 이유는 남을 비판하려는 게 "
        "아니라 **우리 리포트가 왜 버전·커밋·런타임을 다 적는지**를 설명하기 위해서다.",
    )

    # ── TIER 3 : 우리 엔진과 그 한계 ──────────────────────────────────
    add(
        id="F19",
        rank=19,
        tier="엔진",
        claim_ko=f"우리 SBR 커널은 해석적 PO 구 대비 최대 편차 "
        f"{R['kernel_accuracy']['max_abs_db_vs_po']:.4f} dB 다"
        f"(div=16, kr {R['kernel_accuracy']['kr_min']:.0f}~{R['kernel_accuracy']['kr_max']:.0f}, "
        f"입사방향 {R['kernel_accuracy']['n_incidence']}개).",
        claim_en=f"Our SBR kernel agrees with the analytic PO sphere to "
        f"{R['kernel_accuracy']['max_abs_db_vs_po']:.4f} dB max deviation.",
        grade="computed-by-us",
        source={"json": "outputs/sbr_kr_sweep.json : summary_div16.max_abs_db_vs_po"},
        numbers=R["kernel_accuracy"],
        attack=f"정확한 Mie 해와는 최대 {R['kernel_accuracy']['max_abs_db_vs_mie']:.2f} dB 어긋난다. "
        "0.2 dB 만 말하는 것은 유리한 기준을 고른 것 아닌가.",
        answer="두 수를 둘 다 낸다. 커널이 PO 근사이므로 **수치 수렴의 과녁은 해석 PO** 이고, Mie 잔차는 "
        "'PO 근사를 쓴 대가' 라는 별도의 자다. kr≥30 에서 Mie 대비 산포는 1.83% 로 떨어진다 — "
        f"큰 잔차는 저-kr(공진영역)에 몰려 있고, 그게 바로 우리 few-λ 한계다. "
        "⭐ Mie 도 해석 PO 도 **기준해이지 우리 출력이 아니다**.",
    )
    add(
        id="F20",
        rank=20,
        tier="엔진",
        claim_ko=f"실측 앵커는 **주파수 기울기만** 옮기고 절대 레벨은 옮기지 않는다 — 7기체 평균 레벨 이동 "
        f"{R['anchor_slope_only']['mean_level_shift_db']:+.4f} dB(최대 |{R['anchor_slope_only']['max_abs_level_shift_db']:.1e}| dB), "
        f"기울기는 {R['anchor_slope_only']['slope_before_db_per_ghz_range'][0]:.2f}~"
        f"{R['anchor_slope_only']['slope_before_db_per_ghz_range'][1]:.2f} → 0.210 dB/GHz 로 정렬된다.",
        claim_en="The measurement anchor moves the frequency SLOPE only; the mean absolute level "
        "shift is 0.0000 dB over 7 airframes.",
        grade="computed-by-us",
        source={
            "json": "outputs/sigma_anchor.json : drones[*].modes.slope_only "
            "(mu_before_dbsm vs mu_after_dbsm, 7기체 평균)",
            "reproduce": "benchmark/deck_facts.py : recompute()['anchor_slope_only']",
        },
        numbers={
            "mean_level_shift_db": R["anchor_slope_only"]["mean_level_shift_db"],
            "n_airframes": R["anchor_slope_only"]["n_airframes"],
            "slope_before_range": R["anchor_slope_only"]["slope_before_db_per_ghz_range"],
            "slope_after": R["anchor_slope_only"]["slope_after_db_per_ghz"],
        },
        attack="그럼 절대 σ 는 아무 검증도 안 받은 것 아닌가.",
        answer="그렇다. 그것이 정확히 우리 매트릭스에서 진폭 검증이 FULL 이 아니라 PARTIAL 인 이유다. "
        "절대 레벨은 해석 PO 구까지만 검증되었고 측정에 앵커되지 않았다. 우리는 절대 σ 판정을 보류한다.",
    )
    add(
        id="F21",
        rank=21,
        tier="엔진",
        claim_ko=f"설치된 Sionna {R['sionna_installed'].get('version','?')} 의 rt 파이썬 소스에는 "
        f"'rcs' 라는 단어가 {R['sionna_installed'].get('rcs_word_hits','?')}회, "
        f"'radar_cross_section' 이 {R['sionna_installed'].get('radar_cross_section_hits','?')}회 나온다 — "
        f"즉 산란적분도 σ 출력도 없다. 우리 파이프라인이 존재하는 이유가 이 한 줄이다.",
        claim_en=f"The installed Sionna {R['sionna_installed'].get('version','?')} rt package contains "
        "zero occurrences of 'rcs' or 'radar_cross_section' - there is no scattering integral and no "
        "sigma output.",
        grade="computed-by-us (한 줄로 재현)",
        source={
            "command": f"grep -rio '\\brcs\\b' {R['sionna_installed'].get('rt_dir','<sionna.rt>')} --include=*.py | wc -l",
            "json": "outputs/deck_facts.json : recomputed.sionna_installed",
            "corroborating": "benchmark/verify_rt_no_rcs.py · outputs/psolve_diffraction.json : sionna_stock_D",
        },
        numbers=R["sionna_installed"],
        attack="'Sionna 는 RCS 를 못 낸다' 는 말은 예전에 우리가 틀렸다고 정정한 주장 아닌가.",
        answer="맞다 — 그래서 문장을 좁혔다. 틀린 문장은 '광선추적은 RCS 를 못 낸다' 였다(SBR 은 낸다). "
        "참인 문장은 '**Sionna 기본 solver 에 산란적분 단계가 없다**' 뿐이고, 그것이 위 grep 이 보여주는 것이다. "
        "Sionna 는 경로 계수를 내지 σ 를 내지 않는다.",
    )
    add(
        id="F22",
        rank=22,
        tier="엔진",
        claim_ko="⚠ 반대로 'Sionna 에 회절이 없다' 고 말하면 틀린다 — Sionna 는 1차 UTD **쐐기** 회절을 구현하고 "
        "기술보고서가 ITU-R P.526 권고 해를 쓴다고 명시한다. 다만 그것은 전파용 그림자경계 보정이지 "
        "산란적분에 붙는 PTD/fringe 보정이 아니다.",
        claim_en="Sionna DOES implement first-order UTD wedge diffraction (ITU-R P.526 heuristic for "
        "finitely conducting wedges) - but as a propagation shadow-boundary fix, not as a PTD "
        "correction to a scattering integral.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_SIONNA_TR,
            "loc": "p.47 (Sionna RT Technical Report v1.2, arXiv 2504.21719v2)",
            "quote": "While [36] deals with diffraction at edges of perfectly conducting surfaces, it "
            "was heuristically extended to finitely conducting wedges in [37]. This solution, which is "
            "also recomended by the ITU [38], is implemented in Sionna.",
            "quote_fragment_checked": "is implemented in Sionna",
            "json": "outputs/psolve_diffraction.json : sionna_stock_D.what_D_IS",
        },
        attack="그럼 PathSolver(diffraction=True) 를 드론에 켜면 되지 않는가.",
        answer="켜도 σ 는 안 나온다 — 여전히 경로 계수만 나오고, D 가 먹일 산란적분이 없다(F21). "
        "그리고 테셀레이션된 드론 셸에서 Sionna 의 쐐기 각도는 인접 면 법선 두 개로 읽히므로, 메시를 조밀하게 "
        "하면 각도가 바뀐다 — 드론의 성질이 아니라 우리 메싱의 성질이 된다.",
    )
    add(
        id="F23",
        rank=23,
        tier="엔진",
        claim_ko=f"우리 RCS 커널(src/rcs_sbr.py + src/rcs_po.py)에는 diffract·PTD·UTD·creeping·fringe 가 "
        f"{R['our_kernel_diffraction']['total_hits']}회 나온다 — 회절항이 전혀 없다. 이것이 우리 행의 빈칸이다.",
        claim_en=f"Our RCS kernel contains {R['our_kernel_diffraction']['total_hits']} occurrences of "
        "diffract/PTD/UTD/creeping/fringe - there is no edge term of any kind.",
        grade="computed-by-us (한 줄로 재현)",
        source={
            "command": "grep -cEi 'diffract|\\bPTD\\b|\\bUTD\\b|creeping|fringe' src/rcs_sbr.py src/rcs_po.py",
            "json": "outputs/psolve_diffraction.json : our_p4_state_verified",
        },
        numbers=R["our_kernel_diffraction"],
        attack="그러면 결과를 믿을 수 없는 것 아닌가.",
        answer="영향의 크기를 우리가 계산했다(F24). 회절항 부재가 밴드 기울기 초과의 가장 유력한 물리적 후보이지만, "
        "우리 자체 산술은 그것만으로 전부를 설명하기 어렵다고 말한다 — 우리 유효 지수는 2 가 아니라 0.55~1.27 이라 "
        "PO 적분이 이미 단일 평판이 아니다. 그래서 PTD 는 **수정이 아니라 진단으로 먼저** 붙일 계획이다.",
    )
    add(
        id="F24",
        rank=24,
        tier="엔진",
        claim_ko=f"우리 σ 의 주파수 기울기는 실측 앵커보다 가파르다 — 3밴드 적합 7기체에서 "
        f"{R['band_slope']['fit_A_range'][0]:.2f}~{R['band_slope']['fit_A_range'][1]:.2f} dB/GHz, "
        f"22점 el=0 적합에서 {R['band_slope']['fit_B_range'][0]:.2f}~{R['band_slope']['fit_B_range'][1]:.2f} dB/GHz 이고, "
        f"실측 센서스는 {R['band_slope']['measured_census_range'][0]:.2f}~{R['band_slope']['measured_census_range'][1]:.3f} dB/GHz 다 "
        f"(Das 0.210 대비 {R['band_slope']['ratio_fitA_over_das'][0]:.1f}~{R['band_slope']['ratio_fitA_over_das'][1]:.1f}배). "
        f"단 순수 f² 평판 한계는 {R['band_slope']['pure_f2_plate_limit_db_per_ghz']:.3f} dB/GHz 이므로 우리는 그 사이에 있다.",
        claim_en="Our band slope is steeper than measurement but below the pure-f^2 plate limit: "
        "ours 0.74-1.70 dB/GHz (3-band) vs measured 0.07-0.315, with the plate limit at 2.681.",
        grade="computed-by-us",
        source={
            "json_ours_A": "outputs/report02_derived.json : band_slope (3밴드 1.843/3.5/5.21 GHz, 7기체)",
            "json_ours_B": "outputs/rcs_anchor.json : drones[*].regression.el0.a (22점 조밀 적합, 7기체)",
            "json_measured": "outputs/psolve_diffraction.json : our_p4_state_verified.measured_slope_census",
            "anchors": "Das (IEEE WCL 15:3731-3735, 2026, 게재) 0.210 · Yuan/mono3d θ=90° 0.315 dB/GHz",
        },
        numbers=R["band_slope"],
        attack="두 개의 서로 다른 범위(0.74~1.70 과 0.96~1.54)를 내놓았다. 어느 것이 맞는가.",
        answer="둘 다 맞고 **다른 적합**이다 — 하나는 세 밴드 3점 회귀(1.843/3.5/5.21 GHz), 하나는 "
        "1.8~6.0 GHz 22점 조밀 회귀(el=0). 슬라이드에는 하나만 올리고 캡션에 적합 방식을 적는다. "
        "이런 종류의 혼선이 이 프로젝트에서 실제로 정정을 부른 적이 있어서, 규약을 적는 것을 규칙으로 만들었다.",
        caveat="⚠ 어떤 적합을 인용하든 캡션에 밴드 수·점 수·고도각을 밝힌다. "
        "⚠ 능력 매트릭스 그림의 회절 칸은 같은 22점 적합을 **DJI 쿼드 4종으로만** 잘라 "
        "'+0.96~+1.40 dB/GHz' 로 적는다 — 7기체 전체로는 +0.96~+1.54 다. 두 그림을 나란히 놓으면 "
        "차이가 보이므로, 한 발표 안에서는 한쪽 범위만 쓴다.",
    )
    add(
        id="F25",
        rank=25,
        tier="엔진",
        claim_ko=f"우리 커널의 크기지수는 밴드별 "
        f"{R['size_exponent']['exponent_range'][0]:.2f}~{R['size_exponent']['exponent_range'][1]:.2f} 이고 "
        f"상관 r 은 {R['size_exponent']['pearson_r_range'][0]:.2f}~{R['size_exponent']['pearson_r_range'][1]:.2f} 에 "
        f"불과하다 — L²(=2)도 L⁴(=4)도 아니고 산포가 커서, 크기 전이는 앵커의 가장 약한 고리다.",
        claim_en="Our kernel's own size exponent is 1.24-1.32 with Pearson r only 0.64-0.70 over 7 "
        "airframes - neither L^2 nor L^4, and too scattered to use as a single value.",
        grade="computed-by-us",
        source={"json": "outputs/sigma_anchor.json : our_kernel_size_exponent.by_band"},
        numbers=R["size_exponent"],
        attack="자기 약점을 왜 스스로 슬라이드에 올리는가.",
        answer="누군가 물으면 어차피 나올 수이고, 우리가 먼저 말하면 신뢰가 되고 남이 먼저 말하면 흠이 된다. "
        "그리고 실용적 결론이 붙는다 — 350 mm 급 실측 앵커를 1045 mm 옥토콥터로 전이하는 데 단일 크기법칙을 "
        "쓰면 안 된다.",
    )
    add(
        id="F26",
        rank=26,
        tier="엔진",
        claim_ko=f"CFAR 문턱은 이론값이 아니라 GPU 몬테카를로 {R['cfar']['runtime_s']:.0f}초"
        f"(백색 맵 {R['cfar']['n_maps_white']:,}장 + 체인 맵 {R['cfar']['n_maps_chain']:,}장, complex128)의 "
        f"경험적 오경보율에 교정되었고, 네 가드/트레이닝 구성의 α 는 이론값과 상대오차 최대 "
        f"{R['cfar']['alpha_max_rel_err']:.1e} 로 일치한다.",
        claim_en=f"Our CFAR threshold is calibrated to empirical Pfa over {R['cfar']['runtime_s']:.0f} s "
        f"of GPU Monte Carlo ({R['cfar']['n_maps_white']:,} white maps), with alpha matching theory to "
        f"{R['cfar']['alpha_max_rel_err']:.1e} relative error.",
        grade="computed-by-us",
        source={"json": "outputs/verify_cfar.json : meta · alpha_audit"},
        numbers=R["cfar"],
        attack="백색잡음에서의 Pfa 교정은 실제 클러터에서 의미가 없다.",
        answer="맞다 — 그래서 백색 교정과 체인(전 처리사슬) 교정을 따로 냈다. 백색은 α 구현 감사용이고, "
        "실제 오경보 판정은 체인 맵에서 한다. 그리고 우리 챔버는 semi-anechoic 이라 정적 클러터가 "
        "ECA 로 삼중 차단되고, 진짜 위협은 표적경유 바닥유령이라는 별도 축이다.",
    )
    add(
        id="F27",
        rank=27,
        tier="엔진",
        claim_ko="⚠ 지금까지의 검출 결과는 전부 장면방위 φ=90° 한 컷이다. φ=90° 는 베이스라인의 수직이등분선이라 "
        f"R₁≈R₂ 가 구조적으로 성립하고, 거기서 두 기하의 확산항 차는 0.118 dB 뿐이지만 φ 를 쓸면 "
        f"최대 {R['phi_sensitivity']['absmax_over_phi_db']:.2f} dB 로 벌어진다.",
        claim_en=f"Every detection result to date sits at scene azimuth phi=90 deg, where R1~=R2 "
        f"structurally: the geometry difference is 0.118 dB there and up to "
        f"{R['phi_sensitivity']['absmax_over_phi_db']:.2f} dB across phi.",
        grade="computed-by-us",
        source={
            "json": "outputs/geometry_grid.json : range_normalisation.*.absmax_over_phi_db · traps[T1b]",
            "code": "src/experiment_freespace_range.py:322,773 (phi_deg=90.0 기본 인자)",
        },
        numbers=R["phi_sensitivity"],
        attack="φ 는 하드코딩이 아니라 기본 인자다. 언제든 바꿀 수 있지 않은가.",
        answer="정확한 지적이고 우리 표현을 고쳐야 한다 — 하드코딩이 아니라 **기본 인자**다. 결함은 코드가 아니라 "
        "**보고**에 있다: 발표된 모든 숫자가 그 기본값에서 나왔고 φ 스윕을 보고한 적이 없다. 이번 라운드가 "
        "찾아낸 가장 큰 재계산 항목이고, 열린 채로 둔다.",
    )

    # ── TIER 4 : 이번에 발견된 선행 — 우리 문구를 좁히는 것들 ─────────────
    add(
        id="F28",
        rank=28,
        tier="⚠ 우리 문구를 좁히는 선행",
        claim_ko="⭐⭐ 우리 벤치마크 설계('한 표적·한 검출기·교정된 오경보율에서 통제 비교')에 게재된 선례가 있다 — "
        "Taylor & Poullin, IEEE TAES 61(4), 2025 (게재). 표적 DJI Phantom 4, 문턱 13 dB ↔ Pfa 10⁻⁶ 에서 "
        "전 심볼 사용과 CRS 포함 심볼만 사용을 통제 비교했고, 결과 방향이 우리 '점유 대가' 서사와 같다.",
        claim_en="Our benchmark design has a published precedent: Taylor & Poullin, IEEE TAES 61(4), "
        "2025, compared signal-resource choices on one target at a calibrated Pfa of 1e-6.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_TAYLOR,
            "loc": "p.8814 부근 (IEEE TAES vol.61 no.4, August 2025, 게재)",
            "quote": "The highest SNR is obtained by using all the symbols (24.2 dB), followed by a "
            "configuration using symbols containing the CRS (17.5 and 17.9 dB). However, the "
            "configuration using all the symbols also shows the highest number of plots, and thus of "
            "false alarms",
            "quote_fragment_checked": "The highest SNR is obtained by using all the symbols",
            "calibration_quote": "The 13 dB threshold corresponds to a false-alarm rate of 10-6.",
        },
        attack="그럼 우리 벤치마크는 새롭지 않다.",
        answer="⭐ 한정어 하나에 무게가 전부 실린다. 그들의 비교축은 **한 LTE 하향 신호 '안'의 심볼 부분집합**이고, "
        "우리 비교축은 **서로 다른 조명원 종류**(WiFi / LTE / 5G)다. 기하도 그들은 하나, 우리는 셋이다. "
        "그래서 우리 문장은 '조명원 종류를 통제 비교한 연구는 없다' 로만 쓰고, Taylor & Poullin 을 "
        "**선행 방법론으로 반드시 인용**한다. 이 한정어를 빼면 즉시 반례가 된다.",
        caveat="⚠ 이 논문은 슬라이드에 인용으로 올린다. 숨기면 가장 위험한 항목이다. "
        "⭐ 우리 기록 정정: 다른 라운드가 표적을 'DJI Phantom 3' 으로 적었으나 원문은 **Phantom 4** 다"
        "('a DJI Phantom 4 drone evolving above the surveillance antenna'). 내가 이번에 직접 확인했다.",
    )
    add(
        id="F29",
        rank=29,
        tier="⚠ 우리 문구를 좁히는 선행",
        claim_ko="⭐⭐ 다중 Rx 결합의 '10log10(N) 이상적 상한' 규약도 우리 것이 아니다 — 같은 논문이 7심볼 결합에 "
        "10log10(7)=8.4 dB 를 이상이득으로 잡고 문턱을 21.4 dB 로 올려야 한다고 적는다.",
        claim_en="The 10log10(N) ideal-combining ceiling we use is published prior art, not ours.",
        grade="quoted-from-PDF",
        source={
            "pdf": PDF_TAYLOR,
            "loc": "p.8814 (IEEE TAES 61(4), 2025, 게재)",
            "quote": "When performing the detection on all seven symbols, the ideal gain one could "
            "expect would be of 10 log10(7) = 8.4 dB. Theoretically, we thus should have used a "
            "threshold of 21.4 dB when using all the symbols.",
            "quote_fragment_checked": "the ideal gain one could expect would be of 10 log",
        },
        attack="10log10(N) 은 교과서 결합이득이다. 누구의 것도 아니지 않은가.",
        answer="정확히 그렇다 — 그래서 '우리 규약' 이라고 쓰면 안 된다는 것이다. 게다가 이 논문은 "
        "**실측이 이상값에 못 미친다**는 것까지 보였다. report12 의 다중 Rx 서술에서 "
        "'우리가 처음' 이라고 쓸 수 없고, 이 선례와 나란히 놓아야 한다.",
    )
    add(
        id="F30",
        rank=30,
        tier="⚠ 우리 문구를 좁히는 선행",
        claim_ko="⭐ '드론 메시를 Sionna 씬에 넣은 논문이 없다' 로 읽히는 문장은 즉시 거짓이다 — CAVIAR"
        "(arXiv 2401.03310)는 드론을 ITU metal 재질로 씬에 넣고, Cazzella(arXiv 2507.19173)와 "
        "VaN3Twin(arXiv 2505.14184)은 차량 메시를 부품 단위로 갈라 재질을 준다. "
        "살아남는 문장은 '그 메시를 **산란적분**에 통과시켜 검증된 진폭을 낸 게재 논문이 0편' 뿐이다.",
        claim_en="The loose reading of our corpus claim is false - drones and part-segmented vehicle "
        "meshes HAVE been placed in Sionna scenes with materials. Only the scattering-integral "
        "reading survives.",
        grade="SECONDHAND — 다른 정독 라운드가 연 PDF 의 인용에 근거한다. 나는 원문을 열지 않았다.",
        source={
            "json": "outputs/deepread_reconcile.json : claim_status.C1.counterexamples_to_the_loose_reading",
            "upstream": "outputs/deepread_w1.json · outputs/deepread_w2.json (쪽번호·인용 포함)",
            "new_wording_ko": "우리가 보유·정독한 문헌 중, 드론 기체의 3-D 표면 메시를 산란적분에 통과시켜 "
            "그 진폭을 보고한 논문은 0편이다. 장면에 드론·차량 메시를 넣고 재질까지 배정한 선행은 여럿 있으나, "
            "그 메시가 하는 일은 전파 상호작용이지 표적 산란단면적 산출이 아니다.",
        },
        attack="CAVIAR 가 드론을 Sionna 에 넣었는데 왜 우리가 처음인 것처럼 말하는가.",
        answer="말하지 않는다 — 문장을 고쳤다. CAVIAR 의 드론은 **수신기**이지 표적이 아니고 RCS 를 출력하지 않는다. "
        "핵심은 '씬에 메시가 있느냐' 가 아니라 '그 메시가 산란적분을 통과해 σ 를 내느냐' 다. "
        "슬라이드 문구에서 '산란적분' 을 주어 자리에 놓는다.",
        caveat="⚠ 이 항목만은 내가 원문을 직접 열지 않았다. 슬라이드에 올리기 전 CAVIAR 표 V 를 직접 확인한다.",
    )
    add(
        id="F31",
        rank=31,
        tier="⚠ 우리 문구를 좁히는 선행",
        claim_ko=f"Sionna {R['sionna_installed'].get('version','2.0.1')} 의 PathSolver 는 "
        "diffraction=False · edge_diffraction=False 가 **기본값**이다. 즉 '스톡 Sionna 에 회절이 없다' 가 아니라 "
        "'기본으로 꺼져 있다' 가 참이다.",
        claim_en="Sionna's PathSolver defaults are diffraction=False and edge_diffraction=False - the "
        "capability exists and ships off by default.",
        grade="computed-by-us (설치본 소스 직접 확인)",
        source={
            "code": f"{R['sionna_installed'].get('rt_dir','<sionna.rt>')}/path_solvers/path_solver.py:154-155",
            "verbatim": "diffraction: bool = False,  /  edge_diffraction: bool = False,",
            "command": "grep -n 'diffraction' <sionna.rt>/path_solvers/path_solver.py",
        },
        attack="그러면 켜고 다시 돌리면 되는 것 아닌가.",
        answer="켜도 σ 는 안 나온다(F21·F22). 그리고 우리 커널에 없는 것은 UTD 쐐기항이 아니라 "
        "**PO 적분에 더해지는 PTD/fringe 항**이라 종류가 다르다. 다만 우리 쪽 표현이 부정확했던 것은 맞고, "
        "'스톡 Sionna 에 회절이 없다' 는 문장은 금지 목록에 넣었다.",
    )
    add(
        id="F32",
        rank=32,
        tier="⚠ 우리 문구를 좁히는 선행",
        claim_ko="회절항 부재는 우리만의 뒤처짐이 아니라 이 분야의 기본값이다 — 26행 중 회절을 넣은 것이 3편뿐이고, "
        "Sagitta SBR(arXiv'26)·3GPP Rel-19 표준 RCS 모델·Great-X 가 전부 회절 없이 나온다. "
        "⚠ 동시에, 회절을 붙이면 밴드 기울기가 좋아진다는 기대는 **근거가 약하다**.",
        claim_en="Missing diffraction is the field default, not our lag - and the expectation that "
        "adding it fixes our band slope is weakly grounded.",
        grade="computed-by-us",
        source={
            "json": "outputs/capability_matrix.json : column_findings.diffraction · "
            "outputs/psolve_diffraction.json : THE_ANSWER · "
            "outputs/deepread_reconcile.json : diffraction_finding",
        },
        attack="그럼 회절을 붙일 것인가 말 것인가.",
        answer="붙이더라도 **진단으로 먼저** 붙인다. 우리가 지금 가진 것은 '인용할 수 있는 알려진 한계' 이지 "
        "'구현하면 기울기가 나아진다' 가 아니다 — 후자를 슬라이드에 쓰면 근거 없는 약속이 된다.",
    )

    return F


# ────────────────────────────────────────────────────────────────────────────
# 4. 철회 목록
# ────────────────────────────────────────────────────────────────────────────
def build_retractions(R: dict) -> list[dict]:
    return [
        {
            "id": "R1",
            "rank": 1,
            "headline_ko": "무모호 속도 식의 우선권 — 두 번 틀렸고 두 번 고쳤다",
            "we_said": "⑴ 'v_max = λ·PRF/4 는 우리 발견이다' → ⑵ '우리 것이 아니다, Chen 외 Applied Sciences 2024 가 "
            "같은 기호로 먼저 냈다'",
            "what_broke_it": "G1·G2 를 실제로 확보해 두 PDF 를 열었다. ⑴ Chen 은 닫힌 식을 표시하지 않는다 — "
            "수치 대입뿐이다. ⑵ λ/(4T) 의 진짜 선행은 1년 앞선 Abratkiewicz 외 JSTARS 2023 eq.(16) 이고 "
            "반쪽 구간 규약까지 같다. ⑶ Chen 자신이 그 논문을 [8] 로 인용한다.",
            "now_ko": "우선권은 Abratkiewicz 외(IEEE JSTARS 16:3469-3484, 2023, 게재)에 있다. 우리는 재현자다. "
            "우리 몫은 식이 아니라 하나의 규약 아래 놓인 교차표준 표와, 그 표를 실기체 최고속도·검출성능에 잇는 것이다.",
            "evidence": {
                "pdf": PDF_ABRAT,
                "quote": "The Doppler range is limited by T^SSB_dist so that Vb in "
                "[-lambda/(4 T^SSB_dist), lambda/(4 T^SSB_dist)]",
                "json": "outputs/verify_chen.json : priority_ledger.who_owns_what[0] · corrections_to_our_records[1]",
            },
            "why_on_a_slide": "⭐ 우선권 오귀속은 리뷰에서 반드시 걸린다. 우리가 먼저 말하면 감사가 작동한 증거가 되고, "
            "숨기면 나중에 논문 심사에서 드러난다. 게다가 LaSen(SenSys 2026)의 귀속조차 한 세대 늦다는 것을 "
            "우리가 잡아냈다 — 이건 우리 코퍼스 작업의 성과다.",
            "attack": "두 번 틀렸다는 것은 조사 과정이 부실했다는 뜻 아닌가.",
            "answer": "첫 라운드의 인용문 3건은 원문과 축자 일치했다 — 그 라운드는 정직했고, 틀린 것은 "
            "'우리가 확보하지 못한 논문에 대해 결론을 냈다' 는 것이다. 그래서 이번 워크플로의 규칙이 "
            "'내가 직접 연 PDF 아니면 UNVERIFIED' 가 되었다.",
        },
        {
            "id": "R2",
            "rank": 2,
            "headline_ko": "'모노스태틱은 반복률을 자유롭게 고른다' 는 프레이밍",
            "we_said": "모노스태틱 센서는 자기가 송신하므로 PRF 를 설계변수로 자유롭게 고를 수 있고, 그래서 "
            "무모호 속도 문제에서 자유롭다.",
            "what_broke_it": "3GPP 가 sub-6 CSI-RS 에 500 Hz 천장을 걸고, 실측 상용 gNB 는 50~200 Hz 로 돈다 "
            "(Chen 의 상용 gNB 40 슬롯=20 ms=50 Hz, LaSen 의 China Mobile N41 은 자원세트 2개를 엮어 200 Hz).",
            "now_ko": f"모노스태틱의 기준신호 천장은 500 Hz → 3.5 GHz 에서 "
            f"{R['monostatic_ceiling']['v_max_half_ms']:.2f} m/s 이고, 이는 우리가 모형화한 5기체 중 0기를 커버한다. "
            "모노스태틱의 진짜 탈출구는 반복률이 아니라 **데이터 심볼**이며, 그것은 트래픽에 종속된다.",
            "evidence": {
                "json": "outputs/monostatic_prior.json : headline_of_this_file · prf_ladder_at_3p5GHz",
                "pdf": PDF_CHEN,
                "quote": "Table 5. CSI-RS signal parameters of the 5G commercial base station. ... "
                "Period 40 slots",
            },
            "why_on_a_slide": "이 정정이 우리 서사를 **강화**한다 — 접힘 한계가 패시브만의 약점이 아니라 "
            "구조적 한계임을 보여준다. 우리 격자(A/B/C 세 기하)가 존재하는 이유가 이것이다.",
            "attack": "PRS 를 요청하면 되지 않는가.",
            "answer": "된다 — 그리고 그것이 측위 세션 옵션이라는 것이 요점이다. 우리 서사는 '상시 신호' 축이고, "
            "PRS 는 상시가 아니다. 격자에서 그 칸을 따로 표시한다.",
        },
        {
            "id": "R3",
            "rank": 3,
            "headline_ko": "'5G 는 모든 헤딩에서 커버리지 0' 이라는 헤드라인",
            "we_said": "5G 상시기준(SSB)에서는 모든 헤딩에서 검출 커버리지가 0 이다.",
            "what_broke_it": "그 '0' 은 CPI=100 ms 와 2.5빈 선언가드가 **동시에** 성립하는 한 점에서만 참인 "
            "단일-CPI 아티팩트였다. 검출기가 실제로 지우는 1.5빈 규약에서는 같은 CPI 에서 blind=0.636 이고, "
            "CPI 를 200 ms 로만 늘려도 0.303 이다. 게다가 LTE 도 CPI≤0.0393 s 에서는 blind=1.000 이 된다 — "
            "'전 헤딩 블라인드' 는 5G 만의 성질이 아니다.",
            "now_ko": "'0' 을 버리고 **구조적 비율**로 바꿨다: 같은 CPI 에서 5G 블라인드율은 WiFi 의 "
            "12~19배로 일정하게 크고(CPI 로 안 없어짐), 접힘 비율은 CPI 와 무관한 상수 0.861 이다(WiFi·LTE 0).",
            "evidence": {
                "json": "outputs/cpi_guard_sweep.json : verdict.artifact · structural.s1_equal_cpi_penalty · "
                "structural.s2_alias_floor",
                "numbers": {
                    "blind_hard_G1_at_100ms": R["alias"]["artifact"]["blind_hard_same_cpi"],
                    "blind_hard_G1_at_200ms": R["alias"]["artifact"]["blind_hard_at_200ms"],
                    "alias_frac_G1": R["alias"]["alias_frac_G1_5G"],
                },
            },
            "why_on_a_slide": "⭐ 극단적인 수(0, 100%)는 청중이 가장 잘 기억하고 가장 쉽게 반증된다. "
            "우리가 스스로 그 수를 내리고 더 약하지만 더 튼튼한 수로 바꾼 사례다.",
            "attack": "그럼 5G 가 나쁘다는 결론 자체가 흔들리는 것 아닌가.",
            "answer": "결론의 **방향**은 흔들리지 않았고 **크기**가 바뀌었다. 접힘 비율 0.861 대 0 은 CPI 로 "
            "제거되지 않는 구조적 격차이고, 그것이 원래 하려던 말이다. 바뀐 것은 '0' 이라는 단정뿐이다.",
        },
        {
            "id": "R4",
            "rank": 4,
            "headline_ko": "'실측 앵커가 우리 σ 레벨을 정한다' 는 주장",
            "we_said": "우리 절대 σ 는 문헌 실측에 앵커되어 있다.",
            "what_broke_it": "slope_only 모드에서 앵커가 실제로 옮기는 레벨을 계산했더니 7기체 평균 "
            f"{R['anchor_slope_only']['mean_level_shift_db']:+.4f} dB — 정확히 0 이다. 앵커는 회전축(pivot)을 "
            "밴드 비가중 평균에 두고 **기울기만** 돌린다.",
            "now_ko": "앵커는 주파수 기울기만 받고 절대 레벨은 우리 PO 출력 그대로다. 그래서 매트릭스에서 "
            "우리 진폭 검증 칸은 FULL 이 아니라 PARTIAL 이고, 절대 σ 판정은 보류한다.",
            "evidence": {
                "json": "outputs/sigma_anchor.json : drones[*].modes.slope_only",
                "reproduce": "benchmark/deck_facts.py 가 매 실행 7기체 평균을 다시 계산한다",
                "numbers": R["anchor_slope_only"]["per_airframe_level_shift_db"],
            },
            "why_on_a_slide": "레벨과 기울기를 뭉뚱그리면 '검증되었다' 는 인상이 과장된다. "
            "이 정정이 우리 한계 문장(절대 σ 보류)의 근거다.",
            "attack": "그럼 level_and_slope 모드를 쓰면 레벨도 앵커되지 않는가.",
            "answer": "된다 — 그 모드는 크기보정(L² 또는 L⁴)을 가정해야 하고, 우리 자체 크기지수가 1.24~1.32 에 "
            "r=0.64~0.70 이라(F25) 그 가정이 가장 약한 고리다. 그래서 헤드라인은 가정이 가장 적은 "
            "slope_only 로 낸다.",
        },
        {
            "id": "R5",
            "rank": 5,
            "headline_ko": "'상반성 위반 13.7 dB' 라는 수",
            "we_said": "바이스태틱을 β≤45° 로 제한하는 근거는 최대 13.7 dB 의 상반성 위반이다.",
            "what_broke_it": "역검증 결과 13.719 dB 는 **상반성 위반이 아니라** matrice4e·5G 3.5 GHz·β=45° "
            "단일 셀의 **이등분선 근사오차 p95** 였다. 두 양은 크기도 뜻도 다르다.",
            "now_ko": "참값은 이렇다 — 이등분선 근사오차 p95 최대 20.04 dB · rms 중앙 7.47 dB, "
            "상반성 rms 최대 5.80 dB(최악 드론 β=90° 에서 8.24 dB). β 창을 정당화하는 근거는 근사오차 쪽이고, "
            "그 값은 13.7 보다 **크다** — 즉 모노 팔의 이점이 브리핑보다 오히려 더 크다.",
            "evidence": {
                "json": "outputs/geometry_grid.json : sigma_transfer.correction_to_the_brief",
                "cross_check": "outputs/geometry_grid_axis_review.json : OK7 · "
                "outputs/geometry_grid_fairness_audit.json : D6 (독립 감사 2건이 정정을 통과시켰다)",
            },
            "why_on_a_slide": "⭐ 이 정정은 우리에게 **불리하지 않다** — 그래서 더 좋은 사례다. "
            "'우리는 우리 결론에 유리한 방향으로만 고치지 않는다' 를 보여준다. 라벨이 틀렸으면 "
            "결론이 유리해져도 고친다.",
            "attack": "결과적으로 유리해졌다면 왜 처음에 불리하게 적었는가.",
            "answer": "두 양을 구분하지 않았기 때문이다. 값 하나를 여러 라운드가 이어받으며 라벨이 미끄러졌고, "
            "역검증이 잡았다. 그래서 지금은 모든 수치에 '무엇의 어떤 통계인지' 를 함께 적는다.",
        },
        {
            "id": "R6",
            "rank": 6,
            "headline_ko": "(보너스) 게재처·인용문 오류 4건 — 매트릭스 빌드의 자동 재대조가 잡았다",
            "we_said": "Costa 의 게재처는 IEEE JSTSP · RadarTwin 인용문 끝은 '…that the real system cannot "
            "resolve' · Semkin IEEE Access 2020 의 PDF 는 pdf_paths[0]",
            "what_broke_it": "빌드가 매 실행 인용문을 PDF 페이지 텍스트에 재대조하도록 만들었더니 걸렸다.",
            "now_ko": "Costa 는 **IEEE JSTEAP vol.1 (2025)** 이다(게재판 1쪽 DOI 10.1109/JSTEAP.2025.3604407 확인). "
            "RadarTwin 원문은 '…that the real radar does not measure'. Semkin 의 pdf_paths[0] 은 다른 논문"
            "(arXiv 2112.09774)이고 본편은 pdf_paths[1] 이다. Great-X 의 재질 칸은 '언급 없음' 에서 "
            "원문 확인 후 PARTIAL 로 고쳤다.",
            "evidence": {"json": "outputs/capability_matrix.json : record_corrections_ko"},
            "why_on_a_slide": "정정 자체보다 **정정을 잡은 장치**가 요점이다 — 인용문을 매 빌드 재대조하는 "
            "습관이 없었으면 넷 다 발표까지 갔다. 사용자 추적표의 'IEEE JSTEAP 2025' 가 맞았고 우리 기록이 틀렸다.",
            "attack": "그렇게 사소한 오류를 슬라이드에 올릴 필요가 있는가.",
            "answer": "오류를 올리는 게 아니라 **장치**를 올린다. 한 장에 '자동 재대조 80/80 통과, 그 과정에서 "
            "잡힌 기록 오류 4건' 으로 요약한다.",
        },
        {
            "id": "R7",
            "rank": 7,
            "headline_ko": "(보너스) 회절 언급 횟수 — 코퍼스를 밝히지 않으면 셋 다 다른 수가 나온다",
            "we_said": "우리 코퍼스는 diffraction 11회 · UTD 13회 · PTD 1회 · wedge 0회를 언급한다.",
            "what_broke_it": "코퍼스를 특정해 다시 세었다. 그 수는 **reference_library.json 텍스트**의 수이고, "
            "그중 13 은 UTD 가 아니라 diffract* 였다(UTD 는 10, PTD 는 8).",
            "now_ko": f"코퍼스 B(reference_library.json 텍스트): "
            f"diffraction {R['diffraction_census']['corpus_B_reference_library_json_text']['diffraction']} · "
            f"diffract* {R['diffraction_census']['corpus_B_reference_library_json_text']['diffract_star']} · "
            f"UTD {R['diffraction_census']['corpus_B_reference_library_json_text']['UTD']} · "
            f"PTD {R['diffraction_census']['corpus_B_reference_library_json_text']['PTD']} · "
            f"wedge {R['diffraction_census']['corpus_B_reference_library_json_text']['wedge']}. "
            "코퍼스 A(PDF 217편 본문): diffract* 72편/607회 · UTD 10편 · PTD 6편 · wedge 10편. "
            "두 수를 한 문장에 섞으면 안 된다.",
            "evidence": {
                "json": "outputs/psolve_diffraction.json : machine_census · "
                "outputs/deck_facts.json : recomputed.diffraction_census",
            },
            "why_on_a_slide": "⭐ 이 프로젝트가 반복해서 틀린 방식이 정확히 이것이다 — 서로 다른 코퍼스의 수를 "
            "한 호흡에 섞는 것(81개 엔트리 중 8개 인용 건도 같은 실수였다). 규칙으로 승격했다: "
            "모든 개수 주장은 코퍼스 이름을 달고 다닌다.",
            "attack": "단순 오타 아닌가.",
            "answer": "오타가 아니라 **범주 오류**다. 그리고 실질적 결론은 그대로다 — 어느 코퍼스로 세든 "
            "회절을 실제로 구현한 저작은 3편뿐이다.",
        },
        {
            "id": "R8",
            "rank": 8,
            "headline_ko": "⭐⭐ '다중 Rx 10log10(N) 이상 상한' 과 'hover blind' 는 우리 발견이 아니다",
            "we_said": "report12 의 다중 Rx 이상적 결합 상한 10log10(N) 규약, 그리고 report05 의 hover blind"
            "(정지 표적이 패시브 바이스태틱에서 사라진다)를 우리 관찰처럼 서술했다.",
            "what_broke_it": "Taylor & Poullin(IEEE TAES 61(4), 2025, 게재)이 7심볼 결합에 "
            "'the ideal gain one could expect would be of 10 log10(7) = 8.4 dB' 를 이미 적었다 — "
            "내가 이번에 원문에서 직접 확인했다. hover blind 도 게재 실측 선례가 둘 있다"
            "(Taylor & Poullin: 미검출이 0-도플러 근접에 몰림 / Sun 외, IEEE OJ-COMS 2025: "
            "궤적이 바이스태틱 등고선을 따라가 미검출).",
            "now_ko": "둘 다 '우리가 처음' 이라고 쓸 수 없다. 10log10(N) 은 교과서 결합이득이고, "
            "hover blind 는 이 분야의 확립된 사실이다. 우리 몫은 그것을 **네 조명원에 걸쳐 정량화**한 것이며, "
            "선행과 나란히 놓아야 한다. ⭐ 오히려 좋은 소식이다 — 우리 시뮬 결과가 독립 게재 실측으로 확인된다.",
            "evidence": {
                "pdf": PDF_TAYLOR,
                "quote": "When performing the detection on all seven symbols, the ideal gain one could "
                "expect would be of 10 log10(7) = 8.4 dB.",
                "verified_by_me": "이번 라운드에 PDF 를 직접 열어 조각 대조했다(Q.TAY29)",
                "json": "outputs/deepread_reconcile.json : headline_ko · outputs/deepread_w1.json",
            },
            "why_on_a_slide": "novelty 를 과장했다가 좁힌 사례이고, 동시에 우리 시뮬이 게재 실측과 같은 방향임을 "
            "보여주는 슬라이드로 바꿀 수 있다. 잃는 것은 '최초' 주장, 얻는 것은 외부 검증이다.",
            "attack": "그럼 report05·report12 의 결론이 다 남의 것 아닌가.",
            "answer": "결론이 아니라 **관찰**이 선행이다. 우리 결론은 '조명원을 바꾸면 이 현상의 크기가 "
            "어떻게 달라지는가' 이고, 그 비교는 여전히 비어 있다(F28). 다만 그 문장에서 "
            "'조명원 종류' 라는 한정어를 절대 빼면 안 된다.",
        },
        {
            "id": "R9",
            "rank": 9,
            "headline_ko": "'아무도 드론 메시를 Sionna 씬에 넣지 않았다' 로 읽히는 문장",
            "we_said": "Sionna 씬에 표적을 넣은 논문 중 드론 기체 메시를 넣은 것은 없다.",
            "what_broke_it": "CAVIAR(arXiv 2401.03310)가 드론을 ITU metal 재질로 Sionna 씬에 넣고, "
            "Cazzella(arXiv 2507.19173)·VaN3Twin(arXiv 2505.14184)이 차량 메시를 부품 단위로 갈라 재질을 준다. "
            "AirGuard(IEEE JSAC accepted)는 실제 DJI .obj 메시를 부른다.",
            "now_ko": "문장에서 **산란적분을 주어 자리로** 옮겼다: '드론 기체의 3-D 표면 메시를 산란적분에 "
            "통과시켜 그 진폭을 보고한 논문이 0편' 이 살아남는 문장이다. 메시를 씬에 넣은 선행은 여럿 있고, "
            "그 메시가 하는 일은 전파 상호작용이지 σ 산출이 아니다.",
            "evidence": {
                "json": "outputs/deepread_reconcile.json : claim_status.C1 (verdict=NARROWED, "
                "counterexamples_to_the_loose_reading 5건)"
            },
            "why_on_a_slide": "⭐ 이것이 이 발표에서 가장 반증당하기 쉬운 문장이었다. 우리가 먼저 좁히지 않으면 "
            "청중이 CAVIAR 한 편으로 슬라이드를 무너뜨린다.",
            "attack": "그렇게 좁히면 남는 게 거의 없지 않은가.",
            "answer": "좁혀도 남는 것이 정확히 우리 기여다 — 산란적분·재질 가중·자세 분해. "
            "그리고 좁힌 문장은 H8 4관문 판정(12편 중 0편 통과)이 그림으로 뒷받침한다.",
        },
        {
            "id": "R10",
            "rank": 10,
            "headline_ko": "(보너스) 'Chen 이 같은 기호로 냈다' — 기호 주장도 부정확했다",
            "we_said": "Chen 2024 가 v_max 를 우리와 **같은 기호로** 먼저 냈다.",
            "what_broke_it": "Chen 20쪽 전문에 'PRF' 는 **0회**, 'pulse repetition' 0회, 'Nyquist' 0회다 — "
            "내가 이번에 직접 세었다. 같은 것은 eq.(4)의 β·δ 기호뿐이고, 반복률 기호는 공유하지 않는다.",
            "now_ko": "'β·δ 기호는 같지만 PRF 표기는 없다' 로 정확히 쓴다. 그리고 β·δ 조차 Chen 의 것이 아니라 "
            "[16] Samczynski 외 TGRS 인용이다.",
            "evidence": {
                "pdf": PDF_CHEN,
                "command": "fitz 전문 추출 후 정규식 계수 — PRF 0 / pulse repetition 0 / Nyquist 0",
                "verified_by_me": "이번 라운드에 직접 계수",
            },
            "why_on_a_slide": "R1 과 묶어 한 줄로만 보인다. 요점은 '같다' 는 말도 근거를 대고 해야 한다는 것.",
            "attack": "기호가 다르면 같은 식이 아니라는 뜻인가.",
            "answer": "아니다 — 반대다. Chen 은 그 식을 아예 표시하지 않았고(F07), 진짜 선행은 "
            "Abratkiewicz 다. 기호 계수는 우리 이전 서술이 얼마나 성급했는지를 보여주는 지표로만 쓴다.",
        },
    ]


# ────────────────────────────────────────────────────────────────────────────
# 5. 열린 구멍
# ────────────────────────────────────────────────────────────────────────────
def build_gaps(R: dict) -> list[dict]:
    return [
        {
            "id": "G1",
            "title_ko": "Chen 외, Applied Sciences 14(10):4282 (2024, 게재) — 우리의 가장 가까운 선행",
            "was": "MDPI 가 403 을 돌려줘 원문 미확보. LaSen 의 요약을 통한 2차 정보뿐이었다.",
            "status_now": "✅ CLOSED — 확보하고 20쪽 전문을 읽었다.",
            "how": "Semantic Scholar OA 미러(HTTP 200, application/pdf). MDPI 직접 경로는 여전히 403.",
            "evidence": {
                "pdf": PDF_CHEN,
                "sha256": "59593346f4fc540cfbeb04c81c23483d565205bcc87a15911dbfcda5c5da8472",
                "license": "CC BY 4.0 (원문 명시)",
                "json": "outputs/verify_chen.json : acquisition.G1_chen2024",
            },
            "what_it_changed": "⭐ 두 가지가 바뀌었다. ⑴ Chen 은 닫힌 식을 표시하지 않는다 — 우리가 Chen 에게 "
            "돌렸던 우선권이 틀렸다. ⑵ Chen 의 표적은 스테퍼 모터 회전 모형이고 드론 로터는 동기로만 나온다.",
            "honest_statement_ko": "'우리의 가장 가까운 선행이 2차 정보' 라는 구멍은 닫혔다. 이제 우리는 그 논문을 "
            "직접 인용할 수 있고, 실제로 인용하면 우리 이야기가 더 강해진다.",
        },
        {
            "id": "G2",
            "title_ko": "Abratkiewicz 외, IEEE JSTARS 16:3469-3484 (2023, 게재)",
            "was": "미확보. 서지정보만 있었고 references.bib 에 '본문 문장 인용 금지' 가 걸려 있었다.",
            "status_now": "✅ CLOSED — 확보하고 16쪽 전문을 읽었다. 축자 인용 15건.",
            "how": "Crossref 의 link 필드가 실제 파일 경로를 알려줬고, 그 URL 의 Internet Archive 스냅샷"
            "(2024-04-15)에서 CC-BY 원본을 받았다. IEEE 직접 경로는 502/202/418 로 전부 막혔다.",
            "evidence": {
                "pdf": PDF_ABRAT,
                "sha256": "7a25893831ae16c1acaa0ae8cbb1d51a6e0f76ca95e5437667265ff527a2631e",
                "license": "gold OA, CC BY 4.0 (Crossref license 레코드)",
                "json": "outputs/verify_chen.json : acquisition.G2_abratkiewicz2023",
            },
            "what_it_changed": "⭐⭐ 이 라운드의 헤드라인. 우리 v_max 법칙의 진짜 주인이고, 우리가 기록해둔 "
            "Chen 귀속조차 한 세대 늦었음이 드러났다. 동시에 그들이 드론을 future work 로 남겼다는 문장을 얻었다.",
            "honest_statement_ko": "references.bib 의 인용 금지를 해제하고 DOI 를 채워야 한다.",
        },
        {
            "id": "G3",
            "title_ko": "인용 커버리지 — 81개 지면 엔트리 중 축자 인용은 8건",
            "was": f"엔트리 {R['venue_entries']['entries_total']}건 중 축자 인용 "
            f"{R['venue_entries']['entries_with_verbatim_quote']}건, 출력 전반에 UNVERIFIED 마커 다수.",
            "status_now": "⚠ 부분적으로만 개선. 넓은 코퍼스의 인용 커버리지는 그대로다"
            f"(PDF 가 디스크에 있는 엔트리 {R['venue_entries']['entries_with_pdf_on_disk']}건). "
            f"outputs 전체의 UNVERIFIED 마커는 오히려 {R['unverified_markers_in_outputs']}개로 늘었다 — "
            "검증이 후퇴해서가 아니라 스윕이 더 돌아 미검증 항목이 더 많이 **드러났기** 때문이다.",
            "what_changed": "⭐ 발표가 실제로 인용하는 좁은 코퍼스는 다르다 — 능력 매트릭스 26행 234칸에서 "
            "UNVERIFIED 는 0 이고 인용 80건이 매 빌드 재대조된다. 덱은 넓은 코퍼스가 아니라 이 좁은 코퍼스에서만 인용한다.",
            "honest_statement_ko": "'우리 문헌 조사가 검증되었다' 고 말하면 안 된다. "
            "'덱이 인용하는 26행은 검증되었고, 배후의 81개 엔트리 대부분은 서지 수준이다' 가 참이다.",
            "attack": "그럼 배후 코퍼스의 결론(H8 등)은 어떻게 믿는가.",
            "answer": "H8 판정은 배후 코퍼스가 아니라 전문 판정 12편에서 나왔고, 그 12편은 PDF 를 열었다. "
            "배후 81 엔트리는 '무엇을 아직 안 읽었는지' 의 지도이지 결론의 근거가 아니다.",
        },
        {
            "id": "G4",
            "title_ko": "dblp 구조적 사각지대 — IEEE TAP·AWPL·EuCAP·IET RSN·TMTT",
            "was": "자동 지면 스윕이 dblp 를 썼는데 dblp 는 이 지면들을 색인하지 않는다.",
            "status_now": "⚠ 그대로 열려 있다. 이번 라운드가 바꾸지 않았다.",
            "what_it_means": "이 지면들에서 '못 찾았다' 는 '안 봤다' 라는 뜻이고, 그렇게 말해야 한다. "
            "안테나·전파 지면은 정확히 RCS·회절 논문이 사는 곳이라 사각지대의 방향이 우리에게 가장 나쁘다.",
            "honest_statement_ko": "H8 같은 '없다' 형 주장은 반드시 코퍼스를 명시하고, 이 사각지대를 같은 슬라이드에 적는다.",
            "attack": "그러면 novelty 주장을 할 수 없는 것 아닌가.",
            "answer": "'세계 최초' 는 못 한다. 할 수 있는 것은 '우리가 연 N편의 PDF 안에서, 이 축들을 동시에 "
            "채운 것이 없다' 이고, 그 문장은 매트릭스가 그림으로 증명한다. 그리고 EuCAP 은 이미 수동으로 "
            "들어와 있다 — Ziganshin 이 우리 최강 경쟁 행이다.",
        },
        {
            "id": "G5",
            "title_ko": "φ=90° 단일 방위 — 발표된 모든 검출 결과가 한 컷이다",
            "was": "src/experiment_freespace_range.py:322,773 의 phi_deg=90.0 에서 모든 결과가 나왔다.",
            "status_now": "⚠ 그대로 열려 있다. 크기는 이번에 계량되었다 — φ=90° 에서 기하 차 0.118 dB, "
            f"φ 를 쓸면 최대 {R['phi_sensitivity']['absmax_over_phi_db']:.2f} dB.",
            "correction_of_our_own_wording": "⭐ '하드코딩' 이 아니라 **기본 인자**다. 결함은 코드가 아니라 보고에 있다 — "
            "φ 스윕을 보고한 적이 없다.",
            "evidence": {
                "json": "outputs/geometry_grid.json : traps[T1b] · range_normalisation.*.absmax_over_phi_db",
                "code": "src/experiment_freespace_range.py:322,773",
            },
            "honest_statement_ko": "기하 축의 결론은 φ 를 쓸기 전까지 잠정이다. 슬라이드에 '단일 방위' 를 명시한다.",
            "attack": "그러면 지금 발표하는 검출 결과는 다 무효인가.",
            "answer": "무효는 아니다 — 무모호 속도 축은 φ 와 무관하고(F10), 링크버짓 축만 φ 에 매달린다. "
            "영향 범위를 그렇게 좁혀 말한다.",
        },
        {
            "id": "G6",
            "title_ko": "(새로 연) 3GPP 원 규격을 직접 확인하지 않았다",
            "was": "-",
            "status_now": "⚠ 새로 명시한 구멍. CSI-RS 최소 주기 500 Hz 는 LaSen 의 TS 38.331 인용과 "
            "Chen §3 의 슬롯 목록으로 산술 정합만 확인했고, TS 38.331/38.214 원문은 열지 않았다.",
            "honest_statement_ko": "슬라이드에서 500 Hz 옆에 '3GPP TS 38.331 (2차 인용)' 을 붙인다.",
            "attack": "규격 하나 확인 못 했다는 것인가.",
            "answer": "확인할 수 있었지만 이번 라운드에 하지 않았고, 그래서 그렇게 적는다. "
            "그리고 이 값은 우리 결론을 **약하게** 만드는 방향이 아니다 — 실측 상용망은 50~200 Hz 로 더 낮다.",
        },
        {
            "id": "G7",
            "title_ko": "(새로 연) 바이스태틱 도플러 식의 계보 한 단계 위",
            "was": "-",
            "status_now": "⚠ Chen eq.(4) 의 출처인 Samczynski 외, '5G network-based passive radar', "
            "IEEE TGRS 2021/2022 원문 미확보. 계보가 한 단계 남았다.",
            "honest_statement_ko": "'이 식의 계보는 바르샤바 학파로 수렴한다' 까지만 말하고, "
            "'Samczynski 가 최초' 라고는 말하지 않는다.",
            "attack": "그 위에는 더 없는가.",
            "answer": "바이스태틱 도플러는 표준 교재 수준의 식이라 '최초' 를 추적하는 것이 의미가 적다. "
            "우리가 추적하는 것은 **5G 맥락에서 이 한계를 명시한 최초** 이고, 그것이 Abratkiewicz 2023 이다.",
        },
    ]


# ────────────────────────────────────────────────────────────────────────────
# 6. 한 문장 포지션
# ────────────────────────────────────────────────────────────────────────────
def build_position(R: dict) -> dict:
    return {
        "one_sentence_ko": "우리는 새 물리를 주장하지 않는다 — 우리는 드론 기체 메시에서 재질 가중 산란을 "
        "계산하고, 그 σ 를 세 기하·세 조명원 격자에 넣어, 이미 알려진 무모호 속도 한계"
        "(Abratkiewicz, IEEE JSTARS 2023, eq.16)를 네 표준에 걸쳐 하나의 규약으로 평가하며 "
        "교정된 검출성능까지 잇는다. 우리가 연 26편 중 이 여섯 축을 동시에 채운 것은 없고, "
        "우리도 회절과 로터 두 축은 비어 있다.",
        "one_sentence_en": "We claim no new physics: we compute material-weighted scattering from "
        "whole drone airframe meshes, carry that sigma through a three-geometry x three-illuminator "
        "grid, and evaluate a known unambiguous-velocity limit (Abratkiewicz, IEEE JSTARS 2023, "
        "eq.16) across four standards under one stated convention, all the way to CFAR-calibrated "
        "detection - a combination no row in our 26-paper matrix fills, and one where two of our own "
        "columns (diffraction, rotor) are still empty.",
        "derivation_ko": [
            "우리가 FULL 인 여섯 열: engine · mesh · material · aspect · geometry · vmax "
            "(26행 중 이 여섯을 동시에 채운 유일한 행).",
            "빼야 하는 열: rotor(NONE, future work 로 강등) · diffraction(NONE, 우리 최대 물리 공백) · "
            "amplitude validation(PARTIAL, 해석 PO 구까지).",
            "가장 가까운 경쟁: Ziganshin(EuCAP'25 게재 / arXiv'26 프리프린트) 6/9 동점 — 회절은 우리보다 "
            "앞서고 표적은 자동차·구·원기둥이며 PEC 이고 무모호 속도를 다루지 않는다.",
            "다음 경쟁: RadarTwin(arXiv'26) 은 engine·mesh·material·aspect 를 채우지만 vmax·geometry 가 비어 있다.",
            "vmax 가 FULL 인 선행(Abratkiewicz JSTARS'23 · Geng IET RSN'20 · Jopanya SPAWC'25)은 "
            "전부 산란을 계산하지 않는다.",
            "⭐ 반드시 붙는 한정어 둘 — ⑴ '조명원 **종류**를 통제 비교' (한 조명원 '안'의 자원 비교는 "
            "Taylor & Poullin, IEEE TAES 61(4), 2025 게재가 이미 했다, F28). "
            "⑵ '메시를 **산란적분에 통과**' (씬에 메시를 넣은 선행은 여럿 있다, F30).",
        ],
        "hostile_questions": [
            {
                "q": "새로운 게 뭔가. 식도 남의 것, 엔진도 남의 것(Mitsuba), 표적도 남의 CAD 아닌가.",
                "a": "새 물리는 없다고 먼저 말한다. 새로운 것은 **연결**이다 — 기체별 재질 가중 σ 가 "
                "격자를 통과해 교정된 Pd 까지 한 파이프라인으로 이어진다. 매트릭스가 보여주는 것은 "
                "그 연결을 26편 중 아무도 끝까지 하지 않았다는 것이다. 그리고 어느 조각이 남의 것인지 "
                "칸마다 인용으로 적어 뒀다.",
            },
            {
                "q": "회절이 없으면 σ 가 틀린 것 아닌가. 그러면 뒤의 모든 결과가 틀린다.",
                "a": "밴드 **기울기**가 실측보다 3.5~8배 가파르다는 것은 우리가 먼저 말한다(F24). "
                "다만 절대 레벨은 앵커로부터 0.00 dB 이동하므로 앵커가 레벨을 고쳐준 적이 없고(F20), "
                "우리는 절대 σ 판정을 보류한다. 검출 결과는 σ 의 **상대 순서**(기체 간·자세 간)에 주로 "
                "의존하고, 절대 레벨은 링크버짓 상수로 흡수된다 — 그 의존성을 슬라이드에 명시한다.",
            },
            {
                "q": "무향실 시뮬레이션이 실제 배치와 무슨 상관인가.",
                "a": "상관없다고 인정하는 것이 정답이다. 챔버는 **통제된 비교대**이지 배치 예측이 아니다. "
                "배치 주장은 실측(외부 필드테스트, X410)으로만 한다. 그리고 우리가 인용하는 실측 앵커는 "
                "우리 것이 아니라 공개 문헌 RCS 다.",
            },
            {
                "q": "그 6/9 는 자기 채점 아닌가.",
                "a": "그렇다. 그래서 채점표가 아니라 **근거표**를 낸다 — 234칸 중 80칸이 축자 인용이고 "
                "빌드가 매 실행 PDF 와 재대조한다(80/80 통과). 판정에 동의하지 않으면 근거를 보고 "
                "다시 채점할 수 있다. 그리고 우리 행에도 NONE 이 두 개 있다.",
            },
        ],
        "do_not_say": [
            "⛔ '무모호 속도 식을 우리가 제시한다/유도한다' — Abratkiewicz 2023 eq.(16) 이 문자 그대로 같다.",
            "⛔ '반복주기가 무모호 속도를 정한다는 관찰이 새롭다' — 2023년 JSTARS 초록에 있다.",
            "⛔ '5G SSB 가 1 m/s 대에서 접힌다는 것을 우리가 처음 보인다' — ±1.0901 m/s 로 이미 적혀 있다.",
            "⛔ 'ΔR = c/B 규약이 우리 선택' — Abratkiewicz eq.(15)/Malanowski 교재가 근거다.",
            "⛔ 'SSB 상시성 프레임이 우리 것' — Abratkiewicz 서론 문장이다.",
            "⛔ '광선추적은 RCS 를 못 낸다' — SBR 은 계산한다. 참인 문장은 'Sionna 기본 solver 에 산란적분이 없다' 뿐이다.",
            "⛔ 'Sionna 에는 회절이 없다' — 1차 UTD 쐐기 회절이 있다.",
            "⛔ '드론 RCS 를 Sionna 로 낸 논문은 세상에 없다' — 코퍼스를 밝히지 않은 전칭 주장은 금지.",
            "⛔ 다운링크 점유를 성능 축으로 삼는 관점이 우리 것 — Abratkiewicz §V 가 3단계로 이미 갖고 있다.",
            "⛔ 접힘 해제(dealiasing) 대책을 우리가 제안한다 — 제안하지 않는다. eq.(17)-(20) 이 선행이다.",
            "⛔ '다중 Rx 10log10(N) 이상 상한' 이 우리 규약 — Taylor & Poullin(IEEE TAES 61(4), 2025, 게재) "
            "p.8814 에 10log10(7)=8.4 dB 로 이미 있다.",
            "⛔ 'hover blind 를 우리가 발견했다' — 게재 실측 선례가 둘 있다.",
            "⛔ '한 표적·한 검출기·교정 오경보율의 통제 비교를 아무도 안 했다' — 조명원 '종류' 한정어 없이 쓰면 "
            "Taylor & Poullin 이 즉시 반례다.",
            "⛔ '스톡 Sionna 에 회절이 없다' — 1차 UTD 쐐기 회절이 있고 PathSolver 기본값이 False 일 뿐이다.",
            "⛔ '드론 메시를 Sionna 씬에 넣은 논문이 없다' — CAVIAR 등 반례가 있다. "
            "'산란적분에 통과시킨' 을 반드시 넣는다.",
        ],
    }


# ────────────────────────────────────────────────────────────────────────────
# 7. 랭킹
# ────────────────────────────────────────────────────────────────────────────
def build_ranking() -> dict:
    return {
        "rule_ko": "연구실 청중이 무엇을 재미있어 하는가로 정렬했다. 우리 엔진이 아니라 "
        "⑴ 교차표준 속도표와 그 우선권 이야기, ⑵ 철회 목록이 가장 강하다.",
        "order": [
            {
                "slot": 1,
                "what": "철회 목록 (R1~R10, 슬라이드에는 R1·R3·R5·R8 네 개만)",
                "why_ko": "⭐ 이 방의 누구도 자기 정정을 슬라이드에 올리지 않는다. 그래서 가장 기억에 남고 "
                "가장 신뢰를 산다. 특히 R1(우선권을 두 번 고쳤다)과 R5(고쳤더니 우리에게 유리해졌다)는 "
                "'이 팀은 자기 결론에 유리한 방향으로만 고치지 않는다' 를 한 장으로 증명한다.",
            },
            {
                "slot": 2,
                "what": "교차표준 무모호 속도표 + 실기체 최고속도 겹치기 (F02, F03, F05, F06)",
                "why_ko": "숫자 네 개가 289배 벌어지고, 그 위에 드론 다섯 대의 최고속도를 겹치면 "
                "'5G 상시신호로는 나는 드론을 못 잰다' 가 한 그림으로 끝난다. 그리고 그 식의 주인이 "
                "'드론은 아직' 이라고 자기 논문 결론에 적어 놓았다 — 이게 이 발표의 최고 문장이다.",
            },
            {
                "slot": 3,
                "what": "능력 매트릭스 그림 (F12~F15)",
                "why_ko": "사용자 추적표의 형식이고, 산문 열 줄이 하는 일을 한 장이 한다. "
                "'9/9 인 행은 없다' 와 '우리 행도 두 칸 비었다' 를 같이 보여주는 것이 핵심.",
            },
            {
                "slot": 4,
                "what": "열린 구멍 G1~G7 (특히 G1·G2 가 닫혔다는 것)",
                "why_ko": "지난 발표에서 '가장 가까운 선행이 2차 정보' 였던 것을 이번에 닫았다. "
                "진척으로 읽히고, 남은 구멍을 스스로 열거하는 것이 다시 신뢰가 된다.",
            },
            {
                "slot": 5,
                "what": "회절 열 (F14, F22, F23, F24)",
                "why_ko": "우리 최대 공백이면서 동시에 이 분야 전체의 공백이다(26행 중 3편). "
                "약점을 분야 지형으로 바꾸는 슬라이드.",
            },
            {
                "slot": 6,
                "what": "엔진 검증 (F19, F20, F26)",
                "why_ko": "⚠ 가장 공들인 부분이지만 청중에게는 가장 덜 재미있다. "
                "0.2006 dB 같은 수는 신뢰의 배경음이지 헤드라인이 아니다. 뒤로 보낸다.",
            },
            {
                "slot": "백업",
                "what": "우리 문구를 좁히는 선행 (F28~F32) — 슬라이드 아님, 질문 대비",
                "why_ko": "⭐ 발표에 넣지 않되 **손에 들고 있는다**. Taylor & Poullin 이나 CAVIAR 를 아는 "
                "청중이 손을 들면 그 자리에서 인용으로 답해야 한다. '몰랐다' 가 가장 나쁜 답이다. "
                "F28 만은 본편 인용으로 올린다 — 우리 벤치마크 설계의 선행 방법론이기 때문이다.",
            },
        ],
        "warning_ko": "⚠ 우리가 가장 오래 붙든 것(SBR 커널)을 앞에 두고 싶은 유혹이 있다. 두면 안 된다.",
    }


# ────────────────────────────────────────────────────────────────────────────
# 8. 마크다운
# ────────────────────────────────────────────────────────────────────────────
def render_md(doc: dict) -> str:
    L: list[str] = []
    A = L.append
    m = doc["meta"]
    A("# DECK_FACTS — 0804 팀미팅 덱이 인용해도 되는 사실 기반")
    A("")
    A(f"생성 {m['generated']} · 생성기 `{m['script']}` · 런타임 {m['runtime_s']:.1f} s")
    A("")
    A("> **증거 규칙**  한 주장은 (a) 내가 직접 연 PDF 의 축자 문장이거나, (b) 디스크의 JSON 에서 "
      "우리가 계산했고 재현 가능하거나, 둘 중 하나다. 나머지는 UNVERIFIED 로 라벨하거나 뺀다.")
    A("> 인용은 매 빌드 PDF 페이지 텍스트에 재대조된다. 개수 주장은 **코퍼스 이름을 달고 다닌다**.")
    A("")
    c = doc["counts"]
    A(f"**사실 {c['facts']}건**(축자 인용 {c['facts_quoted']} · 우리 계산 {c['facts_computed']} · "
      f"SECONDHAND {c['facts_secondhand']} · UNVERIFIED {c['facts_unverified']}) · "
      f"**철회 {c['retractions']}건** · **열린 구멍 {c['open_gaps']}건** · "
      f"자체검사 {c['checks_passed']}/{c['checks_total']} 통과 "
      f"(인용 재대조 {c['quotes_rechecked']}건)")
    if c["secondhand_ids"]:
        A("")
        A(f"⚠ SECONDHAND {c['secondhand_ids']} — 다른 라운드가 연 PDF 의 인용에 기댄다. "
          "슬라이드에 올리기 전 원문을 직접 열 것.")
    A("")
    A("---")
    A("")

    # 포지션
    p = doc["position"]
    A("## 0. 한 문장 포지션 (적대적 질문을 견디도록 쓴 판)")
    A("")
    A(f"> **{p['one_sentence_ko']}**")
    A("")
    A(f"*(EN)* {p['one_sentence_en']}")
    A("")
    A("**어떻게 나왔는가**")
    for d in p["derivation_ko"]:
        A(f"- {d}")
    A("")
    A("**적대적 질문 4개와 답**")
    for hq in p["hostile_questions"]:
        A(f"- **Q. {hq['q']}**")
        A(f"  - A. {hq['a']}")
    A("")
    A("**절대 말하지 않는다**")
    for s in p["do_not_say"]:
        A(f"- {s}")
    A("")
    A("---")
    A("")

    # 랭킹
    rk = doc["ranking"]
    A("## 1. 슬라이드 순서 — 청중이 재미있어 하는 순")
    A("")
    A(rk["rule_ko"])
    A("")
    A("| # | 무엇 | 왜 |")
    A("|---|---|---|")
    for o in rk["order"]:
        A(f"| {o['slot']} | {o['what']} | {o['why_ko']} |")
    A("")
    A(rk["warning_ko"])
    A("")
    A("---")
    A("")

    # 철회
    A("## 2. ⭐ 철회 목록 — 이 프로젝트가 스스로 내린 주장들")
    A("")
    A("⚠ 이 절은 **슬라이드에 올린다**. 자기 정정을 보여주는 팀은 신뢰받고, 조용히 지우는 팀은 그렇지 않다. "
      "여기 있는 것은 실패가 아니라 감사가 작동한 기록이다.")
    A("")
    for r in doc["retractions"]:
        A(f"### {r['id']}. {r['headline_ko']}")
        A("")
        A(f"- **우리가 말했던 것** — {r['we_said']}")
        A(f"- **무엇이 그것을 깼는가** — {r['what_broke_it']}")
        A(f"- **지금 참인 것** — {r['now_ko']}")
        ev = r["evidence"]
        src = " · ".join(f"`{k}`: {v}" if not isinstance(v, dict) else f"`{k}`: {json.dumps(v, ensure_ascii=False)}"
                         for k, v in ev.items())
        A(f"- **근거** — {src}")
        A(f"- **왜 슬라이드에 올리는가** — {r['why_on_a_slide']}")
        A(f"- **⭐ 예상 공격** — {r['attack']}")
        A(f"- **우리 답** — {r['answer']}")
        A("")
    A("---")
    A("")

    # 사실
    A("## 3. 사실 기반 — 슬라이드에 올려도 되는 것 전부")
    A("")
    A("각 항목: 한 문장 주장 · 증거 등급 · 정확한 출처 · **예상 공격과 우리 답**. "
      "공격을 예상하지 못한 사실은 아직 생각해보지 않은 사실이다.")
    A("")
    cur = None
    for f in doc["facts"]:
        if f["tier"] != cur:
            cur = f["tier"]
            A(f"### [{cur}]")
            A("")
        A(f"#### {f['id']} · {f['claim_ko']}")
        A("")
        A(f"- **등급** `{f['grade']}`")
        A(f"- **EN** {f['claim_en']}")
        s = f["source"]
        for k, v in s.items():
            if k.startswith("quote"):
                A(f"- **{k}** > {v}")
            else:
                A(f"- **{k}** `{v}`")
        if f.get("numbers"):
            A(f"- **수치** `{json.dumps(f['numbers'], ensure_ascii=False)}`")
        if f.get("caveat"):
            A(f"- {f['caveat']}")
        A(f"- **⭐ 예상 공격** — {f['attack']}")
        A(f"- **우리 답** — {f['answer']}")
        A("")
    A("---")
    A("")

    # 구멍
    A("## 4. 열린 구멍 — 이번 워크플로 뒤의 정직한 상태")
    A("")
    for g in doc["open_gaps"]:
        A(f"### {g['id']}. {g['title_ko']}")
        A("")
        A(f"- **이전** — {g['was']}")
        A(f"- **지금** — {g['status_now']}")
        if g.get("how"):
            A(f"- **어떻게** — {g['how']}")
        if g.get("what_it_changed"):
            A(f"- **무엇이 바뀌었는가** — {g['what_it_changed']}")
        if g.get("what_changed"):
            A(f"- **무엇이 바뀌었는가** — {g['what_changed']}")
        if g.get("what_it_means"):
            A(f"- **뜻** — {g['what_it_means']}")
        if g.get("correction_of_our_own_wording"):
            A(f"- **우리 표현 정정** — {g['correction_of_our_own_wording']}")
        if g.get("evidence"):
            A(f"- **근거** — `{json.dumps(g['evidence'], ensure_ascii=False)}`")
        A(f"- **정직한 문장** — {g['honest_statement_ko']}")
        if g.get("attack"):
            A(f"- **⭐ 예상 공격** — {g['attack']}")
            A(f"- **우리 답** — {g['answer']}")
        A("")
    A("---")
    A("")

    # 자체검사
    A("## 5. 자체검사 — 이 문서가 스스로 확인한 것")
    A("")
    A("| 검사 | 결과 | 내용 |")
    A("|---|---|---|")
    for ck in doc["self_check"]["checks"]:
        A(f"| `{ck['id']}` | {'✅' if ck['passed'] else '❌'} | {ck['detail']} |")
    A("")
    if doc["self_check"]["problems"]:
        A("**실패한 검사**")
        for p_ in doc["self_check"]["problems"]:
            A(f"- ❌ {p_}")
    else:
        A("실패 0건.")
    A("")
    return "\n".join(L)


# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    t0 = time.time()
    R = recompute()

    # 인용 재대조
    verify_quote("A2", PDF_ABRAT, "The Doppler range is limited by T")
    verify_quote("A4", PDF_ABRAT, "one can obtain the maximum unambiguous bistatic velocity of")
    verify_quote("A6", PDF_ABRAT, "describes how many times the velocity is aliased")
    verify_quote("A9", PDF_ABRAT, "The cooperative target was a car")
    verify_quote(
        "A10", PDF_ABRAT, "drones whose reflectivity is significantly lower than the car"
    )
    verify_quote("A7", PDF_ABRAT, "The default, and most often used, SSB periodicity is 20 ms")
    verify_quote("C4", PDF_CHEN, "the maximum unambiguous Doppler frequency is 50 Hz")
    verify_quote("C9", PDF_CHEN, "resulting in Doppler blur")
    verify_quote(
        "C11", PDF_CHEN, "a rotating target experimental model employing a stepper motor"
    )
    verify_quote("TR47", PDF_SIONNA_TR, "is implemented in Sionna")
    verify_quote("TAY28", PDF_TAYLOR, "The highest SNR is obtained by using all the symbols")
    verify_quote("TAY29", PDF_TAYLOR, "the ideal gain one could expect would be of 10 log")
    verify_quote("TAY.p4", PDF_TAYLOR, "a DJI Phantom 4 drone evolving above the surveillance antenna")
    # ⚠ 다른 라운드가 이 논문 표적을 'Phantom 3' 으로 적었다. 원문은 Phantom 4 다 — 아래가 그 증거.
    check(
        "REC.phantom",
        "phantom 3" not in pdf_text(PDF_TAYLOR),
        "Taylor & Poullin 표적은 Phantom 4 다 — 전문에 'Phantom 3' 문자열이 없다"
        "(outputs/deepread_reconcile.json 의 'DJI Phantom 3' 기재는 정정 대상)",
    )
    # Chen 전문에 반복률 기호가 없다는 계수(R10 의 근거)
    _ct = pdf_text(PDF_CHEN)
    _prf = len(re.findall(r"\bprf\b", _ct))
    check(
        "R10.prf",
        _prf == 0,
        f"Chen 2024 전문의 'PRF' 출현 {_prf}회 — '같은 기호로 냈다' 는 우리 서술의 반례",
    )

    facts = build_facts(R)
    doc = {
        "meta": {
            "script": "benchmark/deck_facts.py",
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run": "cd /workspace/sionna && PYTHONPATH=src:benchmark "
            "~/.venvs/py312/bin/python benchmark/deck_facts.py",
            "purpose_ko": "0804 팀미팅 덱이 인용해도 되는 검증된 사실 기반. "
            "덱은 이 파일 밖의 수를 인용하지 않는다.",
            "evidence_rule_ko": "(a) 내가 직접 연 PDF 의 축자 문장 또는 (b) 디스크 JSON 에서 우리가 계산한 "
            "재현 가능한 수. 나머지는 UNVERIFIED.",
            "house_rules_ko": "인용은 지면·게재상태·연도를 달고 다닌다. 프리프린트는 arXiv ID 를 단다. "
            "Ziganshin 회의판(게재)과 저널판(프리프린트)을 절대 섞지 않는다. "
            "모든 개수 주장은 코퍼스 이름을 단다.",
            "inputs": [
                "outputs/verify_chen.json",
                "outputs/capability_matrix.json",
                "outputs/geometry_grid.json",
                "outputs/sigma_anchor.json",
                "outputs/sbr_kr_sweep.json",
                "outputs/verify_cfar.json",
                "outputs/reflib_sweep_sionna.json",
                "outputs/report01_paper.json",
                "outputs/cpi_guard_sweep.json",
                "outputs/monostatic_prior.json",
                "outputs/vmax_grid.json",
                "outputs/psolve_diffraction.json",
                "outputs/rcs_anchor.json",
                "outputs/report02_derived.json",
                "outputs/reflib_sweep_venues.json",
            ],
            "runtime_s": 0.0,
        },
        "position": build_position(R),
        "ranking": build_ranking(),
        "retractions": build_retractions(R),
        "facts": facts,
        "open_gaps": build_gaps(R),
        "recomputed": R,
        "self_check": {
            "method_ko": "모든 헤드라인 숫자는 빌드가 상류 JSON 에서 다시 계산해 기록값과 대조한다. "
            "인용문은 정규화 후 PDF 페이지 텍스트에 실제로 들어 있는지 재대조한다.",
            "checks": CHECKS,
            "problems": PROBLEMS,
        },
        "counts": {},
    }
    doc["counts"] = {
        "facts": len(facts),
        "facts_quoted": sum(1 for f in facts if f["grade"].startswith("quoted")),
        "facts_computed": sum(1 for f in facts if f["grade"].startswith("computed")),
        "facts_secondhand": sum(1 for f in facts if f["grade"].startswith("SECONDHAND")),
        "facts_unverified": sum(1 for f in facts if "UNVERIFIED" in f["grade"]),
        "secondhand_ids": [f["id"] for f in facts if f["grade"].startswith("SECONDHAND")],
        "facts_with_attack": sum(1 for f in facts if f.get("attack")),
        "retractions": len(doc["retractions"]),
        "open_gaps": len(doc["open_gaps"]),
        "gaps_closed": sum(1 for g in doc["open_gaps"] if g["status_now"].startswith("✅")),
        "do_not_say": len(doc["position"]["do_not_say"]),
        "checks_total": len(CHECKS),
        "checks_passed": sum(1 for c in CHECKS if c["passed"]),
        "checks_failed": len(PROBLEMS),
        "quotes_rechecked": sum(1 for c in CHECKS if c["id"].startswith("Q.")),
    }
    doc["meta"]["runtime_s"] = time.time() - t0

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(render_md(doc))

    print(f"[deck_facts] {OUT_JSON}  ({os.path.getsize(OUT_JSON)/1024:.1f} KB)")
    print(f"[deck_facts] {OUT_MD}  ({os.path.getsize(OUT_MD)/1024:.1f} KB)")
    print(f"[deck_facts] 사실 {doc['counts']['facts']}건 · 철회 {doc['counts']['retractions']}건 · "
          f"구멍 {doc['counts']['open_gaps']}건(닫힘 {doc['counts']['gaps_closed']})")
    print(f"[deck_facts] 자체검사 {doc['counts']['checks_passed']}/{doc['counts']['checks_total']} 통과 "
          f"(인용 재대조 {doc['counts']['quotes_rechecked']}건 포함)")
    if PROBLEMS:
        print("[deck_facts] ⚠ 실패:")
        for p_ in PROBLEMS:
            print("   -", p_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
