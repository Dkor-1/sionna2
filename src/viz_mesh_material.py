# -*- coding: utf-8 -*-
"""
viz_mesh_material.py — **σ 를 굴리는 입력을 그린다: 재질 · 내부 산란체 · 조명/그늘**
==========================================================================================

왜 이 파일이 있나
-----------------
우리 RCS 는 **재질 가중 PO 적분**이다:

    E(û) = Σ_(조명·가시)  |Γ_그룹| · e^{j2k p·û} · d²        σ = (4π/λ²)|E|²

여기서 `|Γ_그룹|` 은 장식이 아니라 **물리 입력**이고, "조명·가시" 게이트는 그 적분의 정의역이다.
  ⚠ 주장의 범위를 정확히: **스톡 Sionna RT 도 전파경로의 가림은 추적한다**(레이트레이서니까).
    없는 것은 **표면 산란적분**이고, 그래서 표적 σ 자체가 창발하지 않는다(rcs_po 서두).
    즉 "게이트가 없다"가 아니라 **게이트를 걸 적분이 없다**가 참인 명제다.
그런데 저장소의 어느 그림도 이 셋을 보여주지 않았다 —
(1) 기체별 재질 면적 구성, (2) 내부 산란체(배터리·PCB)가 **어디에** 앉아 있는지,
(3) 대표 자세에서 **어느 면이 조명되고 어느 면이 가려지는지**.

만드는 것
---------
  outputs/figures/mesh_compare_material_area.png       (a) 7종 재질 면적 구성 — 누적 막대
  outputs/figures/mesh_compare_material_internal.png   (b) 셸 투과 고스트 + **실단면**(내부 산란체 위치)
  outputs/figures/mesh_compare_material_shadow.png     (c) ⭐ 조명(LIT) vs 그늘(SHADOWED)
  outputs/mesh_compare_material.json                   위 세 그림이 읽는 원장(숫자의 유일 출처)

숫자는 어디서 오나 — **전부 코드에서 읽는다**
-----------------------------------------------
  · 재질 배정   : `drones.DRONE_GROUP_MAT`     (부위 → 재질키)
  · |Γ|         : `materials.gamma_po()`        (ITU εr·σ 는 Sionna 에게 물어본 값)
  · 색          : `drones.MATERIAL_COLOR`       (색 = 순수 재질, 저장소 규약)
  · 면적        : 메쉬 삼각형 면적의 직접 합
  · 조명/그늘   : `rcs_sbr._exit_visible()` — **생산 엔진이 쓰는 바로 그 그림자광선**
  손으로 적은 숫자는 없다. 그림은 JSON 을 **디스크에서 다시 읽어** 그린다.

(c) 는 어떻게 재나 — 엔진과 같은 판정, 더 촘촘한 표본
-------------------------------------------------------
생산 SBR(`rcs_sbr_batch`)은 λ/12 광선 격자의 **첫 충돌점만** 적분한다. 그 격자로 면적을
세면 격자 간격(7 mm)보다 작은 부품이 표본에서 빠져 '그늘'로 오해된다. 그래서 여기서는
**면적 계산을 표면 표본에서** 한다:
  ① `rcs_po.mesh_to_points` 와 **같은 바리센트릭 규칙**으로 표면점 P·n̂·ΔA 를 만든다(λ/7).
  ② 조명 게이트 `n̂·û > 0` 는 PO 커널과 동일.
  ③ 가시 판정은 `rcs_sbr._exit_visible()` 그대로 — û 방향 그림자광선 1발, 같은 Mitsuba 씬.
모노스태틱에서 "첫 충돌점"과 "앞면이면서 시선이 뚫린 점"은 같은 집합이다 → **판정은 엔진과
동일**하고, 면적만 격자가 아닌 표면에서 적분된다.

한계(정직 표기)
  · 면적 귀속은 표면 표본 단위로 양자화된다(λ/7 ≈ 12 mm 이하 면은 표본 1개로 대표).
  · 그늘 판정은 **1차 가림**이다. 다중반사로 그늘 안에 들어오는 에너지는 여기 안 나온다.
  · 셸 투과(τ=1−|Γ|²)는 (b) 에서 수치로 적되, (c) 의 LIT/SHADOWED 분류는 **기하 가림**만 쓴다.
  · (c) 오른쪽의 σ 비교는 **이산화가 다른 두 코드**를 견준다(PO 점구름 λ/7 vs SBR 광선격자
    λ/12·jitter 2). 그래서 PO 를 λ/7↔λ/12 로 한 번 더 돌려 그 폭(`discretisation_spread_db`)을
    같이 재고, 그림에 회색 세로선으로 그린다 — 그 선보다 짧은 막대는 효과라고 부르지 않는다
    (실제로 S1000+ 가 그 경우다).

색 규약
-------
  · (a)(b) 색 = **순수 재질** (`MATERIAL_COLOR`, 저장소 규약이라 여기서 새로 만들지 않는다).
    ⚠ 이 팔레트는 protanopia 에서 camera_assembly(주황)↔pcb(초록) 이 OKLab ΔE 2.8 로 붙는다.
      팔레트는 규약이라 못 바꾸므로 **2차 부호화로 보완**한다 — 모든 조각에 직접 라벨,
      같은 색인 plastic↔prop_plastic 은 해칭, 그리고 표 패널(표 뷰 쌍둥이)을 항상 같이 둔다.
  · (c) 색 = **조명 상태**(재질 아님, 그림에 명시). LIT `#eda100` · SHADOWED `#4a3aa7` —
    dataviz 검증 통과(ΔE protan 41.0 / normal 45.9), 뒷면은 중립 회색(=해당 없음).

실행
----
  cd /workspace/sionna
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/viz_mesh_material.py
  ... --only measure        # JSON 만
  ... --only area|internal|shadow
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

#  ⚠ mitsuba/sionna import **전에** 장치를 정한다(CUDA 컨텍스트는 한 번 잡히면 못 바꾼다).
#    SIONNA2_CPU=1 이면 GPU 를 아예 안 보이게 해서 mitsuba 가 llvm(CPU) 변종으로 뜬다 —
#    이 스크립트의 광선 작업은 그림자광선 수십만 발뿐이라 CPU 로 몇 초면 끝나고,
#    GPU 는 병렬로 도는 파이프라인 재생성에 양보한다(benchmark/verify_ambiguity.py 와 같은 규약).
if os.environ.get("SIONNA2_CPU") == "1":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import viz_mesh_gallery as VG                      # noqa: E402  렌더러(직교투영·화가알고리즘) 재사용
from viz_mesh_gallery import (GRAY, draw_mesh, scale_bar,          # noqa: E402
                              set_view, set_view_free, view_basis, _tri_arrays)
import matplotlib.pyplot as plt                    # noqa: E402  (VG 가 vizstyle.use_korean() 을 이미 부름)
import matplotlib.patheffects as pe                 # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Rectangle, FancyArrow, Patch  # noqa: E402

from drones import (DRONES, DRONE_GROUP_MAT, MATERIAL_COLOR, build_drone,   # noqa: E402
                    drone_gamma_map, drone_keys, drone_label)
from materials import MATERIALS, gamma_bulk, gamma_po, material_params      # noqa: E402
from rcs_po import dbsm, mesh_to_points, rcs_from_points                    # noqa: E402
import rcs_sbr as SBR                               # noqa: E402  (여기서 mitsuba 가 뜬다)
import mitsuba as mi                                # noqa: E402  (변종은 rcs_sbr 이 이미 정했다)

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
LEDGER = os.path.join(OUT, "mesh_compare_material.json")

C0 = 299_792_458.0
BANDS = VG.BANDS                                   # LTE / 5G / WiFi — 갤러리와 같은 정의
FC = BANDS["5G"]                                   # 대표 밴드(리포트 헤드라인 밴드)
MESH_SOURCES = VG.MESH_SOURCES
MEASURED = VG.MEASURED                             # 실물 측정 대상 2종

#: 표면 표본 간격 — `rcs_po.drone_rcs_pattern(engine="po")` 의 기본값과 **같은 규칙**(λ/7).
SAMPLE_DIV = 7.0

#: 대표 자세. el 은 저장소가 SBR 검증 내내 쓰는 15°(src/viz_verify_sbr.py).
#: az 는 손으로 고르지 않는다 — `_pick_azimuth()` 가 스윕에서 **중앙값 자세**를 뽑는다.
EL_DEG = 15.0
AZ_SWEEP = np.arange(0.0, 360.0, 5.0)

#: 관측 카메라는 조명 방향에서 **방위 +65°, 고각 25°** 로 비켜 선다.
#: 조명축에 딱 맞춰 보면 정의상 그늘이 하나도 안 보인다 — 비켜 서야 가림이 보인다.
OBS_DAZ, OBS_EL = 65.0, 25.0

#: 조명 상태 색 (재질색과 **다른** 축이다 — 그림에 그렇게 적는다).
#: dataviz 검증: protan ΔE 41.0 · normal ΔE 45.9 · 명도대역/채도 통과.
C_LIT = "#eda100"
C_SHADOW = "#4a3aa7"
C_BACK = "#b9b9b6"                                 # 뒷면 = 해당 없음(중립)

#: 재질을 |Γ| 오름차순으로 — 누적 막대에서 "면적 큰 저반사"가 아래, "고반사"가 위로 쌓인다.
MAT_ORDER = ("prop_plastic", "plastic", "plastic_blue", "pcb", "camera_assembly",
             "carbon", "metal")

#: 같은 색을 쓰는 재질 쌍(plastic ↔ prop_plastic)은 **해칭으로** 가른다.
MAT_HATCH = {"prop_plastic": "///"}

#: 내부 산란체 판정 문턱 — 스윕 전체에서 직접 보이는 면적이 이 값 미만이면 '내부'.
INTERNAL_VIS_MAX = 0.01

#: `DRONE_GROUP_MAT` 설명에 '내부' 라고 **적혀 있는** 그룹. 측정 결과와 대조해서
#: "적힌 것과 실제가 다른" 경우를 원장에 남긴다(조용히 넘어가지 않는다).
DOC_INTERNAL = frozenset(g for g, (_m, ko) in DRONE_GROUP_MAT.items() if "내부" in ko)

INK, INK2 = "#222222", "#555555"

#: 조각 안 글자는 해칭·짙은 색 위에서도 읽혀야 한다 — 얇은 표면색 테두리를 준다.
_HALO = [pe.withStroke(linewidth=2.0, foreground="white")]


# --------------------------------------------------------------------------- #
#  0.  표면 표본 — rcs_po.mesh_to_points 와 같은 규칙 + 면 인덱스
# --------------------------------------------------------------------------- #
def surface_samples(mesh, spacing):
    """(P, n̂, ΔA, face_idx) — `rcs_po.mesh_to_points` 와 **같은 바리센트릭 규칙**.

    왜 그 함수를 그대로 못 쓰나: 그림이 면 단위로 색을 칠하려면 표본이 어느 삼각형에서
    나왔는지가 필요한데 그 함수는 면 인덱스를 안 돌려준다. 규칙이 갈라지지 않도록
    아래에서 두 결과(점 수·면적 합)를 **직접 대조**한다."""
    V = np.asarray(mesh.v, float)
    Ps, Ns, dAs, Fi = [], [], [], []
    for fi, (ia, ib, ic) in enumerate(mesh.f):
        v0, v1, v2 = V[ia], V[ib], V[ic]
        e1, e2 = v1 - v0, v2 - v0
        nrm = np.cross(e1, e2)
        area = 0.5 * np.linalg.norm(nrm)
        if area < 1e-12:
            continue
        nhat = nrm / (2 * area)
        emax = max(np.linalg.norm(e1), np.linalg.norm(e2), np.linalg.norm(v2 - v1))
        n = max(1, int(np.ceil(emax / spacing)))
        ij = [(i, j) for i in range(n) for j in range(n) if (i + 0.5) + (j + 0.5) <= n]
        if not ij:
            ij = [(0, 0)]
        uv = (np.array(ij) + 0.5) / n
        pts = v0 + uv[:, :1] * e1 + uv[:, 1:] * e2
        Ps.append(pts)
        Ns.append(np.tile(nhat, (len(pts), 1)))
        dAs.append(np.full(len(pts), area / len(pts)))
        Fi.append(np.full(len(pts), fi, int))
    return (np.vstack(Ps), np.vstack(Ns), np.concatenate(dAs), np.concatenate(Fi))


def occluder_depth(scene, P, N, u, sel):
    """그늘 점에서 **가림체까지의 거리**[m] 분포.

    왜 재나: 그늘이 진짜 구조물 때문인지, 아니면 두 면이 겹쳐 있어서(z-fighting) 생긴
    수치 인공물인지 갈라 준다. 겹친 면이라면 거리가 광선 오프셋
    (EXIT_CLEARANCE=1e-05 m) 수준으로 붙는다."""
    idx = np.where(sel)[0]
    if idx.size == 0:
        return None
    cs = np.maximum(N[idx] @ u, SBR.EXIT_COSMIN)
    o = P[idx] + (SBR.EXIT_CLEARANCE / cs)[:, None] * u
    d = np.tile(u, (idx.size, 1))
    ray = mi.Ray3f(o=mi.Point3f(*o.T.astype(np.float32)),
                   d=mi.Vector3f(*d.T.astype(np.float32)))
    si = scene.ray_intersect(ray)
    val = np.asarray(si.is_valid()).astype(bool)
    t = np.asarray(mi.Float(si.t))[val]
    if t.size == 0:
        return None
    return dict(n=int(t.size),
                p01_mm=float(np.percentile(t, 1) * 1000.0),
                p50_mm=float(np.percentile(t, 50) * 1000.0),
                p99_mm=float(np.percentile(t, 99) * 1000.0))


def lit_mask(scene, P, N, dA, u):
    """대표 시선 û 에서 (앞면, 조명·가시) 두 마스크.

    조명 게이트 `n̂·û>0` 는 PO 커널과 같고, 가시 판정은 생산 엔진의
    `rcs_sbr._exit_visible()`(그림자광선 1발) 을 **그대로** 부른다."""
    front = (N @ u) > 1e-6
    lit = np.zeros(len(dA), bool)
    idx = np.where(front)[0]
    if idx.size:
        lit[idx] = SBR._exit_visible(scene, P[idx], N[idx], u)
    return front, lit


# --------------------------------------------------------------------------- #
#  1.  계측 — outputs/mesh_compare_material.json
# --------------------------------------------------------------------------- #
def _mat_of(group: str) -> str:
    return DRONE_GROUP_MAT[group][0]


def _mtime(p):
    return os.path.getmtime(p) if os.path.exists(p) else None


def _stamp(ts):
    return None if ts is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _material_ledger() -> dict:
    """재질 표 — |Γ| 를 **materials.py 에서 읽는다**(손으로 적지 않는다)."""
    used = {}
    for grp, (mat, ko) in DRONE_GROUP_MAT.items():
        used.setdefault(mat, []).append(grp)
    out = {}
    for mat, groups in used.items():
        er, sg, S = material_params(mat, FC)
        gp = {b: float(gamma_po(mat, f)) for b, f in BANDS.items()}
        gb = float(gamma_bulk(mat, FC))
        out[mat] = dict(
            groups=sorted(groups),
            gamma_po=gp, gamma_po_5g=gp["5G"], gamma_bulk_5g=gb,
            effective_override=("gamma_po" in MATERIALS[mat]),
            delta_vs_bulk_db=float(20 * np.log10(gp["5G"] / max(gb, 1e-12))),
            eps_r_5g=float(er), sigma_S_per_m_5g=float(sg), scattering_S=float(S),
            source=("ITU-R P.2040 via Sionna" if "itu" in MATERIALS[mat] else "custom"),
            color_rgb=[float(c) for c in MATERIAL_COLOR[mat]],
            note_ko=MATERIALS[mat]["note"].replace("\n", " "))
    return out


def _pick_azimuth(mean_curve) -> float:
    """대표 방위각 = **중앙값 자세**. 7종 평균 그늘비율 곡선에서 그 곡선의 중앙값에
    가장 가까운 방위를 고른다 — 손으로 고르지 않으므로 '보기 좋은 각도' 편향이 없다."""
    med = float(np.median(mean_curve))
    return float(AZ_SWEEP[int(np.argmin(np.abs(np.asarray(mean_curve) - med)))])


def measure(keys=None, verbose=True) -> dict:
    """7종의 재질 면적 · 내부 산란체 · 조명/그늘 · σ(가림 유무)를 재서 원장을 만든다."""
    keys = list(keys or drone_keys())
    t0 = time.time()
    lam = C0 / FC
    spacing = lam / SAMPLE_DIV
    gm_key = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}     # 그룹 → 재질키(엔진 입력 형식)

    src_mt = {p: _stamp(_mtime(os.path.join(ROOT, p))) for p in MESH_SOURCES}
    newest = max(v for v in (_mtime(os.path.join(ROOT, p)) for p in MESH_SOURCES) if v)

    air, cache = {}, {}
    for key in keys:
        spec = DRONES[key]
        mesh = build_drone(spec)
        V = np.asarray(mesh.v, float)
        F = np.asarray(mesh.f, int)
        G = np.asarray(mesh.g)
        _, _, farea = _tri_arrays(V, F)
        gam = drone_gamma_map(spec, FC)

        # --- 재질 면적 구성 ------------------------------------------------- #
        groups = {}
        for g in sorted(set(mesh.g)):
            sel = G == g
            groups[g] = dict(material=_mat_of(g), desc_ko=DRONE_GROUP_MAT[g][1],
                             gamma_po_5g=float(gam[g]), n_faces=int(sel.sum()),
                             area_m2=float(farea[sel].sum()))
        area_tot = float(farea.sum())
        gA_tot = float(sum(v["area_m2"] * v["gamma_po_5g"] for v in groups.values()))
        mats = {}
        for g, v in groups.items():
            m = mats.setdefault(v["material"], dict(area_m2=0.0, gamma_area_m2=0.0, groups=[]))
            m["area_m2"] += v["area_m2"]
            m["gamma_area_m2"] += v["area_m2"] * v["gamma_po_5g"]
            m["groups"].append(g)
        for m, v in mats.items():
            v["groups"] = sorted(v["groups"])
            v["gamma_po_5g"] = float(gamma_po(m, FC))
            v["area_share"] = v["area_m2"] / area_tot
            v["gamma_share"] = v["gamma_area_m2"] / gA_tot

        # --- 표면 표본 + Mitsuba 씬 ------------------------------------------ #
        P, N, dA, FI = surface_samples(mesh, spacing)
        _Pp, _Np, dAp = mesh_to_points(mesh, spacing)            # 규칙 일치 대조용
        scene, _shapes, _gam = SBR._mi_scene_from_mesh(mesh, gm_key, FC)
        sample_check = dict(
            n_points=int(len(dA)), n_points_rcs_po=int(len(dAp)),
            area_sum_m2=float(dA.sum()), area_sum_rcs_po_m2=float(dAp.sum()),
            mesh_area_m2=area_tot,
            identical=bool(len(dA) == len(dAp) and abs(dA.sum() - dAp.sum()) < 1e-12))

        # --- 방위 스윕: 그룹별 조명면적/가시면적 ------------------------------ #
        gsel = {g: (G[FI] == g) for g in groups}
        sw_front = {g: [] for g in groups}
        sw_lit = {g: [] for g in groups}
        for a in AZ_SWEEP:
            u = SBR._look(a, EL_DEG)
            front, lit = lit_mask(scene, P, N, dA, u)
            for g, s in gsel.items():
                sw_front[g].append(float(dA[s & front].sum()))
                sw_lit[g].append(float(dA[s & lit].sum()))
        for g in groups:
            fr = np.asarray(sw_front[g]); li = np.asarray(sw_lit[g])
            vis = li / np.maximum(fr, 1e-15)
            groups[g]["visible_frac_sweep"] = dict(
                min=float(vis.min()), max=float(vis.max()), mean=float(vis.mean()))
            groups[g]["internal"] = bool(vis.max() < INTERNAL_VIS_MAX)

        internal_groups = sorted(g for g in groups if groups[g]["internal"])
        doc_only = sorted(DOC_INTERNAL & set(groups) - set(internal_groups))
        meas_only = sorted(set(internal_groups) - DOC_INTERNAL)
        ext_groups = sorted(g for g in groups if not groups[g]["internal"])
        F_all = np.array([sum(sw_front[g][i] for g in groups) for i in range(len(AZ_SWEEP))])
        L_all = np.array([sum(sw_lit[g][i] for g in groups) for i in range(len(AZ_SWEEP))])
        F_ext = np.array([sum(sw_front[g][i] for g in ext_groups) for i in range(len(AZ_SWEEP))])
        L_ext = np.array([sum(sw_lit[g][i] for g in ext_groups) for i in range(len(AZ_SWEEP))])
        cache[key] = dict(mesh=mesh, V=V, F=F, G=G, P=P, N=N, dA=dA, FI=FI, scene=scene,
                          farea=farea, shadow_ext=1.0 - L_ext / F_ext,
                          shadow_all=1.0 - L_all / F_all)

        air[key] = dict(
            label=drone_label(key), name=spec.name, measured=bool(key in MEASURED),
            n_tris=int(mesh.n_tris()), surface_area_m2=area_tot,
            gamma_area_m2=gA_tot,
            gamma_area_ratio=float(gA_tot / area_tot),
            groups=groups, materials=mats, sample_check=sample_check,
            internal=dict(
                groups=internal_groups,
                rule=f"방위 스윕({len(AZ_SWEEP)}각, el={EL_DEG}°) 전체에서 직접 보이는 "
                     f"앞면 면적비가 {INTERNAL_VIS_MAX:.0%} 미만인 그룹",
                area_m2=float(sum(groups[g]["area_m2"] for g in internal_groups)),
                area_share=float(sum(groups[g]["area_m2"] for g in internal_groups) / area_tot),
                gamma_share=float(sum(groups[g]["area_m2"] * groups[g]["gamma_po_5g"]
                                      for g in internal_groups) / gA_tot),
                max_visible_frac=float(max((groups[g]["visible_frac_sweep"]["max"]
                                            for g in internal_groups), default=0.0)),
                vs_documented=dict(
                    documented=sorted(DOC_INTERNAL & set(groups)),
                    documented_but_visible=doc_only,
                    visible_in_doc_but_enclosed=meas_only,
                    note=("DRONE_GROUP_MAT 설명에 '내부' 라고 적힌 그룹과 측정 결과의 차이. "
                          "열린 프레임(셸 없음)에서는 배터리·PCB 가 실제로 노출되므로 "
                          "documented_but_visible 이 비어 있지 않은 것이 정상이다."))),
            shadow_sweep=dict(
                az_deg=[float(a) for a in AZ_SWEEP], el_deg=EL_DEG,
                shadow_frac_all=[float(x) for x in (1.0 - L_all / F_all)],
                shadow_frac_exterior=[float(x) for x in (1.0 - L_ext / F_ext)]))
        if verbose:
            print(f"  [material] {key:12s} area={area_tot:.4f} m2  |G|A/A={gA_tot/area_tot:.3f}  "
                  f"internal={internal_groups}  "
                  f"shadow_ext={100*(1-L_ext/F_ext).mean():.1f}% (mean over sweep)")

    # --- 대표 자세: 7종 평균 그늘비율 곡선의 **중앙값 자세** ------------------ #
    mean_curve = np.mean([cache[k]["shadow_ext"] for k in keys], axis=0)
    az_rep = _pick_azimuth(mean_curve)
    ia = int(np.argmin(np.abs(AZ_SWEEP - az_rep)))
    u_rep = SBR._look(az_rep, EL_DEG)

    # --- 대표 자세의 그룹별 조명/그늘 + σ 3종 -------------------------------- #
    for key in keys:
        c = cache[key]
        front, lit = lit_mask(c["scene"], c["P"], c["N"], c["dA"], u_rep)
        c["front"], c["lit"] = front, lit
        Gp = c["G"][c["FI"]]
        per = {}
        for g in air[key]["groups"]:
            s = Gp == g
            fa = float(c["dA"][s & front].sum())
            la = float(c["dA"][s & lit].sum())
            per[g] = dict(front_area_m2=fa, lit_area_m2=la,
                          shadow_frac=float(1.0 - la / fa) if fa > 0 else None)
        depth = occluder_depth(c["scene"], c["P"], c["N"], u_rep, front & ~lit)
        fa = float(c["dA"][front].sum()); la = float(c["dA"][lit].sum())
        ext = [g for g in air[key]["groups"] if not air[key]["groups"][g]["internal"]]
        fe = float(sum(per[g]["front_area_m2"] for g in ext))
        le = float(sum(per[g]["lit_area_m2"] for g in ext))

        t1 = time.time()
        sb_pen = np.asarray(SBR.rcs_sbr_batch(c["mesh"], gm_key, FC, az_deg=AZ_SWEEP,
                                              el_deg=EL_DEG, penetrate=True,
                                              cache_key=(key, "pen")), float)
        sb_opq = np.asarray(SBR.rcs_sbr_batch(c["mesh"], gm_key, FC, az_deg=AZ_SWEEP,
                                              el_deg=EL_DEG, penetrate=False,
                                              cache_key=(key, "opq")), float)
        gmap = drone_gamma_map(DRONES[key], FC)
        Pw, Nw, dAw, w = mesh_to_points(c["mesh"], spacing, gamma=gmap)
        po = np.asarray(rcs_from_points(Pw, Nw, dAw, FC, AZ_SWEEP, EL_DEG, w=w), float)
        #  ⚠ 대조군 — PO 와 SBR 은 **이산화가 다르다**(점구름 λ/7 vs 광선격자 λ/12+jitter).
        #    그 차이가 만드는 바닥잡음을 재 두지 않으면 "가림 효과"라고 부른 것이 사실은
        #    이산화 잡음일 수 있다. PO 를 두 간격으로 돌려 그 폭을 원장에 남긴다.
        Pw2, Nw2, dAw2, w2 = mesh_to_points(c["mesh"], lam / 12.0, gamma=gmap)
        po12 = np.asarray(rcs_from_points(Pw2, Nw2, dAw2, FC, AZ_SWEEP, EL_DEG, w=w2), float)

        air[key]["shadow"] = dict(
            az_deg=az_rep, el_deg=EL_DEG,
            front_area_m2=fa, lit_area_m2=la, shadow_frac=float(1.0 - la / fa),
            exterior_front_area_m2=fe, exterior_lit_area_m2=le,
            exterior_shadow_frac=float(1.0 - le / fe),
            occluder_depth=depth,
            occluder_depth_note=("그늘 표본에서 가림체까지의 거리 분포 [mm]. "
                                 "1 %ile 이 광선 오프셋(0.01 mm)보다 훨씬 크면 "
                                 "그늘은 겹친 면(z-fighting)이 아니라 실제 구조물 때문이다."),
            per_group=per)
        air[key]["sigma"] = dict(
            fc_hz=FC, el_deg=EL_DEG, n_az=int(len(AZ_SWEEP)),
            po_no_occlusion_dbsm=float(dbsm(po.mean())),
            po_no_occlusion_lambda12_dbsm=float(dbsm(po12.mean())),
            discretisation_spread_db=float(abs(dbsm(po.mean()) - dbsm(po12.mean()))),
            sbr_occluded_opaque_dbsm=float(dbsm(sb_opq.mean())),
            sbr_production_dbsm=float(dbsm(sb_pen.mean())),
            d_occlusion_db=float(dbsm(po.mean()) - dbsm(sb_opq.mean())),
            d_shell_transmission_db=float(dbsm(sb_pen.mean()) - dbsm(sb_opq.mean())),
            d_total_db=float(dbsm(po.mean()) - dbsm(sb_pen.mean())),
            runtime_s=round(time.time() - t1, 1),
            definition=("방위평균 σ. po_no_occlusion=rcs_po 점구름 PO(가림 없음, λ/7), "
                        "sbr_occluded_opaque=SBR 1-bounce 가림 O·셸 투과 X, "
                        "sbr_production=SBR 가림 O·셸 투과 O(=drone_rcs_pattern 기본)"),
            caveat=("PO 와 SBR 은 이산화가 다르다(점구름 λ/7 vs 광선격자 λ/12·jitter 2). "
                    "discretisation_spread_db 는 PO 를 λ/7↔λ/12 로 돌렸을 때의 폭이며, "
                    "d_occlusion_db 가 이보다 작으면 가림 효과라고 부를 수 없다."))
        if verbose:
            s = air[key]["sigma"]
            print(f"  [sigma]    {key:12s} PO {s['po_no_occlusion_dbsm']:7.2f} → "
                  f"SBR(opaque) {s['sbr_occluded_opaque_dbsm']:7.2f} → "
                  f"SBR(prod) {s['sbr_production_dbsm']:7.2f} dBsm   "
                  f"가림 {s['d_occlusion_db']:+.2f} dB / 투과 {s['d_shell_transmission_db']:+.2f} dB "
                  f"(이산화폭 {s['discretisation_spread_db']:.2f} dB, {s['runtime_s']} s)")

    matled = _material_ledger()
    order = sorted(air, key=lambda k: air[k]["surface_area_m2"])
    J = dict(
        _meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            generator="src/viz_mesh_material.py :: measure()",
            purpose="재질 면적 구성 · 내부 산란체 · 조명/그늘 — σ 를 굴리는 물리 입력의 원장",
            n_airframes=len(air),
            fc_hz=FC, bands_ghz={k: v / 1e9 for k, v in BANDS.items()},
            mesh_sources=src_mt, mesh_source_newest=_stamp(newest),
            sampling=dict(rule="rcs_po.mesh_to_points 와 같은 바리센트릭 규칙",
                          spacing_m=float(spacing), spacing_rule=f"lambda/{SAMPLE_DIV:g} @ 5G",
                          all_airframes_match_rcs_po=bool(
                              all(air[k]["sample_check"]["identical"] for k in air))),
            aspect=dict(el_deg=EL_DEG, az_deg=az_rep,
                        rule="7종 평균 외부 그늘비율 곡선의 중앙값에 가장 가까운 방위 "
                             "(손으로 고르지 않는다)",
                        rule_en="the azimuth whose 7-airframe mean outer-skin shadow fraction "
                                "is closest to the median of that curve (not hand-picked)",
                        sweep_n=int(len(AZ_SWEEP)), sweep_step_deg=5.0,
                        mean_shadow_frac_at_aspect=float(mean_curve[ia]),
                        mean_shadow_frac_median=float(np.median(mean_curve)),
                        observer=dict(d_az_deg=OBS_DAZ, el_deg=OBS_EL,
                                      why="조명축 위에서 보면 정의상 그늘이 안 보인다")),
            visibility=dict(
                engine="rcs_sbr._exit_visible() — 생산 SBR 이 쓰는 그림자광선 그대로",
                gate="조명 n̂·û>0 (PO 커널과 동일) AND û 방향 광선이 뚫림",
                equivalence="모노스태틱에서 '첫 충돌점'과 '앞면 & 시선 뚫림'은 같은 집합",
                limits=["면적 귀속은 표면 표본 단위로 양자화(λ/7)",
                        "1차 가림만 — 다중반사로 그늘에 들어오는 에너지는 안 나옴",
                        "셸 투과 τ 는 (b) 에 수치로만, LIT/SHADOWED 분류는 기하 가림만"]),
            shell_transmission=dict(
                shell_groups=sorted(SBR._DIELECTRIC_SHELLS),
                gamma_shell=float(gamma_po("plastic", FC)),
                tau_round_trip=float(1.0 - gamma_po("plastic", FC) ** 2),
                tau_db=float(20 * np.log10(1.0 - gamma_po("plastic", FC) ** 2)),
                note="rcs_sbr_batch(penetrate=True) 가 셸 뒤 금속에 곱하는 왕복 투과 진폭"),
            palette=dict(
                material="drones.MATERIAL_COLOR (저장소 규약 — 색 = 순수 재질)",
                material_cvd_warning="protanopia 에서 camera_assembly(#e6800f)↔pcb(#199940) "
                                     "OKLab ΔE 2.8 — 팔레트는 규약이라 유지하고 직접 라벨·"
                                     "해칭·표 패널로 2차 부호화한다",
                illumination=dict(lit=C_LIT, shadowed=C_SHADOW, backface=C_BACK,
                                  validated="protan ΔE 41.0 / normal ΔE 45.9 / 명도·채도 통과")),
            figures=dict(area="outputs/figures/mesh_compare_material_area.png",
                         internal="outputs/figures/mesh_compare_material_internal.png",
                         shadow="outputs/figures/mesh_compare_material_shadow.png"),
            runtime_s=round(time.time() - t0, 1)),
        materials=matled,
        order_by_area=order,
        summary=dict(
            shadow_frac_at_aspect={k: air[k]["shadow"]["shadow_frac"] for k in air},
            exterior_shadow_frac_at_aspect={k: air[k]["shadow"]["exterior_shadow_frac"]
                                            for k in air},
            internal_groups={k: air[k]["internal"]["groups"] for k in air},
            internal_vs_documented={k: air[k]["internal"]["vs_documented"] for k in air},
            occluder_depth_p01_mm={k: (air[k]["shadow"]["occluder_depth"] or {}).get("p01_mm")
                                   for k in air},
            d_occlusion_db={k: air[k]["sigma"]["d_occlusion_db"] for k in air},
            discretisation_spread_db={k: air[k]["sigma"]["discretisation_spread_db"] for k in air},
            occlusion_above_noise={k: bool(air[k]["sigma"]["d_occlusion_db"] >
                                           air[k]["sigma"]["discretisation_spread_db"])
                                   for k in air},
            d_total_db={k: air[k]["sigma"]["d_total_db"] for k in air}),
        airframes=air)

    partial = sorted(keys) != sorted(drone_keys())
    if partial:
        print(f"  ⚠ 부분 계측({len(air)}/{len(DRONES)}종) — {os.path.basename(LEDGER)} 는 "
              f"덮어쓰지 않는다(원장이 기체를 잃지 않도록). 그림만 이 결과로 그린다.")
        return J, cache
    os.makedirs(OUT, exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"  📒 outputs/mesh_compare_material.json  ({len(air)}종, {J['_meta']['runtime_s']} s)")
    return J, cache


# --------------------------------------------------------------------------- #
#  2.  공통 그림 도우미
# --------------------------------------------------------------------------- #
def _load(path=LEDGER):
    if not os.path.exists(path):
        raise SystemExit(f"{path} 이 없다 — `--only measure` 를 먼저 돌릴 것")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _geom(key):
    """그림용 메쉬(캐시 없을 때 다시 만든다)."""
    mesh = build_drone(DRONES[key])
    V = np.asarray(mesh.v, float)
    return mesh, V, np.asarray(mesh.f, int), np.asarray(mesh.g)


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    p = os.path.join(FIG, name)
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/{name}")
    return p


def _prov(fig, J, extra=""):
    m = J["_meta"]
    fig.text(0.008, 0.010,
             f"Mesh rebuilt from {' + '.join(MESH_SOURCES[:2])} (newest edit "
             f"{m['mesh_source_newest']})  ·  material assignment from drones.DRONE_GROUP_MAT, "
             f"|G| from materials.gamma_po()  ·  every number injected from "
             f"outputs/mesh_compare_material.json, generated {m['generated']}"
             + (f"  ·  {extra}" if extra else ""),
             fontsize=7.4, color=GRAY, ha="left")


def _mat_sort(mats):
    """재질을 |Γ| 오름차순(=MAT_ORDER)으로. 목록에 없는 재질은 뒤에 알파벳순."""
    known = [m for m in MAT_ORDER if m in mats]
    return known + sorted(m for m in mats if m not in MAT_ORDER)


# --------------------------------------------------------------------------- #
#  3.  (a) 재질 면적 구성
# --------------------------------------------------------------------------- #
def fig_area(J, outdir=FIG):
    """7종 나란히: 부위별 누적 면적 · 재질 점유율 · **|Γ| 가중 점유율** · 재질표."""
    A = J["airframes"]
    keys = [k for k in J["order_by_area"] if k in A]
    ML = J["materials"]
    x = np.arange(len(keys))

    fig = plt.figure(figsize=(19.0, 11.0))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.30, 1.0, 1.0], height_ratios=[1.0, 0.90],
                          left=0.052, right=0.988, top=0.845, bottom=0.088,
                          wspace=0.20, hspace=0.30)

    # --- (a) 절대 면적, 부위(그룹) 단위로 쌓되 색은 재질 --------------------- #
    axA = fig.add_subplot(gs[0, 0])
    gapf = 0.004                                  # 조각 사이 표면색 틈(2 px 규약)
    top = max(A[k]["surface_area_m2"] for k in keys)
    for i, k in enumerate(keys):
        g = A[k]["groups"]
        order = sorted(g, key=lambda q: (MAT_ORDER.index(g[q]["material"])
                                         if g[q]["material"] in MAT_ORDER else 99,
                                         -g[q]["area_m2"]))
        y, last = 0.0, -1e9
        for q in order:
            h = g[q]["area_m2"]
            mat = g[q]["material"]
            axA.bar(i, max(h - gapf * top, 0.35 * h), bottom=y, width=0.66,
                    color=MATERIAL_COLOR[mat], edgecolor="none",
                    hatch=MAT_HATCH.get(mat), zorder=2)
            #  들어가는 조각만 직접 라벨한다 — 그리고 **직전 라벨과 겹치지 않을 때만**
            #  (인접한 두 조각이 각각 문턱을 넘어도 글자 높이보다 가까울 수 있다).
            yc = y + h / 2
            if h > 0.045 * top and (yc - last) > 0.052 * top:
                axA.text(i, yc, q, ha="center", va="center", fontsize=8.0, zorder=3,
                         color=("#f5f5f5" if mat == "carbon" else INK),
                         path_effects=(None if mat == "carbon" else _HALO))
                last = yc
            y += h
        axA.text(i, y + 0.018 * top, f"{y:.3f}", ha="center", va="bottom",
                 fontsize=9.6, fontweight="bold", color=INK)
    axA.set_xticks(x, [A[k]["label"] for k in keys], rotation=32, ha="right", fontsize=9.0)
    axA.set_ylabel("Mesh surface area  [m$^2$]", fontsize=10.4)
    axA.set_ylim(0, top * 1.16)
    axA.set_title("Surface area by part group, coloured by material class\n"
                  "(thin gap between segments — segments with room are labelled)",
                  fontsize=11.2, color=INK, pad=7)
    axA.grid(axis="y", lw=0.5, color="#e6e6e6", zorder=0)
    axA.set_axisbelow(True)
    for s in ("top", "right"):
        axA.spines[s].set_visible(False)

    # --- (b) 면적 점유율 (재질 단위, 100 %) ---------------------------------- #
    axB = fig.add_subplot(gs[0, 1])
    mats_all = _mat_sort({m for k in keys for m in A[k]["materials"]})
    for i, k in enumerate(keys):
        y = 0.0
        for m in mats_all:
            v = A[k]["materials"].get(m)
            if not v:
                continue
            h = 100.0 * v["area_share"]
            axB.bar(i, max(h - 0.45, 0.35 * h), bottom=y, width=0.66, color=MATERIAL_COLOR[m],
                    edgecolor="none", hatch=MAT_HATCH.get(m), zorder=2)
            if h > 7.0:
                axB.text(i, y + h / 2, f"{h:.0f}", ha="center", va="center", fontsize=8.2,
                         color=("#f5f5f5" if m == "carbon" else INK), zorder=3,
                         path_effects=(None if m == "carbon" else _HALO))
            y += h
    axB.set_xticks(x, [A[k]["label"] for k in keys], rotation=32, ha="right", fontsize=8.8)
    axB.set_ylabel("Share of surface area  [%]", fontsize=10.4)
    axB.set_ylim(0, 104)
    pl_area = [100 * sum(A[k]["materials"][mm]["area_share"]
                         for mm in ("plastic", "prop_plastic") if mm in A[k]["materials"])
               for k in keys]
    axB.set_title(f"Where the area is\n(plastic + propellers: "
                  f"{min(pl_area):.0f}\u2013{max(pl_area):.0f} % of the skin)",
                  fontsize=11.2, color=INK, pad=7)
    axB.grid(axis="y", lw=0.5, color="#e6e6e6", zorder=0)
    axB.set_axisbelow(True)
    for s in ("top", "right"):
        axB.spines[s].set_visible(False)

    # --- (c) |Γ| 가중 점유율 — PO 적분에 실제로 들어가는 몫 ------------------ #
    axC = fig.add_subplot(gs[0, 2])
    for i, k in enumerate(keys):
        y = 0.0
        for m in mats_all:
            v = A[k]["materials"].get(m)
            if not v:
                continue
            h = 100.0 * v["gamma_share"]
            axC.bar(i, max(h - 0.45, 0.35 * h), bottom=y, width=0.66, color=MATERIAL_COLOR[m],
                    edgecolor="none", hatch=MAT_HATCH.get(m), zorder=2)
            if h > 7.0:
                axC.text(i, y + h / 2, f"{h:.0f}", ha="center", va="center", fontsize=8.2,
                         color=("#f5f5f5" if m == "carbon" else INK), zorder=3,
                         path_effects=(None if m == "carbon" else _HALO))
            y += h
    axC.set_xticks(x, [A[k]["label"] for k in keys], rotation=32, ha="right", fontsize=8.8)
    axC.set_ylabel(r"Share of $\Sigma\,|\Gamma|\,A$  [%]", fontsize=10.4)
    axC.set_ylim(0, 104)
    pl_g = [100 * sum(A[k]["materials"][mm]["gamma_share"]
                      for mm in ("plastic", "prop_plastic") if mm in A[k]["materials"])
            for k in keys]
    axC.set_title("Where the reflected amplitude comes from\n(the same plastic: "
                  f"{min(pl_g):.0f}\u2013{max(pl_g):.0f} % of "
                  r"$\Sigma|\Gamma|A$)",
                  fontsize=11.2, color=INK, pad=7)
    axC.grid(axis="y", lw=0.5, color="#e6e6e6", zorder=0)
    axC.set_axisbelow(True)
    for s in ("top", "right"):
        axC.spines[s].set_visible(False)

    # --- (d) 재질표 = 표 뷰 쌍둥이 (CVD 보완 · 색만으로 읽지 않게) ----------- #
    axT = fig.add_subplot(gs[1, :])
    axT.set_axis_off()
    rows = mats_all
    axT.set_xlim(0, 1)
    axT.set_ylim(-2.4, len(rows) + 1.6)
    cols = [("material", 0.040, "left"), ("part groups", 0.150, "left"),
            (r"$\varepsilon_r$", 0.400, "right"), (r"$\sigma$ [S/m]", 0.470, "right"),
            (r"$|\Gamma|$ bulk", 0.556, "right"),
            (r"$|\Gamma|$ LTE", 0.630, "right"), (r"$|\Gamma|$ 5G", 0.694, "right"),
            (r"$|\Gamma|$ WiFi", 0.762, "right"),
            ("area, 7 airframes", 0.876, "right"),
            (r"$\Sigma|\Gamma|A$ share", 0.988, "right")]
    for t, xx, ha in cols:
        axT.text(xx, len(rows) + 0.62, t, fontsize=8.8, color=GRAY, ha=ha)
    axT.plot([0, 1], [len(rows) + 0.24] * 2, color="#d8d8d8", lw=0.8)
    tot_area = sum(A[k]["surface_area_m2"] for k in keys)
    tot_gA = sum(A[k]["gamma_area_m2"] for k in keys)
    for i, m in enumerate(rows):
        y = len(rows) - 1 - i
        ml = ML[m]
        a_m = sum(A[k]["materials"][m]["area_m2"] for k in keys if m in A[k]["materials"])
        g_m = sum(A[k]["materials"][m]["gamma_area_m2"] for k in keys if m in A[k]["materials"])
        axT.add_patch(Rectangle((0.004, y + 0.18), 0.028, 0.58,
                                facecolor=MATERIAL_COLOR[m], edgecolor="#888", lw=0.5,
                                hatch=MAT_HATCH.get(m)))
        axT.text(0.040, y + 0.47, m, fontsize=9.2, va="center", color=INK)
        axT.text(0.150, y + 0.47, ", ".join(ml["groups"]), fontsize=8.6, va="center", color=INK2)
        axT.text(0.400, y + 0.47, f"{ml['eps_r_5g']:.2f}", fontsize=9.0, va="center", ha="right")
        axT.text(0.470, y + 0.47, f"{ml['sigma_S_per_m_5g']:.4g}", fontsize=9.0,
                 va="center", ha="right")
        axT.text(0.556, y + 0.47, f"{ml['gamma_bulk_5g']:.3f}", fontsize=9.0,
                 va="center", ha="right", color=INK2)
        for b, xx in (("LTE", 0.630), ("5G", 0.694), ("WiFi", 0.762)):
            axT.text(xx, y + 0.47, f"{ml['gamma_po'][b]:.3f}", fontsize=9.0,
                     va="center", ha="right",
                     fontweight=("bold" if b == "5G" else "normal"))
        axT.text(0.876, y + 0.47, f"{a_m:.4f} m2  ({100*a_m/tot_area:4.1f} %)",
                 fontsize=9.0, va="center", ha="right")
        axT.text(0.988, y + 0.47, f"{100*g_m/tot_gA:4.1f} %", fontsize=9.0,
                 va="center", ha="right", fontweight="bold")
    axT.text(0.0, -0.55,
             "Table view of the same data — the material is named, never colour-alone.  "
             r"$|\Gamma|$ bulk is the semi-infinite Fresnel value from ($\varepsilon_r$, $\sigma$); "
             r"$|\Gamma|$ per band is what the PO integral uses, and it differs from bulk only where "
             "materials.py records a reason — thin-shell interference (plastic, prop_plastic),\n"
             "woven-fibre apertures (carbon), a composite assembly (camera, pcb).  "
             "prop_plastic is the same ABS/PC as plastic — identical colour, hatched here, and only its "
             "effective thin-blade $|\\Gamma|$ differs.\n"
             r"$\Sigma|\Gamma|A$ is incoherent bookkeeping: it says which materials supply the "
             r"amplitude, not what $\sigma$ is — the PO integral adds those contributions with phase, "
             "and the shadow figure then removes whatever the illuminator cannot see.",
             fontsize=8.4, color=INK2, va="top")
    axT.set_title("Material table — also the legend for every panel above.  Values read from "
                  "materials.MATERIALS and materials.gamma_po(), not typed in",
                  fontsize=11.2, color=INK, pad=8, loc="left")

    fig.suptitle("What the airframes are made of — and what that does to the PO integral",
                 fontsize=17.0, fontweight="bold", y=0.972)
    cond = [100 * sum(A[k]["materials"][mm]["gamma_share"] for mm in A[k]["materials"]
                      if mm not in ("plastic", "prop_plastic")) for k in keys]
    fig.text(0.5, 0.918,
             "Our RCS is a material-weighted physical-optics integral, so the material map is a "
             f"physical input, not decoration. Plastic and propellers are {min(pl_area):.0f}"
             f"\u2013{max(pl_area):.0f} % of the skin but only {min(pl_g):.0f}\u2013{max(pl_g):.0f} % "
             r"of $\Sigma|\Gamma|A$; the conducting groups"
             "\n"
             f"(metal, carbon, camera, PCB) invert that and carry {min(cond):.0f}\u2013{max(cond):.0f} %. "
             "The middle panel is area, the right panel is the same area weighted by "
             r"$|\Gamma|$ — the quantity that enters $E(\hat u)=\Sigma|\Gamma|\,"
             r"e^{j2k\,p\cdot\hat u}\,d^2$.",
             ha="center", fontsize=11.0, color="#333", linespacing=1.5)
    _prov(fig, J)
    return _save(fig, "mesh_compare_material_area.png")


# --------------------------------------------------------------------------- #
#  4.  (b) 내부 산란체 — 고스트 + 실단면
# --------------------------------------------------------------------------- #
def _section_segments(V, F, G, axis=1, value=0.0):
    """평면 (축=value) 과 삼각형의 교선. 반환: (segs (n,2,3), groups (n,))."""
    d = V[:, axis] - value
    dv = d[F]
    npos = (dv > 0).sum(1)
    idx = np.where((npos == 1) | (npos == 2))[0]
    segs, grps = [], []
    for i in idx:
        a, dd = F[i], dv[i]
        pts = []
        for j in range(3):
            k = (j + 1) % 3
            if (dd[j] > 0) != (dd[k] > 0):
                t = dd[j] / (dd[j] - dd[k])
                pts.append(V[a[j]] + t * (V[a[k]] - V[a[j]]))
        if len(pts) >= 2:
            segs.append([pts[0], pts[1]])
            grps.append(G[i])
    return np.asarray(segs, float).reshape(-1, 2, 3), np.asarray(grps, object)


def fig_internal(J, outdir=FIG):
    """셸을 반투명으로 죽여 내부 산란체를 드러내고, y=0 실단면으로 **위치**를 못 박는다."""
    A = J["airframes"]
    keys = [k for k in J["order_by_area"] if k in A]
    m = J["_meta"]
    sh = m["shell_transmission"]
    n = len(keys)

    fig = plt.figure(figsize=(19.4, 11.8))
    outer = fig.add_gridspec(3, 1, height_ratios=[1.0, 0.80, 0.72],
                             left=0.028, right=0.988, top=0.822, bottom=0.135, hspace=0.20)
    g0 = outer[0].subgridspec(1, n, wspace=0.05)
    g1 = outer[1].subgridspec(1, n, wspace=0.07)
    g2 = outer[2].subgridspec(1, n, wspace=0.62)

    for i, k in enumerate(keys):
        rec = A[k]
        mesh, V, F, G = _geom(k)
        cen = 0.5 * (V.min(0) + V.max(0))
        Vc = V - cen
        internal = set(rec["internal"]["groups"])
        rgb = np.asarray([MATERIAL_COLOR[rec["groups"][g]["material"]] for g in mesh.g], float)
        isin = np.asarray([g in internal for g in mesh.g], bool)

        # --- 행 1: 고스트 iso -------------------------------------------------- #
        ax = fig.add_subplot(g0[0, i])
        b = view_basis(20.0, -58.0)
        half = VG.common_half(V, cen, views=((None, 20.0, -58.0, None),), fill=0.62)
        #  내부를 **먼저** 불투명하게, 셸을 **나중에** 반투명으로 — 셸은 항상 내부보다 앞이다.
        if isin.any():
            draw_mesh(ax, Vc, F[isin], rgb[isin], b, alpha=1.0, seam=0.10)
        draw_mesh(ax, Vc, F[~isin], rgb[~isin], b, alpha=0.34, seam=0.0)
        set_view(ax, (0.0, 0.0), half)
        ax.set_title(rec["label"] + ("  ★" if rec["measured"] else ""),
                     fontsize=10.6, fontweight="bold", color=INK, pad=3)
        #  ⚠ 패널마다 기체 크기에 맞춰 축척이 다르다 → **패널마다** 눈금자를 둔다
        #    (기체 간 실제 크기 비교는 mesh_gallery_all.png 가 한다).
        scale_bar(ax, half, (0.0, 0.0), y_frac=-0.80, x_frac=-0.92)
        if internal:
            cap = ("enclosed: " + " + ".join(sorted(internal)) + "\n"
                   f"{rec['internal']['area_m2']*1e4:.0f} cm2  "
                   f"({100*rec['internal']['area_share']:.1f} % of area, "
                   f"{100*rec['internal']['gamma_share']:.1f} % of "
                   r"$\Sigma|\Gamma|A$)")
        else:
            cap = ("nothing is enclosed — open frame\n"
                   "battery and PCB are directly visible")
        ax.text(0.0, -0.95 * half, cap, ha="center", va="top", fontsize=8.4,
                color=INK2, linespacing=1.5)

        # --- 행 2: y = 0 실단면 ------------------------------------------------ #
        axS = fig.add_subplot(g1[0, i])
        segs, sg = _section_segments(Vc, F, G, axis=1, value=0.0)
        if len(segs):
            xz = segs[:, :, [0, 2]]
            ext = np.asarray([g not in internal for g in sg], bool)
            for mask, lw, z in ((ext, 0.9, 2), (~ext, 2.4, 3)):
                if not mask.any():
                    continue
                cols = np.asarray([MATERIAL_COLOR[DRONE_GROUP_MAT[g][0]] for g in sg[mask]])
                axS.add_collection(LineCollection(xz[mask], colors=cols, linewidths=lw,
                                                  zorder=z, capstyle="round"))
            lo = xz.reshape(-1, 2).min(0); hi = xz.reshape(-1, 2).max(0)
            lo = np.array([lo[0], lo[1] - 0.22 * (hi[1] - lo[1])])   # 눈금자 자리
            c_, h_ = set_view_free(axS, lo, hi, pad=1.10)
            scale_bar(axS, float(max(h_)), (c_[0], c_[1] - 0.92 * h_[1]),
                      x_frac=-0.30, y_frac=0.0)
        axS.set_title("section at y = 0   (nose to the left)" if i == 0 else "section at y = 0",
                      fontsize=9.0, color=INK2, pad=2)

        # --- 행 3: 스윕 전체에서 직접 보이는 면적비 --------------------------- #
        axV = fig.add_subplot(g2[0, i])
        gl = sorted(rec["groups"], key=lambda q: rec["groups"][q]["visible_frac_sweep"]["max"])
        yv = np.arange(len(gl))
        vals = [100 * rec["groups"][g]["visible_frac_sweep"]["max"] for g in gl]
        cols = [(C_SHADOW if rec["groups"][g]["internal"] else C_LIT) for g in gl]
        axV.barh(yv, vals, height=0.62, color=cols, edgecolor="none", zorder=2)
        #  '한 번도 안 보임' 은 막대 길이가 0 이라 색이 안 보인다 → 축 위에 표식을 찍어
        #  그 부류가 존재한다는 것을 눈에 남긴다(막대 길이는 실제값 그대로 둔다).
        hid = [j for j, g in enumerate(gl) if rec["groups"][g]["internal"]]
        if hid:
            axV.scatter([0.0] * len(hid), hid, marker="s", s=22, color=C_SHADOW,
                        zorder=4, clip_on=False)
        axV.set_yticks(yv, gl, fontsize=7.6)
        for j, lab in enumerate(axV.get_yticklabels()):
            if rec["groups"][gl[j]]["internal"]:
                lab.set_color(C_SHADOW)
        axV.set_xlim(0, 132)
        axV.set_xticks([0, 50, 100], ["0", "50", "100"], fontsize=7.6)
        axV.grid(axis="x", lw=0.5, color="#e9e9e9", zorder=0)
        axV.set_axisbelow(True)
        for sp in ("top", "right"):
            axV.spines[sp].set_visible(False)
        for yy, v in zip(yv, vals):
            axV.text(min(v, 100) + 3.0, yy, (f"{v:.1f}" if v < 5.0 else f"{v:.0f}"),
                     va="center", fontsize=7.4, color=INK2)
        if i == 0:
            axV.set_xlabel("[%]", fontsize=8.0, color=INK2, loc="left")

    # --- 제목/설명은 **원장에서 만든다** (손으로 적으면 기체가 늘 때 거짓이 된다) --- #
    #  ⚠ 여기서 한 번 틀렸다: "5종은 배터리와 PCB 가 갇혀 있다" 라고 적었는데
    #    Typhoon H 는 **PCB 만** 갇혀 있고 배터리는 셸 밖(아래)에 달려 있어 47 % 보인다.
    #    → 기체를 '무엇이 갇혔는가' 로 분류해서 문장을 만든다.
    def _lab(ks):
        return ", ".join(A[q]["label"] for q in ks)
    doc = sorted(DOC_INTERNAL)
    both = [q for q in keys if set(doc) <= set(A[q]["internal"]["groups"])]
    part = [q for q in keys if A[q]["internal"]["groups"]
            and not set(doc) <= set(A[q]["internal"]["groups"])]
    openf = [q for q in keys if not A[q]["internal"]["groups"]]
    worst = max((A[q]["internal"]["max_visible_frac"] for q in keys
                 if A[q]["internal"]["groups"]), default=0.0)
    extra = sorted({g for q in keys for g in A[q]["internal"]["vs_documented"]
                    ["visible_in_doc_but_enclosed"]})
    part_txt = ""
    for q in part:
        seen = sorted(A[q]["internal"]["vs_documented"]["documented_but_visible"])
        if not seen:                      # 방어: 기체에 battery/pcb 그룹 자체가 없을 수 있다
            continue
        part_txt += (f"  On {A[q]['label']} only {', '.join(A[q]['internal']['groups'])} is enclosed "
                     f"— its {', '.join(seen)} sits outside the shell and reaches "
                     f"{100*max(A[q]['groups'][g]['visible_frac_sweep']['max'] for g in seen):.0f} %.")
    fig.suptitle("Where the internal scatterers sit — and why the engine has to reach through "
                 "the shell", fontsize=17.0, fontweight="bold", y=0.978)
    fig.text(0.5, 0.946,
             "Shell drawn at 34 % opacity, enclosed groups solid. The bottom row is measured, not "
             f"assumed: whatever is enclosed never exceeds {100*worst:.1f} % direct visibility "
             f"anywhere in the {m['aspect']['sweep_n']}-azimuth sweep at "
             f"el = {m['aspect']['el_deg']:.0f}°.\n"
             f"Battery and PCB are both enclosed on {_lab(both)}.{part_txt}  "
             f"On the open-frame {_lab(openf)} nothing is enclosed at all.\n"
             "A first-hit ray tracer deletes whatever is enclosed, which contradicts the material "
             r"model itself — a plastic shell at $|\Gamma|$ = "
             f"{sh['gamma_shell']:.2f} is semi-transparent. So rcs_sbr shoots a second pass with the "
             f"shell ({', '.join(sh['shell_groups'])}) removed and weights it by the round-trip "
             r"transmission $\tau = 1-|\Gamma|^2$ = "
             f"{sh['tau_round_trip']:.3f} ({sh['tau_db']:+.2f} dB).",
             ha="center", va="top", fontsize=10.2, color="#333", linespacing=1.6)
    legend = [Patch(facecolor=MATERIAL_COLOR[mm], edgecolor="#888", lw=0.5,
                    hatch=MAT_HATCH.get(mm), label=mm) for mm in _mat_sort(J["materials"])]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.028), ncol=7,
               frameon=False, fontsize=9.4, handlelength=1.6, columnspacing=1.8)
    note = ("Bottom row: the largest fraction of each group's front-facing area that is directly "
            "visible, over the whole sweep [%]. Colour encodes visibility, not material — "
            "amber = seen directly from at least one aspect, indigo square on the axis = never.")
    if extra:
        note += ("\nMeasured enclosed but not documented as internal in DRONE_GROUP_MAT: "
                 + ", ".join(f"{g} ({', '.join(A[k]['label'] for k in keys if g in A[k]['internal']['groups'])})"
                             for g in extra) + ".")
    fig.text(0.5, 0.082, note, ha="center", va="top", fontsize=9.0, color=INK2, linespacing=1.5)
    _prov(fig, J, "★ = airframe that is also physically measured")
    return _save(fig, "mesh_compare_material_internal.png")


# --------------------------------------------------------------------------- #
#  5.  ⭐ (c) 조명 vs 그늘
# --------------------------------------------------------------------------- #
def _face_class(c):
    """면별 부류: 0 = 뒷면(조명 안 됨) · 1 = LIT · 2 = SHADOWED.

    면 하나에 표면 표본이 여러 개일 수 있으므로 **면적 과반**으로 정한다
    (부분 조명면은 다수 쪽으로 접힌다 — 원장 `visibility.limits` 에 적어 둔 양자화)."""
    nf = len(c["F"])
    fr = np.bincount(c["FI"], weights=c["dA"] * c["front"], minlength=nf)
    li = np.bincount(c["FI"], weights=c["dA"] * c["lit"], minlength=nf)
    cls = np.zeros(nf, int)
    hit = fr > 0
    cls[hit & (li > 0.5 * fr)] = 1
    cls[hit & ~(li > 0.5 * fr)] = 2
    return cls


def _hex(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def _illum_arrow(ax, u, basis, half, color="#b26a00"):
    """조명 방향 화살표 — 광선은 −û 로 진행한다(표적을 향해)."""
    r, up, _d = basis
    s = np.array([float(u @ r), float(u @ up)])
    ln = np.linalg.norm(s)
    if ln < 1e-3:
        return
    s /= ln
    p0 = s * half * 0.99
    p1 = s * half * 0.68
    ax.add_patch(FancyArrow(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1],
                            width=half * 0.012, head_width=half * 0.075,
                            head_length=half * 0.085, length_includes_head=True,
                            color=color, zorder=8, clip_on=False))
    return s


def fig_shadow(J, cache=None, outdir=FIG):
    """대표 자세에서 **어느 면이 조명되고 어느 면이 가려지는가** — 우리 엔진의 게이트.

    윗줄은 **레이더의 눈**(조명 방향에서 본 직교투영)이다:
      · 먼저 LIT 면을 그리고 — 이게 SBR 이 실제로 적분하는 투영면이다,
      · 그 위에 SHADOWED 면을 **덧그린다**(X-ray). 덧그려진 남색이 곧 "앞 구조에 가려서
        레이더가 못 보는데 가림 없는 PO 는 그대로 더해 버리는" 면적이다.
    아랫줄 왼쪽은 같은 자세를 옆에서 본 것 — **무엇이 가리는지**를 보여준다."""
    A = J["airframes"]
    keys = [k for k in J["order_by_area"] if k in A]
    m = J["_meta"]
    az, el = m["aspect"]["az_deg"], m["aspect"]["el_deg"]
    u = SBR._look(az, el)
    n = len(keys)

    if cache is None:                            # 그림만 다시 그릴 때: 대표 자세만 재계산
        cache = {}
        gm_key = {g: mm for g, (mm, _) in DRONE_GROUP_MAT.items()}
        for k in keys:
            mesh, V, F, G = _geom(k)
            P, N, dA, FI = surface_samples(mesh, C0 / FC / SAMPLE_DIV)
            sc, _s, _g = SBR._mi_scene_from_mesh(mesh, gm_key, FC)
            front, lit = lit_mask(sc, P, N, dA, u)
            cache[k] = dict(mesh=mesh, V=V, F=F, G=G, P=P, N=N, dA=dA, FI=FI,
                            front=front, lit=lit)

    fig = plt.figure(figsize=(19.4, 11.8))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.10],
                             left=0.026, right=0.986, top=0.806, bottom=0.155, hspace=0.20)
    g0 = outer[0].subgridspec(1, n, wspace=0.05)
    g1 = outer[1].subgridspec(1, 3, width_ratios=[1.30, 1.0, 1.16], wspace=0.24)

    b_illum = view_basis(el, az)                 # 레이더의 눈 (d = û)
    b_obs = view_basis(OBS_EL, az + OBS_DAZ)     # 비켜 선 관측 카메라

    # --- 행 1: 레이더의 눈 + X-ray ------------------------------------------- #
    for i, k in enumerate(keys):
        rec, c = A[k], cache[k]
        ax = fig.add_subplot(g0[0, i])
        V, F = c["V"], c["F"]
        cen = 0.5 * (V.min(0) + V.max(0))
        cls = _face_class(c)
        half = VG.common_half(V, cen, views=((None, el, az, None),), fill=0.60)
        #  ⚠ 순서가 곧 의미다 — LIT 를 먼저, SHADOWED 를 **나중에**(위에) 그린다.
        #    matplotlib 은 같은 zorder 면 나중에 넣은 컬렉션을 위에 그린다.
        draw_mesh(ax, V - cen, F[cls == 1], np.tile(_hex(C_LIT), ((cls == 1).sum(), 1)),
                  b_illum, seam=0.10)
        if (cls == 2).any():
            draw_mesh(ax, V - cen, F[cls == 2], np.tile(_hex(C_SHADOW), ((cls == 2).sum(), 1)),
                      b_illum, seam=0.10)
        set_view(ax, (0.0, 0.0), half)
        ax.set_title(rec["label"] + ("  ★" if rec["measured"] else ""),
                     fontsize=10.6, fontweight="bold", color=INK, pad=3)
        sd = rec["shadow"]
        ax.text(0.0, -0.86 * half,
                f"{100*sd['exterior_shadow_frac']:.0f} % of the outer skin facing the\n"
                f"illuminator is blocked\n"
                f"({100*sd['shadow_frac']:.0f} % counting every group)",
                ha="center", va="top", fontsize=8.4, color=INK2, linespacing=1.5)
        #  ⚠ 패널마다 축척이 다르다(각 기체에 맞춤) → 패널마다 눈금자를 둔다.
        scale_bar(ax, half, (0.0, 0.0), y_frac=-0.72, x_frac=-0.94)

    # --- 행 2 왼쪽: 비켜 선 카메라 — **무엇이 가리는지** --------------------- #
    kd = next((k for k in keys if A[k]["measured"]), keys[0])
    rec, c = A[kd], cache[kd]
    axD = fig.add_subplot(g1[0, 0])
    V, F = c["V"], c["F"]
    cen = 0.5 * (V.min(0) + V.max(0))
    cls = _face_class(c)
    col = np.where(cls[:, None] == 1, _hex(C_LIT)[None, :],
                   np.where(cls[:, None] == 2, _hex(C_SHADOW)[None, :], _hex(C_BACK)[None, :]))
    half = VG.common_half(V, cen, views=((None, OBS_EL, az + OBS_DAZ, None),), fill=0.56)
    draw_mesh(axD, V - cen, F, col, b_obs, seam=0.12)
    set_view(axD, (0.0, 0.0), half)
    sdir = _illum_arrow(axD, u, b_obs, half)
    if sdir is not None:
        axD.text(sdir[0] * half * 1.20, sdir[1] * half * 1.20,
                 f"illuminator\naz {az:.0f}°, el {el:.0f}°\n(rays travel this way)",
                 ha="center", va="center", fontsize=9.0, color="#b26a00", linespacing=1.4)
    scale_bar(axD, half, (0.0, 0.0), y_frac=0.86, x_frac=-0.94)
    axD.set_title(f"{rec['label']} — seen from {OBS_DAZ:.0f}° off the illuminator, so the "
                  "blocking structure is visible", fontsize=11.0, color=INK, pad=6)
    gtop = sorted(((g, v) for g, v in rec["shadow"]["per_group"].items()
                   if v["shadow_frac"] is not None and not rec["groups"][g]["internal"]),
                  key=lambda t: -t[1]["shadow_frac"])[:3]
    encl = rec["internal"]["groups"]
    axD.text(0.0, -0.045,
             "most-blocked outer groups at this aspect:  "
             + "  ·  ".join(f"{g} {100*v['shadow_frac']:.0f} %" for g, v in gtop)
             + ("\nenclosed groups (" + ", ".join(encl) + ") are 100 % blocked, reached only "
                "through the shell-transmission pass" if encl else ""),
             transform=axD.transAxes, fontsize=8.6, color=INK2, ha="left", va="top",
             linespacing=1.5)

    # --- 행 2 가운데: 그늘 면적비 (대표 자세 + 스윕 범위) -------------------- #
    axS = fig.add_subplot(g1[0, 1])
    y = np.arange(len(keys))
    val = [100 * A[k]["shadow"]["exterior_shadow_frac"] for k in keys]
    lo = [100 * min(A[k]["shadow_sweep"]["shadow_frac_exterior"]) for k in keys]
    hi = [100 * max(A[k]["shadow_sweep"]["shadow_frac_exterior"]) for k in keys]
    for i in range(len(keys)):
        axS.plot([lo[i], hi[i]], [i, i], color="#cfcfcf", lw=3.2, solid_capstyle="round", zorder=1)
    axS.scatter(val, y, s=64, color=C_SHADOW, zorder=3, edgecolor="white", linewidth=1.4)
    for i in range(len(keys)):
        axS.text(hi[i] + 1.4, i, f"{val[i]:.0f} %", fontsize=9.0, color=INK, va="center",
                 fontweight="bold")
    axS.set_yticks(y, [A[k]["label"] for k in keys], fontsize=9.2)
    axS.invert_yaxis()
    axS.set_xlabel("Outer-skin area facing the illuminator that the airframe blocks  [%]",
                   fontsize=9.6)
    axS.set_xlim(0, max(hi) * 1.20)
    axS.grid(axis="x", lw=0.5, color="#ececec", zorder=0)
    axS.set_axisbelow(True)
    for sp in ("top", "right"):
        axS.spines[sp].set_visible(False)
    axS.set_title(f"Self-shadowing at the representative aspect\n"
                  f"(dot = az {az:.0f}°, grey bar = full {m['aspect']['sweep_n']}-azimuth range)",
                  fontsize=11.0, color=INK, pad=6)

    # --- 행 2 오른쪽: 가림을 무시하면 σ 가 얼마나 부풀까 --------------------- #
    axG = fig.add_subplot(g1[0, 2])
    d_occ = [A[k]["sigma"]["d_occlusion_db"] for k in keys]
    d_tot = [A[k]["sigma"]["d_total_db"] for k in keys]
    spread = [A[k]["sigma"]["discretisation_spread_db"] for k in keys]
    axG.barh(y, d_occ, height=0.54, color=C_SHADOW, edgecolor="none", zorder=2)
    axG.scatter(d_tot, y, s=52, marker="D", color=C_LIT, zorder=4,
                edgecolor="white", linewidth=1.2)
    #  ⚠ PO 와 SBR 은 이산화가 다르다 → 그 폭보다 작은 막대는 효과라고 부를 수 없다.
    axG.vlines(spread, y - 0.30, y + 0.30, color="#8a8a8a", lw=1.8, zorder=5)
    xmax = max(max(d_occ), max(d_tot))
    for i, k in enumerate(keys):
        sg = A[k]["sigma"]
        axG.text(max(d_occ[i], d_tot[i]) + 0.12, i - 0.16, f"{d_occ[i]:+.1f} dB",
                 fontsize=9.0, va="center", color=INK, fontweight="bold")
        #  표 뷰 쌍둥이 — 절대 σ 세 값을 막대 옆에 그대로 적는다(색만으로 읽지 않게).
        axG.text(max(d_occ[i], d_tot[i]) + 0.12, i + 0.30,
                 f"{sg['po_no_occlusion_dbsm']:.1f} / {sg['sbr_occluded_opaque_dbsm']:.1f} / "
                 f"{sg['sbr_production_dbsm']:.1f}", fontsize=7.4, va="center", color=INK2)
    axG.set_yticks(y, [A[k]["label"] for k in keys], fontsize=9.2)
    axG.invert_yaxis()
    axG.axvline(0.0, color="#bbbbbb", lw=0.8, zorder=1)
    axG.set_xlim(0, xmax * 1.62)
    axG.set_xlabel(r"Azimuth-averaged $\sigma$ overestimate if the gate is dropped  [dB]",
                   fontsize=9.6)
    axG.grid(axis="x", lw=0.5, color="#ececec", zorder=0)
    axG.set_axisbelow(True)
    for sp in ("top", "right"):
        axG.spines[sp].set_visible(False)
    axG.legend(handles=[Patch(facecolor=C_SHADOW, edgecolor="none",
                              label=r"occlusion alone: PO $-$ SBR opaque"),
                        plt.Line2D([], [], marker="D", ls="none", ms=7, color=C_LIT,
                                   markeredgecolor="white",
                                   label=r"occlusion + shell transmission: PO $-$ production SBR"),
                        plt.Line2D([], [], color="#8a8a8a", lw=1.8,
                                   label="discretisation floor: PO at "
                                         r"$\lambda/7$ vs $\lambda/12$"
                                         f" ($\\leq$ {max(spread):.2f} dB)")],
               loc="lower right", frameon=False, fontsize=8.2, handlelength=1.4)
    axG.set_title("What the visibility gate is worth\n"
                  f"(small type = PO / SBR-opaque / SBR-production, dBsm at "
                  f"{m['fc_hz']/1e9:.2f} GHz, el {el:.0f}°)",
                  fontsize=11.0, color=INK, pad=6)

    fig.suptitle("Lit versus shadowed — the visibility gate inside our PO surface integral",
                 fontsize=17.0, fontweight="bold", y=0.976)
    fig.text(0.5, 0.944,
             r"The PO integral only sums surface the illuminator can actually see: $\hat n\cdot"
             r"\hat u>0$ AND the path out to the radar is clear. That second half is a shadow ray, "
             "and it is the same call (rcs_sbr._exit_visible) the production SBR engine makes.\n"
             "Top row is the radar's own view: the amber surface is what rcs_sbr integrates, and "
             "the indigo is drawn on top of it — an X-ray of the surface hiding directly behind, "
             r"which a PO integral without occlusion adds to $\sigma$ anyway."
             "\nStock Sionna RT does trace occlusion for propagation paths, but its path solver "
             r"carries no surface-scattering integral, so no target $\sigma$ emerges from it and "
             "there is no lit region for it to gate. Colour here encodes illumination, not material.",
             ha="center", va="top", fontsize=10.4, color="#333", linespacing=1.6)
    handles = [Patch(facecolor=C_LIT, edgecolor="none",
                     label="LIT — front-facing and visible to the illuminator"),
               Patch(facecolor=C_SHADOW, edgecolor="none",
                     label="SHADOWED — front-facing but blocked by the airframe itself"),
               Patch(facecolor=C_BACK, edgecolor="none",
                     label="back-facing — never illuminated at this aspect")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.019), ncol=3,
               frameon=False, fontsize=10.0, handlelength=1.7, columnspacing=2.4)
    #  ⚠ 면적과 Δσ 는 같은 이야기가 아니다 — σ 는 코히런트 합이라 몇 개의 정반사 플래시가 지배한다.
    #    반례는 원장에서 뽑는다(손으로 고른 문장이 아니다).
    kw = min(keys, key=lambda q: A[q]["sigma"]["d_occlusion_db"])
    ratio = (A[kw]["sigma"]["d_occlusion_db"]
             / max(A[kw]["sigma"]["discretisation_spread_db"], 1e-9))
    fig.text(0.5, 0.094,
             "Blocked area and the sigma shift are not the same story — sigma is a coherent sum "
             "dominated by a few specular flashes. "
             f"{A[kw]['label']} blocks {100*A[kw]['shadow']['exterior_shadow_frac']:.0f} % of its "
             f"lit skin at this aspect,\nyet its azimuth-averaged sigma moves only "
             f"{A[kw]['sigma']['d_occlusion_db']:+.2f} dB, which is {ratio:.1f} times the "
             "discretisation floor and therefore not a result we would lean on.",
             ha="center", va="top", fontsize=9.2, color=INK2, linespacing=1.6)
    _prov(fig, J, "representative aspect chosen by rule (see _meta.aspect.rule_en in the ledger)")
    return _save(fig, "mesh_compare_material_shadow.png")


# --------------------------------------------------------------------------- #
def build_all(keys=None, only="all"):
    keys = list(keys or drone_keys())
    J, cache = (None, None)
    if only in ("all", "measure"):
        J, cache = measure(keys)
    if J is None:
        J = _load()
    if only in ("all", "area"):
        fig_area(J)
    if only in ("all", "internal"):
        fig_internal(J)
    if only in ("all", "shadow"):
        fig_shadow(J, cache)
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all",
                    choices=["all", "measure", "area", "internal", "shadow"])
    ap.add_argument("--keys", default=None, help="쉼표 구분 (기본: 레지스트리 전부)")
    a = ap.parse_args()
    ks = [k.strip() for k in a.keys.split(",")] if a.keys else None
    build_all(ks, a.only)
    print("재질·내부·조명 그림 완료 →", os.path.relpath(FIG, ROOT))
