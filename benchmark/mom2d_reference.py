# -*- coding: utf-8 -*-
"""mom2d_reference.py — 2 차원 EFIE 모멘트법(MoM) **참조해 솔버** (PEC, TM·TE 양편파)

무엇에 쓰는가
-------------
`docs/PTD_ILDC_FORMULATION.md` §8 Rung 2 (평판 모노스태틱 σ(θ)) 의 **참조해**를 만든다.
Rung 2 가 요구하는 참조는 MoM/실측인데 문서 §10 이 적었듯 R2-a/R2-c/R2-d 는 전부
그림·이차출처뿐이라 **숫자를 읽어올 수 없다**. 그래서 참조를 직접 푼다 — 근사 없이
적분방정식을 그대로 이산화한 MoM 이다. PO 도 PTD 도 들어가지 않으므로 독립 기준이다.

⚠ 2 차원이다. 무한히 긴 띠(strip)를 푼다. 3 차원 직사각 평판(a × b, b ≫ a)의 주평면
   컷과는 정확한 대응관계가 있다(구동 스크립트 §참조):  sigma_3D = (2 b^2 / lam) sigma_2D.
   대응이 정확한 것은 PO 항과 **시선에 수직인 두 모서리(on-cone)** 이고, 나머지 두
   모서리(길이 a, off-cone)는 b 가 커질수록 사라진다 — 구동 스크립트가 그 잔차를 잰다.

정식화
------
시간규약 e^{+jwt}, 발산파 H_0^{(2)}. 입사 평면파는

    E^inc(r) = e_hat * exp(+j k u.r)      (u = 표적→레이더, 진행방향 d = -u)

  TM (E ∥ 불변축): 미지량 J_y, **펄스 기저 + 점정합**.
  TE (H ∥ 불변축): 미지량 J_t, **루프탑(삼각) 기저 + 갤러킨**.
      TE 는 모서리조건(모서리에 수직인 전류는 sqrt(rho) 로 0 에 수렴)을 루프탑이 자동으로
      만족한다. 로그 특이점은 해석적으로 떼어내고(안쪽 적분 닫힌형 + 바깥 등비격자 GL)
      나머지 매끈한 부분만 수치적분한다.

둘 다 같은 정규화의 복소진폭을 돌려준다

    F = e_r . (I - u u) . Integral[ J(r') e^{j k u.r'} dl' ]
    sigma_2D = (k Z^2 / 4) |F|^2 ,  등가폭 W = (Z/2) F [m],  sigma_2D = k |W|^2

검증 (self-test: `python benchmark/mom2d_reference.py`)
------------------------------------------------------
원형 PEC 실린더의 **정확 급수해**(Bessel/Hankel)와 대조한다. kA = 1.0/2.6/4.6,
세그먼트 60→240 에서 TM·TE 모두 |오차| < 0.005 dB 로 2 차 수렴한다.
"""
from __future__ import annotations

import numpy as np
from scipy.special import hankel2, jv, jvp, yv, yvp

Z0 = 376.730313668
EULER = 0.5772156649015329


# --------------------------------------------------------------------------- #
#  kernel with the log singularity split off
# --------------------------------------------------------------------------- #
def _S(x):
    """H_0^{(2)}(x) + j(2/pi) ln x   — finite as x -> 0."""
    x = np.asarray(x, float)
    tiny = x < 1e-30
    xs = np.where(tiny, 1.0, x)
    out = hankel2(0, xs) + 1j * (2.0 / np.pi) * np.log(xs)
    lim = 1.0 + 1j * (2.0 / np.pi) * (np.log(2.0) - EULER)
    return np.where(tiny, lim, out)


def _G_smooth(k, R):
    """G + (1/2pi) ln R  where G = -(j/4) H_0^{(2)}(kR)."""
    return -0.25j * (_S(k * R) - 1j * (2.0 / np.pi) * np.log(k))


