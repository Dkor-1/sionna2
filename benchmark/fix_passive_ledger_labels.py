# -*- coding: utf-8 -*-
"""
fix_passive_ledger_labels.py — 패시브 2채널 원장의 **라벨·문자열만** 고친다.

왜 이 파일이 생겼나
--------------------
`benchmark/passive_two_channel_md.py` 가 낸 원장(outputs/passive_two_channel.json)의
**측정값은 전부 옳은데 그 값에 붙은 이름 네 개가 틀렸다.** 리포트 11-2 를 쓰면서
적대적 감사 두 렌즈가 찾아냈고, 감사 에이전트는 원장 덮어쓰기 금지라 손대지 못했다.

⚠ 이 스크립트는 **어떤 수치도 다시 계산하지 않는다.** 라벨과 설명 문자열만 고친다.
   그래서 원장을 다시 돌릴 필요 없이 리포트가 옳은 이름을 인용할 수 있게 된다.
   고친 자리는 `_label_fixes` 에 무엇을 무엇으로 바꿨는지 남겨 추적 가능하게 한다.
⭐ 생성기(passive_two_channel_md.py)도 같은 라운드에서 함께 고쳤다 — 다음 전체 실행부터는
   이 스크립트가 할 일이 없어야 정상이다(그때는 «고칠 것 없음» 을 찍고 끝난다).

고치는 넷
---------
① `md_survival.nr_alias.what` — «5G 상시 기준신호(SSB)의 **프레임률 2 kHz**»
   ⛔ 2 kHz 는 SSB 버스트율이 아니라 **슬롯율**이다(0.5 ms 슬롯 @ 30 kHz SCS).
   실제 SSB 버스트 주기는 **20 ms = 50 Hz** 이고, 우리 저장소의 다른 그림
   (`benchmark/build_5g_fig.py`)과 10 권이 줄곧 그렇게 적어 왔다.
   ⇒ 이 실험이 실제로 돌린 것은 «슬롯율 2 kHz 로 채널을 읽는 CPI» 다. 그렇게 부른다.
   ⭐ 방향은 안 바뀐다 — 오히려 진짜 SSB(50 Hz)면 무모호 도플러가 ±25 Hz 로
     훨씬 좁아 접힘이 더 심하다. 즉 이 실험은 5G 에 **유리한 쪽으로 낙관적**이었다.

② `E2.wifi_b1.meta.mode` = "G1" — 같은 dict 의 `std` 는 "wifi" 다. WiFi 팔인데 5G 라벨이
   붙었다. 리포트가 이 필드를 안 써서 본문에는 안 샜지만 원장 자체가 틀렸다.

③ `empirical_law.design_rule` — 문자열 안에 «32.9 dB; 실측 요구치 32.8~37.2 dB» 가
   **손으로 박혀** 있다. 하우스 규약(수치는 원장에서 주입)의 유일한 구멍이었고,
   리포트가 이 문자열을 인용하는 통로로 손으로 적은 수치가 본문에 들어왔다.
   ⇒ 수치를 빼고 규칙만 남긴다. 실제 값은 리포트가 `summary` 에서 직접 읽는다.

④ `open_problems[1]` — 과거 버그·수정 과정 서사(«1차 실행에서 … 발산했고 … 다시 돌렸다»)가
   들어 있다. 리포트 톤 정책이 «과거 버그 서사 금지, 현재 상태의 신뢰성과 현재의 한계만» 이라
   충돌한다. ⇒ **현재의 한계만** 남긴다.

    python benchmark/fix_passive_ledger_labels.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = f"{ROOT}/outputs/passive_two_channel.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    J = json.load(open(LEDGER))
    fixes = []

    # ① nr_alias 라벨 — 슬롯율이지 SSB 버스트율이 아니다
    na = J.get("md_survival", {}).get("nr_alias")
    if na and "프레임률" in na.get("what", ""):
        old = na["what"]
        na["what"] = (
            f"이 팔은 5G 슬롯율 {na['prf_hz']/1000:.0f} kHz 로 채널을 읽는다"
            f"(0.5 ms 슬롯 @ 30 kHz SCS). 무모호 도플러가 ±{na['f_unamb_hz']:.0f} Hz 뿐이라 "
            f"로터 끝 {na['f_tip_hz']:.0f} Hz 가 접힌다. "
            "⚠**이것은 SSB 버스트율이 아니다** — 상시 기준신호로 쓸 수 있는 SSB 는 주기 20 ms, "
            "즉 50 Hz 이고 무모호 도플러가 ±25 Hz 로 훨씬 좁다(10 권·build_5g_fig 참조). "
            "⇒ 이 실험은 5G 에 **유리한 쪽으로 낙관적**이며, 진짜 SSB 로는 접힘이 더 심하다.")
        na["rate_is"] = "5G slot rate (0.5 ms slot at 30 kHz SCS)"
        na["ssb_burst_period_ms"] = 20.0
        na["ssb_burst_rate_hz"] = 50.0
        na["optimistic_for_5g"] = True
        fixes.append({"where": "md_survival.nr_alias.what",
                      "why": "2 kHz 는 슬롯율이지 SSB 버스트율(50 Hz)이 아니다",
                      "old": old[:200]})

    # ② WiFi 팔에 5G 라벨
    m = J.get("E2", {}).get("wifi_b1", {}).get("meta")
    if m and m.get("std") == "wifi" and m.get("mode") != "W1":
        old = m.get("mode")
        m["mode"] = "W1"
        fixes.append({"where": "E2.wifi_b1.meta.mode",
                      "why": "std=wifi 인데 5G 라벨(G1)이 붙어 있었다",
                      "old": old})

    # ③ design_rule 안의 손으로 박힌 수치
    el = J.get("empirical_law")
    if el and "여기서는" in str(el.get("design_rule", "")):
        old = el["design_rule"]
        el["design_rule"] = "손실 ≤ 3 dB ⟺ ρ_ref ≥ DTR/2"
        el["design_rule_note"] = ("수치는 이 문자열에 박지 않는다 — 실제 요구치는 "
                                  "summary[파형].ref_snr_needed_for_3db_loss 에서 읽어라. "
                                  "⚠G1 은 SINR 천장(12.0 dB) 근처라 설계 근거에서 뺀다.")
        fixes.append({"where": "empirical_law.design_rule",
                      "why": "문자열 안에 손으로 적은 수치가 있어 리포트로 새는 통로였다",
                      "old": old})

    # ④ 과거 버그 서사 제거 (리포트 톤 정책)
    ops = J.get("open_problems") or []
    for i, s in enumerate(ops):
        if "1차 실행에서" in s and "다시 돌렸다" in s:
            old = s
            cut = s.index("1차 실행에서")
            ops[i] = (s[:cut].rstrip()
                      + " ⚠그래서 G1 의 팔들은 **열잡음 한계가 아니라 잔류 한계**에서 비교된 것이고, "
                        "경험 Pfa 가 팔마다 목표에서 벗어난다 — 팔 간 Pd 를 절대값으로 읽으면 안 된다.")
            fixes.append({"where": f"open_problems[{i}]",
                          "why": "과거 버그·수정 과정 서사는 리포트 톤 정책 위반 — 현재의 한계만 남긴다",
                          "old": old[-260:]})
            break

    if not fixes:
        print("✅ 고칠 것 없음 — 원장 라벨이 이미 옳다(생성기가 고쳐진 뒤 다시 돌린 상태).")
        return

    J.setdefault("_label_fixes", []).append({
        "by": "benchmark/fix_passive_ledger_labels.py",
        "what_ko": "측정값은 건드리지 않고 **라벨·설명 문자열만** 고쳤다",
        "fixes": fixes})

    print(f"고칠 것 {len(fixes)} 건:")
    for f in fixes:
        print(f"  · {f['where']}  ← {f['why']}")
    if a.dry_run:
        print("\n(--dry-run 이라 쓰지 않았다)")
        return
    json.dump(J, open(LEDGER, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ {LEDGER}  (수치 변경 0 · 라벨만)")


if __name__ == "__main__":
    main()
