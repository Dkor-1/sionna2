# -*- coding: utf-8 -*-
"""
mesh_impact_l2_probe_0816.py — **2층 수리 하나를 켠 상태를 재는 자**
==============================================================================

이 자는 값을 넣지 않는다. **켜고 끄고 재기만 한다.**

왜 «소스 트리를 인자로» 받나
  이 라운드가 도는 동안 다른 라운드가 같은 파일을 계속 고친다. 저장소 소스를 직접 재면
  내 대조에 남의 편집이 섞여 **귀속이 깨진다**. 드라이버가 `src/` 를 통째로 얼린 스냅샷을
  만들고, 이 자를 **수리 조합마다 별도 프로세스**로 그 스냅샷 위에서 돌린다.
  ⇒ 한 원장 안의 모든 수치는 **소스 스냅샷 하나**에서 나온다(파일별 sha256 을 원장에 박는다).

왜 환경변수(`MESH_FIX`)로 켜나
  스위치 통로가 둘이다 — 환경변수는 cadkit(i5)·geom(m6)·drone_cad(battery·i4·m4)·
  rcs_po(i3) 를 **전부** 켜지만, 인자(`build_drone(spec, mesh_fix=…)`)는 drone_cad 담당
  수리만 켠다. 여러 수리를 함께 켜는 이 라운드는 환경변수만 쓴다.

무엇을 재나 (수리 조합 하나에 대해, 기체 10종)
  1. 지문 — 드론 / 프레임 / **프로펠러(CCW·CW)** 의 sha256(정점 float64 ‖ 면 int64 ‖ 그룹).
     ⭐프로펠러 지문 = «움직이는 성분을 건드렸나» 의 직접 증거다.
  2. 형상 — 면 수 · 표면적 · 그룹별 면수/면적 · 외형보정 배율 · **로터 중심 좌표**
     (로터가 움직이면 프롭이 움직인 것이다 — 메쉬가 같아도 md 축이 움직인다).
  3. σ — 우리 커널 PO(CPU · 가림 없음 · 재질 가중 |Γ|), 2층 수리 라운드들과 **같은 규약**:
     fc 3.5 GHz · 5G 100 MHz 9점 비코히런트 대역평균 · 점간격 λ/7 · 방위 2° 격자(180점) ·
     배치 3종 = 모노 el 0° / 모노 el −30° / 바이스태틱 β 120° el −30°.
  4. **프롭만의 σ** — 같은 점구름에서 'prop' 그룹 점만 골라 잰다(재샘플링 없음).
     프레임 수리는 이 값을 **한 비트도** 안 바꿔야 한다.
  5. i3(매몰면 마스크)가 켜졌으면 — 어느 그룹의 면이 몇 장·몇 mm² 빠졌나.

⛔ GPU 미사용 · git 미사용 · 소스 편집 없음(이 자는 읽기만 한다).

사용:
  CUDA_VISIBLE_DEVICES="" MESH_FIX=i5 python benchmark/mesh_impact_l2_probe_0816.py \
      --src <스냅샷 src> --out <json> [--keys mini2,mavic4pro]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

FLEET = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4",
         "m350rtk", "x500v2", "s1000plus", "typhoonh480"]

FC = 3.5e9
BW = 100e6
N_F = 9
DIV = 7.0                                   # 점 간격 = λ/DIV
AZ_STEP = 2.0                               # 180 방위 — 2층 수리 라운드 원장과 같다
GEOMS = (("mono_el0", 0.0, 0.0), ("mono_el-30", -30.0, 0.0), ("bi_b120_el-30", -30.0, 120.0))

#  ⚠ ITU 'metal' 만 Sionna RT(=GPU)를 타므로 저장소가 이미 캐시한 3.5 GHz 값을 쓴다
#    (outputs/mesh_compare_material.json :: materials.metal.gamma_po_5g). 나머지는 CPU 표에서 나온다.
METAL_GAMMA_5G = 0.9998026802895116


def sha(*arrs) -> str:
    h = hashlib.sha256()
    for a in arrs:
        h.update(np.ascontiguousarray(a).tobytes() if not isinstance(a, bytes) else a)
    return h.hexdigest()[:16]


def fingerprint(mesh) -> str:
    """정점 좌표(float64) ‖ 면 인덱스(int64) ‖ 그룹 이름. 1 bit 만 달라도 바뀐다.
    ⭐ 앞선 수리 라운드(mesh_fix_holes_poles_0816.fingerprint)와 **같은 정의**라 표가 이어진다."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(mesh.v, float)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(mesh.f, np.int64)).tobytes())
    h.update("|".join(mesh.g).encode())
    return h.hexdigest()[:16]


