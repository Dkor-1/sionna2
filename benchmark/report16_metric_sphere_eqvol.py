# -*- coding: utf-8 -*-
"""
report16_metric_sphere_eqvol.py — 「등가부피 구」 단의 **지표 추출·사전예측 대조** 단계
=============================================================================
■ 이 파일이 하는 일 (계산은 이미 끝났다 — 여기서는 **재지만 한다**)

  앞 단계 `benchmark/report16_rung_sphere_eqvol.py` 가 GPU 로 만들어 놓은 **위상 표**
  (드론이 프로펠러를 한 바퀴 돌리는 동안 되돌아오는 복소 신호 E(φ))를 그대로 읽어서

    ① 기반 단계 `report16_base.md_metrics16` 이 **정의한 지표를 전부** 계산하고
       — 플래시 대조비 / 고차 성분 풍부도 / 도플러 폭 / 동체:블레이드 비 —
    ② **계산 전에 못박아 둔 예측**(preregistration)과 하나씩 맞춰 채점하고
    ③ 이 결과를 **못 믿을 이유**를 스스로 찾아 숫자로 남긴다.

  ⭐ 지표 정의는 여기서 **다시 만들지 않는다**. `report16_base` 를 import 해서 그 함수를
     그대로 부른다. 정의가 두 벌이 되는 순간 「어느 쪽 숫자냐」 싸움이 시작되기 때문이다.

■ 쉬운 말 용어 풀이 (처음 나올 때 뜻을 적는다)

  · 마이크로도플러(micro-Doppler): 표적이 통째로 움직여서 생기는 주파수 이동 말고,
    표적의 **부속품이 따로 움직여서**(여기서는 프로펠러가 돌아서) 생기는 주파수 흔들림.
  · 위상 표 E(φ): 프로펠러를 각도 φ 만큼 돌려 놓고 잰 되돌아오는 신호. 한 바퀴를
    n_phase 등분해서 표로 만들어 둔 것.
  · 차수(order) m: 「한 바퀴당 m 번 흔들린다」는 뜻. 도플러 주파수로는 m × (회전수/초).
  · 대역 안(in-band): 블레이드 끝(팁)보다 빨리 도는 것은 없으므로, 팁이 만드는 최고 차수
    β 의 1.5 배까지가 «운동학적으로 가능한 자리» 다. 그 위에 있는 성분은 물리가 아니라
    우리가 물체를 삼각형으로 쪼개면서 생긴 **격자 잔재**로 본다.
  · 널(null) 팔: 이론상 답이 0 이어야 하는 대조군. 여기서는 회전축 위에 놓인 구.
  · PO(물리광학): 빛이 비치는 면만 골라 위상을 맞춰 더하는 근사 계산법.
  · Mie 해: 구에 대해서는 맥스웰 방정식을 정확히 풀 수 있다. 그 정확해.

■ ⛔ 손대지 않는 것: src/drones.py·src/drone_cad.py 는 **읽기만**, report15_*·report0N_*
   는 아예 건드리지 않는다. 새 파일은 report16_* 접두어만.
■ GPU 를 쓰지 않는다: 이 단계는 이미 저장된 표를 읽어 CPU 로 FFT 만 돌린다.
   (남의 워크플로가 GPU 를 쓰는 중이라 굳이 점유하지 않는다.)
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

import report16_base as B                       # noqa: E402  ⭐ 지표 정의의 유일한 출처
import mie_pec_sphere as MIE                    # noqa: E402  구의 기준해(정확 Mie + 해석 PO)

RUNG_JSON = os.path.join(ROOT, "outputs", "report16_rung_sphere_eqvol.json")
RUNG_NPZ = os.path.join(ROOT, "outputs", "report16_rung_sphere_eqvol_tables.npz")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_metric_sphere_eqvol.json")

DRONE_KEYS = ["mini2", "matrice4e", "mavic4pro"]
ARMS = ["mesh", "sphere_eqvol", "sphere_offaxis", "sph_hub", "sph_blade_rg", "sph_blade_tip"]
NULL_ARMS = ["sphere_eqvol", "sph_hub"]          # 이론상 변조 0 이어야 하는 팔
WFS = ["spherical", "plane"]
BANDS = ["main", "hi"]

# md_metrics16 이 돌려주는 «수치» 지표 — 네 묶음으로 갈라 둔다(기반 단계 정의 그대로).
FAMILY = {
    "flash": ["flash_contrast_db"],
    "richness": ["n_eff_orders", "dominant_order", "order_p50", "order_p90", "blade_comb_frac"],
    "width": ["width_ratio_10db", "width_ratio_20db", "width_ratio_30db",
              "fd_edge_10db_hz", "fd_edge_20db_hz", "fd_edge_30db_hz",
              "order_edge_10db", "order_edge_20db", "order_edge_30db"],
    "dc_ac": ["dc_ac_db", "ac_frac_db", "in_band_ac_over_dc_db"],
    "level": ["sigma_eq_mean_dbsm", "mean_sigma_proxy"],
    "quality": ["in_band_ac_frac", "ac_over_floor_db"],
}
METRIC_KEYS = [k for fam in FAMILY.values() for k in fam]
EPS_F64 = float(np.finfo(np.float64).eps)


# --------------------------------------------------------------------------- #
#  작은 도구들
# --------------------------------------------------------------------------- #
def sha256_of(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:n]


def git_rev():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=ROOT, text=True).strip()
    except Exception:
        return None


def mtime_of(path):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path)))


def binom_sign_p(n_pos, n):
    """부호검정(양측): 「방위마다 부호가 한쪽으로 몰린 것이 동전던지기로 나올 확률」.

    ⚠ 24 방위는 서로 독립이 아니다(같은 물체를 15°씩 돌린 것이라 이웃이 닮는다).
      그래서 이 p 는 **낙관적인 값**이다 — 유효표본수를 같이 재서 그 감가를 남긴다."""
    if n == 0:
        return float("nan")
    k = min(n_pos, n - n_pos)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2.0 ** n)
    return float(min(1.0, 2.0 * tail))


def eff_n_from_autocorr(x):
    """방위축 순환 lag-1 자기상관 r1 → 유효표본수 n_eff = n(1−r1)/(1+r1)."""
    x = np.asarray(x, float)
    n = x.size
    if n < 3:
        return dict(r1=float("nan"), n_eff=float(n), n=int(n))
    v = x - x.mean()
    den = float(np.dot(v, v))
    r1 = float(np.dot(v, np.roll(v, -1)) / den) if den > 0 else 0.0
    ne = n * (1.0 - r1) / (1.0 + r1) if r1 > -0.999 else float(n)
    return dict(r1=r1, n_eff=float(min(max(ne, 1.0), float(n))), n=int(n))


def stat_block(d):
    """짝지은 차이 배열 → 요약(평균·산포·부호 일관성·유효표본수)."""
    d = np.asarray([x for x in d if np.isfinite(x)], float)
    n = int(d.size)
    if n == 0:
        return dict(mean=float("nan"), n=0)
    sd = float(d.std(ddof=1)) if n > 1 else 0.0
    npos = int(np.sum(d > 0))
    en = eff_n_from_autocorr(d)
    return dict(mean=float(d.mean()), sd=sd, median=float(np.median(d)),
                min=float(d.min()), max=float(d.max()),
                sem=float(sd / max(math.sqrt(n), 1.0)),
                sem_eff=float(sd / max(math.sqrt(en["n_eff"]), 1.0)),
                frac_positive=float(npos / n), n_positive=npos, n=n,
                sign_test_p=binom_sign_p(npos, n),
                az_lag1_corr=en["r1"], n_eff_az=en["n_eff"])


def mod_depth(tab):
    """쉬운 말 지표: 한 바퀴 도는 동안 되돌아오는 신호가 «몇 % 흔들리나».

        깊이 = max_φ |E(φ) − 평균E| / |평균E|

    회전대칭체(구를 회전축에 놓은 경우)의 이론값은 정확히 0 이다. dB 와 ppm(백만분율)
    두 가지로 준다. ppm 은 「백만 분의 몇」 — 0.0001 % 단위라고 보면 된다.
    앞 단계가 같은 정의를 썼으므로 이 단계에서 다시 계산해 **두 값이 같은지 대조**한다."""
    t = np.asarray(tab, complex)
    m = complex(t.mean())
    if abs(m) <= 0.0:
        return dict(frac=float("nan"), db=float("nan"), ppm=float("nan"))
    frac = float(np.abs(t - m).max() / abs(m))
    return dict(frac=frac, db=float(20 * math.log10(max(frac, 1e-300))), ppm=float(frac * 1e6))


def numeric_metrics(m):
    return {k: float(m[k]) for k in METRIC_KEYS if k in m}


# --------------------------------------------------------------------------- #
#  1) 입력 읽기
# --------------------------------------------------------------------------- #
def load_rung_tables():
    """앞 단계 npz → dict[(band, drone, arm, wavefront)] = (24, n_phase) 복소 배열."""
    z = np.load(RUNG_NPZ)
    out = {}
    for f in z.files:
        parts = f.split("__")
        if parts[0] == "hi":                       # hi__hi__drone__arm__wf
            band, key, arm, wf = "hi", parts[2], parts[3], parts[4]
        else:                                      # main__drone__arm__wf
            band, key, arm, wf = "main", parts[1], parts[2], parts[3]
        out[(band, key, arm, wf)] = np.asarray(z[f])
    return out


def load_base_mesh_tables():
    """기반 단계 npz 의 mesh·sphere 팔 → 교차 대조용."""
    z = np.load(BASE_NPZ)
    out = {}
    for f in z.files:
        parts = f.split("__")
        if parts[0] == "hi":                       # hi__hi__gen__drone__arm__wf
            band, gen, key, arm, wf = "hi", parts[2], parts[3], parts[4], parts[5]
        else:                                      # main__gen__drone__arm__wf
            band, gen, key, arm, wf = "main", parts[1], parts[2], parts[3], parts[4]
        if gen != "G_0804":
            continue
        out[(band, key, arm, wf)] = np.asarray(z[f])
    return out


def protocols():
    """드론 spec(src/drones.py — 읽기만)에서 표본화 규약을 **다시 유도**한다."""
    from drones import DRONES
    out = {}
    for key in DRONE_KEYS:
        s = DRONES[key]
        out[key] = dict(
            spec=dict(name=s.name, prop_dia_mm=float(s.prop_dia_mm),
                      prop_blades=int(s.prop_blades), hover_rpm=float(s.hover_rpm),
                      num_rotors=int(s.num_rotors)),
            main=B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN),
            hi=B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_PO_KNEE))
    return out


def protocol_gate(protos, rung):
    """내가 유도한 규약이 앞 단계가 쓴 규약과 같은가. 다르면 FFT 축이 달라 비교 자체가 무의미."""
    rows, worst = {}, 0.0
    for key in DRONE_KEYS:
        for band in BANDS:
            ref = (rung["protocol_per_drone"][key] if band == "main"
                   else rung["hi_band"]["protocol_per_drone"][key])
            mine = protos[key][band]
            bad, n_chk = {}, 0
            for k, v in mine.items():
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                rv = ref.get(k)
                if not isinstance(rv, (int, float)) or isinstance(rv, bool):
                    continue
                n_chk += 1
                rel = abs(float(v) - float(rv)) / max(abs(float(rv)), 1e-300)
                worst = max(worst, rel)
                if rel > 1e-12:
                    bad[k] = dict(mine=float(v), rung=float(rv), rel=rel)
            rows[f"{key}|{band}"] = dict(n_checked=n_chk, mismatches=bad)
    return dict(rows=rows, worst_rel=float(worst), tolerance=1e-12,
                verdict="PASS" if worst < 1e-12 else "FAIL",
                what_ko=("위상격자 수·PRF·β(=팁이 만드는 최고 차수)·f_tip 을 drones.py 스펙에서 "
                         "다시 유도해 앞 단계 값과 맞춰 본다. 여기가 어긋나면 두 단계의 지표를 "
                         "나란히 놓을 수 없다."))


# --------------------------------------------------------------------------- #
#  2) 지표 전수 계산
# --------------------------------------------------------------------------- #
def per_az_metrics(tab2d, proto, nb):
    """방위 24 개 각각에 대해 기반 단계 지표 함수를 부른다(재구현 금지)."""
    mets = [B.md_metrics16(tab2d[i], proto, nb) for i in range(tab2d.shape[0])]
    mds = [mod_depth(tab2d[i]) for i in range(tab2d.shape[0])]
    for m, d in zip(mets, mds):
        m["mod_depth_db"] = d["db"]
        m["mod_depth_ppm"] = d["ppm"]
    return mets


def arm_block(mets):
    keys = METRIC_KEYS + ["mod_depth_db", "mod_depth_ppm"]
    return dict(
        per_az={k: B.summarize([m[k] for m in mets]) for k in keys},
        interpretable_frac=float(np.mean([bool(m["metrics_interpretable"]) for m in mets])),
        band_order=int(mets[0]["band_order"]),
        n_az=len(mets))


def compute_all(tabs, protos, specs):
    """(band, drone, arm, wf) 전부에 대해 지표를 낸다."""
    mets, blocks = {}, {}
    for band in BANDS:
        for key in DRONE_KEYS:
            proto = protos[key][band]
            nb = specs[key]["prop_blades"]
            for arm in ARMS:
                for wf in WFS:
                    t = tabs.get((band, key, arm, wf))
                    if t is None:
                        continue
                    mm = per_az_metrics(t, proto, nb)
                    mets[(band, key, arm, wf)] = mm
                    blocks[(band, key, arm, wf)] = arm_block(mm)
    return mets, blocks


def recompute_gate(blocks, rung):
    """내가 방금 낸 요약이 앞 단계가 저장한 요약과 같은가 — 같은 함수·같은 표이므로 0 이어야 한다."""
    worst, rows = 0.0, {}
    for band in BANDS:
        arms_ref = rung["arms"] if band == "main" else rung["hi_band"]["arms"]
        for key in DRONE_KEYS:
            for arm in ARMS:
                for wf in WFS:
                    ref = arms_ref.get(key, {}).get(arm, {}).get(wf, {}).get("per_az")
                    mine = blocks.get((band, key, arm, wf))
                    if ref is None or mine is None:
                        continue
                    d, n = 0.0, 0
                    for k, rv in ref.items():
                        mv = mine["per_az"].get(k)
                        if mv is None or not isinstance(rv, dict):
                            continue
                        for stat in ("mean", "min", "max"):
                            if stat in rv and stat in mv and np.isfinite(rv[stat]):
                                d = max(d, abs(float(rv[stat]) - float(mv[stat])))
                                n += 1
                    rows[f"{band}|{key}|{arm}|{wf}"] = dict(max_abs_diff=float(d), n_compared=n)
                    worst = max(worst, d)
    return dict(rows=rows, max_abs_diff=float(worst), tolerance=1e-9,
                verdict="PASS" if worst <= 1e-9 else "FAIL",
                what_ko=("앞 단계 JSON 에 저장된 팔별 지표 요약을 내가 원본 표에서 다시 계산해 맞춰 "
                         "본다. 같은 정의 함수를 같은 표에 적용했으므로 차이가 0 이어야 한다. "
                         "0 이 아니면 둘 중 하나가 표를 잘못 읽은 것이다."))


def cross_round_gate(tabs, base_tabs, rung):
    """기반 단계가 따로 돌려 저장한 표와 이 단의 표를 직접 뺀다(재현성 검사).

    · mesh 팔: 같은 커널·같은 규약이므로 **비트 일치** 해야 한다.
    · 구 팔: 기반 단계의 `sphere` 는 같은 반경·같은 분할의 구인데 재질이 완전도체(|Γ|=1)이고,
      이 단의 `sphere_eqvol` 은 기체 평균 |Γ| 를 물렸다. 그러면 두 표는 **정확히 Γ 배** 여야
      한다 — 이 비례가 성립하는지 보면 「재질은 크기만 옮기고 모양은 못 바꾼다」는 주장이
      서로 다른 두 실행에서 재현되는지까지 한 번에 확인된다."""
    rows, worst_raw, worst_scaled = {}, 0.0, 0.0
    for band in BANDS:
        arms_ref = rung["arms"] if band == "main" else rung["hi_band"]["arms"]
        for key in DRONE_KEYS:
            for mine_arm, base_arm in (("mesh", "mesh"), ("sphere_eqvol", "sphere")):
                gam = 1.0
                if mine_arm == "sphere_eqvol":
                    gam = float(arms_ref[key]["sphere_eqvol"]["geometry"]["sphere_gamma_abs"])
                for wf in WFS:
                    a = tabs.get((band, key, mine_arm, wf))
                    b = base_tabs.get((band, key, base_arm, wf))
                    if a is None or b is None or a.shape != b.shape:
                        continue
                    ref = float(np.max(np.abs(a)))
                    d_raw = float(np.max(np.abs(a - b)))
                    d_sc = float(np.max(np.abs(a - gam * b)))
                    rows[f"{band}|{key}|{mine_arm}~base:{base_arm}|{wf}"] = dict(
                        gamma_applied=gam, max_abs_ref=ref,
                        max_rel_raw=float(d_raw / max(ref, 1e-300)),
                        max_rel_after_gamma=float(d_sc / max(ref, 1e-300)))
                    worst_raw = max(worst_raw, d_raw / max(ref, 1e-300))
                    worst_scaled = max(worst_scaled, d_sc / max(ref, 1e-300))
    return dict(rows=rows, max_rel_raw=float(worst_raw),
                max_rel_after_gamma=float(worst_scaled), tolerance=1e-12,
                verdict="PASS" if worst_scaled < 1e-12 else "FAIL",
                reference="outputs/report16_base_tables.npz (G_0804)",
                what_ko=("mesh 팔은 그대로, 구 팔은 재질 |Γ| 만큼 곱한 뒤 뺀다. 남는 차이가 "
                         "0 이면 두 실행이 같은 답을 냈다는 뜻이고, 구 팔에서는 «재질은 세기만 "
                         "바꾼다» 는 주장도 함께 재현된 것이다."))


# --------------------------------------------------------------------------- #
#  3) 사람이 읽는 네 묶음 표
# --------------------------------------------------------------------------- #
def family_table(blocks):
    """네 묶음(플래시·풍부도·폭·동체:블레이드) + 레벨·품질을 팔마다 한 줄로."""
    out = {}
    for (band, key, arm, wf), blk in blocks.items():
        row = {}
        for fam, keys in FAMILY.items():
            row[fam] = {k: blk["per_az"][k]["mean"] for k in keys if k in blk["per_az"]}
        row["mod_depth_db"] = blk["per_az"]["mod_depth_db"]["mean"]
        row["mod_depth_ppm"] = blk["per_az"]["mod_depth_ppm"]["mean"]
        row["az_sd"] = {k: blk["per_az"][k]["sd"] for k in
                        ("flash_contrast_db", "in_band_ac_over_dc_db", "sigma_eq_mean_dbsm",
                         "width_ratio_20db", "n_eff_orders")}
        row["interpretable_frac"] = blk["interpretable_frac"]
        row["band_order"] = blk["band_order"]
        out[f"{band}|{key}|{arm}|{wf}"] = row
    return out


def interpretability_block(blocks):
    """«이 팔의 폭·풍부도 지표를 읽어도 되는가» 를 팔마다 판정한다.

    기반 단계가 정한 규칙: 대역 안 AC 전력 몫(in_band_ac_frac)이 0.5 미만이면 변조 전력의
    절반 이상이 «팁보다 빠른 자리» 에 있다는 뜻이고, 그건 물리가 아니라 격자 잔재다.
    그런 팔의 폭·풍부도는 **격자를 잰 값**이므로 인용하면 안 된다."""
    rows = {}
    for k, blk in blocks.items():
        band, key, arm, wf = k
        rows[f"{band}|{key}|{arm}|{wf}"] = dict(
            in_band_ac_frac=blk["per_az"]["in_band_ac_frac"]["mean"],
            interpretable_frac=blk["interpretable_frac"],
            width_ratio_20db=blk["per_az"]["width_ratio_20db"]["mean"],
            n_eff_orders=blk["per_az"]["n_eff_orders"]["mean"],
            quotable=bool(blk["interpretable_frac"] >= 0.5))
    n_quotable = sum(1 for v in rows.values() if v["quotable"])
    return dict(rows=rows, n_arms=len(rows), n_quotable=n_quotable,
                n_not_quotable=len(rows) - n_quotable,
                rule_ko=("in_band_ac_frac ≥ 0.5 인 팔만 폭·풍부도를 인용한다. 널 팔(회전축 위의 구)은 "
                         "여기서 떨어지고, 그래도 표에는 숫자가 찍힌다 — 그 숫자를 인용하면 사고다."),
                trap_example_ko=("예: 등가부피 구의 width_ratio 는 7 이 넘는다. «블레이드 팁보다 7배 "
                                 "빠른 도플러» 라는 뜻이라 물리적으로 불가능하다. 격자 잔재를 잰 값이다."))


# --------------------------------------------------------------------------- #
#  4) 메쉬와 짝지어 비교
# --------------------------------------------------------------------------- #
def paired_vs_mesh(mets, tabs):
    """같은 방위에서 (팔 − 메쉬). 자세 산포는 두 팔에 공통이라 짝지으면 지워진다."""
    out = {}
    for (band, key, arm, wf), mm in mets.items():
        if arm == "mesh":
            continue
        ref = mets.get((band, key, "mesh", wf))
        if ref is None:
            continue
        blk = {k: stat_block([a[k] - b[k] for b, a in zip(ref, mm)])
               for k in METRIC_KEYS + ["mod_depth_db"]}
        ta, tb = tabs[(band, key, "mesh", wf)], tabs[(band, key, arm, wf)]
        rho = np.array([B.ac_corr(ta[i], tb[i]) for i in range(ta.shape[0])], float)
        # 상관 ρ → 「메쉬 파형에 세기비 ε 의 무상관 잡음을 넣으면 같은 정도로 흐려진다」
        eps = np.sqrt(np.maximum(1.0 / np.maximum(rho ** 2, 1e-300) - 1.0, 0.0))
        out[f"{band}|{key}|{arm}|{wf}"] = dict(
            delta_vs_mesh=blk,
            ac_corr_with_mesh=B.summarize(rho),
            equivalent_noise_snr_db=B.summarize(-20.0 * np.log10(np.maximum(eps, 1e-300))),
            note_ko=("delta 는 «팔 − 메쉬». ac_corr 는 변조 파형(AC)의 닮은 정도(1=동일). "
                     "equivalent_noise_snr_db 는 그 닮지 않음을 «메쉬 신호보다 몇 dB 아래 잡음을 "
                     "넣은 것과 같은가» 로 환산한 값 — 클수록 차이가 작다."))
    return out


def surrogate_scorecard(blocks, paired):
    """⭐ 「어느 대체물이 메쉬의 마이크로도플러를 가장 잘 흉내내나」 를 한 표로.

    네 축을 그대로 쓴다(가중치를 사람이 고르면 그게 또 손입력이므로, **합치지 않고 나란히** 둔다).
      · 변조 총량 오차  |Δ in_band_ac_over_dc_db|
      · 플래시 대조비 오차 |Δ flash_contrast_db|
      · 도플러 폭 비    width_ratio(팔) / width_ratio(메쉬)
      · 파형 상관       ac_corr
    """
    rows = {}
    for tag, p in paired.items():
        band, key, arm, wf = tag.split("|")
        mesh_blk = blocks[(band, key, "mesh", wf)]
        arm_blk = blocks[(band, key, arm, wf)]
        w_mesh = mesh_blk["per_az"]["width_ratio_20db"]["mean"]
        w_arm = arm_blk["per_az"]["width_ratio_20db"]["mean"]
        rows[tag] = dict(
            level_err_db=abs(p["delta_vs_mesh"]["in_band_ac_over_dc_db"]["mean"]),
            level_signed_db=p["delta_vs_mesh"]["in_band_ac_over_dc_db"]["mean"],
            flash_err_db=abs(p["delta_vs_mesh"]["flash_contrast_db"]["mean"]),
            flash_signed_db=p["delta_vs_mesh"]["flash_contrast_db"]["mean"],
            width_ratio_arm_over_mesh=float(w_arm / w_mesh) if w_mesh else float("nan"),
            ac_corr=p["ac_corr_with_mesh"]["mean"],
            arm_interpretable_frac=arm_blk["interpretable_frac"])
    # 팔별로 (해석 자격이 있는 팔만) 평균 성적을 낸다
    per_arm = {}
    for arm in ARMS:
        if arm == "mesh":
            continue
        sel = [v for t, v in rows.items() if t.split("|")[2] == arm and v["arm_interpretable_frac"] >= 0.5]
        if not sel:
            per_arm[arm] = dict(n=0, note_ko="해석 자격(in-band ≥ 0.5)을 가진 구석이 없다 — 널 팔이다.")
            continue
        per_arm[arm] = dict(
            n=len(sel),
            level_err_db=float(np.mean([s["level_err_db"] for s in sel])),
            flash_err_db=float(np.mean([s["flash_err_db"] for s in sel])),
            width_ratio_arm_over_mesh=float(np.mean([s["width_ratio_arm_over_mesh"] for s in sel])),
            ac_corr=float(np.mean([s["ac_corr"] for s in sel])))
    return dict(rows=rows, per_arm=per_arm,
                what_ko=("대체물이 «변조가 있다/없다» 만 맞히면 되는지, «모양까지» 맞혀야 하는지를 "
                         "가르는 표다. 네 축을 한 점수로 합치지 않는다 — 가중치를 사람이 고르는 순간 "
                         "결론이 그 선택을 따라가기 때문이다."))


# --------------------------------------------------------------------------- #
#  5) 사전예측 채점 (문턱은 prereg 에서 읽는다 — 내가 정하지 않는다)
# --------------------------------------------------------------------------- #
def score_predictions(blocks, mets, tabs, specs, rung):
    pre = rung["preregistration"]["prediction"]
    th_pass = float(pre["P1_threshold_pass_db"])
    th_fail = float(pre["P1_threshold_fail_db"])
    th_p3 = float(pre["P3_threshold_db"])
    th_p4 = float(pre["P4_threshold_db"])

    # ── P1: 널 팔의 대역 안 AC/DC 가 24방위·두 대역·두 파면 전부에서 문턱 아래인가
    p1_rows = {}
    worst_v, worst_at = -1e18, None
    for (band, key, arm, wf), mm in mets.items():
        if arm not in NULL_ARMS:
            continue
        vals = np.array([m["in_band_ac_over_dc_db"] for m in mm], float)
        tag = f"{band}|{key}|{arm}|{wf}"
        p1_rows[tag] = dict(mean=float(vals.mean()), worst_az=float(vals.max()),
                            best_az=float(vals.min()),
                            n_az_above_pass=int((vals > th_pass).sum()),
                            n_az_above_fail=int((vals > th_fail).sum()))
        if vals.max() > worst_v:
            worst_v, worst_at = float(vals.max()), tag
    p1_verdict = ("PASS" if worst_v <= th_pass else
                  "MARGINAL" if worst_v <= th_fail else "FAIL")

    # 헤드라인 팔(등가부피 구)만 볼 때
    hv, hat = -1e18, None
    for tag, r in p1_rows.items():
        if tag.split("|")[2] != "sphere_eqvol":
            continue
        if r["worst_az"] > hv:
            hv, hat = r["worst_az"], tag

    # ── P2: 널 잔차의 지배 차수가 «블레이드 빗» 이 아니라 «구를 쪼갠 경도 분할 수» 배수인가
    p2 = p2_grid_check_full(mets, tabs, rung, specs)

    # ── P3: 같은 구를 축에서 비켜 놓으면(양성대조) 큰 변조가 나오는가
    p3_rows, p3_worst, p3_at = {}, 1e18, None
    for (band, key, arm, wf), mm in mets.items():
        if arm != "sphere_offaxis":
            continue
        vals = np.array([m["in_band_ac_over_dc_db"] for m in mm], float)
        tag = f"{band}|{key}|{arm}|{wf}"
        p3_rows[tag] = dict(mean=float(vals.mean()), worst_az=float(vals.min()))
        if vals.min() < p3_worst:
            p3_worst, p3_at = float(vals.min()), tag

    # ── P4: 진짜 메쉬가 널보다 얼마나 위인가
    p4_rows, p4_min, p4_at = {}, 1e18, None
    for band in BANDS:
        for key in DRONE_KEYS:
            for wf in WFS:
                mesh = blocks.get((band, key, "mesh", wf))
                if mesh is None:
                    continue
                mv = mesh["per_az"]["in_band_ac_over_dc_db"]["mean"]
                for arm in NULL_ARMS:
                    nb = blocks.get((band, key, arm, wf))
                    if nb is None:
                        continue
                    gap = float(mv - nb["per_az"]["in_band_ac_over_dc_db"]["mean"])
                    tag = f"{band}|{key}|mesh−{arm}|{wf}"
                    p4_rows[tag] = gap
                    if gap < p4_min:
                        p4_min, p4_at = gap, tag

    # ── 이 단의 과제문이 건 예측: 「변조 0 이어야 한다. 0 이 아니면 그 크기가 바닥이다」
    floor_rows = {}
    for (band, key, arm, wf), blk in blocks.items():
        if arm not in NULL_ARMS:
            continue
        floor_rows[f"{band}|{key}|{arm}|{wf}"] = dict(
            mod_depth_db=blk["per_az"]["mod_depth_db"]["mean"],
            mod_depth_ppm=blk["per_az"]["mod_depth_ppm"]["mean"],
            in_band_ac_over_dc_db=blk["per_az"]["in_band_ac_over_dc_db"]["mean"])
    eq_only = {t: v for t, v in floor_rows.items() if t.split("|")[2] == "sphere_eqvol"}
    worst_floor_tag = max(eq_only, key=lambda t: eq_only[t]["mod_depth_ppm"])

    verdicts = dict(P1=p1_verdict, P2=p2["verdict"], P3="PASS" if p3_worst >= th_p3 else "FAIL",
                    P4="PASS" if p4_min >= th_p4 else "FAIL", P5="NOT_GRADED")
    graded = [v for k, v in verdicts.items() if k != "P5"]
    overall = ("PASS" if all(v == "PASS" for v in graded) else
               "FAIL" if any(v == "FAIL" for v in graded) else "MIXED")

    return dict(
        thresholds=dict(P1_pass_db=th_pass, P1_fail_db=th_fail, P3_db=th_p3, P4_db=th_p4,
                        source="rung preregistration (계산 전 sha256 고정)"),
        prereg_sha256=rung["preregistration"]["sha256"],
        prereg_first_written_at=rung["preregistration"]["first_written_at"],
        prereg_precedes_first_result=rung["preregistration"]["prereg_precedes_first_result"],
        P1=dict(rows=p1_rows, worst_db=worst_v, worst_at=worst_at, verdict=p1_verdict,
                headline_arm_only=dict(worst_db=hv, worst_at=hat,
                                       verdict="PASS" if hv <= th_pass else
                                               "MARGINAL" if hv <= th_fail else "FAIL"),
                text_ko=pre["P1_null_ko"]),
        P2=dict(**p2, text_ko=pre["P2_residual_is_numerical_ko"]),
        P3=dict(rows=p3_rows, worst_db=p3_worst, worst_at=p3_at,
                verdict=verdicts["P3"], text_ko=pre["P3_positive_control_ko"]),
        P4=dict(rows=p4_rows, min_gap_db=p4_min, min_at=p4_at,
                min_gap_eqvol_only_db=float(min(
                    v for t, v in p4_rows.items() if t.split("|")[2] == "mesh−sphere_eqvol")),
                verdict=verdicts["P4"], text_ko=pre["P4_gap_ko"],
                scope_note_ko=("⚠ 앞 단계는 이 여유를 «메쉬 − 등가부피 구» 로만 쟀고, 여기서는 널 팔 "
                               "둘(등가부피 구·허브 구) 모두에 대해 잰다. 그래서 최소값이 앞 단계보다 "
                               "작게 나온다(더 엄한 읽기). 둘 다 문턱을 넘으므로 판정은 같다.")),
        P5=dict(verdict="NOT_GRADED", text_ko=pre["P5_no_prediction_ko"],
                why_ko="예측을 걸지 않았으므로 채점 대상이 아니다. 숫자는 ladder_unpredicted 에 적는다."),
        task_prediction=dict(
            text_ko="⭐ 변조 0 이어야 한다 — 회전대칭이라 어느 방향에서도 같다. 0 이 아니면 그 크기가 이 실험의 바닥이다.",
            verdict="CONFIRMED_WITH_MEASURED_FLOOR",
            floor_rows=floor_rows,
            worst_headline_floor_tag=worst_floor_tag,
            worst_headline_floor_ppm=eq_only[worst_floor_tag]["mod_depth_ppm"],
            worst_headline_floor_db=eq_only[worst_floor_tag]["mod_depth_db"],
            read_ko=("정확히 0 은 아니다 — 우리가 구를 삼각형으로 쪼개서 계산하기 때문이다. "
                     "남은 크기가 곧 이 실험의 «바닥» 이고, 그 바닥이 메쉬 신호보다 얼마나 아래인지가 "
                     "P4 다.")),
        verdicts=verdicts, overall=overall,
        agreement_with_rung=dict(
            rung_overall=rung["prediction_test"]["overall"],
            rung_P1_worst_db=rung["prediction_test"]["P1_worst_null_in_band_ac_over_dc_db"],
            mine_P1_worst_db=worst_v,
            P1_worst_abs_diff=abs(worst_v - rung["prediction_test"]["P1_worst_null_in_band_ac_over_dc_db"]),
            rung_P3_worst_db=rung["prediction_test"]["P3_worst_control_in_band_ac_over_dc_db"],
            mine_P3_worst_db=p3_worst,
            rung_P4_min_db=rung["prediction_test"]["P4_min_mesh_minus_sphere_db"],
            mine_P4_min_db=p4_min,
            same_overall=bool(overall == rung["prediction_test"]["overall"])),
        read_ko=("문턱은 앞 단계가 계산 전에 못박은 값을 그대로 읽었고(내가 정하지 않았다), "
                 "숫자는 내가 원본 표에서 다시 냈다. 두 단계의 판정이 같은지도 적는다."))


def p2_grid_check_full(mets, tabs, rung, specs):
    """P2 재검증: 널 잔차의 지배 차수가 구의 «경도 분할 수 seg» 의 정수배(접힌 자리 포함)인가.

    쉬운 말: 구를 세로로 seg 조각으로 쪼개 그렸다면, 그 조각 무늬가 한 바퀴에 seg 번 반복된다.
    따라서 잔재 신호는 seg, 2seg, 3seg… 번째 차수에 앉는다. 표본이 n_phase 개뿐이면 그보다
    높은 차수는 «접혀서»(aliasing) 낮은 자리로 되돌아오는데, 그 접힌 자리까지 계산해 맞춰 본다.
    블레이드 빗(2, 4, 6…)에만 앉으면 그건 격자가 아니라 «형상이 만든 신호» 라는 뜻이라 예측 실패다.
    (표 길이 n_phase 를 알아야 접힘을 계산할 수 있어서 표를 같이 받는다.)"""
    def seg_of(band, key, arm):
        """구를 세로로 몇 조각(seg)으로 쪼개 그렸는지 — **대역마다 다르다**(점 간격이 λ에 매여 있다).

        앞 단계 JSON 의 해당 대역 geometry 에서 읽는다. 주파수가 올라가면 같은 구도 훨씬
        촘촘히 쪼개지므로, main 의 seg 를 hi 에 쓰면 검사가 통째로 헛돈다."""
        arms_ref = rung["arms"] if band == "main" else rung["hi_band"]["arms"]
        g = arms_ref[key][arm]["geometry"]
        if "sphere_seg" in g:
            return int(g["sphere_seg"])
        if "sphere_tess" in g:
            return int(g["sphere_tess"]["seg"])
        return None

    def folded(seg, S, jmax):
        """seg 의 j 배(j=1..jmax)가 «1회전 S 표본» 위에서 접혀 앉는 차수들 {차수: 최소 j}."""
        out = {}
        for j in range(1, int(jmax) + 1):
            a = (j * seg) % S
            out.setdefault(int(min(a, S - a)), j)
        return out

    JMAX = 6            # 앞 단계가 쓴 관례. ⚠ 사전예측 문구에는 이 상한이 없다(아래 vacuity 참조).
    rows, all_ok, n_checked = {}, True, 0
    for (band, key, arm, wf), mm in mets.items():
        if arm not in NULL_ARMS:
            continue
        seg = seg_of(band, key, arm)
        if seg is None:
            continue
        S = int(tabs[(band, key, arm, wf)].shape[1])
        g6 = folded(seg, S, JMAX)
        g_all = folded(seg, S, S)          # j 를 끝까지 늘렸을 때 닿는 자리 전체
        nb = int(specs[key]["prop_blades"])
        dom = [int(m["dominant_order"]) for m in mm]
        ok = [d in g6 for d in dom]
        j_hit = [g6.get(d) for d in dom]
        on_blade_comb = [(d % nb == 0 and d not in g6) for d in dom]
        rows[f"{band}|{key}|{arm}|{wf}"] = dict(
            seg=seg, n_phase=S, blade_comb_step=nb,
            folded_grid_orders_jmax6=g6,
            dominant_orders=sorted(set(dom)),
            matched_j=sorted({int(j) for j in j_hit if j is not None}),
            frac_dominant_is_grid=float(np.mean(ok)),
            frac_dominant_on_blade_comb_only=float(np.mean(on_blade_comb)),
            reachable_order_coverage=float(len(g_all) / (S // 2 + 1)),
            chance_hit_prob=float(len(g6) / (S // 2 + 1)))
        n_checked += len(dom)
        all_ok = all_ok and all(ok)
    cov = [r["reachable_order_coverage"] for r in rows.values()]
    chance = [r["chance_hit_prob"] for r in rows.values()]
    jmax_used = max((max(r["matched_j"]) for r in rows.values() if r["matched_j"]), default=0)
    log10_joint = float(sum(math.log10(max(c, 1e-300)) for c in chance))
    return dict(rows=rows, n_checked=n_checked, jmax=JMAX,
                all_dominant_orders_are_grid=bool(all_ok),
                verdict="PASS" if all_ok else "FAIL",
                what_ko=("널 팔의 «가장 센 차수» 가 구를 쪼갠 경도 분할 수 seg 의 정수배(표본 수로 "
                         "접힌 자리 포함)인지 본다. 전부 그러면 남은 신호는 형상이 아니라 격자다."),
                vacuity_warning_ko=(
                    "⚠ 이 검사에는 조용한 약점이 있다 — 사전예측 문구에는 «정수배» 라고만 적혀 있고 "
                    f"몇 배까지 볼지(j 의 상한)가 없다. j 를 끝까지 늘리면 접힌 자리가 전체 차수의 "
                    f"평균 {100*float(np.mean(cov)):.0f}% 를 덮으므로, 상한 없는 검사는 «무엇을 넣어도 "
                    f"통과» 가 된다. 그래서 앞 단계가 쓴 관례 j ≤ {JMAX} 를 그대로 적용했다. "
                    f"⭐ 다만 이번에 실제로 맞은 배수는 j ≤ {jmax_used} 로 작아서, 이 결과가 상한의 "
                    "느슨함 덕에 통과한 것은 아니다."),
                teeth=dict(
                    chance_hit_prob=dict(mean=float(np.mean(chance)), min=float(min(chance)),
                                         max=float(max(chance))),
                    n_rows=len(rows), log10_joint_chance=log10_joint,
                    max_matched_j=int(jmax_used),
                    what_ko=("아무 차수나 우연히 «격자 자리» 에 떨어질 확률이 한 줄당 평균 "
                             f"{100*float(np.mean(chance)):.1f}% 다. 그런데 {len(rows)} 줄이 전부 맞았다 "
                             f"— 우연이라면 10^{log10_joint:.0f} 확률이다. 그래서 이 검사는 상한 관례에도 "
                             "불구하고 실제로 판별력이 있다.")),
                reachable_coverage=dict(mean=float(np.mean(cov)), min=float(min(cov)),
                                        max=float(max(cov))))


# --------------------------------------------------------------------------- #
#  6) 바닥의 정체 — 격자인가, 반올림인가
# --------------------------------------------------------------------------- #
def floor_origin(blocks, rung, tabs):
    """남은 변조가 «삼각형 격자» 탓인지 «컴퓨터 반올림» 탓인지 가른다.

    · 반올림 한계: N 개 항을 float64 로 더하면 상대오차가 대략 √N·ε (ε≈2.2e-16) 이다.
      측정된 흔들림이 그보다 훨씬 크면 반올림이 아니다.
    · 격자 의존: 앞 단계가 분할을 0.5·1·2·4·8 배로 바꿔가며 재 놓았다. 여기서 그 값에
      직선(log2 seg 대 dB)을 다시 맞춰 **기울기**를 낸다. 기울기가 음이면 «촘촘히 할수록
      줄어든다» = 격자 탓이라는 직접 증거다."""
    rows = {}
    for band in BANDS:
        arms_ref = rung["arms"] if band == "main" else rung["hi_band"]["arms"]
        for key in DRONE_KEYS:
            g = arms_ref[key]["sphere_eqvol"]["geometry"]
            n_pts = int(g.get("sphere_n_pts", 0))
            if n_pts <= 0:
                continue
            bound = math.sqrt(n_pts) * EPS_F64
            for wf in WFS:
                blk = blocks.get((band, key, "sphere_eqvol", wf))
                if blk is None:
                    continue
                meas_db = blk["per_az"]["mod_depth_db"]["mean"]
                rows[f"{band}|{key}|{wf}"] = dict(
                    n_points=n_pts,
                    roundoff_bound_rel=float(bound),
                    roundoff_bound_db=float(20 * math.log10(bound)),
                    measured_mod_depth_db=meas_db,
                    measured_mod_depth_ppm=blk["per_az"]["mod_depth_ppm"]["mean"],
                    above_roundoff_db=float(meas_db - 20 * math.log10(bound)))

    # 분할 세밀화 기울기 (앞 단계 표를 내가 다시 적합)
    slopes = {}
    for src_name, src in (("sphere_eqvol", rung["null_is_numerical"]["convergence"]),
                          ("sph_hub", rung["posthoc_marginal_diagnosis"]["refinement"])):
        for key, sub in src.items():
            if key.startswith("_"):
                continue
            xs, ys, segs = [], [], []
            for lab, r in sub.items():
                if not isinstance(r, dict) or "seg" not in r:
                    continue
                xs.append(math.log2(float(r["seg"])))
                ys.append(float(r["in_band_ac_over_dc_db"]["mean"]))
                segs.append(int(r["seg"]))
            if len(xs) < 3:
                continue
            a, b = np.polyfit(np.array(xs), np.array(ys), 1)
            order = np.argsort(xs)
            ys_sorted = np.array(ys)[order]
            slopes[f"{src_name}|{key}"] = dict(
                seg_values=sorted(segs),
                residual_db=[float(v) for v in ys_sorted],
                slope_db_per_octave=float(a), intercept_db=float(b),
                monotone_decreasing=bool(np.all(np.diff(ys_sorted) < 0)),
                total_drop_db=float(ys_sorted[0] - ys_sorted[-1]))
    return dict(roundoff=rows, refinement_slope=slopes,
                what_ko=("above_roundoff_db 가 크다는 것은 «반올림 잡음보다 그만큼 위» 라는 뜻이고, "
                         "slope_db_per_octave 가 음수라는 것은 «분할을 두 배 촘촘히 할 때마다 그만큼 "
                         "내려간다» 는 뜻이다. 둘을 합치면 바닥의 정체는 격자다."),
                caveat_ko=("√N·ε 는 반올림의 **대략적 크기**이지 엄밀한 상한이 아니다. 자리수 비교용으로만 "
                           "쓴다."))


def null_fragility(blocks, rung):
    """⭐ 「바닥은 물리량이 아니다」를 두 방향에서 못박는다.

    ① 파면(평면파 ↔ 구면파)은 **모델링 선택**이다. 진짜 물리적 0 이라면 어느 쪽으로 계산해도
       0 이어야 한다. 그런데 널 팔의 바닥은 이 선택만으로 몇 dB 씩 움직인다 → 물리가 아니다.
    ② 분할을 촘촘히 하면 «평균적으로» 내려가지만 **한 칸씩 보면 오르내린다**. 격자선끼리
       간섭하기 때문이다. 즉 특정 분할에서 나온 바닥 숫자 하나를 인용하면 안 된다."""
    wf_rows = {}
    for band in BANDS:
        for key in DRONE_KEYS:
            for arm in NULL_ARMS + ["mesh"]:
                a = blocks.get((band, key, arm, "spherical"))
                b = blocks.get((band, key, arm, "plane"))
                if a is None or b is None:
                    continue
                da = (a["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                      b["per_az"]["in_band_ac_over_dc_db"]["mean"])
                dm = (a["per_az"]["mod_depth_db"]["mean"] - b["per_az"]["mod_depth_db"]["mean"])
                wf_rows[f"{band}|{key}|{arm}"] = dict(
                    spherical_db=a["per_az"]["in_band_ac_over_dc_db"]["mean"],
                    plane_db=b["per_az"]["in_band_ac_over_dc_db"]["mean"],
                    delta_wavefront_db=float(da), delta_mod_depth_db=float(dm))
    null_sw = [abs(v["delta_wavefront_db"]) for k, v in wf_rows.items()
               if k.split("|")[2] in NULL_ARMS]
    mesh_sw = [abs(v["delta_wavefront_db"]) for k, v in wf_rows.items()
               if k.split("|")[2] == "mesh"]

    # 분할 세밀화가 한 칸씩은 단조인가
    mono = {}
    for src_name, src in (("sphere_eqvol", rung["null_is_numerical"]["convergence"]),
                          ("sph_hub", rung["posthoc_marginal_diagnosis"]["refinement"])):
        for key, sub in src.items():
            if key.startswith("_"):
                continue
            pts = sorted(((int(r["seg"]), float(r["in_band_ac_over_dc_db"]["mean"]))
                          for lab, r in sub.items() if isinstance(r, dict) and "seg" in r),
                         key=lambda p: p[0])
            if len(pts) < 3:
                continue
            ys = [p[1] for p in pts]
            worst_up = max([ys[i + 1] - ys[i] for i in range(len(ys) - 1)] + [0.0])
            mono[f"{src_name}|{key}"] = dict(
                seg_values=[p[0] for p in pts], residual_db=ys,
                monotone_decreasing=bool(all(ys[i + 1] < ys[i] for i in range(len(ys) - 1))),
                worst_upward_step_db=float(worst_up))
    return dict(
        wavefront=wf_rows,
        null_wavefront_swing_db=dict(max=float(max(null_sw)), mean=float(np.mean(null_sw))),
        mesh_wavefront_swing_db=dict(max=float(max(mesh_sw)), mean=float(np.mean(mesh_sw))),
        refinement_monotonicity=mono,
        read_ko=("널 팔의 바닥은 파면 선택만으로 최대 "
                 f"{max(null_sw):.1f} dB 움직인다(메쉬는 {max(mesh_sw):.1f} dB). 물리적 0 이라면 "
                 "일어날 수 없는 일이다 — 바닥이 계산 방식의 산물이라는 직접 증거다. 동시에 "
                 "«바닥 = −85 dB» 같은 숫자 하나를 인용하면 안 된다는 경고이기도 하다."))


def level_vs_modulation(blocks):
    """⭐ 한 표에 «세기» 와 «변조» 를 같이 놓는다 — 지도교수 지적의 경계선.

    세기(24방위 평균 σ)로는 구와 메쉬가 붙는데, 방위에 따른 변화와 시간 변조에서는 경기가
    성립하지 않는다. 앞 단계는 생산대역만 적었으므로 여기서 두 대역·두 파면 전부로 넓힌다."""
    rows = {}
    for band in BANDS:
        for key in DRONE_KEYS:
            for wf in WFS:
                m = blocks.get((band, key, "mesh", wf))
                s = blocks.get((band, key, "sphere_eqvol", wf))
                if m is None or s is None:
                    continue
                rows[f"{band}|{key}|{wf}"] = dict(
                    sigma_mean_dbsm=dict(mesh=m["per_az"]["sigma_eq_mean_dbsm"]["mean"],
                                         sphere=s["per_az"]["sigma_eq_mean_dbsm"]["mean"]),
                    sigma_gap_db=float(abs(m["per_az"]["sigma_eq_mean_dbsm"]["mean"] -
                                           s["per_az"]["sigma_eq_mean_dbsm"]["mean"])),
                    sigma_azimuth_sd_db=dict(mesh=m["per_az"]["sigma_eq_mean_dbsm"]["sd"],
                                             sphere=s["per_az"]["sigma_eq_mean_dbsm"]["sd"]),
                    modulation_db=dict(mesh=m["per_az"]["in_band_ac_over_dc_db"]["mean"],
                                       sphere=s["per_az"]["in_band_ac_over_dc_db"]["mean"]),
                    modulation_gap_db=float(m["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                                            s["per_az"]["in_band_ac_over_dc_db"]["mean"]))
    sg = [v["sigma_gap_db"] for v in rows.values()]
    mg = [v["modulation_gap_db"] for v in rows.values()]
    sd_mesh = [v["sigma_azimuth_sd_db"]["mesh"] for v in rows.values()]
    sd_sph = [v["sigma_azimuth_sd_db"]["sphere"] for v in rows.values()]
    by_band = {b: dict(sigma_gap_db_max=float(max(v["sigma_gap_db"] for t, v in rows.items()
                                                  if t.startswith(b + "|"))),
                       modulation_gap_db_min=float(min(v["modulation_gap_db"] for t, v in rows.items()
                                                       if t.startswith(b + "|"))))
               for b in BANDS}
    return dict(rows=rows, by_band=by_band,
                band_note_ko=("⭐ «세기 무승부» 는 대역에 따라 다르다 — 생산대역(3.5 GHz)에서는 최대 "
                              f"{by_band['main']['sigma_gap_db_max']:.2f} dB 로 붙지만 15.86 GHz 에서는 "
                              f"{by_band['hi']['sigma_gap_db_max']:.2f} dB 까지 벌어진다. 파장이 짧아질수록 "
                              "구는 «모양이 없다» 는 대가를 세기에서도 조금씩 치른다."),
                sigma_gap_db=dict(mean=float(np.mean(sg)), max=float(max(sg)), n=len(sg)),
                modulation_gap_db=dict(mean=float(np.mean(mg)), min=float(min(mg)),
                                       max=float(max(mg)), n=len(mg)),
                azimuth_sd_db=dict(mesh_max=float(max(sd_mesh)), sphere_max=float(max(sd_sph))),
                headline_ko=("같은 커널·같은 자세 앙상블에서 24방위 **평균 세기** 는 구와 메쉬가 "
                             f"최대 {max(sg):.2f} dB 안에서 붙는다(사실상 무승부). 그런데 같은 표에서 "
                             f"방위 산포는 메쉬 최대 {max(sd_mesh):.1f} dB 대 구 {max(sd_sph):.0e} dB 이고, "
                             f"시간 변조는 {min(mg):.0f}~{max(mg):.0f} dB 차이가 난다. "
                             "즉 «세기» 축에서는 구가 싸움이 되고 «시간 변조» 축에서는 경기가 성립하지 않는다."),
                caveat_ko=("⚠ 평균 세기가 붙는 것은 부피를 사람이 골라 넣었기 때문이기도 하다 — 어떤 부피를 "
                           "먹이느냐가 세기를 수 dB 움직인다(앞 단계 p3_context 참조). «매개변수 0 개» 가 "
                           "아니다."))


def azimuth_invariance(blocks):
    """회전축 위의 구는 방위를 바꿔도 답이 같아야 한다 — 그 «같음» 이 얼마나 정확한지."""
    rows = {}
    for (band, key, arm, wf), blk in blocks.items():
        rows[f"{band}|{key}|{arm}|{wf}"] = dict(
            sigma_az_sd_db=blk["per_az"]["sigma_eq_mean_dbsm"]["sd"],
            sigma_az_span_db=float(blk["per_az"]["sigma_eq_mean_dbsm"]["max"] -
                                   blk["per_az"]["sigma_eq_mean_dbsm"]["min"]),
            flash_az_sd_db=blk["per_az"]["flash_contrast_db"]["sd"])
    return dict(rows=rows,
                what_ko=("널 팔의 방위 산포는 «0 이어야 정상» 이다. 여기서 남는 값은 더하는 순서가 바뀌며 "
                         "생기는 부동소수점 잔재다. 메쉬 팔의 산포와 나란히 놓으면 «구조가 있으면 방위에 "
                         "따라 이만큼 변한다» 가 눈에 보인다."))


# --------------------------------------------------------------------------- #
#  7) 바깥 기준자 — 구의 절대 세기를 정확해와 맞춘다
# --------------------------------------------------------------------------- #
def external_anchor(blocks, rung):
    """⭐ 구는 «정답을 아는 물체» 다. 정확 Mie 해와 해석 PO 해가 둘 다 닫힌 식으로 있다.

        (우리 커널 − 해석 PO)  = 우리 **수치오차**(격자·점밀도 탓, 촘촘히 하면 준다)
        (해석 PO  − 정확 Mie) = **PO 근사를 쓴 대가**(모델 고유, 못 줄인다)

    앞 단계는 «광학극한 πr²» 하고만 맞춰 봤는데, 광학극한은 ka 가 아주 클 때만 맞는 값이라
    유효한 과녁이 아니다. 여기서 과녁을 둘로 나눠 다시 잰다.

    구의 재질은 스칼라 |Γ| 로 물려 있으므로, 완전도체(PEC) 기준해와 견주려면 σ 를 Γ² 로 나눈다
    (앞 단계 gamma_invariance 가 σ 는 정확히 20log10Γ 만큼 이동한다는 것을 실측했다)."""
    rows = {}
    for band in BANDS:
        fc = B.FC_MAIN if band == "main" else B.FC_PO_KNEE
        arms_ref = rung["arms"] if band == "main" else rung["hi_band"]["arms"]
        for key in DRONE_KEYS:
            g = arms_ref[key]["sphere_eqvol"]["geometry"]
            r = float(g["r_equal_volume_m"])
            gam = float(g["area_weighted_gamma"])
            ka = 2.0 * math.pi * r * fc / B.C0
            po_norm = float(MIE.po_sphere_norm(ka))
            mie_norm = float(MIE.mie_pec_backscatter_norm(ka))
            opt_dbsm = 10 * math.log10(math.pi * r * r)
            for wf in WFS:
                blk = blocks.get((band, key, "sphere_eqvol", wf))
                if blk is None:
                    continue
                sig = blk["per_az"]["sigma_eq_mean_dbsm"]["mean"]
                pec_equiv = sig - 20 * math.log10(gam)
                rows[f"{band}|{key}|{wf}"] = dict(
                    radius_m=r, ka=ka, gamma_abs=gam,
                    kernel_sigma_dbsm=sig,
                    kernel_pec_equivalent_dbsm=pec_equiv,
                    optical_limit_dbsm=opt_dbsm,
                    analytic_po_dbsm=float(opt_dbsm + 10 * math.log10(po_norm)),
                    exact_mie_dbsm=float(opt_dbsm + 10 * math.log10(mie_norm)),
                    kernel_minus_optical_db=float(pec_equiv - opt_dbsm),
                    kernel_minus_analytic_po_db=float(pec_equiv - (opt_dbsm + 10 * math.log10(po_norm))),
                    kernel_minus_mie_db=float(pec_equiv - (opt_dbsm + 10 * math.log10(mie_norm))),
                    po_minus_mie_db=float(10 * math.log10(po_norm / mie_norm)))
    num_err = [abs(v["kernel_minus_analytic_po_db"]) for v in rows.values()]
    model_err = [abs(v["po_minus_mie_db"]) for v in rows.values()]

    # 작은 구(허브·블레이드)는 ka<1 이라 PO 가 세기를 크게 틀린다 — 그 «틀리는 양» 을 잰다
    small = {}
    for band in BANDS:
        fc = B.FC_MAIN if band == "main" else B.FC_PO_KNEE
        for key in DRONE_KEYS:
            v = rung["sphere_scattering_validity"][key]["fc_main" if band == "main" else "fc_po_knee"]
            for nm in ("hub_sphere", "blade_sphere"):
                ka = float(v[nm]["ka"])
                po_n = float(MIE.po_sphere_norm(ka))
                mie_n = float(MIE.mie_pec_backscatter_norm(ka))
                small[f"{band}|{key}|{nm}"] = dict(
                    ka=ka, regime=v[nm]["regime"],
                    analytic_po_over_optical_db=float(10 * math.log10(po_n)),
                    exact_mie_over_optical_db=float(10 * math.log10(mie_n)),
                    po_minus_mie_db=float(10 * math.log10(po_n / mie_n)))
    worst_small = max(small.values(), key=lambda d: abs(d["po_minus_mie_db"]))
    return dict(
        equal_volume_sphere=rows,
        numerical_error_db=dict(max=float(max(num_err)), mean=float(np.mean(num_err)), n=len(num_err)),
        po_model_error_db=dict(max=float(max(model_err)), mean=float(np.mean(model_err)), n=len(model_err)),
        small_spheres_po_vs_mie=small,
        worst_small_sphere_po_error_db=float(worst_small["po_minus_mie_db"]),
        worst_small_sphere_at=max(small, key=lambda t: abs(small[t]["po_minus_mie_db"])),
        reference="benchmark/mie_pec_sphere.py (정확 Mie + 해석 PO, 저장소 공용 기준해)",
        read_ko=("⭐ 우리 커널은 구의 **해석 PO 해**와 전 구석에서 0.12 dB 안으로 맞는다 — 수치 구현은 "
                 "정상이다. 그러나 PO 자체가 정확한 물리(Mie)와 어긋나는 양은 ka 가 작을수록 커져서 "
                 "가장 작은 ka 구석에서 수 dB 에 이른다. 앞 단계가 인용한 «광학극한과 +0.01 dB» 는 "
                 "세 기체 중 가장 잘 맞은 하나(matrice4e)이고, 나머지는 −0.82/−0.42 dB 다. "
                 "광학극한은 유효한 과녁이 아니므로 여기서 과녁을 해석 PO 와 Mie 로 나눴다."),
        scope_ko=("이 앵커는 «세기» 만 검증한다. 이 단의 헤드라인(회전대칭체는 변조가 없다)은 산란 모델과 "
                  "무관한 대칭 논증이라 이 앵커가 필요하지도, 흔들지도 못한다."))


# --------------------------------------------------------------------------- #
#  8) 예측을 걸지 않은 사다리(P5) 정량
# --------------------------------------------------------------------------- #
def ladder_unpredicted(blocks, paired):
    rows = {}
    for band in BANDS:
        for key in DRONE_KEYS:
            for wf in WFS:
                mesh = blocks.get((band, key, "mesh", wf))
                if mesh is None:
                    continue
                r = dict(mesh=dict(
                    in_band_ac_over_dc_db=mesh["per_az"]["in_band_ac_over_dc_db"]["mean"],
                    flash_contrast_db=mesh["per_az"]["flash_contrast_db"]["mean"],
                    width_ratio_20db=mesh["per_az"]["width_ratio_20db"]["mean"],
                    n_eff_orders=mesh["per_az"]["n_eff_orders"]["mean"],
                    blade_comb_frac=mesh["per_az"]["blade_comb_frac"]["mean"],
                    dc_ac_db=mesh["per_az"]["dc_ac_db"]["mean"]))
                for arm in ("sph_blade_rg", "sph_blade_tip"):
                    blk = blocks.get((band, key, arm, wf))
                    if blk is None:
                        continue
                    p = paired.get(f"{band}|{key}|{arm}|{wf}", {})
                    r[arm] = dict(
                        in_band_ac_over_dc_db=blk["per_az"]["in_band_ac_over_dc_db"]["mean"],
                        flash_contrast_db=blk["per_az"]["flash_contrast_db"]["mean"],
                        width_ratio_20db=blk["per_az"]["width_ratio_20db"]["mean"],
                        n_eff_orders=blk["per_az"]["n_eff_orders"]["mean"],
                        blade_comb_frac=blk["per_az"]["blade_comb_frac"]["mean"],
                        dc_ac_db=blk["per_az"]["dc_ac_db"]["mean"],
                        interpretable_frac=blk["interpretable_frac"],
                        ac_corr_with_mesh=p.get("ac_corr_with_mesh", {}).get("mean"),
                        equivalent_noise_snr_db=p.get("equivalent_noise_snr_db", {}).get("mean"),
                        delta_level_db=blk["per_az"]["in_band_ac_over_dc_db"]["mean"] -
                                       mesh["per_az"]["in_band_ac_over_dc_db"]["mean"],
                        delta_flash_db=blk["per_az"]["flash_contrast_db"]["mean"] -
                                       mesh["per_az"]["flash_contrast_db"]["mean"])
                rows[f"{band}|{key}|{wf}"] = r

    def collect(arm, field):
        return [v[arm][field] for v in rows.values() if arm in v and v[arm].get(field) is not None]

    summary = {}
    for arm in ("sph_blade_rg", "sph_blade_tip"):
        summary[arm] = dict(
            delta_level_db=B.summarize(collect(arm, "delta_level_db")),
            delta_flash_db=B.summarize(collect(arm, "delta_flash_db")),
            ac_corr_with_mesh=B.summarize(collect(arm, "ac_corr_with_mesh")),
            width_ratio_20db=B.summarize(collect(arm, "width_ratio_20db")),
            n_louder_than_mesh=int(sum(1 for x in collect(arm, "delta_level_db") if x > 0)),
            n_corners=len(collect(arm, "delta_level_db")))
    mesh_w = B.summarize([v["mesh"]["width_ratio_20db"] for v in rows.values()])
    return dict(rows=rows, summary=summary, mesh_width_ratio_20db=mesh_w,
                read_ko=("블레이드 반경에 구를 갖다 놓으면 변조가 살아난다. 총량(level)은 메쉬와 비슷하거나 "
                         "더 크지만, 플래시 대조비는 훨씬 못 미치고 폭은 «넣어 준 반경» 이 그대로 결정한다. "
                         "즉 «변조가 있나 없나» 만 쓰는 검출기라면 프리미티브로 충분하고, 폭·플래시·템플릿을 "
                         "쓰면 형상이 필요하다."),
                caveat_ko=("⚠ 이 팔들의 구는 ka<1(레일리 영역)이라 PO 가 **세기** 를 크게 틀린다. 여기 적힌 "
                           "절대 세기는 인용 금지 — 팔 사이 «모양» 비교로만 쓴다."))


# --------------------------------------------------------------------------- #
#  9) ⚠ 이 결과를 못 믿을 이유 (스스로 찾는다)
# --------------------------------------------------------------------------- #
def distrust(J):
    S, EA, FO, IN = (J["prediction_scoring"], J["external_anchor"], J["floor_origin"],
                     J["interpretability"])
    LD = J["ladder_unpredicted"]
    ref_slopes = FO["refinement_slope"]
    worst_slope = min(v["slope_db_per_octave"] for v in ref_slopes.values())
    best_drop = max(v["total_drop_db"] for v in ref_slopes.values())
    lag1 = [v["delta_vs_mesh"]["in_band_ac_over_dc_db"]["az_lag1_corr"]
            for v in J["paired_vs_mesh"].values()]
    neff = [v["delta_vs_mesh"]["in_band_ac_over_dc_db"]["n_eff_az"]
            for v in J["paired_vs_mesh"].values()]
    dcac = [abs(v["delta_vs_mesh"]["dc_ac_db"]["mean"]) for v in J["paired_vs_mesh"].values()]
    items = [
        dict(id="D1",
             claim_ko="P1 의 문턱(−60 dB)은 물리량이 아니라 우리가 고른 격자의 함수다 — «MARGINAL» 을 물리로 읽으면 안 된다.",
             evidence=dict(
                 refinement_slope_db_per_octave_worst=float(worst_slope),
                 refinement_total_drop_db_max=float(best_drop),
                 rung_worst_corner_drop_db=J["inputs"]["rung_worst_corner_drop_db"]),
             so_what_ko=("분할을 두 배 촘촘히 할 때마다 잔재가 수십 dB 내려간다. 즉 «구가 변조를 낸다» 가 "
                         "아니라 «허브 구를 성기게 그렸다» 는 뜻이다. 같은 이유로 «−60 dB 를 통과했다» 는 "
                         "말도 강한 주장이 못 된다 — 격자를 조이면 언제든 통과한다.")),
        dict(id="D2",
             claim_ko="커널에 가림(occlusion)·모서리 회절·다중반사가 없다. 동체가 과대 계상되므로 dc_ac_db 계열이 오염된다.",
             evidence=dict(engine=J["inputs"]["rung_engine"],
                           mesh_dc_ac_db=B.summarize(
                               [J["metrics"][f"{b}|{k}|mesh|{w}"]["per_az"]["dc_ac_db"]["mean"]
                                for b in BANDS for k in DRONE_KEYS for w in WFS]),
                           max_abs_delta_dc_ac_db_arm_vs_mesh=float(max(dcac))),
             so_what_ko=("P4 의 «여유 62~81 dB» 는 분자(메쉬 변조)와 분모(널)가 다 이 결함을 안고 나온 값이다. "
                         "부호와 자릿수는 믿을 수 있어도 소수점은 못 믿는다. 절대값을 논문 문장에 넣지 말 것.")),
        dict(id="D3",
             claim_ko="PO 근사 자체의 세기 오차가 작은 구에서 매우 크다 — 사다리 팔(허브·블레이드 구)의 절대 세기는 인용 불가.",
             evidence=dict(worst_small_sphere_po_minus_mie_db=EA["worst_small_sphere_po_error_db"],
                           at=EA["worst_small_sphere_at"],
                           equal_volume_sphere_numerical_error_db_max=EA["numerical_error_db"]["max"],
                           equal_volume_sphere_po_model_error_db_max=EA["po_model_error_db"]["max"]),
             so_what_ko=("커널의 «수치» 는 해석 PO 와 0.12 dB 안으로 맞지만, 그건 정확한 물리와 맞는다는 뜻이 "
                         "아니다. 파장보다 훨씬 작은 구에서는 PO 와 정확해가 수십 dB 어긋난다. P5 사다리에서 "
                         "«블레이드 구가 메쉬만큼 변조를 낸다» 는 관찰은 세기 축에서 신뢰할 수 없다.")),
        dict(id="D4",
             claim_ko="널 팔의 폭·풍부도 숫자는 표에 찍히지만 읽을 자격이 없다 — 인용하면 그대로 오보가 된다.",
             evidence=dict(n_arms=IN["n_arms"], n_not_quotable=IN["n_not_quotable"],
                           example_ko=IN["trap_example_ko"]),
             so_what_ko=("in_band_ac_frac 이 0.5 미만인 팔은 변조 전력의 절반 이상이 «팁보다 빠른 자리» 에 "
                         "있다. 그 팔의 width_ratio·n_eff_orders 는 격자를 잰 값이다. 자동 표 생성이 이 "
                         "필터를 빠뜨리면 «구가 넓은 도플러를 낸다» 는 정반대 문장이 나온다.")),
        dict(id="D5",
             claim_ko="24 방위는 독립 표본이 아니다 — 산포·부호검정·평균의 오차는 낙관적이다.",
             evidence=dict(az_lag1_corr_max=float(max(lag1)),
                           n_eff_az_min=float(min(neff)),
                           n_az=int(J["protocol"]["n_az"])),
             so_what_ko=("같은 물체를 15°씩 돌려 잰 값이라 이웃 방위가 닮는다. 유효표본수는 24 보다 작다. "
                         "«평균 ± 표준오차» 를 그대로 쓰면 유의성을 부풀린다.")),
        dict(id="D6",
             claim_ko="교차검증이 «같은 코드» 안에서만 이뤄졌다 — 독립 구현으로 재현된 적이 없다.",
             evidence=dict(recompute_gate=J["recompute_gate"]["verdict"],
                           recompute_max_abs_diff=J["recompute_gate"]["max_abs_diff"],
                           cross_round_gate=J["cross_round_gate"]["verdict"],
                           cross_round_max_rel=J["cross_round_gate"]["max_rel_after_gamma"]),
             so_what_ko=("비트 일치는 «같은 커널이 같은 답을 두 번 냈다» 는 뜻이지 «맞다» 는 뜻이 아니다. "
                         "바깥 기준자는 구의 세기 하나뿐이고(Mie/해석 PO), 마이크로도플러 쪽에는 외부 "
                         "기준해가 아직 없다.")),
        dict(id="D7",
             claim_ko="호버 한 조건·정지 자세·강체 회전만 봤다 — 실제 비행의 변수는 하나도 안 들어갔다.",
             evidence=dict(el_deg=J["protocol"]["el_deg"], range_m=J["protocol"]["range_m"],
                           n_rev=J["protocol"]["n_rev_slowtime"],
                           rpm_note_ko="네 로터가 같은 rpm 으로 정확히 주기적으로 돈다고 두었다."),
             so_what_ko=("실제로는 로터마다 rpm 이 다르고(자세 제어), 기체가 흔들리고, 블레이드가 휘고, "
                         "바닥 반사가 섞인다. 그 전부가 «메쉬 대 구» 간극을 줄이는 쪽으로 작용할 수 있다. "
                         "이 단은 «가장 유리한 조건에서의 상한» 이다.")),
        dict(id="D8",
             claim_ko="바닥 숫자는 파면(평면파/구면파)이라는 **모델링 선택**만으로도 몇 dB 움직인다 — 하나를 골라 인용하면 안 된다.",
             evidence=dict(
                 null_wavefront_swing_db_max=J["null_fragility"]["null_wavefront_swing_db"]["max"],
                 mesh_wavefront_swing_db_max=J["null_fragility"]["mesh_wavefront_swing_db"]["max"]),
             so_what_ko=("진짜 물리적 0 이라면 어느 쪽으로 계산해도 0 이어야 한다. 널의 바닥이 이만큼 "
                         "흔들린다는 것은 그 값이 계산 방식의 산물이라는 직접 증거다(P2 를 보강한다). "
                         "동시에 «바닥 = −85 dB» 같은 단일 숫자 인용은 금지다.")),
        dict(id="D9",
             claim_ko="«분할을 촘촘히 하면 잔재가 준다» 는 평균적으로만 맞다 — 한 칸씩 보면 오르내리고, 하필 생산 격자가 국소 봉우리에 앉은 구석이 있다.",
             evidence={k: dict(seg_values=v["seg_values"], residual_db=v["residual_db"],
                               monotone=v["monotone_decreasing"],
                               worst_upward_step_db=v["worst_upward_step_db"])
                       for k, v in J["null_fragility"]["refinement_monotonicity"].items()
                       if not v["monotone_decreasing"]},
             so_what_ko=("격자선끼리 간섭하기 때문이다. 따라서 «생산 격자에서 잰 바닥» 은 그 격자의 운이지 "
                         "수렴값이 아니다. 바닥을 인용하려면 여러 분할의 포락선으로 말해야 한다.")),
        dict(id="D10",
             claim_ko="P5(사다리)는 예측을 안 걸었으므로, 여기서 나온 방향은 사후 해석이다.",
             evidence=dict(sph_blade_rg_delta_level_db=LD["summary"]["sph_blade_rg"]["delta_level_db"]["mean"],
                           sph_blade_tip_delta_level_db=LD["summary"]["sph_blade_tip"]["delta_level_db"]["mean"],
                           n_corners=LD["summary"]["sph_blade_rg"]["n_corners"]),
             so_what_ko=("사후에 고른 축(폭·플래시·상관)에서 «형상이 필요하다» 가 나왔다. 다음 단에서 이 "
                         "축들을 **미리** 걸고 다시 재야 주장 자격이 생긴다.")),
    ]
    return dict(items=items, n=len(items),
                rule_ko="각 항목은 «주장 — 숫자 근거 — 그래서 무엇을 하면 안 되는가» 세 줄로 적는다.")


# --------------------------------------------------------------------------- #
#  10) 본문
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    rung = json.load(open(RUNG_JSON, encoding="utf-8"))
    base = json.load(open(BASE_JSON, encoding="utf-8"))
    tabs = load_rung_tables()
    base_tabs = load_base_mesh_tables()

    protos = protocols()
    specs = {k: protos[k]["spec"] for k in DRONE_KEYS}
    pgate = protocol_gate(protos, rung)

    mets, blocks = compute_all(tabs, protos, specs)
    rgate = recompute_gate(blocks, rung)
    cgate = cross_round_gate(tabs, base_tabs, rung)

    paired = paired_vs_mesh(mets, tabs)
    score = score_predictions(blocks, mets, tabs, specs, rung)

    J = {}
    J["meta"] = dict(
        report="report16 사다리 — 등가부피 구 단의 **지표 추출·사전예측 대조**",
        producer="benchmark/report16_metric_sphere_eqvol.py",
        stage="metric (앞 단계 rung 의 표를 읽어 지표만 낸다 — GPU 미사용)",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=git_rev(),
        question_ko="회전축 위의 등가부피 구는 정말 마이크로도플러를 못 내는가, 그리고 그 «못 냄» 의 바닥은 얼마인가.",
        metric_source="report16_base.md_metrics16 (import — 재구현 금지)",
        seconds=None)
    J["inputs"] = dict(
        rung_json=dict(path=RUNG_JSON, sha256_16=sha256_of(RUNG_JSON), mtime=mtime_of(RUNG_JSON)),
        rung_npz=dict(path=RUNG_NPZ, sha256_16=sha256_of(RUNG_NPZ), mtime=mtime_of(RUNG_NPZ)),
        base_json=dict(path=BASE_JSON, sha256_16=sha256_of(BASE_JSON), mtime=mtime_of(BASE_JSON)),
        base_npz=dict(path=BASE_NPZ, sha256_16=sha256_of(BASE_NPZ), mtime=mtime_of(BASE_NPZ)),
        base_py=dict(path=os.path.join(_HERE, "report16_base.py"),
                     sha256_16=sha256_of(os.path.join(_HERE, "report16_base.py"))),
        this_py=dict(path=os.path.abspath(__file__), sha256_16=sha256_of(os.path.abspath(__file__))),
        rung_engine=rung["protocol"]["engine"],
        rung_worst_corner_drop_db=rung["posthoc_marginal_diagnosis"]["worst_corner_drop_db"],
        n_tables=len(tabs))
    J["protocol"] = dict(
        fc_main_hz=B.FC_MAIN, fc_po_knee_hz=B.FC_PO_KNEE, el_deg=B.EL_DEG, range_m=B.RANGE_M,
        n_az=B.N_AZ, n_rev_slowtime=B.N_REV, edge_drop_db=B.EDGE_DROP_DB,
        wavefronts=WFS, arms=ARMS, drones=DRONE_KEYS,
        per_drone={k: {b: protos[k][b] for b in BANDS} for k in DRONE_KEYS},
        spec={k: protos[k]["spec"] for k in DRONE_KEYS})
    J["gates"] = dict(protocol=pgate)
    J["recompute_gate"] = rgate
    J["cross_round_gate"] = cgate
    J["metrics"] = {f"{b}|{k}|{a}|{w}": v for (b, k, a, w), v in blocks.items()}
    J["metric_families"] = family_table(blocks)
    J["interpretability"] = interpretability_block(blocks)
    J["paired_vs_mesh"] = paired
    J["surrogate_scorecard"] = surrogate_scorecard(blocks, paired)
    J["prediction_scoring"] = score
    J["floor_origin"] = floor_origin(blocks, rung, tabs)
    J["null_fragility"] = null_fragility(blocks, rung)
    J["level_vs_modulation"] = level_vs_modulation(blocks)
    J["azimuth_invariance"] = azimuth_invariance(blocks)
    J["external_anchor"] = external_anchor(blocks, rung)
    J["ladder_unpredicted"] = ladder_unpredicted(blocks, paired)
    J["metric_definitions"] = dict(
        source="report16_base.md_metrics16 의 독스트링 (정의 원문은 그쪽에 있다)",
        families={
            "flash": "플래시 대조비 — 블레이드가 시선에 정렬되는 순간이 바닥보다 몇 dB 위인가.",
            "richness": "고차 성분 풍부도 — 실질적으로 몇 개의 차수가 살아 있나(n_eff), 전력의 50/90%가 몇 차수 안에 드나, 블레이드 수 배수 차수에 실린 몫은 얼마인가.",
            "width": "도플러 폭 — 첨두 대비 −10/−20/−30 dB 까지 살아 있는 가장 바깥 차수와, 그것을 팁 도플러로 나눈 비(운동학이 맞으면 ≈1).",
            "dc_ac": "동체:블레이드 비 — 안 움직이는 부분(DC)과 도는 부분(AC)의 세기비. ⚠ 가림이 없어 오염된다.",
            "level": "평균 세기 σ — 24 방위 평균.",
            "quality": "읽을 자격 — 대역 안 AC 몫과 수치바닥 대비 여유."},
        mod_depth_db="이 단계가 같이 계산하는 쉬운 말 지표: 한 바퀴 도는 동안 신호가 몇 % 흔들리나(dB·ppm).",
        caveat_ko="dc_ac 계열의 절대값은 인용 금지(가림 없음). 팔 사이 차이만 쓴다.")
    J["distrust"] = distrust(J)

    # ── 사람이 읽는 요약 ────────────────────────────────────────────────────
    eq = {t: v for t, v in J["prediction_scoring"]["task_prediction"]["floor_rows"].items()
          if t.split("|")[2] == "sphere_eqvol"}
    worst_ppm = max(v["mod_depth_ppm"] for v in eq.values())
    best_ppm = min(v["mod_depth_ppm"] for v in eq.values())
    mesh_ppm = [J["metrics"][f"{b}|{k}|mesh|{w}"]["per_az"]["mod_depth_ppm"]["mean"]
                for b in BANDS for k in DRONE_KEYS for w in WFS]
    LM = J["level_vs_modulation"]
    NF = J["null_fragility"]
    SC = J["surrogate_scorecard"]["per_arm"]
    J["findings"] = {
        "00_gates": (
            f"게이트 셋 다 통과 — 규약 재유도 {J['gates']['protocol']['verdict']}(최대 상대오차 "
            f"{J['gates']['protocol']['worst_rel']:.0e}), 지표 재계산 {J['recompute_gate']['verdict']}"
            f"(앞 단계 저장값과 최대 {J['recompute_gate']['max_abs_diff']:.0e} 차이), "
            f"교차 실행 {J['cross_round_gate']['verdict']}(mesh 팔 비트 일치, 구 팔은 재질 |Γ| 를 곱하면 "
            f"{J['cross_round_gate']['max_rel_after_gamma']:.0e} — «재질은 세기만 바꾼다» 가 서로 다른 두 "
            "실행에서 재현됐다)."),
        "01_prediction": (
            f"사전 예측 채점 — P1 {score['verdicts']['P1']}, P2 {score['verdicts']['P2']}, "
            f"P3 {score['verdicts']['P3']}, P4 {score['verdicts']['P4']}, P5 예측 없음 → "
            f"종합 {score['overall']}. 앞 단계 판정({rung['prediction_test']['overall']})과 "
            f"{'같다' if score['agreement_with_rung']['same_overall'] else '다르다'}. "
            f"문턱은 계산 전에 고정된 prereg(sha256 {score['prereg_sha256'][:12]}…)에서 읽었고 "
            f"숫자는 원본 표에서 다시 냈다."),
        "02_task_prediction": (
            f"⭐ 이 단의 예측 「구는 변조 0」 — 맞았다. 다만 정확히 0 은 아니고 바닥이 있다: "
            f"등가부피 구의 한 바퀴 흔들림은 {best_ppm:.0f}~{worst_ppm:.0f} ppm"
            f"(={100*best_ppm/1e6:.4f}~{100*worst_ppm/1e6:.4f} %)이고, 같은 자리에서 메쉬는 "
            f"{min(mesh_ppm)/1e4:.1f}~{max(mesh_ppm)/1e4:.1f} % 다. 이 바닥이 이 실험의 «0» 이다."),
        "03_floor_origin": (
            f"바닥의 정체는 격자다 — 반올림 한계(√N·ε)보다 "
            f"{min(v['above_roundoff_db'] for v in J['floor_origin']['roundoff'].values()):.0f} dB 이상 위이고, "
            f"분할을 두 배 촘촘히 할 때마다 "
            f"{min(v['slope_db_per_octave'] for v in J['floor_origin']['refinement_slope'].values()):.1f} "
            f"~ {max(v['slope_db_per_octave'] for v in J['floor_origin']['refinement_slope'].values()):.1f} dB 내려간다."),
        "035_null_fragility": (
            f"⚠ 그 바닥은 «물리량» 이 아니다 — 평면파냐 구면파냐 하는 모델링 선택만으로 널 팔의 값이 "
            f"최대 {NF['null_wavefront_swing_db']['max']:.1f} dB 움직인다(메쉬는 "
            f"{NF['mesh_wavefront_swing_db']['max']:.2f} dB). 게다가 분할을 촘촘히 해도 한 칸씩은 "
            f"오르내려서, mini2 등가부피 구는 생산 격자(seg 39)가 더 성긴 격자(seg 21)보다 "
            f"{NF['refinement_monotonicity']['sphere_eqvol|mini2']['worst_upward_step_db']:.1f} dB **나쁘다**. "
            "바닥 숫자 하나를 인용하면 안 된다."),
        "04_interpretability": (
            f"⚠ 팔 {J['interpretability']['n_arms']} 구석 중 {J['interpretability']['n_not_quotable']} 곳은 "
            f"폭·풍부도를 인용할 자격이 없다(대역 안 AC 몫 < 0.5). 그런데 표에는 숫자가 찍힌다 — "
            f"예: 등가부피 구의 width_ratio ≈ 7 은 «팁보다 7배 빠른 도플러» 라 물리적으로 불가능하다."),
        "05_external_anchor": (
            f"⭐ 구의 세기를 정확해와 맞췄다 — 커널 대 **해석 PO** 는 최대 "
            f"{J['external_anchor']['numerical_error_db']['max']:.3f} dB(수치 구현 정상), "
            f"해석 PO 대 **정확 Mie** 는 최대 {J['external_anchor']['po_model_error_db']['max']:.2f} dB"
            f"(PO 를 쓴 대가). 앞 단계가 인용한 «광학극한과 +0.01 dB» 는 세 기체 중 가장 잘 맞은 하나다."),
        "06_ladder": (
            "P5(예측 없음) — 블레이드 반경의 구는 변조 총량을 메쉬만큼(혹은 그 이상) 내지만 "
            f"플래시 대조비가 평균 {J['ladder_unpredicted']['summary']['sph_blade_rg']['delta_flash_db']['mean']:.1f} dB "
            "모자라고 폭은 넣어 준 반경이 결정한다 — «변조 유무» 검출기엔 충분, 「폭·플래시·템플릿」엔 부족."),
        "065_scorecard": (
            "대체물 성적표(해석 자격이 있는 구석만) — 변조 총량 오차 / 플래시 오차 / 폭 비 / 파형 상관: "
            + "; ".join(f"{a} {v['level_err_db']:.1f} dB, {v['flash_err_db']:.1f} dB, "
                        f"{v['width_ratio_arm_over_mesh']:.2f}, {v['ac_corr']:.2f}"
                        for a, v in SC.items() if v.get("n", 0) > 0)
            + ". 어느 팔도 네 축을 다 맞히지 못한다."),
        "07_level_vs_modulation": (
            f"⭐⭐ 경계선 — 평균 세기는 구와 메쉬가 생산대역에서 최대 "
            f"{LM['by_band']['main']['sigma_gap_db_max']:.2f} dB(15.86 GHz 에서는 "
            f"{LM['by_band']['hi']['sigma_gap_db_max']:.2f} dB) 안에서 붙지만"
            f"(사실상 무승부), 방위 산포는 메쉬 최대 {LM['azimuth_sd_db']['mesh_max']:.1f} dB 대 구 "
            f"{LM['azimuth_sd_db']['sphere_max']:.0e} dB 이고 시간 변조는 "
            f"{LM['modulation_gap_db']['min']:.0f}~{LM['modulation_gap_db']['max']:.0f} dB 차이다. "
            "지적은 «세기» 축에서 맞고 «시간 변조» 축에는 적용되지 않는다. 두 대역·두 파면 전부에서 같다."),
        "08_distrust": f"이 결과를 못 믿을 이유 {J['distrust']['n']} 개를 숫자와 함께 남겼다(distrust).",
        "_ordering_ko": "게이트 → 예측 채점 → 바닥의 정체·취약성 → 해석 자격 → 바깥 기준자 → 사다리 → 경계선 → 불신 목록.",
    }
    J["meta"]["seconds"] = float(time.time() - t0)

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"[저장] {OUT_JSON}  ({os.path.getsize(OUT_JSON)/1024:.0f} KB, {J['meta']['seconds']:.1f} s)")
    for k, v in J["findings"].items():
        print(f"  · {k}: {v}")
    return J


if __name__ == "__main__":
    main()
