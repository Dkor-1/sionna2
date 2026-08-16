# -*- coding: utf-8 -*-
"""제품사진에서 **팁이 정말 뭉툭한가** 를 잰다 (감사 I8 ⓓ).

CAD·GLB 와 독립인 증거가 필요하다. 흰 배경 제품사진의 실루엣을 뽑아, 허브 중심에서
반경 r 마다 날의 각폭 Δφ 를 재고 시위 c(r) ≈ r·Δφ 로 읽는다(투영 평면형).
⚠ 이 자는 «투영» 이라 스윕·비틀림 때문에 참시위를 약간 크게 읽는다(감사 부록 C 와 같은 한계).
   그래서 절대값이 아니라 **팁 쪽 c/c_max 의 모양**만 결론에 쓴다.
"""
import sys
import numpy as np
from PIL import Image

PH = {
    "matrice4e_1157F": "/workspace/sionna/assets/photos/matrice4e/matrice4e_c02_prop_standard_1157F_pair.jpg",
    "matrice4e_1154F": "/workspace/sionna/assets/photos/matrice4e/matrice4e_c01_prop_low_noise_1154F_pair.jpg",
    "mavic4pro_1158F": "/workspace/sionna/assets/photos/mavic4pro/mavic4pro_c10_propeller_pair_1158F.jpg",
}


def silhouette(path, thr=200):
    im = np.array(Image.open(path).convert("L"), float)
    return im < thr


def biggest_blob(mask):
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def profile(mask, tag):
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    order = np.argsort(sizes)[::-1]
    out = []
    for oi in order[:2]:                      # 사진에 프롭이 2개
        m = lab == (oi + 1)
        ys, xs = np.nonzero(m)
        # 허브 중심 = 실루엣의 «가장 두꺼운» 곳이 아니라, 최대 관성축의 중점
        c = np.array([xs.mean(), ys.mean()])
        pts = np.c_[xs, ys] - c
        ev, evec = np.linalg.eigh(np.cov(pts.T))
        ax = evec[:, -1]                       # 스팬 방향
        s = pts @ ax                            # 스팬 좌표
        t = pts @ np.array([-ax[1], ax[0]])     # 시위 방향
        R = max(s.max(), -s.min())
        for sign, nm in ((+1, "A"), (-1, "B")):
            sel = (sign * s) > 0
            ss, tt = sign * s[sel], t[sel]
            rr = np.arange(0.30, 1.0005, 0.01)
            c_r = []
            band = 0.004 * R
            for x in rr:
                q = np.abs(ss - x * R) <= band
                c_r.append((tt[q].max() - tt[q].min()) if q.sum() > 3 else np.nan)
            c_r = np.array(c_r)
            cmax = np.nanmax(c_r)
            out.append((f"{tag}-blob{oi}-{nm}", R, rr, c_r / cmax,
                        rr[int(np.nanargmax(c_r))], cmax / R))
    return out


def main():
    for tag, path in PH.items():
        try:
            m = silhouette(path)
        except Exception as e:
            print(tag, "ERR", e)
            continue
        rows = profile(m, tag)
        print(f"\n=== {tag}  ({path.split('/')[-1]})")
        for nm, R, rr, cn, rpk, cmaxR in rows:
            idx = {x: i for i, x in enumerate(np.round(rr, 2))}
            def g(x):
                return cn[idx[round(x, 2)]]
            print(f" {nm}: R_px {R:6.1f}  c_max/R {cmaxR:.3f} @ r/R {rpk:.2f} | "
                  f"c/c_max: 0.70 {g(0.70):.3f}  0.80 {g(0.80):.3f}  0.90 {g(0.90):.3f}  "
                  f"0.95 {g(0.95):.3f}  0.97 {g(0.97):.3f}  0.99 {g(0.99):.3f}  1.00 {g(1.00):.3f}")


if __name__ == "__main__":
    main()
