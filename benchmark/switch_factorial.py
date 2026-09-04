# -*- coding: utf-8 -*-
"""
switch_factorial.py — **R13 · 스위치 완전요인을 절대 dB 로 분해**
(설계서 `docs/NEXT_EXPERIMENTS.md` 4 위 · ⑥ 표 3 번)

■ 묻는 것 두 가지
    ① 회절(D)이 리듬을 **지우나**, 아니면 리듬 없는 에코를 얹어 **덮나**.
    ② 반사 깊이 축(`--max-depth`)은 살아 있나.

■ 왜 절대 dB 인가
    지금 이 자리의 헤드라인(리포트 18 · `outputs/switch_grid.json`)은 **몫(비율)** 하나 위에 서
    있다. 「회절이 든 조합은 리듬 몫 11.7~13.2 % 로 잡음이 된다」는 문장은 분자(빗살)가 줄어서
    그렇게 된 것인지, 분모(바닥)가 커져서 그렇게 된 것인지 **구별하지 못한다**. 그래서 이 실험은
    같은 원장을 **절대 dB 세 열**로 다시 적는다.

      ① DC 제거 AC          — 정지성분(시계열 평균)을 뺀 요동 전력
      ② 상한 위 **바닥**    — |f| ≥ f_tip(el) 에서 빗살 밖 빈의 전력 합
      ③ 상한 위 **빗살 선** — 같은 영역에서 f_flash 정수배 ±8 Hz 빈의 전력 합
                              (＋국소 바닥을 뺀 **선 초과분**과 **선/바닥 대비**를 함께 적는다)

■ 사전등록 판정 (설계서 그대로)
    A. 회절이 «바닥만 올리고 빗살 선은 그대로» 면 ⇒ «회절이 지운다» 를
       «회절이 리듬 없는 에코를 얹어 덮는다» 로 고친다.
    B. 깊이 1↔3 쌍 **전부**에서 레벨 차 < 2 dB 이고 리듬 차 < 3 %p 면 ⇒ **깊이 축 종결**.

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt·mitsuba 임포트 없음)
    outputs/elevation_sweep_md.json    행(팔·앙각·f_tip·결측·출처)
    outputs/elevation_sweep_md.npz     시계열 — 키 "<팔>/el<±NN>"
    outputs/elev_sweep_shards/*.npz    교차확인 · cfg 비트 검증 · 0 에코 증명
    outputs/switch_grid.json           옛 몫 원장(재현 게이트 · 정정 대상)

■ 굽는 것 (전부 새 파일)
    outputs/switch_factorial.json
    outputs/figures/switch_factorial_abs_db.png       ⭐주 그림 — 조합 축 × 세 열 막대
    outputs/figures/switch_factorial_elevation.png    보조 — 앙각별 세 열

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/switch_factorial.py
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import re

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402
from matplotlib.patches import Patch                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
LEDJ = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDN = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
OLDJ = os.path.join(ROOT, "outputs", "switch_grid.json")
OUTJ = os.path.join(ROOT, "outputs", "switch_factorial.json")
FIG1 = os.path.join(ROOT, "outputs", "figures", "switch_factorial_abs_db.png")
FIG2 = os.path.join(ROOT, "outputs", "figures", "switch_factorial_elevation.png")

HALF_HZ = 8.0          # 빗살 반폭 — 표준 레시피
DB_SAME = 2.0          # 사전등록 B: 레벨 «같다» 밴드
PP_SAME = 3.0          # 사전등록 B: 리듬 «같다» 밴드 [%p]

# ═══════════════════════════════════════════════════════════════════════════
# 0. 이름 대조표 — 꼬리표 없는 팔이 어느 조합인가
#    (근거: benchmark/elevation_sweep_md.py 의 --sw / --stock / --only / --physics 분기.
#     확산반사 F 는 스윕의 상수(켬)이고, --sw 와 --stock 만 그것을 바꾼다.)
# ═══════════════════════════════════════════════════════════════════════════
EQUIV = {
    "sionna_p4000000000_r15_n8192_d1":
        ("R0D0E0F1", 1, "꼬리표 없는 기본 — 스위치 전부 끔 · 확산 켬 · 깊이 1"),
    "sionna_p4000000000_onlyrefr_r15_n8192":
        ("R1D0E0F1", 1, "--only refr"),
    "sionna_p4000000000_onlydiffr_r15_n8192":
        ("R0D1E0F1", 1, "--only diffr"),
    "sionna_p4000000000_onlyedge_r15_n8192":
        ("R0D0E1F1", 1, "--only edge"),
    "sionna_p4000000000_onlydepth3_r15_n8192":
        ("R0D0E0F1", 3, "--only depth3 — 기본 조합의 깊이 3 짝"),
    "sionna_p4000000000_phys_r15_n8192_d1":
        ("R1D1E1F1", 1, "--physics --max-depth 1"),
    "sionna_p4000000000_phys_r15_n8192_d2":
        ("R1D1E1F1", 2, "--physics --max-depth 2 (깊이 2 — 보조)"),
    "sionna_p4000000000_stockdef_r15_n8192":
        ("R1D0E0F0", 3, "--stock 순정 기본값 — 굴절 켬 · 확산 끔 · 깊이 3"),
}
#: ⭐2026-08-27 확장 — 기체 토큰과 정본 메쉬 꼬리표를 받는다.
#  옛 이름(`..._r15_n8192_d1`)도 그대로 잡히므로 기존 판독은 안 깨진다.
#  ⛔로터 프리셋(`_rotoutdoor_v2`)은 **일부러 안 받는다** — 요인표에 로터 열이 없어
#    섞이면 축차이가 로터 효과와 뒤엉킨다.
SW_RE = re.compile(
    r"^sionna_p4000000000_sw(R[01]D[01]E[01]F[01])"
    r"(?:_(?:mavic4pro|mini5pro|s1000plus))?"
    r"_r15_n8192(?:_mfixbatteryi5_blperairframe)?_d(\d)$")
REF_ARMS = {
    "ours_r15_n8192": "우리 커널 (SBR+PO, 스위치·깊이 개념 없음)",
    #: ⭐정본 메쉬 판 — 덱 매트릭스가 쓰는 이름(2026-08-27 추가)
    "ours_r15_n8192_mfixbatteryi5_blperairframe": "우리 커널 (정본 메쉬)",
    "ours_mavic4pro_r15_n8192_mfixbatteryi5_blperairframe": "우리 커널 · mavic4pro",
    "ours_mini5pro_r15_n8192_mfixbatteryi5_blperairframe": "우리 커널 · mini5pro",
    "ours_s1000plus_r15_n8192_mfixbatteryi5_blperairframe": "우리 커널 · s1000plus",
}
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)


def combo_of(arm: str):
    """팔 이름 → (조합태그, 깊이, 근거). 스위치 격자 밖이면 None."""
    if arm in EQUIV:
        t, d, why = EQUIV[arm]
        return t, d, why
    m = SW_RE.match(arm)
    if m:
        return m.group(1), int(m.group(2)), f"--sw {m.group(1)} --max-depth {m.group(2)}"
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 1. 잣대 — 표준 레시피 그대로, 다만 **절대 dB** 로 정규화한다
# ═══════════════════════════════════════════════════════════════════════════
def rhythm_share_ref(E, prf, ffl, ft, hw=HALF_HZ):
    """⭐대조용 — build_switch_grid_figs.py:rhythm_share 와 **같은 식**(독립 구현)."""
    E = np.asarray(E, complex)
    n = E.size
    P = np.abs(np.fft.fft((E - E.mean()) * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= ft
    k = np.round(np.abs(fr) / ffl)
    on = np.abs(np.abs(fr) - k * ffl) <= hw
    tot = P[above].sum()
    return float(100.0 * P[above & on].sum() / tot) if tot > 0 else None


def db(v):
    return None if (v is None or not np.isfinite(v) or v <= 0) else round(float(10 * np.log10(v)), 2)


def columns(E, prf, ffl, ft, hw=HALF_HZ):
    """세 열 + 파생. 전력 단위는 원장의 진폭 단위² (rows[].level_db 와 같은 눈금)."""
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    w = np.hanning(n)
    # ⭐Parseval 정규화 — sum(P) ≈ mean(|x|²) 가 되게 창 에너지로 나눈다.
    #   그래야 각 열이 «시계열의 절대 요동 전력» 과 같은 눈금에 선다.
    P = np.abs(np.fft.fft(x * w)) ** 2 / (n * np.sum(w ** 2))
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= ft
    k = np.round(np.abs(fr) / ffl)
    on = np.abs(np.abs(fr) - k * ffl) <= hw
    m_fl, m_cb = above & ~on, above & on
    nb_f, nb_c = int(m_fl.sum()), int(m_cb.sum())
    p_fl, p_cb = float(P[m_fl].sum()), float(P[m_cb].sum())
    p_ab = p_fl + p_cb
    ac_t = float(np.mean(np.abs(x) ** 2))
    dens_f = p_fl / nb_f if nb_f else np.nan
    dens_c = p_cb / nb_c if nb_c else np.nan
    excess = p_cb - dens_f * nb_c                      # 국소 바닥을 뺀 «선» 초과분
    # 창가중 시간평균 — Parseval 항등식의 시간축 쪽(스펙트럼 합과 **정확히** 같아야 한다)
    ac_w = float(np.sum(np.abs(x * w) ** 2) / np.sum(w ** 2))
    out = dict(
        # ── ① ② ③ 세 열 (절대 dB) ────────────────────────────────────────
        ac_db=db(ac_t),
        above_floor_db=db(p_fl),
        above_comb_db=db(p_cb),
        # ── 파생 ───────────────────────────────────────────────────────────
        above_total_db=db(p_ab),
        above_comb_line_db=db(excess) if excess > 0 else None,
        comb_over_floor_db=(round(float(10 * np.log10(dens_c / dens_f)), 2)
                            if (nb_f and nb_c and dens_f > 0 and dens_c > 0) else None),
        floor_density_db=db(dens_f),
        rhythm_share_pct=(round(100.0 * p_cb / p_ab, 2) if p_ab > 0 else None),
        # ── 자가검사용 ─────────────────────────────────────────────────────
        ac_spec_db=db(float(P.sum())), ac_windowed_db=db(ac_w),
        n_bins_above=int(above.sum()), n_bins_comb=nb_c, n_bins_floor=nb_f,
        n_poses=int(n), f_tip_hz=round(float(ft), 1),
        zero_echo=bool(not np.any(E)),
    )
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 2. 원장 읽기
# ═══════════════════════════════════════════════════════════════════════════
def mtime(p):
    return _dt.datetime.fromtimestamp(os.path.getmtime(p),
                                      _dt.timezone(_dt.timedelta(hours=9))
                                      ).strftime("%Y-%m-%d %H:%M KST")


def shard_cfg(arm, el):
    """샤드 하나에서 cfg 를 읽는다 — [range, max_depth, spp, physics, R, D, E]."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None, 0
    z = np.load(fs[0])
    c = np.asarray(z["cfg"], float) if "cfg" in z else None
    return (None if c is None else c.tolist()), len(fs)


