# -*- coding: utf-8 -*-
"""
mesh_check.py — **trimesh 로 메쉬를 검증한다** (자작 geom.py 가 못 잡는 것들)
==============================================================================
왜 필요한가 (2026-07-14)
  geom.py 는 의존성 없이 삼각형을 쌓는 도구다. 대신 **메쉬가 옳은지 검사할 능력이 없다.**
  실제로 조용히 살아 있던 버그:
    · prop_blade 의 **캡 2장이 뒤집혀 있었다**(법선 안쪽). 주석엔 "outward" 라고 적혀 있었다.
      → PO 의 조명 판정(n̂·û>0)이 그 면들을 **잘못 포함/제외**한다.
      → 프로펠러는 **마이크로도플러의 신호 그 자체**라 특히 민감하다.
  trimesh 는 이걸 1초 만에 잡는다. (설치 가능하다 — py312 는 사용자 소유 uv venv 다.
  geom.py 주석의 "설치 권한 없음" 은 **낡은 이유**였다.)

무엇을 검사하나 — **부품(연결요소) 단위**로. 드론은 프리미티브의 합집합이라 전체 메쉬는
원래 watertight 가 아니다. 의미 있는 검사는 **부품별** 검사다.
  1. watertight   : 부품이 닫힌 껍질인가 (구멍 없음)
  2. winding      : 이웃한 면들이 같은 방향으로 감겼는가
  3. 법선 방향    : 바깥을 향하는가 (닫힌 부품의 부호있는 부피 > 0)
  4. 퇴화면·중복정점

실행:  python src/mesh_check.py          (DRONES 레지스트리 전 기종 + 챔버 전수 검사)
       assert_ok() 를 빌드 파이프라인에서 부르면 회귀를 막는다.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _tm(v, f):
    import trimesh
    return trimesh.Trimesh(vertices=np.asarray(v, float),
                           faces=np.asarray(f, int), process=True)


def check_mesh(mesh, name="mesh") -> dict:
    """geom.Mesh → 부품별 검진 결과. 그룹(부위) 단위로 쪼개서 본다."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    groups = {}
    for grp in sorted(set(G.tolist())):
        f = F[G == grp]
        used = np.unique(f)
        remap = {int(o): i for i, o in enumerate(used)}
        tm = _tm(V[used], np.vectorize(remap.get)(f))
        comps = tm.split(only_watertight=False)
        n_wt = sum(1 for c in comps if c.is_watertight)
        n_inward = sum(1 for c in comps if c.is_watertight and c.volume < 0)
        n_badwind = sum(1 for c in comps if not c.is_winding_consistent)
        n_degen = int((tm.area_faces < 1e-14).sum())
        groups[grp] = dict(
            n_faces=int(len(f)), n_parts=len(comps),
            watertight=f"{n_wt}/{len(comps)}",
            inward_normals=n_inward, bad_winding=n_badwind, degenerate=n_degen,
            ok=(n_wt == len(comps) and n_inward == 0 and n_badwind == 0 and n_degen == 0),
        )
    return dict(name=name, groups=groups, ok=all(g["ok"] for g in groups.values()))


def report(res: dict) -> str:
    lines = [f"  {'그룹':10s} {'면':>6} {'부품':>5} {'watertight':>11} {'법선안쪽':>8} "
             f"{'winding깨짐':>11} {'퇴화면':>6}  판정"]
    for grp, g in res["groups"].items():
        lines.append(f"  {grp:10s} {g['n_faces']:6d} {g['n_parts']:5d} {g['watertight']:>11s} "
                     f"{g['inward_normals']:8d} {g['bad_winding']:11d} {g['degenerate']:6d}"
                     f"  {'✅' if g['ok'] else '❌'}")
    return "\n".join(lines)


