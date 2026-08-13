# -*- coding: utf-8 -*-
"""verify_po_elev_attack.py — 「잣대 재정립 + 커널 cos(el) 판정」에 대한 반증 라운드.

⛔ 기존 원장 수정 금지. 산출물은 outputs/verify_po_elev_attack.json 하나.
⛔ GPU 미사용(순수 numpy).
"""
from __future__ import annotations
import json, os, sys, time
import numpy as np

ROOT = "/workspace/sionna"
for p in (ROOT + "/src", ROOT + "/benchmark"):
    if p not in sys.path:
        sys.path.insert(0, p)

C0 = 299792458.0
FC = 3.5e9
LAM = C0 / FC
PRF = 19700.0
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
EK = [f"{e:+.0f}" for e in ELS]
F_FLASH = 126.66666666666667
F_TIP0 = 1272.91
QS = (0.75, 0.90, 0.95)
NPZ = ROOT + "/outputs/elevation_sweep_md.npz"
LED = ROOT + "/outputs/verify_po_elev_metric.json"
OUT = ROOT + "/outputs/verify_po_elev_attack.json"

J = {}


# ───────────────────────── 독립 재구현 ─────────────────────────
def spec_ac(x, pad=4, win="hann"):
    x = np.asarray(x, complex)
    x = x - x.mean()
    n = len(x)
    w = {"hann": np.hanning(n), "rect": np.ones(n),
         "black": np.blackman(n), "hamm": np.hamming(n)}[win]
    Z = np.fft.fftshift(np.fft.fft(x * w, n=pad * n))
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / PRF))
    return f, np.abs(Z) ** 2


def wq(x, qs=QS, pad=4, smooth=40.0, forbid=2 * F_TIP0, win="hann",
       floor="mean", f_kin=None):
    f, P = spec_ac(x, pad=pad, win=win)
    df = f[1] - f[0]
    m = max(1, int(round(smooth / df)) | 1)
    Ps = np.convolve(P, np.ones(m) / m, mode="same") if m > 1 else P
    nb = np.abs(f) >= forbid
    Pn = (float(Ps[nb].mean()) if floor == "mean" else
          float(np.median(Ps[nb])) if floor == "median" else 0.0)
    Pc = Ps - Pn
    inb = ~nb
    o = np.argsort(np.abs(f))
    c = np.cumsum(Pc[o])
    tot = float(c[inb[o]].max())
    out = {}
    if tot <= 0:
        return {f"W{int(q*100)}": 0.0 for q in qs}
    cc = c / tot
    for q in qs:
        i = int(np.argmax(cc >= q)) if (cc >= q).any() else len(cc) - 1
        out[f"W{int(q*100)}"] = float(abs(f[o[i]]))
    sig = float(Pc[inb].clip(0).sum()); noi = float(Pn * inb.sum())
    out["snr_db"] = float(10 * np.log10(max(sig, 1e-300) / max(noi, 1e-300)))
    if f_kin:
        ov = Pc[inb & (np.abs(f) > f_kin)].clip(0).sum()
        out["over"] = float(ov / max(Pc[inb].clip(0).sum(), 1e-300))
    return out


def old_ptp(x):
    return float(np.ptp(np.unwrap(np.angle(np.asarray(x, complex)))) * 180 / np.pi)


def old_w(x, thr=20.0, pad=8):
    x = np.asarray(x, complex); n = len(x)
    Z = np.fft.fftshift(np.fft.fft(x * np.hanning(n), n=pad * n))
    f = np.fft.fftshift(np.fft.fftfreq(pad * n, 1.0 / PRF))
    S = np.abs(Z)
    return float(np.abs(f[S > S.max() * 10 ** (-thr / 20)]).max())


def pear(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a ** 2).sum() * (b ** 2).sum())
    return float((a * b).sum() / d) if d > 0 else float("nan")


def spear(a, b):
    from scipy.stats import rankdata
    return pear(rankdata(a), rankdata(b))


