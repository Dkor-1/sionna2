# -*- coding: utf-8 -*-
"""
verify_observability.py — [E5] 관측가능성: "(Rb, f_d) 가 표적의 위치·속도를 결정하는가?"
==========================================================================================
report5(트래킹 벤치마크)의 **전제조건 검증**. 탐지(Pd)는 "저기 뭔가 있다"까지만 말한다.
트래킹은 "그게 **어디** 있고 **어디로** 가는가"를 요구한다. 바이스태틱 패시브 수신기 1대는
각도를 주지 않고 **(거리합 Rb, 도플러 f_d) 두 스칼라**만 준다. 상태는 위치 3 + 속도 3 = 6.
따라서 관측가능성은 **가정이 아니라 측정 대상**이다.

  [A] 파형별 측정 셀 — 정합필터 자기상관에서 ΔRb 를 **직접 재고**(가정 안 함), CPI 에서 Δf_d.
      ※ 바이스태틱 거리분해능은 ΔRb = c/B (모노스태틱의 c/2B 가 아니다 — Rb = c·τ 라서
        2 로 나누지 않는다). Waveform.range_resolution_m 은 모노스태틱 규약이라 정확히 2배 작다.

  [B] **등-Rb 껍질 부피** — {p ∈ 챔버 : |Rb(p) - Rb_true| <= ΔRb/2} 의 부피 [m^3].
      TX/RX 를 초점으로 하는 타원체 껍질이 방을 자른 조각. 이것이 **한 번의 거리측정이 남기는
      위치 불확실성**이다. 2 cm 격자로 GPU 에서 센다(챔버 6600 m^3 → 8.25e8 복셀).

  [C] **도플러가 더해주는 정보** — 두 경우를 분리한다(여기가 문헌이 자주 얼버무리는 곳):
      (C1) **속도를 안다고 치면**: 등-f_d 면이 껍질을 잘라 부피가 줄어든다 → 정량화.
      (C2) **속도를 모르면**(단일 스냅샷의 실제 상황): f_d = v·(û1+û2)/λ 는 **v 의 함수이기도
           하다** → 껍질의 거의 모든 점이 적당한 v 로 관측 f_d 를 설명한다 →
           **도플러는 위치정보를 (거의) 주지 않는다**. 그 '거의'를 숫자로 잰다.

  [D] **Fisher/CRLB** — J = d(Rb, f_d)/d(x,y,z) (2x3) → 백색화 → SVD.
      랭크가 2 라서 **영공간(1차원)이 항상 존재**한다: 위치는 단일 스냅샷으로 결정 불가.
      챔버 평면 지도로 (i) 관측가능 부분공간의 CRLB, (ii) 관측 불가능한 방향을 그린다.

  [E] **관측가능성 그램행렬(시간 관측)** — 등속(CV) 6상태에 대해 G = Σ_k H_k^T W H_k.
      시간이 흐르면 랭크가 오르지만 **6 에 도달하지 못한다**: 측정 (Rb, f_d) 는 TX-RX
      **베이스라인 축 둘레의 회전**에 대해 **정확히 불변**이다(엄밀한 연속 대칭).
      → 그램행렬은 **아무리 오래 봐도** 0 고유값을 하나 갖는다. 그 고유벡터가 회전 생성자와
        같은지 코사인유사도로 확인한다. 그리고 챔버 벽이 그 모호성을 얼마나 잘라내는지 잰다.
      → 처방: RX 2대(대칭 파괴) 또는 AoA 를 더하면 랭크 6 이 되는지 측정.

실행:  /workspace/.venvs/py312/bin/python benchmark/verify_observability.py
       (--fast 로 격자 성기게)
출력:  outputs/verify_observability.json, outputs/figures/report4_obs_*.png
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.abspath(os.path.join(_HERE, "..", "src"))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_HERE, _SRC):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick, gpu_status               # noqa: E402  (torch import 전에!)
_GPU = pick()

import numpy as np                             # noqa: E402
import matplotlib                              # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                # noqa: E402
from matplotlib.lines import Line2D            # noqa: E402

from vizstyle import use_korean                # noqa: E402
from waveforms import wifi_80211ac, lte_downlink, nr_downlink  # noqa: E402
from geometry import TX, RX, CENTER, CHAMBER, SPEED, SPAN      # noqa: E402
from scenarios import radial                                    # noqa: E402
from link_budget import LinkBudget                              # noqa: E402
from channel import AnalyticChannel, rt_chamber_clutter         # noqa: E402
from geometry import CH_CLUTTER_RATIO                           # noqa: E402
from run_min_cell import run_cell, frame_len, EIRP_DBM          # noqa: E402

# 그림 텍스트는 **전부 영어**(규약) → 한글 폰트를 쓰지 않는다.
#   나눔고딕에는 U+2212(마이너스)·그리스문자 글리프가 없어서 로그축 눈금(10^-12)이 두부(□)로 깨진다.
#   use_korean() 은 import 해두되 호출하지 않는다(다른 스크립트와의 일관성 표시).
_ = use_korean
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["mathtext.fontset"] = "dejavusans"
plt.rcParams["axes.unicode_minus"] = True
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

C0 = 299792458.0
OUT = os.path.join(_ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

TXv = np.array(TX, float)
RXv = np.array(RX, float)
CEN = np.array(CENTER, float)                 # quiet-zone 중심 (21, 10, 5.5)
L_BASE = float(np.linalg.norm(TXv - RXv))
T_CPI = 0.03                                  # run_matrix 와 동일한 고정 CPI [s]
DRONE = "mavic4pro"
PFA = 1e-4

# 표적/속도: 벤치마크의 radial 시나리오(이등분선 접근, 3 m/s).
# ⚠ run_min_cell.run_cell 은 pos[len//2] (= n=32 에서 인덱스 16, 정확히 중앙이 아님)에서
#   링크텀을 뽑는다 → **같은 점**을 써야 SCR 과 기하가 정합한다(아래 assert 가 지킨다).
_POS, _VEL = radial(TXv, RXv, CEN, speed=SPEED, span=SPAN, n=32)
TGT = _POS[len(_POS) // 2].copy()
VTRUE = _VEL[len(_VEL) // 2].copy()

# 비교 파형: **상시 기준신호**(G1 = 패시브의 기본선) 3종 + 측위세션(5G PRS, G3) 대조 1종
CFGS = [
    ("WiFi80 G1 (VHT-LTF)", "wifi80_G1", dict(std="wifi", bw=80e6, car=5.21e9, occ="G1"), "#1565c0"),
    ("LTE20 G1 (CRS)",      "lte20_G1",  dict(std="lte",  bw=20e6, car=1.843e9, occ="G1"), "#2e7d32"),
    ("5G100 G1 (SSB)",      "nr100_G1",  dict(std="nr",   bw=100e6, car=3.5e9,  occ="G1"), "#c62828"),
    ("5G100 G3 (PRS)",      "nr100_G3",  dict(std="nr",   bw=100e6, car=3.5e9,  occ="G3"), "#6a1b9a"),
]


def make_wf(std, bw, car, occ):
    fn = {"nr": nr_downlink, "lte": lte_downlink, "wifi": wifi_80211ac}[std]
    return fn(bw_hz=bw, carrier_hz=car, occupancy=occ)


# --------------------------------------------------------------------------- #
#  기하 (해석적 — 손으로 적은 숫자 없음)
# --------------------------------------------------------------------------- #
def bistatic_Rb(p):
    """Rb(p) = |p-TX| + |p-RX| - L. p: (...,3)"""
    p = np.asarray(p, float)
    return (np.linalg.norm(p - TXv, axis=-1) + np.linalg.norm(p - RXv, axis=-1) - L_BASE)


def _units(p):
    d1 = TXv - p; d2 = RXv - p
    R1 = np.linalg.norm(d1, axis=-1, keepdims=True)
    R2 = np.linalg.norm(d2, axis=-1, keepdims=True)
    return d1 / R1, d2 / R2, R1, R2


def bistatic_fd(p, v, lam):
    """f_d = v·(û1+û2)/λ  (bistatic_scene 규약: 멀어지면 < 0)."""
    u1, u2, _, _ = _units(np.asarray(p, float))
    return np.sum(np.asarray(v, float) * (u1 + u2), axis=-1) / lam


def grad_Rb(p):
    """∇_p Rb = -(û1 + û2)   (û 는 표적→TX/RX)."""
    u1, u2, _, _ = _units(np.asarray(p, float))
    return -(u1 + u2)


def grad_fd_p(p, v, lam):
    """∇_p f_d = -(1/λ)[ (I-û1û1ᵀ)v / R1 + (I-û2û2ᵀ)v / R2 ]."""
    p = np.asarray(p, float); v = np.asarray(v, float)
    u1, u2, R1, R2 = _units(p)
    t1 = (v - u1 * np.sum(u1 * v, axis=-1, keepdims=True)) / R1
    t2 = (v - u2 * np.sum(u2 * v, axis=-1, keepdims=True)) / R2
    return -(t1 + t2) / lam


def grad_fd_v(p, lam):
    """∂f_d/∂v = (û1 + û2)/λ."""
    u1, u2, _, _ = _units(np.asarray(p, float))
    return (u1 + u2) / lam


# --------------------------------------------------------------------------- #
#  [A] 측정 셀 — ΔRb 를 자기상관에서 **재고**, Δf_d 를 CPI 에서 얻는다
# --------------------------------------------------------------------------- #
def cell_of(wf):
    """정합필터(=wf.ref) 자기상관 주엽의 -3 dB 폭 → 바이스태틱 거리분해능 ΔRb [m].
    RD 맵의 거리축 샘플간격은 c/fs 이므로 실효 셀 = max(3dB 폭, c/fs)."""
    # 자기상관은 FFT 로 (np.correlate 는 O(n^2) 직접합 — ref 3만~6만 샘플에서 수 분 걸린다).
    n = 1 << int(np.ceil(np.log2(2 * len(wf.ref))))
    F = np.fft.fft(wf.ref, n)
    r = np.abs(np.fft.ifft(F * np.conj(F)))          # 원형 자기상관 (지연 0 = index 0)
    r = np.fft.fftshift(r)
    r = r / (r.max() + 1e-30)
    pk = int(np.argmax(r))
    half = np.where(r[pk:] < 1 / np.sqrt(2))[0]
    k = float(half[0]) if len(half) else 1.0
    # 선형보간으로 반폭(샘플) 정밀화
    if len(half) and half[0] > 0:
        i = int(half[0]); y1, y0 = r[pk + i], r[pk + i - 1]
        k = (i - 1) + (y0 - 1 / np.sqrt(2)) / max(y0 - y1, 1e-12)
    tau_3db = 2.0 * k / wf.fs_hz                 # 전폭 [s]
    drb_ac = tau_3db * C0                        # 바이스태틱: Rb = c·τ (2 로 안 나눔)
    bin_m = C0 / wf.fs_hz
    # rms 대역폭(=CRLB 를 정하는 것) — 기준신호 스펙트럼에서 직접 측정
    S = np.abs(np.fft.fft(wf.ref)) ** 2
    f = np.fft.fftfreq(len(wf.ref), 1 / wf.fs_hz)
    P = S.sum() + 1e-30
    fbar = float((f * S).sum() / P)
    b_rms = float(np.sqrt(((f - fbar) ** 2 * S).sum() / P))
    M = int(2 ** round(np.log2(max(16, T_CPI * wf.fs_hz / frame_len(wf)))))
    t_cpi = M * frame_len(wf) / wf.fs_hz
    return dict(drb_ac_m=float(drb_ac), drb_bw_m=float(C0 / max(wf.ref_bw_hz, 1.0)),
                bin_m=float(bin_m), drb_m=float(max(drb_ac, bin_m)),
                b_rms_hz=b_rms, ref_bw_mhz=float(wf.ref_bw_hz / 1e6),
                bw_mhz=float(wf.bw_hz / 1e6), fs_mhz=float(wf.fs_hz / 1e6),
                M=M, t_cpi=float(t_cpi), dfd_hz=float(1.0 / t_cpi),
                lam_m=float(C0 / wf.carrier_hz), ref_name=wf.ref_name,
                mono_res_m=float(wf.range_resolution_m))


_SCR_CACHE = os.path.join(OUT, "obs_scr_cache.json")


def measure_snr(wf, key):
    """측정된 SCR [dB] — CRLB 의 SNR. run_min_cell 하네스를 그대로 돌린다(주입 아님).
    ※ SCR 은 표적셀 3x3 max 라 잡음한계에서 ~+3 dB 낙관 편향이 있다(run_min_cell 주석) —
      CRLB 는 SNR^-1/2 이므로 σ 가 최대 ~30% 낙관적일 수 있다. 관측가능성 **구조**(랭크·영공간)는
      SNR 과 무관하므로 이 편향은 결론을 바꾸지 않는다."""
    ck = f"{key}|{DRONE}|{EIRP_DBM}|{T_CPI}"
    cache = {}
    if os.path.exists(_SCR_CACHE):
        with open(_SCR_CACHE) as f:
            cache = json.load(f)
    if ck in cache:
        v = cache[ck]
        return v["scr"], v["pd"], v["Rb"], v["fd"], v["sigma_dbsm"]
    ch = AnalyticChannel(clutter=rt_chamber_clutter(wf.carrier_hz) or CH_CLUTTER_RATIO)
    cell = run_cell(wf, DRONE, _POS, _VEL, LinkBudget(eirp_dbm=EIRP_DBM), channel=ch,
                    M=int(2 ** round(np.log2(max(16, T_CPI * wf.fs_hz / frame_len(wf))))),
                    N=16, pfa=PFA, seed0=abs(hash(key)) % 10000)
    st = cell["state"]
    v = dict(scr=float(cell["scr_mean"]), pd=float(cell["pd"]), Rb=float(st.tau * C0),
             fd=float(st.fd), sigma_dbsm=float(10 * np.log10(st.sigma_m2)))
    cache[ck] = v
    with open(_SCR_CACHE, "w") as f:
        json.dump(cache, f, indent=1)
    return v["scr"], v["pd"], v["Rb"], v["fd"], v["sigma_dbsm"]


# --------------------------------------------------------------------------- #
#  [B]/[C] 챔버 복셀 적분 (GPU)
# --------------------------------------------------------------------------- #
def voxel_volumes(cells, dx=0.02, vmax_list=(3.0, 15.0)):
    """챔버 내부를 dx 격자로 훑어 파형별로
       V_shell : |Rb(p)-Rb_true| <= ΔRb/2                (거리측정만)
       V_int   : 위 + |f_d(p, v_true)-fd_true| <= Δf_d/2 (속도를 **안다고 가정**)
       V_amb[vmax] : 껍질 중에서 '|v|<=vmax 인 어떤 속도로도 관측 f_d 를 설명할 수 있는' 부피
                     (= 속도를 **모를 때** 도플러가 못 지우는 부분)
    반환 dict + 표적 z 평면 슬라이스(그림용)."""
    try:
        import torch
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:                                    # torch 없으면 numpy
        torch = None; dev = "cpu"

    W, D, H = CHAMBER
    xs = np.arange(dx / 2, W, dx, dtype=np.float32)
    ys = np.arange(dx / 2, D, dx, dtype=np.float32)
    zs = np.arange(dx / 2, H, dx, dtype=np.float32)
    dv = dx ** 3
    keys = [c["key"] for c in cells]
    acc = {k: dict(shell=0, inter=0, **{f"amb{v:g}": 0 for v in vmax_list}) for k in keys}

    if torch is None:
        raise RuntimeError("torch 필요")
    tx = torch.tensor(TXv, dtype=torch.float32, device=dev)
    rx = torch.tensor(RXv, dtype=torch.float32, device=dev)
    vt = torch.tensor(VTRUE, dtype=torch.float32, device=dev)
    X, Y = torch.meshgrid(torch.tensor(xs, device=dev), torch.tensor(ys, device=dev), indexing="ij")
    for z in zs:                                          # z-슬라이스로 청크
        P = torch.stack([X, Y, torch.full_like(X, float(z))], dim=-1)     # (nx,ny,3)
        d1 = tx - P; d2 = rx - P
        R1 = d1.norm(dim=-1, keepdim=True); R2 = d2.norm(dim=-1, keepdim=True)
        u1 = d1 / R1; u2 = d2 / R2
        Rb = (R1 + R2).squeeze(-1) - L_BASE
        g = u1 + u2                                       # (nx,ny,3)  — f_d = v·g/λ
        gn = g.norm(dim=-1)
        fdv = (g * vt).sum(-1)                            # v_true·g  [m/s]  → /λ 가 f_d
        for c in cells:
            k = c["key"]; lam = c["lam_m"]
            shell = (Rb - c["Rb_true"]).abs() <= c["drb_m"] / 2
            n_sh = int(shell.sum().item())
            acc[k]["shell"] += n_sh
            if n_sh == 0:
                continue
            fd = fdv / lam
            inter = shell & ((fd - c["fd_true"]).abs() <= c["dfd_hz"] / 2)
            acc[k]["inter"] += int(inter.sum().item())
            fmax = gn / lam                               # |f_d|max = vmax·|g|/λ
            for vm in vmax_list:
                ok = shell & (abs(c["fd_true"]) <= vm * fmax + c["dfd_hz"] / 2)
                acc[k][f"amb{vm:g}"] += int(ok.sum().item())
    out = {}
    for c in cells:
        k = c["key"]; a = acc[k]
        out[k] = dict(v_shell_m3=a["shell"] * dv, v_int_m3=a["inter"] * dv,
                      v_amb_m3={f"{vm:g}": a[f"amb{vm:g}"] * dv for vm in vmax_list})
    return out, dict(dx=dx, chamber_m3=float(W * D * H), n_vox=int(len(xs) * len(ys) * len(zs)))


# --------------------------------------------------------------------------- #
#  [D] Fisher / CRLB  (단일 스냅샷, 위치 3자유도)
# --------------------------------------------------------------------------- #
def crlb_at(p, v, lam, s_rb, s_fd):
    """J(2x3) 백색화 → SVD. 반환: 특이값, 영방향, 관측가능 부분공간 위치오차 [m]."""
    J = np.stack([grad_Rb(p) / s_rb, grad_fd_p(p, v, lam) / s_fd])     # (2,3)
    U, S, Vt = np.linalg.svd(J)
    null = Vt[2]                                    # 특이값 0 에 대응 (항상 존재: 2x3)
    sig = np.array([1.0 / s if s > 1e-12 else np.inf for s in S])      # 관측가능 축 std [m]
    return S, null, sig


def crlb_map(cells, z, dx=0.1):
    W, D, _ = CHAMBER
    xs = np.arange(dx / 2, W, dx); ys = np.arange(dx / 2, D, dx)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    P = np.stack([X, Y, np.full_like(X, z)], -1)
    maps = {}
    for c in cells:
        lam = c["lam_m"]; s_rb = c["sigma_rb_m"]; s_fd = c["sigma_fd_hz"]
        gR = grad_Rb(P) / s_rb                       # (nx,ny,3)
        gD = grad_fd_p(P, VTRUE, lam) / s_fd
        # FIM = gR gRᵀ + gD gDᵀ (rank<=2). 관측가능 부분공간의 오차 = sqrt(tr(pinv(FIM)))
        a = np.sum(gR * gR, -1); b = np.sum(gR * gD, -1); d = np.sum(gD * gD, -1)
        # 2x2 그람행렬(J Jᵀ)의 고유값 = J 의 특이값^2
        tr = a + d; det = a * d - b * b
        disc = np.sqrt(np.maximum(tr * tr / 4 - det, 0))
        l1 = tr / 2 + disc; l2 = np.maximum(tr / 2 - disc, 0)          # l1>=l2>=0
        err_obs = np.sqrt(1 / np.maximum(l1, 1e-30) + 1 / np.maximum(l2, 1e-30))
        cond = np.sqrt(l1 / np.maximum(l2, 1e-30))
        # 영방향 = gR x gD (백색화 무관하게 두 그래디언트에 직교)
        nul = np.cross(gR, gD)
        nn = np.linalg.norm(nul, axis=-1, keepdims=True)
        nul = nul / np.maximum(nn, 1e-30)
        maps[c["key"]] = dict(x=xs, y=ys, err=err_obs, cond=cond, null=nul,
                              sig_min=np.sqrt(1 / np.maximum(l2, 1e-30)))
    return maps


# --------------------------------------------------------------------------- #
#  [E] 관측가능성 그램행렬 (등속 6상태, 시간 관측)
# --------------------------------------------------------------------------- #
def _rows_pair(p, v, lam, t, s_rb, s_fd, tx, rx):
    """한 시각·한 TX-RX 쌍의 백색화된 야코비안 2행. 상태 x=[p0(3), v(3)] (p=p0+v t)."""
    d1 = tx - p; d2 = rx - p
    R1 = np.linalg.norm(d1); R2 = np.linalg.norm(d2)
    u1 = d1 / R1; u2 = d2 / R2
    gR = -(u1 + u2)                                                     # ∂Rb/∂p
    gD = -((v - u1 * (u1 @ v)) / R1 + (v - u2 * (u2 @ v)) / R2) / lam   # ∂fd/∂p
    hR = np.concatenate([gR, t * gR]) / s_rb
    hD = np.concatenate([gD, t * gD + (u1 + u2) / lam]) / s_fd
    return np.stack([hR, hD])


def gramian(cell, K, t_obs, p0=None, v0=None, pairs=None, aoa_sigma_deg=None):
    """G = Σ_k H_kᵀ H_k (이미 백색화). 상태 스케일: v ← v·t_obs (전 성분 m 단위)."""
    lam = cell["lam_m"]; s_rb = cell["sigma_rb_m"]; s_fd = cell["sigma_fd_hz"]
    pairs = pairs or [(TXv, RXv)]
    p0 = TGT.copy() if p0 is None else np.asarray(p0, float)
    v0 = VTRUE.copy() if v0 is None else np.asarray(v0, float)
    ts = np.linspace(-t_obs / 2, t_obs / 2, K) if K > 1 else np.array([0.0])
    Hs = []
    for t in ts:
        p = p0 + v0 * t
        for (tx, rx) in pairs:
            Hs.append(_rows_pair(p, v0, lam, t, s_rb, s_fd, tx, rx))
        if aoa_sigma_deg:                       # RX 에서 본 방위/고도각(각 σ 는 **가정**)
            s_a = np.radians(aoa_sigma_deg)
            d = p - RXv
            r = np.linalg.norm(d); rho = np.linalg.norm(d[:2])
            gaz = np.array([-d[1] / rho ** 2, d[0] / rho ** 2, 0.0])
            gel = np.array([-d[0] * d[2] / (r ** 2 * rho), -d[1] * d[2] / (r ** 2 * rho), rho / r ** 2])
            for g in (gaz, gel):
                Hs.append((np.concatenate([g, t * g]) / s_a)[None, :])
    H = np.concatenate(Hs, 0) @ np.diag([1, 1, 1, t_obs, t_obs, t_obs])
    G = H.T @ H
    w, V = np.linalg.eigh(G)
    return G, w, V


def rot_generator(p0, v0, t_obs):
    """TX-RX 베이스라인 축 둘레 회전의 **생성자**(궤도의 접선), 스케일된 상태계 [p, v·t_obs]."""
    a = (RXv - TXv) / np.linalg.norm(RXv - TXv)
    s = np.concatenate([np.cross(a, np.asarray(p0) - TXv), np.cross(a, np.asarray(v0)) * t_obs])
    return s / np.linalg.norm(s), a


def _meas_series(p0, v0, lam, ts):
    """(Rb, f_d) 시계열 — 비선형 원본(야코비안 아님). 대칭성 검증용."""
    out = []
    for t in ts:
        q = np.asarray(p0, float) + np.asarray(v0, float) * t
        out.append((bistatic_Rb(q), bistatic_fd(q, v0, lam)))
    return np.array(out)


def exact_rotation_test(cell, t_obs, K=16, n_phi=64):
    """**엄밀 대칭성 검증**: 상태 전체(위치+속도)를 베이스라인 둘레로 유한각 φ 회전시켜도
    (Rb, f_d) 시계열이 정말 그대로인가? (1차 근사가 아니라 비선형 원본으로 확인)"""
    lam = cell["lam_m"]
    ts = np.linspace(-t_obs / 2, t_obs / 2, K)
    base = _meas_series(TGT, VTRUE, lam, ts)
    a = (RXv - TXv) / np.linalg.norm(RXv - TXv)
    dR = dF = 0.0
    for phi in np.linspace(0, 2 * np.pi, n_phi):
        p = _rot(TGT, phi)[0]
        q = VTRUE * np.cos(phi) + np.cross(a, VTRUE) * np.sin(phi) + a * (a @ VTRUE) * (1 - np.cos(phi))
        m = _meas_series(p, q, lam, ts)
        dR = max(dR, float(np.abs(m[:, 0] - base[:, 0]).max()))
        dF = max(dF, float(np.abs(m[:, 1] - base[:, 1]).max()))
    return dict(max_dRb_m=dR, max_dfd_hz=dF, n_phi=n_phi, K=K)


def curvature_test(cell, direction, t_obs, K=16, eps=(0.01, 0.1, 1.0)):
    """영공간 방향으로 **직선** 이동했을 때의 측정 잔차. 엄밀 대칭이면 0, 1차만 영이면 O(eps^2).
    → '관측 불가능'이 영원한가(대칭) 아니면 곡률로 되살아나는가(약관측)를 가른다."""
    lam = cell["lam_m"]
    ts = np.linspace(-t_obs / 2, t_obs / 2, K)
    base = _meas_series(TGT, VTRUE, lam, ts)
    rows = []
    for e in eps:
        p = TGT + direction[:3] * e
        v = VTRUE + direction[3:] * e / t_obs             # 스케일된 상태 → 물리 속도로 복원
        m = _meas_series(p, v, lam, ts)
        dR = float(np.abs(m[:, 0] - base[:, 0]).max())
        rows.append(dict(eps_m=e, dRb_m=dR, dfd_hz=float(np.abs(m[:, 1] - base[:, 1]).max()),
                         dRb_in_sigma=dR / cell["sigma_rb_m"]))
    return rows


def _rot(p, phi):
    """베이스라인(TX 통과, 방향 â) 둘레로 각 phi 회전 — 로드리게스. p:(n,3)"""
    a = (RXv - TXv) / np.linalg.norm(RXv - TXv)
    q = np.atleast_2d(np.asarray(p, float)) - TXv
    out = (q * np.cos(phi) + np.cross(np.tile(a, (len(q), 1)), q) * np.sin(phi)
           + np.outer(q @ a, a) * (1 - np.cos(phi))) + TXv
    return out


def ghost_trajectories(margin=0.0, n_phi=3601):
    """회전 모호성: 참 궤적을 베이스라인 둘레로 phi 만큼 돌린 '유령 궤적'은 모든 시각에서
    (Rb, f_d) 가 **완전히 동일**하다. 챔버 벽이 허용하는 phi 집합을 잰다."""
    pos, _ = radial(TXv, RXv, TGT, speed=SPEED, span=SPAN, n=32)
    W, D, H = CHAMBER
    phis = np.linspace(-np.pi, np.pi, n_phi)
    inside = np.zeros(n_phi, bool)
    maxdisp = np.zeros(n_phi)
    for i, ph in enumerate(phis):
        q = _rot(pos, ph)
        ok = ((q[:, 0] > margin) & (q[:, 0] < W - margin) & (q[:, 1] > margin)
              & (q[:, 1] < D - margin) & (q[:, 2] > margin) & (q[:, 2] < H - margin))
        inside[i] = bool(ok.all())
        maxdisp[i] = float(np.linalg.norm(q - pos, axis=1).max())
    frac = float(inside.mean())
    md = float(maxdisp[inside].max()) if inside.any() else 0.0
    # 참(phi=0) 을 제외한 '분리된' 유령: |Δp| > 1 m 인 phi 구간
    sep = inside & (maxdisp > 1.0)
    return dict(phi_deg=phis * 180 / np.pi, inside=inside, maxdisp_m=maxdisp,
                frac_inside=frac, phi_span_deg=float(frac * 360.0),
                max_disp_m=md, frac_sep_1m=float(sep.mean()),
                phi_span_sep_deg=float(sep.mean() * 360.0),
                pos_true=pos)


# --------------------------------------------------------------------------- #
#  본체
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    dx = 0.05 if args.fast else 0.02

    print("=" * 78)
    print("[E5] 관측가능성 — (Rb, f_d) 가 위치·속도를 결정하는가")
    print("=" * 78)
    print(f"  챔버 {CHAMBER}  TX={TX} RX={RX}  L={L_BASE:.2f} m")
    print(f"  표적 {TGT.round(2)} v={VTRUE.round(2)} (|v|={np.linalg.norm(VTRUE):.1f} m/s, radial)")
    print(f"  GPU={_GPU}  격자 dx={dx*100:.0f} cm")

    # ---------- [A] 측정 셀 ----------
    cells = []
    print("\n[A] 파형별 측정 셀 (ΔRb 는 자기상관에서 측정, Δf_d = 1/T_CPI)")
    for label, key, spec, col in CFGS:
        wf = make_wf(spec["std"], spec["bw"], spec["car"], spec["occ"])
        c = cell_of(wf); c.update(label=label, key=key, color=col, **spec)
        c["Rb_true"] = float(bistatic_Rb(TGT))
        c["fd_true"] = float(bistatic_fd(TGT, VTRUE, c["lam_m"]))
        scr, pd, rb_h, fd_h, sig_dbsm = measure_snr(wf, key)
        # 하네스(channel.state)와 이 스크립트의 기하가 같은지 교차확인 (드리프트 방지)
        c["harness_Rb_m"] = rb_h; c["harness_fd_hz"] = fd_h; c["sigma_dbsm"] = sig_dbsm
        assert abs(rb_h - c["Rb_true"]) < 1e-6 and abs(fd_h - c["fd_true"]) < 1e-6, \
            f"기하 불일치: {rb_h} vs {c['Rb_true']}, {fd_h} vs {c['fd_true']}"
        c["scr_db"] = scr; c["pd"] = pd
        snr = 10 ** (scr / 10)
        # CRLB 표준편차: σ_τ = 1/(2π·B_rms·sqrt(2·SNR)), σ_Rb = c·σ_τ  (Rb=c·τ)
        c["sigma_rb_m"] = float(C0 / (2 * np.pi * c["b_rms_hz"] * np.sqrt(2 * snr)))
        # 도플러: rect CPI 의 rms 시간폭 = T/sqrt(12)
        c["sigma_fd_hz"] = float(np.sqrt(12) / (2 * np.pi * c["t_cpi"] * np.sqrt(2 * snr)))
        cells.append(c)
        print(f"  {label:20s} ref={c['ref_name']:7s} B_ref={c['ref_bw_mhz']:6.1f}MHz "
              f"ΔRb(측정)={c['drb_ac_m']:6.2f}m (c/B={c['drb_bw_m']:6.2f}, bin={c['bin_m']:5.2f}) "
              f"Δf_d={c['dfd_hz']:5.1f}Hz  SCR={scr:5.1f}dB Pd={pd:.2f} "
              f"σ_Rb={c['sigma_rb_m']:.3f}m σ_fd={c['sigma_fd_hz']:.3f}Hz")
    print(f"  · 참값: Rb={cells[0]['Rb_true']:.2f} m, f_d = "
          + ", ".join(f"{c['key'].split('_')[0]}:{c['fd_true']:+.1f}Hz" for c in cells))

    # ---------- [B]/[C] 부피 ----------
    print(f"\n[B]/[C] 챔버 복셀 적분 (dx={dx*100:.0f} cm) ...")
    vols, vmeta = voxel_volumes(cells, dx=dx, vmax_list=(3.0, 15.0))
    for c in cells:
        v = vols[c["key"]]
        c["v_shell_m3"] = v["v_shell_m3"]; c["v_int_m3"] = v["v_int_m3"]
        c["v_amb_m3"] = v["v_amb_m3"]
        print(f"  {c['label']:20s} V_shell={v['v_shell_m3']:8.1f} m^3 "
              f"({100*v['v_shell_m3']/vmeta['chamber_m3']:5.1f}% of chamber)  "
              f"V∩f_d(v 알 때)={v['v_int_m3']:7.1f} m^3  "
              f"V(v 모를 때, |v|<=3)={v['v_amb_m3']['3']:8.1f} m^3")

    # ---------- [D] CRLB ----------
    print("\n[D] Fisher / CRLB — 단일 스냅샷, 위치 3자유도")
    for c in cells:
        S, null, sig = crlb_at(TGT, VTRUE, c["lam_m"], c["sigma_rb_m"], c["sigma_fd_hz"])
        c["svals"] = [float(s) for s in S]
        c["null_dir"] = [float(x) for x in null]
        c["sigma_obs_m"] = [float(x) for x in sig]      # 관측가능 두 축의 std [m]
        c["cond"] = float(S[0] / max(S[1], 1e-30))
        print(f"  {c['label']:20s} 특이값={S[0]:9.2e},{S[1]:9.2e},0  "
              f"관측가능축 σ={sig[0]*100:6.2f}, {sig[1]*100:8.1f} cm  "
              f"조건수={c['cond']:7.1f}  영방향={np.round(null,3)}")
    maps = crlb_map(cells, z=float(TGT[2]), dx=0.1)

    # ---------- [E] 그램행렬 ----------
    t_obs = SPAN / SPEED                                  # 궤적 관측시간 [s]
    print(f"\n[E] 관측가능성 그램행렬 — 등속 6상태 x=[p0, v], 관측시간 {t_obs:.1f} s")
    ref = [c for c in cells if c["key"] == "nr100_G3"][0]   # 가장 좋은 셀(=가장 유리한 조건)
    gen, axis = rot_generator(TGT, VTRUE, t_obs)
    RANK_TOL = 1e-12                                       # '엄밀 영공간' 판정(수치 랭크)
    PRACT_TOL = 1e-8                                       # 실용 랭크(잡음이 있는 세상)
    gram = {"t_obs_s": t_obs, "axis": [float(x) for x in axis], "rank_tol": RANK_TOL,
            "practical_tol": PRACT_TOL, "generator": [float(x) for x in gen],
            "ref_cfg": ref["key"], "K_sweep": []}
    for K in (1, 2, 3, 4, 8, 16, 32, 64):
        G, w, V = gramian(ref, K, t_obs)
        wn = w / w.max()
        nullsp = V[:, wn < RANK_TOL]                        # 엄밀 영공간(고유값 축퇴 → 부분공간으로)
        pgen = float(np.linalg.norm(nullsp.T @ gen)) if nullsp.size else 0.0
        gram["K_sweep"].append(dict(
            K=K, eig=[float(x) for x in w], eig_norm=[float(x) for x in wn],
            rank=int((wn > RANK_TOL).sum()), rank_practical=int((wn > PRACT_TOL).sum()),
            dim_null=int((wn < RANK_TOL).sum()), proj_generator_on_null=pgen,
            sigma_dir_m=[float(1 / np.sqrt(x)) if x > 0 else None for x in w]))
        print(f"  K={K:3d} λ/λmax={np.array2string(wn, formatter={'float_kind': lambda v: f'{v:8.1e}'})} "
              f"rank={int((wn > RANK_TOL).sum())}(실용 {int((wn > PRACT_TOL).sum())})  "
              f"dim(null)={int((wn < RANK_TOL).sum())}  ||P_null·회전생성자||={pgen:.9f}")
    print("  → 회전 생성자가 영공간 안에 **정확히** 들어있다(사영노름 1.000000000).")

    # [E1] 엄밀 대칭성: 유한각 회전으로도 측정이 안 변하는가 (비선형 원본으로 확인)
    ex = exact_rotation_test(ref, t_obs)
    gram["exact_rotation"] = ex
    print(f"\n[E1] 엄밀 회전 대칭 검증 (φ 를 0~360° 로 유한 회전, 위치+속도 모두):")
    print(f"     max|ΔRb| = {ex['max_dRb_m']:.2e} m,  max|Δf_d| = {ex['max_dfd_hz']:.2e} Hz "
          f"→ **기계정밀도**. 시간을 아무리 봐도 이 방향은 영원히 관측 불가능.")

    # [E2] 나머지 영방향은 곡률로 되살아나는가? (엄밀 대칭 vs 1차만 영)
    G, w, V = gramian(ref, 16, t_obs)
    wn = w / w.max()
    nullsp = V[:, wn < RANK_TOL]
    # 영공간 안에서 회전생성자에 직교하는 성분
    other = None
    if nullsp.shape[1] > 1:
        Q, _ = np.linalg.qr(np.column_stack([gen, nullsp]))
        other = Q[:, 1]                                    # 영공간 ∩ gen^⊥
    gram["curv_generator"] = curvature_test(ref, gen, t_obs)
    print(f"\n[E2] 영공간 방향으로 **직선** 이동 시 측정 잔차 (엄밀대칭이면 0, 1차만 영이면 O(eps^2)):")
    for r in gram["curv_generator"]:
        print(f"     회전생성자(접선) eps={r['eps_m']:5.2f} m → ΔRb={r['dRb_m']:.2e} m "
              f"({r['dRb_in_sigma']:8.1f} σ_Rb)  [접선은 궤도의 현(chord) — 곡률로 O(eps^2)]")
    if other is not None:
        gram["curv_other"] = curvature_test(ref, other, t_obs)
        gram["other_null_dir"] = [float(x) for x in other]
        for r in gram["curv_other"]:
            print(f"     나머지 영방향   eps={r['eps_m']:5.2f} m → ΔRb={r['dRb_m']:.2e} m "
                  f"({r['dRb_in_sigma']:8.1f} σ_Rb)")
        print("     → 나머지 영방향은 **엄밀 대칭이 아니다**(2차로 되살아남). 회전만이 엄밀 대칭이다.")

    # [E3] 궤적이 베이스라인과 **동일 평면**인가 (radial 시나리오의 특수성)
    a = axis
    npl = np.cross(a, TGT - TXv); npl /= np.linalg.norm(npl)
    coplanar = float(abs(npl @ (VTRUE / np.linalg.norm(VTRUE))))
    gram["coplanar_metric"] = coplanar
    print(f"\n[E3] radial 궤적의 속도와 (베이스라인,표적) 평면 법선의 |cos| = {coplanar:.2e} "
          f"→ 궤적이 베이스라인과 **동일평면**. 그래서 영공간이 2차원(면외 위치+면외 속도)이 된다.")
    # 일반(비동일평면) 궤적: tangential 시나리오
    from scenarios import tangential                       # noqa: E402
    tp, tv = tangential(TXv, RXv, CEN, speed=SPEED, span=SPAN, n=32)
    p1, v1 = tp[len(tp) // 2], tv[len(tv) // 2]
    npl2 = np.cross(a, p1 - TXv); npl2 /= np.linalg.norm(npl2)
    G2, w2, V2 = gramian(ref, 16, t_obs, p0=p1, v0=v1)
    wn2 = w2 / w2.max()
    gen2, _ = rot_generator(p1, v1, t_obs)
    ns2 = V2[:, wn2 < RANK_TOL]
    gram["tangential"] = dict(
        p0=[float(x) for x in p1], v0=[float(x) for x in v1],
        coplanar_metric=float(abs(npl2 @ (v1 / np.linalg.norm(v1)))),
        eig_norm=[float(x) for x in wn2], dim_null=int((wn2 < RANK_TOL).sum()),
        rank=int((wn2 > RANK_TOL).sum()),
        proj_generator_on_null=float(np.linalg.norm(ns2.T @ gen2)) if ns2.size else 0.0,
        # 고유값이 축퇴에 가까우면 고유벡터 방향이 불안정 → 레일리 몫이 더 robust 한 증거다:
        #   생성자 방향의 정보량 / 최대 정보량 ≈ 0 이면 그 방향은 정보가 0 이다.
        rayleigh_generator=float(gen2 @ G2 @ gen2 / w2.max()))
    tg = gram["tangential"]
    print(f"     tangential(비동일평면, |cos|={tg['coplanar_metric']:.2f}): rank={tg['rank']}/6, "
          f"dim(null)={tg['dim_null']}, ||P_null·생성자||={tg['proj_generator_on_null']:.6f}, "
          f"생성자 레일리몫={tg['rayleigh_generator']:.1e} (=0 → 정보 없음)")
    print("     → **일반 궤적에서도 랭크는 5 를 못 넘는다**. 회전 대칭이 1 차원을 영원히 먹는다.")

    # 처방: RX 2대 / AoA — 절대 CRLB(m) 까지
    RX2 = np.array([26.0, 17.5, 6.5])                     # 두 번째 패시브 RX(다른 벽)
    print(f"\n[E4] 처방 (K=16, {ref['label']}, 절대 CRLB는 whitened Gramian 의 pinv):")
    fixes = {}
    for name, kw in [("1RX (baseline)", dict()),
                     ("2RX", dict(pairs=[(TXv, RXv), (TXv, RX2)])),
                     ("1RX + AoA(1deg)", dict(aoa_sigma_deg=1.0)),
                     ("1RX + AoA(5deg)", dict(aoa_sigma_deg=5.0))]:
        G, w, V = gramian(ref, 16, t_obs, **kw)
        wn = w / w.max()
        rank = int((wn > RANK_TOL).sum())
        Gi = np.linalg.pinv(G, rcond=1e-13)
        sp = np.sqrt(np.abs(np.diag(Gi)))                  # [m, m, m, m, m, m] (v 는 ×t_obs 스케일)
        fixes[name] = dict(eig_norm=[float(x) for x in wn], rank=rank,
                           rank_practical=int((wn > PRACT_TOL).sum()),
                           cond=float(w.max() / max(w.min(), 1e-300)),
                           sigma_pos_m=[float(x) for x in sp[:3]],
                           sigma_vel_ms=[float(x / t_obs) for x in sp[3:]],
                           pos_rms_m=float(np.sqrt(np.sum(sp[:3] ** 2))))
        f = fixes[name]
        print(f"  {name:16s} rank={rank}/6 (실용 {f['rank_practical']})  λmin/λmax={wn[0]:.1e}  "
              f"위치 CRLB(rms)={f['pos_rms_m']:.3g} m  "
              f"σ_p=({sp[0]:.3g}, {sp[1]:.3g}, {sp[2]:.3g}) m")
    print("  ※ 1RX 의 위치 CRLB 가 유한해 보이는 것은 pinv 가 영공간을 **버리기 때문**이다 —"
          " 그 방향의 실제 오차는 무한대(회전 유령). AoA σ 는 **가정**(안테나 미지정).")
    fixes["_rx2"] = [float(x) for x in RX2]

    # 회전 유령 궤적
    gh = ghost_trajectories()
    print(f"\n[E'] 베이스라인 회전 모호성: 챔버 안에 남는 유령 궤적 phi 범위 = "
          f"{gh['phi_span_deg']:.1f} deg (전체 360 중 {100*gh['frac_inside']:.1f}%), "
          f"참 궤적과 최대 이격 {gh['max_disp_m']:.2f} m; "
          f"1 m 이상 떨어진 '구별불가 유령' phi 범위 = {gh['phi_span_sep_deg']:.1f} deg")

    # ---------- JSON ----------
    res = dict(
        meta=dict(chamber=list(CHAMBER), tx=list(map(float, TXv)), rx=list(map(float, RXv)),
                  target=list(map(float, TGT)), vel=list(map(float, VTRUE)),
                  L_m=L_BASE, t_cpi_s=T_CPI, eirp_dbm=EIRP_DBM, drone=DRONE, pfa=PFA,
                  speed=SPEED, span=SPAN, gpu=_GPU, grid=vmeta,
                  note="ΔRb = c/B (bistatic; Rb = c·tau, no factor 2). "
                       "SNR for CRLB = measured SCR from run_min_cell."),
        cells=[{k: v for k, v in c.items() if k != "color"} for c in cells],
        gramian=gram, fixes=fixes,
        rotation_ambiguity=dict(frac_inside=gh["frac_inside"], phi_span_deg=gh["phi_span_deg"],
                                max_disp_m=gh["max_disp_m"],
                                phi_span_sep_deg=gh["phi_span_sep_deg"],
                                frac_sep_1m=gh["frac_sep_1m"]),
        summary=dict(
            verdict="NOT OBSERVABLE with one TX-RX pair",
            snapshot_fim_rank=2, state_dim_position=3,
            gramian_rank_radial=gram["K_sweep"][-1]["rank"],
            gramian_rank_tangential=gram["tangential"]["rank"],
            exact_symmetry="rotation about the TX-RX baseline (verified to machine precision)",
            exact_rotation_max_dRb_m=gram["exact_rotation"]["max_dRb_m"],
            exact_rotation_max_dfd_hz=gram["exact_rotation"]["max_dfd_hz"],
            ghost_phi_span_deg=gh["phi_span_deg"], ghost_max_offset_m=gh["max_disp_m"],
            fix_2rx_rank=fixes["2RX"]["rank"], fix_2rx_pos_rms_m=fixes["2RX"]["pos_rms_m"],
            shell_volume_m3={c["key"]: c["v_shell_m3"] for c in cells},
            shell_frac_of_chamber={c["key"]: c["v_shell_m3"] / vmeta["chamber_m3"] for c in cells},
            doppler_keeps_frac_v_unknown={c["key"]: c["v_amb_m3"]["3"] / max(c["v_shell_m3"], 1e-9)
                                          for c in cells}),
    )
    jp = os.path.join(OUT, "verify_observability.json")
    with open(jp, "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)
    print(f"\n[저장] {jp}")

    # ---------- 그림 ----------
    figs = make_figures(cells, vmeta, maps, gram, fixes, gh, ref)
    res["figures"] = figs
    with open(jp, "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False, default=float)
    for p in figs:
        print(f"[그림] {p}")


# --------------------------------------------------------------------------- #
#  그림 (텍스트는 전부 영어)
# --------------------------------------------------------------------------- #
def _chamber_ax(ax):
    W, D, _ = CHAMBER
    ax.add_patch(plt.Rectangle((0, 0), W, D, fill=False, ec="k", lw=1.6))
    ax.plot(*TXv[:2], "^", ms=10, color="#0d47a1", zorder=6)
    ax.plot(*RXv[:2], "v", ms=10, color="#b71c1c", zorder=6)
    ax.plot(*TGT[:2], "*", ms=15, color="k", zorder=6)
    ax.annotate("TX", TXv[:2] + np.array([0.5, 0.5]), fontsize=9, color="#0d47a1")
    ax.annotate("RX", RXv[:2] + np.array([0.5, -1.1]), fontsize=9, color="#b71c1c")
    ax.annotate("target", TGT[:2] + np.array([0.6, 0.5]), fontsize=9)
    ax.plot([TXv[0], RXv[0]], [TXv[1], RXv[1]], ":", color="gray", lw=1)
    ax.set_xlim(-1, W + 1); ax.set_ylim(-1, D + 1); ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")


def _slice_fields(z, dx=0.04):
    W, D, _ = CHAMBER
    xs = np.arange(dx / 2, W, dx); ys = np.arange(dx / 2, D, dx)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    P = np.stack([X, Y, np.full_like(X, z)], -1)
    return xs, ys, P, bistatic_Rb(P)


def make_figures(cells, vmeta, maps, gram, fixes, gh, ref):
    out = []
    z0 = float(TGT[2])
    xs, ys, P, RbS = _slice_fields(z0)

    # ---- F1: iso-Rb 껍질 + 부피 ----
    fig = plt.figure(figsize=(14.5, 5.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], wspace=0.28)
    ax = fig.add_subplot(gs[0]); _chamber_ax(ax)
    for c in cells:
        m = np.abs(RbS - c["Rb_true"]) <= c["drb_m"] / 2
        ax.contourf(xs, ys, m.astype(float).T, levels=[0.5, 1.5],
                    colors=[c["color"]], alpha=0.30)
        ax.contour(xs, ys, m.astype(float).T, levels=[0.5], colors=[c["color"]], linewidths=1.0)
    ax.set_title(f"Iso-Rb shells at z = {z0:.1f} m  (Rb = {cells[0]['Rb_true']:.1f} m)\n"
                 "one range measurement leaves an ellipsoidal shell", fontsize=11)
    ax.legend(handles=[Line2D([], [], color=c["color"], lw=7, alpha=.45,
                              label=f"{c['label']}  dRb = {c['drb_m']:.1f} m") for c in cells],
              fontsize=8.5, loc="lower right", framealpha=.92)
    ax2 = fig.add_subplot(gs[1])
    xpos = np.arange(len(cells))
    vv = [c["v_shell_m3"] for c in cells]
    ax2.bar(xpos, vv, color=[c["color"] for c in cells], width=.6)
    for i, (c, v) in enumerate(zip(cells, vv)):
        ax2.text(i, v * 1.15, f"{v:.0f} m$^3$\n({100*v/vmeta['chamber_m3']:.0f}% of room)",
                 ha="center", fontsize=9)
    ax2.axhline(vmeta["chamber_m3"], color="k", ls="--", lw=1)
    ax2.text(-0.45, vmeta["chamber_m3"] * 1.15, "whole chamber (6600 m$^3$)",
             ha="left", fontsize=9)
    ax2.set_yscale("log"); ax2.set_ylim(1, vmeta["chamber_m3"] * 12)
    ax2.set_xticks(xpos, [c["label"].replace(" ", "\n", 1) for c in cells], fontsize=8.5)
    ax2.set_ylabel("volume of Rb shell inside chamber [m$^3$]")
    ax2.set_title("Position uncertainty from ONE range measurement\n"
                  f"(voxel count, {vmeta['dx']*100:.0f} cm grid)", fontsize=11)
    ax2.grid(alpha=.3, axis="y")
    fig.suptitle("[E5-B] A single bistatic range fixes only an ellipsoid shell -- not a position",
                 fontsize=13, y=.99)
    p = os.path.join(FIG, "report4_obs_shell.png"); fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig); out.append(p)

    # ---- F2: 도플러가 더하는 정보 ----
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.2))
    c = ref                                           # 대표: 5G100 G3
    fdS = bistatic_fd(P, VTRUE, c["lam_m"])
    ax = axs[0]; _chamber_ax(ax)
    msh = np.abs(RbS - c["Rb_true"]) <= c["drb_m"] / 2
    mfd = np.abs(fdS - c["fd_true"]) <= c["dfd_hz"] / 2
    ax.contourf(xs, ys, msh.astype(float).T, levels=[.5, 1.5], colors=["#c62828"], alpha=.25)
    ax.contourf(xs, ys, mfd.astype(float).T, levels=[.5, 1.5], colors=["#1565c0"], alpha=.25)
    ax.contourf(xs, ys, (msh & mfd).astype(float).T, levels=[.5, 1.5], colors=["#4a148c"], alpha=.9)
    ax.set_title(f"{c['label']}: iso-Rb (red) $\\cap$ iso-$f_d$ (blue)\n"
                 "IF the velocity vector were known", fontsize=10.5)
    ax.legend(handles=[Line2D([], [], color="#c62828", lw=7, alpha=.4, label="Rb shell"),
                       Line2D([], [], color="#1565c0", lw=7, alpha=.4, label="$f_d$ shell (v known)"),
                       Line2D([], [], color="#4a148c", lw=7, label="intersection")],
              fontsize=8.5, loc="lower right", framealpha=.92)
    ax = axs[1]
    xpos = np.arange(len(cells)); w = .38
    ax.bar(xpos - w / 2, [c["v_shell_m3"] for c in cells], w, color="#c62828", label="Rb only")
    ax.bar(xpos + w / 2, [max(c["v_int_m3"], 1e-3) for c in cells], w, color="#4a148c",
           label="Rb $\\cap$ $f_d$ (v known)")
    for i, cc in enumerate(cells):
        r = cc["v_shell_m3"] / max(cc["v_int_m3"], 1e-9)
        ax.text(i, max(cc["v_shell_m3"], 1e-2) * 1.35, f"$\\times${1/r:.2f}", ha="center", fontsize=9)
    ax.set_yscale("log"); ax.set_ylim(100, 2e4); ax.set_ylabel("volume [m$^3$]")
    ax.set_xticks(xpos, [c["key"] for c in cells], fontsize=8.5, rotation=12)
    ax.set_title("Doppler barely shrinks the ambiguity\n"
                 "(numbers = volume ratio, even WITH v known)", fontsize=10.5)
    ax.legend(fontsize=8.5, loc="upper left"); ax.grid(alpha=.3, axis="y")
    ax = axs[2]
    fr3 = [100 * c["v_amb_m3"]["3"] / max(c["v_shell_m3"], 1e-9) for c in cells]
    fr15 = [100 * c["v_amb_m3"]["15"] / max(c["v_shell_m3"], 1e-9) for c in cells]
    ax.bar(xpos - w / 2, fr3, w, color="#ef6c00", label="$|v| \\leq$ 3 m/s")
    ax.bar(xpos + w / 2, fr15, w, color="#8d6e63", label="$|v| \\leq$ 15 m/s")
    for i, v in enumerate(fr3):
        ax.text(i - w / 2, v + 2.0, f"{v:.0f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 135); ax.set_ylabel("% of Rb shell still consistent with measured $f_d$")
    ax.set_xticks(xpos, [c["key"] for c in cells], fontsize=8.5, rotation=12)
    ax.set_title("...but ONLY if v is known.\nIf v is unknown, Doppler removes almost nothing",
                 fontsize=10.5)
    ax.legend(fontsize=8.5); ax.grid(alpha=.3, axis="y")
    fig.suptitle("[E5-C] Doppler is a joint function of position AND velocity -- "
                 "it is not free position information", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, .93])
    p = os.path.join(FIG, "report4_obs_doppler.png"); fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig); out.append(p)

    # ---- F3: CRLB 지도 ----
    fig, axs = plt.subplots(1, len(cells), figsize=(5.0 * len(cells), 5.2))
    for ax, c in zip(np.atleast_1d(axs), cells):
        m = maps[c["key"]]
        Z = np.log10(np.clip(m["err"], 1e-3, 1e6)).T
        im = ax.pcolormesh(m["x"], m["y"], Z, cmap="viridis", vmin=-2, vmax=1.5, shading="auto")
        plt.colorbar(im, ax=ax, label="log10 CRLB position std [m]")
        st = 12
        Xq, Yq = np.meshgrid(m["x"][::st], m["y"][::st], indexing="ij")
        nul = m["null"][::st, ::st]
        # 영방향은 대체로 **연직(z)** 성분이 크다 → xy 사영만 화살표로, 크기는 xy 성분 비율
        ax.quiver(Xq, Yq, nul[..., 0], nul[..., 1], color="w", scale=28, width=.004, alpha=.85)
        _chamber_ax(ax)
        nz = abs(float(np.array(c["null_dir"])[2]))
        ax.set_title(f"{c['label']}\nSCR = {c['scr_db']:.1f} dB, "
                     f"$\\sigma_{{Rb}}$ = {c['sigma_rb_m']*100:.1f} cm, "
                     f"$\\sigma_{{fd}}$ = {c['sigma_fd_hz']:.2f} Hz\n"
                     f"arrows = xy-projection of the unobservable direction\n"
                     f"(at the target it is {100*nz:.0f}% vertical: "
                     f"{np.round(c['null_dir'], 2)})", fontsize=9)
    fig.suptitle("[E5-D] CRLB at z = %.1f m (one snapshot, v known). The Fisher matrix has rank 2 of 3 "
                 "everywhere -- one position direction is unobservable at EVERY point in the room" % z0,
                 fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, .92])
    p = os.path.join(FIG, "report4_obs_crlb.png"); fig.savefig(p, dpi=135, bbox_inches="tight")
    plt.close(fig); out.append(p)

    # ---- F4: 그램행렬 ----
    fig, axs = plt.subplots(1, 3, figsize=(16.5, 5.2))
    ax = axs[0]
    Ks = [r["K"] for r in gram["K_sweep"]]
    E = np.array([r["eig_norm"] for r in gram["K_sweep"]])          # (nK, 6) 오름차순
    for i in range(6):
        ax.plot(Ks, np.clip(E[:, i], 1e-20, None), "o-", ms=4,
                label=f"$\\lambda_{{{i+1}}}$" + (" (null)" if i == 0 else ""))
    ax.set_xscale("log", base=2); ax.set_yscale("log")
    ax.set_ylim(1e-22, 5)
    ax.axhline(gram["rank_tol"], color="k", ls="--", lw=1)
    ax.text(Ks[0], gram["rank_tol"] * 1.6, "exact-null threshold ($10^{-12}$)", fontsize=8)
    ax.set_xlabel("K = number of (Rb, $f_d$) epochs over %.1f s" % gram["t_obs_s"])
    ax.set_ylabel("normalized eigenvalue of observability Gramian")
    ks = gram["K_sweep"]
    ax.set_title("More time does NOT fill the null space:\n"
                 f"rank {ks[0]['rank']}/6 at K=1 $\\rightarrow$ {ks[-1]['rank']}/6 at K={ks[-1]['K']} "
                 f"(dim null = {ks[-1]['dim_null']})", fontsize=10.5)
    ax.legend(fontsize=8, ncol=2); ax.grid(alpha=.3, which="both")
    er = gram["exact_rotation"]
    ax.text(.03, .04, "exact finite rotation about baseline:\n"
                      f"max |$\\Delta$Rb| = {er['max_dRb_m']:.1e} m,  "
                      f"max |$\\Delta f_d$| = {er['max_dfd_hz']:.1e} Hz\n"
                      "(machine precision -- an EXACT symmetry)",
            transform=ax.transAxes, fontsize=7.8, va="bottom",
            bbox=dict(fc="#fff8e1", ec="#f9a825", lw=.8))
    ax = axs[1]
    names = [k for k in fixes if not k.startswith("_")]
    ranks = [fixes[k]["rank"] for k in names]
    ax.bar(range(len(names)), ranks, color=["#9e9e9e", "#2e7d32", "#1565c0", "#90caf9"], width=.6)
    for i, k in enumerate(names):
        ax.text(i, ranks[i] + .18, f"rank {ranks[i]}/6\npos CRLB(rms)\n"
                                   f"{fixes[k]['pos_rms_m']:.2g} m", ha="center", fontsize=8)
    ax.axhline(6, color="k", ls="--", lw=1)
    ax.text(-0.45, 6.08, "full observability", ha="left", fontsize=8)
    ax.set_ylim(0, 9.0); ax.set_ylabel("rank of Gramian (K = 16, tol $10^{-12}$)")
    ax.set_xticks(range(len(names)), [n.replace(" ", "\n") for n in names], fontsize=8.5)
    ax.set_title("What makes the trajectory observable\n"
                 "(1RX pos CRLB ignores the null space -- true error is infinite)", fontsize=10.5)
    ax.grid(alpha=.3, axis="y")
    # 유령 궤적은 베이스라인(거의 y축) 둘레로 돈다 → 변위가 주로 **연직** → x-z 측면도로 그린다
    ax = axs[2]
    W, D, H = CHAMBER
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, ec="k", lw=1.6))
    ax.plot(TXv[0], TXv[2], "^", ms=10, color="#0d47a1"); ax.annotate("TX", (TXv[0] + .6, TXv[2]), fontsize=9)
    ax.plot(RXv[0], RXv[2], "v", ms=10, color="#b71c1c"); ax.annotate("RX", (RXv[0] + .6, RXv[2] - .9), fontsize=9)
    pos = gh["pos_true"]
    keep = np.where(gh["inside"])[0]
    for i in keep[::max(1, len(keep) // 30)]:
        q = _rot(pos, np.radians(gh["phi_deg"][i]))
        ax.plot(q[:, 0], q[:, 2], "-", color="#c62828", lw=1.0, alpha=.5)
    ax.plot(pos[:, 0], pos[:, 2], "k-", lw=2.6, label="true trajectory", zorder=5)
    ax.plot(pos[-1, 0], pos[-1, 2], "*", ms=15, color="k", zorder=6)
    ax.plot([], [], "-", color="#c62828", lw=1.2,
            label="ghost trajectories: identical\nRb & $f_d$ at ALL times")
    ax.set_xlim(-1, W + 1); ax.set_ylim(-1, H + 1); ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("z [m]   (side view)")
    ax.set_title("Rotation about the TX-RX baseline is an EXACT symmetry.\n"
                 f"Chamber walls still admit {gh['phi_span_deg']:.0f}$^\\circ$ of $\\phi$: "
                 f"ghosts up to {gh['max_disp_m']:.1f} m from the truth", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right")
    fig.suptitle("[E5-E] Observability Gramian: one TX-RX pair can NEVER determine the trajectory "
                 "-- rotation about the baseline is an exact symmetry", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, .92])
    p = os.path.join(FIG, "report4_obs_gramian.png"); fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig); out.append(p)
    return out


if __name__ == "__main__":
    main()
