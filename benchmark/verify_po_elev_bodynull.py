# -*- coding: utf-8 -*-
"""verify_po_elev_verdict.py — ⭐앙각 스윕 «−30°·−60° 이상» 최종 판정 원장.

앞선 두 산출물을 읽어 하나의 판정으로 묶는다(계산 안 함 · GPU 안 씀).
  · outputs/verify_po_elev_nulls.json       격자감사 + 고정자세 미세스윕 + DC/AC 분리
  · outputs/verify_po_elev_gridladder.json  격자 간격·부분셀 사다리(아티팩트 시험)

■ 이 라운드가 뒤집은 것 — **내 잣대가 틀렸다**
  (1) 「위상 변동폭(np.unwrap)」 은 도플러가 아니라 **복소 궤적의 원점 감김수**를 잰다.
      −60° 에서 min|E|/평균 = 0.012 라 궤적이 원점을 10.04 바퀴 감는다 → 4217° 는
      «도플러가 커졌다» 가 아니라 «|E| 가 0 을 스쳤다» 는 뜻이다.
  (2) 「−20 dB 폭」 은 전 구간 단일 Hann FFT 라 깊은 AM 의 측대역을 도플러로 오독한다.
  (3) 「변조 깊이」·「0 Hz 몫」 은 **비율**이다. 분모(정적 성분)가 죽으면 분자가 커진 것처럼
      보인다. ⇒ 대신 **절대 세기**를 갈라 써야 한다: P_dc = |⟨E⟩|² · P_ac = ⟨|E−⟨E⟩|²⟩.
"""
from __future__ import annotations

import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N = json.load(open(f"{ROOT}/outputs/verify_po_elev_nulls.json"))
G = json.load(open(f"{ROOT}/outputs/verify_po_elev_gridladder.json"))
F = json.load(open(f"{ROOT}/outputs/verify_po_elev_floor.json"))
OUT = f"{ROOT}/outputs/verify_po_elev_bodynull.json"

el = np.asarray(G["el_deg"], float)
tags = list(G["curves_db"].keys())
C = np.stack([np.asarray(G["curves_db"][t], float) for t in tags])


def at(t):
    i = int(np.argmin(np.abs(el - t)))
    v = C[:, i]
    return dict(el_deg=float(el[i]), median_db=round(float(np.median(v)), 2),
                spread_db=round(float(v.max() - v.min()), 2),
                per_lattice_db=[round(float(x), 2) for x in v])


scatter = {f"el{t:+.0f}": at(t) for t in (-30, -35, -45, -55, -60)}
ser = {int(r["el_deg"]): r for r in N["series_split"]}

# ── 동체 붕괴 vs 블레이드 증가 — 어느 쪽이 몇 dB 인가 ────────────────────────
def delta(a, b, key):
    return round(ser[a][key] - ser[b][key], 2)


mech = {
    "el-60_vs_el-15": dict(
        dP_dc_db=delta(-60, -15, "P_dc_db"),      # 동체(정적)
        dP_ac_db=delta(-60, -15, "P_ac_db"),      # 블레이드(변조)
        note_ko="동체가 −26.9 dB 무너지고 블레이드는 +5.4 dB 오른다 — 붕괴가 5 배 크다"),
    "el-30_vs_el-15": dict(
        dP_dc_db=delta(-30, -15, "P_dc_db"),
        dP_ac_db=delta(-30, -15, "P_ac_db"),
        note_ko="동체 −13.1 dB · 블레이드 +2.3 dB — 여기서도 붕괴가 지배"),
}
for k in mech:
    mech[k]["note_ko"] = (
        f"동체(P_dc) {mech[k]['dP_dc_db']:+.1f} dB · 블레이드(P_ac) {mech[k]['dP_ac_db']:+.1f} dB "
        f"— 동체 붕괴가 {abs(mech[k]['dP_dc_db'])/max(abs(mech[k]['dP_ac_db']), 1e-9):.1f} 배 크다")

