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

  ⑴ 그룹 안 (check_mesh)
     1. watertight   : 부품이 닫힌 껍질인가 (구멍 없음)
     2. 경계 모서리  : 삼각형 하나만 쓰는 모서리 = 구멍의 테두리. **0 이어야 한다**
     3. winding      : 이웃한 면들이 같은 방향으로 감겼는가
     4. 법선 방향    : 바깥을 향하는가 (닫힌 부품의 부호있는 부피 > 0)
     5. 부호부피(원본): trimesh 를 **전혀 안 거치고** 출하 인덱스로 직접 계산한 부피 > 0
     6. 퇴화면       : 절대 잣대(면적) + **상대 잣대(최소 내각)** 둘 다
     7. 그룹 안 겹침 : 같은 그룹의 두 부품이 서로 파묻혀 있는가 (PO 면적 이중계상)
  ⑵ 스펙 대조 (check_dimensions · check_handedness)
     8. 치수         : 프롭 지름·로터 대각·공식 외형을 **DroneSpec 의 수**와 대조
     9. 손대칭성     : 로터별 날 비틀림 방향이 회전방향(dir)과 맞는가 (거울상 기체 탐지)
  ⑶ 그룹 사이 (check_prop_bell · check_prop_bell_solid)
    10. 프롭↔모터 벨 관통 — 원통 근사(빠름) + 솔리드 내부판정(판정 기준)

⭐⭐ 2026-08-16 — **검사기가 자기가 방금 수리한 사본을 검사하고 있었다**(감사 C1).
  `trimesh.split()` 은 trimesh 5.x 에서 `repair=True` 가 **기본**이라, 구멍 뚫린 부품을
  조용히 메운 뒤 «수밀 통과» 를 돌려줬다(합성 대조: 삼각형 1장 뺀 상자가 11면 → 12면·수밀 True).
  이제 **모든 split 호출에 `repair=False` 를 명시**하고, 경계 모서리 수를 결과에 싣는다.
  ⚠ 구별할 것 — **웰딩(process=True)은 유지한다.**
     · 웰딩  = 같은 자리의 중복 «정점» 을 합치는 것. 새 형상을 만들지 않는다.
               우리 geom.Mesh 는 프리미티브마다 정점을 따로 쌓으므로 웰딩 없이는
               멀쩡한 부품도 전부 «비수밀» 로 나온다(감사 m6).
     · 수리(repair=True) = 없는 «삼각형» 을 지어 구멍을 메우는 것. **검사기가 하면 안 된다.**

실행:  python src/mesh_check.py          (DRONES 레지스트리 **전 기종** 전수 검사)
       assert_ok() 는 메쉬 내보내기 경로(`python src/drones.py`)에 게이트로 배선돼 있다.
