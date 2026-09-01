# -*- coding: utf-8 -*-
"""
build_part06_ladder.py — 부 6 「표적 사다리」 → reports/30~33_*.ipynb
==========================================================================================
한 편 = 중심 메시지 하나. 이 부는 네 편이다.

    30 ladder-three      사다리가 하나가 아니라 셋이었다
    31 ladder-calibrated 교정 사다리만 답할 자격이 있다
    32 ladder-answer     모양의 유무 vs 모양의 정밀도
    33 ladder-premature  이 답을 결론이라 못 부르는 이유

서술 원천은 `docs/TARGET_LADDER.md`(문장) 이고 숫자는 `outputs/report16_*.json` 이다.
근거 JSON 은 한 줄도 안 고쳤다 — 서술만 옮겼다.

⭐ 인용 조건 — 종합 판정이 PREMATURE 다. 30~32 를 인용하려면 33 을 함께 읽어야 하고,
   그 사실을 세 편 모두의 여는 블록과 마지막 절이 적는다.

실행
    cd /workspace/sionna
    PYTHONPATH=src ~/.venvs/py312/bin/python src/build_part06_ladder.py

⚠ GPU 도 Sionna 도 필요 없다 — JSON 을 읽어 노트북을 조립할 뿐이다.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, os.path.join(_ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from report_style import (ContractError, build_notebook, caption,   # noqa: E402
                          fetch, header, md, next_steps, num, table, table_from)

# --------------------------------------------------------------------------- #
#  앵커 해결기 — 번호는 실행 계획이 정본이다(`src/report_registry.py` 가 서면 그리로 옮긴다)
# --------------------------------------------------------------------------- #
_PLAN = os.path.join(_ROOT, "outputs", "restruct_exec_plan.json")


def _registry() -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    return {r["anchor"]: (str(r["no"]), r["title_ko"]) for r in plan["reports"]}


REG = _registry()


def ref(anchor: str, short: str | None = None) -> str:
    """`[편 33 «제목»](33_ladder-premature.ipynb)` — 없는 앵커면 빌드가 멈춘다."""
    if anchor not in REG:
        raise ContractError(f"모르는 앵커: {anchor!r} — 실행 계획에 없다")
    no, title = REG[anchor]
    return f"[편 {no} «{short or title}»]({no}_{anchor}.ipynb)"


# --------------------------------------------------------------------------- #
#  근거 JSON
# --------------------------------------------------------------------------- #
SYN = "outputs/report16_synthesis.json"
VK = "outputs/report16_verify_kernel.json"
VD = "outputs/report16_verify_detector.json"
VT = "outputs/report16_verify_tautology.json"
RMF = "outputs/report16_rung_mesh_full.json"    # 사다리 기준선 — 엔진 계약이 여기 적혀 있다
RSE = "outputs/report16_rung_sphere_eqvol.json"   # ⛔ 구 «널» 의 바닥 원장 — 분할 수렴열 네 판이 여기 있다
MSE = "outputs/report16_metric_sphere_eqvol.json"  # ⛔ 12 칸 풀(2 대역 × 3 기체 × 2 파면) — 규약별로 갈라 읽는다
RB = "outputs/report16_base.json"                 # ⛔ 점 간격 세분 대조군(refine_x4)이 여기 있다
P3V2 = "outputs/p3_validation_v2.json"          # 구 대조군 — 어느 부피를 골랐나가 갈리는 곳
P3O = "outputs/p3_ours_v2.json"                 # ①② 축의 상류 — 팔(B)과 기체(Phantom 3)가 여기 적혀 있다

OUT = os.path.join(_ROOT, "reports", "_parts")   # ⭐조각 — 사람이 읽는 문서는 src/build_volumes.py 가 묶은 권이다
FIG = "../outputs/figures"

REPRO = dict(
    cmd="PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py",
    out=[SYN],
    runtime="약 3 초 (CPU — 저장된 위상표 후처리)")

#: 세 편이 공유하는 인용 조건. 여는 블록의 «앞 편에서» 로 나간다.
GATE = [("판정", "종합 판정 PREMATURE — " + ref("ladder-premature", "이르다고 부르는 이유")
         + " 를 함께 읽는다")]


def _n(key: str, fmt: str | None = None, unit: str = "", src: str = SYN) -> str:
    return num(None, (src, key), fmt, unit)


def _fig(no: int, stem: str, question: str) -> list[str]:
    return [f"![{stem}]({FIG}/{stem}.png)", "", caption(no, question)]


# =========================================================================== #
#  편 30 — 사다리가 하나가 아니라 셋이었다
# =========================================================================== #
def blocks_30() -> list:
    A = "ladder_A_as_run.matrice4e"
    K = "shape_vs_kinematics.rows"

    def kin_rows():
        rows = []
        for dk, dn in (("mini2", "Mini 2"), ("matrice4e", "Matrice 4E")):
            for px, pn in (("cube_eqvol", "등가부피 정육면체"),
                           ("box_bbox", "외접 직육면체")):
                b = f"{K}.{dk}.ac_power_db_LENS_CONVENTION.{px}"
                rows.append([dn, pn,
                             _n(b + ".total_db", "{:+.2f}", "dB"),
                             _n(b + ".kinematics_part_db", "{:+.2f}", "dB"),
                             _n(b + ".material_part_db", "{:+.2f}", "dB"),
                             _n(b + ".shape_part_db", "{:+.2f}", "dB"),
                             _n(b + ".kinematics_share", "{:.0%}")])
        return rows

    return [
        header(
            num=30,
            title="사다리가 하나가 아니라 셋이었다 — 여섯 단이 서로 다른 운동학을 쓰고 있었다",
            did="표적을 점점 거칠게 바꾸는 사다리 여섯 단을 돌린 뒤 단마다 «무엇이 도는가» 를 "
                "세어 사다리를 세 벌로 갈랐다.",
            results=[
                f"여섯 단이 같은 운동학을 쓰지 않았다 — 구·정육면체·상자 단은 기체 전체를 "
                f"덩어리로 바꿔 통째로 돌리고, 진짜 드론 단은 몸통이 서고 프로펠러만 돈다.",

                f"그래서 가장 인용하기 좋은 «정육면체 대 메쉬» 차이는 **Mini 2** 에서 "
                f"{_n(K + '.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.total_db', '{:+.2f}', 'dB')} "
                f"이고, 그 안에서 운동학 몫이 "
                f"{_n(K + '.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_part_db', '{:+.2f}', 'dB')}, "
                f"형상 몫이 "
                f"{_n(K + '.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.shape_part_db', '{:+.2f}', 'dB')} 다 — "
                f"**Matrice 4E** 는 같은 규약에서 총 "
                f"{_n(K + '.matrice4e.ac_power_db_LENS_CONVENTION.cube_eqvol.total_db', '{:+.2f}', 'dB')} · "
                f"형상 몫 "
                f"{_n(K + '.matrice4e.ac_power_db_LENS_CONVENTION.cube_eqvol.shape_part_db', '{:+.2f}', 'dB')} 다.",

                f"운동학 비중은 Mini 2 "
                f"{_n(K + '.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')} · "
                f"Matrice 4E "
                f"{_n(K + '.matrice4e.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')} — "
                f"형상 몫보다 크다.",

                f"세 몫의 합은 정의상 총 차이와 닫힌다 — 닫힘오차 "
                f"{_n(K + '.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.closure_err_db', '{:.2f}', 'dB')}.",

                f"그래서 사다리를 A(있는 그대로) · B(온몸 자전 고정) · C(진짜 비행 고정) "
                f"세 벌로 갈라 적는다. 답할 자격은 C 에만 있고 그 편이 "
                + ref("ladder-calibrated", "교정 사다리") + " 다.",
            ],
            method=[
                ("사다리 규약",
                 "기체 mini2 · matrice4e — 있는 그대로의 사다리 표는 matrice4e 이고 "
                 "몫 분해 표는 두 기체를 함께 싣는다 · 반송파 "
                 + _n("protocol.fc_main_hz", "{:.3g}", "Hz") + " · 앙각 "
                 + _n("protocol.el_deg", "{:.0f}", "°") + " · 구면파 · 방위 "
                 + _n("protocol.n_az", "{:.0f}", "점") + " 평균"),
                ("운동학 라벨",
                 "단마다 «무엇이 도는가» 를 산출물에 그대로 적었다 — "
                 "`whole body spins` · `rotors only` · `nothing moves`"),
                ("몫 분해",
                 "총 차이 = 운동학 몫 + 재질 몫 + 형상 몫. 렌즈가 인용한 것과 같은 규약"
                 "(방위평균 AC 전력의 dB 비)으로 다시 계산했다"),
                ("엔진",
                 "표면에 붙은 점구름 위의 순수 PO 다 — "
                 + _n("kinematics_contract.shared.engine", src=RMF)
                 + " 다. 점이 표적과 **함께 돌아** 광선 격자를 쓰지 않으므로, 자세마다 격자를 "
                 "다시 잡는 SBR 쪽 규약은 이 사다리에 들어오지 않는다"),
                ("게이트",
                 "네 파일의 mesh 팔이 비트 단위로 같은지 · 규약이 자기모순인지 · 도플러 칸 "
                 "합이 총 RCS 와 맞는지를 먼저 통과시켰다"),
            ],
            prereq=GATE,
            repro=REPRO,
        ),

        md("## 무엇을 물었나", "",
           "드론이 제자리에 떠 있어도 프로펠러가 돌기 때문에 되돌아오는 전파의 세기와 위상이 "
           "시간에 따라 흔들린다. 이 흔들림을 **마이크로도플러**라고 부른다 — 표적 전체가 "
           "움직여서 생기는 도플러가 아니라 표적의 *일부*(날개)가 움직여서 생기는 도플러라는 뜻이다.",
           "",
           "지도교수의 지적은 «드론 RCS 정밀도는 연구 값어치가 없다» 이고, 절대 세기 축에서는 "
           "우리 데이터가 그 지적을 뒷받침한다. 이 라운드는 그 지적이 마이크로도플러에서도 "
           "성립하는지를 물었다.",
           "",
           "방법은 **사다리**다 — 표적을 점점 거칠게 바꿔 가며 신호가 언제 무너지는지 본다."),

        md("## 사다리를 돌려 보니 여섯 단이 운동학을 섞어 쓰고 있었다", "",
           "구·정육면체·상자 단은 기체 전체를 덩어리 하나로 바꿔 **통째로 돌린** 물체이고, "
           "진짜 드론은 몸통이 서 있고 프로펠러만 돈다. 두 개를 나란히 놓고 «형상 차이» 라고 "
           "부르면 그 안에 형상 교체와 운동학 교체가 섞인다.", "",
           table(["사다리", "무엇이 도나", "무엇이 바뀌나", "질문에 답할 자격"], [
               ["A. 있는 그대로", "단마다 다름", "형상 + 운동학 + 재질", "❌ 섞여 있다"],
               ["B. 온몸 자전 고정", "전부 온몸 자전", "형상만", "△ 실제 드론이 아님"],
               ["C. ⭐ 진짜 비행 고정", "전부 프로펠러만", "**프로펠러 형상만**", "✅ 이 축이 답이다"],
           ])),

        md("## 있는 그대로의 사다리 — 단마다 무엇이 도는가", "",
           table_from(f"{SYN}:{A}",
                      [("표적", None), ("무엇으로 바꿨나", "label_en"),
                       ("무엇이 도나", "kinematics"), ("인용 자격", "quotable")],
                      key_col="표적"), "",
           f"D 단(`mesh_no_rotor`)은 도는 부품이 아예 없다. 변조 전력이 «작다» 가 아니라 "
           f"정확히 0 이라"
           f"(⟨{SYN} : {A}.mesh_no_rotor.ac_power_exactly_zero⟩) "
           f"네 지표 중 셋은 값 자체가 존재하지 않는다 — 아래 표에서 그 단을 뺐다."),

        md("## 같은 사다리를 지표로 읽으면", "",
           table_from(f"{SYN}:{A}",
                      [("표적", None), ("플래시 대조비", "flash_contrast_db.mean"),
                       ("풍부도 n_eff", "n_eff_orders.mean"),
                       ("폭/자기β", "width_ratio_20db.mean"),
                       ("검출 단면적", "sigma_ac_peak_dbsm.mean")],
                      key_col="표적",
                      order=["sphere_eqvol", "cube_eqvol", "box_bbox",
                             "mesh_half_tri", "mesh_full"],
                      fmt={"flash_contrast_db.mean": "{:.2f} dB",
                           "n_eff_orders.mean": "{:.2f}",
                           "width_ratio_20db.mean": "{:.2f}",
                           "sigma_ac_peak_dbsm.mean": "{:.2f} dBsm"}), "",
           "**지표 넷이 무엇을 뜻하나** — 플래시 대조비: 날개가 시선에 수직으로 설 때의 "
           "번쩍임이 바닥보다 몇 dB 위인가. 풍부도 n_eff: 실질적으로 몇 개의 배음이 살아 있나. "
           "폭: 도플러가 날개 끝 속도가 예측하는 만큼 넓게 퍼지나(1.0 이면 딱 맞음). "
           "검출 단면적: 호버 표적이 실제로 쓸 수 있는 «가장 센 배음 한 줄의 RCS»."),

        md("## 인용되는 숫자를 세 몫으로 쪼갠다", "",
           *_fig(1, "report16_synthesis_ladder",
                 "빨간 사다리와 초록 사다리는 같은 단에서 왜 다른 값을 내는가?"),
           "빨간 점선이 있는 그대로의 사다리(운동학이 단마다 바뀐다), 초록 실선이 프로펠러만 "
           "도는 교정 사다리다. 속 빈 표식은 «인용 자격 없음» — 변조 전력의 절반 이상이 "
           "운동학적으로 불가능한 자리에 있다는 뜻이다. E·F 단은 두 사다리에서 같은 팔이라 "
           "빨간 점이 초록 점 아래에 정확히 겹쳐 있다."),

        md("## 운동학 몫이 형상 몫보다 크다", "",
           table(["기체", "대리 형상", "총 차이", "운동학 몫", "재질 몫", "형상 몫",
                  "운동학 비중"],
                 kin_rows()), "",
           "즉 «정육면체가 틀린 이유» 는 대부분 «모양이 거칠어서» 가 아니라 "
           "**«무엇이 도는지를 틀리게 놓아서»** 다. 운동학이 같으면서 날개 디테일만 없앤 "
           "유일한 팔인 `slab` 의 차이는 "
           + _n(f"{K}.mini2.ac_power_db_LENS_CONVENTION.slab_pure_shape_only_db",
                "{:+.2f}", "dB") + " · "
           + _n(f"{K}.matrice4e.ac_power_db_LENS_CONVENTION.slab_pure_shape_only_db",
                "{:+.2f}", "dB") + " 로 훨씬 작다.", "",
           "⚠ 같은 «정육면체 대 메쉬» 라도 무엇을 재느냐에 따라 값이 다르다. 위 표는 절대 AC "
           "전력의 비이고, AC 를 DC(동체 반사)로 나눈 «상대 변조 깊이» 로 재면 "
           + _n(f"{K}.mini2.in_band_modulation_depth_db.cube_eqvol.total_db",
                "{:+.2f}", "dB") + " · "
           + _n(f"{K}.matrice4e.in_band_modulation_depth_db.cube_eqvol.total_db",
                "{:+.2f}", "dB") + " 가 된다. 프리미티브는 동체 반사도 함께 바꾸기 때문이다."),

        next_steps([
            ("운동학을 고정한 교정 사다리로 형상 축만 읽는다",
             "«단순화의 값» 이 형상만의 값으로 확정된다",
             ref("ladder-calibrated", "교정 사다리 편")),
            ("가림(그늘)을 켜고 여섯 단을 다시 채점한다",
             "운동학 몫과 형상 몫의 부호가 가림 아래에서 유지되는지가 갈린다",
             "`benchmark/report16_verify_kernel.py` 의 z-buffer 를 기반 커널로"),
            ("이 부의 숫자를 인용하기 전에 판정 조건을 읽는다",
             "어느 숫자를 부호·자릿수까지만 써야 하는지가 정해진다",
             ref("ladder-premature", "이르다고 부르는 이유")),
        ]),
    ]


# =========================================================================== #
#  편 31 — 교정 사다리만 답할 자격이 있다
# =========================================================================== #
def blocks_31() -> list:
    C = "ladder_C_matched_flight.matrice4e"
    Cm = "ladder_C_matched_flight.mini2"

    return [
        header(
            num=31,
            title="몸통은 진짜 CAD, 프로펠러만 갈아 끼운 교정 사다리가 답할 자격이 있는 유일한 축이다",
            did="여섯 단 전부를 «몸통은 진짜 CAD · 프로펠러만 돈다» 는 같은 운동학에 고정하고 "
                "프로펠러 형상 하나만 바꿔 사다리를 다시 세웠다.",
            results=[
                f"여섯 단이 같은 운동학을 쓴다 — "
                f"{_n(C + '.mesh_full.kinematics')} 하나로 전부 통일했다.",

                f"바뀌는 것은 프로펠러 모양 하나다 — 회전대칭 원판 · 회전반경 위의 공 · "
                f"감싸는 상자 · 평판 두 장 · 삼각형 절반 · 진짜 CAD 여섯 단이다.",

                f"기준선(진짜 CAD)의 검출 단면적은 "
                f"{_n(C + '.mesh_full.sigma_ac_peak_dbsm.mean', '{:.2f}', 'dBsm')}, "
                f"플래시 대조비 "
                f"{_n(C + '.mesh_full.flash_contrast_db.mean', '{:.2f}', 'dB')}, "
                f"풍부도 {_n(C + '.mesh_full.n_eff_orders.mean', '{:.2f}')} 다.",

                f"회전대칭 원판 단만 인용 자격이 "
                f"{_n(C + '.disc.quotable')} 다 — 변조 전력의 "
                f"{_n(C + '.disc.quotable_frac', '{:.0%}')} 만 운동학이 허용하는 자리에 든다.",

                f"이 축의 오차는 전부 **같은 방위끼리** 뺀 값이다 — 방위 "
                f"{_n('protocol.n_az', '{:.0f}', '점')} 을 짝지어 뺐다.",
            ],
            method=[
                ("운동학 고정",
                 "여섯 단 모두 몸통은 진짜 CAD 로 두고 프로펠러 자리에만 대리 형상을 넣는다 — "
                 "도는 것은 언제나 프로펠러다"),
                ("형상 대리 다섯 종",
                 "회전대칭 원판 · 회전반경 위의 공 · 감싸는 상자 · 스팬·두께·부피가 같은 평판 "
                 "두 장 · 삼각형을 절반으로 줄인 CAD"),
                ("짝지어 빼기",
                 "방위마다 진짜 CAD 와 같은 방위끼리 뺀다 — 방위 산포가 오차에 안 섞이게"),
                ("템플릿 손실",
                 "그 형상으로 정합필터 본을 뜨면 잃는 SNR = −20 log10(파형 상관)"),
            ],
            prereq=GATE + [
                ("앞 편", ref("ladder-three", "사다리가 셋이었다") + " — 왜 이 축이 필요한가")],
            repro=REPRO,
        ),

        md("## 왜 이 축만 답할 자격이 있는가", "",
           "«표적을 얼마나 단순화해도 되나» 라는 물음에 답하려면 바뀌는 것이 형상 하나여야 한다. "
           "있는 그대로의 사다리는 형상과 함께 운동학·재질도 바꾸므로 그 답을 못 준다"
           f"({ref('ladder-three', '앞 편')}).", "",
           "교정 사다리는 그 셋 중 둘을 묶는다 — 몸통은 언제나 진짜 CAD 이고, 도는 것은 언제나 "
           "프로펠러다. 그래서 단 사이의 차이는 **프로펠러 모양의 차이**다."),

        md("## 교정 사다리 여섯 단 — Matrice 4E", "",
           table_from(f"{SYN}:{C}",
                      [("프로펠러를 무엇으로", "label_en"),
                       ("플래시 대조비", "flash_contrast_db.mean"),
                       ("풍부도 n_eff", "n_eff_orders.mean"),
                       ("폭/자기β", "width_ratio_20db.mean"),
                       ("동체:날개", "dc_ac_db.mean"),
                       ("검출 단면적", "sigma_ac_peak_dbsm.mean")],
                      fmt={"flash_contrast_db.mean": "{:.2f} dB",
                           "n_eff_orders.mean": "{:.2f}",
                           "width_ratio_20db.mean": "{:.2f}",
                           "dc_ac_db.mean": "{:.2f} dB",
                           "sigma_ac_peak_dbsm.mean": "{:.2f} dBsm"})),

        md("## 같은 사다리 — Mini 2", "",
           table_from(f"{SYN}:{Cm}",
                      [("프로펠러를 무엇으로", "label_en"),
                       ("플래시 대조비", "flash_contrast_db.mean"),
                       ("풍부도 n_eff", "n_eff_orders.mean"),
                       ("폭/자기β", "width_ratio_20db.mean"),
                       ("동체:날개", "dc_ac_db.mean"),
                       ("검출 단면적", "sigma_ac_peak_dbsm.mean")],
                      fmt={"flash_contrast_db.mean": "{:.2f} dB",
                           "n_eff_orders.mean": "{:.2f}",
                           "width_ratio_20db.mean": "{:.2f}",
                           "dc_ac_db.mean": "{:.2f} dB",
                           "sigma_ac_peak_dbsm.mean": "{:.2f} dBsm"})),

        md("## 원판 단이 인용 자격에서 떨어지는 이유", "",
           f"회전대칭 원판은 돌려도 모양이 안 바뀐다. 그래서 변조를 **만들 방법**이 기하학적으로 "
           f"막혀 있고, 남는 것은 격자 잔재다 — 변조 전력의 "
           f"{_n(C + '.disc.quotable_frac', '{:.0%}')} 만 운동학이 허용하는 자리에 든다.", "",
           f"Mini 2 쪽도 같다 — {_n(Cm + '.disc.quotable_frac', '{:.0%}')} 다. "
           f"이 단은 «형상을 얼마나 거칠게 그려도 되나» 의 답이 아니라 "
           f"**«형상을 아예 지우면 어떻게 되나» 의 답**이므로, 사다리의 낭떠러지로 따로 읽는다."),

        next_steps([
            ("교정 사다리의 단별 오차를 진짜 CAD 대비로 읽는다",
             "«얼마나 단순화해도 되나» 의 구간이 dB 로 확정된다",
             ref("ladder-answer", "사다리의 답")),
            ("프로펠러 자리 대리 형상을 부피 보존 여부로 다시 짠다",
             "«단순화의 값» 을 정하는 것이 삼각형 수인지 보존량인지 갈린다",
             "`benchmark/report16_rung_*.py` 확장"),
            ("이 사다리를 검출 통계량(σ_ac_peak · Pd · 검출거리비)으로 다시 채점한다",
             "지표 선택이 결론을 만든 것인지가 정해진다",
             "`benchmark/report16_verify_detector.py` 의 T1 번역기"),
        ]),
    ]


# =========================================================================== #
#  편 32 — 모양의 유무 vs 모양의 정밀도
# =========================================================================== #
def blocks_32() -> list:
    P = "professor_answer.axis4_what_simplification_actually_costs.rows"
    A3 = "professor_answer.axis3_time_modulation"
    FB = "frame_blindness_audit"
    LC = "ladder_C_matched_flight.matrice4e"   # 아랫줄 패널 A~F 의 원장(교정 사다리)

    def cost_rows(dk: str):
        rows = []
        for arm, ko in (("disc", "회전대칭 원판"),
                        ("sph_blade_rg", "회전반경 위의 공"),
                        ("prop_bbox", "감싸는 상자"),
                        ("slab", "평판 두 장 (스팬·부피 보존)"),
                        ("mesh_half_tri", "CAD, 삼각형 절반")):
            b = f"{P}.{dk}.{arm}"
            rows.append([ko,
                         _n(b + ".sigma_ac_peak_err_db", "{:+.2f}", "dB"),
                         _n(b + ".template_loss_db", "{:.2f}", "dB"),
                         _n(b + ".waveform_corr", "{:.3f}")])
        return rows

    return [
        header(
            num=32,
            title="모양의 유무는 수십 dB 를 가르고, 모양의 정밀도는 한 자릿수 dB 안에서 논다",
            did="교정 사다리에서 진짜 CAD 대비 오차를 방위별로 짝지어 빼고 «단순화의 값» 을 "
                "네 구간으로 갈랐다.",
            results=[
                f"**낭떠러지** — 날개를 회전대칭 원판으로 바꾸면 검출 단면적 오차가 "
                f"{_n(P + '.mini2.disc.sigma_ac_peak_err_db', '{:+.2f}', 'dB')} · "
                f"{_n(P + '.matrice4e.disc.sigma_ac_peak_err_db', '{:+.2f}', 'dB')} 다. "
                f"회전대칭체의 참 변조는 정확히 0 이므로 이 두 수가 재는 것은 낭떠러지의 «깊이» "
                f"가 아니라 **메쉬가 우리 점구름의 수치 바닥보다 얼마나 위인가**이고, 그래서 "
                f"부호까지만 인용한다.",

                f"**공짜 구간** — 도는 부품의 삼각형을 절반으로 줄이면 검출 단면적이 "
                f"{_n(P + '.mini2.mesh_half_tri.sigma_ac_peak_err_db', '{:+.2f}', 'dB')} · "
                f"{_n(P + '.matrice4e.mesh_half_tri.sigma_ac_peak_err_db', '{:+.2f}', 'dB')}, "
                f"템플릿 손실이 "
                f"{_n(P + '.matrice4e.mesh_half_tri.template_loss_db', '{:.2f}', 'dB')} 움직인다.",

                f"**싼 구간** — 날개를 평판 두 장으로 바꾸면 검출 단면적이 "
                f"{_n(P + '.mini2.slab.sigma_ac_peak_err_db', '{:+.2f}', 'dB')} · "
                f"{_n(P + '.matrice4e.slab.sigma_ac_peak_err_db', '{:+.2f}', 'dB')} 틀리고 "
                f"템플릿 손실은 "
                f"{_n(P + '.matrice4e.slab.template_loss_db', '{:.2f}', 'dB')} 다.",

                f"«디테일 0 인 평판» 이 «메쉬 − 구» 간격의 "
                f"{_n(A3 + '.but_how_much_of_that_gap_is_cad_precision.share_bought_by_detail_free_slab.matrice4e', '{:.0%}')}~"
                f"{_n(A3 + '.but_how_much_of_that_gap_is_cad_precision.share_bought_by_detail_free_slab.mini2', '{:.0%}')} "
                f"를 이미 산다 — 남는 «CAD 정밀도 단독 몫»(메쉬 − 평판)은 "
                f"{_n(A3 + '.but_how_much_of_that_gap_is_cad_precision.cad_precision_only_db.mini2', '{:.2f}')}~"
                f"{_n(A3 + '.but_how_much_of_that_gap_is_cad_precision.cad_precision_only_db.matrice4e', '{:.2f}', 'dB')} "
                f"다. ⛔ 간격 자체의 크기는 구 널의 격자 바닥이 정하므로 하한으로만 쓴다.",

                f"⚠ «공짜» 는 **도는 부품에 한정된 진술**이다 — 동체까지 깎으면 AC 상대 변화가 "
                f"{_n(FB + '.rows.mini2.ac_relative_difference_frame_decimation.max', '{:.1e}')} "
                f"(기계 정밀도)로, 이 커널에서 동체는 AC 에 정확히 0 을 기여한다.",
            ],
            method=[
                ("오차 정의",
                 "교정 사다리의 각 단을 진짜 CAD 와 **같은 방위끼리** 빼고 방위평균했다"),
                ("검출 단면적 오차",
                 "그 형상을 쓰면 검출 성능이 얼마나 틀리는가 — 가장 센 배음 한 줄의 RCS 차"),
                ("템플릿 손실",
                 "그 형상으로 정합필터 본을 뜨면 잃는 SNR = −20 log10(방위평균 파형 상관)"),
                ("동체 감도",
                 "동체까지 삼각형을 깎아 AC 가 움직이는지를 따로 쟀다 — 커널이 동체를 "
                 "보는지 여부가 «공짜» 의 성립 범위를 정한다"),
            ],
            prereq=GATE + [
                ("앞 편", ref("ladder-calibrated", "교정 사다리") + " — 이 표가 서 있는 축")],
            repro=REPRO,
        ),

        md("## 스펙트로그램 — 같은 축, 같은 색눈금", "",
           *_fig(1, "report16_synthesis_spectrograms",
                 "여섯 표적 모델의 마이크로도플러는 눈으로 얼마나 갈리는가?"),
           "열두 칸 모두 같은 색눈금과 같은 축이다. 세로축은 도플러(Hz), 가로축은 느린 시간(ms), "
           "색은 그 도플러 칸에서 보이는 RCS 다. 점선은 운동학이 예측하는 날개 끝 도플러다. "
           "윗줄이 있는 그대로의 사다리, 아랫줄이 교정 사다리다."),

        md("## 눈으로 읽히는 것 셋", "",
           f"1. 어느 칸에서나 가장 밝은 것은 0 Hz 가로줄 — 몸통이다. 날개 신호는 그보다 한참 "
           f"어둡다. 이 낙차(호버 벌금)가 10 기체 평균 "
           f"{_n('professor_answer.hover_penalty_db.mean_min', '{:.1f}')}~"
           f"{_n('professor_answer.hover_penalty_db.mean_max', '{:.1f}', 'dB')} 다.",
           f"2. 회전대칭 표적(구·원판)은 0 Hz 한 줄만 있고 위아래가 비어 있다. 돌려도 모양이 "
           f"안 바뀌니 변조를 만들 방법이 막힌다 — 이것은 계산 결과가 아니라 기하학이다.",
           f"3. 아랫줄에서 배음 풍부도가 가장 높은 칸은 C(감싸는 상자)·D(평판)이고 "
           f"E·F(진짜 CAD 쪽)에서 내려간다 — Matrice 4E 의 n_eff 는 "
           f"C {_n(LC + '.prop_bbox.n_eff_orders.mean', '{:.2f}')} · "
           f"D {_n(LC + '.slab.n_eff_orders.mean', '{:.2f}')} · "
           f"F {_n(LC + '.mesh_full.n_eff_orders.mean', '{:.2f}')} 다. "
           f"평판이 진짜 CAD 보다 배음이 풍부한 이 역전이 이 편의 핵심 대조이고, "
           f"가림을 켜면 그 부호가 뒤집힌다"
           f"({ref('ladder-premature', '이르다고 부르는 이유')} P2)."),

        md("## 얼마나 단순화해도 되나 — Matrice 4E", "",
           table(["프로펠러를 무엇으로", "검출 단면적 오차", "템플릿 손실", "파형 상관"],
                 cost_rows("matrice4e"))),

        md("## 같은 표 — Mini 2", "",
           table(["프로펠러를 무엇으로", "검출 단면적 오차", "템플릿 손실", "파형 상관"],
                 cost_rows("mini2"))),

        md("## 읽는 법 — 네 구간", "",
           "- **공짜 — 해상도.** 도는 부품의 삼각형을 절반으로 줄이면 검출 단면적이 "
           + _n(P + ".matrice4e.mesh_half_tri.sigma_ac_peak_err_db", "{:+.2f}", "dB")
           + ", 템플릿 손실이 "
           + _n(P + ".matrice4e.mesh_half_tri.template_loss_db", "{:.2f}", "dB")
           + " 움직인다. 잣대는 **같은 양**의 방위 산포다 — 검출 단면적 자체가 방위 "
           + _n(LC + ".mesh_full.sigma_ac_peak_dbsm.n", "{:.0f}", "점")
           + " 사이에서 Mini 2 "
           + _n("ladder_C_matched_flight.mini2.mesh_full.sigma_ac_peak_dbsm.sd", "{:.2f}", "dB")
           + " · Matrice 4E "
           + _n(LC + ".mesh_full.sigma_ac_peak_dbsm.sd", "{:.2f}", "dB")
           + " 흔들리는데, 방위를 짝지어 뺀 이 차이의 표준편차는 그 "
           + _n(LC + ".mesh_half_tri.paired_vs_mesh.d_sigma_ac_peak_db.n", "{:.0f}", "점")
           + " 에서 "
           + _n("ladder_C_matched_flight.mini2.mesh_half_tri.paired_vs_mesh."
                "d_sigma_ac_peak_db.sd", "{:.3f}", "dB")
           + " · "
           + _n(LC + ".mesh_half_tri.paired_vs_mesh.d_sigma_ac_peak_db.sd", "{:.3f}", "dB")
           + " 다. ⚠ 잣대로 "
           + _n(A3 + ".azimuth_sd_db.mesh_max", "{:.2f}", "dB")
           + " 를 쓰던 자리다 — 그것은 다른 양(방위별 총 RCS)의 방위 사이 표준편차를 "
           + _n("level_vs_modulation.modulation_gap_db.n", "{:.0f}", "칸", src=MSE)
           + " 짜리 풀에서 최대로 잡은 값이고, 그 최댓값이 나온 행은 mavic4pro 인데 이 절은 "
             "mini2 · matrice4e 를 다룬다.",
           "- **싼 구간 — 날개를 평판으로.** 스팬·두께·부피가 같은 평판 두 장이면 검출 단면적이 "
           "한 자릿수 dB 안에 든다. «변조가 있나 없나» 만 보는 검출기라면 충분하고, 파형을 "
           "본뜨는 검출기라면 이미 비싸다.",
           "- **비싼 구간 — 날개를 덩어리로.** 감싸는 상자는 속을 꽉 채웠으니 검출 단면적을 "
           "과대하게 낸다. 회전반경 위의 공은 Matrice 4E 에서 레벨만 보면 «잘 맞는» 것처럼 "
           "보이지만 파형 상관이 "
           + _n(P + ".matrice4e.sph_blade_rg.waveform_corr", "{:.3f}")
           + " 뿐이라 템플릿 손실이 "
           + _n(P + ".matrice4e.sph_blade_rg.template_loss_db", "{:.2f}", "dB")
           + " 다 — **레벨이 맞았다고 신호가 맞은 것이 아니다**.",
           "- **낭떠러지 — 회전대칭.** 원판으로 바꾸면 검출 단면적 오차가 "
           + _n(P + ".matrice4e.disc.sigma_ac_peak_err_db", "{:+.2f}", "dB")
           + " 다. 어떤 커널 결함에도 안 흔들리는 것은 **부호**다 — 회전대칭이면 변조가 "
             "원리적으로 0 이라 오차는 음수다. **자릿수는 우리 격자가 정한다**: "
             "원판 팔의 AC 중 운동학이 허용하는 대역에 남는 몫은 Mini 2 "
           + _n("ladder_C_matched_flight.mini2.disc.in_band_ac_frac.mean", "{:.4f}")
           + " · Matrice 4E "
           + _n(LC + ".disc.in_band_ac_frac.mean", "{:.4f}")
           + " 이고(첨두 차수 중앙값 "
           + _n("ladder_C_matched_flight.mini2.disc.peak_order.median", "{:.0f}")
           + " · "
           + _n(LC + ".disc.peak_order.median", "{:.0f}")
           + "), 같은 팔에서 점 간격을 1/4 로 줄이면(점 "
           + _n("point_density_control.deltas.mini2|disc.pts_coarse", "{:.0f}", src=RB)
           + "→"
           + _n("point_density_control.deltas.mini2|disc.pts_fine", "{:.0f}", src=RB)
           + " · "
           + _n("point_density_control.deltas.matrice4e|disc.pts_coarse", "{:.0f}", src=RB)
           + "→"
           + _n("point_density_control.deltas.matrice4e|disc.pts_fine", "{:.0f}", src=RB)
           + ") 동체:날개 비가 "
           + _n("point_density_control.deltas.mini2|disc.delta.dc_ac_db", "{:+.2f}", "dB",
                src=RB)
           + " · "
           + _n("point_density_control.deltas.matrice4e|disc.delta.dc_ac_db", "{:+.2f}", "dB",
                src=RB)
           + " 움직인다. ⛔ 그래서 이 값은 부호까지만 인용한다."),

        md("## 사다리의 순서는 삼각형 수가 아니라 보존량이 정한다", "",
           "감싸는 상자(C)가 평판(D)보다 오차가 큰 것은 «형상 정보가 더 적어서» 가 아니라 "
           "부피를 안 지켜서다. 즉 «단순화의 값» 을 정하는 것은 삼각형 수가 아니라 "
           "**무엇을 보존했는가**(회전대칭 깨짐 → 스팬 → 부피 → 두께 순)다.", "",
           "⭐ 한 줄로: **«모양이 있느냐 없느냐» 는 우리가 잴 수 있는 바닥 끝까지 가르고, "
           "«모양이 얼마나 정밀하냐» 는 한 자릿수 dB 안에서 논다.** 지도교수의 지적은 앞쪽이 "
           "아니라 뒤쪽을 겨눈 것이고, 뒤쪽에서는 지적이 맞는다.", "",
           "⛔ 앞쪽에 자릿수를 붙이는 것은 우리 격자다 — 회전대칭 팔(구·원판)의 참 변조가 "
           "정확히 0 이라 그 자리에 남는 값은 점 간격이 정한 바닥이다. 앞쪽에서 확실한 것은 "
           "부호와 «뒤쪽과 자릿수가 다르다» 까지다."),

        md("## 지도교수 지적에 답한다 — 네 축", "",
           table(["축", "팔", "기체", "무엇을 쟀나", "결과"], [
               ["① 절대 세기", "B — SBR+PO (가림 O)", "Phantom 3", "실측 앵커 대비 rms",
                "자유 모수 "
                + _n("professor_answer.axis1_absolute_level.equal_volume_sphere.n_free_params",
                     "{:.0f}", "개")
                + " 짜리 등가부피 구가 우리 Phantom 3 메쉬를 rms "
                + _n("professor_answer.axis1_absolute_level.sphere_beats_mesh_by_rms_db",
                     "{:.2f}", "dB") + " 이긴다"],
               ["② 방위 산포", "B — SBR+PO (가림 O)", "Phantom 3", "실측 대비 오차",
                "우리 Phantom 3 메쉬 "
                + _n("professor_answer.axis2_azimuth_spread.eps_err_vs_das_db.our_mesh",
                     "{:+.2f}", "dB") + " · 구 "
                + _n("professor_answer.axis2_azimuth_spread.eps_err_vs_das_db.equal_volume_sphere",
                     "{:+.2f}", "dB") + " · 상자 "
                + _n("professor_answer.axis2_azimuth_spread.eps_err_vs_das_db.bounding_box",
                     "{:+.2f}", "dB")],
               ["③ 시간 변조", "P — 순수 PO (가림 X)", "Mini 2 · Matrice 4E",
                "메쉬 − 구 간격 — **하한만**",
                "간격의 크기는 구 널의 격자 바닥이 정한다(바로 아래 ⛔ 절). 그 간격에서 "
                "CAD 정밀도 단독 몫은 "
                + _n(A3 + ".but_how_much_of_that_gap_is_cad_precision.cad_precision_only_db.mini2",
                     "{:.2f}") + "~"
                + _n(A3 + ".but_how_much_of_that_gap_is_cad_precision.cad_precision_only_db.matrice4e",
                     "{:.2f}", "dB") + " 다"],
               ["④ 단순화의 값", "P — 순수 PO (가림 X)", "Mini 2 · Matrice 4E",
                "교정 사다리", "위 두 표가 그 답이다"],
           ]), "",
           "①② 는 Phantom 3 를 B 팔로 잰 축이고 그 엔진은 "
           + num(None, (P3O, "meta.engine")) + " 이며 실측 앵커는 "
           + _n("professor_answer.axis1_absolute_level.measured_anchor")
           + " 다. ③④ 는 Mini 2 · Matrice 4E 를 P 팔로 잰 축이고 그 엔진은 "
           + _n("kinematics_contract.shared.engine", src=RMF) + " 다.", "",
           "① 에서는 지적이 맞는다. ② 는 구가 원리적으로 못 내는 축이다 — 구의 방위 산포는 "
           "«작다» 가 아니라 정확히 0 이고, 회전대칭이라 만들 방법이 막혀 있다. ③ 의 큰 간격은 "
           "«메쉬가 정밀해서» 가 아니라 «회전대칭이 아니라서» 번 것이다.", "",
           "⚠ ① 의 «자유 모수 0 개» 는 **구의 부피를 논문표기 상자로 잡았을 때**의 값이다 — 그 "
           "구는 레벨오차 "
           + num(None, (P3V2, "controls.table.sphere_eqvol_paperbox.level_err_db"),
                 "{:+.2f}", "dB")
           + " 이고, 같은 기체에서 **메쉬 부피**로 잡은 구는 "
           + num(None, (P3V2, "controls.table.sphere_vol_v2.level_err_db"), "{:+.2f}", "dB")
           + " 로 우리 Phantom 3 메쉬 "
           + num(None, (P3V2, "controls.table.ours_phantom3_mesh_v2.level_err_db"),
                 "{:+.2f}", "dB")
           + " 보다 멀다. 즉 이 축의 자유 매개변수는 구의 모수가 아니라 **어느 부피에 맞출지의 "
           "선택**이고, 그 대조군 표는 " + ref("box-sphere-control", "상자·구 대조군") + " 에 있다.",
           "",
           "⭐ 그래서 다시 잡아야 할 방향은 «정밀도» 가 아니라 «무엇이 도는가» 다"
           "(" + ref("ladder-three", "사다리가 셋이었다") + ")."),

        md("## ⛔ ③ 의 분모가 무엇인지 — 구 팔의 값은 격자가 정한다", "",
           "이 편의 규약(반송파 "
           + _n("po_validity.production_band_ghz", "{:.2f}", "GHz")
           + " · 구면파 · 방위 " + _n("protocol.n_az", "{:.0f}", "점") + " 평균)에서 "
             "«메쉬 − 구» 는 Mini 2 "
           + _n("level_vs_modulation.rows.main|mini2|spherical.modulation_gap_db",
                "{:.1f}", src=MSE)
           + " · Matrice 4E "
           + _n("level_vs_modulation.rows.main|matrice4e|spherical.modulation_gap_db",
                "{:.1f}", "dB", src=MSE)
           + " 다. 분모에 서는 구 팔의 값은 경도 분할 수(seg)를 따라간다. 운동학이 허용하는 "
             "대역에 남는 AC 몫은 Mini 2 "
           + _n("null_is_numerical.interpretability.mini2.sphere_in_band_ac_frac",
                "{:.3f}", src=RSE)
           + " · Matrice 4E "
           + _n("null_is_numerical.interpretability.matrice4e.sphere_in_band_ac_frac",
                "{:.3f}", src=RSE)
           + " 인데 같은 표에서 메쉬는 "
           + _n("null_is_numerical.interpretability.mini2.mesh_in_band_ac_frac",
                "{:.3f}", src=RSE)
           + " 이다.", "",
           "seg 를 흔들면 그 바닥이 어디로 가는지 원장이 네 판을 적어 둔다 — Mini 2 는 seg "
           + _n("null_is_numerical.convergence.mini2.refine_x0.5.seg", "{:.0f}", src=RSE)
           + " 에서 "
           + _n("null_is_numerical.convergence.mini2.refine_x0.5."
                "in_band_ac_over_dc_db.mean", "{:.2f}", src=RSE)
           + " · seg "
           + _n("null_is_numerical.convergence.mini2.refine_x1.seg", "{:.0f}", src=RSE)
           + " 에서 "
           + _n("null_is_numerical.convergence.mini2.refine_x1."
                "in_band_ac_over_dc_db.mean", "{:.2f}", src=RSE)
           + " · seg "
           + _n("null_is_numerical.convergence.mini2.refine_x2.seg", "{:.0f}", src=RSE)
           + " 에서 "
           + _n("null_is_numerical.convergence.mini2.refine_x2."
                "in_band_ac_over_dc_db.mean", "{:.2f}", src=RSE)
           + " · seg "
           + _n("null_is_numerical.convergence.mini2.refine_x4.seg", "{:.0f}", src=RSE)
           + " 에서 "
           + _n("null_is_numerical.convergence.mini2.refine_x4."
                "in_band_ac_over_dc_db.mean", "{:.2f}", "dB", src=RSE)
           + " 다. 네 판을 그대로 싣는다 — 이 편이 여기서 쓰는 것은 «구 팔의 값이 seg 와 "
             "함께 움직인다» 까지다.",
           "",
           "⛔ 그래서 ③ 은 **하한**으로만 쓴다. 회전대칭체의 참 변조가 정확히 0 이라 구 팔의 참값이 "
           "−∞ 쪽이고, 잰 값은 우리 점구름이 멈춘 자리다. 평판이 산 몫(%)도 같은 이유로 "
           "하한이다 — 분자·분모가 같은 바닥을 빼고 있어서 바닥이 내려갈수록 그 몫은 커진다."),

        md("## 자기반증 — 이 «공짜» 가 어디까지 참인가", "",
           f"이 커널에서 동체는 AC 에 정확히 0 을 기여한다. 동체를 아무리 깎아도 마이크로도플러 "
           f"지표가 눈금 하나 움직이지 않는 것은 형상의 성질이 아니라 **가림 없는 커널의 성질**이다.",
           "",
           table(["검사", "Mini 2", "Matrice 4E"], [
               ["동체까지 깎았을 때 AC 의 상대 변화",
                _n(FB + ".rows.mini2.ac_relative_difference_frame_decimation.max", "{:.1e}"),
                _n(FB + ".rows.matrice4e.ac_relative_difference_frame_decimation.max", "{:.1e}")],
               ["같은 팔에서 동체:날개 비의 이동",
                _n(FB + ".rows.mini2.dc_ac_shift_from_frame_decimation_db.mean",
                   "{:+.2f}", "dB"),
                _n(FB + ".rows.matrice4e.dc_ac_shift_from_frame_decimation_db.mean",
                   "{:+.2f}", "dB")],
           ]), "",
           f"첫 줄이 기계 정밀도라는 것은 AC 가 동체를 아예 안 본다는 뜻이다. 둘째 줄이 0 에서 "
           f"떨어져 있는 것은 동체 간략화가 «몸통 대 날개 비» 는 움직인다는 뜻이다 — 면적·부피를 "
           f"잃기 때문이다. 가림을 켜면 날개가 동체 뒤로 사라졌다 나타나면서 동체 형상이 AC 에 "
           f"들어오기 시작한다."),

        next_steps([
            ("가림(그늘)을 켜고 교정 사다리 여섯 단을 다시 채점한다",
             "«삼각형 절반은 공짜» 가 유지되면 굳고, 뒤집히면 그 주장을 철회한다",
             "`benchmark/report16_verify_kernel.py` 의 z-buffer 를 기반 커널로"),
            ("프로펠러를 PO 가 유효한 대역으로 올려 사다리를 한 번 더 돌린다",
             "생산 대역의 통과가 형상의 성질인지 파장의 성질인지 갈린다 — 문턱 대역은 "
             + _n("po_validity.blade_knee_ghz", "{:.2f}", "GHz") + " 다",
             ref("ladder-premature", "이르다고 부르는 이유")),
            ("동체 감도를 가림 있는 커널에서 다시 잰다",
             "«공짜» 진술의 성립 범위가 도는 부품 밖으로 넓어지는지가 정해진다",
             "이 편의 자기반증 표를 격자로"),
        ]),
    ]


# =========================================================================== #
#  편 33 — 이 답을 결론이라고 부를 수 없는 이유
# =========================================================================== #
def blocks_33() -> list:
    V = "verdict"
    PO = "po_validity"

    return [
        header(
            num=33,
            title="이 답을 아직 결론이라고 부를 수 없는 이유가 일곱 가지이고, 그중 둘이 치명적이다",
            did="적대검증 세 렌즈를 따로 돌려 사다리의 결론을 어느 수준까지 인용할 수 있는지를 "
                "일곱 항목으로 적었다.",
            results=[
                f"세 렌즈의 판정은 전부 PREMATURE 다 — 자명성 "
                f"{_n(V + '.lenses.tautology')} · 커널 {_n(V + '.lenses.kernel')} · "
                f"검출 {_n(V + '.lenses.detector')}. 종합도 "
                f"{_n(V + '.aggregate')} 다.",

                f"치명적인 것은 둘이다 — (P2) 가림을 넣으면 헤드라인 대조의 부호가 네 구석 "
                f"4/4 에서 뒤집히고, (P4) 인용되는 «정육면체 대 메쉬» 차이의 "
                f"{_n('shape_vs_kinematics.rows.matrice4e.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')}~"
                f"{_n('shape_vs_kinematics.rows.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')} "
                f"가 운동학 몫이다.",

                f"⚠ 그 위에 하나가 더 얹힌다 — 마이크로도플러를 만드는 프로펠러 날개 폭 "
                f"{_n(PO + '.blade_width_mm', '{:.2f}', 'mm')} 는 생산 대역 "
                f"{_n(PO + '.production_band_ghz', '{:.2f}', 'GHz')} 에서 파장의 "
                f"{_n(PO + '.blade_width_over_lambda', '{:.3f}')} 배로, PO 유효 문턱 "
                f"{_n(PO + '.po_knee_a_over_lambda', '{:.3f}')} 배에 "
                f"{_n(PO + '.shortfall_x', '{:.2f}')} 배 모자란다.",

                f"문턱을 넘는 주파수는 {_n(PO + '.blade_knee_ghz', '{:.2f}', 'GHz')} 이고 "
                f"동체는 {_n(PO + '.body_knee_ghz', '{:.2f}', 'GHz')} 부터 유효하다 — "
                f"**커널이 가장 약한 부품이 이 실험의 주인공**이다.",

                f"그래서 이 부의 숫자는 **부호와 자릿수까지** 인용한다 — 소수점은 가림 "
                f"재계산 뒤에 연다.",
            ],
            method=[
                ("적대검증 세 렌즈",
                 "자명성(tautology) · 커널(kernel) · 검출(detector) 을 서로 다른 스크립트로 "
                 "따로 돌리고 각각 독립 재구현으로 표를 다시 만들었다"),
                ("판정 규칙",
                 "세 렌즈 중 둘 이상이 PREMATURE 이면 결론을 그 수준으로 낮춰 적는다 — "
                 "규칙은 결과를 보기 전에 정했다"),
                ("PO 유효 하한",
                 "부품의 특징 폭이 파장의 "
                 + _n(PO + ".po_knee_a_over_lambda", "{:.3f}")
                 + " 배 이상이어야 1 dB 안으로 맞는다는 문턱을 날개 폭과 동체 폭에 각각 적용했다"),
                ("가림 시험",
                 "커널 렌즈가 깊이버퍼 그늘을 넣어 같은 표를 다시 만들고 부호가 유지되는지 봤다"),
            ],
            prereq=GATE,
            repro=dict(
                cmd=["PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_tautology.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_kernel.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_verify_detector.py",
                     "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/report16_synthesis.py"],
                out=[VT, VK, VD, SYN],
                runtime="약 40 분 (GPU 1장 — 커널 렌즈의 가림 재계산이 대부분)"),
        ),

        md("## 세 렌즈가 각각 무엇을 봤나", "",
           table(["렌즈", "무엇을 물었나", "판정"], [
               ["자명성", "인용되는 숫자가 반증 가능한 예측에서 나왔는가",
                _n(V + ".lenses.tautology")],
               ["커널", "그 크기가 커널 결함의 이동보다 큰가",
                _n(V + ".lenses.kernel")],
               ["검출", "그 차이가 검출식에 들어가는가",
                _n(V + ".lenses.detector")],
           ]), "",
           f"{_n(V + '.n_premature_or_broken', '{:.0f}', '개')} 가 PREMATURE 이므로 "
           f"종합 판정도 {_n(V + '.aggregate')} 다."),

        md("## 일곱 가지", "",
           table_from(f"{SYN}:why_premature",
                      [("#", "id"), ("무엇이 문제인가", "claim_ko"), ("숫자", "number_ko")]), "",
           "P1 이 드는 «메쉬 − 구» 간격은 헤드라인 규약(반송파 "
           + _n(PO + ".production_band_ghz", "{:.2f}", "GHz") + " · 구면파 · 방위 "
           + _n("protocol.n_az", "{:.0f}", "점") + " 평균 · mini2 · matrice4e)에서 "
           + _n("level_vs_modulation.rows.main|mini2|spherical.modulation_gap_db",
                "{:.1f}", src=MSE) + "~"
           + _n("level_vs_modulation.rows.main|matrice4e|spherical.modulation_gap_db",
                "{:.1f}", "dB", src=MSE) + " 이고, 원장의 "
           + _n("level_vs_modulation.modulation_gap_db.n", "{:.0f}", "칸", src=MSE)
           + " 을 한 통에 넣으면 "
           + _n("professor_answer.axis3_time_modulation.modulation_gap_mesh_minus_sphere_db.min",
                "{:.1f}") + "~"
           + _n("professor_answer.axis3_time_modulation.modulation_gap_mesh_minus_sphere_db.max",
                "{:.1f}", "dB")
           + " 가 된다. 넓어진 축은 **대역과 파면**이다 — 그 풀은 두 대역("
           + _n(PO + ".production_band_ghz", "{:.2f}") + " · "
           + _n(PO + ".blade_knee_ghz", "{:.2f}", "GHz")
           + ") × 세 기체 × 두 파면이고 각 행이 이미 방위 평균이다"
             "(`benchmark/report16_metric_sphere_eqvol.py` 의 `level_vs_modulation()` 이 "
             "per-az 평균끼리 뺀다). 상한 행은 `hi|matrice4e|plane` — 바로 위 P6 이 «판정이 "
             "뒤집히는 대역» 이라 적은 그 대역의 평면파 대조군이다("
           + ref("ladder-answer", "형상 축의 값") + " 이 헤드라인 규약을 쓰고 이 대조를 "
             "하한으로만 쓴다)."),

        md("## 치명적인 둘", "",
           "**P2 — 커널이 가림(그늘)을 안 본다.** 커널 렌즈가 깊이버퍼 그늘을 넣어 보니, 이 "
           "라운드에서 가장 인용될 대조(«평판이 CAD 보다 배음이 풍부하다», n_eff 간격)가 "
           "두 대역 × 두 기체 네 구석 전부에서 **부호가 뒤집혔다**. 가림 없는 결과는 방향조차 "
           "못 정한다.", "",
           "**P4 — 사다리 여섯 단이 운동학을 섞어 썼다.** «정육면체 대 메쉬» 로 인용되는 차이의 "
           f"{_n('shape_vs_kinematics.rows.matrice4e.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')}~"
           f"{_n('shape_vs_kinematics.rows.mini2.ac_power_db_LENS_CONVENTION.cube_eqvol.kinematics_share', '{:.0%}')} "
           f"가 형상이 아니라 운동학이다"
           f"({ref('ladder-three', '사다리가 셋이었다')}). 교정 사다리가 그 몫을 갈랐으므로 "
           f"P4 는 {ref('ladder-calibrated', '교정 사다리')} 안에서 닫힌다."),

        md("## 프로펠러는 우리 커널의 사각지대다", "",
           f"우리 PO(물리광학) 커널이 1 dB 안으로 맞으려면 부품의 특징 폭이 파장의 "
           f"{_n(PO + '.po_knee_a_over_lambda', '{:.3f}')} 배 이상이어야 한다. 프로펠러 날개 폭 "
           f"{_n(PO + '.blade_width_mm', '{:.2f}', 'mm')} 는 생산 대역 "
           f"{_n(PO + '.production_band_ghz', '{:.2f}', 'GHz')} 에서 파장의 "
           f"{_n(PO + '.blade_width_over_lambda', '{:.3f}')} 배에 그쳐 문턱에 "
           f"{_n(PO + '.shortfall_x', '{:.2f}')} 배 모자란다.", "",
           f"동체는 {_n(PO + '.body_knee_ghz', '{:.2f}', 'GHz')} 부터 유효하므로 통과한다. "
           f"⭐ 즉 **마이크로도플러를 만드는 바로 그 부품이 우리 커널이 가장 약한 부품**이다. "
           f"이 부의 모든 마이크로도플러 숫자는 그 사실을 안고 읽는다.", "",
           f"PO 유효 무릎 자체의 근거는 {ref('po-knee', 'PO 무릎을 부품 폭으로')} 에 있다."),

        md("## 그래서 어디까지 인용해도 되나", "",
           table(["주장", "인용 범위"], [
               ["회전대칭 표적의 변조는 정확히 0 이다", "그대로 인용 — 계산이 아니라 기하학"],
               ["모양의 유무가 큰 간격을 가른다",
                "**부호만** — 크기는 구·원판 팔의 격자 바닥이 정하는 하한이다"],
               ["도는 부품의 삼각형 절반은 공짜다", "부호와 자릿수까지 · 도는 부품에 한정"],
               ["평판 근사는 한 자릿수 dB 다", "부호와 자릿수까지 · 가림 재계산 전"],
               ["«정육면체 대 메쉬» 차이", "교정 사다리 값만 · 있는 그대로의 값은 운동학이 섞임"],
               ["동체 해상도는 무관하다", "가림 없는 커널 안에서만"],
           ])),

        next_steps([
            ("가림(그늘)을 켜고 사다리 전체를 다시 채점한다",
             "«평판이 CAD 보다 배음이 풍부하다» 대조의 부호가 확정되고, "
             "«삼각형 절반은 공짜» 가 굳거나 철회된다",
             "`benchmark/report16_verify_kernel.py` 의 z-buffer 를 기반 커널로 · GPU 반나절"),
            ("지표를 버리고 검출 통계량으로 사다리를 다시 세운다",
             "네 지표 중 셋이 검출식에 안 들어가는 문제가 닫히고, 호버 벌금이 사다리 안으로 들어온다",
             "`benchmark/report16_verify_detector.py` 의 T1 번역기 · CPU 한두 시간"),
            ("프로펠러를 생산 대역부터 무릎 대역 "
             + _n(PO + ".blade_knee_ghz", "{:.2f}", "GHz") + " 위까지 올려 사다리 순서를 본다",
             "생산 대역의 통과가 형상의 성질인지 파장의 성질인지 갈린다 — 문턱은 생산 대역 것을 그대로 쓴다",
             "`benchmark/report16_rung_*.py` · GPU 하루"),
            ("openEMS 같은 정확해로 날개 하나만 교차검증한다",
             "PO 근사의 대가가 dB 로 못 박힌다",
             ref("kernel-open-items", "커널의 열린 항목")),
        ]),
    ]


# --------------------------------------------------------------------------- #
#  색인 샤드 — 편마다 하나. W0 이 `outputs/reports_index.json` 으로 병합한다.
#  ⚠ 편마다 따로 쓰므로 부 에이전트가 동시에 돌아도 안 부딪친다.
# --------------------------------------------------------------------------- #
_SHARD_DIR = os.path.join(_ROOT, "outputs", "reports_index")


def _plan_meta(anchor: str) -> dict:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    for r in plan["reports"]:
        if r["anchor"] == anchor:
            return r
    return {}


def _part_name(part: int) -> str:
    with open(_PLAN, encoding="utf-8") as f:
        plan = json.load(f)
    for p in plan["parts"]:
        if int(p["part"]) == part:
            return p["name"]
    return ""


def write_shard(no: str, anchor: str, rep: dict, part: int) -> None:
    meta = _plan_meta(anchor)
    title = REG[anchor][1]
    short = title.split("—")[0].split(",")[0].strip()
    if len(short) > 26:
        short = short[:25].rstrip() + "…"
    shard = dict(
        no=no, anchor=anchor, part=part, part_name=_part_name(part),
        title=title, short=short,
        file=f"reports/{no}_{anchor}.ipynb",
        builder=f"src/{os.path.basename(__file__)}",
        in_plan=bool(meta),
        evidence=list(meta.get("evidence_json") or []),
        from_cells=list(meta.get("from_cells") or []),
        md_cells=rep["md_cells"], figures=rep["figures"],
        provenance_tags=rep["provenance_tags"],
        negatives=rep["n_negatives"], hedges=rep["n_hedges"], ok=rep["ok"])
    os.makedirs(_SHARD_DIR, exist_ok=True)
    with open(os.path.join(_SHARD_DIR, f"{anchor}.json"), "w", encoding="utf-8") as f:
        json.dump(shard, f, ensure_ascii=False, indent=1)


# =========================================================================== #
REPORTS = [
    ("30", "ladder-three", blocks_30),
    ("31", "ladder-calibrated", blocks_31),
    ("32", "ladder-answer", blocks_32),
    ("33", "ladder-premature", blocks_33),
]


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    print("── 부 6 「표적 사다리」 빌드 ──")
    for no, anchor, fn in REPORTS:
        path = os.path.join(OUT, f"{no}_{anchor}.ipynb")
        rep = build_notebook(path, fn(), strict=True)
        write_shard(no, anchor, rep, 6)
    print(f"✅ {len(REPORTS)} 편 → {os.path.relpath(OUT, _ROOT)}/")


if __name__ == "__main__":
    main()
