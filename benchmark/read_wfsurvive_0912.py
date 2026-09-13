#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""read_wfsurvive_0912.py — **실외 원장으로** 파형 생존을 다시 본다.

■ 왜 만들었나 (사용자 지시 2026-09-12 「가·나·다 모두」 중 (나))
  파형 생존은 이미 한 번 쟀다 — `benchmark/passive_two_channel_md.py` (2026-08-10).
  ⛔그런데 그 판은 **챔버 기하**(30×20×11 m semi-anechoic)이고, 챔버는 덱·그림·각주
    어디에도 넣지 않는다(집 규약). 그래서 그 결과는 보여 줄 수가 없다.
  ⛔또 그 판의 마이크로도플러 원장은 **모노스태틱 az0/el−15 한 칸**이다(그 원장의 가정 7).
    그 실험이 스스로 적어 둔 열린 문제 4: 「바이스태틱 마이크로도플러의 깨끗한 원장은 아직 없다」.
  ⇒ 여기서는 **실외 원장**으로, **기하에 안 매달리는 부분**만 다시 잰다:
    「망이 읽는 **프레임율**로 회전자 구조가 얼마나 살아남나」.

■ 무엇을 재나 — 두 가지를 가른다
  ① 이상적 솎아내기  프레임율로 **표본만** 뽑는다 → 접힘(aliasing)만 본다
  ② 프레임 평균 후 표본  한 프레임 동안 **평균**을 낸 뒤 표본 → 접힘 + 번짐을 함께 본다
  ⭐②가 추정기가 실제로 하는 일에 가깝다. ①과 ②의 차이가 «프레임 길이의 값» 이다.

■ ⛔이 판독기가 답하지 않는 것
  · ⛔**OFDM 을 계산하지 않는다.** 프레임율과 프레임 길이만 모형화한다 — 대역폭·부반송파·
    추정 잡음은 여기 없다. (대역폭은 0929 큐가 따로 잰다.)
  · ⛔검출 성능(Pd·Pfa)을 말하지 않는다. 그것은 패시브 사슬(passive_two_channel_md.py)의
    몫이고 그 판은 챔버 기하다.
  · ⛔「그래서 어느 파형이 낫다」로 넓히지 않는다. 잰 것은 **회전자 구조의 생존**뿐이고,
    실제 망은 대역폭·전력·안테나가 함께 다르다.
  · ⛔5G 의 2 kHz 는 **슬롯율**이다. 상시 기준신호로 쓸 수 있는 SSB 는 주기 20 ms(50 Hz)라
    무모호 도플러가 ±25 Hz 로 훨씬 좁다 — 이 판은 5G 에 **유리한 쪽으로 낙관적**이다
    (passive_two_channel.json 의 md_survival.nr_alias 가 먼저 적어 둔 단서).
  · ⛔실기 계측 대조는 0 건이고 이 판독으로도 안 생긴다.

쓰는 법:
    CUDA_VISIBLE_DEVICES="" PYTHONPATH=src:benchmark \
      /workspace/.venvs/py312/bin/python benchmark/read_wfsurvive_0912.py
