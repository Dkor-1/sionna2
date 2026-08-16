#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""«기체마다 진짜로 다른 프로펠러가 달렸나» — 지어진 메쉬로 되재는 검증 (2026-08-16).

왜 또 재나
  법칙 원장(outputs/prop_law_by_airframe_0816.json)은 **설계표**다. 표에 곡선을 적어 넣는
  것과, 그 곡선이 실제로 지어진 프롭 메쉬에 **들어간 것**은 다른 주장이다. 지난 라운드들이
  반복해서 걸린 자리가 정확히 여기다(파라미터 값 ↔ 실현값이 다른데 같은 이름으로 인용).
  그래서 이 스크립트는 설계표를 한 번도 안 믿고, **build_propeller 가 뱉은 삼각형만** 가지고
  ① 정말 기체마다 다른가 ② 표에 적힌 곡선이 맞게 실현됐나 ③ 기본값은 그대로인가 를 잰다.

무엇을 재나 (계측은 전부 «메쉬를 자른 단면»에서 나온다 — 설계 상수를 안 읽는다)
  · 스팬 x = r 평면으로 날을 잘라 단면 다각형을 얻고, 그 **최대 캘리퍼**를 시위로 쓴다.
    ⭐ 캘리퍼는 회전에 불변이라 비틀림(피치)이 값을 안 건드린다 — 설계 시위와 같은 자다.
    ⚠ 익형은 두께가 있으므로 캘리퍼는 시위보다 아주 조금 크다(앞·뒷전 살). 그래서 절대값은
      +1 % 안팎 위로 나오고, **정규화 곡선**(c/c_max)은 그 몫이 거의 상쇄된다.
  · 날 1장 면적 ∫ c dx 도 같은 단면들에서 사다리꼴로 적분한다(원장의 해석 적분과 다른 길).

⭐⭐ 잣대를 먼저 맞춘다 — 안 맞추면 «형상이 틀렸다» 는 거짓 경보가 난다
  빌더는 **스윕디스크 정규화**를 한다. 스윕이 팁을 옆으로 밀어내므로 스팬을 R 로 잡으면
  실제 최대반경이 R 을 넘는다 → 그래서 스팬을 0.991~0.992 배로 줄여 짓는다. 결과적으로
  «x = 0.5·R_공칭» 은 날 자신의 스팬으로는 0.504 지점이다. 형상(정규화 곡선) 비교는 반드시
  **날 자신의 스팬**(꼭짓점 x 최대)으로 정규화해서 해야 하고, 물리량(c_max/R)은 공칭 R 로
  적어야 한다. 이 스크립트는 둘을 갈라서 낸다.

판정 (전부 실패하면 종료코드 1)
  V1 기본값 불변   : 인자 없는 호출 == blade_law='legacy'  (꼭짓점 바이트 동일)
  V2 실현 충실도   : 지어진 메쉬의 정규화 시위곡선 ↔ 레지스트리 곡선   (0.20~0.96R, 허용 3 %)
                    ⚠ 0.10~0.20R 은 따로 적는다 — 로프트 단면이 22개뿐이라 뿌리의 급한
                      곡률을 직선으로 잇고, 거기서 3~6 % 가 난다(형상 오류가 아니라 해상도).
  V3 기체 구분     : 기종끼리 정규화 곡선이 얼마나 다른가 (대리 쌍은 0 이어야 정직하다)
  V4 변화표 재현   : 지어진 메쉬로 잰 날 면적 변화율 ↔ 원장 D 표     (허용 3 %p)

⛔ GPU 미사용 · git 미접촉 · **코드 기본값 미변경**(이 파일은 읽기만 한다).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
OUT = os.path.join(ROOT, "outputs")

import drones as DR            # noqa: E402
import drone_cad as DC         # noqa: E402

T0 = time.time()
GRID = np.round(np.arange(0.10, 0.995, 0.01), 3)      # 자를 위치 r/R (x 축 기준)
TOL_SHAPE_PCT = 3.0
TOL_AREA_PP = 3.0


