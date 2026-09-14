#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""대역 안에서 **전력과 변조 구조**가 반송파를 따라 움직이나 — 5G NR 100 MHz 다섯 점.

⛔⛔**제목을 좁혔다** (2026-09-13(6)). 처음에는 「표적이 평평한가」·「복소 반사율이
평평한가」로 적었는데 **이 판독기는 위상을 못 본다.** 여기 지표는 전부 |E| 나
|E − mean E| 로 만들어져 반송파마다 **상수 위상을 돌려도 값이 한 자리도 안 바뀐다**
(점검자 실측: 1.1 rad 씩 4.4 rad 범위로 돌려도 출력 변화 0 건. 정의상 불변이다).
⇒ 발주서(runners/make_jobs_0929.py:35)가 물은 「크기·위상 모두」 중 **크기 쪽만** 답한다.
  위상 평탄성은 알려진 전파 지연을 제거하고 같은 자세의 복소 응답을 견주는 **별도 항목**이고,
  성긴 다섯 점 사이의 지연 모호성도 함께 적어야 한다 — 아직 안 했다.

  PYTHONPATH=src:benchmark python benchmark/read_bandflat_0913.py

무엇을 묻나
-----------
지금 사슬에서 파형은 **산란이 끝난 뒤 곱해지는 스칼라**다. 그래서 「한 대역 안에서 표적의
복소 반사율이 평평한가」를 한 번도 안 봤다. 0929 가 그 구멍을 메우려고 3.450 · 3.475 ·
3.525 · 3.550 GHz 를 샀다(중앙 3.500 은 이미 있었다) — **자유공간과 실외 둘 다**.

⛔이것은 OFDM 을 계산한 것이 아니다. 다섯 점을 **따로** 계산해 겹쳐 보는 것뿐이다.
⛔여기 나오는 레벨은 σ(dBsm)가 아니다 — 면적이 그 식에 없다. 환산하지 않는다.
⛔다른 엔진과 절대 레벨을 견주지 않는다. 이 글의 모든 칸은 **한 엔진·한 팔**이다.

어떻게 읽나 — ⭐대조군이 없으면 「퍼짐 4 dB」는 아무 뜻이 없다
-----------------------------------------------------------
반송파를 갈면 값이 달라진다. 그런데 **같은 반송파로 다시 재도** 값은 달라진다(자세를 유한
개 뽑으므로). 그래서 두 퍼짐을 나란히 낸다.

  대역 퍼짐        다섯 반송파 사이의 최대−최소 [dB]
  짝·홀 분할 차이  **같은 칸**의 자세를 짝수/홀수로 갈라 각각 잰 값의 차 [dB]

⛔⛔**통계를 짝 맞춰 견딘다** (2026-09-13(6) 정정 — 여기서 한 번 틀렸다)
  전체 전력의 대역 퍼짐  ↔  **전체 전력**의 짝·홀 분할 차이
  움직이는 몫의 대역 퍼짐 ↔  **AC 전력**(전체 평균을 뺀)의 짝·홀 분할 차이
  섞으면 결론이 거꾸로 나온다. 실측: 실외 el −30 의 분할 차이가 전체 전력으로는
  0.015 dB 인데 같은 AC 통계로는 **1.647 dB** 다(el −60 은 0.008 → 0.833 dB). 처음 판은
  전자와 견주어 「대역 퍼짐이 분할 차이보다 크다」고 적었는데, 맞춰 보면 실외 두 줄은
  **분할 차이에 묻힌다.**

⛔⛔**이 분할 차이가 무엇이고 무엇이 아닌지**
  이다    결정적 표본 분할의 민감도 — 자세를 어느 쪽 절반으로 재느냐의 차이.
  아니다  재실행 산포(이 엔진은 씨앗이 없어 같은 장면은 같은 값이다) · 광선 격자 민감도
          (격자를 흔들려면 격자 사다리 칸을 따로 사야 한다 — ⛔실측: 원장에 537 행 있지만
           **이 팔 계열에는 0 개**다) · 신뢰구간.
  ⇒ 「대역 퍼짐 ÷ 분할 차이」 배수를 **머리기사 숫자로 쓰지 않는다.**

⛔여기서 «평평하다»로 결론짓지 않는다 — 다섯 점은 다섯 점이다.

마이크로도플러 축
-----------------
⛔반송파가 바뀌면 날개끝 도플러도 fc 를 탄다(f_tip ∝ fc). 겹쳐 볼 때는 띠를 **그 칸의
f_tip** 으로 잡는다 — 안 그러면 「무늬가 달라졌다」가 아니라 「자를 바꿨다」를 보는 것이다.

⛔⛔정지 성분을 먼저 뺀다 — 2026-09-13 에 이것 때문에 헛것을 볼 뻔했다
--------------------------------------------------------------------
실외에서 돌아오는 것의 **99.1 %는 안 움직인다**(지면). 정지 성분을 둔 채 STFT 를 뜨면
0 Hz 의 거대한 에너지가 창의 옆잎으로 날개끝 띠(0.35~1.0×f_tip)까지 샌다. 실측(el −30):

    띠 전력   정지 성분 그대로 −49.8 dB   ·   정지 성분 제거 −64.3 dB
    ⇒ 그 띠에 있던 것의 약 97 %가 **지면이 샌 것**이었다.

그 샘을 두고 재면 으뜸 봉우리가 3.500 과 3.525 GHz 사이에서 460.7 → 58.2 Hz 로 **계단처럼**
갈아타고 모양 상관이 0.38 까지 떨어진다 — 25 MHz 가 만든 물리로 읽으면 틀린다. 정지 성분을
빼면 다섯 반송파가 모두 58.2 Hz 에 모이고 상관이 0.9986 이상이 된다. 그래서 여기서는
**언제나 빼고 잰다**. 뺀 것과 안 뺀 것을 둘 다 적어 둔다(왜 그렇게 골랐는지가 보이게).

⛔레벨도 마찬가지다 — 실외의 level_db 는 **지면**이지 표적이 아니다. 표적에 관해 말할 수
있는 것은 «움직이는 몫» 뿐이므로 둘을 갈라 적는다.

⛔⛔⛔그런데 실외에서는 **그 «움직이는 몫»도 두 구조 문턱을 못 넘는다** (2026-09-13 실측)
------------------------------------------------------------------------
「정지 성분을 뺐으니 이제 표적이다」로 넘어가면 또 틀린다. 뺀 나머지에 날개 무늬가 있는지
**세어 보면** 이렇다(확산만 팔 · 15 m):

              리듬 몫 [%]     빗살 대비 [dB]     날개끝 띠가 움직임에서
    자유공간   80 ~ 96         +46 ~ +54          24 ~ 87 %
    실외       12.5 ~ 13.1     −0.8 ~ +0.3         4.8 ~ 8.0 %
    백색잡음   12.6 (셀 수 있는 널)   0.0

실외 값은 **설정한 두 문턱을 못 넘는다.** ⛔«백색잡음이다» 로 읽지 않는다 — 두 문턱은
우리가 정한 값이고 잡음 모형과의 검정이 아니다(널 분포·오류율·검정력을 안 쟀다).
반례: 잡음 0 인 501 Hz 단일 정현파도 빗살 대비 86.08 dB 인데 AND 라서 미통과다.
그 바닥은 정지 성분의 −20.4 dB(el −30)
· −19.8 dB(el −60)로, 두 앙각에서 거의 같은 비율로 따라붙고 다섯 반송파에서 전부 0.9 %다
— 정지 성분에 **비례하는 바닥**의 모습이다.

⇒ 그래서 실외 줄의 「대역을 가로질러 0.24 dB」는 **표적이 평평하다는 뜻이 아니다.** 이 팔·
  이 거리에서 **두 구조 문턱을 못 넘는다**는 뜻이고, 그것이 「날개가 없다」는 아니다. ⛔실외 숫자를 「표적의 대역 평탄성」
  으로 인용하지 않는다. ⚠그 바닥을 무엇이 만드는지는 이 자료만으로 못 가른다 — 자세마다
  광선 집합이 조금씩 달라지는 것이 유력하지만, 여기서 단정하지 않는다.
