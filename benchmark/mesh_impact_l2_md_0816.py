# -*- coding: utf-8 -*-
"""
mesh_impact_l2_md_0816.py — **2층 수리가 «움직이는 성분» 을 건드리나** (마이크로도플러 축)
==============================================================================

이 라운드의 규약: 프로펠러는 아무도 안 건드렸으니 **움직이는 성분의 변화는 0 이어야 한다.**
0 이 아니면 수리가 의도 밖의 것을 건드린 것이니 그 자리에서 멈추고 보고한다.

어떻게 «움직이는 성분» 만 떼어내나 — 세 가지를 따로 잰다
  1. `sigma_prop`  프롭 점만의 σ(위상). 프레임이 사라진 값이라 프레임 수리와 **무관해야** 한다.
  2. `sigma_full`  프레임+프롭 전체(관측되는 신호). 프레임이 바뀌면 이 값은 **당연히** 바뀐다 —
     정지성분(DC)이 움직였기 때문이지 날이 바뀌어서가 아니다.
  3. ⭐`sigma_ac`   전체 필드에서 **위상평균을 뺀 뒤**의 세기:
         E_ac(φ) = E_full(φ) − ⟨E_full⟩_φ = E_prop(φ) − ⟨E_prop⟩_φ
     프레임은 위상에 안 변하므로 평균을 뺄 때 **정확히 소거된다**. 즉 이 양은 대수적으로
     프레임과 무관하다 — «프레임 수리가 움직이는 성분을 건드렸나» 의 가장 날카로운 잣대다.
     (메모리의 ⚠AC/DC 잣대 아티팩트: 정지성분을 **빼기 전** 레벨 비교는 결론을 뒤집는다.
      그래서 여기서는 레벨(σ_full)과 AC 를 **따로** 적고 비율은 안 쓴다.)

메쉬는 위상마다 `pose_articulated` 로 다시 짓는다(프롭을 실제로 돌린다). i3(매몰면 마스크)는
**위상마다 다시 계산**한다 — 그래야 «마스크 자체가 위상에 따라 움직이나» 까지 보인다.

⛔ GPU 미사용 · git 미사용 · 소스 편집 없음.

사용:
  CUDA_VISIBLE_DEVICES="" MESH_FIX=i3 python benchmark/mesh_impact_l2_md_0816.py \
      --src <스냅샷 src> --out <json> [--keys mavic4pro,mini2]
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

KEYS = ["mavic4pro", "mini5pro", "mini2", "matrice4e", "m350rtk"]
FC = 3.5e9
DIV = 7.0
N_PH = 12                      # 로터 한 바퀴 위상 표본 (0,30,…,330°)
AZ = (0.0, 45.0, 90.0, 180.0)
ELS = (0.0, -30.0)
#  ⭐ el 0° 만 보면 z 이동이 안 보인다 — 시선 û 의 z 성분이 0 이라 위상 2k(r·û) 에 z 가
#     아예 안 들어간다. 그래서 el −30° 를 같이 본다(2층 σ 규약의 두 번째 배치와 같은 각).
METAL_GAMMA_5G = 0.9998026802895116


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
    from geom import mesh_fix_enabled
    assert os.path.dirname(os.path.abspath(dr.__file__)) == src

    gm = {g: (METAL_GAMMA_5G if m == "metal" else gamma_po(m, FC))
          for g, (m, _) in dr.DRONE_GROUP_MAT.items()}
    lam = rp.C0 / FC
    keys = [k for k in (a.keys.split(",") if a.keys else KEYS) if k]
    use_i3 = mesh_fix_enabled("i3")
    phases = np.arange(N_PH) * (360.0 / N_PH)

    t0 = time.time()
    out = dict(_meta=dict(src=src, mesh_fix=os.environ.get("MESH_FIX", ""),
                          ts_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          fc_hz=FC, spacing=f"lambda/{DIV:g}", n_phase=N_PH,
                          az_deg=list(AZ), el_deg=list(ELS), i3_on=bool(use_i3)),
               drones={})
    for k in keys:
        spec = dr.DRONES[k]
        dr._FIT_CACHE.clear()
        nrot = spec.num_rotors
        Ef = np.zeros((N_PH, len(ELS), len(AZ)), complex)     # 전체
        Ep = np.zeros_like(Ef)                                # 프롭만
        info = dict(n_rotor=int(nrot), phases_deg=[float(p) for p in phases],
                    n_pts=[], n_pts_prop=[], i3_removed=[], i3_removed_prop=[],
                    fp_prop_ccw=hashlib.sha256(
                        np.ascontiguousarray(np.asarray(dr.build_propeller(spec).v, float)).tobytes()
                    ).hexdigest()[:16])
        for ip, ph in enumerate(phases):
            mesh = dr.pose_articulated(spec, rotor_phase_deg=[float(ph)] * nrot)
            G = np.asarray(mesh.g)
            fmask = None
            if use_i3:
                fmask = mb.keep_face_mask(mesh, kind="defect")
                rem = ~np.asarray(fmask, bool)
                info["i3_removed"].append(int(rem.sum()))
                info["i3_removed_prop"].append(int((rem & (G == "prop")).sum()))
            P, N, dA, w, fidx = rp.mesh_to_points(mesh, lam / DIV, gamma=gm,
                                                  face_mask=fmask, return_face_idx=True)
            isp = (G[fidx] == "prop")
            info["n_pts"].append(int(len(dA)))
            info["n_pts_prop"].append(int(isp.sum()))
            for ie, el in enumerate(ELS):
                for ia, az in enumerate(AZ):
                    u = rp._look_dirs(az, el)[0]
                    Ef[ip, ie, ia] = rp.po_field_dir(P, N, dA, FC, u, w=w)
                    Ep[ip, ie, ia] = rp.po_field_dir(P[isp], N[isp], dA[isp], FC, u, w=w[isp])
        pre = 4 * np.pi / lam ** 2
        eac_f = Ef - Ef.mean(axis=0, keepdims=True)
        eac_p = Ep - Ep.mean(axis=0, keepdims=True)
        info.update(
            sigma_full=(pre * np.abs(Ef) ** 2).tolist(),
            sigma_prop=(pre * np.abs(Ep) ** 2).tolist(),
            sigma_ac_full=(pre * (np.abs(eac_f) ** 2).mean(axis=0)).tolist(),
            sigma_ac_prop=(pre * (np.abs(eac_p) ** 2).mean(axis=0)).tolist(),
            #  ⭐필드 자체의 지문 — dB 로 반올림하기 전에 «한 비트라도 달랐나» 를 본다
            fp_E_full=hashlib.sha256(np.ascontiguousarray(Ef).tobytes()).hexdigest()[:16],
            fp_E_prop=hashlib.sha256(np.ascontiguousarray(Ep).tobytes()).hexdigest()[:16],
            fp_E_ac=hashlib.sha256(np.ascontiguousarray(eac_f).tobytes()).hexdigest()[:16],
        )
        out["drones"][k] = info
        print(f"  [{os.environ.get('MESH_FIX','off')}] md {k} {time.time()-t0:.0f}s", flush=True)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    with open(a.out, "w") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"[md {os.environ.get('MESH_FIX','off')}] {a.out} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
