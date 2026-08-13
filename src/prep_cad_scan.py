# -*- coding: utf-8 -*-
"""
prep_cad_scan.py — 실물 3D 스캔(STL) → PO 용 경량 점구름(npz) 전처리 (report03 §2 · mesh08 A/B)
=======================================================================================
목적: 파라메트릭 메쉬 vs **실물 스캔** 의 RCS 패턴 비교(형상 리얼리즘 민감도 정량화).

입력  : DJI Phantom 4 실기체 0.4mm 스캔 (Thingiverse thing:1456295, "DJI PHANTOM 4 HI
        RES SCAN" by NeverDun/Eamon McQuaide, 라이선스 CC-BY — attribution 필수).
        원본 STL(154MB)은 저장소에 넣지 않는다. 재현:
          curl -LO https://archive.org/download/thingiverse-1456295/DJ_PHANTOM_4_HI_RES_SCAN_1456295.zip
출력  : assets/meshes/cad/phantom4_scan_points.npz — (P[m], N, dA[m²]) 면적가중 점구름
        (3mm 격자 클러스터 ≈ λ/10 @5.2GHz 이하 전 대역에서 PO 에 충분히 조밀)

처리  : ① binary STL 파싱(numpy) ② 삼각형 무게중심/법선/면적 ③ mm→m + 스케일 보정
        (모터 허브 대각 345.7mm → 스펙 350mm, ×1.0125) ④ PCA 로 z-up 정렬(최소분산축=z,
        랜딩기어가 아래로 가도록 부호 결정) ⑤ 3mm 복셀 클러스터: 면적 합·면적가중 법선
        (mesh_to_points 와 동일한 물리량) — 3.09M tris → 수만 점.
주의  : 스캔에는 **프로펠러·짐벌카메라가 없다**(A/B 시 파라메트릭도 해당 그룹 제외해 비교).
        비다양체/부유 링 아티팩트(~0.8%)는 면적이 미미해 클러스터 합산에서 무시 가능.
"""
from __future__ import annotations

import os
import sys

import numpy as np

STL = ("/tmp/claude-1015/-workspace/b16ec570-b204-4255-9c8a-da23fd2adf6d/"
       "scratchpad/cad/phantom4_scan/files/DJIPHANTOM4_.3MM.stl")
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "meshes", "cad"))
OUT = os.path.join(OUT_DIR, "phantom4_scan_points.npz")
SCALE = 1.0125 / 1000.0          # mm→m + 휠베이스 보정(345.7→350mm)
CELL = 0.003                     # 클러스터 격자 [m] (λ/10 @5.2GHz=5.8mm 보다 조밀)


def read_binary_stl(path):
    """binary STL → (v0, v1, v2) 각 (n,3) float64 [파일 단위 그대로]."""
    with open(path, "rb") as f:
        f.seek(80)
        n = np.frombuffer(f.read(4), dtype=np.uint32)[0]
        rec = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    tri = rec[:, 12:48].copy().view(np.float32).reshape(n, 3, 3).astype(np.float64)
    return tri[:, 0], tri[:, 1], tri[:, 2]


def main():
    if not os.path.exists(STL):
        sys.exit(f"스캔 STL 없음: {STL}\n(모듈 docstring 의 archive.org 미러에서 내려받으세요)")
    v0, v1, v2 = read_binary_stl(STL)
    print(f"STL 로드: {len(v0):,} tris")

    # 무게중심/법선/면적 (mm)
    nrm = np.cross(v1 - v0, v2 - v0)
    area2 = np.linalg.norm(nrm, axis=1)
    keep = area2 > 1e-12
    v0, v1, v2, nrm, area2 = v0[keep], v1[keep], v2[keep], nrm[keep], area2[keep]
    cen = (v0 + v1 + v2) / 3.0
    nhat = nrm / area2[:, None]
    area = 0.5 * area2                                    # [mm²]

    # 스케일: mm→m + 휠베이스 보정
    cen = cen * SCALE
    area = area * (SCALE ** 2)

    # PCA 정렬: 최소분산축 → z. (면적 가중 공분산)
    c0 = np.average(cen, axis=0, weights=area)
    X = cen - c0
    cov = (X * area[:, None]).T @ X / area.sum()
    w, V = np.linalg.eigh(cov)                            # 오름차순 → V[:,0]=최소분산축
    R = V[:, [1, 2, 0]]                                   # (x,y,z)=(중간, 최대, 최소) 분산축
    if np.linalg.det(R) < 0:
        R[:, 1] *= -1
    Xr = X @ R
    Nr = nhat @ R
    # z 부호: 랜딩기어(긴 다리)가 아래로 — 아래쪽 꼬리가 더 길도록
    zc = np.average(Xr[:, 2], weights=area)
    lo = np.percentile(Xr[:, 2], 2) - zc
    hi = np.percentile(Xr[:, 2], 98) - zc
    if abs(hi) > abs(lo):                                 # 위 꼬리가 더 길면 뒤집는다
        Xr[:, 1:] *= -1                                   # z 반전 + (오른손계 유지 위해 y 도)
        Nr[:, 1:] *= -1
    Xr -= np.average(Xr, axis=0, weights=area)            # 중심 재정렬

    # 3mm 복셀 클러스터: 면적 합, 면적가중 법선/위치
    key = np.floor(Xr / CELL).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    nc = inv.max() + 1
    A = np.bincount(inv, weights=area, minlength=nc)
    P = np.stack([np.bincount(inv, weights=Xr[:, i] * area, minlength=nc) / A for i in range(3)], 1)
    N = np.stack([np.bincount(inv, weights=Nr[:, i] * area, minlength=nc) for i in range(3)], 1)
    nlen = np.linalg.norm(N, axis=1)
    ok = nlen > 1e-12                                     # 상쇄된(양면 접힘) 셀 제거
    P, N, A, nlen = P[ok], N[ok], A[ok], nlen[ok]
    N = N / nlen[:, None]
    # 셀 내 법선 상쇄만큼 유효면적 축소(평평한 셀=유지, 접힌 셀=감소) — PO 물리와 정합
    A_eff = nlen

    os.makedirs(OUT_DIR, exist_ok=True)
    np.savez_compressed(OUT, P=P.astype(np.float32), N=N.astype(np.float32),
                        dA=A_eff.astype(np.float32))
    b0, b1 = P.min(0), P.max(0)
    print(f"점구름 저장: {OUT}")
    print(f"  점 {len(P):,}개  bbox(m) x[{b0[0]:+.3f},{b1[0]:+.3f}] "
          f"y[{b0[1]:+.3f},{b1[1]:+.3f}] z[{b0[2]:+.3f},{b1[2]:+.3f}]")
    print(f"  총 유효면적 {A_eff.sum():.4f} m² (원 면적 {A.sum():.4f} m²)")


if __name__ == "__main__":
    main()