def _log_int_linear(p, q0, tau, L):
    """I0 = int_0^L ln R ds',  I1 = int_0^L s' ln R ds',  R = |p - (q0 + s' tau)|."""
    d = np.asarray(p, float) - q0
    s0 = d @ tau
    h = np.linalg.norm(d - s0[..., None] * tau, axis=-1)
    u1, u2 = -s0, L - s0

    def A(u):
        r2 = u * u + h * h
        lg = np.where(r2 > 0, 0.5 * np.log(np.where(r2 > 0, r2, 1.0)), 0.0)
        at = np.where(h > 0, h * np.arctan2(u, np.where(h > 0, h, 1.0)), 0.0)
        return u * lg - u + at

    def B(u):
        r2 = u * u + h * h
        return 0.25 * (np.where(r2 > 0, r2 * np.log(np.where(r2 > 0, r2, 1.0)), 0.0) - u * u)

    I0 = A(u2) - A(u1)
    return I0, (B(u2) - B(u1)) + s0 * I0


def _gl(n):
    x, w = np.polynomial.legendre.leggauss(n)
    return 0.5 * (x + 1.0), 0.5 * w


def _graded(sing, nsub=10, ratio=0.35, ng=10):
    """Composite GL on [0,1], geometrically graded toward `sing` (0.0, 1.0 or None)."""
    xg, wg = _gl(ng)
    if sing is None:
        return xg, wg
    e = [0.0, 1.0]
    r = 1.0
    for _ in range(nsub):
        r *= ratio
        e.append(1.0 - r if sing == 0.0 else r)
    e = np.unique(np.clip(np.array(e), 0.0, 1.0))
    xs = [a + (b - a) * xg for a, b in zip(e[:-1], e[1:])]
    ws = [(b - a) * wg for a, b in zip(e[:-1], e[1:])]
    return np.concatenate(xs), np.concatenate(ws)


def pair_moments(P0a, P1a, P0b, P1b, k, near):
    """M[(p,q)] = int_A int_B xi^p xi'^q G dl' dl   (xi, xi' normalised 0..1)."""
    La = float(np.linalg.norm(P1a - P0a))
    Lb = float(np.linalg.norm(P1b - P0b))
    tb = (P1b - P0b) / Lb

    ng = 16 if near else 10
    xa, wa = _gl(ng)
    xb, wb = _gl(ng)
    A = P0a + xa[:, None] * (P1a - P0a)
    B = P0b + xb[:, None] * (P1b - P0b)
    R = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=-1)
    Gs = _G_smooth(k, R)
    M = {}
    for p in (0, 1):
        for q in (0, 1):
            M[(p, q)] = La * Lb * np.einsum("a,b,ab->", wa * xa ** p, wb * xb ** q, Gs)

    if not near:
        Rl = np.log(R)
        for p in (0, 1):
            for q in (0, 1):
                M[(p, q)] -= (1.0 / (2 * np.pi)) * La * Lb * np.einsum(
                    "a,b,ab->", wa * xa ** p, wb * xb ** q, Rl)
        return M

    tol = 1e-9 * max(La, Lb)
    if min(np.linalg.norm(P0a - P0b), np.linalg.norm(P0a - P1b)) < tol:
        sing = 0.0
    elif min(np.linalg.norm(P1a - P0b), np.linalg.norm(P1a - P1b)) < tol:
        sing = 1.0
    else:
        sing = None
    if sing is None:                                  # self pair: split at both ends
        x0, w0 = _graded(0.0); x1, w1 = _graded(1.0)
        xs = np.concatenate([0.5 * x0, 0.5 + 0.5 * x1])
        ws = np.concatenate([0.5 * w0, 0.5 * w1])
    else:
        xs, ws = _graded(sing)
    Aa = P0a + xs[:, None] * (P1a - P0a)
    I0, I1 = _log_int_linear(Aa, P0b, tb, Lb)
    for p in (0, 1):
        wgt = ws * xs ** p * La
        M[(p, 0)] -= (1.0 / (2 * np.pi)) * float(np.sum(wgt * I0))
        M[(p, 1)] -= (1.0 / (2 * np.pi)) * float(np.sum(wgt * I1)) / Lb
    return M


