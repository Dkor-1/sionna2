# -*- coding: utf-8 -*-
"""
report15_attack_physics_post.py — 공격 실험 후처리 · 판정
================================================================================
report15_attack_physics.py 가 남긴 JSON 을 열어 **판정에 필요한 요약**을 덧붙인다.
GPU 를 쓰지 않는다(순수 numpy + 파일 판독).

덧붙이는 것
  · q1_flag_census 재계산 — 공격 스크립트 자신을 감사 대상에서 뺀다
  · q2_incoherent  — **수렴하는 관측량**(E_inc = Σ|a|²)에도 같은 빗이 있는가
                     (h_coh 는 √spp 로 자라 절대값이 유보라고 원 보고서가 스스로 적었다)
  · q1_summary / q2_summary / q4_summary — 판정 문장이 딛는 수치
  · repair_integrity — mini2 격자 복구본이 중간저장 백업과 원소 단위로 같은가
  · verdict — SOUND / PREMATURE / BROKEN
⛔ 숫자 손입력 금지.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report15_verdict as VD                                          # noqa: E402
import report15_verdict_geomref as GR                                  # noqa: E402
from drones import DRONES                                              # noqa: E402

#  ⚠ report15_attack_physics 를 import 하면 mitsuba/GPU 가 올라간다. 필요 없다 —
#     §0 이 이미 **모든 PathSolver 호출**을 JSON 에 남겼으므로 거기서 자기 파일만 빼고 다시 센다.

OUT_JSON = os.path.join(ROOT, "outputs", "report15_attack_physics.json")


def _f(o):
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


def comb_cos(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    n = min(a.size, b.size); a, b = a[:n], b[:n]
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else 0.0


# --------------------------------------------------------------------------- #
def sec_incoherent(J) -> dict:
    """E_inc(위상무관 에너지, spp 에 대해 수렴함)에도 같은 조화 빗이 있는가."""
    out = {}
    for key, L in J["q1q2_ladder"].items():
        rows = {}
        for k, B in L["blocks"].items():
            X = np.asarray([[np.nan if v is None else float(v) for v in row]
                            for row in B["inc_prop"]], float)
            if not np.isfinite(X).all() or X.size == 0:
                rows[k] = dict(available=False,
                               finite_frac=float(np.mean(np.isfinite(X))) if X.size else 0.0)
                continue
            P = 10.0 ** (X / 10.0)                    # dB → 선형 전력
            Pm = P.mean(axis=1)
            H = VD.harm_seeded(P.astype(complex))     # 실수열이지만 같은 분해기를 쓴다
            E = VD.edge_bin(H)
            an = J["q1q2_analysis"][key]["blocks"][k]["prop"]
            rows[k] = dict(
                available=True,
                level_db=float(10 * np.log10(Pm.mean() + 1e-300)),
                modulation_ptp_db=float(np.ptp(10 * np.log10(Pm + 1e-300))),
                modulation_index=float(np.ptp(Pm) / (Pm.mean() + 1e-300)),
                ac_over_noise_db=H["total_ac_over_noise_db"],
                peak_bin=E["peak_bin"], edge_bin=E["edge_bin"],
                comb_cos_vs_coherent=(comb_cos(H["harm_abs"], an["harm_abs"])
                                      if not an.get("empty", True) else None),
                comb_cos_vs_geom=(comb_cos(H["harm_abs"],
                                           _geom_of(J, key, k)) if _geom_of(J, key, k) else None))
        out[key] = rows
    out["note_ko"] = ("E_inc 는 원 보고서가 '수렴한다' 고 실측한 관측량이다(coh 는 √spp 로 자란다). "
                      "여기에도 같은 빗이 있으면 변조는 코히런트 합의 몬테카를로 부작용이 아니다.")
    return out


_GEOM_CACHE: dict = {}
_POSE_CACHE: dict = {}


def _geom_of(J, key, blockkey):
    """그 칸의 기하 위상 기준 빗(조화 크기) — 같은 메쉬로 왕복 위상만 더한 것."""
    an = J["q1q2_analysis"][key]["blocks"].get(blockkey)
    if not an:
        return None
    ck = (key, float(an["range_m"]), float(an["el_deg"]))
    if ck not in _GEOM_CACHE:
        spec = DRONES[key]
        n = int(J["meta"]["n_phase"])
        #  ⚠ 자세 생성이 포즈당 2~3 초다. 자세는 **기체와 위상에만** 의존하므로 기체당 한 번만
        #     만들어 재사용한다(칸마다 다시 만들면 분석이 수십 분이 된다).
        if key not in _POSE_CACHE:
            period = 360.0 / int(spec.prop_blades)
            phis = np.arange(n) * (period / n)
            _POSE_CACHE[key] = [GR.prop_vertices(spec, float(p)) for p in phis]
        P = _POSE_CACHE[key]
        az = 0.0 if an["el_deg"] in (0.0, 75.0) else float(an.get("az_deg", 0.0))
        tx, rx = GR.antennas(az, float(an["el_deg"]), float(an["range_m"]))
        a, _, _ = GR.comb(GR.geom_wave(P, tx, rx))
        _GEOM_CACHE[ck] = [float(x) for x in a]
    return _GEOM_CACHE[ck]


def _census_from_calls(J) -> dict:
    """§0 이 저장한 PathSolver 호출 목록에서 **공격 스크립트 자신을 빼고** 다시 센다."""
    C = J["q1_flag_census"]
    #  ⚠ 감사 대상은 **판정을 낸 코드**다. 이번 적대검증이 새로 쓴 report15_attack_* 는 전부 뺀다.
    SELF = "benchmark/report15_attack_"
    calls = [c for c in C["calls"] if not c["file"].startswith(SELF)]
    r15 = [c for c in calls if c["file"].startswith("benchmark/report15_")]

    def off(c, k):
        return (k not in c["kwargs"]) or (c["kwargs"][k] in (False, "False"))
    return dict(
        signature_defaults=C["signature_defaults"],
        excluded_file_prefix=SELF,
        n_pathsolver_calls_total=len(calls),
        n_pathsolver_calls_report15=len(r15),
        calls=calls,
        report15_calls=[f"{c['file']}:{c['line']}" for c in r15],
        report15_diffraction_never_enabled=bool(all(off(c, "diffraction") for c in r15)),
        report15_edge_diffraction_never_enabled=bool(
            all(off(c, "edge_diffraction") for c in r15)),
        report15_diffuse_enabled_somewhere=bool(any(
            c["kwargs"].get("diffuse_reflection") not in (None, False, "False") for c in r15)),
        report15_refraction_explicitly_off=bool(all(
            c["kwargs"].get("refraction") in (False, "False") for c in r15)),
        report15_max_depth_values=sorted({str(c["kwargs"].get("max_depth")) for c in r15}),
        note_ko=C["note_ko"])


# --------------------------------------------------------------------------- #
def sec_q1_summary(J) -> dict:
    """Q1 — 회절을 켜면 무엇이 달라지나."""
    rows = {}
    for key, A in J["q1q2_analysis"].items():
        blocks = A["blocks"]
        for cellname in sorted({b["cell"] for b in blocks.values()}):
            bs = blocks.get(f"{cellname}|base_spec")
            sd = blocks.get(f"{cellname}|spec_diffr")
            bp = blocks.get(f"{cellname}|base_prod")
            pd = blocks.get(f"{cellname}|prod_diffr")
            if bs is None or sd is None:
                continue
            r = dict(airframe=key, cell=cellname)
            #  결정론(정반사) 채널 — 회절 OFF vs ON
            r["specular_det"] = dict(
                prop_phase_frac_off=bs["frac_phase_with_prop_path"],
                prop_phase_frac_on=sd["frac_phase_with_prop_path"],
                any_phase_frac_off=bs["frac_phase_with_any_path"],
                any_phase_frac_on=sd["frac_phase_with_any_path"],
                n_prop_mean_off=bs["n_prop_mean"], n_prop_mean_on=sd["n_prop_mean"],
                prop_empty_off=bool(bs["prop"].get("empty", True)),
                prop_empty_on=bool(sd["prop"].get("empty", True)),
                ptp_db_on=(None if sd["prop"].get("empty", True)
                           else sd["prop"]["modulation_ptp_db"]),
                edge_bin_on=(None if sd["prop"].get("empty", True) else sd["prop"]["edge_bin"]),
                edge_over_ftip_on=(None if sd["prop"].get("empty", True)
                                   else sd["prop"]["edge_over_ftip"]),
                comb_cos_vs_geom_on=(None if sd["prop"].get("empty", True)
                                     else sd["prop"]["comb_cos_vs_geom"]),
                continuous_on=bool(sd["frac_phase_with_prop_path"] == 1.0),
                turns_on_where_it_was_empty=bool(
                    bs["frac_phase_with_prop_path"] < 0.5
                    and sd["frac_phase_with_prop_path"] > bs["frac_phase_with_prop_path"]))
            #  확산 채널 — 회절 OFF vs ON
            if bp is not None and pd is not None and not bp["prop"].get("empty", True):
                cmp = J["q1q2_vs_base"][key].get(cellname, {}).get("prod_diffr", {}).get("prop", {})
                r["diffuse"] = dict(
                    d_level_db=cmp.get("d_level_db"), d_ptp_db=cmp.get("d_ptp_db"),
                    waveform_ac_corr=cmp.get("waveform_ac_corr"),
                    comb_cos_vs_base=cmp.get("comb_cos_vs_base"),
                    edge_bin=cmp.get("edge_bin"), edge_bin_base=cmp.get("edge_bin_base"),
                    comb_cos_vs_geom=cmp.get("comb_cos_vs_geom"),
                    comb_cos_vs_geom_base=cmp.get("comb_cos_vs_geom_base"),
                    ac_over_noise_db=cmp.get("ac_over_noise_db"),
                    ac_over_noise_db_base=cmp.get("ac_over_noise_db_base"),
                    edge_over_ftip=cmp.get("edge_over_ftip"),
                    edge_over_ftip_base=cmp.get("edge_over_ftip_base"),
                    d_n_paths_frac=J["q1q2_vs_base"][key][cellname]["prod_diffr"]["d_n_paths_frac"])
            rows[f"{key}/{cellname}"] = r
    #  전체 판단
    det = [r["specular_det"] for r in rows.values()]
    dif = [r["diffuse"] for r in rows.values() if "diffuse" in r]
    return dict(
        by_cell=rows,
        n_cells=len(rows),
        n_cells_specular_turns_on=int(sum(1 for d in det if d["turns_on_where_it_was_empty"])),
        n_cells_specular_continuous_with_diffraction=int(sum(1 for d in det if d["continuous_on"])),
        max_prop_phase_frac_with_diffraction=float(max(d["prop_phase_frac_on"] for d in det)),
        diffuse_min_waveform_corr=(float(min(d["waveform_ac_corr"] for d in dif
                                             if d.get("waveform_ac_corr") is not None))
                                   if dif else None),
        diffuse_max_abs_d_ptp_db=(float(max(abs(d["d_ptp_db"]) for d in dif
                                            if d.get("d_ptp_db") is not None)) if dif else None),
        note_ko=("회절을 켜면 결정론(정반사) 채널에 프롭 경로가 새로 생기는가, 그리고 "
                 "확산 채널의 결론(변조 파형·빗)이 흔들리는가 — 둘을 따로 본다."))


def sec_q2_summary(J) -> dict:
    """Q2 — 더 유리하게 만들 여지가 실제로 남았나(spp↑ · depth↑ · 더 가깝게 · refraction)."""
    rows = {}
    for key, V in J["q1q2_vs_base"].items():
        for cellname, cfgs in V.items():
            for cfg, r in cfgs.items():
                p = r.get("prop", {})
                if p.get("empty_self") or p.get("empty_base"):
                    continue
                rows[f"{key}/{cellname}/{cfg}"] = dict(
                    airframe=key, cell=cellname, config=cfg,
                    d_level_db=p.get("d_level_db"), d_ptp_db=p.get("d_ptp_db"),
                    waveform_ac_corr=p.get("waveform_ac_corr"),
                    ac_over_noise_db=p.get("ac_over_noise_db"),
                    ac_over_noise_db_base=p.get("ac_over_noise_db_base"),
                    d_ac_over_noise_db=((p["ac_over_noise_db"] - p["ac_over_noise_db_base"])
                                        if (p.get("ac_over_noise_db") is not None
                                            and p.get("ac_over_noise_db_base") is not None)
                                        else None),
                    comb_cos_vs_geom=p.get("comb_cos_vs_geom"),
                    comb_cos_vs_geom_base=p.get("comb_cos_vs_geom_base"),
                    edge_over_ftip=p.get("edge_over_ftip"),
                    edge_over_ftip_base=p.get("edge_over_ftip_base"),
                    d_n_paths_frac=r.get("d_n_paths_frac"))
    #  0.5 m 칸이 1 m 칸보다 유리한가 (같은 구성끼리)
    near = {}
    for key, A in J["q1q2_analysis"].items():
        b = A["blocks"]
        for cfg in ("base_prod", "prod_diffr", "spec_diffr", "base_spec"):
            a1 = b.get(f"1/hot|{cfg}")
            a05 = b.get(f"0.5/hot|{cfg}")
            if a1 is None or a05 is None:
                continue
            p1, p05 = a1["prop"], a05["prop"]
            near[f"{key}/{cfg}"] = dict(
                n_prop_mean_1m=a1["n_prop_mean"], n_prop_mean_0p5m=a05["n_prop_mean"],
                level_db_1m=p1.get("level_db"), level_db_0p5m=p05.get("level_db"),
                ptp_db_1m=p1.get("modulation_ptp_db"), ptp_db_0p5m=p05.get("modulation_ptp_db"),
                ac_over_noise_db_1m=p1.get("ac_over_noise_db"),
                ac_over_noise_db_0p5m=p05.get("ac_over_noise_db"),
                comb_cos_vs_geom_1m=p1.get("comb_cos_vs_geom"),
                comb_cos_vs_geom_0p5m=p05.get("comb_cos_vs_geom"),
                edge_over_ftip_1m=p1.get("edge_over_ftip"),
                edge_over_ftip_0p5m=p05.get("edge_over_ftip"),
                prop_phase_frac_1m=a1["frac_phase_with_prop_path"],
                prop_phase_frac_0p5m=a05["frac_phase_with_prop_path"])
    return dict(vs_base=rows, closer_range=near,
                grid_spp_used=int(J["meta"]["spp_base"]),
                spp_ceiling=int(J["meta"]["spp_max"]),
                spp_headroom_factor=float(J["meta"]["spp_max"] / J["meta"]["spp_base"]),
                note_ko=("본 격자는 uint32 한계 4.096e9 의 **절반**인 2.048e9 만 썼다. "
                         "코히런트 관측량이 √spp 로 자라므로 예산 여유는 그 자체로 "
                         "'더 유리하게 할 여지' 다 — 실제로 판정이 바뀌는지 잰다."))


def sec_q4_extra(J) -> dict:
    """Q4 보강 — (a) 준-모노스태틱 바이스태틱 각이 f_tip 예측을 얼마나 바꾸나
                 (b) 한 주기(180°)만 표본하면 어떤 성분이 **구조적으로** 빠지나."""
    out = {"by_cell": {}}
    B = float(J["meta"]["baseline_m"])
    for key, K in J["q4_kinematics"].items():
        for cellkey, an in J["q1q2_analysis"].get(key, {}).get("blocks", {}).items():
            cell = an["cell"]
            R = float(an["range_m"])
            k = f"{key}/{cell}"
            if k in out["by_cell"]:
                continue
            #  TX/RX 가 표적을 사이에 두고 벌어진 각(= 바이스태틱 각 β)
            beta = 2.0 * math.degrees(math.atan((B / 2.0) / R))
            fac = math.cos(math.radians(beta / 2.0))
            out["by_cell"][k] = dict(
                airframe=key, cell=cell, range_m=R, baseline_m=B,
                bistatic_deg=float(beta),
                doppler_bistatic_factor=float(fac),
                f_tip_mono_hz=float(K["f_tip_hz"] * math.cos(math.radians(an["el_deg"]))),
                f_tip_bistatic_hz=float(K["f_tip_hz"] * math.cos(math.radians(an["el_deg"])) * fac),
                relative_error_of_mono_convention=float(1.0 - fac),
                inside_ftip_tolerance=bool((1.0 - fac) < float(VD.TH["ftip_tol"])))
    #  로터 위상 잠금이 실제로 몇 개의 서로 다른 날 방향을 만드는가 (메쉬 규약 그대로 계산)
    from drones import rotor_layout as _rl
    for key in J["q4_kinematics"]:
        spec = DRONES[key]
        lay = _rl(spec)
        nb = int(spec.prop_blades)
        per = 360.0 / nb
        eff = [((float(r["base_ang"]) + int(r["dir"]) * 0.0) % per) for r in lay]
        #  φ 를 여러 값으로 넣어 '서로 다른 유효 날 방향' 개수를 센다 (부호까지 반영)
        cnt = []
        for phi in (0.0, 17.0, 41.0, 73.0):
            v = sorted({round(((float(r["base_ang"]) + int(r["dir"]) * phi) % per), 6)
                        for r in lay})
            cnt.append(len(v))
        out[f"{key}_rotor_phase_lock"] = dict(
            base_ang_deg=[float(r["base_ang"]) for r in lay],
            dirs=[int(r["dir"]) for r in lay],
            base_ang_mod_period_deg=[float(x) for x in eff],
            n_distinct_blade_orientations=cnt,
            n_rotors=len(lay),
            all_rotors_share_one_phase_magnitude=True,
            note_ko=("로터 k 의 스핀 = base_ang_k + dir_k·φ 다. 장착 오프셋이 다르므로 네 로터가 "
                     "같은 날 방향에 있지는 않지만, |φ| 는 하나뿐이라 회전수 분산·위상 지터가 "
                     "없다. 실물은 로터마다 RPM 이 다르고 그것이 스펙트럼 선폭을 만든다."))
    for key, K in J["q4_kinematics"].items():
        out[f"{key}_odd_harmonic_scope"] = dict(
            f_rev_hz=K["f_rev_hz"], f_flash_hz=K["f_flash_hz"],
            sampled_period_deg=K["geometric_period_deg"],
            representable_lines_hz="k·f_flash (k=1..N/2)",
            structurally_absent_ko=("한 주기(180°)만 표본하므로 f_rev 의 **홀수 배** 성분은 "
                                    "표현 자체가 안 된다. 메쉬가 정확히 2회 대칭이라 그 성분이 "
                                    "0 인 것이 맞지만, 실물 프로펠러(날 불일치·허브 비대칭)는 "
                                    "홀수 성분을 낸다 — 이 격자는 그것을 잴 수 없다."),
            rt_periodicity_verified_elsewhere=True)
    out["note_ko"] = ("f_tip 규약은 모노스태틱(2v/λ)이다. 준-모노스태틱 baseline 0.2 m 의 "
                      "바이스태틱 보정은 cos(β/2) 배이고, 그 크기를 여기서 계산해 ±20 % 허용치와 "
                      "비교한다.")
    return out


def sec_q4_diffraction_resolution() -> dict:
    """회절 ON 채널이 64 스텝으로 분해되는가 — 128 스텝 대조 결과를 붙인다."""
    p = os.path.join(ROOT, "outputs", "report15_attack_diffr_alias.json")
    if not os.path.exists(p):
        return dict(available=False,
                    note_ko="회절 격자분해 대조가 없다 — 회절 ON 스펙트럼 폭은 미확정으로 둔다.")
    D = json.load(open(p))
    rows = {}
    for key, A in D["airframes"].items():
        for cname, c in A["cells"].items():
            rows[f"{key}/{cname}"] = {k: c[k] for k in
                                      ("edge_bin_64", "nyquist_bin_64", "edge_bin_128",
                                       "nyquist_bin_128", "edge_at_nyquist_64",
                                       "edge_at_nyquist_128", "comb_cos_first32",
                                       "energy_frac_above_bin32", "ac_over_noise_db_64",
                                       "ac_over_noise_db_128")}
    #  ⚠ '가장자리가 나이키스트 빈과 정확히 같은가' 로 보면 62/64 를 '분해됐다' 고 잘못 읽는다.
    #     제대로 된 시험은 **가장자리가 나이키스트를 따라 움직이는가** 다 — 격자를 2배로 늘렸는데
    #     가장자리도 2배로 따라가면 그 채널은 여전히 분해되지 않은 것이다.
    for k, r in rows.items():
        r["edge_frac_of_nyquist_64"] = (float(r["edge_bin_64"] / r["nyquist_bin_64"])
                                        if r["edge_bin_64"] else None)
        r["edge_frac_of_nyquist_128"] = (float(r["edge_bin_128"] / r["nyquist_bin_128"])
                                         if r["edge_bin_128"] else None)
        r["edge_tracks_nyquist"] = bool(
            r["edge_frac_of_nyquist_64"] is not None
            and r["edge_frac_of_nyquist_128"] is not None
            and r["edge_frac_of_nyquist_64"] >= 0.9 and r["edge_frac_of_nyquist_128"] >= 0.9)
        r["resolved_at_128"] = bool(
            r["edge_frac_of_nyquist_128"] is not None
            and r["edge_frac_of_nyquist_128"] < 0.9
            and r["energy_frac_above_bin32"] < 0.05)
    resolved = bool(rows) and all(r["resolved_at_128"] for r in rows.values())
    return dict(available=True, meta=D["meta"], by_cell=rows,
                diffraction_channel_resolved_at_128=resolved,
                n_cells_edge_tracks_nyquist=int(sum(1 for r in rows.values()
                                                    if r["edge_tracks_nyquist"])),
                max_energy_frac_above_bin32=float(max(r["energy_frac_above_bin32"]
                                                      for r in rows.values())),
                min_comb_cos_first32=float(min(r["comb_cos_first32"] for r in rows.values())),
                diffraction_channel_resolved_at_64=bool(
                    rows and all((r["edge_frac_of_nyquist_64"] or 0) < 0.9
                                 for r in rows.values())),
                note_ko=("회절을 켜면 스펙트럼 가장자리가 나이키스트까지 올라간다. 그것이 "
                         "'정말 넓다' 인지 '격자가 부족하다' 인지는 격자를 2배로 늘려봐야 갈린다. "
                         "128 스텝에서도 가장자리가 나이키스트에 붙어 있으면 그 채널은 **아직 "
                         "분해되지 않은 것**이고, 회절 ON 의 (b) 수치는 인용하면 안 된다 "
                         "— 인용해도 되는 것은 '(b) 판정이 이 플래그에 견고하지 않다' 뿐이다. "
                         "⭐ 반대로 나이키스트 아래(빈 1..32)의 빗은 comb_cos_first32 로 거의 "
                         "그대로였다 — 저차 조화(기하 마이크로도플러가 실린 자리)는 견고하다."))


def sec_q1_diffuse_completeness() -> dict:
    """⭐ Q1 의 짝 — '확산은 켜져 있었다' 는 맞지만, **확산 채널이 표적의 일부만 담는다**.
    Sionna 의 확산 산란은 재질의 산란계수 S 로만 열린다. S=0 인 재질(ITU metal 계열)은
    diffuse_reflection=True 여도 기여가 정확히 0 이다. 그 크기를 면적으로 잰다."""
    from materials import material_params
    from drones import DRONE_GROUP_MAT, build_drone
    out = dict(by_material={}, by_airframe={})
    for mk in sorted({v[0] for v in DRONE_GROUP_MAT.values()}):
        er, sg, S = material_params(mk, 3.5e9)
        out["by_material"][mk] = dict(
            eps_r=float(er), sigma=float(sg), scattering_coefficient_S=float(S),
            diffuse_power_fraction=float(S) ** 2,
            diffuse_power_fraction_db=(float(20 * np.log10(float(S)))
                                       if S > 0 else None),
            contributes_to_diffuse=bool(S > 0))
    for key in ("mini2", "matrice4e"):
        m = build_drone(DRONES[key])
        V = np.asarray(m.v, float); F = np.asarray(m.f, int)
        G = np.asarray(m.g, dtype=object)
        a = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]],
                                          V[F[:, 2]] - V[F[:, 0]]), axis=1)
        tot = float(a.sum())
        by_g = {}
        for g in sorted(set(G.tolist())):
            sel = (G == g)
            mk = DRONE_GROUP_MAT.get(g, (None,))[0]
            S = float(material_params(mk, 3.5e9)[2]) if mk else None
            by_g[g] = dict(area_m2=float(a[sel].sum()), area_frac=float(a[sel].sum() / tot),
                           material=mk, S=S)
        dead = sum(v["area_frac"] for v in by_g.values() if v["S"] == 0.0)
        prop = by_g.get("prop", {})
        out["by_airframe"][key] = dict(
            total_area_m2=tot, by_group=by_g,
            area_frac_with_S_zero=float(dead),
            prop_S=prop.get("S"),
            prop_diffuse_power_fraction=(float(prop["S"]) ** 2 if prop.get("S") else None),
            prop_diffuse_power_fraction_db=(float(20 * np.log10(float(prop["S"])))
                                            if prop.get("S") else None))
    out["note_ko"] = ("판정이 딛는 관측량은 **확산 채널**이다. 그런데 금속 계열(모터·배터리·PCB·"
                      "카메라)은 S=0 이라 확산 기여가 정확히 0 이고, 프로펠러조차 반사전력의 S² "
                      "만 확산으로 간다. 나머지는 정반사 채널로 가는데 그 채널은 이 기하에서 "
                      "사실상 비어 있다 — 즉 관측량은 표적 반사전력의 작은 부분집합이다. "
                      "이것은 보고서의 '절대값 유보' 를 **수치로** 만든 것이다.")
    return out


def sec_q2_polarization() -> dict:
    """Q2 보강 — 교차편파(VH) 결과를 요약해 붙인다(있으면)."""
    p = os.path.join(ROOT, "outputs", "report15_attack_polarization.json")
    if not os.path.exists(p):
        return dict(available=False,
                    note_ko="교차편파 실험 산출물이 없다 — 이 축은 미검증으로 남긴다.")
    D = json.load(open(p))
    out = dict(available=True, meta=D["meta"], by_airframe={})
    for key, A in D["airframes"].items():
        rows = {}
        for k, v in A["rows"].items():
            if k.endswith("xpol_ratio"):
                rows[k] = v
            elif not v.get("empty", False):
                rows[k] = {kk: v[kk] for kk in
                           ("level_db", "modulation_ptp_db", "ac_over_noise_db",
                            "peak_bin", "edge_bin") if kk in v}
        out["by_airframe"][key] = rows
    xr = [v for A in out["by_airframe"].values() for k, v in A.items()
          if k.endswith("xpol_ratio")]
    #  ⚠ 교차편파는 사실상 0 이라 시드 분산이 0 이 되는 칸이 있다 → ac/n 이 None 이다.
    #     None 은 '문턱 미달' 로 읽는다(변조를 못 잰 것이지 센 것이 아니다).
    acn = [v.get("cross_ac_over_noise_db") for v in xr]
    lv = [v.get("cross_minus_co_level_db") for v in xr
          if v.get("cross_minus_co_level_db") is not None]
    out["cross_pol_detected_modulation"] = bool(
        xr and all((v if v is not None else -99.0) >= float(VD.TH["margin_db_min"])
                   for v in acn))
    out["n_cross_cells_noise_degenerate"] = int(sum(1 for v in acn if v is None))
    out["min_cross_ac_over_noise_db"] = (float(min(v for v in acn if v is not None))
                                         if any(v is not None for v in acn) else None)
    out["max_cross_ac_over_noise_db"] = (float(max(v for v in acn if v is not None))
                                         if any(v is not None for v in acn) else None)
    out["max_cross_minus_co_level_db"] = (float(max(lv)) if lv else None)
    out["note_ko"] = ("본 격자는 TX/RX 둘 다 V 단일편파였다. 회전 블레이드는 교차편파를 만드는 "
                      "산란체이므로 '가장 유리한 조건' 을 주장하려면 이 축도 봐야 한다.")
    return out


def sec_q3_arm_selection(J) -> dict:
    """⭐ Q3 의 진짜 급소 — PO 대조군은 **평면파 문제가 아니라 팔 선택 문제**다.
    우리 커널에는 가림 없는 PO 와 가림 있는 SBR 이 둘 다 있고, 둘이 서로 안 맞는다.
    판정이 인용한 '두 엔진 일치도' 가 어느 팔을 골랐는지를 수치로 드러낸다."""
    pc = os.path.join(ROOT, "outputs", "report15_po_control.json")
    if not os.path.exists(pc):
        return dict(available=False)
    D = json.load(open(pc))
    out = dict(available=True, range_m=float(D["meta"]["range_m"]), by_airframe={})
    for key, A in D["airframes"].items():
        X = A.get("arm_cross_matrix", {})
        rows = {}
        for stem, blk in X.items():
            pairs = blk.get("ac_corr_pairs", {})
            sio = {k: v for k, v in pairs.items() if "sionna" in k}
            po_sbr = {k: v for k, v in pairs.items()
                      if ("po_" in k and "sbr" in k)}
            po_po = {k: v for k, v in pairs.items()
                     if k.count("po_") == 2 and "sbr" not in k and "sionna" not in k}
            rows[stem] = dict(
                sionna_vs_arms=sio,
                sionna_vs_po_max=(max(v for k, v in sio.items() if "po_" in k)
                                  if any("po_" in k for k in sio) else None),
                sionna_vs_sbr_max=(max(v for k, v in sio.items() if "sbr" in k)
                                   if any("sbr" in k for k in sio) else None),
                po_vs_sbr_max=(max(po_sbr.values()) if po_sbr else None),
                po_internal_min=(min(po_po.values()) if po_po else None))
            r = rows[stem]
            r["reference_arm_disagreement_span"] = (
                None if (r["sionna_vs_po_max"] is None or r["sionna_vs_sbr_max"] is None)
                else float(r["sionna_vs_po_max"] - r["sionna_vs_sbr_max"]))
        out["by_airframe"][key] = rows
    #  판정 JSON 이 이 사실을 안고 갔는가
    vpath = os.path.join(ROOT, "outputs", "report15_verdict.json")
    if os.path.exists(vpath):
        s = json.dumps(json.load(open(vpath)), ensure_ascii=False)
        out["verdict_json_mentions"] = {w: int(s.count(w))
                                        for w in ("sbr", "SBR", "가림", "occl")}
    out["note_ko"] = ("PO 격자 팔은 구면파였다(평면파 아님) — 그쪽 우려는 기각된다. 대신 남는 것은 "
                      "**가림**이다. 우리 두 팔(PO 가림없음 / SBR 가림있음)이 서로 크게 어긋나고, "
                      "판정이 인용한 일치도는 그중 가림 없는 팔과의 값이다.")
    return out


def sec_q5_targets(J) -> dict:
    """Q5 — 이 결과가 실제로 건드리는 문장을 **파일에서 그대로** 뽑는다(손타이핑 금지)."""
    import subprocess
    targets = {
        "sionna_rt_reference_rotor": ("docs/SIONNA_RT_REFERENCE.md", r"회전 프로펠러"),
        "mesh_validation_doppler": ("docs/MESH_VALIDATION.md", r"Paths\.doppler"),
        "deck_facts_diffraction_default": ("docs/DECK_FACTS.md", r"diffraction=False"),
        "deck_facts_why_not_turn_on": ("docs/DECK_FACTS.md", r"왜 그냥 켜지 않는가"),
        "retraction_R6": ("docs/RETRACTION_LOG.md", r"R6"),
    }
    out = {}
    for nm, (path, pat) in targets.items():
        try:
            r = subprocess.run(["grep", "-nE", pat, path], cwd=ROOT,
                               capture_output=True, text=True, timeout=60)
            lines = [l for l in r.stdout.splitlines() if l.strip()]
        except Exception as e:
            lines = [f"grep 실패: {e}"]
        out[nm] = dict(file=path, pattern=pat, n=len(lines), lines=lines[:8])
    #  report15 산출물 자신의 문장
    vpath = os.path.join(ROOT, "outputs", "report15_verdict.json")
    if os.path.exists(vpath):
        V = json.load(open(vpath))
        out["report15_verdict_statements"] = dict(
            path_count_verdict_ko=V["path_count_census"]["verdict_ko"],
            caveat_specular=[c for c in V["conclusion"]["caveats_ko"] if "정반사" in c],
            caveat_max_depth=[c for c in V["conclusion"]["caveats_ko"] if "max_depth" in c],
            conclusion_contains_glint_claim=bool("글린트" in V["conclusion"]["text_ko"]))
    return out


#  ⭐ 판정 문턱은 **결과를 보기 전에** 정한다(사전등록).
MAT = dict(
    waveform_corr_unchanged=0.90,     # 이 위면 '같은 파형'
    ptp_unchanged_db=3.0,             # 이 안이면 '같은 변조 깊이'
    edge_bin_tol=1,                   # ±1 조화면 '같은 빗 폭'
    spec_populated_frac=0.90,         # 위상의 이 비율 이상에 경로가 있으면 '연속'
    spec_empty_frac=0.50,             # 이 아래면 '사실상 비어 있음'
    comb_cos_unchanged=0.90)


def sec_verdict(J) -> dict:
    q1, q2 = J["q1_summary"], J["q2_summary"]
    det = [r["specular_det"] for r in q1["by_cell"].values()]
    dif = [r["diffuse"] for r in q1["by_cell"].values() if "diffuse" in r]

    #  ① 헤드라인(확산 채널 변조)이 회절을 켜도 살아남는가
    corrs = [d["waveform_ac_corr"] for d in dif if d.get("waveform_ac_corr") is not None]
    ptps = [abs(d["d_ptp_db"]) for d in dif if d.get("d_ptp_db") is not None]
    combs = [d["comb_cos_vs_base"] for d in dif if d.get("comb_cos_vs_base") is not None]
    headline_survives = bool(corrs and min(corrs) >= MAT["waveform_corr_unchanged"]
                             and (not ptps or max(ptps) <= MAT["ptp_unchanged_db"])
                             and (not combs or min(combs) >= MAT["comb_cos_unchanged"]))

    #  ①-b ⭐ **존재 주장**과 **정량 주장**을 가른다.
    #      사전등록 문턱(waveform_corr·ptp)은 "파형이 그대로인가" 를 재는 것이지
    #      "변조가 있는가" 를 재는 것이 아니다. 회절을 켜서 변조가 **더 세지는** 것은
    #      존재 주장을 깨지 않는다 — 정량 주장만 깬다. 둘을 따로 판정한다.
    acn = [r["ac_over_noise_db"] for k, r in q2["vs_base"].items()
           if r["config"].startswith("prod") and r.get("ac_over_noise_db") is not None]
    existence_survives = bool(acn and min(acn) >= float(VD.TH["margin_db_min"]))
    #  판정기준 (b): 관측 가장자리 / f_tip 이 1±tol 안인가 — 회절 ON/OFF 로 뒤집히는 칸 세기
    tol = float(VD.TH["ftip_tol"])
    b_flips = []
    for k, r in q2["vs_base"].items():
        if r["config"] != "prod_diffr":
            continue
        a, b = r.get("edge_over_ftip"), r.get("edge_over_ftip_base")
        if a is None or b is None:
            continue
        pa, pb = abs(a - 1.0) <= tol, abs(b - 1.0) <= tol
        if pa != pb:
            b_flips.append(dict(cell=k, base_ratio=b, diffraction_ratio=a,
                                base_passes=pb, diffraction_passes=pa))

    #  ② 결정론(정반사) 채널의 '비어 있다' 서술이 회절로 바뀌는가
    flips = [d for d in det
             if d["prop_phase_frac_off"] < MAT["spec_empty_frac"]
             and d["prop_phase_frac_on"] >= MAT["spec_populated_frac"]]
    turns_on = [d for d in det if d["turns_on_where_it_was_empty"]]
    spec_claim_changes = bool(flips)

    #  ③ 더 유리한 설정이 판정 재료를 바꾸는가
    def worst(cfg, field):
        vals = [r[field] for k, r in q2["vs_base"].items()
                if r["config"] == cfg and r.get(field) is not None]
        return (float(min(vals)) if vals else None)

    def widest(cfg, field):
        vals = [abs(r[field]) for k, r in q2["vs_base"].items()
                if r["config"] == cfg and r.get(field) is not None]
        return (float(max(vals)) if vals else None)

    fav = {}
    for cfg in ("prod_sppmax", "prod_d3", "prod_refr", "prod_diffr"):
        fav[cfg] = dict(min_waveform_corr=worst(cfg, "waveform_ac_corr"),
                        max_abs_d_ptp_db=widest(cfg, "d_ptp_db"),
                        max_abs_d_level_db=widest(cfg, "d_level_db"),
                        max_abs_d_ac_over_noise_db=widest(cfg, "d_ac_over_noise_db"))
    favourability_changes = {
        c: bool((v["min_waveform_corr"] is not None
                 and v["min_waveform_corr"] < MAT["waveform_corr_unchanged"])
                or (v["max_abs_d_ptp_db"] is not None
                    and v["max_abs_d_ptp_db"] > MAT["ptp_unchanged_db"]))
        for c, v in fav.items()}

    #  ④ 에일리어싱
    al = J.get("q4_alias_measured", {})
    alias_ok = bool(al) and all(
        (a["prop"]["comb_cos_64_vs_128"] >= MAT["comb_cos_unchanged"]) for a in al.values())

    #  ⑤ 판정 당시 **안 건드린 축** 목록 (자체로 판정을 뒤집지는 않지만 범위를 좁힌다)
    C = J["q1_flag_census"]
    pol = J.get("q2_polarization", {})
    untested = []
    if C["report15_diffraction_never_enabled"]:
        untested.append("diffraction")
    if C["report15_edge_diffraction_never_enabled"]:
        untested.append("edge_diffraction")
    if C["report15_max_depth_values"] and all(
            v in ("1", "int(max_depth)") for v in C["report15_max_depth_values"]):
        untested.append("max_depth>1 (격자 본체)")
    if J["q2_summary"]["spp_headroom_factor"] > 1.0:
        untested.append("samples_per_src 상한(2배 여유)")
    if pol.get("available"):
        untested.append("교차편파(이번에 우리가 채움)")
    else:
        untested.append("교차편파(여전히 미검증)")
    untested.append("R < 1 m (이번에 우리가 채움)")

    quantitative_claims_change = bool(
        (not headline_survives) or spec_claim_changes or b_flips
        or any(favourability_changes.values()) or (not alias_ok))
    dres = J.get("q4_diffraction_resolution", {})
    verdict = ("BROKEN" if not existence_survives
               else ("PREMATURE" if quantitative_claims_change else "SOUND"))
    return dict(
        thresholds_preregistered=MAT,
        rule_ko=("사전등록 문턱은 '파형이 그대로인가' 를 잰다. 그것이 깨졌다고 '변조가 없다' 가 "
                 "되지는 않으므로, BROKEN 은 **존재 주장**(a 여유 ≥ 문턱)이 무너질 때만 쓴다. "
                 "존재는 살아 있는데 정량 서술(정반사 공백·(b) 가장자리·변조 깊이·에일리어싱)이 "
                 "바뀌면 PREMATURE 다."),
        existence_claim_survives=existence_survives,
        existence_min_ac_over_noise_db=(float(min(acn)) if acn else None),
        existence_threshold_db=float(VD.TH["margin_db_min"]),
        criterion_b_flips_with_diffraction=b_flips,
        n_criterion_b_flips=len(b_flips),
        headline_diffuse_modulation_survives_diffraction=headline_survives,
        headline_min_waveform_corr=(float(min(corrs)) if corrs else None),
        headline_max_abs_d_ptp_db=(float(max(ptps)) if ptps else None),
        headline_min_comb_cos=(float(min(combs)) if combs else None),
        specular_claim_changes_with_diffraction=spec_claim_changes,
        n_cells_specular_becomes_continuous=len(flips),
        n_cells_specular_turns_on_at_all=len(turns_on),
        favourability=fav, favourability_changes=favourability_changes,
        alias_free=alias_ok,
        diffraction_channel_resolved_at_64=dres.get("diffraction_channel_resolved_at_64"),
        diffraction_channel_resolved_at_128=dres.get("diffraction_channel_resolved_at_128"),
        alias_comb_cos_64_vs_128={k: v["prop"]["comb_cos_64_vs_128"] for k, v in al.items()},
        diffraction_never_enabled_in_report15=J["q1_flag_census"][
            "report15_diffraction_never_enabled"],
        untested_axes_at_verdict_time=untested,
        cross_pol_modulation_detected=pol.get("cross_pol_detected_modulation"),
        cross_pol_min_ac_over_noise_db=pol.get("min_cross_ac_over_noise_db"),
        verdict=verdict)


def sec_repair(J) -> dict:
    """mini2 격자 복구본이 중간저장 백업과 **원소 단위로** 같은가."""
    a = os.path.join(ROOT, "outputs", "report15_verdict_grid_mini2.json")
    b = a + ".prerepair"
    if not (os.path.exists(a) and os.path.exists(b)):
        return dict(available=False)
    A = json.load(open(a))["grid"]; B = json.load(open(b))["grid"]
    ka, kb = set(A["blocks"]), set(B["blocks"])
    diff = 0; tot = 0; shape_bad = 0
    for k in sorted(ka & kb):
        for f in ("hr", "hi", "hpr", "hpi", "n", "n_prop"):
            X = np.asarray(A["blocks"][k][f], float)
            Y = np.asarray(B["blocks"][k][f], float)
            tot += X.size
            if X.shape == Y.shape:
                diff += int(np.sum(X != Y))
            else:
                shape_bad += 1
    return dict(available=True, n_blocks_common=len(ka & kb),
                blocks_identical_sets=bool(ka == kb),
                n_elements_compared=int(tot), n_elements_differing=int(diff),
                n_shape_mismatch=int(shape_bad),
                repair_was_metadata_only=bool(diff == 0 and shape_bad == 0 and ka == kb),
                keys_added=sorted(set(A.keys()) - set(B.keys())),
                note_ko="복구가 추적 자료를 건드리지 않았는지 백업과 직접 대조한 결과다.")


# --------------------------------------------------------------------------- #
def main():
    J = json.load(open(OUT_JSON))
    #  ① 플래그 감사 재계산 (공격 스크립트 자신 제외)
    J["q1_flag_census"] = _census_from_calls(J)
    #  ② 수렴하는 관측량
    J["q2_incoherent"] = sec_incoherent(J)
    #  ③ 요약
    J["q1_summary"] = sec_q1_summary(J)
    J["q2_summary"] = sec_q2_summary(J)
    J["q4_extra"] = sec_q4_extra(J)
    J["q1_diffuse_completeness"] = sec_q1_diffuse_completeness()
    J["q4_diffraction_resolution"] = sec_q4_diffraction_resolution()
    J["q2_polarization"] = sec_q2_polarization()
    J["q3_arm_selection"] = sec_q3_arm_selection(J)
    J["q5_targets"] = sec_q5_targets(J)
    J["repair_integrity"] = sec_repair(J)
    J["verdict"] = sec_verdict(J)
    with open(OUT_JSON, "w") as f:
        json.dump(_f(J), f, ensure_ascii=False)
    print("✅ 후처리 완료 →", OUT_JSON)
    print(json.dumps(_f(dict(
        q1_n_cells_specular_turns_on=J["q1_summary"]["n_cells_specular_turns_on"],
        q1_diffuse_min_corr=J["q1_summary"]["diffuse_min_waveform_corr"],
        q1_diffuse_max_abs_dptp=J["q1_summary"]["diffuse_max_abs_d_ptp_db"],
        repair_ok=J["repair_integrity"].get("repair_was_metadata_only"))),
        ensure_ascii=False))


if __name__ == "__main__":
    main()