# --------------------------------------------------------------------------- #
#  단면 캘리퍼 — 메쉬를 x = X 평면으로 자른다
# --------------------------------------------------------------------------- #
def section_caliper_mm(V, F, X):
    """x = X 평면으로 자른 단면의 **최대 캘리퍼**[mm]. 못 자르면 0."""
    tri = V[F]                                             # (n,3,3)
    d = tri[:, :, 0] - X
    hit = ~(np.all(d > 0, axis=1) | np.all(d < 0, axis=1))
    tri, d = tri[hit], d[hit]
    if len(tri) == 0:
        return 0.0
    pts = []
    for k in range(3):
        a, b = k, (k + 1) % 3
        da, db = d[:, a], d[:, b]
        cross = (da * db) < 0
        if not np.any(cross):
            continue
        t = (da[cross] / (da[cross] - db[cross]))[:, None]
        pts.append(tri[cross, a, 1:] + t * (tri[cross, b, 1:] - tri[cross, a, 1:]))
        on = np.abs(da) < 1e-15
        if np.any(on):
            pts.append(tri[on, a, 1:])
    if not pts:
        return 0.0
    P = np.vstack(pts)
    if len(P) > 3:                                          # 볼록껍질로 점을 줄인다(속도)
        try:
            from scipy.spatial import ConvexHull
            P = P[ConvexHull(P).vertices]
        except Exception:
            pass
    if len(P) < 2:
        return 0.0
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
    return float(D.max()) * 1000.0


