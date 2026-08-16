# -*- coding: utf-8 -*-
"""
noise_distance_frame.py — 잡음을 실제로 넣으면 거리별로 어느 팔이 무엇까지 읽히나
=================================================================================

무엇을 묻나 (사용자 질문, 2026-08-15)
------------------------------------
«거리 결과 보니까 잡음 모델링하면 물리 켬 버전은 아무것도 못 읽겠는데?
 잡음 모델링해서 우리 커널과 물리 끔을 비교해 줄 수 있을까?»

그래서 **표준 비교 프레임**(docs/STANDARD_FRAME.md)의 팔들을 거리축에 나란히 놓고,
저장된 원장 시계열에 **실제 열잡음을 섞은 뒤** 두 가지를 따로 잰다.

  (a) 탐지  — 표적(움직이는 부분)이 있나 없나.  Pfa 1e-3 문턱은 **잡음 전용** 시행으로 교정.
  (b) ⭐판독 — 잡음을 섞고도 **날개 무늬가 남나**. 이것이 사용자가 실제로 묻는 것이다.
             잣대는 빗살 대비 comb_contrast_db(백색 = 0 dB)를 **잡음 섞은 시계열에서 다시** 잰 값.

⭐(a)와 (b)는 다른 질문이다. 세기만 크면 (a)는 통과한다 — 스펙트럼이 백색이어도 빗살 칸에
에너지가 들어차기 때문이다. «읽힌다» 는 (b)만 말할 수 있다.

표준 프레임 (⛔회절 D1 조합은 프레임 밖이라 빼고, 물리 전부 켬은 «참고» 로만 싣는다)
-----------------------------------------------------------------------------------
  · 내 커널 (SBR+PO)            ours_r{15,30,60,120}_n8192            — 거리 4점
  · 내 커널 + PTD               ours_ptd_r15_n8192                    — 원장에 15 m 판만
  · PathSolver 다 끔 (R0D0E0F1) sionna_p4000000000_r{15,30,60,120}_n8192_d1 — 거리 4점
  · PathSolver 굴절만 (R1D0E0F1) sionna_p4000000000_onlyrefr_r15_n8192 — 15 m 판만(거리 팔 계산 중)
  · PathSolver 모서리만          ≡ 다 끔과 동일 데이터(별칭, 재계산 없음 — 자가검사 6 이 확인)
  · PathSolver 굴절+모서리       ≡ 굴절만과 동일 데이터(별칭)
  · 선배 커널 (jihyuck PO)       거리 팔 **해당 없음** — 아래 프레임 표에 이유를 수치로 적었다
  · [프레임 밖 참고] 물리 전부 켬 sionna_p4000000000_phys_r{15,30,60,120}_n8192_d1

⭐⭐이 분석의 최대 함정 — 엔진 간 절대 세기는 비교할 수 없다
------------------------------------------------------------
우리 커널의 E 는 «그 거리의 수신 전력» 이 아니라 σ = (4π/λ²)|E|² 로 읽어야 하는 양이고
(1/r 확산을 안 넣는다 — rcs_sbr 규약), PathSolver 의 경로 진폭은 **자기 확산을 이미 품고**
있다. 실제로 원장에서 거리 4점의 세기를 재 보면(자가검사 3):

    우리 커널   : 15→120 m 에서 0.2 dB 만 변한다        → 자체 거리법칙 지수 p = 0
    PathSolver  : 옥타브마다 정확히 −6.03 dB (el 0°)    → 전력 ∝ 1/R², 즉 p = 2
                  (경로 진폭 ∝ 1/Σr — 소형 표적 산란이 아니라 «거울 반사» 의 확산법칙이다)

그래서 세 규약을 다 계산하고 결과가 어떻게 갈리는지까지 적는다.

    S1 [헤드라인]  엔진의 자체 확산을 벗겨(×(R/15)^p) σ 로 되돌린 뒤, 물리적 1/R⁴ 을
                   레이더 방정식에서 **한 번만** 건다. 레벨은 팔·앙각마다 그 팔의 15 m
                   판을 문헌 앵커 σ_ref 에 맞춘다.
    S2 [순진]      벗기지 않고 엔진 세기를 그대로 σ 로 읽고 1/R⁴ 을 또 건다(=이중계상).
                   PathSolver 는 120 m 에서 S1 보다 18.1 dB 손해를 본다.
    S3 [AC 앵커]   총 σ 대신 **움직이는 성분**(AC)을 σ_ref 에 맞춘다. 동체 받침대(DC)가
                   지우는 몫이 얼마인지 보는 규약 — 물리 켬 팔이 여기서 +31 dB 를 돌려받는다.

⭐그리고 SNR 축을 따로 낸다 — 잣대 곡선(빗살 대비 vs SNR)은 **규약과 무관**하다.
규약이 바꾸는 것은 «거리 → SNR» 지도뿐이다. 그래서 이 스크립트는 곡선을 한 번만 재고,
규약 셋을 그 곡선 위의 서로 다른 자리로 읽는다. 함정이 어디에 사는지가 그 구조로 드러난다.

거리축 두 종류
--------------
  A2 [원장 4점]  15·30·60·120 m — 엔진이 **그 거리에서 다시 계산한** 시계열(모양도 바뀐다).
  A1 [연장선]    15 m 모양을 얼리고 거리로 **잡음 크기만** 바꾼 축(15~3000 m).
                 rx_noise/experiment_md_range 의 A1 규약. 자가검사 9 가 A1↔A2 어긋남을
                 원장 4점에서 직접 재서 연장선을 어디까지 믿어도 되는지 적는다.

잣대와 판정
-----------
  빗살 대비 comb_contrast_db  build_md_atlas 정의 그대로(2·f_flash ~ f_tip, 정수배 ÷ 중간자리).
                              백색 ≈ 0 dB. ⭐헤드라인 잣대.
  리듬 몫 rhythm_share_pct    build_md_atlas/structure_bars 정의 그대로(날개끝 상한 **위**).
                              ⛔상한 위만 보므로 0 % 가 «무늬 없음» 을 뜻하지 않는다 — 교차검증용.
  탐지 통계량                 detection_curves.py 규약 그대로(DC 제거·한나창 FFT,
                              대역 0.35~1.0×f_tip, 주=빗살칸 에너지 / 보조=대역 전체),
                              + 에너지 검출기(DC 포함 총 전력) 하나 더.
  판정 밴드                   격자 흔들림(λ/12↔λ/24) 밴드 = 리듬 21.8 %p · 세기 3.86 dB
                              (outputs/grid_convergence_check.json). 이 안이면 «판정 불가».
                              ⚠3.86 dB 는 AC **절대전력** 에서 잰 밴드다 — dB 잣대인 빗살
                              대비에 그대로 대는 것은 보수적 대용이며, 그 사실을 함께 적는다.

⛔GPU/솔버 없음 — sionna.rt·mitsuba 임포트 없음(자가검사 1). 저장된 원장만 읽는 CPU 분석.
⛔기존 파일 수정 없음 — 산출은 outputs/noise_distance_frame.json +
   outputs/figures/noise_distance_frame.png 둘뿐.

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/noise_distance_frame.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import asdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 재사용(재발명 금지): 잡음 N=kT0·F·PRF · σ=(4π/λ²)|E|² · 문헌 앵커 · 1/R⁴ 레이더 방정식
from rx_noise import (RxSpec, noise_power_w, sigma_kernel_m2,          # noqa: E402
                      sigma_ref_from_literature)
from link_budget import LinkBudget, C0, lin2db                          # noqa: E402

# --------------------------------------------------------------------------- #
#  설정 — 전부 원장에 기록된다
# --------------------------------------------------------------------------- #
SEED = 20260815
PFA = 1e-3
N_MC = 240          # 거리·팔당 몬테카를로 시행 (요구 ≥200)
N_SNR = 200         # SNR 격자 점당 시행 (요구 ≥200)
N_NULL = 4000       # 널 대조(잡음 전용) 시행 — 잣대 분포용
N_CAL = 30000       # 문턱 교정용 잡음 전용 시행
N_VER = 30000       # Pfa 실측 검증용 홀드아웃(다른 씨앗)
BATCH = 500         # 잡음 배치(메모리 절충: 500×8192 complex ≈ 65 MB)

HW_HZ = 8.0         # 빗살 반폭 [Hz] — 표준 레시피
BAND_LO = 0.35      # 탐지 대역 하한 = 0.35·f_tip (원장 band_track 정본)
EIRP_DBM = 30.0     # ⭐선언값 — 소형 모노스태틱 센서급(rx_noise 데모·detection_curves 와 동일)
R_REF = 15.0        # 앵커 거리
# 요구 −10~+40 dB 를 여유 있게 덮는다. 아래쪽을 −60 까지 늘린 이유: 에너지 검출기는
# 8192 표본을 모아 −45 dB 언저리에서도 터져서, 격자 안에 교차점이 들어와야 한계거리를 낸다.
SNR_GRID_DB = np.concatenate([np.arange(-60.0, -20.0, 2.0),
                              np.arange(-20.0, 55.0 + 1e-9, 1.0)])
R_EXT = np.geomspace(15.0, 3000.0, 61)              # A1 연장 거리축

# 격자 흔들림 밴드 — outputs/grid_convergence_check.json (판정 불가 폭)
GRID_BAND_RHYTHM_PP = 21.819
GRID_BAND_DB = 3.861

LEDGER_JSON = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
GRID_JSON = os.path.join(ROOT, "outputs", "grid_convergence_check.json")
OUT_JSON = os.path.join(ROOT, "outputs", "noise_distance_frame.json")
OUT_PNG = os.path.join(ROOT, "outputs", "figures", "noise_distance_frame.png")

RANGES = [15.0, 30.0, 60.0, 120.0]
ELS = [-30.0, 0.0]          # 헤드라인 = −30°(프레임 주판), 보조 = 0°
EL_MAIN = -30.0

# 검증된 기성 카테고리 팔레트(dataviz 스킬 references/palette.md 의 고정 슬롯 순서.
# node 검증기가 이 환경에 없어 문서화된 검증값을 슬롯 순서 그대로 쓴다 — 자작 색 금지).
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MUTED, SURFACE, INK, INK2 = "#52514e", "#fcfcfb", "#0b0b0b", "#52514e"

# --------------------------------------------------------------------------- #
#  표준 프레임 — 팔 정의
# --------------------------------------------------------------------------- #
ARMS = [
    dict(key="ours", label_en="Ours (SBR+PO)", label_ko="내 커널 (SBR+PO)",
         pat="ours_r{R}_n8192", ranges=RANGES, family="ours", p_engine=0.0,
         in_frame=True, color=SLOT[0], ls="-", marker="o"),
    dict(key="ours_ptd", label_en="Ours + PTD", label_ko="내 커널 + PTD",
         pat="ours_ptd_r{R}_n8192", ranges=[15.0], family="ours", p_engine=0.0,
         in_frame=True, color=SLOT[1], ls="-", marker="s"),
    dict(key="ps_off", label_en="PathSolver all-off (R0D0E0F1)",
         label_ko="PathSolver 다 끔 (R0D0E0F1)",
         pat="sionna_p4000000000_r{R}_n8192_d1", ranges=RANGES, family="sionna",
         p_engine=2.0, in_frame=True, color=SLOT[2], ls="--", marker="^"),
    dict(key="ps_refr", label_en="PathSolver refraction-only (R1D0E0F1)",
         label_ko="PathSolver 굴절만 (R1D0E0F1)",
         pat="sionna_p4000000000_onlyrefr_r{R}_n8192", ranges=[15.0],
         family="sionna", p_engine=2.0, in_frame=True, color=SLOT[3], ls="--",
         marker="D"),
    dict(key="ps_phys", label_en="PathSolver all physics ON (out of frame)",
         label_ko="PathSolver 물리 전부 켬 (프레임 밖 참고)",
         pat="sionna_p4000000000_phys_r{R}_n8192_d1", ranges=RANGES,
         family="sionna", p_engine=2.0, in_frame=False, color=MUTED, ls=":",
         marker="v"),
]

ALIASES = [
    dict(key="ps_edge", label_ko="PathSolver 모서리만", alias_of="ps_off",
         evidence="sionna_p4000000000_onlyedge_r15_n8192 ↔ 다 끔: 자가검사 6"),
    dict(key="ps_refr_edge", label_ko="PathSolver 굴절+모서리", alias_of="ps_refr",
         evidence="소스 게이트상 모서리 스위치가 결과를 안 바꾼다 — 같은 데이터"),
]

# 거리 팔이 원장에 없는 칸의 사유 (사용자 확인 사항 포함)
MISSING_REASON = {
    "ours_ptd": ("ledger_has_15m_only",
                 "원장에 15 m 판만 있다(PTD 는 자세당 1.3 s, 순정의 10배). 거리 팔 미계산."),
    "ps_refr": ("computing_now",
                "⚠거리 팔(30·60·120 m)이 지금 큐에서 계산 중이라 원장에 아직 없다. "
                "나중에 다시 돌리면 이 칸이 채워진다."),
}

# --------------------------------------------------------------------------- #
#  원장 읽기
# --------------------------------------------------------------------------- #
def el_key(el: float) -> str:
    return "el+0" if el == 0 else f"el{int(el):d}"


def load_cells():
    """표준 프레임의 (팔 × 거리 × 앙각) 칸을 원장에서 읽는다. 없는 칸은 사유와 함께 남긴다."""
    led = json.load(open(LEDGER_JSON))
    meta = led["_meta"]
    z = np.load(LEDGER_NPZ)
    rows = {}
    for r in led["rows"]:
        rows[(r["engine"], float(r["el_deg"]))] = r      # 마지막 행이 정본
    cells, frame_status = [], []
    for arm in ARMS:
        for R in RANGES:
            eng = arm["pat"].format(R=int(R))
            for el in ELS:
                key = f"{eng}/{el_key(el)}"
                present = (R in arm["ranges"]) and (key in z.files) \
                    and ((eng, el) in rows)
                st = dict(arm=arm["key"], range_m=R, el_deg=el, engine=eng,
                          present=bool(present))
                if not present:
                    code, why = MISSING_REASON.get(
                        arm["key"], ("not_in_ledger", "원장에 이 칸이 없다"))
                    if R in arm["ranges"]:      # 거리는 있는데 앙각이 없는 경우
                        code, why = ("elevation_absent",
                                     "이 거리 팔에는 이 앙각이 원장에 없다")
                    st.update(status=code, note_ko=why)
                    frame_status.append(st)
                    continue
                row = rows[(eng, el)]
                E = np.asarray(z[key], complex)
                n_zero = int(np.count_nonzero(E == 0))
                if int(row.get("n_missing") or 0) or n_zero:
                    raise ValueError(f"{key}: 덜 찬 칸(n_missing={row.get('n_missing')}, "
                                     f"zeros={n_zero}) — 잣대를 낼 자격이 없다")
                if abs(float(row["range_m"]) - R) > 1e-9:
                    raise ValueError(f"{key}: 원장 range_m={row['range_m']} ≠ {R}")
                st.update(status="present", note_ko="")
                frame_status.append(st)
                cells.append(dict(
                    cell_id=f"{arm['key']}_r{int(R)}_el{int(el):+d}", arm=arm["key"],
                    range_m=R, el_deg=el, engine=eng, npz_key=key, E=E,
                    f_tip_hz=float(row["f_tip_hz"]), fc_hz=float(row["fc_hz"]),
                    n=int(E.size), level_db=float(row["level_db"]),
                    ledger=dict(n_poses=int(row["n_poses"]), seconds=row.get("seconds"),
                                spp=row.get("spp"), max_depth=row.get("max_depth"),
                                physics=row.get("physics"), grid_div=row.get("grid_div"))))
    ns = {c["n"] for c in cells}
    if len(ns) != 1:
        raise ValueError(f"시계열 길이가 섞였다 {ns} — 문턱 공유 전제가 깨진다")
    fcs = {c["fc_hz"] for c in cells}
    if len(fcs) != 1:
        raise ValueError(f"반송파가 섞였다 {fcs}")
    return cells, frame_status, dict(
        prf_hz=float(meta["prf_hz"]), f_flash_hz=float(meta["f_flash_hz"]),
        fc_hz=fcs.pop(), drone=str(meta["drone"]), n=int(ns.pop()))


# --------------------------------------------------------------------------- #
#  마스크 — 판독 잣대(아틀라스 규약) + 탐지 통계량(detection_curves 규약)
# --------------------------------------------------------------------------- #
def make_masks(n: int, prf: float, f_tip: float, f_flash: float) -> dict:
    fr_s = np.fft.fftfreq(n, 1.0 / prf)
    fr = np.abs(fr_s)
    # (1) 판독 — 빗살 대비: 상한 아래 [2·f_flash, f_tip], 정수배 ÷ 중간자리
    lo, hi = 2.0 * f_flash, f_tip
    if hi < 3.0 * f_flash:
        raise ValueError(f"빗살 대비 대역이 좁다 (f_tip={f_tip})")
    k = fr / f_flash
    band_c = (fr >= lo) & (fr <= hi)
    comb_on = band_c & (np.abs(k - np.round(k)) * f_flash <= HW_HZ)
    comb_off = band_c & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= HW_HZ)
    if comb_on.sum() < 4 or comb_off.sum() < 4:
        raise ValueError("빗살 on/off 칸이 4개 미만")
    # (2) 판독 보조 — 리듬 몫: 상한 **위** 에서 정수배 몫
    above = fr >= f_tip
    kk = np.round(fr / f_flash)
    rhy_on = above & (np.abs(fr - kk * f_flash) <= HW_HZ)
    # (3) 탐지 — 블레이드 대역 0.35~1.0×f_tip, 그 안의 빗살
    band_d = (fr >= BAND_LO * f_tip) & (fr <= f_tip)
    det_comb = band_d & (np.abs(fr - kk * f_flash) <= HW_HZ) & (kk >= 1)
    if not det_comb.any():
        raise ValueError("탐지 빗살 마스크가 비었다")
    return dict(comb_on=comb_on, comb_off=comb_off, above=above, rhy_on=rhy_on,
                band_d=band_d, det_comb=det_comb,
                rhythm_null_pct=float(100.0 * rhy_on.sum() / above.sum()),
                n_comb_on=int(comb_on.sum()), n_comb_off=int(comb_off.sum()),
                n_band_d=int(band_d.sum()), n_det_comb=int(det_comb.sum()))


def stats_batch(X: np.ndarray, w: np.ndarray, m: dict) -> dict:
    """행렬 X(시행×n) → 판독 잣대 2 종 + 탐지 통계량 3 종. ⭐행마다 DC 제거 후 한나창 FFT."""
    Xc = (X - X.mean(axis=1, keepdims=True)) * w
    P = np.abs(np.fft.fft(Xc, axis=1)) ** 2
    on, off = P[:, m["comb_on"]].mean(axis=1), P[:, m["comb_off"]].mean(axis=1)
    comb_db = 10.0 * np.log10(np.maximum(on, 1e-300) / np.maximum(off, 1e-300))
    rhy = 100.0 * P[:, m["rhy_on"]].sum(axis=1) / np.maximum(
        P[:, m["above"]].sum(axis=1), 1e-300)
    return dict(comb_db=comb_db, rhythm_pct=rhy,
                t_comb=P[:, m["det_comb"]].sum(axis=1),
                t_band=P[:, m["band_d"]].sum(axis=1),
                t_energy=(np.abs(X) ** 2).sum(axis=1))     # ⭐에너지 검출기는 DC 포함


def noise_batch(rng, m: int, n: int, var: float = 1.0) -> np.ndarray:
    """복소 백색가우스 CN(0, var) — 실·허 각각 분산 var/2 (rx_noise 규약)."""
    return ((rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n)))
            * math.sqrt(var / 2.0))


def run_noise_only(rng, n_trial: int, n: int, w, masks: dict) -> dict:
    """잡음 **전용** 시행 — 신호는 인자에도 없다(문턱 누설 원천 차단)."""
    acc = {el: {k: [] for k in ("comb_db", "rhythm_pct", "t_comb", "t_band",
                                "t_energy")} for el in masks}
    done = 0
    while done < n_trial:
        mb = min(BATCH, n_trial - done)
        Z = noise_batch(rng, mb, n)
        for el, mk in masks.items():
            s = stats_batch(Z, w, mk)
            for k in acc[el]:
                acc[el][k].append(s[k])
        done += mb
    return {el: {k: np.concatenate(v) for k, v in d.items()} for el, d in acc.items()}


def run_signal(rng, E_unit: np.ndarray, snr_ac_db: float, n_trial: int, w,
               mk: dict) -> dict:
    """AC 전력이 snr_ac 가 되도록 신호를 키우고 단위분산 잡음을 섞어 잣대를 잰다.

    E_unit 은 ⟨|E−mean|²⟩ = 1 로 정규화된 열(DC 는 그대로 실려 있다 — 에너지 검출기가 쓴다).
    잡음 전력을 1 로 고정했으므로 SNR 은 신호 배율로만 들어간다(백색잡음이라 비율만 의미)."""
    a = 10.0 ** (snr_ac_db / 20.0)
    x0 = a * E_unit
    out = {k: [] for k in ("comb_db", "rhythm_pct", "t_comb", "t_band", "t_energy")}
    done = 0
    while done < n_trial:
        mb = min(BATCH, n_trial - done)
        X = x0[None, :] + noise_batch(rng, mb, E_unit.size)
        s = stats_batch(X, w, mk)
        for k in out:
            out[k].append(s[k])
        done += mb
    return {k: np.concatenate(v) for k, v in out.items()}


def _q(v, lo=None):
    return dict(mean=float(np.mean(v)), std=float(np.std(v)),
                p05=float(np.quantile(v, 0.05)), p95=float(np.quantile(v, 0.95)))


# --------------------------------------------------------------------------- #
#  본체
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    cells, frame_status, meta = load_cells()
    n, prf, f_flash = meta["n"], meta["prf_hz"], meta["f_flash_hz"]
    fc, lam = meta["fc_hz"], C0 / meta["fc_hz"]
    w = np.hanning(n)

    # --- 마스크(앙각당) — f_tip 은 팔 사이에서 같아야 한다 --------------------- #
    ftip = {}
    for c in cells:
        ftip.setdefault(c["el_deg"], set()).add(c["f_tip_hz"])
    for el, s in ftip.items():
        if len(s) != 1:
            raise ValueError(f"el={el}: 팔 간 f_tip 불일치 {s}")
    ftip = {el: s.pop() for el, s in ftip.items()}
    masks = {el: make_masks(n, prf, ft, f_flash) for el, ft in ftip.items()}

    # --- 수신 예산 + 잡음 전력(절대 눈금) ------------------------------------- #
    spec = RxSpec(eirp_dbm=EIRP_DBM)
    N_w = noise_power_w(spec, prf)                     # N = k·T0·F·PRF [W]
    lb = LinkBudget(eirp_dbm=spec.eirp_dbm, rx_gain_dbi=spec.grx_dbi,
                    noise_figure_db=spec.nf_db, sys_loss_db=spec.sys_loss_db)
    ref = sigma_ref_from_literature(fc, meta["drone"])
    sigma_ref = 10.0 ** (ref["sigma_ref_dbsm"] / 10.0)

    # --- ⭐엔진 자체 거리법칙 실측(자가검사 3 의 근거) ------------------------- #
    lvl = {(c["arm"], c["range_m"], c["el_deg"]):
           float(np.mean(np.abs(c["E"]) ** 2)) for c in cells}
    engine_law = {}
    for arm in ARMS:
        for el in ELS:
            pts = [(R, lvl[(arm["key"], R, el)]) for R in RANGES
                   if (arm["key"], R, el) in lvl]
            if len(pts) < 3:
                continue
            x = np.log10([p[0] / R_REF for p in pts])
            y = 10.0 * np.log10([p[1] for p in pts])
            slope = float(np.polyfit(x, y, 1)[0])       # dB per decade
            engine_law[f"{arm['key']}_el{int(el):+d}"] = dict(
                measured_slope_db_per_decade=round(slope, 2),
                measured_p=round(-slope / 10.0, 3), assumed_p=arm["p_engine"],
                levels_db={str(int(R)): round(10 * math.log10(lvl[(arm['key'], R, el)]), 2)
                           for R in RANGES if (arm["key"], R, el) in lvl})

    # --- 절대 눈금(규약 S1/S2/S3) — 팔·앙각마다 그 팔의 15 m 판을 앵커 ---------- #
    #   σ̃(t;R) = (4π/λ²)|E|²·(R/15)^p  ,  c = σ_ref/⟨σ̃(15 m)⟩
    #   P_echo(t;R) = EIRP·G·λ²·σ̃c/((4π)³R⁴)  ⇒ x = g·E (모양은 손대지 않는다)
    armd = {a["key"]: a for a in ARMS}
    anchor = {}
    for c in cells:
        if c["range_m"] != R_REF:
            continue
        sk = sigma_kernel_m2(c["E"], fc)
        ac = sigma_kernel_m2(c["E"] - c["E"].mean(), fc)
        anchor[(c["arm"], c["el_deg"])] = dict(
            sigma_kernel_mean=float(sk.mean()), sigma_kernel_ac_mean=float(ac.mean()),
            c_total=float(sigma_ref / sk.mean()), c_ac=float(sigma_ref / ac.mean()),
            engine_level_dbsm_like=round(float(lin2db(sk.mean())), 2))

    def residual_db(c) -> float:
        """⭐엔진 자체 확산(p)을 벗기고도 남는 레벨 변화 [dB] — 15 m 대비.

        0 이면 «그 엔진의 거리 거동은 자기 확산법칙 하나로 설명된다» 는 뜻이고,
        크게 음수면 그 팔의 거리 거동에 확산 말고 다른 것(성긴 경로·수치 바닥)이 섞여 있다."""
        p = armd[c["arm"]]["p_engine"]
        base = lvl.get((c["arm"], R_REF, c["el_deg"]))
        if base is None or base <= 0:
            return float("nan")
        return float(10.0 * math.log10(
            lvl[(c["arm"], c["range_m"], c["el_deg"])]
            * (c["range_m"] / R_REF) ** p / base))

    def snr_of(c, conv: str) -> dict:
        """칸의 (총·AC) 표본 SNR [dB] — 규약 S1/S2/S3."""
        a = armd[c["arm"]]
        an = anchor[(c["arm"], c["el_deg"])]
        p = a["p_engine"] if conv != "S2" else 0.0        # S2 = 벗기지 않는다
        cc = an["c_ac"] if conv == "S3" else an["c_total"]
        sig = sigma_kernel_m2(c["E"], fc) * (c["range_m"] / R_REF) ** p * cc
        sig_ac = sigma_kernel_m2(c["E"] - c["E"].mean(), fc) \
            * (c["range_m"] / R_REF) ** p * cc
        R = c["range_m"]
        P = lb.echo_power_w(lam, sig, R, R)               # 1/R⁴ 은 여기 한 번뿐
        P_ac = lb.echo_power_w(lam, sig_ac, R, R)
        return dict(snr_total_db=float(lin2db(P.mean() / N_w)),
                    snr_ac_db=float(lin2db(P_ac.mean() / N_w)))

    # --- 문턱 교정(잡음 전용) + 홀드아웃 Pfa 실측 + 널 대조 -------------------- #
    rng_cal = np.random.default_rng(SEED)
    rng_ver = np.random.default_rng(SEED + 1)
    rng_null = np.random.default_rng(SEED + 2)
    rng_sig = np.random.default_rng(SEED + 3)
    cal = run_noise_only(rng_cal, N_CAL, n, w, masks)
    ver = run_noise_only(rng_ver, N_VER, n, w, masks)
    nul = run_noise_only(rng_null, N_NULL, n, w, masks)
    thr, pfa_meas, null_stat = {}, {}, {}
    for el in masks:
        thr[el] = {st: float(np.quantile(cal[el][st], 1.0 - PFA))
                   for st in ("t_comb", "t_band", "t_energy")}
        pfa_meas[el] = {st: float((ver[el][st] > thr[el][st]).mean())
                        for st in thr[el]}
        null_stat[el] = dict(
            comb_contrast_db=_q(nul[el]["comb_db"]),
            rhythm_share_pct=_q(nul[el]["rhythm_pct"]),
            rhythm_null_analytic_pct=round(masks[el]["rhythm_null_pct"], 2),
            n_trial=N_NULL)

    # 판정선: 백색선 + 격자 밴드 / 백색선 + 2σ
    read_line = {el: dict(
        white_mean_db=null_stat[el]["comb_contrast_db"]["mean"],
        readable_db=null_stat[el]["comb_contrast_db"]["mean"] + GRID_BAND_DB,
        undecidable_db=null_stat[el]["comb_contrast_db"]["mean"]
        + 2 * null_stat[el]["comb_contrast_db"]["std"],
        rhythm_readable_pct=null_stat[el]["rhythm_share_pct"]["mean"]
        + GRID_BAND_RHYTHM_PP) for el in masks}

    # --- ⭐SNR 축(규약 무관) — 칸마다 잣대·Pd vs SNR 곡선 ---------------------- #
    for c in cells:
        E = c["E"]
        ac_pow = float(np.mean(np.abs(E - E.mean()) ** 2))
        c["ac_frac"] = ac_pow / float(np.mean(np.abs(E) ** 2))
        c["E_unit"] = E / math.sqrt(ac_pow)              # ⟨|AC|²⟩ = 1
        mk = masks[c["el_deg"]]
        s0 = stats_batch(E[None, :], w, mk)              # 무잡음 잣대
        c["clean"] = dict(comb_contrast_db=float(s0["comb_db"][0]),
                          rhythm_share_pct=float(s0["rhythm_pct"][0]))
        rows = []
        for snr in SNR_GRID_DB:
            r = run_signal(rng_sig, c["E_unit"], float(snr), N_SNR, w, mk)
            rows.append(dict(
                snr_ac_db=float(snr),
                comb_db_mean=float(np.mean(r["comb_db"])),
                comb_db_std=float(np.std(r["comb_db"])),
                rhythm_pct_mean=float(np.mean(r["rhythm_pct"])),
                pd_comb=float((r["t_comb"] > thr[c["el_deg"]]["t_comb"]).mean()),
                pd_band=float((r["t_band"] > thr[c["el_deg"]]["t_band"]).mean()),
                pd_energy=float((r["t_energy"] > thr[c["el_deg"]]["t_energy"]).mean())))
        c["snr_curve"] = rows

    # --- 곡선에서 SNR 문턱 뽑기(단조 증가 가정, 선형보간) --------------------- #
    def crossing(rows, key, level, rising=True):
        x = np.array([r["snr_ac_db"] for r in rows], float)
        y = np.array([r[key] for r in rows], float)
        ok = y >= level if rising else y <= level
        if ok.all():
            return float(x[0])
        if not ok.any():
            return None
        i = int(np.argmax(ok))
        if i == 0:
            return float(x[0])
        y0, y1 = y[i - 1], y[i]
        if abs(y1 - y0) < 1e-12:
            return float(x[i])
        return float(x[i - 1] + (level - y0) / (y1 - y0) * (x[i] - x[i - 1]))

    for c in cells:
        el = c["el_deg"]
        c["snr_thresholds_db"] = dict(
            pattern_readable=crossing(c["snr_curve"], "comb_db_mean",
                                      read_line[el]["readable_db"]),
            pattern_above_2sigma=crossing(c["snr_curve"], "comb_db_mean",
                                          read_line[el]["undecidable_db"]),
            rhythm_readable=crossing(c["snr_curve"], "rhythm_pct_mean",
                                     read_line[el]["rhythm_readable_pct"]),
            pd_comb_50=crossing(c["snr_curve"], "pd_comb", 0.5),
            pd_comb_90=crossing(c["snr_curve"], "pd_comb", 0.9),
            pd_energy_90=crossing(c["snr_curve"], "pd_energy", 0.9))

    # --- 거리 표(A2: 원장 4점, 규약 셋) --------------------------------------- #
    def verdict(comb_mean, pd_comb, el):
        rl = read_line[el]
        if comb_mean >= rl["readable_db"]:
            read = "무늬 읽힘"
        elif comb_mean >= rl["undecidable_db"]:
            read = "판정 불가(격자 밴드 안)"
        else:
            read = "무늬 안 읽힘"
        det = "탐지" if pd_comb >= 0.9 else ("애매" if pd_comb > 0.1 else "미탐지")
        return read, det

    for c in cells:
        mk = masks[c["el_deg"]]
        c["by_convention"] = {}
        for conv in ("S1", "S2", "S3"):
            s = snr_of(c, conv)
            r = run_signal(rng_sig, c["E_unit"], s["snr_ac_db"], N_MC, w, mk)
            comb_mean = float(np.mean(r["comb_db"]))
            pd_comb = float((r["t_comb"] > thr[c["el_deg"]]["t_comb"]).mean())
            rd, dt = verdict(comb_mean, pd_comb, c["el_deg"])
            c["by_convention"][conv] = dict(
                snr_ac_db=round(s["snr_ac_db"], 2),
                snr_total_db=round(s["snr_total_db"], 2),
                comb_contrast_db_mean=round(comb_mean, 2),
                comb_contrast_db_std=round(float(np.std(r["comb_db"])), 2),
                rhythm_share_pct_mean=round(float(np.mean(r["rhythm_pct"])), 1),
                pd_comb=pd_comb,
                pd_band=float((r["t_band"] > thr[c["el_deg"]]["t_band"]).mean()),
                pd_energy=float((r["t_energy"] > thr[c["el_deg"]]["t_energy"]).mean()),
                verdict_read_ko=rd, verdict_detect_ko=dt)

    # --- A1 연장선(15 m 모양을 얼리고 거리로 잡음만 바꾼다) -------------------- #
    ext = {}
    for c in cells:
        if c["range_m"] != R_REF:
            continue
        s15 = c["by_convention"]["S1"]["snr_ac_db"]
        rows = c["snr_curve"]
        x = np.array([r["snr_ac_db"] for r in rows], float)
        snr_R = s15 - 40.0 * np.log10(R_EXT / R_REF)          # 1/R⁴
        get = lambda k: np.interp(snr_R, x, [r[k] for r in rows],           # noqa: E731
                                  left=np.nan, right=np.nan)
        st = c["snr_thresholds_db"]

        def r_at(snr_th):
            if snr_th is None:
                return None
            return float(R_REF * 10.0 ** ((s15 - snr_th) / 40.0))
        ext[c["cell_id"]] = dict(
            arm=c["arm"], el_deg=c["el_deg"], snr_ac_db_at_15m=round(s15, 2),
            R_m=[round(float(r), 1) for r in R_EXT],
            snr_ac_db=[round(float(v), 2) for v in snr_R],
            comb_db=[None if not np.isfinite(v) else round(float(v), 2)
                     for v in get("comb_db_mean")],
            pd_comb=[None if not np.isfinite(v) else round(float(v), 3)
                     for v in get("pd_comb")],
            R_pattern_readable_m=r_at(st["pattern_readable"]),
            R_pd_comb_90_m=r_at(st["pd_comb_90"]),
            R_pd_comb_50_m=r_at(st["pd_comb_50"]),
            R_pd_energy_90_m=r_at(st["pd_energy_90"]))

    # --- 감도(규약이 결과를 어떻게 바꾸나) ------------------------------------ #
    sens = dict(
        S2_minus_S1_db={}, S3_minus_S1_db={},
        note_ko="규약 차이는 «거리→SNR» 지도만 옮긴다 — 잣대 곡선(SNR 축)은 그대로다.")
    for c in cells:
        b = c["by_convention"]
        sens["S2_minus_S1_db"][c["cell_id"]] = round(
            b["S2"]["snr_ac_db"] - b["S1"]["snr_ac_db"], 2)
        sens["S3_minus_S1_db"][c["cell_id"]] = round(
            b["S3"]["snr_ac_db"] - b["S1"]["snr_ac_db"], 2)
    flips = []
    for c in cells:
        v = {k: c["by_convention"][k]["verdict_read_ko"] for k in ("S1", "S2", "S3")}
        if len(set(v.values())) > 1:
            flips.append(dict(cell=c["cell_id"], verdicts=v))
    sens["verdict_flips_between_conventions"] = flips

    # --- 자가검사 ------------------------------------------------------------- #
    st = {}
    st["1_no_gpu_import"] = dict(
        ok=not any(m.startswith(("sionna", "mitsuba", "drjit")) for m in sys.modules),
        loaded=[m for m in sys.modules if m.startswith(("sionna", "mitsuba", "drjit"))])
    st["2_cells_complete"] = dict(
        ok=True, n_cells=len(cells),
        note_ko="load_cells 가 n_missing·0 표본이 있는 칸을 예외로 막는다(여기 온 칸은 전부 온전)")
    # 3. 엔진 자체 거리법칙 — 가정 p 와 실측이 맞나(신호가 있는 앙각에서만 의미)
    law_ok = []
    for k, v in engine_law.items():
        strong = k.endswith("el+0") or k.startswith("ours")
        law_ok.append(dict(arm_el=k, measured_p=v["measured_p"], assumed_p=v["assumed_p"],
                           checked=strong,
                           ok=(abs(v["measured_p"] - v["assumed_p"]) < 0.1) if strong else None))
    st["3_engine_range_law"] = dict(
        ok=all(r["ok"] for r in law_ok if r["checked"]), rows=law_ok,
        note_ko="⚠앙각 −30° 의 PathSolver 팔은 반사가 사실상 없어(15 m 에서 −134 dB) "
                "자체 레벨이 어떤 법칙도 안 따른다 — 검사 대상에서 뺐고, 그 잔차는 "
                "distance 표의 residual 열로 남는다")
    # 4. 거리 눈금 한 번만
    probe = np.full(8, 1e-3)
    ratio = lb.echo_power_w(lam, probe, 150.0, 150.0) / lb.echo_power_w(lam, probe, 15.0, 15.0)
    st["4_scale_applied_once"] = dict(ok=bool(np.allclose(ratio, (15.0 / 150.0) ** 4, rtol=1e-9)),
                                      measured=float(ratio[0]), expected=(15.0 / 150.0) ** 4)
    # 5. 신호는 E 의 스칼라배 — 모양 불변
    c0 = cells[0]
    g = np.abs(c0["E_unit"]).sum() / np.abs(c0["E"]).sum()
    dev = float(np.max(np.abs(c0["E_unit"] - g * c0["E"])) / np.max(np.abs(c0["E_unit"])))
    st["5_shape_preserved"] = dict(ok=bool(dev < 1e-12), max_rel_dev=dev)
    # 6. 별칭 — 모서리만 ≡ 다 끔
    zz = np.load(LEDGER_NPZ)
    al = {}
    for el in ELS:
        a = zz[f"sionna_p4000000000_onlyedge_r15_n8192/{el_key(el)}"]
        b = zz[f"sionna_p4000000000_r15_n8192_d1/{el_key(el)}"]
        al[f"el{int(el):+d}"] = dict(
            bit_identical=bool(np.array_equal(a, b)),
            max_rel_diff=float(np.abs(a - b).max() / np.abs(b).max()))
    st["6_alias_edge_equals_off"] = dict(
        ok=all(v["max_rel_diff"] < 1e-12 for v in al.values()), rows=al,
        note_ko="비트동일은 아니고 배정밀도 반올림 수준(≤5e-16)에서 동일 — 별칭 표기는 유효")
    # 7. Pfa 실측
    pv = [pfa_meas[el][s] for el in pfa_meas for s in pfa_meas[el]]
    st["7_pfa_holdout"] = dict(ok=bool(all(0.4e-3 <= v <= 2.5e-3 for v in pv)),
                               measured=pfa_meas, target=PFA, n_ver=N_VER)
    # 8. 널 대조 — 백색의 빗살 대비 ≈ 0 dB, 리듬 몫 ≈ 해석적 널
    n8 = []
    for el in masks:
        cd = null_stat[el]["comb_contrast_db"]["mean"]
        rp = null_stat[el]["rhythm_share_pct"]["mean"]
        n8.append(dict(el=el, comb_db_mean=round(cd, 3), rhythm_pct_mean=round(rp, 2),
                       rhythm_analytic=null_stat[el]["rhythm_null_analytic_pct"],
                       ok=bool(abs(cd) < 1.0
                               and abs(rp - null_stat[el]["rhythm_null_analytic_pct"]) < 2.0)))
    st["8_null_control"] = dict(ok=all(r["ok"] for r in n8), rows=n8)
    # 9. A1(모양 얼림) ↔ A2(엔진 재계산) 어긋남 — 연장선을 어디까지 믿나
    a12 = {}
    for arm in ARMS:
        for el in ELS:
            got = [(c["range_m"], c["clean"]["comb_contrast_db"]) for c in cells
                   if c["arm"] == arm["key"] and c["el_deg"] == el]
            if len(got) < 2:
                continue
            got.sort()
            d = max(abs(v - got[0][1]) for _, v in got)
            a12[f"{arm['key']}_el{int(el):+d}"] = dict(
                clean_comb_db={str(int(R)): round(v, 1) for R, v in got},
                max_shape_drift_db=round(d, 2),
                trust_A1=bool(d <= GRID_BAND_DB))
    st["9_A1_vs_A2_shape_drift"] = dict(
        rows=a12, ok=True,
        note_ko="A1 연장선은 15 m 모양을 얼린 축이다. 드리프트가 격자 밴드(3.86 dB)를 "
                "넘는 팔(⚠PathSolver −30°)은 연장선을 «대략의 기울기» 로만 읽어라")
    # 10. 고 SNR 극한 — 잡음 섞은 잣대가 무잡음 값으로 수렴하나
    n10 = []
    for c in cells:
        hi = c["snr_curve"][-1]
        n10.append(dict(cell=c["cell_id"], snr_db=hi["snr_ac_db"],
                        noisy=round(hi["comb_db_mean"], 2),
                        clean=round(c["clean"]["comb_contrast_db"], 2),
                        ok=bool(abs(hi["comb_db_mean"] - c["clean"]["comb_contrast_db"]) < 1.5)))
    st["10_high_snr_limit"] = dict(ok=all(r["ok"] for r in n10), rows=n10)
    # 11. 규약 감도가 이론값과 맞나 — S2−S1 = −10·p·log10(R/15)
    n11 = []
    for c in cells:
        exp = -10.0 * armd[c["arm"]]["p_engine"] * math.log10(c["range_m"] / R_REF)
        got = sens["S2_minus_S1_db"][c["cell_id"]]
        n11.append(dict(cell=c["cell_id"], expected=round(exp, 2), got=got,
                        ok=bool(abs(exp - got) < 0.05)))
    st["11_convention_shift_matches_theory"] = dict(ok=all(r["ok"] for r in n11), rows=n11)
    # 12. 단조성 — 빗살 대비가 SNR 에 대해 (거의) 단조 증가
    n12 = []
    for c in cells:
        y = np.array([r["comb_db_mean"] for r in c["snr_curve"]])
        n12.append(dict(cell=c["cell_id"], max_backstep_db=round(float(np.min(np.diff(y))), 2),
                        ok=bool(np.min(np.diff(y)) > -1.0)))
    st["12_monotone_in_snr"] = dict(ok=all(r["ok"] for r in n12), rows=n12)
    st["ok"] = all(v.get("ok") for v in st.values() if isinstance(v, dict))

    # --- JSON 원장 ------------------------------------------------------------ #
    out = dict(
        _meta=dict(
            generator="benchmark/noise_distance_frame.py",
            generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                        time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
            question_ko="잡음을 실제로 넣으면 거리별로 어느 팔이 무엇까지 읽히나",
            user_quote_ko="거리 결과 보니까 잡음 모델링하면 물리 켬 버전은 아무것도 못 "
                          "읽겠는데? 잡음 모델링해서 우리 커널과 물리 끔을 비교해 줄 수 있을까?",
            frame_doc="docs/STANDARD_FRAME.md",
            inputs=[os.path.relpath(p, ROOT) for p in (LEDGER_JSON, LEDGER_NPZ, GRID_JSON)],
            reused_code=["src/rx_noise.py (RxSpec·noise_power_w·sigma_kernel_m2·앵커)",
                         "benchmark/link_budget.py (echo_power_w·잡음전력)",
                         "benchmark/detection_curves.py (탐지 통계량·문턱 교정 규약)",
                         "benchmark/build_md_atlas.py (comb_contrast_db·rhythm_share 정의)"],
            gpu_ko="⛔GPU/솔버 호출 없음 — sionna.rt·mitsuba 임포트 없음(자가검사 1)",
            two_questions_ko="(a) 탐지=표적이 있나 (b) ⭐판독=무늬가 남나 — 다른 질문이다. "
                             "세기만 크면 (a)는 통과한다(백색이어도 빗살 칸이 차오른다)",
            conventions=dict(
                scale_ko="σ̃(t;R) = (4π/λ²)|E|²·(R/15)^p_engine, c = σ_ref/⟨σ̃(15 m)⟩, "
                         "P_echo = EIRP·G·λ²·σ̃c/((4π)³R⁴) — 1/R⁴ 은 레이더 방정식에서 한 번뿐",
                anchor_scope_ko="⭐앵커는 (팔, 앙각)마다 그 팔의 15 m 판에 건다. 이 실험의 "
                                "축은 «거리» 라, 다른 축(엔진·앙각)의 레벨 차이는 일부러 "
                                "지우고 거리만 레벨을 나르게 했다. 지워진 값은 "
                                "level_erased 열에 그대로 남긴다. 헤드라인 앙각(−30°)만 "
                                "보면 앙각당/팔당 앵커는 같은 수를 낸다",
                p_engine_ko="우리 커널 p=0(E 에 1/r 확산 없음), PathSolver p=2(경로 진폭 "
                            "∝1/Σr) — 자가검사 3 에서 실측으로 확인",
                noise_ko="N = k·T0·F·PRF (rx_noise 풀캡처 v2), CN(0,N) 백색, 씨앗 고정",
                metric_read_ko="빗살 대비 comb_contrast_db — build_md_atlas 정의 그대로, "
                               "**잡음 섞은 시계열에서 다시** 계산. 백색 ≈ 0 dB",
                metric_rhythm_ko="리듬 몫 — 날개끝 상한 **위** 만 본다(교차검증용). "
                                 "⛔0 % 는 «무늬 없음» 이 아니라 «이 자리에선 못 읽음»",
                metric_detect_ko="탐지 = detection_curves 통계량(빗살·대역) + 에너지 검출기, "
                                 "문턱은 잡음 전용 30000 시행의 (1−Pfa) 분위수",
                judgement_band_ko=f"격자 흔들림 밴드 — 리듬 {GRID_BAND_RHYTHM_PP} %p · "
                                  f"세기 {GRID_BAND_DB} dB. ⚠dB 밴드는 AC 절대전력에서 잰 "
                                  f"값이라 빗살 대비(dB)에 대는 것은 보수적 대용이다",
                A1_A2_ko="A2=원장 4점(엔진 재계산), A1=15 m 모양 얼린 연장선(잡음만 바뀜)"),
            fc_hz=fc, prf_hz=prf, f_flash_hz=f_flash, drone=meta["drone"], n_slow=n,
            cpi_s=round(n / prf, 4),
            f_tip_hz_by_el={f"{el:+.0f}": round(v, 1) for el, v in ftip.items()},
            rx_spec=dict(asdict(spec), note_ko="EIRP 30 dBm 은 선언값 — 소형 모노스태틱 "
                                               "센서급(detection_curves·rx_noise 데모와 동일)"),
            noise_power_w=N_w,
            sigma_anchor=dict(sigma_ref_dbsm=ref["sigma_ref_dbsm"], **ref["provenance"]),
            seeds=dict(master=SEED, n_mc=N_MC, n_snr=N_SNR, n_null=N_NULL,
                       n_cal=N_CAL, n_ver=N_VER),
            snr_grid_db=[float(s) for s in SNR_GRID_DB],
            grid_band=dict(rhythm_pp=GRID_BAND_RHYTHM_PP, level_db=GRID_BAND_DB,
                           source="outputs/grid_convergence_check.json")),
        frame=dict(
            arms=[dict(key=a["key"], label_ko=a["label_ko"], label_en=a["label_en"],
                       engine_pattern=a["pat"], ranges_in_ledger=a["ranges"],
                       in_frame=a["in_frame"], p_engine=a["p_engine"]) for a in ARMS],
            aliases=ALIASES,
            senior_kernel_jihyuck=dict(
                status="해당 없음",
                why_ko="선배 커널(jihyuck PO) 원장은 거리 팔이 아니다 — outputs/jihyuck_po 는 "
                       "고정 슬랜트거리 63.25 m·fc 9.85 GHz·PRF 35 kHz 의 가림 등급(grade 0~7) "
                       "축이다. 이 실험의 축(3.5 GHz·PRF 19.7 kHz·거리 4점)과 겹치는 칸이 없어 "
                       "거리 비교에 넣을 수 없다"),
            cells_status=frame_status,
            missing_note_ko="⚠굴절만 팔의 거리 칸(30·60·120 m)은 지금 큐에서 계산 중이라 "
                            "비워 두었다 — 나중에 다시 돌리면 채워진다"),
        engine_range_law=engine_law,
        anchor={f"{k[0]}_el{int(k[1]):+d}": dict(
            v, level_erased_note_ko="c_total 을 곱해 이 칸의 15 m 총 σ 를 σ_ref 로 눌렀다 "
                                    "— engine_level_dbsm_like 가 눌리기 전 엔진 자체 레벨")
            for k, v in anchor.items()},
        null_control={f"{el:+.0f}": null_stat[el] for el in null_stat},
        thresholds={f"{el:+.0f}": thr[el] for el in thr},
        pfa_measured={f"{el:+.0f}": pfa_meas[el] for el in pfa_meas},
        read_lines={f"{el:+.0f}": read_line[el] for el in read_line},
        cells=[dict(cell_id=c["cell_id"], arm=c["arm"], range_m=c["range_m"],
                    el_deg=c["el_deg"], engine=c["engine"], npz_key=c["npz_key"],
                    ledger=c["ledger"], engine_level_db=c["level_db"],
                    ac_fraction=round(c["ac_frac"], 6),
                    ac_fraction_db=round(10 * math.log10(c["ac_frac"]), 2),
                    residual_after_deembed_db=round(residual_db(c), 2),
                    clean=dict(comb_contrast_db=round(c["clean"]["comb_contrast_db"], 2),
                               rhythm_share_pct=round(c["clean"]["rhythm_share_pct"], 1)),
                    snr_thresholds_db={k: (None if v is None else round(v, 2))
                                       for k, v in c["snr_thresholds_db"].items()},
                    by_convention=c["by_convention"],
                    snr_curve=[{k: (round(v, 3) if isinstance(v, float) else v)
                                for k, v in r.items()} for r in c["snr_curve"]])
               for c in cells],
        extended_range_A1=ext,
        sensitivity=sens,
        selftest=st)

    out["headline_ko"] = build_headline(out, cells, read_line)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print(f"  ✅ {OUT_JSON}")
    make_figure(out, cells, masks, ftip)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    json.dump(out, open(OUT_JSON, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(selftest_ok=st["ok"], headline=out["headline_ko"][:3]),
                     ensure_ascii=False, indent=1))
    return out


def build_headline(out, cells, read_line):
    """한 줄짜리 결론들 — 표에서 직접 뽑는다(손으로 적은 수 없음)."""
    lines = []
    by = {c["cell_id"]: c for c in cells}
    for arm in ("ours", "ps_off", "ps_phys"):
        row = []
        for R in RANGES:
            cid = f"{arm}_r{int(R)}_el-30"
            if cid not in by:
                row.append(f"{int(R)} m: —")
                continue
            b = by[cid]["by_convention"]["S1"]
            row.append(f"{int(R)} m: {b['comb_contrast_db_mean']:.0f} dB "
                       f"/ Pd {b['pd_comb']:.2f} / {b['verdict_read_ko']}")
        lines.append(f"[el −30°, S1] {arm}: " + " · ".join(row))
    for cid, e in out["extended_range_A1"].items():
        if not cid.endswith("el-30"):
            continue
        rr = e["R_pattern_readable_m"]
        lines.append(f"[A1 연장선] {cid}: 무늬 읽히는 한계 "
                     + ("정의 안 됨(15 m 에서도 못 읽음)" if rr is None else f"{rr:.0f} m")
                     + f" · Pd90 한계 "
                     + ("없음" if e["R_pd_comb_90_m"] is None else f"{e['R_pd_comb_90_m']:.0f} m"))
    for arm in ("ours", "ps_off"):
        cid = f"{arm}_r15_el+0"
        if cid in by:
            b = by[cid]["by_convention"]["S1"]
            lines.append(f"[el 0°, 15 m, S1] {arm}: 빗살 대비 {b['comb_contrast_db_mean']:.1f} dB "
                         f"({b['verdict_read_ko']}) — 앙각 0° 는 동체 정반사가 판을 덮어 "
                         f"PathSolver 쪽에 날개 무늬가 애초에 없다")
    s2 = out["sensitivity"]["S2_minus_S1_db"]
    s3 = out["sensitivity"]["S3_minus_S1_db"]
    lines.append(f"[함정·감도] 거리법칙을 안 벗기면(S2) 120 m 에서 PathSolver 는 "
                 f"{s2.get('ps_off_r120_el-30')} dB, 우리 커널은 "
                 f"{s2.get('ours_r120_el-30')} dB 움직인다 — 헤드라인 S1 은 PathSolver 에 "
                 f"**유리한** 쪽 선택이다")
    lines.append(f"[함정·감도] 총 σ 대신 움직이는 성분에 앵커를 걸면(S3) 물리 켬 팔이 "
                 f"{s3.get('ps_phys_r15_el-30')} dB 를 돌려받는다 — 물리 켬을 죽이는 것의 "
                 f"큰 몫은 «동체 받침대(DC)» 다")
    return lines


# --------------------------------------------------------------------------- #
#  그림 — 4 칸(영어). 겹침 금지·범례 1:1·단일 축
# --------------------------------------------------------------------------- #
def make_figure(out, cells, masks, ftip):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    armd = {a["key"]: a for a in ARMS}
    el = EL_MAIN
    rl = out["read_lines"][f"{el:+.0f}"]
    by = {c["cell_id"]: c for c in cells}
    order = ["ours", "ours_ptd", "ps_off", "ps_refr", "ps_phys"]

    fig, axes = plt.subplots(2, 2, figsize=(13.6, 9.4), facecolor=SURFACE)
    for ax in axes.ravel():
        ax.set_facecolor(SURFACE)
        ax.grid(True, which="both", color="0.92", lw=0.7)
        ax.set_axisbelow(True)
        ax.tick_params(colors=INK2, labelsize=9)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(INK2)

    # ── (A) range → SNR map (the convention lives here) ───────────────────── #
    ax = axes[0, 0]
    for k in order:
        a = armd[k]
        pts = sorted((c["range_m"], c["by_convention"]["S1"]["snr_ac_db"])
                     for c in cells if c["arm"] == k and c["el_deg"] == el)
        cid = f"{k}_r15_el{int(el):+d}"
        if cid in out["extended_range_A1"]:
            e = out["extended_range_A1"][cid]
            ax.plot(e["R_m"], e["snr_ac_db"], color=a["color"], ls=a["ls"], lw=1.6,
                    alpha=0.55)
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=a["color"],
                    ls="none", marker=a["marker"], ms=8, mec=SURFACE, mew=1.2)
    ax.axhline(0, color=INK2, lw=1.0, ls=":")
    ax.text(R_EXT[-1], 0, "SNR = 0 dB", fontsize=8.5, color=INK2, ha="right",
            va="bottom")
    ax.set_xscale("log")
    ax.set_xlabel("Range R [m]", color=INK)
    ax.set_ylabel("Per-sample SNR of the moving part [dB]", color=INK)
    ax.set_title("A. Link budget: range → SNR (convention S1)", fontsize=11, color=INK)

    # ── (B) metric vs SNR — convention-free ───────────────────────────────── #
    ax = axes[0, 1]
    for k in order:
        a = armd[k]
        cid = f"{k}_r15_el{int(el):+d}"
        if cid not in by:
            continue
        rows = by[cid]["snr_curve"]
        ax.plot([r["snr_ac_db"] for r in rows], [r["comb_db_mean"] for r in rows],
                color=a["color"], ls=a["ls"], lw=2.0, label=a["label_en"])
    ax.axhline(rl["white_mean_db"], color=INK2, lw=1.4, ls="--")
    ax.axhspan(rl["white_mean_db"], rl["readable_db"], color=INK2, alpha=0.12, lw=0)
    ax.text(0.02, 0.95, "shaded = white-noise line + grid band "
            f"({GRID_BAND_DB:.1f} dB)\n= cannot tell the pattern from noise",
            transform=ax.transAxes, ha="left", va="top", fontsize=8.5, color=INK2,
            bbox=dict(fc=SURFACE, ec="none", alpha=0.85, pad=2))
    ax.set_xlabel("Per-sample SNR of the moving part [dB]", color=INK)
    ax.set_ylabel("Comb contrast in noise [dB]   (white = 0 dB)", color=INK)
    ax.set_title("B. Is the pattern readable? — vs SNR (convention-free, 15 m shapes)",
                 fontsize=11, color=INK)

    # ── (C) comb contrast vs range ────────────────────────────────────────── #
    ax = axes[1, 0]
    for k in order:
        a = armd[k]
        cid = f"{k}_r15_el{int(el):+d}"
        if cid in out["extended_range_A1"]:
            e = out["extended_range_A1"][cid]
            yy = [np.nan if v is None else v for v in e["comb_db"]]
            ax.plot(e["R_m"], yy, color=a["color"], ls=a["ls"], lw=1.6, alpha=0.55)
        pts = sorted((c["range_m"], c["by_convention"]["S1"]["comb_contrast_db_mean"])
                     for c in cells if c["arm"] == k and c["el_deg"] == el)
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=a["color"],
                    ls="none", marker=a["marker"], ms=8, mec=SURFACE, mew=1.2)
    ax.axhline(rl["white_mean_db"], color=INK2, lw=1.4, ls="--")
    ax.axhspan(rl["white_mean_db"], rl["readable_db"], color=INK2, alpha=0.12, lw=0)
    ax.text(0.98, 0.95, "shaded = white-noise line (0 dB) + grid band",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=INK2,
            bbox=dict(fc=SURFACE, ec="none", alpha=0.85, pad=2))
    ax.set_xscale("log")
    ax.set_xlabel("Range R [m]", color=INK)
    ax.set_ylabel("Comb contrast in noise [dB]", color=INK)
    ax.set_title("C. Pattern readability vs range", fontsize=11, color=INK)

    # ── (D) detection probability vs range ────────────────────────────────── #
    ax = axes[1, 1]
    for k in order:
        a = armd[k]
        cid = f"{k}_r15_el{int(el):+d}"
        if cid in out["extended_range_A1"]:
            e = out["extended_range_A1"][cid]
            yy = [np.nan if v is None else v for v in e["pd_comb"]]
            ax.plot(e["R_m"], yy, color=a["color"], ls=a["ls"], lw=1.6, alpha=0.55)
        pts = sorted((c["range_m"], c["by_convention"]["S1"]["pd_comb"])
                     for c in cells if c["arm"] == k and c["el_deg"] == el)
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=a["color"],
                    ls="none", marker=a["marker"], ms=8, mec=SURFACE, mew=1.2)
    ax.axhline(0.5, color=INK2, lw=1.0, ls=":")
    ax.text(0.02, 0.47, "Pd = 0.5", transform=ax.transAxes, ha="left", va="top",
            fontsize=8.5, color=INK2)
    ax.set_xscale("log")
    ax.set_ylim(-0.03, 1.06)
    ax.set_xlabel("Range R [m]", color=INK)
    ax.set_ylabel("Detection probability Pd (comb statistic)", color=INK)
    ax.set_title(f"D. Is a moving target detected? — Pfa = {PFA:g}", fontsize=11, color=INK)

    # 범례는 그림 하나에 하나 — 선(팔)과 표식(원장 거리점)을 같은 손잡이에 묶는다
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=armd[k]["color"], ls=armd[k]["ls"], lw=2.0,
                      marker=armd[k]["marker"], ms=7, mec=SURFACE, mew=1.0,
                      label=armd[k]["label_en"]) for k in order]
    m = out["_meta"]
    fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=9.5,
               frameon=True, framealpha=0.95, edgecolor="0.85",
               bbox_to_anchor=(0.5, 0.945))
    fig.suptitle("Noise on the standard frame — what each arm can still read at range "
                 f"(elevation −{abs(int(el))}°, {m['drone']})",
                 fontsize=13.5, color=INK)
    foot = (
        "Markers = the four ledger ranges, where the engine re-computed the series (A2).   "
        "Faint lines = the 15 m shape frozen, range changes only the noise (A1).\n"
        "Signal = stored ledger slow-time series; each (arm, elevation) is levelled to the "
        f"literature σ anchor at 15 m, the engine's own spreading law is removed "
        "(ours p=0, PathSolver p=2), then one monostatic 1/R⁴.\n"
        f"EIRP {m['rx_spec']['eirp_dbm']:.0f} dBm (declared), NF {m['rx_spec']['nf_db']:.0f} dB, "
        f"PRF {m['prf_hz'] / 1e3:.1f} kHz, N = kT₀F·PRF; comb contrast re-measured on "
        f"the noisy series ({N_MC} trials, seed {SEED}).   "
        "⚠ Absolute levels are never compared across engines — the anchor removes them "
        "by construction.")
    fig.text(0.5, 0.008, foot, ha="center", va="bottom", fontsize=8.2, color=INK2,
             linespacing=1.5)
    fig.tight_layout(rect=(0, 0.075, 1, 0.895))
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"  ✅ {OUT_PNG}")


if __name__ == "__main__":
    main()
