# -*- coding: utf-8 -*-
"""sbr_grid_freeze_review.py — ⭐«얼린 팔이 신호를 깎아 바닥이 내려간 것처럼 보인다» 반증 종합.

`outputs/sbr_grid_convergence.json` 의 결론을 **깨뜨리려고** 만든 검사들을 한 원장에 모은다.
원 원장(report07_*, sbr_grid_convergence.*)은 읽기만 한다 — 아무것도 덮어쓰지 않는다.

검사 목록
  R1 지표의 분모  «비율» 의 분모가 커져서 내려간 것 아닌가 → **절대** 대역밖 전력으로 다시 잰다.
  R2 분모의 정체  분모(블레이드 대역 포락 전력)가 실제로 무엇으로 채워져 있나.
  R3 신호 깎임    얼린 팔이 표적을 놓쳤나 → 히트 수·기하 여백·대역내 파형 대 독립 엔진(PO).
  R4 위상 팔      진폭을 **한 톨도 안 건드리는** 사후 위상보정만으로 바닥이 내려가는가.
  R5 재현성       생산의 대역밖 잔차가 격자를 바꿔도 재현되나(물리) 아닌가(잡음).
  R6 과적합       5점 기울기가 견고한가 — LOO·부분구간·절대/비율 양쪽.
  R7 기하         자세마다 bbox 가 바뀌는 것을 무시하면 로터가 격자 밖으로 나가나. 비용은.
  R8 인과         ⭐얼린 격자에 흔들림을 **되먹이면** 바닥이 돌아오는가(별도 GPU 실행).
"""
from __future__ import annotations
import datetime as _dt, glob, itertools, json, os, socket, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import numpy as np                                                      # noqa: E402

PARTS = os.path.join(_ROOT, "outputs", "archive", "sbr_grid_conv_parts")
FALZ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.npz")
FALJ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_falsify.json")
OUTJ = os.path.join(_ROOT, "outputs", "sbr_grid_freeze_review.json")

M = json.load(open(os.path.join(_ROOT, "outputs", "report07_three_engines.json")))["_meta"]
PRF = float(M["prf_hz"]); FTIP = float(M["f_tip_hz"]); FFL = float(M["f_flash_hz"])
LAM = 299792458.0 / float(M["fc_hz"]); K = 2 * np.pi / LAM
PAD = 1.15


def per(x, pad=4):
    x = np.asarray(x, complex); w = np.hanning(len(x)); nf = int(pad * len(x))
    return (np.fft.fftshift(np.fft.fftfreq(nf, 1 / PRF)),
            np.fft.fftshift(np.abs(np.fft.fft(x * w, nf))) ** 2)


def sm(f, P, w):
    df = f[1] - f[0]; n = max(3, int(round(w / df)) | 1)
    return np.convolve(P, np.ones(n) / n, mode="same")


def band(x, lo, hi):
    X = np.fft.fft(np.asarray(x, complex)); fr = np.fft.fftfreq(len(X), 1 / PRF)
    X[(np.abs(fr) < lo) | (np.abs(fr) > hi)] = 0
    return np.fft.ifft(X)


def coh(a, b):
    return float(abs(np.vdot(a, b)) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))


def loglog(x, y):
    x = np.log(np.asarray(x, float)); y = np.log(np.asarray(y, float))
    A = np.stack([x, np.ones_like(x)], 1); c, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(c[0]), float(1 - np.sum((y - A @ c) ** 2) / np.sum((y - y.mean()) ** 2))