verdict = {
    "_meta": {
        "generator": "benchmark/verify_po_elev_verdict.py",
        "inputs": ["outputs/verify_po_elev_nulls.json",
                   "outputs/verify_po_elev_gridladder.json",
                   "outputs/elevation_sweep_md.npz"],
        "question_ko": "−30°·−60° 만 왜 튀는가 — 물리인가 아티팩트인가",
    },
    # ─────────────────────────────────────────────────────────────────────────
    "A_격자는_원인이_아니다": {
        "frozen_across_elevations": N["_meta"]["grid_frozen_across_elevations"],
        "why_ko": "얼린 격자의 (ctr, Rout, n, spacing) 은 자세 합집합의 정점만으로 정해져 "
                  "앙각과 무관하다. grid_ref 는 앙각 루프 **밖에서 한 번** 만들어진다"
                  "(benchmark/elevation_sweep_md.py L114). 앙각에 걸리는 것은 격자의 방향뿐이고 "
                  "그건 광선이 레이더 쪽에서 와야 하므로 물리적 필연이다.",
        "basis_switch_ko": "다만 _grid_basis 는 |u_z| ≥ 0.9 (|el| ≥ 64.16°) 에서 보조축을 z→x 로 "
                           "바꾼다 → −75°·−90° 만 다른 in-plane 회전이다. −30°·−60° 는 "
                           "0/−15/−45 와 **같은** 규약이므로 이 전환은 이번 이상의 원인이 아니다.",
    },
    # ─────────────────────────────────────────────────────────────────────────
    "B_기제_동체붕괴이지_블레이드증가가_아니다": mech,
    "B_표": [dict(el_deg=k, P_dc_db=v["P_dc_db"], P_ac_db=v["P_ac_db"],
                 ac_over_dc_db=v["ac_over_dc_db"],
                 min_abs_over_mean=v["min_abs_over_mean"],
                 winding_turns=v["winding_turns"],
                 frozen_pose_body_db=v["frozen_pose_body_db"],
                 frozen_pose_prop_db=v["frozen_pose_prop_db"])
                for k, v in sorted(ser.items(), reverse=True)],
    # ─────────────────────────────────────────────────────────────────────────
    "C_널은_얇다": {
        "body_nulls_from_fine_sweep": [f for f in N["fine_nulls"] if f["tag"] == "body"][0],
        "note_ko": "동체 전용 패턴의 깊은 널은 3 dB 폭이 1.0~2.5° 다. 스윕은 15° 간격이라 "
                   "널이 «어디 있나» 를 못 본다 — 7 점 중 2 점(−30, −60)이 널 위에 앉은 것이다. "
                   "−30°·−60° 는 물리적으로 특별한 각이 아니라 **표본이 널을 밟은 각**이다.",
    },
    # ─────────────────────────────────────────────────────────────────────────
    "D_아티팩트_시험_격자사다리": {
        "verdict": G["verdict"],
        "lattice_scatter_db": scatter,
        "conclusion_ko": {
            "el-60": "⭐**물리다(위치는).** 격자 6 판(λ/12·λ/16·λ/20 + 부분셀 3 종) 전부에서 "
                     "널이 −59.9°~−61.7° 에 남는다. 광선을 아예 안 쏘는 **기하 PO**(면적분만)도 "
                     "−58.5° 에 동체 널을 낸다 — 독립 경로 2 개가 같은 각을 가리킨다. "
                     "다만 **깊이는 못 믿는다**: 9.4~41.3 dB 로 32 dB 흔들린다.",
            "el-30": "⚠**못 가른다 — 깊이는 격자가 지배한다.** 깊이가 3.3 dB(λ/16)~25.8 dB(λ/12) 로 "
                     "22 dB 흔들리므로 생산판(λ/12)이 인용한 −64.3 dB 는 그대로 못 쓴다. "
                     "다만 6 판 **중앙값**으로도 −63.8 dB 라 이웃(−35°: −51.8 · −45°: −58.1)보다 "
                     "6~12 dB 낮다 ⇒ 완전한 아티팩트라고도 못 한다. "
                     "광선을 안 쏘는 기하 PO 에는 이 널이 **없으므로**(−36°~−25° 가 −44.1~−45.2 dB 로 "
                     "1.1 dB 밖에 안 변한다) 원인은 (a) 가림·투과처럼 기하 PO 에 없는 물리이거나 "
                     "(b) 모든 광선격자가 공유하는 공통 편향이다 — **이번 라운드로는 둘을 못 가른다.** "
                     "가르려면 가림·투과를 끈 커널 대조군이 필요하다(다음 라운드).",
            "floor_ko": "널 밖에서도 동체 복소장의 격자 산포는 max−min 2.7~3.3 dB (±1.6 dB) 다. "
                        "널 바닥에서는 ±6 dB 로 벌어진다. ⇒ **우리 PO 의 단일 앙각 절대 DC 는 "
                        "널 근방에서 ±6 dB 이내로만 유효하다.**",
        },
    },
    # ─────────────────────────────────────────────────────────────────────────
    "E_왜_AC는_안_흔들리나": {
        "note_ko": "생산 스윕은 4096 자세 전부에 **같은 격자 한 판**을 쓴다. 그래서 격자 오차가 "
                   "슬로타임에 **공통 모드**로 들어간다 — 차이를 보는 P_ac 에서는 거의 상쇄되고, "
                   "절대값인 P_dc 에는 그대로 남는다. 실제로 P_ac 는 0°→−60° 에서 "
                   "−69.8→−65.4 dB 로 매끈하고(4.4 dB), P_dc 는 −54.5→−78.1 dB 로 들쭉날쭉하다. "
                   "⇒ 마이크로도플러(변조)는 이 결함에 강하고, 비율 잣대만 취약하다.",
        "P_ac_by_el_db": {str(k): v["P_ac_db"] for k, v in sorted(ser.items(), reverse=True)},
        "P_dc_by_el_db": {str(k): v["P_dc_db"] for k, v in sorted(ser.items(), reverse=True)},
    },
    # ─────────────────────────────────────────────────────────────────────────
    "F_el-90_은_예측대로다": {
        "P_ac_db": ser[-90]["P_ac_db"], "ac_over_dc_db": ser[-90]["ac_over_dc_db"],
        "note_ko": "−90° 에서 P_ac 는 −80.0 dB 로 이웃(−58~−70 dB)보다 10~22 dB 낮고 "
                   "AC/DC = −38.3 dB 다. 기하 PO 로는 **정확히 0** 이다 — 수직축 회전은 면의 "
                   "z 좌표도 n̂·û 도 안 바꾸므로 E 가 위상에 불변이다. 남은 −80 dB 는 "
                   "블레이드가 동체를 가리는 그림자의 회전 + 격자 이산화다. "
                   "⭐사용자 물리(직하방 도플러 0)와 커널이 맞는다.",
    },
    # ─────────────────────────────────────────────────────────────────────────
    "F2_물리상한으로_잰_수치바닥": {
        "numerical_floor_db": F["_meta"]["numerical_floor_db"],
        "how_ko": "|f| > 1.15·f_tip 의 슬로타임 전력은 물리적으로 불가능하다(팁보다 빠른 "
                  "산란체가 없고 sbr_field 는 단일 반사라 2× 도플러 경로가 없다). 그 전력이 "
                  "앙각 7 각 전부에서 −83~−88.5 dB (중앙값 −86.5) 로 **평평하다** ⇒ 이것이 "
                  "AC 채널의 수치 바닥이다.",
        "rows": F["band_limit_test"],
        "conclusion_ko": {
            "blade_is_real": "−60° 의 P_ac = −65.5 dB 는 바닥보다 **+20.9 dB** 위다 → "
                             "그 앙각의 블레이드 변조는 진짜다(아티팩트가 아니다).",
            "body_is_the_fragile_one": "반면 −60° 의 P_dc = −78.1 dB 는 바닥에서 8 dB 위일 뿐이고 "
                                       "격자 산포가 ±6 dB 다 → **분모가 못 믿을 양**이다. "
                                       "그 분모로 나눈 변조깊이 0.390 · 0 Hz 몫 5.91 % 는 "
                                       "그래서 커진 것이다.",
            "el-90_validates": "−90° 는 P_ac 가 바닥에서 +6.5 dB 이고 그 전력의 100 % 가 "
                               "대역 밖(f_tip = 0 이므로 전부)이다 → 사실상 **바닥 그 자체**. "
                               "사용자 물리(직하방 도플러 0)와 커널이 맞는다.",
        },
    },
    "F3_동체_면법선_투영": {
        "rows_at_7els": [r for r in F["body_normals"]
                         if int(r["el_deg"]) in (0, -15, -30, -45, -60, -75, -90)],
        "mechanism_ko": "정반사(법선이 시선 10° 안) 면적은 el 0° 에서 투영면적의 36.1 % "
                        "(정면 판) → −25°~−45° 에서 **0.27~0.32 %** 로 사라짐 → −60° 4.6 % → "
                        "−90° 47.1 % (평평한 배면) 로 되돌아온다. ⭐즉 −25°~−45° 는 "
                        "**동체에 정반사면이 아예 없는 어깨 구간**이라 장이 «작은 기여들의 "
                        "무작위 위상 합» 이 된다 — 깊은 널이 잘 생기고 격자에 가장 민감하다. "
                        "−60° 는 배면 판이 켜지기 시작하지만 정반사에서 30° 벗어나 판 위에서 "
                        "위상이 감겨 **상쇄가 27.3 dB 로 최대**다(−90° 42.0 dB 제외). "
                        "⇒ −60° 널은 «큰 판의 사이드로브 널» 이라 구조적이고, −30° 널은 "
                        "«정반사 없는 구간의 스페클» 이라 격자마다 달라진다. "
                        "격자 사다리 결과와 정확히 맞물린다.",
    },
    "G_남은_결함": [
        "널 근방의 절대 DC 는 격자 의존이 ±6 dB 라 신뢰구간을 붙이지 않고 인용하면 안 된다.",
        "15° 간격 앙각 스윕은 3 dB 폭 1~2.5° 의 널 구조를 근본적으로 못 푼다 — "
        "앙각을 결론에 쓰려면 2° 이하 간격이거나 널을 평균해 없애야 한다.",
        "elevation_sweep_md.json 의 _meta.ours_illumination 이 'spherical wave at 15 m' 인데 "
        "실제 RANGE_M 은 10.0 m 다 — 문서 오기(계산은 10 m 로 돌았다).",
        "이번 판정은 az 고정 단면이다. 널의 방위각 의존은 안 쟀다.",
        "−30° 널의 «가림·투과 물리» vs «광선격자 공통 편향» 을 못 갈랐다 — 가림·투과를 끈 "
        "커널 대조군이 있어야 갈린다.",
        "고정 자세(ph[0]) 한 장으로 미세 스윕을 했다. 생산 계열의 P_dc 는 4096 자세 평균이라 "
        "블레이드 DC 가 더 상쇄에 끼어든다(그래서 −60° 에서 −78.1 dB 로 고정자세 −71.8 dB 보다 "
        "더 깊다) — 두 수를 같은 것처럼 나란히 쓰면 안 된다.",
    ],
}
json.dump(verdict, open(OUT, "w"), ensure_ascii=False, indent=1)
print(json.dumps(verdict["D_아티팩트_시험_격자사다리"]["conclusion_ko"],
                 ensure_ascii=False, indent=1))
print(f"\n✅ {OUT}")
