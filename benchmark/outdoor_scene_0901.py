# -*- coding: utf-8 -*-
"""outdoor_scene_0901.py — 실외 장면이 날개 박자에 하는 일 (리포트 12 원장).

무엇을 묻나
-----------
지금까지 스윕은 **자유공간**이었다 — `rt.load_scene()` 빈 씬에 드론 부품만 넣는다.
그래서 우리가 «클러터» 라고 부르며 걷어낸 것은 전부 **드론 자신의 동체**였다.
지면·건물을 넣으면 박자가 살아남나, 그리고 정지 클러터 제거로 되돌릴 수 있나.

잣대 — ⭐**빗살 하모닉 SNR**(2026-09-02 정본)
--------------------------------------------
⛔dB 잣대(봉우리÷바닥)는 **몇 자세짜리 낙차 임펄스열**에도 큰 값을 준다. 2026-08-31
적대 검증에서 실제로 그 함정이 드러났다 — el 0 기록의 변동 100 % 가 8,192 자세 중
19~52 개의 낙차인데 dB 는 9.5 를 줬다.

⛔⛔**ρ(포락 자기상관)도 정본이 아니다** — `docs/RHO_IS_SMOOTHNESS_0902.md` 가 폐기했다.
ρ 가 재는 것은 «리듬» 이 아니라 **«매끄러움»** 이다: 직선 0.9996 · 2 차 추세 0.9996 ·
한가운데 계단 하나 0.9996 · AR(1) 붉은잡음(φ=0.99) 0.9748 이 **전부 «박자» 칸**에 든다.
2026-09-02 실외 판정에서 **40 칸 중 12 칸이 ρ 의 거짓음성**이었다.
⛔옛 눈금 「잡음 −0.06~+0.07 · 박자 +0.92~+0.99」는 **인용 금지**다 — ρ 가 리듬 검출기라는
인상을 준다. ⛔「대체 잣대 넷 중 살아남은 것은 ρ 하나다」도 뺀다.

⛔우리 커널은 이 비교에 못 들어간다 — `--env` 는 PathSolver 씬에만 붙고 `sbr_field` 는
   드론 메쉬만 받는다. 격자가 표적 bbox 로 정해지므로 지면 120 m 를 통째로 넣으면
   격자점이 79,483 배가 된다. 그 수도 여기서 낸다.

⛔GPU 를 쓰지 않는다. CUDA_VISIBLE_DEVICES="" 로 돌린다.

    PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/outdoor_scene_0901.py
"""
import json
import os
import sys

import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
sys.path.insert(0, f"{ROOT}/src")
OUT = f"{ROOT}/outputs/outdoor_scene_0901.json"
MESH = "mfixbatteryi5_blperairframe"
ELS = [0.0, -30.0, -60.0]
CUTS = [5.0, 20.0, 60.0, 100.0, 120.0]


def arm(el, env=False):
    tag = "_envoutdoor01" if env else ""
    return f"sionna_p4000000000_swR0D0E0F1_r15_n8192{tag}_{MESH}_d2/el{el:+.0f}"


def rho(E):
    """포락 자기상관(1 지연)."""
    a = np.abs(np.asarray(E))
    ac = a - a.mean()
    d = float(np.dot(ac, ac))
    return float(np.dot(ac[:-1], ac[1:]) / d) if d > 0 else float("nan")


def corr(a, b):
    a = np.asarray(a) - np.mean(a)
    b = np.asarray(b) - np.mean(b)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(abs(np.vdot(a, b)) / d) if d > 0 else float("nan")


def lvl(E):
    return float(20 * np.log10(np.abs(np.asarray(E)).mean()))



