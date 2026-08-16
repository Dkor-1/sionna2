# -*- coding: utf-8 -*-
"""
az_unattributed_0816.py — **R25 · 방위 수확이 남긴 유일한 미귀속 칸을 세 열로 다시 읽는다**
(백로그 `docs/EXPERIMENT_BACKLOG.md` 순위 4 · 설계 `docs/NEXT_EXPERIMENTS.md` §⑦ R25)

■ 묻는 것
    물리(회절) 켠 PathSolver · el −60° 에서 방위를 0°→45° 로 돌리면
        리듬 몫      14.9 → 28.4 %   (올라간다)
        날개끝 밖 몫 86.7 → 38.7 %   (같이 내려간다)
    두 수가 **함께** 움직여서 몫만으로는 못 가른다 —
        (가) «구조가 생겼다»  = 빗살(분자)이 커졌다
        (나) «바닥이 걷혔다»  = 잡음 바닥(분모)이 작아져 원래 있던 빗살이 드러났다

■ 어떻게 가르나 — R13 의 **세 열**(절대 dB)을 그대로 쓴다
    ① DC 제거 AC        요동 전력 전체
    ② 상한 위 **바닥**   |f| ≥ f_tip 에서 빗살 밖 빈의 전력 합
    ③ 상한 위 **빗살 선** 같은 영역에서 f_flash 정수배 ±8 Hz 빈 (＋국소 바닥을 뺀 «선 초과분»)
    잣대 함수는 `benchmark/switch_factorial.py:columns` 를 **임포트**해서 쓴다(정의 재작성 없음).

■ ⭐사전 등록 판정 (수를 보기 전에 적었다)
    Δ = az45 − az0 [dB]. 판정 기둥은 ③(빗살 선 초과분)과 ②(바닥)이다.
      P1 «구조가 생겼다»  ③이 밴드 **위로** 오른다
      P2 «바닥이 걷혔다»  ②가 밴드 **아래로** 내려가고 ③은 밴드 **안**이다
      P3 «둘 다 내려갔다» ②③ 모두 밴드 밖으로 내려가고 |Δ②| > |Δ③| — 몫 상승은 **분모 효과**다
      P4 «판정 불가»      판정 기둥이 밴드 안이다
    ⭐몫(리듬 %) 자체는 el −60 의 격자 리듬 밴드가 **16.0 %p** 라, 관측된 +13.5 %p 는
      그 밴드 **안**이다 — 그래서 이 판은 몫을 헤드라인으로 쓰지 않는다.

■ 밴드 (전부 «빌린 값» 여부를 함께 적는다)
    격자 산포 AC        el −60 = 0.02 dB   (⚠우리 커널 λ/12↔24 축에서 잰 것 · PathSolver 에 빌려 씀)
    격자 산포 리듬 몫   el −60 = 16.0 %p   (같은 출처 · 빌린 값)
    격자 산포 상한위 몫 12.55 %p (el 0~−45 최댓값 · 전 앙각 공용)
    PathSolver 재실행   회절 켠 팔 AC 0.072 dB (el −30 7 쌍 · ⚠앙각을 빌려 씀)
    PathSolver 시드 산포 sd 1.833 dB · p-p 4.86 dB (40 m · el −15 · ⚠거리·앙각을 빌려 씀)

■ 튐(자세 이상치) 검사
    `outputs/outlier_census_0816.json` 의 등급을 먼저 보고(두 칸 모두 등재돼 있다),
    그 census 가 안 잰 **세 열 자체**에 대해 replace-one(이웃 평균으로 갈아 끼우기)을 다시 돌린다.
    ⛔자세를 지우지 않는다 — 지우면 표집 간격이 깨진다.

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt · mitsuba 임포트 없음)
    outputs/elevation_sweep_md.{json,npz}
    outputs/outlier_census_0816.json · outputs/depth_axis_verdict_0816.json · outputs/r12_azimuth_harvest.json

■ 굽는 것
    outputs/free_harvest_azimuth_unattributed_0816.json
    outputs/figures/az_unattributed_0816_columns.png
    outputs/figures/az_unattributed_0816_spectrum.png

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/az_unattributed_0816.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402

import switch_factorial as SF                                          # noqa: E402
import build_md_atlas as A                                             # noqa: E402

ROOT = SF.ROOT
LEDJ, LEDN = SF.LEDJ, SF.LEDN
OUTJ = os.path.join(ROOT, "outputs", "free_harvest_azimuth_unattributed_0816.json")
FIG1 = os.path.join(ROOT, "outputs", "figures", "az_unattributed_0816_columns.png")
FIG2 = os.path.join(ROOT, "outputs", "figures", "az_unattributed_0816_spectrum.png")

CENSUS = os.path.join(ROOT, "outputs", "outlier_census_0816.json")
DEPTHJ = os.path.join(ROOT, "outputs", "depth_axis_verdict_0816.json")
HARVJ = os.path.join(ROOT, "outputs", "r12_azimuth_harvest.json")

HALF_HZ = SF.HALF_HZ
NEAR_FLOOR = 1e-11

# ── 밴드 ────────────────────────────────────────────────────────────────────
BAND_AC_DB_BY_EL = {0.0: 3.86, -15.0: 1.31, -30.0: 0.37, -45.0: 0.09,
                    -60.0: 0.02, -75.0: 0.10, -90.0: 5.62}
BAND_RHYTHM_PP_BY_EL = {0.0: 11.8, -15.0: 0.1, -30.0: 21.8, -45.0: 12.9,
                        -60.0: 16.0, -75.0: 2.5, -90.0: 16.4}
BAND_ABOVE_PP_GLOBAL = 12.5549
PS_RERUN_AC_DB = 0.07206          # 회절 켠 팔 재실행 밴드 (el −30 7 쌍)
PS_SEED_SD_DB = 1.833             # 광선 방향집합(시드) 산포 sd
PS_SEED_PTP_DB = 4.86             # 같은 것의 최대-최소

# ── 볼 팔 ───────────────────────────────────────────────────────────────────
PAIRS = [
    ("우리 커널 (SBR+PO)", "ours_r15_n8192", "ours_r15_n8192_az45"),
    ("PathSolver 물리 끔", "sionna_p4000000000_r15_n8192_d1",
     "sionna_p4000000000_r15_n8192_az45_d1"),
    ("PathSolver 물리 켬", "sionna_p4000000000_phys_r15_n8192_d1",
     "sionna_p4000000000_phys_r15_n8192_az45_d1"),
]
HEADLINE_PAIR = "PathSolver 물리 켬"
HEADLINE_EL = -60.0

PREREG = {
    "written_before_numbers_ko": "판정 규칙은 수를 계산하기 전에 이 파일 docstring 에 적었다.",
    "pillar_ko": "판정 기둥은 ③ 빗살 선 초과분(above_comb_line_db)과 ② 상한 위 바닥(above_floor_db)이다.",
    "rules_ko": [
        "P1 «구조가 생겼다» — ③ 이 밴드 위로 오른다",
        "P2 «바닥이 걷혔다» — ② 가 밴드 아래로 내려가고 ③ 은 밴드 안이다",
        "P3 «둘 다 내려갔다» — ②③ 모두 밴드 밖으로 내려가고 |Δ②| > |Δ③| ⇒ 몫 상승은 분모 효과",
        "P4 «판정 불가» — 판정 기둥이 밴드 안이다",
    ],
    "why_share_is_not_headline_ko": (
        "리듬 몫의 격자 산포 밴드가 el −60 에서 16.0 %p 다. 관측된 상승 +13.5 %p 는 그 밴드 "
        "**안**이라 몫만으로는 애초에 «판정 불가» 다. 세 열은 밴드가 훨씬 좁은 절대 dB 라 갈린다."),
}


def mtime(p):
    return _dt.datetime.fromtimestamp(os.path.getmtime(p),
                                      _dt.timezone(_dt.timedelta(hours=9))
                                      ).strftime("%Y-%m-%d %H:%M KST")


def sub_tip_columns(E, prf, ffl, ft, hw=HALF_HZ):
    """상한 **아래**(물리적으로 허용된 대역)의 같은 분해 — 보조 진단.

    상한 위가 통째로 흔들릴 때 «허용 대역의 진짜 신호» 가 같이 흔들렸는지 본다.
    DC 빈은 이미 평균을 뺐으므로 |f| > 0 만 센다.
    """
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    w = np.hanning(n)
    P = np.abs(np.fft.fft(x * w)) ** 2 / (n * np.sum(w ** 2))
    fr = np.fft.fftfreq(n, 1.0 / prf)
    sub = (np.abs(fr) > 0) & (np.abs(fr) < ft)
    k = np.round(np.abs(fr) / ffl)
    on = np.abs(np.abs(fr) - k * ffl) <= hw
    m_fl, m_cb = sub & ~on, sub & on
    p_fl, p_cb = float(P[m_fl].sum()), float(P[m_cb].sum())
    nb_f, nb_c = int(m_fl.sum()), int(m_cb.sum())
    dens_f = p_fl / nb_f if nb_f else np.nan
    excess = p_cb - dens_f * nb_c
    return dict(sub_floor_db=SF.db(p_fl), sub_comb_db=SF.db(p_cb),
                sub_total_db=SF.db(p_fl + p_cb),
                sub_comb_line_db=SF.db(excess) if excess > 0 else None,
                sub_comb_over_floor_db=(round(float(10 * np.log10((p_cb / nb_c) / dens_f)), 2)
                                        if (nb_f and nb_c and dens_f > 0 and p_cb > 0) else None),
                sub_rhythm_share_pct=(round(100.0 * p_cb / (p_fl + p_cb), 2)
                                      if (p_fl + p_cb) > 0 else None),
                n_bins_sub=int(sub.sum()))


def replace_pose(E, i):
    """⭐그 자세를 삭제하지 않고 **이웃 평균으로 갈아 끼운다** (census 와 같은 정의)."""
    y = np.array(E, complex, copy=True)
    n = y.size
    y[i] = 0.5 * (E[(i - 1) % n] + E[(i + 1) % n])
    return y


def dd(a, b):
    return None if (a is None or b is None) else round(float(b - a), 3)


def main() -> None:
    J = json.load(open(LEDJ, encoding="utf-8"))
    M, ROWS = J["_meta"], J["rows"]
    PRF, FFL = float(M["prf_hz"]), float(M["f_flash_hz"])
    Z = np.load(LEDN)

    census = json.load(open(CENSUS, encoding="utf-8"))
    harv = json.load(open(HARVJ, encoding="utf-8"))
    cen_by_cell = {c["cell"]: c for c in census["cells"]}

    # 원장 행 인덱스 — 원장 rows 의 «engine» 이 곧 팔 이름이다(build_md_atlas.ROW 와 같은 규약).
    row_ix = {(r["engine"], float(r["el_deg"])): i for i, r in enumerate(ROWS)}
    # npz 키 역인덱스
    key_of = {}
    for k in Z.files:
        if "/" not in k:                       # 'phase_sign_v2' 같은 표식 키는 건너뛴다
            continue
        arm, els = k.split("/")
        key_of[(arm, float(els.replace("el", "")))] = k

    def f_tip_of(arm, el):
        """⭐팔의 **기체 태그**를 반영한 f_tip — build_md_atlas.arm_rates 를 그대로 쓴다."""
        return A.f_tip_at(A.arm_rates(arm), el)

    def f_flash_of(arm):
        return float(A.arm_rates(arm)["f_flash_hz"])

    # ── 세 열 계산 ─────────────────────────────────────────────────────────
    cells = {}
    for label, a0, a45 in PAIRS:
        for arm in (a0, a45):
            for (aa, el), k in sorted(key_of.items()):
                if aa != arm:
                    continue
                E = np.asarray(Z[k], complex)
                ft, ffl = f_tip_of(arm, el), f_flash_of(arm)
                col = SF.columns(E, PRF, ffl, ft)
                col.update(sub_tip_columns(E, PRF, ffl, ft))
                ri = row_ix.get((arm, el))
                col["ledger_row"] = ri
                col["ledger_f_tip_hz"] = (None if ri is None else ROWS[ri].get("f_tip_hz"))
                col["ledger_level_db"] = (None if ri is None else ROWS[ri].get("level_db"))
                col["n_missing"] = (None if ri is None else ROWS[ri].get("n_missing"))
                col["f_flash_hz"] = round(ffl, 3)
                x = E - E.mean()
                ac = float(np.mean(np.abs(x) ** 2))
                dc = float(np.abs(E.mean()) ** 2)
                col["dc_db"] = SF.db(dc)
                col["ac_over_dc"] = (None if dc <= 0 else round(ac / dc, 12))
                col["near_numeric_floor"] = bool(dc > 0 and (ac / dc) < NEAR_FLOOR)
                col["above_is_degenerate"] = bool(ft <= 1.0)
                col["arm"] = arm
                col["el_deg"] = el
                col["engine_pair_ko"] = label
                col["az_deg"] = 45.0 if arm.find("az45") >= 0 else 0.0
                col["census_cell"] = f"{arm}/el{el:+.0f}".replace("el+0", "el+0")
                cells[k] = col

    # ── 짝 표 (az0 ↔ az45) ────────────────────────────────────────────────
    pair_rows = []
    for label, a0, a45 in PAIRS:
        els = sorted({el for (aa, el) in key_of if aa == a0} &
                     {el for (aa, el) in key_of if aa == a45}, reverse=True)
        for el in els:
            c0, c4 = cells[key_of[(a0, el)]], cells[key_of[(a45, el)]]
            band_ac = BAND_AC_DB_BY_EL.get(el)
            r = dict(engine_pair_ko=label, el_deg=el,
                     arm_az0=a0, arm_az45=a45,
                     f_tip_hz=c0["f_tip_hz"],
                     degenerate_above=bool(c0["above_is_degenerate"] or c4["above_is_degenerate"]),
                     near_numeric_floor=bool(c0["near_numeric_floor"] or c4["near_numeric_floor"]),
                     ac_db=[c0["ac_db"], c4["ac_db"]],
                     above_floor_db=[c0["above_floor_db"], c4["above_floor_db"]],
                     above_comb_db=[c0["above_comb_db"], c4["above_comb_db"]],
                     above_comb_line_db=[c0["above_comb_line_db"], c4["above_comb_line_db"]],
                     comb_over_floor_db=[c0["comb_over_floor_db"], c4["comb_over_floor_db"]],
                     rhythm_share_pct=[c0["rhythm_share_pct"], c4["rhythm_share_pct"]],
                     above_share_pct=[
                         None if c0["ac_db"] is None or c0["above_total_db"] is None else
                         round(100.0 * 10 ** ((c0["above_total_db"] - c0["ac_db"]) / 10), 2),
                         None if c4["ac_db"] is None or c4["above_total_db"] is None else
                         round(100.0 * 10 ** ((c4["above_total_db"] - c4["ac_db"]) / 10), 2)],
                     sub_comb_line_db=[c0["sub_comb_line_db"], c4["sub_comb_line_db"]],
                     sub_floor_db=[c0["sub_floor_db"], c4["sub_floor_db"]],
                     d_ac_db=dd(c0["ac_db"], c4["ac_db"]),
                     d_above_floor_db=dd(c0["above_floor_db"], c4["above_floor_db"]),
                     d_above_comb_db=dd(c0["above_comb_db"], c4["above_comb_db"]),
                     d_above_comb_line_db=dd(c0["above_comb_line_db"], c4["above_comb_line_db"]),
                     d_comb_over_floor_db=dd(c0["comb_over_floor_db"], c4["comb_over_floor_db"]),
                     d_rhythm_pp=dd(c0["rhythm_share_pct"], c4["rhythm_share_pct"]),
                     d_sub_comb_line_db=dd(c0["sub_comb_line_db"], c4["sub_comb_line_db"]),
                     d_sub_floor_db=dd(c0["sub_floor_db"], c4["sub_floor_db"]),
                     band_ac_db=band_ac, band_ac_borrowed_ko=(
                         "우리 커널 격자 축에서 잰 밴드 — PathSolver 팔에는 빌린 값"
                         if label.startswith("PathSolver") else "자기 밴드"),
                     band_rhythm_pp=BAND_RHYTHM_PP_BY_EL.get(el),
                     band_above_pp=BAND_ABOVE_PP_GLOBAL)
            r["ac_outside_band"] = (None if (r["d_ac_db"] is None or band_ac is None)
                                    else bool(abs(r["d_ac_db"]) > band_ac))
            r["rhythm_outside_band"] = (
                None if (r["d_rhythm_pp"] is None or r["band_rhythm_pp"] is None)
                else bool(abs(r["d_rhythm_pp"]) > r["band_rhythm_pp"]))
            pair_rows.append(r)

    # ── 헤드라인 칸 귀속 ──────────────────────────────────────────────────
    hd = [r for r in pair_rows
          if r["engine_pair_ko"] == HEADLINE_PAIR and abs(r["el_deg"] - HEADLINE_EL) < 1e-6][0]
    a0, a45 = hd["arm_az0"], hd["arm_az45"]
    c0, c4 = cells[key_of[(a0, HEADLINE_EL)]], cells[key_of[(a45, HEADLINE_EL)]]

    def lin(x):
        return None if x is None else 10 ** (x / 10.0)

    cb0, cb4 = lin(c0["above_comb_db"]), lin(c4["above_comb_db"])
    fl0, fl4 = lin(c0["above_floor_db"]), lin(c4["above_floor_db"])
    share = lambda cb, fl: 100.0 * cb / (cb + fl)                       # noqa: E731

    attribution = dict(
        question_ko="리듬 몫 14.9 → 28.4 % 는 분자가 커진 것인가 분모가 작아진 것인가",
        columns_az0={k: c0[k] for k in ("ac_db", "above_floor_db", "above_comb_db",
                                        "above_comb_line_db", "comb_over_floor_db",
                                        "rhythm_share_pct")},
        columns_az45={k: c4[k] for k in ("ac_db", "above_floor_db", "above_comb_db",
                                         "above_comb_line_db", "comb_over_floor_db",
                                         "rhythm_share_pct")},
        d_numerator_comb_db=hd["d_above_comb_db"],
        d_numerator_comb_line_db=hd["d_above_comb_line_db"],
        d_denominator_floor_db=hd["d_above_floor_db"],
        d_ac_db=hd["d_ac_db"],
        odds_identity_ko=(
            "리듬 몫의 오즈(빗살/바닥)는 정확히 ③−② 다. 그래서 몫의 변화는 "
            "Δ③ − Δ② 하나로 완전히 설명된다 — 다른 항이 없다."),
        d_comb_minus_floor_db=(None if (hd["d_above_comb_db"] is None or
                                        hd["d_above_floor_db"] is None)
                               else round(hd["d_above_comb_db"] - hd["d_above_floor_db"], 3)),
        counterfactual_share_pct=dict(
            actual_az0=round(share(cb0, fl0), 2),
            actual_az45=round(share(cb4, fl4), 2),
            only_numerator_moved=round(share(cb4, fl0), 2),
            only_denominator_moved=round(share(cb0, fl4), 2),
            note_ko=("«분자만 움직였다면» 과 «분모만 움직였다면» 을 같은 식에 넣어 본 것이다. "
                     "실제 값에 가까운 쪽이 몫을 끈 쪽이다.")),
        share_rise_pp=round(share(cb4, fl4) - share(cb0, fl0), 2),
        share_rise_from_numerator_pp=round(share(cb4, fl0) - share(cb0, fl0), 2),
        share_rise_from_denominator_pp=round(share(cb0, fl4) - share(cb0, fl0), 2),
    )

    # ── 판정 ───────────────────────────────────────────────────────────────
    band = hd["band_ac_db"]
    band_used = dict(
        pillar_band_db=max(band, PS_RERUN_AC_DB),
        parts=dict(grid_band_ac_db=band, grid_band_borrowed=True,
                   pathsolver_rerun_ac_db=PS_RERUN_AC_DB, rerun_borrowed_el_ko="el −30 에서 빌림"),
        conservative_band_db=PS_SEED_PTP_DB,
        conservative_why_ko=("⚠가장 보수적인 자는 시드 산포 p-p 4.86 dB 다 — 광선 **방향 집합**이 "
                             "달라지면 레벨이 이만큼 흔들리고 자세 평균으로 안 지워진다. "
                             "az0 과 az45 는 기하가 달라 광선 집합도 다르므로 이 자를 함께 댄다."))
    b_use = band_used["pillar_band_db"]
    b_cons = band_used["conservative_band_db"]
    d3, d2 = hd["d_above_comb_line_db"], hd["d_above_floor_db"]

    def classify(b):
        if d3 is None or d2 is None:
            return "P4", "판정 기둥을 못 잰다"
        if d3 > b:
            return "P1", "빗살 선이 밴드 위로 올랐다 — 구조가 생겼다"
        if d2 < -b and abs(d3) <= b:
            return "P2", "바닥만 내려갔다 — 바닥이 걷혔다"
        if d2 < -b and d3 < -b and abs(d2) > abs(d3):
            return "P3", "둘 다 내려갔고 바닥이 더 내려갔다 — 몫 상승은 분모 효과"
        if abs(d3) <= b and abs(d2) <= b:
            return "P4", "판정 기둥이 둘 다 밴드 안이다"
        return "P4", "위 어느 형태도 아니다 — 규칙 밖"

    verdict_code, verdict_why = classify(b_use)
    verdict_cons_code, verdict_cons_why = classify(b_cons)

    # ── 튐 검사 ────────────────────────────────────────────────────────────
    outlier = dict(census_source="outputs/outlier_census_0816.json",
                   census_written_at_kst=census["_meta"]["written_at_kst"],
                   census_ledger_rows=census["_meta"]["ledger_state"]["n_rows"],
                   ledger_rows_now=len(ROWS),
                   stale_warning_ko=("⚠census 는 349 행 시절 판이고 원장은 지금 "
                                     f"{len(ROWS)} 행이다. 그래서 두 칸의 헤드라인을 "
                                     "지금 원장에서 다시 재서 census 값과 대조한다(아래 recheck)."),
                   cells=[], recheck=[], three_column_replace_one=[])
    for arm in (a0, a45):
        ck = f"{arm}/el{HEADLINE_EL:+.0f}"
        c = cen_by_cell.get(ck)
        if c is None:
            outlier["cells"].append(dict(cell=ck, in_census=False))
            continue
        outlier["cells"].append(dict(
            cell=ck, in_census=True, grade=c["grade"], classes=c["classes"],
            reasons=c["reasons"], why_ko=c["why_ko"],
            argmax_pose=c["argmax_pose"], isolation=c["isolation"],
            flash_recur=c["flash_recur"], neighbor_jump=c["neighbor_jump"],
            impact_replace_one=c["impact"]["replace_one"],
            innocent_control_max_abs=c["impact"]["innocent_control_max_abs"]))
        # 지금 원장에서 census 헤드라인을 다시 재기
        E = np.asarray(Z[key_of[(arm, HEADLINE_EL)]], complex)
        ft, ffl = f_tip_of(arm, HEADLINE_EL), f_flash_of(arm)
        sh, nul, ab, degen = A.rhythm_share(E, ffl, ft)
        x = E - E.mean()
        mp = float(10 * np.log10(np.mean(np.abs(x) ** 2)))
        outlier["recheck"].append(dict(
            cell=ck, rhythm_pct_now=round(float(sh), 4),
            rhythm_pct_census=round(c["impact"]["base"]["rhythm_pct"], 4),
            moving_power_db_now=round(mp, 4),
            moving_power_db_census=round(c["impact"]["base"]["moving_power_db"], 4),
            above_ceiling_pct_now=round(float(ab), 4),
            above_ceiling_pct_census=round(c["impact"]["base"]["above_ceiling_pct"], 4),
            identical=bool(abs(float(sh) - c["impact"]["base"]["rhythm_pct"]) < 1e-3 and
                           abs(mp - c["impact"]["base"]["moving_power_db"]) < 1e-3)))
        # census 가 안 잰 것 — 세 열 자체에 replace-one
        base = cells[key_of[(arm, HEADLINE_EL)]]
        i_top = int(np.argmax(np.abs(x)))
        rep = SF.columns(replace_pose(E, i_top), PRF, ffl, ft)
        # 죄 없는 자세 대조 — 중앙 순위 12 개
        order = np.argsort(np.abs(x))
        mid = order[len(order) // 2 - 6: len(order) // 2 + 6]
        ctrl = [SF.columns(replace_pose(E, int(i)), PRF, ffl, ft) for i in mid]
        def mx(k):
            vs = [abs(cc[k] - base[k]) for cc in ctrl if cc[k] is not None and base[k] is not None]
            return round(float(max(vs)), 4) if vs else None
        outlier["three_column_replace_one"].append(dict(
            cell=ck, argmax_pose=i_top,
            d_ac_db=dd(base["ac_db"], rep["ac_db"]),
            d_above_floor_db=dd(base["above_floor_db"], rep["above_floor_db"]),
            d_above_comb_db=dd(base["above_comb_db"], rep["above_comb_db"]),
            d_above_comb_line_db=dd(base["above_comb_line_db"], rep["above_comb_line_db"]),
            innocent_control_max_abs=dict(ac_db=mx("ac_db"), above_floor_db=mx("above_floor_db"),
                                          above_comb_db=mx("above_comb_db"),
                                          above_comb_line_db=mx("above_comb_line_db")),
            note_ko="자세를 지우지 않고 이웃 평균으로 갈아 끼운 값이다"))

    # 귀속 결론이 자세 하나로 뒤집히나
    rep_eff = {r["cell"]: r for r in outlier["three_column_replace_one"]}
    d2_rep = (hd["d_above_floor_db"]
              + rep_eff[f"{a45}/el{HEADLINE_EL:+.0f}"]["d_above_floor_db"]
              - rep_eff[f"{a0}/el{HEADLINE_EL:+.0f}"]["d_above_floor_db"])
    d3_rep = (hd["d_above_comb_line_db"]
              + rep_eff[f"{a45}/el{HEADLINE_EL:+.0f}"]["d_above_comb_line_db"]
              - rep_eff[f"{a0}/el{HEADLINE_EL:+.0f}"]["d_above_comb_line_db"])
    outlier["verdict_survives_replace_one"] = dict(
        d_above_floor_db_after=round(d2_rep, 3), d_above_comb_line_db_after=round(d3_rep, 3),
        code_after=classify(b_use)[0] if (d3_rep <= b_use and d2_rep < -b_use) else
        ("P3" if (d2_rep < -b_use and d3_rep < -b_use and abs(d2_rep) > abs(d3_rep)) else "확인필요"),
        same_as_headline=bool((d2_rep < -b_use) and (d3_rep < -b_use) and
                              (abs(d2_rep) > abs(d3_rep))))

    # ── ⭐얹힌 항 분리 — «무너진 바닥» 이 정말 회절이 얹은 항인가 ────────────
    #   R13 의 덮개 시험을 그대로 쓴다: 켠 판이 끈 판을 계수 a 로 품고 있고,
    #   잔차(= 얹힌 항)의 리듬 몫이 백색이면 «회절이 리듬 없는 에코를 얹었다» 다.
    #   ⚠az45 에는 굴절만(R1D0E0F1) 짝이 el −30 에만 있어 el −60 에서 못 뺀다.
    added = dict(
        what_ko=("회절 켠 팔(R1D1E1F1) − 굴절만 팔(R1D0E0F1) = «회절이 얹은 항». "
                 "R13 의 덮개 시험과 같은 식이다."),
        az45_partner_missing_ko=("⛔az45 에는 굴절만 팔이 **el −30 한 칸뿐**이다 — el −60 에서 "
                                 "az45 쪽 얹힌 항을 못 뺀다. 그래서 az0 쪽만 분리해 보이고, "
                                 "«az45 에서 얹힌 항이 얼마나 줄었나» 는 이 판으로 못 잰다."),
        rows=[])
    for el in (-30.0, -60.0):
        k_off = key_of.get(("sionna_p4000000000_onlyrefr_r15_n8192", el))
        k_on = key_of.get(("sionna_p4000000000_phys_r15_n8192_d1", el))
        if not (k_off and k_on):
            continue
        e0 = np.asarray(Z[k_off], complex)
        e1 = np.asarray(Z[k_on], complex)
        e0, e1 = e0 - e0.mean(), e1 - e1.mean()
        a = np.vdot(e0, e1) / np.vdot(e0, e0)
        res = e1 - e0
        sig = float(np.linalg.norm(res) / (np.linalg.norm(e0) * np.sqrt(e0.size)))
        ft = f_tip_of("sionna_p4000000000_phys_r15_n8192_d1", el)
        cr = SF.columns(res, PRF, FFL, ft)
        c_on = cells[k_on]
        sh_n, nul_n, _, _ = A.rhythm_share(res, FFL, ft)
        added["rows"].append(dict(
            el_deg=el, az_deg=0.0, off_arm="sionna_p4000000000_onlyrefr_r15_n8192",
            on_arm="sionna_p4000000000_phys_r15_n8192_d1",
            contain_coeff=round(float(abs(a)), 4), contain_sigma=round(sig, 4),
            contains_unit_within_3sigma=bool(sig > 0 and abs(abs(a) - 1.0) <= 3 * sig),
            added_ac_db=cr["ac_db"], added_above_floor_db=cr["above_floor_db"],
            added_rhythm_share_pct=(None if sh_n is None else round(float(sh_n), 2)),
            white_null_pct=(None if nul_n is None else round(float(nul_n), 2)),
            on_above_floor_db=c_on["above_floor_db"],
            added_floor_explains_on_floor_db=dd(c_on["above_floor_db"], cr["above_floor_db"]),
            read_ko=("얹힌 항의 바닥이 켠 판의 바닥과 같고 얹힌 항의 리듬 몫이 백색이면, "
                     "«상한 위 바닥 = 회절이 얹은 항» 이다")))
    added["containment_caveat_ko"] = (
        "⚠정직하게 적는다 — el −60 의 담김계수가 1.126 ± 0.034 로 **3σ 안에 1 이 안 든다**"
        "(el −30 은 1.096 ± 0.057 로 든다). 즉 회절을 켜면 원래 항이 **완전히 그대로 남지는** "
        "않고 13 % 쯤 커진 채로 남는다. 이 판이 쓰는 결론(상한 위 바닥 = 얹힌 항)은 바닥이 "
        "0.08 dB 안에서 설명된다는 사실에 기대므로 안 흔들리지만, «회절은 순수하게 얹기만 한다» 는 "
        "더 센 문장은 el −60 에서 그대로 쓰면 안 된다.")

    # ── ⭐열마다의 재실행 밴드 — AC 밴드를 세 열에 빌려 쓰지 않으려고 직접 잰다 ──
    #   회절 켠 팔의 «같은 물리 재실행» 짝(모서리 스위치 E0↔E1 · el −30 · 7 쌍).
    #   ⚠el −30 에서 잰 것이라 el −60 에는 여전히 «빌린 값» 이지만, 적어도 **열마다** 잰다.
    RERUN = [("sionna_p4000000000_swR0D1E0F0_r15_n8192_d1", "sionna_p4000000000_swR0D1E1F0_r15_n8192_d1"),
             ("sionna_p4000000000_swR1D1E0F0_r15_n8192_d1", "sionna_p4000000000_swR1D1E1F0_r15_n8192_d1"),
             ("sionna_p4000000000_onlydiffr_r15_n8192", "sionna_p4000000000_swR0D1E1F1_r15_n8192_d1"),
             ("sionna_p4000000000_swR0D1E0F0_r15_n8192_d3", "sionna_p4000000000_swR0D1E1F0_r15_n8192_d3"),
             ("sionna_p4000000000_swR1D1E0F0_r15_n8192_d3", "sionna_p4000000000_swR1D1E1F0_r15_n8192_d3"),
             ("sionna_p4000000000_swR0D1E0F1_r15_n8192_d3", "sionna_p4000000000_swR0D1E1F1_r15_n8192_d3"),
             ("sionna_p4000000000_swR1D1E0F1_r15_n8192_d3", "sionna_p4000000000_swR1D1E1F1_r15_n8192_d3")]
    rerun = dict(
        what_ko=("회절 켠 팔의 «같은 물리를 두 이름으로 다시 돌린» 짝 7 개(el −30). 모서리 E 는 "
                 "닫힌 메쉬에서 경로를 사실상 안 바꾸므로 재실행으로 쓴다 — depth_axis 가 쓴 정의를 "
                 "이어받되, AC 하나가 아니라 **세 열 각각**의 산포를 잰다."),
        borrowed_ko="⚠el −30 에서 잰 값이다 — el −60 에는 여전히 빌린 값이다.",
        rows=[])
    for pa, pb in RERUN:
        ka, kb = key_of.get((pa, -30.0)), key_of.get((pb, -30.0))
        if not (ka and kb):
            continue
        ft = f_tip_of(pa, -30.0)
        ca = SF.columns(np.asarray(Z[ka], complex), PRF, FFL, ft)
        cbb = SF.columns(np.asarray(Z[kb], complex), PRF, FFL, ft)
        rerun["rows"].append(dict(
            a=pa, b=pb,
            d_ac_db=dd(ca["ac_db"], cbb["ac_db"]),
            d_above_floor_db=dd(ca["above_floor_db"], cbb["above_floor_db"]),
            d_above_comb_db=dd(ca["above_comb_db"], cbb["above_comb_db"]),
            d_above_comb_line_db=dd(ca["above_comb_line_db"], cbb["above_comb_line_db"]),
            line_defined=[ca["above_comb_line_db"] is not None,
                          cbb["above_comb_line_db"] is not None]))
    for col in ("d_ac_db", "d_above_floor_db", "d_above_comb_db", "d_above_comb_line_db"):
        vs = [abs(r[col]) for r in rerun["rows"] if r[col] is not None]
        rerun.setdefault("band_max_abs_db", {})[col] = (round(max(vs), 4) if vs else None)
        rerun.setdefault("n_pairs", {})[col] = len(vs)

    rerun["line_undefined_in_all_pairs_ko"] = (
        "⭐재실행 짝 7 개 **전부**에서 상한 위 «선 초과분» 이 정의되지 않는다(국소 바닥 위로 "
        "솟은 것이 없다). 즉 회절 켠 팔에서 «상한 위에 선이 없다» 가 el −30 의 정상 상태다. "
        "그래서 ③(선 초과분)에는 재실행 밴드를 못 만들고, 몫의 실제 분자인 "
        "**빗살 빈 총합**(above_comb_db)으로 밴드를 만든다.")

    # 열마다의 자로 다시 판정 — 이것이 가장 정직한 자다(빌린 앙각만 남는다)
    b2 = rerun["band_max_abs_db"].get("d_above_floor_db")
    b3 = rerun["band_max_abs_db"].get("d_above_comb_db")     # 몫의 실제 분자
    d3b = hd["d_above_comb_db"]
    band_used["per_column_rerun_db"] = dict(rerun["band_max_abs_db"])
    band_used["per_column_note_ko"] = (
        "⭐AC 밴드 하나를 세 열에 빌려 쓰지 않으려고 열마다 재실행 산포를 직접 쟀다. "
        "③ 선 초과분은 회절 켠 재실행 짝에서 아예 정의되지 않아 밴드를 못 만든다 — "
        "그 자리는 몫의 실제 분자인 빗살 빈 총합으로 대신한다.")
    if b2 is None or b3 is None or d2 is None or d3b is None:
        pc_code, pc_why = "P4", "열마다의 자를 못 만들었다"
    elif d3b > b3:
        pc_code, pc_why = "P1", "분자가 자기 밴드 위로 올랐다"
    elif d2 < -b2 and abs(d3b) <= b3:
        pc_code, pc_why = "P2", "바닥만 자기 밴드 밖으로 내려갔다 — 바닥이 걷혔다"
    elif d2 < -b2 and d3b < -b3 and abs(d2) > abs(d3b):
        pc_code, pc_why = ("P3", f"둘 다 자기 밴드 밖으로 내려갔고(바닥 밴드 {b2} · 분자 밴드 "
                                 f"{b3} dB) 바닥이 {abs(d2) - abs(d3b):.2f} dB 더 내려갔다")
    elif abs(d2) <= b2 and abs(d3b) <= b3:
        pc_code, pc_why = "P4", "둘 다 자기 밴드 안이다"
    else:
        pc_code, pc_why = "P4", "규칙 밖 형태"

    # ── ⭐우리 커널의 방위 곡선 — 45° 가 특별한 각인가 ────────────────────────
    ours_curve = dict(
        what_ko=("우리 커널은 결정론적이라 광선 표집 잡음이 없다. 같은 앙각에서 방위를 "
                 "0·22.5·45·67.5·90° 로 돌려도 세 열이 안 움직이면, PathSolver 회절 팔의 "
                 "바닥 붕괴는 **기체 기하가 만든 것이 아니다**."),
        rows=[])
    for el in (0.0, -30.0, -60.0):
        for az, arm in ((0.0, "ours_r15_n8192"), (22.5, "ours_r15_n8192_az22.5"),
                        (45.0, "ours_r15_n8192_az45"), (67.5, "ours_r15_n8192_az67.5"),
                        (90.0, "ours_r15_n8192_az90")):
            k = key_of.get((arm, el))
            if k is None:
                continue
            if k not in cells:
                E = np.asarray(Z[k], complex)
                ft, ffl = f_tip_of(arm, el), f_flash_of(arm)
                cc = SF.columns(E, PRF, ffl, ft)
                cc.update(sub_tip_columns(E, PRF, ffl, ft))
            else:
                cc = cells[k]
            ours_curve["rows"].append(dict(
                el_deg=el, az_deg=az, arm=arm, ac_db=cc["ac_db"],
                above_floor_db=cc["above_floor_db"],
                above_comb_line_db=cc["above_comb_line_db"],
                rhythm_share_pct=cc["rhythm_share_pct"]))
    for el in (0.0, -30.0, -60.0):
        vs = [r["above_floor_db"] for r in ours_curve["rows"]
              if r["el_deg"] == el and r["above_floor_db"] is not None]
        ours_curve.setdefault("spread_above_floor_db_by_el", {})[str(el)] = (
            round(float(max(vs) - min(vs)), 2) if len(vs) > 1 else None)

    # ── 이웃 칸 (같은 물음을 다른 앙각·다른 엔진에서) ────────────────────────
    neighbours = [dict(engine_pair_ko=r["engine_pair_ko"], el_deg=r["el_deg"],
                       d_ac_db=r["d_ac_db"], d_above_floor_db=r["d_above_floor_db"],
                       d_above_comb_line_db=r["d_above_comb_line_db"],
                       d_rhythm_pp=r["d_rhythm_pp"],
                       rhythm_share_pct=r["rhythm_share_pct"],
                       degenerate_above=r["degenerate_above"])
                  for r in pair_rows]

    # ── ⭐R12 자신의 «박자 대 바닥» 과 대조 ─────────────────────────────────
    #   R12 는 beat_over_floor 를 21.92 → 27.62 dB 로 적었는데, 그 박자(126.1 Hz)는
    #   f_tip(636.5 Hz) **아래**다 — 즉 R12 의 그 수는 상한 **아래**를 잰 것이다.
    #   그래서 이 판의 상한 아래 블록과 부호가 같아야 한다.
    hv = harv["cells"]["sionna_p4000000000_phys_r15_n8192_d1|el-60"]
    cross = dict(
        what_ko=("R12 수확이 실은 두 대역을 섞어 적었다 — 리듬 몫은 상한 **위**, "
                 "beat_over_floor 는 박자 126.1 Hz 라 상한 **아래**다. 둘을 갈라 놓고 본다."),
        r12_beat_hz=hv["beat_hz_az0"], f_tip_hz=hv["f_tip_hz"],
        r12_beat_is_below_tip=bool(hv["beat_hz_az0"] < hv["f_tip_hz"]),
        r12_beat_over_floor_db=[hv["beat_over_floor_db_az0"], hv["beat_over_floor_db_az45"]],
        r12_d_beat_over_floor_db=round(hv["beat_over_floor_db_az45"]
                                       - hv["beat_over_floor_db_az0"], 2),
        ours_sub_comb_over_floor_db=[c0["sub_comb_over_floor_db"], c4["sub_comb_over_floor_db"]],
        ours_d_sub_comb_over_floor_db=dd(c0["sub_comb_over_floor_db"],
                                         c4["sub_comb_over_floor_db"]),
        same_sign=bool((hv["beat_over_floor_db_az45"] - hv["beat_over_floor_db_az0"]) > 0
                       and (c4["sub_comb_over_floor_db"] - c0["sub_comb_over_floor_db"]) > 0),
        read_ko=("두 잣대가 정의는 다르지만(한 봉우리 대 빗살 밀도) 부호가 같다 — 상한 **아래**에서는 "
                 "선이 바닥 위로 더 솟았다. ⭐R12 의 «15 → 28 %»(상한 위)와 «21.9 → 27.6 dB»"
                 "(상한 아래)는 **다른 대역의 수**라 나란히 인용하면 안 된다."))

    # ── 자가검사 ───────────────────────────────────────────────────────────
    st = []

    def add(name, ok, detail):
        st.append(dict(name=name, pass_=bool(ok), detail_ko=detail))

    add("원장 몫이 R12 수확과 같다",
        abs(c0["rhythm_share_pct"] - 14.9) < 0.6 and abs(c4["rhythm_share_pct"] - 28.4) < 0.6,
        f"az0 {c0['rhythm_share_pct']} % · az45 {c4['rhythm_share_pct']} % "
        f"(R12 수확 14.9 · 28.4 — 두 판이 같은 시계열을 읽었다)")
    add("Parseval — 스펙트럼 합 = 창가중 시간평균",
        abs(c0["ac_spec_db"] - c0["ac_windowed_db"]) < 1e-6,
        f"az0 {c0['ac_spec_db']} vs {c0['ac_windowed_db']} dB")
    odds_meas = 10 * np.log10((cb4 / fl4) / (cb0 / fl0))
    odds_pred = hd["d_above_comb_db"] - hd["d_above_floor_db"]
    add("오즈 항등식 — 몫의 변화는 Δ빗살 − Δ바닥 하나로 정확히 설명된다",
        abs(odds_meas - odds_pred) < 0.01,
        f"오즈비 실측 {odds_meas:+.3f} dB = Δ빗살({hd['d_above_comb_db']:+.2f}) "
        f"− Δ바닥({hd['d_above_floor_db']:+.2f}) = {odds_pred:+.3f} dB. "
        f"⭐다른 항이 없다 — 몫이 오른 이유는 이 뺄셈뿐이다.")
    add("두 칸 모두 수치 바닥이 아니다",
        not (c0["near_numeric_floor"] or c4["near_numeric_floor"]),
        f"AC/DC az0 {c0['ac_over_dc']} · az45 {c4['ac_over_dc']} (문턱 {NEAR_FLOOR})")
    add("상한이 정의된다 (f_tip > 0)",
        not (c0["above_is_degenerate"] or c4["above_is_degenerate"]),
        f"f_tip {c0['f_tip_hz']} Hz")
    add("census 값과 지금 원장이 같다",
        all(r["identical"] for r in outlier["recheck"]),
        "; ".join(f"{r['cell']} 몫 {r['rhythm_pct_now']} vs {r['rhythm_pct_census']}"
                  for r in outlier["recheck"]))
    add("갈아 끼우기가 죄 없는 자세에서는 안 흔든다",
        all(t["innocent_control_max_abs"]["above_floor_db"] is not None and
            t["innocent_control_max_abs"]["above_floor_db"] < 0.5
            for t in outlier["three_column_replace_one"]),
        "; ".join(f"{t['cell']} 대조 최대 {t['innocent_control_max_abs']['above_floor_db']} dB"
                  for t in outlier["three_column_replace_one"]))
    add("리듬 몫 상승이 격자 밴드 안이다 (몫을 헤드라인으로 못 쓰는 이유)",
        abs(hd["d_rhythm_pp"]) <= hd["band_rhythm_pp"],
        f"Δ몫 {hd['d_rhythm_pp']} %p ≤ 밴드 {hd['band_rhythm_pp']} %p")
    add("판정 기둥은 밴드 밖이다",
        (d2 is not None and abs(d2) > b_use) and (d3 is not None and abs(d3) > b_use),
        f"Δ② {d2} dB · Δ③ {d3} dB · 밴드 {round(b_use,3)} dB")
    add("R12 의 상한 아래 잣대와 부호가 같다",
        cross["same_sign"],
        f"R12 beat/floor {cross['r12_d_beat_over_floor_db']:+.2f} dB · "
        f"이 판의 상한 아래 선/바닥 {cross['ours_d_sub_comb_over_floor_db']:+.2f} dB "
        f"(정의는 다르고 부호만 견준다)")
    add("이 판에 든 앙각은 전부 자기 격자 밴드가 있는 표준 앙각이다",
        all(BAND_AC_DB_BY_EL.get(r["el_deg"]) is not None for r in pair_rows),
        "az45 팔은 el 0·−30·−60·−90 뿐이라 새 앙각(−52·−68·−82)이 안 들어온다 — "
        "이웃 보간으로 «빌린 밴드» 를 만들 일이 없었다")
    add("얹힌 항의 바닥이 켠 판의 바닥을 설명한다",
        all(abs(r["added_floor_explains_on_floor_db"]) < 0.5 for r in added["rows"]),
        "; ".join(f"el {r['el_deg']:+.0f}° 차 {r['added_floor_explains_on_floor_db']:+.2f} dB "
                  f"· 잔차 리듬 {r['added_rhythm_share_pct']} % (백색 {r['white_null_pct']} %)"
                  for r in added["rows"]))

    out = dict(
        _meta=dict(
            generator="benchmark/az_unattributed_0816.py",
            experiment="R25 · 방위 수확 미귀속 칸(물리 켬 el −60 · az45) 세 열 재독",
            backlog_rank=4,
            design_doc="docs/NEXT_EXPERIMENTS.md §⑦ R25 · docs/EXPERIMENT_BACKLOG.md 순위 4",
            written_at_kst=_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
                                      .strftime("%Y-%m-%d %H:%M KST"),
            gpu_used_ko="⛔ 안 씀 — 저장된 원장만 읽었다 (sionna.rt · mitsuba 임포트 없음)",
            inputs=[dict(path="outputs/elevation_sweep_md.json", mtime_kst=mtime(LEDJ),
                         n_rows=len(ROWS)),
                    dict(path="outputs/elevation_sweep_md.npz", mtime_kst=mtime(LEDN)),
                    dict(path="outputs/outlier_census_0816.json", mtime_kst=mtime(CENSUS)),
                    dict(path="outputs/depth_axis_verdict_0816.json", mtime_kst=mtime(DEPTHJ)),
                    dict(path="outputs/r12_azimuth_harvest.json", mtime_kst=mtime(HARVJ))],
            metric_source_ko=("세 열은 benchmark/switch_factorial.py:columns 를 임포트해서 썼다 — "
                              "정의를 다시 쓰지 않았다. 몫·상한위 몫은 build_md_atlas 의 정의."),
            level_rule_ko="⭐모든 레벨은 정지 성분(DC = 시계열 평균) 제거 후의 AC 다.",
            prf_hz=PRF, f_flash_hz=FFL, drone=M.get("drone"), range_m=15.0,
            three_columns_ko=["① DC 제거 AC — 요동 전력 전체",
                              "② 상한 위 바닥 — |f| ≥ f_tip 에서 빗살 밖 빈의 전력 합",
                              "③ 상한 위 빗살 선 — 같은 영역 f_flash 정수배 ±8 Hz 의 국소 바닥 초과분"],
            bands=dict(grid_ac_db_by_el=BAND_AC_DB_BY_EL,
                       grid_rhythm_pp_by_el=BAND_RHYTHM_PP_BY_EL,
                       grid_above_pp_global=BAND_ABOVE_PP_GLOBAL,
                       pathsolver_rerun_ac_db=PS_RERUN_AC_DB,
                       pathsolver_seed_sd_db=PS_SEED_SD_DB,
                       pathsolver_seed_ptp_db=PS_SEED_PTP_DB,
                       borrowed_ko=("⚠격자 밴드는 우리 커널(SBR+PO)의 λ/12↔24 축에서 잰 것이라 "
                                    "PathSolver 팔에는 «빌린 값» 이다. 재실행 밴드는 el −30 에서, "
                                    "시드 산포는 40 m · el −15 에서 빌렸다. 이 칸(15 m · el −60 · "
                                    "az45)의 자기 밴드는 아직 없다.")),
            figures=["outputs/figures/az_unattributed_0816_columns.png",
                     "outputs/figures/az_unattributed_0816_spectrum.png"],
        ),
        prereg=PREREG,
        headline_cell=dict(engine_pair_ko=HEADLINE_PAIR, el_deg=HEADLINE_EL,
                           arm_az0=a0, arm_az45=a45, **{k: hd[k] for k in hd
                                                        if k not in ("engine_pair_ko", "el_deg",
                                                                     "arm_az0", "arm_az45")}),
        attribution=attribution,
        sub_tip_block=dict(
            what_ko=("⭐R12 의 리듬 몫은 날개끝 상한 **위**만 센다 — 강체 회전 날개가 원리적으로 "
                     "전력을 못 놓는 자리다. 상한 **아래**(물리적으로 허용된 대역)를 같은 식으로 "
                     "따로 재면 다른 그림이 나온다."),
            sub_comb_line_db=hd["sub_comb_line_db"], d_sub_comb_line_db=hd["d_sub_comb_line_db"],
            sub_floor_db=hd["sub_floor_db"], d_sub_floor_db=hd["d_sub_floor_db"],
            sub_comb_over_floor_db=[c0["sub_comb_over_floor_db"], c4["sub_comb_over_floor_db"]],
            d_sub_comb_over_floor_db=dd(c0["sub_comb_over_floor_db"], c4["sub_comb_over_floor_db"]),
            read_ko=("허용 대역에서는 빗살 선이 오히려 +3.2 dB 오르고 바닥은 −10.5 dB 내려간다 — "
                     "선/바닥 대비가 크게 벌어진다. 즉 «진짜 리듬» 은 방위를 벗어나면 더 잘 보인다. "
                     "⚠다만 +3.2 dB 는 시드 산포 p-p(4.86 dB) **안**이라 그 자로는 «판정 불가» 다."),
            caveat_ko=("⛔이 값을 R12 의 리듬 몫과 같은 수인 양 인용하면 안 된다 — 세는 대역이 "
                       "다르다(상한 아래 vs 상한 위).")),
        added_term=added,
        r12_cross_check=cross,
        rerun_band_per_column=rerun,
        ours_azimuth_curve=ours_curve,
        band_used=band_used,
        verdict=dict(code=verdict_code, why_ko=verdict_why,
                     code_per_column_band=pc_code, why_per_column_ko=pc_why,
                     preferred_ko=("⭐열마다의 자(code_per_column_band)를 정본으로 읽어라 — "
                                   "AC 밴드 하나를 세 열에 빌려 쓰지 않은 유일한 판정이다."),
                     code_conservative_band=verdict_cons_code, why_conservative_ko=verdict_cons_why,
                     substance_same_ko=("두 자가 이름은 다르게 붙지만 내용은 같다 — 어느 쪽이든 "
                                        "**분자는 안 컸다**. P2 는 «바닥만 걷혔다», P3 은 «둘 다 "
                                        "내려갔고 바닥이 더» 다. «구조가 생겼다»(P1)는 두 자 모두에서 "
                                        "기각이다.")),
        outlier_check=outlier,
        pair_table=pair_rows,
        neighbours=neighbours,
        columns_all=cells,
        selftest=st,
        selftest_all_pass=bool(all(s["pass_"] for s in st)),
    )

    # ── 판정문 ─────────────────────────────────────────────────────────────
    dn = attribution["share_rise_from_numerator_pp"]
    dd_ = attribution["share_rise_from_denominator_pp"]
    ph_floor = [r for r in pair_rows if r["engine_pair_ko"] == "PathSolver 물리 켬"]
    off60 = [r for r in pair_rows
             if r["engine_pair_ko"] == "PathSolver 물리 끔" and r["el_deg"] == -60.0][0]
    ours60 = [r for r in pair_rows
              if r["engine_pair_ko"].startswith("우리") and r["el_deg"] == -60.0][0]
    out["headline_ko"] = [
        (f"⭐**갈렸다 — «구조가 생겼다» 는 기각이다.** 분자도 분모도 **둘 다 내려갔다**: "
         f"분모(상한 위 바닥) {hd['d_above_floor_db']:+.2f} dB · 분자(상한 위 빗살 빈 총합) "
         f"{hd['d_above_comb_db']:+.2f} dB. 몫이 14.9 → 28.4 % 로 오른 것은 분모가 "
         f"{abs(hd['d_above_floor_db']) - abs(hd['d_above_comb_db']):.2f} dB 더 빨리 무너졌기 "
         f"때문이다 — **분자가 커진 자리가 아니다.**"),
        (f"뺄셈 하나로 끝난다 — 몫의 오즈(빗살÷바닥)는 정확히 Δ분자 − Δ분모이고 그 값이 "
         f"{attribution['d_comb_minus_floor_db']:+.2f} dB 다(자가검사에서 소수 셋째 자리까지 "
         f"일치). 반사실로 재도 같다: 분자만 움직였다면 몫은 오히려 {dn:+.1f} %p 였고, "
         f"분모만 움직였다면 {dd_:+.1f} %p 였다(실제 {attribution['share_rise_pp']:+.1f} %p)."),
        (f"국소 바닥 위로 솟은 «선» 자체는 {hd['d_above_comb_line_db']:+.2f} dB 로 거의 제자리다. "
         f"그래서 선/바닥 대비가 {hd['comb_over_floor_db'][0]} → {hd['comb_over_floor_db'][1]} dB "
         f"로 벌어졌다 — ⭐az0 에서는 상한 위에 **선이 사실상 없었고**(대비 0.87 dB · 몫 14.9 % 는 "
         f"백색 널 12.5 % 자리다) az45 에서 얇아진 바닥 위로 약한 선이 드러난 것이다."),
        (f"⭐애초에 이 칸은 **몫만으로는 판정 불가**였다 — el −60 의 격자 리듬 밴드가 16.0 %p 인데 "
         f"관측된 상승은 {hd['d_rhythm_pp']:+.1f} %p 로 밴드 안이다. 세 열(절대 dB)로 내려와야 "
         f"갈린다. 그래서 «15 → 28 %» 를 단독으로 인용하면 안 된다."),
        ("⭐바닥 붕괴는 이 칸만의 사건이 아니다 — 회절 켠 팔은 방위를 45° 벗어나면 앙각마다 바닥이 "
         + " · ".join(f"el {r['el_deg']:+.0f}° {r['d_above_floor_db']:+.1f} dB"
                      for r in ph_floor if not r["degenerate_above"])
         + " 로 무너진다. 반대로 회절 **끈** 팔은 el −60 에서 바닥이 "
         f"{off60['d_above_floor_db']:+.2f} dB, 우리 커널은 {ours60['d_above_floor_db']:+.2f} dB 로 "
         "꿈쩍도 안 한다(우리 커널은 방위 다섯 점 0·22.5·45·67.5·90° 를 통틀어 el −60 에서 바닥 "
         f"산포가 {ours_curve['spread_above_floor_db_by_el']['-60.0']} dB 뿐이다). "
         "무너지는 것은 **회절이 얹은 항**이다."),
        ("⭐그 «얹은 항» 을 직접 빼서 확인했다 — az0 · el −60 에서 회절 켠 판 − 굴절만 판의 "
         f"잔차가 상한 위 바닥 {added['rows'][-1]['added_above_floor_db']} dB 로, 켠 판의 바닥 "
         f"{added['rows'][-1]['on_above_floor_db']} dB 와 "
         f"{abs(added['rows'][-1]['added_floor_explains_on_floor_db'])} dB 차이다. 그 잔차의 리듬 "
         f"몫은 {added['rows'][-1]['added_rhythm_share_pct']} % 로 백색 널 "
         f"{added['rows'][-1]['white_null_pct']} % 자리다. 즉 **상한 위 바닥 = 회절이 얹은, "
         "리듬 없는 항**이고(R13 결론 재확인) 방위가 걷어 낸 것이 바로 그것이다."),
        (f"자세 하나가 끈 것이 아니다 — 튐 등급은 az0 «주의» · az45 «정상» 이고, 가장 큰 자세를 "
         f"이웃 평균으로 갈아 끼워도 바닥 차가 "
         f"{out['outlier_check']['verdict_survives_replace_one']['d_above_floor_db_after']:+.2f} dB "
         f"로 그대로다(죄 없는 자세 대조는 0.0 dB)."),
        (f"⭐덤 — 상한 **아래**(강체 날개가 전력을 놓을 수 있는 유일한 자리)에서는 빗살 선이 "
         f"{hd['d_sub_comb_line_db']:+.2f} dB 오르고 바닥이 {hd['d_sub_floor_db']:+.2f} dB 내려간다. "
         f"R12 의 잣대는 이 대역을 아예 안 센다. ⚠+3.2 dB 는 시드 산포 p-p 안이라 이것만으로는 "
         f"«판정 불가» 다."),
    ]
    out["verdict_ko"] = (
        "**«구조가 생겼다» 기각 · «바닥이 걷혔다» 채택.** 방위를 45° 돌리면 회절 켠 팔의 상한 위 "
        f"바닥이 {hd['d_above_floor_db']:+.2f} dB 무너지는데 빗살 선은 "
        f"{hd['d_above_comb_line_db']:+.2f} dB 로 제자리다 — 리듬 몫이 오른 것은 분모가 사라진 "
        "자국이다. 빗살/바닥 대비로 보면 0.87 → 4.40 dB, 즉 az0 에서는 상한 위에 **빗살이 사실상 "
        "없었고**(백색 널 12.5 % 대비 몫 14.9 %) az45 에서 얇아진 바닥 위로 약한 선이 드러난 것이다. "
        "이것은 R13 의 «회절은 지우지 않고 덮는다» 와 같은 그림의 반대쪽 — 방위를 벗어나면 덮개가 "
        "얇아진다. ⭐**방위 서사가 닫힌다: 방위 축의 미귀속 칸은 이제 없다.** "
        "⚠단 «덮개가 왜 얇아졌나»(방위 기하인가 다른 광선 실현인가)는 이 판이 못 닫는다 — "
        "그것은 시드 복제가 필요한 별개 물음이고 영구 단서로 남긴다.")
    out["open_items_ko"] = [
        ("⚠**남은 단서 ①** «덮개가 왜 얇아졌나» 는 안 닫혔다. 이 팔은 회절 항을 광선으로 확률 "
         "표집하고 시드 산포가 sd 1.83 · p-p 4.86 dB 다(40 m · el −15 에서 빌린 값). az0 과 az45 는 "
         "기하가 달라 광선 집합도 다르니, 바닥 −10.4 dB 가 «방위 기하» 인지 «다른 광선 실현» 인지 "
         "이 판으로는 못 가른다. ⭐다만 붕괴가 el 0·−30·−60 **세 앙각에서 모두** 같은 부호로 "
         "나오므로 우연한 실현 하나로 설명하기는 어렵다 — 그래도 확정은 시드 복제(백로그 11 위, "
         "`--seed` 배관 선행)가 있어야 한다."),
        ("⚠**남은 단서 ②** az45 쪽 «얹힌 항» 을 못 뺐다. 회절 켠 − 굴절만 뺄셈에 필요한 "
         "`sionna_p4000000000_onlyrefr_r15_n8192_az45` 가 **el −30 한 칸뿐**이다. el −60 az45 칸이 "
         "생기면 «얹힌 항이 얼마나 줄었나» 를 직접 잰다 — 값싼 8 줄이다 "
         "(`--engine sionna --only refr --spp 4000000000 --range-m 15 --n-poses 8192 "
         "--az-deg 45 --els=-60`)."),
        ("⚠**밴드가 전부 빌린 값이다.** 15 m · el −60 · az45 · 회절 켬 조합의 자기 격자·시드 산포를 "
         "한 번도 안 쟀다. 격자 밴드는 우리 커널 축에서, 재실행 밴드는 el −30 에서, 시드 산포는 "
         "40 m · el −15 에서 빌렸다(band_used 에 그대로 적어 뒀다)."),
        (f"⚠az45 의 빗살 선 절대값 {c4['above_comb_line_db']} dB 는 R28 이 의심하는 계산 바닥 "
         "(−145 dB) 에서 2 dB 안쪽이다. 이 선이 «진짜 약한 선» 인지 «계산 바닥의 무늬» 인지는 "
         "표적 없는 잡음 전용 팔이 나와야 갈린다. 결론(분자가 안 컸다)은 이 물음과 무관하지만, "
         "그 선의 **절대값**을 다른 데 인용할 때는 이 꼬리표를 함께 단다."),
        ("az0 칸은 튐 등급 «주의» 다 — 플래시 85 개가 한 표본 폭으로 찍혔고 "
         "(flash_comb_undersampled) 최대 자세의 경로 수가 분포의 0.16 % 꼬리다. 갈아 끼우기 검사를 "
         "통과해 결론은 안 흔들리지만, 이 칸의 절대값 인용에는 꼬리표가 붙는다."),
        ("⚠**내 근거 하나를 스스로 깎는다** — el −60 의 담김계수가 1.126 ± 0.034 라 3σ 안에 1 이 "
         "안 든다. 회절을 켜면 원래 항이 그대로 남는 게 아니라 13 % 쯤 커진 채 남는다는 뜻이다. "
         "바닥 귀속(0.08 dB 안에서 설명)은 안 흔들리지만 «회절은 순수하게 얹기만 한다» 는 더 센 "
         "문장은 el −60 에서 쓰면 안 된다."),
        ("⚠**R12 원문에 섞임이 있다** — 같은 칸에 실린 «리듬 몫 15 → 28 %»(상한 **위**)와 "
         "«beat/floor 21.9 → 27.6 dB»(박자 126.1 Hz = 상한 **아래**)는 서로 다른 대역의 수다. "
         "나란히 인용하면 «몫도 오르고 대비도 올랐다» 로 잘못 읽힌다. r12_cross_check 참고."),
        ("⭐남은 상류 물음은 «상한 위에 애초에 왜 빗살이 서나» 다 — 날개끝 상한 위는 강체 회전 "
         "날개가 전력을 놓을 수 없는 자리다. R24(자세 수 사다리)가 그 정체를 가른다."),
    ]

    os.makedirs(os.path.dirname(FIG1), exist_ok=True)
    json.dump(out, open(OUTJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ {OUTJ}")
    print(f"   판정 {verdict_code} — {verdict_why}")
    print(f"   Δ① AC {hd['d_ac_db']} · Δ② 바닥 {hd['d_above_floor_db']} · "
          f"Δ③ 빗살선 {hd['d_above_comb_line_db']} dB")
    for s in st:
        print(f"   {'PASS' if s['pass_'] else 'FAIL'} · {s['name']} — {s['detail_ko']}")

    # ═══ 그림 ═══════════════════════════════════════════════════════════════
    make_figs(out, cells, key_of, Z, PRF, FFL, a0, a45)


#: 색은 dataviz 스킬의 검증된 기본 팔레트 슬롯 1·2 (light) 를 그대로 쓴다.
#  ⚠이 컨테이너에 node 가 없어 validate_palette.js 를 직접 못 돌렸다 — 그래서 새 색을 만들지 않고
#    문서에 «adjacent 쌍 전부 통과» 로 기록된 슬롯을 **그대로** 가져다 썼다.
C_AZ0, C_AZ45 = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#c9c8c3"


def make_figs(out, cells, key_of, Z, PRF, FFL, a0, a45):
    hd = out["headline_cell"]
    el = HEADLINE_EL

    # ── 그림 1 · 세 열의 «어디서 어디로» — 두 상태를 잇는 화살표 ──────────────
    #   ⛔막대(0 기준)를 안 쓴다: dB 레벨에 0 은 뜻이 없어 막대 길이가 거짓말을 한다.
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.8))
    panels = [("PathSolver, physics ON", "sionna_p4000000000_phys_r15_n8192_d1",
               "sionna_p4000000000_phys_r15_n8192_az45_d1"),
              ("PathSolver, physics OFF", "sionna_p4000000000_r15_n8192_d1",
               "sionna_p4000000000_r15_n8192_az45_d1"),
              ("Our kernel (SBR+PO)", "ours_r15_n8192", "ours_r15_n8192_az45")]
    keys = [("ac_db", "(1)\nAC power"),
            ("above_floor_db", "(2)\nfloor"),
            ("above_comb_db", "(3)\ncomb bins")]
    for ax, (title, p0, p45) in zip(axes, panels):
        v0 = [cells[key_of[(p0, el)]][k] for k, _ in keys]
        v4 = [cells[key_of[(p45, el)]][k] for k, _ in keys]
        vals = [v for v in v0 + v4 if v is not None]
        lo, hi = min(vals), max(vals)
        pad = max(2.0, 0.16 * (hi - lo))
        for i, (a, b) in enumerate(zip(v0, v4)):
            if a is None or b is None:
                continue
            # ⭐두 점이 겹칠 때 하나가 다른 하나를 가리지 않게 x 를 조금 벌린다
            xa, xb = i - 0.055, i + 0.055
            ax.annotate("", xy=(xb, b), xytext=(xa, a),
                        arrowprops=dict(arrowstyle="-|>", lw=1.8, color=INK2,
                                        shrinkA=6.0, shrinkB=4.0, alpha=0.7))
            ax.plot([xa], [a], "o", ms=9, color=C_AZ0, zorder=3,
                    markeredgecolor="white", markeredgewidth=1.4)
            ax.plot([xb], [b], "s", ms=9, color=C_AZ45, zorder=3,
                    markeredgecolor="white", markeredgewidth=1.4)
            dlt = b - a
            txt = "0.0" if abs(dlt) < 0.05 else f"{dlt:+.1f}"
            ax.annotate(txt, (i + 0.17, 0.5 * (a + b)), fontsize=10.5,
                        color=INK, va="center", ha="left", fontweight="bold")
        ax.set_xticks(range(3))
        ax.set_xticklabels([lb for _, lb in keys], fontsize=9.5, color=INK2)
        ax.set_xlim(-0.55, 2.75)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_title(title, fontsize=11, color=INK)
        ax.grid(axis="y", alpha=0.5, lw=0.6, color=GRID)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=9)
    axes[0].set_ylabel("absolute power [dB]", fontsize=10, color=INK2)
    h = [plt.Line2D([], [], marker="o", ls="", ms=9, color=C_AZ0,
                    markeredgecolor="white", markeredgewidth=1.4, label="azimuth 0 deg"),
         plt.Line2D([], [], marker="s", ls="", ms=9, color=C_AZ45,
                    markeredgecolor="white", markeredgewidth=1.4, label="azimuth 45 deg")]
    axes[0].legend(handles=h, fontsize=9.5, loc="lower left", frameon=False)
    fig.suptitle(f"Turning 45 degrees off the nose at elevation {el:+.0f} degrees "
                 f"(matrice4e, 15 m) — numbers are the change in dB",
                 fontsize=12, color=INK)
    fig.text(0.5, 0.055,
             "Column (2) is the denominator of the rhythm share and (3) is its numerator.",
             ha="center", fontsize=9.5, color=INK2)
    fig.text(0.5, 0.017,
             "Only the diffraction arm moves — floor down 10.4 dB, comb bins down 6.8 dB — so "
             "the share rises with no new structure.   Each panel keeps its own scale.",
             ha="center", fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.095, 1, 0.93))
    fig.savefig(FIG1, dpi=155)
    plt.close(fig)
    print(f"✅ {FIG1}")

    # ── 그림 2 · 스펙트럼 — 바닥(굵은 선)과 빗살(점)을 갈라 그린다 ───────────
    fig, ax = plt.subplots(figsize=(11.6, 5.0))
    ft = cells[key_of[(a0, el)]]["f_tip_hz"]
    fmax = 4000.0
    ax.axvspan(ft, fmax, color="#f0efe9", zorder=0)
    for arm, c, lab in ((a0, C_AZ0, "azimuth 0 deg"), (a45, C_AZ45, "azimuth 45 deg")):
        E = np.asarray(Z[key_of[(arm, el)]], complex)
        x = E - E.mean()
        w = np.hanning(x.size)
        P = np.abs(np.fft.fft(x * w)) ** 2 / (x.size * np.sum(w ** 2))
        fr = np.fft.fftfreq(x.size, 1.0 / PRF)
        m = (fr > 0) & (fr < fmax)
        f, p = fr[m], P[m]
        k = np.round(f / FFL)
        on = np.abs(f - k * FFL) <= HALF_HZ
        # 바닥 — 빗살 밖 빈만 모아 구간 중앙값
        edges = np.linspace(0, fmax, 41)
        fc, fl = [], []
        for lo_, hi_ in zip(edges[:-1], edges[1:]):
            sel = (f >= lo_) & (f < hi_) & ~on
            if sel.sum() > 8:
                fc.append(0.5 * (lo_ + hi_))
                fl.append(10 * np.log10(np.median(p[sel])))
        ax.plot(f, 10 * np.log10(np.maximum(p, 1e-32)), lw=0.45, color=c, alpha=0.15, zorder=1)
        ax.plot(fc, fl, lw=2.6, color=c, zorder=3)
        # 빗살 — 각 배음의 최댓값
        hx, hy = [], []
        for kk in range(1, int(fmax / FFL) + 1):
            f0 = kk * FFL
            sel = np.abs(f - f0) <= HALF_HZ
            if sel.any():
                hx.append(f0)
                hy.append(10 * np.log10(max(p[sel].max(), 1e-32)))
        ax.plot(hx, hy, "o", ms=5.2, color=c, zorder=4, markeredgecolor="white",
                markeredgewidth=0.8)
    ax.axvline(ft, color=INK, lw=1.2, ls="--", zorder=2)
    ax.set_ylim(-206, -136)
    y0, y1 = ax.get_ylim()
    ax.annotate(f"blade-tip limit {ft:.0f} Hz  |  no rigid blade can put power to the right",
                (ft + 60, y0 + 0.035 * (y1 - y0)), fontsize=10, color=INK,
                ha="left", va="bottom",
                bbox=dict(boxstyle="round,pad=0.34", fc="white", ec=GRID, lw=0.7, alpha=0.94))
    ax.set_xlabel("modulation frequency [Hz]", fontsize=10, color=INK2)
    ax.set_ylabel("power spectral density [dB]", fontsize=10, color=INK2)
    fig.suptitle(f"PathSolver with diffraction on, elevation {el:+.0f} degrees — "
                 f"off nose the floor drops but the harmonics stay",
                 fontsize=12.5, color=INK, y=0.975)
    # ⭐범례는 축 밖(제목 아래)에 둔다 — 안에 두면 자료를 가린다.
    #   색은 방위, 모양은 «바닥이냐 배음이냐» 로 뜻을 갈라 적는다.
    lg = [plt.Line2D([], [], color=C_AZ0, lw=2.6, label="azimuth 0 deg"),
          plt.Line2D([], [], color=C_AZ45, lw=2.6, label="azimuth 45 deg"),
          plt.Line2D([], [], color="#8a8984", lw=2.6, label="thick line: floor (comb-free median)"),
          plt.Line2D([], [], color="#8a8984", marker="o", ls="", ms=5.2,
                     markeredgecolor="white", markeredgewidth=0.8,
                     label="dot: blade-flash harmonic")]
    fig.legend(handles=lg, loc="upper center", bbox_to_anchor=(0.5, 0.925), ncol=4,
               frameon=False, fontsize=9.5, handlelength=1.9, columnspacing=1.7)
    ax.grid(alpha=0.5, lw=0.6, color=GRID)
    ax.set_axisbelow(True)
    ax.set_xlim(0, fmax)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    fig.text(0.5, 0.015, "Faint traces are the raw spectra. Off nose the floor falls 10.4 dB "
                         "while the harmonics fall only 6.8 dB — that gap, not new structure, "
                         "is the whole rise in rhythm share.",
             ha="center", fontsize=9.5, color=INK2)
    fig.tight_layout(rect=(0, 0.055, 1, 0.875))
    fig.savefig(FIG2, dpi=155)
    plt.close(fig)
    print(f"✅ {FIG2}")


if __name__ == "__main__":
    main()
