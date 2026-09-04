# -*- coding: utf-8 -*-
"""
make_report11_2_two_channel.py — 리포트 8-2 「기준채널이 현실이면 얼마를 잃는가」를 짓는다.

8 권(`reports/08_detector.ipynb`)이 ECA·CFAR 사슬을 세웠다. 다만 그 권과 헤드라인 검출
수치는 기준신호를 **송신 파형 그 자체**(잡음 0 · 다중경로 0)로 준다 — 즉 «기준안테나가
완벽하다» 는 상한이다. 이 편은 그 가정 하나를 푼다.
6 권 5 편(`reports/06_5_bistatic.ipynb`)이 «이 편은 기하만 본다, 2채널 처리는 쓰지 않는다» 고
그은 경계의 반대편이 여기다.

⭐ 그림은 base64 로 **박아 넣는다**(상대 경로로 걸면 보는 환경에 따라 안 뜬다).
⭐ 본문 수치는 손으로 안 적는다 — 전부 `outputs/passive_two_channel.json` 에서 주입한다.

    PYTHONPATH=src python src/make_report11_2_two_channel.py
"""
#: ⛔⛔ **2026-09-04 — 이 빌더는 기본으로 쓰지 않는다.**
#  산출물 `reports/08_2_two_channel.ipynb` 는 **실내 통제 기하(챔버 바이스태틱)** 판이고,
#  사용자 지시(2026-09-03) 「챔버 관련 내용은 아카이브로 넘기고 없애버려」에 따라
#  `archive/chamber_0903/reports/` 로 내려갔다. 그런데 이 빌더를 돌리면 그 파일이
#  `reports/` 로 **되살아난다** — 2026-09-04 에 실제로 그랬고 손으로 지웠다.
#  ⇒ 되살리려면 `SIONNA_ALLOW_CHAMBER=1` 을 명시해야 한다.
from __future__ import annotations

import base64
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

if not os.environ.get("SIONNA_ALLOW_CHAMBER"):
    raise SystemExit(
        "⛔ 챔버 편은 2026-09-03 에 archive/chamber_0903/ 로 내렸다(사용자 지시).\n"
        "   이 빌더를 돌리면 reports/08_2_two_channel.ipynb 가 되살아난다.\n"
        "   정말 되살리려면: SIONNA_ALLOW_CHAMBER=1 PYTHONPATH=src python "
        "src/make_report11_2_two_channel.py")

FIG = os.path.join(_ROOT, "outputs", "figures")
OUT = os.path.join(_ROOT, "reports", "08_2_two_channel.ipynb")

J = json.load(open(f"{_ROOT}/outputs/passive_two_channel.json"))

META, GEO, MDL, CFG = J["_meta"], J["geometry"], J["md_ledger"], J["config"]
IDC, SUM, MECH, LAW = J["identity_check"], J["summary"], J["mechanism"], J["empirical_law"]
SURV, SPREAD, E2 = J["md_survival"], J["md_spreading_loss"], J["E2"]
ASSUM, OPEN = J["assumptions"], J["open_problems"]

E1 = {b["mode"]: b for b in J["E1"]}
E1R = {m: {r["arm"]: r for r in b["rows"]} for m, b in E1.items()}
E1B = {b["mode"]: b for b in J["E1b"]}
E1BR = {m: {r["arm"]: r for r in b["rows"]} for m, b in E1B.items()}
E1C = {b["mode"]: b for b in J["E1c"]}
E1CR = {m: {r["arm"]: r for r in b["rows"]} for m, b in E1C.items()}
DTRS = {(b["mode"], b["dtr_db"]): {r["arm"]: r for r in b["rows"]}
        for b in J["E1_dtr_sensitivity"]}
DTR_AXIS = sorted({k[1] for k in DTRS})

MODES = ["W1", "L1", "G1"]
STD_KO = {"wifi": "WiFi", "lte": "LTE", "nr": "5G NR"}
LBL = {m: f"`{m}` · {STD_KO[E1[m]['std']]} {E1[m]['ref_name']}" for m in MODES}
SH = {m: f"`{m}`" for m in MODES}          # 문장 안에서 쓰는 짧은 이름

RHO = sorted(SUM["W1"]["loss_db_by_refsnr"], key=float, reverse=True)      # +40…+0
MDR = sorted(SUM["W1"]["loss_db_by_mdr"], key=float)                       # -30…-10
WM, NM = E2["wifi_b1"]["meta"], E2["nr_b1"]["meta"]
ALIAS = SURV["nr_alias"]
LD = SURV["ledger_direct"]
NOTCH = SURV["eca_notch_cost_db"]

_EMBEDDED: list[str] = []

# ── 상속한 마이크로도플러 원장의 광선 격자 세대 — 원장 스스로가 스위치다.
#    커널은 자세 사이에 격자를 고정하는 `grid_ref` 를 받는다. 그 인자로 계산된 원장은
#    메타에 `grid_ref` 를 남기므로, 없으면 «자세마다 격자를 다시 잡은 산출» 이다.
#    다시 낸 원장으로 갈아끼우면 이 경고는 저절로 사라진다. ────────────────────────── #
GRID_PENDING = "" if MDL.get("grid_ref") else (
    "⚠ **이 원장은 광선 격자를 자세마다 다시 잡는 설정에서 계산된 것이다** — 메타에 "
    "`grid_ref` 기록이 없다. 격자 중심·반경이 프레임마다 움직이면 그 움직임이 표적 운동과 "
    "같은 자리에 들어간다. 얼린 격자로 다시 낸 원장 위에서 **절 5 의 플래시 지표와 확산 "
    "손실은 다시 잰다(재계산 대기)**. 절 2~4 의 손실 축은 표적 변조가 아니라 기준채널 "
    "품질의 함수이고, 그 팔들의 표적은 단일 톤이다.")


def embed(stem: str, ext: str = "png") -> str:
    _EMBEDDED.append(stem)
    with open(os.path.join(FIG, f"{stem}.{ext}"), "rb") as f:
        b = base64.b64encode(f.read()).decode()
    return f"![{stem}](data:image/{ext};base64,{b})"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {},
            "source": [l + "\n" for l in "\n".join(lines).split("\n")]}


# ── 원장에서 «읽어낸» 파생값 (손으로 적지 않는다) ────────────────────────────
def cliff_bracket(mode: str):
    """Pd 가 0.5 를 가로지르는 ρ 두 칸 — «절벽» 이 어디인지 원장이 스스로 말하게 한다."""
    pd = SUM[mode]["pd_by_refsnr"]
    for hi, lo in zip(RHO, RHO[1:]):
        if pd[hi] >= 0.5 > pd[lo]:
            return hi, lo
    return RHO[0], RHO[-1]


CLIFF = {m: cliff_bracket(m) for m in MODES}
CL_HI, CL_LO = CLIFF["W1"]
CL_SAME = all(CLIFF[m] == CLIFF["W1"] for m in MODES)
CL_HI_N, CL_LO_N = CL_HI.lstrip("+"), CL_LO.lstrip("+")
MDR_ABS = [abs(SUM[m]["loss_db_by_mdr"][k]) for m in MODES for k in MDR]
MDR_WORST = max(MDR_ABS)
RHO_HALF_DTR = GEO["dtr_db"] / 2.0
IDC_WORST = max(IDC[m]["rel_err"] for m in MODES)
CAF_ROWS = [E1CR[m][f"CAFonly-noisy{r}dB"]["loss_db"] for m in MODES for r in ("+20", "+10")]
CAF_LO, CAF_HI = min(CAF_ROWS), max(CAF_ROWS)
F_FOLD = ALIAS["f_tip_hz"] - ALIAS["prf_hz"]
SPREAD_LO = min(SPREAD[m]["spreading_loss_db"] for m in MODES)
SPREAD_HI = max(SPREAD[m]["spreading_loss_db"] for m in MODES)
G1_CEIL = E1["G1"]["sinr_ceiling_db"]
G1_TGT = E1["G1"]["sinr_target_db"]
PFA_WL = [SUM[m]["pfa_emp_by_arm"][a] for m in ("W1", "L1") for a in SUM[m]["pfa_emp_by_arm"]]
PFA_G1 = list(SUM["G1"]["pfa_emp_by_arm"].values())
# DTR 민감도 스윕이 쓴 ρ_ref 한 칸 · 그리고 설계 규칙(ρ_ref ≥ DTR/2)의 등호가 앉는 칸
# ⛔ 이 스윕은 **DTR 세 칸 · ρ_ref 한 칸**이다. 아래 파생값은 그 격자를 문장이 스스로
#    말하게 하려고 둔다 — 기울기는 칸마다 다르고, 격자의 아래끝이 경험식의 «무릎»
#    (DTR = 2ρ_ref)이라 거기서 곡선이 눕는다. 평균 기울기 하나로 요약하면 그 꺾임이 사라지고,
#    ρ_ref = DTR/2 자리의 3 dB 는 식의 등호라 «측정으로 확인» 되는 값이 아니다.
DTR_SENS_ARM = next(a for a in DTRS[("W1", DTR_AXIS[0])] if a.startswith("refSNR"))
DTR_SENS_RHO = DTRS[("W1", DTR_AXIS[0])][DTR_SENS_ARM]["axis_value"]
DTR_CHECK = min(DTR_AXIS, key=lambda d: abs(d / 2 - DTR_SENS_RHO))
DTR_DROP_HI, DTR_DROP_LO = max(DTR_AXIS), min(DTR_AXIS)


def dtr_loss(m: str, d: float) -> float:
    return DTRS[(m, d)][DTR_SENS_ARM]["loss_db"]


def dtr_law(d: float) -> float:
    """경험식이 이 칸에 주는 값 — ρ_ref = DTR/2 면 지수가 정확히 0 이라 10log10(2) 다."""
    return 10 * math.log10(1 + 10 ** ((d - 2 * DTR_SENS_RHO) / 10))


DTR_DOWN = sorted(DTR_AXIS, reverse=True)
DTR_STEPS = list(zip(DTR_DOWN, DTR_DOWN[1:]))
DTR_SLOPE = {m: [(dtr_loss(m, hi) - dtr_loss(m, lo)) / (hi - lo) for hi, lo in DTR_STEPS]
             for m in MODES}
DTR_RESID = {m: [dtr_loss(m, d) - dtr_law(d) for d in DTR_DOWN] for m in MODES}
DTR_K = {m: sorted({r["K"] for d in DTR_AXIS for r in DTRS[(m, d)].values()}) for m in MODES}
DTR_KNEE = 2 * DTR_SENS_RHO          # 경험식의 무릎이 앉는 DTR — 이 격자의 아래끝이다
DTR_LAW_3DB = dtr_law(DTR_CHECK)     # = 10log10(2) — 설계 규칙이 «정의상» 내놓는 값
DTR_RESID_WL = max(abs(r) for m in ("W1", "L1") for r in DTR_RESID[m])
SECONDS = (sum(b["seconds"] for k in ("E1", "E1b", "E1c", "E1_dtr_sensitivity")
               for b in J[k]) + WM["seconds_run"] + NM["seconds_run"])

# ── 원장의 미해결 목록을 **번호로** 못 박지 않는다 — 키워드로 찾는다 ───────────
def op_no(*keys: str) -> int:
    """`open_problems` 에서 키워드를 다 가진 항목의 번호. 목록 순서가 바뀌어도 안 깨진다."""
    for i, s in enumerate(OPEN):
        if all(k in s for k in keys):
            return i + 1
    raise KeyError(keys)


OP_TPL = op_no("정합필터 템플릿")          # 정합필터 템플릿이 프레임 0 에 얼어 있다
OP_CEIL = op_no("운용점이 «천장»")          # G1 의 운용점이 천장이다
OP_PFA = op_no("Pfa 교정표")                # 팔마다 경험 Pfa 가 다르다
OP_BIST = op_no("마이크로도플러 원장이 모노스태틱")
OP_ECAS = op_no("ECA-S")
OP_SURVMP = op_no("감시채널에는 넣지 않았다")
OP_DTR = op_no("DTR 에 강하게 의존")
OP_DECIM = op_no("여파·데시메이션")
AS_MD = next(i + 1 for i, s in enumerate(ASSUM) if "마이크로도플러 원장" in s)

