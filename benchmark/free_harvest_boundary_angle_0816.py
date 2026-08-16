# -*- coding: utf-8 -*-
"""
free_harvest_boundary_angle_0816.py — ⭐**정면 체제의 경계각** (백로그 1 위 · GPU 0)

■ 묻는 것
    ① 정면(앙각 0°)에서 프로펠러 무늬가 «익사» 하는 것이 **몇 도부터 풀리나**.
       잣대는 두 개다 — 리듬 몫(구조)·빗살 대비(선 대 사이). 각 기체의 **자기 널**을 넘어서는
       자리를 경계로 본다.
    ② 그 경계가 **팔마다**(우리 커널 · PathSolver 다 끔 · PathSolver 굴절만) 다른가.
    ③ **기체마다**(matrice4e · mini5pro · s1000plus) 다른가.
    ④ 새로 들어온 **−52 · −68 · −82°** 에서 무엇이 새로 보이나.

■ ⛔GPU 를 쓰지 않는다 — sionna.rt · mitsuba 를 임포트하지 않는다. 저장된 원장만 읽는다.

■ 잣대 규약 (어기면 결론이 뒤집힌다)
    · 레벨[dB]은 **정지 성분(DC) 제거 뒤**의 AC 로만 잰다.
    · 리듬 몫의 널(백색값)은 **기체·앙각마다 다르다** — 칸마다 그 칸의 널을 쓴다
      (matrice4e ≈ 12.5 · s1000plus ≈ 10.9 · mini5pro ≈ 8.7 %). ⛔한 값을 모든 팔에 대지 않는다.
    · 격자 산포 밴드는 **앙각마다 다르다**. 새 앙각(−52·−68·−82)에는 밴드가 없어 **이웃에서
      선형 보간해 빌려 쓴다** — 그 칸은 `band_borrowed: true` 로 표시한다.
    · 밴드 안이면 **판정 불가**. 모르면 모른다고 적는다.
    · 수치 바닥(AC/DC ≤ 1e-11) 근처는 near_numeric_floor 로 표시하고 물리로 읽지 않는다.
    · ⭐튀는 자세 검사: 이미 있는 등급은 `outputs/outlier_census_0816.json`(349 행 판)에서
      가져오고, **새 칸은 같은 절차로 직접 잰다**. 자세는 **지우지 않고 이웃 평균으로 갈아 끼운다**.

■ 원장 (읽기 전용)
    outputs/elevation_sweep_md.{json,npz}   병합 원장 (411 행 · 앙각 10 점)
    outputs/elev_sweep_shards/*.npz         자세별 경로 수
    outputs/outlier_census_0816.json        튐 문턱·등급 (349 행 시점)

■ 굽는 것
    outputs/free_harvest_boundary_angle_0816.json
    outputs/figures/free_harvest_boundary_angle_0816.png

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/free_harvest_boundary_angle_0816.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
from matplotlib.lines import Line2D                                    # noqa: E402

import build_md_atlas as A                                             # noqa: E402
import depth_axis_verdict_0816 as D                                    # noqa: E402
import outlier_census_0816 as OC                                       # noqa: E402

ROOT = A.ROOT
OUTJ = os.path.join(ROOT, "outputs", "free_harvest_boundary_angle_0816.json")
FIGP = os.path.join(ROOT, "outputs", "figures", "free_harvest_boundary_angle_0816.png")
CENSUS_J = os.path.join(ROOT, "outputs", "outlier_census_0816.json")

NEAR_FLOOR = 1e-11
COMB_NULL_DB = D.COMB_NULL_DB          # 3.0 — 빗살 «백색 널 자리» 폭
NEW_ELS = (-52.0, -68.0, -82.0)
RNG = np.random.default_rng(20260816)
N_CONTROL = 12

# ── 팔 표 ──────────────────────────────────────────────────────────────────
#   (팔 열쇠, 영어 이름, 한국어 이름) — 기체는 팔 이름이 정한다
ARMS = {
    "ours": dict(
        en="Our kernel (SBR+PO)", ko="우리 커널",
        by_drone={"matrice4e": "ours_r15_n8192",
                  "mini5pro": "ours_mini5pro_r15_n8192",
                  "s1000plus": "ours_s1000plus_r15_n8192"}),
    "ps_alloff": dict(
        en="PathSolver, all physics off", ko="PS 다 끔(확산만)",
        by_drone={"matrice4e": "sionna_p4000000000_r15_n8192_d1",
                  "mini5pro": "sionna_p4000000000_mini5pro_r15_n8192_d1",
                  "s1000plus": "sionna_p4000000000_s1000plus_r15_n8192_d1"}),
    "ps_refr": dict(
        en="PathSolver, refraction only", ko="PS 굴절만",
        by_drone={"matrice4e": "sionna_p4000000000_onlyrefr_r15_n8192",
                  "mini5pro": "sionna_p4000000000_onlyrefr_mini5pro_r15_n8192",
                  "s1000plus": "sionna_p4000000000_onlyrefr_s1000plus_r15_n8192"}),
    "ps_phys": dict(
        en="PathSolver, physics on (reference)", ko="PS 물리 켬(참고)",
        by_drone={"matrice4e": "sionna_p4000000000_phys_r15_n8192_d1",
                  "mini5pro": "sionna_p4000000000_phys_mini5pro_r15_n8192_d1",
                  "s1000plus": "sionna_p4000000000_phys_s1000plus_r15_n8192_d1"}),
}
SCORED_ARMS = ("ours", "ps_alloff", "ps_refr")     # ②의 세 팔 — ps_phys 는 참고
DRONES = ("matrice4e", "mini5pro", "s1000plus")
#: 기전 대조 — «로터만» 장면(같은 회전 시계열, 동체 없음)
ROTOR_ONLY = "sionna_p4000000000_partsprop_r15_n8192_d1"
BODY_ONLY = "sionna_p4000000000_partsnoprop_r15_n8192_d1"

CENSUS = json.load(open(CENSUS_J))
TH = CENSUS["thresholds"]
NULL_ISO = CENSUS["null_isolation"]
CENSUS_GRADE = {c["cell"]: c for c in CENSUS["cells"]}


# ═══════════════════════════════════════════════════════════════════════════
# 0. 밴드 — 앙각마다 다르고, 새 앙각은 이웃에서 빌린다
# ═══════════════════════════════════════════════════════════════════════════
def _interp_band(table: dict, el: float):
    """이웃 앙각의 밴드를 선형 보간한다. 한쪽이 None 이면 정의된 쪽을 그대로 빌린다."""
    if el in table:
        return table[el], False, "표에 있는 값"
    ks = sorted(table.keys(), reverse=True)          # 0, −15, … , −90
    #: ⚠«가장 가까운» 이웃이다 — 얕은 쪽은 el 보다 큰 값 중 **최소**(−52 → −45),
    #  깊은 쪽은 el 보다 작은 값 중 **최대**(−52 → −60). 여기를 뒤집으면 0°·−90° 를 잡는다.
    lo = min([k for k in ks if k > el], default=None)     # 얕은 쪽 이웃
    hi = max([k for k in ks if k < el], default=None)     # 깊은 쪽 이웃
    vlo = table.get(lo) if lo is not None else None
    vhi = table.get(hi) if hi is not None else None
    if vlo is not None and vhi is not None:
        w = (el - lo) / (hi - lo)
        return round(vlo + w * (vhi - vlo), 3), True, f"{lo:+.0f}°({vlo}) ↔ {hi:+.0f}°({vhi}) 선형 보간"
    if vlo is not None:
        return vlo, True, f"더 깊은 쪽에 정의된 밴드가 없어 얕은 쪽 {lo:+.0f}°({vlo}) 를 그대로 빌림"
    if vhi is not None:
        return vhi, True, f"더 얕은 쪽에 정의된 밴드가 없어 깊은 쪽 {hi:+.0f}°({vhi}) 를 그대로 빌림"
    return None, True, "이웃에 정의된 밴드가 없다"


def bands_at(el: float) -> dict:
    ac, ac_b, ac_w = _interp_band(D.GRID_BAND_AC_DB, el)
    rh, rh_b, rh_w = _interp_band(D.GRID_BAND_RHYTHM_PP_BY_EL, el)
    cb, cb_b, cb_w = _interp_band(
        {k: v for k, v in D.GRID_BAND_COMB_DB_BY_EL.items() if v is not None}, el)
    return dict(ac_db=ac, rhythm_pp=rh, comb_db=cb,
                borrowed=bool(ac_b or rh_b or cb_b),
                how_ko=dict(ac=ac_w, rhythm=rh_w, comb=cb_w))


# ═══════════════════════════════════════════════════════════════════════════
# 1. 칸 재기
# ═══════════════════════════════════════════════════════════════════════════
def measure(arm: str, el: float) -> dict | None:
    key = f"{arm}/el{el:+.0f}"
    if key not in A.Z.files:
        return None
    E = np.asarray(A.Z[key], complex)
    r = A.ROW[(arm, el)]
    rates = A.arm_rates(arm)
    ffl, ft = rates["f_flash_hz"], A.f_tip_at(rates, el)
    x = E - E.mean()
    p_ac = float(np.mean(np.abs(x) ** 2))
    p_tot = float(np.mean(np.abs(E) ** 2))
    acdc = (p_ac / p_tot) if p_tot > 0 else 0.0
    base = OC.headline(E, ffl, ft)
    bd = bands_at(el)

    degen = []
    if ft <= 1e-6:
        degen.append("f_tip_zero_nadir")
    if acdc < NEAR_FLOOR:
        degen.append("near_numeric_floor")
    if int(r.get("n_missing") or 0):
        degen.append("incomplete")

    c = dict(
        cell=key, arm=arm, el_deg=el, drone=rates["drone"], n_poses=int(E.size),
        n_missing=int(r.get("n_missing") or 0), range_m=r["range_m"],
        f_tip_hz=round(ft, 1), f_flash_hz=round(ffl, 2),
        ac_level_db=round(10 * np.log10(p_ac), 2) if p_ac > 0 else None,
        dc_level_db=round(20 * np.log10(abs(complex(E.mean()))), 2) if abs(E.mean()) > 0 else None,
        ac_over_dc=float(f"{acdc:.4g}"),
        rhythm_pct=None if base["rhythm_pct"] is None else round(base["rhythm_pct"], 2),
        rhythm_null_pct=None if base["rhythm_null_pct"] is None else round(base["rhythm_null_pct"], 2),
        rhythm_degenerate=base["rhythm_degenerate"],
        comb_db=None if base["comb_db"] is None else round(base["comb_db"], 2),
        above_ceiling_pct=None if base["above_ceiling_pct"] is None else round(base["above_ceiling_pct"], 2),
        degenerate=degen, bands=bd,
    )

    # ── 널 대비 여유 ────────────────────────────────────────────────────────
    m_rh = (None if (c["rhythm_pct"] is None or c["rhythm_null_pct"] is None)
            else round(c["rhythm_pct"] - c["rhythm_null_pct"], 2))
    # 빗살 널은 백색잡음 0 dB (실측 +0.4) — 문턱은 «백색 널 폭» 과 «격자 밴드» 중 큰 쪽
    cb_thr = max(COMB_NULL_DB, bd["comb_db"] or 0.0)
    c["margin_rhythm_pp"] = m_rh
    c["margin_comb_db"] = c["comb_db"]
    c["threshold_rhythm_pp"] = bd["rhythm_pp"]
    c["threshold_comb_db"] = round(cb_thr, 2)

    def verdict(margin, thr):
        if margin is None or thr is None:
            return "정의 안 됨"
        if margin > thr:
            return "산다"
        if margin < -thr:
            return "널 아래"
        return "판정 불가(밴드 안)"

    c["verdict_rhythm"] = ("퇴화(f_tip=0)" if c["rhythm_degenerate"]
                           else verdict(m_rh, bd["rhythm_pp"]))
    c["verdict_comb"] = verdict(c["comb_db"], cb_thr)
    alive = [v == "산다" for v in (c["verdict_rhythm"], c["verdict_comb"])
             if v not in ("정의 안 됨", "퇴화(f_tip=0)")]
    c["alive"] = (bool(alive) and all(alive))
    c["alive_any"] = bool(any(alive))
    c["n_witness"] = len(alive)
    return c, E, ffl, ft


# ═══════════════════════════════════════════════════════════════════════════
# 2. 튐 진단 — outlier_census_0816 절차 그대로 (새 칸은 직접 잰다)
# ═══════════════════════════════════════════════════════════════════════════
def census_probe(c: dict, E: np.ndarray, ffl: float, ft: float) -> dict:
    a = np.abs(E - E.mean())
    n = a.size
    if not np.any(a):
        return dict(grade="퇴화", why_ko="AC 가 통째로 0 — 잴 것이 없다", fresh=True)
    srt = np.sort(a)[::-1]
    ip = int(np.argmax(a))
    med = float(np.median(a))
    pw = a ** 2
    tot = float(pw.sum())
    iso = float(srt[0] / srt[1]) if srt[1] > 0 else float("inf")
    s1 = float(pw[ip] / tot * n)
    s8 = float(np.sort(pw)[::-1][:8].sum() / tot * n / 8.0)
    T = A.PRF / ffl
    rec = []
    for m2 in (1, 2, 3, 4, -1, -2, -3, -4):
        cpos = int(round(ip + m2 * T))
        if 0 <= cpos < n:
            w = a[max(cpos - 2, 0):min(cpos + 3, n)]
            if w.size:
                rec.append(float(w.max()))
    recur = (float(a[ip] / max(rec)) if (rec and max(rec) > 0) else None)
    nb = float(np.median(a[[(ip + d) % n for d in (-3, -2, -1, 1, 2, 3)]]))
    jump = float(a[ip] / nb) if nb > 0 else float("inf")

    MK = ("rhythm_pct", "comb_db", "moving_power_db", "above_ceiling_pct")
    base = OC.headline(E, ffl, ft)
    rank = np.argsort(a)[::-1]
    rep1 = OC.headline(OC.replace_pose(E, ip), ffl, ft)
    rep2 = OC.headline(OC.replace_pose(E, int(rank[1])), ffl, ft)
    mid = rank[n // 4: 3 * n // 4]
    ctrl = [OC.headline(OC.replace_pose(E, int(i)), ffl, ft)
            for i in RNG.choice(mid, size=min(N_CONTROL, mid.size), replace=False)]
    d_top = {k: OC.dd(base[k], rep1[k]) for k in MK}
    d_2nd = {k: OC.dd(base[k], rep2[k]) for k in MK}
    d_ctl = {}
    for k in MK:
        v = [abs(OC.dd(base[k], q[k])) for q in ctrl if OC.dd(base[k], q[k]) is not None]
        d_ctl[k] = None if not v else float(max(v))

    def dom(k):
        t = d_top.get(k)
        if t is None:
            return None
        ref = [abs(v) for v in (d_2nd.get(k), d_ctl.get(k)) if v is not None]
        ref = max(ref) if ref else 0.0
        if ref <= 0:
            return None if abs(t) <= 0 else float("inf")
        return float(abs(t) / ref)

    dline = TH["dominance_pooled"]["outer_fence"]
    bd = c["bands"]
    band_of = {"rhythm_pct": bd["rhythm_pp"], "moving_power_db": bd["ac_db"],
               "comb_db": bd["comb_db"], "above_ceiling_pct": D.GRID_BAND_ABOVE_PP_GLOBAL}
    big, watch, reasons = [], [], []
    for k in MK:
        if base["rhythm_degenerate"] and k in ("rhythm_pct", "above_ceiling_pct"):
            continue
        v, dv = d_top.get(k), dom(k)
        if v is None:
            continue
        over = (dv is None and abs(v) > 0) or (dv is not None and not np.isfinite(dv)) \
            or (dv is not None and np.isfinite(dv) and dv > dline)
        if not over:
            continue
        tag = "대조군이 0" if (dv is None or not np.isfinite(dv)) else f"쏠림 {dv:.0f}×"
        reasons.append(f"자세 하나로 {k} {v:+.3g} · {tag}")
        b0 = base[k]
        frozen = ""
        if k == "comb_db" and b0 is not None and max(abs(b0), abs(b0 + v)) <= COMB_NULL_DB:
            frozen = "빗살 백색 널 자리 안 — 읽기 안 바뀜"
        if k == "rhythm_pct" and b0 is not None and base["rhythm_null_pct"] is not None \
                and max(b0, b0 + v) <= base["rhythm_null_pct"]:
            frozen = "리듬이 백색 널 아래 — 읽기 안 바뀜"
        bnd = band_of.get(k)
        if frozen:
            watch.append(f"{k} {v:+.3g} ({frozen})")
        elif bnd is not None and abs(v) > bnd:
            big.append(f"{k} {v:+.3g} > 격자밴드 {bnd} ({abs(v) / bnd:.1f} 배) · {tag}")
        else:
            watch.append(f"{k} {v:+.3g} · {tag} (격자밴드 안)")

    # ⭐덜 찍힌 플래시 빗살 — 튐이 **아니다**(시간 분해능). census 와 같은 정의로 재현한다.
    la = np.log10(a[a > 0])
    q1, q3 = np.percentile(la, [25, 75])
    hi_line = (10 ** (q3 + 3.0 * (q3 - q1)) if q3 > q1 else float(a.max()) * 1.001)
    hi = np.where(a > hi_line)[0]
    hi_jump = None
    if hi.size:
        jj = [a[i] / np.median(a[[(i + d) % n for d in (-3, -2, -1, 1, 2, 3)]]) for i in hi]
        jj = [v for v in jj if np.isfinite(v)]
        hi_jump = float(np.median(jj)) if jj else None
    hi_over_flash = (float(hi.size) / (n / T)) if hi.size else 0.0
    comb_like = bool(hi.size >= 8 and hi_over_flash >= 0.5 and (hi_jump or 0) > 5)
    if comb_like:
        reasons.append(f"플래시 {int(hi.size)} 개가 한 표본 폭(이웃 대비 중앙 {hi_jump:.1f}×) — "
                       "덜 찍힌 것이지 튐이 아니다")
        watch.append("플래시가 한 표본 폭 — 덜 찍힘(시간 분해능)")

    iso_null = NULL_ISO.get(str(n), {}).get("p999")
    if iso_null and np.isfinite(iso) and iso > iso_null:
        reasons.append(f"고립도 {iso:.2f} > 잡음판 99.9 % {iso_null:.3f}")
        watch.append("고립도가 잡음판 꼬리 밖")
    if recur is not None and recur > TH["flash_recur"]["outer_fence"]:
        reasons.append(f"날개 통과 주기에 되풀이 없음 {recur:.1f}×")
    if np.isfinite(jump) and jump > TH["neighbor_jump"]["inner_fence"]:
        reasons.append(f"이웃 자세 대비 {jump:.0f}× — 한 표본 폭")

    npm = OC.shard_npaths_map(c["arm"], c["el_deg"])
    np_note = None
    if npm and ip in npm:
        v = np.asarray(list(npm.values()), float)
        tail = float(min((v <= npm[ip]).mean(), (v >= npm[ip]).mean()))
        med_np = float(np.median(v))
        mad = float(np.median(np.abs(v - med_np)))
        if mad <= 0:
            iqr = float(np.subtract(*np.percentile(v, [75, 25])))
            mad = iqr / 1.349 if iqr > 0 else 0.0
        zz = float((npm[ip] - med_np) / (1.4826 * mad)) if mad > 0 else None
        if zz is not None and abs(zz) > TH["npaths_abs_z"]["outer_fence"]:
            reasons.append(f"그 자세의 경로 수가 중앙에서 z={zz:+.1f} "
                           f"({npm[ip]:.0f} 대 중앙 {med_np:.0f})")
            watch.append("그 자세만 경로 수가 크게 다르다")
        if tail < 0.01:
            np_note = (f"그 자세의 경로 수 {npm[ip]:.0f} 이 분포의 {100 * tail:.2f} % 꼬리 "
                       f"(중앙 {med_np:.0f}) — 혼자서는 등급을 올리지 않는다")
            reasons.append(np_note)

    grade = "튐" if big else ("주의" if watch else "정상")
    return dict(
        grade=grade, fresh=True, argmax_pose=ip,
        isolation=round(iso, 4) if np.isfinite(iso) else None,
        top1_over_median=round(float(srt[0] / med), 3) if med > 0 else None,
        share_top1_x=round(s1, 3), share_top8_x=round(s8, 3),
        flash_recur=None if recur is None else round(recur, 3),
        neighbor_jump=round(jump, 3) if np.isfinite(jump) else None,
        replace_one={f"d_{k}": (None if d_top[k] is None else round(d_top[k], 4)) for k in MK},
        dominance={k: (None if dom(k) is None else
                       (None if not np.isfinite(dom(k)) else round(dom(k), 2))) for k in MK},
        dominance_fence=round(dline, 2),
        flash_comb_undersampled=comb_like, n_hi_poses=int(hi.size),
        impact_over_band=big, watch=watch, reasons=reasons,
        repaired={k: (None if (base[k] is None or d_top[k] is None) else
                      round(base[k] + d_top[k], 3)) for k in MK},
        band_borrowed=bd["borrowed"], npaths_note_ko=np_note)


# ═══════════════════════════════════════════════════════════════════════════
# 3. 본체
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    cells = {}
    for akey, spec in ARMS.items():
        for drone, arm in spec["by_drone"].items():
            for el in sorted({float(r["el_deg"]) for r in A.J["rows"] if r["engine"] == arm},
                             reverse=True):
                got = measure(arm, el)
                if got is None:
                    continue
                c, E, ffl, ft = got
                c["arm_key"] = akey
                c["arm_en"], c["arm_ko"] = spec["en"], spec["ko"]
                stored = CENSUS_GRADE.get(c["cell"])
                pr = census_probe(c, E, ffl, ft)
                c["outlier"] = pr
                c["outlier"]["stored_grade_349row"] = (stored or {}).get("grade")
                c["outlier"]["stored_classes"] = (stored or {}).get("classes")
                c["outlier"]["source_ko"] = (
                    "새 칸 — 이 스크립트가 census 절차로 직접 쟀다"
                    if stored is None else
                    "349 행 census 에 있던 칸 — 여기서 다시 재어 등급이 같은지 확인했다")
                # ⭐수리판(가장 튄 자세를 이웃 평균으로 갈아 끼움)으로 판정이 바뀌는지
                rep = pr.get("repaired", {})
                nullp = c["rhythm_null_pct"]
                bd = c["bands"]
                rr = rep.get("rhythm_pct")
                cc = rep.get("comb_db")
                ok_r = (None if (rr is None or nullp is None or bd["rhythm_pp"] is None
                                 or c["rhythm_degenerate"])
                        else bool((rr - nullp) > bd["rhythm_pp"]))
                ok_c = (None if cc is None else bool(cc > c["threshold_comb_db"]))
                same = True
                if ok_r is not None:
                    same &= (ok_r == (c["verdict_rhythm"] == "산다"))
                if ok_c is not None:
                    same &= (ok_c == (c["verdict_comb"] == "산다"))
                c["verdict_survives_pose_repair"] = bool(same)
                cells[c["cell"]] = c

    # ── 기전 대조: 로터만 장면 ↔ 전체 장면 ──────────────────────────────────
    mech = []
    for el in sorted({float(r["el_deg"]) for r in A.J["rows"] if r["engine"] == ROTOR_ONLY},
                     reverse=True):
        full = cells.get(f"{ARMS['ps_alloff']['by_drone']['matrice4e']}/el{el:+.0f}")
        got = measure(ROTOR_ONLY, el)
        if got is None or full is None:
            continue
        rc = got[0]
        mech.append(dict(
            el_deg=el,
            full_scene_ac_db=full["ac_level_db"], rotor_only_ac_db=rc["ac_level_db"],
            flicker_excess_db=round(full["ac_level_db"] - rc["ac_level_db"], 2),
            full_rhythm_pct=full["rhythm_pct"], rotor_only_rhythm_pct=rc["rhythm_pct"],
            full_comb_db=full["comb_db"], rotor_only_comb_db=rc["comb_db"],
            full_above_ceiling_pct=full["above_ceiling_pct"]))
    body = measure(BODY_ONLY, 0.0)
    body_c = body[0] if body else None

    # ── 경계각 ─────────────────────────────────────────────────────────────
    def boundary(akey: str, drone: str) -> dict:
        arm = ARMS[akey]["by_drone"][drone]
        seq = [c for c in cells.values() if c["arm"] == arm]
        seq.sort(key=lambda c: -c["el_deg"])          # 0 → −90
        usable = [c for c in seq if "f_tip_zero_nadir" not in c["degenerate"]]
        out = dict(arm=arm, arm_key=akey, arm_ko=ARMS[akey]["ko"], drone=drone,
                   elevations_deg=[c["el_deg"] for c in seq],
                   n_elevations=len(seq),
                   rhythm_pct=[c["rhythm_pct"] for c in seq],
                   rhythm_null_pct=[c["rhythm_null_pct"] for c in seq],
                   comb_db=[c["comb_db"] for c in seq],
                   above_ceiling_pct=[c["above_ceiling_pct"] for c in seq],
                   ac_level_db=[c["ac_level_db"] for c in seq],
                   verdicts=[f"{c['el_deg']:+.0f}: {c['verdict_rhythm']}/{c['verdict_comb']}"
                             for c in seq])
        if not usable:
            out["boundary_ko"] = "쓸 수 있는 칸이 없다"
            return out
        head = usable[0]
        if head["alive"]:
            out["boundary_deg"] = None
            out["boundary_kind"] = "없음 — 정면에서 이미 산다"
            out["boundary_ko"] = (
                f"앙각 0° 에서 이미 두 잣대가 다 널 위다 (리듬 {head['rhythm_pct']} % vs 널 "
                f"{head['rhythm_null_pct']} % · 빗살 {head['comb_db']} dB vs 문턱 "
                f"{head['threshold_comb_db']} dB) — **익사 자체가 없다.** 경계각은 정의되지 않는다.")
            return out
        first = next((c for c in usable if c["alive"]), None)
        if first is None:
            out["boundary_deg"] = None
            out["boundary_kind"] = "없음 — 어느 앙각에서도 안 산다"
            out["boundary_ko"] = "0° 부터 −90° 까지 두 잣대가 한 번도 함께 널 위로 못 올라온다"
            return out
        prev = usable[usable.index(first) - 1]
        out["boundary_deg"] = None
        out["boundary_bracket_deg"] = [prev["el_deg"], first["el_deg"]]
        out["boundary_kind"] = "괄호 — 표집 간격 안"
        out["boundary_midpoint_deg"] = round(0.5 * (prev["el_deg"] + first["el_deg"]), 1)
        out["boundary_halfwidth_deg"] = round(0.5 * abs(first["el_deg"] - prev["el_deg"]), 1)
        out["boundary_ko"] = (
            f"{prev['el_deg']:+.0f}° 에서는 익사(리듬 {prev['rhythm_pct']} % vs 널 "
            f"{prev['rhythm_null_pct']} % · 빗살 {prev['comb_db']} dB), "
            f"{first['el_deg']:+.0f}° 에서는 산다(리듬 {first['rhythm_pct']} % · 빗살 "
            f"{first['comb_db']} dB). 경계는 그 사이 어딘가다 — **표집 간격이 "
            f"{abs(first['el_deg'] - prev['el_deg']):.0f}° 라 더 좁힐 수 없다.**")
        return out

    bounds = {}
    for akey in ARMS:
        for drone in DRONES:
            arm = ARMS[akey]["by_drone"][drone]
            if not any(c["arm"] == arm for c in cells.values()):
                continue
            bounds[f"{akey}|{drone}"] = boundary(akey, drone)

    # ── 새 세 각도가 무엇을 더 주나 ─────────────────────────────────────────
    new = []
    for akey in ("ours", "ps_alloff", "ps_phys"):
        arm = ARMS[akey]["by_drone"]["matrice4e"]
        for el in NEW_ELS:
            c = cells.get(f"{arm}/el{el:+.0f}")
            if c is None:
                continue
            new.append(dict(cell=c["cell"], arm_ko=c["arm_ko"], el_deg=el,
                            f_tip_hz=c["f_tip_hz"],
                            rhythm_pct=c["rhythm_pct"], rhythm_null_pct=c["rhythm_null_pct"],
                            comb_db=c["comb_db"], comb_defined=c["comb_db"] is not None,
                            above_ceiling_pct=c["above_ceiling_pct"],
                            ac_level_db=c["ac_level_db"],
                            verdict=f"{c['verdict_rhythm']}/{c['verdict_comb']}",
                            band_borrowed=c["bands"]["borrowed"],
                            band_how_ko=c["bands"]["how_ko"],
                            outlier_grade=c["outlier"]["grade"]))

    fig = make_figure(cells, mech)

    now = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
    doc = dict(
        _meta=dict(
            generator="benchmark/free_harvest_boundary_angle_0816.py",
            written_at_kst=now.strftime("%Y-%m-%d %H:%M KST"),
            gpu_used="⛔ 안 씀 — 저장된 원장만 읽었다 (sionna.rt · mitsuba 임포트 없음)",
            question_ko=["① 정면 익사가 몇 도부터 풀리나", "② 경계가 팔마다 다른가",
                         "③ 경계가 기체마다 다른가", "④ 새 세 각도(−52·−68·−82)가 무엇을 더 주나"],
            ledger=dict(json="outputs/elevation_sweep_md.json",
                        npz="outputs/elevation_sweep_md.npz",
                        n_rows=len(A.J["rows"]),
                        elevations_deg=sorted({float(r["el_deg"]) for r in A.J["rows"]},
                                              reverse=True),
                        mtime_kst=_dt.datetime.fromtimestamp(
                            os.path.getmtime(A.LED_J), _dt.timezone(_dt.timedelta(hours=9))
                        ).strftime("%Y-%m-%d %H:%M KST")),
            rules_ko=[
                "레벨[dB]은 전부 **정지 성분(DC) 제거 뒤** AC 로 잰다.",
                "리듬 몫의 널은 칸마다 그 칸의 값을 쓴다 — 기체·앙각마다 다르다"
                "(matrice4e ≈ 12.5 · s1000plus ≈ 10.9 · mini5pro ≈ 8.7 %). ⛔한 값 돌려쓰기 금지.",
                "빗살 대비의 널은 백색잡음 0 dB 다. 문턱은 «백색 널 폭 3 dB» 와 «그 앙각의 격자 밴드» "
                "중 큰 쪽으로 잡았다 — 둘 다 넘어야 «산다».",
                "격자 산포 밴드는 앙각마다 다르다. **새 앙각(−52·−68·−82)에는 밴드가 없어 이웃에서 "
                "선형 보간해 빌렸다** — 그 칸은 bands.borrowed = true 다. 빌린 값으로 내린 판정은 "
                "«빌린 잣대» 라는 꼬리표를 달고 읽어야 한다.",
                "밴드 안이면 «판정 불가» 로 적는다. 산다/죽는다로 밀어붙이지 않는다.",
                "AC/DC ≤ 1e-11 는 near_numeric_floor 로 표시하고 물리로 읽지 않는다.",
                "튀는 자세는 **지우지 않고 이웃 평균으로 갈아 끼워** 영향을 잰다"
                "(지우면 표집 간격이 깨져 빗살 잣대가 망가진다).",
            ],
            metric_defs_ko=[
                "리듬 몫[%] — 날개끝 상한 f_tip **위** 에너지 중 «날개 지나가는 박자» 의 정수배 "
                "자리(±8 Hz)에 붙은 몫. 세기가 아니라 **구조**를 잰다. 백색잡음이면 널 값이 나온다.",
                "빗살 대비[dB] — 상한 **아래** 대역([2·f_flash, f_tip])에서 «박자 정수배 자리» ÷ "
                "«그 사이 한가운데 자리». 백색잡음이면 0 dB. 무늬가 상한 아래에 얌전히 들어앉아도 잡힌다.",
                "상한 위 몫[%] — 움직이는 에너지 중 날개가 만들 **수 없는** 자리(f_tip 위)에 있는 몫. "
                "이 값이 크면 «날개 신호» 가 아니라 자세 사이의 깜빡임이 잣대를 채우고 있다는 뜻이다.",
                "익사 초과[dB] — 전체 장면 AC − 로터만 장면 AC. 0 dB 면 «흔들리는 것이 곧 로터» 고, "
                "크면 로터가 아닌 것(동체 가림 깜빡임)이 그만큼 위를 덮고 있다는 뜻이다.",
            ],
            outlier_policy_ko=(
                "튐 등급은 outputs/outlier_census_0816.json 의 문턱(349 행 표본에서 딴 Tukey 울타리 "
                f"쏠림 {TH['dominance_pooled']['outer_fence']:.0f}× · 잡음판 고립도 99.9 %)을 그대로 쓰고, "
                "**새 칸은 같은 절차로 여기서 직접 쟀다.** 옛 칸도 다시 재어 저장된 등급과 대조했다. "
                "⚠문턱 자체는 411 행이 아니라 **349 행 표본**의 꼬리라 새 칸에는 «빌린 문턱» 이다."),
            honesty_ko=[
                "⭐**새로 산 세 각도는 이 물음의 답을 좁히지 못한다.** 경계는 0°↔−15° 사이에 있는데 "
                "새 각도는 −52·−68·−82° 로 전부 그 아래(이미 사는 구간)다. 이 사실을 숨기지 않는다.",
                "경계각을 «한 숫자» 로 못 준다 — 0° 와 −15° 사이에 표본이 하나도 없다. 괄호로만 준다.",
                "기전(왜 익사하나)은 이 판이 새로 증명한 것이 아니라 로터만/동체만 장면 대조로 "
                "**재확인**한 것이다.",
            ],
        ),
        bands_used=dict(
            source="depth_axis_verdict_0816 (frame_completion_0816.q4_grid_band)",
            ac_db_by_el=D.GRID_BAND_AC_DB, rhythm_pp_by_el=D.GRID_BAND_RHYTHM_PP_BY_EL,
            comb_db_by_el=D.GRID_BAND_COMB_DB_BY_EL,
            comb_white_null_db=COMB_NULL_DB,
            borrowed_for_new_els={f"{el:+.0f}": bands_at(el) for el in NEW_ELS}),
        cells=[cells[k] for k in sorted(cells)],
        boundaries=bounds,
        mechanism_rotor_only=dict(
            rotor_only_arm=ROTOR_ONLY, body_only_arm=BODY_ONLY,
            rows=mech,
            body_only_el0=None if body_c is None else dict(
                ac_level_db=body_c["ac_level_db"], ac_over_dc=body_c["ac_over_dc"],
                note_ko="동체만 장면은 AC 가 사실상 0 이다 — 동체는 안 움직이니 순수 정지 성분이다. "
                        "그러므로 정면의 요동은 «동체 에코» 가 아니라 도는 프롭이 동체 가림을 "
                        "흔드는 **깜빡임**이다."),
        ),
        new_angles=new,
        figure=os.path.relpath(fig, ROOT),
    )
    grades = {}
    for c in cells.values():
        grades[c["outlier"]["grade"]] = grades.get(c["outlier"]["grade"], 0) + 1
    flips = [c["cell"] for c in cells.values() if not c["verdict_survives_pose_repair"]]
    diffs = [dict(cell=c["cell"], fresh=c["outlier"]["grade"],
                  stored=c["outlier"]["stored_grade_349row"])
             for c in cells.values()
             if c["outlier"]["stored_grade_349row"] not in (None, c["outlier"]["grade"])]
    doc["gates"] = dict(
        n_cells=len(cells), grades=grades,
        n_spike=grades.get("튐", 0),
        verdict_flips_under_pose_repair=flips,
        reproduction_vs_stored_census=dict(
            n_mismatch=len(diffs), rows=diffs,
            note_ko=("남는 어긋남은 «죄 없는 자세» 대조군을 무작위로 뽑는 데서 온다 — 등급이 "
                     "«정상↔주의» 사이에서만 흔들리고 «튐» 은 어느 쪽에서도 안 나온다.")),
        reads_ko=("이 판이 쓰는 칸 전부에서 **튐 등급은 0 개**고, 가장 튄 자세를 이웃 평균으로 "
                  "갈아 끼워도 **산다/익사 판정이 하나도 안 뒤집힌다.** 그러므로 아래 결론은 "
                  "자세 하나가 끌고 있는 것이 아니다."),
        near_numeric_floor_cells=[c["cell"] for c in cells.values()
                                  if "near_numeric_floor" in c["degenerate"]],
        degenerate_nadir_cells=[c["cell"] for c in cells.values()
                                if "f_tip_zero_nadir" in c["degenerate"]],
    )
    doc["answers"] = build_answers(cells, bounds, mech, new)
    doc["open_questions_ko"] = [
        "⭐**경계각의 실제 값** — 0°와 −15° 사이에 표본이 없어 못 잡는다. 사려면 "
        "PS 다 끔·PS 굴절만 × matrice4e·mini5pro × el −4·−8·−11°(GPU 필요).",
        "**절벽인가 비탈인가** — 15° 한 칸에 리듬 +68 %p·빗살 +46 dB 가 움직이지만, 그 사이 "
        "모양은 표본이 없어 모른다.",
        "**s1000plus 가 왜 안 익사하나** — 큰 프로펠러(f_tip0 2081 Hz) 라는 읽기와 맞지만 "
        "인과는 안 증명됐다. 로터만/동체만 장면이 s1000plus 에는 없다.",
        "**s1000plus PS 다 끔의 −75° 구멍** — 리듬 여유가 +7.9 %p 로 꺼지고 상한 위 몫이 "
        "63.2 % 로 치솟는다. 튐은 아니다(등급 정상). 설명 없음.",
        "**새 세 각도는 matrice4e 에만 있다** — mini5pro·s1000plus 에는 −52·−68·−82° 가 없어 "
        "③(기체 차이)은 여전히 15°(굴절만은 30°) 간격으로만 답한다.",
        "**빌린 잣대 둘** — ⓐ 새 앙각의 격자 산포 밴드는 이웃 보간이고 ⓑ 튐 문턱은 349 행 "
        "표본의 꼬리다. 둘 다 411 행에서 다시 뜨면 값이 바뀔 수 있다(이 판의 판정은 밴드를 "
        "0°↔−90° 로 잘못 빌린 첫 계산에서도 하나도 안 뒤집혔으므로 여유는 넓다).",
        "**정면 칸의 «덜 찍힌 플래시»** — PS 두 팔의 el 0 은 플래시가 한 표본 폭이다. 튐이 "
        "아니라 시간 분해능이지만, 정면을 더 촘촘한 자세로 다시 찍으면 잣대가 달라질 수 있다.",
    ]
    with open(OUTJ, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("wrote", OUTJ)
    print("wrote", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 4. 답
# ═══════════════════════════════════════════════════════════════════════════
def build_answers(cells, bounds, mech, new) -> dict:
    def g(akey, drone, el):
        return cells.get(f"{ARMS[akey]['by_drone'][drone]}/el{el:+.0f}")

    a1 = dict(
        headline_ko=(
            "**익사가 일어나는 팔·기체에서 경계는 0° 와 −15° 사이에 있다 — 그보다 좁게는 못 "
            "잡는다.** PathSolver 두 팔 × matrice4e·mini5pro 에서 정면 0° 는 리듬·빗살 둘 다 "
            "널 자리인데, 한 칸 내려간 −15° 에서는 두 잣대가 함께 펄쩍 뛴다"
            "(PS 다 끔 리듬 13.1 → 81.3 % · 빗살 −0.8 → +45.5 dB). 그 사이에 표본이 "
            "**하나도 없어서** 경계각을 한 숫자로 줄 수 없다. ⭐우리 커널과 s1000plus 는 "
            "정면에서 애초에 익사하지 않아 경계 자체가 없다(②·③)."),
        bracket_deg=[0.0, -15.0],
        why_not_narrower_ko=(
            "원장의 앙각 표본이 0 · −15 · −30 · −45 · −52 · −60 · −68 · −75 · −82 · −90° 다. "
            "0° 와 −15° 사이가 비어 있고, 이번에 새로 들어온 세 각도(−52·−68·−82)는 전부 "
            "**경계보다 3.5 배 이상 깊은 쪽**이라 이 물음에는 한 칸도 보태지 못한다."),
        cliff_not_slope_ko=(
            "경계는 완만한 비탈이 아니라 **절벽**으로 보인다 — 15° 한 칸에 리듬 몫이 +68 %p, "
            "빗살 대비가 +46 dB 움직인다. 다만 «절벽이냐 비탈이냐» 는 사이에 표본이 없으니 "
            "**아직 못 가른다.**"),
        witnesses=[dict(arm=ARMS[k]["ko"],
                        el0=dict(rhythm=g(k, "matrice4e", 0)["rhythm_pct"],
                                 null=g(k, "matrice4e", 0)["rhythm_null_pct"],
                                 comb=g(k, "matrice4e", 0)["comb_db"],
                                 above_ceiling=g(k, "matrice4e", 0)["above_ceiling_pct"]),
                        el15=dict(rhythm=g(k, "matrice4e", -15)["rhythm_pct"],
                                  comb=g(k, "matrice4e", -15)["comb_db"],
                                  above_ceiling=g(k, "matrice4e", -15)["above_ceiling_pct"]))
                   for k in ("ours", "ps_alloff", "ps_refr")],
        what_to_buy_ko=(
            "⭐경계를 좁히려면 사야 할 것은 깊은 각이 아니라 **0°와 −15° 사이**다 — "
            "PS 다 끔·PS 굴절만 두 팔 × matrice4e·mini5pro 두 기체 × el −4 · −8 · −11°. "
            "우리 커널은 정면에서 익사하지 않으니 이 물음에는 필요 없다."),
        release_is_the_drowner_leaving_ko=(
            "⭐경계가 «에코가 커지는 자리» 가 아니라는 것을 분명히 해 둔다. 0° → −15° 에서 "
            "PS 다 끔의 AC 레벨은 −94.30 → −145.33 dB 로 **51.0 dB 떨어진다**. 무늬가 살아나는 "
            "것은 날개가 커져서가 아니라 **익사시키던 깜빡임이 사라져서**다. "
            "⚠R12(방위축)는 같은 크기의 붕괴(−51.1 dB)를 보고 «에코 부재» 로 비율 채점을 "
            "거부했다. 그 게이트는 «같은 앙각·다른 방위» 의 A/B 를 위한 것이고 여기서는 레벨 "
            "변화 자체가 재려는 물리라 적용하지 않았다 — 그러나 두 자리가 같은 크기라는 사실은 "
            "적어 둔다."),
        frontal_cell_caveat_ko=(
            "⚠정면 칸(PS 두 팔)은 튐 검사에서 «주의 — 플래시가 한 표본 폭(덜 찍힘)» 이 붙는다. "
            "이는 **튐이 아니라 시간 분해능** 문제다. 다만 정면 칸의 «상한 위 몫» 이 85~86 % 라 "
            "잣대가 재고 있는 것의 대부분이 날개가 만들 수 **없는** 자리라는 사실과 같은 방향이다."),
    )

    a2 = dict(
        headline_ko=(
            "**팔마다 다르다 — 그것도 «몇 도냐» 가 아니라 «있냐 없냐» 로 다르다.** "
            "우리 커널은 정면에서 **애초에 익사하지 않아** 경계각이 존재하지 않는다"
            "(0°에서 리듬 63.3 % ≫ 널 12.5 · 빗살 47.8 dB). PathSolver 는 다 끔·굴절만 "
            "두 팔 다 정면에서 익사하고 경계가 0°↔−15° 사이에 있다. 물리 켬 팔은 정반대로 "
            "**어느 앙각에서도 안 산다**(회절이 바닥을 덮는다)."),
        per_arm={k: dict(arm_ko=ARMS[k]["ko"],
                         boundary=bounds[f"{k}|matrice4e"]["boundary_kind"],
                         boundary_ko=bounds[f"{k}|matrice4e"]["boundary_ko"])
                 for k in ARMS},
        same_boundary_for_two_ps_arms_ko=(
            "PS 다 끔과 PS 굴절만은 경계가 **구별되지 않는다** — 0°에서 리듬 13.06 vs 13.33 %, "
            "빗살 −0.84 vs +0.31 dB 로 둘 다 널 자리이고, −15°에서 둘 다 산다. ⚠두 팔의 경계가 "
            "**같은 괄호(0°, −15°] 안에 떨어진다**는 뜻일 뿐이다 — 굴절이 괄호 **안에서** 경계를 "
            "옮기는지는 그 사이에 표본이 없어 **판정 불가**다. «굴절은 경계를 안 옮긴다» 로 쓰면 "
            "안 된다."),
        ps_phys_note_ko=(
            "⚠물리 켬 팔은 **참고로만** 싣는다. 이 팔은 회절이 바닥을 덮어 거의 전 앙각에서 널에 "
            "붙어 있고(리듬 8.3~17.8 % — matrice4e 11.9~15.0 · mini5pro 8.3~14.3 · "
            "s1000plus 11.2~17.8, 각자의 널 12.5·8.7·10.9 % 바로 위), 그래서 «경계각» 이라는 "
            "물음 자체가 잘 안 선다. "
            "s1000plus 물리 켬에서 코드가 −60°↔−75° 괄호를 내놓지만, 그 자리의 여유는 "
            "리듬 +5.9 %p(밴드 2.5) 로 밴드에 바짝 붙어 있어 **경계로 인용하면 안 된다** — "
            "밴드가 앙각마다 크게 달라(−60° 16.0 vs −75° 2.5 %p) 생긴 잣대 효과일 수 있다."),
    )

    a3 = dict(
        headline_ko=(
            "**기체마다 다르다. s1000plus 는 정면에서도 산다 — 경계가 없다.** "
            "PathSolver 다 끔에서 s1000plus 는 0°에서 리듬 27.9 %(자기 널 10.9 대비 +17.1 %p, "
            "격자 밴드 11.8 %p 밖)·빗살 +26.7 dB 로 두 잣대가 다 널 위다. 같은 팔에서 "
            "matrice4e 는 +0.5 %p·−0.8 dB, mini5pro 는 +0.04 %p·0.0 dB 로 **널에 붙어 있다.**"),
        per_drone={d: dict(
            ps_alloff=dict(
                el0_rhythm=g("ps_alloff", d, 0)["rhythm_pct"],
                el0_null=g("ps_alloff", d, 0)["rhythm_null_pct"],
                el0_margin_pp=g("ps_alloff", d, 0)["margin_rhythm_pp"],
                el0_comb_db=g("ps_alloff", d, 0)["comb_db"],
                el0_above_ceiling_pct=g("ps_alloff", d, 0)["above_ceiling_pct"],
                boundary=bounds[f"ps_alloff|{d}"]["boundary_kind"]),
            ps_refr=dict(
                el0_rhythm=g("ps_refr", d, 0)["rhythm_pct"],
                el0_null=g("ps_refr", d, 0)["rhythm_null_pct"],
                el0_comb_db=g("ps_refr", d, 0)["comb_db"],
                boundary=bounds[f"ps_refr|{d}"]["boundary_kind"]),
            ours=dict(
                el0_rhythm=g("ours", d, 0)["rhythm_pct"],
                el0_null=g("ours", d, 0)["rhythm_null_pct"],
                el0_comb_db=g("ours", d, 0)["comb_db"],
                boundary=bounds[f"ours|{d}"]["boundary_kind"]),
        ) for d in DRONES},
        caution_ko=(
            "⚠s1000plus 의 «산다» 는 리듬 쪽으로는 여유가 밴드의 **1.4 배**밖에 안 된다"
            "(+17.1 %p vs 밴드 11.8 %p). 빗살 쪽은 +26.7 dB 로 문턱 3 dB 를 크게 넘으므로 "
            "판정을 떠받치는 것은 주로 **빗살**이다. ⛔기체끼리 리듬 몫 숫자를 직접 비교하지 마라 — "
            "널이 기체마다 다르다(12.5 · 10.9 · 8.7 %). 각자의 널 대비로만 읽는다."),
        why_ko=(
            "s1000plus 는 프로펠러가 훨씬 크다(f_tip0 2081 Hz — matrice4e 1273 · mini5pro 1025 Hz). "
            "정면에서도 날개가 만드는 대역이 넓어 동체 깜빡임이 그 대역을 다 덮지 못한다는 "
            "**읽기와 맞는다** — 다만 이 판은 그 인과를 증명하지 않았다(로터만 장면이 "
            "s1000plus 에는 없다)."),
        s1000plus_open_items_ko=[
            "정면 0° 의 «상한 위 몫» 이 39.6 % 다(−15° 22.7 % · −30~−60° 1.5~3.6 %) — "
            "산다고 판정되지만 깜빡임이 **일부** 덮고 있다. 완전히 깨끗한 정면은 아니다.",
            "PS 다 끔 s1000plus 는 −75° 에서 리듬 여유가 +7.9 %p 로 푹 꺼지고 «상한 위 몫» 이 "
            "63.2 % 로 치솟는다 — 깊은 각의 **국소 구멍**이다. 튐 등급은 «정상» 이라 자세 하나 "
            "탓이 아니다. 아직 설명 못 한다.",
        ],
    )

    m0 = next((m for m in mech if m["el_deg"] == 0.0), None)
    m30 = next((m for m in mech if m["el_deg"] == -30.0), None)
    a4 = dict(
        headline_ko=(
            "**경계에는 한 칸도 못 보탠다. 대신 깊은 쪽에서 세 가지가 새로 보인다.** "
            "① −68° 는 **빗살 대비를 잴 수 있는 가장 깊은 각**이 됐다(이전 한계는 −60°). "
            "우리 커널이 거기서 전 앙각 최고값 54.3 dB 를 낸다. "
            "② PathSolver 다 끔은 −45 → −90° 로 갈수록 리듬 몫이 84 → 98 % 로 계속 올라가고, "
            "새 세 점(89.4 · 92.4 · 97.5 %)이 그 오름을 **메운다**. "
            "③ 우리 커널은 같은 구간에서 46~75 % 사이를 오르내린다 — 새 점들도 그 흔들림 폭 "
            "안이라 «깊은 쪽에서 우리 커널이 더 흔들린다» 를 표본 3 개로 **보강**한다."),
        comb_now_measurable_ko=(
            f"빗살 대비는 대역 [2·f_flash, f_tip] 에 배음이 셋은 들어가야 정의된다. "
            f"matrice4e 는 f_flash 126.7 Hz 라 f_tip ≥ 380 Hz 가 필요하고, 이는 앙각 −72.6° 까지다. "
            f"−68° 는 f_tip 476.8 Hz 로 **아슬아슬하게 안쪽**, −75° 는 329.5 Hz 로 밖, "
            f"−82° 는 177.2 Hz 로 한참 밖이다. 그래서 새 각 셋 중 빗살을 준 것은 −68° 하나뿐이다."),
        rows=new,
        band_caveat_ko=(
            "⚠세 각도 모두 **격자 산포 밴드가 없다.** 이웃에서 선형 보간해 빌려 썼다 — "
            f"−52°: AC {bands_at(-52.0)['ac_db']} dB · 리듬 {bands_at(-52.0)['rhythm_pp']} %p · "
            f"빗살 {bands_at(-52.0)['comb_db']} dB, "
            f"−68°: {bands_at(-68.0)['ac_db']} · {bands_at(-68.0)['rhythm_pp']} · "
            f"{bands_at(-68.0)['comb_db']}, "
            f"−82°: {bands_at(-82.0)['ac_db']} · {bands_at(-82.0)['rhythm_pp']} · "
            f"{bands_at(-82.0)['comb_db']}. **−82° 의 AC 밴드는 −90°(5.62 dB)의 큰 값이 끌어올려 "
            f"2.68 dB 나 된다 — 빌린 값이라 그 자리의 레벨 비교는 특히 헐겁다.**"),
        mechanism_recheck_ko=(
            None if not (m0 and m30) else
            f"기전 재확인(로터만 장면 대조) — 정면 0°에서 전체 장면의 흔들림이 로터 자신의 "
            f"에코보다 **{m0['flicker_excess_db']:+.1f} dB** 위다. 즉 흔들리는 것의 "
            f"{100 * (1 - 10 ** (-m0['flicker_excess_db'] / 10)):.4f} % 가 로터가 아니다. "
            f"−30°에서는 그 초과가 {m30['flicker_excess_db']:+.2f} dB — **흔들리는 것이 곧 로터다.** "
            f"동체만 장면은 AC 가 −384 dB(사실상 0)라, 정면의 흔들림은 동체 에코가 아니라 "
            f"도는 프롭이 동체 가림을 흔드는 **깜빡임**이다."),
    )
    return dict(q1_boundary=a1, q2_by_arm=a2, q3_by_drone=a3, q4_new_angles=a4)


# ═══════════════════════════════════════════════════════════════════════════
# 5. 그림 — 영어 · 겹침 금지
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11.5,
    "xtick.labelsize": 10.5, "ytick.labelsize": 10.5, "legend.fontsize": 9.8,
    "figure.facecolor": "white", "savefig.facecolor": "white", "axes.axisbelow": True,
})
COL = {"ours": "#1f77b4", "ps_alloff": "#d62728", "ps_refr": "#2ca02c", "ps_phys": "#9467bd"}
DCOL = {"matrice4e": "#d62728", "mini5pro": "#ff7f0e", "s1000plus": "#1f77b4"}
MK = {"matrice4e": "o", "mini5pro": "s", "s1000plus": "^"}


def _series(cells, arm, field, drop_nadir=False):
    pts = sorted([c for c in cells.values() if c["arm"] == arm], key=lambda c: -c["el_deg"])
    if drop_nadir:
        pts = [c for c in pts if "f_tip_zero_nadir" not in c["degenerate"]]
    return ([c["el_deg"] for c in pts], [c[field] for c in pts],
            [c["el_deg"] in NEW_ELS for c in pts])


def _plot(ax, xs, ys, isnew, color, label, ls="-"):
    x = [a for a, b in zip(xs, ys) if b is not None]
    y = [b for b in ys if b is not None]
    ax.plot(x, y, ls, color=color, lw=2.0, zorder=3, label=label)
    for a, b, nn in zip(xs, ys, isnew):
        if b is None:
            continue
        ax.plot([a], [b], marker="D" if nn else "o", ms=9.5 if nn else 6.5,
                mfc="white" if nn else color, mec=color, mew=2.0, zorder=4)


def make_figure(cells, mech) -> str:
    fig, axs = plt.subplots(2, 2, figsize=(15.4, 10.4))
    (axA, axB), (axC, axD) = axs

    # ── (a) rhythm share, matrice4e, three arms + reference ────────────────
    for k in ("ours", "ps_alloff", "ps_refr", "ps_phys"):
        arm = ARMS[k]["by_drone"]["matrice4e"]
        xs, ys, nn = _series(cells, arm, "rhythm_pct", drop_nadir=True)
        _plot(axA, xs, ys, nn, COL[k], ARMS[k]["en"],
              ls="--" if k == "ps_phys" else "-")
    null = cells[f"{ARMS['ours']['by_drone']['matrice4e']}/el+0"]["rhythm_null_pct"]
    axA.axhline(null, color="#444444", ls=":", lw=2.0, zorder=2)
    axA.annotate(f"white-noise null {null:.1f} %  (this airframe)", (-88, null + 3.0),
                 fontsize=10, color="#333333", ha="left", va="bottom")
    axA.axvspan(-15, 0, color="#f2c14e", alpha=0.30, zorder=1)
    axA.annotate("boundary lives in here\nno sample between 0 and -15", xy=(-8.0, 26),
                 xytext=(-33.0, 31), ha="center", va="center", fontsize=10.2,
                 color="#8a5a00", fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color="#8a5a00", lw=1.6))
    axA.annotate("-90 omitted: this ruler degenerates there (f_tip = 0)",
                 (-88, 3.0), fontsize=9.6, color="#666666", ha="left", va="bottom")
    axA.set_ylabel("Rhythm share above blade-tip ceiling [%]")
    axA.set_title("(a) Matrice 4E: the frontal cell is the only drowned one")
    axA.set_ylim(0, 110)

    # ── (b) comb contrast ─────────────────────────────────────────────────
    for k in ("ours", "ps_alloff", "ps_refr", "ps_phys"):
        arm = ARMS[k]["by_drone"]["matrice4e"]
        xs, ys, nn = _series(cells, arm, "comb_db")
        _plot(axB, xs, ys, nn, COL[k], ARMS[k]["en"], ls="--" if k == "ps_phys" else "-")
    axB.axhline(0.0, color="#444444", ls=":", lw=2.0, zorder=2)
    axB.axhspan(-3, 3, color="#bbbbbb", alpha=0.35, zorder=1)
    axB.annotate("white-noise null band, +/-3 dB", (-46, -7.0), fontsize=10,
                 color="#333333", ha="center", va="center")
    axB.axvspan(-15, 0, color="#f2c14e", alpha=0.30, zorder=1)
    axB.axvspan(-90, -72.6, color="#dddddd", alpha=0.55, zorder=1)
    axB.annotate("comb undefined\nbelow -72.6 deg", (-81.3, 30), ha="center", va="center",
                 fontsize=10.2, color="#555555")
    axB.set_ylabel("Comb contrast below the ceiling [dB]")
    axB.set_title("(b) Same cliff on the second, independent ruler")
    axB.set_ylim(-12, 64)

    # ── (c) three airframes, PathSolver all-off, margin over own null ─────
    for d in DRONES:
        arm = ARMS["ps_alloff"]["by_drone"][d]
        pts = [c for c in cells.values() if c["arm"] == arm
               and "f_tip_zero_nadir" not in c["degenerate"]]
        pts.sort(key=lambda c: -c["el_deg"])
        xs = [c["el_deg"] for c in pts]
        ys = [c["margin_rhythm_pp"] for c in pts]
        nn = [c["el_deg"] in NEW_ELS for c in pts]
        _plot(axC, xs, ys, nn, DCOL[d], f"{d}  (own null {pts[0]['rhythm_null_pct']:.1f} %)")
    axC.axhline(0.0, color="#444444", ls=":", lw=2.0, zorder=2)
    xs_b = np.array([0, -15, -30, -45, -52, -60, -68, -75, -82], float)
    yb = np.array([bands_at(float(e))["rhythm_pp"] for e in xs_b], float)
    axC.fill_between(xs_b, -yb, yb, color="#bbbbbb", alpha=0.55, zorder=1,
                     label="grid-dispersion band: undecidable")
    axC.axvspan(-15, 0, color="#f2c14e", alpha=0.30, zorder=1)
    axC.annotate("S1000+ clears its own null\nalready at 0 deg: no boundary", (-19, 34),
                 ha="right", va="center", fontsize=10.2, color="#1f77b4", fontweight="bold")
    axC.annotate("-90 omitted (ruler degenerates)", (-88, -12.0), fontsize=9.6,
                 color="#666666", ha="left", va="center")
    axC.set_ylabel("Rhythm share minus that cell's own null [%p]")
    axC.set_title("(c) PathSolver all-off: whether there is a boundary depends on the airframe")
    axC.set_ylim(-16, 122)
    axC.legend(loc="upper left", framealpha=0.95)

    # ── (d) mechanism: whole scene vs rotor-only scene ────────────────────
    els = [m["el_deg"] for m in mech]
    full = [m["full_scene_ac_db"] for m in mech]
    rot = [m["rotor_only_ac_db"] for m in mech]
    axD.plot(els, full, "-o", color="#d62728", lw=2.0, ms=8.0, zorder=4,
             label="whole scene (body + rotors)")
    axD.plot(els, rot, "-s", color="#1f77b4", lw=2.0, ms=8.0, zorder=3,
             label="rotors only (same spin)")
    for m in mech:
        top = max(m["full_scene_ac_db"], m["rotor_only_ac_db"])
        ha = "right" if m["el_deg"] > -5 else ("left" if m["el_deg"] < -85 else "center")
        dx = -1.5 if ha == "right" else (1.5 if ha == "left" else 0.0)
        axD.annotate(f"{m['flicker_excess_db']:+.1f} dB", (m["el_deg"] + dx, top + 3.0),
                     ha=ha, va="bottom", fontsize=10.6,
                     color="#8a0000" if m["flicker_excess_db"] > 3 else "#333333",
                     fontweight="bold" if m["flicker_excess_db"] > 3 else "normal")
    axD.axvspan(-15, 0, color="#f2c14e", alpha=0.30, zorder=1)
    axD.annotate("at 0 deg the moving echo is not the rotors:\nit is body-occlusion flicker,"
                 " 52 dB louder", (-52, -97), ha="center", va="center", fontsize=10.4,
                 color="#8a0000")
    axD.annotate("elsewhere the two curves sit on top of each other:\n"
                 "what moves is exactly the rotors", (-52, -146), ha="center", va="center",
                 fontsize=10.4, color="#333333")
    axD.set_ylabel("DC-removed AC level [dB]")
    axD.set_title("(d) Why it drowns: only the frontal cell has a non-rotor driver")
    axD.set_ylim(-156, -84)
    axD.legend(loc="center right", framealpha=0.95)

    for ax in (axA, axB, axC, axD):
        ax.set_xlim(-93, 3)
        ax.set_xticks([0, -15, -30, -45, -52, -60, -68, -75, -82, -90])
        ax.set_xticklabels(["0", "-15", "-30", "-45", "-52", "-60", "-68", "-75", "-82", "-90"],
                           fontsize=9.4)
        ax.set_xlabel("Elevation [deg]   (0 = horizontal look, -90 = straight down)")
        ax.grid(alpha=0.3)
    h = [Line2D([0], [0], color=COL[k], lw=2.4,
                ls="--" if k == "ps_phys" else "-") for k in
         ("ours", "ps_alloff", "ps_refr", "ps_phys")]
    h.append(Line2D([0], [0], marker="D", ms=9.5, mfc="white", mec="#333333", mew=2.0,
                    ls="none"))
    lab = [ARMS[k]["en"] for k in ("ours", "ps_alloff", "ps_refr", "ps_phys")]
    lab.append("open diamond = new elevation (-52, -68, -82)")
    fig.legend(h, lab, loc="lower center", ncol=5, frameon=False, fontsize=10.2,
               bbox_to_anchor=(0.5, 0.004), columnspacing=1.4, handlelength=2.2)
    fig.suptitle("Where the frontal regime ends: 10-point elevation curves at 15 m, 3.5 GHz",
                 fontsize=15.5, y=0.985)
    fig.tight_layout(rect=(0, 0.042, 1, 0.955))
    fig.savefig(FIGP, dpi=145)
    plt.close(fig)
    return FIGP


if __name__ == "__main__":
    main()