"""
from __future__ import annotations

import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


#  ── 검사 잣대 ────────────────────────────────────────────────────────────── #
#  ⚠ 아래 «예산» 표들은 전부 **«지금 이만큼이다» 라는 선언**이지 «이만큼이 옳다» 가 아니다.
#    (이 저장소의 기존 규약 — PROP_BELL_* 표와 같은 뜻.) 값은 2026-08-16 전수 실측으로
#    초기화했고, 여유는 실측값의 약 10 % 다. 새로 생기는 결함은 예산을 넘겨 **실패한다.**

SLIVER_MIN_ANGLE_DEG = 0.5      # 이보다 좁은 내각을 가진 삼각형 = 슬리버(상대 잣대, 감사 m2)
DEGENERATE_AREA_M2 = 1e-14      # 절대 잣대(옛 기준). 기체 크기에 따라 뜻이 달라져 상대 잣대를 겸용한다

#  ⑵ 경계 모서리(구멍) 예산 — (기종, 그룹) → 허용 개수. **원칙은 0 이다.**
BOUNDARY_EDGE_BUDGET = {
    "_default": 0,
    #  ↓ 선언된 기존 결함(감사 I5). 2층 수리 대상이라 여기 «지금 상태» 로 박아 둔다.
    #    mini2 body 는 면 수가 7757(홀수)로, **`cadkit.union_group('body')`** 의
    #    nondegenerate_faces() 가 needle 삼각형 1장을 지우면서 경계 모서리 3개짜리 구멍이
    #    남았다(⚠감사 I5 는 이 자리를 `Assembly.add()` 로 적었는데 실측은 union 쪽이다 —
    #    body 로 들어온 파트 10개는 전부 수밀·퇴화면 0 이고, 불리언 합집합 출력에서 생긴다).
    #    구멍 삼각형 면적은 4.95e-06 mm² 라 산란에는 영향이 없고, 진짜 피해는 간접이다 —
    #    is_watertight=False 라 부피·contains() 가 무효가 되어 **내부판정을 쓰는 검사가
    #    이 부품을 조용히 건너뛴다.**
    ("mini2", "body"): 3,
}

#  ⭐ 수리를 켜면 예산도 **같이 조인다** — 안 그러면 «고쳤는데 다시 열려도» 통과한다.
#    `MESH_FIX=i5` 에서는 모든 (기종, 그룹) 의 경계 모서리 예산이 0 이다.
BOUNDARY_EDGE_BUDGET_FIXED = {"_default": 0}


def _boundary_budget(name: str, grp: str) -> int:
    """경계 모서리 예산 — 수리 스위치 상태에 따라 표를 갈아 끼운다."""
    from geom import mesh_fix_enabled
    tbl = BOUNDARY_EDGE_BUDGET_FIXED if mesh_fix_enabled("i5") else BOUNDARY_EDGE_BUDGET
    return int(tbl.get((name, grp), tbl["_default"]))

#  ⑶ 슬리버(최소 내각 < 0.5°) 예산 — 기종 전체 개수. 실측 + 10 % 여유.
#     면적 비중은 0.0001~0.03 % 라 σ 에는 무해하다(감사 m2 가 확인). 감시하는 이유는
#     법선이 수치적으로 불안정한데 PO 조명판정이 n̂·û>0 이기 때문이다.
SLIVER_BUDGET = {
    "_default": 0,
    "mini5pro": 382, "mavic4pro": 261, "matrice4e": 312, "s1000plus": 638,
    "phantom4": 270, "typhoonh480": 508, "x500v2": 420, "phantom3": 339,
    "m350rtk": 347, "mini2": 198,
}
#  ⑶-2 ⭐ 2026-08-16 — **수리를 켰을 때만** 쓰는 슬리버 예산 (감사 §⑤ 2층 i4).
#     불리언 합집합은 두 껍질이 만나는 **교차곡선을 따라 얇은 삼각형을 남긴다** — CSG 의
#     성질이지 새로 생긴 결함이 아니다. 그래도 «수리판은 예산을 밑돌면 된다» 는 원칙의
#     예외이므로 **여기 선언**한다(값·근거를 안 적고 통과시키지 않는다).
#     실측(2026-08-16, i4 켬 ↔ 끔) — 셸형 7기체 + x500v2:
#       mavic4pro 239→239 · phantom3 301→301 · phantom4 234→234 (증가 0)
#       matrice4e 239→261 · mini5pro 235→285 · **mini2 185→215** · **typhoonh480 461→508**
#       (m4 · x500v2 381→389)
#     완전 매몰 기체(mavic4pro·phantom3)가 0 인 이유는 그쪽이 불리언을 아예 안 태우기 때문이다.
#     늘어난 삼각형은 전부 body 씨접합이고 mini2 기준 **면적 합 0.73 mm²** = 표면적의 0.0008 %.
#     그 대가로 없애는 이중계상은 8,474 mm² 다 — **11,600 배**.
#     ⚠ 기존 예산을 넘는(또는 여유가 0인) 둘만 선언한다. 나머지는 기존 예산 안이다.
#     ⚠ 0.1 mm 정점 용접으로 씨접합 슬리버를 78 → 32 장까지 줄일 수는 있으나(실측), 그건 씨접합
#       **밖의** 정점까지 움직이므로 이 라운드에서는 안 쓴다 — 원장에 측정치만 남긴다.
SLIVER_BUDGET_MESH_FIX = {
    ("i4", "mini2"): 240,          # 실측 215 + 약 10 %  (기존 예산 198)
    ("i4", "typhoonh480"): 560,    # 실측 508 + 약 10 %  (기존 예산 508 — 여유가 0이었다)
}

#  ⑷ **그룹 안** 부품 겹침 예산 [%] — (기종, 그룹) → 그 그룹 표면적 중 다른 부품 솔리드
#     안에 파묻힌 비율. `build_frame_cad` 의 불리언 union 목록에 없는 그룹은 겹치면
#     내부 면이 그대로 남아 **PO 가 면적을 이중계상**한다(PO 는 가림을 안 본다).
#     ⭐ 2026-08-16 신규 발견 — 셸형 공용 경로의 'battery' 그룹에서 배터리 팩 상자와
#        구조판 상자가 실제로 파고들어 있다(48~50 %). `drone_cad.py` INTERNALS 주석은
#        «battery·pcb 는 union 목록에 없으니 서로 겹치지 않게 놓는다» 고 적는데,
#        기종별 실측표를 받은 matrice4e·phantom3 만 그 규칙을 지키고 있다(겹침 0 %).
#        ⇒ 2층 수리 대상(`MESH_FIX=battery`). 아래 55 % 는 **수리 전 상태의 선언**이다.
GROUP_OVERLAP_BUDGET_PCT = {
    "_default": 0.1,
    ("mini2", "battery"): 55.0,
    ("mini5pro", "battery"): 55.0,
    ("mavic4pro", "battery"): 55.0,
    ("phantom4", "battery"): 55.0,
}

#  ⭐ 수리를 켜면 예산도 **같이 조인다** — 안 그러면 «고쳤는데 다시 겹쳐도» 통과한다.
#    `MESH_FIX=battery` 에서 'battery' 그룹의 겹침 예산은 기본값(0.1 %)이다. 실측은 0.0 %.
GROUP_OVERLAP_BUDGET_FIXED = {"_default": 0.1}


def _overlap_budget(name: str, grp: str) -> float:
    """그룹 안 겹침 예산 [%] — 수리 스위치 상태에 따라 표를 갈아 끼운다."""
    from geom import mesh_fix_enabled
    tbl = (GROUP_OVERLAP_BUDGET_FIXED
           if (grp == "battery" and mesh_fix_enabled("battery")) else GROUP_OVERLAP_BUDGET_PCT)
    return float(tbl.get((name, grp), tbl["_default"]))


#  ⑸ 치수 대조 허용오차 [%] — 메쉬에서 잰 값 ↔ DroneSpec 의 수
DIM_TOL_PCT = {
    "prop_dia": 1.0,        # 실측 전 10기체 −0.000 % (스윕디스크 정규화가 정확히 작동)
    "envelope": 1.0,        # 실측 전 10기체 0.0 % (frame_fit_scale 이 외형을 맞춘다)
    "diagonal": 3.0,        # ⭐ 2026-08-16 갱신: 실측 −0.14~+0.02 % (예외 mini5pro 는 아래 표).
                            #   최대였던 phantom4 +1.98 % 가 **0.000 %** 로 내려왔다 —
                            #   L/W 외형 강제를 풀어 축간거리를 공표 350 mm 로 되돌린 결과다
                            #   (감사 B6 · outputs/mesh_apply_caps_envelope_0816.json).
                            #   ⚠ 문턱값 3.0 은 **안 내렸다**: 병행 라운드들이 형상 상수를
                            #     고치는 중이라 지금 조이면 남의 작업을 게이트로 막게 된다.
}
#  ↓ 대각선만 기종별 예외가 있다 — spec note 에 이미 선언된 값들.
DIM_DIAGONAL_TOL_PCT = {
    #  mini5pro: spec note 가 «diagonal_mm 275 는 로터 위치를 정하지 않는다» 고 선언한다.
    "mini5pro": 12.0,       # 실측 −9.46 %
}

#  ⑹ 손대칭성 — 날 비틀림 방향 지표의 최소 크기. 이보다 작으면 «날이 비틀리지 않았다» 는 뜻이라
#     부호를 믿을 수 없다. 실측 |h| = 0.16~0.29 라 0.05 는 3배 이상 여유다.
HANDEDNESS_MIN_ABS = 0.05


def _tm(v, f):
    """(정점, 면) → trimesh. **웰딩만 하고 수리는 하지 않는다**(파일 머리말 참조)."""
    import trimesh
    return trimesh.Trimesh(vertices=np.asarray(v, float),
                           faces=np.asarray(f, int), process=True)


def _split(tm):
    """연결요소 분리 — ⭐`repair=False` 를 **반드시** 명시한다(감사 C1).
    trimesh 5.x 의 `split` 은 repair 기본값이 True 라, 그냥 부르면 구멍을 메운 사본을 돌려준다."""
    return tm.split(only_watertight=False, repair=False)


def _edge_defects(tm):
    """`is_watertight` 를 **두 원인으로 쪼갠다**.
      · 경계 모서리   = 삼각형 하나만 쓰는 모서리 → 구멍의 테두리
      · 비다양체 모서리 = 삼각형 셋 이상이 쓰는 모서리 → 껍질이 겹쳐 붙음
    trimesh 의 `is_watertight` 는 «모든 모서리가 정확히 두 번» 이라 이 둘을 합쳐 참/거짓
    하나로 뭉갠다. 쪼개 놓으면 «구멍 3개» 를 예산으로 선언하면서 **새로 생긴 겹침은
    그대로 실패**시킬 수 있다."""
    import trimesh
    e = tm.edges_sorted
    n_b = int(len(trimesh.grouping.group_rows(e, require_count=1)))
    n_2 = int(len(trimesh.grouping.group_rows(e, require_count=2)))
    n_all = int(len(trimesh.grouping.group_rows(e)))
    return n_b, int(n_all - n_b - n_2)


def _min_angles_deg(V, F) -> np.ndarray:
    """삼각형별 **최소 내각**[deg] — 슬리버의 상대 잣대. 절대 면적 잣대는 기체 크기에 따라
    뜻이 달라져서(m350rtk 는 mini2 의 20배) 같은 1e-14 m² 가 전혀 다른 엄격도가 된다."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]

    def ang(P, Q, R):
        u, w = Q - P, R - P
        nu = np.linalg.norm(u, axis=1)
        nw = np.linalg.norm(w, axis=1)
        d = np.clip((u * w).sum(1) / np.maximum(nu * nw, 1e-300), -1.0, 1.0)
        return np.degrees(np.arccos(d))

    return np.minimum(np.minimum(ang(A, B, C), ang(B, C, A)), ang(C, A, B))


