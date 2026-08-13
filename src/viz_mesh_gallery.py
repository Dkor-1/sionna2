# -*- coding: utf-8 -*-
"""
viz_mesh_gallery.py — **현재 메쉬 소스에서 7종 전 기체를 새로 렌더한다**
=========================================================================

왜 이 파일이 있나
-----------------
`src/drone_cad.py` · `src/drones.py` 가 크게 바뀌면서 7종 전부의 형상이 달라졌는데,
저장소의 그림 대부분은 그보다 **오래된 메쉬**를 보여주고 있었다. 즉 독자가 지금 보는
그림 중 일부는 **더 이상 존재하지 않는 기하**다. 이 스크립트는 그 구멍을 메운다 —
기체마다 직교 4뷰 + 재질 분해도를 새로 만들고, 7종을 **실제 상대 크기**로 한 장에 모은다.

만드는 것
---------
  outputs/figures/mesh_gallery_<key>.png   기체별 5패널 (top / front / side / iso / exploded)
  outputs/figures/mesh_gallery_all.png     ⭐ 7종 **true relative scale** 갤러리
  outputs/mesh_gallery.json                기체별 기하 원장 (리포트가 주입해서 쓴다)

규약 (저장소 하우스룰)
----------------------
  · 그림 안 글자는 **전부 영어**. 산문·주석·print 는 한국어.
  · 그림의 숫자는 **손으로 적지 않는다** — `measure()` 가 메쉬를 재서 `mesh_gallery.json` 에
    쓰고, 그림은 그 JSON 을 **디스크에서 다시 읽어** 그린다(그림과 원장이 어긋날 수 없다).
  · 색 = **순수 재질 5색**. `drones.MATERIAL_COLOR` 가 유일한 출처이고 여기서 새 색을
    만들지 않는다(σ 가 재질 가중이라 **색이 곧 정보**다). 음영은 명도만 건드리고
    색상(hue)은 그대로 둔다 — 범례 스와치는 항상 **순수색**을 쓴다.

렌더러 — 왜 matplotlib 3D 가 아닌가
-----------------------------------
`Poly3DCollection` 은 삼각형 3만 개를 여러 패널에 그리면 느리고, 축 상자 비율 때문에
**패널마다 실제 축척이 미묘하게 달라진다**(= 기체 간 비교가 불가능). 여기서는 직교투영을
직접 계산해 2D `PolyCollection` 으로 그린다:
  · 진짜 직교투영 → 패널·기체가 **같은 m/inch 축척**을 공유한다(3번 갤러리의 전제).
  · 화가 알고리즘(깊이 정렬) + 후면 컬링 → 워터타이트 메쉬에서 가림이 정확하다.
카메라 각도(iso elev=18/azim=-60, top elev=90/azim=-90)와 재질색은 `report_mesh` 의
기존 와이어프레임 그림과 **같은 규약**을 쓴다 — 새로운 룩을 만들지 않는다.

실행
----
  cd /workspace/sionna
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/viz_mesh_gallery.py
  ... --only measure          # JSON 만
  ... --only gallery          # 갤러리 한 장만
  ... --keys mini5pro,matrice4e
"""
from __future__ import annotations

import argparse
import json
import os
import time

import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Circle, Rectangle

from drones import (DRONES, DRONE_GROUP_MAT, MATERIAL_COLOR, build_drone,
                    drone_gamma_map, drone_keys, drone_label, frame_envelope_mm)

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
LEDGER = os.path.join(OUT, "mesh_gallery.json")
REPORT1 = os.path.join(OUT, "report1.json")

C0 = 299_792_458.0

#: 리포트 전체가 쓰는 세 밴드 [Hz]. `make_report02_target.BANDS` 와 같은 값이며 아래에서 검사한다.
BANDS = {"LTE": 1.843e9, "5G": 3.500e9, "WiFi": 5.210e9}

#: 메쉬 형상을 정하는 소스 — 그림/원장이 이보다 낡았는지 판정하는 기준이다.
MESH_SOURCES = ("src/drone_cad.py", "src/drones.py", "src/cadkit.py", "src/geom.py")

#: 카메라 (라벨, elev, azim). report_mesh/viz_mesh_reports 의 iso(18/-60)·top(90/-90) 규약을 따른다.
VIEWS = (("top",   90.0, -90.0, "Top  (+x right, +y up)"),
         ("front",  0.0,   0.0, "Front  (nose toward viewer)"),
         ("side",   0.0, -90.0, "Side  (nose right)"),
         ("iso",   18.0, -60.0, "Isometric"))

#: 카메라 정책 — 반폭 = CAM_FILL × (그 기체를 **네 뷰에 투영했을 때의 최대 화면폭**).
#: 네 패널이 **한 값**을 공유하므로 패널끼리 축척이 같고, 규칙이 하나라서 기체끼리도 여백 비율이 같다.
#: (뷰마다 따로 맞추면 iso 뷰만 잘리거나 패널마다 축척이 달라져 비교가 깨진다.)
CAM_FILL = 0.55
EXPLODE_STEP = 0.30          # 분해 간격 / span

#: 눈금자 사다리 [m] — 어떤 기체든 이 중에서 고른다(막대 길이가 곧 크기 비교가 된다).
BAR_LADDER = (0.05, 0.10, 0.20, 0.25, 0.50, 1.00, 2.00)

#: 음영 — 명도만 [AMBIENT, 1.0] 범위로 바꾼다. 색상(hue)=재질 규약은 그대로 유지된다.
AMBIENT = 0.58
_LIGHT_CAM = np.array([-0.42, 0.46, 0.78])       # 카메라 좌표계: 왼쪽 위 앞
_LIGHT_CAM = _LIGHT_CAM / np.linalg.norm(_LIGHT_CAM)

