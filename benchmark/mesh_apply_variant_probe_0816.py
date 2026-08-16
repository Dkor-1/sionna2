"""2026-08-16 — **변종 A/B 자**. 소스 트리를 인자로 받아 같은 측정을 낸다.

왜 필요한가: 이 파일들을 **다른 라운드가 동시에 고치고 있다**. 저장소 소스를 직접 재면
내 변경과 남의 변경이 섞여 귀속이 안 된다. 그래서 소스 트리를 통째로 복사해 두고
«내 상수만 다른» 두 트리를 각각 별도 프로세스에서 재서 차이를 낸다.

사용법:
  python benchmark/mesh_apply_variant_probe_0816.py --src <srcdir> --what geom  --out <json>
  python benchmark/mesh_apply_variant_probe_0816.py --src <srcdir> --what sigma --key mavic4pro --out <json>
⛔ GPU 미사용(CUDA_VISIBLE_DEVICES=''). σ 는 우리 커널 PO(CPU).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

FLEET = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4",
         "m350rtk", "x500v2", "s1000plus", "typhoonh480"]
FC_HZ, BW_HZ, N_F, N_AZ, ELS = 3.5e9, 100e6, 9, 72, (0.0, 15.0)


def fingerprint(mesh) -> str:
    h = hashlib.sha256()
    h.update(np.asarray(mesh.v, np.float32).tobytes())
    h.update(np.asarray(mesh.f, np.int32).tobytes())
    return h.hexdigest()[:16]


def geom_report():
    from drones import DRONES, build_drone, _build_frame_raw, frame_fit_scale
    rep = {}
    for k in FLEET:
        spec = DRONES[k]
        try:
            raw = _build_frame_raw(spec)
        except Exception as e:                       # 다른 라운드가 편집 **중** 이면 여기 걸린다
            rep[k] = dict(build_error=f"{type(e).__name__}: {e}")
            continue
        V = np.asarray(raw.v, float) * 1000.0
        F = np.asarray(raw.f, int)
        G = np.asarray(raw.g, object)
        gz = {}
        for g in sorted(set(raw.g)):
            z = V[np.unique(F[G == g]), 2]
            gz[g] = [round(float(z.min()), 3), round(float(z.max()), 3)]
        fit = frame_fit_scale(spec)
        body = V[np.unique(F[G == "body"]), 2] if "body" in gz else None
        rep[k] = dict(
            sha=fingerprint(build_drone(spec)),
            sha_frame=fingerprint(raw),
            fit_scale=[round(float(v), 6) for v in fit],
            raw_bbox_mm=[round(float(v), 3) for v in (V.max(0) - V.min(0))],
            raw_z_mm=[round(float(V[:, 2].min()), 3), round(float(V[:, 2].max()), 3)],
            z_min_by_group_mm={g: v[0] for g, v in gz.items()},
            z_max_by_group_mm={g: v[1] for g, v in gz.items()},
            lowest_group=min(gz, key=lambda g: gz[g][0]),
            body_h_raw_mm=(round(float(body.max() - body.min()), 3) if body is not None else None),
            body_h_delivered_mm=(round(float((body.max() - body.min()) * fit[2]), 3)
                                 if body is not None else None),
        )
    return rep


def sigma_report(key):
    from rcs_po import drone_rcs_pattern_bw
    az = np.linspace(0.0, 360.0, N_AZ, endpoint=False)
    out = dict(convention=dict(engine="po (우리 커널, CPU, 가림 없음)", fc_hz=FC_HZ, bw_hz=BW_HZ,
                               n_f=N_F, n_az=N_AZ, materials=True))
    for el in ELS:
        t0 = time.time()
        s, npts = drone_rcs_pattern_bw(key, FC_HZ, BW_HZ, az, el_deg=el, n_f=N_F, engine="po")
        s = np.asarray(s, float)
        out[f"el{int(el)}"] = dict(
            mean_dbsm=round(float(10 * np.log10(s.mean())), 4),
            median_dbsm=round(float(10 * np.log10(np.median(s))), 4),
            worst_dbsm=round(float(10 * np.log10(s.min())), 4),
            worst_az_deg=round(float(az[int(np.argmin(s))]), 1),
            best_dbsm=round(float(10 * np.log10(s.max())), 4),
            n_points=int(npts), secs=round(time.time() - t0, 1),
            sigma_dbsm=[round(float(v), 4) for v in 10 * np.log10(s)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--what", choices=["geom", "sigma"], required=True)
    ap.add_argument("--key", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sys.path.insert(0, a.src)
    rep = geom_report() if a.what == "geom" else sigma_report(a.key)
    rep["_src"] = a.src
    with open(a.out, "w") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