def measure(mesh):
    """지어진 프롭에서 시위곡선을 되잰다.

    돌려주는 것: (c_mm[grid], c_max_mm, 면적 mm², 날 자신의 스팬 mm)
    격자는 **날 자신의 스팬**에 건다(위 «잣대» 문단 참조)."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    span = float(V[:, 0].max())
    c = np.array([section_caliper_mm(V, F, rr * span) for rr in GRID])
    x_mm = GRID * span * 1000.0
    return c, float(c.max()), float(np.trapezoid(c, x_mm)), span * 1000.0


def vhash(mesh):
    return (np.asarray(mesh.v, float).tobytes(), np.asarray(mesh.f, np.int64).tobytes())


# --------------------------------------------------------------------------- #
LEDGER = json.load(open(os.path.join(OUT, "prop_law_by_airframe_0816.json"), encoding="utf-8"))
LAW = LEDGER["C_law_by_airframe"]
DROWS = {r["aircraft"]: r for r in LEDGER["D_change_table"]["rows"]}

fails, res = [], {}
norm_curves = {}
for key in LAW:
    spec = DR.DRONES[key]
    R_m = spec.prop_dia_mm / 2000.0

    m_def = DR.build_propeller(spec)                       # 인자 없음 = 기본
    m_leg = DR.build_propeller(spec, blade_law="legacy")
    m_new = DR.build_propeller(spec, blade_law="per_airframe")

    # ── V1 기본값 불변 ──────────────────────────────────────────────────
    same = vhash(m_def) == vhash(m_leg)
    if not same:
        fails.append(f"V1 {key}: 인자 없는 호출이 legacy 와 다르다")

    c_old, cmax_old, area_old, span_old = measure(m_leg)
    c_new, cmax_new, area_new, span_new = measure(m_new)
    norm = c_new / cmax_new
    norm_curves[key] = norm

    # ── V2 실현 충실도 — 레지스트리 곡선을 같은 격자에 얹어 견준다 ─────────
    want = np.interp(GRID, LAW[key]["chord_rr"], LAW[key]["chord_frac"])
    want = want / want.max()
    #  ⚠ 팁(>0.96R)은 로프트 마지막 구간 세분과 뭉툭한 끝 처리가 걸리고, 뿌리(<0.20R)는
    #    22개 단면의 직선 이음이 걸린다. 판정 밴드는 0.20~0.96R 이고 나머지는 따로 적는다.
    main = (GRID >= 0.20) & (GRID <= 0.96)
    root = GRID < 0.20
    rel = np.abs(norm / np.maximum(want, 1e-9) - 1) * 100
    dev, dev_root = float(rel[main].max()), float(rel[root].max())
    dev_fine, verdict_v2 = None, "OK"
    if dev > TOL_SHAPE_PCT:
        #  ⭐ 실패로 적기 전에 **원인을 가른다**: 법칙이 틀린 것인가, 로프트가 성긴 것인가.
        #    단면 수를 4배로 올려 다시 재서, 오차가 따라 줄면 «해상도» 이고 남으면 «법칙» 이다.
        c_f, cm_f, _, _ = measure(DR.build_propeller(spec, n=40, blade_law="per_airframe"))
        dev_fine = float((np.abs((c_f / cm_f) / np.maximum(want, 1e-9) - 1) * 100)[main].max())
        if dev_fine <= 1.5:
            verdict_v2 = "resolution_limited"
        else:
            verdict_v2 = "FAIL"
            fails.append(f"V2 {key}: 지어진 곡선이 레지스트리와 {dev:.1f} % 어긋나고 "
                         f"단면을 4배로 올려도 {dev_fine:.1f} % 남는다 (0.20~0.96R)")

    # ── V4 변화표 재현 — 지어진 메쉬로 잰 면적 변화율 ────────────────────
    a_pct = 100 * (area_new / area_old - 1)
    d_pct = float(DROWS[key]["blade_area_pct"])
    if abs(a_pct - d_pct) > TOL_AREA_PP:
        fails.append(f"V4 {key}: 면적 변화율 {a_pct:+.1f} % ↔ 원장 {d_pct:+.1f} %")

    res[key] = dict(
        grade=LAW[key]["grade"], proxy_of=LAW[key]["proxy_of"], prop=LAW[key]["prop"],
        default_is_legacy=bool(same),
        R_nominal_mm=round(R_m * 1000.0, 2), blade_span_built_mm=round(span_new, 2),
        c_max_mm_built_old=round(cmax_old, 2), c_max_mm_built_new=round(cmax_new, 2),
        #  물리량은 **공칭 반경**으로 적는다(디스크가 쓸고 가는 원의 반지름)
        c_max_over_R_built_new=round(cmax_new / (R_m * 1000.0), 4),
        c_max_over_R_registry=LAW[key]["c_max_over_R"],
        #  ⭐ 봉우리 적자 — 로프트 단면이 22개뿐이라 곡선의 봉우리를 정확히 안 밟는다
        peak_realized_ratio=round((cmax_new / (R_m * 1000.0)) / LAW[key]["c_max_over_R"], 4),
        blade_area_mm2_built_old=round(area_old, 1), blade_area_mm2_built_new=round(area_new, 1),
        blade_area_pct_built=round(a_pct, 1), blade_area_pct_ledger=d_pct,
        shape_max_dev_pct_main_band=round(dev, 2),
        shape_max_dev_pct_root_band=round(dev_root, 2),
        shape_max_dev_pct_4x_sections=(None if dev_fine is None else round(dev_fine, 2)),
        v2=verdict_v2,
        span_scale=round(span_new / (R_m * 1000.0), 5),
        peak_r_over_R_built=float(GRID[int(np.argmax(norm))]),
        peak_r_over_R_registry=LAW[key]["peak_r_over_R"],
    )

# ── V3 기체 구분 — 정규화 곡선끼리 얼마나 다른가 ──────────────────────────
keys = list(norm_curves)
pair = []
band_cmp = (GRID >= 0.20) & (GRID <= 0.96)
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        a, b = norm_curves[keys[i]], norm_curves[keys[j]]
        pair.append(dict(a=keys[i], b=keys[j],
                         max_dev_pct=round(float(np.max(np.abs(a[band_cmp] / b[band_cmp] - 1))
                                                 * 100), 1)))
pair.sort(key=lambda d: -d["max_dev_pct"])
distinct = sum(1 for p in pair if p["max_dev_pct"] > 1.0)
proxy_pairs = [p for p in pair if p["max_dev_pct"] <= 1.0]
#  대리로 선언한 쌍(phantom3 ↔ phantom4 ↔ x500v2)만 «같아야» 정직하다
declared_proxy = {frozenset(("phantom3", "phantom4")), frozenset(("phantom3", "x500v2")),
                  frozenset(("phantom4", "x500v2"))}
for p in proxy_pairs:
    if frozenset((p["a"], p["b"])) not in declared_proxy:
        fails.append(f"V3 {p['a']}↔{p['b']}: 곡선이 사실상 같은데 대리 선언이 없다")

# --------------------------------------------------------------------------- #
#  V5 «지은 날이 법칙보다 2 % 좁다» — 그 적자를 원인별로 가른다
# --------------------------------------------------------------------------- #
#  왜 여기까지 파나: 파라미터와 실현값이 다른데 같은 이름으로 인용하는 것이 이 저장소가
#  반복해서 걸린 함정이다(감사 m3). 크기를 재서 적어 두면 다음 사람이 안 걸린다.
#  두 원인 다 **legacy 에도 똑같이** 걸리므로 변화표(비율)는 안 흔들린다 — 그것도 확인한다.
V5 = []
for key in ("mini2", "matrice4e", "m350rtk"):
    spec = DR.DRONES[key]
    R_m = spec.prop_dia_mm / 2000.0
    P = float(spec.prop_pitch_in or 5.0) * 0.0254
    law = LAW[key]

    def _one(n_pts, n_sec=80):
        m = DC._blade(R_m, root_frac=0.070, chord_max=law["c_max_over_R"], pitch_m=P,
                      n_sec=n_sec, law="legacy", chord_rr=law["chord_rr"],
                      chord_frac=law["chord_frac"], n_pts=n_pts)
        V = np.asarray(m.vertices, float)
        F = np.asarray(m.faces, np.int64)
        span = float(V[:, 0].max())
        c = np.array([section_caliper_mm(V, F, rr * span) for rr in GRID])
        return float(c.max()) / (span * 1000.0)

    coarse, fine = _one(36), _one(288)
    V5.append(dict(
        aircraft=key,
        span_scale=res[key]["span_scale"],
        loft_perimeter_ratio=round(coarse / fine, 4),
        residual_ratio=round(fine / law["c_max_over_R"], 4),
        total_built_over_law=res[key]["peak_realized_ratio"],
    ))
V5_note = ("지어진 날의 c_max 는 법칙보다 ~2 % 작다. 원인 둘 — ①스윕디스크 정규화가 스팬을 "
           "0.991~0.992 배로 줄인다(팁이 공칭 지름을 넘지 않게 하는 **의도된** 보정) "
           "②로프트가 단면 외곽선을 36점 등간격으로 재샘플하면서 앞·뒷전 꼭짓점을 스쳐 "
           "~1 % 를 깎는다(n_pts 를 288 로 올리면 회복). 둘 다 legacy 에도 똑같이 걸리므로 "
           "«옛→새» 변화율에는 안 들어간다 — V4 가 그것을 확인한다.")

led = dict(
    _meta=dict(
        title="기체별 프롭 법칙 — 지어진 메쉬로 되잰 검증 (2026-08-16)",
        generated_kst=time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 9 * 3600)),
        script="benchmark/verify_prop_law_per_airframe_0816.py",
        what_ko="설계표를 안 믿고 build_propeller 가 뱉은 삼각형만 잘라서 되쟀다.",
        method_ko="x = r 평면 단면의 최대 캘리퍼(회전 불변 ⇒ 비틀림 무관). 격자 0.10~0.99, "
                  "0.01 간격, **날 자신의 스팬**으로 정규화(스윕디스크 정규화 때문). "
                  "c_max/R 만 공칭 반경으로 적는다.",
        tolerance=dict(shape_pct=TOL_SHAPE_PCT, area_pp=TOL_AREA_PP),
    ),
    V1_default_unchanged=all(v["default_is_legacy"] for v in res.values()),
    V2_V4_by_airframe=res,
    V3_pairwise_shape_dev_pct=pair,
    V3_summary=dict(pairs=len(pair), distinct_over_1pct=distinct,
                    identical_pairs=[[p["a"], p["b"]] for p in proxy_pairs]),
    V5_realization_deficit=dict(note_ko=V5_note, rows=V5),
    verdict="PASS" if not fails else "FAIL",
    fails=fails,
)
with open(os.path.join(OUT, "prop_law_verify_0816.json"), "w", encoding="utf-8") as f:
    json.dump(led, f, ensure_ascii=False, indent=1)

print(f"{'기체':<12}{'등':<3}{'c_max/R 지음':>13}{'레지스트리':>10}{'봉우리실현':>11}"
      f"{'곡선(본)':>9}{'(뿌리)':>8}{'면적 지음':>10}{'원장':>8}")
for k, v in res.items():
    print(f"{k:<12}{v['grade']:<3}{v['c_max_over_R_built_new']:>13.4f}"
          f"{v['c_max_over_R_registry']:>10.4f}{v['peak_realized_ratio']:>11.3f}"
          f"{v['shape_max_dev_pct_main_band']:>8.1f}%{v['shape_max_dev_pct_root_band']:>7.1f}%"
          f"{v['blade_area_pct_built']:>+9.1f}%{v['blade_area_pct_ledger']:>+7.1f}%")
print("\nV5 실현 적자 귀속   : " + " · ".join(
    f"{r['aircraft']} 스팬 {r['span_scale']:.3f} × 재샘플 {r['loft_perimeter_ratio']:.3f} "
    f"× 잔여(단면수) {r['residual_ratio']:.3f} ⇒ 지음/법칙 {r['total_built_over_law']:.3f}"
    for r in V5))
print(f"V1 기본값 == legacy : {'통과' if led['V1_default_unchanged'] else '실패'} (10 기종)")
print(f"V3 기체 구분        : 45 쌍 중 {distinct} 쌍이 1 % 넘게 다르다 — "
      f"같은 쌍 {len(proxy_pairs)} (선언된 대리: phantom3/phantom4/x500v2)")
print(f"V3 가장 크게 갈리는 쌍: {pair[0]['a']} ↔ {pair[0]['b']}  {pair[0]['max_dev_pct']} %")
print(f"\n{led['verdict']}   ({time.time() - T0:.1f} s)  → outputs/prop_law_verify_0816.json")
for x in fails:
    print("   -", x)
raise SystemExit(0 if not fails else 1)
