#!/usr/bin/env python3
"""재질 정정 판정 원장 생성 — outputs/material_verdict_0816.json

셸 두께(0.5/0.75/1.5 mm)·프롭 0.9 mm 팔을 기본(Sionna 100 mm)과 비교해
docs/MATERIAL_CORRECTION.md §2-4 사전등록 잣대로 채점한다. 전부 CPU·원장 읽기만.
"""
import json, math, sys, datetime
import numpy as np

sys.path.insert(0, "/workspace/sionna/src")
sys.path.insert(0, "/workspace/sionna/benchmark")
from md_mapstyle import flash_spec  # noqa: E402

OUT = "/workspace/sionna/outputs/material_verdict_0816.json"
LEDGER = "/workspace/sionna/outputs/elevation_sweep_md.json"
NPZ = "/workspace/sionna/outputs/elevation_sweep_md.npz"
GRID = "/workspace/sionna/outputs/grid_convergence_check.json"

COMB_TOL_HZ = 8.0
AC_MIN_HZ = 8.0
RHY_HW = 8.0
EPS0 = 8.8541878128e-12
C = 299792458.0

led = json.load(open(LEDGER))
npz = np.load(NPZ)
meta = led["_meta"]
PRF = float(meta["prf_hz"])
FFL = float(meta["f_flash_hz"])
FC = 3.5e9
rows = {(r["engine"], round(float(r["el_deg"]), 3)): r for r in led["rows"]}


# ── 표준 잣대(전부 DC 제거) ──────────────────────────────────────────────────
def series(arm, el):
    return np.asarray(npz[f"{arm}/el{el:+.0f}"], dtype=complex)


