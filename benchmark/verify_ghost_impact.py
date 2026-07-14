# -*- coding: utf-8 -*-
"""
verify_ghost_impact.py — [E6] **표적 경유 바닥 유령이 탐지·추적을 얼마나 망치는가**
====================================================================================
이미 아는 것(verify_floor_ghost.py, 궤적 중앙 1 스냅샷):
    유령은 표적보다 **+3.53 m 뒤**, **-18.1 dB 약함**, **도플러가 실려 ECA 를 통과**한다.
여기서 하는 것: 그 유령이 **궤적 전체**에서 탐지·추적에 무엇을 하는지 **정량화**한다.

  [A] 두 개의 평행 궤적 — 표적이 날면 유령도 같이 난다. (Rb, f_d) 평면의 궤적 두 개.
  [B] 파형별 분해 — dRb=c/B, df_d=1/T_CPI 로 궤적의 **몇 %에서 유령이 분리되는가**.
  [C] CFAR 오검출 — run_cell(floor_ghost_on=True) 를 궤적 전체에 돌려
      P(유령 셀이 CFAR 를 울림), P(유령이 **별개** 표적으로 찍힘)을 잰다.
  [D] 추적기 관점 — 유령은 **구조적(structural) 오경보**다: 표적과 상관돼 매 프레임 같은
      자리에 다시 나타난다. 랜덤 오경보는 M-of-N 개시로 걸러지지만 유령은 **안 걸러진다**.
      → 랜덤 FA 의 트랙 개시 확률 vs 유령의 트랙 개시 확률을 같은 논리로 계산해 비교.
      → 유령 트랙의 '물리적 그럴듯함'(챔버 안 실제 드론 위치로 설명 가능한가)도 검사.
  [E] 완화 — 유령은 항상 표적보다 뒤(Rb 큼)·약함(-18 dB)·도플러 약간 작음. 챔버에선
      TX/RX/바닥이 **알려져 있다** → 기하 게이트를 칠 수 있는가? 그 게이트가 **진짜 2번째
      드론을 얼마나 지우는가**(오배제 비용)를 몬테카를로로 잰다.

실행:  ~/.venvs/py312/bin/python benchmark/verify_ghost_impact.py
       (σ 프리필만 GPU(SBR), CFAR 는 numpy 병렬)
출력:  outputs/verify_ghost_impact.json  +  outputs/figures/ghost_impact.png
"""
from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.abspath(os.path.join(_HERE, "..", "src"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bistatic_scene import bistatic_params, C0                     # noqa: E402
from geometry import TX, RX, CENTER, SPEED, SPAN, floor_ghost      # noqa: E402
from link_budget import LinkBudget                                 # noqa: E402
from run_min_cell import run_cell, EIRP_DBM, frame_len             # noqa: E402
from scenarios import radial, tangential, waypoint                 # noqa: E402
from waveforms import lte_downlink, nr_downlink, wifi_80211ac      # noqa: E402

OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs", "verify_ghost_impact.json"))
FIG = os.path.abspath(os.path.join(_HERE, "..", "outputs", "figures", "ghost_impact.png"))
DRONE = "mavic4pro"
CHAMBER = (30.0, 20.0, 11.0)

M_CPI = 48            # CPI 프레임 수 (run_min_cell 기본값과 동일)
N_TRIAL = 60          # CFAR 몬테카를로 trial/스냅샷
N_TRAJ = 64           # 기하 궤적 샘플 수 (A/B — 해석적, 싸다)
N_CFAR = 9            # CFAR 를 도는 스냅샷 수 (궤적 등간격 서브샘플)
PFA = 1e-4
N_WORKERS = 16


def waveforms():
    return [("5G NR 100MHz", nr_downlink(bw_hz=100e6, carrier_hz=3.5e9, occupancy="G3")),
            ("WiFi 80MHz", wifi_80211ac(bw_hz=80e6, carrier_hz=5.2e9)),
            ("LTE 20MHz", lte_downlink(bw_hz=20e6, carrier_hz=1.8e9, occupancy="G3"))]


SCEN = {"radial": radial, "tangential": tangential, "waypoint": waypoint}


def res_cells(wf, M=M_CPI):
    """파형 → (dRb=c/B [m], df_d=1/T_CPI [Hz], 거리셀 c/fs [m])."""
    Lf = frame_len(wf)
    return dict(d_rb_m=C0 / wf.bw_hz, d_fd_hz=wf.fs_hz / (M * Lf),
                cell_rb_m=C0 / wf.fs_hz, t_cpi_s=M * Lf / wf.fs_hz)


# --------------------------------------------------------------------------- #
#  [A][B] 두 평행 궤적 + 파형별 분해 판정 (해석 기하 — GPU/CFAR 불필요)
# --------------------------------------------------------------------------- #
def ab_tracks():
    out = {}
    for sname, fn in SCEN.items():
        pos, vel = fn(TX, RX, CENTER, speed=SPEED, span=SPAN, n=N_TRAJ)
        per_wf = {}
        for wname, wf in waveforms():
            rc = res_cells(wf)
            rows = []
            for p, v in zip(pos, vel):
                b = bistatic_params(TX, RX, p, v, wf.carrier_hz)
                g = floor_ghost(TX, RX, p, v, wf.carrier_hz, pol="V")
                rows.append((b["Rb"], b["fd"], g["rb_m"], g["fd"],
                             20 * np.log10(g["amp_ratio"] + 1e-30)))
            arr = np.array(rows)                       # [n, 5]
            rb_t, fd_t, rb_g, fd_g, gdb = arr.T
            sep = rb_g - rb_t                          # 유령은 항상 뒤 (>0 이어야)
            dfd = fd_g - fd_t
            r_res = np.abs(sep) > rc["d_rb_m"]         # 거리축 분해
            d_res = np.abs(dfd) > rc["d_fd_hz"]        # 도플러축 분해
            per_wf[wname] = dict(
                **rc,
                rb_true=rb_t.tolist(), fd_true=fd_t.tolist(),
                rb_ghost=rb_g.tolist(), fd_ghost=fd_g.tolist(),
                sep_m=sep.tolist(), dfd_hz=dfd.tolist(), ghost_db=gdb.tolist(),
                sep_mean=float(sep.mean()), sep_min=float(sep.min()), sep_max=float(sep.max()),
                dfd_mean=float(dfd.mean()), dfd_absmax=float(np.abs(dfd).max()),
                ghost_db_mean=float(gdb.mean()),
                sep_over_drb_mean=float((sep / rc["d_rb_m"]).mean()),
                dfd_over_dfdres_mean=float(np.abs(dfd / rc["d_fd_hz"]).mean()),
                frac_range_resolved=float(r_res.mean()),
                frac_doppler_resolved=float(d_res.mean()),
                frac_resolved=float((r_res | d_res).mean()),
                frac_merged=float((~(r_res | d_res)).mean()))
        out[sname] = per_wf
    return out


# --------------------------------------------------------------------------- #
#  [C] CFAR — 궤적 전체 (병렬 워커)
# --------------------------------------------------------------------------- #
def _cfar_worker(args):
    """워커: (시나리오, 파형이름, 스냅샷 idx, pos, vel) → 유령/표적 검출 통계."""
    os.environ["SIONNA2_NO_GPU"] = "1"                 # σ 는 캐시 조회만(프리필 완료 가정)
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[k] = "4"
    sname, wname, i, p, v = args
    wf = dict(waveforms())[wname]
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    r = run_cell(wf, DRONE, np.array([p]), np.array([v]), lb, M=M_CPI, N=N_TRIAL,
                 pfa=PFA, seed0=1000 * i + 7, floor_ghost_on=True)
    g = r["ghost"]
    return dict(scen=sname, wf=wname, i=int(i),
                pd=r["pd"], scr=r["scr_mean"],
                ghost_p_det=g["p_det"], ghost_p_false=g["p_false"],
                ghost_margin_db=g["margin_db"],
                sep_m=g["sep_m"], d_rb_m=g["d_rb_m"], resolved=bool(g["resolved"]),
                bins_apart=list(g["bins_apart"]),
                rb_true=float(r["state"].tau * C0), fd_true=float(r["state"].fd),
                rb_ghost=g["rb_m"], fd_ghost=g["fd"], ghost_db=g["amp_db"])


def c_cfar(idx_by_scen):
    jobs = []
    for sname, fn in SCEN.items():
        pos, vel = fn(TX, RX, CENTER, speed=SPEED, span=SPAN, n=N_TRAJ)
        for i in idx_by_scen:
            for wname, _ in waveforms():
                jobs.append((sname, wname, i, pos[i].tolist(), vel[i].tolist()))
    print(f"  CFAR 셀 {len(jobs)}개 (시나리오 {len(SCEN)} × 스냅샷 {len(idx_by_scen)} × 파형 3, "
          f"M={M_CPI}, N={N_TRIAL}, Pfa={PFA:g}) — 워커 {N_WORKERS}개")
    with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
        rows = list(ex.map(_cfar_worker, jobs))
    return rows


# --------------------------------------------------------------------------- #
#  [D] 추적기 관점 — 구조적 오경보 vs 랜덤 오경보
# --------------------------------------------------------------------------- #
def _fa_worker(args):
    """랜덤 오경보(잡음) 셀당 발화율 측정 — 유령/표적/0-도플러 능선을 제외한 셀들.
    (E1 의 Pfa 교정과 별개로, **트래커 비교에 쓸 랜덤 FA 기준선**을 이 하네스에서 직접 잰다.)"""
    os.environ["SIONNA2_NO_GPU"] = "1"
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[k] = "4"
    wname, p, v, n_trial = args
    wf = dict(waveforms())[wname]
    from passive_process import make_cpi, ECACanceller, range_doppler, ca_cfar_2d
    from channel import AnalyticChannel
    from link_budget import link_terms
    from geometry import chamber_window
    lb = LinkBudget(eirp_dbm=EIRP_DBM)
    ch = AnalyticChannel()
    fs = wf.fs_hz
    st = ch.state(TX, RX, np.array(p), np.array(v), wf.carrier_hz, DRONE)
    lt = link_terms(lb, st.lam, st.sigma_m2, st.R1, st.R2, st.L, wf.bw_hz)
    txp = float(np.sqrt(np.mean(np.abs(wf.tx) ** 2)))
    ref_frame = wf.ref.astype(complex) / txp
    tx_frame = wf.tx.astype(complex) / txp
    Lf = frame_len(wf)
    if Lf > len(tx_frame):
        pad = np.zeros(Lf - len(tx_frame), complex)
        ref_frame = np.concatenate([ref_frame, pad]); tx_frame = np.concatenate([tx_frame, pad])
    n_range, n_taps = chamber_window(wf)
    bw_corr = float(np.sqrt(wf.bw_hz / fs))
    dpi = lt["dpi_amp"] * bw_corr
    a_tgt = lt["a_tgt"] * bw_corr
    g = floor_ghost(TX, RX, np.array(p), np.array(v), wf.carrier_hz, pol="V")
    tgt_det, ref_cpi = make_cpi(ref_frame, M_CPI, fs, st.tau, st.fd, a_tgt=a_tgt, dpi_amp=0.0,
                                clutter=(), abs_noise=True, noise_var=0.0,
                                ghosts=((g["tau"], g["fd"], a_tgt * g["amp_ratio"]),))
    dpi_det, _ = make_cpi(tx_frame, M_CPI, fs, 0.0, 0.0, a_tgt=0.0, dpi_amp=dpi,
                          clutter=(), abs_noise=True, noise_var=0.0)
    surv_det = tgt_det + dpi_det
    can = ECACanceller(ref_cpi, n_taps)
    Ncpi = len(surv_det)
    fa, cells_free, n_maps = 0, 0, 0
    for k in range(n_trial):
        rng = np.random.default_rng(50000 + k)
        noise = (rng.standard_normal(Ncpi) + 1j * rng.standard_normal(Ncpi)) / np.sqrt(2.0)
        Rb, f_d, rd = range_doppler(can.cancel(surv_det + noise), ref_cpi, fs, M_CPI, n_range=n_range)
        det, _, _ = ca_cfar_2d(rd, pfa=PFA)
        zd = int(np.argmin(np.abs(f_d))); det[zd, :] = False
        mask = np.ones_like(det)                       # 유효(=랜덤 FA 를 셀 수 있는) 셀
        mask[max(0, zd - 1):zd + 2, :] = False
        ri = int(np.argmin(np.abs(Rb - st.tau * C0))); di = int(np.argmin(np.abs(f_d - st.fd)))
        gi = int(np.argmin(np.abs(Rb - g["rb_m"]))); gd = int(np.argmin(np.abs(f_d - g["fd"])))
        for (a, b) in ((di, ri), (gd, gi)):            # 표적/유령 주변 ±3 셀 제외
            mask[max(0, a - 3):a + 4, max(0, b - 3):b + 4] = False
        fa += int((det & mask).sum()); cells_free += int(mask.sum()); n_maps += 1
    return dict(wf=wname, n_maps=n_maps, fa=fa, cells=cells_free,
                pfa_emp=fa / max(cells_free, 1), map_cells=int(det.size),
                fa_per_map=fa / max(n_maps, 1))


def _binom_at_least(k, n, p):
    from math import comb
    return float(sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


def is_merged(r):
    """이 셀에서 유령이 표적과 **같은 검출**로 뭉쳤는가 (거리·도플러 빈 차이 ≤1).
    ⚠ 뭉친 셀에서는 run_cell 의 ghost_p_det(유령셀 ±1 CFAR 히트)가 **표적 피크 자체**를 세므로
      '유령이 검출됐다'는 뜻이 아니다. 이 리포트는 뭉친 셀과 분리된 셀을 항상 구분해 보고한다."""
    br, bd = r["bins_apart"]
    return abs(br) <= 1 and abs(bd) <= 1


def d_tracker(rows, fa_rows, tracks):
    """M-of-N 트랙 개시 논리로 '구조적 vs 랜덤' 오경보를 같은 잣대로 비교."""
    out = {"init_logic": "3-of-5", "per_wf": {}}
    for wname, wf in waveforms():
        rr = [r for r in rows if r["wf"] == wname]
        fa = next(f for f in fa_rows if f["wf"] == wname)
        res = [r for r in rr if not is_merged(r)]                       # 분리된(=유령이 별개 셀) 셀만
        p_ghost = (float(np.mean([r["ghost_p_det"] for r in res])) if res else 0.0)
        p_false = float(np.mean([r["ghost_p_false"] for r in rr]))     # **별개 표적**으로 찍힐 확률
        p_cell = fa["pfa_emp"]                                          # 랜덤 FA 의 셀당 발화율
        # 랜덤 FA 가 트랙이 되려면 **같은 셀(±1 게이트, 9셀)** 에서 5프레임 중 3번 떠야 한다.
        p_gate = min(1.0, 9 * p_cell)
        rand_track_per_cell = _binom_at_least(3, 5, p_gate)
        n_cells = fa["map_cells"]
        out["per_wf"][wname] = dict(
            # p_ghost_frame: **분리된 셀에서만** 잰 유령셀 CFAR 발화율(뭉친 셀은 표적 피크를 세므로 제외)
            p_ghost_frame=p_ghost, n_cells_resolved=len(res), n_cells_total=len(rr),
            p_ghost_false_frame=p_false, pfa_emp_cell=p_cell,
            fa_per_map=fa["fa_per_map"], map_cells=n_cells,
            p_track_ghost=_binom_at_least(3, 5, p_ghost),
            p_track_ghost_separate=_binom_at_least(3, 5, p_false),
            p_track_random_per_cell=rand_track_per_cell,
            n_random_tracks_per_window=float(rand_track_per_cell * n_cells),
            ghost_margin_db=(float(np.mean([r["ghost_margin_db"] for r in res])) if res else None))
    # 유령 트랙의 '그럴듯함' — 표적 궤적과의 상관 + 2차 다항 잔차(운동학적 매끄러움)
    sm = {}
    for sname, per_wf in tracks.items():
        t = per_wf["5G NR 100MHz"]
        rb_t = np.array(t["rb_true"]); rb_g = np.array(t["rb_ghost"])
        fd_t = np.array(t["fd_true"]); fd_g = np.array(t["fd_ghost"])
        k = np.arange(len(rb_t))

        def resid(y):                                   # 2차 다항 적합 잔차 RMS (매끄러움)
            c = np.polyfit(k, y, 2)
            return float(np.sqrt(np.mean((y - np.polyval(c, k)) ** 2)))
        sm[sname] = dict(corr_rb=float(np.corrcoef(rb_t, rb_g)[0, 1]),
                         corr_fd=float(np.corrcoef(fd_t, fd_g)[0, 1]),
                         resid_rb_true_m=resid(rb_t), resid_rb_ghost_m=resid(rb_g),
                         resid_fd_true_hz=resid(fd_t), resid_fd_ghost_hz=resid(fd_g))
    out["ghost_track_smoothness"] = sm
    return out


def d_phantom(fc=3.5e9, vmax=6.0):
    """유령의 (Rb, f_d) 를 만들어낼 수 있는 **실제 드론 위치가 챔버 안에 있는가?**
    있으면 트래커는 '물리적으로 불가능하다'는 이유로 유령을 버릴 수 없다."""
    b = bistatic_params(TX, RX, CENTER, (0, 0, 0), fc)
    v = np.array(radial(TX, RX, CENTER, n=3)[1][1])
    g = floor_ghost(TX, RX, np.array(CENTER, float), v, fc, pol="V")
    bt = bistatic_params(TX, RX, CENTER, v, fc)
    # 챔버 격자(드론이 있을 수 있는 공간: 벽에서 1 m, 높이 1~9 m)
    xs = np.arange(1.0, 29.01, 0.25); ys = np.arange(1.0, 19.01, 0.25); zs = np.arange(1.0, 9.01, 0.25)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    tx = np.array(TX); rx = np.array(RX)
    R1 = np.linalg.norm(P - tx, axis=1); R2 = np.linalg.norm(P - rx, axis=1)
    Rb = R1 + R2 - np.linalg.norm(rx - tx)
    d_rb = C0 / 98.28e6                                  # 5G 거리분해능
    sel = np.abs(Rb - g["rb_m"]) < d_rb / 2              # 유령 Rb 와 같은 거리셀에 있는 위치들
    n_sel = int(sel.sum())
    res = dict(fc=float(fc), rb_ghost=g["rb_m"], rb_true=float(bt["Rb"]),
               fd_ghost=g["fd"], fd_true=float(bt["fd"]), d_rb_m=float(d_rb),
               n_positions_in_ghost_cell=n_sel,
               volume_frac=float(sel.mean()))
    if n_sel:
        Q = P[sel]
        # 그 위치에서 f_d = f_d(유령) 을 내려면 필요한 **최소 속도** (v ∥ (u1+u2) 일 때)
        u1 = (tx - Q) / np.linalg.norm(tx - Q, axis=1, keepdims=True)
        u2 = (rx - Q) / np.linalg.norm(rx - Q, axis=1, keepdims=True)
        s = np.linalg.norm(u1 + u2, axis=1)
        lam = C0 / fc
        vmin = np.abs(g["fd"]) * lam / np.maximum(s, 1e-9)
        ok = vmin <= vmax
        d_tgt = np.linalg.norm(Q - np.array(CENTER), axis=1)
        res.update(n_positions_kinematically_ok=int(ok.sum()),
                   min_speed_needed_ms=float(vmin.min()),
                   nearest_phantom_dist_m=float(d_tgt[ok].min()) if ok.any() else None,
                   phantom_exists=bool(ok.any()), vmax_ms=float(vmax))
    return res


# --------------------------------------------------------------------------- #
#  [E] 완화 — 기하 게이트가 가능한가, 그 비용은 얼마인가
# --------------------------------------------------------------------------- #
def e_mitigation(fc=3.5e9, bw=98.28e6, n_mc=200000, seed=3):
    """유령 게이트: '어떤 검출 B 가 검출 A 보다 (a) Rb 가 sep 구간만큼 뒤 (b) 진폭이 amp 구간만큼
    약하면 → 유령으로 보고 버린다'. 게이트 폭은 **챔버 안 모든 표적 위치**에서 유령이 취할 수
    있는 (sep, amp) 범위로 정한다(TX/RX/바닥을 알기 때문에 계산 가능).
    비용 = 그 게이트가 **진짜 두 번째 드론**을 지울 확률(무작위 드론쌍 몬테카를로)."""
    rng = np.random.default_rng(seed)
    tx = np.array(TX); rx = np.array(RX); L = float(np.linalg.norm(rx - tx))
    lam = C0 / fc
    d_rb = C0 / bw

    def rand_pos(n):                                   # 드론이 있을 수 있는 공간 (벽 1 m, z 1~9 m)
        return np.stack([rng.uniform(1, 29, n), rng.uniform(1, 19, n), rng.uniform(1, 9, n)], 1)

    def rand_vel(n, speed=SPEED):
        d = rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        return d * speed

    # --- 게이트 폭: 챔버 전체(그리고 quiet zone) 에서 유령이 만드는 (sep, dfd, amp) 분포
    n_g = 20000
    Pg, Vg = rand_pos(n_g), rand_vel(n_g)
    sep, amp, dfd = np.empty(n_g), np.empty(n_g), np.empty(n_g)
    for i in range(n_g):
        b = bistatic_params(tx, rx, Pg[i], Vg[i], fc)
        g = floor_ghost(tx, rx, Pg[i], Vg[i], fc, pol="V")
        sep[i] = g["rb_m"] - b["Rb"]
        amp[i] = 20 * np.log10(g["amp_ratio"] + 1e-30)
        dfd[i] = g["fd"] - b["fd"]
    q = lambda a, p: float(np.quantile(a, p))
    gate = dict(sep_lo=q(sep, 0.005), sep_hi=q(sep, 0.995),
                amp_lo=q(amp, 0.005), amp_hi=q(amp, 0.995),
                sep_med=q(sep, 0.5), amp_med=q(amp, 0.5),
                dfd_lo=q(dfd, 0.005), dfd_hi=q(dfd, 0.995), dfd_med=q(dfd, 0.5),
                sep_min=float(sep.min()), sep_max=float(sep.max()),
                amp_min=float(amp.min()), amp_max=float(amp.max()))

    # --- 비용: 진짜 드론 2대(무작위 위치·속도) 가 게이트에 걸릴 확률
    #     (A = 더 강한/앞선 검출, B = 뒤쪽 검출. 진폭비는 두 드론의 σ 차이를 모르므로
    #      **기하만 쓰는 게이트**(sep+dfd)와 **진폭까지 쓰는 게이트**를 따로 잰다.
    #      진폭은 1/(R1²R2²) 기하 감쇠 + σ 동일 가정 — σ 차이는 별도 스윕.)
    A = rand_pos(n_mc); B = rand_pos(n_mc)
    VA, VB = rand_vel(n_mc), rand_vel(n_mc)

    def meas(P, V):
        R1 = np.linalg.norm(P - tx, axis=1); R2 = np.linalg.norm(P - rx, axis=1)
        Rb = R1 + R2 - L
        u1 = (tx - P) / R1[:, None]; u2 = (rx - P) / R2[:, None]
        fd = np.sum(V * (u1 + u2), axis=1) / lam
        amp_db = -20 * np.log10(R1 * R2)               # 진폭 ∝ 1/(R1·R2) (σ 동일 가정)
        return Rb, fd, amp_db

    RbA, fdA, ampA = meas(A, VA)
    RbB, fdB, ampB = meas(B, VB)
    dRb = RbB - RbA; dfd2 = fdB - fdA; damp = ampB - ampA
    in_sep = (dRb >= gate["sep_lo"]) & (dRb <= gate["sep_hi"])
    in_dfd = (dfd2 >= gate["dfd_lo"]) & (dfd2 <= gate["dfd_hi"])
    in_amp = (damp >= gate["amp_lo"]) & (damp <= gate["amp_hi"])
    # 애초에 분해되지 않는 쌍(같은 거리셀)은 게이트와 무관하게 트래커가 못 나눔 → 제외하고 본다
    resolvable = np.abs(dRb) > d_rb
    cost = dict(
        n_mc=int(n_mc), d_rb_m=float(d_rb),
        p_pair_resolvable=float(resolvable.mean()),
        p_gate_sep_only=float(in_sep.mean()),
        p_gate_sep_dfd=float((in_sep & in_dfd).mean()),
        p_gate_sep_dfd_amp=float((in_sep & in_dfd & in_amp).mean()),
        p_gate_sep_dfd_amp_given_resolvable=float(
            (in_sep & in_dfd & in_amp & resolvable).sum() / max(resolvable.sum(), 1)))
    # --- **조건부 게이트**: 유령의 sep/amp 는 표적 **위치만**의 함수다(속도 무관).
    #     그리고 우리는 A 의 Rb 를 **측정**했다 → 표적은 그 등Rb 타원체 위에 있다.
    #     그 타원체 조각(챔버 안) 위에서만 sep/amp 범위를 잡으면 게이트가 훨씬 좁아진다.
    #     (챔버라서 TX/RX/바닥을 알기 때문에 가능한 계산.)
    xs = np.arange(1.0, 29.01, 0.4); ys = np.arange(1.0, 19.01, 0.4); zs = np.arange(1.0, 9.01, 0.4)
    G = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).reshape(-1, 3)
    gR1 = np.linalg.norm(G - tx, axis=1); gR2 = np.linalg.norm(G - rx, axis=1)
    gRb = gR1 + gR2 - L
    rx_img = rx.copy(); rx_img[2] = -rx_img[2]
    gR2f = np.linalg.norm(G - rx_img, axis=1)
    gsep = gR2f - gR2                                   # sep = R2f - R2 (속도 무관!)
    dvec = rx_img - G
    th = np.arctan2(np.linalg.norm(dvec[:, :2], axis=1), np.abs(dvec[:, 2]))
    from geometry import _fresnel_floor
    gam = np.array([_fresnel_floor(t, fc, "V") for t in th])
    gamp = 20 * np.log10(gam * gR2 / gR2f + 1e-30)
    edges = np.arange(0.0, 60.001, d_rb)               # Rb 를 거리분해능 폭으로 빈닝
    bidx = np.clip(np.digitize(gRb, edges) - 1, 0, len(edges) - 2)
    cond = []
    for b in range(len(edges) - 1):
        m = bidx == b
        if m.sum() < 20:
            continue
        cond.append(dict(rb_lo=float(edges[b]), rb_hi=float(edges[b + 1]), n=int(m.sum()),
                         sep_lo=float(np.quantile(gsep[m], 0.005)),
                         sep_hi=float(np.quantile(gsep[m], 0.995)),
                         amp_lo=float(np.quantile(gamp[m], 0.005)),
                         amp_hi=float(np.quantile(gamp[m], 0.995))))
    # 조건부 게이트의 비용 — 같은 몬테카를로 쌍에 Rb_A 별 게이트를 적용
    lo = np.full(n_mc, np.nan); hi = np.full(n_mc, np.nan)
    alo = np.full(n_mc, np.nan); ahi = np.full(n_mc, np.nan)
    for cbin in cond:
        m = (RbA >= cbin["rb_lo"]) & (RbA < cbin["rb_hi"])
        lo[m], hi[m] = cbin["sep_lo"], cbin["sep_hi"]
        alo[m], ahi[m] = cbin["amp_lo"], cbin["amp_hi"]
    valid = ~np.isnan(lo)
    in_c = valid & (dRb >= lo) & (dRb <= hi) & (damp >= alo) & (damp <= ahi)
    cost["p_gate_conditional"] = float(in_c[valid].mean())
    cost["p_gate_conditional_given_resolvable"] = float(
        (in_c & resolvable)[valid].sum() / max((resolvable & valid).sum(), 1))
    cost["cond_gate_width_at_rb22_m"] = next(
        (c2["sep_hi"] - c2["sep_lo"] for c2 in cond if c2["rb_lo"] <= 22.0 < c2["rb_hi"]), None)

    # 그림용 실제 표본(진짜 드론쌍 800개, 지어낸 점이 아니라 위 몬테카를로에서 뽑음)
    k = rng.choice(n_mc, 800, replace=False)
    sample = dict(dRb=dRb[k].tolist(), damp=damp[k].tolist(),
                  ghost_sep=sep[:800].tolist(), ghost_amp=amp[:800].tolist())
    return dict(gate=gate, cost=cost, cond_gate=cond, sample=sample)


# --------------------------------------------------------------------------- #
#  그림
# --------------------------------------------------------------------------- #
def figure(tracks, rows, mit):
    import matplotlib
    matplotlib.use("Agg")
    import vizstyle
    vizstyle.use_korean()
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, axs = plt.subplots(2, 2, figsize=(13.2, 9.0), constrained_layout=True)
    wf_names = [n for n, _ in waveforms()]
    colors = {"5G NR 100MHz": "#d62728", "WiFi 80MHz": "#1f77b4", "LTE 20MHz": "#2ca02c"}

    # (a) 두 평행 궤적 — 5G, 3 시나리오
    ax = axs[0, 0]
    scol = {"radial": "#d62728", "tangential": "#1f77b4", "waypoint": "#7f3fbf"}
    for sname, per in tracks.items():
        t = per["5G NR 100MHz"]
        ax.plot(t["rb_true"], t["fd_true"], "-", color=scol[sname], lw=2, label=f"{sname} target")
        ax.plot(t["rb_ghost"], t["fd_ghost"], "--", color=scol[sname], lw=2, alpha=0.75,
                label=f"{sname} floor ghost")
    t0 = tracks["radial"]["5G NR 100MHz"]
    ax.add_patch(Rectangle((t0["rb_true"][0], t0["fd_true"][0]), t0["d_rb_m"], t0["d_fd_hz"],
                           fc="none", ec="k", lw=1.4))
    ax.annotate(f"5G resolution cell\n{t0['d_rb_m']:.1f} m x {t0['d_fd_hz']:.1f} Hz",
                xy=(t0["rb_true"][0] + t0["d_rb_m"], t0["fd_true"][0]),
                xytext=(8, -28), textcoords="offset points", fontsize=8.5,
                arrowprops=dict(arrowstyle="->", lw=0.9))
    ax.set_xlabel("Bistatic range Rb [m]"); ax.set_ylabel("Doppler f_d [Hz]")
    ax.set_title("(a) Target and floor-ghost move together: two parallel tracks\n"
                 "(5G NR 100 MHz; ghost trails the target by ~3.5 m at all times)", fontsize=10)
    ax.legend(fontsize=7.5, ncol=2); ax.grid(alpha=0.3)

    # (b) 분해 여부 — sep / dRb 및 |dfd| / df_res
    ax = axs[0, 1]
    for wname in wf_names:
        t = tracks["waypoint"][wname]
        s = np.array(t["sep_m"]) / t["d_rb_m"]
        ax.plot(s, color=colors[wname], lw=2,
                label=f"{wname}  (range-resolved {100*t['frac_range_resolved']:.0f}% of track)")
    ax.axhline(1.0, color="k", ls=":", lw=1.4)
    ax.text(1, 1.05, "resolution limit  sep = dRb", fontsize=8.5)
    ax.set_xlabel("Trajectory snapshot (waypoint scenario)")
    ax.set_ylabel("Ghost-target separation / dRb")
    ax.set_title("(b) Does the ghost resolve? sep = 3.5 m is fixed; dRb = c/B decides\n"
                 "(above the line: ghost becomes a SEPARATE detection)", fontsize=10)
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # (c) CFAR — 유령이 **별개 표적**으로 찍힐 확률 + 궤적 중 뭉친 비율
    ax = axs[1, 0]
    w = 0.26
    scens = list(SCEN)
    x = np.arange(len(scens))
    for k, wname in enumerate(wf_names):
        pf_, merged_ = [], []
        for s in scens:
            rr = [r for r in rows if r["scen"] == s and r["wf"] == wname]
            pf_.append(np.mean([r["ghost_p_false"] for r in rr]))
            merged_.append(np.mean([is_merged(r) for r in rr]))
        ax.bar(x + (k - 1) * w, merged_, w * 0.9, color=colors[wname], alpha=0.20, hatch="//",
               edgecolor=colors[wname],
               label=f"{wname}: ghost MERGED into the target cell (fraction of track)")
        ax.bar(x + (k - 1) * w, pf_, w * 0.5, color=colors[wname],
               label=f"{wname}: ghost detected as a SEPARATE target (P per CPI)")
    ax.set_xticks(x); ax.set_xticklabels(scens)
    ax.set_ylabel("Probability / fraction"); ax.set_ylim(0, 1.35)
    ax.set_title("(c) CFAR over the whole trajectory (measured, N=%d trials/snapshot)\n"
                 "solid = ghost becomes a separate false target; hatched = ghost hides inside "
                 "the target cell" % N_TRIAL, fontsize=10)
    ax.legend(fontsize=6.5, ncol=1, loc="upper left"); ax.grid(alpha=0.3, axis="y")

    # (d) 완화 게이트와 그 비용
    ax = axs[1, 1]
    g = mit["gate"]; c = mit["cost"]; sp = mit["sample"]
    ax.scatter(sp["dRb"], sp["damp"], s=6, color="#888", alpha=0.35,
               label="real 2nd drone (Monte-Carlo, %d shown)" % len(sp["dRb"]))
    ax.scatter(sp["ghost_sep"], sp["ghost_amp"], s=7, color="#d62728", alpha=0.5,
               label="floor ghost (all chamber positions)")
    ax.add_patch(Rectangle((g["sep_lo"], g["amp_lo"]), g["sep_hi"] - g["sep_lo"],
                           g["amp_hi"] - g["amp_lo"], fc="none", ec="#d62728",
                           lw=1.8, ls="--", label="ghost gate (99% of ghosts)"))
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlim(-12, 14); ax.set_ylim(-32, 12)
    ax.set_xlabel("Range offset of 2nd detection, Rb_B - Rb_A [m]")
    ax.set_ylabel("Amplitude offset [dB]")
    ax.set_title("(d) Geometric mitigation gate (needs TX/RX/floor - known in chamber)\n"
                 "cost: deletes %.1f%% of REAL 2nd-drone pairs (%.1f%% with the Rb-conditional gate)"
                 % (100 * c["p_gate_sep_dfd_amp_given_resolvable"],
                    100 * c["p_gate_conditional_given_resolvable"]), fontsize=10)
    ax.legend(fontsize=8, loc="lower right"); ax.grid(alpha=0.3)

    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=130)
    plt.close(fig)
    print(f"\n그림 → {os.path.relpath(FIG, os.path.join(_HERE, '..'))}")


# --------------------------------------------------------------------------- #
def main():
    print("=" * 84)
    print("[E6] 표적 경유 바닥 유령이 탐지·추적을 얼마나 망치는가 — 궤적 전체 정량화")
    print("=" * 84)

    # ---- [A][B] 궤적 + 분해
    tracks = ab_tracks()
    print("\n[A] 두 평행 궤적 (유령은 표적을 그림자처럼 따라다닌다) — 5G 기준")
    for sname, per in tracks.items():
        t = per["5G NR 100MHz"]
        print(f"  {sname:11s} Rb(표적) {min(t['rb_true']):5.1f}~{max(t['rb_true']):5.1f} m  "
              f"유령 sep {t['sep_min']:.2f}~{t['sep_max']:.2f} m (평균 {t['sep_mean']:.2f})  "
              f"df_d {t['dfd_mean']:+.1f} Hz  유령진폭 {t['ghost_db_mean']:+.1f} dB")

    print("\n[B] 파형별 분해 여부 (dRb=c/B, df_d=1/T_CPI) — 궤적의 몇 %에서 분리되는가")
    print(f"  {'시나리오':11s} {'파형':14s} {'dRb[m]':>7} {'df_d[Hz]':>8} "
          f"{'거리분해':>8} {'도플러분해':>10} {'둘중하나':>8}")
    for sname, per in tracks.items():
        for wname, t in per.items():
            print(f"  {sname:11s} {wname:14s} {t['d_rb_m']:7.1f} {t['d_fd_hz']:8.1f} "
                  f"{100*t['frac_range_resolved']:7.0f}% {100*t['frac_doppler_resolved']:9.0f}% "
                  f"{100*t['frac_resolved']:7.0f}%")

    # ---- [C] CFAR  (--reuse 면 지난 실행의 측정치를 재사용 — 재계산 40분 절약)
    idx = np.linspace(0, N_TRAJ - 1, N_CFAR).astype(int).tolist()
    reuse = "--reuse" in sys.argv and os.path.exists(OUT)
    if reuse:
        with open(OUT) as f:
            prev = json.load(f)
        rows, fa_rows = prev["C_cfar"], prev["fa_rows"]
        print(f"\n[C] CFAR — 지난 실행 측정치 재사용 (--reuse, {len(rows)} 셀)")
    else:
        # σ 프리필 (GPU) — CFAR 스냅샷 전부
        from channel import sbr_sigma_prefill
        reqs = []
        for sname, fn in SCEN.items():
            pos, vel = fn(TX, RX, CENTER, speed=SPEED, span=SPAN, n=N_TRAJ)
            for i in idx:
                for _, wf in waveforms():
                    b = bistatic_params(TX, RX, pos[i], vel[i], wf.carrier_hz)
                    reqs.append((DRONE, wf.carrier_hz, b["u1"], b["u2"], 8.0, 5))
        print(f"\n[σ] SBR 프리필 (GPU) — {len(reqs)} 요청")
        sbr_sigma_prefill(reqs)
        print("\n[C] CFAR 오검출 — 궤적 전체 (측정)")
        rows = c_cfar(idx)
        pos, vel = radial(TX, RX, CENTER, speed=SPEED, span=SPAN, n=N_TRAJ)
        mid = idx[N_CFAR // 2]       # ⚠ σ 캐시가 채워진 스냅샷이어야 한다(프리필 인덱스)
        fa_jobs = [(w, pos[mid].tolist(), vel[mid].tolist(), 40) for w, _ in waveforms()]
        with ProcessPoolExecutor(max_workers=3) as ex:
            fa_rows = list(ex.map(_fa_worker, fa_jobs))

    print(f"  {'시나리오':11s} {'파형':14s} {'Pd(표적)':>8} {'뭉침(궤적%)':>11} "
          f"{'P(별개 표적)':>12} {'유령 임계여유*':>14}")
    for sname in SCEN:
        for wname, _ in waveforms():
            rr = [r for r in rows if r["scen"] == sname and r["wf"] == wname]
            res = [r for r in rr if not is_merged(r)]
            mg = (f"{np.mean([r['ghost_margin_db'] for r in res]):+9.1f} dB" if res else "   (뭉침)")
            print(f"  {sname:11s} {wname:14s} {np.mean([r['pd'] for r in rr]):8.2f} "
                  f"{100*np.mean([is_merged(r) for r in rr]):10.0f}% "
                  f"{np.mean([r['ghost_p_false'] for r in rr]):12.2f} {mg:>14}")
    print("  * 유령 임계여유 = 유령셀 진폭 / CFAR 임계 [dB], **분리된 셀에서만**. 뭉친 셀에서는")
    print("    '유령셀'이 표적 피크와 같은 셀이라 그 수치가 유령이 아니라 표적을 재게 된다.")

    # ---- [D] 추적기
    print("\n[D] 추적기 관점 — 구조적 오경보 vs 랜덤 오경보")
    D = d_tracker(rows, fa_rows, tracks)
    for wname, d in D["per_wf"].items():
        mg = "n/a" if d["ghost_margin_db"] is None else f"{d['ghost_margin_db']:+.1f} dB"
        print(f"  {wname:14s} 유령이 별개 표적으로 찍힐 확률 {d['p_ghost_false_frame']:.2f}/CPI → "
              f"3-of-5 유령 트랙개시 {d['p_track_ghost_separate']:.3f}   |   랜덤 FA 셀당 "
              f"{d['pfa_emp_cell']:.2e} → 3-of-5 랜덤 트랙 기대수 "
              f"{d['n_random_tracks_per_window']:.2e}  (분리셀 유령여유 {mg})")
    ph = d_phantom()
    D["phantom"] = ph
    print(f"  유령이 앉은 (Rb,f_d) 셀을 설명하는 **실제 드론 위치**가 챔버 안에 "
          f"{ph['n_positions_in_ghost_cell']}개 (속도 <= {ph.get('vmax_ms')} m/s 로 가능한 것 "
          f"{ph.get('n_positions_kinematically_ok')}개) → 유령은 물리적으로 그럴듯하다"
          f" (가장 가까운 것은 진짜 표적에서 {ph.get('nearest_phantom_dist_m'):.1f} m).")
    for sname, s in D["ghost_track_smoothness"].items():
        print(f"  {sname:11s} corr(Rb) {s['corr_rb']:+.4f}  잔차(2차적합) 표적 "
              f"{s['resid_rb_true_m']:.3f} m vs 유령 {s['resid_rb_ghost_m']:.3f} m "
              f"→ 유령 트랙도 매끄럽다(운동학 필터로 못 버림)")

    # ---- [E] 완화
    print("\n[E] 완화 — 기하 게이트와 그 비용")
    mit = e_mitigation()
    g, c = mit["gate"], mit["cost"]
    print(f"  챔버 전 위치에서 유령의 범위: sep {g['sep_lo']:.2f}~{g['sep_hi']:.2f} m "
          f"(중앙 {g['sep_med']:.2f}), 진폭 {g['amp_lo']:.1f}~{g['amp_hi']:.1f} dB "
          f"(중앙 {g['amp_med']:.1f}), df_d {g['dfd_lo']:+.1f}~{g['dfd_hi']:+.1f} Hz")
    print(f"  게이트 비용(무작위 드론 2대 몬테카를로, n={c['n_mc']}): "
          f"진짜 2번째 드론이 게이트에 걸릴 확률 = {100*c['p_gate_sep_dfd_amp']:.2f}% "
          f"(거리분해되는 쌍만 보면 {100*c['p_gate_sep_dfd_amp_given_resolvable']:.2f}%)")
    print(f"  **조건부 게이트**(측정한 Rb_A 의 등Rb 타원체 위에서만 sep/진폭 범위를 잡음): "
          f"Rb≈22 m 에서 sep 폭 {c['cond_gate_width_at_rb22_m']:.2f} m "
          f"→ 오배제 {100*c['p_gate_conditional']:.2f}% "
          f"(거리분해되는 쌍만 {100*c['p_gate_conditional_given_resolvable']:.2f}%)")

    figure(tracks, rows, mit)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(dict(config=dict(M=M_CPI, N=N_TRIAL, pfa=PFA, drone=DRONE,
                                   n_traj=N_TRAJ, cfar_idx=idx, eirp_dbm=EIRP_DBM,
                                   speed=SPEED, span=SPAN, TX=list(TX), RX=list(RX),
                                   CENTER=list(CENTER)),
                       A_B_tracks=tracks, C_cfar=rows, D_tracker=D,
                       E_mitigation=mit, fa_rows=fa_rows),
                  f, ensure_ascii=False, indent=1, default=float)
    print(f"→ {os.path.relpath(OUT, os.path.join(_HERE, '..'))}")


if __name__ == "__main__":
    main()
