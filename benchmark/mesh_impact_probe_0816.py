# -*- coding: utf-8 -*-
"""
mesh_impact_probe_0816.py — **한 소스 트리 하나를 재는 자**(영향 측정 라운드)
==============================================================================

왜 «소스 트리를 인자로» 받나
  이 라운드가 도는 동안 **다른 라운드가 같은 파일을 계속 고친다**(2층 수리 라운드).
  저장소 소스를 직접 재면 내 대조가 남의 편집과 섞여 귀속이 깨진다. 그래서
  드라이버가 소스를 통째로 복사해 «수리를 하나씩 되돌린» 트리들을 만들고,
  이 자를 **트리마다 별도 프로세스**로 돌린다.

무엇을 재나 (한 트리에 대해)
  1. 지문 — 기체별 build_drone / _build_frame_raw / **프로펠러**(CCW·CW) / 그룹별
     → «안 건드린 기체는 비트동일» 과 «움직이는 성분(프롭)은 0» 을 해시로 증명한다.
  2. 기하 — fit_scale · 프레임/드론 바운딩박스 · 축간거리 · 유효대각 · 그룹별 z 범위 ·
     로터 중심 좌표(프롭이 앉는 자리).
  3. σ — 우리 커널 PO(CPU · 가림 없음 · 재질 가중 |Γ|):
     fc 3.5 GHz · 대역 100 MHz **5주파 비코히런트 평균** · 점간격 λ/7(중심주파수) ·
     방위 1.0° 격자(360점) · el 0° 와 15°.
       · 방위평균 = 10log10(mean_az σ)      · 최악방위 = 3° 각도평활 뒤 최저 σ
     (단일주파 코히런트 널은 수치 아티팩트 → 대역평균 + 각도평활, rcs_po 규약)
  4. 마이크로도플러 축 — **로터 위상 한 바퀴**를 돌려 σ(위상)을 낸다.
       · `md_prop_only`  = 프로펠러 점만(= 움직이는 성분 그 자체)
       · `md_single_rotor` = 로터 1개만, 그 로터 중심을 원점으로 옮겨서
         (강체 평행이동에 **불변**이어야 하는 양 — 진짜 «날 형상» 축)
       · `md_full`       = 프레임 + 프롭 전체(관측되는 신호)
     프롭 메쉬를 매 위상마다 다시 짓지 않고 점구름을 z축 회전시킨다(정확히 같은 변환).

⛔ GPU 미사용 · git 미사용 · 소스 편집 없음(이 자는 읽기만 한다).

사용:
  CUDA_VISIBLE_DEVICES="" python benchmark/mesh_impact_probe_0816.py \
      --src <srcdir> --out <json> [--sigma key1,key2] [--md key1,key2] [--az-step 1.0]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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
NF = 5
DIV = 7.0                 # 점 간격 = λ/DIV
ELS = (0.0, 15.0)
MD_AZ = (0.0, 45.0, 90.0, 180.0)
#  ⭐ el 0° 만 보면 **z 이동이 안 보인다** — 시선 û 의 z 성분이 0 이라 위상 2k(r·û) 에
#     z 가 아예 안 들어간다. B7 이 로터면을 14.65 mm 내렸는데도 el 0° 에서는 프롭 에코가
#     비트동일로 나온다(1차 측정에서 실제로 그랬다). 그래서 el 30° 를 같이 본다.
MD_ELS = (0.0, 30.0)
MD_NPH = 36               # 로터 한 바퀴 위상 표본


def sha(*arrs) -> str:
    h = hashlib.sha256()
    for a in arrs:
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()[:16]


def mesh_sha(m) -> str:
    return sha(np.asarray(m.v, np.float64), np.asarray(m.f, np.int32))


# --------------------------------------------------------------------------- #
#  1·2. 지문 · 기하
# --------------------------------------------------------------------------- #
def geom_of(key, dr):
    spec = dr.DRONES[key]
    dr._FIT_CACHE.clear()
    out = {}
    try:
        raw = dr._build_frame_raw(spec)
        drone = dr.build_drone(spec)
    except Exception as e:                       # 남의 라운드가 편집 **중** 이면 여기 걸린다
        return dict(build_error=f"{type(e).__name__}: {e}")

    V = np.asarray(drone.v, float) * 1000.0
    F = np.asarray(drone.f, int)
    G = np.asarray(drone.g, object)
    groups = {}
    gz = {}
    Vf = np.asarray(drone.v, np.float64)
    for g in sorted(set(drone.g)):
        sel = (G == g)
        vi = np.unique(F[sel])
        #  ⚠ 그룹 지문은 **좌표만**으로 낸다(면 인덱스 금지). 앞 그룹의 정점 수가 바뀌면
        #    뒤 그룹의 인덱스가 통째로 밀려서, 형상이 하나도 안 바뀐 그룹까지 «바뀜» 으로
        #    보인다 — 1차 측정에서 실제로 걸렸던 함정이다(mini5pro/matrice4e 의 유령 그룹).
        groups[g] = sha(Vf[F[sel]])          # (n_tri, 3, 3) 삼각형 좌표 = 인덱스 무관
        z = V[vi]
        gz[g] = dict(z_mm=[round(float(z[:, 2].min()), 4), round(float(z[:, 2].max()), 4)],
                     n_tri=int(sel.sum()))
    env = dr.frame_envelope_mm(spec)
    rl = dr.rotor_layout(spec)
    out.update(
        sha_drone=mesh_sha(drone),
        sha_frame_raw=mesh_sha(raw),
        sha_prop_ccw=mesh_sha(dr.build_propeller(spec)),
        sha_prop_cw=mesh_sha(dr.build_propeller(spec, mirror=True)),
        group_sha=groups,
        group_z=gz,
        fit_scale=[round(float(v), 9) for v in dr.frame_fit_scale(spec)],
        frame_raw_bbox_mm=[round(float(v), 4) for v in
                           (np.asarray(raw.v, float).max(0) - np.asarray(raw.v, float).min(0)) * 1000],
        drone_bbox_mm=[round(float(v), 4) for v in (V.max(0) - V.min(0))],
        drone_z_mm=[round(float(V[:, 2].min()), 4), round(float(V[:, 2].max()), 4)],
        lwh_mm=[round(float(v), 4) for v in env["lwh_mm"]],
        wheelbase_mm=round(float(env["wheelbase_opposite_mm"]), 4),
        diag_eff_mm=round(float(env["diagonal_effective_mm"]), 4),
        n_tri=int(len(drone.f)),
        rotor_centers_mm=[[round(float(c) * 1000, 4) for c in r["center"]] for r in rl],
        rotor_base_ang=[round(float(r["base_ang"]), 4) for r in rl],
        rotor_dir=[int(r["dir"]) for r in rl],
    )
    return out


# --------------------------------------------------------------------------- #
#  3. σ (PO)
# --------------------------------------------------------------------------- #
def sigma_of(key, dr, rp, az):
    spec = dr.DRONES[key]
    dr._FIT_CACHE.clear()
    m = dr.build_drone(spec)
    P, N, dA, w = rp.mesh_to_points(m, rp.C0 / FC / DIV, gamma=dr.drone_gamma_map(spec))
    freqs = (FC - BW / 2) + BW * np.arange(NF) / max(1, NF - 1)
    out = dict(n_pts=int(len(dA)))
    for el in ELS:
        acc = np.zeros(len(az))
        for f in freqs:
            #  방위를 60개씩 잘라 돈다 — (점수 × 방위수) 임시배열이 수백 MB 가 되면
            #  같은 기계를 쓰는 다른 라운드까지 스왑으로 끌고 들어간다. 값은 동일.
            for i in range(0, len(az), 60):
                acc[i:i + 60] += rp.rcs_from_points(P, N, dA, f, az[i:i + 60], el, w=w) / NF
        out[f"el{int(el)}"] = [float(v) for v in acc]
    return out


# --------------------------------------------------------------------------- #
#  4. 마이크로도플러 축 — 로터 위상 스윕
# --------------------------------------------------------------------------- #
def _rotz(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def md_of(key, dr, rp):
    """로터 위상 한 바퀴에 대한 σ(위상). 프롭 점구름을 z회전시켜 배치한다
    (pose_articulated 와 같은 변환: M = T(center) @ Rz(base_ang + dir·ph))."""
    spec = dr.DRONES[key]
    dr._FIT_CACHE.clear()
    gam = dr.drone_gamma_map(spec)
    sp = rp.C0 / FC / DIV

    frame = dr.build_frame(spec)
    Pf, Nf, dAf, wf = rp.mesh_to_points(frame, sp, gamma=gam)

    g_prop = float(gam.get("prop", 1.0))
    props = {}
    for tag, mir in (("ccw", False), ("cw", True)):
        pm = dr.build_propeller(spec, mirror=mir)
        Pp, Np_, dAp = rp.mesh_to_points(pm, sp)
        props[tag] = (Pp, Np_, dAp, np.full(len(dAp), g_prop))

    rl = dr.rotor_layout(spec)
    phases = np.arange(MD_NPH) * (360.0 / MD_NPH)
    az = np.array(MD_AZ)
    res = dict(n_rotor=len(rl), n_pts_frame=int(len(dAf)),
               n_pts_prop=int(len(props["ccw"][2])), phases_deg=[float(p) for p in phases],
               az_deg=list(MD_AZ), els=list(MD_ELS), gamma_prop=g_prop)
    shp = (len(phases), len(MD_ELS), len(az))
    full, only, single = np.zeros(shp), np.zeros(shp), np.zeros(shp)
    for ip, ph in enumerate(phases):
        Ps, Ns, dAs, ws = [Pf], [Nf], [dAf], [wf]
        Po, No, dAo, wo = [], [], [], []
        P1 = N1 = dA1 = w1 = None
        for ir, rot in enumerate(rl):
            Pp, Np_, dAp, wp = props["ccw" if rot["dir"] > 0 else "cw"]
            R = _rotz(rot["base_ang"] + rot["dir"] * ph)
            c = np.asarray(rot["center"], float)
            Pw = Pp @ R.T + c
            Nw = Np_ @ R.T
            Ps.append(Pw); Ns.append(Nw); dAs.append(dAp); ws.append(wp)
            Po.append(Pw); No.append(Nw); dAo.append(dAp); wo.append(wp)
            if ir == 0:                        # 로터 1개 · 중심을 원점으로(평행이동 불변 축)
                P1, N1, dA1, w1 = Pp @ R.T, Nw, dAp, wp
        PA, NA, dAA, wA = (np.vstack(Ps), np.vstack(Ns), np.concatenate(dAs), np.concatenate(ws))
        PO_, NO_, dAO, wO = (np.vstack(Po), np.vstack(No), np.concatenate(dAo), np.concatenate(wo))
        for ie, el in enumerate(MD_ELS):
            full[ip, ie] = rp.rcs_from_points(PA, NA, dAA, FC, az, el, w=wA)
            only[ip, ie] = rp.rcs_from_points(PO_, NO_, dAO, FC, az, el, w=wO)
            single[ip, ie] = rp.rcs_from_points(P1, N1, dA1, FC, az, el, w=w1)
    res["md_full"] = full.tolist()
    res["md_prop_only"] = only.tolist()
    res["md_single_rotor"] = single.tolist()
    return res


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sigma", default="")
    ap.add_argument("--md", default="")
    ap.add_argument("--az-step", type=float, default=1.0)
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    sys.path.insert(0, src)
    import drones as dr
    import rcs_po as rp
    assert os.path.dirname(os.path.abspath(dr.__file__)) == src, \
        f"엉뚱한 트리를 import 했다: {dr.__file__}"

    t0 = time.time()
    az = np.arange(0.0, 360.0, a.az_step)
    out = dict(_meta=dict(src=src, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          md5={f: hashlib.md5(open(os.path.join(src, f), "rb").read()).hexdigest()
                               for f in ("drone_cad.py", "drones.py", "cadkit.py", "geom.py")},
                          fc_hz=FC, bw_hz=BW, n_f=NF, spacing="lambda/%g" % DIV,
                          az_step_deg=a.az_step, els=list(ELS), md_nph=MD_NPH),
               geom={}, sigma={}, md={})
    for k in FLEET:
        out["geom"][k] = geom_of(k, dr)
        print(f"  geom {k} {time.time()-t0:.0f}s", flush=True)
    for k in [x for x in a.sigma.split(",") if x]:
        out["sigma"][k] = sigma_of(k, dr, rp, az)
        print(f"  sigma {k} {time.time()-t0:.0f}s", flush=True)
    for k in [x for x in a.md.split(",") if x]:
        out["md"][k] = md_of(k, dr, rp)
        print(f"  md {k} {time.time()-t0:.0f}s", flush=True)
    out["_meta"]["elapsed_s"] = round(time.time() - t0, 1)
    with open(a.out, "w") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print(f"[probe] {a.out} ({os.path.getsize(a.out)/1024:.0f} KB, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