d = np.load(NPZ)
LEDG = json.load(open(LED))
OURS = {e: d[f"ours/el{e:+.0f}"] for e in ELS}
SION = {e: d[f"sionna/el{e:+.0f}"] for e in ELS}
cos_el = {e: float(np.cos(np.radians(e))) for e in ELS}

# ═══ A. 옛 잣대 독립 재현 ═══════════════════════════════════════════
A = {}
for e in ELS:
    A[f"{e:+.0f}"] = dict(phase_ptp_deg=round(old_ptp(OURS[e]), 1),
                          w20_hz=round(old_w(OURS[e]), 1))
J["A_old_metric_independent"] = A
print("A 옛 잣대(독립):", {k: v["phase_ptp_deg"] for k, v in A.items()})

# ═══ B. W90 독립 재현 (원장과 대조) ══════════════════════════════════
B = {}
led_rows = LEDG["rows"]
for arm, ser in (("ours", OURS), ("sionna", SION)):
    B[arm] = {}
    for e in ELS:
        mine = wq(ser[e])
        B[arm][f"{e:+.0f}"] = dict(
            mine_W90=round(mine["W90"], 1),
            ledger_W90=round(led_rows[arm][f"{e:+.0f}"]["W90"], 1),
            rel_diff=round(abs(mine["W90"] - led_rows[arm][f"{e:+.0f}"]["W90"])
                           / max(led_rows[arm][f"{e:+.0f}"]["W90"], 1e-9), 5))
J["B_W90_reproduction"] = B
print("B 재현 최대 상대오차:",
      max(v["rel_diff"] for arm in B.values() for v in arm.values()))

# ═══ C. W90 의 nuisance 민감도 (실측 데이터) ════════════════════════
knobs = [("base", dict()),
         ("pad1", dict(pad=1)), ("pad2", dict(pad=2)), ("pad8", dict(pad=8)),
         ("smooth0", dict(smooth=0.0)), ("smooth10", dict(smooth=10.0)),
         ("smooth80", dict(smooth=80.0)), ("smooth160", dict(smooth=160.0)),
         ("rect", dict(win="rect")), ("blackman", dict(win="black")),
         ("forbid1.5", dict(forbid=1.5 * F_TIP0)),
         ("forbid3", dict(forbid=3.0 * F_TIP0)),
         ("forbid4", dict(forbid=4.0 * F_TIP0)),
         ("nofloor", dict(floor="none")), ("medfloor", dict(floor="median"))]
C = {}
for name, kw in knobs:
    C[name] = {f"{e:+.0f}": round(wq(OURS[e], **kw)["W90"], 1) for e in ELS}
# 기록 절반씩
for half, sl in (("first_half", slice(0, 2048)), ("second_half", slice(2048, 4096))):
    C[half] = {f"{e:+.0f}": round(wq(OURS[e][sl])["W90"], 1) for e in ELS}
C["_spread_per_el"] = {
    k: round(max(C[n][k] for n, _ in knobs) / max(min(C[n][k] for n, _ in knobs), 1e-9), 2)
    for k in EK}
C["_r_cos_per_knob"] = {}
for n in list(C.keys()):
    if n.startswith("_"):
        continue
    v = [C[n][k] for k in EK]
    C["_r_cos_per_knob"][n] = dict(
        r=round(pear(v, [cos_el[e] for e in ELS]), 3),
        rho=round(spear(v, [cos_el[e] for e in ELS]), 3))
J["C_W90_nuisance_sensitivity"] = C
print("C 앙각별 knob 산포:", C["_spread_per_el"])
print("C r(cos) per knob:", {k: v["r"] for k, v in C["_r_cos_per_knob"].items()})