GRAY = "#5a5a5a"

#: 실물 측정 대상 — 이 둘의 형상 충실도가 제일 중요하므로 그림에 표시한다.
MEASURED = ("matrice4e", "mini5pro")


# --------------------------------------------------------------------------- #
#  0.  직교 카메라 + 화가 알고리즘 렌더러
# --------------------------------------------------------------------------- #
def view_basis(elev_deg: float, azim_deg: float):
    """(right, up, toward_camera) 정규직교기저. matplotlib `view_init(elev, azim)` 과 같은 규약."""
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])   # 장면→카메라
    r = np.array([-np.sin(a), np.cos(a), 0.0])                                # 화면 오른쪽
    u = np.cross(d, r)                                                        # 화면 위
    return r, u, d


def _tri_arrays(V: np.ndarray, F: np.ndarray):
    """삼각형 꼭짓점 (n,3,3) · 단위법선 (n,3) · 면적 (n,)."""
    tri = V[F]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    area = 0.5 * ln
    nh = nrm / np.where(ln[:, None] < 1e-30, 1.0, ln[:, None])
    return tri, nh, area


def draw_mesh(ax, V, F, face_rgb, basis, *, cull=True, alpha=1.0,
              offsets=None, seam=0.12):
    """메쉬를 직교투영해 2D `PolyCollection` 으로 그린다.

    face_rgb : (n_faces, 3) 면별 **순수 재질색**. 음영(명도)은 여기서 곱한다.
    offsets  : (n_faces, 3) 면별 이동벡터 [m] — 분해도용(없으면 0).
    seam     : 인접 삼각형 사이 흰 실선(핀홀)을 막는 얇은 테두리 두께.
    반환     : 화면좌표 (X, Y) 의 (min, max) — 축 범위 계산용.
    """
    r, u, d = basis
    tri, nh, _ = _tri_arrays(V, F)
    if offsets is not None:
        tri = tri + offsets[:, None, :]
    facing = nh @ d
    keep = np.ones(len(tri), bool) if not cull else (facing > 1e-9)
    if not keep.any():
        keep = np.ones(len(tri), bool)
    tri, nh, facing = tri[keep], nh[keep], facing[keep]
    rgb = np.asarray(face_rgb, float)[keep]

    L = _LIGHT_CAM[0] * r + _LIGHT_CAM[1] * u + _LIGHT_CAM[2] * d      # 월드 좌표 광원
    shade = AMBIENT + (1.0 - AMBIENT) * np.clip(nh @ L, 0.0, 1.0)
    cols = np.clip(rgb * shade[:, None], 0.0, 1.0)

    P = np.stack([tri @ r, tri @ u], axis=-1)                           # (n,3,2) 화면좌표
    order = np.argsort((tri @ d).mean(1))                               # 먼 것부터(화가 알고리즘)
    P, cols = P[order], cols[order]
    ax.add_collection(PolyCollection(P, facecolors=cols, edgecolors=cols,
                                     linewidths=seam, alpha=alpha, zorder=2))
    flat = P.reshape(-1, 2)
    return flat.min(0), flat.max(0)


