# -*- coding: utf-8 -*-
"""
mesh_buried.py — **매몰면(buried face) 전수 검사 + PO 이중계상 수리 손잡이** (감사 I3)
================================================================================

용어 한 줄 풀이
  · **매몰면**   : 어떤 부품의 삼각형이 **다른 부품 솔리드 안**에 들어가 있는 것.
                   실물이라면 바깥에서 절대 안 보이는 면이다.
  · **PO**       : 우리 산란 커널 하나(`rcs_po`). **가림(그림자)을 안 본다** — 자기 문서가
                   `rcs_po.py` 46-53행에서 스스로 선언한다. 그래서 매몰면을 **그대로 더한다**.
  · **SBR**      : 다른 커널(`rcs_sbr`, 기본 엔진). 광선이 «처음 맞은 지점» 만 적분하므로
                   매몰면 오차가 **구조적으로 0** 이다.
  · **수밀**     : 껍질에 구멍이 없어 «안/밖» 이 정의되는 상태. 내부판정(contains)의 전제.

왜 필요한가 (2026-08-16)
------------------------
기존 그룹 사이 관통 검사는 `mesh_check.check_prop_bell_solid` **하나뿐**이고 그것은
prop↔motor **한 쌍**만 본다. 나머지 쌍은 검사도 예산도 없었다. 실제로 재 보면 표면적의
**8.0 %(s1000plus) ~ 44.4 %(mini2)** 가 다른 부품 속에 있다. PO 경로에서 이것은 곧
**이중계상**이다 — 주력 표적 두 대(mavic4pro·mini5pro)에서 σ 방위평균 **+2.3 / +4.0 dB**.

⭐ 매몰면은 **두 종류로 갈라야 한다**
------------------------------------
  ① **설계 의도** — battery·pcb·fc 가 **셸(body/canopy) 안**에 있는 것.
     `rcs_po.py` 30-36행이 «반투명 셸을 통과해 내부가 보이는 효과는 셸 |Γ| 축소 +
     내부 |Γ|=1 합산으로 1차 근사» 라고 스스로 적는다. ⇒ **빼면 안 된다.**
     (빼면 σ 지배 부품이 사라진다: m350rtk −6.30 dB · phantom3 −5.73 dB.)
  ② **진짜 결함** — 그 밖의 모든 매몰면. 셸이 금속 상자 안에 든 것, canopy 가 body 안에
     든 것, camera 가 body 안에 든 것, battery 끼리 겹친 것 등. 실물이라면 안 보이는 면이고
     PO 가 그대로 더한다.

  ⚠ **판정 규칙과 그 한계를 여기 못 박는다**:
     면 f 가 «설계 의도» 인 조건은 **(f 의 그룹 ∈ INTERNAL_GROUPS) 이고 (f 를 담은 컨테이너
     그룹이 **전부** SHELL_GROUPS)** 이다. 컨테이너 중 하나라도 셸이 아니면(예: battery 면이
     다른 battery 상자 안에도 있으면, camera 하우징 안에도 있으면) **결함으로 친다** —
     불투명한 금속 솔리드가 실제로 가리기 때문이다.
     ⇒ 다르게 가르면 수치가 달라진다. 대안 규칙(«첫 컨테이너가 이긴다», 그룹 알파벳 순)과의
       차이는 10기체 중 3기체에서 0.16~0.88 pp 다(benchmark/adv_mesh_buried_faces_0816.py 가
       두 규칙을 나란히 잰다). 총 매몰 %는 규칙과 **무관**하다.

무엇을 제공하나
---------------
  · `buried_census(mesh, ...)`   — 전 부품쌍 매몰면 전수. 기체별 예산표의 출처.
  · `buried_face_mask(mesh, ...)`— 면별 True/False. PO 적분에서 **뺄 면**을 고른다.
  · `keep_face_mask(mesh, ...)`  — 그 반대(남길 면). `rcs_po.mesh_to_points(face_mask=…)` 에 그대로 넣는다.

⛔ **기본은 끔** — 이 모듈은 아무도 자동으로 부르지 않는다. `rcs_po.drone_rcs_pattern` 은
   `mesh_fix=` 인자를 **명시**해야만 이 경로를 밟고, 안 주면 옛 결과와 **비트동일**이다.
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


#  ── 그룹 분류 ─────────────────────────────────────────────────────────────── #
#  ⚠ 근거: drones.DRONE_GROUP_MAT 의 부위 뜻 + rcs_po.py 30-36행(셸 투과 1차 근사).
#     «셸» 은 반투명(plastic |Γ|=0.28)이라 그 **안**의 금속을 일부러 합산한다.
INTERNAL_GROUPS = ("battery", "pcb", "fc")     # 셸 안에 있는 것이 **설계**인 내부 산란체
SHELL_GROUPS = ("body", "canopy")              # 반투명 셸 — 이 안에 든 내부 금속은 «보인다»

#  매몰 판정에서 **일부러 뺄 쌍**. prop↔motor 은 이미 전용 검사(check_prop_bell_solid)와
#  전용 예산이 있고, 그 예산은 «설계상 겹침»(나사머리 포스트·상부 커버)을 선언한다.
#  여기서 다시 세면 같은 결함을 두 번 세는 셈이라 **세되 표시만** 한다(제외는 안 한다).
PAIR_NOTE = {("prop", "motor"): "check_prop_bell_solid 가 따로 보는 쌍(전용 예산 있음)"}


def _fingerprint(mesh) -> str:
    """메쉬 지문 — 캐시 키. 정점·면·그룹이 1 비트라도 바뀌면 값이 바뀐다."""
    v = np.ascontiguousarray(np.asarray(mesh.v, float))
    f = np.ascontiguousarray(np.asarray(mesh.f, np.int64))
    g = "|".join(map(str, mesh.g))
    h = hashlib.sha1()
    h.update(v.tobytes()); h.update(f.tobytes()); h.update(g.encode())
    return h.hexdigest()


def _parts(mesh, patch_holes: bool):
    """부품(연결요소) 목록 — **그룹 안에서** 웰딩하고 쪼갠다(`mesh_check` 와 같은 부품 정의).

    왜 그룹 안에서만 웰딩하나: 좌표가 같은 두 **그룹**(x500v2 의 accent↔arm, 감사 m4)을
    통째로 웰딩하면 둘이 한 부품으로 붙어 버려 그 쌍의 매몰면이 **안 보이게** 된다.

    patch_holes : 컨테이너(담는 쪽)가 비수밀이면 **사본에서만** 구멍을 메워 내부판정을 살린다.
      ⚠ 메운 사본은 **contains() 에만** 쓴다. σ 계산·마스크·면적에는 절대 안 들어간다.
      왜 필요한가: mini2 body 는 삼각형 1장이 빠져 있어(감사 I5) 비수밀이고, 메우지 않으면
      **이 부품이 담은 매몰면 전부가 0 으로 보고된다** — 실제로 44.45 % 가 29.71 % 로 보인다.
      «못 봄» 을 «없음» 으로 보고하지 않기 위해 두 판을 다 계산해서 둘 다 싣는다.
    """
    import trimesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    out = []
    for grp in sorted(set(G.tolist())):
        idx = np.where(G == grp)[0]
        f = F[idx]
        used = np.unique(f)
        remap = np.zeros(int(used.max()) + 1, np.int64)
        remap[used] = np.arange(len(used))
        tm = trimesh.Trimesh(vertices=V[used], faces=remap[f], process=True)
        comps = trimesh.graph.connected_components(
            tm.face_adjacency, nodes=np.arange(len(tm.faces)), min_len=1)
        for c in comps:
            sm = tm.submesh([c], append=True, repair=False)
            cont, patched = sm, False
            if patch_holes and not sm.is_watertight:
                cont = sm.copy()
                cont.fill_holes()
                patched = bool(cont.is_watertight)
                if not patched:
                    cont = sm
            out.append(dict(group=grp, face_idx=idx[c], solid=cont,
                            watertight_shipped=bool(sm.is_watertight),
                            watertight_container=bool(cont.is_watertight),
                            hole_patched=patched))
    return out


def _classify(mesh, patch_holes: bool, vertex_test: bool, center_jitter_m: float = 0.0):
    """면별 매몰 분류. 반환 dict 의 배열은 전부 길이 = 면 수.

      buried        : 다른 부품 솔리드 안에 **면 중심**이 든 면
      design_intent : buried 이면서 (그룹 ∈ INTERNAL) 이고 (컨테이너가 **전부** 셸)
      defect        : buried 이면서 design_intent 가 아닌 면  ← **수리 대상**
      ambiguous     : (vertex_test=True 일 때만) 면 중심과 세 꼭짓점의 판정이 **엇갈리는** 면.
                      = 솔리드 경계에 걸친 면. «면 단위로 자르는» 이 수리의 알갱이 굵기다.

    center_jitter_m : **강건성 시험용**. 질의점(면 중심)을 이만큼 무작위로 흔들어도 답이
      그대로인가를 본다. 내부판정은 광선을 쏘아 세는 방식이라 **표면 위의 점**에서 흔들린다 —
      동일평면(x500v2 accent↔arm 은 1 µm 안에서 겹친다)에서 특히 그렇다. 기본 0 = 안 흔듦.
      ⚠ 솔리드는 안 건드리고 **질의점만** 흔든다(형상은 그대로).
    """
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    nF = len(F)
    C = V[F].mean(1)
    if center_jitter_m:
        rng = np.random.default_rng(20260816)      # 고정 씨앗 — 재현 가능
        C = C + rng.normal(0.0, float(center_jitter_m), C.shape)
    area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]],
                                         V[F[:, 2]] - V[F[:, 0]]), axis=1)
    parts = _parts(mesh, patch_holes)

    in_shell = np.zeros(nF, bool)       # 셸 그룹 컨테이너 안
    in_other = np.zeros(nF, bool)       # 셸이 아닌 컨테이너 안
    first_container = np.full(nF, "", object)   # 대안 규칙(«첫 컨테이너가 이긴다») 용
    vert_hit = np.zeros((nF, 3), bool) if vertex_test else None
    pairs: dict[tuple, list] = {}
    blind = []
    for p in parts:
        if not p["watertight_container"]:
            blind.append(dict(group=p["group"], faces=int(len(p["face_idx"])),
                              area_mm2=round(float(area[p["face_idx"]].sum()) * 1e6, 4),
                              why="비수밀 — contains() 가 성립 안 함(구멍을 메워도 안 닫힘)"))
            continue
        #  ⚠ 법선이 안쪽인 솔리드는 contains() 의 «안/밖» 이 **뒤집힌다**. 지금 함대는 전부
        #    바깥 법선이지만(mesh_check 의 inward_normals=0), 조용히 뒤집히면 이 검사가
        #    거짓말을 하므로 여기서 막고 «못 봤다» 고 보고한다.
        if float(p["solid"].volume) <= 0.0:
            blind.append(dict(group=p["group"], faces=int(len(p["face_idx"])),
                              area_mm2=round(float(area[p["face_idx"]].sum()) * 1e6, 4),
                              why="부호부피 ≤ 0 — 법선이 안쪽이라 contains() 가 뒤집힌다"))
            continue
        solid, gj = p["solid"], p["group"]
        lo, hi = solid.bounds
        own = np.zeros(nF, bool)
        own[p["face_idx"]] = True
        cand = np.where((~own) & np.all((C >= lo - 1e-12) & (C <= hi + 1e-12), axis=1))[0]
        if len(cand):
            hit = cand[solid.contains(C[cand])]
            if gj in SHELL_GROUPS:
                in_shell[hit] = True
            else:
                in_other[hit] = True
            new = hit[first_container[hit] == ""]
            first_container[new] = gj
            gs = G[hit]
            for g in sorted(set(gs.tolist())):
                sel = hit[gs == g]
                k = (g, gj)
                if k not in pairs:
                    pairs[k] = [0, 0.0]
                pairs[k][0] += int(len(sel))
                pairs[k][1] += float(area[sel].sum())
        if vertex_test:
            for a in range(3):
                Pv = V[F[:, a]]
                cv = np.where((~own) & np.all((Pv >= lo - 1e-12) & (Pv <= hi + 1e-12), axis=1))[0]
                if len(cv):
                    vert_hit[cv[solid.contains(Pv[cv])], a] = True

    buried = in_shell | in_other
    is_internal = np.isin(G, list(INTERNAL_GROUPS))
    design = buried & is_internal & (~in_other)     # 컨테이너가 **전부** 셸일 때만 설계 의도
    defect = buried & (~design)
    amb = None
    if vertex_test:
        amb = (vert_hit.any(1) | buried) & ~(vert_hit.all(1) & buried)
    return dict(F=F, G=G, area=area, parts=parts, buried=buried, design=design,
                defect=defect, in_shell=in_shell, in_other=in_other,
                first_container=first_container, pairs=pairs, blind=blind,
                ambiguous=amb)


_CACHE: dict = {}


def _cached(mesh, patch_holes: bool, vertex_test: bool, jitter: float = 0.0):
    key = (_fingerprint(mesh), bool(patch_holes), bool(vertex_test), float(jitter))
    if key not in _CACHE:
        if len(_CACHE) > 24:            # 메모리 폭주 방지(부품 솔리드를 들고 있다)
            _CACHE.clear()
        _CACHE[key] = _classify(mesh, patch_holes, vertex_test, jitter)
    return _CACHE[key]


# --------------------------------------------------------------------------- #
#  ① 전수 검사 — 기체별 예산표의 출처
# --------------------------------------------------------------------------- #
def buried_census(mesh, name: str = "mesh", patch_holes: bool = True,
                  vertex_test: bool = False, top_pairs: int = 8,
                  center_jitter_m: float = 0.0) -> dict:
    """전 부품쌍 매몰면 전수. 면적은 **mm²**, 비율은 전체 표면적 대비 **%**.

    ⚠ `pairs` 표는 **포함(inclusive)** 이다 — 한 면이 두 솔리드에 다 들어 있으면 두 쌍에
      각각 센다. 그래서 쌍의 합은 `total` 보다 클 수 있다(합집합이 `total`).
      대안으로 «첫 컨테이너가 이긴다»(그룹 알파벳 순) 분할 표도 `pairs_partition` 에 싣는다 —
      기준선 원장(`outputs/mesh_layer2_baseline_0816.json`)이 쓴 규칙이 이것이다.
    """
    r = _cached(mesh, patch_holes, vertex_test, center_jitter_m)
    area, G = r["area"], r["G"]
    tot = float(area.sum())
    mm2 = 1e6

    def pct(m):
        return round(100.0 * float(area[m].sum()) / tot, 4) if tot > 0 else 0.0

    by_group = {}
    for g in sorted(set(G.tolist())):
        sel = G == g
        ga = float(area[sel].sum())
        by_group[g] = dict(
            faces=int(sel.sum()), area_mm2=round(ga * mm2, 4),
            buried_faces=int((sel & r["buried"]).sum()),
            buried_area_mm2=round(float(area[sel & r["buried"]].sum()) * mm2, 4),
            buried_pct_of_group=round(100.0 * float(area[sel & r["buried"]].sum()) / ga, 4)
            if ga > 0 else 0.0,
            defect_pct_of_mesh=pct(sel & r["defect"]),
            design_pct_of_mesh=pct(sel & r["design"]))

    pr = sorted(r["pairs"].items(), key=lambda kv: -kv[1][1])[:top_pairs]
    pairs = {f"{a}_in_{b}": dict(faces=n, area_mm2=round(ar * mm2, 4),
                                 pct_of_mesh=round(100.0 * ar / tot, 4),
                                 note=PAIR_NOTE.get((a, b), ""))
             for (a, b), (n, ar) in pr}

    #  대안 규칙(기준선 원장이 쓴 것) — 첫 컨테이너가 이기는 분할
    fc = r["first_container"]
    is_int = np.isin(G, list(INTERNAL_GROUPS))
    des_part = is_int & np.isin(fc.astype(str), list(SHELL_GROUPS))
    part_tab = {}
    for i in np.where(r["buried"])[0]:
        k = f"{G[i]}_in_{fc[i]}"
        e = part_tab.setdefault(k, [0, 0.0])
        e[0] += 1
        e[1] += float(area[i])
    part_tab = {k: dict(faces=v[0], area_mm2=round(v[1] * mm2, 4),
                        pct_of_mesh=round(100.0 * v[1] / tot, 4))
                for k, v in sorted(part_tab.items(), key=lambda kv: -kv[1][1])[:top_pairs]}

    out = dict(
        name=name, n_faces=int(len(area)), total_area_mm2=round(tot * mm2, 4),
        n_parts=len(r["parts"]),
        patch_holes=bool(patch_holes),
        buried_pct=pct(r["buried"]), buried_area_mm2=round(float(area[r["buried"]].sum()) * mm2, 4),
        design_intent_pct=pct(r["design"]), defect_pct=pct(r["defect"]),
        defect_area_mm2=round(float(area[r["defect"]].sum()) * mm2, 4),
        blind_containers=r["blind"],
        n_patched_containers=int(sum(1 for p in r["parts"] if p["hole_patched"])),
        by_group=by_group, pairs=pairs, pairs_partition=part_tab,
        design_intent_pct_partition_rule=pct(des_part),
        defect_pct_partition_rule=pct(r["buried"] & ~des_part),
    )
    if r["ambiguous"] is not None:
        out["ambiguous_pct"] = pct(r["ambiguous"])
        out["ambiguous_faces"] = int(r["ambiguous"].sum())
    return out


# --------------------------------------------------------------------------- #
#  ② 수리 손잡이 — PO 적분에서 **뺄 면**을 고른다
# --------------------------------------------------------------------------- #
def buried_face_mask(mesh, kind: str = "defect", patch_holes: bool = True) -> np.ndarray:
    """면별 «매몰인가» 불리언 (True = 매몰).

      kind="defect" : **진짜 결함**만 (설계 의도인 셸 속 내부 금속은 남긴다) ← 수리안
      kind="all"    : 매몰면 **전부** (⚠ 수리안이 아니다 — σ 지배 부품이 사라진다. 참고용)
      kind="design" : 설계 의도만 (감도 분석용)
    """
    r = _cached(mesh, patch_holes, False)
    if kind == "defect":
        return r["defect"].copy()
    if kind == "all":
        return r["buried"].copy()
    if kind == "design":
        return r["design"].copy()
    raise ValueError(f"kind 는 'defect'|'all'|'design' — 받은 값 {kind!r}")


def keep_face_mask(mesh, kind: str = "defect", patch_holes: bool = True) -> np.ndarray:
    """`rcs_po.mesh_to_points(face_mask=…)` 에 그대로 넣을 **남길 면** 마스크."""
    return ~buried_face_mask(mesh, kind=kind, patch_holes=patch_holes)


if __name__ == "__main__":
    import json
    from drones import DRONES, build_drone
    print("=" * 100)
    print("매몰면 전수 — 부품이 다른 부품 **안**에 들어간 면적 (PO 경로에서 곧 이중계상)")
    print("=" * 100)
    print(f"  {'기체':12s} {'면':>7} {'부품':>4} {'총매몰%':>8} {'설계의도%':>9} "
          f"{'⭐진짜결함%':>10} {'결함면적mm²':>12}  {'못본컨테이너':>10}")
    for k, s in DRONES.items():
        c = buried_census(build_drone(s), k)
        print(f"  {k:12s} {c['n_faces']:7d} {c['n_parts']:4d} {c['buried_pct']:8.3f} "
              f"{c['design_intent_pct']:9.3f} {c['defect_pct']:10.3f} "
              f"{c['defect_area_mm2']:12.1f}  {len(c['blind_containers']):10d}")
    print("\n(예산표는 mesh_check.BURIED_FACE_BUDGET_PCT · 원장은 "
          "outputs/mesh_layer2_buried_faces_0816.json)")
