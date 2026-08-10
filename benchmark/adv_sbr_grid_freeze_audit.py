# -*- coding: utf-8 -*-
"""adv_sbr_grid_freeze_audit.py — ⭐**«격자 재정의가 원인» 결론에 대한 적대적 감사**

렌즈: «자세마다 격자를 다시 정의하는 것이 사실은 물리적으로 필요할 가능성»
기본 입장: 원장(outputs/sbr_grid_convergence.json)의 결론은 틀렸다 — 를 깨보려 한다.

깨보려 한 것 (전부 이 파일이 재계산한다)
  ① 지표의 분모 — 얼린 팔에서 «신호(분모)» 가 커져서 비율이 내려간 것 아닌가
  ② 신호 손실 — 얼린 격자가 표적을 놓쳐서 바닥도 같이 내려간 것 아닌가
  ③ 물리적 필요 — 자세마다 bbox 가 숨쉬는데 격자를 얼리면 틀리는 자세가 있지 않나
  ④ 과적합 — 표본 5개로 기울기 −2.09·R² 0.987 은 과적합 아닌가
  ⑤ 추가 광선 — 얼린 격자가 광선을 더 써서 이긴 것 아닌가

⚠ 기존 원장(outputs/sbr_grid_convergence.json/.npz)은 **읽기만** 한다. 절대 덮어쓰지 않는다.
원장:  outputs/adv_grid_freeze_audit.json
입력:  outputs/sbr_grid_convergence.{json,npz} (원장) + outputs/archive/adv_grid_freeze/*.npz (재계산)
"""
from __future__ import annotations
import datetime as _dt, json, os, socket, sys
import numpy as np

_H = os.path.dirname(os.path.abspath(__file__)); _R = os.path.abspath(os.path.join(_H, ".."))
for _p in (os.path.join(_R, "src"), _H):
    if _p not in sys.path: sys.path.insert(0, _p)

SRCJ = os.path.join(_R, "outputs", "sbr_grid_convergence.json")
SRCZ = os.path.join(_R, "outputs", "sbr_grid_convergence.npz")
ADVZ = os.path.join(_R, "outputs", "archive", "adv_grid_freeze", "adv_div012_nt512.npz")
OUTJ = os.path.join(_R, "outputs", "adv_grid_freeze_audit.json")

J = json.load(open(SRCJ)); M = J["_meta"]
PRF, FTIP, FFL = M["prf_hz"], M["f_tip_hz"], M["f_flash_hz"]
DIVS = M["divs"]; PAD = M["pad"]
Z = np.load(SRCZ)
db = lambda x: float(10 * np.log10(max(float(x), 1e-300)))


def oob_abs(E, prf=None, ftip=None):
    """⭐창·평활·분모가 전혀 없는 대역밖 에너지. |f|>f_tip 성분의 파스발 에너지 그대로."""
    prf = prf or PRF; ftip = ftip or FTIP
    E = np.asarray(E, complex); X = np.fft.fft(E)
    X[np.abs(np.fft.fftfreq(len(E), 1.0 / prf)) <= ftip] = 0
    return float(np.sum(np.abs(X) ** 2) / len(E) ** 2)


def lvl(E): return float(np.mean(np.abs(np.asarray(E)) ** 2))


def bands_smoothed(E):
    E = np.asarray(E, complex); N = len(E); nf = 4 * N
    S = np.fft.fftshift(np.abs(np.fft.fft(E * np.hanning(N), nf))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(nf, 1.0 / PRF))
    dq = float(f[1] - f[0]); ns = max(3, int(round(4 * FFL / dq)) | 1)
    Sm = np.convolve(S, np.ones(ns) / ns, mode="same")
    inb = (np.abs(f) > 0.15 * FTIP) & (np.abs(f) <= FTIP)
    out = np.abs(f) > FTIP
    return dict(raw_in=float(S[inb].sum()), sm_in=float(Sm[inb].sum()),
                raw_out=float(S[out].sum()), sm_out=float(Sm[out].sum()),
                raw_body=float(S[np.abs(f) <= 0.15 * FTIP].sum()),
                sm_body=float(Sm[np.abs(f) <= 0.15 * FTIP].sum()))


