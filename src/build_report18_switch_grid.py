# -*- coding: utf-8 -*-
"""
build_report18_switch_grid.py — 리포트 5-2 «물리 스위치 격자» 조립 (별편, reports/05_2_switch-grid.ipynb).

사용자 지시(2026-08-15): 「스위치 7 조합 STFT 맵·blade band energy 를 다 실어 읽기
편하게, **팀미팅 때 보이는 분석 방식**으로」. 그 방식이란:
  · 그림 먼저, 숫자는 그림에서 본 것을 확인하는 자리에만
  · 패널마다 자기 최댓값 정규화 — 모양을 읽고 세기는 안 읽는다
  · 각도는 «−30°» 표기, 쉬운 말, 그림 안 글자는 영어
  · 봉우리의 위치(예측 126.7 Hz 배수에 앉는가)를 항상 함께 본다

이 보고서는 리포트 5 «엔진의 물리 스위치» 의 **별편**이다(외부 빌더 — 엄격 규약 빌더를
안 탄다). 부모의 단일축 귀속을 7 조합 전수 격자로 완결한다.

원장 네 개를 쓴다.
  · outputs/switch_factorial.json (R13) — 몫이 아니라 **절대 dB** 로 다시 읽은 판.
    회절이 리듬을 지우는지 덮는지, 축이 «바꾸는 축» 인지 «얹는 축» 인지가 여기서
    나온다. 리듬 몫·바닥·빗살 솟음·빠진 자세는 전부 이 원장.
  · outputs/switch_grid.json — 아래 네 그림(맵·대역 에너지)을 만든 원장. 1 차 선과
    봉우리 위치 두 열만 여기서 읽는다.
  · outputs/depth_axis_verdict_0816.json — ⛔깊이 절의 정본. R13 의 −60° 실패 쌍을
    «자세 하나의 튐» 으로 철회했고, 표준 프레임 짝의 트림(k1) 채점을 들고 있다.
  · outputs/rhythm_share_knob_audit_0825.json — ⚠리듬 몫이 타는 자유 파라미터(빗살
    반폭)의 흔들기 폭. 깊이 절에서 절대값 인용을 막는 데만 쓴다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/build_report18_switch_grid.py
"""
from __future__ import annotations

import json
import os

import nbformat as nbf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: 그림 원장 — 맵·대역 에너지 네 장과 1 차 선/봉우리 열.
J = json.load(open(f"{ROOT}/outputs/switch_grid.json", encoding="utf-8"))
M, C = J["_meta"], J["cells"]

#: R13 원장 — 절대 dB 판. 이 리포트의 숫자 대부분이 여기서 온다.
F = json.load(open(f"{ROOT}/outputs/switch_factorial.json", encoding="utf-8"))
FM, FC, V = F["_meta"], F["cells"], F["verdict"]
CTRL = F["controls"]
EL = M["el_deg"]

#: ⭐그림 원장(STFT 맵)이 실제로 담은 «다섯 팔». 확산 F 는 다섯 곳 모두 켜져 있다.
#: ⛔여기 이름과 R13 인수분해 원장의 조합 이름을 섞어 쓰면 안 된다 — 같은 말이 다른 조합을
#:   가리킨다. 이 원장의 «굴절+회절» 은 모서리까지 켠 R1D1E1F1(=다 켬)이다.
ORDER = ["Our kernel", "all off (diffuse only)", "refraction",
         "diffraction", "refraction + diffraction"]
KO = {"Our kernel": "우리 커널", "all off (diffuse only)": "다 끔(확산만)",
      "refraction": "굴절", "diffraction": "회절",
      "refraction + diffraction": "굴절+회절"}


def fac(name):
    """그림 원장의 팔을 그대로 들고 가 R13 원장의 −30° 칸을 찾아온다."""
    arm = C[name]["arm"]
    for pool in (FC, F["reference_arms"]):
        for v in pool.values():
            if v["arm"] == arm and v["el_deg"] == EL:
                return v
    raise KeyError(f"{name} ({arm}) 의 el{EL:+.0f} 칸이 R13 원장에 없다")


def facc(combo, depth=1):
    """⭐R13 원장을 «조합 비트» 로 곧장 찾는다 — 그림 원장에 없는 팔도 읽으려고.

    이름이 아니라 R/D/E/F 비트로 짚기 때문에 두 원장의 어휘가 엉킬 자리가 없다."""
    k = f"{combo}_d{depth}/el{EL:+.0f}"
    if k not in FC:
        raise KeyError(f"{k} 가 R13 원장에 없다")
    return FC[k]


def md(*lines):
    return nbf.v4.new_markdown_cell("\n".join(lines))


def ang(x):
    """각도는 «−30°» 표기 — 빼기표(U+2212)를 쓴다(하우스 규약)."""
    return f"{x:.0f}°".replace("-", "−")


# ── 헤드라인 쌍: 판 위(−30°)의 «꼬리표 없는 기본» 칸에서 회절만 켠 짝 ──────────
PAIR = next(p for p in F["diffraction_on_plate_el30"]
            if p["off"] == "R0D0E0F1_d1/el-30")
OFF, ON = FC[PAIR["off"]], FC[PAIR["on"]]
BURIAL = next(b for b in F["diffraction_burial"]
              if b["pair"] == f"{PAIR['off']} → {PAIR['on']}")
BUR_LO = min(b["burial_depth_db"] for b in F["diffraction_burial"])
BUR_HI = max(b["burial_depth_db"] for b in F["diffraction_burial"])

# ── 판 위 깊이 1 칸들의 리듬 몫 범위 — 회절 든 칸 ↔ 안 든 칸 ─────────────────
D1 = [v for v in FC.values()
      if v["el_deg"] == EL and v["depth"] == 1 and not v["zero_echo"]]
ON_SH = [v["rhythm_share_pct"] for v in D1 if v["diffraction"]]
OFF_SH = [v["rhythm_share_pct"] for v in D1 if not v["diffraction"]]
lo_on, hi_on = min(ON_SH), max(ON_SH)
lo_off, hi_off = min(OFF_SH), max(OFF_SH)
WHITE = CTRL["white_share_pct_mean"]
WBAND = F["selfcheck"]["white_control"]["band"]

