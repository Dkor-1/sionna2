#!/usr/bin/env python
"""⭐ 프로펠러 평면형 정밀 계측 — 나머지 6기종  (2026-08-16)

   s1000plus · phantom3 · phantom4 · typhoonh480 · x500v2 · m350rtk

왜 재는가
---------
`src/drone_cad.py` 는 날 폭 최대값을 `CHORD_MAX_OVER_R = 0.25` **단일 상수**로 10기종
전부에 걸고, 시위 분포는 3DR Solo 하나에서 베꼈다. 즉 지금은 «모든 드론에 같은 프로펠러를
달아 놓은 것» 과 같다. 표적 신호의 움직이는 성분은 사실상 전부 프로펠러이므로
(`outputs/material_verdict_0816.json`), 기종 비교(=분류)가 그 상수 하나 위에 서 있다.

주력 3기종(mini5pro·mavic4pro·matrice4e)은 `measure_props_photo_0816.py` 가 맡았다.
이 파일은 **나머지 6기종**을 «같은 자» 로 잰다 — 측정 원시함수(`blade_polar`,
`blade_cartesian`, `root_radius`, `summarize`)를 그 파일에서 그대로 가져다 쓴다.

⭐ 규약 — 이게 다르면 비교가 무의미하다
--------------------------------------
R 의 정의   : **스윕 디스크 반경**. 회전중심 C 에서 날 끝까지의 거리.
              C = 2날 프롭의 두 날끝 **중점**. `reference_props.json` 의 R_disc/2 와 같은 뜻.
              ⚠ 접힌 프롭(m350rtk)은 두 날이 «같은 쪽» 을 보므로 이 정의를 쓸 수 없다 —
                거기서는 R = r_h(축→힌지) + L(힌지→팁) 로 **조립**한다(§E).
날 뿌리     : r_root = 각폭 곡선이 허브 덩어리를 벗어나 날 폭으로 «떨어지는» 반경
              (안쪽 국소 최소). 요약 통계는 **max(0.25R, r_root+0.03R) ~ 0.96R** 만 쓴다.
              ⚠ 이 하한이 없으면 허브가 «가장 넓은 시위» 로 잡혀 값이 두 배로 뜬다.
시위 c(r)   : **두 정의를 끝까지 구분한다.**
   (1) c_arc = r·Δθ  — 회전면에 **투영된** 폭. 사진(2D)이 줄 수 있는 것은 이것뿐이다.
   (2) c_cal = 반경 r 원통 단면의 최대 캘리퍼 — `measure_reference_props.py` 와
       `drone_cad` 의 시위. 날이 비틀려 있으므로 항상 c_cal ≥ c_arc.
   ⭐ 이 파일이 **두 번째 다리**(cal/arc)를 Yuneec 실물 3D 에서 실측한다.
      (첫 번째는 Mini 2 공식 CAD 에서 나왔다: 1.038.)
      ⛔ 사진값(arc)과 메쉬값(caliper)을 그냥 한 표에 나란히 적으면 안 된다.

⭐ 같은 양을 두 방법 이상으로 (규약 요구사항)
---------------------------------------------
  방법 A(극좌표) : 반경 밴드의 각폭 → c = r·Δθ
  방법 B(직교)   : 날을 스팬축으로 돌려 열마다 수직 폭   (표본 방식이 A 와 다르다)
  방법 C(3D)     : 원통 단면 최대 캘리퍼                  (STL 이 있는 기체만)
  §V0 은 **자 검증**이다 — Yuneec 실물 3D 를 정투영 상면으로 «렌더» 해 2D 코드에 먹이고
  같은 물건의 3D 직접 측정과 비교한다. 앞 스크립트의 Mini 2 자 검증이 실패(오차 918 %)
  했으므로 검증을 새로 세운다. 이게 통과하지 못하면 아래 사진값은 못 믿는다.

⭐ 이 라운드에서 새로 실측한 함정 — «안쪽 날은 잘린다»
-----------------------------------------------------
조립된 기체를 위에서 찍은 그림에서는 **회전중심에서 기체 안쪽을 향한 날**이 암(arm)·동체와
한 실루엣으로 붙어버린다. 그러면 추적기가 안쪽을 못 보고 뿌리가 «0.44R» 같은 헛값으로
잡히며, 요약 구간이 시위 최대점(0.33R)보다 바깥에서 시작해 **c_max 를 놓친다**.
실측(s1000plus, 로터 8개): 잘 보인 날 0.176 ± 0.002 ↔ 잘린 날 0.141 ± 0.005 (−20 %).
⇒ 그래서 **날마다 r_root 를 재고, r_root ≤ 0.30 인 «깨끗한 날» 만** 요약에 넣는다.
   ⛔ 처음에는 «기체 중심에서 먼 쪽 날이 깨끗하다» 는 기하 규칙을 쓰려 했는데 **틀렸다** —
     프롭이 커서 안쪽 날끝이 기체 반대편까지 뻗는 기체(phantom3: 두 날끝이 중심에서
     457 px ↔ 446 px)에서는 그 규칙이 뜻을 잃는다. 판정은 «측정된 r_root» 로만 한다.
   두 날 평균(투영 기울기의 1차 오차를 지우는 장치)도 같이 남기되, 한쪽 날이 잘린 그림에서는
   그 평균이 **아래로 편향**된다(s1000plus 0.143 ↔ 0.176, phantom3 0.207 ↔ 0.263).
   ⚠ 대신 잃는 것: 기울기 1차 오차의 상쇄. 그 대가는 «로터 여러 개가 서로 다른 방위를
     보고 있는데도 값이 흩어지지 않는가» 로 검사한다(s1000plus 8 로터 흩어짐 1.2 %).

⛔ 정책: 코드 무변경(`src/` 미접촉 · 형제 스크립트 미수정) · GPU 미사용 · git 미접촉.

산출: outputs/prop_measure_others_0816.json
실행: PYTHONPATH=src:benchmark /workspace/.venvs/py312/bin/python \
        benchmark/measure_props_others_0816.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure_props_photo_0816 as M          # noqa: E402  — «같은 자» 를 그대로 쓴다

ROOT = Path("/workspace/sionna")
PHOTO = ROOT / "assets/photos"
REF = ROOT / "assets/meshes/reference"
OUT = ROOT / "outputs/prop_measure_others_0816.json"
SCRATCH = Path("/tmp/claude-0/-workspace/e9e31991-b542-4f3a-b8e2-570320d555ba/scratchpad")

GRID, RSTEP = M.GRID, M.RSTEP
R_LO, R_HI = M.R_LO, M.R_HI
ROOT_CLEAN_MAX = 0.30      # r_root 가 이보다 크면 «안쪽을 못 본 날» 로 본다


# ===================================================================== #
#  1. 날끝 찾기                                                          #
# ===================================================================== #
def walk_tips(mask, n_props, sep_frac=0.18, pca_r=55.0, step=2.0, wjump=2.2):
    """바깥 날끝에서 안쪽으로 «걸어가» 허브를 찾고, 그 허브의 반대쪽 날끝을 잡는다.

    ⭐ 왜 필요한가: 기존 `envelope_tips` 는 «실루엣 중심에서 가장 먼 점 2N 개» 를 고른다.
    옥토콥터(s1000plus)처럼 프롭이 8개면 안쪽 날끝이 중심에 너무 가까워 그 방법이 무너진다 —
    실측: 날끝-날끝 길이가 895 px 와 698 px 두 무리로 갈렸다(서로 다른 로터의 날을 한 쌍으로
    묶은 것이다. 참값은 243 px). 시위가 143 % 흩어졌다.

    이 방법은 **한 날 안에서만** 움직인다:
      ① 바깥 날끝 N 개를 고른다(서로 sep 이상 떨어지게).
      ② 각 날끝에서 국소 주축을 따라 안쪽으로 걸으며 «수직 폭» 을 잰다.
      ③ 폭이 날 기준폭의 wjump 배를 넘는 곳 = 허브 → 회전중심 후보.
      ④ 허브 주위 1.25 R 안에서 그 날끝으로부터 가장 먼 점 = 반대쪽 날끝.
    실측(s1000plus): 8 로터 전부 성공, 날끝-날끝 242.9 px(×6) / 238.5 px(×2), 흩어짐 0.8 %.
    반환은 항상 **(바깥 날끝, 안쪽 날끝)** 순서다 — 아래에서 inner/outer 를 가르는 데 쓴다.
    """
    ys, xs = np.where(mask)
    Q = np.c_[xs.astype(float), ys.astype(float)]
    c0 = Q.mean(0)
    rr = np.linalg.norm(Q - c0, axis=1)
    order = np.argsort(rr)[::-1]
    sep = sep_frac * float(rr.max())
    outer = []
    for k in order:
        p = Q[k]
        if all(np.linalg.norm(p - q) > sep for q in outer):
            outer.append(p)
        if len(outer) == n_props:
            break
    pairs, diag = [], []
    for T in outer:
        near = Q[np.linalg.norm(Q - T, axis=1) < pca_r]
        X = near - near.mean(0)
        _, V = np.linalg.eigh(X.T @ X / len(X))
        e = V[:, 1]
        if (T - c0) @ e < 0:
            e = -e                                        # e = 바깥(팁) 방향
        nvec = np.array([-e[1], e[0]])
        widths, pos, s = [], [], 0.0
        smax = 0.95 * float(np.linalg.norm(T - c0))
        while s < smax:
            d = Q - (T - e * s)
            m = np.abs(d @ e) < 2.0
            if m.sum() < 3:
                break
            perp = d[m] @ nvec
            widths.append(float(perp.max() - perp.min()))
            pos.append(s)
            s += step
        widths, pos = np.array(widths), np.array(pos)
        if len(widths) < 20:
            diag.append(dict(tip=T.tolist(), hub_found=False, why="걸음이 20 칸 미만"))
            continue
        base = float(np.median(widths[5:min(len(widths), 40)]))
        hit = np.where((pos > 0.25 * pos.max()) & (widths > wjump * base))[0]
        if len(hit) == 0:
            diag.append(dict(tip=T.tolist(), hub_found=False, why="허브 폭 점프 없음"))
            continue
        C0 = T - e * float(pos[hit[0]])
        R0 = float(np.linalg.norm(T - C0))
        cand = Q[np.linalg.norm(Q - C0, axis=1) < 1.25 * R0]
        T2 = cand[int(np.argmax(np.linalg.norm(cand - T, axis=1)))]
        pairs.append((T, T2))
        diag.append(dict(tip=T.tolist(), hub=C0.tolist(), blade_base_width_px=base,
                         hub_found=True, tip2tip_px=float(np.linalg.norm(T2 - T))))
    return pairs, diag


def isolated_pairs(mask, n_props, min_frac=0.004):
    """따로 놓인 프롭(제품컷·부품 사진): 성분마다 «가장 먼 두 점» 이 두 날끝."""
    lab, n = ndimage.label(mask)
    sz = ndimage.sum(mask, lab, range(1, n + 1))
    order = [i for i in np.argsort(sz)[::-1] if sz[i] > min_frac * mask.size][:n_props]
    pairs = []
    for i in order:
        ys, xs = np.where(lab == i + 1)
        P = np.c_[xs.astype(float), ys.astype(float)]
        c = P.mean(0)
        p1 = P[int(np.argmax(np.linalg.norm(P - c, axis=1)))]
        p2 = P[int(np.argmax(np.linalg.norm(P - p1, axis=1)))]
        pairs.append((p1, p2))
    return pairs


# ===================================================================== #
#  2. 프롭 하나 재기 — 형제 스크립트의 «원시함수» 를 그대로 쓴다           #
# ===================================================================== #
def measure_pairs(mask, pairs, label="", grade="", src=""):
    """날끝 쌍 목록 → 프롭별·날별 평면형.

    형제 스크립트 `measure_photo` 의 속알맹이와 **같은 함수·같은 문턱**을 쓴다.
    다른 점은 딱 둘: (1) 날끝을 밖에서 받는다 (2) 날마다 inner/outer 를 표시한다.
    """
    ys, xs = np.where(mask)
    P = np.c_[xs.astype(float), ys.astype(float)]
    img_c = P.mean(0)
    out = []
    for pi, (t1, t2) in enumerate(pairs):
        C = 0.5 * (np.asarray(t1, float) + np.asarray(t2, float))
        Rpx = float(0.5 * (np.linalg.norm(t1 - C) + np.linalg.norm(t2 - C)))
        blades, prof = [], []
        for bi, tp in enumerate((np.asarray(t1, float), np.asarray(t2, float))):
            th = float(np.arctan2(*(tp - C)[::-1]))
            rrA, cA, sel = M.blade_polar(P, C, Rpx, th)
            rrB, cB = M.blade_cartesian(P[sel] if sel.sum() > 40 else P, C, Rpx, tp)
            rroot = M.root_radius(rrA, cA)
            lo = (rroot + 0.03) if rroot else None
            sA = M.summarize(rrA, cA, Rpx, lo, "A_polar")
            sB = M.summarize(rrB, cB, Rpx, lo, "B_cartesian")
            if sA is None:
                blades.append(dict(blade=bi, error="A 요약 실패(가림·잘림)",
                                   r_root_over_R=rroot))
                continue
            g = np.arange(0.35, 0.9001, 0.02)
            oa, ob = np.isfinite(cA), np.isfinite(cB)
            if oa.sum() > 8 and ob.sum() > 8:
                aa = np.interp(g, rrA[oa], cA[oa])
                bb = np.interp(g, rrB[ob], cB[ob])
                dmean = float(np.mean(np.abs(aa - bb) / aa) * 100)
                dmax = float(np.max(np.abs(aa - bb) / aa) * 100)
            else:
                dmean = dmax = None
            blades.append(dict(
                blade=bi, tip_px=tp.tolist(),
                # ⚠ 이 꼬리표는 «날끝이 기체 중심에서 더 먼 쪽인가» 일 뿐이다. 프롭 반경이
                #   암 길이보다 훨씬 작을 때만(s1000plus) 뜻이 있다. phantom3 처럼 프롭이
                #   커서 안쪽 날끝이 기체 반대편까지 뻗으면 두 날끝의 거리가 비슷해져
                #   무의미해진다(실측: 457 px ↔ 446 px). ⇒ **판정은 이 꼬리표가 아니라
                #   측정된 r_root(=clean)로 한다.**
                tip_farther_from_airframe_centroid=bool(
                    np.linalg.norm(tp - img_c)
                    >= np.linalg.norm(np.asarray(t2 if bi == 0 else t1, float) - img_c)),
                r_root_over_R=rroot,
                clean=bool(rroot is not None and rroot <= ROOT_CLEAN_MAX),
                A_polar=sA, B_cartesian=sB,
                AB_diff_pct_mean=dmean, AB_diff_pct_max=dmax))
            prof.append((rrA, cA, rroot))
        rec = dict(prop=pi, R_px=Rpx, blades=blades)
        if len(prof) == 2:
            rr = prof[0][0]
            cavg = np.nanmean(np.vstack([prof[0][1], prof[1][1]]), axis=0)
            lo = max([q[2] for q in prof if q[2] is not None] or [None])
            rec["two_blade_mean"] = M.summarize(rr, cavg, Rpx,
                                                (lo + 0.03) if lo else None,
                                                "two_blade_mean")
            w = [b["A_polar"]["c_max_over_R"] for b in blades if "A_polar" in b]
            if len(w) == 2:
                rec["blade_asym_pct"] = float(100 * abs(w[0] - w[1]) / (w[0] + w[1]))
        out.append(rec)

    def _stat(vals):
        v = np.array(vals, float)
        if not len(v):
            return None
        return dict(n=int(len(v)), mean=float(v.mean()),
                    sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                    median=float(np.median(v)), min=float(v.min()), max=float(v.max()),
                    spread_pct=float(100 * (v.max() - v.min()) / v.mean()))

    clean = [b for o in out for b in o["blades"] if b.get("clean")]
    res = dict(label=label, grade=grade, source=src, n_props=len(out),
               tip2tip_px=[float(2 * o["R_px"]) for o in out],
               tip2tip_spread_pct=float(100 * (max(o["R_px"] for o in out)
                                               - min(o["R_px"] for o in out))
                                        / np.mean([o["R_px"] for o in out]))
               if out else None,
               props=out)
    res["clean_blades"] = dict(
        n=len(clean),
        n_blades_total=sum(len(o["blades"]) for o in out),
        rule_ko=(f"r_root ≤ {ROOT_CLEAN_MAX} 인 날만 쓴다 — 추적기가 «허브를 벗어나는 반경» "
                 "을 실제로 본 날이라는 뜻이다. 이게 헤드라인이다."),
        c_max_over_R=_stat([b["A_polar"]["c_max_over_R"] for b in clean]),
        peak_r_over_R=_stat([b["A_polar"]["peak_r_over_R"] for b in clean]),
        area_over_R2=_stat([b["A_polar"]["area_over_R2"] for b in clean]),
        AB_diff_pct=_stat([b["AB_diff_pct_mean"] for b in clean
                           if b["AB_diff_pct_mean"] is not None]),
        c_over_cmax_mean={f"{q:.2f}": (float(np.mean(
            [b["A_polar"]["c_over_cmax"][f"{q:.2f}"] for b in clean
             if b["A_polar"]["c_over_cmax"][f"{q:.2f}"] is not None]))
            if any(b["A_polar"]["c_over_cmax"][f"{q:.2f}"] is not None for b in clean)
            else None) for q in GRID},
    )
    res["dirty_blades"] = dict(
        n=sum(len(o["blades"]) for o in out) - len(clean),
        meaning_ko=("암·동체와 한 실루엣으로 붙어 안쪽을 못 본 날. 요약 구간이 시위 최대점보다 "
                    "바깥에서 시작해 c_max 를 **놓친다** — 그래서 헤드라인에서 뺀다."),
        c_max_over_R=_stat([b["A_polar"]["c_max_over_R"] for o in out
                            for b in o["blades"]
                            if "A_polar" in b and not b.get("clean")]))
    res["two_blade_mean_stat"] = _stat([o["two_blade_mean"]["c_max_over_R"] for o in out
                                        if o.get("two_blade_mean")])
    res["two_blade_mean_warning_ko"] = (
        "두 날 평균은 «투영 기울기의 1차 오차» 를 지우는 장치지만, 한쪽 날이 잘린 그림에서는 "
        "그 평균이 **아래로 편향**된다. 잘린 날이 하나라도 있으면 헤드라인으로 쓰지 말 것.")
    res["blade_asym_pct"] = [round(o["blade_asym_pct"], 2) for o in out
                             if "blade_asym_pct" in o]
    return res


def measure_image(path, mode, n_props, thr=None, how="walk", label="", grade="", **kw):
    mask, thr_used, _ = M.silhouette(path, mode, thr)
    if how == "walk":
        pairs, diag = walk_tips(mask, n_props, **kw)
    elif how == "isolated":
        pairs, diag = isolated_pairs(mask, n_props), None
    elif how == "envelope":
        # 형제 스크립트의 «봉투 날끝 + 선분 덮개로 짝짓기» 를 그대로 쓴다.
        # 프롭 수가 적고(≤4) 서로 멀리 떨어진 그림에서는 이쪽이 더 튼튼하다.
        T = M.envelope_tips(mask, 2 * n_props)
        pp, worst = M.pair_tips(T, mask)
        pairs = [(T[i], T[j]) for (i, j, _) in pp]
        diag = [dict(pair=[int(i), int(j)], seg_coverage=float(c)) for (i, j, c) in pp]
        diag.append(dict(worst_coverage=float(worst)))
    else:
        raise ValueError(how)
    if len(pairs) != n_props:
        return dict(file=Path(path).name, label=label, grade=grade,
                    error=f"프롭 {len(pairs)}개만 잡힘 (필요 {n_props})", walk=diag)
    res = measure_pairs(mask, pairs, label, grade, str(path))
    res.update(file=Path(path).name, mode=mode, threshold=thr_used, tips_from=how)
    if diag:
        res["tip_diag"] = diag
    return res


def crop_to_png(src, box, name):
    """사진 일부만 재야 할 때(잡동사니 배제). 잘라낸 파일과 상자를 원장에 남긴다."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    dst = SCRATCH / name
    Image.open(src).convert("RGBA").crop(box).save(dst)
    return dst, dict(source=str(Path(src).relative_to(ROOT)), crop_box_xyxy=list(box),
                     cropped_file=str(dst))


