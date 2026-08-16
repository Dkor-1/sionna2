# -*- coding: utf-8 -*-
"""검증 C — σ 영향의 **독립 재계산**.

독립성의 근거(무엇을 안 빌려 썼나)
  · 점 샘플러를 새로 썼다 — 저장소의 `mesh_to_points`(바리센트릭 격자)가 아니라
    **삼각형 4분할 재귀 + 무게중심**이다. 같은 형상이라도 점 배치가 다르다.
  · σ 식도 새로 썼다(`rcs_from_points` 를 안 부른다).
  · 격자가 다르다 — 방위 1°부터 3° 간격(120점, 저쪽은 0°부터 2° 180점),
    점 간격 λ/6(저쪽 λ/7), 주파수 5점(저쪽 9점).
  ⇒ 절대 σ 는 당연히 조금 다르다. **Δ(수리 후 − 전)** 가 같은 방향·같은 크기로 나오는지만 본다.

⛔ CPU 전용. 저장소 파일 수정 없음.
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.pop("MESH_FIX", None)
sys.path.insert(0, "/workspace/sionna/src")

C0 = 299792458.0
FC = 3.5e9
BW = 100e6
NF = 5
DIV = 6.0
AZ = np.arange(1.0, 360.0, 3.0)          # 120점, 1° offset
GEOMS = (("mono_el0", 0.0, 0.0), ("mono_el-30", -30.0, 0.0), ("bi_b120_el-30", -30.0, 120.0))
METAL_GAMMA_5G = 0.9998026802895116


def sampler(mesh, spacing, gamma, face_keep=None):
    """삼각형을 4분할로 잘게 쪼갠 뒤 **무게중심 1점**씩. (저장소 샘플러와 다른 방식)"""
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    if face_keep is not None:
        sel = np.asarray(face_keep, bool)
        F, G = F[sel], G[sel]
    T = V[F]                                  # (nF,3,3)
    grp = G
    Ps, Ns, As, Ws, Gs = [], [], [], [], []
    cur_T, cur_g = T, grp
    for _ in range(8):
        e = np.stack([np.linalg.norm(cur_T[:, 1] - cur_T[:, 0], axis=1),
                      np.linalg.norm(cur_T[:, 2] - cur_T[:, 1], axis=1),
                      np.linalg.norm(cur_T[:, 0] - cur_T[:, 2], axis=1)], 1).max(1)
        big = e > spacing
        if not big.any():
            break
        keep_T, keep_g = cur_T[~big], cur_g[~big]
        B, bg = cur_T[big], cur_g[big]
        m01 = 0.5 * (B[:, 0] + B[:, 1])
        m12 = 0.5 * (B[:, 1] + B[:, 2])
        m20 = 0.5 * (B[:, 2] + B[:, 0])
        sub = np.concatenate([np.stack([B[:, 0], m01, m20], 1),
                              np.stack([m01, B[:, 1], m12], 1),
                              np.stack([m20, m12, B[:, 2]], 1),
                              np.stack([m01, m12, m20], 1)], 0)
        subg = np.concatenate([bg] * 4)
        cur_T = np.concatenate([keep_T, sub], 0)
        cur_g = np.concatenate([keep_g, subg], 0)
    cr = np.cross(cur_T[:, 1] - cur_T[:, 0], cur_T[:, 2] - cur_T[:, 0])
    a2 = np.linalg.norm(cr, axis=1)
    ok = a2 > 2e-12
    cur_T, cur_g, cr, a2 = cur_T[ok], cur_g[ok], cr[ok], a2[ok]
    P = cur_T.mean(1)
    N = cr / a2[:, None]
    A = 0.5 * a2
    W = np.array([gamma.get(g, 1.0) for g in cur_g], float)
    return P, N, A, W, cur_g


def look(az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg))
    el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], -1)


def sigma(P, N, A, W, el, beta, chunk=20):
    """대역평균 σ(az). beta=0 이면 모노(û_i=û_s)."""
    acc = np.zeros(len(AZ))
    for f in np.linspace(FC - BW / 2, FC + BW / 2, NF):
        lam = C0 / f
        k = 2 * np.pi / lam
        Ui = look(AZ - beta / 2.0, el)
        Us = look(AZ + beta / 2.0, el)
        E = np.empty(len(AZ), complex)
        amp = A * W
        for s in range(0, len(AZ), chunk):
            a, b = Ui[s:s + chunk], Us[s:s + chunk]
            NI = N @ a.T
            NS = N @ b.T
            PH = P @ (a + b).T
            g = np.where((NI > 0) & (NS > 0), NI, 0.0)
            E[s:s + chunk] = (g * amp[:, None] * np.exp(1j * k * PH)).sum(0)
        acc += (4 * np.pi / lam ** 2) * np.abs(E) ** 2
    return acc / NF


def stats(s0, s1):
    d_mean = 10 * np.log10(s1.mean()) - 10 * np.log10(s0.mean())
    per = 10 * np.log10(np.maximum(s1, 1e-300)) - 10 * np.log10(np.maximum(s0, 1e-300))
    return dict(sigma_before_dbsm=round(float(10 * np.log10(s0.mean())), 4),
                sigma_after_dbsm=round(float(10 * np.log10(s1.mean())), 4),
                delta_mean_db=round(float(d_mean), 4),
                per_az_absmedian_db=round(float(np.median(np.abs(per))), 4),
                per_az_abs_p90_db=round(float(np.percentile(np.abs(per), 90)), 4),
                per_az_absmax_db=round(float(np.abs(per).max()), 4),
                frac_az_over_1db=round(float((np.abs(per) > 1.0).mean()), 4),
                frac_az_over_3db=round(float((np.abs(per) > 3.0).mean()), 4))


def build(key, fix):
    import drones as dr
    import geom
    dr._FIT_CACHE.clear()
    if fix:
        geom.set_mesh_fix(fix)
    else:
        os.environ.pop("MESH_FIX", None)
    m = dr.build_drone(dr.DRONES[key])
    os.environ.pop("MESH_FIX", None)
    return m


def fp(mesh):
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(mesh.v, float)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(mesh.f, np.int64)).tobytes())
    h.update("|".join(mesh.g).encode())
    return h.hexdigest()[:16]


def main():
    import drones as dr
    from materials import gamma_po
    import mesh_buried as mb
    gm = {g: (METAL_GAMMA_5G if m == "metal" else gamma_po(m, FC))
          for g, (m, _) in dr.DRONE_GROUP_MAT.items()}
    spacing = C0 / FC / DIV

    cells = json.loads(sys.argv[1]) if len(sys.argv) > 1 else []
    out = {}
    for fix, key in cells:
        t0 = time.time()
        #  «전» 판: i3 는 메쉬를 안 바꾸므로 같은 메쉬에 마스크만 다르다.
        base_fix = ""
        if fix == "i3":
            m0 = build(key, "")
            m1 = m0
            keep = mb.keep_face_mask(m0, kind="defect")
        elif fix == "i5+i4":                       # mini2 는 i5 가 선행이라 «i5» 대비로 잰다
            m0 = build(key, "i5")
            m1 = build(key, "i5,i4")
            keep = None
        else:
            m0 = build(key, "")
            m1 = build(key, fix)
            keep = None
        P0, N0, A0, W0, _ = sampler(m0, spacing, gm)
        P1, N1, A1, W1, _ = sampler(m1, spacing, gm, face_keep=keep)
        rec = dict(fp_before=fp(m0), fp_after=fp(m1),
                   n_faces=[int(len(m0.f)), int(len(m1.f))],
                   n_pts=[int(len(A0)), int(len(A1))],
                   area_mm2=[round(float(A0.sum()) * 1e6, 3), round(float(A1.sum()) * 1e6, 3)])
        if keep is not None:
            rec["i3_faces_removed"] = int((~keep).sum())
        for name, el, beta in GEOMS:
            s0 = sigma(P0, N0, A0, W0, el, beta)
            s1 = sigma(P1, N1, A1, W1, el, beta)
            rec[name] = stats(s0, s1)
        rec["elapsed_s"] = round(time.time() - t0, 1)
        out[f"{fix}|{key}"] = rec
        print(f"  {fix}|{key}  el0 Δ={rec['mono_el0']['delta_mean_db']:+.3f} dB "
              f"({rec['elapsed_s']}s)", flush=True)
        with open(f"/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/"
                  f"scratchpad/verify2/sigma_indep_{os.environ.get('TAG','x')}.json", "w") as fh:
            json.dump(dict(_conv=dict(fc=FC, bw=BW, nf=NF, spacing=f"lam/{DIV}",
                                      az="1:3:359", geoms=[list(g) for g in GEOMS],
                                      sampler="quad-subdiv centroid (독립)"),
                           cells=out), fh, ensure_ascii=False, indent=1)
    print("done")


if __name__ == "__main__":
    main()