def tri_area_mm2(mesh) -> np.ndarray:
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, int)
    return np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2 * 1e6


# --------------------------------------------------------------------------- #
#  PO — 모노는 **출하 커널 그대로**, 바이스태틱만 같은 식으로 확장
# --------------------------------------------------------------------------- #
def _look(rp, az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg))
    el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def sigma_bistatic(rp, P, N, dA, w, fc, az_deg, el_deg, beta_deg, chunk=24):
    """바이스태틱 스칼라 PO σ(az) — 2층 수리 라운드들이 쓴 식 그대로:
       E = Σ [n̂·û_i>0][n̂·û_s>0] |Γ| (n̂·û_i) ΔA · exp(j k P·(û_i+û_s)),  σ = 4π/λ²|E|².
    β=0 에서 출하 커널(rcs_from_points)로 정확히 되돌아간다(드라이버가 그것을 잰다)."""
    lam = rp.C0 / fc
    k = 2 * np.pi / lam
    Ui = _look(rp, np.asarray(az_deg) - beta_deg / 2.0, el_deg)
    Us = _look(rp, np.asarray(az_deg) + beta_deg / 2.0, el_deg)
    amp = dA if w is None else dA * w
    out = np.empty(len(Ui), complex)
    for s in range(0, len(Ui), chunk):
        a, b = Ui[s:s + chunk], Us[s:s + chunk]
        NI = N @ a.T
        NS = N @ b.T
        PH = P @ (a + b).T
        g = np.where((NI > 0) & (NS > 0), NI, 0.0)
        out[s:s + chunk] = (g * amp[:, None] * np.exp(1j * k * PH)).sum(axis=0)
    return (4 * np.pi / lam ** 2) * np.abs(out) ** 2


def sigma_band(rp, P, N, dA, w, az, el_deg, beta_deg):
    """대역평균 σ(az) — 5G 100 MHz·9점 비코히런트. 단일주파수 널은 rcs_po 자신이
    «개별적으로는 수치 아티팩트» 라고 선언한 값이라 방위별 dB 는 대역평균으로 읽는다."""
    acc = 0.0
    for f in np.linspace(FC - BW / 2, FC + BW / 2, N_F):
        if beta_deg == 0.0:
            acc = acc + rp.rcs_from_points(P, N, dA, f, az, el_deg, w=w)   # ⭐출하 커널
        else:
            acc = acc + sigma_bistatic(rp, P, N, dA, w, f, az, el_deg, beta_deg)
    return acc / N_F


