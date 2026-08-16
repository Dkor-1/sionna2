"""2026-08-16 — **값 적용 라운드**의 자[尺]: 형상(mm)과 σ(dB)를 같은 규약으로 잰다.

이 파일은 상수를 **바꾸지 않는다.** 바꾸기 전/후를 같은 방법으로 재기만 한다.
(무엇을 왜 바꿨는지는 outputs/mesh_apply_gimbal_then_height_0816.json 에 적는다.)

⛔ GPU 미사용 · ⛔ git 미사용. σ 는 **우리 커널 PO**(engine="po", CPU)로만 잰다.

사용법
  python benchmark/mesh_apply_gimbal_height_0816.py geom  --tag baseline
  python benchmark/mesh_apply_gimbal_height_0816.py sigma --key mavic4pro --tag baseline
결과는 outputs/_apply0816/<what>_<tag>[_<key>].json 에 쌓인다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

OUT = pathlib.Path(__file__).resolve().parents[1] / "outputs" / "_apply0816"
OUT.mkdir(parents=True, exist_ok=True)

FLEET = ["mini5pro", "mavic4pro", "matrice4e", "mini2", "phantom3", "phantom4",
         "m350rtk", "x500v2", "s1000plus", "typhoonh480"]

#  σ 규약 — 한 번 정하고 라운드 내내 고정한다.
FC_HZ = 3.5e9          # 5G n78 중심
BW_HZ = 100e6          # 5G 100 MHz — 코히런트 PO 의 가짜 널을 메운다(rcs_po.drone_rcs_pattern_bw 주석)
N_F = 9                # 대역 내 주파수 점
N_AZ = 72              # 방위 5° 간격
ELS = (0.0, 15.0)      # 저앙각(지상 레이다) · 중앙각


# --------------------------------------------------------------------------- #
#  형상 자
# --------------------------------------------------------------------------- #
def fingerprint(mesh) -> str:
    """build_drone 지문 — float32 정점 + int32 삼각형의 sha256 (2026-08-04 라운드와 같은 규약)."""
    v = np.asarray(mesh.v, np.float32)
    f = np.asarray(mesh.f, np.int32)
    h = hashlib.sha256()
    h.update(v.tobytes())
    h.update(f.tobytes())
    return h.hexdigest()[:16]


def _group_z(mesh):
    """그룹별 z 범위[mm] — 면이 쓰는 정점만 본다."""
    V = np.asarray(mesh.v, float) * 1000.0
    F = np.asarray(mesh.f, int)
    G = np.asarray(mesh.g, object)
    out = {}
    for g in sorted(set(mesh.g)):
        idx = np.unique(F[G == g])
        z = V[idx, 2]
        out[g] = [round(float(z.min()), 3), round(float(z.max()), 3)]
    return out


def _shell_h_mm(spec):
    """셸(body 그룹)만 따로 지어 잰 높이[mm] — 보정 전(raw)."""
    from drones import _build_frame_raw
    m = _build_frame_raw(spec)
    V = np.asarray(m.v, float) * 1000.0
    F = np.asarray(m.f, int)
    G = np.asarray(m.g, object)
    idx = np.unique(F[G == "body"])
    z = V[idx, 2]
    return round(float(z.max() - z.min()), 3)


def geom_report(keys=None) -> dict:
    from drones import DRONES, build_drone, _build_frame_raw, frame_fit_scale
    keys = keys or FLEET
    rep = {}
    for k in keys:
        spec = DRONES[k]
        raw = _build_frame_raw(spec)
        V = np.asarray(raw.v, float) * 1000.0
        gz = _group_z(raw)
        fit = frame_fit_scale(spec)
        low = min(gz, key=lambda g: gz[g][0])
        rep[k] = dict(
            sha=fingerprint(build_drone(spec)),
            fit_scale=[round(float(v), 6) for v in fit],
            raw_bbox_mm=[round(float(v), 3) for v in (V.max(0) - V.min(0))],
            raw_z_mm=[round(float(V[:, 2].min()), 3), round(float(V[:, 2].max()), 3)],
            z_min_by_group_mm={g: v[0] for g, v in gz.items()},
            z_max_by_group_mm={g: v[1] for g, v in gz.items()},
            lowest_group=low,
            shell_h_raw_mm=_shell_h_mm(spec) if "body" in gz else None,
            shell_h_delivered_mm=(round(_shell_h_mm(spec) * float(fit[2]), 3)
                                  if "body" in gz else None),
        )
    return rep


# --------------------------------------------------------------------------- #
#  σ 자 — 우리 커널 PO(가림 없음), CPU
# --------------------------------------------------------------------------- #
def sigma_report(key, els=ELS) -> dict:
    from rcs_po import drone_rcs_pattern_bw
    az = np.linspace(0.0, 360.0, N_AZ, endpoint=False)
    out = dict(convention=dict(engine="po(우리 커널, CPU, 가림 없음)", fc_hz=FC_HZ,
                               bw_hz=BW_HZ, n_f=N_F, n_az=N_AZ, materials=True))
    for el in els:
        t0 = time.time()
        s, npts = drone_rcs_pattern_bw(key, FC_HZ, BW_HZ, az, el_deg=el, n_f=N_F, engine="po")
        s = np.asarray(s, float)
        out[f"el{int(el)}"] = dict(
            mean_dbsm=round(float(10 * np.log10(s.mean())), 4),      # 방위평균(선형 평균 후 dB)
            median_dbsm=round(float(10 * np.log10(np.median(s))), 4),
            worst_dbsm=round(float(10 * np.log10(s.min())), 4),      # 최악방위(가장 어두운 방위)
            worst_az_deg=round(float(az[int(np.argmin(s))]), 1),
            best_dbsm=round(float(10 * np.log10(s.max())), 4),
            n_points=int(npts), secs=round(time.time() - t0, 1),
            sigma_dbsm=[round(float(v), 4) for v in 10 * np.log10(s)],
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["geom", "sigma"])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    if a.what == "geom":
        rep = geom_report()
        p = OUT / f"geom_{a.tag}.json"
    else:
        rep = sigma_report(a.key)
        p = OUT / f"sigma_{a.tag}_{a.key}.json"
    p.write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
