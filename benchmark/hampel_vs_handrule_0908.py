#!/usr/bin/env python
"""«튀는 자세»를 손 규칙 대신 **햄펠 필터**로 잡는다 — 둘을 나란히 잰다.

왜 있나 — 2026-09-08 에 사용자가 물었다: 「값이 튀는 부분을 일일이 확인해서 제거하는
방향으로 후처리하는 것 같은데, 저런 이상치 제거에 어울리는 필터가 있지 않나? 미디안 필터?」

**맞다.** 지금까지 쓰던 손 규칙은 사실상 햄펠 필터를 손으로 만든 것인데, 두 군데가 나쁘다:

  ⛔① **전체 중앙값**을 기준으로 삼는다. 실외에서는 지면이 중앙 레벨을 +44.5 dB 올려
     놓아서, 그 기준이 «드론이 보통 얼마나 밝은가» 가 아니라 «지면이 얼마나 밝은가» 가 된다.
  ⛔② **문턱이 둘**이다. 꺼진 자세 0.1 과 밝은 자세 1.05 — 2026-09-07 감사에서 1.05 를
     1 % 만 올려도 판정이 뒤집히는 것이 잡혔다(자세 하나가 16.33 dB 를 갈랐다).

햄펠은 **미끄러지는 창 안의 국소 중앙값**과 MAD 를 쓴다:

    이상치 ⟺ |x − 국소중앙| > k · 1.4826 · MAD

  ⭐국소 중앙값이라 날개 변조를 «정상» 으로 보고 튀는 자세만 잡는다.
  ⭐위·아래를 한 잣대로 잡으므로 «꺼진»·«밝은» 두 문턱이 하나로 준다.

  ⛔**2026-09-08 설계 검토가 두 가지를 낮췄다:**
    ⑭ 입력이 복소 E 의 **절댓값**이라 **진폭이 같은 위상 점프는 못 본다**(위상만 뒤집은
       합성 입력에서 표식이 안 나온다). 그리고 국소적으로 뾰족한 «정상» 날개 플래시가
       창·문턱에 따라 잡힐 수 있다 — 국소 중앙값이라는 이유만으로 배제 못 한다.
       ⇒ «이상치를 모두 찾는다» 가 아니라 «선택한 창·문턱에서 **진폭** 이상 후보를
         표시했다» 까지다.
    ⑮ `recovered` 는 **빗살 지표가 자유공간 지표에 가까워졌나**일 뿐, 그 자세의
       **정답 신호와 견준 것이 아니다.** 빗살 지표는 대역 안 조화선 대 바닥의 비라
       **바닥이 줄어도 오른다** — 보간이 바닥을 깎으면 지표가 오를 수 있다.
       ⇒ «복원됐다»·«돌아왔다» 가 아니라 «선택한 지표가 가까워졌다» 로 쓴다.
       원래 파형과 탐지 성능의 복원은 **확인하지 않았다.**

■ 실측 (2026-09-08 · 창 5 × k 5 = 25 판을 흔들었다)
  · 회절 끈 두 팔(R0D0E0F1 · R1D0E0F1)은 앙각 다섯 자리 전부에서 25 판 중 24~25 판이
    빈 하늘과 3 dB 안에 든다. 손 규칙이 못 살리던 el −60(16.53 dB)이 49.8~51.9 로 돌아온다.
  · ⚠회절 켠 두 팔은 다르다 — el −45·−75 에서 햄펠 뒤 값이 **빈 하늘보다 높다**
    (예: R0D1E1F1 el−45 빈 하늘 9.1 → 햄펠 20.1~23.1). 필터가 없던 구조를 만들었는지,
    그 칸의 빈 하늘 값 자체가 눌려 있는지 **안 갈랐다.** ⛔그 팔에는 아직 쓰지 않는다.

⛔이 원장은 «어느 쪽이 옳다» 를 말하지 않는다 — 두 방법의 수를 나란히 놓는다.
⛔메우기는 어느 쪽이든 «이상치를 이웃값으로 갈아끼우는» 것이라, 그 자세의 진짜 값을
  복원하지 않는다. 「빗살이 돌아온다」는 «그 자세들이 빗살을 가리고 있었다» 까지다.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 nice -n 19 \
      PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
      benchmark/hampel_vs_handrule_0908.py
    → outputs/hampel_vs_handrule_0908.json
"""
from __future__ import annotations