# --------------------------------------------------------------------------- #
#  geometry
# --------------------------------------------------------------------------- #
def strip_nodes(a, M):
    x = np.linspace(-a / 2, a / 2, M + 1)
    return np.stack([x, np.zeros_like(x)], axis=1)


def circle_nodes(rad, M):
    t = np.linspace(0.0, 2 * np.pi, M + 1)
    return np.stack([rad * np.cos(t), rad * np.sin(t)], axis=1)


# --------------------------------------------------------------------------- #
#  TM: pulse basis + point matching
# --------------------------------------------------------------------------- #
def assemble_tm(nodes, k):
    P0, P1 = nodes[:-1], nodes[1:]
    M = len(P0)
    L = np.linalg.norm(P1 - P0, axis=1)
    tau = (P1 - P0) / L[:, None]
    C = 0.5 * (P0 + P1)
    xg, wg = _gl(12)
    Zm = np.empty((M, M), complex)
    for n in range(M):
        Q = P0[n] + xg[:, None] * (P1[n] - P0[n])
        R = np.linalg.norm(C[:, None, :] - Q[None, :, :], axis=-1)
        sm = L[n] * (_G_smooth(k, R) @ wg)
        I0, _ = _log_int_linear(C, P0[n], tau[n], L[n])
        Zm[:, n] = 1j * k * Z0 * (sm - (1.0 / (2 * np.pi)) * I0)   # jkZ int_n G dl'
    return dict(Z=np.linalg.inv(Zm), C=C, L=L, tau=tau, k=k)


def solve_tm(pre, u):
    k, C, L, tau = pre["k"], pre["C"], pre["L"], pre["tau"]
    V = np.exp(1j * k * (C @ u))
    J = pre["Z"] @ V
    ph = k * (tau @ u) * L / 2.0
    return complex(np.sum(J * L * np.exp(1j * k * (C @ u)) * np.sinc(ph / np.pi))), J


# --------------------------------------------------------------------------- #
#  TE: rooftop basis + Galerkin
# --------------------------------------------------------------------------- #
def assemble_te(nodes, k, closed=False):
    P0, P1 = nodes[:-1], nodes[1:]
    M = len(P0)
    L = np.linalg.norm(P1 - P0, axis=1)
    tau = (P1 - P0) / L[:, None]
    C = 0.5 * (P0 + P1)

    pairs = ([(i, (i + 1) % M) for i in range(M)] if closed
             else [(i, i + 1) for i in range(M - 1)])
    NB = len(pairs)

    Mom = {}
    for m in range(M):
        for n in range(M):
            touch = (m == n) or min(
                np.linalg.norm(P0[m] - P0[n]), np.linalg.norm(P0[m] - P1[n]),
                np.linalg.norm(P1[m] - P0[n]), np.linalg.norm(P1[m] - P1[n])) < 1e-9 * L[m]
            d = np.linalg.norm(C[m] - C[n])
            Mom[(m, n)] = pair_moments(P0[m], P1[m], P0[n], P1[n], k,
                                       bool(touch or d < 2.5 * max(L[m], L[n])))

    def wm(mom, km, kn):
        if km == 'r' and kn == 'r':
            return mom[(1, 1)]
        if km == 'r' and kn == 'f':
            return mom[(1, 0)] - mom[(1, 1)]
        if km == 'f' and kn == 'r':
            return mom[(0, 1)] - mom[(1, 1)]
        return mom[(0, 0)] - mom[(1, 0)] - mom[(0, 1)] + mom[(1, 1)]

    supp = [[(s1, 'r', +1.0 / L[s1]), (s2, 'f', -1.0 / L[s2])] for (s1, s2) in pairs]

    Zm = np.zeros((NB, NB), complex)
    for i in range(NB):
        for j in range(NB):
            acc = 0.0 + 0j
            for (sm, km, dm) in supp[i]:
                for (sn, kn, dn) in supp[j]:
                    mom = Mom[(sm, sn)]
                    acc += (1j * k * Z0 * float(tau[sm] @ tau[sn]) * wm(mom, km, kn)
                            + (Z0 / (1j * k)) * dm * dn * mom[(0, 0)])
            Zm[i, j] = acc

    return dict(Z=np.linalg.inv(Zm), supp=supp, P0=P0, P1=P1, L=L, tau=tau, k=k, NB=NB)


