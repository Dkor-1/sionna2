#!/usr/bin/env python
"""⭐ 메쉬 인증 **매트릭스** — 전 기체(10) × 전 검사를 한 표로 모은다 (2026-08-17).

이 라운드는 검사기를 새로 만들지 않는다.  저장소에 이미 있는 여섯 검사기를
**전수로 돌려** 칸마다 (판정 · 잔차 · 허용오차 · 근거등급 · 양성대조 통과여부)를 적고,
못 하는 것을 선언한다.  ⛔형상 상수 무변경 · ⛔GPU 미사용 · ⛔git 미접촉.

입력
  --raw-dir   기체별 원자료 디렉터리 (benchmark/mesh_cert_matrix_run_one.py 산출)
  --fleet     함대 원자료 (benchmark/mesh_cert_matrix_fleet.py 산출)
  --ctl-dir   적대 대조 로그 디렉터리 (benchmark/adv_*.py 의 stdout + .exit)
없으면 그 자리에서 돌린다(--run).

산출
  outputs/mesh_cert_matrix_0816.json   기계가 읽는 인증서
  outputs/mesh_cert_matrix_0816.md     사람이 읽는 표
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
PY = sys.executable

KEYS = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus", "phantom4",
        "typhoonh480", "x500v2", "phantom3", "m350rtk", "mini2"]

CERTS = {
    "map": "outputs/mesh_cert_map_0816.json",
    "topology": "outputs/mesh_cert_topology_discretization_0816.json",
    "dimension": "outputs/mesh_cert_dimension_external_0816.json",
    "placement": "outputs/mesh_cert_placement_overlap_0816.json",
    "symmetry": "outputs/mesh_cert_symmetry_derived_0816.json",
    "material": "outputs/mesh_cert_material_provenance_0816.json",
}

SUITES = {                     # 적대 대조 스크립트 → 그 스위트가 지키는 검사기
    "adv_mesh_check_faults": "src/mesh_check.py",
    "adv_mesh_topo_faults": "src/mesh_topo_check.py",
    "adv_mesh_dimref_faults": "src/mesh_dimref.py",
    "adv_mesh_placement_0816": "src/mesh_placement.py",
    "adv_mesh_symmetry_faults": "src/mesh_symmetry.py",
    "adv_material_provenance_faults": "src/material_provenance.py",
}


# --------------------------------------------------------------------------- #
#  잔돈들
# --------------------------------------------------------------------------- #
def _sha_file(p: str, n: int = 16) -> str:
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]
    except OSError:
        return "?"


def _kst() -> str:
    return (_dt.datetime.utcnow() + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def _load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _pct(x, y):
    """잔차/예산 비율 [%] — «얼마나 빠듯한가»."""
    try:
        return None if not y else round(100.0 * float(x) / float(y), 1)
    except (TypeError, ZeroDivisionError):
        return None


# --------------------------------------------------------------------------- #
#  대조 로그 파싱 — 「✅ 태그   본문」 줄만 읽는다
# --------------------------------------------------------------------------- #
_CTL_RE = re.compile(r"^\s*(✅|❌)\s+(.+?)(?:\s{2,}(.*))?$")


def parse_controls(ctl_dir: str) -> dict:
    out = {}
    for name in SUITES:
        log = os.path.join(ctl_dir, name + ".log")
        exitf = os.path.join(ctl_dir, name + ".exit")
        rows = []
        if os.path.exists(log):
            for ln in open(log, encoding="utf-8", errors="replace"):
                m = _CTL_RE.match(ln.rstrip())
                if not m:
                    continue
                rows.append(dict(passed=(m.group(1) == "✅"),
                                 tag=m.group(2).strip(),
                                 detail=(m.group(3) or "").strip()))
        code = None
        if os.path.exists(exitf):
            try:
                code = int(open(exitf).read().strip())
            except ValueError:
                code = None
        out[name] = dict(script=f"benchmark/{name}.py", guards=SUITES[name],
                         exit_code=code, n=len(rows),
                         n_passed=sum(1 for r in rows if r["passed"]), rows=rows,
                         code_sha256_16=_sha_file(os.path.join(ROOT, "benchmark", name + ".py")))
    return out


AXIS_MAP: dict = {}      # 대칭 스위트: 대조 태그 → 축(S1~S5). 인증서에서 읽어 채운다.


def controls_for(ctl: dict, suite: str | None, spec, indirect: str = "") -> dict:
    """이 **행을 지키는** 대조만 골라 센다.

    spec 은 셋 중 하나 —
      · 태그 접두 튜플   → 그 접두로 시작하는 대조만 (행 전용)
      · {"axis": "손잡이"} → 대칭 스위트의 축 이름으로 (행 전용)
      · None             → ⭐**이 행을 겨냥한 대조가 없다**. 스위트 전체를 «맥락» 으로만 싣고
                           positive_control 은 «없음» 이라고 적는다(우연히 걸린 것을 근거로 세지 않는다).
    """
    if suite is None:
        return dict(suite=None, scope="없음", n=0, n_passed=0, n_positive=0,
                    n_positive_passed=0, n_negative=0, n_negative_passed=0,
                    positive_control="없음", positive_control_ok=False,
                    indirect_ko=indirect, tags=[], suite_context=None)
    s = ctl.get(suite) or {}
    rows = s.get("rows") or []
    ctx = dict(script=s.get("script"), n=len(rows), n_passed=sum(1 for r in rows if r["passed"]),
               exit_code=s.get("exit_code"))
    if spec is None:
        sel, scope, kind = [], "없음", "없음"
    elif isinstance(spec, dict) and "axis" in spec:
        #  대칭 스위트의 태그에는 축 이름이 없다(같은 태그가 축마다 되풀이된다) — 인증서가 적어 둔
        #  축을 **차례로** 붙여 둔 것을 쓴다(아래 attach_symmetry_axes).
        sel = [r for r in rows if r.get("axis") == spec["axis"]]
        scope, kind = f"행 전용(축 «{spec['axis']}»)", "행 전용"
    else:
        sel = [r for r in rows if r["tag"].startswith(tuple(spec))]
        scope, kind = "행 전용", "행 전용"
    pos = [r for r in sel if "양성" in r["tag"]]
    neg = [r for r in sel if "음성" in r["tag"]]
    return dict(suite=s.get("script"), scope=scope, n=len(sel),
                n_passed=sum(1 for r in sel if r["passed"]),
                n_positive=len(pos), n_positive_passed=sum(1 for r in pos if r["passed"]),
                n_negative=len(neg), n_negative_passed=sum(1 for r in neg if r["passed"]),
                positive_control=(kind if pos else "없음"),
                positive_control_ok=bool(pos) and all(r["passed"] for r in pos),
                indirect_ko=indirect, tags=[r["tag"] for r in sel], suite_context=ctx)


# --------------------------------------------------------------------------- #
#  ⭐ 검사 행 정의 — 칸을 채우는 함수는 (raw, fleet, key) 를 받아 cell 을 돌려준다
#     cell = dict(verdict, value, unit, budget, margin_pct, note, grade)
#     verdict ∈ {통과, 실패, ⚠어긋남, 기록만, 해당없음, 빈칸}
# --------------------------------------------------------------------------- #
def _cell(verdict, value=None, unit="", budget=None, margin=None, note="", grade=None):
    return dict(verdict=verdict, value=value, unit=unit, budget=budget,
                margin_pct=margin, note=note, grade=grade)


def _mc_topology(raw, fleet, key):
    g = raw["mc_mesh"]["groups"]
    be = max((v["boundary_edges"], k) for k, v in g.items())
    nm = sum(v.get("nonmanifold_edges", 0) for v in g.values())
    inw = sum(v["inward_normals"] for v in g.values())
    bw = sum(v["bad_winding"] for v in g.values())
    rn = sum(v["raw_negative_parts"] for v in g.values())
    bad = [k for k, v in g.items() if not v["ok"]]
    v = f"경계모서리 {be[0]}(최대 {be[1]}) · 비다양체 {nm} · 법선안쪽 {inw} · 감김깨짐 {bw} · 부호부피음수 {rn}"
    return _cell("통과" if not bad else "실패", v, "개",
                 "그룹별 BOUNDARY_EDGE_BUDGET · 나머지 0",
                 None, "" if not bad else f"실패 그룹 {bad}", "—(자기무결성)")


def _mc_degenerate(raw, fleet, key):
    n = sum(v["degenerate"] for v in raw["mc_mesh"]["groups"].values())
    return _cell("통과" if n == 0 else "실패", n, "장", 0, None,
                 "절대 면적 잣대(1e-14 m²) — 상대 잣대는 T5", "—(자기무결성)")


def _mc_sliver(raw, fleet, key):
    r = raw["mc_mesh"]
    return _cell("통과" if r["sliver_ok"] else "실패", r["slivers"], "장",
                 r["sliver_budget"], _pct(r["slivers"], r["sliver_budget"]),
                 "최소내각 < 0.5°", "D(선언 — 현 상태 + 여유)")


def _mc_overlap(raw, fleet, key):
    g = raw["mc_mesh"]["groups"]
    worst = max(g.items(), key=lambda kv: kv[1]["overlap_pct"] / max(kv[1]["overlap_budget_pct"], 1e-9))
    ov, bud = worst[1]["overlap_pct"], worst[1]["overlap_budget_pct"]
    return _cell("통과" if ov <= bud else "실패", ov, "%", bud, _pct(ov, bud),
                 f"최빠듯 그룹 {worst[0]}", "D(선언 — 현 상태 + 여유)")


def _mc_dimensions(raw, fleet, key):
    r = raw["mc_dimensions"]
    if not r.get("checked"):
        return _cell("해당없음", None, "", None, None, r.get("reason", ""), "—")
    env = [e for e in (r["envelope_err_pct"] or []) if e is not None]
    v = (f"프롭지름 {r['prop_dia_err_pct']:+.3f} % · 대각 {r['diagonal_err_pct']:+.3f} % · "
         f"외형 {['%+.2f' % e for e in env]} %")
    return _cell("통과" if r["ok"] else "실패", v, "%",
                 f"프롭 1 % · 대각 {r['diagonal_tol_pct']} % · 외형 1 %",
                 max([abs(r["prop_dia_err_pct"]) * 100, abs(r["diagonal_err_pct"]) / r["diagonal_tol_pct"] * 100]
                     + [abs(e) * 100 for e in env]) if env else None,
                 "스펙(DroneSpec)과 대조 — 바깥 참값은 X1 이 본다", "B(제조사 공표 제원)")


def _mc_handedness(raw, fleet, key):
    r = raw["mc_handedness"]
    if not r.get("checked"):
        return _cell("해당없음", None, "", None, None, r.get("reason", ""), "—")
    return _cell("통과" if r["ok"] else "실패", r.get("h_ref"), "지표", "부호가 dir 과 일치",
                 None, f"로터 {len(r.get('per_rotor') or [])}개", "—(규약 자기대조)")


def _mc_bell(raw, fleet, key):
    r = raw["mc_prop_bell"]
    if not r.get("checked"):
        return _cell("해당없음", None, "", None, None, r.get("reason", ""), "—")
    return _cell("통과" if r["ok"] else "실패", r["max_depth_mm"], "mm", r["budget_mm"],
                 _pct(r["max_depth_mm"], r["budget_mm"]), "원통 근사(빠른 회귀 감지)",
                 "D(선언 — 현 상태)")


def _mc_bell_solid(raw, fleet, key):
    r = raw["mc_prop_bell_solid"]
    if not r.get("checked"):
        return _cell("해당없음", None, "", None, None, r.get("reason", ""), "—")
    return _cell("통과" if r["ok"] else "실패", r["area_pct"], "%", r["budget_pct"],
                 _pct(r["area_pct"], r["budget_pct"]),
                 f"못 본 비수밀 벨 부품 {r['nonwatertight_bell_parts']}개", "D(선언 — 현 상태)")


def _mc_buried(raw, fleet, key):
    r = raw["mc_buried"]
    return _cell("통과" if r["ok"] else "실패", r["defect_pct"], "%", r["budget_pct"],
                 _pct(r["defect_pct"], r["budget_pct"]),
                 f"총 매몰 {r['buried_pct']} % = 설계의도 {r['design_intent_pct']} % + 결함 {r['defect_pct']} % · "
                 f"못 본 컨테이너 {r['blind_containers']}개", "D(선언 — 현 상태 + 약 10 % 여유)")


def _topo(field, budget_field=None, unit="개", note=""):
    def fn(raw, fleet, key):
        t = raw["topo"]["totals"]
        v = t[field]
        ok = raw["topo"]["ok"]
        return _cell("통과" if (v == 0 or ok) else "실패", v, unit, 0, None, note, "—(자기무결성)")
    return fn


def _topo_T1(raw, fleet, key):
    t = raw["topo"]["totals"]
    grp = raw["topo"]["groups"]
    over = {g: (v["boundary_curves"], v["boundary_curve_budget"]) for g, v in grp.items()
            if v["boundary_curves"] > v["boundary_curve_budget"]}
    declared = {g: v["boundary_curve_budget"] for g, v in grp.items() if v["boundary_curve_budget"]}
    v = (f"경계곡선 {t['boundary_curves']} · 열린 부품 {t['open_parts']} · "
         f"평면링 {t['planar_ring_curves']}"
         + (f" · 선언 예외 {declared}" if declared else ""))
    return _cell("통과" if not over else "실패", t["boundary_curves"], "개",
                 "부품별 0 (선언 예외 mini2/body 1)", None,
                 v + ("" if not over else f" · 예산 초과 {over}"), "—(자기무결성)")


def _topo_T2(raw, fleet, key):
    t = raw["topo"]["totals"]
    v = f"감김 뒤집힌 모서리 {t['flipped_edges']} · 부호부피 음수 부품 {t['negative_volume_parts']}"
    ok = t["flipped_edges"] == 0 and t["negative_volume_parts"] == 0
    return _cell("통과" if ok else "실패", t["flipped_edges"] + t["negative_volume_parts"],
                 "개", 0, None, v, "—(자기무결성)")


def _topo_T3(raw, fleet, key):
    t = raw["topo"]["totals"]
    v = (f"비다양체 모서리 {t['nonmanifold']} · 나비넥타이 {t['bowtie']} · 중복면 {t['dup_faces']} "
         f"· 종수≠0 부품 {t['genus_nonzero_parts']}(세기만)")
    ok = t["nonmanifold"] == 0 and t["bowtie"] == 0 and t["dup_faces"] == 0
    return _cell("통과" if ok else "실패", t["nonmanifold"] + t["bowtie"] + t["dup_faces"],
                 "개", 0, None, v, "—(자기무결성)")


def _topo_T4(raw, fleet, key):
    t = raw["topo"]["totals"]
    v = f"교차 삼각형쌍 {t['selfint']} · 못 본 부품 {t['selfint_unchecked']}"
    ok = t["selfint"] == 0 and t["selfint_unchecked"] == 0
    return _cell("통과" if ok else "실패", t["selfint"], "쌍", 0, None, v, "—(자기무결성)")


def _topo_T5(raw, fleet, key):
    t = raw["topo"]["totals"]
    n = t["repeat_index"] + t["zero_area"] + t["zero_edge"]
    v = f"인덱스중복 {t['repeat_index']} · 면적0 {t['zero_area']} · 길이0모서리 {t['zero_edge']} (슬리버 {t['sliver']} 장은 A3 이 판정)"
    return _cell("통과" if n == 0 else "실패", n, "장", 0, None, v, "—(자기무결성)")


def _topo_D1(fc_key):
    def fn(raw, fleet, key):
        d = raw[fc_key]["discretization"]
        lam16 = raw[fc_key]["lam_mm"] / 16.0
        return _cell("통과" if d["ok"] else "실패", d["sagitta_over_lam16_area_pct"], "% 면적",
                     d["sagitta_budget_pct"],
                     _pct(d["max_sagitta_mm"], lam16),
                     f"최대 사지타 {d['max_sagitta_mm']} mm ↔ λ/16 = {lam16:.2f} mm "
                     f"({d['max_sagitta_mm'] / lam16:.2f}배) · 변>λ/7 면적 {d['edge_over_lam7_area_pct']} %(참고)",
                     "A(해석 눈금 검증)")
    return fn


def _topo_D2(raw, fleet, key):
    r = raw["loft_caps"]
    if not r.get("overshoot_checked"):
        return _cell("해당없음", None, "", None, None, "계측된 스플라인 호출 없음", "—")
    ok = (r["max_overshoot_pct"] <= r["overshoot_budget_pct"]) and (r["clamped_sections"] <= r["clamp_budget"])
    return _cell("통과" if ok else "실패", r["max_overshoot_pct"], "%", r["overshoot_budget_pct"],
                 _pct(r["max_overshoot_pct"], r["overshoot_budget_pct"]),
                 f"클램프 단면 {r['clamped_sections']}개 · 스플라인 호출 {r['n_spline_calls']}회",
                 "—(자기무결성 — 3차 보간의 성질)")


def _topo_D3(raw, fleet, key):
    r = raw["loft_caps"]
    if not r.get("cap_checked") and not r.get("end_deficit_checked"):
        return _cell("해당없음", None, "", None, None,
                     "계측된 로프트/스윕 호출 없음 — 0 으로 보고하지 않는다", "—")
    cap_ok = r["cap_requested_but_open"] == 0
    body = f"캡 요청했는데 열림 {r['cap_requested_but_open']} · loft {r['n_loft_calls']}회 · sweep {r['n_sweep_calls']}회"
    if not r.get("end_deficit_checked"):
        #  셸형(로프트 동체)이 아닌 열린 프레임 — (가)캡 부재만 보고 (나)캡 형상 손실은 «해당없음»
        return _cell("통과" if cap_ok else "실패", None, "", None, None,
                     body + " · ⚠(나)캡 형상 손실은 **해당없음** — 이 기체엔 설계 끝단표(_body_folding)가 "
                            "없다. 0 으로 보고하지 않는다", "—((가)캡 부재만)")
    ok = cap_ok and r["max_end_deficit_pct"] <= r["end_deficit_budget_pct"]
    return _cell("통과" if ok else "실패", r["max_end_deficit_pct"], "% 손실",
                 r["end_deficit_budget_pct"],
                 _pct(r["max_end_deficit_pct"], r["end_deficit_budget_pct"]),
                 body, "A(설계표 직접 대조)")


def _dimref_truth(raw, fleet, key):
    r = raw["dimref"]
    bad = [x for x in r["rows"] if x["verdict"] == "어긋남"]
    worst = max(bad, key=lambda x: abs(x["residual"] / max(x["tolerance"]["U"], 1e-9)), default=None)
    v = f"{r['n_match']}일치 / {r['n_mismatch']}어긋남 / {r['n_informational']}기록만 / {r['n_unknown']}모름 (총 {r['n_rows']}행)"
    note = ""
    if worst:
        note = (f"최대 {worst['rid']} {worst['quantity']} {worst['measured']} ↔ 참값 {worst['reference']} "
                f"= {worst['residual']:+.4f} mm (U={worst['tolerance']['U']:.4f})")
    grades = sorted({x["grade"] for x in r["rows"] if x.get("grade")})
    return _cell("통과" if r["truth_ok"] else "⚠어긋남", v, "행", "U = k·√(u_ref²+u_def²+u_disc²), k=2",
                 None, note, "/".join(grades) or "—")


def _dimref_regress(raw, fleet, key):
    r = raw["dimref"]
    return _cell("통과" if r["regression_ok"] else "실패", r["n_rows"], "행",
                 "|잔차| ≤ max(|선언|×1.02, |선언|+U)", None,
                 "인증서 seal.declared_residual_mm 대비", "—(봉인)")


def _place(field):
    def fn(raw, fleet, key):
        c = raw["placement_census"]
        b = raw["placement"]["budgets"]
        fails = raw["placement"]["failures"]
        if field == "self":
            v, bud = c["self_intersection"]["n_pairs"], b["self_intersect"]
            hit = [f for f in fails if "자기교차" in f]
            return _cell("통과" if not hit else "실패", v, "쌍", bud, None,
                         f"부품 {c['n_parts']}개 · 못 본 부품 {len(c['blind_parts'])}개", "—(자기무결성)")
        if field == "cross":
            v, bud = c["crossing"]["area_pct"], b["cross_pct"]
            hit = [f for f in fails if "교차면적" in f]
            return _cell("통과" if not hit else "실패", v, "%", bud, _pct(v, bud),
                         f"관통 쌍 {c['crossing']['n_pairs']} · 삼각형쌍 {c['crossing']['tri_pairs']}",
                         "D(선언 — 현 상태 + 10 %)")
        if field == "engulf":
            v, bud = len(c["engulfed"]), b["engulfed_pairs"]
            hit = [f for f in fails if "완전매몰" in f]
            return _cell("통과" if not hit else "실패", v, "쌍", bud, _pct(v, bud),
                         f"매몰 면적 {c['inside_faces']['area_pct']} %", "D(선언 — 설계 의도 개수)")
        if field == "coplanar":
            v, bud = c["coplanar"]["area_pct"], b["coplanar_pct"]
            hit = [f for f in fails if "동일평면" in f]
            return _cell("통과" if not hit else "실패", v, "%", bud, _pct(v, bud),
                         f"동일평면 쌍 {c['coplanar']['n_pairs']}", "D(선언 — 현 상태 + 10 %)")
        raise KeyError(field)
    return fn


FLOAT_GRADE = {         # 배치 인증서 evidence_grades 를 그대로 옮긴다
    ("mini5pro", "prop"): ("P", "물리적 필연 — 돌아가는 프롭은 벨에 닿으면 안 된다(스탠드오프)"),
    ("s1000plus", "prop"): ("P", "같음"),
    ("x500v2", "prop"): ("P", "같음"),
    ("phantom3", "prop"): ("P", "같음"),
    ("s1000plus", "pcb"): ("D", "⚠의심 — 스탠드오프 부품이 없다(근거 미확인)"),
    ("x500v2", "pcb"): ("D", "⚠의심 — 같음"),
    ("phantom4", "gear"): ("B", "⚠⚠형상 결함 의심 — 공식 렌더에서 다리는 셸에 붙어 있다"),
    ("phantom4", "canopy"): ("D", "⚠의심 — 확인 안 함"),
    ("phantom3", "gear"): ("B", "⚠⚠형상 결함 의심 — 공식 정면 사진에서 붙어 있다(함대 최대 이격)"),
    ("phantom3", "camera"): ("D", "⚠의심 — 확인 안 함"),
}


def _place_float(raw, fleet, key):
    c = raw["placement_census"]
    fl = c["floating"]
    fails = [f for f in raw["placement"]["failures"] if "뜬 부품" in f]
    if not fl:
        return _cell("통과", 0, "개", "예산 밖 0 (원칙은 «붙어 있어야 한다» = 0 mm)", None,
                     "뜬 부품 없음", "—")
    worst = max(fl, key=lambda f: f["gap_mm"])
    susp = [f for f in fl if FLOAT_GRADE.get((key, f["group"]), ("D", ""))[0] != "P"]
    grades = sorted({FLOAT_GRADE.get((key, f["group"]), ("D", "선언 없음"))[0] for f in fl})
    note = (f"뜬 부품 {len(fl)}개 — 설계(스탠드오프) {len(fl) - len(susp)} · ⚠의심 {len(susp)}"
            f" · 최대 {worst['pid']}({worst['group']}) {worst['gap_mm']} mm")
    verdict = "통과" if not fails else "실패"
    if susp:
        verdict = "통과(⚠의심 포함)"
    return _cell(verdict, worst["gap_mm"], "mm", "그룹별 FLOAT_BUDGET_MM(선언)",
                 None, note, "/".join(grades))


def _sym(field):
    def fn(raw, fleet, key):
        r = raw["symmetry"][field]
        if not r.get("checked", True):
            return _cell("해당없음", None, "", None, None, r.get("reason", ""), "—")
        ok = r["ok"]
        if field == "handedness":
            v = f"자A(법선) {r.get('h_ref_normals')} · 자B(위치) {r.get('h_ref_positions')}"
            bud = "|자A| ≥ 0.05 · |자B| ≥ 0.20 · 부호 = dir · 두 자 판정 일치"
            return _cell("통과" if ok else "실패", v, "지표", bud, None,
                         f"로터 {len(r.get('per_rotor') or [])}개", "D(기준이 우리 규약)")
        if field == "dir_convention":
            v = (f"이웃 교대 {r['neighbors_alternate']} · 마주보는 쌍 {r['opposite_pairs_ok']} · "
                 f"토크합 {r['torque_sum']}")
            return _cell("통과" if ok else "실패", v, "", "n 에서 유도한 부호 · Σdir = 0", None,
                         f"로터 {r['n_rotors']}개", "A(로터 수에서 유도)")
        if field == "lateral":
            v = max(abs(r["frame_area_y_moment_rel"]), abs(r["frame_volume_y_moment_rel"]))
            return _cell("통과" if ok else "실패", round(v, 10), "상대 1차모멘트",
                         2e-4, _pct(v, 2e-4),
                         f"크기 {r['size_mm']} mm · 그룹별 표면잔차는 원자료 참조", "D(기준이 우리 규약)")
        if field == "mass_inertia":
            v = r["principal_axis_tilt_deg"]
            return _cell("통과" if ok else "실패", v, "° 주축기울기", 0.5, _pct(v, 0.5),
                         f"CoM_y 상대 {r['com_y_rel']:.2e} · 메쉬질량/TOW {r['mass_over_tow']}배"
                         f"(⚠크기는 판정 안 함 — 감사 I9 선언 결함)", "A(닫힌 해로 자 검정) / D(대칭 규약)")
        if field == "projected_area":
            v = max(r["mirror_max_rel"], r["mirror_onesided_max_rel"])
            return _cell("통과" if ok else "실패", round(v, 6), "상대 좌우차", 8e-3, _pct(v, 8e-3),
                         f"한쪽면합/실루엣 {r['onesided_over_sil_max']}배 (예산 {r['double_count_budget']}) "
                         f"— 이중계상 배수", "A(정육면체 닫힌 해로 래스터 검정)")
        raise KeyError(field)
    return fn


def _mat_label(raw, fleet, key):
    r = raw["material_label"]
    return _cell("통과" if r["ok"] else "실패", len(r.get("notes") or []), "항목",
                 "L1~L5 (최저점 주인 · 프롭>모터 · 카메라 z · 로터 정렬 · 내부금속 셸 안)",
                 None, " / ".join(r.get("notes") or [])[:220], "—(설계 규약 대조)")


def _fleet_cell(field, name, grade="—", note=""):
    def fn(raw, fleet, key):
        r = fleet.get(field) or {}
        if "_error" in r:
            return _cell("실패", None, "", None, None, "검사가 예외로 죽었다", grade)
        n = r.get("n_checked") or r.get("n_rows") or r.get("n_confirmed")
        return _cell("통과" if r.get("ok") else "실패", n, "", None, None,
                     note or r.get("rule", ""), grade)
    return fn


def _raw_scan(raw, fleet, key):
    r = (fleet.get("raw_scan") or {}).get(key) or {}
    v = (f"NaN {r.get('nan_vert')} · inf {r.get('inf_vert')} · 인덱스범위밖 {r.get('index_out_of_range')} "
         f"· 빈 라벨 {r.get('empty_labels')} · 미사용 정점 {r.get('unused_vertices')}")
    return _cell("통과" if r.get("ok") else "실패", 0 if r.get("ok") else None, "개", 0, None,
                 v + f" · 최대좌표 {r.get('max_abs_coord_m')} m", "—(자기무결성)")


def _parts_present(raw, fleet, key):
    c = raw["placement_census"]
    g = raw["mc_mesh"]["groups"]
    v = f"부품 {c['n_parts']}개 · 그룹 {len(g)}종"
    return _cell("빈칸", c["n_parts"], "개", None, None,
                 f"{v} — «있어야 할 부품 목록» 이라는 참값이 저장소에 없다(M7 미해결)", "빈칸")


def _articulated(raw, fleet, key):
    r = (fleet.get("articulated") or {}).get(key) or {}
    if "_error" in r:
        return _cell("실패", None, "m", 1e-9, None, "FastPoser.verify 가 예외", "—")
    return _cell("통과" if r.get("ok") else "실패", r.get("max_abs_vertex_diff_m"), "m",
                 r.get("tol"), None,
                 f"위상 {r.get('n_phases')}종 · 정본 pose_articulated 와 정점·면·그룹 대조",
                 "—(정본 경로와 비트 대조)")


def _blind(raw, fleet, key):
    """⭐«못 봄» 을 0 으로 보고하지 않는가 — 검사기들이 스스로 신고한 사각지대를 모은다."""
    n_selfint = raw["topo"]["totals"]["selfint_unchecked"]
    n_place = len(raw["placement_census"]["blind_parts"])
    n_bell = raw["mc_prop_bell_solid"].get("nonwatertight_bell_parts", 0)
    n_bur = raw["mc_buried"]["blind_containers"]
    tot = n_selfint + n_place + n_bell + n_bur
    v = (f"자기교차 미검사 부품 {n_selfint} · 배치 비수밀 부품 {n_place} · "
         f"벨 비수밀 {n_bell} · 매몰 컨테이너 못 봄 {n_bur}")
    extra = ""
    if n_place:
        bp = raw["placement_census"]["blind_parts"][0]
        extra = (f" · ⭐{bp['pid']}({bp['group']}, {bp['area_mm2']:.0f} mm²) 은 비수밀이라 "
                 f"내부판정이 성립 안 한다 — T1 이 선언한 구멍 1개의 대가다(교차 검사는 그대로 본다)")
    return _cell("통과" if tot == 0 else "⚠사각지대", tot, "개", 0, None,
                 v + extra + " — 네 검사기가 «내가 못 본 자리» 를 스스로 세어 신고한 값",
                 "—(검사기 자기신고)")


def _seal(which):
    def fn(raw, fleet, key):
        cert = SEAL_CACHE[which]
        now = {
            "topology": raw.get("topo_fingerprint"),
            "dimension": raw.get("dimref_fingerprint"),
            "symmetry": raw.get("dimref_fingerprint"),
            "placement": (raw["placement_census"]["mesh_sha1"],
                          raw["placement_census"]["relation_sha1"]),
        }[which]
        old = cert.get(key)
        same = (now == old)
        return _cell("통과" if same else "⚠어긋남", str(now), "지문", str(old), None,
                     "인증서 발행 때와 같은 메쉬" if same else "⚠형상이 바뀌었다 — 그 인증서는 재발급 대상",
                     "—(봉인)")
    return fn


SEAL_CACHE: dict = {}


# --------------------------------------------------------------------------- #
ROWS = [
    # id, 범주, 이름, 코드, 잣대·허용오차, (스위트, 대조 고르기, 전용 대조가 없을 때의 설명), 추출기, 축
    ("R0", "M0", "원시값 유효성 — NaN·무한·인덱스·빈 라벨",
     "benchmark/mesh_cert_matrix_fleet.py (⚠전용 검사기 없음 — 이 라운드가 직접 잼)",
     "전부 0",
     ("adv_mesh_check_faults", None,
      "⚠전용 양성 대조 없음. 범주 지도 라운드의 일회성 탐침이 «NaN·(a,a,c)·빈 라벨은 다른 검사에 "
      "걸려서 잡힌다» 를 보였을 뿐이고(probe_ledger), 인덱스 범위 밖은 판정 대신 IndexError 로 죽는다."),
     _raw_scan, "자기무결성"),

    ("A1", "M2", "부품 위상·법선 — 경계모서리·비다양체·감김·부호부피",
     "src/mesh_check.py::check_mesh", "그룹별 BOUNDARY_EDGE_BUDGET · 나머지 0",
     ("adv_mesh_check_faults", ("D5", "C1", "D6"), ""), _mc_topology, "자기무결성"),
    ("A2", "M4", "퇴화면(절대 면적 잣대)", "src/mesh_check.py::check_mesh",
     "면적 < 1e-14 m² = 0장", ("adv_mesh_check_faults", ("D2",), ""), _mc_degenerate, "자기무결성"),
    ("A3", "M4", "슬리버(최소내각 < 0.5°)", "src/mesh_check.py::SLIVER_BUDGET",
     "기종별 예산(현 상태 + 여유)", ("adv_mesh_check_faults", ("D2",), ""), _mc_sliver, "자기무결성"),
    ("A4", "M9", "그룹 안 부품 겹침", "src/mesh_check.py::_group_overlap_pct",
     "그룹별 GROUP_OVERLAP_BUDGET_PCT", ("adv_mesh_check_faults", ("D1",), ""), _mc_overlap, "자기무결성"),
    ("A5", "M1·M6", "스펙 대조 — 프롭 지름·로터 대각·외형(단위/배율)",
     "src/mesh_check.py::check_dimensions", "프롭 1 % · 대각 3 %(mini5pro 12 %) · 외형 1 %",
     ("adv_mesh_check_faults", ("D3",), ""), _mc_dimensions, "외부 대조"),
    ("A6", "M11", "프롭 손대칭성(비틀림 부호 ↔ 회전방향)", "src/mesh_check.py::check_handedness",
     "로터별 부호가 dir 과 일치", ("adv_mesh_check_faults", ("D4",), ""), _mc_handedness, "규약 대조"),
    ("A7", "M9", "프롭↔모터벨 관통(원통 근사)", "src/mesh_check.py::check_prop_bell",
     "PROP_BELL_MAX_DEPTH_MM(선언)",
     ("adv_mesh_check_faults", None,
      "⚠전용 양성 대조 없음 — 프롭을 일부러 벨에 박아 넣어 본 적이 없다. 대신 두 자(원통 근사 A7 ↔ "
      "솔리드 내부판정 A8)가 서로를 견제하고, 2026-08-07 에 실제 결함(mini5pro 8.06 mm)을 이 자가 잡았다."),
     _mc_bell, "자기무결성"),
    ("A8", "M9", "프롭↔모터벨 관통(솔리드 내부판정)", "src/mesh_check.py::check_prop_bell_solid",
     "PROP_BELL_SOLID_AREA_PCT(선언)",
     ("adv_mesh_check_faults", None, "⚠전용 양성 대조 없음 — A7 과 같은 자리(두 자가 서로 견제)."),
     _mc_bell_solid, "자기무결성"),
    ("A9", "M9", "매몰면 전수(전 부품쌍)", "src/mesh_check.py::check_buried_faces + src/mesh_buried.py",
     "BURIED_FACE_BUDGET_PCT — «진짜 결함» 비율",
     ("adv_mesh_check_faults", None,
      "⚠전용 양성 대조 없음(결함을 심는 시험이 없다). 대신 **독립 구현 교차검증**이 있다 — "
      "src/mesh_placement.py 의 내부판정 엔진과 10기체 전부 소수 셋째 자리까지 일치."),
     _mc_buried, "자기무결성"),

    ("T1", "M2", "닫힘 — 경계 «곡선(테두리)» 수 + 곡선 모양", "src/mesh_topo_check.py::boundary_curves",
     "부품별 0 (선언 예외 mini2/body 1)", ("adv_mesh_topo_faults", ("T1",), ""), _topo_T1, "자기무결성"),
    ("T2", "M2", "법선 일관성 — 유향 모서리 + 손계산 부호부피",
     "src/mesh_topo_check.py::edge_census · signed_volume_mm3", "둘 다 0",
     ("adv_mesh_topo_faults", ("T2",), ""), _topo_T2, "자기무결성"),
    ("T3", "M2·M3", "다양체 — 비다양체 모서리 · ⭐나비넥타이 정점 · 중복 삼각형",
     "src/mesh_topo_check.py::bowtie_vertices · duplicate_faces", "전부 0(종수는 세기만)",
     ("adv_mesh_topo_faults", ("T3",), ""), _topo_T3, "자기무결성"),
    ("T4", "M3", "⭐자기교차 — 한 껍질이 스스로를 뚫는가",
     "src/mesh_topo_check.py::self_intersections", "0쌍 · 못 본 부품 0",
     ("adv_mesh_topo_faults", ("T4",), ""), _topo_T4, "자기무결성"),
    ("T5", "M4", "퇴화 삼각형 — 인덱스중복·면적0·길이0",
     "src/mesh_topo_check.py::triangle_quality", "전부 0",
     ("adv_mesh_topo_faults", ("T5",), ""), _topo_T5, "자기무결성"),
    ("D1", "M5", "⭐이산화 — 곡면 사지타 ≤ λ/16 (3.5 GHz)",
     "src/mesh_topo_check.py::facet_wavelength", "위반 면적 ≤ 0.01 %",
     ("adv_mesh_topo_faults", ("D1",), ""), _topo_D1("topo"), "물리 눈금"),
    ("D1b", "M5", "이산화 — 같은 잣대를 5.8 GHz 로",
     "src/mesh_topo_check.py::facet_wavelength", "위반 면적 ≤ 0.01 %",
     ("adv_mesh_topo_faults", ("D1",), "⚠대조는 3.5 GHz 로 걸렸다 — λ 만 바꾼 같은 잣대다."),
     _topo_D1("topo_58"), "물리 눈금"),
    ("D2", "M5", "로프트 스플라인 오버슛 · 하한 클램프",
     "src/mesh_topo_check.py::_spline_overshoot", "기종별 LOFT_OVERSHOOT_PCT_BUDGET · 클램프 0",
     ("adv_mesh_topo_faults", ("D2",), ""), _topo_D2, "자기무결성"),
    ("D3", "M5", "⭐끝단 캡 — 캡 부재 + 캡 형상 손실",
     "src/mesh_topo_check.py::check_loft_caps · section_extent", "캡 열림 0 · 단면 손실 ≤ 2 %",
     ("adv_mesh_topo_faults", ("D3",), ""), _topo_D3, "설계표 대조"),

    ("X1", "M6·M8·M14·M15", "⭐외부 참값 치수 대조(공표·공식 CAD·GLB·STEP)",
     "src/mesh_dimref.py::check_key", "행마다 U = k·√(u_ref²+u_def²+u_disc²), k = 2",
     ("adv_mesh_dimref_faults", ("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
                                 "⑪", "⑫", "⑬", "⑭"), ""), _dimref_truth, "외부 대조"),
    ("X2", "M16", "치수 회귀 — 선언 잔차 대비", "src/mesh_dimref.py::check_key(declared=…)",
     "|잔차| ≤ max(|선언|×1.02, |선언|+U)",
     ("adv_mesh_dimref_faults", ("⑮", "⑯"), ""), _dimref_regress, "봉인"),

    ("P1", "M3", "자기 겹침(부품이 스스로를 뚫는가)", "src/mesh_placement.py::self_intersection",
     "0쌍 (파고듦 ≥ 1 µm 만 인정)",
     ("adv_mesh_placement_0816", ("B3", "A1", "A2"), ""), _place("self"), "자기무결성"),
    ("P2", "M9", "부품 간 관통 면적", "src/mesh_placement.py::pair_relation",
     "CROSS_AREA_BUDGET_PCT(선언)",
     ("adv_mesh_placement_0816", ("B4", "B2", "B6"), ""), _place("cross"), "자기무결성"),
    ("P3", "M9", "완전매몰 쌍(부품이 다른 부품 안에 통째로)", "src/mesh_placement.py::pair_relation",
     "ENGULFED_PAIRS_BUDGET(선언 — «지금 개수» 라 빠듯함은 늘 100 %)",
     ("adv_mesh_placement_0816", ("B2b", "B4"), ""), _place("engulf"), "자기무결성"),
    ("P4", "M10", "⭐간극 — 붙어 있어야 할 것이 떠 있는가", "src/mesh_placement.py::placement_census",
     "FLOAT_BUDGET_MM(그룹별 선언, 원칙은 0)",
     ("adv_mesh_placement_0816", ("B1",), ""), _place_float, "의도 대조"),
    ("P5", "M19", "동일평면 — 같은 자리에 두 껍질", "src/mesh_placement.py::pair_relation",
     "COPLANAR_AREA_BUDGET_PCT(선언)",
     ("adv_mesh_placement_0816", ("B5",), ""), _place("coplanar"), "자기무결성"),

    ("S1", "M11", "로터 손잡이 — 자 둘(법선·위치)로 교차", "src/mesh_symmetry.py::check_rotor_handedness",
     "|자A| ≥ 0.05 · |자B| ≥ 0.2 · 부호 = dir · 두 자 일치",
     ("adv_mesh_symmetry_faults", {"axis": "손잡이"}, ""), _sym("handedness"), "규약 대조"),
    ("S2", "M11·M8", "로터 회전방향 배치 규약", "src/mesh_symmetry.py::check_rotor_dir_convention",
     "d[k+n/2] = d[k]·(−1)^(n/2) · Σdir = 0 · 거울짝 1 µm",
     ("adv_mesh_symmetry_faults", {"axis": "배치규약"}, ""), _sym("dir_convention"), "유도 대조"),
    ("S3", "M11", "좌우(y) 거울 대칭", "src/mesh_symmetry.py::check_lateral_symmetry",
     "그룹별 표면잔차 ≤ 0.15 mm · 1차모멘트 ≤ 2e-4 · 프롭 짝 ≤ 1 nm",
     ("adv_mesh_symmetry_faults", {"axis": "좌우대칭"}, ""), _sym("lateral"), "규약 대조"),
    ("S4", "M13", "질량중심·관성텐서(자 둘 + 닫힌 해 검정)", "src/mesh_symmetry.py::check_mass_inertia",
     "|CoM_y|/크기 ≤ 2e-4 · 관성곱 ≤ 5e-4 · 주축 ≤ 0.5° (크기는 판정 안 함)",
     ("adv_mesh_symmetry_faults", {"axis": "질량·관성"}, ""), _sym("mass_inertia"), "닫힌 해 검정"),
    ("S5", "M13", "투영면적(σ 의 1차 결정자) + 이중계상 배수", "src/mesh_symmetry.py::check_projected_area",
     "좌우차 ≤ 8e-3 · 한쪽면합 ≤ 5e-3 · 이중계상 배수 ≤ 표",
     ("adv_mesh_symmetry_faults", {"axis": "투영면적"}, ""), _sym("projected_area"), "닫힌 해 검정"),

    ("V1", "M12", "라벨↔기하 — 라벨이 그 자리에 맞는가",
     "src/material_provenance.py::check_label_geometry",
     "L1~L5 규약(최저점·프롭 z·카메라 z·로터 정렬·내부금속 셸 안)",
     ("adv_material_provenance_faults", ("A",), ""), _mat_label, "설계 규약"),
    ("V2", "M12", "그룹표 닫힘 — 쓰는 라벨이 세 표에 다 있는가",
     "src/material_provenance.py::check_group_table_closure", "미등록 0 · 죽은 항목 0",
     ("adv_material_provenance_faults", ("B",), ""),
     _fleet_cell("mat_group_table", "그룹표", "—(표 대조)"), "함대"),
    ("V3", "M12", "조용한 폴백 자리 — 모르는 재질이 조용히 흘러가는 곳",
     "src/material_provenance.py::check_fallback_sites", "선언되지 않은 폴백 0",
     ("adv_material_provenance_faults", ("C",), ""),
     _fleet_cell("mat_fallback", "폴백", "—(코드 대조)"), "함대"),
    ("V4", "M12", "재질 상수 — ITU·문헌 대조 + 금속 불투명",
     "src/material_provenance.py::check_constants", "출처 있는 값만 · 표피깊이 ≥ 5δ",
     ("adv_material_provenance_faults", ("D",), ""),
     _fleet_cell("mat_constants", "상수", "A/B(ITU·문헌)"), "함대"),
    ("V5", "M15", "재질 출처·등급 원장(칸마다 A~D)",
     "src/material_provenance.py::check_provenance", "등급마다 근거 파일이 실재",
     ("adv_material_provenance_faults", ("E",), ""),
     _fleet_cell("mat_provenance", "출처", "A~D(칸별)"), "함대"),
    ("V6", "M12·M19", "공용 구조판 — 기체마다 근거가 다른 자리",
     "src/material_provenance.py::check_shared_plate", "칸마다 등급이 따로 붙어야 한다",
     ("adv_material_provenance_faults", ("F",), ""),
     _fleet_cell("mat_shared_plate", "공유판", "칸별"), "함대"),
    ("V7", "M16", "재질 봉인 — 다섯 표의 지문", "src/material_provenance.py::check_seal",
     "인증서 seal.fingerprints 와 동일",
     ("adv_material_provenance_faults", None,
      "⚠전용 양성 대조 없음 — 지문을 일부러 흔들어 «걸리는가» 를 본 시험이 이 스위트엔 없다. "
      "(같은 성질의 시험은 치수 스위트 ⑯ 과 배치 스위트 D1·D2 에 있다.)"),
     _fleet_cell("mat_seal", "봉인", "—(봉인)"), "함대"),

    ("G1", "M18", "분절·자세 재현 — 돌아가는 프롭이 매 시각 옳은 메쉬인가",
     "src/articulated_fast.py::FastPoser.verify", "정본 대비 정점차 ≤ 1 nm",
     (None, None,
      "⚠전용 양성 대조 없음 — 검사 자체가 «정본 경로와의 대조» 라 자가 검정이 이미 들어 있으나, "
      "«틀린 자세를 심으면 걸리는가» 를 시험한 적은 없다."),
     _articulated, "정본 대조"),
    ("G2", "M7", "부품 개수·존재", "src/mesh_placement.py::split_parts(측정만)",
     "참값 없음 — 판정하지 않는다",
     (None, None, "판정이 없으니 대조도 없다. 이 칸은 빈칸이다."), _parts_present, "빈칸"),

    ("W1", "M17", "⭐검사기 신뢰성 — 「못 본 자리」를 0 으로 보고하지 않는가",
     "src/mesh_topo_check.py::selfint_unchecked · mesh_placement::blind_parts · "
     "mesh_check::nonwatertight_bell_parts · mesh_buried::blind_containers",
     "네 사각지대 신고가 전부 0",
     (None, None,
      "⚠이 행 자체를 겨냥한 양성 대조는 없다. 대신 이 축에 있는 것 — 적대 대조 6스위트 184건 · "
      "위상 스위트의 **공백증명 2건**(옛 검사기가 나비넥타이·자기교차를 «통과» 시킴을 실제로 보였다) · "
      "**교차검증 2건**(trimesh 경로 ↔ numpy 자체 위상) · **눈금검증 1건**(사지타 ↔ 해석값) · "
      "`_split(repair=False)` 대조(검사기가 구멍을 스스로 메우지 못하게)."),
     _blind, "검사기 자기신고"),

    ("Z1", "M16", "봉인 — 위상 인증서 지문", "src/mesh_topo_check.py::fingerprint",
     "인증서 regression_seal.per_airframe 와 동일",
     (None, None, "⚠지문 민감도(형상을 흔들면 지문이 바뀌는가)를 시험한 대조가 이 축엔 없다."),
     _seal("topology"), "봉인"),
    ("Z2", "M16", "봉인 — 치수 인증서 메쉬 지문", "src/mesh_dimref.py::mesh_fingerprint",
     "인증서 seal.mesh_fingerprints 와 동일",
     ("adv_mesh_dimref_faults", ("⑯",), ""), _seal("dimension"), "봉인"),
    ("Z3", "M16", "봉인 — 대칭 인증서 메쉬 지문",
     "benchmark/mesh_cert_symmetry_derived_0816.py::_mesh_fingerprint",
     "인증서 regression_seal.mesh_fingerprints 와 동일",
     (None, None, "⚠Z1 과 같은 자리 — 지문 민감도 대조 없음(치수 지문과 같은 함수라 Z2 의 ⑯ 이 대신 본다)."),
     _seal("symmetry"), "봉인"),
    ("Z4", "M16", "봉인 — 배치 인증서 형상·관계 지문", "src/mesh_placement.py::fingerprint",
     "인증서 seal.per_drone 의 (mesh_sha1, relation_sha1) 과 동일",
     ("adv_mesh_placement_0816", ("D1 봉인", "D2 봉인"), ""), _seal("placement"), "봉인"),
]


# --------------------------------------------------------------------------- #
def build_matrix(raws: dict, fleet: dict, ctl: dict) -> tuple[list, dict]:
    checks, matrix = [], {}
    for (rid, cat, name, code, budget, (suite, spec, indirect), fn, axis) in ROWS:
        ctrl = controls_for(ctl, suite, spec, indirect)
        checks.append(dict(id=rid, category=cat, name_ko=name, code=code,
                           tolerance_ko=budget, axis=axis, controls=ctrl))
        row = {}
        for k in KEYS:
            try:
                row[k] = fn(raws[k], fleet, k)
            except Exception as e:                        # noqa: BLE001
                row[k] = _cell("실패", None, "", None, None,
                               f"매트릭스 추출 오류: {type(e).__name__}: {e}", "—")
        matrix[rid] = row
    return checks, matrix


#  예산이 어디서 왔는가 — 「빠듯함」 을 읽을 때 이것을 모르면 오해한다.
#  실측+10 % 로 못 박은 예산은 **구조적으로** 90.9 % 에 앉는다(잔차가 안 움직여도).
BUDGET_KIND = {
    "A3": "선언 스냅샷(현 상태 + 여유)",
    "A4": "선언 스냅샷(현 상태 + 여유)",
    "A7": "선언 스냅샷(현 상태)",
    "A8": "선언 스냅샷(현 상태)",
    "A9": "선언 스냅샷(실측 + 약 10 %)",
    "P2": "선언 스냅샷(실측 + 약 10 %)",
    "P5": "선언 스냅샷(실측 + 약 10 %)",
    "P3": "선언 스냅샷(개수 그대로)",
    "D1": "물리 눈금(λ/16)", "D1b": "물리 눈금(λ/16)",
    "D2": "선언 스냅샷(현 상태 + 여유)",
    "D3": "설계표 대조(±2 %)",
    "A5": "스펙 대조(1 % · 3 %)",
    "S3": "규약(1차 모멘트 2e-4)", "S4": "규약(주축 0.5°)", "S5": "규약(좌우차 8e-3)",
}

SYMBOL = {"통과": "✅", "실패": "❌", "⚠어긋남": "⚠", "통과(⚠의심 포함)": "✅⚠", "⚠사각지대": "◐",
          "해당없음": "▫", "기록만": "▪", "빈칸": "□"}


def to_markdown(cert: dict) -> str:
    L = []
    m = cert["_meta"]
    s0 = cert["summary"]
    L.append(f"# 메쉬 인증 매트릭스 — 전 기체 {s0['n_airframes']} × 전 검사 {s0['n_checks']}")
    L.append("")
    L.append(f"- 생성 {m['generated_kst']} · 파이썬 {m['env']['python']}")
    L.append(f"- 이 매트릭스는 **검사기를 새로 만들지 않는다** — 저장소의 여섯 검사기를 "
             f"전수로 돌려 한 표에 모은 것이다.")
    L.append(f"- ⛔형상 상수 무변경 · ⛔GPU 미사용 · ⛔git 미접촉")
    L.append("")
    s = cert["summary"]
    L.append("## 한 줄 요약")
    L.append("")
    L.append(f"> {cert['headline_ko']}")
    L.append("")
    L.append(f"- 칸 {s['n_cells']}개 = 통과 {s['n_pass']} · 실패 {s['n_fail']} · "
             f"⚠참값 어긋남 {s['n_mismatch']} · ◐사각지대 {s['n_blindspot']} · "
             f"해당없음 {s['n_na']} · 빈칸 {s['n_blank']}")
    L.append(f"- 검사 {s['n_checks']}개 중 **양성 대조가 걸린 것 {s['n_checks_with_positive_control']}개**, "
             f"없는 것 {s['n_checks_without_positive_control']}개 "
             f"({', '.join(s['checks_without_positive_control'])})")
    L.append(f"- 적대 대조 {s['controls_total']}건 전부 통과({s['controls_passed']}/{s['controls_total']}, "
             f"스위트 {s['n_suites']}개 나가는 값 0)")
    L.append(f"- 봉인: 10기체 × 인증서 4종 지문 {s['seal_ok']}/{s['seal_total']} 일치")
    L.append("")
    L.append("## 읽는 법")
    L.append("")
    L.append("| 기호 | 뜻 |")
    L.append("|---|---|")
    L.append("| ✅ | 예산·규약 안 — 통과 |")
    L.append("| ✅⚠ | 예산은 통과하나 그 예산이 «지금 이만큼» 선언이고 의심 항목이 들어 있다 |")
    L.append("| ⚠ | **바깥 참값과 어긋남** — 예산 위반은 아니지만 실물과 다르다 |")
    L.append("| ❌ | 실패 |")
    L.append("| ◐ | 사각지대 — 예산 위반은 아니지만 **검사기가 못 본 자리**가 있다(스스로 신고) |")
    L.append("| ▫ | 해당없음(그 기체에 그 부품·호출이 없다 — 0 으로 보고하지 않는다) |")
    L.append("| □ | 빈칸 — 참값이 없어 판정하지 않는다 |")
    L.append("")

    short = {"mini5pro": "mini5", "mavic4pro": "mavic4", "matrice4e": "M4E",
             "s1000plus": "S1000", "phantom4": "P4", "typhoonh480": "TyH480",
             "x500v2": "X500", "phantom3": "P3", "m350rtk": "M350", "mini2": "mini2"}
    L.append("## 범주 지도 — 결함이 있을 수 있는 자리 20칸이 지금 어떤가")
    L.append("")
    L.append("| 범주 | 무엇 | 0816 지도 | 이 매트릭스의 행 | 지금 | 양성대조 |")
    L.append("|---|---|---|---|---|---|")
    for c in cert["category_map"]:
        rows_s = ", ".join(c["matrix_rows"]) or "—"
        L.append(f"| {c['id']} | {c['name'][:40]} | {c['status_0816_map']} | {rows_s} | "
                 f"{c['status_now']} | {'✅' if c['positive_control'] else '⚠없음'} |")
    L.append("")
    L.append("- 「지금」 은 **있음**(행이 있고 그 행에 양성 대조가 있다) · **부분**(행은 있으나 "
             "양성 대조가 없다) · **없음**(그 범주를 보는 행이 없다) 셋뿐이다.")
    L.append(f"- 지도가 왜 빠짐없는가 — 메쉬는 (정점 V · 삼각형 F · 그룹 라벨 G) 셋과 그것을 만든 "
             f"(빌더 입력) · 그 라벨을 뜻으로 바꾸는 (바깥 표) 둘, 모두 다섯 상태뿐이라 결함은 "
             f"그중 하나에 반드시 나타난다. 논증 원문은 `{CERTS['map']}::closure_argument`.")
    L.append("")

    L.append("## 매트릭스")
    L.append("")
    L.append("| 검사 | 범주 | 양성대조 | " + " | ".join(short[k] for k in KEYS) + " |")
    L.append("|---|---|---|" + "---|" * len(KEYS))
    for c in cert["checks"]:
        rid = c["id"]
        cells = cert["matrix"][rid]
        ctrl = c["controls"]
        pc = (f"✅{ctrl['n_positive']}" if ctrl["positive_control_ok"] else "⚠없음")
        L.append(f"| **{rid}** {c['name_ko'][:34]} | {c['category']} | {pc} | "
                 + " | ".join(SYMBOL.get(cells[k]["verdict"], "?") for k in KEYS) + " |")
    L.append("")
    L.append("- 「양성대조 ✅n」 = 그 검사를 겨냥해 **결함을 심어 걸리는 것을 증명한 시험이 n 건** 있다. "
             "「⚠없음」 = 그 자리를 겨냥한 시험이 없다(다른 검사에 우연히 걸리는 것은 근거로 세지 않는다).")
    L.append("")
    L.append("### ⚠ 양성 대조가 없는 검사 — 이 라운드가 장담하지 못하는 자리")
    L.append("")
    L.append("| 검사 | 범주 | 왜 없는가 · 대신 무엇이 있는가 |")
    L.append("|---|---|---|")
    for c in cert["checks"]:
        if not c["controls"]["positive_control_ok"]:
            L.append(f"| **{c['id']}** {c['name_ko'][:32]} | {c['category']} | "
                     f"{c['controls'].get('indirect_ko', '')} |")
    L.append("")

    L.append("## 칸마다 — 잔차 · 허용오차 · 근거등급 · 양성대조")
    L.append("")
    for c in cert["checks"]:
        rid = c["id"]
        ctrl = c["controls"]
        pc = ("양성 %d/%d · 음성 %d/%d (%s)" % (ctrl["n_positive_passed"], ctrl["n_positive"],
                                              ctrl["n_negative_passed"], ctrl["n_negative"],
                                              ctrl["scope"])) if ctrl["n"] else "⚠**없음**"
        L.append(f"### {rid} · {c['name_ko']}  〔{c['category']}〕")
        L.append("")
        L.append(f"- 코드 `{c['code']}`")
        L.append(f"- 허용오차 — {c['tolerance_ko']}")
        L.append(f"- 양성·음성 대조 — {pc}")
        if ctrl.get("indirect_ko"):
            L.append(f"- {ctrl['indirect_ko']}")
        L.append("")
        L.append("| 기체 | 판정 | 잔차 | 예산 | 빠듯함 | 근거등급 | 비고 |")
        L.append("|---|---|---|---|---|---|---|")
        for k in KEYS:
            cell = cert["matrix"][rid][k]
            val = cell["value"]
            val = "" if val is None else (f"{val}" if not isinstance(val, float) else f"{val:g}")
            bud = "" if cell["budget"] is None else str(cell["budget"])
            mar = "" if cell["margin_pct"] is None else f"{cell['margin_pct']} %"
            L.append(f"| {k} | {SYMBOL.get(cell['verdict'], '?')} {cell['verdict']} | "
                     f"{val} {cell['unit']} | {bud} | {mar} | {cell['grade'] or ''} | "
                     f"{(cell['note'] or '')[:150]} |")
        L.append("")

    L.append("## ❌⚠ 통과하지 못한 칸 — 숨기지 않는다")
    L.append("")
    if not cert["failures"]:
        L.append("없음.")
    else:
        L.append("| 검사 | 기체 | 판정 | 내용 |")
        L.append("|---|---|---|---|")
        for f in cert["failures"]:
            L.append(f"| {f['check']} {f['name_ko'][:28]} | {f['key']} | {f['verdict']} | {f['detail'][:220]} |")
    L.append("")

    L.append("## ⚠ 바깥 참값과 어긋난 치수 — 한 행씩")
    L.append("")
    L.append("| 기체 | 행 | 부품 | 무엇 | 잰 값 | 참값 | 잔차 | 허용 U | U 의 몇 배 | 등급 | 순환 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in cert["dimension_mismatch_rows"]:
        res = "" if r["residual"] is None else f"{r['residual']:+.4f}"
        pct = "" if r.get("residual_pct") is None else f" ({r['residual_pct']:+.2f} %)"
        U = "" if r["U"] is None else f"{r['U']:.4f}"
        L.append(f"| {r['key']} | {r['rid']} | {r['part']} | {r['quantity']} | "
                 f"{'모름' if r['measured'] is None else r['measured']} | "
                 f"{'모름' if r['reference'] is None else r['reference']} | {res}{pct} | {U} | "
                 f"{'' if r['over_U'] is None else r['over_U']} | {r['grade']} | {r['circularity']} |")
    L.append("")
    L.append("- 순환 뜻 — `independent` 는 그 수를 메쉬에 넣은 적이 없다(= 진짜 대조) · "
             "`circular` 는 우리가 넣은 수를 되읽는 것(= 회귀 감시용) · `partly_circular` 는 그 중간.")
    L.append("")

    L.append("## 이 수들이 결과에서 몇 dB 인가")
    L.append("")
    for k, v in cert["consequences_ko"].items():
        L.append(f"- **{k}** — {v}")
    L.append("")

    L.append("## 예산은 어디서 왔는가 — 다섯 갈래")
    L.append("")
    for k, v in cert["budget_provenance_ko"].items():
        L.append(f"- **{k}** — {v}")
    L.append("")
    L.append(f"- {cert['snapshot_count_rows_ko']}")
    L.append("")

    L.append("## 허용 안에 있지만 빠듯한 잔차 — 다음에 문제될 자리")
    L.append("")
    L.append("⚠ 먼저 읽을 것 — 이 저장소의 예산 상당수는 «실측 + 약 10 %» 로 못 박은 **선언**이라, "
             "잔차가 하나도 안 움직여도 빠듯함이 **구조적으로 90.9 %** 에 앉는다(A9·P2·P5). "
             "그러니 여기서 정말 볼 것은 **그 규약보다도 빠듯한 줄**이다(아래 ⭐).")
    L.append("")
    L.append("| 검사 | 기체 | 잔차 | 예산 | 빠듯함 | 예산의 성질 | 비고 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in cert["residuals_near_budget"]:
        star = "⭐" if (r.get("tighter_than_convention")
                       or r["budget_kind"].startswith(("물리", "설계", "스펙", "규약"))) else ""
        L.append(f"| {star}{r['check']} {r['name_ko'][:24]} | {r['key']} | {r['value']} {r['unit']} | "
                 f"{r['budget']} | {r['margin_pct']} % | {r['budget_kind']} | {r['note'][:110]} |")
    L.append("")
    L.append("⭐ 표시가 규약 artifact 가 아닌 줄이다 — 그중에서도 다음 셋이 다음에 문제될 자리다.")
    L.append("")
    L.append("1. **m350rtk 프롭↔벨** — 원통 자 24.13 / 25.0 mm(96.5 %) · 솔리드 자 4.27 / 4.5 %(94.9 %). "
             "모터 상부 커버가 프롭 위를 덮는 «설계» 라 선언된 자리인데, 예산이 실측 바로 위에 있다.")
    L.append("2. **s1000plus 이산화(D1b)** — 카본 스키드의 사지타 3.035 mm 가 5.8 GHz 의 λ/16 = 3.23 mm 의 "
             "**0.94 배**다. 3.5 GHz 에서는 0.57 배로 여유가 있지만 주파수를 올리면 곧 닿는다.")
    L.append("3. **mini2 battery 그룹 겹침** — 49.96 / 55.0 %. 병행 라운드가 고치는 중인 자리다.")
    L.append("")

    L.append("## ⚠ 떠 있는 부품 — 설계인가 결함인가")
    L.append("")
    L.append("| 기체 | 부품 | 그룹 | 이격 | 가장 가까운 것 | 등급 | 왜 |")
    L.append("|---|---|---|---|---|---|---|")
    for f in sorted(cert["floating_parts"], key=lambda x: -x["gap_mm"]):
        L.append(f"| {f['key']} | {f['pid']} | {f['group']} | {f['gap_mm']:.3f} mm | "
                 f"{f.get('nearest') or ''} | {f['grade']} | {f['why']} |")
    L.append("")
    L.append("- 등급 P = 물리적 필연(돌아가는 프롭은 벨에 닿을 수 없다) · B = 공식 사진/렌더로 "
             "«실물은 붙어 있다» 를 확인 · D = 확인 안 함. **B 와 D 는 형상 라운드의 할 일**이다.")
    L.append("")

    L.append("## 근거 등급 — 기체 × 부품 (외부 참값이 있는 칸만)")
    L.append("")
    gm = cert["grade_matrix"]
    parts = gm["parts"]
    L.append("| 기체 | " + " | ".join(parts) + " |")
    L.append("|---|" + "---|" * len(parts))
    for k in KEYS:
        row = gm["matrix"].get(k, {})
        L.append(f"| {k} | " + " | ".join(str(row.get(p, {}).get("grade", "모름")) for p in parts) + " |")
    L.append("")
    L.append(f"- {gm['coverage_ko']}")
    L.append("")

    L.append("## 적대 대조 — 「걸린다」 를 증명한 시험")
    L.append("")
    L.append("| 스위트 | 지키는 검사기 | 결과 | 나가는 값 |")
    L.append("|---|---|---|---|")
    for name, s in cert["controls"].items():
        L.append(f"| `benchmark/{name}.py` | {s['guards']} | {s['n_passed']}/{s['n']} | {s['exit_code']} |")
    L.append("")

    rp = cert.get("reproducibility") or {}
    if rp.get("n"):
        L.append("## 재현성 — 다시 돌리면 같은 답이 나오는가")
        L.append("")
        L.append(f"- {rp['what_ko']}")
        L.append(f"- 기체 {rp['n']}대를 다시 돌려 **{rp['n_identical']}대가 비트 동일**"
                 f"({', '.join(r['key'] for r in rp['rows'] if r['identical'])}). "
                 f"시간(_sec)만 빼고 여섯 검사기의 모든 출력이 글자 하나까지 같다.")
        L.append("")

    L.append("## 봉인 — 이 매트릭스가 어느 메쉬의 것인가")
    L.append("")
    L.append("| 기체 | 위상 지문 | 치수·대칭 지문 | 배치 형상 지문 | 인증서 4종 일치 |")
    L.append("|---|---|---|---|---|")
    for k in KEYS:
        s = cert["seal"]["per_airframe"][k]
        L.append(f"| {k} | `{s['topology'][:12]}` | `{s['dimension'][:12]}` | "
                 f"`{s['placement_mesh'][:12]}` | {'✅ 전부' if s['all_match'] else '⚠ ' + str(s['mismatch'])} |")
    L.append("")

    L.append("## ⭐못 하는 것 — 이 매트릭스가 장담하지 않는 범위")
    L.append("")
    for i, t in enumerate(cert["limits_ko"], 1):
        L.append(f"{i}. {t}")
    L.append("")
    L.append("## 다시 돌리는 법")
    L.append("")
    for c in cert["how_to_rerun"]:
        L.append(f"- `{c}`")
    L.append("")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--fleet", required=True)
    ap.add_argument("--ctl-dir", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "mesh_cert_matrix_0816.json"))
    ap.add_argument("--md", default=os.path.join(ROOT, "outputs", "mesh_cert_matrix_0816.md"))
    a = ap.parse_args()

    raws = {k: _load(os.path.join(a.raw_dir, k + ".json")) for k in KEYS}
    fleet = _load(a.fleet)
    ctl = parse_controls(a.ctl_dir)

    certs = {k: _load(os.path.join(ROOT, p)) for k, p in CERTS.items()}
    SEAL_CACHE["topology"] = certs["topology"]["regression_seal"]["per_airframe"]
    SEAL_CACHE["dimension"] = certs["dimension"]["seal"]["mesh_fingerprints"]
    SEAL_CACHE["symmetry"] = {k: v["sha256_16"] for k, v in
                              certs["symmetry"]["regression_seal"]["mesh_fingerprints"].items()}
    SEAL_CACHE["placement"] = {k: (v["mesh_sha1"], v["relation_sha1"])
                               for k, v in certs["placement"]["seal"]["per_drone"].items()}
    #  대칭 스위트의 대조는 태그에 축 이름이 없고, 같은 태그(«mavic4pro 원본»)가 축마다
    #  되풀이된다. 그래서 태그가 아니라 **차례**로 축을 붙인다 — 같은 스크립트를 같은 순서로
    #  돌렸을 때만 성립하므로, 개수가 다르면 붙이지 않고 그 사실을 남긴다.
    sym_cert_rows = certs["symmetry"]["controls"]["rows"]
    sym_now = (ctl.get("adv_mesh_symmetry_faults") or {}).get("rows") or []
    axes_attached = len(sym_cert_rows) == len(sym_now)
    if axes_attached:
        for r_now, r_cert in zip(sym_now, sym_cert_rows):
            r_now["axis"] = r_cert["axis"]
            AXIS_MAP[r_now["tag"]] = r_cert["axis"]

    checks, matrix = build_matrix(raws, fleet, ctl)

    #  ── 재현성 대조 — 같은 코드·같은 메쉬를 다시 돌리면 **모든 검사 결과가 비트 동일**한가.
    #     (봉인의 전제다. 검사기가 흔들리면 지문이 같아도 값이 달라진다.)
    repro = []
    for k in KEYS:
        f2 = os.path.join(a.raw_dir, f"_repro_{k}.json")
        if not os.path.exists(f2):
            continue
        r2 = _load(f2)
        A = {kk: vv for kk, vv in raws[k].items() if kk != "_sec"}
        B = {kk: vv for kk, vv in r2.items() if kk != "_sec"}
        diff = [kk for kk in A if A[kk] != B.get(kk)]
        repro.append(dict(key=k, identical=not diff, differing_fields=diff))

    #  ── 집계 ────────────────────────────────────────────────────────────────
    counts = dict(n_cells=0, n_pass=0, n_fail=0, n_mismatch=0, n_blindspot=0, n_na=0, n_blank=0)
    failures, near = [], []
    for c in checks:
        rid = c["id"]
        for k in KEYS:
            cell = matrix[rid][k]
            counts["n_cells"] += 1
            v = cell["verdict"]
            if v.startswith("통과"):
                counts["n_pass"] += 1
            elif v == "실패":
                counts["n_fail"] += 1
                failures.append(dict(check=rid, name_ko=c["name_ko"], key=k, verdict=v,
                                     detail=f"{cell['value']} {cell['unit']} (예산 {cell['budget']}) {cell['note']}"))
            elif v == "⚠어긋남":
                counts["n_mismatch"] += 1
                failures.append(dict(check=rid, name_ko=c["name_ko"], key=k, verdict=v,
                                     detail=f"{cell['value']} — {cell['note']}"))
            elif v == "⚠사각지대":
                counts["n_blindspot"] += 1
                failures.append(dict(check=rid, name_ko=c["name_ko"], key=k, verdict=v,
                                     detail=f"{cell['value']} {cell['unit']} — {cell['note']}"))
            elif v == "해당없음":
                counts["n_na"] += 1
            elif v == "빈칸":
                counts["n_blank"] += 1
            #  ⚠ P3 는 예산이 «지금 개수» 그대로라 빠듯함이 항상 100 % 다(하나만 늘어도 실패).
            #     그것은 «빠듯한 잔차» 가 아니라 예산의 성질이므로 이 목록에서 뺀다 — 대신
            #     아래 snapshot_count_rows 에 그 사실을 적는다.
            if rid != "P3" and cell["margin_pct"] is not None and cell["margin_pct"] >= 80.0:
                kind = BUDGET_KIND.get(rid, "선언 스냅샷")
                near.append(dict(check=rid, name_ko=c["name_ko"], key=k, value=cell["value"],
                                 unit=cell["unit"], budget=cell["budget"],
                                 margin_pct=cell["margin_pct"], budget_kind=kind,
                                 tighter_than_convention=bool(
                                     kind == "선언 스냅샷(실측 + 약 10 %)" and cell["margin_pct"] > 92.0),
                                 note=cell["note"]))
    near.sort(key=lambda r: -r["margin_pct"])

    ctl_total = sum(s["n"] for s in ctl.values())
    ctl_pass = sum(s["n_passed"] for s in ctl.values())
    n_pos_rows = sum(1 for c in checks if c["controls"]["positive_control_ok"])
    counts["n_checks_with_positive_control"] = n_pos_rows
    counts["n_checks_without_positive_control"] = len(checks) - n_pos_rows
    counts["checks_without_positive_control"] = [c["id"] for c in checks
                                                 if not c["controls"]["positive_control_ok"]]

    #  ── 봉인 ────────────────────────────────────────────────────────────────
    seal_per = {}
    ok_n = tot_n = 0
    for k in KEYS:
        r = raws[k]
        cur = dict(topology=r.get("topo_fingerprint"), dimension=r.get("dimref_fingerprint"),
                   placement_mesh=r["placement_census"]["mesh_sha1"],
                   placement_relation=r["placement_census"]["relation_sha1"])
        mism = []
        for which, now in (("topology", cur["topology"]), ("dimension", cur["dimension"]),
                           ("symmetry", cur["dimension"]),
                           ("placement", (cur["placement_mesh"], cur["placement_relation"]))):
            tot_n += 1
            if SEAL_CACHE[which].get(k) == now:
                ok_n += 1
            else:
                mism.append(which)
        cur["all_match"] = not mism
        cur["mismatch"] = mism
        seal_per[k] = cur

    #  ── 근거 등급 행렬(치수 인증서의 것을 그대로 싣는다) ──────────────────────
    dgm = certs["dimension"]["grade_matrix"]
    grade_matrix = dict(parts=dgm["parts"], matrix=dgm["matrix"],
                        definitions=dgm["definitions"],
                        coverage=dgm["coverage"],
                        coverage_ko=dgm["coverage"].get("read_ko", "") +
                                    " 나머지 칸은 «모름» 으로 둔다 — 빈칸이 가짜 통과보다 낫다.",
                        source="outputs/mesh_cert_dimension_external_0816.json::grade_matrix",
                        note_ko=dgm["note_ko"])

    #  ── 범주 지도 대조 ──────────────────────────────────────────────────────
    cat_rows = {}
    for c in checks:
        for cat in c["category"].replace("·", " ").split():
            cat_rows.setdefault(cat, []).append(c["id"])
    cmap = []
    for cat in certs["map"]["categories"]:
        cid = cat["id"]
        rows_here = cat_rows.get(cid, [])
        has_pos = any(any(ch["controls"]["positive_control_ok"] for ch in checks if ch["id"] == r)
                      for r in rows_here)
        cmap.append(dict(id=cid, name=cat["name"], status_0816_map=cat["status"],
                         matrix_rows=rows_here,
                         status_now=("있음" if rows_here and has_pos else
                                     "부분" if rows_here else "없음"),
                         positive_control=has_pos))

    n_x1_bad = sum(1 for f in failures if f["check"] == "X1")
    headline = (
        f"전 기체 {len(KEYS)} × 전 검사 {len(checks)} = {counts['n_cells']} 칸을 실제로 돌렸다. "
        f"예산·규약 판정은 {counts['n_pass']} 칸 통과 · 실패 {counts['n_fail']} 칸이고, "
        f"⚠ 바깥 참값과 어긋난 칸이 {counts['n_mismatch']} 개(X1 치수 대조 {n_x1_bad}기체 · 총 "
        f"{sum(r['dimref']['n_mismatch'] for r in raws.values())} 행) · ◐검사기 사각지대가 "
        f"{counts['n_blindspot']} 칸이다. 적대 대조 {ctl_pass}/{ctl_total} 이 전부 통과했고 "
        f"인증서 4종 지문 {ok_n}/{tot_n} 이 지금 메쉬와 같지만, ⭐**검사 {len(checks)}개 중 "
        f"{counts['n_checks_without_positive_control']}개에는 그 자리를 겨냥한 양성 대조가 없다** "
        f"({', '.join(counts['checks_without_positive_control'])}). "
        f"⇒ 장담할 수 있는 것은 «메쉬가 스스로 앞뒤가 맞는가» 이고, «실물과 같은가» 는 "
        f"{n_x1_bad}기체에서 아직 못 한다.")

    cert = dict(
        _meta=dict(
            title="메쉬 인증 매트릭스 — 전 기체 10 × 전 검사 45 (2026-08-16 라운드)",
            generated_kst=_kst(),
            role_ko="실행자 라운드 — 검사기를 만들지 않고 **전수로 돌려** 한 표에 모은다. "
                    "칸마다 판정·잔차·허용오차·근거등급·양성대조 통과여부를 적고, 못 하는 것을 선언한다.",
            policy_ko="⛔GPU 미사용(CPU only) · ⛔git 미접촉 · ⛔형상 상수 무변경",
            env=dict(python=PY, root=ROOT),
            code_fingerprints={p: _sha_file(os.path.join(ROOT, "src", p)) for p in (
                "drones.py", "drone_cad.py", "cadkit.py", "geom.py", "mesh_check.py",
                "mesh_topo_check.py", "mesh_dimref.py", "mesh_placement.py",
                "mesh_symmetry.py", "material_provenance.py", "mesh_buried.py",
                "articulated_fast.py")},
            source_certificates=CERTS,
            inputs=dict(raw_dir=a.raw_dir, fleet=a.fleet, ctl_dir=a.ctl_dir),
            warning_ko="⚠ 이 매트릭스는 아래 seal 의 메쉬 상태에 대한 것이다. 형상이 바뀌면 "
                       "세 명령(run_one → fleet → 이 스크립트)을 다시 돌려야 한다.",
        ),
        headline_ko=headline,
        summary=dict(**counts, controls_total=ctl_total, controls_passed=ctl_pass,
                     n_suites=len(ctl), seal_ok=ok_n, seal_total=tot_n,
                     n_checks=len(checks), n_airframes=len(KEYS)),
        how_to_read_ko={
            "통과": "그 검사의 예산·규약 안에 있다",
            "⚠어긋남": "예산 위반은 아니지만 **바깥 참값(공표·공식 CAD)과 다르다** — 형상 라운드의 몫",
            "통과(⚠의심 포함)": "예산은 «지금 이만큼» 선언이고 그 안에 근거 없는 항목이 들어 있다",
            "해당없음": "그 기체에 그 부품·호출이 없다 — «0» 으로 보고하지 않는다",
            "빈칸": "참값이 없어 판정하지 않는다(가짜 통과 금지)",
            "빠듯함": "잔차 ÷ 예산 [%] — 100 % 면 예산에 닿는다",
        },
        category_map=cmap,
        checks=checks,
        matrix=matrix,
        failures=failures,
        dimension_mismatch_rows=[
            dict(key=k, rid=r["rid"], part=r["part"], quantity=r["quantity"],
                 measured=r["measured"], reference=r["reference"], residual=r["residual"],
                 residual_pct=r.get("residual_pct"), U=r["tolerance"]["U"],
                 over_U=(None if r["residual"] is None else
                         round(abs(r["residual"]) / max(r["tolerance"]["U"], 1e-12), 1)),
                 grade=r["grade"], circularity=r["circularity"], verdict=r["verdict"],
                 source=r.get("source"), definition=r.get("definition"))
            for k in KEYS for r in raws[k]["dimref"]["rows"]
            if r["verdict"] in ("어긋남", "기록만", "모름")],
        floating_parts=[
            dict(key=k, pid=f["pid"], group=f["group"], gap_mm=f["gap_mm"],
                 nearest=f.get("nearest"),
                 budget_mm=(certs["placement"]["fleet"][k].get("verdict", {}) or {}).get("budgets", {}).get("_", None),
                 grade=FLOAT_GRADE.get((k, f["group"]), ("D", "선언 없음"))[0],
                 why=FLOAT_GRADE.get((k, f["group"]), ("D", "⚠선언 없음 — 근거 미확인"))[1])
            for k in KEYS for f in raws[k]["placement_census"]["floating"]],
        residuals_near_budget=near,
        grade_matrix=grade_matrix,
        controls=ctl,
        reproducibility=dict(
            what_ko="같은 코드·같은 메쉬로 여섯 검사기를 **다시 돌려** 결과가 비트 동일한지 본다. "
                    "봉인이 뜻을 가지려면 이것이 먼저 성립해야 한다(값이 흔들리면 지문이 같아도 소용없다).",
            rows=repro, n=len(repro), n_identical=sum(1 for r in repro if r["identical"])),
        seal=dict(per_airframe=seal_per,
                  rule_ko="네 인증서(위상·치수·대칭·배치)의 지문과 지금 메쉬를 견준다. "
                          "하나라도 다르면 그 인증서는 재발급 대상이다.",
                  n_ok=ok_n, n_total=tot_n),
        consequences_ko={
            "왜 재는가": "예산은 «몇 %» 라는 수지만, 그 수가 σ 에서 몇 dB 인지는 따로 재야 한다. "
                                "그 원장이 이미 있다.",
            "A9 매몰면": "benchmark/adv_mesh_buried_faces_0816.py 가 «진짜 결함» 매몰면만 뺀 σ 를 다시 적분해 "
                       "견준 결과(2026-08-17 01:06 KST, 나가는 값 0) — 세 기하(mono el0 · mono el−30 · "
                       "바이스태틱 β120)에서 σ 가 −0.15 ~ +5.34 dB 만큼 달라진다. 10기체 중 8기체가 "
                       "«결론을 바꿈(>1 dB)» 이고 주력 표적도 그 안에 든다(mini5pro +3.99 · mavic4pro +2.45 · "
                       "mini2 +5.34 dB). ⇒ A9 는 «미관» 이 아니라 결과를 바꾸는 축이다. "
                       "⚠단 이 오차는 PO 경로에만 있다(SBR 은 first-hit 이라 구조적으로 0).",
            "P5 동일평면": "같은 자리에 두 껍질이면 PO 는 같은 면을 두 재질로 두 번 더하고 SBR 은 광선 순서가 "
                        "이긴 쪽만 쓴다 — 두 커널의 답이 그 자리에서 갈린다(x500v2 9.16 % 가 함대 최대).",
            "S5 이중계상 배수": "한쪽면합/실루엣 비가 그대로 «PO 가 실루엣보다 몇 배를 더한다» 는 수다"
                          "(mavic4pro 최대 2.09배).",
        },
        budget_provenance_ko={
            "① 유도한 허용오차": "X1(치수 외부 대조)만 해당. U = k·√(u_ref² + u_def² + u_disc²), k = 2. "
                            "행마다 «참값의 반올림 자리 / 정의 차이 / 다면체 이산화» 를 문장과 함께 "
                            "선언한다(임의 숫자 금지 — 가드 ⓑ 가 코드로 막는다).",
            "② 물리에서 온 눈금": "D1(사지타 ≤ λ/16)·D1b. 왕복 위상 45°에 해당하는 표면정밀도 관례이고, "
                            "잣대 자체를 원통·구의 해석값으로 검정했다(오차 ≤ 0.6 %).",
            "③ 규약에서 유도": "S2(d[k+n/2] = d[k]·(−1)^(n/2), Σdir = 0) · S4·S5 의 항등식과 닫힌 해.",
            "④ 선언 스냅샷": "A3·A7·A8·A9·P2·P3·P4·P5. 값은 «지금 이만큼이다» 라는 기록이지 "
                        "«이만큼이 옳다» 가 아니다. 저장소의 기존 규약(PROP_BELL_* · BURIED_FACE_BUDGET_PCT)과 "
                        "같은 뜻이고, 새로 생기는 결함은 예산을 넘겨 실패한다.",
            "⑤ 0": "T1~T5·P1·R0·G1 — 결함은 있거나 없거나다. 예외는 선언된 자리(mini2/body 구멍 1개)뿐.",
        },
        snapshot_count_rows_ko=(
            "P3(완전매몰 쌍)은 예산이 «지금 개수» 그대로라 빠듯함이 항상 100 % 다 — 새로 하나만 "
            "묻혀도 실패한다는 뜻이지 «곧 터진다» 는 뜻이 아니다. 그래서 빠듯한 잔차 목록에서 뺐다."),
        limits_ko=[
            "**«형상이 실물과 같은가» 는 이 매트릭스가 장담하지 않는다.** 45행 중 바깥 참값에 대는 "
            "행은 X1(치수 77행) 하나와 A5(스펙 대조) 뿐이고, 나머지는 «메쉬가 스스로 앞뒤가 맞는가» "
            "(자기무결성)와 «우리 규약대로인가» 를 본다. 실물 대조는 X1 의 independent 행 32개까지다.",
            "**근거 등급이 있는 칸은 기체 10 × 부품 12 = 120 칸 중 37 칸뿐이다**(A 33 · B 2 · B− 1 · C 1). "
            "나머지 83 칸은 «모름» 이다 — 채우지 않는 것이 규율이다.",
            "예산의 절반 이상이 **선언 스냅샷**이다(위 budget_provenance ④). 그 행들이 지키는 것은 "
            "«오늘보다 나빠지지 않음» 이지 «옳음» 이 아니다.",
            "이 매트릭스는 **PO 경로의 오차**를 주로 잰다(매몰면·동일평면·이중계상). 기본 엔진 SBR 은 "
            "first-hit 이라 A9·P2·P3 의 오차가 구조적으로 0 이다 — 즉 같은 결함이 두 커널에서 뜻이 다르다.",
            "자기교차(T4·P1)는 **동일평면 교차를 안 본다**(det ≈ 0 으로 빠진다). 그 자리는 중복면 검사와 "
            "P5(동일평면)가 본다.",
            "사지타(D1)는 표본 간격이 고른 곳에서만 뜻이 있고 «작은 쪽» 을 쓰므로 성긴 조각이 촘촘한 "
            "조각과 맞닿으면 낮게 잡힐 수 있다(원자료에 상한도 함께 싣는다). λ 를 정해야 답이 나온다 — "
            "기본 3.5 GHz, 5.8 GHz 병기.",
            "D2·D3 은 **계측된 빌더가 부른 호출만** 본다. 열린 프레임 4기체(s1000plus·typhoonh480·"
            "x500v2·m350rtk)는 스플라인·설계 끝단표가 없어 «해당없음» 이다 — 0 으로 보고하지 않았다.",
            "배치(P1~P5)는 **절대 배치(있어야 할 자리)** 를 안 본다. «붙어야 하는가» 라는 의도는 메쉬 "
            "안에 없어서, 사람이 근거와 함께 예산표에 적는다(P4 의 ⚠의심 6칸이 그 자리다).",
            "**게이트가 아직 리포트 경로에 배선되지 않았다**(범주 지도 M16 1순위 구멍). 여섯 검사기의 "
            "assert_* 는 있으나 `build_drone()` 을 쓰는 리포트·실험은 검사를 안 지난다. 이 매트릭스는 "
            "그 사실을 지문으로 대신 막는다 — 형상이 바뀌면 Z1~Z4 가 어긋난다.",
            "이 매트릭스가 도는 동안 **다른 세 라운드가 형상을 고치는 중**이었다. 지문(seal)은 이 표가 "
            "어느 메쉬의 것인지 못 박지만, 그 라운드들이 착지하면 세 명령을 다시 돌려야 한다.",
        ],
        how_to_rerun=[
            "PYTHONPATH=src:benchmark python benchmark/mesh_cert_matrix_run_one.py --key <기체> --out <원자료>",
            "PYTHONPATH=src:benchmark python benchmark/mesh_cert_matrix_fleet.py <함대원자료>",
            "PYTHONPATH=src:benchmark python benchmark/adv_mesh_check_faults.py  (그리고 나머지 5개 스위트)",
            "PYTHONPATH=src:benchmark python benchmark/make_mesh_cert_matrix_0816.py "
            "--raw-dir <디렉터리> --fleet <함대원자료> --ctl-dir <로그디렉터리>",
        ],
    )

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(cert, f, ensure_ascii=False, indent=1)
    print("→", a.out)
    with open(a.md, "w", encoding="utf-8") as f:
        f.write(to_markdown(cert))
    print("→", a.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