# ===================================================================== #
#  3. 3D 프롭 (STL) — arc · caliper · 정투영 렌더                        #
# ===================================================================== #
def _load_prop_stl(path):
    """STL → mm, 회전축을 z 로, 원점 중심."""
    import trimesh
    m = trimesh.load(str(path), force="mesh", process=False)
    ext = np.asarray(m.extents, float)
    unit = "mm" if ext.max() > 5.0 else "m"
    if unit == "m":
        m.apply_scale(1000.0)
    m.apply_translation(-m.bounds.mean(axis=0))
    ext = np.asarray(m.extents, float)
    spin = int(np.argmin(ext))                 # 회전축 = 가장 납작한 축
    order = [a for a in range(3) if a != spin] + [spin]
    return (np.asarray(m.vertices, float)[:, order], np.asarray(m.faces, int),
            unit, ext[order].tolist())


def _center_and_R(P2):
    """2날 프롭: 회전중심 C = 두 날끝의 중점 — 사진 규약과 «같은» 정의."""
    C = P2.mean(0)
    for _ in range(8):
        t1 = P2[int(np.argmax(np.linalg.norm(P2 - C, axis=1)))]
        t2 = P2[int(np.argmax(np.linalg.norm(P2 - t1, axis=1)))]
        C = 0.5 * (t1 + t2)
    return C, float(0.5 * (np.linalg.norm(t1 - C) + np.linalg.norm(t2 - C))), t1, t2