# ── 모서리 무동작 시험 — 다 끔 ↔ 모서리만, 함께 가진 수치가 몇 개나 같나 ────
_A, _B = facc("R0D0E0F1"), facc("R0D0E1F1")
_NUM = [k for k in _A if k in _B
        and isinstance(_A[k], (int, float)) and not isinstance(_A[k], bool)
        and k not in ("ledger_row", "seconds")]      # ⛔장부 기록·벽시계는 물리가 아니다
#: ⭐표에 실리는 다섯 팔 중 회절이 켜진 행 수 — 손으로 세면 팔이 바뀔 때 낡는다.
_ROWS = [fac(nm) for nm in ORDER]
N_D_ON = sum(1 for v in _ROWS if v.get("diffraction"))
#: 회절 켠 칸의 가장 높은 바닥 ↔ 끈 칸의 가장 낮은 바닥 사이 폭 [dB]
D_FLOOR_LIFT = (max(v["above_floor_db"] for v in _ROWS if v.get("diffraction"))
                - min(v["above_floor_db"] for v in _ROWS
                      if v.get("diffraction") is False))

N_SAME = sum(1 for k in _NUM if _A[k] == _B[k])
N_DIFF = len(_NUM) - N_SAME
#: 딱 하나 어긋나는 칸의 크기 — 배정밀도 끝자리 몇 칸인지 보이려고 절대값으로 든다.
ULP_GAP = max((abs(_A[k] - _B[k]) for k in _NUM if _A[k] != _B[k]), default=0.0)

# ── 덮개 시험 — 판 위 다섯 쌍 ───────────────────────────────────────────────
PL = F["diffraction_on_plate_el30"]
A_LO = min(p["contain_coeff"] for p in PL)
A_HI = max(p["contain_coeff"] for p in PL)
PH_HI = max(abs(p["contain_phase_deg"]) for p in PL)
N_UNIT = sum(1 for p in PL if p["contains_unit_within_3sigma"])
ORTH_GAP = max(abs(p["residual_ac_db"] - p["orthogonal_pred_db"]) for p in PL)
RES_LO = min(p["residual_rhythm_pct"] for p in PL)
RES_HI = max(p["residual_rhythm_pct"] for p in PL)
FL_LO = min(p["d_above_floor_db"] for p in PL)
FL_HI = max(p["d_above_floor_db"] for p in PL)

# ── 적용 범위 — 다른 앙각 ──────────────────────────────────────────────────
SC = F["diffraction_scope_other_elevations"]
Z0 = next(p for p in SC if p["el_deg"] == 0.0)
Z0_OFF = FC[Z0["off"]]
OBL = [p for p in SC if p["el_deg"] < 0.0]
OBL_LO = min(p["d_above_floor_db"] for p in OBL)
OBL_HI = max(p["d_above_floor_db"] for p in OBL)
OBL_BAD = [p for p in OBL if not p["contains_unit_within_3sigma"]]
OBL_LIST = " · ".join(ang(p["el_deg"]) for p in OBL)

# ── 축의 성질 ──────────────────────────────────────────────────────────────
AX = V["E_axis_mechanism"]
LIFT = [AX[k] for k in ("D", "E", "F")]
LIFT_LO = min(a["a_min"] for a in LIFT)
LIFT_HI = max(a["a_max"] for a in LIFT)

# ── 깊이 축 ────────────────────────────────────────────────────────────────
#: ⛔철회 원장 — outputs/depth_axis_verdict_0816.json 이 R13 의 −60° 쌍(B_failures 첫
#:   줄)을 «자세 하나의 튐» 으로 철회했다(closure.retractions_ko · do_not_write_ko).
DA = json.load(open(f"{ROOT}/outputs/depth_axis_verdict_0816.json", encoding="utf-8"))
DA_OF = DA["outlier_forensics"]
DA_SC = DA["scorecard"]
OUT60 = DA_OF["el60_case"]
TRIM60 = OUT60["drop_one_pose"]
#: 회절 켠 팔의 재실행 문턱 — 같은 물리를 두 이름으로 독립 재실행한 폭.
RERUN = DA["null_bands"]["pathsolver_repeatability"]["diffraction_on"]["band_ac_db"]
#: 표준 프레임이 싣는 두 팔(PS 다 끔 · PS 굴절만)의 깊이 짝. 채점은 원장 규약대로
#: «가장 튄 자세 1 개를 뺀» k1 판으로 한다(scorecard.band_rule_ko 마지막 줄).
SF = [p for p in DA["pairs"] if p["in_standard_frame"]]
SF_RHY = max(abs(p["trim"]["k1"]["d_rhythm_pp"]) for p in SF)
#: 빗살 대비는 «값이 잡히는 빗각·거리 칸» 에서만 잰다 — 판 밖 −90° 는 값 자체가 없고
#: 정면 0° 는 이 범위 밖이다(closure.closed_part_ko 가 못 박아 둔 범위).
SF_CMB = [p["trim"]["k1"]["d_comb_contrast_db"] for p in SF if p["el_deg"] < 0.0]
SF_CMB_OBL = [c for c in SF_CMB if c is not None]
SF_CMB_HI = max(abs(c) for c in SF_CMB_OBL)
SF_C0 = next(p["trim"]["k1"]["d_comb_contrast_db"] for p in SF if p["el_deg"] == 0.0)
SF_EL = sorted({p["el_deg"] for p in SF}, reverse=True)
SF_RG = sorted({p["range_m"] for p in SF})
#: ⚠리듬 몫이 타는 자유 파라미터(빗살 반폭)의 기하학적 바닥 — 흔들기 폭을 함께 적는다.
HWF = json.load(open(f"{ROOT}/outputs/rhythm_share_knob_audit_0825.json",
                     encoding="utf-8"))["기하학적_바닥_2hw_over_fflash"]
HW_LO, HW_HI = HWF["hw=2.0"], HWF["hw=32.0"]

BF = V["B_failures"]
#: ⛔철회된 −60° 쌍을 뺀 «살아 있는» 실패 쌍. 개수를 인쇄할 때는 이쪽을 쓴다.
BF_LIVE = [b for b in BF
           if not (b["combo"] == "R0D0E0F1" and b["el_deg"] == -60.0)]
