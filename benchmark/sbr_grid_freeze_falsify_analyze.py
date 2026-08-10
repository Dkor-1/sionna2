# -*- coding: utf-8 -*-
"""sbr_grid_freeze_falsify_analyze.py — 반증 실험 집계.

`sbr_grid_freeze_falsify.py` 가 낸 팔들을 원 실험의 생산/얼림 팔과 **같은 잣대**로 잰다.
잣대는 두 가지를 나란히 둔다:
  · `frac_oob`   리포트 7b·원 실험과 같은 비율 (Hann·4배패딩 → 4·f_flash 포락 → 블레이드
                 대역 전력 중 |f|>f_tip 비율).  ⚠ 이 분모는 대부분 DC 누설이다(아래 참조).
  · `P_oob_abs`  **절대** 대역밖 전력 (포락·평활 없는 원 주기도) — 비율의 분모 장난을 배제한다.
"""
from __future__ import annotations
import datetime as _dt, json, os, socket, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np                                                      # noqa: E402

PARTS = os.path.join(_ROOT, "outputs", "archive", "sbr_grid_conv_parts")
OUTJ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.json")

M = json.load(open(os.path.join(_ROOT, "outputs", "report07_three_engines.json")))["_meta"]
PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
LAM = 299792458.0 / float(M["fc_hz"]); K = 2 * np.pi / LAM


def per(E, pad=4):
    E = np.asarray(E, complex); w = np.hanning(len(E)); nf = int(pad * len(E))
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1 / PRF))
    return f, np.fft.fftshift(np.abs(np.fft.fft(E * w, nf))) ** 2