# ═══ D. r(cos) 의 판별력 — 다른 모형도 똑같이 잘 맞나 ═══════════════
w = np.array([led_rows["ours"][k]["W90"] for k in EK])
g = np.array([led_rows["geom_prop"][k]["W90"] for k in EK])
cs = np.array([cos_el[e] for e in ELS])
el = np.array(ELS)
models = {
    "cos(el)": cs,
    "cos^2(el)": cs ** 2,
    "cos^0.5(el)": np.sqrt(cs),
    "cos^3(el)": cs ** 3,
    "linear_in_el": 1.0 + el / 90.0,
    "sin(90+el)^1": np.sin(np.radians(90 + el)),
    "step_half": np.array([1, 1, 1, 1, 0.3, 0.15, 0.15], float),
    "constant_then_drop": np.array([1, 1, 1, .8, .3, .15, .15], float),
    "1/(1+ (el/45)^2)": 1.0 / (1.0 + (el / 45.0) ** 2),
    "exp(el/40)": np.exp(el / 40.0),
    "geom_pred_W90": np.array([LEDG["prediction_geometric"][k]["W90"] for k in EK]),
}
D = {}
for nm, mv in models.items():
    D[nm] = dict(r_ours=round(pear(w, mv), 3), rho_ours=round(spear(w, mv), 3),
                 r_geom=round(pear(g, mv), 3))
# 무작위 단조감소 수열의 r(cos) 귀무분포
rng = np.random.default_rng(0)
null = []
for _ in range(20000):
    v = np.sort(rng.random(7))[::-1]
    null.append(pear(v, cs))
null = np.array(null)
D["_null_monotone_decreasing"] = dict(
    mean=round(float(null.mean()), 3), p05=round(float(np.quantile(null, .05)), 3),
    p50=round(float(np.quantile(null, .5)), 3), p95=round(float(np.quantile(null, .95)), 3),
    frac_above_0932=round(float((null > 0.932).mean()), 3))
J["D_shape_discrimination"] = D
print("D 모형별 r(ours):", {k: v["r_ours"] for k, v in D.items() if not k.startswith("_")})
print("D 귀무:", D["_null_monotone_decreasing"])

# ═══ E. 합성 AM 스윕이 항등식인가 (동어반복 검사) ═══════════════════
def synth(beta, b, n=4096, f_rev=63.333333, nb=2):
    t = np.arange(n) / PRF
    x = np.zeros(n, complex)
    for k in range(nb):
        x += np.exp(1j * beta * np.sin(2 * np.pi * f_rev * t + k * np.pi / nb))
    return x / nb + b


beta0 = F_TIP0 / 63.333333
x0 = synth(beta0, 0.0)
E = {"ac_identical_across_b": {}}
for b in (0.0, 0.5, 0.9, 1.0, 2.0):
    xb = synth(beta0, b)
    E["ac_identical_across_b"][f"{b:g}"] = dict(
        max_abs_diff_of_AC=float(np.abs((xb - xb.mean()) - (x0 - x0.mean())).max()),
        W90=round(wq(xb)["W90"], 2))
E["note_ko"] = ("합성 AM 스윕의 b 는 **가산 상수**라 x−mean(x) 가 비트 동일하다. "
                "그래서 W90 이 안 흔들리는 것은 강건성의 증거가 아니라 항등식이다.")

# 진짜 곱셈형 AM 시험 — 주기 플래시 포락선 × 같은 FM
def flash_env(n=4096, f=F_FLASH, dutylike=8.0, depth=1.0):
    t = np.arange(n) / PRF
    c = np.cos(2 * np.pi * f * t)
    env = np.exp(dutylike * (c - 1.0))            # 좁은 주기 펄스 (0~1)
    return 1.0 - depth + depth * env


E["true_multiplicative_AM"] = {}
truth = 1272.9
for depth in (0.0, 0.3, 0.6, 0.9, 1.0):
    for sharp in (4.0, 16.0, 64.0):
        xm = synth(beta0, 0.0) * flash_env(depth=depth, dutylike=sharp)
        r = wq(xm, f_kin=truth)
        E["true_multiplicative_AM"][f"depth{depth:g}_sharp{sharp:g}"] = dict(
            W90=round(r["W90"], 1), W95=round(r["W95"], 1),
            over_kin=round(100 * r.get("over", 0), 1))
