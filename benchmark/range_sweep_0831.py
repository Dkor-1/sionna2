# -*- coding: utf-8 -*-
"""range_sweep_0831.py — 박자가 거리를 따라 어떻게 가나 (다섯 팔 × 네 거리)

무엇을 묻나
-----------
0829~0830 에 거리 축(30·45·60·90 m)을 다 돌려 놓고 **읽는 스크립트가 없었다.**
물음은 하나다 — **가까이에서 본 순위 뒤집힘이 멀리서도 그대로인가.**

⛔el −90 은 뺀다. f_tip 이 앙각 코사인을 따라가 −90 에서 0 이 되므로
   «상한 위» 가 전체가 되어 이 잣대가 정의되지 않는다.
⛔절대 세기(level_db)를 거리끼리 견주지 않는다 — 자유공간 감쇠가 그대로 들어간다.
   `h1_over_floor_db` 는 **국소 바닥 위 솟음**이라 눈금과 무관하다. 그래서 이것만 쓴다.

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
OUT = f"{ROOT}/outputs/range_sweep_0831.json"
MESH = "mfixbatteryi5_blperairframe"

ARMS = [("①all off (diffuse only)", "R0D0E0F1"),
        ("②refraction",             "R1D0E0F1"),
        ("③diffraction",            "R0D1E1F1"),
        ("④refraction+diffraction", "R1D1E1F1"),
        ("⑤ours (SBR+PO)",          None)]
RANGES = [15, 30, 45, 60, 90]
ELS = [0.0, -30.0, -60.0]


def arm_name(bits, r):
    rtag = "" if r == 10 else f"_r{r:g}"
    if bits is None:
        return f"ours{rtag}_n8192_{MESH}"
    return f"sionna_p4000000000_sw{bits}{rtag}_n8192_{MESH}_d2"


def grid_mod(el):
    """⭐앙각마다 모듈을 다시 불러온다 — FT30 이 임포트 시점에 굳는다(0830 에 실제로 틀렸다)."""
    import importlib
    os.environ["SWGRID_EL"] = f"{el:g}"
    import build_switch_grid_figs as M
    importlib.reload(M)
    return M


def main():
    os.environ.setdefault("MPLBACKEND", "Agg")
    L = json.load(open(LEDJ, encoding="utf-8"))
    Z = np.load(LEDN)
    rows = {(r["engine"], float(r["el_deg"])): r for r in L["rows"]}

    cells, missing = {}, []
    for el in ELS:
        M = grid_mod(el)
        print(f"\n── el {el:+.0f}°  (f_tip {M.FT30:.1f} Hz)")
        hdr = "".join(f"{str(r) + ' m':>12}" for r in RANGES)
        print(f"  {'':<24}{hdr}")
        for nm, bits in ARMS:
            line = f"  {nm:<24}"
            for r in RANGES:
                eng = arm_name(bits, r)
                key = f"{eng}/el{el:+.0f}"
                rw = rows.get((eng, el))
                if key not in Z.files or rw is None:
                    line += f"{'—':>12}"
                    missing.append(f"{nm}/r{r}/el{el:+.0f}")
                    continue
                if int(rw.get("n_missing", 0)):
                    line += f"{'결측':>12}"
                    missing.append(f"{nm}/r{r}/el{el:+.0f} (결측)")
                    continue
                fr, Y = M.modspec(np.asarray(Z[key]))
                df = fr[1] - fr[0]
                floor = float(np.median(Y[(fr > 20) & (fr < 500)]))
                b = int(round(M.FFL / df))
                seg = Y[max(0, b - 3):b + 4]
                pk = max(0, b - 6) + int(np.argmax(Y[max(0, b - 6):b + 7]))
                v = float(10 * np.log10(seg.max() / floor))
                pkhz = float(fr[pk])
                cells[f"{nm}/r{r}/el{el:+.0f}"] = dict(
                    arm=nm, range_m=r, el_deg=el, h1_over_floor_db=round(v, 2),
                    h1_peak_hz=round(pkhz, 2),
                    peak_is_beat=bool(abs(pkhz - M.FFL) < 4.0))
                mark = "" if abs(pkhz - M.FFL) < 4.0 else "*"
                line += f"{v:>11.1f}{mark or ' '}"
            print(line)

    # ── 순위가 거리를 따라 유지되나
    print("\n═══ ⭐순위가 거리를 따라 유지되나 (1 등이 누구인가) ═══")
    ranks = {}
    for el in ELS:
        line = f"  el {el:+.0f}°  "
        for r in RANGES:
            got = [(c["h1_over_floor_db"], c["arm"]) for k, c in cells.items()
                   if c["range_m"] == r and c["el_deg"] == el and c["peak_is_beat"]]
            if not got:
                line += f"{'—':>16}"
                continue
            v, a = max(got)
            ranks[f"r{r}/el{el:+.0f}"] = dict(winner=a, value_db=round(v, 2),
                                              n_valid=len(got))
            line += f"{a.split('(')[0].strip()[1:12]:>16}"
        print(line)
    print(f"  {'':<9}" + "".join(f"{str(r) + ' m':>16}" for r in RANGES))

    json.dump(dict(_meta=dict(
        generator="benchmark/range_sweep_0831.py", gpu_used=False,
        question_ko="가까이에서 본 순위 뒤집힘이 멀리서도 그대로인가",
        metric_ko=("h1_over_floor_db — build_switch_grid_figs 와 같은 계산. "
                   "국소 바닥 위 솟음이라 눈금과 무관하다."),
        scope_ko=("⛔el −90 은 뺀다(f_tip=0 이라 잣대가 정의되지 않는다). "
                  "⛔절대 세기를 거리끼리 견주지 않는다 — 자유공간 감쇠가 그대로 들어간다."),
        confound_ko=("⛔⛔**두 엔진이 거리에 대해 대등하지 않다.** "
                     "PathSolver 팔은 전 거리에 --spp 4e9 로 고정해 돌렸는데, 표적이 가리는 "
                     "입체각이 1/r² 로 줄어 표적에 닿는 광선이 15 m 214,134 개에서 "
                     "90 m 5,948 개로 떨어진다(3 %). 집 규칙 rule_spp=(R/3)²×1M 에 견주면 "
                     "여유가 15 m 160 배에서 90 m 4.4 배로 36 배 줄어든다. "
                     "우리 커널(rcs_sbr)은 표면 격자를 표집하므로 거리로 성기어지지 않는다. "
                     "⇒ «스톡 엔진의 박자가 멀어지며 흐려진다» 를 **물리라고 말할 수 없다** — "
                     "광선 예산이 준 것과 갈라내지 못했다. 가르려면 spp 를 r² 로 올려 다시 "
                     "돌려야 한다."),
        star_ko="* 표시는 봉우리가 f_flash 가 아닌 칸 — 그 dB 는 박자 값이 아니다.",
        ranges_m=RANGES, els_deg=ELS, n_missing_cells=len(missing)),
        cells=cells, rank_by_range=ranks, missing=missing),
        open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {OUT}   (빈 칸 {len(missing)})")


if __name__ == "__main__":
    main()