# ── 두 축을 같이 흔든 칸 · G1 의 오검출 0 팔 — 원장이 스스로 고르게 한다 ───────
JOINT = next((a for a in E1R["W1"] if "+MDR" in a), None)
JOINT_RHO = "+" + JOINT.split("dB")[0].replace("refSNR+", "") if JOINT else None
JOINT_MDR = JOINT.split("+MDR")[1].replace("dB", "") if JOINT else None
G1_FA_MIN_ROW = min(E1["G1"]["rows"], key=lambda r: r["n_fa"])
PFA_WL_RATIO = [p / CFG["pfa_target_emp"] for p in PFA_WL]
# ⭐ 이 편이 돌린 **모든** 실험 묶음 — 절 2 사다리(E1)만 보고 «팔 전체» 를 말하면
#    절 4(E1c)·절 5(E1b)·DTR 스윕의 팔이 통째로 빠진다(트라이얼 수도 Pfa 도 다르다).
BLK_ALL = J["E1"] + J["E1b"] + J["E1c"] + J["E1_dtr_sensitivity"]
PFA_WL_ALL = [r["pfa_emp"] for b in BLK_ALL if b["mode"] in ("W1", "L1") for r in b["rows"]]
PFA_WL_ALL_RATIO = [p / CFG["pfa_target_emp"] for p in PFA_WL_ALL]
K_ALL = [r["K"] for b in BLK_ALL for r in b["rows"]]
KPFA_ALL = [r["Kpfa"] for b in BLK_ALL for r in b["rows"]]
K_E1 = [r["K"] for b in J["E1"] for r in b["rows"]]
KPFA_E1 = [r["Kpfa"] for b in J["E1"] for r in b["rows"]]
K_REST = [r["K"] for b in J["E1b"] + J["E1c"] + J["E1_dtr_sensitivity"] for r in b["rows"]]
KPFA_REST = [r["Kpfa"] for b in J["E1b"] + J["E1c"] + J["E1_dtr_sensitivity"]
             for r in b["rows"]]
MDR_PD_G1 = [E1R["G1"][f"MDR{k}dB"]["pd"] for k in MDR]

# ── 절 5 «생존» 을 재는 사슬은 절 2 의 검출 사슬과 다른 물건이다 ──────────────
DET, SURVCFG = E1B["W1"], WM
NV_GAP_DB = 10 * math.log10(E1["W1"]["noise_var"] / DET["noise_var"])
FL_LADDER = ["ideal", "refSNR+20dB", "refSNR+10dB"]
FL = {k: SURV[k]["flash_line_db"] for k in FL_LADDER}
FL_DROP_1 = FL["ideal"] - FL["refSNR+20dB"]
FL_DROP_TOT = FL["ideal"] - FL["refSNR+10dB"]
PD_B = {k: E1BR["W1"][k]["pd"] for k in FL_LADDER}
SURV_NOISY_ARMS = [k for k in SURV if k.startswith("refSNR")]
NR_SURV_ARMS = list(E2["nr_b1"]["metrics"])
REQ_WL_LO = min(SUM[m]["ref_snr_needed_for_3db_loss"] for m in ("W1", "L1"))
REQ_WL_HI = max(SUM[m]["ref_snr_needed_for_3db_loss"] for m in ("W1", "L1"))
GAIN_WL_LO = min(SUM[m]["ref_antenna_gain_needed_db"] for m in ("W1", "L1"))
GAIN_WL_HI = max(SUM[m]["ref_antenna_gain_needed_db"] for m in ("W1", "L1"))


# ── «필요한 ρ_ref» 는 손실 오름차순 보간이다 — 사다리가 비단조면 격자 한 칸을 건너뛴다 ─
def loss_monotone(mode: str) -> bool:
    """ρ_ref 를 내릴수록 손실이 커지는가 — 원장의 사다리가 스스로 답한다."""
    ys = [SUM[mode]["loss_db_by_refsnr"][k] for k in RHO]          # RHO 는 +40…+0
    return all(a <= b for a, b in zip(ys, ys[1:]))


def req_bracket(mode: str):
    """3 dB 교차점이 앉는 두 격자 칸(손실 오름차순)과 그 사이에서 건너뛴 칸들."""
    pts = sorted((SUM[mode]["loss_db_by_refsnr"][k], float(k)) for k in RHO)
    for (y0, x0), (y1, x1) in zip(pts, pts[1:]):
        if y0 <= 3.0 <= y1:
            skip = [(float(k), SUM[mode]["loss_db_by_refsnr"][k]) for k in RHO
                    if min(x0, x1) < float(k) < max(x0, x1)]
            return (x0, y0), (x1, y1), skip
    return None, None, []


NONMONO = [m for m in MODES if not loss_monotone(m)]
NM_MARK = {m: (" ⚠ 비단조 보간" if m in NONMONO else "") for m in MODES}


def req_note(m: str) -> str:
    lo, hi, skip = req_bracket(m)
    if lo is None:
        return (f"{SH[m]} 의 손실 사다리는 3 dB 를 격자 안에서 가로지르지 않아 "
                f"{SUM[m]['ref_snr_needed_for_3db_loss']:.2f} dB 는 격자 밖 값이다.")
    sk = " · ".join(f"ρ_ref {x:.0f} dB 칸(손실 {y:+.2f} dB)" for x, y in skip)
    return (f"{SH[m]} 의 3 dB 교차점은 손실을 오름차순으로 세운 뒤 보간해 얻으므로 "
            f"ρ_ref {lo[0]:.0f} dB(손실 {lo[1]:+.2f} dB)와 {hi[0]:.0f} dB({hi[1]:+.2f} dB) "
            f"사이에서 **{SUM[m]['ref_snr_needed_for_3db_loss']:.2f} dB** 가 나오고, 그 사이의 "
            f"{sk}은 건너뛴다.")


REQ_NOTE = (("⚠ **" + "·".join(SH[m] for m in NONMONO) + " 행은 비단조 곡선의 보간값이다.** "
             + " ".join(req_note(m) for m in NONMONO)
             + " 절 2 사다리의 그 칸과 이 값은 같은 곡선을 두 방향으로 읽은 결과이고, "
             "한 점에서 만나지 않는다.") if NONMONO else "")

# ── CFAR 명목 Pfa 를 준 교정표의 «형상» — 그 원장이 직접 말하게 한다 ──────────────
try:
    CAL = json.load(open(os.path.join(_ROOT, CFG["pfa_calibration_source"])))
except OSError:
    CAL = {}
CALM = CAL.get("meta", {})
CAL_M, CAL_MASK = CALM.get("M_cpi"), CALM.get("zd_mask_operational")
CAL_NR = {m: next((v.get("n_range_op") for k, v in CAL.get("chain", {}).items()
                   if k.lower().startswith(E1[m]["std"].lower())), None) for m in MODES}
CAL_OK = CAL_M is not None and CAL_MASK is not None and all(CAL_NR[m] is not None
                                                            for m in MODES)
SHAPE_ORDER = "·".join(SH[m] for m in MODES)
SHAPE_GAP = ((f"교정표는 0-도플러 마스크 **{CAL_MASK} 빈** · CPI 프레임 M **{CAL_M}** · "
              f"거리빈 **{'/'.join(str(CAL_NR[m]) for m in MODES)}**({SHAPE_ORDER} 순)에서 "
              f"쟀고, 이 편은 가드 폭 **{CFG['guard_width']}** · M "
              f"**{'/'.join(str(E1[m]['M']) for m in MODES)}** · 거리빈 "
              f"**{CFG['n_range']}** 다")
             if CAL_OK else "교정표의 형상은 **원장 없음** 이다")
# 두 형상이 실제로 다른가 — 원장 대 이 편의 설정이 스스로 답한다. 같아지면(또는 대조할
# 원장이 없으면) 아래 세 경고문은 «다르다» 를 주장하지 않는 문장으로 저절로 바뀐다.
SHAPE_DIFFERS = CAL_OK and (CAL_MASK != CFG["guard_width"]
                            or any(CAL_M != E1[m]["M"] or CAL_NR[m] != CFG["n_range"]
                                   for m in MODES))
SHAPE_W_CHAIN = ((f"⚠ **그 교정표는 이 편과 다른 형상에서 쟀다** — {SHAPE_GAP}. 명목 Pfa 는 "
                  "형상의 함수이므로, 빌려 온 문턱이 이 편의 맵 위에서 목표 경험 Pfa 를 "
                  "그대로 내지는 않는다. 그 어긋남의 크기는 절 2 끝에서 팔마다 잰다.")
                 if SHAPE_DIFFERS else
                 (f"{SHAPE_GAP} — 빌려 온 문턱이 이 편의 맵 위에서 목표 경험 Pfa 를 내는지는 "
                  "절 2 끝에서 팔마다 잰다."))
SHAPE_W_FORM = (f"⚠ 8 권의 CFAR 교정 형상은 이것과 다르다({SHAPE_GAP}) — 그 권에서 빌려 오는 "
                "것은 명목 Pfa 값 하나뿐이다."
                if SHAPE_DIFFERS else
                f"8 권에서 빌려 오는 것은 명목 Pfa 값 하나뿐이다({SHAPE_GAP}).")
SHAPE_W_PFA = (f"**오염 이전에 형상부터 다르다** — {SHAPE_GAP}(절 1). " if SHAPE_DIFFERS
               else f"형상 대조는 절 1 에 있다({SHAPE_GAP}). ")
PFA_IDEAL_R = {m: SUM[m]["pfa_emp_by_arm"]["ideal"] / CFG["pfa_target_emp"] for m in MODES}

