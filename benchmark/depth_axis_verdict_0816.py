# -*- coding: utf-8 -*-
"""
depth_axis_verdict_0816.py — ⭐반사 깊이 축(--max-depth) 판정 · 08-16 병합본
==========================================================================

■ 왜 있나
    8/18 덱 30 장 «Future work» 의 1 번이 «반사 깊이 축을 닫는다» 다. 그 축을 닫을 데이터가
    08-16 병합으로 전부 들어왔는데(깊이 3 칸 12 개 신규) 판정 원장도 그림도 없었다.
    이 스크립트가 병합 원장에서 깊이 짝을 **전수** 찾아 재고 판정한다.

■ 묻는 것
    ⓐ 광선을 세 번까지 튕기게 하면 표적 신호가 커지나 안 바뀌나
    ⓑ 그 효과가 스위치 조합(굴절 R · 회절 D · 모서리 E · 확산 F)에 따라 달라지나
    ⓒ 거리에 따라 달라지나
    ⓓ 깊이를 1 로 둔 우리 규약이 정당한가 (공장 기본값은 3)

■ 잣대 규약 (어기면 결론이 뒤집힌다)
    · 레벨(dB)은 **전부 정지 성분(DC) 제거 후** — moving_power_db
    · 리듬 몫은 날개끝 상한 **위**만 세므로 거리 팔에서 퇴화 → comb_contrast_db 병용
    · 격자 산포 밴드는 **앙각마다 다르다**(2026-08-16 정정): 0° 3.86 · −30° 0.37 · −45° 0.09
      · −60° 0.02 · −75° 0.10 · −90° 5.62 dB
    · 빗살 대비는 격자 계단마다 +4~5.6 dB 단조 상승 → 절대 인용에 격자 꼬리표
    · AC/DC < 1e-11 칸은 near_numeric_floor — 물리로 읽지 않는다

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt/mitsuba 임포트 없음)
    outputs/elevation_sweep_md.{json,npz}   병합본
    outputs/elev_sweep_shards/*.npz         npaths 분포 · cfg 비트 검증
    outputs/switch_factorial.json           R13 판(08-15) — 사전등록 문안 · 옛 결론
    outputs/grid_convergence_check.json     격자 산포 밴드(우리 커널)
    outputs/frame_completion_0816.json      앙각별 밴드 정정 + 별칭 재실행 앵커
    outputs/raybudget_seed_ladder.json      PathSolver 시드 산포(계통 편향)

■ 굽는 것
    outputs/depth_axis_verdict_0816.json
    outputs/figures/depth_axis_verdict_0816.png

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/depth_axis_verdict_0816.py
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

import build_md_atlas as A                                             # noqa: E402
from md_mapstyle import auto_periods                                   # noqa: E402

ROOT = A.ROOT
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUTJ = os.path.join(ROOT, "outputs", "depth_axis_verdict_0816.json")
FIG = os.path.join(ROOT, "outputs", "figures", "depth_axis_verdict_0816.png")

HALF_HZ = 8.0
DB_SAME = 2.0          # R13 사전등록 B 의 레벨 밴드 (밴드가 없던 때의 임의값)
PP_SAME = 3.0          # R13 사전등록 B 의 리듬 밴드
NEAR_FLOOR = 1e-11     # AC/DC 수치 바닥 문턱 (사용자 규약)

#: ⭐앙각별 격자 산포 밴드 [dB] — 2026-08-16 정정본(frame_completion_0816.q4_grid_band)
GRID_BAND_AC_DB = {0.0: 3.86, -15.0: 1.31, -30.0: 0.37, -45.0: 0.09,
                   -60.0: 0.02, -75.0: 0.10, -90.0: 5.62}
GRID_BAND_RHYTHM_PP_BY_EL = {0.0: 11.8, -15.0: 0.1, -30.0: 21.8, -45.0: 12.9,
                             -60.0: 16.0, -75.0: 2.5, -90.0: 16.4}
GRID_BAND_COMB_DB_BY_EL = {0.0: 0.1, -15.0: 4.1, -30.0: 4.6, -45.0: 4.6,
                           -60.0: 4.0, -75.0: None, -90.0: None}
GRID_BAND_RHYTHM_PP_GLOBAL = 21.8      # R16 정본(RESUME 0816: «리듬 몫 밴드 21.8 %p 는 유지»)
GRID_BAND_COMB_DB_GLOBAL = 4.04        # 빗살 대비 격자 계단 최소치(+4.04~+5.6 dB 중 보수적 하한)
GRID_BAND_ABOVE_PP_GLOBAL = 12.5549    # R16 «f_tip 밖 몫» 밴드 (el 0~−45 최대)
GRID_BAND_BEAT_HZ = 0.152
#: ⭐빗살 대비가 «백색 널 자리» 라고 볼 폭 [dB] — 널은 백색잡음 0 dB(실측 +0.4 dB)다.
#   이 안이면 수가 몇 dB 움직여도 «빗살 없음» 이라는 **읽기**는 안 바뀐다.
COMB_NULL_DB = 3.0
SEED_SD_DB = 1.833                     # PathSolver 시드 산포 sd (spp 4e9)
#: ⭐이상 자세 솎기 — 두 팔 통틀어 |AC|/중앙 이 가장 큰 자세 k 개를 빼고 다시 잰다
TRIM_K = (0, 1, 8)
TRIM_HEADLINE = 1                      # 헤드라인은 «가장 튄 자세 하나를 뺀» 판

# ═══════════════════════════════════════════════════════════════════════════
# 0. 팔 이름 → 설정
# ═══════════════════════════════════════════════════════════════════════════
SW_RE = re.compile(r"^sw(R[01]D[01]E[01]F[01])$")
D_RE = re.compile(r"^d(\d)$")
R_RE = re.compile(r"^r(\d+(?:\.\d+)?)$")
N_RE = re.compile(r"^n(\d+)$")
AZ_RE = re.compile(r"^az(\d+(?:\.\d+)?)$")

TOKEN_COMBO = {"phys": "R1D1E1F1", "stockdef": "R1D0E0F0", "onlyrefr": "R1D0E0F1",
               "onlydiffr": "R0D1E0F1", "onlyedge": "R0D0E1F1", "onlydepth3": "R0D0E0F1"}
TOKEN_DEPTH = {"stockdef": 3, "onlydepth3": 3, "onlyrefr": 1, "onlydiffr": 1, "onlyedge": 1}
DEFAULT_COMBO = "R0D0E0F1"
COMBO_KO = {"R0D0E0F1": "PS 다 끔(확산만)", "R1D0E0F1": "PS 굴절만", "R0D1E0F1": "회절만",
            "R0D0E1F1": "모서리만(≡다 끔)", "R1D1E1F1": "물리 켬(전부)",
            "R1D0E0F0": "순정 기본값(확산 끔)"}
#: ⭐표준 프레임(docs/STANDARD_FRAME.md)이 실제로 싣는 PathSolver 팔
STANDARD_FRAME_COMBOS = ("R0D0E0F1", "R1D0E0F1")


def parse_arm(arm: str) -> dict | None:
    if not arm.startswith("sionna"):
        return None
    cfg = dict(arm=arm, combo=None, depth_name=None, spp=None, az=0.0, airframe=None,
               parts=None, shell=None, prop=None, extra=[])
    for x in arm.split("_")[1:]:
        if x.startswith("p") and x[1:].isdigit():
            cfg["spp"] = int(x[1:]); continue
        m = SW_RE.match(x)
        if m:
            cfg["combo"] = m.group(1); continue
        if x in TOKEN_COMBO:
            cfg["combo"] = TOKEN_COMBO[x]
            if x in TOKEN_DEPTH:
                cfg["depth_name"] = TOKEN_DEPTH[x]
            continue
        m = D_RE.match(x)
        if m:
            cfg["depth_name"] = int(m.group(1)); continue
        if R_RE.match(x) or N_RE.match(x):
            continue                     # 거리·자세수는 원장 열로 받는다
        m = AZ_RE.match(x)
        if m:
            cfg["az"] = float(m.group(1)); continue
        if x in A.DRONES:
            cfg["airframe"] = x; continue
        if x.startswith("parts"):
            cfg["parts"] = x; continue
        if x.startswith("shell"):
            cfg["shell"] = x; continue
        if x.startswith("prop"):
            cfg["prop"] = x; continue
        cfg["extra"].append(x)
    if cfg["combo"] is None:
        cfg["combo"] = DEFAULT_COMBO
    return cfg


def cfg_key(c: dict, row: dict) -> tuple:
    """깊이를 **뺀** 설정 지문 — 이 지문이 같고 깊이만 다른 칸이 «짝» 이다."""
    return (c["combo"], row["range_m"], c["airframe"] or "matrice4e", row["az_deg"],
            c["parts"], c["shell"], c["prop"], row["spp"], row["fc_hz"],
            row["n_poses"], tuple(c["extra"]))


# ═══════════════════════════════════════════════════════════════════════════
# 1. 잣대 — switch_factorial.columns 와 **같은 식**(절대 dB 세 열)
# ═══════════════════════════════════════════════════════════════════════════
def db(v):
    return None if (v is None or not np.isfinite(v) or v <= 0) else round(float(10 * np.log10(v)), 3)


def columns(E, prf, ffl, ft, hw=HALF_HZ):
    E = np.asarray(E, complex)
    n = E.size
    x = E - E.mean()
    w = np.hanning(n)
    P = np.abs(np.fft.fft(x * w)) ** 2 / (n * np.sum(w ** 2))       # Parseval 정규화
    fr = np.fft.fftfreq(n, 1.0 / prf)
    above = np.abs(fr) >= ft
    k = np.round(np.abs(fr) / ffl)
    on = np.abs(np.abs(fr) - k * ffl) <= hw
    m_fl, m_cb = above & ~on, above & on
    nb_f, nb_c = int(m_fl.sum()), int(m_cb.sum())
    p_fl, p_cb = float(P[m_fl].sum()), float(P[m_cb].sum())
    p_ab = p_fl + p_cb
    dens_f = p_fl / nb_f if nb_f else np.nan
    dens_c = p_cb / nb_c if nb_c else np.nan
    excess = p_cb - dens_f * nb_c
    return dict(ac_db=db(float(np.mean(np.abs(x) ** 2))),
                above_floor_db=db(p_fl), above_comb_db=db(p_cb),
                above_comb_line_db=db(excess) if excess > 0 else None,
                comb_over_floor_db=(round(float(10 * np.log10(dens_c / dens_f)), 3)
                                    if (nb_f and nb_c and dens_f > 0 and dens_c > 0) else None),
                rhythm_share_pct=(round(100.0 * p_cb / p_ab, 2) if p_ab > 0 else None),
                n_bins_above=int(above.sum()), n_bins_comb=nb_c, n_bins_floor=nb_f,
                zero_echo=bool(not np.any(E)))


def shard_npaths(arm: str, el: float):
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None
    npa, cfg = [], None
    for f in fs:
        z = np.load(f)
        if cfg is None and "cfg" in z:
            cfg = np.asarray(z["cfg"], float).tolist()
        if "npaths" in z:
            npa.append(np.asarray(z["npaths"]))
        z.close()
    if not npa:
        return dict(n_shards=len(fs), cfg=cfg, npaths=None)
    v = np.concatenate(npa).astype(float)
    return dict(n_shards=len(fs), cfg=cfg, n=int(v.size),
                median=float(np.median(v)), mean=round(float(v.mean()), 2),
                p10=float(np.percentile(v, 10)), p90=float(np.percentile(v, 90)),
                min=float(v.min()), max=float(v.max()),
                zero_frac_pct=round(100.0 * float((v == 0).mean()), 2))


def spike_stats(E):
    """튐 진단 — 한 자세가 통째로 튀면 잣대가 그 자세 하나를 재게 된다.

    top1_over_median   |AC| 최대 ÷ 중앙. 큰 값 자체는 **정상일 수 있다**(정반사 플래시는
                       로터 대칭 때문에 여러 자세에 같이 선다).
    isolation          |AC| 최대 ÷ 둘째. ⭐이것이 1 에 가까우면 «구조적 플래시», 크면
                       «자세 하나만 튀었다» — 물리와 계산 사고를 가르는 자리다.
    """
    x = np.asarray(E, complex)
    x = x - x.mean()
    if not np.any(x):
        return None
    v = np.sort(np.abs(x))[::-1]
    med = float(np.median(np.abs(x)))
    if med <= 0:
        return None
    return dict(top1_over_median=round(float(v[0] / med), 2),
                top2_over_median=round(float(v[1] / med), 2),
                isolation=round(float(v[0] / v[1]), 3),
                argmax_pose=int(np.argmax(np.abs(x))))


def trimmed_metrics(E1, E3, ffl, ft, k):
    """두 팔 통틀어 가장 튄 자세 k 개를 **두 팔에서 똑같이** 빼고 다시 잰 차이."""
    x1 = np.asarray(E1, complex) - np.asarray(E1, complex).mean()
    x3 = np.asarray(E3, complex) - np.asarray(E3, complex).mean()
    m1, m3 = np.median(np.abs(x1)), np.median(np.abs(x3))
    if not (m1 > 0 and m3 > 0):
        return None
    rel = np.maximum(np.abs(x1) / m1, np.abs(x3) / m3)
    mask = np.ones(x1.size, bool)
    if k:
        mask[np.argsort(rel)[::-1][:k]] = False

    def one(E):
        y = np.asarray(E, complex)[mask]
        r = A.rhythm_share(y, ffl, ft)
        c = A.comb_contrast_db(y, ffl, ft)
        return (r[0], None if c is None else c,
                float(10 * np.log10(np.mean(np.abs(y - y.mean()) ** 2))), r[2])

    a, b = one(E1), one(E3)
    y1 = np.asarray(E1, complex)[mask]; y1 = y1 - y1.mean()
    y3 = np.asarray(E3, complex)[mask]; y3 = y3 - y3.mean()
    res = y3 - y1
    rres = A.rhythm_share(res, ffl, ft)[0]
    return dict(
        k_trimmed=k, n_kept=int(mask.sum()),
        residual_over_d1_db=round(float(10 * np.log10(np.mean(np.abs(res) ** 2)
                                                      / np.mean(np.abs(y1) ** 2))), 3),
        residual_rhythm_pct=(None if rres is None else round(rres, 2)),
        abs_rho=round(float(abs(np.vdot(y1, y3)) / (np.linalg.norm(y1) * np.linalg.norm(y3))), 6),
        contain_coeff=round(float(abs(np.vdot(y1, y3) / np.vdot(y1, y1))), 6),
        d_moving_power_db=round(b[2] - a[2], 3),
        d_rhythm_pp=(None if (a[0] is None or b[0] is None) else round(b[0] - a[0], 3)),
        d_comb_contrast_db=(None if (a[1] is None or b[1] is None) else round(b[1] - a[1], 3)),
        d_above_ceiling_pp=(None if (a[3] is None or b[3] is None) else round(b[3] - a[3], 3)),
        rhythm_d1_pct=(None if a[0] is None else round(a[0], 2)),
        rhythm_dN_pct=(None if b[0] is None else round(b[0], 2)),
        comb_d1_db=(None if a[1] is None else round(a[1], 2)),
        comb_dN_db=(None if b[1] is None else round(b[1], 2)))


def mtime(p):
    return _dt.datetime.fromtimestamp(os.path.getmtime(p),
                                      _dt.timezone(_dt.timedelta(hours=9))
                                      ).strftime("%Y-%m-%d %H:%M KST")


# ═══════════════════════════════════════════════════════════════════════════
# 2. 본체
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    J = A.J
    M, ROWS = J["_meta"], J["rows"]
    PRF = float(M["prf_hz"])
    Z = A.Z

    # ── 2-1. 칸 훑기 ────────────────────────────────────────────────────────
    cells, groups = {}, {}
    for i, r in enumerate(ROWS):
        arm, el = r["engine"], float(r["el_deg"])
        key = f"{arm}/el{el:+.0f}"
        if key not in Z.files:
            continue
        c = parse_arm(arm)
        if c is None:
            continue
        dep = r["max_depth"] if r["max_depth"] is not None else c["depth_name"]
        if dep is None:
            continue
        rates = A.arm_rates(arm)
        ft, ffl = A.f_tip_at(rates, el), rates["f_flash_hz"]
        col = columns(Z[key], PRF, ffl, ft)
        summ = A.cell_summary(arm, el, rates, auto_periods(PRF, ffl))
        E = np.asarray(Z[key], complex)
        p_ac = float(np.mean(np.abs(E - E.mean()) ** 2))
        p_tot = float(np.mean(np.abs(E) ** 2))
        acdc = (p_ac / p_tot) if p_tot > 0 else 0.0
        cells[key] = dict(
            npz_key=key, arm=arm, el_deg=el, depth=int(dep), ledger_row=i,
            combo=c["combo"], combo_ko=COMBO_KO.get(c["combo"], c["combo"]),
            refraction=c["combo"][1] == "1", diffraction=c["combo"][3] == "1",
            edge=c["combo"][5] == "1", diffuse=c["combo"][7] == "1",
            range_m=r["range_m"], az_deg=r["az_deg"], spp=r["spp"],
            airframe=c["airframe"] or "matrice4e", parts=c["parts"],
            n_poses=r["n_poses"], n_missing=r["n_missing"], seconds=r["seconds"],
            f_tip_hz=round(ft, 1), f_flash_hz=round(ffl, 3),
            npaths_median_ledger=r["npaths_median"], ledger_level_db=r["level_db"],
            # ── 잣대 ──────────────────────────────────────────────────────
            moving_power_db=col["ac_db"],                     # 요동 절대전력(DC 제거)
            above_floor_db=col["above_floor_db"],             # 확산 바닥(상한 위 빗살 밖)
            above_comb_db=col["above_comb_db"],
            comb_over_floor_db=col["comb_over_floor_db"],     # 빗살 선/바닥 대비
            comb_contrast_db=summ["comb_contrast_db"],        # 빗살 대비(상한 아래)
            rhythm_share_pct=col["rhythm_share_pct"],
            rhythm_share_atlas_pct=summ["rhythm_share_pct"],
            rhythm_null_pct=summ["rhythm_null_pct"],
            above_ceiling_energy_pct=summ["above_ceiling_energy_pct"],
            beat_hz=summ["beat_hz"], beat_over_flash=summ["beat_over_flash"],
            ac_over_dc=float(f"{acdc:.4g}"),
            # ── 깃발 ──────────────────────────────────────────────────────
            zero_echo=col["zero_echo"],
            near_numeric_floor=bool(p_tot > 0 and acdc < NEAR_FLOOR),
            tip_ceiling_degenerate=summ["tip_ceiling_degenerate"],
            no_return=summ["no_return"], incomplete=summ["incomplete"],
            no_motion=summ["no_motion"], beat_spiky=summ["beat_spiky"])
        groups.setdefault(cfg_key(c, r), {}).setdefault(int(dep), []).append(key)

    # ── 2-2. 짝 만들기 ──────────────────────────────────────────────────────
    def dd(a, b):
        return None if (a is None or b is None) else round(b - a, 3)

    pairs, dead_pairs = [], []
    for gk, byd in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(byd) < 2:
            continue
        depths = sorted(byd)
        lo = depths[0]
        for hi in depths[1:]:
            for k1 in byd[lo]:
                for kN in byd[hi]:
                    a, b = cells[k1], cells[kN]
                    if a["el_deg"] != b["el_deg"]:
                        continue
                    if a["zero_echo"] and b["zero_echo"]:
                        dead_pairs.append(dict(
                            combo=a["combo"], combo_ko=a["combo_ko"], el_deg=a["el_deg"],
                            depths=[lo, hi], d1=k1, dN=kN, range_m=a["range_m"],
                            npaths_d1=a["npaths_median_ledger"], npaths_dN=b["npaths_median_ledger"],
                            why_ko="두 판 모두 경로 0 — 깊이가 바꿀 것이 없다"))
                        continue
                    el = a["el_deg"]
                    # ── 읽어도 되나: 잣대마다 따로 정한다 ─────────────────
                    hard = [f for f in ("near_numeric_floor", "no_motion", "incomplete", "no_return")
                            if a[f] or b[f]]
                    lvl_ok = not hard
                    tip_ok = lvl_ok and not (a["tip_ceiling_degenerate"] or b["tip_ceiling_degenerate"])
                    comb_ok = lvl_ok and a["comb_contrast_db"] is not None and b["comb_contrast_db"] is not None
                    beat_ok = lvl_ok and not (a["beat_spiky"] or b["beat_spiky"])
                    row = dict(
                        combo=a["combo"], combo_ko=a["combo_ko"], el_deg=el, depths=[lo, hi],
                        range_m=a["range_m"], az_deg=a["az_deg"], airframe=a["airframe"],
                        parts=a["parts"], d1=k1, dN=kN, n_poses=a["n_poses"],
                        in_standard_frame=bool(a["combo"] in STANDARD_FRAME_COMBOS),
                        switches=dict(R=a["refraction"], D=a["diffraction"],
                                      E=a["edge"], F=a["diffuse"]),
                        seconds_d1=a["seconds"], seconds_dN=b["seconds"],
                        cost_ratio=(round(b["seconds"] / a["seconds"], 3)
                                    if (a["seconds"] or 0) > 0 else None),
                        # ── 짝별 차이 (전부 dN − d1) ──────────────────────
                        d_moving_power_db=dd(a["moving_power_db"], b["moving_power_db"]),
                        d_above_floor_db=dd(a["above_floor_db"], b["above_floor_db"]),
                        d_above_comb_db=dd(a["above_comb_db"], b["above_comb_db"]),
                        d_comb_over_floor_db=dd(a["comb_over_floor_db"], b["comb_over_floor_db"]),
                        d_comb_contrast_db=dd(a["comb_contrast_db"], b["comb_contrast_db"]),
                        d_rhythm_pp=dd(a["rhythm_share_pct"], b["rhythm_share_pct"]),
                        d_above_ceiling_pp=dd(a["above_ceiling_energy_pct"], b["above_ceiling_energy_pct"]),
                        d_beat_hz=dd(a["beat_hz"], b["beat_hz"]),
                        d_ledger_level_db=dd(a["ledger_level_db"], b["ledger_level_db"]),
                        rhythm_d1_pct=a["rhythm_share_pct"], rhythm_dN_pct=b["rhythm_share_pct"],
                        rhythm_null_pct=a["rhythm_null_pct"],
                        comb_d1_db=a["comb_contrast_db"], comb_dN_db=b["comb_contrast_db"],
                        npaths_d1=a["npaths_median_ledger"], npaths_dN=b["npaths_median_ledger"],
                        npaths_ratio=(round(b["npaths_median_ledger"] / a["npaths_median_ledger"], 4)
                                      if (a["npaths_median_ledger"] or 0) > 0 else None),
                        ac_over_dc_d1=a["ac_over_dc"], ac_over_dc_dN=b["ac_over_dc"],
                        flags_d1=[f for f in ("near_numeric_floor", "tip_ceiling_degenerate",
                                              "no_motion", "incomplete", "beat_spiky") if a[f]],
                        flags_dN=[f for f in ("near_numeric_floor", "tip_ceiling_degenerate",
                                              "no_motion", "incomplete", "beat_spiky") if b[f]],
                        readable=dict(level=lvl_ok, above_tip=tip_ok, comb=comb_ok, beat=beat_ok),
                        hard_flags=hard)
                    # ── 파형 상관 · 담김계수 · ⭐얹힌 항의 성격 ────────────
                    e0 = np.asarray(Z[k1], complex); e0 = e0 - e0.mean()
                    e1 = np.asarray(Z[kN], complex); e1 = e1 - e1.mean()
                    if np.any(e0) and np.any(e1):
                        co = np.vdot(e0, e1) / np.vdot(e0, e0)
                        res = e1 - e0
                        sig = float(np.linalg.norm(res) / (np.linalg.norm(e0) * np.sqrt(e0.size)))
                        rr = A.rhythm_share(res, a["f_flash_hz"], a["f_tip_hz"])[0]
                        rrc = A.comb_contrast_db(res, a["f_flash_hz"], a["f_tip_hz"])
                        row.update(
                            abs_rho=round(float(abs(np.vdot(e0, e1))
                                                / (np.linalg.norm(e0) * np.linalg.norm(e1))), 6),
                            rho_null=round(float(1.0 / np.sqrt(e0.size)), 6),
                            contain_coeff=round(float(abs(co)), 6),
                            contain_phase_deg=round(float(np.degrees(np.angle(co))), 3),
                            contain_sigma=round(sig, 6),
                            contains_unit_within_3sigma=bool(sig > 0 and abs(abs(co) - 1.0) <= 3 * sig),
                            residual_over_d1_db=round(float(10 * np.log10(
                                np.mean(np.abs(res) ** 2) / np.mean(np.abs(e0) ** 2))), 3),
                            residual_rhythm_pct=(None if rr is None else round(rr, 2)),
                            residual_comb_contrast_db=(None if rrc is None else round(rrc, 2)),
                            bit_identical=bool(np.array_equal(np.asarray(Z[k1]), np.asarray(Z[kN]))))
                        # ⭐얹힌 항이 «날개 박자를 아는가» — 백색 널은 칸마다 정확히 셀 수 있다
                        nul = a["rhythm_null_pct"]
                        row["residual_carries_rhythm"] = bool(
                            tip_ok and rr is not None and nul is not None and rr > 2.0 * nul)
                        row["residual_character_ko"] = (
                            "판정 불가(상한 퇴화)" if not tip_ok else
                            ("표적 에코 — 얹힌 항이 날개 박자를 안다"
                             if row["residual_carries_rhythm"] else
                             "구조 없음 — 얹힌 항이 백색(널 수준)"))
                    # ── ⭐튐 진단 + 이상 자세 솎기 ─────────────────────────
                    row["spike_d1"] = spike_stats(Z[k1])
                    row["spike_dN"] = spike_stats(Z[kN])
                    row["trim"] = {}
                    for kt in TRIM_K:
                        t = trimmed_metrics(Z[k1], Z[kN], a["f_flash_hz"], a["f_tip_hz"], kt)
                        if t:
                            row["trim"][f"k{kt}"] = t
                    hl = row["trim"].get(f"k{TRIM_HEADLINE}") or row["trim"].get("k0")
                    row["trim_headline_k"] = TRIM_HEADLINE
                    # 솎기가 결론을 바꾸나 — 이상 자세 의존성
                    raw = row["trim"].get("k0")
                    row["outlier_driven"] = bool(
                        raw and hl and raw["d_rhythm_pp"] is not None and hl["d_rhythm_pp"] is not None
                        and abs(raw["d_rhythm_pp"] - hl["d_rhythm_pp"]) > 5.0)

                    # ── 밴드 대조 (⭐헤드라인은 솎은 판) ───────────────────
                    band = GRID_BAND_AC_DB.get(el)
                    row["grid_band_ac_db_at_el"] = band
                    # ⭐2026-08-18: 밴드가 **없는** 앙각에서 조용히 «안 유의» 로 넘어가지 않는다.
                    #   레벨 판정 밴드는 λ/12↔λ/24 격자 사다리에서 나오는데, 새로 채운 앙각
                    #   (−52·−68·−82)에는 그 사다리가 없다. band is None 이면 sig_lv 가 무조건
                    #   False 가 되어 «잣대가 없다» 가 «차이가 없다» 로 읽힌다 — 그것을 막는다.
                    row["level_band_missing"] = band is None
                    if band is None:
                        row["level_verdict_ko"] = (
                            "⛔판정 불가 — 이 앙각에는 격자 산포 밴드가 없다(λ/24 판이 없어 "
                            "잣대를 못 만든다). ⚠«안 유의» 와 **다르다**")
                    row["grid_band_rhythm_pp"] = GRID_BAND_RHYTHM_PP_GLOBAL
                    row["grid_band_comb_db"] = GRID_BAND_COMB_DB_GLOBAL
                    row["grid_band_above_ceiling_pp"] = GRID_BAND_ABOVE_PP_GLOBAL
                    row["grid_band_ac_db_at_el_note_ko"] = (
                        "레벨만 앙각별 밴드를 쓴다(2026-08-16 정정). 리듬 몫 21.8 %p 는 R16 정본 "
                        "유지값이고, 빗살 대비 4.04 dB 는 격자 계단(+4.04~+5.6 dB)의 보수적 하한, "
                        "상한 위 몫 12.55 %p 는 R16 전앙각 최대다 — 앙각별 단일 측정값은 "
                        "grid_band_by_el_reference 에 참고로만 싣는다.")
                    row["grid_band_by_el_reference"] = dict(
                        rhythm_pp=GRID_BAND_RHYTHM_PP_BY_EL.get(el),
                        comb_db=GRID_BAND_COMB_DB_BY_EL.get(el))
                    hv = hl or {}
                    dlv = hv.get("d_moving_power_db", row["d_moving_power_db"])
                    drh = hv.get("d_rhythm_pp", row["d_rhythm_pp"])
                    dcb = hv.get("d_comb_contrast_db", row["d_comb_contrast_db"])
                    dab = hv.get("d_above_ceiling_pp", row["d_above_ceiling_pp"])
                    sig_lv = bool(lvl_ok and band is not None and dlv is not None and abs(dlv) > band)
                    sig_rh = bool(tip_ok and drh is not None and abs(drh) > GRID_BAND_RHYTHM_PP_GLOBAL)
                    sig_cb = bool(comb_ok and dcb is not None and abs(dcb) > GRID_BAND_COMB_DB_GLOBAL)
                    sig_ab = bool(tip_ok and dab is not None and abs(dab) > GRID_BAND_ABOVE_PP_GLOBAL)
                    row["level_outside_band"] = sig_lv
                    row["rhythm_outside_band"] = sig_rh
                    row["comb_outside_band"] = sig_cb
                    row["above_ceiling_outside_band"] = sig_ab
                    row["inside_seed_band"] = bool(dlv is not None and abs(dlv) <= 2 * SEED_SD_DB)
                    row["moves_the_reading"] = bool(sig_rh or sig_cb or sig_ab)
                    # ⭐앙각별 밴드로도 채점해서 **나란히** 싣는다 — 전역 밴드(리듬 21.8 %p ·
                    #   빗살 4.04 dB)는 보수적이라 «판정 불가» 쪽으로 기운다. 어느 쪽으로 기울든
                    #   숨기지 않으려고 두 채점을 함께 낸다(2026-08-16 적대검산).
                    bcb = GRID_BAND_COMB_DB_BY_EL.get(el)
                    brh = GRID_BAND_RHYTHM_PP_BY_EL.get(el)
                    sig_cb_el = bool(comb_ok and dcb is not None and bcb is not None
                                     and abs(dcb) > bcb)
                    sig_rh_el = bool(tip_ok and drh is not None and brh is not None
                                     and abs(drh) > brh)
                    row["comb_outside_band_by_el"] = sig_cb_el
                    row["rhythm_outside_band_by_el"] = sig_rh_el
                    row["moves_the_reading_by_el_band"] = bool(sig_rh_el or sig_cb_el or sig_ab)
                    # «둘 다 백색 널 자리인가» — 잣대가 움직여도 읽기가 안 바뀌는 자리를 가른다
                    cd1, cdN = hv.get("comb_d1_db"), hv.get("comb_dN_db")
                    row["both_sides_at_comb_null"] = bool(
                        cd1 is not None and cdN is not None
                        and abs(cd1) <= COMB_NULL_DB and abs(cdN) <= COMB_NULL_DB)
                    row["band_scorings_disagree"] = bool(
                        row["moves_the_reading"] != row["moves_the_reading_by_el_band"])
                    row["band_scoring_note_ko"] = (
                        None if not row["band_scorings_disagree"] else
                        ("⭐전역 밴드로는 «판정 불가», **그 앙각의 밴드로는 밴드 밖**이다. "
                         + ("다만 빗살 대비가 양쪽 다 백색 널 자리(|R| ≤ %.0f dB)라 "
                            "«빗살 없음» 이라는 읽기 자체는 안 바뀐다." % COMB_NULL_DB
                            if row["both_sides_at_comb_null"] else
                            "⚠양쪽이 널 자리도 아니다 — 이 칸은 «판독이 바뀌었을 수 있다» 로 남긴다.")))
                    row["level_move_trivial"] = bool(sig_lv and dlv is not None and abs(dlv) < 0.5)
                    row["verdict_ko"] = (
                        "판정 불가 — 하드 깃발" if hard else
                        ("⭐깊이가 판독을 바꾼다" if row["moves_the_reading"] else
                         (("깊이가 레벨을 아주 조금 움직인다(밴드 밖이나 0.5 dB 미만 — "
                           "그 앙각 밴드가 극도로 좁아서다)" if row["level_move_trivial"] else
                           "깊이가 레벨만 움직인다(판독 불변)") if sig_lv else
                          "밴드 안 — 판정 불가(«안 바뀐다»로 단정 못 한다)")))
                    if row["outlier_driven"]:
                        row["verdict_ko"] += " ⚠생값은 자세 하나가 끌었다(솎은 값으로 판정)"
                    # R13 사전등록 B 문안 그대로 (2 dB · 3 %p)
                    lv = [abs(v) for v in (row["d_moving_power_db"], row["d_above_floor_db"],
                                           row["d_above_comb_db"], row["d_ledger_level_db"])
                          if v is not None]
                    row["max_abs_level_db"] = round(max(lv), 3) if lv else None
                    row["r13_level_within_2db"] = bool(lv and max(lv) < DB_SAME)
                    row["r13_rhythm_within_3pp"] = bool(row["d_rhythm_pp"] is not None
                                                        and abs(row["d_rhythm_pp"]) < PP_SAME)
                    row["r13_pass"] = bool(row["r13_level_within_2db"] and row["r13_rhythm_within_3pp"])
                    pairs.append(row)

    pairs.sort(key=lambda r: (r["range_m"], r["combo"], -r["el_deg"], r["depths"][1]))

    # ── 2-3. 샤드 npaths 분포 + cfg 비트 검증 ───────────────────────────────
    npaths_tbl = []
    for r in pairs:
        a, b = cells[r["d1"]], cells[r["dN"]]
        sa, sb = shard_npaths(a["arm"], a["el_deg"]), shard_npaths(b["arm"], b["el_deg"])
        if not (sa and sb):
            continue
        npaths_tbl.append(dict(
            pair=f"{r['combo']}_d{r['depths'][0]}→d{r['depths'][1]} · el{r['el_deg']:+.0f}"
                 f" · {r['range_m']:.0f} m",
            d1=a["arm"], dN=b["arm"], d1_cfg=sa.get("cfg"), dN_cfg=sb.get("cfg"),
            cfg_layout_ko="[거리, 깊이, 광선, 물리, R, D, E] — 옛 샤드는 앞 4 칸만",
            cfg_depth_ok=bool(sa.get("cfg") and sb.get("cfg")
                              and int(sa["cfg"][1]) == r["depths"][0]
                              and int(sb["cfg"][1]) == r["depths"][1]),
            d1_median=sa.get("median"), dN_median=sb.get("median"),
            d1_mean=sa.get("mean"), dN_mean=sb.get("mean"),
            d1_p90=sa.get("p90"), dN_p90=sb.get("p90"),
            d1_max=sa.get("max"), dN_max=sb.get("max"),
            mean_ratio=(round(sb["mean"] / sa["mean"], 4)
                        if sa.get("mean") and sb.get("mean") else None)))

    # ── 2-4. PathSolver 재현성 앵커 ─────────────────────────────────────────
    alias = [("sionna_p4000000000_onlyrefr_mini5pro_r15_n8192",
              "sionna_p4000000000_swR1D0E0F1_mini5pro_r15_n8192_d1", (0.0, -30.0, -60.0)),
             ("sionna_p4000000000_onlyrefr_s1000plus_r15_n8192",
              "sionna_p4000000000_swR1D0E0F1_s1000plus_r15_n8192_d1", (0.0, -30.0, -60.0))]

    def _rerun_row(x, y, el):
        kx, ky = f"{x}/el{el:+.0f}", f"{y}/el{el:+.0f}"
        if kx not in Z.files or ky not in Z.files:
            return None
        a0, b0 = np.asarray(Z[kx], complex), np.asarray(Z[ky], complex)
        e0, e1 = a0 - a0.mean(), b0 - b0.mean()
        with np.errstate(divide="ignore", invalid="ignore"):
            relp = np.abs(a0 - b0) / np.abs(a0)
        relp = np.nan_to_num(relp, nan=0.0, posinf=0.0)
        return dict(
            a=x, b=y, el_deg=el,
            bit_identical=bool(np.array_equal(a0, b0)),
            #: 마지막 비트까지 따진 수 — 거의 모든 자세가 여기 걸린다(의미 없음)
            n_poses_differing_any_bit=int(np.count_nonzero(a0 != b0)),
            #: ⭐**뜻이 있는** 차이 — 상대차 1e-9 을 넘는 자세만 센다
            n_poses_differing=int(np.count_nonzero(relp > 1e-9)),
            max_rel_pose_diff=float(f"{float(relp.max()):.3g}"),
            d_moving_power_db=float(f"{10 * np.log10(np.mean(np.abs(e1) ** 2) / np.mean(np.abs(e0) ** 2)):.3e}"),
            one_minus_abs_rho=float(f"{1.0 - abs(np.vdot(e0, e1)) / (np.linalg.norm(e0) * np.linalg.norm(e1)):.3e}"))

    rerun = []
    for x, y, els in alias:
        for el in els:
            r = _rerun_row(x, y, el)
            if r:
                rerun.append(r)
    rerun_band = max(abs(r["d_moving_power_db"]) for r in rerun) if rerun else None

    # ⭐회절 켠 팔의 재현성은 **따로** 잰다 — 위 여섯 칸은 전부 회절 **끈** 팔이라
    #   그 결과(≤1e-14 dB)를 회절 켠 팔에 그대로 옮기면 안 된다. 회절을 켜면 쐐기 표집이
    #   난수를 쓰므로 «같은 물리·다른 이름» 두 판이 자세 몇 개에서 갈린다.
    #   모서리 E 는 회절 D 안에서 **자유 모서리**(prim0 == primn)에만 걸리는 스위치라
    #   닫힌 메쉬에서는 경로를 사실상 안 바꾼다 — 그래서 E0↔E1 두 판을 «같은 물리의 재실행»
    #   으로 쓰되, 그 차이가 0 이 아니라는 사실 자체를 밴드로 싣는다.
    alias_d1 = [("sionna_p4000000000_swR0D1E0F0_r15_n8192_d1",
                 "sionna_p4000000000_swR0D1E1F0_r15_n8192_d1"),
                ("sionna_p4000000000_swR1D1E0F0_r15_n8192_d1",
                 "sionna_p4000000000_swR1D1E1F0_r15_n8192_d1"),
                ("sionna_p4000000000_onlydiffr_r15_n8192",
                 "sionna_p4000000000_swR0D1E1F1_r15_n8192_d1"),
                ("sionna_p4000000000_swR0D1E0F0_r15_n8192_d3",
                 "sionna_p4000000000_swR0D1E1F0_r15_n8192_d3"),
                ("sionna_p4000000000_swR1D1E0F0_r15_n8192_d3",
                 "sionna_p4000000000_swR1D1E1F0_r15_n8192_d3"),
                ("sionna_p4000000000_swR0D1E0F1_r15_n8192_d3",
                 "sionna_p4000000000_swR0D1E1F1_r15_n8192_d3"),
                ("sionna_p4000000000_swR1D1E0F1_r15_n8192_d3",
                 "sionna_p4000000000_swR1D1E1F1_r15_n8192_d3")]
    rerun_d1on = []
    for x, y in alias_d1:
        r = _rerun_row(x, y, -30.0)
        if r:
            rerun_d1on.append(r)
    rerun_band_diffr_on = (max(abs(r["d_moving_power_db"]) for r in rerun_d1on)
                           if rerun_d1on else None)

    # ── 2-5. ⭐튕김 사다리 — 한 칸에서 깊이 1·2·3 이 다 있는 자리 ──────────
    ladder = None
    kk = ["sionna_p4000000000_phys_r15_n8192_d1/el-30",
          "sionna_p4000000000_phys_r15_n8192_d2/el-30",
          "sionna_p4000000000_swR1D1E1F1_r15_n8192_d3/el-30"]
    if all(k in Z.files for k in kk):
        Es = [np.asarray(Z[k], complex) for k in kk]
        Aa = [e - e.mean() for e in Es]
        P = [float(np.mean(np.abs(v) ** 2)) for v in Aa]
        ladder = dict(
            combo="R1D1E1F1", el_deg=-30.0, range_m=15.0, keys=kk,
            ac_db=[round(10 * np.log10(p), 3) for p in P],
            power_ratio_to_d1=[round(p / P[0], 4) for p in P],
            added_by_2nd_bounce_rel_d1=round((P[1] - P[0]) / P[0], 4),
            added_by_3rd_bounce_rel_d1=round((P[2] - P[1]) / P[0], 4),
            third_over_second=round((P[2] - P[1]) / (P[1] - P[0]), 3),
            abs_rho_d1_d2=round(float(abs(np.vdot(Aa[0], Aa[1]))
                                      / (np.linalg.norm(Aa[0]) * np.linalg.norm(Aa[1]))), 4),
            abs_rho_d2_d3=round(float(abs(np.vdot(Aa[1], Aa[2]))
                                      / (np.linalg.norm(Aa[1]) * np.linalg.norm(Aa[2]))), 4),
            npaths_median=[cells[k]["npaths_median_ledger"] for k in kk],
            expectation_ko="물리적 다중 반사 급수라면 튕김마다 더해지는 에너지가 **줄어야** 한다"
                           "(표적은 손실이 있고 매 튕김마다 일부만 되돌아온다).",
            observed_ko=None)
        ladder["observed_ko"] = (
            f"세 번째 튕김이 두 번째 튕김의 **{ladder['third_over_second']:.1f} 배**를 더한다 — "
            "급수가 줄지 않는다. 감쇠하는 물리 급수의 모양이 아니다.")
        ladder["decaying_series"] = bool(ladder["third_over_second"] < 1.0)
        # 솎아도 같은가
        rel = np.maximum.reduce([np.abs(v) / np.median(np.abs(v)) for v in Aa])
        rob = {}
        for kt in TRIM_K:
            msk = np.ones(Aa[0].size, bool)
            if kt:
                msk[np.argsort(rel)[::-1][:kt]] = False
            Pk = [float(np.mean(np.abs(v[msk] - v[msk].mean()) ** 2)) for v in Es]
            rob[f"k{kt}"] = round((Pk[2] - Pk[1]) / (Pk[1] - Pk[0]), 3)
        ladder["third_over_second_trimmed"] = rob
        ladder["robust_ko"] = "가장 튄 자세 1·8 개를 빼도 4.7~4.9 로 그대로다 — 튐 탓이 아니다."

    # ── 2-6. ⭐튐 census — 짝에 쓰인 칸 전부 ────────────────────────────────
    spike_census = []
    for k in sorted({r[e] for r in pairs for e in ("d1", "dN")}):
        s = spike_stats(Z[k])
        if s:
            spike_census.append(dict(cell=k, **s))
    spike_census.sort(key=lambda r: -r["isolation"])
    iso_med = float(np.median([r["isolation"] for r in spike_census])) if spike_census else None
    isolated = [r for r in spike_census if r["isolation"] > 2.0]

    # ── 2-7. ⭐−60° 단일 자세 감식 — R13 «종결 불가» 근거 ② 를 직접 겨눈다 ──
    forensic = None
    fk1, fk3 = ("sionna_p4000000000_r15_n8192_d1/el-60",
                "sionna_p4000000000_onlydepth3_r15_n8192/el-60")
    if fk1 in Z.files and fk3 in Z.files:
        rt = A.arm_rates("sionna_p4000000000_r15_n8192_d1")
        ft6, ffl6 = A.f_tip_at(rt, -60.0), rt["f_flash_hz"]
        E1, E3 = np.asarray(Z[fk1], complex), np.asarray(Z[fk3], complex)
        x3 = E3 - E3.mean()
        ip = int(np.argmax(np.abs(x3)))
        nb = np.abs(E3[max(ip - 3, 0):ip + 4])
        halves = []
        for lab, sl in (("A", slice(0, E1.size // 2)), ("B", slice(E1.size // 2, E1.size))):
            r1 = A.rhythm_share(E1[sl], ffl6, ft6)[0]
            r3 = A.rhythm_share(E3[sl], ffl6, ft6)[0]
            halves.append(dict(half=lab, rhythm_d1_pct=round(r1, 2), rhythm_dN_pct=round(r3, 2),
                               contains_the_pose=bool(sl.start <= ip < sl.stop)))
        sh = shard_npaths("sionna_p4000000000_onlydepth3_r15_n8192", -60.0)

        def _npaths_at(arm, el, pose):
            """⭐그 자세 하나의 경로 수 — 샤드의 idx 열로 되짚는다.
            (예전 판은 여기를 못 채우고 None 을 냈는데 본문은 «경로 수도 정상» 이라고
             적고 있었다 — 근거 없는 문장이 되지 않게 실제로 센다.)"""
            got = None
            for f in sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz")):
                z = np.load(f)
                if "idx" in z and "npaths" in z:
                    w = np.where(np.asarray(z["idx"]) == pose)[0]
                    if w.size:
                        got = int(np.asarray(z["npaths"])[w[0]])
                z.close()
            return got
        forensic = dict(
            what_ko="R13 이 «깊이 축 종결 불가» 의 근거 ② 로 든 칸 — el −60° · PS 다 끔 · 15 m",
            r13_number_ko="AC 는 +0.09 dB 로 같은데 상한 위 바닥만 +12.7 dB 오르고 리듬이 "
                          "86.6 → 32.4 %(−54.3 %p) 로 무너진다",
            reproduced_on_merged_ledger=True,
            culprit_pose_index=ip, n_poses=int(E1.size),
            pose_abs_E_dN=float(f"{abs(E3[ip]):.4g}"), pose_abs_E_d1=float(f"{abs(E1[ip]):.4g}"),
            neighbour_abs_E_dN=[float(f"{v:.4g}") for v in nb],
            pose_over_median_dN=round(float(np.abs(x3)[ip] / np.median(np.abs(x3))), 2),
            isolation_dN=spike_stats(E3)["isolation"], isolation_d1=spike_stats(E1)["isolation"],
            npaths_at_pose=_npaths_at("sionna_p4000000000_onlydepth3_r15_n8192", -60.0, ip),
            npaths_at_pose_d1=_npaths_at("sionna_p4000000000_r15_n8192_d1", -60.0, ip),
            npaths_median_dN=(None if sh is None else sh.get("median")),
            npaths_range_dN=(None if sh is None else [sh.get("min"), sh.get("max")]),
            rotor_symmetry_partners_over_median=[
                round(float(np.abs(x3)[(ip + q * (E1.size // 4)) % E1.size]
                            / np.median(np.abs(x3))), 2) for q in range(4)],
            split_half=halves,
            drop_one_pose=trimmed_metrics(E1, E3, ffl6, ft6, 1),
            drop_eight_poses=trimmed_metrics(E1, E3, ffl6, ft6, 8),
            verdict_ko="⭐**자세 8192 개 중 하나**(#" + str(ip) + ")가 이 칸의 붕괴를 통째로 끌었다. "
                       "그 자세의 |E| 는 이웃의 약 5 배(전력 25 배)인데 이웃도, 로터 4 회 대칭 짝도, "
                       "경로 수도 정상이다(그 자세 경로 수는 npaths_at_pose 열에 실제로 실었다 — "
                       "중앙값 대비 정상 범위) — 구조적 정반사 플래시라면 여러 자세에 같이 서야 한다. "
                       "그 자세 **하나만 빼면** 두 판이 리듬 85.5 ↔ 85.2 %, 빗살 대비 45.4 ↔ 45.3 dB "
                       "로 일치한다. ⇒ R13 의 근거 ② 는 **깊이 효과가 아니라 자세 하나의 튐**이다.",
            adversarial_recheck_0816_ko="⭐적대검산 — «자세를 빼는 것» 자체가 잣대를 흔든 것 아닌가를 "
                                        "따로 검사했다. ①그 자세를 **삭제**하지 않고 이웃 평균으로 "
                                        "**갈아 끼우면**(표집 간격을 안 깨는 방법) 리듬이 32.4 → 86.4 % "
                                        "로 같은 자리로 돌아온다. ②죄 없는 자세 하나를 빼는 검사를 40 번 "
                                        "돌리면 리듬이 ±0.3 %p 밖에 안 움직인다 — 삭제 자체는 무해하다. "
                                        "③그 자세는 다른 어느 칸에서도 안 튄다(전 칸 훑음). "
                                        "⇒ 튐 판정은 세 방법이 같은 답을 낸다.")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. 물음에 답하기
    # ═══════════════════════════════════════════════════════════════════════
    p13 = [r for r in pairs if r["depths"] == [1, 3]]
    p12 = [r for r in pairs if r["depths"] == [1, 2]]
    live = [r for r in p13 if r["readable"]["level"]]

    def stat(sel, key):
        v = [r[key] for r in sel if r.get(key) is not None]
        return (dict(n=len(v), min=round(min(v), 3), max=round(max(v), 3),
                     median=round(float(np.median(v)), 3),
                     max_abs=round(max(abs(x) for x in v), 3)) if v else None)

    D_on = [r for r in live if r["switches"]["D"]]
    D_off = [r for r in live if not r["switches"]["D"]]
    R_on = [r for r in live if r["switches"]["R"]]
    R_off = [r for r in live if not r["switches"]["R"]]
    sf = [r for r in p13 if r["in_standard_frame"]]

    def hl(r, key):
        """⭐헤드라인은 «가장 튄 자세 하나를 뺀» 판 — 생값은 raw_ 로 따로 싣는다."""
        t = (r.get("trim") or {}).get(f"k{TRIM_HEADLINE}")
        if t and key in t and t[key] is not None:
            return t[key]
        return r.get(key)

    def hstat(sel, key):
        v = [hl(r, key) for r in sel if hl(r, key) is not None]
        return (dict(n=len(v), min=round(min(v), 3), max=round(max(v), 3),
                     median=round(float(np.median(v)), 3),
                     max_abs=round(max(abs(x) for x in v), 3)) if v else None)

    #: 경로가 실제로 늘어난 짝만 — 확산 끈 조합은 경로 8 개 고정이라 깊이가 손댈 것이 없다
    live_paths = [r for r in live if (r["npaths_ratio"] or 0) > 1.01]

    ans_a = dict(
        question_ko="ⓐ 광선을 세 번까지 튕기게 하면 표적 신호가 커지나 안 바뀌나",
        n_pairs=len(p13), n_pairs_level_readable=len(live),
        npaths_ratio_all=stat(p13, "npaths_ratio"),
        npaths_ratio_where_paths_grow=stat(live_paths, "npaths_ratio"),
        d_moving_power_db=hstat(live, "d_moving_power_db"),
        d_moving_power_db_raw=stat(live, "d_moving_power_db"),
        contain_coeff=hstat(live, "contain_coeff"),
        residual_over_d1_db=hstat(live, "residual_over_d1_db"),
        residual_over_d1_db_diffraction_off=hstat(
            [r for r in live if not r["switches"]["D"]], "residual_over_d1_db"),
        residual_rhythm_pct_diffraction_off=hstat(
            [r for r in live if not r["switches"]["D"]], "residual_rhythm_pct"),
        residual_rhythm_pct_diffraction_on=hstat(
            [r for r in live if r["switches"]["D"]], "residual_rhythm_pct"),
        answer_ko="**커진다. 다만 아주 조금이고, 커진 것의 정체가 조합에 따라 갈린다.** "
                  "깊이 3 은 경로를 실제로 **더 찾는다** — 경로가 늘 수 있는 짝 11 개에서 중앙값 "
                  "×1.04~1.14 이고, 경로 중앙값이 **줄어든 짝은 0** 이다(나머지 네 칸은 확산을 "
                  "꺼서 8→8 로 제자리). 찾은 것은 원래 신호를 바꾸지 않고 **위에 얹는다**"
                  " — 담김계수 a = 0.95~1.02, 위상 ≈0°. 얹힌 항의 크기와 성격이 갈린다. "
                  "회절을 **끈** 팔(우리가 쓰는 팔)에서는 빗각 다섯 칸 전부 원 신호보다 **16~23 dB 아래**이고 "
                  "**날개 박자를 갖고 있다**(얹힌 항의 리듬 몫 52~85 % ≫ 백색 널 12.6 %) — "
                  "즉 진짜 다중 반사 표적 에코다. 회절을 **켠** 팔에서는 1.4~4.3 dB 아래로 크지만 "
                  "**백색**이다(11.2~12.3 % = 널). ⚠그 백색은 **깊이의 성질이 아닐 수 있다** — "
                  "그 팔은 깊이 1 판부터 이미 백색이라(리듬 몫 11.7~12.1 %) 얹힌 항이 백색인 것이 "
                  "새 정보가 아니다(2026-08-16 적대검산 정정). "
                  "⇒ «작은 표적엔 다중 경로가 안 생긴다» 는 **틀렸다** — 생긴다. "
                  "«표적 신호가 커진다» 도 과장이다 — 우리 팔에서 그것은 −16~−23 dB 짜리 곁가지라 "
                  "판독을 못 바꾼다. ⚠«16~23 dB» 의 범위는 **빗각**(−30 · −60°)과 거리 팔(30 · 120 m)의 "
                  "다섯 칸이다. 정면 0° 는 −3.1 dB 로 크고 백색인데, 그 칸은 깊이를 손대기 전에 "
                  "이미 상한 위가 백색(익사)이라 «깊이가 백색을 얹었다» 로 못 읽는다. "
                  "직하방 −90° 는 상한 잣대가 퇴화한 칸이다.",
        caveat_ko="⚠확산 F 를 끈 조합(R0D1E0F0 · R0D1E1F0 · R1D1E0F0 · R1D1E1F0)은 빗각에서 경로가 "
                  "8 개뿐이고 깊이 3 에서도 8 개다(8.04→8.06). 그 칸의 «깊이가 안 늘린다» 는 "
                  "깊이의 성질이 아니라 **경로원이 없어서**다.")

    ans_b = dict(
        question_ko="ⓑ 깊이 효과가 스위치 조합에 따라 달라지나",
        answer_ko="**갈린다 — 회절 D 스위치 하나가 가른다.** 회절을 끄면 깊이 3 의 요동 절대전력 "
                  "변화가 −0.39~+1.72 dB 이고, 켜면 +1.32~+2.33 dB 로 한 묶음이 된다. "
                  "회절을 **끈** 팔에서는 얹힌 항이 날개 박자를 갖는다(리듬 몫 52~85 %, 널 12.6 %) — "
                  "원 신호(60~86 %)와 같은 얼굴이니 **로터를 거친 진짜 에코**로 읽는다. "
                  "⚠회절을 **켠** 팔에서 얹힌 항이 백색(11.2~12.3 %)인 것은 **판별 근거가 못 된다** "
                  "— 그 팔은 원 신호부터 이미 백색이라(리듬 몫 11.7~12.1 % = 널) 무엇을 얹든 백색으로 "
                  "나온다(2026-08-16 적대검산 정정). 그래서 «깊이가 회절 항을 한 번 더 태워 나른다» 는 "
                  "**그럴듯한 후보**이지 이 원장이 세운 사실이 아니다 — 가르려면 깊이 3 에서 광선 사다리를 "
                  "돌려야 한다. 모서리 E 는 회절이 꺼져 있으면 무동작이고, 켜져 있으면 «거의» 무동작이다 "
                  "(자세 8~26 개 · 최대 0.07 dB — answers.b.edge_is_noop_ko). 확산 F 를 끄면 빗각에서 "
                  "경로가 8 개뿐이라 깊이가 늘릴 경로 자체가 없다.",
        diffraction_on=dict(n=len(D_on), d_moving_power_db=hstat(D_on, "d_moving_power_db"),
                            residual_over_d1_db=hstat(D_on, "residual_over_d1_db"),
                            residual_rhythm_pct=hstat(D_on, "residual_rhythm_pct")),
        diffraction_off=dict(n=len(D_off), d_moving_power_db=hstat(D_off, "d_moving_power_db"),
                             residual_over_d1_db=hstat(D_off, "residual_over_d1_db"),
                             residual_rhythm_pct=hstat(D_off, "residual_rhythm_pct")),
        refraction_on=dict(n=len(R_on), d_moving_power_db=hstat(R_on, "d_moving_power_db")),
        refraction_off=dict(n=len(R_off), d_moving_power_db=hstat(R_off, "d_moving_power_db")),
        edge_is_noop_ko="⭐**모서리 E 는 «거의» 무동작이지 «완전» 무동작이 아니다**(2026-08-16 적대검산 "
                        "정정). 회절 D 가 꺼져 있으면 소스 게이트에 막혀 진짜로 무동작이다. 그러나 "
                        "**회절을 켠 판**에서는 E 가 자유 모서리에 걸리고 난수 흐름도 갈려서, 같은 물리 "
                        "두 판(E0↔E1)이 자세 8192 개 중 **8~26 개**에서 갈린다(그 자세의 |E| 는 최대 "
                        "23 % 차). 그 결과 경로 수 평균이 1e-4 자리에서 다르고(8.0444↔8.0441 · "
                        "1589.9183↔1589.9182 · 382.2659↔382.2662) 요동 절대전력이 최대 **0.07 dB** "
                        "흔들린다. ⇒ «소수점까지 같다» 로 쓰면 안 되고, 그 0.07 dB 는 회절 켠 팔의 "
                        "**재실행 문턱**으로 쓴다(null_bands.pathsolver_repeatability.diffraction_on). "
                        "깊이 효과 +1.32~+2.33 dB 는 그 문턱의 19~33 배라 살아남는다.",
        diffuse_off_paths_ko="확산 F 를 끈 조합은 경로가 8 개다 — 깊이 3 에서도 8 개.",
        per_combo={})
    for r in p13:
        ans_b["per_combo"].setdefault(r["combo"], []).append(dict(
            el_deg=r["el_deg"], range_m=r["range_m"],
            d_moving_power_db=hl(r, "d_moving_power_db"),
            d_moving_power_db_raw=r["d_moving_power_db"],
            d_above_floor_db_raw=r["d_above_floor_db"],
            d_comb_contrast_db=hl(r, "d_comb_contrast_db"),
            d_rhythm_pp=hl(r, "d_rhythm_pp"),
            residual_over_d1_db=hl(r, "residual_over_d1_db"),
            residual_rhythm_pct=hl(r, "residual_rhythm_pct"),
            npaths_ratio=r["npaths_ratio"], outlier_driven=r["outlier_driven"],
            verdict_ko=r["verdict_ko"]))

    rng_rows = [r for r in p13 if r["combo"] == DEFAULT_COMBO and r["el_deg"] == -30.0]
    ans_c = dict(
        question_ko="ⓒ 깊이 효과가 거리에 따라 달라지나",
        answer_ko="**거리 의존을 주장할 근거가 없다**(«거리와 무관하다» 를 세운 것은 아니다 — "
                  "거리가 세 점뿐이다). PS 다 끔 팔의 el −30° 에서 깊이 3 의 "
                  "요동 절대전력 변화가 15 m −0.08 · 30 m −0.39 · 120 m +0.26 dB 로 **추세가 없고** "
                  "부호도 왔다 갔다 한다. 빗살 대비 변화는 +0.2 · −0.1 · −0.2 dB, 리듬 몫 변화는 "
                  "+0.10 · −0.33 · +0.14 %p 로 전부 밴드 안이다. 얹힌 항은 세 거리 모두 날개 박자를 "
                  "갖고(리듬 몫 69~79 %) 원 신호보다 17~21 dB 아래다 — 거리를 8 배 늘려도 그 관계가 "
                  "유지된다. ⚠30 m 의 −0.39 dB 만 −30° 밴드(0.37 dB)를 **0.02 dB 차로** 넘는데, "
                  "그 폭으로는 «거리 의존» 을 주장할 수 없다(15 m·120 m 가 반대 방향이다).",
        rows=[dict(range_m=r["range_m"],
                   d_moving_power_db=hl(r, "d_moving_power_db"),
                   d_moving_power_db_raw=r["d_moving_power_db"],
                   d_above_floor_db_raw=r["d_above_floor_db"],
                   d_comb_contrast_db=hl(r, "d_comb_contrast_db"),
                   d_rhythm_pp=hl(r, "d_rhythm_pp"),
                   residual_over_d1_db=hl(r, "residual_over_d1_db"),
                   residual_rhythm_pct=hl(r, "residual_rhythm_pct"),
                   abs_rho=hl(r, "abs_rho"), npaths_d1=r["npaths_d1"], npaths_dN=r["npaths_dN"],
                   ac_over_dc_d1=r["ac_over_dc_d1"], verdict_ko=r["verdict_ko"])
              for r in sorted(rng_rows, key=lambda x: x["range_m"])],
        scope_ko="⚠거리 축의 깊이 짝은 **PS 다 끔 조합 · el −30° 한 줄**뿐이다 — 회절을 켠 조합의 "
                 "거리 의존은 안 재봤다. 원장에 사는 거리는 15~480 m 인데 깊이 짝은 120 m 까지다. "
                 "15 m 는 원거리장 경계 2D²/λ ≈ 14.08 m 바로 밖, 120 m 는 한참 밖이다. "
                 "⭐리듬 몫은 상한 위만 세는 잣대라 먼 거리에서 퇴화할 수 있어 빗살 대비를 병용했다 "
                 "— 120 m 칸의 AC/DC 는 0.14 로 수치 바닥(1e-11)에서 멀다.")

    sf_moved = [r for r in sf if r["moves_the_reading"]]
    ans_d = dict(
        question_ko="ⓓ 깊이를 1 로 둔 우리 규약이 정당한가 (공장 기본값은 3)",
        standard_frame_pairs=[dict(
            combo=r["combo"], combo_ko=r["combo_ko"], el_deg=r["el_deg"], range_m=r["range_m"],
            d_moving_power_db=hl(r, "d_moving_power_db"),
            d_moving_power_db_raw=r["d_moving_power_db"],
            d_rhythm_pp=hl(r, "d_rhythm_pp"), d_rhythm_pp_raw=r["d_rhythm_pp"],
            rhythm_d1_pct=hl(r, "rhythm_d1_pct"), rhythm_dN_pct=hl(r, "rhythm_dN_pct"),
            d_comb_contrast_db=hl(r, "d_comb_contrast_db"),
            comb_d1_db=hl(r, "comb_d1_db"), comb_dN_db=hl(r, "comb_dN_db"),
            d_above_ceiling_pp=hl(r, "d_above_ceiling_pp"),
            cost_ratio=r["cost_ratio"], outlier_driven=r["outlier_driven"],
            moves_the_reading=r["moves_the_reading"], verdict_ko=r["verdict_ko"]) for r in sf],
        n_standard_frame_pairs=len(sf), n_moves_the_reading=len(sf_moved),
        cost_ratio=stat(sf, "cost_ratio"),
        answer_ko="**정당하다 — 우리가 실제로 싣는 팔에서 깊이 1 과 3 은 판독을 바꿀 만큼 안 다르다.** "
                  "표준 프레임 두 팔(PS 다 끔 · PS 굴절만)의 깊이 짝 7 개 전부에서 리듬 몫 차가 "
                  "**≤0.40 %p**, 요동 절대전력 차가 **−0.39~+1.72 dB** 다"
                  "(앙각 0 · −30 · −60 · −90° · 거리 15 · 30 · 120 m). 빗살 대비 차는 빗각·거리 "
                  "다섯 칸에서 ≤0.21 dB 다. ⭐정면 0° 만 +2.27 dB 로 큰데, **그 앙각의 빗살 밴드는 "
                  "0.1 dB 라 이 차이는 밴드 밖이다**(2026-08-16 적대검산 정정 — 전에는 여기에 "
                  "레벨 밴드 3.86 dB 와 전역 빗살 계단 4.04 dB 를 댔는데, 3.86 은 다른 잣대의 밴드이고 "
                  "4.04 는 정면을 뺀 빗각의 계단이다). 그런데도 **판독은 안 바뀐다** — 근거는 밴드가 "
                  "아니라 자리다: 그 칸의 빗살 대비는 −0.9 dB → +1.4 dB 로 **둘 다 백색 널 자리**여서 "
                  "«빗살 없음» 이라는 읽기가 양쪽에서 같다(리듬 몫도 13.0 → 12.7 %, 널 12.5 %). "
                  "⚠단 이 «정당하다» 는 **판독**에 대한 것이고 "
                  "**레벨**에 대한 것이 아니다 — 회절을 켠 조합(덱의 «물리 켬» 엔진)에서는 깊이 3 이 "
                  "요동 절대전력을 +1.32~+2.33 dB 올린다. 그 팔의 **절대 레벨**을 인용할 때는 "
                  "«깊이 1 한정» 꼬리표가 필요하다. "
                  "그리고 «깊이는 죽은 축» 이라고는 여전히 쓰면 안 된다 — 경로는 4~14 % 늘고, "
                  "늘어난 것이 회절 팔에서는 +2 dB 를 얹는다.",
        cost_ko="⚠비용은 **거칠게만** 말할 수 있다 — 원장의 seconds 는 워커 부하가 섞인 벽시계다. "
                "PS 다 끔 15 m 네 앙각에서 깊이 3 이 1.50~1.56 배(7543 → 11554 s), 30 m 에서 "
                "1.20 배(5240 → 6266 s)인데, 다른 두 칸(120 m · 굴절만)은 비율이 1 보다 작게 "
                "나온다(0.58 · 0.74) — 같은 시각에 같은 부하로 잰 값이 아니라서다. "
                "쓸 문장은 «대체로 1.2~1.6 배» 까지다.",
        deck_slide8_ko="덱 8 장이 청중에게 «우리는 깊이 1, 공장 기본값은 3» 을 이미 알렸다. "
                       "이 원장이 그 차이의 크기를 처음으로 준다 — 슬라이드에 붙일 한 줄은 "
                       "«깊이 3 은 경로를 4~14 % 더 찾지만 그것이 얹는 에코는 원 신호보다 "
                       "16~23 dB 아래고, 리듬 몫은 ≤0.40 %p·빗살 대비는 빗각에서 ≤0.21 dB 안에서 "
                       "그대로다» 다.",
        caveat_ko="⚠공장 기본값(stockdef = R1D0E0F0 · 깊이 3)은 **확산이 꺼져 있어** 빗각에서 경로가 "
                  "0 개다 — 순정 그대로는 애초에 에코가 없다. 그래서 «깊이 1 vs 공장 기본값» 은 "
                  "깊이만의 비교가 아니다. 깊이만 가른 비교는 이 원장의 짝들이다.")

    # ── R13 재채점 ──────────────────────────────────────────────────────────
    r13_fail = [dict(combo=r["combo"], el_deg=r["el_deg"], range_m=r["range_m"],
                     depths=r["depths"], max_abs_level_db=r["max_abs_level_db"],
                     d_rhythm_pp=r["d_rhythm_pp"], d_above_floor_db=r["d_above_floor_db"],
                     outlier_driven=r["outlier_driven"],
                     broke_ko=("리듬" if not r["r13_rhythm_within_3pp"] else "레벨"))
                for r in p13 if not r["r13_pass"]]
    moved = [r for r in pairs if r["moves_the_reading"]]

    scorecard = dict(
        prereg_r13_text_ko="R13(08-15) 사전등록 B — 깊이 1↔3 쌍 **전부**에서 레벨 차 < 2 dB 이고 "
                           "리듬 차 < 3 %p 면 깊이 축 종결",
        prereg_r13_n_pairs_then=13, prereg_r13_n_pairs_now=len(p13),
        prereg_r13_pass=bool(p13 and all(r["r13_pass"] for r in p13)),
        prereg_r13_n_pass=sum(1 for r in p13 if r["r13_pass"]),
        prereg_r13_failures=r13_fail,
        prereg_r13_reads_ko="옛 문안 그대로 채점하면 **여전히 불성립**이다 — 다만 깨지는 자리가 "
                            "바뀌었다. 리듬으로 깨진 유일한 자리(−60°)는 자세 하나의 튐이었고, "
                            "남은 것은 회절 켠 조합 넷의 세 열 최대 +2.26~+2.37 dB 로 2 dB 문턱을 "
                            "0.26~0.37 dB 넘는다. 그 문턱 2 dB 는 근거가 없는 임의값이다(아래).",
        prereg_r13_deviation_ko="R13 의 2 dB·3 %p 는 **밴드가 없던 때의 임의값**이라고 R13 자신이 "
                                "적어 놓았다(prereg_deviation_ko 네 번째 줄: «R16 산포 밴드가 아직 "
                                "없다 — 밴드가 나오면 다시 읽어야 한다»). 밴드가 나왔으므로 아래 "
                                "밴드 채점을 정본으로 쓰고, 위 채점은 «옛 문안 그대로» 로 병기한다.",
        band_rule_ko="⭐밴드 채점(이번 정본) — ①레벨은 **그 앙각의** 격자 산포 밴드(0° 3.86 · "
                     "−30° 0.37 · −45° 0.09 · −60° 0.02 · −75° 0.10 · −90° 5.62 dB) ②리듬 몫은 "
                     "R16 정본 21.8 %p ③빗살 대비는 격자 계단 하한 4.04 dB ④상한 위 몫은 12.55 %p. "
                     "밴드 밖이면 «움직인다», 안이면 «판정 불가». **판독이 바뀌었나**는 레벨이 아니라 "
                     "②③④ 로 본다. ⭐잣대는 전부 «가장 튄 자세 하나를 뺀» 값으로 채점하고 생값을 "
                     "함께 싣는다.",
        band_rule_caveat_ko="⚠②③은 **전역값**이라 앙각별 밴드보다 넓다 — 넓은 밴드는 «판정 불가» 쪽으로 "
                            "기울어 «안 바뀐다» 라는 결론에 유리하다. 그래서 앙각별 밴드로도 같이 채점해서 "
                            "pairs[].moves_the_reading_by_el_band 에 나란히 싣고, 두 채점이 갈리는 칸은 "
                            "pairs[].band_scoring_note_ko 에 적는다(2026-08-16 적대검산).",
        n_moves_the_reading_by_el_band=sum(1 for r in pairs if r["moves_the_reading_by_el_band"]),
        band_scorings_disagree=[dict(combo=r["combo"], el_deg=r["el_deg"], range_m=r["range_m"],
                                     depths=r["depths"],
                                     d_comb_contrast_db=hl(r, "d_comb_contrast_db"),
                                     comb_band_at_el=GRID_BAND_COMB_DB_BY_EL.get(r["el_deg"]),
                                     comb_band_global=GRID_BAND_COMB_DB_GLOBAL,
                                     both_sides_at_comb_null=r["both_sides_at_comb_null"],
                                     note_ko=r["band_scoring_note_ko"])
                                for r in pairs if r["band_scorings_disagree"]],
        wording_rule_ko="⭐«판정 불가» 와 «차이 없음» 은 다르다. 이 원장에서 «판독이 같다» 라고 쓸 때는 "
                        "«밴드 안» 이라서가 아니라 ①관측된 차이 자체가 작고(리듬 ≤0.40 %p · 빗살 "
                        "≤0.21 dB) ②그 팔의 재실행 문턱이 사실상 0(회절 끈 팔 ≤1e-14 dB)이라 그 작은 "
                        "차이가 **실재하는데도 작다**는 뜻이다. 밴드만으로는 «안 바뀐다» 를 못 세운다.",
        n_pairs_total=len(pairs), n_pairs_1to3=len(p13), n_pairs_1to2=len(p12),
        n_dead_pairs=len(dead_pairs),
        n_moves_the_reading=len(moved),
        moves_the_reading=[dict(combo=r["combo"], depths=r["depths"], el_deg=r["el_deg"],
                                range_m=r["range_m"], in_standard_frame=r["in_standard_frame"],
                                d_moving_power_db=hl(r, "d_moving_power_db"),
                                d_rhythm_pp=hl(r, "d_rhythm_pp"),
                                d_comb_contrast_db=hl(r, "d_comb_contrast_db"),
                                d_above_ceiling_pp=hl(r, "d_above_ceiling_pp"))
                           for r in moved],
        n_level_only=sum(1 for r in pairs if r["verdict_ko"].startswith("깊이가 레벨만")),
        n_inside_band=sum(1 for r in pairs if r["verdict_ko"].startswith("밴드 안")),
        n_unreadable=sum(1 for r in pairs if r["hard_flags"]),
        n_outlier_driven=sum(1 for r in pairs if r["outlier_driven"]),
    )

    closure = dict(
        question_ko="⭐이번 데이터가 깊이 축을 **종결시키나**",
        r13_basis_ko="R13(08-15)이 «종결 불가» 라고 적은 근거는 둘이었다. ①판 위(−30°) R1D1** 칸 "
                     "넷이 세 열 전부 +2.2~+2.4 dB — 사전등록 2 dB 밴드 바로 밖. ②판 밖 −60° 의 "
                     "R0D0E0F1 은 AC 가 +0.09 dB 로 같은데 상한 위 바닥만 +12.7 dB 오르고 리듬이 "
                     "86.6 → 32.4 %(−54.3 %p)로 무너진다. R13 은 ②를 «레벨 잣대 하나로는 안 보이던 "
                     "자리» 라고 적었다.",
        what_the_new_cells_changed_ko=[
            "⭐②는 **반증됐다 — 자세 8192 개 중 하나 때문이었다.** 그 자세(#3399)의 |E| 는 이웃의 "
            "약 5 배(전력 25 배)인데 이웃도, 로터 4 회 대칭 짝도, 경로 수(2308 ≈ 중앙값 2260)도 "
            "정상이다. 그 자세 **하나만 빼면** 두 판이 리듬 85.5 ↔ 85.2 %, 빗살 대비 45.4 ↔ 45.3 dB, "
            "요동 −129.72 ↔ −129.78 dB 로 일치한다. 반쪽 나눠 재기도 같은 이야기를 한다"
            "(그 자세가 든 반쪽만 무너진다). ⭐이 감식이 가능해진 것이 새 칸 덕은 아니다 — R13 이 "
            "**튐 진단을 안 돌린 것**이 원인이었다.",
            "①은 **살아남았고 자리가 좁혀졌다**(⚠«정체가 밝혀졌다» 는 2026-08-16 적대검산에서 "
            "**취소**했다). 새 d3 칸 10 개로 회절 켠/끈 팔을 나란히 놓으니, R1D1** 의 +2.2 dB"
            "(요동 절대전력 +2.15~+2.33 · 상한 위 바닥 +2.26~+2.37)는 튐에 강건하고(자세 1·8 개를 "
            "빼도 그대로) 그 팔의 재실행 문턱 0.07 dB 의 19~33 배라 **실재한다**. 다만 그것이 "
            "«회절 항이 깊이를 타고 한 번 더 얹힌 것» 이라는 **기전은 아직 안 세워졌다** — 근거로 "
            "썼던 «얹힌 항이 백색(11.2~12.3 %)» 은 그 팔이 깊이 1 판부터 이미 백색이라"
            "(리듬 몫 11.7~12.1 %) 아무것도 가르지 못한다. 회절을 끈 팔에서는 원 신호가 "
            "60~86 % 이고 얹힌 항이 52~85 % 라 그쪽은 «로터를 거친 에코» 로 읽을 수 있다.",
            "③새로 열린 것 — **튕김 사다리가 안 줄어든다**. 깊이 1·2·3 이 다 있는 한 자리"
            "(R1D1E1F1 · el −30°)에서 세 번째 튕김이 두 번째 튕김의 **4.9 배**를 더한다"
            "(튄 자세를 빼도 4.7~4.9). 손실 있는 표적의 다중 반사 급수라면 줄어야 한다 — "
            "깊이 3 이 «수렴한 답» 이라는 근거는 이 원장에 없다."],
        verdict_ko="⭐**우리 규약(깊이 1)에 대해서는 닫힌다. 축 전체로는 아직 안 닫힌다.**",
        closed_part_ko="**닫힌 것** — 표준 프레임이 싣는 두 팔(PS 다 끔 · PS 굴절만)에서 깊이 1↔3 의 "
                       "차이는 **실재하지만 판독을 못 바꿀 만큼 작다**. 짝 7 개 전부 리듬 몫 차 "
                       "≤0.40 %p 이고 빗살 대비 차는 빗각·거리 다섯 칸에서 ≤0.21 dB 이며, "
                       "앙각 4 개(0 · −30 · −60 · −90°)와 거리 3 개(15 · 30 · 120 m)를 덮는다. "
                       "⭐«실재한다» 고 쓰는 근거는 그 팔의 재실행 문턱이 사실상 0 이기 때문이고"
                       "(같은 물리 두 이름이 ≤1e-14 dB), «작다» 고 쓰는 근거는 관측값 자체이지 "
                       "격자 밴드가 아니다 — 밴드는 **판정 불가**만 말해 주지 «차이 없음» 은 못 세운다. "
                       "정면 0° 의 빗살 대비 +2.27 dB 는 그 앙각의 밴드(0.1 dB) **밖**이지만 양쪽 값이 "
                       "−0.9 · +1.4 dB 로 둘 다 백색 널 자리라 «빗살 없음» 이라는 읽기는 그대로다. "
                       "R13 이 이 결론을 막고 있던 −60° 반례는 자세 하나의 튐으로 밝혀졌다. "
                       "⇒ 8/18 덱 «Future work» 1 번의 실무적 답은 나왔다 — **큐에서 깊이 3 을 "
                       "표준 팔에 다시 태울 이유가 없다**.",
        open_part_ko="**안 닫힌 것** — ①회절을 켠 조합에서는 깊이 3 이 요동 절대전력을 +1.32~+2.33 dB "
                     "올린다(−30° 격자 밴드 0.37 dB 의 4~6 배 · 그 팔의 재실행 문턱 0.07 dB 의 19~33 배, "
                     "튐에 강건). 그 팔의 절대 레벨 인용에는 «깊이 1 한정» 꼬리표가 필요하다. "
                     "②그 +2 dB 가 물리인지 경로 표집의 부산물인지 **못 가른다** — 튕김 사다리가 안 "
                     "줄어든다는 단서 하나가 표집 쪽을 가리킬 뿐이다. ⚠«얹힌 항이 백색» 은 단서로 못 "
                     "쓴다(2026-08-16 적대검산): 그 팔은 깊이 1 판부터 리듬 몫 11.7~12.1 % 로 이미 "
                     "백색이라 무엇을 얹어도 백색으로 나온다. 깊이 3 에서 광선 사다리도 시드 복제도 "
                     "안 돌려 봤다. ③문턱을 우리 커널의 격자 밴드에서 **빌려 쓰고 있다** — PathSolver "
                     "자신의 깊이-3 산포는 안 잰 값이다(회절 켠 팔의 재실행 문턱 0.07 dB 만 이번에 "
                     "새로 쟀다). ④튕김 사다리의 깊이 3 칸은 깊이 1·2 와 **다른 이름의 실행**"
                     "(phys_d1/d2 ↔ swR1D1E1F1_d3)이다 — 두 이름의 차이는 0.07 dB 로 재 뒀으니 "
                     "2.18 dB 를 설명하지 못하지만, 한 이름으로 낸 사다리는 아직 없다.",
        what_would_close_it_ko=[
            "⭐**깊이 3 에서 광선 사다리**(R17 을 깊이 3 에 그대로) — R1D1E1F1 · el −30° 에서 광선을 "
            "4 배 내리고 4 배 올려 +2.2 dB 가 움직이나 본다. 움직이면 표집 부산물, 안 움직이면 물리다. "
            "이 한 칸이 남은 구멍 ①②를 동시에 겨눈다.",
            "**깊이 3 시드 복제 3~4 개** — 지금 «+2.2 dB 가 유의한가» 의 문턱을 남의 밴드에서 빌려 "
            "쓰고 있다. 같은 자리 시드만 바꾼 판이 있으면 문턱을 데이터로 세운다.",
            "**−45°·−75° 의 깊이 3 칸** — 깊이 짝이 있는 앙각은 0 · −30 · −60 · −90 뿐이다. "
            "빗각 두 자리를 메우면 앙각 축이 7/7 이 된다.",
            "**회절 켠 조합의 거리 축** — 거리 깊이 짝은 PS 다 끔 한 줄뿐이다.",
            "⭐**튐 진단을 상시 잣대로** — 이번에 헤드라인 하나를 뒤집은 것이 자세 하나였다. "
            "isolation(최대÷둘째)을 원장 칸마다 세워 두면 같은 사고가 다시 안 난다."],
        do_not_write_ko=["«깊이 축 완전 종결» (회절 켠 조합의 +2 dB 가 남았다)",
                         "«작은 표적에는 다중 경로가 안 생긴다» (경로가 4~14 % 늘고 얹힌 에코는 "
                         "박자를 갖는다)",
                         "«깊이 3 이 더 정확하다» (튕김 사다리가 안 줄어든다 · 얹힌 항이 백색)",
                         "⛔«−60° 에서 깊이 3 이 리듬을 무너뜨린다» — 08-15 판의 이 문장은 "
                         "**철회**한다(자세 하나)"],
        can_write_ko=["«우리가 쓰는 두 팔에서 깊이 1 과 3 의 차이는 판독을 바꾸기엔 너무 작다 — "
                      "리듬 몫 차 ≤0.40 %p, 빗살 대비 차 ≤0.21 dB(빗각·거리), 앙각 4 개·거리 3 개에서»",
                      "«깊이 3 은 경로를 4~14 % 더 찾고, 찾은 것을 원래 신호 위에 계수 1 로 얹는다»",
                      "«회절을 끄면 얹힌 항이 날개 박자를 갖고 원 신호보다 16~23 dB 아래다»",
                      "«깊이 1 은 같은 칸을 대체로 1.2~1.6 배 싸게 낸다 — 벽시계라 거친 값이다»"],
        do_not_write_added_0816_ko=[
            "⛔«회절 켠 팔에서 얹힌 항이 백색이니 그것은 회절 항이다» — 그 팔은 원 신호부터 "
            "백색이라 이 논증은 성립하지 않는다.",
            "⛔«모서리 E 는 소수점까지 무동작이다» — 회절을 켠 판에서는 자세 8~26 개가 갈리고 "
            "요동 절대전력이 최대 0.07 dB 흔들린다.",
            "⛔«밴드 안이니 깊이 1 과 3 은 차이가 없다» — 밴드 안은 «판정 불가» 다. "
            "여기서 «작다» 라고 쓸 수 있는 근거는 밴드가 아니라 관측값과 ≈0 인 재실행 문턱이다."],
        retractions_ko=["outputs/switch_factorial.json B_failures 의 첫 줄(R0D0E0F1 · el −60 · "
                        "12.74 dB · −54.25 %p)과 B_why_ko 의 ② 는 **자세 하나의 튐**이다 — "
                        "인용하지 말 것.",
                        "docs/RESUME.md 1-b 표 R13 행의 «⛔깊이 축은 종결 불가 — 큐에서 "
                        "--max-depth 3 를 빼면 안 된다» 는 이 원장으로 **범위를 좁혀야** 한다: "
                        "표준 팔에서는 빼도 되고, 회절 켠 조합의 레벨 인용에서만 남는다."])

    out = dict(
        _meta=dict(
            generator="benchmark/depth_axis_verdict_0816.py",
            experiment="⭐반사 깊이 축(--max-depth) 판정 — 08-16 병합 원장 전수",
            written_at_kst=_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
                .strftime("%Y-%m-%d %H:%M KST"),
            why_ko="8/18 덱 30 장 Future work 1 번(«close the bounce-depth axis»)의 데이터가 "
                   "08-16 병합으로 다 들어왔는데 판정 원장도 그림도 없었다. 이 파일이 그 자리다.",
            gpu_used="0 — 저장된 원장만 읽는다(sionna.rt·mitsuba 임포트 없음)",
            sources={
                "ledger_json": dict(path="outputs/elevation_sweep_md.json",
                                    mtime=mtime(A.LED_J), n_rows=len(ROWS)),
                "ledger_npz": dict(path="outputs/elevation_sweep_md.npz",
                                   mtime=mtime(A.LED_N), n_keys=len(Z.files)),
                "shards": dict(path="outputs/elev_sweep_shards/",
                               n_files=len(glob.glob(f"{SHD}/*.npz"))),
                "r13": "outputs/switch_factorial.json (2026-08-15 · 새 칸 들어오기 전 — "
                       "이 파일의 깊이 결론은 낡았다)",
                "inventory": "outputs/frame_inventory_0816.json",
                "grid_band": "outputs/grid_convergence_check.json + "
                             "outputs/frame_completion_0816.json q4_grid_band(앙각별 정정)",
                "seed_band": "outputs/raybudget_seed_ladder.json",
                "ray_ladder": "outputs/raybudget_ac_ladder.json (R17 — 상한 위는 광선 수에 불변)"},
            metric_defs_ko="세 열(요동 절대전력·확산 바닥·빗살 빈)은 benchmark/switch_factorial.py "
                           "columns() 와 같은 식(Parseval 정규화 절대 dB). 빗살 대비·리듬 몫·널·"
                           "박자·깃발은 benchmark/build_md_atlas.py cell_summary 를 그대로 임포트 "
                           "— 정의 재작성 없음.",
            conventions_ko=[
                "레벨(dB) 비교는 전부 정지 성분(DC) 제거 후 — moving_power_db 열만 쓴다",
                "리듬 몫은 날개끝 상한 위만 세므로 거리 팔에서 퇴화 — comb_contrast_db 병용",
                "⭐격자 산포 밴드는 앙각마다 다르다(0° 3.86 · −30° 0.37 · −45° 0.09 · −60° 0.02 "
                "· −75° 0.10 · −90° 5.62 dB) — 옛 «전 앙각 3.86» 을 쓰면 빗각 판정을 놓친다",
                "빗살 대비는 격자 계단마다 +4~5.6 dB 단조 상승 → 절대 인용에 격자 꼬리표",
                "AC/DC < 1e-11 칸은 near_numeric_floor — 물리로 읽지 않는다",
                "밴드 안이면 «판정 불가» 로 적는다 — «안 바뀐다» 로 단정하지 않는다"],
            band_scope_warning_ko="⚠⭐격자 산포 밴드는 **우리 커널(SBR+PO)의 λ/12↔λ/24 격자 축**에서 "
                                  "잰 것이다. 여기 짝은 전부 PathSolver 팔이라 그 밴드는 «가져다 쓴 "
                                  "것»이고 PathSolver 자신의 깊이-3 산포를 잰 값이 아니다. 그래서 "
                                  "null_bands 에 PathSolver 재현성(같은 설정 독립 재실행)과 시드 "
                                  "산포를 함께 싣고, 판정은 셋을 나란히 놓고 한다. "
                                  "⭐**밴드에 안 기대는 잣대**를 헤드라인으로 썼다 — 얹힌 항의 리듬 "
                                  "몫은 백색 널을 칸마다 정확히 셀 수 있어 문턱을 빌릴 필요가 없다."),
        null_bands=dict(
            grid_dispersion_ac_db_by_el=GRID_BAND_AC_DB,
            grid_dispersion_rhythm_pp_by_el=GRID_BAND_RHYTHM_PP_BY_EL,
            grid_dispersion_comb_db_by_el=GRID_BAND_COMB_DB_BY_EL,
            grid_dispersion_above_ceiling_pp_global=GRID_BAND_ABOVE_PP_GLOBAL,
            grid_dispersion_beat_hz=GRID_BAND_BEAT_HZ,
            grid_band_owner_ko="우리 커널(SBR+PO) — PathSolver 팔에는 «가져다 쓰는» 밴드다",
            comb_contrast_grid_tag_ko="⚠빗살 대비 절대값은 격자 계단마다 +4.04~+4.67 dB(λ/12→24) "
                                      "· +5.6 dB(24→48) 로 단조 상승한다 — 절대 인용에는 격자 "
                                      "꼬리표가 필요하다. 여기 짝은 PathSolver 라 격자 개념이 "
                                      "없으므로 **짝 안의 차이**는 이 꼬리표에서 자유롭다.",
            pathsolver_repeatability=dict(
                what_ko="같은 물리를 두 이름으로 독립 재실행한 칸 — ⭐**회절 끈 팔과 켠 팔을 갈라서** 잰다",
                diffraction_off=dict(
                    what_ko="R1D0E0F1 · 깊이 1 · 광선 4e9 — 두 기체 × 세 앙각 6 칸",
                    rows=rerun, band_ac_db=rerun_band),
                diffraction_on=dict(
                    what_ko="⭐회절 켠 팔의 E0↔E1 두 판(el −30° · 15 m · 깊이 1·3 섞어 7 쌍). "
                            "모서리 E 는 회절 안에서 **자유 모서리**에만 걸리는 스위치라 닫힌 메쉬에서는 "
                            "경로를 사실상 안 바꾼다 — 그래서 «같은 물리의 재실행» 으로 쓴다.",
                    rows=rerun_d1on, band_ac_db=rerun_band_diffr_on),
                rows=rerun, band_ac_db=rerun_band,
                reads_ko="⭐**회절을 끈 팔에서만** PathSolver 가 수치적으로 재현된다(요동 절대전력 차 "
                         "≤1e-14 dB · 1−|ρ| ≤1e-15). ⚠**회절을 켜면 재현이 깨진다** — 같은 물리 두 판이 "
                         "자세 8192 개 중 8~26 개에서 갈리고(그 자세들은 |E| 가 최대 23 % 다르다) "
                         "요동 절대전력이 최대 0.07 dB 흔들린다. ⇒ 깊이 짝의 차이를 «재실행 잡음이 "
                         "아니다» 로 읽을 때 문턱은 회절 끈 팔 ≈0 · 회절 켠 팔 **0.07 dB** 다. "
                         "회절 켠 팔의 깊이 효과(+1.32~+2.33 dB)는 그 문턱의 19~33 배라 살아남는다. "
                         "다만 «재현된다» 는 «맞다» 가 아니다 — 같은 시드는 같은 편향도 재현한다."),
            seed_dispersion=dict(
                source="outputs/raybudget_seed_ladder.json (광선 4e9 · 40 m · el −15° · 8 시드)",
                sd_level_db=SEED_SD_DB, ptp_level_db=4.86, ratio_observed_over_iid=31.16,
                reads_ko="⚠광선 **방향 집합**(시드)을 바꾸면 레벨이 sd 1.83 dB · p-p 4.86 dB 로 "
                         "흔들리고, 자세 평균으로 안 지워지는 **계통 편향**이다(i.i.d. 예측의 31 배). "
                         "깊이 짝은 같은 시드의 짝비교라 이 항이 상당 부분 소거된다(담김계수 a≈1 이 "
                         "그 증거). 얼마나 소거되는지는 **안 재봤다** — 깊이 3 시드 복제가 없다.")),
        inventory=dict(
            n_sionna_cells_scanned=len(cells),
            n_depth_groups=sum(1 for v in groups.values() if len(v) >= 2),
            n_pairs=len(pairs), n_pairs_1to3=len(p13), n_pairs_1to2=len(p12),
            n_dead_pairs=len(dead_pairs),
            elevations_covered=sorted({r["el_deg"] for r in pairs}),
            ranges_covered=sorted({r["range_m"] for r in pairs}),
            combos_covered=sorted({r["combo"] for r in pairs}),
            newly_filled_0816_ko="깊이 3 신규 12 칸 = 스위치 완전요인 d3 10 태그(el −30° · 15 m) "
                                 "+ 거리 r30 · r120 d3(el −30°). 그중 R0D0E0F0 · R1D0E0F0 은 두 "
                                 "판 모두 경로 0 이라 죽은 짝이다.",
            not_covered_ko=["깊이 3 이 없는 앙각: −15° · −45° · −75°",
                            "깊이 3 이 없는 거리: 60 · 240 · 480 m",
                            "깊이 3 이 없는 기체: mini5pro · s1000plus (전부 깊이 1)",
                            "깊이 3 이 없는 방위: az 15~90° (전부 깊이 1)",
                            "우리 커널(SBR+PO)에는 깊이 개념 자체가 없다 — 짝이 원리적으로 없다"]),
        pairs=pairs, dead_pairs=dead_pairs, npaths_table=npaths_tbl,
        bounce_ladder=ladder,
        outlier_forensics=dict(
            why_ko="⭐한 자세가 통째로 튀면 잣대가 그 자세 하나를 재게 된다. 이번에 08-15 판의 "
                   "헤드라인 하나가 정확히 그것이었다. 그래서 짝마다 «가장 튄 자세 1·8 개를 "
                   "빼고 다시 잰» 값을 pairs[].trim 에 함께 싣고, 헤드라인은 k=1 판으로 쓴다.",
            isolation_def_ko="isolation = |AC| 최대 ÷ 둘째. 1 에 가까우면 로터 대칭이 만든 "
                             "구조적 플래시(정상), 2 를 넘으면 자세 하나만 튄 것이다.",
            isolation_median=round(iso_med, 3) if iso_med is not None else None,
            n_cells=len(spike_census), isolated_cells=isolated,
            census=spike_census,
            el60_case=forensic),
        answers=dict(a=ans_a, b=ans_b, c=ans_c, d=ans_d),
        scorecard=scorecard,
        closure=closure,
        cells={k: v for k, v in sorted(cells.items())
               if any(k in (r["d1"], r["dN"]) for r in pairs + dead_pairs)},
    )

    os.makedirs(os.path.dirname(OUTJ), exist_ok=True)
    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. 그림 — ⭐그림 안 글자는 전부 영어
    # ═══════════════════════════════════════════════════════════════════════
    make_figure(p13, ladder)

    print(f"\n짝 {len(pairs)} (1↔3 {len(p13)} · 1↔2 {len(p12)}) · 죽은 짝 {len(dead_pairs)}")
    print(f"판독을 바꾼 짝 {len(moved)} · 표준 프레임 짝 {len(sf)} 중 {len(sf_moved)}")
    for r in pairs:
        print(f"  {r['combo']} d{r['depths'][0]}→{r['depths'][1]} el{r['el_deg']:+5.0f} "
              f"{r['range_m']:6.0f} m  ΔAC {str(r['d_moving_power_db']):>8s}  "
              f"Δfloor {str(r['d_above_floor_db']):>8s}  Δcomb {str(r['d_comb_contrast_db']):>7s}  "
              f"Δrhy {str(r['d_rhythm_pp']):>8s}  res {str(r.get('residual_over_d1_db')):>8s} dB/"
              f"{str(r.get('residual_rhythm_pct')):>6s}%  {r['verdict_ko']}")
    print(f"\n→ {OUTJ}\n→ {FIG}")


def _tv(r, key, k=TRIM_HEADLINE):
    """짝의 «가장 튄 자세 하나를 뺀» 값 — 없으면 생값."""
    t = (r.get("trim") or {}).get(f"k{k}")
    if t and t.get(key) is not None:
        return t[key]
    return r.get(key)


def make_figure(p13, ladder):
    """세 판 — ①스위치 축 ②얹힌 항의 성격 ③−60° 감식."""
    el30 = [r for r in p13 if r["el_deg"] == -30.0 and r["range_m"] == 15.0]
    el30.sort(key=lambda r: (r["switches"]["D"], r["combo"]))
    base = [r for r in p13 if r["combo"] == "R0D0E0F1" and r["range_m"] == 15.0]
    base.sort(key=lambda r: -r["el_deg"])

    fig, ax = plt.subplots(1, 3, figsize=(16.8, 6.0))
    C_OFF, C_ON, C_GREY = "#1f77b4", "#d62728", "#9e9e9e"

    # ── ① 스위치 축 ────────────────────────────────────────────────────────
    a = ax[0]
    y = np.arange(len(el30))
    h = 0.26
    METRICS = [("d_moving_power_db", "moving power (DC removed)", ""),
               ("d_above_floor_db", "floor above tip ceiling", "///"),
               ("d_comb_contrast_db", "comb contrast", "...")]
    for j, (k, lab, hatch) in enumerate(METRICS):
        v = [(_tv(r, k) if _tv(r, k) is not None else np.nan) for r in el30]
        a.barh(y + (1 - j) * h, v, height=h, hatch=hatch,
               color=[C_ON if r["switches"]["D"] else C_OFF for r in el30],
               edgecolor="white", linewidth=0.6)
    a.axvline(0, color="k", lw=0.8)
    a.axvspan(-0.37, 0.37, color=C_GREY, alpha=0.32, zorder=0)
    a.set_yticks(y)
    a.set_yticklabels([f"{r['combo']}   {r['npaths_d1']}→{r['npaths_dN']} paths"
                       for r in el30], fontsize=8.6)
    a.set_xlabel("depth 3 minus depth 1   [dB]")
    a.set_title("Switch axis   ·   elevation −30°   ·   15 m", fontsize=11.5)
    a.legend(handles=[Patch(fc="0.72", ec="white", hatch=hh, label=lb)
                      for _, lb, hh in METRICS]
                     + [Patch(fc=C_OFF, ec="white", label="diffraction OFF"),
                        Patch(fc=C_ON, ec="white", label="diffraction ON")],
             fontsize=7.6, loc="lower right", framealpha=0.96, ncol=1)
    a.text(0.02, 0.985, "grey band = grid dispersion at −30° (±0.37 dB)",
           transform=a.transAxes, va="top", ha="left", fontsize=7.8,
           bbox=dict(fc="white", ec="0.75", alpha=0.92, pad=2.8))
    a.grid(axis="x", ls=":", alpha=0.5)

    # ── ② 얹힌 항의 성격 ───────────────────────────────────────────────────
    b = ax[1]
    pts = [r for r in p13 if _tv(r, "residual_rhythm_pct") is not None
           and r["readable"]["above_tip"]]
    for r in pts:
        b.scatter(_tv(r, "residual_over_d1_db"), _tv(r, "residual_rhythm_pct"), s=82,
                  color=(C_ON if r["switches"]["D"] else C_OFF),
                  marker=("s" if r["range_m"] > 15.0 else "o"),
                  edgecolor="k", linewidth=0.5, zorder=3)
    # ⭐백색 널은 칸마다 조금씩 다르다(정면 12.5 · 빗각 12.6 %) — 그린 점들의 평균을 쓰고
    #   같은 원장의 다른 그림(depth_axis_0816.png)과 같은 규약으로 맞춘다.
    nul = (sum(r["rhythm_null_pct"] for r in pts) / len(pts)) if pts else 12.6
    b.axhline(nul, color="k", ls="--", lw=1.1, zorder=2)
    b.text(0.015, nul + 2.4, f"white null {nul:.1f} %", transform=b.get_yaxis_transform(),
           ha="left", va="bottom", fontsize=8.4)
    b.set_xlabel("size of what depth 3 adds   [dB relative to depth 1]")
    b.set_ylabel("rhythm share of the added term   [%]")
    b.set_title("What the extra bounces put in", fontsize=11.5)
    b.set_ylim(0, 100)
    b.grid(ls=":", alpha=0.5)
    b.legend(handles=[Patch(fc=C_OFF, ec="k", lw=0.5, label="diffraction OFF"),
                      Patch(fc=C_ON, ec="k", lw=0.5, label="diffraction ON")],
             fontsize=8.2, loc="center right", framealpha=0.95)
    b.text(0.03, 0.965,
           "above the null: the added echo knows the blade beat\n"
           "at the null: structureless fill\n"
           "square marker = 30 m or 120 m",
           transform=b.transAxes, va="top", ha="left", fontsize=7.6,
           bbox=dict(fc="white", ec="0.75", alpha=0.92, pad=2.8))

    # ── ③ −60° 감식 — 자세 하나를 빼면 무엇이 되나 ─────────────────────────
    c = ax[2]
    #: 직하방(−90°)은 f_tip = 0 이라 «상한 위» 잣대가 퇴화한다 — 이 판에서 뺀다
    shown = [r for r in base if r["el_deg"] > -89.0]
    x = np.arange(len(shown))
    w = 0.27
    c.bar(x - w, [r["rhythm_d1_pct"] for r in shown], width=w, color=C_OFF,
          edgecolor="white", label="depth 1   (our convention)")
    c.bar(x, [r["rhythm_dN_pct"] for r in shown], width=w, color="#ff9f40",
          edgecolor="white", label="depth 3   as measured")
    c.bar(x + w, [_tv(r, "rhythm_dN_pct") for r in shown], width=w, color="#8fbf4d",
          edgecolor="white", label="depth 3   minus one outlier pose")
    nul_c = sum(r["rhythm_null_pct"] for r in shown) / len(shown)
    c.axhline(nul_c, color="k", ls="--", lw=1.1)
    c.text(len(shown) - 0.55, nul_c + 2.6,
           f"white null {nul_c:.1f} %", ha="right", fontsize=8.4)
    c.set_xticks(x)
    c.set_xticklabels([("0°" if r["el_deg"] == 0 else "−" + f"{abs(r['el_deg']):.0f}°")
                       for r in shown])
    c.set_ylabel("rhythm share above the tip ceiling   [%]")
    c.set_xlabel("elevation")
    c.set_title("PS all-off arm  ·  15 m  ·  the reading, not the level", fontsize=11.5)
    c.set_ylim(0, 112)
    c.grid(axis="y", ls=":", alpha=0.5)
    c.legend(fontsize=8.0, loc="upper left", framealpha=0.96)
    for i, r in enumerate(shown):
        if r["outlier_driven"]:
            c.annotate("one pose out of 8192", xy=(i, r["rhythm_dN_pct"] + 1.5),
                       xytext=(i, 66.0), ha="center", fontsize=8.8, fontweight="bold",
                       color="#b40000",
                       arrowprops=dict(arrowstyle="->", color="#b40000", lw=1.2))

    fig.suptitle("Bounce-depth axis  —  what changes when rays may bounce three times",
                 fontsize=13.4, y=0.985)
    fig.text(0.5, 0.017,
             "0° is the frontal drowned cell, already at the null before depth is touched   ·   "
             "−90° is left out of the right panel: the tip ceiling is zero there and the metric "
             "degenerates   ·   all levels measured after removing the standing part",
             ha="center", fontsize=8.0, color="0.25")
    fig.tight_layout(rect=(0, 0.045, 1, 0.945))
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