def _raw_components(F, n_vert):
    """**출하 인덱스 그대로**의 연결요소 라벨 — trimesh 를 안 거친다(웰딩도 수리도 없음).
    geom.Mesh 는 프리미티브마다 정점 블록을 따로 쌓으므로 «인덱스 연결» = «부품» 이다."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    rows = np.repeat(np.arange(len(F)), 3)
    M = coo_matrix((np.ones(len(rows), np.int8), (rows, F.reshape(-1))),
                   shape=(len(F), n_vert)).tocsr()
    n, lab = connected_components(M @ M.T, directed=False)
    return n, lab


def _raw_signed_volumes_mm3(V, F):
    """수리 없는 **손계산 부호부피**[mm³] — 감사 §⑤ 0층 4번.
    발산정리로 Σ a·(b×c)/6. 법선이 안쪽을 보면 부호가 음수가 된다. 이 축은 지금 깨끗하고
    (2026-07-01 안쪽법선 수정이 살아 있다) C1 과 **무관하게** 지킬 수 있어서 게이트에 넣는다."""
    used = np.unique(F)
    remap = np.zeros(int(used.max()) + 1, np.int64)
    remap[used] = np.arange(len(used))
    ff = remap[F]
    Vv = np.asarray(V, float)[used]
    n, lab = _raw_components(ff, len(used))
    a, b, c = Vv[ff[:, 0]], Vv[ff[:, 1]], Vv[ff[:, 2]]
    d = np.einsum("ij,ij->i", a, np.cross(b, c)) / 6.0
    return np.bincount(lab, weights=d, minlength=n) * 1e9      # m³ → mm³


def _group_overlap_pct(comps) -> float:
    """**그룹 안** 부품 겹침 — 한 부품의 삼각형 중심이 같은 그룹의 다른 (수밀) 부품 솔리드
    **안**에 드는 면적의 비율 [%]. PO 는 가림을 안 보므로 이 면적은 그대로 이중계상된다.

    ⚠ 담는 쪽(cj)이 수밀이 아니면 `contains()` 가 성립하지 않아 **그 부품은 담는 쪽에서 뺀다.**
      즉 이 수는 «겹침의 하한» 이다 — «못 봄» 이 0 으로 보고될 수 있다는 뜻인데, 그 조건
      (비수밀 부품의 존재)은 같은 그룹의 `boundary_edges` 가 따로 드러내므로 정보가 사라지진
      않는다. 감사 부록 A 의 교훈(«수밀 필터를 건 검사는 못 봄을 0 으로 보고한다»)을 여기 적어 둔다."""
    if len(comps) < 2:
        return 0.0
    cen = [c.triangles_center for c in comps]
    ar = [c.area_faces for c in comps]
    tot = float(sum(float(a.sum()) for a in ar))
    if tot <= 0:
        return 0.0
    buried = 0.0
    for i, _ in enumerate(comps):
        for j, cj in enumerate(comps):
            if i == j or not cj.is_watertight:
                continue
            lo, hi = cj.bounds
            sel = np.all((cen[i] >= lo - 1e-12) & (cen[i] <= hi + 1e-12), axis=1)
            if not sel.any():
                continue
            hit = cj.contains(cen[i][sel])
            buried += float(ar[i][np.where(sel)[0][hit]].sum())
    return round(100.0 * buried / tot, 4)


def check_mesh(mesh, name="mesh") -> dict:
    """geom.Mesh → 부품별 검진 결과. 그룹(부위) 단위로 쪼개서 본다.

    name 은 예산표(BOUNDARY_EDGE_BUDGET·GROUP_OVERLAP_BUDGET_PCT·SLIVER_BUDGET)의 키다 —
    레지스트리에 없는 이름(임시·합성 메쉬)이면 `_default`(=결함 0 허용)가 걸린다."""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g)
    ang_all = _min_angles_deg(V, F)
    groups = {}
    n_sliver_total = 0
    for grp in sorted(set(G.tolist())):
        sub = G == grp
        f = F[sub]
        used = np.unique(f)
        remap = {int(o): i for i, o in enumerate(used)}
        f_local = np.vectorize(remap.get)(f)
        tm = _tm(V[used], f_local)
        comps = _split(tm)
        n_wt = sum(1 for c in comps if c.is_watertight)
        n_inward = sum(1 for c in comps if c.is_watertight and c.volume < 0)
        n_badwind = sum(1 for c in comps if not c.is_winding_consistent)
        n_degen = int((tm.area_faces < DEGENERATE_AREA_M2).sum())
        n_bedge, n_nonmani = _edge_defects(tm)
        n_sliver = int((ang_all[sub] < SLIVER_MIN_ANGLE_DEG).sum())
        n_sliver_total += n_sliver
        raw_vol = _raw_signed_volumes_mm3(V, f)
        n_rawneg = int((raw_vol <= 0.0).sum())
        overlap = _group_overlap_pct(comps)
        be_budget = _boundary_budget(name, grp)
        ov_budget = _overlap_budget(name, grp)
        groups[grp] = dict(
            n_faces=int(len(f)), n_parts=len(comps),
            watertight=f"{n_wt}/{len(comps)}",
            inward_normals=n_inward, bad_winding=n_badwind, degenerate=n_degen,
            #  ↓ 2026-08-16 추가
            boundary_edges=n_bedge, boundary_edge_budget=be_budget,
            nonmanifold_edges=n_nonmani,
            raw_min_signed_volume_mm3=round(float(raw_vol.min()), 4),
            raw_negative_parts=n_rawneg,
            slivers=n_sliver, min_angle_deg=round(float(ang_all[sub].min()), 5),
            overlap_pct=overlap, overlap_budget_pct=ov_budget,
            #  ⚠ 판정에서 `is_watertight` 자체를 쓰지 않는다 — 그 참/거짓은 «구멍» 과
            #    «겹침» 을 뭉쳐 놓아서 선언된 구멍(mini2 body 3개)을 예산으로 통과시키면
            #    새로 생긴 겹침까지 같이 통과해 버린다. 두 원인을 따로 판정한다.
            ok=(n_inward == 0 and n_badwind == 0 and n_degen == 0
                and n_bedge <= be_budget and n_nonmani == 0
                and n_rawneg == 0 and overlap <= ov_budget),
        )
    sl_budget = SLIVER_BUDGET.get(name, SLIVER_BUDGET["_default"])
    #  ⭐ 수리가 켜져 있으면 그 수리용으로 **선언된** 예산을 쓴다(위 SLIVER_BUDGET_MESH_FIX).
    #    스위치가 꺼져 있으면 이 줄들은 아무 일도 안 한다 → 기존 판정과 비트동일.
    from geom import mesh_fix_set
    for _fid in mesh_fix_set():
        _v = SLIVER_BUDGET_MESH_FIX.get((_fid, name))
        if _v is not None:
            sl_budget = max(sl_budget, _v)
    #  ⚠ 슬리버는 **`ok` 에 넣지 않는다** — 일부러 그렇다.
    #    `check_mesh(...)["ok"]` 는 예전부터 «부품 무결성» 의 뜻으로 쓰여 왔고, 실제로
    #    `benchmark/audit_m350rtk_mesh.py` 는 그 값을 `watertight_all_parts` 라는 이름으로
    #    원장에 싣는다. 슬리버는 기체 전체를 보는 **다른 층의 잣대**(상대 잣대·기종별 예산)라
    #    그 자리에 섞으면 뜻이 흐려지고, 미등록 이름으로 부른 기존 호출부가 조용히 뒤집힌다.
    #    게이트(assert_ok)와 check_all 은 `sliver_ok` 를 따로 확인한다.
    return dict(name=name, groups=groups,
                slivers=n_sliver_total, sliver_budget=sl_budget,
                sliver_ok=bool(n_sliver_total <= sl_budget),
                ok=all(g["ok"] for g in groups.values()))


def report(res: dict) -> str:
    lines = [f"  {'그룹':10s} {'면':>6} {'부품':>5} {'watertight':>11} {'법선안쪽':>8} "
             f"{'winding깨짐':>11} {'퇴화면':>6} {'경계모서리':>10} {'비다양체':>8} "
             f"{'슬리버':>6} {'그룹내겹침%':>11}  판정"]
    for grp, g in res["groups"].items():
        be = f"{g['boundary_edges']}/{g['boundary_edge_budget']}"
        ov = f"{g['overlap_pct']:.2f}/{g['overlap_budget_pct']:g}"
        lines.append(f"  {grp:10s} {g['n_faces']:6d} {g['n_parts']:5d} {g['watertight']:>11s} "
                     f"{g['inward_normals']:8d} {g['bad_winding']:11d} {g['degenerate']:6d}"
                     f" {be:>10s} {g.get('nonmanifold_edges', 0):8d}"
                     f" {g['slivers']:6d} {ov:>11s}"
                     f"  {'✅' if g['ok'] else '❌'}")
    if "slivers" in res:
        lines.append(f"  슬리버(최소내각<{SLIVER_MIN_ANGLE_DEG}°) 합계 {res['slivers']} "
                     f"(예산 {res['sliver_budget']})  {'✅' if res['sliver_ok'] else '❌'}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  ⭐ 2026-08-16 — 스펙 대조 검사 (감사 I6). 위의 검사들은 전부 «메쉬가 스스로 앞뒤가
#     맞는가» 만 본다. 그래서 **단위를 1000 배 틀린 메쉬**도, **좌우가 뒤집힌 기체**도
#     통과했다(감사 I6: 나쁜 메쉬 5종을 지어 시험했더니 5/5 통과). 이 두 검사는 메쉬를
#     **바깥의 수(DroneSpec)** 와 대조해서 그 구멍을 막는다.
# --------------------------------------------------------------------------- #
def _rotor_clusters(spec, V_mm, F_prop):
    """프롭 삼각형을 로터별로 나눈다 — 삼각형 중심에서 가장 가까운 로터 축.
    반환: (로터별 면 인덱스 리스트, 로터 정보 리스트)."""
    from drones import rotor_layout
    rl = rotor_layout(spec)
    ctr = np.asarray([r["center"] for r in rl], float) * 1000.0
    C = V_mm[F_prop].mean(1)
    idx = np.linalg.norm(C[:, None, :2] - ctr[None, :, :2], axis=2).argmin(1)
    return [np.where(idx == i)[0] for i in range(len(rl))], rl, ctr


def check_dimensions(spec, mesh=None, verbose=False) -> dict:
    """**치수 검사** — 메쉬에서 잰 프롭 지름·로터 대각·외형을 DroneSpec 의 수와 대조한다.
    이 검사가 없으면 단위를 1000 배 틀린 메쉬가 모든 위상 검사를 통과한다(감사 I6 D3)."""
    from drones import build_drone
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    if not (G == "prop").any():
        return dict(key=spec.key, checked=False, ok=True, reason="prop 그룹 없음")
    Fp = F[G == "prop"]
    sel_list, rl, _ = _rotor_clusters(spec, V, Fp)

    dia, errs = [], []
    for sel in sel_list:
        if not len(sel):
            continue
        P = V[Fp[sel]].reshape(-1, 3)
        cx, cy = float(P[:, 0].mean()), float(P[:, 1].mean())
        dia.append(2.0 * float(np.hypot(P[:, 0] - cx, P[:, 1] - cy).max()))
        errs.append((cx, cy))
    dia_mean = float(np.mean(dia)) if dia else 0.0
    e_prop = 100.0 * (dia_mean / spec.prop_dia_mm - 1.0) if spec.prop_dia_mm else 0.0

    #  로터 대각 = 2 × (로터 중심의 평균 반경). 프롭 군집의 xy 무게중심이 로터 축이다
    #  (2날 프롭은 허브 기준 대칭이라 무게중심이 축 위에 온다).
    ctr_meas = np.asarray(errs, float)
    diag_meas = 2.0 * float(np.linalg.norm(ctr_meas, axis=1).mean()) if len(ctr_meas) else 0.0
    e_diag = 100.0 * (diag_meas / spec.diagonal_mm - 1.0) if spec.diagonal_mm else 0.0

    #  외형 — 공식 치수가 «프롭 포함» 이면 전체 드론을, 아니면 프레임(프롭 제외)을 견준다.
    #  (frame_envelope_mm 과 같은 규약)
    full = V.max(0) - V.min(0)
    nonp = np.unique(F[G != "prop"])
    frame = (V[nonp].max(0) - V[nonp].min(0)) if len(nonp) else full
    cmp_mm = full if bool(getattr(spec, "env_props_included", False)) else frame
    env = spec.envelope_mm
    e_env = [None if (env is None or env[i] is None) else
             round(100.0 * (float(cmp_mm[i]) / float(env[i]) - 1.0), 4) for i in range(3)]

    tol_diag = DIM_DIAGONAL_TOL_PCT.get(spec.key, DIM_TOL_PCT["diagonal"])
    bad = []
    if abs(e_prop) > DIM_TOL_PCT["prop_dia"]:
        bad.append(f"prop_dia {dia_mean:.2f} mm ↔ spec {spec.prop_dia_mm} ({e_prop:+.2f} %)")
    if abs(e_diag) > tol_diag:
        bad.append(f"diagonal {diag_meas:.2f} mm ↔ spec {spec.diagonal_mm} "
                   f"({e_diag:+.2f} %, 허용 {tol_diag} %)")
    for i, e in enumerate(e_env):
        if e is not None and abs(e) > DIM_TOL_PCT["envelope"]:
            bad.append(f"envelope[{'LWH'[i]}] {cmp_mm[i]:.2f} mm ↔ 공식 {env[i]} ({e:+.2f} %)")

    res = dict(key=spec.key, checked=True, prop_dia_mm=round(dia_mean, 3),
               prop_dia_err_pct=round(e_prop, 4), diagonal_mm=round(diag_meas, 3),
               diagonal_err_pct=round(e_diag, 4), diagonal_tol_pct=tol_diag,
               envelope_err_pct=e_env,
               envelope_includes_props=bool(getattr(spec, "env_props_included", False)),
               failures=bad, ok=not bad)
    if verbose:
        print(f"  치수: 프롭지름 {dia_mean:.2f} mm ({e_prop:+.3f} %) · 대각 {diag_meas:.1f} mm "
              f"({e_diag:+.2f} %) · 외형 {e_env}  {'✅' if res['ok'] else '❌'}")
    return res


def _twist_chirality(V, F, cx, cy) -> float:
    """날 비틀림의 **손대칭성 지표**. 윗면(n_z>0) 삼각형만 골라 법선의 «접선방향 성분» 을
    면적가중 평균한다. 값의 부호가 곧 날이 어느 쪽으로 비틀렸는가다.

    왜 윗면만 쓰나: 닫힌 껍질에서는 ∮(r×n)dS ≡ 0 이라 전면을 다 더하면 **항등적으로 0** 이
    나온다(실측으로 확인: 1e-21 수준). 윗면만 고르면 그 상쇄가 깨진다.
    왜 부호가 뒤집히나: y→−y 거울에서 n → M n 이고 접선 단위벡터는 φ̂ → −M φ̂ 이므로
    n·φ̂ 의 부호가 뒤집힌다. 실측 |값| = 0.16~0.29 라 잡음이 아니다."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(B - A, C - A)
    a2 = np.linalg.norm(n, axis=1)
    ok = a2 > 0
    if not ok.any():
        return 0.0
    nh = n[ok] / a2[ok][:, None]
    area = 0.5 * a2[ok]
    c = ((A + B + C) / 3.0)[ok]
    x, y = c[:, 0] - cx, c[:, 1] - cy
    rho = np.hypot(x, y)
    m = (rho > 1e-12) & (nh[:, 2] > 0.0)
    if not m.any():
        return 0.0
    tang = nh[m, 0] * (-y[m] / rho[m]) + nh[m, 1] * (x[m] / rho[m])
    return float((area[m] * tang).sum() / area[m].sum())