#  ⭐⭐ 2026-08-07 — **그룹 사이 관통 검사**. 위의 검사는 전부 «그룹 안»만 본다.
#     `build_drone` 은 그룹끼리 불리언 합집합을 **하지 않으므로**, 프로펠러가 모터 벨 속에
#     박히면 겹친 자리의 면이 **둘 다 살아서** PO 적분에 들어간다(면적 이중계상). 예외는 안 난다.
#     실제로 mini5pro 가 2026-07-14 부터 24 일 동안 그 상태였다 — 앞 프롭 밑면이 벨 윗면보다
#     8.06 mm 아래였고 프롭 면적의 9.6 %(1521 mm²)가 이중계상됐다. 아무 검사도 그걸 안 봤다.
#
#  ⚠ **판정법을 여기 적어 둔다**(안 적어서 «526 ↔ 662» 혼선이 났다):
#     · 벨    = 그 로터 축에서 반경 60·(diag/438.8) mm 안의 'motor' 그룹 정점들이 만드는
#               (최대반경 rad, z 범위 [zlo, zhi]).
#     · 관통  = 'prop' 그룹 **삼각형 중심**이 (반경 ≤ rad) 이고 (zlo ≤ z ≤ zhi − 1 µm).
#     · 깊이  = zhi − (관통한 삼각형 중심의 최소 z).  단위 mm, 외형보정(sz) 적용 후.
PROP_BELL_MAX_DEPTH_MM = {
    #  기본 예산 — 우리 블레이드 로프트는 뿌리가 장착면보다 0.7~2.0 mm **아래로** 내려간다
    #  (익형 비틀림). 프롭 허브 밑면을 벨 윗면에 앉히면(2026-08-07 C1) 그만큼이 캡과 겹친다.
    "_default": 2.5,
    #  ↓ 설계상 겹치는 기체 — 값은 «지금 이만큼이다» 라는 기록이지 «이만큼이 옳다» 가 아니다.
    "mini2":       4.0,   # 프롭 마운트 나사머리 포스트가 프롭 허브 보어를 채운다(PROP_SCREW_POSTS).
                          #   포스트를 벨 꼭대기부터 꽉 찬 기둥으로 짓는 것이 그 라운드의 결정이었다.
    "typhoonh480": 4.0,   # «모터 벨 + 프롭 허브 축» 원통이 허브 보어를 관통한다. 설계인지 결함인지
                          #   아직 안 갈랐다(2026-08-07 선언).
    "m350rtk":    25.0,   # 모터 **상부 커버**(프롭 위를 덮는 원통)가 'motor' 그룹이라 벨 z 범위가
                          #   프롭 위까지 뻗는다. 이 기체는 사실상 이 검사가 안 걸린다 — 선언.
}


def check_prop_bell(spec, verbose=False) -> dict:
    """프로펠러가 모터 벨 **속에 박혔는가** — 그룹 사이 관통 검사(판정법은 위 주석)."""
    from drones import build_drone, rotor_layout
    m = build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    G = np.asarray(m.g)
    F = np.asarray(m.f, np.int64)
    if not (G == "prop").any() or not (G == "motor").any():
        return dict(key=spec.key, checked=False, ok=True, reason="prop 또는 motor 그룹 없음")
    mot = V[np.unique(F[G == "motor"])]
    Fp = F[G == "prop"]
    Cp = V[Fp].mean(1)
    ar = 0.5 * np.linalg.norm(np.cross(V[Fp[:, 1]] - V[Fp[:, 0]],
                                       V[Fp[:, 2]] - V[Fp[:, 0]]), axis=1)
    rows, depth, tris, area = [], 0.0, 0, 0.0
    for i, r in enumerate(rotor_layout(spec)):
        cx, cy, cz = np.asarray(r["center"], float) * 1000.0
        near = np.hypot(mot[:, 0] - cx, mot[:, 1] - cy) < 60.0 * (spec.diagonal_mm / 438.8)
        if not near.any():
            continue
        bm = mot[near]
        rad = float(np.hypot(bm[:, 0] - cx, bm[:, 1] - cy).max())
        zlo, zhi = float(bm[:, 2].min()), float(bm[:, 2].max())
        sel = ((np.hypot(Cp[:, 0] - cx, Cp[:, 1] - cy) <= rad)
               & (Cp[:, 2] >= zlo) & (Cp[:, 2] <= zhi - 1e-3))
        dep = float(zhi - Cp[sel][:, 2].min()) if sel.any() else 0.0
        rows.append(dict(rotor=i, gap_mm=round(float(cz - zhi), 4), depth_mm=round(dep, 4),
                         tris=int(sel.sum()), area_mm2=round(float(ar[sel].sum()), 2)))
        depth = max(depth, dep); tris += int(sel.sum()); area += float(ar[sel].sum())
    lim = PROP_BELL_MAX_DEPTH_MM.get(spec.key, PROP_BELL_MAX_DEPTH_MM["_default"])
    res = dict(key=spec.key, checked=True, per_rotor=rows, max_depth_mm=round(depth, 4),
               budget_mm=lim, tris=tris, area_mm2=round(area, 2),
               area_pct=round(100.0 * area / float(ar.sum()), 3) if ar.sum() else 0.0,
               ok=bool(depth <= lim))
    if verbose:
        print(f"  프롭↔벨 관통: 깊이 {depth:.3f} mm (예산 {lim}) · 삼각형 {tris} · "
              f"면적 {area:.1f} mm² ({res['area_pct']} %)  {'✅' if res['ok'] else '❌'}")
    return res


