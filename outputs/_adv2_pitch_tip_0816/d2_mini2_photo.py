# -*- coding: utf-8 -*-
"""ⓓ 핵심 대조 — **실물 Mini 2 프롭 사진**의 팁이 GLB 만큼 뭉툭한가.

왜 필요한가: 감사의 팁 근거는 전부 `WM161_zhankai_1k.glb` 에서 나왔는데 그 파일은 **1k 로
간략화된 게임용 자산**이다. 간략화가 팁을 뭉개 «뭉툭하게» 만들었을 수 있다. 같은 프롭의
실물 사진(FCC 제출 사진)으로 가른다.

Mini 2 프롭은 **접이식 2날**이라 정지 상태에서 두 날의 사잇각이 180° 가 아니다 →
무게중심을 허브로 쓸 수 없다. 그래서 **두 날의 주축을 각각 세워 교점**을 허브로 잡는다.
⛔ 저장소 코드 무변경. GPU 미사용.
"""
import json

import numpy as np
from PIL import Image
from scipy import ndimage

OUT = "/workspace/sionna/outputs/_adv2_pitch_tip_0816/d2_mini2_photo.json"
IMGS = [("/workspace/sionna/assets/photos/mini2/mini2_c07_fcc_mt2wd_propeller_2blade_ruler.jpg", 100),
        ("/workspace/sionna/assets/photos/mini2/mini2_t28_fcc_mt2wd_propeller_motor_view.jpg", 100)]
GRID = np.array([0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.92, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99])


def biggest(mask):
    lab, n = ndimage.label(ndimage.binary_opening(mask, np.ones((3, 3))))
    sz = ndimage.sum(mask, lab, range(1, n + 1))
    return lab == (int(np.argmax(sz)) + 1)


def axis_of(P):
    c = P.mean(0)
    _, U = np.linalg.eigh(np.cov((P - c).T))
    return c, U[:, -1]


def hub_from_two_blades(P, iters=6):
    """두 날의 주축 교점 = 허브. 초기 중심은 무게중심."""
    c = P.mean(0)
    for _ in range(iters):
        ang = np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0])
        # 각도를 2군집으로 — 원형 k-means 2개
        v = np.c_[np.cos(ang), np.sin(ang)]
        m0 = v[np.argmax(np.linalg.norm(P - c, axis=1))]
        m1 = -m0
        for _ in range(25):
            d0 = v @ m0
            d1 = v @ m1
            g = d0 >= d1
            if g.sum() < 20 or (~g).sum() < 20:
                break
            m0 = v[g].mean(0) / np.linalg.norm(v[g].mean(0))
            m1 = v[~g].mean(0) / np.linalg.norm(v[~g].mean(0))
        A = []
        b = []
        for sel in (g, ~g):
            if sel.sum() < 20:
                continue
            c0, u = axis_of(P[sel])
            nrm = np.array([-u[1], u[0]])       # 직선 n·(x−c0)=0
            A.append(nrm)
            b.append(nrm @ c0)
        if len(A) < 2:
            break
        c = np.linalg.lstsq(np.array(A), np.array(b), rcond=None)[0]
    return c, g


def profile(P, c, sel):
    d = P[sel] - c
    r = np.hypot(d[:, 0], d[:, 1])
    R = r.max()
    ph = np.arctan2(d[:, 1], d[:, 0])
    a0 = ph[int(np.argmax(r))]
    rel = (ph - a0 + np.pi) % (2 * np.pi) - np.pi
    nb = 200
    e = np.linspace(0, R, nb + 1)
    i = np.clip(np.digitize(r, e) - 1, 0, nb - 1)
    rm = 0.5 * (e[:-1] + e[1:])
    ch = np.full(nb, np.nan)
    for bb in range(nb):
        m = i == bb
        if m.sum() >= 6:
            ch[bb] = rm[bb] * (rel[m].max() - rel[m].min())
    ok = np.isfinite(ch)
    cm = float(np.nanmax(ch))
    return dict(R_px=float(R), c_max_over_R=cm / float(R), n_px=int(sel.sum()),
                c_norm={f"{g:.3f}": round(float(np.interp(g, rm[ok] / R, ch[ok]) / cm), 4)
                        for g in GRID})


def main():
    res = {"_meta": dict(what="실물 Mini 2 프롭 사진 — GLB 팁이 간략화 인공물인지 가른다",
                         method="어두운 화소 → 최대 연결성분 → 두 날 주축 교점을 허브로",
                         caveat="사진은 투영 + 원근이라 절대 c/R 은 못 믿는다. 정규화 모양만 본다.")}
    for path, thr in IMGS:
        im = np.asarray(Image.open(path).convert("RGB"), float)
        m = biggest(im.min(2) < thr)
        ys, xs = np.nonzero(m)
        P = np.c_[xs.astype(float), ys.astype(float)]
        c, g = hub_from_two_blades(P)
        rows = []
        for sel, nm in ((g, "blade_a"), (~g, "blade_b")):
            if sel.sum() < 200:
                continue
            rows.append(dict(blade=nm, **profile(P, c, sel)))
        res[path.split("/")[-1]] = dict(hub_px=[round(float(x), 1) for x in c],
                                        n_px=int(m.sum()), blades=rows)
        for r in rows:
            print(f"{path.split('/')[-1][:40]:40s} {r['blade']} R={r['R_px']:.0f}px "
                  f"c_max/R={r['c_max_over_R']:.4f}  " +
                  " ".join(f"{x:.2f}:{r['c_norm'][f'{x:.3f}']:.3f}"
                           for x in (0.70, 0.90, 0.95, 0.98, 0.99)))
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
