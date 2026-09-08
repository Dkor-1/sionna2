#!/usr/bin/env python
"""우리 실외 씬과 엔비디아 기본 씬이 **기하로** 무엇이 다른가.

왜 있나 — 2026-09-08 에 사용자가 물었다: 「엔비디아 기본 제공 환경이랑 뭐가 다른지
분석해볼래?」 우리 씬에서만 «자세마다 지면 몫이 통째로 빠지는» 일이 나기 때문이다
(outputs/outdoor_dip_origin_0908.json).

■ ⛔이 원장이 **죽인** 가설 셋 (전부 재서 죽였다)

  ① 「우리 지면 재질이 거울(S=0)이라서」 — **아니다.**
     기본 씬 재질도 전부 S=0.0 이다(거리 협곡 5 종 · 뮌헨 5 종).
     ⚠거칠기를 주면 우리 씬의 무너짐이 **사라지는 것은 맞다**(S=0.3 에서 낙차 74 → 0).
       그래서 「거칠기가 끈다」는 참이고 「거칠기가 두 씬을 갈랐다」는 거짓이다. 다른 말이다.

  ② 「우리 씬은 면이 적어서」 — **아니다.**
     거리 협곡도 삼각형이 **74 개**로 우리와 같다(뮌헨은 38,936).

  ③ 「우리 지면이 삼각형 두 개짜리 큰 평판이라서」 — **아니다.**
     세 씬 **모두** 지면이 삼각형 2 개짜리 평면이고, 우리 것이 **가장 작다**:
         우리      120 × 120 m   =    14,400 m²
         거리 협곡  186 × 121 m   =    22,579 m²
         뮌헨      1476 × 1206 m  = 1,778,875 m²

■ ⭐남은 가설 (⛔아직 안 시험했다)
  「우리 씬에서는 지면 반사가 **한 갈래에 몰려** 있고, 기본 씬에서는 여러 면·여러
   갈래로 흩어져 있다. 그래서 우리 씬에서는 그 한 갈래를 잃으면 총합이 무너지고,
   기본 씬에서는 하나를 잃어도 티가 안 난다.」
  ⚠이 가설과 어긋나 보이는 관측이 하나 있다 — 무너지는 자세의 **경로 수가 오히려
    몇 개 많다**(1,897 대 1,893). 한 갈래가 사라지는 것이 아니라 **갈라지는** 것일 수도 있다.
  ⇒ 가르려면 자세 몇 개의 **경로 목록을 직접 덤프**해서 지면 갈래를 세어야 한다.
    이 원장은 거기까지 안 간다.

⛔「솔버가 틀렸다」로 결론짓지 않는다(집 규약). 이 원장이 말하는 것은
  「자주 드는 설명 셋이 이 차이를 설명하지 못한다」까지다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" SIONNA2_ALLOW_CPU=1 OMP_NUM_THREADS=1 nice -n 19 \
      /workspace/.venvs/py312/bin/python benchmark/scene_compare_0908.py
    → outputs/scene_compare_0908.json
"""
from __future__ import annotations

import argparse, glob, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = os.path.join(ROOT, "outputs", "scene_compare_0908.json")
OURS_DIR = os.path.join(ROOT, "assets", "meshes", "outdoor01")
BUILTINS = ("simple_street_canyon", "munich")
HORIZ_COS = 0.95          # 법선의 |z| 성분이 이보다 크면 «수평면» 으로 센다


def tri_areas_normals(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a)
    ln = np.linalg.norm(n, axis=1)
    return 0.5 * ln, np.abs(n[:, 2]) / np.maximum(ln, 1e-30)


def read_obj(path):
    V, F = [], []
    with open(path, encoding="utf-8") as f:
        for l in f:
            if l.startswith("v "):
                V.append([float(x) for x in l.split()[1:4]])
            elif l.startswith("f "):
                F.append([int(x.split("/")[0]) - 1 for x in l.split()[1:4]])
    return np.asarray(V, float), np.asarray(F, int)


def _span(v):
    return round(float(v.max() - v.min()), 2)