BF_PLATE = [b for b in BF_LIVE if b["el_deg"] == EL]
#: 판 위 실패 쌍의 «세 열 전부» 폭 — 세기 최대치와 바닥 차의 최소치를 함께 훑는다.
PL_SPAN = [v for b in BF_PLATE for v in (b["max_abs_level_db"], b["d_above_floor_db"])]
PL_LO, PL_HI = min(PL_SPAN), max(PL_SPAN)
D60 = next(p for p in F["depth_pairs"]
           if p["combo"] == "R0D0E0F1" and p["el_deg"] == -60.0 and p["depths"] == [1, 3])
D60_1, D60_3 = FC[D60["d1"]], FC[D60["dN"]]
#: 튐 자세의 둘째 대비 — 고립도 = 최대 ÷ 둘째(outlier_forensics.isolation_def_ko).
P60_TOP2 = OUT60["pose_over_median_dN"] / OUT60["isolation_dN"]
ROT60_TXT = " · ".join(f"{r:.2f}"
                       for r in OUT60["rotor_symmetry_partners_over_median"][1:])


#: 순정 기본값의 «에코 0» 칸 — 돌렸는데 경로가 0 이라는 증거.
ZE = [v for k, v in F["zero_echo_proof"].items() if "stockdef" in v["arm"]]
ZE_SHARDS = sorted({v["n_shards"] for v in ZE})


def axis_table():
    rows = ["| 스위치 | 쌍 수 | 담김계수 a | 읽는 법 |", "|---|---|---|---|"]
    for k in ("R", "D", "E", "F"):
        a = AX[k]
        rows.append(f"| {k} — {FM['switch_meaning_ko'][k]} | {a['n_pairs']} | "
                    f"{a['a_min']:.2f}~{a['a_max']:.2f} (가운데 {a['a_median']:.2f}) | "
                    f"{a['reads_ko']} |")
    return "\n".join(rows)


def table():
    rows = ["| 조합 | 리듬 몫 [%] | 상한 위 바닥 [dB] | 빗살 솟음 [dB] | 1차 선 [dB] | "
            "봉우리 [Hz] | 빠진 자세 |",
            "|---|---|---|---|---|---|---|"]
    for nm in ORDER:
        g, f = C[nm], fac(nm)
        rows.append(f"| {KO[nm]} ({nm}) | {f['rhythm_share_pct']:.2f} | "
                    f"{f['above_floor_db']:.1f} | {f['comb_over_floor_db']:+.1f} | "
                    f"{g['h1_over_floor_db']:.1f} | {g['h1_peak_hz']:.1f} | "
                    f"{f['n_missing']} |")
    return "\n".join(rows)