def check_handedness(spec, mesh=None, verbose=False) -> dict:
    """**손대칭성 검사** — 로터마다 날의 비틀림 방향이 그 로터의 회전방향(dir)과 맞는가.

    왜 필요한가: 좌우를 통째로 뒤집은(거울상) 기체는 위상·치수 검사를 **전부 통과한다**
    (감사 I6 D4). 그런데 거울상 기체는 프롭의 회전방향과 피치 부호가 물리적으로 반대라
    마이크로도플러의 부호와 추력 방향이 뒤집힌다.

    기준은 이 스펙 자신의 `build_propeller(spec)`(=CCW 기준 형상)에서 뽑는다. 즉 «규약이
    무엇인가» 를 코드에 박지 않고 **매번 같은 출처에서 다시 읽는다**."""
    from drones import build_drone, build_propeller
    m = mesh if mesh is not None else build_drone(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, np.int64)
    G = np.asarray(m.g)
    if not (G == "prop").any():
        return dict(key=spec.key, checked=False, ok=True, reason="prop 그룹 없음")
    p = build_propeller(spec)
    h_ref = _twist_chirality(np.asarray(p.v, float) * 1000.0,
                             np.asarray(p.f, np.int64), 0.0, 0.0)
    if abs(h_ref) < HANDEDNESS_MIN_ABS:
        return dict(key=spec.key, checked=False, ok=True,
                    reason=f"기준 프롭의 비틀림이 너무 작다(|h_ref|={abs(h_ref):.4f})")
    Fp = F[G == "prop"]
    sel_list, rl, ctr = _rotor_clusters(spec, V, Fp)
    rows, bad = [], []
    for i, (sel, r) in enumerate(zip(sel_list, rl)):
        if not len(sel):
            continue
        h = _twist_chirality(V, Fp[sel], ctr[i, 0], ctr[i, 1])
        want = float(np.sign(h_ref) * r["dir"])       # dir=+1 → 기준 형상, dir=−1 → 거울상
        good = (abs(h) >= HANDEDNESS_MIN_ABS) and (np.sign(h) == want)
        rows.append(dict(rotor=i, dir=int(r["dir"]), h=round(h, 5),
                         expect_sign=int(want), ok=bool(good)))
        if not good:
            bad.append(f"rotor{i}(dir {r['dir']:+d}) h={h:+.4f}, 기대부호 {want:+.0f}")
    res = dict(key=spec.key, checked=True, h_ref=round(h_ref, 5),
               per_rotor=rows, failures=bad, ok=not bad)
    if verbose:
        print(f"  손대칭성: h_ref {h_ref:+.4f} · 로터 {len(rows)}개  "
              f"{'✅' if res['ok'] else '❌'}" + (f"  {bad}" if bad else ""))
    return res


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
    PO 이중계상 면적의 직접 측정. 근사 없음(trimesh contains).

    ⚠ 여기서도 split 은 `repair=False` 다(감사 C1). 수밀이 아닌 벨 부품은 contains() 를
    쓸 수 없으므로 **세지 않고 개수만 보고한다** — «못 봄» 을 0 으로 보고하지 않기 위해서다."""
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
    comps = _split(tm)
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


#  ⭐⭐ 2026-08-16 — **매몰면 전수 검사**(감사 I3). 위의 그룹 사이 검사는 prop↔motor **한 쌍**
#     뿐이었다. 나머지 쌍은 검사도 예산도 없었고, 실제로 표면적의 8.0~44.4 % 가 다른 부품
#     **안**에 들어 있다. PO 는 가림을 안 보므로(rcs_po.py 46-53행 자기선언) 그 면적은 그대로
#     **이중계상**된다 — 주력 표적에서 σ 방위평균 +2.3(mavic4pro) / +4.0 dB(mini5pro).
#     엔진은 `mesh_buried.buried_census` 이고, 여기서는 **예산으로 감시**만 한다.
#
#  ⚠ 무엇을 예산에 거는가 — **«진짜 결함» 비율**이다(총 매몰이 아니다).
#     매몰면은 두 종류다(정본 설명은 mesh_buried 머리말):
#       · 설계 의도 = battery·pcb·fc 가 셸(body/canopy) **안**에 있는 것. 반투명 셸을 통과해
#         내부 금속이 보이는 효과를 그렇게 1차 근사하기로 한 것이므로 **결함이 아니다**.
#       · 진짜 결함 = 그 밖의 전부. canopy 가 body 안에, camera 가 body 안에, battery 끼리 겹침 …
#     아래 값은 2026-08-16 **출하 상태의 실측 + 약 10 % 여유**다. «이만큼이 옳다» 가 아니라
#     «지금 이만큼이다» 라는 선언이며(PROP_BELL_* 표와 같은 규약), 새로 생기는 매몰은 예산을
#     넘겨 **실패**한다. 수리(`MESH_FIX=battery` 등)를 켜면 값이 내려가므로 그대로 통과한다.
#  ⚠ 아래 «실측» 은 **2026-08-16 23:46(2층 수리 전) 출하 메쉬**에서 잰 값이다. 같은 날
#    다른 수리자들이 형상을 고치면서 기본 메쉬가 움직였고(그때는 6/10 기체), 그 뒤 실측은
#    ±0.5 pp 안에서 달라진다 — 예산은 여전히 넉넉하다. 어느 형상에서 잰 수인지는 원장
#    `outputs/mesh_layer2_buried_faces_0816.json` 의 `census[*].⭐mesh_state` 지문이 못 박는다.
#    ⇒ 2층 수리가 다 끝나면 `benchmark/adv_mesh_buried_faces_0816.py` 를 다시 돌려 이 표를 갱신할 것.
BURIED_FACE_BUDGET_PCT = {
    #  _default 를 0.1 로 두는 이유: 새 기체가 들어오면 **선언 없이는 통과 못 하게** 한다.
    "_default": 0.1,
    "mini2": 37.7,        # 실측 34.273
    "mini5pro": 36.2,     # 실측 32.920   ⭐주력 표적
    "phantom4": 33.6,     # 실측 30.503
    "mavic4pro": 32.7,    # 실측 29.741   ⭐주력 표적
    "matrice4e": 20.6,    # 실측 18.674
    "x500v2": 20.0,       # 실측 18.139
    "typhoonh480": 15.4,  # 실측 13.920
    "m350rtk": 9.8,       # 실측 8.820
    "phantom3": 9.2,      # 실측 8.273
    "s1000plus": 7.6,     # 실측 6.891
}


def check_buried_faces(spec, mesh=None, verbose=False) -> dict:
    """**매몰면 전수** — 부품이 다른 부품 솔리드 안에 든 면적을 전 그룹쌍에서 잰다.

    판정은 «진짜 결함» 비율 ≤ BURIED_FACE_BUDGET_PCT. 총 매몰·설계 의도·못 본 컨테이너
    개수도 같이 싣는다(«못 봄» 을 0 으로 보고하지 않기 위해서다).
    ⚠ 이 검사는 **PO 경로의 예산**이다. 기본 엔진 SBR 은 first-hit 이라 이 오차가 구조적으로 0."""
    from drones import build_drone
    from mesh_buried import buried_census
    m = mesh if mesh is not None else build_drone(spec)
    c = buried_census(m, spec.key)
    lim = BURIED_FACE_BUDGET_PCT.get(spec.key, BURIED_FACE_BUDGET_PCT["_default"])
    res = dict(key=spec.key, checked=True, buried_pct=c["buried_pct"],
               design_intent_pct=c["design_intent_pct"], defect_pct=c["defect_pct"],
               defect_area_mm2=c["defect_area_mm2"], budget_pct=lim,
               blind_containers=len(c["blind_containers"]),
               patched_containers=c["n_patched_containers"],
               top_pairs=list(c["pairs"])[:3],
               ok=bool(c["defect_pct"] <= lim))
    if verbose:
        print(f"  매몰면(전 부품쌍): 총 {c['buried_pct']:.2f} % = 설계의도 "
              f"{c['design_intent_pct']:.2f} % + ⭐진짜결함 {c['defect_pct']:.2f} % "
              f"(예산 {lim} %) · 못 본 컨테이너 {len(c['blind_containers'])}개"
              f"  {'✅' if res['ok'] else '❌'}")
    return res


def check_all(verbose=True, mesh_fix=None) -> dict:
    """DRONES 레지스트리 **전 기종** 전수 검사(기종 수는 len(DRONES)).
    검사 5층: ① 부품별 수밀·경계모서리·winding·법선(부호부피 2종)·퇴화면·슬리버·
                그룹내 겹침 (check_mesh)
             ② 치수 대조 — 프롭 지름·로터 대각·공식 외형 vs DroneSpec (check_dimensions)
             ③ 손대칭성 — 날 비틀림 방향 vs 로터 회전방향 (check_handedness)
             ④ 프롭↔벨 원통 근사 관통(check_prop_bell — 빠른 회귀 감지)
             ⑤ 프롭↔벨 솔리드 내부판정(check_prop_bell_solid — 이중계상 면적의 판정 기준)

    mesh_fix : ⭐선택 메쉬 수리 스위치(기본 None = 끔 = 출하 메쉬). 켜면 **수리된 메쉬**를
        검사한다 — 「고치고 나서도 검사기를 통과하는가」를 같은 잣대로 확인하는 통로다.
        토큰은 `drone_cad.MESH_FIX_TOKENS`. ⚠예산표(BOUNDARY_EDGE_BUDGET·
        GROUP_OVERLAP_BUDGET_PCT 등)는 **출하 상태의 선언**이므로 수리판은 예산을 밑돌면 된다."""
    from drones import DRONES, build_drone
    out = {}
    for k, s in DRONES.items():
        m = build_drone(s, mesh_fix=mesh_fix)
        r = check_mesh(m, k)
        dim = check_dimensions(s, mesh=m)
        hnd = check_handedness(s, mesh=m)
        pb = check_prop_bell(s)
        ps = check_prop_bell_solid(s, mesh=m)
        bf = check_buried_faces(s, mesh=m)
        r["dimensions"] = dim
        r["handedness"] = hnd
        r["prop_bell"] = pb
        r["prop_bell_solid"] = ps
        r["buried_faces"] = bf
        r["ok"] = bool(r["ok"] and r.get("sliver_ok", True) and dim["ok"] and hnd["ok"]
                       and pb["ok"] and ps["ok"] and bf["ok"])
        out[k] = r
        if verbose:
            print(f"\n[{k}]  {'✅ 통과' if r['ok'] else '❌ 결함'}")
            print(report(r))
            check_dimensions(s, mesh=m, verbose=True)
            check_handedness(s, mesh=m, verbose=True)
            print(f"  프롭↔벨 관통(원통): 깊이 {pb.get('max_depth_mm', 0)} mm "
                  f"(예산 {pb.get('budget_mm', '-')}) · 삼각형 {pb.get('tris', 0)} · "
                  f"면적 {pb.get('area_mm2', 0)} mm² ({pb.get('area_pct', 0)} %)"
                  f"  {'✅' if pb['ok'] else '❌'}")
            print(f"  프롭↔벨 관통(솔리드): 삼각형 {ps.get('tris', 0)} · "
                  f"면적 {ps.get('area_mm2', 0)} mm² ({ps.get('area_pct', 0)} %, "
                  f"예산 {ps.get('budget_pct', '-')} %)  {'✅' if ps['ok'] else '❌'}")
            check_buried_faces(s, mesh=m, verbose=True)
    return out


def assert_ok(mesh_fix=None):
    """빌드 파이프라인용 — 결함이 있으면 예외를 던진다(회귀 방지).

    배선 위치: `python src/drones.py`(메쉬 내보내기 경로)가 OBJ 를 쓰기 **전에** 부른다.
    ⚠ 인메모리로 `build_drone()` 을 직접 부르는 경로는 이 게이트를 거치지 않는다.
    mesh_fix : check_all 과 같은 뜻(기본 None = 출하 메쉬)."""
    res = check_all(verbose=False, mesh_fix=mesh_fix)
    bad = {}
    for k, r in res.items():
        if r["ok"]:
            continue
        why = [g for g, v in r["groups"].items() if not v["ok"]]
        if not r.get("sliver_ok", True):
            why.append(f"슬리버 {r['slivers']} > {r['sliver_budget']}")
        why += r["dimensions"].get("failures", [])
        why += r["handedness"].get("failures", [])
        if not r["prop_bell"]["ok"]:
            why.append(f"prop↔bell(cyl) {r['prop_bell']['max_depth_mm']} mm > "
                       f"{r['prop_bell']['budget_mm']} mm")
        if not r["prop_bell_solid"]["ok"]:
            why.append(f"prop↔bell(solid) {r['prop_bell_solid']['area_pct']} % > "
                       f"{r['prop_bell_solid']['budget_pct']} %")
        if not r.get("buried_faces", {"ok": True})["ok"]:
            why.append(f"매몰면(진짜결함) {r['buried_faces']['defect_pct']} % > "
                       f"{r['buried_faces']['budget_pct']} %")
        bad[k] = why
    if bad:
        raise AssertionError(f"메쉬 검증 실패 — 결함: {bad}\n"
                             f"  python src/mesh_check.py 로 상세 확인")
    return True


def _cli_mesh_fix(argv) -> str:
    """`--mesh-fix i5,m6[,battery]` 를 읽어 **두 통로를 한 번에** 켠다.

    2026-08-16 현재 수리 스위치가 두 갈래로 자랐다(정직하게 적는다):
      · **환경변수 통로** `geom.MESH_FIX` — 호출 시점에 읽으므로 인자를 안 배운 스크립트에도
        닿는다. `i5`(cadkit 슬리버 붕괴) · `m6`(geom.uv_sphere 극점) · 검사기 예산표가 이걸 본다.
      · **인자 통로** `drone_cad.MESH_FIX_TOKENS` — `build_drone(spec, mesh_fix=…)` 로 내려간다.
    이 CLI 는 준 이름을 **환경변수에 그대로 넣고**, 그중 drone_cad 가 아는 토큰만 골라
    `check_all(mesh_fix=…)` 로도 넘긴다. 모르는 이름은 여기서 **막는다**(조용한 무시 금지)."""
    from geom import MESH_FIX_KNOWN, set_mesh_fix
    from drone_cad import MESH_FIX_TOKENS
    names: list[str] = []
    for i, a in enumerate(argv):
        if a == "--mesh-fix" and i + 1 < len(argv):
            names += argv[i + 1].replace(";", ",").split(",")
        elif a.startswith("--mesh-fix="):
            names += a.split("=", 1)[1].replace(";", ",").split(",")
    names = [s.strip().lower() for s in names if s.strip()]
    if not names:
        return ""
    known = set(MESH_FIX_KNOWN) | set(MESH_FIX_TOKENS) | {"all"}
    bad = [n for n in names if n not in known]
    if bad:
        raise SystemExit(f"⛔ 모르는 --mesh-fix 이름 {bad}. 아는 이름 = {sorted(known)}")
    set_mesh_fix(names)
    return ",".join(n for n in names if n in MESH_FIX_TOKENS or n == "all") or None


if __name__ == "__main__":
    fix = _cli_mesh_fix(sys.argv[1:])
    print("=" * 110)
    print("trimesh 메쉬 검증 — 부품(연결요소) 단위 · split(repair=False) · 스펙 대조 포함")
    if fix or os.environ.get("MESH_FIX"):
        print(f"⭐ 메쉬 수리 켜짐 — MESH_FIX={os.environ.get('MESH_FIX','')!r} "
              f"(인자 통로로 넘기는 토큰: {fix!r}). 기본은 꺼짐이고, 켜면 형상이 바뀐다.")
    print("=" * 110)
    res = check_all(mesh_fix=fix or None)
    n_ok = sum(1 for r in res.values() if r["ok"])
    print(f"\n{'='*110}\n결과: {n_ok}/{len(res)} 통과")
    if n_ok < len(res):
        sys.exit(1)
