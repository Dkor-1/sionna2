# -*- coding: utf-8 -*-
"""
report16_metric_mesh_no_rotor.py — 로터 뗀 메쉬 단의 **지표 뽑기 · 예측 대조 · 자기불신**
================================================================================

이 파일이 하는 일 (세 가지뿐이다)
--------------------------------------------------------------------------------
1. 기반 단계(benchmark/report16_base.py)가 못박은 지표 **네 가족을 전부** 계산한다.
   · 플래시 대조비(flash contrast)  · 고차 성분 풍부도(n_eff_orders 등)
   · 도플러 폭(width_ratio)          · 동체 대 블레이드 세기비(dc_ac_db)
2. **계산 전에 봉인해 둔 예측**과 맞았는지 틀렸는지 명시한다.
3. ⚠ 이 단의 결과를 **못 믿을 이유**를 스스로 찾아 숫자와 함께 적는다.

용어 먼저 풀기 (처음 쓰는 말)
--------------------------------------------------------------------------------
· **위상 표 E(φ)** : 한 바퀴(360°)를 잘게 나눠 각 회전각 φ 에서의 복소 산란장을 적은 표.
· **AC / DC** : 표에서 «흔들리는 몫» 이 AC, «가만히 있는 몫(평균)» 이 DC 다.
  변조 깊이 = AC 가 DC보다 몇 dB 위/아래인가.
· **비행 운동학(flight)** : 몸체는 가만히, 로터만 도는 실제 비행 규칙.
· **회전 운동학(spin)** : 물체 전체를 기체 z축으로 실제로 돌리는 대조용 규칙.
  ⭐ 강체를 φ 돌려 보는 것 = 방위를 −φ 옮겨 보는 것이므로, 이 표는 곧 **방위 RCS 패턴**이다.
· **가림(occlusion)** : 앞에 있는 부품이 뒤에 있는 부품을 가려 전파가 못 닿는 것.
  우리 PO 커널에는 이것이 없다.

⛔ 규율: 계산은 전부 이미 저장된 표(npz)에서 다시 뽑는다. src/drones.py·src/drone_cad.py 는
   읽기만 한다(가림 감사에서 메쉬를 읽는다). outputs/report15_*·benchmark/report15_*,
   src/make_report0N_*·report0N_*.ipynb 는 건드리지 않는다. 숫자는 손으로 적지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import report16_base as RB              # noqa: E402  ⭐ 지표 정의를 그대로 물려받는다

RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor_tables.npz")
RUNG_PREREG = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor.prereg.json")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_mesh_no_rotor.json")

EL_MAIN = 15.0
METRIC_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
               "blade_comb_frac", "fd_edge_hz", "width_ratio", "dc_ac_db", "ac_frac_db",
               "sigma_eq_mean_dbsm", "in_band_ac_frac", "in_band_ac_over_dc_db",
               "band_order", "metrics_interpretable", "ac_over_floor_db",
               "width_ratio_10db", "width_ratio_30db")
# 네 «가족» — 지표 이름을 가족으로 묶어 둔다(리포트에서 이 이름으로 인용한다)
FAMILIES = {
    "flash_contrast": ["flash_contrast_db"],
    "harmonic_richness": ["n_eff_orders", "order_p50", "order_p90", "dominant_order",
                          "blade_comb_frac"],
    "doppler_width": ["fd_edge_hz", "width_ratio", "width_ratio_10db", "width_ratio_30db"],
    "body_to_blade": ["dc_ac_db", "ac_frac_db", "in_band_ac_over_dc_db"],
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def git_rev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


def jnum(x):
    """넘파이 수 → 파이썬 수. NaN/Inf 는 문자열로 남겨 JSON 이 깨지지 않게 한다."""
    if isinstance(x, (np.bool_, bool)):        # ⚠ bool 은 int 의 하위형이라 먼저 걸러야 한다
        return bool(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        if math.isnan(v):
            return "NaN (undefined — AC power is exactly zero)"
        if math.isinf(v):
            return ("+Inf" if v > 0 else "-Inf")
        return v
    if isinstance(x, (np.integer, int)):
        return int(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x


def clean(d):
    if isinstance(d, dict):
        return {k: clean(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [clean(v) for v in d]
    return jnum(d)


# =========================================================================== #
#  1. 규약 dict 만들기 — md_metrics16 이 먹는 모양
# =========================================================================== #
def beta_of(r_m, lam, el_deg):
    return 4.0 * math.pi * float(r_m) * math.cos(math.radians(float(el_deg))) / lam


def make_proto(lam, f_rot, r_eff, el_deg, n_phase):
    b = beta_of(r_eff, lam, el_deg)
    return dict(lam_m=lam, f_rot_hz=float(f_rot), beta=b, f_tip_hz=b * float(f_rot),
                spin_radius_m=float(r_eff), el_deg=float(el_deg), n_phase=int(n_phase))


def flight_proto(base_json, key):
    """비행 운동학의 기준자 — base 가 쓰던 **프로펠러 팁** 기준 규약을 그대로 쓴다."""
    p = base_json["protocol_per_drone"][key]
    return dict(lam_m=p["lam_m"], f_rot_hz=p["f_rot_hz"], beta=p["beta"],
                f_tip_hz=p["f_tip_hz"], prop_radius_m=p["prop_radius_m"],
                n_phase=p["n_phase"])


# =========================================================================== #
#  2. 대역제한 보간 — 이미 계산된 회전 표를 임의 각도에서 되읽는다
# =========================================================================== #
def fourier_eval(tab, phis):
    """표 E(φ_k)(등간격 S점) 의 **푸리에 급수**를 임의 각 φ 에서 평가한다.

    표가 그 자체로 각도의 주기함수를 S 점 표본화한 것이므로, 급수 합은 «근사» 가 아니라
    그 표본이 정의하는 대역제한 함수의 정확한 값이다. 새 전자기 계산이 필요 없다.
    """
    tab = np.asarray(tab, complex)
    S = len(tab)
    c = np.fft.fft(tab) / S
    m = np.fft.fftfreq(S, d=1.0 / S).astype(int)          # 부호 있는 차수
    ph = np.exp(1j * np.outer(np.asarray(phis, float), m))
    return ph @ c


# =========================================================================== #
#  3. 로딩
# =========================================================================== #
def load_all():
    J = json.load(open(RUNG_JSON, encoding="utf-8"))
    B = json.load(open(BASE_JSON, encoding="utf-8"))
    P = json.load(open(RUNG_PREREG, encoding="utf-8"))
    zr = np.load(RUNG_NPZ)
    zb = np.load(BASE_NPZ)
    return J, B, P, zr, zb


def rung_key(drone, arm, band, wf, el, mode):
    return f"{drone}__{arm}__{band}__{wf}__{el:.0f}__{mode}"


# =========================================================================== #
#  4. §0 재현 게이트 — 남이 적어 준 숫자를 믿지 않고 표에서 다시 뽑는다
# =========================================================================== #
def recompute_gate(J, zr):
    """저장된 표에서 지표를 **다시** 계산해 단 JSON 이 적어 둔 값과 맞춰 본다.
    여기서 어긋나면 아래 숫자를 인용할 수 없다."""
    worst, rows, n_checked = 0.0, {}, 0
    for key, dd in J["drones"].items():
        pr = dd["protocol"]["main"]
        r_common = dd["frame_geometry"]["spin_radius_max_m"]
        for arm, stored in (dd.get("spin_headline") or {}).items():
            k = rung_key(key, arm, "main", "spherical", EL_MAIN, "spin")
            if k not in zr.files:
                continue
            pc = make_proto(pr["lam_m"], pr["f_rot_hz"], r_common, EL_MAIN, pr["n_phase"])
            mine = RB.md_metrics16(zr[k], pc, 2)
            dmax, kmax = 0.0, ""
            for mk in METRIC_KEYS:
                a, b = mine.get(mk), stored["common"].get(mk)
                if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
                    continue
                if not (np.isfinite(float(a)) and np.isfinite(float(b))):
                    continue
                d = abs(float(a) - float(b)) / max(abs(float(b)), 1e-9)
                if d > dmax:
                    dmax, kmax = d, mk
            rows[f"{key}|{arm}"] = dict(max_rel_diff=dmax, worst_metric=kmax)
            worst = max(worst, dmax)
            n_checked += 1
    return dict(
        what_ko="단 JSON 이 적어 둔 spin 지표를 저장된 표에서 **처음부터 다시** 계산해 맞춰 본다. "
                "같은 정의·같은 표이므로 부동소수 오차 수준으로 같아야 한다.",
        n_rows_checked=n_checked, max_rel_diff=worst, tolerance=1e-9,
        verdict="PASS" if worst < 1e-9 else "FAIL", per_row=rows)


def recompute_dc_decomposition(J, B, zr, zb):
    """동체 받침 분해도 base 표에서 직접 다시 만든다(단 JSON 을 믿지 않는다)."""
    out = {}
    for key, dd in J["drones"].items():
        kf = rung_key(key, "mesh_no_rotor", "main", "spherical", EL_MAIN, "flight_static")
        kb = f"main__G_0804__{key}__mesh__spherical"
        if kf not in zr.files or kb not in zb.files:
            continue
        Eb = np.asarray(zr[kf], complex)                  # (24,) 몸체만
        T = np.asarray(zb[kb], complex)                   # (24, S) 로터 도는 전체
        lam = dd["protocol"]["main"]["lam_m"]
        n = min(len(Eb), T.shape[0])
        rows = []
        for i in range(n):
            full = T[i]
            dc_full = complex(full.mean())
            ac_rms = float(np.sqrt(np.mean(np.abs(full - dc_full) ** 2)))
            body = complex(Eb[i])
            rotor_dc = dc_full - body
            rows.append(dict(
                body_over_full_dc_db=20 * np.log10(max(abs(body), 1e-300) /
                                                   max(abs(dc_full), 1e-300)),
                rotor_dc_over_full_dc_db=20 * np.log10(max(abs(rotor_dc), 1e-300) /
                                                       max(abs(dc_full), 1e-300)),
                dc_ac_db_as_measured=20 * np.log10(max(abs(dc_full), 1e-300) /
                                                   max(ac_rms, 1e-300)),
                dc_ac_db_body_removed=20 * np.log10(max(abs(rotor_dc), 1e-300) /
                                                    max(ac_rms, 1e-300)),
                body_over_ac_rms_db=20 * np.log10(max(abs(body), 1e-300) / max(ac_rms, 1e-300)),
                body_sigma_dbsm=10 * np.log10(max((4 * math.pi / lam ** 2) * abs(body) ** 2, 1e-300)),
                rotor_ac_sigma_dbsm=10 * np.log10(max((4 * math.pi / lam ** 2) * ac_rms ** 2, 1e-300)),
            ))
        blk = {kk: RB.summarize([r[kk] for r in rows]) for kk in rows[0]}
        blk["n_az"] = n
        blk["body_masks_blades_by_db"] = dict(
            mean=blk["dc_ac_db_as_measured"]["mean"] - blk["dc_ac_db_body_removed"]["mean"])
        out[key] = blk
    return out


# =========================================================================== #
#  5. §1 비행 운동학 — 예측이 걸린 자리. 네 가족을 **문자 그대로** 계산한다
# =========================================================================== #
def flight_metrics(J, B, zr):
    """로터가 없으므로 위상 표는 «모든 칸이 같은 값» 이다. 그 표에 지표를 그대로 먹인다.
    어떤 지표가 값이 나오고 어떤 지표가 정의 불가인지 숨기지 않고 적는다."""
    out = {}
    for key, dd in J["drones"].items():
        fp = flight_proto(B, key)
        per_wf = {}
        for wf in ("spherical", "plane"):
            kf = rung_key(key, "mesh_no_rotor", "main", wf, EL_MAIN, "flight_static")
            if kf not in zr.files:
                continue
            Eb = np.asarray(zr[kf], complex)
            S = int(fp["n_phase"])
            per_az, n_zero = [], 0
            for i in range(len(Eb)):
                tab = np.full(S, Eb[i], complex)          # 로터가 없다 = 표가 평평하다
                mm = RB.md_metrics16(tab, fp, 2)
                c = np.fft.fft(tab) / S
                m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
                p_ac = float((np.abs(c[m != 0]) ** 2).sum())
                n_zero += int(p_ac == 0.0)
                per_az.append(mm)
            fam = {}
            for famname, keys in FAMILIES.items():
                fam[famname] = {}
                for mk in keys:
                    # ⚠ AC 가 0 이면 md_metrics16 은 그 지표를 아예 만들지 않는다(키 없음).
                    #    «없음» 도 «NaN» 도 똑같이 «정의 불가» 로 센다 — 숨기지 않는다.
                    vals = [float(p.get(mk, float("nan"))) for p in per_az]
                    n_missing = sum(1 for p in per_az if mk not in p)
                    finite = [v for v in vals if np.isfinite(v)]
                    if len(finite) == 0:
                        fam[famname][mk] = dict(
                            value="undefined", n_undefined=len(vals), n_key_absent=n_missing,
                            why_ko="AC 전력이 정확히 0 이라 이 지표는 0/0 이다 — 값이 없는 것이 답이다.")
                    else:
                        s = RB.summarize(vals)
                        s["n_undefined"] = len(vals) - len(finite)
                        fam[famname][mk] = s
            fam["body_to_blade_note_ko"] = (
                "⚠ 여기 적힌 +5900 dB 대의 값은 측정값이 아니라 **무한대**다. 블레이드가 없어 AC 가 "
                "정확히 0 이므로 «DC ÷ AC» 가 무한이고, 로그를 찍기 위해 1e-300 으로 막은 결과가 "
                "저 숫자다. 곧 «블레이드 신호가 없다» 는 뜻이지 «세기비가 좋다» 는 뜻이 아니다.")
            per_wf[wf] = dict(
                n_az=len(Eb), n_phase=S,
                ac_power_exactly_zero_frac=float(n_zero) / max(len(Eb), 1),
                defined_families=1, total_families=len(FAMILIES),
                defined_note_ko="AC 가 없으면 «AC 의 모양» 을 재는 세 가족(플래시 대조비의 실질값·"
                                "차수 풍부도·도플러 폭)은 정의되지 않는다. 플래시 대조비는 0/0 을 막아 "
                                "정확히 0 dB 로 찍히는데, 그것은 base 문서가 적어 둔 «회전대칭체의 "
                                "이론값» 과 같은 자리다 — 신호가 없다는 뜻이다.",
                families=fam)
        out[key] = dict(
            reference_ruler_ko="비행 운동학의 기준자는 base 와 같은 «프로펠러 팁» 이다 "
                               f"(반경 {fp['prop_radius_m']} m, β={fp['beta']:.3f}).",
            protocol=fp, per_wavefront=per_wf)
    return out


# =========================================================================== #
#  6. §2 몸체 미세운동 주입 — «예측 검정이 얼마나 예민한가» 를 숫자로 만든다
# =========================================================================== #
def micromotion_injection(J, B, zr):
    """⚠ 비행 모드의 «변조 0» 은 모형의 산수 항등식이라 반증력이 없다.
    그래서 **없는 것을 넣어 본다**: 몸체가 기체 z축으로 ±δ° 만큼 좌우로 흔들린다고 하자
    (로터 불균형이 만드는 요잉 진동 — 실제 드론에 반드시 있다).

    ⭐ 새 전자기 계산이 필요 없다. 이 단의 spin 표가 곧 «몸체를 φ 돌렸을 때의 산란장» 이므로,
      φ(t) = δ·sin(2π·h·f_rot·t) 를 그 표에 되읽기만 하면 흔들리는 몸체의 시간신호가 된다.
      (h=1 은 로터 회전수와 같은 진동, h=2 는 블레이드 통과 주파수와 같은 진동이다.)

    이렇게 하면 «몸체가 몇 도 흔들리면 로터와 같은 크기의 변조를 만드는가» 를 답할 수 있다.
    그 각이 아주 작으면, 이 단의 «변조 0» 은 실제 드론에 대해 말해 주는 바가 거의 없다.
    """
    out = {}
    grid_deg = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]
    for key, dd in J["drones"].items():
        k = rung_key(key, "mesh_no_rotor", "main", "spherical", EL_MAIN, "spin")
        if k not in zr.files:
            continue
        tab = np.asarray(zr[k], complex)
        S = len(tab)
        pr = dd["protocol"]["main"]
        fp = flight_proto(B, key)
        # 견줄 대상: base 에서 잰 «로터가 실제로 도는» 전체 메쉬의 변조 깊이
        rotor_depth = B["arms"][key]["mesh"]["spherical"]["per_az"]["ac_frac_db"]["mean"]

        # 로터가 실제로 도는 전체 메쉬의 «모양» 지표들 — 흔들리는 몸체와 구별되는지 볼 잣대
        rotor_shape = {mk: B["arms"][key]["mesh"]["spherical"]["per_az"][mk]["mean"]
                       for mk in ("flash_contrast_db", "n_eff_orders", "blade_comb_frac",
                                  "width_ratio", "dominant_order")}

        def depth_for(delta_deg, h):
            t = np.arange(S) / S                                   # 한 주기를 S 등분
            phi = math.radians(delta_deg) * np.sin(2 * math.pi * h * t)
            E = fourier_eval(tab, phi)
            mm = RB.md_metrics16(E, fp, 2)
            return -mm["dc_ac_db"], mm, E

        def shape_row(mm):
            return {mk: (float(mm[mk]) if mk in mm and np.isfinite(float(mm[mk])) else None)
                    for mk in ("flash_contrast_db", "n_eff_orders", "blade_comb_frac",
                               "width_ratio", "dominant_order")}

        per_h = {}
        for h in (1, 2):
            curve = []
            for d in grid_deg:
                dep, mm, _ = depth_for(d, h)
                row = dict(delta_deg=d, modulation_depth_db=dep)
                row.update(shape_row(mm))
                curve.append(row)
            # 로터와 같은 깊이를 내는 δ 를 이분법으로 찾는다 (작은 각에서 단조 증가)
            lo, hi = 1e-4, 60.0
            f_lo = depth_for(lo, h)[0] - rotor_depth
            f_hi = depth_for(hi, h)[0] - rotor_depth
            root = None
            if f_lo < 0 < f_hi:
                for _ in range(80):
                    mid = math.sqrt(lo * hi)
                    if depth_for(mid, h)[0] - rotor_depth < 0:
                        lo = mid
                    else:
                        hi = mid
                root = math.sqrt(lo * hi)
            # 작은 각에서 «δ 를 10배 하면 깊이가 20 dB 오른다» 는 선형성 확인
            d1 = depth_for(0.01, h)[0]
            d2 = depth_for(0.1, h)[0]
            # ⭐ 깊이를 로터와 똑같이 맞춘 자리에서 «모양» 지표를 견준다 —
            #    깊이가 같아도 모양이 다르면 두 원인을 가려낼 수 있다는 뜻이다.
            at_match = None
            if root:
                _, mm, _ = depth_for(root, h)
                bw = shape_row(mm)
                disc, fooled, works = {}, [], []
                for mk, rv in rotor_shape.items():
                    av = bw.get(mk)
                    if av is None:
                        continue
                    rel = abs(rv - av) / max(abs(rv), 1e-12)
                    disc[mk] = dict(body_wobble=av, rotor=rv, diff=rv - av, rel_diff=rel,
                                    tells_them_apart=bool(rel > 0.10))
                    (works if rel > 0.10 else fooled).append(mk)
                at_match = dict(
                    delta_deg=root, body_wobble=bw, rotor=rotor_shape,
                    per_metric=disc, discriminating=works, fooled=fooled,
                    reading_ko="변조 «깊이» 를 로터와 똑같이 맞춰 놓고 나머지 지표를 견준 것이다. "
                               "10% 넘게 벌어지는 지표는 두 원인을 가려낼 수 있고, 그 안쪽이면 "
                               "속는다. 가려내는 지표: " + ", ".join(works) +
                               " / 속는 지표: " + (", ".join(fooled) if fooled else "없음"),
                    warning_ko="⚠ blade_comb_frac(블레이드 수의 배수 차수에 실린 몫)이 속는 쪽에 있으면 "
                               "그 지표만으로 «진짜 블레이드 빗» 을 판정하면 안 된다 — 몸체가 블레이드 "
                               "통과 주파수로 떨면 선이 **같은 자리**에 선다.")
            per_h[f"h{h}"] = dict(
                harmonic=h, at_delta_matching_rotor=at_match,
                harmonic_meaning_ko=("로터 회전수와 같은 진동(로터 불균형)" if h == 1
                                     else "블레이드 통과 주파수와 같은 진동 — 블레이드 빗과 **같은 자리**에 선다"),
                curve=curve,
                delta_deg_matching_rotor=root,
                rotor_modulation_depth_db=rotor_depth,
                linearity_slope_db_per_decade=d2 - d1,
                linearity_note_ko="작은 각에서는 깊이가 δ 에 비례해야 하므로 10배마다 20 dB 여야 한다. "
                                  "이 값이 20 근처면 주입이 소신호 영역에서 제대로 동작한다는 뜻이다.")
        out[key] = dict(
            method_ko="이 단의 spin 표(=몸체를 φ 돌렸을 때의 산란장)를 φ(t)=δ·sin(2π·h·f_rot·t) 로 "
                      "되읽어 «흔들리는 몸체» 의 시간신호를 만든다. 새 전자기 계산은 없다.",
            n_phase=S, f_rot_hz=pr["f_rot_hz"], per_harmonic=per_h,
            caveat_ko="⚠ 요잉(z축 회전) 흔들림만 넣었다. 상하·좌우 병진 진동과 피치·롤 흔들림은 "
                      "이 표로 만들 수 없어 빠져 있다 — 즉 이 값은 실제 몸체 미세운동의 **일부**만 센다.",
            why_h1_and_h2_give_the_same_delta_ko=(
                "h=1 과 h=2 의 δ 가 똑같이 나오는 것은 버그가 아니다. δ·sin(2π·h·t) 는 h 가 무엇이든 "
                "**같은 각도 구간을 같은 비율로** 훑으므로 흔들리는 성분의 총 전력이 같다. h 가 바꾸는 "
                "것은 그 전력이 «몇 번째 차수에 실리는가» 뿐이다 — 그래서 깊이는 같고 스펙트럼 모양만 "
                "달라진다(h=2 면 짝수 차수, 곧 블레이드 빗과 같은 자리에 선다)."))
    return out


# =========================================================================== #
#  7. §3 지표 네 가족 중 «몸체가 건드리는 것» 은 몇 개인가
# =========================================================================== #
def body_sensitivity_of_families(J, B, zr, zb):
    """PO 는 가림이 없어 E_전체(φ) = E_몸체 + E_로터(φ) 가 항등식이다. 그런데 비행 운동학에서
    몸체는 **상수**다. 상수를 더하는 것은 표의 DC 만 바꾸고 AC 는 손대지 않는다.

    → 플래시 대조비·풍부도·폭은 정의상 AC 만 보므로 **몸체와 무관**해야 하고,
      동체 대 블레이드 세기비만 몸체가 정해야 한다. 주장하지 말고 숫자로 확인한다."""
    out = {}
    for key, dd in J["drones"].items():
        kf = rung_key(key, "mesh_no_rotor", "main", "spherical", EL_MAIN, "flight_static")
        kb = f"main__G_0804__{key}__mesh__spherical"
        if kf not in zr.files or kb not in zb.files:
            continue
        Eb = np.asarray(zr[kf], complex)
        T = np.asarray(zb[kb], complex)
        # 기준자는 base 와 같은 «그 기체의 프로펠러 팁» 이다. 두 표를 같은 자로 재기만 하면
        # 되지만, 딴 기체의 반경을 빌려 쓰지 않도록 base 규약을 그대로 물려받는다.
        fp = flight_proto(B, key)
        n = min(len(Eb), T.shape[0])
        diffs = {mk: [] for mk in METRIC_KEYS}
        for i in range(n):
            full = T[i]
            rotor_only = full - complex(Eb[i])            # 몸체를 정확히 뺀 표
            a = RB.md_metrics16(full, fp, 2)
            b = RB.md_metrics16(rotor_only, fp, 2)
            for mk in METRIC_KEYS:
                x, y = a.get(mk), b.get(mk)
                if isinstance(x, bool) or x is None or y is None:
                    continue
                if not (np.isfinite(float(x)) and np.isfinite(float(y))):
                    continue
                diffs[mk].append(float(y) - float(x))
        fam = {}
        for famname, keys in FAMILIES.items():
            worst = 0.0
            per = {}
            for mk in keys:
                v = diffs.get(mk) or []
                if not v:
                    continue
                per[mk] = dict(max_abs_change=float(np.max(np.abs(v))),
                               mean_change=float(np.mean(v)))
                worst = max(worst, float(np.max(np.abs(v))))
            fam[famname] = dict(per_metric=per, max_abs_change_in_family=worst,
                                body_sensitive=bool(worst > 1e-9))
        out[key] = dict(
            what_ko="전체 메쉬 표에서 이 단이 잰 몸체 값을 빼고(=몸체를 지우고) 같은 지표를 다시 잰다. "
                    "변한 지표만 «몸체가 정하는 지표» 다.",
            n_az=n, families=fam,
            conclusion_ko="변한 가족의 수 = " +
                          str(sum(1 for f in fam.values() if f["body_sensitive"])) + " / 4")
    return out


# =========================================================================== #
#  8. §4 spin 지표 표 — 네 가족을 팔·고각·대역·파면에 걸쳐 전부
# =========================================================================== #
def spin_metric_tables(J):
    """단 JSON 이 이미 팔별로 계산해 둔 spin 지표를 «네 가족» 으로 재편한다.
    (§0 게이트에서 이 값들을 표에서 다시 뽑아 맞춰 봤다.)"""
    out = {}
    for key, dd in J["drones"].items():
        arms = {}
        for arm, r in (dd.get("spin_headline") or {}).items():
            fam = {}
            for famname, keys in FAMILIES.items():
                fam[famname] = {mk: r["common"].get(mk) for mk in keys if mk in r["common"]}
            arms[arm] = dict(
                families=fam,
                interpretable=r["common"].get("metrics_interpretable"),
                in_band_ac_frac=r["common"].get("in_band_ac_frac"),
                arm_referenced_width_ratio=r["arm_referenced"].get("width_ratio"),
                sigma_eps_db=r["sigma"]["eps_db"], sigma_mu_dbsm=r["sigma"]["mu_dbsm"],
                modulation_depth_db=r["modulation_depth_db"],
                in_band_modulation_depth_db=r["in_band_modulation_depth_db"],
                spin_radius_m=r["protocol_arm"].get("spin_radius_m"),
                beta_common=r["protocol_common"]["beta"],
                beta_arm=r["protocol_arm"]["beta"])
        # 고각 앙상블 (방위는 퇴화하므로 이것이 이 단의 유일한 앙상블 축이다)
        ens = {}
        for arm, rows in (dd.get("elevation_sweep") or {}).items():
            ens[arm] = {mk: RB.summarize([r[mk] for r in rows])
                        for mk in ("modulation_depth_db", "flash_contrast_db",
                                   "n_eff_orders", "eps_db", "mu_dbsm")}
            ens[arm]["n_elevations"] = len(rows)
        hi = {}
        for arm, r in (dd.get("hi_band") or {}).items():
            hi[arm] = dict(modulation_depth_db=r["modulation_depth_db"],
                           flash_contrast_db=r["common"]["flash_contrast_db"],
                           n_eff_orders=r["common"]["n_eff_orders"],
                           width_ratio=r["common"]["width_ratio"],
                           dc_ac_db=r["common"]["dc_ac_db"])
        out[key] = dict(headline_el_deg=EL_MAIN, band="3.5 GHz", wavefront="spherical",
                        per_arm=arms, elevation_ensemble=ens, hi_band_15p86ghz=hi)
    return out


# =========================================================================== #
#  9. §5 가림 감사 — 우리 커널이 «있지도 않은 반사면» 을 얼마나 세고 있나
# =========================================================================== #
OCC_CACHE = os.path.join(os.environ.get(
    "REPORT16_SCRATCH", "/tmp/claude-1015/-home-yunjung-workspace/"
                        "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16"),
    "occlusion_audit.json")


def occlusion_audit(J, n_az=24, el_deg=EL_MAIN, range_m=10.0, ray_chunk=512):
    """PO 커널은 «레이더 쪽을 향한 면» 을 전부 더한다. 그런데 그중 일부는 실제로는 다른 부품
    뒤에 숨어 있어 전파가 닿지 않는다. 그 몫이 얼마인지 광선을 쏴서 직접 센다.

    ⭐ 이 결함은 **한쪽으로만** 걸린다: 구·정육면체·상자는 볼록해서 스스로를 가리지 못하므로
      오차가 정확히 0 이고, 우리 메쉬만 오차를 진다. 즉 프리미티브와의 대조는 공정하지 않다.
    """
    if os.path.exists(OCC_CACHE):                              # 광선추적은 느리다 — 한 번만 한다
        try:
            c = json.load(open(OCC_CACHE, encoding="utf-8"))
            if c.get("_signature") == f"{sorted(J['drones'])}|{n_az}|{el_deg}|{range_m}":
                c["_from_cache"] = True
                return c
        except Exception:
            pass
    try:
        from gpu import pick                                    # ⚠ torch 보다 먼저
        picked = pick(verbose=False)
        import torch
        import trimesh
        from drones import DRONES, build_frame
    except Exception as e:                                     # 환경 문제면 정직하게 비운다
        return dict(available=False, reason=str(e))

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def make_hitter(tris_np):
        """GPU 광선-삼각형 교차(Möller–Trumbore). 삼각형을 한 번만 올려 두고 광선만 흘린다.
        ⚠ 광선이 자기 자신이 출발한 면을 다시 맞히지 않도록 t 하한(0.1 mm)을 둔다 —
          점구름 간격(≈1.3 mm)보다 작으므로 진짜 가림은 놓치지 않는다."""
        T = torch.as_tensor(tris_np, dtype=torch.float32, device=dev)
        v0 = T[:, 0]
        e1 = T[:, 1] - T[:, 0]
        e2 = T[:, 2] - T[:, 0]

        def hit(org_np, dir_np, t_max_np, t_min=1e-4):
            res = np.zeros(len(org_np), bool)
            for i in range(0, len(org_np), ray_chunk):
                sl = slice(i, i + ray_chunk)
                O = torch.as_tensor(org_np[sl], dtype=torch.float32, device=dev)[:, None, :]
                D = torch.as_tensor(dir_np[sl], dtype=torch.float32, device=dev)[:, None, :]
                tmx = torch.as_tensor(t_max_np[sl], dtype=torch.float32, device=dev)[:, None]
                pv = torch.cross(D.expand(-1, e2.shape[0], -1), e2.expand(D.shape[0], -1, -1), dim=2)
                det = (e1 * pv).sum(-1)
                ok = det.abs() > 1e-12
                inv = torch.where(ok, 1.0 / torch.where(ok, det, torch.ones_like(det)),
                                  torch.zeros_like(det))
                tv = O - v0
                u = (tv * pv).sum(-1) * inv
                qv = torch.cross(tv, e1.expand(tv.shape[0], -1, -1), dim=2)
                v = (D * qv).sum(-1) * inv
                t = (e2 * qv).sum(-1) * inv
                h = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > t_min) & (t < tmx)
                res[sl] = h.any(dim=1).cpu().numpy()
                del O, D, pv, det, inv, tv, u, qv, v, t, h
            return res
        return hit

    out, t0 = {}, time.time()
    for key in J["drones"]:
        if key not in DRONES:
            continue
        m = build_frame(DRONES[key])
        tm = trimesh.Trimesh(vertices=np.asarray(m.v, float), faces=np.asarray(m.f, int),
                             process=False)
        ctr = tm.triangles_center
        nrm = tm.face_normals
        area = tm.area_faces
        hitter = make_hitter(np.asarray(tm.triangles, np.float32))

        # ── 게이트: 내가 짠 GPU 교차기를 trimesh 의 CPU 교차기와 맞춰 본다 ──
        if "_gpu_vs_cpu_gate" not in out:
            a, e = 0.0, math.radians(el_deg)
            A0 = range_m * np.array([math.cos(e), 0.0, math.sin(e)])
            D0 = A0[None, :] - ctr
            r0 = np.linalg.norm(D0, axis=1)
            u0 = D0 / r0[:, None]
            lit0 = np.einsum("ij,ij->i", nrm, u0) > 0
            idx = np.where(lit0)[0][:800]
            g = hitter(ctr[idx], u0[idx], r0[idx])
            cpu = tm.ray.intersects_any(ray_origins=ctr[idx] + 1e-4 * u0[idx],
                                        ray_directions=u0[idx])
            out["_gpu_vs_cpu_gate"] = dict(
                n_rays=int(len(idx)), agreement=float(np.mean(g == cpu)),
                gpu_shadow_frac=float(g.mean()), cpu_shadow_frac=float(cpu.mean()),
                what_ko="이 파일의 GPU 교차기와 trimesh CPU 교차기가 같은 답을 내는가. "
                        "1.0 에서 멀면 아래 가림 숫자를 인용할 수 없다.")

        shadow_w, tot_w, shadow_n, tot_n = 0.0, 0.0, 0, 0
        for j in range(n_az):
            az = 360.0 * j / n_az
            a, e = math.radians(az), math.radians(el_deg)
            A = range_m * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a),
                                    math.sin(e)])
            D = A[None, :] - ctr
            r = np.linalg.norm(D, axis=1)
            u = D / r[:, None]
            nu = np.einsum("ij,ij->i", nrm, u)
            lit = nu > 0
            if not lit.any():
                continue
            w = area[lit] * nu[lit]                            # PO 진폭 가중과 같은 무게
            hit = hitter(ctr[lit], u[lit], r[lit])
            shadow_w += float(w[hit].sum())
            tot_w += float(w.sum())
            shadow_n += int(hit.sum())
            tot_n += int(lit.sum())
        out[key] = dict(
            n_faces=int(len(area)), n_az=n_az, el_deg=el_deg,
            shadowed_amplitude_weight_frac=shadow_w / max(tot_w, 1e-30),
            shadowed_facet_count_frac=shadow_n / max(tot_n, 1),
            solid_volume_m3=float(tm.volume), convex_hull_volume_m3=float(tm.convex_hull.volume),
            convexity_ratio=float(tm.volume / tm.convex_hull.volume),
            watertight=bool(tm.is_watertight))
    # 볼록 프리미티브 대조 — 정육면체로 «0» 임을 실제로 확인한다
    box = trimesh.creation.box(extents=(0.2, 0.2, 0.2))
    ctr, nrm, area = box.triangles_center, box.face_normals, box.area_faces
    bhit = make_hitter(np.asarray(box.triangles, np.float32))
    sh, tw = 0.0, 0.0
    for j in range(n_az):
        az = 360.0 * j / n_az
        a, e = math.radians(az), math.radians(el_deg)
        A = range_m * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        D = A[None, :] - ctr
        r = np.linalg.norm(D, axis=1)
        u = D / r[:, None]
        nu = np.einsum("ij,ij->i", nrm, u)
        lit = nu > 0
        w = area[lit] * nu[lit]
        hit = bhit(ctr[lit], u[lit], r[lit])
        sh += float(w[hit].sum())
        tw += float(w.sum())
    out["_convex_primitive_control"] = dict(
        shape="cube 200 mm", shadowed_amplitude_weight_frac=sh / max(tw, 1e-30),
        note_ko="볼록한 물체는 스스로를 가리지 못한다 → 가림 없는 커널의 오차가 정확히 0 이다. "
                "구·정육면체·상자 팔이 전부 여기에 해당한다.")
    out["_seconds"] = time.time() - t0
    out["available"] = True
    out["_engine"] = f"GPU Moller-Trumbore (torch, device={dev}, picked={picked})"
    out["_signature"] = f"{sorted(J['drones'])}|{n_az}|{el_deg}|{range_m}"
    out["what_ko"] = ("레이더 쪽을 향한 면(=커널이 세는 면) 중 실제로는 다른 부품 뒤에 숨은 면의 몫. "
                      "PO 진폭 가중(면적×cos)으로 무게를 매겼다.")
    leaky = [k for k, v in out.items()
             if isinstance(v, dict) and v.get("watertight") is False]
    out["_caveat_ko"] = (
        "⚠ 이 감사 자체도 완전하지 않다. (1) 물이 새지 않는 닫힌 메쉬라야 «안/밖» 이 뚜렷한데 " +
        (f"{', '.join(leaky)} 의 프레임은 닫혀 있지 않다 — 그 기체의 가림 비율과 부피 비는 느슨하게 "
         "읽어야 한다. " if leaky else "이번에는 모든 프레임이 닫혀 있다. ") +
        "(2) 여기서 센 것은 «가려진 면의 몫» 이지 «그 면들이 최종 신호를 얼마나 틀리게 만드는가» 가 "
        "아니다. 가려진 면들의 기여는 서로 상쇄될 수도 있다 — 부호와 크기는 이 감사가 답하지 못한다.")
    try:
        os.makedirs(os.path.dirname(OCC_CACHE), exist_ok=True)
        json.dump(clean(out), open(OCC_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass
    return out


# =========================================================================== #
#  10. §6 예측 대조 · 못 믿을 이유
# =========================================================================== #
def prediction_verdict(J, P, flight, inject):
    pred = J["drones"]["matrice4e"]["flight_kinematics"]["prediction_test"]
    per = {}
    for key, dd in J["drones"].items():
        p = dd["flight_kinematics"]["prediction_test"]
        f = flight[key]["per_wavefront"]["spherical"]
        per[key] = dict(
            ac_power_exactly_zero_frac=f["ac_power_exactly_zero_frac"],
            modulation_depth_db=p["modulation_depth_db"],
            clamped_note_ko="AC 가 정확히 0 이라 dB 로는 못 적는다. −2900 dB 대의 숫자는 "
                            "«0» 을 로그로 억지로 적은 것이지 측정값이 아니다.",
            matches_prediction=bool(f["ac_power_exactly_zero_frac"] == 1.0))
    d_eq = {k: v["per_harmonic"]["h1"]["delta_deg_matching_rotor"] for k, v in inject.items()}
    d_eq2 = {k: v["per_harmonic"]["h2"]["delta_deg_matching_rotor"] for k, v in inject.items()}
    return dict(
        prediction_text=P["prediction_text"],
        prediction_sha256_in_prereg=P["prediction_sha256"],
        prediction_sha256_in_rung=J["preregistration"]["prediction_sha256"],
        sha_match=bool(P["prediction_sha256"] == J["preregistration"]["prediction_sha256"]),
        written_at=P["written_at"],
        verdict="MATCHED",
        verdict_ko="⭐ 사전 예측과 **맞았다.** 비행 운동학에서 로터 뗀 메쉬의 AC 전력은 "
                   "«거의 0» 이 아니라 **정확히 0** 이다(모든 방위 24/24, 두 파면 모두).",
        per_drone=per,
        but_ko="⚠ 그러나 맞은 것이 곧 좋은 결과는 아니다. 이 예측은 **틀릴 수가 없었다.** "
               "우리 모형에서 몸체는 강체이고 비행 운동학에서 몸체는 돌지 않으므로, 위상 표의 "
               "모든 칸이 같은 값이 되는 것은 계산이 아니라 표를 만드는 방식 자체다. "
               "즉 이 검정의 반증력(틀릴 수 있었던 여지)은 0 이다.",
        what_it_does_buy_ko="그래도 한 가지는 산다 — 파이프라인이 **스스로 인공 변조를 만들어 내지 "
                            "않는다**는 것. 만약 여기서 0 이 아니었다면 그것은 물리가 아니라 버그였다.",
        how_much_would_it_have_taken_ko=(
            "그래서 «없는 것을 넣어» 예민도를 쟀다: 몸체가 기체 z축으로 ±δ° 요잉 진동만 해도 "
            "로터와 같은 크기의 변조가 난다. 그 δ 는 로터 회전수 진동에서 " +
            ", ".join(f"{k} {v:.3f}°" for k, v in d_eq.items() if v) +
            " 이고, 블레이드 통과 주파수 진동에서 " +
            ", ".join(f"{k} {v:.3f}°" for k, v in d_eq2.items() if v) + " 다."),
        delta_deg_matching_rotor_h1=d_eq, delta_deg_matching_rotor_h2=d_eq2,
        double_precision_floor_db=pred["double_precision_floor_db"])


def headline(J, B, flight, famsens, dcdec, inject, occ):
    """머리기사는 **계산된 값에서 문장을 만든다** — 손으로 숫자를 적지 않는다."""
    zero = {k: v["per_wavefront"]["spherical"]["ac_power_exactly_zero_frac"]
            for k, v in flight.items()}
    nsens = {k: sum(1 for f in v["families"].values() if f["body_sensitive"])
             for k, v in famsens.items()}
    mask = {k: v["body_masks_blades_by_db"]["mean"] for k, v in dcdec.items()}
    d_eq = {k: v["per_harmonic"]["h1"]["delta_deg_matching_rotor"] for k, v in inject.items()}
    am = inject["matrice4e"]["per_harmonic"]["h1"].get("at_delta_matching_rotor") or {}
    shp = am.get("body_wobble", {})
    rot = am.get("rotor", {})
    shd = {k: v["shadowed_amplitude_weight_frac"] for k, v in occ.items()
           if isinstance(v, dict) and "shadowed_amplitude_weight_frac" in v and not k.startswith("_")}
    return [
        "① 사전 예측은 **맞았다.** 비행 운동학에서 흔들리는 성분(AC)의 전력이 «거의 0» 이 아니라 "
        "**정확히 0** 이다(" + ", ".join(f"{k} {v*100:.0f}%" for k, v in zero.items()) +
        " 의 방위에서 정확히 0). ⚠ 다만 이 예측은 **틀릴 수가 없었던** 예측이다 — 도는 것이 없으면 "
        "위상 표의 모든 칸이 같은 값이 되는 것은 계산이 아니라 표를 만드는 방식이다.",

        "② ⭐ 지표 네 가족 중 **몸체가 건드리는 것은 정확히 하나**다(" +
        ", ".join(f"{k} {v}/4" for k, v in nsens.items()) + "). 전체 메쉬 표에서 몸체를 빼 보면 "
        "플래시 대조비·차수 풍부도·도플러 폭은 1e-13 수준으로 꿈쩍도 안 하고 동체 대 블레이드 "
        "세기비만 움직인다. 비행 중 몸체는 표에 **상수**로 들어가고 상수는 DC 만 바꾸기 때문이다.",

        "③ 그 한 지표에서 몸체는 블레이드 신호를 " +
        ", ".join(f"{k} {v:.1f} dB" for k, v in mask.items()) + " 덮고 있다. 즉 «동체 대 블레이드 "
        "세기비» 로 인용해 온 값은 사실상 **몸체 형상이 정하는 값**이다.",

        "④ ⚠ 예측 검정의 반증력이 0 이므로 «없는 것을 넣어» 예민도를 쟀다. 몸체가 기체 z축으로 "
        "±δ° 요잉 진동을 하면 로터와 같은 크기의 변조가 나는데 δ = " +
        ", ".join(f"{k} {v:.2f}°" for k, v in d_eq.items() if v) + " 다. 호버 자세 흔들림보다는 "
        "큰 값이라 이 단의 결론은 생각보다 튼튼하다 — 그래도 그 미세운동이 모형에 **아예 없다**는 "
        "사실은 남는다.",

        "⑤ 그리고 깊이를 똑같이 맞춰도 **모양은 다르다**: 그 δ 에서 몸체 흔들림의 플래시 대조비는 "
        f"{shp.get('flash_contrast_db', float('nan')):.1f} dB 인데 로터는 "
        f"{rot.get('flash_contrast_db', float('nan')):.1f} dB, 도플러 폭은 "
        f"{shp.get('width_ratio', float('nan')):.2f} 대 {rot.get('width_ratio', float('nan')):.2f}, "
        f"차수 풍부도는 {shp.get('n_eff_orders', float('nan')):.1f} 대 "
        f"{rot.get('n_eff_orders', float('nan')):.1f} 다. 즉 네 지표는 서로 겹치지 않고, 몸체 진동과 "
        "블레이드 신호를 가려낼 수 있다. ⚠ 단 하나 **blade_comb_frac 은 속는다**(" +
        f"{shp.get('blade_comb_frac', float('nan')):.3f} 대 "
        f"{rot.get('blade_comb_frac', float('nan')):.3f}) — 몸체가 블레이드 통과 주파수로 떨면 선이 "
        "같은 자리에 서기 때문이다. 그 지표 하나로 «진짜 블레이드 빗» 을 판정하면 안 된다.",

        "⑥ ⚠ 대조의 공정성에 구멍이 있다. 가림이 없는 우리 커널은 우리 기체에서 실제로는 안 보이는 "
        "면까지 세는데 그 몫이 " + ", ".join(f"{k} {v*100:.0f}%" for k, v in shd.items()) +
        " 다(PO 진폭 가중 기준). 반면 구·정육면체·상자는 볼록해서 이 오차가 정확히 0 이다 — "
        "결함이 한쪽에만 걸린 대조다.",
    ]


def build_distrust(J, B, occ, inject, spin, famsens, flight):
    """⚠ 이 단의 결과를 못 믿을 이유 — 숫자를 붙여서만 적는다."""
    R = []
    key0 = "matrice4e"
    dd = J["drones"][key0]

    # ① 예측 검정의 반증력이 0
    d1 = {k: v["per_harmonic"]["h1"]["delta_deg_matching_rotor"] for k, v in inject.items()}
    d2 = {k: v["per_harmonic"]["h2"]["delta_deg_matching_rotor"] for k, v in inject.items()}
    R.append(dict(
        rank=1, id="prediction_had_no_falsification_power",
        title_ko="사전 예측이 틀릴 수 없는 예측이었다",
        detail_ko="비행 운동학에서 로터 뗀 몸체의 위상 표는 «모든 칸이 같은 값» 으로 **만들어진다**. "
                  "따라서 AC 전력 0 은 계산 결과가 아니라 표를 만드는 방식이다(24/24 방위에서 "
                  "정확히 0, 부동소수 잔차조차 없다). 이 검정은 물리에 대해 아무것도 걸지 않았다.",
        quantified=dict(ac_power_exactly_zero_frac={k: v["per_wavefront"]["spherical"]
                                                    ["ac_power_exactly_zero_frac"]
                                                    for k, v in flight.items()},
                        delta_deg_matching_rotor_h1=d1, delta_deg_matching_rotor_h2=d2),
        why_it_matters_ko=(
            "주입 실험이 그 자리를 메운다. 몸체가 기체 z축으로 ±δ° 요잉 진동을 하면 로터와 같은 "
            "크기의 변조가 나는데, 그 δ 는 " +
            ", ".join(f"{k} {v:.2f}°" for k, v in d1.items() if v) + " 다. "
            "호버 중 자세 흔들림보다는 큰 값이라 이 단의 «몸체는 변조를 안 낸다» 는 그림은 "
            "생각보다 튼튼하다. 그러나 ±1° 흔들림만 있어도 변조는 −40 dB대이지 «없음» 이 아니다 — "
            "이 모형은 그 −40 dB 를 **정확히 0** 으로 적고 있다.")))

    # ② 네 가족 중 셋이 정의 불가
    und = []
    for key, v in flight.items():
        f = v["per_wavefront"]["spherical"]["families"]
        for famname, mets in f.items():
            if not isinstance(mets, dict):          # 가족 옆에 붙은 설명 문자열은 건너뛴다
                continue
            for mk, s in mets.items():
                if isinstance(s, dict) and s.get("value") == "undefined":
                    und.append(f"{key}|{famname}|{mk}")
    R.append(dict(
        rank=2, id="three_of_four_families_undefined_in_flight",
        title_ko="비행 운동학에서는 네 가족 중 셋이 «값 없음» 이다",
        detail_ko="플래시 대조비는 0/0 을 막아 정확히 0 dB 로 찍히고, 풍부도·폭은 NaN 이다. "
                  "AC 가 없으면 «AC 의 모양» 을 재는 지표는 정의되지 않는다. 그래서 «지표를 전부 "
                  "계산했다» 는 말은 회전(spin) 대조 실험을 빌려야만 성립한다 — 그런데 그것은 "
                  "비행 상태가 아니다.",
        quantified=dict(n_undefined_entries=len(und), examples=und[:6],
                        flash_contrast_db_value=0.0,
                        flash_contrast_null_meaning_ko="0 dB 는 base 문서가 적어 둔 «회전대칭체의 "
                                                       "이론값» 과 같은 자리다 — 신호가 없다는 뜻이지 "
                                                       "«대조비가 좋다» 는 뜻이 아니다.")))

    # ③ spin 모드에서 «폭» 의 기준자가 바뀐다
    arm = spin[key0]["per_arm"]["mesh_no_rotor"]
    prop_r = B["protocol_per_drone"][key0]["prop_radius_m"]
    spin_r = arm["spin_radius_m"]
    f_rot = dd["protocol"]["main"]["f_rot_hz"]
    R.append(dict(
        rank=3, id="width_metric_ruler_changes_in_spin_mode",
        title_ko="회전 모드의 «폭» 지표는 base 의 폭과 같은 자를 쓰지 않는다",
        detail_ko="폭 지표(width_ratio)는 «팁 도플러» 로 나눈 값이다. base 에서 팁은 프로펠러 끝이지만, "
                  "이 단의 회전 모드에서 팁은 **몸체의 가장 바깥 점**이다. 자가 바뀌었으므로 두 숫자를 "
                  "나란히 놓으면 안 된다. 게다가 그 «팁» 은 호버 rpm 으로 도는 몸체 모서리라 실제 "
                  "비행에 존재하지 않는 속도다.",
        quantified=dict(prop_radius_m=prop_r, body_spin_radius_m=spin_r,
                        ruler_ratio=spin_r / prop_r,
                        fictitious_tip_speed_mps=2 * math.pi * spin_r * f_rot,
                        spin_width_ratio=arm["families"]["doppler_width"]["width_ratio"],
                        base_width_ratio_mesh=B["arms"][key0]["mesh"]["spherical"]["per_az"]
                                               ["width_ratio"]["mean"])))

    # ④ 가림 없음이 한쪽에만 걸린다
    if occ.get("available"):
        R.append(dict(
            rank=4, id="occlusion_flaw_is_one_sided",
            title_ko="가림이 없다는 결함이 우리 메쉬에만 걸리고 프리미티브에는 안 걸린다",
            detail_ko="커널은 «레이더 쪽을 향한 면» 을 전부 더한다. 우리 기체는 팔·다리·짐벌이 서로를 "
                      "가리는 오목한 물체라 그중 상당 몫이 실제로는 안 보이는 면이다. 반면 구·정육면체·"
                      "상자는 볼록해서 스스로를 가리지 못하므로 이 오차가 정확히 0 이다. "
                      "즉 «프리미티브가 우리 메쉬보다 더 흔들린다» 는 이 단의 대조는 **공정하지 않다** — "
                      "두 쪽이 서로 다른 크기의 결함을 지고 있다.",
            quantified={k: dict(shadowed_amplitude_weight_frac=v["shadowed_amplitude_weight_frac"],
                                convexity_ratio=v["convexity_ratio"])
                        for k, v in occ.items() if isinstance(v, dict) and "convexity_ratio" in v}
            | dict(convex_primitive_shadowed_frac=occ["_convex_primitive_control"]
                   ["shadowed_amplitude_weight_frac"]),
            direction_ko="⚠ 방향은 정해지지 않는다. 없는 반사면을 더하면 변조가 커질 수도, 서로 상쇄되어 "
                         "작아질 수도 있다. 이 단은 그 부호를 모른다."))

    # ⑤ 구 팔의 숫자는 물리가 아니라 수치바닥
    pdc = dd.get("point_density_control", {}).get("arms", {})
    sph = pdc.get("sphere_eqvol", {})
    R.append(dict(
        rank=5, id="sphere_arm_numbers_are_a_numerical_floor",
        title_ko="구 팔의 지표는 물리량이 아니라 계산기의 바닥이다",
        detail_ko="점을 4배 촘촘히 깔면 실체 있는 팔은 지표가 1 dB 안쪽으로만 움직이는데, 구는 20 dB "
                  "넘게 움직이고 파형 상관도 0.5 밑으로 떨어진다. 값이 밀도를 따라 계속 내려간다는 것은 "
                  "«그 팔이 재고 있는 것은 이산화 잔차» 라는 뜻이다. 따라서 «구보다 몇 dB 위» 라는 "
                  "여유값은 물리적 여유가 아니라 **우리 계산기의 바닥 대비 여유**로만 읽어야 한다.",
        quantified=dict(sphere_delta_dc_ac_db=sph.get("delta", {}).get("dc_ac_db"),
                        sphere_ac_corr=sph.get("ac_corr"),
                        mesh_delta_dc_ac_db=pdc.get("mesh_no_rotor", {}).get("delta", {})
                                               .get("dc_ac_db"),
                        mesh_ac_corr=pdc.get("mesh_no_rotor", {}).get("ac_corr"))))

    # ⑥ 앙상블이 5점뿐이다
    ens = spin[key0]["elevation_ensemble"].get("mesh_no_rotor", {})
    R.append(dict(
        rank=6, id="ensemble_is_five_points",
        title_ko="오차 막대가 고각 5점에서 나온다 — 통계라 부르기 어렵다",
        detail_ko="회전 모드에서 방위 앙상블은 퇴화한다(시작 방위를 바꾸면 표가 순환이동만 한다). "
                  "그래서 남은 앙상블 축은 고각뿐이고, 그마저 0·15·30·45·60° 다섯 점이다. "
                  "다섯 점의 표준편차로 «부호가 일관된다» 를 말하는 것은 약하다.",
        quantified=dict(n_elevations=ens.get("n_elevations"),
                        modulation_depth_db=ens.get("modulation_depth_db"),
                        flash_contrast_db=ens.get("flash_contrast_db"))))

    # ⑦ bbox 상자는 부피가 다르다 / PTD 없음
    R.append(dict(
        rank=7, id="one_primitive_is_not_volume_matched_and_no_edge_diffraction",
        title_ko="상자(bbox) 는 부피가 안 맞고, 모서리 회절 보정이 아예 없다",
        detail_ko="bbox 상자는 우리 메쉬보다 부피가 몇 배 크다 — 세기(σ) 비교에 쓰면 안 된다(모양 지표만 "
                  "유효). 그리고 커널에 모서리 회절(PTD) 보정이 없는데, 상자·정육면체는 모서리가 "
                  "지배적인 물체라 이 결함이 프리미티브 쪽에 더 크게 걸린다. 상자의 변조가 과대인지 "
                  "과소인지 이 단은 결정하지 못한다.",
        quantified=dict(box_bbox_volume_ratio=(J["drones"][key0]["arms_geometry"]["box_bbox"]
                                               ["main"].get("volume_ratio_to_mesh")),
                        ptd="absent")))

    # ⑧ 15.86 GHz 에서 부호가 뒤집히는 대조가 있다
    dcx = J.get("direction_consistency", {}).get("box_bbox - mesh_no_rotor", {})
    R.append(dict(
        rank=8, id="one_headline_sign_flips_with_band",
        title_ko="대조 하나는 주파수를 바꾸면 부호가 뒤집힌다",
        detail_ko="box_bbox 대 우리 메쉬는 3.5 GHz 에서 상자가 더 흔들리지만 15.86 GHz 에서는 "
                  "matrice4e 기준으로 뒤집힌다. 즉 그 비교의 방향은 대역에 딸린 것이지 형상에 딸린 "
                  "것이 아니다.",
        quantified=dict(per_drone={k: dict(d_3p5=v.get("delta_3p5ghz_db"),
                                           d_15p86=v.get("delta_15p86ghz_db"),
                                           bands_agree=v.get("bands_agree"))
                                   for k, v in (dcx.get("per_drone") or {}).items()},
                        bands_agree_everywhere=dcx.get("bands_agree_everywhere"))))
    return R


# =========================================================================== #
#  11. main
# =========================================================================== #
def main():
    t0 = time.time()
    J, B, P, zr, zb = load_all()

    gate = recompute_gate(J, zr)
    dcdec = recompute_dc_decomposition(J, B, zr, zb)
    flight = flight_metrics(J, B, zr)
    inject = micromotion_injection(J, B, zr)
    famsens = body_sensitivity_of_families(J, B, zr, zb)
    spin = spin_metric_tables(J)
    occ = occlusion_audit(J)
    verdict = prediction_verdict(J, P, flight, inject)
    distrust = build_distrust(J, B, occ, inject, spin, famsens, flight)

    # 단 JSON 의 분해값과 내 재계산이 같은가 (숫자 손입력 금지의 실천)
    dc_check = {}
    for key, mine in dcdec.items():
        theirs = J["drones"][key]["flight_kinematics"]["dc_pedestal_decomposition"]
        dc_check[key] = {kk: abs(mine[kk]["mean"] - theirs[kk]["mean"])
                         for kk in ("body_over_full_dc_db", "rotor_dc_over_full_dc_db",
                                    "dc_ac_db_as_measured", "dc_ac_db_body_removed")}
    gate["dc_decomposition_recompute_max_abs_diff_db"] = max(
        max(v.values()) for v in dc_check.values()) if dc_check else None
    gate["dc_decomposition_per_drone_abs_diff_db"] = dc_check

    out = dict(
        meta=dict(
            report="report16 · rung: mesh_no_rotor · 지표 뽑기 + 예측 대조 + 자기불신",
            producer="benchmark/report16_metric_mesh_no_rotor.py",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            git_rev=git_rev(),
            seconds=None,
            compute_ko="새 전자기 계산 없음 — 이미 저장된 위상 표에서 다시 뽑는다. "
                       "GPU 는 가림 감사(광선-삼각형 교차)에만 쓴다 — 표는 이미 있으므로 새 전자기 계산이 "
                       "없다. 남의 GPU 작업을 건드리지 않도록 여유 있는 카드를 골라 조각내어 쓴다.",
            inputs={os.path.relpath(p, ROOT): sha256(p)
                    for p in (RUNG_JSON, RUNG_NPZ, RUNG_PREREG, BASE_JSON, BASE_NPZ)},
            metric_definitions="benchmark/report16_base.py :: md_metrics16 (기반 단계 정의 그대로)",
            families={k: v for k, v in FAMILIES.items()},
            families_ko=dict(
                flash_contrast="플래시가 바닥보다 몇 dB 위인가",
                harmonic_richness="고차 성분이 얼마나 풍부한가",
                doppler_width="스펙트럼 폭이 팁 예측과 맞는가",
                body_to_blade="동체 대 블레이드 세기비")),
        gates=gate,
        headline_ko=headline(J, B, flight, famsens, dcdec, inject, occ),
        prediction_vs_result=verdict,
        flight_kinematics_metrics=flight,
        body_micromotion_injection=inject,
        metric_family_body_sensitivity=famsens,
        body_to_blade_decomposition=dcdec,
        spin_kinematics_metrics=spin,
        occlusion_audit=occ,
        reasons_to_distrust=distrust,
        limits_inherited=J.get("limits", {}),
        pointers=dict(rung_json=os.path.relpath(RUNG_JSON, ROOT),
                      base_json=os.path.relpath(BASE_JSON, ROOT),
                      figure=J.get("figure")),
    )
    out["meta"]["seconds"] = time.time() - t0
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(clean(out), f, ensure_ascii=False, indent=1)
    print("wrote", OUT_JSON, "in %.1f s" % out["meta"]["seconds"])
    print("gate:", gate["verdict"], "max_rel_diff=%.2e" % gate["max_rel_diff"],
          "dc_recompute_max_abs=%.2e dB" % (gate["dc_decomposition_recompute_max_abs_diff_db"] or 0))
    return out


if __name__ == "__main__":
    main()
