#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""팔 이름을 문법으로 되읽을 수 있나 — 상시 검사 (2026-09-13).

    CUDA_VISIBLE_DEVICES="" taskset -c 8-11 \
      /workspace/.venvs/py312/bin/python benchmark/check_arm_names.py
    …            --groups fc          한 축만 다른 대조군 묶음을 보여준다
    …            --groups prf env     여러 축도 된다

왜 있나
-------
대조군을 **즉석 정규식**으로 지어서 낸 사고가 이 레포에 다섯 건 있다(전부
`src/arm_grammar.py` 머리말에 적어 뒀다). 가장 최근 것:

  · 반송파 비교에 **다른 기체(s1000plus)와 다른 대역(24 GHz)** 이 섞여 20 dB·48 dB 폭이 났다
  · 환경 정규식이 `outdoor01_fc3550` 을 **환경 이름으로** 삼켰다

이 검사는 창고와 원장의 팔 이름을 **전부** 문법으로 되읽고, 되읽은 것을 다시 지어
원본과 글자까지 같은지 본다. 하나라도 어긋나면 exit 1 이다.

⛔⛔**되짓기가 맞다고 «뜻»이 맞는 것은 아니다** (2026-09-13(6) 적대 검증이 잡은 것).
  ⓐ 왕복은 **유일성을 안 준다.** 꼬리표 정규식만으로 왕복까지 성립하는 배정을 전수로
    세면 844 팔 중 **160 팔(19 %)** 이 둘 이상이다. 예: `…_rotoutdoor_v2_mfixbatteryi5_
    blperairframe` 은 rotor 를 `outdoor_v2` · `outdoor_v2_mfixbatteryi5` ·
    `outdoor_v2_mfixbatteryi5_blperairframe` 로 읽어도 **셋 다 왕복한다.**
    지금 옳은 것을 고르는 것은 왕복이 아니라 **KNOWN_VALUES 를 긴 것부터 맞추는 정책**이다.
  ⓑ 실제로 뜻이 틀린 적이 있다 — 로터 씨앗 `s<N>` 이 밑줄 없이 앞 꼬리표에 붙어
    `az0.7s1` 이 «방위각 0.7s1» 로 읽혔다(원장 행의 az_deg 는 0.7). 왕복은 맞고
    경고도 안 났다. 2026-09-13(6) 에 씨앗을 값에서 떼어 `rotor_seed` 로 옮겨 고쳤다.
⇒ 이 검사가 보증하는 것은 **「형태가 문법에 맞는다」까지**다. 뜻은 원장 행의 값
  (az_deg · fc_hz · prf_hz …)과 **맞대어** 확인해야 한다. 밑줄을 품는 꼬리표(환경·로터)는
  발주서가 실제로 쓴 값 표와 따로 맞춰 보고, 처음 보는 값은 ⚠로 짚는다(막지는 않는다).
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from arm_grammar import (ArmNameError, describe, key_without,   # noqa: E402
                         matched_groups, parse, unparse, warnings_for)

LED_J = os.path.join(ROOT, "outputs", "elevation_sweep_md.json")
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
#: 샤드 파일 이름 = <팔>_el<앙각>_<조각번호>.npz
SHARD_RE = re.compile(r"^(?P<arm>.+)_el(?P<el>[-+][\d.]+)_(?P<sh>\d+)\.npz$")


def arms_from_ledger() -> list[str]:
    if not os.path.exists(LED_J):
        return []
    J = json.load(open(LED_J))
    return sorted({r["engine"] for r in J["rows"]})


def arms_from_shards() -> list[str]:
    out = set()
    for p in glob.glob(os.path.join(SHD, "*.npz")):
        m = SHARD_RE.match(os.path.basename(p))
        if m:
            out.add(m.group("arm"))
    return sorted(out)


def check(arms: list[str], where: str) -> tuple[int, int, list]:
    bad, warn = [], []
    for a in arms:
        try:
            f = parse(a)                      # strict — 되짓기까지 확인한다
        except ArmNameError as e:
            bad.append((a, str(e)))
            continue
        w = warnings_for(f)
        if w:
            warn.append((a, w))
    print(f"── {where}: 팔 {len(arms)} · 되읽기+되짓기 성공 "
          f"{len(arms) - len(bad)} · ⛔실패 {len(bad)} · ⚠처음 보는 값 {len(warn)}")
    for a, e in bad[:20]:
        print(f"   ⛔ {a}\n      {e.splitlines()[0]}")
    if len(bad) > 20:
        print(f"   … 그리고 {len(bad) - 20} 개 더")
    for a, w in warn[:20]:
        print(f"   ⚠ {a}\n      {' · '.join(w)}")
    return len(bad), len(warn), bad


