# -*- coding: utf-8 -*-
"""prior_work/md_classification_dl_survey.md 의 §3 표를 그대로 파싱해 수치 원장 JSON 을 만든다.

⭐«표 내용 그대로»를 보장하는 방법: 문서를 쓰고 나서 **문서에서 되읽어** JSON 을 만든다.
   손으로 두 번 적지 않는다.
"""
from __future__ import annotations

import json
import os
import re

MD = "/workspace/sionna/prior_work/md_classification_dl_survey.md"
OUT = "/workspace/sionna/outputs/md_classification_dl_survey.json"
REC = ("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
       "scratchpad/survey_recovered.json")

COLS = ["paper", "year", "method", "input_representation", "data", "accuracy", "link"]


def split_row(line: str) -> list[str]:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def parse_table(lines: list[str], header_idx: int) -> list[dict]:
    """header_idx = 헤더 줄 인덱스. 구분선 다음부터 표가 끝날 때까지."""
    rows = []
    i = header_idx + 2
    while i < len(lines) and lines[i].lstrip().startswith("|"):
        cells = split_row(lines[i])
        assert len(cells) == 7, f"열 수가 7이 아니다({len(cells)}): {lines[i][:120]}"
        row = dict(zip(COLS, cells))
        row["year"] = int(row["year"])
        rows.append(row)
        i += 1
    return rows


def find_table_after(lines: list[str], heading: str) -> list[dict]:
    for n, ln in enumerate(lines):
        if ln.startswith(heading):
            for m in range(n, min(n + 12, len(lines))):
                if lines[m].lstrip().startswith("| 논문 |"):
                    return parse_table(lines, m)
    raise AssertionError(f"표를 못 찾았다: {heading}")


