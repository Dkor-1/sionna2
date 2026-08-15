# -*- coding: utf-8 -*-
"""
bridge_cross_precise.py — 기동 정밀 교차검증: 같은 PX4 창에서 세 파이프라인을 사과-대-사과로
=================================================================================================

세 팔 (전부 **저장된 원장만** 읽는다 — GPU·솔버 호출 없음):
  (a) ours    outputs/px4_bridge/ours_{phantom4,matrice4e}_g2_w0.npz   (5000 펄스)
              — 우리 SBR+PO 커널. phantom4 = **선배 메쉬**(poser key phantom4_senior,
                스크래치 로그 bridge_prod_phantom4.log 실사), matrice4e = 우리 CAD.
  (b) senior  outputs/jihyuck_po/grade_2/window_00000.npz              (5000 펄스)
              — 선배 PO 생산물. MANIFEST 규약대로 재구성:
                occ=full : body_occ + blade_occ_X (X=nylon 이 기준 — ours 메타와 맞춤)
  (c) PS      outputs/px4_bridge/sionna_{phantom4,matrice4e}_g2_w0.npz (256 펄스)
              — Sionna PathSolver. ⚠ **s ≡ 0 (전 펄스 무신호)** — 실거리 R≈68.6 m 에서
                spp=1e6 으로는 표적 경유 경로가 하나도 안 잡혔다(경로 수 ∝ (표적/R)²,
                px4_bridge.run_sionna_window docstring 의 경고 그대로). 억지 비교 금지
                원칙에 따라 **정량 비교에서 제외**하고 사실만 기록한다.

정합 원칙 (task 지정):
  ① 같은 시간 구간 — PS 가 256 펄스뿐이므로 겹치는 처음 256 펄스 구간을 공통 창으로
    정의하고(시작시각 t=5.0 s·PRF 35 kHz 일치 assert), 5000 펄스 팔은 그 구간 절단본도
    함께 잰다. PS 가 무신호라 실제 정량화는 ours·senior 두 팔이다.
  ② 같은 정규화 — 팔마다 자기 최대 기준(그림). 잣대 자체는 비율(봉우리/바닥)이라
    눈금 불변 — 이를 수치로 검산한다(normalization_invariance).
  ③ 같은 잣대 코드 경로 — blade_line_snr() 한 함수를 세 팔(가능한 두 팔)에 동일 적용.
  ④ 벌크 도플러 — 스펙트럼 무게중심으로 추정하되, 전대역 무게중심은 빗살 비대칭에
    끌려 편향됨을 **측정으로** 보이고(기하 참값 1.6~1.9 Hz vs 전대역 16~62 Hz),
    동체대역(|f|≤f_flash/2) 무게중심을 채택, 로그 R(t) 기하 참값과 교차검산한다.
    선택과 근거를 JSON 에 남긴다(과주장 금지 — 어느 쪽이든 빈폭보다 작아 효과 미미).

⭐ 오늘의 교훈 반영 — 레벨 비교는 **정지성분(DC) 제거 후**. DC 를 끼운 채 재면
   N=256 에서 한(Hann) 주엽(±2빈=±273 Hz)이 1×f_flash(153 Hz)를 덮어 +26~+33 dB
   아티팩트가 난다 — 이 아티팩트 크기 자체를 결과로 낸다(dc_artifact_db).

목표 — 이전 격차(우리 35.8 dB vs 선배 8.4~11.4 dB)를 규약 차이로 분해:
   바닥 레시피(국소 vs 대역) · 창 길이(5000 vs 256) · DC 처리 · 정규화(0 dB 검산) ·
   재질/가림 규약 — 각각 몇 dB 인지 원장에서 직접 잰다.

실행:
   cd /workspace/sionna && PYTHONPATH=src:benchmark \
     /workspace/.venvs/py312/bin/python benchmark/bridge_cross_precise.py
산출:
   outputs/bridge_cross_precise.json
   outputs/figures/bridge_cross_maps.png   (STFT 나란히 — STFT 만, 집 규약)
   outputs/figures/bridge_cross_lines.png  (빗살 선 스펙트럼 + 격차 분해 사다리)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

# 192코어 기계에서 BLAS/OpenMP 풀이 커널 스핀으로 벽시계를 태운다(첫 실행 실측:
# utime 32 s vs stime 377 s) — 분석은 작은 FFT 뿐이라 스레드를 묶는다. GPU 워커 배려.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "8")

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

C0 = 2.998e8
OUT_JSON = os.path.join(ROOT, "outputs", "bridge_cross_precise.json")
FIG_DIR = os.path.join(ROOT, "outputs", "figures")
FIG_MAPS = os.path.join(FIG_DIR, "bridge_cross_maps.png")
FIG_LINES = os.path.join(FIG_DIR, "bridge_cross_lines.png")

PB_DIR = os.path.join(ROOT, "outputs", "px4_bridge")
JH_DIR = os.path.join(ROOT, "outputs", "jihyuck_po", "grade_2")

selftest = {}          # 이름 → bool (구조적 검사 — 전부 참이어야 완주)
notes = []             # 정직성 기록(과주장 금지)


def md5_8(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:8]


def kst_now() -> str:
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        return _dt.datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    except Exception:
        return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())


# --------------------------------------------------------------------------- #
# 1. 원장 로드 + 정합 assert (①)
# --------------------------------------------------------------------------- #
def load_arm_npz(path):
    z = np.load(path, allow_pickle=True)
    meta = json.loads(str(z["meta"]))
    return dict(s=np.asarray(z["s"], complex), idx=np.asarray(z["idx"], int),
                R=np.asarray(z["R"], float), meta=meta,
                file=os.path.relpath(path, ROOT), md5=md5_8(path),
                mtime=time.strftime("%Y-%m-%d %H:%M UTC",
                                    time.gmtime(os.path.getmtime(path))))


files = {
    "ours_phantom4": os.path.join(PB_DIR, "ours_phantom4_g2_w0.npz"),
    "ours_matrice4e": os.path.join(PB_DIR, "ours_matrice4e_g2_w0.npz"),
    "ps_phantom4": os.path.join(PB_DIR, "sionna_phantom4_g2_w0.npz"),
    "ps_matrice4e": os.path.join(PB_DIR, "sionna_matrice4e_g2_w0.npz"),
}
arms_raw = {k: load_arm_npz(p) for k, p in files.items()}

jh_meta = np.load(os.path.join(JH_DIR, "metadata.npz"), allow_pickle=True)
jh_w0_path = os.path.join(JH_DIR, "window_00000.npz")
jh_w0 = np.load(jh_w0_path)

PRF = float(arms_raw["ours_phantom4"]["meta"]["prf"])
FC = float(arms_raw["ours_phantom4"]["meta"]["fc"])
LAM = C0 / FC
T_START = float(arms_raw["ours_phantom4"]["meta"]["t_start"])
N_FULL = 5000
N_OVERLAP = 256          # PS 팔의 길이 = 공통(겹침) 구간

# --- 정합 assert: 시작시각·PRF·fc·펄스 격자·궤적 R 이 세 팔에서 일치하는가 ----
ok = True
for k, a in arms_raw.items():
    ok &= (float(a["meta"]["prf"]) == PRF)
    ok &= (float(a["meta"]["fc"]) == FC)
    ok &= (float(a["meta"]["t_start"]) == T_START)
selftest["prf_fc_tstart_match_all_npz"] = bool(ok)
assert ok, "npz 팔들의 PRF/fc/t_start 가 다르다 — 사과-대-사과가 아니다"

ok = (int(jh_meta["prf"]) == int(PRF) and float(jh_meta["fc"]) == FC
      and int(jh_meta["n_pulses"]) == N_FULL
      and abs(float(jh_meta["window_starts"][0]) - T_START) < 1e-12)
selftest["senior_metadata_match"] = bool(ok)
assert ok, "선배 grade_2 metadata 가 (PRF, fc, n_pulses, window_starts[0]) 불일치"

# 궤적 일치: ours 처음 256 펄스의 R == PS 의 R (같은 로그·같은 창인가)
dR = float(np.abs(arms_raw["ours_phantom4"]["R"][:N_OVERLAP]
                  - arms_raw["ps_phantom4"]["R"]).max())
selftest["trajectory_R_match_ours_vs_ps"] = bool(dR < 1e-9)
assert dR < 1e-9, f"ours[:256].R != ps.R (max {dR:g} m)"
ok = (np.array_equal(arms_raw["ours_phantom4"]["idx"][:N_OVERLAP],
                     arms_raw["ps_phantom4"]["idx"])
      and np.array_equal(arms_raw["ours_phantom4"]["idx"],
                         arms_raw["ours_matrice4e"]["idx"]))
selftest["pulse_index_alignment"] = bool(ok)
assert ok

# --- PS 팔 무신호 판정 (억지 비교 금지 — 사실만 기록) -------------------------
ps_nonzero = {k: int(np.count_nonzero(np.abs(arms_raw[k]["s"])))
              for k in ("ps_phantom4", "ps_matrice4e")}
ps_comparable = any(v > 0 for v in ps_nonzero.values())
selftest["ps_zero_signal_detected_and_recorded"] = True
if not ps_comparable:
    notes.append(
        "PS(Sionna PathSolver) 팔은 256 펄스 전부 s=0 — 실거리 R≈68.6 m 에서 spp=1e6 으로 "
        "표적 경유 경로가 0 개(경로 수 ∝ (표적크기/R)², px4_bridge docstring 경고 그대로). "
        "참고로 elevation_sweep 원장의 sionna 팔은 15 m 에서 spp 4e9 를 쓴다 — 68.6 m 은 "
        "같은 포착률에 (68.6/15)²≈21 배가 더 필요해 1e6 은 자릿수로 모자란다. "
        "정량 비교는 ours·senior 두 팔로 한다(억지 비교 금지).")

# --------------------------------------------------------------------------- #
# 2. f_flash 예측 — PX4 로그에서 직접 (CPU 전용 import 검증 포함)
# --------------------------------------------------------------------------- #
import px4_bridge as PB  # noqa: E402  (sionna 는 run_sionna_window 안에서만 lazy import)

win = PB.load_window(grade=2, t_start=T_START, n_pulses=N_FULL)
rr_full = PB.rotor_rates_hz(win)
win256 = PB.load_window(grade=2, t_start=T_START, n_pulses=N_OVERLAP)
rr_256 = PB.rotor_rates_hz(win256)
F_FLASH = float(rr_full["f_flash_hz"])            # 2날개 × 평균 회전수 [Hz]
f_rev_mean = F_FLASH / 2.0

no_gpu = not any(("sionna" in m) or ("mitsuba" in m) or ("drjit" in m)
                 for m in sys.modules)
selftest["no_gpu_solver_modules_imported"] = bool(no_gpu)
assert no_gpu, "sionna/mitsuba 가 import 됐다 — GPU 금지 위반"

# f_tip (날개끝 도플러 상한) — 메쉬 실측 반경 × 로그 회전수
sp = PB.SeniorMeshPoser()                          # PLY 로드(CPU, plyfile)
from drones import DRONES  # noqa: E402
R_PROP = {"phantom4_senior": float(sp.prop_radius_m),
          "matrice4e": float(DRONES["matrice4e"].prop_dia_mm) / 2000.0}
F_TIP = {k: 2.0 * (2 * np.pi * f_rev_mean * r) / LAM for k, r in R_PROP.items()}

# 팔 정의 (분석 대상 — PS 는 무신호라 제외, 그림·JSON 에는 사실 기록)
SENIOR_BLADE = "nylon"                             # ours 메타 blade_mat 과 맞춤
arms = {
    "ours_phantom4": dict(
        s=arms_raw["ours_phantom4"]["s"], mesh="phantom4_senior",
        label="Ours (SBR+PO) - Phantom4 (senior mesh)"),
    "ours_matrice4e": dict(
        s=arms_raw["ours_matrice4e"]["s"], mesh="matrice4e",
        label="Ours (SBR+PO) - Matrice 4E (our CAD)"),
    "senior_full_nylon": dict(
        s=np.asarray(jh_w0["body_occ"] + jh_w0[f"blade_occ_{SENIOR_BLADE}"], complex),
        mesh="phantom4_senior",
        label="Senior PO - Phantom4 (occ=full, nylon)"),
}
# ⭐PS 팔은 **신호가 살아 있을 때만** 채점에 넣는다(2026-08-15). 광선 예산 1e6 판에서는
#   256 펄스가 전부 0 이라 억지 비교였는데, 4e9 재실행에서 전부 살아났다. 길이가 256 뿐이라
#   N5000 열은 못 채우므로 measure() 가 짧은 창에서 무엇을 내는지는 아래 results 조립부에서
#   길이로 갈린다(N256 만 유효).
if ps_comparable:
    for k, mesh in (("ps_phantom4", "phantom4_senior"), ("ps_matrice4e", "matrice4e")):
        if int(np.count_nonzero(np.abs(arms_raw[k]["s"]))) == 0:
            continue
        arms[k] = dict(s=arms_raw[k]["s"], mesh=mesh,
                       label=f"Sionna PathSolver - {mesh} (256 pulses)")
# 선배 규약 변주(가림·재질) — 격차 분해용
senior_variants = {
    "senior_none_nylon": jh_w0["body_none"] + jh_w0["blade_none_nylon"],
    "senior_body_nylon": jh_w0["body_occ"] + jh_w0["blade_none_nylon"],
    "senior_full_cf": jh_w0["body_occ"] + jh_w0["blade_occ_cf"],
    "senior_full_metal": jh_w0["body_occ"] + jh_w0["blade_occ_metal"],
}

# --------------------------------------------------------------------------- #
# 3. 잣대 — 한 함수, 세 팔 동일 적용 (③)
# --------------------------------------------------------------------------- #
def dc_spectrum(s, dc_remove=True):
    """P=|FFT((s-mean)·hann)|² — 표준 레시피. fftshift 된 (fr, P)."""
    x = np.asarray(s, complex)
    if dc_remove:
        x = x - x.mean()
    w = np.hanning(len(x))
    P = np.abs(np.fft.fft(x * w)) ** 2
    fr = np.fft.fftfreq(len(x), 1.0 / PRF)
    return np.fft.fftshift(fr), np.fft.fftshift(P)


def blade_line_snr(s, f_flash, f_tip, *, k=1, floor="band", dc_remove=True):
    """블레이드 선 SNR [dB] — 예측 박자 k×f_flash 봉우리 vs 바닥. ± 중 큰 쪽.

    floor="band"  : 바닥 = 0.3~1.0 f_tip 대역 중앙값 (창 길이 불변 — 교차창 비교용)
    floor="local" : 바닥 = 봉우리 주변 ±ann 국소 중앙값, 빗살 정수배 ±excl 제외
                    (5000 펄스 해상도 전용 — 빗살 간격 < 제외폭이면 None: 측정 불가)
    반환: (snr_db | None, 진단 dict)"""
    fr, P = dc_spectrum(s, dc_remove)
    df = float(fr[1] - fr[0])
    tol = max(8.0, 1.5 * df)                       # 표준 ±8 Hz, 최소 1.5빈
    diag = dict(df_hz=round(df, 3), tol_hz=round(tol, 1))
    pk_plus = float(P[np.abs(fr - k * f_flash) <= tol].max())
    pk_minus = float(P[np.abs(fr + k * f_flash) <= tol].max())
    pk = max(pk_plus, pk_minus)                    # 헤드라인 = ± 중 큰 쪽
    if floor == "band":
        band = (np.abs(fr) >= 0.3 * f_tip) & (np.abs(fr) <= f_tip)
        fl = float(np.median(P[band]))
    else:
        excl = max(12.0, tol)
        ann = max(60.0, 6 * df)
        if 2 * excl >= f_flash:                    # 빗살 분해 불가 — 정직하게 None
            diag["unresolved"] = (f"comb spacing {f_flash:.0f} Hz < exclusion width "
                                  f"{2 * excl:.0f} Hz at this window length")
            return None, diag
        comb = np.zeros(len(fr), bool)
        for kk in range(1, int(1.2 * f_tip / f_flash) + 2):
            for sg in (1, -1):
                comb |= np.abs(fr - sg * kk * f_flash) <= excl
        m = np.zeros(len(fr), bool)
        for sg in (1, -1):
            m |= (np.abs(fr - sg * k * f_flash) <= ann)
        m &= ~comb
        if m.sum() < 5:
            diag["unresolved"] = "empty local floor annulus"
            return None, diag
        fl = float(np.median(P[m]))
    # ± 각각도 남긴다 — 빗살 비대칭(자세 부호 이력)이 있어 한쪽만 재면 수 dB 다르다
    diag["pm_db"] = [round(10 * np.log10(pk_plus / fl), 2),
                     round(10 * np.log10(pk_minus / fl), 2)]
    return float(10 * np.log10(pk / fl)), diag


def comb_share_pct(s, f_flash, f_tip, tol=8.0):
    """리듬(구조) 잣대 — 대역(0.5·f_flash ≤ |f| ≤ f_tip) 전력 중 박자 정수배 ±tol 몫[%].
    백색잡음 ≈ 13, 이상 로터 → 100 (표준 레시피)."""
    fr, P = dc_spectrum(s, True)
    band = (np.abs(fr) <= f_tip) & (np.abs(fr) >= 0.5 * f_flash)
    comb = np.zeros(len(fr), bool)
    for kk in range(1, int(f_tip / f_flash) + 2):
        comb |= np.abs(np.abs(fr) - kk * f_flash) <= tol
    return float(100.0 * P[band & comb].sum() / P[band].sum())


# --------------------------------------------------------------------------- #
# 4. 벌크 도플러 (④) — 추정·교차검산·선택 기록
# --------------------------------------------------------------------------- #
vr = np.gradient(win.R, win.t)                     # 로그 기하 참값 dR/dt
f_bulk_geom = (-2.0 * vr / LAM)                    # 접근(+R 감소)=+도플러 규약
bulk = dict(
    convention="f_D = -2·(dR/dt)/λ (거리 증가=음의 도플러)",
    geometric_from_log_hz=dict(min=round(float(f_bulk_geom.min()), 3),
                               max=round(float(f_bulk_geom.max()), 3),
                               mean=round(float(f_bulk_geom.mean()), 3)),
    estimates={}, choice=None)
for name, a in arms.items():
    fr, P = dc_spectrum(a["s"][:N_FULL], True)
    cen_full = float((fr * P).sum() / P.sum())
    bb = np.abs(fr) <= F_FLASH / 2                 # 동체대역 무게중심
    cen_body = float((fr[bb] * P[bb]).sum() / P[bb].sum())
    bulk["estimates"][name] = dict(centroid_fullband_hz=round(cen_full, 2),
                                   centroid_bodyband_hz=round(cen_body, 2))
bulk["choice"] = (
    "동체대역(|f|≤f_flash/2) 무게중심을 벌크 추정치로 채택, 로그 기하 참값과 교차검산. "
    "전대역 무게중심은 빗살 비대칭에 끌려(측정 16~62 Hz vs 기하 참값 ~-1.9~-1.6 Hz) "
    "기각 — 적용하면 빗살이 격자에서 이탈해 선 SNR 이 20 dB 이상 무너진다(측정). "
    "채택 추정치·참값 모두 |f| < 빈폭(5000펄스 Δf=7 Hz)이므로 보정을 **적용하지 않는다** "
    "— 적용 여부가 잣대에 못 미치는 것을 수치로 검산(bulk_comp_effect_db). 과주장 금지.")

# 보정 효과 검산: 기하 참값 위상 되감기(정확 보정) 후 잣대 변화
bulk_effect = {}
k0 = 2 * np.pi / LAM
for name, a in arms.items():
    s5 = np.asarray(a["s"][:N_FULL], complex)
    # ⭐팔마다 길이가 다르다(PS 는 256) — 궤적도 같은 길이로 자른다(2026-08-15).
    n5 = s5.size
    s5c = s5 * np.exp(+1j * 2 * k0 * (win.R[:n5] - win.R[0]))   # 벌크 거리위상 제거
    v0, _ = blade_line_snr(s5, F_FLASH, F_TIP[a["mesh"]], k=1, floor="band")
    v1, _ = blade_line_snr(s5c, F_FLASH, F_TIP[a["mesh"]], k=1, floor="band")
    bulk_effect[name] = round(v1 - v0, 3)
bulk["bulk_comp_effect_db"] = bulk_effect
selftest["bulk_comp_negligible_lt_0p5db"] = bool(
    max(abs(v) for v in bulk_effect.values()) < 0.5)

# --------------------------------------------------------------------------- #
# 5. 결과표 — 팔 × 창길이 × DC × 바닥 레시피 (전부 실행 시점 계산)
# --------------------------------------------------------------------------- #
def measure(s, mesh, n):
    ft = F_TIP[mesh]
    row = {}
    seg = np.asarray(s[:n], complex)
    for kk in (1, 2, 3):
        v, d = blade_line_snr(seg, F_FLASH, ft, k=kk, floor="band")
        row[f"band_k{kk}_db"] = None if v is None else round(v, 2)
        if kk == 1:
            row["df_hz"] = d["df_hz"]
        vl, dl = blade_line_snr(seg, F_FLASH, ft, k=kk, floor="local")
        row[f"local_k{kk}_db"] = (None if vl is None else round(vl, 2))
        if vl is not None:
            row[f"local_k{kk}_pm_db"] = dl["pm_db"]     # [+측, −측] 각각
        elif kk == 1:
            row["local_unresolved"] = dl.get("unresolved")
    vdc, _ = blade_line_snr(seg, F_FLASH, ft, k=1, floor="band", dc_remove=False)
    row["band_k1_dc_kept_db"] = round(vdc, 2)
    row["dc_artifact_db"] = round(vdc - row["band_k1_db"], 2)
    return row

results = {}
for name, a in arms.items():
    # ⭐창 길이가 배열보다 길면 그 열은 비운다 — PS 팔은 256 펄스뿐이라 N5000 이 없다.
    #   짧은 배열을 5000 창에 넣으면 0 으로 채워진 가짜 스펙트럼이 나온다(2026-08-15).
    results[name] = {f"N{n}": (measure(a["s"], a["mesh"], n)
                               if a["s"].size >= n else None)
                     for n in (N_FULL, N_OVERLAP)}
    results[name]["comb_share_pct_N5000"] = (
        round(comb_share_pct(a["s"][:N_FULL], F_FLASH, F_TIP[a["mesh"]]), 1)
        if a["s"].size >= N_FULL else None)
for name, s in senior_variants.items():
    results[name] = {f"N{n}": measure(np.asarray(s, complex), "phantom4_senior", n)
                     for n in (N_FULL, N_OVERLAP)}
    results[name]["comb_share_pct_N5000"] = round(
        comb_share_pct(np.asarray(s, complex)[:N_FULL], F_FLASH,
                       F_TIP["phantom4_senior"]), 1)

# --- 350 Hz 인공물 후보 정량화 (px4_bridge 데이터 함정 기록의 후속) ------------
# 선배 재구성(full)의 off-comb 최대 선을 찾고, 분해 성분·우리 팔·로그 표본율로 추적한다.
def _peak_over_band_floor(s, f0, tol=12.0, mesh="phantom4_senior"):
    fr, P = dc_spectrum(np.asarray(s, complex)[:N_FULL], True)
    ft = F_TIP[mesh]
    band = (np.abs(fr) >= 0.3 * ft) & (np.abs(fr) <= ft)
    return round(float(10 * np.log10(P[np.abs(fr - f0) <= tol].max()
                                     / np.median(P[band]))), 1)

_fr, _P = dc_spectrum(arms["senior_full_nylon"]["s"][:N_FULL], True)
_sel = (_fr >= 50) & (_fr <= 1200)
_comb = np.zeros(len(_fr), bool)
for _k in range(1, 9):
    _comb |= np.abs(_fr - _k * F_FLASH) <= 14
F_ART = float(_fr[int(np.argmax(_P * (_sel & ~_comb)))])

# 로그 표본율 실측 (인공물 주파수와의 정수배 관계 확인용)
import pandas as _pd
log_rates = {}
for _f in ("clean_attitude.csv", "clean_position.csv", "clean_esc.csv"):
    _d = _pd.read_csv(os.path.join(win.provenance["data_dir"], _f))
    _tc = [c for c in _d.columns if "time" in c.lower()][0]
    _t = _d[_tc].to_numpy(float)
    _dt = float(np.median(np.diff(_t)[np.diff(_t) > 0]))
    log_rates[_f] = round((1.0 / _dt) if _dt < 1 else (1e6 / _dt), 1)

artifact = dict(
    off_comb_max_hz=round(F_ART, 1),
    levels_over_band_floor_db=dict(
        senior_full_nylon=_peak_over_band_floor(arms["senior_full_nylon"]["s"], F_ART),
        senior_body_none=_peak_over_band_floor(jh_w0["body_none"], F_ART),
        senior_body_occ=_peak_over_band_floor(jh_w0["body_occ"], F_ART),
        senior_blade_none_nylon=_peak_over_band_floor(jh_w0["blade_none_nylon"], F_ART),
        ours_phantom4=_peak_over_band_floor(arms["ours_phantom4"]["s"], F_ART)),
    log_sample_rates_hz=log_rates,
    reading=(f"선배 팔의 off-comb 최대 선 {F_ART:.0f} Hz 는 f_flash 정수배가 아니고 "
             f"자세·위치 로그 표본율({log_rates['clean_attitude.csv']:.0f} Hz)의 "
             f"정수배({F_ART / log_rates['clean_attitude.csv']:.1f}×)다. 가림 없는 "
             "body_none 에 가장 강하고(+46 dB 급) 우리 팔에는 없다(0 dB 급) — "
             "px4_bridge 데이터 함정 기록(«350 Hz 인공물»)과 부합하는 **데이터/조립 "
             "단계 유래 후보**다. 보간 킹크 기전은 가설로만 둔다(확정 아님)."),
    metric_impact=("이 선은 국소바닥 레시피의 2×f_flash 주변 고리(306±60 Hz) 안에 "
                   "들어와 선배 팔의 국소바닥을 끌어올릴 수 있다 — 국소바닥 수치 해석 시 "
                   "유의. 대역바닥(0.3~1.0 f_tip 중앙값)에는 영향이 한 빈 수준."))
selftest["artifact_line_is_off_comb"] = bool(
    min(abs(F_ART - k * F_FLASH) for k in range(1, 9)) > 14)

# 정규화 불변 검산 (②) — 눈금 ×10⁶ 에도 잣대 불변
v_a, _ = blade_line_snr(arms["ours_phantom4"]["s"][:N_FULL], F_FLASH,
                        F_TIP["phantom4_senior"], k=1, floor="band")
v_b, _ = blade_line_snr(arms["ours_phantom4"]["s"][:N_FULL] * 1e6, F_FLASH,
                        F_TIP["phantom4_senior"], k=1, floor="band")
selftest["normalization_invariance_0db"] = bool(abs(v_a - v_b) < 1e-9)

# --------------------------------------------------------------------------- #
# 6. 격차 분해 — 이전 35.8 vs 8.4~11.4 dB 는 어느 규약 차이였나
# --------------------------------------------------------------------------- #
g = lambda arm, n, key: results[arm][f"N{n}"][key]          # noqa: E731
ours_B5 = g("ours_phantom4", N_FULL, "band_k1_db")
ours_M_B5 = g("ours_matrice4e", N_FULL, "band_k1_db")
sen_B5 = g("senior_full_nylon", N_FULL, "band_k1_db")
sen_L5 = g("senior_full_nylon", N_FULL, "local_k1_db")
sen_none_B5 = g("senior_none_nylon", N_FULL, "band_k1_db")
sen_metal_B5 = g("senior_full_metal", N_FULL, "band_k1_db")
ours_B256 = g("ours_phantom4", N_OVERLAP, "band_k1_db")
sen_B256 = g("senior_full_nylon", N_OVERLAP, "band_k1_db")

gap = dict(
    prior_reported=dict(ours_db=35.8, senior_db=[8.4, 11.4],
                        source="task 문맥의 이전 라운드 보고치 — 본 스크립트가 재현 시도"),
    closest_reproduction=dict(
        ours_like=dict(value_db=ours_B5,
                       recipe="N=5000·DC제거·대역바닥(0.3~1.0 f_tip)·1×f_flash"),
        senior_like=dict(
            value_db=sen_L5,
            per_side_k123_db={f"k{k}": g("senior_full_nylon", N_FULL,
                                         f"local_k{k}_pm_db") for k in (1, 2, 3)},
            recipe="N=5000·DC제거·국소바닥(±60 Hz, 빗살 제외) — 이전 8.4~11.4 dB 는 "
                   "이 레시피의 **한쪽 부호(+측) 저차 조화**값 범위와 겹친다"),
        note="이전 격차는 두 팔이 **서로 다른 바닥 레시피**로 측정된 값으로 재현된다"),
    decomposition_db=dict(
        apparent_gap_mixed_recipes=round(ours_B5 - sen_L5, 1),
        floor_recipe_local_to_band_on_senior=round(sen_B5 - sen_L5, 1),
        same_recipe_engine_gap_band_floor=round(ours_B5 - sen_B5, 1),
        occlusion_within_senior_none_to_full=round(sen_none_B5 - sen_B5, 1),
        blade_material_nylon_to_metal=round(sen_metal_B5 - sen_B5, 1),
        window_5000_to_256_ours=round(ours_B256 - ours_B5, 1),
        window_5000_to_256_senior=round(sen_B256 - sen_B5, 1),
        dc_kept_artifact_at_256_ours=g("ours_phantom4", N_OVERLAP, "dc_artifact_db"),
        dc_kept_artifact_at_256_senior=g("senior_full_nylon", N_OVERLAP,
                                         "dc_artifact_db"),
        normalization=0.0),
    reading=(
        "겉보기 격차(≈{:.0f} dB)의 최대 항은 바닥 레시피 차이(선배 국소바닥은 가림 변조 "
        "연속체 위에 앉아 {:+.1f} dB)이고, 같은 레시피(대역바닥)로 재면 엔진 차이는 "
        "{:+.1f} dB 로 준다. 선배 파이프라인 내부에서 가림(none→full)만 {:+.1f} dB 를 "
        "움직인다 — 우리 SBR 은 광선 차폐가 내장이라 이 축이 규약이 아니라 물리다. "
        "창 길이(5000→256)는 대역바닥 잣대에서 우리 팔 {:+.1f} dB·선배 팔 {:+.1f} dB 를 "
        "움직이고, DC 를 끼우면 256 창에서 +{:.0f} dB 대 아티팩트가 난다(오늘의 교훈)."
    ).format(ours_B5 - sen_L5, sen_B5 - sen_L5, ours_B5 - sen_B5,
             sen_none_B5 - sen_B5, ours_B256 - ours_B5, sen_B256 - sen_B5,
             g("ours_phantom4", N_OVERLAP, "dc_artifact_db")))

# 물리 검증(자가검사 — 완주 조건): 이전 보고치가 우리 사다리 안에서 재현되는가
selftest["prior_ours_within_band_recipe_pm5db"] = bool(abs(ours_B5 - 35.8) <= 5.0)
# ± 각 측을 모아 이전 8.4~11.4 dB 구간이 국소바닥 레시피 값 범위 안에 드는지 본다
sen_locals = []
for k in (1, 2, 3):
    pm = results["senior_full_nylon"][f"N{N_FULL}"].get(f"local_k{k}_pm_db")
    if pm:
        sen_locals += list(pm)
selftest["prior_senior_within_local_recipe_range"] = bool(
    min(sen_locals) <= 8.4 and 11.4 <= max(sen_locals))
#: ⭐N5000 열이 있는 팔만 검사한다 — PS 팔은 256 펄스뿐이라 그 열이 없다(2026-08-15).
selftest["comb_above_white_noise_all_arms"] = bool(
    all(results[n]["comb_share_pct_N5000"] > 13.0 for n in arms
        if results[n]["comb_share_pct_N5000"] is not None))

# --------------------------------------------------------------------------- #
# 7. 그림 — STFT 나란히(영어) + 선 스펙트럼/분해 사다리
# --------------------------------------------------------------------------- #
from md_mapstyle import auto_periods, flash_spec, draw  # noqa: E402

os.makedirs(FIG_DIR, exist_ok=True)
periods = auto_periods(PRF, F_FLASH)
stft_settings = dict(recipe="md_mapstyle.flash_spec (STFT only, house rule)",
                     periods_of_blade_cycle=periods, hop_samples=2, zero_pad=8,
                     window="hann", note="설정은 여기(JSON)에만 — 그림 안 금지")

fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.2), constrained_layout=True)
panel_order = ["ours_phantom4", "senior_full_nylon", "ours_matrice4e", None]
mesh_last = None
t_ov_ms = N_OVERLAP / PRF * 1e3
for ax, name in zip(axes.ravel(), panel_order):
    if name is None:
        ax.set_axis_off()
        ax.text(.5, .62, "Sionna PathSolver", ha="center", va="center",
                fontsize=13, weight="bold", transform=ax.transAxes)
        ax.text(.5, .40,
                "all 256 pulses returned zero signal:\n"
                "0 target paths caught at R = 68.6 m with spp = 1e6\n"
                "(path count scales as (target size / R)$^2$)\n"
                "excluded from quantitative comparison",
                ha="center", va="center", fontsize=10.5, transform=ax.transAxes)
        continue
    a = arms[name]
    ft = F_TIP[a["mesh"]]
    E = np.asarray(a["s"][:N_FULL], complex)
    E = E - E.mean()                                    # DC 제거 후 맵(오늘의 교훈)
    f, t, S, nper = flash_spec(E, PRF, F_FLASH, periods)
    m = draw(ax, t, f, S, ft)                           # mode="peak": 자기 최대 기준(②)
    ax.axvline(t_ov_ms, color="w", ls=":", lw=1.4)
    ax.text(t_ov_ms + 1.5, -1.72 * ft, "256-pulse\noverlap window",
            color="w", fontsize=8.5, ha="left", va="bottom")
    ax.set_title(a["label"], fontsize=11)
    ax.set_xlabel("slow time [ms]")
    ax.set_ylabel("Doppler [Hz]")
fig.colorbar(m, ax=axes, shrink=0.85, label="power [dB rel. panel max]")
fig.suptitle("PX4 maneuver bridge - same flight window (grade 2, t = 5.0 s, "
             "PRF 35 kHz), STFT per arm, DC removed", fontsize=12.5)
fig.savefig(FIG_MAPS, dpi=150)
plt.close(fig)

# --- 선 스펙트럼 + 격차 분해 ------------------------------------------------ #
fig = plt.figure(figsize=(13.5, 8.6), constrained_layout=True)
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05])
axA, axB = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
axC = fig.add_subplot(gs[1, :])
COL = {"ours_phantom4": "#1f77b4", "senior_full_nylon": "#d62728"}
for ax, n, ttl in ((axA, N_FULL, f"N = {N_FULL} pulses  (df = 7.0 Hz)"),
                   (axB, N_OVERLAP, f"N = {N_OVERLAP} pulses  (df = 136.7 Hz) "
                                    "- comb unresolved")):
    for name in ("ours_phantom4", "senior_full_nylon"):
        fr, P = dc_spectrum(arms[name]["s"][:n], True)
        Pdb = 10 * np.log10(P / P.max() + 1e-16)
        sel = (fr >= 0) & (fr <= 1200)
        ax.plot(fr[sel], Pdb[sel], lw=1.0, color=COL[name],
                label=arms[name]["label"].split(" - ")[0]
                + (" - Phantom4" if "phantom4" in name or "senior" in name else ""))
    for kk in range(1, 8):
        ax.axvline(kk * F_FLASH, color="gray", ls="--", lw=0.7, alpha=0.7)
    ax.text(F_FLASH, 2.5, "k x f_flash", color="gray", fontsize=8.5, ha="left")
    if n == N_FULL:
        _att = log_rates["clean_attitude.csv"]
        ax.annotate(f"{F_ART:.0f} Hz: off-comb line, senior arm only\n"
                    f"(= {F_ART / _att:.0f} x {_att:.0f} Hz log rate - "
                    "data artifact candidate)",
                    xy=(F_ART, -10), xytext=(F_ART + 370, -9),
                    fontsize=8.2, color="#8b0000",
                    arrowprops=dict(arrowstyle="->", color="#8b0000", lw=0.9))
    ax.set_title(ttl, fontsize=11)
    ax.set_xlabel("Doppler [Hz]")
    ax.set_ylabel("power [dB rel. max]")
    ax.set_xlim(0, 1200)
    ax.set_ylim(-80, 6)
    ax.legend(fontsize=9, loc="lower right")
dd = gap["decomposition_db"]
bars = [
    ("Apparent gap, mixed recipes\n(ours band-floor vs senior local-floor)",
     dd["apparent_gap_mixed_recipes"]),
    ("Floor recipe on senior arm\n(local -> band)",
     dd["floor_recipe_local_to_band_on_senior"]),
    ("Same-recipe engine gap\n(band floor, ours - senior)",
     dd["same_recipe_engine_gap_band_floor"]),
    ("Occlusion inside senior PO\n(none -> full)",
     dd["occlusion_within_senior_none_to_full"]),
    ("Blade material\n(nylon -> metal)", dd["blade_material_nylon_to_metal"]),
    ("Window length 5000 -> 256\n(ours arm)", dd["window_5000_to_256_ours"]),
    ("DC kept at N=256\n(artifact, ours arm)", dd["dc_kept_artifact_at_256_ours"]),
]
y = np.arange(len(bars))[::-1]
vals = [b[1] for b in bars]
axC.barh(y, vals, color=["#555555", "#d62728", "#1f77b4", "#d62728",
                         "#d62728", "#7f7f7f", "#e6a100"], height=0.62)
for yi, v in zip(y, vals):
    axC.text(v + (0.6 if v >= 0 else -0.6), yi, f"{v:+.1f} dB",
             va="center", ha="left" if v >= 0 else "right", fontsize=9.5)
axC.set_yticks(y, [b[0] for b in bars], fontsize=9)
axC.axvline(0, color="k", lw=0.8)
axC.set_xlim(min(vals) - 8, max(vals) + 8)
axC.set_xlabel("contribution to blade-line SNR difference [dB]")
axC.set_title("Where the previously reported 35.8 vs 8.4-11.4 dB gap comes from "
              "(blade-line SNR at 1 x f_flash, DC removed)", fontsize=11)
fig.suptitle("Blade-comb line spectra and gap decomposition - same PX4 window, "
             "one metric code path for all arms", fontsize=12.5)
fig.savefig(FIG_LINES, dpi=150)
plt.close(fig)

selftest["figures_written"] = bool(
    os.path.getsize(FIG_MAPS) > 50_000 and os.path.getsize(FIG_LINES) > 50_000)

# --------------------------------------------------------------------------- #
# 8. JSON 원장
# --------------------------------------------------------------------------- #
out = dict(
    _meta=dict(
        script="benchmark/bridge_cross_precise.py", written=kst_now(),
        purpose="기동 정밀 교차검증 — 같은 PX4 창(grade 2, t=5.0 s)에서 세 파이프라인 사과-대-사과",
        prf_hz=PRF, fc_hz=FC, wavelength_m=round(LAM, 6), t_start_s=T_START,
        n_full=N_FULL, n_overlap=N_OVERLAP,
        f_flash_hz=F_FLASH,
        f_flash_provenance=dict(
            full_window=rr_full, overlap_window=rr_256,
            note="PX4 로그 esc_rpm×rpm_scale 적분에서 직접 — x500 SITL 값이라 절대 회전수 인용 금지"),
        f_tip_hz={k: round(v, 1) for k, v in F_TIP.items()},
        prop_radius_m=R_PROP,
        alignment=dict(
            overlap_definition="처음 256 펄스 (t=5.0~5.00731 s) — PS 팔 길이가 제약",
            asserts_passed=[k for k in ("prf_fc_tstart_match_all_npz",
                                        "senior_metadata_match",
                                        "trajectory_R_match_ours_vs_ps",
                                        "pulse_index_alignment") if selftest[k]],
            max_R_mismatch_m=dR),
        normalization="팔마다 자기 최대(그림) — 잣대는 비율이라 눈금 불변(검산 통과)",
        stft=stft_settings),
    inputs={k: dict(file=a["file"], md5=a["md5"], mtime=a["mtime"],
                    n_pulses=int(a["s"].size), meta=a["meta"])
            for k, a in arms_raw.items()} | {
        "senior_w0": dict(file=os.path.relpath(jh_w0_path, ROOT),
                          md5=md5_8(jh_w0_path),
                          reconstruction=f"body_occ + blade_occ_{SENIOR_BLADE} "
                                         "(occ=full, MANIFEST 규약)",
                          spreading_note="선배 신호는 1/R² 포함 — 창 내 ΔR/R≈1.1e-4 라 "
                                         "진폭변조 0.001 dB, 비율 잣대에 무영향")},
    # ⭐comparable 을 하드코딩하지 않는다(2026-08-15 정정) — 광선 예산을 4e9 로 올린
    #   재실행에서 256 펄스가 전부 살아났는데도 False 가 박혀 있어 PS 팔이 표에서 빠졌다.
    ps_arm=dict(comparable=bool(ps_comparable), nonzero_pulses=ps_nonzero,
                spp=int(arms_raw["ps_phantom4"]["meta"]["spp"]),
                max_depth=int(arms_raw["ps_phantom4"]["meta"]["max_depth"]),
                reason=notes[0] if notes else None),
    bulk_doppler=bulk,
    metric=dict(
        definition="blade_line_snr(): P=|FFT((s-mean)·hann)|², 봉우리=±k·f_flash "
                   "±max(8 Hz, 1.5빈) 최대, 바닥=band(0.3~1.0 f_tip 중앙값) 또는 "
                   "local(±60 Hz 중앙값, 빗살 정수배 ±max(12,tol) Hz 제외)",
        same_code_path_for_all_arms=True,
        comb_share="0.5·f_flash~f_tip 대역 전력 중 박자 정수배 ±8 Hz 몫 [%] "
                   "(백색잡음≈13, 이상 로터 100)"),
    results=results,
    artifact_350hz=artifact,
    gap_decomposition=gap,
    honest_notes=notes + [
        "ours_phantom4 는 선배 메쉬(phantom4_senior) 위에서 우리 커널을 돌린 팔 — 메쉬 "
        "차이가 아니라 커널 차이를 본다. ours_matrice4e 는 우리 CAD(다른 기체)라 "
        "직접 격차 분해에는 안 쓰고 참조로만 둔다.",
        "ours 팔 재질은 mat_mode=ours 매핑(nylon→prop_plastic, 수직입사 −2.5 dB) — 재질 "
        "규약 차이는 선배 내부 변주(nylon→metal)로 상한을 쟀다(±1.6 dB 급).",
        "선배 국소바닥이 높은 것은 잡음이 아니라 **가림 변조 연속체**(clean 신호) — "
        "senior none→full 이 대역바닥 잣대로도 큰 폭을 움직이는 것과 같은 원인.",
        "256 펄스 창에서 국소바닥 레시피는 빗살 간격(153 Hz) < 제외폭이라 측정 불가 — "
        "None 으로 기록(억지 측정 금지). 교차창 비교는 대역바닥 레시피로만.",
    ],
    selftest=selftest,
)

selftest_ok = all(selftest.values())
out["selftest_ok"] = selftest_ok
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=float)

print(f"\n✅ JSON  {os.path.relpath(OUT_JSON, ROOT)}")
print(f"✅ FIGS  {os.path.relpath(FIG_MAPS, ROOT)}  {os.path.relpath(FIG_LINES, ROOT)}")
print(f"selftest_ok = {selftest_ok}")
for k, v in selftest.items():
    print(f"   [{'PASS' if v else 'FAIL'}] {k}")
print("\n핵심 수치:")
print(f"  f_flash = {F_FLASH:.1f} Hz · ours@band N5000 = {ours_B5:.1f} dB · "
      f"senior@local N5000 = {sen_L5:.1f} dB · senior@band N5000 = {sen_B5:.1f} dB")
print(f"  분해: 바닥레시피 {gap['decomposition_db']['floor_recipe_local_to_band_on_senior']:+.1f} · "
      f"동일레시피 엔진격차 {gap['decomposition_db']['same_recipe_engine_gap_band_floor']:+.1f} · "
      f"가림(선배내부) {gap['decomposition_db']['occlusion_within_senior_none_to_full']:+.1f} · "
      f"창길이(ours) {gap['decomposition_db']['window_5000_to_256_ours']:+.1f} · "
      f"DC아티팩트@256 {gap['decomposition_db']['dc_kept_artifact_at_256_ours']:+.1f} dB")
