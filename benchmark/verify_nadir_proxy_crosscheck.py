# -*- coding: utf-8 -*-
"""
verify_nadir_proxy_crosscheck.py — 나딧 잔여를 **격자 없는 대리모형**과 맞대본다 (CPU 전용).

⛔GPU 미사용. sbr_field·PathSolver 를 부르지 않는다. 평면패싯 PO 대리모형만 numpy 로 돈다.

■ 왜 필요한가
S3 에서 드러난 사실: **PathSolver 의 나딧 요동도 플래시 빗살에 97~99 % 몰려 있다.**
씨앗이 고정(seed=1)이라 표본화 오차가 «자세의 결정론적 함수» 이고 자세는 로터 주기로
반복하므로, 표본잡음도 빗살에 얹힌다. ⇒ **빗살 구조는 물리의 증거가 아니다.** 두 팔 다.
가르는 건 두 가지뿐이다 — (a) 예산 사다리, (b) **격자가 아예 없는 독립 모형과의 상관**.

■ 대리모형 (verify_nadir_flash.geometry 와 같은 식, 여기서 재현·확장)
    E_proxy(자세) = Σ_facet (n·û)_+ · area · exp(−j2k·|c_facet − p_tx|)
  광선격자 없음·재질 없음·가림 없음·다중반사 없음. 절대레벨은 못 비교, AC/DC 는 무차원이라 비교 가능.
  평면파판은 exp(−j2k·(c·û)) 로 바꾼다 — 나딧에서 z 축 회전은 c·û 도 n·û 도 안 바꾸므로
  **원리적으로 정확히 상수**여야 한다.

■ 출력  outputs/verify_nadir_proxy_crosscheck.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

ROOT = "/workspace/sionna"
for _p in (f"{ROOT}/src", f"{ROOT}/benchmark"):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ["CUDA_VISIBLE_DEVICES"] = ""

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
SW = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz", allow_pickle=True)
GS = json.load(open(f"{ROOT}/outputs/verify_po_elev_gridscale.json"))
NF = json.load(open(f"{ROOT}/outputs/verify_nadir_flash.json"))

FC, RANGE_M = 3.5e9, 10.0
K = 2 * np.pi * FC / 2.998e8
PRF, N = float(TJ["prf_hz"]), int(TJ["n"])
FFL = float(TJ["f_flash_hz"])
RPMS = np.asarray(TJ["rpm_per_rotor"], float)


def facets(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    nn = np.cross(b - a, c - a)
    ar2 = np.linalg.norm(nn, axis=1)
    return nn / (ar2[:, None] + 1e-300), 0.5 * ar2, (a + b + c) / 3.0


def acdc(x):
    x = np.asarray(x, complex)
    return float(10 * np.log10(np.mean(np.abs(x / x.mean() - 1.0) ** 2) + 1e-300))


def rel(x):
    x = np.asarray(x, complex)
    return x / x.mean() - 1.0


def cxcorr(a, b):
    """복소 상관의 크기. 위상규약이 팔마다 달라(+j vs −j) 켤레도 같이 재고 큰 쪽을 쓴다."""
    a = np.asarray(a, complex) - np.mean(a)
    b = np.asarray(b, complex) - np.mean(b)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0, "n/a"
    r1 = abs(np.vdot(a, b)) / (na * nb)
    r2 = abs(np.vdot(a, np.conj(b))) / (na * nb)
    return (float(r1), "direct") if r1 >= r2 else (float(r2), "conjugated")


def comb_mask(n, prf=PRF, ffl=FFL, half=12.0, nh=60):
    fq = np.fft.fftfreq(n, 1 / prf)
    m = np.zeros(n, bool)
    for k in range(1, nh + 1):
        m |= np.abs(np.abs(fq) - k * ffl) <= half
    return m


def band(x, msk):
    """주파수 마스크를 통과시킨 성분."""
    return np.fft.ifft(np.where(msk, np.fft.fft(np.asarray(x, complex)), 0))


# ═══ 대리모형 시계열 계산 ════════════════════════════════════════════════════
from articulated_fast import FastPoser, rotor_phases                  # noqa: E402
from drones import DRONES                                             # noqa: E402

fp = FastPoser(DRONES[TJ.get("drone", "matrice4e")])
f = np.asarray(fp.f)
gg = np.asarray(fp.g)
isp = gg == "prop"
c0 = 0.5 * (fp.v.min(0) + fp.v.max(0))
u90 = np.array([0.0, 0.0, -1.0])
ph = rotor_phases(np.arange(N) / PRF, RPMS, fp.dirs)

RS = [10.0, 20.0, 40.0, 80.0, 160.0]
Ssph = {R: np.zeros(N, complex) for R in RS}
Spl = np.zeros(N, complex)
Sprop = np.zeros(N, complex)
Sbody = np.zeros(N, complex)
t0 = time.time()
for i in range(N):
    v = fp.pose(ph[i]).v
    nn, ar, cen = facets(v, f)
    w = np.maximum(nn @ u90, 0.0) * ar
    for R in RS:
        d = np.linalg.norm(cen - (c0 + R * u90), axis=1)
        q = w * np.exp(-1j * 2 * K * d)
        Ssph[R][i] = q.sum()
        if R == 10.0:
            Sprop[i] = q[isp].sum(); Sbody[i] = q[~isp].sum()
    Spl[i] = (w * np.exp(-1j * 2 * K * (cen @ u90))).sum()
    if i and i % 1024 == 0:
        print(f"  proxy {i}/{N}  {time.time()-t0:.0f}s", flush=True)
print(f"  proxy done {time.time()-t0:.0f}s", flush=True)

P10 = Ssph[10.0]

J = {"_meta": {
    "generator": "benchmark/verify_nadir_proxy_crosscheck.py",
    "gpu_ko": "⛔미사용. numpy 평면패싯 PO 대리모형만 CPU 로 돌렸다.",
    "question_ko": ("빗살 구조가 두 팔 모두에서 나타나므로(씨앗·격자가 자세의 결정론적 함수라 "
                    "표본오차도 로터 주기로 반복) 빗살은 물리의 증거가 못 된다. 대신 "
                    "**격자가 아예 없는 독립 모형과의 상관**으로 가른다."),
    "proxy_ko": "E = Σ (n·û)_+ · area · exp(−j2k·|c−p_tx|). 격자·재질·가림·다중반사 없음.",
    "n_poses": N, "prf_hz": PRF, "fc_hz": FC, "f_flash_hz": FFL,
    "n_facets": int(f.shape[0]),
}}

# ── 1. 대리모형 자체 (원장 재현 확인) ───────────────────────────────────────
geo = NF["C_D_geometry"]
J["P1_proxy_self"] = {
    "plane_wave_far_field_ac_db": round(acdc(Spl), 2),
    "plane_wave_ledger_db": geo["nadir_plane_wave_ac_over_dc_db"],
    "why_exactly_zero_ko": ("나딧에서 시선 û = −ẑ 다. 로터는 z 축 둘레로 돈다 → 면 법선의 "
                            "z 성분도, 면 중심의 z 좌표도 **안 변한다**. 평면파 위상은 c·û 뿐이라 "
                            "합이 자세와 무관하게 상수다. ⇒ 원거리장 나딧 마이크로도플러는 "
                            "**정확히 0** 이다. 수치로 −300 dB 대."),
    "spherical_by_range_db": {f"{int(R)}m": round(acdc(Ssph[R]), 2) for R in RS},
    "spherical_10m_ledger_db": geo["nadir_spherical_10m_ac_over_dc_db"],
    "db_per_octave_of_range": round(acdc(Ssph[160.0]) - acdc(Ssph[10.0]), 2),
    "octaves": 4,
    "power_law_exponent_vs_range": round(
        (acdc(Ssph[160.0]) - acdc(Ssph[10.0])) / (10 * np.log10(16.0)), 3),
    "props_only_db": round(acdc(Sprop), 2),
    "body_only_db": round(acdc(Sbody), 2),
    "reading_ko": ("동체만 남기면 나딧 변조가 사라지고(−300 dB 대) 프로펠러만 남기면 "
                   "전체와 같다 ⇒ 대리모형의 나딧 변조는 **전적으로 회전날개** 때문이다."),
}

# ── 2. 우리 팔 × 대리모형 상관, 격자 사다리 위에서 ─────────────────────────
runs = {}
for tag, r in GS["runs"].items():
    E = np.asarray(r["E_re"], float) + 1j * np.asarray(r["E_im"], float)
    nn_ = E.size
    m = comb_mask(nn_)
    dE, dP = rel(E), rel(P10[:nn_])
    rc, cv = cxcorr(dE, dP)
    rcomb, _ = cxcorr(band(dE, m), band(dP, m))
    roff, _ = cxcorr(band(dE, ~m), band(dP, ~m))
    runs[tag] = dict(
        div=r["div"], spacing_mm=round(r["spacing_m"] * 1000, 4), n_poses=nn_,
        ac_over_dc_db=round(acdc(E), 2),
        proxy_ac_over_dc_db=round(acdc(P10[:nn_]), 2),
        corr_with_proxy=round(rc, 4), corr_convention=cv,
        corr_on_comb=round(rcomb, 4), corr_off_comb=round(roff, 4),
        comb_share_of_ac=round(float(np.mean(np.abs(band(dE, m)) ** 2) /
                                     np.mean(np.abs(dE) ** 2)), 4),
        explained_power_share=round(rc ** 2, 4),
    )
full = np.asarray(SW["ours/el-90"], complex)
mfull = comb_mask(N)
dF, dP = rel(full), rel(P10)
rf, cvf = cxcorr(dF, dP)
rfc, _ = cxcorr(band(dF, mfull), band(dP, mfull))
rfo, _ = cxcorr(band(dF, ~mfull), band(dP, ~mfull))
J["P2_ours_vs_proxy"] = {
    "note_ko": ("⭐격자를 조이면 대리모형(=격자 없는 물리)과의 상관이 **오르는가**. "
                "오르면 남는 것이 물리라는 뜻이다."),
    "grid_ladder": [runs[k] for k in sorted(runs, key=lambda t: GS["runs"][t]["div"])],
    "full_sweep_lambda12_4096poses": dict(
        ac_over_dc_db=round(acdc(full), 2),
        proxy_ac_over_dc_db=round(acdc(P10), 2),
        corr_with_proxy=round(rf, 4), corr_convention=cvf,
        corr_on_comb=round(rfc, 4), corr_off_comb=round(rfo, 4),
        ledger_comb_corr=geo["proxy_vs_measured_split"]["comb"]["corr_with_proxy"],
        ledger_comb_share_db=geo["proxy_vs_measured_split"]["comb"]["share_of_measured_ac_db"]),
}

# ── 3. PathSolver × 대리모형 상관 ───────────────────────────────────────────
ps = {}
for arm, spp in (("sionna", 11_111_111), ("sionna_p250000000", 250_000_000)):
    key = f"{arm}/el-90"
    E = np.asarray(SW[key], complex)
    dE = rel(E)
    rc, cv = cxcorr(dE, dP)
    rcomb, _ = cxcorr(band(dE, mfull), band(dP, mfull))
    # 우리 팔과의 상관도 — 두 팔이 같은 물리를 보고 있나
    ro, cvo = cxcorr(dE, dF)
    ps[arm] = dict(spp=spp, ac_over_dc_db=round(acdc(E), 2),
                   corr_with_proxy=round(rc, 4), corr_convention=cv,
                   corr_on_comb_with_proxy=round(rcomb, 4),
                   explained_power_share=round(rc ** 2, 4),
                   corr_with_our_kernel=round(ro, 4), corr_conv_vs_ours=cvo,
                   comb_share_of_ac=round(float(np.mean(np.abs(band(dE, mfull)) ** 2) /
                                                np.mean(np.abs(dE) ** 2)), 4))
# 통제군 — 대리모형 vs 무작위 위상 잡음 (같은 길이·같은 빗살 마스크)
rng = np.random.default_rng(0)
ctrl = []
for _ in range(24):
    z = rng.normal(size=N) + 1j * rng.normal(size=N)
    ctrl.append(cxcorr(z, dP)[0])
J["P3_pathsolver_vs_proxy"] = {
    "note_ko": ("PathSolver 의 나딧 요동이 «격자 없는 물리» 와 상관이 있나. "
                "빗살에 몰려 있어도 물리와 상관이 없으면 그것은 자세동기 **표본오차**다."),
    "arms": ps,
    "white_noise_control": {
        "n_draws": len(ctrl),
        "corr_mean": round(float(np.mean(ctrl)), 4),
        "corr_p95": round(float(np.percentile(ctrl, 95)), 4),
        "meaning_ko": "같은 길이의 무작위 복소 잡음이 대리모형과 내는 상관 — 우연 수준의 눈금.",
    },
}

# ── 4. 자세동기 표본오차가 왜 빗살에 얹히나 (설명 + 수치 근거) ──────────────
mE = comb_mask(N)
J["P4_why_comb_is_not_evidence"] = {
    "mechanism_ko": ("PathSolver 는 seed=1 고정이고 우리 팔은 격자가 얼려 있다. 둘 다 표본화가 "
                     "**자세의 결정론적 함수**다. 자세는 로터 회전으로 (거의) 주기적이므로 "
                     "표본오차도 같은 주기를 갖고, 주파수축에서 **플래시 빗살에 정확히 얹힌다**. "
                     "⇒ 빗살 구조는 두 팔 모두에서 물리의 증거가 못 된다."),
    "comb_power_share": {
        k: round(float(np.mean(np.abs(band(rel(np.asarray(SW[k], complex)), mE)) ** 2) /
                       np.mean(np.abs(rel(np.asarray(SW[k], complex))) ** 2)), 4)
        for k in ("ours/el-90", "sionna/el-90", "sionna_p250000000/el-90", "ours/el+0")},
    "comb_bin_fraction": round(float(mE.mean()), 4),
    "counter_example_ko": ("반례가 하나 있다 — sionna el+0 최고예산(4,000 M)에서는 빗살 비중이 "
                           "빈 비중과 같아 **백색**이다. 거기서는 확산반사 표본이 자세와 무관하게 "
                           "새로 뽑혀 자세동기가 깨진다."),
}

json.dump(J, open(f"{ROOT}/outputs/verify_nadir_proxy_crosscheck.json", "w"),
          ensure_ascii=False, indent=1)
print("wrote", f"{ROOT}/outputs/verify_nadir_proxy_crosscheck.json")
np.savez_compressed(f"{ROOT}/outputs/verify_nadir_proxy_crosscheck.npz",
                    proxy_plane=Spl, proxy_props=Sprop, proxy_body=Sbody,
                    **{f"proxy_sph{int(R)}": Ssph[R] for R in RS})
print("wrote npz")
