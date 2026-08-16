# -*- coding: utf-8 -*-
"""
measure_reference_props.py — 실물 참조 프로펠러 CAD 정밀 측정 → 기준표 JSON
=============================================================================
왜 필요한가: `src/drone_cad.py` 의 블레이드 법칙(시위 분포·트위스트·두께·캠버)은
지금까지 **근거 없는 상수**이거나, 더 나쁘게는 **bbox 아티팩트에서 유도된 값**이었다
(`chord_max=0.26R` 의 주석 "실물 1345 는 0.30R" 은 프롭 전체 bbox x-폭이지 시위가 아니다).
이 스크립트는 저장소에 실재하는 **실물 하드웨어 CAD 3종**을 직접 재서 그 근거를 만든다.

측정 대상 (assets/meshes/reference/)
  * `1345_prop_cw.stl`                  Holybro 1345 (13×4.5 in) — PX4-gazebo-models, BSD-3
  * `solo_prop_cw.stl`                  3DR Solo 10 in — rotors_simulator 계열
  * `prop_cw_assembly_remeshed_v3.stl`  Yuneec Typhoon H480

⚠ **세 개 모두 시뮬레이터/시각화용 CAD 이지 계측 스캔이 아니다.** 특히 1345 는 트위스트가
   전 스팬 19.2~19.9° 로 **워시아웃이 0** 이라 물리적으로 실현 불가능한 로프트다 —
   트위스트 기준으로 쓰면 안 된다.

⛔⛔ **2026-08-16 정정 — 옛 문장 두 개를 철회한다.**
   옛 문장 ①: «저장소에 DJI 프로펠러 실물 기하는 하나도 없다»
   옛 문장 ②: «Solo 가 소비자용 쿼드 프롭이라 DJI 급에 가장 가깝다»
   ① 은 **거짓이 됐다.** 2026-08-07 에 들어온 `assets/meshes/reference/WM161_zhankai_1k.glb`
     (DJI Mini 2 공식 3D 모델) 안에 **날 8장 + 허브 4개**가 실재한다
     (디스크 지름 118.4~119.7 mm ↔ 공칭 4726F 119.4 mm, −0.9~+0.3 %).
   ② 는 ① 위에 서 있던 판단이라 같이 무너졌다. 실물 DJI 평면형과 대보니 **Solo 가 참조
     넷 중 유일한 이상치**다 — 정규화 시위 `c/c_max @0.70R` 이 Mini2 공식CAD 0.866 ·
     Yuneec 0.866 인데 Solo 계열 법칙은 0.577 이다(감사 `docs/MESH_AUDIT_0816.md` C3·C4).
   ⇒ **1차 앵커는 이제 DJI Mini 2 공식 CAD 다.** 이 스크립트가 재는 3종은 «같은 급 소형 프롭의
     참조 밴드» 로 남는다(여전히 쓸모 있다 — 밴드 안인지 밖인지를 보는 데 쓴다).
   ⚠ 여전히 참인 것: 세 CAD 는 계측 스캔이 아니고, 절대 σ 앵커는 계속
     `docs/DRONE_SPECS.md` §4 의 실측 문헌에 의존한다.

측정 방법 — **원통 단면**(프로펠러 단면의 정식 정의)
  반경 r 인 원통으로 날을 잘라 (접선 호길이, 축방향) 단면을 얻고, 최대 캘리퍼로 시위선을
  찾은 뒤 시위 좌표계로 회전시켜 상·하면에서 두께·평균선(캠버)을 뽑는다.
  ⚠ 평면절단(스팬축 수직)은 **못 쓴다** — 자세한 이유는 `_cyl_sections` 의 docstring 에 있다
    (스윕 큰 프롭은 팁이 절단면 밖으로 밀리고, 비폐곡면 어셈블리는 폴리곤이 안 나온다).

실행: cd sionna2 && PYTHONPATH=src ~/.venvs/py312/bin/python benchmark/measure_reference_props.py
산출: outputs/reference_props.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import trimesh

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, "src"))

REF = os.path.join(_ROOT, "assets", "meshes", "reference")
OUT = os.path.join(_ROOT, "outputs", "reference_props.json")

PROPS = {
    "holybro_1345": dict(
        file="1345_prop_cw.stl", label="Holybro 1345 (13x4.5 in)",
        nominal_dia_mm=330.2, nominal_pitch_in=4.5,
        source="PX4-gazebo-models (BSD-3)",
        caveat="트위스트 워시아웃 0 — 이상화 로프트. 트위스트 기준으로 쓰지 말 것."),
    "3dr_solo": dict(
        file="solo_prop_cw.stl", label="3DR Solo 10 in",
        nominal_dia_mm=254.0, nominal_pitch_in=4.5,
        source="rotors_simulator 계열",
        caveat="소비자용 쿼드 프롭(10 in). 공칭 피치 4.5 in 은 가정. "
               "⛔2026-08-16 정정: «DJI 급에 가장 가까운 참조» 였다는 옛 판단은 철회됐다 — "
               "실물 DJI(Mini 2 공식 CAD)와 대보니 참조 넷 중 유일한 이상치다"
               "(c/c_max @0.70R: Solo 계열 0.577 ↔ DJI 0.866 ↔ Yuneec 0.866)."),
    "yuneec_typhoon": dict(
        file="prop_cw_assembly_remeshed_v3.stl", label="Yuneec Typhoon H480",
        nominal_dia_mm=None, nominal_pitch_in=None,
        source="Typhoon H480 실물 CAD (report03 대조용)",
        caveat="헥사 기체용. 허브 어셈블리 포함일 수 있음."),
}

# 측정 반경 격자 (r/R)
RR = np.round(np.arange(0.10, 0.98, 0.025), 4)


def _prep(path):
    """STL → mm 단위, 회전축이 z 가 되도록 정렬, 원점 중심."""
    m = trimesh.load(path, force="mesh")
    ext = np.asarray(m.extents, float)
    unit = "mm" if ext.max() > 5.0 else "m"
    if unit == "m":
        m.apply_scale(1000.0)
    m.apply_translation(-m.bounds.mean(axis=0))
    ext = np.asarray(m.extents, float)
    spin = int(np.argmin(ext))                 # 회전축 = 디스크가 납작한 축
    order = [a for a in range(3) if a != spin] + [spin]
    V = np.asarray(m.vertices)[:, order]
    m = trimesh.Trimesh(vertices=V, faces=np.asarray(m.faces), process=False)
    return m, unit, ext


def _cyl_sections(m, n_sample=2_000_000, seed=0):
    """표면을 조밀 샘플링해 원통좌표 (rho, phi, z) 로 반환.

    ⚠ 평면절단(스팬축 수직)을 쓰지 않는 이유: 스윕이 큰 프롭(3DR Solo)은 팁이 옆으로
      밀려 bbox 최장축 위에 없다(측정: 스팬축 최대 93.3 mm ≪ R_disc 127.0 mm)라
      바깥쪽 절단이 블레이드를 통째로 빗나간다. 또 비폐곡면 어셈블리(Typhoon, 35 조각)는
      절단이 열린 경로가 되어 폴리곤이 안 나온다.
      **원통 단면**은 프로펠러 단면의 정식 정의이자 두 문제 모두에 면역이다."""
    rng = np.random.default_rng(seed)
    pts, _ = trimesh.sample.sample_surface(m, int(n_sample), seed=int(seed))
    rho = np.hypot(pts[:, 0], pts[:, 1])
    phi = np.arctan2(pts[:, 1], pts[:, 0])
    return rho, phi, pts[:, 2], pts


def _blade_cluster(phi_sel):
    """한 반경 고리에서 **블레이드 한 장**만 골라낸다(φ 최대공백 기준 군집)."""
    if len(phi_sel) < 40:
        return None
    o = np.sort(phi_sel)
    gaps = np.diff(np.r_[o, o[0] + 2 * np.pi])
    k = int(np.argmax(gaps))
    start = o[(k + 1) % len(o)]
    rel = np.mod(phi_sel - start, 2 * np.pi)
    # 가장 큰 공백 다음부터 이어지는 덩어리 = 한 장
    ro = np.sort(rel)
    g2 = np.diff(ro)
    cut = ro[int(np.argmax(g2))] if len(g2) else ro[-1]
    m = rel <= cut + 1e-12
    return m if m.sum() >= 30 else None


def _section_metrics(u, v):
    """단면 점구름(u=접선 호길이, v=축방향) → 시위·피치각·두께·캠버."""
    P = np.c_[u, v]
    from scipy.spatial import ConvexHull
    try:
        Q = P[ConvexHull(P).vertices]
    except Exception:
        return None
    D = Q[:, None, :] - Q[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    c = float(np.sqrt(d2[i, j]))
    if c <= 0:
        return None
    e = (Q[j] - Q[i]) / c
    # 피치각: 시위선이 회전평면(접선방향 u)과 이루는 각
    theta = float(np.degrees(np.arctan2(abs(e[1]), abs(e[0]))))
    R2 = np.array([[e[0], e[1]], [-e[1], e[0]]])
    Pc = (P - Q[i]) @ R2.T
    n = 41
    xs = np.linspace(0.03, 0.97, n) * c
    hw = (c / (n - 1)) * 0.9
    up, lo = [], []
    for x in xs:
        mm = np.abs(Pc[:, 0] - x) <= hw
        if mm.sum() < 3:
            up.append(np.nan); lo.append(np.nan); continue
        up.append(Pc[mm, 1].max()); lo.append(Pc[mm, 1].min())
    up, lo = np.asarray(up), np.asarray(lo)
    ok = np.isfinite(up) & np.isfinite(lo)
    if ok.sum() < 8:
        return None
    t = up[ok] - lo[ok]; cam = 0.5 * (up[ok] + lo[ok]); xo = xs[ok] / c
    it, ic = int(np.argmax(t)), int(np.argmax(np.abs(cam)))
    return dict(chord_mm=c, theta_deg=theta,
                t_over_c=float(t[it] / c), t_peak_x_over_c=float(xo[it]),
                camber_over_c=float(abs(cam[ic]) / c), camber_peak_x_over_c=float(xo[ic]))


def measure(key, meta):
    path = os.path.join(REF, meta["file"])
    if not os.path.exists(path):
        return dict(key=key, error=f"missing {path}")
    m, unit, ext = _prep(path)
    rho, phi, z, pts = _cyl_sections(m)
    R_disc = float(np.percentile(rho, 99.99))          # 팁 (이상점 방어)

    rows = []
    for rr in RR:
        r = rr * R_disc
        band = np.abs(rho - r) <= max(0.006 * R_disc, 0.6)
        if band.sum() < 60:
            continue
        sel = _blade_cluster(phi[band])
        if sel is None:
            continue
        pb, zb = phi[band][sel], z[band][sel]
        u = r * (pb - pb.mean())                        # 접선 호길이
        mt = _section_metrics(u, zb)
        if mt is None:
            continue
        # 허브/모터캡 배제: 익형이 아니면(t/c 너무 크거나 각폭이 넓으면) 버린다
        ang_deg = float(np.degrees(pb.max() - pb.min()))
        if mt["t_over_c"] > 0.20 or ang_deg > 75.0:
            mt["rejected"] = f"hub-like (t/c={mt['t_over_c']:.3f}, arc={ang_deg:.0f}deg)"
        rows.append(dict(r_over_R=float(rr), arc_deg=ang_deg,
                         chord_over_R=float(mt["chord_mm"] / R_disc), **mt))

    good = [r for r in rows if "rejected" not in r]
    ch = [r["chord_over_R"] for r in good]
    i_max = int(np.argmax(ch)) if ch else -1
    band_ok = [r for r in good if 0.25 <= r["r_over_R"] <= 0.90]
    cam_v = [r["camber_over_c"] for r in band_ok]
    tc_v = [r["t_over_c"] for r in band_ok]
    return dict(
        key=key, label=meta["label"], file=meta["file"], source=meta["source"],
        caveat=meta["caveat"], unit_detected=unit,
        nominal_dia_mm=meta["nominal_dia_mm"], nominal_pitch_in=meta["nominal_pitch_in"],
        bbox_mm=[float(v) for v in ext], R_disc_mm=R_disc, disc_dia_mm=2 * R_disc,
        n_stations=len(rows), n_stations_used=len(good),
        chord_max_over_R=float(ch[i_max]) if i_max >= 0 else None,
        chord_peak_r_over_R=float(good[i_max]["r_over_R"]) if i_max >= 0 else None,
        camber_over_c_mean_025_090=float(np.mean(cam_v)) if cam_v else None,
        camber_over_c_range=[float(np.min(cam_v)), float(np.max(cam_v))] if cam_v else None,
        camber_peak_x_over_c_mean=float(np.mean([r["camber_peak_x_over_c"] for r in band_ok]))
        if band_ok else None,
        t_over_c_range=[float(np.min(tc_v)), float(np.max(tc_v))] if tc_v else None,
        theta_deg_by_rr={f"{r['r_over_R']:.2f}": round(r["theta_deg"], 2) for r in good},
        stations=rows,
    )


def main():
    t0 = time.time()
    res = {k: measure(k, v) for k, v in PROPS.items()}
    for k, r in res.items():
        if "error" in r:
            print(f"[skip] {k}: {r['error']}"); continue
        print(f"{r['label']:28s} disc {r['disc_dia_mm']:7.2f} mm  "
              f"c_max/R {r['chord_max_over_R']:.4f} @ r/R {r['chord_peak_r_over_R']:.2f}  "
              f"camber {r['camber_over_c_mean_025_090']*100 if r['camber_over_c_mean_025_090'] else float('nan'):5.2f}%  "
              f"t/c {r['t_over_c_range'][0]*100:4.1f}-{r['t_over_c_range'][1]*100:4.1f}%")
    doc = dict(
        meta=dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
                  purpose="실물 참조 프로펠러 CAD 3종 측정 — 같은 급 소형 프롭의 참조 밴드",
                  #  ⛔ m8 정정(2026-08-16): 옛 문면은 «스팬축 수직 평면 절단» 이었는데
                  #     실제 코드(_cyl_sections)는 **원통 단면**이고, 그 docstring 이 평면절단을
                  #     못 쓰는 이유를 적고 있다. 측정값 자체는 옳다 — 틀린 건 기록이었다.
                  method="원통 단면(반경 r 인 원통으로 절단) → 최대캘리퍼 시위선 "
                         "→ 시위좌표계 상하면에서 두께·캠버",
                  r_over_R_grid=[float(v) for v in RR],
                  warning=("세 CAD 모두 시뮬/시각화용이지 계측 스캔이 아니다. "
                           "1345 는 워시아웃 0 이라 트위스트 기준 부적합. "
                           "⛔2026-08-16 정정: 옛 문장 «저장소에 DJI 프로펠러 실물 기하는 "
                           "존재하지 않는다» 는 거짓이 됐다 — assets/meshes/reference/"
                           "WM161_zhankai_1k.glb (DJI Mini 2 공식)에 날 8장·허브 4개가 있다. "
                           "1차 앵커는 그 GLB 이고, 여기 3종은 참조 밴드로 쓴다."),
                  runtime_s=round(time.time() - t0, 1)),
        props=res)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    os.replace(tmp, OUT)
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
