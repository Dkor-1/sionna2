# -*- coding: utf-8 -*-
"""
mesh_fix_battery_union_0816.py — **battery 그룹 자기겹침 수리의 전후 실측** (감사 §⑤ 2층)
================================================================================================

무엇을 고쳤나 (한 줄)
--------------------
셸형 공용 경로에서 **배터리 팩 상자와 v2 «마그네슘 구조판» 상자가 서로 파고들어** 있었다.
두 상자 모두 `battery` 그룹이고 |Γ|≈1(금속)이다. 겹친 자리의 면은 메쉬에 그대로 남고,
**PO 는 가림을 안 보므로**(rcs_po.py 가 스스로 선언) 그 면적을 한 번 더 더한다 = 이중계상.

어떻게 고쳤나
-------------
`MESH_FIX=battery` 를 켜면 `drone_cad.build_frame_cad` 가 'battery' 를 불리언 합집합 목록에
넣는다. ⭐**치수는 하나도 안 바꾼다.** 기종별 실측 치수가 없는데 상자를 옮기면 «임의로 옮긴
손잡이» 가 된다(실측표를 받은 matrice4e·phantom3 는 애초에 안 겹친다 — 그 둘이 규칙을 지키는
쪽이고, 규칙을 어긴 것은 규칙을 적어 놓은 공용 경로였다). 합집합은 겹친 자리의 **내부 면만**
없앤다 — 바깥 껍질은 한 삼각형도 안 움직인다.

무엇을 재나 — 결함마다 **세 수**
--------------------------------
① 결함의 크기 : 이중계상 면적 [mm²·%] 을 **두 잣대**로 잰다.
     · 검사기 잣대(면 **중심**이 남의 솔리드 안) — mesh_check 가 쓰는 수. 면이 6~24장뿐이라 알이 굵다.
     · ⭐정확한 잣대(합집합 전후 **면적 차**) — 실제로 메쉬에서 사라지는 면적. 이쪽이 참값이다.
       (두 상자의 합집합 표면 = ∂A 중 B 밖 + ∂B 중 A 밖 이므로 차이가 곧 매몰면적이다.)
② σ 변화   : 우리 커널 PO 로 직접. 대역평균 3.5 GHz·100 MHz·9점, 방위 180, el 0/−30, 바이 β=120.
③ 판정 밴드: 무해 <0.1 dB · 보임 0.1~1.0 dB · 결론을 바꿈 >1 dB (기준선 원장과 같은 밴드).

⚠ 적용 범위 — 이 dB 는 **PO 경로 전용**이다. 기본 엔진 SBR 은 first-hit 이라 매몰면 오차가
   구조적으로 0 이다. 다만 메쉬 자체가 바뀌므로 SBR 결과도 «비트동일» 로는 안 남는다
   (형상이 같은 자리에서 면만 사라지므로 SBR σ 는 사실상 안 움직여야 한다 — GPU 금지라 이번엔 못 쟀다).

실행: PYTHONPATH=src:benchmark python benchmark/mesh_fix_battery_union_0816.py
산출: outputs/mesh_layer2_battery_overlap_0816.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import drone_cad                                                    # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT             # noqa: E402
from rcs_po import mesh_to_points, rcs_from_points, C0              # noqa: E402

OUT = os.path.join(ROOT, "outputs", "mesh_layer2_battery_overlap_0816.json")

FC = 3.5e9
LAM = C0 / FC
SPACING = LAM / 7.0                 # rcs_po 순수 PO 기본 간격
AZ = np.arange(0.0, 360.0, 2.0)     # 180 방위 — 기준선 원장과 같다
BW = 100e6                          # 5G 100 MHz
N_F = 9
GEOMS = (("mono_el0", 0.0, 0.0), ("mono_el-30", -30.0, 0.0), ("bi_b120_el-30", -30.0, 120.0))
FIX = "battery"

#  ⚠ ITU 'metal' 만 Sionna RT(=OptiX/GPU)를 타므로 저장소가 이미 캐시한 3.5 GHz 값을 쓴다
#    (outputs/mesh_compare_material.json :: materials.metal.gamma_po_5g). 나머지는 CPU 표에서 나온다.
METAL_GAMMA_5G = 0.9998026802895116


def gamma_map():
    from materials import gamma_po
    return {g: (METAL_GAMMA_5G if mat == "metal" else gamma_po(mat, FC))
            for g, (mat, _) in DRONE_GROUP_MAT.items()}


GAMMA = gamma_map()


# --------------------------------------------------------------------------- #
#  PO — 모노는 **출하 커널 그대로**, 바이스태틱만 같은 식으로 확장(β=0 회귀로 확인)
# --------------------------------------------------------------------------- #
def _look(az_deg, el_deg):
    az = np.radians(np.atleast_1d(az_deg)); el = np.radians(el_deg)
    return np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az),
                     np.full_like(az, np.sin(el))], axis=-1)


def sigma_bistatic(P, N, dA, w, fc, az_deg, el_deg, beta_deg, chunk=24):
    """바이스태틱 스칼라 PO σ(az). 식은 benchmark/adv_consequence_0816_bistatic 과 같다:
       E = Σ [n̂·û_i>0][n̂·û_s>0] |Γ| (n̂·û_i) ΔA · exp(j k P·(û_i+û_s)),  σ = 4π/λ²|E|².
    β=0 에서 출하 커널(rcs_from_points)로 정확히 되돌아간다 — 아래 회귀가 그것을 잰다."""
    lam = C0 / fc; k = 2 * np.pi / lam
    Ui = _look(np.asarray(az_deg) - beta_deg / 2.0, el_deg)
    Us = _look(np.asarray(az_deg) + beta_deg / 2.0, el_deg)
    amp = dA if w is None else dA * w
    out = np.empty(len(Ui), complex)
    for s in range(0, len(Ui), chunk):
        a, b = Ui[s:s + chunk], Us[s:s + chunk]
        NI = N @ a.T; NS = N @ b.T
        PH = P @ (a + b).T
        g = np.where((NI > 0) & (NS > 0), NI, 0.0)
        out[s:s + chunk] = (g * amp[:, None] * np.exp(1j * k * PH)).sum(axis=0)
    return (4 * np.pi / lam ** 2) * np.abs(out) ** 2


def sigma_band(P, N, dA, w, el_deg, beta_deg):
    """대역평균 σ(az) — 5G 100 MHz·9점(비코히런트). 단일주파수 널은 rcs_po 자신이
    «개별적으로는 수치 아티팩트» 라고 선언한 값이라 방위별 dB 는 대역평균으로 읽는다."""
    freqs = np.linspace(FC - BW / 2, FC + BW / 2, N_F)
    acc = 0.0
    for f in freqs:
        if beta_deg == 0.0:
            acc = acc + rcs_from_points(P, N, dA, f, AZ, el_deg, w=w)   # ⭐출하 커널
        else:
            acc = acc + sigma_bistatic(P, N, dA, w, f, AZ, el_deg, beta_deg)
    return acc / len(freqs)


def ang_smooth(sig, win_deg=3.0):
    from rcs_po import angular_smooth
    return angular_smooth(sig, win_deg, float(AZ[1] - AZ[0]))


# --------------------------------------------------------------------------- #
#  메쉬 인구조사
# --------------------------------------------------------------------------- #
def group_stats(mesh, grp="battery"):
    V = np.asarray(mesh.v, float); F = np.asarray(mesh.f, int); G = np.asarray(mesh.g)
    a = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 2
    sel = G == grp
    return dict(n_faces_total=int(len(F)), area_total_mm2=round(float(a.sum()) * 1e6, 4),
                n_faces_grp=int(sel.sum()), area_grp_mm2=round(float(a[sel].sum()) * 1e6, 4))


def checker_overlap(mesh, key, grp="battery"):
    """mesh_check 가 보는 그룹내 겹침 [%] + 그 잣대로 잰 매몰 면적[mm²]."""
    import mesh_check as mc
    V = np.asarray(mesh.v, float); F = np.asarray(mesh.f, int); G = np.asarray(mesh.g)
    sub = G == grp
    if not sub.any():
        return None, None
    f = F[sub]; used = np.unique(f)
    remap = {int(o): i for i, o in enumerate(used)}
    tm = mc._tm(V[used], np.vectorize(remap.get)(f))
    comps = mc._split(tm)
    pct = mc._group_overlap_pct(comps)
    area = float(sum(float(c.area) for c in comps)) * 1e6
    return pct, round(pct / 100.0 * area, 4)


def kst_now():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")


def band(delta_db):
    d = abs(delta_db)
    return "무해(<0.1dB)" if d < 0.1 else ("보임(0.1~1dB)" if d <= 1.0 else "결론을바꿈(>1dB)")


def main():
    t0 = time.time()
    keys = list(DRONES)
    res = {}
    census = {}
    #  ── 1) 인구조사 + σ ─────────────────────────────────────────────────── #
    for k in keys:
        spec = DRONES[k]
        m_off = build_drone(spec)
        m_on = build_drone(spec, mesh_fix=FIX)
        s_off, s_on = group_stats(m_off), group_stats(m_on)
        ov_off, ovA_off = checker_overlap(m_off, k)
        ov_on, ovA_on = checker_overlap(m_on, k)
        A_off, A_on = drone_cad.build_frame_cad(spec), drone_cad.build_frame_cad(spec, mesh_fix=FIX)
        vol_off = sum(float(mm.volume) for mm in A_off.parts.get("battery", [])) * 1e9
        vol_on = sum(float(mm.volume) for mm in A_on.parts.get("battery", [])) * 1e9
        n_parts_off = len(A_off.parts.get("battery", []))
        exact = s_off["area_grp_mm2"] - s_on["area_grp_mm2"]        # ⭐정확한 이중계상 면적
        c = dict(
            battery_parts_before=n_parts_off,
            battery_parts_after=len(A_on.parts.get("battery", [])),
            faces_total=[s_off["n_faces_total"], s_on["n_faces_total"]],
            battery_faces=[s_off["n_faces_grp"], s_on["n_faces_grp"]],
            battery_area_mm2=[s_off["area_grp_mm2"], s_on["area_grp_mm2"]],
            drone_area_mm2=[s_off["area_total_mm2"], s_on["area_total_mm2"]],
            #  ⭐ 결함 크기 — 두 잣대
            double_counted_area_mm2_exact=round(exact, 4),
            double_counted_pct_of_battery_exact=round(100.0 * exact / max(s_off["area_grp_mm2"], 1e-9), 4),
            double_counted_pct_of_drone_exact=round(100.0 * exact / max(s_off["area_total_mm2"], 1e-9), 4),
            checker_overlap_pct=[ov_off, ov_on],
            checker_buried_area_mm2=[ovA_off, ovA_on],
            #  질량축(감사 I9) — 부품마다 부피를 따로 더하므로 겹친 부피는 두 번 들어간다
            battery_volume_mm3=[round(vol_off, 4), round(vol_on, 4)],
            double_counted_volume_mm3=round(vol_off - vol_on, 4),
            double_counted_volume_pct=round(100.0 * (vol_off - vol_on) / max(vol_off, 1e-9), 4),
        )
        census[k] = c
        print(f"[{k}] parts {c['battery_parts_before']}→{c['battery_parts_after']} · "
              f"겹침 {ov_off}%→{ov_on}% · 정확매몰면적 {exact:.3f} mm² "
              f"({c['double_counted_pct_of_battery_exact']:.2f} % of battery)", flush=True)

        if n_parts_off < 2:                       # 합집합할 것이 없다 = 이 수리와 무관
            res[k] = dict(touched=False, note="battery 부품이 1개 — 이 수리가 손댈 것이 없다")
            continue

        P0, N0, dA0, w0 = mesh_to_points(m_off, SPACING, gamma=GAMMA)
        P1, N1, dA1, w1 = mesh_to_points(m_on, SPACING, gamma=GAMMA)
        row = dict(touched=True, n_points=[int(len(dA0)), int(len(dA1))], sigma={})
        for name, el, beta in GEOMS:
            s0 = sigma_band(P0, N0, dA0, w0, el, beta)
            s1 = sigma_band(P1, N1, dA1, w1, el, beta)
            d_az = 10 * np.log10(s0.mean() / s1.mean())              # (+) = 결함이 밝다
            d_per = 10 * np.log10(s0 / s1)
            w0s, w1s = ang_smooth(s0), ang_smooth(s1)
            d_win = 10 * np.log10(w0s / w1s)
            row["sigma"][name] = dict(
                sigma_defect_azmean_dbsm=round(float(10 * np.log10(s0.mean())), 4),
                sigma_fixed_azmean_dbsm=round(float(10 * np.log10(s1.mean())), 4),
                azimuth_mean_db=round(float(d_az), 4),
                worst_az_db=round(float(d_per[np.argmax(np.abs(d_per))]), 4),
                worst_az_deg=float(AZ[np.argmax(np.abs(d_per))]),
                worst_az_db_3deg_window=round(float(d_win[np.argmax(np.abs(d_win))]), 4),
                p95_abs_db=round(float(np.percentile(np.abs(d_per), 95)), 4),
                verdict=band(float(d_az)))
            print(f"    {name:14s} {10*np.log10(s0.mean()):8.3f} → "
                  f"{10*np.log10(s1.mean()):8.3f} dBsm  Δ={d_az:+.4f} dB  [{band(float(d_az))}]",
                  flush=True)
        res[k] = row

    #  ── 2) 커널 회귀 — 내 바이스태틱이 β=0 에서 출하 커널로 돌아오나 ──────── #
    spec = DRONES["mini2"]
    m = build_drone(spec)
    P, N, dA, w = mesh_to_points(m, SPACING, gamma=GAMMA)
    ref = rcs_from_points(P, N, dA, FC, AZ, -30.0, w=w)
    got = sigma_bistatic(P, N, dA, w, FC, AZ, -30.0, 0.0)
    rel = float(np.max(np.abs(got - ref) / np.maximum(np.abs(ref), 1e-300)))

    #  ── 3) 질량축(감사 I9) — 부위별 질량 배분 ──────────────────────────── #
    from gazebo_export import inertia_from_mesh
    mass = {}
    for k in ("mini2", "phantom4", "mavic4pro", "mini5pro"):
        a = inertia_from_mesh(DRONES[k])
        b = inertia_from_mesh(DRONES[k], mesh_fix=FIX)
        mass[k] = dict(
            battery_mass_g=[round(a["per_group"]["battery"] * 1000, 3),
                            round(b["per_group"]["battery"] * 1000, 3)],
            battery_share_pct=[round(100 * a["per_group"]["battery"] / a["mass"], 3),
                               round(100 * b["per_group"]["battery"] / b["mass"], 3)],
            com_mm=[[round(float(v) * 1000, 4) for v in a["com"]],
                    [round(float(v) * 1000, 4) for v in b["com"]]],
            Idiag_kgm2=[[round(float(a["I"][i, i]), 8) for i in range(3)],
                        [round(float(b["I"][i, i]), 8) for i in range(3)]],
            total_mass_kg=round(a["mass"], 4))
        print(f"[{k}] 배터리 질량배분 {mass[k]['battery_share_pct'][0]} % → "
              f"{mass[k]['battery_share_pct'][1]} %", flush=True)

    out = dict(
        _meta=dict(
            title="battery 그룹 자기겹침 — 수리(불리언 합집합) 전후 실측",
            generated_kst=kst_now(),
            role="수리자 — 담당 결함 하나만 정밀하게 고치고 전후를 같은 잣대로 잰다.",
            defect="신규(0층 검사기가 잡은 것) — 셸형 공용 경로의 battery 팩 상자 ↔ v2 구조판 상자 자기겹침",
            fix=dict(switch=f"MESH_FIX={FIX}", 기본="꺼짐",
                     방법="drone_cad.build_frame_cad 의 불리언 union 목록에 'battery' 추가",
                     치수변경="없음 — 상자 크기·위치는 한 mm 도 안 건드렸다",
                     왜_옮기지_않았나="기종별 실측 치수가 없다. 없는 치수로 상자를 옮기면 «임의로 "
                                      "옮긴 손잡이» 가 된다(감사가 반복해 경고한 함정)."),
            compute="CPU 전용(GPU 금지). PO·메쉬 전부 numpy/trimesh.",
            python="/workspace/.venvs/py312/bin/python (PYTHONPATH=src:benchmark)",
            측정_규약=dict(
                주파수="3.5 GHz, 대역평균 100 MHz·9점", 점간격="λ/7 = 12.24 mm (rcs_po 기본)",
                방위="0~358°, 2° 간격 180 방위", 고각="el 0° · el −30°",
                바이스태틱="β=120°, el −30°",
                재질="drones.DRONE_GROUP_MAT → materials. ⚠ITU 'metal' 만 캐시값 "
                     f"{METAL_GAMMA_5G} (Sionna RT=GPU 필요)",
                부호="(+) = 결함이 σ 를 밝게 만든다(과대계상)",
                커널="모노는 출하 커널 rcs_po.rcs_from_points 그대로. 바이스태틱만 같은 식으로 확장."),
            판정_밴드=dict(무해="<0.1 dB", 보임="0.1~1.0 dB", 결론을_바꿈=">1 dB"),
            적용_범위="⚠PO 경로 전용. SBR 은 first-hit 이라 매몰면 오차가 구조적으로 0 이다.",
        ),
        커널_회귀=dict(내_바이스태틱_beta0_vs_출하커널_최대상대오차=rel,
                       뜻="1e-12 이하면 같은 답이다 — 아래 dB 는 출하 커널의 답으로 읽어도 된다."),
        인구조사=census,
        σ=res,
        질량축_감사I9=mass,
        소요_초=round(time.time() - t0, 1),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"\n저장: {OUT}  ({time.time()-t0:.1f} s)")
    print(f"커널 회귀(β=0 vs 출하): 최대 상대오차 {rel:.3e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