J["E_synthetic_AM_audit"] = E
print("E 가산 AM 은 항등식? max|ΔAC| =",
      {k: v["max_abs_diff_of_AC"] for k, v in E["ac_identical_across_b"].items()})
print("E 곱셈 AM:", {k: v["W90"] for k, v in E["true_multiplicative_AM"].items()})

# ═══ F. −60° 스파이크가 「같은 자리」인가 — b 를 흔들어 본다 ═════════
F = {}
for b in (0.5, 0.7, 0.9, 1.0, 1.1, 1.5, 2.0):
    row = {}
    for e in ELS:
        xs = synth(beta0 * cos_el[e], b)
        row[f"{e:+.0f}"] = round(old_ptp(xs), 0)
    F[f"b={b:g}"] = row
    arg = max(row, key=lambda k: row[k])
    F[f"b={b:g}"]["_argmax_el"] = arg
J["F_synth_spike_location"] = F
print("F 스파이크 위치:", {k: v["_argmax_el"] for k, v in F.items()})

# ═══ G. FM 이론상 over_kinematic 바닥 (단일 산란점) ═════════════════
G = {}
for e in ELS:
    dfmax = F_TIP0 * cos_el[e]
    for fm in (63.333333, 126.666667):
        beta = dfmax / fm
        n = 4096
        t = np.arange(n) / PRF
        x = np.exp(1j * beta * np.sin(2 * np.pi * fm * t))
        r = wq(x, f_kin=max(dfmax, 1e-9))
        G[f"el{e:+.0f}_fm{fm:.0f}"] = dict(
            beta=round(beta, 2), delta_f=round(dfmax, 1),
            over_kin_pct=round(100 * r.get("over", 0), 2),
            W90=round(r["W90"], 1), W90_over_deltaf=round(r["W90"] / max(dfmax, 1e-9), 3))
J["G_FM_theory_over_kinematic_floor"] = G
print("G 단일 산란점 FM 의 한계초과 %:",
      {k: v["over_kin_pct"] for k, v in G.items() if "fm127" in k or "fm63" in k})

# ═══ H. ours 의 스펙트럼 CDF — 좁아진 것이 가장자리인가 몸통인가 ════
H = {}
for e in ELS:
    row = {}
    for nm, x in (("ours", OURS[e]),):
        f, P = spec_ac(x)
        df = f[1] - f[0]
        m = max(1, int(round(40.0 / df)) | 1)
        Ps = np.convolve(P, np.ones(m) / m, mode="same")
        nb = np.abs(f) >= 2 * F_TIP0
        Pc = Ps - Ps[nb].mean()
        inb = ~nb
        tot = Pc[inb].clip(0).sum()
        # 첫 두 플래시 조화(±190 Hz 이내) 에너지 몫
        low = inb & (np.abs(f) <= 1.5 * F_FLASH)
        low2 = inb & (np.abs(f) <= 2.5 * F_FLASH)
        row["frac_below_1.5xflash"] = round(float(Pc[low].clip(0).sum() / tot), 3)
        row["frac_below_2.5xflash"] = round(float(Pc[low2].clip(0).sum() / tot), 3)
        for q in (0.99, 0.995):
            o = np.argsort(np.abs(f)); c = np.cumsum(Pc[o]) / tot
            i = int(np.argmax(c >= q)) if (c >= q).any() else len(c) - 1
            row[f"W{q}"] = round(float(abs(f[o[i]])), 1)
    H[f"{e:+.0f}"] = row
J["H_spectral_shape"] = H
print("H 저역(≤2.5×flash) 에너지 몫:",
      {k: v["frac_below_2.5xflash"] for k, v in H.items()})

with open(OUT, "w") as fh:
    json.dump(J, fh, ensure_ascii=False, indent=1)
print("\nOK", OUT)