"""
from __future__ import annotations
import json, os, re, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "src"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
from md_mapstyle import auto_periods, flash_spec                      # noqa: E402
from arm_grammar import matched_groups, parse as parse_arm, unparse  # noqa: E402
from drones import DRONES                                            # noqa: E402
from reader_gate import cell, check_series, publish                        # noqa: E402
from arm_grammar import unparse as unparse_arm                       # noqa: E402


def ray_spread_db(arm: str, el: float, rows: list, Z, win: float = 0.05) -> tuple:
    """⭐⭐**정본 대조군** — 광선 예산을 ±win 흔들었을 때 움직이는 몫의 퍼짐 [dB].

    ⛔⛔2026-09-13(8) — 이 판독은 대조군을 **세 번** 갈았다. 짝·홀 자세 분할(틀림:
      이 물음에 대응하지 않는 비교) → 되풀이(재현성 2.76e−05 dB 안인데 **같은
      광선 격자를 다시 도는 것**이라 격자 민감도를 못 덮는다) → **광선 예산 사다리**.
    ⭐그 사다리가 **이미 원장에 있었다**(자유공간 19 묶음 · 협곡 5 앙각 × 7 점 ·
      지면조각 2 벌). 살 것이 아니라 읽을 것이었다.
    ⛔⛔**이것은 대역 «모양» 의 잣대가 아니다**(2026-09-14 정정). 이 값은 **한 반송파의
      레벨 민감도**다. 예산을 흔들었을 때 다섯 반송파의 레벨이 **똑같이** 움직이면
      대역 모양은 한 자리도 안 바뀌는데 이 값은 커진다 — 합성 반례로 재현했다(모든
      반송파를 정확히 1 dB 올리면 모양 변화 0.000 dB 인데 옛 판정은 「묻힌다」였다).
      거꾸로 레벨은 그대로 두고 기울기만 갈아타면 이 값이 0 이 되어 「크다」가 나온다.
      ⇒ 대역 모양이 예산에 얼마나 민감한지는 `budget_shape_spread_db`(아래)로 잰다.
    ⛔실측(±5 %): 자유공간 el −30 **1.042 dB** · el −60 **1.414 dB**.
    ⚠실외(`envoutdoor01`) 팔에는 짝이 **없다** — 사다리가 `outdoor01_ground` 와 협곡에만
      있다. 그 이웃들의 값(지면조각 0.303 · 협곡 0.426~0.910 dB)은 실외 대역 퍼짐
      0.235~0.239 dB 보다 **크다** — 곧 실외 두 줄도 묻힐 자리로 보이지만, 짝이 없으므로
      **여기서 «묻힌다»로 단정하지 않는다.**
    """
    try:
        from arm_grammar import parse as _p
        f = _p(arm)
    except Exception:
        return None, 0
    base = float(f.get("spp") or 0) or 4e9
    key = {k: v for k, v in f.items() if k != "spp"}
    vals = []
    for r in rows:
        if float(r["el_deg"]) != el:
            continue
        try:
            g = _p(r["engine"])
        except Exception:
            continue
        if {k: v for k, v in g.items() if k != "spp"} != key or not g.get("spp"):
            continue
        if abs(float(g["spp"]) - base) > win * base:
            continue
        k = f"{r['engine']}/el{el:+g}"
        if k not in Z.files:
            continue
        E = np.asarray(Z[k], complex)
        p = float(np.mean(np.abs(E - E.mean()) ** 2))
        if p > 0:
            vals.append(10.0 * np.log10(p))
    #: ⭐**반올림하지 않는다**(2026-09-13(10)) — 옛 판의 「0.000 dB」는 정확한 영이
    #  아니라 작은 수의 반올림이었다(실측 2.76e−05 · 2.07e−06 · 2.97e−08 · 5.30e−07 dB).
    return (float(max(vals) - min(vals)) if len(vals) > 1 else None), len(vals)


def budget_shape_spread_db(arm_by_fc: dict, el: float, rows: list, Z,
                           win: float = 0.05) -> dict | None:
    """⭐**대역 «모양»이 광선 예산에 얼마나 움직이나** — 레벨 민감도와 다른 자다.

    무엇을 재나
    -----------
    예산 b 마다 그 예산으로 있는 반송파들의 움직이는 몫 L_b(f) 를 모아
        D_b(f) = L_b(f) − L_b(f중심)
    을 만들고, 기준 예산(SPP_PRIMARY) 대비 `max_f |D_b(f) − D기준(f)|` 의 예산별 최대를
    돌려준다. 모든 반송파가 **같은 양**만큼 움직이면 D 가 안 변하므로 이 값은 0 이다 —
    레벨 민감도(`ray_spread_db`)와 갈리는 지점이 바로 여기다.

    왜 필요한가 (2026-09-14 · 외부 점검 + 적대 검증이 합성 반례로 재현)
    -----------------------------------------------------------------
    옛 판정은 **중심 반송파 하나**의 레벨 민감도를 대역 기울기의 문턱으로 썼다.
      · 다섯 반송파를 정확히 1 dB 올린 판 → 모양 변화 **0.000 dB** 인데 「묻힌다」
      · 레벨은 그대로 두고 기울기만 2 dB 갈아탄 판 → 레벨 민감도 **0.000 dB** 라 「크다」
    둘 다 거꾸로다. 옛 규칙은 대역 모양을 안 보고 있었다.

    ⛔**짝이 없으면 None 을 돌려준다** — 반송파 2 개 미만이거나 예산 2 개 미만.
      오늘 원장이 정확히 그 상태다: 예산 사다리는 **중심 반송파에만** 있고 비중심
      네 반송파는 예산이 한 벌뿐이다(2026-09-14 실측). 큐 0930 의 C 묶음 10 줄이
      예산 3.9e9 × 반송파 5 개 × el −60 을 사서 그 짝을 처음 만든다.
    ⛔None 일 때 「묻힌다/크다」로 단정하지 않는다. 못 잰 것은 못 잰 것이다.
    """
    try:
        from arm_grammar import parse as _p, unparse as _u
    except Exception:
        return None
    #: 예산 → {반송파: 레벨}. 이름에서 spp 만 갈아 끼워 찾는다.
    by_budget: dict[str, dict[int, float]] = {}
    #: 뺀 칸을 사유와 함께 남긴다 — 조용히 버리지 않는다.
    dropped: list[dict] = []
    ref_prf: list = [None]
    for fc_mhz, arm0 in sorted(arm_by_fc.items()):
        try:
            f0 = _p(arm0)
        except Exception:
            continue
        base = float(f0.get("spp") or 0) or 4e9
        #: ⛔⛔2026-09-14 사용자 점검 — 기준 표집률이 **행 순서**를 탔다. 위에서 「모든 검사를
        #  지난 행에서만 기준을 세운다」로 고쳤지만, 그래도 «어느 지난 행이 먼저 오나» 가
        #  남는다(거절 사유 문구가 갈린다). ⇒ 순회를 **이름순으로 고정**해 기준이 되는 행을
        #  입력 순서와 무관하게 정한다. 값도 사유도 그때 보존된다.
        for r in sorted(rows, key=lambda x: (str(x.get("engine")), float(x.get("el_deg") or 0.0))):
            if float(r["el_deg"]) != el:
                continue
            try:
                g = _p(r["engine"])
            except Exception:
                continue
            if {k: v for k, v in g.items() if k != "spp"} != {k: v for k, v in f0.items()
                                                              if k != "spp"}:
                continue
            spp = g.get("spp")
            if not spp or abs(float(spp) - base) > win * base:
                continue
            k = f"{r['engine']}/el{el:+g}"
            if k not in Z.files:
                continue
            #: ⛔⛔2026-09-14(4) — 이 대조군은 **주 곡선이 지나는 관문을 통째로 건너뛰었다.**
            #  실측 반례: 대조군 원장에 빠진 자세 4,096 개와 다른 표집률 10,000 Hz 를
            #  적어도 이 함수는 20.0 dB 를 그대로 돌려줬다. 주 곡선은 :531 에서 완전성·
            #  전계 0·잘림·세대·반송파 어긋남을 보고 거르는데 여기만 안 봤다.
            #  ⇒ **같은 계약**을 건다. 뺀 예산·반송파는 사유와 함께 남긴다.
            _w = []
            if r.get("n_missing"):
                _w.append(f"자세가 덜 찼다({r['n_missing']} 개)")
            if r.get("n_zero_field"):
                _w.append(f"전계가 0 인 자세({r['n_zero_field']} 개)")
            if r.get("truncated") or r.get("n_trunc"):
                _w.append("경로가 잘렸다")
            _mg2 = r.get("mixed_generations")
            if isinstance(_mg2, dict):
                if (int(_mg2.get("kept_conflicting_poses") or 0)
                        or _mg2.get("tie_unresolved") or _mg2.get("n_poses_disagree")):
                    _w.append("굽기 세대를 하나로 못 풀었다")
            elif _mg2:
                _w.append("굽기 세대가 섞였다")
            #: ⭐**시간축** — 표집률이 기준과 다르면 대역 모양을 견줄 수 없다.
            #  ⛔⛔2026-09-14 사용자 점검이 찾은 것 — 전에는 **여기서 바로** ref_prf 를 세웠다.
            #    그런데 이 행은 아직 다른 검사를 안 지났다. 거절될 행이 기준을 선점하면,
            #    그 행을 버린 뒤에도 기준은 남아 **멀쩡한 행까지 거절한다.**
            #    실측: 같은 행 집합의 **순서만 바꿔도** 비교 주파수 수가 0 ↔ 2 로 뒤집혔다.
            #  ⇒ 기준은 **모든 검사를 지난 행**에서만 세운다(아래 `if _w:` 뒤).
            _pr = r.get("prf_hz")
            if _pr is None:
                _w.append("표집률을 모른다")
            elif ref_prf[0] is not None and abs(float(_pr) - ref_prf[0]) > 1.0:
                _w.append(f"표집률이 기준과 다르다({_pr} · 기준 {ref_prf[0]})")
            if abs(float(r.get("fc_hz", 0)) / 1e6 - float(fc_mhz)) > 1.0:
                _w.append(f"원장 fc_hz({r.get('fc_hz')})가 이름 꼬리표와 어긋난다")
            E = np.asarray(Z[k], complex)
            if not np.isfinite(E).all():
                _w.append(f"비유한 값이 {int((~np.isfinite(E)).sum())} 자세에 있다")
            if _w:
                dropped.append({"spp": str(spp), "fc_mhz": int(fc_mhz),
                                "el_deg": el, "why": " · ".join(_w)})
                continue
            #: ⭐여기까지 온 행만 **모든 검사를 지났다.** 기준 표집률은 그런 행에서만 세운다.
            if ref_prf[0] is None:
                ref_prf[0] = float(_pr)
            pw = float(np.mean(np.abs(E - E.mean()) ** 2))
            if pw > 0:
                by_budget.setdefault(str(spp), {})[int(fc_mhz)] = 10.0 * np.log10(pw)
    ref = str(int(float(SPP_PRIMARY)))
    if ref not in by_budget:
        ref = max(by_budget, key=lambda b: len(by_budget[b])) if by_budget else None
    if ref is None:
        return ({"ref_spp": None, "per_budget": [], "n_budgets": 0, "n_fc": 0,
                 "shape_spread_db": None, "dropped": dropped,
                 "n_dropped": len(dropped), "prf_hz": ref_prf[0],
                 "gate_ko": "쓸 수 있는 예산이 없다 — 아래 dropped 를 본다."}
                if dropped else None)
    #: 두 예산 **모두**에 있는 반송파만 쓴다 — 없는 칸을 0 으로 메우지 않는다.
    out = {"ref_spp": ref, "per_budget": [], "n_budgets": 0, "n_fc": 0,
           "shape_spread_db": None, "dropped": dropped, "n_dropped": len(dropped),
           "gate_ko": ("주 곡선과 **같은 관문**을 건다 — 완전성·전계 0·잘림·세대·표집률·"
                       "반송파 어긋남·비유한 값. 뺀 칸은 dropped 에 사유와 함께 남는다."),
           "prf_hz": ref_prf[0]}
    best = None
    for b, cur in sorted(by_budget.items()):
        if b == ref:
            continue
        fcs = sorted(set(cur) & set(by_budget[ref]))
        if len(fcs) < 2:
            continue
        ctr = 3500 if 3500 in fcs else fcs[len(fcs) // 2]
        d_ref = {f: by_budget[ref][f] - by_budget[ref][ctr] for f in fcs}
        d_cur = {f: cur[f] - cur[ctr] for f in fcs}
        m = max(abs(d_cur[f] - d_ref[f]) for f in fcs)
        out["per_budget"].append({"spp": b, "n_fc": len(fcs), "fc_mhz": fcs,
                                  "center_fc_mhz": ctr,
                                  "shape_spread_db": round(float(m), 4)})
        out["n_fc"] = max(out["n_fc"], len(fcs))
        best = m if best is None else max(best, m)
    out["n_budgets"] = len(out["per_budget"]) + (1 if out["per_budget"] else 0)
    if best is None:
        return None
    out["shape_spread_db"] = round(float(best), 4)
    return out


def repeat_spread_db(arm: str, el: float, rows: list, Z) -> tuple:
    """⭐**옳은 대조군** — 같은 설정을 다시 돌린 판(`--rep`) 사이의 움직이는 몫 퍼짐 [dB].

    ⛔⛔2026-09-13(7) → (10) 정정. 처음에는 짝·홀 자세 분할 차이를 «흔들림» 이라 부르며
      대조군으로 썼고, 그 뒤 「같은 AC 통계로 맞추면 실외 두 줄이 묻힌다」로 **뒤집었다.**
      ⛔둘 다 틀렸고, 그것을 «계통적 치우침» 이라 부른 **논증도 거둔다** — 「AC 를 10^±6 배
        해도 dB 차가 같다」는 전력비에서 **공통 배율이 정의상 소거**되므로 아무것도 증명하지
        않는다. 짝·홀 분할이 대조군이 아닌 까닭은 **이 물음에 대응하지 않기 때문**이다:
        각 집합을 중앙 반송파에 맞추면 반송파 변화 대비 최대 차가 0.0033 dB 이고
        짝수만·홀수만의 대역 퍼짐은 0.2359·0.2342 dB 로 거의 같다 — 절대 짝·홀 차가 커도
        **대역 축의 비교는 그 차에 안 실린다.**
    ⭐실측(2026-09-13(10), 원정밀도): 이 팔들의 되풀이 판은 합친 움직이는 몫이
      **2.76e−05 · 2.07e−06 · 2.97e−08 · 5.30e−07 dB** 안에서 같다(옛 「0.000 dB」는
      반올림이었다). 자세 하나까지 보면 자유공간 el −30 에서 최대 **2.85 %** 다르다
      (옛 「44~48 %」는 다른 정의로 잰 수였다 — 여기 정의는 |ΔE|/|E| 다).
    ⚠되풀이가 있는 반송파는 **중앙 3.500 GHz 하나**뿐이다 — 대역 전체의 수렴성이 아니다.
    ⚠되풀이는 **같은 광선 격자를 다시 도는 것**이라 격자 민감도는 못 덮는다 —
      그 대조군(광선 예산 사다리)은 이 팔 계열에 아직 없다.
    """
    f = None
    try:
        from arm_grammar import parse as _p
        f = _p(arm)
    except Exception:
        return None, 0
    #: ⛔⛔2026-09-13(10) — **되풀이가 있는 반송파는 중앙(3.500 GHz) 하나뿐**이다.
    #  옛 판은 다섯 반송파의 단독 실행까지 판 수에 넣어 10·12·8·8 로 적었는데, 같은
    #  조건의 **되풀이 수**는 6·8·4·4 다. 그 둘을 나눠 센다.
    vals, n = [], 0
    have = {(r["engine"], float(r["el_deg"])) for r in rows}

    def _ac(a):
        k = f"{a}/el{el:+g}"
        if k not in Z.files:
            return None
        E = np.asarray(Z[k], complex)
        p = float(np.mean(np.abs(E - E.mean()) ** 2))
        return 10.0 * np.log10(p) if p > 0 else None

    v = _ac(arm)
    if v is not None:
        vals.append(v)
    for k in range(1, 9):
        g = dict(f)
        g["rep"] = str(k)
        nm = unparse_arm(g)
        if (nm, el) in have:
            w = _ac(nm)
            if w is not None:
                vals.append(w)
                n += 1
    #: ⭐**반올림하지 않는다**(2026-09-13(10)) — 옛 판의 「0.000 dB」는 정확한 영이
    #  아니라 작은 수의 반올림이었다(실측 2.76e−05 · 2.07e−06 · 2.97e−08 · 5.30e−07 dB).
    return (float(max(vals) - min(vals)) if len(vals) > 1 else None), len(vals)


def flash_of(arm: str, default: float) -> float:
    """⭐그 팔의 날개 통과율 [Hz] — 기체 꼬리표가 정한다(2026-09-13(6)).

    ⛔머리말의 한 값(기본 기체)을 모든 팔에 쓰면 기체가 다른 팔의 배음 잣대가 엉뚱한
      자리에서 잰다 — 주 집계에서 실제로 그랬다(488 칸 중 445 칸이 바뀐다).
    ⚠이 판독기가 고른 20 칸은 지금 **전부 기본 기체**라 값은 안 바뀐다. 그래도 규칙을
      코드에 박아 둔다 — 팔 목록이 늘면 조용히 틀리기 때문이다.
    """
    try:
        key = parse_arm(arm).get("drone")
    except Exception:
        key = None
    sp = DRONES.get(key) if key else None
    return (float(int(sp.prop_blades) * float(sp.hover_rpm) / 60.0)
            if sp is not None else float(default))

LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
LED_N = os.path.join(ROOT, "outputs", "elevation_sweep_md.npz")
OUT_J = os.path.join(ROOT, "outputs", "bandflat_0913.json")
#: ⭐다른 두 갈래(장면 물리·파형 생존)와 같은 규약 — 읽는 문서도 함께 굽는다.
#  ⛔손으로 쓰지 않는다. 이 스크립트만이 이 파일을 만든다.
OUT_MD = os.path.join(ROOT, "docs", "BANDFLAT_0913.md")

#: 5G NR n78 의 100 MHz 폭 한 덩이를 다섯 점으로. 중앙은 꼬리표가 **없는** 팔이다.
FCS_MHZ = (3450, 3475, 3500, 3525, 3550)
#: ⛔⛔**읽을 범위를 선언한다.** 같은 대조군 안에도 24 GHz 팔이 있어서(꼬리표가 fc 하나만
#  다르므로 문법으로는 한 묶음이다), 범위를 안 적으면 「대역 평탄성」에 **반송파 의존성**이
#  섞인다 — 퍼짐이 4.24 dB 가 아니라 28.32 dB 가 된다(2026-09-13 실측).
BAND_SPAN_MHZ = (3400, 3600)
#: ⭐이 판독이 **일부러 흔드는 축**. 대조군 검사는 이 축들만 달라도 «한 묶음» 으로 본다.
#  ⛔2026-09-13(9) 신설 — 0930 발주서가 광선 예산 짝(3.9e9)을 사 온다. 그것이 원장에
#    들어오면 옛 검사(vary=["fc","env"])는 묶음을 둘로 세어 **SystemExit 로 죽는다**.
#    자료가 오기 전에 미리 넓혀 둔다. ⚠판독은 여전히 **예산마다 따로** 낸다 — 예산이
#    다른 칸을 같은 대역 곡선에 섞지 않는다(아래 SPP_PRIMARY).
VARY_AXES = ("fc", "env", "spp")
#: 대역 곡선을 그리는 정본 예산. 나머지 예산은 **대조군**으로만 읽는다.
SPP_PRIMARY = "4000000000"
ELS = (-30.0, -60.0)
#: 팔 이름의 형태 — 꼬리표 하나만 다르고 나머지가 **글자 그대로 같아야** 짝이다.
STEM_HEAD = "sionna_p4000000000_swR0D0E0F1_r15_n8192"
STEM_TAIL = "mfixbatteryi5_blperairframe_d2"
ENVS = {"free": "", "outdoor01": "envoutdoor01"}

FC_RE = re.compile(r"_fc(\d+)(?=_)")


def arm_name(env: str, fc_mhz: int) -> str:
    """⭐이름을 **짓는다** — 원장에서 정규식으로 긁으면 «outdoor01_fc3450» 같은 것이
    환경 이름으로 딸려 온다(2026-09-13 에 실제로 당했다). 지어서 찾으면 그 일이 없다.

    ⭐2026-09-13(2): 지은 이름이 **문법으로 되읽히는지** `src/arm_grammar` 로 확인한다.
      되읽은 환경·반송파가 내가 뜻한 것과 다르면 여기서 멈춘다 — 판독기가 엉뚱한 팔을
      집어 들고 조용히 계속 가는 일이 없게."""
    mid = [x for x in (ENVS[env], "" if fc_mhz == 3500 else f"fc{fc_mhz}") if x]
    name = "_".join([STEM_HEAD, *mid, STEM_TAIL])
    f = parse_arm(name)                       # strict — 되짓기까지 확인한다
    want_env = None if env == "free" else env
    want_fc = None if fc_mhz == 3500 else str(fc_mhz)
    if f.get("env") != want_env or f.get("fc") != want_fc:
        raise SystemExit(f"⛔ 지은 이름이 뜻대로 안 읽힌다: {name}\n"
                         f"   뜻한 것 env={want_env} fc={want_fc}\n"
                         f"   읽힌 것 env={f.get('env')} fc={f.get('fc')}")
    return name


def control_group_check(arms: list[str]) -> dict:
    """⭐이 판독기가 고른 팔들이 **정말 한 축만 다른가** — 문법으로 확인한다.

    ⛔이 검사가 있는 까닭(사용자 지적, 2026-09-13): 즉석 필터로 반송파를 견주다가
      다른 기체(s1000plus)와 다른 대역(24 GHz)이 섞여 20 dB·48 dB 폭이 나왔다.
      숫자가 커서 «발견» 처럼 보였지만 그것은 표적이 아니라 **섞임**이었다.
    """
    g = matched_groups(arms, vary=list(VARY_AXES))
    return {"n_groups": len(g),
            "one_group_only": len(g) == 1,
            "fixed_fields": (sorted(dict(list(g)[0]).items()) if len(g) == 1 else None),
            "varied": sorted("·".join("없음" if x is None else str(x) for x in k)
                             for k in list(g.values())[0]) if len(g) == 1 else None}


def el_key(el: float) -> str:
    return f"{el:+g}"


def halves_level_db(E: np.ndarray, *, ac: bool = False) -> tuple[float, float]:
    """같은 칸을 짝수 자세 / 홀수 자세로 갈라 각각 레벨을 낸다 — **짝·홀 분할 차이**.

    ac : 참이면 **전체 자세 평균을 한 번 빼고** 같은 분할을 적용한다(움직이는 몫의 통계).

    ⛔⛔**이것은 대조군이 아니다** (2026-09-13(6) → (10) 다시 정정).
      ⛔한때 나는 「AC 를 10^±6 배 해도 이 dB 차가 안 바뀌니 계통적 치우침이다」라고 적었다.
        **그 논증은 성립하지 않는다** — 전력비 10log10(c²P짝 / c²P홀) 에서 공통 배율 c 는
        **정의상 소거된다**. 진폭 불변은 «계통» 의 증거가 아니라 그 잣대의 성질일 뿐이다.
      ⭐대조군의 적절성은 **물음에 대응하는 비교와 그 불확도**로 정한다. 여기 물음은
        「반송파를 옮기면 값이 움직이나」이므로, 대조군은 **반송파를 안 옮기고 다시 잰 것**
        (되풀이)과 **광선 표본 자리를 흔든 것**(예산 사다리)이다. 짝·홀 자세 분할은
        그 물음에 대응하지 않는다 — 각 집합을 중앙 반송파에 맞춰 보면 반송파 변화 대비
        최대 차는 0.0033 dB 이고, 짝수만·홀수만으로 잰 대역 퍼짐은 0.2359·0.2342 dB 로
        거의 같다. 곧 절대 짝·홀 차가 커도 **대역 축의 비교는 그 차에 안 실린다.**
      ⇒ 표에 **참고로만** 남긴다.
    ⛔⛔**전체 전력의 분할 차이를 움직이는 몫의 대역 퍼짐과 견주면 안 된다** — 통계가
      다르다. 실측(점검자 2026-09-13): 실외 el −30 에서 전체 전력 분할 차이는 0.015 dB
      인데 **같은 AC 통계로 맞추면 1.647 dB** 다(el −60 은 0.008 → 0.833 dB). 그 통계로
      맞추면 실외 두 줄의 「대역 퍼짐이 분할 차이보다 크다」가 **성립하지 않는다.**

    ⚠ **자세를 앞뒤로 자르지 않는다.** 앞 절반 / 뒤 절반으로 가르면 로터 위상이 한 바퀴를
      고르게 안 돌아 «분할 차이» 가 아니라 «다른 자세 집합» 을 재게 된다. 짝/홀은 격자를
      균일하게 반으로 나누므로 그 문제가 없다.
    """
    x = np.asarray(E, complex)
    if ac:
        x = x - x.mean()
    out = []
    for s in (x[0::2], x[1::2]):
        p = float(np.mean(np.abs(s) ** 2))
        out.append(10.0 * np.log10(p) if p > 0 else float("nan"))
    return out[0], out[1]


def modspec_norm(E: np.ndarray, prf: float, f_flash: float, f_tip: float,
                 dc_removed: bool = True):
    """날개끝 띠 전력의 변조 스펙트럼. ⭐띠는 **fc 로 스케일된 f_tip** 으로 잡는다.

    dc_removed : ⭐기본 참 — 정지 성분을 STFT **전에** 뺀다(머리말 참조). 거짓은 그 선택이
                 무엇을 막았는지 보이려고만 쓴다.
    """
    x = np.asarray(E, complex)
    #: ⛔⛔입력을 **먼저 거절한다**(2026-09-13(6)). 전에는 비유한 값이 들어오면 한참 뒤
    #  TypeError 로 죽었다 — 사유도 안 남기고. 판독기는 못 읽는 입력을 조용히 통과시키거나
    #  엉뚱한 자리에서 죽는 대신, **여기서** 거절해야 한다.
    #: ⛔⛔길이 관문이 8 이면 **안 된다**(2026-09-13(6) 적대 검증). 조각 길이는
    #  auto_periods(prf, f_flash) × prf / f_flash 표본이고, STFT 는 그보다 긴 입력을
    #  요구한다. 실측: 길이 8~70 은 ValueError «noverlap must be less than nperseg»,
    #  71 은 IndexError 로 죽었다. ⇒ **필요한 길이를 세어** 그보다 짧으면 거절한다.
    _nper = max(8, int(round(auto_periods(prf, f_flash) * prf / f_flash)))
    if x.size <= _nper + 1 or not np.isfinite(x).all():
        return None, None, None
    if dc_removed:
        x = x - x.mean()
    per = auto_periods(prf, f_flash)
    f, t, S, _ = flash_spec(x, prf, f_flash, per)
    m = (np.abs(f) >= 0.35 * f_tip) & (np.abs(f) <= f_tip)
    if int(m.sum()) < 2:
        #: ⛔반환값 **세 개**다 — 호출부가 셋을 받는다(2026-09-13(6) 정정. 전에는 둘이라
        #  띠가 좁은 칸에서 ValueError 로 터졌다).
        return None, None, None
    g = (S[m, :] ** 2).sum(axis=0)
    fs_g = 1.0 / float(t[1] - t[0])
    n = g.size
    Y = np.abs(np.fft.rfft((g - g.mean()) * np.hanning(n))) ** 2
    fr = np.fft.rfftfreq(n, 1.0 / fs_g)
    return fr, Y, float((S[m, :] ** 2).sum())


def write_md(out: dict, to_string: bool = False):
    """읽는 문서. ⛔여기서 새로 계산하지 않는다 — 위에서 낸 수를 그대로 옮긴다."""
    L: list[str] = []
    a = L.append
    a("# 대역 안에서 표적이 평평한가 — 5G NR 100 MHz 를 다섯 점으로")
    a("")
    a(f"> ⛔손으로 쓰지 않는다. `benchmark/read_bandflat_0913.py` 가 굽는다. "
      f"`{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`")
    a("")
    a("지금 사슬에서 파형은 **산란이 끝난 뒤 곱해지는 스칼라**다. 그래서 「한 대역 안에서 "
      "표적의 복소 반사율이 평평한가」를 한 번도 안 봤다. 0929 가 그 구멍을 메우려고 "
      "3.450 · 3.475 · 3.525 · 3.550 GHz 를 샀다(중앙 3.500 은 이미 있었다) — "
      "**자유공간과 실외 둘 다**.")
    a("")
    a("⛔OFDM 을 계산한 것이 아니다 — 다섯 점을 따로 계산해 겹쳐 본 것이다. "
      "⛔여기 레벨은 σ(dBsm)가 아니다. "
      "⛔다른 엔진과 절대 레벨을 견주지 않는다(모두 한 엔진·한 팔).")
    a("")
    cg = out["_meta"].get("control_group") or {}
    a(f"대조군 확인: 고른 팔 {out['_meta']['n_cells']} 칸이 반송파·환경 **말고는** 글자까지 "
      f"같다(문법 묶음 {cg.get('n_groups')} 개, `src/arm_grammar.py`). "
      f"읽는 대역은 {out['_meta']['band_span_mhz']} MHz 로 선언했다 — 같은 묶음에 24 GHz 팔이 "
      f"있어서, 범위를 안 적으면 대역 평탄성이 아니라 반송파 의존성이 된다.")
    a("")
    a("## 레벨 — 전체와 «움직이는 몫»을 가른다")
    a("")
    a("⛔실외의 전체 레벨은 **지면**이지 표적이 아니다.")
    a("")
    a("| 환경 | 앙각 | 움직이는 몫 퍼짐 | ⭐⭐광선 ±5 % | 되풀이 | (참고) 짝·홀 | 읽기 |")
    a("|---|---:|---:|---:|---:|---:|---|")
    for r in out["series"]:
        if r.get("n", 0) < 3:
            continue
        _rs = r.get("repeat_spread_db"); _ry = r.get("ray_budget_spread_db")
        _rep_txt = ("—" if _rs is None else
                    f"{_rs:.2e} dB ({r.get('repeat_n_runs', 0)} 판 @ "
                    f"{r.get('repeat_fcs_mhz') or '—'} MHz)")
        #: ⛔⛔2026-09-14 — 옛 판은 **중심 반송파 하나의 레벨 민감도**(_ry)의 두 배를
        #  대역 기울기의 문턱으로 썼다. 합성 반례로 양쪽이 다 뒤집혔다: 다섯 반송파를
        #  똑같이 1 dB 올려 모양 변화가 정확히 0 인 판에서 「묻힌다」가, 레벨은 그대로
        #  두고 기울기만 갈아탄 판에서 「크다」가 나왔다. 곧 그 자는 대역 «모양» 을
        #  안 보고 있었다. ⇒ 배수 비교를 지우고 **두 수를 나란히 적는다.**
        _sh = r.get("budget_shape_spread_db")
        #: ⛔2026-09-14(4) — 「(N 반송파)」의 N 이 괄호 안에 **단위 없이** 붙어 글 검사를
        #  빠져나갔다(발간물 훑기가 잡았다). 수가 글이 되는 자리를 cell() 로 옮긴다.
        _v = (f"모양 민감도 {cell(_sh, '.3f', ' dB')}"
              f"({cell(r.get('budget_shape_n_fc'), 'd', ' 반송파')})"
              if _sh is not None else
              "⚠예산을 흔들었을 때 **대역 모양**이 얼마나 움직이는지 잴 짝이 없다 — 판정 미룸")
        #: ⚠소수 두 자리면 0.015 와 0.008 이 **둘 다 0.01** 로 찍혀 산문과 어긋난다.
        a(f"| {r['env']} | {r['el_deg']:+.0f} | {r['moving_band_spread_db']:.3f} dB | "
          f"{'— (짝 없음)' if _ry is None else f'{_ry:.3f} dB ({r.get(chr(114)+chr(97)+chr(121)+chr(95)+chr(98)+chr(117)+chr(100)+chr(103)+chr(101)+chr(116)+chr(95)+chr(110)+chr(95)+chr(112)+chr(111)+chr(105)+chr(110)+chr(116)+chr(115), 0)} 점)'} | "
                    f"{_rep_txt} | "
          f"{r['within_cell_spread_ac_db']:.3f} dB | {_v} |")
    a("")
    a("⭐⭐**대조군은 광선 예산 사다리다** — 예산을 ±5 % 흔들면 광선 표본 자리가 통째로 "
      "바뀐다. 그 사다리가 **이미 원장에 있었다**(자유공간 19 묶음 · 협곡 5 앙각 × 7 점 · "
      "지면조각 2 벌) — 살 것이 아니라 읽을 것이었다.")
    a("")
    a("⭐되풀이 판(같은 설정 재실행)의 퍼짐은 표의 «되풀이» 칸에 **원정밀도로** 적혀 있다 "
      "— 2.76e−05 ~ 2.97e−08 dB 이고, 옛 「0.000 dB」는 반올림이었다. 자세 하나까지 보면 "
      "자유공간 el −30 에서 최대 2.85 % 다르다(|ΔE|/|E| 기준). ⚠되풀이가 있는 반송파는 "
      "**중앙 3.500 GHz 하나**뿐이라 대역 전체의 수렴성이 아니다. 그리고 되풀이는 **같은 "
      "광선 격자를 다시 도는 것**이라 격자 민감도를 못 덮는다 — 그래서 대조군이 아니다.")
    a("")
    a("⛔**짝·홀 자세 분할 차는 대조군이 아니다** — 이 물음에 대응하지 않기 때문이다. "
      "물음은 「반송파를 옮기면 값이 움직이나」이고, 대조군은 반송파를 **안 옮기고** 다시 "
      "잰 것(되풀이)과 광선 표본 자리를 흔든 것(예산 사다리)이다. 실제로 각 집합을 중앙 "
      "반송파에 맞춰 보면 반송파 변화 대비 최대 차는 0.0033 dB 이고, 짝수만·홀수만으로 잰 "
      "대역 퍼짐은 0.2359·0.2342 dB 로 거의 같다 — 절대 짝·홀 차가 커도 **대역 축의 비교는 "
      "그 차에 안 실린다.** 표에는 참고로만 남긴다.")
    a("")
    a("⛔**앞서 쓴 논증 하나를 거둔다**: 「진폭을 10^±6 배 해도 짝·홀 dB 차가 같으니 "
      "계통적 치우침이다」는 성립하지 않는다 — 전력비에서 공통 배율은 **정의상 소거된다**.")
    a("")
    a("⚠**실외 두 줄은 판정을 미룬다** — `envoutdoor01` 팔에 광선 예산 짝이 없다"
      "(사다리가 `outdoor01_ground` 와 협곡에만 있다). 이웃 장면의 같은 사다리는 "
      "0.303(지면조각) · 0.426~0.910 dB(협곡)이라 실외의 0.235~0.239 dB 는 묻힐 자리로 "
      "보이지만, **짝이 없으므로 여기서 단정하지 않는다.** 그 짝을 사는 것이 이 판독에 "
      "남은 가장 싼 빈자리다(8 줄 · 약 17 일꾼시간).")
    a("")
    a("## ⭐구조 관문 — 움직이는 몫에 날개 무늬가 있나")
    a("")
    a("문턱: 리듬 몫이 **그 칸의 널**을 5 %p 넘게 · 빗살 대비가 3 dB 넘게, 둘 **다**.")
    a("")
    a("⛔이 관문을 통과 못 한 줄의 대역 수는 **표적 이야기가 아니다.** "
      "⛔그렇다고 «백색잡음이다» 로도 읽지 않는다 — 두 문턱은 우리가 정한 값이고 잡음 "
      "모형과의 검정이 아니다. 반례: 잡음을 하나도 안 섞은 **501 Hz 단일 정현파**가 "
      "리듬 몫 15.38 %(널 12.65 %, 초과 2.73 %p) · 빗살 대비 **86.08 dB** 인데 AND 라서 "
      "관문은 미통과다.")
    a("")
    a("| 환경 | 앙각 | 리듬 몫 | (그 칸의 널) | 널 초과 | 빗살 대비 | "
      "날개끝 띠가 움직임에서 | 리듬 문턱 | 빗살 문턱 |")
    a("|---|---:|---:|---:|---:|---:|---:|---|---|")
    for g in out.get("structure", []):
        rs = [x for x in g["rhythm_pct"] if x is not None]
        nl = [x for x in g["rhythm_null_pct"] if x is not None]
        cb = [x for x in g["comb_db"] if x is not None]
        tp = [x for x in g["tip_band_share_of_moving_pct"] if x is not None]
        a(f"| {g['env']} | {g['el_deg']:+.0f} | {min(rs):.1f}~{max(rs):.1f} % | "
          f"{max(nl):.1f} % | {g['rhythm_over_null_pct']:+.2f} %p | "
          f"{min(cb):+.1f}~{max(cb):+.1f} dB | {min(tp):.1f}~{max(tp):.1f} % | "
          f"{'✅ 통과' if g['pass_rhythm_over_null'] else '✗ 미달'} | "
          f"{'✅ 통과' if g['pass_comb_contrast'] else '✗ 미달'} |")
    a("")
    a("## 무늬 — 주파수축을 그 칸의 날개끝 상한으로 잡고 겹친다")
    a("")
    a("⛔정지 성분은 STFT **전에** 뺐다. 안 빼면 0 Hz 의 에너지가 창 옆잎으로 날개끝 띠까지 "
      "새어, 으뜸 봉우리가 3.500 과 3.525 GHz 사이에서 계단처럼 갈아탄다 — 25 MHz 가 만든 "
      "물리로 읽으면 틀린다.")
    a("")
    a("| 환경 | 앙각 | 3.500 GHz 와의 모양 상관(최소) | 으뜸 봉우리 | 정지 성분이 띠에 넣던 몫 |")
    a("|---|---:|---:|---|---:|")
    for g in out.get("gates", []):
        pk = g["dc_removed"]["peaks_hz"]
        leak = g.get("static_leak_into_band_db")
        #: ⛔⛔2026-09-14(3) — 이 네 자리를 `reader_gate.cell()` 로 옮겼다. 글 검사만으로는
        #  「1272.9 · 759.9 · nan Hz ⚠갈린다」처럼 **꼬리가 붙은** 칸을 못 가른다(한글 두 자
        #  꼬리가 단위와 문장을 못 가르기 때문이다 — 틀을 네 번 고치고 얻은 결론이다).
        #  ⇒ 수가 글로 바뀌는 **그 자리**에 문을 둔다. 유한한 값에서는 글자가 한 자도 안 바뀐다.
        leak_txt = cell(leak, "+.1f", " dB", none="—")
        peak_txt = " · ".join(cell(x, "g") for x in pk) + " Hz"
        if len(pk) > 1:
            peak_txt += " ⚠갈린다"
        a(f"| {g['env']} | {cell(g['el_deg'], '+.0f')} | "
          f"{cell(g['shape_corr_min'], '.4f')} | {peak_txt} | {leak_txt} |")
    a("")
    a(f"원장 `{os.path.relpath(OUT_J, ROOT)}` · 칸 {out['_meta']['n_cells']}/"
      f"{out['_meta']['n_expected']} · 건너뜀 {len(out['skipped'])}")
    a("")
    txt = "\n".join(L)
    if to_string:
        return txt
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(txt)
    return None


def main() -> int:
    J = json.load(open(LED_J))
    Z = np.load(LED_N, allow_pickle=True)
    M = J["_meta"]
    ROW = {(r["engine"], float(r["el_deg"])): r for r in J["rows"]}

    out: dict = {"_meta": {
        "generator": "benchmark/read_bandflat_0913.py",
        "ledger": os.path.relpath(LED_J, ROOT),
        "ledger_rows": len(J["rows"]),
        "question_ko": "한 대역(5G NR 100 MHz) 안에서 표적의 반사와 마이크로도플러가 "
                       "반송파를 따라 움직이나 — 다섯 점을 따로 계산해 겹쳐 본다",
        "not_ofdm_ko": "⛔OFDM 을 계산한 것이 아니다. 다섯 점은 각각 단일 반송파다.",
        "level_is_not_sigma_ko": "⛔level_db 는 σ(dBsm)가 아니다 — 면적이 그 식에 없다.",
        "fcs_mhz": list(FCS_MHZ), "els_deg": list(ELS), "envs": sorted(ENVS),
        "arm_ko": "확산만(R0D0E0F1) · 15 m · 자세 8,192 · matrice4e",
        "f_flash_ko": ("날개 통과율은 **팔의 기체 꼬리표**가 정한다(src/drones.py). "
                       "이 판독기의 20 칸은 전부 기본 기체라 머리말 값과 같다."),
    }, "cells": [], "series": [], "skipped": [], "gates": []}

    # ── 1. 칸을 모으고, 쓸 자격이 있는지 먼저 건다 ──────────────────────────
    cells: dict[tuple, dict] = {}
    for env in ENVS:
        for fc in FCS_MHZ:
            arm = arm_name(env, fc)
            #: ⭐정본 예산 칸만 곡선에 쓴다(다른 예산은 ray_spread_db 가 대조군으로 읽는다).
            if parse_arm(arm).get("spp") not in (None, SPP_PRIMARY):
                continue
            for el in ELS:
                r = ROW.get((arm, el))
                if r is None:
                    out["skipped"].append({"arm": arm, "el_deg": el, "why": "원장에 없다"})
                    continue
                why = []
                if r.get("n_missing"):
                    why.append(f"자세가 덜 찼다({r['n_missing']} 개)")
                if r.get("n_zero_field"):
                    why.append(f"전계가 0 인 자세({r['n_zero_field']} 개)")
                if r.get("truncated") or r.get("n_trunc"):
                    why.append("경로가 잘렸다")
                #: ⛔⛔2026-09-14 — 「있으면 거절」이 아니라 **필드로** 본다. `one_generation`
                #  은 세대를 **깨끗이 푼** 칸에도 진단을 남긴다(창고의 두 세대 칸 4 개는 전부
                #  갈린 자세 0 · 동점 없음으로 풀렸다). 참·거짓만 보면 그런 칸까지 버린다.
                _mg = r.get("mixed_generations")
                if isinstance(_mg, dict):
                    _k = int(_mg.get("kept_conflicting_poses") or 0)
                    _t = bool(_mg.get("tie_unresolved"))
                    _d = _mg.get("n_poses_disagree")
                    if _k or _t or _d:
                        why.append(f"굽기 세대를 하나로 못 풀었다(갈린 자세 {_k} · 동점 {_t})")
                elif _mg:
                    why.append("굽기 세대가 섞였다")
                cap = r.get("max_paths_cap")
                med = r.get("npaths_median")
                if cap and med and med >= 0.9 * float(cap):
                    why.append(f"경로 수가 상한을 따라간다({med}/{cap}) — 이 축은 접는다")
                if abs(float(r.get("fc_hz", 0)) / 1e6 - fc) > 1.0:
                    why.append(f"원장 fc_hz({r.get('fc_hz')})가 이름 꼬리표와 어긋난다")
                if why:
                    out["skipped"].append({"arm": arm, "el_deg": el, "why": " · ".join(why)})
                    continue
                cells[(env, fc, el)] = r

    out["_meta"]["n_cells"] = len(cells)
    out["_meta"]["n_expected"] = len(ENVS) * len(FCS_MHZ) * len(ELS)
    #: ⭐대조군 확인 — 고른 팔들이 반송파·환경 **말고는** 글자까지 같아야 한다.
    cg = control_group_check(sorted({r["engine"] for r in cells.values()}))
    out["_meta"]["control_group"] = cg
    out["_meta"]["band_span_mhz"] = list(BAND_SPAN_MHZ)
    if not cg["one_group_only"]:
        raise SystemExit(f"⛔ 고른 팔이 한 대조군이 아니다 — 묶음 {cg['n_groups']} 개. "
                         f"반송파·환경 말고 다른 축(기체·거리·팔·표집률)이 섞였다.")
    #: ⛔범위 밖 반송파가 한 칸이라도 들어오면 멈춘다 — 문법만으로는 못 막는 자리다.
    _out_of_band = sorted({fc for (_e, fc, _l) in cells
                           if not (BAND_SPAN_MHZ[0] <= fc <= BAND_SPAN_MHZ[1])})
    if _out_of_band:
        raise SystemExit(f"⛔ 선언한 대역 {BAND_SPAN_MHZ} MHz 밖의 반송파가 섞였다: "
                         f"{_out_of_band}. 대역 평탄성이 아니라 반송파 의존성이 된다.")

    # ── 2. 칸마다 레벨·대조군·박자 ────────────────────────────────────────
    for (env, fc, el), r in sorted(cells.items()):
        E = np.asarray(Z[f"{r['engine']}/el{el_key(el)}"], complex)
        #: ⭐공통 입력 관문 — 못 쓰는 칸은 **까닭과 함께 건너뛴다**(2026-09-13(10)).
        #  ⛔전에는 NaN 이 섞이면 한참 뒤 TypeError 로 죽었고, 그 전에 **오염된 JSON 을
        #    이미 저장**해 두었다(비유한 수 260 개).
        _why = check_series(E, n_poses=r.get("n_poses"), prf=r.get("prf_hz"),
                            prf_seen=r.get("prf_hz_seen"),
                            mixed_generations=r.get("mixed_generations"))
        if _why:
            out["skipped"].append(dict(engine=r["engine"], el_deg=el,
                                       why=" · ".join(_why)))
            continue
        a, b = halves_level_db(E)                 # 전체 전력 기준
        aa, bb = halves_level_db(E, ac=True)      # ⭐움직이는 몫과 **같은 통계**
        p = float(np.mean(np.abs(E) ** 2))
        lvl = 10.0 * np.log10(p) if p > 0 else None
        #: ⭐정지(자세평균) / 움직임(나머지)을 가른다 — 실외의 level_db 는 지면이다.
        p_dc = float(np.abs(E.mean()) ** 2)
        p_ac = float(np.mean(np.abs(E - E.mean()) ** 2))
        tr = r.get("track") or {}
        out["cells"].append({
            "env": env, "fc_mhz": fc, "el_deg": el, "engine": r["engine"],
            #: ⛔⛔**두 레벨은 다른 통계다** — 섞어 인용하면 퍼짐이 달라진다.
            #    원장 level_db = 20·log10(mean|E|)   ← **크기**의 평균 (:1675)
            #    여기 level_db_here = 10·log10(mean|E|²) ← **전력**의 평균
            #  젠센 부등식으로 언제나 mean|E| ≤ sqrt(mean|E|²) 라 값도 퍼짐도 다르다.
            #  실측(자유공간 el −30 · 100 MHz): 원장 정의 4.24 dB · 전력 정의 3.62 dB.
            #  ⭐이 글의 모든 «퍼짐·기울기» 는 **전력 정의**로 낸 것이다.
            "level_db_ledger": r.get("level_db"),
            "level_db_ledger_def_ko": "20·log10(mean|E|) — 크기의 평균(원장 정의)",
            "level_db_here": None if lvl is None else round(lvl, 4),
            "level_db_here_def_ko": "10·log10(mean|E|²) — 전력의 평균(이 글의 정본)",
            "static_db": None if p_dc <= 0 else round(10.0 * np.log10(p_dc), 4),
            "moving_db": None if p_ac <= 0 else round(10.0 * np.log10(p_ac), 4),
            "moving_frac_of_total": None if p <= 0 else round(p_ac / p, 6),
            "half_even_db": round(a, 4), "half_odd_db": round(b, 4),
            "half_spread_db": round(abs(a - b), 4),
            #: ⭐움직이는 몫의 대역 퍼짐과 견줄 때는 **이쪽**을 쓴다(같은 통계).
            "half_spread_ac_db": round(abs(aa - bb), 4),
            "half_note_ko": ("짝·홀 자세 분할 차이 — 결정적 표본 분할의 민감도다. "
                             "⛔재실행 산포도 광선 격자 민감도도 신뢰구간도 아니다."),
            "f_tip_hz": r.get("f_tip_hz"), "prf_hz": r.get("prf_hz"),
            "npaths_median": r.get("npaths_median"), "seconds": r.get("seconds"),
            "beat_hz": tr.get("beat_hz"), "band_power_db": tr.get("band_power_db"),
            "h1_over_h2_db": tr.get("h1_over_h2_db"),
        })

    # ── 3. 대역을 가로지른 퍼짐 vs 칸 안 퍼짐 ──────────────────────────────
    for env in ENVS:
        for el in ELS:
            got = [(fc, c) for fc in FCS_MHZ
                   for c in out["cells"]
                   if c["env"] == env and c["el_deg"] == el and c["fc_mhz"] == fc]
            if len(got) < 3:
                out["series"].append({"env": env, "el_deg": el, "n": len(got),
                                      "why_ko": "점이 셋도 안 된다 — 기울기를 안 잰다"})
                continue
            fcs = np.array([g[0] for g in got], float)
            lv = np.array([g[1]["level_db_here"] for g in got], float)
            mv = np.array([g[1]["moving_db"] for g in got], float)
            #: ⭐통계를 **짝 맞춰** 견준다(2026-09-13(6)) — 전체 퍼짐은 전체 분할 차이와,
            #  움직이는 몫의 퍼짐은 **AC 분할 차이**와. 섞으면 결론이 뒤집힌다.
            half = float(np.median([g[1]["half_spread_db"] for g in got]))
            half_ac = float(np.median([g[1]["half_spread_ac_db"] for g in got]))
            #: ⭐**되풀이 대조군** — 이것이 재실행 재현성이다(짝·홀 차이가 아니다).
            _rs = [repeat_spread_db(g[1]["engine"], el, J["rows"], Z) for g in got]
            _rv = [x[0] for x in _rs if x[0] is not None]
            rep_spread = float(max(_rv)) if _rv else None
            #: ⛔되풀이가 **있는 반송파만** 센다(2026-09-13(10)). 옛 판은 다섯 반송파의
            #  단독 실행까지 더해 10·12·8·8 로 적었는데 실제 되풀이 수는 6·8·4·4 다.
            rep_n = sum(x[1] for x in _rs if x[0] is not None)
            rep_fcs = sorted(g[0] for g, x in zip(got, _rs) if x[0] is not None)
            #: ⭐⭐정본 대조군 — 광선 예산 ±5 % 사다리(중앙 반송파 팔에서 잰다).
            _ctr = next((g[1] for g in got if g[0] == 3500), got[0][1])
            ray_spread, ray_n = ray_spread_db(_ctr["engine"], el, J["rows"], Z, 0.05)
            #: ⭐**반송파마다** 레벨 민감도를 잰다(2026-09-14). 옛 판은 중심 하나만 불러
            #  큐 C 가 사는 비중심 예산 짝 8 줄이 통계에 아예 안 들어왔다.
            level_by_fc = {}
            for _fc, _c in got:
                _v, _n = ray_spread_db(_c["engine"], el, J["rows"], Z, 0.05)
                if _v is not None:
                    level_by_fc[int(_fc)] = {"level_spread_db": round(float(_v), 4),
                                             "n_budgets": int(_n)}
            #: ⭐⭐대역 **모양**의 예산 민감도 — 레벨 민감도와 다른 자다(함수 머리말 참조).
            shape = budget_shape_spread_db({f: c["engine"] for f, c in got}, el,
                                           J["rows"], Z, 0.05)
            band = float(lv.max() - lv.min())
            slope = float(np.polyfit(fcs / 1000.0, lv, 1)[0])          # dB per GHz
            d = np.diff(lv)
            mono = bool(np.all(d > 0) or np.all(d < 0))
            #: ⚠배수는 **참고**다 — 대조군이 자세 표집만 덮는다(머리말). 머리기사 아님.
            ratio = None if half <= 0 else round(band / half, 3)
            mv_band = float(np.ptp(np.array([g[1]["moving_db"] for g in got], float)))
            #: 날개끝 상한이 fc 에 정비례하나 — 자를 바꾼 것이 맞는지 확인
            ft = np.array([g[1]["f_tip_hz"] for g in got], float)
            ft_over_fc = ft / fcs
            out["series"].append({
                "env": env, "el_deg": el, "n": len(got),
                #: ⭐두 자를 **따로** 싣는다 — 레벨 민감도는 대역 모양의 잣대가 아니다.
                "budget_level_spread_by_fc_mhz": level_by_fc,
                "budget_shape_spread_db": (shape or {}).get("shape_spread_db"),
                "budget_shape_n_fc": (shape or {}).get("n_fc", 0),
                "budget_shape_n_budgets": (shape or {}).get("n_budgets", 0),
                "budget_shape_detail": shape,
                "budget_shape_note_ko": (
                    "D_b(f) = L_b(f) − L_b(중심) 을 예산마다 만들고 기준 예산 대비 "
                    "max_f |D_새 − D_기준| 을 잰다. 모든 반송파가 같은 양만큼 움직이면 "
                    "0 이다 — 그래서 레벨 민감도와 갈린다. ⛔짝이 없으면 null 이고, "
                    "그때는 «크다/묻힌다» 를 말하지 않는다."),
                "fc_mhz": [int(x) for x in fcs],
                "level_db": [round(float(x), 3) for x in lv],
                "band_spread_db": round(band, 3),
                #: ⭐표적에 관해 말할 수 있는 것은 이쪽이다 — 실외의 전체 레벨은 지면이다.
                "moving_db": [round(float(x), 3) for x in mv],
                "moving_band_spread_db": round(float(mv.max() - mv.min()), 3),
                "moving_slope_db_per_ghz": round(
                    float(np.polyfit(fcs / 1000.0, mv, 1)[0]), 3),
                "moving_frac_of_total": [g[1]["moving_frac_of_total"] for g in got],
                "within_cell_spread_db": round(half, 3),
                "band_spread_over_pose_sampling": ratio,
                "within_cell_spread_ac_db": round(half_ac, 3),
                "moving_spread_over_split_ac": (None if half_ac <= 0 else
                                                round(mv_band / half_ac, 3)),
                #: ⭐정본 대조군 — 되풀이 판 사이의 움직이는 몫 퍼짐.
                "repeat_spread_db": rep_spread,
                "repeat_spread_db_sci": (None if rep_spread is None
                                         else f"{rep_spread:.3e}"),
                "repeat_n_runs": rep_n,
                "repeat_fcs_mhz": rep_fcs,
                "repeat_scope_ko": ("되풀이가 있는 반송파는 repeat_fcs_mhz 뿐이다 — 나머지 "
                                    "반송파는 단독 실행이라 판 수에 안 넣는다. ⚠이 재현성은 "
                                    "**중앙 반송파 조건**의 것이고 대역 전체의 수렴성이 아니다."),
                #: ⭐⭐이것이 정본 대조군이다 — 광선 표본 자리를 실제로 흔든다.
                "ray_budget_spread_db": ray_spread,
                "ray_budget_n_points": ray_n,
                "ray_note_ko": ("광선 예산을 ±5 % 흔들었을 때 움직이는 몫의 퍼짐. "
                                "⭐되풀이가 못 덮는 **격자 민감도**를 이것이 덮는다. "
                                "짝이 없으면 null 이고, 그때는 판정을 미룬다."),
                "repeat_note_ko": ("같은 설정을 다시 돌린 판 사이의 퍼짐 — **재실행 "
                                   "재현성**이다. ⚠같은 광선 격자를 다시 도는 것이라 "
                                   "격자 민감도는 못 덮는다(그 사다리는 이 팔 계열에 없다)."),
                "control_covers_ko": ("짝·홀 자세 분할만 — 광선 격자는 못 덮는다"
                                      "(이 팔 계열에 격자 사다리 칸 0 개). "
                                      "⛔재실행 산포도 신뢰구간도 아니다."),
                "slope_db_per_ghz": round(slope, 3),
                "monotonic": mono,
                "f_tip_over_fc_ppb": [round(float(x) * 1e9, 3) for x in ft_over_fc],
                "f_tip_scales_with_fc": bool(
                    ft_over_fc.max() / ft_over_fc.min() - 1.0 < 1e-3),
                #: ⭐표적을 말하는 것은 **움직이는 몫**이고, 그것은 **AC 분할 차이**와
                #  견준다(2026-09-13(6) 정정 — 전에는 전체 전력의 분할 차이와 견주어
                #  실외 두 줄에서 결론이 거꾸로 나왔다).
                #: ⭐읽기는 **되풀이 대조군**으로 한다(2026-09-13(7) 두 번째 정정).
                #  짝·홀 분할 차이는 흔들림이 아니라 자세 집합의 계통적 치우침이라
                #  대조군이 아니다 — 그것으로 판정하면 실외 두 줄이 거꾸로 읽힌다.
                #: ⭐읽기는 **광선 예산 사다리**로 한다(2026-09-13(8) 세 번째이자 마지막 정정).
                #: ⛔⛔2026-09-14 — 여기도 같은 배수 비교였다(위 :495 와 한 쌍). 대역
                #  «모양» 의 잣대는 `budget_shape_spread_db` 이고, 레벨 민감도는 참고로만
                #  적는다. 오늘 원장에는 짝이 없으므로 네 줄 모두 «판정 미룸» 이 된다.
                "reading_ko": (
                    f"움직이는 몫이 100 MHz 를 가로질러 {mv_band:.2f} dB 움직인다 — "
                    + (f"같은 예산 변경이 **대역 모양**을 바꾼 폭은 {shape['shape_spread_db']:.3f} dB "
                       f"다({shape['n_fc']} 반송파 × 예산 {shape['n_budgets']} 벌). "
                       "⛔두 수를 나란히 읽는다 — 어느 쪽이 크면 «가른다» 로 자르는 문턱을 "
                       "우리는 아직 안 세웠다(널 분포·오류율을 안 쟀다)."
                       if shape else
                       "⚠예산을 흔들었을 때 **대역 모양**이 얼마나 움직이는지 잴 짝이 "
                       "**없다 — 판정을 미룬다**. 같은 조건에서 반송파 둘 이상 × 예산 둘 "
                       "이상이 있어야 잰다."
                       + (f" (참고: 중심 반송파의 레벨 민감도 {ray_spread:.3f} dB · {ray_n} 점 "
                          "— ⛔이것은 대역 모양의 잣대가 아니다)"
                          if ray_spread is not None else " (중심 반송파의 예산 짝도 없다)"))
                    + f" [되풀이 재현성 {('없음' if rep_spread is None else f'{rep_spread:.3f} dB')}"
                      f" · 짝·홀 분할 차 {half_ac:.3f} dB 는 흔들림이 아니라 자세 집합의 "
                      f"계통적 치우침이라 대조군이 아니다]"),
            })

    # ── 4. 겹쳐 보기 — 주파수축을 fc 로 나눈 변조 스펙트럼 ─────────────────
    for env in ENVS:
        for el in ELS:
            got = [c for c in out["cells"] if c["env"] == env and c["el_deg"] == el]
            if len(got) < 3:
                continue
            ffl0 = float(M["f_flash_hz"])
            rec = {}
            for dcr in (True, False):            # ⭐참이 정본 · 거짓은 대조로만 적는다
                curves, bpow = {}, {}
                for c in got:
                    E = np.asarray(Z[f"{c['engine']}/el{el_key(el)}"], complex)
                    fr, Y, bp = modspec_norm(E, float(c["prf_hz"]),
                                             flash_of(c["engine"], ffl0),
                                             float(c["f_tip_hz"]), dc_removed=dcr)
                    if fr is None:
                        continue
                    s = (fr > 20.0) & (fr < 1000.0)
                    if not s.any() or float(Y[s].max()) <= 0:
                        continue
                    curves[c["fc_mhz"]] = (fr[s], Y[s] / float(Y[s].max()))
                    bpow[c["fc_mhz"]] = round(10.0 * np.log10(bp), 3) if bp > 0 else None
                if len(curves) < 3:
                    continue
                ks = sorted(curves)
                ref = curves[3500] if 3500 in curves else curves[ks[0]]
                ds = []
                for k in ks:
                    fr, Y = curves[k]
                    Yi = np.interp(ref[0], fr, Y)
                    #: ⭐모양 차이는 **상관**으로 — 레벨을 이미 뺐으므로 남는 것은 무늬다.
                    cc = float(np.corrcoef(ref[1], Yi)[0, 1])
                    ds.append({"fc_mhz": k, "shape_corr_vs_3500": round(cc, 5),
                               "peak_hz": round(float(fr[int(np.argmax(Y))]), 2),
                               "band_power_db": bpow.get(k)})
                rec["dc_removed" if dcr else "dc_left_in"] = {
                    "curves": ds,
                    "shape_corr_min": round(min(d["shape_corr_vs_3500"] for d in ds), 5),
                    "peaks_hz": sorted({d["peak_hz"] for d in ds}),
                }
            if not rec.get("dc_removed"):
                continue
            prim, ctrl = rec["dc_removed"], rec.get("dc_left_in") or {}
            leak = None
            if ctrl.get("curves"):
                bp0 = [d["band_power_db"] for d in ctrl["curves"] if d["band_power_db"]]
                bp1 = [d["band_power_db"] for d in prim["curves"] if d["band_power_db"]]
                if bp0 and bp1:
                    leak = round(float(np.median(bp0) - np.median(bp1)), 2)
            out["gates"].append({
                "env": env, "el_deg": el, "n_curves": len(prim["curves"]),
                "note_ko": "날개끝 띠(0.35~1.0×f_tip) 전력의 변조 스펙트럼 — 띠를 그 칸의 "
                           "f_tip 으로 잡았으므로 반송파가 만드는 «자 바뀜» 은 이미 빠졌다. "
                           "⭐정지 성분은 STFT 전에 뺐다.",
                "dc_removed": prim, "dc_left_in": ctrl,
                "static_leak_into_band_db": leak,
                #: ⛔문장을 **틀에 박지 않는다** — 봉우리가 실제로 달라졌을 때만 그렇게 적고,
                #  뺀 뒤에도 갈리면 갈린다고 적는다(2026-09-13 에 거짓 문장 둘을 잡았다).
                "leak_note_ko": (None if leak is None else " · ".join(filter(None, [
                    f"정지 성분을 두면 이 띠의 전력이 {leak:+.1f} dB 부푼다",
                    ("그러면 으뜸 봉우리가 %s Hz 로 갈린다" % ctrl.get("peaks_hz")
                     if len(ctrl.get("peaks_hz") or []) > 1 else None),
                    ("빼면 %s Hz 하나로 모인다" % prim["peaks_hz"][0]
                     if len(prim["peaks_hz"]) == 1 else
                     "빼고도 으뜸 봉우리는 %s Hz 로 갈린다 — ⚠낮은 쪽에 엇비슷한 봉우리가 "
                     "여럿이라 «가장 큰 하나»는 흔들린다. 모양 상관으로 읽는다"
                     % prim["peaks_hz"]),
                ]))),
                "peak_stable_across_band": len(prim["peaks_hz"]) == 1,
                "shape_corr_min": prim["shape_corr_min"],
            })

    # ── 5. ⭐구조 관문 — 「움직이는 몫」에 날개 무늬가 있나 ──────────────────
    #  ⛔이 관문을 통과 못 한 줄의 대역 평탄성은 **표적 이야기가 아니다**.
    import build_md_atlas as _A                                        # noqa: E402
    ffl0 = float(M["f_flash_hz"])
    for env in ENVS:
        for el in ELS:
            got = [c for c in out["cells"] if c["env"] == env and c["el_deg"] == el]
            if not got:
                continue
            rs, nl, cb, tipfrac = [], [], [], []
            for c in got:
                E = np.asarray(Z[f"{c['engine']}/el{el_key(el)}"], complex)
                ft, prf = float(c["f_tip_hz"]), float(c["prf_hz"])
                ffl = flash_of(c["engine"], ffl0)      # ⭐그 팔의 날개 통과율
                sh, null, _above, _deg = _A.rhythm_share(E, ffl, ft, prf=prf)
                comb = _A.comb_contrast_db(E, ffl, ft, prf=prf)
                ac = E - E.mean()
                n = ac.size
                Pp = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
                fr = np.abs(np.fft.fftfreq(n, 1.0 / prf))
                tip = (fr >= 0.35 * ft) & (fr <= ft)
                tot = float(Pp.sum())
                rs.append(sh); nl.append(null); cb.append(comb)
                tipfrac.append(100.0 * float(Pp[tip].sum()) / tot if tot > 0 else None)
            rs_ok = [x for x in rs if x is not None]
            nl_ok = [x for x in nl if x is not None]
            cb_ok = [x for x in cb if x is not None]
            #: ⭐널은 칸마다 셀 수 있다 — «13» 하나를 모든 팔에 대지 않는다.
            over_null = (min(rs_ok) - max(nl_ok)) if (rs_ok and nl_ok) else None
            #: ⛔⛔두 문턱(5 %p · 3 dB)은 **우리가 정한 값**이고 검정이 아니다.
            #  2026-09-13(6) 반례: 잡음을 하나도 안 섞은 **501 Hz 단일 정현파**가
            #    리듬 몫 15.38 % · 널 12.65 %(초과 2.73 %p) · 빗살 대비 **86.08 dB**
            #  인데 AND 라서 관문은 false 다. 그 자리에서 «백색잡음과 구별되지 않는다» 는
            #  문장을 내면 **거짓**이다 — 86 dB 빗살을 가진 순수 선 하나이므로.
            #  ⇒ 문장을 «두 지표의 공동 문턱 미충족» 으로 바꾸고 두 지표를 따로 보인다.
            pass_rhythm = bool(over_null is not None and over_null > 5.0)
            pass_comb = bool(cb_ok and min(cb_ok) > 3.0)
            has = bool(pass_rhythm and pass_comb)
            #: 바닥이 정지 성분에 비례하나 — 비례하면 «표적» 으로 못 읽는다
            fr_mv = [c["moving_frac_of_total"] for c in got
                     if c["moving_frac_of_total"] is not None]
            out.setdefault("structure", []).append({
                "env": env, "el_deg": el,
                "rhythm_pct": [None if x is None else round(x, 2) for x in rs],
                "rhythm_null_pct": [None if x is None else round(x, 2) for x in nl],
                "rhythm_over_null_pct": None if over_null is None else round(over_null, 2),
                "comb_db": [None if x is None else round(x, 2) for x in cb],
                "tip_band_share_of_moving_pct": [None if x is None else round(x, 2)
                                                 for x in tipfrac],
                "moving_frac_of_total": fr_mv,
                "moving_frac_spread": (None if not fr_mv else
                                       round(max(fr_mv) - min(fr_mv), 6)),
                "blade_structure_present": has,
                "pass_rhythm_over_null": pass_rhythm,
                "pass_comb_contrast": pass_comb,
                "thresholds_ko": ("리듬 몫이 그 칸의 널을 5 %p 넘게 · 빗살 대비가 3 dB 넘게. "
                                  "⛔우리가 정한 값이고 잡음 모형과의 검정이 아니다."),
                "verdict_ko": (
                    "두 구조 지표가 **함께** 문턱을 넘는다 — 이 줄의 수를 날개 무늬가 있는 "
                    "것으로 읽는다"
                    if has else
                    "설정한 두 구조 지표의 **공동 문턱을 못 넘는다**"
                    + f"(리듬 몫 널 초과 {'통과' if pass_rhythm else '미달'}"
                    + f" · 빗살 대비 {'통과' if pass_comb else '미달'})"
                    + " — ⛔이 줄의 대역 수를 «표적이 평평하다»로 읽지 않는다. "
                      "⛔«백색잡음이다» 로도 읽지 않는다 — 이 두 요약치는 잡음 모형과의 "
                      "구별을 검정한 것이 아니다(널 분포·오류율·검정력을 안 쟀다)."),
            })

    #: ⭐⭐**다 만든 뒤 한 번에** 발간한다 — 계산이 중간에 죽으면 옛 발간물이 그대로 남고,
    #  비유한 수가 있으면 아무것도 안 바꾸고 멈춘다(src/reader_gate.publish).
    _md = write_md(out, to_string=True)
    publish({OUT_J: out, OUT_MD: _md})

    # ── 화면 ───────────────────────────────────────────────────────────────
    print("═══ 대역 안 평탄성 — 5G NR 100 MHz 다섯 점 ═══")
    print(f"  칸 {out['_meta']['n_cells']}/{out['_meta']['n_expected']} · "
          f"건너뜀 {len(out['skipped'])}")
    _cg = out["_meta"]["control_group"]
    print(f"  ⭐대조군 확인: 고른 팔이 반송파·환경 말고 전부 같다 "
          f"(문법 묶음 {_cg['n_groups']} 개 · 다른 값 {_cg['varied']})")
    for s in out["skipped"]:
        #: ⚠건너뜀 항목의 열쇠는 둘이다 — 이름을 지어 찾다 없던 칸은 `arm`,
        #  입력 관문이 거절한 칸은 `engine`. 둘 다 받는다(2026-09-13(10)).
        _n = s.get("arm") or s.get("engine") or "?"
        print(f"   ⛔ {_n[-52:]} el{s['el_deg']:+.0f} — {s['why']}")
    print()
    for s in out["series"]:
        if s.get("n", 0) < 3:
            print(f"  {s['env']:10s} el{s['el_deg']:+.0f}  {s['why_ko']}")
            continue
        print(f"  {s['env']:10s} el{s['el_deg']:+.0f}  "
              f"전체 퍼짐 {s['band_spread_db']:6.2f} dB ↔ 전체 짝·홀 차 "
              f"{s['within_cell_spread_db']:5.2f} dB · "
              f"기울기 {s['slope_db_per_ghz']:+8.2f} dB/GHz · "
              f"{'단조' if s['monotonic'] else '비단조'}")
        print(f"             전체 레벨   {s['level_db']}")
        print(f"             움직이는 몫 {s['moving_db']}  "
              f"(퍼짐 {s['moving_band_spread_db']:.2f} dB ↔ AC 짝·홀 차 "
              f"{s['within_cell_spread_ac_db']:.2f} dB · "
              f"기울기 {s['moving_slope_db_per_ghz']:+.2f} dB/GHz)")
        print(f"             움직이는 몫이 전체에서 차지하는 비 "
              f"{[f'{x:.3f}' for x in s['moving_frac_of_total']]}")
        print(f"             날개끝 상한이 fc 에 비례: {s['f_tip_scales_with_fc']}")
        print(f"             → {s['reading_ko']}")
        print(f"             (대조군 범위: {s['control_covers_ko']})")
    print()
    for g in out["gates"]:
        print(f"  무늬 {g['env']:10s} el{g['el_deg']:+.0f}  "
              f"3.500 GHz 와의 모양 상관 최소 {g['shape_corr_min']:.4f}  "
              f"({g['n_curves']} 곡선) · 으뜸 봉우리 {g['dc_removed']['peaks_hz']} Hz"
              f" {'(다섯 점이 한 자리)' if g['peak_stable_across_band'] else '(갈린다)'}")
        print("             " + " · ".join(
            f"{d['fc_mhz']}:{d['shape_corr_vs_3500']:.4f}"
            for d in g["dc_removed"]["curves"]))
        if g.get("leak_note_ko"):
            print(f"             ⚠ {g['leak_note_ko']}")
    print("\n── ⭐구조 관문 — 움직이는 몫에 날개 무늬가 있나 ──")
    for g in out.get("structure", []):
        mark = "✔" if g["blade_structure_present"] else "⛔"
        _pf = f"리듬 {'✔' if g['pass_rhythm_over_null'] else '✗'}·빗살 {'✔' if g['pass_comb_contrast'] else '✗'}"
        print(f"  {mark} {g['env']:10s} el{g['el_deg']:+.0f}  리듬몫 "
              f"{min(x for x in g['rhythm_pct'] if x is not None):.1f}~"
              f"{max(x for x in g['rhythm_pct'] if x is not None):.1f} % "
              f"(널 ~{max(x for x in g['rhythm_null_pct'] if x is not None):.1f}) · 빗살 "
              f"{min(x for x in g['comb_db'] if x is not None):+.1f}~"
              f"{max(x for x in g['comb_db'] if x is not None):+.1f} dB · "
              f"날개끝띠가 움직임의 "
              f"{min(g['tip_band_share_of_moving_pct']):.1f}~"
              f"{max(g['tip_band_share_of_moving_pct']):.1f} %  [{_pf}]")
        print(f"      {g['verdict_ko']}")
    print(f"\n  → {os.path.relpath(OUT_J, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