# ═══════════════════════════════════════════════════════════════════════════ #
#  ⭐낙차를 세는 두 규칙 — 둘 다 낸다 (2026-09-03 신설)
# ═══════════════════════════════════════════════════════════════════════════ #
def drop_rules(Z, els=ELS):
    """⛔«낙차 몇 개» 는 **어느 자로 재느냐에 따라 갈린다.** 이 원장은 둘 다 적는다.

    자유공간 el −30° 를 두 규칙으로 세면 0 개와 73 개가 나온다. 본문이 한쪽만 쓰고
    «같은 규칙으로 셌다» 라고만 적으면, 읽는 사람은 다른 쪽 수를 볼 방법이 없다
    (2026-09-03 에 실제로 그랬다 — 「자유공간 빗각에는 낙차 0 개」가 그 자리다).

    ratio  |E| 가 중앙값의 10 % 아래   — 빗살 SNR 블록이 쓰는 자
    mad    |E| 가 중앙값에서 MAD 의 k 배 아래 — 본문 절 2 가 쓰는 자(k=10 이 정본)

    ⚠두 자는 성질이 다르다. ratio 는 **중앙값 대비 절대 비율**이라 흩어짐과 무관하고,
      mad 는 **그 기록의 흩어짐**을 기준 삼는다. 그래서 매끄러운 기록에서는 MAD 가 작아
      문턱이 중앙값에 붙고, 흩어진 기록에서는 문턱이 0 아래로 내려가 아무것도 안 잡힌다.
      어느 쪽이 옳다고 이 함수가 정하지 않는다 — 둘을 나란히 적어 사람이 고르게 한다.
    """
    out = {}
    for el in els:
        row = {}
        for tag, env in (("free", False), ("outdoor", True)):
            k = arm(el, env)
            if k not in Z:
                continue
            a = np.abs(np.asarray(Z[k]))
            med = float(np.median(a))
            mad = float(np.median(np.abs(a - med)))
            cell = dict(n_poses=int(a.size), median=med, mad=mad,
                        ratio_rule_ko="|E| < 중앙값 × 0.1",
                        mad_rule_ko="|E| < 중앙값 − k × MAD")
            cell["n_ratio"] = int(np.sum(a / med < 0.1)) if med > 0 else 0
            for kk in (5, 8, 10, 15, 20, 30):
                thr = med - kk * mad
                cell[f"n_mad_k{kk}"] = int(np.sum(a < thr))
                cell[f"thr_mad_k{kk}_over_median"] = round(thr / med, 4) if med > 0 else None
            #: ⭐문턱이 0 아래로 내려가면 그 자는 **구조적으로 아무것도 못 잡는다.**
            cell["mad_k10_threshold_is_negative"] = bool(med - 10 * mad <= 0)
            row[tag] = cell
        if row:
            out[f"el{el:+.0f}"] = row
    return out


# ═══════════════════════════════════════════════════════════════════════════ #
#  ⭐빗살 SNR — ρ 를 대신하는 잣대 (2026-09-02 신설)
# ═══════════════════════════════════════════════════════════════════════════ #
def comb_block(Z, els=ELS):
    """⭐ρ 는 «리듬» 이 아니라 «매끄러움» 을 잰다(docs/RHO_IS_SMOOTHNESS_0902.md).
    여기서는 **빗살 하모닉 SNR** 로 다시 낸다. 낙차를 **안 메운 원본**과,
    깊은 낙차(r<0.1, 솔버 인공물)를 메운 판, 그리고 **무작위 자세를 같은 수만큼**
    메운 대조군을 함께 낸다 — 보간 자체의 몫을 빼려고."""
    import comb_snr as C
    from clutter_parts_ladder_0824 import PRF
    rng = np.random.default_rng(0)
    out = {}
    for el in els:
        row = {}
        for tag, env in (("free", False), ("outdoor", True)):
            k = arm(el, env)
            if k not in Z:
                continue
            E = np.asarray(Z[k])
            a = np.abs(E); med = float(np.median(a))
            bad = np.where(a / med < 0.1)[0] if med > 0 else np.zeros(0, int)
            good = np.setdiff1d(np.arange(E.size), bad)
            def fill(idx):
                R = E.copy()
                if len(idx) and len(good) > 1:
                    R[idx] = (np.interp(idx, good, E[good].real)
                              + 1j * np.interp(idx, good, E[good].imag))
                return R
            def snr(x):
                v = C.comb_snr(np.asarray(x), PRF, el, arm=k)
                return None if v is None else round(float(v), 2)
            ctl = [snr(fill(rng.choice(good[(good > 0) & (good < E.size - 1)],
                                       len(bad), replace=False))) for _ in range(5)] \
                if len(bad) else []
            row[tag] = dict(n_deep=int(len(bad)),
                            comb_raw=snr(E),
                            comb_repaired=snr(fill(bad)) if len(bad) else snr(E),
                            comb_random_ctl=[c for c in ctl if c is not None])
        out[f"el{el:+.0f}"] = row
    return out