def sm(f, P, w):
    df = f[1] - f[0]; n = max(3, int(round(w / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same")


def meas(E):
    f, P = per(E); Pe = sm(f, P, 4 * FFL)
    b = np.abs(f) > 0.15 * FTIP; o = b & (np.abs(f) > FTIP)
    inb = (np.abs(f) > 0.3 * FTIP) & (np.abs(f) <= FTIP)      # DC 누설 밖의 깨끗한 대역내
    return dict(frac_oob=float(Pe[o].sum() / Pe[b].sum()),
                P_oob_abs=float(P[np.abs(f) > FTIP].sum()),
                P_inband_clean=float(P[inb].sum()),
                level_db=float(10 * np.log10(np.mean(np.abs(E) ** 2))))


def bp(E, lo, hi):
    X = np.fft.fft(np.asarray(E, complex)); fr = np.fft.fftfreq(len(X), 1 / PRF)
    X[(np.abs(fr) < lo) | (np.abs(fr) > hi)] = 0
    return np.fft.ifft(X)


def main():
    Z = np.load(os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.npz"))
    NT = int(Z["nt"][0]); div = int(Z["div"][0])
    zp = np.load(os.path.join(PARTS, f"div{div:03d}.npz"))
    cu = zp["ctr_u"][:NT]
    E = {"prod": zp["E_prod"][:NT], "froz_ref": zp["E_froz"][:NT],
         "phase": zp["E_prod"][:NT] * np.exp(1j * 2 * K * (cu - cu[0]))}
    for a in ("froz", "froz_half", "dith", "replay", "nflip"):
        E[a] = Z[f"E_{a}"]
    PO = np.load(os.path.join(PARTS, "po.npz"))["po_div11"][:NT]
    E["pure_PO"] = PO

    # ── 회귀 게이트: 내 froz 가 원 실험의 froz 와 같은가 ─────────────────────
    a, b = E["froz"], E["froz_ref"]
    rel = np.abs(a - b) / (np.abs(b) + 1e-300)
    gate = dict(n=NT, max_rel_err=float(rel.max()), median_rel_err=float(np.median(rel)),
                n_bit_identical=int(np.sum(a == b)),
                note="내 트레이서가 원 실험의 얼린 팔을 재현하는가 (ctr₀·Rout₀ 상속)")
    print(f"[gate] froz vs 원장 froz : max rel err {rel.max():.3e} · 비트동일 "
          f"{gate['n_bit_identical']}/{NT}")

    rows = {}
    for nm, e in E.items():
        r = meas(e)
        r["corr_inband_vs_PO"] = float(abs(np.vdot(bp(e, 0.15 * FTIP, FTIP), bp(PO, 0.15 * FTIP, FTIP)))
                                       / (np.linalg.norm(bp(e, 0.15 * FTIP, FTIP))
                                          * np.linalg.norm(bp(PO, 0.15 * FTIP, FTIP)) + 1e-300))
        r["nlit_mean"] = float(Z[f"nlit_{nm}"].mean()) if f"nlit_{nm}" in Z else None
        r["nlit_ptp"] = int(Z[f"nlit_{nm}"].max() - Z[f"nlit_{nm}"].min()) if f"nlit_{nm}" in Z else None
        rows[nm] = r

    ref = rows["froz"]
    order = ["prod", "phase", "froz", "froz_half", "dith", "replay", "nflip", "pure_PO"]
    print(f"\n{'arm':10} {'frac_oob':>10} {'P_oob 절대':>12} {'froz 대비 dB':>12} "
          f"{'대역내(깨끗)':>13} {'PO상관':>7} {'level dB':>9} {'n_lit':>9}")
    for nm in order:
        r = rows[nm]
        db = 10 * np.log10(r["P_oob_abs"] / ref["P_oob_abs"])
        r["P_oob_db_vs_froz"] = float(db)
        nl = f"{r['nlit_mean']:9.1f}" if r["nlit_mean"] else "        -"
        print(f"{nm:10} {r['frac_oob']:10.5f} {r['P_oob_abs']:12.4e} {db:+12.2f} "
              f"{r['P_inband_clean']:13.4e} {r['corr_inband_vs_PO']:7.3f} {r['level_db']:9.3f} {nl}")

    # ── 판정 ────────────────────────────────────────────────────────────────
    def g(a, b_):
        return float(10 * np.log10(rows[a]["P_oob_abs"] / rows[b_]["P_oob_abs"]))
    gap = g("prod", "froz")
    verdict = dict(
        prod_over_froz_db=gap,
        F1_lucky_draw=dict(
            froz_half_over_froz_db=g("froz_half", "froz"),
            note=("F1 = «얼린 격자가 운 좋은 오프셋을 뽑았을 뿐». 반 칸 옮긴 두 번째 판이 "
                  "생산 수준(+%.1f dB)으로 올라가면 F1 이 맞다." % gap),
            falsified=bool(abs(g("froz_half", "froz")) < 0.5 * gap)),
        F3_causality=dict(
            dith_over_froz_db=g("dith", "froz"),
            replay_over_froz_db=g("replay", "froz"),
            nflip_over_froz_db=g("nflip", "froz"),
            note=("F3 = «격자 재정의는 원인이 아니다». 얼린 격자에 흔들림만 되먹였을 때 "
                  "바닥이 생산 수준으로 되돌아오면 인과가 확인된다(F3 반증)."),
            confirmed=bool(max(g("dith", "froz"), g("replay", "froz"), g("nflip", "froz"))
                           > 0.5 * gap)),
    )
    print("\n=== 판정 ===")
    print(f"  생산이 얼림보다 {gap:+.2f} dB 높다 (절대 대역밖 전력)")
    print(f"  F1 운좋은판 : froz_half {verdict['F1_lucky_draw']['froz_half_over_froz_db']:+.2f} dB "
          f"→ {'반증됨(운이 아니다)' if verdict['F1_lucky_draw']['falsified'] else '⚠살아있음'}")
    for kk in ("dith", "replay", "nflip"):
        print(f"  F3 인과    : {kk:7} {verdict['F3_causality'][kk+'_over_froz_db']:+.2f} dB "
              f"({100*10**(verdict['F3_causality'][kk+'_over_froz_db']/10)/10**(gap/10):.0f}% 회복)")
    print(f"  → 인과 {'확인' if verdict['F3_causality']['confirmed'] else '⚠미확인 — 결론이 깨진다'}")

    out = dict(_meta=dict(generated=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                          host=socket.gethostname(),
                          script="benchmark/sbr_grid_freeze_falsify.py (+_analyze)",
                          purpose=("outputs/sbr_grid_convergence.json 의 결론을 **반증하려는** "
                                   "적대적 재실험. 원 원장은 건드리지 않는다."),
                          div=div, nt=NT, spacing_m=float(Z["d"][0]), n0=int(Z["n0"][0]),
                          drone=M["drone"], fc_hz=M["fc_hz"], prf_hz=PRF, f_tip_hz=FTIP,
                          f_flash_hz=FFL, az_deg=M["az_deg"], el_deg=M["el_deg"],
                          arms=dict(
                              prod="생산 그대로(원 원장에서 잘라옴)",
                              phase="생산에 위상원점만 사후 고정 — 진폭 불변(1e-16)",
                              froz="얼린 격자(원 실험의 ctr₀·Rout₀ 상속) — 재현 게이트",
                              froz_half="⭐얼리되 반 칸 옆으로 — 두 번째 오프셋 판(F1)",
                              dith="⭐얼린 격자에 자세마다 무작위 서브셀 오프셋 되먹임(F3)",
                              replay="⭐생산이 겪은 ctr 의 가로 성분만 그대로 재생(F3)",
                              nflip="⭐격자 칸 수 n 만 ±1 토글 = 격자가 d/2 밀림(F3)",
                              pure_PO="독립 엔진(몸에 붙은 점구름, 격자 없음)"),
                          metrics=dict(
                              frac_oob="리포트 7b 잣대 (포락 비율)",
                              P_oob_abs="⭐절대 대역밖 전력 — 분모 없음",
                              P_inband_clean="0.3~1.0 f_tip 원 주기도 — DC 누설 밖",
                              corr_inband_vs_PO="블레이드 대역 복소 파형과 독립 PO 엔진의 상관")),
              regression_gate_froz=gate, rows=rows, verdict=verdict)
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"\n→ {OUTJ}")


if __name__ == "__main__":
    main()
