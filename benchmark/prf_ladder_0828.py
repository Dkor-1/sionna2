# -*- coding: utf-8 -*-
"""prf_ladder_0828.py — 섬광 폭이 자세 격자를 따라가나, 각도로 수렴하나 (PRF 사다리)

무엇을 묻나
-----------
PathSolver 섬광은 «자세 하나» 폭이다(0825 판독: 중앙값 1 자세 · 98.2 %가 한 자세짜리).
⚠**한 자세 폭 자체는 PathSolver 만의 성질이 아니다** — 우리 커널도 el 0·−15·−30·−90 에서
  중앙값 1 자세이고, el −90 에서는 한-자세 비율이 100 % 다(`crossterm_elev_sweep_0825.json`).
  두 엔진을 실제로 가르는 것은 **한-자세 사건의 비율(98.2 % 대 52.6 %)과 첨도(139 대 3.0)** 다.

개구 한계는 다음과 같다:
  프로펠러 **반경** 0.137 m → λ/2D = 17.91°
  기체 대각   0.439 m      → 5.59° (**최악 하한**)
⛔**«그러니 더 넓어야 한다» 고 말하지 않는다.** 그건 현실성 판정이고 이 스크립트는 그걸 못 잰다.
   묻는 것은 하나다 — **관측된 좁은 폭이 표집 격자를 따라가나, 아니면 각도로 버티나.**

⛔**`--n-poses` 로는 못 묻는다.** 자세 간격 dt = 1/PRF 는 n 과 무관하므로 n 을 4 배 해도
   «4 배 긴 기록»일 뿐 촘촘해지지 않는다(블레이드 통과당 자세 수 155.5 로 불변).
⇒ **PRF 를 k 배 올린다.** t_i = i/(k·PRF₀) 이므로 k 단의 자세 i·k 가 k=1 의 자세 i 와
   **같은 시각**이다 — 같은 섬광을 촘촘히 다시 보는 «짝지은» 관측이다.

잣대 — ⛔«자세 개수» 를 버리고 **도(°)** 로 간다
------------------------------------------------
자세 하나가 가리키는 회전각이 k 에 반비례하므로(k=1 1.157° · k=4 0.289°),
«1 자세» 라는 말은 k 마다 뜻이 다르다. 그래서 폭을 각도로 환산해 비교한다.

  θ_half [°] = (상위 봉우리의 반진폭 폭 중앙값, 자세) × 360·(f_flash/2)/PRF

⚠3σ 문턱 런길이(옛 `median_event_width_poses`)는 쓰지 않는다 — 문턱을 기록 자신이
  만들고 하한이 1 자세라 내려갈 자리가 없다. 반진폭 폭은 문턱이 없다.

⛔⛔**그런데 이 잣대에도 하한이 있다 — 2 자세다**(국소최대 하나와 양옆).
   2026-08-29 검증에서 드러났다: **p=+1.000 판정 10 칸이 전부 k=1·2·4·8 에서 폭 2.0** 이다.
   하한에 붙으면 θ_half ∝ 1/k 가 잔차 0 으로 자동 성립하므로 **p=1 은 적합이 아니라 항등식**이고,
   뜻은 «폭이 표집에 딸린다» 가 아니라 **«매 k 마다 여전히 하한이라 폭을 못 쟀다»** 다.
   ⇒ 하한 고정을 먼저 걸러 **D 판정**으로 뺀다. 옛 잣대를 버린 사유가 여기서 되풀이됐다.

판정 (네 점 k=1,2,4,8 에서 log θ_half 대 log k 의 기울기 p — θ_half ∝ k^−p)
----------------------------------------------------------------------------
  ⭐먼저: 네 k 전부 폭이 하한(2 자세)이면
            ⇒ D. **이 잣대로는 폭을 못 쟀다** — 하한에 붙어 있다. p 를 읽지 않는다
  p ≥ 0.75  ⇒ A. **폭이 표집에 딸린다** — 촘촘히 볼수록 각도 폭이 그만큼 좁아진다
  p ≤ 0.25  ⇒ B. **폭이 각도로 수렴한다** — 표집을 바꿔도 각도 폭이 그대로다
  그 사이   ⇒ C. **이 표집으로는 해상 못 한다**

⚠**A 칸과 B 칸은 같은 종류의 대상이 아니다.** 이웃 낙차를 보면 갈린다 —
  하한 고정 칸은 −18~−54 dB(고립 스파이크), B 칸은 −0.06~−0.8 dB(사실상 연속 곡선)다.
  즉 한 p 축이 «고립 스파이크가 얼마나 좁은가» 와 «연속 곡선의 물결이 얼마나 넓은가» 를
  한꺼번에 얹고 있다. **판정을 엔진 간 우열로 읽으면 안 되는 이유가 여기 있다.**

⚠**백색 널과 겹치는 칸을 표시한다.** 널(200 판) 폭 2.0 [2.0, 3.0] · 이웃 낙차 −9.98 dB
  [−12.58, −7.58]. 낙차가 이 밴드 안이면 «잡음과 구별 안 됨» 으로 꼬리표를 단다.

⛔**이 잣대가 «어느 엔진이 현실에 가까운가» 를 말하지 않는다.**
   재는 것은 «섬광 폭이 표집 격자를 따라가나» 하나뿐이다.
   · A 가 «틀렸다» 는 뜻이 아니다. 실제 평평한 블레이드 면의 정반사는 정말로 아주 좁을 수 있고,
     PathSolver 가 이상화 물리와 다른 것이 오히려 현실을 담은 것일 수도 있다.
   · B 가 «맞다» 는 뜻도 아니다. 우리 커널(SBR+PO)도 **근사**다 — 매끄러움이 제대로
     모델링해서인지 «덜 잡아서» 인지 이 데이터로 못 가른다(0827 `ee61028` 이 명시).
   · ⚠**같은 잣대를 우리 커널에도 그대로 댄다** — ⑤/el−90 의 θ_half 1.3~2.3° 는 이 스크립트가
     세운 개구 최악 하한 5.59° 보다 **좁다**. 우리 커널도 그 칸에서는 해명이 안 된다.
   ⇒ 판정은 **표집 의존성**에 대한 것이고, 현실성 판정은 **실측 대조가 있어야** 한다.

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
KS = [(1, ""), (2, "_prf39400"), (4, "_prf78800"), (8, "_prf157600")]
ELS = [0.0, -30.0, -60.0, -90.0]
N_PEAKS = 10                    # 상위 몇 봉우리의 폭을 볼 것인가
WIDTH_FLOOR = 2.0               # ⭐반진폭 폭 탐색의 하한 — 국소최대 하나와 양옆
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

    null = white_null()                 # ⭐판정에서 널 밴드를 쓰므로 먼저 낸다
    print(f"\n백색잡음 널 (200 판): 폭 {null['width_poses'][1]:.1f} 자세 "
          f"[{null['width_poses'][0]:.1f}, {null['width_poses'][2]:.1f}] "
          f"· 이웃낙차 {null['neighbour_drop_db'][1]:.1f} dB "
          f"[{null['neighbour_drop_db'][0]:.1f}, {null['neighbour_drop_db'][2]:.1f}]")

    cells, verdicts = {}, {}
    for el in ELS:
        print(f"\n── el {el:+.0f}°" + " " * 6
              + "".join(f"{'k=' + str(k):>26}" for k, _ in KS))
        for nm, bits in ARMS:
            line, thetas, ks, ws_all, dr_all = f"  {nm:<24}", [], [], [], []
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
                ws_all.append(w)
                dr_all.append(d)
                line += f"{w:>7.1f}자세 {th:>7.3f}° {d:>6.1f}dB"
            print(line)
            if len(thetas) == len(KS):
                p = float(-np.polyfit(np.log(ks), np.log(thetas), 1)[0])
                # ⭐하한 고정을 먼저 거른다 — p 는 이때 항등식이라 읽으면 안 된다
                pinned = all(w <= WIDTH_FLOOR for w in ws_all)
                if pinned:
                    v = "D. 이 잣대로는 폭을 못 쟀다 — 하한 2 자세에 붙어 있다"
                else:
                    v = ("A. 폭이 표집에 딸린다" if p >= 0.75 else
                         "B. 폭이 각도로 수렴한다" if p <= 0.25 else
                         "C. 이 표집으로는 해상 못 한다")
                lo, hi = null["neighbour_drop_db"][0], null["neighbour_drop_db"][2]
                in_null = [bool(lo <= x <= hi) for x in dr_all]
                verdicts[f"{nm}/el{el:+.0f}"] = dict(
                    p=round(p, 3), verdict_ko=v,
                    floor_pinned=bool(pinned),
                    width_poses=[round(w, 1) for w in ws_all],
                    neighbour_drop_db=[round(x, 2) for x in dr_all],
                    in_white_null=in_null,
                    near_threshold=bool(not pinned and
                                        (abs(p - 0.25) < 0.05 or abs(p - 0.75) < 0.05)),
                    theta_half_deg=[round(t, 4) for t in thetas])
                mark = ""
                if pinned:
                    mark = "  ⚠하한고정 — p 는 항등식"
                elif any(in_null):
                    mark = f"  ⚠널밴드 겹침 {sum(in_null)}/{len(in_null)}칸"
                elif abs(p - 0.25) < 0.05 or abs(p - 0.75) < 0.05:
                    mark = "  ⚠문턱에 걸침"
                print(f"  {'':<24}⇒ p = {p:+.3f}   {v}{mark}")

    doc = dict(_meta=dict(
        generator="benchmark/prf_ladder_0828.py",
        question_ko=("관측된 좁은 섬광 폭이 자세 표집 격자를 따라 내려가나, "
                     "아니면 각도로 버티나. ⛔어느 엔진이 현실에 가까운지는 묻지 않는다."),
        gpu_used=False, prf0_hz=prf0, f_flash_hz=ffl,
        deg_per_pose={f"k{k}": round(deg_per_pose(k), 4) for k, _ in KS},
        metric_ko=("θ_half = 상위 봉우리 반진폭 폭 중앙값 × 자세당 회전각. "
                   "⛔3σ 문턱 런길이는 쓰지 않는다 — 하한이 1 자세라 내려갈 자리가 없다."),
        decision_rule_ko=("⭐먼저 네 k 전부 폭이 하한(2 자세)이면 D. 이 잣대로는 폭을 못 쟀다 — "
                          "그때 p 는 적합이 아니라 항등식이라 읽지 않는다. "
                          "그 다음 p ≥ 0.75 폭이 표집에 딸린다 · p ≤ 0.25 폭이 각도로 수렴한다 · "
                          "그 사이 이 표집으로는 해상 못 한다"),
        width_floor_ko=("반진폭 폭 탐색의 하한은 2 자세다(국소최대 하나와 양옆). "
                        "하한에 붙으면 θ_half ∝ 1/k 가 잔차 0 으로 자동 성립해 p=1 이 된다. "
                        "2026-08-29 검증에서 옛 A 판정 10 칸이 전부 이 경우였다."),
        not_symmetric_ko=("⚠A/D 칸과 B 칸은 같은 종류의 대상이 아니다 — 이웃 낙차가 "
                          "각각 −18~−54 dB(고립 스파이크)와 −0.06~−0.8 dB(연속 곡선)다. "
                          "한 p 축이 두 가지를 얹고 있으니 엔진 간 우열로 읽지 마라."),
        scope_ko=("⛔이 잣대는 «어느 엔진이 현실에 가까운가» 를 말하지 않는다. "
                  "재는 것은 표집 의존성 하나뿐이다. A 가 틀렸다는 뜻이 아니고"
                  "(실제 정반사가 정말 좁을 수 있다), B 가 맞다는 뜻도 아니다"
                  "(우리 커널도 근사이고, 매끄러움이 «덜 잡아서» 일 수 있다 — 0827 ee61028). "
                  "현실성 판정에는 실측 대조가 필요하다."),
        aperture_limit_ko=("개구 한계: 프로펠러 반경 0.137 m → 17.91° · "
                           "기체 대각 0.439 m → 5.59°(최악 하한). "
                           "θ_half 가 5.59° 보다 좁게 수렴하면 «폭은 있으나 개구보다 좁다» 다. "
                           "⛔«그러니 더 넓어야 한다» 는 현실성 판정이라 이 잣대가 못 한다. "
                           "⚠이 하한은 우리 커널에도 그대로 댄다 — ⑤/el−90 도 5.59° 보다 좁다."),
        n_ledger_rows=len(L["rows"])),
        white_null=null, cells=cells, verdicts=verdicts)
    json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
