# -*- coding: utf-8 -*-
"""spread_band_0830.py — 박자 잣대의 «자연 산포» 를 잰다 (B 층 게이트)

무엇을 묻나
-----------
덱 7 장의 박자 표(`h1_over_floor_db`)에 **오차막대가 한 칸도 없다.**
`docs/EQUIVALENCE_GATES.md` B 층은 «밴드 안» 을 말하려면 **옛↔옛 산포를 먼저 재라**고
요구한다. PathSolver 는 결정적이지 않으므로(NVlabs/sionna #1175 — 회절 웨지 중복제거
해시 테이블 삽입 순서) 같은 인자로 여러 판 돌리면 값이 갈린다.

⇒ 같은 칸을 여러 판(`--rep`) 돌려 그 갈림폭을 잰다. **이 폭보다 작은 차이는
   «다르다» 고 말할 수 없다.**

⛔**거리 주의 — 2026-08-30 에 실제로 틀렸다.**
   `RANGE_M` 기본값은 **10 m** 다. 덱 표가 쓰는 팔은 `--range-m 15` 로 만든 `_r15` 판이다.
   내가 만든 첫 되풀이 큐는 `--range-m` 을 안 줘서 **10 m** 로 났다. 그래서 이 판독기는
   **거리를 명시적으로 갈라서** 읽고, 섞이면 소리 내어 거른다.

잣대 — `build_switch_grid_figs.py` 와 **똑같이** 계산한다
--------------------------------------------------------
  변조 스펙트럼 → 20~500 Hz 중앙값을 바닥으로 → f_flash 빈 ±3 의 최댓값 / 바닥 [dB]

⛔GPU 를 쓰지 않는다.
"""
import json
import os
import sys
import numpy as np

ROOT = "/workspace/sionna"
sys.path.insert(0, f"{ROOT}/benchmark")
LEDJ = f"{ROOT}/outputs/elevation_sweep_md.json"
LEDN = f"{ROOT}/outputs/elevation_sweep_md.npz"
OUT = f"{ROOT}/outputs/spread_band_0830.json"
MESH = "mfixbatteryi5_blperairframe"
ELS = [0.0, -30.0, -60.0]

#: 다섯 팔 — 사용자 확정 축. ⭐확산 F 는 항상 켠다.
ARMS = [("①all off (diffuse only)", "R0D0E0F1"),
        ("②refraction",             "R1D0E0F1"),
        ("③diffraction",            "R0D1E1F1"),
        ("④refraction+diffraction", "R1D1E1F1"),
        ("⑤ours (SBR+PO)",          None)]
REPS = [0, 1, 2, 3, 4, 5]          # 0 = 꼬리표 없는 판


def arm_name(bits, rep, r15):
    """⭐거리를 명시적으로 받는다 — 10 m 판과 15 m 판을 절대 섞지 않는다."""
    rtag = "_r15" if r15 else ""
    reptag = "" if not rep else f"_rep{rep}"
    if bits is None:
        return f"ours{rtag}_n8192{reptag}_{MESH}"
    return f"sionna_p4000000000_sw{bits}{rtag}_n8192{reptag}_{MESH}_d2"


def grid_mod(el):
    """⭐앙각마다 모듈을 다시 불러온다.

    ⛔`build_switch_grid_figs.FT30` 은 **임포트 시점에** 환경변수 `SWGRID_EL` 로 굳고,
       `modspec()` 의 블레이드 대역 마스크(0.35~1.0 × f_tip)가 그 값을 쓴다.
       한 번만 불러오면 모든 앙각이 −30° 대역으로 읽혀 값이 틀린다.
       2026-08-30 에 실제로 틀렸다 — el −60 에서 43.5 dB 가 나왔는데 정본은 57.8 dB 다.
    """
    import importlib
    os.environ["SWGRID_EL"] = f"{el:g}"
    import build_switch_grid_figs as M
    importlib.reload(M)
    return M


def h1_over_floor(E, modspec, ffl):
    """⭐build_switch_grid_figs.py:225-231 과 같은 계산."""
    fr, Y = modspec(np.asarray(E))
    df = fr[1] - fr[0]
    floor = float(np.median(Y[(fr > 20) & (fr < 500)]))
    b = int(round(ffl / df))
    seg = Y[max(0, b - 3):b + 4]
    pk = max(0, b - 6) + int(np.argmax(Y[max(0, b - 6):b + 7]))
    return float(10 * np.log10(seg.max() / floor)), float(fr[pk])


