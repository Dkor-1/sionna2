# -*- coding: utf-8 -*-
"""prf_ladder_0828.py — 섬광 폭이 자세 격자를 따라가나, 각도로 수렴하나 (PRF 사다리)

무엇을 묻나
-----------
PathSolver 섬광은 «자세 하나» 폭이다(0825 판독: 중앙값 1 자세 · 98.2 %가 한 자세짜리).
블레이드가 만드는 로브는 개구 한계상 그보다 훨씬 넓어야 한다 —
  프로펠러 반경 0.137 m → λ/2D = 17.91° (k=1 에서 15.5 자세)
  기체 대각 0.439 m    → 5.59° (4.83 자세, **최악 하한**)
관측된 1.157°(1 자세)는 그 하한의 1/4.8 이다. ⇒ 경로 이산화 흔적 의심.

⛔**`--n-poses` 로는 못 묻는다.** 자세 간격 dt = 1/PRF 는 n 과 무관하므로 n 을 4 배 해도
   «4 배 긴 기록»일 뿐 촘촘해지지 않는다(블레이드 통과당 자세 수 155.5 로 불변).
⇒ **PRF 를 k 배 올린다.** t_i = i/(k·PRF₀) 이므로 k 단의 자세 i·k 가 k=1 의 자세 i 와
   **비트 동일한 시각**이다 — 같은 섬광을 촘촘히 다시 보는 «짝지은» 관측이다.

잣대 — ⛔«자세 개수» 를 버리고 **도(°)** 로 간다
------------------------------------------------
자세 하나가 가리키는 회전각이 k 에 반비례하므로(k=1 1.157° · k=4 0.289°),
«1 자세» 라는 말은 k 마다 뜻이 다르다. 그래서 폭을 각도로 환산해 비교한다.

  θ_half [°] = (상위 봉우리의 반진폭 폭 중앙값, 자세) × 360·(f_flash/2)/PRF

⚠3σ 문턱 런길이(옛 `median_event_width_poses`)는 쓰지 않는다 — 문턱을 기록 자신이
  만들고 하한이 1 자세라 내려갈 자리가 없다. 반진폭 폭은 문턱이 없다.

판정
----
  세 점(k=1,2,4)에서 log θ_half 대 log k 를 맞춰 기울기 p 를 낸다(θ_half ∝ k^−p).
    p ≥ 0.75  ⇒ A. **격자 산물** — 폭이 자세 하나를 계속 따라 내려간다(= 폭이 없다)
    p ≤ 0.25  ⇒ B. **물리** — 폭이 각도로 수렴한다
    그 사이   ⇒ C. **해상 못 함** — 8192·19.7 kHz 원장이 이 구조를 못 잡는다

⛔GPU 를 쓰지 않는다. CUDA_VISIBLE_DEVICES="" 로 돌린다.
"""
import json
import os
import numpy as np

ROOT = "/workspace/sionna"
LEDJ = f"{ROOT}/outputs/elevation_sweep_md.json"
LEDN = f"{ROOT}/outputs/elevation_sweep_md.npz"
OUT = f"{ROOT}/outputs/prf_ladder_0828.json"
MESH = "mfixbatteryi5_blperairframe"

#: 다섯 팔 — 사용자 확정 축. ⭐확산 F 는 항상 켠다.
ARMS = [("①all off (diffuse only)", "R0D0E0F1"),
        ("②refraction",             "R1D0E0F1"),
        ("③diffraction",            "R0D1E1F1"),
        ("④refraction+diffraction", "R1D1E1F1"),
        ("⑤ours (SBR+PO)",          None)]          # None = --engine ours
KS = [(1, ""), (2, "_prf39400"), (4, "_prf78800")]
ELS = [0.0, -30.0, -60.0, -90.0]
N_PEAKS = 10                    # 상위 몇 봉우리의 폭을 볼 것인가
RNG = np.random.default_rng(20260828)


def arm_name(bits, tag):
    if bits is None:
        return f"ours_r15_n8192{tag}_{MESH}"
    return f"sionna_p4000000000_sw{bits}_r15_n8192{tag}_{MESH}_d2"


def half_width_poses(a, n_peaks=N_PEAKS):
    """상위 봉우리들의 **반진폭 폭**(자세) 중앙값과 이웃 낙차(dB).

    ⚠배열 끝에 닿은 봉우리는 폭을 못 재므로 버린다.
    반환 (폭중앙값, 이웃낙차중앙값dB, 쓴 봉우리 수).
    """
    a = np.asarray(a, float)
    n = a.size
    # 국소 최대만 후보로
    loc = np.where((a[1:-1] >= a[:-2]) & (a[1:-1] >= a[2:]))[0] + 1
    if loc.size == 0:
        return None, None, 0
    loc = loc[np.argsort(a[loc])[::-1]][:n_peaks * 3]
    widths, drops = [], []
    for i in loc:
        half = a[i] / 2.0
        L = i
        while L > 0 and a[L] > half:
            L -= 1
        R = i
        while R < n - 1 and a[R] > half:
            R += 1
        if L == 0 or R == n - 1:                       # 끝에 닿았다 — 버린다
            continue
        widths.append(R - L)
        nb = 0.5 * (a[max(0, i - 1)] + a[min(n - 1, i + 1)])
        drops.append(20 * np.log10((nb + 1e-300) / (a[i] + 1e-300)))
        if len(widths) >= n_peaks:
            break
    if not widths:
        return None, None, 0
    return float(np.median(widths)), float(np.median(drops)), len(widths)