# --------------------------------------------------------------------------- #
def measure(key, dr, rp, mb, gm, az):
    spec = dr.DRONES[key]
    dr._FIT_CACHE.clear()
    out = {}
    t0 = time.time()
    mesh = dr.build_drone(spec)
    frame = dr.build_frame(spec)
    prop_ccw = dr.build_propeller(spec)
    prop_cw = dr.build_propeller(spec, mirror=True)

    A = tri_area_mm2(mesh)
    G = np.asarray(mesh.g)
    out["fp_drone"] = fingerprint(mesh)
    out["fp_frame"] = fingerprint(frame)
    out["fp_prop_ccw"] = fingerprint(prop_ccw)
    out["fp_prop_cw"] = fingerprint(prop_cw)
    out["n_faces"] = int(len(mesh.f))
    out["n_verts"] = int(len(mesh.v))
    out["area_mm2"] = round(float(A.sum()), 6)
    out["groups"] = {g: dict(n=int((G == g).sum()), area_mm2=round(float(A[G == g].sum()), 6))
                     for g in sorted(set(G.tolist()))}
    out["fit_scale"] = [round(float(v), 12) for v in dr.frame_fit_scale(spec)]
    out["rotor_centers_mm"] = [[round(float(c) * 1000, 9) for c in r["center"]]
                               for r in dr.rotor_layout(spec)]

    #  i3 — 매몰면 마스크(출하 경로 rcs_po.drone_rcs_pattern 의 PO 갈래와 같은 호출)
    from geom import mesh_fix_enabled
    fmask = None
    if mesh_fix_enabled("i3"):
        fmask = mb.keep_face_mask(mesh, kind="defect")
        rem = ~np.asarray(fmask, bool)
        out["i3"] = dict(
            n_faces_removed=int(rem.sum()),
            area_removed_mm2=round(float(A[rem].sum()), 6),
            by_group={g: dict(n=int((rem & (G == g)).sum()),
                              area_mm2=round(float(A[rem & (G == g)].sum()), 6))
                      for g in sorted(set(G[rem].tolist()))},
        )

    #  점구름 한 번만 깐다 — 프롭만의 σ 도 **같은 점구름**에서 골라 낸다(재샘플링 금지).
    P, N, dA, w, fidx = rp.mesh_to_points(mesh, rp.C0 / FC / DIV, gamma=gm,
                                          face_mask=fmask, return_face_idx=True)
    is_prop = (G[fidx] == "prop")
    out["n_pts"] = int(len(dA))
    out["n_pts_prop"] = int(is_prop.sum())
    out["sigma"] = {}
    out["sigma_prop"] = {}
    for name, el, beta in GEOMS:
        s = sigma_band(rp, P, N, dA, w, az, el, beta)
        out["sigma"][name] = [float(v) for v in s]
        sp = sigma_band(rp, P[is_prop], N[is_prop], dA[is_prop], w[is_prop], az, el, beta)
        out["sigma_prop"][name] = [float(v) for v in sp]
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--keys", default="")
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    sys.path.insert(0, src)
    import drones as dr
    import rcs_po as rp
    import mesh_buried as mb
    from materials import gamma_po
    assert os.path.dirname(os.path.abspath(dr.__file__)) == src, \
        f"엉뚱한 트리를 import 했다: {dr.__file__}"

    gm = {g: (METAL_GAMMA_5G if m == "metal" else gamma_po(m, FC))
          for g, (m, _) in dr.DRONE_GROUP_MAT.items()}
    az = np.arange(0.0, 360.0, AZ_STEP)
    keys = [k for k in (a.keys.split(",") if a.keys else FLEET) if k]

    t0 = time.time()
    out = dict(_meta=dict(
        src=src, mesh_fix=os.environ.get("MESH_FIX", ""),
        ts_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        fc_hz=FC, bw_hz=BW, n_f=N_F, spacing=f"lambda/{DIV:g}", az_step_deg=AZ_STEP,
        geoms=[list(g) for g in GEOMS], gamma_metal=METAL_GAMMA_5G,
        src_sha256={f: hashlib.sha256(open(os.path.join(src, f), "rb").read()).hexdigest()[:16]
                    for f in ("drone_cad.py", "drones.py", "cadkit.py", "geom.py",
                              "rcs_po.py", "mesh_buried.py", "mesh_check.py")}),
        drones={})
    #  ⚠ 기체마다 **바로 저장**한다. 이 기계는 메모리 압박(PSI full 46 %)으로 언제 느려질지
    #    모르고, 끝에 한 번만 쓰면 중간에 끊길 때 아무 것도 안 남는다(1차 시도에서 실제로 그랬다).
    for k in keys:
        out["drones"][k] = measure(k, dr, rp, mb, gm, az)
        out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
        with open(a.out, "w") as fh:
            json.dump(out, fh, ensure_ascii=False)
        print(f"  [{os.environ.get('MESH_FIX','off')}] {k} {time.time()-t0:.0f}s", flush=True)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out["_meta"]["complete"] = True
    with open(a.out, "w") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"[probe {os.environ.get('MESH_FIX','off')}] {a.out} "
          f"({os.path.getsize(a.out)/1024:.0f} KB, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
