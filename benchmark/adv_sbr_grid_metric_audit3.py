# -*- coding: utf-8 -*-
"""적대적 감사 3 — 결정타 두 개.

Q1. 얼린 팔의 «블레이드 대역 전력이 생산 팔보다 15 dB 낮다» — 신호를 깎은 것인가,
    아니면 생산 팔의 위상흔들림 누설을 지운 것인가?
    → 심판 둘: (a) phase 팔(격자는 그대로, 위상원점만 사후 고정), (b) 순수 PO(독립 엔진).
    평활(DC 번짐)을 **쓰지 않고** 잰다.
Q2. 팔끼리 비교는 전역 상수위상 때문에 NRMSE 가 부풀 수 있다 — 위상 정렬 후 다시 잰다.
"""
from __future__ import annotations
import json, os
import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
J = json.load(open(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.json")))
M = J["_meta"]
PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
Z = np.load(os.path.join(_ROOT, "outputs", "sbr_grid_convergence.npz"))
DIVS = M["divs"]; NT = int(M["n"]); FB = 0.15 * FTIP
PO_DIVS = M["po_divs"]


def spec(E, pad=4):
    E = np.asarray(E, complex)
    S = np.fft.fftshift(np.abs(np.fft.fft(E * np.hanning(len(E)), int(pad * len(E)))))
    f = np.fft.fftshift(np.fft.fftfreq(int(pad * len(E)), 1.0 / PRF))
    return f, S


def bands(E):
    """평활 없이 — DC 번짐이 섞이지 않는다."""
    f, S = spec(E)
    P = S ** 2 / NT ** 2
    return dict(dc=float(P[np.abs(f) <= FB].sum()),
                mid=float(P[(np.abs(f) > FB) & (np.abs(f) <= FTIP)].sum()),
                out=float(P[np.abs(f) > FTIP].sum()),
                tot=float(P.sum()))


def db(a, b):
    return float(10 * np.log10(a / b))


# ── Q1 ────────────────────────────────────────────────────────────────────
series = {}
for dv in DIVS:
    for arm in ("prod", "phase", "froz"):
        series[(arm, dv)] = Z[f"E_{arm}_div{dv}"]
for dv in PO_DIVS:
    series[("po", dv)] = Z[f"po_div{dv}"]

B = {k: bands(v) for k, v in series.items()}

print("[Q1] 평활 없는 대역 전력 (DC 번짐 없음).  단위: 절대, 팔·div 간 직접 비교 가능")
print(f"{'arm':>6} {'div':>4} {'P_dc':>11} {'P_mid':>11} {'P_out':>11} "
      f"{'mid/dc dB':>10} {'out/mid dB':>11}")
for arm in ("prod", "phase", "froz", "po"):
    for dv in (PO_DIVS if arm == "po" else DIVS):
        b = B[(arm, dv)]
        print(f"{arm:>6} {dv:>4} {b['dc']:>11.4e} {b['mid']:>11.4e} {b['out']:>11.4e} "
              f"{db(b['mid'], b['dc']):>10.2f} {db(b['out'], b['mid']):>11.2f}")

print("\n[Q1b] 블레이드 대역(P_mid) — 누가 맞나. 순수 PO(div16)를 0 dB 로 둔다")
po_mid = B[("po", 16)]["mid"]
po_dc = B[("po", 16)]["dc"]
print(f"{'div':>4} {'prod':>9} {'phase':>9} {'froz':>9}   (dB vs 순수 PO 의 P_mid)")
q1b = []
for dv in DIVS:
    r = dict(div=dv, **{a: db(B[(a, dv)]["mid"], po_mid) for a in ("prod", "phase", "froz")})
    q1b.append(r)
    print(f"{dv:>4} {r['prod']:>9.2f} {r['phase']:>9.2f} {r['froz']:>9.2f}")
print(f"  참고: P_mid/P_dc 비 — po {db(po_mid, po_dc):+.2f} dB")

# ── Q2. 위상 정렬 후 팔끼리 비교 ───────────────────────────────────────────
def lp(E, fc=FTIP):
    X = np.fft.fft(np.asarray(E, complex))
    fr = np.fft.fftfreq(len(X), 1.0 / PRF)
    X[np.abs(fr) > fc] = 0
    return np.fft.ifft(X)


def aligned_err(a, b):
    """전역 상수 위상(그리고 원하면 스케일)을 최적으로 맞춘 뒤의 상대오차."""
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    ph = np.vdot(b, a)
    ph = ph / (abs(ph) + 1e-300)
    return float(np.linalg.norm(a - ph * b) / np.linalg.norm(b))


def coh(a, b):
    a = np.asarray(a, complex); b = np.asarray(b, complex)
    return float(abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))


print("\n[Q2] 전역 상수위상 정렬 후 — 팔끼리 (같은 div)")
print(f"{'div':>4} {'phase↔froz raw':>15} {'정렬후':>9} {'|coh|':>8} | "
      f"{'phase↔po 정렬후':>16} {'froz↔po 정렬후':>15}")
q2 = []
for dv in DIVS:
    eh = lp(Z[f"E_phase_div{dv}"]); ef = lp(Z[f"E_froz_div{dv}"])
    epo = lp(Z["po_div16"])
    raw = float(np.linalg.norm(eh - ef) / np.linalg.norm(ef))
    r = dict(div=dv, phase_froz_raw=raw, phase_froz_aligned=aligned_err(eh, ef),
             phase_froz_coh=coh(eh, ef),
             phase_po_aligned=aligned_err(eh, epo), froz_po_aligned=aligned_err(ef, epo),
             phase_po_coh=coh(eh, epo), froz_po_coh=coh(ef, epo))
    q2.append(r)
    print(f"{dv:>4} {raw:>15.4f} {r['phase_froz_aligned']:>9.4f} {r['phase_froz_coh']:>8.4f} | "
          f"{r['phase_po_aligned']:>16.4f} {r['froz_po_aligned']:>15.4f}")

# ── Q3. 평활 없는 «정직한» 대역밖 비율 + 그 수렴 ────────────────────────────
print("\n[Q3] 평활 없는 정직한 지표  frac = P_out / P_mid   (DC 번짐 없음)")
print(f"{'div':>4} {'prod':>11} {'phase':>11} {'froz':>11} {'po':>11} | "
      f"{'freeze 이득 dB':>14} {'phase→froz dB':>14}")
q3 = []
po_frac = B[("po", 16)]["out"] / B[("po", 16)]["mid"]
for dv in DIVS:
    fr = {a: B[(a, dv)]["out"] / B[(a, dv)]["mid"] for a in ("prod", "phase", "froz")}
    r = dict(div=dv, **fr, po=po_frac,
             freeze_gain_db=db(fr["prod"], fr["froz"]),
             phase_to_froz_db=db(fr["phase"], fr["froz"]))
    q3.append(r)
    print(f"{dv:>4} {fr['prod']:>11.4e} {fr['phase']:>11.4e} {fr['froz']:>11.4e} "
          f"{po_frac:>11.4e} | {r['freeze_gain_db']:>14.2f} {r['phase_to_froz_db']:>14.2f}")


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.stack([np.log(x), np.ones(len(x))], 1)
    c, *_ = np.linalg.lstsq(A, np.log(y), rcond=None)
    p = A @ c
    ss = float(np.sum((np.log(y) - np.log(y).mean()) ** 2))
    return float(c[0]), float(1 - np.sum((np.log(y) - p) ** 2) / ss)


print("\n[Q4] 평활 없는 지표의 수렴 기울기 (전 사다리 / λ12 이상)")
conv = {}
for a in ("prod", "phase", "froz"):
    for key, get in (("frac_nosmooth", lambda d, a=a: B[(a, d)]["out"] / B[(a, d)]["mid"]),
                     ("P_out_nosmooth", lambda d, a=a: B[(a, d)]["out"]),
                     ("P_mid_nosmooth", lambda d, a=a: B[(a, d)]["mid"])):
        y = [get(d) for d in DIVS]
        s, r2 = slope(DIVS, y)
        s12, r212 = slope([d for d in DIVS if d >= 12], [v for d, v in zip(DIVS, y) if d >= 12])
        conv[f"{a}_{key}"] = dict(values=y, slope=s, r2=r2, slope_ge12=s12, r2_ge12=r212)
        print(f"  {a:>6} {key:>16}  전체 {s:+.2f}(R²{r2:.3f})   ≥12 {s12:+.2f}(R²{r212:.3f})")

OUT = os.path.join(_ROOT, "outputs", "adv_sbr_grid_metric_audit3.json")
json.dump(dict(_meta=dict(purpose="평활(DC 번짐) 없이 재측정 + 위상정렬 팔 비교",
                          note="원장 outputs/sbr_grid_convergence.* 는 수정하지 않았다"),
               band_powers_nosmooth={f"{a}_div{d}": B[(a, d)] for (a, d) in B},
               pmid_vs_pure_po_db=q1b, arm_alignment=q2,
               honest_frac=q3, convergence_nosmooth=conv),
          open(OUT, "w"), ensure_ascii=False, indent=1)
print("\n→", OUT)
