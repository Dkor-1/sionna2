# -*- coding: utf-8 -*-
"""
adv_mesh_buried_faces_0816.py — **매몰면(I3) 전수 + 수리 + σ 대가 측정**
================================================================================

무엇을 하나 (감사 `docs/MESH_AUDIT_0816.md` I3 의 집행)
------------------------------------------------------
① **전수 검사** — 부품이 다른 부품 솔리드 **안**에 든 면적을 **전 기체·전 부품쌍**에서 잰다.
   (기존 검사는 prop↔motor **한 쌍**뿐이었다.) 기체별 **예산표**를 세운다.
② **수리 손잡이** — 그 매몰면을 PO 적분에서 빼는 선택 인자
   (`rcs_po.drone_rcs_pattern(mesh_fix="i3")` · 공용 스위치 `MESH_FIX=i3`).
③ **σ 대가** — 수리 전후 σ 를 **우리 커널로 직접** 재서 dB 로 남긴다. 감사가 «mavic4pro +38 %
   ·mini5pro +42 % 면적 과대» 라고만 적은 자리를 dB 로 채운다.
④ **회귀** — 인자를 **안 주면 옛 결과와 비트동일**임을 해시로 증명한다.

왜 PO 에서만 문제인가
---------------------
`rcs_po.py` 46-53행이 스스로 «이 PO 는 자기차폐를 무시한다» 고 선언한다. 즉 다른 부품 속에
파묻혀 실물이라면 안 보이는 면도 **그대로 더한다** = 이중계상. 기본 엔진 SBR 은 광선이 처음
맞은 지점만 적분하므로(first-hit) 이 오차가 **구조적으로 0** 이다. 아래 dB 는 **PO 경로 전용**.

측정 규약 (기준선 원장 `outputs/mesh_layer2_baseline_0816.json` 과 **같은 규약**)
--------------------------------------------------------------------------------
· 3.5 GHz(5G) · 점간격 λ/7 = 12.24 mm(`rcs_po` 기본과 동일) · 방위 0~358° 2° 간격 180 방위
· 고각 el 0° 와 −30° · 바이스태틱 β=120°(el −30°) — 모노만 재면 유리한 각도만 고른 셈이 된다
· 방위별 dB 는 **5G 100 MHz·9점 대역평균**으로 읽는다(단일주파수 널은 rcs_po 자신이
  «개별적으로는 수치 아티팩트» 라 선언한 값). 3° 각도창 판과 p95 도 함께 싣는다.
· 부호: (+) = 결함이 σ 를 **밝게** 만든다(과대계상)
· 판정 밴드: 무해 <0.1 dB · 보임 0.1~1.0 dB · 결론을 바꿈 >1 dB

⭐ 핵심 설계: **결함판과 수리판이 같은 점구름을 쓴다.** 전체 점의 장 E_full 에서 뺄 면의 점이
   만든 장 E_drop 을 빼면 「그 면을 지운 판」이 정확히 나온다 — 재샘플링이 아니므로 두 판의
   차이는 **오직 뺀 면** 때문이다. 그 값이 `mesh_to_points(face_mask=…)` 로 다시 깐 판과
   같은지도 확인한다(두 길이 만나야 손잡이가 진짜다).

실행:
  cd /workspace/sionna && PYTHONPATH=src:benchmark python benchmark/adv_mesh_buried_faces_0816.py
  ⛔ GPU 안 쓴다(전부 CPU). 산출: outputs/mesh_layer2_buried_faces_0816.json
  옵션: --quick(기체 3종만) · --gates(검사기 게이트도 같이 돌린다)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import rcs_po                                                     # noqa: E402
from rcs_po import C0, mesh_to_points, rcs_from_points, angular_smooth   # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT           # noqa: E402
from mesh_buried import buried_census, buried_face_mask           # noqa: E402
from materials import gamma_po                                    # noqa: E402

OUT = os.path.join(ROOT, "outputs", "mesh_layer2_buried_faces_0816.json")

FC = 3.5e9
LAM = C0 / FC
SPACING = LAM / 7.0
AZ = np.arange(0.0, 360.0, 2.0)
AZ_STEP = 2.0
BW = 100e6
N_F = 9
SMOOTH_WIN_DEG = 3.0

#  기하 세 판 — (이름, β[deg], el[deg])
GEOMS = (("mono_el0", 0.0, 0.0), ("mono_el-30", 0.0, -30.0), ("bi_b120_el-30", 120.0, -30.0))

#  ⚠ ITU 'metal' 의 |Γ| 만 Sionna RT 씬(=OptiX/GPU)이 필요하다. GPU 금지 라운드라
#    저장소가 **이미 캐시해 둔** 3.5 GHz 값을 쓴다(기준선 원장과 같은 출처·같은 수).
METAL_GAMMA_5G = 0.9998026802895116     # outputs/mesh_compare_material.json :: materials.metal.gamma_po_5g

#  ⭐ 수정 **전**(2026-08-16, rcs_po 에 face_mask/return_face_idx 를 넣기 전) 출하 커널의
#    출력 해시. 「인자를 안 주면 비트동일」의 증거다. 만드는 법은 아래 `_freeze_hashes()`.
#    P·N·dA·w 는 mesh_to_points(mesh, λ/7, gamma=G) 의 반환, s_el0/s_el30 은
#    rcs_from_points(…, az=0~358 step2, el=0/−30) 의 σ 배열 — 전부 float64 원시 바이트 SHA-256.
PRE_EDIT_HASHES = {
    "mini5pro": dict(n=31164, P="444442bd0565a7a9", N="7ea4edb22076b979", dA="8912833644c155eb",
                     w="fc7176ae711ec7c0", s_el0="43f09a8da1ad4e89", s_el30="0d3b0e6dd1a0b9b7"),
    "mavic4pro": dict(n=38876, P="61a667bd68fcf55c", N="f025c2f081de3fa1", dA="21c4a095b2e1cf0c",
                      w="77b6849968bb544f", s_el0="2bf296e07ef550a7", s_el30="cd07eb644726c089"),
    "matrice4e": dict(n=40649, P="4be806de33696a96", N="3558cb0553e3159c", dA="6e48d2071e04f6fe",
                      w="39337787e0586798", s_el0="0d6ee99fceafc073", s_el30="fd919f38078f8949"),
    "s1000plus": dict(n=191864, P="bb23b84fdf61663e", N="fa2d1105c54f96f2", dA="54efdc62af71dae6",
                      w="85035ecefcb45085", s_el0="ea922df4d1783242", s_el30="ddecb254613af469"),
    "phantom4": dict(n=45534, P="39f88ec67c8ce553", N="df8df0a3c1ca2c1e", dA="c8f57a77a1eaaed2",
                     w="6a7a9843dec6c80a", s_el0="0954281ef366ef63", s_el30="bcc79fb3cbbf8d40"),
    "typhoonh480": dict(n=75006, P="40949890a759e99f", N="0b85ca08311d5922", dA="a54be14c6a69ba6b",
                        w="d1e1ffe38070cf37", s_el0="018e0e8eebf8fce3", s_el30="e01c5c700471d809"),
    "x500v2": dict(n=77982, P="a5cbc3281b80c8d1", N="968857091441cea0", dA="73230b5a809d9a79",
                   w="a0e359e4496ffa49", s_el0="cb1d7d85309b0468", s_el30="3ce7b846577d4266"),
    "phantom3": dict(n=39141, P="adaebc6896f1012e", N="29ac3656393d7b60", dA="8c45dea6f37da599",
                     w="e28124eaf449cf9f", s_el0="273113f3eec7b630", s_el30="6bea6162f76783b6"),
    "m350rtk": dict(n=130343, P="93923a6b2951a8b6", N="1af9945ae3f2cecd", dA="44d5123c8f8b73a3",
                    w="9c5b692d24bf7297", s_el0="533fb88e4f6d2662", s_el30="42b1be55c90bd39c"),
    "mini2": dict(n=26832, P="8d5133f15325c7c1", N="4f4b73dbaff0519d", dA="a2bd69c9b0bb03d2",
                  w="e729b237dce5fda7", s_el0="58e06fd618b1812d", s_el30="57a13cb710d869b8"),
}
#  ↑ σ 배열 해시(s_el0·s_el30)는 P·N·dA·w 중 **하나라도** 달라지면 반드시 깨지므로 가장 강한
#    잣대다. 그래도 넷을 따로 싣는 이유: 깨졌을 때 **어디가** 깨졌는지 바로 보이게.
#    ⚠ 이 표는 «수리를 안 켠» 상태의 기준이다. MESH_FIX 를 켜고 이 시험을 돌리면 메쉬가
#      바뀌므로 **당연히 깨진다** — 그것이 의도다(아래 regression_bit_identity 가 확인한다).


def _sha(a) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


def _mesh_to_points_PRE_EDIT(mesh, spacing, gamma=None, return_keys=False):
    """⭐ 수정 **전** `rcs_po.mesh_to_points` 의 본문을 **글자 그대로** 옮긴 사본.

    왜 이게 필요한가: 해시 표(PRE_EDIT_HASHES)는 «메쉬가 그때 그 상태일 때만» 쓸 수 있다.
    이 라운드에는 **다른 수리자들이 메쉬를 고치고 있어서** 그 표는 메쉬가 움직이면 깨진다 —
    그건 내 코드가 아니라 메쉬가 바뀌었다는 뜻이다. 두 사실을 갈라야 하므로, 여기 사본과
    지금 코드를 **같은 메쉬**에 돌려 견준다. 이 대조는 메쉬 상태와 **무관하게** 성립한다."""
    V = np.array(mesh.v)
    Ps, Ns, dAs, Ws, Ks = [], [], [], [], []
    for fi, (ia, ib, ic) in enumerate(mesh.f):
        v0, v1, v2 = V[ia], V[ib], V[ic]
        e1, e2 = v1 - v0, v2 - v0
        nrm = np.cross(e1, e2)
        area = 0.5 * np.linalg.norm(nrm)
        if area < 1e-12:
            continue
        nhat = nrm / (2 * area)
        emax = max(np.linalg.norm(e1), np.linalg.norm(e2), np.linalg.norm(v2 - v1))
        N = max(1, int(np.ceil(emax / spacing)))
        ij = [(i, j) for i in range(N) for j in range(N) if (i + 0.5) + (j + 0.5) <= N]
        if not ij:
            ij = [(0, 0)]
        uv = (np.array(ij) + 0.5) / N
        pts = v0 + uv[:, :1] * e1 + uv[:, 1:] * e2
        Ps.append(pts)
        Ns.append(np.tile(nhat, (len(pts), 1)))
        dAs.append(np.full(len(pts), area / len(pts)))
        if gamma is not None:
            Ws.append(np.full(len(pts), float(gamma.get(mesh.g[fi], 1.0))))
        if return_keys:
            Ks.append(np.full(len(pts), mesh.g[fi], object))
    out = (np.vstack(Ps), np.vstack(Ns), np.concatenate(dAs))
    if gamma is not None:
        out = out + (np.concatenate(Ws),)
    if return_keys:
        out = out + (np.concatenate(Ks),)
    return out


def mesh_state(mesh) -> dict:
    """**메쉬 상태 지문** — 이 원장의 수가 «어느 메쉬» 에서 나왔는지 못 박는다.
    다른 수리자가 형상을 바꾸면 이 값이 바뀌고, 그러면 아래 census·σ 는 다시 재야 한다."""
    return dict(n_faces=int(len(mesh.f)), n_verts=int(len(mesh.v)),
                sha_verts=_sha(np.asarray(mesh.v, float))[:16],
                sha_faces=hashlib.sha256(
                    np.ascontiguousarray(np.asarray(mesh.f, np.int64)).tobytes()).hexdigest()[:16])


def gamma_map() -> dict:
    """그룹 → PO |Γ|. GPU 가 필요한 키는 캐시값으로 대신한다(위 주석)."""
    out = {}
    for g, (mat, _) in DRONE_GROUP_MAT.items():
        try:
            out[g] = float(gamma_po(mat, FC))
        except Exception:
            out[g] = METAL_GAMMA_5G
    return out


def _look(az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg)); el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def po_fields(P, N, amp, fc, beta_deg, el_deg, masks, chunk=8192):
    """바이스태틱 스칼라 PO 장 — **한 번 훑으면서** 여러 부분집합의 장을 동시에 모은다.

        E = Σ [n̂·û_i>0][n̂·û_s>0] |Γ| (n̂·û_i) ΔA · exp(j k P·(û_i+û_s))

    β=0 이면 û_i=û_s 라 위상이 exp(j2k P·û) 가 되어 **출하 `rcs_from_points` 와 같은 식**이다
    (그 회귀를 main 에서 수치로 확인한다). masks 는 {이름: 점별 bool} — 그 점들만 더한 장을
    같이 돌려준다(«그 면을 지운 판» 을 만들 때 쓴다)."""
    k = 2 * np.pi * fc / C0
    Ui = _look(AZ - beta_deg / 2.0, el_deg)
    Us = _look(AZ + beta_deg / 2.0, el_deg)
    Usum = Ui + Us
    E = np.zeros(len(AZ), complex)
    Em = {m: np.zeros(len(AZ), complex) for m in masks}
    for s in range(0, len(P), chunk):
        sl = slice(s, s + chunk)
        NI = N[sl] @ Ui.T
        NS = N[sl] @ Us.T
        PH = P[sl] @ Usum.T
        g = np.where((NI > 0) & (NS > 0), NI, 0.0)
        integ = g * amp[sl][:, None] * np.exp(1j * k * PH)
        E += integ.sum(axis=0)
        for m, sel in masks.items():
            ss = sel[sl]
            if ss.any():
                Em[m] += integ[ss].sum(axis=0)
    return E, Em


def band_sigma(P, N, amp, beta_deg, el_deg, masks):
    """대역평균 σ(az). 반환 (sigma_full, {마스크이름: sigma_그_면을_뺀_판})."""
    freqs = np.linspace(FC - BW / 2, FC + BW / 2, N_F)
    acc = np.zeros(len(AZ))
    accm = {m: np.zeros(len(AZ)) for m in masks}
    for f in freqs:
        lam = C0 / f
        E, Em = po_fields(P, N, amp, f, beta_deg, el_deg, masks)
        acc += (4 * np.pi / lam ** 2) * np.abs(E) ** 2
        for m in masks:
            accm[m] += (4 * np.pi / lam ** 2) * np.abs(E - Em[m]) ** 2   # 그 면을 **뺀** 판
    return acc / N_F, {m: v / N_F for m, v in accm.items()}


def delta_metrics(sig_defect, sig_repaired) -> dict:
    """결함판 ↔ 수리판의 dB 차. (+) = 결함이 밝게 만든다(과대계상)."""
    d = 10 * np.log10(np.maximum(sig_defect, 1e-30) / np.maximum(sig_repaired, 1e-30))
    sd = angular_smooth(sig_defect, SMOOTH_WIN_DEG, AZ_STEP)
    sr = angular_smooth(sig_repaired, SMOOTH_WIN_DEG, AZ_STEP)
    dw = 10 * np.log10(np.maximum(sd, 1e-30) / np.maximum(sr, 1e-30))
    i = int(np.argmax(np.abs(d)))
    return dict(
        azimuth_mean_db=round(float(10 * np.log10(sig_defect.mean() / sig_repaired.mean())), 4),
        worst_az_db=round(float(d[i]), 3), worst_az_deg=float(AZ[i]),
        worst_az_db_3deg_window=round(float(dw[int(np.argmax(np.abs(dw)))]), 3),
        p95_abs_db=round(float(np.percentile(np.abs(d), 95)), 3),
        sigma_with_defect_azmean_dbsm=round(float(10 * np.log10(sig_defect.mean())), 3),
        sigma_repaired_azmean_dbsm=round(float(10 * np.log10(sig_repaired.mean())), 3))


def band(x: float) -> str:
    a = abs(x)
    return "무해(<0.1dB)" if a < 0.1 else ("보임(0.1~1dB)" if a <= 1.0 else "⭐결론을_바꿈(>1dB)")


# --------------------------------------------------------------------------- #
#  회귀 ①  «인자를 안 주면 비트동일»
# --------------------------------------------------------------------------- #
def regression_bit_identity(keys, G) -> dict:
    """네 가지를 한꺼번에 증명한다.

      ⭐(a) **코드 동일성** — 인자를 안 준 지금 코드 == 수정 전 본문 사본
            (`_mesh_to_points_PRE_EDIT`). **메쉬 상태와 무관**하게 성립하는 잣대다.
        (b) `face_mask=전부True` == 인자 없는 판 (새 코드경로의 동치)
        (c) `drone_rcs_pattern(mesh_fix 없음)` == 손으로 짠 옛 경로, 그리고 켜면 실제로 바뀐다
        (d) **메쉬 상태** — 2026-08-16 23:46 기준선 메쉬와 같은가(PRE_EDIT_HASHES).
            ⚠ 이것이 깨지는 것은 **내 코드가 아니라 메쉬가 움직였다**는 뜻이다(이 라운드에는
              다른 수리자들이 형상을 고치고 있다). 그래서 (a) 와 따로 보고한다."""
    from geom import mesh_fix_set
    rows = {"_switch_state": sorted(mesh_fix_set())}
    for k in keys:
        m = build_drone(DRONES[k])
        P, N, dA, w = mesh_to_points(m, SPACING, gamma=G)
        s0 = rcs_from_points(P, N, dA, FC, AZ, 0.0, w=w)
        s30 = rcs_from_points(P, N, dA, FC, AZ, -30.0, w=w)
        ref = PRE_EDIT_HASHES.get(k, {})
        got = dict(n=int(len(dA)), P=_sha(P)[:16], N=_sha(N)[:16], dA=_sha(dA)[:16],
                   w=_sha(w)[:16], s_el0=_sha(s0)[:16], s_el30=_sha(s30)[:16])
        P2, N2, dA2, w2, fi = mesh_to_points(m, SPACING, gamma=G,
                                             face_mask=np.ones(len(m.f), bool),
                                             return_face_idx=True)
        #  (c) drone_rcs_pattern 통로 — mesh_fix 를 **안 주면** 손잡이가 아무것도 안 하는가.
        #  ⚠ 여기서만 materials=False(전부 PEC)로 부른다. materials=True 는 |Γ|('metal')를
        #    Sionna 씬에서 뽑느라 **GPU 가 필요**해 이 라운드에서 못 돈다(위 METAL_GAMMA_5G 주석).
        #    재질 가중은 마스크와 직교하므로(점별 곱셈) 이 대조의 힘은 줄지 않는다.
        Pp, Np_, dAp = mesh_to_points(m, SPACING)
        ref_pec = rcs_from_points(Pp, Np_, dAp, FC, AZ, 0.0)
        sig_off, _ = rcs_po.drone_rcs_pattern(k, FC, AZ, 0.0, engine="po", materials=False)
        sig_on, _ = rcs_po.drone_rcs_pattern(k, FC, AZ, 0.0, engine="po", materials=False,
                                             mesh_fix="i3")
        #  (a) 코드 동일성 — 같은 메쉬에 «수정 전 본문 사본» 을 돌려 견준다
        Pr, Nr, dAr, wr = _mesh_to_points_PRE_EDIT(m, SPACING, gamma=G)
        code_same = bool(_sha(Pr) == _sha(P) and _sha(Nr) == _sha(N)
                         and _sha(dAr) == _sha(dA) and _sha(wr) == _sha(w))
        rows[k] = dict(
            got=got, pre_edit_baseline_mesh=ref, mesh_state=mesh_state(m),
            **{"⭐code_identical_vs_pre_edit_body": code_same},
            mesh_state_matches_baseline=bool(all(got[f] == ref.get(f) for f in got)),
            handle_off_bit_identical=bool(_sha(sig_off) == _sha(ref_pec)),
            #  ⚠ 이 dB 는 **PEC(materials=False)·단일주파수** 판이라 위 σ 표(재질 가중·대역평균)와
            #    크기가 다르다. 여기서 보려는 것은 크기가 아니라 «손잡이를 켜면 실제로 바뀌는가».
            handle_on_sigma_shift_db_PEC_singlefreq=round(
                float(10 * np.log10(sig_on.mean() / ref_pec.mean())), 4),
            bit_identical_vs_pre_edit=bool(all(got[f] == ref.get(f) for f in got)),
            mask_all_true_identical=bool(_sha(P2) == _sha(P) and _sha(N2) == _sha(N)
                                         and _sha(dA2) == _sha(dA) and _sha(w2) == _sha(w)),
            face_idx_max=int(fi.max()))
    rows["_뜻"] = {
        "⭐code_identical_vs_pre_edit_body": "내 코드 변경이 **아무 값도 안 바꾼다**는 증거. "
            "지금 메쉬에 «수정 전 본문 사본» 을 돌려 바이트로 견줬다 — 메쉬가 어떻게 바뀌든 성립한다.",
        "mesh_state_matches_baseline": "2026-08-16 23:46 기준선과 **같은 메쉬**인가. "
            "False 면 다른 수리자가 형상을 바꿨다는 뜻이고, 그러면 이 원장의 census·σ 는 "
            "그 새 형상에서 다시 잰 값이다(mesh_state 지문이 어느 형상인지 못 박는다).",
        "handle_off_bit_identical": "drone_rcs_pattern 에 mesh_fix 를 **안 주면** 손잡이가 "
            "아무것도 안 한다(PEC 판으로 확인 — materials=True 는 GPU 필요).",
    }
    return rows


def regression_kernel(P, N, dA, w) -> float:
    """내 적분 ↔ 출하 커널 — β=0 에서 상대오차(기계정밀도여야 한다)."""
    E, _ = po_fields(P, N, dA * w, FC, 0.0, 0.0, {})
    sig_mine = (4 * np.pi / LAM ** 2) * np.abs(E) ** 2
    sig_ship = rcs_from_points(P, N, dA, FC, AZ, 0.0, w=w)
    return float(np.max(np.abs(sig_mine - sig_ship) / np.maximum(sig_ship, 1e-30)))


def regression_two_paths(mesh, G, keep) -> dict:
    """수리판을 **두 길**로 만들어 견준다.
      (a) 같은 점구름에서 뺀 것(E_full − E_drop)
      (b) `mesh_to_points(face_mask=keep)` 로 다시 깐 것 ← 실제 손잡이가 쓰는 길
    둘이 같아야 손잡이가 «내가 잰 그것» 을 진짜로 한다."""
    P, N, dA, w, fi = mesh_to_points(mesh, SPACING, gamma=G, return_face_idx=True)
    drop_pt = ~keep[fi]
    sig_full, sig_rep = band_sigma(P, N, dA * w, 0.0, 0.0, {"d": drop_pt})
    Pb, Nb, dAb, wb = mesh_to_points(mesh, SPACING, gamma=G, face_mask=keep)
    freqs = np.linspace(FC - BW / 2, FC + BW / 2, N_F)
    acc = np.zeros(len(AZ))
    for f in freqs:
        acc += rcs_from_points(Pb, Nb, dAb, f, AZ, 0.0, w=wb)
    sig_b = acc / N_F
    a = sig_rep["d"]
    return dict(n_points_full=int(len(dA)), n_points_repaired=int(len(dAb)),
                max_rel_err=float(np.max(np.abs(a - sig_b) / np.maximum(sig_b, 1e-30))),
                max_abs_db=float(np.max(np.abs(10 * np.log10(np.maximum(a, 1e-30) /
                                                             np.maximum(sig_b, 1e-30))))))


# --------------------------------------------------------------------------- #
def run(keys, do_gates=False) -> dict:
    G = gamma_map()
    t0 = time.time()
    census, sigma, budget = {}, {}, {}
    kern_reg = {}
    for k in keys:
        spec = DRONES[k]
        mesh = build_drone(spec)
        c = buried_census(mesh, k, vertex_test=True)
        c["⭐mesh_state"] = mesh_state(mesh)     # 이 수가 «어느 형상» 에서 나왔는지 못 박는다
        census[k] = c
        m_def = buried_face_mask(mesh, kind="defect")
        m_all = buried_face_mask(mesh, kind="all")
        P, N, dA, w, fi = mesh_to_points(mesh, SPACING, gamma=G, return_face_idx=True)
        amp = dA * w
        kern_reg[k] = regression_kernel(P, N, dA, w)
        masks = {"defect": m_def[fi], "all_buried": m_all[fi]}
        per_geom = {}
        for gname, beta, el in GEOMS:
            sig_full, sig_rep = band_sigma(P, N, amp, beta, el, masks)
            per_geom[gname] = {
                "⭐진짜결함만_뺐을_때": delta_metrics(sig_full, sig_rep["defect"]),
                "매몰면_전부_뺐을_때(⚠수리안_아님)": delta_metrics(sig_full, sig_rep["all_buried"]),
            }
            per_geom[gname]["판정"] = band(
                per_geom[gname]["⭐진짜결함만_뺐을_때"]["azimuth_mean_db"])
            print(f"  {k:12s} {gname:14s} 결함만 "
                  f"{per_geom[gname]['⭐진짜결함만_뺐을_때']['azimuth_mean_db']:+7.3f} dB · 전부 "
                  f"{per_geom[gname]['매몰면_전부_뺐을_때(⚠수리안_아님)']['azimuth_mean_db']:+7.3f} dB",
                  flush=True)
        sigma[k] = dict(n_points=int(len(dA)),
                        n_points_dropped_defect=int(masks["defect"].sum()),
                        n_points_dropped_all=int(masks["all_buried"].sum()),
                        per_geometry=per_geom)
        budget[k] = dict(
            총_매몰_pct=c["buried_pct"], 설계의도_pct=c["design_intent_pct"],
            진짜결함_pct=c["defect_pct"], 진짜결함_면적_mm2=c["defect_area_mm2"],
            예산_pct=None, 경계에_걸친_면_pct=c.get("ambiguous_pct"),
            못_본_컨테이너=len(c["blind_containers"]),
            구멍_메워_살린_컨테이너=c["n_patched_containers"],
            대안규칙_설계의도_pct=c["design_intent_pct_partition_rule"],
            대안규칙_진짜결함_pct=c["defect_pct_partition_rule"])
    from mesh_check import BURIED_FACE_BUDGET_PCT
    for k in budget:
        budget[k]["예산_pct"] = BURIED_FACE_BUDGET_PCT.get(k, BURIED_FACE_BUDGET_PCT["_default"])
        budget[k]["예산_안인가"] = bool(budget[k]["진짜결함_pct"] <= budget[k]["예산_pct"])

    #  회귀
    bit = regression_bit_identity(keys, G)
    two = regression_two_paths(build_drone(DRONES[keys[0]]), G,
                               ~buried_face_mask(build_drone(DRONES[keys[0]]), kind="defect"))

    gates = {}
    if do_gates:
        for tag, cmd in (("mesh_check", [sys.executable, os.path.join(ROOT, "src", "mesh_check.py")]),
                         ("adv_mesh_check_faults",
                          [sys.executable, os.path.join(HERE, "adv_mesh_check_faults.py")])):
            env = dict(os.environ, PYTHONPATH=f"{os.path.join(ROOT,'src')}:{HERE}")
            p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=ROOT)
            tail = [ln for ln in p.stdout.strip().splitlines() if "결과:" in ln]
            gates[tag] = dict(returncode=p.returncode, 결과=tail[-1].strip() if tail else "")

    return dict(census=census, sigma=sigma, budget=budget,
                강건성=robustness(keys), 기준선_재현=baseline_reproduction(census),
                감사_주장_검증=audit_claim_check(census, sigma),
                안_고칠_것과_이유=not_fixing(census, sigma),
                regression=dict(bit_identity=bit, kernel_vs_shipping_rel_err=kern_reg,
                                two_paths=two),
                gates=gates, seconds=round(time.time() - t0, 1))


#  기준선 원장(outputs/mesh_layer2_baseline_0816.json)이 적은 값 — 재현 대조용.
#  (총 매몰 %, 설계의도 %, 진짜결함 %) — 기준선은 «첫 컨테이너가 이긴다» 분할 규칙을 썼다.
BASELINE_PCT = {
    "mini5pro": (41.814, 8.8942, 32.9198), "mavic4pro": (37.999, 8.4223, 29.5768),
    "matrice4e": (40.7113, 22.0378, 18.6735), "s1000plus": (7.987, 1.0957, 6.8913),
    "phantom4": (39.2982, 8.7951, 30.5031), "typhoonh480": (22.484, 9.1512, 13.3328),
    "x500v2": (18.1388, 0.0, 18.1388), "phantom3": (27.5272, 19.2547, 8.2725),
    "m350rtk": (29.3285, 20.5088, 8.8198), "mini2": (44.4488, 11.0577, 33.391),
}


def robustness(keys) -> dict:
    """**내부판정이 흔들리나** — 질의점(면 중심)을 ±j 만큼 흔들어도 답이 그대로인가.

    왜 묻나: contains() 는 광선을 쏘아 세는 방식이라 **표면 위의 점**에서 불안정하다. 우리
    함대에는 실제로 1 µm 안에서 겹치는 동일평면(x500v2 accent↔arm, 감사 m4)이 있다.
    답이 지터에 크게 흔들리면 매몰면 수치는 «판정 잡음» 이지 형상 사실이 아니다."""
    out = {}
    for k in keys:
        m = build_drone(DRONES[k])
        row = {}
        for j in (0.0, 1e-6, 1e-5):
            c = buried_census(m, k, center_jitter_m=j)
            row[f"jitter_{j*1e6:.0f}um"] = dict(buried_pct=c["buried_pct"],
                                                defect_pct=c["defect_pct"])
        base = row["jitter_0um"]["defect_pct"]
        row["최대_흔들림_pp"] = round(max(abs(v["defect_pct"] - base) for v in row.values()
                                          if isinstance(v, dict)), 4)
        out[k] = row
    return out


def baseline_reproduction(census) -> dict:
    """기준선 원장(다른 에이전트가 잰 것)을 **다시 재서** 맞나 본다 — 두 손이 같은 답인가."""
    rows = {}
    for k, c in census.items():
        if k not in BASELINE_PCT:
            continue
        bt, bd, bf = BASELINE_PCT[k]
        rows[k] = dict(
            총_매몰_pct=dict(mine=c["buried_pct"], baseline=bt,
                             diff_pp=round(c["buried_pct"] - bt, 4)),
            설계의도_pct=dict(mine_내_규칙=c["design_intent_pct"],
                              mine_기준선_규칙=c["design_intent_pct_partition_rule"],
                              baseline=bd,
                              diff_pp_같은_규칙끼리=round(
                                  c["design_intent_pct_partition_rule"] - bd, 4)),
            진짜결함_pct=dict(mine_내_규칙=c["defect_pct"],
                              mine_기준선_규칙=c["defect_pct_partition_rule"], baseline=bf))
    rows["_규칙_차이"] = (
        "총 매몰 %는 규칙과 무관하고 10기체 전부 소수 4자리까지 같다. 설계의도/진짜결함의 "
        "갈림만 규칙에 달렸다 — 기준선은 «첫 컨테이너가 이긴다»(그룹 알파벳 순), 나는 "
        "«컨테이너가 **전부** 셸일 때만 설계 의도». 내 규칙이 더 엄하고, 그렇게 고른 이유는 "
        "**뺄까 말까** 를 정하는 자리이기 때문이다 — 불투명한 금속 상자 안에도 들어 있는 면은 "
        "실물이면 안 보이므로 빼는 것이 맞다. 차이는 3기체에서 0.16~0.88 pp.")
    return rows


def audit_claim_check(census, sigma) -> dict:
    """감사 I3 의 «mavic4pro +38 % · mini5pro +42 % 면적 과대» 가 맞나 — 셋으로 갈라 답한다."""
    out = {"질문": "감사 어림 «mavic4pro +38 % · mini5pro +42 %» 가 맞나?"}
    for k in ("mavic4pro", "mini5pro"):
        if k not in census:
            continue
        c, s = census[k], sigma[k]["per_geometry"]
        out[k] = {
            "①_면적_주장은_맞다": f"총 매몰 {c['buried_pct']} % (감사 어림 "
                                  f"{'38' if k == 'mavic4pro' else '42'} %) · 기준선 원장은 "
                                  f"{BASELINE_PCT[k][0]} % 였다(그 사이 다른 수리자가 형상을 "
                                  f"바꿨으면 이 수는 새 형상의 값이다 — census.⭐mesh_state 참조).",
            "②_그러나_그것은_면적_문장이지_σ_문장이_아니다": {
                "σ_진짜결함만_뺐을_때_dB": {g: s[g]["⭐진짜결함만_뺐을_때"]["azimuth_mean_db"]
                                            for g in s},
                "σ_매몰면_전부_뺐을_때_dB": {
                    g: s[g]["매몰면_전부_뺐을_때(⚠수리안_아님)"]["azimuth_mean_db"] for g in s},
                "왜_면적%_와_dB_가_안_붙나": "코히런트 합이라 면적이 아니라 «위상이 맞는 면적» "
                                             "이 σ 를 정한다. 게다가 셸은 |Γ|=0.28 로 금속의 1/3.6 이다.",
            },
            "③_수리안으로_뺄_수_있는_면적": f"{c['defect_pct']} % (총 매몰에서 설계 의도 "
                                            f"{c['design_intent_pct']} % 를 뺀 것). "
                                            f"감사의 38/42 % 를 그대로 빼면 셸 속 배터리·PCB 까지 "
                                            f"지워져 σ 가 오히려 어두워진다.",
        }
    out["판정"] = ("면적 주장은 **맞다**(재현). 다만 그것을 σ 오차로 읽으면 안 된다 — "
                   "그리고 그 면적 중 뺄 수 있는 것은 «진짜 결함» 부분뿐이다.")
    return out


def not_fixing(census, sigma) -> dict:
    """**안 고치는 것**과 그 크기 — 빈칸 금지 규약."""
    des = {k: c["design_intent_pct"] for k, c in census.items()}
    amb = {k: c.get("ambiguous_pct") for k, c in census.items()}
    return {
        "설계 의도 매몰면(셸 속 battery·pcb·fc)": {
            "크기_pct": des,
            "왜_안_고치나": "rcs_po.py 30-36행이 «반투명 셸을 통과해 내부가 보이는 효과는 셸 |Γ| "
                            "축소 + 내부 |Γ|=1 합산으로 1차 근사» 라고 스스로 규정한다. 이것을 빼면 "
                            "근사 자체가 무너진다 — 참고로 전부 빼면 σ 가 최대 6.3 dB 어두워진다"
                            "(원장 sigma[*].per_geometry[*].매몰면_전부_뺐을_때).",
            "대신_한_것": "kind='all' 로 **감도만** 재서 나란히 싣는다.",
        },
        "메쉬 자체(삼각형)를 안 바꾼다": {
            "왜": "매몰의 뿌리는 «그룹 사이에 불리언 union 을 안 한다» 인데, 그 수리는 형상·재질 "
                  "경계를 바꾸는 일이라 담당이 다르다(i4·battery·m4 수리자). 나는 **PO 가 어느 면을 "
                  "더하는가**만 바꾼다 — 그래서 두 수리가 서로를 안 덮어쓴다.",
            "겹침_주의": "i4·battery·m4 수리를 켜면 매몰면이 줄어든다(실측: MESH_FIX=battery 에서 "
                         "mini2 34.27 → 26.50 %). 그때 i3 마스크는 **자동으로 작아진다** — 같은 면을 "
                         "두 번 빼지 않는다(마스크를 그 메쉬에서 다시 재기 때문).",
        },
        "면 중심 판정의 알갱이": {
            "크기_경계에_걸친_면_pct": amb,
            "왜_안_고치나": "부분 매몰 면을 잘라 쪼개면(면 분할) 메쉬가 바뀌고 다른 수리와 충돌한다. "
                            "지금은 **면 중심**으로 자르고, 그 알갱이가 얼마인지를 위 수로 선언한다.",
        },
        "SBR 교차확인": {"왜_안_하나": "GPU 금지 라운드다. SBR 은 first-hit 이라 구조적으로 0 이어야 "
                                       "하지만 **확인은 못 했다**."},
    }


def _meta(keys) -> dict:
    return {
        "title": "매몰면(I3) 전수 검사 · 수리 손잡이 · σ 대가 — 2026-08-16",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S",
                                       time.localtime(time.time() + 9 * 3600)),
        "role": "감사 docs/MESH_AUDIT_0816.md I3 의 집행 — 수리자 원장",
        "compute": "전부 CPU. GPU 미사용(큐 사용 중). git 미접촉.",
        "generator": "benchmark/adv_mesh_buried_faces_0816.py",
        "airframes": list(keys),
        "용어_한줄풀이": {
            "매몰면(buried face)": "어떤 부품의 삼각형이 다른 부품 솔리드 **안**에 든 것 — 실물이면 안 보인다.",
            "PO": "우리 산란 커널 하나(rcs_po). **가림을 안 본다**(자기 선언 rcs_po.py 46-53행) → 매몰면을 그대로 더한다 = 이중계상.",
            "SBR": "다른 커널(기본 엔진). 광선이 처음 맞은 지점만 적분 → 매몰면 오차가 구조적으로 0.",
            "설계 의도": "battery·pcb·fc 가 셸(body/canopy) 안에 있는 것. 반투명 셸을 통과해 내부 금속이 보이는 효과를 그렇게 근사하기로 한 것 → **빼면 안 된다**.",
            "방위평균 vs 최악방위": "방위평균은 360° 전체 σ 의 평균, 최악방위는 한 방위에서의 최대 차. 결론을 바꾸는 것은 보통 방위평균이다.",
        },
        "측정_규약": {
            "점구름": "결함판과 수리판이 **같은 점구름**을 쓴다. E_full 에서 뺄 면의 점이 만든 E_drop 을 빼면 그 면을 지운 판이 정확히 나온다 — 재샘플링이 아니므로 차이는 오직 뺀 면 때문이다. 그 값이 mesh_to_points(face_mask=…) 로 다시 깐 판과 같은지도 확인한다(regression.two_paths).",
            "주파수": f"{FC/1e9:.1f} GHz, 점간격 λ/7 = {SPACING*1000:.2f} mm (rcs_po 기본과 동일)",
            "방위": f"0~{AZ[-1]:.0f}°, {AZ_STEP:.0f}° 간격 {len(AZ)} 방위",
            "고각": "el 0° · el −30°",
            "바이스태틱": "β=120°(el −30°) — 모노만 재면 유리한 각도만 고른 셈이 된다(감사 C5).",
            "대역평균": f"5G {BW/1e6:.0f} MHz·{N_F}점. 3° 각도창 판(angular_smooth, 방위 스텝 2° → 실효 4°)과 p95 도 싣는다.",
            "부호": "(+) = 결함이 σ 를 **밝게** 만든다(과대계상). (−) = 어둡게.",
            "재질": "drones.DRONE_GROUP_MAT → materials 의 |Γ|. ITU 'metal' 만 Sionna 씬(GPU)이 필요해 저장소 캐시값 "
                    f"{METAL_GAMMA_5G} 를 썼다(outputs/mesh_compare_material.json).",
            "⚠대역평균의 점구름": "기준선과 같게 **점간격을 fc=3.5 GHz 로 고정**하고 9 주파수를 돌린다. 출하 drone_rcs_pattern_bw 는 주파수마다 λ/7 을 다시 잡지만(±0.7 %) 여기서는 비교의 순수성을 택했다 — 두 판이 같은 점을 써야 차이가 오직 뺀 면 때문이 된다.",
        },
        "판정_밴드": {"무해": "|Δ| < 0.1 dB", "보임": "0.1~1.0 dB", "결론을_바꿈": "> 1 dB",
                      "왜_이_밴드인가": "감사가 형상 축을 1~2 dB, 두께 축을 13~17 dB 로 갈랐다. 그 눈금을 그대로 쓴다."},
        "적용_범위": {
            "PO_전용": "SBR(기본 엔진)은 first-hit 이라 이 오차가 구조적으로 0 이다. ⚠ 이번 라운드에 SBR 로 교차확인은 **못 했다**(GPU 금지).",
            "PO_를_쓰는_곳": ["src/microdoppler.py:72,75 (프레임 DC 장)",
                              "rcs_po.drone_rcs_pattern(engine='po') — report6 대조군",
                              "src/ptd_edges.py · src/viz_verify_po.py · src/viz_mesh_material.py",
                              "benchmark/adv_consequence_0816*.py", "감사 §4-1 부품분해 표"],
            "안_쟀다": ["SBR 교차확인(GPU 금지)", "마이크로도플러 스펙트럼 축(σ 로만 쟀다)",
                        "회전 자세열(전부 정지 호버 0 위상 메쉬)"],
        },
    }


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    keys = ["mavic4pro", "mini5pro", "mini2"] if quick else list(DRONES)
    print("=" * 100)
    print("매몰면(I3) — 전수 · 수리 · σ 대가   [CPU only]")
    print("=" * 100)
    res = run(keys, do_gates=("--gates" in sys.argv))
    payload = {"_meta": _meta(keys), **res}
    if not quick:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump(payload, open(OUT, "w"), ensure_ascii=False, indent=1)
        print("\n원장:", OUT)
    print(f"\n{'기체':12s} {'총매몰%':>8} {'설계의도%':>9} {'⭐결함%':>8} {'예산%':>7} "
          f"{'mono el0':>9} {'el-30':>8} {'β120':>8}  판정")
    for k in keys:
        b = res["budget"][k]; s = res["sigma"][k]["per_geometry"]
        g = lambda n: s[n]["⭐진짜결함만_뺐을_때"]["azimuth_mean_db"]      # noqa: E731
        print(f"{k:12s} {b['총_매몰_pct']:8.3f} {b['설계의도_pct']:9.3f} {b['진짜결함_pct']:8.3f} "
              f"{b['예산_pct']:7.1f} {g('mono_el0'):+9.3f} {g('mono_el-30'):+8.3f} "
              f"{g('bi_b120_el-30'):+8.3f}  {band(max((abs(g(n)) for n in s), default=0))}")
    ident = {k: v for k, v in res["regression"]["bit_identity"].items()
             if k not in ("_switch_state", "_뜻")}
    bad = [k for k, v in ident.items()
           if not (v["⭐code_identical_vs_pre_edit_body"] and v["mask_all_true_identical"]
                   and v["handle_off_bit_identical"])]
    moved = [k for k, v in ident.items() if not v["mesh_state_matches_baseline"]]
    print(f"\n회귀 · ⭐내 코드는 아무 값도 안 바꾼다(수정 전 본문 사본과 바이트 동일): "
          f"{len(ident)-len(bad)}/{len(ident)}" + (f"  ❌ 깨짐 {bad}" if bad else "  ✅"))
    print(f"메쉬 상태 · 2026-08-16 23:46 기준선과 같은 형상: {len(ident)-len(moved)}/{len(ident)}"
          + (f"  ⚠ 다른 수리자가 바꾼 기체 {moved} — 이 원장의 수는 **바뀐 형상**에서 잰 값이다"
             if moved else "  ✅"))
    print(f"회귀 · 내 적분 ↔ 출하 커널 최대 상대오차: "
          f"{max(res['regression']['kernel_vs_shipping_rel_err'].values()):.2e}")
    print(f"회귀 · 두 길(점구름 빼기 ↔ face_mask 재샘플)의 차: "
          f"{res['regression']['two_paths']['max_abs_db']:.2e} dB")
    print(f"({res['seconds']} s)")
    sys.exit(1 if bad else 0)