"""
from __future__ import annotations

import glob
import importlib.util
import io
import json
import os
import re
import contextlib
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs/read_wfsurvive_0912.json")
MD = os.path.join(ROOT, "docs/WFSURVIVE_0912.md")

#: 망이 채널을 읽는 프레임율과 프레임 길이 — src/experiment_detection.py:98-102 의 CPI_CFG
#:   ⛔여기 값을 손으로 적지 않는다. 그 파일에서 읽어 온다.
def net_rates() -> list[dict]:
    src = open(os.path.join(ROOT, "src/experiment_detection.py"), encoding="utf-8").read()
    m = re.search(r"CPI_CFG\s*=\s*\{(.*?)\n\}", src, re.S)
    if not m:
        raise SystemExit("⛔CPI_CFG 를 못 찾았다 — src/experiment_detection.py 가 바뀌었다")
    out = []
    for line in m.group(1).splitlines():
        g = re.search(r'"(\w+)":\s*dict\(M=(\d+),\s*b=(\d+)\).*?#\s*(.*)', line)
        if not g:
            continue
        std, b, note = g.group(1), int(g.group(3)), g.group(4)
        pr = re.search(r"PRF\s*([\d.]+)\s*Hz", note)
        bl = re.search(r"\(([\d.]+)(ms|µs)\)", note)
        if not (pr and bl):
            continue
        #: ⛔⛔2026-09-13 정정 — 첫 판은 주석의 괄호 값을 **프레임 길이**로 썼다. 그것은
        #  **블록 하나**의 길이다. 한 프레임은 `b` 개 블록이다(CPI_CFG 의 b).
        #  ⛔실측: Wi-Fi 는 블록 4160 표본(52 µs) × b=9 ⇒ 프레임 0.468 ms 인데 0.052 를 썼다
        #    — **9 배 짧다**. 그래서 「Wi-Fi 는 거의 안 번진다(−0.06 dB)」가 나왔다.
        #  ⭐프레임율과 서로 검산한다: 1/프레임율 ≈ 블록 길이 × b 여야 한다. 어긋나면 멈춘다.
        blk_ms = float(bl.group(1)) * (1.0 if bl.group(2) == "ms" else 1e-3)
        frame_ms = blk_ms * b
        rate = float(pr.group(1))
        period_ms = 1000.0 / rate
        if abs(period_ms - frame_ms) > 0.05 * max(period_ms, frame_ms):
            raise SystemExit(
                f"⛔{std}: 프레임율 {rate} Hz 는 주기 {period_ms:.3f} ms 인데 "
                f"블록 {blk_ms:.3f} ms × b={b} = {frame_ms:.3f} ms 다 — 둘이 어긋난다")
        out.append(dict(std=std, frame_rate_hz=rate, frame_ms=frame_ms,
                        block_ms=blk_ms, n_blocks=b, frame_ms_from_rate=round(period_ms, 4),
                        source_note=note.strip()))
    if len(out) != 3:
        raise SystemExit(f"⛔CPI_CFG 에서 파형 3 개를 못 읽었다 — {len(out)} 개")
    return out


def prod():
    """생산 코드를 그대로 불러 쓴다 — ⛔여기서 병합을 다시 구현하지 않는다."""
    spec = importlib.util.spec_from_file_location(
        "esm", os.path.join(ROOT, "benchmark/elevation_sweep_md.py"))
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except SystemExit:
        pass
    return m


def cell_series(esm, arm: str, el: float):
    """한 칸의 복소 시계열 E(자세) 와 PRF. 미완이면 None."""
    fs = sorted(glob.glob(f"{esm.SHD}/{arm}_el{el:+g}_*.npz"))
    if not fs:
        return None
    with contextlib.redirect_stdout(io.StringIO()):
        fs, _ = esm.one_generation(fs, f"{arm}/el{el:+g}")
    E = seen = None
    prf = None
    for f in fs:
        z = np.load(f)
        ii = z["idx"].astype(int)
        meta = np.asarray(z["meta"], float)
        if E is None:
            n0 = int(meta[3])
            E = np.zeros(n0, complex)
            seen = np.zeros(n0, bool)
            prf = float(meta[4])
        E[ii] = z["E"]
        seen[ii] = True
    if not seen.all():
        return None
    return E, prf


def survive(E, prf, rates, f_tip=None):
    """정지 성분을 뺀 뒤, 프레임율로 ① 솎아내기 ② 프레임 평균 후 표본 을 둘 다 잰다.

    ⛔⛔2026-09-12 정정 — 처음에는 **스펙트럼 전체의 최강선**을 썼다가 오염됐다.
      SBR 스펙트럼 바닥이 나이퀴스트까지 차 있어(±9.8 kHz @ −30 dB, passive_two_channel.json
      의 열린 문제 4 가 먼저 적어 둔 사실) 최강선이 날개끝이 아니라 바닥을 집는다.
      ⛔실측: 날개끝 1,102 Hz 인 칸에서 전체 최강선이 9,631 Hz 로 나왔다.
    ⇒ **날개끝 띠 안**([0.5, 1.5]·f_tip)에서 잰다. 전체 최강선은 진단용으로만 함께 싣고,
      둘이 갈리면 그 칸은 바닥이 센 칸이라고 읽는다.
    """
    x = E - E.mean()                      # ⛔동체(0 도플러) 선을 뺀다 — 회전자만 본다
    ref_rms = float(np.std(x))

    def bandpow(v, fs_, lo, hi):
        """[lo,hi] Hz 안의 변동 전력의 제곱근(RMS). 띠가 없으면 None."""
        if lo is None or hi is None or v.size < 8:
            return None
        F = np.fft.fft(v)
        f = np.fft.fftfreq(v.size, 1 / fs_)
        F = F * ((np.abs(f) >= lo) & (np.abs(f) <= hi))
        y = np.fft.ifft(F)
        return float(np.std(y))

    def _spec(v, fs_):
        w = np.hanning(v.size)
        S = np.abs(np.fft.fftshift(np.fft.fft(v * w)))
        f = np.fft.fftshift(np.fft.fftfreq(v.size, 1 / fs_))
        return f, S

    def peak(v, fs_, lo=None, hi=None):
        f, S = _spec(v, fs_)
        m = np.abs(f) > 20.0              # 0 둘레의 잔류는 뺀다
        if lo is not None:
            m &= (np.abs(f) >= lo) & (np.abs(f) <= hi)
        if not m.any():
            return None
        return float(abs(f[m][int(np.argmax(S[m]))]))

    #: ⛔⛔2026-09-13 정정 — 첫 판은 띠가 창 밖이면 **중심만 접어** ±25 % 를 띠로 삼았다.
    #  그러면 **입력 띠 안의 다른 점이 접혀 들어온 자리**가 그 창 밖으로 떨어진다.
    #  ⛔반례(점검자 합성): f_tip 1,102 Hz · 입력 1,550 Hz(원래 띠 [551,1653] 안) ·
    #    프레임율 2,000 Hz ⇒ 참 접힘은 450 Hz 인데 옛 띠는 [551,1000] 이라 **그 선을 제외**하고
    #    750.9 Hz 의 딴 성분을 골랐다.
    #  ⇒ **입력 띠 전체를 촘촘히 접어** 닿는 구간의 합집합을 띠로 쓴다.
    def band_set(fs_):
        """[0.5,1.5]·f_tip 을 프레임율로 접었을 때 닿는 구간들. (없으면 None)"""
        if not f_tip or f_tip <= 0:
            return None
        ny = fs_ / 2
        lo, hi = 0.5 * f_tip, 1.5 * f_tip
        #: 입력 띠를 촘촘히 훑어 접힌 자리를 모은다 — 창 분해능보다 잘게 뜬다
        n = max(64, int(np.ceil((hi - lo) / max(ny / 256.0, 1e-9))))
        t = np.linspace(lo, hi, n)
        folded = np.abs(((t + ny) % fs_) - ny)
        lo2, hi2 = float(folded.min()), float(folded.max())
        #: 접으면 조각이 갈릴 수 있다 — 여기서는 **닿는 최소~최대**로 감싼다(보수적).
        #  ⛔감싸면 띠가 넓어져 딴 성분이 들어올 수 있다. 그래서 아래에 넓이도 함께 싣는다.
        return max(20.0, lo2), min(ny, max(hi2, lo2 + ny / 128.0)), float(folded.size)

    def band(fs_):
        b = band_set(fs_)
        return (None, None) if b is None else (b[0], b[1])

    lo0, hi0 = band(prf)
    out = dict(has_tipband=bool(lo0 is not None),
               ref_peak_hz=peak(x, prf), ref_peak_in_tipband_hz=peak(x, prf, lo0, hi0),
               tipband_lo_hz=lo0, tipband_hi_hz=hi0, f_tip_hz_used=f_tip,
               tipband_note_ko=("[0.5,1.5]·f_tip 을 프레임율로 접어 닿는 최소~최대로 감싼 띠. "
                                "⛔감싸므로 띠가 넓어질 수 있다 — 넓이를 함께 본다."),
               ref_rms=ref_rms, n_poses=int(x.size), prf_hz=prf)
    for r in rates:
        fr, blk = r["frame_rate_hz"], r["frame_ms"]
        step = prf / fr
        i = np.round(np.arange(0, x.size, step)).astype(int)
        i = i[i < x.size]
        y1 = x[i]
        L = max(1, int(round(prf * blk / 1000.0)))
        st = np.round(np.arange(0, x.size - L, step)).astype(int)
        y2 = np.array([x[s:s + L].mean() for s in st]) if st.size else y1
        lo, hi = band(fr)
        #: ⛔⛔2026-09-13(2) 적대적 검증이 찾은 것 — **이 띠는 구실을 못 한다.**
        #  접힌 상(像)이 무모호 창의 중앙 72~96 %(최대 98 %)를 덮어, «띠 안 최강선» 이
        #  272 칸 중 136~261 칸에서 **전체 최강선과 같다.** 09-12 에 띠를 넣은 까닭(스펙트럼
        #  바닥을 빼려고)이 사라진 것이다. 그리고 rms_keep_db 는 **광대역**이라 그 바닥의
        #  비간섭 평균이 수를 지배한다 — 회전자 구조의 생존이 아니다.
        #  ⇒ ⓐ 띠가 창의 몇 %인지 **함께 싣는다**(넓으면 그 칸의 띠 값은 읽지 않는다)
        #    ⓑ **우리 격자의 날개끝 띠**를 기준으로 한 생존을 따로 낸다 —
        #      우리 격자에서는 그 띠가 ±9,850 Hz 중 좁아 뜻이 선다.
        #  ⛔접힌 뒤에는 회전자 몫을 딴 것과 **못 가른다** — 그 사실 자체가 결과다.
        _frac = (None if (lo is None or hi is None) else round((hi - lo) / (fr / 2), 3))
        _ref_tb = bandpow(x, prf, lo0, hi0)          # 우리 격자의 날개끝 띠
        _post_tb = bandpow(y2, fr, lo, hi)           # 접힌 상 안
        out[r["std"]] = dict(
            frame_rate_hz=fr, frame_ms=blk, n_samples=int(y1.size),
            n_samples_frameavg=int(y2.size),
            unambiguous_hz=fr / 2, tipband_lo_hz=lo, tipband_hi_hz=hi,
            tipband_frac_of_window=_frac,
            #: ⛔띠가 창의 절반을 넘으면 «띠 안» 이라는 말이 뜻을 잃는다
            tipband_discriminates=(None if _frac is None else bool(_frac < 0.5)),
            rms_keep_tipband_db=(None if (_ref_tb is None or _post_tb is None or _ref_tb <= 0)
                                 else round(float(20 * np.log10(_post_tb / _ref_tb)), 2)),
            tip_folds=bool(f_tip and f_tip > fr / 2),
            peak_decimated_hz=peak(y1, fr),
            peak_frameavg_hz=peak(y2, fr),
            peak_frameavg_in_tipband_hz=peak(y2, fr, lo, hi),
            rms_keep_db=round(float(20 * np.log10(np.std(y2) / (ref_rms + 1e-300) + 1e-300)), 2),
            frame_samples=int(L),
        )
    return out


def main() -> int:
    esm = prod()
    rates = net_rates()
    L = json.load(open(os.path.join(ROOT, "outputs/elevation_sweep_md.json"), encoding="utf-8"))
    R = L["rows"]

    def scene(e):
        return ("canyon" if "envsionna-simple_street_canyon" in e else
                "gnd" if "envoutdoor01_ground" in e else
                "bldg" if "envoutdoor01_bldg" in e else
                "outdoor" if "envoutdoor01" in e else "free")

    #: ⭐실외 계열과 그 빈 하늘 짝만 본다 — 챔버는 아예 손대지 않는다
    want = [r for r in R
            if r["engine"].startswith("sionna") and r.get("n_missing") == 0
            and r.get("n_poses") == 8192 and r.get("spp") == 4e9
            and r["engine"].endswith("_d2") and "_r15_" in r["engine"]
            and not re.search(r"_(ps|fs|bs|az|rot|shell|S0|rep|div|onlyrefr|phys|alt|fc)[\d._]",
                              r["engine"])
            and not any(d in r["engine"] for d in
                        ("mini5pro", "mavic4pro", "phantom4", "s1000plus"))]
    rows = []
    for r in sorted(want, key=lambda r: (scene(r["engine"]), r["engine"], r["el_deg"])):
        got = cell_series(esm, r["engine"], r["el_deg"])
        if got is None:
            continue
        E, prf = got
        s = survive(E, prf, rates, f_tip=r.get("f_tip_hz"))
        arm = re.search(r"_sw(R\dD\dE\dF\d)", r["engine"])
        rows.append(dict(engine=r["engine"], scene=scene(r["engine"]), el_deg=r["el_deg"],
                         arm=arm.group(1) if arm else None,
                         f_tip_hz=r.get("f_tip_hz"), **s))
        print(f"  {scene(r['engine']):8s} el{r['el_deg']:+4g} {arm.group(1) if arm else '?':10s}"
              f" f_tip {r.get('f_tip_hz', 0):7.1f} · 띠 안 최강선 "
              f"{(s.get('ref_peak_in_tipband_hz') or float('nan')):7.1f}"
              f" · NR 띠안 {(s['nr'].get('peak_frameavg_in_tipband_hz') or float('nan')):7.1f}"
              f" ({s['nr']['rms_keep_db']:+5.1f} dB) · 접힘 {s['nr']['tip_folds']}",
              flush=True)

    out = dict(_meta=dict(
        generator="benchmark/read_wfsurvive_0912.py",
        made_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        question_ko="망이 읽는 프레임율로 회전자 구조가 얼마나 살아남나 — **실외 원장으로**",
        why_ko=("파형 생존은 passive_two_channel_md.py 가 2026-08-10 에 이미 쟀지만 그 판은 "
                "챔버 기하라 보여 줄 수 없고, 마이크로도플러 원장도 모노스태틱 한 칸이다. "
                "여기서는 실외 원장으로, 기하에 안 매달리는 부분만 다시 잰다."),
        rates=rates,
        limits_ko=[
            "⛔OFDM 을 계산하지 않는다 — 프레임율과 프레임 길이만 모형화한다. 대역폭·부반송파·"
            "추정 잡음은 여기 없다(대역폭은 0929 큐가 따로 잰다).",
            "⛔검출 성능(Pd·Pfa)을 말하지 않는다 — 그것은 패시브 사슬의 몫이고 그 판은 챔버다.",
            "⛔어느 파형이 «낫다» 로 넓히지 않는다. 잰 것은 회전자 구조의 생존뿐이고 실제 망은 "
            "대역폭·전력·안테나가 함께 다르다.",
            "⛔5G 의 2 kHz 는 **슬롯율**이다. 상시 기준신호로 쓸 수 있는 SSB 는 주기 20 ms(50 Hz)라 "
            "무모호 도플러가 ±25 Hz 로 훨씬 좁다 — 이 판은 5G 에 유리한 쪽으로 낙관적이다.",
            "⛔정지 성분(0 도플러 동체선)을 빼고 잰다. 그것을 남기면 생존 수가 동체에 지배된다.",
            "⛔⛔rms_keep_db 는 **광대역**이다 — SBR 스펙트럼 바닥이 나이퀴스트까지 차 있어 "
            "그 바닥의 비간섭 평균이 이 수를 지배한다. 회전자 구조의 생존으로 읽지 마라. "
            "그쪽은 rms_keep_tipband_db(우리 격자의 날개끝 띠를 기준으로 한 것)를 본다.",
            "⛔⛔접힌 상이 무모호 창의 72~96 %(최대 98 %)를 덮는다 — «띠 안» 이 창 전체와 "
            "사실상 같다. tipband_frac_of_window 가 0.5 를 넘는 칸의 «띠 안» 값은 읽지 않는다"
            "(tipband_discriminates=false). ⭐접힌 뒤에는 회전자 몫을 딴 것과 **못 가른다** — "
            "그 사실 자체가 이 판독의 결과다.",
            "⛔f_tip 이 0 인 칸(직하방)은 띠가 없다 — has_tipband=false 이고 띠 값이 전부 null 이다.",
            "⛔실기 계측 대조는 0 건이고 이 판독으로도 안 생긴다.",
        ]), rows=rows)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    render(out)
    print(f"\n✅ {os.path.relpath(OUT, ROOT)} · {os.path.relpath(MD, ROOT)}  ({len(rows)} 칸)")
    return 0


def render(o) -> None:
    rows, m = o["rows"], o["_meta"]
    lines = ["# 망 프레임율에서 회전자 구조가 얼마나 살아남나 — 실외 원장",
             "",
             f"> ⛔손으로 쓰지 않는다. `{m['generator']}` 가 굽는다. `{m['made_utc']}`",
             "", m["why_ko"], "",
             "## 망이 읽는 프레임율 (src/experiment_detection.py 의 CPI_CFG 에서 읽어 온다)",
             "", "| 파형 | 프레임율 | 무모호 창 | 프레임 길이 |", "|---|---:|---:|---:|"]
    for r in m["rates"]:
        lines.append(f"| {r['std']} | {r['frame_rate_hz']:.0f} Hz | "
                     f"±{r['frame_rate_hz']/2:.0f} Hz | {r['frame_ms']:g} ms |")
    lines += ["", "## 칸마다", "",
              "| 장면 | 앙각 | 팔 | 날개끝 | 띠 안 최강선 | 전체 최강선 | NR | Wi-Fi | LTE |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        def c(k):
            v = r.get(k) or {}
            p = v.get("peak_frameavg_in_tipband_hz")
            return (f"{p:.0f} ({v.get('rms_keep_db', 0):+.1f})" if p is not None
                    else f"— ({v.get('rms_keep_db', 0):+.1f})")
        lines.append(f"| {r['scene']} | {r['el_deg']:+g} | {r['arm']} | "
                     f"{(r.get('f_tip_hz') or 0):.0f} | "
                     f"{(r.get('ref_peak_in_tipband_hz') or float('nan')):.0f} | "
                     f"{(r.get('ref_peak_hz') or 0):.0f} | "
                     f"{c('nr')} | {c('wifi')} | {c('lte')} |")
    lines += ["", "값은 «프레임 평균 뒤 가장 센 선 [Hz] (남은 변동 [dB])» 다.", "",
              "## ⛔이 판독이 말하지 않는 것", ""]
    lines += [f"- {x}" for x in m["limits_ko"]]
    lines.append("")
    with open(MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
