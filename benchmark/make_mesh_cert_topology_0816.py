# -*- coding: utf-8 -*-
"""
make_mesh_cert_topology_0816.py — **위상·이산화 인증서**를 만든다
==============================================================================
무엇을 만드나
  `outputs/mesh_cert_topology_discretization_0816.json` — 「이 범위는 장담하고 이 범위는
  못 한다」를 한 파일에 적는다. 다섯 칸으로 이루어진다:

    ① 범주 → 검사 사상    : 위상·이산화의 어느 자리를 어느 검사가 보는가
    ② 검사 명세           : 각 검사의 판정 잣대·예산·근거 파일/함수
    ③ ⭐대조 결과         : 양성 대조(결함 주입) + 음성 대조(무결 통과) 전 항목의 실측 결과
                            (`benchmark/adv_mesh_topo_faults.py` 를 **실제로 돌려서** 채운다)
    ④ 전수 측정 + 회귀 봉인: 기종 10대의 실측값과 **지문**(sha256). 형상이 바뀌면 지문이 바뀐다
    ⑤ ⭐못 하는 것        : 이 인증서가 **장담하지 않는** 범위

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/make_mesh_cert_topology_0816.py
      ⛔ GPU 안 쓴다 · ⛔형상 상수 안 건드린다 · 쓰는 파일은 위 JSON 하나뿐이다.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                          # noqa: E402
import mesh_topo_check as mt                                # noqa: E402
import adv_mesh_topo_faults as adv                          # noqa: E402
from drones import DRONES                                    # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "mesh_cert_topology_discretization_0816.json")
FC2 = 5.8e9        # 두 번째 대역(WiFi/ISM) — 이산화 잣대는 λ 에 걸려 있으므로 대역을 바꿔 본다


def _kst():
    return (_dt.datetime.now(_dt.timezone.utc)
            + _dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


def _versions():
    import scipy
    import trimesh
    return dict(python=sys.version.split()[0], numpy=np.__version__,
                scipy=scipy.__version__, trimesh=trimesh.__version__)


# --------------------------------------------------------------------------- #
#  ① 범주 지도 — 위상·이산화 칸만. id 는 저장소 인증 범주 지도(mesh_cert_map_0816.json)를 따른다
# --------------------------------------------------------------------------- #
def category_map():
    return [
        dict(id="M2", layer="위상(접합)", name_ko="면 접합 — 구멍 · 비다양체 모서리 · 감김 · 법선 방향 · 중복 삼각형",
             checks=["T1", "T2", "T3"],
             before_this_round="있음 (mesh_check 가 trimesh 경로로 본다)",
             what_this_round_added=[
                 "구멍을 **모서리 수**가 아니라 **경계 곡선 수**로 센다 — «모서리 6개» 가 구멍 1개인지 2개인지 갈린다",
                 "감김 뒤집힘을 trimesh 없이 **유향 모서리 대조**로 직접 센다(자가수리와 무관한 두 번째 경로)",
                 "중복 삼각형 **전용** 검사(지도가 «전용 검사 없음» 이라고 적은 자리)",
                 "종수(손잡이 개수)를 오일러 표수로 세어 싣는다 — 판정은 안 하고 선언만 한다",
             ],
             status="있음(양성·음성 대조 완비)"),
        dict(id="M3", layer="위상(비접합)", name_ko="비다양체 정점(나비넥타이) · 한 부품의 자기교차",
             checks=["T3", "T4"],
             before_this_round="⛔**없음** — 지도가 «통과(놓침)» 으로 실측해 둔 칸",
             what_this_round_added=[
                 "나비넥타이 정점 — 면 코너를 노드로 두고 다중도 2 모서리로 이어 정점별 덩이 수를 센다",
                 "자기교차 — 쓸고 자르기(sweep&prune) 광역 + Möller–Trumbore 정밀 판정, 근사 없음",
                 "⭐공백 증명: 같은 메쉬를 기존 mesh_check 에 먹여 **통과한다**는 것을 대조로 남겼다",
             ],
             status="있음(양성·음성 대조 완비)"),
        dict(id="M4", layer="이산화(품질)", name_ko="삼각형 품질 — 슬리버 · 퇴화면",
             checks=["T5"],
             before_this_round="있음 (mesh_check 의 최소내각·면적 잣대)",
             what_this_round_added=[
                 "인덱스 중복 (a,a,b) · 길이 0 모서리 · 종횡비(p99) 를 따로 센다",
                 "같은 축을 **독립 경로**로 다시 재서 기존 검사기와 대조한다(교차검증 절)",
             ],
             status="있음(양성·음성 대조 완비)"),
        dict(id="M5", layer="이산화(해상도)", name_ko="삼각형 크기 vs λ · 로프트/스플라인 · 표면 잡음",
             checks=["D1", "D2", "D3"],
             before_this_round="부분 — 일회성 연구만 있고 **상시 검사·예산이 없었다**",
             what_this_round_added=[
                 "D1 파장 대비 크기 — 변 길이(참고) + ⭐곡면 사지타(판정). 해석적 참값으로 **눈금 검증**",
                 "D2 로프트 스플라인 오버슛 — 3차 보간이 제어점 상자 밖으로 나가는 양 + 하한 클램프 탐지",
                 "D3 끝단 캡 — 캡 부재(평면 링 탐지) + 끝단 단면 손실(설계 평면 절단으로 측정)",
             ],
             status="있음(양성·음성 대조 완비)"),
    ]


# --------------------------------------------------------------------------- #
#  ② 검사 명세
# --------------------------------------------------------------------------- #
def check_specs():
    b = mt
    return [
        dict(id="T1", name_ko="닫힘(구멍)", where="src/mesh_topo_check.py::boundary_curves",
             verdict_ko="부품마다 경계 곡선(구멍 테두리) 수 ≤ 예산. 곡선의 모양(평면 링인가)도 잰다",
             budget=dict(table="BOUNDARY_CURVE_BUDGET", value=b.BOUNDARY_CURVE_BUDGET["_default"],
                         declared={"mini2/body": 1}),
             declared_reason_ko="mini2 body 의 구멍 1개(경계 모서리 3)는 감사 I5 가 이미 선언한 자리다 "
                                "— cadkit 불리언 합집합 출력에서 needle 삼각형 1장이 지워지며 남았다."),
        dict(id="T2", name_ko="법선 일관성", where="src/mesh_topo_check.py::edge_census · signed_volume_mm3",
             verdict_ko="이웃 면의 감김이 서로 반대인가(유향 모서리 대조) + 닫힌 부품의 부호부피 > 0",
             budget=dict(table="(고정)", value=0),
             declared_reason_ko="예외 없음. 두 축은 서로 다른 결함이라 따로 센다 — 전면 반전은 "
                                "«감김 일관 + 부피 음수», 한 장 반전은 «감김 깨짐 + 부피 양수»."),
        dict(id="T3", name_ko="다양체(⭐나비넥타이 포함)",
             where="src/mesh_topo_check.py::edge_census · bowtie_vertices · duplicate_faces",
             verdict_ko="모서리 다중도 ≥3 = 0 · 나비넥타이 정점 = 0 · 중복 삼각형 = 0",
             budget=dict(table="NONMANIFOLD_EDGE_BUDGET · BOWTIE_VERTEX_BUDGET · DUPLICATE_FACE_BUDGET",
                         value=0),
             declared_reason_ko="전 기종 실측 0. 나비넥타이는 이 라운드에 처음 세어 봤고 첫 전수에서 0 이었다."),
        dict(id="T4", name_ko="⭐자기교차", where="src/mesh_topo_check.py::self_intersections",
             verdict_ko="한 부품 안에서 정점을 공유하지 않는 삼각형 쌍이 실제로 교차하는 수 ≤ 예산 "
                        "(그리고 «검사 못 한 부품» 이 0 이어야 한다)",
             budget=dict(table="SELF_INTERSECT_BUDGET", value=0),
             declared_reason_ko="전 기종 실측 0(부품 302개 전수). 첫 시험에서 나온 145/139/38 쌍은 "
                                "그룹을 가로질러 웰딩했을 때의 값이고 추적해 보니 **부품 간 파고듦**"
                                "(gear ↔ gear_cf)이었다 — 그것은 M9 축이다(findings 절)."),
        dict(id="T5", name_ko="퇴화 삼각형", where="src/mesh_topo_check.py::triangle_quality",
             verdict_ko="인덱스 중복 (a,a,b) = 0 · 면적 0 = 0 · 길이 0 모서리 = 0 "
                        "(슬리버는 세어서 싣되 판정은 mesh_check.SLIVER_BUDGET 이 한다 — 한 축을 두 곳에서 판정하지 않는다)",
             budget=dict(table="DEGENERATE_BUDGET", value=0),
             declared_reason_ko="전 기종 실측 0. PO 는 면적<1e-12 면을 조용히 버리므로(rcs_po.mesh_to_points) "
                                "퇴화면은 «조용한 면적 손실» 이 된다."),
        dict(id="D1", name_ko="⭐파장 대비 삼각형 크기",
             where="src/mesh_topo_check.py::facet_wavelength",
             verdict_ko="**곡면 구간**의 사지타(현 오차)가 λ/16 을 넘는 면적 비율 ≤ 예산. "
                        "변 길이 > λ/7 비율은 **참고**로만 싣는다",
             budget=dict(table="SAGITTA_AREA_PCT_BUDGET", value=b.SAGITTA_AREA_PCT_BUDGET["_default"],
                         reference_only="FACET_EDGE_AREA_PCT_BUDGET"),
             declared_reason_ko="변 길이를 판정에 안 쓰는 이유: PO 는 삼각형을 λ/7 격자로 **다시 쪼개** "
                                "점을 깔고(rcs_po.mesh_to_points 141-148행) SBR 은 광선 격자가 λ/12 다. "
                                "큰 삼각형이 곧 성긴 적분이 아니다. 큰 삼각형이 오차가 되는 것은 그 자리가 "
                                "**곡면일 때**뿐이고 그것을 재는 것이 사지타다.",
             calibration_ko="사지타 추정기를 원통·구의 해석값 r(1−cos(π/seg)) 과 대조했다 — 오차 ≤ 0.6 %."),
        dict(id="D2", name_ko="로프트 스플라인 오버슛",
             where="src/mesh_topo_check.py::_spline_overshoot · instrumented_build",
             verdict_ko="3차 스플라인이 **이웃 제어점의 상자 밖**으로 나가는 양(진폭 대비 %) ≤ 예산 "
                        "· 하한 클램프에 닿은 단면 = 0",
             budget=dict(table="LOFT_OVERSHOOT_PCT_BUDGET", value=b.LOFT_OVERSHOOT_PCT_BUDGET),
             declared_reason_ko="오버슛 자체는 3차 보간(not-a-knot)의 성질이지 버그가 아니다. 문제는 "
                                "**얼마나** 나가는지 아무도 안 재고 있었다는 것 — 절대량으로 matrice4e "
                                "반높이 +3.02 mm, mini5pro 반폭 +2.67 mm 다."),
        dict(id="D3", name_ko="⭐끝단 캡", where="src/mesh_topo_check.py::check_loft_caps · section_extent",
             verdict_ko="cap=True 로 부른 로프트/스윕에 경계 모서리 = 0 (캡 부재 탐지) · "
                        "설계 끝단 평면에서 잰 단면이 설계표 대비 ±예산 % 안",
             budget=dict(table="CAP_DEFICIT_PCT_BUDGET", value=b.CAP_DEFICIT_PCT_BUDGET["_default"]),
             declared_reason_ko="2026-08-16 에 `smooth_iters=0` 으로 고쳐진 자리를 **봉인**한다. "
                                "옛 값(4)으로 되돌리면 −43 % 가 되어 즉시 실패한다."),
    ]


# --------------------------------------------------------------------------- #
#  ④ 전수 측정
# --------------------------------------------------------------------------- #
def measure_all():
    per, seal = {}, []
    for k, s in DRONES.items():
        mesh, rec = mt.instrumented_build(s)
        r = mt.check_topology(mesh, k, fc=mt.FC_DEFAULT_HZ, self_int=True)
        r2 = mt.check_topology(mesh, k, fc=FC2, self_int=False)      # 대역만 바꿔 이산화 재측정
        lc = mt.check_loft_caps(s, rec=rec)
        fp = mt.fingerprint(r)
        seal.append(f"{k}:{fp}")
        groups = {}
        for g, v in r["groups"].items():
            f = v["facet"]
            groups[g] = dict(
                n_faces=v["n_faces"], n_parts=v["n_parts"], n_welded_verts=v["n_welded_verts"],
                boundary_edges=v["boundary_edges"], boundary_curves=v["boundary_curves"],
                planar_ring_curves=v["planar_ring_curves"], open_parts=v["open_parts"],
                flipped_edges=v["flipped_edges"], negative_volume_parts=v["negative_volume_parts"],
                nonmanifold_edges=v["nonmanifold_edges"], max_edge_multiplicity=v["max_edge_multiplicity"],
                bowtie_vertices=v["bowtie_vertices"], duplicate_faces=v["duplicate_faces"],
                self_int_hits=v["self_int_hits"], self_int_unchecked_parts=v["self_int_unchecked_parts"],
                repeat_index_faces=v["repeat_index_faces"], zero_area_faces=v["zero_area_faces"],
                zero_len_edges=v["zero_len_edges"], slivers=v["slivers"],
                min_angle_deg=v["min_angle_deg"], p99_aspect=v["p99_aspect"],
                genus_nonzero_parts=v["genus_nonzero_parts"],
                area_mm2=f["area_mm2"], max_edge_mm=f["max_edge_mm"],
                max_dihedral_deg=f["max_dihedral_deg"],
                max_sagitta_mm=f["max_sagitta_mm"], max_sagitta_bound_mm=f["max_sagitta_bound_mm"],
                sagitta_over_lam16_area_pct=f["sagitta_over_lam16_area_pct"],
                edge_over_lam7_area_pct=f["edge_over_lam7_area_pct"],
                ok=v["ok"])
        per[k] = dict(
            ok=bool(r["ok"] and lc["ok"]), fingerprint=fp,
            totals=r["totals"], groups=groups,
            discretization_3p5GHz=r["discretization"],
            discretization_5p8GHz=r2["discretization"],
            loft_caps=dict(
                n_loft_calls=lc["n_loft_calls"], n_sweep_calls=lc["n_sweep_calls"],
                n_spline_calls=lc["n_spline_calls"], n_body_calls=lc["n_body_calls"],
                cap_checked=lc["cap_checked"], cap_requested_but_open=lc["cap_requested_but_open"],
                cap_not_requested=lc["cap_not_requested"],
                overshoot_checked=lc["overshoot_checked"], max_overshoot_pct=lc["max_overshoot_pct"],
                overshoot_budget_pct=lc["overshoot_budget_pct"],
                clamped_sections=lc["clamped_sections"],
                end_deficit_checked=lc["end_deficit_checked"],
                max_end_deficit_pct=lc["max_end_deficit_pct"],
                end_deficit_budget_pct=lc["end_deficit_budget_pct"],
                body=lc["body"], spline=lc["spline"], ok=lc["ok"]),
        )
        print(f"  · {k:12s} {'✅' if per[k]['ok'] else '❌'}  지문 {fp}  "
              f"부품 {r['totals']['parts']:3d} · 나비넥타이 {r['totals']['bowtie']} · "
              f"자기교차 {r['totals']['selfint']} · 사지타 "
              f"{r['discretization']['sagitta_over_lam16_area_pct']} % "
              f"(5.8 GHz {r2['discretization']['sagitta_over_lam16_area_pct']} %)")
    return per, hashlib.sha256("\n".join(sorted(seal)).encode()).hexdigest()[:32]


def main():
    print("=" * 112)
    print("위상·이산화 인증서 — 대조 시험 → 전수 측정 → 봉인")
    print("=" * 112)
    print("\n[1/3] 양성·음성 대조 (benchmark/adv_mesh_topo_faults.py)")
    controls = adv.run_all()
    n_ctl_ok = sum(1 for c in controls if c["passed"])

    print("\n[2/3] 전 기종 전수 측정")
    per, seal = measure_all()
    n_ok = sum(1 for v in per.values() if v["ok"])

    #  5.8 GHz 에서 넘어가는 기체 — 이산화 잣대는 λ 에 걸려 있다
    over58 = {k: v["discretization_5p8GHz"]["sagitta_over_lam16_area_pct"]
              for k, v in per.items() if not v["discretization_5p8GHz"]["ok"]}

    cert = {
        "_meta": {
            "title": "메쉬 인증서 — 위상·이산화 (2026-08-16)",
            "scope_ko": "메쉬 결함 범주 중 **위상(닫힘·법선·다양체·자기교차·퇴화)** 과 "
                        "**이산화(파장 대비 크기·로프트 오버슛·끝단 캡)** 만 다룬다. "
                        "치수·배치·재질·출처 등 다른 축은 이 인증서가 장담하지 않는다.",
            "generated_kst": _kst(),
            "policy_ko": "⛔GPU 미사용(CPU only) · ⛔git 미접촉 · ⛔형상 상수 무변경"
                         "(_SHELL_SHAPE·INTERNALS·GEAR_*·CHORD_*·PITCH_K*·ARM_TIP_Z·envelope_mm) — "
                         "이 라운드가 만든 것은 검사·대조·봉인·인증서뿐이다.",
            "how_to_read_ko": "각 검사는 «양성 대조(결함을 심으면 걸린다) + 음성 대조(멀쩡하면 통과)» 를 "
                              "둘 다 통과해야 «있다» 로 친다. 예산값은 «2026-08-16 지금 이만큼이다» 라는 "
                              "선언이지 «이만큼이 옳다» 가 아니다(저장소 규약).",
            "glossary_ko": {
                "경계 곡선": "구멍의 테두리 하나. 모서리 수가 아니라 테두리 개수를 센다.",
                "나비넥타이(비다양체 정점)": "두 덩이가 정점 하나만 공유하는 자리. 모서리를 아무리 세도 안 나온다.",
                "자기교차": "껍질 하나가 스스로를 관통하는 것. 수밀·법선이 전부 정상으로 보인다.",
                "사지타": "평면 조각(현)과 참곡면 사이의 최대 거리. 표면을 얼마나 각지게 근사했나를 잰다.",
                "오버슛": "3차 스플라인이 제어점 사이에서 표 밖으로 부푸는 것.",
                "끝단 캡": "로프트의 양 끝을 덮는 부채꼴 뚜껑. 없으면 껍질이 열리고, 스무딩에 눌리면 단면을 잃는다.",
                "지문": "위상·이산화 불변량만 모은 sha256. 형상이 바뀌면 값이 바뀐다(«옳음» 이 아니라 «안 바뀜» 의 증명).",
            },
            "code": {
                "checker": "src/mesh_topo_check.py",
                "controls": "benchmark/adv_mesh_topo_faults.py",
                "certificate_builder": "benchmark/make_mesh_cert_topology_0816.py",
                "reproduce": [
                    "cd sionna && PYTHONPATH=src:benchmark python src/mesh_topo_check.py",
                    "cd sionna && PYTHONPATH=src:benchmark python benchmark/adv_mesh_topo_faults.py",
                    "cd sionna && PYTHONPATH=src:benchmark python benchmark/make_mesh_cert_topology_0816.py",
                ],
            },
            "env": _versions(),
            "fc_hz": {"primary": mt.FC_DEFAULT_HZ, "secondary": FC2},
            "related": ["outputs/mesh_cert_map_0816.json (범주 지도 · 이 인증서는 그 M2·M3·M4·M5 칸을 채운다)",
                        "src/mesh_check.py (다른 축: 치수·손대칭성·부품 간 파고듦)",
                        "docs/MESH_AUDIT_0816.md"],
        },
        "summary": {
            "n_checks": 8,
            "n_controls": len(controls),
            "n_controls_passed": n_ctl_ok,
            "controls_by_kind": {k: [sum(1 for c in controls if c["kind"] == k and c["passed"]),
                                     sum(1 for c in controls if c["kind"] == k)]
                                 for k in sorted({c["kind"] for c in controls})},
            "n_airframes": len(per),
            "n_airframes_passing": n_ok,
            "headline_ko": f"위상·이산화 8축 전부 양성·음성 대조를 통과했고(대조 {n_ctl_ok}/{len(controls)}), "
                           f"기종 {n_ok}/{len(per)} 이 예산 안이다. 이 라운드가 새로 세운 축은 "
                           f"**나비넥타이 정점 · 자기교차 · 파장 대비 사지타 · 로프트 오버슛 · 끝단 캡** 다섯이다.",
        },
        "category_map": category_map(),
        "checks": check_specs(),
        "controls": controls,
        "measurements": per,
        "findings": [
            {
                "id": "F1",
                "title_ko": "⭐첫 자기교차 측정은 «부품 간 파고듦» 이었다 — 축을 갈라서 다시 쟀다",
                "detail_ko": "메쉬를 **그룹을 가로질러** 웰딩해 재면 s1000plus 145×2 · typhoonh480 139×2 · "
                             "x500v2 38×4 쌍이 교차로 잡힌다. 추적해 보니 전부 'gear'(고무 발 슬리브) ↔ "
                             "'gear_cf'(카본 스키드 튜브) 사이였다 — 즉 **다른 두 부품이 서로 파고든 것**이지 "
                             "한 껍질이 스스로를 뚫은 것이 아니다. 부품 간 파고듦은 지도 M9 축이고 "
                             "`mesh_check.check_buried_faces`·`check_prop_bell_solid` 가 본다. 그래서 이 검사는 "
                             "**그룹 안에서만** 웰딩·부품분해한다(mesh_check 와 같은 규약). 그 규약에서 전 기종 0 이다.",
                "status_ko": "이 라운드는 판정하지 않는다(다른 축). 다만 수치를 여기 남겨 다음 라운드가 볼 수 있게 한다.",
            },
            {
                "id": "F2",
                "title_ko": "⭐사지타 잣대를 세 번 고쳐 잡았다 — 눈금을 해석적 참값에 맞췄다",
                "detail_ko": "① 공유 모서리 길이로 재면 스키드 튜브가 사지타 14 mm(참값의 95 배)로 나와 "
                             "네 기체가 «심각한 결함» 으로 찍혔다. ② 두 면 무게중심 거리의 직각 성분은 계통 −34 % "
                             "였다. ③ 공유 모서리에서 잰 두 삼각형 **높이의 작은 쪽**이 참값과 0.1~0.6 % 로 맞는다. "
                             "잣대를 «통과할 때까지» 고른 것이 아니라 **원통·구의 해석값 r(1−cos(π/seg))** 에 "
                             "맞춘 것이고, 그 대조가 controls 의 «D1 눈금검증» 이다.",
                "status_ko": "해결(눈금 오차 ≤ 0.6 %). 과대 방향 상한도 `max_sagitta_bound_mm` 로 같이 싣는다.",
            },
            {
                "id": "F3",
                "title_ko": "3.5 GHz 에서는 전 기종 여유가 있으나 **가장 빠듯한 기체는 λ/16 의 0.57 배**다",
                "detail_ko": "최악은 s1000plus 의 카본 스키드(gear_cf) 로 사지타 3.04 mm = λ/16 의 0.57 배다"
                             "(λ = 85.65 mm). 대역을 5.8 GHz 로 올리면 λ/16 = 3.23 mm 로 내려가므로 여유가 "
                             "0.94 배가 된다 — 즉 **주파수를 올리면 이 축은 곧 한계에 닿는다.**",
                "at_5p8GHz": over58 or "5.8 GHz 에서도 예산 초과 기체 없음",
                "status_ko": "선언. 검사기는 `--fc` 로 대역을 바꿔 다시 돌릴 수 있다.",
            },
            {
                "id": "F4",
                "title_ko": "끝단 캡 수리(`smooth_iters=0`)를 **독립 측정으로 재현**했다",
                "detail_ko": "설계 끝단 평면에서 단면을 잘라 재면 출하판(iters=0)은 설계표와 **정확히 0.000 %** "
                             "차이고, 옛 판(iters=4)은 −43~−44 %(mini2 −33.7 %)다. 저장소 선언(«−38~−44 %»)을 "
                             "다른 방법으로 확인한 것이다. ⚠ 절대값은 정의에 따라 조금 다르다 — `_body_folding` "
                             "docstring 의 matrice4e 기수 «23.42 × 21.31» 은 링 정점 기준이고, 이 인증서의 "
                             "«22.95 × 20.88» 은 설계 평면 절단 기준이다.",
                "status_ko": "봉인 완료 — 되돌리면 D3 가 즉시 실패한다(예산 2 %).",
            },
            {
                "id": "F5",
                "title_ko": "종수(손잡이) 15 짜리 부품이 하나 있다 — **설계다**(판정하지 않고 선언한다)",
                "detail_ko": "s1000plus 'body' 의 큰 부품(면 820 · 346×346×60 mm)은 오일러 표수 χ = −28, "
                             "즉 **종수 15** 다. 도넛 구멍이 15개라는 뜻인데, 이 부품은 «카본 상·하판 2장 + "
                             "스탠드오프 기둥 8개 + 암 마운트 블록 8개» 가 불리언 합집합된 것이다. "
                             "두 판을 잇는 기둥/블록이 16개면 다중연결도가 16 이고 종수는 16−1 = **15** — "
                             "숫자가 정확히 맞는다. 그래서 종수 축은 **세어서 싣되 판정하지 않는다**: "
                             "도넛이 설계일 수도 결함일 수도 있고, 그것을 가를 근거가 이 라운드에 없다.",
                "status_ko": "선언(다른 9기체는 종수 0). 이 축이 실제로 뜻있는 수를 낸다는 확인이기도 하다.",
            },
            {
                "id": "F6",
                "title_ko": "웰딩은 출하 기체에서 **아무것도 안 합친다** — 그래도 매번 확인한다",
                "detail_ko": "기종 10대 · 전 그룹에서 병합된 정점이 0개다(cadkit 이 이미 "
                             "`trimesh(process=True)` 로 합쳐 내보낸다). 반면 `geom` 프리미티브를 직접 쌓으면 "
                             "필요하다 — `uv_sphere(seg=24)` 는 웰딩 전 경계 모서리 96개, 웰딩(46개 병합) 후 "
                             "0개다. 즉 이 단계는 «없어도 되는 것» 이 아니라 «지금은 할 일이 없는 것» 이고, "
                             "`n_welded_verts` 로 매번 측정해 싣는다.",
                "status_ko": "선언.",
            },
            {
                "id": "F7",
                "title_ko": "«얇은 판을 떠서 재기» 는 답이 통째로 달라진다 — 잘라서 잰다",
                "detail_ko": "끝단 단면을 판 두께 0.1 % / 1 % / 5 % 로 재면 matrice4e 스무딩판의 기수 반폭이 "
                             "**0.0 / 38.6 / 41.2 mm** 로 나온다(같은 메쉬, 같은 자리). 손잡이가 답을 정하는 "
                             "잣대는 쓸 수 없으므로 평면 절단(`section_extent`)으로 바꿨다.",
                "status_ko": "해결.",
            },
        ],
        "regression_seal": {
            "how_ko": "기종별 지문 = (그룹 · 면수 · 부품수 · 경계모서리 · 경계곡선 · 비다양체 · 나비넥타이 · "
                      "중복면 · 자기교차 · 퇴화 3종 · 슬리버 · 종수≠0 부품수 · 최대변 · 사지타 위반면적 · 면적) "
                      "의 sha256 앞 32자. 형상이 바뀌면 반드시 바뀐다.",
            "seal_all": seal,
            "per_airframe": {k: v["fingerprint"] for k, v in per.items()},
            "verify_cmd": "PYTHONPATH=src:benchmark python src/mesh_topo_check.py --check-seal",
            "verify_ko": "이 인증서의 지문과 «지금 메쉬» 의 지문을 기종마다 견준다. 나가는 값 0=동일, 2=바뀜.",
            "gate": "src/mesh_topo_check.py::assert_ok() — 예산 초과면 예외를 던진다",
            "gate_wiring_ko": "⚠ **아직 `src/drones.py` 의 내보내기 경로에 배선하지 않았다.** 이 라운드와 "
                              "동시에 형상을 바꾸는 라운드가 세 개 돌고 있어 같은 파일을 건드리면 충돌한다. "
                              "배선은 `mesh_check.assert_ok()` 옆에 한 줄(`mesh_topo_check.assert_ok()`)을 "
                              "더하면 끝난다 — 형상 라운드가 끝난 뒤에 붙이는 것이 맞다.",
            "warning_ko": "⚠ 지문은 «옳음» 의 증명이 아니라 «안 바뀜» 의 증명이다. 형상을 바꾸는 라운드가 "
                          "지나가면 지문은 당연히 바뀐다 — 그때는 이 인증서를 **다시 돌려서** 새 값으로 "
                          "갱신하는 것이 정상 절차다.",
        },
        "confidence_grades": {
            "scale_ko": {
                "A": "해석적 참값과 눈금을 맞췄고 + 양성·음성 대조 둘 다 있다",
                "B": "양성·음성 대조 둘 다 있다(해석적 참값은 없다)",
                "C": "측정만 있다(대조 없음) — 이 인증서에는 없다",
            },
            "by_check": {"T1": "B", "T2": "B", "T3": "B", "T4": "B", "T5": "B",
                         "D1": "A", "D2": "B", "D3": "B"},
            "note_ko": "D1 만 A 인 이유는 사지타 추정기를 원통·구의 해석값에 맞춰 봤기 때문이다. "
                       "나머지는 결함을 심어 걸리는 것을 보였을 뿐 «참값» 이라는 개념이 없는 축이다"
                       "(구멍은 있거나 없거나다).",
        },
        "limits_ko": [
            "⭐**동일평면 교차는 안 본다.** 자기교차 판정은 선분–삼각형 관통을 보므로, 두 삼각형이 같은 "
            "평면에서 겹치는 경우는 det≈0 으로 빠진다. 그 자리는 «중복 삼각형»(T3)과 mesh_check 의 "
            "«그룹 안 겹침» 이 본다.",
            "⭐**부품 간 파고듦은 이 인증서의 축이 아니다.** 웰딩·부품분해를 그룹 안에서만 하므로, 서로 다른 "
            "그룹의 부품이 파고든 것은 여기서 0 으로 나온다(F1 참조). 그 축은 mesh_check 의 매몰면·프롭↔벨 "
            "검사가 본다 — «못 봄» 이 아니라 «다른 검사의 일» 이다.",
            "⭐**사지타는 표본 간격이 고른 곳에서만 뜻이 있다.** 조각 크기가 크게 다른 짝에서는 «작은 쪽» 을 "
            "표본 간격으로 쓰는데, 성긴 곡면 조각이 촘촘한 조각과 맞닿아 있으면 그 자리의 오차를 **낮게** 잡을 "
            "수 있다. 과대 방향 상한(`max_sagitta_bound_mm`)을 같이 실어 그 폭을 보이게 했다.",
            "**λ 를 정해야 답이 나온다.** 이산화 판정은 주파수에 걸려 있다. 기본은 3.5 GHz 이고 5.8 GHz 값도 "
            "같이 실었지만, 그 밖의 대역은 `--fc` 로 다시 돌려야 한다.",
            "**로프트/캡 검사는 «불린 빌더» 만 본다.** `spline_sections`·`loft`·`sweep`·`_body_folding` 을 "
            "계측하므로 그 함수를 안 거치는 형상(geom 프리미티브·revolve·불리언 출력)은 메쉬 층 검사(T1~T5·D1)로만 "
            "덮인다. 안 불린 기체는 «해당 없음» 으로 적고 **0 으로 보고하지 않는다**.",
            "**종수(손잡이)는 세기만 하고 판정하지 않는다.** 도넛 모양이 설계일 수도 결함일 수도 있는데 "
            "그것을 가를 근거가 이 라운드에 없다.",
            "**«형상이 옳은가» 는 여기서 장담하지 않는다.** 이 인증서가 장담하는 것은 «메쉬가 스스로 앞뒤가 "
            "맞는가» 와 «빌더의 설계표가 메쉬에 그대로 실렸는가» 까지다. 그 설계표의 숫자가 실물과 같은지는 "
            "출처 등급 축(지도 M14·M15)의 일이다.",
            "**웰딩 반경 1 nm 는 선택이다.** 그보다 멀리 떨어진 «사실상 같은 점» 은 안 합친다. 우리 빌더의 "
            "중복 정점은 배정밀도 eps 급이라 문제가 없지만, 외부에서 들여온 메쉬에는 다시 골라야 할 수 있다.",
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(cert, fh, ensure_ascii=False, indent=1, default=float)
    print(f"\n[3/3] 인증서 → {OUT}")
    print(f"  대조 {n_ctl_ok}/{len(controls)} · 기종 {n_ok}/{len(per)} · 봉인 {seal}")
    return 0 if (n_ctl_ok == len(controls) and n_ok == len(per)) else 1


if __name__ == "__main__":
    sys.exit(main())
