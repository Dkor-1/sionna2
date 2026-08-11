# -*- coding: utf-8 -*-
"""
probe_prf_effect.py — **PRF 를 올리면 그림이 달라지나**를 실제로 재본다.

사용자(2026-08-10)
> "PRF 를 35 kHz 정도로 높이면 그림이 달라지니? 확인해줄래?"

■ 이론이 말하는 것 (그래서 무엇을 반증해야 하나)
주파수 분해능은 창의 **시간 길이**가 정한다 — Δf = 1/T_win — 표본율이 아니다.
PRF 를 올리면 같은 시간 창에 표본이 더 들어갈 뿐 자는 그대로다.
  · 창 3.553 ms:  19.7 kHz → 70 표본 · 35 kHz → 124 표본, 둘 다 Δf = 281 Hz
  · 도플러축은 ±PRF/2 로 넓어지지만 f_tip 이 1.23 kHz 라 그 위는 원래 비어 있다
⇒ **«거의 안 달라진다» 가 예측이다. 이 스크립트는 그 예측을 깨려고 돌린다.**

■ 어떻게 공정하게 비교하나 (여기가 이 실험의 전부다)
PRF 를 바꾸면 «표본 수» 를 고정할지 «기록 길이» 를 고정할지 갈린다. 둘을 섞으면
PRF 효과와 기록 길이 효과가 뒤엉킨다. 그래서 **기록 길이를 고정**한다:
  n = round(T_rec · PRF)  로 자세 수를 PRF 에 비례해 늘린다.
그리고 STFT 창도 **시간으로** 고정한다(표본 수가 아니라):
  nperseg = round(T_win · PRF)
이렇게 해야 «자» 가 같고 표본율만 다른 비교가 된다.

⚠ 우리 커널만 쓴다. Sionna 팔은 몬테카를로라 PRF 를 바꾸면 난수 추첨도 같이 바뀌어
  두 효과가 섞인다(오늘 8 m·40 m 에서 그 함정을 이미 봤다).
⭐ 격자는 얼린다(오늘 규약). 조명은 평면파(기본).

읽는 것: outputs/report07_three_engines.json(_meta — 기체·자세·회전수를 물려받는다)
쓰는 것: outputs/probe_prf_effect.json · outputs/figures/probe_prf_effect.png

    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/probe_prf_effect.py --shard i --nshards N
    SIONNA2_GPU=2 PYTHONPATH=src python benchmark/probe_prf_effect.py --merge
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

os.environ.setdefault("SIONNA2_GPU", "2")

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gpu import pick                                                  # noqa: E402
pick(verbose=True)

import numpy as np                                                    # noqa: E402
from articulated_fast import FastPoser, rotor_phases                  # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT                            # noqa: E402
from rcs_sbr import C0, DEFAULT_DIV, grid_ref_from, sbr_field         # noqa: E402

TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]
OUT = f"{ROOT}/outputs/probe_prf_effect.json"
SHD = f"{ROOT}/outputs/prf_probe_shards"

T_REC = TJ["n"] / TJ["prf_hz"]        # 기록 길이 [s] — 고정
PRFS = [TJ["prf_hz"], 35000.0]        # 비교할 표본율


def _look(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()

    spec = DRONES[TJ.get("drone", "matrice4e")]
    fc = float(TJ["fc_hz"])
    u = _look(float(TJ.get("az_deg", 0.0)), float(TJ.get("el_deg", -15.0)))
    rpms = np.asarray(TJ["rpm_per_rotor"], float)

    if a.merge:
        from md_mapstyle import FLASH_HOP, FLASH_PAD, auto_periods, flash_spec
        FFL, FTIP = TJ["f_flash_hz"], TJ["f_tip_hz"]
        T_WIN = auto_periods(TJ["prf_hz"], FFL) / FFL      # 창의 **시간 길이** [s] — 고정
        out, maps = {}, {}
        for prf in PRFS:
            n = int(round(T_REC * prf))
            E = np.zeros(n, complex); secs = 0.0
            for f in sorted(glob.glob(f"{SHD}/P{prf:.0f}_*.npz")):
                z = np.load(f); E[z["idx"]] = z["E"]; secs += float(z["secs"])
            # ⭐창을 «시간» 으로 고정 — 표본 수가 아니라
            nper = max(8, int(round(T_WIN * prf)))
            per = nper / (prf / FFL)                        # 블레이드 주기 배수(검산용)
            f, t, S, _ = flash_spec(E, prf, FFL, per)
            b = (np.abs(f) >= 0.35 * FTIP) & (np.abs(f) <= 1.0 * FTIP)
            g = (S[b, :] ** 2).sum(axis=0); g = g - g.mean()
            dt = float(t[1] - t[0]); m = len(g)
            A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
            fr = np.fft.rfftfreq(64 * m, dt)
            sel = (fr >= 40) & (fr <= 400)
            i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
            y0, y1, y2 = A[i - 1], A[i], A[i + 1]; den = y0 - 2 * y1 + y2
            pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])
            An = A / A.max()

            def line(f0):
                w = (fr > f0 - 6) & (fr < f0 + 6)
                return float(20 * np.log10(An[w].max() + 1e-30)) if w.any() else -99.0

            out[f"{prf:.0f}"] = dict(
                prf_hz=prf, n_poses=n, cpu_seconds=round(secs, 1),
                window_samples=nper, window_ms=nper / prf * 1e3,
                blade_periods=nper / (prf / FFL),
                df_hz=prf / nper, unambiguous_doppler_hz=prf / 2,
                fft_size=nper * FLASH_PAD, hop_samples=FLASH_HOP,
                hop_ms=FLASH_HOP / prf * 1e3, n_time_slots=len(t),
                level_db=float(20 * np.log10(np.abs(E).mean() + 1e-30)),
                beat_hz=float(pk), beat_dev_pct=float(100 * (pk - FFL) / FFL),
                line_1x_db=line(FFL), line_2x_db=line(2 * FFL),
                margin_1x_2x_db=line(FFL) - line(2 * FFL))
            maps[f"{prf:.0f}"] = (f, t, S)
            r = out[f"{prf:.0f}"]
            print(f"  PRF {prf/1000:5.1f} kHz · 자세 {n:5d} · 창 {nper:3d}표본"
                  f"({r['window_ms']:.3f} ms, {r['blade_periods']:.3f}주기) · "
                  f"Δf {r['df_hz']:6.1f} Hz · 박자 {pk:7.2f} Hz · "
                  f"1x−2x {r['margin_1x_2x_db']:+.1f} dB", flush=True)

        # ⭐판정 — 자가 같은가, 그림이 같은가
        a0, a1 = out[f"{PRFS[0]:.0f}"], out[f"{PRFS[1]:.0f}"]
        v = dict(
            df_same=abs(a0["df_hz"] - a1["df_hz"]) < 5.0,
            window_ms_same=abs(a0["window_ms"] - a1["window_ms"]) < 0.05,
            beat_shift_hz=abs(a0["beat_hz"] - a1["beat_hz"]),
            margin_shift_db=abs(a0["margin_1x_2x_db"] - a1["margin_1x_2x_db"]),
            cost_ratio=a1["n_poses"] / a0["n_poses"],
            verdict_ko="")
        v["verdict_ko"] = (
            "⭐PRF 를 올려도 **자가 그대로**다 — 분해능은 창의 시간 길이가 정하기 때문이다. "
            f"Δf {a0['df_hz']:.0f} → {a1['df_hz']:.0f} Hz, 창 {a0['window_ms']:.3f} → "
            f"{a1['window_ms']:.3f} ms. 바뀌는 것은 도플러축 상한"
            f"(±{a0['unambiguous_doppler_hz']/1000:.1f} → ±{a1['unambiguous_doppler_hz']/1000:.1f} kHz)"
            f"인데 f_tip 이 {FTIP/1000:.2f} kHz 라 **그 위는 원래 비어 있다**. "
            f"대가는 계산량 {v['cost_ratio']:.2f} 배."
            if v["df_same"] else
            "⚠예측이 깨졌다 — 자가 달라졌다. 비교 설계를 다시 봐야 한다.")
        json.dump({"_meta": {
            "generator": "benchmark/probe_prf_effect.py",
            "question_ko": "PRF 를 35 kHz 로 올리면 그림이 달라지나",
            "design_ko": "기록 길이와 STFT 창의 **시간 길이**를 고정하고 표본율만 바꾼다. "
                         "그래야 «자» 가 같고 표본율만 다른 비교가 된다.",
            "arm_ko": "우리 커널만(얼린 격자·평면파). Sionna 는 PRF 를 바꾸면 난수 추첨도 "
                      "같이 바뀌어 두 효과가 섞이므로 뺐다.",
            "drone": spec.key, "fc_hz": fc, "f_flash_hz": FFL, "f_tip_hz": FTIP,
            "record_s": T_REC, "window_s": T_WIN},
            "by_prf": out, "verdict": v}, open(OUT, "w"), ensure_ascii=False, indent=1)
        print(f"\n{v['verdict_ko']}\n\n✅ {OUT}")
        _figure(maps, out, FTIP)
        return

    # ── 계산 ────────────────────────────────────────────────────────────────
    fp = FastPoser(spec)
    gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
    d = (C0 / fc) / DEFAULT_DIV
    os.makedirs(SHD, exist_ok=True)
    for prf in PRFS:
        n = int(round(T_REC * prf))
        ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
        gref = grid_ref_from([fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))],
                             fc, spacing=d)
        idx = np.arange(a.shard, n, a.nshards)
        E = np.zeros(idx.size, complex)
        t0 = time.time()
        for j, i in enumerate(idx):
            E[j] = sbr_field(fp.pose(ph[int(i)]), gm, fc, u, spacing=d, grid_ref=gref)
            if j and j % 256 == 0:
                el = time.time() - t0
                print(f"    PRF {prf/1000:.1f}k shard {a.shard}: {j}/{idx.size} "
                      f"{el/60:.1f}분 ETA {(idx.size-j)/j*el/60:.1f}분", flush=True)
        np.savez_compressed(f"{SHD}/P{prf:.0f}_{a.shard:02d}.npz",
                            idx=idx, E=E, secs=time.time() - t0)
        print(f"  ✅ PRF {prf/1000:.1f} kHz shard {a.shard} · {idx.size} 자세 · "
              f"{(time.time()-t0)/60:.1f}분", flush=True)


def _figure(maps, out, FTIP):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from md_mapstyle import draw
    ZOOM = (0.020, 0.080)                                  # 같은 시간 창을 본다
    fig, axes = plt.subplots(1, len(maps), figsize=(6.2 * len(maps), 4.6), sharey=True)
    for ax, (k, (f, t, S)) in zip(np.atleast_1d(axes), maps.items()):
        s = (t >= ZOOM[0]) & (t <= ZOOM[1])
        draw(ax, t[s], f, S[:, s], FTIP)
        r = out[k]
        ax.set_title(f"PRF {r['prf_hz']/1000:.1f} kHz\n"
                     f"window {r['window_samples']} samples = {r['window_ms']:.2f} ms, "
                     f"resolution {r['df_hz']:.0f} Hz", fontsize=11)
        ax.set_xlabel("Time [s]")
    np.atleast_1d(axes)[0].set_ylabel("Doppler [Hz]")
    fig.suptitle("Same window duration, different sampling rate. "
                 "The ruler does not change.", fontsize=12.5)
    fig.tight_layout()
    fig.savefig(f"{ROOT}/outputs/figures/probe_prf_effect.png",
                bbox_inches="tight", facecolor="white", dpi=200)
    print("✅ outputs/figures/probe_prf_effect.png")


if __name__ == "__main__":
    main()