def main():
    os.environ.setdefault("MPLBACKEND", "Agg")

    L = json.load(open(LEDJ, encoding="utf-8"))
    Z = np.load(LEDN)
    rows = {(r["engine"], float(r["el_deg"])): r for r in L["rows"]}

    doc, cells = {}, {}
    for r15 in (True, False):
        rlab = "15 m (덱 표가 쓰는 판)" if r15 else "10 m (기본값)"
        print(f"\n═══ 거리 {rlab} ═══")
        for el in ELS:
            M = grid_mod(el)                 # ⭐앙각마다 다시 불러온다
            modspec, FFL = M.modspec, M.FFL
            print(f"\n── el {el:+.0f}° (f_tip {M.FT30:.1f} Hz)")
            for nm, bits in ARMS:
                vals, got = [], []
                for rep in REPS:
                    eng = arm_name(bits, rep, r15)
                    key = f"{eng}/el{el:+.0f}"
                    if key not in Z.files or (eng, el) not in rows:
                        continue
                    r = rows[(eng, el)]
                    if int(r.get("n_missing", 0)):      # ⛔결측이 있으면 안 쓴다
                        continue
                    v, pk = h1_over_floor(Z[key], modspec, FFL)
                    vals.append(v)
                    got.append(rep)
                if not vals:
                    continue
                a = np.array(vals)
                key = f"{'r15' if r15 else 'r10'}/{nm}/el{el:+.0f}"
                cells[key] = dict(
                    range_m=15.0 if r15 else 10.0, arm=nm, el_deg=el,
                    reps=got, n=len(vals),
                    h1_over_floor_db=[round(x, 3) for x in vals],
                    median=round(float(np.median(a)), 3),
                    spread_pp=round(float(a.max() - a.min()), 3),
                    std=round(float(a.std(ddof=1)), 4) if len(a) > 1 else None)
                s = f"폭 {a.max()-a.min():.3f} dB" if len(a) > 1 else "판 하나 — 폭 못 냄"
                print(f"  {nm:<24} 판 {len(vals)} (rep {got}) "
                      f"중앙값 {np.median(a):7.2f} dB · {s}")

    # ── 덱 주장이 밴드를 넘나
    print("\n═══ ⭐덱 7 장 주장이 산포 밴드를 넘나 ═══")
    claims = []
    for r15 in (True, False):
        p = "r15" if r15 else "r10"
        for el, a1, a2, ko in ((0.0, "⑤ours (SBR+PO)", "③diffraction", "정면 ⑤ vs ③"),
                               (-30.0, "①all off (diffuse only)", "⑤ours (SBR+PO)", "빗각 ① vs ⑤"),
                               (-60.0, "①all off (diffuse only)", "⑤ours (SBR+PO)", "빗각 ① vs ⑤")):
            c1, c2 = cells.get(f"{p}/{a1}/el{el:+.0f}"), cells.get(f"{p}/{a2}/el{el:+.0f}")
            if not c1 or not c2:
                continue
            d = c1["median"] - c2["median"]
            # ⭐판이 하나뿐인 칸은 «밴드 0» 이 아니라 «밴드를 안 쟀다» 다
            measured = c1["n"] > 1 and c2["n"] > 1
            band = max(c1["spread_pp"] or 0, c2["spread_pp"] or 0)
            ok = (abs(d) > band) if measured else None
            claims.append(dict(range_m=c1["range_m"], el_deg=el, pair=ko,
                               diff_db=round(d, 3),
                               band_db=round(band, 3) if measured else None,
                               n_reps=[c1["n"], c2["n"]],
                               band_measured=bool(measured), survives=ok,
                               note_ko=("⛔밴드를 안 쟀다 — 판이 하나뿐이라 «넘는다» 고 "
                                        "말할 수 없다" if not measured else
                                        "차이가 산포 밴드보다 크다 — 말할 수 있다" if ok else
                                        "⛔차이가 산포 밴드 안이다 — 말할 수 없다")))
            tag = ("⚠밴드 미측정 (판 %d·%d)" % (c1["n"], c2["n"]) if not measured
                   else ("✅ 넘는다" if ok else "⛔밴드 안"))
            bs = f"{band:.3f} dB" if measured else "—"
            print(f"  {c1['range_m']:.0f} m · el {el:+.0f} {ko:<14} "
                  f"차이 {d:+7.2f} dB · 밴드 {bs:>9}  {tag}")

    json.dump(dict(_meta=dict(
        generator="benchmark/spread_band_0830.py", gpu_used=False,
        metric_ko="h1_over_floor_db — build_switch_grid_figs.py 와 같은 계산",
        question_ko=("같은 인자로 여러 판 돌렸을 때 박자 값이 얼마나 갈리나. "
                     "이 폭보다 작은 차이는 «다르다» 고 말할 수 없다."),
        why_ko=("PathSolver 는 결정적이지 않다(NVlabs/sionna #1175). "
                "docs/EQUIVALENCE_GATES.md B 층이 옛↔옛 산포를 먼저 재라고 요구한다."),
        range_warning_ko=("⛔RANGE_M 기본값은 10 m 다. 덱 표가 쓰는 팔은 --range-m 15 로 "
                          "만든 _r15 판이다. 2026-08-30 에 첫 되풀이 큐가 --range-m 을 "
                          "빠뜨려 10 m 로 났다. 두 거리를 절대 섞어 읽지 않는다."),
        n_ledger_rows=len(L["rows"])),
        cells=cells, claim_checks=claims),
        open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}")


if __name__ == "__main__":
    main()
