# -*- coding: utf-8 -*-
"""
noise_main_gates.py — 잡음 **본판**의 판정·검산 장치 (설계 모듈, CPU 전용)
============================================================================

무엇을 하나
-----------
`benchmark/noise_distance_frame.py` 가 «방법 만들기 판» 이었다면 본판은 **결과판**이다.
결과판이 흔들리지 않으려면 **판정 규칙을 미리 못 박고, 검산을 자동으로 걸고, 규약을
흔들어 봐야** 한다. 이 모듈이 그 셋을 담는다 — 본판 스크립트가 `import` 해서 쓰고,
단독 실행하면 **지금 있는 원장으로 예행(dry-run)** 을 돌려 게이트가 실제로 도는지 보인다.

담긴 게이트 (본판은 전부 통과해야 수를 인용한다)
------------------------------------------------
  G1  앵커 동일성   — 두 원장의 c_anchor 가 같은 수인가 (같아야 R50 을 나란히 놓는다)
  G2  R50 교차검산  — `outputs/detection_curves.json` 과 맞나. ⭐허용오차를 **손으로 정하지
                      않고** 몬테카를로 표준편차에서 유도한다(Δ/σ 로 채점)
  G3  판정 막대     — «판정량 자체의 귀무분포 p99.9»(사용자 규칙) + 격자 재현 밴드 = **두 줄**
  G4  규약 무관 생존 — 앵커·막대·적분길이·기준안테나를 흔들고 살아남는 주장만 남긴다
  G5  운동학 게이트 — ⭐로터 산포가 빗살 격자를 부수지 않나 (본판 최대 위험, 아래 참조)
  G6  튀는 자세     — 삭제 금지·갈아끼움만(정본 규약), 고립도 + 유효 자세 수 + 상위 8 몫
  G7  앙각별 밴드   — 「전 앙각 3.861」 대신 `material_canon_0816` 의 앙각별 정본 밴드
  G8  덜 찬 칸      — n_missing>0 인 칸은 **예외로 죽지 말고 사유와 함께 제외**
  G9  A1↔A2        — 얼린 모양 연장선을, 원장에 이미 있는 **240·480 m 판**으로 검증

⭐G5 가 왜 이 라운드의 최대 위험인가
------------------------------------
빗살 대비는 «f_flash 의 정수배 ±8 Hz» 라는 **고정 격자**에서 잰다. 지금 원장의 로터
회전수 산포는 0.22 %(`legacy`)라 8번째 배음에서도 어긋남이 2.2 Hz — 격자 안이다.
재계산 큐가 로터 프리셋을 `outdoor_v2`(산포 5.3 %)로 바꾸면 어긋남이 배음 k 에서
k·6.7 Hz 가 되어 k≥2 부터 격자 밖으로 나간다. 저장된 실제 시계열로 재 보면 격자를
4 Hz 만 어긋내도 우리 커널의 빗살 대비가 42.9 → 2.5 dB 로 무너진다.
⇒ **프리셋을 바꾸면 잣대부터 다시 정의해야 한다.** 이 게이트가 그것을 막는다.

⛔GPU/솔버 없음. ⛔기존 파일 수정 없음(산출은 outputs/noise_main_gates_dryrun.json 하나).

실행:  cd /workspace/sionna && PYTHONPATH=src:benchmark \
       /workspace/.venvs/py312/bin/python benchmark/noise_main_gates.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = os.path.join(ROOT, "outputs")
LEDGER_JSON = os.path.join(OUT, "elevation_sweep_md.json")
LEDGER_NPZ = os.path.join(OUT, "elevation_sweep_md.npz")
FRAME_JSON = os.path.join(OUT, "noise_distance_frame.json")
DETCURVE_JSON = os.path.join(OUT, "detection_curves.json")
CANON_JSON = os.path.join(OUT, "material_canon_0816.json")
DRYRUN_JSON = os.path.join(OUT, "noise_main_gates_dryrun.json")

# --------------------------------------------------------------------------- #
#  0. 잣대 정의 — ⭐본판에서 **여기 말고 다른 데서 정의하지 않는다**
# --------------------------------------------------------------------------- #
DEFS = {
    "R_read": (
        "무늬 판독 한계 R_read [m] — 잡음을 섞은 시계열에서 다시 잰 빗살 대비의 "
        "**시행 평균**이 판정 막대와 만나는 거리. 막대는 G3 이 세운다. "
        "⛔한 판의 넘김이 아니라 N_MC 시행의 평균이다."),
    "R50": (
        "탐지 사거리 R50 [m] — 빗살 검출기의 탐지확률 Pd 가 **0.5** 로 내려가는 거리. "
        "Pfa = 1e−3, 문턱은 잡음 전용 시행의 (1−Pfa) 분위수. 거리 격자 위에서 "
        "**직접 측정**하고 log R 에서 선형보간. detection_curves.py 와 같은 정의."),
    "Pd90": (
        "Pd90 [m] — 같은 검출기의 Pd 가 **0.9** 로 내려가는 거리. R50 과 같은 방식."),
    "ceiling": (
        "무늬 천장 [dB] — **무잡음** 시계열의 빗살 대비. 잡음·거리·앵커·EIRP 와 무관하고, "
        "SNR 을 아무리 올려도 그 이상 안 올라간다(자가검사 10 이 수렴을 확인)."),
}

# 팔 정의 — ⭐거리 목록을 하드코딩하지 않는다. 원장을 조회해서 채운다(G8·G9).
ARM_PATTERNS = {
    "ours":     "ours_r{R}_n8192",
    "ours_ptd": "ours_ptd_r{R}_n8192",
    "ps_off":   "sionna_p4000000000_r{R}_n8192_d1",
    "ps_refr":  "sionna_p4000000000_onlyrefr_r{R}_n8192",
    "ps_phys":  "sionna_p4000000000_phys_r{R}_n8192_d1",
}
RANGE_CANDIDATES = [15.0, 30.0, 60.0, 120.0, 240.0, 480.0]
ELS = [-30.0, 0.0, -60.0]

HW_HZ = 8.0            # 빗살 반폭 [Hz] — 규약. G5 가 이 값이 아직 쓸 수 있는지 판정한다
K_BAND = (2.0, None)   # 빗살 대역 [2·f_flash, f_tip]; 위 끝은 f_tip 이 정한다


def _el_key(el: float) -> str:
    return "el+0" if el == 0 else f"el{int(el):d}"


def _load(path):
    with open(path) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
#  G8. 덜 찬 칸 — 죽지 말고 제외한다
# --------------------------------------------------------------------------- #
def inventory(ledger_json=LEDGER_JSON, ledger_npz=LEDGER_NPZ) -> dict:
    """(팔 × 거리 × 앙각) 재고 조사. 덜 찬 칸은 **사유와 함께 제외**(예외 아님).

    ⭐지금 코드(noise_distance_frame.load_cells)는 n_missing>0 이면 예외를 던져
    스크립트 전체가 죽는다. 원장에 실제로 그런 칸이 있다
    (sionna_p4000000000_r480_n8192_d1 / el−30, n_missing 5287) — 본판은 480 m 칸을
    쓰고 싶으므로 «죽음» 이 아니라 «제외» 여야 한다."""
    led, z = _load(ledger_json), np.load(ledger_npz)
    rows = {(r["engine"], float(r["el_deg"])): r for r in led["rows"]}
    cells, dropped = [], []
    for arm, pat in ARM_PATTERNS.items():
        for R in RANGE_CANDIDATES:
            eng = pat.format(R=int(R))
            for el in ELS:
                key = f"{eng}/{_el_key(el)}"
                if key not in z.files or (eng, el) not in rows:
                    continue
                row = rows[(eng, el)]
                nm = int(row.get("n_missing") or 0)
                E = np.asarray(z[key], complex)
                nz = int(np.count_nonzero(E == 0))
                rec = dict(arm=arm, range_m=R, el_deg=el, engine=eng, npz_key=key,
                           n_missing=nm, n_zero=nz, n_poses=int(row["n_poses"]),
                           f_tip_hz=float(row["f_tip_hz"]),
                           shell_mm=row.get("shell_mm"), prop_mm=row.get("prop_mm"))
                if nm or nz:
                    rec["drop_reason_ko"] = (
                        f"덜 찬 칸 — n_missing={nm}, 0 표본={nz}. 잣대를 낼 자격이 없다. "
                        "⛔예외로 죽이지 않고 제외만 한다(다른 칸은 살린다)")
                    dropped.append(rec)
                else:
                    cells.append(rec)
    have = {}
    for c in cells:
        have.setdefault((c["arm"], c["el_deg"]), []).append(c["range_m"])
    return dict(cells=cells, dropped=dropped,
                ranges_by_arm_el={f"{a}_el{int(e):+d}": sorted(v)
                                  for (a, e), v in have.items()})


# --------------------------------------------------------------------------- #
#  잣대 — 빗살 대비 (한 곳에서만 정의)
# --------------------------------------------------------------------------- #
def comb_masks(n: int, prf: float, f_flash: float, f_tip: float,
               hw_hz: float = HW_HZ, k_hi: float | None = None):
    fr = np.abs(np.fft.fftfreq(n, 1.0 / prf))
    hi = f_tip if k_hi is None else min(f_tip, k_hi * f_flash)
    band = (fr >= K_BAND[0] * f_flash) & (fr <= hi)
    k = fr / f_flash
    on = band & (np.abs(k - np.round(k)) * f_flash <= hw_hz)
    off = band & (np.abs(np.abs(k - np.floor(k)) - 0.5) * f_flash <= hw_hz)
    return on, off


def comb_contrast_db(E, n, prf, f_flash, f_tip, hw_hz=HW_HZ, k_hi=None,
                     f_flash_assumed=None) -> float | None:
    """빗살 대비 [dB] — build_md_atlas 정의 그대로. 백색 ≈ 0 dB.

    f_flash_assumed 를 주면 «잣대가 가정한 박자» 와 «실제 박자» 를 갈라 잰다(G5)."""
    fa = f_flash if f_flash_assumed is None else f_flash_assumed
    on, off = comb_masks(n, prf, fa, f_tip, hw_hz, k_hi)
    if on.sum() < 4 or off.sum() < 4:
        return None
    x = (np.asarray(E, complex) - np.mean(E)) * np.hanning(n)
    P = np.abs(np.fft.fft(x)) ** 2
    return float(10.0 * np.log10(P[on].mean() / P[off].mean()))


# --------------------------------------------------------------------------- #
#  G3. 판정 막대 — ⭐판정량 **자체**의 귀무분포 p99.9 (사용자 규칙) + 격자 밴드
# --------------------------------------------------------------------------- #
def _null_chunk(args):
    """한 덩어리의 귀무 시행 — 프로세스 풀에서 돈다(⭐CPU 가 붐비므로 병렬이 필수)."""
    m, n, prf, f_flash, f_tip, hw, k_hi, seed = args
    on, off = comb_masks(n, prf, f_flash, f_tip, hw, k_hi)
    w = np.hanning(n)
    rng = np.random.default_rng(seed)
    Z = (rng.standard_normal((m, n)) + 1j * rng.standard_normal((m, n))) / math.sqrt(2)
    Z = (Z - Z.mean(axis=1, keepdims=True)) * w
    P = np.abs(np.fft.fft(Z, axis=1)) ** 2
    return 10.0 * np.log10(P[:, on].mean(axis=1) / P[:, off].mean(axis=1))


def decision_bars(n: int, prf: float, f_flash: float, f_tip: float,
                  n_null: int = 20000, seed: int = 20260819,
                  hw_hz: float = HW_HZ, k_hi: float | None = None,
                  grid_band_db: float | None = None, batch: int = 500,
                  workers: int = 1) -> dict:
    """⭐본판의 판정 막대. **두 줄**을 낸다 — 섞으면 안 되는 두 물음이라서다.

      ① 잡음선  bar_noise  = 빗살 대비의 **귀무분포 p99.9** (Pfa 1e−3)
                 → 물음: «이 무늬가 잡음과 구별되나»  (docs/MAP_SCALING §2-b 규칙)
      ② 재현선  bar_grid   = 귀무평균 + 그 앙각의 **격자 재현 밴드**
                 → 물음: «격자를 바꿔도 남는 무늬인가»  (grid_convergence 규약)

    ⛔둘은 다른 물음이라 하나로 합치면 안 된다. 본판은 판독거리를 **구간**으로 낸다
    (①에서 먼 거리 … ②에서 가까운 거리). 지금 원장은 ② 하나만 쓰고 있었고, 그래서
    「몇 미터」가 규약 하나에 매달려 있었다.

    ⚠n_null: p99.9 를 안정적으로 뽑으려면 꼬리에 표본이 20 개는 있어야 한다
    (20,000 시행 → 20 개). 현행 4,000 은 2 개뿐이라 부족하다 —
    `build_scaled_maps.py` 가 같은 목적에 20,000 을 쓴 선례를 따른다."""
    jobs, done, i = [], 0, 0
    while done < n_null:
        m = min(batch, n_null - done)
        jobs.append((m, n, prf, f_flash, f_tip, hw_hz, k_hi, seed + 7919 * i))
        done += m
        i += 1
    if workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as ex:
            vals = np.concatenate(list(ex.map(_null_chunk, jobs)))
    else:
        vals = np.concatenate([_null_chunk(j) for j in jobs])
    rng = np.random.default_rng(seed + 1)
    mu, sd = float(vals.mean()), float(vals.std())
    p999 = float(np.quantile(vals, 0.999))
    # 꼬리 표본 수와 가우스 근사와의 차 — «막대를 믿어도 되나» 를 수로 남긴다
    n_tail = int((vals > p999).sum())
    gauss = mu + 3.0902 * sd
    out = dict(
        n_null=n_null, seed=seed, hw_hz=hw_hz, k_hi=k_hi,
        null_mean_db=mu, null_sd_db=sd,
        bar_noise_db=p999, bar_noise_rule="귀무분포 p99.9 (Pfa 1e−3) — 판정량 자체에서",
        bar_noise_gauss_db=gauss, bar_noise_gauss_minus_empirical_db=gauss - p999,
        tail_samples_above_bar=n_tail,
        bar_noise_bootstrap_sd_db=float(np.std([
            np.quantile(rng.choice(vals, vals.size, replace=True), 0.999)
            for _ in range(60)])),
        undecidable_db=mu + 2.0 * sd)
    if grid_band_db is not None:
        out.update(bar_grid_db=mu + float(grid_band_db), grid_band_db=float(grid_band_db),
                   bar_grid_rule="귀무평균 + 그 앙각의 격자 재현 밴드(material_canon 정본)")
    return out


def canon_bands(canon_json=CANON_JSON) -> dict:
    """G7 — 앙각별 정본 밴드. ⛔「전 앙각 3.861」은 **정면 값**이라 빗각에 쓰면 안 된다."""
    p = _load(canon_json)["metric_protocol"]
    return dict(comb_db_by_el=p["comb_grid_band_db_by_el"],
                ac_db_by_el=p["ac_grid_band_db_by_el"],
                rhythm_pp_by_el=p["rhythm_grid_band_pp_by_el"],
                hairline_rule_ko=p["hairline_band_rule_ko"],
                trim_rule_ko=p["trim_ruling_ko"])


# --------------------------------------------------------------------------- #
#  G2. R50 교차검산 — ⭐허용오차를 손으로 정하지 않는다
# --------------------------------------------------------------------------- #
def r50_from_pd(R_grid, pd, level=0.5):
    """Pd 곡선의 첫 하강 교차 — detection_curves.r50 과 **같은 정의**."""
    pd = np.asarray(pd, float)
    R_grid = np.asarray(R_grid, float)
    if pd[0] < level:
        return None
    below = pd < level
    if not below.any():
        return None
    i = int(np.argmax(below))
    x0, x1 = math.log10(R_grid[i - 1]), math.log10(R_grid[i])
    y0, y1 = pd[i - 1], pd[i]
    return float(10 ** (x0 + (y0 - level) / max(y0 - y1, 1e-12) * (x1 - x0)))


def r50_mc_sigma_pct(R_grid, pd, n_mc: int, level=0.5) -> float | None:
    """⭐R50 의 **몬테카를로 표준편차** [%] — 교차검산 허용오차를 여기서 유도한다.

    Pd 는 이항이라 sd(Pd) = √(p(1−p)/N). 교차점 근처의 기울기 dPd/dlogR 로 나누면
    sd(logR) 이 되고, 두 점의 오차가 섞이므로 √2 를 곱한다."""
    pd = np.asarray(pd, float)
    R_grid = np.asarray(R_grid, float)
    if pd[0] < level or not (pd < level).any():
        return None
    i = int(np.argmax(pd < level))
    dlog = math.log10(R_grid[i]) - math.log10(R_grid[i - 1])
    dpd = max(pd[i - 1] - pd[i], 1e-9)
    sd_pd = math.sqrt(level * (1 - level) / n_mc)
    sd_log = sd_pd * dlog / dpd * math.sqrt(2.0)
    return float(100.0 * (10 ** sd_log - 1.0))


def crosscheck_r50(new_r50_m: float, new_sigma_pct: float, arm_id: str,
                   detector: str = "comb", det_json=DETCURVE_JSON,
                   anchor_shift_db: float = 0.0, n_sigma: float = 3.0) -> dict:
    """⭐본판 R50 ↔ `detection_curves.json` R50 자동 교차검산.

    합격 규칙: |Δ| ≤ n_sigma·√(σ_new² + σ_ref²).  ⛔「1 % 안」 같은 손으로 고른 수를
    쓰지 않는다 — 지난번의 「1 % 안에서 맞았다」는 **가둔 게이트가 아니라 운 좋은
    표집**이었다(σ 가 이미 1.4~1.9 % 다). 옳은 보고는 Δ% 가 아니라 **Δ/σ** 다.

    anchor_shift_db: 두 원장의 앵커가 다르면 상대 거리를 10^(Δ/40) 로 환산한다.
    같으면 0 을 주고, G1 이 «정말 같은지» 를 따로 확인한다."""
    d = _load(det_json)
    row = next((a for a in d["arms"] if a["arm_id"] == arm_id), None)
    if row is None:
        return dict(ok=False, reason=f"detection_curves 에 팔 {arm_id} 가 없다")
    ref = row["R50_m"].get(detector)
    if ref is None:
        return dict(ok=False, reason=f"{arm_id}/{detector} R50 이 없다")
    ref_conv = float(ref) * 10.0 ** (anchor_shift_db / 40.0)
    sig_ref = r50_mc_sigma_pct(d["_meta"]["R_grid_m"], row[f"pd_{detector}"],
                               int(d["_meta"]["n_mc"]))
    sig_ref = 3.0 if sig_ref is None else sig_ref
    dev = 100.0 * (new_r50_m / ref_conv - 1.0)
    comb_sig = math.hypot(new_sigma_pct, sig_ref)
    return dict(ok=bool(abs(dev) <= n_sigma * comb_sig),
                arm_id=arm_id, detector=detector,
                r50_new_m=round(new_r50_m, 1), r50_ref_m=round(float(ref), 1),
                anchor_shift_db=anchor_shift_db, r50_ref_converted_m=round(ref_conv, 1),
                deviation_pct=round(dev, 2),
                sigma_new_pct=round(new_sigma_pct, 2), sigma_ref_pct=round(sig_ref, 2),
                combined_sigma_pct=round(comb_sig, 2),
                deviation_over_sigma=round(dev / comb_sig, 2),
                tolerance_pct=round(n_sigma * comb_sig, 2),
                rule_ko=f"|Δ| ≤ {n_sigma:g}σ_결합 — 허용오차는 손으로 정하지 않고 "
                        f"몬테카를로 표준편차에서 유도한다")


def anchor_identity(frame_json=FRAME_JSON, det_json=DETCURVE_JSON,
                    arm="ours", el=-30.0) -> dict:
    """G1 — 두 원장의 앵커가 **정말 같은 수**인가. 다르면 R50 을 나란히 못 놓는다."""
    f = _load(frame_json)["anchor"][f"{arm}_el{int(el):+d}"]
    dc = _load(det_json)["_meta"]["c_anchor"]["ours" if arm.startswith("ours") else "sionna"]
    a, b = float(f["c_total"]), float(dc["c_anchor"])
    diff = 10.0 * math.log10(a / b)
    return dict(ok=bool(abs(diff) < 0.01), frame_c_anchor=a, detcurve_c_anchor=b,
                diff_db=round(diff, 6),
                note_ko="같은 (엔진, el −30) 판에 걸린 앵커라 비트동일이어야 한다. "
                        "다르면 먼저 환산하고 그 값을 원장에 적는다(MAP_SCALING §4-b)")


# --------------------------------------------------------------------------- #
#  G5. ⭐운동학 게이트 — 로터 산포가 빗살 격자를 부수지 않나
# --------------------------------------------------------------------------- #
def kinematics_gate(f_flash: float, f_tip: float, sigma_s: float,
                    hw_hz: float = HW_HZ, n_sigma: float = 3.0) -> dict:
    """⭐본판 최대 위험. 로터별 회전수 산포 σ_s 는 배음 k 에서 k·σ_s·f_flash 의
    주파수 어긋남을 만든다. 그 어긋남이 빗살 반폭 hw 를 넘으면 그 배음은 «빗살 칸»
    에서 빠져나가고, 잣대는 «무늬가 없다» 고 말한다 — **무늬는 멀쩡한데** 잣대가 못 본다.

    쓸 수 있는 최대 배음:  k_max = hw / (n_sigma·σ_s·f_flash)
    잣대 대역은 [2·f_flash, f_tip] 이므로 k_max < 2 면 잣대가 **정의되지 않는다**.
    반폭을 배음마다 넓히는 길도 있지만, 넓힘이 f_flash/2 를 넘으면 빗살 칸과 그
    사이 칸이 겹쳐 잣대 자체가 무너진다 ⇒ 그때의 상한도 같이 낸다."""
    k_top = f_tip / f_flash
    spread_hz = lambda k: n_sigma * sigma_s * f_flash * k          # noqa: E731
    k_fit = float("inf") if sigma_s <= 0 else hw_hz / (n_sigma * sigma_s * f_flash)
    # 반폭을 넓혀 구제할 때의 상한: n_sigma·σ_s·f_flash·k < f_flash/2
    k_widen = float("inf") if sigma_s <= 0 else 0.5 / (n_sigma * sigma_s)
    verdict = ("고정 격자 그대로 쓴다" if k_fit >= k_top else
               ("반폭을 넓혀 구제 가능 — 대역을 k ≤ %.1f 로 좁힌다" % min(k_widen, k_top)
                if k_widen >= 2.0 else "⛔잣대 재정의 필요 — 고정 격자로는 못 잰다"))
    return dict(
        sigma_s=sigma_s, hw_hz=hw_hz, n_sigma=n_sigma,
        f_flash_hz=f_flash, f_tip_hz=f_tip, k_top=round(k_top, 2),
        spread_at_k_top_hz=round(spread_hz(k_top), 2),
        k_max_fixed_grid=round(k_fit, 2) if math.isfinite(k_fit) else None,
        k_max_widened_grid=round(k_widen, 2) if math.isfinite(k_widen) else None,
        ok=bool(k_fit >= k_top),
        rescue_ok=bool(k_widen >= 2.0),
        verdict_ko=verdict,
        note_ko="σ_s 는 원장 meta 의 rpm_per_rotor 에서 재거나 rotor_dynamics 프리셋에서 "
                "읽는다. ⭐본판 원장에는 rotor_preset 필드를 **반드시** 남긴다 — "
                "지금 행 스키마에는 없어서 어느 운동학으로 잰 수인지 사후에 못 가린다")


def sigma_s_from_ledger(ledger_json=LEDGER_JSON) -> dict:
    """원장 meta 의 rpm_per_rotor 에서 로터 간 산포를 **실측**한다(선언 아님)."""
    m = _load(ledger_json)["_meta"]
    rpm = np.asarray(m.get("rpm_per_rotor", []), float)
    if rpm.size < 2:
        return dict(ok=False, reason="원장에 rpm_per_rotor 가 없다")
    return dict(ok=True, rpm=list(map(float, rpm)),
                sigma_s=float(rpm.std(ddof=1) / rpm.mean()),
                spread_pct=round(100.0 * rpm.std(ddof=1) / rpm.mean(), 3),
                rotor_note_ko=m.get("rotor_ko"))


def detune_probe(E, n, prf, f_flash, f_tip, detunes_hz=(0, 1, 2, 4, 8),
                 hws_hz=(2, 4, 8, 16, 32)) -> dict:
    """⭐G5 의 실증 — 저장된 **실제** 시계열에서 «격자를 어긋내면 잣대가 얼마나 무너지나».
    이론이 아니라 측정이다. 본판은 이 표를 팔마다 원장에 남긴다."""
    return dict(
        by_detune_hz={str(d): comb_contrast_db(E, n, prf, f_flash, f_tip,
                                               f_flash_assumed=f_flash + d)
                      for d in detunes_hz},
        by_halfwidth_hz={str(h): comb_contrast_db(E, n, prf, f_flash, f_tip, hw_hz=h)
                         for h in hws_hz},
        by_k_hi={str(k): comb_contrast_db(E, n, prf, f_flash, f_tip, k_hi=k)
                 for k in (3.0, 4.0, 6.0)})


# --------------------------------------------------------------------------- #
#  G6. 튀는 자세(이상값) — ⛔삭제 금지, 갈아끼움만 (material_canon 정본 규약)
# --------------------------------------------------------------------------- #
def pose_outlier_grades(E) -> dict:
    """자세열의 이상값 등급. ⭐고립도(최대÷둘째)만으로는 **여럿이 함께 튀는 칸**을
    못 잡는다(정본 판정) — 유효 자세 수와 상위 8 자세 몫을 같이 낸다."""
    p = np.abs(np.asarray(E, complex) - np.mean(E)) ** 2
    s = np.sort(p)[::-1]
    tot = float(p.sum()) or 1e-300
    n_eff = float(tot ** 2 / np.sum(p ** 2))            # 참여 자세 수(participation ratio)
    n_eff_min, top8_max = 256.0, 5.0        # ⭐문턱의 근거는 아래 rule_ko
    top8 = 100.0 * float(s[:8].sum()) / tot
    return dict(n_poses=int(p.size),
                isolation=float(s[0] / max(s[1], 1e-300)),
                n_effective_poses=round(n_eff, 1),
                top8_share_pct=round(top8, 3),
                max_over_median=round(float(s[0] / max(np.median(p), 1e-300)), 1),
                n_eff_min=n_eff_min, top8_max_pct=top8_max,
                readable=bool(n_eff >= n_eff_min and top8 < top8_max),
                rule_ko="⛔삭제 솎기 금지(뒤가 당겨져 배음선이 번진다) — 이웃 평균 "
                        "**갈아끼움** 또는 균일 재표집(반쪽·짝/홀)으로만 검사한다. "
                        "⭐문턱: 유효 자세 ≥256(=8192 의 1/32, 빗살 대역 배음 8개를 "
                        "자세 32개씩으로 받치는 최소선) · 상위 8 자세 몫 <5 %. "
                        "고립도만 보면 «여럿이 함께 튀는 칸» 을 놓친다(정본 판정)")


def replace_outlier(E, k: int = 1):
    """정본 솎기 — 가장 튀는 k 자세를 **이웃 평균으로 갈아끼운다**(삭제 아님)."""
    E = np.asarray(E, complex).copy()
    p = np.abs(E - E.mean()) ** 2
    for i in np.argsort(p)[::-1][:k]:
        a, b = E[(i - 1) % E.size], E[(i + 1) % E.size]
        E[i] = 0.5 * (a + b)
    return E


def uniform_resamples(E):
    """균일 재표집 — 앞반·뒷반·짝수·홀수. 잣대가 표집에 얼마나 흔들리나."""
    E = np.asarray(E, complex)
    h = E.size // 2
    return dict(first_half=E[:h], second_half=E[h:], even=E[0::2], odd=E[1::2])


# --------------------------------------------------------------------------- #
#  G4. 규약 무관 생존 검사
# --------------------------------------------------------------------------- #
#  ⭐선례: 앵커 규약을 바꾸니 엔진 간 배수가 12배 → 1.3배로 변했다. 그때 살아남은
#  주장은 «물리 켬의 무늬 천장» 하나뿐이었다. 그래서 본판은 주장을 **미리 등급으로
#  나눠 놓고** 규약 격자 위에서 전수 채점한다.
CLAIM_CLASSES = {
    "A_convention_free": (
        "규약과 **구조적으로** 무관 — 무잡음 잣대에서 나오는 양. 앵커·EIRP·잡음지수·"
        "막대·거리·capture 어느 것도 안 들어간다. 예: 무늬 천장, 천장의 팔 간 차이."),
    "B_bar_dependent": (
        "막대에만 의존 — 판독거리의 **순서**·**배수**. 막대를 바꾸면 거리는 같이 움직이지만 "
        "팔 사이 비는 거의 유지된다."),
    "C_budget_dependent": (
        "링크버짓 전체에 의존 — «몇 미터». EIRP·이득·NF·PRF·capture 가 전부 들어간다. "
        "⛔이 등급의 수는 **가정과 함께**만 인용한다."),
}


def survival_matrix(claims: list[dict]) -> dict:
    """주장마다 «어느 규약을 흔들면 뒤집히나» 를 채점한 표를 만든다.

    claims 원소: dict(id, text_ko, klass, values_by_variant={변형이름: 수})
    변형 전부에서 부호·순서가 유지되면 survives=True."""
    out = []
    for c in claims:
        v = c["values_by_variant"]
        vals = [x for x in v.values() if x is not None]
        if not vals:
            out.append(dict(**{k: c[k] for k in ("id", "text_ko", "klass")},
                            survives=None, reason="값 없음"))
            continue
        same_sign = all(np.sign(x) == np.sign(vals[0]) for x in vals)
        spread = max(vals) - min(vals)
        rel = spread / max(abs(np.mean(vals)), 1e-12)
        out.append(dict(id=c["id"], text_ko=c["text_ko"], klass=c["klass"],
                        values_by_variant=v, min=min(vals), max=max(vals),
                        spread=round(spread, 3), spread_rel=round(rel, 3),
                        same_sign=bool(same_sign),
                        survives=bool(same_sign and rel <= c.get("tol_rel", 0.25))))
    return dict(classes=CLAIM_CLASSES, claims=out,
                n_survive=sum(1 for r in out if r["survives"]),
                n_total=len(out))


# --------------------------------------------------------------------------- #
#  G9. A1 ↔ A2 — 원장에 이미 있는 240·480 m 판으로 연장선을 검증
# --------------------------------------------------------------------------- #
def a1_a2_drift(inv: dict, ledger_npz=LEDGER_NPZ, prf=19700.0, f_flash=126.66666666666667,
                el=-30.0, band_db_by_el=None) -> dict:
    """⭐연장선(A1)은 15 m 모양을 얼린 축이다. 원장에 30·60·120·**240·480 m** 판이
    있으므로 «얼린 모양이 그 거리에서도 맞나» 를 **직접** 잴 수 있다.
    판독 한계(554 m 언저리)에 가장 가까운 검증점이 480 m 다 — 본판은 이것을 쓴다."""
    z = np.load(ledger_npz)
    rows = {}
    for c in inv["cells"]:
        if c["el_deg"] != el:
            continue
        E = np.asarray(z[c["npz_key"]], complex)
        v = comb_contrast_db(E, E.size, prf, f_flash, c["f_tip_hz"])
        rows.setdefault(c["arm"], {})[int(c["range_m"])] = None if v is None else round(v, 2)
    band = (band_db_by_el or {}).get(f"{int(el):+d}".replace("+0", "+0"), None)
    out = {}
    for arm, d in rows.items():
        if 15 not in d or len(d) < 2:
            continue
        base = d[15]
        drift = max(abs(v - base) for v in d.values() if v is not None)
        out[arm] = dict(clean_comb_db=d, max_shape_drift_db=round(drift, 2),
                        farthest_ledger_range_m=max(d),
                        trust_A1=None if band is None else bool(drift <= band))
    return dict(rows=out, band_db=band, el_deg=el,
                note_ko="드리프트가 그 앙각의 격자 밴드를 넘는 팔은 A1 연장선을 «기울기» "
                        "로만 읽는다. ⭐240·480 m 판이 있는 팔은 A2 를 헤드라인으로 쓰고 "
                        "A1 은 보조로 내린다")


# --------------------------------------------------------------------------- #
#  ⭐사전등록 채점기 — 재계산 뒤 «맞았나 틀렸나» 를 코드가 매긴다
# --------------------------------------------------------------------------- #
def score_prereg(prereg_path: str, observed: dict) -> dict:
    """사전등록 JSON 의 예측 × 실제 관측을 대조해 채점한다.

    observed: {예측 id: 관측값}. 예측마다 `bracket`(하한, 상한)이 있고 관측이 그 안이면
    hit. `direction` 만 있는 예측은 부호만 채점한다. ⛔예측이 «모른다» 로 등록된 항목은
    관측을 적되 hit/miss 를 매기지 않는다 — **모른다고 미리 말한 것은 틀린 것이 아니다**."""
    pre = _load(prereg_path)
    rows, hit, miss, unscored = [], 0, 0, 0
    for p in pre["predictions"]:
        pid = p["id"]
        if pid not in observed or observed[pid] is None:
            rows.append(dict(id=pid, status="관측 없음", **{k: p[k] for k in ("what_ko",)}))
            continue
        v = float(observed[pid])
        if p.get("unknown"):
            rows.append(dict(id=pid, what_ko=p["what_ko"], observed=v,
                             status="채점 안 함(모른다고 미리 등록)"))
            unscored += 1
            continue
        lo, hi = p["bracket"]
        ok = (lo <= v <= hi)
        sign_ok = (np.sign(v - p.get("pivot", 0.0)) == np.sign(p.get("direction", 0.0))
                   if p.get("direction") else None)
        rows.append(dict(id=pid, what_ko=p["what_ko"], predicted=p.get("point"),
                         bracket=[lo, hi], observed=v, hit=bool(ok),
                         direction_ok=None if sign_ok is None else bool(sign_ok),
                         miss_by=0.0 if ok else round(min(abs(v - lo), abs(v - hi)), 3)))
        hit += int(ok)
        miss += int(not ok)
    return dict(prereg=os.path.relpath(prereg_path, ROOT),
                scored=hit + miss, hit=hit, miss=miss, unscored=unscored,
                hit_rate=None if hit + miss == 0 else round(hit / (hit + miss), 3),
                rows=rows,
                rule_ko="⭐채점은 사전등록 파일을 **고치지 않고** 한다. 예측이 틀리면 "
                        "틀린 대로 남기고 원인을 원장에 적는다 — 사후에 브래킷을 넓히면 "
                        "사전등록이 아니다")


# --------------------------------------------------------------------------- #
#  예행(dry-run) — 지금 원장으로 게이트를 실제로 돌려 본다
# --------------------------------------------------------------------------- #
def dry_run(n_null: int = 1500, workers: int = 1) -> dict:
    t0 = time.time()
    led = _load(LEDGER_JSON)["_meta"]
    prf, f_flash = float(led["prf_hz"]), float(led["f_flash_hz"])
    inv = inventory()
    bands = canon_bands()
    frame = _load(FRAME_JSON)
    z = np.load(LEDGER_NPZ)

    # G5 — 지금 원장의 운동학, 그리고 재계산 후보 프리셋
    sig_now = sigma_s_from_ledger()
    f_tip30 = 1102.4
    kin = {}
    for name, ss in [("legacy(현행 원장 실측)", sig_now.get("sigma_s", 0.0022)),
                     ("outdoor_v2 σs=5.3%", 0.053),
                     ("outdoor_v2_eff σs=5.757%", 0.05757)]:
        kin[name] = kinematics_gate(f_flash, f_tip30, ss)

    # G5 실증 — 실제 시계열의 격자 어긋남 감도
    probes = {}
    for arm in ("ours", "ps_off", "ps_refr", "ps_phys"):
        c = next((x for x in inv["cells"] if x["arm"] == arm and x["range_m"] == 15
                  and x["el_deg"] == -30.0), None)
        if c:
            E = np.asarray(z[c["npz_key"]], complex)
            probes[arm] = detune_probe(E, E.size, prf, f_flash, c["f_tip_hz"])

    # G3 — 막대 두 줄(예행은 표본을 줄여 빠르게; 본판은 20,000)
    bar30 = decision_bars(8192, prf, f_flash, f_tip30, n_null=n_null, workers=workers,
                          grid_band_db=bands["comb_db_by_el"]["-30"])
    bar00 = decision_bars(8192, prf, f_flash, 1272.9, n_null=n_null, workers=workers,
                          grid_band_db=bands["comb_db_by_el"]["+0"])

    # G2 — 교차검산(현행 프레임 값으로 예행)
    fr_cells = {c["cell_id"]: c for c in frame["cells"]}
    xchecks = []
    det = _load(DETCURVE_JSON)
    for arm, arm_id in (("ours", "ours_el-30"), ("ps_off", "sionna_el-30")):
        cid = f"{arm}_r15_el-30"
        if cid not in fr_cells:
            continue
        e = frame["extended_range_A1"].get(cid, {})
        r50 = e.get("R_pd_comb_50_m")
        if r50 is None:
            continue
        sig = r50_mc_sigma_pct(det["_meta"]["R_grid_m"],
                               next(a["pd_comb"] for a in det["arms"]
                                    if a["arm_id"] == arm_id), frame["_meta"]["seeds"]["n_mc"])
        xchecks.append(crosscheck_r50(r50, sig or 3.0, arm_id))

    # G6 — 이상값 등급(헤드라인 칸)
    grades = {}
    for arm in ("ours", "ps_off", "ps_phys"):
        c = next((x for x in inv["cells"] if x["arm"] == arm and x["range_m"] == 15
                  and x["el_deg"] == -30.0), None)
        if c:
            grades[arm] = pose_outlier_grades(np.asarray(z[c["npz_key"]], complex))

    out = dict(
        _meta=dict(generator="benchmark/noise_main_gates.py (dry-run)",
                   generated_kst=time.strftime(
                       "%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 9 * 3600)) + " (UTC+9)",
                   role_ko="잡음 **본판**이 쓸 판정·검산 장치의 예행. 지금 원장(잠정)으로 "
                           "게이트가 실제로 도는지만 본다 — 여기 나온 수는 결과가 아니다",
                   gpu_ko="⛔GPU/솔버 임포트 없음",
                   definitions=DEFS),
        G8_inventory=dict(ranges_by_arm_el=inv["ranges_by_arm_el"],
                          dropped=[{k: v for k, v in d.items() if k != "npz_key"}
                                   for d in inv["dropped"]]),
        G7_canon_bands=bands,
        G5_kinematics=dict(measured_now=sig_now, gates=kin, detune_probe=probes),
        G3_bars=dict(el_minus30=bar30, el_plus0=bar00),
        G1_anchor=anchor_identity(),
        G2_crosscheck_r50=xchecks,
        G6_pose_outliers=grades,
        G9_a1_a2=a1_a2_drift(inv, band_db_by_el={"-30": bands["comb_db_by_el"]["-30"]}),
    )
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    with open(DRYRUN_JSON, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--null", type=int, default=1500,
                    help="예행의 귀무 시행 수(본판 정본은 20000)")
    ap.add_argument("--workers", type=int, default=1)
    args = ap.parse_args()
    o = dry_run(n_null=args.null, workers=args.workers)
    print(f"  ✅ {DRYRUN_JSON}")
    print("\n[G8] 팔·앙각별 원장 거리점")
    for k, v in o["G8_inventory"]["ranges_by_arm_el"].items():
        print(f"   {k:18s} {v}")
    for d in o["G8_inventory"]["dropped"]:
        print(f"   ⛔제외 {d['engine']} el{d['el_deg']:+.0f} — n_missing={d['n_missing']}")
    print("\n[G5] 운동학 게이트")
    print(f"   현행 원장 실측 로터 산포 {o['G5_kinematics']['measured_now']['spread_pct']} %")
    for k, v in o["G5_kinematics"]["gates"].items():
        print(f"   {k:26s} k_max(고정격자)={v['k_max_fixed_grid']} / 대역상단 k={v['k_top']}"
              f"  → {v['verdict_ko']}")
    print("\n[G3] 판정 막대 두 줄 (el −30, 예행 4000 시행)")
    b = o["G3_bars"]["el_minus30"]
    print(f"   귀무 평균 {b['null_mean_db']:+.3f} dB · sd {b['null_sd_db']:.3f}")
    print(f"   ① 잡음선 p99.9 = {b['bar_noise_db']:.3f} dB  (가우스 근사와 차 "
          f"{b['bar_noise_gauss_minus_empirical_db']:+.3f} dB, 부트스트랩 sd "
          f"{b['bar_noise_bootstrap_sd_db']:.3f})")
    print(f"   ② 재현선 = 귀무평균 + 격자밴드 {b['grid_band_db']:.3f} = {b['bar_grid_db']:.3f} dB")
    print("\n[G2] R50 교차검산")
    for x in o["G2_crosscheck_r50"]:
        print(f"   {x['arm_id']:14s} Δ={x['deviation_pct']:+.2f} %  σ={x['combined_sigma_pct']:.2f} %"
              f"  Δ/σ={x['deviation_over_sigma']:+.2f}  허용 ±{x['tolerance_pct']:.2f} %  "
              f"{'통과' if x['ok'] else '⛔불합격'}")
    print("\n[G9] A1↔A2 (el −30)")
    for a, r in o["G9_a1_a2"]["rows"].items():
        print(f"   {a:9s} {r['clean_comb_db']}  드리프트 {r['max_shape_drift_db']} dB  "
              f"최원 원장점 {r['farthest_ledger_range_m']} m  trust_A1={r['trust_A1']}")
    print("\n[G6] 튀는 자세 등급 (15 m, el −30)")
    for a, g in o["G6_pose_outliers"].items():
        print(f"   {a:9s} 고립도 {g['isolation']:.3f}  유효자세 {g['n_effective_poses']}  "
              f"상위8몫 {g['top8_share_pct']} %  읽을만함={g['readable']}")
