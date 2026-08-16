# -*- coding: utf-8 -*-
"""ⓓ 독립 증거 — **CAD 를 안 쓰고** 제품사진 실루엣만으로 «실물 팁이 뭉툭한가» 를 본다.

GLB 는 1k 로 간략화된 게임용 자산이라 팁이 간략화로 뭉툭해졌을 가능성이 있다. 그 의심을
사진으로 가른다. 사진은 **투영** 평면형이라 참시위를 크게 읽지만, 팁 근처는 비틀림이 작고
여기서 보는 것은 **정규화 곡선의 모양**(c(r)/c_max)이라 그 편향이 크게 상쇄된다.

방법: 흰 배경 대비 임계 → 연결성분 → 성분 무게중심을 허브로(2날 프롭은 점대칭) →
      화소의 (r, φ) → 반경빈마다 한쪽 날의 방위폭 × r = 투영 시위.
⛔ 저장소 코드 무변경. GPU 미사용.
"""
import glob
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/d_photo_tip.json"
PH = "/workspace/sionna/assets/photos"
FILES = [f"{PH}/mini2/mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg",
         f"{PH}/mini2/mini2_t28_fcc_mt2wd_propeller_motor_view.jpg",
         f"{PH}/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg",
         f"{PH}/matrice4e/matrice4e_c01_prop_low_noise_1154F_pair.jpg",
         f"{PH}/mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg"]
GRID = np.array([0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.94, 0.95, 0.96,
                 0.97, 0.98, 0.99, 0.995])


def profile(mask, nbin=220):
    ys, xs = np.nonzero(mask)
    cy, cx = ys.mean(), xs.mean()
    dy, dx = ys - cy, xs - cx
    r = np.hypot(dx, dy)
    R = r.max()
    ph = np.arctan2(dy, dx)
    #  두 날 중 하나만: 주축(가장 먼 화소 방향)에서 ±90° 안
    i = int(np.argmax(r))
    a0 = ph[i]
    rel = (ph - a0 + np.pi) % (2 * np.pi) - np.pi
    sel = np.abs(rel) < np.pi / 2
    r, rel = r[sel], rel[sel]
    edges = np.linspace(0, R, nbin + 1)
    idx = np.clip(np.digitize(r, edges) - 1, 0, nbin - 1)
    rm = 0.5 * (edges[:-1] + edges[1:])
    c = np.full(nbin, np.nan)
    for b in range(nbin):
        m = idx == b
        if m.sum() >= 6:
            c[b] = rm[b] * (rel[m].max() - rel[m].min())
    ok = np.isfinite(c)
    cmax = float(np.nanmax(c))
    return dict(R_px=float(R), c_max_px=cmax, c_max_over_R=cmax / float(R),
                c_norm={f"{g:.3f}": round(float(np.interp(g, rm[ok] / R, c[ok]) / cmax), 4)
                        for g in GRID},
                n_px=int(sel.sum()))


def main():
    res = {"_meta": dict(what="제품사진 실루엣 투영 평면형 — CAD 와 독립인 팁 증거",
                         caveat="투영이라 참시위보다 좁게 읽힌다(비틀림). 모양 비교용.",
                         grid=GRID.tolist())}
    for f in FILES:
        if not os.path.exists(f):
            continue
        im = np.asarray(Image.open(f).convert("RGB"), float)
        # 흰 배경에서 얼마나 떨어졌나
        d = 255.0 - im.min(2)
        mk = d > 60
        mk = ndimage.binary_opening(mk, np.ones((3, 3)))
        lab, n = ndimage.label(mk)
        sizes = ndimage.sum(mk, lab, range(1, n + 1))
        order = np.argsort(sizes)[::-1]
        rows = []
        for j in order[:6]:
            if sizes[j] < 0.02 * mk.sum():
                continue
            m = lab == (j + 1)
            ys, xs = np.nonzero(m)
            # 워터마크·자 같은 가로줄 제거: 세장비가 프롭답지 않으면 버린다
            h, w = int(ys.max() - ys.min()) + 1, int(xs.max() - xs.min()) + 1
            if min(h, w) < 0.04 * max(h, w) or max(h, w) < 80:
                continue
            rows.append(dict(px=int(sizes[j]), bbox=[int(w), int(h)], **profile(m)))
        res[os.path.basename(f)] = rows
        for k, r in enumerate(rows):
            print(f"{os.path.basename(f)[:38]:38s} #{k} R={r['R_px']:.0f}px "
                  f"c_max/R={r['c_max_over_R']:.4f}  " +
                  " ".join(f"{g:.2f}:{r['c_norm'][f'{g:.3f}']:.3f}"
                           for g in (0.70, 0.90, 0.95, 0.98, 0.99)))
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
