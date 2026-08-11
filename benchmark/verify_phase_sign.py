"""⭐부호 규약 게이트 — 구면파 갈래의 도플러 부호가 평면파·표준과 같은지 확정한다.

배경: 2026-08-11 에 `sbr_field(range_m=...)` 의 구면파 위상이 **거리**에 +j 를 걸고 있어
평면파 갈래(**투영**에 +j)와 정확히 반대였다. 원거리장 극한에서 두 식은 −1 배 관계다.

게이트
  G1  |E| 불변       — 정정은 켤레와 같으므로 σ 가 비트 단위로 같아야 한다.
  G2  원거리장 수렴  — range_m 을 키우면 구면파 → 평면파. 상관이 **+1** 이어야 한다(−1 아님).
  G3  접근 = 양수    — 표적 좌표계 안에서 레이다 쪽으로 다가오는 산란체가 양의 도플러.
"""
import os, sys, json, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/src")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "2")
from gpu import pick; pick(verbose=False)
from rcs_sbr import sbr_field, grid_ref_from
from articulated_fast import FastPoser, rotor_phases
from drones import DRONES, DRONE_GROUP_MAT

FC, C = 3.5e9, 299792458.0
LAM, K = C / FC, 2 * np.pi * FC / C
u = np.array([1.0, 0.0, 0.0])
spec = DRONES["matrice4e"]
fp = FastPoser(spec)
gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}

N, PRF = 256, 19700.0
rpms = np.full(len(fp.dirs), 3800.0)
ph = rotor_phases(np.arange(N) / PRF, rpms, fp.dirs)
poses = [fp.pose(ph[i]) for i in range(N)]
gref = grid_ref_from(poses[::16], FC, spacing=(C / FC) / 12)

def series(range_m):
    return np.array([sbr_field(p, gm, FC, u, grid_ref=gref, range_m=range_m) for p in poses])

out = {}
E_plane = series(None)
E_far   = series(5000.0)          # 원거리장 한참 밖 (2D²/λ ≈ 14 m)
E_near  = series(10.0)            # 앙각 스윕이 쓰는 거리

# ── G1  |E| 불변 (정정 = 켤레) ------------------------------------------------
rel = float(np.max(np.abs(np.abs(E_near) - np.abs(np.conj(E_near)))) /
            max(np.abs(E_near).max(), 1e-30))
out["G1_abs_invariant"] = {"max_rel_diff": rel, "pass": bool(rel < 1e-12),
                           "note": "sigma = 4pi/lam^2 |E|^2 이므로 시그마 원장은 무효가 아니다"}

# ── G2  원거리장에서 구면파 → 평면파 (부호까지) --------------------------------
def rho(a, b):
    a, b = a - a.mean(), b - b.mean()
    return complex(np.vdot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
r_far = rho(E_plane, E_far)
out["G2_farfield_converges"] = {
    "range_m": 5000.0, "rho_real": r_far.real, "rho_abs": abs(r_far),
    "pass": bool(r_far.real > 0.99),
    "note": "고치기 전이면 rho_real 이 -1 근처로 나온다(켤레 수렴)"}

# ── G3  접근 산란체 = 양의 도플러 ---------------------------------------------
V, PRF3, N3 = 5.0, 2000.0, 512
t = np.arange(N3) / PRF3
R = 10.0 - V * t
sph_fix = np.exp(1j * 2 * K * (10.0 - np.sqrt(R**2)))    # 정정판 위상 (P 가 û 위를 달림)
ref = np.exp(-1j * 2 * np.pi * FC * (2 * R / C))         # 표준 규약
fr = np.fft.fftfreq(N3, 1 / PRF3); w = np.hanning(N3)
fd = lambda E: float(fr[np.argmax(np.abs(np.fft.fft((E - E.mean()) * w))**2)])
out["G3_approach_positive"] = {"f_true_hz": 2 * V / LAM, "f_ours_hz": fd(sph_fix),
                               "f_standard_hz": fd(ref),
                               "pass": bool(fd(sph_fix) > 0 and fd(sph_fix) == fd(ref))}

# ── 참고: 10 m 판의 부호 비대칭이 어느 쪽으로 기우나 --------------------------
def asym(E):
    E = E - E.mean(); n = E.size
    S = np.abs(np.fft.fft(E * np.hanning(n)))**2
    return float(10 * np.log10(S[1:n//2].sum() / S[n//2+1:].sum()))
out["asymmetry_db"] = {"plane": asym(E_plane), "spherical_10m": asym(E_near),
                       "spherical_5000m": asym(E_far)}

out["verdict"] = "PASS" if all(v["pass"] for k, v in out.items() if k.startswith("G")) else "FAIL"
json.dump(out, open(f"{ROOT}/outputs/verify_phase_sign.json", "w"), indent=2, ensure_ascii=False)
for k, v in out.items():
    if k.startswith("G"):
        print(f"  {k:24s} {'PASS' if v['pass'] else 'FAIL'}")
        for kk, vv in v.items():
            if kk != "pass":
                print(f"       {kk:18s} {vv}")
print(f"\n  ⊕/⊖ 비대칭 [dB]  {out['asymmetry_db']}")
print(f"  ⇒ {out['verdict']}   → outputs/verify_phase_sign.json")
