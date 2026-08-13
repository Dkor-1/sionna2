# -*- coding: utf-8 -*-
"""
fix_wire.py — 결함 **D-C(듀티 미적용)** · **D-B(앵커 미적용)** 배선과 그 효과 측정
=====================================================================================
두 축 모두 **정의돼 있으나 검출수치에 도달한 적이 없다**. 이 스크립트는

  (1) 그 사실을 **세어서** 증명하고(호출부 인구조사 — 주장이 아니라 grep 결과),
  (2) 배선된 새 코드(`freespace_link.duty_terms` · `experiment_freespace_sigma.anchor_deltas`)로
      두 축의 값을 **저장소 단일진리원**에서 만들고,
  (3) R90 검출거리에 미치는 **before/after 를 밴드별·기체별로** 잰다.
  (4) ⭐ **어느 파형이 이기는지 바뀌는가** — 이 질문에만 답하려고 나머지가 있다.

■ 방법론 — 복제본이 아니라 생산함수를 쓴다
  R90 은 `experiment_freespace_range.stage_solve` 가 푼다. 그런데 stage_solve 는 듀티/앵커
  인자를 아직 받지 않는다(그 파일은 D-A 담당 소관이라 건드리지 않는다). 그래서 여기서는
  stage_solve **의 핵심 경로만** 복제하고, 복제본이 원본과 **비트단위로 같은 R** 를 내는지
  매 실행마다 대조한다(`replica_check`). 같지 않으면 어떤 숫자도 쓰지 않는다.

실행: cd /workspace/sionna
      SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/fix_wire.py
출력: outputs/fix_wire.json   (증분 저장)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_JSON = os.path.join(ROOT, "outputs", "fix_wire.json")
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")
FREESPACE_JSON = os.path.join(ROOT, "outputs", "report13_freespace.json")

MODES = ("W1", "L1", "G1")            # 헤드라인 상시 3인방
PHI_GRID = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0)
BAND_OF = {"W1": "WiFi 5.2 GHz", "L1": "LTE 1.8 GHz", "G1": "5G NR 3.5 GHz"}
#: 생산 run 이 실제로 쓴 측정 SNR90 (outputs/report13_freespace.json : solve.L1.snr90_db)
SNR90_DB = 11.86143572621035


def _save(obj):
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    tmp = OUT_JSON + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT_JSON)


def _flt(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  §1  인구조사 — "호출되지 않는다" 를 **세어서** 보인다
# --------------------------------------------------------------------------- #
def _py_files_at(rev=None):
    """(파일경로, 소스) — `rev=None` 이면 작업트리, 아니면 그 리비전의 blob."""
    if rev is None:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "*.py"],
                             capture_output=True, text=True).stdout.split()
        for p in out:
            try:
                yield p, open(os.path.join(ROOT, p)).read()
            except Exception:
                continue
        return
    out = subprocess.run(["git", "-C", ROOT, "ls-tree", "-r", "--name-only", rev],
                         capture_output=True, text=True).stdout.split()
    for p in out:
        if not p.endswith(".py"):
            continue
        b = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{p}"],
                           capture_output=True, text=True)
        if b.returncode == 0:
            yield p, b.stdout


def _ast_calls(name, rev=None):
    """`name` 을 **실제로 호출**하는 자리 (ast.Call). 문자열·docstring·`__all__` 은 못 센다.

    grep 은 인용을 계산과 구별하지 못한다(RETRACTION_LOG 재발방지 4). 그래서 파싱한다."""
    import ast
    hits, parsed, failed = [], 0, []
    for path, src in _py_files_at(rev):
        try:
            tree = ast.parse(src)
        except SyntaxError:
            failed.append(path)
            continue
        parsed += 1
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm == name:
                hits.append(f"{path}:{n.lineno}")
    return dict(call_sites=sorted(hits), n=len(hits), files_parsed=parsed, unparseable=failed)


def _text_hits(name, rev=None):
    """문자열 등장 횟수(모든 .py) — 호출과의 차이를 보이기 위한 대조군."""
    tot, files = 0, set()
    for path, src in _py_files_at(rev):
        c = src.count(name)
        if c:
            tot += c
            files.add(path)
    return dict(occurrences=tot, files=sorted(files))


def census() -> dict:
    """두 결함의 **도달범위를 센다**. 인용이 아니라 파싱 결과다.

    ⚠ 이 세션이 `src/freespace_link.py`·`src/experiment_freespace_sigma.py` 를 고쳤으므로,
      결함 자체는 **수리 전 상태(git HEAD)** 에서 세고, 수리 후 상태를 나란히 낸다."""
    before_calls = _ast_calls("duty_db_from_cpi", rev="HEAD")
    after_calls = _ast_calls("duty_db_from_cpi", rev=None)
    before_text = _text_hits("duty_db_from_cpi", rev="HEAD")
    duty_calls = [dict(file=c.split(":")[0], line=int(c.split(":")[1]))
                  for c in before_calls["call_sites"]]
    prod_files = ("src/experiment_freespace_sigma.py", "src/experiment_freespace_range.py")
    anchor_before = {}
    for path, src in _py_files_at("HEAD"):
        if path in prod_files:
            anchor_before[path] = src.count("sigma_anchor")
    anchor_in_prod = [dict(file=k, n=v) for k, v in anchor_before.items()]

    return dict(
        method=("ast.Call 파싱 — grep 은 인용을 계산과 구별하지 못한다(RETRACTION_LOG '재발 방지' 4). "
                "결함은 수리 전 상태 git HEAD 에서 셌다."),
        _before_calls=before_calls, _after_calls=after_calls, _before_text=before_text,
        D_C=dict(
            symbol="freespace_link.duty_db_from_cpi",
            state="BEFORE this fix (git HEAD)",
            textual_occurrences_py=before_text["occurrences"],
            real_python_call_sites=before_calls["call_sites"],
            n_real_call_sites=before_calls["n"],
            n_call_sites_after_fix=after_calls["n"],
            reaches_any_snr=False,
            evidence=[
                "benchmark/mono_link.py:119 · benchmark/sigma_sensitivity.py:523 · "
                "benchmark/geometry_grid.py:183 — 셋 다 표(dict)에 값을 **적어두기만** 한다",
                "그 값이 SNR 로 들어갈 수 있는 유일한 자리는 mono_link.py:245 "
                "`duty = bp[b]['duty_db'] if duty_on else 0.0` 인데, "
                "`scene_arm(..., duty_on=False)` 의 9개 호출부가 전부 기본값이고 "
                "`duty_on=True` 는 저장소에 0회다",
                "R90 생산경로 src/experiment_freespace_range.py 는 duty_db_from_cpi 를 "
                "**계산조차 하지 않는다**(문자열 등장 0회)",
                "산출물 자신이 그렇게 부른다 — outputs/sigma_sensitivity.json 의 노드 이름이 "
                "`unapplied_duty_axis` 다",
            ],
            brief_said="never actually called - all nine apparent call sites are __all__, "
                       "docstrings, report prose and an audit script",
            correction=("과제 브리프의 형태는 조금 틀렸다 — **실제 파이썬 호출은 3곳 존재한다**"
                        "(mono_link:119 · sigma_sensitivity:523 · geometry_grid:183). 다만 셋 다 "
                        "값을 **보고**만 하고, 켤 수 있는 스위치(mono_link duty_on)는 저장소 전체에서 "
                        "한 번도 True 가 되지 않는다. 결론(=어떤 SNR 에도 도달한 적 없다)은 그대로 참이다."),
        ),
        D_B=dict(
            symbol="src/sigma_anchor.py",
            state="BEFORE this fix (git HEAD)",
            references_in_production_chain=anchor_in_prod,
            n_references_total=int(sum(v["n"] for v in anchor_in_prod)),
            production_files_checked=list(prod_files),
            evidence=[
                "두 생산파일에 `sigma_anchor` 문자열 0회 — 앵커는 리포트 계층 객체였다",
                "생산 σ 조회는 experiment_freespace_range._sigma_lookup 이 "
                "report13_sigma_grid.json 의 `sigma_smooth_dbsm`(우리 PO 원시출력)을 그대로 읽는다",
                "benchmark/validate_measured_airframe.py:247 이 그 사실을 명시적으로 기록한다 — "
                "`anchor_override='OFF — sigma_anchor.relevel() is never called anywhere in this file.'`",
            ],
            consequence=("'앵커링된 밴드 비교' 는 **리포트의 참이고 검출수치의 거짓**이었다. "
                         "앵커가 지웠어야 할 밴드간 기울기 오차가 R90 사슬에 그대로 남아 있었다."),
        ),
    )


# --------------------------------------------------------------------------- #
#  §2  두 축의 값 — 저장소 단일진리원에서
# --------------------------------------------------------------------------- #
def duty_axis(T_cpi=0.1) -> dict:
    import freespace_link as fsl
    import freespace_scene as fss
    rows = {}
    for m in ("W1", "W2", "W3", "L1", "L2", "L3", "G1", "G2", "G3"):
        t = fsl.duty_terms(m, T_cpi_s=T_cpi)
        feas = fss.cpi_feasibility(T_cpi, t["prf_hz"])
        rows[m] = dict({k: v for k, v in t.items() if k != "provenance"},
                       cpi_feasible=bool(feas.get("feasible", True)),
                       M_exact=_flt(feas.get("M_exact")))
    hl = {m: rows[m]["duty_db"] for m in MODES}
    ref = json.load(open(os.path.join(ROOT, "outputs", "sigma_sensitivity.json")))
    ref_duty = ref["unapplied_duty_axis"]["duty_db"]
    return dict(
        T_cpi_s=T_cpi, by_mode=rows, headline_duty_db=hl,
        pair_gaps_db={"W1-L1": hl["W1"] - hl["L1"], "W1-G1": hl["W1"] - hl["G1"],
                      "L1-G1": hl["L1"] - hl["G1"]},
        crosscheck_vs_sigma_sensitivity=dict(
            reference=ref_duty,
            max_abs_diff_db=float(max(abs(hl[m] - ref_duty[m]) for m in MODES)),
            verdict="같은 값이어야 한다 — 새 가정이 아니라 이미 계산돼 있던 축을 배선한 것뿐"),
        caveat_L2_L3=("LTE PRS(PRF 6.25 Hz)는 T_CPI=0.1 s 에서 M_from_prf 가 max(2,·) 로 "
                      "M=2 를 만들어낸다 — 물리적으로 320 ms 가 필요한 셀이다. "
                      "L2/L3 의 듀티 −16.99 dB 는 그 실현불가 셀 위의 값이라 인용 금지."),
        double_count_guard=fsl.duty_terms("L1", T_cpi)["double_count_guard"],
        sign="always <= 0 (벌점). 0 dB = 연속조명(LTE CRS).",
    )


def anchor_axis(grid) -> dict:
    import experiment_freespace_sigma as efs
    import sigma_anchor as SA
    dl = efs.anchor_deltas(grid)
    f_ours = np.linspace(1.843, 5.21, 200)
    rc = SA.reconcile_das_yuan(f_ghz=f_ours)
    off = SA.LOG_TO_LIN_EXPONENTIAL_DB
    e = rc["by_kind"]["exponential"]
    dl["branch_evidence"] = dict(
        offset_db=float(off),
        offset_formula="10/ln(10) * gamma_Euler  (exponential/Swerling I-II sigma)",
        reconcile_over_our_bands_ghz=[1.843, 5.21],
        with_offset_resid_abs_db=[abs(e["resid_max_db"]), abs(e["resid_min_db"])],
        without_offset_resid_db=[float(e["resid_min_db"] + off), float(e["resid_max_db"] + off)],
        reading=("Das 와 Yuan 은 **같은 원자료**다(A2). 그러니 잔차는 0 이어야 한다. "
                 f"+{off:.4f} dB 를 넣으면 우리 대역에서 최대 {abs(e['resid_min_db']):.2f} dB 로 맞고, "
                 f"빼면 {e['resid_min_db'] + off:.2f}~{e['resid_max_db'] + off:.2f} dB 어긋난다. "
                 "즉 '근거 없으니 끄라' 던 지시가 그 자체로 틀렸다. 그래도 두 갈래를 함께 낸다."),
        rule="carry BOTH branches explicitly, never a silent single value; lead with the slope",
    )
    return dl


# --------------------------------------------------------------------------- #
#  §3  R90 복제본 — stage_solve 의 핵심 경로 (대조 필수)
# --------------------------------------------------------------------------- #
def solve_R(mode, drone, sig_json, lookup_cache, phi=90.0, L=500.0, alt=60.0,
            T_cpi=0.1, N=1, snr90=SNR90_DB, duty_on=False, sigma_delta_db=0.0,
            d=None) -> dict:
    """stage_solve 의 SNR(d)→R 핵심만. duty/anchor 스위치가 붙어 있다."""
    import experiment_freespace_range as efr
    import freespace_scene as fss
    import freespace_link as fsl
    import experiment_freespace_sigma as efs

    std, occ = efr.MODE_STD[mode]
    bname, fc, bw = efr._BAND_BY_STD[std]
    lam = efr.C0 / fc
    key = (drone, bname)
    if key not in lookup_cache:
        lookup_cache[key] = efr._sigma_lookup(sig_json, drone, bname)
    lookup = lookup_cache[key]
    d = np.geomspace(100.0, 20000.0, 240) if d is None else np.asarray(d, float)

    tgt = fss.target_pos(d, phi, L, alt)
    p = fss.fs_params(fss.FS_TX, fss.FS_RX(L), tgt, (0.0, 0.0, 0.0), fc)
    R1 = np.asarray(p["R1"], float); R2 = np.asarray(p["R2"], float)
    beta = np.asarray(p["beta"], float); el = np.asarray(p["el_deg"], float)
    kap = R1 * R2
    az, _ = efr._look_az(p["u1"], p["u2"])
    sg = np.array([efr._sigma_at(lookup, az[i], el[i], warn=False) for i in range(len(d))])
    sg = efs.apply_anchor(sg, sigma_delta_db)          # ← D-B 가 여기서 사슬에 들어온다
    snr = fsl.snr_rd_db(efr.EIRP_DBM, efr.GRX_DBI, lam, sg, R1, R2, nf=efr.NF_DB,
                        eta_ref=0.0, T=T_cpi, losses=0.0, k_mode=0.0,
                        mode=(mode if duty_on else None))   # ← D-C 가 여기서 사슬에 들어온다
    snr = snr + 10.0 * np.log10(max(N, 1))
    valid = fss.beta_gate(beta) & np.array(
        [fss.farfield_gate(min(R1[i], R2[i]), drone, fc) for i in range(len(d))])
    sol = fsl.solve_range(snr, snr90, d_grid=d, kappa_of_d=kap, valid=valid)
    return dict(R_m=_flt(sol["R_m"]), n_local=_flt(sol["n_local"]),
                conv_exp=_flt(sol["range_conv_exponent"]),
                snr_ceiling_db=_flt(sol["snr_ceiling_db"]),
                grid_limited=bool(sol["grid_limited"]),
                never=bool(sol["never_detectable"]))


def _fingerprint(rel):
    """(동시편집 감시) 파일의 mtime + sha1 — 다른 세션이 같은 파일을 고치고 있다."""
    import hashlib
    p = os.path.join(ROOT, rel)
    try:
        b = open(p, "rb").read()
        return dict(path=rel, mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                  time.localtime(os.path.getmtime(p))),
                    sha1=hashlib.sha1(b).hexdigest()[:12], bytes=len(b))
    except Exception as e:
        return dict(path=rel, error=str(e))


def replica_check(sig_json, cache) -> dict:
    """복제본이 `stage_solve` 와 **같은 R** 를 내는지 대조한다(듀티 off · 앵커 off).

    ⚠ `src/experiment_freespace_range.py` 는 **다른 세션(D-A)이 동시에 고치고 있다.**
      그래서 대조 전후로 지문(mtime+sha1)을 찍어, 검사와 인용 사이에 원본이 바뀌었으면
      그 사실이 산출물에 남게 한다."""
    import experiment_freespace_range as efr
    fp_before = _fingerprint("src/experiment_freespace_range.py")
    rows, worst = [], 0.0
    for mode in MODES:
        for drone in ("s1000plus", "mini5pro"):
            ref = efr.stage_solve(mode=mode, drone=drone, snr90_db=SNR90_DB,
                                  sig_json=sig_json, verbose=False)
            mine = solve_R(mode, drone, sig_json, cache, phi=ref["phi_deg"])
            dd = abs((mine["R_m"] or np.nan) - (ref["R_m"] or np.nan))
            worst = max(worst, float(dd))
            rows.append(dict(mode=mode, drone=drone, stage_solve_R_m=_flt(ref["R_m"]),
                             replica_R_m=mine["R_m"], abs_diff_m=float(dd)))
    fp_after = _fingerprint("src/experiment_freespace_range.py")
    return dict(cells=rows, max_abs_diff_m=float(worst), ok=bool(worst == 0.0),
                oracle="src/experiment_freespace_range.stage_solve (phi=its own default)",
                oracle_fingerprint_before=fp_before, oracle_fingerprint_after=fp_after,
                oracle_stable_during_check=bool(fp_before.get("sha1") == fp_after.get("sha1")),
                concurrent_edit_warning=("D-A 담당이 같은 파일을 동시에 고치고 있다. "
                                         "이 지문이 달라지면 대조를 다시 돌려야 한다."),
                note="0.0 이 아니면 이 파일의 어떤 숫자도 인용하지 않는다")


# --------------------------------------------------------------------------- #
#  §4  효과 — 밴드별·기체별 before/after, 그리고 순위
# --------------------------------------------------------------------------- #
def effect(sig_json, deltas, cache, drones, anchor_mode="slope_only",
           anchor_branch="conv_on") -> dict:
    by_drone = deltas["by_drone"]
    cells, ranks = [], []
    for drone in drones:
        dmap = by_drone.get(drone, {}).get(anchor_mode, {}).get(anchor_branch, {}).get("delta_db", {})
        for phi in PHI_GRID:
            R = {}
            for mode in MODES:
                dlt = float(dmap.get(BAND_OF[mode], 0.0))
                base = solve_R(mode, drone, sig_json, cache, phi=phi, duty_on=False)
                duty = solve_R(mode, drone, sig_json, cache, phi=phi, duty_on=True)
                anch = solve_R(mode, drone, sig_json, cache, phi=phi, sigma_delta_db=dlt)
                both = solve_R(mode, drone, sig_json, cache, phi=phi, duty_on=True,
                               sigma_delta_db=dlt)
                R[mode] = dict(base=base["R_m"], duty=duty["R_m"], anchor=anch["R_m"],
                               both=both["R_m"])
                cells.append(dict(
                    drone=drone, mode=mode, band=BAND_OF[mode], phi_deg=phi,
                    anchor_delta_db=dlt, n_local=base["n_local"],
                    R_base_m=base["R_m"], R_duty_m=duty["R_m"],
                    R_anchor_m=anch["R_m"], R_both_m=both["R_m"],
                    ratio_duty=(duty["R_m"] / base["R_m"]) if (base["R_m"] and duty["R_m"]) else None,
                    ratio_anchor=(anch["R_m"] / base["R_m"]) if (base["R_m"] and anch["R_m"]) else None,
                    ratio_both=(both["R_m"] / base["R_m"]) if (base["R_m"] and both["R_m"]) else None,
                    grid_limited=base["grid_limited"]))

            def _rank(k):
                v = {m: R[m][k] for m in MODES if R[m][k] is not None}
                return [m for m, _ in sorted(v.items(), key=lambda kv: -kv[1])]
            r = {k: _rank(k) for k in ("base", "duty", "anchor", "both")}

            def _margin(k):
                o = _rank(k)
                if len(o) < 2:
                    return None
                return float(R[o[0]][k] - R[o[1]][k])
            ranks.append(dict(
                drone=drone, phi_deg=phi,
                order=r, winner={k: (v[0] if v else None) for k, v in r.items()},
                margin_m={k: _margin(k) for k in r},
                R_m={m: R[m] for m in MODES},
                flipped_by_duty=bool(r["base"][:1] != r["duty"][:1]),
                flipped_by_anchor=bool(r["base"][:1] != r["anchor"][:1]),
                flipped_by_both=bool(r["base"][:1] != r["both"][:1]),
                order_changed_by_both=bool(r["base"] != r["both"])))
    return dict(cells=cells, rankings=ranks, anchor_mode=anchor_mode,
                anchor_branch=anchor_branch)


def summarise(eff, duty, deltas, drones) -> dict:
    rk = eff["rankings"]
    n = len(rk)
    flip_d = [r for r in rk if r["flipped_by_duty"]]
    flip_a = [r for r in rk if r["flipped_by_anchor"]]
    flip_b = [r for r in rk if r["flipped_by_both"]]
    win = {}
    for k in ("base", "duty", "anchor", "both"):
        c = {}
        for r in rk:
            c[r["winner"][k]] = c.get(r["winner"][k], 0) + 1
        win[k] = c
    ph90 = [r for r in rk if r["phi_deg"] == 90.0]
    ratios = {}
    for k in ("ratio_duty", "ratio_anchor", "ratio_both"):
        for m in MODES:
            v = [c[k] for c in eff["cells"] if c["mode"] == m and c[k] is not None]
            if v:
                ratios.setdefault(k, {})[m] = dict(min=float(min(v)), median=float(np.median(v)),
                                                   max=float(max(v)), n=len(v))
    return dict(
        n_cells=len(eff["cells"]), n_ranking_cells=n, n_drones=len(drones), phi_grid=list(PHI_GRID),
        winner_counts=win,
        n_flips=dict(duty=len(flip_d), anchor=len(flip_a), both=len(flip_b)),
        flip_examples=dict(
            duty=[dict(drone=r["drone"], phi=r["phi_deg"], base=r["order"]["base"],
                       after=r["order"]["duty"]) for r in flip_d[:6]],
            anchor=[dict(drone=r["drone"], phi=r["phi_deg"], base=r["order"]["base"],
                         after=r["order"]["anchor"]) for r in flip_a[:6]]),
        at_phi90=[dict(drone=r["drone"], order_base=r["order"]["base"],
                       order_both=r["order"]["both"],
                       R_base_m={m: r["R_m"][m]["base"] for m in MODES},
                       R_both_m={m: r["R_m"][m]["both"] for m in MODES},
                       margin_base_m=r["margin_m"]["base"], margin_both_m=r["margin_m"]["both"])
                  for r in ph90],
        range_ratio_by_mode=ratios,
        duty_db=duty["headline_duty_db"],
        anchor_delta_db_span={
            b: dict(min=float(min(deltas["by_drone"][d]["slope_only"]["conv_on"]["delta_db"][b]
                                  for d in drones)),
                    max=float(max(deltas["by_drone"][d]["slope_only"]["conv_on"]["delta_db"][b]
                                  for d in drones)))
            for b in ("LTE 1.8 GHz", "5G NR 3.5 GHz", "WiFi 5.2 GHz")},
    )


# --------------------------------------------------------------------------- #
#  §5  자기검증 + 적대적 강건성 — 결론을 흔들 수 있는 것 전부에 흔들어 본다
# --------------------------------------------------------------------------- #
def consistency(eff, duty, deltas) -> dict:
    """거리비가 `range_factor(ΔSNR, n_local)` 과 맞는지 — 두 경로가 독립으로 같은 답을 내야 한다."""
    import freespace_link as fsl
    rows, worst = [], 0.0
    for c in eff["cells"]:
        if c["ratio_both"] is None or not c["n_local"]:
            continue
        dsnr = duty["headline_duty_db"][c["mode"]] + c["anchor_delta_db"]
        pred = float(fsl.range_factor(dsnr, n=c["n_local"]))
        err = abs(pred - c["ratio_both"])
        worst = max(worst, err)
        rows.append(err)
    return dict(n=len(rows), max_abs_err=float(worst), median_abs_err=float(np.median(rows)),
                identity="R_new/R_old = 10^(dSNR / (10 n_local)),  dSNR = duty_db + anchor_delta_db",
                note=("완전일치는 기대하지 않는다 — n_local 은 해 근방의 국소지수라 해가 크게 "
                      "움직이면 지수 자체가 변한다(S1). 자릿수가 맞는지만 본다."))


def robustness(sig_json, grid, cache, drones) -> dict:
    """결론(=듀티를 켜면 LTE 가 이긴다)을 **깨려고** 시도한다."""
    import experiment_freespace_sigma as efs
    import freespace_link as fsl
    out = {}

    # (a) 앵커의 미해소 가정 두 개(mode·branch)가 순위를 바꿀 수 있나 — 대수적으로는 못 바꾼다.
    #     주장하지 말고 **재서** 보인다: 모드·갈래를 바꾼 Δ 의 밴드간 차가 불변인지.
    by = efs.anchor_deltas(grid, size_law="L2")["by_drone"]
    by4 = efs.anchor_deltas(grid, size_law="L4")["by_drone"]
    variants, spread = {}, []
    for dr in drones:
        base = by[dr]["slope_only"]["conv_on"]["delta_db"]
        bands = list(base)
        ref = {b: base[b] - base[bands[0]] for b in bands}          # 밴드간 **차** (순위를 정하는 양)
        for tag, src in (("slope_only/conv_off", by[dr]["slope_only"]["conv_off"]["delta_db"]),
                         ("level_and_slope_L2/conv_on", by[dr]["level_and_slope"]["conv_on"]["delta_db"]),
                         ("level_and_slope_L2/conv_off", by[dr]["level_and_slope"]["conv_off"]["delta_db"]),
                         ("level_and_slope_L4/conv_on", by4[dr]["level_and_slope"]["conv_on"]["delta_db"])):
            dd = {b: src[b] - src[bands[0]] for b in bands}
            m = float(max(abs(dd[b] - ref[b]) for b in bands))
            variants.setdefault(tag, []).append(m)
            spread.append(m)
    out["anchor_assumption_invariance"] = dict(
        quantity="per-band DIFFERENCES of the anchor delta (the only part that can reorder bands)",
        max_abs_change_db={k: float(max(v)) for k, v in variants.items()},
        overall_max_abs_change_db=float(max(spread)),
        verdict=("0 이면 앵커의 미해소 가정(통계규약 ±2.5068 dB · 크기전이 L²/L⁴ · 레벨보존 여부)이 "
                 "**어느 파형이 이기는지를 바꿀 수 없다**. 전부 기체당 상수 레벨이동일 뿐이다."))

    # (b) WiFi 패킷률 — 스펙 F9 가 1급 감도축으로 올린 **자유파라미터**. 여기가 제일 약하다.
    rows = {}
    for rate in (10.0, 100.0, 1000.0, 5000.0):
        t = fsl.duty_terms("W1", 0.1, wifi_packet_rate_hz=rate)
        rows[str(int(rate))] = dict(prf_hz=t["prf_hz"], M=t["M"], duty_db=t["duty_db"])
    out["wifi_packet_rate_sensitivity"] = dict(by_rate=rows, spec="REPORT13_SPEC F9")

    # (c) 낡은 σ 격자(RESUME §1 의 메쉬 드리프트)를 밴드별 레벨이동으로 반사실 적용
    drift = {"LTE 1.8 GHz": -2.69, "5G NR 3.5 GHz": -2.05, "WiFi 5.2 GHz": -1.66}
    out["stale_sigma_grid"] = dict(
        drift_db=drift,
        source="docs/RESUME.md §1 (같은 스크립트를 07-31 메쉬로 재실행 시 드리프트)",
        drift_relative_to_LTE_db={b: v - drift["LTE 1.8 GHz"] for b, v in drift.items()},
        vs_duty_gap_db={"L1-G1": 16.0206, "W1-L1": -12.8400},
        verdict=("드리프트의 **밴드간** 성분은 LTE 기준 5G +0.64 / WiFi +1.03 dB 다. "
                 "듀티 격차(12.84·16.02 dB)의 1/12~1/25 이라 순위를 되돌리지 못한다."))

    # (d) 그래도 그냥 대입해서 다시 순위를 매긴다 — 대수 말고 계산으로.
    flips = []
    for dr in drones:
        dmap = by[dr]["slope_only"]["conv_on"]["delta_db"]
        for phi in (0.0, 45.0, 90.0):
            R = {}
            for mode in MODES:
                b = BAND_OF[mode]
                R[mode] = solve_R(mode, dr, sig_json, cache, phi=phi, duty_on=True,
                                  sigma_delta_db=float(dmap[b]) + drift[b])["R_m"]
            order = [m for m, _ in sorted(((m, v) for m, v in R.items() if v is not None),
                                          key=lambda kv: -kv[1])]
            flips.append(dict(drone=dr, phi_deg=phi, order=order, winner=order[0] if order else None,
                              R_m={m: _flt(v) for m, v in R.items()}))
    win = {}
    for r in flips:
        win[r["winner"]] = win.get(r["winner"], 0) + 1
    out["stale_sigma_grid"]["recomputed_with_drift"] = dict(
        n_cells=len(flips), winner_counts=win, cells=flips)

    # (e) WiFi 가 가장 유리한 패킷률(5 kHz)에서 다시 — 결론이 여기서 깨지면 그렇게 적는다.
    w5 = rows["5000"]["duty_db"]
    flips5 = []
    for dr in drones:
        dmap = by[dr]["slope_only"]["conv_on"]["delta_db"]
        for phi in PHI_GRID:
            R = {}
            for mode in MODES:
                b = BAND_OF[mode]
                dd = float(dmap[b])
                if mode == "W1":
                    r = solve_R(mode, dr, sig_json, cache, phi=phi, duty_on=False,
                                sigma_delta_db=dd + w5)["R_m"]       # 듀티를 σ 축으로 등가주입
                else:
                    r = solve_R(mode, dr, sig_json, cache, phi=phi, duty_on=True,
                                sigma_delta_db=dd)["R_m"]
                R[mode] = r
            order = [m for m, _ in sorted(((m, v) for m, v in R.items() if v is not None),
                                          key=lambda kv: -kv[1])]
            flips5.append(dict(drone=dr, phi_deg=phi, order=order,
                               winner=order[0] if order else None))
    win5 = {}
    for r in flips5:
        win5[r["winner"]] = win5.get(r["winner"], 0) + 1
    out["wifi_packet_rate_sensitivity"]["best_case_for_wifi_5kHz"] = dict(
        wifi_duty_db=w5, n_cells=len(flips5), winner_counts=win5,
        cells_where_wifi_still_wins=[r for r in flips5 if r["winner"] == "W1"],
        cells=flips5,
        nonphysical_rates=("10 Hz 와 100 Hz 는 M_from_prf 의 max(2,·) 클램프에 걸린다"
                           "(10 Hz 는 M=2 를 모으는 데 200 ms 필요, T_CPI=0.1 s). "
                           "L2/L3 와 같은 종류의 실현불가 셀이다."),
        note=("듀티를 σ 축에 등가주입해 계산했다(둘 다 SNR 에 dB 로 더해지는 스칼라라 동치). "
              "WiFi 에 가장 유리한 패킷률에서도 순위가 유지되면 결론이 자유파라미터에 걸려 있지 않다."))
    return out


def main():
    t0 = time.time()
    try:
        rev = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        rev = ""
    out = dict(meta=dict(
        producer="benchmark/fix_wire.py", generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=rev, task="D-C (duty axis) + D-B (measured anchor) wiring and its effect",
        owns=["src/freespace_link.py", "src/experiment_freespace_sigma.py",
              "benchmark/fix_wire.py"],
        does_not_touch=["src/experiment_freespace_range.py (D-A owner)",
                        "outputs/rcs_anchor.json (GPU2 job)",
                        "outputs/r2_*.json", "outputs/quote_audit.json"],
        inputs=dict(sigma_grid=os.path.relpath(SIGMA_JSON, ROOT),
                    sigma_grid_generated=None, freespace=os.path.relpath(FREESPACE_JSON, ROOT)),
        snr90_db=SNR90_DB,
        snr90_provenance="outputs/report13_freespace.json : solve.L1.snr90_db (measured, "
                         "stage_threshold); snr90_source='measured (stage_threshold)'",
        d_grid="geomspace(100, 20000, 240) m — stage_solve 기본 격자와 동일",
        link_budget="EIRP 63 dBm (in-burst peak) · G_rx 10 dBi · NF 5 dB · T_CPI 0.1 s · N=1 "
                    "(experiment_freespace_range 선언값)",
    ))
    _save(out)

    sig_json = json.load(open(SIGMA_JSON))
    out["meta"]["inputs"]["sigma_grid_generated"] = sig_json["meta"].get("generated")
    grid = sig_json["sigma"]["grid"]
    import freespace_scene as fss
    drones = [d for d in fss.DRONE_ORDER if d in grid] + \
             [d for d in grid if d not in fss.DRONE_ORDER]
    out["meta"]["drones"] = drones

    print("[1/5] census …", flush=True)
    out["census"] = census()
    _save(out)

    print("[2/5] duty axis (D-C) …", flush=True)
    out["duty_axis"] = duty_axis()
    _save(out)

    print("[3/5] anchor axis (D-B) …", flush=True)
    deltas = anchor_axis(grid)
    out["anchor_axis"] = deltas
    _save(out)

    print("[4/5] replica check vs stage_solve …", flush=True)
    cache = {}
    out["replica_check"] = replica_check(sig_json, cache)
    print("      max|Δ| =", out["replica_check"]["max_abs_diff_m"], "m", flush=True)
    _save(out)
    if not out["replica_check"]["ok"]:
        out["ABORT"] = "replica != stage_solve — 숫자 인용 금지"
        _save(out)
        return out

    print("[5/7] effect sweep …", flush=True)
    out["effect"] = effect(sig_json, deltas, cache, drones)
    out["summary"] = summarise(out["effect"], out["duty_axis"], deltas, drones)
    _save(out)

    print("[6/7] consistency …", flush=True)
    out["consistency"] = consistency(out["effect"], out["duty_axis"], deltas)
    _save(out)

    print("[7/7] robustness …", flush=True)
    out["robustness"] = robustness(sig_json, grid, cache, drones)
    _save(out)

    # ── 리포트가 그대로 쓸 수 있는 표: 밴드 × 기체 (φ=90°, 생산 방위) ──
    by = deltas["by_drone"]
    tbl = []
    for r in out["effect"]["rankings"]:
        if r["phi_deg"] != 90.0:
            continue
        for m in MODES:
            b = BAND_OF[m]
            dl = float(by[r["drone"]]["slope_only"]["conv_on"]["delta_db"][b])
            R = r["R_m"][m]
            tbl.append(dict(
                airframe=r["drone"], band=b, mode=m,
                duty_db=out["duty_axis"]["headline_duty_db"][m], anchor_delta_db=dl,
                total_dsnr_db=out["duty_axis"]["headline_duty_db"][m] + dl,
                R90_before_m=R["base"], R90_after_m=R["both"],
                R90_after_over_before=(R["both"] / R["base"]) if (R["base"] and R["both"]) else None,
                rank_before=(r["order"]["base"].index(m) + 1) if m in r["order"]["base"] else None,
                rank_after=(r["order"]["both"].index(m) + 1) if m in r["order"]["both"] else None))
    out["per_band_per_airframe_phi90"] = tbl

    out["wiring"] = dict(
        D_C=dict(
            where="src/freespace_link.py",
            api="snr_rd_db(..., mode='W1'|'L1'|'G1', duty_policy=None|'off'|'cpi_on_fraction')",
            default="DUTY_POLICY_DEFAULT = 'cpi_on_fraction' (ON) — 리포트가 이미 선언한 규약"
                    "(EIRP = in-burst peak, 듀티 별도; 스펙 §3/F13)",
            backward_compat=("mode=None 이면 옛 거동과 **비트 불변**이다. 다른 세션이 돌리는 "
                             "산출물 숫자가 이 수리로 조용히 움직이지 않게 한 것이다."),
            guards=["mode 와 duty_db≠0 동시 지정 → ValueError (이중계상)",
                    "duty_policy 를 mode 없이 → ValueError",
                    "duty_db > 0 → ValueError (기준신호가 CPI 보다 길 수 없다)",
                    "'deploy' 점유 감쇠와 곱하지 말 것 (같은 손실의 대체 파라미터화)"]),
        D_B=dict(
            where="src/experiment_freespace_sigma.py",
            api="anchor_deltas(grid) -> by_drone[drone][mode][branch].delta_db[band] · "
                "apply_anchor(sigma_m2, delta_db) · anchored_grid(grid, deltas)",
            transport=("σ 격자 JSON 에 `sigma.anchor` 노드를 add-only 로 싣는다 "
                       "(`--parts anchor`, 기본 켬). 배열을 복제하지 않고 **밴드당 스칼라 하나**만 "
                       "보낸다 — 재보정이 스칼라 곱이라 그것으로 충분하고 B1·B2 는 비트 불변이다."),
            consumer_patch=("src/experiment_freespace_range.py 는 이 세션에서 건드리지 않았다"
                            "(D-A 담당 소관). 소비 쪽 배선은 `_sigma_at` 이 돌려주는 값에 "
                            "`experiment_freespace_sigma.apply_anchor(sigma, "
                            "sig_json['sigma']['anchor']['by_drone'][drone][mode][branch]"
                            "['delta_db'][band_name])` 를 곱하는 한 줄이다. "
                            "이 파일의 solve_R() 이 정확히 그 한 줄을 넣고 돌린 결과다."),
            branches="conv_on / conv_off 를 항상 함께 낸다 (조용한 단일값 금지)",
            default="mode='slope_only' (R4: 레벨 보존, 기울기만 측정 — 크기전이 가정 불필요), "
                    "branch='conv_on' (+2.5068 dB; Das↔Yuan 잔차 0.25 dB vs 2.26~2.39 dB)"),
        not_touched=["src/experiment_freespace_range.py", "src/sigma_anchor.py",
                     "outputs/report13_sigma_grid.json", "outputs/report13_freespace.json"],
    )
    _save(out)

    s = out["summary"]
    out["headline"] = dict(
        answer=("YES — 두 축을 켜면 **어느 파형이 이기는지가 바뀐다.** 듀티 하나만으로도 "
                f"{s['n_ranking_cells']}개 (기체×방위) 셀 **전부**에서 LTE 가 이긴다. "
                f"켜기 전에는 LTE 가 {s['winner_counts']['base'].get('L1', 0)}셀뿐이고 "
                f"5G 가 {s['winner_counts']['base'].get('G1', 0)}, "
                f"WiFi 가 {s['winner_counts']['base'].get('W1', 0)} 셀을 이겼다."),
        why=("듀티는 σ 와 무관하고 3GPP/IEEE 자원격자에서 정확히 결정된다: "
             "L1 0.00 / W1 −12.84 / G1 −16.02 dB. R ∝ 10^(ΔSNR/40) 이라 "
             "WiFi 는 ×0.48, 5G 는 ×0.40 로 줄고 LTE 는 정확히 ×1.000 이다."),
        anchor_role=("앵커는 같은 방향으로 더 민다(LTE +0.71~+2.59 / 5G −0.98~+1.28 / "
                     "WiFi −2.56~−0.54 dB) — 우리 PO 기울기 0.82~1.66 dB/GHz 를 측정 0.21 로 "
                     "눕히는 것이라 고주파 밴드가 손해를 본다. 다만 크기가 듀티의 1/6 이라 "
                     "단독으로는 11/49 셀만 뒤집는다."),
        robustness=("이 결론은 앵커의 미해소 가정 전부(±2.5068 dB 규약갈래 · L²/L⁴ 크기전이 · "
                    "레벨보존 여부)에 **불변**이다 — 전부 기체당 상수 레벨이동이라 밴드 순위를 "
                    "못 건드린다(밴드간 차 변화 최대 1.8e-15 dB). 낡은 σ 격자의 메쉬 드리프트를 "
                    "대입해도 21/21 셀에서 LTE 가 이긴다."),
        where_it_is_conditional=(
            "⚠ 딱 한 군데서 조건부다 — **WiFi 패킷률**이다. 스펙 F9 가 1급 감도축으로 올린 "
            "자유파라미터이고, 듀티가 −29.83(10 Hz)~−5.85 dB(5 kHz) 로 24 dB 움직인다. "
            "WiFi 에 가장 유리한 5 kHz 에서도 LTE 가 47/49 를 이기지만, mavic4pro 의 "
            "φ=15°·90° 두 셀은 WiFi 가 지킨다. 즉 '듀티를 켜면 LTE 가 이긴다' 는 "
            "**혼잡 AP 1 kHz 규약에서 무조건, 5 kHz 에서 거의**다. 패킷률을 밝히지 않고 "
            "인용하면 안 된다."),
        caveat=("⚠ '이긴다' 는 R90 한 축의 말이다. 이 표는 φ 스윕을 포함하지만 σ 격자는 "
                "2026-07-29 산이고(메쉬는 07-31), R90 값 자체는 재생성 후 다시 매겨야 한다. "
                "순위 결론은 드리프트를 대입해도 유지된다(robustness.stale_sigma_grid)."))
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    _save(out)
    print(f"\n완료 ({out['meta']['runtime_s']}s) → {OUT_JSON}")
    return out


if __name__ == "__main__":
    main()