def stl_prop_3d(path, label, n_sample=1_200_000, seed=0, caliper_pts=700):
    """실물 3D 프롭을 arc·caliper 두 정의로 잰다 (형제 스크립트의 mini2_cad 와 같은 방식)."""
    V, F, unit, ext = _load_prop_stl(path)
    S = M._sample_surface(V, F, n_sample, seed)
    P2, z = S[:, :2], S[:, 2]
    C, R, t1, t2 = _center_and_R(P2)
    d = P2 - C
    rad = np.hypot(d[:, 0], d[:, 1])
    th = np.arctan2(d[:, 1], d[:, 0])
    rng = np.random.default_rng(seed)
    out = []
    for bi, tp in enumerate((t1, t2)):
        th_tip = float(np.arctan2(*(tp - C)[::-1]))
        rr = np.round(np.arange(R_LO, R_HI + 1e-9, RSTEP), 4)
        ca, cc = np.full(len(rr), np.nan), np.full(len(rr), np.nan)
        for a, x in enumerate(rr):
            m = np.abs(rad - x * R) < 0.006 * R
            if m.sum() < 30:
                continue
            aa = M._arcs(th[m], np.radians(14.0))
            if not aa:
                continue

            def gap(a_):                       # 이 날에 속한 호만 고른다
                e = abs(np.angle(np.exp(1j * (0.5 * (a_[0] + a_[1]) - th_tip))))
                return max(0.0, e - 0.5 * (a_[1] - a_[0]))

            k = int(np.argmin([gap(a_) for a_ in aa]))
            if gap(aa[k]) > np.radians(35.0):
                continue
            lo, hi = aa[k]
            ca[a] = x * R * (hi - lo)
            ref = 0.5 * (lo + hi)
            tl = ref + np.angle(np.exp(1j * (th[m] - ref)))
            sel = (tl >= lo - 1e-12) & (tl <= hi + 1e-12)
            Q = np.c_[x * R * tl[sel], z[m][sel]]
            if len(Q) < 8:
                continue
            if len(Q) > caliper_pts:
                Q = Q[rng.choice(len(Q), caliper_pts, replace=False)]
            cc[a] = float(np.linalg.norm(Q[:, None] - Q[None], axis=2).max())
        rroot = M.root_radius(rr, ca)
        lo0 = (rroot + 0.03) if rroot else None
        sa = M.summarize(rr, ca, R, lo0, "A_arc_projected")
        sc = M.summarize(rr, cc, R, lo0, "C_cylindrical_caliper")
        m_blade = np.abs(np.angle(np.exp(1j * (th - th_tip)))) < np.radians(70.0)
        rrB, cB = M.blade_cartesian(P2[m_blade], C, R, tp)
        sb = M.summarize(rrB, cB, R, lo0, "B_cartesian")
        if not (sa and sc):
            continue
        g = np.arange(0.35, 0.9001, 0.02)
        oa, oc = np.isfinite(ca), np.isfinite(cc)
        ratio = np.interp(g, rr[oc], cc[oc]) / np.interp(g, rr[oa], ca[oa])
        ab = None
        if sb:
            u = np.array([sa["c_over_R"][f"{q:.2f}"] for q in GRID], float)
            w = np.array([sb["c_over_R"][f"{q:.2f}"] if sb["c_over_R"][f"{q:.2f}"]
                          else np.nan for q in GRID], float)
            ab = float(np.nanmean(np.abs(w - u) / u) * 100)
        out.append(dict(blade=bi, R_mm=R, disc_dia_mm=2 * R, r_root_over_R=rroot,
                        A_arc=sa, B_cartesian=sb, C_caliper=sc,
                        AB_diff_pct_mean=ab,
                        cal_over_arc_mean=float(ratio.mean()),
                        cal_over_arc_at={f"{x:.2f}": float(np.interp(x, g, ratio))
                                         for x in (0.4, 0.5, 0.7, 0.9)}))
    if not out:
        return dict(file=Path(path).name, label=label, error="측정 실패")
    arc = np.array([b["A_arc"]["c_max_over_R"] for b in out])
    cal = np.array([b["C_caliper"]["c_max_over_R"] for b in out])
    br = np.array([b["cal_over_arc_mean"] for b in out])

    def _sd(v):
        return float(v.std(ddof=1)) if len(v) > 1 else 0.0

    return dict(file=Path(path).name, label=label, unit_detected=unit, bbox_mm=ext,
                n_blades=len(out), blades=out,
                summary=dict(
                    disc_dia_mm=float(np.mean([b["disc_dia_mm"] for b in out])),
                    arc_c_max_over_R=dict(mean=float(arc.mean()), sd=_sd(arc)),
                    caliper_c_max_over_R=dict(mean=float(cal.mean()), sd=_sd(cal)),
                    cal_over_arc=dict(mean=float(br.mean()), sd=_sd(br)),
                    c_over_cmax_arc_mean={
                        f"{q:.2f}": (float(np.mean([b["A_arc"]["c_over_cmax"][f"{q:.2f}"]
                                                    for b in out]))
                                     if all(b["A_arc"]["c_over_cmax"][f"{q:.2f}"]
                                            is not None for b in out) else None)
                        for q in GRID}))


def stl_ortho_render(path, name, px_per_mm=4.0, n_sample=1_500_000, close_px=3):
    """STL 을 «회전축에서 내려다본 정투영 실루엣» PNG 로 굽는다.

    ⭐ 왜: 2D(사진) 코드를 **답을 아는 물건** 위에서 검증하기 위해서다. 같은 STL 을
      3D 로 직접 잰 값과, 이 그림을 2D 코드에 먹여 얻은 값이 맞아야 그 자를 믿는다.
    """
    V, F, _, _ = _load_prop_stl(path)
    S = M._sample_surface(V, F, n_sample, 1)
    xy = S[:, :2] * px_per_mm
    xy -= xy.min(0) - 8
    W, H = int(xy[:, 0].max() + 8), int(xy[:, 1].max() + 8)
    img = np.zeros((H, W), bool)
    img[np.clip(xy[:, 1].astype(int), 0, H - 1),
        np.clip(xy[:, 0].astype(int), 0, W - 1)] = True
    img = ndimage.binary_fill_holes(
        ndimage.binary_closing(img, np.ones((close_px, close_px))))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    dst = SCRATCH / name
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = np.where(img, 255, 0)
    Image.fromarray(rgba).save(dst)
    return dst, dict(px_per_mm=px_per_mm, size=[W, H], on_frac=float(img.mean()),
                     note_ko=("2날 프롭의 정투영 실루엣은 «원반» 이 아니라 길쭉한 조각이다 — "
                              "가로 세로가 크게 다른 게 정상이다."))