#  ⭐⭐ 2026-08-10 — **솔리드 자(내부판정) 관통 검사**. 위 check_prop_bell 의 원통 근사는
#     벨을 (최대반경 × z범위) 원통으로 부풀려 보므로 **진짜 이중계상 면적과 다르게 센다**
#     (확정검사 meshgate_verify.json check5: mini5pro 원통 2.50 % ↔ 솔리드 0.81 %,
#      m350rtk 원통 11.27 % ↔ 솔리드 4.27 %). PO 가 실제로 이중계상하는 것은 «벨 솔리드
#     안의 프롭 면적» 이므로 trimesh contains() 로 직접 센다. 두 자를 **둘 다** 돌린다 —
#     원통 자는 빠른 회귀 감지용, 솔리드 자가 판정 기준이다.
#  ⚠ 예산값의 뜻은 PROP_BELL_MAX_DEPTH_MM 과 같다 — «지금 이만큼이다» 라는 기록이지
#     «이만큼이 옳다» 가 아니다(2026-08-10 전수 실측으로 초기화).
PROP_BELL_SOLID_AREA_PCT = {
    "_default": 0.1,      # 목표 수준 = matrice4e(0.01 %). mini5pro 도 스탠드오프 1.0 mm
                          #   (PROP_STANDOFF_M) 적용 후 0.00 % 로 이 예산을 탄다.
    "mavic4pro":   1.0,   # 블레이드 뿌리 droop 가 캡과 겹침(0.76 %) — 적용 라운드 선언 잔차.
    "phantom4":    4.2,   # 같은 droop(3.74 %) — 선언 잔차. 스탠드오프 mm 근거가 아직 없다.
    "typhoonh480": 5.5,   # «벨+허브 축» 원통이 허브 보어 관통(5.13 %) — 설계/결함 미판정(선언).
    "m350rtk":     4.5,   # 모터 상부 커버가 프롭 위를 덮는 설계(4.27 %) — 선언.
    "mini2":       3.2,   # 나사머리 포스트가 허브 보어를 채우는 설계(2.98 %) — 선언.
}


def check_prop_bell_solid(spec, verbose=False, mesh=None) -> dict:
    """프롭 삼각형 **중심**이 로터 근방 motor 솔리드(수밀 연결요소) **안**에 드는가 —
    PO 이중계상 면적의 직접 측정. 근사 없음(trimesh contains)."""
    import trimesh
    from drones import build_drone, rotor_layout
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    if not (G == "prop").any() or not (G == "motor").any():
        return dict(key=spec.key, checked=False, ok=True, reason="prop 또는 motor 그룹 없음")
    Fp = F[G == "prop"]
    Cp = V[Fp].mean(1)
    ar = 0.5 * np.linalg.norm(np.cross(V[Fp[:, 1]] - V[Fp[:, 0]],
                                       V[Fp[:, 2]] - V[Fp[:, 0]]), axis=1)
    fm = F[G == "motor"]
    used = np.unique(fm)
    remap = {int(o): i for i, o in enumerate(used)}
    tm = trimesh.Trimesh(vertices=V[used], faces=np.vectorize(remap.get)(fm), process=True)
    comps = tm.split(only_watertight=False)
    inside = np.zeros(len(Cp), bool)
    n_nonwt = 0
    for r in rotor_layout(spec):
        cx, cy, _ = np.asarray(r["center"], float) * 1000.0
        gate = 60.0 * (spec.diagonal_mm / 438.8)
        for c in comps:
            cen = c.bounding_box.centroid
            if np.hypot(cen[0] - cx, cen[1] - cy) > gate:
                continue
            if not c.is_watertight:        # contains() 는 수밀 전제 — 비수밀은 세지 않고 개수만 보고
                n_nonwt += 1
                continue
            near = np.hypot(Cp[:, 0] - cx, Cp[:, 1] - cy) < gate * 1.5
            if near.any():
                hit = c.contains(Cp[near])
                inside[np.where(near)[0][hit]] = True
    pct = round(100.0 * float(ar[inside].sum()) / float(ar.sum()), 3) if ar.sum() else 0.0
    lim = PROP_BELL_SOLID_AREA_PCT.get(spec.key, PROP_BELL_SOLID_AREA_PCT["_default"])
    res = dict(key=spec.key, checked=True, tris=int(inside.sum()),
               area_mm2=round(float(ar[inside].sum()), 2), area_pct=pct,
               budget_pct=lim, nonwatertight_bell_parts=n_nonwt, ok=bool(pct <= lim))
    if verbose:
        print(f"  프롭↔벨 솔리드내부: 삼각형 {res['tris']} · 면적 {res['area_mm2']} mm² "
              f"({pct} %, 예산 {lim} %)  {'✅' if res['ok'] else '❌'}")
    return res