def main() -> None:
    with open(MD, encoding="utf-8") as f:
        lines = f.read().split("\n")

    classification = find_table_after(lines, "### 3-1.")
    sim_anchor = find_table_after(lines, "### 3-2.")
    surveys = find_table_after(lines, "### 3-3.")

    rec = json.load(open(REC, encoding="utf-8"))
    verdicts = {v["title"]: v for v in rec["verdicts"]}
    papers = {p["title"]: p for p in rec["papers"]}
    verified_titles = sorted(t for t, v in verdicts.items() if v["verified"])
    failed_titles = sorted(t for t, v in verdicts.items() if not v["verified"])
    unjudged_titles = sorted(set(papers) - set(verdicts))

    n_table = len(classification) + len(sim_anchor) + len(surveys)
    assert n_table == len(verified_titles) == 39, (n_table, len(verified_titles))

    ours = json.load(open("/workspace/sionna/outputs/classify_airframe.json",
                          encoding="utf-8"))
    ref = json.load(open("/workspace/sionna/outputs/refute_classify_airframe.json",
                         encoding="utf-8"))

    doc = {
        "_meta": {
            "title": "드론 마이크로도플러 분류 딥러닝 선행연구 — 수치 원장",
            "date": "2026-08-15",
            "companion_doc": "prior_work/md_classification_dl_survey.md",
            "generator": "종합 세션이 문서를 쓴 뒤 문서의 §3 표를 되읽어 생성(손으로 두 번 적지 않음)",
            "scope": ("① 기법 계보(고전→CNN 전이→경량 스크래치→시퀀스/트랜스포머) "
                      "② 입력 표현 표준 ③ 합성학습(sim-to-real) 성숙도 "
                      "④ 패시브 조명원 분류 존재 여부 ⑤ 우리 첫 분류 실험과의 거리"),
            "recovery": {
                "why": "앞 라운드에서 수집·원문검증까지 끝났으나 종합 단계에서 세션 한도로 중단",
                "recovered_file": REC,
                "recovered_bytes": os.path.getsize(REC),
                "papers_collected": len(papers),
                "verdicts_made": len(verdicts),
                "verified_true": len(verified_titles),
                "verified_false": len(failed_titles),
                "no_verdict": len(unjudged_titles),
                "table_policy": "본표에는 verified=true 39편만 넣는다. 불통과 2편과 미판정 4편은 §5.",
                "sibling_drafts": [
                    "prior_work/drone_md_dl_classification_survey.md",
                    "prior_work/sim2real_md_classification_survey.md",
                    "prior_work/drone_md_classification_dl_survey.md",
                ],
                "trust_note": ("39편의 '원문과 맞다'는 판정은 앞 라운드 검증자의 것이다. "
                               "이번 세션이 다시 연 것은 link_checks 의 7건뿐이다."),
            },
            "table_columns": COLS,
            "counts": {
                "classification_papers": len(classification),
                "simulation_anchors_no_classifier": len(sim_anchor),
                "surveys": len(surveys),
                "total_in_tables": n_table,
            },
        },
        "table_classification_papers": classification,
        "table_simulation_anchors": sim_anchor,
        "table_surveys": surveys,
        "verified_titles": verified_titles,
        "verification_failed": [
            {
                "title": t,
                "corrections": verdicts[t]["corrections"],
                "evidence": verdicts[t]["evidence"],
            }
            for t in failed_titles
        ],
        "no_verdict_carried_over": [
            {
                "title": t,
                "year": papers[t]["year"],
                "venue": papers[t]["venue"],
                "link": papers[t]["link"],
                "why_it_matters": papers[t]["claim"],
                "status": "수집만 됨 — 이번 라운드의 원문 검증이 닿지 못함",
            }
            for t in unjudged_titles
        ],
        # ⚠이름 그대로: 일부 항목은 «정정 없음 + 보충»이다(전부가 정정인 것은 아니다).
        "verdict_notes_and_corrections": [
            {"title": t, "note": verdicts[t]["corrections"]}
            for t in verified_titles
            if verdicts[t]["corrections"].strip()
            and verdicts[t]["corrections"].strip() != "(없음)"
        ],
        "our_first_classification_experiment": {
            "generator": ours["_meta"]["generator"],
            "ledger": "outputs/classify_airframe.json",
            "refutation_ledger": "outputs/refute_classify_airframe.json",
            "method_ko": "스펙 유래 빗살 템플릿 정합(학습 파라미터 0개) — 딥러닝 아님",
            "genealogy_slot_ko": "문헌 계보의 0세대 앞자리(고전 특징+분류기보다 앞) · 물리유도 열",
            "fc_hz": ours["_meta"]["fc_hz"],
            "prf_hz": ours["_meta"]["prf_hz"],
            "range_m": 15.0,
            "airframes": ours["airframes"],
            "templates_hz": {k: v["f_flash_hz_spec"] for k, v in ours["templates"].items()},
            "window": ours["_meta"]["window"],
            "chance_level": ours["_meta"]["chance_level"],
            "accuracy": {
                "ours_kernel": ours["results"]["ours"]["aggregate_accuracy"],
                "sionna": ours["results"]["sionna"]["aggregate_accuracy"],
                "null_shuffle_ours": ours["results"]["ours"]["null_aggregate_accuracy"],
                "null_shuffle_sionna": ours["results"]["sionna"]["null_aggregate_accuracy"],
            },
            "n_windows_total_per_engine": ours["results"]["ours"]["n_windows_total"],
            "effective_independent_units": {
                "ours": ref["G_effective_sample_size"]["ours"]["n_series"],
                "sionna": ref["G_effective_sample_size"]["sionna"]["n_series"],
                "note_ko": ref["G_effective_sample_size"]["note_ko"],
            },
            "robustness": {
                "win256_x32": {
                    "ours": ref["C_window_convention"]["win256_x32"]["ours"]["accuracy"],
                    "sionna": ref["C_window_convention"]["win256_x32"]["sionna"]["accuracy"],
                },
                "template_shift_+5Hz": {
                    "ours": ref["E_template_shift_control"]["+5Hz"]["ours"]["accuracy"],
                    "sionna": ref["E_template_shift_control"]["+5Hz"]["sionna"]["accuracy"],
                },
                "template_shift_+10Hz": {
                    "ours": ref["E_template_shift_control"]["+10Hz"]["ours"]["accuracy"],
                    "sionna": ref["E_template_shift_control"]["+10Hz"]["sionna"]["accuracy"],
                },
                "phase_randomized": ref["F_spectrum_preserving_controls"]["phase_randomized_accuracy"],
                "sionna_el0_only": ours["results"]["sionna"]["per_elevation"]["+0"]["accuracy"],
            },
            "apples_to_apples_warning_ko": (
                "문헌=실측 스펙트로그램 수천~수만 장·잡음 주입·학습 있음·우연 1/5~1/6, "
                "우리=무잡음 시뮬 자세 시계열 8192점·학습 없음·우연 1/3·실질 독립 단위 21. "
                "우리 100%는 분류 성능이 아니라 '분류 가능성의 상한'이다."
            ),
            "unique_axis_ko": (
                "우리는 '엔진이 무늬를 그리는가'를 묻는다 — 같은 분류기로 두 시뮬 엔진을 겨룬 "
                "편은 검증 39편 중 0편이고, Kearney & Gurbuz(TAES 2026)는 저충실도 시뮬 단독 "
                "학습이 random guessing 을 못 넘는다고 경고한다. 우리 수는 엔진 비교의 눈금이다."
            ),
        },
        "borrow_plan": [
            {"order": 1, "item": "입력 표현 승격(STFT 스펙트로그램 + CVD 병합)",
             "evidence": "Kim +5.4pp · Park(A-SPC) +10pp(망 고정) · Chen 3종 융합 >97%"},
            {"order": 2, "item": "경량 스크래치 CNN(0.15~0.5M) 부터, ImageNet 전이 아님",
             "evidence": "Park 0.217M 97.14% · DIAT-RadSATNet 0.45M 97.3% · AirGuard 0.15M 99.37%"},
            {"order": 3, "item": "시계열 직행 분기(Conv1D/GRU/LSTM/Transformer 비교)",
             "evidence": "Larrat 2025 복소 시계열 직행 4종 비교 · μDopplerTag 1D 언랩"},
            {"order": 4, "item": "듀얼밴드 late fusion(밴드를 합치지 말고 판정을 합친다)",
             "evidence": "Zhang & Song 2026 L/K Mamba 97.5% · Ritchie 2016 노드별 투표"},
            {"order": 5, "item": "분할 규약을 먼저 못 박기(창 단위 분할 금지)",
             "evidence": "Gérard 날짜 분리 안 하면 98~100% 부풀음 · White 비행 단위 · AirGuard 미기재 누수 위험"},
            {"order": 6, "item": "잡음 축을 곡선으로(F1 vs SNR)",
             "evidence": "Raval F1 vs SNR 규약 · Larrat 4종 잡음 · Malarvanan 펄스당 SNR"},
            {"order": 7, "item": "새(bird) 클래스 도입 전엔 난이도 비교 성립 안 함",
             "evidence": "Molchanov 2014 이후 거의 전편이 새를 포함"},
        ],
        "not_found": [
            "CNN-LSTM / CRNN 하이브리드 — 검증 39편에 0편(시계열 결합은 Larrat 의 4종 병렬 비교뿐)",
            "자기지도 사전학습(SimCLR·MAE·MoCo 류) 0편 — 대조학습은 Zhang & Song 의 보조 손실로만",
            "패시브(방송·셀룰러 조명원) 에코 + 딥러닝 분류 0편",
            "바이스태틱 마이크로도플러 + 학습 분류 0편 — Costa 2025 는 모델만, 학습은 후속과제",
            "레이트레이싱(Sionna 포함) 합성 데이터로 분류망을 학습한 편 0편 — Li 2025 는 분류 없음",
            "두 시뮬레이션 엔진을 같은 분류기로 겨룬 편 0편",
            "공개 코드 저장소 확인 안 함; 공개 벤치마크는 DIAT-μSAT·LSS-FMCWR-1.0 둘뿐(둘 다 능동)",
            "수치 미확보: Björklund 2018(초록에 수치 없음) · Björklund 2019(미공개) · Hanif 2022(본문 미확보) · Li 2025(전문 유료)",
            "본문 미열람(초록·2차만): Björklund 2018/2019 · Chen 2024 · DC-Former · PinpuNet · Li ICCT · Hanif",
            "언어권 공백: 러시아어권·폴란드어권·중국어권 회의록(SPSympo·IRS·CIE Radar·Journal of Radars 원문) 목차 훑기 안 함",
            "개방집합(open-set) 인식·운용 Pfa 비용을 다룬 편 못 찾음 — Networked ISAC 의 미지 서브타입 일반화가 최근접",
            "prior_work/pdfs/jsen2022_hanif_microdoppler_review.pdf 는 논문이 아니라 Cloudflare 차단 페이지 — 교체 필요",
        ],
        "link_checks": [
            {"url": "https://api.crossref.org/works/10.1109/LGRS.2016.2624820",
             "checked": "Kim 외 GRSL 서지",
             "result": "OK — 제목·저자 3인·GRSL·2017·vol.14·38-42 일치"},
            {"url": "https://arxiv.org/abs/2009.14422",
             "checked": "Park(J.) 초록",
             "result": "OK — 제목·저자 3인·2020-09-30, 초록에 light CNN·A-SPC·97.14%·10% 향상 실재"},
            {"url": "https://api.crossref.org/works/10.3390/app15189957",
             "checked": "Cao 외 서지(미판정 4편 중 1편)",
             "result": "OK — Applied Sciences 15(18) article 9957, 2025, 저자 5인 실재(내용은 미검증)"},
            {"url": "https://arxiv.org/abs/2603.13112",
             "checked": "AirGuard 초록",
             "result": "OK — 저자 6인·2026-03-13, cmD+HRRP 이중입력 CNN 실재. 99.37% 는 초록에 없음(본문 수치)"},
            {"url": "https://api.crossref.org/works/10.1109/ICCT67417.2025.11374154",
             "checked": "Li 외(Sionna RT) 서지",
             "result": "OK — 2025 IEEE 25th ICCT, 저자 6인 일치"},
            {"url": "https://api.crossref.org/works/10.1109/TAES.2026.3685229",
             "checked": "Kearney & Gurbuz 저널판 서지",
             "result": "OK — TAES vol.62:9875-9891, 2026 — 학회판과 제목이 다르다는 판정 확인"},
            {"url": "https://api.crossref.org/works/10.1109/JSTEAP.2025.3604407",
             "checked": "Costa 외 저널판 서지",
             "result": "OK — JSTEAP 1(1):208-222, 2025, 저자 7인(Engelhardt 포함) — 회의판 6인과 다름 확인"},
        ],
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")
    print("rows:", doc["_meta"]["counts"])
    print("verified/false/unjudged:", len(verified_titles), len(failed_titles), len(unjudged_titles))


if __name__ == "__main__":
    main()