def white_null(n=8192, trials=200):
    """백색잡음이 같은 잣대에서 무엇을 내나 — 널 밴드."""
    w, d = [], []
    for _ in range(trials):
        x = RNG.normal(size=n) + 1j * RNG.normal(size=n)
        a = np.abs(x - x.mean())
        ww, dd, k = half_width_poses(a)
        if ww is not None:
            w.append(ww)
            d.append(dd)
    q = lambda v: (float(np.percentile(v, 2.5)), float(np.median(v)),
                   float(np.percentile(v, 97.5)))
    return dict(width_poses=q(w), neighbour_drop_db=q(d), trials=len(w))


def main():
    L = json.load(open(LEDJ, encoding="utf-8"))
    prf0 = float(L["_meta"]["prf_hz"])
    ffl = float(L["_meta"]["f_flash_hz"])
    Z = np.load(LEDN)
    rows = {(r["engine"], float(r["el_deg"])): r for r in L["rows"]}

    deg_per_pose = lambda k: 360.0 * (ffl / 2.0) / (prf0 * k)

    print("\n═══ PRF 사다리 · 섬광 폭이 격자를 따라가나 ═══")
    print(f"원장 {len(L['rows'])} 행 · PRF₀ {prf0:.0f} Hz · f_flash {ffl:.2f} Hz")
    print(f"자세 1 개 = " + " · ".join(f"k{k} {deg_per_pose(k):.4f}°" for k, _ in KS))

    cells, verdicts = {}, {}
    for el in ELS:
        print(f"\n── el {el:+.0f}°" + " " * 6
              + "".join(f"{'k=' + str(k):>26}" for k, _ in KS))
        for nm, bits in ARMS:
            line, thetas, ks = f"  {nm:<24}", [], []
            for k, tag in KS:
                eng = arm_name(bits, tag)
                key = f"{eng}/el{el:+.0f}"
                r = rows.get((eng, el))
                if key not in Z.files or r is None:
                    line += f"{'—':>26}"
                    continue
                E = Z[key]
                a = np.abs(np.asarray(E) - np.asarray(E).mean())
                w, d, npk = half_width_poses(a)
                if w is None:
                    line += f"{'없음':>26}"
                    continue
                th = w * deg_per_pose(k)
                cells[f"{nm}/el{el:+.0f}/k{k}"] = dict(
                    arm=eng, el_deg=el, k=k, prf_hz=prf0 * k,
                    width_poses=round(w, 2), theta_half_deg=round(th, 4),
                    neighbour_drop_db=round(d, 2), n_peaks_used=npk,
                    n_missing=int(r["n_missing"]))
                thetas.append(th)
                ks.append(k)
                line += f"{w:>7.1f}자세 {th:>7.3f}° {d:>6.1f}dB"
            print(line)
            if len(thetas) == len(KS):
                p = float(-np.polyfit(np.log(ks), np.log(thetas), 1)[0])
                v = ("A. 격자 산물" if p >= 0.75 else
                     "B. 물리" if p <= 0.25 else "C. 해상 못 함")
                verdicts[f"{nm}/el{el:+.0f}"] = dict(
                    p=round(p, 3), verdict_ko=v,
                    theta_half_deg=[round(t, 4) for t in thetas])
                print(f"  {'':<24}⇒ p = {p:+.3f}   {v}")

    null = white_null()
    print(f"\n백색잡음 널 (200 판): 폭 {null['width_poses'][1]:.1f} 자세 "
          f"· 이웃낙차 {null['neighbour_drop_db'][1]:.1f} dB "
          f"[{null['neighbour_drop_db'][0]:.1f}, {null['neighbour_drop_db'][2]:.1f}]")

    doc = dict(_meta=dict(
        generator="benchmark/prf_ladder_0828.py",
        question_ko=("PathSolver 섬광 폭이 자세 격자를 따라 내려가나(격자 산물), "
                     "아니면 각도로 수렴하나(물리)"),
        gpu_used=False, prf0_hz=prf0, f_flash_hz=ffl,
        deg_per_pose={f"k{k}": round(deg_per_pose(k), 4) for k, _ in KS},
        metric_ko=("θ_half = 상위 봉우리 반진폭 폭 중앙값 × 자세당 회전각. "
                   "⛔3σ 문턱 런길이는 쓰지 않는다 — 하한이 1 자세라 내려갈 자리가 없다."),
        decision_rule_ko="p ≥ 0.75 격자 산물 · p ≤ 0.25 물리 · 그 사이 해상 못 함",
        aperture_limit_ko=("개구 한계: 프로펠러 반경 0.137 m → 17.91° · "
                           "기체 대각 0.439 m → 5.59°(최악 하한). "
                           "θ_half 가 5.59° 보다 좁게 수렴하면 «폭은 있으나 개구보다 좁다» 다."),
        n_ledger_rows=len(L["rows"])),
        white_null=null, cells=cells, verdicts=verdicts)
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
