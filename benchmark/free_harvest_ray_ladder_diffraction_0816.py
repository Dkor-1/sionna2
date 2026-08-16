# -*- coding: utf-8 -*-
"""
free_harvest_ray_ladder_diffraction_0816.py — ⭐회절 켠 팔의 «광선 사다리» 판독
==============================================================================

■ 묻는 것 (백로그 2 위 · docs/EXPERIMENT_BACKLOG.md)
    회절을 켜면 날개끝 상한 **위**에 바닥이 얹힌다. 그 바닥이
      ⓐ **계산 표집**인가 — 광선을 더 부으면 움직인다
      ⓑ **결정론적 물리**인가 — 광선을 부어도 그 자리에 그대로 있다
    를 가른다. 갈라 주는 것은 08-16 병합으로 원장에 처음 올라온
    **같은 설정 · 광선만 4 배** 두 칸이다.

■ 사다리 (전부 el −30° · 15 m · 자세 8192 · matrice4e · az 0 · 3.5 GHz · 셸 100 mm)
    깊이 1 :  p1e9 swR1D1E1F1_d1   →  p4e9 phys_d1          (광선 ×4 = 2 옥타브)
    깊이 3 :  p1e9 swR1D1E1F1_d3   →  p4e9 swR1D1E1F1_d3    (광선 ×4 = 2 옥타브)
    ⭐`_phys_d1` 과 `_swR1D1E1F1_d1` 은 **같은 솔버 설정**이다(소스 실측:
      `--physics` 는 refraction·diffraction·edge 를 켜고 확산은 상수로 켜져 있다 →
      R1D1E1F1, `--max-depth 1`). 이름만 다른 별칭이라 사다리로 이어 붙일 수 있다.

■ 미리 못 박는 세 갈래 (재기 전에 적는다)
    ①  −6.02 dB (=−3.01 dB/옥타브)  광선을 부으면 **평균으로 지워지는 표집 잡음**
    ②   0 dB (널 밴드 안)            **결정론적 물리** — 광선과 무관
    ③  +6.02 dB (=+3.01 dB/옥타브)  광선마다 **무작위 위상 몫이 쌓인다**(정규화 없는 누적)
    ①과 ③은 부호만 다르고 **둘 다 «계산 표집»** 이다. «물리» 는 ② 하나뿐이다.

■ 딸린 물음 — 깊이 축의 «회절 켠 조합 +1.32~+2.33 dB» 도 광선 몫인가
    depth_axis_verdict_0816 의 미해결 ②다. 같은 사다리에서 깊이 증분을 두 광선 예산에서
    각각 재면, 그 증분이 광선 축과 같은 얼굴인지 아닌지가 나온다.

■ ⭐잣대 규약 (어기면 결론이 뒤집힌다)
    · 레벨(dB)은 전부 **정지 성분(DC) 제거 후** — `moving_power_db`
    · 잣대 식은 `depth_axis_verdict_0816.columns()` 를 **그대로 임포트**(재작성 없음)
    · 격자 산포 밴드는 앙각마다 다르다 — 이 판은 전부 el −30° 라 **0.37 dB**(빌린 값 아님).
      ⚠단 그 밴드는 **우리 커널의 격자 축**에서 잰 것이라 PathSolver 에는 «빌려 온 자» 다.
    · 그래서 널을 셋 나란히 놓는다: 재실행 0.07 dB(회절 켠) · 격자 0.37 dB(빌림) ·
      ⭐**시드 산포 1.833 dB**(같은 예산에서 광선 방향 집합만 바꿨을 때) — 광선 축 물음에는
      **시드 산포가 가장 알맞은 자**다(예산을 바꾸면 광선 방향 집합도 통째로 바뀐다).
    · AC/DC < 1e-11 은 near_numeric_floor — 물리로 안 읽는다
    · 튐(이상 자세)은 `outputs/outlier_census_0816.json` 등급을 먼저 보고, 원장에 없던
      새 칸은 같은 절차로 직접 잰다. ⭐자세는 **지우지 않고 이웃 평균으로 갈아 끼운다**.
    · ⚠D1 조합(R1D1E1F1)은 `docs/STANDARD_FRAME.md` **밖**이다 — 「별도 트랙」 꼬리표 필수.

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt / mitsuba 임포트 없음)
    outputs/elevation_sweep_md.{json,npz}      08-16 병합본(411 행)
    outputs/elev_sweep_shards/*.npz            자세별 경로 수(npaths) · cfg 출처
    outputs/depth_axis_verdict_0816.json       깊이 축 판정 · 재실행 문턱
    outputs/raybudget_ac_ladder.json           R17 — 물리 끔 예산 사다리
    outputs/raybudget_seed_ladder.json         시드 산포(계통 편향)
    outputs/outlier_census_0816.json           튐 등급(349 행 판)

■ 굽는 것
    outputs/free_harvest_ray_ladder_diffraction_0816.json
    outputs/figures/free_harvest_ray_ladder_diffraction_0816.png

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/free_harvest_ray_ladder_diffraction_0816.py
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import math
import os

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                        # noqa: E402

import build_md_atlas as A                                             # noqa: E402
import depth_axis_verdict_0816 as D                                    # noqa: E402
import outlier_census_0816 as O                                        # noqa: E402

ROOT = A.ROOT
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUTJ = os.path.join(ROOT, "outputs", "free_harvest_ray_ladder_diffraction_0816.json")
FIG = os.path.join(ROOT, "outputs", "figures",
                   "free_harvest_ray_ladder_diffraction_0816.png")

PRF = A.PRF
NEAR_FLOOR = D.NEAR_FLOOR

# ── 널 셋 ────────────────────────────────────────────────────────────────────
NULL_RERUN_DIFFR_ON_DB = 0.07     # 같은 설정·같은 시드 재실행 (회절 켠 팔)
NULL_GRID_EL30_DB = 0.37          # 격자 산포 밴드 el −30 (⚠우리 커널에서 빌림)
NULL_SEED_SD_DB = 1.833           # 시드(광선 방향 집합) 산포 sd · spp 4e9
NULL_SEED_PTP_DB = 4.86           # 같은 판의 최대−최소 (판정에는 sd 를 쓴다)

OCT = math.log2(4.0)              # 광선 4 배 = 2 옥타브
PRED = {"sampling_average": -3.01 * OCT,     # ① 1/N
        "deterministic": 0.0,                # ②
        "sampling_accumulate": +3.01 * OCT}  # ③ ∝N

# ── 칸 ──────────────────────────────────────────────────────────────────────
LAD = {  # (깊이, spp) → 팔 이름
    (1, 1_000_000_000): "sionna_p1000000000_swR1D1E1F1_r15_n8192_d1",
    (3, 1_000_000_000): "sionna_p1000000000_swR1D1E1F1_r15_n8192_d3",
    (1, 4_000_000_000): "sionna_p4000000000_phys_r15_n8192_d1",
    (3, 4_000_000_000): "sionna_p4000000000_swR1D1E1F1_r15_n8192_d3",
}
LAD_EL = -30.0

#: 같은 앙각·거리·예산의 **회절 끈** 이웃 — 「회절이 얹는 것」의 뺄셈 짝(4e9 에서만 가능)
DFLIP = {"R1D0E0F1": "sionna_p4000000000_onlyrefr_r15_n8192",     # 굴절만
         "R0D0E0F1": "sionna_p4000000000_r15_n8192_d1",            # 다 끔(확산만)
         "R0D1E0F1": "sionna_p4000000000_onlydiffr_r15_n8192"}     # 회절만

#: 대조 사다리 — 10 m 팔(⚠거리가 다르다. 절대 dB 를 15 m 판과 섞지 않는다)
CTRL_OFF = [("sionna", 11_111_111), ("sionna_p250000000", 250_000_000),
            ("sionna_p1000000000", 1_000_000_000),
            ("sionna_p4000000000", 4_000_000_000)]          # 회절 끔 · 깊이 1
CTRL_ON = [("sionna_phys", 11_111_111),
           ("sionna_p250000000_phys", 250_000_000)]         # 회절 켬 · 깊이 3
CTRL_ELS = [0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0]


def kst(p):
    return _dt.datetime.fromtimestamp(os.path.getmtime(p),
                                      _dt.timezone(_dt.timedelta(hours=9))
                                      ).strftime("%Y-%m-%d %H:%M KST")


def npaths_of(arm: str, el: float):
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    v = []
    for f in fs:
        z = np.load(f)
        if "npaths" in z:
            v.append(np.asarray(z["npaths"]))
        z.close()
    if not v:
        return dict(n_shards=len(fs), median=None, mean=None, zero_frac_pct=None)
    w = np.concatenate(v).astype(float)
    return dict(n_shards=len(fs), n=int(w.size), median=float(np.median(w)),
                mean=round(float(w.mean()), 2), p10=float(np.percentile(w, 10)),
                p90=float(np.percentile(w, 90)),
                zero_frac_pct=round(100.0 * float((w == 0).mean()), 3))


def cell(arm: str, el: float) -> dict | None:
    """한 칸의 잣대 — 식은 depth_axis_verdict_0816.columns() 그대로."""
    key = f"{arm}/el{el:+.0f}"
    if key not in A.Z.files:
        return None
    E = np.asarray(A.Z[key], complex)
    rates = A.arm_rates(arm)
    ft, ffl = A.f_tip_at(rates, el), rates["f_flash_hz"]
    col = D.columns(E, PRF, ffl, ft)
    x = E - E.mean()
    p_ac = float(np.mean(np.abs(x) ** 2))
    p_dc = float(np.abs(E.mean()) ** 2)
    p_tot = float(np.mean(np.abs(E) ** 2))
    # 바닥 **밀도** — 빈 수가 달라도 비교되게 빈당 전력으로도 낸다
    fden = (col["above_floor_db"] - 10 * math.log10(col["n_bins_floor"])
            if (col["above_floor_db"] is not None and col["n_bins_floor"]) else None)
    cden = (col["above_comb_db"] - 10 * math.log10(col["n_bins_comb"])
            if (col["above_comb_db"] is not None and col["n_bins_comb"]) else None)
    # 상한 **아래**
    n = E.size
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2 / (n * np.sum(np.hanning(n) ** 2))
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    below = np.abs(fr) < ft
    row = next((r for r in A.J["rows"]
                if r["engine"] == arm and abs(float(r["el_deg"]) - el) < 1e-6), None)
    npa = npaths_of(arm, el)
    #: ⭐경로 하나당 바닥 — «찾은 경로마다 일정한 무작위 위상 몫이 쌓이나» 를 직접 본다.
    #   이 수가 예산을 올려도 그대로면 바닥은 경로 수에 **비례**한다(=계산 표집).
    fpp = (round(col["above_floor_db"] - 10 * math.log10(npa["median"]), 3)
           if (col["above_floor_db"] is not None and (npa["median"] or 0) > 0) else None)
    return dict(
        cell=key, arm=arm, el_deg=el, n_poses=int(n),
        n_missing=(None if row is None else row["n_missing"]),
        range_m=(None if row is None else row["range_m"]),
        max_depth=(None if row is None else row["max_depth"]),
        spp=(None if row is None else row["spp"]),
        seconds=(None if row is None else row["seconds"]),
        f_tip_hz=round(ft, 1), f_flash_hz=round(ffl, 3),
        # ── 잣대 (전부 DC 제거 후) ──────────────────────────────────────
        moving_power_db=col["ac_db"],
        dc_power_db=(None if p_dc <= 0 else round(10 * math.log10(p_dc), 3)),
        above_floor_db=col["above_floor_db"],
        above_floor_density_db=(None if fden is None else round(fden, 3)),
        above_comb_db=col["above_comb_db"],
        above_comb_density_db=(None if cden is None else round(cden, 3)),
        comb_over_floor_db=col["comb_over_floor_db"],
        below_tip_db=D.db(float(P[below].sum())) if below.any() else None,
        rhythm_share_pct=col["rhythm_share_pct"],
        rhythm_null_pct=round(A.rhythm_share(E, ffl, ft)[1], 3),
        comb_contrast_db=(None if (c := A.comb_contrast_db(E, ffl, ft)) is None
                          else round(c, 3)),
        n_bins_above=col["n_bins_above"], n_bins_comb=col["n_bins_comb"],
        n_bins_floor=col["n_bins_floor"],
        ac_over_dc=float(f"{(p_ac / p_tot if p_tot > 0 else 0.0):.4g}"),
        near_numeric_floor=bool(p_tot > 0 and p_ac / p_tot < NEAR_FLOOR),
        zero_echo=col["zero_echo"],
        floor_per_path_db=fpp,
        npaths=npa)


def spike(arm: str, el: float, ffl: float, ft: float) -> dict:
    """튐 진단 — 원장에 없던 새 칸은 census 절차(outlier_census_0816)를 그대로 쓴다.
    ⭐자세는 **지우지 않고 이웃 평균으로 갈아 끼운다**(표집 간격 보존)."""
    E = np.asarray(A.Z[f"{arm}/el{el:+.0f}"], complex)
    x = E - E.mean()
    v = np.sort(np.abs(x))[::-1]
    med = float(np.median(np.abs(x)))
    i0 = int(np.argmax(np.abs(x)))
    base = O.headline(E, ffl, ft)
    rep = O.headline(O.replace_pose(E, i0), ffl, ft)
    # 죄 없는 자세 대조(중앙값 근처 12 개)
    order = np.argsort(np.abs(np.abs(x) - med))
    ctrl = [O.headline(O.replace_pose(E, int(j)), ffl, ft) for j in order[:12]]
    dctrl = max(abs((c["moving_power_db"] or 0) - (base["moving_power_db"] or 0))
                for c in ctrl)
    d1 = (rep["moving_power_db"] - base["moving_power_db"])
    return dict(argmax_pose=i0,
                isolation=round(float(v[0] / v[1]), 4),
                top1_over_median=round(float(v[0] / med), 3),
                replace_one_d_moving_power_db=round(float(d1), 4),
                replace_one_d_rhythm_pp=round(float(rep["rhythm_pct"]
                                                    - base["rhythm_pct"]), 4),
                innocent_control_max_abs_db=round(float(dctrl), 5),
                dominance=(round(float(abs(d1) / dctrl), 2) if dctrl > 0 else None),
                over_grid_band=bool(abs(d1) > NULL_GRID_EL30_DB),
                reads_ko=("자세 하나를 이웃 평균으로 갈아 끼워도 요동 전력이 "
                          f"{d1:+.3f} dB 움직인다 — 격자 밴드 {NULL_GRID_EL30_DB} dB "
                          + ("**밖**(⚠튐 의심)" if abs(d1) > NULL_GRID_EL30_DB
                             else "안(튐 아님)")))


def rung(lo: dict, hi: dict, octaves: float) -> dict:
    """한 계단 — 전부 (큰 예산 − 작은 예산)."""
    def dd(k):
        a, b = lo.get(k), hi.get(k)
        return None if (a is None or b is None) else round(float(b - a), 3)

    d_floor = dd("above_floor_db")
    per_oct = None if d_floor is None else round(d_floor / octaves, 3)
    # 세 갈래 중 어디에 가장 가까운가 (dB 거리)
    dist = ({k: round(abs(d_floor - v), 3) for k, v in PRED.items()}
            if d_floor is not None else None)
    return dict(
        lo=lo["cell"], hi=hi["cell"], spp_lo=lo["spp"], spp_hi=hi["spp"],
        ray_factor=(None if not lo["spp"] else round(hi["spp"] / lo["spp"], 4)),
        octaves=round(octaves, 3),
        npaths_lo=lo["npaths"]["median"], npaths_hi=hi["npaths"]["median"],
        npaths_ratio=(None if not lo["npaths"]["median"]
                      else round(hi["npaths"]["median"] / lo["npaths"]["median"], 4)),
        d_moving_power_db=dd("moving_power_db"),
        d_dc_power_db=dd("dc_power_db"),
        d_above_floor_db=d_floor,
        d_above_floor_density_db=dd("above_floor_density_db"),
        d_above_comb_db=dd("above_comb_db"),
        d_below_tip_db=dd("below_tip_db"),
        d_comb_over_floor_db=dd("comb_over_floor_db"),
        d_rhythm_pp=dd("rhythm_share_pct"),
        d_comb_contrast_db=dd("comb_contrast_db"),
        d_floor_per_path_db=dd("floor_per_path_db"),
        floor_db_per_octave=per_oct,
        moving_db_per_octave=(None if dd("moving_power_db") is None
                              else round(dd("moving_power_db") / octaves, 3)),
        distance_to_hypotheses_db=dist,
        nearest_hypothesis=(None if dist is None else min(dist, key=dist.get)),
        over_null=dict(
            rerun_0p07=(None if d_floor is None
                        else bool(abs(d_floor) > NULL_RERUN_DIFFR_ON_DB)),
            grid_0p37=(None if d_floor is None
                       else bool(abs(d_floor) > NULL_GRID_EL30_DB)),
            seed_sd_1p833=(None if d_floor is None
                           else bool(abs(d_floor) > NULL_SEED_SD_DB))))


def repaired_delta(a_key: str, b_key: str, k: int = 8) -> dict:
    """⭐튐 강건판 — 두 칸 통틀어 가장 튄 자세 k 개를 **양쪽에서 똑같이** 이웃 평균으로
    갈아 끼우고 다시 잰 차이. ⛔지우지 않는다(지우면 표집 간격이 깨져 빗살 잣대가 망가진다)."""
    arm = a_key.rsplit("/", 1)[0]
    el = float(a_key.rsplit("el", 1)[1])
    rates = A.arm_rates(arm)
    ft, ffl = A.f_tip_at(rates, el), rates["f_flash_hz"]
    E0 = np.asarray(A.Z[a_key], complex)
    E1 = np.asarray(A.Z[b_key], complex)
    x0, x1 = E0 - E0.mean(), E1 - E1.mean()
    m0, m1 = np.median(np.abs(x0)), np.median(np.abs(x1))
    rel = np.maximum(np.abs(x0) / m0, np.abs(x1) / m1)
    bad = np.argsort(rel)[::-1][:k]
    for i in bad:                                     # ⭐갈아 끼우기(삭제 아님)
        E0 = O.replace_pose(E0, int(i))
        E1 = O.replace_pose(E1, int(i))
    c0, c1 = D.columns(E0, PRF, ffl, ft), D.columns(E1, PRF, ffl, ft)
    return dict(k_replaced=k, replaced_poses=[int(i) for i in sorted(bad)],
                d_moving_power_db=round(c1["ac_db"] - c0["ac_db"], 3),
                d_above_floor_db=round(c1["above_floor_db"] - c0["above_floor_db"], 3),
                d_rhythm_pp=round(c1["rhythm_share_pct"] - c0["rhythm_share_pct"], 3))


def pairwise(a_key: str, b_key: str) -> dict:
    """두 칸의 파형 관계 — 담김계수·상관·잔차의 얼굴."""
    e0 = np.asarray(A.Z[a_key], complex); e0 = e0 - e0.mean()
    e1 = np.asarray(A.Z[b_key], complex); e1 = e1 - e1.mean()
    if not (np.any(e0) and np.any(e1)):
        return dict(degenerate=True)
    arm = a_key.rsplit("/", 1)[0]
    el = float(a_key.rsplit("el", 1)[1])
    rates = A.arm_rates(arm)
    ft, ffl = A.f_tip_at(rates, el), rates["f_flash_hz"]
    co = np.vdot(e0, e1) / np.vdot(e0, e0)
    res = e1 - e0
    rr = A.rhythm_share(res, ffl, ft)
    return dict(
        abs_rho=round(float(abs(np.vdot(e0, e1))
                            / (np.linalg.norm(e0) * np.linalg.norm(e1))), 6),
        rho_null=round(float(1.0 / math.sqrt(e0.size)), 6),
        contain_coeff=round(float(abs(co)), 6),
        contain_phase_deg=round(float(np.degrees(np.angle(co))), 2),
        residual_over_lo_db=round(float(10 * math.log10(
            np.mean(np.abs(res) ** 2) / np.mean(np.abs(e0) ** 2))), 3),
        residual_power_db=round(float(10 * math.log10(np.mean(np.abs(res) ** 2))), 3),
        residual_rhythm_pct=(None if rr[0] is None else round(rr[0], 2)),
        residual_rhythm_null_pct=(None if rr[1] is None else round(rr[1], 2)))


def main() -> None:
    els_missing = [k for k in LAD.values()
                   if f"{k}/el{LAD_EL:+.0f}" not in A.Z.files]
    if els_missing:
        raise SystemExit(f"⛔ 원장에 없는 팔: {els_missing} — 먼저 --merge 를 돌린다")

    cells = {k: cell(v, LAD_EL) for k, v in LAD.items()}
    ffl = A.arm_rates(LAD[(1, 4_000_000_000)])["f_flash_hz"]
    ftp = A.f_tip_at(A.arm_rates(LAD[(1, 4_000_000_000)]), LAD_EL)

    # ── 0. 별칭 정합성 게이트 ────────────────────────────────────────────
    alias = dict(
        claim_ko=("`_phys_d1` 과 `_swR1D1E1F1_d1` 은 같은 솔버 설정인가 — "
                  "사다리를 이어 붙여도 되나"),
        source_ko=("elevation_sweep_md.py:341-352 — `--physics` 는 "
                   "sw=dict(refraction=True, diffraction=True, edge_diffraction=True) "
                   "이고 diffuse 는 상수 True 다. `--sw R1D1E1F1` 은 같은 dict 에 "
                   "diffuse=True. 깊이는 둘 다 `--max-depth 1` 로 명시했다."),
        shard_cfg={}, verdict_ko=None)
    for k, arm in LAD.items():
        f = sorted(glob.glob(f"{SHD}/{arm}_el{LAD_EL:+.0f}_*.npz"))[0]
        z = np.load(f)
        alias["shard_cfg"][arm] = dict(
            cfg=np.asarray(z["cfg"], float).tolist(),
            cfg_cols_ko="[range_m, max_depth, spp, physics_flag, R, D, E] (옛 샤드는 앞 4 개만)",
            n_shards=len(glob.glob(f"{SHD}/{arm}_el{LAD_EL:+.0f}_*.npz")),
            shard_mtime_kst=kst(f))
        z.close()
    # ⭐자세 집합 게이트 — 샤드 수가 4 ↔ 16 으로 다르다. 같은 자세를 재고 있나
    pose_gate = {}
    for k, arm in LAD.items():
        ii = []
        for f in sorted(glob.glob(f"{SHD}/{arm}_el{LAD_EL:+.0f}_*.npz")):
            z = np.load(f); ii.append(np.asarray(z["idx"], int)); z.close()
        u = np.sort(np.concatenate(ii))
        pose_gate[arm] = dict(
            n_shards=len(ii), n_idx=int(u.size), n_unique=int(np.unique(u).size),
            covers_0_to_8191=bool(np.array_equal(u, np.arange(8192))))
    alias["pose_set_gate"] = dict(
        why_ko=("1e9 팔은 샤드 4 개 · 4e9 팔은 16 개다. 샤드는 `idx = arange(shard, n, "
                "nshards)` 로 자세를 나눠 갖고, 합집합이 0~8191 이면 **네 칸이 같은 자세 "
                "8192 개를 잰 것**이다(로터 위상 ph 는 n·prf 만으로 정해져 네 칸이 같다). "
                "샤드 수는 판정에 안 들어온다."),
        per_arm=pose_gate,
        all_pass=bool(all(v["covers_0_to_8191"] for v in pose_gate.values())))
    alias["vintage_ko"] = (
        "⚠샤드가 구워진 날이 다르다 — 4e9 깊이 1 은 08-13(cfg 4 열, 옛 형식) · 4e9 깊이 3 은 "
        "08-14 · 1e9 두 칸은 08-16(cfg 7 열)이다. 그래서 **깊이 3 계단이 더 깨끗하다** "
        "(양쪽 다 7 열 신형식). 두 계단이 +6.23 · +6.93 dB 로 같은 답을 내므로 «옛 코드가 "
        "만든 차이» 로는 안 읽는다. cfg 열 수는 출처 기록의 폭일 뿐 솔버 설정이 아니다.")
    alias["verdict_ko"] = (
        "✅ 같다. 깊이 1 두 칸의 cfg 가 [15.0, 1.0, spp, ...] 로 같고, `phys` 팔은 "
        "physics_flag=1 로 R·D·E 열이 아예 없는 **옛 샤드 형식**이라 그 세 열이 비어 "
        "있을 뿐이다(그 형식에서 physics=1 은 셋 다 켬을 뜻한다). ⚠«별칭이 같다» 는 "
        "**설정**이 같다는 뜻이고 **결과가 비트동일**하다는 뜻이 아니다 — 광선 예산이 "
        "다르므로 결과는 당연히 다르다.")

    # ── 1. 튐 검사 ───────────────────────────────────────────────────────
    cen = json.load(open(os.path.join(ROOT, "outputs", "outlier_census_0816.json")))
    cen_by = {c["cell"]: c for c in cen["cells"]}
    outl = {}
    for k, arm in LAD.items():
        ck = f"{arm}/el{LAD_EL:+.0f}"
        rec = cen_by.get(ck)
        outl[ck] = dict(
            in_census_0816=bool(rec),
            census_grade=(rec["grade"] if rec else None),
            census_classes=(rec["classes"] if rec else None),
            census_why_ko=(rec.get("why_ko") if rec else None),
            census_replace_one_d_moving_power_db=(
                rec["impact"]["replace_one"]["d_moving_power_db"] if rec else None),
            measured_here=spike(arm, LAD_EL, ffl, ftp))
    outl["_note_ko"] = (
        f"⭐census 원장은 {cen['_meta']['ledger_state']['n_rows']} 행 판이라 "
        f"1e9 두 칸이 아직 없다(병합으로 411 행이 된 뒤에 들어온 칸). 그 두 칸은 "
        f"outlier_census_0816 의 함수(headline·replace_pose)를 **그대로 임포트**해 "
        f"여기서 직접 쟀다. ⭐자세는 지우지 않고 이웃 평균으로 갈아 끼웠다.")

    # ── 2. 사다리 ────────────────────────────────────────────────────────
    rungs = {
        "depth1_1e9_to_4e9": rung(cells[(1, 1_000_000_000)],
                                  cells[(1, 4_000_000_000)], OCT),
        "depth3_1e9_to_4e9": rung(cells[(3, 1_000_000_000)],
                                  cells[(3, 4_000_000_000)], OCT)}
    for r in rungs.values():
        r["waveform"] = pairwise(r["lo"], r["hi"])
        r["repaired"] = repaired_delta(r["lo"], r["hi"], k=8)

    # ── 3. 깊이 증분을 두 예산에서 ───────────────────────────────────────
    def depth_step(spp):
        a, b = cells[(1, spp)], cells[(3, spp)]
        d = rung(a, b, 1.0)          # 옥타브 나눗셈은 의미 없다 — 1 로 두고 무시
        for k in ("floor_db_per_octave", "moving_db_per_octave", "octaves",
                  "distance_to_hypotheses_db", "nearest_hypothesis", "ray_factor"):
            d.pop(k, None)
        d["waveform"] = pairwise(a["cell"], b["cell"])
        d["repaired"] = repaired_delta(a["cell"], b["cell"], k=8)
        d["spp"] = spp
        return d

    depth = {f"spp_{s}": depth_step(s) for s in (1_000_000_000, 4_000_000_000)}

    # 2×2 가법성 — 광선 몫 + 깊이 몫이 전체를 설명하나
    m = {k: cells[k]["moving_power_db"] for k in cells}
    f = {k: cells[k]["above_floor_db"] for k in cells}
    inter = dict(
        moving_power=dict(
            d_ray_at_d1=round(m[(1, 4_000_000_000)] - m[(1, 1_000_000_000)], 3),
            d_ray_at_d3=round(m[(3, 4_000_000_000)] - m[(3, 1_000_000_000)], 3),
            d_depth_at_1e9=round(m[(3, 1_000_000_000)] - m[(1, 1_000_000_000)], 3),
            d_depth_at_4e9=round(m[(3, 4_000_000_000)] - m[(1, 4_000_000_000)], 3),
            total=round(m[(3, 4_000_000_000)] - m[(1, 1_000_000_000)], 3),
            interaction_db=round((m[(3, 4_000_000_000)] - m[(1, 4_000_000_000)])
                                 - (m[(3, 1_000_000_000)] - m[(1, 1_000_000_000)]), 3)),
        above_floor=dict(
            d_ray_at_d1=round(f[(1, 4_000_000_000)] - f[(1, 1_000_000_000)], 3),
            d_ray_at_d3=round(f[(3, 4_000_000_000)] - f[(3, 1_000_000_000)], 3),
            d_depth_at_1e9=round(f[(3, 1_000_000_000)] - f[(1, 1_000_000_000)], 3),
            d_depth_at_4e9=round(f[(3, 4_000_000_000)] - f[(1, 4_000_000_000)], 3),
            total=round(f[(3, 4_000_000_000)] - f[(1, 1_000_000_000)], 3),
            interaction_db=round((f[(3, 4_000_000_000)] - f[(1, 4_000_000_000)])
                                 - (f[(3, 1_000_000_000)] - f[(1, 1_000_000_000)]), 3)))

    # ── 4. 「회절이 얹는 것」 — 4e9 에서만 가능한 뺄셈 ────────────────────
    dflip = {}
    on = cells[(1, 4_000_000_000)]
    for combo, arm in DFLIP.items():
        c = cell(arm, LAD_EL)
        if c is None:
            continue
        dflip[combo] = dict(
            arm=arm, combo=combo,
            above_floor_db=c["above_floor_db"], moving_power_db=c["moving_power_db"],
            npaths_median=c["npaths"]["median"],
            d_floor_vs_D_on_db=round(on["above_floor_db"] - c["above_floor_db"], 3),
            d_moving_vs_D_on_db=round(on["moving_power_db"] - c["moving_power_db"], 3))
    dflip["_note_ko"] = (
        "⚠회절을 끈 짝은 **4e9 에만** 있다(15 m·el −30). 1e9 에는 회절 끈 짝이 없어서 "
        "«회절이 얹는 양» 자체의 사다리는 못 만든다 — 이 절은 4e9 한 자리의 뺄셈이고, "
        "사다리 판정은 위 rungs 가 한다.")

    # ── 5. 대조 사다리 (10 m) ────────────────────────────────────────────
    def ladder(arms, els):
        out = {}
        for el in els:
            seq = []
            for arm, spp in arms:
                c = cell(arm, el)
                if c is None:
                    continue
                seq.append(dict(arm=arm, spp=spp, n_poses=c["n_poses"],
                                n_missing=c["n_missing"], max_depth=c["max_depth"],
                                npaths_median=c["npaths"]["median"],
                                moving_power_db=c["moving_power_db"],
                                dc_power_db=c["dc_power_db"],
                                above_floor_db=c["above_floor_db"],
                                floor_per_path_db=c["floor_per_path_db"],
                                above_comb_db=c["above_comb_db"],
                                below_tip_db=c["below_tip_db"],
                                rhythm_share_pct=c["rhythm_share_pct"],
                                ac_over_dc=c["ac_over_dc"],
                                near_numeric_floor=c["near_numeric_floor"]))
            seq = [s for s in seq if not s["n_missing"]]
            if len(seq) < 2:
                continue
            oc = math.log2(seq[-1]["spp"] / seq[0]["spp"])
            out[f"el{el:+.0f}"] = dict(
                rungs=seq, octaves_total=round(oc, 3),
                d_above_floor_db=round(seq[-1]["above_floor_db"]
                                       - seq[0]["above_floor_db"], 3),
                d_moving_power_db=round(seq[-1]["moving_power_db"]
                                        - seq[0]["moving_power_db"], 3),
                d_dc_power_db=round(seq[-1]["dc_power_db"] - seq[0]["dc_power_db"], 3),
                d_floor_per_path_db=round(seq[-1]["floor_per_path_db"]
                                          - seq[0]["floor_per_path_db"], 3),
                floor_db_per_octave=round((seq[-1]["above_floor_db"]
                                           - seq[0]["above_floor_db"]) / oc, 3),
                npaths_ratio=(round(seq[-1]["npaths_median"] / seq[0]["npaths_median"], 3)
                              if seq[0]["npaths_median"] else None),
                spp_ratio=round(seq[-1]["spp"] / seq[0]["spp"], 2))
        return out

    ctrl = dict(
        warning_ko=("⚠이 두 사다리는 **10 m**(원거리장 경계 14.08 m 안쪽)이고 자세 4096 이다. "
                    "헤드라인 사다리는 15 m·자세 8192 다 — 절대 dB 를 섞지 않는다. "
                    "여기서 가져다 쓰는 것은 **기울기(dB/옥타브)의 부호와 크기**뿐이다."),
        diffraction_off_depth1=ladder(CTRL_OFF, CTRL_ELS),
        diffraction_on_depth3=ladder(CTRL_ON, CTRL_ELS))

    # ── 6. 기제 — «경로 하나당 일정한 몫이 쌓이나» ────────────────────────
    off30 = ctrl["diffraction_off_depth1"].get("el-30", {})
    mech = dict(
        question_ko=("바닥이 광선에 따라 올라간다면 무엇이 쌓이나 — 찾은 **경로 하나당** "
                     "일정한 무작위 위상 몫인가"),
        method_ko=("바닥 절대전력에서 그 칸의 경로 수(중앙값)를 나눈다 "
                   "(floor_per_path_db = above_floor_db − 10log10 npaths_median). "
                   "이 수가 예산을 올려도 그대로면 바닥은 경로 수에 비례한다."),
        diffraction_on_15m=[dict(
            cell=cells[k]["cell"], spp=cells[k]["spp"],
            npaths_median=cells[k]["npaths"]["median"],
            above_floor_db=cells[k]["above_floor_db"],
            floor_per_path_db=cells[k]["floor_per_path_db"]) for k in sorted(cells)],
        d_floor_per_path_db=dict(
            depth1=rungs["depth1_1e9_to_4e9"]["d_floor_per_path_db"],
            depth3=rungs["depth3_1e9_to_4e9"]["d_floor_per_path_db"]),
        diffraction_off_10m_el30=dict(
            rungs=[dict(spp=s["spp"], npaths_median=s["npaths_median"],
                        above_floor_db=s["above_floor_db"],
                        floor_per_path_db=s["floor_per_path_db"])
                   for s in off30.get("rungs", [])],
            d_above_floor_db=off30.get("d_above_floor_db"),
            d_floor_per_path_db=off30.get("d_floor_per_path_db"),
            npaths_ratio=off30.get("npaths_ratio")),
        reads_ko=(
            "⭐**회절 켠 팔에서는 바닥이 경로 수에 거의 정비례한다.** 경로 하나당 바닥은 "
            f"광선 4 배에 {rungs['depth1_1e9_to_4e9']['d_floor_per_path_db']:+.2f} dB"
            f"(깊이 1) · {rungs['depth3_1e9_to_4e9']['d_floor_per_path_db']:+.2f} dB"
            "(깊이 3) 밖에 안 움직인다 — 즉 새로 찾은 경로마다 **같은 크기의 무작위 위상 "
            "몫**이 하나씩 더 얹힌 것이다. 회절 끈 팔은 정반대다: 같은 자리에서 경로가 "
            f"{off30.get('npaths_ratio')} 배로 늘어도 바닥은 "
            f"{off30.get('d_above_floor_db')} dB 로 제자리고, 그래서 경로당 바닥은 "
            f"{off30.get('d_floor_per_path_db')} dB 로 크게 **내려간다**(경로가 늘어도 "
            "총합이 그대로라는 뜻 = 수렴한 적분). 두 팔의 차이가 판정의 실체다."))

    # ── 7. 판정 ──────────────────────────────────────────────────────────
    r1, r3 = rungs["depth1_1e9_to_4e9"], rungs["depth3_1e9_to_4e9"]
    fl = [r1["d_above_floor_db"], r3["d_above_floor_db"]]
    mv = [r1["d_moving_power_db"], r3["d_moving_power_db"]]
    both_over_seed = all(abs(v) > NULL_SEED_SD_DB for v in fl)
    same_sign = (fl[0] > 0) == (fl[1] > 0)
    verdict = dict(
        headline_ko=None, floor_deltas_db=fl, moving_deltas_db=mv,
        floor_db_per_octave=[r1["floor_db_per_octave"], r3["floor_db_per_octave"]],
        nearest_hypothesis=[r1["nearest_hypothesis"], r3["nearest_hypothesis"]],
        both_rungs_over_seed_band=bool(both_over_seed),
        both_rungs_same_sign=bool(same_sign),
        prereg_predictions_db=PRED,
        nulls_db=dict(rerun_diffraction_on=NULL_RERUN_DIFFR_ON_DB,
                      grid_el30_borrowed=NULL_GRID_EL30_DB,
                      seed_sd_spp4e9=NULL_SEED_SD_DB,
                      seed_ptp_spp4e9=NULL_SEED_PTP_DB))

    if not both_over_seed:
        verdict["headline_ko"] = (
            "⚠**판정 불가** — 광선 4 배에 상한 위 바닥이 시드 산포 밴드(1.833 dB) 안에서만 "
            "움직였다. 이 사다리로는 «표집» 과 «물리» 를 못 가른다.")
        verdict["answer"] = "undecided"
    elif same_sign and fl[0] > 0:
        verdict["headline_ko"] = (
            f"⭐**계산 표집이다 — 그것도 «평균으로 지워지는 잡음» 이 아니라 «쌓이는» 쪽이다.** "
            f"광선을 4 배 부으면 회절 켠 팔의 상한 위 바닥이 깊이 1 에서 "
            f"{fl[0]:+.2f} dB · 깊이 3 에서 {fl[1]:+.2f} dB **올라간다**. 사전등록의 "
            f"«−6.02 dB 면 표집» 은 부호를 하나만 봤다 — 관측은 **+6.02 dB 쪽**(∝N)이다. "
            f"둘 다 광선 수에 매인 값이라 **결정론적 물리가 아니다**.")
        verdict["answer"] = "sampling_accumulate"
    elif same_sign and fl[0] < 0:
        verdict["headline_ko"] = (
            f"⭐**계산 표집이다(평균으로 지워지는 쪽).** 광선 4 배에 바닥이 "
            f"{fl[0]:+.2f} · {fl[1]:+.2f} dB 내려간다.")
        verdict["answer"] = "sampling_average"
    else:
        verdict["headline_ko"] = (
            f"⚠두 계단의 **부호가 갈린다**({fl[0]:+.2f} · {fl[1]:+.2f} dB) — "
            f"한 방향으로 못 읽는다.")
        verdict["answer"] = "inconsistent"

    # ⭐엔진 대조 — 회절 끔 팔은 같은 축에서 안 움직인다
    verdict["control_contrast_ko"] = (
        "회절을 **끄면** 같은 축이 죽는다 — 10 m·깊이 1 팔에서 광선을 90~360 배 부어도 "
        "상한 위 바닥이 el −15~−90 에서 −1.52 ~ +1.23 dB(−0.18 ~ +0.19 dB/옥타브) 밖에 "
        "안 움직인다(R17 과 같은 결론). 회절을 **켜면** 10 m·깊이 3 팔에서 22.5 배에 "
        "+10.1 ~ +35.3 dB(+2.26 ~ +7.86 dB/옥타브) 오른다. 15 m 새 사다리(+3.11 · "
        "+3.47 dB/옥타브)는 그 켠 쪽 무리 안이다. ⚠거리(10 m ↔ 15 m)와 자세 수"
        "(4096 ↔ 8192)가 달라 **절대 dB 는 안 섞었고 기울기만** 나란히 놓았다. "
        "⚠정면(el 0)은 회절을 꺼도 오른다(+66 dB) — R17 이 이미 예외로 적어 둔 자리다"
        "(정지 성분이 이미 수렴해 새 경로가 전부 요동으로 들어간다).")
    verdict["waveform_contrast_ko"] = (
        "⭐**광선 예산이 반사 깊이보다 답을 더 많이 바꾼다.** 같은 깊이에서 광선만 4 배로 "
        f"바꾸면 두 시계열의 상관이 |ρ| = "
        f"{rungs['depth1_1e9_to_4e9']['waveform']['abs_rho']:.3f} · "
        f"{rungs['depth3_1e9_to_4e9']['waveform']['abs_rho']:.3f} 로 떨어지는데, 같은 "
        f"예산에서 깊이를 1→3 으로 바꾸면 |ρ| = "
        f"{depth['spp_1000000000']['waveform']['abs_rho']:.3f} · "
        f"{depth['spp_4000000000']['waveform']['abs_rho']:.3f} 로 훨씬 높게 남는다"
        f"(백색 널 {rungs['depth1_1e9_to_4e9']['waveform']['rho_null']:.3f}). 수렴한 "
        "계산이라면 광선을 늘릴수록 ρ 가 1 로 가야 한다 — 안 간다.")

    # 딸린 물음
    dr = [inter["moving_power"]["d_ray_at_d1"], inter["moving_power"]["d_ray_at_d3"]]
    dd_ = [inter["moving_power"]["d_depth_at_1e9"], inter["moving_power"]["d_depth_at_4e9"]]
    drift = round(abs(dd_[1] - dd_[0]), 3)
    npr = rungs["depth1_1e9_to_4e9"]["npaths_ratio"]
    dpr = depth["spp_4000000000"]["npaths_ratio"]
    verdict["depth_question"] = dict(
        question_ko="깊이 축의 «회절 켠 조합 +1.32~+2.33 dB» 도 광선 몫으로 설명되나",
        d_depth_moving_db=dd_, d_ray_moving_db=dr,
        ray_over_depth=(None if not dd_[1] else round(abs(dr[0]) / abs(dd_[1]), 2)),
        depth_drift_across_budgets_db=drift,
        depth_drift_inside_seed_band=bool(drift < NULL_SEED_SD_DB),
        npaths_ratio_ray=npr, npaths_ratio_depth=dpr,
        depth_predicted_if_path_count_db=round(10 * math.log10(dpr), 3),
        answer_ko=(
            "**아니다 — 그러나 그 +2 dB 도 물리로 인용하면 안 된다.** 셋으로 갈라 적는다. "
            f"①**직접 원인은 아니다**: 깊이 1→3 은 경로를 {dpr:.3f} 배(+"
            f"{10 * math.log10(dpr):.2f} dB) 밖에 안 늘리는데 레벨은 {dd_[1]:+.2f} dB "
            "올린다 — 광선 사다리에서 본 «경로당 일정 몫» 만으로는 그 크기가 안 나온다. "
            f"②**그런데 광선 축이 훨씬 세다**: 물리적 의미가 없는 손잡이(광선 4 배)가 같은 "
            f"레벨을 {dr[0]:+.2f} · {dr[1]:+.2f} dB 움직인다 — 깊이 축 전체가 하는 일의 "
            f"{abs(dr[0]) / abs(dd_[1]):.1f}~{abs(dr[1]) / abs(dd_[0]):.1f} 배다. "
            "깊이 증분은 **수렴하지 않은 두 수의 차**이므로 그 절대값은 정본이 못 된다. "
            f"③**깊이 증분 자체도 예산을 탄다**: 1e9 에서 {dd_[0]:+.2f} · 4e9 에서 "
            f"{dd_[1]:+.2f} dB 로 {drift:.2f} dB 움직인다. ⚠단 이 {drift:.2f} dB 는 시드 "
            f"산포 밴드(1.833 dB) **안**이라 «깊이 증분이 예산에 비례한다» 고까지는 "
            "**판정 불가**다 — 계단이 둘뿐이라 기울기를 못 낸다."),
        what_would_close_it_ko=(
            "깊이 1·3 × 광선 3 계단(예: 1e9·2e9·4e9) 이면 깊이 증분의 기울기를 시드 밴드 "
            "밖으로 끌어낼 수 있다. 더 싼 길은 **같은 예산에서 시드만 바꾼 회절 켠 판** "
            "(현재 `--seed` 배관 없음 — 백로그 11·12 위, 함정 2)이다. 그게 있어야 이 "
            "판의 널이 «빌려 온 40 m·el −15 값» 을 벗어난다."))

    # ⭐바닥만 오르는 게 아니다 — 판을 통째로 들어 올린다
    verdict["not_only_the_floor"] = dict(
        d_for_4x_rays_db=dict(
            dc_power=[r1["d_dc_power_db"], r3["d_dc_power_db"]],
            moving_power=[r1["d_moving_power_db"], r3["d_moving_power_db"]],
            above_floor=[r1["d_above_floor_db"], r3["d_above_floor_db"]],
            above_comb=[r1["d_above_comb_db"], r3["d_above_comb_db"]],
            below_tip=[r1["d_below_tip_db"], r3["d_below_tip_db"]]),
        ac_over_dc=[cells[k]["ac_over_dc"] for k in sorted(cells)],
        floor_minus_moving_db=[round(cells[k]["above_floor_db"]
                                     - cells[k]["moving_power_db"], 3)
                               for k in sorted(cells)],
        path_cap="max_num_paths_per_src = 2,000,000 · 관측 최대 428 → **잘림 없음**",
        reads_ko=(
            "⭐«바닥만» 오르는 게 아니다 — 광선 4 배에 정지 성분 +4.86~4.87 · 요동 "
            "+5.25~6.10 · 상한 위 바닥 +6.23~6.93 · 빗살 +5.64~6.20 · 상한 아래 "
            "+5.05~6.27 dB 로 **판 전체가 함께 올라간다**(바닥이 가장 빠르다). 그래서 "
            "정확한 말은 «회절 켠 팔은 이 예산 범위에서 **아무것도 수렴하지 않았다**» 다. "
            "AC/DC 는 7.1e-4→7.7e-4 · 9.6e-4→12.8e-4 로 거의 그대로라, 예산은 무늬의 "
            "**모양**보다 **크기**를 바꾼다. ⇒ «바닥이 표집이냐» 라는 물음의 답은 어느 "
            "쪽으로 읽어도 같다 — **결정론적 물리가 아니다**."))

    verdict["what_this_does_not_say_ko"] = [
        "⛔«회절은 물리가 아니다» 가 아니다. 잰 것은 **이 예산 범위에서 회절 켠 팔의 상한 위 "
        "바닥이 수렴하지 않았다** 는 것뿐이다. 더 부으면 어디선가 꺾일 수도 있다 — 그건 안 쟀다.",
        "⛔«Sionna 가 틀렸다» 가 아니다. 정규화가 빠졌는지 경로 집합이 원래 안 닫히는지는 "
        "이 원장으로 못 가른다 — 그러려면 솔버 안의 확산·회절 진폭 규약을 소스에서 따로 읽어야 한다.",
        "⛔이 판은 **el −30° 한 자리 · 15 m · matrice4e** 다. 앙각·거리·기체를 옮겨도 같은지는 "
        "10 m 대조 사다리(앙각 7 점)가 방향만 지지할 뿐, 15 m 에서는 안 쟀다.",
        "⛔계단이 **둘**뿐이라 «기울기» 라고 부르지만 회귀가 아니다 — 두 점을 이은 선이다.",
        "⚠D1 조합(R1D1E1F1)은 표준 프레임 밖이다 — **별도 트랙**. 표준 두 팔"
        "(R0D0E0F1·R1D0E0F1)의 정본 수치는 이 판정에 안 흔들린다."]
    verdict["consequences_ko"] = [
        "⭐**회절 켠 팔의 절대 레벨은 인용하면 안 된다** — 광선 예산이 정본이 없는 손잡이인데 "
        "레벨이 그 손잡이에 +3 dB/옥타브로 매여 있다. 인용할 거면 «spp 4e9 한정» 꼬리표가 "
        "«깊이 1 한정» 보다 먼저 붙어야 한다.",
        "⭐**깊이 축 미해결 ②(«+2 dB 가 물리냐 표집이냐»)는 이 판으로 «물리로 인용 불가» 까지 "
        "간다** — 원인 귀속은 아직 열려 있다(위 depth_question ③).",
        "⭐**회절 켠 팔로 GPU 를 더 사도 이 자리는 안 좋아진다** — 바닥이 예산을 따라 올라가므로 "
        "«더 부으면 수렴한다» 는 기대가 이 범위에서는 반증됐다. 백로그 26 위(두께 × 회절 켠 팔, "
        "≈5.9 워커-시간)는 **바닥이 예산에 매인 팔 위에서** 두께를 재는 셈이라, 사기 전에 "
        "«무엇에 대한 두께 감도인가» 를 다시 적어야 한다.",
        "⭐리듬(구조) 판정은 안 흔들린다 — 얹히는 것이 **백색**이라(잔차 리듬 몫 12.6~12.9 % ↔ "
        "널 12.65 %) 무늬가 아니라 바닥만 오른다. 「회절이 확산 바닥을 덮는다」는 서술은 살아 있다."]

    # ── 8. 그림 ──────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig, axs2 = plt.subplots(2, 2, figsize=(13.2, 9.0))
    axs = axs2.ravel()
    ax = axs[0]
    for dep, col_, mk in ((1, "#1f77b4", "o"), (3, "#d62728", "s")):
        xs = [1_000_000_000, 4_000_000_000]
        ys = [cells[(dep, s)]["above_floor_db"] for s in xs]
        ax.plot(xs, ys, mk + "-", color=col_, label=f"depth {dep}")
        for s, y in zip(xs, ys):
            ax.annotate(f"{y:.1f}", (s, y), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=8.5, color=col_)
    y0 = cells[(1, 1_000_000_000)]["above_floor_db"]
    for nm, dv, c_, ls in (("+3.01 dB/oct  (power ∝ N)", PRED["sampling_accumulate"],
                            "#888", ":"),
                           ("0 dB/oct  (deterministic)", 0.0, "#444", "-."),
                           ("−3.01 dB/oct  (power ∝ 1/N)", PRED["sampling_average"],
                            "#888", "--")):
        ax.plot([1e9, 4e9], [y0, y0 + dv], ls, color=c_, lw=1.2, label=nm)
    ax.set_xscale("log")
    ax.set_xlabel("rays per source (spp)")
    ax.set_ylabel("floor above tip ceiling  [dB, DC removed]")
    ax.set_title("A · Ray ladder, diffraction ON\n15 m · el −30° · 8192 poses",
                 fontsize=11)
    ax.legend(fontsize=7.6, loc="lower left")
    ax.margins(y=0.16)
    ax.grid(alpha=0.3)

    ax = axs[1]
    lbl = ["moving\npower", "floor\nabove tip", "comb\nabove tip", "below\ntip"]
    k1 = [r1["d_moving_power_db"], r1["d_above_floor_db"], r1["d_above_comb_db"],
          r1["d_below_tip_db"]]
    k3 = [r3["d_moving_power_db"], r3["d_above_floor_db"], r3["d_above_comb_db"],
          r3["d_below_tip_db"]]
    xx = np.arange(len(lbl))
    ax.bar(xx - 0.19, k1, 0.36, color="#1f77b4", label="depth 1")
    ax.bar(xx + 0.19, k3, 0.36, color="#d62728", label="depth 3")
    for xi, (a_, b_) in enumerate(zip(k1, k3)):
        ax.annotate(f"{a_:+.1f}", (xi - 0.19, a_), ha="center", fontsize=8,
                    va="bottom" if a_ >= 0 else "top",
                    xytext=(0, 3 if a_ >= 0 else -3), textcoords="offset points")
        ax.annotate(f"{b_:+.1f}", (xi + 0.19, b_), ha="center", fontsize=8,
                    va="bottom" if b_ >= 0 else "top",
                    xytext=(0, 3 if b_ >= 0 else -3), textcoords="offset points")
    ax.axhline(0, color="k", lw=0.8)
    ax.axhspan(-NULL_SEED_SD_DB, NULL_SEED_SD_DB, color="#999", alpha=0.22,
               label="seed band ±1.83 dB")
    ax.axhline(PRED["sampling_accumulate"], ls=":", color="#555", lw=1.1)
    ax.axhline(PRED["sampling_average"], ls="--", color="#555", lw=1.1)
    ax.set_xticks(xx); ax.set_xticklabels(lbl, fontsize=9)
    ax.set_ylabel("Δ for 4× rays  [dB]")
    ax.set_title("B · What 4× rays moves\n(dotted ±6.02 dB = power ∝ N or 1/N)",
                 fontsize=11)
    ax.legend(fontsize=8, loc="lower left"); ax.grid(alpha=0.3, axis="y")

    # ── C · 대조 — 회절 끔 팔은 같은 축에서 안 움직인다 (10 m) ─────────────
    ax = axs[2]
    for nm, key, c_, mk in (("diffraction OFF (depth 1)", "diffraction_off_depth1",
                             "#2ca02c", "o"),
                            ("diffraction ON (depth 3)", "diffraction_on_depth3",
                             "#d62728", "s")):
        d_ = ctrl[key]
        xs = [float(k.replace("el", "")) for k in d_]
        ys = [d_[k]["floor_db_per_octave"] for k in d_]
        o = np.argsort(xs)
        ax.plot(np.array(xs)[o], np.array(ys)[o], mk + "-", color=c_, label=nm)
    ax.axhspan(-0.5, 0.5, color="#999", alpha=0.20,
               label="±0.5 dB/oct (flat)")
    for dep, c_ in ((1, "#1f77b4"), (3, "#7b1fa2")):
        ax.plot([-30], [rungs[f"depth{dep}_1e9_to_4e9"]["floor_db_per_octave"]],
                "*", ms=16, color=c_, zorder=5,
                label=f"new 15 m rung, depth {dep}")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("elevation  [deg]")
    ax.set_ylabel("floor slope  [dB per octave of rays]")
    ax.set_title("C · Control — only the diffraction-on arm rides the ray budget\n"
                 "(10 m ladders, 4096 poses; slopes only, no absolute dB mixing)",
                 fontsize=10.4)
    ax.margins(y=0.22)
    ax.set_ylim(bottom=-4.6)          # 범례가 앉을 빈 자리를 만든다(선과 안 겹치게)
    ax.legend(fontsize=7.8, loc="lower left")
    ax.grid(alpha=0.3)

    ax = axs[3]
    names = ["ray ×4\n@ depth 1", "ray ×4\n@ depth 3",
             "depth 1→3\n@ 1e9", "depth 1→3\n@ 4e9"]
    vals = [dr[0], dr[1], dd_[0], dd_[1]]
    cols = ["#1f77b4", "#1f77b4", "#2ca02c", "#2ca02c"]
    ax.bar(names, vals, color=cols)
    for i, v in enumerate(vals):
        ax.annotate(f"{v:+.2f}", (i, v), ha="center", fontsize=9,
                    va="bottom" if v >= 0 else "top",
                    xytext=(0, 3 if v >= 0 else -3), textcoords="offset points")
    ax.axhspan(-NULL_SEED_SD_DB, NULL_SEED_SD_DB, color="#999", alpha=0.22)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("Δ moving power  [dB, DC removed]")
    ax.set_title("D · Ray budget vs bounce depth\ngrey = seed band ±1.83 dB",
                 fontsize=11)
    ax.tick_params(axis="x", labelsize=8.4)
    ax.margins(y=0.14)
    ax.grid(alpha=0.3, axis="y")
    fig.suptitle("Diffraction-on ray ladder — is the added floor sampling or physics?\n"
                 "separate track: R1D1E1F1 is outside the standard frame  ·  "
                 "all levels with the static (DC) component removed",
                 fontsize=11.8)
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    fig.savefig(FIG, dpi=170)
    plt.close(fig)

    # ── 9. 굽기 ──────────────────────────────────────────────────────────
    out = dict(
        _meta=dict(
            generator="benchmark/free_harvest_ray_ladder_diffraction_0816.py",
            experiment="⭐회절 켠 팔의 광선 사다리 — 백로그 2 위",
            written_at_kst=_dt.datetime.now(
                _dt.timezone(_dt.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M KST"),
            question_ko=("회절이 얹는 바닥이 광선 수에 따라 움직이나(계산 표집) "
                         "안 움직이나(결정론적 물리)"),
            gpu_used="0 — 저장된 원장만 읽었다(sionna.rt·mitsuba 임포트 없음)",
            separate_track_ko=("⚠**별도 트랙** — 이 판의 D1 조합(R1D1E1F1, 회절·모서리 켬)은 "
                               "docs/STANDARD_FRAME.md 가 싣는 두 팔(R0D0E0F1 · R1D0E0F1) "
                               "**밖**이다. 여기 수치는 표준 프레임 정본에 섞지 않는다."),
            conventions_ko=[
                "레벨(dB)은 전부 정지 성분(DC) 제거 후 — moving_power_db",
                "잣대 식은 depth_axis_verdict_0816.columns() 를 그대로 임포트(재작성 없음)",
                "격자 산포 밴드는 앙각마다 다르다 — 이 판은 전부 el −30° 라 0.37 dB "
                "(⚠우리 커널 격자 축에서 «빌려 온» 자다. PathSolver 자신의 밴드가 아니다)",
                "⭐광선 축 물음에는 **시드 산포 1.833 dB** 가 가장 알맞은 널이다 — "
                "예산을 바꾸면 광선 방향 집합이 통째로 바뀌기 때문이다",
                "AC/DC < 1e-11 은 near_numeric_floor — 물리로 안 읽는다",
                "밴드 안이면 «판정 불가» 로 적는다 — «안 바뀐다» 로 단정하지 않는다",
                "튐 검사: census 등급을 먼저 보고 새 칸은 같은 절차로 직접 잰다. "
                "⭐자세는 지우지 않고 이웃 평균으로 갈아 끼운다"],
            sources={
                "ledger_json": dict(
                    path="outputs/elevation_sweep_md.json",
                    mtime=kst(os.path.join(ROOT, "outputs", "elevation_sweep_md.json")),
                    n_rows=len(A.J["rows"])),
                "ledger_npz": dict(
                    path="outputs/elevation_sweep_md.npz",
                    mtime=kst(os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")),
                    n_keys=len(A.Z.files)),
                "shards": "outputs/elev_sweep_shards/",
                "depth_axis": "outputs/depth_axis_verdict_0816.json (재실행 문턱 0.07 dB)",
                "r17": "outputs/raybudget_ac_ladder.json (물리 끔 예산 사다리)",
                "seed": "outputs/raybudget_seed_ladder.json (시드 산포 sd 1.833 dB)",
                "census": "outputs/outlier_census_0816.json (349 행 판)"}),
        prereg=dict(
            written_before_measuring_ko=True,
            hypotheses_db=PRED,
            decision_rule_ko=("바닥 Δ(광선 4 배)가 시드 산포 밴드(±1.833 dB) **밖**이고 "
                              "두 계단(깊이 1·3)의 **부호가 같으면** «광선에 매인 값» 으로 "
                              "읽는다. 밴드 안이면 «판정 불가». ⭐−6.02 도 +6.02 도 "
                              "**둘 다 계산 표집**이다 — 물리는 0 하나뿐이다."),
            why_three_branches_ko=("사전등록의 옛 문안은 «바닥이 광선 수에 반비례해 내려가면 "
                                   "표집» 이라 한 갈래만 봤다. 정규화가 빠진 누적이면 바닥이 "
                                   "**올라간다** — 그것도 광선에 매인 값이므로 «물리» 가 "
                                   "아니다. 그래서 세 갈래로 미리 적었다.")),
        alias_gate=alias,
        cells={f"depth{d}_spp{s}": c for (d, s), c in cells.items()},
        outlier_check=outl,
        rungs=rungs,
        depth_steps=depth,
        factorial_2x2=inter,
        diffraction_flip_at_4e9=dflip,
        control_ladders_10m=ctrl,
        mechanism=mech,
        verdict=verdict,
        figures=["outputs/figures/free_harvest_ray_ladder_diffraction_0816.png"])
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"✅ {OUTJ}\n✅ {FIG}")

    # 콘솔 요약
    print("\n═══ 회절 켠 팔 · 광선 사다리 (15 m · el −30° · 자세 8192) ═══")
    print(f"{'칸':>46} {'spp':>12} {'경로':>7} {'요동dB':>9} {'바닥dB':>10} {'리듬%':>7}")
    for (d, s), c in sorted(cells.items()):
        print(f"{c['arm']:>46} {s:>12} {c['npaths']['median']:>7.0f} "
              f"{c['moving_power_db']:>9.2f} {c['above_floor_db']:>10.2f} "
              f"{c['rhythm_share_pct']:>7.2f}")
    for k, r in rungs.items():
        print(f"\n{k}: 바닥 {r['d_above_floor_db']:+.2f} dB "
              f"({r['floor_db_per_octave']:+.2f} dB/옥타브) · 요동 "
              f"{r['d_moving_power_db']:+.2f} dB · 경로 ×{r['npaths_ratio']:.2f} "
              f"→ 가장 가까운 가설 {r['nearest_hypothesis']}")
    print("\n" + verdict["headline_ko"])


if __name__ == "__main__":
    main()