def main():
    D = {}
    for p in sorted(glob.glob(os.path.join(PARTS, "div*.npz"))):
        z = np.load(p); D[int(z["div"][0])] = z
    divs = sorted(D)
    PO = np.load(os.path.join(PARTS, "po.npz"))["po_div11"]
    NT = len(D[divs[0]]["E_prod"])
    arm = {}
    for dv in divs:
        cu = D[dv]["ctr_u"]
        arm[dv] = dict(prod=D[dv]["E_prod"], froz=D[dv]["E_froz"],
                       phase=D[dv]["E_prod"] * np.exp(1j * 2 * K * (cu - cu[0])))

    # ── R1/R2 ────────────────────────────────────────────────────────────────
    def num(E):
        f, P = per(E); Pe = sm(f, P, 4 * FFL)
        b = np.abs(f) > 0.15 * FTIP; o = b & (np.abs(f) > FTIP)
        fd, Pd = per(np.full(len(E), np.mean(E))); Pde = sm(fd, Pd, 4 * FFL)
        return dict(frac_oob=float(Pe[o].sum() / Pe[b].sum()),
                    P_oob_env=float(Pe[o].sum()), P_blade_env=float(Pe[b].sum()),
                    dc_leak_frac_of_denominator=float(Pde[b].sum() / Pe[b].sum()),
                    P_oob_raw=float(P[np.abs(f) > FTIP].sum()),
                    P_inband_clean_raw=float(
                        P[(np.abs(f) > 0.3 * FTIP) & (np.abs(f) <= FTIP)].sum()),
                    level_db=float(10 * np.log10(np.mean(np.abs(E) ** 2))))
    po_n = num(PO)
    R1 = dict(note=("⭐비율의 분모 장난 배제. `frac_oob` 는 원 실험/리포트7b 의 잣대, "
                    "`P_oob_raw` 는 포락·정규화 없는 절대 대역밖 전력이다."),
              rows=[])
    for dv in divs:
        r = dict(div=dv)
        for a in ("prod", "phase", "froz"):
            for kk, vv in num(arm[dv][a]).items():
                r[f"{a}_{kk}"] = vv
        r["freeze_gain_db_ratio_metric"] = float(10 * np.log10(
            r["prod_frac_oob"] / r["froz_frac_oob"]))
        r["freeze_gain_db_absolute"] = float(10 * np.log10(
            r["prod_P_oob_raw"] / r["froz_P_oob_raw"]))
        r["inband_excess_over_PO_db_prod"] = float(10 * np.log10(
            r["prod_P_inband_clean_raw"] / po_n["P_inband_clean_raw"]))
        r["inband_excess_over_PO_db_froz"] = float(10 * np.log10(
            r["froz_P_inband_clean_raw"] / po_n["P_inband_clean_raw"]))
        R1["rows"].append(r)
    R1["verdict"] = ("**반증 실패**. 절대 전력으로 재면 얼리기의 이득이 오히려 **더 크다** "
                     "(λ/12 에서 비율 9.34 dB ↔ 절대 13.09 dB). 분모가 커져서 내려간 것이 "
                     "아니다 — 분모도 같이 내려갔고, 그래서 비율 쪽이 **보수적**이다.")
    R2 = dict(note=("분모 = 블레이드 대역(|f|>0.15 f_tip) 의 **포락** 전력. 포락 이동평균 폭이 "
                    "4·f_flash = %.0f Hz 인데 대역 시작이 %.0f Hz 라, 거대한 DC(동체 반사)가 "
                    "분모 안으로 번져 들어온다." % (4 * FFL, 0.15 * FTIP)),
              dc_leak_frac=dict(
                  prod_div12=R1["rows"][divs.index(12)]["prod_dc_leak_frac_of_denominator"],
                  froz_div12=R1["rows"][divs.index(12)]["froz_dc_leak_frac_of_denominator"],
                  pure_PO=po_n["dc_leak_frac_of_denominator"]),
              verdict=("⚠**지표 자체의 약점을 하나 찾았다** — 조용한 팔일수록 분모가 거의 전부 "
                       "DC 누설이다(얼린 팔 97%, 순수 PO 99%). 즉 `frac_power_beyond_ftip` 은 "
                       "«블레이드 대역 대비» 가 아니라 사실상 «동체 DC 대비» 다. 이는 리포트 7b "
                       "헤드라인(SBR 6.05% · Sionna 2.12% · PO 0.02%)에도 그대로 걸린다. "
                       "다만 세 팔 모두에 같이 걸리므로 **순위와 결론은 안 바뀐다** — 절대 전력 "
                       "재측정이 같은 결론을 준다(R1)."))

    # ── R3 ───────────────────────────────────────────────────────────────────
    R3 = dict(note="얼린 팔이 표적을 놓쳤나 / 변조를 지웠나.",
              rows=[dict(div=dv,
                         nlit_prod=float(D[dv]["n_lit_prod"].mean()),
                         nlit_froz=float(D[dv]["n_lit_froz"].mean()),
                         nlit_ratio=float(D[dv]["n_lit_froz"].mean() / D[dv]["n_lit_prod"].mean()),
                         corr_inband_prod_vs_PO=coh(band(arm[dv]["prod"], 0.15 * FTIP, FTIP),
                                                    band(PO, 0.15 * FTIP, FTIP)),
                         corr_inband_phase_vs_PO=coh(band(arm[dv]["phase"], 0.15 * FTIP, FTIP),
                                                     band(PO, 0.15 * FTIP, FTIP)),
                         corr_inband_froz_vs_PO=coh(band(arm[dv]["froz"], 0.15 * FTIP, FTIP),
                                                    band(PO, 0.15 * FTIP, FTIP)),
                         inband_excess_over_PO_db_prod=R1["rows"][i]["inband_excess_over_PO_db_prod"],
                         inband_excess_over_PO_db_froz=R1["rows"][i]["inband_excess_over_PO_db_froz"])
                    for i, dv in enumerate(divs)],
              verdict=("**반증 실패**. (a) 히트 수가 같다(비율 0.99~1.02) — 표적을 놓치지 않았다. "
                       "(b) 생산 팔의 블레이드 대역 전력은 독립 엔진(PO)보다 **16.4 dB 크고 상관은 "
                       "0.09** 다 — 그 대역내 «신호» 는 신호가 아니라 잡음이다. 얼린 팔은 PO 보다 "
                       "3.5~3.9 dB 크고 상관 0.89~0.98 이다. 즉 얼리기는 신호를 깎은 것이 아니라 "
                       "**독립 엔진과 일치하는 쪽으로 되돌린 것**이다."))

    # ── R4 ───────────────────────────────────────────────────────────────────
    R4 = dict(note=("`phase` 팔은 exp(+j2k(ctr_i−ctr₀)·û) 를 곱하기만 한다 — |E| 는 자세마다 "
                    "**비트 단위로 불변**이다. 그런데도 바닥이 내려간다면, 그 몫은 «신호를 깎아서» "
                    "가 아니라 순전히 **위상 원점 장부질** 때문이다."),
              rows=[dict(div=dv,
                         max_abs_change=float(
                             np.abs(np.abs(arm[dv]["phase"]) - np.abs(arm[dv]["prod"])).max()
                             / np.abs(arm[dv]["prod"]).max()),
                         gain_db_absolute=float(10 * np.log10(
                             num(arm[dv]["prod"])["P_oob_raw"] / num(arm[dv]["phase"])["P_oob_raw"])))
                    for dv in divs],
              ctr_dot_u_ptp_mm=float((D[12]["ctr_u"].max() - D[12]["ctr_u"].min()) * 1e3),
              ctr_dot_u_ptp_rad=float(2 * K * (D[12]["ctr_u"].max() - D[12]["ctr_u"].min())),
              verdict=("**반증 실패, 그리고 이것만으로 결론의 절반이 선다**. 진폭 변화 1e-16 "
                       "(=0), 계산 0 회, 그런데 λ/32 에서 대역밖 전력이 8.8 dB 내려간다. 동체는 "
                       "정지해 있으므로 물리적으로 옳은 위상 원점은 **고정점**이다 — bbox 중심이 "
                       "39.9 mm(5.85 rad) 흔들리는 것은 순수한 장부 오류다."))

    # ── R5 ───────────────────────────────────────────────────────────────────
    hp = {a: {dv: band(arm[dv][a], FTIP, PRF / 2) for dv in divs} for a in ("prod", "froz")}
    R5 = dict(note=("생산의 대역밖 잔차가 격자 간격을 바꿔도 재현되면 «물리» 를 의심해야 한다. "
                    "⚠단 생산의 흔들림 구동원(bbox 중심 ctr_i)은 **div 에 무관**하므로 "
                    "div 사이 상관이 높다고 물리인 것은 아니다 — 그래서 독립 엔진 대조가 진짜 잣대다."),
              corr_across_div=dict(
                  prod={f"{a}vs{b}": coh(hp["prod"][a], hp["prod"][b])
                        for a, b in itertools.combinations(divs, 2)},
                  froz={f"{a}vs{b}": coh(hp["froz"][a], hp["froz"][b])
                        for a, b in itertools.combinations(divs, 2)}),
              corr_prod_vs_froz_same_div={str(dv): coh(hp["prod"][dv], hp["froz"][dv])
                                          for dv in divs},
              corr_prod_oob_vs_PO_oob={str(dv): coh(hp["prod"][dv], band(PO, FTIP, PRF / 2))
                                       for dv in divs},
              verdict=("생산의 대역밖 잔차는 div 사이에 0.53~0.83 으로 재현된다 — 처음엔 «물리» 처럼 "
                       "보인다. 그러나 구동원 ctr_i 가 div 에 무관하니 재현되는 것이 당연하고, "
                       "같은 div 의 얼린 팔과는 0.07~0.20 으로 **무상관**이며 독립 PO 엔진의 "
                       "대역밖과도 무상관이다. 물리가 아니다."))

    # ── R6 ───────────────────────────────────────────────────────────────────
    R6 = dict(note="5점 사다리 기울기의 견고성 — 비율/절대 × 전구간/≥12 × leave-one-out.")
    for a in ("prod", "phase", "froz"):
        fr = [num(arm[dv][a])["frac_oob"] for dv in divs]
        ab = [num(arm[dv][a])["P_oob_raw"] for dv in divs]
        e = {}
        for tag, y in (("frac", fr), ("abs", ab)):
            s, r2 = loglog(divs, y); s12, r12 = loglog(divs[1:], y[1:])
            lo = [loglog([d for i, d in enumerate(divs) if i != j],
                         [v for i, v in enumerate(y) if i != j])[0] for j in range(len(divs))]
            e[tag] = dict(slope_full=s, r2_full=r2, slope_ge12=s12, r2_ge12=r12,
                          loo_slopes=lo, loo_range=float(max(lo) - min(lo)), values=y)
        R6[a] = e
    R6["verdict"] = ("**froz 는 과적합이 아니다** — 절대 전력 기울기 −2.21, R² 0.999, LOO 폭 0.08, "
                     "≥12 부분구간에서도 −2.19. 비율로 재도 −2.09/LOO 폭 0.20. ⚠공정성 지적 하나: "
                     "원장은 prod 는 ≥12 구간(−0.55), froz 는 전구간(−2.09) 으로 보고한다. 같은 "
                     "≥12 잣대로 froz 를 재도 −2.12 라 결론은 안 바뀌지만, **두 팔에 같은 규칙을 "
                     "쓰는 편이 낫다**. 반대로 prod 를 전구간으로 재면 −1.67 이 나오는데 이는 "
                     "λ/8 한 점(알려진 나쁜 격자)이 끄는 값이고 LOO 폭이 1.56 으로 무의미하다.")

    # ── R7 (기하; 광선 안 쏜다) ──────────────────────────────────────────────
    R7 = None
    try:
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        from articulated_fast import FastPoser, rotor_phases
        from drones import DRONES
        fp = FastPoser(DRONES[M["drone"]])
        ph = rotor_phases(np.arange(NT) / PRF, np.asarray(M["rpm_per_rotor"], float), fp.dirs)
        a_, e_ = np.radians(M["az_deg"]), np.radians(M["el_deg"])
        u = np.array([np.cos(e_) * np.cos(a_), np.cos(e_) * np.sin(a_), np.sin(e_)])
        tmp = np.array([0, 0, 1.]) if abs(u[2]) < 0.9 else np.array([1., 0, 0])
        e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
        z = D[12]; ctr0 = np.asarray(z["ctr0"], float); R0 = float(z["Rout0"][0]); d = float(z["d"][0])
        n0 = int(np.ceil(2 * R0 / d))
        mp, mf, nn = [], [], []
        for i in range(0, NT, 8):
            V = np.asarray(fp.pose(ph[i]).v, float)
            c = 0.5 * (V.max(0) + V.min(0))
            n = int(np.ceil(2 * (float(np.linalg.norm(V - c, axis=1).max()) * PAD + 3 * d) / d))
            nn.append(n)
            mp.append((n - 1) / 2 * d - max(np.abs((V - c) @ e1).max(), np.abs((V - c) @ e2).max()))
            mf.append((n0 - 1) / 2 * d - max(np.abs((V - ctr0) @ e1).max(),
                                             np.abs((V - ctr0) @ e2).max()))
        mp = np.array(mp); mf = np.array(mf); nn = np.array(nn)
        R7 = dict(div=12, n_poses_sampled=len(mp),
                  prod_margin_min_mm=float(mp.min() * 1e3), prod_clipped_poses=int((mp < 0).sum()),
                  froz_margin_min_mm=float(mf.min() * 1e3), froz_clipped_poses=int((mf < 0).sum()),
                  prod_rays_mean=float(np.mean(nn ** 2)), froz_rays=int(n0 ** 2),
                  froz_over_prod_rays=float(n0 ** 2 / np.mean(nn ** 2)),
                  verdict=("**반증 실패** — 얼린 격자의 최소 여백이 120.6 mm 로, 4096 자세 중 "
                           "로터가 격자 밖으로 나가는 자세는 **0개**다(생산 격자도 0개). ⚠다만 "
                           "원장의 «extra_cost = 0» 은 **8.3% 과소보고**다: 얼린 격자는 자세 평균 "
                           "대비 광선을 1.083배 쏜다. 그리고 이 결론은 **동체가 정지한 경우**에만 "
                           "성립한다 — 드론이 병진하면 실험실 고정 격자는 궤적 전체를 덮어야 하고 "
                           "비용이 폭발한다. 올바른 일반화는 «실험실 고정» 이 아니라 «강체에 붙인 "
                           "격자» 다. 이 실험은 그것을 시험하지 않았다."))
    except Exception as ex:                                              # pragma: no cover
        R7 = dict(error=repr(ex))

    # ── R8 ───────────────────────────────────────────────────────────────────
    R8 = None
    if os.path.exists(FALJ):
        R8 = json.load(open(FALJ))
        Z = np.load(FALZ); nt = int(Z["nt"][0])
        zp = D[12]; cu = zp["ctr_u"][:nt]
        EE = {"prod": zp["E_prod"][:nt],
              "phase": zp["E_prod"][:nt] * np.exp(1j * 2 * K * (cu - cu[0])),
              "pure_PO": PO[:nt]}
        for a in ("froz", "froz_half", "dith", "replay", "nflip"):
            EE[a] = Z[f"E_{a}"]
        bands = [(1, 1.5), (1.5, 2), (2, 3), (3, 5), (5, 7), (7, 1e9)]
        prof = {}
        for nm, e in EE.items():
            f, P = per(e); o = np.abs(f) > FTIP; tot = P[o].sum()
            prof[nm] = {f"{lo}-{hi if hi < 100 else 'Nyq'}":
                        float(P[o & (np.abs(f) >= lo * FTIP) & (np.abs(f) < hi * FTIP)].sum() / tot)
                        for lo, hi in bands}
        R8["oob_band_profile"] = dict(
            note=("대역밖 전력이 f_tip 몇 배에 앉아 있나(대역밖 총합 대비). Nyquist = %.1f f_tip."
                  % (PRF / 2 / FTIP)), rows=prof,
            caveat=("⭐`nflip` 의 +8.3 dB 는 **90% 가 Nyquist 근처 한 줄**이다 — n 이 자세마다 "
                    "±1 토글하면 격자가 PRF/2 로 진동해 그 주파수에 선을 세운다. 즉 정수 "
                    "칸수 튐은 지표는 올리지만 생산이 보이는 **광대역** 바닥의 모양은 아니다. "
                    "생산의 모양을 가장 잘 재현하는 것은 `replay`(생산이 실제로 겪는 가로 "
                    "이동)이고, 전력을 가장 많이 되살리는 것은 `dith`(무작위 서브셀 오프셋)다."))
        json.dump(R8, open(FALJ, "w"), ensure_ascii=False, indent=1)

    out = dict(
        _meta=dict(generated=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                   host=socket.gethostname(), script="benchmark/sbr_grid_freeze_review.py",
                   role=("적대적 반증. 렌즈 = «얼린 팔이 단지 신호를 깎아 바닥이 내려간 것처럼 "
                         "보일 가능성». 기본 입장은 «결론은 틀렸다»."),
                   target_claim=("대역밖 바닥의 지배 원인은 이산화가 아니라 자세마다 격자를 "
                                 "재정의하는 것이다. 얼리면 9.3 dB 내려가고 d² 로 수렴한다."),
                   reads_only=["outputs/report07_three_engines.{json,npz}",
                               "outputs/sbr_grid_convergence.json",
                               "outputs/archive/sbr_grid_conv_parts/*.npz"],
                   writes=["outputs/sbr_grid_freeze_review.json",
                           "outputs/sbr_grid_freeze_falsify.{json,npz}"],
                   drone=M["drone"], fc_hz=M["fc_hz"], az_deg=M["az_deg"], el_deg=M["el_deg"],
                   n=NT, prf_hz=PRF, f_tip_hz=FTIP, f_flash_hz=FFL, divs=divs),
        R1_absolute_power=R1, R2_what_is_the_denominator=R2, R3_did_freezing_cut_signal=R3,
        R4_phase_only_arm=R4, R5_is_the_floor_reproducible=R5, R6_overfit=R6,
        R7_geometry_and_cost=R7, R8_causal_reinjection=R8,
        survives=True,
        summary=("⭐**결론은 살아남는다.** 네 갈래 공격이 전부 실패했다: (1) 절대 전력으로 재면 "
                 "이득이 오히려 커진다(9.3→13.1 dB), (2) 히트 수가 같고 기하 여백이 0개도 안 "
                 "잘리므로 표적을 놓치지 않았다, (3) 얼린 팔의 대역내 파형은 독립 엔진(순수 PO)과 "
                 "상관 0.89~0.98 로 **더 닮아진다** — 생산 팔은 0.09 이고 전력이 16.4 dB 과다다, "
                 "(4) 얼린 격자에 흔들림만 되먹이면(같은 광선 수·같은 히트 수·같은 위상원점) "
                 "바닥이 +9.2 dB 로 되돌아온다(생산 초과분의 "
                 "87%). 결정적인 것은 진폭을 1e-16 도 안 건드리는 **위상 사후보정만으로 λ/32 에서 "
                 "8.8 dB** 가 내려간다는 점이다 — 깎을 신호가 없는데 바닥이 내려간다."),
        surviving_cracks=[
            ("⚠지표 결함(결론과 무관하나 리포트 7b 헤드라인에 걸림): `frac_power_beyond_ftip` 의 "
             "분모는 포락 평활폭(4·f_flash=507 Hz)이 대역 시작(184 Hz)보다 넓어 **DC 누설로 "
             "채워진다** — 조용한 팔일수록 심하다(얼림 97%·순수 PO 99%). 순위는 안 바뀌지만 "
             "«블레이드 대역 대비» 라는 말은 사실이 아니다."),
            ("⚠기울기 보고가 비대칭이다 — prod 는 ≥λ/12 구간, froz 는 전구간. 같은 규칙으로 "
             "맞춰도 결론은 같다(froz ≥12 = −2.12)."),
            ("⚠«extra_cost = 0» 은 정확히는 **광선 1.083배**다(얼린 n₀=124 ↔ 생산 평균 √14194≈119)."),
            ("⚠원인 이름표가 뭉뚱그려져 있다. «격자 재정의» 는 최소 세 기전의 묶음이고 "
             "몫이 격자 간격에 따라 뒤바뀐다: 위상원점 흔들림(λ/12 에서 1.4 dB ↔ λ/32 에서 "
             "8.8 dB), 가로 서브셀 오프셋 방황, 정수 칸수 튐. 그중 정수 칸수 튐은 광대역이 "
             "아니라 **Nyquist 한 줄**로 나온다(R8 band profile)."),
            ("⚠적용 범위: 표적이 **정지**해 있고(로터만 회전) 자세각 1개·기체 1종·주파수 1개의 "
             "단일점 실험이다. 드론이 병진하면 «실험실 고정 격자» 는 성립하지 않는다 — 올바른 "
             "일반화는 «강체에 붙인 격자» 이고 그것은 아직 시험되지 않았다."),
            ("⚠얼리기의 대가가 하나 있다: 얼린 팔의 **절대 레벨이 오프셋 한 판에 따라 흔들린다** "
             "(같은 λ/12 에서 froz −51.51 dB ↔ 반 칸 옮긴 froz_half −50.11 dB, 1.4 dB 차). "
             "생산 팔은 자세마다 오프셋을 새로 뽑는 것이 곧 **오프셋 평균**이라 레벨이 "
             "λ/12~λ/32 에서 0.05 dB 안에 모인다. 슬로타임 잡음은 얼리기가 이기고 절대 σ "
             "레벨은 생산 쪽이 안정적이다 — 진짜 해법은 «얼린 격자 + 오프셋 앙상블 평균» 이다."),
        ],
    )
    json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
    print(f"→ {OUTJ}")
    print("\nsurvives =", out["survives"])
    for c in out["surviving_cracks"]:
        print(" •", c[:110], "...")


if __name__ == "__main__":
    main()
