# -*- coding: utf-8 -*-
"""
make_report00_foundations.py — 리포트 00 「기초」 빌더  →  report00_foundations.ipynb
============================================================================================
계약: `docs/REBUILD_2026-07-30.md` §5 (서술 규약) — 강제는 `src/report_style.py` 가 한다.
     여는 블록·분량 상한·톤 검사·**출처 없는 숫자 금지**가 전부 함수 안에서 터진다.

이 편이 한 일 하나
    **Sionna RT 설치본을 인자 목록까지 해부해 "광선이 면을 맞았을 때 무엇이 계산되는가" 를
    적고, 표적 산란이 어디서부터 별도 항이 되는지를 실측과 결정표로 갈랐다.**
    다른 편이 압축돼 있다면 이 편은 풀어 쓴다 — 유도를 건너뛰지 않고, 기호를 처음 쓸 때마다
    뜻을 적고, 비유마다 그 비유가 깨지는 자리를 붙인다.

⭐ 이 편의 공정성 규약 (근거 JSON 의 `_meta.fairness_note` 를 그대로 따른다)
    · Sionna 는 반사 세기를 **정확히 계산한다** — Fresnel r_te/r_tm, Jones 행렬, 편파.
    · Sionna RT 에는 **1차 UTD 쐐기회절이 구현돼 있다**. 설치본 기본값이 off 일 뿐이다.
    · 환경·클러터에서는 Sionna 가 **맞는 도구**다.
    틀린 것은 "Sionna 가 부실하다" 가 아니라 "전파용 도구에 표적 산란을 시켰다" 이다.
    "무한평면 가정" 같은 거친 요약도 쓰지 않는다 — 기술보고서 원문과 코드 인자를 그대로 인용한다.

근거 파일 다섯 갈래
    `outputs/report00_sionna_anatomy.json` — 설치본 2.0.1 소스 해부(발사·중복제거·인자·확산인자·
                                             회절·확산산란·rcs 문자열 계수·종합 판정)
    `outputs/report00_sionna_probe.json`   — 실행 프로브(광선 수 400배 스윕·평판 크기 125배 스윕·
                                             이미지소스 해석해 대조)
    `outputs/report00_evidence.json`       — A~H 실측 근거(평판 1600배·면 수 사다리·모양 대조·
                                             단위 논증·확산 우회·공정성·원문 인용·테셀레이션)
    `outputs/report00_po_case.json`        — 왜 PO 인가 · 우리 커널 유도 · 검증 3층 · 한계 · 선행
                                             (`benchmark/build_report00_po_case.py`)
    `outputs/report00_decision_map.json`   — §4 결정표의 축·칸·항목
                                             (`benchmark/build_report00_decision_map.py`)

그림 4장은 `src/figs_report00.py` 가 게재 규격(벡터 PDF + 400 dpi PNG · 9 pt · 색+해치)으로 그린다.
그림 안의 글자는 전부 영어이고, 본문·주석·print 는 한국어다.

이 파일이 하는 일
    JSON 을 읽어 노트북을 조립하는 것뿐이다. **계산도 그림도 여기서 새로 하지 않는다.**
    본문의 수치는 하나도 손으로 치지 않는다 — 전부 `num(None, …)` 과 `table_from()` 이
    JSON 에서 직접 읽어 출처 태그를 달고 넣는다.

실행
    cd /home/yunjung/workspace/sionna2
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report00_po_case.py       # ① PO 근거
    PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_report00_decision_map.py  # ② 결정표 근거
    PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_report00.py                      # ③ 그림 4장
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report00_foundations.py          # ④ 리포트

⚠ GPU 도 Sionna 실행도 필요 없다. 전부 합쳐 수 분.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (build_notebook, caption, fetch, header, md,     # noqa: E402
                          next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  근거 파일 — 이 편의 모든 숫자가 나오는 곳
# --------------------------------------------------------------------------- #
ANA = "outputs/report00_sionna_anatomy.json"
PRB = "outputs/report00_sionna_probe.json"
EVD = "outputs/report00_evidence.json"
POC = "outputs/report00_po_case.json"
DEC = "outputs/report00_decision_map.json"
MDP = "outputs/report00_microdoppler.json"

NB_OUT = os.path.join(_ROOT, "report00_foundations.ipynb")
FIG = "outputs/figures"

#: `report00_decision_map.json:items` 는 순서가 고정돼 있다. 표를 반으로 쪼갤 때
#: 이름이 아니라 이 인덱스로 뽑는다 — 표 하나가 결정표의 한쪽 절반이 되도록.
RIGHT_HALF = [0, 1, 2, 3, 4]        # 표적 항이 소거되는 칸 (Z1 · Z2)
LEFT_HALF = [5, 6, 7, 8, 9, 10]     # 표적 항이 답에 남는 칸 (Z3 · Z4)

ITEM_COLS = [("실험 유형", "label_en"), ("칸", "zone"), ("왜 그런지", "why_ko")]


def _n(key: str, src: str, fmt: str | None = None, unit: str = "") -> str:
    """`num(None, …)` 축약. **값은 언제나 JSON 이 정한다** — 이 파일에 숫자 리터럴은 없다."""
    return num(None, (src, key), fmt, unit)


def _fig(no: int, name: str, question: str) -> list[str]:
    """그림 한 장 = 마크다운 이미지 + 질문 캡션 한 줄(§5.6-2)."""
    return [f"![report00 {name}]({FIG}/report00_{name}.png)", "", caption(no, question)]


# --------------------------------------------------------------------------- #
def blocks():
    return [
        # ── 여는 블록 ───────────────────────────────────────────────────────
        header(
            num=0,
            title="기초: Sionna 로 되는 것과, 표적 산란이 시작되는 자리",
            did="Sionna RT 설치본을 인자 목록까지 해부해 광선이 면을 맞았을 때 무엇이 계산되는지를 "
                "적고, 표적 산란이 어디서부터 별도 항이 되는지를 실측과 결정표로 갈랐다.",
            results=[
                f"Sionna 는 자기 문제를 정확히 푼다 — 자유공간 직접파가 Friis 이론과 "
                f"{_n('F_what_sionna_gets_right.numbers.los_agreement_db', EVD, '{:.1e}', 'dB')} "
                f"안이고, 평면 반사 진폭이 이미지-소스 해석해 대비 "
                f"{_n('exp_c_spreading_check.ratio_measured_over_predicted', PRB, '{:.4f}')} 다.",

                f"금속 평판의 면적을 "
                f"{_n('A_plate_size_sweep.numbers.area_ratio_max', EVD, '{:.0f}')}배 키우면 "
                f"PO 단면적은 "
                f"{_n('A_plate_size_sweep.numbers.po_theory_span_db', EVD, '{:.2f}', 'dB')} 커지고, "
                f"path solver 의 표적 경로 진폭은 "
                f"{_n('A_plate_size_sweep.numbers.rt_span_db', EVD, '{:.1e}', 'dB')} 움직인다 — "
                f"경로 수는 전 구간 "
                f"{_n('A_plate_size_sweep.numbers.n_paths_target_set_union[0]', EVD, '{:.0f}')}개다.",

                f"같은 재질·같은 정면면적에서 모양만 바꾸면 σ 가 "
                f"{_n('C_same_material_different_shape.numbers.shape_gap_db', EVD, '{:.2f}', 'dB')} "
                f"갈린다 — 같은 반사계수 위에서 위상 정렬이 답을 정한다.",

                f"우리 PO 커널은 해석 PO 대비 "
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_max_abs_db_vs_po_div16', POC, '{:.3f}', 'dB')} "
                f"안에서 수렴하고, 유효 하한은 특징 폭 "
                f"{_n('s4_limits.po_validity_knee_a_over_lambda', POC, '{:.3f}')}λ 다.",

                "결정표는 두 문장으로 갈린다 — 표적 항이 비에서 상수로 소거되는가, "
                "절대값이 필요한가(그림 4).",
            ],
            method=[
                ("경로 탐색·필드 계산의 인자",
                 f"설치본 {_n('item6_versions.values.sionna_rt', ANA)} 소스를 직접 읽고 "
                 f"`inspect.signature` 로 런타임 재확인"),
                ("크기 무응답",
                 f"빈 씬에서 평판 변만 바꾸며 예산 {len(fetch((EVD, '_meta.solver.budgets')))}단 · "
                 f"시드 {len(fetch((EVD, '_meta.solver.seeds')))}개 · "
                 f"깊이 {len(fetch((EVD, '_meta.solver.depths')))}단으로 "
                 f"{_n('A_plate_size_sweep.numbers.n_cells', EVD, '{:.0f}')}셀 반복"),
                ("우리 커널의 정확도", "해석 PO 구 · PEC 구 Mie 정확해 · 얇은 띠 2D EFIE MoM · "
                                     "PEC 이면각 닫힌형과 대조"),
                ("절대 레벨", "공개 실측(Das, IEEE WCL 2026)에 A(f) 의 기울기를 맞춤"),
                ("결정표의 배치", "판단이다. 행마다 그 판단이 선 근거 JSON 키를 붙였다"),
            ],
            repro=dict(
                cmd=[
                    "PYTHONPATH=src python benchmark/build_report00_po_case.py",
                    "PYTHONPATH=src python benchmark/build_report00_decision_map.py",
                    "PYTHONPATH=src python src/figs_report00.py",
                    "PYTHONPATH=src python src/make_report00_foundations.py",
                ],
                out=[POC, DEC, ANA, PRB, EVD],
                runtime="약 3분 (GPU 0장 — 전부 JSON 읽기와 그림 그리기다)",
                note="anatomy · probe · evidence 세 JSON 은 설치본 해부와 실행 프로브의 산출물이고, "
                     "각 파일의 `_meta` 가 자기 생성기 경로를 들고 있다"),
        ),

        # ═══ §1 ════════════════════════════════════════════════════════════
        md("## §1. Sionna 는 광선이 맞으면 무엇을 계산하는가", "",
           "답은 **두 단계**로 만들어진다. **① 경로 탐색.** 소스마다 광선을 구면에 뿌려"
           "(피보나치 격자, 난수가 아니다) "
           "어느 면들을 어떤 순서로 맞는지 후보를 모은다.", "",
           "같은 면 순서를 발견한 광선은 "
           "**첫 발만 남기고 나머지를 버린다** — 면 해시로 만든 경로 지문의 카운터를 "
           "원자적으로 올리고 `samples_counter == 0` 인 광선만 저장한다"
           "(`sb_candidate_generator.py:484-498`). 그다음 이미지법이 소스를 각 면에 거울반사시켜 "
           "교점 좌표를 해석적으로 다시 푼다(`image_method.py:37-47`).", "",
           "**② 필드 계산.** 그렇게 확정된 경로 **하나**를 따라가며 진폭 a 를 만든다"
           "(`field_calculator.py`).", "",
           "그래서 광선은 **정찰병**이고, 답의 단위는 경로다. 이 구분이 §2 의 출발점이다.", "",
           "그림을 셋 잡고 들어간다. 비유는 **깨지는 자리**를 함께 적어야 쓸모가 있다 "
           "(근거 `outputs/report00_po_case.json:s0_fair_boundary.analogies_and_where_they_break`).", "",
           table(["비유", "그래서 맞는 것", "⚠ 이 비유가 깨지는 자리"], [
               ["Sionna 의 표면 처리는 **거울 한 장**이다",
                "반사 세기(Fresnel)도 방향도 맞다",
                "거울은 각도만 돌려준다 — 평판을 키워도 진폭이 그대로인 것이 그 뜻이다(§3)"],
               ["PO 표면적분은 **조명면에 붙은 작은 안테나들의 합**이다",
                "점마다 위상이 더해지므로 모양이 바뀌면 보강·상쇄가 바뀐다 — σ 가 여기서 창발한다",
                "그 작은 안테나의 세기를 국소 평면 반사로 정한다. 특징 폭이 파장 아래로 가면 "
                "그 가정이 깨진다(§6 의 무릎)"],
               ["SBR 은 **손전등으로 비추고 빛이 닿은 자리만 세는 것**이다",
                "자기가림이 공짜로 처리된다 — 빛이 닿은 면만 세면 된다",
                "손전등은 모서리에서 휘는 빛과 몸통을 감아 도는 빛을 빼놓는다 — "
                "전자가 PTD, 후자가 크리핑파다(§8)"],
           ])),

        md("### Sionna 가 정확히 계산하는 것 — 먼저 이것부터", "",
           table_from(f"{ANA}:item9_verdict.can_do",
                      [("메커니즘", "항목"), ("코드", "근거"), ("무엇을 어떻게", "설명_ko")])),

        md("### 필드 계산의 식 — 경로 하나가 진폭 하나가 되는 자리", "",
           "`a = (안테나 패턴) × (경로 위 Jones 행렬들의 곱) × spreading_factor × λ/4π`", "",
           "기호를 하나씩. **Jones 행렬**은 전계를 (⊥, ∥) 2성분 복소 벡터로 보고 그것을 "
           "변환하는 2×2 행렬이고, 정반사에서는 대각 성분이 Fresnel 계수 r_te · r_tm 이다. "
           "**spreading_factor** 는 파면이 퍼지면서 진폭이 줄어드는 비율 [1/m] 이고, "
           "**λ/4π** 는 등방 안테나의 유효개구 λ²/4π 를 진폭 차원으로 옮긴 상수 [m] 다.", "",
           "반사 경로의 spreading_factor 는 `1/ray_tube_length` 하나로 끝난다"
           "(`field_calculator.py:323-326`). 왜 거리만으로 끝나는지가 이 편의 첫 유도다.", "",
           "점원에서 나온 구면파는 진폭이 1/r 로 준다. 이 파가 **평평한** 면에 부딪히면 "
           "반사파는 여전히 구면파이고 그 중심은 소스를 면에 대해 거울반사시킨 상(image)이다. "
           "상은 면 뒤 s′ 에 있으므로 반사점에서 s 를 더 간 수신점은 상으로부터 s′+s 이고, "
           "진폭은 1/(s′+s) — 정확히 `1/ray_tube_length` 다."),

        md("### 굽은 면이면 무엇이 더 붙는가 — 그리고 회절과 λ 의 자리", "",
           "일반 기하광학의 광선관 확산인자는 `A(s) = sqrt( ρ₁ρ₂ / ((ρ₁+s)(ρ₂+s)) )` 이고, "
           "ρ₁·ρ₂ 는 반사 **직후** 파면의 두 주곡률반경이다. 곡면 반사에서 이 ρ 는 입사 파면의 "
           "곡률과 **면의 주곡률**이 섞여 정해진다.", "",
           "면이 평평하면 면곡률 항이 0 이 되어 ρ = s′ 가 되고, 위 식이 s′/(s′+s) 로 붕괴한다 — "
           "여기에 소스에서 반사점까지의 1/s′ 를 곱하면 1/(s+s′) 다. "
           "**Sionna 는 이 일반 공식의 면곡률 0 특수해를 정확히 구현한다.** 면곡률 항을 채우려면 "
           "그 점에서 표면의 제2기본형식이 필요한데, 삼각형 메쉬는 면마다 곡률이 정의상 0 이라 "
           "그 항이 구성상 0 으로 남는다.", "",
           "회절 경로는 `1/sqrt(s·s′·(s+s′))` 로 갈라진다. 두 조각으로 읽으면 뜻이 보인다 — "
           "`(1/s′) × sqrt( s′/(s(s+s′)) )` 에서 앞은 모서리까지 오는 구면파의 평범한 확산이고, "
           "뒤가 UTD 표준 모서리 인자다. sqrt 가 붙는 이유는 모서리에서 나온 파가 켈러 원뿔을 "
           "따라 한 방향으로 **원통형**으로 퍼지기 때문이다.", "",
           "⚠ 마지막 λ/4π 를 보고 '파장이 들어가니 산란도 다루겠지' 라고 읽기 쉽다. 그 λ 는 "
           "**수신 안테나** 항이고, 표적의 전기적 크기 L/λ 는 이 식 밖에 있다."),

        md(*_fig(1, "f1",
                 "같은 광선엔진을 쓰는 두 계산은 표면에서 무엇이 갈라지는가?"), "",
           f"광선 수는 이 진폭에 들어가지 않는다 — 실행으로 확인했다. "
           f"{_n('exp_a_ray_count_sweep[0].samples_per_src', PRB, '{:,.0f}')} 발에서 "
           f"{_n('exp_a_ray_count_sweep[-1].samples_per_src', PRB, '{:,.0f}')} 발까지 "
           f"{_n('summary.ray_count_span', PRB, '{:.0f}')}배를 올려도 정반사 진폭 스프레드는 "
           f"{_n('summary.abs_a_spread_over_ray_count_db', PRB, '{:.1f}', 'dB')} 다.", "",
           "⭐ 공정하게 단서를 붙인다. 광선 수가 진폭에 **전혀** 안 들어가는 것은 정반사·투과·"
           "회절 경로에서 참이다.", "",
           "확산산란 경로에서는 다르다 — `solid_angle` 이 4π/N 으로 초기화돼 재질까지 실려 가고, "
           "진폭에 sqrt(fs · solid_angle) 로 곱해져 1/sqrt(N) 으로 스케일된다.", "",
           "그것이 몬테카를로 추정량의 올바른 정규화다 — 경로 하나는 작아지고 경로 개수가 N 에 "
           "비례해 늘어 총 전력이 수렴한다. 그 4π/N 은 **첫 상호작용에만** 살아 있고, 확산이 "
           "샘플링되는 순간 2π(반구 입체각)로 덮어써진다"
           "(근거 `item1_ray_shooting_and_dedup.d_ray_count_in_amplitude`)."),

        # ═══ §2 ════════════════════════════════════════════════════════════
        md("## §2. 그 수식에 없는 것 — 인자 여덟 개를 그대로 센다", "",
           table_from(f"{ANA}:item2_field_calculation_arguments.argument_inventory",
                      [("인자", None), ("무엇인가", "")], key_col="인자")),

        md("### 목록 밖에 있는 양들", "",
           table_from(f"{ANA}:item2_field_calculation_arguments.absent_quantities",
                      [("필드 갱신 인자 목록 밖에 있는 양", "")]), "",
           "여덟 인자 중 여섯은 방향(단위벡터·회전)이고 둘은 Fresnel 계수다. 더 결정적인 것은 "
           "호출부다 — `field_calculator.py:404-405` 가 `return_vertices=False` 로 "
           "**정점 좌표를 일부러 요청하지 않고** 법선만 가져온다. 삼각형 크기를 알 수 있는 "
           "유일한 통로가 그 자리에서 닫힌다."),

        md("### 정확히 말하는 법 — '무한평면 가정' 은 거친 요약이다", "",
           "Sionna 가 무한평면을 가정한다고 쓰면 반박당한다. 기하는 유한하고, 광선이 그 삼각형을 "
           "맞았는지는 Mitsuba 가 정확히 판정한다(가림·그림자는 제대로 작동한다).", "",
           "정확한 진술은 이것이다 — **광선이 면을 맞았는가는 유한 기하로 판정하고, 맞은 뒤 "
           "필드를 얼마나 바꿀지는 국소 평면파–평면경계 문제의 해로 계산한다.** "
           "즉 크기는 `yes/no` 에만 쓰인다. `how much` 는 국소 해가 정한다.", "",
           "기술보고서 원문이 그 층을 각각 못 박는다.", "",
           f"· 경로 기하 — {_n('G_exact_wording_infinite_surface.numbers.quote_path_geometry', EVD)}", "",
           f"· 계수 — {_n('G_exact_wording_infinite_surface.numbers.quote_coefficients', EVD)}", "",
           "· ⚠ 낱말 주의 — 기술보고서의 'locally planar' 는 **파(wave)** 에 붙는 말이다"
           "(p.50 “an incoming locally planar linearly polarized wave”). 표면에 대해서는 조건 없이 "
           "extend infinitely · of infinite size 라고 쓴다 "
           "(근거 `outputs/report00_evidence.json:G_exact_wording_infinite_surface.numbers.caution_locally`)."),

        md("### 단위가 이미 답을 말한다 — Γ 는 무차원, σ 는 m²", "",
           "반사계수 Γ 는 무차원이고 레이더단면적 σ 의 단위는 m² 다. 무차원을 아무리 정확히 "
           "계산해도 결과는 무차원으로 남는다. 면적은 **조명면 위의 면적분**에서만 들어온다.", "",
           "평판의 PO 공식 `σ = 4πA²/λ²` 는 `4π·[m²]²/[m]² = m²` 로 닫히는데, "
           "Sionna 의 정반사 진폭 `|a| = λ/(4π(R₁+R₂))` 는 `[m]/[m] = 1` 로 닫힌다 — "
           "면적 기호는 그 식 밖에 있다.", "",
           f"그래서 같은 PEC, 같은 정면면적 "
           f"{_n('C_same_material_different_shape.numbers.frontal_area_m2', EVD, '{:.4f}')} m², "
           f"같은 5G 밴드 "
           f"{_n('s4_limits.our_production_bands_vs_knee.nr_ghz', POC, '{:.1f}', 'GHz')} 에서 구는 "
           f"{_n('C_same_material_different_shape.numbers.sphere_sigma_dbsm', EVD, '{:.2f}', 'dBsm')}, "
           f"평판은 "
           f"{_n('C_same_material_different_shape.numbers.plate_same_area_sigma_dbsm', EVD, '{:.2f}', 'dBsm')} "
           f"다.", "",
           f"주파수를 두 배로 올리면 평판은 "
           f"{_n('C_same_material_different_shape.numbers.plate_sigma_df_db_per_octave', EVD, '{:+.2f}', 'dB')}/옥타브, "
           f"구는 "
           f"{_n('C_same_material_different_shape.numbers.sphere_sigma_df_db_per_octave', EVD, '{:+.2f}', 'dB')}/옥타브 "
           f"움직인다. 갈라지는 이유는 하나다 — "
           f"{_n('C_same_material_different_shape.formula.why_they_differ', EVD)}", "",
           *_fig(3, "f3", "같은 재질·같은 정면면적에서 모양만 바꾸면 σ 는 얼마나 갈라지는가?")),

        # ═══ §3 ════════════════════════════════════════════════════════════
        md("## §3. 실측 — 크기를 흔들어 보면 무엇이 움직이는가", "",
           f"빈 자유공간에 금속 평판 하나를 두고 변만 "
           f"{_n('A_plate_size_sweep.numbers.side_m[0]', EVD, '{:.1f}', 'm')} → "
           f"{_n('A_plate_size_sweep.numbers.side_m[-1]', EVD, '{:.1f}', 'm')} "
           f"(면적 {_n('A_plate_size_sweep.numbers.area_ratio_max', EVD, '{:.0f}')}배) "
           f"로 키운다. PO 단면적은 면적 dB 당 "
           f"{_n('A_plate_size_sweep.numbers.slope_sigma_db_per_area_db', EVD, '{:.2f}', 'dB')}씩, "
           f"총 {_n('A_plate_size_sweep.numbers.po_theory_span_db', EVD, '{:.2f}', 'dB')} 오른다.", "",
           f"같은 구간에서 path solver 의 표적 경로 진폭은 "
           f"{_n('A_plate_size_sweep.numbers.rt_span_db', EVD, '{:.1e}', 'dB')} 움직이고 "
           f"경로 수는 내내 "
           f"{_n('A_plate_size_sweep.numbers.n_paths_target_set_union[0]', EVD, '{:.0f}')}개다 — "
           f"예산 {len(fetch((EVD, '_meta.solver.budgets')))}단 · "
           f"시드 {len(fetch((EVD, '_meta.solver.seeds')))}개 · "
           f"깊이 {len(fetch((EVD, '_meta.solver.depths')))}단 "
           f"{_n('A_plate_size_sweep.numbers.n_cells', EVD, '{:.0f}')}셀 전부에서.", "",
           f"⭐ 그 진폭이 무엇인지도 같이 확인된다. RT 값은 이미지-소스 해석해와 "
           f"{_n('A_plate_size_sweep.numbers.rt_minus_image_source_max_abs_db', EVD, '{:.4f}', 'dB')} "
           f"안에서 맞는다. **엔진은 자기가 푸는 문제를 정확히 푼다.**", "",
           f"두 곡선이 만나는 자리는 "
           f"변 {_n('A_plate_size_sweep.numbers.side_m_where_rt_equals_po', EVD, '{:.2f}', 'm')} "
           f"한 점뿐이고, 그것은 우연이다.", "",
           *_fig(2, "f2", "표적을 키우면 무엇이 움직이고 무엇이 그대로인가?")),

        md("### 드론 메쉬에서는 정반사 경로가 자세 하나에서만 살아남는다", "",
           f"같은 실험을 기체 메쉬로 옮긴다. 삼각형을 "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[0]', EVD, '{:,.0f}')}개 → "
           f"{_n('B_facet_count_sweep.numbers.n_tri_per_level[-1]', EVD, '{:.0f}')}개"
           f"({_n('B_facet_count_sweep.numbers.n_tri_span_decades', EVD, '{:.2f}')} decade)로 "
           f"깎아도 실루엣은 유지된다. 그런데 "
           f"{_n('B_facet_count_sweep.numbers.spec_n_aspects', EVD, '{:.0f}')}자세 중 정반사 "
           f"경로가 존재하는 자세는 "
           f"{_n('B_facet_count_sweep.numbers.spec_n_aspects_nonzero_per_level[0]', EVD, '{:.0f}')}개다.", "",
           f"그 한 자세에서 진폭은 기여 면 개수를 따라 계단으로 떨어져 총 "
           f"{_n('B_facet_count_sweep.numbers.total_collapse_db', EVD, '{:.2f}', 'dB')} 무너진다 — "
           f"면 2→1 계단이 "
           f"{_n('B_facet_count_sweep.numbers.step_2to1_facet_db', EVD, '{:+.2f}', 'dB')} 로 "
           f"닫힌형 20·log₁₀(1/2) = "
           f"{_n('B_facet_count_sweep.numbers.theoretical_step_two_to_one_facet_db', EVD, '{:+.2f}', 'dB')} "
           f"에 붙는다.", "",
           f"⚠ 나머지 자세가 빈 이유는 따로 있다. 같은 자세에 확산을 켜면 "
           f"표적경유 경로가 자세당 "
           f"{_n('B_facet_count_sweep.numbers.hot_n_paths_min', EVD, '{:.0f}')}개 넘게 잡힌다. "
           f"비어 있는 것은 광선이 아니라 **거울 조건을 만족하는 삼각형**이다.", "",
           "### 반대 방향도 같은 뿌리 — 쪼개기만 해도 답이 부푼다", "",
           f"같은 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].side_m', EVD, '{:.0f}', 'm')} "
           f"평판을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[0]', EVD, '{:.0f}')}개 → "
           f"{_n('H_tessellation_changes_the_answer.numbers.per_side[1].n_tri[-1]', EVD, '{:.0f}')}개 "
           f"삼각형으로 **쪼개기만** 해도 코히어런트 전력이 "
           f"{_n('H_tessellation_changes_the_answer.numbers.max_inflation_db', EVD, '{:.2f}', 'dB')} "
           f"부푼다. 늘어난 경로들은 진폭 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].amp_spread_db', EVD, '{:.1f}', 'dB')} · "
           f"지연 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].tau_spread_ns', EVD, '{:.1f}', 'ns')} · "
           f"위상 산포 "
           f"{_n('H_tessellation_changes_the_answer.numbers.duplicate_path_forensics[0].phase_spread_deg', EVD, '{:.1f}', '°')} "
           f"인 **완전한 복사본**이고, 합은 20·log₁₀(N) 을 "
           f"{_n('H_tessellation_changes_the_answer.numbers.coherent_N_law_max_resid_db', EVD, '{:.4f}', 'dB')} "
           f"안에서 따른다. 격자 위치를 옮겨도 중복은 남는다"
           f"(`offset_removes_duplication` = "
           f"{_n('H_tessellation_changes_the_answer.numbers.offset_removes_duplication', EVD)}).", "",
           "메쉬를 깎으면 무너지고 쪼개면 부푼다. 두 방향이 같은 뿌리에서 나온다 — "
           "**답의 단위가 면적이 아니라 경로라서** 면 수가 곧 답이 된다."),

        # ═══ §4 ════════════════════════════════════════════════════════════
        md("## §4. 할 수 있는 것과 없는 것 — 결정표", "",
           "판별 기준은 두 문장이다.", "",
           "**① 표적 산란량이 비(比)를 취할 때 상수로 소거되는가.** 소거되면 표적 모델 없이도 "
           "답이 선다. **② 결론이 절대 dBsm·dB 를 인쇄해야 하는가.**", "",
           "이 두 물음이 실험을 네 칸으로 가른다.", "",
           table_from(f"{DEC}:zones",
                      [("칸", "id"), ("표적 항이 소거되는가", "x_cancels"),
                       ("절대값이 필요한가", "y_absolute"), ("그래서 무엇을 쓰나", "tool_en")]), "",
           f"바닥 문장은 레이더 방정식 자신의 것이다 — {_n('footer_en', DEC)}"),

        md(*_fig(4, "f4", "두 물음을 던지면 각 실험은 어느 칸에 앉는가?"), "",
           "### 오른쪽 절반 — 표적 항이 소거되는 칸", "",
           table_from(f"{DEC}:items", ITEM_COLS, order=RIGHT_HALF)),

        md("### 왼쪽 절반 — 표적 항이 답에 남는 칸", "",
           table_from(f"{DEC}:items", ITEM_COLS, order=LEFT_HALF), "",
           "⚠ 단서 하나. 소거 논증은 표적이 **한 방향에서** 조명될 때의 것이다.", "",
           "다중경로에서는 직접파와 바닥 반사가 서로 다른 방향에서 동시에 표적을 때리므로 "
           "표적 항이 방향마다 달라진다. 커널의 "
           f"{_n('s2_our_kernel.derivation[7].statement', POC)} 가 보여주듯 "
           "각 조명 방향마다 다른 E 가 나온다. 그때는 오른쪽 칸의 실험도 왼쪽으로 이사한다."),

        # ═══ §4a ═══════════════════════════════════════════════════════════
        md("## §4a. 결정표를 한 사례로 시험한다 — 마이크로도플러", "",
           "날개가 도는 것을 보는 일은 **비율**만 필요하므로 표의 오른쪽 칸에 앉아야 한다. "
           "로터를 같은 각도씩 돌리고 매번 처음부터 다시 계산한 세 팔을 나란히 놓았다 — "
           "거리·자세·재질·주파수가 전부 같고, ③ 은 널 대조다(구는 어느 방향에서 봐도 같은 "
           "모양이라 변조가 원리적으로 0 이다).",
           *_fig(5, "f5", "같은 로터를 두 엔진으로 돌리면 무늬가 닮는가, 그리고 구는 조용한가?"),
           "| 기체 | ① Sionna | ② 우리 PO 커널 | ③ 같은 부피의 구 |",
           "|---|---|---|---|",
           f"| DJI Mini 2 | {_n('rows[0].ptp_sionna_db', MDP, '{:.2f}', 'dB')} | "
           f"{_n('rows[0].ptp_po_db', MDP, '{:.2f}', 'dB')} | "
           f"**{_n('rows[0].ptp_sphere_db', MDP, '{:.2f}', 'dB')}** |",
           f"| DJI Matrice 4E | {_n('rows[1].ptp_sionna_db', MDP, '{:.2f}', 'dB')} | "
           f"{_n('rows[1].ptp_po_db', MDP, '{:.2f}', 'dB')} | "
           f"**{_n('rows[1].ptp_sphere_db', MDP, '{:.2f}', 'dB')}** |",
           "⭐ ①②의 무늬가 닮고 ③ 이 검게 남는다 — **Sionna 는 도는 기하의 왕복 위상을 따라간다**.", "",
           f"⚠ 다만 세기의 출처가 다르다. 자세×로터위상 "
           f"{_n('specular_census.total.n_cells', MDP, '{:,.0f}', '칸')} 전수에서 Sionna 의 거울반사는 "
           f"{_n('specular_census.total.n_with_specular', MDP, '{:.0f}', '칸')}(전부 짐벌 렌즈면)이고, "
           f"프로펠러에서는 {_n('specular_census.total.n_with_prop_specular', MDP, '{:.0f}', '칸')} 이다"
           f"(대조 금속평판은 경로 {_n('specular_census.plate_control.n_paths', MDP, '{:.0f}', '개')}로 정상). "
           f"위상은 Sionna 가, 세기는 PO 커널이 맡는 이유가 여기 있다 — 단서는 "
           f"`{MDP} : caveats_ko` 에 넷으로 적었다."),

        # ═══ §5 ════════════════════════════════════════════════════════════
        md("## §5. 그래서 왜 PO 인가 — 다섯 갈래의 지도", "",
           table_from(f"{POC}:s1_alternatives.alternatives",
                      [("방법", "method"), ("무엇을 푸는가", "what_it_solves")]), "",
           f"⭐ ②의 위치를 정확히 적는다. {_n('s2_our_kernel.same_methodology_as.statement', POC)}"),

        md("### 비용과 정확도 — 그리고 게재된 반론 하나", "",
           f"완전파는 정확도의 과녁이다. 우리 2D EFIE MoM 자체검사는 정확 원기둥 고유함수해 대비 "
           f"{_n('s3_validation.layer3_thin_plate_2d_mom.mom_selftest_worst_db', POC, '{:.5f}', 'dB')} "
           f"다.", "",
           f"그 대신 비용이 표를 못 만들게 한다. 게재본 문장 그대로 — "
           f"{_n('s1_alternatives.alternatives[0].cost_quote_mlfmm', POC)}", "",
           f"우리 커널은 자세 하나(방위·고도 한 점 × 반송파 하나 → σ 한 값)에 중앙값 "
           f"{_n('s1_alternatives.ours_runtime.ours_per_pose_ms_median', POC, '{:.1f}', 'ms')} "
           f"다. 같은 `RTX 4090`, 같은 챔버 씬에서 스톡 `sionna.rt.PathSolver` 전파 해가 "
           f"{_n('s1_alternatives.stock_sionna_same_card.stock_sionna_ms_median', POC, '{:.1f}', 'ms')} "
           f"이므로 하드웨어 변수는 여기서 제거된다(⚠ 재는 양은 서로 다르다 — 전파 경로 대 σ).", "",
           f"⚠ 반론도 그대로 싣는다 — "
           f"{_n('s1_alternatives.cascade_cost_objection._the_objection', POC)}", "",
           f"우리 구현에서 PO 적분은 광선캐스팅의 "
           f"{_n('s1_alternatives.cascade_cost_objection.our_po_over_rt', POC, '{:.1f}')}배다 — "
           f"적분이 아직 호스트 numpy 라서다.", "",
           f"게재된 유일한 GPU 커널 분해(SagittaSBR)는 같은 "
           f"캐스케이드를 광선발사의 "
           f"{_n('s1_alternatives.cascade_cost_objection.sagitta_po_over_raylaunch_A100_fp32', POC, '{:.1%}')} "
           f"로 적는다. 절반은 우리 몫이다."),

        # ═══ §6 ════════════════════════════════════════════════════════════
        md("## §6. 우리 PO 는 납득 가능한 수준인가 — 검증 3층과 자기검사 2건", "",
           f"분해가 먼저다. {_n('s3_validation._the_decomposition', POC)}", "",
           table(["층", "과녁", "무엇을 재나", "결과"], [
               ["①",
                f"해석 PO 구 (kr "
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_kr_min', POC, '{:.0f}')}~"
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_kr_max', POC, '{:.0f}')} · 입사 "
                f"{_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_n_incidence', POC, '{:.0f}')}방향)",
                "커널 구현",
                f"최대 {_n('s3_validation.layer1_analytic_po_convergence.kr_sweep_max_abs_db_vs_po_div16', POC, '{:.3f}', 'dB')}"],
               ["②", "PEC 구 Mie 정확해", "PO 라는 모형",
                f"ka=1 에서 {_n('s3_validation.layer2_pec_sphere_mie.po_minus_mie_at_ka1_db', POC, '{:+.2f}', 'dB')}, "
                f"격자 {_n('s3_validation.layer1_analytic_po_convergence.sphere_ka1_grid_refine_factor', POC, '{:.0f}')}배 조여도 "
                f"{_n('s3_validation.layer2_pec_sphere_mie.improvement_from_refining_grid_db', POC, '{:+.3f}', 'dB')} 이동 · "
                f"광학영역 산포 {_n('s3_validation.layer2_pec_sphere_mie.kr_sweep_std_pct_vs_mie_kr_ge30_div16', POC, '{:.2f}', '%')}"],
               ["③", "얇은 띠 2D EFIE MoM", "가는 특징",
                f"가장 가는 시험 폭에서 TM {_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_tm_at_0p15lam_db', POC, '{:+.2f}', 'dB')} · "
                f"TE {_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')} "
                f"(참값 자체가 편파로 {_n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')} 갈린다)"],
               ["+", "PEC 이면각 닫힌형 8πa²b²/λ²", "다중반사 위상",
                f"2-bounce 최대 {_n('s3_validation.layer4_dihedral_multibounce.max_abs_err_2bounce_db', POC, '{:.3f}', 'dB')}"],
               ["+", "상반성 σ(û_i,û_s)=σ(û_s,û_i)", "정리 위반 = 모형오차",
                f"기체 최악 {_n('s3_validation.layer5_reciprocity_selfcheck.drone_worst_violation_db', POC, '{:.2f}', 'dB')} "
                f"(같은 검사를 인쇄한 선행 0편)"],
           ])),

        md("### ⚠ 한계는 정면으로 — PO 무릎과 우리 세 밴드", "",
           f"무릎의 정의는 «{_n('s4_limits.po_validity_knee_rule', POC)}» 이고, 그 아래로 "
           f"내려가려면 특징 폭이 "
           f"{_n('s4_limits.po_validity_knee_a_over_lambda', POC, '{:.3f}')}λ 이상이어야 한다. "
           f"그 무릎을 주파수로 옮기면 동체는 "
           f"{_n('s4_limits.feature_knee_frequencies.body_81p51mm_ghz', POC, '{:.2f}', 'GHz')}, "
           f"팔뿌리는 "
           f"{_n('s4_limits.feature_knee_frequencies.arm_root_45mm_ghz', POC, '{:.2f}', 'GHz')}, "
           f"블레이드는 "
           f"{_n('s4_limits.feature_knee_frequencies.prop_blade_13p78mm_ghz', POC, '{:.2f}', 'GHz')} "
           f"에서야 통과한다. 우리 생산 밴드는 LTE "
           f"{_n('s4_limits.our_production_bands_vs_knee.lte_ghz', POC, '{:.3f}', 'GHz')} · 5G "
           f"{_n('s4_limits.our_production_bands_vs_knee.nr_ghz', POC, '{:.1f}', 'GHz')} · WiFi "
           f"{_n('s4_limits.our_production_bands_vs_knee.wifi_ghz', POC, '{:.2f}', 'GHz')} 이므로, "
           f"**동체를 뺀 모든 특징이 무릎 아래에 있다.**", "",
           f"절대 σ 에는 격자 불확도도 함께 붙는다 — λ/16 서브셀 디더 산포 "
           f"{_n('s2_our_kernel.grid_dither.dither_spread_div16_db', POC, '{:.2f}', 'dB')} 다. "
           f"그리고 저대역 판정의 라벨 "
           f"`{_n('s4_limits.adversarial_verdict_verbatim.attacked_verdict_label', POC)}` 에 대한 "
           f"적대검증 판정은 "
           f"`{_n('s4_limits.adversarial_verdict_verbatim.adversarial_verdict', POC)}` 다. "
           f"살아남은 것은 표본화 배제뿐이고, 정직한 라벨 세 장은 "
           f"`{' · '.join(fetch((POC, 's4_limits.adversarial_verdict_verbatim.honest_labels')))}` 다 — "
           f"PO 한계는 **부호만** 확인됐고 크기 귀속은 아직 열려 있다.", "",
           f"부호는 한 방향을 가리킨다. {_n('s4_limits.our_production_bands_vs_knee.sign_of_the_error', POC)}"),

        # ═══ §7 ════════════════════════════════════════════════════════════
        md("## §7. 선행에서 무엇을 빌렸나", "",
           table_from(f"{POC}:s5_prior_work.already_borrowed",
                      [("빌린 것", "what"), ("어디서", "from"), ("그것이 사 준 것", "what_it_bought")])),

        md("### 아직 안 빌린 것 — 순위와 값", "",
           table_from(f"{POC}:s5_prior_work.not_yet_borrowed",
                      [("순위", "rank"), ("무엇을", "what"), ("어디서", "from"), ("비용", "cost")]), "",
           f"맨 위 두 줄이 이 편의 다음 단계와 같다 — 유효성 바닥을 기체 × 밴드 표로 인쇄하는 "
           f"일과, 정준체를 캠페인 패드에 올려 절대 σ 에 처음으로 실측 검사를 붙이는 일이다. "
           f"의도적으로 안 빌린 것도 셋이다 — "
           f"«{_n('s5_prior_work.deliberately_not_borrowed[1].what', POC)}» 가 그중 하나이고, "
           f"이유는 도구가 다르다는 것이다: D 는 σ 가 아니라 경로계수를 만들고, wedge 각을 "
           f"인접 두 면의 법선에서 읽으므로 면분할된 셸에서 그 각은 기체의 성질이 아니라 "
           f"**우리 메싱의 성질**이 된다."),

        # ═══ §8 ════════════════════════════════════════════════════════════
        md("## §8. 아직 못 하는 것 — 열린 항목과 그 크기", "",
           table(["열린 항목", "현재 상태", "크기"], [
               ["편파", "면적분이 스칼라다 — 한 채널의 σ 를 낸다",
                f"가장 가는 시험 폭에서 참값이 TM−TE "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')} 로 갈린다"],
               ["모서리 프린지(PTD)", "배선은 있고 생산 경로는 ptd=False 다",
                f"PTD 를 켜면 TE 가 "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')} → "
                f"{_n('s3_validation.layer3_thin_plate_2d_mom.po_ptd_minus_te_at_0p15lam_db', POC, '{:+.2f}', 'dB')} 로 벌어진다"],
               ["2회 이상 다중반사", "생산 σ 는 1-bounce 다",
                f"이면각에서 1-bounce "
                f"{_n('s3_validation.layer4_dihedral_multibounce.a03_sbr_1bounce_dbsm', POC, '{:.2f}', 'dBsm')} ↔ "
                f"2-bounce {_n('s3_validation.layer4_dihedral_multibounce.a03_sbr_2bounce_dbsm', POC, '{:.2f}', 'dBsm')}"],
               ["크리핑파·표면파", "우리 커널과 Sionna 가 같은 자리에 선다 — GO/UTD 계열 고주파 근사의 바깥이다",
                "매끄러운 볼록체 그림자 경계를 감아 도는 성분"],
               ["전방산란 `β→180°`", "조명 게이트와 수신 게이트가 상호배타라 σ ≡ 0 이 된다",
                "주장 창을 후방~중간 바이스태틱각으로 못박는다"],
               ["생산 경로의 참값 대조", "참값 앵커는 penetrate=False · |Γ|=1 · 볼록이다",
                "생산은 penetrate=True · 재질 Γ · 자기가림 · 1-bounce 다"],
               ["테셀레이션 축", "메쉬 사다리는 앵커 물체 두 점에서 돌렸다",
                f"같은 평판을 쪼개기만 해도 "
                f"{_n('H_tessellation_changes_the_answer.numbers.max_inflation_db', EVD, '{:.2f}', 'dB')} 부푼다"],
               ["회전 프로펠러 도플러", "Sionna 의 Paths.doppler 는 객체당 강체 속도 1벡터다",
                "부품별 위상은 우리 커널의 복소 E 에서 온다"],
           ])),

        # ── 다음 단계 ───────────────────────────────────────────────────────
        next_steps([
            ("공개된 세 유효성 바닥을 기체 × 밴드 표로 인쇄한다",
             "'전기적 소형' 이 고백에서 표가 되고, 어느 기체·어느 밴드가 공개 바닥 아래인지가 "
             "행 단위로 확정된다",
             "`benchmark/verify_sbr_kr_sweep.py` → 02편 §3"),
            ("정준체(구·원통)를 캠페인 패드에 올려 우리 커널과 같은 자로 잰다",
             "절대 σ 에 처음으로 실측 검사가 붙는다 — 레벨이 자체 앵커를 갖는다",
             "06편 §2 측정 설계"),
            ("PO 면적분을 편파 있는 커널로 올린다",
             f"가장 가는 시험 폭에서 참값이 갈라지는 "
             f"{_n('s3_validation.layer3_thin_plate_2d_mom.tm_minus_te_at_0p15lam_db', POC, '{:.2f}', 'dB')} 가 "
             f"우리 σ 의 어느 쪽 오차인지가 결정된다",
             "`src/rcs_sbr.py` → 이 편 §6"),
            ("드론 본체에서 재테셀레이션 사다리를 돌린다",
             "적대검증이 무경계로 남긴 기하 축(C)에 크기가 붙는다",
             "`benchmark/facet_mechanism.py` → 이 편 §3"),
            ("다중경로 기하에서 표적 항이 소거되는지를 직접 잰다",
             "결정표 오른쪽 칸의 실험이 챔버 안에서도 그 칸에 남는지가 확정된다",
             "이 편 §4 결정표 → 05편 검출 결과"),
            ("PO 적분을 디바이스 커널로 내린다",
             f"캐스케이드 반론의 비율 "
             f"{_n('s1_alternatives.cascade_cost_objection.our_po_over_rt', POC, '{:.1f}')}배가 "
             f"게재된 GPU 분해 수준으로 내려가는지가 결정된다",
             "`src/rcs_sbr.py` → 이 편 §5"),
        ]),
    ]


if __name__ == "__main__":
    rep = build_notebook(NB_OUT, blocks(), strict=True)
    print(f"\n→ {os.path.relpath(NB_OUT, _ROOT)}  "
          f"(md {rep['md_cells']}/{rep['caps']['md_cells']} · "
          f"code {rep['code_cells']} · 그림 {rep['figures']}/{rep['caps']['figures']} · "
          f"출처태그 {rep['provenance_tags']}개 · 부정문 {rep['n_negatives']} · "
          f"완충어 {rep['n_hedges']} · 권고 {len(rep['advisories'])}건)")
