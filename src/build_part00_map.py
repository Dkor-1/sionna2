# -*- coding: utf-8 -*-
"""
build_part00_map.py — 부 0 「지도」 → 편 00
==========================================================================================
편 00 이 답하는 질문 하나
    **무엇부터 읽어야 하나.**

제목 = 결론 문장
    00 map  읽는 목적이 셋이면 읽는 순서도 셋이다

⚠ 이 편은 «신규» 다 — 옛 셀에서 오지 않고 README 와 각 편의 여는 문장에서 조립한다.
   그래서 숫자는 전부 `outputs/reports_index.json`(= 편 78개를 실제로 세어 만든 색인)에서
   읽는다. 편이 늘거나 줄면 이 편의 숫자가 따라 움직인다.

실행 순서
    ① PYTHONPATH=src python src/make_reports_index.py   ← 색인을 먼저 만든다
    ② PYTHONPATH=src python src/build_part00_map.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from report_registry import PARTS, index_shard, nb_path, ref, ref_doc    # noqa: E402
from report_style import (ContractError, build_notebook, header, md,     # noqa: E402
                          next_steps, num, table)

IDX = "outputs/reports_index.json"
PLAN = "outputs/restruct_exec_plan.json"
DIAG = "outputs/restruct_diagnose.json"


def _n(key: str, src: str = IDX, fmt: str | None = None, unit: str = "") -> str:
    return num(None, (src, key), fmt, unit)


#: 읽기 경로 — 계획 `reading_paths` 의 route 를 앵커로 옮긴 것.
#  ⚠ 계획은 편 **번호**로 적혀 있어 편이 늘면 어긋난다. 앵커로 적어 두면 번호가 바뀌어도 산다.
PATH_FAST = ["decision-table", "where-we-stand", "mesh-vs-real", "kernel-vs-reference",
             "anchor-mode", "ladder-answer", "md-prf", "cost-ledger", "cfar-calib", "r90",
             "sim-vs-meas"]
PATH_TRUST = ["stock-says", "eight-factors", "size-sweep", "kernel-vs-reference",
              "po-knee", "blind-p3", "box-sphere-control", "fleet-prereg",
              "sigma-robustness", "ladder-premature", "md-calibration", "cfar-calib",
              "cfar-why", "rank-durability", "session-drift"]


def _route(anchors: list[str]) -> str:
    return " → ".join(ref(a, short=True) for a in anchors)


def report_00_map():
    with open(os.path.join(_ROOT, IDX), encoding="utf-8") as f:
        idx = json.load(f)
    rows = idx["reports"]
    by_part = {k: [r for r in rows if r["part"] == k] for k in PARTS}

    part_rows = []
    for k, p in sorted(PARTS.items()):
        sub = by_part.get(k) or []
        if not sub:
            continue
        span = f"{sub[0]['no']}~{sub[-1]['no']}" if len(sub) > 1 else sub[0]["no"]
        part_rows.append([f"부 {k}", p["name"], p["question"], span, str(len(sub))])

    return [
        header(
            num="00",
            title="읽는 목적이 셋이면 읽는 순서도 셋이다",
            did="편 78개를 부 12개로 묶고, 읽는 목적마다 다른 진입 경로 셋을 깔았다.",
            results=[
                f"편은 {_n('_meta.n_reports', fmt='{:.0f}', unit='개')} 이고 부는 "
                f"{_n('_meta.n_parts', fmt='{:.0f}', unit='개')} 다 — 한 편이 중심 메시지 하나를 "
                f"들고, 편 제목이 곧 그 편의 결론 문장이다.",

                f"재구성 전은 편 8개였고 그중 7개를 진단했다 — 화면 글자의 "
                f"{_n('s1_source_tags.size_on_screen.share_pct_of_chars', DIAG, '{:.1f}', '%')} 가 "
                f"본문이 아니라 출처 태그였고, 태그는 "
                f"{_n('s1_source_tags.counts.total_tags', DIAG, '{:,.0f}', '개')} 였다.",

                f"그래서 출처를 각주로 뺐다 — 태그를 지우면 문장이 "
                f"{_n('s1_source_tags.per_sentence.sentence_length_inflation.median_with_tags', DIAG, '{:.0f}')} → "
                f"{_n('s1_source_tags.per_sentence.sentence_length_inflation.median_without_tags', DIAG, '{:.0f}', '자')} "
                f"였고, 같은 (파일, 키) 재인용 "
                f"{_n('s1_source_tags.counts.repeat_occurrences', DIAG, '{:,.0f}', '회')} 가 번호 "
                f"하나로 모인다.",

                f"경로는 셋이다 — **빨리 훑기**(부마다 결론 편 하나씩) · **왜 믿을 수 있나**"
                f"(검증·대조·반증 편만) · **다시 돌리기**(리포트를 안 읽고 명령만 본다).",

                f"논문 문장과 재현 절차는 리포트 밖에 산다 — "
                f"{ref_doc('docs/paper/README.md', '`docs/paper/`')} 와 "
                f"{ref_doc('docs/REPRODUCE.md', '`docs/REPRODUCE.md`')} 다.",
            ],
            method=[
                ("편 하나 = 메시지 하나", "제목이 «…다» 로 끝나는 평서문이고, 그 문장이 그 편이 "
                                  "판 결론이다. 제목만 읽어도 목차가 된다"),
                ("부 = 물음 하나", "부마다 답하는 질문이 하나다. 그 질문에 답하는 편들이 그 부에 "
                             "모여 있다"),
                ("색인", "편마다 «어느 JSON 을 읽고 어느 명령으로 다시 나오나» 를 "
                      f"`{IDX}` 에 기계용으로 적었다 — 각 편의 여는 블록에서 직접 읽어 만든다"),
                ("경로", "읽는 목적이 다르면 순서도 다르다. 세 경로가 같은 78편을 서로 다르게 "
                      "가로지른다"),
            ],
            repro=dict(cmd=["PYTHONPATH=src python src/make_reports_index.py",
                            "PYTHONPATH=src python src/build_part00_map.py",
                            "PYTHONPATH=src python benchmark/check_report_links.py"],
                       out=[IDX], runtime="약 5초 (GPU 0장)",
                       note="편이 늘거나 줄면 색인을 다시 만들고 이 편을 다시 조립한다"),
        ),

        md("## 부 12개 — 각 부가 답하는 물음 하나 (앞 절반)", "",
           table(["부", "이름", "이 부가 답하는 물음", "편", "수"], part_rows[:6])),

        md("## 부 12개 (뒤 절반)", "",
           table(["부", "이름", "이 부가 답하는 물음", "편", "수"], part_rows[6:])),

        md("## ① 빨리 훑기 — 30분", "",
           "**이 저장소가 무엇을 해냈는지만 알면 되는 사람.** 부마다 결론 편 하나씩이다. "
           "제목만 읽어도 되고, 막히는 데서만 그 편을 연다.", "",
           _route(PATH_FAST)),

        md("## ② 왜 믿을 수 있나 — 2시간", "",
           "**판정을 검사하려는 사람**(심사·적대검증). 검증·대조·반증 편만 모았다. 뼈대는 "
           "눈감기 대조·사전등록 채점·PREMATURE 판정·널 교정 넷이다.", "",
           _route(PATH_TRUST)),

        md("## ③ 다시 돌리기 · ④ 논문 쓰는 사람", "",
           f"**③ 숫자를 재생산하려는 사람** — 리포트를 읽지 않는다. "
           f"{ref_doc('docs/REPRODUCE.md')} 의 «편 → 명령 → 출력 → 소요» 표 하나면 끝나고, "
           f"기계용 사본은 {ref_doc('outputs/reports_index.json')} 다.", "",
           f"**④ 원고에 옮기려는 사람** — 리포트 본문에는 논문 문장이 없다. 전부 "
           f"{ref_doc('docs/paper/README.md', 'docs/paper/')} 에 있고, 조각마다 «어느 편에서 "
           f"왔나» 가 붙어 있다.", "",
           f"전체 목차와 부 소개는 {ref_doc('README.md')} 다."),

        md("## 이 편들을 읽을 때 알아 두면 되는 규약 다섯", "",
           table(["규약", "무슨 뜻인가"],
                 [["제목이 결론이다", "편 제목은 «…다» 로 끝나는 평서문이고, 그 편이 판 결론 "
                                "그 자체다. 물음표로 끝나는 제목은 규약이 막는다"],
                  ["숫자 옆의 `[^n]`", "그 숫자가 온 JSON 파일과 키다. 편 끝 «출처» 표에 "
                                  "파일·키·값이 있고, 그 값은 표를 만들 때 JSON 을 다시 열어 "
                                  "채운 것이다"],
                  ["여는 블록 넷", "한 일 · 결과 · 방법 · 재현. **결과만 읽어도** 그 편의 답을 "
                              "알 수 있게 쓴다"],
                  ["마지막 절은 «다음 단계»", "한계 목록이 아니라 **앞을 보는 행동**이다. 가운데 "
                                      "칸이 «그러면 결정되는 것» 이고, 그 칸이 빈 행은 "
                                      "규약이 막는다"],
                  ["⚠ 와 ⭐", "⚠ 는 그 숫자가 서 있는 전제(사슬 세대·메쉬 판)를, ⭐ 는 그 절의 "
                          "핵심 판단을 가리킨다"]])),

        next_steps([
            ("편이 늘거나 줄면 색인과 이 편을 다시 만든다",
             "지도의 편 수·부 구성이 실제 디스크와 같아진다",
             "`src/make_reports_index.py` → `src/build_part00_map.py`"),
            ("편 사이 참조를 매번 검사한다",
             "끊긴 링크·없는 앵커·안 열리는 출처가 0 인 채로 유지된다",
             "`benchmark/check_report_links.py`"),
            ("읽기 경로 ①②를 독자에게 태워 보고 막히는 자리를 센다",
             "경로에 넣을 편과 뺄 편이 실제 독자 반응으로 확정된다",
             ref("decision-matrix", short=True)),
        ]),
    ]


def main() -> int:
    if not os.path.exists(os.path.join(_ROOT, IDX)):
        raise ContractError(
            f"색인이 없다 — {IDX}\n"
            f"  → 먼저 `PYTHONPATH=src python src/make_reports_index.py` 를 돌려라.")
    rep = build_notebook(nb_path("map"), report_00_map(), strict=True, quiet=True)
    index_shard("map", md_cells=rep["md_cells"], figures=rep["figures"],
                provenance_tags=rep["provenance_tags"],
                negatives=rep["n_negatives"], builder=os.path.basename(__file__))
    mark = "✅" if rep["ok"] else "⛔"
    print(f"── 부 0 「지도」 ──")
    print(f"  {mark} {rep['path']:46s} md {rep['md_cells']:2d}/25 · "
          f"그림 {rep['figures']}/8 · 출처 {rep['provenance_tags']:3d} · "
          f"부정문 {rep['n_negatives']}/3 · 완충어 {rep['n_hedges']}/0")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
