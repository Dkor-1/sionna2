# -*- coding: utf-8 -*-
"""
report16_verify_kernel.py — ⭐ **적대검증: 이 라운드의 숫자를 커널이 감당하는가**
================================================================================

무엇을 묻는가 (쉬운 말로)
--------------------------------------------------------------------------------
report16 라운드는 «드론이 떠 있을 때 프로펠러가 돌아서 생기는 전파의 떨림»
(마이크로도플러) 을 계산하고, 그것으로 «정밀한 3D 형상이 값어치가 있는가» 를 따졌다.
그 계산을 하는 프로그램(우리는 «커널» 이라 부른다) 은 **물리광학(PO)** 이라는 근사다.
PO 는 «전파가 부딪히는 면이 파장에 비해 충분히 넓을 때» 만 맞는다.

문제는 이렇다 — 프로펠러 날개의 폭은 **13.78 mm** 인데, 우리가 쓰는 3.5 GHz 의
파장은 **85.7 mm** 다. 날개는 파장의 **0.16 배**밖에 안 된다. PO 가 1 dB 안으로
맞으려면 폭이 파장의 **0.729 배**는 되어야 한다(outputs/report00_po_case.json).
그 조건을 넘으려면 **15.86 GHz** 가 필요하다.
**즉, 떨림을 만드는 바로 그 부품이 커널이 가장 못 믿을 부품이다.**

그래서 이 파일은 네 가지를 직접 계산해서 확인한다.

  T1  **가림(occlusion)** — 날개가 동체 뒤로 돌아갈 때 그늘에 들어가는가.
      라운드의 커널에는 그늘이 아예 없다(선언된 통제다). 없으면 얼마나 틀리나?
      → 깊이버퍼(z-buffer) 로 그늘을 **넣어서** 다시 계산하고, 그 이동량을
        라운드가 주장하는 효과 크기와 나란히 놓는다.
  T2  **주파수** — PO 무릎(15.86 GHz) 위로 올리면 결론이 뒤집히는가.
      라운드는 3.5 와 15.86 두 점뿐이다. 여기서는 그 사이를 훑어 곡선으로 만든다.
  T3  **크기 견주기** — «옛 메쉬(07-27) → 새 메쉬» 로 바뀐 양이 이 라운드의 결론
      크기보다 큰가. 크다면 «메쉬 정밀도가 마이크로도플러를 바꾼다» 가 별개의 강한
      결과이고, 동시에 이 라운드 숫자의 유통기한이 짧다는 뜻이다.
  T4  **삼각형 절반 단** — 대역을 올렸을 때 판정이 뒤집혔는가(기존 산출물 감사).

⭐ 이 파일이 새로 만든 숫자는 **전부 crude(거친 추정)** 다. 깊이버퍼 그늘은 진짜
  광선추적이 아니고, 회절·다중반사·편파는 여전히 없다. 그래도 «없는 것보다 크게 나은»
  하한선은 준다 — 그늘을 넣었더니 지표가 얼마나 움직이는지는 실제로 재는 것이기 때문이다.

⛔ outputs/report15_*·benchmark/report15_* 미접촉. src/make_report0N_*·report0N_*.ipynb 미접촉.
⛔ src/drones.py·src/drone_cad.py 는 **읽기 전용**으로만 import.
⛔ 숫자 손입력 금지 — 아래 문턱 몇 개(격자 칸 크기 후보 등) 말고는 전부 계산한다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, _HERE)

OUT_JSON = os.path.join(ROOT, "outputs", "report16_verify_kernel.json")

# --------------------------------------------------------------------------- #
#  손으로 정하는 수 — 이것뿐이다 (나머지는 계산하거나 기존 산출물에서 읽는다)
# --------------------------------------------------------------------------- #
CELL_CANDIDATES_M = (1e-3, 2e-3, 5e-3)     # 깊이버퍼 칸 크기 후보 [m] — 민감도용
TOL_MODES = ("adaptive", "fixed")          # 그늘 판정 여유 방식
SWEEP_GHZ = (3.5, 5.0, 7.0, 10.0, 15.86, 22.0)   # 주파수 훑기 (3.5=생산, 15.86=PO 무릎)
N_AZ_SWEEP = 12                            # 훑기 방위 수 (기반 24 의 절반 — 계산비 절약)
N_AZ_OCC_HI = 8                            # 무릎 대역 가림 시험 방위 수


def sha(path, n=12):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:n]


def summar(v):
    v = np.asarray([x for x in np.ravel(v) if np.isfinite(x)], float)
    if v.size == 0:
        return dict(mean=float("nan"), n=0)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else 0.0,
                min=float(v.min()), max=float(v.max()), n=int(v.size))


# =========================================================================== #
#  §A  가림을 넣을 수 있는 전역좌표 PO 커널 (내가 새로 짠 것)
# =========================================================================== #
#  기반 커널은 «안테나를 반대로 돌려» 로터 하나씩 따로 더한다 — 빠르지만 부품끼리
#  서로를 가릴 수가 없다(각자 자기 좌표계에 있으므로). 여기서는 모든 점을 **전역좌표**로
#  옮겨 한 판에 올린다. 그래야 «동체 뒤로 들어간 날개» 를 지울 수 있다.
def _rz(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


class Kernel:
    def __init__(self):
        from gpu import pick, budget_mb            # ⚠ torch 보다 먼저
        self.picked = pick(verbose=True)
        import torch
        self.torch = torch
        self.dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.budget_mb = budget_mb()

    def tg(self, x):
        return self.torch.as_tensor(np.ascontiguousarray(x), dtype=self.torch.float64,
                                    device=self.dev)

    def table(self, cl, fc, az_deg, proto, occlude=False, cell_m=2e-3, tol_mode="adaptive",
              tol_cells=1.0, wavefront="spherical", batch=None):
        """한 방위의 한 바퀴 위상 표 E(φ).

        가림 = **깊이버퍼**: 시선에 수직인 평면을 cell_m 짜리 칸으로 나누고, 한 칸 안에서
        레이더에 가장 가까운 면보다 뒤에 있는 점은 그늘로 본다. 여유(tol) 를 두는 이유는
        «같은 면» 이 칸 안에서 기울어져 있으면 깊이가 조금씩 다르기 때문이다.
          · adaptive : 여유 = cell / |n̂·û|  → 비스듬한 면일수록 여유를 크게 (자기그늘 방지)
          · fixed    : 여유 = tol_cells · cell
        ⚠ 이것은 진짜 광선추적이 아니다. 거친 하한선이다."""
        from report16_base import look_and_antenna, EL_DEG, RANGE_M, C0
        torch = self.torch
        dev = self.dev
        S = int(proto["n_phase"])
        k = 2.0 * math.pi / (C0 / fc)
        phis = np.linspace(0.0, 2 * math.pi, S, endpoint=False)
        u0, A, R_t = look_and_antenna(az_deg, EL_DEG, RANGE_M)
        tmp = np.array([0.0, 0.0, 1.0]) if abs(u0[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 = np.cross(u0, tmp); e1 /= np.linalg.norm(e1)
        e2 = np.cross(u0, e1)

        n_tot = (0 if cl["frame"] is None else len(cl["frame"][2])) + \
            len(cl["rotors"]) * len(cl["rot"][2])
        if batch is None:                    # GPU 예산에 맞춰 배치 크기를 **계산**한다
            per = n_tot * 3 * 8 * (14.0 if wavefront != "plane" else 8.0)
            batch = max(1, min(128, int(0.30 * self.budget_mb * 1024 ** 2 / max(per, 1.0))))
        At, u0t, e1t, e2t = self.tg(A), self.tg(u0), self.tg(e1), self.tg(e2)
        if cl["frame"] is not None:
            Pft, Nft, Wft = (self.tg(x) for x in cl["frame"])
        Prt = {d: tuple(self.tg(x) for x in (cl["rot"] if d > 0 else cl["rotm"]))
               for d in (1, -1)}
        out = np.zeros(S, complex)
        s0 = 0
        while s0 < S:
            ph = phis[s0:s0 + batch]
            b = len(ph)
            try:
                Pl, Nl, Wl = [], [], []
                if cl["frame"] is not None:
                    Pl.append(Pft.unsqueeze(0).expand(b, -1, -1))
                    Nl.append(Nft.unsqueeze(0).expand(b, -1, -1))
                    Wl.append(Wft.unsqueeze(0).expand(b, -1))
                for rot in cl["rotors"]:
                    d = 1 if float(rot["dir"]) > 0 else -1
                    Pt_, Nt_, Wt_ = Prt[d]
                    th = math.radians(float(rot["base_ang"])) + float(rot["dir"]) * ph
                    Rt = self.tg(np.stack([_rz(t) for t in th]))
                    Ct = self.tg(np.asarray(rot["center"], float))
                    Pl.append(torch.einsum("bij,pj->bpi", Rt, Pt_) + Ct)
                    Nl.append(torch.einsum("bij,pj->bpi", Rt, Nt_))
                    Wl.append(Wt_.unsqueeze(0).expand(b, -1))
                Pb = torch.cat(Pl, dim=1); Nb = torch.cat(Nl, dim=1); Wb = torch.cat(Wl, dim=1)
                del Pl, Nl, Wl
                if wavefront == "plane":
                    nu = torch.einsum("bpi,i->bp", Nb, u0t)
                    phz = 2.0 * k * torch.einsum("bpi,i->bp", Pb, u0t)
                    amp = torch.clamp(nu, min=0.0) * Wb
                else:
                    D = At.view(1, 1, 3) - Pb
                    r = torch.linalg.norm(D, dim=2)
                    ui = D / r.unsqueeze(2)
                    nu = torch.einsum("bpi,bpi->bp", Nb, ui)
                    amp = torch.clamp(nu, min=0.0) * Wb * (R_t * R_t) / (r * r)
                    phz = -k * (2.0 * r - 2.0 * R_t)
                    del D, r, ui
                if occlude:
                    depth = torch.einsum("bpi,i->bp", Pb, u0t)
                    a1 = torch.einsum("bpi,i->bp", Pb, e1t)
                    a2 = torch.einsum("bpi,i->bp", Pb, e2t)
                    i1 = torch.floor((a1 - a1.min()) / cell_m).to(torch.int64)
                    i2 = torch.floor((a2 - a2.min()) / cell_m).to(torch.int64)
                    n2 = int(i2.max().item()) + 1
                    ncell = (int(i1.max().item()) + 1) * n2
                    gid = (torch.arange(b, device=dev).view(-1, 1) * ncell +
                           (i1 * n2 + i2)).reshape(-1)
                    lit = amp > 0                       # 뒷면은 이미 빠져 있다
                    dd = torch.where(lit, depth, torch.full_like(depth, -1e30)).reshape(-1)
                    top = torch.full((b * ncell,), -1e30, dtype=torch.float64, device=dev)
                    top.scatter_reduce_(0, gid, dd, reduce="amax", include_self=True)
                    near = top[gid].reshape(b, -1)
                    if tol_mode == "adaptive":
                        cosn = torch.clamp(torch.abs(torch.einsum("bpi,i->bp", Nb, u0t)), min=0.10)
                        tol = cell_m / cosn
                        del cosn
                    else:
                        tol = float(tol_cells) * cell_m
                    amp = torch.where(depth >= (near - tol), amp, torch.zeros_like(amp))
                    del depth, a1, a2, i1, i2, gid, lit, dd, top, near, tol
                re = torch.sum(amp * torch.cos(phz), dim=1)
                im = torch.sum(amp * torch.sin(phz), dim=1)
                out[s0:s0 + b] = re.cpu().numpy() + 1j * im.cpu().numpy()
                del Pb, Nb, Wb, nu, amp, phz, re, im
            except torch.OutOfMemoryError:                # 공용 GPU — 죽지 말고 줄여서 계속
                torch.cuda.empty_cache()
                if batch == 1:
                    raise
                batch = max(1, batch // 2)
                continue
            s0 += b
        return out, n_tot


# =========================================================================== #
#  §B  점구름 만들기 — 기반 단(report16_base._worker.clouds_for)과 같은 규약
# =========================================================================== #
FRAME_DIV, BLADE_DIV, BLADE_N = 6.0, 11.0, 26


def _odd(n):
    return int(n) if int(n) % 2 == 1 else int(n) + 1


def mesh_volume(m):
    V = np.asarray(m.v, float); F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)


def disc_mesh(R, thick, zc, target):
    """균일 격자 원판(위·아래 면 + 테두리) — 회전대칭이라 물리적 변조가 정확히 0."""
    from geom import Mesh
    n_seg = _odd(max(9, int(math.ceil(2 * math.pi * R / target))))
    n_ring = max(2, int(math.ceil(R / target)))
    m = Mesh("prop")
    ang = np.arange(n_seg) * (2 * math.pi / n_seg)
    rad = np.linspace(0.0, R, n_ring + 1)
    idx = {}
    for ir, rr in enumerate(rad):
        for ia in range(n_seg):
            for sgn, zz in ((0, zc - thick / 2), (1, zc + thick / 2)):
                idx[(ir, ia, sgn)] = m.add_vertex(rr * math.cos(ang[ia]),
                                                  rr * math.sin(ang[ia]), zz)
    for ir in range(n_ring):
        for ia in range(n_seg):
            ja = (ia + 1) % n_seg
            m.add_quad(idx[(ir, ia, 1)], idx[(ir, ja, 1)], idx[(ir + 1, ja, 1)],
                       idx[(ir + 1, ia, 1)], "prop")
            m.add_quad(idx[(ir, ia, 0)], idx[(ir + 1, ia, 0)], idx[(ir + 1, ja, 0)],
                       idx[(ir, ja, 0)], "prop")
    for ia in range(n_seg):
        ja = (ia + 1) % n_seg
        m.add_quad(idx[(n_ring, ia, 0)], idx[(n_ring, ja, 0)],
                   idx[(n_ring, ja, 1)], idx[(n_ring, ia, 1)], "prop")
    return m


def slab_prop(prop, Pcloud):
    """프로펠러 → 스팬·코드 보존, 두께는 부피가 같아지도록 푼 평판 (고전 회전평판 모델)."""
    from geom import box
    V = np.asarray(prop.v, float)
    lx = float(V[:, 0].max() - V[:, 0].min())
    ly = float(V[:, 1].max() - V[:, 1].min())
    lz = abs(mesh_volume(prop)) / max(lx * ly, 1e-30)
    zc = float(np.mean(Pcloud[:, 2]))
    return box(lx, ly, lz, center=(0.0, 0.0, zc), group="prop")


def clouds_for(key, arm, fc):
    """팔 하나의 점구름. arm ∈ {mesh, slab, disc, sphere}."""
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,
                        drone_gamma_map, build_drone)
    from rcs_po import mesh_to_points
    from geom import uv_sphere
    lam = 299792458.0 / float(fc)
    s = DRONES[key]
    gm = drone_gamma_map(s)
    spac = lam / BLADE_DIV
    if arm == "sphere":
        drone = build_drone(s)
        vol = abs(mesh_volume(drone))
        r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        seg = _odd(max(9, int(math.ceil(2 * math.pi * r_eq / spac))))
        rings = max(3, int(math.ceil(math.pi * r_eq / spac)))
        sph = uv_sphere(r_eq, seg=seg, rings=rings, group="sph")
        Ps, Ns, dAs = mesh_to_points(sph, spac)
        return dict(frame=None, rot=(Ps, Ns, dAs), rotm=(Ps, Ns, dAs),
                    rotors=[dict(center=(0.0, 0.0, 0.0), base_ang=0.0, dir=1)],
                    spec=s, lam=lam, r_eq_m=r_eq)
    frame = build_frame(s)
    Pf, Nf, dAf, wf = mesh_to_points(frame, lam / FRAME_DIV, gamma=gm)
    prop = build_propeller(s, n=BLADE_N)
    if arm == "mesh":
        pa = prop
    elif arm == "slab":
        P0, _, _, _ = mesh_to_points(prop, spac, gamma=gm)
        pa = slab_prop(prop, P0)
    elif arm == "disc":
        V = np.asarray(prop.v, float)
        th = float(V[:, 2].max() - V[:, 2].min())
        zc = float(0.5 * (V[:, 2].max() + V[:, 2].min()))
        pa = disc_mesh(float(s.prop_dia_mm) / 2000.0, th, zc, spac)
    else:
        raise ValueError(arm)
    Pp, Np_, dAp, wp = mesh_to_points(pa, spac, gamma=gm)
    M = np.array([1.0, -1.0, 1.0])
    if arm == "mesh":
        rotm = (Pp * M, Np_ * M, dAp * wp)         # 반대회전 로터 = 거울상 프롭
    else:
        rotm = (Pp, Np_, dAp * wp)                 # 회전대칭/대칭 프리미티브는 거울=자기자신
    return dict(frame=(Pf, Nf, dAf * wf), rot=(Pp, Np_, dAp * wp), rotm=rotm,
                rotors=rotor_layout(s), spec=s, lam=lam)


# =========================================================================== #
#                                  본문
# =========================================================================== #
def main():
    from report16_base import derive_protocol, md_metrics16, EL_DEG, RANGE_M, C0
    from drones import DRONES
    t_all = time.time()
    J = {}
    J["meta"] = dict(
        report="report16_verify_kernel",
        producer="benchmark/report16_verify_kernel.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        lens_ko="적대검증 — 커널 신뢰도. 기본 입장은 «이 결론은 이르다».",
        crude_warning_ko=("⭐ 이 파일이 **새로 만든** 숫자는 전부 crude(거친 추정)다. "
                          "깊이버퍼 그늘은 광선추적이 아니고, 회절·다중반사·편파는 여전히 없다. "
                          "그래도 «그늘이 있으면 지표가 얼마나 움직이나» 의 크기 자릿수는 준다."),
        forbidden_untouched=["outputs/report15_*", "benchmark/report15_*",
                             "src/make_report0N_*.py", "report0N_*.ipynb",
                             "src/drones.py (읽기 전용 import)",
                             "src/drone_cad.py (미접촉)"])

    # ── §0 출처 ─────────────────────────────────────────────────────────── #
    inputs = {}
    for rel in ("outputs/report16_base.json", "outputs/report16_base_tables.npz",
                "outputs/report16_metric_mesh_full.json",
                "outputs/report16_metric_mesh_half_tri.json",
                "outputs/report16_metric_cube_eqvol.json",
                "outputs/report16_metric_box_bbox.json",
                "outputs/report16_metric_sphere_eqvol.json",
                "outputs/report16_metric_mesh_no_rotor.json",
                "outputs/report00_po_case.json"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            inputs[rel] = dict(sha256_12=sha(p), mtime=time.strftime(
                "%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p))))
    J["provenance"] = dict(inputs=inputs)

    B = json.load(open(os.path.join(ROOT, "outputs", "report16_base.json")))
    TB = np.load(os.path.join(ROOT, "outputs", "report16_base_tables.npz"))
    pov = B["po_validity_warning"]

    # ── §1 왜 이 렌즈인가 — 무릎까지의 거리를 **계산**한다 ─────────────── #
    lam_main = C0 / B["protocol"]["fc_main_hz"]
    blade_w_m = pov["knee_a_over_lambda"] * C0 / (pov["blade_knee_ghz"] * 1e9)
    J["why_this_lens"] = dict(
        blade_width_m=blade_w_m,
        blade_width_over_lambda_main=blade_w_m / lam_main,
        po_knee_a_over_lambda=pov["knee_a_over_lambda"],
        shortfall_x=pov["knee_a_over_lambda"] / (blade_w_m / lam_main),
        blade_knee_ghz=pov["blade_knee_ghz"], body_knee_ghz=pov["body_knee_ghz"],
        statement_ko=("마이크로도플러를 만드는 부품(날개, 폭 %.2f mm)은 3.5 GHz 에서 파장의 "
                      "%.3f 배다. PO 가 1 dB 안으로 맞는 문턱 %.3f λ 에 **%.2f 배 모자란다**. "
                      "동체(문턱 %.2f GHz)는 통과하지만 날개는 통과하지 못한다."
                      % (blade_w_m * 1000, blade_w_m / lam_main, pov["knee_a_over_lambda"],
                         pov["knee_a_over_lambda"] / (blade_w_m / lam_main), pov["body_knee_ghz"])))

    # ── §2 게이트 — 내 커널이 기반 표를 재현하는가(가림 끈 상태) ───────── #
    K = Kernel()
    gate = dict(device=str(K.dev), gpu=K.picked, budget_mb=K.budget_mb, per_case={})
    worst = 0.0
    for key in ("mini2", "matrice4e", "mavic4pro"):
        cl = clouds_for(key, "mesh", B["protocol"]["fc_main_hz"])
        s = DRONES[key]
        proto = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades,
                                B["protocol"]["fc_main_hz"])
        for wfr in ("spherical", "plane"):
            ref = TB[f"main__G_0804__{key}__mesh__{wfr}"]
            errs = []
            for ia in range(0, 24, 6):                 # 4 방위 표본
                E, _ = K.table(cl, B["protocol"]["fc_main_hz"], ia * 15.0, proto,
                               occlude=False, wavefront=wfr)
                errs.append(float(np.abs(E - ref[ia]).max() / max(np.abs(ref[ia]).max(), 1e-300)))
            gate["per_case"][f"{key}|{wfr}"] = max(errs)
            worst = max(worst, max(errs))
    gate["max_rel_diff"] = worst
    gate["tolerance"] = 1e-9
    gate["verdict"] = "PASS" if worst < 1e-9 else "FAIL"
    gate["what_ko"] = ("이 파일은 기반 단과 **다른 방식**으로 같은 계산을 한다 — 기반은 로터마다 "
                       "안테나를 반대로 돌리고, 여기서는 모든 점을 전역좌표로 옮겨 한 판에 올린다"
                       "(그래야 서로 가릴 수 있다). 가림을 끄면 두 방식이 같은 답을 내야 한다. "
                       "여기서 틀리면 아래 숫자는 전부 무효다.")
    J["independent_kernel_gate"] = gate
    print(f"[gate] max_rel={worst:.2e} {gate['verdict']}", flush=True)

    # ── §3 T1 가림 — 3.5 GHz, 24 방위 ─────────────────────────────────── #
    MET = ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
           "width_ratio", "dc_ac_db", "sigma_eq_mean_dbsm")
    fc0 = B["protocol"]["fc_main_hz"]
    az24 = np.arange(24) * 15.0
    occ = dict(band_hz=fc0, n_az=24, wavefront="spherical",
               cell_m_headline=CELL_CANDIDATES_M[1], tol_mode_headline="adaptive")
    tables = {}          # (key, arm, occ_on) -> (24, S) 표
    protos = {}
    for key in ("mini2", "matrice4e"):
        s = DRONES[key]
        protos[key] = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc0)
        for arm in ("mesh", "slab", "disc", "sphere"):
            cl = clouds_for(key, arm, fc0)
            for on in (False, True):
                T = np.zeros((24, protos[key]["n_phase"]), complex)
                for ia, az in enumerate(az24):
                    T[ia], npts = K.table(cl, fc0, az, protos[key], occlude=on,
                                          cell_m=CELL_CANDIDATES_M[1], tol_mode="adaptive")
                tables[(key, arm, on)] = T
            print(f"  [T1] {key} {arm} done ({npts} pts)", flush=True)

    def met_per_az(T, key):
        s = DRONES[key]
        return [md_metrics16(T[ia], protos[key], s.prop_blades) for ia in range(len(T))]

    occ["convexity_control"] = {}
    occ["per_arm"] = {}
    occ["shift_by_occlusion"] = {}
    for key in ("mini2", "matrice4e"):
        for arm in ("mesh", "slab", "disc", "sphere"):
            m0 = met_per_az(tables[(key, arm, False)], key)
            m1 = met_per_az(tables[(key, arm, True)], key)
            occ["per_arm"][f"{key}|{arm}|no_occ"] = {k: summar([m[k] for m in m0]) for k in MET}
            occ["per_arm"][f"{key}|{arm}|occ"] = {k: summar([m[k] for m in m1]) for k in MET}
            occ["shift_by_occlusion"][f"{key}|{arm}"] = {
                k: summar([m1[i][k] - m0[i][k] for i in range(len(m0))]) for k in MET}
            if arm == "sphere":
                # 볼록체는 앞면끼리 서로 못 가린다 → 이동이 0 이어야 한다(내 그늘 코드의 자기검사)
                d = max(abs(m1[i][k] - m0[i][k]) for i in range(len(m0))
                        for k in ("flash_contrast_db", "dc_ac_db", "sigma_eq_mean_dbsm")
                        if np.isfinite(m1[i][k]) and np.isfinite(m0[i][k]))
                occ["convexity_control"][key] = dict(
                    max_abs_metric_shift_on_convex_sphere=float(d),
                    verdict="PASS" if d < 0.5 else "SUSPECT",
                    what_ko=("등가부피 구는 볼록체라 앞면끼리 서로 가릴 수 없다 — 진짜 답은 "
                             "«이동 0» 이다. 여기서 큰 값이 나오면 내 깊이버퍼가 «자기 자신을 "
                             "그늘로 잘못 판정» 하고 있다는 뜻이므로, 아래 이동량은 그만큼 부풀려진 것이다."))

    # 라운드의 헤드라인 주장(P1: 평판이 CAD 메쉬보다 하모닉이 풍부하다)이 그늘 아래서도 사나
    occ["headline_gap_slab_minus_mesh"] = {}
    for key in ("mini2", "matrice4e"):
        row = {}
        for on, nm in ((False, "no_occ"), (True, "occ")):
            ms = met_per_az(tables[(key, "mesh", on)], key)
            sl = met_per_az(tables[(key, "slab", on)], key)
            row[nm] = {k: summar([sl[i][k] - ms[i][k] for i in range(24)]) for k in MET}
            row[nm + "_frac_positive"] = {
                k: float(np.mean([(sl[i][k] - ms[i][k]) > 0 for i in range(24)])) for k in MET}
        row["sign_flipped"] = {k: bool(np.sign(row["no_occ"][k]["mean"]) !=
                                       np.sign(row["occ"][k]["mean"])) for k in MET}
        row["gap_change_over_gap"] = {
            k: float(abs(row["occ"][k]["mean"] - row["no_occ"][k]["mean"]) /
                     max(abs(row["no_occ"][k]["mean"]), 1e-12)) for k in MET}
        occ["headline_gap_slab_minus_mesh"][key] = row

    # 깊이버퍼 칸 크기·여유 민감도 (방위 4점만 — 거친 민감도)
    sens = {}
    for key in ("mini2",):
        cl = clouds_for(key, "mesh", fc0)
        base_m = met_per_az(tables[(key, "mesh", False)], key)
        for cell in CELL_CANDIDATES_M:
            for tm in TOL_MODES:
                d = []
                for ia in range(0, 24, 6):
                    E, _ = K.table(cl, fc0, ia * 15.0, protos[key], occlude=True,
                                   cell_m=cell, tol_mode=tm)
                    m = md_metrics16(E, protos[key], DRONES[key].prop_blades)
                    d.append({k: m[k] - base_m[ia][k] for k in MET})
                sens[f"{key}|cell{cell*1000:g}mm|{tm}"] = {
                    k: summar([x[k] for x in d]) for k in MET}
    occ["cell_and_tolerance_sensitivity"] = sens
    occ["method_ko"] = ("깊이버퍼(z-buffer) 그늘. 시선 수직면을 cell 크기 칸으로 나눠 칸마다 "
                        "레이더에 가장 가까운 면만 남긴다. 여유는 면의 기울기로 나눠 준다"
                        "(adaptive) — 비스듬한 면이 자기 자신을 그늘로 잘못 지우지 않게.")
    occ["crude"] = True
    J["T1_occlusion"] = occ
    print("[T1] occlusion done", flush=True)

    # ── §4 T2 주파수 훑기 — PO 무릎을 넘으면 결론이 바뀌는가 ──────────── #
    from report16_base import field_static, field_rotor, look_and_antenna
    torch = K.torch
    sweep = dict(freqs_ghz=list(SWEEP_GHZ), n_az=N_AZ_SWEEP, wavefront="spherical",
                 knee_ghz=pov["blade_knee_ghz"], rows={}, crude=True)
    az_s = np.arange(N_AZ_SWEEP) * (360.0 / N_AZ_SWEEP)
    for key in ("mini2", "matrice4e"):
        s = DRONES[key]
        for gh in SWEEP_GHZ:
            fc = gh * 1e9
            proto = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
            k_wav = 2.0 * math.pi / (C0 / fc)
            phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
            mm = {}
            for arm in ("mesh", "slab"):
                cl = clouds_for(key, arm, fc)
                T = np.zeros((len(az_s), proto["n_phase"]), complex)
                for ia, az in enumerate(az_s):
                    u, A, R_t = look_and_antenna(az, EL_DEG, RANGE_M)
                    Pf, Nf, Wf = cl["frame"]
                    Ef = field_static(torch, K.dev, Pf, Nf, Wf, k_wav, A, R_t, "spherical")
                    tot = np.full(proto["n_phase"], Ef, complex)
                    for rot in cl["rotors"]:
                        d = float(rot["dir"])
                        P, N, W = cl["rot"] if d > 0 else cl["rotm"]
                        tot += field_rotor(torch, K.dev, P, N, W, k_wav, A, R_t, rot["center"],
                                           math.radians(float(rot["base_ang"])), d, phis,
                                           "spherical")
                    T[ia] = tot
                mm[arm] = [md_metrics16(T[ia], proto, s.prop_blades) for ia in range(len(az_s))]
                sweep["rows"][f"{key}|{gh}|{arm}"] = dict(
                    n_pts_frame=len(Wf), n_pts_blade=len(cl["rot"][2]),
                    n_phase=proto["n_phase"], beta=proto["beta"],
                    blade_w_over_lambda=blade_w_m / (C0 / fc),
                    above_po_knee=bool(blade_w_m / (C0 / fc) >= pov["knee_a_over_lambda"]),
                    **{k: summar([m[k] for m in mm[arm]]) for k in MET})
            sweep["rows"][f"{key}|{gh}|gap_slab_minus_mesh"] = {
                k: summar([mm["slab"][i][k] - mm["mesh"][i][k] for i in range(len(az_s))])
                for k in MET}
            sweep["rows"][f"{key}|{gh}|gap_slab_minus_mesh"]["frac_positive"] = {
                k: float(np.mean([(mm["slab"][i][k] - mm["mesh"][i][k]) > 0
                                  for i in range(len(az_s))])) for k in MET}
            print(f"  [T2] {key} {gh} GHz done", flush=True)
    # 결론이 대역을 넘어 살아남는가
    surv = {}
    for key in ("mini2", "matrice4e"):
        for k in ("n_eff_orders", "flash_contrast_db", "width_ratio", "dc_ac_db"):
            sg = [np.sign(sweep["rows"][f"{key}|{gh}|gap_slab_minus_mesh"][k]["mean"])
                  for gh in SWEEP_GHZ]
            surv[f"{key}|{k}"] = dict(
                sign_by_freq={f"{gh}": float(x) for gh, x in zip(SWEEP_GHZ, sg)},
                all_same=bool(len(set(sg)) == 1),
                magnitude_by_freq={f"{gh}": sweep["rows"][f"{key}|{gh}|gap_slab_minus_mesh"][k]["mean"]
                                   for gh in SWEEP_GHZ})
    sweep["conclusion_survives_across_band"] = surv
    J["T2_frequency_sweep"] = sweep

    # ── §5 T2b 무릎 대역에서 가림 ─────────────────────────────────────── #
    fchi = B["protocol"]["fc_po_knee_hz"]
    hi = dict(band_hz=fchi, n_az=N_AZ_OCC_HI, crude=True, rows={})
    az_h = np.arange(N_AZ_OCC_HI) * (360.0 / N_AZ_OCC_HI)
    for key in ("mini2", "matrice4e"):
        s = DRONES[key]
        proto = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fchi)
        for arm in ("mesh", "slab"):
            cl = clouds_for(key, arm, fchi)
            mm = {}
            for on, nm in ((False, "no_occ"), (True, "occ")):
                M = []
                for az in az_h:
                    E, npts = K.table(cl, fchi, az, proto, occlude=on,
                                      cell_m=CELL_CANDIDATES_M[0], tol_mode="adaptive")
                    M.append(md_metrics16(E, proto, s.prop_blades))
                mm[nm] = M
                hi["rows"][f"{key}|{arm}|{nm}"] = dict(
                    n_pts=int(npts), n_phase=proto["n_phase"],
                    **{k: summar([m[k] for m in M]) for k in MET})
            hi["rows"][f"{key}|{arm}|shift"] = {
                k: summar([mm["occ"][i][k] - mm["no_occ"][i][k]
                           for i in range(len(az_h))]) for k in MET}
            print(f"  [T2b] hi {key} {arm} done", flush=True)
    for key in ("mini2", "matrice4e"):
        for nm in ("no_occ", "occ"):
            hi["rows"][f"{key}|gap_slab_minus_mesh|{nm}"] = {
                k: hi["rows"][f"{key}|slab|{nm}"][k]["mean"] -
                   hi["rows"][f"{key}|mesh|{nm}"][k]["mean"] for k in MET}
    J["T2b_occlusion_at_knee"] = hi

    # ── §6 T3 크기 견주기 ─────────────────────────────────────────────── #
    led = dict(what_ko=("이 라운드가 주장하는 효과의 크기와, 커널·메쉬가 흔들릴 때의 크기를 "
                        "같은 지표 위에 나란히 놓는다. 흔들림이 효과보다 크면 그 결론은 이르다."))
    # (a) 메쉬 세대 (07-27 → 08-04) — 통제된 A/B (같은 커널)
    gen = B["findings"]["q1_did_the_mesh_change_the_micro_doppler"]
    led["mesh_generation_0727_to_0804"] = dict(
        waveform_corr_matrice4e=gen["matrice4e_pattern_corr"]["matrice4e|G_0727->G_0804"],
        waveform_corr_mavic4pro=gen["control_mavic4pro"]["mavic4pro|G_0727->G_0804"],
        metric_delta=gen["matrice4e_metric_delta"]["matrice4e|G_0727->G_0804"])
    # (b) 07-29 아카이브(SBR=가림 있음) vs 새 PO — 같은 기체끼리만
    arch = B["archive_2026_07_29"]["drones"]
    newv = B["archive_2026_07_29"]["same_gauge_on_new_run"]["values"]
    eng = {}
    for key in ("mavic4pro", "matrice4e"):
        if key in arch and key in newv:
            a = arch[key]["legacy"]["dc_ac_db"]
            b = newv[key]["dc_ac_db"]["mean"]
            # SBR 대역밖 잡음을 걷어낸 보정치 — 대역 안 몫만 AC 로 인정하면 dc_ac 는 이만큼 오른다
            fr = arch[key]["in_band"]["in_band_ac_frac"]
            eng[key] = dict(sbr_0729_dc_ac_db=a, po_new_dc_ac_db=b, gap_db=b - a,
                            sbr_in_band_ac_frac=fr,
                            sbr_dc_ac_db_inband_corrected=a - 10 * math.log10(fr),
                            gap_db_after_correction=b - (a - 10 * math.log10(fr)))
    led["engine_gap_sbr_vs_po_dc_ac"] = dict(
        values=eng,
        caveat_ko=("⚠ 통제된 A/B 가 아니다 — 엔진(SBR↔PO)·메쉬·규약(주기 180° 근사·평면파)이 "
                   "모두 다르다. 그래도 «가림이 있는 계산과 없는 계산이 동체:날개 비에서 "
                   "얼마나 벌어지나» 의 자릿수는 보여 준다. 대역밖 잡음 보정을 해도 갭은 거의 안 준다."))
    # (c) 라운드가 주장하는 효과 크기 (기존 산출물에서 읽는다)
    HT = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_mesh_half_tri.json")))
    CB = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_box_bbox.json")))
    claim = {}
    g = HT["grading_independent"]["P1_primitive_richness_verdict_survives"]["actual"]
    for key in g:
        claim[f"P1_slab_minus_mesh_n_eff|{key}"] = g[key]["mean"]
    for key in ("mini2", "matrice4e"):
        kk = f"main|{key}|cube_eqvol - mesh"
        if kk in CB["paired_vs_mesh"]:
            claim[f"cube_minus_mesh_flash_db|{key}"] = CB["paired_vs_mesh"][kk]["flash_contrast_db"]["paired_mean"]
            claim[f"cube_minus_mesh_n_eff|{key}"] = CB["paired_vs_mesh"][kk]["n_eff_orders"]["paired_mean"]
    led["round_claimed_effect_sizes"] = claim
    # (d) 흔들림 ÷ 효과 — 내 가림 이동량 대 라운드 효과
    ratio = {}
    for key in ("mini2", "matrice4e"):
        sh = J["T1_occlusion"]["shift_by_occlusion"][f"{key}|mesh"]
        for mk, ck in (("n_eff_orders", f"P1_slab_minus_mesh_n_eff|{key}"),
                       ("n_eff_orders", f"cube_minus_mesh_n_eff|{key}"),
                       ("flash_contrast_db", f"cube_minus_mesh_flash_db|{key}")):
            if ck in claim:
                ratio[f"{key}|occ_shift[{mk}] / |{ck}|"] = float(
                    abs(sh[mk]["mean"]) / max(abs(claim[ck]), 1e-12))
    ratio_gen = {}
    md = led["mesh_generation_0727_to_0804"]["metric_delta"]
    for ck, mk in (("cube_minus_mesh_flash_db|matrice4e", "flash_contrast_db"),
                   ("cube_minus_mesh_n_eff|matrice4e", "n_eff_orders"),
                   ("P1_slab_minus_mesh_n_eff|matrice4e", "n_eff_orders")):
        if ck in claim:
            ratio_gen[f"mesh_gen_delta[{mk}] / |{ck}|"] = float(
                abs(md[mk]["delta"]) / max(abs(claim[ck]), 1e-12))
    led["shake_over_effect"] = dict(occlusion=ratio, mesh_generation=ratio_gen,
                                    read_ko="1.0 을 넘으면 «흔들림이 효과보다 크다» — 그 결론은 이르다.")
    J["T3_magnitude_ledger"] = led
    # 비싼 §2~§6 을 잃지 않도록 여기서 한 번 떨군다 (뒤 단계가 넘어져도 다시 안 돌린다)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print("  [cache] 비싼 부분 저장 완료", flush=True)

    # ── §7 T4 삼각형 절반 단 감사 ─────────────────────────────────────── #
    r3 = [x for x in HT["reasons_to_distrust"] if x["id"].startswith("R3")]
    t4 = dict(
        grading_main_band={k: v.get("verdict") for k, v in HT["grading_independent"].items()
                           if isinstance(v, dict) and not k.startswith("_")},
        agreement_with_rung=HT.get("grading_agreement_with_rung", {}),
        hi_vs_main_amplification=(r3[0]["evidence"] if r3 else {}),
        what_ko=("삼각형 절반 단은 주 대역(3.5 GHz)에서 9/9 PASS 였다. 그러나 같은 단이 "
                 "무릎 대역에서 다시 재 보니 같은 «절반 메쉬» 가 지표를 훨씬 크게 흔들었다. "
                 "판정 자체가 뒤집힌 것은 아니지만, 그 판정이 **대역에 딸린 성질**임이 드러났다."))
    if r3:
        hi_m = r3[0]["evidence"]["hi_band_half_minus_full_n_eff"]["mean"]
        lo_m = r3[0]["evidence"]["main_band_half_minus_full_n_eff"]["mean"]
        t4["amplification_x"] = float(abs(hi_m) / max(abs(lo_m), 1e-12))
        # 무릎 대역에서 절반메쉬 흔들림이 라운드 효과(P1 갭)를 넘는가
        p1 = HT["grading_independent"]["P1_primitive_richness_verdict_survives"]["actual"]
        t4["hi_band_half_mesh_shift_over_P1_gap"] = {
            key: float(abs(hi_m) / max(abs(p1[key]["mean"]), 1e-12)) for key in p1}
        t4["verdict_flipped_at_hi_band"] = None      # 아래에서 내 훑기로 판정
    J["T4_half_triangle_audit"] = t4

    # ── §8 판정 ───────────────────────────────────────────────────────── #
    def worst_ratio(d):
        v = [x for x in d.values() if np.isfinite(x)]
        return float(max(v)) if v else float("nan")

    r_occ = worst_ratio(J["T3_magnitude_ledger"]["shake_over_effect"]["occlusion"])
    r_gen = worst_ratio(J["T3_magnitude_ledger"]["shake_over_effect"]["mesh_generation"])
    all_same = all(v["all_same"] for v in J["T2_frequency_sweep"]
                   ["conclusion_survives_across_band"].values())
    conv_ok = all(v["verdict"] == "PASS" for v in J["T1_occlusion"]["convexity_control"].values())
    J["verdict"] = dict(
        gate=gate["verdict"],
        worst_occlusion_shake_over_effect=r_occ,
        worst_mesh_generation_shake_over_effect=r_gen,
        sweep_sign_stable_across_band=all_same,
        convexity_control=conv_ok)
    J["seconds"] = float(time.time() - t_all)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print("→", OUT_JSON, f"[{J['seconds']:.1f}s]")
    return J


# =========================================================================== #
#  §9  마무리 — 기존 산출물만 읽어서 «대역 넘김 감사 + 결함표 + 판정» 을 덧붙인다
#      (새 전자기 계산 없음. 비싼 §2~§6 을 다시 돌리지 않으려고 분리했다.)
# =========================================================================== #
def _sphere_po_error():
    """구 단이 이미 잰 «PO 그 자체의 모형오차» — 커널 코드가 맞아도 남는 오차."""
    p = os.path.join(ROOT, "outputs", "report16_metric_sphere_eqvol.json")
    if not os.path.exists(p):
        return {}
    S = json.load(open(p))
    for it in S.get("distrust", {}).get("items", []):
        if it.get("id") == "D3":
            return dict(it["evidence"], source="report16_metric_sphere_eqvol.json :: distrust D3",
                        read_ko=("커널의 «수치» 는 해석 PO 와 0.12 dB 안으로 맞지만, 해석 PO 와 "
                                 "정확해(Mie)는 등가부피 구에서 2.93 dB, 작은 구에서 6.8 dB 어긋난다. "
                                 "즉 코드가 맞는 것과 물리가 맞는 것은 다른 문제다."))
    return {}


def finalize():
    J = json.load(open(OUT_JSON))

    # ── 9.1 대역 넘김 감사: 같은 대조를 3.5 / 15.86 GHz 에서 각각 채점 ──── #
    CB = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_box_bbox.json")))
    pv = CB["paired_vs_mesh"]
    keys = sorted({k.split("|", 1)[1] for k in pv if k.startswith("main|")} &
                  {k.split("|", 1)[1] for k in pv if k.startswith("hi|")})
    MET = ("flash_contrast_db", "n_eff_orders", "order_p90", "width_ratio")
    flips, tot, nflip = {}, 0, 0
    for kk in keys:
        row = {}
        for m in MET:
            a = pv[f"main|{kk}"].get(m, {}).get("paired_mean")
            b = pv[f"hi|{kk}"].get(m, {}).get("paired_mean")
            if a is None or b is None:
                continue
            fl = bool(np.sign(a) != np.sign(b) and abs(a) > 0 and abs(b) > 0)
            row[m] = dict(main=a, hi=b, sign_flip=fl,
                          hi_over_main=float(abs(b) / max(abs(a), 1e-12)))
            tot += 1
            nflip += int(fl)
        flips[kk] = row
    J["T5_cross_band_audit_of_existing_artifacts"] = dict(
        source="outputs/report16_metric_box_bbox.json :: paired_vs_mesh (main| vs hi|)",
        n_comparisons=tot, n_sign_flips=nflip,
        flip_rate=float(nflip / max(tot, 1)), per_arm=flips,
        what_ko=("같은 «프리미티브 − 메쉬» 대조를 생산 대역(3.5 GHz)과 PO 무릎(15.86 GHz)에서 "
                 "각각 채점했다. 부호가 뒤집히면 그 대조의 방향은 형상이 아니라 **대역**이 정한 것이다."))

    # ── 9.2 다른 단이 이미 정량화한 가림 결함 ─────────────────────────── #
    MF = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_mesh_full.json")))
    NR = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_mesh_no_rotor.json")))
    occ_prior = dict(
        mesh_full_zbuffer_area=MF["reasons_to_doubt_detail"]["no_occlusion"],
        no_rotor_amplitude_weight={x["id"]: x for x in NR["reasons_to_distrust"]
                                   if x["id"] == "occlusion_flaw_is_one_sided"},
        band_flip_already_found={x["id"]: x for x in NR["reasons_to_distrust"]
                                 if x["id"] == "one_headline_sign_flips_with_band"})
    J["T6_prior_stage_admissions"] = dict(
        detail=occ_prior,
        what_ko=("앞 단들이 스스로 적어 둔 결함 중 이 렌즈와 겹치는 것. 이들은 «넓이가 몇 % "
                 "가려지나» 까지만 쟀고, **그 가림이 지표를 얼마나 옮기나** 는 재지 않았다 — "
                 "그것을 이 파일의 T1 이 처음으로 잰다."))

    # ── 9.2b ⭐ 같은 문턱을 무릎 대역에 대 보면 판정이 뒤집히는가 ──────── #
    HT = json.load(open(os.path.join(ROOT, "outputs", "report16_metric_mesh_half_tri.json")))
    gi = HT["grading_independent"]
    pmain, phi = HT["paired_spherical"], HT["hi_band"]["paired"]
    regr = {}
    for pid, met, thr_key in (("P2_half_mesh_moves_n_eff_little", "n_eff_orders", "abs_mean_le"),
                              ("P3_half_mesh_moves_flash_little", "flash_contrast_db", "abs_mean_le"),
                              ("P4_half_mesh_moves_dc_ac_little", "dc_ac_db", "abs_mean_le")):
        thr = float(gi[pid]["thresholds"][thr_key])
        row = dict(threshold=thr, metric=met, main={}, hi={})
        vmain, vhi = [], []
        for key in ("mini2", "matrice4e"):
            kk = f"{key}|mesh_half_tri - mesh"
            if kk in pmain and met in pmain[kk]:
                row["main"][key] = pmain[kk][met]["mean"]; vmain.append(abs(pmain[kk][met]["mean"]))
            if kk in phi and met in phi[kk]:
                row["hi"][key] = phi[kk][met]["mean"]; vhi.append(abs(phi[kk][met]["mean"]))
        row["verdict_main"] = "PASS" if max(vmain) <= thr else "FAIL"
        row["verdict_hi"] = "PASS" if max(vhi) <= thr else "FAIL"
        row["flipped"] = bool(row["verdict_main"] != row["verdict_hi"])
        row["hi_over_main_worst"] = float(max(vhi) / max(max(vmain), 1e-12))
        regr[pid] = row
    J["T4b_same_threshold_at_the_knee"] = dict(
        gates=regr,
        n_flipped=int(sum(v["flipped"] for v in regr.values())),
        method_ko=("앞 단이 3.5 GHz 에서 쓴 **그 문턱 그대로** 를, 앞 단이 이미 계산해 둔 "
                   "15.86 GHz(PO 무릎) 짝지은 값에 대 본다. 문턱을 사후에 바꾸지 않았다."),
        meaning_ko=("⭐ 여기서 뒤집히는 항목은 «메쉬 해상도가 안 중요하다» 를 **커널이 유효한 "
                    "대역에서는 말할 수 없다** 는 뜻이다. 3.5 GHz 의 PASS 는 형상의 성질이 아니라 "
                    "파장이 그 형상을 못 보는 데서 온 것일 수 있다."))

    # ⭐⭐ 헤드라인 대조가 «가림» 만으로 부호가 뒤집히는가 — 두 대역 네 구석 전부
    hg = J["T1_occlusion"]["headline_gap_slab_minus_mesh"]
    kg = J["T2b_occlusion_at_knee"]["rows"]
    corners = {}
    for key in hg:
        corners[f"3.5GHz|{key}"] = dict(
            no_occ=hg[key]["no_occ"]["n_eff_orders"]["mean"],
            occ=hg[key]["occ"]["n_eff_orders"]["mean"],
            frac_positive_occ=hg[key]["occ_frac_positive"]["n_eff_orders"],
            sign_flip=hg[key]["sign_flipped"]["n_eff_orders"])
    for key in ("mini2", "matrice4e"):
        a = kg.get(f"{key}|gap_slab_minus_mesh|no_occ", {}).get("n_eff_orders")
        b = kg.get(f"{key}|gap_slab_minus_mesh|occ", {}).get("n_eff_orders")
        if a is not None and b is not None:
            corners[f"15.86GHz|{key}"] = dict(no_occ=a, occ=b,
                                              sign_flip=bool(np.sign(a) != np.sign(b)))
    n_flip = sum(int(v["sign_flip"]) for v in corners.values())
    J["headline_contrast_under_occlusion"] = dict(
        metric="n_eff_orders, gap = slab primitive − CAD mesh",
        corners=corners, n_corners=len(corners), n_sign_flips=n_flip, crude=True,
        statement_ko=(
            "⭐⭐ 이 라운드에서 가장 많이 인용될 대조 — «기하 프리미티브(평판)가 우리 CAD 메쉬보다 "
            "하모닉이 풍부하다» — 는 **가림을 넣는 것만으로 부호가 뒤집힌다**. 두 대역 × 두 기체 "
            "네 구석 전부에서 뒤집혔다. 방향도 물리적으로 말이 된다: 그늘은 CAD 메쉬에 «날개가 "
            "동체 뒤로 사라졌다 나타나는» 새 변조를 **더하고**(n_eff +1.2~+10.1), 평판에서는 "
            "정반사 플래시를 **잘라 낸다**(n_eff −0.2~−31.1). 즉 이 대조는 형상의 성질이 아니라 "
            "**그늘을 모형에 넣었는가**의 성질이다."),
        caveat_ko=("⭐ crude. 내 깊이버퍼는 회전대칭 널에 66~74 dB 의 가짜 변조를 주입하고, "
                   "메쉬의 신호는 그 바닥보다 24~27 dB 위에 있을 뿐이다(T1b.C2). 평판 팔의 주입 "
                   "바닥은 따로 재지 않았다. 그래서 «뒤집힌다» 를 확정으로 읽으면 안 되고, "
                   "«부호가 그늘 모형에 좌우된다» 로 읽어야 한다 — 그 자체가 결론을 못 내리게 하는 사실이다."))

    # ── 9.3 결함표 ────────────────────────────────────────────────────── #
    T1 = J["T1_occlusion"]
    T2 = J["T2_frequency_sweep"]
    LED = J["T3_magnitude_ledger"]
    sh = {k: T1["shift_by_occlusion"][k] for k in T1["shift_by_occlusion"] if "|mesh" in k}
    worst_occ = max(abs(v["flash_contrast_db"]["mean"]) for v in sh.values())
    worst_occ_neff = max(abs(v["n_eff_orders"]["mean"]) for v in sh.values())
    worst_ratio = max([x for x in LED["shake_over_effect"]["occlusion"].values()
                       if np.isfinite(x)] or [float("nan")])
    unstable = [k for k, v in T2["conclusion_survives_across_band"].items() if not v["all_same"]]

    D = []
    D.append(dict(
        id="K1", severity="critical",
        where="benchmark/report16_base.py :: field_static/field_rotor (가림 없음) — 라운드 전 단계가 상속",
        title_ko="가림이 없다. 넣어 보니 지표가 라운드가 주장하는 효과와 **같은 크기**로 움직인다",
        numbers=dict(flash_shift_db=sh, worst_shift_over_claimed_effect=worst_ratio,
                     prior_stage_hidden_amplitude_frac=(
                         occ_prior["no_rotor_amplitude_weight"]
                         .get("occlusion_flaw_is_one_sided", {}).get("quantified"))),
        why_ko=("우리 기체는 팔·짐벌·동체가 서로를 가리는 오목한 물체다. 앞 단 추정으로 조명된 "
                "진폭의 **절반가량**이 실제로는 안 보이는 면에 실려 있다. 프리미티브(구·정육면체·상자)는 "
                "볼록해서 이 오차가 정확히 0 이다 — 즉 결함이 **한쪽에만** 걸린 채로 «프리미티브가 "
                "메쉬보다 낫다/못하다» 를 겨루고 있다."),
        crude_ko="⭐ 내 그늘은 깊이버퍼 근사이지 광선추적이 아니다. 부호와 자릿수만 읽어라.",
        what_would_settle_ko="진짜 SBR 가림(광선추적) 으로 같은 표를 다시 만들고, 프리미티브 팔에도 같은 처리를 한다."))
    D.append(dict(
        id="K1b", severity="critical",
        where="라운드 헤드라인 대조 (report16_metric_mesh_half_tri.json :: P1) — 근본 원인은 base 커널의 가림 부재",
        title_ko=("⭐⭐ 헤드라인 대조 «프리미티브가 CAD 메쉬보다 하모닉이 풍부하다» 가 "
                  "**가림을 넣는 것만으로 부호가 뒤집힌다** (%d/%d 구석)"
                  % (J["headline_contrast_under_occlusion"]["n_sign_flips"],
                     J["headline_contrast_under_occlusion"]["n_corners"])),
        numbers=J["headline_contrast_under_occlusion"],
        why_ko=("그늘은 두 팔에 **반대 방향**으로 작용한다. CAD 메쉬에서는 «날개가 동체 뒤로 "
                "사라졌다 다시 나타나는» 새 변조를 더하고, 평판에서는 정반사 플래시를 잘라 낸다. "
                "그래서 결론의 방향이 형상이 아니라 모형 선택에 매인다. K1(가림 없음)이 "
                "«오차가 있다» 였다면, 이것은 «그 오차가 결론의 부호를 바꾼다» 다."),
        crude_ko="⭐ crude. 널 주입 바닥 대비 24~27 dB 여유뿐이고 평판 팔의 주입 바닥은 미측정.",
        what_would_settle_ko=("SBR 광선추적 가림으로 mesh·slab·cube·sphere 네 팔을 **똑같이** "
                              "다시 돌린다. 그늘을 양쪽에 공평하게 넣기 전에는 이 대조를 인용할 수 없다.")))
    D.append(dict(
        id="K2", severity="critical",
        where="benchmark/report16_base.py :: FC_MAIN=3.5e9 (헤드라인 대역) — 전 단계 상속",
        title_ko="헤드라인 대역에서 날개는 파장의 0.16 배다. PO 가 1 dB 안으로 맞는 문턱의 **1/4.5**",
        numbers=dict(J["why_this_lens"], po_model_error_on_spheres=_sphere_po_error()),
        why_ko=("PO 는 «면이 파장보다 넉넉히 클 때» 의 근사다. 날개는 그 반대다. 그런데 "
                "마이크로도플러는 **오직 날개**가 만든다. 즉 이 라운드의 신호는 커널이 "
                "가장 못 믿는 부품에서만 나온다. 동체(문턱 2.68 GHz)는 통과하므로, "
                "동체가 지배하는 양(σ·dc_ac 의 분자)은 상대적으로 안전하고 날개가 지배하는 "
                "양(플래시·풍부도·폭)이 위험하다 — 하필 라운드의 헤드라인이 후자다."),
        crude_ko="무릎 값 0.729λ 는 report00 의 PO↔MoM 비교에서 온 것이고 2D 판 기준이다.",
        what_would_settle_ko="같은 날개 형상을 MoM/FEM 으로 한 번 풀어 3.5 GHz 에서의 PO 오차를 직접 잰다."))
    D.append(dict(
        id="K3", severity=("high" if unstable else "medium"),
        where="이 파일 T2/T5 + outputs/report16_metric_*.json (hi| 항목)",
        title_ko="주파수를 무릎 위로 올리면 일부 대조의 **부호가 뒤집힌다**",
        numbers=dict(sweep_unstable=unstable,
                     cross_band_flip_rate=J["T5_cross_band_audit_of_existing_artifacts"]["flip_rate"],
                     n_sign_flips=J["T5_cross_band_audit_of_existing_artifacts"]["n_sign_flips"],
                     n_comparisons=J["T5_cross_band_audit_of_existing_artifacts"]["n_comparisons"]),
        why_ko=("어떤 대조가 «대역에 딸린» 것이면 그 결론은 형상에 대한 진술이 아니다. "
                "우리는 두 대역만 갖고 있고, 그 사이에서 방향이 뒤집히는 항목이 실제로 있다."),
        crude_ko="내 훑기는 방위 12점·평면 통제 없음. 부호만 읽어라.",
        what_would_settle_ko="표면오차÷파장을 축으로 여러 주파수를 훑어 «무해→유해» 경계를 곡선으로 낸다."))
    D.append(dict(
        id="K3b", severity="critical",
        where="outputs/report16_metric_mesh_half_tri.json :: grading_independent P2·P3 (문턱) × hi_band.paired",
        title_ko=("⭐ «메쉬 해상도는 안 중요하다» 는 3 개 게이트 중 **%d 개가 무릎 대역에서 뒤집힌다** "
                  "(같은 문턱, 앞 단이 이미 계산해 둔 값)" % J["T4b_same_threshold_at_the_knee"]["n_flipped"]),
        numbers=J["T4b_same_threshold_at_the_knee"],
        why_ko=("삼각형을 절반으로 줄여도 지표가 안 움직인다는 판정은 3.5 GHz 에서만 성립한다. "
                "블레이드가 PO 유효 범위에 드는 15.86 GHz 에서 **같은 문턱**을 대면 같은 절반 메쉬가 "
                "문턱을 넘는다. 즉 «해상도 무관» 은 형상의 성질이 아니라 **파장이 그 형상을 못 보는** "
                "성질이다. 논문 문장으로 나가면 조건 없이 틀린 문장이 된다."),
        crude_ko="이 숫자는 앞 단이 계산한 것이고 내가 문턱만 다시 댄 것이다 — 새 계산 없음.",
        what_would_settle_ko="주파수를 축으로 «해상도 무해 → 유해» 경계를 곡선으로 내고, 그 곡선 위에서 3.5 GHz 의 위치를 밝힌다."))
    D.append(dict(
        id="K4", severity="high",
        where="outputs/report16_base.json :: findings.q1 (mesh_generations)",
        title_ko="같은 커널로도 옛 메쉬(07-27) 와 새 메쉬는 **파형이 알아볼 수 없이** 다르다",
        numbers=dict(waveform_corr=LED["mesh_generation_0727_to_0804"],
                     shake_over_effect=LED["shake_over_effect"]["mesh_generation"]),
        why_ko=("정합필터·템플릿 분류가 보는 것은 파형이다. 그 상관이 matrice4e 0.51 · "
                "mavic4pro 0.19 라면, 옛 메쉬로 학습한 분류기는 새 메쉬에서 쓸 수 없다. "
                "요약 지표는 훨씬 덜 움직이므로 «메쉬 정밀도가 중요한가» 의 답이 **쓰임새에 따라 갈린다**. "
                "⭐ 이것은 이 라운드의 결론보다 큰 별개의 결과이며, 동시에 이 라운드 숫자의 유통기한이 "
                "메쉬 한 번 고칠 때까지라는 뜻이다."),
        crude_ko="이 수치는 기반 단이 계산한 것이고 내가 재계산하지 않았다(내 게이트는 표 재현까지만).",
        what_would_settle_ko="다음 CAD 정정 때 같은 표를 다시 만들어 상관이 또 0.5 로 떨어지는지 본다."))
    D.append(dict(
        id="K5", severity="high",
        where="outputs/report16_base.json :: archive_2026_07_29 (SBR) vs 새 PO",
        title_ko="가림이 있는 옛 엔진과 없는 새 엔진은 «동체:날개 비» 에서 20 dB 넘게 벌어진다",
        numbers=LED["engine_gap_sbr_vs_po_dc_ac"],
        why_ko=("dc_ac_db 는 네 지표 가족 중 하나다. 엔진을 바꾸는 것만으로 20 dB 이상 움직이는 "
                "양이라면, 그 절대값은 물리가 아니라 **엔진 선택**을 재고 있다. 대역밖 잡음 보정을 "
                "해도 갭은 거의 그대로다."),
        crude_ko="⚠ 통제된 A/B 가 아니다(엔진·메쉬·규약이 동시에 다름). 자릿수 논거로만 쓸 것.",
        what_would_settle_ko="같은 메쉬·같은 규약으로 SBR 과 PO 를 나란히 돌린다."))
    D.append(dict(
        id="K6", severity="medium",
        where="benchmark/report16_base.py :: md_metrics16 (지표 정의) + 각 metric 단",
        title_ko="네 지표 가족이 서로 독립이 아니고, 널(구·원판)에서 값이 정의되지 않는다",
        numbers=dict(
            identity_err=CB["metric_redundancy"]["max_abs_err_sym180_identity"],
            null_false_positive=CB["null_calibration_of_separation_count"].get("false_positive_on_nulls"),
            convexity_control=T1["convexity_control"]),
        why_ko=("«6 지표 중 n 개가 갈렸다» 식 집계는 지표가 독립일 때만 뜻이 있다. 실제로는 "
                "블레이드 2 장일 때 대칭상관 = |2·빗몫 − 1| 이 대수적 항등식이고, 회전대칭 널에서도 "
                "4~6/6 이 «갈린다» 고 나온다."),
        crude_ko="이 항목은 앞 단이 이미 계산해 둔 값을 인용한 것이다.",
        what_would_settle_ko="지표를 상관행렬로 묶어 독립 축 수를 세고, 널 통과 게이트를 집계 전에 건다."))
    D.append(dict(
        id="K7", severity="medium",
        where="benchmark/report16_base.py :: EL_DEG=15, RANGE_M=10, N_AZ=24, 모노스태틱 고정",
        title_ko="앙상블이 자세 하나뿐이다 — 고각 1 점·거리 1 점·바이스태틱 각 0 점",
        numbers=dict(n_az=24, el_points=1, range_points=1, bistatic_points=0,
                     az_not_independent_note="이웃 15° 방위는 서로 닮아 유효표본은 24 보다 적다"),
        why_ko=("«24 방위 전부 같은 부호» 는 독립 24 표본이 아니다. 게다가 우리 논문의 시나리오는 "
                "패시브 **바이스태틱**인데 이 라운드는 전부 모노스태틱이다."),
        crude_ko="",
        what_would_settle_ko="고각 여러 개·바이스태틱 각 여러 개에서 같은 부호가 남는지 본다."))
    D.append(dict(
        id="K8", severity="low",
        where="이 파일 §A Kernel.table (깊이버퍼)",
        title_ko="내 그늘 코드 자체의 오차 — 볼록체 통제로 잰다",
        numbers=dict(convexity_control=T1["convexity_control"],
                     cell_and_tolerance_sensitivity=T1["cell_and_tolerance_sensitivity"]),
        why_ko=("볼록체(등가부피 구)는 앞면끼리 서로 가릴 수 없으므로 참값은 «이동 0» 이다. "
                "여기서 나오는 값이 곧 내 깊이버퍼가 스스로 만드는 가짜 이동량이다. "
                "칸 크기·여유를 바꿔 본 표도 같이 둔다 — 그 폭이 T1 의 신뢰구간이다."),
        crude_ko="⭐ 이 파일의 모든 새 숫자는 crude 다.",
        what_would_settle_ko="Möller–Trumbore 광선추적으로 같은 표를 다시 만든다."))
    J["defects"] = D

    # ── 9.3b 무엇이 살아남았나 — 적대검증은 «다 틀렸다» 가 아니라 «어디까지 참인가» 다 ── #
    surv = J["T2_frequency_sweep"]["conclusion_survives_across_band"]
    stable = {k: v["magnitude_by_freq"] for k, v in surv.items() if v["all_same"]}
    unstable_d = {k: v["magnitude_by_freq"] for k, v in surv.items() if not v["all_same"]}
    growth = {}
    for k in stable:
        mv = stable[k]
        lo, hi_ = mv[str(SWEEP_GHZ[0])], mv[str(SWEEP_GHZ[-1])]
        growth[k] = float(abs(hi_) / max(abs(lo), 1e-12))
    J["what_survives"] = dict(
        sign_stable_across_3p5_to_22GHz_NO_OCCLUSION=stable,
        sign_unstable=unstable_d,
        growth_22GHz_over_3p5GHz=growth,
        statement_ko=(
            "살아남은 것을 정직하게 적는다. ① **계산 자체** — 서로 다른 두 구현이 상대차 1e-13 "
            "으로 만난다. ② **존재/부재 진술** — 회전대칭체(구·원판)는 마이크로도플러를 원리적으로 "
            "못 만든다. 이것은 어떤 커널 결함에도 안 흔들린다. ③ **주파수 축의 안정성**(단, 가림 "
            "없는 커널 안에서만) — 풍부도 대조는 3.5~22 GHz 여섯 대역 전부 같은 부호이고 격차가 "
            "커진다. 반면 플래시 대조비·도플러 폭은 주파수만 바꿔도 부호가 바뀐다."),
        caveat_ko=(
            "⚠ ③ 은 **가림을 넣으면 무너진다**(headline_contrast_under_occlusion 참조 — 네 구석 "
            "전부 부호 반전). 처음에 나는 ③ 을 «대역 탓이 아니다» 의 근거로 적었는데 틀렸다. "
            "주파수를 훑은 커널에 그늘이 없었으므로 그 안정성은 «그늘 없는 세계 안에서의 안정성» "
            "이다. 이 정정을 지운 채로 인용하면 안 된다."))

    # ── 9.4 판정 ──────────────────────────────────────────────────────── #
    v = J["verdict"]
    crit = [d for d in D if d["severity"] == "critical"]
    verdict = "PREMATURE"
    if v["gate"] != "PASS":
        verdict = "BROKEN"
    J["verdict"] = dict(
        v, verdict=verdict, n_critical=len(crit),
        n_high=len([d for d in D if d["severity"] == "high"]),
        worst_occlusion_shift_flash_db=worst_occ,
        worst_occlusion_shift_n_eff=worst_occ_neff,
        unstable_across_band=unstable,
        rationale_ko=(
            "BROKEN 이 아니다 — 커널은 자기가 하겠다고 한 계산을 **정확히** 한다. 나는 전혀 다른 "
            "방식(전역좌표 일괄)으로 같은 표를 다시 만들어 상대차 %.1e 로 일치시켰고, 수렴·파면·"
            "점밀도 통제도 앞 단들이 통과시켜 놓았다. 그러나 SOUND 도 아니다 — 이 라운드의 헤드라인은 "
            "«정밀 형상 대 프리미티브» 라는 **크기 비교**인데, 그 크기가 (i) 없는 가림을 넣었을 때의 "
            "이동, (ii) 메쉬 세대를 바꿨을 때의 이동, (iii) 대역을 커널 유효범위로 옮겼을 때의 판정 "
            "뒤집힘과 같은 자릿수이거나 그보다 작다. 결정적으로 두 가지가 **부호까지** 뒤집힌다: "
            "(a) 헤드라인 대조 «프리미티브가 CAD 메쉬보다 풍부하다» 는 그늘을 넣으면 네 구석 전부 "
            "반대가 되고, (b) «메쉬 해상도는 안 중요하다» 는 3 게이트 중 2 개가 커널 유효 대역에서 "
            "FAIL 로 바뀐다. → PREMATURE."
            % J["independent_kernel_gate"]["max_rel_diff"]),
        what_is_safe_ko=("① 계산 자체 — 서로 다른 두 구현이 상대차 1e-13 으로 만난다. "
                         "② «구·원판은 방향 변동이 원리적으로 0 이므로 마이크로도플러를 못 낸다» "
                         "처럼 **존재/부재**에 걸린 진술. 이것은 어떤 커널 결함에도 안 흔들린다. "
                         "흔들리는 것은 «메쉬가 프리미티브보다 몇 dB 낫다/못하다» 같은 크기 진술이고, "
                         "⚠ 그중 헤드라인 대조는 크기만이 아니라 **부호**까지 흔들린다(K1b)."),
        headline_ko=("⭐ 이 라운드보다 큰 결과가 데이터 안에 이미 있다: 같은 커널로도 07-27 메쉬와 "
                     "현재 메쉬의 마이크로도플러 **파형**은 상관 0.19~0.51 로 다르다. "
                     "«메쉬 정밀도는 값어치가 없다» 는 요약 지표에서만 참이고, 파형을 쓰는 "
                     "분류기에서는 거짓이다."))
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print("→ finalized", OUT_JSON)
    return J


# =========================================================================== #
#  §10 ⭐ T1 재검 — 내 그늘 코드가 «없는 변조를 만들어 내는가»
#      첫 판의 볼록체 통제가 SUSPECT 로 나왔다. 그 통제 자체가 잘못 설계돼 있었다:
#      구 팔의 flash·n_eff·dc_ac 는 **수치 바닥**을 재는 값이라(앞 단들이 이미 «인용 자격
#      없음» 으로 분류) 아주 작은 흔들림에도 수십 dB 씩 튄다. 볼록체에서 실제로 0 이어야
#      하는 것은 **에너지**(σ)다. 여기서는 통제를 다시 설계해 세 가지를 잰다.
#        C1 에너지 통제 : 볼록한 구에서 |Δσ| ≈ 0 인가 (그늘이 에너지를 안 지워야 맞다)
#        C2 널 주입 통제: 회전대칭 원판에서 **대역 안** 변조가 새로 생기지는 않는가
#        C3 자격 통제   : 각 팔의 in_band_ac_frac 이 가림 전후로 0.5 를 넘는가
# =========================================================================== #
def t1_recheck():
    from report16_base import derive_protocol, md_metrics16, C0
    from drones import DRONES
    J = json.load(open(OUT_JSON))
    B = json.load(open(os.path.join(ROOT, "outputs", "report16_base.json")))
    fc0 = B["protocol"]["fc_main_hz"]
    MET2 = ("flash_contrast_db", "n_eff_orders", "width_ratio", "dc_ac_db",
            "sigma_eq_mean_dbsm", "in_band_ac_frac", "in_band_ac_over_dc_db",
            "metrics_interpretable")
    K = Kernel()
    az24 = np.arange(24) * 15.0
    out = dict(cell_m=CELL_CANDIDATES_M[1], tol_mode="adaptive", crude=True, per_arm={})
    store = {}
    for key in ("mini2", "matrice4e"):
        s = DRONES[key]
        proto = derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc0)
        for arm in ("mesh", "disc", "sphere"):
            cl = clouds_for(key, arm, fc0)
            for on in (False, True):
                M = []
                for az in az24:
                    E, _ = K.table(cl, fc0, az, proto, occlude=on,
                                   cell_m=CELL_CANDIDATES_M[1], tol_mode="adaptive")
                    M.append(md_metrics16(E, proto, s.prop_blades))
                store[(key, arm, on)] = M
                out["per_arm"][f"{key}|{arm}|{'occ' if on else 'no_occ'}"] = {
                    m: (summar([x[m] for x in M]) if m != "metrics_interpretable"
                        else float(np.mean([bool(x[m]) for x in M]))) for m in MET2}
            print(f"  [T1r] {key} {arm} done", flush=True)

    # C1 에너지 통제 (볼록한 구)
    c1 = {}
    for key in ("mini2", "matrice4e"):
        d = [abs(store[(key, "sphere", True)][i]["sigma_eq_mean_dbsm"] -
                 store[(key, "sphere", False)][i]["sigma_eq_mean_dbsm"]) for i in range(24)]
        c1[key] = dict(max_abs_dsigma_db=float(max(d)), mean_abs_dsigma_db=float(np.mean(d)),
                       verdict="PASS" if max(d) < 0.05 else "FAIL")
    # C2 널 주입 통제 (회전대칭 원판) — 대역 안 변조가 새로 생기나
    c2 = {}
    for key in ("mini2", "matrice4e"):
        a = [store[(key, "disc", False)][i]["in_band_ac_over_dc_db"] for i in range(24)]
        b = [store[(key, "disc", True)][i]["in_band_ac_over_dc_db"] for i in range(24)]
        mm = [store[(key, "mesh", True)][i]["in_band_ac_over_dc_db"] for i in range(24)]
        c2[key] = dict(disc_no_occ_db=summar(a), disc_occ_db=summar(b),
                       injected_db=float(np.mean(b) - np.mean(a)),
                       mesh_occ_db=summar(mm),
                       margin_mesh_over_injected_null_db=float(np.mean(mm) - np.mean(b)),
                       verdict="PASS" if (np.mean(mm) - np.mean(b)) > 20.0 else "MARGINAL")
    # C3 자격 통제
    c3 = {f"{key}|{arm}|{'occ' if on else 'no_occ'}":
          float(np.mean([x["in_band_ac_frac"] for x in store[(key, arm, on)]]))
          for key in ("mini2", "matrice4e") for arm in ("mesh", "disc", "sphere")
          for on in (False, True)}
    # 다시 쓴 이동량 — **자격 있는 팔(mesh)만**
    shifts = {}
    for key in ("mini2", "matrice4e"):
        shifts[key] = {m: summar([store[(key, "mesh", True)][i][m] -
                                  store[(key, "mesh", False)][i][m] for i in range(24)])
                       for m in ("flash_contrast_db", "n_eff_orders", "width_ratio",
                                 "dc_ac_db", "sigma_eq_mean_dbsm")}
        shifts[key]["frac_same_sign"] = {
            m: float(np.mean([np.sign(store[(key, "mesh", True)][i][m] -
                                      store[(key, "mesh", False)][i][m]) ==
                              np.sign(shifts[key][m]["mean"]) for i in range(24)]))
            for m in ("flash_contrast_db", "n_eff_orders", "dc_ac_db", "sigma_eq_mean_dbsm")}
    out["C1_energy_control_convex_sphere"] = c1
    out["C2_null_injection_control_disc"] = c2
    out["C3_interpretability_in_band_frac"] = c3
    out["mesh_shift_qualified"] = shifts
    out["why_the_first_control_was_wrong_ko"] = (
        "첫 판은 볼록한 구에서 flash·n_eff·dc_ac 의 이동을 통제로 삼았다. 잘못이다 — 그 팔의 "
        "변조는 물리가 아니라 **격자 잔재**라(앞 단들이 이미 «인용 자격 없음» 으로 분류) 아주 "
        "작은 흔들림에도 수십 dB 튄다. 볼록체에서 진짜로 0 이어야 하는 것은 **에너지**다. "
        "그래서 통제를 σ 로 바꾸고, 별도로 «없는 변조를 만들어 내는가» 를 회전대칭 원판으로 잰다.")
    J["T1b_occlusion_recheck"] = out

    # 결함표·판정 갱신
    for d in J["defects"]:
        if d["id"] == "K8":
            d["numbers"] = dict(d.get("numbers", {}), recheck=dict(
                C1=c1, C2=c2, C3=c3))
            d["title_ko"] = "내 그늘 코드 자체의 오차 — 에너지 통제는 통과, 널 주입은 남는다"
            d["severity"] = "medium"
        if d["id"] == "K1":
            d["numbers"] = dict(d.get("numbers", {}), qualified_shift=shifts,
                                controls=dict(C1=c1, C2=c2))
    # ⭐ 크기 견주기를 **자격 있는** 이동량으로 다시 계산한다 (첫 판은 통제 전 값이었다)
    claim = J["T3_magnitude_ledger"]["round_claimed_effect_sizes"]
    rq = {}
    for key in ("mini2", "matrice4e"):
        for mk, ck in (("n_eff_orders", f"P1_slab_minus_mesh_n_eff|{key}"),
                       ("n_eff_orders", f"cube_minus_mesh_n_eff|{key}"),
                       ("flash_contrast_db", f"cube_minus_mesh_flash_db|{key}")):
            if ck in claim:
                rq[f"{key}|occ_shift[{mk}] / |{ck}|"] = float(
                    abs(shifts[key][mk]["mean"]) / max(abs(claim[ck]), 1e-12))
    J["T3_magnitude_ledger"]["shake_over_effect"]["occlusion_qualified"] = rq
    J["T3_magnitude_ledger"]["shake_over_effect"]["note_qualified_ko"] = (
        "T1b 의 통제를 통과한 mesh 팔 이동량으로 다시 계산한 비. 1.0 을 넘으면 «가림을 넣었을 때의 "
        "이동이 라운드가 주장하는 효과보다 크다» 는 뜻이다.")
    # 첫 판의 잘못 설계된 통제·통제 전 비율은 여기서 **덮어쓴다** (남겨 두면 오독된다)
    J["verdict"]["convexity_control"] = all(v["verdict"] == "PASS" for v in c1.values())
    J["verdict"]["convexity_control_note_ko"] = (
        "T1_occlusion.convexity_control 의 SUSPECT 는 통제 설계가 잘못된 것이었다 — "
        "T1b 의 C1(에너지) 로 대체한다. 첫 판 값은 기록용으로 남긴다.")
    J["verdict"]["worst_occlusion_shake_over_effect"] = float(max(rq.values())) if rq else float("nan")
    J["verdict"]["worst_occlusion_shake_over_effect_note_ko"] = "T1b 통제를 통과한 값으로 갱신"
    J["verdict"]["occlusion_controls"] = dict(
        C1_energy=all(v["verdict"] == "PASS" for v in c1.values()),
        C2_null_injection=all(v["verdict"] == "PASS" for v in c2.values()),
        worst_qualified_shake_over_effect=float(max(rq.values())) if rq else float("nan"))
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1, default=float)
    print("→ T1 recheck merged", OUT_JSON)
    return out


if __name__ == "__main__":
    if "--t1-recheck" in sys.argv:
        t1_recheck()
    elif "--finalize" in sys.argv:
        finalize()
    else:
        main()
        finalize()