# ===================================================================== #
#  4. 접힌 프롭 (m350rtk 2110s)                                          #
# ===================================================================== #
def folded_rows(path):
    """접힌 프롭 제품컷: 행마다 «두 덩이인가 한 덩이인가» 와 이음매를 기록한다."""
    a = np.asarray(Image.open(path).convert("RGBA"))
    mask, lum = a[..., 3] > 128, a[..., :3].astype(float).mean(2)
    lab, n = ndimage.label(mask)
    sz = ndimage.sum(mask, lab, range(1, n + 1))
    props = []
    for i in np.argsort(sz)[::-1][:2]:
        sel = (lab == i + 1)
        ys, xs = np.where(sel)
        rows = []
        for y in range(int(ys.min()), int(ys.max()) + 1):
            idx = np.where(sel[y])[0]
            if len(idx) < 4:
                continue
            runs, s0, p0 = [], idx[0], idx[0]
            for k in idx[1:]:
                if k > p0 + 1:
                    runs.append((s0, p0))
                    s0 = k
                p0 = k
            runs.append((s0, p0))
            runs = [r for r in runs if r[1] - r[0] >= 3]
            if len(runs) == 2:
                (a0, a1), (b0, b1) = runs
                rows.append(dict(y=y, kind="split", W=float(b1 - a0 + 1),
                                 w=[float(a1 - a0 + 1), float(b1 - b0 + 1)],
                                 centre_gap=float(0.5 * (b0 + b1) - 0.5 * (a0 + a1))))
            elif len(runs) == 1:
                lo, hi = runs[0]
                seg = lum[y, lo:hi + 1]
                m0, m1 = max(1, int(0.25 * len(seg))), int(0.75 * len(seg)) + 1
                if len(seg) < 12 or m1 <= m0:
                    continue
                j = int(np.argmin(seg[m0:m1])) + m0
                if seg[j] > 20.0:
                    rows.append(dict(y=y, kind="merged_noseam", W=float(hi - lo + 1),
                                     w=None))
                else:
                    rows.append(dict(y=y, kind="merged", W=float(hi - lo + 1),
                                     w=[float(j), float(hi - lo - j)],
                                     seam_lum=float(seg[j])))
        props.append(dict(bbox=[int(xs.min()), int(ys.min()),
                                int(xs.max()), int(ys.max())],
                          n_px=int(sz[i]), rows=rows))
    return dict(file=Path(path).name, n_props=len(props), props=props)


def folded_geometry(prop, dia_mm):
    """접힌 프롭 한 개에서 r_h · L · R · 시위분포를 «그림 안에서» 조립한다.

    ⭐ 기하 (이 절의 전부)
      접이 프롭은 축에서 r_h 떨어진 «힌지» 에 날이 달리고, 날은 회전면 «안에서» 접힌다.
      → 접혀도 날 자체의 평면형은 안 변한다. 펼치면 팁이 R 에 오므로
            R = r_h + L,   L = 힌지→팁
      즉 **축척을 그림 안에서 조립할 수 있다**(사진에 자가 없어도 된다).
      c_max/R 은 이 조립만으로 나오고 공칭 지름에 기대지 않는다 — 공칭은 mm 로 바꿀 때만 쓴다.

    ⛔ 어려운 점과 처리
      ① 두 날이 겹친다. 실루엣만 보면 «봉투 폭» W 만 나온다. 앞 날이 온전히 보이면
         그림자 이음매가 생기고, 거울 대칭이므로  W = w_front + w_back_visible.
         이 항등식이 성립하는지를 매 행마다 확인해 `sum_check_pct` 로 남긴다.
         시위 = 둘 중 **큰** 쪽(= 앞 날).
      ② 팁·뿌리 근처에서는 두 날이 실제로 떨어져 **가정 없이** 잰다(`n_rows_split`).
      ③ 힌지 높이 y_h 는 직접 안 보인다. 그래서 **구간으로** 잡는다 —
         아래끝(마지막 분리 행) ~ 위끝(성분 바닥). 가운데를 값으로, 양끝을 오차로 낸다.
    """
    rows, (x0, y0, x1, y1) = prop["rows"], prop["bbox"]
    H = y1 - y0
    low = [r for r in rows if r["kind"] == "split" and r["y"] > y0 + 0.7 * H]
    if not low:
        return dict(error="뿌리 쪽 분리 구간이 없다 — 힌지 간격을 못 잰다")
    tail = sorted(low, key=lambda r: -r["y"])[:6]
    r_h_px = float(np.median([r["centre_gap"] for r in tail])) / 2.0
    y_tip = min(r["y"] for r in rows)
    y_lo, y_hi = max(r["y"] for r in low), y1          # 힌지 높이의 구간
    out = dict(r_h_px=r_h_px, y_tip=y_tip, y_hinge_bracket=[y_lo, y_hi],
               n_rows_split=len([r for r in rows if r["kind"] == "split"]),
               n_rows_merged=len([r for r in rows if r["kind"] == "merged"]),
               n_rows_merged_noseam=len([r for r in rows
                                         if r["kind"] == "merged_noseam"]))
    mg = [r for r in rows if r["kind"] == "merged"]
    out["sum_check_pct"] = (float(np.mean([abs(r["w"][0] + r["w"][1] - r["W"]) / r["W"]
                                           for r in mg])) * 100) if mg else None
    # ⭐ 시위 자료로 쓸 행은 **마지막 분리 행(y_lo)까지**다. 그 아래는 허브 막대라 폭이
    #   날 폭이 아니다 — 이걸 안 자르면 c_max 가 허브를 물어 최대 11 % 부푼다(실측).
    s, c = [], []
    for r in rows:
        if r["w"] is None or r["y"] > y_lo:
            continue
        s.append(float(r["y"] - y_tip))
        c.append(float(max(r["w"])))
    s, c = np.array(s), np.array(c)
    variants = {}
    for tag, y_h in (("low", y_lo), ("mid", 0.5 * (y_lo + y_hi)), ("high", y_hi)):
        L = float(y_h - y_tip)                # 힌지→팁
        R = L + r_h_px                        # 축→팁 (펼친 상태)
        rr = 1.0 - s / R                      # r/R = (R - s)/R,  s = 팁에서 안쪽 거리
        o = np.argsort(rr)
        grid = np.round(np.arange(R_LO, R_HI + 1e-9, RSTEP), 4)
        prof = np.interp(grid, rr[o], c[o], left=np.nan, right=np.nan)
        rroot = M.root_radius(grid, prof)
        sm = M.summarize(grid, prof, R, (rroot + 0.03) if rroot else None,
                         "folded_front_blade")
        ok = np.isfinite(prof)
        variants[tag] = dict(
            y_hinge=float(y_h), L_px=L, R_px=R, r_h_over_R=r_h_px / R,
            r_root_over_R=rroot, summary=sm,
            # 규약 밖 진단: 하한 0.25R 을 안 걸었을 때의 최대 시위와 그 위치.
            # m350rtk 처럼 뿌리가 넓은 프롭은 «규약값이 참 최대보다 작다» 는 것을 드러낸다.
            unconstrained=dict(
                c_max_over_R=float(np.nanmax(prof[ok]) / R) if ok.any() else None,
                at_r_over_R=float(grid[ok][int(np.nanargmax(prof[ok]))])
                if ok.any() else None,
                measured_r_range=[float(grid[ok].min()), float(grid[ok].max())]
                if ok.any() else None))
    out["variants"] = variants
    v = [variants[t]["summary"]["c_max_over_R"] for t in ("low", "mid", "high")
         if variants[t]["summary"]]
    if v:
        out["c_max_over_R"] = float(variants["mid"]["summary"]["c_max_over_R"])
        out["c_max_over_R_bracket"] = [float(min(v)), float(max(v))]
        out["hinge_uncertainty_pct"] = float(100 * (max(v) - min(v)) / np.mean(v))
        mmpx = dia_mm / (2 * variants["mid"]["R_px"])
        out["mm_per_px"] = float(mmpx)
        out["blade_len_mm"] = float(variants["mid"]["L_px"] * mmpx)
        out["hinge_radius_mm"] = float(r_h_px * mmpx)
        out["c_max_mm"] = float(out["c_max_over_R"] * variants["mid"]["R_px"] * mmpx)
        out["unconstrained_mid"] = variants["mid"]["unconstrained"]
    return out


# ===================================================================== #
#  5. main                                                              #
# ===================================================================== #
def _slim(o, drop=("rows", "props_rows")):
    if isinstance(o, dict):
        return {k: _slim(v, drop) for k, v in o.items() if k not in drop}
    if isinstance(o, list):
        return [_slim(v, drop) for v in o]
    return o


