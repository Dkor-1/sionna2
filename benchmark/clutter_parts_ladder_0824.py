# -*- coding: utf-8 -*-
"""clutter_parts_ladder_0824.py — 클러터를 지우면 묻힌 날개 리듬이 돌아오나
================================================================================

무엇을 묻나
-----------
8/18 덱 23 번 «The drowned blades» 가 낸 결론은 이랬다:

  · 프로펠러 **단독**은 리듬 몫 90 % 로 뛴다(백색잡음은 13 %).
  · 그런데 **정면(el 0)** 에서 그 반향은 동체 반향보다 **78 dB 아래**다.
  · ⇒ 「날개가 없는 게 아니라 **묻힌** 것이다」

그러면 다음 물음은 하나다 — **정지 클러터를 제대로 걷어내면 그 묻힌 리듬이 돌아오나?**
수동 레이다가 실제로 하는 일이 그것이다.

무엇을 하나
-----------
같은 자리에서 세 판을 나란히 놓는다:
  ① 통짜 기체 **날것**            — 동체가 날개를 덮은 상태
  ② 통짜 기체 **클러터 제거 후**   — ECA 부분공간 소거(|f| ≤ 100 Hz)
  ③ 프로펠러 **단독**             — 도달 가능한 천장

⭐앙각 사다리 0 · −30 · −60 · −90 로 낸다. **0 도가 메인**이다(동체 단독이 거기만 있고,
  8/18 이 «붕괴» 라 부른 자리가 거기다).

⛔⛔**잣대의 앙각 보정** — 이게 없으면 사다리가 거짓말을 한다.
   날개끝 주파수는 시선 방향으로 투영되므로 앙각을 탄다:
       f_tip(el) = 1101.6 / cos(30°) × cos(el)
   `switch_clutter_stft_0818.py` 의 metrics() 는 이 값을 **el −30 판(1101.6 Hz)으로 고정**해
   쓴다. 그 파일은 el −30 한 자리만 보므로 그때는 맞았다. 사다리에서는 틀린다:
       el 0 → 1272.0 Hz · el −30 → 1101.6 · el −60 → 636.0 · el −90 → **0.0**
   ⇒ el −90 에서는 「상한 위」가 «전체 스펙트럼» 이 되어 리듬 몫이 의미를 잃는다.
     `coverage_verify_0820.json` 에서 el −60·−90 칸의 comb_db 가 전부 null 인 것이 같은 이유다.
   ⇒ **이 파일은 앙각마다 f_tip 을 다시 계산하고, 잣대가 무너지는 칸을 명시적으로 표시한다.**

⛔**A4 규약을 지킨다**(0818 파일에서 물려받음) — 몫과 **절대 dB 를 함께** 낸다.
   몫만 보면 «분모가 준 것» 을 «신호가 는 것» 으로 오독한다. 클러터를 지우면 분모가 줄어들어
   리듬 «몫» 은 자동으로 오른다. 그게 신호가 돌아온 것인지 아닌지는 **절대 dB** 가 말해 준다.

⛔GPU 를 쓰지 않는다. 이미 있는 샤드만 읽는다.
산출: outputs/clutter_parts_ladder_0824.json
실행: PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/clutter_parts_ladder_0824.py
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
try:
    from thread_guard import apply as _tg
    _tg(2, verbose=False)
except Exception:                                              # noqa: BLE001
    pass

SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUT = os.path.join(ROOT, "outputs", "clutter_parts_ladder_0824.json")

_TJ = json.load(open(os.path.join(ROOT, "outputs", "switch_grid.json")))["_meta"]
PRF = 19700.0
FFL = float(_TJ["f_flash_hz"])                 # 날개 박자 — 앙각과 무관(회전수가 정한다)
FTIP_EL30 = float(_TJ["f_tip_hz"])             # 1101.6 Hz — el −30 판
HW = 8.0
FCUT = 100.0                                   # ECA 노치 — f_flash(126.7) 아래라 신호 불변

ELS = [0.0, -30.0, -60.0, -90.0]

#: (샤드 이름, 표시명, 갈래) — 갈래: whole = 통짜 · prop = 프로펠러만 · body = 동체만
ARMS = [
    ("ours_r15_n8192",                              "Our kernel",        "whole"),
    ("sionna_p4000000000_r15_n8192_d1",             "Sionna physics off", "whole"),
    ("sionna_p4000000000_onlydiffr_r15_n8192",      "diffraction only",  "whole"),
    ("sionna_p4000000000_phys_r15_n8192_d1",        "Sionna physics on", "whole"),
    ("sionna_p4000000000_partsprop_r15_n8192_d1",   "propellers only (off)", "prop"),
    ("sionna_p4000000000_phys_partsprop_r15_n8192_d1", "propellers only (on)", "prop"),
    ("sionna_p4000000000_partsnoprop_r15_n8192_d1", "body only",         "body"),
]


def f_tip(el_deg: float) -> float:
    """⭐앙각으로 보정한 날개끝 주파수. coverage_verify_0820.py:106 과 같은 식."""
    return FTIP_EL30 / np.cos(np.radians(-30.0)) * np.cos(np.radians(el_deg))


def load(arm: str, el: float):
    """그 팔·그 앙각의 샤드를 **자세 번호 제자리에 흩뿌려** 재조립한다.

    ⛔⛔샤드는 자세를 «건너뛰며» 나눠 갖는다 — 각 파일의 `idx` 가 그 자세 번호이고
      `meta[3]` 이 전체 자세 수다. 통짜는 16 샤드×512, 동체·프로펠러는 2~4 샤드×4096 으로
      **쪼갠 수가 팔마다 다르다.** 그냥 이어붙이면 (a) 시간 순서가 깨져 리듬이 사라지고
      (b) 팔끼리 자세 정렬이 어긋나 W−(B+P) 같은 뺄셈이 **다른 자세를 뺀다**.
      (2026-08-24 실측: 이어붙이기 판은 el −30 «다 끔» 리듬을 2.47 % 로 냈는데
       정본 `switch_grid.json` 은 같은 칸을 **80.5 %** 로 적고 있었다 — 그래서 잡았다.)
    반환: (E, 안 채워진 자세 수)
    """
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None, -1
    E = seen = None
    for f in fs:
        try:
            d = np.load(f)
            n = int(np.asarray(d["meta"], float)[3])
            if E is None:
                E = np.zeros(n, complex)
                seen = np.zeros(n, bool)
            ii = np.asarray(d["idx"]).astype(int)
            E[ii] = np.asarray(d["E"]).ravel()
            seen[ii] = True
        except Exception:                                      # noqa: BLE001
            pass
    if E is None:
        return None, -1
    return E, int((~seen).sum())


def cs_mean(x):
    return x - x.mean()


def cs_eca(x, fcut=FCUT):
    """⭐**도플러 0 Hz 노치** — 느린시간 DFT 에서 |f| ≤ fcut 칸을 0 으로 만든다.

    ⛔**이름이 «ECA» 인 것은 잘못이다**(2026-09-02 사용자 지적). 진짜 ECA
       (`src/passive_process.eca(surv, ref, n_taps)`)는 **기준채널**의 지연 복사본이 만드는
       부분공간에 투영해 빼는 패시브 바이스태틱 기법이다. 이 함수에는 기준채널이 없고
       부분공간도 없다 — 그냥 **직각 대역저지(노치)** 다. 이름은 옛 원장·파일명과의 호환 때문에
       남기지만, **문서·슬라이드에서는 «노치» 라고 부른다.**

    ⚠앙각 스윕의 기하는 **모노스태틱**이다(`elevation_sweep_md.py` 의 `baseline=0.0`).
      모노스태틱 CW 에서 정지 클러터를 버리는 표준이 바로 이 0 Hz 노치다 — ECA 가 아니다.

    실측(el 0, matrice4e, 8,192 자세, PRF 19.7 kHz):
      · 도플러 격자 2.40 Hz · |f| ≤ 100 Hz 는 **83 칸**(전체 8,192 칸의 1.0 %)
      · 날개 박자 126.7 Hz 는 노치 가장자리보다 26.7 Hz 위 — **신호를 안 건드린다**
      · 몸통 상수는 **100.0000 % 제거**된다
      · ⛔낙차 58 자세는 **거의 안 지워진다**(변동 몫 99.3 → 98.4 %)
    ⚠**STFT(`md_mapstyle.flash_spec`)에서는 이 노치가 «구멍» 으로 안 보인다**(2026-09-02 검증).
       창이 70 표본(3.55 ms)이라 한나 주엽이 **1,126 Hz**(= 4·PRF/70) 인데 노치는 197 Hz —
       주엽의 **17.5 %** 다. 깊은 골을 그릴 분해능이 없다. ⛔그렇다고 노치가 무의미한 것은 아니다:
       도플러 0 줄이 판 최댓값(−0.02 dB) → 최댓값 아래 **13.9 dB** 로 내려가고, 그려지는 58 ms
       구간 에너지의 **99.92 %** 가 사라진다. ⭐노치 뒤 0 Hz 에 남은 것의 **98.6 % 는 낙차**다
       (낙차를 메우면 그 줄이 36.9 dB 더 내려간다) — 클러터 잔재가 아니다.
       구멍으로 보이게 하려면 창을 512 표본(26 ms)으로 늘려야 하고, 그러면 플래시를 잃는다. — 임펄스라 대역 전체에
        퍼져 있어서 0 Hz 근처만 도려내는 노치에 안 걸린다.
    """
    X = np.fft.fft(x)
    fr = np.fft.fftfreq(x.size, 1.0 / PRF)
    X[np.abs(fr) <= fcut] = 0.0
    return np.fft.ifft(X)


def cs_mti3(x):
    y = np.zeros_like(x)
    y[2:] = x[2:] - 2.0 * x[1:-1] + x[:-2]
    return y


def metrics(x, ft: float) -> dict:
    """⭐ft 를 인자로 받는다 — 앙각마다 다르기 때문이다(0818 판은 고정이었다)."""
    ac = x - x.mean()
    n = ac.size
    P = np.abs(np.fft.fft(ac * np.hanning(n))) ** 2
    fr = np.fft.fftfreq(n, 1.0 / PRF)
    ab = np.abs(fr) >= ft
    k = np.round(np.abs(fr) / FFL)
    on = np.abs(np.abs(fr) - k * FFL) <= HW
    comb_bins, floor_bins = ab & on, ab & ~on
    ac_db = float(10 * np.log10(np.maximum((np.abs(ac) ** 2).mean(), 1e-300)))
    d = dict(ac_db=round(ac_db, 2),
             n_above_tip=int(ab.sum()),
             above_tip_pct=round(float(100 * P[ab].sum() / P.sum()), 2))
    # ⛔잣대가 성립하는지 먼저 본다 — 성립 안 하면 숫자를 내지 않는다(null 로 남긴다)
    d["metric_valid"] = bool(ft > 1.0 and comb_bins.any() and floor_bins.any()
                             and P[ab].sum() > 0)
    if d["metric_valid"]:
        d["rhythm_pct"] = round(float(100 * P[comb_bins].sum() / P[ab].sum()), 2)
        d["comb_over_floor_db"] = round(
            float(10 * np.log10(P[comb_bins].mean() / P[floor_bins].mean())), 2)
    else:
        d["rhythm_pct"] = None
        d["comb_over_floor_db"] = None
    return d


def decompose(el: float) -> dict | None:
    """⭐통짜 = 동체 + 프로펠러 인가 — 선형 중첩 검정.

    el 0 실측(2026-08-24): 성립하지 **않는다**. 잔차 W−(B+P) 의 AC 가 통짜 AC 와
    **소수점까지 같다**(−94.30 dB). 즉 통짜가 흔들리는 것의 **전부**가 교차항이고,
    프로펠러 자신의 흔들림(−146.68 dB)은 그보다 52.4 dB 아래다.
    ⇒ 정면에서 날개를 덮는 것은 정지 클러터도, 날개 자신도 아니라
      «도는 날개가 동체 반향을 가리고 흔드는 항» 이다. 그 항은 도플러가 실려 있어
      **어떤 정지-클러터 제거로도 안 지워진다**.
    """
    W, mw = load("sionna_p4000000000_r15_n8192_d1", el)
    B, mb = load("sionna_p4000000000_partsnoprop_r15_n8192_d1", el)
    P, mp = load("sionna_p4000000000_partsprop_r15_n8192_d1", el)
    if W is None or B is None or P is None:
        return None
    if not (W.size == B.size == P.size):
        return {"error_ko": f"자세 수가 다르다 W={W.size} B={B.size} P={P.size}"}
    n = W.size
    missing = {"whole": mw, "body": mb, "prop": mp}
    R = W - (B + P)

    def pw(x):
        return round(float(10 * np.log10(max((np.abs(x) ** 2).mean(), 1e-300))), 2)

    def ac(x):
        return pw(x - x.mean())
    return {
        "n": int(n), "n_missing_poses": missing,
        "total_db": {"whole": pw(W), "body": pw(B), "prop": pw(P),
                     "body_plus_prop": pw(B + P), "residual": pw(R)},
        "ac_db": {"whole": ac(W), "body": ac(B), "prop": ac(P),
                  "body_plus_prop": ac(B + P), "residual": ac(R)},
        "body_over_prop_db": round(pw(B) - pw(P), 2),
        "whole_ac_over_prop_ac_db": round(ac(W) - ac(P), 2),
        "residual_ac_equals_whole_ac": bool(abs(ac(R) - ac(W)) < 0.05),
        "verdict_ko": "통짜의 흔들림이 전부 교차항이면 정지-클러터 제거로는 못 푼다",
    }


def main() -> int:
    t0 = time.time()
    doc = {"_meta": {
        "generator": "benchmark/clutter_parts_ladder_0824.py",
        "generated_kst": time.strftime("%Y-%m-%d %H:%M:%S (UTC+9)",
                                       time.gmtime(time.time() + 9 * 3600)),
        "role_ko": "클러터를 지우면 동체에 묻힌 날개 리듬이 돌아오나 — 통짜 날것 · 통짜 제거후 · "
                   "프로펠러 단독을 앙각 사다리로 나란히 놓는다",
        "why_ko": "8/18 덱 23 번: 프로펠러 단독은 리듬 90 % 인데 el 0 에서 동체보다 78 dB 아래라 묻힌다",
        "gpu_used": False,
        "prf_hz": PRF, "f_flash_hz": FFL, "f_cut_hz": FCUT, "hw_hz": HW,
        "f_tip_by_el": {f"{e:+.0f}": round(float(f_tip(e)), 2) for e in ELS},
        "ftip_note_ko": "f_tip(el) = 1101.6/cos(30°)·cos(el). el −90 에서 0 이 되어 «상한 위» 가 "
                        "전체가 된다 ⇒ 그 칸은 metric_valid=false 로 표시하고 수치를 내지 않는다",
        "methods_ko": {"raw": "무처리", "mean": "평균 빼기(도플러 0 Hz 한 칸)",
                       "eca": f"ECA 부분공간 소거 |f| ≤ {FCUT:.0f} Hz", "mti3": "3-펄스 MTI"},
        "a4_note_ko": "몫과 절대 dB 를 함께 낸다 — 클러터를 지우면 분모가 줄어 몫은 자동으로 오른다",
    }, "cells": {}, "missing": []}

    print(f"  앙각 {ELS} · 팔 {len(ARMS)} · ECA 노치 {FCUT:.0f} Hz")
    print(f"  f_tip: " + " · ".join(f"el{e:+.0f}={f_tip(e):.1f}Hz" for e in ELS) + "\n")

    for el in ELS:
        ft = float(f_tip(el))
        print(f"── el {el:+.0f}  (f_tip {ft:.1f} Hz)" + ("  ⛔잣대 무효" if ft <= 1.0 else ""))
        for arm, name, kind in ARMS:
            E, nmiss = load(arm, el)
            if E is None:
                doc["missing"].append({"el": el, "arm": arm, "name": name})
                print(f"     {name:26s} —  샤드 없음")
                continue
            row = {"arm": arm, "kind": kind, "n_missing_poses": nmiss, "n_poses": int(E.size)}
            for meth, fn in (("raw", lambda z: z), ("mean", cs_mean),
                             ("eca", cs_eca), ("mti3", cs_mti3)):
                row[meth] = metrics(fn(E), ft)
            r0 = row["raw"]["rhythm_pct"]
            r1 = row["eca"]["rhythm_pct"]
            a0, a1 = row["raw"]["ac_db"], row["eca"]["ac_db"]
            s = (f"리듬 {r0:>6} → {r1:>6} %" if r0 is not None else "리듬   —(잣대무효)")
            print(f"     {name:26s} 자세{E.size:6d}(빈칸{nmiss:4d})  {s}   AC {a0:8.2f} → {a1:8.2f} dB")
            doc["cells"].setdefault(f"{el:+.0f}", {})[name] = row
        print()

    doc["decomposition"] = {f"{e:+.0f}": decompose(e) for e in ELS}
    for e in ELS:
        d = doc["decomposition"][f"{e:+.0f}"]
        if d:
            print(f"  분해 el{e:+.0f}: 동체/프롭 {d['body_over_prop_db']:+.1f} dB · "
                  f"통짜AC/프롭AC {d['whole_ac_over_prop_ac_db']:+.1f} dB · "
                  f"잔차AC=통짜AC {d['residual_ac_equals_whole_ac']}")
    doc["_meta"]["elapsed_s"] = round(time.time() - t0, 2)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"  saved {OUT}  ({doc['_meta']['elapsed_s']}s · 없는 칸 {len(doc['missing'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