import argparse, glob, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (HERE, os.path.join(ROOT, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import comb_snr as CS                                                  # noqa: E402

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "hampel_vs_handrule_0908.json")
MESH = "mfixbatteryi5_blperairframe"
PRF = 19700.0
DIP, BRIGHT = 0.1, 1.05          # 손 규칙의 두 문턱 (견주기 위해 그대로 쓴다)
WINS = (31, 51, 71, 101, 151)    # 햄펠 창 [자세]
KS = (3.0, 4.0, 5.0, 6.0, 8.0)   # 햄펠 문턱 [MAD 배수]
GAP_OK = 3.0                     # 「돌아왔다」 = 빈 하늘과 이 안


def load(tag, el, arm):
    fs = sorted(glob.glob(
        f"{SHD}/sionna_p4000000000_sw{arm}_r15_n8192_{tag}{MESH}_d2_el{el:+g}_*.npz"))
    if not fs:
        return None
    E, I = [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
    return np.concatenate(E)[np.argsort(np.concatenate(I))]


def hand_mask(E, dip=DIP, bright=None):
    """옛 손 규칙 — **전체** 중앙값 대비 문턱 둘."""
    a = np.abs(E)
    r = a / float(np.median(a))
    m = r < dip
    if bright is not None:
        m = m | (r > bright)
    return m


def hampel_mask(x, win, k):
    """햄펠 — 미끄러지는 창의 국소 중앙값과 MAD.

    ⚠가장자리는 `reflect` 로 채운다. 자세열은 로터 각도라 **주기적**이므로 `wrap` 이
      더 옳을 수 있는데, 8,192 자세가 박자 주기의 정수배가 아니라(52.7 주기) wrap 이
      이음매를 만든다. 그래서 reflect 를 쓰고, 이 선택이 결과를 정하는지는
      창 크기를 흔들어 본다(창이 커질수록 가장자리 몫이 는다).
    """
    h = win // 2
    W = np.lib.stride_tricks.sliding_window_view(np.pad(x, (h, h), mode="reflect"), win)
    med = np.median(W, axis=1)
    mad = np.median(np.abs(W - med[:, None]), axis=1) * 1.4826
    return np.abs(x - med) > k * np.maximum(mad, 1e-300)


def fill(E, bad):
    """이상치를 이웃값으로 갈아끼운다(복소수 실·허부 각각 선형보간)."""
    if not bad.any():
        return E, 0
    g = np.where(~bad)[0]
    b = np.where(bad)[0]
    if g.size < 2:
        return E, 0
    R = E.copy()
    R[b] = np.interp(b, g, E[g].real) + 1j * np.interp(b, g, E[g].imag)
    return R, int(b.size)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="R0D0E0F1,R1D0E0F1,R0D1E1F1,R1D1E1F1")
    ap.add_argument("--els", default="-15,-30,-45,-60,-75")
    ap.add_argument("--scenes", default="envoutdoor01_,envsionna-simple_street_canyon_,"
                                        "envsionna-munich_",
                    help="견줄 장면 꼬리표. ⭐우리가 만들지 않은 씬을 함께 넣는 것이 요점이다")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    t0, cells = time.time(), {}
    for arm in a.arms.split(","):
        for el in [float(x) for x in a.els.split(",")]:
            F = load("", el, arm)
            if F is None:
                continue
            for _tag in a.scenes.split(","):
                if not _tag:
                    continue
                O = load(_tag, el, arm)
                if O is None or O.size != F.size:
                    continue
                nm = f"sionna_p4000000000_sw{arm}_r15_n8192_{_tag}{MESH}_d2"

                def snr(x, _nm=nm, _el=el):
                    v = CS.comb_snr(np.asarray(x), PRF, _el, arm=_nm)
                    return None if v is None else round(float(v), 2)

                free, raw = snr(F), snr(O)
                if free is None:
                    continue
                c = {"arm": arm, "el_deg": el, "scene": _tag or "(free)",
                     "comb_free_db": free, "comb_out_db": raw}

                #: ── 옛 손 규칙 두 갈래 ─────────────────────────────────
                for lbl, bright in (("hand_dip_only", None),
                                    ("hand_dip_and_bright", BRIGHT)):
                    m = hand_mask(O, DIP, bright)
                    R, n = fill(O, m)
                    v = snr(R)
                    c[lbl] = {"n_replaced": n, "comb_db": v,
                              "gap_db": None if v is None else round(v - free, 2),
                              "recovered": None if v is None
                              else bool(abs(v - free) <= GAP_OK)}

                #: ── 햄펠 — 손잡이를 흔든다 ─────────────────────────────
                grid, hand_m = {}, hand_mask(O, DIP, None)
                for w in WINS:
                    for k in KS:
                        hm = hampel_mask(np.abs(O), w, k)
                        R, n = fill(O, hm)
                        v = snr(R)
                        grid[f"win{w}_k{k:g}"] = {
                            "n_replaced": n, "comb_db": v,
                            "gap_db": None if v is None else round(v - free, 2),
                            "recovered": None if v is None
                            else bool(abs(v - free) <= GAP_OK),
                            "covers_hand_dips": bool((hm | ~hand_m).all()),
                        }
                c["hampel_grid"] = grid
                vs = [g["comb_db"] for g in grid.values() if g["comb_db"] is not None]
                ns = [g["n_replaced"] for g in grid.values()]
                if not vs:
                    continue
                ok = sum(1 for g in grid.values() if g["recovered"])
                c["hampel_summary"] = {
                    "n_settings": len(grid), "n_recovered": ok,
                    "comb_db_min": round(min(vs), 2), "comb_db_max": round(max(vs), 2),
                    "comb_db_median": round(float(np.median(vs)), 2),
                    "spread_db": round(max(vs) - min(vs), 2),
                    "n_replaced_min": int(min(ns)), "n_replaced_max": int(max(ns)),
                    #: ⛔갈아끼운 자세가 너무 많으면 «이상치 제거» 가 아니라 신호를 뭉갠 것이다
                    "replaced_share_max_pct": round(100.0 * max(ns) / O.size, 2),
                    "all_cover_hand_dips": all(g["covers_hand_dips"]
                                               for g in grid.values()),
                    "exceeds_free_space": bool(min(vs) > free + GAP_OK),
                }
                key = f"{arm}/el{el:+.0f}/{(_tag or 'free').rstrip('_')}"
                cells[key] = c
                print(f"  {key}  빈하늘 {free:>6.1f} · 그대로 {raw:>5.1f} · "
                      f"햄펠 {c['hampel_summary']['comb_db_min']:>6.1f}~"
                      f"{c['hampel_summary']['comb_db_max']:>6.1f} "
                      f"({ok}/{len(grid)} 돌아옴 · 갈아낀 자세 "
                      f"{c['hampel_summary']['replaced_share_max_pct']:.1f}% 까지)",
                      flush=True)

    tot = len(cells)
    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "benchmark/hampel_vs_handrule_0908.py",
            "question_ko": "튀는 자세를 손 규칙으로 잡을 것인가 햄펠 필터로 잡을 것인가",
            "hand_rule_ko": f"전체 중앙값 대비 |E| < {DIP} (그리고 갈래에 따라 > {BRIGHT})."
                            " ⛔전체 중앙값은 실외에서 지면이 +44.5 dB 올려 놓은 값이다",
            "hampel_ko": "미끄러지는 창의 국소 중앙값과 MAD — |x − 국소중앙| > k·1.4826·MAD."
                         f" 창 {list(WINS)} × k {list(KS)} 를 흔들었다",
            "recovered_rule_ko": f"메운 뒤 값이 빈 하늘과 {GAP_OK} dB 안이면 «돌아왔다»",
            "edge_ko": "가장자리는 reflect 로 채운다 — 자세열은 주기적이지만 8,192 가 박자"
                       " 주기의 정수배가 아니라(52.7 주기) wrap 이 이음매를 만든다",
            "limits_ko": [
                "⛔어느 쪽이 «옳다» 를 말하지 않는다 — 두 방법의 수를 나란히 놓는다.",
                "⛔메우기는 그 자세의 진짜 값을 복원하지 않는다. 말할 수 있는 것은"
                " «그 자세들이 빗살을 가리고 있었다» 까지다.",
                "⛔exceeds_free_space 가 참인 칸에는 이 방법을 쓰지 않는다 —"
                " 필터가 없던 구조를 만들었는지 안 갈랐다.",
                "⛔이 저장소에 실기 계측 대조는 0 건이다.",
            ],
        },
        "summary": {
            "n_cells": tot,
            "hand_dip_only_recovered": sum(
                1 for c in cells.values() if c["hand_dip_only"]["recovered"]),
            "hand_dip_and_bright_recovered": sum(
                1 for c in cells.values() if c["hand_dip_and_bright"]["recovered"]),
            "hampel_recovered_all_settings": sum(
                1 for c in cells.values()
                if c["hampel_summary"]["n_recovered"] == c["hampel_summary"]["n_settings"]),
            "hampel_recovered_no_setting": sum(
                1 for c in cells.values() if c["hampel_summary"]["n_recovered"] == 0),
            #: ⭐⭐**우리가 만들지 않은 씬에서도 되나** — 이것이 결론의 유효 범위를 정한다
            "by_scene": {
                sc: {"n_cells": sum(1 for c in cells.values() if c["scene"] == sc),
                     "n_recovered_all_settings": sum(
                         1 for c in cells.values() if c["scene"] == sc
                         and c["hampel_summary"]["n_recovered"]
                         == c["hampel_summary"]["n_settings"]),
                     "max_replaced_share_pct": max(
                         [c["hampel_summary"]["replaced_share_max_pct"]
                          for c in cells.values() if c["scene"] == sc] or [0])}
                for sc in sorted({c["scene"] for c in cells.values()})},
            "cells_where_hampel_exceeds_free": [
                k for k, c in cells.items() if c["hampel_summary"]["exceeds_free_space"]],
            "hampel_always_covers_hand_dips": all(
                c["hampel_summary"]["all_cover_hand_dips"] for c in cells.values()),
            "elapsed_s": round(time.time() - t0, 1),
        },
        "cells": cells,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n⭐{a.out}  칸 {tot}")
    for k, v in doc["summary"].items():
        print(f"   {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