def describe(name, parts):
    """parts: [(부품이름, V, F, 산란계수 또는 None)] → 한 씬의 기하 요약."""
    rows, A, tot = [], [], 0
    for nm, V, F, sc in parts:
        ar, nz = tri_areas_normals(V, F)
        hz = nz > HORIZ_COS
        tot += int(F.shape[0])
        A.append(ar)
        rows.append({
            "part": nm, "n_tri": int(F.shape[0]),
            "scattering_coefficient": sc,
            "z_min": round(float(V[:, 2].min()), 2),
            "z_max": round(float(V[:, 2].max()), 2),
            "span_x_m": _span(V[:, 0]), "span_y_m": _span(V[:, 1]),
            "area_median_m2": round(float(np.median(ar)), 2),
            "area_max_m2": round(float(ar.max()), 2),
            "n_horizontal_tri": int(hz.sum()),
            "horizontal_area_m2": round(float(ar[hz].sum()), 1),
        })
    Aall = np.concatenate(A) if A else np.zeros(1)
    #: ⭐지면 노릇을 하는 부품 = 수평 넓이가 가장 큰 것
    gnd = max(rows, key=lambda r: r["horizontal_area_m2"]) if rows else None
    return {
        "scene": name, "n_parts": len(rows), "n_tri_total": tot,
        "tri_area_median_m2": round(float(np.median(Aall)), 2),
        "tri_area_max_m2": round(float(Aall.max()), 1),
        "n_tri_over_1000_m2": int((Aall > 1000).sum()),
        "scattering_all_zero": (None if any(r["scattering_coefficient"] is None
                                            for r in rows)
                                else bool(all(r["scattering_coefficient"] == 0.0
                                              for r in rows))),
        "ground_like_part": None if gnd is None else {
            "part": gnd["part"], "n_tri": gnd["n_tri"],
            "span_x_m": gnd["span_x_m"], "span_y_m": gnd["span_y_m"],
            "horizontal_area_m2": gnd["horizontal_area_m2"]},
        "parts": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    t0, scenes = time.time(), {}

    #: ── 우리 씬 — .obj 를 직접 읽는다(솔버를 안 띄운다) ──────────────────
    try:
        from materials import MATERIALS                                # noqa: PLC0415
    except Exception:                                                  # noqa: BLE001
        MATERIALS = {}
    ours = []
    for f in sorted(glob.glob(f"{OURS_DIR}/*.obj")):
        V, F = read_obj(f)
        nm = os.path.splitext(os.path.basename(f))[0]
        #: 재질은 elevation_sweep_md.ENV_SPECS 가 정한다 — 지면은 concrete_dark
        key = "concrete_dark" if nm == "ground" else (
            "metal" if nm.startswith("pole") else "concrete_light")
        sc = MATERIALS.get(key, {}).get("S")
        ours.append((nm, V, F, None if sc is None else float(sc)))
    scenes["ours_outdoor01"] = describe("ours_outdoor01", ours)

    #: ── 기본 씬 — 솔버로 열어 읽는다 ────────────────────────────────────
    try:
        import sionna.rt as rt                                         # noqa: PLC0415
        for nm in BUILTINS:
            sc_ = rt.load_scene(getattr(rt.scene, nm))
            parts = []
            for k, o in sc_.objects.items():
                m = getattr(o, "mi_mesh", None)
                if m is None:
                    continue
                V = np.array(m.vertex_positions_buffer()).reshape(-1, 3)
                F = np.array(m.faces_buffer()).reshape(-1, 3)
                try:
                    s_ = float(np.asarray(
                        o.radio_material.scattering_coefficient).ravel()[0])
                except Exception:                                      # noqa: BLE001
                    s_ = None
                parts.append((k, V, F, s_))
            scenes[nm] = describe(nm, parts)
    except Exception as e:                                             # noqa: BLE001
        scenes["_builtin_error"] = f"{type(e).__name__}: {e}"

    got = [v for k, v in scenes.items() if isinstance(v, dict)]
    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "benchmark/scene_compare_0908.py",
            "question_ko": "우리 실외 씬과 엔비디아 기본 씬이 기하로 무엇이 다른가",
            "why_ko": "우리 씬에서만 «자세마다 지면 몫이 통째로 빠지는» 일이 난다"
                      "(outputs/outdoor_dip_origin_0908.json). 그 차이를 기하에서 찾는다",
            "horizontal_rule_ko": f"법선의 |z| 성분이 {HORIZ_COS} 보다 크면 «수평면»",
            "killed_hypotheses_ko": [
                "① 재질이 거울이라서 — 아니다. 기본 씬도 전부 S=0.0 이다. "
                "(⚠거칠기를 주면 우리 씬의 무너짐이 사라지는 것은 참이다 — 다른 말이다.)",
                "② 면이 적어서 — 아니다. 거리 협곡도 삼각형 74 개로 우리와 같다.",
                "③ 지면이 삼각형 둘짜리 큰 평판이라서 — 아니다. 세 씬 모두 그렇고 "
                "우리 것이 가장 작다.",
            ],
            "open_hypothesis_ko": "지면 반사가 우리 씬에서는 한 갈래에 몰리고 기본 씬에서는 "
                                  "흩어져 있다. ⚠무너지는 자세의 경로 수가 오히려 몇 개 "
                                  "많다는 관측과 어긋나 보인다. 가르려면 경로 목록을 덤프해야 "
                                  "한다 — 이 원장은 거기까지 안 간다",
            "limits_ko": [
                "⛔「솔버가 틀렸다」로 결론짓지 않는다.",
                "⚠드론 고도가 다르다 — 우리 씬 20 m, 기본 씬 25 m(ENV_BUILTIN_ALT).",
                "⚠기하만 본다. 재질의 유전율·도전율은 안 봤다.",
            ],
        },
        "summary": {
            "n_scenes": len(got),
            "n_tri_total": {v["scene"]: v["n_tri_total"] for v in got},
            "ground_span_m": {v["scene"]: [v["ground_like_part"]["span_x_m"],
                                           v["ground_like_part"]["span_y_m"]]
                              for v in got if v.get("ground_like_part")},
            "ground_n_tri": {v["scene"]: v["ground_like_part"]["n_tri"]
                             for v in got if v.get("ground_like_part")},
            "ground_area_m2": {v["scene"]: v["ground_like_part"]["horizontal_area_m2"]
                               for v in got if v.get("ground_like_part")},
            "scattering_all_zero": {v["scene"]: v["scattering_all_zero"] for v in got},
            "ours_ground_is_smallest": None,
            "elapsed_s": round(time.time() - t0, 1),
        },
        "scenes": scenes,
    }
    ga = doc["summary"]["ground_area_m2"]
    if "ours_outdoor01" in ga and len(ga) > 1:
        doc["summary"]["ours_ground_is_smallest"] = bool(
            ga["ours_outdoor01"] == min(ga.values()))
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"⭐{a.out}  씬 {len(got)}")
    for k, v in doc["summary"].items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
