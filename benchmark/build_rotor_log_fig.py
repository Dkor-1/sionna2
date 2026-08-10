# -*- coding: utf-8 -*-
"""
build_rotor_log_fig.py — ⭐로터 산포·흔들림의 «근거 그림»: 공개 실기체 비행로그 실측.

왜 이 그림인가 (2026-08-10)
---------------------------
report07 그림 11(실내-이상 vs 야외 프리셋)의 야외 값(산포 ±2 %, 흔들림 2.5 % @ 1 Hz)을
본문이 한때 «문헌 앵커»라고 불렀다. 정확하지 않다 — 근거는 **논문이 아니라 공개된
실기체 비행로그 3종**이고(outputs/rotor_rpm_web_anchor.json), 그 수치는 우리가 그
로그를 직접 열어서 잰 값이다. 그래서 «논문 그림을 인용»하는 대신 **그 로그에서 잰
그림을 우리가 그린다**. 사용자가 자기 눈으로 확인할 수 있는 형태가 이쪽이다.

세 원천 (자세한 URL·주의사항은 outputs/rotor_rpm_web_anchor.json):
  ① NeuroBEM (UZH RPG)          실내 레이싱 쿼드 · 모터별 **실측 rpm** 400 Hz
  ② PX4 Flight Review CODEV V3  야외 상용 대형 쿼드 · esc_status **실측 rpm** 4 Hz
  ③ DJI Phantom 3 DAT (DROP)    야외 · 진짜 DJI · 모터 **PWM 명령** 50 Hz (rpm 아님)

읽는 것: 원자료 디렉터리(SIONNA2_ROTORLOG_DIR, 기본은 세션 스크래치패드)
         └ neurobem/processed_data/*.csv · ulogs/*.ulg · dji/*.DAT
         원자료가 없으면 outputs/rotor_log_traces.npz 캐시로 그림만 다시 그린다.
         프리셋 값은 outputs/report07_hover_long{,_outdoor}.json 에서 읽는다.
쓰는 것: outputs/figures/report07_f13.{png,pdf}
         outputs/rotor_log_traces.json  (창 목록·모터별 통계·접근 성공/실패)
         outputs/rotor_log_traces.npz   (그림 재현용 표시 구간 시계열만)

의존성: pyulog (②용). 없으면 `pip install pyulog` 하거나
        SIONNA2_PYLIBS=<pyulog 설치 경로> 로 알려 준다. 실패해도 나머지는 진행한다.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import textwrap
from glob import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get(
    "SIONNA2_ROTORLOG_DIR",
    "/tmp/claude-1015/-home-yunjung-workspace/"
    "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad",
)
if os.environ.get("SIONNA2_PYLIBS"):
    sys.path.insert(0, os.environ["SIONNA2_PYLIBS"])

# ── 호버 창·측정 규약 (세 원천 공통) ────────────────────────────────────────
V_MAX = 0.30          # m/s, 호버 판정 속도
WOBBLE_BAND = (0.3, 5.0)   # Hz, 흔들림 대역 (fs 가 낮으면 0.45*fs 로 잘림)
MIN_DUR = {"neurobem": 1.2, "px4": 3.0, "dji": 3.0}   # s (원천별 가용 길이)


# ── 공통 측정기 ─────────────────────────────────────────────────────────────
def band_amp(x, fs, lo, hi):
    """상대 신호 x 의 [lo,hi] Hz 성분 → 등가 사인 진폭(rms*√2) 와 PSD 피크 주파수."""
    n = len(x)
    x = x - x.mean()
    f = np.fft.rfftfreq(n, 1 / fs)
    X = np.fft.rfft(x)
    m = (f >= lo) & (f <= min(hi, 0.45 * fs))
    if not m.any():
        return np.nan, np.nan
    xb = np.fft.irfft(np.where(m, X, 0), n)
    p = np.abs(X) ** 2
    return xb.std() * np.sqrt(2), float(f[m][np.argmax(p[m])])


def window_stats(seg, fs, meta):
    """seg: (n, n_motor) 절대 rpm 또는 PWM. 정적 산포 + 모터별 흔들림."""
    per = seg.mean(0)
    mean_all = float(seg.mean())
    dev = (per - mean_all) / mean_all
    amps, pks = [], []
    for k in range(seg.shape[1]):
        a, p = band_amp(seg[:, k] / per[k] - 1.0, fs, *WOBBLE_BAND)
        amps.append(a)
        pks.append(p)
    out = dict(meta)
    out.update(
        n_motor=int(seg.shape[1]), fs_hz=round(float(fs), 2),
        level_mean=round(mean_all, 1),
        static_dev_pct=[round(100 * x, 3) for x in dev],
        static_std_pct=round(100 * float(dev.std()), 3),
        static_maxabs_pct=round(100 * float(np.abs(dev).max()), 3),
        wobble_amp_pct=[round(100 * a, 3) for a in amps],
        wobble_peak_hz=[round(p, 2) for p in pks],
    )
    return out


def runs(ok, fs, min_dur):
    idx = np.flatnonzero(np.diff(np.r_[0, ok.astype(int), 0])).reshape(-1, 2)
    return [(s, e) for s, e in idx if (e - s) / fs >= min_dur]


# ── ① NeuroBEM: 모터별 실측 회전수 [rad/s] @ 400 Hz ─────────────────────────
W_MAX_NB = 0.35   # rad/s, 자세각속도 상한 (실내 레이싱기라 «호버»가 짧다)


def load_neurobem():
    files = sorted(glob(f"{RAW}/neurobem/processed_data/*.csv"))
    if not files:
        return [], {}, "no CSV under neurobem/processed_data"
    wins, traces = [], {}
    for path in files:
        d = np.genfromtxt(path, delimiter=",", names=True, deletechars="")
        t = d["t"]
        v = np.sqrt(d["vel_x"] ** 2 + d["vel_y"] ** 2 + d["vel_z"] ** 2)
        w = np.sqrt(d["ang_vel_x"] ** 2 + d["ang_vel_y"] ** 2 + d["ang_vel_z"] ** 2)
        mot = np.stack([d[f"mot_{k}"] for k in (1, 2, 3, 4)], 1) * 60 / (2 * np.pi)
        fs = 1.0 / float(np.median(np.diff(t)))
        for s, e in runs((v < V_MAX) & (w < W_MAX_NB), fs, MIN_DUR["neurobem"]):
            wins.append(window_stats(mot[s:e], fs, dict(
                file=os.path.basename(path), t0=round(float(t[s]), 2),
                dur_s=round((e - s) / fs, 2),
                v_mean=round(float(v[s:e].mean()), 3))))
            traces[f"{os.path.basename(path)}@{t[s]:.2f}"] = (
                t[s:e] - t[s], mot[s:e])
    return wins, traces, None


# ── ② PX4 ulog: esc_status.esc_rpm (CAN ESC 실측) @ 4 Hz ───────────────────
def load_px4():
    files = sorted(glob(f"{RAW}/ulogs/*.ulg"))
    if not files:
        return [], {}, "no .ulg under ulogs/"
    try:
        from pyulog import ULog
    except ImportError:
        return [], {}, "pyulog not importable (pip install pyulog, or SIONNA2_PYLIBS=...)"
    wins, traces, skipped = [], {}, 0
    for path in files:
        try:
            u = ULog(path, message_name_filter_list=[
                "esc_status", "vehicle_local_position"])
            esc = next(d for d in u.data_list if d.name == "esc_status")
            lp = next(d for d in u.data_list if d.name == "vehicle_local_position")
        except (StopIteration, Exception):       # esc_status 없는 로그가 대부분
            skipped += 1
            continue
        te = esc.data["timestamp"] / 1e6
        nm = int(esc.data["esc_count"].max())
        rpm = np.stack([esc.data[f"esc[{k}].esc_rpm"] for k in range(nm)],
                       1).astype(float)
        tl = lp.data["timestamp"] / 1e6
        v = np.sqrt(lp.data["vx"] ** 2 + lp.data["vy"] ** 2 + lp.data["vz"] ** 2)
        fs = 1.0 / float(np.median(np.diff(te)))
        v_on = np.interp(te, tl, v)
        for s, e in runs((v_on < V_MAX) & (rpm.min(1) > 500), fs, MIN_DUR["px4"]):
            wins.append(window_stats(rpm[s:e], fs, dict(
                file=os.path.basename(path), t0=round(float(te[s]), 1),
                dur_s=round((e - s) / fs, 1),
                v_mean=round(float(v_on[s:e].mean()), 3))))
            traces[f"{os.path.basename(path)[:8]}@{te[s]:.1f}"] = (
                te[s:e] - te[s], rpm[s:e])
    return wins, traces, (f"{skipped}/{len(files)} ulog 에 esc_status 없음"
                          if skipped else None)


# ── ③ DJI Phantom 3 DAT: MotorCtrl(type 54) PWM 명령 [%] @ 50 Hz ───────────
# 프레임 규격은 DatCon 소스(BudWalkerJava/DatCon)를 그대로 이식:
#   0x55, len(u8), 0, hdrchk, type(u16 LE), tick(u32 LE), payload, chksum(u16)
#   payload 는 (tick % 256) XOR, clockRate 600 tick/s, startOfRecords=128
#   type 54 : pwm1..4 = u16/100 [%] @ payload 19,21,23,25
#   type  5 : velN/E/D = f32/100 [m/s] @ payload 20,24,28
PWM_HOVER_MIN = 55.0   # %, 지면 스핀업·착륙을 걸러내는 «진짜 호버» 하한


def _parse_dat(path):
    buf = open(path, "rb").read()
    n, pos = len(buf), 128
    pwm, gps = [], []
    while pos + 12 < n:
        if buf[pos] != 0x55:
            nxt = buf.find(b"\x55", pos + 1)
            if nxt < 0:
                break
            pos = nxt
            continue
        length = buf[pos + 1]
        if length < 12 or pos + length > n:
            pos += 1
            continue
        if pos + length < n and buf[pos + length] != 0x55:
            pos += 1
            continue
        rtype = int.from_bytes(buf[pos + 4:pos + 6], "little")
        tick = int.from_bytes(buf[pos + 6:pos + 10], "little")
        pl = bytes(b ^ (tick % 256) for b in buf[pos + 10:pos + length - 2])
        if rtype == 54 and len(pl) >= 27:
            pwm.append((tick,) + tuple(x / 100.0
                                       for x in struct.unpack_from("<4H", pl, 19)))
        elif rtype == 5 and len(pl) >= 32:
            vn, ve, vd = struct.unpack_from("<fff", pl, 20)
            gps.append((tick, vn / 100.0, ve / 100.0, vd / 100.0))
        pos += length
    return np.array(pwm, float), np.array(gps, float)


def load_dji():
    files = sorted(glob(f"{RAW}/dji/*.DAT"))
    if not files:
        return [], {}, "no .DAT under dji/"
    wins, traces = [], {}
    for path in files:
        pwm, gps = _parse_dat(path)
        if len(pwm) < 100 or len(gps) < 10:
            continue
        tp, tg = pwm[:, 0] / 600.0, gps[:, 0] / 600.0
        fs = 1.0 / float(np.median(np.diff(tp)))
        v = np.interp(tp, tg, np.linalg.norm(gps[:, 1:4], axis=1))
        ok = (v < V_MAX) & (pwm[:, 1:5].mean(1) > PWM_HOVER_MIN)
        for s, e in runs(ok, fs, MIN_DUR["dji"]):
            wins.append(window_stats(pwm[s:e, 1:5], fs, dict(
                file=os.path.basename(path), t0=round(float(tp[s]), 1),
                dur_s=round((e - s) / fs, 1),
                v_mean=round(float(v[s:e].mean()), 3))))
            traces[f"{os.path.basename(path)}@{tp[s]:.1f}"] = (
                tp[s:e] - tp[s], pwm[s:e, 1:5])
    return wins, traces, None


# ── 데이터셋 정의 ───────────────────────────────────────────────────────────
DATASETS = [
    dict(key="neurobem", loader=load_neurobem,
         short="NeuroBEM", venue="indoor", unit="rpm",
         title="NeuroBEM racing quad — indoor, measured rpm",
         ylabel="Rotor speed [rpm]",
         xtick="NeuroBEM\nindoor, rpm",
         # 표시 창: 조용한(과도 없는) 창 중 정적 산포가 중앙값에 가장 가까운 것
         pick=lambda w: (np.median(w["wobble_amp_pct"]) < 2.0, -w["dur_s"])),
    dict(key="px4", loader=load_px4,
         short="PX4 CODEV AQUILA V3", venue="outdoor", unit="rpm",
         title="PX4 CODEV AQUILA V3 — outdoor, measured rpm",
         ylabel="Rotor speed [rpm]",
         xtick="PX4 CODEV\noutdoor, rpm",
         pick=lambda w: (True, -w["dur_s"])),
    dict(key="dji", loader=load_dji,
         short="DJI Phantom 3", venue="outdoor", unit="pwm",
         title="DJI Phantom 3 — outdoor, motor PWM command (not rpm)",
         ylabel="Motor command [% PWM]",
         xtick="DJI Phantom 3\noutdoor, PWM",
         pick=lambda w: (True, -w["dur_s"])),
]

MOTOR_COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd",
                "#ff7f0e", "#8c564b", "#17becf", "#7f7f7f"]
BOX_FACE = {"indoor": "#cfe2f3", "outdoor": "#fbe0d0"}


# ── 수집 ────────────────────────────────────────────────────────────────────
def collect():
    data, notes = {}, {}
    for ds in DATASETS:
        wins, traces, note = ds["loader"]()
        data[ds["key"]] = dict(windows=wins, traces=traces)
        notes[ds["key"]] = note
        print(f"  {ds['key']:9s}: {len(wins):3d} hover windows"
              + (f"   [{note}]" if note else ""))
    return data, notes


def pick_display(ds, wins):
    """표시할 대표 창 = pick 규칙 상위 + 정적 산포가 그 원천 중앙값에 가장 가까운 창."""
    med = float(np.median([w["static_std_pct"] for w in wins]))
    cand = sorted(wins, key=ds["pick"], reverse=True)
    cand = [w for w in cand if ds["pick"](w)[0] == cand[0] and True] or cand
    keep = [w for w in wins if ds["pick"](w)[0]] or wins
    return min(keep, key=lambda w: abs(w["static_std_pct"] - med)), med


# ── 그림 ────────────────────────────────────────────────────────────────────
FS = 9.5
plt.rcParams.update({
    "font.size": FS, "axes.labelsize": FS, "axes.titlesize": FS,
    "xtick.labelsize": FS - 1, "ytick.labelsize": FS - 1, "legend.fontsize": FS - 1.5,
    "axes.linewidth": 0.9, "figure.dpi": 200, "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
})

CAPTION = (
    "Rotor-speed spread and wobble measured directly from three public real-flight "
    "logs, not quoted from a paper. Top: one hover window per log, all motors "
    "overlaid. Bottom: per-window statistics of every hover window found in each "
    "log, against the two presets used in this report. The DJI log records the motor "
    "PWM command, not measured rpm, so its percentages are a control-loop proxy and "
    "are not directly comparable to the two rpm columns."
)


def build(data, notes, presets):
    fig = plt.figure(figsize=(10.6, 6.6))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.0, 1.15], hspace=0.46, wspace=1.05,
                          left=0.062, right=0.985, bottom=0.175, top=0.915)

    picks = {}
    for i, ds in enumerate(DATASETS):
        ax = fig.add_subplot(gs[0, 2 * i:2 * i + 2])
        wins = data[ds["key"]]["windows"]
        if not wins:
            ax.text(0.5, 0.5, "data unavailable", ha="center", va="center",
                    transform=ax.transAxes, color="0.45")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(ds["title"], fontsize=FS - 0.5)
            continue
        w, med = pick_display(ds, wins)
        key = [k for k in data[ds["key"]]["traces"]
               if k.endswith(f"@{w['t0']:.2f}") or k.endswith(f"@{w['t0']:.1f}")]
        key = [k for k in key if k.split("@")[0][:8] == w["file"][:8]] or key
        t, y = data[ds["key"]]["traces"][key[0]]
        picks[ds["key"]] = (w, med, key[0])
        for k in range(y.shape[1]):
            ax.plot(t, y[:, k], lw=0.85, color=MOTOR_COLORS[k],
                    label=f"rotor {k + 1}")
        ax.set_xlim(0, t[-1])
        ax.set_xlabel("Time [s]")
        ax.set_ylabel(ds["ylabel"])
        ax.set_title(ds["title"], fontsize=FS - 0.5)
        ax.grid(alpha=0.25, lw=0.5)
        if i == 0:
            ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(1.72, 1.34),
                      framealpha=0.0, columnspacing=1.4, handlelength=1.6)

    panels = [
        ("Static spread across motors", "static_std_pct",
         "Spread [% of mean, std across motors]", "static_spread"),
        ("Wobble amplitude per motor", "wobble_amp_pct",
         "Wobble [% of mean, equivalent sine]", "wobble_amp"),
    ]
    for j, (title, field, ylab, pkey) in enumerate(panels):
        ax = fig.add_subplot(gs[1, 3 * j:3 * j + 3])
        vals, faces = [], []
        for ds in DATASETS:
            wins = data[ds["key"]]["windows"]
            if field == "static_std_pct":
                v = [w[field] for w in wins]
            else:
                v = [x for w in wins for x in w[field] if np.isfinite(x)]
            vals.append(np.asarray(v, float))
            faces.append(BOX_FACE[ds["venue"]])
        pos = np.arange(1, len(DATASETS) + 1)
        good = [k for k, v in enumerate(vals) if len(v)]
        if good:
            bp = ax.boxplot([vals[k] for k in good], positions=pos[good],
                            widths=0.46, showfliers=False, patch_artist=True,
                            medianprops=dict(color="black", lw=1.4),
                            whiskerprops=dict(lw=0.9), capprops=dict(lw=0.9),
                            boxprops=dict(lw=0.9))
            for b, k in zip(bp["boxes"], good):
                b.set_facecolor(faces[k])
                b.set_alpha(0.85)
                if DATASETS[k]["unit"] == "pwm":
                    b.set_hatch("//")
        rng = np.random.default_rng(7)
        for k, v in enumerate(vals):
            if not len(v):
                continue
            ax.plot(pos[k] + rng.uniform(-0.16, 0.16, len(v)), v, ".",
                    ms=3.6, color="0.28", alpha=0.75, zorder=3)
        for name, style in (("indoor", dict(color="#1f77b4", ls="--")),
                            ("outdoor", dict(color="#d62728", ls="-."))):
            ax.axhline(100 * presets[name][pkey], lw=1.3,
                       label=f"{name.capitalize()} preset", **style)
        ax.set_yscale("log")
        ax.set_xlim(0.45, len(DATASETS) + 0.55)
        ax.set_xticks(pos)
        ax.set_xticklabels([d["xtick"] for d in DATASETS])
        ax.set_ylabel(ylab)
        ax.set_title(title, fontsize=FS - 0.5)
        ax.grid(axis="y", alpha=0.28, lw=0.5, which="both")
        if j == 0:
            ax.legend(loc="upper left", framealpha=0.85)

    fig.suptitle("Rotor speed in real hover — three public flight logs vs the two "
                 "presets used in this report", fontsize=FS + 1.0, y=0.978)
    fig.text(0.5, 0.012, "\n".join(textwrap.wrap(CAPTION, 128)),
             ha="center", va="bottom", fontsize=FS - 1.5, color="0.25")

    os.makedirs(f"{ROOT}/outputs/figures", exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(f"{ROOT}/outputs/figures/report07_f13.{ext}",
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return picks


# ── 실행 ────────────────────────────────────────────────────────────────────
def main():
    presets = {}
    for name, tag in (("indoor", ""), ("outdoor", "_outdoor")):
        m = json.load(open(f"{ROOT}/outputs/report07_hover_long{tag}.json"))["_meta"]
        presets[name] = {k: m[k] for k in ("static_spread", "wobble_amp", "wobble_hz")}

    cache = f"{ROOT}/outputs/rotor_log_traces.npz"
    data, notes = collect()
    have_raw = any(d["windows"] for d in data.values())

    if not have_raw and os.path.exists(cache):
        print("  ⚠ 원자료 없음 — 캐시(rotor_log_traces.npz)로 그림만 재생성")
        Z = np.load(cache, allow_pickle=True)
        data = {k: dict(windows=list(Z[f"{k}_windows"]),
                        traces={str(Z[f'{k}_key']): (Z[f"{k}_t"], Z[f"{k}_y"])})
                for k in [d["key"] for d in DATASETS] if f"{k}_t" in Z}
        for d in DATASETS:
            data.setdefault(d["key"], dict(windows=[], traces={}))

    picks = build(data, notes, presets)

    # ── 근거 JSON + 표시 구간 npz ──
    npz = {}
    srcs = {}
    for ds in DATASETS:
        key = ds["key"]
        wins = data[key]["windows"]
        srcs[key] = dict(
            name=ds["short"], venue=ds["venue"],
            signal=("motor PWM command [%] (NOT measured rpm)"
                    if ds["unit"] == "pwm" else "measured rotor speed [rpm]"),
            access_ok=bool(wins), note=notes.get(key),
            n_windows=len(wins),
            files=sorted({w["file"] for w in wins}),
        )
        if not wins:
            continue
        st = np.array([w["static_std_pct"] for w in wins])
        wb = np.array([x for w in wins for x in w["wobble_amp_pct"]
                       if np.isfinite(x)])
        pk = np.array([x for w in wins for x in w["wobble_peak_hz"]
                       if np.isfinite(x)])
        srcs[key].update(
            total_hover_s=round(float(sum(w["dur_s"] for w in wins)), 1),
            fs_hz=wins[0]["fs_hz"], level_mean=float(np.median(
                [w["level_mean"] for w in wins])),
            static_std_pct=dict(median=round(float(np.median(st)), 2),
                                min=round(float(st.min()), 2),
                                max=round(float(st.max()), 2)),
            wobble_amp_pct=dict(median=round(float(np.median(wb)), 2),
                                p25=round(float(np.percentile(wb, 25)), 2),
                                p75=round(float(np.percentile(wb, 75)), 2),
                                min=round(float(wb.min()), 2),
                                max=round(float(wb.max()), 2)),
            wobble_peak_hz=dict(median=round(float(np.median(pk)), 2),
                                p25=round(float(np.percentile(pk, 25)), 2),
                                p75=round(float(np.percentile(pk, 75)), 2)),
            windows=wins,
        )
        if key in picks:
            w, med, tkey = picks[key]
            srcs[key]["displayed_window"] = dict(
                file=w["file"], t0_s=w["t0"], dur_s=w["dur_s"],
                v_mean_ms=w["v_mean"], level_mean=w["level_mean"],
                static_std_pct=w["static_std_pct"],
                wobble_amp_pct=w["wobble_amp_pct"],
                wobble_peak_hz=w["wobble_peak_hz"],
                why="정적 산포가 그 원천의 창 중앙값에 가장 가까운 창"
                    + (" (과도응답 창 제외)" if key == "neurobem" else ""))
            t, y = data[key]["traces"][tkey]
            npz[f"{key}_t"] = np.asarray(t, np.float32)
            npz[f"{key}_y"] = np.asarray(y, np.float32)
            npz[f"{key}_key"] = np.array(tkey)
            npz[f"{key}_windows"] = np.array(wins, dtype=object)

    doc = dict(
        title="report07 그림 13 근거 — 공개 실기체 비행로그에서 직접 잰 로터 산포·흔들림",
        purpose="그림 11 의 «야외 프리셋»(산포 ±2 %, 흔들림 2.5 % @ 1 Hz)이 논문 인용이 "
                "아니라 공개 비행로그 실측임을 사용자가 눈으로 확인할 수 있게 한다.",
        date="2026-08-10",
        figure="outputs/figures/report07_f13.{png,pdf}",
        builder="benchmark/build_rotor_log_fig.py",
        raw_data_dir=RAW,
        source_urls_and_cautions="outputs/rotor_rpm_web_anchor.json",
        measurement_convention=dict(
            hover_window=f"|v| < {V_MAX} m/s 연속 구간 (NeuroBEM 은 추가로 "
                         f"|ω| < {W_MAX_NB} rad/s, DJI 는 평균 PWM > {PWM_HOVER_MIN} %)",
            min_duration_s=MIN_DUR,
            static_spread="창 내 모터별 평균의 모터간 std / 전체평균 [%]",
            wobble=f"모터별 상대 신호의 {WOBBLE_BAND[0]}–{WOBBLE_BAND[1]} Hz 대역 "
                   "rms×√2 (등가 사인 진폭) [%], 지배 주파수 = 그 대역 PSD 피크. "
                   "샘플링이 낮으면 상한은 0.45·fs 로 잘린다 "
                   "(PX4 fs=4 Hz → 실효 0.3–1.8 Hz)",
            note="세 원천 모두 같은 규약으로 다시 쟀다. 단 DJI 는 PWM 명령이라 "
                 "백분율의 의미가 rpm 두 원천과 다르다.",
        ),
        presets_in_report=dict(
            indoor={k: presets["indoor"][k] for k in presets["indoor"]},
            outdoor={k: presets["outdoor"][k] for k in presets["outdoor"]},
            source="outputs/report07_hover_long{,_outdoor}.json",
        ),
        sources=srcs,
    )
    with open(f"{ROOT}/outputs/rotor_log_traces.json", "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    if npz:
        np.savez_compressed(f"{ROOT}/outputs/rotor_log_traces.npz", **npz)

    print("  ✅ outputs/figures/report07_f13.png")
    print("  ✅ outputs/rotor_log_traces.json / .npz")
    for ds in DATASETS:
        s = srcs[ds["key"]]
        if not s["access_ok"]:
            print(f"     {ds['short']:22s}: ❌ {s['note']}")
            continue
        print(f"     {ds['short']:22s}: {s['n_windows']:2d} win "
              f"({s['total_hover_s']:.0f} s) · spread med "
              f"{s['static_std_pct']['median']:.2f}% "
              f"[{s['static_std_pct']['min']:.2f}–{s['static_std_pct']['max']:.2f}] · "
              f"wobble med {s['wobble_amp_pct']['median']:.2f}% "
              f"@ {s['wobble_peak_hz']['median']:.2f} Hz")


if __name__ == "__main__":
    main()
