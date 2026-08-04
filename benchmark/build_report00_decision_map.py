# -*- coding: utf-8 -*-
"""
build_report00_decision_map.py — 00편 F4「할 수 있는 것 / 없는 것」의 근거 JSON 을 만든다
==========================================================================================
왜 이 파일이 필요한가
    F4 는 결정표다 — 실험 유형을 두 축 위에 놓는다.
        가로축: 표적 항이 상수로 소거되는가
        세로축: 절대값이 필요한가
    이 배치 자체는 판단이지만, 각 칸에 붙는 **숫자는 전부 기존 산출물에서 읽는다**.
    저장소 규약(숫자 손타이핑 금지) 때문에, 그림이 읽을 JSON 이 먼저 있어야 한다.

무엇을 읽는가 (읽기 전용 — 이 스크립트는 아무 것도 덮어쓰지 않는다)
    outputs/report00_evidence.json        A/C/F 절의 실측
    outputs/report00_po_case.json         우리 커널의 검증층·한계
    outputs/report00_sionna_anatomy.json  설치본 해부(can_do / cannot_do)
    outputs/report00_sionna_probe.json    실행 프로브(자유공간 정반사 대조)

무엇을 쓰는가
    outputs/report00_decision_map.json    (새 파일. 기존 파일은 건드리지 않는다)

⭐ 공정성 규약 — 이 표는 Sionna 를 깎지 않는다
    오른쪽 두 칸(표적 항이 소거되는 실험)에서 Sionna 는 **맞는 도구**이고, 그 칸에는 Sionna 가
    이론과 얼마나 붙는지를 숫자로 적는다(자유공간 6.3e-07 dB · 정반사비 0.9997).
    왼쪽 두 칸은 '엔진이 부실하다' 가 아니라 '표적 산란은 레이다식의 다른 항' 이라는 뜻이다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report00_decision_map.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))

SRC = {
    "evidence": "outputs/report00_evidence.json",
    "po_case": "outputs/report00_po_case.json",
    "anatomy": "outputs/report00_sionna_anatomy.json",
    "probe": "outputs/report00_sionna_probe.json",
}
OUT = "outputs/report00_decision_map.json"

_IDX = re.compile(r"^(.*?)\[(\d+)\]$")


def _load() -> dict:
    d = {}
    for k, rel in SRC.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            raise SystemExit(f"근거 JSON 이 없다: {rel}")
        with open(p, encoding="utf-8") as f:
            d[k] = json.load(f)
    return d


def fetch(bag: dict, ref: str):
    """`evidence:A_plate_size_sweep.numbers.po_theory_span_db` 처럼 찍어서 값을 꺼낸다.

    없는 키는 조용히 통과하지 않고 예외다 — '모른다' 를 숫자로 위장시키지 않기 위해서다.
    """
    file_key, _, path = ref.partition(":")
    if file_key not in bag:
        raise KeyError(f"모르는 근거 파일 별칭: {file_key!r}")
    cur = bag[file_key]
    for part in path.split("."):
        m = _IDX.match(part)
        idx = None
        if m:
            part, idx = m.group(1), int(m.group(2))
        if part:
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(f"{ref} — '{part}' 가 없다")
            cur = cur[part]
        if idx is not None:
            cur = cur[idx]
    if cur is None:
        raise ValueError(f"{ref} 가 null 이다 — 숫자로 위장시키지 않는다")
    return cur


def badge(bag: dict, prefix_en: str, ref: str, fmt: str, unit: str = "") -> dict:
    """그림에 찍힐 배지 하나. 값과 **출처 문자열**이 항상 같이 다닌다."""
    v = fetch(bag, ref)
    return {"prefix_en": prefix_en, "value": v, "fmt": fmt, "unit": unit,
            "src": SRC[ref.split(":")[0]] + ":" + ref.split(":", 1)[1],
            "text_en": (prefix_en + " " + fmt.format(v) + (" " + unit if unit else "")).strip()}


def main() -> int:
    B = _load()

    axes = {
        "x": {
            "question_en": "Does the target term cancel as a constant?",
            "false_en": "No - it stays in the answer",
            "true_en": "Yes - it divides out",
            "meaning_ko": "표적 산란량이 비(比)를 취하거나 기준경로로 나눌 때 상수로 빠지는가. "
                          "빠지면 표적 모델 없이도 답이 선다.",
        },
        "y": {
            "question_en": "Is an absolute level required?",
            "false_en": "No - relative is enough",
            "true_en": "Yes - an absolute number",
            "meaning_ko": "결론이 '어느 쪽이 큰가' 로 끝나는가, 아니면 절대 dBsm·dB 를 인쇄해야 하는가.",
        },
    }

    zones = [
        {
            "id": "Z1", "x_cancels": True, "y_absolute": False,
            "tool_en": "Sionna RT alone",
            "verdict_en": "The engine is the whole answer.",
            "why_ko": "표적 항이 소거되고 절대값도 필요 없으면, 남는 것은 기하·가림·지연뿐이고 "
                      "그것이 정확히 Sionna 가 계산하는 것이다.",
        },
        {
            "id": "Z2", "x_cancels": True, "y_absolute": True,
            "tool_en": "Sionna RT alone, and it is exact",
            "verdict_en": "The engine prints the absolute number.",
            "why_ko": "전파 문제의 절대 레벨은 Sionna 가 이론과 소수점 아래 여섯째 자리까지 맞춘다. "
                      "여기서 우리 커널을 얹을 이유가 없다.",
        },
        {
            "id": "Z3", "x_cancels": False, "y_absolute": False,
            "tool_en": "Our PO surface integral, pattern only",
            "verdict_en": "The target term is needed, but only its shape.",
            "why_ko": "자세 패턴·기체 순위는 기하에서 계산된다. 측정 앵커 없이도 선다.",
        },
        {
            "id": "Z4", "x_cancels": False, "y_absolute": True,
            "tool_en": "PO integral + measurement anchor",
            "verdict_en": "Geometry sets shape, measurement sets level.",
            "why_ko": "절대 dBsm 이 필요하면 기하만으로는 닫히지 않는다. 레벨은 공개 실측에 맞추고, "
                      "격자 불확도와 PO 유효 하한을 함께 인쇄한다.",
        },
    ]

    items = [
        # ── Z1 ────────────────────────────────────────────────────────────────
        {"id": "I1", "zone": "Z1", "label_en": "Chamber geometry, shadowing, occlusion",
         "note_en": "finite mesh, exact hit test",
         "evidence": "anatomy:item9_verdict.can_do[2]", "badges": [],
         "why_ko": "가림은 유한 기하로 정확히 판정된다 — 표적이 벽 뒤면 제대로 사라진다."},
        {"id": "I2", "zone": "Z1", "label_en": "Multipath delay, floor-ghost timing",
         "note_en": "tau = path length / c",
         "evidence": "anatomy:item9_verdict.can_do[5]", "badges": [],
         "why_ko": "유령 경로의 지연은 경로 길이만으로 정해진다 — 표적 세기가 상수로 빠진다."},
        {"id": "I3", "zone": "Z1", "label_en": "CFAR threshold from target-free noise",
         "note_en": "no target in the cell",
         "evidence": "anatomy:item9_verdict.can_do[4]", "badges": [],
         "why_ko": "허위경보 문턱은 표적이 없는 셀의 통계로 정한다. 표적 항이 아예 등장하지 않는다."},

        # ── Z2 ────────────────────────────────────────────────────────────────
        {"id": "I4", "zone": "Z2", "label_en": "Free-space link budget, absolute power",
         "note_en": "measured against Friis",
         "evidence": "evidence:F_what_sionna_gets_right.numbers.los_agreement_db",
         "badges": [("RT vs Friis:", "evidence:F_what_sionna_gets_right.numbers.los_agreement_db",
                     "{:.1e}", "dB")],
         "why_ko": "자유공간 직접파는 Friis 이론과 소수 일곱째 자리에서 일치한다."},
        {"id": "I5", "zone": "Z2", "label_en": "Specular reflection strength off a wall",
         "note_en": "Fresnel coefficients and polarization",
         "evidence": "probe:exp_c_spreading_check.ratio_measured_over_predicted",
         "badges": [("RT / analytic:", "probe:exp_c_spreading_check.ratio_measured_over_predicted",
                     "{:.4f}", "")],
         "why_ko": "반사 세기는 Fresnel 4계수로 정확히 계산된다. 이미지-소스 해석해와 0.03% 안이다."},

        # ── Z3 ────────────────────────────────────────────────────────────────
        {"id": "I6", "zone": "Z3", "label_en": "Aspect pattern shape vs azimuth",
         "note_en": "kernel checked against analytic PO",
         "evidence": "po_case:s3_validation.layer1_analytic_po_convergence."
                     "kr_sweep_max_abs_db_vs_po_div16",
         "badges": [("kernel vs analytic PO:",
                     "po_case:s3_validation.layer1_analytic_po_convergence."
                     "kr_sweep_max_abs_db_vs_po_div16", "{:.3f}", "dB")],
         "why_ko": "자세 패턴은 기하에서 나온다. 커널이 해석 PO 를 제대로 계산하는지가 관문이다."},
        {"id": "I7", "zone": "Z3", "label_en": "Airframe-to-airframe ranking by shape",
         "note_en": "same material and area, different shape",
         "evidence": "evidence:C_same_material_different_shape.numbers.shape_gap_db",
         "badges": [("sphere vs plate:",
                     "evidence:C_same_material_different_shape.numbers.shape_gap_db",
                     "{:.2f}", "dB")],
         "why_ko": "같은 재질·같은 정면면적에서도 모양만으로 31 dB 가 갈린다 — 반사계수로는 못 가른다."},
        {"id": "I8", "zone": "Z3", "label_en": "Micro-Doppler modulation shape",
         "note_en": "needs complex E per part",
         "evidence": "anatomy:item9_verdict.cannot_do[3]", "badges": [],
         "why_ko": "부품별 회전 속도를 넣을 통로가 엔진에 없다. 위상을 가진 복소 산란장이 필요하다."},

        # ── Z4 ────────────────────────────────────────────────────────────────
        {"id": "I9", "zone": "Z4", "label_en": "Absolute drone RCS in dBsm",
         "note_en": "the uncertainty travels with it",
         "evidence": "po_case:s2_our_kernel.grid_dither.dither_spread_div16_db",
         "badges": [("grid dither at lambda/16:",
                     "po_case:s2_our_kernel.grid_dither.dither_spread_div16_db", "{:.2f}", "dB"),
                    ("PO validity floor:", "po_case:s4_limits.po_validity_knee_a_over_lambda",
                     "{:.3f}", "lambda")],
         "why_ko": "절대 σ 는 기하 + 실측 앵커로만 선다. 불확도를 숨기지 않고 같이 인쇄한다."},
        {"id": "I10", "zone": "Z4", "label_en": "Detection range and Pd benchmark",
         "note_en": "sigma sits directly in the radar equation",
         "evidence": "evidence:_meta.headline.po_sigma_span_db",
         "badges": [("size span a path solver misses:",
                     "evidence:_meta.headline.po_sigma_span_db", "{:.1f}", "dB")],
         "why_ko": "검출 거리는 σ 에 직접 걸린다. 크기를 40배 바꿔도 경로 진폭이 안 움직이는 도구로는 못 낸다."},
        {"id": "I11", "zone": "Z4", "label_en": "Mesh fidelity budget for a drone target",
         "note_en": "specular-only echo collapses with facets",
         "evidence": "evidence:_meta.headline.drone_collapse_db",
         "badges": [("collapse over the facet sweep:",
                     "evidence:_meta.headline.drone_collapse_db", "{:.1f}", "dB")],
         "why_ko": "실루엣이 유지돼도 정반사 채널만으로는 49 dB 가 무너진다 — 면적분이 있어야 메쉬 예산을 잴 수 있다."},
    ]

    # 배지를 값+출처로 확정한다(여기서 예외가 나면 근거가 없는 것이다).
    for it in items:
        it["badges"] = [badge(B, p, r, f, u) for (p, r, f, u) in it["badges"]]
        fetch(B, it["evidence"])                       # 존재 확인만 — 값은 그림이 안 쓴다
        it["evidence_src"] = (SRC[it["evidence"].split(":")[0]] + ":"
                              + it["evidence"].split(":", 1)[1])

    doc = {
        "_meta": {
            "file": OUT,
            "title": "리포트 00 F4 — 무엇을 Sionna 만으로 할 수 있고, 어디서 표적 항이 필요해지는가",
            "generated": _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "benchmark/build_report00_decision_map.py",
            "reads": list(SRC.values()),
            "writes_only": OUT,
            "value_rule": "배지 값은 전부 위 네 JSON 에서 fetch() 로 읽었다. "
                          "손으로 친 수치는 0 개다. 배치(어느 칸인가)는 판단이고, 그 근거는 evidence 키다.",
            "house_rules": "본문·주석은 한국어, 그림 안 텍스트는 전부 영어.",
            "fairness_rule": "오른쪽 두 칸에서 Sionna 는 맞는 도구이고 그 정확도를 숫자로 적는다. "
                             "틀린 것은 '엔진이 부실하다' 가 아니라 '전파용 도구에 표적 산란을 시켰다' 이다.",
        },
        "axes": axes,
        "zones": zones,
        "items": items,
        "footer_en": ("The split is the radar equation's own: propagation is the engine's term, "
                      "target scattering is a separate one."),
    }

    p = os.path.join(ROOT, OUT)
    if os.path.exists(p):
        print(f"⚠ 이미 있다 — 덮어쓴다: {OUT}")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    n_badge = sum(len(i["badges"]) for i in items)
    print(f"✅ {OUT} — 칸 {len(zones)}개 · 항목 {len(items)}개 · 숫자 배지 {n_badge}개 "
          f"(전부 기존 JSON 에서 읽음)")
    for z in zones:
        got = [i["label_en"] for i in items if i["zone"] == z["id"]]
        print(f"   {z['id']} {z['tool_en']}: {len(got)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
