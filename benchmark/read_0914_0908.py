#!/usr/bin/env python
"""jobs_0914 를 읽는다 — «정적 몫이 사라지는» 사건을 **레벨 문턱 없이** 센다.

⛔2026-09-10 정정 — 옛 문면 「문턱 없이」는 틀렸다. 쓰는 것은 **상대 편차 문턱**(DEV)이고,
  안 쓰는 것은 **레벨 문턱**(|E| < 자세중앙×0.1)뿐이다. ⛔DEV 는 자유 파라미터다.

■ 왜 별도 판독기인가
  ⛔낙차 개수(|E| < 중앙×0.1)로 세면 **못 본다.** 정적 경로가 여럿인 장면에서는 그중
  하나가 빠져도 합이 **커질** 수 있어 레벨이 안 떨어진다(거리 협곡에서 실제로 그렇다).
  ⇒ 레벨이 아니라 «장면을 더했을 때의 복소 신호 차» D = E_실외 − E_빈하늘 이
    **중앙에서 얼마나 벗어났나** 로 센다. D 는 성한 자세에서 거의 상수라 이 잣대가 선다.

■ 무엇을 답하나 (묶음마다 물음 하나 — ⛔원인을 확정하지 않는다)
    A 기체를 바꾸면 사건 비율이 어떻게 변하나
    B 광선 예산을 1/40·1/4 로 줄이면
    C 반사 깊이 1·3 에서는
    D 동체 크기를 반/두 배로 하면
    E 지면 거칠기를 주면 (⚠경로 상한에 붙는지 먼저 본다)

⛔**손잡이와 원인은 일대일이 아니다**(2026-09-08 설계 검토 ⑯). 이 원장은 «이 손잡이를
  바꿨을 때 사건과 레벨이 어떻게 변했나» 를 **기록**한다. 「기체를 바꿔도 나면 메쉬 탓이
  아니다」 처럼 읽지 않는다.
⚠**대역 고침 뒤에 읽어야 한다** — `comb_snr.f_tip` 이 프롭 지름을 안 써서 기체별 대역이
  틀렸던 것을 2026-09-08 에 고쳤다(mini5pro 920.57 → 512.37 Hz). 이 판독기는 고친 뒤의
  코드를 쓴다. ⛔고치기 전 수와 섞지 마라.

쓰는 법
    cd /workspace/sionna
    CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 PYTHONPATH=src:benchmark nice -n 19 \
      /workspace/.venvs/py312/bin/python benchmark/read_0914_0908.py
    → outputs/read_0914_0908.json   (⭐아직 안 온 칸은 조용히 건너뛴다)
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
OUT = os.path.join(ROOT, "outputs", "read_0914_0908.json")
MESH = "mfixbatteryi5_blperairframe"
ARM = "R0D0E0F1"
EL = -60.0
PRF = 19700.0
CAP = 2_000_000            # 경로 상한 — npaths 가 여기 붙으면 그 칸은 접는다
DEV = 0.5                  # |D − 중앙D| 가 |중앙D| 의 이 배를 넘으면 «정적 몫이 달라진 자세»


def load(name):
    """이름 조각으로 샤드를 모아 idx 로 잇는다. 없으면 None."""
    fs = sorted(glob.glob(f"{SHD}/{name}_el{EL:+g}_*.npz"))
    if not fs:
        return None
    E, I, P = [], [], []
    for f in fs:
        z = np.load(f)
        E.append(z["E"])
        I.append(z["idx"])
        P.append(z["npaths"] if "npaths" in z.files else np.full(z["idx"].shape, -1))
    o = np.argsort(np.concatenate(I))
    return {"E": np.concatenate(E)[o], "npaths": np.concatenate(P)[o], "n_shards": len(fs)}


def stem(spp=4_000_000_000, drone="", env="", depth=2, body=0.0, scat=-1.0):
    """`elevation_sweep_md` 의 이름 규칙을 그대로 따른다(순서가 중요하다)."""
    s = f"sionna_p{spp}_sw{ARM}"
    if drone:
        s += f"_{drone}"
    s += "_r15_n8192"
    if env:
        s += f"_env{env}"
    if scat >= 0:
        s += f"_S{scat:g}"
    if abs(body - 1.0) > 1e-9 and body:
        s += f"_bs{body:g}"
    return s + f"_{MESH}_d{depth}"


def db(x):
    return float(20.0 * np.log10(max(float(x), 1e-300)))


def measure(free, out):
    """한 칸 — 상대 편차 문턱(DEV)을 적용한 사건 셈과 레벨·잣대. ⛔레벨 문턱은 안 쓴다."""
    F, O = free["E"], out["E"]
    if F.size != O.size:
        return None
    D = O - F
    med = complex(np.median(D.real), np.median(D.imag))
    dev = np.abs(D - med) > DEV * abs(med)
    amp = np.abs(O)
    m = float(np.median(amp))
    r = {
        "n_poses": int(O.size), "n_shards": out["n_shards"],
        #: ⭐이것이 이 원장의 머리 수 — 레벨 문턱을 안 쓴다
        "n_static_changed": int(dev.sum()),
        "share_pct": round(100.0 * float(dev.mean()), 2),
        "level_at_events_db": (None if not dev.any()
                               else round(db(np.median(amp[dev])) - db(m), 2)),
        "median_level_db": round(db(m), 2),
        "static_term_db": round(db(abs(med)), 2),
        "lift_over_free_db": round(db(m) - db(np.median(np.abs(F))), 2),
        #: 견주기용 — 옛 낙차 규칙이 몇 개나 보나
        "n_caught_by_dip_rule": int((amp / m < 0.1).sum()),
        #: ⭐칸끼리 견주려고 자세 번호를 들고 나간다(⑬ 에서 쓴다)
        "_flag": dev,
    }
    #: ⛔경로 상한에 붙으면 그 칸은 접는다
    npa = out["npaths"]
    if (npa >= 0).any():
        r["npaths_median"] = int(np.median(npa[npa >= 0]))
        r["at_path_cap"] = bool(np.median(npa[npa >= 0]) >= 0.99 * CAP)
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    t0 = time.time()

    #: (묶음, 이름, 실외 stem, 빈 하늘 stem)
    CELLS = [
        ("기준", "기본 (matrice4e · 4e9 · 깊이 2)",
         stem(env="outdoor01_ground"), stem()),
        ("A 기체", "phantom4",
         stem(drone="phantom4", env="outdoor01_ground"), stem(drone="phantom4")),
        ("A 기체", "mini5pro",
         stem(drone="mini5pro", env="outdoor01_ground"), stem(drone="mini5pro")),
        #: ⛔짝이 어긋난 칸 — 실외는 1e8/1e9 인데 빈 하늘 짝은 4e9 밖에 없다.
        #:   D = E_실외(적은 광선) − E_빈하늘(많은 광선) 이라 두 예산이 섞인다.
        #:   0914 발주서가 이 두 줄의 빈 하늘 짝을 안 시켰다(runners/jobs_0914.txt B 묶음).
        #:   0916 에서 짝을 채운다 — 그 전까지 이 두 칸의 «사건 수»를 인용하지 않는다.
        ("B 광선", "광선 1e8",
         stem(spp=100_000_000, env="outdoor01_ground"), stem(),
         "짝이 어긋난다 — 빈 하늘은 4e9 다. 사건 수를 인용하지 않는다"),
        ("B 광선", "광선 1e9",
         stem(spp=1_000_000_000, env="outdoor01_ground"), stem(),
         "짝이 어긋난다 — 빈 하늘은 4e9 다. 사건 수를 인용하지 않는다"),
        ("C 깊이", "깊이 1",
         stem(env="outdoor01_ground", depth=1), stem(depth=1)),
        ("C 깊이", "깊이 3",
         stem(env="outdoor01_ground", depth=3), stem(depth=3)),
        ("D 크기", "동체 ×0.5",
         stem(env="outdoor01_ground", body=0.5), stem(body=0.5)),
        ("D 크기", "동체 ×2",
         stem(env="outdoor01_ground", body=2.0), stem(body=2.0)),
        ("E 거칠기", "거칠기 0.3",
         stem(env="outdoor01_ground", scat=0.3), stem()),
    ]
    cells, missing, flags = {}, [], {}
    CELLS = [(c + ("",))[:5] if len(c) == 4 else c for c in CELLS]
    for grp, lbl, so, sf, warn in CELLS:
        O, F = load(so), load(sf)
        if O is None or F is None:
            missing.append({"group": grp, "cell": lbl,
                            "have_outdoor": O is not None, "have_free": F is not None})
            continue
        r = measure(F, O)
        if r is None:
            missing.append({"group": grp, "cell": lbl, "why": "자세 수가 안 맞는다"})
            continue
        flags[f"{grp}/{lbl}"] = r.pop("_flag")
        r.update(group=grp, cell=lbl, stem_outdoor=so, stem_free=sf)
        if warn:
            r["warn_ko"] = warn
        cells[f"{grp}/{lbl}"] = r
        cap = " ⛔상한" if r.get("at_path_cap") else ""
        cap += "  ⛔" + warn if warn else ""
        print(f"  {grp:<8}{lbl:<26} 사건 {r['n_static_changed']:>4}"
              f" ({r['share_pct']:>5.2f} %) · 그때 {str(r['level_at_events_db']):>7} dB"
              f" · 지면이 올린 몫 {r['lift_over_free_db']:>6.1f} dB"
              f" · 옛 규칙 {r['n_caught_by_dip_rule']:>4}{cap}", flush=True)
    for m in missing:
        print(f"  ⏳{m['group']:<8}{m['cell']:<26} 아직 없다"
              f" (실외 {m.get('have_outdoor')} · 빈 하늘 {m.get('have_free')})", flush=True)

    #: ⑬ 손잡이를 돌리면 «걸리는 자세» 가 옮겨 가나, 그대로인다
    #:    ⭐우연히 겹칠 기댓값 = n_a·n_b / N — 관측이 그 언저리면 «상관 없다» 는 뜻이다.
    #:    ⛔겹침이 크다고 원인이 같다는 뜻은 아니다(설계 검토 ⑯).
    #:    ⛔⛔**자세 i 는 «시각» t=i/PRF 이지 로터 각이 아니다**
    #:      (elevation_sweep_md.py:363 「--n-poses 는 촘촘함이 아니라 기록 길이다」).
    #:      기체마다 호버 회전수가 다르면 같은 i 가 **다른 로터 각**이라 자세를 견줄 수 없다.
    #:      matrice4e 3800 rpm · phantom4 5500 · mini5pro 5500 —
    #:      ⭐phantom4↔mini5pro 만 회전수가 같아 «같은 각, 다른 기체» 로 깨끗하게 견준다.
    #:      matrice4e 가 낀 줄은 not_comparable 로 표시하고 인용하지 않는다.
    def _rpm_of(st: str) -> float:
        for k, v in (("_phantom4", 5500.0), ("_mini5pro", 5500.0)):
            if k in st:
                return v
        return 3800.0                                    #: matrice4e (원장 기본)
    cross, ks = {}, [k for k in cells if not cells[k].get("warn_ko")]
    for i, ka in enumerate(ks):
        for kb in ks[i + 1:]:
            fa, fb = flags[ka], flags[kb]
            if fa.size != fb.size:
                continue
            na, nb, N = int(fa.sum()), int(fb.sum()), int(fa.size)
            inter = int((fa & fb).sum())
            uni = int((fa | fb).sum())
            ra = _rpm_of(cells[ka]["stem_outdoor"])
            rb = _rpm_of(cells[kb]["stem_outdoor"])
            cross[f"{ka} ∩ {kb}"] = {
                "n_a": na, "n_b": nb, "n_intersect": inter,
                "jaccard": round(inter / max(uni, 1), 4),
                "expected_if_unrelated": round(na * nb / N, 2),
                "share_of_smaller": round(inter / max(min(na, nb), 1), 4),
                "rpm_a": ra, "rpm_b": rb,
                "comparable": ra == rb,
                **({} if ra == rb else {"why_not_ko":
                   f"호버 회전수가 다르다({ra:.0f} 대 {rb:.0f} rpm) — "
                   "같은 자세 번호가 다른 로터 각이라 자세를 견줄 수 없다"})}
    print("\n  ⑬ 칸끼리 같은 자세가 걸리나 (우연 기댓값과 견준다)")
    for k, v in cross.items():
        bad = "" if v["comparable"] else "  ⛔회전수가 달라 못 견준다"
        print(f"    {'⭐' if v['comparable'] else '  '}{k:<56} 교집합 {v['n_intersect']:>3}"
              f" / 작은쪽 {min(v['n_a'], v['n_b']):>3}"
              f" · 우연이면 {v['expected_if_unrelated']:>5.2f}"
              f" · 자카드 {v['jaccard']:.3f}{bad}", flush=True)

    doc = {
        "_meta": {
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generator": "benchmark/read_0914_0908.py",
            "question_ko": "jobs_0914 의 손잡이를 바꾸면 «정적 몫이 사라지는» 사건이 어떻게 변하나",
            "metric_ko": f"레벨 문턱을 안 쓴다 — D = E_실외 − E_빈하늘 이 중앙에서 "
                         f"|중앙D|×{DEV} 넘게 벗어난 자세를 센다",
            "why_not_dip_rule_ko": "낙차 규칙(|E| < 중앙×0.1)은 정적 경로가 여럿인 장면에서 "
                                   "합이 커지는 경우를 원리적으로 못 본다",
            "band_fix_ko": "⚠comb_snr.f_tip 이 프롭 지름을 안 써서 기체별 대역이 틀렸던 것을 "
                           "2026-09-08 에 고쳤다(mini5pro 920.57 → 512.37 Hz). "
                           "이 판독기는 고친 뒤 코드를 쓴다 — 고치기 전 수와 섞지 마라",
            "el_deg": EL, "arm": ARM, "path_cap": CAP,
            "elapsed_s": round(time.time() - t0, 1),
            "limits_ko": [
                "⛔손잡이와 원인은 일대일이 아니다 — 이 원장은 변화를 기록할 뿐 원인을 "
                "확정하지 않는다(설계 검토 ⑯).",
                "⛔경로 상한(at_path_cap)이 참인 칸은 접는다.",
                "⚠빈 하늘 짝의 세대가 다르면 D 가 오염된다 — stem 을 함께 적어 뒀다.",
                "⛔이 저장소에 실기 계측 대조는 0 건이다.",
            ],
        },
        "summary": {
            "n_cells_read": len(cells), "n_cells_missing": len(missing),
            "share_pct_by_cell": {k: v["share_pct"] for k, v in cells.items()},
            "level_at_events_db_by_cell": {k: v["level_at_events_db"]
                                           for k, v in cells.items()},
            "cells_with_mismatched_pair": [k for k, v in cells.items()
                                           if v.get("warn_ko")],
            "cells_at_path_cap": [k for k, v in cells.items() if v.get("at_path_cap")],
            "missing": missing,
        },
        "cross_cell_overlap": cross,
        "cells": cells,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"\n⭐{a.out}  읽은 칸 {len(cells)} · 아직 없는 칸 {len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