def solve_te(pre, u, e_r):
    k, L, tau, supp = pre["k"], pre["L"], pre["tau"], pre["supp"]
    P0, P1, NB = pre["P0"], pre["P1"], pre["NB"]
    xg, wg = _gl(12)
    V = np.zeros(NB, complex)
    for i in range(NB):
        for (sm, km, dm) in supp[i]:
            r = P0[sm] + xg[:, None] * (P1[sm] - P0[sm])
            w = xg if km == 'r' else (1.0 - xg)
            ph = np.exp(1j * k * (r @ u))
            V[i] += L[sm] * float(tau[sm] @ e_r) * np.sum(wg * w * ph)
    I = pre["Z"] @ V
    return complex(np.sum(I * V)), I          # Galerkin: far-field weights == excitation


# --------------------------------------------------------------------------- #
#  exact PEC circular cylinder (2-D Mie)
# --------------------------------------------------------------------------- #
def cyl_exact(kA, k, pol, nmax=None):
    n = np.arange(-(nmax or int(kA + 30)), (nmax or int(kA + 30)) + 1)
    if pol == "TM":
        a = -jv(n, kA) / hankel2(n, kA)
    else:
        h2p = jvp(n, kA) - 1j * yvp(n, kA)
        a = -jvp(n, kA) / h2p
    return (4.0 / k) * abs(np.sum(((-1.0) ** n) * a)) ** 2


# --------------------------------------------------------------------------- #
#  self-test: exact circular cylinder
# --------------------------------------------------------------------------- #
def selftest(verbose=True):
    k = 2 * np.pi
    u = np.array([1.0, 0.0])
    e_r = np.array([0.0, 1.0])
    rows = []
    for kA in (1.0, 2.6, 4.6):
        for M in (60, 120, 240):
            nd = circle_nodes(kA / k, M)
            s_tm = (k * Z0 ** 2 / 4) * abs(solve_tm(assemble_tm(nd, k), u)[0]) ** 2
            s_te = (k * Z0 ** 2 / 4) * abs(
                solve_te(assemble_te(nd, k, closed=True), u, e_r)[0]) ** 2
            r = dict(kA=kA, n_seg=M,
                     tm_err_db=float(10 * np.log10(s_tm / cyl_exact(kA, k, "TM"))),
                     te_err_db=float(10 * np.log10(s_te / cyl_exact(kA, k, "TE"))))
            rows.append(r)
            if verbose:
                print("  kA=%.1f  seg=%3d   TM %+0.4f dB   TE %+0.4f dB"
                      % (kA, M, r["tm_err_db"], r["te_err_db"]))
    worst = max(max(abs(r["tm_err_db"]), abs(r["te_err_db"])) for r in rows)
    fine = [r for r in rows if r["n_seg"] == 240]
    worst_fine = max(max(abs(r["tm_err_db"]), abs(r["te_err_db"])) for r in fine)
    return dict(rows=rows, worst_abs_db=float(worst),
                worst_abs_db_at_240seg=float(worst_fine),
                reference="exact 2-D PEC circular cylinder eigenfunction series",
                passes=bool(worst_fine < 0.01))


if __name__ == "__main__":
    print("== mom2d_reference self-test vs exact PEC circular cylinder ==")
    out = selftest()
    print("  worst |err| = %.4f dB (all), %.4f dB (240 seg)  ->  %s"
          % (out["worst_abs_db"], out["worst_abs_db_at_240seg"],
             "PASS" if out["passes"] else "FAIL"))
