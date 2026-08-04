# -*- coding: utf-8 -*-
"""
report15_probe_blade_flash.py — **블레이드 플래시(정반사 글린트)가 스톡 RT 에 존재하는가**
==========================================================================================

`report15_probe.py` 의 부록. 같은 배선·같은 규약을 재사용하고 결과를 같은 JSON 에
`blade_flash` 로 덧붙인다(⛔ 새 산출물·기존 산출물 덮어쓰기 없음).

왜 따로 묻나 — 마이크로도플러의 교과서적 정체는 **블레이드 플래시**다: 블레이드 면이 시선의
이등분선에 수직이 되는 순간 강한 **정반사** 글린트가 번쩍인다. 본편에서 확인된 것은
"프롭 경유 **확산** 경로의 복소합이 로터 위상에 따라 변한다" 였고, 이는 플래시와 다른 기전이다.
그래서 여기서는 **정반사 채널만 켜고**(diffuse_reflection=False) 자세×로터위상 격자를 훑어
**프롭 그룹을 맞은 정반사 경로가 단 하나라도 나오는지** 센다.

양성 대조: 시선 이등분선에 법선을 맞춘 금속 평판. 여기서 경로가 나와야 "정반사 탐색기가
살아 있는데 프롭에서만 안 나온다" 라고 말할 수 있다(안 나오면 실험이 무효다).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import report15_probe as P                                            # noqa: E402
from drones import DRONES                                             # noqa: E402
from scene_build import build_scene, Part                             # noqa: E402
from geom import Mesh                                                 # noqa: E402

JSON = P.OUT_JSON


def plate_control(spp=8_000_000, az=P.AZ_DEG, el=P.EL_DEG):
    """양성 대조 — 이등분선에 법선을 맞춘 한 변 0.3 m 금속 평판(프롭 지름 급)."""
    u = P.look_dir(az, el)
    e1, e2 = P.basis_perp(u)
    h = 0.15
    m = Mesh("plate")
    idx = [m.add_vertex(*(s1 * h * e1 + s2 * h * e2))
           for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    m.add_quad(*idx, group="plate")
    d = os.path.join(P.SCRATCH, "flash_plate")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "plate.obj")
    m.write_obj(p)
    sc = build_scene([Part(name="plate", obj=p, mat_key="metal")], fc=P.FC)
    g2 = P.id_to_group(sc, "plate")
    P.place(sc, az=az, el=el)
    r = P.rt_echo(sc, spp, 1, diffuse=False, id2grp=g2)
    P.drop_scratch(d)
    return dict(side_m=2 * h, az_deg=az, el_deg=el, spp=int(spp),
                n_paths=int(r["n_paths"]), amp_db=r["amp_db"],
                works=bool(r["n_paths"] > 0))


def scan(spec, spp=256_000_000, n_az=12, els=(0., 10., 20., 30., 45., 60.), n_phase=8):
    """자세(az×el) × 로터위상 격자를 정반사 전용으로 훑어 **부위별** 경로수를 센다."""
    azs = list(np.arange(0.0, 360.0, 360.0 / n_az))
    period = 360.0 / max(1, int(spec.prop_blades))
    phis = list(np.linspace(0.0, period, int(n_phase), endpoint=False))
    rows, tot_prop, tot_any = [], 0, 0
    for i, ph in enumerate(phis):
        sc, _, d = P.build_posed_scene(spec, float(ph), f"F{i:02d}")
        g2 = P.id_to_group(sc, spec.key)
        for el in els:
            for az in azs:
                P.place(sc, az=az, el=el)
                r = P.rt_echo(sc, spp, 1, diffuse=False, id2grp=g2)
                gp = r.get("groups") or {}
                npr = int(gp.get("prop", {}).get("n", 0))
                tot_prop += int(npr > 0); tot_any += int(r["n_paths"] > 0)
                if r["n_paths"]:
                    rows.append(dict(phase_deg=float(ph), az_deg=float(az), el_deg=float(el),
                                     n_paths=int(r["n_paths"]), n_prop=npr,
                                     amp_db=r["amp_db"],
                                     groups={g: v["n"] for g, v in gp.items()}))
        P.drop_scratch(d)
        print(f"    [{spec.key}] 위상 {ph:6.2f}° 완료 — 누적 정반사자세 {tot_any}, 그중 프롭 {tot_prop}",
              flush=True)
    n_cell = len(azs) * len(els) * len(phis)
    return dict(spp=int(spp), az_deg=azs, el_deg=list(els), phases_deg=phis,
                n_cells=n_cell, n_cells_with_specular=tot_any,
                n_cells_with_prop_specular=tot_prop,
                frac_cells_with_specular=float(tot_any / n_cell),
                frac_cells_with_prop_specular=float(tot_prop / n_cell),
                rows=rows,
                note=("블레이드 플래시가 스톡 RT 에 있으려면 프롭 그룹을 맞은 정반사 경로가 "
                      "적어도 일부 (자세, 위상) 칸에서 나와야 한다."))


def main():
    with open(JSON) as f:
        J = json.load(f)
    out = dict(plate_control=plate_control(), airframes={})
    print(f"  양성대조 금속평판: 경로 {out['plate_control']['n_paths']}개 "
          f"→ 정반사 탐색기 동작 {out['plate_control']['works']}", flush=True)
    for key in J["airframes"]:
        print(f"  ── {key} 정반사 격자 스캔", flush=True)
        out["airframes"][key] = scan(DRONES[key])
        s = out["airframes"][key]
        print(f"     → 정반사 칸 {s['n_cells_with_specular']}/{s['n_cells']} "
              f"({100*s['frac_cells_with_specular']:.2f}%), "
              f"그중 **프롭** 정반사 칸 {s['n_cells_with_prop_specular']} "
              f"({100*s['frac_cells_with_prop_specular']:.2f}%)", flush=True)
    J["blade_flash"] = out
    with open(JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ blade_flash 추가 → {JSON}")


if __name__ == "__main__":
    main()