nb = nbf.v4.new_notebook()
nb.cells = [
    md("# 리포트 5-2 — 물리 스위치 격자: 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다",
       "",
       "이 편은 [리포트 5 «엔진의 물리 스위치»](05_engine-physics.ipynb) 의 **별편**이다.",
       "",
       f"**판**: {M['setup_ko']} · 앙각 {ang(EL)} 한 자리. 갈리는 축은 굴절 R · "
       f"회절 D · 모서리회절 E 세 스위치뿐이다.",
       "",
       "### 한 일",
       "> 세 스위치의 의미 있는 조합 7 개를 같은 자리·같은 광선 예산(4×10⁹ 발)에서 "
       "**몫이 아니라 절대 dB** 로 재어, 회절이 리듬을 지우는지 덮는지를 갈랐다. "
       "일곱 칸 모두 확산은 켠 채다 — 이 표적은 확산을 끄면 비스듬한 각에서 에코가 아예 "
       "없어 견줄 것이 남지 않는다(절 «영 에코»). STFT 맵과 블레이드 대역 에너지는 그 중 "
       "**다섯 팔**(다 끔·굴절·회절·굴절+회절, 그리고 우리 커널)에 대해 그렸다. 우리 "
       "커널은 광선 예산 축 밖의 별개 엔진이라 기준 팔로만 함께 둔다.",
       "",
       "### 결과",
       f"1. ⭐**회절 스위치 하나가 경계선이다** — 회절을 켜면 상한 위 **바닥이 "
       f"{PAIR['d_above_floor_db']:+.1f} dB**({OFF['above_floor_db']:.1f} → "
       f"{ON['above_floor_db']:.1f} dB) 오르고, 빗살 선의 바닥 위 솟음은 "
       f"{OFF['comb_over_floor_db']:+.1f} dB → {ON['comb_over_floor_db']:+.1f} dB 로 "
       f"무너진다. 리듬 몫이 {lo_on:.1f}~{hi_on:.1f} %(백색 = {WHITE:.1f})로 떨어진 것은 "
       f"분자가 준 것이 아니라 **분모가 커진 것**이다. 회절이 없는 칸은 "
       f"{lo_off:.1f}~{hi_off:.1f} %.",
       f"2. ⭐**회절이 얹는 것은 리듬 없는 에코다** — 회절을 켠 시계열은 끈 시계열을 계수 "
       f"{PAIR['contain_coeff']:.2f}·위상 {PAIR['contain_phase_deg']:.1f}° 로 그대로 품고 "
       f"있고, 뺀 나머지에는 날개 박자가 없다(몫 {RES_LO:.1f}~{RES_HI:.1f} % = 백색). "
       f"원래 빗살은 새 바닥보다 {BURIAL['burial_depth_db']:.1f} dB 아래에 잠겨 있을 뿐 "
       f"사라지지 않았다 — 아래 «덮개 시험» 절.",
       f"3. ⭐**바꾸는 축은 하나, 얹는 축이 셋이다** — 굴절 R 만 원래 시계열 자체를 다른 "
       f"것으로 만들고(담김계수 {AX['R']['a_min']:.2f}~{AX['R']['a_max']:.2f}), 회절 D · "
       f"모서리 E · 확산 F 는 원래 것을 남긴 채 위에 새 항을 더한다"
       f"(≈{LIFT_LO:.2f}~{LIFT_HI:.2f}).",
       f"4. **모서리회절 스위치는 혼자서는 아무것도 안 한다** — 그것만 켠 칸은 다 끈 칸과 "
       f"리듬 {facc('R0D0E1F1')['rhythm_share_pct']:.2f} %, 바닥 "
       f"{facc('R0D0E1F1')['above_floor_db']:.1f} dB 로 같다. 두 칸이 함께 가진 물리 수치 "
       f"{N_SAME + N_DIFF} 개 가운데 {N_SAME} 개가 비트단위로 같고, 남은 {N_DIFF} 개도 "
       f"배정밀도 끝자리 차이(Δ = {ULP_GAP:.1e})다 — 갈리는 것은 원장 줄번호와 벽시계뿐. "
       f"모서리회절 후보를 만드는 자리가 회절 스위치 안에 있기 때문이다.",
       f"5. **굴절은 깎지만 죽이지 않는다** — 혼자 켜면 리듬 "
       f"{facc('R0D0E0F1')['rhythm_share_pct']:.1f} → "
       f"{facc('R1D0E0F1')['rhythm_share_pct']:.1f} %, 빗살 솟음 "
       f"{facc('R0D0E0F1')['comb_over_floor_db']:+.1f} → "
       f"{facc('R1D0E0F1')['comb_over_floor_db']:+.1f} dB. 선의 자리는 "
       f"{C['refraction']['h1_peak_hz']:.1f} Hz 로 그대로다.",
       f"6. **봉우리 위치는 다섯 팔 전부 "
       f"{C['refraction + diffraction']['h1_peak_hz']:.1f} Hz** — 예측 "
       f"{M['f_flash_hz']:.1f} Hz 의 자리다. 위치가 아니라 **선명도**가 갈린다.",
       f"7. ⚠**사전등록 문턱 밖에 남은 것은 회절 켠 조합의 절대 레벨 하나다** — 깊이 "
       f"1↔3 을 견준 {V['B_n_pairs_1to3']} 쌍 중 문턱 밖은 판 위({ang(EL)}) R1D1** "
       f"{len(BF_LIVE)} 쌍(깊이 3 에서 세 열 전부 +{PL_LO:.1f}~+{PL_HI:.1f} dB)이고, "
       f"그 +2 dB 의 기전은 아직 안 세워졌다. ⛔전 판이 여기 함께 적었던 «판 밖 −60° 의 "
       f"리듬 붕괴» 는 그 칸 자세 {OUT60['n_poses']:,} 개 중 하나가 만든 값이라 "
       f"**철회했다**(2026-08-16) — 아래 «깊이» 절.",
       "",
       "### 잣대 — 무엇을 재나 (쉬운 말)",
       "- **상한 위** — 날개 끝이 낼 수 있는 최고 도플러(f_tip) **위쪽** 자리. 몸통은 "
       "여기까지 못 온다. 즉 날개만 만들 수 있는 구역이다.",
       "- **바닥** — 상한 위에서 빗살 자리를 뺀 나머지 에너지. 리듬이 없는 부분이다.",
       f"- **빗살** — 예측 박자 {M['f_flash_hz']:.1f} Hz 의 정수배 ±{FM['comb_half_width_hz']:.0f} Hz "
       f"자리. 날개 플래시가 앉는 곳이다.",
       "- **빗살 솟음** — 빗살 자리의 빈 하나당 에너지를 바닥 빈 하나당 에너지로 나눈 것. "
       "0 dB 면 «선이 없다 = 백색» 이라는 뜻이다.",
       f"- **리듬 몫** — {M['rhythm_ko'].replace('백색잡음 13', f'백색 {WHITE:.1f}')}. "
       f"몫이라서 바닥이 커져도 내려간다 — 그래서 절대 dB 를 함께 본다.",
       f"- **1차 선** — {M['h1_ko']}",
       "",
       f"⭐{FM['units_ko']}"),

    md("## 맵 — 다섯 팔이 같은 자리에서 그린 것",
       "",
       "![switch grid maps](../outputs/figures/swgrid_maps.png)",
       "",
       "**그림 1.** 스위치를 바꿔 끼우면 맵이 어떻게 변하나? 패널마다 자기 최댓값 기준이라 "
       "모양만 읽는다.",
       "",
       "읽는 법: 시간축으로 규칙적으로 지나가는 덩어리가 날개, 가운데 가로띠가 동체다. "
       "왼쪽 세 패널(우리 커널 · 다 끔 · 굴절)에는 날개 플래시가 또렷하고, 오른쪽 두 "
       "패널 — 회절이 켜지는 순간 — 무늬가 세로 얼룩으로 바뀐다.",
       "",
       "⚠패널마다 따로 정규화했기 때문에 이 그림은 **모양**만 말한다. 회절 켠 패널의 "
       "얼룩이 원래 플래시보다 얼마나 센지는 뒤의 절대 dB 그림에서 읽는다."),

    md("## 같은 맵, 정지 성분 제거",
       "",
       "![switch grid maps dc removed](../outputs/figures/swgrid_maps_dc.png)",
       "",
       "**그림 2.** 가만히 있는 부분(동체 에코)을 빼면 차이가 더 선명하다 — 회절 없는 "
       "팔들은 규칙적으로 뛰고, 회절 든 팔들은 번진다."),

    md("## 블레이드 대역 에너지 — 넓은 범위 (100~1,000 Hz)",
       "",
       "![switch grid band energy wide](../outputs/figures/swgrid_be_wide.png)",
       "",
       "**그림 3.** 조합당 한 패널. 옅은 빨강이 우리 커널(기준), 파랑이 그 조합이다. "
       "점선 = 예측 박자의 정수배.",
       "",
       f"회절 없는 {len(ORDER) - N_D_ON} 팔은 고차 조화선까지 점선 위에 서고, 회절 든 "
       f"{N_D_ON} 팔은 선 없이 바닥이 출렁인다."),

    md("## 블레이드 대역 에너지 — 확대 (0~420 Hz)",
       "",
       "![switch grid band energy zoom](../outputs/figures/swgrid_be_zoom.png)",
       "",
       f"**그림 4.** 1~3 차 선 확대. 봉우리 위치가 다섯 팔 전부 예측 자리"
       f"({M['f_flash_hz']:.1f} Hz)에 앉는다는 것, 그리고 회절 든 조합의 선이 바닥에 "
       f"눌린다는 것이 함께 보인다."),

    md("## 숫자 확인 — 그림에서 본 것",
       "",
       table(),
       "",
       f"스위치 조합이 여덟(2³)이 아니라 일곱인 이유: {M['excluded_ko']}",
       "",
       f"리듬 몫 · 상한 위 바닥 · 빗살 솟음 · 빠진 자세는 outputs/switch_factorial.json "
       f"(cells, 앙각 {ang(EL)} · 깊이 1)에서, 1 차 선과 봉우리는 그림 네 장을 만든 "
       f"outputs/switch_grid.json 에서 읽었다. 리듬 몫의 눈금 — 백색 {WHITE:.1f} "
       f"(±{CTRL['white_share_pct_std']:.1f}, 뽑기 {CTRL['white_draws']} 회), 이상 로터 "
       f"{CTRL['ideal_comb_share_pct']:.0f}. 다섯 팔 전부 {OFF['n_poses']:,} 자세가 다 "
       f"찼다.",
       "",
       "⚠**바닥 dB 열은 세로로만 읽는다.** 우리 커널 행과 Sionna 행은 애초에 단위가 "
       "다르다 — 우리 커널이 내는 것은 산란장(면적 차원)이고 Sionna 가 내는 것은 "
       "무차원 채널계수다. 그래서 두 엔진의 절대 dB 를 서로 빼는 것은 뜻이 없고, "
       "**같은 엔진 안에서 스위치를 바꿨을 때의 차이**만 이 열의 쓰임이다. 빗살 솟음 "
       "열은 같은 시계열 안의 비(선 ÷ 바닥)라 단위가 상쇄되므로 엔진 사이에서도 읽힌다.",
       "",
       f"표를 가로로 읽으면 결과 1 이 그대로 보인다. 회절이 켜진 {N_D_ON} 행은 **바닥 "
       f"열이 {D_FLOOR_LIFT:.0f} dB 넘게 위로 올라와 있고**, 그래서 빗살 솟음이 "
       f"0 dB 근처(=선 없음)로 주저앉고, "
       "그 결과로 리듬 몫이 백색 자리에 앉는다. 리듬 몫 하나만 보면 «선이 사라졌다» 로 "
       "읽히지만, 바닥 열을 같이 보면 «바닥이 올라왔다» 다.",
       "",
       f"⭐두 원장이 서로를 재현한다 — {len(ORDER)} 행 전부 자세 {OFF['n_poses']:,} 개가 "
       f"다 찼고, 리듬 몫이 "
       f"{F['selfcheck']['reproduces_switch_grid_json']['max_abs_diff_pp']:.2f} %p 안에서 "
       f"맞는다. ⛔전 판이 «굴절+회절» 행에 달았던 «1 차 선 갱신 대기» 꼬리표는 뗐다 — "
       f"그림 원장을 이 팔의 자세가 다 찬 뒤 다시 구웠고, 이제 그 행이 정확히 맞는다."),

    md("## 덮개 시험 — 회절은 지우나, 덮나",
       "",
       "![switch factorial absolute dB](../outputs/figures/switch_factorial_abs_db.png)",
       "",
       "**그림 5.** 같은 격자를 절대 dB 로 다시 읽은 판. 왼쪽 열이 깊이 1, 오른쪽 열이 "
       "깊이 3 이다. 위 두 패널은 세 열(움직이는 성분의 세기 AC · 상한 위 바닥 · 상한 위 "
       "빗살)의 절대 세기, 아래 두 패널은 «빗살 빈이 바닥 빈보다 얼마나 솟았나» 다 — "
       "0 dB 면 선이 없다는 뜻이다. 회색 음영 줄이 회절을 끈 칸이다.",
       "",
       "회색 줄(회절 끔)에서는 바닥 막대가 짧고 아래 패널 막대가 오른쪽(초록)으로 나가 "
       "있다. 흰 줄(회절 켬)에서는 바닥 막대가 길게 자라 있고 아래 패널 막대는 0 에 "
       "붙는다. **선이 사라진 것이 아니라 바닥이 선 높이까지 올라온 그림**이다.",
       "",
       "### 세 가지로 갈라 물었다",
       "",
       f"판정은 설계서가 정한 판 — 앙각 {ang(EL)} · matrice4e · 15 m · 광선 4×10⁹ — 의 "
       f"{V['A_n_pairs_plate']} 쌍(회절만 켜고 끈 짝)에서만 내린다.",
       "",
       f"1. ⛔**«빗살 총합이 그대로냐»로 물으면 아니다.** 올라온 바닥이 빗살 자리 안에도 "
       f"똑같이 들어차서 빗살 빈 총합도 함께 올라간다. 이 정의로는 «선» 을 잴 수 없다.",
       f"2. ✅**«선이 바닥 위로 솟았느냐»로 물으면 맞다.** 바닥은 "
       f"{FL_LO:.1f}~{FL_HI:.1f} dB 오르고, 빗살 솟음은 0 dB(=백색)로 주저앉는다.",
       f"3. ✅**덮개 시험 — 켠 판이 끈 판을 품고 있느냐.** 켠 시계열을 «계수 a × 끈 "
       f"시계열 + 나머지» 로 갈라 보면 a 가 {A_LO:.2f}~{A_HI:.2f} 이고 위상 틀어짐은 "
       f"많아야 {PH_HI:.1f}° 다. {V['A_n_pairs_plate']} 쌍 중 "
       f"{N_UNIT} 쌍이 «a = 1» 을 3σ 안에서 담는다. 나머지의 전력은 두 판 전력의 차와 "
       f"{ORTH_GAP:.2f} dB 안에서 같다 — 원래 신호와 겹치지 않는 **새 항이 더해졌다**는 "
       f"뜻이다.",
       "",
       f"그리고 그 «나머지» 만 따로 재면 리듬 몫이 {RES_LO:.1f}~{RES_HI:.1f} % 로 백색 "
       f"밴드({WBAND[0]:.0f}~{WBAND[1]:.0f} %) 안이다. **얹힌 것에는 날개 박자가 없다.**",
       "",
       "### 얼마나 깊이 잠겼나",
       "",
       f"원래 빗살(회절 끈 판)과 그 자리를 채운 새 바닥(회절 켠 판)의 높이 차 — 판 위 "
       f"{len(F['diffraction_burial'])} 쌍에서 {BUR_LO:.1f}~{BUR_HI:.1f} dB, 기본 칸에서 "
       f"{BURIAL['burial_depth_db']:.1f} dB 다. 리듬은 사라진 것이 아니라 그만큼 아래에 "
       f"있다.",
       "",
       "⇒ 기전이 다르면 다음 실험이 달라진다. **지운다면** 회절 모형 자체가 틀린 것이고, "
       "**덮는다면** 회절 항의 절대 크기가 문제다. 남은 질문은 하나로 좁혀진다 — 상한 "
       "위로 새는 그 회절 항이 물리인가, 아니면 광선을 유한하게 쏴서 생기는 계산 "
       "흔들림인가.",
       "",
       f"⟨outputs/switch_factorial.json : verdict.A_* · diffraction_on_plate_el30 · "
       f"diffraction_burial⟩"),

    md("## 적용 범위 — 정면(0°)은 예외다",
       "",
       "![switch factorial across elevation](../outputs/figures/switch_factorial_elevation.png)",
       "",
       "**그림 6.** 같은 세 열을 앙각으로 훑은 것. 기전이 서로 다른 여섯 팔만 골랐다. "
       "(a) 움직이는 성분의 세기, (b) 상한 위 바닥, (c) 상한 위 빗살.",
       "",
       f"⚠**덮개 문장은 빗각에서만 쓴다.** 앙각 0° 에서는 회절을 켜도 바닥이 "
       f"{Z0['d_above_floor_db']:+.1f} dB 밖에 안 오른다. 정면에서는 회절이 오기 전에 이미 "
       f"동체 정반사를 유한한 광선으로 재느라 생긴 계산 흔들림이 상한 위를 백색으로 채워 "
       f"놨기 때문이다 — 회절을 끈 판의 리듬 몫이 벌써 "
       f"{Z0_OFF['rhythm_share_pct']:.1f} %(= 백색 {WHITE:.1f})다. 덮을 것이 이미 덮여 "
       f"있으니 회절이 더 얹어도 눈금이 안 움직인다.",
       "",
       f"판 밖 빗각 {len(OBL)} 자리({OBL_LIST})"
       f"에서는 회절이 바닥을 {OBL_LO:.1f}~{OBL_HI:.1f} dB 올리고 빗살 솟음을 0 dB 로 "
       f"눌러, 판 위에서 본 것과 같은 그림이 나온다. 다만 «계수 1» 이 3σ 안에 드는지는 "
       f"자리마다 다르다 — "
       + ("모든 빗각에서 든다." if not OBL_BAD else
          " · ".join(f"{ang(p['el_deg'])} 는 3σ 밖(계수 {p['contain_coeff']:.2f})"
                     for p in OBL_BAD) + " 이라 그 자리에서는 «품고 있다» 를 "
          "단정하지 않는다.") +
       f" 사전등록 판정은 판 위 한 자리에서만 내렸고, 문장을 쓰는 범위는 **빗각 "
       f"−15°~−75°** 로 적는다.",
       "",
       "⟨outputs/switch_factorial.json : verdict.A_scope_ko⟩ "
       "⟨outputs/switch_factorial.json : diffraction_scope_other_elevations⟩"),

    md("## 축의 성질 — 바꾸는 축 하나, 얹는 축 셋",
       "",
       f"덮개 시험의 담김계수 a 를 네 스위치 전부에 돌리면 축이 두 종류로 갈린다"
       f"(앙각 {ang(EL)} 판 위의 쌍만).",
       "",
       axis_table(),
       "",
       f"⭐**굴절 R 만 «바꾸는 축»**이다(a {AX['R']['a_min']:.2f}~{AX['R']['a_max']:.2f}) — "
       f"셸을 통과시켜 원래 반사 자체를 다른 것으로 만든다. **회절 D · 모서리 E · 확산 F "
       f"는 «얹는 축»**이다(a ≈ {LIFT_LO:.2f}~{LIFT_HI:.2f}) — 원래 반사를 남긴 채 위에 "
       f"새 항을 더한다.",
       "",
       f"모서리 E 가 얹는 항은 크기가 0 이다 — 회절 D 가 꺼져 있으면 «모서리만» 은 "
       f"«다 끔» 과 세 열이 소수점까지 같다. 확산 F 도 회절이 켜져 있으면 세기를 "
       f"0.1~0.4 dB 밖에 안 바꾸지만, 회절이 꺼져 있으면 **에코의 유무**를 가른다 — "
       f"빗각에서 살아 있는 유일한 경로원이다.",
       "",
       "⟨outputs/switch_factorial.json : verdict.E_axis_mechanism⟩ "
       "⟨outputs/switch_factorial.json : verdict.C_edge_is_noop_ko⟩ "
       "⟨outputs/switch_factorial.json : verdict.F_diffuse_keeps_it_alive_ko⟩"),

    md("## 깊이 — 판 밖 −60° 반례는 철회했다, 남은 것은 판 위 +2 dB 하나다",
       "",
       f"사전등록한 문턱은 «깊이 1↔3 쌍 전부에서 세기 차 < 2 dB 이고 리듬 차 < 3 %p 면 "
       f"깊이 축 종결» 이었다. 실측은 견줄 수 있는 쌍이 {V['B_n_pairs_1to3']} 쌍"
       f"(판 위 {V['B_n_pairs_1to3_on_plate']} 쌍) + 두 판 모두 경로가 0 이라 견줄 것이 "
       f"없는 죽은 쌍 {V['B_n_dead_pairs']} 쌍이다. 이 원장(R13)은 {len(BF)} 쌍을 문턱 "
       f"밖에 적었는데 그중 −60° 한 쌍은 뒤 원장이 **철회**했으므로(아래 2 번), 남는 "
       f"것은 **{len(BF_LIVE)} 쌍**이다. 아래 1·2 번 값은 15 m · 자세 "
       f"{D60_1['n_poses']:,} 개 생값 · 광선 4×10⁹ 발 · PRF {FM['prf_hz']:,.0f} Hz · "
       f"빗살 반폭 ±{FM['comb_half_width_hz']:.0f} Hz 한 설정에서 잰 것이다(«자세를 뺀» "
       f"값은 가장 튄 자세 1 개 또는 8 개를 뺀 판이다).",
       "",
       f"1. **판 위({ang(EL)})** — R1D1** 칸 "
       f"{len(BF_PLATE)} 개가 깊이 3 에서 세 열 전부 +{PL_LO:.1f}~+{PL_HI:.1f} dB 다. "
       f"2 dB 밴드 바로 밖이다. 가장 튄 자세 1 개·8 개를 빼도 그대로이고, 그 팔의 재실행 "
       f"문턱(같은 물리를 두 이름으로 독립 재실행한 폭) {RERUN:.2f} dB 의 "
       f"{PL_LO / RERUN:.0f}~{PL_HI / RERUN:.0f} 배라 **차이 자체는 실재한다.** "
       f"⚠다만 **그 +2 dB 의 기전은 모른다** — «회절 항이 깊이를 타고 한 번 더 얹힌 "
       f"것» 은 후보일 뿐이고, 깊이 3 에서 광선 사다리도 시드 복제도 아직 안 돌렸다. "
       f"물리인지 경로 표집의 부산물인지 이 원장으로는 못 가른다.",
       f"2. ⛔**판 밖(−60°) 은 반례가 아니었다 — 자세 하나다(2026-08-16 철회).** "
       f"«세기는 {D60['d_ac_db']:+.2f} dB 로 같은데 상한 위 바닥만 "
       f"{D60['d_above_floor_db']:+.1f} dB 오르고 리듬 몫이 "
       f"{D60_1['rhythm_share_pct']:.1f} → {D60_3['rhythm_share_pct']:.1f} %"
       f"(낙차 {abs(D60['d_rhythm_pp']):.2f} %p)로 무너진다» 는 그 칸 자세 "
       f"{OUT60['n_poses']:,} 개 중 **#{OUT60['culprit_pose_index']} 하나**가 만든 "
       f"값이다. 그 자세의 움직이는 성분 |AC| 는 중앙값의 "
       f"{OUT60['pose_over_median_dN']:.1f} 배인데 둘째 자세는 {P60_TOP2:.2f} 배뿐이고"
       f"(고립도 = 최대÷둘째 = {OUT60['isolation_dN']:.2f} — 이 원장 "
       f"{DA_OF['n_cells']} 칸의 고립도 중앙값은 {DA_OF['isolation_median']:.3f} 다), "
       f"깊이 1 판의 같은 칸은 고립도 {OUT60['isolation_d1']:.3f} 로 평범하다. 경로 수도 "
       f"정상이고({OUT60['npaths_at_pose']:,} ≈ 중앙값 "
       f"{OUT60['npaths_median_dN']:,.0f}), 로터 4 회 대칭 짝 셋도 {ROT60_TXT} 배로 안 "
       f"튄다. **그 자세 하나만 빼면** 두 판이 리듬 {TRIM60['rhythm_d1_pct']:.2f} ↔ "
       f"{TRIM60['rhythm_dN_pct']:.2f} %(차 {TRIM60['d_rhythm_pp']:+.2f} %p) · 세기 차 "
       f"{TRIM60['d_moving_power_db']:+.3f} dB 로 붙는다. 원장은 이 판정을 세 방법"
       f"(이웃 평균으로 갈아 끼우기 · 죄 없는 자세를 빼는 대조검사 · 그 자세가 다른 어느 "
       f"칸에서도 안 튄다는 전 칸 훑음)으로 각각 확인해 뒀다. ⚠**왜 그 자세가 튀는지는 "
       f"모른다** — 이웃도 대칭 짝도 경로 수도 정상이라 구조적 정반사 플래시로는 안 "
       f"읽힌다.",
       "",
       f"⛔**여기서 «깊이는 상한 위 바닥을 올리는 축» 이라고는 못 쓴다** — 전 판이 그렇게 "
       f"쓴 근거는 위 2 번 하나였다. 표준 프레임이 싣는 두 팔(PS 다 끔 · PS 굴절만)의 "
       f"깊이 짝 {len(SF)} 개는, 가장 튄 자세 1 개를 뺀 값으로 리듬 몫 차가 최대 "
       f"{SF_RHY:.2f} %p 이고, 빗살 대비 차는 값이 잡히는 빗각·거리 "
       f"{len(SF_CMB_OBL)} 칸에서 최대 {SF_CMB_HI:.2f} dB 다"
       f"(앙각 {len(SF_EL)} 개 {' · '.join(ang(e) for e in SF_EL)}, 거리 "
       f"{'·'.join(f'{r:.0f}' for r in SF_RG)} m). ⚠**빗살 대비의 이 범위에 정면 0° 는 "
       f"안 든다** — 그 칸은 {SF_C0:+.2f} dB 로 범위 밖이고, 판 밖 −90° 는 빗살 대비 값 "
       f"자체가 없다. 그리고 «작다» 라고 쓰는 근거는 격자 밴드가 아니라 관측값과 "
       f"≈0 인 재실행 문턱이다 — 밴드는 «판정 불가» 만 말한다"
       f"(원장 scorecard.wording_rule_ko).",
       "",
       f"밴드로도 채점해 뒀다. **정본(전역)** 밴드로는 깊이 쌍 "
       f"{DA_SC['n_pairs_total']} 개 중 판독을 바꾼 쌍이 "
       f"{DA_SC['n_moves_the_reading']} 개다. ⚠전역 밴드는 앙각별 밴드보다 넓어 «안 "
       f"바뀐다» 쪽에 유리하다고 원장이 스스로 적어 뒀다"
       f"(scorecard.band_rule_caveat_ko) — **앙각별 밴드로 채점하면 "
       f"{DA_SC['n_moves_the_reading_by_el_band']} 개**다. 둘 다 정면 0° 의 빗살 대비 "
       f"칸이고, 양쪽 판이 다 백색 널 자리라 «빗살 없음» 이라는 읽기 자체는 안 바뀐다.",
       "",
       f"⚠**리듬 몫 자체가 자유 파라미터 하나를 탄다.** 빗살 반폭을 ±2 → ±32 Hz 로 "
       f"흔들면 이 잣대의 기하학적 바닥(= 2·hw/f_flash, 백색 대조군이 앉는 자리)이 "
       f"{HW_LO:.1f} → {HW_HI:.1f} % 로 옮겨 간다. 위 값들은 "
       f"±{FM['comb_half_width_hz']:.0f} Hz 한 값에서 잰 **두 판의 차**로만 쓴다 — "
       f"리듬 몫의 절대값을 다른 문서로 들고 나가지 않는다.",
       "",
       f"⇒ 이 원장으로 확실한 것은 둘이다. ①**표준 프레임의 두 팔에서는 깊이 1 과 3 의 "
       f"판독이 같다** — 큐의 표준 팔에 `--max-depth 3` 을 다시 태울 이유가 없다. "
       f"②**회절을 켠 조합의 절대 레벨을 인용할 때만 «깊이 1 한정» 꼬리표를 단다.** "
       f"「깊이 축이 통째로 살아 있다」도 「죽었다」도 이 원장으로는 못 쓴다.",
       "",
       "⟨outputs/switch_factorial.json : verdict.B_* · depth_pairs⟩ "
       "⟨outputs/depth_axis_verdict_0816.json : outlier_forensics.el60_case · "
       "pairs[].in_standard_frame·trim.k1 · scorecard · closure.retractions_ko⟩ "
       "⟨outputs/rhythm_share_knob_audit_0825.json : 기하학적_바닥_2hw_over_fflash⟩"),

    md("## 곁가지 — 순정 공장 기본값은 빗각에서 에코가 정확히 0",
       "",
       f"위 격자의 일곱 조합은 전부 확산 반사를 켠 판이다. 스위치를 하나도 안 만진 "
       f"**순정 공장 기본값**(굴절 켬 · 확산 끔 · 깊이 3)은 같은 조건의 앙각 스윕에서 "
       f"앙각 0° 에만 에코가 있고, 빗각 여섯 자리(−15°~−90°, 이 격자의 자리 {ang(EL)} "
       f"포함)에서는 {OFF['n_poses']:,} 자세 **전부 에코가 정확히 0** 이다 — 경로 수 "
       f"자체가 0 이다. 이 칸들은 «안 돌린 칸» 이 아니라 «돌렸는데 경로가 0» 인 칸이다 — "
       f"자리마다 샤드 {ZE_SHARDS[0]} 개가 다 돌아 있고, 경로 합이 0 이고, 시계열이 전부 "
       f"0 이다.",
       "",
       "거울면 반사만으로는 빗각에서 수신기로 돌아오는 경로가 안 생기고, 확산이 꺼져 "
       "있으면 그것을 메울 길이 없다. 확산도 끄고 회절도 끄면 굴절을 켜든 말든 빗각에서 "
       "경로가 0 개다. 즉 이 격자의 «회절 없는 세 조합이 날개 구조를 유지한다» 는 결과는 "
       "확산을 켰기 때문에 성립하는 것이다.",
       "",
       "원장: outputs/switch_factorial.json : zero_echo_proof · "
       "verdict.D_no_diffuse_no_diffraction_zero_ko."),

    md("## 판정과 다음 작업",
       "",
       f"1. ⭐**회절이 얹는 것은 리듬 없는 에코다.** 회절이 든 조합은 굴절·모서리 동반 "
       f"여부와 무관하게 상한 위 바닥이 같은 자리로 올라오고"
       f"(≈{ON['above_floor_db']:.0f} dB), 그 바닥이 원래 있던 빗살을 덮는다. **원래 "
       f"빗살은 그대로 남아 있다** — 계수 ≈1 로 품고 있고, "
       f"{BURIAL['burial_depth_db']:.1f} dB 아래에 잠겨 있을 뿐이다. 상호작용은 없다.",
       "2. **모서리회절 스위치는 이 표적에서 완전한 무동작**이므로 이후 실험에서 축을 "
       "제외해도 된다.",
       f"3. **굴절은 별개의 순한 축**이다 — 선을 지우지 않고 깎기만 한다(리듬 몫 "
       f"{facc('R0D0E0F1')['rhythm_share_pct']:.1f} → "
       f"{facc('R1D0E0F1')['rhythm_share_pct']:.1f} %, 빗살 솟음 "
       f"{facc('R0D0E0F1')['comb_over_floor_db']:+.1f} → "
       f"{facc('R1D0E0F1')['comb_over_floor_db']:+.1f} dB). 다만 담김계수가 "
       f"{AX['R']['a_min']:.2f}~{AX['R']['a_max']:.2f} 라 «얹는» 것이 아니라 «바꾸는» "
       f"것이다. 물을 것은 «Sionna 의 유전체 셸 투과가 우리 커널의 투과 규약과 왜 "
       f"다른가» 다.",
       f"4. ⚠**깊이 축 — 표준 팔은 닫혔고, 문턱 밖에는 회절 켠 조합의 레벨만 남았다.** "
       f"문턱 밖은 판 위 R1D1** {len(BF_LIVE)} 쌍(세 열 전부 "
       f"+{PL_LO:.1f}~+{PL_HI:.1f} dB)뿐이고 "
       f"그 기전은 안 세워졌다. 표준 팔에서는 `--max-depth 3` 를 뺀다. ⛔전 판이 근거로 "
       f"든 «−60° 리듬 붕괴» 는 자세 하나의 튐이라 **철회했다**(2026-08-16) — 그 숫자를 "
       f"근거로 한 깊이 재발주(docs/NEXT_EXPERIMENTS.md ⑦ R26)는 취소하고, 다시 물으려면 "
       f"판 위 +2 dB 쪽을 **깊이 3 광선 사다리**로 묻는다.",
       "5. ⇒ 다음 작업 제안: (a) 상한 위로 새는 회절 항이 물리인지 계산 흔들림인지 "
       "가르기 — 같은 칸을 광선 수를 내리며 재서 바닥이 광선 수를 따라가는지 본다, "
       "(b) 회절 경로만 뽑아 그 도플러 분포를 직접 보기 — 왜 리듬이 없는가의 기전, "
       "(c) 우리 커널 PTD 수리 후 «우리 모서리회절» 과 Sionna 회절의 대조, "
       "(d) 회절을 끈 채 물리(굴절·다중반사)만 켠 조합을 실전 기본값으로 쓰는 권고를 "
       "리포트 5 에 편입."),
]

out = f"{ROOT}/reports/05_2_switch-grid.ipynb"
nbf.write(nb, out)
print(f"✅ {out}  ({len(nb.cells)} 셀)")