def check_all(verbose=True) -> dict:
    """DRONES 레지스트리 **전 기종** + 챔버 전수 검사(기종 수는 len(DRONES)).
    검사 4층: ① 부품별 수밀·winding·법선(부피부호)·퇴화면(check_mesh)
             ② 프롭↔벨 원통 근사 관통(check_prop_bell — 빠른 회귀 감지)
             ③ 프롭↔벨 솔리드 내부판정(check_prop_bell_solid — 이중계상 면적의 판정 기준)"""
    from drones import DRONES, build_drone
    out = {}
    for k, s in DRONES.items():
        m = build_drone(s)
        r = check_mesh(m, k)
        pb = check_prop_bell(s)
        ps = check_prop_bell_solid(s, mesh=m)
        r["prop_bell"] = pb
        r["prop_bell_solid"] = ps
        r["ok"] = bool(r["ok"] and pb["ok"] and ps["ok"])
        out[k] = r
        if verbose:
            print(f"\n[{k}]  {'✅ 통과' if r['ok'] else '❌ 결함'}")
            print(report(r))
            print(f"  프롭↔벨 관통(원통): 깊이 {pb.get('max_depth_mm', 0)} mm "
                  f"(예산 {pb.get('budget_mm', '-')}) · 삼각형 {pb.get('tris', 0)} · "
                  f"면적 {pb.get('area_mm2', 0)} mm² ({pb.get('area_pct', 0)} %)"
                  f"  {'✅' if pb['ok'] else '❌'}")
            print(f"  프롭↔벨 관통(솔리드): 삼각형 {ps.get('tris', 0)} · "
                  f"면적 {ps.get('area_mm2', 0)} mm² ({ps.get('area_pct', 0)} %, "
                  f"예산 {ps.get('budget_pct', '-')} %)  {'✅' if ps['ok'] else '❌'}")
    return out


def assert_ok():
    """빌드 파이프라인용 — 결함이 있으면 예외를 던진다(회귀 방지)."""
    res = check_all(verbose=False)
    bad = {k: ([g for g, v in r["groups"].items() if not v["ok"]]
               + ([f"prop↔bell(cyl) {r['prop_bell']['max_depth_mm']} mm > "
                   f"{r['prop_bell']['budget_mm']} mm"] if not r["prop_bell"]["ok"] else [])
               + ([f"prop↔bell(solid) {r['prop_bell_solid']['area_pct']} % > "
                   f"{r['prop_bell_solid']['budget_pct']} %"]
                  if not r["prop_bell_solid"]["ok"] else []))
           for k, r in res.items() if not r["ok"]}
    if bad:
        raise AssertionError(f"메쉬 검증 실패 — 결함 그룹: {bad}\n"
                             f"  python src/mesh_check.py 로 상세 확인")
    return True


if __name__ == "__main__":
    print("=" * 84)
    print("trimesh 메쉬 검증 — 부품(연결요소) 단위")
    print("=" * 84)
    res = check_all()
    n_ok = sum(1 for r in res.values() if r["ok"])
    print(f"\n{'='*84}\n결과: {n_ok}/{len(res)} 통과")
    if n_ok < len(res):
        sys.exit(1)