def metrics(arm, el):
    E = series(arm, el)
    row = rows[(arm, el)]
    f_tip = float(row["f_tip_hz"])
    dc = complex(E.mean())
    x = E - dc
    n = E.size
    P = np.abs(np.fft.fft(x * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, d=1.0 / PRF)
    fa = np.abs(fr)
    above = fa >= f_tip
    ac_band = fa >= AC_MIN_HZ
    k = np.round(fa / FFL)
    on = (k >= 1) & (np.abs(fa - k * FFL) <= COMB_TOL_HZ)
    p_above, p_ac = float(P[above].sum()), float(P[ac_band].sum())
    d = {
        "arm": arm, "el_deg": el,
        "shell_mm": row["shell_mm"], "prop_mm": row["prop_mm"],
        "n_poses": int(row["n_poses"]), "n_missing": int(row["n_missing"]),
        "f_tip_hz": f_tip,
        "dc_power_db": round(10 * math.log10(abs(dc) ** 2 + 1e-300), 3),
        "ac_power_db": round(10 * math.log10(float((np.abs(x) ** 2).mean()) + 1e-300), 3),
        "level_db_ledger": row["level_db"],
        "rhythm_share_pct": round(100 * float(P[above & on].sum()) / p_above, 3) if p_above > 0 else None,
        "above_f_tip_pct": round(100 * p_above / p_ac, 4) if p_ac > 0 else None,
        "beat_hz_track": row["track"]["beat_hz"],
        "blade_band_power_db_track": row["track"]["band_power_db"],
    }
    frac = p_above / p_ac if p_ac > 0 else None
    d["floor_above_tip_db"] = round(d["ac_power_db"] + 10 * math.log10(frac), 3) if frac and frac > 0 else None
    # 빗살 대비(상한 아래) — build_md_atlas 정의 그대로
    lo, hi = 2.0 * FFL, f_tip
    comb = None
    if hi >= 3.0 * FFL:
        band = (fa >= lo) & (fa <= hi)
        kk = fa / FFL
        on2 = band & (np.abs(kk - np.round(kk)) * FFL <= RHY_HW)
        off2 = band & (np.abs(np.abs(kk - np.floor(kk)) - 0.5) * FFL <= RHY_HW)
        if int(on2.sum()) >= 4 and int(off2.sum()) >= 4:
            num, den = float(P[on2].mean()), float(P[off2].mean())
            if num > 0 and den > 0:
                comb = round(10 * math.log10(num / den), 3)
    d["comb_contrast_db"] = comb
    return d, E


def wave_cmp(a, b):
    x, y = a - a.mean(), b - b.mean()
    na, nb = np.linalg.norm(x), np.linalg.norm(y)
    r = abs(complex(np.vdot(x, y) / (na * nb))) if na and nb else None
    _, _, Sa, _ = flash_spec(np.asarray(x, complex), PRF, FFL)
    _, _, Sb, _ = flash_spec(np.asarray(y, complex), PRF, FFL)
    A = 10 * np.log10(Sa / Sa.max() + 1e-12)
    B = 10 * np.log10(Sb / Sb.max() + 1e-12)
    mc = float(np.corrcoef(A.ravel(), B.ravel())[0, 1])
    return {"abs_rho_dc_removed": round(r, 4), "stft_db_map_corr_dc_removed": round(mc, 4)}


# ── 슬래브 예측(ITU-R P.2040, plastic εr 2.7 · σ 0.02, 편파 전력평균) ────────
lam = C / FC
eps = 2.7 - 1j * 0.02 / (2 * np.pi * FC * EPS0)


def slab_R2(d_m, th_deg):
    th = np.radians(th_deg)
    s, c = np.sin(th), np.cos(th)
    q = np.sqrt(eps - s ** 2)
    k0 = 2 * np.pi / lam
    ph = np.exp(-2j * k0 * d_m * q)
    tot = 0.0
    for r in ((c - q) / (c + q), (eps * c - q) / (eps * c + q)):
        R = r * (1 - ph) / (1 - r ** 2 * ph)
        tot += abs(R) ** 2
    return 0.5 * tot


def slab_row(mm):
    th = np.linspace(0.0, 89.9, 2000)
    w = np.sin(np.radians(th)) * np.cos(np.radians(th))
    avg = float((np.array([slab_R2(mm / 1000, t) for t in th]) * w).sum() / w.sum())
    return {
        "normal_db": round(10 * math.log10(slab_R2(mm / 1000, 0.0)), 2),
        "angle_avg_db": round(10 * math.log10(avg), 2),
        "deg45_db": round(10 * math.log10(slab_R2(mm / 1000, 45.0)), 2),
    }


slab = {f"{mm:g}mm": slab_row(mm) for mm in (0.5, 0.75, 0.9, 1.43, 1.5, 100.0)}
base_s = slab["100mm"]
slab_delta = {k: {kk.replace("_db", "_delta_db"): round(v[kk] - base_s[kk], 2) for kk in v}
              for k, v in slab.items() if k != "100mm"}

# ── 팔 계산 ──────────────────────────────────────────────────────────────────
BASE = "sionna_p4000000000_r15_n8192_d1"
SH = {
    0.5: "sionna_p4000000000_r15_n8192_shell0.5mm_d1",
    0.75: "sionna_p4000000000_r15_n8192_shell0.75mm_d1",
    1.5: "sionna_p4000000000_r15_n8192_shell1.5mm_d1",
}
COMBO = "sionna_p4000000000_r15_n8192_shell0.75mm_prop0.9mm_d1"
PROPS = "sionna_p4000000000_partsprop_r15_n8192_d1"
DIFFR = "sionna_p4000000000_onlydiffr_r15_n8192"

DKEYS = ["floor_above_tip_db", "ac_power_db", "dc_power_db", "level_db_ledger",
         "comb_contrast_db", "rhythm_share_pct", "above_f_tip_pct", "beat_hz_track"]


def delta(d, b):
    out = {}
    for k in DKEYS:
        if d.get(k) is None or b.get(k) is None:
            out["d_" + k] = None
        else:
            out["d_" + k] = round(d[k] - b[k], 4)
    return out


b30, Eb30 = metrics(BASE, -30.0)
arms30 = {"base_100mm": b30}
waves = {}
for mm, arm in SH.items():
    d, E = metrics(arm, -30.0)
    d["delta_vs_base"] = delta(d, b30)
    d["vs_base_waveform"] = wave_cmp(Eb30, E)
    arms30[f"shell_{mm:g}mm"] = d
dc, Ec = metrics(COMBO, -30.0)
dc["delta_vs_base"] = delta(dc, b30)
dc["vs_base_waveform"] = wave_cmp(Eb30, Ec)
arms30["shell0.75_prop0.9mm"] = dc
dp, _ = metrics(PROPS, -30.0)
arms30["ref_props_only_100mm"] = dp
dd, _ = metrics(DIFFR, -30.0)
arms30["ref_onlydiffr_100mm"] = dd

b0, Eb0 = metrics(BASE, 0.0)
c0, Ec0 = metrics(COMBO, 0.0)
c0["delta_vs_base"] = delta(c0, b0)
c0["vs_base_waveform"] = wave_cmp(Eb0, Ec0)
el0 = {"base_100mm": b0, "shell0.75_prop0.9mm": c0}

# ── 밴드 ────────────────────────────────────────────────────────────────────
g = json.load(open(GRID))
pe = g["per_elevation"]
floor_band = {}
for el, blk in pe.items():
    l2 = blk["layer2_statistics"]
    f12 = l2["div12"]["ac_power_db"] + 10 * math.log10(l2["div12"]["above_f_tip_frac"])
    f24 = l2["div24"]["ac_power_db"] + 10 * math.log10(l2["div24"]["above_f_tip_frac"])
    floor_band[el] = round(f24 - f12, 3)
bands = {
    "note_ko": ("격자 산포 밴드는 grid_convergence_check.json(우리 커널 λ/12↔λ/24)에서, "
                "확산 바닥 밴드는 MATERIAL_CORRECTION §2-4 규약대로 ac_power_db+10log10(above_f_tip_frac) "
                "합성으로 재계산(여기서 재현). PathSolver 시드 밴드는 raybudget_seed_ladder(4e9, el-15·40m) "
                "sd 1.833 dB의 «빌려 온 값» — 시드 복제 팔은 이번 큐에 없었다. "
                "⚠단 이번 비교는 같은 seed=1 짝지은 비교라 표집 요동이 대부분 소거된다(ρ=1.0000이 그 증거)."),
    "floor_above_tip_grid_db": {"per_el": floor_band, "max_abs": max(abs(v) for v in floor_band.values()),
                                "el_minus30": abs(floor_band["-30"])},
    "ac_power_grid_db": 3.861, "dc_power_grid_db": 6.613, "level_grid_db": 6.56,
    "rhythm_grid_pp": 21.819, "above_f_tip_grid_pp": 12.5549, "beat_grid_hz": 0.152,
    "stft_map_corr_grid_floor": {"min_4el": 0.6039, "el_minus30": 0.6825},
    "comb_contrast_band": None,
    "comb_note_ko": "빗살 대비의 격자 밴드는 사전등록에 없다 — 참고 눈금은 백색잡음 ≈ 0 dB(실측 +0.4).",
    "seed_borrowed_db": {"sd": 1.833, "2sd": 3.67, "3sd": 5.5, "tag": "빌려 온 값(el-15·40 m·4e9)"},
}

# ── 채점 ────────────────────────────────────────────────────────────────────
sh75 = arms30["shell_0.75mm"]
combo = arms30["shell0.75_prop0.9mm"]
scoring = {
    "H1_주판정_확산바닥": {
        "prereg_ko": "100→0.75 mm 셸에서 빗각 확산 바닥 −10~−18 dB, 밴드(9.30 dB) 밖일 것",
        "measured_shell_only_delta_db": sh75["delta_vs_base"]["d_floor_above_tip_db"],
        "verdict": "판정 불가(사전등록 문면) + 귀속 정정(사후 판독)",
        "verdict_ko": ("사전등록 문면으로는 Δ바닥 −0.002 dB 로 밴드(9.30 dB) 안 — 판정 불가. "
                       "그러나 같은 seed 짝지은 비교에서 AC 파형 ρ=1.0000·ΔAC +0.002 dB 라 이것은 "
                       "«못 잰 것»이 아니라 «셸 손잡이가 AC 에 배선 자체가 없음»(구조적 0)이다. "
                       "el −30 의 AC 는 프롭이 사실상 전부다(props-only AC −135.47 ≈ 전체 −135.66). "
                       "H1 이 예측한 −10~−18 dB 창은 **프롭 손잡이**에서 실현됐다 — "
                       "프롭 0.9 mm: 바닥 −12.56 dB·AC −16.99 dB(밴드 9.30·시드 3.7 밖, 유의). "
                       "즉 H1 의 물리(박막 정정이 빗각 바닥을 두 자릿수 dB 어둡게 한다)는 참, "
                       "귀속(셸)은 거짓 — 바닥의 재질은 프롭 플라스틱이다."),
    },
    "H2_단조성": {
        "prereg_ko": "두께 순으로 바닥이 단조(0.75<1.5<3.0 예정이었으나 실제 축은 0.5/0.75/1.5)",
        "verdict": "바닥 축 채점 불가 · DC 축 통과",
        "verdict_ko": ("바닥(AC) 축은 세 점 전부 0.00 dB 라 순서 자체가 없다(위 구조적 0). "
                       "DC 축에서는 0.5(−7.13) < 0.75(−6.24) < 1.5(−4.14) < 100(0) 로 안 뒤집히고, "
                       "단일 셸 몫 s 로 슬래브 모형과 정합(s≈0.74~0.83, 잔차 ≤0.9 dB) — "
                       "손잡이가 셸 플라스틱을 옳게 물고 있다는 배선 증거."),
        "dc_delta_db": {"shell_0.5mm": -7.132, "shell_0.75mm": -6.24, "shell_1.5mm": -4.144},
        "shell_share_of_dc_fit": "0.74~0.83 (각도평균 슬래브 기준 3점 역산)",
    },
    "H3_배선대조군_el0": {
        "prereg_ko": "el 0 총 레벨이 시드 밴드(빌려 온 3.7 dB) 안 — 금속 거울이라 안 움직여야",
        "measured_delta_db": {"level": c0["delta_vs_base"]["d_level_db_ledger"],
                              "dc": c0["delta_vs_base"]["d_dc_power_db"],
                              "ac": c0["delta_vs_base"]["d_ac_power_db"]},
        "verdict": "통과",
        "verdict_ko": ("셸 0.75+프롭 0.9 결합판인데도 el 0 은 레벨·DC·AC 전부 0.000 dB — "
                       "손잡이가 의도 밖 재질(금속)을 안 잡았다. 덤으로 §2-4 의 "
                       "«방아쇠는 프롭·크기는 금속» 이 실측 확증됐다 — 프롭을 −17 dB 어둡게 해도 "
                       "el 0 AC(추첨 잡음)가 1/1000 dB 도 안 움직였다."),
    },
    "H4_표적축_불변": {
        "prereg_ko": "리듬 몫·f_tip 밖 몫은 밴드 안, STFT 맵 상관은 격자 바닥 위",
        "measured": {
            "rhythm_pp_combo": combo["delta_vs_base"]["d_rhythm_share_pct"],
            "above_f_tip_pp_combo": combo["delta_vs_base"]["d_above_f_tip_pct"],
            "stft_map_corr_combo": combo["vs_base_waveform"]["stft_db_map_corr_dc_removed"],
            "beat_hz_delta_combo": combo["delta_vs_base"]["d_beat_hz_track"],
        },
        "verdict": "통과",
        "verdict_ko": ("결합판 기준 리듬 −5.21 %p(밴드 21.8 안)·f_tip 밖 +1.88 %p(밴드 12.6 안)·"
                       "맵 상관 0.8923(바닥 0.6825 위)·박자 Δ −0.04 Hz(밴드 0.152 안). "
                       "박자 구조는 재질 정정에 강건 — 무늬·분류 서사는 산다. "
                       "빗살 대비는 −6.98 dB 내려가되(51.99→45.01) 백색 0 dB 대비 +45 dB 로 건재. "
                       "⚠빗살 대비는 사전등록 밴드가 없어 참고 판정."),
    },
    "H5_투과_반대항": {
        "prereg_ko": "굴절 켠 팔은 셸 안쪽 금속이 밝아져(왕복 +6.2 dB) 덜 내려가야",
        "verdict": "미착지",
        "verdict_ko": ("굴절만×셸두께 칸이 이번 큐 착지 목록에 없다(굴절만 팔은 전부 100 mm). "
                       "투과 반대항은 여전히 슬래브 수학 추론이다 — 굴절 팔 레벨 인용에 100 mm 꼬리표 유지."),
    },
}

attribution = {
    "ko": ("el −30 물리끔 d1 에코의 해부(이번 실측): AC(움직이는 부분·확산 바닥·빗살)는 프롭 플라스틱이 "
           "사실상 전부(셸 손잡이 0.00 dB·props-only ≈ 전체), DC(정지 성분)는 셸 플라스틱이 약 3/4~4/5 "
           "(세 두께 점 역산 s≈0.74~0.83), 나머지는 카본·프롭 정지항. "
           "그래서 «잣대 주의»가 다시 맞았다 — 레벨(DC 포함)로 보면 셸이 −2.3 dB 움직인 것처럼 보이지만 "
           "DC 를 걷어내면 셸의 표적 축 기여는 0 이다."),
    "prop_0p9mm_measured_vs_slab": {
        "ac_delta_db": combo["delta_vs_base"]["d_ac_power_db"],
        "slab_pred_delta_db": slab_delta["0.9mm"],
        "note_ko": ("실측 AC −16.99 dB 는 45° 입사 예측(−16.65)과 0.34 dB 차 — 빗각 기하에서 "
                    "날면 입사각이 45° 부근에 몰린다는 읽기와 정합. 각도평균 예측(−11.34)보다 가파르다."),
    },
    "caution_0p9_not_canonical": ("⚠0.9 mm 는 D2 정본(matrice4e 시위평균 1.43 mm)이 아니라 민감도 점이다. "
                                  "45° 열 스케일로 정본 1.43 mm 의 예상 AC 이동은 약 −13 dB(추정·미실측)."),
}

headlines = {
    "굴절만_거리_생존": ("유지(방향은 강화) — 굴절만 팔은 전부 100 mm 에서 돌았고, 정정(셸 0.75 mm)은 "
                    "왕복 투과를 −6.35→−0.13 dB 로 밝게 하므로 굴절 채널 레벨은 올라가는 쪽. "
                    "거리 기울기는 재질 곱셈 이득과 무관해 «완만 감쇄» 자체는 안 흔들린다. "
                    "단 H5 미착지라 이 방향 진술은 슬래브 추론 꼬리표를 단다."),
    "회절_덮음": ("유지(브래킷) — 이 원장 AC 기준 onlydiffr(−124.74) 이 물리끔 바닥(−135.66)보다 +10.9 dB 위. "
              "프롭 정정으로 바닥이 −17.0 dB 더 내려가고 회절 자신의 두께 민감도는 0~−18 dB(쐐기면) 브래킷이라 "
              "정정 뒤 간격은 +10.9~+27.9 dB — 어느 끝에서도 덮음은 유지되고 넓어지는 쪽이 개연. "
              "⚠덱 25 장의 «+36 dB» 는 switch_factorial 레벨 기준 수치라 별도 원장 — 여기서 재채점 안 함."),
    "el0_금속_추첨": ("실측 확증 — 프롭 −17 dB 에도 el 0 AC 0.000 dB. §2-4 의 «방아쇠는 프롭·크기는 금속» 이 "
                  "손잡이 실험으로 닫혔다."),
    "100mm_때문에_12~13dB_밝게": ("실측 확증 — §6 게이트 2 의 추정(12~13 dB)이 바닥 실측 −12.56 dB 로 적중. "
                             "이제 추정이 아니라 측정이다(단 0.9 mm 프롭 점 기준)."),
    "drowned_blades_덱24": ("강화 — 프롭 에코가 −17 dB 더 어두워지므로 금속 거울 아래 익사 간격은 더 벌어진다. "
                        "덱 문구의 값 정정(§4-3)은 그대로 필요."),
    "절대_판독거리_R50": ("보류 유지(D4) — 이번 실측이 프롭 축의 크기를 처음으로 쟀다: PathSolver AC −16.99 dB(0.9 mm). "
                     "커널 프롭 정정(−34 % R50 추정)의 방향을 독립 엔진에서 뒷받침. 절대 거리 주장은 게이트 전까지 보류."),
    "무늬_분류_서사": ("유지 — H4 통과. 빗살·리듬·박자 구조는 재질 정정에 강건. 읽히는 «거리»의 절대값만 게이트 대상."),
    "PS다끔_480m_인용보류": "무관 — 이번 판정과 독립(표집 희소성 문제).",
}

out = {
    "_meta": {
        "generator": "scratchpad/build_material_verdict.py (재질 정정 판정자 라운드)",
        "date_kst": "2026-08-16",
        "question_ko": "셸 두께(0.5/0.75/1.5 mm)·프롭 0.9 mm 팔이 기본(Sionna 100 mm)과 어디서 얼마나 다른가",
        "inputs": [LEDGER, NPZ, GRID, "outputs/raybudget_seed_ladder.json(밴드 인용)"],
        "conventions_ko": ("모든 비교는 DC 제거 후(ac_power_db·확산 바닥·빗살 대비·리듬). "
                           "확산 바닥 = ac_power_db + 10log10(above_f_tip_frac). "
                           "빗살 대비 = build_md_atlas.comb_contrast_db(2·f_flash~f_tip, 정수배÷중간자리). "
                           "팔: PathSolver 4e9·물리끔·d1·15 m·matrice4e·seed 1(짝지은 비교). "
                           "우리 커널은 두께 개념이 없어 이 축 구조적 N/A(D3 동결)."),
        "prereg_ref": "docs/MATERIAL_CORRECTION.md §2-4 (실제 축이 계획과 다름: 0.5/0.75/1.5, 프롭 0.9 — §판정 참조)",
    },
    "slab_predictions_3p5ghz": {"abs": slab, "delta_vs_100mm": slab_delta,
                                "note_ko": "ITU-R P.2040 단층 슬래브, plastic εr 2.7·σ 0.02, 편파 전력평균 — §9 재현판과 동일 규약"},
    "el_minus30": arms30,
    "el_0_wiring_control": el0,
    "bands": bands,
    "prereg_scoring": scoring,
    "attribution": attribution,
    "headline_impacts_ko": headlines,
    "verdict_headline_ko": (
        "① 셸 두께 손잡이는 el −30 에서 **DC 만** 움직인다(0.75 mm: DC −6.24 dB·AC +0.00 dB·바닥 −0.00 dB) — "
        "표적 축(확산 바닥·빗살·리듬)은 셸 정정에 완전 불변(ρ=1.0000). "
        "② 실측 0.75 mm 판 vs 기본: 표적 축 차이는 밴드 안(사전등록 문면 «판정 불가»)이나, 짝지은 비교의 "
        "구조적 0 이라 «영향 없음» 으로 읽는 것이 정직. DC −6.24 dB 도 격자 DC 밴드(6.61) 안 — 단독으로는 "
        "판정 불가, 세 점 단조+슬래브 정합(s≈0.74~0.83)이 방향만 지지. "
        "③ 진짜 손잡이는 프롭이다 — 0.9 mm 에서 AC −16.99 dB·바닥 −12.56 dB·빗살 −6.98 dB(밴드 밖·유의), "
        "45° 슬래브 예측과 0.34 dB 차. 기존 헤드라인 중 뒤집히는 것은 없고(굴절만 생존·회절 덮음 유지), "
        "«12~13 dB 밝게 깔림»·«el0 금속 추첨» 두 주장은 실측으로 확증됐다. "
        "④ H5(투과 반대항)·el −60 두께·시드 복제·정본 1.43 mm 프롭 점은 미착지로 남는다."),
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved", OUT)
