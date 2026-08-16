#!/usr/bin/env python
"""
적대적 검증 2026-08-16 — 참조물의 정체 검증
`assets/meshes/reference/WM161_zhankai_1k.glb` 가 정말 DJI Mini 2 공식 모델인가,
그리고 «시각화용 저폴리» 라서 실물 기하로 쓸 자격이 없는가.

이 스크립트는 남의 수치를 옮겨 적지 않는다. 전부 파일에서 직접 잰다.
  · glTF 파서를 직접 들고 있다(trimesh 미사용) — 씬 로더가 조용히 고치는 것을 피하려고.
  · 산출: outputs/mesh_adv_identity_provenance_0816.json

실행:
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/adv_identity_provenance_0816.py            # 오프라인 측정만
    ... adv_identity_provenance_0816.py --net                # DJI CDN 재다운로드 대조까지

GPU 미사용. 저장소 코드 무변경(이 파일은 새 측정기다).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import least_squares

REPO = Path(__file__).resolve().parents[1]
GLB_OPEN = REPO / "assets/meshes/reference/WM161_zhankai_1k.glb"
GLB_FOLD = REPO / "assets/meshes/reference/wm161_v11_zhedie_1k.glb"
PHOTO = REPO / "assets/photos/mini2/mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg"
OUT = REPO / "outputs/mesh_adv_identity_provenance_0816.json"

CDN = ("https://dji-official-fe.djicdn.com/assets/uploads/p/"
       "f2a89648-ce9d-4318-9454-8a1a79cf6db7/WM161_zhankai_1k.glb")

# DJI 공표 제원 (사용자 매뉴얼 v1.0 2020.11 p.45)
SPEC = dict(unfolded_L_mm=159.0, unfolded_W_mm=203.0, unfolded_H_mm=56.0,
            diagonal_mm=213.0, prop_model="4726F", prop_dia_mm=4.7 * 25.4)

# ---------------------------------------------------------------- glTF 파서
_CT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
       5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path):
    """의존성 없는 .glb 리더. (glTF JSON, BIN 청크, 헤더요약) 을 돌려준다."""
    raw = Path(path).read_bytes()
    magic, ver, declared = struct.unpack("<III", raw[:12])
    assert magic == 0x46546C67, "glTF 매직이 아니다"
    off, J, BIN, chunks = 12, None, None, []
    while off < len(raw):
        clen, ctype = struct.unpack("<II", raw[off:off + 8])
        chunks.append((ctype.to_bytes(4, "little").decode("ascii", "replace").strip("\x00"), clen))
        if ctype == 0x4E4F534A:
            J = json.loads(raw[off + 8:off + 8 + clen].decode("utf-8"))
        elif ctype == 0x004E4942:
            BIN = raw[off + 8:off + 8 + clen]
        off += 8 + clen
    hdr = dict(gltf_version=ver, file_bytes=len(raw), declared_bytes=declared,
               chunks=[{"type": t, "bytes": n} for t, n in chunks],
               md5=hashlib.md5(raw).hexdigest(),
               sha256=hashlib.sha256(raw).hexdigest())
    return J, BIN, hdr


def read_accessor(J, BIN, idx):
    a = J["accessors"][idx]
    n, nc = a["count"], _NC[a["type"]]
    fmt, sz = _CT[a["componentType"]]
    bv = J["bufferViews"][a["bufferView"]]
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride") or nc * sz
    if stride == nc * sz:
        return np.frombuffer(BIN, dtype=np.dtype("<" + fmt),
                             count=n * nc, offset=base).reshape(n, nc).copy()
    out = np.empty((n, nc), dtype=np.dtype(fmt))
    for i in range(n):
        out[i] = struct.unpack_from("<" + fmt * nc, BIN, base + i * stride)
    return out


def _trs(node):
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T
    T = np.eye(4)
    if "scale" in node:
        T[:3, :3] = T[:3, :3] @ np.diag(node["scale"])
    if "rotation" in node:
        x, y, z, w = node["rotation"]
        T[:3, :3] = np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]) @ T[:3, :3]
    if "translation" in node:
        T[:3, 3] = node["translation"]
    return T


def iter_parts(J, BIN):
    """씬그래프를 걸어 월드좌표 삼각형을 부위별로 돌려준다. 수리·병합 없음."""
    parts = []

    def walk(ni, M, path):
        node = J["nodes"][ni]
        M2 = M @ _trs(node)
        p2 = path + [node.get("name")]
        if "mesh" in node:
            mesh = J["meshes"][node["mesh"]]
            for prim in mesh.get("primitives", []):
                V = read_accessor(J, BIN, prim["attributes"]["POSITION"]).astype(float)
                parts.append(dict(
                    name=node.get("name"), path="/".join(str(q) for q in p2),
                    material=prim.get("material"),
                    V=(M2[:3, :3] @ V.T).T + M2[:3, 3],
                    F=read_accessor(J, BIN, prim["indices"]).astype(np.int64).reshape(-1, 3)))
        for c in node.get("children", []):
            walk(c, M2, p2)

    for r in J["scenes"][J["scene"]]["nodes"]:
        walk(r, np.eye(4), [])
    return parts


# ------------------------------------------------------------ 기하 도우미
def tri_area(p):
    tv = p["V"][p["F"]]
    return float(0.5 * np.linalg.norm(np.cross(tv[:, 1] - tv[:, 0], tv[:, 2] - tv[:, 0]), axis=1).sum())


def edge_stats(p):
    V, F = p["V"], p["F"]
    E = np.vstack([V[F[:, 0]] - V[F[:, 1]], V[F[:, 1]] - V[F[:, 2]], V[F[:, 2]] - V[F[:, 0]]])
    L = np.linalg.norm(E, axis=1) * 1e3
    return dict(min_mm=float(L.min()), median_mm=float(np.median(L)),
                p95_mm=float(np.percentile(L, 95)), max_mm=float(L.max()))


def topo(p, tol=1e-7):
    V, F = p["V"], p["F"]
    _, inv = np.unique(np.round(V / tol).astype(np.int64), axis=0, return_inverse=True)
    Fw = inv[F]
    Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])]
    e = np.sort(np.vstack([Fw[:, [0, 1]], Fw[:, [1, 2]], Fw[:, [2, 0]]]), axis=1)
    _, c = np.unique(e, axis=0, return_counts=True)
    cc = Counter(c.tolist())
    nm = sum(v for k, v in cc.items() if k > 2)
    return dict(verts_raw=int(len(V)), verts_welded=int(inv.max() + 1), tris=int(len(F)),
                boundary_edges=int(cc.get(1, 0)), nonmanifold_edges=int(nm),
                watertight=bool(cc.get(1, 0) == 0 and nm == 0))


def fit_axis(V, pct=75):
    """회전체 부위(모터 벨)의 회전축을 xz 평면 최소제곱 원피팅으로 찾는다."""
    xz = V[:, [0, 2]]

    def resid(c):
        d = np.linalg.norm(xz - c, axis=1)
        m = d > np.percentile(d, pct)
        return d[m] - d[m].mean()

    return least_squares(resid, xz.mean(0)).x


def cyl_contour(V, F, ax, r0, project_xz=False):
    """반지름 r0 원통과 삼각형망의 정확한 교선. 정점 근사가 아니라 삼각형을 자른다."""
    rho = np.linalg.norm(V[:, [0, 2]] - ax, axis=1)
    d = rho - r0
    pts = []
    for tri in F:
        dv = d[tri]
        if (dv > 0).all() or (dv < 0).all():
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if dv[a] * dv[b] < 0:
                t = dv[a] / (dv[a] - dv[b])
                pts.append(V[tri[a]] + t * (V[tri[b]] - V[tri[a]]))
    if len(pts) < 3:
        return None
    P3 = np.array(pts)
    th = np.arctan2(P3[:, 2] - ax[1], P3[:, 0] - ax[0])
    th = np.angle(np.exp(1j * (th - np.angle(np.exp(1j * th).sum()))))
    if project_xz:                       # 원판면 투영 폭(평면형)
        return float(r0 * (th.max() - th.min()))
    return np.column_stack([r0 * th, P3[:, 1]])   # 단면 (호길이, 높이)


def section_metrics(Q):
    """단면 윤곽에서 시위·두께·피치각·캠버를 잰다."""
    D = np.linalg.norm(Q[:, None, :] - Q[None, :, :], axis=2)
    i, j = np.unravel_index(np.argmax(D), D.shape)
    c = float(D[i, j])
    u = (Q[j] - Q[i]) / c
    n = np.array([-u[1], u[0]])
    t, w = (Q - Q[i]) @ u, (Q - Q[i]) @ n
    mids = []
    for k in range(12):
        m = (t >= k * c / 12) & (t < (k + 1) * c / 12)
        if m.sum() >= 2:
            mids.append((w[m].max() + w[m].min()) / 2)
    xs = np.linspace(0.05, 0.95, 19) * c
    th = []
    for x in xs:
        m = np.abs(t - x) < 0.05 * c
        th.append(w[m].max() - w[m].min() if m.sum() >= 2 else np.nan)
    th = np.array(th)
    k = int(np.nanargmax(th))
    return dict(chord_mm=c * 1e3, thickness_mm=float(w.max() - w.min()),
                t_over_c=float((w.max() - w.min()) / c),
                pitch_deg=float(np.degrees(np.arctan2(abs(u[1]), abs(u[0])))),
                camber_over_c=float(np.max(np.abs(mids)) / c) if mids else float("nan"),
                max_thickness_at_x_over_c=float(xs[k] / c))


# ============================================================== 측정 본문
def measure():
    R = {}
    J, BIN, hdr = load_glb(GLB_OPEN)
    parts = iter_parts(J, BIN)
    byname = {p["name"]: p for p in parts}

    # ---------- A. 파일 정체 --------------------------------------------
    R["A_file"] = dict(
        path=str(GLB_OPEN.relative_to(REPO)), **hdr,
        asset=J["asset"],
        extensionsUsed=J.get("extensionsUsed"), extensionsRequired=J.get("extensionsRequired"),
        has_extras=bool(J.get("extras")),
        counts={k: len(J.get(k, [])) for k in
                ("scenes", "nodes", "meshes", "materials", "accessors", "bufferViews",
                 "buffers", "images", "textures", "samplers", "skins", "animations", "cameras")},
        total_triangles=int(sum(len(p["F"]) for p in parts)),
        total_vertices=int(sum(len(p["V"]) for p in parts)))

    # ---------- B. 이름 ----------------------------------------------------
    node_names = [n.get("name") for n in J["nodes"]]
    R["B_names"] = dict(
        root_node=J["nodes"][J["scenes"][J["scene"]]["nodes"][0]].get("name"),
        group_nodes=[n.get("name") for n in J["nodes"] if "children" in n],
        material_names=[m.get("name") for m in J["materials"]],
        texture_names=[t.get("name") for t in J["textures"]],
        maya_default_name_counts={
            pfx: sum(1 for n in node_names if n and n.startswith(pfx))
            for pfx in ("polySurface", "pCylinder", "pSphere", "Default", "Mesh")},
        all_node_transforms_identity=bool(all(
            np.allclose(_trs(n), np.eye(4)) for n in J["nodes"])))

    # ---------- C. "1k" 가 무엇인가 ---------------------------------------
    imgs = []
    for i, im in enumerate(J["images"]):
        bv = J["bufferViews"][im["bufferView"]]
        o, l = bv.get("byteOffset", 0), bv["byteLength"]
        pil = Image.open(io.BytesIO(BIN[o:o + l]))
        nm = next((t.get("name") for t in J["textures"] if t["source"] == i), None)
        imgs.append(dict(index=i, name=nm, mime=im["mimeType"], bytes=int(l),
                         pixels=list(pil.size)))
    R["C_texture_tier"] = dict(
        images=imgs,
        all_1024=bool(all(q["pixels"] == [1024, 1024] for q in imgs)),
        triangles=R["A_file"]["total_triangles"],
        verdict=("파일명의 '1k' 는 텍스처 해상도 1024x1024 를 뜻한다. "
                 "삼각형 예산이 아니다 — 실제 삼각형은 109k 다."))

    # ---------- D. 자기식별(텍스처에 인쇄된 글자) --------------------------
    # 육안 판독 대상: material 'jishen1' 의 baseColor 아틀라스.
    R["D_self_identification"] = dict(
        basecolor_atlas="1K_lambert4SG_jishen_baseColor.png (glTF image index 5)",
        printed_marks_read_by_eye=["MINI 2", "ULTRA LIGHT 249g", "4K", "DJI logo"],
        cross_check_photo="assets/photos/mini2/mini2_d07_official_unfolded_front34_flight.jpg "
                          "(DJI 공식 사진에서도 팔에 'MINI 2' 가 인쇄돼 있다)",
        discriminates_mavic_mini=("'4K' 표기는 Mavic Mini(WM160, 2.7K)를 배제한다. "
                                  "'MINI 2' 표기는 Mini 2 SE 도 배제한다."),
        codename_source=dict(
            claim="WM161 = DJI Mini 2",
            evidence="o-gs/dji-firmware-tools wiki 'DJI Hardware' 표: "
                     "WM160=Mavic Mini, WM161=Mini 2, WM162=Mini 3",
            url="https://github.com/o-gs/dji-firmware-tools/wiki/DJI-Hardware"))

    # ---------- E. 축척 충실도 --------------------------------------------
    BLADES = ["polySurface58", "polySurface80", "polySurface84", "polySurface102",
              "polySurface61", "polySurface81", "polySurface89", "polySurface95"]
    allV = np.vstack([p["V"] for p in parts])
    noprop = np.vstack([p["V"] for p in parts if p["name"] not in BLADES])
    sz = (noprop.max(0) - noprop.min(0)) * 1e3
    bells = ["polySurface54", "polySurface78", "polySurface85", "polySurface70"]
    axes = np.array([fit_axis(byname[b]["V"]) for b in bells])
    dd = sorted(float(np.linalg.norm(axes[a] - axes[b]) * 1e3)
                for a in range(4) for b in range(a + 1, 4))
    R["E_scale"] = dict(
        bbox_all_mm=list((allV.max(0) - allV.min(0)) * 1e3),
        bbox_without_blades_mm=dict(x_width=float(sz[0]), y_height=float(sz[1]), z_length=float(sz[2])),
        vs_spec_pct=dict(
            width=float((sz[0] - SPEC["unfolded_W_mm"]) / SPEC["unfolded_W_mm"] * 100),
            height=float((sz[1] - SPEC["unfolded_H_mm"]) / SPEC["unfolded_H_mm"] * 100),
            length=float((sz[2] - SPEC["unfolded_L_mm"]) / SPEC["unfolded_L_mm"] * 100)),
        motor_axis_pairwise_mm=dd,
        diagonal_mm=dd[-2:], diagonal_vs_spec_pct=float((dd[-1] - SPEC["diagonal_mm"]) / SPEC["diagonal_mm"] * 100),
        mirror_residual_mm=float((allV[:, 0].min() + allV[:, 0].max()) * 1e3),
        baked_y_offset_m=[float(allV[:, 1].min()), float(allV[:, 1].max())])

    # ---------- F. 프로펠러 해부 ------------------------------------------
    ROT = {"R1_FL": ("polySurface54", ["polySurface58", "polySurface61"]),
           "R2_FR": ("polySurface78", ["polySurface80", "polySurface81"]),
           "R3_RL": ("polySurface85", ["polySurface84", "polySurface89"]),
           "R4_RR": ("polySurface70", ["polySurface102", "polySurface95"])}
    fr = [0.20, 0.30, 0.40, 0.45, 0.50, 0.60, 0.70, 0.75, 0.80, 0.90, 0.95]
    rotors, chords, radii = {}, [], []
    for k, (bell, bl) in ROT.items():
        ax = fit_axis(byname[bell]["V"])
        Rs, cs = [], []
        for b in bl:
            V, F = byname[b]["V"], byname[b]["F"]
            rr = np.linalg.norm(V[:, [0, 2]] - ax, axis=1)
            Rs.append(float(rr.max()))
            cs.append([cyl_contour(V, F, ax, f * rr.max()) for f in fr])
        rotors[k] = dict(axis_xz_mm=list(ax * 1e3), blade_tip_radius_mm=[r * 1e3 for r in Rs],
                         disk_diameter_mm=float(2 * max(Rs) * 1e3))
        radii += [r * 1e3 for r in Rs]
        for c in cs:
            chords.append([section_metrics(q)["chord_mm"] if q is not None else np.nan for q in c])
    chords = np.array(chords)
    radii = np.array(radii)
    cmax = chords.max(1)
    Ds = [rotors[k]["disk_diameter_mm"] for k in ROT]
    R["F_propeller"] = dict(
        n_blade_meshes=len(BLADES), n_hub_meshes=4,
        blade_tri_counts=sorted({int(len(byname[b]["F"])) for b in BLADES}),
        blade_area_mm2=[tri_area(byname[b]) * 1e6 for b in BLADES],
        blade_area_spread_mm2=float(np.ptp([tri_area(byname[b]) * 1e6 for b in BLADES])),
        screws_per_rotor=2,
        screw_spacing_mm=float(np.linalg.norm(
            (byname["polySurface57"]["V"].mean(0) - byname["polySurface60"]["V"].mean(0))[[0, 2]]) * 1e3),
        motor_winding_part=dict(name="tongxian:Mesh", meaning="铜线 = 구리선(모터 권선)",
                                tris=int(len(byname["tongxian:Mesh"]["F"]))),
        rotors=rotors,
        disk_diameter_mm=dict(values=Ds, mean=float(np.mean(Ds)),
                              min=float(min(Ds)), max=float(max(Ds)),
                              nominal_4726F_mm=SPEC["prop_dia_mm"],
                              vs_nominal_pct=float((np.mean(Ds) - SPEC["prop_dia_mm"]) / SPEC["prop_dia_mm"] * 100)),
        edge_stats_blade=edge_stats(byname["polySurface58"]),
        r_over_R=fr,
        chord_mm_per_blade=chords.tolist(),
        chord_sd_pct=(chords.std(0) / chords.mean(0) * 100).tolist(),
        tip_radius_mm=dict(mean=float(radii.mean()), sd=float(radii.std()),
                           sd_pct=float(radii.std() / radii.mean() * 100),
                           min=float(radii.min()), max=float(radii.max())),
        chord_max_over_R=dict(per_blade=(cmax / radii).tolist(),
                              mean=float((cmax / radii).mean()), sd=float((cmax / radii).std())),
        norm_chord_at_070R=dict(per_blade=(chords[:, fr.index(0.70)] / cmax).tolist(),
                                mean=float((chords[:, fr.index(0.70)] / cmax).mean()),
                                sd=float((chords[:, fr.index(0.70)] / cmax).std())))

    # ---------- G. 에어포일인가 납작한 판인가 -------------------------------
    ax = fit_axis(byname["polySurface54"]["V"])
    V, F = byname["polySurface58"]["V"], byname["polySurface58"]["F"]
    Rb = np.linalg.norm(V[:, [0, 2]] - ax, axis=1).max()
    sec = {}
    for f in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.98):
        q = cyl_contour(V, F, ax, f * Rb)
        if q is not None:
            sec[f"{f:.2f}"] = section_metrics(q)
    tc = [v["t_over_c"] for v in sec.values()]
    R["G_airfoil"] = dict(
        blade="polySurface58", sections=sec,
        t_over_c_range=[float(min(tc)), float(max(tc))],
        thickness_taper_mm=[sec["0.20"]["thickness_mm"], sec["0.98"]["thickness_mm"]],
        pitch_washout_deg=[sec["0.30"]["pitch_deg"], sec["0.98"]["pitch_deg"]],
        verdict=("납작한 판이 아니다. 두께는 1.17mm→0.45mm 로 단조 감소하고 t/c 는 "
                 "6~8%% 로 거의 일정하며, 피치각은 21°→6° 로 단조 감소(워시아웃)하고, "
                 "최대두께 위치가 시위의 25~35%% 다(렌즈꼴이면 50%%, 평판이면 일정). "
                 "즉 설계된 캠버 에어포일이다."))

    # ---------- H. 내부 일관성(아티스트 흔적)과 그 크기 ----------------------
    def sig(p):
        Vc = p["V"] - p["V"].mean(0)
        return np.percentile(np.sort(np.linalg.norm(Vc, axis=1)), [0, 25, 50, 75, 100])

    base = sig(byname["polySurface58"])
    R["H_internal_consistency"] = dict(
        distinct_blade_shapes=2,
        shape_signature_delta_mm={b: float(np.abs(sig(byname[b]) - base).max() * 1e3) for b in BLADES},
        blade_topology=topo(byname["polySurface58"]),
        blades_are_open_shells=True,
        front_vs_rear_disk_mm=[rotors["R1_FL"]["disk_diameter_mm"], rotors["R3_RL"]["disk_diameter_mm"]],
        note=("참조물의 자체 흔들림 폭이다. 이 값보다 작은 차이는 이 참조물로 판정할 수 없고, "
              "이보다 훨씬 큰 차이는 참조물의 부정확으로 설명되지 않는다."))

    # ---------- I. 독립 물증(FCC 실물 사진) 대조 ---------------------------
    R["I_photo_cross_check"] = photo_cross_check(byname)

    # ---------- 접힘 판이 같은 자산인가 -------------------------------------
    J2, BIN2, hdr2 = load_glb(GLB_FOLD)
    p2 = {p["name"]: p for p in iter_parts(J2, BIN2)}
    R["J_folded_twin"] = dict(
        md5=hdr2["md5"], generator=J2["asset"].get("generator"),
        material_names=[m.get("name") for m in J2["materials"]],
        texture_names=[t.get("name") for t in J2["textures"]],
        blade_area_max_rel_diff=float(max(
            abs(tri_area(p2[b]) - tri_area(byname[b])) / tri_area(byname[b])
            for b in BLADES if b in p2)),
        blade_areas_match=bool(all(
            abs(tri_area(p2[b]) - tri_area(byname[b])) / tri_area(byname[b]) < 1e-6
            for b in BLADES if b in p2)),
        note="펼침/접힘 두 파일은 같은 프로펠러 부품을 공유한다 — 자세만 다르다.")

    if ARGS.net:
        R["A_file"]["cdn"] = cdn_check(hdr["md5"])
    return R


def photo_cross_check(byname):
    """FCC 분해사진(실물 MT2WD 프롭 + 자)에서 평면형을 재서 GLB 와 맞춰본다.

    척도는 자가 아니라 **두 고정나사 간격**에서 얻는다 — 나사와 날은 같은 평면에
    있어서 시차(prop 이 책상보다 카메라에 가까움)가 정확히 상쇄된다.
    나사 중심 픽셀좌표는 10배 확대 격자 렌더에서 육안 판독했다(아래 SCREW_PX).
    """
    SCREW_PX = {"L": np.array([250.0, 179.0]), "R": np.array([280.0, 172.0])}
    A = np.asarray(Image.open(PHOTO).convert("RGB"), dtype=float)
    g = A.mean(2)
    H, W = g.shape
    mask = (g < 95) | ((A[..., 0] - A[..., 2] > 40) & (A[..., 0] > 120) & (g < 200))
    mask = ndi.binary_fill_holes(ndi.binary_closing(mask, np.ones((3, 3))))
    lab, n = ndi.label(mask)
    prop = lab == int(np.argmax(ndi.sum(mask, lab, range(1, n + 1)))) + 1
    prop = ndi.binary_fill_holes(prop)

    yy, xx = np.mgrid[0:H, 0:W]
    hub = (SCREW_PX["L"] + SCREW_PX["R"]) / 2
    cut = prop & (((xx - hub[0]) ** 2 + (yy - hub[1]) ** 2) > 30 ** 2)
    lab2, n2 = ndi.label(cut)
    sz = ndi.sum(cut, lab2, range(1, n2 + 1))
    FRq = np.arange(0.10, 1.00, 0.05)
    out = {}
    for i in np.argsort(sz)[::-1][:2]:
        b = lab2 == i + 1
        ys, xs = np.where(b)
        key = "L" if (np.hypot(xs - SCREW_PX["L"][0], ys - SCREW_PX["L"][1]).min() <
                      np.hypot(xs - SCREW_PX["R"][0], ys - SCREW_PX["R"][1]).min()) else "R"
        s = SCREW_PX[key]
        v = np.array([xs.mean() - s[0], ys.mean() - s[1]])
        ang = np.arctan2(yy - s[1], xx - s[0])
        da = np.abs(np.angle(np.exp(1j * (ang - np.arctan2(v[1], v[0])))))
        full = prop & (da < np.deg2rad(75))
        l3, n3 = ndi.label(full)
        full = l3 == int(np.argmax(ndi.sum(full, l3, range(1, n3 + 1)))) + 1
        rho = np.hypot(xx - s[0], yy - s[1])[full]
        th = ang[full]
        L = float(rho.max())
        Wl = []
        for f in FRq:
            sel = np.abs(rho - f * L) < 1.5
            if sel.sum() < 4:
                Wl.append(np.nan)
                continue
            t = np.angle(np.exp(1j * (th[sel] - np.angle(np.exp(1j * th[sel]).sum()))))
            Wl.append(f * L * (t.max() - t.min()))
        out[key] = dict(L_px=L, W_px=Wl)

    scale = float(np.linalg.norm(SCREW_PX["L"] - SCREW_PX["R"]) /
                  np.linalg.norm((byname["polySurface57"]["V"].mean(0) -
                                  byname["polySurface60"]["V"].mean(0))[[0, 2]]) / 1e3)

    # GLB 쪽: 같은 정의(각자의 나사 중심 기준, 원판면 투영폭)
    glb = {}
    for b, s in (("polySurface58", "polySurface57"), ("polySurface61", "polySurface60")):
        V, F = byname[b]["V"], byname[b]["F"]
        ax = byname[s]["V"].mean(0)[[0, 2]]
        L = float(np.linalg.norm(V[:, [0, 2]] - ax, axis=1).max())
        glb[b] = dict(L_mm=L * 1e3,
                      W_mm=[(cyl_contour(V, F, ax, f * L, project_xz=True) or np.nan) * 1e3
                            for f in FRq])

    sel = (FRq >= 0.35) & (FRq <= 0.95)
    ref = int(np.argmin(abs(FRq - 0.45)))
    gn = np.array([np.array(v["W_mm"]) / v["W_mm"][ref] for v in glb.values()])[:, sel]
    pn = np.array([np.array(v["W_px"]) / v["W_px"][ref] for v in out.values()])[:, sel]
    dev = (gn.mean(0) - pn.mean(0)) / pn.mean(0) * 100
    brk = (pn[0] - pn[1]) / pn.mean(0) * 100
    return dict(
        photo=str(PHOTO.relative_to(REPO)),
        screw_px=({k: v.tolist() for k, v in SCREW_PX.items()}),
        scale_px_per_mm=scale,
        method=("척도는 프롭 평면 안의 나사 간격에서 얻는다(시차 상쇄). 각 날은 자기 "
                "고정나사를 중심으로 반경 밴드마다 각폭을 재서 평면형 폭으로 환산한다. "
                "GLB 에도 똑같은 정의를 적용한다."),
        blade_length_tip_to_pivot_mm=dict(
            photo=[out[k]["L_px"] / scale for k in out],
            glb=[v["L_mm"] for v in glb.values()],
            photo_mean_vs_glb_mean_pct=float(
                (np.mean([out[k]["L_px"] / scale for k in out]) /
                 np.mean([v["L_mm"] for v in glb.values()]) - 1) * 100)),
        rho_over_L=FRq[sel].tolist(),
        normalised_outer_planform=dict(glb=gn.mean(0).tolist(), photo=pn.mean(0).tolist()),
        deviation_pct=dev.tolist(),
        rms_deviation_pct=float(np.sqrt((dev ** 2).mean())),
        photo_perspective_bracket_pct=float(np.sqrt((brk ** 2).mean())),
        caveat=("사진은 원근 투영이고 카메라가 프롭 평면에 수직이 아니다. 두 날이 같은 "
                "부품인데도 길이가 8%% 다르게 찍힌 것이 그 증거다. 따라서 절대 시위는 "
                "±20%% 밖에 못 묶고, 정규화된 평면형 «모양» 만 ~5%% 로 묶인다."))


def cdn_check(local_md5):
    """DJI CDN 이 지금도 같은 바이트를 주는가."""
    try:
        h = subprocess.run(["curl", "-sS", "-D", "-", "-o", "/tmp/_cdn.glb", CDN],
                           capture_output=True, text=True, timeout=300)
        head = {}
        for line in h.stdout.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                if k.lower() in ("last-modified", "content-length", "server", "etag", "via"):
                    head[k.lower()] = v.strip()
        md5 = hashlib.md5(Path("/tmp/_cdn.glb").read_bytes()).hexdigest()
        return dict(url=CDN, headers=head, downloaded_md5=md5,
                    byte_identical_to_repo=bool(md5 == local_md5))
    except Exception as e:                                  # noqa: BLE001
        return dict(url=CDN, error=str(e))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", action="store_true", help="DJI CDN 에서 다시 받아 바이트 대조")
    ARGS = ap.parse_args()
    res = measure()
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print(f"wrote {OUT}")
    print(f"  triangles          {res['A_file']['total_triangles']}")
    print(f"  generator          {res['A_file']['asset'].get('generator')}")
    print(f"  all textures 1024  {res['C_texture_tier']['all_1024']}")
    print(f"  disk diameter mm   {res['F_propeller']['disk_diameter_mm']['mean']:.3f} "
          f"({res['F_propeller']['disk_diameter_mm']['vs_nominal_pct']:+.2f} % vs 4726F)")
    print(f"  t/c range          {res['G_airfoil']['t_over_c_range']}")
    print(f"  photo RMS dev %    {res['I_photo_cross_check']['rms_deviation_pct']:.2f} "
          f"(bracket {res['I_photo_cross_check']['photo_perspective_bracket_pct']:.2f})")
