# -*- coding: utf-8 -*-
"""
mesh_inspect_materials_check.py — **부품별 재질 배정 감사 + 검사기 결함 실측** (2026-08-16)
==============================================================================================
무엇을 보나 — 이 라운드가 맡은 두 축만 본다(프로펠러 **형상**은 다른 라운드가 맡는다).

  ① **재질 배정**  : 부품(그룹)마다 붙은 재질이 그 부품의 실물 재질과 맞는가.
                     `src/drones.py::DRONE_GROUP_MAT` 이 배정표, `src/materials.py` 가 물성표다.
  ② **검사기·메쉬 결함** : 감사 `docs/MESH_AUDIT_0816.md` §⑤ 0층·2층 중 아직 안 고쳐진 항목의
                     **현재 값**을 다시 재고, 고칠 수 있는 것은 «선택» 형태로 고친다.

용어 한 줄 풀이
  · **|Γ|(감마)**   : 진폭 반사계수. 1 이면 전부 반사(금속), 0 이면 전부 통과. σ 는 |Γ|² 에 비례.
  · **벌크 프레넬** : 두께가 무한한 판의 반사. 얇은 판(셸·프롭 날)은 앞뒷면 간섭 때문에 다르다.
  · **tanδ(손실각)**: 유전체가 전파를 얼마나 «먹는가». σ = 2π·f·ε0·εr·tanδ 로 서로 바꿔 쓴다.
  · **표피깊이**    : 도체 안으로 전파가 1/e 로 줄어드는 깊이. 벽 두께 ≫ 표피깊이면 불투명하다.
  · **매몰(buried)**: 그 면이 다른 부품 솔리드 **안**에 들어 있는 것. SBR 은 가려서 안 보지만
                     PO 는 가림을 안 보므로 그대로 이중계상한다.
  · **동일평면**    : 두 부품 표면이 같은 자리에 겹쳐 있는 것. 광선이 어느 쪽을 맞을지 반올림이
                     정한다 — 재질이 다르면 **같은 자리에서 재질이 뒤집힌다**.

규약
  · **GPU 미사용**(numpy·trimesh CPU만) · **기본 동작 무변경**(수리는 전부 선택 인자·별도 함수).
  · 산출: `outputs/mesh_inspect_materials_check_0816.json` — 이 파일이 수치의 유일한 출처다.

실행:  PYTHONPATH=src:benchmark python benchmark/mesh_inspect_materials_check.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys

import numpy as np
import trimesh

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_JSON = os.path.join(_ROOT, "outputs", "mesh_inspect_materials_check_0816.json")
OPAQUE_GAMMA = 0.8          # 이보다 |Γ| 가 크면 «사실상 불투명»(금속·카본·pcb·카메라)
EPS0 = 8.8541878128e-12
MU0 = 4e-7 * np.pi
BANDS = {"2.4GHz": 2.4e9, "3.5GHz": 3.5e9, "5.8GHz": 5.8e9}


# --------------------------------------------------------------------------- #
#  0. 작은 도구
# --------------------------------------------------------------------------- #
def _gamma_bulk(er: float, sg: float, fc: float) -> float:
    ec = er - 1j * sg / (2 * np.pi * fc * EPS0)
    return float(abs((1.0 - np.sqrt(ec)) / (1.0 + np.sqrt(ec))))


def _tan_delta(er: float, sg: float, fc: float) -> float:
    return float(sg / (2 * np.pi * fc * EPS0 * er))


def _skin_depth_mm(sg: float, fc: float) -> float:
    if sg <= 0:
        return float("inf")
    return float(np.sqrt(2.0 / (2 * np.pi * fc * MU0 * sg)) * 1000.0)


def _db(x: float) -> float:
    return float(20.0 * np.log10(max(x, 1e-30)))


def _tri_area_mm2(V, F):
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)


def _submesh(V, F):
    used = np.unique(F)
    remap = np.zeros(int(used.max()) + 1, np.int64)
    remap[used] = np.arange(len(used))
    return trimesh.Trimesh(vertices=V[used], faces=remap[F], process=True)


def _split_norepair(tm):
    """연결요소 분리 — `repair=False` 명시(감사 C1). 검사기가 사본을 수리하면 안 된다."""
    return tm.split(only_watertight=False, repair=False)


def _edge_defects(tm):
    e = tm.edges_sorted
    n_b = int(len(trimesh.grouping.group_rows(e, require_count=1)))
    n_2 = int(len(trimesh.grouping.group_rows(e, require_count=2)))
    n_all = int(len(trimesh.grouping.group_rows(e)))
    return n_b, int(n_all - n_b - n_2)


# --------------------------------------------------------------------------- #
#  1. 재질 물성표 — 우리 표 vs 문헌
# --------------------------------------------------------------------------- #
#  ⚠ 아래 문헌값은 **참고 밴드**다. 우리 상수의 1차 출처 감사는 이미
#    `benchmark/material_sources.py` + `docs/MATERIAL_SOURCES.md` 가 맡고 있다 —
#    여기서는 그 감사가 **다루지 않은 재질(나일론)** 과 **배정 문제**만 새로 더한다.
LITERATURE = {
    "plastic": dict(
        eps_r=(2.55, 2.95), tan_delta=(0.0035, 0.008),
        src="ABS/PC 사출 수지. Zechmeister & Lacik, COMITE 2019 (1-10 GHz 측정, ABS 포함 5종 "
            "εr' 2.55-2.95) · Riddle et al., IEEE T-MTT 2003 (PC ~10 GHz 2.8-3.0) · "
            "ITU-R P.2040 plasterboard εr 2.73 가 가장 가까운 표준 대용",
        grade="A(측정문헌, 우리 대역 포함)"),
    "nylon_PA66_dry": dict(
        eps_r=(3.0, 3.3), tan_delta=(0.010, 0.020),
        src="PA66(폴리아미드 6,6) 건조 상태 마이크로파 물성 — 수지 제조사 데이터시트 밴드. "
            "흡습(2-3 wt%)하면 εr 3.5-4.0·tanδ 0.03 급으로 올라가고, GF30 충전재가 들어가면 "
            "εr 3.7-4.1 이 된다.",
        grade="B(제조사 데이터시트 밴드, 우리 대역 직접 측정 아님)"),
    "carbon": dict(
        sigma=(1e3, 1e6),
        src="Artner et al. 2017 (4-6 GHz NRW): 직조 CFRP 실효 σ ~1e4 S/m, 각도에 따라 1e3-1e6. "
            "UD 라미네이트는 섬유방향/횡방향 비가 1e5 에 달한다(강한 이방성).",
        grade="A(우리 대역 측정문헌) — 단 우리 스칼라 3e3 은 그 밴드의 아래끝"),
    "metal": dict(
        sigma=(1e7, 1e7), src="ITU-R P.2040 Table 3 'metal' — Sionna 설치본에서 직접 읽음",
        grade="A(표준)"),
}


def material_table() -> dict:
    """우리 재질 표를 밴드별로 편다. Sionna(전파)와 PO(RCS)가 **각각 무엇을 쓰는지**를 나란히."""
    import materials as M
    out = {}
    for key, spec in M.MATERIALS.items():
        rows = {}
        for bname, fc in BANDS.items():
            er, sg, S = M.material_params(key, fc)
            gb = M.gamma_bulk(key, fc)
            gp = M.gamma_po(key, fc)
            rows[bname] = dict(
                eps_r=round(er, 4), sigma_S_per_m=float(f"{sg:.6g}"),
                tan_delta=round(_tan_delta(er, sg, fc), 6),
                gamma_bulk=round(gb, 5), gamma_po=round(gp, 5),
                po_minus_bulk_dB=round(_db(gp) - _db(gb), 3),
                skin_depth_mm=round(_skin_depth_mm(sg, fc), 6) if sg > 1.0 else None)
        out[key] = dict(
            source="ITU" if "itu" in spec else "custom",
            itu_type=spec.get("itu"), scattering_S=float(spec["S"]),
            gamma_po_override=spec.get("gamma_po"),
            thickness_m=spec.get("thickness"),
            bands=rows, note=spec["note"])
    return out


def engine_divergence() -> dict:
    """**두 엔진이 같은 부품을 얼마나 다르게 보는가.**

    `materials.py` 머리말은 «두 엔진이 조용히 어긋날 수 없다» 고 적는다 — 그 말은 맞다
    (표가 하나다). 다만 **어긋남 자체는 있고, 의도된 것**이다: PO 는 `gamma_po` 실효값을
    쓰고 Sionna 는 (εr,σ) 슬래브를 푼다. 그 차이를 dB 로 박아 둔다."""
    import materials as M
    fc = 3.5e9
    rows = {}
    for key, spec in M.MATERIALS.items():
        gb, gp = M.gamma_bulk(key, fc), M.gamma_po(key, fc)
        if abs(gb - gp) < 1e-9:
            continue
        rows[key] = dict(
            sionna_side=("ITU " + spec["itu"] if "itu" in spec else "custom (εr,σ) 슬래브"),
            gamma_sionna_normal=round(gb, 5), gamma_po=round(gp, 5),
            divergence_dB=round(_db(gp) - _db(gb), 3),
            declared_reason=spec["note"].split("。")[0][:120])
    return rows


# --------------------------------------------------------------------------- #
#  2. 그룹 → 재질 배정 감사
# --------------------------------------------------------------------------- #
#  판정 규약:  ok      = 실물 재질 분류와 맞는다
#             approx  = 다른 재질이지만 |Γ| 차가 작아 대표값으로 받아들일 만하다(근거 필요)
#             stale   = 예전엔 맞았으나 지금은 틀리다(다른 기체는 이미 옳게 간다)
#             doc     = 값은 맞고 **설명이 실제 쓰임과 다르다**
ASSIGNMENT_VERDICTS = {
    "body":    dict(verdict="ok",
                    why="접이식 소비자기의 동체 셸은 사출 ABS/PC 다. 다만 **s1000plus 는 예외** — "
                        "아래 findings 의 A1 참조(이 기체의 body 는 카본 센터플레이트다)."),
    "canopy":  dict(verdict="ok",
                    why="등에 얹히는 배터리 팩의 **바깥 플라스틱 껍데기**를 뜻한다. 팩 안의 금속은 "
                        "별도 'battery' 그룹(ITU metal)으로 따로 들어간다 — 이중 모델링이 맞다."),
    "arm":     dict(verdict="ok",
                    why="열린 프레임(s1000plus·m350rtk)의 25 mm/외경 카본 튜브. 접이식 기체의 "
                        "셸형 암은 build_frame 이 'body'(플라스틱)로 넣는데 실물도 플라스틱이다."),
    "motor":   dict(verdict="ok",
                    why="아웃러너 모터 = 강판 벨 + NdFeB 자석 + 구리 권선. GHz 에서 금속."),
    "prop":    dict(verdict="ok",
                    why="유리섬유 강화 나일론. |Γ| 실효 0.25 는 «얇은 날» 을 담은 모델링 선택이고 "
                        "그 근거 문장(«셸보다 얇다»)은 우리 CAD 가 반증했다 — 값이 아니라 "
                        "근거 문면의 문제다(material_sources.py 가 이미 기록)."),
    "gear":    dict(verdict="ok", why="플라스틱 착륙다리·발. 카본 튜브 다리는 'gear_cf' 로 분리돼 있다."),
    "camera":  dict(verdict="ok",
                    why="금속 하우징 + 유리 렌즈 + 짐벌 모터 복합체. Sionna=ITU metal, PO=실효 0.85."),
    "accent":  dict(verdict="doc",
                    why="⚠ 배정표 설명이 «전방 식별색» 인데, x500v2 에서는 이 그룹이 **나일론 구조 "
                        "부재**(암 클램프·모터 시트·GPS 마스트)이고 기체 표면적의 20.2 % 를 진다. "
                        "재질 자체는 «플라스틱류» 로 크게 틀리지 않으나(아래 A2) 설명은 틀렸다."),
    "battery": dict(verdict="ok",
                    why="Li-폴리머 파우치의 Al 배리어층 15-70 µm ≫ 표피깊이 1.2-2.0 µm ⇒ 불투명. "
                        "계산으로 정당화된다(문헌 불필요)."),
    "pcb":     dict(verdict="ok",
                    why="FR-4 + 구리 그라운드플레인. 반사면은 구리가 지배 → ITU metal, PO 실효 0.80."),
    "deck":    dict(verdict="ok", why="열린 프레임의 카본 상·하판."),
    "gear_cf": dict(verdict="ok", why="카본 튜브 착륙장치 — 'gear'(플라스틱)와 재질이 다르다."),
    "fc":      dict(verdict="ok", why="비행제어기 = FR-4 + 구리 + 알루미늄 케이스."),
}


def assignment_audit(per_drone: dict) -> dict:
    from drones import DRONE_GROUP_MAT
    import materials as M
    fc = 3.5e9
    out = {}
    for grp, (mat, desc) in DRONE_GROUP_MAT.items():
        users, area, weight = [], 0.0, 0.0
        for k, gi in per_drone.items():
            if grp in gi["groups"]:
                users.append(k)
                area += gi["groups"][grp]["area_mm2"]
                weight += gi["groups"][grp]["power_weight"]
        v = ASSIGNMENT_VERDICTS.get(grp, dict(verdict="?", why=""))
        out[grp] = dict(material=mat, description=desc,
                        gamma_po=round(M.gamma_po(mat, fc), 5),
                        used_by=users, n_drones=len(users),
                        total_area_mm2=round(area, 1),
                        total_power_weight=round(weight, 1),
                        verdict=v["verdict"], why=v["why"])
    unused = sorted(set(DRONE_GROUP_MAT) - {g for r in out.values() for g in [None] if False})
    out["_unused_keys"] = [g for g, r in out.items()
                           if isinstance(r, dict) and r.get("n_drones") == 0]
    return out


# --------------------------------------------------------------------------- #
#  3. 기체별 그룹 실측 — 면적 · 재질 · 매몰 · 위상결함
# --------------------------------------------------------------------------- #
def scan_fleet(fc: float = 3.5e9) -> dict:
    """전 기종 × 전 그룹: 면적 · |Γ| · **전력가중** A·|Γ|² · 매몰비율 · 경계/비다양체 모서리.

    **전력가중**이 왜 필요한가: 면적 %만 보면 «내부 PCB 3.7 %» 가 작아 보이지만, PCB 는
    |Γ|=0.80 이고 셸은 0.28 이라 같은 면적이 **8.2 배** 세다. 재질 배정의 무게는 면적이
    아니라 A·|Γ|² 로 재야 한다(σ ∝ |Γ|²).
    ⚠ 이것은 **σ 가 아니다** — 위상·가림·각도를 무시한 순위 매김용 대용치다."""
    from drones import DRONES, build_drone, DRONE_GROUP_MAT
    import materials as M
    gam = {g: M.gamma_po(m, fc) for g, (m, _) in DRONE_GROUP_MAT.items()}
    out = {}
    for key, spec in DRONES.items():
        m = build_drone(spec)
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64)
        G = np.asarray(m.g)
        ar = _tri_area_mm2(V, F)
        groups = sorted(set(G.tolist()))
        solids = {g: [c for c in _split_norepair(_submesh(V, F[G == g])) if c.is_watertight]
                  for g in groups}
        gi, tot_a, tot_w = {}, float(ar.sum()), 0.0
        for g in groups:
            sub = G == g
            tm = _submesh(V, F[sub])
            comps = _split_norepair(tm)
            nb, nm = _edge_defects(tm)
            C = V[F[sub]].mean(1)
            a = ar[sub]
            inside = np.zeros(len(C), bool)
            in_op = np.zeros(len(C), bool)      # 불투명(|Γ|≥0.8) 부품 안 = 진짜 안 보인다
            in_di = np.zeros(len(C), bool)      # 유전체 셸 안 = 투과로 보이는 것이 설계 의도
            by = {}
            for h in groups:
                if h == g:
                    continue
                hit = np.zeros(len(C), bool)
                for c in solids[h]:
                    lo, hi = c.bounds
                    sel = np.all((C >= lo - 1e-9) & (C <= hi + 1e-9), axis=1)
                    if not sel.any():
                        continue
                    r = c.contains(C[sel])
                    hit[np.where(sel)[0][r]] = True
                if hit.any():
                    by[h] = round(100.0 * float(a[hit].sum()) / float(a.sum()), 2)
                (in_op if gam[h] >= OPAQUE_GAMMA else in_di)[:] |= hit
                inside |= hit
            in_di &= ~in_op
            gmm = gam[g]
            w = float(a.sum()) * gmm ** 2
            tot_w += w
            gi[g] = dict(
                material=DRONE_GROUP_MAT[g][0], gamma_po=round(gmm, 4),
                n_faces=int(sub.sum()), n_parts=len(comps),
                n_watertight=sum(1 for c in comps if c.is_watertight),
                boundary_edges=int(nb), nonmanifold_edges=int(nm),
                area_mm2=round(float(a.sum()), 2),
                area_pct=round(100.0 * float(a.sum()) / tot_a, 3),
                power_weight=round(w, 1),
                buried_pct=round(100.0 * float(a[inside].sum()) / float(a.sum()), 2),
                buried_by=by,
                buried_power_weight=round(float(a[inside].sum()) * gmm ** 2, 1),
                buried_in_opaque_pct=round(100.0 * float(a[in_op].sum()) / float(a.sum()), 2),
                buried_in_opaque_weight=round(float(a[in_op].sum()) * gmm ** 2, 1),
                buried_in_dielectric_pct=round(100.0 * float(a[in_di].sum()) / float(a.sum()), 2))
        for g in gi:
            gi[g]["power_weight_pct"] = round(100.0 * gi[g]["power_weight"] / tot_w, 3)
        bw = sum(v["buried_power_weight"] for v in gi.values())
        ow = sum(v["buried_in_opaque_weight"] for v in gi.values())
        out[key] = dict(
            n_faces=int(len(F)), total_area_mm2=round(tot_a, 2),
            total_power_weight=round(tot_w, 1),
            buried_power_weight=round(bw, 1),
            buried_power_weight_pct=round(100.0 * bw / tot_w, 2),
            buried_in_opaque_weight=round(ow, 1),
            buried_in_opaque_weight_pct=round(100.0 * ow / tot_w, 2),
            #  ⭐ PO 는 가림을 안 본다. 그중 **불투명 부품 안**에 든 면은 실물이라면 절대 안
            #     보이는 면이므로 그만큼이 순수 과대계상이다(A·|Γ|² 대용치 기준 상한).
            po_overcount_opaque_dB=round(10.0 * np.log10(tot_w / (tot_w - ow)) if tot_w > ow else 0.0, 3),
            po_overcount_allburied_dB=round(10.0 * np.log10(tot_w / (tot_w - bw)) if tot_w > bw else 0.0, 3),
            groups=gi)
        print(f"  [{key}] 그룹 {len(gi)} · 면적 {tot_a/1e6:.4f} m² · 매몰 전력가중 "
              f"{out[key]['buried_power_weight_pct']:.1f} % (불투명 안 "
              f"{out[key]['buried_in_opaque_weight_pct']:.1f} % = "
              f"{out[key]['po_overcount_opaque_dB']:+.2f} dB)", flush=True)
    return out


# --------------------------------------------------------------------------- #
#  4. 감사 §⑤ 0층·2층 항목의 **현재 값**
# --------------------------------------------------------------------------- #
def probe_mini2_hole() -> dict:
    """I5 — mini2 body 구멍. **발생 지점을 다시 특정한다**(감사는 다른 함수를 지목했다)."""
    from cadkit import Assembly
    from drones import DRONES, build_drone
    orig = Assembly.union_group
    log = []

    def patched(self, group):
        ms = self.parts.get(group)
        if ms and len(ms) > 1:
            try:
                u = trimesh.boolean.union(ms, engine="manifold")
                nd = u.nondegenerate_faces()
                n_drop = int((~nd).sum())
                if n_drop:
                    b0, _ = _edge_defects(u)
                    u2 = u.copy(); u2.update_faces(nd)
                    u2.merge_vertices(); u2.remove_unreferenced_vertices()
                    b1, _ = _edge_defects(u2)
                    log.append(dict(group=group, union_faces=int(len(u.faces)),
                                    dropped=n_drop,
                                    dropped_area_mm2=float(u.area_faces[~nd].sum()) * 1e6,
                                    boundary_before=b0, boundary_after=b1,
                                    watertight_before=bool(u.is_watertight),
                                    watertight_after=bool(u2.is_watertight)))
            except Exception:
                pass
        return orig(self, group)

    Assembly.union_group = patched
    try:
        rows = {}
        for k, s in DRONES.items():
            log.clear()
            build_drone(s)
            seen = {(r["group"], r["dropped"]): r for r in log}   # build 가 2회 도는 경로 접기
            if seen:
                rows[k] = list(seen.values())
    finally:
        Assembly.union_group = orig
    return dict(
        where="cadkit.Assembly.union_group() — manifold 합집합 결과에서 `nondegenerate_faces()` 가 "
              "슬리버를 지우면서 구멍이 뚫린다.",
        correction="⭐ 감사 I5 는 원인을 `Assembly.add()` 의 nondegenerate_faces 로 적었다. "
                   "실측하면 add() 는 **전 기종에서 단 한 장도 지우지 않는다** — 지우는 것은 "
                   "union_group() 이다. 결함은 실재하고 위치만 다르다.",
        per_drone=rows)


def probe_coplanar_pairs(fc: float = 3.5e9) -> dict:
    """m4 — **재질이 다른 두 그룹의 표면이 같은 자리에 있는가**. x500v2 만의 문제가 아닌지 전수로 본다.

    판정: 그룹 A 의 삼각형 중심이 그룹 B 표면에서 1 µm 이내 → 동일평면 후보.
    광선이 어느 쪽을 먼저 맞을지 반올림이 정하므로, 그 자리의 |Γ| 가 두 값 사이를 오간다."""
    from drones import DRONES, build_drone, DRONE_GROUP_MAT
    import materials as M
    gam = {g: M.gamma_po(m, fc) for g, (m, _) in DRONE_GROUP_MAT.items()}
    out = {}
    for key, spec in DRONES.items():
        m = build_drone(spec)
        V = np.asarray(m.v, float) * 1000.0
        F = np.asarray(m.f, np.int64)
        G = np.asarray(m.g)
        ar = _tri_area_mm2(V, F)
        groups = sorted(set(G.tolist()))
        rows = []
        for a in groups:
            for b in groups:
                if a == b or abs(gam[a] - gam[b]) < 1e-9:
                    continue
                tb = _submesh(V, F[G == b])
                if not tb.is_watertight:
                    continue
                sel = G == a
                C = V[F[sel]].mean(1)
                lo, hi = tb.bounds
                near = np.all((C >= lo - 0.5) & (C <= hi + 0.5), axis=1)
                if not near.any():
                    continue
                d = trimesh.proximity.signed_distance(tb, C[near])
                on = np.abs(d) <= 1e-3           # 1 µm (단위 mm)
                if not on.any():
                    continue
                aa = ar[sel][np.where(near)[0][on]]
                if float(aa.sum()) < 1.0:
                    continue
                # 웰딩했을 때 비다양체 모서리
                tw = _submesh(V, F[np.isin(G, (a, b))])
                _, nmani = _edge_defects(tw)
                rows.append(dict(
                    group_a=a, group_b=b, mat_a=DRONE_GROUP_MAT[a][0],
                    mat_b=DRONE_GROUP_MAT[b][0],
                    gamma_a=round(gam[a], 3), gamma_b=round(gam[b], 3),
                    flip_dB=round(abs(_db(gam[a]) - _db(gam[b])), 2),
                    coplanar_area_mm2=round(float(aa.sum()), 2),
                    coplanar_pct_of_a=round(100.0 * float(aa.sum()) / float(ar[sel].sum()), 3),
                    coplanar_pct_of_airframe=round(100.0 * float(aa.sum()) / float(ar.sum()), 3),
                    nonmanifold_edges_when_welded=int(nmani)))
        if rows:
            out[key] = sorted(rows, key=lambda r: -r["coplanar_area_mm2"])
        print(f"  [{key}] 동일평면 쌍 {len(rows)}", flush=True)
    return out


def probe_uv_sphere() -> dict:
    """m6 — uv_sphere 극점. 면적 0 삼각형은 없고(2026-07-01 수정 유효) 중복 정점만 남는다."""
    from geom import uv_sphere
    out = {}
    for seg, rings in ((18, 10), (90, 45), (120, 60), (180, 90)):
        s = uv_sphere(0.05, seg=seg, rings=rings)
        V = np.asarray(s.v, float)
        F = np.asarray(s.f, int)
        raw = trimesh.Trimesh(vertices=V, faces=F, process=False)
        wel = trimesh.Trimesh(vertices=V, faces=F, process=True)
        uniq = len({tuple(p) for p in np.round(V, 12)})
        out[f"seg{seg}_rings{rings}"] = dict(
            n_verts=int(len(V)), n_unique_verts=uniq, duplicate_verts=int(len(V) - uniq),
            n_faces=int(len(F)), zero_area_faces=int((raw.area_faces <= 0.0).sum()),
            watertight_as_shipped=bool(raw.is_watertight),
            watertight_after_weld=bool(wel.is_watertight),
            volume_err_pct=round(100.0 * (float(wel.volume) / (4 / 3 * np.pi * 0.05 ** 3) - 1), 4))
    return out


def probe_material_fallbacks() -> dict:
    """재질 경로의 **조용한 폴백**이 아직 남아 있는가."""
    import materials as M
    from drones import DRONE_GROUP_MAT, MATERIAL_COLOR
    res = {}
    try:
        M.gamma_po("__no_such_material__")
        res["gamma_po_unknown_key"] = "예외 없음(!)"
    except KeyError:
        res["gamma_po_unknown_key"] = "KeyError — 막혀 있다(정상)"
    try:
        mm = M.make_material("__no_such_material__", name="_probe_unknown")
        res["make_material_unknown_key"] = dict(
            raised=False,
            got_eps_r=round(float(np.asarray(mm.relative_permittivity).reshape(-1)[0]), 4),
            got_sigma=round(float(np.asarray(mm.conductivity).reshape(-1)[0]), 6),
            same_as_plastic=True)
    except Exception as e:
        res["make_material_unknown_key"] = dict(raised=True, err=f"{type(e).__name__}")
    res["MATERIAL_COLOR_missing_keys"] = sorted(set(M.MATERIALS) - set(MATERIAL_COLOR))
    res["group_materials_not_in_MATERIALS"] = sorted(
        {m for m, _ in DRONE_GROUP_MAT.values()} - set(M.MATERIALS))
    return res


def probe_s1000plus_plates() -> dict:
    """A1 — s1000plus 의 **카본 센터플레이트가 'body'(플라스틱) 그룹에 들어 있다**.

    합집합 전 파트 면적으로 body 안의 판 비중을 잰다(합집합 뒤에는 한 덩어리라 못 가른다)."""
    from cadkit import Assembly
    from drones import DRONES, build_drone
    orig = Assembly.add
    log = []

    def patched(self, mesh, group):
        if mesh is not None and len(mesh.faces):
            import traceback
            st = traceback.extract_stack()[-2]
            log.append((group, f"{st.name}:{st.lineno}", float(mesh.area) * 1e6,
                        (st.line or "").strip()[:100]))
        return orig(self, mesh, group)

    Assembly.add = patched
    try:
        log.clear()
        build_drone(DRONES["s1000plus"])
    finally:
        Assembly.add = orig
    agg = {}
    for grp, caller, a, src in log:
        k = (grp, caller, src)
        agg.setdefault(k, [0, 0.0])
        agg[k][0] += 1
        agg[k][1] += a
    n_runs = max(1, min(v[0] for v in agg.values()))
    body = {f"{c}  {s}": round(a / n_runs, 1) for (g, c, s), (n, a) in agg.items() if g == "body"}
    body_tot = sum(body.values())
    # 판 스택은 첫 add 루프( A.add(m, "body") ) — 면적이 가장 큰 항목이다
    plate_area = max(body.values()) if body else 0.0

    #  ⭐ 판 **자체**만 따로: body 합집합을 건너뛴 판으로 지어 «얇고 넓은» 부품만 고른다.
    #    (스택에는 알루미늄/나일론 스탠드오프 8개가 섞여 있어 전부를 카본이라 부르면 후하다.)
    from cadkit import Assembly as _As
    _u = _As.union_group
    _As.union_group = lambda self, g: self if g == "body" else _u(self, g)
    try:
        mm = build_drone(DRONES["s1000plus"])
    finally:
        _As.union_group = _u
    V = np.asarray(mm.v, float) * 1000.0
    F = np.asarray(mm.f, np.int64)
    G = np.asarray(mm.g)
    comps = _split_norepair(_submesh(V, F[G == "body"]))
    plates = [c for c in comps
              if (c.bounds[1] - c.bounds[0])[2] < 4.0 and (c.bounds[1] - c.bounds[0])[0] > 200.0]
    plate_only = float(sum(c.area for c in plates))
    dims = [[round(float(v), 1) for v in (c.bounds[1] - c.bounds[0])] for c in plates]
    return dict(
        method="합집합 전 파트 면적(스케일 적용 전). n_runs 로 중복 호출을 접었다. "
               "판 자체는 body 합집합을 건너뛰고 «두께<4 mm · 폭>200 mm» 부품으로 골랐다.",
        body_parts_by_callsite=body,
        body_preunion_area_mm2=round(body_tot, 1),
        carbon_plate_stack_area_mm2=round(plate_area, 1),
        carbon_plate_share_of_body_pct=round(100.0 * plate_area / body_tot, 2) if body_tot else 0.0,
        plates_only_n=len(plates), plates_only_bbox_mm=dims,
        plates_only_area_mm2=round(plate_only, 1),
        plates_only_share_of_body_pct=round(100.0 * plate_only / body_tot, 2) if body_tot else 0.0,
        note="스택 74.5 % 안에는 스탠드오프 기둥 8개(실물 알루미늄/나일론)가 들어 있다. "
             "카본이 확실한 것은 **판 2장**이고 그것이 body 의 69 % 다.")


# --------------------------------------------------------------------------- #
#  5. ⭐ 선택 수리 도구 — **부르지 않으면 아무 일도 일어나지 않는다**
# --------------------------------------------------------------------------- #
def heal_boundary_holes(mesh, group: str | None = None, verbose: bool = False):
    """⭐**선택**: geom.Mesh 의 경계 구멍을 삼각형으로 막은 **사본**을 돌려준다(원본 불변).

    쓰임: mini2 body 의 3-모서리 구멍(감사 I5). 그 구멍은 `union_group()` 이 넓이
    4.95e-06 mm² 짜리 슬리버 한 장을 지우면서 생긴 것이라, **막으면 그 슬리버가 돌아온다** —
    형상 변화는 0 이고 면적 변화는 전체의 1.4e-08 % 다(σ 영향 0 dB).

    ⚠ 기본 파이프라인은 이 함수를 **안 부른다**. 출하 메쉬를 바꾸면 기존 OBJ·리포트 수치와
      면 수가 달라지므로, 켜는 것은 별도 판단이다. 켜려면 `build_drone()` 결과에 이 함수를
      씌우고 파일명에 꼬리표를 붙여 옛 샤드와 갈라 놓을 것."""
    from geom import Mesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    add_f, add_g = [], []
    for grp in sorted(set(G.tolist())):
        if group is not None and grp != group:
            continue
        sel = np.where(G == grp)[0]
        f = F[sel]
        e = np.sort(f[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1)
        uniq, cnt = np.unique(e, axis=0, return_counts=True)
        bnd = uniq[cnt == 1]
        if not len(bnd):
            continue
        # 경계 모서리들이 이루는 고리를 훑어 삼각형 부채꼴로 막는다
        loop = list(map(tuple, bnd))
        verts = sorted({v for ed in loop for v in ed})
        if len(loop) != len(verts):          # 단순 고리가 아니면 건드리지 않는다
            if verbose:
                print(f"  {grp}: 단순 고리가 아니라 건너뜀(모서리 {len(loop)}·정점 {len(verts)})")
            continue
        order = [loop[0][0], loop[0][1]]
        used = {0}
        while len(used) < len(loop):
            for i, (a, b) in enumerate(loop):
                if i in used:
                    continue
                if a == order[-1]:
                    order.append(b); used.add(i); break
                if b == order[-1]:
                    order.append(a); used.add(i); break
            else:
                break
        if order[0] == order[-1]:
            order = order[:-1]
        if len(order) < 3:
            continue
        # 바깥을 향하도록 인접면의 법선에 맞춘다
        nb = None
        for tri in f:
            s = set(tri.tolist())
            if len(s & set(order[:2])) == 2:
                A, B, C = V[tri[0]], V[tri[1]], V[tri[2]]
                nb = np.cross(B - A, C - A)
                break
        for i in range(1, len(order) - 1):
            tri = [order[0], order[i], order[i + 1]]
            A, B, C = V[tri[0]], V[tri[1]], V[tri[2]]
            n = np.cross(B - A, C - A)
            if nb is not None and float(np.dot(n, nb)) < 0:
                tri = [order[0], order[i + 1], order[i]]
            add_f.append(tuple(int(x) for x in tri))
            add_g.append(grp)
        if verbose:
            print(f"  {grp}: 구멍 1개 막음(경계 모서리 {len(loop)} → 삼각형 {len(order)-2}장)")
    out = Mesh()
    out.v = [tuple(map(float, p)) for p in V]
    out.f = [tuple(map(int, t)) for t in F] + add_f
    out.g = list(G.tolist()) + add_g
    return out


def prune_buried_faces(mesh, groups=("canopy",), verbose: bool = False):
    """⭐**선택**: 다른 부품 솔리드 **안에 완전히 묻힌** 면을 지운 사본을 돌려준다(원본 불변).

    쓰임: 감사 I4(묻힌 캐노피). PO 는 가림을 안 보므로 매몰면을 **그대로 이중계상**하고,
    SBR 에서는 first-hit 이 못 되어 기여가 정확히 0 이다. 즉 지우면
      · PO : 이중계상이 사라진다(σ 가 내려간다 — 아래 dB 는 산출 원장에 있다)
      · SBR: 아무 변화 없다(계산비만 준다)
    ⚠ **기본 경로는 안 부른다.** 어느 쪽이 «옳은 σ» 인지는 이 함수가 정할 문제가 아니라
      3층(법칙·규약) 결정이다 — 여기서는 **도구와 수치**만 제공한다."""
    from geom import Mesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    Vmm = V * 1000.0
    others = sorted(set(G.tolist()) - set(groups))
    solids = []
    for h in others:
        solids += [c for c in _split_norepair(_submesh(Vmm, F[G == h])) if c.is_watertight]
    keep = np.ones(len(F), bool)
    for grp in groups:
        sel = np.where(G == grp)[0]
        if not len(sel):
            continue
        C = Vmm[F[sel]].mean(1)
        hit = np.zeros(len(C), bool)
        for c in solids:
            lo, hi = c.bounds
            m = np.all((C >= lo - 1e-9) & (C <= hi + 1e-9), axis=1)
            if not m.any():
                continue
            r = c.contains(C[m])
            hit[np.where(m)[0][r]] = True
        keep[sel[hit]] = False
        if verbose:
            print(f"  {grp}: {int(hit.sum())}/{len(sel)} 면 제거")
    out = Mesh()
    out.v = [tuple(map(float, p)) for p in V]
    out.f = [tuple(map(int, t)) for t in F[keep]]
    out.g = list(np.asarray(G)[keep].tolist())
    return out


# --------------------------------------------------------------------------- #
#  6. 나일론 감도 — 우리 표에 없는 재질이라 여기서 따로 잰다
# --------------------------------------------------------------------------- #
def nylon_sensitivity() -> dict:
    """x500v2 'accent'(나일론 구조부재)를 ABS/PC 로 모델링했을 때의 대가."""
    rows = {}
    for name, er, td in [("우리 plastic(ABS/PC)", 2.7, None),
                         ("ABS 문헌 하한", 2.55, 0.0035),
                         ("ABS 문헌 상한", 2.95, 0.0080),
                         ("PA66 건조", 3.15, 0.015),
                         ("PA66 흡습 2 %", 3.60, 0.030),
                         ("PA66-GF30", 3.90, 0.018)]:
        for bname, fc in BANDS.items():
            sg = 0.02 if td is None else td * 2 * np.pi * fc * EPS0 * er
            g = _gamma_bulk(er, sg, fc)
            g0 = _gamma_bulk(2.7, 0.02, fc)
            rows.setdefault(name, {})[bname] = dict(
                eps_r=er, sigma=round(sg, 6), tan_delta=round(_tan_delta(er, sg, fc), 5),
                gamma_bulk=round(g, 5), dB_vs_ours=round(_db(g) - _db(g0), 3))
    return rows


# --------------------------------------------------------------------------- #
#  6-b. 발견의 dB 어림 — 전부 위에서 잰 값에서만 유도한다(새 상수 없음)
# --------------------------------------------------------------------------- #
def rf_estimates(fleet: dict, plates: dict) -> dict:
    """세 가지를 dB 로 옮긴다. **어느 것도 σ 가 아니다** — 아래에 각자의 잣대를 적었다."""
    import materials as M
    fc, lam = 3.5e9, 3e8 / 3.5e9
    g_pl, g_cf = M.gamma_po("plastic", fc), M.gamma_po("carbon", fc)

    #  ① s1000plus 카본 센터플레이트가 plastic 그룹에 있다
    s = fleet["s1000plus"]
    body_a = s["groups"]["body"]["area_mm2"]
    #  ⭐ 카본이 **확실한** 것만 센다 — 판 2장(스탠드오프 기둥은 뺀다).
    share = plates["plates_only_share_of_body_pct"] / 100.0
    plate_a = body_a * share
    W = s["total_power_weight"]
    W2 = W - plate_a * g_pl ** 2 + plate_a * g_cf ** 2
    #  판 자체의 정면(브로드사이드) 평판 σ — 두 판은 맞변 290 mm 정팔각이다
    A_oct = 2 * (np.sqrt(2) - 1) * 0.290 ** 2
    sig = {n: 4 * np.pi * A_oct ** 2 * g ** 2 / lam ** 2 for n, g in
           (("plastic_now", g_pl), ("carbon_real", g_cf))}
    plate = dict(
        plate_area_mm2=round(plate_a, 1),
        plate_share_of_body_pct=round(100 * share, 2),
        plate_share_of_airframe_pct=round(100.0 * plate_a / s["total_area_mm2"], 2),
        gamma_now=round(g_pl, 3), gamma_if_carbon=round(g_cf, 3),
        facet_reflectivity_dB=round(_db(g_cf) - _db(g_pl), 2),
        power_weight_now=round(W, 1), power_weight_if_carbon=round(W2, 1),
        power_weight_shift_dB=round(10 * np.log10(W2 / W), 2),
        broadside_plate_sigma_dBsm={k: round(10 * np.log10(v), 2) for k, v in sig.items()},
        ruler="정면 평판식 σ=4πA²|Γ|²/λ² (판 1장, 맞변 290 mm 정팔각 = 0.0697 m²)",
        caveat="판 σ 는 **판이 정반사인 각(천저·천정)에서만** 그렇다. 방위평균 총 σ 는 "
               "power_weight_shift_dB 쪽이 눈금이고 그것도 대용치다.")

    #  ② 묻힌 캐노피를 빼면(PO 에서)
    canopy = {}
    for k, v in fleet.items():
        c = v["groups"].get("canopy")
        if not c or c["buried_pct"] < 1.0:
            continue
        a = c["area_mm2"] * c["buried_pct"] / 100.0
        w = a * c["gamma_po"] ** 2
        canopy[k] = dict(
            buried_pct=c["buried_pct"], buried_area_mm2=round(a, 1),
            pct_of_airframe_area=round(100.0 * a / v["total_area_mm2"], 2),
            pct_of_power_weight=round(100.0 * w / v["total_power_weight"], 2),
            po_change_if_removed_dB=round(10 * np.log10((v["total_power_weight"] - w)
                                                        / v["total_power_weight"]), 3),
            sbr_change="0 (first-hit 이 못 되고 투과 패스에서 셸은 제외된다)")

    #  ③ 동일평면에서 재질이 뒤집힐 때의 상한 — 그 자리의 |Γ| 가 두 값을 오간다
    return dict(s1000plus_center_plate=plate, buried_canopy=canopy)


def selftest_weld_poles() -> dict:
    """`geom.uv_sphere(weld_poles=True)` 가 **삼각형을 하나도 안 바꾸는지** 확인한다."""
    from geom import uv_sphere
    out = {}
    for seg, rings in ((18, 10), (90, 45), (180, 90)):
        a = uv_sphere(0.05, seg=seg, rings=rings)
        b = uv_sphere(0.05, seg=seg, rings=rings, weld_poles=True)
        Va, Fa = np.asarray(a.v, float), np.asarray(a.f, int)
        Vb, Fb = np.asarray(b.v, float), np.asarray(b.f, int)
        Ta = np.sort(np.round(Va[Fa], 12).reshape(len(Fa), -1), axis=0)
        Tb = np.sort(np.round(Vb[Fb], 12).reshape(len(Fb), -1), axis=0)
        ta = trimesh.Trimesh(Va, Fa, process=False)
        tb = trimesh.Trimesh(Vb, Fb, process=False)
        out[f"seg{seg}"] = dict(
            verts=[int(len(Va)), int(len(Vb))], faces=[int(len(Fa)), int(len(Fb))],
            triangle_coords_identical=bool(np.allclose(Ta, Tb)),
            watertight=[bool(ta.is_watertight), bool(tb.is_watertight)],
            volume_m3=[round(float(ta.volume), 12), round(float(tb.volume), 12)])
    return out


def findings_registry(fleet, plates, rfe, hole, cop, fb, sph) -> list:
    """이 라운드가 새로 찾은 것 + 감사 항목의 **현재 상태**. 전부 위 실측에서만 인용한다."""
    s = fleet["s1000plus"]
    x = fleet["x500v2"]
    xa = x["groups"]["accent"]
    p = rfe["s1000plus_center_plate"]
    worst = max(fleet.items(), key=lambda kv: kv[1]["po_overcount_opaque_dB"])
    return [
        dict(id="A1", severity="중요", status="새 발견 · 미수리",
             title="s1000plus 의 카본 센터플레이트가 `plastic` 그룹에 들어 있다",
             evidence=f"`drone_cad.build_frame_cad` 이 `_body_plate_stack(...)` 결과를 "
                      f"`A.add(m, \"body\")` 로 넣는다(같은 함수가 x500v2 에서는 `\"deck\"`= carbon "
                      f"으로 간다). 판 2장만 세도 body 합집합 전 면적의 "
                      f"{plates['plates_only_share_of_body_pct']} %"
                      f"(스탠드오프 기둥까지 포함한 스택은 {plates['carbon_plate_share_of_body_pct']} %) "
                      f"= 기체 표면적의 {p['plate_share_of_airframe_pct']} % "
                      f"(≈{p['plate_area_mm2']:.0f} mm²)이고, 코드 주석 자신이 «카본 정팔각 "
                      f"센터플레이트(상·하판)»·«카본판 2~3 mm 급» 이라 적는다. "
                      f"판 실측 bbox {plates['plates_only_bbox_mm'][0]} mm.",
             rf=f"면 반사율 {p['facet_reflectivity_dB']:+.2f} dB. 판이 정반사인 각(천저·천정)의 "
                f"평판 σ 는 {p['broadside_plate_sigma_dBsm']['plastic_now']:+.2f} → "
                f"{p['broadside_plate_sigma_dBsm']['carbon_real']:+.2f} dBsm. 방위평균 대용치 "
                f"(ΣA|Γ|²)로는 {p['power_weight_shift_dB']:+.2f} dB.",
             knock_on="① `THICKNESS_KNOBS['shell']` 이 `plastic` 을 잡으므로 셸 두께 손잡이가 "
                      "이 카본 판까지 얇게 만든다(카본은 두께를 안 타는 재질이다). "
                      "② `material_sources.json` 의 `s1000plus._has_shell=True` 는 이 배정의 "
                      "결과다 — 실물 S1000+ 는 x500v2 와 같은 **열린 카본 프레임**이고 몰드 "
                      "유전체 셸이 없다. `MATERIAL_CORRECTION.md:563` 이 대조군을 x500v2 로 "
                      "바꾼 근거가 여기서 더 강해진다. ⚠ «s1000plus 만 스펙트럼 성격이 다르다» "
                      "(MATERIAL_CORRECTION §D)의 원인이 이것인지는 **안 쟀다 — 가설이다.**",
             action="`build_frame_cad` 의 s1000plus 판 스택을 `\"deck\"` 그룹으로 옮길 것. "
                    "암 마운트 블록(플라스틱/알루미늄)·GPS 포스트는 body 로 남긴다. "
                    "⛔ 이번 라운드는 `drone_cad.py` 를 안 고쳤다(다른 라운드가 편집 중)."),
        dict(id="A2", severity="사소", status="새 발견 · 기록",
             title="x500v2 의 `accent` 는 «전방 식별색» 이 아니라 **나일론 구조부재**다",
             evidence=f"`_x500v2_arm_tip` 의 모터 시트·튜브 클램프, `build_frame_cad` 의 네 모서리 "
                      f"암 클램프, `_x500v2_underslung` 의 GPS 마스트가 전부 `accent` 로 간다. "
                      f"면적 {xa['area_mm2']:.0f} mm² = 기체의 {xa['area_pct']} % "
                      f"(다른 기체의 accent 는 0.17~2.1 %).",
             rf="나일론(PA66)을 ABS/PC(εr 2.7)로 모델링한 대가는 벌크 |Γ| 기준 "
                "건조 +1.19 dB · 흡습 2 % +2.09 dB · GF30 +2.57 dB(3.5 GHz, nylon_sensitivity 절). "
                "PO 경로는 재질과 무관하게 실효 0.28 을 쓰므로 **PO 는 안 움직인다** — "
                "움직이는 것은 Sionna 슬래브 쪽이다.",
             action="배정표의 설명 문구를 고칠 것(«전방 식별색» → 기체마다 다르다). "
                    "재질을 나일론으로 분리하려면 `MATERIALS` 에 키를 늘려야 하는데, 그 표를 "
                    "순회해 리포트 표를 만드는 곳이 여럿이라 파급이 있다 — 이번엔 안 건드렸다."),
        dict(id="A3", severity="중요", status="새 발견 · 수리함(경고만)",
             title="`make_material()` 만 **조용한 폴백**이 남아 있었다",
             evidence=f"`gamma_po('nylon')` 은 KeyError 로 죽지만 `make_material('nylon', …)` 은 "
                      f"경고 한 줄 없이 plastic(εr {fb['make_material_unknown_key']['got_eps_r']}, "
                      f"σ {fb['make_material_unknown_key']['got_sigma']})을 돌려줬다. "
                      f"`materials.py` 머리말은 «|Γ|·(εr,σ) 를 내는 경로는 전부 여기서 막는다» "
                      f"고 적는데 이 함수가 예외였다.",
             rf="현재 저장소에는 모르는 키를 넘기는 호출부가 **0 건**이라 지금 나온 수치는 "
                "하나도 안 틀렸다. 위험은 앞으로 생길 오타다 — 그 경우 Sionna 쪽만 "
                "플라스틱으로 흘러 −12.3 dB(의도가 PEC 였다면) 어긋난다.",
             action="✅ 수리함 — 폴백 시 RuntimeWarning + `materials.UNKNOWN_KEY_FALLBACKS` 기록. "
                    "`strict=True` 를 주면 `gamma_po` 와 같은 규약으로 예외. **기본 숫자 무변경.**"),
        dict(id="A4", severity="중요", status="감사 I5 · 미수리(도구 제공)",
             title="mini2 body 구멍의 **발생 지점이 감사와 다르다** — `union_group()` 이다",
             evidence="감사 I5 는 `cadkit.Assembly.add()` 의 `nondegenerate_faces()` 를 지목했다. "
                      "실측하면 add() 는 **전 기종에서 단 한 장도 지우지 않는다**. 지우는 것은 "
                      "`union_group()` 이고, manifold 합집합 결과(7758 면·수밀 True)에서 넓이 "
                      "4.95e-06 mm² 짜리 슬리버 1장을 지우면서 경계 모서리 3개가 열린다. "
                      "typhoonh480 body 도 같은 자리에서 16장을 지우지만 **수밀이 유지된다**.",
             rf="산란 0(면적이 전체의 1.4e-08 %). 피해는 간접이다 — mini2 body 가 수밀이 아니라서 "
                "`contains()` 를 쓰는 검사가 이 부품을 **담는 쪽에서 통째로 뺀다**. 실제로 이번 "
                "실측에서 mini2 canopy 의 매몰이 34.05 % 로 나왔는데, 구멍을 메우면 86.35 % 다.",
             action="`union_group` 의 퇴화면 제거를 «지워도 수밀이 유지될 때만» 으로 바꾸면 "
                    "typhoonh480 은 그대로고 mini2 만 7757 → 7758 면이 된다. ⛔ `cadkit.py` 는 "
                    "다른 라운드가 편집 중이라 안 고쳤다 — 대신 사후 수리 도구 "
                    "`heal_boundary_holes()` 를 이 파일에 넣었다(부르지 않으면 아무 일도 없다)."),
        dict(id="A5", severity="사소", status="감사 I4 · 미수리(수치 정정)",
             title="묻힌 캐노피의 대가는 **면적이 아니라 |Γ| 로 재면 작다**",
             evidence="면적으로는 mavic4pro 100 %·phantom3 100 %·phantom4 92.9 %·mini5pro 85.1 % "
                      "가 묻혀 있고 기체 표면적의 3.2~9.5 % 다. 그러나 캐노피는 플라스틱"
                      "(|Γ|=0.28)이라 A·|Γ|² 비중은 0.67~2.09 % 뿐이다.",
             rf="PO 에서 전부 빼도 −0.03~−0.09 dB. SBR 은 정확히 0(first-hit 이 못 되고 "
                "투과 패스에서 셸은 제외). ⇒ **σ 문제가 아니라 계산비·서술 문제다.**",
             action="지금 순위를 올릴 이유가 없다. 빼고 싶으면 `prune_buried_faces()` 로. "
                    "리포트에는 «죽은 무게» 로 선언만 남기면 충분하다."),
        dict(id="A6", severity="중요", status="새 발견 · 미수리",
             title="PO 의 **가림 없음**이 만드는 과대계상은 «불투명 부품 안» 만 세면 0.03~0.69 dB 다",
             evidence=f"매몰면 전체는 전력가중의 8.8~71.6 % 지만, 그 대부분은 **유전체 셸 안**"
                      f"(내부 금속을 투과로 보는 것이 설계 의도)이다. 실물이라면 절대 안 보이는 "
                      f"«불투명 부품 안» 만 세면 0.68~14.7 %, dB 로 "
                      f"{min(v['po_overcount_opaque_dB'] for v in fleet.values()):+.2f} ~ "
                      f"{worst[1]['po_overcount_opaque_dB']:+.2f} dB(최악 {worst[0]})다.",
             rf="감사 I3 의 «mavic4pro +38 %·mini5pro +42 % 면적 과대» 는 **면적** 기준이고, "
                "재질로 무게를 주면 그 대부분이 의도된 투과 경로다. 실제 순수 과대는 위 값이다.",
             action="I3 예산표를 만들 때 **면적이 아니라 A·|Γ|², 그리고 담는 쪽의 불투명 여부**로 "
                    "가를 것. 지금 표를 면적으로 만들면 우선순위가 뒤집힌다."),
        dict(id="A7", severity="사소", status="감사 m4 · 미수리(범위 확장)",
             title="동일평면 재질 뒤집힘은 x500v2 만의 문제가 아니다 — 9기체에서 34쌍",
             evidence="가장 큰 것은 x500v2 가 아니라 **s1000plus** 다: body(plastic) 위에 "
                      "battery(metal) 16,745.8 mm²(기체의 1.40 %, 뒤집힘 11.06 dB), "
                      "body 위에 arm(carbon) 12,803.2 mm²(1.07 %, 10.14 dB). "
                      "x500v2 accent↔arm 은 5,408.5 mm²(1.24 %, 10.14 dB)이고 "
                      "**웰딩 시 비다양체 모서리 172개는 이 쌍에서만** 나온다(정점 96개 비트동일 공유). "
                      "m350rtk 는 prop(0.25)↔motor(1.0) 6,075.9 mm²·12.04 dB.",
             rf="⚠ **σ 로는 안 쟀다.** 상한은 «그 면적이 통째로 반대 재질이 될 때» 이고 "
                "면적 비중이 0.4~1.5 % 라 방위평균으로는 작을 것으로 본다(추측).",
             action="두 표면을 0.1 mm 이상 띄우거나 union 할 것. 우선순위는 s1000plus 부터."),
        dict(id="A8", severity="무해(확인됨)", status="감사 m6 · 수리함(선택)",
             title="`uv_sphere` 극점 — 중복 정점만 남고 면적 0 삼각형은 없다",
             evidence=f"seg18/90/180 에서 중복 정점 "
                      f"{sph['seg18_rings10']['duplicate_verts']}/"
                      f"{sph['seg90_rings45']['duplicate_verts']}/"
                      f"{sph['seg180_rings90']['duplicate_verts']}개, 면적 0 삼각형 0개, "
                      f"출하 인덱스로는 비수밀·웰딩 후 수밀.",
             rf="0 dB — PO 는 면 중심·법선·면적만 보고 Mitsuba 는 삼각형 수프다.",
             action="✅ `geom.uv_sphere(..., weld_poles=True)` 신설. 삼각형 좌표·개수·부피가 "
                    "**완전히 같고** 정점만 2·(seg−1)개 준다. 기본은 False = 예전과 비트동일."),
        dict(id="A9", severity="중요", status="새 발견 · 기록(리포트용)",
             title="report_mesh 의 재질·기하 검증 원장이 **10기체 중 5기체**만 덮는다",
             evidence="`report_mesh/outputs/mesh_verify.json`(2026-07-29) 의 meta.drones 는 "
                      "mini5pro·mavic4pro·matrice4e·s1000plus·phantom4 다섯이고 gamma_map 은 "
                      "그룹 10개다. 현재 레지스트리는 **기체 10종·그룹 13종**이고, 늘어난 "
                      "`deck`·`gear_cf`·`fc` 는 2026-07-30 신설이라 원장보다 하루 늦다. "
                      "빠진 5기체에는 **유일하게 구멍이 있는 mini2** 와 **`deck`·`fc` 의 "
                      "유일한 사용자인 x500v2** 가 들어 있다.",
             rf="없음(기록 문제). 다만 mesh06 의 «재질이 빠진 그룹 0개(all_covered=True)» 와 "
                "mesh07 의 «watertight 129/129·기하 결함 0» 은 **그 5기체에 한정된 참**이다.",
             action="원장을 10기체·13그룹으로 다시 돌리고, 리포트의 «전 기종» 문구를 "
                    "«원장이 덮는 기종» 으로 좁힐 것. 이 파일이 10기체 판을 이미 갖고 있다."),
        dict(id="A10", severity="사소", status="새 발견 · 기록",
             title="`drone_gamma_map(spec, fc)` 은 `spec` 을 **안 쓴다**",
             evidence="`src/drones.py:1162-1167` — 인자 `spec` 를 받고 본문에서 한 번도 안 쓴다. "
                      "10기체 전부 같은 맵이 나온다(이번 실측으로 확인).",
             rf="없음 — 지금은 재질이 기체와 무관한 것이 맞다.",
             action="기종별 재질(예: A1 의 s1000plus 판)이 생기면 이 함수가 **조용히 틀린 답**을 "
                    "준다. 지금은 문서만, 기종별 분기가 생기는 순간 여기부터 고칠 것."),
    ]


# --------------------------------------------------------------------------- #
#  7. 조립
# --------------------------------------------------------------------------- #
def main():
    t0 = _dt.datetime.now()
    print("=" * 100)
    print("부품별 재질 배정 감사 + 검사기 결함 실측 — CPU 전용 · 기본 동작 무변경")
    print("=" * 100)

    print("\n[1] 재질 물성표")
    mt = material_table()
    div = engine_divergence()

    print("[2] 전 기종 그룹 실측(면적·재질·매몰)")
    fleet = scan_fleet()

    print("[3] 그룹→재질 배정 감사")
    assign = assignment_audit(fleet)

    print("[4] mini2 body 구멍(I5)")
    hole = probe_mini2_hole()

    print("[5] 동일평면 재질 뒤집힘(m4) — 전 기종")
    cop = probe_coplanar_pairs()

    print("[6] uv_sphere 극점(m6)")
    sph = probe_uv_sphere()

    print("[7] 재질 경로 조용한 폴백")
    fb = probe_material_fallbacks()

    print("[8] s1000plus 카본 판 비중")
    s1k = probe_s1000plus_plates()

    print("[9] 나일론 감도")
    nyl = nylon_sensitivity()

    print("[10] dB 어림 · 자체점검 · 발견 목록")
    rfe = rf_estimates(fleet, s1k)
    wp = selftest_weld_poles()
    finds = findings_registry(fleet, s1k, rfe, hole, cop, fb, sph)

    doc = dict(
        _meta=dict(
            generated=t0.isoformat(timespec="seconds"),
            script="benchmark/mesh_inspect_materials_check.py",
            scope="재질 배정 · 검사기 · 프로펠러 **외** 부품(프롭 형상은 별도 라운드)",
            rules=["GPU 미사용(numpy·trimesh CPU)",
                   "코드 기본 동작 무변경 — 수리는 전부 선택 함수(heal_boundary_holes · "
                   "prune_buried_faces)와 선택 인자(geom.uv_sphere(weld_poles=True))",
                   "|Γ| 는 materials.gamma_po(=PO 경로) 기준 · 3.5 GHz"],
            caveat="`power_weight`(A·|Γ|²)는 **σ 가 아니다** — 위상·가림·각도를 무시한 순위 대용치다."),
        material_table=mt,
        engine_divergence=div,
        assignment_audit=assign,
        fleet=fleet,
        mini2_body_hole=hole,
        coplanar_material_flip=cop,
        uv_sphere=sph,
        material_path_fallbacks=fb,
        s1000plus_center_plate=s1k,
        nylon_sensitivity=nyl,
        rf_estimates=rfe,
        selftest_weld_poles=wp,
        findings=finds,
        code_changes=[
            dict(file="src/materials.py", what="`make_material()` 의 모르는-키 폴백에 "
                 "RuntimeWarning + `UNKNOWN_KEY_FALLBACKS` 기록, `strict=True` 선택 인자 추가",
                 default_behaviour="**무변경** — 아는 키는 경고도 안 나고 값도 그대로. "
                                   "모르는 키도 예전과 **같은 값**(plastic)을 돌려준다."),
            dict(file="src/geom.py", what="`uv_sphere(..., weld_poles=True)` 선택 인자 신설 "
                 "(감사 m6) + `__main__` 자체점검이 존재하지 않는 `blade()` 를 불러 NameError 로 "
                 "죽던 두 줄 교체",
                 default_behaviour="**무변경** — `weld_poles=False` 가 기본이고 그때 정점·면 "
                                   "인덱스가 예전과 비트동일하다(selftest_weld_poles 절 참조)."),
            dict(file="benchmark/mesh_inspect_materials_check.py", what="이 파일(신규). 선택 수리 "
                 "도구 `heal_boundary_holes()`·`prune_buried_faces()` 포함",
                 default_behaviour="아무 파이프라인도 이 파일을 import 하지 않는다."),
        ],
        not_touched=dict(
            files=["src/drone_cad.py", "src/cadkit.py", "src/drones.py", "src/mesh_check.py"],
            why="이 라운드가 도는 동안 **다른 라운드가 같은 파일들을 편집 중**이었다"
                "(mtime 이 이 세션 안에서 움직였다). 겹쳐 쓰면 서로의 수정을 지운다. "
                "그래서 A1(s1000plus 판 → deck) · A4(union_group 퇴화면 규칙) · "
                "A7(동일평면 0.1 mm 띄움)은 **수치와 패치 방향만 남기고 안 고쳤다.**"),
    )
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"\n→ {OUT_JSON}  ({os.path.getsize(OUT_JSON)/1024:.0f} KB, "
          f"{(_dt.datetime.now()-t0).total_seconds():.0f} s)")
    return doc


if __name__ == "__main__":
    main()