def set_view(ax, center_xy, half, *, pad=1.0):
    """모든 패널이 같은 **m/point** 축척을 갖도록 정사각 시야를 강제한다."""
    ax.set_xlim(center_xy[0] - half * pad, center_xy[0] + half * pad)
    ax.set_ylim(center_xy[1] - half * pad, center_xy[1] + half * pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()


def set_view_free(ax, lo, hi, *, pad=1.06):
    """데이터 비율을 그대로 쓰는 시야(분해도처럼 세로로 긴 그림용). 축척은 등방."""
    c = 0.5 * (np.asarray(lo) + np.asarray(hi))
    h = 0.5 * (np.asarray(hi) - np.asarray(lo)) * pad
    h = np.maximum(h, 1e-6)
    ax.set_xlim(c[0] - h[0], c[0] + h[0])
    ax.set_ylim(c[1] - h[1], c[1] + h[1])
    ax.set_aspect("equal", adjustable="box")
    ax.set_axis_off()
    return c, h


def common_half(V, cen, views=VIEWS, fill=CAM_FILL) -> float:
    """네 직교뷰가 **공유할** 시야 반폭 [m].

    뷰별로 따로 맞추면 (a) 패널마다 축척이 달라져 비교가 깨지고 (b) iso 뷰는 투영폭이
    bbox 최대변보다 커서 잘린다. 그래서 네 뷰의 투영폭 중 **최대**를 기준으로 하나만 정한다."""
    P = np.asarray(V, float) - np.asarray(cen, float)
    w = 0.0
    for _tag, elev, azim, _t in views:
        r, u, _d = view_basis(elev, azim)
        X, Y = P @ r, P @ u
        w = max(w, float(X.max() - X.min()), float(Y.max() - Y.min()))
    return fill * w


def _nice_bar(half_width: float) -> float:
    """시야 반폭에 맞는 눈금자 길이 [m] — 사다리에서 고르므로 기체가 달라도 규칙이 같다."""
    target = 0.55 * half_width
    return min(BAR_LADDER, key=lambda b: abs(np.log(b / target)))


def scale_bar(ax, half, center_xy, *, y_frac=-0.86, x_frac=-0.90, color="#222"):
    """왼쪽 아래 눈금자. 길이는 사다리에서 고르고 라벨은 cm/m 로 적는다(영어)."""
    L = _nice_bar(half)
    x0 = center_xy[0] + x_frac * half
    y0 = center_xy[1] + y_frac * half
    ax.plot([x0, x0 + L], [y0, y0], color=color, lw=2.6, solid_capstyle="butt", zorder=6)
    for xx in (x0, x0 + L):
        ax.plot([xx, xx], [y0 - 0.028 * half, y0 + 0.028 * half], color=color, lw=1.6, zorder=6)
    lab = f"{L*100:.0f} cm" if L < 1.0 else f"{L:.0f} m"
    ax.text(x0 + L / 2, y0 + 0.05 * half, lab, ha="center", va="bottom",
            fontsize=8.4, color=color, zorder=6)
    return L


# --------------------------------------------------------------------------- #
#  1.  계측 — outputs/mesh_gallery.json
# --------------------------------------------------------------------------- #
def _enclosing_radius(V: np.ndarray) -> float:
    """**외접구 반경**: bbox 중심에서 가장 먼 정점까지 [m].

    `src/make_report02_target.py::_enclosing_radius` 와 **같은 정의**다 — kr 의 정의가
    저장소 안에서 갈라지면 안 된다. 아래 `measure()` 가 report02_derived.json 과
    수치를 대조해서, 어긋나면 원장에 그대로 기록한다(조용히 넘어가지 않는다)."""
    c = 0.5 * (V.min(0) + V.max(0))
    return float(np.linalg.norm(V - c, axis=1).max())


def _mtime(path: str):
    return os.path.getmtime(path) if os.path.exists(path) else None


def _stamp(ts):
    return None if ts is None else time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def measure(keys=None, verbose=True) -> dict:
    """7종(또는 지정 기체)의 기하를 재서 원장 dict 를 만든다. GPU 불필요."""
    from mesh_check import check_mesh

    keys = list(keys or drone_keys())
    t0 = time.time()

    src_mt = {p: _stamp(_mtime(os.path.join(ROOT, p))) for p in MESH_SOURCES}
    newest_src = max(v for v in (_mtime(os.path.join(ROOT, p)) for p in MESH_SOURCES) if v)

    # ⚠ report1.json 은 지금도 다시 쓰이는 중일 수 있다 → **빌드 시점에 새로 읽고**,
    #   낡았거나 기체가 빠져 있으면 그 사실을 원장에 남긴다(옛 값으로 슬쩍 때우지 않는다).
    #
    # ⭐ **신선도는 mtime 이 아니라 내용의 stamp 로 판정한다.** 2026-07-31 실제로 겪은 일:
    #    report1.json 의 mtime 은 02:33 인데 `meshes` 블록은 07-29 11:35 값 그대로였다 —
    #    다른 스크립트(benchmark/refresh_material_table.py)가 **materials 블록만** 갱신하면서
    #    파일 전체 mtime 을 올렸기 때문이다. mtime 을 믿으면 낡은 메쉬 숫자를 최신인 줄 알고 쓴다.
    #    viz_report1 이 남기는 `_provenance.<block>.stamp` 가 블록별 진짜 신선도다.
    R1 = _load_json(REPORT1) or {}
    r1_mt = _mtime(REPORT1)
    r1_drones = (R1.get("meshes") or {}).get("drones") or {}
    r1_block = ((R1.get("_provenance") or {}).get("mesh") or {}).get("stamp") \
        or (R1.get("meta") or {}).get("stamp")
    r1_block_ts = None
    if r1_block:
        try:
            r1_block_ts = time.mktime(time.strptime(r1_block, "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            r1_block_ts = None
    r1_fresh = bool(r1_block_ts and r1_block_ts >= newest_src)

    # kr 은 report02 가 이미 같은 정의로 계산해 둔다 → 대조용으로 읽는다(우리가 다시 재기도 한다).
    R02 = _load_json(os.path.join(OUT, "report02_derived.json")) or {}
    r02_air = R02.get("airframes") or {}
    r02_mt = _mtime(os.path.join(OUT, "report02_derived.json"))

    air = {}
    for key in keys:
        spec = DRONES[key]
        mesh = build_drone(spec)
        V = np.asarray(mesh.v, float)
        F = np.asarray(mesh.f, int)
        G = np.asarray(mesh.g, object)
        _, _, area = _tri_arrays(V, F)
        env = frame_envelope_mm(spec)
        chk = check_mesh(mesh, key)
        gam = drone_gamma_map(spec, BANDS["5G"])

        grp = {}
        for g in sorted(set(mesh.g)):
            sel = (G == g)
            gv = V[F[sel]].reshape(-1, 3)
            mat = DRONE_GROUP_MAT[g][0]
            grp[g] = dict(
                material=mat, desc_ko=DRONE_GROUP_MAT[g][1],
                gamma_po_5g=float(gam[g]),
                color_rgb=[float(c) for c in MATERIAL_COLOR[mat]],
                n_faces=int(sel.sum()),
                n_parts=int(chk["groups"][g]["n_parts"]),
                area_m2=float(area[sel].sum()),
                bbox_mm=[float(x) for x in (gv.max(0) - gv.min(0)) * 1000.0],
                mean_z_mm=float(gv[:, 2].mean() * 1000.0))

        r_enc = _enclosing_radius(V)
        kr = {b: float(2.0 * np.pi * r_enc / (C0 / f)) for b, f in BANDS.items()}
        ref = r02_air.get(key)
        kr_ref = None
        if ref is not None:
            kr_ref = dict(r_encl_m=float(ref["r_encl_m"]),
                          delta_pct=float(100.0 * (r_enc - ref["r_encl_m"]) / ref["r_encl_m"]),
                          source="outputs/report02_derived.json",
                          source_mtime=_stamp(r02_mt))

        # 공식 외형 대비 오차 — **여기서 다시 잰다**. report1.json 이 낡아 있어도 그림은 옳다.
        #  ⚠ 공식 높이가 프롭 포함인 기체는 프레임이 아니라 전체 드론과 견준다
        #    (frame_envelope_mm 이 그 판단을 이미 하고 lwh_compare_mm 로 돌려준다).
        off_mm = list(spec.envelope_mm or (None, None, None))
        cmp_mm = env["lwh_compare_mm"]
        err_pct = [(100.0 * (cmp_mm[i] - off_mm[i]) / off_mm[i]) if off_mm[i] is not None else None
                   for i in range(3)]

        r1 = r1_drones.get(key)
        span = float((V.max(0) - V.min(0)).max())
        rec = dict(
            name=spec.name, label=drone_label(key), release=spec.release,
            confidence=spec.confidence, num_rotors=int(spec.num_rotors),
            coaxial=bool(spec.coaxial), prop_dia_mm=float(spec.prop_dia_mm),
            prop_blades=int(spec.prop_blades), weight_g=float(spec.weight_g),
            body_style=spec.body_style, arm_shape=spec.arm_shape,
            n_tris=int(mesh.n_tris()), n_groups=len(grp),
            n_parts=int(sum(v["n_parts"] for v in grp.values())),
            mesh_ok=bool(chk["ok"]),
            surface_area_m2=float(area.sum()),
            lwh_full_mm=[float(x) for x in env["lwh_full_mm"]],
            lwh_frame_mm=[float(x) for x in env["lwh_mm"]],
            official_mm=[(float(x) if x is not None else None) for x in off_mm],
            lwh_compare_mm=[float(x) for x in cmp_mm],
            err_pct=[(float(e) if e is not None else None) for e in err_pct],
            official_includes_props=bool(env["official_includes_props"]),
            diagonal_spec_mm=float(spec.diagonal_mm),
            diagonal_mesh_mm=float(env["diagonal_effective_mm"]),
            span_max_m=span,
            r_encl_m=float(r_enc), kr=kr, kr_crosscheck=kr_ref,
            groups=grp,
            report1=dict(present=r1 is not None,
                         n_tris=(int(r1["n_tris"]) if r1 else None),
                         err_pct=(r1["err_pct"] if r1 else None),
                         note=(None if r1 else
                               "report1.json 에 이 기체가 없다 — 재생성이 아직 여기까지 오지 않았다")),
            figure=f"outputs/figures/mesh_gallery_{key}.png")
        air[key] = rec
        if verbose:
            print(f"  [gallery] {key:12s} tris={rec['n_tris']:6,d}  parts={rec['n_parts']:3d}  "
                  f"groups={rec['n_groups']:2d}  span={span*1000:7.1f} mm  "
                  f"r={r_enc:.4f} m  kr(5G)={kr['5G']:.1f}"
                  + ("" if r1 else "   ⚠ report1.json 미수록"))

    order = sorted(air, key=lambda k: air[k]["span_max_m"])
    missing = [k for k in keys if not air[k]["report1"]["present"]]
    drift = [k for k, v in air.items()
             if v["kr_crosscheck"] and abs(v["kr_crosscheck"]["delta_pct"]) > 0.5]

    J = dict(
        _meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            generator="src/viz_mesh_gallery.py :: measure()",
            purpose="현재 메쉬 소스에서 다시 잰 기체별 기하 원장. 리포트는 이 값을 주입해서 쓴다.",
            n_airframes=len(air),
            bands_ghz={k: v / 1e9 for k, v in BANDS.items()},
            mesh_sources=src_mt,
            mesh_source_newest=_stamp(newest_src),
            report1=dict(path="outputs/report1.json", mtime=_stamp(r1_mt),
                         mesh_block_stamp=r1_block,
                         fresher_than_mesh=r1_fresh,
                         airframes_present=sorted(r1_drones),
                         airframes_missing=missing,
                         freshness_rule="mtime 이 아니라 _provenance.mesh.stamp(없으면 meta.stamp)로 판정",
                         note=(f"report1.json 의 메쉬 블록({r1_block})이 메쉬 소스"
                               f"({_stamp(newest_src)})보다 낡았다 — 그림은 이 원장의 값을 쓰고, "
                               "report1.json 값은 대조용으로만 적는다."
                               if not r1_fresh else "report1.json 의 메쉬 블록이 메쉬보다 새롭다.")),
            crosscheck=dict(
                definition="r_encl = bbox 중심에서 가장 먼 정점까지의 거리 [m] "
                           "(src/make_report02_target.py 와 동일 정의)",
                report02_derived_mtime=_stamp(r02_mt),
                drifted_airframes=drift,
                note=("report02_derived.json 과 r_encl 이 0.5% 넘게 어긋난 기체가 있다 — "
                      "둘 중 하나가 낡았다는 뜻이다." if drift else
                      "report02_derived.json 의 r_encl 과 0.5% 이내로 일치한다.")),
            definitions=dict(
                lwh_full_mm="프로펠러 포함 전체 바운딩박스 [mm]",
                lwh_frame_mm="프로펠러 제외 프레임 바운딩박스 [mm]",
                n_parts="그룹별 연결성분(=실제 부품) 수의 합 — 모터 4개는 4로 센다",
                n_groups="재질 그룹 수 (= OBJ 파트 수 = Sionna 재질 수)",
                kr="2*pi*r_encl/lambda — 밴드 중심주파수 기준 전기적 크기",
                span_max_m="프로펠러 포함 바운딩박스의 최대 변 [m] — 갤러리 정렬·카메라 기준"),
            figures=dict(per_airframe="outputs/figures/mesh_gallery_<key>.png",
                         gallery="outputs/figures/mesh_gallery_all.png"),
            runtime_s=round(time.time() - t0, 1)),
        order_by_size=order,
        size_spread=dict(
            smallest=order[0], largest=order[-1],
            smallest_span_m=air[order[0]]["span_max_m"],
            largest_span_m=air[order[-1]]["span_max_m"],
            span_ratio=float(air[order[-1]]["span_max_m"] / air[order[0]]["span_max_m"]),
            kr_5g_min=air[order[0]]["kr"]["5G"], kr_5g_max=air[order[-1]]["kr"]["5G"]),
        airframes=air)

    # ⛔ 부분 계측은 원장을 덮지 않는다. `--keys mini5pro` 로 한 종만 재면 나머지 6종이
    #    파일에서 **조용히 사라지고** 리포트가 그 원장을 주입한다. 부분 결과는 메모리로만 쓴다.
    partial = sorted(keys) != sorted(drone_keys())
    if partial:
        print(f"  ⚠ 부분 계측({len(air)}/{len(DRONES)}종) — outputs/mesh_gallery.json 은 "
              f"덮어쓰지 않는다(원장이 기체를 잃지 않도록). 그림만 이 결과로 그린다.")
        return J
    os.makedirs(OUT, exist_ok=True)
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"  📒 outputs/mesh_gallery.json  ({len(air)}종, {J['_meta']['runtime_s']} s)")
    if missing:
        print(f"  ⚠ report1.json 에 없는 기체: {missing} — 재생성이 아직 그 단계에 오지 않았다.")
    if drift:
        print(f"  ⚠ report02_derived.json 과 r_encl 이 어긋난 기체: {drift}")
    return J


# --------------------------------------------------------------------------- #
#  2.  기체별 5패널
# --------------------------------------------------------------------------- #
def _face_rgb(mesh, rec) -> np.ndarray:
    """면별 **순수 재질색** (n_faces,3). 색 출처는 drones.MATERIAL_COLOR 하나뿐."""
    col = {g: rec["groups"][g]["color_rgb"] for g in rec["groups"]}
    return np.asarray([col[g] for g in mesh.g], float)


def _explode_offsets(mesh, rec, span):
    """분해도용 면별 z 이동벡터. 그룹을 **평균 높이 순서**로 세워 조립 순서가 읽히게 한다."""
    gs = sorted(rec["groups"], key=lambda g: rec["groups"][g]["mean_z_mm"])
    n = len(gs)
    step = EXPLODE_STEP * span
    dz = {g: (i - (n - 1) / 2.0) * step for i, g in enumerate(gs)}
    off = np.zeros((len(mesh.f), 3))
    off[:, 2] = [dz[g] for g in mesh.g]
    return off, gs, dz


def _fmt_lwh(v):
    return " x ".join(f"{x:.0f}" for x in v)


def _fmt_err(err):
    """공식 외형 대비 오차 [%] 3축. 공식값이 없는 축은 n/a (그 축은 비교 대상이 아니다)."""
    if err is None or all(e is None for e in err):
        return "no official envelope"
    return "  /  ".join("n/a" if e is None else f"{e:+.2f} %" for e in err)


def _report1_note(rec, meta) -> str:
    """report1.json 과의 대조 한 줄. **낡았으면 낡았다고 적는다** — 조용히 때우지 않는다."""
    r1 = rec["report1"]
    m1 = meta["report1"]
    if not r1["present"]:
        return ("Cross-check: outputs/report1.json does not list this airframe.\n"
                f"Its mesh block is stamped {m1['mesh_block_stamp']}, before the mesh edit "
                f"{meta['mesh_source_newest']}.")
    if r1["n_tris"] == rec["n_tris"]:
        return f"Cross-check: outputs/report1.json agrees ({r1['n_tris']:,} triangles)."
    return (f"Cross-check: outputs/report1.json says {r1['n_tris']:,} triangles, this mesh has "
            f"{rec['n_tris']:,}.\nIts mesh block is stamped {m1['mesh_block_stamp']}, before the "
            f"mesh edit {meta['mesh_source_newest']}.")


def fig_airframe(key: str, J: dict, outdir=FIG):
    """기체 1종: 직교 4뷰(같은 축척) + 재질 분해도 + 재질표 + 기하표."""
    rec = J["airframes"][key]
    meta = J["_meta"]
    spec = DRONES[key]
    mesh = build_drone(spec)
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    rgb = _face_rgb(mesh, rec)
    cen = 0.5 * (V.min(0) + V.max(0))
    span = rec["span_max_m"]
    half = common_half(V, cen)                     # 네 뷰 공통 반폭 — 축척이 하나다

    fig = plt.figure(figsize=(17.6, 10.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[1.0, 1.0, 0.72, 1.02],
                          left=0.010, right=0.992, top=0.868, bottom=0.052,
                          wspace=0.06, hspace=0.09)

    # --- (a~d) 직교 4뷰 (2x2) — 넷 다 같은 반폭 → 패널끼리 축척이 같다 --------- #
    for i, (tag, elev, azim, title) in enumerate(VIEWS):
        ax = fig.add_subplot(gs[i // 2, i % 2])
        draw_mesh(ax, V - cen, F, rgb, view_basis(elev, azim))
        set_view(ax, (0.0, 0.0), half)
        ax.set_title(title, fontsize=11.0, color="#222", pad=3)
        if i == 0:
            scale_bar(ax, half, (0.0, 0.0))
            ax.text(-0.92 * half, -0.955 * half,
                    f"all four views share one scale: panel width = {2*half*100:.0f} cm",
                    fontsize=7.8, color=GRAY, ha="left", va="top")

    # --- (e) 재질 분해도 — 세로로 긴 패널 -------------------------------------- #
    axE = fig.add_subplot(gs[:, 2])
    off, gorder, dz = _explode_offsets(mesh, rec, span)
    bE = view_basis(12.0, -62.0)
    lo, hi = draw_mesh(axE, V - cen, F, rgb, bE, offsets=off)
    r_, u_, _ = bE
    labels = []
    for g in gorder:
        sel = np.asarray([x == g for x in mesh.g], bool)
        pts = (V - cen)[F[sel]].reshape(-1, 3) + np.array([0.0, 0.0, dz[g]])
        labels.append((g, float((pts @ r_).min()), float((pts @ u_).mean())))
    wpx = float(hi[0] - lo[0])
    lo = np.array([min(lo[0], min(l[1] for l in labels)) - 0.42 * wpx, lo[1]])
    c_, h_ = set_view_free(axE, lo, hi, pad=1.05)
    for g, xmin, ymid in labels:
        axE.text(xmin - 0.022 * wpx, ymid, g, ha="right", va="center",
                 fontsize=9.0, color="#333")
    axE.set_title("Exploded by material group\n(vertical order = height in the assembly)",
                  fontsize=10.2, color="#222", pad=3)
    _bar_h = max(h_[0], h_[1] * 0.35)
    scale_bar(axE, _bar_h, (c_[0] + 0.55 * h_[0], c_[1] - 0.98 * h_[1]),
              x_frac=0.0, y_frac=0.0)

    # --- (f) 재질표 --------------------------------------------------------- #
    axM = fig.add_subplot(gs[0, 3]); axM.set_axis_off()
    rows = [(g, rec["groups"][g]) for g in gorder[::-1]]
    axM.set_xlim(0, 1); axM.set_ylim(-1.9, len(rows) + 1.5)
    hdr = [("group", 0.052), ("material", 0.30), ("|G|", 0.635), ("faces", 0.81), ("parts", 0.975)]
    for t, x in hdr:
        axM.text(x, len(rows) + 0.55, t, fontsize=8.4, color=GRAY,
                 ha="right" if x > 0.6 else "left")
    axM.plot([0, 1], [len(rows) + 0.20] * 2, color="#cccccc", lw=0.8)
    for i, (g, v) in enumerate(rows):
        y = len(rows) - 1 - i
        axM.add_patch(Rectangle((0.004, y + 0.16), 0.034, 0.60,
                                facecolor=tuple(v["color_rgb"]), edgecolor="k", lw=0.5))
        axM.text(0.052, y + 0.46, g, fontsize=9.0, va="center")
        axM.text(0.30, y + 0.46, v["material"], fontsize=9.0, va="center", color="#333")
        axM.text(0.635, y + 0.46, f"{v['gamma_po_5g']:.2f}", fontsize=9.0, va="center", ha="right")
        axM.text(0.81, y + 0.46, f"{v['n_faces']:,}", fontsize=9.0, va="center", ha="right")
        axM.text(0.975, y + 0.46, f"{v['n_parts']}", fontsize=9.0, va="center", ha="right")
    axM.text(0.0, -0.75,
             "Colour is the material class and the rule is identical for every airframe.\n"
             "Rows sharing a colour share a material: prop_plastic is the same ABS/PC as\n"
             "plastic, only the effective |G| of a thin blade differs.",
             fontsize=7.6, color=GRAY, va="top")
    axM.set_title("Colour = pure material class   "
                  "(|G| = PO amplitude reflection @ 3.5 GHz)",
                  fontsize=10.2, color="#222", pad=6)

    # --- (g) 기하표 --------------------------------------------------------- #
    axN = fig.add_subplot(gs[1, 3]); axN.set_axis_off()
    off_mm = rec["official_mm"]
    r1 = rec["report1"]
    lines = [
        ("Overall  L x W x H", f"{_fmt_lwh(rec['lwh_full_mm'])} mm", "propellers included"),
        ("Frame only", f"{_fmt_lwh(rec['lwh_frame_mm'])} mm", "propellers excluded"),
        ("Official envelope",
         "not published" if all(x is None for x in off_mm)
         else " x ".join("n/a" if x is None else f"{x:.0f}" for x in off_mm) + " mm",
         "props included" if rec["official_includes_props"] else "props excluded"),
        ("Envelope error  L / W / H", _fmt_err(rec["err_pct"]), "mesh vs official"),
        ("Motor-to-motor diagonal", f"{rec['diagonal_mesh_mm']:.0f} mm",
         f"spec sheet {rec['diagonal_spec_mm']:.0f} mm"),
        ("Triangles", f"{rec['n_tris']:,}", f"surface area {rec['surface_area_m2']:.3f} m2"),
        ("Material groups / parts", f"{rec['n_groups']} / {rec['n_parts']}",
         "parts = connected components"),
        ("Rotors x blades", f"{rec['num_rotors']} x {rec['prop_blades']}",
         f"propeller diameter {rec['prop_dia_mm']:.0f} mm"),
        ("Mass", f"{rec['weight_g']:.0f} g", ""),
        ("Enclosing radius r", f"{rec['r_encl_m']:.3f} m", "bbox centre to farthest vertex"),
    ]
    nk = len(BANDS)
    axN.set_xlim(0, 1); axN.set_ylim(-2.6, len(lines) + nk + 1.4)
    y = len(lines) + nk + 0.6
    for lab, val, note in lines:
        axN.text(0.0, y, lab, fontsize=9.0, va="center", color="#333")
        axN.text(0.585, y, val, fontsize=9.0, va="center", fontweight="bold")
        if note:
            axN.text(0.585, y - 0.40, note, fontsize=7.4, va="center", color=GRAY)
        y -= 1.0
    y -= 0.20
    axN.text(0.0, y, "Electrical size  kr = 2*pi*r/lambda", fontsize=9.4,
             va="center", fontweight="bold")
    y -= 0.92
    for b, f in BANDS.items():
        axN.text(0.035, y, f"{b}   {f/1e9:.3f} GHz", fontsize=9.0, va="center", color="#333")
        axN.text(0.585, y, f"kr = {rec['kr'][b]:.1f}", fontsize=9.0, va="center",
                 fontweight="bold")
        y -= 0.90
    axN.text(0.0, y - 0.35, _report1_note(rec, meta), fontsize=7.6, color=GRAY, va="top")
    axN.set_title("Geometry, measured from the mesh drawn in this figure",
                  fontsize=10.2, color="#222", pad=6)

    # --- 제목 / 출처 -------------------------------------------------------- #
    meas = "   [physically measured airframe]" if key in MEASURED else ""
    fig.suptitle(f"{rec['label']}  —  {rec['name']}{meas}",
                 fontsize=16.0, fontweight="bold", y=0.977)
    fig.text(0.5, 0.936,
             f"{rec['n_tris']:,} triangles  ·  {rec['n_groups']} material groups  ·  "
             f"{rec['n_parts']} parts  ·  {_fmt_lwh(rec['lwh_full_mm'])} mm  ·  "
             f"kr = {rec['kr']['LTE']:.1f} / {rec['kr']['5G']:.1f} / {rec['kr']['WiFi']:.1f} "
             f"at LTE 1.843 / 5G 3.500 / WiFi 5.210 GHz",
             ha="center", fontsize=11.0, color="#333")
    fig.text(0.010, 0.012,
             f"Mesh rebuilt from {' + '.join(MESH_SOURCES[:2])} (newest edit "
             f"{meta['mesh_source_newest']})  ·  every number injected from "
             f"outputs/mesh_gallery.json, generated {meta['generated']}",
             fontsize=7.6, color=GRAY, ha="left")

    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, f"mesh_gallery_{key}.png")
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/mesh_gallery_{key}.png")
    return p


# --------------------------------------------------------------------------- #
#  3.  ⭐ 7종 true-relative-scale 갤러리
# --------------------------------------------------------------------------- #
def fig_gallery(J: dict, outdir=FIG):
    """7종을 **하나의 좌표계**에 실제 상대 크기로 늘어놓는다.

    크기 격차가 downstream 을 지배한다 — 전기적 크기 kr, 그래서 σ, 그래서 검지거리.
    그러니 패널마다 축척을 바꾸지 않는다. 위(top)·아래(side) 두 줄이 **같은 m/inch** 를 쓰고,
    가로 배치는 `xs[key]` 하나로 공유하므로 두 줄의 같은 열이 같은 기체다.

    ⚠ 가로 슬롯 폭은 **max(화면 폭, 2·r_encl)** 이다 — 외접구 원(kr 의 r)이 이웃을 침범하면
      크기 비교 그림에서 원이 겹쳐 읽히지 않는다."""
    meta = J["_meta"]
    keys = [k for k in J["order_by_size"] if k in J["airframes"]]
    ss = J["size_spread"]
    A = J["airframes"]

    bT = view_basis(*VIEWS[0][1:3])          # top
    bS = view_basis(*VIEWS[2][1:3])          # side
    meshes, rgbs, cens = {}, {}, {}
    for k in keys:
        m = build_drone(DRONES[k])
        meshes[k] = m
        rgbs[k] = _face_rgb(m, A[k])
        Vk = np.asarray(m.v, float)
        cens[k] = 0.5 * (Vk.min(0) + Vk.max(0))

    # --- 가로 슬롯: 화면 폭과 외접구 지름 중 큰 쪽 --------------------------- #
    slot, ytop, hside = {}, {}, {}
    for k in keys:
        P = np.asarray(meshes[k].v, float) - cens[k]
        wx = float((P @ bT[0]).max() - (P @ bT[0]).min())
        wy = float((P @ bT[1]).max() - (P @ bT[1]).min())
        slot[k] = max(wx, 2.0 * A[k]["r_encl_m"])
        ytop[k] = max(wy / 2.0, A[k]["r_encl_m"])
        hside[k] = float((P @ bS[1]).max() - (P @ bS[1]).min())
    gap = 0.10 * max(slot.values())
    xs, cur = {}, 0.0
    for k in keys:
        xs[k] = cur + slot[k] / 2.0
        cur += slot[k] + gap
    total = cur - gap
    R = max(ytop.values())                   # 위 줄 반높이 [m]
    Hs = max(hside.values())                 # 아래 줄 높이 [m]

    fig = plt.figure(figsize=(19.4, 10.6))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.44],
                          left=0.016, right=0.990, top=0.855, bottom=0.088, hspace=0.02)

    # --- (a) top view, true relative scale ---------------------------------- #
    axT = fig.add_subplot(gs[0]); axT.set_axis_off()
    for k in keys:
        V = np.asarray(meshes[k].v, float) - cens[k] + np.array([xs[k], 0.0, 0.0])
        draw_mesh(axT, V, np.asarray(meshes[k].f, int), rgbs[k], bT)
        axT.add_patch(Circle((xs[k], 0.0), A[k]["r_encl_m"], fill=False, ls=(0, (4, 3)),
                             lw=1.0, ec="#b71c1c", zorder=4))
    axT.set_xlim(-gap, total + gap)
    axT.set_ylim(-R * 2.10, R * 1.30)
    axT.set_aspect("equal", adjustable="box")
    for k in keys:
        rec = A[k]
        axT.text(xs[k], -R * 1.10, rec["label"], ha="center", va="top",
                 fontsize=12.0, fontweight="bold")
        axT.text(xs[k], -R * 1.32,
                 f"{rec['lwh_full_mm'][0]:.0f} x {rec['lwh_full_mm'][1]:.0f} mm\n"
                 f"r = {rec['r_encl_m']:.3f} m\n"
                 f"kr {rec['kr']['LTE']:.1f} / {rec['kr']['5G']:.1f} / {rec['kr']['WiFi']:.1f}",
                 ha="center", va="top", fontsize=9.4, color="#333", linespacing=1.45)
    axT.text(0.0, R * 1.26, "Top view — one shared scale, every airframe at true relative size",
             fontsize=12.5, color="#222", va="top", ha="left")
    y_bar = R * 1.05
    axT.plot([0.0, 1.0], [y_bar] * 2, color="#222", lw=3.0, solid_capstyle="butt", zorder=6)
    for xx in (0.0, 1.0):
        axT.plot([xx, xx], [y_bar - 0.028 * R, y_bar + 0.028 * R], color="#222", lw=1.8, zorder=6)
    axT.text(0.5, y_bar - 0.05 * R, "1 m", ha="center", va="top", fontsize=10.0, color="#222")
    axT.text(total, R * 1.26, "dashed circle = enclosing-sphere radius r  (the r in kr)",
             fontsize=10.0, color="#b71c1c", ha="right", va="top")

    # --- (b) side view, same scale ------------------------------------------ #
    axS = fig.add_subplot(gs[1]); axS.set_axis_off()
    for k in keys:
        V = np.asarray(meshes[k].v, float) - cens[k] + np.array([xs[k], 0.0, 0.0])
        draw_mesh(axS, V, np.asarray(meshes[k].f, int), rgbs[k], bS)
    axS.set_xlim(-gap, total + gap)
    axS.set_ylim(-Hs * 1.65, Hs * 1.15)
    axS.set_aspect("equal", adjustable="box")
    axS.text(0.0, Hs * 1.10, "Side view — same scale as above; the airframes are flat",
             fontsize=12.5, color="#222", va="top", ha="left")
    for k in keys:
        axS.text(xs[k], -Hs * 0.72, f"H {A[k]['lwh_full_mm'][2]:.0f} mm",
                 ha="center", va="top", fontsize=9.4, color="#333")

    fig.suptitle("Seven airframes at true relative scale — the size spread is the story",
                 fontsize=17.0, fontweight="bold", y=0.976)
    fig.text(0.5, 0.933,
             f"{A[ss['largest']]['label']} spans {ss['largest_span_m']*1000:.0f} mm, "
             f"{A[ss['smallest']]['label']} spans {ss['smallest_span_m']*1000:.0f} mm — "
             f"a factor of {ss['span_ratio']:.2f}, and kr at 5G runs "
             f"{ss['kr_5g_min']:.1f} to {ss['kr_5g_max']:.1f}.  "
             f"Electrical size decides where physical optics holds, it sets sigma, "
             f"and sigma sets detection range.",
             ha="center", fontsize=11.2, color="#333")
    fig.text(0.016, 0.038,
             "Colour = pure material class: grey plastic (shell, canopy, gear, propellers)  ·  "
             "black carbon  ·  blue metal (motors, battery)  ·  orange camera assembly  ·  "
             f"green PCB — the same rule for all {meta['n_airframes']} airframes.",
             fontsize=9.4, color="#333", ha="left")
    fig.text(0.016, 0.014,
             f"Ordered by overall span. Mesh rebuilt from {' + '.join(MESH_SOURCES[:2])} "
             f"(newest edit {meta['mesh_source_newest']})  ·  every number injected from "
             f"outputs/mesh_gallery.json, generated {meta['generated']}",
             fontsize=7.8, color=GRAY, ha="left")

    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, "mesh_gallery_all.png")
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print("  🖼  outputs/figures/mesh_gallery_all.png")
    return p