def main():
    t0 = time.time()
    doc = {"_meta": {
        "title": "프로펠러 평면형 정밀 계측 — 나머지 6기종",
        "aircraft": ["s1000plus", "phantom3", "phantom4", "typhoonh480",
                     "x500v2", "m350rtk"],
        "generated_kst": time.strftime("%Y-%m-%d %H:%M",
                                       time.localtime(time.time() + 9 * 3600)),
        "script": "benchmark/measure_props_others_0816.py",
        "python": "/workspace/.venvs/py312/bin/python",
        "policy": "⛔코드 무변경 · ⛔GPU 미사용 · ⛔git 미접촉",
        "sibling_ledgers": ["outputs/prop_identity_0816.json (신원)",
                            "outputs/prop_measure_mavic4pro_mini5pro_0816.json (주력 2종)",
                            "outputs/prop_measure_matrice4e_0816.json (주력 1종)",
                            "outputs/reference_props.json (참조 프롭 3종)"],
        "R_definition_ko": ("R = 스윕 디스크 반경 = 회전중심 C 에서 날 끝까지. "
                            "C = 2날 프롭의 두 날끝 중점. reference_props.json 의 R_disc/2 "
                            "와 같은 뜻 → 사과-대-사과. "
                            "⚠접힌 프롭(m350rtk)만 예외: R = r_h + L 로 조립한다(§E)."),
        "root_definition_ko": ("r_root = 각폭 곡선이 허브를 벗어나는 반경(안쪽 국소 최소). "
                              "요약은 max(0.25R, r_root+0.03R) ~ 0.96R 만 쓴다. 이 하한이 "
                              "없으면 허브가 «가장 넓은 시위» 로 잡혀 값이 두 배로 뜬다."),
        "clean_blade_rule_ko": (f"r_root ≤ {ROOT_CLEAN_MAX} 인 날만 «깨끗» 으로 본다. "
                                "이보다 크면 추적기가 안쪽을 못 본 것이고(암·동체와 붙음), "
                                "요약 구간이 시위 최대점보다 바깥에서 시작해 c_max 를 놓친다. "
                                "⭐헤드라인은 언제나 `clean_blades` 다. `two_blade_mean_stat` "
                                "은 잘린 날이 섞이면 아래로 편향되므로 참고용이다."),
        "chord_definitions_ko": {
            "c_arc": "r·Δθ — 회전면 투영 폭. 사진이 줄 수 있는 유일한 값.",
            "c_caliper": "반경 r 원통 단면의 최대 캘리퍼 — drone_cad/reference_props 의 시위.",
            "bridge": "cal/arc. Mini2 공식 CAD 1.038, 이 파일이 Yuneec 에서 두 번째를 잰다."},
        "methods_ko": {"A": "극좌표 각폭 (r·Δθ)",
                       "B": "직교 — 스팬축으로 돌려 열마다 수직 폭(표본 방식이 A 와 다르다)",
                       "C": "3D 원통 단면 최대 캘리퍼 (STL 있는 기체만)"},
        "grading_ko": {"A": "그 프롭 자체의 제조사 공식 3D",
                       "A-": "그 프롭 자체의 3D 이나 제조사 공식임이 문서로 확인 안 됨",
                       "B": "그 프롭 실물/공식 렌더 사진의 정밀 계측",
                       "B-": "같은 사진이나 투영·겹침·워터마크·저해상도로 정밀도가 낮음",
                       "C": "같은 계열 다른 프롭에서 유추",
                       "D": "대리 — 다른 회사·다른 치수 프롭"},
    }}

    # ---------------------------------------------------------------- #
    #  V0 자 검증 — Yuneec 실물 3D 를 «정투영 렌더 → 2D 코드» 로 되재기    #
    # ---------------------------------------------------------------- #
    V0 = {"why_ko": (
        "새 대상에 대기 전에 답을 아는 물건으로 자를 검증한다. 형제 스크립트의 Mini 2 자 "
        "검증은 **실패**했다(3D 직접 0.2477 ↔ 2D 코드 2.52, 오차 918 %) — 그래서 2D 결과를 "
        "그냥 믿을 수 없다. 여기서는 «그 프롭 자체의 3D» 가 있는 Typhoon H480 프롭으로 검증을 "
        "새로 세운다: 같은 STL 을 회전축에서 내려다본 정투영 실루엣으로 굽고, 그 그림을 2D "
        "코드에 먹여 3D 직접값과 비교한다. 두 값 모두 arc(투영) 정의라 사과-대-사과다.")}
    yn_cw = REF / "prop_cw_assembly_remeshed_v3.stl"
    V0["cad_direct_3d"] = stl_prop_3d(yn_cw, "Yuneec Typhoon H480 CW — 3D 직접")
    png, meta = stl_ortho_render(yn_cw, "yuneec_cw_ortho_top.png")
    V0["ortho_render"] = meta
    V0["render_through_2d_pipeline"] = measure_image(
        png, "alpha", 1, how="isolated",
        label="같은 STL 의 정투영 상면 렌더 → 2D 코드", grade="검증")
    try:
        a3 = V0["cad_direct_3d"]["summary"]["arc_c_max_over_R"]["mean"]
        ph = V0["render_through_2d_pipeline"]["clean_blades"]["c_max_over_R"]["mean"]
        V0["verdict"] = dict(cad_direct_arc=a3, two_d_pipeline_same_object=ph,
                             error_pct=float(100 * (ph - a3) / a3),
                             pass_rule_ko="±5 % 안이면 아래 사진값을 쓸 만하다고 본다",
                             passed=bool(abs(100 * (ph - a3) / a3) <= 5.0))
    except Exception as e:                                     # pragma: no cover
        V0["verdict"] = {"error": repr(e)}
    doc["V0_ruler_validation"] = V0

    # ---------------------------------------------------------------- #
    #  A. typhoonh480 — Yuneec Typhoon H (H480)   [A-]                  #
    # ---------------------------------------------------------------- #
    A = {"identity": dict(
        prop="Propeller A / B (YUNTYH118A / YUNTYH118B)", dia_mm_nominal=228.6,
        dia_in=9.0, pitch_in=6.0,
        pitch_grade="DERIVED — Yuneec 은 지름·피치를 공표한 적이 없다(호환 프롭 판매 스펙)",
        blades=2, rotors=6, folding=False,
        source_ko="Yuneec 유럽 공식 스페어파츠 상점 + OEM 부품번호 (prop_identity_0816.json)"),
        "grade": "A-",
        "why_A_minus_ko": ("**그 프롭 자체의 3D 기하**가 있다(단위 mm). 다만 상류 저장소"
                           "(ethz-asl/rotors_simulator, Apache-2.0)가 이 메쉬의 출처를 밝히지 "
                           "않아 «Yuneec 공식 CAD» 라는 문서 근거가 없다 — 제조사 CAD 일 수도, "
                           "재현 모델일 수도 있다. 그래서 [A] 가 아니라 [A-] 다. "
                           "감사(docs/MESH_AUDIT_0816.md)가 이 메쉬를 «참조 밴드» 로 쓰고 있어 "
                           "그 판정의 강도도 여기 묶여 있다."),
        "note_ko": ("mini2 를 빼면 저장소에서 «기체별 프롭 3D» 가 있는 유일한 기체다. "
                    "그래서 이 기체가 자 검증(§V0)과 arc↔caliper 다리의 근거를 겸한다.")}
    A["cw"] = V0["cad_direct_3d"]
    A["ccw"] = stl_prop_3d(REF / "prop_ccw_assembly_remeshed_v3.stl",
                           "Yuneec Typhoon H480 CCW — 3D 직접")
    try:
        c1 = A["cw"]["summary"]["caliper_c_max_over_R"]["mean"]
        c2 = A["ccw"]["summary"]["caliper_c_max_over_R"]["mean"]
        A["cw_vs_ccw"] = dict(caliper_diff_pct=float(200 * abs(c1 - c2) / (c1 + c2)),
                              note_ko="거울쌍이므로 같아야 한다 — 이 차이가 3D 측정의 재현성.")
    except Exception:
        pass
    A["cross_check_legacy_ko"] = (
        "기존 원장 `outputs/reference_props.json` 의 yuneec_typhoon: 디스크 230.098 mm, "
        "caliper c_max/R 0.17688 @ 0.45R. 이 파일은 «독립 재구현» 으로 같은 STL 을 다시 "
        "재므로 두 값이 맞으면 두 코드가 서로를 검증한 것이다.")
    doc["A_typhoonh480"] = A

    # ---------------------------------------------------------------- #
    #  B. s1000plus — DJI Spreading Wings S1000+   [B-]  ⭐정면 신호 기체  #
    # ---------------------------------------------------------------- #
    B = {"identity": dict(
        prop="1552 / 1552R (거울쌍, 옥토라 4+4 = 8장)", dia_mm=381.0, dia_in=15.0,
        pitch_mm=132.1, pitch_in=5.2, blades=2, rotors=8, folding=True,
        material="접이 탄소 블레이드 + 금속 브래킷",
        source_ko="DJI 뉴스룸 «15 x 5.2 inch» + S1000+ Part 58 프로펠러 팩"),
        "grade": "B-",
        "why_important_ko": ("⭐s1000plus 는 정면에서도 신호가 사는 유일한 기체라 프롭 형상이 "
                            "특히 중요하다. 상면 평면 이미지에 8 로터가 전부 전개돼 있어 "
                            "«한 장에서 8 번» 잰다 — 8 로터가 서로 다른 방위를 보는데도 값이 "
                            "안 흩어지면, 그게 곧 투영 기울기 오차가 작다는 증거다.")}
    s1 = PHOTO / "s1000plus/s1000+_1.png"
    B["primary"] = measure_image(s1, "dark_on_light", 8, thr=140.0, how="walk",
                                 label="[B-] 상면 평면 — 8 로터 전개", grade="B-")
    for th in (110.0, 170.0):
        B[f"threshold_{int(th)}"] = _slim(measure_image(
            s1, "dark_on_light", 8, thr=th, how="walk",
            label=f"문턱값 감도 {th:.0f}", grade="B-"), drop=("props", "tip_diag"))
    B["caveats_ko"] = [
        "⚠ 이 폴더에 SOURCES.md 가 **없다** — 두 이미지의 출처가 기록돼 있지 않다. "
        "워터마크 «XCOPTER» 로 보아 판매점 자산이다. 계측 전에 출처부터 적어야 한다.",
        "⚠ 1552 는 «접이 탄소 블레이드 + 금속 브래킷» 이라 **뿌리 형상이 사출 소비자 프롭과 "
        "근본적으로 다르다.** 바깥쪽(0.3R~0.96R)은 쓰되, 뿌리 쪽을 소비자 프롭 법칙으로 "
        "채우면 틀린다.",
        "⭐ 로터마다 **한쪽 날이 암(arm)에 붙어 잘린다**(r_root 가 0.44R 로 잡힌다). "
        "그래서 헤드라인은 `clean_blades`(뿌리를 실제로 본 날)이고, 두 날 평균은 아래로 "
        "편향된 값으로 함께 남긴다.",
        "⭐ **문턱값이 지배 오차다.** 같은 그림을 110 / 140 / 170 으로 자르면 c_max/R 이 "
        "0.164 / 0.176 / 0.184 로 움직인다(±6 %). 프롭이 배경과 경계가 흐린 렌더라 그렇다 — "
        "이 기체 값에는 이 폭을 반드시 붙여 쓸 것.",
        "s1000+_2.png 는 3/4 뷰라 평면형 계측에 못 쓴다(투영 오차가 지배).",
    ]
    doc["B_s1000plus"] = B

    # ---------------------------------------------------------------- #
    #  C. phantom3 — DJI Phantom 3 Professional   [B]                   #
    # ---------------------------------------------------------------- #
    C = {"identity": dict(
        prop="9450 (자동조임)", dia_mm=240.0, dia_in=9.4, pitch_mm=127.0, pitch_in=5.0,
        blades=2, rotors=4, folding=False, mass_g_each=12.0,
        material="Glass fiber reinforced nylon",
        source_ko="DJI 공식 프롭 표 «Phantom 3 Series | 9450 | 24 x 12.7 cm»"),
        "grade": "B"}
    p3 = PHOTO / "phantom3/phantom3_d03_official_top.png"
    C["primary"] = measure_image(
        p3, "alpha", 4, how="envelope",
        label="[B] DJI 공식 상면 렌더 — 프롭 4개 전개", grade="B")
    C["walk_alternative"] = _slim(measure_image(
        p3, "alpha", 4, how="walk", label="같은 그림, 날끝을 walk 로", grade="B"),
        drop=("props", "tip_diag"))
    C["tip_method_note_ko"] = (
        "이 그림에서는 «허브까지 걸어가기»(walk)가 안 통한다 — 9450 은 허브가 작고 날이 "
        "동체 위를 덮어 «폭이 갑자기 커지는 지점» 이 안 생긴다. 프롭이 4개뿐이고 서로 멀어서 "
        "형제 스크립트의 봉투 날끝 방식이 오히려 튼튼하다(날끝-날끝 흩어짐 0.30 %). "
        "walk 는 대조로만 남긴다. ⇒ 날끝 찾는 법은 그림마다 골라야 하고, 어느 쪽을 썼는지 "
        "`tips_from` 에 적힌다.")

    crop, cmeta = crop_to_png(
        PHOTO / "phantom3/phantom3_p09_fccse_all_items_props_steelruler.jpg",
        (690, 370, 1010, 630), "phantom3_p09_props_crop.png")
    C["cross_check_fcc_p09"] = measure_image(
        crop, "not_blue", 4, thr=40.0, how="isolated",
        label="[B-] FCC 사진 — 9450 4장을 눕힘(강철자 동봉)", grade="B-")
    C["cross_check_fcc_p09"]["crop"] = cmeta
    C["caveats_ko"] = [
        "FCC 사진(p09)은 **비스듬히 내려다본 컷**이다. 프롭이 화면에서 세로로 누워 있어 길이 "
        "방향이 압축되고, 그러면 c_max/R 이 «위로» 치우친다. 1차 근거는 공식 상면 렌더이고 "
        "FCC 사진은 «같은 자릿수인지» 보는 교차검증으로만 쓴다.",
        "FCC 사진 해상도가 낮다(1048×697, 프롭 4장이 320×260 안에 들어간다) — 이 자료의 시위 "
        "정밀도는 ±3~5 %다.",
        "두 갈래(9450 ABS 자동조임 / 9450 탄소강화)는 **형상이 아니라 재질** 갈래다 — |Γ| "
        "축에서만 갈리고 평면형은 같다.",
    ]
    doc["C_phantom3"] = C

    # ---------------------------------------------------------------- #
    #  D. phantom4 — DJI Phantom 4 (원조 2016)   [C]                     #
    # ---------------------------------------------------------------- #
    doc["D_phantom4"] = {
        "identity": dict(
            prop_repo_current="9450", prop_likely="9450S (퀵릴리즈)",
            dia_mm=240.0, dia_in=9.4, pitch_mm=127.0, pitch_in=5.0, blades=2, rotors=4,
            mass_g_each=11.0, material="Glass fiber reinforced nylon",
            unresolved_ko=("DJI 공식 프롭 표는 «Phantom 4 | 9450», DJI 스토어는 «Phantom 4 "
                           "Series Quick Release Propellers = 9450S». 두 갈래 다 공칭은 "
                           "24 × 12.7 cm 로 같아서 **규격은 안 흔들리고** 허브(자동조임 ↔ "
                           "퀵릴리즈)와 날 세부만 갈린다. 부품번호는 «9450S 유력·미해결».")),
        "grade": "C",
        "geometry_source_ko": ("[C] 같은 세대·같은 공칭(24 × 12.7 cm)인 **phantom3 의 9450** "
                              "에서 유추한다 — 위 §C 의 수치를 그대로 쓴다."),
        "own_photos_verdict_ko": (
            "⛔⛔ **저장소의 assets/photos/phantom4/ 폴더는 다른 기체다.** 파일 5장이 전부 "
            "«Phantom 4 Pro+ V2.0» 이고 그 기체는 **9455S**(24 × 13.97 cm, 저소음)를 단다. "
            "게다가 5장 모두 3/4 투시 렌더라 평면형 계측 자체가 불가능하다(정면 상면이 없다). "
            "→ **이 폴더에서는 어떤 시위 수치도 뽑지 않았다.** 여기서 재면 «다른 프롭» 을 "
            "P4 에 입히는 새 오류가 된다. (폴더에 SOURCES.md 도 없다.)"),
        "expected_error_ko": ("9450(자동조임) ↔ 9450S(퀵릴리즈)는 허브가 다르고 날도 미세하게 "
                              "다르다. 공칭 지름·피치가 같으므로 c_max/R 차이는 ±3 % 안팎으로 "
                              "본다 — 다만 이건 «측정» 이 아니라 **추정**이다."),
        "promotion_path_ko": "9450S 단품의 평면 사진 한 장이면 [B] 로 올라간다.",
    }

    # ---------------------------------------------------------------- #
    #  E. m350rtk — DJI Matrice 350 RTK   [B-]                           #
    # ---------------------------------------------------------------- #
    E = {"identity": dict(
        prop="2110s (표준·순정)", variant_other="2112 고고도 저소음(별매)",
        dia_mm=533.4, dia_in=21.0, pitch_mm=254.0, pitch_in=10.0, blades=2, rotors=4,
        folding=True, part_number="CP.EN.00000470.01",
        source_ko=("DJI 공식 프롭 표의 M300 RTK 행 «2110 | 21 × 10 inch» + 2110s 가 "
                   "M300/M350 공용이라는 DJI 상품 설명. ⛔같은 표의 «M350 RTK | 1345S/1345T» "
                   "행은 DJI 자신의 오류다 — 1345 는 13 인치 Inspire 1 프롭이라 21 인치 "
                   "기체에 물리적으로 안 맞는다. 그 행을 인용하면 새 오류를 만든다.")),
        "grade": "B-"}
    fr = folded_rows(PHOTO / "m350rtk/m350rtk_c01_prop_2110s_pair.png")
    E["source"] = dict(file=fr["file"], n_props=fr["n_props"],
                       label="[B-] DJI 제품사진 — 2110s 1쌍(접힘, CW+CCW)")
    E["props"] = []
    for pi, pr in enumerate(fr["props"]):
        g = folded_geometry(pr, 533.4)
        g.update(prop_index=pi, bbox=pr["bbox"])
        E["props"].append(g)
    good = [p for p in E["props"] if p.get("c_max_over_R")]
    if good:
        v = np.array([p["c_max_over_R"] for p in good])
        E["summary"] = dict(
            n_props=len(good), c_max_over_R_mean=float(v.mean()),
            c_max_over_R_sd=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
            c_max_over_R_bracket=[float(min(p["c_max_over_R_bracket"][0] for p in good)),
                                  float(max(p["c_max_over_R_bracket"][1] for p in good))],
            r_h_over_R=float(np.mean([p["variants"]["mid"]["r_h_over_R"] for p in good])),
            blade_len_mm=float(np.mean([p["blade_len_mm"] for p in good])),
            hinge_radius_mm=float(np.mean([p["hinge_radius_mm"] for p in good])),
            c_max_mm=float(np.mean([p["c_max_mm"] for p in good])),
            c_over_cmax_mean={f"{q:.2f}": (float(np.mean(
                [p["variants"]["mid"]["summary"]["c_over_cmax"][f"{q:.2f}"]
                 for p in good if p["variants"]["mid"]["summary"]["c_over_cmax"]
                 [f"{q:.2f}"] is not None]))
                if any(p["variants"]["mid"]["summary"]["c_over_cmax"][f"{q:.2f}"]
                       is not None for p in good) else None) for q in GRID})
    E["caveats_ko"] = [
        "접힌 상태라 두 날이 겹친다. 겹친 구간의 시위는 «앞 날이 온전히 보인다» 는 가정 아래 "
        "이음매(그림자)로 갈랐다. 그 가정의 검사기가 `sum_check_pct` 다 — 앞·뒤 폭의 합이 "
        "봉투 폭과 같아야 한다(0 % 에 가까울수록 좋다).",
        "팁·뿌리 근처에서는 두 날이 실제로 떨어져 **가정 없이** 잰다(`n_rows_split`). "
        "그 구간이 위 가정의 대조군이다.",
        "사진 안에 물리 자가 없다. 축척은 **그림 안에서 조립**한다(R = r_h + L). 그래서 "
        "c_max/R 자체는 공칭 지름에 안 기대고, 공칭 533.4 mm 는 mm 로 환산할 때만 쓴다.",
        "힌지 높이가 직접 안 보여 **구간**으로 잡았다 — `c_max_over_R_bracket` 이 그 "
        "불확실성이고 `hinge_uncertainty_pct` 가 크기다. 이게 이 기체 값의 지배 오차다.",
        "원본이 520×694 로 작다(날 폭 40~50 px). 이음매 중심을 ±2 px 로 잡으면 시위에 "
        "±4 % 가 더 붙는다.",
        "2110s 는 «접이 브래킷 + 긴 블레이드» 라 뿌리 형상이 소비자 사출 프롭과 다르다.",
        "⚠ **프롭 2개가 11 % 어긋난다**(0.171 ↔ 0.190). 거울쌍이라 같아야 하므로 이 차이는 "
        "물리가 아니라 계측 오차다 — 겹친 구간에서 «앞 날» 이 좌우 어느 쪽인지가 두 프롭에서 "
        "반대라, 이음매 판정의 편향이 반대 방향으로 나타난 것으로 본다. 평균을 쓰되 밴드를 "
        "함께 적는다.",
        "⚠ 이 프롭은 0.25R 하한에서도 시위가 아직 오르는 중이라(최대가 0.26~0.32R) 규약값이 "
        "참 최대보다 작을 수 있다 — `variants.mid.unconstrained` 에 규약 밖 최대를 적었다.",
        "교차검증 후보(아직 안 씀): m350rtk_p05/p06 는 접힌 기체를 강철자와 함께 찍은 컷이라 "
        "**물리 축척**을 줄 수 있다. 다만 프롭이 암 위에 얹혀 자보다 높이 떠 있어 시차 보정이 "
        "필요하다 — 그 보정 없이 쓰면 x500v2 사진에서 이미 겪은 실수를 되풀이한다.",
    ]
    doc["E_m350rtk"] = E

    # ---------------------------------------------------------------- #
    #  F. x500v2 — Holybro X500 V2   [D]                                 #
    # ---------------------------------------------------------------- #
    doc["F_x500v2"] = {
        "identity": dict(
            prop="1045 (범용 규격명 = 10 × 4.5 in — 특정사 전용 부품이 아니다)",
            dia_mm=254.0, dia_in=10.0, pitch_mm=114.3, pitch_in=4.5, blades=2, rotors=4,
            folding=False,
            source_ko="Holybro 공식 킷 페이지 동봉품 «1045 Propellers (6 pcs) with retainer»"),
        "grade": "D",
        "measured": None,
        "verdict_ko": (
            "⛔ **1045 의 기하가 저장소에 없다. 이 기체는 지금 형상 근거가 «없다».**\n"
            " · [A] 막힘: Holybro 공식 STEP(`x500v2-frame.step`)에 프로펠러 솔리드가 하나도 "
            "없다(부품명 57종 전수 확인 기록이 prop_identity_0816.json 에 있다).\n"
            " · [B] 막힘: 프롭 근접컷 `x500v2_10_prop_1045_on_2216.jpg` 는 **양쪽 날끝이 "
            "화면 밖으로 잘려** R 을 정의할 수 없다. R 이 없으면 c_max/R 이 정의되지 않는다. "
            "나머지 프롭 사진 2장(_01·_09)은 투시 3/4 라 평면형이 안 나온다.\n"
            " · ⚠ 게다가 이 폴더에는 **전례가 있다**: `assets/photos/x500v2/SOURCES.md` 가 "
            "«_03 을 정투영 톱뷰로 오인하고 뽑은 치수는 시차 때문에 틀렸다» 를 반증으로 "
            "보존하고 있다. 같은 함정을 두 번 밟지 않는다.\n"
            "→ **빈칸으로 둔다.** 대리를 쓰려면 등급 [D] 와 아래 예상 오차를 함께 못박는다."),
        "current_proxy_ko": (
            "지금 코드가 쓰는 대리 `1345_prop_cw.stl` 은 **다른 프롭**이다 — PX4-gazebo-models "
            "의 13 인치급(실측 디스크 346.7 mm). 저장소 스스로 «X500 V2 의 프롭이 아니다» 라고 "
            "적어 두었다. 공칭 지름이 13 → 10 in 으로 1.3 배 다르다. "
            "참조 원장의 값: caliper c_max/R 0.225 @ 0.30R."),
        "expected_error_ko": (
            "같은 자로 잰 프롭들의 c_max/R(caliper)은 0.177(Yuneec 9 in) ~ 0.273(Solo 10 in) "
            "으로 **같은 10 in 급 안에서도 1.5 배** 벌어진다. 즉 1045 를 대리로 채울 때 "
            "c_max/R 의 예상 오차는 **±30 % 수준**이다. ⭐근거 없는 수를 만들어 채우지 않는다."),
        "promotion_path_ko": (
            "[B] 로 올리는 가장 짧은 길: 1045 **단품의 평면 사진**(또는 판매사 도면) 한 장. "
            "어느 회사 1045 인지도 함께 적어야 한다 — 범용 규격이라 회사마다 평면형이 다르다."),
        "photos_examined_ko": [
            "x500v2_10_prop_1045_on_2216.jpg — 1045 근접컷이지만 양 날끝이 프레임 밖(R 불가)",
            "x500v2_01_arf_front34_props.jpg — 투시 3/4",
            "x500v2_09_arf_iso34_props.jpg — 투시 3/4",
            "x500v2_03_top_ortho.jpg — 프롭이 아예 없고, 정투영이 아님이 이미 반증됨",
            "x500v2-frame.step — 공식 CAD 이나 프로펠러 솔리드 없음"],
    }

    # ---------------------------------------------------------------- #
    #  G. 한 자 위의 함대 표                                              #
    # ---------------------------------------------------------------- #
    def gg(path, default=None):
        o = doc
        for k in path:
            if not isinstance(o, dict) or o.get(k) is None:
                return default
            o = o[k]
        return o

    bridge = gg(["A_typhoonh480", "cw", "summary", "cal_over_arc", "mean"])
    rows = [
        dict(aircraft="typhoonh480", prop="Yuneec A/B", grade="A-",
             method="3D 직접(원통 단면 + 극좌표)", n_blades=4,
             c_max_over_R_arc=gg(["A_typhoonh480", "cw", "summary",
                                  "arc_c_max_over_R", "mean"]),
             c_max_over_R_caliper=gg(["A_typhoonh480", "cw", "summary",
                                      "caliper_c_max_over_R", "mean"]),
             caliper_is_measured=True,
             disc_dia_mm=gg(["A_typhoonh480", "cw", "summary", "disc_dia_mm"])),
        dict(aircraft="s1000plus", prop="DJI 1552", grade="B-",
             method="사진(상면 평면) — 뿌리를 본 «깨끗한» 날만",
             n_blades=gg(["B_s1000plus", "primary", "clean_blades", "n"]),
             c_max_over_R_arc=gg(["B_s1000plus", "primary", "clean_blades",
                                  "c_max_over_R", "mean"]),
             c_max_over_R_arc_sd=gg(["B_s1000plus", "primary", "clean_blades",
                                     "c_max_over_R", "sd"]),
             uncertainty_ko=("문턱값 감도가 지배 오차다 — 110/140/170 에서 "
                             "0.164 / 0.177 / 0.184. ±6 % 로 본다."),
             c_max_over_R_caliper=None, caliper_is_measured=False, disc_dia_mm=381.0),
        dict(aircraft="phantom3", prop="DJI 9450", grade="B",
             method="사진(DJI 공식 상면 렌더) — 뿌리를 본 «깨끗한» 날만",
             n_blades=gg(["C_phantom3", "primary", "clean_blades", "n"]),
             c_max_over_R_arc=gg(["C_phantom3", "primary", "clean_blades",
                                  "c_max_over_R", "mean"]),
             c_max_over_R_arc_sd=gg(["C_phantom3", "primary", "clean_blades",
                                     "c_max_over_R", "sd"]),
             uncertainty_ko="로터 간 흩어짐 + FCC 사진 교차검증의 어긋남을 함께 볼 것.",
             c_max_over_R_caliper=None, caliper_is_measured=False, disc_dia_mm=240.0),
        dict(aircraft="phantom4", prop="DJI 9450S(유력)", grade="C",
             method="phantom3 9450 에서 유추 — ⚠자체 측정 아님",
             n_blades=None,
             c_max_over_R_arc=gg(["C_phantom3", "primary", "clean_blades",
                                  "c_max_over_R", "mean"]),
             uncertainty_ko="phantom3 오차 + 9450↔9450S 갈래 ±3 %(추정).",
             c_max_over_R_caliper=None, caliper_is_measured=False, disc_dia_mm=240.0),
        dict(aircraft="m350rtk", prop="DJI 2110s", grade="B-",
             method="사진(접힌 쌍, 이음매 분리 + 축척 조립)", n_blades=2,
             c_max_over_R_arc=gg(["E_m350rtk", "summary", "c_max_over_R_mean"]),
             uncertainty_ko=("힌지 높이 구간 + 프롭 간 차이. `c_max_over_R_bracket` 참조. "
                             "⚠이 프롭은 0.25R 하한에서도 시위가 아직 오르는 중이라 규약값이 "
                             "참 최대보다 «작다» — `unconstrained_mid` 에 규약 밖 최대를 "
                             "따로 적었다."),
             c_max_over_R_caliper=None, caliper_is_measured=False, disc_dia_mm=533.4),
        dict(aircraft="x500v2", prop="1045(범용)", grade="D",
             method="근거 없음 — 빈칸", n_blades=0,
             c_max_over_R_arc=None, c_max_over_R_caliper=None,
             caliper_is_measured=False, disc_dia_mm=254.0),
    ]
    for r in rows:
        if r["c_max_over_R_arc"] and not r["c_max_over_R_caliper"] and bridge:
            r["c_max_over_R_caliper_bridged"] = float(r["c_max_over_R_arc"] * bridge)
    doc["G_fleet_one_ruler"] = dict(
        rows=rows, bridge_cal_over_arc=bridge,
        bridge_note_ko=("사진은 arc(투영 폭)만 준다. `drone_cad`·`reference_props` 의 시위는 "
                        "caliper(원통 단면 최대 캘리퍼)다. 둘을 잇는 계수 cal/arc 를 실물 3D "
                        "두 개에서 실측했다 — Mini 2 공식 CAD 1.038, 이 파일의 Yuneec(위 값). "
                        "`_bridged` 열은 그 계수를 곱한 **환산값**이지 직접 잰 값이 아니다."),
        legacy_ko=("현재 코드의 단일 상수 `CHORD_MAX_OVER_R = 0.25` (10기종 공통) 와 "
                   "3DR Solo 에서 베낀 시위 분포 `CHORD_FRAC`."),
        reference_band_ko=("같은 caliper 정의의 기존 참조 3종(outputs/reference_props.json): "
                           "Holybro 1345 0.225 · 3DR Solo 0.273 · Yuneec 0.1769."))

    # ---------------------------------------------------------------- #
    #  H. 한 줄 답 — 기종마다 «무엇을 쓸 것인가»                            #
    # ---------------------------------------------------------------- #
    p3v = gg(["C_phantom3", "primary", "clean_blades", "c_max_over_R", "mean"])
    p3x = gg(["C_phantom3", "cross_check_fcc_p09", "two_blade_mean_stat", "mean"])
    doc["C_phantom3"]["cross_check_verdict_ko"] = (
        f"공식 상면 렌더의 깨끗한 날 {p3v:.4f} ↔ FCC 사진의 두 날 평균 {p3x:.4f} — "
        f"차이 {100*abs(p3v-p3x)/p3v:.1f} %. 서로 «다른 사진·다른 방법» 인데 이만큼 맞으면 "
        "자릿수는 확정이다. 다만 FCC 사진 자체는 날별로 0.20~0.36 까지 흩어지므로(비스듬한 "
        "컷) **그 사진 하나로는 값을 정할 수 없다** — 렌더가 1차 근거다."
        if (p3v and p3x) else "교차검증 실패")

    hl = []
    hl.append(dict(
        aircraft="typhoonh480", prop="Yuneec Propeller A/B (YUNTYH118A/B)", grade="A-",
        use_c_max_over_R_arc=gg(["A_typhoonh480", "cw", "summary",
                                 "arc_c_max_over_R", "mean"]),
        use_c_max_over_R_caliper=gg(["A_typhoonh480", "cw", "summary",
                                     "caliper_c_max_over_R", "mean"]),
        uncertainty_pct=1.0,
        basis_ko="그 프롭 자체의 3D. CW·CCW 4날, 거울쌍 재현성 0.008 %.",
        caveat_ko="제조사 공식 CAD 라는 문서 근거가 없다 — 그래서 [A] 가 아니라 [A-]."))
    hl.append(dict(
        aircraft="s1000plus", prop="DJI 1552 / 1552R", grade="B-",
        use_c_max_over_R_arc=gg(["B_s1000plus", "primary", "clean_blades",
                                 "c_max_over_R", "mean"]),
        use_c_max_over_R_caliper=None, uncertainty_pct=6.0,
        basis_ko="상면 평면 사진, 로터 8개 중 깨끗한 날. 로터 간 흩어짐 2 %.",
        caveat_ko=("문턱값 감도가 ±6 % 로 지배 오차(110/140/170 → 0.164/0.177/0.184). "
                   "출처 미기록 판매점 이미지. 접이 탄소 블레이드라 뿌리 형상이 사출 프롭과 "
                   "다르다 — 0.3R 안쪽은 이 값으로 채우지 말 것.")))
    hl.append(dict(
        aircraft="phantom3", prop="DJI 9450", grade="B",
        use_c_max_over_R_arc=p3v, use_c_max_over_R_caliper=None, uncertainty_pct=3.0,
        basis_ko="DJI 공식 상면 렌더, 깨끗한 날 4장(로터 간 흩어짐 1.5 %).",
        caveat_ko="FCC 실물 사진과 자릿수는 맞지만 그 사진 자체는 흩어짐이 커서 못 쓴다."))
    hl.append(dict(
        aircraft="phantom4", prop="DJI 9450S (유력·미해결)", grade="C",
        use_c_max_over_R_arc=p3v, use_c_max_over_R_caliper=None, uncertainty_pct=5.0,
        basis_ko="⚠자체 측정 없음 — phantom3 의 9450 을 그대로 쓴다(같은 세대·같은 공칭).",
        caveat_ko=("저장소 phantom4 사진 폴더는 **다른 기체**(Phantom 4 Pro+ V2.0 = 9455S). "
                   "거기서 재면 새 오류다.")))
    hl.append(dict(
        aircraft="m350rtk", prop="DJI 2110s", grade="B-",
        use_c_max_over_R_arc=gg(["E_m350rtk", "summary", "c_max_over_R_mean"]),
        use_c_max_over_R_caliper=None, uncertainty_pct=10.0,
        basis_ko=("접힌 쌍 제품사진. 축척을 그림 안에서 조립(R = r_h + L) — 실측 힌지반경 "
                  "22.4 mm, 날 길이 244 mm, 최대 시위 48 mm."),
        caveat_ko=("프롭 2개가 0.171 ↔ 0.190 으로 11 % 어긋난다(거울쌍이라 같아야 한다). "
                   "여기에 힌지 높이 구간 ±6 % 가 더 붙는다 ⇒ 실질 밴드 0.165~0.190. "
                   "저해상도(520×694)와 겹친 날의 이음매 판정이 원인이다.")))
    hl.append(dict(
        aircraft="x500v2", prop="1045 (범용 규격)", grade="D",
        use_c_max_over_R_arc=None, use_c_max_over_R_caliper=None, uncertainty_pct=None,
        basis_ko="⛔없음 — 빈칸으로 둔다.",
        caveat_ko=("공식 CAD 에 프롭이 없고, 프롭 근접 사진은 양 날끝이 프레임 밖이라 R 을 "
                   "정의할 수 없다. 대리를 쓰면 등급 [D] 와 ±30 % 를 함께 적을 것.")))
    legacy = 0.25
    for h in hl:
        v = h["use_c_max_over_R_arc"]
        h["legacy_constant_error_pct"] = (
            float(100 * (legacy - v * (bridge or 1.0)) / (v * (bridge or 1.0)))
            if v else None)
    doc["H_headline"] = dict(
        rows=hl,
        legacy_constant=legacy,
        legacy_note_ko=("`legacy_constant_error_pct` = 현재의 단일 상수 0.25 가 «그 기체의 진짜 "
                        "프롭» 보다 몇 % 넓은가. caliper 축으로 환산해 비교했다(사진값 × "
                        "cal/arc). ⭐지금 코드는 6기종 전부에 같은 0.25 를 걸고 있으므로, "
                        "이 열이 곧 «같은 프로펠러를 달아 놓은 대가» 다."),
        headline_ko=("6기종 중 **4기종은 새로 쟀고**(typhoonh480 [A-] · phantom3 [B] · "
                     "s1000plus [B-] · m350rtk [B-]), 1기종은 같은 계열에서 유추했고"
                     "(phantom4 [C]), **1기종은 근거가 없어 빈칸으로 뒀다**(x500v2 [D])."))

    doc["_meta"]["runtime_s"] = round(time.time() - t0, 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    print("wrote", OUT, f"({OUT.stat().st_size/1024:.0f} KB, {doc['_meta']['runtime_s']} s)")
    return doc


if __name__ == "__main__":
    main()
