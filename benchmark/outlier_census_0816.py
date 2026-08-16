# -*- coding: utf-8 -*-
"""
outlier_census_0816.py — ⭐원장 **전 칸** 튐(자세 이상치) 진단
=============================================================

■ 왜 있나
    2026-08-16 깊이 축 판정에서 드러났다 — R13 의 «−60° 에서 깊이 3 이면 리듬이
    86.6 → 32.4 % 로 무너진다» 는 자세 8192 개 중 **단 하나**(#3399) 때문이었다.
    그 자세를 빼면 두 판이 85.5 대 85.2 % 로 같다. 즉 **자세 하나가 헤드라인을
    뒤집을 수 있다.** 그 사고를 다시 안 내려면 튐 진단이 상시 잣대여야 한다.
    depth_axis_verdict_0816 의 census 는 **짝에 쓰인 43 칸**만 봤고 잣대도 isolation
    하나였다. 이 스크립트는 원장 **모든 칸**(뜰 때마다 현재 행 수 — _meta.ledger_state)에
    일곱 갈래 잣대를 돌린다.

■ 잣대 (각각 왜 필요한지는 _meta.metric_defs_ko 에 한 줄씩)
    ① isolation           최대 ÷ 둘째        — 혼자 튀었나, 여럿이 함께 섰나
    ② top1_over_median    중앙 대비 최대     — 얼마나 큰가 (크다고 다 튐은 아니다)
    ③ share_top1_x/​top8_x 상위 k 자세 전력 몫 — 잣대가 몇 자세를 재고 있나
    ④ sym4_mismatch·flash_recur  로터 대칭 짝·날개 통과 주기 되풀이 — 구조인가
    ⑤ neighbor_jump       이웃 자세 급변      — 대역폭이 허용하는 매끄러움을 깼나
    ⑥ npaths_z·tail_p     그 자세의 경로 수   — 계산 자체가 그 자세에서 달랐나
    ⑦ 영향(replace-one)   그 자세 하나를 이웃 평균으로 갈아 끼우면 헤드라인이 얼마나 움직이나

■ 문턱 — ⛔임의 숫자 금지
    · 비율 잣대: 원장 **자기 분포의 꼬리**에서 딴다. log10 위 Tukey 울타리
      (안 = Q3+1.5·IQR, 밖 = Q3+3·IQR). 값·개수를 thresholds 에 그대로 싣는다.
    · 영향 잣대: «쏠림»(맨 위 자세의 영향 ÷ 둘째·죄 없는 자세의 영향)의 울타리 **와**
      프로젝트 자신의 격자 산포 밴드(depth_axis_verdict_0816 의 앙각별 밴드) **둘 다**
      넘어야 «튐» 이다.
      격자 밴드는 «격자를 옆으로 옮겨 재면 이만큼 움직인다» 는 계통 폭이라,
      그보다 크게 움직이면 자세 하나가 계통 오차보다 세다는 뜻이다.
    · 퇴화 칸(에코 0 · f_tip=0 인 −90° · AC/DC 수치 바닥 · 자세 결측)은 문턱을
      만드는 표본에서 **뺀다** — 안 빼면 꼬리가 퇴화 칸으로 오염된다.

■ 원장 (읽기 전용 · ⛔GPU 0 · sionna.rt/mitsuba 임포트 없음)
    outputs/elevation_sweep_md.{json,npz}   병합 원장 (⚠살아 있다 — 행 수·시각은 _meta.ledger_state)
    outputs/elev_sweep_shards/*.npz         자세별 경로 수(npaths·idx)

■ 굽는 것
    outputs/outlier_census_0816.json

실행
    cd /workspace/sionna
    PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python benchmark/outlier_census_0816.py
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import re

import numpy as np

import build_md_atlas as A                                             # noqa: E402
import depth_axis_verdict_0816 as D                                    # noqa: E402

ROOT = A.ROOT
SHD = os.path.join(ROOT, "outputs", "elev_sweep_shards")
OUTJ = os.path.join(ROOT, "outputs", "outlier_census_0816.json")

PRF = A.PRF
NEAR_FLOOR = 1e-11          # AC/DC 수치 바닥 (프로젝트 규약 · depth_axis 와 같은 값)
NO_MOTION = A.NO_MOTION_ACDC
RNG = np.random.default_rng(20260816)
N_CONTROL = 12              # 죄 없는 자세를 갈아 끼우는 대조 횟수
#: 경로 수 «꼬리» 로 볼 양쪽 꼬리 확률 — 관행 1 %. 우연 기대치를 summary 에 함께 적어 교정한다.
NPATH_TAIL = 0.01


# ═══════════════════════════════════════════════════════════════════════════
# 0. 잣대
# ═══════════════════════════════════════════════════════════════════════════
def tukey(vals, log=True):
    """분포의 꼬리에서 문턱을 딴다 — Tukey 울타리(안 Q3+1.5·IQR · 밖 Q3+3·IQR)."""
    v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
    if log:
        v = v[v > 0]
        if v.size < 8:
            return None
        w = np.log10(v)
    else:
        if v.size < 8:
            return None
        w = v
    q1, q3 = np.percentile(w, [25, 75])
    iqr = q3 - q1
    inn, out = q3 + 1.5 * iqr, q3 + 3.0 * iqr
    f = (lambda z: float(10 ** z)) if log else float
    return dict(n=int(v.size), scale="log10" if log else "linear",
                q25=round(f(q1), 6), q50=round(f(float(np.median(w))), 6),
                q75=round(f(q3), 6), iqr_dex=round(float(iqr), 6),
                inner_fence=round(f(inn), 6), outer_fence=round(f(out), 6),
                n_over_inner=int((w > inn).sum()), n_over_outer=int((w > out).sum()))


#: ⭐빗살 대비가 «백색 널 자리» 라고 볼 폭 [dB] — depth_axis_verdict_0816.COMB_NULL_DB 와 같은 값.
#  이 안에서 수가 움직이면 «빗살 없음» 이라는 **읽기**는 안 바뀐다 → 판정을 뒤집지 못한다.
COMB_NULL_DB = D.COMB_NULL_DB


def headline(E, ffl, ft):
    """헤드라인 넷 — 리듬 몫 · 빗살 대비 · 요동 전력 · 상한 위 몫."""
    share, null, above, degen = A.rhythm_share(E, ffl, ft)
    comb = A.comb_contrast_db(E, ffl, ft)
    x = np.asarray(E, complex)
    x = x - x.mean()
    p = float(np.mean(np.abs(x) ** 2))
    return dict(rhythm_pct=(None if share is None else float(share)),
                comb_db=(None if comb is None else float(comb)),
                moving_power_db=(None if p <= 0 else float(10 * np.log10(p))),
                above_ceiling_pct=(None if above is None else float(above)),
                rhythm_null_pct=(None if null is None else float(null)),
                rhythm_degenerate=bool(degen))


def replace_pose(E, i):
    """⭐그 자세를 **삭제하지 않고** 이웃 평균으로 갈아 끼운다 — 표집 간격을 안 깬다.

    삭제(마스킹)는 표본 간격을 깨서 스펙트럼 자체를 바꾼다. 갈아 끼우기는 격자를
    지키므로 «그 자세 하나가 얼마나 끌었나» 를 깨끗하게 잰다. 두 방법을 함께 낸다.
    """
    y = np.array(E, complex, copy=True)
    n = y.size
    y[i] = 0.5 * (E[(i - 1) % n] + E[(i + 1) % n])
    return y


def drop_pose(E, idx):
    m = np.ones(np.size(E), bool)
    m[np.asarray(idx, int)] = False
    return np.asarray(E, complex)[m]


def dd(a, b):
    return None if (a is None or b is None) else float(b - a)


def shard_npaths_map(arm: str, el: float):
    """샤드에서 «자세 번호 → 경로 수» 를 모은다. 없으면 None."""
    fs = sorted(glob.glob(f"{SHD}/{arm}_el{el:+.0f}_*.npz"))
    if not fs:
        return None
    idx, npa = [], []
    for f in fs:
        z = np.load(f)
        if "idx" in z.files and "npaths" in z.files:
            idx.append(np.asarray(z["idx"]))
            npa.append(np.asarray(z["npaths"]))
        z.close()
    if not idx:
        return None
    i = np.concatenate(idx)
    v = np.concatenate(npa).astype(float)
    m = {}
    for a, b in zip(i.tolist(), v.tolist()):
        m[int(a)] = b
    return m


# ═══════════════════════════════════════════════════════════════════════════
# 1. 인용 추적 — «이 팔이 어디에 쓰이고 있나»
# ═══════════════════════════════════════════════════════════════════════════
TOKEN = re.compile(r"(?:sionna|ours)[A-Za-z0-9_.]*")
#: 판정을 싣는 파일들 — 여기서 인용되면 «판정에 쓰이는 칸» 이다
JUDGE_PAT = ("verdict", "falsify", "switch_factorial", "frame_completion",
             "audit", "adv_", "atlas_index", "carrier_transition", "recheck")


def usage_index(arms: set[str]) -> dict:
    files = []
    for pat in ("outputs/*.json", "docs/*.md", "docs/**/*.md", "reports/*.ipynb",
                "reports/**/*.ipynb", "decks/**/*.py", "benchmark/*.py", "*.ipynb"):
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)
    files = sorted(set(files))
    hits: dict[str, list[str]] = {a: [] for a in arms}
    for f in files:
        if os.path.getsize(f) > 40_000_000:
            continue
        try:
            txt = open(f, "r", errors="ignore").read()
        except Exception:
            continue
        found = set(TOKEN.findall(txt)) & arms
        rel = os.path.relpath(f, ROOT)
        for a in found:
            hits[a].append(rel)
    return hits


def is_judge(path: str) -> bool:
    b = os.path.basename(path).lower()
    return (path.startswith("reports/") or path.startswith("docs/")
            or path.startswith("decks/") or any(p in b for p in JUDGE_PAT))


# ═══════════════════════════════════════════════════════════════════════════
# 2. 본체
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    J, Z = A.J, A.Z
    rows = J["rows"]
    arms = sorted({r["engine"] for r in rows})
    cite = usage_index(set(arms))

    cells = []
    for ri, r in enumerate(rows):
        arm, el = r["engine"], float(r["el_deg"])
        key = f"{arm}/el{el:+.0f}"
        E = np.asarray(Z[key], complex)
        n = E.size
        x = E - E.mean()
        a = np.abs(x)
        p_ac = float(np.mean(a ** 2))
        p_tot = float(np.mean(np.abs(E) ** 2))
        acdc = (p_ac / p_tot) if p_tot > 0 else 0.0
        rates = A.arm_rates(arm)
        ffl = rates["f_flash_hz"]
        ft = A.f_tip_at(rates, el)
        cfg = D.parse_arm(arm) or {}
        n_zero = int(np.count_nonzero(E == 0))
        n_miss = int(r.get("n_missing") or 0)

        # ── 퇴화 판정 — 튐과 **구별해서** 따로 단다 ─────────────────────────
        degen, mute = [], False
        if not np.any(E):
            degen.append("zero_echo")
            mute = True
        else:
            if (0 < n_zero < n) or (0 < n_miss < n):
                degen.append("incomplete")
            if acdc < NO_MOTION:
                degen.append("no_motion")
                mute = True
            elif acdc < NEAR_FLOOR:
                degen.append("near_numeric_floor")
                mute = True
        if ft <= 1e-6:
            degen.append("f_tip_zero_nadir")     # ⭐퇴화지만 «튐이냐» 는 여전히 물을 수 있다

        c = dict(
            cell=key, arm=arm, el_deg=el, ledger_row=ri, n_poses=n,
            range_m=r["range_m"], max_depth=r["max_depth"], spp=r["spp"],
            physics=r["physics"], az_deg=r["az_deg"], grid_div=r["grid_div"],
            fc_hz=r["fc_hz"], airframe=(cfg.get("airframe") or A.DRONE_DEFAULT),
            combo=cfg.get("combo"), f_tip_hz=round(ft, 1), f_flash_hz=round(ffl, 3),
            ledger_level_db=r["level_db"], ac_over_dc=float(f"{acdc:.4g}"),
            n_zero_samples=n_zero, n_missing=n_miss,
            degenerate=degen, mute=mute,
            cited_files_n=len(cite.get(arm, [])),
            cited_in_judgment_n=sum(1 for f in cite.get(arm, []) if is_judge(f)),
            cited_examples=sorted(cite.get(arm, []),
                                  key=lambda f: (not is_judge(f), f))[:6],
            #: ⚠«sionna» · «ours» 는 팔 이름이면서 라이브러리·일반 낱말이라 인용 수가 부풀려진다
            cited_count_unreliable=bool(arm in ("sionna", "ours")),
        )

        if mute or not np.any(a):              # 잴 것이 없다 — 튐 진단 자체가 성립 안 한다
            c["gradeable"] = False
            c["in_threshold_sample"] = False
            c["grade"] = "퇴화"
            c["why_ko"] = ("AC 가 통째로 0 — 잴 것이 없다" if not np.any(a) else
                           "AC/DC 가 수치 바닥 — 움직이는 것이 없어 «튐» 이 정의되지 않는다")
            c["reasons"] = []
            cells.append(c)
            continue

        srt = np.sort(a)[::-1]
        ip = int(np.argmax(a))
        med = float(np.median(a))
        pw = a ** 2
        tot = float(pw.sum())

        # ① 고립도 ─ 최대 ÷ 둘째
        iso = float(srt[0] / srt[1]) if srt[1] > 0 else float("inf")
        # ② 중앙 대비 배수
        t1m = float(srt[0] / med) if med > 0 else float("inf")
        t2m = float(srt[1] / med) if med > 0 else float("inf")
        # ③ 상위 k 전력 몫 (균등 몫 대비 배수 — 1 이면 «고르게 퍼졌다»)
        s1 = float(pw[ip] / tot * n)
        s8 = float(np.sort(pw)[::-1][:8].sum() / tot * n / 8.0)
        # ④-a 로터 4 회 대칭 짝 (depth_axis 정의 유지)
        sym = [float(a[(ip + q * (n // 4)) % n] / med) for q in range(4)] if med > 0 else None
        sym_mis = (float(sym[0] / max(sym[1:])) if (sym and max(sym[1:]) > 0) else None)
        # ④-b 날개 통과 주기 되풀이 — 구조적 플래시라면 T=PRF/f_flash 마다 다시 선다
        T = PRF / ffl
        rec = []
        for m2 in (1, 2, 3, 4, -1, -2, -3, -4):
            cpos = int(round(ip + m2 * T))
            if 0 <= cpos < n:
                w = a[max(cpos - 2, 0):min(cpos + 3, n)]
                if w.size:
                    rec.append(float(w.max()))
        recur = (float(a[ip] / max(rec)) if (rec and max(rec) > 0) else None)
        # ⑤ 이웃 급변 — 신호는 f_tip 으로 대역제한되어 있으니 «한 표본 델타» 는 물리가 아니다
        nb = float(np.median(a[[(ip + d) % n for d in (-3, -2, -1, 1, 2, 3)]]))
        jump = float(a[ip] / nb) if nb > 0 else float("inf")
        # 칸 자신의 꼬리로 뽑은 «높은 자세» 집합
        la = np.log10(a[a > 0])
        q1, q3 = np.percentile(la, [25, 75])
        hi_line = (10 ** (q3 + 3.0 * (q3 - q1)) if q3 > q1 else float(a.max()) * 1.001)
        hi = np.where(a > hi_line)[0]
        hi_share = float(pw[hi].sum() / tot) if hi.size else 0.0
        hi_jump = None
        if hi.size:
            jj = [a[i] / np.median(a[[(i + d) % n for d in (-3, -2, -1, 1, 2, 3)]])
                  for i in hi]
            hi_jump = float(np.median([v for v in jj if np.isfinite(v)]))
        # ⑥ 경로 수
        npm = shard_npaths_map(arm, el)
        np_at = np_med = np_z = np_rar = np_share = None
        if npm and ip in npm:
            v = np.asarray(list(npm.values()), float)
            np_at = float(npm[ip])
            np_med = float(np.median(v))
            mad = float(np.median(np.abs(v - np_med)))
            if mad <= 0:                        # 경로 수가 거의 한 값에 몰려 있다
                iqr = float(np.subtract(*np.percentile(v, [75, 25])))
                mad = iqr / 1.349 if iqr > 0 else 0.0
            np_z = (float((np_at - np_med) / (1.4826 * mad)) if mad > 0 else None)
            #: ⭐MAD 가 0 인 칸(경로 수가 거의 상수)에서도 «그 자세만 다르다» 를 잡는 잣대 —
            #  양쪽 꼬리 확률 min(P(X ≤ v), P(X ≥ v)). 값이 여러 개로 퍼진 칸에서 «그 값 자체가
            #  드물다» 를 세면 아무 자세나 드물어지므로, **꼬리**로 센다.
            np_share = float(min((v <= np_at).mean(), (v >= np_at).mean()))
            np_rar = float(-np.log10(max(np_share, 1.0 / max(v.size, 1))))

        c.update(dict(
            gradeable=True,                     # 잴 수 있다 (퇴화 깃발은 따로 단다)
            in_threshold_sample=not bool(degen),  # ⭐문턱 표본에서는 퇴화 칸을 뺀다
            argmax_pose=ip, median_abs_ac=float(f"{med:.4g}"),
            isolation=round(iso, 4) if np.isfinite(iso) else None,
            top1_over_median=round(t1m, 3), top2_over_median=round(t2m, 3),
            share_top1_x=round(s1, 3), share_top8_x=round(s8, 3),
            sym4_over_median=[round(v, 3) for v in sym] if sym else None,
            sym4_mismatch=None if sym_mis is None else round(sym_mis, 3),
            flash_recur=None if recur is None else round(recur, 3),
            neighbor_jump=round(jump, 3) if np.isfinite(jump) else None,
            n_hi_poses=int(hi.size), hi_power_share=round(hi_share, 5),
            hi_expected_flashes=round(n / T, 1),
            hi_count_over_flashes=(round(float(hi.size) / (n / T), 3) if hi.size else 0.0),
            hi_neighbor_jump_med=None if hi_jump is None else round(hi_jump, 2),
            npaths_at_spike=np_at, npaths_median=np_med,
            npaths_z=None if np_z is None else round(np_z, 2),
            npaths_tail_p=None if np_share is None else round(np_share, 5),
            npaths_rarity=None if np_rar is None else round(np_rar, 3),
        ))

        # ⑦ 영향 — 그 자세 하나를 갈아 끼우면 헤드라인이 얼마나 움직이나
        MK = ("rhythm_pct", "comb_db", "moving_power_db", "above_ceiling_pct")
        base = headline(E, ffl, ft)
        rank = np.argsort(a)[::-1]
        rep1 = headline(replace_pose(E, ip), ffl, ft)
        drp1 = headline(drop_pose(E, [ip]), ffl, ft)
        i2 = int(rank[1])
        rep2 = headline(replace_pose(E, i2), ffl, ft)          # ⭐둘째 자세 대조
        rep8 = E.copy()
        for i8 in sorted(rank[:8].tolist()):
            rep8 = replace_pose(rep8, int(i8))
        rp8 = headline(rep8, ffl, ft)
        # 대조 — 죄 없는 자세(중앙 순위)를 같은 방법으로 갈아 끼운다
        mid = rank[n // 4: 3 * n // 4]
        ctrl = [headline(replace_pose(E, int(i)), ffl, ft)
                for i in RNG.choice(mid, size=min(N_CONTROL, mid.size), replace=False)]

        def _sp(k):
            v = [abs(dd(base[k], q[k])) for q in ctrl if dd(base[k], q[k]) is not None]
            return None if not v else float(max(v))

        d_top = {k: dd(base[k], rep1[k]) for k in MK}
        d_2nd = {k: dd(base[k], rep2[k]) for k in MK}
        d_ctl = {k: _sp(k) for k in MK}

        def _dom(k):
            """⭐그 자세가 얼마나 «혼자» 끌었나 — 맨 위 자세의 영향 ÷ (둘째 자세 · 죄 없는 자세)의 영향.

            1 이면 맨 위 자세가 특별할 것 없다(구조적 플래시는 여럿이 같은 크기로 끈다).
            크면 그 자세 하나가 잣대를 끌고 있다. ⭐칸마다 자기 대조군을 쓰므로 임의 숫자가 없다.
            """
            t = d_top.get(k)
            if t is None:
                return None
            ref = [abs(v) for v in (d_2nd.get(k), d_ctl.get(k)) if v is not None]
            ref = max(ref) if ref else 0.0
            if ref <= 0:
                return None if abs(t) <= 0 else float("inf")
            return float(abs(t) / ref)

        c["impact"] = dict(
            base={k: (None if base[k] is None else round(base[k], 4)) for k in MK},
            replace_one={f"d_{k}": _r(d_top[k]) for k in MK},
            drop_one={f"d_{k}": _r(dd(base[k], drp1[k])) for k in MK},
            replace_runnerup={f"d_{k}": _r(d_2nd[k]) for k in MK},
            replace_top8={f"d_{k}": _r(dd(base[k], rp8[k])) for k in MK},
            innocent_control_max_abs={f"d_{k}": _r(d_ctl[k]) for k in MK},
            dominance={k: (None if _dom(k) is None else
                           (None if not np.isfinite(_dom(k)) else round(_dom(k), 3)))
                       for k in MK},
            dominance_inf=[k for k in MK if _dom(k) is not None and not np.isfinite(_dom(k))],
            runnerup_pose=i2, n_control=len(ctrl),
            rhythm_null_pct=_r(base["rhythm_null_pct"]),
            rhythm_degenerate=base["rhythm_degenerate"])
        cells.append(c)

    # ── 2-2. 문턱 — 퇴화 칸을 뺀 표본의 꼬리에서 딴다 ────────────────────────
    G = [c for c in cells if c.get("in_threshold_sample")]
    GRADED = [c for c in cells if c.get("gradeable")]
    TH = {
        "isolation": tukey([c["isolation"] for c in G]),
        "top1_over_median": tukey([c["top1_over_median"] for c in G]),
        "share_top1_x": tukey([c["share_top1_x"] for c in G]),
        "share_top8_x": tukey([c["share_top8_x"] for c in G]),
        "sym4_mismatch": tukey([c["sym4_mismatch"] for c in G]),
        "flash_recur": tukey([c["flash_recur"] for c in G]),
        "neighbor_jump": tukey([c["neighbor_jump"] for c in G]),
        "npaths_abs_z": tukey([abs(c["npaths_z"]) for c in G if c.get("npaths_z") is not None],
                              log=False),
        "npaths_rarity": tukey([c["npaths_rarity"] for c in G
                                if c.get("npaths_rarity") is not None], log=False),
    }
    if TH["npaths_rarity"]:
        TH["npaths_rarity"]["note_ko"] = (
            "⚠이 값은 −log10(그 경로 수를 가진 자세의 몫)이라 위로 log10(자세 수) ≈ 3.9 에서 "
            "막힌다. 바깥 울타리가 그 천장보다 높아 아무 칸도 못 넘으므로 **안쪽 울타리**를 쓴다.")
    MKEYS = ("rhythm_pct", "comb_db", "moving_power_db", "above_ceiling_pct")
    #: ⭐쏠림 문턱은 **네 잣대를 한 표본으로 모아** 딴다. 잣대마다 따로 뜨면 리듬처럼 퍼진
    #  분포에서 문턱이 수만 배로 튀어 아무것도 못 잡는다. 그리고 «움직임이 아예 없는 칸» 은
    #  작은 수 ÷ 작은 수라 비율이 요동치므로, |Δ| 가 그 잣대 중앙값 **위**인 절반에서만 딴다.
    pool = []
    for k in MKEYS:
        vv = [(abs(c["impact"]["replace_one"][f"d_{k}"]), c["impact"]["dominance"][k])
              for c in G if c["impact"]["replace_one"].get(f"d_{k}") is not None
              and c["impact"]["dominance"].get(k)]
        if not vv:
            continue
        med = float(np.median([x[0] for x in vv]))
        pool += [b for a_, b in vv if a_ > med]
        TH[f"dominance_{k}"] = tukey([b for _, b in vv], log=True)
        TH[f"abs_d_{k}"] = tukey([a_ for a_, _ in vv], log=True)
    TH["dominance_pooled"] = tukey(pool, log=True)
    TH["dominance_pooled"]["basis_ko"] = (
        "네 헤드라인 잣대의 쏠림 값을 한 표본으로 모으고, 각 잣대에서 |Δ| 가 중앙값 위인 "
        "절반만 남긴 뒤 log10 위 Tukey 울타리를 땄다 — 등급에 쓰는 선은 이 하나다.")

    # 무작위 잡음 판(같은 길이)에서 고립도가 어디까지 올라가나 — 두 번째 독립 잣대
    null_iso = {}
    for nn in sorted({c["n_poses"] for c in GRADED}):
        v = []
        for _ in range(4000):
            z = (RNG.standard_normal(nn) + 1j * RNG.standard_normal(nn))
            s = np.sort(np.abs(z - z.mean()))[::-1]
            v.append(s[0] / s[1])
        v = np.asarray(v)
        null_iso[str(nn)] = dict(p50=round(float(np.percentile(v, 50)), 4),
                                 p99=round(float(np.percentile(v, 99)), 4),
                                 p999=round(float(np.percentile(v, 99.9)), 4),
                                 max=round(float(v.max()), 4), n_draws=4000)

    # ── 2-3. 등급 ───────────────────────────────────────────────────────────
    band_ac = D.GRID_BAND_AC_DB
    band_rh = D.GRID_BAND_RHYTHM_PP_BY_EL
    band_cb = D.GRID_BAND_COMB_DB_BY_EL
    for c in cells:
        if not c.get("gradeable"):
            continue
        R, big, watch = [], [], []
        imp, dom = c["impact"]["replace_one"], c["impact"]["dominance"]
        el = c["el_deg"]

        # ── ⓐ 영향 — 정본 잣대. «자세 하나가 헤드라인을 끄나» ────────────────
        #    쏠림(dominance)이 꼬리 울타리 밖이고, 움직인 폭이 그 앙각의 격자 밴드보다 크면 튐.
        dline = TH["dominance_pooled"]["outer_fence"]
        for kk, bnd, unit in (("rhythm_pct", band_rh.get(el), "%p"),
                              ("moving_power_db", band_ac.get(el), "dB"),
                              ("comb_db", band_cb.get(el), "dB"),
                              ("above_ceiling_pct", D.GRID_BAND_ABOVE_PP_GLOBAL, "%p")):
            if kk == "rhythm_pct" and c["impact"]["rhythm_degenerate"]:
                continue                      # −90° 는 «상한 위» 잣대가 퇴화 — 영향으로 안 센다
            if kk == "above_ceiling_pct" and c["impact"]["rhythm_degenerate"]:
                continue
            v = imp.get(f"d_{kk}")
            dv = dom.get(kk)
            if v is None:
                continue
            inf = kk in c["impact"]["dominance_inf"]
            over_dom = inf or (dv is not None and dv > dline)
            if not over_dom:
                continue
            tag = ("대조군이 0" if inf else f"쏠림 {dv:.0f}×")
            R.append(f"자세 하나로 {kk} {v:+.3g}{unit} · {tag} (쏠림 울타리밖 {dline:.0f}×)")
            # ⭐«읽기» 가 안 바뀌는 자리는 판정을 못 뒤집는다 — 프로젝트 규약을 그대로 쓴다
            b0 = c["impact"]["base"].get(kk)
            reading_frozen = ""
            if kk == "comb_db" and b0 is not None and \
                    max(abs(b0), abs(b0 + v)) <= COMB_NULL_DB:
                reading_frozen = f"빗살 백색 널 자리(±{COMB_NULL_DB} dB) 안 — 읽기 안 바뀜"
            nullp = c["impact"].get("rhythm_null_pct")
            if kk == "rhythm_pct" and b0 is not None and nullp is not None and \
                    max(b0, b0 + v) <= nullp:
                reading_frozen = f"리듬이 백색 널 {nullp} % 아래 — 읽기 안 바뀜"
            if reading_frozen:
                watch.append(f"{kk} {v:+.3g}{unit} · {tag} ({reading_frozen})")
            elif bnd is not None and abs(v) > bnd:
                # ⭐밴드 대비 몇 배인지 함께 적는다 — 0° 빗살 밴드처럼 아주 좁은 자리에서는
                #   «넘었다» 가 절대 폭으로는 작을 수 있다. 읽는 사람이 그걸 알아야 한다.
                big.append(f"{kk} {v:+.3g}{unit} > 격자밴드 {bnd}{unit} "
                           f"({abs(v) / bnd:.1f} 배) · {tag}")
            else:
                watch.append(f"{kk} {v:+.3g}{unit} · {tag} (격자밴드 안)")

        # ── ⓑ 구조 — 왜 그렇게 됐는지 설명하는 증거 ──────────────────────────
        iso_null = null_iso.get(str(c["n_poses"]), {}).get("p999")
        if iso_null and c["isolation"] is not None and c["isolation"] > iso_null:
            R.append(f"고립도 {c['isolation']:.2f} > 잡음판 99.9 % {iso_null:.3f} "
                     f"(꼬리 울타리 {TH['isolation']['outer_fence']:.3f})")
            watch.append("고립도가 잡음판 꼬리 밖")
        if TH["flash_recur"] and c["flash_recur"] is not None and \
                c["flash_recur"] > TH["flash_recur"]["outer_fence"]:
            R.append(f"날개 통과 주기에 되풀이 없음 {c['flash_recur']:.1f}× "
                     f"(울타리밖 {TH['flash_recur']['outer_fence']:.2f})")
        if TH["neighbor_jump"] and c["neighbor_jump"] is not None and \
                c["neighbor_jump"] > TH["neighbor_jump"]["inner_fence"]:
            R.append(f"이웃 자세 대비 {c['neighbor_jump']:.0f}× — 한 표본 폭")
        # ⭐경로 수 — 칸 하나만 놓고 보면 약한 증거다(자세가 8192 개면 어느 자세든 꼬리에 들 수
        #   있다). 그래서 **혼자서는 등급을 올리지 않고** 증거로만 싣는다. 대신 «몇 칸에서 이런
        #   일이 일어나나» 를 summary.npaths_association 에 우연 기대치와 나란히 적는다.
        if c.get("npaths_z") is not None and TH["npaths_abs_z"] and \
                abs(c["npaths_z"]) > TH["npaths_abs_z"]["outer_fence"]:
            R.append(f"그 자세의 경로 수가 중앙에서 z={c['npaths_z']:+.1f} "
                     f"({c['npaths_at_spike']:.0f} 대 중앙 {c['npaths_median']:.0f})")
            watch.append("그 자세만 경로 수가 크게 다르다")
        if c.get("npaths_tail_p") is not None and c["npaths_tail_p"] < NPATH_TAIL:
            R.append(f"그 자세의 경로 수 {c['npaths_at_spike']:.0f} 이 분포의 "
                     f"{100 * c['npaths_tail_p']:.2f} % 꼬리 (중앙 {c['npaths_median']:.0f})")
            c["npaths_odd"] = True

        # ── ⓒ 덜 찍힌 플래시 빗살 — ⭐튐이 **아니다**. 시간 분해능 문제다 ──────
        comb_like = bool(c["n_hi_poses"] >= 8 and c["hi_count_over_flashes"] >= 0.5
                         and (c["hi_neighbor_jump_med"] or 0) > 5)
        c["flash_comb_undersampled"] = comb_like
        if comb_like:
            R.append(f"플래시 {c['n_hi_poses']} 개가 한 표본 폭(이웃 대비 중앙 "
                     f"{c['hi_neighbor_jump_med']}×) — 덜 찍힌 것이지 튐이 아니다")
            watch.append("플래시가 한 표본 폭 — 덜 찍힘")

        c["reasons"] = R
        c["impact_over_band"] = big
        c["grade"] = "튐" if big else ("주의" if watch else "정상")
        cls = []
        if big:
            cls.append("one_pose_moves_headline")       # 자세 하나가 헤드라인을 밴드 밖으로 민다
        elif any("쏠림" in w for w in watch):
            cls.append("one_pose_dominates_within_band")  # 쏠리긴 하는데 밴드 안 — 읽기는 안 바뀐다
        if comb_like:
            cls.append("flash_comb_undersampled")       # ⭐튐이 아니라 시간 분해능
        if any("고립도" in w for w in watch):
            cls.append("isolation_over_noise_null")
        if c.get("npaths_odd") or any("경로 수" in w for w in watch):
            cls.append("npaths_odd_at_spike")
        if c["degenerate"]:
            cls.append("degenerate:" + "+".join(c["degenerate"]))
        c["classes"] = cls
        c["why_ko"] = _why(c)

    # ── 2-4. 용의자 — «판정에 쓰이는데 튐 의심» 우선 ────────────────────────
    def prio(c):
        sev = {"튐": 0, "주의": 1, "정상": 2, "퇴화": 3}[c["grade"]]
        return (sev, -c["cited_in_judgment_n"], -(c.get("isolation") or 0))

    suspects = [c for c in cells if c["grade"] in ("튐", "주의")]
    suspects.sort(key=prio)

    meta = dict(
        generator="benchmark/outlier_census_0816.py",
        experiment="원장 전 칸 자세 튐 진단 (outlier census)",
        written_at_kst=_dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9)))
                                   .strftime("%Y-%m-%d %H:%M KST"),
        gpu_used="⛔ 안 씀 — 저장된 원장만 읽었다 (sionna.rt · mitsuba 임포트 없음)",
        why_ko="깊이 축 판정에서 «−60° 에서 리듬이 86.6→32.4 % 로 무너진다» 가 자세 8192 개 중 "
               "하나(#3399) 때문이었다. 자세 하나가 헤드라인을 뒤집을 수 있다 — 그래서 튐 진단을 "
               "43 칸 census 가 아니라 원장 337 칸 **전부**에 상시 잣대로 돌린다.",
        ledger_state=dict(
            n_rows=len(rows),
            ledger_json_mtime_kst=_mtime(A.LED_J), ledger_npz_mtime_kst=_mtime(A.LED_N),
            warning_ko="⚠원장은 **살아 있다** — 스윕이 돌면 행이 늘어난다(이 판을 뜰 때 "
                       f"{len(rows)} 행). 문턱은 이 표본의 꼬리에서 딴 값이라 원장이 자라면 "
                       "다시 돌려야 한다. 등급을 인용할 때는 위 시각을 함께 적는다."),
        sources=dict(
            ledger_json="outputs/elevation_sweep_md.json",
            ledger_npz="outputs/elevation_sweep_md.npz",
            shards="outputs/elev_sweep_shards/*.npz (자세별 경로 수)",
            prior="outputs/depth_axis_verdict_0816.json (outlier_forensics · 43 칸 census)",
            bands="격자 산포 밴드는 depth_axis_verdict_0816 의 앙각별 밴드를 그대로 쓴다"),
        metric_defs_ko=[
            "isolation = |AC| 최대 ÷ 둘째 — 로터 대칭이 만든 구조적 플래시는 여러 자세에 "
            "같이 서므로 1 에 가깝다. 혼자 튀면 커진다.",
            "top1_over_median = 최대 ÷ 중앙 — 얼마나 큰가. ⚠크다고 다 튐이 아니다(정반사 "
            "플래시는 원래 크다). 크기와 고립을 갈라 보려고 함께 싣는다.",
            "share_top1_x · share_top8_x = 상위 1·8 자세가 가진 AC 전력 ÷ 균등 몫 — 잣대가 "
            "실제로 몇 자세를 재고 있나. 1 이면 고르게 퍼졌다, 1000 이면 사실상 그 자세 하나를 쟀다.",
            "sym4_mismatch = 최대 자세 ÷ 로터 4 회 대칭 짝의 최대 — depth_axis 가 쓴 정의를 "
            "이어 쓴다. ⚠이 짝은 «기록 길이의 1/4» 자리라 회전 위상이 아니다. 그래서 아래 "
            "flash_recur 를 함께 낸다.",
            "flash_recur = 최대 자세 ÷ 날개 통과 주기(T = PRF/f_flash) ±1~4 배 자리의 최대 — "
            "구조적 플래시라면 날개가 지나갈 때마다 다시 서야 한다. 안 서면 그 자세만의 사건이다.",
            "neighbor_jump = 최대 자세 ÷ 이웃 ±3 자세의 중앙 — 에코는 f_tip 으로 대역제한되어 "
            "있어 최소 폭이 PRF/(2·f_tip) 표본이다(0° 에서 ≈ 7.7 표본). 한 표본만 뛴 것은 "
            "물리가 낼 수 있는 모양이 아니다.",
            "npaths_z · npaths_tail_p = 그 자세의 경로 수가 칸 중앙에서 몇 MAD 떨어졌나 · "
            "분포의 양쪽 꼬리 몇 %에 있나 — 계산 자체가 그 자세에서 달랐는지(경로가 갑자기 "
            "생겼나 사라졌나) 본다. 경로 수가 거의 상수인 칸은 MAD 가 0 이라 z 가 안 나오므로 "
            "꼬리 확률을 함께 쓴다. ⚠칸 하나만 놓고는 약한 증거다 — 모집단 통계는 "
            "summary.npaths_association 에 있다.",
            "impact.replace_one = 그 자세 하나를 **이웃 평균으로 갈아 끼우고** 헤드라인을 다시 잰 "
            "차이. 삭제는 표집 간격을 깨므로 갈아 끼우기를 정본으로 쓰고 drop_one 도 함께 낸다.",
            "innocent_control_max_abs = 죄 없는 자세(중앙 순위) 12 개를 같은 방법으로 갈아 끼웠을 "
            "때의 최대 변화 — «갈아 끼우기 자체가 잣대를 흔든 것 아닌가» 의 대조군이다."],
        threshold_policy_ko=[
            "⭐임의 숫자를 쓰지 않는다. 비율 잣대는 원장 자신의 분포를 log10 으로 놓고 Tukey "
            "울타리(안 = Q3+1.5·IQR · 밖 = Q3+3·IQR)를 문턱으로 쓴다. 실제 값과 넘은 칸 수는 "
            "thresholds 에 그대로 실었다.",
            "고립도는 두 번째 독립 잣대를 함께 댄다 — 같은 길이의 무작위 잡음 판 4000 개를 만들어 "
            "고립도의 99.9 % 자리를 읽었다(null_isolation). 잡음도 이 값은 못 넘는다.",
            "영향 잣대는 «꼬리 울타리 밖» **이고** «그 앙각의 격자 산포 밴드보다 크다» 를 둘 다 "
            "만족해야 «튐» 이다. 격자 밴드는 격자를 옆으로 옮겨 재면 생기는 계통 폭이라, 그보다 "
            "크게 움직이면 자세 하나가 계통 오차보다 세다는 뜻이다.",
            "문턱을 만드는 표본에서 퇴화 칸(에코 0 · f_tip=0 · 수치 바닥 · 결측)은 뺐다 — 안 빼면 "
            "꼬리가 퇴화 칸으로 오염된다."],
        grade_rule_ko=[
            "튐   = 자세 하나를 갈아 끼웠을 때 헤드라인이 꼬리 울타리 **와** 격자 밴드를 함께 넘는다",
            "주의 = 구조 잣대(고립·되풀이·이웃·전력몫·경로수) 중 하나가 울타리 밖이거나, 영향이 "
            "꼬리 울타리만 넘는다. 또는 플래시가 한 표본 폭으로 덜 찍혔다",
            "정상 = 아무 잣대도 울타리 밖이 아니다",
            "퇴화 = 튐과 **다른 것**. 에코 0 · f_tip=0 인 −90°(상한 위라는 잣대가 정의되지 않음) · "
            "AC/DC 수치 바닥 · 자세 결측. 물리로 읽지 않는다"],
        honesty_ko=[
            "⭐크다고 다 튐이 아니다 — 정반사 플래시는 원래 크다. 그래서 «크기»(top1_over_median)는 "
            "등급에 안 쓰고, «고립·되풀이·이웃·영향»으로만 판정한다.",
            "⭐PathSolver 팔 여럿에서 플래시가 **한 표본 폭**으로 나온다. 이것은 자세 하나의 튐이 "
            "아니라 **덜 찍힌 것**(시간 분해능)이다 — flash_comb_undersampled 로 따로 단다. "
            "판정은 «튐» 이 아니라 «주의» 이고, 읽는 법도 다르다.",
            "npaths 는 샤드가 있는 칸에만 있다. 없는 칸은 None 이고, 없다는 이유로 «정상» 이 되지 "
            "않는다."],
    )

    counts = {}
    for c in cells:
        counts[c["grade"]] = counts.get(c["grade"], 0) + 1

    out = dict(
        _meta=meta,
        thresholds=TH,
        null_isolation=null_iso,
        summary=dict(
            n_cells=len(cells), n_gradeable=len(GRADED),
            n_in_threshold_sample=len(G), grades=counts,
            n_degenerate=sum(1 for c in cells if c["degenerate"]),
            degenerate_breakdown=_deg_counts(cells),
            n_flash_comb_undersampled=sum(1 for c in cells
                                          if c.get("flash_comb_undersampled")),
            n_suspects=len(suspects),
            n_suspects_used_in_judgment=sum(1 for c in suspects
                                            if c["cited_in_judgment_n"] > 0),
            npaths_association=_npaths_assoc(GRADED)),
        suspects=[dict(cell=c["cell"], grade=c["grade"], classes=c["classes"],
                       el_deg=c["el_deg"], range_m=c["range_m"], max_depth=c["max_depth"],
                       combo=c["combo"], n_poses=c["n_poses"], degenerate=c["degenerate"],
                       n_missing=c["n_missing"],
                       cited_in_judgment_n=c["cited_in_judgment_n"],
                       cited_files_n=c["cited_files_n"], cited_examples=c["cited_examples"],
                       argmax_pose=c["argmax_pose"],
                       isolation=c["isolation"], top1_over_median=c["top1_over_median"],
                       neighbor_jump=c["neighbor_jump"], flash_recur=c["flash_recur"],
                       sym4_over_median=c["sym4_over_median"],
                       share_top1_x=c["share_top1_x"], share_top8_x=c["share_top8_x"],
                       npaths_at_spike=c.get("npaths_at_spike"),
                       npaths_median=c.get("npaths_median"), npaths_z=c.get("npaths_z"),
                       npaths_tail_p=c.get("npaths_tail_p"),
                       n_hi_poses=c["n_hi_poses"], hi_power_share=c["hi_power_share"],
                       hi_neighbor_jump_med=c["hi_neighbor_jump_med"],
                       flash_comb_undersampled=c["flash_comb_undersampled"],
                       impact=c["impact"], reasons=c["reasons"],
                       impact_over_band=c["impact_over_band"], why_ko=c["why_ko"])
                  for c in suspects],
        degenerate=[dict(cell=c["cell"], el_deg=c["el_deg"], flags=c["degenerate"],
                         ac_over_dc=c["ac_over_dc"], ledger_level_db=c["ledger_level_db"],
                         n_zero_samples=c["n_zero_samples"], n_missing=c["n_missing"],
                         f_tip_hz=c["f_tip_hz"], cited_in_judgment_n=c["cited_in_judgment_n"])
                    for c in cells if c["degenerate"]],
        cells=cells,
    )
    with open(OUTJ, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {OUTJ}")
    print("grades:", counts)
    for c in suspects[:20]:
        print(f"  {c['grade']:4s} {c['cell']:62s} iso={c['isolation']} "
              f"jump={c['neighbor_jump']} used={c['cited_in_judgment_n']}")


def _r(v, nd=4):
    return None if v is None else round(float(v), nd)


def _mtime(p):
    return _dt.datetime.fromtimestamp(
        os.path.getmtime(p), _dt.timezone(_dt.timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M KST")


def _npaths_assoc(cells):
    """⭐«가장 튄 자세는 경로 수도 이상한가» — 칸 하나가 아니라 **모집단**으로 묻는다.

    가장 튄 자세가 아무 자세나였다면 양쪽 꼬리 확률은 0~1 에 고르게 퍼지고, 1 % 꼬리에
    걸리는 칸은 2 % 뿐이어야 한다. 실제 수가 그보다 훨씬 많으면 «튐과 경로 수는 같이
    움직인다» 는 뜻이다 — 튐이 계산 사건이라는 증거다.
    """
    v = [c["npaths_tail_p"] for c in cells if c.get("npaths_tail_p") is not None]
    if not v:
        return None
    n = len(v)
    obs = sum(1 for p in v if p < NPATH_TAIL)
    return dict(n_cells_with_npaths=n, tail_level=NPATH_TAIL,
                n_observed=obs, n_expected_by_chance=round(2 * NPATH_TAIL * n, 2),
                ratio=(None if n == 0 else round(obs / max(2 * NPATH_TAIL * n, 1e-9), 1)),
                median_tail_p=round(float(np.median(v)), 4),
                reads_ko="가장 튄 자세가 아무 자세나였다면 1 % 꼬리에 걸릴 칸은 "
                         f"{round(2 * NPATH_TAIL * n, 1)} 개다. 실제로 {obs} 개가 걸렸다 — "
                         "튐과 경로 수는 함께 움직인다(계산 사건이라는 증거). "
                         "⚠칸 하나만 놓고 보면 약한 증거라 등급은 이것만으로 안 올린다.")


def _deg_counts(cells):
    d = {}
    for c in cells:
        for f in c["degenerate"]:
            d[f] = d.get(f, 0) + 1
    return d


def _why(c) -> str:
    if c["grade"] == "정상":
        return "울타리 밖 잣대 없음 — 자세 하나가 끌고 있지 않다"
    bits = []
    if c["flash_comb_undersampled"]:
        bits.append(f"플래시 {c['n_hi_poses']} 개가 한 표본 폭으로 찍혔다 — 튐이 아니라 "
                    f"시간 분해능 문제")
    if c["impact_over_band"]:
        bits.append("자세 하나가 격자 밴드보다 크게 헤드라인을 움직인다: "
                    + " · ".join(c["impact_over_band"]))
    if c["reasons"] and not bits:
        bits.append(" · ".join(c["reasons"][:3]))
    return " / ".join(bits) if bits else " · ".join(c["reasons"][:3])


if __name__ == "__main__":
    main()
