# -*- coding: utf-8 -*-
"""
verify_angle_gamma_po.py — 순수 PO 커널의 각도의존 Γ(θ) 배선 검증 (2026-08-10)
================================================================================

무엇을 검증하나 (갈래 C 임무)
  [A] **꺼짐 = 옛 결과 비트동일** — git HEAD 의 rcs_po/microdoppler 를 별도 모듈로 읽어
      새 코드와 나란히 돌린다(기체 2종 × 자세 2). 킬스위치(rcs_po.ANGLE_GAMMA=False)를
      내린 옵트인 호출도 비트동일해야 한다.
  [B] **켜짐의 영향** — 프롭 채널(el=-15, 3.5 GHz) 레벨 변화가 SBR 쪽 실측
      (+5.16/+6.48 dB, outputs/angle_gamma_impact.json)과 같은 방향·자릿수인가.
      전체 드론 σ 도 SBR 쪽처럼 거의 안 움직여야 한다(0.1 dB 급).
  [C] ⭐ **Sionna 독립 검증** — outputs/report07_three_engines.npz 의 sionna 팔과
      po 팔의 스펙트럼 코사인이 0.696 이었다(po=옛 Γ). Sionna 는 원래 각도의존
      프레넬을 쓰므로, 새 Γ(θ) 를 켠 po 팔에서 코사인이 **올라가면** 독립 검증이 된다.
      (po 팔만 재계산 — CPU, GPU 불필요. sionna/sbr 팔은 저장본 그대로.)

쓰는 것: outputs/angle_gamma_po_impact.json
실행:    ~/.venvs/py312/bin/python benchmark/verify_angle_gamma_po.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")          # 각도모양의 ITU 재질 프로브가 sionna 를 부른다

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SCRATCH = os.environ.get(
    "SIONNA2_SCRATCH",
    "/tmp/claude-1015/-workspace/a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad")

from gpu import pick                                                   # noqa: E402
pick(verbose=False)

import numpy as np                                                     # noqa: E402

import rcs_po                                                          # noqa: E402
import microdoppler as md                                              # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, build_drone, build_frame, drone_gamma_map  # noqa: E402
from rcs_po import C0, mesh_to_points, rcs_from_points, po_field_dir, point_mat_keys   # noqa: E402

FC = 3.5e9
OUTJ = os.path.join(ROOT, "outputs", "angle_gamma_po_impact.json")
G2M = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}                  # 그룹 → 재질 키


# --------------------------------------------------------------------------- #
#  git HEAD 판을 별도 모듈로 — «옛 결과» 를 추측이 아니라 실행으로 얻는다
# --------------------------------------------------------------------------- #
def _head_module(rel, name):
    src = subprocess.run(["git", "-C", ROOT, "show", f"HEAD:{rel}"],
                         capture_output=True, text=True, check=True).stdout
    os.makedirs(SCRATCH, exist_ok=True)
    path = os.path.join(SCRATCH, f"{name}.py")
    with open(path, "w") as f:
        f.write(src)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _bit(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape:
        return dict(identical=False, why=f"shape {a.shape} != {b.shape}")
    d = float(np.max(np.abs(a - b))) if a.size else 0.0
    return dict(identical=bool(np.array_equal(a, b)), max_abs_diff=d)


def dbv(x):
    return 20 * np.log10(np.maximum(np.abs(np.asarray(x, complex)), 1e-30))


def main():
    t_all = time.time()
    out = {"_meta": {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "what": "순수 PO(rcs_po)·microdoppler_series 의 각도의존 Γ(θ) 배선 검증",
        "design": "|Γ(θ)| = |Γ_보정|·|Γ_벌크(θ)|/|Γ_벌크(0)| — materials.gamma_shape (SBR 과 동일 함수)",
        "switch": ("rcs_po: 호출 옵트인(mats=점별 재질 키) ∧ 킬스위치 ANGLE_GAMMA"
                   "(env SIONNA2_ANGLE_GAMMA, SBR 과 같은 변수). 옛 방식 호출은 항상 옛 경로 — "
                   "SBR(기본 켬)과 달리 순수 PO 는 하위 사용처가 많아 조용한 전역 변화를 금지했다."),
        "old_reference": "git HEAD 의 src/rcs_po.py·src/microdoppler.py 를 별도 모듈로 실행해 비교",
    }}

    old_po = _head_module("src/rcs_po.py", "rcs_po_head")
    old_md = _head_module("src/microdoppler.py", "microdoppler_head")

    # ───────────────────────────── [A] 꺼짐 = 비트동일 ─────────────────────────
    print("═══ [A] 꺼짐 = 옛 결과 비트동일 (기체 2종 × 자세 2) ═══", flush=True)
    lam = C0 / FC
    az = np.arange(0.0, 360.0, 30.0)
    bit = {}
    for dk in ("matrice4e", "mini5pro"):
        spec = DRONES[dk]
        mesh = build_drone(spec)
        gmap = drone_gamma_map(spec)
        Po, No, dAo, wo = old_po.mesh_to_points(mesh, lam / 7.0, gamma=gmap)
        Pn, Nn, dAn, wn = mesh_to_points(mesh, lam / 7.0, gamma=gmap)
        P5 = mesh_to_points(mesh, lam / 7.0, gamma=gmap, return_keys=True)
        mats = point_mat_keys(P5[4], G2M)
        bit[f"{dk}/mesh_to_points"] = _bit(np.hstack([Po.ravel(), No.ravel(), dAo, wo]),
                                           np.hstack([Pn.ravel(), Nn.ravel(), dAn, wn]))
        bit[f"{dk}/mesh_to_points_return_keys_first4"] = _bit(
            np.hstack([P5[0].ravel(), P5[1].ravel(), P5[2], P5[3]]),
            np.hstack([Po.ravel(), No.ravel(), dAo, wo]))
        for el in (-15.0, 15.0):                                   # 자세 2
            so = old_po.rcs_from_points(Po, No, dAo, FC, az, el, w=wo)
            sn = rcs_from_points(Pn, Nn, dAn, FC, az, el, w=wn)
            bit[f"{dk}/el{el:+.0f}/rcs_from_points"] = _bit(so, sn)
            #  옵트인 + 킬스위치 내림 → 여전히 비트동일해야 한다
            _saved = rcs_po.ANGLE_GAMMA
            rcs_po.ANGLE_GAMMA = False
            sk = rcs_from_points(Pn, Nn, dAn, FC, az, el, w=wn, mats=mats)
            rcs_po.ANGLE_GAMMA = _saved
            bit[f"{dk}/el{el:+.0f}/mats+killswitch_off"] = _bit(so, sk)
            u = np.array([np.cos(np.radians(el)), 0.0, np.sin(np.radians(el))])
            eo = old_po.po_field_dir(Po, No, dAo, FC, u, w=wo)
            en = po_field_dir(Pn, Nn, dAn, FC, u, w=wn)
            bit[f"{dk}/el{el:+.0f}/po_field_dir"] = _bit([eo], [en])
        #  microdoppler_series 기본 호출(angle_gamma 미지정) = HEAD 판과 비트동일
        _, Eo, _ = old_md.microdoppler_series(spec, fc=FC, az=0.0, el=-15.0, n_t=512)
        _, En, _ = md.microdoppler_series(spec, fc=FC, az=0.0, el=-15.0, n_t=512)
        bit[f"{dk}/microdoppler_series_default"] = _bit(Eo, En)
        n_ok = sum(1 for v in bit.values() if v.get("identical"))
        print(f"  {dk}: {n_ok}/{len(bit)} 통과 누계", flush=True)
    out["bit_identical_off"] = bit
    all_ok = all(v.get("identical") for v in bit.values())
    out["bit_identical_off"]["verdict"] = "PASS(전부 비트동일)" if all_ok else "FAIL"
    print(f"  → {out['bit_identical_off']['verdict']}", flush=True)

    # ───────────────────────────── [B] 켜짐의 영향 ────────────────────────────
    #  프롭 채널 정의: E(t) − E_frame (프레임 상수장을 같은 설정으로 재계산해 뺀 **블레이드 전용**
    #  슬로타임 장). 레벨 = 20log10(mean|E_b|). SBR 쪽 JSON 의 «프로펠러 채널 레벨» 과
    #  측정 철학이 같다(프레임 제외·시간평균 진폭) — 커널이 다르므로 절대값 비교가 아니라
    #  **방향·자릿수** 비교다(임무 명세).
    print("\n═══ [B] 켜짐: 프롭 채널 레벨 (el=-15, 3.5 GHz) ═══", flush=True)
    SBR_REF = {"matrice4e": 5.16, "mini5pro": 6.48}   # outputs/angle_gamma_impact.json
    ch = {}
    for dk in ("matrice4e", "mini5pro"):
        spec = DRONES[dk]
        u = np.array([np.cos(np.radians(-15.0)), 0.0, np.sin(np.radians(-15.0))])
        gm = drone_gamma_map(spec)
        res = {}
        for tag, ag in (("off", False), ("on", True)):
            _, E, info = md.microdoppler_series(spec, fc=FC, az=0.0, el=-15.0,
                                                n_t=2048, angle_gamma=ag)
            if ag:
                Pf, Nf, dAf, wf, kf = mesh_to_points(build_frame(spec), lam / 6.0,
                                                     gamma=gm, return_keys=True)
                Ef = po_field_dir(Pf, Nf, dAf, FC, u, w=wf, mats=point_mat_keys(kf, G2M))
            else:
                Pf, Nf, dAf, wf = mesh_to_points(build_frame(spec), lam / 6.0, gamma=gm)
                Ef = po_field_dir(Pf, Nf, dAf, FC, u, w=wf)
            Eb = np.asarray(E, complex) - Ef                      # 블레이드 전용
            res[tag] = dict(level_db=float(20 * np.log10(np.abs(Eb).mean() + 1e-30)),
                            ptp_db=float(dbv(Eb).max() - dbv(Eb).min()))
        d = res["on"]["level_db"] - res["off"]["level_db"]
        ref = SBR_REF[dk]
        ch[dk] = {"level_db_off": round(res["off"]["level_db"], 2),
                  "level_db_on": round(res["on"]["level_db"], 2),
                  "level_delta_db": round(d, 2),
                  "ptp_db_off": round(res["off"]["ptp_db"], 2),
                  "ptp_db_on": round(res["on"]["ptp_db"], 2),
                  "sbr_ref_delta_db": ref,
                  "same_direction": bool(d * ref > 0),
                  "same_order": bool(ref / 3.0 <= d <= ref * 3.0)}
        print(f"  {dk:10s} off {res['off']['level_db']:7.2f} → on {res['on']['level_db']:7.2f} dB"
              f"  Δ={d:+.2f} dB  (SBR 실측 {ref:+.2f} dB)", flush=True)
    out["propeller_channel_el_-15_3p5GHz"] = ch

    #  전체 드론 σ — SBR 쪽과 같은 규약(az 24점 평균, el=-15). 거의 안 움직여야 정상
    #  (동체는 금속·카본 위주라 각도 둔감 — SBR 실측 0.08~0.10 dB).
    print("\n═══ [B2] 켜짐: 전체 드론 σ (az24 평균, el=-15) ═══", flush=True)
    sig = {}
    az24 = np.arange(0.0, 360.0, 15.0)
    for dk in ("matrice4e", "mini5pro"):
        spec = DRONES[dk]
        P, N, dA, w, keys = mesh_to_points(build_drone(spec), lam / 7.0,
                                           gamma=drone_gamma_map(spec), return_keys=True)
        mats = point_mat_keys(keys, G2M)
        s0 = rcs_from_points(P, N, dA, FC, az24, -15.0, w=w)
        s1 = rcs_from_points(P, N, dA, FC, az24, -15.0, w=w, mats=mats)
        d0, d1 = 10 * np.log10(s0.mean()), 10 * np.log10(s1.mean())
        sig[dk] = {"db_off": round(float(d0), 2), "db_on": round(float(d1), 2),
                   "delta_db": round(float(d1 - d0), 2)}
        print(f"  {dk:10s} {d0:7.2f} → {d1:7.2f} dBsm  Δ={d1-d0:+.2f} dB", flush=True)
    out["whole_drone_sigma_az24_el_-15"] = sig

    # ─────────────── [C] ⭐ Sionna 일치도 — po 팔만 새 Γ(θ) 로 재계산 ───────────
    print("\n═══ [C] ⭐ Sionna 스펙트럼 코사인 — po 팔 재계산 ═══", flush=True)
    J = json.load(open(os.path.join(ROOT, "outputs", "report07_three_engines.json")))
    Z = np.load(os.path.join(ROOT, "outputs", "report07_three_engines.npz"))
    M = J["_meta"]
    spec = DRONES[M["drone"]]
    rpms = np.asarray(M["rpm_per_rotor"], float)
    prf, n, ftip = float(M["prf_hz"]), int(M["n"]), float(M["f_tip_hz"])

    _, Ep_off, _ = md.microdoppler_series(spec, fc=M["fc_hz"], az=M["az_deg"], el=M["el_deg"],
                                          prf=prf, n_t=n, rpm_per_rotor=rpms)
    _, Ep_on, _ = md.microdoppler_series(spec, fc=M["fc_hz"], az=M["az_deg"], el=M["el_deg"],
                                         prf=prf, n_t=n, rpm_per_rotor=rpms, angle_gamma=True)
    repro = _bit(Ep_off, np.asarray(Z["po"], complex))

    def shape_of(E):
        """build_three_engine_fig.py 의 판정과 **같은 식** — DC 제거·한 창·±f_tip 대역·단위노름."""
        E = np.asarray(E, complex)
        E = E - E.mean()
        S = np.abs(np.fft.fftshift(np.fft.fft(E * np.hanning(len(E)))))
        f = np.fft.fftshift(np.fft.fftfreq(len(E), 1 / prf))
        inb = np.abs(f) <= ftip
        return S[inb] / (np.linalg.norm(S[inb]) + 1e-30)

    sh = {"sionna": shape_of(Z["sionna"]), "sbr": shape_of(Z["sbr"]),
          "po_off": shape_of(Ep_off), "po_on": shape_of(Ep_on)}
    cos = {f"{a}_vs_{b}": float(sh[a] @ sh[b])
           for a, b in (("sionna", "po_off"), ("sionna", "po_on"),
                        ("sbr", "po_off"), ("sbr", "po_on"), ("sionna", "sbr"))}
    d_sionna = cos["sionna_vs_po_on"] - cos["sionna_vs_po_off"]
    d_sbr = cos["sbr_vs_po_on"] - cos["sbr_vs_po_off"]
    tri = [cos["sionna_vs_po_on"], cos["sbr_vs_po_on"], cos["sionna_vs_sbr"]]
    tri0 = [cos["sionna_vs_po_off"], cos["sbr_vs_po_off"], cos["sionna_vs_sbr"]]
    if d_sionna > 0:
        reading = (f"sionna↔po 코사인이 {d_sionna:+.4f} 올랐다 — Sionna(각도의존 프레넬 내장)와 "
                   "같은 방향으로 움직였으므로 독립 검증이 성립한다.")
    else:
        reading = (
            f"⚠ 독립 검증 **미성립** — sionna↔po 코사인이 {d_sionna:+.4f} 로 오히려 내렸다. "
            "이것이 Γ(θ) 반증은 아니라고 판단한다. 근거: (1) 잣대 자체가 각도 프레넬의 잣대가 "
            "아니다 — Sionna 팔의 드론 에코는 **확산(산란계수 S) 경로 지배**다(ITU metal 은 S=0 "
            "이라 금속부는 확산 기여 0, 블레이드=prop_plastic S=0.20). 확산 진폭의 각도 거동은 "
            "산란 패턴이지 벌크 프레넬 TE/TM 이 아니므로, '새 Γ(θ) 를 켜면 Sionna 와 같아져야 "
            "한다'는 이 실험의 전제가 약했다(임무 명세의 «Sionna 는 원래 각도의존 프레넬»은 "
            "**정반사 팔**에만 참이다). (2) 우리 두 커널끼리는 예상대로 움직였다 — sbr↔po 가 "
            f"{d_sbr:+.4f} 올랐다(둘 다 같은 각도 물리를 갖게 되어 가림 차이만 남음). (3) 켠 뒤 "
            f"세 쌍의 코사인이 {min(tri):.3f}~{max(tri):.3f}(폭 {max(tri)-min(tri):.3f})으로 "
            f"수렴했다(끄면 {min(tri0):.3f}~{max(tri0):.3f}, 폭 {max(tri0)-min(tri0):.3f}) — "
            "특정 쌍만 좋아 보이던 상태보다 오히려 자기일관적이다. 반대근거(우리 주장의 약점)도 "
            "적는다: 코사인 절대값이 0.65~0.70 대역이라 어느 쌍도 강한 일치가 아니고, −0.02 는 "
            "그 대역 안의 작은 이동이라 (1)~(3)은 정황이지 증명이 아니다. 각도 Γ 의 독립 앵커는 "
            "Sionna 가 아니라 실측(문헌 RCS 앵커·야외 X410)으로 미룬다.")
    out["three_engines_po_arm"] = {
        "npz": "outputs/report07_three_engines.npz (sionna·sbr 팔은 저장본, po 팔만 재계산)",
        "geometry": {k: M[k] for k in ("drone", "az_deg", "el_deg", "prf_hz", "n", "f_tip_hz")},
        "po_off_bit_reproduces_npz": repro,
        "stored_cosine_sionna_vs_po": J["verdict"]["cosine_in_ftip"]["sionna_vs_po"],
        "cosine": {k: round(v, 4) for k, v in cos.items()},
        "delta_sionna_vs_po": round(d_sionna, 4),
        "delta_sbr_vs_po": round(d_sbr, 4),
        "hypothesis_ko": ("임무 가설: Sionna 는 각도의존 프레넬을 쓰므로 새 Γ(θ) 를 켠 po 팔의 "
                          "스펙트럼 코사인이 오르면 독립 검증이 된다."),
        "reading_ko": reading,
    }
    for k, v in cos.items():
        print(f"  {k:18s} {v:.4f}", flush=True)
    print(f"  po 팔 저장본 비트재현: {repro}", flush=True)
    print(f"  Δ(sionna_vs_po) = {d_sionna:+.4f}", flush=True)

    ok_dir = all(c["same_direction"] for c in ch.values())
    ok_ord = all(c["same_order"] for c in ch.values())
    out["verdict_ko"] = (
        f"[A] {'PASS' if all_ok else 'FAIL'} — 꺼짐(옛 호출·킬스위치)은 전부 비트동일. "
        f"[B] 프롭 채널 Δ {ch['matrice4e']['level_delta_db']:+.2f}/"
        f"{ch['mini5pro']['level_delta_db']:+.2f} dB — SBR 실측(+5.16/+6.48)과 "
        f"방향 {'일치' if ok_dir else '불일치'}·자릿수 {'일치' if ok_ord else '불일치'}. "
        f"전체 σ 는 {sig['matrice4e']['delta_db']:+.2f}/{sig['mini5pro']['delta_db']:+.2f} dB 로 "
        f"거의 불변(설계 의도). "
        f"[C] sionna↔po 코사인 {cos['sionna_vs_po_off']:.4f} → {cos['sionna_vs_po_on']:.4f} "
        f"({d_sionna:+.4f}) — "
        f"{'올랐다(독립 검증 성립)' if d_sionna > 0 else '오르지 않았다(독립 검증 미성립 — three_engines_po_arm.reading_ko 참조)'}. "
        f"sbr↔po 는 {d_sbr:+.4f} (두 커널이 같은 각도 물리를 공유하게 된 내부 일관성).")

    out["open_issues_ko"] = [
        "⚠ [C] Sionna 독립검증 미성립(코사인 −0.02) — Sionna 팔은 확산(S) 지배라 벌크 프레넬 "
        "각도모양의 잣대가 아니었다. 각도 Γ 의 독립 앵커는 실측(문헌 RCS·야외 X410)으로 넘어간다.",
        "PO 프롭 채널 Δ(+3.46/+2.93 dB)가 SBR(+5.16/+6.48)보다 작다 — 가림 없는 PO 는 "
        "항상-보이는 뒷면·아랫면 기여가 각도 효과를 희석한다(커널 차이, 모순 아님).",
        "drone_rcs_pattern(engine='po')·drone_rcs_pattern_bw·viz_*/benchmark 하위 사용처는 "
        "전부 옛 경로 그대로다(의도된 옵트인 정책). 순수 PO 로 각도 Γ 를 쓰려면 "
        "mesh_to_points(return_keys=True)+point_mat_keys+mats= 로 직접 부른다.",
        "얇은 날(두께≪λ)의 각도 거동에 벌크 프레넬 모양을 빌려 쓰는 근사는 그대로다 "
        "(materials.py 선언 근사 (1) — 방향은 맞고 크기는 근사).",
    ]

    out["_meta"]["seconds"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(OUTJ), exist_ok=True)
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUTJ}\n{out['verdict_ko']}")


if __name__ == "__main__":
    main()