def main():
    from clutter_parts_ladder_0824 import cs_eca, PRF, FFL, FCUT
    from rcs_sbr import DEFAULT_DIV
    Z = np.load(f"{ROOT}/outputs/elevation_sweep_md.npz")

    cells = {}
    print(f"═══ 실외 장면 · ECA 노치 {FCUT:g} Hz · f_flash {FFL:.2f} Hz ═══\n")
    hdr = (f"{'앙각':>5}{'자유공간 ρ':>12}{'실외 ρ':>10}{'제거 후 ρ':>11}"
           f"{'레벨 변화':>11}{'|상관| 잔차↔자유':>17}{'AC 남은몫':>10}")
    print(hdr)
    print("-" * len(hdr))
    for el in ELS:
        F = np.asarray(Z[arm(el, False)])
        O = np.asarray(Z[arm(el, True)])
        R = cs_eca(O)
        ac0 = float(np.sum(np.abs(O - O.mean()) ** 2))
        ac1 = float(np.sum(np.abs(R - R.mean()) ** 2))
        c = dict(el_deg=el,
                 rho_free=round(rho(F), 4), rho_outdoor=round(rho(O), 4),
                 rho_removed=round(rho(R), 4),
                 level_free_db=round(lvl(F), 2), level_outdoor_db=round(lvl(O), 2),
                 d_level_db=round(lvl(O) - lvl(F), 2),
                 corr_removed_vs_free=round(corr(R, F), 4),
                 ac_left_pct=round(100 * ac1 / ac0, 1),
                 rho_free_removed=round(rho(cs_eca(F)), 4))
        cells[f"el{el:+.0f}"] = c
        print(f"{el:>+5.0f}{c['rho_free']:>+12.3f}{c['rho_outdoor']:>+10.3f}"
              f"{c['rho_removed']:>+11.3f}{c['d_level_db']:>+10.1f} dB"
              f"{c['corr_removed_vs_free']:>17.4f}{c['ac_left_pct']:>9.1f}%")

    # ── 노치 폭 사다리
    print(f"\n═══ 노치 폭을 흔들어도 같은가 ═══")
    notch = {}
    for el in (-30.0, -60.0):
        F = np.asarray(Z[arm(el, False)])
        O = np.asarray(Z[arm(el, True)])
        row = {}
        line = f"  el{el:>+4.0f}  "
        for fc in CUTS:
            R = cs_eca(O, fcut=fc)
            row[f"fcut{fc:g}"] = dict(rho=round(rho(R), 4),
                                      corr_vs_free=round(corr(R, F), 4))
            line += f"fcut{fc:>5.0f}: ρ {rho(R):+.3f} |r| {corr(R, F):.3f}   "
        notch[f"el{el:+.0f}"] = row
        print(line)

    # ── ⭐빗살 SNR (ρ 대체)
    comb = comb_block(Z)
    print("\n═══ 빗살 하모닉 SNR — 인공물을 빼면 날개 박자가 보이나 ═══")
    print(f"{'앙각':>5}{'자유 원본':>11}{'실외 원본':>11}{'실외 인공물뺌':>14}{'무작위 대조':>13}{'깊은낙차':>9}")
    for k, v in comb.items():
        o = v.get("outdoor", {}); f_ = v.get("free", {})
        c = o.get("comb_random_ctl") or []
        print(f"{k:>5}{str(f_.get('comb_raw')):>11}{str(o.get('comb_raw')):>11}"
              f"{str(o.get('comb_repaired')):>14}"
              f"{(f'{np.mean(c):.1f}' if c else '—'):>13}{o.get('n_deep',0):>9}")

    # ── 격자 비용 — 왜 우리 커널이 못 들어가나
    lam = 2.998e8 / 3.5e9
    d = lam / DEFAULT_DIV
    pad = 1.15

    def grid(Rmax):
        Rout = Rmax * pad + 3 * d
        n = int(np.ceil(2 * Rout / d))
        return dict(R_max_m=round(Rmax, 3), R_out_m=round(Rout, 3), n=n, points=n * n)

    G = {"drone_only": grid(0.28), "ground_120m": grid(float(np.hypot(60, 60))),
         "patch_2m": grid(float(np.hypot(1.0, 1.0))),
         "patch_5m": grid(float(np.hypot(2.5, 2.5)))}
    base = G["drone_only"]["points"]
    for k in G:
        G[k]["vs_drone"] = round(G[k]["points"] / base, 1)
    print(f"\n═══ 광선 격자 비용 (λ/{DEFAULT_DIV} = {d*1000:.2f} mm) ═══")
    for k, v in G.items():
        print(f"  {k:<14} R_max {v['R_max_m']:>7.2f} m · n {v['n']:>7,} · "
              f"격자점 {v['points']:>15,} · {v['vs_drone']:>10,.0f} 배")

    # ── 제1 프레넬 존 — 실제로 필요한 지면 넓이
    r_m = 15.0
    R1 = float(np.sqrt(lam * r_m * r_m / (2 * r_m)))
    print(f"\n  제1 프레넬 반경 (15 m·3.5 GHz) = {R1*100:.0f} cm · 지름 {2*R1:.2f} m")

    doc = dict(_meta=dict(
        generator="benchmark/outdoor_scene_0901.py", gpu_used=False,
        generated_ko="2026-09-01",
        question_ko=("실외 장면(지면·건물)을 넣으면 날개 박자가 살아남나, "
                     "그리고 정지 클러터 제거로 되돌릴 수 있나"),
        metric_ko=(
            "⛔ρ(포락 자기상관)는 «리듬» 이 아니라 «매끄러움» 을 잰다 — 직선·계단·붉은잡음이 "
            "전부 «박자» 칸(0.92~0.99)에 든다(docs/RHO_IS_SMOOTHNESS_0902.md, 2026-09-02). "
            "⭐정본 잣대는 **빗살 하모닉 SNR** 이다(백색잡음 2,000 판 영분포 p99 ≈ 8.4). 옛 설명: ""포락 자기상관 ρ(1 지연). 잡음 −0.06~+0.07 · 박자 +0.92~+0.99. "
                   "⛔dB(봉우리÷바닥)는 몇 자세짜리 낙차 임펄스열에도 큰 값을 주므로 쓰지 않는다."),
        arm_ko=("스톡 엔진 ①다끔(R0D0E0F1) · matrice4e · 15 m · 자세 8,192 · "
                "광선 4e9 · 깊이 2. 실외 팔은 파일명에 _envoutdoor01 이 붙는다."),
        env_ko=("assets/meshes/outdoor01 — 지면 120×120 m 콘크리트 · 건물 넷 9~24 m · "
                "금속 기둥 둘. 드론 고도 20 m(레이다가 rng·sin(el) 깊이에 오므로 "
                "15 m·el −90 의 −15 m 보다 지면이 아래여야 한다)."),
        ours_absent_ko=("⛔우리 커널은 이 비교에 없다 — --env 는 build_scene(PathSolver 씬)에만 "
                        "붙고 sbr_field 는 자세 잡힌 드론 메쉬만 받는다. 그 상태로 난 샤드 6 개는 "
                        "자유공간과 상대차 1e−16 이라 2026-09-01 에 지웠고, "
                        "--engine ours 에 --env 를 주면 이제 거부한다."),
        removal_ko=f"benchmark/clutter_parts_ladder_0824.cs_eca — 느린시간 DFT 에서 |f| ≤ fcut 칸을 0 으로 두는 **직각 노치**. 정본 {FCUT:g} Hz",
        prf_hz=float(PRF), f_flash_hz=float(FFL), fcut_hz=float(FCUT),
        lam_m=round(lam, 6), grid_spacing_m=round(d, 6), grid_div=int(DEFAULT_DIV),
        fresnel_r1_m=round(R1, 3), range_m=r_m),
        cells=cells, notch_ladder=notch, grid_cost=G, comb=comb, drop_rules=drop_rules(Z))
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