cells = [
    md("# 리포트 8-2 — 기준채널이 현실이면 **얼마를 잃는가**", "",
       "이 편은 [리포트 8 «처리 사슬»](08_detector.ipynb) 의 **별편**이다 — 8 권의 사슬을 "
       "한 줄도 안 고치고 기준신호 가정 하나만 푼다. 분권이 아니다.", "",
       "> **절벽은 기준채널 잡음 축에 있고, 다중경로 축은 평지다. 그리고 그 대가는 전부 "
       "ECA 단이 문다.**", "",
       "패시브 레이더는 채널을 두 개 쓴다 — 조명원을 곧바로 받는 **기준채널**과 표적 에코를 "
       "받는 **감시채널**이다. 기준채널은 «수신해서 재는 신호» 이므로 잡음도 다중경로도 "
       "섞인다. 그런데 8 권의 사슬과 우리 헤드라인 검출 수치는 기준신호로 **송신 파형 "
       "그 자체**를 넣는다 — 잡음 0 · 다중경로 0, 즉 «기준안테나가 완벽하다» 는 상한이다. "
       "이 편은 그 가정 하나만 푼다.", "",
       f"질문은 원장이 스스로 적어 둔 그대로다 — **«{META['question']}»**", "",
       "| 무엇 | 값 |",
       "|---|---|",
       "| 조명원 | " + " · ".join(f"**{m}** {STD_KO[E1[m]['std']]} {E1[m]['ref_name']} "
                                 f"{E1[m]['ref_bw_mhz']:.1f} MHz" for m in MODES) + " |",
       f"| 기하 | 챔버 바이스태틱 · β {GEO['beta_deg']:.1f}° · R_b {GEO['Rb_m']:.2f} m · "
       f"τ {GEO['tau_s']*1e9:.1f} ns |",
       f"| 직접파/표적비 DTR | **{GEO['dtr_db']:.1f} dB** (σ {GEO['sigma_dbsm']:.2f} dBsm · "
       "감시안테나 **등방** 가정 = 최악값) |",
       f"| 사슬 | `{META['chain']}` |",
       f"| 단일축 | 기준채널 SNR ρ_ref {RHO[-1].lstrip('+')}~{RHO[0].lstrip('+')} dB · "
       f"다중경로비 MDR {MDR[0]}~{MDR[-1]} dB |",
       f"| 계산 | {SECONDS/60:.0f} 분 · {META['host']} · {META['generated'][:16]} |",
       "",
       "⭐ **한 줄 요약 넷**", "",
       f"1. **절벽은 잡음 축에 있다.** ρ_ref 를 {CL_HI_N} → {CL_LO_N} dB 로 한 칸 내리면 "
       f"{SH['W1']}(WiFi VHT-LTF) 의 손실이 **{SUM['W1']['loss_db_by_refsnr'][CL_HI]:.1f} → "
       f"{SUM['W1']['loss_db_by_refsnr'][CL_LO]:.1f} dB**, 검출률 Pd 가 "
       f"**{SUM['W1']['pd_by_refsnr'][CL_HI]:.2f} → {SUM['W1']['pd_by_refsnr'][CL_LO]:.2f}** "
       "로 무너진다.",
       f"2. **다중경로 축은 평지다.** MDR {MDR[0]}~{MDR[-1]} dB 어디서도 손실이 "
       f"**{MDR_WORST:.2f} dB** 를 넘지 않는다(세 파형 전부). 기준채널에서 무서운 것은 "
       "«반사가 섞이는 것» 이 아니라 «잡음이 섞이는 것» 이다.",
       f"3. **ρ_ref 는 우리가 고르는 값이 아니다.** ρ_ref[dB] = DTR − G_proc + SINR_target "
       f"이라는 닫힌 꼴이 성립하고, 그것을 뒤집으면 손실 3 dB 를 지키는 데 필요한 "
       f"**기준안테나 이득 {SUM['W1']['ref_antenna_gain_needed_db']:.1f} dB**"
       f"({SH['W1']} 기준)가 나온다. 이 편이 실측 설계로 넘어가는 다리가 그것이다. "
       f"⚠ 이 이득은 «기준안테나와 감시안테나가 똑같다» 는 **퇴화된 기준점**에서 잰 "
       f"차이지 절대 사양이 아니다(절 3).",
       f"4. **대가는 전부 ECA 단이 문다.** 정합필터만 오염시키면 손실이 "
       f"{CAF_LO:+.1f}~{CAF_HI:+.1f} dB(사실상 0)이고, ECA 만 오염시키면 전체 손실이 거의 "
       f"그대로 나온다. 반면 ECA **노치 자체**의 순수 대가는 "
       f"**{NOTCH['value']:.2f} dB** 로 싸다.", "",
       "⚠ 이 편의 검출 수치는 **한 기하 · 한 σ · 한 CPI** 에서 잰 것이다. 절대 거리나 순위는 "
       "10 권이 말하고, 여기서 말하는 것은 **이상적 기준 대비 손실**뿐이다.", "",
       f"⚠ **{SH['G1']}(5G SSB) 은 이 편에서 성한 물건이 아니다 — 표를 읽기 전에 알아야 한다.** "
       f"① 잡음을 0 으로 보내도 출력 SINR 이 **{G1_CEIL:.1f} dB** 를 못 넘는 천장에 눌려 있어 "
       f"이상 팔조차 Pd 가 {E1R['G1']['ideal']['pd']:.2f} 다({SH['W1']}·{SH['L1']} 은 "
       f"{E1R['W1']['ideal']['pd']:.2f}). ② 경험 Pfa 가 {min(PFA_G1):.1e}~{max(PFA_G1):.1e} 로 "
       f"목표 {CFG['pfa_target_emp']:.0e} 보다 크게 아래여서 문턱이 다른 두 파형보다 보수적으로 "
       f"서 있다. **아래 모든 표에서 {SH['G1']} 열은 {SH['W1']}·{SH['L1']} 과 나란히 읽으면 "
       f"안 된다** — 근거는 절 2 끝, 이유는 절 6 의 {OP_CEIL}·{OP_DECIM}번 항목."),

    md("## 절 0. 무엇을 묻나 · 무엇을 안 묻나", "",
       "**묻는 것 하나.** 기준채널이 이상적이지 않을 때, 같은 사슬이 같은 표적을 놓고 "
       "**이상적 기준 대비 몇 dB 를 잃는가**. 축은 둘이고 각각 **단일축**으로만 흔든다 — "
       "기준채널 잡음(ρ_ref)과 기준채널 다중경로(MDR).", "",
       "⭐ 오염되는 것은 **우리가 재는 기준신호**이지 송신기가 보내는 신호가 아니다. "
       "그래서 감시채널의 직접파는 팔마다 **깨끗한 송신 파형 그대로** 둔다. 이 구분을 "
       "흐리면 «기준채널 품질» 축이 «조명원 품질» 축과 섞인다.", "",
       "**이 편의 앞뒤**", "",
       "| 어디 | 무엇을 했나 | 이 편과의 관계 |",
       "|---|---|---|",
       "| [6 권 5 편 «마이크로도플러 — 바이스태틱»](06_5_bistatic.ipynb) | 표적이 바이스태틱 "
       "기하에서 무엇을 되돌려주는가 | 그 편은 «2채널 처리(ECA·CAF)는 쓰지 않는다» 고 경계를 "
       "긋고, 그 다음 질문을 이 편에 넘겼다 |",
       "| [8 권 «처리 사슬»](08_detector.ipynb) | ECA·거리도플러·CFAR 를 세우고 경험 Pfa 를 "
       "교정했다 | 그 사슬을 **한 줄도 안 고치고** 그대로 쓴다. 다른 것은 기준신호 하나뿐 |",
       "| **이 편 (8-2)** | 기준채널이 현실이면 그 사슬이 얼마를 잃는가 | — |",
       "| [10 권 «결과»](10_results.ipynb) | R90 과 파형 순위 | 그 수치는 «이상적 기준» 위에 "
       "서 있다. 이 편의 손실이 그 위에 얹힌다 |",
       "| [11 권 «실측 계획»](11_measurement.ipynb) | 야외 캠페인 규약 | 절 3 의 "
       "**기준안테나 이득 요구치**가 그리로 간다 |",
       "",
       "**안 묻는 것 — 경계선**", "",
       "| 안 한 것 | 왜 |",
       "|---|---|",
       "| 감시채널의 다중경로 | 같은 방이면 감시채널에도 다중경로가 있어야 물리적으로 "
       "일관되지만, 그러면 축이 둘이 된다(단일축 규칙). 표적경유 유령은 원장의 "
       "`geometry.floor_ghost` 가 따로 다룬다 |",
       "| 안테나 패턴·차폐 설계 | 여기 DTR 은 **감시안테나 등방**이라는 최악 가정이다. 실제 "
       "패시브는 패턴으로 DTR 을 깎는다 — 그 기울기만 절 2 끝의 민감도 표로 잰다 |",
       "| sliding ECA-S | 이 편의 ECA 는 `passive_process` 의 standard(1회 최소제곱 사영)다. "
       "저도플러 표적 보존은 ECA-S 의 장점이지 여기 것이 아니다 |",
       "| 추적·분류기 | 이 프로젝트의 메인 태스크는 탐지다. 절 5 의 «마이크로도플러가 "
       "남는가» 는 **알아보기**에 대한 진술이지 **찾기**에 대한 진술이 아니고, 분류기를 "
       "돌려 본 적도 없다 |",
       f"| 실제 2채널 CAF 승격 | `passive_process` 에 CAF 는 있으나 이 편의 정합필터는 "
       f"«기준신호 한 프레임» 템플릿을 쓴다(절 6 의 {OP_TPL}번 항목) |"),

    md("## 절 1. 시나리오와 사슬 — 무엇을 재사용했고 무엇을 새로 했나", "",
       "**재사용(읽기 전용).** 사슬은 `src/passive_process.py` 의 것을 그대로 쓴다 — "
       "`make_cpi` · `ECACanceller` · `range_doppler` · `ca_cfar_2d`. 이 편은 그 파일을 "
       "**읽기만 한다.** CFAR 명목 Pfa 는 같은 파일의 교정표"
       f"(`{CFG['pfa_calibration_source']}`, 8 권 절 3)를 그대로 부르고, 0-도플러 가드는 "
       f"폭 {CFG['guard_width']} 다.", "",
       SHAPE_W_CHAIN, "",
       "**새로 한 것 하나.** 기준채널을 «측정된 신호» 로 만드는 팔이다.", "",
       "| 팔 | 무엇을 넣나 |",
       "|---|---|",
       "| `ideal` | 송신 파형 그대로 — 지금의 헤드라인 가정 |",
       f"| `refSNR ρ` | + 백색잡음, 기준채널 SNR = ρ ({', '.join(RHO)} dB) |",
       f"| `MDR d` | + 지연·감쇠 복사본, 다중경로/직접파 = d ({', '.join(MDR)} dB) · "
       f"지연 {', '.join(f'{x:.1f}' for x in CFG['mp_delays_ns'])} ns · 위상은 트라이얼마다 무작위 |",
       "| `ECAonly` / `CAFonly` | 오염된 기준신호를 **한 단에만** 준다 — 절 4 의 분해 |",
       "",
       "**기하와 링크버짓** — 8 권·10 권과 같은 챔버 기하다.", "",
       "| 무엇 | 값 |",
       "|---|---|",
       f"| R1 (TX→표적) · R2 (표적→RX) · L (기선) | {GEO['R1']:.2f} m · {GEO['R2']:.2f} m · "
       f"{GEO['L']:.2f} m |",
       f"| 바이스태틱 거리합 R_b · 여분지연 τ | {GEO['Rb_m']:.2f} m · {GEO['tau_s']*1e9:.1f} ns |",
       f"| 바이스태틱각 β · 표적 도플러 f_d | {GEO['beta_deg']:.2f}° · {GEO['fd_hz']:.2f} Hz "
       f"(속도 {abs(GEO['vel'][0]):.0f} m/s 직진) |",
       f"| 표적 σ | {GEO['sigma_dbsm']:.2f} dBsm |",
       f"| **DTR = 4π R1²R2²/(L²σ)** | **{GEO['dtr_db']:.1f} dB** |",
       "",
       f"⚠ **DTR {GEO['dtr_db']:.1f} dB 는 최악 가정이다.** 원장이 그 자리에 적어 둔 문장 그대로 — "
       f"«{GEO['note']}»", "",
       "**사슬의 형상** — 파형이 정한다. 전부 10 권 «결과» 의 헤드라인 규약 그대로다. "
       + SHAPE_W_FORM, "",
       "| 무엇 | " + " | ".join(LBL[m] for m in MODES) + " |",
       "|---|---|---|---|",
       "| 기준신호 대역 | " + " | ".join(f"{E1[m]['ref_bw_mhz']:.2f} MHz" for m in MODES) + " |",
       "| 표본율 f_s | " + " | ".join(f"{E1[m]['fs_hz']/1e6:.2f} MHz" for m in MODES) + " |",
       "| 프레임 M × 블록 b | " + " | ".join(f"{E1[m]['M']} × {E1[m]['b']}" for m in MODES) + " |",
       "| 슬로타임 PRF · T_CPI | " + " | ".join(f"{E1[m]['prf_hz']:.0f} Hz · "
                                              f"{E1[m]['T_cpi_ms']:.1f} ms" for m in MODES) + " |",
       "| 거리빈 폭 ΔR_b | " + " | ".join(f"{E1[m]['dRb_m']:.2f} m" for m in MODES) + " |",
       f"| 거리빈 수 · ECA 탭 | " + " | ".join(f"{E1[m]['n_range']} · {E1[m]['n_taps']}"
                                            for m in MODES) + " |",
       "| 이상 팔 출력 SINR | " + " | ".join(f"{E1[m]['sinr_ideal_db']:.2f} dB"
                                          for m in MODES) + " |",
       "| 트라이얼 (Pd · Pfa) | " + " | ".join(f"{E1R[m]['ideal']['K']} · "
                                             f"{E1R[m]['ideal']['Kpfa']}" for m in MODES) + " |",
       "| CFAR 셀 수 (Pfa 표본) | " + " | ".join(f"{E1R[m]['ideal']['n_cell']:,}"
                                              for m in MODES) + " |",
       "",
       f"⚠ 세 파형의 σ² 는 **팔 A 의 출력 SINR 이 목표값이 되도록 파형마다 교정**된다"
       f"(목표 {CFG['target_sinr_ideal_db']:.0f} dB). W1·L1 은 그 자리에 앉았고, "
       f"**G1 은 못 앉았다** — 잡음을 0 으로 보내도 출력 SINR 이 **{G1_CEIL:.1f} dB** 를 못 "
       f"넘는 천장이 있어 목표가 {G1_TGT:.2f} dB 로 내려갔다. 그 천장의 정체는 열잡음이 아니라 "
       f"**ECA 가 못 지운 직접파 잔류**다(절 6 의 {OP_CEIL}·{OP_DECIM}번 항목)."),

    md("### ⭐ 갈아끼워도 사슬이 안 변했다 — 항등식 검사", "",
       "표적을 «단일 도플러 톤» 에서 «마이크로도플러 원장» 으로 갈아끼우려면 `make_cpi` 의 "
       "표적항을 못 쓴다(그 항은 톤이다). 그래서 `make_cpi` 를 고치는 대신 **두 번 불러** "
       "① 깨끗한 지연복제 g 와 ② 배경(직접파+정적 클러터)을 따로 받고, g 에 복소변조 m(t) 를 "
       "곱한다. m(t)=exp(j2πf_d t) 를 넣으면 `make_cpi` 원래 동작과 **수치적으로 같아야 "
       "한다** — 그것을 실측한다.", "",
       "| 파형 | 상대오차 |",
       "|---|---|",
       "\n".join(f"| {LBL[m]} | {IDC[m]['rel_err']:.2e} |" for m in MODES),
       "",
       f"세 파형 모두 **{IDC_WORST:.1e}** — 배정밀도 반올림 수준이다. 원장이 그 자리에 적어 둔 "
       f"판정 그대로: «{IDC['W1']['note']}»", "",
       "즉 이 편에서 달라지는 것은 **기준신호 하나**이고, 사슬도 표적 주입 경로도 8 권의 "
       "그것과 같은 물건이다."),

    md("## 그림 1 — 기준채널 품질 사다리", "",
       embed("passive_f1"), "",
       "왼쪽이 기준채널 **잡음** 축, 오른쪽이 기준채널 **다중경로** 축이고 **세로 눈금이 "
       "같다**. 그 대비가 이 그림의 전부다 — 같은 자로 재면 한쪽은 벼랑이고 한쪽은 평지다. "
       "표식 채움과 아래 띠의 숫자가 검출률 Pd 다."),

    md("## 절 2. 절벽은 SNR 축에 있고 다중경로 축은 평지다", "",
       "**기준채널 잡음 — 손실 [dB] / Pd**", "",
       "| ρ_ref | " + " | ".join(LBL[m] for m in MODES) + " |",
       "|---|---|---|---|",
       "\n".join(f"| {k} dB | " + " | ".join(
           f"{SUM[m]['loss_db_by_refsnr'][k]:.2f} / {SUM[m]['pd_by_refsnr'][k]:.2f}"
           for m in MODES) + " |" for k in RHO),
       "",
       f"⭐ **절벽은 {CL_HI_N} ↔ {CL_LO_N} dB 사이다.** "
       + ("세 열이 전부 그 한 칸에서 Pd 0.5 를 가로지르지만, 그것이 «검출이 무너졌다» 와 "
          f"같은 사건인 것은 {SH['W1']}·{SH['L1']} 뿐이다(바로 아래 ⚠). "
          if CL_SAME else "파형마다 가로지르는 칸이 다르다"
          + "".join(f"({SH[m]} {CLIFF[m][0].lstrip('+')}→{CLIFF[m][1].lstrip('+')} dB) "
                    for m in MODES))
       + "그 한 칸에서 잃는 양은 "
       + " · ".join(f"{SH[m]} {SUM[m]['loss_db_by_refsnr'][CL_LO] - SUM[m]['loss_db_by_refsnr'][CL_HI]:.1f} dB"
                    for m in MODES) + " 다.", "",
       f"⚠ **{SH['G1']} 의 «가로지름» 은 이름뿐이다.** 그 열은 Pd 가 ρ 를 올려도 단조로 "
       f"오르지 않고(+{RHO[0].lstrip('+')} dB 에서 {SUM['G1']['pd_by_refsnr'][RHO[0]]:.2f}, "
       f"+{RHO[1].lstrip('+')} dB 에서 {SUM['G1']['pd_by_refsnr'][RHO[1]]:.2f}), 이상 팔조차 "
       f"{E1R['G1']['ideal']['pd']:.2f} 라 «Pd 0.5 를 가로지른다» 가 {SH['W1']}·{SH['L1']} 의 "
       f"그 한 칸에서 보이는 "
       f"{SUM['W1']['pd_by_refsnr'][CL_HI]:.2f}·{SUM['L1']['pd_by_refsnr'][CL_HI]:.2f} → "
       f"{SUM['W1']['pd_by_refsnr'][CL_LO]:.2f}·{SUM['L1']['pd_by_refsnr'][CL_LO]:.2f} 와 같은 "
       f"사건이 아니다. 절벽의 근거로는 {SH['W1']}·{SH['L1']} 만 쓴다.", "",
       "**기준채널 다중경로 — 손실 [dB]**", "",
       "| MDR | " + " | ".join(LBL[m] for m in MODES) + " |",
       "|---|---|---|---|",
       "\n".join(f"| {k} dB | " + " | ".join(f"{SUM[m]['loss_db_by_mdr'][k]:+.2f}"
                                             for m in MODES) + " |" for k in MDR),
       "",
       f"⭐ **평지다.** {len(MDR) * len(MODES)} 칸 전부 절댓값 **{MDR_WORST:.2f} dB** 안이고, "
       "부호가 왔다 갔다 한다 — 트라이얼 산포와 같은 크기라는 뜻이다. 검출률은 "
       f"{SH['W1']}·{SH['L1']} 에서 어느 칸이든 "
       f"{min(E1R[m][f'MDR{k}dB']['pd'] for m in ('W1', 'L1') for k in MDR):.2f} 이다"
       f"({SH['G1']} 은 {min(MDR_PD_G1):.2f}~{max(MDR_PD_G1):.2f} 로 이상 팔의 "
       f"{E1R['G1']['ideal']['pd']:.2f} 주변에서 떠다닌다 — 위 경고대로 따로 읽는다).", "",
       f"⚠ **«평지» 는 잰 구간 안에서의 진술이다.** 다중경로 축은 {MDR[-1]} dB 에서 끝난다 — "
       f"반사가 직접파와 비슷한 크기까지 세지는 경우는 이 편이 **안 쟀다**. 지연도 "
       f"{', '.join(f'{x:.1f}' for x in CFG['mp_delays_ns'])} ns 세 개의 단일 반사이고, "
       "확산된 다중경로가 아니다.", "",
       f"⭐ **두 축을 같이 흔든 칸이 하나 있다** — `{JOINT}`. 잡음 위에 다중경로를 얹어도 "
       "손실이 잡음만 넣은 것과 거의 같다. 다중경로가 «잡음이 없을 때만 무해한 것» 이 아니라는 "
       "확인이다.", "",
       "| 파형 | 잡음만 | 다중경로만 | 둘 다 | 둘 다 − 잡음만 |",
       "|---|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | {SUM[m]['loss_db_by_refsnr'][JOINT_RHO]:.2f} dB / Pd "
                 f"{E1R[m]['refSNR' + JOINT_RHO + 'dB']['pd']:.2f} | "
                 f"{SUM[m]['loss_db_by_mdr'][JOINT_MDR]:+.2f} dB / Pd "
                 f"{E1R[m]['MDR' + JOINT_MDR + 'dB']['pd']:.2f} | "
                 f"{E1R[m][JOINT]['loss_db']:.2f} dB / Pd {E1R[m][JOINT]['pd']:.2f} | "
                 f"{E1R[m][JOINT]['loss_db'] - SUM[m]['loss_db_by_refsnr'][JOINT_RHO]:+.2f} dB |"
                 for m in MODES), "",
       "**왜 한쪽만 절벽인가 — 표적이 내려간 것이 아니라 바닥이 올라온 것이다.**", "",
       "같은 팔 안에서 RD 맵의 **표적 피크**와 **바닥**을 따로 재면 갈린다.", "",
       f"⚠ **이 표는 E1c 묶음이다 — 절 4 의 분해와 같은 팔이고, 위 사다리(E1)와는 다른 "
       f"실험이다.** 팔 이름은 같지만 트라이얼이 팔당 "
       f"{E1R['W1']['ideal']['K']} → {E1CR['W1']['ideal']['K']} 으로 적고, σ² 도 따로 "
       f"재교정했다({E1['W1']['noise_var']:.0f} → {E1C['W1']['noise_var']:.0f}, "
       f"{SH['W1']} 기준). 그래서 같은 `refSNR{JOINT_RHO}dB` 라벨의 손실이 위 사다리에서 "
       f"{SUM['W1']['loss_db_by_refsnr'][JOINT_RHO]:.2f} dB, 이 표에서 "
       f"{MECH['W1']['rows']['refSNR' + JOINT_RHO + 'dB']['loss_db']:.2f} dB 다. 두 값이 "
       f"어디서 갈리는지는 절 5 첫 표가 한 자리에 놓는다.", "",
       "| 파형 | 팔 (E1c) | 피크 변화 | 바닥 변화 | 손실 (E1c) |",
       "|---|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | `{a}` | {MECH[m]['rows'][a]['d_peak_db']:+.2f} dB | "
                 f"**{MECH[m]['rows'][a]['d_floor_db']:+.2f} dB** | "
                 f"{MECH[m]['rows'][a]['loss_db']:.2f} dB |"
                 for m in MODES for a in ("refSNR+20dB", "refSNR+10dB")),
       "",
       f"원장의 판정 그대로 — «{MECH['W1']['verdict']}»", "",
       "기준신호에 섞인 잡음은 ECA 가 푸는 최소제곱 가중치에 실려 나오고, 그 가중치로 뺀 "
       "직접파는 **덜 지워진다**. 남은 직접파가 맵 전체의 바닥을 들어 올린다. 그래서 "
       "표적 신호는 그대로인데 SINR 만 무너진다.", "",
       "**ECA 소거깊이가 그 사슬을 그대로 보여준다** — 이 표는 다시 **E1 사다리**다"
       "(위 피크·바닥 표만 E1c 다).", "",
       "| ρ_ref (E1) | " + " | ".join(LBL[m] for m in MODES) + " |",
       "|---|---|---|---|",
       "\n".join(f"| `{('ideal' if k is None else 'refSNR' + k + 'dB')}` | " + " | ".join(
           f"{SUM[m]['eca_depth_db_by_arm']['ideal' if k is None else 'refSNR' + k + 'dB']:.1f} dB"
           for m in MODES) + " |" for k in [None] + RHO),
       "",
       "⚠ **G1 은 이 표에서 다른 물건이다.** 이상 팔에서도 Pd 가 "
       f"{E1R['G1']['ideal']['pd']:.2f} 이고(W1·L1 은 "
       f"{E1R['W1']['ideal']['pd']:.2f}), 손실이 ρ 를 내려도 W1·L1 만큼 안 오른다. "
       f"이유는 G1 의 팔 A 바닥이 이미 열잡음이 아니라 직접파 잔류이기 때문이다"
       f"(천장 {G1_CEIL:.1f} dB). 절 3 의 경험식이 G1 에서 깨지는 것도 같은 이유다.", "",
       f"⚠ **팔 간 Pd 비교는 «같은 경험적 Pfa» 가 아니다 — 어긋남은 오염 이전부터 있다.** "
       f"명목 Pfa 는 별도 교정표(`{CFG['pfa_calibration_source']}`)에서 빌려 온 값이고, "
       + SHAPE_W_PFA
       + f"그래서 오염이 0 인 `ideal` "
       f"팔에서도 경험 Pfa 가 목표({CFG['pfa_target_emp']:.0e})의 "
       + " · ".join(f"{SH[m]} {PFA_IDEAL_R[m]:.2f}" for m in MODES)
       + " 배다. 기준채널이 오염되면 RD 맵의 통계가 거기서 더 움직여 교정이 더는 성립하지 "
       f"않는다. 그래서 팔마다 경험 Pfa 를 같이 쟀다(절 6 의 {OP_PFA}번 항목).", "",
       f"· {SH['W1']}·{SH['L1']} 은 **이 사다리의** 팔 전체가 "
       f"**{min(PFA_WL):.1e} ~ {max(PFA_WL):.1e}**, 즉 목표의 "
       f"{min(PFA_WL_RATIO):.2f}~{max(PFA_WL_RATIO):.2f} 배다. 같은 자릿수 안이라 "
       "이 두 파형끼리는 Pd 를 나란히 읽는다 — 다만 «똑같은 Pfa 에서 잰 Pd» 는 아니다.", "",
       f"· ⚠ {SH['G1']} 은 **{min(PFA_G1):.1e} ~ {max(PFA_G1):.1e}** 로 목표보다 크게 아래이고, "
       f"한 팔은 오검출이 아예 {G1_FA_MIN_ROW['n_fa']} 건이다"
       f"(`{G1_FA_MIN_ROW['arm']}`, 셀 {G1_FA_MIN_ROW['n_cell']:,} 개). 문턱이 그만큼 보수적으로 "
       f"서 있다는 뜻이므로 **{SH['G1']} 의 Pd 는 다른 두 파형과 나란히 읽으면 안 된다.** "
       f"오검출이 {G1_FA_MIN_ROW['n_fa']} 건이면 그 팔의 Pfa 는 «측정된 값» 이 아니라 "
       f"«{E1R['G1']['ideal']['Kpfa']} 트라이얼로는 못 잰 값» 이다.", "",
       f"⚠ 위 두 범위는 **이 사다리(E1)** 의 것이다. 절 4·절 5 의 팔까지 넣으면 "
       f"{SH['W1']}·{SH['L1']} 의 경험 Pfa 가 **{min(PFA_WL_ALL):.1e} ~ "
       f"{max(PFA_WL_ALL):.1e}**(목표의 {min(PFA_WL_ALL_RATIO):.2f}~"
       f"{max(PFA_WL_ALL_RATIO):.2f} 배)로 벌어진다 — 그 팔들은 트라이얼이 적어 추정 자체가 "
       "성기다(부록의 트라이얼 표)."),

    md("### DTR 을 깎으면 절벽이 어디로 가나", "",
       "헤드라인 DTR 은 감시안테나가 등방이라는 최악값이다. 안테나 패턴·차폐로 DTR 을 깎으면 "
       "같은 ρ_ref 에서 손실이 어떻게 되는지, ρ_ref = "
       f"{DTR_SENS_RHO:.0f} dB 한 칸에서 잰다.", "",
       "| DTR | " + " | ".join(LBL[m] for m in MODES) + " |",
       "|---|---|---|---|",
       "\n".join(f"| {d:.0f} dB | " + " | ".join(
           f"{DTRS[(m, d)][DTR_SENS_ARM]['loss_db']:.2f} dB / "
           f"Pd {DTRS[(m, d)][DTR_SENS_ARM]['pd']:.2f}" for m in MODES) + " |"
           for d in DTR_AXIS)
       + f"\n| **{GEO['dtr_db']:.1f} dB (헤드라인)** | " + " | ".join(
           f"**{SUM[m]['loss_db_by_refsnr']['+20']:.2f} dB / Pd "
           f"{SUM[m]['pd_by_refsnr']['+20']:.2f}**" for m in MODES) + " |",
       "",
       f"⭐ **DTR 은 둘째 손잡이다 — 다만 «dB 대 dB» 는 격자 위쪽에서만이다.** 이 표는 "
       f"**DTR {'·'.join(f'{d:.0f}' for d in sorted(DTR_AXIS))} dB {len(DTR_AXIS)} 칸 × "
       f"ρ_ref {DTR_SENS_RHO:.0f} dB 한 칸**을 팔당 "
       f"{'/'.join(str(k) for k in DTR_K['W1'])} 트라이얼로 잰 것이다. {SH['W1']} 에서 DTR 을 "
       f"{DTR_DROP_HI:.0f} → {DTR_DROP_LO:.0f} dB 로 {DTR_DROP_HI - DTR_DROP_LO:.0f} dB 깎으면 "
       f"손실이 {dtr_loss('W1', DTR_DROP_HI):.1f} → {dtr_loss('W1', DTR_DROP_LO):.1f} dB 로 "
       f"내려간다. 그러나 **기울기는 칸마다 다르다** — "
       + " · ".join(f"{hi:.0f}→{lo:.0f} dB 에서 {SH['W1']} {sw:.2f} · {SH['L1']} {sl:.2f} dB/dB"
                    for (hi, lo), sw, sl in zip(DTR_STEPS, DTR_SLOPE["W1"], DTR_SLOPE["L1"]))
       + f" 다. 아래쪽 칸에서 꺾이는 것은 잡음이 아니라 **경험식의 무릎**이다 — 이 격자의 "
       f"아래끝 DTR {DTR_DROP_LO:.0f} dB 가 정확히 2ρ_ref = {DTR_KNEE:.0f} dB 라 거기서 곡선이 "
       f"{DTR_LAW_3DB:.2f} dB 로 눕는다. ⛔ 그러므로 «DTR 을 1 dB 깎으면 손실 1 dB 를 "
       f"돌려받는다» 는 **DTR ≫ 2ρ_ref 인 쪽에서만** 읽는다. DTR {DTR_DROP_LO:.0f} dB 아래는 "
       f"**안 쟀다** — 더 깎아서 남은 {DTR_LAW_3DB:.2f} dB 보다 더 벌 수 있는지는 이 편이 "
       f"모른다. {SH['G1']} 행은 기울기가 "
       + "·".join(f"{s:.2f}" for s in DTR_SLOPE["G1"])
       + f" dB/dB 로 아예 다른 물건이다(천장 {G1_CEIL:.1f} dB). 이 표에서 확실한 것은 하나다 "
       "— 이 편의 손실 수치는 «기준채널이 나쁘다» 만의 함수가 아니라 **감시안테나가 직접파를 "
       "얼마나 죽였는가**의 함수이기도 하고, 실측 설계에서 두 손잡이는 **독립**이다.", "",
       f"⚠ **«검출이 되살아난다» 도 {len(DTR_AXIS)} 칸짜리 진술이다.** {SH['W1']} 의 Pd 는 DTR "
       + " → ".join(f"{d:.0f} dB {DTRS[('W1', d)][DTR_SENS_ARM]['pd']:.2f}" for d in DTR_DOWN)
       + f" 인데 팔당 {DTR_K['W1'][0]} 트라이얼이라 Pd 눈금 자체가 "
       f"{1.0/DTR_K['W1'][0]:.2f} 다. Pd 가 0.5 를 가로지르는 자리는 **DTR "
       f"{DTR_DOWN[0] - DTR_DOWN[1]:.0f} dB 폭 한 칸 안**으로만 안다 — 그 안 어디인지는 "
       "안 쟀다.", "",
       f"⚠ **이 표는 절 3 의 설계 규칙(ρ_ref ≥ DTR/2)을 «확인» 하지 못한다 — 그 자리는 "
       f"경험식의 등호 자리라 값이 정의상 나온다.** ρ_ref 가 DTR/2 면 식의 지수가 정확히 "
       f"0 이라 loss = 10log₁₀(1+10⁰) = **{DTR_LAW_3DB:.2f} dB** 이고, 설계 규칙은 그 등호를 "
       f"«{LAW['design_rule']}» 로 옮겨 적은 것이다. DTR {DTR_CHECK:.0f} dB 칸"
       f"(ρ_ref = {DTR_SENS_RHO:.0f} dB 가 정확히 DTR/2 인 자리)에서 «3 dB 가 나왔다» 는 "
       "그래서 규칙의 검증이 아니다.", "",
       f"이 칸이 실제로 재는 것은 하나다 — **ρ 축에서 맞춘 식이 DTR 축에서도 같은 "
       f"DTR − 2ρ_ref 꼴로 움직이는가.** 잰 값과 식의 차이는 "
       + " · ".join(f"{SH[m]} " + "/".join(f"{r:+.2f}" for r in DTR_RESID[m])
                    for m in ("W1", "L1"))
       + f" dB(DTR {'/'.join(f'{d:.0f}' for d in DTR_DOWN)} dB 순), 즉 {len(DTR_AXIS)} 칸 전부 "
       f"절댓값 {DTR_RESID_WL:.2f} dB 안이다. ⛔ 다만 그 차이는 같은 식이 ρ 축에서 이미 내는 "
       f"평균절대오차 **{LAW['fit_mae_db_W1_L1']:.2f} dB** 보다 작다 — 이 격자로는 규칙의 "
       f"3 dB 를 그 오차보다 좁게 못 박는다. 그리고 이것은 **ρ_ref 한 칸 · DTR "
       f"{len(DTR_AXIS)} 칸 · 팔당 {DTR_K['W1'][0]} 트라이얼 · {SH['W1']}·{SH['L1']} 두 "
       f"파형**의 진술이다. 같은 {len(DTR_AXIS)} 칸에서 {SH['G1']} 의 차이는 "
       + "/".join(f"{r:+.2f}" for r in DTR_RESID["G1"])
       + " dB 라 규칙이 거기까지 가지 않는다.", "",
       "⚠ **왜 2ρ_ref 인지는 모른다.** 원장이 그 자리에 적어 둔 그대로 — 이 식은 유도된 "
       "것이 아니라 **맞춰 본** 것이고, 1차 이론 추정(잔류 = dpi²σ_n²)은 이 기울기를 "
       "재현하지 못한다(절 3 의 적용범위 문장). 그러므로 «ρ_ref ≥ DTR/2» 는 **잰 격자 안에서 "
       "성립한 경험 규칙**이지 물리에서 나온 문턱이 아니다."),

    md("## 절 3. ⭐ ρ 는 자유 파라미터가 아니다", "",
       "절 2 의 사다리는 ρ_ref 를 **가정**해 훑은 것이다. 그런데 같은 링크버짓 안에서는 "
       "ρ_ref 가 계산된다 — 기준안테나가 받는 것은 감시안테나가 지우려는 바로 그 직접파이고, "
       "잡음은 같은 수신기의 잡음이다.", "",
       "$$\\rho_{ref}[\\mathrm{dB}] \\;=\\; \\mathrm{DTR} \\;-\\; G_{proc} \\;+\\; "
       "\\mathrm{SINR}_{target}$$", "",
       f"원장이 그 자리에 적어 둔 문장 그대로 — «{SUM['W1']['closed_form']}»", "",
       "| 파형 | DTR | 처리이득 G_proc | 이상 팔 SINR | ⇒ 자기일관 ρ_ref | 그 자리의 손실 / Pd |",
       "|---|---|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | {SUM[m]['dtr_db']:.1f} dB | {SUM[m]['proc_gain_db']:.2f} dB | "
                 f"{SUM[m]['sinr_ideal_db']:.2f} dB | **{SUM[m]['rho_ref_selfconsistent_db']:.2f} dB** | "
                 f"{SUM[m]['loss_at_selfconsistent_db']:.2f} dB / "
                 f"{SUM[m]['pd_at_selfconsistent']:.2f} |" for m in MODES),
       "",
       f"⚠ 이 ρ_ref 는 **«안테나로 아무것도 안 했을 때» 의 점**이지 예측이 아니다. 원장의 "
       f"단서 그대로 — «{SUM['W1']['note']}»", "",
       f"⚠ **오른쪽 두 칸은 사다리 두 칸 사이의 선형 보간이다.** 자기일관 ρ_ref 가 스윕 격자 "
       f"위에 앉지 않아서다. 특히 Pd 는 그 구간이 바로 절 2 의 **절벽**이라"
       f"({CL_HI_N} dB 에서 {SUM['W1']['pd_by_refsnr'][CL_HI]:.2f}, {CL_LO_N} dB 에서 "
       f"{SUM['W1']['pd_by_refsnr'][CL_LO]:.2f}) 그 보간값"
       f"({SUM['W1']['pd_at_selfconsistent']:.2f})은 **측정된 검출률이 아니다** — «절벽 안쪽» "
       "이라는 위치 표시로만 읽어야 한다.", "",
       "**그래서 뒤집어 읽는다 — 3 dB 손실을 지키려면 기준채널 SNR 이 얼마여야 하나.**", "",
       "| 파형 | 필요한 ρ_ref (손실 3 dB) | 지금 서 있는 자리 | ⇒ **기준안테나 이득 요구치** |",
       "|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | {SUM[m]['ref_snr_needed_for_3db_loss']:.2f} dB"
                 f"{NM_MARK[m]} | "
                 f"{SUM[m]['rho_ref_selfconsistent_db']:.2f} dB | "
                 f"**{SUM[m]['ref_antenna_gain_needed_db']:.2f} dB** |" for m in MODES),
       "",
       REQ_NOTE, "",
       f"⭐ **이것이 이 편에서 실측 설계로 넘어가는 다리다.** {SH['W1']}·{SH['L1']} 의 요구치가 "
       f"{GAIN_WL_LO:.1f}~{GAIN_WL_HI:.1f} dB 이므로, 기준안테나는 조명원 방향으로 그만큼의 "
       "이득을 **감시안테나보다 더** 가져야 한다. «패시브 수신기를 두 개 만든다» 는 설계 "
       "결정이 여기서 숫자로 나온다.", "",
       "⚠ 이 «요구치» 는 절대 사양이 아니라 **바로 위 표의 자기일관 ρ_ref 를 기준선으로 뺀 "
       "차이**다. 그 기준선이 퇴화된 점이므로(바로 위 ⚠), 읽는 법은 «기준안테나가 이만큼의 "
       "이득을 내야 한다» 가 아니라 «안테나로 아무것도 안 한 자리에서 이만큼을 더 벌어야 "
       "한다» 다. 실제 프론트엔드가 그것을 내는지는 11 권이 닫는다.", "",
       f"⚠ 세 요구치 중 **{SH['G1']} 의 값은 다른 뜻이다** — {SH['G1']} 은 손실 곡선 자체가 "
       f"천장에 눌려 있어 «3 dB 손실» 이라는 기준이 {SH['W1']}·{SH['L1']} 과 같은 물건이 "
       f"아니고, 그 눌림이 곡선을 비단조로 만들어 교차점이 위 ⚠ 의 보간으로 잡힌다. "
       f"설계 근거로는 {SH['W1']}·{SH['L1']} 의 "
       f"{GAIN_WL_LO:.1f}~{GAIN_WL_HI:.1f} dB 를 쓴다.", "",
       "**⭐ 스윕에서 읽어낸 경험식**", "",
       f"$$\\text{{loss}}[\\mathrm{{dB}}] \\;=\\; 10\\log_{{10}}\\!\\left(1 + "
       f"10^{{(\\mathrm{{DTR}} - 2\\rho_{{ref}})/10}}\\right)$$", "",
       f"같은 것을 다르게 쓰면 — «{LAW['equivalently']}» 이고, 설계 규칙으로 옮기면 "
       f"«{LAW['design_rule']}» 이다.", "",
       "| 파형 | ρ_ref | 실측 손실 | 식이 주는 값 | 잔차 |",
       "|---|---|---|---|---|",
       "\n".join(f"| {LBL[p['mode']]} | {p['rho_db']:.0f} dB | {p['measured_db']:.2f} dB | "
                 f"{p['law_db']:.2f} dB | {p['resid_db']:+.2f} dB |" for p in LAW["points"]),
       "",
       f"W1·L1 은 평균절대오차 **{LAW['fit_mae_db_W1_L1']:.2f} dB** 로 맞는다. "
       f"**G1 은 안 맞는다 — {LAW['fit_mae_db_G1']:.1f} dB** 다.", "",
       f"⚠ 원장이 스스로 적어 둔 적용범위 그대로 — «{LAW['scope']}»"),

    md("## 그림 2 — 어느 단이 대가를 무나", "",
       embed("passive_f2"), "",
       "(a)(b) 가 오염을 **한 단에만** 넣은 분해이고, (c)(d) 가 ECA 노치의 값과 대가다. "
       "(c) 의 세로축 0 dB 는 날개끝 띠이고, (d) 의 대조군은 직접파를 끈 **표적만 있는** "
       "형상이다 — 그래야 노치가 «무엇을 걷어냈나» 가 아니라 «표적에서 무엇을 뺏었나» 를 "
       "잰다."),

    md("## 절 4. 손실은 전부 ECA 단에서 나온다 — 그리고 노치 자체는 싸다", "",
       "오염된 기준신호를 **정합필터에만** 준 팔, **ECA 에만** 준 팔, 둘 다 준 팔을 나란히 "
       "돌린다.", "",
       f"⚠ 이 분해는 **E1c 묶음**이다 — 절 2 의 피크·바닥 표와 같은 팔이고, 절 2 사다리(E1)와는 "
       f"트라이얼(팔당 {E1CR['W1']['ideal']['K']} 대 {E1R['W1']['ideal']['K']})도 σ² 교정도 "
       f"다른 실험이다(절 5 첫 표).", "",
       "| 파형 | 오염 수준 | 정합필터만 | ECA 만 | 둘 다 |",
       "|---|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | ρ_ref {r} dB | "
                 f"**{E1CR[m][f'CAFonly-noisy{r}dB']['loss_db']:+.2f} dB** | "
                 f"{E1CR[m][f'ECAonly-noisy{r}dB']['loss_db']:.2f} dB | "
                 f"{E1CR[m][f'refSNR{r}dB']['loss_db']:.2f} dB |"
                 for m in MODES for r in ("+20", "+10")),
       "",
       f"⭐ **판정: 전부 ECA 단이다.** 정합필터만 오염시키면 손실이 "
       f"{CAF_LO:+.2f}~{CAF_HI:+.2f} dB 이고 검출률도 안 떨어진다"
       f"(`CAFonly-noisy+20dB` 의 Pd "
       + " · ".join(f"{SH[m]} {E1CR[m]['CAFonly-noisy+20dB']['pd']:.2f}" for m in MODES)
       + "). ECA 만 오염시키면 둘 다 오염시킨 것과 거의 같은 손실이 나온다.", "",
       "**왜 ECA 만 아픈가.** 정합필터는 기준신호를 **상관기의 템플릿**으로 쓴다 — 템플릿에 "
       "잡음이 섞이면 정합이 조금 나빠질 뿐이고, 그 대가는 상관이득 안에서 평균된다. ECA 는 "
       "기준신호로 **XᴴX 를 풀어 감시채널에서 뺄 것을 만든다** — 그 역행렬이 잡음을 "
       "증폭하고, 잘못 만든 뺄셈은 직접파를 남긴다. 남은 직접파는 평균되지 않고 맵 전체의 "
       "바닥이 된다(절 2 의 피크/바닥 표).", "",
       "그 민감도는 기준신호의 조건수로 갈린다.", "",
       "| 파형 | ECA 행렬 조건수 |",
       "|---|---|",
       "\n".join(f"| {LBL[m]} | {MECH[m]['ref_cond_db']:.1f} dB |" for m in MODES),
       "",
       f"⚠ 조건수가 가장 나쁜 것은 대역이 가장 좁은 {SH['G1']}"
       f"({MECH['G1']['ref_cond_db']:.1f} dB)이고, 그것이 G1 의 «천장» 과 같은 뿌리다 — "
       f"{E1['G1']['ref_bw_mhz']:.1f} MHz 기준신호를 {E1['G1']['fs_hz']/1e6:.2f} MHz 로 "
       "표본화한 채 ECA 를 풀면 행렬이 준특이라 직접파가 안 지워진다.", "",
       "**⭐ 그런데 노치 자체는 싸다.**", "",
       "| 무엇 | 값 |",
       "|---|---|",
       f"| ECA 를 끄면 0-도플러가 날개끝 띠 대비 | **{SURV['noECA']['zero_bin_rel_tip_db']:+.1f} dB** |",
       f"| ECA 를 켜면 | {SURV['ideal']['zero_bin_rel_tip_db']:+.1f} dB |",
       f"| ⇒ 직접파가 있을 때 노치가 버는 값 | "
       f"{SURV['noECA']['zero_bin_rel_tip_db'] - SURV['ideal']['zero_bin_rel_tip_db']:.2f} dB |",
       f"| **표적만 있는 대조군에서 노치가 무는 대가** | "
       f"**{NOTCH['value']:.2f} dB** |",
       "",
       f"원장의 정의 그대로 — «{NOTCH['what']}»", "",
       "즉 «ECA 가 0-도플러를 파먹어 동체선을 잃는다» 는 걱정은 이 형상에서 값이 "
       f"{NOTCH['value']:.2f} dB 이고, 같은 노치가 직접파가 있을 때 "
       f"{SURV['noECA']['zero_bin_rel_tip_db'] - SURV['ideal']['zero_bin_rel_tip_db']:.0f} dB 를 "
       "번다. ⚠ 이 대조군은 **로터가 지배하는 호버**라 0-도플러에 노치가 가져갈 동체 에너지가 "
       "애초에 적다 — 기동 중인 표적에서는 이 값이 커진다."),

    md("## 그림 3 — 마이크로도플러는 검출이 죽은 뒤에도 남는가", "",
       embed("passive_f3"), "",
       "(a)~(d) 가 사다리의 시간-도플러 맵이고 **공통 눈금**이다(팔마다 자기 최대로 맞추면 "
       "«바닥이 올라온다» 가 사라진다). (e) 가 그 바닥을 절대 눈금 하나로 잰 것, (f) 가 "
       "날개끝 띠 전력의 시간축(플래시 빗살), (g) 가 플래시 선 세기와 Pd 를 나란히 놓은 "
       "것이다. (h)(i)(j) 는 **잡음이 아닌 방식으로** 빗살이 죽는 두 경우다.", "",
       "⚠ (g) 의 막대(플래시)와 아래 띠(Pd)는 **다른 사슬에서 잰 값**이다 — 팔 이름만 같다. "
       "무엇이 다른지는 절 5 첫 표에 있다.", "",
       "⭐ 맵은 전부 `src/md_mapstyle.py` 규약이다 — STFT 만 쓰고(재할당·WVD 없음), "
       "jet · 0~−40 dB · gouraud · 날개끝 흰 파선. 조각 길이·hop 등 설정값은 부록에 적었다."),

    md("## 절 5. Pd 가 0 인 칸에서 빗살은 어디까지 남나 — 그리고 5G 는 접힌다", "",
       "표적 거리빈에서 슬로타임을 꺼내 시간-도플러 맵을 만들고, 같은 이름의 사다리에서 "
       "**플래시가 읽히는가**를 잰다.", "",
       f"**먼저 지표의 뜻.** `플래시 선 세기` 는 절대 세기가 아니라 **비**다 — 날개끝 띠 전력의 "
       f"시간축 스펙트럼에서 플래시 주파수 성분이 그 스펙트럼의 **배경 중앙값보다 몇 dB "
       f"솟았나**이다(정의는 `{META['script']}` 의 `md_metrics`). 그래서 이 값이 0 dB 로 "
       "내려오면 빗살이 배경에 묻혔다는 뜻이고, 값이 크면 «빗살이 주기적으로 서 있다» 는 뜻이다. "
       "`플래시 대비` 는 같은 띠 전력의 시간축 p95−p5 이고 **잡음 변동만으로도 커진다** — "
       "판정값은 선 세기 쪽이다.", "",
       "⚠ **여기에는 사다리가 둘이고, 둘 다 절 2 의 사다리와 같은 물건이 아니다.** 팔 이름만 "
       "같다 — 맵은 생존 사다리에서, Pd 는 그것과 또 다른 검출 사다리에서 나온다. 아래 표는 "
       "이 편이 돌린 네 묶음을 한 자리에 놓는다. 절 2 끝의 피크·바닥 표와 절 4 의 분해가 쓰는 "
       f"**E1c** 도 여기 들어 있다 — 같은 `refSNR{JOINT_RHO}dB` 라벨의 손실이 "
       f"{SUM['W1']['loss_db_by_refsnr'][JOINT_RHO]:.2f} dB(E1) 와 "
       f"{E1CR['W1']['refSNR' + JOINT_RHO + 'dB']['loss_db']:.2f} dB(E1c) 로 갈리는 자리가 "
       "이 표의 마지막 두 줄이다.", "",
       "| 무엇 | 절 2 의 검출 사다리 (E1) | 절 2 끝·절 4 의 피크·바닥과 분해 (E1c) | "
       "절 5 의 Pd 를 낸 사다리 (E1b) | 절 5 의 맵 (E2) |",
       "|---|---|---|---|---|",
       f"| 표적 모형 | {E1['W1']['target_model']} (단일 도플러 톤) | "
       f"{E1C['W1']['target_model']} (같은 톤) | "
       f"{DET['target_model']} (마이크로도플러 원장) | {DET['target_model']} (같은 원장) |",
       f"| 슬로타임 사슬 | 블록 b={E1['W1']['b']} · PRF {E1['W1']['prf_hz']:.0f} Hz · "
       f"T_CPI {E1['W1']['T_cpi_ms']:.0f} ms | b={E1C['W1']['b']} · PRF "
       f"{E1C['W1']['prf_hz']:.0f} Hz · T_CPI {E1C['W1']['T_cpi_ms']:.0f} ms | "
       f"b={DET['b']} · PRF {DET['prf_hz']:.0f} Hz · "
       f"T_CPI {DET['T_cpi_ms']:.0f} ms | b={SURVCFG['b']} · PRF {SURVCFG['prf_hz']:.0f} Hz · "
       f"관측 {SURVCFG['seconds']*1e3:.0f} ms |",
       f"| 날개끝이 접히나 | **접힌다** (f_tip {ALIAS['f_tip_hz']:.0f} Hz > "
       f"±{E1['W1']['prf_hz']/2:.0f} Hz) | **접힌다** (±{E1C['W1']['prf_hz']/2:.0f} Hz) | "
       f"**접힌다** (±{DET['prf_hz']/2:.0f} Hz) | "
       f"안 접힌다 (±{SURVCFG['f_unamb_hz']:.0f} Hz) |",
       f"| σ² | {E1['W1']['noise_var']:.0f} (목표 SINR "
       f"{CFG['target_sinr_ideal_db']:.0f} dB) | {E1C['W1']['noise_var']:.0f} — 같은 목표 "
       f"{E1C['W1']['sinr_target_db']:.0f} dB 를 이 묶음에서 **따로 재교정**했다 | "
       f"{DET['noise_var']:.0f} — 표적이 "
       f"마이크로도플러라 같은 출력 SINR 을 맞추려고 톤 실험보다 **{NV_GAP_DB:.1f} dB 낮게** "
       f"잡혔다 | {SURVCFG['noise_var']:.0f} (목표 SINR "
       f"{SURVCFG['sinr_target_db']:.0f} dB) |",
       f"| 트라이얼 (Pd · Pfa) | {E1R['W1']['ideal']['K']} · {E1R['W1']['ideal']['Kpfa']} | "
       f"{E1CR['W1']['ideal']['K']} · {E1CR['W1']['ideal']['Kpfa']} | "
       f"{E1BR['W1']['ideal']['K']} · {E1BR['W1']['ideal']['Kpfa']} | — |",
       f"| `refSNR{JOINT_RHO}dB` 팔의 손실 | "
       f"**{SUM['W1']['loss_db_by_refsnr'][JOINT_RHO]:.2f} dB** | "
       f"**{E1CR['W1']['refSNR' + JOINT_RHO + 'dB']['loss_db']:.2f} dB** | "
       f"{E1BR['W1']['refSNR' + JOINT_RHO + 'dB']['loss_db']:.2f} dB | — |",
       "",
       f"그래서 같은 `refSNR{JOINT_RHO}dB` 라벨인데도 Pd 가 절 2 표에서는 "
       f"{SUM['W1']['pd_by_refsnr'][JOINT_RHO]:.2f}, 여기서는 "
       f"{PD_B['refSNR+20dB']:.2f} 다 — 모순이 아니라 **링크버짓이 다른 두 실험**이다. "
       "⚠ 따라서 아래 표의 «플래시» 열과 «Pd» 열은 **서로 다른 사슬에서 잰 값**이다. "
       "나란히 놓은 것은 «같은 기준채널 품질에서 두 능력이 각각 어떻게 되나» 를 보려는 "
       "것이지 한 실험의 두 출력이 아니다.", "",
       "| 팔 | 플래시 선 세기 | 플래시 대비 | 0-도플러 / 날개끝 | 같은 이름 팔의 Pd |",
       "|---|---|---|---|---|",
       "\n".join(f"| `{k}` | {SURV[k]['flash_line_db']:.1f} dB | "
                 f"{SURV[k]['flash_contrast_db']:.2f} dB | "
                 f"{SURV[k]['zero_bin_rel_tip_db']:+.2f} dB | "
                 + (f"{E1BR['W1'][k]['pd']:.2f} |" if k in E1BR["W1"] else "— |")
                 for k in ("ideal", "refSNR+20dB", "refSNR+10dB", "MDR-20dB", "noECA"))
       + f"\n| `ledger_direct` (사슬 미경유) | {LD['flash_line_db']:.1f} dB | "
         f"{LD['flash_contrast_db']:.2f} dB | — | — |",
       "",
       f"⭐ **Pd 가 {PD_B['refSNR+10dB']:.2f} 인 칸에서도 빗살 선은 배경보다 "
       f"{FL['refSNR+10dB']:.1f} dB 위에 있다 — 다만 여유는 그 전에 거의 다 썼다.** "
       f"플래시 선은 {FL['ideal']:.1f} → {FL['refSNR+20dB']:.1f} → {FL['refSNR+10dB']:.1f} dB "
       f"로 모두 {FL_DROP_TOT:.1f} dB 내려가는데, 그 중 **{FL_DROP_1:.1f} dB 가 첫 칸에서** "
       f"빠진다. 그 첫 칸의 Pd 는 아직 {PD_B['refSNR+20dB']:.2f} 다. 즉 «검출이 먼저 죽는다» "
       f"는 순서는 **마지막 한 칸에서만** 성립하고, 여유를 잃는 속도는 빗살 쪽이 훨씬 빠르다. "
       f"그리고 `refSNR{FL_LADDER[-1].replace('refSNR', '')}` 아래 칸은 **안 쟀다** — "
       "곡선이 어디서 0 dB 에 닿는지는 이 편이 모른다.", "",
       f"⚠ **이 «생존» 은 측정점 한 개다.** Pd 가 0 인 팔은 `{FL_LADDER[-1]}` 하나뿐이고, "
       f"파형은 {SH['W1']} 하나뿐이며(5G 사슬의 맵은 `{NR_SURV_ARMS[0]}` 팔 "
       f"{len(NR_SURV_ARMS)} 개뿐이라 사다리가 없다), 잡음 팔 자체가 "
       f"{len(SURV_NOISY_ARMS)} 칸뿐이다. 게다가 이 사슬은 **날개끝이 안 접히는 쪽**이고 "
       f"검출 CPI 는 접히는 쪽이다. ⛔ 그러므로 이 절을 **«검출은 실패해도 분류는 된다»** 로 "
       "일반화하면 안 된다 — 분류기를 돌려 본 적이 없고, 잰 것은 «한 칸에서 빗살 선이 아직 "
       "배경 위에 있었다» 까지다.", "",
       f"⚠ 플래시 **대비**는 오히려 {SURV['ideal']['flash_contrast_db']:.2f} → "
       f"{SURV['refSNR+10dB']['flash_contrast_db']:.2f} dB 로 **커진다**. 무늬가 또렷해진 것이 "
       "아니라 띠 전력의 변동에 잡음 변동이 얹힌 것이다 — 이 상승을 «잡음이 늘었는데 분류가 "
       "쉬워졌다» 로 읽으면 거꾸로 읽는 것이다.", "",
       "⚠ 이 판정은 **표적의 거리빈을 알고 있을 때** 읽은 것이다. 즉 «찾기» 가 아니라 "
       "«알아보기» 에 대한 진술이다. 검출이 죽은 팔에서 이 맵을 얻으려면 표적 위치를 다른 "
       "수단이 알려 줘야 한다.", "",
       "**빗살이 죽는 방식은 잡음 말고 둘 더 있다.**", "",
       f"① **ECA 를 끄면 동체선이 덮는다.** 0-도플러 한 빈이 날개끝 띠보다 "
       f"**{SURV['noECA']['zero_bin_rel_tip_db']:+.1f} dB** 위로 솟는다(켜면 "
       f"{SURV['ideal']['zero_bin_rel_tip_db']:+.1f} dB). 플래시 선 세기 자체는 "
       f"{SURV['noECA']['flash_line_db']:.1f} dB 로 높지만, 읽히는 것은 동체선이지 "
       "블레이드가 아니다.", "",
       f"② ⭐ **5G 팔은 프레임률로 날개끝이 접힌다.** 이 팔이 채널을 읽는 속도는 "
       f"{ALIAS['prf_hz']/1e3:.0f} kHz — 슬롯 하나를 한 프레임으로 읽는 **슬롯율**이다"
       f"(원장의 이름 그대로 «{ALIAS['rate_is']}»). 그래서 무모호 도플러가 "
       f"**±{ALIAS['f_unamb_hz']:.0f} Hz** 뿐인데, 이 기체의 날개끝 도플러는 "
       f"**{ALIAS['f_tip_hz']:.0f} Hz** 다. 그 차이는 측정 잡음이 아니라 **접힘**으로 "
       f"나타난다 — 참 도플러 {ALIAS['f_tip_hz']:.0f} Hz 가 **{F_FOLD:.0f} Hz**, 즉 "
       "«멀어지는 블레이드» 로 읽힌다.", "",
       f"⚠ **그 {ALIAS['prf_hz']/1e3:.0f} kHz 는 SSB 버스트율이 아니다.** 상시 기준신호로 "
       f"쓸 수 있는 SSB 는 주기 {ALIAS['ssb_burst_period_ms']:.0f} ms, 즉 "
       f"{ALIAS['ssb_burst_rate_hz']:.0f} Hz 라 무모호 도플러가 "
       f"±{ALIAS['ssb_burst_rate_hz']/2:.0f} Hz 로 훨씬 좁다(7 권 절 7). 그래서 이 팔은 "
       f"5G 에 **유리한 쪽으로 낙관적**이고, 진짜 상시 SSB 로는 접힘이 더 심하다 — 원장이 "
       f"그 자리에 스스로 적어 둔 단서다 "
       f"⟨outputs/passive_two_channel.json : md_survival.nr_alias.what⟩.", "",
       "| 파형 | 슬로타임 PRF | 무모호 도플러 | 날개끝 f_tip | 접히나 |",
       "|---|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | {SPREAD[m]['prf_hz']:.0f} Hz | "
                 f"±{SPREAD[m]['prf_hz']/2:.0f} Hz | {SPREAD[m]['f_tip_hz']:.0f} Hz | "
                 f"{'**접힌다**' if SPREAD[m]['aliased'] else '아니오'} |" for m in MODES)
       + f"\n| 생존 판정에 쓴 WiFi 사슬 | {WM['prf_hz']:.0f} Hz | "
         f"±{WM['f_unamb_hz']:.0f} Hz | {ALIAS['f_tip_hz']:.0f} Hz | 아니오 |",
       "",
       f"⚠ 표의 PRF 는 **사슬이 프레임을 끊어 읽는 속도**(검출기 프레임률)다 — {SH['G1']} 행의 "
       f"{ALIAS['prf_hz']/1e3:.0f} kHz 는 5G 슬롯율이고, 상시 SSB 의 물리 반복률 "
       f"{ALIAS['ssb_burst_rate_hz']:.0f} Hz 와는 다른 양이다(바로 위 ⚠).", "",
       f"⚠ 검출용 CPI(첫 세 줄)는 세 파형 **모두** 접힌다 — 슬로타임 PRF 가 f_tip 의 두 배에 "
       "못 미친다. 그것이 검출 성능에 얹는 대가가 다음 표다.", "",
       "**마이크로도플러가 검출에 무는 값 — 톤 표적 대비**", "",
       "| 파형 | 톤 표적 RD 피크 | 마이크로도플러 표적 | 확산 손실 |",
       "|---|---|---|---|",
       "\n".join(f"| {LBL[m]} | {SPREAD[m]['peak_tone_db']:.2f} dB | "
                 f"{SPREAD[m]['peak_md_db']:.2f} dB | "
                 f"**{SPREAD[m]['spreading_loss_db']:.2f} dB** |" for m in MODES),
       "",
       f"같은 평균전력으로 정규화한 표적을 톤에서 로터 변조로 갈아끼우면 RD 피크가 "
       f"{SPREAD_LO:.1f}~{SPREAD_HI:.1f} dB 내려간다 — 로터가 표적 에너지를 도플러축으로 "
       "흩는 대가이고, PRF 가 낮으면 접힘이 거기 겹친다. 원장의 정의 그대로 — "
       f"«{SPREAD['W1']['what']}»", "",
       "⚠ **이 절의 마이크로도플러 원장은 모노스태틱이다.** "
       f"`{MDL['path']}` ({MDL['name']} · 방위 {MDL['az_deg']:.0f}° · 앙각 "
       f"{MDL['el_deg']:.0f}° · 반송파 {MDL['fc_hz']/1e9:.1f} GHz · PRF "
       f"{MDL['prf_hz']:.0f} Hz)를 바이스태틱 사슬의 표적 복소변조로 **재사용**했다. "
       "[6 권 5 편](06_5_bistatic.ipynb)이 보인 대로 바이스태틱이 되면 도플러축이 이등분선의 "
       "수평 성분만큼 눌리므로 이것은 **기하 근사**다. 깨끗한 바이스태틱 마이크로도플러 원장이 "
       f"없는 이유는 절 6 의 {OP_BIST}번 항목에 있다. ⚠ 게다가 조명 반송파가 이 원장의 "
       f"{MDL['fc_hz']/1e9:.1f} GHz 와 같은 팔은 세 팔 중 {SH['G1']} 하나뿐이다 — 도플러축은 "
       f"**원장의 반송파 기준**으로 읽어야 한다(절 6 의 가정 {AS_MD}번이 그중 {SH['W1']} 의 "
       "축척을 적어 두었다). 표적의 병진 도플러 f_d 도 세 팔 모두 그 반송파 하나로 계산된 "
       "값이다(가정 2) — 팔마다 실제 반송파로 다시 잡지 않았다.", "",
       GRID_PENDING),

    md("## 절 6. 무엇을 못 말하나", "",
       "아래 두 목록은 원장(`outputs/passive_two_channel.json`)의 `assumptions` 와 "
       "`open_problems` 를 **그대로** 옮긴 것이다. 줄이지도 부드럽게 고치지도 않는다.", "",
       f"### 딛고 선 가정 ({len(ASSUM)}건)", "",
       "\n".join(f"{i+1}. {s}" for i, s in enumerate(ASSUM)), "",
       f"### 미해결 ({len(OPEN)}건)", "",
       "\n".join(f"{i+1}. {s}" for i, s in enumerate(OPEN)), "",
       "⭐ 위 두 목록에 나오는 `report12` 는 원장이 쓰던 옛 편 번호이고, 현재 편성에서는 "
       "**10 권 «결과»**(`10_results.ipynb`)다 — 헤드라인 검출 수치가 사는 권이다.", "",
       "⭐ 이 중 결론을 **바꿀 수 있는** 것은 셋이다 — 어느 결론을 바꾸는지까지 적는다.", "",
       f"- **{OP_DECIM}번 → 이 편의 5G 수치 전부.** {SH['G1']} 의 천장이 처리 규약의 "
       "산물이라면, 기준신호 대역으로 여파·데시메이션한 뒤의 값은 여기 수치보다 나을 수 있다. "
       "**얼마나 나은지는 아직 안 쟀다.** 그래서 이 편의 5G 수치는 «지금 우리 하우스 형상이 "
       "내는 값» 이지 «5G SSB 가 낼 수 있는 값» 이 아니다.",
       f"- **{OP_DTR}번 → 손실의 절대 크기.** 손실 수치가 DTR 에 강하게 의존한다. 헤드라인 "
       f"{GEO['dtr_db']:.1f} dB 는 감시안테나 등방이라는 최악값이고, 절 2 끝의 민감도 표가 "
       "그 기울기다.",
       f"- **{OP_BIST}번 → 절 5 의 «빗살이 남는다».** 그 판정은 **모노스태틱** 원장을 "
       "바이스태틱 사슬의 표적 변조로 재사용해 얻은 것이다. 깨끗한 바이스태틱 원장에서는 "
       "날개끝 도플러가 이등분선만큼 눌리므로 띠의 위치도 선 세기도 달라질 수 있다."),

    md("## 절 7. 이 편이 서 있는 자리", "",
       "**세 문장으로**", "",
       f"1. 기준채널 품질이 패시브 검출을 정하는 **문턱 파라미터**이고, 그 문턱은 "
       f"ρ_ref ≈ DTR/2 = {RHO_HALF_DTR:.1f} dB 근처에 있다 — {SH['W1']}·{SH['L1']} 의 실측 "
       f"요구치 {REQ_WL_LO:.1f}~{REQ_WL_HI:.1f} dB. ⚠ {SH['G1']} 은 손실 곡선이 천장에 눌려 "
       "«3 dB 손실» 이라는 기준 자체가 성립하지 않아 이 범위에서 뺐다.",
       f"2. 그 문턱을 넘는 방법은 **안테나**다 — 감시안테나 대비 기준안테나 이득 "
       f"{GAIN_WL_LO:.1f}~{GAIN_WL_HI:.1f} dB, 또는 감시안테나 쪽에서 DTR 을 깎는 것. "
       "⚠ 그 이득 값은 «두 안테나가 똑같다» 는 퇴화된 기준점에서 잰 **차이**이지 장비 "
       "사양이 아니다.",
       f"3. Pd 가 {PD_B['refSNR+10dB']:.2f} 인 **한 칸**에서 빗살 선은 아직 배경보다 "
       f"{FL['refSNR+10dB']:.1f} dB 위에 있었다 — 다만 이상 팔의 {FL['ideal']:.1f} dB 에서 "
       f"{FL_DROP_TOT:.1f} dB 를 잃은 뒤이고, {SH['W1']} 한 파형 · 날개끝이 안 접히는 별도 "
       "슬로타임 사슬 · 표적 거리빈을 아는 조건에서다. ⛔ 이것은 «검출이 실패해도 분류는 "
       "된다» 는 뜻이 **아니다**(분류기를 돌린 적이 없다). 5G 상시 기준신호에서는 날개끝이 "
       "아예 접힌다.", "",
       "**다음에 할 일 — 상류부터**", "",
       "| 순서 | 무엇 | 왜 지금이 아니라 다음인가 |",
       "|---|---|---|",
       "| ① | 기준신호 대역으로 **여파·데시메이션**한 뒤 G1 의 천장을 다시 잰다 | 이 편의 "
       "G1 수치 전부와 경험식의 적용범위가 여기에 매달려 있다. 가장 상류다 |",
       "| ② | 오염된 기준신호 형상에서 **CFAR 명목 Pfa 를 다시 교정**한다 | 지금은 팔마다 "
       "경험 Pfa 가 달라 팔 간 Pd 비교가 반쪽이다(8 권 절 3 의 절차를 그대로 쓰면 된다) |",
       "| ③ | 깨끗한 **바이스태틱 마이크로도플러 원장**을 만든다 | 절 5 의 모노스태틱 재사용 "
       "근사를 없앤다. 광선 팔의 광대역 슬로타임 바닥이 먼저 풀려야 한다(6 권 5 편 절 2) |",
       "| ④ | 감시채널 다중경로를 **둘째 축**으로 연다 | 단일축 규칙 때문에 이 편에서 뺐다. "
       "표적경유 유령과 함께 봐야 한다 |",
       "| ⑤ | sliding **ECA-S** 로 갈아 끼워 저도플러 표적 보존을 잰다 | 사슬을 바꾸는 "
       "일이라 이 편의 «사슬 고정» 설계와 충돌한다. 별도 판이 필요하다 |",
       f"| ⑥ | 실제 2채널 **CAF 승격** — 기준채널 프레임마다 독립인 템플릿 | 절 6 의 "
       f"{OP_TPL}번 항목. E1c 가 «헤드라인 결론은 안 바뀐다» 를 보였으므로 급하지 않다 |",
       "",
       "**11 권으로 넘기는 것 하나** — 이 편이 준 기준안테나 이득 요구치는 퇴화된 기준점 대비 "
       "**차이값**이지 장비 사양이 아니다. 그것을 실제 수신 프론트엔드의 사양으로 옮기는 일은 "
       "그 권에서 닫힌다."),

    md("## 부록 — 그림을 만든 설정 전부", "",
       "그림에는 설정 수치를 안 적는다(하우스 규약). 여기가 그 수치들의 자리다.", "",
       "**검출 실험 (그림 1·2)**", "",
       "| 항목 | 값 |",
       "|---|---|",
       f"| CPI | 파형별 M×b (절 1 표) · T_CPI {min(E1[m]['T_cpi_ms'] for m in MODES):.0f}~"
       f"{max(E1[m]['T_cpi_ms'] for m in MODES):.0f} ms |",
       f"| 거리빈 수 · ECA 탭 · 릿지 | {CFG['n_range']} · {CFG['n_taps']} · "
       f"{CFG['ridge_rel']:.0e} (상대) |",
       f"| CFAR | 경험 목표 Pfa {CFG['pfa_target_emp']:.0e} · 명목값은 "
       f"`pfa_nominal_for` 교정표 · 0-도플러 가드 폭 {CFG['guard_width']} |",
       "| 파형별 명목 Pfa | " + " · ".join(f"{SH[m]} {E1[m]['pfa_nominal']:.2e}"
                                         for m in MODES) + " |",
       f"| σ² 교정 | 팔 A 출력 SINR = {CFG['target_sinr_ideal_db']:.0f} dB 목표 "
       f"(G1 은 천장 {G1_CEIL:.1f} dB 때문에 {G1_TGT:.2f} dB) |",
       f"| 정적 클러터 | {len(CFG['clutter_ratio'])} 개 (지연, 진폭비) — 이 하네스에서는 "
       "ECA 가 정확히 소거하는 죽은 파라미터다 |",
       f"| 다중경로 지연 | {', '.join(f'{x:.1f}' for x in CFG['mp_delays_ns'])} ns "
       "(첫 값만 챔버 바닥반사 실측, 나머지는 선언된 가정) |",
       f"| 트라이얼 — 절 2 사다리(E1) | Pd 팔당 {min(K_E1)}~{max(K_E1)} · "
       f"Pfa 팔당 {min(KPFA_E1)}~{max(KPFA_E1)} |",
       f"| 트라이얼 — 절 4 분해(E1c) · 절 5 검출(E1b) · DTR 스윕 | Pd 팔당 "
       f"{min(K_REST)}~{max(K_REST)} · Pfa 팔당 {min(KPFA_REST)}~{max(KPFA_REST)} |",
       "",
       f"⚠ **트라이얼 수가 실험마다 다르다**(전체 Pd {min(K_ALL)}~{max(K_ALL)} · "
       f"Pfa {min(KPFA_ALL)}~{max(KPFA_ALL)}). 그림 2 와 절 5 의 Pd 는 절 2 표보다 "
       f"**적은 트라이얼**에서 나온 값이라 눈금이 성기다 — 팔당 {min(K_REST)} 트라이얼이면 "
       f"Pd 의 눈금 자체가 {1.0/min(K_REST):.2f} 다. 소수 둘째 자리는 정밀도가 아니라 "
       "표기일 뿐이고, 절 2 표와 그 두 곳의 Pd 를 나란히 읽으면 안 된다.", "",
       "**마이크로도플러 맵 (그림 3) — `src/md_mapstyle.py` 가 강제한다**", "",
       "| 항목 | WiFi 사슬 (a)~(h) | 5G 사슬 (i) |",
       "|---|---|---|",
       f"| 관측 길이 | {WM['seconds']*1e3:.0f} ms | {NM['seconds']*1e3:.0f} ms |",
       f"| 슬로타임 프레임 수 | {WM['M_tot']:,} @ {WM['prf_hz']:.0f} Hz | "
       f"{NM['M_tot']:,} @ {NM['prf_hz']:.0f} Hz |",
       f"| STFT 조각 | {WM['nper']} 표본 = {WM['nper_periods']:.2f} 블레이드 주기 | "
       f"{NM['nper']} 표본 = {NM['nper_periods']:.2f} 주기 "
       f"({'최소 표본수로 **강제**' if NM['forced_nper'] else '규약값'}) |",
       f"| hop · 시간 슬롯 | {WM['hop']} · {WM['n_slot']:,} | {NM['hop']} · {NM['n_slot']:,} |",
       f"| Δt · Δf | {WM['dt_ms']:.2f} ms · {WM['df_hz']:.1f} Hz | "
       f"{NM['dt_ms']:.2f} ms · {NM['df_hz']:.1f} Hz |",
       f"| 무모호 도플러 | ±{WM['f_unamb_hz']:.0f} Hz | ±{NM['f_unamb_hz']:.0f} Hz |",
       f"| 읽은 거리빈 | {WM['range_bin']} | {NM['range_bin']} |",
       f"| 계산 시간 | {WM['seconds_run']/60:.1f} 분 | {NM['seconds_run']/60:.1f} 분 |",
       "",
       f"⚠ {WM['pad_note']}", "",
       f"⚠ 5G 패널의 조각이 {NM['nper_periods']:.2f} 주기로 **길다** — 프레임률이 낮아 "
       f"규약값({WM['nper_periods']:.2f} 주기)으로는 조각에 표본이 남지 않는다. 그래서 "
       "(i) 는 (a)~(h) 와 **같은 시간 분해능이 아니다**. 그 패널에서 읽을 것은 무늬의 "
       "선명도가 아니라 **접힘의 위치**뿐이다.", "",
       "**표적 원장 (그림 3 의 복소변조)**", "",
       "| 항목 | 값 |",
       "|---|---|",
       f"| 원장 | `{MDL['path']}` · {MDL['generated'][:16]} |",
       f"| 기체 | {MDL['name']} · 호버 · 방위 {MDL['az_deg']:.0f}° 앙각 {MDL['el_deg']:.0f}° |",
       f"| 반송파 · PRF · 길이 | {MDL['fc_hz']/1e9:.1f} GHz · {MDL['prf_hz']:.0f} Hz · "
       f"{MDL['n']:,} 표본 = {MDL['seconds']:.1f} s = {MDL['blade_periods']:.0f} 블레이드 주기 |",
       f"| 회전수 · 플래시율 · 날개끝 | {MDL['rpm0']:.0f} rpm · {MDL['f_flash_hz']:.1f} Hz · "
       f"{MDL['f_tip_hz']:.0f} Hz |",
       f"| 로터 산포 · 흔들림 | ±{MDL['static_spread']*100:.2f} % · "
       f"{MDL['wobble_amp']*100:.2f} % @ {MDL['wobble_hz']:.1f} Hz "
       f"(프리셋 `{MDL['preset']}` — {MDL['preset_why_ko']}) |",
       "",
       f"{MDL['declared_ko']}", "",
       GRID_PENDING),

    md("## 부록 — 재현", "",
       "```bash",
       "cd sionna2",
       "# ① 실험 (CPU 다중프로세스) → outputs/passive_two_channel.{json,npz}",
       f"PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \\",
       f"    {META['script']} --stage all",
       "",
       "# ② 그림 셋",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_passive_figs.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_passive_figs2.py",
       "PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/build_passive_figs3.py",
       "",
       "# ③ 이 노트북",
       "PYTHONPATH=src ~/.venvs/py312/bin/python src/make_report11_2_two_channel.py",
       "```", "",
       "**딸린 파일**", "",
       "| 무엇 | 어디 |",
       "|---|---|",
       "| 사슬 (이 편은 **안 고친다**) | `src/passive_process.py` |",
       "| 표시 규약 | `src/md_mapstyle.py` |",
       f"| 실험 | `{META['script']}` |",
       "| 그림 | `benchmark/build_passive_figs.py` · `build_passive_figs2.py` · "
       "`build_passive_figs3.py` |",
       "| 원장 | `outputs/passive_two_channel.{json,npz}` · "
       "`outputs/figures/passive_f{1,2,3}.{png,pdf}` |",
       f"| 상속한 원장 | `{MDL['path']}` (표적 변조) · `{CFG['pfa_calibration_source']}` "
       "(CFAR 교정) |",
       "",
       "**무결성 게이트** — 그림 3 의 빌더는 그리기 전에 `.npz` 맵에서 지표를 **다시 계산**해 "
       "원장의 `md_survival` 과 1e-6 안에서 맞는지 확인하고, 원장 내부의 두 갈래"
       "(`md_survival` ↔ `E2.wifi_b1.metrics`)도 대조한다. 맵과 숫자가 다른 원장이면 그림이 "
       "거짓말을 한다.", "",
       "이 노트북의 본문 수치는 **전부** 원장에서 주입된다 — 원장이 다시 계산되면 이 빌더를 "
       "돌리는 것만으로 본문이 따라 바뀐다."),
]

nb = {"cells": cells, "metadata": {
    "kernelspec": {"display_name": "py312", "language": "python", "name": "py312"},
    "language_info": {"name": "python"}},
    "nbformat": 4, "nbformat_minor": 5}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"  ✅ {os.path.basename(OUT)} — 셀 {len(cells)}개 · 그림 {len(_EMBEDDED)}장 박아 넣음 "
      f"({', '.join(_EMBEDDED)}) · {os.path.getsize(OUT)/1e6:.1f} MB")
