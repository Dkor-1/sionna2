# -*- coding: utf-8 -*-
"""
make_readme.py — README.md 를 편성에서 직접 짓는다
==========================================================================================
편이 8 → 78 이 되면서 README 를 손으로 유지하면 반드시 어긋난다. 그래서 목차를
`report_registry`(= 계획 + 지어진 노트북의 H1)와 `outputs/reports_index.json` 에서
**읽어서** 만든다. 편을 하나 더 지으면 이 스크립트를 다시 돌리는 것으로 끝난다.

산출
    README.md

⭐ 출처는 각주다. 리포트와 같은 규약이고, GitHub 이 `[^n]` 을 그대로 각주로 렌더한다.
   숫자는 `report_style.num()` 이 JSON 을 열어 대조한 값이다 — 손으로 친 숫자가 없다.

실행 (색인이 먼저다)
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_reports_index.py
    PYTHONPATH=src ~/.venvs/py312/bin/python src/make_readme.py
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import report_style as RS                                              # noqa: E402
from report_registry import PARTS, REPORTS                             # noqa: E402
from report_style import num                                           # noqa: E402

OUT = os.path.join(ROOT, "README.md")
IDX = "outputs/reports_index.json"

#: 부 소개 한 줄 — 그 부가 무엇을 해냈는지. 물음(`PARTS[k]["question"]`)과 짝이다.
PART_LEAD = {
    0: "읽는 목적이 셋이라 진입 경로도 셋이다. 여기서 갈라진다.",
    1: "Sionna RT 설치본을 인자 목록까지 해부해, 광선이 면을 맞았을 때 무엇이 계산되고 "
       "무엇이 계산되지 않는지를 확정했다. 표적 산란이 별도 항이 되는 자리가 여기서 정해진다.",
    2: "게재본 16편이 표적 서명을 어디서 조달했는지 전문으로 판정하고, 그 조달처가 사 준 "
       "주장의 크기를 카탈로그로 만들었다.",
    3: "기체 7종을 제원과 제조사 CAD 치수에서 세우고, 외형이 실물과 얼마나 맞는지를 사진 "
       "IoU·CAD 치수·실물 스캔 세 자로 쟀다.",
    4: "광선으로 조명면을 찾고 그 위에서 부품별 재질 PO 를 적분하는 커널을, 닫힌형 기준해 "
       "셋과 맞대 구현오차와 모형 간극을 따로 쟀다.",
    5: "σ 의 주파수 기울기만 공개 측정에서 받고 레벨과 각패턴은 우리 출력으로 두었다. 그 "
       "판정을 눈감기 대조·대조군·사전등록 채점으로 때렸다.",
    6: "드론을 얼마나 거칠게 그려도 되는지를 사다리로 물었다 — 몸통은 진짜 CAD 로 두고 "
       "프로펠러만 갈아 끼운 축이 답할 자격이 있는 유일한 축이다.",
    7: "로터를 돌려가며 시간표본마다 다시 추적해, 마이크로도플러 무늬를 정하는 것이 "
       "회전수·가림·자세임을 단일축으로 갈랐다.",
    8: "상시 기준신호를 세 표준의 자원격자에서 세우고, 조명원을 고르는 대가를 dB 원장으로 "
       "닫았다.",
    9: "수신 신호가 판정이 되기까지의 사슬을 세우고, CFAR 문턱을 경험 Pfa 로 교정했다.",
    10: "같은 표적·같은 기하·같은 교정문턱에서 세 조명원의 검출거리를 앵커 σ 위에서 쟀다.",
    11: "X410 으로 교정된 σ 를 얻는 세션 설계와, 어느 측정이 어느 주장을 결판내는지를 "
        "수치로 고정했다.",
}


def _rows() -> list[dict]:
    with open(os.path.join(ROOT, IDX), encoding="utf-8") as f:
        return json.load(f)["reports"]


def _slug(k: int) -> str:
    return f"부-{k}-" + PARTS[k]["name"].replace(" ", "-")


def _ref(anchor: str, short: bool = True) -> str:
    r = REPORTS[anchor]
    t = r["short"] if short else r["title"]
    return f"[{r['no']} «{t}»](reports/{r['file']})"


#: 읽기 경로 — 편 00 과 같은 앵커 목록을 쓴다(정본은 `src/build_part00_map.py`).
sys.path.insert(0, _HERE)
from build_part00_map import PATH_FAST, PATH_TRUST                     # noqa: E402


def _footnotes(text: str) -> str:
    """본문의 `값 ⟨파일 : 키⟩` 를 `값[^n]` 으로 바꾸고 문서 끝에 각주 정의를 붙인다.

    GitHub 마크다운이 `[^n]` / `[^n]: …` 를 각주로 렌더한다 — 리포트와 같은 규약이다.
    """
    order: list[tuple[str, str]] = []
    seen: dict[tuple[str, str], int] = {}

    def mark(m: re.Match) -> str:
        key = (m.group(1).strip(), m.group(2).strip())
        n = seen.get(key)
        if n is None:
            order.append(key)
            n = seen[key] = len(order)
        return f"[^{n}]"

    text = RS._PROV_PARTS.sub(mark, text)
    text = re.sub(r"(\[\^\d+\])\(", r"\1 (", text)
    if not order:
        return text
    L = ["", "---", "", "## 출처", "",
         "위 숫자에 붙은 `[^n]` 은 그 값이 온 JSON 파일과 키다. 값은 이 문서를 만들 때 "
         "JSON 을 다시 열어 채웠다.", ""]
    for n, (p, k) in enumerate(order, 1):
        L.append(f"[^{n}]: `{p}` : `{k}` = {RS._resolve_cite(p, k)}")
    return text + "\n".join(L) + "\n"


def build() -> str:
    rows = _rows()
    by_part = {k: [r for r in rows if r["part"] == k] for k in PARTS}
    n_rep, n_fig = len(rows), sum(len(r["figures"]) for r in rows)

    L: list[str] = []
    A = L.append

    A("<!-- 생성물 — `src/make_readme.py` 가 편성에서 읽어 쓴다. "
      "손으로 고치지 말고 그 파일을 고쳐라. -->")
    A("")
    A("# sionna2 — 통신신호를 조명원 삼는 패시브 바이스태틱 드론 탐지 시뮬레이터")
    A("")
    A("셀이 이미 켜 두는 상시 신호(WiFi · LTE · 5G NR)를 조명 삼아 드론을 탐지하는 패시브")
    A("바이스태틱 레이더를, Sionna RT 2.0.1 위에서 자유공간 기하로 끝까지 시뮬레이션한다.")
    A("표적 산란은 Sionna 의 Mitsuba/OptiX 광선엔진으로 면별 가림을 풀고 그 조명면 위에서")
    A("부품별 재질 PO 를 적분해 만든다. σ 의 **주파수 의존성**은 공개 측정(Das)에 맞추고,")
    A("**자세 패턴과 절대 레벨은 우리 PO 출력**이다.")
    A("")
    A(f"보고서는 **편 {n_rep}개 · 부 {len(PARTS)}개** 다. 한 편이 중심 메시지 하나를 들고,")
    A("**편 제목이 곧 그 편의 결론 문장**이다 — 목차를 읽는 것이 결론을 읽는 것이다.")
    A("")

    # ── 읽기 경로 ────────────────────────────────────────────────────────────
    A("## 어디부터 읽어라")
    A("")
    A(f"편 {n_rep}개를 처음부터 읽지 않는다. **읽는 목적이 셋이면 읽는 순서도 셋**이고,")
    A(f"그 갈림길이 [편 00 «읽는 목적이 셋이면 읽는 순서도 셋이다»](reports/00_map.ipynb) 다.")
    A("")
    A("| 무엇을 하려는가 | 어디로 | 얼마나 |")
    A("|---|---|---|")
    A("| 이 저장소가 무엇을 해냈는지만 알고 싶다 | ↓ **① 빨리 훑기** | 30분 |")
    A("| 판정을 검사하려 한다(심사·적대검증) | ↓ **② 왜 믿을 수 있나** | 2시간 |")
    A("| 숫자를 재생산하려 한다 | [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — "
      "편 → 명령 → 출력 → 소요 | 리포트를 안 읽는다 |")
    A("| 원고에 옮기려 한다 | [`docs/paper/`](docs/paper/README.md) — 조각마다 "
      "«어느 편에서 왔나» 가 붙어 있다 | — |")
    A("")
    A("### ① 빨리 훑기 — 30분")
    A("")
    A("부마다 결론 편 하나씩이다. **오른쪽 칸이 그 편의 결론 문장 전체**이므로, 제목만 읽어도")
    A("한 바퀴가 돈다. 막히는 데서만 그 편을 연다.")
    A("")
    A("| 부 | 편 | 이 편의 결론 |")
    A("|---|---|---|")
    for a in PATH_FAST:
        r = REPORTS[a]
        A(f"| {r['part']} | [{r['no']}](reports/{r['file']}) `{a}` "
          f"| {RS._md_escape_cell(r['title'])} |")
    A("")
    A("### ② 왜 믿을 수 있나 — 2시간")
    A("")
    A("검증·대조·반증 편만 모았다. 뼈대는 **눈감기 대조 · 사전등록 채점 · PREMATURE 판정 ·")
    A("널 교정** 넷이다 — 우리가 틀렸을 수 있는 자리를 우리가 먼저 때린 편들이다.")
    A("")
    A("| 부 | 편 | 무엇을 때렸나 |")
    A("|---|---|---|")
    for a in PATH_TRUST:
        r = REPORTS[a]
        A(f"| {r['part']} | [{r['no']}](reports/{r['file']}) `{a}` "
          f"| {RS._md_escape_cell(r['title'])} |")
    A("")
    A("---")
    A("")

    # ── 저장소가 한 일 ────────────────────────────────────────────────────────
    A("## 이 저장소가 한 일")
    A("")
    A("| 한 일 | 수치 | 어느 편 |")
    A("|---|---|---|")
    for what, value, anchor in _headline():
        A(f"| {what} | {value} | {_ref(anchor)} |")
    A("")
    A("---")
    A("")

    # ── 부 목차 ──────────────────────────────────────────────────────────────
    A("## 목차 — 부 12개")
    A("")
    A("부마다 답하는 물음이 하나다. 아래 표의 «편» 칸은 그 편의 **결론 문장** 그대로다.")
    A("")
    A("| 부 | 이름 | 이 부가 답하는 물음 | 편 |")
    A("|---|---|---|---|")
    for k, p in sorted(PARTS.items()):
        sub = by_part.get(k) or []
        if not sub:
            continue
        span = f"{sub[0]['no']}~{sub[-1]['no']}" if len(sub) > 1 else sub[0]["no"]
        A(f"| [{k}](#{_slug(k)}) | {p['name']} | {p['question']} | {span} ({len(sub)}편) |")
    A("")

    for k, p in sorted(PARTS.items()):
        sub = by_part.get(k) or []
        if not sub:
            continue
        A(f"### 부 {k} «{p['name']}»")
        A("")
        A(f"**{p['question']}**")
        A("")
        A(PART_LEAD.get(k, ""))
        A("")
        A("| 편 | 이 편의 결론 | 그림 |")
        A("|---|---|---|")
        for r in sub:
            nfig = len(r["figures"])
            A(f"| [{r['no']}](reports/{os.path.basename(r['file'])}) `{r['anchor']}` "
              f"| {RS._md_escape_cell(r['title'])} | {nfig or ''} |")
        A("")

    A("---")
    A("")

    # ── 부록 · 규약 · 재현 ───────────────────────────────────────────────────
    A("## 부록 — 동결(유효하고, 새 작업은 넣지 않는다)")
    A("")
    A("| 위치 | 내용 |")
    A("|---|---|")
    A("| [`report_mesh/`](report_mesh) 8편 | 드론 메쉬 제작·검증 심화 가이드 |")
    A("| [`prior_work/`](prior_work) | 선행연구·오픈소스 조사 원자료 — 부 2 의 census 가 "
      "여기서 나온다 |")
    A("| [`OPENSOURCE.md`](OPENSOURCE.md) | 오픈소스 대체 지도(RadarSimPy 교차검증 · "
      "OpenISAC X410 실측) |")
    A("| `report0N_*.ipynb` (루트) | **옛 8편** — 재구성 전 원본이고 대조가 끝날 때까지 "
      "제자리에 둔다 |")
    A("")
    A("## 다시 만들기")
    A("")
    A("```bash")
    A("cd /home/yunjung/workspace/sionna2")
    A("PY=~/.venvs/py312/bin/python")
    A("")
    A("# ① 편 78개를 다시 조립한다 (계산 없음 · GPU 0장 · 수 초)")
    A("for f in src/build_part*.py; do PYTHONPATH=src $PY \"$f\"; done")
    A("")
    A("# ② 색인 · 재현 문서 · 논문 목차 · 지도 편 · README")
    A("PYTHONPATH=src $PY src/make_reports_index.py")
    A("PYTHONPATH=src $PY src/build_part00_map.py")
    A("PYTHONPATH=src $PY src/make_legacy_map.py")
    A("PYTHONPATH=src $PY src/make_readme.py")
    A("")
    A("# ③ 편 사이 참조 검사 — 끊긴 링크·없는 앵커·안 열리는 출처를 센다")
    A("PYTHONPATH=src $PY benchmark/check_report_links.py")
    A("")
    A("# ④ 숫자 자체를 다시 낸다 (GPU) — 어느 편의 어느 명령인지는 docs/REPRODUCE.md 에")
    A("PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py --list")
    A("PYTHONPATH=src:benchmark $PY benchmark/regen_mesh_dependents.py")
    A("```")
    A("")
    A("| | |")
    A("|---|---|")
    A("| Python | `~/.venvs/py312/bin/python` (3.12) — 이 한 env 로 전부 실행 |")
    A("| 핵심 | Sionna RT 2.0.1 · Mitsuba 3.8.0 · drjit 1.3.1 (OptiX GPU) · torch · "
      "numpy · trimesh + manifold3d |")
    A("| 노트북 커널 | `py312` |")
    A("| 실행 규약 | `PYTHONPATH=src:benchmark` 를 반드시 준다 |")
    A("")
    A("## 하우스 규약")
    A("")
    A("- **편 제목이 결론 문장이다.** «…다» 로 끝나는 평서문이고, 물음표로 끝나는 제목은")
    A("  `src/report_style.py` 가 막는다.")
    A(f"- **숫자는 손으로 치지 않는다.** 전부 `num()` 이 JSON 을 열어 값을 대조하고, 화면에는")
    A(f"  각주 `[^n]` 으로 찍힌다. 편 끝 «출처» 표의 값은 표를 만들 때 JSON 을 **다시 열어**")
    A(f"  채운 것이다(왕복 검사). 지금 편 {n_rep}개에 그림 {n_fig}장이 실려 있다.")
    A("- **논문 문장과 재현 절차는 리포트 밖에 산다** — 사용자 지시다. "
      "[`docs/paper/`](docs/paper/README.md) 와 [`docs/REPRODUCE.md`](docs/REPRODUCE.md).")
    A("- 각 편은 `한 일 / 결과 / 방법 / 재현` 으로 열고 `다음 단계` 표로 닫는다. "
      "«다음 단계» 는 한계 목록이 아니라 앞을 보는 행동이다.")
    A("- 그림 텍스트(제목·축·범례·주석)는 **영어**, 본문·주석·print 는 **한국어**.")
    A("- 분량 상한: 편당 마크다운 25셀 · 셀당 12줄 · 편당 그림 8장. **넘치면 내용을 줄이지 "
      "말고 편을 쪼갠다.**")
    A("")
    A("## 저장소 구조")
    A("")
    A("```")
    A("reports/NN_<anchor>.ipynb   ⭐본편 78편 (생성물) — 번호는 읽는 순서다")
    A("report_mesh/               부록 8편 (동결)")
    A("prior_work/                선행연구 조사 원자료")
    A("")
    A("src/")
    A("  build_part0N_*.py        ⭐편 생성기 — 서술의 원본. 계산은 없다")
    A("  build_part00_map.py      지도 편 + 읽기 경로의 정본")
    A("  make_reports_index.py    색인 · docs/REPRODUCE.md · docs/paper/README.md")
    A("  make_readme.py           이 파일을 만든다")
    A("  report_style.py          규약 강제(num()·각주·분량 상한·부정문 계수)")
    A("  report_registry.py       앵커 사전 — 편 사이 링크의 유일한 출처")
    A("  drones.py                ⭐표적 레지스트리 DRONES — 기종·제원의 유일한 출처")
    A("  materials.py             ⭐전파재질 단일 진리원 — Sionna RT 와 PO 가 둘 다 읽는다")
    A("  rcs_sbr.py               ⭐SBR+PO 커널 (Mitsuba 광선조준 + PO 표면적분)")
    A("  sigma_anchor.py          ⭐측정 앵커 재보정 σ=A(f)·B₁·B₂ + 미통제 항 원장")
    A("  waveforms*.py            WiFi/LTE/5G OFDM 합성 + Sionna PHY 대조")
    A("  passive_process.py       패시브 DSP: ECA → CAF 거리도플러 → CA-CFAR")
    A("  experiment_*.py          검출·자유공간 실험(GPU 몬테카를로)")
    A("  viz_*.py                 그림 (텍스트는 전부 영어)")
    A("")
    A("benchmark/")
    A("  check_report_links.py    ⭐편 사이 참조 전수 검사")
    A("  regen_mesh_dependents.py ⭐재생성 파이프라인 — 무엇을 어느 순서로 돌리나")
    A("  mie_pec_sphere.py        기준해 두 개(정확 Mie · 해석 PO) — 커널의 과녁")
    A("  verify_*.py              검증 하네스 (편이 읽는 verify_*.json 생산)")
    A("")
    A("outputs/                   *.json(숫자의 원본) · figures/ · reports_index.json")
    A("docs/                      REPRODUCE.md · paper/ · repro/ · SPECS.md · "
      "MEASUREMENT_PLAN.md")
    A("```")
    A("")
    A("## 별도 주제 — 코드는 그대로 있다")
    A("")
    A("| 주제 | 코드 |")
    A("|---|---|")
    A("| 반무향 챔버 환경 | `src/chamber.py` · `benchmark/verify_clutter_doppler.py` |")
    A("| 바닥 유령 표적 | `benchmark/verify_floor_ghost.py` · `src/experiment_ghost.py` |")
    A("")
    return _footnotes("\n".join(L))


def _headline() -> list[tuple[str, str, str]]:
    """저장소 헤드라인 — (한 일, 수치, 어느 편)."""
    KRS, DFX, ANC = ("outputs/sbr_kr_sweep.json", "outputs/sbr_defect_fixes.json",
                     "outputs/rcs_anchor.json")
    DER, CEN = "outputs/report02_derived.json", "outputs/prior_census.json"
    LED, CFR = "outputs/report03_illuminators.json", "outputs/verify_cfar.json"
    return [
        ("**광선엔진 안에서 산란을 적분한다** — Sionna 자체 Mitsuba/OptiX 로 first-hit 가림을 "
         "판정하고 조명면 위에서 부품별 재질 PO 를 적분한다",
         "`src/rcs_sbr.py:184` · `src/materials.py`", "kernel-what"),

        ("**커널을 기준해로 검증했다** — 해석 PO 구 대비 kr 1~100 전 구간",
         "최대 " + num(None, (KRS, "summary_div16.max_abs_db_vs_po"), "{:.3f}", "dB"),
         "kernel-vs-reference"),

        ("**다중반사 위상을 PEC 이면각 닫힌형 8πa²b²/λ² 와 맞췄다** — 변 길이 4점",
         "최대 " + num(None, (DFX, "d3_multibounce_phase.max_abs_err_db"), "{:.3f}", "dB"),
         "kernel-vs-reference"),

        ("**바이스태틱 출사 가시성을 넣었다** — 히트마다 수신기 방향으로 그림자 광선을 쏜다",
         "상반성 위반 최악 "
         + num(None, (DFX, "d2_exit_vis_effect_on_reciprocity.worst_without_exit_vis_db"),
               "{:.2f}") + " → "
         + num(None, (DFX, "d2_exit_vis_effect_on_reciprocity.worst_with_exit_vis_db"),
               "{:.2f}", "dB"), "bistatic-exit"),

        ("**σ 의 주파수 기울기를 측정에 정렬했다** — σ = A(f)·B₁·B₂ 에서 A(f) 의 **기울기만** "
         "측정, **절대 레벨과 B₁ 은 우리 PO 출력**",
         num(None, (ANC, "literature.mu_eps.das_phantom3_mono.mu_a"), "{:.3f}", "dB/GHz")
         + " · 평균 레벨이동 "
         + num(None, (DER, "anchor_modes.level_shift_abs_max_db"), "{:.2f}", "dB")
         + " · 정규화 각패턴 이동 "
         + num(None, (DER, "anchor.shape_invariance_max_abs_db"), "{:.1e}", "dB"),
         "anchor-mode"),

        ("**모드 선택의 대가를 수치로 적었다** — 레벨까지 앵커에 맞추려면 크기전이 법칙을 하나 "
         "골라야 하고, 그 선택 하나가 기체당 최대 이만큼을 정한다",
         "L² ↔ L⁴ 예측 차 최대 "
         + num(None, (DER, "anchor_modes.size_law_spread_max_db"), "{:.2f}", "dB"),
         "anchor-ledger"),

        ("**우리 σ 를 눈감고 내고 봉인을 풀었다** — 문헌 상수를 한 번도 안 읽은 경로로 Phantom 3 "
         "를 내고 별도 스크립트가 열었다",
         "사전등록 판정 "
         + num(None, ("outputs/das_fleet_validation.json", "prereg_judgement.verdict")),
         "fleet-prereg"),

        ("**CFAR 를 경험 Pfa 로 교정했다** — GPU 몬테카를로로 오경보 셀을 직접 세었다",
         num(None, (CFR, "meta.runtime_s"), "{:,.0f}", "s") + ", 명목 1e-4 에서 배율을 "
         "형상마다 다시 잰다", "cfar-calib"),

        ("**세 파형을 한 표적·한 검출기로 비교했다** — 점유·대역·PRF·λ² 를 dB 원장으로 닫았다",
         "점유 " + num(None, (LED, "occupancy_cost.value_db"), "{:.1f}", "dB"), "cost-ledger"),

        ("**기체 7종을 사진·제원에서 세우고 실물 CAD 와 맞댔다**",
         "메쉬 " + num(None, (DER, "mesh.n"), "{:.0f}", "종") + " · 삼각형 "
         + num(None, (DER, "mesh.n_tris_total"), "{:,.0f}", "개"), "mesh-vs-real"),

        ("**선행연구를 전문으로 판정했다** — 아카이브 PDF 41편 중 16편, 게재상태는 PDF 로 확정",
         "드론 메쉬에서 산란을 계산한 게재본 "
         + num(None, (CEN, "funnel.all.g3_mesh_scattering"), "{:.0f}", "편"),
         "census-published"),
    ]


def main() -> int:
    text = build()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    n_foot = len(re.findall(r"^\[\^\d+\]:", text, re.M))
    print(f"✅ README.md — {len(text):,}자 · 각주 {n_foot}개 · "
          f"편 {len(_rows())}개 · 부 {len(PARTS)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
