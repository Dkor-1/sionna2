# -*- coding: utf-8 -*-
"""
build_part13_engine_physics.py — 권 17 「엔진의 물리 스위치」의 조각 → reports/_parts/83~87_*.ipynb
==========================================================================================
권 17 은 스톡 PathSolver 의 굴절·회절·모서리회절·다중반사를 하나씩 켜서 **무엇이 결과를
만들었는지 귀속**한다. 편성은 `outputs/volumes_16_17_plan.json:volumes[1]` 이 정본이다.

    83 physics-single-axis   나딧 레벨을 올리는 스위치는 회절 하나다        ⭐헤드라인 절
    84 physics-denominator   AC/DC 하락은 분모가 커진 결과다
    85 physics-above-limit   물리를 켜면 날개끝 상한 위 에너지 몫이 커진다
    86 physics-deck-match    우리 팔과 8/11 덱 판의 STFT 상관
    87 budget-not-physics    광선 예산을 늘려도 레벨은 모이고 박자는 헤맨다

⭐ 이 빌더는 **읽기만** 한다 — 원장 JSON 과 이미 그려진 그림을 인용해 노트북을 조립한다.
   GPU 도 Sionna 도 부르지 않는다.

⚠ 조각은 **사람이 직접 읽는 문서가 아니다.** 사람이 읽는 것은 `src/build_volumes.py` 가
  조각을 이어 만든 권(`reports/17_physics-switches.ipynb`)이다.

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_part13_engine_physics.py
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (BREAK, ContractError, build_notebook,     # noqa: E402
                          caption, from_json, header, md, next_steps, num, table)
from report_registry import get as _get_old                         # noqa: E402


def ref_old(anchor: str, text: str) -> str:
    """옛 조각(78 편 시절 번호)을 가리키는 링크. 표시 글자는 여기서 고른다."""
    r = _get_old(anchor)
    return f"[편 {r['no']} «{text}»]({r['file']})"

# --------------------------------------------------------------------------- #
#  앵커 해결기 — 번호는 계획 JSON 이 정본이다
#  ⚠ 새 조각(78~87)은 옛 실행계획(`restruct_exec_plan.json`)에 없다. 그래서 형제 조각은
#    여기 지역 사전으로 풀고, 옛 조각은 `report_registry.ref()` 로 푼다
#    (`build_part11_measurement.py` 가 같은 방식을 쓴다).
# --------------------------------------------------------------------------- #
_PLAN = os.path.join(_ROOT, "outputs", "volumes_16_17_plan.json")


def _registry() -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    return {r["anchor"]: (str(r["no"]), r["title"]) for r in plan["parts"]}


REG = _registry()

#: 계획(78~87) 밖에서 이 파일이 하나 더 짓는 조각 — 권 17 의 마지막 절(범위 표).
EXTRA_PARTS = {
    "engine-claim-scope": ("88", "이 비교가 세우는 것은 el −90 한 자리의 스위치 귀속이고, "
                                 "절대 σ 는 산포 16.27 dB 로 미검증이다"),
}
REG.update(EXTRA_PARTS)

#: ⚠ 계획의 조각 80 은 `el-prediction-gap` 으로 적혀 있으나 그 자리에 지어진 조각은
#  `el-above-tip-limit`(권 16 절 3)이다. 계획 JSON 은 손대지 않고 여기서만 이름을 맞춘다.
#  같은 이유로 계획의 조각 81 `el-beat-vs-tip` 은 이 라운드에 지어지지 않았다 — 그 앵커로
#  링크를 걸면 없는 파일을 가리키므로, 이 파일은 그 자리를 조각 80 으로 보낸다.
REG["el-above-tip-limit"] = ("80", "물리 상한 위 누설은 우리 팔 0.26~15.65 %, "
                                   "스톡 PathSolver 두 예산 5.12~87.02 % 이고, "
                                   "그 위 끝은 평평한 스펙트럼이 받는 점수다")


def ref(anchor: str, short: str | None = None) -> str:
    """형제 조각을 가리키는 링크. `build_volumes.py` 가 권·절 주소로 다시 배선한다."""
    if anchor not in REG:
        raise ContractError(
            f"모르는 앵커: {anchor!r} — `{os.path.relpath(_PLAN, _ROOT)}:parts[]` 에 없다")
    no, title = REG[anchor]
    return f"[편 {no} «{short or title}»]({no}_{anchor}.ipynb)"


# --------------------------------------------------------------------------- #
#  근거 JSON — 전부 읽기 전용
# --------------------------------------------------------------------------- #
DP = from_json("outputs/diag_physics_paths_el-90.json")   # 스위치 단일축 분해
RT = from_json("outputs/rt_no_rcs_verify.json")           # 경로 수를 읽는 법

OUT = os.path.join(_ROOT, "reports", "_parts")
FIG = "../outputs/figures"
_SHARD_DIR = os.path.join(_ROOT, "outputs", "reports_index")

_SWPJ = "outputs/elevation_sweep_md.json"

# --------------------------------------------------------------------------- #
#  행 인용의 안정키 — `rows[i]` 의 i 는 병합마다 밀린다
#  ⭐행은 (engine, 앙각)으로 찾고, 인용에도 그 안정키를 함께 찍는다. 그래서 독자는
#    나중에 병합이 한 번 더 돌아도 팔 이름으로 같은 칸을 다시 찾는다.
# --------------------------------------------------------------------------- #
_ARM_BY_ROW: dict[str, str] = {}
_ROW_HEAD = re.compile(r"^(rows\[\d+\])")


def _arm_key(engine: str, el_deg: float) -> str:
    """다른 원장(`wideband_energy` 등)이 칸 이름으로 쓰는 표기 그대로 — `sionna_phys/el-15`."""
    return f"{engine}/el{el_deg:+.0f}"


def _mark_row(i: int, engine: str, el_deg: float) -> str:
    """행 하나를 안정키에 등록하고 `rows[i]` 를 돌려준다."""
    key = f"rows[{i}]"
    _ARM_BY_ROW[key] = _arm_key(engine, el_deg)
    return key


def cite_row(src, key: str, value=None, fmt=None, unit="") -> str:
    """앙각 스윕 원장 한 칸 — 인용에 `rows[i].<양> → <engine>/el<앙각>` 을 함께 찍는다."""
    text = src.num(key, value, fmt=fmt, unit=unit)
    m = _ROW_HEAD.match(key)
    arm = _ARM_BY_ROW.get(m.group(1)) if m else None
    return f"{text[:-1]} → {arm}⟩" if arm else text


def row_tag(key: str, path: str = _SWPJ) -> str:
    """값 없이 행 하나를 가리키는 태그 — 같은 안정키를 붙인다."""
    m = _ROW_HEAD.match(key)
    arm = _ARM_BY_ROW.get(m.group(1)) if m else None
    return f"⟨{path} : {key} → {arm}⟩" if arm else f"⟨{path} : {key}⟩"


def count_tag(what: str, path: str = _SWPJ) -> str:
    """행을 세어 쓴 수의 출처 — 어느 파일의 어느 배열을 어떻게 셌는지 적는다."""
    return f"⟨{path} : rows → {what}⟩"


def rows_of(engine: str) -> list:
    """그 팔의 행 전부 — 개수는 손으로 적지 말고 여기서 센다."""
    return [r for r in from_json(_SWPJ).get("rows") if r.get("engine") == engine]


def n_arm(engine: str) -> tuple[int, int]:
    """(그 팔의 행 수, 그중 `n_missing == 0` 인 행 수)."""
    rs = rows_of(engine)
    return len(rs), sum(1 for r in rs if not r.get("n_missing"))


def n_rows() -> int:
    """병합판 원장의 행 수 — 병합이 돌 때마다 늘어난다."""
    return len(from_json(_SWPJ).get("rows"))


# =========================================================================== #
#  조각 83 — 스위치 단일축                                        ⭐권 17 헤드라인
# =========================================================================== #
TITLE_83 = "나딧에서 레벨을 −130.78 dB 에서 −64.23 dB 로 올리는 스위치는 회절 하나다"


def _rise_db() -> float:
    """회절만 켠 판이 기준 판보다 몇 dB 위인가 — 두 원장 칸의 차."""
    return (float(DP.get("cases.회절만 켬.level_db"))
            - float(DP.get("cases.기준(지금까지의 실행).level_db")))


def blocks_83() -> list:
    lvl = "cases.{}.level_db"
    npm = "cases.{}.npaths_median"
    base, diff = "기준(지금까지의 실행)", "회절만 켬"
    return [
        header(
            num=83,
            title=TITLE_83,
            did="앙각 스윕이 두 엔진에 넘긴 물리 스위치를 소스에서 읽어 표로 적고, "
                "PathSolver 의 네 스위치를 하나씩만 켜서 나딧 레벨의 상승을 귀속했다.",
            results=[
                f"스윕이 돈 기준 판은 레벨 "
                f"{DP.num(lvl.format(base), -130.78, '{:.2f}', 'dB')} · 경로 중앙값 "
                f"{DP.num(npm.format(base), 11, '{:.0f}', '개')} 다.",

                f"회절만 켠 판은 {DP.num(lvl.format(diff), -64.23, '{:.2f}', 'dB')} 로 "
                f"올라가고, 네 스위치를 전부 켠 판도 "
                f"{DP.num(lvl.format('전부 켬 (--physics)'), -64.23, '{:.2f}', 'dB')} 로 "
                f"같은 자리에 선다.",

                f"굴절만 켠 판 "
                f"{DP.num(lvl.format('굴절만 켬'), -132.48, '{:.2f}', 'dB')} · 다중반사만 켠 판 "
                f"{DP.num(lvl.format('다중반사만 (depth 3)'), -130.76, '{:.2f}', 'dB')} · "
                f"모서리회절만 켠 판 "
                f"{DP.num(lvl.format('모서리회절만 켬'), -130.78, '{:.2f}', 'dB')} 는 기준 자리에 "
                f"머문다.",

                f"기준 실행의 투과 축에서는 우리 팔이 켠 물리가 하나 더 많다 — 우리 팔은 "
                f"`penetrate=True`, 그 PathSolver 팔은 `refraction=False` 다.",

                f"두 팔 다 거리 {DP.num('_meta.range_m', 10.0, '{:.0f}', 'm')} 의 실제 기하로 "
                f"위상을 준다 — 평면파 근사는 두 팔의 이번 설정 밖에 있다.",
            ],
            method=[
                ("우리 팔의 설정",
                 "`benchmark/elevation_sweep_md.py:134`~`135` 의 `sbr_field(…)` 호출 인자를 "
                 "그대로 읽었다 — `penetrate` 는 기본값 True(`src/rcs_sbr.py:1009`), `ptd` 는 "
                 "False, `range_m` 은 10 m 고정(`benchmark/elevation_sweep_md.py:74`)"),
                ("PathSolver 의 설정",
                 "`benchmark/elevation_sweep_md.py:176`~`183` 의 호출 인자. 스위치 넷은 "
                 "`--physics` 플래그 하나에 묶여 있어 팔이 두 갈래다 — 없이 돌면 "
                 "`max_depth=1`·굴절·회절·모서리회절 모두 끔, 주면 `max_depth=3` 에 셋 다 켬"),
                ("스톡 기본값과의 거리",
                 "Sionna 2.0.1 의 `PathSolver.__call__` 기본값은 `max_depth=3` · "
                 "`refraction=True` · `diffuse_reflection=False` 다"
                 "(`sionna/rt/path_solvers/path_solver.py:146`·`152`~`155`) — 이 스윕의 기준 "
                 "팔은 그 기본값에서 세 칸을 옮긴 설정이다"),
                ("스위치 귀속",
                 "`benchmark/diag_physics_paths.py:35`~`42` 가 자세·광선 예산·거리를 고정하고 "
                 "스위치 하나씩만 바꿔 여섯 판을 돌린 원장"),
                ("경로 수를 읽는 법",
                 "같은 엔진이 PEC 구와 챔버 판에서 낸 경로 수 — `outputs/rt_no_rcs_verify.json`"),
            ],
            repro=dict(
                cmd="PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                    "benchmark/diag_physics_paths.py -90 20",
                out="outputs/diag_physics_paths_el-90.json",
                runtime="여섯 판 × 자세 20 개 (GPU 1 장)",
                note="자세 수만 줄인 진단 판이다 — 광선 예산·거리·기체는 앙각 스윕 본판과 같다"),
        ),

        md("## 두 엔진에 실제로 넘어간 스위치", "",
           "엔진이 «할 수 있는 것»과 «이번에 한 것»은 다른 물음이다. 아래 표는 그 둘을 갈라 "
           "적는다 — 왼쪽 두 칸이 우리 팔(SBR + 물리광학), 오른쪽 두 칸이 스톡 PathSolver 다.", "",
           "낱말부터 푼다. **가림**은 앞면이 뒷면을 막는 것, **투과**는 플라스틱 셸을 지나 "
           "안쪽 금속(배터리·PCB)까지 세는 것, **쐐기 회절**은 실루엣 모서리에서 빛이 꺾여 "
           "도는 것, **다중반사**는 표적 안에서 두 번 이상 튀는 것이다."),

        md("## 스위치 대조표", "",
           table(["물리", "우리 팔이 담을 수 있나", "이번에 켰나",
                  "PathSolver 가 담을 수 있나", "이번에 켰나"],
                 [["가림", "담는다 — 첫 충돌만 채택(`src/rcs_sbr.py:1068`)", "켬",
                   "담는다 — 광선추적 그 자체", "켬"],
                  ["산란 표면적분(PO)", "담는다 — 조명면 적분(`src/rcs_sbr.py:1101`)", "켬",
                   "스톡에는 그 단계가 빠져 있다", "—"],
                  ["투과(셸 → 내부 금속)",
                   "담는다 — τ=1−|Γ|² 로 두 번째 패스(`src/rcs_sbr.py:1105`)", "켬",
                   "담는다 — `refraction`", "끔"],
                  ["쐐기 회절", "담는다 — PTD 프린지(`src/rcs_sbr.py:1112`)", "끔",
                   "담는다 — `diffraction`", "끔"],
                  ["자유 모서리 회절", "PTD 프린지 항이 그 자리를 맡는다", "끔",
                   "담는다 — `edge_diffraction`", "끔"],
                  ["다중반사", "담는다 — `rcs_sbr(max_bounce≥2)`(`src/rcs_sbr.py:1302`)",
                   "끔 — 스윕은 1차 히트 커널을 부른다", "담는다 — `max_depth`",
                   "끔 — `max_depth=1`"],
                  ["확산 반사", "PO 적분이 그 자리를 맡는다", "—",
                   "담는다 — `diffuse_reflection`", "켬"],
                  ["구면파 조명", "담는다 — `range_m`(`src/rcs_sbr.py:1093`)", "켬",
                   "송수신점을 실제 자리에 놓는다", "켬"]])),

        md("## 이 표가 서는 범위 — 어느 팔을 말하는가", "",
           "위 표의 «이번에 켰나» 칸은 **기준 실행**(`--physics` 없이 돈 `sionna` 계열 네 팔)의 "
           "상태다. 같은 스크립트가 `--physics` 로 돌린 팔이 둘 더 있고, 그 팔은 같은 줄에서 "
           "`max_depth=3` 에 굴절·회절·모서리회절을 전부 켠다. 원장에도 그 팔의 행이 있다 — "
           f"`engine=\"sionna_phys\"` {n_arm('sionna_phys')[0]} 행이고 그중 "
           f"{n_arm('sionna_phys')[1]} 행이 `n_missing = 0` 인 완결 행이다"
           + count_tag("engine=sionna_phys 행 수와 그중 n_missing=0 인 행 수") + ".", "",
           "그래서 축마다 성립 범위가 다르다.", "",
           "- **다중반사** — 기준 실행에서는 두 팔 다 끔이라 사과-대-사과다. `--physics` 판에서는 "
           "PathSolver 만 깊이 3 이 되고, 우리 팔은 스윕이 부르는 1 차 히트 커널에 "
           "다중반사 루프 자체가 없다(`src/rcs_sbr.py:1068`·투과 패스 `:1105`; 루프가 있는 "
           "`rcs_sbr(max_bounce≥2)` 는 스윕이 부르지 않는다).",
           "- **투과** — 기준 실행에서는 우리 팔만 셸 안을 본다. 그 τ 는 수직입사 |Γ| 로 "
           "만든 값이고 굴절각·유전체 내 위상지연·두께는 들어가지 않는다.",
           "- **조명** — 두 팔 다 실제 기하로 위상을 준다. 우리 커널의 평면파 갈래는 "
           "`range_m=None` 일 때만 켜지는 별개의 길이다.", "",
           f"⚠ 10 m 는 이 기체의 원거리장 경계 안쪽이다 — 두 팔 다 근거리장 판을 계산한 "
           f"것이고, 원거리장 평면파 값과 나란히 놓는 비교는 이 절의 범위 밖이다."),

        md("## 스위치를 하나씩 켠 여섯 판", "",
           DP.table("cases",
                    [("설정", None),
                     ("경로 중앙값", "npaths_median"),
                     ("레벨 [dB]", "level_db"),
                     ("자세당 초", "sec_per_pose")],
                    fmt={"npaths_median": "{:.0f}", "level_db": "{:.2f}",
                         "sec_per_pose": "{:.3f}"},
                    key_col="설정")),

        md(f"![switch axis]({FIG}/report17_switch_axis.png)", "",
           caption(1, "네 스위치 중 어느 것이 나딧 레벨을 올리나?"), "",
           f"회절만 켠 판 {DP.num(lvl.format(diff), -64.23, '{:.2f}', 'dB')} 은 기준 판 "
           f"{DP.num(lvl.format(base), -130.78, '{:.2f}', 'dB')} 보다 **{_rise_db():.2f} dB** "
           f"위에 선다(두 칸의 차). 나머지 세 스위치는 기준 자리에 머물고, 네 스위치를 전부 "
           f"켠 판의 레벨은 회절만 켠 판과 같다 — `--physics` 가 올린 것은 회절 하나다."),

        md("## 모서리 회절만 켠 판이 기준과 같은 이유", "",
           f"모서리회절만 켠 판은 레벨 "
           f"{DP.num(lvl.format('모서리회절만 켬'), -130.78, '{:.2f}', 'dB')} · 경로 중앙값 "
           f"{DP.num(npm.format('모서리회절만 켬'), 11, '{:.0f}', '개')} 로 기준 판과 같은 "
           f"자리에 선다.", "",
           "이유는 엔진 소스에 적혀 있다. `edge_diffraction` 은 "
           "`sionna/rt/path_solvers/sb_candidate_generator.py:600` 의 `if diffraction_enabled:` "
           "블록 **안에서만** 읽힌다. 즉 `diffraction=False` 인 채로 `edge_diffraction=True` 를 "
           "주면 그 인자는 자유 모서리를 여는 대신 그냥 지나간다 — 이 행은 스위치의 크기가 "
           "아니라 **설정의 항등식**이고, 세 앙각 전부에서 네 값이 똑같이 겹치는 것이 그 "
           "표시다.", "",
           "⭐그러니 `--physics` 의 네 스위치 중 실제로 레벨을 만든 것은 회절 하나이고, "
           "모서리 회절의 크기는 `diffraction=True` 를 고정한 채 그 스위치만 뒤집는 판에서 "
           "잰다. 그 판은 다음 단계 표에 있다.", "",
           "스톡 Sionna 2.0.1 이 여는 회절은 **1 차 한 번까지**다 — 소스가 "
           "«Only first order diffraction is supported» 라 적고"
           "(`sb_candidate_generator.py:394`), 회절을 뽑은 경로에서는 이후 회절과 확산반사를 "
           "끈다(같은 파일 `:405`~`:407`)."),

        md("## 경로 수는 스위치의 지표이고, 세기는 레벨 칸이 잰다", "",
           f"이 절의 표에 경로 수를 함께 적은 것은 스위치가 무엇을 열었는지 보이기 "
           f"위해서다. 같은 엔진이 반지름 "
           f"{RT.num('C_pec_sphere[0].r', 0.3, '{:.1f}', 'm')} 짜리 금속 구에 광선 "
           f"{RT.num('C_pec_sphere[0].spp', 1000000, '{:,.0f}', '발')} 을 쏘아 얻은 표적 "
           f"경로는 {RT.num('C_pec_sphere[0].n_paths', 0, '{:.0f}', '개')} 이고, 챔버 판의 "
           f"표적 근처 경로 {RT.num('D_chamber_paths.n_near', 12, '{:.0f}', '개')} 중 진짜 "
           f"에코는 {RT.num('D_chamber_paths.n_true', 1, '{:.0f}', '개')} 다.", "",
           f"경로 수와 레벨이 갈라지는 자리도 이 표 안에 있다 — 전부 켠 판은 경로 중앙값 "
           f"{DP.num(npm.format('전부 켬 (--physics)'), 6, '{:.0f}', '개')} 로 회절만 켠 판의 "
           f"{DP.num(npm.format(diff), 14, '{:.0f}', '개')} 보다 적은데 레벨은 같다.", "",
           f"스톡 솔버의 경로 진폭이 표적 면적을 어떻게 따라가는지는 "
           f"{ref_old('size-sweep', '면적을 키운 스윕')} 이 이미 재 놓았다. 여기서는 그 결론을 "
           f"**경로 수를 읽는 주의**로만 쓴다."),

        md("## 이 절이 고정한 것", "",
           "① 두 팔의 스위치 상태는 소스 줄 번호로 고정됐다. ② `--physics` 의 상승은 회절 "
           "하나에 귀속된다. ③ 경로 수는 스위치의 지표이고, 세기는 레벨 칸이 잰다.", "",
           f"회절이 올린 그 상승분이 표적에서 온 것인지 정적 성분에서 온 것인지는 다음 절이 "
           f"분모를 갈라 답한다 — {ref('physics-denominator', '분모가 커진 결과')}."),

        next_steps([
            ("우리 팔의 모서리 회절을 켜고(`--ptd`) 같은 나딧 판을 다시 돌린다",
             "두 팔이 모서리 회절 축에서 같은 설정이 되어 회절 상승을 팔 사이에서 비교할 수 있다",
             "`benchmark/elevation_sweep_md.py --ptd`"),
            ("`diffraction=True` 를 고정한 채 `edge_diffraction` 만 껐다 켠 판을 돌린다",
             "모서리 회절 스위치 자체의 크기가 처음으로 수치로 나온다",
             "`benchmark/diag_physics_paths.py` 케이스 추가 · **새 계산이 필요하다**"),
            ("회절을 켠 판의 시계열을 대역 잣대로 읽는다",
             "회절이 올린 전력이 날개끝 상한 위로 새는 몫인지가 수치로 갈린다",
             ref("physics-above-limit", "상한 위 에너지 몫")),
            ("굴절만 켠 판을 앙각 일곱 점으로 넓힌다",
             "투과 축의 두 팔 차이가 앙각마다 확정된다",
             "`benchmark/diag_physics_paths.py <el>`"),
        ]),
    ]


# =========================================================================== #
#  조각 86 — 권 17 절 4 「같은 기하에서 8/11 덱의 무늬가 재현된다」
#  ⚠ 이 절만의 원장·헬퍼는 이 블록 안에 모아 둔다(형제 절과 안 부딪치게).
# =========================================================================== #
PVD = from_json("outputs/physics_vs_deck.json")           # 덱 대조 (이 절 전용)
SWP = from_json("outputs/elevation_sweep_md.json")        # 앙각 스윕 원장
RPC = from_json("outputs/physics_deck_repro_check.json")  # 대조표 재현·완결성 점검


def row(engine: str, el_deg: float, *, complete: bool = True) -> str:
    """`rows[i]` 의 i 를 (엔진, 앙각)으로 찾아 준다 — 병합마다 인덱스가 밀리기 때문이다.

    complete=True 면 `n_missing == 0` 인 행만 고른다(부분 병합 행은 시계열에 0 이 박혀 있다).
    """
    for i, r in enumerate(SWP.get("rows")):
        if r.get("engine") != engine or abs(float(r.get("el_deg")) - el_deg) > 1e-9:
            continue
        if complete and r.get("n_missing"):
            continue
        return _mark_row(i, engine, el_deg)
    raise ContractError(
        f"찾는 행이 없다 — engine={engine!r}, el={el_deg}, complete={complete}")


_R_OURS = row("ours", -15.0)                          # 우리 팔 el −15 (완결 행)
_R_PHYS = row("sionna_phys", -15.0)                   # 물리 팔 el −15 (완결 행)
_R_PHYS250 = row("sionna_p250000000_phys", -15.0)     # 광선 250M + 물리 el −15 (완결 행)

#: 채점된 칸은 원장이 정한다 — 상관 열을 든 칸을 그대로 세어 덱 축과 엔진 축으로 가른다.
_CORR_CELLS = [c for c, v in PVD.get("cells").items() if "corr_with_ours_db_map" in v]
_CORR_DECK = [c for c in _CORR_CELLS if c.startswith("deck:")]
_CORR_ENGINE = [c for c in _CORR_CELLS if not c.startswith("deck:")]


def _corr(cell: str) -> float:
    return float(PVD.get(f"cells.{cell}.corr_with_ours_db_map"))


#: 상관이 큰 순 — 표와 제목이 같은 순서를 쓴다.
_CORR_ORDER = sorted(_CORR_CELLS, key=_corr, reverse=True)

#: 계획의 제목은 이 절의 세 상관을 «우리 팔 대 덱» 으로 적는다. 덱 세 판은 같은 커널을
#  거리만 바꿔 다시 돌린 것이라 그 셋은 **거리 축의 자기일관성**이고, 엔진이 바뀐 칸은
#  원장이 든 만큼이다. 계획 JSON 은 그대로 두고 제목만 그 범위로 맞춘다.
TITLE_86 = (
    f"우리 커널은 덱 3~40 m 판과 "
    f"{min(map(_corr, _CORR_DECK)):.4f}~{max(map(_corr, _CORR_DECK)):.4f}"
    f" 로 겹치고, 엔진이 바뀐 {len(_CORR_ENGINE)} 칸은 "
    f"{min(map(_corr, _CORR_ENGINE)):.4f}~{max(map(_corr, _CORR_ENGINE)):.4f} 다")
REG["physics-deck-match"] = ("86", TITLE_86)

REPRO_86 = dict(
    cmd="PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
        "benchmark/build_physics_vs_deck_fig.py",
    out=["outputs/physics_vs_deck.json",
         "outputs/figures/physics_vs_deck_el-15.png"],
    runtime="약 36 초 (CPU · GPU 미사용)",
    note="시계열은 `outputs/elevation_sweep_md.npz`(스윕)와 "
         "`outputs/deck_ours_by_range.npz`(덱)에서 읽는다. 팔의 완결성은 "
         "`outputs/elevation_sweep_md.json` 의 `n_missing` 이 정한다")


def blocks_86() -> list:
    return [
        header(
            num=86,
            title=REG["physics-deck-match"][1],
            did="앙각 스윕의 el −15° 시계열을 8/11 덱이 쓴 같은 기하의 시계열과 같은 STFT "
                "규약으로 나란히 놓고 dB 맵 상관·빗살 간격·빗살 높낮이로 대조했다.",
            results=[
                f"우리 팔은 덱 15 m 판과 "
                f"{PVD.num('cells.deck:R15/E.corr_with_ours_db_map', fmt='{:.4f}')}, "
                f"40 m 판과 "
                f"{PVD.num('cells.deck:R40/E.corr_with_ours_db_map', fmt='{:.4f}')}, "
                f"3 m 판과 "
                f"{PVD.num('cells.deck:R3/E.corr_with_ours_db_map', fmt='{:.4f}')} 로 겹친다.",

                f"덱 세 판은 **같은 커널을 거리만 바꿔** 다시 돌린 것이라, 그 세 값은 우리 "
                f"커널의 거리 무관성을 잰다⟨outputs/deck_ours_by_range.json : _meta.what_ko⟩.",

                f"엔진이 바뀐 칸은 {len(_CORR_ENGINE)} 개다 — 물리 끔 "
                f"{PVD.num('cells.sionna/el-15.corr_with_ours_db_map', fmt='{:.4f}')} · "
                f"물리 켬 "
                f"{PVD.num('cells.sionna_phys/el-15.corr_with_ours_db_map', fmt='{:.4f}')} · "
                f"광선 250M 에 물리 켬 "
                f"{PVD.num('cells.sionna_p250000000_phys/el-15.corr_with_ours_db_map', fmt='{:.4f}')}"
                f" 다.",

                f"빗살 간격은 {len(_CORR_CELLS) + 1} 판이 모두 "
                f"{PVD.num('cells.ours/el-15.comb_spacing_hz', fmt='{:.2f}', unit='Hz')} 이고 "
                f"예측 대비 오차도 "
                f"{PVD.num('cells.ours/el-15.comb_spacing_err_hz', fmt='{:+.2f}', unit='Hz')} "
                f"로 같다 — 그 칸의 눈금은 4.81 Hz 라 반 칸보다 작은 차이를 접는다.",

                f"물리를 켠 두 팔의 el −15° 행은 자세 "
                f"{cite_row(SWP, f'{_R_PHYS}.n_poses', fmt='{:,.0f}', unit='개')} 가 다 차 "
                f"있다 — `n_missing` 이 "
                f"{cite_row(SWP, f'{_R_PHYS}.n_missing', fmt='{:,.0f}')} · "
                f"{cite_row(SWP, f'{_R_PHYS250}.n_missing', fmt='{:,.0f}')} 다.",
            ],
            method=[
                ("나란히 놓은 것",
                 f"같은 표적·같은 자세열의 시계열 {len(_CORR_CELLS) + 1} 개 — 우리 커널 · "
                 f"PathSolver 세 팔(물리 끔 · 물리 켬 · 광선 250M 에 물리 켬) · "
                 f"8/11 덱의 3 · 15 · 40 m 판"),
                ("닮음의 잣대",
                 "`md_mapstyle.flash_spec` 의 STFT 로 만든 dB 맵끼리의 상관계수. 패널마다 "
                 "자기 최대값으로 정규화한다 — 팔 사이 정규화가 달라서다"),
                ("박자의 잣대",
                 "±m·f_flash(m = 1~8) 근방 첨두 위치의 차이 중앙값. f_flash 는 입력한 "
                 "회전수에서 나온 예측값이다"),
                ("팔을 거르는 문턱",
                 "`outputs/elevation_sweep_md.json` 의 `n_missing` 이 0 인 팔만 쓴다"),
                ("시간·주파수 표현",
                 "STFT 하나만 쓴다 — 재할당·WVD 는 이 프로젝트의 상설 금지 항목이다"),
            ],
            prereq=[
                (ref("physics-single-axis", "물리 단일축 분해"),
                 "회절 스위치 하나가 나딧에서 무엇을 올리는가"),
                (ref("el-sweep-design", "앙각 스윕 설계"),
                 f"병합판 {n_rows()} 행 중 어느 행을 판정에 쓰는가"),
            ],
            repro=REPRO_86,
        ),

        md("## 덱과 다른 것은 거리 하나다", "",
           "이 대조가 성립하는 이유는 두 자료가 **같은 물건을 같은 설정으로** 낸 것이기 "
           "때문이다⟨outputs/physics_vs_deck.json : _meta.geometry_ko⟩. 아래 일곱 줄 중 "
           "여섯 줄이 같고, 다른 것은 거리 한 줄이다.", "",
           table(["무엇", "8/11 덱", "앙각 스윕"], [
               ["표적", f"`{SWP.get('_meta.drone')}`", f"`{SWP.get('_meta.drone')}`"],
               ["방위 · 앙각", "az 0° · el −15°", "az 0° · el −15°"],
               ["반송주파수",
                "3.5 GHz⟨outputs/elevation_sweep_md.json : _meta.fc_hz⟩",
                "같음"],
               ["PRF", PVD.num("_meta.prf_hz", fmt="{:,.0f}", unit="Hz"), "같음"],
               ["자세 수", cite_row(SWP, f"{_R_OURS}.n_poses", fmt="{:,.0f}"), "같음"],
               ["플래시 예측",
                PVD.num("_meta.f_flash_hz", fmt="{:.2f}", unit="Hz"), "같음"],
               ["거리", "3 · 15 · 40 m",
                SWP.num("_meta.range_m", fmt="{:.0f}", unit="m")],
           ])),

        md("## 닮음을 눈이 아니라 수로 잰다", "",
           f"우리 팔의 dB 맵을 기준으로 나머지 {len(_CORR_CELLS)} 판과의 상관계수를 잰다. "
           f"덱 15 m 판이 가장 가깝고, 광선 250M 에 물리를 켠 PathSolver 가 가장 멀다.", "",
           "⭐덱 세 판은 **우리 커널을 거리만 바꿔 다시 돌린 것**이다"
           "(`benchmark/deck_ours_by_range.py`, 조명은 «위상만 구면파» "
           "⟨outputs/deck_ours_by_range.json : _meta.caveat_ko⟩). 그러니 그 세 값은 엔진 "
           "사이의 교차검증이라기보다 **한 커널이 3~40 m 에서 같은 무늬를 내는가**를 잰다. "
           f"엔진이 바뀐 칸은 아래 표의 `sionna` 계열 {len(_CORR_ENGINE)} 줄이다."),

        md(PVD.table("cells",
                     [("판", None), ("우리 팔과의 상관", "corr_with_ours_db_map")],
                     key_col="판", fmt={"corr_with_ours_db_map": "{:.4f}"},
                     order=_CORR_ORDER), "",
           "⚠ 이 상관은 **패널마다 자기 최대값으로 정규화한 dB 맵**끼리 잰 값이다"
           "⟨outputs/physics_vs_deck.json : _meta.normalisation_ko⟩. 두 팔의 절대 레벨은 "
           "이 표에 들어 있지 않다 — 레벨 축은 "
           + ref("budget-not-physics", "예산은 물리가 아니다") + " 가 같은 엔진 안에서 다룬다."),

        md(f"![physics vs deck]({FIG}/physics_vs_deck_el-15.png)", "",
           caption(1, "우리 팔의 el −15° 무늬는 이미 발표한 덱의 판과 같은 물건인가?"), "",
           "위 줄은 우리 커널 · 물리를 끈 PathSolver · 물리를 켠 PathSolver(11.1M) 이고, "
           "가운데 줄은 광선 250M 에 물리를 켠 판과 덱 3 · 15 m 판, 아래 줄이 덱 40 m 판이다. "
           "흰 점선은 날개끝 속도가 정하는 예측 상한이다. 우리 팔과 덱 세 판은 그 선 아래에 "
           "같은 간격의 빗살을 세우고, 물리를 끈 PathSolver 는 그 위로 번진 얼룩을 얹는다. "
           "물리를 켠 두 판은 0 Hz 띠와 자세 몇 개를 가로지르는 세로선으로 선다."),

        md(f"## 빗살 간격은 {len(_CORR_CELLS) + 1} 판이 한 값이다", "",
           f"{len(_CORR_CELLS) + 1} 판의 빗살 간격과 예측 대비 오차, 그리고 정규화와 무관한 "
           f"양인 AC/DC(0 Hz 정지 성분 대비 변조 성분의 비)를 한 표에 놓는다.", "",
           PVD.table("cells",
                     [("판", None),
                      ("빗살 간격 [Hz]", "comb_spacing_hz"),
                      ("예측 대비 오차 [Hz]", "comb_spacing_err_hz"),
                      ("AC/DC [dB] (el −15° 판)", "ac_over_dc_db")],
                     key_col="판",
                     fmt={"comb_spacing_hz": "{:.2f}",
                          "comb_spacing_err_hz": "{:+.2f}",
                          "ac_over_dc_db": "{:.2f}"},
                     order=["ours/el-15"] + _CORR_ORDER)),

        md("간격 칸이 모든 판에서 한 값인 것은 **눈금이 한 칸뿐이기 때문**이다. 첨두는 "
           "주파수 격자 위에만 놓이고, PRF "
           + PVD.num("_meta.prf_hz", fmt="{:,.0f}", unit="Hz") + " 를 4,096 자세로 잰 격자의 "
           "한 칸은 4.81 Hz 다. 125.05 Hz 는 그 26 칸이고, 입력한 f_flash "
           + PVD.num("_meta.f_flash_hz", fmt="{:.2f}", unit="Hz")
           + " 는 26.34 칸 자리라 26 칸으로 내려앉는다 — 예측 대비 오차 −1.62 Hz 는 커널이 "
           "낸 값이라기보다 그 내림 나머지다.", "",
           "⇒ 이 칸이 가르는 것은 **반 칸(±2.4 Hz)보다 큰 박자 차이**뿐이고, 모든 판이 그 "
           "안에 들어 있다. 박자 자체는 우리가 입력한 회전수가 정하므로 이 칸은 산란 커널을 "
           "재지 않는다 — 팔을 가르는 잣대는 "
           + ref("el-above-tip-limit", "상한 위 누설") + " 가 앙각 여섯 점에서 다룬다. "
           "AC/DC 는 우리 팔·덱·물리 끔 팔이 "
           + PVD.num("cells.deck:R3/E.ac_over_dc_db", fmt="{:.2f}", unit="dB")
           + " 에서 "
           + PVD.num("cells.sionna/el-15.ac_over_dc_db", fmt="{:.2f}", unit="dB")
           + " 사이에 모이고, 물리를 켠 두 팔은 "
           + PVD.num("cells.sionna_phys/el-15.ac_over_dc_db", fmt="{:.2f}", unit="dB")
           + " · "
           + PVD.num("cells.sionna_p250000000_phys/el-15.ac_over_dc_db",
                     fmt="{:.2f}", unit="dB")
           + " 로 그 아래에 앉는다 — 이 값은 판 안에서의 비라 정규화가 달라도 나란히 놓을 수 "
           "있는 칸이다."),

        md("## 팔을 가르는 것은 빗살의 높낮이다", "",
           "빗살 간격이 같으므로, 무늬를 가르는 것은 **몇 차 빗살이 얼마나 높은가**다. "
           "1~8 차 빗살의 잡음바닥 대비 높이를 판마다 적는다.", "",
           PVD.table("cells",
                     [("판", None), ("1x", "line_snr_db.1x"), ("2x", "line_snr_db.2x"),
                      ("3x", "line_snr_db.3x"), ("4x", "line_snr_db.4x"),
                      ("5x", "line_snr_db.5x"), ("6x", "line_snr_db.6x"),
                      ("7x", "line_snr_db.7x"), ("8x", "line_snr_db.8x")],
                     key_col="판",
                     fmt={f"line_snr_db.{m}x": "{:.2f}" for m in range(1, 9)},
                     order=["ours/el-15"] + _CORR_ORDER)),

        md("우리 팔과 덱 판은 같은 모양의 사다리를 그린다 — 3 차에서 골이 지고 "
           "6~7 차에서 마루가 선다. 우리 팔의 3 차는 "
           + PVD.num("cells.ours/el-15.line_snr_db.3x", fmt="{:.2f}", unit="dB")
           + ", 7 차는 "
           + PVD.num("cells.ours/el-15.line_snr_db.7x", fmt="{:.2f}", unit="dB")
           + " 이고, 덱 15 m 판의 같은 두 칸은 "
           + PVD.num("cells.deck:R15/E.line_snr_db.3x", fmt="{:.2f}", unit="dB")
           + " 과 "
           + PVD.num("cells.deck:R15/E.line_snr_db.7x", fmt="{:.2f}", unit="dB")
           + " 다.", "",
           "물리를 끈 PathSolver 판에도 3 차 골은 있다 — "
           + PVD.num("cells.sionna/el-15.line_snr_db.3x", fmt="{:.2f}", unit="dB")
           + " 로 그 행 여덟 칸 중 가장 낮다. 갈리는 것은 **골의 깊이와 마루의 자리**다. 그 "
           "판의 마루는 7 차("
           + PVD.num("cells.sionna/el-15.line_snr_db.7x", fmt="{:.2f}", unit="dB")
           + ")가 아니라 4 차("
           + PVD.num("cells.sionna/el-15.line_snr_db.4x", fmt="{:.2f}", unit="dB")
           + ")에 서고, 최고−최저가 8.15 dB 로 우리 팔 18.60 dB 의 절반보다 작다. 상관 "
           + PVD.num("cells.sionna/el-15.corr_with_ours_db_map", fmt="{:.4f}")
           + " 의 정체가 이 **덜 굴곡짐**이다."),

        md("물리를 켠 두 팔은 사다리 자체가 낮다 — 여덟 칸이 "
           + PVD.num("cells.sionna_phys/el-15.line_snr_db.7x", fmt="{:.2f}") + "~"
           + PVD.num("cells.sionna_phys/el-15.line_snr_db.5x", fmt="{:.2f}", unit="dB")
           + "(물리 켬 11.1M) 과 "
           + PVD.num("cells.sionna_p250000000_phys/el-15.line_snr_db.4x", fmt="{:.2f}")
           + "~"
           + PVD.num("cells.sionna_p250000000_phys/el-15.line_snr_db.3x",
                     fmt="{:.2f}", unit="dB")
           + "(물리 켬 250M) 안에 다 들어간다. 그 폭은 우리 팔 18.60 dB 의 3 분의 1 아래이고, "
           "상관 "
           + PVD.num("cells.sionna_phys/el-15.corr_with_ours_db_map", fmt="{:.4f}")
           + " · "
           + PVD.num("cells.sionna_p250000000_phys/el-15.corr_with_ours_db_map",
                     fmt="{:.4f}")
           + " 이 그 평평함의 점수다.", "",
           "`line_snr_db` 는 팔마다 **자기 대역외 바닥**에 대한 비다. 바닥이 다르면 여덟 "
           "칸이 통째로 평행이동하므로, 비교되는 것은 한 팔 안의 **모양**이다."),

        md("## 이 대조에서 빠진 팔은 하나다", "",
           "el −15° 의 채점표에 자리가 빈 팔은 모서리 회절을 켠 우리 커널 하나다"
           "⟨outputs/physics_vs_deck.json : _meta.missing_arms[0]⟩ — 그 팔의 시계열이 "
           "아직 계산되지 않았고, 그 계산이 다음 단계 표에 있다.", "",
           "물리를 켠 두 팔은 el −15° 에서 자세가 다 차 있어 채점됐다 — `n_missing` 이 "
           + cite_row(SWP, f"{_R_PHYS}.n_missing", fmt="{:,.0f}") + " · "
           + cite_row(SWP, f"{_R_PHYS250}.n_missing", fmt="{:,.0f}") + " 다. 광선 250M 에 "
           "물리를 끈 팔(`sionna_p250000000/el-15`)도 완결 행이고"
           + row_tag(row("sionna_p250000000", -15.0) + ".n_missing")
           + " 이 대조표에는 그 팔의 시계열이 아직 들어가 있지 않다.", "",
           "완결성 문턱은 대조표를 만드는 스크립트 밖에 있다"
           "⟨outputs/physics_deck_repro_check.json : gate.script_has_completeness_gate⟩ — "
           "스크립트는 npz 에 키가 있으면 패널로 넣고, 자세 완결성은 "
           "`outputs/elevation_sweep_md.json` 의 `n_missing` 이 따로 들고 있다.", "",
           "⚠ 그 점검 원장은 `gate.sionna_phys_el-15_n_missing` 을 "
           + RPC.num("gate.sionna_phys_el-15_n_missing", fmt="{:,.0f}")
           + " 로 들고 있다 — 병합판이 그보다 뒤 판이고, 같은 팔의 지금 값은 위의 0 이다."),

        md("## 이 표는 명령 한 줄로 다시 나온다", "",
           "같은 명령을 출력 경로만 바꿔 다시 돌려 원장과 맞대 보면, 공통 "
           + RPC.num("n_shared_cells", fmt="{:.0f}", unit="칸")
           + " 의 숫자 "
           + RPC.num("n_values_compared", fmt="{:.0f}", unit="개")
           + " 가 최대 차이 "
           + RPC.num("max_abs_diff", fmt="{:.6f}")
           + " 로 같은 값을 낸다⟨outputs/physics_deck_repro_check.json : _meta.rerun_cmd⟩. "
           "간격 · 오차 · AC/DC · 상관 · 1~8 차 빗살 높이가 전부 그 안에 든다.", "",
           "재현에 걸린 시간은 "
           + RPC.num("_meta.runtime_s", fmt="{:.1f}", unit="초")
           + " 이고, 돌린 장치는 CPU 하나다"
           "⟨outputs/physics_deck_repro_check.json : _meta.device⟩."),

        next_steps([
            ("재현 점검을 지금 병합판으로 다시 돌린다",
             f"점검 원장의 `gate.sionna_phys_el-15_n_missing`"
             f"({RPC.num('gate.sionna_phys_el-15_n_missing', fmt='{:,.0f}')})이 병합판의 "
             f"현재 값과 같은 자리에 선다",
             "`benchmark/build_physics_vs_deck_fig.py` 를 출력 경로만 바꿔 재실행 → "
             "`outputs/physics_deck_repro_check.json`"),

            ("대조표 생성 스크립트에 `n_missing` 문턱을 넣는다",
             "미완결 팔이 대조표에 자동으로 들어오는 길이 막힌다",
             "`benchmark/build_physics_vs_deck_fig.py:110` 의 `load()`"),

            ("모서리 회절을 켠 우리 커널(`ours_ptd/el-15`)을 같은 대조에 넣는다",
             "PTD 가 덱 무늬를 얼마나 옮기는지가 상관 한 칸으로 확정된다",
             ref("physics-above-limit", "상한 위 누설") + " 와 같은 팔 구성"),

            ("광선 250 M 팔(`sionna_p250000000/el-15`)을 같은 대조표에 넣는다",
             "빗살 사다리의 «평평함» 이 엔진의 성질인지 광선 예산의 성질인지가 갈린다",
             "`benchmark/build_physics_vs_deck_fig.py` 의 팔 목록 — 시계열은 이미 완결이다"),

            ("상관 잣대의 널(위상 무작위 대리신호·시간 뒤집기)을 같은 격자에서 잰다",
             f"엔진 축의 세 칸"
             f"({min(map(_corr, _CORR_ENGINE)):.4f}~{max(map(_corr, _CORR_ENGINE)):.4f})이 "
             f"«엔진이 다르다» 를 뜻하는지, 대역 봉투만 공유해도 나오는 값인지 결정된다",
             "`benchmark/build_physics_vs_deck_fig.py` 에 대리신호 칸 추가"),

            ("덱 8 m 판의 시계열을 새로 계산해 대조에 추가한다",
             "10 m 스윕과 가장 가까운 거리 판이 생겨 거리 차가 상관에 넣는 몫이 갈린다",
             "`outputs/deck_ours_by_range.npz` 는 3 · 15 · 40 m 만 들고 있다 — 새 계산이 "
             "필요하다"),
        ]),
    ]


# =========================================================================== #
#  조각 88 — 권 17 **마지막 절** 「이 엔진 비교로 말할 수 있는 것과 없는 것」
#  (계획의 절 1~5 는 83~87 이 채운다. 이 절은 그 뒤에 붙는 범위 표다.)
#  ⚠ 이 절은 위 코드에 의존하지 않는다 — 원장·헬퍼 이름이 전부 `_S88_` 로 시작한다.
#    형제 절이 이 파일을 다시 쓰더라도 이 블록만 그대로 옮겨 붙이면 살아난다.
# =========================================================================== #
_S88_FIG = "../outputs/figures"                                # 권(reports/) 기준
_S88_DP = from_json("outputs/diag_physics_paths_el-90.json")   # 스위치 단일축 6 케이스
_S88_D45 = from_json("outputs/diag_physics_paths_el-45.json")  # 같은 6 케이스, el −45
_S88_D0 = from_json("outputs/diag_physics_paths_el+0.json")    # 같은 6 케이스, el 0
_S88_RT = from_json("outputs/rt_no_rcs_verify.json")           # 경로가 σ 를 안 재는 실증
_S88_WB = from_json("outputs/wideband_energy.json")            # 날개끝 상한 위 누설
_S88_PD = from_json("outputs/physics_vs_deck.json")            # 8/11 덱 STFT 대조
_S88_DF = from_json("outputs/das_fleet_validation.json")       # 절대 σ 사전등록 채점
_S88_EM = from_json("outputs/engine_physics_matrix.json")      # 두 엔진 능력·전기적 크기
_S88_PO = from_json("outputs/po_refinement_survey.json")       # 선행연구 — UTD facet 전제
_S88_SW = from_json("outputs/elevation_sweep_md.json")         # 앙각 스윕 완결성

_S88_EMJ = "outputs/engine_physics_matrix.json"


def _s88_row(engine: str, el_deg: float) -> str:
    """`rows[i]` 를 (엔진, 앙각, `n_missing == 0`)으로 찾는다 — 인덱스는 병합마다 밀린다."""
    for i, r in enumerate(_S88_SW.get("rows")):
        if (r.get("engine") == engine
                and abs(float(r.get("el_deg")) - el_deg) < 1e-9
                and not r.get("n_missing")):
            return _mark_row(i, engine, el_deg)
    raise ContractError(f"완결 행이 없다 — {engine} el {el_deg}")


def _s88_link(no: str, anchor: str, label: str) -> str:
    """이미 디스크에 있는 조각으로 가는 링크. `build_volumes.py` 가 권·절 주소로 배선한다."""
    return f"[편 {no} «{label}»]({no}_{anchor}.ipynb)"


_S88_P0 = _s88_row("sionna_phys", 0.0)      # 물리 팔 el +0 (완결)
_S88_P90 = _s88_row("sionna_phys", -90.0)   # 물리 팔 el −90 (완결)

REPRO_88 = dict(
    cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/diag_physics_paths.py -90 20",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/verify_rt_no_rcs.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python src/figs_vol17_scope.py"],
    out=["outputs/diag_physics_paths_el-90.json",
         "outputs/rt_no_rcs_verify.json",
         "outputs/figures/ch17_scope_coverage.png"],
    runtime="그림 1 초 (CPU). 원장 둘은 GPU 1 장에서 만들어졌다",
    note="범위표가 함께 인용하는 원장 여덟은 `wideband_energy` · `physics_vs_deck` · "
         "`elevation_sweep_md` · `das_fleet_validation` · `engine_physics_matrix` · "
         "`po_refinement_survey` · `diag_physics_paths_el-45` · "
         "`diag_physics_paths_el+0` 다")


def blocks_88() -> list:
    L_SIZE = _s88_link("05", "size-sweep", "경로 진폭과 표적 면적")
    L_FLEET = _s88_link("28", "fleet-prereg", "함대 사전등록 채점")

    return [
        header(
            num=88,
            title=REG["engine-claim-scope"][1],
            did="권 17 이 쓴 원장 열 개를 열어, 이 엔진 비교가 세우는 주장 넷과 아직 "
                "열려 있는 질문 일곱을 범위 표 두 장으로 갈랐다.",
            results=[
                f"스위치 귀속은 el {_S88_DP.num('_meta.el_deg', -90.0, '{:.0f}', '°')} "
                f"한 자리에서 자세 {_S88_DP.num('_meta.n_poses', 20, '{:.0f}')} 개로 잰 "
                f"값이다 — 기준 "
                f"{_S88_DP.num('cases.기준(지금까지의 실행).level_db', -130.78, '{:.2f}', 'dB')}"
                f" 대 회절만 켠 판 "
                f"{_S88_DP.num('cases.회절만 켬.level_db', -64.23, '{:.2f}', 'dB')}.",
                f"물리 팔은 앙각 {n_arm('sionna_phys')[0]} 점에 행이 있고 그중 "
                f"{n_arm('sionna_phys')[1]} 점이 완결이다"
                + count_tag("engine=sionna_phys 행 수와 그중 n_missing=0 인 행 수")
                + f" — el +0 와 el −90 의 `n_missing` 은 "
                f"{cite_row(_S88_SW, f'{_S88_P0}.n_missing', 0, '{:.0f}')} · "
                f"{cite_row(_S88_SW, f'{_S88_P90}.n_missing', 0, '{:.0f}')} 다.",
                f"평판 σ 를 {_S88_RT.num('A_plate[0].sigma_dbsm', fmt='{:.2f}', unit='dBsm')}"
                f" 에서 {_S88_RT.num('A_plate[4].sigma_dbsm', fmt='{:.2f}', unit='dBsm')} 로 "
                f"키워도 경로 진폭비는 "
                f"{_S88_RT.num('A_plate[0].ratio_db', fmt='{:.6f}', unit='dB')} 에서 "
                f"{_S88_RT.num('A_plate[4].ratio_db', fmt='{:.6f}', unit='dB')} 로 머문다.",
                f"절대 σ 는 사전등록 채점에서 산포 "
                f"{_S88_DF.num('prereg_judgement.P3_spread_db', fmt='{:.2f}', unit='dB')} · "
                f"판정 {_S88_DF.num('prereg_judgement.verdict')} 다 — 우리 커널을 Das 측정 "
                f"함대로 채점한 판이다.",
                f"날개는 λ = "
                f"{_S88_EM.num('target_electrical_size.lambda_m_at_3p5GHz', fmt='{:.4f}', unit='m')}"
                f" 에서 최대 코드 "
                f"{_S88_EM.num('target_electrical_size.matrice4e_blade.chord_max_over_lambda', fmt='{:.2f}')}"
                f" λ · 최대 두께 "
                f"{_S88_EM.num('target_electrical_size.matrice4e_blade.thickness_as_lambda_fraction')}"
                f" 라 1차 회절 이론의 점근 영역 밖이다.",
            ],
            method=[
                ("스위치 귀속의 범위",
                 "`diag_physics_paths_el-90` 의 6 케이스 — 광선 예산을 고정하고 스위치만 "
                 "하나씩 바꾼 판"),
                ("앙각 커버리지",
                 "`elevation_sweep_md.rows` 에서 `(engine, el, n_missing == 0)` 으로 완결 "
                 "행만 골랐다"),
                ("상한 위 누설의 범위",
                 "`wideband_energy` 의 `sionna_phys` 칸 — el +0 와 el −90 두 칸이다"),
                ("덱 대조의 범위",
                 "`physics_vs_deck` 의 STFT dB 지도 상관 · `_meta.missing_arms` 가 어느 칸이 "
                 "비었는지 적는다"),
                ("σ 를 재는가",
                 "`rt_no_rcs_verify` 의 평판 다섯 크기와 PEC 구 여섯 조합"),
                ("절대 σ 의 판정",
                 "`das_fleet_validation` 의 사전등록 네 게이트 — 우리 커널을 Das 측정 함대에 "
                 "맞춘 판을 그 함대로 채점한다"),
                ("날개의 전기적 크기",
                 "`engine_physics_matrix` 가 `drone_cad` 의 블레이드 법칙 상수와 "
                 "`drones.matrice4e.prop_dia_mm` 로 계산한 값"),
            ],
            prereq=[("권 17 절 1", "el −90 에서 어느 스위치가 레벨을 올렸나"),
                    ("권 02", "스톡 경로 진폭이 표적 크기에 반응하는 폭")],
            repro=REPRO_88,
        ),

        md("## 이 절이 세우는 주장 넷", "",
           f"논거는 앞 절들이 편다 — {ref('physics-single-axis', '스위치 단일축')} 부터 "
           f"{ref('budget-not-physics', '예산 축')} 까지다. 이 표는 각 주장이 서는 "
           f"**범위**만 못 박는다. 그 밖에 있는 것은 다음 표로 넘어간다.",
           "",
           table(["주장", "무엇이 그것을 세우나", "어디까지"], [
               ["el −90 에서 레벨을 올린 스위치는 회절 하나다",
                f"6 케이스 단일축 — 기준 "
                f"{_S88_DP.num('cases.기준(지금까지의 실행).level_db', -130.78, '{:.2f}', 'dB')}"
                f" 과 모서리회절만 켠 판 "
                f"{_S88_DP.num('cases.모서리회절만 켬.level_db', -130.78, '{:.2f}', 'dB')} "
                f"이 소수점까지 같다",
                f"el −90 · 자세 {_S88_DP.num('_meta.n_poses', 20, '{:.0f}')} 개 · 광선 예산 "
                f"{_S88_DP.num('_meta.spp', 11111111, '{:,.0f}')} 고정"],
               ["규칙 예산 11.1M · el +0 에서 상한 위 몫이 커진다",
                f"el +0 에서 "
                f"{_S88_WB.num('cells.sionna/el+0.above_f_tip_frac', 0.29027, '{:.3f}')} → "
                f"{_S88_WB.num('cells.sionna_phys/el+0.above_f_tip_frac', 0.83078, '{:.3f}')}",
                "**el +0 한 칸.** el −90 은 f_tip = 0 이라 이 몫이 정의되지 않고, 광선을 "
                "250M 으로 맞춘 짝에서는 같은 스위치가 0.00084 만 남긴다"],
               ["우리 팔의 STFT 는 덱 15 m 판과 겹친다",
                f"dB 지도 상관 "
                f"{_S88_PD.num('cells.deck:R15/E.corr_with_ours_db_map', 0.9877, '{:.4f}')}",
                f"el −15 한 자리 · 물리를 켠 두 팔의 같은 칸은 "
                f"{_S88_PD.num('cells.sionna_phys/el-15.corr_with_ours_db_map', fmt='{:.4f}')}"
                f" · "
                f"{_S88_PD.num('cells.sionna_p250000000_phys/el-15.corr_with_ours_db_map', fmt='{:.4f}')}"
                f" 이고, 자리가 빈 팔은 "
                f"{_S88_PD.num('_meta.missing_arms[0]')} 하나다"],
               ["PathSolver 의 경로 진폭은 표적 σ 와 독립이다",
                f"평판 σ "
                f"{_S88_RT.num('A_plate[0].sigma_dbsm', fmt='{:.2f}', unit='dBsm')} → "
                f"{_S88_RT.num('A_plate[4].sigma_dbsm', fmt='{:.2f}', unit='dBsm')} 에 "
                f"진폭비 {_S88_RT.num('A_plate[4].ratio_db', fmt='{:.6f}', unit='dB')}",
                f"이 기하 한 벌 · 판별 구간은 far-field 를 지키는 변 0.2·0.5 m 두 판 · "
                f"PEC 구는 산란계수 0 인 여섯 조합에서 경로 "
                f"{_S88_RT.num('C_pec_sphere[5].n_paths', 0, '{:.0f}')} 개이고 산란계수를 "
                f"주면 {_S88_RT.num('B_sphere_S[0].n', 6, '{:.0f}')} ~ "
                f"{_S88_RT.num('B_sphere_S[3].n', 212, '{:.0f}')} 개로 선다 — 논거 전체는 "
                f"{L_SIZE}"],
           ])),

        md(f"![vol17 scope]({_S88_FIG}/ch17_scope_coverage.png)", "",
           caption(1, "물리 스위치 비교의 증거는 앙각 축에서 어디에 있나?")),

        md("## 아직 열려 있는 질문 일곱", "",
           table(["열린 질문", "지금 원장이 덮는 범위", "무엇을 재면 닫히나"], [
               ["다른 앙각의 스위치 귀속",
                f"귀속을 세운 판은 el −90(자세 "
                f"{_S88_DP.num('_meta.n_poses', 20, '{:.0f}')}) 한 자리이고, 같은 6 케이스가 "
                f"el −45(자세 {_S88_D45.num('_meta.n_poses', 16, '{:.0f}')}) · "
                f"el 0(자세 {_S88_D0.num('_meta.n_poses', 16, '{:.0f}')}) 에도 있다",
                "el −45 · el 0 을 el −90 판과 같은 자세 수로 다시 내고, "
                "el −15 · −30 · −60 · −75 에서 같은 6 케이스를 한 번씩"],
               ["다른 기체의 스위치 귀속", "matrice4e 한 대",
                "mavic4pro · mini5pro 에서 같은 6 케이스"],
               ["굴절 축의 공정한 대조",
                f"Sionna 는 플라스틱을 두께 "
                f"{_S88_EM.num('q2_refraction_fairness.measured_here_slab_numbers.sionna_default_thickness_m', fmt='{:.1f}', unit='m')}"
                f" 판으로 본다 — 왕복 "
                f"{_S88_EM.num('q2_refraction_fairness.measured_here_slab_numbers.at_d_100mm.round_trip_db', fmt='{:.2f}', unit='dB')}"
                f" 대 우리 "
                f"{_S88_EM.num('q2_refraction_fairness.measured_here_slab_numbers.our_kernel_tau.round_trip_db', fmt='{:.2f}', unit='dB')}",
                "`make_material` 이 실제 셸 두께를 넘기게 고친 뒤 `--physics` 재실행"],
               ["회절을 켠 판의 표본 배분",
                "회절 스위치가 표본의 20 % ⟨outputs/engine_physics_matrix.json : "
                "what_the_running_comparison_will_and_wont_answer.sionna_phys_wont_answer[2]⟩ "
                "를 회절로 가져간다",
                "표본 배분을 고정한 채 같은 spp 로 다시 재는 예산 사다리"],
               ["이 날개에서 1차 회절 이론이 서는 폭",
                f"코드 "
                f"{_S88_EM.num('target_electrical_size.matrice4e_blade.chord_max_over_lambda', fmt='{:.2f}')}"
                f" λ · 두께 "
                f"{_S88_EM.num('target_electrical_size.matrice4e_blade.thickness_as_lambda_fraction')}",
                "2차 회절을 계산하는 판 하나 또는 모서리 항을 분리해 재는 측정"],
               ["절대 σ",
                f"사전등록 산포 "
                f"{_S88_DF.num('prereg_judgement.P3_spread_db', fmt='{:.2f}', unit='dB')} · "
                f"{_S88_DF.num('prereg_judgement.verdict')}",
                f"교정 구를 함께 두고 재는 실측 — 설계는 {L_FLEET}"],
               ["나딧에서 물리 팔의 변조가 무엇인가",
                f"물리 팔의 el −90 행은 완결이고 레벨 "
                f"{cite_row(_S88_SW, f'{_S88_P90}.level_db', -64.23, '{:.2f}', 'dB')} 다. 같은 "
                f"자리에서 **물리를 끈** 팔의 AC/DC 는 "
                f"{_S88_EM.num('q3_can_diffraction_make_doppler_at_nadir.measured_here_nadir_spectra.rows.sionna/el-90.ac_over_dc_db', fmt='{:.2f}', unit='dB')}"
                f" · 2.5억 spp 판도 "
                f"{_S88_EM.num('q3_can_diffraction_make_doppler_at_nadir.measured_here_nadir_spectra.rows.sionna_p250000000/el-90.ac_over_dc_db', fmt='{:.2f}', unit='dB')}"
                f" 라, 그 자리의 표본잡음 마루가 이만큼 높다",
                "표본 배분을 고정한 예산 사다리로 물리 팔의 **절대** 변조를 그 마루 아래로 "
                "내린다"],
           ])),

        md("## 날개는 λ 의 절반보다 좁다 — 회절 근사가 서는 자리", "",
           f"3.5 GHz ⟨outputs/diag_physics_paths_el-90.json : _meta.fc_hz⟩ 에서 λ = "
           f"{_S88_EM.num('target_electrical_size.lambda_m_at_3p5GHz', fmt='{:.4f}', unit='m')}"
           f" 다. matrice4e 날개는 반경 "
           f"{_S88_EM.num('target_electrical_size.matrice4e_blade.radius_over_lambda', fmt='{:.1f}')}"
           f" λ · 최대 코드 "
           f"{_S88_EM.num('target_electrical_size.matrice4e_blade.chord_max_over_lambda', fmt='{:.2f}')}"
           f" λ · 최대 두께 "
           f"{_S88_EM.num('target_electrical_size.matrice4e_blade.max_thickness_mm', fmt='{:.2f}', unit='mm')}"
           f" = "
           f"{_S88_EM.num('target_electrical_size.matrice4e_blade.thickness_as_lambda_fraction')}"
           f" 다.",
           "",
           "그 두께는 블레이드 법칙의 **두께비**(무차원 비율) 상수와 코드 분포에서 스팬을 "
           f"따라 계산한 최대값이다 ⟨{_S88_EMJ} : target_electrical_size.measured_here_ko⟩ "
           "— 파장 대비는 위의 mm 값이 정한다.",
           "",
           "반경만 기체 관측(공표 프로펠러 지름)에 묶여 있고, 코드와 두께는 **CAD 블레이드 "
           "법칙에서 계산한 모델값**이다. 그 상수는 참조 프롭에서 상속한 것이라 이 기체를 잰 "
           "값이 아니다 — 어느 쪽 숫자를 쓰든 코드가 λ 의 절반보다 좁다는 결론은 선다.",
           "",
           "1차 UTD 와 1차 PTD 는 «모서리가 고립돼 있고 인접면이 여러 λ 에 걸쳐 평평하다» 를 "
           "전제로 선다. Ziganshin 외(`arXiv:2604.05991`, IEEE OJAP 투고본)가 그 전제를 facet "
           "변길이로 못 박았다 — 축자 «the facet size should be of several wavelengths in "
           "order to satisfy the UTD assumptions, typically E > 1.5λ».",
           BREAK,
           f"우리 메쉬의 `prop` 그룹 facet 변은 중앙 "
           f"{_S88_PO.num('our_mesh_discretization_check.measured.per_group.prop.E_median_lam', fmt='{:.3f}')}"
           f" λ 이고, 굽은 여섯 그룹은 그 전제를 "
           f"{_S88_PO.num('our_mesh_discretization_check.our_arithmetic_out_of_scope.violation_factor_vs_1p5lam[0]', fmt='{:.1f}')}"
           f" ~ "
           f"{_S88_PO.num('our_mesh_discretization_check.our_arithmetic_out_of_scope.violation_factor_vs_1p5lam[1]', fmt='{:.1f}')}"
           f" 배 벗어난다.",
           "",
           "Sionna 의 쐐기 회절은 그 면들 위에 붙고 1차까지 계산한다. 두 엔진 다 이 날개에서는 "
           "점근 영역 밖에서 회절을 다룬다.",
           "",
           "코드가 λ 의 절반보다 좁은 유전체 날개에서 1차 회절 근사의 오차 크기를 잰 선행은 우리 "
           "조사 두 편(`prior_work/po_refinement_survey.md` · "
           "`prior_work/sionna_sensing_survey.md`)에 없다. 그 크기는 다음 단계 표의 마지막 "
           "행이 재는 양이다."),

        md("## 절대 σ 는 우리 커널 자신의 채점에서도 미검증이다", "",
           "이 절의 주장 넷은 전부 상대량이다 — 레벨 차 · 에너지 몫 · 상관 · 진폭비.", "",
           table(["사전등록 게이트", "값"], [
               ["전 기체 6 dB 안",
                _S88_DF.num("prereg_judgement.P1_all_within_6db")],
               ["4 dB 안에 드는 기체 수",
                _S88_DF.num("prereg_judgement.P2_count_within_4db", 2, "{:.0f}")],
               ["산포",
                _S88_DF.num("prereg_judgement.P3_spread_db", fmt="{:.2f}", unit="dB")],
               ["부호 일치",
                _S88_DF.num("prereg_judgement.P4_sign_agreement")],
               ["판정", _S88_DF.num("prereg_judgement.verdict")],
           ]), "",
           f"채점의 내용과 그 판정이 무엇을 묶는지는 {L_FLEET} 가 편다."),

        next_steps([
            ("이미 디스크에 있는 물리 팔 샤드를 병합한다",
             "물리 팔이 두 칸에서 다섯 칸 이상으로 늘어 상한 위 누설과 덱 대조의 빈칸이 닫힌다",
             "`benchmark/elevation_sweep_md.py --merge` — 기존 원장을 덮으므로 상위 판단이 "
             "먼저다"),
            ("`make_material` 이 실제 셸 두께를 Sionna 에 넘기게 고친 뒤 `--physics` 를 다시 "
             "돌린다",
             "굴절 축이 같은 두께에서 비교되고, 두 커널의 왕복 감쇠 차가 레벨 변화에서 "
             "빠진다",
             "`src/materials.py` → 권 17 절 1"),
            ("`diag_physics_paths` 를 el 0 · −15 · −45 에서 한 번씩 더 돌린다",
             "스위치 귀속이 앙각의 함수인지 나딧 한 자리의 성질인지 갈린다",
             "`benchmark/diag_physics_paths.py <el> 20`"),
            ("표본 배분을 고정한 채 spp 사다리를 올려 물리 켬·끔을 다시 잰다",
             "레벨 변화 중 물리가 옮긴 몫과 표본 분산이 옮긴 몫이 갈린다",
             f"`benchmark/elevation_sweep_md.py` → {ref('budget-not-physics', '예산 축')}"),
            ("블레이드 모서리를 2차 회절까지 계산하는 판을 하나 만든다",
             "1차 회절 근사가 이 날개에서 내는 오차 크기가 숫자로 확정된다",
             "`src/ptd_edges.py` → 이 절의 범위표 다섯째 행"),
            ("교정 구를 함께 두고 실측한다",
             "절대 σ 의 자체 앵커가 서고 사전등록 산포가 다시 채점된다",
             f"{L_FLEET} → 권 11 실측 설계"),
        ]),
    ]


# =========================================================================== #
#  조각 87 — 권 17 절 5 「광선을 늘려도 레벨은 모이고 박자는 헤맨다」
#  ⚠ 이 절만의 원장·헬퍼는 이 블록 안에 모아 둔다(형제 절과 안 부딪치게).
#  ⭐ 이 절은 권 16 「앙각 커버리지」의 마지막 자리에도 그대로 선다 — 경로 수가 앙각에
#     걸린다는 교란(예산 축 ↔ 앙각 축)을 이 절이 들고 있기 때문이다.
# =========================================================================== #
from report_style import table_from                                  # noqa: E402

E87 = from_json("outputs/elevation_sweep_md.json")        # 앙각·예산 스윕 원장
D87 = from_json("outputs/ch1_elevation_figdata.json")     # 파생량·게이트
S87 = from_json("outputs/raybudget_seed_ladder.json")     # 40 m 시드 사다리


def _row87(engine: str, el_deg: float) -> str:
    """완결(`n_missing` = 0) 행의 `rows[i]` — 병합마다 인덱스가 밀리기 때문이다."""
    for i, r in enumerate(E87.get("rows")):
        if r.get("engine") == engine and abs(float(r.get("el_deg")) - el_deg) < 1e-9 \
                and not r.get("n_missing"):
            return _mark_row(i, engine, el_deg)
    raise ContractError(f"완결 행이 없다 — engine={engine!r}, el={el_deg}")


#: el 0 사다리 네 계단 · el −30 대조군 세 계단
_L0 = [_row87("sionna", 0.0), _row87("sionna_p250000000", 0.0),
       _row87("sionna_p1000000000", 0.0), _row87("sionna_p4000000000", 0.0)]
_L30 = [_row87("sionna", -30.0), _row87("sionna_p250000000", -30.0),
        _row87("sionna_p1000000000", -30.0)]
#: 대조 — 같은 한 계단(11.1 M → 250 M)이 다른 앙각에서 레벨을 얼마나 옮기나
_R75 = [_row87("sionna", -75.0), _row87("sionna_p250000000", -75.0)]
_R45 = [_row87("sionna", -45.0), _row87("sionna_p250000000", -45.0)]

_COLS87 = [("팔", "engine"), ("자세당 경로 수 중앙값", "npaths_median"),
           ("레벨 [dB]", "level_db"), ("박자 [Hz]", "track.beat_hz"),
           ("1 차 − 2 차 [dB]", "track.h1_over_h2_db"), ("추적 시간 [s]", "seconds")]
_FMT87 = {"npaths_median": "{:,.0f}", "level_db": "{:.2f}",
          "track.beat_hz": "{:.2f}", "track.h1_over_h2_db": "{:+.2f}",
          "seconds": "{:,.1f}"}

EVID_87 = ["outputs/elevation_sweep_md.json", "outputs/ch1_elevation_figdata.json",
           "outputs/raybudget_seed_ladder.json"]

#: 계획의 제목은 «광선을 360 배 늘려도 레벨이 모인다» 를 예산 축의 성질로 적는다. 같은
#  한 계단이 다른 앙각에서 레벨을 10 dB 넘게 옮기므로, 이 절의 제목만 el 0 으로 좁힌다
#  (계획 JSON 은 손대지 않는다). 두 숫자는 원장에서 뺀 값이라 원장이 바뀌면 제목도 바뀐다.
_D_EL0 = abs(float(E87.get(f"{_L0[3]}.level_db")) - float(E87.get(f"{_L0[0]}.level_db")))
_D_EL75 = abs(float(E87.get(f"{_R75[1]}.level_db")) - float(E87.get(f"{_R75[0]}.level_db")))
TITLE_87 = (f"el 0 에서 광선을 360 배 늘리면 정지 성분은 {_D_EL0:.2f} dB 안에 모이고, "
            f"같은 한 계단이 el −75 의 레벨을 {_D_EL75:.2f} dB 옮긴다")
REG["budget-not-physics"] = ("87", TITLE_87)
FIGS_87 = ["ch1_f6_el0_budget_ladder.png", "ch1_f5_raybudget.png"]

REPRO_87 = dict(
    cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/elevation_sweep_md.py --merge",
         "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
         "benchmark/build_ch1_elevation_figs.py",
         "PYTHONPATH=src ~/.venvs/py312/bin/python src/viz_ch1_el0_budget_ladder.py"],
    out=["outputs/elevation_sweep_md.json", "outputs/ch1_elevation_figdata.json",
         "outputs/figures/ch1_f6_el0_budget_ladder.png"],
    runtime="병합·그림 약 1 분 (CPU). 네 계단의 추적 자체는 합계 약 4.3 시간 (GPU 1 장)",
    note="계단은 `--spp` 로 광선 수를 직접 준 팔이다 — 팔 이름 꼬리의 숫자가 그 값이고, "
         "꼬리가 없는 `sionna` 가 규칙값이다")


def _n(key: str, fmt: str = "{:.2f}", unit: str = "") -> str:
    """앙각 스윕 원장 한 칸 — `rows[i]` 인용에는 (engine, el) 안정키가 함께 붙는다."""
    return cite_row(E87, key, fmt=fmt, unit=unit)


def blocks_87() -> list:
    return [
        header(
            num=87,
            title=REG["budget-not-physics"][1],
            did="el 0 에서 자세당 광선 수를 네 계단 올려 레벨·프로펠러 대역 전력·박자·경로 "
                "수가 각각 어디로 가는지 재고, 같은 사다리를 el −30 에서 대조했다.",
            results=[
                f"el 0 의 레벨은 광선 11.1 M 에서 {_n(f'{_L0[0]}.level_db', unit='dB')}, "
                f"4,000 M 에서 {_n(f'{_L0[3]}.level_db', unit='dB')} 로 0.03 dB 폭 안에 "
                f"모인다 — 광선이 360 배이고 경로는 223 배다.",

                f"그 수렴은 el 0 의 성질이다 — 예산을 한 계단(11.1 M → 250 M)만 올려도 "
                f"el −75 의 레벨은 {_n(f'{_R75[0]}.level_db')} → "
                f"{_n(f'{_R75[1]}.level_db', unit='dB')} 로 12.55 dB 움직인다.",

                f"같은 네 계단에서 박자는 {_n(f'{_L0[0]}.track.beat_hz')} → "
                f"{_n(f'{_L0[1]}.track.beat_hz')} → {_n(f'{_L0[2]}.track.beat_hz')} → "
                f"{_n(f'{_L0[3]}.track.beat_hz', unit='Hz')} 로 옮겨 다니고, 입력한 "
                f"f_flash 는 {_n('_meta.f_flash_hz', unit='Hz')} 다.",

                f"el −30 은 앙각 7 점 중 규칙 예산에서 최강선이 어긋나 있던 유일한 자리이고, "
                f"예산을 올리면 {_n(f'{_L30[0]}.track.beat_hz')} → "
                f"{_n(f'{_L30[1]}.track.beat_hz', unit='Hz')} 로 붙는다.",

                f"el 0 에서 오른 것은 변조가 아니라 평평한 표본화 바닥이다 — 250 M 판의 "
                f"프로펠러 대역 몫 "
                f"{D87.num('cells.sionna_p250000000/el+0.share_track_db', fmt='{:.2f}')} 와 "
                f"대역외 기준띠 "
                f"{D87.num('cells.sionna_p250000000/el+0.share_track_oob_db', fmt='{:.2f}', unit='dB')} "
                f"가 0.02 dB 차다.",
            ],
            method=[
                ("사다리",
                 "표적·기하·자세 격자·시드를 고정하고 자세당 광선 수만 11.1 M → 250 M → "
                 "1,000 M → 4,000 M 으로 올렸다 — 네 계단 모두 자세 4,096 개가 완결"
                 "(`n_missing` = 0)이다"),
                ("레벨",
                 "자세 4,096 개의 |E| 평균을 dB 로 적은 값. 팔마다 정규화가 달라서 "
                 "**같은 엔진·같은 앙각 안에서만** 견준다"),
                ("박자",
                 "프로펠러 대역 전력의 시간열을 다시 FFT 해 40~400 Hz 안의 최강선을 "
                 "잡는다 — `benchmark/elevation_sweep_md.py:237`"),
                ("대조군",
                 "같은 사다리를 el −30 에서 세 계단(11.1 M · 250 M · 1,000 M) 돌렸다"),
                ("시드",
                 "두 사다리 모두 시드 하나로 돈다"
                 "(`benchmark/elevation_sweep_md.py:183`). 시드 축의 크기는 40 m 자리의 "
                 "8 시드 사다리가 따로 잰다"),
            ],
            prereq=[
                (ref("el-above-tip-limit", "상한 위 누설"),
                 "팔을 가르는 잣대가 무엇인가 — f_flash 는 입력값이라 박자는 잣대가 아니다"),
                (ref("el-sweep-design", "앙각 스윕 설계"),
                 f"병합판 {n_rows()} 행 중 어느 행을 판정에 쓰는가"),
            ],
            repro=REPRO_87,
        ),

        md("## 네 계단은 자세당 광선 수 하나만 흔든다", "",
           "팔 이름이 곧 예산이다. `sionna` 는 광선 규칙 (R/3)² × 1M 을 그대로 쓴 팔이고 "
           "10 m 에서 " + _n("_meta.sionna_spp", "{:,.0f}", "발")
           + " 이다(`benchmark/elevation_sweep_md.py:89`). 꼬리에 숫자가 붙은 팔"
           "(`sionna_p250000000` 등)은 그 수를 직접 준 것이다.", "",
           "네 계단 모두 자세 " + _n(f"{_L0[0]}.n_poses", "{:,.0f}", "개")
           + " 가 채워져 있다 — 부분 병합 행은 이 절에서 제외한다."),

        md(table_from("outputs/elevation_sweep_md.json:rows", _COLS87,
                      fmt=_FMT87, order=[int(k[5:-1]) for k in _L0]), "",
           "레벨 칸은 0.03 dB 폭 안에 모이고, 그 옆에서 박자 칸은 326 Hz 를 오간다. "
           "**수렴한 것과 맞은 것은 다른 일이다.**", "",
           "네 계단은 시드가 하나씩이라 그 박자 흔들림이 예산 축 하나로 닫히지 않는다 — "
           "예산을 " + S87.num("cells[1].spp", fmt="{:,.0f}", unit="발")
           + " 로 고정하고 시드만 " + S87.num("cells[1].n_seeds", fmt="{:.0f}", unit="장")
           + " 바꾼 40 m 자리에서도 최강선의 표준편차가 "
           + S87.num("cells[1].sd_beat_hz", fmt="{:.2f}", unit="Hz") + " 다."),

        md("## el 0 에서 모이는 것은 정지 성분이다", "",
           f"![el0 budget ladder]({FIG}/ch1_f6_el0_budget_ladder.png)", "",
           caption(1, "광선을 360 배 늘리면 el 0 의 레벨과 박자는 각각 어디로 가는가?"), "",
           "왼쪽이 가장 작은 예산 대비 레벨 변화, 가운데가 최강선의 위치, 오른쪽이 자세당 "
           "경로 수다. 파랑이 el 0, 빨강이 대조군 el −30 이다."),

        md("프로펠러 대역 전력도 레벨과 함께 모인다 — "
           + _n(f"{_L0[0]}.track.band_power_db") + " 에서 "
           + _n(f"{_L0[3]}.track.band_power_db", unit="dB")
           + " 로 0.07 dB 폭이다. 두 양 모두 **동체 정반사가 지배하는 정지 성분**이고, "
           "그 성분은 광선 몇 발로도 금방 자리를 잡는다.", "",
           "그 수렴은 el 0 한 점의 성질이다. 예산을 한 계단(11.1 M → 250 M)만 올려도 "
           "el −45 의 레벨은 " + _n(f"{_R45[0]}.level_db") + " → "
           + _n(f"{_R45[1]}.level_db", unit="dB") + ", el −75 는 "
           + _n(f"{_R75[0]}.level_db") + " → " + _n(f"{_R75[1]}.level_db", unit="dB")
           + " 로 움직인다. 정반사가 꺼지는 앙각에서는 레벨 자체가 예산에 매달린다."),

        md("## 오른 것은 변조가 아니라 표본화 바닥이다", "",
           "el 0 의 변조 대 정지 비는 "
           + D87.num("cells.sionna/el+0.ac_over_dc_db", fmt="{:.2f}") + " 에서 "
           + D87.num("cells.sionna_p250000000/el+0.ac_over_dc_db", fmt="{:.2f}", unit="dB")
           + " 로 43.91 dB 올라온다. 올라온 것이 회전 성분인지 잡음 바닥인지는 같은 원장의 "
           "세 칸이 가른다.", "",
           "250 M 판의 프로펠러 대역 몫은 "
           + D87.num("cells.sionna_p250000000/el+0.share_track_db", fmt="{:.2f}") + " 이고, "
           "블레이드가 원리적으로 못 오는 대역외 기준띠는 "
           + D87.num("cells.sionna_p250000000/el+0.share_track_oob_db", fmt="{:.2f}", unit="dB")
           + " 로 **0.02 dB 차**다. 그 판의 빗살 선 SNR 최대는 "
           + D87.num("cells.sionna_p250000000/el+0.comb_snr_db[0]", fmt="{:.1f}", unit="dB")
           + " 이고 최강선은 " + _n(f"{_L0[1]}.track.beat_hz", unit="Hz") + " 로 f_flash "
           + _n("_meta.f_flash_hz", unit="Hz") + " 와 어긋난다.", "",
           "같은 자리 우리 커널은 대역 몫 "
           + D87.num("cells.ours/el+0.share_track_db", fmt="{:.2f}") + " 대 기준띠 "
           + D87.num("cells.ours/el+0.share_track_oob_db", fmt="{:.2f}", unit="dB")
           + " 로 24.60 dB 여유가 있고, 빗살 1 차가 "
           + D87.num("cells.ours/el+0.comb_snr_db[0]", fmt="{:.1f}", unit="dB")
           + " · 최강선이 " + D87.num("cells.ours/el+0.beat_track_hz", fmt="{:.2f}", unit="Hz")
           + " 다. ⇒ el 0 에서 PathSolver 의 AC/DC 가 재는 것은 자세 간 표본화 잡음이고, "
           "우리 커널의 같은 열은 변조 깊이를 잰다.", "",
           "최강선은 40~400 Hz 안에서 고른다(`benchmark/elevation_sweep_md.py:237`). "
           "11.1 M 계단의 " + _n(f"{_L0[0]}.track.beat_hz", unit="Hz")
           + " 는 f_flash 의 3 배 자리(380.0 Hz)에서 한 칸 안이고, 250 M 계단의 "
           + _n(f"{_L0[1]}.track.beat_hz", unit="Hz")
           + " 는 빗살 밖의 창 아래 가장자리 값이다."),

        md("## el −30 은 같은 사다리에서 박자가 붙는다", "",
           table_from("outputs/elevation_sweep_md.json:rows", _COLS87,
                      fmt=_FMT87, order=[int(k[5:-1]) for k in _L30])),

        md("11.1 M 계단의 " + _n(f"{_L30[0]}.track.beat_hz", unit="Hz")
           + " 는 f_flash 의 두 배 자리다. 그 계단에서는 1 차 빗살이 2 차보다 "
           + _n(f"{_L30[0]}.track.h1_over_h2_db", "{:+.2f}", "dB")
           + " 라 최강선이 2 차로 넘어간다. 250 M 에서 그 차이가 "
           + _n(f"{_L30[1]}.track.h1_over_h2_db", "{:+.2f}", "dB")
           + " 로 뒤집히면서 최강선이 1 차로 돌아오고, 1,000 M 에서도 "
           + _n(f"{_L30[2]}.track.beat_hz", unit="Hz") + " 로 머문다.", "",
           "같은 세 계단에서 el −30 의 레벨은 " + _n(f"{_L30[0]}.level_db")
           + " 에서 " + _n(f"{_L30[2]}.level_db", unit="dB")
           + " 로 4.25 dB 올라간다 — el 0 에서 모였던 그 양이 여기서는 계속 움직인다.", "",
           "el −30 은 앙각 7 점 중 규칙 예산에서 최강선이 어긋나 있던 **유일한 자리**다. "
           "나머지 앙각(−15·−45·−60·−75)은 11.1 M 에서 이미 126.45~126.85 Hz 라 예산이 고칠 "
           "최강선이 남아 있지 않고, el 0 은 예산을 360 배까지 올려도 최강선이 창 안을 옮겨 "
           "다닌다.", "",
           "⇒ 예산이 최강선을 되돌리는 자리는 변조 몫이 이미 큰 앙각이다 — el −30 의 추적 "
           "대역 몫은 " + D87.num("cells.sionna/el-30.share_track_db", fmt="{:.2f}", unit="dB")
           + " 이고 el 0 은 "
           + D87.num("cells.sionna/el+0.share_track_db", fmt="{:.2f}", unit="dB")
           + " 다. 두 앙각을 가르는 것은 표적이 아니라 변조 성분의 크기다."),

        md("## 박자의 참값은 우리가 넣은 입력이다", "",
           "f_flash " + _n("_meta.f_flash_hz", unit="Hz")
           + " 는 로터 회전수에서 나온 **입력값**이다. 네 로터의 회전수는 "
           + _n("_meta.rpm_per_rotor[1]", "{:,.2f}") + " · "
           + _n("_meta.rpm_per_rotor[2]", "{:,.3f}") + " · "
           + _n("_meta.rpm_per_rotor[3]", "{:,.3f}") + " · "
           + _n("_meta.rpm_per_rotor[0]", "{:,.2f}", "rpm")
           + " 이고, 2 엽 기준 `rpm / 60 × 2` 로 바꾸면 126.39 ~ 126.95 Hz 로 흩어져 "
           "있다 — 참값 한 점은 그 넷의 평균 자리다.", "",
           "그래서 이 절이 박자에서 읽는 것은 **같은 입력을 되찾는가**까지다. 그 잣대의 "
           "성질은 " + ref("el-above-tip-limit", "상한 위 누설") + " 가 앙각 여섯 점에서 다룬다."),

        md("## 예산을 고정해도 경로 수는 앙각을 탄다", "",
           f"![ray budget]({FIG}/ch1_f5_raybudget.png)", "",
           caption(2, "같은 광선 예산 아래에서 경로 수는 앙각을 따라 얼마나 달라지는가?"), "",
           "이 스윕은 거리를 10 m 로 고정했으므로 규칙 (R/3)² × 1M 이 주는 예산은 앙각 7 점에 "
           "같은 값 하나다(`benchmark/elevation_sweep_md.py:89`). 앙각을 따라 달라지는 것은 "
           "예산이 아니라 **찾아낸 경로의 수**다."),

        md("규칙값 팔의 경로 수 중앙값은 앙각 7 점에서 "
           + D87.num("gates.G5_sionna_npaths_min_max[0]", fmt="{:.0f}") + "~"
           + D87.num("gates.G5_sionna_npaths_min_max[1]", fmt="{:.0f}", unit="개")
           + ", 손으로 250 M 을 고정한 팔은 "
           + D87.num("gates.G5_sionna_p250000000_npaths_min_max[0]", fmt="{:.0f}") + "~"
           + D87.num("gates.G5_sionna_p250000000_npaths_min_max[1]", fmt="{:.0f}", unit="개")
           + " 로 2.8 배 폭이다. 거리와 무관하게 고정한 팔의 폭이 더 넓으므로, 이 앙각 의존은 "
           "규칙의 거리 항이 만든 것이 아니다.", "",
           "250 M 팔에서 가장 적은 칸이 el 0 의 "
           + _n(f"{_L0[1]}.npaths_median", "{:,.0f}", "개") + " 이고 el −30 은 같은 예산에서 "
           + _n(f"{_L30[1]}.npaths_median", "{:,.0f}", "개") + " 다. 같은 비(1.66 배)가 1 G "
           "계단에서도 " + _n(f"{_L0[2]}.npaths_median", "{:,.0f}") + " 대 "
           + _n(f"{_L30[2]}.npaths_median", "{:,.0f}", "개")
           + " 로 유지되므로, 앙각 의존은 표적을 보는 각도가 만든다.", "",
           "규칙값 팔이 남기는 문제는 축이 섞이는 것이라기보다 **경로가 너무 적은 것**이다 — "
           "6~13 개뿐이라 250 M 팔이 단조 증가로 그리는 추이가 그 팔에서는 나타나지 않는다. "
           "앙각 축 전체의 경로 수 표는 " + ref("el-sweep-design", "앙각 스윕 설계")
           + " 에 있다."),

        md("## 40 m 자리에서는 시드가 같은 크기의 축이다", "",
           "el 0 사다리는 시드 하나로 돈다. 시드 축의 크기는 40 m·el −15 자리에서 시드 "
           + S87.num("cells[0].n_seeds", fmt="{:.0f}", unit="장")
           + " 으로 따로 쟀다 — 시드 간 레벨 표준편차가 "
           + S87.num("cells[0].spp", fmt="{:,.0f}") + " 발에서 "
           + S87.num("cells[0].sd_level_db", fmt="{:.3f}", unit="dB") + ", "
           + S87.num("cells[1].spp", fmt="{:,.0f}") + " 발에서 "
           + S87.num("cells[1].sd_level_db", fmt="{:.3f}", unit="dB") + " 다.", "",
           "그 산포는 자세 평균으로 지워지는 종류가 아니다 — i.i.d. 예측 대비 배수가 "
           + S87.num("cells[0].structure.ratio_observed_over_iid", fmt="{:.2f}") + " 배와 "
           + S87.num("cells[1].structure.ratio_observed_over_iid", fmt="{:.2f}")
           + " 배다⟨outputs/raybudget_seed_ladder.json : verdict.structure_ko⟩. 시드는 "
           "자세마다 다시 뽑는 잡음이 아니라 **광선 방향 집합 하나**를 고르는 일이다."),

        md("같은 판의 박자도 시드마다 갈린다 — 4,000 M 여덟 시드 중 앞의 넷이 "
           + S87.num("cells[1].beats_hz[0]", fmt="{:.2f}") + " · "
           + S87.num("cells[1].beats_hz[1]", fmt="{:.2f}") + " · "
           + S87.num("cells[1].beats_hz[2]", fmt="{:.2f}") + " · "
           + S87.num("cells[1].beats_hz[3]", fmt="{:.2f}", unit="Hz")
           + " 이고, 넷째가 2 차 자리로 넘어가 있다.", "",
           "⚠ 이 시드 판정은 40 m·matrice4e·el −15°·기선 0 한 자리에서 잰 것이다"
           "⟨outputs/raybudget_seed_ladder.json : verdict.caveat_ko⟩. 예산 축을 따라 "
           "판정 통계가 어떻게 움직이는지는 " + ref_old("md-ray-budget", "예산 법칙")
           + " 이 검출 통계 쪽에서 같은 축으로 다룬다.", "",
           "그러므로 el 0 의 박자 흔들림에서 예산 몫과 시드 몫을 가르는 일이 다음 단계 표의 "
           "첫 줄이다."),

        next_steps([
            ("el 0 사다리를 시드 8 장으로 다시 돌린다",
             f"박자 {_n(f'{_L0[1]}.track.beat_hz')}~"
             f"{_n(f'{_L0[0]}.track.beat_hz', unit='Hz')} 의 흔들림이 시드 성질인지 예산 "
             f"성질인지 갈린다",
             "`benchmark/raybudget_seed_ladder.py` 를 10 m·el 0 에 적용 — 새 GPU 계산이 "
             "필요하다"),

            ("광선 규칙 (R/3)² × 1M 에 앙각 항을 넣어 경로 수를 앙각마다 맞춘다",
             "앙각 곡선에서 예산 축이 분리되고, 남는 차이가 표적의 성질로 닫힌다",
             "`benchmark/elevation_sweep_md.py:89` 의 `rule_spp()`"),

            ("최강선 탐색창 40~400 Hz 를 f_flash 배수 기준으로 다시 잡는다",
             f"{_n(f'{_L0[1]}.track.beat_hz')} 와 "
             f"{_n(f'{_L0[0]}.track.beat_hz', unit='Hz')} 가 창 가장자리에 눌린 값인지가 "
             f"확정된다",
             "`benchmark/elevation_sweep_md.py:237` 의 `band_metrics()`"),

            ("el −30 사다리에 4,000 M 계단을 더한다",
             "박자가 붙은 뒤에도 레벨이 계속 오르는지, 어느 계단에서 멈추는지가 정해진다",
             "`benchmark/elevation_sweep_md.py --els -30 --spp 4000000000` — 새 GPU "
             "계산이 필요하다"),
        ]),
    ]


# =========================================================================== #
#  조각 84 — 권 17 절 2 「AC/DC 하락은 분모 쪽 사건이다」
#  ⭐같은 원장(`diag_physics_paths_el-90.json`)의 **AC/DC 열**을 맡는다. 레벨 열의 귀속은
#    조각 83 이 이미 세웠으므로 여기서는 그 위에 «비가 왜 내려갔나» 를 얹는다.
# =========================================================================== #
SWP = from_json("outputs/elevation_sweep_md.json")        # 앙각 스윕 본판
DP45 = from_json("outputs/diag_physics_paths_el-45.json")  # 같은 여섯 판, el −45
DP0 = from_json("outputs/diag_physics_paths_el+0.json")    # 같은 여섯 판, el 0

#: 앙각별 진단판 — (앙각 표기, 원장). 개수·자세 수는 여기서 읽는다.
DIAG_BY_EL = [("−90°", DP), ("−45°", DP45), ("0°", DP0)]

K_BASE = "기준(지금까지의 실행)"
K_REFR = "굴절만 켬"
K_DIFF = "회절만 켬"
K_EDGE = "모서리회절만 켬"
K_MULT = "다중반사만 (depth 3)"
K_ALL = "전부 켬 (--physics)"
CASE_ORDER = [K_BASE, K_REFR, K_DIFF, K_EDGE, K_MULT, K_ALL]


def sw(case: str, field: str, fmt: str, unit: str = "") -> str:
    """스위치 판 한 칸 — `cases.<판>.<양>` 을 원장에서 읽어 출처 태그까지 붙인다."""
    return DP.num(f"cases.{case}.{field}", fmt=fmt, unit=unit)


def _d(case: str, field: str) -> float:
    return float(DP.get(f"cases.{case}.{field}"))


def _d45(case: str, field: str = "level_db") -> float:
    return float(DP45.get(f"cases.{case}.{field}"))


def _d0(case: str, field: str = "level_db") -> float:
    return float(DP0.get(f"cases.{case}.{field}"))


#: 파생값 — 두 원장 칸의 차. 본문에서 두 칸을 각각 인용한 뒤에만 쓴다.
LEVEL_RISE = _d(K_DIFF, "level_db") - _d(K_BASE, "level_db")          # +66.55 dB
ACDC_DROP = _d(K_DIFF, "ac_over_dc_db") - _d(K_BASE, "ac_over_dc_db")  # −69.02 dB
AC_SHIFT = LEVEL_RISE + ACDC_DROP                                      # −2.47 dB (하한)

#: ⭐레벨은 «크기의 평균» mean|E| 이고 AC/DC 의 분모는 «평균의 크기» |mean E|² 다.
#  mean|E| ≥ |mean E| 이므로 레벨은 정적 성분을 δ ≥ 0 만큼 위로 얹어 읽는다. 그 δ 는
#  총전력 부등식이 10·log₁₀(1 + AC/DC) 로 묶는다 — 한쪽으로만 쏠린 **보정항**이지
#  오차막대가 아니다. 회절 판은 AC/DC 가 −68 dB 라 δ ≈ 0, 기준판은 아래 값이 상한이다.
_DELTA_BASE = 10.0 * __import__("math").log10(1.0 + 10.0 ** (_d(K_BASE, "ac_over_dc_db") / 10.0))
_DELTA_DIFF = 10.0 * __import__("math").log10(1.0 + 10.0 ** (_d(K_DIFF, "ac_over_dc_db") / 10.0))
DC_RISE_LO = LEVEL_RISE                       # δ_기준 = 0 일 때
DC_RISE_HI = LEVEL_RISE + _DELTA_BASE         # δ_기준 이 상한일 때
AC_SHIFT_HI = AC_SHIFT + _DELTA_BASE          # 같은 부등식이 주는 위쪽 끝


def _row(engine: str, el_deg: float) -> str:
    """`rows[i]` 의 i 를 (엔진, 앙각)으로 찾는다 — 병합할 때마다 인덱스가 밀리기 때문이다.

    `n_missing == 0` 인 행만 고른다(부분 병합 행은 시계열에 0 이 박혀 있다).
    """
    for i, r in enumerate(SWP.get("rows")):
        if r.get("engine") != engine or abs(float(r.get("el_deg")) - el_deg) > 1e-9:
            continue
        if r.get("n_missing"):
            continue
        return _mark_row(i, engine, el_deg)
    raise ContractError(f"완결된 행이 없다 — engine={engine!r}, el={el_deg}")


R_PHYS90 = _row("sionna_phys", -90.0)      # 물리 팔 나딧 (자세 4,096 · 완결)
R_STOCK90 = _row("sionna", -90.0)          # 물리 끈 팔 나딧 (같은 엔진 계열)

#: 계획 JSON 의 제목은 66.55 dB 를 점값으로 적는다. 두 열의 평균 방식이 달라 그 값은
#  구간의 아래 끝이므로, 이 절의 제목만 «이상» 으로 크기를 맞춘다(원장은 손대지 않는다).
TITLE_84 = (f"AC/DC 가 {_d(K_BASE, 'ac_over_dc_db'):+.2f} dB 에서 "
            f"{_d(K_DIFF, 'ac_over_dc_db'):+.2f} dB 로 내려간 것은 분모가 "
            f"{DC_RISE_LO:.2f} dB 이상 커진 결과다").replace("-", "\u2212")
REG["physics-denominator"] = ("84", TITLE_84)


def blocks_84() -> list:
    return [
        header(
            num=84,
            title=REG["physics-denominator"][1],
            did="스위치를 하나씩 켠 여섯 판의 경로 수·레벨·AC/DC 를 한 표에 놓고, 비가 "
                "내려간 것이 분자 쪽 사건인지 분모 쪽 사건인지를 레벨 열로 갈랐다.",
            results=[
                f"회절을 켜면 레벨이 {sw(K_BASE, 'level_db', '{:.2f}', 'dB')} 에서 "
                f"{sw(K_DIFF, 'level_db', '{:.2f}', 'dB')} 로 {LEVEL_RISE:+.2f} dB 오르고, "
                f"AC/DC 는 {sw(K_BASE, 'ac_over_dc_db', '{:+.2f}', 'dB')} 에서 "
                f"{sw(K_DIFF, 'ac_over_dc_db', '{:+.2f}', 'dB')} 로 {ACDC_DROP:+.2f} dB "
                f"내려간다.",

                f"두 열의 평균 방식이 달라 정적 성분의 상승은 "
                f"{DC_RISE_LO:.2f} ~ {DC_RISE_HI:.2f} dB 구간으로, 변조 성분의 이동은 "
                f"{AC_SHIFT:+.2f} ~ {AC_SHIFT_HI:+.2f} dB 구간으로 묶인다 — 비를 끌어내린 "
                f"것은 분모다.",

                f"경로 중앙값을 {sw(K_BASE, 'npaths_median', '{:.0f}', '개')} 에서 "
                f"{sw(K_REFR, 'npaths_median', '{:.0f}', '개')} 로 줄인 스위치는 굴절이고, "
                f"굴절 판의 레벨은 {sw(K_REFR, 'level_db', '{:.2f}', 'dB')} 로 기준 자리에서 "
                f"1.70 dB 안에 머문다.",

                f"모서리회절 행은 스위치의 크기가 아니라 설정의 항등식이다 — 경로 "
                f"{sw(K_EDGE, 'npaths_median', '{:.0f}', '개')} · 레벨 "
                f"{sw(K_EDGE, 'level_db', '{:.2f}', 'dB')} · AC/DC "
                f"{sw(K_EDGE, 'ac_over_dc_db', '{:+.2f}', 'dB')} 로 기준판의 네 값과 같다.",

                f"자세 {cite_row(SWP, f'{R_PHYS90}.n_poses', fmt='{:,.0f}', unit='개')} 로 돌린 "
                f"스윕 본판의 물리 팔은 "
                f"{cite_row(SWP, f'{R_PHYS90}.level_db', fmt='{:.2f}', unit='dB')} · 경로 "
                f"{cite_row(SWP, f'{R_PHYS90}.npaths_median', fmt='{:.0f}', unit='개')} 로 진단판의 "
                f"«전부 켬» 칸과 같고, 물리를 끈 행은 자세 수를 따라 0.49 dB 옮겨 앉는다.",
            ],
            method=[
                ("AC/DC 의 정의",
                 "자세축 변동 전력 ÷ 자세평균(정적) 성분 전력 [dB] — "
                 "`benchmark/diag_physics_paths.py:76`"),
                ("레벨의 정의",
                 "자세별 복소 합 |E| 의 **크기 평균**을 20·log₁₀ 로 적은 상대량. AC/DC 의 "
                 "분모는 **복소 평균의 크기** |mean E|² 라 서로 다른 양이다"),
                ("분자·분모 가르기",
                 "mean|E| ≥ |mean E| 와 총전력 부등식이 두 양의 간극을 10·log₁₀(1 + AC/DC) "
                 "로 묶는다. 그 부등식으로 정적 성분의 상승과 변조 성분의 이동을 각각 구간으로 "
                 "낸다 — 회절 판은 AC/DC 가 −68 dB 라 간극이 0 이고, 기준판만 폭을 가진다"),
                ("단일축 설계",
                 "광선 예산·자세열·거리·반송주파수·표적을 여섯 판이 공유하고 스위치 하나만 "
                 "바꾼다 — `benchmark/diag_physics_paths.py:33` 의 `CASES`"),
                ("본판 대조",
                 "`outputs/elevation_sweep_md.json` 에서 `n_missing == 0` 인 행만 골라 "
                 "같은 엔진 계열(PathSolver) 안에서만 견준다"),
            ],
            prereq=[
                (ref("physics-single-axis", "스위치 단일축"),
                 "레벨을 올린 스위치가 회절 하나라는 귀속"),
                (ref("el-nadir-floor", "나딧 바닥"),
                 "물리를 끈 우리 커널이 같은 자리에서 무엇을 남기는가"),
            ],
            repro=dict(
                cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                     "benchmark/diag_physics_paths.py -90 20",
                     "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                     "benchmark/build_vol17_switch_fig.py"],
                out=["outputs/diag_physics_paths_el-90.json",
                     "outputs/figures/vol17_f1_switches.png"],
                runtime="약 1 분 (GPU 1 장) + 그림 3 초 (CPU)",
                note="판마다 자세 하나에 걸린 시간은 아래 표의 «초/자세» 칸에 있다"),
        ),

        md("## 비가 내려가는 길은 둘이다", "",
           "AC/DC 는 **변조 전력 ÷ 정적 전력**이다. 비가 내려가는 길은 둘뿐이다 — 분자인 "
           "변조 성분이 줄거나, 분모인 정적 성분이 커지거나.", "",
           "둘을 가르는 잣대는 같은 표의 **레벨 열**이다. 레벨은 자세평균 크기라서 정적 "
           "성분이 커지면 함께 오르고, 변조만 사라지면 제자리에 머문다. 그래서 «비는 "
           "내려갔는데 레벨은 올랐다» 는 곧 분모 쪽 사건이라는 뜻이다."),

        md("## 여섯 판의 값 전체", "",
           DP.table("cases",
                    [("설정", None),
                     ("경로 중앙값", "npaths_median"),
                     ("경로 평균", "npaths_mean"),
                     ("레벨 [dB]", "level_db"),
                     ("AC/DC [dB]", "ac_over_dc_db"),
                     ("초/자세", "sec_per_pose"),
                     ("최대 깊이", "max_depth"),
                     ("굴절", "refraction"),
                     ("회절", "diffraction"),
                     ("모서리회절", "edge_diffraction")],
                    key_col="설정",
                    fmt={"npaths_mean": "{:.2f}", "level_db": "{:.2f}",
                         "ac_over_dc_db": "{:+.2f}", "sec_per_pose": "{:.3f}"},
                    order=CASE_ORDER)),

        md(f"![physics switches]({FIG}/vol17_f1_switches.png)", "",
           caption(1, "스위치 하나를 켜면 경로 수 · 레벨 · 변조비 중 무엇이 움직이나?"), "",
           "세 눈금이 서로 달라 패널을 셋으로 갈랐다. 왼쪽은 0 이 진짜 0 인 개수라 막대이고, "
           "가운데 레벨은 0 이 없는 dB 눈금이라 점으로 놓았다.", "",
           "오른쪽 AC/DC 는 0 dB 를 사이에 두고 갈리므로 0 에서 시작하는 막대다. 색은 "
           "스위치를 따라가고, 세 패널에서 같은 스위치는 같은 색이다."),

        md("## 경로를 무너뜨린 것은 굴절이다", "",
           "굴절을 켜면 경로 중앙값이 " + sw(K_BASE, "npaths_median", "{:.0f}", "개")
           + " 에서 " + sw(K_REFR, "npaths_median", "{:.0f}", "개") + " 로, 평균이 "
           + sw(K_BASE, "npaths_mean", "{:.2f}", "개") + " 에서 "
           + sw(K_REFR, "npaths_mean", "{:.2f}", "개") + " 로 내려간다.", "",
           "굴절 스위치는 표면에 닿은 광선이 **매질 속으로 들어가는 길**을 연다. Sionna 는 "
           "교점마다 반사·확산·투과 중 하나를 |R|²·|T|² 에 비례한 확률로 뽑으므로"
           "(`sionna/rt/radio_materials/radio_material.py:764`~`776`), 투과 계수가 큰 플라스틱 "
           "면에서는 대부분의 광선이 투과 가지로 간다. `max_depth=1` 이라 그 광선은 그 자리에서 "
           "예산을 다 쓴다.", "",
           "⇒ 줄어드는 것은 **발견된 사슬의 수**다. 한 번이라도 발견된 사슬은 이미지법으로 "
           "정확히 다시 풀리므로 진폭은 표본 수와 무관하고, 그래서 경로가 5.5 배 줄어도 레벨은 "
           + sw(K_REFR, "level_db", "{:.2f}", "dB") + " 로 기준판 "
           + sw(K_BASE, "level_db", "{:.2f}", "dB") + " 에서 1.70 dB 안에 머문다.", "",
           "그 1.70 dB 는 나딧의 값이다 — 같은 스위치가 el −45° 에서는 레벨을 "
           + DP45.num(f"cases.{K_BASE}.level_db", fmt="{:.2f}") + " 에서 "
           + DP45.num(f"cases.{K_REFR}.level_db", fmt="{:.2f}", unit="dB") + " 로 내리고, "
           "el 0° 에서는 "
           + DP0.num(f"cases.{K_BASE}.level_db", fmt="{:.2f}") + " 에서 "
           + DP0.num(f"cases.{K_REFR}.level_db", fmt="{:.2f}", unit="dB") + " 다. 그 두 판은 "
           "자세 " + DP45.num("_meta.n_poses", fmt="{:.0f}", unit="개") + " 로 돌린 표본이라 "
           "나딧 판(자세 " + DP.num("_meta.n_poses", fmt="{:.0f}", unit="개")
           + ")과 표본 수가 다르다.", "",
           "나딧 판의 AC/DC 는 "
           + sw(K_REFR, "ac_over_dc_db", "{:+.2f}", "dB") + " 로 올라가는데, 남은 경로 "
           + sw(K_REFR, "npaths_median", "{:.0f}", "개") + " 가 자세마다 크게 흔들린 결과다.", "",
           "굴절 하나는 `--physics` 의 경로 감소를 분해하지 않는다 — 넷을 다 켠 판의 중앙값은 "
           + sw(K_ALL, "npaths_median", "{:.0f}", "개") + " 이고, 회절만 켠 판은 "
           + sw(K_DIFF, "npaths_median", "{:.0f}", "개") + " 로 오히려 늘어난다."),

        md("## 레벨을 올린 것은 회절이고, 그 크기는 판 대 판의 차다", "",
           "회절만 켠 판의 레벨은 " + sw(K_DIFF, "level_db", "{:.2f}", "dB") + " 이고 넷을 다 "
           "켠 판도 " + sw(K_ALL, "level_db", "{:.2f}", "dB") + " 다 — 귀속은 "
           + ref("physics-single-axis", "스위치 단일축") + " 가 세웠다.", "",
           f"⭐ 그 {LEVEL_RISE:.2f} dB 는 «회절 항 대 정반사 항» 의 비가 아니라 **판 대 판의 "
           f"레벨 차**다. 여섯 판 모두 정반사와 확산 반사를 함께 켜고 굴절을 끈 깊이 1 로 "
           f"돌았으므로(`benchmark/diag_physics_paths.py:61`), 기준판의 이름은 «반사만» 이다.", "",
           "이 차에는 등급이 있다 — el −45° 에서 "
           + DP45.num(f"cases.{K_BASE}.level_db", fmt="{:.2f}") + " → "
           + DP45.num(f"cases.{K_DIFF}.level_db", fmt="{:.2f}", unit="dB")
           + f" 로 {_d45(K_DIFF) - _d45(K_BASE):.2f} dB, el 0° 에서 "
           + DP0.num(f"cases.{K_BASE}.level_db", fmt="{:.2f}") + " → "
           + DP0.num(f"cases.{K_DIFF}.level_db", fmt="{:.2f}", unit="dB")
           + f" 로 {_d0(K_DIFF) - _d0(K_BASE):.2f} dB 다 — 두 판 다 자세 "
           + DP45.num("_meta.n_poses", fmt="{:.0f}", unit="개") + " 표본이다.", "",
           f"⭐ 나딧은 표적 바닥이 파면과 정면으로 마주 보는 자리다. 회절을 켠 판은 el 0° 에서 "
           f"나딧까지 {_d0(K_DIFF) - _d(K_DIFF, 'level_db'):.2f} dB 내려가는 동안 반사만 켠 "
           f"판은 {_d0(K_BASE) - _d(K_BASE, 'level_db'):.2f} dB 내려간다. 그래서 이 레벨이 "
           f"묻는 것은 «회절이 그만큼 세다» 가 아니라 «스톡 솔버의 반사 경로가 나딧에서 무엇을 "
           f"잃고 회절 경로가 그 자리를 채우는가» 다."),

        md("## 그래서 −68 dB 는 분모 쪽 사건이다", "",
           "회절 판의 AC/DC 는 " + sw(K_DIFF, "ac_over_dc_db", "{:+.2f}", "dB")
           + f" 라 그 판의 간극 δ 는 {_DELTA_DIFF:.2f} dB 이고, 레벨이 곧 정적 성분이다. "
           f"기준판은 AC/DC 가 " + sw(K_BASE, "ac_over_dc_db", "{:+.2f}", "dB")
           + f" 라 δ 의 상한이 {_DELTA_BASE:.2f} dB 다.", "",
           f"그래서 정적 성분의 상승은 {DC_RISE_LO:.2f} ~ {DC_RISE_HI:.2f} dB 구간이고, 비가 "
           f"{ACDC_DROP:+.2f} dB 내려간 것과 합치면 변조 성분의 이동은 "
           f"{AC_SHIFT:+.2f} ~ {AC_SHIFT_HI:+.2f} dB 구간이다 — 분자는 몇 dB 안에 갇혀 있고, "
           f"수십 dB 움직인 것은 분모다.", "",
           "그러니 「물리를 켜니 나딧 도플러가 이론대로 0 이 됐다」는 문장은 이 분모 상승의 "
           "다른 이름이다. 회절이 정적 성분을 수십 dB 올렸고, 변조는 그 자리에 남았다.", "",
           f"⚠ 레벨차 {LEVEL_RISE:.2f} dB 와 합산값 {AC_SHIFT:+.2f} dB 는 각각 구간의 **끝**으로 "
           f"읽는다. 점값을 내려면 자세별 복소 합을 저장해 |mean E|² 를 직접 재야 하고, 그것이 "
           f"다음 단계 표의 둘째 줄이다."),

        md("## 모서리회절 행은 항등식이고, 깊이 축은 둘째 자리다", "",
           "모서리회절만 켠 판은 경로 " + sw(K_EDGE, "npaths_median", "{:.0f}", "개")
           + " · 레벨 " + sw(K_EDGE, "level_db", "{:.2f}", "dB") + " · AC/DC "
           + sw(K_EDGE, "ac_over_dc_db", "{:+.2f}", "dB") + " 로 기준판과 **네 값이 모두 같다.** "
           "그 스위치가 `diffraction` 의 하위 옵션이라 `diffraction=False` 인 판에서는 계산에 "
           "들어가지 않기 때문이다 — 세 앙각(0°·−45°·−90°) 전부에서 네 값이 똑같이 겹치는 "
           "것이 그 표시다. 모서리회절의 크기는 다음 단계 표의 판이 잰다.", "",
           "다중반사(최대 깊이 " + sw(K_MULT, "max_depth", "{:.0f}") + ")는 이 앙각에서 레벨 "
           + sw(K_MULT, "level_db", "{:.2f}", "dB") + " · AC/DC "
           + sw(K_MULT, "ac_over_dc_db", "{:+.2f}", "dB") + " 로 소수점 둘째 자리에서 갈리고, "
           "경로 중앙값만 " + sw(K_BASE, "npaths_median", "{:.0f}", "개") + " → "
           + sw(K_MULT, "npaths_median", "{:.0f}", "개") + " 로 하나 는다. 세 앙각을 다 보면 "
           f"깊이 축이 레벨을 {abs(_d45(K_MULT) - _d45(K_BASE)):.2f} dB(el −45°), AC/DC 를 "
           f"{abs(_d0(K_MULT, 'ac_over_dc_db') - _d0(K_BASE, 'ac_over_dc_db')):.2f} dB(el 0°) "
           f"안에서 움직인다"
           "⟨outputs/diag_physics_paths_el-45.json : cases.다중반사만 (depth 3).level_db⟩.", "",
           "선행 스위치 연구는 깊이 축에서 갈린다 — 도시 규모 경로손실을 관측량으로 삼은 판은 "
           "`max_depth` 무감을 보고하고, 방위 추정과 라디오맵을 관측량으로 삼은 두 판은 깊이가 "
           "결과를 옮긴다고 적는다"
           "(`prior_work/sionna_solver_settings_survey.md` 의 도시 판·방위 판·라디오맵 판). 우리 소형 표적 "
           "후방산란은 앞쪽과 같은 방향이고, 갈리는 것은 불리언 스위치 쪽이다."),

        md("## 자세 수에 걸리는 칸과 걸리지 않는 칸", "",
           "이 절이 여는 el −90 진단판은 자세 "
           + DP.num("_meta.n_poses", fmt="{:.0f}", unit="개")
           + " 로 돌린 표본이고, el −45·el 0 판은 자세 "
           + DP45.num("_meta.n_poses", fmt="{:.0f}", unit="개")
           + " 다. 같은 스위치를 켜고 자세 "
           + cite_row(SWP, f"{R_PHYS90}.n_poses", fmt="{:,.0f}", unit="개")
           + " 로 돌린 스윕 본판의 나딧 행은 레벨 "
           + cite_row(SWP, f"{R_PHYS90}.level_db", fmt="{:.2f}", unit="dB") + " · 경로 "
           + cite_row(SWP, f"{R_PHYS90}.npaths_median", fmt="{:.0f}", unit="개") + " 로 진단판의 "
           "«전부 켬» 칸과 **같은 값**이다. 그 판은 AC/DC 가 −68 dB 라 자세축 변동이 평균의 "
           "0.04 % 이고, 자세를 몇 개 뽑아도 자세평균 크기가 같은 자리에 온다.", "",
           "물리를 끈 같은 엔진의 나딧 행은 **자세 수에 걸린다** — 본판은 레벨 "
           + cite_row(SWP, f"{R_STOCK90}.level_db", fmt="{:.2f}", unit="dB") + " · 경로 "
           + cite_row(SWP, f"{R_STOCK90}.npaths_median", fmt="{:.0f}", unit="개") + " 이고, 진단판의 "
           "기준 칸은 " + sw(K_BASE, "level_db", "{:.2f}", "dB") + " · "
           + sw(K_BASE, "npaths_median", "{:.0f}", "개") + " 다. 그 판의 AC/DC 가 "
           + sw(K_BASE, "ac_over_dc_db", "{:+.2f}", "dB") + " 라 자세마다 크게 흔들리기 "
           "때문이다. 두 행 모두 자세가 하나도 비지 않은 완결 행이다"
           + row_tag(R_PHYS90 + ".n_missing") + ".", "",
           f"⇒ 이 절의 레벨 상승 {LEVEL_RISE:.2f} dB 는 **el −90 진단판의 자세 "
           f"{int(DP.get('_meta.n_poses'))} 개 기준**으로 닫아 계산한 값이다. 본판 행을 "
           f"피감수로 쓰면 같은 뺄셈이 66.06 dB 가 되므로, 두 판의 행은 따로 읽는다.", "",
           "⚠ 이 대조는 **PathSolver 계열 안에서만** 성립한다. 우리 커널은 정규화가 달라 레벨 축을 "
           "따로 쓴다."),

        md("## 이 판이 서는 범위", "",
           "여섯 줄은 el " + DP.num("_meta.el_deg", fmt="{:+.0f}", unit="°")
           + " 한 점에서, 표적 `" + str(SWP.get("_meta.drone")) + "` 하나로, 거리 "
           + DP.num("_meta.range_m", fmt="{:.0f}", unit="m")
           + " · 반송주파수 3.5 GHz⟨outputs/diag_physics_paths_el-90.json : _meta.fc_hz⟩"
           + " · 광선 "
           + DP.num("_meta.spp", fmt="{:,.0f}", unit="개") + " · 자세 "
           + DP.num("_meta.n_poses", fmt="{:.0f}", unit="개") + " 로 잰 값이다.", "",
           "분자·분모 가르기는 부등식이 주는 **구간**이다. 회절 판은 AC/DC 가 "
           + sw(K_DIFF, "ac_over_dc_db", "{:+.2f}", "dB") + f" 라 간극이 {_DELTA_DIFF:.2f} dB "
           f"이고, 기준판은 " + sw(K_BASE, "ac_over_dc_db", "{:+.2f}", "dB")
           + f" 라 간극의 상한이 {_DELTA_BASE:.2f} dB 다. 그 폭이 "
           f"{AC_SHIFT:+.2f} ~ {AC_SHIFT_HI:+.2f} dB 라는 구간을 만든다.", "",
           f"같은 여섯 판을 돌린 원장은 앙각 {len(DIAG_BY_EL)} 점에 있다 — el "
           + " · el ".join(el for el, _ in DIAG_BY_EL)
           + f" 이고, el −45·el 0 판은 자세 "
           + DP45.num("_meta.n_poses", fmt="{:.0f}", unit="개")
           + " 표본이다. 남은 앙각으로 넓히는 일이 아래 표의 첫 줄이다."),

        next_steps([
            ("같은 여섯 판 분해를 el −15° 에서 자세 20 개로 돌린다",
             "분모 상승이 나딧 전용인지 앙각축 전체인지가 네 점으로 결정된다",
             "`benchmark/diag_physics_paths.py -15 20` — 새 계산이 필요하다"),

            ("회절 판의 자세별 복소 합을 저장해 정적 성분과 변조 성분을 따로 적는다",
             "지금 레벨로 대리한 분모가 직접 측정값으로 바뀐다",
             "`benchmark/diag_physics_paths.py:70` 의 `E` 를 npz 로 남긴다"),

            ("물리 팔 나딧 시계열의 대역 에너지를 운동학 상한과 맞대 본다",
             "회절이 올린 전력이 블레이드가 만들 수 있는 자리에 있는지가 갈린다",
             ref("physics-above-limit", "상한 위 누설")),

            ("회절 판의 광선 예산을 사다리로 올려 레벨이 한 값으로 모이는지 본다",
             "분모 상승이 표본화 잡음인지 수렴값인지 결정된다",
             ref("budget-not-physics", "예산은 물리가 아니다")),
        ]),
    ]


# =========================================================================== #
#  조각 85 — 상한 위 누설: 스위치 축 대 예산 축
# =========================================================================== #
W = from_json("outputs/wideband_energy.json")             # 병합판 대역 에너지
FB = from_json("outputs/wideband_energy_fairbudget.json")  # 공정 예산 팔 + 자기시험

#: 공정 예산(250M) 짝에서 스위치가 상한 위 몫에 남기는 크기 — 앙각마다 다르다.
_FAIR_ELS = ("+0", "-15", "-30", "-45")


def _fair_gap(el: str) -> float:
    return (float(FB.get(f"cells.sionna_p250000000_phys/el{el}.above_f_tip_frac"))
            - float(FB.get(f"cells.sionna_p250000000/el{el}.above_f_tip_frac")))


TITLE_85 = (
    f"광선을 250M 으로 맞추면 물리 스위치가 상한 위 몫에 남기는 것은 앙각 0° 에서 "
    f"{_fair_gap('+0'):.5f} 이고, 기울인 세 앙각에서 "
    f"{min(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f}~"
    f"{max(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f} 다")
REG["physics-above-limit"] = ("85", TITLE_85)

#: el 0 의 다섯 칸 — (표에 쓸 이름, 광선 예산, 물리 스위치, 원장, 칸 키)
#  ⭐우리 커널은 광선 예산 대신 **얼린 격자**로 표본을 잡는다 — 그 판을 원장에서 주입한다.
_ARMS85 = [
    ("우리 커널 (SBR+PO)", SWP.num("_meta.grid_ko"), "PO · 투과 켬 · PTD 끔",
     W, "ours/el+0", None, 0.02285),
    ("PathSolver", "11.1M", "끔", W, "sionna/el+0", 9, 0.29027),
    ("PathSolver", "11.1M", "켬", W, "sionna_phys/el+0", 5, 0.83078),
    ("PathSolver", "250M", "끔", W, "sionna_p250000000/el+0", 127, 0.87023),
    ("PathSolver", "250M", "켬", FB, "sionna_p250000000_phys/el+0", 33, 0.87107),
]


def _leak(cell: str) -> float:
    """상한 위 몫 — 병합판에 있으면 병합판, 없으면 공정예산 원장."""
    src = W if cell in W.get("cells") else FB
    return float(src.get(f"cells.{cell}.above_f_tip_frac"))


def _sec_per_pose(cell: str) -> float:
    r = FB.get(f"rows.{cell}")
    return float(r["seconds"]) / float(r["n_poses"])


def _ratio(off: str, on: str) -> float:
    return float(FB.get(f"rows.{on}.seconds")) / float(FB.get(f"rows.{off}.seconds"))


def _n_scored_els() -> int:
    """이 잣대가 채점하는 앙각 점 수 — f_tip = 0 인 나딧은 몫이 정의되지 않아 빠진다."""
    return sum(1 for c, v in W.get("cells").items()
               if c.startswith("ours/") and "above_f_tip_frac" in v)


def blocks_85() -> list:
    frac = "cells.{}.above_f_tip_frac"
    d_fair = _leak("sionna_p250000000_phys/el+0") - _leak("sionna_p250000000/el+0")
    span = W.get("_meta.nyquist_hz") / W.get("_meta.f_tip_el0_hz")
    r0, r90, r250 = (_ratio("sionna/el+0", "sionna_phys/el+0"),
                     _ratio("sionna/el-90", "sionna_phys/el-90"),
                     _ratio("sionna_p250000000/el+0",
                            "sionna_p250000000_phys/el+0"))

    return [
        header(
            num=85,
            title=TITLE_85,
            did="물리 스위치를 켠 팔의 도플러 에너지를 날개끝 상한 위까지 넓혀 재고, 광선 "
                "예산을 맞춘 짝에서 스위치 축과 예산 축을 앙각 네 점에서 갈랐다.",
            results=[
                f"규칙 예산 11.1M · 앙각 0° 에서 상한 위 몫은 물리 끔 "
                f"{W.num(frac.format('sionna/el+0'), 0.29027, '{:.3f}')} · 물리 켬 "
                f"{W.num(frac.format('sionna_phys/el+0'), 0.83078, '{:.3f}')} 다.",

                f"그 자리에서는 예산 축 혼자서도 같은 상승을 만든다 — 물리를 끈 채 광선만 "
                f"22.5 배 올린 팔이 "
                f"{W.num(frac.format('sionna_p250000000/el+0'), 0.87023, '{:.3f}')} 다.",

                f"광선을 250M 으로 맞춘 짝에서 앙각 0° 의 뺄셈은 {d_fair:.5f} 이고, 그 자리는 "
                f"두 팔이 이미 포화점에 닿아 스위치가 더할 자리가 없는 앙각이다.",

                f"기울인 세 앙각에서는 같은 짝의 스위치가 몫을 "
                f"{min(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f}~"
                f"{max(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f} 올린다 — 예산을 맞춰도 "
                f"스위치가 상한 위 누설을 만든다.",

                f"앙각 0° 의 자세당 경로 중앙값은 250M 에서 "
                f"{FB.num('rows.sionna_p250000000/el+0.npaths_median', 127, '{:.0f}')} → "
                f"{FB.num('rows.sionna_p250000000_phys/el+0.npaths_median', 33, '{:.0f}')} 로 "
                f"줄고, 우리 커널의 같은 칸은 "
                f"{W.num(frac.format('ours/el+0'), 0.02285, '{:.5f}')} 다.",
            ],
            method=[
                ("상한 위 몫",
                 "자세 시계열의 슬로타임 FFT 전력을 |f| ≥ f_tip 에서 합해 그 팔의 전체 "
                 "전력으로 나눈다 — 눈금과 무관한 몫이라 팔끼리 나란히 놓을 수 있는 양이다"),
                ("물리 켬의 뜻",
                 "PathSolver 의 굴절 · 회절 · 모서리회절을 켜고 반사 깊이를 3 으로 둔 실행 "
                 "(`benchmark/elevation_sweep_md.py:179`)"),
                ("두 축",
                 "광선 예산(규칙값 "
                 + num(None, ("outputs/elevation_sweep_md.json", "_meta.sionna_spp"),
                       "{:,.0f}", "광선/자세")
                 + " · 250M)과 물리 스위치(끔 · 켬) 두 축만 움직이고 앙각 0° · "
                 + FB.num("rows.sionna/el+0.n_poses", 4096, "{:.0f}", "자세")
                 + " · 10 m 구면 · 같은 로터 패턴은 고정한다"),
                ("공정 예산 팔",
                 f"샤드를 `idx` 로 제자리에 꽂아 시계열을 복원했다 — 병합기와 같은 조립 "
                 f"규칙이다. 같은 팔은 병합판 원장에도 앙각 {n_arm('sionna_p250000000_phys')[0]}"
                 f" 점 행으로 서 있다"),
                ("자기시험",
                 "이미 병합된 19 칸을 같은 코드로 다시 내 원장과 대조한다"),
            ],
            prereq=[
                (ref("physics-single-axis", "스위치 단일축"),
                 "네 스위치 중 회절 하나가 나딧 레벨을 올린다는 귀속"),
                (ref("el-above-tip-limit", "상한 위 누설"),
                 "f_tip 위로 새는 몫이 팔을 가르는 잣대라는 것"),
            ],
            repro=dict(
                cmd=["PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                     "benchmark/wideband_energy_fairbudget.py",
                     "PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python "
                     "benchmark/fig_fairbudget_leak.py"],
                out=["outputs/wideband_energy_fairbudget.json",
                     "outputs/figures/fairbudget_leak.png"],
                runtime="합쳐 약 2 초 (CPU — 샤드를 읽어 FFT 만 한다)",
                note="병합판 그림·원장은 `benchmark/build_wideband_energy_fig.py` 가 만든 "
                     "그대로 인용한다"),
        ),

        md("## 상한 위 몫이 무엇을 재는가", "",
           f"날개끝 속도가 정하는 도플러 상한은 f_tip = "
           f"{W.num('_meta.f_tip_el0_hz', 1272.9, '{:.1f}', 'Hz')} × cos(앙각) 이다. "
           f"시선 방향으로 가장 빠른 점이 날개끝이므로 그보다 높은 주파수는 블레이드가 "
           f"닿는 자리 밖이고, 거기 담긴 전력은 전부 엔진이 만든 인공물이다.", "",
           f"관찰 상한은 나이퀴스트 "
           f"{W.num('_meta.nyquist_hz', 9850.0, '{:.0f}', 'Hz')} 라, 앙각 0° 에서는 f_tip "
           f"위로 {span:.1f} 배(= 9850 ÷ 1272.9) 폭의 자리를 들여다본다. 그 자리에 무엇이 "
           f"얼마나 앉는지가 이 절의 잣대다.", "",
           "몫은 팔마다 자기 전체 전력으로 나눈 값이라 눈금과 무관하다. 팔 사이 레벨 "
           f"비교는 같은 엔진 안에서만 하고, 그 자리는 {ref('budget-not-physics', '예산 사다리')} 다."),

        md("## 앙각 0° 에서 스위치 축과 예산 축을 따로 움직인다", "",
           table(["팔", "광선 예산", "물리 스위치", "경로/자세(중앙값)", "상한 위 몫"],
                 [[nm, bud, sw,
                   ("—" if npm is None else
                    FB.num(f"rows.{cell}.npaths_median", npm, "{:.0f}", "개")),
                   src.num(frac.format(cell), val, "{:.5f}")]
                  for nm, bud, sw, src, cell, npm, val in _ARMS85])),

        md(f"규칙 예산에서 스위치를 켜면 몫이 "
           f"{W.num(frac.format('sionna/el+0'), 0.29027, '{:.3f}')} 에서 "
           f"{W.num(frac.format('sionna_phys/el+0'), 0.83078, '{:.3f}')} 로 올라간다. "
           f"그 상승은 예산 축 혼자서도 나온다 — 물리를 끈 채 광선만 22.5 배 올린 팔이 "
           f"{W.num(frac.format('sionna_p250000000/el+0'), 0.87023, '{:.3f}')} 다.", "",
           f"두 축을 가르는 자리는 광선을 맞춘 짝이다. 250M 에서 물리 끔 "
           f"{_leak('sionna_p250000000/el+0'):.5f} 대 물리 켬 "
           f"{_leak('sionna_p250000000_phys/el+0'):.5f} 이고, 뺄셈이 {d_fair:.5f} 다.", "",
           f"앙각 0° 가 그렇게 되는 것은 그 자리가 이 잣대의 **포화점**이기 때문이다 — 상한 "
           f"위 대역이 관찰 대역의 {(1.0 - 1.0 / span):.2%} 를 덮으므로, 시간 구조가 남지 않은 "
           f"시계열이 받는 점수가 그 값이다. 두 팔 다 이미 그 포화값에 앉아 있어 스위치가 "
           f"더할 몫은 소수점 넷째 자리에 남는다."),

        md("## 기울인 앙각에서는 예산을 맞춰도 스위치가 몫을 올린다", "",
           table(["앙각", "250M · 물리 끔", "250M · 물리 켬", "뺄셈"],
                 [[f"{el.replace('+0', '0')}°",
                   FB.num(f"cells.sionna_p250000000/el{el}.above_f_tip_frac",
                          fmt="{:.5f}"),
                   FB.num(f"cells.sionna_p250000000_phys/el{el}.above_f_tip_frac",
                          fmt="{:.5f}"),
                   f"{_fair_gap(el):+.5f}"] for el in _FAIR_ELS]), "",
           f"⇒ «상한 위 누설은 광선 표본이 깔아 놓는 바닥이다» 는 **앙각 0° 에서** 성립한다. "
           f"기울인 세 앙각에서는 예산을 맞춘 뒤에도 스위치가 몫을 "
           f"{min(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f}~"
           f"{max(_fair_gap(e) for e in _FAIR_ELS[1:]):.2f} 올리므로, 그 자리의 누설은 물리 "
           f"스위치가 주된 원천이다.", "",
           "이 절의 파생값(차이 · 배율 · 자세당 초)은 전부 표의 칸을 빼거나 나눈 것이고, "
           "칸마다 붙은 각주가 그 원장 파일과 키다."),

        md(f"![wideband energy]({FIG}/wideband_energy.png)", "",
           caption(1, "물리 상한 위로 새는 몫이 팔마다 얼마나 되나?")),

        md(f"![fair budget leak]({FIG}/fairbudget_leak.png)", "",
           caption(2, "광선 예산을 맞추면 물리 스위치가 누설을 얼마나 움직이나?")),

        md("## 같은 광선 수는 팔마다 다른 경로 수로 갈린다", "",
           f"물리를 켜면 광선 하나가 굴절 · 회절 · 모서리회절 · 3 회 반사로 갈라진다. 앙각 0° "
           f"에서 자세당 경로 중앙값은 11.1M 에서 "
           f"{FB.num('rows.sionna/el+0.npaths_median', 9, '{:.0f}')} → "
           f"{FB.num('rows.sionna_phys/el+0.npaths_median', 5, '{:.0f}')}, 250M 에서 "
           f"{FB.num('rows.sionna_p250000000/el+0.npaths_median', 127, '{:.0f}')} → "
           f"{FB.num('rows.sionna_p250000000_phys/el+0.npaths_median', 33, '{:.0f}')} 로 "
           f"줄어든다.", "",
           f"부호는 앙각이 정한다 — 같은 11.1M 짝이 앙각 −30° 에서는 "
           f"{FB.num('rows.sionna/el-30.npaths_median', fmt='{:.0f}')} → "
           f"{FB.num('rows.sionna_phys/el-30.npaths_median', fmt='{:.0f}')} 로 오히려 는다. "
           f"굶기는 스위치는 굴절 하나이고, 회절만 켜면 나딧에서 경로가 늘어난다"
           f"⟨outputs/diag_physics_paths_el-90.json : cases.회절만 켬.npaths_median⟩.", "",
           f"이 열이 세는 것은 **자세당 되돌아온 경로의 개수**이고 표면 표본 밀도는 이 원장 "
           f"밖이다. 그리고 굶음은 같은 예산 짝 안의 상대량이다 — 250M 물리 팔의 "
           f"{FB.num('rows.sionna_p250000000_phys/el+0.npaths_median', 33, '{:.0f}')} 개는 "
           f"규칙 예산 물리 끔 팔의 "
           f"{FB.num('rows.sionna/el+0.npaths_median', 9, '{:.0f}')} 개보다 3.67 배 많다.", "",
           f"그래서 11.1M 짝의 "
           f"{W.num(frac.format('sionna/el+0'), 0.29027, '{:.3f}')} 대 "
           f"{W.num(frac.format('sionna_phys/el+0'), 0.83078, '{:.3f}')} 는 스위치와 경로 수가 "
           f"함께 움직인 값이고, 같은 예산에서 스위치만 남긴 크기는 위 표의 뺄셈 열이다."),

        md("## 비용 — 같은 예산 짝에서 벽시계가 2 배다", "",
           table(["짝", "물리 끔", "물리 켬", "배율"],
                 [["앙각 0° · 11.1M",
                   FB.num("rows.sionna/el+0.seconds", 1549.9, "{:.1f}", "s"),
                   FB.num("rows.sionna_phys/el+0.seconds", 3361.5, "{:.1f}", "s"),
                   f"{r0:.2f} 배"],
                  ["앙각 −90° · 11.1M",
                   FB.num("rows.sionna/el-90.seconds", 1818.0, "{:.1f}", "s"),
                   FB.num("rows.sionna_phys/el-90.seconds", 3621.6, "{:.1f}", "s"),
                   f"{r90:.2f} 배"],
                  ["앙각 0° · 250M",
                   FB.num("rows.sionna_p250000000/el+0.seconds", 1221.3, "{:.1f}", "s"),
                   FB.num("rows.sionna_p250000000_phys/el+0.seconds", 1530.0,
                          "{:.1f}", "s"),
                   f"{r250:.2f} 배"]]), "",
           f"«배율» 은 켬 ÷ 끔 이다. 초를 "
           f"{FB.num('rows.sionna/el+0.n_poses', 4096, '{:.0f}', '자세')} 로 나누면 자세당 "
           f"{_sec_per_pose('sionna/el+0'):.2f} → {_sec_per_pose('sionna_phys/el+0'):.2f} 초"
           f"(앙각 0°), {_sec_per_pose('sionna/el-90'):.2f} → "
           f"{_sec_per_pose('sionna_phys/el-90'):.2f} 초(앙각 −90°) 다."),

        md("이 초는 여러 실행이 같은 GPU 를 나눠 쓴 조건에서 잰 벽시계다. 광선을 22.5 배 더 "
           f"쏜 팔의 벽시계가 오히려 짧은 칸이 있고"
           f"(1221.3 ÷ 1549.9 = {_ratio('sionna/el+0', 'sionna_p250000000/el+0'):.2f} 배), "
           f"같은 스위치의 배율도 {r0:.2f} · {r250:.2f} 로 갈린다. 비용 축은 카드 한 장을 비워 놓고 다시 재야 "
           "확정된다 — 이 절이 비용에 대해 세우는 주장은 «같은 예산 짝에서 켜면 더 걸린다» "
           "까지다."),

        md("## 게이트를 지난 것과 아직 기제 후보인 것", "",
           table(["문장", "상태", "근거"],
                 [[f"250M 짝에서 스위치가 상한 위 몫을 {d_fair:.5f} 움직인다",
                   f"검증됨 — 자기시험 "
                   f"{FB.num('selftest.verdict', 'PASS')}",
                   f"칸 {FB.num('selftest.n_cells_compared', 19, '{:.0f}')} 최대차 "
                   f"{FB.num('selftest.max_abs_diff_frac', 0.0)} · 행 "
                   f"{FB.num('selftest.n_rows_compared', 23, '{:.0f}')} 불일치 "
                   f"{FB.num('selftest.n_row_mismatches', 0, '{:.0f}')}"],
                  ["f_tip 위 에너지는 엔진이 만든 인공물이다", "운동학 정의",
                   "f_tip = 날개끝 속도 / (λ/2) × cos(앙각)"],
                  ["경로 집합이 자세마다 깜빡여 그 에너지를 만든다", "기제 후보 — 게이트 없음",
                   ref("budget-not-physics", "예산 사다리")]])),

        md("## 이 표의 값은 샤드에서, 팔의 행은 병합판에서 온다", "",
           f"이 절은 샤드를 병합기와 같은 규칙(`idx` 로 제자리 꽂기)으로 복원해 읽었고, 그 "
           f"스냅숏 시각은 {FB.num('_meta.snapshot_local', None)} 다. 같은 팔(250M + 물리)은 "
           f"병합판 `outputs/elevation_sweep_md.json` 에 앙각 "
           f"{n_arm('sionna_p250000000_phys')[0]} 점 · 완결 "
           f"{n_arm('sionna_p250000000_phys')[1]} 점으로 서 있다"
           + count_tag("engine=sionna_p250000000_phys 행 수와 그중 n_missing=0 인 행 수")
           + ".", "",
           f"⚠ 그 스냅숏 원장은 `_meta.new_arm_ko` 에 «병합판 원장에는 아직 행이 없는 팔» 이라 "
           f"적는다 — 병합판이 그보다 뒤 판이고, 위의 행 수가 지금 값이다.", "",
           f"자기시험이 그 복원을 보증한다 — 이미 병합된 "
           f"{FB.num('selftest.n_cells_compared', 19, '{:.0f}')} 칸을 같은 코드로 다시 내 "
           f"차이 {FB.num('selftest.max_abs_diff_frac', 0.0)} 이고, 행 "
           f"{FB.num('selftest.n_rows_compared', 23, '{:.0f}')} 개의 초 · 경로 · 레벨도 "
           f"전부 같다."),

        md("### 그 게이트가 덮는 범위", "",
           table(["칸", "무엇이 대조됐나"], [
               ["칸 19 개",
                "우리 커널 · 11.1M · 250M 이 각각 앙각 여섯 점, 그리고 물리 팔의 앙각 0° 한 칸"],
               ["앙각 −90°",
                "f_tip = 0 이라 «상한 위 몫» 이 정의되지 않아 어느 팔도 채점에서 빠진다"],
               ["물리 경로",
                "대역 에너지 원장(`wideband_energy.json`)에 채점 가능한 물리 칸이 앙각 0° "
                "하나뿐이라, 물리 축의 대조는 그 한 점에서 성립한다"],
               ["«최대 차이 0.0»",
                "양쪽 값이 5 자리로 반올림된 상태의 일치다(허용치 1e−5 = 반올림 눈금)"],
               ["행 23 개",
                "스냅숏 시각의 병합판에서 샤드가 없는 행과 미완결 수가 달라진 2 행"
                "(`stale_merge_rows`)을 뺀 나머지 — 지금 병합판은 "
                f"{n_rows()} 행이다" + count_tag("행 수")],
               ["경로 중앙값",
                "우리 커널 7 행은 양쪽 다 값이 비어, 실제로는 Sionna 계열 16 행에서 "
                "비교된다"],
           ]), "",
           "⇒ 이 게이트가 자격을 주는 범위는 **샤드 → 시계열 복원**이다. 대역 규약은 그림 "
           "스크립트와 같은 코드라 같은 오류를 같이 낸다. 원장 한 판으로 좁히는 일은 "
           "`build_wideband_energy_fig.py` 한 번이고, 그 명령은 기존 대역 에너지 원장을 "
           "덮어쓴다."),

        next_steps([
            ("대역 에너지 원장을 지금 병합판으로 다시 낸다",
             f"이 절의 표가 원장 두 파일에서 한 파일로 좁혀지고, 물리 두 팔이 f_tip 이 0 이 "
             f"아닌 앙각 {_n_scored_els()} 점에서 채점된다",
             "`benchmark/build_wideband_energy_fig.py` — 기존 "
             "`outputs/wideband_energy.json` 을 덮어쓰므로 상위 판단이 먼저다"),
            ("카드 한 장을 비우고 같은 예산 짝의 벽시계를 다시 잰다",
             f"스위치의 비용 배율이 {r0:.2f} · {r250:.2f} 중 어디로 수렴하는지 정해진다",
             ref("budget-not-physics", "예산 사다리")),
            ("경로 집합의 자세간 깜빡임을 세어 상한 위 몫과 나란히 놓는다",
             "«광선 표본이 바닥을 깐다» 가 기제 후보에서 게이트 있는 문장으로 올라간다",
             "`benchmark/wideband_energy_fairbudget.py` 에 경로수 시계열 통계 추가"),
        ]),
    ]


# --------------------------------------------------------------------------- #
#  색인 샤드 — 조각마다 하나. `src/make_reports_index.py` 가 병합한다.
#  ⚠ 조각마다 따로 쓰므로 형제 에이전트가 동시에 돌아도 안 부딪친다.
#  ⚠ `part=12` 는 계획 밖 번호다 — 옛 부 0~11 집계를 흔들지 않는다.
# --------------------------------------------------------------------------- #
def write_shard(no: str, anchor: str, rep: dict, evidence: list[str],
                figures: list[str] | None = None) -> None:
    title = REG[anchor][1]
    short = title.split("—")[0].split(",")[0].strip()
    if len(short) > 26:
        short = short[:25].rstrip() + "…"
    shard = dict(
        no=no, anchor=anchor, part=12, part_name="앙각·물리 스위치",
        title=title, short=short,
        file=f"reports/{no}_{anchor}.ipynb",
        builder=f"src/{os.path.basename(__file__)}",
        # 계획(78~87) 안에 있는 조각만 in_plan=True 다. `EXTRA_PARTS` 는 그 뒤에 붙은 절이다.
        in_plan=(anchor not in EXTRA_PARTS), volume="17",
        evidence=list(evidence), from_cells=[],
        figures_used=list(figures or []),
        md_cells=rep["md_cells"], figures=rep["figures"],
        provenance_tags=rep["provenance_tags"],
        negatives=rep["n_negatives"], hedges=rep["n_hedges"], ok=rep["ok"])
    os.makedirs(_SHARD_DIR, exist_ok=True)
    with open(os.path.join(_SHARD_DIR, f"{anchor}.json"), "w", encoding="utf-8") as f:
        json.dump(shard, f, ensure_ascii=False, indent=1)


# =========================================================================== #
#: (번호, 앵커, 블록 함수, 근거 JSON, 쓰는 그림)
REPORTS = [
    ("83", "physics-single-axis", blocks_83,
     ["outputs/diag_physics_paths_el-90.json", "outputs/rt_no_rcs_verify.json"],
     ["report17_switch_axis.png"]),
    ("86", "physics-deck-match", blocks_86,
     ["outputs/physics_vs_deck.json", "outputs/physics_deck_repro_check.json",
      "outputs/elevation_sweep_md.json"],
     ["physics_vs_deck_el-15.png"]),
    ("84", "physics-denominator", blocks_84,
     ["outputs/diag_physics_paths_el-90.json", "outputs/elevation_sweep_md.json"],
     ["vol17_f1_switches.png"]),
    ("87", "budget-not-physics", blocks_87, EVID_87, FIGS_87),
    ("88", "engine-claim-scope", blocks_88,
     ["outputs/diag_physics_paths_el-90.json", "outputs/diag_physics_paths_el-45.json",
      "outputs/diag_physics_paths_el+0.json", "outputs/rt_no_rcs_verify.json",
      "outputs/wideband_energy.json", "outputs/physics_vs_deck.json",
      "outputs/das_fleet_validation.json", "outputs/engine_physics_matrix.json",
      "outputs/po_refinement_survey.json", "outputs/elevation_sweep_md.json"],
     ["ch17_scope_coverage.png"]),
]

#: 조각 85 — 리터럴을 고치지 않고 덧붙인다(형제 조각 편집과 안 부딪치게).
REPORTS.append(("85", "physics-above-limit", blocks_85,
                ["outputs/wideband_energy.json",
                 "outputs/wideband_energy_fairbudget.json",
                 "outputs/elevation_sweep_md.json"],
                ["wideband_energy.png", "fairbudget_leak.png"]))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("── 권 17 「엔진의 물리 스위치」 조각 빌드 ──")
    for no, anchor, fn, evid, figs in REPORTS:
        path = os.path.join(OUT, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, fn(), strict=True)
        write_shard(no, anchor, rep, evid, figs)
    print(f"✅ {len(REPORTS)} 조각 → {os.path.relpath(OUT, _ROOT)}/")


if __name__ == "__main__":
    main()