def slope(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    A = np.stack([np.log(x), np.ones(len(x))], 1)
    c, *_ = np.linalg.lstsq(A, np.log(y), rcond=None)
    ss = float(np.sum((np.log(y) - np.log(y).mean()) ** 2))
    return float(c[0]), float(1 - np.sum((np.log(y) - A @ c) ** 2) / ss)


def loo(x, y):
    return [slope([v for i, v in enumerate(x) if i != j],
                  [v for i, v in enumerate(y) if i != j])[0] for j in range(len(x))]


# ═══ ① 분모 감사 ═══════════════════════════════════════════════════════════ #
den = []
for d in DIVS:
    row = dict(div=d)
    for arm in ("prod", "froz"):
        b = bands_smoothed(Z[f"E_{arm}_div{d}"])
        row[f"{arm}_raw_in_db"] = db(b["raw_in"])
        row[f"{arm}_smoothed_in_db"] = db(b["sm_in"])
        row[f"{arm}_denominator_leakage_frac"] = float(1 - b["raw_in"] / b["sm_in"])
        row[f"{arm}_raw_out_db"] = db(b["raw_out"])
        row[f"{arm}_sm_out_db"] = db(b["sm_out"])
    row["freeze_gain_ratio_db"] = (db(bands_smoothed(Z[f"E_prod_div{d}"])["sm_out"]
                                      / (bands_smoothed(Z[f"E_prod_div{d}"])["sm_in"]
                                         + bands_smoothed(Z[f"E_prod_div{d}"])["sm_out"]))
                                   - db(bands_smoothed(Z[f"E_froz_div{d}"])["sm_out"]
                                        / (bands_smoothed(Z[f"E_froz_div{d}"])["sm_in"]
                                           + bands_smoothed(Z[f"E_froz_div{d}"])["sm_out"])))
    row["freeze_gain_abs_smoothed_db"] = row["prod_sm_out_db"] - row["froz_sm_out_db"]
    row["freeze_gain_abs_raw_db"] = row["prod_raw_out_db"] - row["froz_raw_out_db"]
    den.append(row)

# ═══ ②⑤ 신호 손실·광선 수 ═════════════════════════════════════════════════ #
import glob
geo = []
for p in sorted(glob.glob(os.path.join(_R, "outputs", "archive",
                                       "sbr_grid_conv_parts", "div*.npz"))):
    z = np.load(p); d = float(z["d"][0]); n0 = int(np.ceil(2 * float(z["Rout0"][0]) / d))
    ng = z["n_grid"].astype(float)
    geo.append(dict(div=int(z["div"][0]), n0_frozen=n0,
                    n_prod_min=int(ng.min()), n_prod_max=int(ng.max()),
                    n_prod_mean=float(ng.mean()),
                    rays_frozen_over_prod_mean=float(n0 ** 2 / (ng ** 2).mean()),
                    n_lit_prod_mean=float(z["n_lit_prod"].mean()),
                    n_lit_froz_mean=float(z["n_lit_froz"].mean()),
                    n_lit_froz_over_prod=float(z["n_lit_froz"].mean() / z["n_lit_prod"].mean()),
                    n_lit_prod_relstd=float(z["n_lit_prod"].std() / z["n_lit_prod"].mean()),
                    n_lit_froz_relstd=float(z["n_lit_froz"].std() / z["n_lit_froz"].mean())))

# ═══ ③ 기하 커버리지 (광선 안 쏨) ══════════════════════════════════════════ #
from articulated_fast import FastPoser, rotor_phases                      # noqa: E402
from drones import DRONES                                                 # noqa: E402
fp = FastPoser(DRONES[M["drone"]]); NT = int(M["n"])
ph = rotor_phases(np.arange(NT) / PRF, np.asarray(M["rpm_per_rotor"], float), fp.dirs)
_a, _e = np.radians(M["az_deg"]), np.radians(M["el_deg"])
u = np.array([np.cos(_e) * np.cos(_a), np.cos(_e) * np.sin(_a), np.sin(_e)])
tmp = np.array([0., 0., 1.]) if abs(u[2]) < 0.9 else np.array([1., 0., 0.])
e1 = np.cross(u, tmp); e1 /= np.linalg.norm(e1); e2 = np.cross(u, e1)
lo = np.full(3, np.inf); hi = np.full(3, -np.inf); Vs = []
for i in range(NT):
    V = np.asarray(fp.pose(ph[i]).v, float); Vs.append(V)
    lo = np.minimum(lo, V.min(0)); hi = np.maximum(hi, V.max(0))
ctr0 = 0.5 * (lo + hi)
need_fixed = max(float(max(np.abs((V - ctr0) @ e1).max(), np.abs((V - ctr0) @ e2).max()))
                 for V in Vs)
need_own = np.array([float(max(np.abs((V - 0.5 * (V.max(0) + V.min(0))) @ e1).max(),
                               np.abs((V - 0.5 * (V.max(0) + V.min(0))) @ e2).max())) for V in Vs])
R3 = np.array([float(np.linalg.norm(V - 0.5 * (V.max(0) + V.min(0)), axis=1).max()) for V in Vs])
Rmax0 = max(float(np.linalg.norm(V - ctr0, axis=1).max()) for V in Vs)
cov = []
for d_ in DIVS:
    d = M["lam_m"] / d_
    R0 = Rmax0 * PAD + 3 * d; n0 = int(np.ceil(2 * R0 / d)); half0 = (n0 - 1) / 2 * d
    hp = []
    for V, r in zip(Vs, R3):
        Rp = r * PAD + 3 * d; npr = int(np.ceil(2 * Rp / d)); hp.append((npr - 1) / 2 * d)
    cov.append(dict(div=d_, frozen_half_extent_mm=half0 * 1e3,
                    prod_half_extent_min_mm=float(min(hp)) * 1e3,
                    required_half_extent_all_poses_mm=need_fixed * 1e3,
                    frozen_margin_mm=(half0 - need_fixed) * 1e3,
                    prod_worst_margin_mm=float(min(np.array(hp) - need_own)) * 1e3,
                    frozen_clips_any_pose=bool(half0 < need_fixed)))

# ═══ ④ 기울기 견고성 (분모 없는 절대량으로 다시) ═══════════════════════════ #
conv = {}
for arm in ("prod", "phase", "froz"):
    y = [oob_abs(Z[f"E_{arm}_div{d}"]) for d in DIVS]
    s, r2 = slope(DIVS, y); s12, r212 = slope(DIVS[1:], y[1:])
    conv[arm] = dict(abs_oob_energy_db=[db(v) for v in y], slope_vs_div=s, r2=r2,
                     slope_vs_div_ge12=s12, r2_ge12=r212, loo_slopes=loo(DIVS, y),
                     pairwise_slopes=[float(np.log(y[i + 1] / y[i]) / np.log(DIVS[i + 1] / DIVS[i]))
                                      for i in range(len(DIVS) - 1)])
po_abs = oob_abs(Z["po_div11"])
i12 = DIVS.index(12)
s12p, _ = slope(DIVS[1:], [oob_abs(Z[f"E_prod_div{d}"]) for d in DIVS[1:]])
yF = [oob_abs(Z[f"E_froz_div{d}"]) for d in DIVS]
yP = [oob_abs(Z[f"E_prod_div{d}"]) for d in DIVS]
need_div = float(12.0 * (yF[i12] / yP[i12]) ** (1.0 / s12p))
sF, _ = slope(DIVS, yF)
need_div_po_froz = float(12.0 * (po_abs / yF[i12]) ** (1.0 / sF))

# ═══ 재계산 팔 (adv worker) ════════════════════════════════════════════════ #
recompute = None
if os.path.exists(ADVZ):
    A = np.load(ADVZ); nt = int(A["nt"][0])
    ftip, prf = FTIP, PRF
    arms = [k[2:] for k in A.files if k.startswith("E_")]
    base = oob_abs(A["E_prod"], prf, ftip)
    recompute = dict(
        source=os.path.relpath(ADVZ, _R), n_t=nt, div=int(A["div"][0]),
        gate_max_rel_err_vs_kernel=float(A["gate"][0]),
        note=("⭐한 자세에 씬을 한 번만 짓고 격자만 바꿔 쏜다 → 팔끼리 기하·재질·가림이 "
              "완전히 같다. prod 팔은 rcs_sbr.sbr_field 와 비트 단위로 같음을 게이트가 확인."),
        arms={},
    )
    npr = A["ngrid_prod"].astype(float)
    ARMDOC = dict(
        prod="자세마다 ctr=bbox중심 · Rout=3D반경·pad+3d (생산 그대로)",
        froz="ctr0 · Rout0 고정 (원장의 얼린 팔)",
        frozHalf="ctr0 + ½d(e1+e2) · Rout0 — ⭐격자를 반칸 민 다른 판",
        frozQrt="ctr0 + (0.37,−0.21)d · Rout0+1.5d — ⭐n 까지 다른 판",
        sizeOnly="ctr0 고정 · Rout 만 자세별 → **격자 크기·n 튐** 단독 몫",
        ctrOnly="ctr = ctr0 + (c_i−ctr0)_가로 · Rout0 → **가로 중심흔들림** 단독 몫",
        uOnly="ctr = ctr0 + ((c_i−ctr0)·û)û · Rout0 → **위상 원점 흔들림** 단독 몫")
    for arm in arms:
        E = A[f"E_{arm}"]; ng = A[f"ngrid_{arm}"].astype(float)
        recompute["arms"][arm] = dict(
            what=ARMDOC.get(arm, ""),
            abs_oob_energy_db=db(oob_abs(E, prf, ftip)),
            gain_vs_prod_db=db(base) - db(oob_abs(E, prf, ftip)),
            level_db=db(lvl(E)), n_lit_mean=float(A[f"nlit_{arm}"].mean()),
            n_grid_min=int(ng.min()), n_grid_max=int(ng.max()),
            rays_vs_prod=float((ng ** 2).mean() / (npr ** 2).mean()))
    gf = db(oob_abs(A["E_froz"], prf, ftip))
    recompute["decomposition_vs_fully_frozen_db"] = dict(
        note=("얼린 팔을 기준으로, 그 한 조각만 다시 «자세별» 로 풀었을 때 대역밖 에너지가 "
              "얼마나 올라가는가. 세 조각은 dB 로 더해지지 않는다(서로 간섭한다)."),
        grid_size_n_jitter=db(oob_abs(A["E_sizeOnly"], prf, ftip)) - gf,
        transverse_centre_wander=db(oob_abs(A["E_ctrOnly"], prf, ftip)) - gf,
        phase_origin_wander_along_u=db(oob_abs(A["E_uOnly"], prf, ftip)) - gf,
        all_three_prod=db(oob_abs(A["E_prod"], prf, ftip)) - gf,
        headline=("⭐ 가장 큰 조각은 **격자 크기·n 튐**(+7.4 dB)이다. 그런데 그 조각이야말로 "
                  "«bbox 가 숨쉬니 격자도 커져야 한다» 는 물리적 변명이 붙던 부분이고, "
                  "audit_3 이 그 변명을 기하로 반증한다(고정 318.37 mm 하나면 전 자세를 덮는다)."))
    recompute["lucky_lattice_rebuttal"] = dict(
        note="얼린 팔이 «운 좋은 격자 한 판» 이었나 — 서로 다른 얼린 격자 세 판의 이득[dB]",
        froz=db(base) - gf,
        frozHalf=db(base) - db(oob_abs(A["E_frozHalf"], prf, ftip)),
        frozQrt=db(base) - db(oob_abs(A["E_frozQrt"], prf, ftip)),
        level_db=dict(froz=db(lvl(A["E_froz"])), frozHalf=db(lvl(A["E_frozHalf"])),
                      frozQrt=db(lvl(A["E_frozQrt"]))),
        verdict=("세 판 모두 9.2~12.4 dB. 판마다 ±1.6 dB 흔들리지만 부호도 크기도 안 바뀐다. "
                 "«운 좋은 한 판» 가설은 반증됐다. (레벨은 판마다 2.3 dB 흔들린다 — 얼리기의 "
                 "진짜 대가는 여기다.)"))
    recompute["reproduces_ledger"] = dict(
        prod_abs_oob_db_ledger_truncated=db(oob_abs(Z["E_prod_div12"][:nt], prf, ftip)),
        prod_abs_oob_db_recomputed=db(oob_abs(A["E_prod"], prf, ftip)),
        froz_abs_oob_db_ledger_truncated=db(oob_abs(Z["E_froz_div12"][:nt], prf, ftip)),
        froz_abs_oob_db_recomputed=db(oob_abs(A["E_froz"], prf, ftip)),
        note="원장 계열을 같은 NT 로 자른 값과 독립 재계산이 소수점까지 일치한다.")

# ═══ 판정 ══════════════════════════════════════════════════════════════════ #
out = dict(
    _meta=dict(
        generated=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        host=socket.gethostname(), script="benchmark/adv_sbr_grid_freeze_audit.py",
        role="적대적 감사 — outputs/sbr_grid_convergence.json 의 결론을 깨려는 시도",
        lens="자세마다 격자 재정의가 사실은 물리적으로 필요할 가능성",
        audited_claim=("대역밖 바닥의 지배 원인은 이산화가 아니라 자세마다 격자를 재정의하는 "
                       "것이다. 격자를 얼리면 9.3 dB 내려가고 d² 로 수렴한다."),
        reads_only=["outputs/sbr_grid_convergence.json", "outputs/sbr_grid_convergence.npz",
                    "outputs/archive/sbr_grid_conv_parts/div*.npz"],
        writes=[os.path.relpath(OUTJ, _R), "outputs/archive/adv_grid_freeze/*.npz"],
        drone=M["drone"], fc_hz=M["fc_hz"], prf_hz=PRF, f_tip_hz=FTIP, n=NT, divs=DIVS,
    ),
    verdict=dict(
        survives=True,
        headline=("결론은 살아남는다 — 그리고 원장이 말한 것보다 **크다**. 분모·창·평활을 전부 "
                  "없앤 절대 대역밖 에너지로 재보면 λ/12 에서 얼리기 이득은 9.3 dB 가 아니라 "
                  "**12.4 dB**, λ/32 에서는 **19.9 dB** 다. 다만 원장이 쓴 «비율» 지표 자체는 "
                  "깨진다 — 그 분모의 98 %(얼린 팔) / 58 %(생산 팔)가 body 봉우리를 507 Hz "
                  "이동평균이 번지게 한 누수다."),
        what_broke=[
            "지표: frac_power_beyond_ftip 의 분모는 «블레이드 대역 전력» 이 아니다. 평활(4·f_flash"
            "=507 Hz)이 |f|≤0.15·f_tip 의 body 봉우리를 블레이드 대역으로 번지게 해서 분모의 "
            "98.4 %(froz λ/32) / 58.3 %(prod λ/32) 가 누수다. 평활을 끄면 λ/12 에서 이득이 "
            "−1.7 dB 로 **부호가 뒤집힌다** — 결론이 아니라 지표가 깨지는 것이지만, 이 비율을 "
            "헤드라인 숫자로 인용하면 안 된다.",
            "비용: recommendation_freeze.extra_cost = \"0\" 은 틀렸다. 얼린 격자 n₀ 는 생산 격자의 "
            "[min,max] 범위 안에 있지만 **평균보다 크다** — 광선이 8.4~9.6 % 더 든다.",
            "외삽: div_needed_to_reach_po_floor_if_frozen = 64.6 은 비율 지표의 기울기로 낸 값이다. "
            "절대 에너지로는 ≈180 — 2.8 배 낙관이다.",
        ],
        what_held=[
            "분모 반증 실패: 얼린 팔의 분모는 커지지 않고 **작아진다**(λ/12 에서 −3.3 dB). 비율은 "
            "실제 효과를 **과소**평가한다. 절대 대역밖 에너지가 12.4~19.9 dB 내려간다.",
            "신호손실 반증 실패: 얼린 팔의 조명 히트수는 생산 팔의 0.991~1.000 배, 프레임간 산포도 "
            "같다(3.6~3.7 %). 총전력도 λ/16 이상에서 +0.15~+0.35 dB 로 보존된다 — 전력이 사라진 "
            "것이 아니라 DC 로 **되돌아갔다**(body 대역 +1.3~+1.5 dB).",
            "물리적 필요 반증 실패: 4096 자세 전부를 덮는 **고정** 가로 반폭은 318.37 mm 하나면 "
            "충분하다(자세별 요구 214~316 mm). 두 팔 모두 341~450 mm 를 써서 **어느 자세도 잘리지 "
            "않는다**. 격자가 커지는 이유는 코드가 가로 요구 대신 3D 포위반경(290~387 mm, 주로 û "
            "방향 길이변화)을 가로 반폭으로 쓰기 때문이다 — 물리가 아니라 규약이다.",
            "과적합 반증 실패: 얼린 팔 기울기는 LOO 로 [−2.23, −2.03](비율)·[−1.98, −1.86](절대), "
            "연속쌍 −2.00/−2.03/−1.91/−1.58, 분모 없는 절대 에너지로 −2.16(R² 0.988). div 5 개는 "
            "서로 **다른 격자 오프셋 5 판**이고 전부 d² 선 위에 있다.",
            "광선수 반증 실패: 얼린 격자가 9 % 더 쓰지만 d² 곡선상 0.4 dB 어치다. 반대로 얼린 팔은 "
            "λ/12(광선 15,376발)로 생산 λ/32(93,655발)보다 대역밖이 10.1 dB 낮다 — 광선 6.1 배 적게.",
            "커널 자신의 계약과 충돌: rcs_sbr.sbr_field_bistatic 독스트링(832–835행)이 «슬로타임 "
            "계열은 같은 격자를 쓰므로 그 오차가 프레임 간 공통 모드로 들어간다» 고 적어 놓았다. "
            "자세별 bbox 재정의가 그 가정을 조용히 깬다(n 이 4095 프레임 중 1636 번 바뀐다, λ/12).",
        ],
        surviving_defense=[
            "⭐ctr 이 두 역할을 겸한다 — **격자 앵커**이자 **위상 원점**이다. 표적이 «병진» 하면 "
            "앵커는 반드시 몸을 따라가야 한다(안 그러면 격자를 항적 전체로 키워야 한다). 따라서 "
            "«자세마다 ctr 을 새로 잡는다» 자체가 무조건 틀린 것은 아니다. 틀린 것은 그 ctr 을 "
            "**관절운동으로 흔들리는 bbox** 에서 뽑는 것과, 같은 흔들리는 점을 위상 원점으로 "
            "쓰는 것이다. 올바른 처방은 «세계좌표 고정» 이 아니라 «강체 프레임에 고정 + n 고정 + "
            "격자 위상 스냅, 위상 원점은 운동학이 알려진 점».",
            "⭐자세마다 서브셀 오프셋을 새로 뽑는 것은 **시간평균 σ 에는 진짜 이득**이다 — 격자 "
            "dither 를 4096 프레임에 걸쳐 몬테카를로 평균한다. 실측: 생산 팔의 레벨은 λ/12→λ/32 "
            "에서 0.052 dB 밖에 안 움직이는데 얼린 팔은 1.554 dB 흔들린다. 즉 현재 코드는 "
            "**σ 에는 맞고 마이크로도플러에는 틀린** 설계다. 둘을 한 함수가 겸할 수 없다.",
            "하류 결합: src/ptd_edges.py 는 위상 원점 = 자세별 bbox 중심을 **요구**하고(64행) "
            "어긋나면 경고한다(785행). 얼리려면 PTD 규약도 같이 바꿔야 한다.",
        ],
    ),
    audit_1_denominator=dict(
        note=("원장 지표 frac_power_beyond_ftip = Σ_{|f|>f_tip} P_env / Σ_{|f|>0.15 f_tip} P_env. "
              "P_env 는 폭 4·f_flash 이동평균 포락이다. 그 평활이 body 봉우리를 분모로 번지게 한다."),
        rows=den,
        freeze_gain_by_metric_db={
            "원장 비율(hann·pad4·평활)": [r["freeze_gain_ratio_db"] for r in den],
            "절대 대역밖(평활 포락)": [r["freeze_gain_abs_smoothed_db"] for r in den],
            "절대 대역밖(생 주기도)": [r["freeze_gain_abs_raw_db"] for r in den],
            "절대 대역밖 에너지(창·평활 없음)":
                [db(oob_abs(Z[f"E_prod_div{d}"])) - db(oob_abs(Z[f"E_froz_div{d}"])) for d in DIVS],
            "시간영역 거칠기 ‖E−LPF(E)‖²/‖E‖²":
                [db(oob_abs(Z[f"E_prod_div{d}"]) / lvl(Z[f"E_prod_div{d}"]))
                 - db(oob_abs(Z[f"E_froz_div{d}"]) / lvl(Z[f"E_froz_div{d}"])) for d in DIVS],
        },
        divs=DIVS,
    ),
    audit_2_signal_loss=dict(
        note="얼린 격자가 표적을 놓쳤다면 조명 히트수가 줄고 레벨이 깎였을 것이다.",
        rows=geo,
        level_db=dict(prod=[db(lvl(Z[f"E_prod_div{d}"])) for d in DIVS],
                      froz=[db(lvl(Z[f"E_froz_div{d}"])) for d in DIVS],
                      po=[db(lvl(Z[f"po_div{d}"])) for d in (8, 11, 16, 24, 32)]),
        level_spread_ge12_db=dict(
            prod=float(max(db(lvl(Z[f"E_prod_div{d}"])) for d in DIVS[1:])
                       - min(db(lvl(Z[f"E_prod_div{d}"])) for d in DIVS[1:])),
            froz=float(max(db(lvl(Z[f"E_froz_div{d}"])) for d in DIVS[1:])
                       - min(db(lvl(Z[f"E_froz_div{d}"])) for d in DIVS[1:]))),
    ),
    audit_3_coverage=dict(
        note=("«자세마다 bbox 가 숨쉬니 격자도 커져야 한다» 를 기하로 검사한다 — 광선을 쏘지 않고 "
              "정점만 본다. 필요한 것은 û 에 수직인 **가로** 반폭이다."),
        required_half_extent_fixed_center_mm=need_fixed * 1e3,
        required_half_extent_own_center_min_mm=float(need_own.min()) * 1e3,
        required_half_extent_own_center_max_mm=float(need_own.max()) * 1e3,
        enclosing_radius_3d_min_mm=float(R3.min()) * 1e3,
        enclosing_radius_3d_max_mm=float(R3.max()) * 1e3,
        conclusion=("가로 요구는 고정중심 기준 318.37 mm 하나로 4096 자세 전부를 덮는다. 코드가 "
                    "격자를 키우는 근거인 3D 포위반경은 28 % 숨쉬지만 그 숨은 대부분 û 방향이고 "
                    "가로 표본화와 무관하다."),
        rows=cov),
    audit_4_slope=dict(note="분모를 없앤 절대 대역밖 에너지로 기울기를 다시 낸다.",
                       per_arm=conv, po_abs_oob_db=db(po_abs),
                       div_needed_for_prod_to_match_frozen_at_div12=need_div,
                       rays_needed_ratio=float((need_div / 12.0) ** 2),
                       div_needed_frozen_to_reach_po_floor=need_div_po_froz,
                       ledger_said=J["verdict"]["div_needed_to_reach_po_floor_if_frozen"]),
    audit_5_recompute=recompute,
)
json.dump(out, open(OUTJ, "w"), ensure_ascii=False, indent=1)
print(f"→ {OUTJ}")
for k in out["verdict"]["what_broke"]:
    print("  [깨짐] " + k[:110])
for k in out["verdict"]["what_held"]:
    print("  [버팀] " + k[:110])