def shard_assemble(arm, el):
    """샤드를 idx 로 제자리에 꽂는다 — analyse() 와 같은 조립 규칙(교차확인용)."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None, None, 0.0
    E = None
    npa, secs = [], 0.0
    for f in fs:
        z = np.load(f)
        if E is None:
            E = np.zeros(int(np.asarray(z["meta"], float)[3]), complex)
        E[z["idx"].astype(int)] = z["E"]
        secs += float(np.asarray(z["meta"], float)[5])
        if "npaths" in z:
            npa.append(z["npaths"])
        z.close()
    return E, (np.concatenate(npa) if npa else None), secs


def main() -> None:
    J = json.load(open(LEDJ, encoding="utf-8"))
    M, ROWS = J["_meta"], J["rows"]
    PRF, FFL = float(M["prf_hz"]), float(M["f_flash_hz"])
    Z = np.load(LEDN)

    # 행 색인 — (팔, 앙각) → 행 번호
    ridx = {(r["engine"], float(r["el_deg"])): i for i, r in enumerate(ROWS)}

    print(f"\n═══ R13 · 스위치 완전요인 → 절대 dB 세 열 ═══")
    print(f"원장 {os.path.basename(LEDJ)} ({mtime(LEDJ)}) · PRF {PRF:.0f} Hz · "
          f"f_flash {FFL:.2f} Hz · 빗살 반폭 ±{HALF_HZ:.0f} Hz\n")

    # ── 2-1. 채점할 팔 고르기 ───────────────────────────────────────────────
    cells, refs, other_drone, gates = {}, {}, {}, []
    combos_seen = {}
    for i, r in enumerate(ROWS):
        arm, el = r["engine"], float(r["el_deg"])
        key_np = f"{arm}/el{el:+.0f}"
        if key_np not in Z.files:
            continue
        c = combo_of(arm)
        is_ref = arm in REF_ARMS
        # 다른 기체(mini5pro·s1000plus)는 f_tip 이 달라 완전요인 표와 나란히 못 놓는다.
        # ⭐mavic4pro 가 빠져 있었다(2026-08-27) — 기체 넷이 다 들어와야 한다.
        other = any(k in arm for k in ("mavic4pro", "mini5pro", "s1000plus"))
        if not (c or is_ref or (other and "_sw" in arm)):
            continue
        ft = float(r["f_tip_hz"])
        col = columns(Z[key_np], PRF, FFL, ft)
        col.update(arm=arm, el_deg=el, ledger_row=i, npz_key=key_np,
                   n_missing=int(r["n_missing"]), seconds=r["seconds"],
                   range_m=r["range_m"], ledger_level_db=r["level_db"],
                   ledger_max_depth=r["max_depth"], spp=r["spp"],
                   npaths_median=r["npaths_median"])
        col["rhythm_share_ref_pct"] = rhythm_share_ref(Z[key_np], PRF, FFL, ft)
        col["above_is_degenerate"] = bool(ft <= 1.0)      # el −90 은 f_tip = 0
        if other and "_sw" in arm:
            other_drone[key_np] = col
            continue
        if is_ref:
            col["what_ko"] = REF_ARMS[arm]
            refs[key_np] = col
            continue
        tag, dep, why = c
        col.update(combo=tag, depth=dep, provenance_ko=why,
                   refraction=tag[1] == "1", diffraction=tag[3] == "1",
                   edge_diffraction=tag[5] == "1", diffuse=tag[7] == "1")
        cells[f"{tag}_d{dep}/el{el:+.0f}"] = col
        combos_seen.setdefault((tag, dep), []).append(el)

        # ⭐게이트 — 샤드 cfg 의 R·D·E·깊이가 배정한 태그와 맞나 (F 는 cfg 에 자리가 없다)
        #   ⚠옛 샤드는 cfg 가 4 칸(거리·깊이·광선·물리)뿐이다 — 그때는 깊이만 검증한다.
        cfg, nsh = shard_cfg(arm, el)
        ok, scope = None, "cfg 없음 — 검증 불가"
        if cfg is not None and len(cfg) >= 7:
            ok = bool(int(cfg[1]) == dep and int(cfg[4]) == int(tag[1])
                      and int(cfg[5]) == int(tag[3]) and int(cfg[6]) == int(tag[5]))
            scope = "깊이 + R·D·E 비트"
        elif cfg is not None and len(cfg) >= 4:
            ok = bool(int(cfg[1]) == dep
                      and bool(cfg[3]) == (tag == "R1D1E1F1"))
            scope = "깊이 + physics 플래그(옛 4칸 cfg — R·D·E 개별비트 없음)"
        gates.append(dict(cell=f"{tag}_d{dep}/el{el:+.0f}", arm=arm, n_shards=nsh,
                          cfg=cfg, cfg_len=(None if cfg is None else len(cfg)),
                          checked_ko=scope, cfg_matches_tag=ok))

    print(f"채점 칸 {len(cells)} · 기준 팔 {len(refs)} · 다른 기체 스위치 팔 {len(other_drone)}")

    # ── 2-2. 완전요인 완성도 (el −30 = 유일하게 격자가 다 사는 자리) ─────────
    all16 = [f"R{r}D{d}E{e}F{f}" for r in (0, 1) for d in (0, 1)
             for e in (0, 1) for f in (0, 1)]
    grid30 = {}
    for dep in (1, 3):
        have = [t for t in all16 if f"{t}_d{dep}/el-30" in cells]
        grid30[f"depth{dep}"] = dict(present=have, missing=[t for t in all16 if t not in have],
                                     n_present=len(have))
    print(f"el −30 완전요인: 깊이1 {grid30['depth1']['n_present']}/16 · "
          f"깊이3 {grid30['depth3']['n_present']}/16")

    # ── 2-3. 0 에코 칸 — «계산했는데 경로가 0» 인지 증명한다 ────────────────
    zero_proof = {}
    for k, c in cells.items():
        if not c["zero_echo"]:
            continue
        E, npa, secs = shard_assemble(c["arm"], c["el_deg"])
        zero_proof[k] = dict(
            arm=c["arm"], n_shards=len(glob.glob(f"{SHD}/{c['arm']}_el{c['el_deg']:+.0f}_*.npz")),
            npaths_sum=(int(npa.sum()) if npa is not None else None),
            seconds=round(secs, 1), all_E_zero=bool(E is not None and not np.any(E)),
            computed_not_missing=bool(npa is not None and int(npa.sum()) == 0 and secs > 0))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. 축별 차이표 — 한 비트만 다른 칸끼리
    # ═══════════════════════════════════════════════════════════════════════
    AXIS = {"R": 1, "D": 3, "E": 5, "F": 7}

    def flip(tag, ax):
        i = AXIS[ax]
        return tag[:i] + ("0" if tag[i] == "1" else "1") + tag[i + 1:]

    def dd(a, b):
        return None if (a is None or b is None) else round(b - a, 2)

    axis_tbl = {ax: [] for ax in AXIS}
    for key, c in cells.items():
        tag, rest = key.split("_d")
        dep, elk = rest.split("/")
        for ax in AXIS:
            if tag[AXIS[ax]] != "0":          # 0→1 방향만 한 번씩
                continue
            k1 = f"{flip(tag, ax)}_d{dep}/{elk}"
            if k1 not in cells:
                continue
            o, n = c, cells[k1]
            row = dict(off=key, on=k1, el_deg=o["el_deg"], depth=int(dep),
                       d_ac_db=dd(o["ac_db"], n["ac_db"]),
                       d_above_floor_db=dd(o["above_floor_db"], n["above_floor_db"]),
                       d_above_comb_db=dd(o["above_comb_db"], n["above_comb_db"]),
                       d_comb_over_floor_db=dd(o["comb_over_floor_db"], n["comb_over_floor_db"]),
                       d_rhythm_pp=(None if (o["rhythm_share_pct"] is None
                                             or n["rhythm_share_pct"] is None)
                                    else round(n["rhythm_share_pct"] - o["rhythm_share_pct"], 2)),
                       off_zero_echo=o["zero_echo"], on_zero_echo=n["zero_echo"])
            # ⭐덮개 시험 — 켠 판이 끈 판을 **계수 1 로 품고 있나** (지움 vs 덮음)
            if not o["zero_echo"] and not n["zero_echo"]:
                e0 = np.asarray(Z[o["npz_key"]], complex)
                e1 = np.asarray(Z[n["npz_key"]], complex)
                e0 = e0 - e0.mean()
                e1 = e1 - e1.mean()
                a = np.vdot(e0, e1) / np.vdot(e0, e0)
                res = e1 - e0
                # ⭐계수 1 의 불확도 — 얹힌 항 N 이 끈 판과 무상관이라 보면
                #   a = 1 + <e0,N>/||e0||² 이고 표준편차는 (||N||/||e0||)/√n 이다.
                sig = float(np.linalg.norm(res) / (np.linalg.norm(e0) * np.sqrt(e0.size)))
                row.update(
                    contain_coeff=round(float(abs(a)), 4),
                    contain_phase_deg=round(float(np.degrees(np.angle(a))), 2),
                    contain_sigma=round(sig, 4),
                    contain_dev_sigma=(round(float(abs(abs(a) - 1.0) / sig), 2)
                                       if sig > 0 else None),
                    contains_unit_within_3sigma=bool(sig > 0 and abs(abs(a) - 1.0) <= 3 * sig),
                    coh_rho=round(float(abs(np.vdot(e0, e1))
                                        / (np.linalg.norm(e0) * np.linalg.norm(e1))), 4),
                    coh_rho_null=round(float(1.0 / np.sqrt(e0.size)), 4),
                    residual_ac_db=db(float(np.mean(np.abs(res) ** 2))),
                    orthogonal_pred_db=db(max(float(np.mean(np.abs(e1) ** 2)
                                                    - np.mean(np.abs(e0) ** 2)), 0.0)),
                    residual_rhythm_pct=(None if rhythm_share_ref(res, PRF, FFL, o["f_tip_hz"])
                                         is None else
                                         round(rhythm_share_ref(res, PRF, FFL,
                                                                o["f_tip_hz"]), 2)))
            axis_tbl[ax].append(row)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. 사전등록 판정 A — 회절은 지우나 덮나
    # ═══════════════════════════════════════════════════════════════════════
    #: ⭐판정 판(plate)은 설계서가 정한 **el −30** 이다(«입력: el −30 의 sw 팔 전량»).
    #   다른 앙각의 쌍은 «적용 범위» 로 따로 적는다 — 판정에 섞지 않는다.
    dall = [r for r in axis_tbl["D"] if not r["off_zero_echo"] and not r["on_zero_echo"]]
    dpairs = [r for r in dall if r["el_deg"] == -30.0]
    dscope = [r for r in dall if r["el_deg"] != -30.0]
    dzero = [r for r in axis_tbl["D"] if r["off_zero_echo"]]
    lit_floor = [r["d_above_floor_db"] for r in dpairs]
    lit_comb = [r["d_above_comb_db"] for r in dpairs]
    lit_line = [r["d_comb_over_floor_db"] for r in dpairs]
    a_literal = bool(dpairs and all(v is not None and v >= DB_SAME for v in lit_floor)
                     and all(v is not None and abs(v) < DB_SAME for v in lit_comb))
    # 선/바닥 대비로 읽은 판 — «선» 은 국소 바닥 위 솟음이지 빈 총합이 아니다
    a_line = bool(dpairs and all(v is not None and v >= DB_SAME for v in lit_floor)
                  and all(v is not None and v <= -DB_SAME for v in lit_line))
    a_cover = bool(dpairs and all(r.get("contains_unit_within_3sigma") for r in dpairs))
    a_white = bool(dpairs and all(r.get("residual_rhythm_pct") is not None
                                  and 9.0 <= r["residual_rhythm_pct"] <= 17.0 for r in dpairs))
    a_cover_all_el = bool(dall and all(r.get("contains_unit_within_3sigma") for r in dall))
    # 덮힘 깊이 — 끈 판의 «선» 이 켠 판의 바닥 밑 몇 dB 로 내려앉나
    burial = []
    for r in dpairs:
        o, n = cells[r["off"]], cells[r["on"]]
        if o["above_comb_db"] is None or n["floor_density_db"] is None:
            continue
        fl_in_comb = n["floor_density_db"] + 10 * np.log10(max(n["n_bins_comb"], 1))
        burial.append(dict(pair=f"{r['off']} → {r['on']}",
                           off_comb_db=o["above_comb_db"],
                           on_floor_in_comb_bins_db=round(float(fl_in_comb), 2),
                           burial_depth_db=round(float(fl_in_comb - o["above_comb_db"]), 2)))

    # ⭐축마다 «얹나 바꾸나» — 담김계수 a 가 1 이면 얹은 것(원래 항이 그대로 남았다),
    #   1 보다 작으면 원래 항 자체를 바꾼 것이다. 회절만 유별난지 이 표가 말한다.
    mech = {}
    for ax in AXIS:
        v = [r["contain_coeff"] for r in axis_tbl[ax]
             if r["el_deg"] == -30.0 and r.get("contain_coeff") is not None]
        if not v:
            continue
        mech[ax] = dict(
            n_pairs=len(v), a_min=round(min(v), 3), a_max=round(max(v), 3),
            a_median=round(float(np.median(v)), 3),
            reads_ko=("얹는다 — 원래 시계열이 계수 1 로 그대로 남아 있다"
                      if min(v) >= 0.9 and max(v) <= 1.25 else
                      "바꾼다 — 원래 시계열 자체가 다른 것이 된다"))
    mech_note = ("⭐축을 가르는 한 줄: 회절 D 와 모서리 E 와 확산 F 는 **얹는 축**(a≈1)이고, "
                 "굴절 R 만 **바꾸는 축**(a≈0.5)이다. 굴절은 셸을 통과시켜 원래 반사 자체를 "
                 "다른 것으로 만들고, 회절은 원래 반사를 남긴 채 위에 새 항을 더한다.")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. 사전등록 판정 B — 깊이 축
    # ═══════════════════════════════════════════════════════════════════════
    depth_pairs, dead_pairs = [], []
    for (tag, dep), els in sorted(combos_seen.items()):
        if dep != 1:
            continue
        for hi in (3, 2):
            if (tag, hi) not in combos_seen:
                continue
            for el in sorted(set(els) & set(combos_seen[(tag, hi)])):
                k1, k3 = f"{tag}_d1/el{el:+.0f}", f"{tag}_d{hi}/el{el:+.0f}"
                a, b = cells[k1], cells[k3]
                if a["zero_echo"] and b["zero_echo"]:
                    dead_pairs.append(dict(combo=tag, el_deg=el, depths=[1, hi],
                                           note_ko="두 판 모두 경로 0 — 깊이가 바꿀 것이 없다"))
                    continue
                row = dict(combo=tag, el_deg=el, depths=[1, hi], d1=k1, dN=k3,
                           d_ac_db=dd(a["ac_db"], b["ac_db"]),
                           d_above_floor_db=dd(a["above_floor_db"], b["above_floor_db"]),
                           d_above_comb_db=dd(a["above_comb_db"], b["above_comb_db"]),
                           d_rhythm_pp=(None if (a["rhythm_share_pct"] is None
                                                 or b["rhythm_share_pct"] is None)
                                        else round(b["rhythm_share_pct"]
                                                   - a["rhythm_share_pct"], 2)),
                           d_ledger_level_db=round(b["ledger_level_db"]
                                                   - a["ledger_level_db"], 2))
                lv = [abs(v) for v in (row["d_ac_db"], row["d_above_floor_db"],
                                       row["d_above_comb_db"], row["d_ledger_level_db"])
                      if v is not None]
                row["max_abs_level_db"] = round(max(lv), 2) if lv else None
                row["level_within_2db"] = bool(lv and max(lv) < DB_SAME)
                row["rhythm_within_3pp"] = bool(row["d_rhythm_pp"] is not None
                                                and abs(row["d_rhythm_pp"]) < PP_SAME)
                row["pass"] = bool(row["level_within_2db"] and row["rhythm_within_3pp"])
                depth_pairs.append(row)
    p13 = [r for r in depth_pairs if r["depths"] == [1, 3]]
    p13_plate = [r for r in p13 if r["el_deg"] == -30.0]
    p12 = [r for r in depth_pairs if r["depths"] == [1, 2]]
    b_pass = bool(p13 and all(r["pass"] for r in p13))
    b_pass_plate = bool(p13_plate and all(r["pass"] for r in p13_plate))
    b_fail_rows = [dict(combo=r["combo"], el_deg=r["el_deg"],
                        max_abs_level_db=r["max_abs_level_db"], d_rhythm_pp=r["d_rhythm_pp"],
                        d_above_floor_db=r["d_above_floor_db"],
                        broke_ko=("리듬" if not r["rhythm_within_3pp"] else "레벨"))
                   for r in p13 if not r["pass"]]

    # ═══════════════════════════════════════════════════════════════════════
    # 6. 대조군 — 백색잡음 / 이상 로터
    # ═══════════════════════════════════════════════════════════════════════
    n0 = 8192
    ft30 = next((c["f_tip_hz"] for k, c in cells.items() if k.endswith("/el-30")), 1102.4)
    rng = np.random.default_rng(13)
    ws = [rhythm_share_ref(rng.normal(size=n0) + 1j * rng.normal(size=n0), PRF, FFL, ft30)
          for _ in range(200)]
    t = np.arange(n0) / PRF
    kmax = int(0.98 * (PRF / 2) / FFL)
    ideal = np.zeros(n0, complex)
    for k in range(1, kmax + 1):
        ideal += np.exp(2j * np.pi * k * FFL * t)
    ctrl = dict(
        white_share_pct_mean=round(float(np.mean(ws)), 2),
        white_share_pct_std=round(float(np.std(ws)), 2), white_draws=len(ws),
        white_expected_from_bin_count_pct=None,
        ideal_comb_share_pct=round(float(rhythm_share_ref(ideal, PRF, FFL, ft30)), 2),
        ideal_comb_k_max=kmax,
        note_ko="백색의 몫은 «빗살 빈이 상한 위 전체 빈에서 차지하는 비율» 로 수렴한다 — "
                "그것이 설계서가 말한 «백색 ≈ 13» 의 정체다")
    any30 = next((c for k, c in cells.items() if k.endswith("/el-30")), None)
    if any30:
        ctrl["white_expected_from_bin_count_pct"] = round(
            100.0 * any30["n_bins_comb"] / any30["n_bins_above"], 2)

    # ═══════════════════════════════════════════════════════════════════════
    # 7. 자가검사
    # ═══════════════════════════════════════════════════════════════════════
    sc = {}
    live = [c for c in list(cells.values()) + list(refs.values()) if not c["zero_echo"]]
    v = [abs(c["ac_windowed_db"] - c["ac_spec_db"]) for c in live
         if c["ac_windowed_db"] is not None and c["ac_spec_db"] is not None]
    g = [abs(c["ac_db"] - c["ac_spec_db"]) for c in live
         if c["ac_db"] is not None and c["ac_spec_db"] is not None]
    sc["parseval_identity"] = dict(
        max_abs_db=round(max(v), 6) if v else None, tol_db=0.001,
        pass_=bool(v and max(v) < 0.001),
        window_weighting_gap_max_db=round(max(g), 2) if g else None,
        note_ko="창가중 시간평균 ↔ 창정규화 스펙트럼 합은 **항등식**이라 정확히 같아야 한다. "
                "별도로 적은 window_weighting_gap 은 창을 안 씌운 평균과의 차이로, 시계열이 "
                "얼마나 비정상(non-stationary)인지를 말한다 — 잣대의 결함이 아니다.")
    e = []
    for c in live:
        if None in (c["above_floor_db"], c["above_comb_db"], c["above_total_db"]):
            continue
        s = 10 * np.log10(10 ** (c["above_floor_db"] / 10) + 10 ** (c["above_comb_db"] / 10))
        e.append(abs(s - c["above_total_db"]))
    sc["decomposition_floor_plus_comb"] = dict(
        max_abs_db=round(max(e), 4) if e else None, tol_db=0.02, pass_=bool(e and max(e) < 0.02))
    r = [abs(c["rhythm_share_pct"] - c["rhythm_share_ref_pct"]) for c in live
         if None not in (c["rhythm_share_pct"], c["rhythm_share_ref_pct"])]
    sc["share_matches_standard_recipe"] = dict(
        max_abs_pp=round(max(r), 6) if r else None, tol_pp=0.01, pass_=bool(r and max(r) < 0.01),
        note_ko="절대 dB 분해로 다시 만든 몫이 표준 레시피(=build_switch_grid_figs.rhythm_share)와 같나")
    sc["cfg_bits_match_tag"] = dict(
        n_checked=len(gates), n_pass=sum(1 for g in gates if g["cfg_matches_tag"]),
        n_no_cfg=sum(1 for g in gates if g["cfg"] is None),
        pass_=bool(gates and all(g["cfg_matches_tag"] for g in gates)),
        note_ko="샤드 cfg 의 굴절·회절·모서리·깊이가 이름에서 읽은 태그와 일치하나 "
                "(확산 F 는 cfg 에 자리가 없어 CLI 규칙에서 읽는다)")
    xs = []
    for k in list(cells)[:4] + list(refs)[:1]:
        c = (cells.get(k) or refs.get(k))
        E, _, _ = shard_assemble(c["arm"], c["el_deg"])
        if E is None:
            continue
        xs.append(float(np.max(np.abs(E - np.asarray(Z[c["npz_key"]], complex)))))
    sc["npz_vs_shards"] = dict(max_abs_diff=(float(max(xs)) if xs else None), n_checked=len(xs),
                               pass_=bool(xs and max(xs) == 0.0))
    sc["zero_cells_are_computed"] = dict(
        n=len(zero_proof), pass_=bool(zero_proof
                                      and all(z["computed_not_missing"]
                                              for z in zero_proof.values())),
        note_ko="0 에코 칸은 «안 돌린 칸» 이 아니라 «돌렸는데 경로가 0» 이다")
    miss = {k: c["n_missing"] for k, c in cells.items()
            if c["n_missing"] and not c["zero_echo"]}
    sc["no_missing_pose"] = dict(cells_with_missing=miss, pass_=bool(not miss))
    sc["white_control"] = dict(value_pct=ctrl["white_share_pct_mean"], band=[10.0, 16.0],
                               pass_=bool(10.0 <= ctrl["white_share_pct_mean"] <= 16.0))
    sc["ideal_comb_control"] = dict(value_pct=ctrl["ideal_comb_share_pct"], floor=99.0,
                                    pass_=bool(ctrl["ideal_comb_share_pct"] >= 99.0))
    # 옛 원장 재현
    rep = []
    if os.path.exists(OLDJ):
        old = json.load(open(OLDJ, encoding="utf-8"))
        for nm, oc in old["cells"].items():
            k = f"{oc['arm']}/el-30"
            mine = next((c for c in list(cells.values()) + list(refs.values())
                         if c["npz_key"] == k), None)
            if mine is None or mine["rhythm_share_pct"] is None:
                continue
            rep.append(dict(name=nm, arm=oc["arm"], old_pct=oc["rhythm_share_pct"],
                            new_pct=mine["rhythm_share_pct"],
                            diff_pp=round(mine["rhythm_share_pct"] - oc["rhythm_share_pct"], 2),
                            old_n_missing=oc["n_missing"], new_n_missing=mine["n_missing"]))
    sc["reproduces_switch_grid_json"] = dict(
        rows=rep, max_abs_diff_pp=(round(max(abs(x["diff_pp"]) for x in rep), 2) if rep else None),
        tol_pp=1.0, pass_=bool(rep and max(abs(x["diff_pp"]) for x in rep) <= 1.0),
        note_ko="옛 판은 f_tip 1101.6 Hz(report07_three_engines 유래), 이 판은 원장 행의 "
                "1102.4 Hz 를 쓴다 — 0.8 Hz 차이만큼 어긋난다")

    # ═══════════════════════════════════════════════════════════════════════
    # 8. 그림
    # ═══════════════════════════════════════════════════════════════════════
    figs = {}
    try:
        figs["abs_db"] = fig_factorial(cells, refs, all16)
    except Exception as ex:                                   # noqa: BLE001
        figs["abs_db"] = f"FAILED: {ex!r}"
    try:
        figs["elevation"] = fig_elevation(cells, refs)
    except Exception as ex:                                   # noqa: BLE001
        figs["elevation"] = f"FAILED: {ex!r}"
    sc["figures_written"] = dict(
        files={k: (os.path.getsize(p) if isinstance(p, str) and os.path.exists(p) else p)
               for k, p in figs.items()},
        pass_=bool(all(isinstance(p, str) and os.path.exists(p) and os.path.getsize(p) > 0
                       for p in figs.values())))
    sc["all_pass"] = bool(all(x.get("pass_") for x in sc.values() if isinstance(x, dict)))

    # ═══════════════════════════════════════════════════════════════════════
    # 9. 판정문 · 정정 대상
    # ═══════════════════════════════════════════════════════════════════════
    d_main = next((r for r in dpairs if r["off"] == "R0D0E0F1_d1/el-30"), None)
    verdict = dict(
        plate_ko="⭐판정은 설계서가 정한 판 — 앙각 −30° · matrice4e · 15 m · 광선 4e9 — 에서만 "
                 "내린다. 다른 앙각의 쌍은 «적용 범위(scope)» 로 따로 적는다.",
        A_prereg_text_ko="회절(D)이 «바닥만 올리고 빗살 선은 그대로» 면 «회절이 지운다» 를 "
                         "«회절이 리듬 없는 에코를 얹어 덮는다» 로 고친다",
        A_n_pairs_plate=len(dpairs), A_n_pairs_from_zero=len(dzero),
        A_literal_pass=a_literal,
        A_literal_why_ko="문자 그대로(빗살 **빈 총합**이 불변) 읽으면 **불성립**이다 — 올라온 바닥이 "
                         "빗살 빈 안에도 똑같이 들어차서 빈 총합이 +16~+22 dB 함께 올라간다. "
                         "이 정의로는 «선» 을 못 잰다.",
        A_line_pass=a_line,
        A_line_why_ko="«선» 을 국소 바닥 위 솟음(빗살 빈 밀도 ÷ 바닥 빈 밀도)으로 읽으면 성립한다 "
                      "— 바닥은 +27~+37 dB 오르고 선은 대비 0 dB(=백색)로 주저앉는다",
        A_cover_pass=a_cover, A_cover_pass_all_elevations=a_cover_all_el,
        A_cover_why_ko="회절을 켠 시계열은 끈 시계열을 **계수 1 (3σ 안) · 위상 ≈0°** 로 그대로 "
                       "품고 있고, 잔차 전력이 두 판 전력의 차와 일치한다(직교 합) — "
                       "지운 것이 아니라 얹은 것이다",
        A_residual_is_white_pass=a_white,
        A_residual_why_ko="얹힌 항(켠 판 − 끈 판)만 따로 재면 리듬 몫이 백색 밴드(9~17 %) 안이다 "
                          "— 얹힌 것에는 날개 박자가 없다",
        A_verdict_ko=("«회절이 리듬 없는 에코를 얹어 덮는다» 로 고친다"
                      if (a_line and a_cover and a_white) else "판정 보류 — 아래 수를 다시 읽어라"),
        A_scope_ko="⚠앙각 0° 는 예외다 — 거기서는 회절을 켜도 바닥이 +1.8 dB 밖에 안 오른다. "
                   "정면에서는 회절이 오기 전에 이미 동체 정반사의 몬테카를로 잡음이 상한 위를 "
                   "백색으로 채워 놨기 때문이다(끈 판의 몫이 이미 13.1 % = 백색). "
                   "덮개 문장은 **빗각(−15°~−75°)** 에서 쓴다.",
        B_prereg_text_ko="깊이 1↔3 쌍 전부에서 레벨 차 < 2 dB 이고 리듬 차 < 3 %p 면 깊이 축 종결",
        B_pass=b_pass, B_pass_on_plate_el30=b_pass_plate,
        B_n_pairs_1to3=len(p13), B_n_pairs_1to3_on_plate=len(p13_plate),
        B_n_pairs_1to2=len(p12), B_n_dead_pairs=len(dead_pairs),
        B_max_level_db=(round(max(r["max_abs_level_db"] for r in p13), 2) if p13 else None),
        B_max_rhythm_pp=(round(max(abs(r["d_rhythm_pp"]) for r in p13
                                   if r["d_rhythm_pp"] is not None), 2) if p13 else None),
        B_failures=b_fail_rows,
        B_verdict_ko=("깊이 축 종결 — 앞으로 큐에서 --max-depth 3 를 빼도 된다" if b_pass else
                      "⛔깊이 축 종결 **불가** — 큐에서 --max-depth 3 를 빼면 안 된다"),
        B_why_ko="두 가지로 깨진다. ①판 위(−30°)의 R1D1** 칸 넷이 깊이 3 에서 세 열 전부 "
                 "+2.2~+2.4 dB — 사전등록 2 dB 밴드 바로 밖이다. ②판 밖 −60° 의 R0D0E0F1 은 "
                 "AC 가 +0.09 dB 로 «같은데» 상한 위 바닥만 **+12.7 dB** 오른다 — 레벨 "
                 "잣대 하나로는 안 보이던 자리다. ⛔**여기 있던 «리듬이 86.6 → 32.4 % 로 "
                 "무너진다» 는 2026-08-16 에 철회됐다** — 그 낙차는 8,192 자세 중 **#3399 "
                 "하나 탓**이었고, 그 자세만 빼면 두 판이 리듬 85.52 대 85.24 % · 빗살 45.37 "
                 "대 45.29 dB 로 일치한다(RETRACTION_LOG 2026-08-16 ③). 그리고 리듬 몫 "
                 "크기 자체가 R29 로 인용 대상이 아니다.",
        B_lesson_ko="⭐깊이를 «레벨이 안 변하니 죽은 축» 이라 부른 근거가 레벨 하나였다는 것이 "
                    "이 실험의 부산물이다. 세 열로 갈라 보니 깊이는 **바닥을 올리는 축**이다.",
        C_edge_is_noop_ko="모서리회절 E 는 회절 D 가 꺼져 있으면 완전 무동작이다 — «모서리만» 은 "
                          "«다 끔» 과 세 열이 소수점까지 같다(담김계수 1.0000, axis_diffs.E)",
        E_axis_mechanism=mech, E_axis_mechanism_ko=mech_note,
        F_diffuse_keeps_it_alive_ko="확산 F 는 회절이 켜져 있으면 AC 를 0.1~0.4 dB 밖에 안 "
                                    "바꾸지만, 회절이 꺼져 있으면 **에코의 유무를 가른다** — "
                                    "빗각에서 살아 있는 유일한 경로원이다",
        D_no_diffuse_no_diffraction_zero_ko="확산 F 도 끄고 회절 D 도 끄면 빗각(−30°)에서 경로가 "
                                            "**0 개** 다 — 에코가 아예 없다(굴절 켜도 마찬가지). "
                                            "순정 기본값(stockdef=R1D0E0F0·d3)이 여기 걸린다.",
    )
    if d_main:
        verdict["A_headline_ko"] = (
            f"el −30 기본 칸에서 회절을 켜면 상한 위 **바닥은 {d_main['d_above_floor_db']:+.1f} dB** "
            f"오르는데 **선/바닥 대비는 {d_main['d_comb_over_floor_db']:+.1f} dB** 로 무너진다 — "
            f"그러면서도 켠 판은 끈 판을 계수 {d_main['contain_coeff']:.2f}"
            f"(±{d_main['contain_sigma']:.2f}) 로 품고 있고, 얹힌 항만 재면 리듬 몫이 "
            f"{d_main['residual_rhythm_pct']:.1f} %(백색)다")

    corrections = build_corrections(cells, refs, d_main, verdict, burial, rep, p13, dead_pairs)

    out = dict(
        _meta=dict(
            generator="benchmark/switch_factorial.py",
            experiment="R13 · 스위치 완전요인을 절대 dB 로 분해",
            design_doc="docs/NEXT_EXPERIMENTS.md (순위 4 · ⑥ 표 3 번)",
            written_at_kst=_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
            .strftime("%Y-%m-%d %H:%M KST"),
            question_ko="회절이 리듬을 지우나 아니면 리듬 없는 에코를 얹어 덮나 · 깊이 축은 살아 있나",
            gpu_used="0 — 저장된 원장만 읽는다(sionna.rt·mitsuba 임포트 없음)",
            sources=dict(
                ledger_json=dict(path="outputs/elevation_sweep_md.json", mtime=mtime(LEDJ),
                                 n_rows=len(ROWS)),
                ledger_npz=dict(path="outputs/elevation_sweep_md.npz", mtime=mtime(LEDN),
                                n_keys=len(Z.files)),
                shards=dict(path="outputs/elev_sweep_shards/", n_files=len(os.listdir(SHD))),
                old_ratio_ledger=dict(path="outputs/switch_grid.json",
                                      mtime=(mtime(OLDJ) if os.path.exists(OLDJ) else None))),
            plate_ko="matrice4e · 3.5 GHz · 15 m · 자세 8192 · 광선 4e9 · 확산/스위치만 갈린다",
            prf_hz=PRF, f_flash_hz=FFL, comb_half_width_hz=HALF_HZ,
            units_ko="세 열은 전부 **절대 dB** — 원장 시계열 진폭의 제곱 단위(행의 level_db 와 같은 눈금). "
                     "비율이 아니다.",
            recipe_ko="P = |FFT((E − mean(E))·hanning)|² 를 창 에너지 n·Σw² 로 나눠 Parseval 정규화. "
                      "above = |f| ≥ f_tip(el). 빗살 = |f| 가 f_flash 정수배 ±8 Hz. "
                      "바닥 = above 중 빗살 밖. 세 열은 ①mean|E−mean|² ②바닥 합 ③빗살 빈 합.",
            column_note_ko="③ 은 «빗살 빈 총합» 이라 올라온 바닥을 함께 담는다. 그래서 «선» 그 자체는 "
                           "above_comb_line_db(국소 바닥 뺀 초과분)와 comb_over_floor_db(빈 밀도 대비)로 읽는다.",
            prereg_deviation_ko=[
                "설계서는 «D 는 바닥만 올린다» 를 빗살 **총합** 불변으로 적었으나, 그 정의로는 바닥이 "
                "빗살 빈 안에도 들어차서 총합이 같이 오른다 — 물리적으로 «선» 이 아니다. 그래서 판정 A 를 "
                "①문자 그대로 ②선/바닥 대비 ③덮개 시험(계수 1 포함) 셋으로 갈라 전부 적었다.",
                "설계서의 «7 쌍» 은 sw 꼬리표만 센 수다. 꼬리표 없는 등가칸(기본↔onlydepth3, "
                f"onlyrefr↔swR1D0E0F1_d3 …)까지 세면 살아 있는 1↔3 쌍은 {len(p13)} 쌍, "
                f"두 판 모두 경로 0 인 죽은 쌍이 {len(dead_pairs)} 쌍이다.",
                "설계서의 «swR1D1E0F1_d1 은 n_missing=512» 는 이 원장에서 해소됐다(0). 결측 제외 없이 "
                "표에 실었다.",
                "판정 A 의 «그대로 / 올린다» 문턱은 설계서가 A 에는 안 줬으므로 B 의 2 dB 를 그대로 "
                "썼다(R16 산포 밴드가 아직 없다 — 밴드가 나오면 다시 읽어야 한다).",
            ],
            factorial_grid_el30=grid30,
            name_map=EQUIV, sw_name_rule="sionna_p4000000000_sw<RDEF>_r15_n8192_d<depth>",
            switch_meaning_ko=dict(R="굴절(refraction)", D="쐐기 회절(diffraction)",
                                   E="모서리 회절(edge_diffraction)", F="확산 반사(diffuse)"),
        ),
        headline=[
            verdict.get("A_headline_ko", ""),
            verdict["A_verdict_ko"], mech_note, verdict["B_verdict_ko"],
        ],
        verdict=verdict,
        controls=ctrl,
        cells=cells,
        reference_arms=refs,
        other_drone_switch_arms=other_drone,
        axis_diffs=axis_tbl,
        diffraction_on_plate_el30=dpairs,
        diffraction_scope_other_elevations=dscope,
        diffraction_burial=burial,
        diffraction_from_zero=dzero,
        depth_pairs=depth_pairs,
        depth_dead_pairs=dead_pairs,
        zero_echo_proof=zero_proof,
        cfg_gates=gates,
        selfcheck=sc,
        corrections=corrections,
        figures={k: (os.path.relpath(p, ROOT) if isinstance(p, str) and os.path.exists(p) else p)
                 for k, p in figs.items()},
    )
    json.dump(out, open(OUTJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (o.item() if hasattr(o, "item") else str(o)))

    # ── 콘솔 요약 ──────────────────────────────────────────────────────────
    print(f"\n{'칸':<22}{'AC':>9}{'바닥':>10}{'빗살빈':>10}{'선/바닥':>9}{'몫%':>7}")
    for k in sorted(cells, key=lambda s: (s.split("/")[1], s)):
        c = cells[k]
        if not k.endswith("/el-30"):
            continue
        f = lambda x, w=9: (f"{x:>{w}.2f}" if isinstance(x, (int, float)) else f"{'—':>{w}}")
        print(f"{k.split('/')[0]:<22}{f(c['ac_db'])}{f(c['above_floor_db'],10)}"
              f"{f(c['above_comb_db'],10)}{f(c['comb_over_floor_db'])}"
              f"{f(c['rhythm_share_pct'],7)}"
              + ("   ⛔경로 0" if c["zero_echo"] else ""))
    print(f"\n[판 el −30] D 쌍 {len(dpairs)} + 0에코출발 {len(dzero)} · 판정 A "
          f"문자그대로 {a_literal} · 선/바닥 {a_line} · 덮개 {a_cover} · 잔차백색 {a_white}")
    print(f"  ⇒ {verdict['A_verdict_ko']}")
    if d_main:
        print(f"  {verdict['A_headline_ko']}")
    print("축별 담김계수(el −30) — 1 이면 «얹는다», 1 미만이면 «바꾼다»")
    for ax, m in mech.items():
        print(f"    {ax}: a {m['a_min']:.2f}~{m['a_max']:.2f} (중앙 {m['a_median']:.2f}, "
              f"{m['n_pairs']} 쌍) — {m['reads_ko']}")
    print(f"판정 B 1↔3 {len(p13)} 쌍(판 위 {len(p13_plate)} · 죽은 쌍 {len(dead_pairs)}) "
          f"· 깨진 쌍 {len(b_fail_rows)} ⇒ {verdict['B_verdict_ko']}")
    for r in b_fail_rows:
        print(f"    ⛔ {r['combo']} el{r['el_deg']:+.0f} — 레벨 {r['max_abs_level_db']:+.2f} dB · "
              f"바닥 {r['d_above_floor_db']:+.2f} dB · 리듬 {r['d_rhythm_pp']:+.2f} %p")
    print(f"자가검사 전체통과 = {sc['all_pass']}")
    for k, v_ in sc.items():
        if isinstance(v_, dict) and "pass_" in v_:
            print(f"  {'✅' if v_['pass_'] else '⛔'} {k}")
    print(f"\n원장 {os.path.relpath(OUTJ, ROOT)}\n그림 {figs}\n")


# ═══════════════════════════════════════════════════════════════════════════
# 그림 — 그림 안 글자는 전부 영어
# ═══════════════════════════════════════════════════════════════════════════
C_AC, C_FL, C_CB = "#4c72b0", "#dd8452", "#55a868"
ORD16 = [f"R{r}D{d}E{e}F{f}" for d in (0, 1) for r in (0, 1)
         for e in (0, 1) for f in (0, 1)]


def _style():
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 12.5, "axes.labelsize": 11,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 10,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True})


def fig_factorial(cells, refs, all16, el=-30.0):
    """조합 축으로 세 열을 나란히 놓은 막대 + 선/바닥 대비."""
    _style()
    tags = list(ORD16)
    n_off = sum(1 for t in tags if t[3] == "0")          # 회절 끈 칸의 개수(음영 경계)
    fig, axes = plt.subplots(2, 2, figsize=(17.4, 11.6),
                             gridspec_kw=dict(height_ratios=[1.0, 0.60], hspace=0.20, wspace=0.14))
    lo = min([c["above_floor_db"] for c in cells.values()
              if c["above_floor_db"] is not None] + [-170.0]) - 4
    xb = max([c["ac_db"] for c in cells.values() if c["ac_db"] is not None] + [-120.0]) + 2
    #: ⭐숫자는 막대 끝이 아니라 오른쪽 «수 칸» 에 세 줄로 적는다 — 막대끼리 라벨이 겹치지 않게.
    gut = [xb + 6.5, xb + 15.0, xb + 23.5]
    hi = xb + 27.0
    for j, dep in enumerate((1, 3)):
        ax, ax2 = axes[0][j], axes[1][j]
        h = 0.26
        ax.axvline(xb + 1.5, color="0.75", lw=1.0)
        for gx, nm, cl in zip(gut, ("AC", "floor", "comb"), (C_AC, C_FL, C_CB)):
            ax.text(gx, -0.95, nm, ha="right", va="center", fontsize=9.5, color=cl,
                    fontweight="bold")
        for i, t in enumerate(tags):
            c = cells.get(f"{t}_d{dep}/el{el:+.0f}")
            if c is None:
                ax.text(lo + 2, i, "not computed", va="center", fontsize=9,
                        color="0.55", style="italic")
                ax2.text(0.35, i, "not computed", va="center", fontsize=9,
                         color="0.55", style="italic")
                continue
            if c["zero_echo"]:
                ax.text(lo + 2, i, "no echo — solver returned 0 paths", va="center",
                        fontsize=9.5, color="#b03030", fontweight="bold")
                ax2.text(0.35, i, "no echo", va="center", fontsize=9.5, color="#b03030",
                         fontweight="bold")
                continue
            for o, (kk, col) in enumerate((("ac_db", C_AC), ("above_floor_db", C_FL),
                                           ("above_comb_db", C_CB))):
                val = c[kk]
                if val is None:
                    continue
                ax.barh(i + (1 - o) * h, val - lo, height=h * 0.92, left=lo,
                        color=col, edgecolor="white", linewidth=0.7)
                ax.text(gut[o], i, f"{val:.1f}", ha="right", va="center",
                        fontsize=9.2, color=col)
            ct = c["comb_over_floor_db"]
            if ct is not None:
                ax2.barh(i, ct, height=0.55, color=("#55a868" if ct >= 2 else "#b03030"),
                         edgecolor="white", linewidth=0.7)
                ax2.text(ct + (0.55 if ct >= 0 else -0.55), i, f"{ct:+.1f}", va="center",
                         ha=("left" if ct >= 0 else "right"), fontsize=9, color="0.25")
        for a in (ax, ax2):
            a.set_yticks(np.arange(len(tags)))
            a.set_yticklabels(tags, fontfamily="monospace")
            a.set_ylim(-0.72, len(tags) - 0.28)
            a.invert_yaxis()
            a.axhspan(-0.72, n_off - 0.5, color="0.86", alpha=0.45, zorder=0)
        ax.set_xlim(lo, hi)
        #: 눈금은 막대 구역까지만 — 오른쪽 «수 칸» 에 눈금이 들어가면 잘못 읽힌다.
        ax.set_xticks([t for t in range(-200, -100, 10) if lo <= t <= xb])
        ax.set_title(f"({'ab'[j]}) max_depth = {dep}  —  absolute power of the three columns",
                     loc="left")
        ax.set_xlabel("absolute power [dB, ledger amplitude units]")
        ax2.axvline(0, color="0.25", lw=1.4)
        ax2.set_xlim(-4.5, 20.5)
        ax2.set_title(f"({'cd'[j]}) max_depth = {dep}  —  is there a comb line above the "
                      f"local floor?", loc="left")
        ax2.set_xlabel("comb-bin density / floor-bin density [dB]   (0 dB = white, no line)")
    ref = refs.get(f"ours_r15_n8192/el{el:+.0f}")
    hnd = [Patch(facecolor=C_AC, label="(1) AC  =  DC-removed fluctuation power"),
           Patch(facecolor=C_FL, label="(2) floor above f_tip  =  off-comb bins"),
           Patch(facecolor=C_CB, label="(3) comb bins above f_tip  =  k x f_flash +/- 8 Hz"),
           Patch(facecolor="0.86", label="shaded rows: diffraction OFF (D = 0)")]
    fig.text(0.5, 0.972, "Switch grid re-read in absolute dB — does diffraction erase the "
                         "rhythm, or bury it?", ha="center", fontsize=15)
    fig.text(0.5, 0.947, "PathSolver switch grid at elevation -30 deg.  matrice4e, 15 m, "
                         "8192 poses, 4e9 rays per pose.", ha="center", fontsize=11,
             color="0.3")
    tail = ("R = refraction,  D = wedge diffraction,  E = edge diffraction,  "
            "F = diffuse reflection.")
    if ref and ref["ac_db"] is not None:
        tail += f"   Our SBR+PO kernel at the same cell, for scale: AC {ref['ac_db']:.1f} dB."
    fig.text(0.5, 0.925, tail, ha="center", fontsize=11, color="0.3")
    fig.legend(handles=hnd, loc="lower center", ncol=4, frameon=False,
               bbox_to_anchor=(0.5, 0.004))
    fig.subplots_adjust(top=0.895, bottom=0.075, left=0.072, right=0.988)
    fig.savefig(FIG1, dpi=135)
    plt.close(fig)
    return FIG1


#: 앙각 그림에 싣는 팔 — 기전이 서로 다른 것만 고른다(중복 팔은 본문에서 말한다).
EL_ARMS = [
    ("ours_r15_n8192", "ours (SBR+PO)", "k", "-"),
    ("sionna_p4000000000_r15_n8192_d1", "R0D0E0F1 d1  all switches off", "#e08214", "--"),
    ("sionna_p4000000000_onlydepth3_r15_n8192", "R0D0E0F1 d3  depth 3 only", "#2a9d3a", "--"),
    ("sionna_p4000000000_onlyrefr_r15_n8192", "R1D0E0F1 d1  refraction only", "#8c6bb1", "--"),
    ("sionna_p4000000000_onlydiffr_r15_n8192", "R0D1E0F1 d1  diffraction only", "#d62728", "--"),
    ("sionna_p4000000000_phys_r15_n8192_d1", "R1D1E1F1 d1  all on", "#1f77b4", "--"),
]


def fig_elevation(cells, refs):
    """앙각별 세 열 — 기전이 다른 여섯 팔."""
    _style()
    byarm = {}
    for c in list(cells.values()) + list(refs.values()):
        byarm.setdefault(c["arm"], []).append(c)
    use = [(a, lb, cl, ls) for a, lb, cl, ls in EL_ARMS if len(byarm.get(a, [])) >= 2]
    if not use:
        raise RuntimeError("앙각이 둘 이상인 팔이 없다")
    fig, ax = plt.subplots(1, 3, figsize=(17.0, 5.9), sharex=True)
    for kk, a_, ttl in (("ac_db", ax[0], "(a) AC — DC-removed fluctuation power"),
                        ("above_floor_db", ax[1], "(b) floor above f_tip"),
                        ("above_comb_db", ax[2], "(c) comb bins above f_tip")):
        for arm, lb, cl, ls in use:
            v = sorted(byarm[arm], key=lambda c: -c["el_deg"])
            xs = [c["el_deg"] for c in v if c[kk] is not None]
            ys = [c[kk] for c in v if c[kk] is not None]
            if len(xs) < 2:
                continue
            a_.plot(xs, ys, marker="o", ms=5.5, lw=2.0, ls=ls, color=cl, label=lb,
                    zorder=(4 if cl == "k" else 3))
        a_.axvspan(-93, -85, color="0.86", alpha=0.7, zorder=0)
        a_.set_title(ttl, loc="left")
        a_.set_xlabel("elevation [deg]")
        a_.set_xlim(4, -94)
        a_.set_xticks([0, -15, -30, -45, -60, -75, -90])
    ax[0].set_ylabel("absolute power [dB, ledger amplitude units]")
    ax[1].annotate("depth 3 lifts the floor\nby 12.7 dB here", xy=(-59, -141.6),
                   xytext=(-36, -134.5), fontsize=10, color="#1a6b26", va="center",
                   arrowprops=dict(arrowstyle="->", lw=1.3, color="#1a6b26"))
    for a_ in ax:
        a_.text(-86, a_.get_ylim()[0] + 0.055 * (a_.get_ylim()[1] - a_.get_ylim()[0]),
                "f_tip = 0\nband degenerate", fontsize=8.5, ha="right", color="0.4")
    fig.text(0.5, 0.965, "The same three columns across elevation — one arm per mechanism",
             ha="center", fontsize=14)
    fig.text(0.5, 0.928, "Edge diffraction is omitted: with D = 0 it is bit-for-bit identical "
                         "to 'all switches off'.  max_depth 2 is omitted: it sits within "
                         "0.5 dB of max_depth 1.", ha="center", fontsize=10, color="0.35")
    h, lb_ = ax[0].get_legend_handles_labels()
    fig.legend(h, lb_, loc="lower center", ncol=6, frameon=False, fontsize=10,
               bbox_to_anchor=(0.5, 0.002))
    fig.subplots_adjust(top=0.855, bottom=0.185, left=0.058, right=0.99, wspace=0.17)
    fig.savefig(FIG2, dpi=135)
    plt.close(fig)
    return FIG2


# ═══════════════════════════════════════════════════════════════════════════
def build_corrections(cells, refs, d_main, verdict, burial, rep, p13, dead_pairs):
    """⭐어느 문장을 무엇으로 — 파일은 고치지 않는다(여기 적기만 한다)."""
    out = []
    base = cells.get("R0D0E0F1_d1/el-30")
    diff = cells.get("R0D1E0F1_d1/el-30")
    #: 재계산한 몫의 범위 — 옛 문장의 «11.7~13.2 %» 는 결측 512 자세 위에서 잰 값이다.
    d1s = sorted(c["rhythm_share_pct"] for k, c in cells.items()
                 if k.endswith("_d1/el-30") and c["rhythm_share_pct"] is not None
                 and c["diffraction"])
    d0s = sorted(c["rhythm_share_pct"] for k, c in cells.items()
                 if k.endswith("_d1/el-30") and c["rhythm_share_pct"] is not None
                 and not c["diffraction"])
    if base and diff:
        out.append(dict(
            where="reports/18_switch-grid.ipynb · 제목",
            old="리포트 18 — 물리 스위치 격자: 회절이 든 조합은 전부 잡음이 된다",
            new="리포트 18 — 물리 스위치 격자: 회절은 리듬을 지우지 않고 리듬 없는 에코로 덮는다",
            why_ko=f"회절을 켠 팔은 끈 팔을 계수 {d_main['contain_coeff']:.2f}·위상 "
                   f"{d_main['contain_phase_deg']:+.1f}° 로 그대로 품고 있다. 「잡음이 된다」는 "
                   f"신호가 사라졌다는 뜻으로 읽히는데, 사라진 것이 아니라 "
                   f"{d_main['d_above_floor_db']:+.1f} dB 올라온 바닥 밑에 잠긴 것이다.",
            evidence="outputs/switch_factorial.json · axis_diffs.D · diffraction_burial"))
        out.append(dict(
            where="reports/18_switch-grid.ipynb · 결과 1",
            old="⭐회절 스위치 하나가 경계선이다 — 회절이 든 네 조합은 리듬 몫 11.7~13.2 %"
                "(백색잡음 = 13)로 전부 잡음 수준이고, 회절이 없는 세 조합은 62.1~80.5 % 로 "
                "날개 구조를 유지한다.",
            new=f"⭐회절 스위치 하나가 경계선이다 — 회절을 켜면 상한 위 **바닥이 "
                f"{d_main['d_above_floor_db']:+.1f} dB**({base['above_floor_db']:.1f} → "
                f"{diff['above_floor_db']:.1f} dB) 오르고, 빗살 선의 바닥 위 솟음은 "
                f"{base['comb_over_floor_db']:+.1f} dB → {diff['comb_over_floor_db']:+.1f} dB "
                f"로 무너진다. 리듬 몫이 {d1s[0]:.1f}~{d1s[-1]:.1f} %(백색 = 12.7)로 떨어진 "
                f"것은 분자가 준 것이 아니라 **분모가 커진 것**이다. 회절이 없는 칸은 "
                f"{d0s[0]:.1f}~{d0s[-1]:.1f} %.",
            why_ko="몫만 인용하면 «분자가 줄었나 분모가 컸나» 를 못 가른다. 절대 dB 로 읽으면 "
                   "분모(바닥)가 커진 쪽이다.",
            evidence="outputs/switch_factorial.json · cells.R0D0E0F1_d1/el-30 ↔ R0D1E0F1_d1/el-30"))
        out.append(dict(
            where="reports/18_switch-grid.ipynb · 판정 1",
            old="범인은 회절이다. … 회절이 든 조합은 굴절·모서리 동반 여부와 무관하게 전부 잡음이 된다.",
            new="회절이 얹는 것은 **리듬 없는 에코**다. 회절이 든 조합은 굴절·모서리 동반 여부와 "
                "무관하게 상한 위 바닥이 같은 자리로 올라오고(≈−126 dB), 그 바닥이 원래 있던 "
                "빗살을 덮는다. 원래 빗살은 그대로 남아 있다.",
            why_ko="「잡음이 된다」→「잡음이 덮는다」. 기전이 다르면 다음 실험도 달라진다 — "
                   "지운다면 회절 모형이 틀린 것이고, 덮는다면 회절 항의 **절대 크기**가 문제다.",
            evidence="outputs/switch_factorial.json · verdict.A_cover_pass · axis_diffs.D"))
    if burial:
        b = next((x for x in burial if x["pair"].startswith("R0D0E0F1_d1")), burial[0])
        lo_, hi_ = min(x["burial_depth_db"] for x in burial), max(x["burial_depth_db"]
                                                                 for x in burial)
        out.append(dict(
            where="docs/RESUME.md:25 (미해결 선언)",
            old="⚠회절이 왜 리듬을 지우는가는 여전히 미규명이다. 이번에 좁힌 것은 «동체 탓이 아니다» 까지다.",
            new=f"⚠회절은 리듬을 **지우지 않는다** — 덮는다. 회절을 켠 시계열은 끈 시계열을 계수 "
                f"≈1 로 품고 있고, 원래 빗살은 새 바닥보다 {b['burial_depth_db']:.1f} dB "
                f"(다섯 쌍에서 {lo_:.1f}~{hi_:.1f} dB) 아래에 잠긴다. 남은 미해결은 «상한 위로 "
                f"새는 그 회절 항이 물리인가 추정기 잡음인가» (R1 · spp 내림 사다리) 하나다.",
            why_ko="미해결 목록을 좁힌다 — «왜 지우나» 라는 질문 자체가 잘못된 질문이었다.",
            evidence="outputs/switch_factorial.json · diffraction_burial"))
    out.append(dict(
        where="docs/RESUME.md:12 (로터만 남긴 판 해석)",
        old="로터만 판도 물리를 켜면 리듬 몫이 13 %(백색잡음 수준)로 주저앉는다. 동체가 없는데도 "
            "지워진다 ⇒ 회절 자체가 범인이다",
        new="로터만 판도 물리를 켜면 리듬 몫이 13 %(백색잡음 수준)로 주저앉는다. 동체가 없는데도 "
            "그렇다 ⇒ 회절 항이 **로터 자신의 모서리에서** 리듬 없는 에코를 얹는다. 몫이 내려간 "
            "것은 빗살이 사라져서가 아니라 바닥이 올라와서다.",
        why_ko="같은 관측, 다른 기전. «지워진다» 를 «덮인다» 로 바꾼다.",
        evidence="outputs/switch_factorial.json · verdict.A_cover_pass"))
    stale = [r for r in rep if r["old_n_missing"] and not r["new_n_missing"]]
    if stale:
        s = stale[0]
        out.append(dict(
            where="reports/18_switch-grid.ipynb · 표 «굴절+회절» 행 · outputs/switch_grid.json",
            old=f"굴절+회절 … 리듬 몫 {s['old_pct']} % · 빠진 자세 {s['old_n_missing']}"
                " / ⚠«굴절+회절» 행은 빠진 자세가 있으면 그 수가 0 이 될 때까지 재병합 후 다시 읽는다.",
            new=f"굴절+회절 … 리듬 몫 {s['new_pct']} % · 빠진 자세 0 (재병합 완료, 경고 문장 삭제)",
            why_ko="원장이 채워졌다. 옛 몫은 결측 512 자세 위에서 잰 값이라 재인용 금지.",
            evidence="outputs/elevation_sweep_md.json rows[engine="
                     "sionna_p4000000000_swR1D1E0F1_r15_n8192_d1] n_missing=0"))
    if p13:
        out.append(dict(
            where="docs/NEXT_EXPERIMENTS.md · R13 판정란 «깊이 1↔3 이 7 쌍»",
            old="깊이 1↔3 이 7 쌍 전부 레벨 <2 dB·리듬 <3 %p 면 깊이 축 종결"
                "(큐에서 --max-depth 3 제거)",
            new=f"깊이 1↔3 은 살아 있는 쌍 {len(p13)} 쌍(판 위 −30° 에 "
                f"{verdict['B_n_pairs_1to3_on_plate']} 쌍) + 두 판 모두 경로 0 인 죽은 쌍 "
                f"{len(dead_pairs)} 쌍이다(꼬리표 없는 등가칸 포함). 판정: "
                f"{verdict['B_verdict_ko']} — {verdict['B_why_ko']}",
            why_ko="꼬리표만 세면 7 쌍이지만 등가칸까지 세면 더 많고, 사전등록 문턱을 실제로 "
                   "적용하면 통과하지 못한다.",
            evidence="outputs/switch_factorial.json · depth_pairs · verdict.B_failures"))
    out.append(dict(
        where="큐 규약 (docs/NEXT_EXPERIMENTS.md ⑦ 큐에 붙일 줄)",
        old="R13 이 통과하면 스위치 팔에서 --max-depth 3 를 뺀다",
        new=("--max-depth 3 를 뺀다 — 깊이는 죽은 축이다(판정 B 성립)"
             if verdict["B_pass"] else
             "⛔--max-depth 3 를 **그대로 둔다** — 판정 B 불성립. 다만 깊이는 «레벨을 옮기는 "
             "축» 이 아니라 «상한 위 바닥을 올리는 축» 이므로, 깊이 팔을 발주할 때 읽을 잣대는 "
             "레벨이 아니라 세 열이다."),
        why_ko="같은 GPU 시간을 어디에 쓸지가 이 한 줄에서 갈린다.",
        evidence="outputs/switch_factorial.json · verdict.B_pass · verdict.B_failures"))
    b60 = next((r for r in verdict.get("B_failures", []) if r["el_deg"] == -60.0), None)
    if b60:
        out.append(dict(
            where="docs/RESUME.md · «모서리회절·다중반사는 영향 0» (물리 단일축 표 아래 요약)",
            old="모서리회절·다중반사는 영향 0.",
            #: ⚠리듬 몫 «%p» 는 창 반폭 hw·f_above 를 타므로 크기를 인용하지 않는다(R29).
            #  살아남는 근거는 **상한 위 바닥** 쪽이다.
            new=f"모서리회절은 영향 0(회절이 꺼져 있으면 무동작). **다중반사는 영향 0 이 아니다** "
                f"— 레벨로는 안 보이지만(−60° 에서 AC 차 +0.09 dB) 상한 위 바닥을 "
                f"{b60['d_above_floor_db']:+.1f} dB 올린다. ⚠리듬 몫도 함께 움직이지만 그 "
                f"**크기는 인용하지 않는다**(R29 — 창 반폭 hw·f_above 를 탄다).",
            why_ko="옛 결론은 레벨 하나로 잰 것이다. 세 열로 갈라 보니 깊이는 바닥을 올린다.",
            evidence="outputs/switch_factorial.json · depth_pairs[combo=R0D0E0F1, el=-60]"))
    return out


if __name__ == "__main__":
    main()