#: 문법이 읽은 꼬리표 ↔ 원장 행이 적어 둔 값. ⭐이것이 «뜻» 을 보는 유일한 자리다.
MEANING = {"az": ("az_deg", 1.0), "fc": ("fc_hz", 1e6), "prf": ("prf_hz", 1.0),
           "range_m": ("range_m", 1.0), "n_poses": ("n_poses", 1.0),
           "max_depth": ("max_depth", 1.0), "spp": ("spp", 1.0)}


def check_meaning() -> tuple[int, int]:
    """⭐**형태가 아니라 뜻을 본다** — 문법이 읽은 값이 원장 행의 값과 같은가.

    ⛔왕복 검사만으로는 못 잡는다. 2026-09-13(6) 실측: `az0.7s1` 은 왕복이 맞는데
      문법은 방위각을 '0.7s1' 로 읽었고 원장 행은 0.7 이었다(로터 씨앗이 붙은 것).
    """
    if not os.path.exists(LED_J):
        return 0, 0
    J = json.load(open(LED_J))
    bad, n = [], 0
    for r in J["rows"]:
        try:
            f = parse(r["engine"])
        except ArmNameError:
            continue
        for k, (col, scale) in MEANING.items():
            v, w = f.get(k), r.get(col)
            if v is None or w is None:
                continue
            n += 1
            try:
                got = float(v) * scale
            except (TypeError, ValueError):
                bad.append((r["engine"], r["el_deg"], k, v, w, "수로 안 읽힘"))
                continue
            if abs(got - float(w)) > max(1e-6, abs(float(w)) * 1e-9):
                bad.append((r["engine"], r["el_deg"], k, got, float(w), "값이 다르다"))
    print(f"── 뜻 대조: 문법값 ↔ 원장 열 {n} 쌍 · ⛔어긋남 {len(bad)}")
    for e, el, k, v, w, why in bad[:12]:
        print(f"   ⛔ {e[-56:]} el{el:+g} · {k}: 문법 {v!r} ↔ 원장 {w!r} — {why}")
    return len(bad), n


def show_groups(arms: list[str], vary: list[str]) -> None:
    """⭐«한 축만 다르고 나머지는 글자까지 같은» 묶음을 보여준다 — 대조군의 정의다."""
    g = matched_groups(arms, vary)
    sized = collections.Counter(len(v) for v in g.values())
    multi = {k: v for k, v in g.items() if len(v) > 1}
    print(f"\n── 대조군 (다른 축: {vary}) ─────────────────────────────")
    print(f"  묶음 {len(g)} 개 · 크기 분포 {dict(sorted(sized.items()))}")
    print(f"  ⭐둘 이상 모인 묶음 {len(multi)} 개")
    for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1]))[:8]:
        fixed = dict(k)
        head = " · ".join(f"{a}={b}" for a, b in sorted(fixed.items())
                          if a in ("engine", "switches", "drone", "range_m",
                                   "n_poses", "env", "prf"))
        print(f"\n   [{len(v)} 점] {head}")
        for kk in sorted(v, key=lambda t: tuple("" if x is None else str(x) for x in t)):
            print(f"      {'·'.join('없음' if x is None else str(x) for x in kk):>18s}"
                  f"  {v[kk][-58:]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", default=None,
                    help="이 축(들)만 다른 대조군 묶음을 보여준다 (예: fc · prf env)")
    ap.add_argument("--shards", action="store_true", help="창고 파일 이름도 검사한다")
    a = ap.parse_args()

    print("═══ 팔 이름 문법 검사 ═══")
    led = arms_from_ledger()
    nbad, nwarn, _ = check(led, "원장")
    total_bad = nbad

    if a.shards:
        shd = arms_from_shards()
        b2, _w2, _ = check(shd, "창고")
        total_bad += b2
        extra = sorted(set(shd) - set(led))
        if extra:
            print(f"   ⚠창고에만 있고 원장에 없는 팔 {len(extra)} 개 "
                  f"(아직 병합 안 됐거나 조각이 덜 찼다)")
            for x in extra[:8]:
                print(f"      {x[-70:]}")

    nmis, npair = check_meaning()
    total_bad += nmis

    if a.groups is not None:
        show_groups(led, a.groups or ["fc"])

    if total_bad:
        print(f"\n⛔ 되읽을 수 없는 팔 {total_bad} 개 — src/arm_grammar.py 의 꼬리표 표에 "
              f"**빌더와 같은 자리**로 넣어라(benchmark/elevation_sweep_md.py:453 이 정본).")
        return 1
    print(f"\n✅ 팔 이름 {len(led)} 개가 전부 문법으로 되읽히고 되짓기가 원본과 같다"
          f" · 문법값과 원장 열이 맞는 쌍 {npair}"
          + (f" (⚠처음 보는 값 {nwarn} 개는 사람이 볼 것)" if nwarn else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
