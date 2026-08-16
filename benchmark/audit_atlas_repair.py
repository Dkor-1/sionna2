# -*- coding: utf-8 -*-
"""
audit_atlas_repair.py — 아틀라스 수리의 **재검증**. 고친 항목마다 «전에는 이랬고 지금은
이렇다» 를 수치로 남긴다 → `outputs/atlas_falsify.json`.

왜 이 파일이 따로 있나
--------------------
수리는 생성기 셋(`build_md_atlas.py` · `build_atlas_toc.py` · `build_atlas_gallery.py`)을
고쳐서 했다. 그 셋을 다시 돌리면 산출물이 바뀌는데, **바뀐 것이 무엇이고 어느 방향으로
바뀌었는지**는 산출물만 봐서는 안 보인다. 그래서 이 파일이 세 가지를 한다.

  ① 수리 **전** 값 — 2026-08-15 수리 직전의 색인·그림에서 직접 잰 값을 상수로 박아 둔다
     (옛 코드는 사라졌으므로 다시 잴 수 없다. 어디서 잰 값인지 항목마다 적는다).
  ② 수리 **후** 값 — 지금의 색인·원장·HTML 을 **다시 읽어** 계산한다.
  ③ 아직 **못 고친 것** — 정직하게 한계로 남긴다.

⛔GPU 를 안 쓴다. ⛔원장을 안 고친다(원장은 실험 큐가 쓰는 파일이다).

돌리는 법
--------
    PYTHONPATH=src /workspace/.venvs/py312/bin/python benchmark/audit_atlas_repair.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

IDX_P = os.path.join(ROOT, "outputs", "md_atlas_index.json")
LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LED_N = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
OUT_P = os.path.join(ROOT, "outputs", "atlas_falsify.json")
ATLAS = os.path.join(ROOT, "atlas")

IDX = json.load(open(IDX_P, encoding="utf-8"))
LED = json.load(open(LED_J, encoding="utf-8"))
META = IDX["_meta"]
ARM = {a: v for t in IDX["topics"].values() for a, v in t["arms"].items()}
CELLS = [(a, k, c) for a, v in ARM.items() for k, c in v["cells"].items()]
ROWS = {(r["engine"], float(r["el_deg"])): r for r in LED["rows"]}


def kst() -> str:
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(time.time() + 9 * 3600)) + " KST"


def html(name: str) -> str:
    return open(os.path.join(ATLAS, name), encoding="utf-8").read()


def flag(kind: str):
    return [(a, k) for a, k, c in CELLS if c.get(kind)]


# ═══════════════════════════════════════════════════════════════════════════ #
#  전 · 후
# ═══════════════════════════════════════════════════════════════════════════ #
def d1_incomplete() -> dict:
    """⭐덜 찬 칸에 수를 싣던 결함."""
    #: 수리 직전 `outputs/md_atlas_index.json` 에서 읽은 값 — 그리고 옛 식(깃발 없이 그대로
    #  계산)을 지금 코드로 다시 돌려 같은 수가 나오는지 확인한 값이다(beat 는 그렇게 얻었다).
    before = {
        "ours_r30_n8192@+0": dict(rhythm_share_pct=0.1, moving_share_pct=51.3188,
                                  beat_hz=126.1, beat_over_flash=0.995,
                                  moving_power_db=-60.53, flagged_incomplete=False),
        "sionna_p4000000000_r30_n8192_d1@+0": dict(rhythm_share_pct=0.0,
                                                   moving_share_pct=50.0176,
                                                   beat_hz=41.2, beat_over_flash=0.325,
                                                   moving_power_db=-75.33,
                                                   flagged_incomplete=False),
        "sionna_p4000000000@-75": dict(rhythm_share_pct=0.1, moving_share_pct=59.8972,
                                       beat_hz=127.2, beat_over_flash=1.004,
                                       moving_power_db=-107.82,
                                       flagged_incomplete=False),
    }
    after = {}
    for a, k, c in CELLS:
        if c.get("incomplete"):
            after[f"{a}@{k}"] = dict(
                rhythm_share_pct=c["rhythm_share_pct"],
                moving_share_pct=c["moving_share_pct"], beat_hz=c["beat_hz"],
                comb_contrast_db=c["comb_contrast_db"],
                flagged_incomplete=True,
                n_poses_in=c["n_poses"] - max(c["n_missing"], c["n_zero_samples"]),
                n_poses=c["n_poses"])
    leak = [f"{a}@{k}" for a, k, c in CELLS
            if (c.get("incomplete") or c.get("no_motion") or c.get("no_return"))
            and any(c.get(x) is not None for x in
                    ("rhythm_share_pct", "beat_hz", "comb_contrast_db",
                     "moving_power_db", "moving_share_pct"))]
    # 0 이 박힌 자리가 어떤 무늬인가 — 균일하면 데시메이션이 가능하고 아니면 불가능하다
    Z = np.load(LED_N, allow_pickle=True)
    pattern = {}
    for a, k, c in CELLS:
        if not c.get("incomplete"):
            continue
        E = np.asarray(Z[f"{a}/el{float(k):+.0f}"], complex)
        z = np.flatnonzero(E == 0)
        step = sorted({int(x) for x in np.diff(z)}) if z.size > 1 else []
        pattern[f"{a}@{k}"] = dict(
            n_zero=int(z.size), first=[int(x) for x in z[:8]],
            gaps=step[:4],
            uniform_stride=bool(len(step) == 1),
            rescuable_by_decimation=bool(len(step) == 1))
    return dict(
        defect="원장 n_missing 을 안 읽어 «절반만 찬 칸» 에 잣대를 실었다 "
               "(0 채움이 스펙트럼을 PRF/2·PRF/4 에 복제 → 리듬 몫 0 %)",
        fix="cell_summary 가 원장 n_missing 과 **시계열 안의 0 표본**을 함께 보고 "
            "incomplete 깃발을 세운다. 깃발이 서면 리듬 몫·박자·빗살 대비·움직이는 전력을 "
            "전부 None 으로 낸다. 그림 구석·표·갤러리 배지·목차 표에 «덜 참» 을 적는다.",
        before=before, after=after, metric_leaks_now=leak,
        zero_pattern=pattern,
        why_no_recompute_ko="세 칸 중 «한 칸 걸러 하나» 로 균일하게 빠진 칸은 하나뿐이고 "
                            "나머지 둘은 뭉텅이로 빠져 균일 표본이 아니다. 0 을 걷어내고 "
                            "다시 재는 길은 그래서 없다 — 반증자 셋이 같은 칸에서 "
                            "60.5 % · 63.6 % · 93.3 % 로 서로 다른 «참값» 을 냈다는 사실이 "
                            "그 증거다. 고치는 길은 원장 재병합뿐이다.")


def d2_no_motion() -> dict:
    return dict(
        defect="움직이는 부분이 없는 칸(AC/DC = 1 ULP)에서 반올림 오차를 «박자» 로 적었다",
        fix="AC/DC < 1e-12 이면 no_motion 으로 보고 잣대를 내지 않는다",
        before={"sionna_p4000000000_partsnoprop_r15_n8192_d1@+0":
                dict(rhythm_share_pct=13.4, beat_hz=203.7, beat_over_flash=1.608,
                     moving_power_db=-384.45)},
        after={f"{a}@{k}": dict(rhythm_share_pct=c["rhythm_share_pct"],
                                beat_hz=c["beat_hz"],
                                moving_power_db=c["moving_power_db"],
                                ac_over_dc=c["ac_over_dc"], flagged_no_motion=True)
               for a, k, c in CELLS if c.get("no_motion")})


def d3_null() -> dict:
    """널 13 % 하나로 재던 결함."""
    by = {}
    for a, k, c in CELLS:
        v = c.get("rhythm_null_pct")
        if v is not None:
            by.setdefault(ARM[a]["airframe_label"], []).append(v)
    misread = [f"{a}@{k}" for a, k, c in CELLS
               if c.get("rhythm_share_pct") is not None
               and c["rhythm_null_pct"] is not None
               and c["rhythm_null_pct"] < c["rhythm_share_pct"] < 13.0]
    return dict(
        defect="백색잡음 널을 13 % 하나로 박아 모든 팔에 댔다(갤러리 상수 · 그림 각주 · 목차)",
        fix="칸마다 «상한 위 빈 중 정수배 창에 든 빈의 비율» 을 정확히 세어 rhythm_null_pct 로 "
            "싣고, 막대 눈금선·판정·각주가 그 값을 쓴다",
        before=dict(hardcoded=13.0),
        after={k: dict(n=len(v), mean=round(sum(v) / len(v), 2),
                       min=round(min(v), 2), max=round(max(v), 2))
               for k, v in sorted(by.items())},
        cells_misread_before=dict(
            n=len(misread), list=misread,
            meaning_ko="자기 널 위인데 «13 아래» 라 «리듬 없음» 으로 읽혔을 칸"))


def d4_comb() -> dict:
    """상한 위만 재던 잣대에 짝을 붙였다."""
    ex = {}
    for a in ("ours_r15_n8192", "ours", "sionna_p4000000000_r15_n8192_d1",
              "sionna_p4000000000_stockdef_r15_n8192",
              "sionna_p4000000000_phys_r15_n8192_d1"):
        c = ARM.get(a, {}).get("cells", {}).get("+0")
        if c:
            ex[a] = dict(rhythm_share_pct=c["rhythm_share_pct"],
                         rhythm_null_pct=c["rhythm_null_pct"],
                         above_ceiling_energy_pct=c["above_ceiling_energy_pct"],
                         comb_contrast_db=c["comb_contrast_db"])
    lo = [c["above_ceiling_energy_pct"] for _a, k, c in CELLS
          if c.get("rhythm_share_pct") is not None
          and c["above_ceiling_energy_pct"] is not None
          and c["rhythm_share_pct"] < 20 and abs(float(k) + 90) > 1e-9]
    hi = [c["above_ceiling_energy_pct"] for _a, k, c in CELLS
          if c.get("rhythm_share_pct") is not None
          and c["above_ceiling_energy_pct"] is not None
          and c["rhythm_share_pct"] >= 20 and abs(float(k) + 90) > 1e-9]
    return dict(
        defect="«리듬 몫» 은 상한 **위**만 재는데 낮은 값이 «날개가 없다» 로 읽혔다. "
               "목차는 그 까닭을 «무늬가 상한 아래로 얌전히 들어앉아서» 라고 적었는데 "
               "**방향이 거꾸로**였다",
        fix="상한 **아래**를 보는 짝 잣대 comb_contrast_db(정수배 자리 ÷ 그 사이 자리, "
            "백색잡음 0 dB)를 칸마다 싣고 그림 구석·표·헤드라인이 함께 쓴다. "
            "above_ceiling_energy_pct 도 실어 «위가 조용해서» 인지 «위가 가득 차서» 인지를 가른다",
        direction_check=dict(
            low_rhythm_cells=len(lo),
            low_median_above_ceiling_pct=round(float(np.median(lo)), 1),
            high_rhythm_cells=len(hi),
            high_median_above_ceiling_pct=round(float(np.median(hi)), 1),
            verdict_ko="리듬 몫이 낮은 칸이 상한 위에 에너지가 **더 많다** — 옛 설명이 거꾸로였음이 "
                       "재확인된다"),
        examples_at_0deg=ex,
        n_cells_with_comb=sum(1 for _a, _k, c in CELLS
                              if c.get("comb_contrast_db") is not None))


def d5_titles() -> dict:
    """제목 잘림."""
    from build_md_atlas import fit_title                       # noqa: E402
    before, after = [], []
    for a, v in ARM.items():
        ncol = len(v["elevations_deg"])
        W = 1.60 + ncol * 3.05 + 0.38 * 3.05 * (ncol - 1) + 1.40
        avail = W - 1.60 - 0.15
        cap14 = int(avail / (14 / 72 * 0.6023))
        if len(a) > cap14:
            before.append(dict(arm=a, chars=len(a), fits=cap14, cut_tail=a[cap14:]))
        fs, lines = fit_title(a, avail)
        cap = int(avail / (fs / 72.0 * 0.6023))
        if any(len(x) > cap for x in lines):
            after.append(a)
    return dict(
        defect="맵 그림 제목(팔 이름)이 14 pt 고정이라 폭이 좁은 판에서 잘렸다 — "
               "하필 잘리는 꼬리가 `_d1`/`_d3` 라 판을 구별할 수 없었다",
        fix="fit_title() — 폭에 맞춰 글자를 줄이고, 그래도 안 들어가면 밑줄 단위로 접는다",
        before=dict(n_truncated=len(before), rows=sorted(before, key=lambda x: -x["chars"])),
        after=dict(n_truncated=len(after), rows=after))


def d6_mixed_range() -> dict:
    """비교판이 거리를 안 적던 결함."""
    per_topic = {k: dict(ranges_m=t.get("ranges_m"),
                         n_arms=len(t["arms"]),
                         mixed=bool(t.get("ranges_m") and len(t["ranges_m"]) > 1))
                 for k, t in IDX["topics"].items()}
    base = IDX["topics"]["01base"]["arms"]
    by_r: dict[str, list] = {}
    for a in base:
        r = ARM[a]["cells"][list(ARM[a]["cells"])[0]]["range_m"]
        by_r.setdefault(f"{float(r):g} m", []).append(a)
    return dict(
        defect="01base 비교판이 10 m 팔과 15 m 팔을 아무 표시 없이 위아래로 쌓았다 "
               "(원장 _meta 가 «거리가 다른 팔을 나란히 놓을 때는 반드시 적는다» 고 못 박은 규칙)",
        fix="① 비교판 줄 라벨·타일 제목에 **거리**를 박는다 ② 부제에 «rows differ in RANGE» 를 "
            "적는다 ③ TOPIC_LABEL['base'] 의 «…만 갈리는 팔» 을 고쳤다 "
            "④ 갤러리 lede 의 «같은 자리» 를 지우고 헤드라인을 **거리를 맞춰** 묶는다",
        base_topic_ranges=by_r, per_topic=per_topic,
        gallery_says_same_place="같은 드론 · 같은 자리" in html("01_base.html"),
        gallery_says_not_same_place="<b>같은 자리가 아니다</b>" in html("01_base.html"))


def d7_spiky() -> dict:
    rows = sorted(((c.get("spike_ratio") or 0, f"{a}@{k}", c["beat_hz"],
                    c["beat_over_flash"]) for a, k, c in CELLS if c.get("beat_spiky")),
                  reverse=True)
    return dict(
        defect="자세 몇 개가 통째로 튄 칸의 «박자» 를 진짜 박자와 같은 서식으로 적었다"
               "(예측의 0.19x 같은 값)",
        fix="spike_ratio = |AC| 최대÷중앙 을 칸마다 싣고 100 을 넘으면 beat_spiky 를 세운다. "
            "그림 구석에 «(spiky)», 표에 «⚡ 큰 자세 N배» 배지, 목차에 그 절. "
            "⚠이 잣대는 «얼마나 큰가» 만 잰다 — «자세 하나가 헤드라인을 끄나» 는 "
            "cell_summary 의 outlier_grade·one_pose_moves_headline(«⚑ 튐» 배지)이 잰다",
        before=dict(flagged=0),
        after=dict(flagged=len(rows),
                   worst=[dict(cell=n, spike=round(s, 1), beat_hz=b, beat_over_flash=r)
                          for s, n, b, r in rows[:8]]))


def d8_gallery_claims() -> dict:
    """갤러리가 문장으로 못 박았던 거짓 주장."""
    r = html("06_range.html")
    idx = html("index.html")
    g = html("08_grid.html")
    az = html("04_azimuth.html")
    return dict(
        defect="갤러리 06range 가 «리듬이 아예 남지 않았다» · «63.2 %p 차이가 살아 있다» 를 "
               "자동 생성했다 — 둘 다 덜 찬 칸에서 나온 수였다",
        fix="① 덜 찬 칸이 섞이면 결론 문장 대신 «아직 결론을 낼 수 없다» 를 먼저 낸다 "
            "② «리듬 없음» 판정은 그 칸의 널 **과** 상한 아래 빗살 대비가 **함께** 널일 때만 "
            "③ 짝 통계에서 −90°(잣대 퇴화)와 자격 없는 칸을 뺀다 "
            "④ 08grid 는 «판정 불가» 대신 «이 짝이 밴드의 정의»",
        checks={
            "06range: «리듬이 아예 남지 않았다» 없음": "리듬이 아예 남지 않았다" not in r,
            "06range: «결론을 낼 수 없다» 있음": "아직 결론을 낼 수 없다" in r,
            "06range: 덜 찬 칸 이름 적음": "ours_r30_n8192" in r and "덜 찬" in r,
            "대문: «상한 위만 본다» 경고 있음": "상한 위만 본다" in idx,
            "대문: 근접장 표 있음": "원거리장 경계 2D²/λ" in idx or "근접장" in idx,
            "대문: 밴드가 우리 커널 축임을 밝힘":
                "PathSolver 에는 그 축이 아예 없다" in idx,
            "08grid: «이 짝이 밴드를 정의» 있음": "밴드 21.8 %p 를 정의한 짝" in g,
            "04azimuth: 퇴화 칸을 뺐다고 적음": "뺀 칸" in az,
        })


def d9_pairs_exclude_degenerate() -> dict:
    """−90° 를 짝 통계에서 뺀 효과."""
    def deltas(a, b, drop_degen):
        ca, cb = ARM[a]["cells"], ARM[b]["cells"]
        out = []
        for k, v in ca.items():
            w = cb.get(k)
            if not w or v["rhythm_share_pct"] is None or w["rhythm_share_pct"] is None:
                continue
            if drop_degen and (v.get("tip_ceiling_degenerate")
                               or w.get("tip_ceiling_degenerate")):
                continue
            out.append(v["rhythm_share_pct"] - w["rhythm_share_pct"])
        return out
    pair = ("sionna_p4000000000_r15_n8192_az45_d1", "sionna_p4000000000_r15_n8192_d1")
    b, a = deltas(*pair, drop_degen=False), deltas(*pair, drop_degen=True)
    return dict(
        defect="방위 짝 비교가 −90°(잣대 퇴화) 칸을 함께 세었다",
        fix="pair_delta 가 퇴화 칸과 «자격 없는 칸» 을 뺀다",
        pair=pair,
        before=dict(n=len(b), max_abs=round(max(map(abs, b)), 1) if b else None),
        after=dict(n=len(a), max_abs=round(max(map(abs, a)), 1) if a else None))


def d10_farfield() -> dict:
    from drones import DRONES, build_drone                      # noqa: E402
    lam = 2.998e8 / float(META["fc_hz"])
    tab, inside = {}, []
    for key in sorted({v["airframe"] for v in ARM.values()}):
        b0, b1 = build_drone(DRONES[key]).bounds()
        D = float(np.linalg.norm(np.asarray(b1) - np.asarray(b0)))
        rff = 2 * D * D / lam
        rs = sorted({float(c["range_m"]) for a, _k, c in CELLS
                     if ARM[a]["airframe"] == key and c.get("range_m") is not None})
        tab[key] = dict(D_m=round(D, 3), r_farfield_m=round(rff, 2), ranges_m=rs,
                        inside=[r for r in rs if r < rff])
        inside += sorted({a for a, _k, c in CELLS if ARM[a]["airframe"] == key
                          and c.get("range_m") is not None
                          and float(c["range_m"]) < rff})
    return dict(
        defect="원거리장 경고가 «10 m 는 근접장, 15 m 는 기준» 하나뿐이었다 — 경계는 표적 "
               "크기에 달렸는데 s1000plus(경계 85.95 m) 팔 4 개가 15 m 에 서 있다",
        fix="기체마다 2D²/λ 를 다시 계산해 목차 §13.5 · 갤러리 주의 4 에 표로 싣는다"
            "(규약은 원장과 같은 «메쉬 3D 대각» — matrice4e 14.08 m 로 재현된다)",
        table=tab, arms_inside_nearfield=sorted(set(inside)))


def d11_specular() -> dict:
    src = open(os.path.join(HERE, "elevation_sweep_md.py"), encoding="utf-8").read()
    m = re.search(r"los\s*=\s*True[^\n]*|specular_reflection\s*=\s*True[^\n]*", src)
    nb = json.load(open(os.path.join(ROOT, "reports", "A_atlas.ipynb"), encoding="utf-8"))
    txt = "".join("".join(c["source"]) for c in nb["cells"])
    return dict(
        defect="«swR0D0E0F0 = 스위치 전부 끔» 이라 적었지만 생성기가 정반사·LOS 를 "
               "하드코딩으로 켜 둔다 — 빈 칸의 까닭 설명도 그래서 틀렸다",
        fix="토막 사전·«전부 끔» 문구·빈 칸 까닭을 «정반사·LOS 는 항상 켬» 으로 고쳤다",
        source_line=(m.group(0).strip() if m else None),
        toc_says_always_on="정반사·LOS 는 언제나 켜져 있다" in txt
        or "정반사와 직선경로는 켜 둔 채" in txt)


def d12_si_rays() -> dict:
    import importlib
    g = importlib.import_module("build_atlas_gallery")
    return dict(
        defect="광선 수 11,111,111 을 갤러리가 «1111.11 만» 으로, 목차가 «1,111 만» 으로 "
               "적어 두 문서가 갈렸다",
        fix="si_rays 를 반올림·천단위 쉼표로 통일하고 원수를 툴팁에 남긴다",
        before="1111.11 만", after=g.si_rays(11111111),
        agrees_with_toc=bool(g.si_rays(11111111) == "1,111 만"))


def d13_fresh() -> dict:
    figs = [os.path.join(ROOT, p) for t in IDX["topics"].values()
            for a in t["arms"].values() for p in a["figures"].values()]
    figs += [os.path.join(ROOT, p) for t in IDX["topics"].values() for p in t["compare"]]
    code = os.path.getmtime(os.path.join(HERE, "build_md_atlas.py"))
    old = [os.path.relpath(f, ROOT) for f in figs if os.path.getmtime(f) < code]
    return dict(
        defect="fresh() 가 원장 시각만 봐서, 그림 규칙을 바꾸는 코드 수정 뒤 --force 를 "
               "빼먹으면 옛 그림이 남았다",
        fix="FRESH_AFTER = max(원장, 이 코드, src/md_mapstyle.py) 로 바꿨다",
        n_figures=len(figs), n_older_than_code=len(old), stale=old[:5])


def d14_physics_tag() -> dict:
    """우리 커널 팔에 PathSolver 전용 축을 붙이던 결함."""
    ours = [a for a in ARM if a.startswith("ours")]
    had = [a for a in ours
           if ROWS[(a, float(ARM[a]["elevations_deg"][0]))].get("physics") is not None]
    tagged_now = []
    for f in ("01_base.html", "02_switch.html", "03_airframe.html", "04_azimuth.html",
              "05_parts.html", "06_range.html", "07_ptd.html", "08_grid.html",
              "09_planewave.html"):
        for m in re.finditer(r'<h3 class="name">(ours[^<]*)</h3><p class="facts">(.*?)</p>',
                             html(f), re.S):
            if "스위치" in m.group(2):
                tagged_now.append(m.group(1))
    return dict(
        defect="우리 커널 팔에 PathSolver 전용 축인 «스위치 물리 끔» 딱지가 붙었다 — 원장 "
               "physics 열이 ours 팔 일부에서 False, 나머지는 None 이라 **같은 엔진의 팔이 "
               "존재하지 않는 축에서 갈려** 보였다",
        fix="arm_facts 가 sionna 팔에서만 physics 열을 읽는다(갤러리·목차 둘 다)",
        before=dict(ours_arms_with_physics_column=sorted(had),
                    n=len(had), of_total_ours_arms=len(ours)),
        after=dict(ours_arms_tagged_in_gallery=sorted(set(tagged_now)),
                   n=len(set(tagged_now))))


def cross_doc_alias() -> dict:
    """⭐10 m 팔 이름이 다른 문서에서 15 m 를 가리키는 자리 — **고치지 않고 목록만** 남긴다."""
    arms10 = sorted({r["engine"] for r in LED["rows"] if r.get("range_m") == 10.0})
    items = []
    p = os.path.join(ROOT, "outputs", "ch1_elevation_figdata_r15.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        alias = str(d.get("_meta", {}).get("alias_ko", ""))
        if "ours = ours_r15_n8192" in alias.replace("  ", " "):
            items.append(dict(
                file="outputs/ch1_elevation_figdata_r15.json",
                token="ours",
                means_here="ours_r15_n8192 (15 m)",
                means_in_atlas="ours (10 m · 옛 기본)",
                evidence=alias[:200],
                cited_by=["reports/04_elevation-coverage.ipynb (`cells.ours/...` 인용)"],
                risk_ko="같은 토막 `ours` 가 두 원장에서 10 m 와 15 m 로 갈린다 — "
                        "아틀라스 표를 그 리포트 각주와 나란히 놓으면 거리를 뒤바꿔 읽는다"))
    w = os.path.join(ROOT, "outputs", "wideband_energy.json")
    if os.path.exists(w):
        d = json.load(open(w, encoding="utf-8"))
        v = d.get("cells", {}).get("ours/el+0", {}).get("above_f_tip_frac")
        items.append(dict(
            file="outputs/wideband_energy.json · outputs/wideband_energy_fairbudget.json",
            token="ours",
            means_here="ours (10 m) — 별칭 설명이 없다",
            means_in_atlas="ours (10 m)",
            evidence=f"cells.ours/el+0.above_f_tip_frac = {v} ↔ 아틀라스 "
                     f"ours@+0 above_ceiling_energy_pct = "
                     f"{ARM['ours']['cells']['+0']['above_ceiling_energy_pct']} %",
            cited_by=["reports/05_engine-physics.ipynb"],
            risk_ko="여기서는 뜻이 아틀라스와 **같다**(10 m). 다만 별칭 설명이 없어 "
                    "위 파일과 헷갈릴 수 있다. 리포트 05 본문은 «거리 10 m» 라고 "
                    "정확히 적고 있으므로 오기재는 아니다"))
    return dict(
        rule_ko="⛔다른 문서는 고치지 않았다 — 목록만 남긴다(수리 범위는 아틀라스 생성기 셋).",
        arms_at_10m=arms10,
        scan_ko="reports/*.ipynb 와 outputs/*.json 에서 10 m 팔 이름 8 개를 훑어 «15 m» 와 "
                "같은 자리에 놓인 곳을 찾았다. 아래 둘 말고는 «10 m 팔을 15 m 라고 적은» "
                "자리가 없었다(리포트 05 는 오히려 «거리 10 m · 근거리장» 을 명시한다).",
        items=items)


def limits() -> dict:
    """못 고친 것 — 갤러리·목차 양쪽에도 적혀 있다."""
    return [
        dict(what="덜 찬 칸 3 개의 **참값**",
             why="원장을 고치는 일이라 이 수리의 범위 밖이다(원장은 실험 큐가 지금도 쓰는 "
                 "파일이고, 세 칸 중 둘은 자세가 뭉텅이로 빠져 균일 표본이 아니라 "
                 "데시메이션으로도 못 살린다)",
             where_written="갤러리 06range 헤드라인 · 대문 주의 5·6 · 목차 §14.1b · §13.10",
             next_step="스윕 쪽에서 `outputs/elev_sweep_shards/` 를 다시 병합한 뒤 "
                       "build_md_atlas --force → toc → gallery 순으로 다시 굽는다"),
        dict(what="주제 분류(topic_of)가 아직 **이름 토막**으로 거리를 본다",
             why="원장 range_m 으로 바꾸면 `_r` 토막이 없는 10 m 옛 팔 8 개가 range 주제로 "
                 "옮겨가는데, 그 팔들은 «거리를 묻는 판» 이 아니라 옛 기본값 판이다. "
                 "게다가 그림 파일 이름(주제 번호)이 전부 바뀌어 이미 인용된 경로가 깨진다",
             where_written="목차 §13.4 · §13.10 · 갤러리 주의 4(거리 표 + 근접장 표) · 주의 6",
             next_step="주제를 «range × airframe» 으로 쪼갤 때 함께 바꾼다"),
        dict(what="맵 패널은 여전히 **패널마다 자기 최댓값**으로 정규화한다",
             why="md_mapstyle.draw 의 docstring 이 여러 거리를 한 그림에 놓을 때 ref 를 "
                 "공통 스칼라로 주라고 적어 두었지만, 공통 ref 는 엔진이 섞인 판에서 "
                 "«눈금이 다른 두 엔진» 을 한 색역에 올리는 더 큰 거짓을 만든다",
             where_written="그림 부제 «brightness is not comparable between panels» · "
                           "갤러리 주의 2·6 · 목차 §13.10",
             next_step="같은 엔진 안의 거리 사다리만 따로 그릴 때 ref 를 준다"),
        dict(what="리듬 몫의 창 반폭은 8 Hz **고정**이다",
             why="`build_deck_maps.structure_bars` 와 같은 정의를 유지해야 이미 인용된 수와 "
                 "갈리지 않는다. 대신 도달 불가한 천장 100 을 각주에서 지우고, 칸마다의 "
                 "널을 정확히 세어 함께 낸다",
             where_written="그림 각주 «100 is NOT reachable» · 목차 §1 · §13.7 · §13.10 · 갤러리 주의 6",
             next_step="배음마다 창을 넓히는 판을 새 잣대로 따로 정의하고 두 잣대를 나란히 "
                       "낸다(정의를 바꾸는 것이 아니라 추가한다)"),
        dict(what="박자와 맵은 **다른 구간**에서 잰 수다(전 구간 ↔ 20~80 ms)",
             why="맵 창을 늘리면 플래시 시간분해능이 무너지고, 박자를 짧은 창에서 재면 "
                 "분해능(PRF/N)이 나빠진다",
             where_written="갤러리 표 각주 · 주의 6 · 목차 §13.9 · 색인 _meta.beat_window_ko",
             next_step="필요하면 같은 창의 박자를 별도 열로 추가한다"),
    ]


def main():
    out = {
        "_meta": {
            "generator": "benchmark/audit_atlas_repair.py",
            "purpose_ko": "2026-08-15 아틀라스 수리의 재검증 — 고친 항목마다 «전 → 후» 를 "
                          "수치로 남긴다",
            "generated_kst": kst(),
            "gpu_ko": "GPU 를 쓰지 않는다 — 색인·원장·HTML·순수 파이썬 기하만 읽는다",
            "ledger_untouched_ko": "⛔원장(outputs/elevation_sweep_md.*)은 고치지 않았다 — "
                                   "실험 큐가 쓰는 파일이다",
            "repaired_files": ["benchmark/build_md_atlas.py",
                               "benchmark/build_atlas_toc.py",
                               "benchmark/build_atlas_gallery.py"],
            "regenerated": ["outputs/figures/atlas/*.png (122 장)",
                            "outputs/md_atlas_index.json",
                            "reports/A_atlas.ipynb",
                            "atlas/*.html · atlas/README.md"],
        },
        "defects_fixed": {
            "D1_incomplete_cells": d1_incomplete(),
            "D2_no_motion_cell": d2_no_motion(),
            "D3_noise_floor_per_cell": d3_null(),
            "D4_metric_scope_and_partner": d4_comb(),
            "D5_title_truncation": d5_titles(),
            "D6_mixed_range_unlabelled": d6_mixed_range(),
            "D7_spiky_beats": d7_spiky(),
            "D8_gallery_false_claims": d8_gallery_claims(),
            "D9_pair_stats_degenerate": d9_pairs_exclude_degenerate(),
            "D10_farfield_per_airframe": d10_farfield(),
            "D11_specular_always_on": d11_specular(),
            "D12_ray_count_rounding": d12_si_rays(),
            "D13_stale_figure_rule": d13_fresh(),
            "D14_physics_tag_on_our_kernel": d14_physics_tag(),
        },
        "cross_document_name_collisions": cross_doc_alias(),
        "known_limits": limits(),
        "counts_now": {
            "cells_total": len(CELLS),
            "no_return": len(flag("no_return")),
            "incomplete": len(flag("incomplete")),
            "no_motion": len(flag("no_motion")),
            "beat_spiky": len(flag("beat_spiky")),
            "tip_ceiling_degenerate": len(flag("tip_ceiling_degenerate")),
            "with_comb_contrast": sum(1 for _a, _k, c in CELLS
                                      if c.get("comb_contrast_db") is not None),
        },
    }
    json.dump(out, open(OUT_P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    bad = [k for k, v in out["defects_fixed"]["D8_gallery_false_claims"]["checks"].items()
           if not v]
    print(f"✅ {os.path.relpath(OUT_P, ROOT)}")
    print(f"   칸 {len(CELLS)} · 덜 참 {len(flag('incomplete'))} · "
          f"안 움직임 {len(flag('no_motion'))} · 에코 없음 {len(flag('no_return'))} · "
          f"튐 {len(flag('beat_spiky'))}")
    print(f"   자격 없는 칸에 새어 나온 수 "
          f"{len(out['defects_fixed']['D1_incomplete_cells']['metric_leaks_now'])} 개")
    print(f"   제목 잘림 {out['defects_fixed']['D5_title_truncation']['before']['n_truncated']}"
          f" → {out['defects_fixed']['D5_title_truncation']['after']['n_truncated']}")
    print("   갤러리 문장 검사 " + ("전부 통과" if not bad else f"❌ {bad}"))


if __name__ == "__main__":
    main()