# --------------------------------------------------------------------------- #
def build_all(keys=None, only="all"):
    keys = list(keys or drone_keys())
    J = None
    if only in ("all", "measure"):
        J = measure(keys)
    if J is None:
        J = _load_json(LEDGER)
        if J is None:
            raise SystemExit("outputs/mesh_gallery.json 이 없다 — --only measure 를 먼저 돌릴 것")
    if only in ("all", "airframes"):
        for k in keys:
            fig_airframe(k, J)
    if only in ("all", "gallery"):
        # ⭐ 갤러리는 **정의상 전 기종**이다. 부분 원장으로 그리면 "7종 상대크기" 그림이
        #   조용히 3종짜리가 된다 → 전 기종이 들어있는 원장이 아니면 그리지 않고 이유를 말한다.
        if sorted(J["airframes"]) != sorted(drone_keys()):
            print(f"  ⚠ 갤러리 건너뜀 — 원장에 {len(J['airframes'])}/{len(DRONES)}종만 있다. "
                  f"`--only gallery` 는 전 기종 계측 뒤에 돌릴 것.")
        else:
            fig_gallery(J)
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="all",
                    choices=["all", "measure", "airframes", "gallery"])
    ap.add_argument("--keys", default=None, help="쉼표 구분 (기본: 레지스트리 전부)")
    a = ap.parse_args()
    ks = [k.strip() for k in a.keys.split(",")] if a.keys else None
    build_all(ks, a.only)
    print("메쉬 갤러리 완료 →", os.path.relpath(FIG, ROOT))
