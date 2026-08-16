# -*- coding: utf-8 -*-
"""
mesh_placement.py — **배치·겹침·묻힘** 검사 엔진 (메쉬 인증 라운드 2026-08-16)
================================================================================

무엇을 보는가 — 한 줄로
  «부품들이 **서로 어디에 놓여 있는가**». 부품 하나하나가 멀쩡한지(위상·치수)는 다른 검사가
  본다. 이 파일은 **부품 사이의 관계**만 본다: 떨어졌나 · 붙었나 · 파고들었나 · 통째로
  들어갔나 · 같은 자리에 두 껍질이 겹쳤나 · 한 부품이 자기 자신을 뚫고 지나가나.

용어 한 줄 풀이
  · **부품**      : 삼각형이 모서리로 이어진 덩어리 하나(연결요소). 그룹 안에서 센다.
  · **수밀**      : 껍질에 구멍이 없어 «안/밖» 이 정의되는 상태. 내부판정의 전제다.
  · **내부판정**  : 점이 껍질 «안» 인지 «밖» 인지 가리는 것(trimesh `contains`). 수밀이어야 한다.
  · **교차**      : 두 삼각형이 실제로 서로를 **뚫고 지나가는 것**(가로지름). 같은 평면에
                    붙어만 있는 것은 교차로 치지 않는다 — 그건 «동일평면» 이라는 다른 항목이다.
  · **간극**      : 두 부품 표면 사이의 최단거리. 0 이면 붙었고, 양수면 떨어졌다.
  · **동일평면**  : 두 부품의 껍질이 **같은 자리에 같은 방향으로** 겹쳐 있는 것(z-fighting).
                    PO 는 가림을 안 보므로 같은 물리적 면을 **두 재질로 두 번** 더한다.

⭐ 왜 이 파일이 따로 있는가 — **측정법이 틀리면 검사가 거짓말을 한다**
--------------------------------------------------------------------------------
간극을 «한쪽 방향으로만» 재면 틀린다. **큰 상자가 가는 봉을 감싸고 있을 때**,
상자의 정점에서 봉까지를 재면 «멀다» 가 나온다(상자 모서리는 봉에서 멀다). 그래서
«간극 큼 → 뜬 부품» 이라는 **거짓양성**이 난다. 실제로 이 저장소에서 2건 났다.
그래서 이 엔진은 **세 가지를 함께** 쓴다:

  ① **양방향 정점↔면**  : A 의 정점 → B 의 **면**(삼각형 표면) 최단거리와, 그 반대를 **둘 다**
                          재서 작은 쪽을 쓴다. (정점↔정점은 쓰지 않는다 — 면 한복판에 닿는
                          접촉을 통째로 놓친다.)
  ② **내부판정**        : 부호를 준다. 안에 들어간 것은 «간극» 이 아니라 **음수**다.
  ③ **삼각형 교차**     : 수밀을 **요구하지 않는** 독립 잣대. 구멍 난 부품(내부판정 불가)에서도
                          «파고듦» 을 본다. 즉 ②가 못 보는 자리를 ③이 본다.

  ⭐ 셋을 **다** 써야 한다는 것은 대조 시험이 증명한다(benchmark/adv_mesh_placement_0816.py):
     · 큰 상자를 꿰뚫은 가는 봉 — ①만 쓰면 «69 mm 떨어짐» 이라고 답한다(정점이 서로 멀다). ③이 잡는다.
     · 상자 **안에 통째로** 든 봉 — ③은 교차가 0 이라 못 본다. ②가 잡는다.
     · 옆면이 딱 맞물려 겹친 두 상자 — 표면이 «가로지르지» 않아 ③이 0 이다. ②가 잡는다.
     · 구멍 난 상자를 꿰뚫은 봉 — ②가 성립 안 한다(수밀 아님). ③이 잡는다.
     ⇒ 어느 하나만으로도, 둘만으로도 구멍이 남는다.

⭐⭐ 범주가 닫혀 있다는 논증 (두 부품 A, B 가 서로 어떤 관계일 수 있는가)
--------------------------------------------------------------------------------
껍질 두 개 사이에 성립할 수 있는 관계는 **다음 넷뿐이고 서로 배타적**이다:

     삼각형 교차 있나? ──예──▶ **R2 관통** (부분적으로 파고듦)
        │
        아니오
        │
     한쪽이 **통째로** 다른 쪽 안에 있나? ──예──▶ **R3 완전매몰**
        │
        아니오
        │
     안에 든 면적이 적지 않고(≥1 %) **깊이도 깊나**(>10 µm)? ──예──▶ **R2 관통**
        │                     ⤷ 옆면이 딱 맞물린 두 상자는 표면이 «가로지르지» 않아서
        │                       교차 잣대에 안 걸린다. 내부판정이 그 자리를 잡는다.
        아니오
        │
     간극 ≤ 접촉허용? ──예──▶ **R1 접촉** (그중 법선이 나란하면 **동일평면**)
        │
        아니오 ──▶ **R0 떨어짐** (그중 «붙어 있어야 하는데» 떨어진 것 = **뜬 부품**)

  논증: 두 닫힌 곡면의 관계는 «표면이 만나는가» 로 먼저 갈린다(만나면 R2). 안 만나면 두
  내부는 서로소이거나 하나가 다른 하나에 포함된다 — 위상적으로 그 둘뿐이다(포함이면 R3).
  서로소이면 남는 자유도는 **거리 하나**이고, 그것을 허용오차로 자르면 R1/R0 이다.
  ⇒ 이 네 칸 밖의 관계는 없다. **한 부품 안**에서만 따로 생기는 것이 «자기교차» 이고
  (표면이 자기 자신과 만난다), 그래서 이 파일의 검사 항목은 **다섯**이다.

  ⚠ 이 논증이 **증명하지 않는 것**: 「부품이 **있어야 할 자리**에 있는가」는 여기서 안 본다.
    (그건 배치 절대좌표 = 다른 범주다. 여기 있는 것은 **상대 관계**뿐이다.)

무엇을 내놓나
  · `placement_census(mesh, name)` — 기체 한 대의 전 부품쌍 관계표(원장의 출처)
  · `check_placement(...)`         — 예산표와 대조한 판정(게이트에 그대로 쓸 수 있다)
  · `assert_placement_ok()`        — 회귀 봉인용 예외 던지기

⛔ 이 파일은 **형상을 하나도 안 바꾼다.** 읽고 재고 판정할 뿐이다.
⚠ 부품 분해(`split_parts`)를 `mesh_buried._parts` 와 **일부러 따로** 짰다 — 같은 결론이
   **독립된 두 경로**에서 나와야 교차검증이 되기 때문이다(중복은 알고 남긴 것이다).
   실제로 두 엔진의 매몰면적은 10 기체 중 9 기체에서 **소수 넷째 자리까지 같고**, 다른 한 대
   (mini2)는 «구멍을 메우느냐» 하나 때문이며 그 조건을 맞추면 역시 같다.

실행:  PYTHONPATH=src python src/mesh_placement.py          (전 기종 원장 인쇄)
"""
from __future__ import annotations

import hashlib
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


# ─────────────────────────────────────────────────────────────────────────────
#  잣대(허용오차) — 전부 **길이**로 정의한다. 상대 잣대가 필요한 곳은 그 자리에 적었다.
# ─────────────────────────────────────────────────────────────────────────────
PLANE_EPS_M = 1e-9          # 1 nm. 교차 판정에서 «평면 위에 있다» 로 볼 두께(부호 판정용).
                            #   물리적 잣대는 아래 CROSS_PEN_MIN_M 이다.
CROSS_PEN_MIN_M = 1e-6      # ⭐1 µm. **이만큼은 파고들어야 «관통» 이라고 부른다.**
                            #   왜 필요한가: 부호만 보면 «두 껍질이 깊이 박힌 것» 과 «같은 면에
                            #   0.1 µm 어긋나 얹힌 것» 이 같은 답이 된다. 실제로 우리 CSG 합집합
                            #   산출물의 씨접합 면들이 법선각 0.0025°·어긋남 0.1 µm 로 그렇게 나오고,
                            #   그 자리에서는 **독립 구현과 답이 갈린다**(같은 형상을 두고 32 % 불일치
                            #   — 어느 쪽도 틀린 게 아니라 그 척도에서 «교차» 라는 말이 뜻을 잃는다).
                            #   1 µm 는 그 잡음의 열 배이고, 우리 파장(㎝)의 1e-5 이하다.
                            #   ⚠ 그러므로 이 검사는 «1 µm 보다 얕은 파고듦은 못 본다» 고 선언한다.
TOUCH_TOL_M = 1e-5          # 10 µm. 이보다 가까우면 «붙었다»(접촉). 우리 CSG 합집합 산출물의
                            #   씨접합 정점 오차(0.1 µm 급)보다 두 자리 크게 잡았다.
INSIDE_MIN_PCT = 1.0        # [%] 표면 교차가 없는데 상대 솔리드 안에 든 면적이 이보다 크면
                            #   «두 부피가 겹친다»(관통)고 본다. 이보다 작으면 접촉면에서 내부판정이
                            #   흔들린 것으로 본다. ⚠ 이 잣대가 필요한 이유: 옆면이 **딱 맞물린**
                            #   두 상자는 표면이 «가로지르지» 않고 같은 평면에서 만나므로 교차 잣대에
                            #   안 걸린다(합성 대조 B4 가 그 상황을 실제로 만든다).
COPLANAR_GAP_M = 1e-5       # 10 µm. 동일평면 판정 — 면 중심이 상대 표면에서 이 안에 있고
COPLANAR_ANG_DEG = 5.0      #        법선이 이 각 안에서 나란/반대면 «같은 자리에 겹친 껍질».
DEPTH_SAMPLE_MAX = 4000     # 관통 깊이는 **표본**으로 잰다(고정 씨앗). 판정 잣대가 아니라 진단값.
_RNG_SEED = 20260816


# ─────────────────────────────────────────────────────────────────────────────
#  기하 원시함수 — 전부 numpy 벡터화. 외부 의존은 scipy.cKDTree 와 trimesh(내부판정)뿐.
# ─────────────────────────────────────────────────────────────────────────────
def _tri_geom(V, F):
    """삼각형의 중심 C, 법선 n(정규화 안 함), 면적, **외접반경 상한** r 을 한 번에.

    r = 중심에서 세 꼭짓점까지 거리의 최대값. 두 삼각형이 만나면 그 접점까지의 거리가
    각각 r 이하이므로 **|C1−C2| ≤ r1+r2** 가 반드시 성립한다 — 후보 짝짓기의 근거다(보수적)."""
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cen = (A + B + C) / 3.0
    nrm = np.cross(B - A, C - A)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    r = np.maximum(np.maximum(np.linalg.norm(A - cen, axis=1),
                              np.linalg.norm(B - cen, axis=1)),
                   np.linalg.norm(C - cen, axis=1))
    return cen, nrm, area, r


def _size_buckets(r, n_bins=4):
    """반경을 log2 로 몇 칸에 나눈다 — 「가장 큰 삼각형 하나」가 후보 반경을 지배하지 않게.
    반환: {칸번호: 인덱스배열}"""
    r = np.asarray(r, float)
    rmax = float(r.max()) if len(r) else 1.0
    if rmax <= 0:
        return {0: np.arange(len(r))}
    k = np.clip(np.floor(np.log2(np.maximum(rmax / np.maximum(r, 1e-300), 1.0))),
                0, n_bins - 1).astype(int)
    return {int(b): np.where(k == b)[0] for b in np.unique(k)}


def _candidate_tri_pairs(C1, r1, C2, r2, extra=0.0, max_pairs=40_000_000):
    """삼각형 후보 짝 — |C1−C2| ≤ r1+r2+extra 인 (i, j) 전부. **놓치지 않는다**(보수적).

    크기 칸으로 나눠 KD-트리를 여러 번 돌린다. 안 그러면 큰 삼각형 한 장 때문에 반경이
    부풀어 후보가 폭발한다."""
    from scipy.spatial import cKDTree
    if len(C1) == 0 or len(C2) == 0:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    ii, jj = [], []
    total = 0
    for _, i1 in _size_buckets(r1).items():
        t1 = cKDTree(C1[i1])
        for _, i2 in _size_buckets(r2).items():
            R = float(r1[i1].max() + r2[i2].max() + extra)
            t2 = cKDTree(C2[i2])
            res = t1.query_ball_tree(t2, R)
            for a, lst in enumerate(res):
                if lst:
                    ii.append(np.full(len(lst), i1[a], np.int64))
                    jj.append(i2[np.asarray(lst, np.int64)])
                    total += len(lst)
            if total > max_pairs:
                raise MemoryError(f"후보 삼각형 짝이 {total} 개 — 상한 {max_pairs} 초과")
    if not ii:
        return np.empty(0, np.int64), np.empty(0, np.int64)
    return np.concatenate(ii), np.concatenate(jj)


def tri_tri_cross_mask(V1, F1, V2, F2, i1, i2, plane_eps=PLANE_EPS_M,
                       min_pen=CROSS_PEN_MIN_M, want_len=False):
    """**삼각형 가로지름** 판정 (Möller 1997 의 구간겹침법, 벡터화).

    참 = 두 삼각형이 실제로 서로를 뚫고 지난다. **같은 평면에 얹힌 경우는 거짓**이다 —
    그것은 «동일평면» 이라는 다른 항목이고, 수치적으로도 부호가 흔들려 교차로 세면 잡음이 된다.

    plane_eps [m] : «평면 위» 로 볼 두께. 법선을 정규화한 뒤 거리로 비교하므로 **길이 단위**다.
    ⚠ 퇴화삼각형(면적 0)은 **판정에서 뺀다**(법선이 없다). 그 축은 다른 검사(슬리버·퇴화면)가 본다.

    ⭐ want_len=True 면 **교차선분의 길이**[m]도 준다. 왜 필요한가: 참/거짓만으로는
      «두 껍질이 깊이 파고든 것» 과 «모서리에서 나노미터만큼 스친 것» 이 같은 값이 된다.
      실제로 우리 함대의 씨접합 슬리버가 그렇다 — 독립 구현과 답이 갈리는 자리가 전부 그 언저리다.
      길이는 교선 방향 D(단위벡터) 위의 좌표로 재므로 **그대로 미터**다.

    min_pen [m] : **파고든 깊이**의 하한. 삼각형이 상대 평면 너머로 내민 두께(양쪽 중 얇은 쪽,
      두 삼각형 중 작은 쪽)가 이보다 얕으면 «관통» 으로 세지 않는다 — 위 CROSS_PEN_MIN_M 참조."""
    if len(i1) == 0:
        return (np.zeros(0, bool), np.zeros(0), np.zeros(0)) if want_len \
            else np.zeros(0, bool)
    P0, P1, P2 = V1[F1[i1, 0]], V1[F1[i1, 1]], V1[F1[i1, 2]]
    Q0, Q1, Q2 = V2[F2[i2, 0]], V2[F2[i2, 1]], V2[F2[i2, 2]]
    n1 = np.cross(P1 - P0, P2 - P0)
    n2 = np.cross(Q1 - Q0, Q2 - Q0)
    l1 = np.linalg.norm(n1, axis=1)
    l2 = np.linalg.norm(n2, axis=1)
    live = (l1 > 0) & (l2 > 0)                       # 퇴화삼각형 제외
    out = np.zeros(len(i1), bool)
    if not live.any():
        return out
    seg = np.zeros(len(i1))
    pen = np.zeros(len(i1))
    u1 = n1[live] / l1[live][:, None]                 # 단위법선 → 거리 단위로 잰다
    u2 = n2[live] / l2[live][:, None]
    p0, p1, p2 = P0[live], P1[live], P2[live]
    q0, q1, q2 = Q0[live], Q1[live], Q2[live]

    def sd(u, base, X):
        return np.einsum("ij,ij->i", u, X - base)

    dq = np.stack([sd(u1, p0, q0), sd(u1, p0, q1), sd(u1, p0, q2)], 1)
    dp = np.stack([sd(u2, q0, p0), sd(u2, q0, p1), sd(u2, q0, p2)], 1)
    #  ⑴ 한쪽 삼각형이 상대 평면의 **한쪽에만** 있으면 만날 수 없다
    sep = ((dq > plane_eps).all(1) | (dq < -plane_eps).all(1)
           | (dp > plane_eps).all(1) | (dp < -plane_eps).all(1))
    #  ⑵ **같은 평면**(세 점 전부 평면 위)은 «가로지름» 이 아니다 → 여기서 뺀다
    copl = (np.abs(dq) <= plane_eps).all(1) | (np.abs(dp) <= plane_eps).all(1)
    #  ⑵-2 **파고든 두께** — 평면 너머로 내민 쪽의 두께(얇은 쪽). 물리적 잣대다.
    def protrude(d):
        return np.minimum(np.maximum(d.max(1), 0.0), np.maximum(-d.min(1), 0.0))

    pen_live = np.minimum(protrude(dp), protrude(dq))
    cand = ~(sep | copl) & (pen_live >= min_pen)
    if not cand.any():
        return (out, seg, pen) if want_len else out
    D = np.cross(u1[cand], u2[cand])                  # 두 평면의 교선 방향
    dl = np.linalg.norm(D, axis=1)
    ok = dl > 1e-12                                   # 평행 평면은 위에서 이미 걸러졌다
    D = np.where(ok[:, None], D / np.maximum(dl, 1e-300)[:, None], 0.0)

    def interval(Va, Vb, Vc, d):
        """평면을 가로지르는 구간 [lo, hi] 를 교선 위 좌표 t = D·V 로."""
        t = np.stack([np.einsum("ij,ij->i", D, Va),
                      np.einsum("ij,ij->i", D, Vb),
                      np.einsum("ij,ij->i", D, Vc)], 1)
        lo = np.full(len(t), np.inf)
        hi = np.full(len(t), -np.inf)
        on = np.abs(d) <= plane_eps                   # 평면 위의 꼭짓점 자체도 구간의 끝점이다
        for k in range(3):
            lo = np.where(on[:, k], np.minimum(lo, t[:, k]), lo)
            hi = np.where(on[:, k], np.maximum(hi, t[:, k]), hi)
        for a, b in ((0, 1), (1, 2), (2, 0)):         # 부호가 다른 변은 평면을 자른다
            m = (d[:, a] * d[:, b] < 0) & (~on[:, a]) & (~on[:, b])
            den = np.where(m, d[:, a] - d[:, b], 1.0)
            s = t[:, a] + (t[:, b] - t[:, a]) * (d[:, a] / den)
            lo = np.where(m, np.minimum(lo, s), lo)
            hi = np.where(m, np.maximum(hi, s), hi)
        return lo, hi

    lo1, hi1 = interval(p0[cand], p1[cand], p2[cand], dp[cand])
    lo2, hi2 = interval(q0[cand], q1[cand], q2[cand], dq[cand])
    L = np.minimum(hi1, hi2) - np.maximum(lo1, lo2)   # 겹친 구간 = 교차선분 길이[m]
    hit = ok & np.isfinite(lo1) & np.isfinite(lo2) & (L >= 0.0)
    idx_live = np.where(live)[0]
    tgt = idx_live[np.where(cand)[0][hit]]
    out[tgt] = True
    seg[tgt] = np.maximum(L[hit], 0.0)
    pen[tgt] = pen_live[cand][hit]
    return (out, seg, pen) if want_len else out


def _pt_tri_dist(P, A, B, C):
    """점 ↔ **삼각형(면)** 최단거리 — Ericson 의 영역판정, 벡터화.
    ⚠ 정점끼리 재는 것이 아니라 **면 위의 가장 가까운 점**까지 잰다. 면 한복판에 닿는 접촉을
      놓치지 않으려면 이래야 한다."""
    ab, ac = B - A, C - A
    ap = P - A
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = P - B
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = P - C
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    den = va + vb + vc
    safe = np.abs(den) > 1e-300
    v = np.where(safe, vb / np.where(safe, den, 1.0), 0.0)
    w = np.where(safe, vc / np.where(safe, den, 1.0), 0.0)
    Q = A + ab * v[:, None] + ac * w[:, None]          # 내부(면) 영역
    #  ↓ 가장자리·꼭짓점 영역은 덮어쓴다(Ericson 의 우선순위 역순)
    m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    if m.any():
        t = (d4[m] - d3[m]) / np.maximum((d4[m] - d3[m]) + (d5[m] - d6[m]), 1e-300)
        Q[m] = B[m] + (C[m] - B[m]) * t[:, None]
    m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    if m.any():
        t = d2[m] / np.maximum(d2[m] - d6[m], 1e-300)
        Q[m] = A[m] + ac[m] * t[:, None]
    m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    if m.any():
        t = d1[m] / np.maximum(d1[m] - d3[m], 1e-300)
        Q[m] = A[m] + ab[m] * t[:, None]
    m = (d6 >= 0) & (d5 <= d6)
    Q[m] = C[m]
    m = (d3 >= 0) & (d4 <= d3)
    Q[m] = B[m]
    m = (d1 <= 0) & (d2 <= 0)
    Q[m] = A[m]
    d = np.linalg.norm(P - Q, axis=1)
    #  안전장치 — 퇴화삼각형에서 영역판정이 흔들려도 «꼭짓점까지의 거리» 는 언제나 유효한 상한.
    d = np.minimum(d, np.minimum(np.linalg.norm(P - A, axis=1),
                                 np.minimum(np.linalg.norm(P - B, axis=1),
                                            np.linalg.norm(P - C, axis=1))))
    return d


def points_to_surface(P, V2, F2, C2=None, r2=None, kd_vert=None, want_face=False,
                      only_within=None, min_only=False):
    """점 무리 → **면(표면)** 최단거리. 각 점마다 정확한 값(정점 근사가 아니다).

    방법: ① 가장 가까운 **정점** 거리 dv 를 KD-트리로 얻는다(상한). ② 최단 표면점을 품은
    삼각형은 반드시 중심이 dv + r_max 안에 있다(외접반경의 뜻). 그 후보만 정확히 계산한다.
    ⇒ 근사가 아니라 **정확**하다(정점→면 방향에 한해서).
    want_face=True 면 (거리, 그 삼각형 번호) 를 함께 준다.

    ⚠ 가지치기 두 개 — **정확도를 안 깎는다**(둘 다 부등식으로 증명된다):
      only_within=t : 답이 t 이하인 점만 정확히 푼다. dv−r_max ≤ d_true ≤ dv 이므로
                      dv > t + r_max 인 점은 d_true > t 가 **확정**이라 풀 필요가 없다.
                      (그런 점의 반환값은 상한 dv 다 — «t 보다 크다» 는 사실만 쓰라는 뜻.)
      min_only=True : 무리 전체의 **최소값**만 필요할 때. dv 의 최소 D 에 대해
                      d_true ≥ dv − r_max 이므로 dv > D + r_max 인 점은 최소가 될 수 없다.
      ⇒ 이 가지치기가 없으면 «멀리 떨어진 두 부품» 에서 후보가 폭발한다(점 8천 × 면 8천).
    """
    from scipy.spatial import cKDTree
    if len(P) == 0 or len(F2) == 0:
        return (np.zeros(len(P)), np.full(len(P), -1)) if want_face else np.zeros(len(P))
    if C2 is None or r2 is None:
        C2, _, _, r2 = _tri_geom(V2, F2)
    kd_vert = kd_vert or cKDTree(V2)
    dv, _ = kd_vert.query(P)
    rmax = float(r2.max())
    #  cap = «이 값보다 큰 답은 알 필요 없다» 는 상한. 그러면 찾을 반경은 cap + r_max 로 **고정**된다
    #  (답이 cap 이하인 삼각형은 중심이 그 안에 반드시 있다). dv 를 반경으로 쓰면 멀리 떨어진
    #  부품에서 반경이 부풀어 후보가 폭발한다 — 실제로 그래서 느려졌다.
    cap = np.inf
    if min_only:
        cap = float(dv.min())
    if only_within is not None:
        cap = min(cap, float(only_within))
    rad = (cap + rmax) if np.isfinite(cap) else None
    keep = np.where(dv <= (rad if rad is not None else np.inf) + 1e-15)[0]
    kd_cen = cKDTree(C2)
    lists = kd_cen.query_ball_point(P[keep], rad if rad is not None else (dv[keep] + rmax + 1e-15))
    best = np.array(dv, float)
    bidx = np.full(len(P), -1, np.int64)
    pi, ti = [], []
    for a, lst in enumerate(lists):
        if lst:
            pi.append(np.full(len(lst), keep[a], np.int64))
            ti.append(np.asarray(lst, np.int64))
    if pi:
        pi = np.concatenate(pi)
        ti = np.concatenate(ti)
        d = _pt_tri_dist(P[pi], V2[F2[ti, 0]], V2[F2[ti, 1]], V2[F2[ti, 2]])
        order = np.lexsort((d, pi))                    # 점별 최소값을 고른다
        pi, d, ti = pi[order], d[order], ti[order]
        first = np.ones(len(pi), bool)
        first[1:] = pi[1:] != pi[:-1]
        sel = np.where(first)[0]
        better = d[sel] < best[pi[sel]]
        idx = pi[sel][better]
        best[idx] = d[sel][better]
        bidx[idx] = ti[sel][better]
    return (best, bidx) if want_face else best


# ─────────────────────────────────────────────────────────────────────────────
#  부품 분해 — ⚠ `mesh_buried._parts` 와 **일부러 따로** 짠 독립 경로다.
# ─────────────────────────────────────────────────────────────────────────────
def fingerprint(mesh) -> str:
    """메쉬 지문(sha1) — 정점·면·그룹이 1 비트라도 바뀌면 값이 바뀐다. 인증서 봉인의 열쇠."""
    v = np.ascontiguousarray(np.asarray(mesh.v, float))
    f = np.ascontiguousarray(np.asarray(mesh.f, np.int64))
    h = hashlib.sha1()
    h.update(v.tobytes())
    h.update(f.tobytes())
    h.update("|".join(map(str, mesh.g)).encode())
    return h.hexdigest()


class Part:
    """부품 하나 — 그룹 안에서 웰딩한 뒤 쪼갠 연결요소.

    ⚠ 웰딩(process=True)은 **같은 자리의 중복 정점을 합치는 것**이라 형상을 안 바꾼다.
      수리(repair)는 **하지 않는다** — 검사기가 자기가 메운 사본을 검사하면 안 된다(감사 C1)."""

    __slots__ = ("pid", "group", "face_idx", "V", "F", "C", "N", "A", "R",
                 "lo", "hi", "watertight", "volume_mm3", "_tm")

    def __init__(self, pid, group, face_idx, V, F, tm):
        self.pid = pid
        self.group = group
        self.face_idx = face_idx
        self.V, self.F = V, F
        self.C, self.N, self.A, self.R = _tri_geom(V, F)
        self.lo, self.hi = V.min(0), V.max(0)
        self._tm = tm
        self.watertight = bool(tm.is_watertight)
        self.volume_mm3 = float(tm.volume) * 1e9 if self.watertight else float("nan")

    def contains(self, P):
        """점이 이 부품 **안**인가. 수밀이 아니면 판정 자체가 성립 안 하므로 None 을 준다
        («못 봄» 을 «없음(False)» 으로 보고하지 않기 위해서다)."""
        if not self.watertight or not np.isfinite(self.volume_mm3) or self.volume_mm3 <= 0:
            return None
        if len(P) == 0:
            return np.zeros(0, bool)
        return np.asarray(self._tm.contains(P), bool)

    def aabb_gap(self, o) -> float:
        """축정렬 상자끼리의 거리 — 실제 표면거리의 **하한**(짝 고르기용 빠른 잣대)."""
        d = np.maximum(np.maximum(self.lo - o.hi, o.lo - self.hi), 0.0)
        return float(np.linalg.norm(d))


def split_parts(mesh) -> list[Part]:
    """geom.Mesh → 부품 목록. 그룹 안에서만 웰딩한다(다른 그룹이 같은 좌표를 써도 안 붙는다)."""
    import trimesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    out: list[Part] = []
    for grp in sorted(set(G.tolist())):
        gidx = np.where(G == grp)[0]
        f = F[gidx]
        used = np.unique(f)
        remap = np.zeros(int(used.max()) + 1, np.int64)
        remap[used] = np.arange(len(used))
        tm = trimesh.Trimesh(vertices=V[used], faces=remap[f], process=True)
        comps = trimesh.graph.connected_components(
            tm.face_adjacency, nodes=np.arange(len(tm.faces)), min_len=1)
        for k, c in enumerate(sorted(comps, key=lambda a: int(np.min(a)))):
            cs = np.sort(np.asarray(c, np.int64))
            sm = tm.submesh([cs], append=True, repair=False)
            p = Part(f"{grp}#{k}", grp, gidx[cs],
                     np.asarray(sm.vertices, float), np.asarray(sm.faces, np.int64), sm)
            #  ⚠ 번호 정렬 확인 — 부품의 삼각형 k 번이 **출하 메쉬의 몇 번째 삼각형**인지가
            #    어긋나면 면적·마스크가 전부 엉뚱한 자리를 가리킨다. 조용히 어긋나느니 죽는다.
            if len(p.F) != len(cs):
                raise RuntimeError(f"부품 분해 어긋남: {grp}#{k} 면 {len(p.F)} ≠ {len(cs)}")
            a_glob = _tri_geom(V, F[p.face_idx])[2]
            if not np.allclose(np.sort(p.A), np.sort(a_glob), rtol=1e-9, atol=1e-18):
                raise RuntimeError(f"부품 분해 어긋남: {grp}#{k} 면적이 출하 메쉬와 다르다")
            out.append(p)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  ① 자기 겹침 — 한 부품이 **자기 자신을** 뚫고 지나가나
# ─────────────────────────────────────────────────────────────────────────────
def self_intersection(part: Part, plane_eps=PLANE_EPS_M) -> dict:
    """부품 안에서 **정점을 공유하지 않는** 두 삼각형이 교차하는가.

    ⚠ 정점을 공유하는 삼각형(이웃)은 당연히 «만난다» — 그건 결함이 아니라 접합이다.
      웰딩을 했으므로 «같은 자리 다른 번호» 는 없다 ⇒ 번호 공유 = 진짜 이웃이다."""
    V, F = part.V, part.F
    i, j = _candidate_tri_pairs(part.C, part.R, part.C, part.R)
    m = i < j
    i, j = i[m], j[m]
    if len(i):
        share = ((F[i][:, :, None] == F[j][:, None, :]).any(axis=(1, 2)))
        i, j = i[~share], j[~share]
    hit = tri_tri_cross_mask(V, F, V, F, i, j, plane_eps) if len(i) else np.zeros(0, bool)
    n = int(hit.sum())
    faces = np.unique(np.concatenate([i[hit], j[hit]])) if n else np.empty(0, np.int64)
    return dict(pid=part.pid, group=part.group, n_pairs=n, n_faces=int(len(faces)),
                area_mm2=round(float(part.A[faces].sum()) * 1e6, 6) if n else 0.0,
                candidates=int(len(i)))


# ─────────────────────────────────────────────────────────────────────────────
#  ② 부품쌍 관계 — R0 떨어짐 / R1 접촉(동일평면) / R2 관통 / R3 완전매몰
# ─────────────────────────────────────────────────────────────────────────────
def pair_relation(a: Part, b: Part, touch_tol=TOUCH_TOL_M, coplanar_gap=COPLANAR_GAP_M,
                  coplanar_ang=COPLANAR_ANG_DEG) -> dict:
    """두 부품의 관계를 **위 네 칸 중 하나**로 판정하고 근거 수치를 함께 낸다.

    측정 세 갈래를 **전부** 쓴다(파일 머리말 ⭐):
      ① 삼각형 교차   — 수밀을 요구하지 않는다
      ② 내부판정      — 부호(안/밖). 수밀이 아니면 «못 봄» 으로 남긴다
      ③ 양방향 정점↔면 — 간극. 한 방향만 재면 큰 상자↔가는 봉에서 거짓양성이 난다

    ⭐ 빠른 갈림길: 두 축정렬 상자가 **떨어져 있으면**(AABB 간극 > 접촉허용) 표면이 만날 수도,
      한쪽이 다른 쪽 안에 있을 수도 **없다**(상자는 부품을 감싼다). 그때는 간극만 재고 끝낸다 —
      근사가 아니라 **부등식으로 확정**되는 생략이다."""
    far = a.aabb_gap(b) > touch_tol
    #  ⑴ 삼각형 교차 (AABB 가 겹칠 때만 후보가 생긴다)
    if far:
        i = j = np.empty(0, np.int64)
        cross = np.zeros(0, bool)
    else:
        i, j = _candidate_tri_pairs(a.C, a.R, b.C, b.R)
        cross = tri_tri_cross_mask(a.V, a.F, b.V, b.F, i, j) if len(i) else np.zeros(0, bool)
    n_cross = int(cross.sum())
    fa = np.unique(i[cross]) if n_cross else np.empty(0, np.int64)
    fb = np.unique(j[cross]) if n_cross else np.empty(0, np.int64)

    #  ⑵ 내부판정 — **양방향**. 면 중심을 질의점으로 쓴다(매몰면 검사와 같은 알갱이).
    def frac_inside(src: Part, dst: Part):
        if far:
            return 0.0, 0.0, True, np.empty(0, np.int64)
        sel = np.all((src.C >= dst.lo - 1e-12) & (src.C <= dst.hi + 1e-12), axis=1)
        if not sel.any():
            return 0.0, 0.0, True, np.empty(0, np.int64)
        r = dst.contains(src.C[sel])
        if r is None:
            return None, None, False, np.empty(0, np.int64)     # 못 봄(비수밀)
        idx = np.where(sel)[0][r]
        return (round(100.0 * float(src.A[idx].sum()) / float(src.A.sum()), 4),
                round(float(src.A[idx].sum()) * 1e6, 4), True, idx)

    a_in_b_pct, a_in_b_mm2, seen_ab, ia = frac_inside(a, b)
    b_in_a_pct, b_in_a_mm2, seen_ba, ib = frac_inside(b, a)

    #  ⑶ 간극 — **양방향** 정점↔면. 교차·매몰이면 표면이 만나거나 안에 있으므로 따로 다룬다.
    d_ab = float(points_to_surface(a.V, b.V, b.F, b.C, b.R, min_only=True).min()) \
        if len(a.V) else np.inf
    d_ba = float(points_to_surface(b.V, a.V, a.F, a.C, a.R, min_only=True).min()) \
        if len(b.V) else np.inf
    gap_bidir = min(d_ab, d_ba)
    #  ↓ 대조군: **한 방향만** 재는 순진한 잣대(정점↔정점). 어디서 틀리는지 원장에 남긴다.
    from scipy.spatial import cKDTree
    gap_vv = float(cKDTree(b.V).query(a.V)[0].min()) if len(a.V) and len(b.V) else np.inf

    contained = ((a_in_b_pct is not None and a_in_b_pct >= 99.9999)
                 or (b_in_a_pct is not None and b_in_a_pct >= 99.9999))
    inside_max = max(a_in_b_pct or 0.0, b_in_a_pct or 0.0)
    any_inside = inside_max > 0.0

    #  ⑷ 동일평면 — 면 중심이 상대 표면 위(≤coplanar_gap)이고 법선이 나란/반대인 면적
    def coplanar(src: Part, dst: Part):
        if far:
            return 0.0, np.empty(0, np.int64)
        sel = np.all((src.C >= dst.lo - coplanar_gap) & (src.C <= dst.hi + coplanar_gap), axis=1)
        if not sel.any():
            return 0.0, np.empty(0, np.int64)
        d, fi = points_to_surface(src.C[sel], dst.V, dst.F, dst.C, dst.R,
                                  want_face=True, only_within=coplanar_gap)
        near = (d <= coplanar_gap) & (fi >= 0)
        if not near.any():
            return 0.0, np.empty(0, np.int64)
        ns = src.N[np.where(sel)[0][near]]
        nd = dst.N[fi[near]]
        ns = ns / np.maximum(np.linalg.norm(ns, axis=1), 1e-300)[:, None]
        nd = nd / np.maximum(np.linalg.norm(nd, axis=1), 1e-300)[:, None]
        par = np.abs(np.einsum("ij,ij->i", ns, nd)) >= np.cos(np.radians(coplanar_ang))
        idx = np.where(sel)[0][near][par]
        return round(float(src.A[idx].sum()) * 1e6, 6), idx

    cop_a_mm2, cop_ia = coplanar(a, b)
    cop_b_mm2, cop_ib = coplanar(b, a)

    #  ⑸ **파고든 깊이** — 안에 들었다고 판정된 면 중심이 상대 표면에서 얼마나 들어가 있나.
    #     ⭐ 이 수가 «딱 맞대어 붙은 것»(0)과 «진짜 부피가 겹친 것»(mm)을 가른다. 표면 위의 점에서
    #     내부판정은 동전던지기라, 개수만 보면 **맞댄 두 상자가 «관통» 으로 둔갑한다**(실제로 그랬다).
    rng = np.random.default_rng(_RNG_SEED)

    def deepest(src: Part, dst: Part):
        if not dst.watertight:
            return 0.0
        sel = np.all((src.C >= dst.lo) & (src.C <= dst.hi), axis=1)
        if not sel.any():
            return 0.0
        r = dst.contains(src.C[sel])
        if r is None or not r.any():
            return 0.0
        P = src.C[np.where(sel)[0][r]]
        if len(P) > DEPTH_SAMPLE_MAX:                   # 표본(고정 씨앗) — 진단값이지 판정 잣대가 아니다
            P = P[rng.choice(len(P), DEPTH_SAMPLE_MAX, replace=False)]
        return float(points_to_surface(P, dst.V, dst.F, dst.C, dst.R).max())

    depth = max(deepest(a, b), deepest(b, a)) if any_inside else 0.0
    depth_mm = round(depth * 1000.0, 6)

    #  ⑹ 관계 판정 — 머리말의 결정나무 그대로
    if n_cross > 0:
        rel = "R2_관통"
        gap_mm = 0.0
    elif contained:
        rel = "R3_완전매몰"
        gap_mm = -round(gap_bidir * 1000.0, 6)          # 안에 있으면 «음의 간극»
    elif inside_max >= INSIDE_MIN_PCT and depth > touch_tol:
        #  ⭐ 표면 교차가 **하나도 없는데** 상대 솔리드 안에 적지 않은 면적이 **깊이** 들어 있다
        #     = 두 부피가 겹치는데 두 껍질이 **같은 평면에서 만나는** 배치다(옆면이 딱 맞물린 두 상자).
        #     교차 잣대만 있으면 통째로 놓치는 자리라 내부판정이 여기서 잡는다.
        rel = "R2_관통"
        gap_mm = 0.0
    elif any_inside:
        #  안에 들긴 했는데 깊이가 접촉허용 안 = 맞댄 면 위에서 내부판정이 흔들린 것(경계 잡음).
        rel = "R1_접촉"
        gap_mm = 0.0
    elif gap_bidir <= touch_tol:
        rel = "R1_접촉"
        gap_mm = round(gap_bidir * 1000.0, 6)
    else:
        rel = "R0_떨어짐"
        gap_mm = round(gap_bidir * 1000.0, 6)

    #  ⭐ 순진한 잣대(한 방향 · 정점↔정점)라면 이 쌍을 뭐라고 판정했을까 — 거짓양성 기록용
    rel_naive = "R0_떨어짐" if gap_vv > touch_tol else "R1_접촉"

    return dict(
        a=a.pid, b=b.pid, groups=[a.group, b.group], relation=rel,
        cross_pairs=n_cross,
        cross_area_mm2=round(float(a.A[fa].sum() + b.A[fb].sum()) * 1e6, 6) if n_cross else 0.0,
        a_in_b_pct=a_in_b_pct, b_in_a_pct=b_in_a_pct,
        a_in_b_mm2=a_in_b_mm2, b_in_a_mm2=b_in_a_mm2,
        containment_seen=bool(seen_ab and seen_ba),
        gap_mm=gap_mm,
        gap_bidir_mm=round(gap_bidir * 1000.0, 6),
        gap_a_to_b_mm=round(d_ab * 1000.0, 6), gap_b_to_a_mm=round(d_ba * 1000.0, 6),
        gap_vertex_only_mm=round(gap_vv * 1000.0, 6),
        relation_if_one_way_ruler=rel_naive,
        one_way_ruler_wrong=bool(rel_naive != rel and rel != "R1_접촉"),
        penetration_depth_mm=depth_mm,
        coplanar_a_mm2=cop_a_mm2, coplanar_b_mm2=cop_b_mm2,
        coplanar_faces=int(len(cop_ia) + len(cop_ib)),
        coplanar=bool(cop_a_mm2 > 0.0 or cop_b_mm2 > 0.0),
        #  ↓ **출하 메쉬의 면 번호**(전역). 기체 단위 면적 합에서 같은 면을 두 번 안 세려고 싣는다.
        _gf_cross=np.concatenate([a.face_idx[fa], b.face_idx[fb]]) if n_cross
        else np.empty(0, np.int64),
        _gf_coplanar=np.concatenate([a.face_idx[cop_ia], b.face_idx[cop_ib]]),
        _gf_inside=np.concatenate([a.face_idx[ia], b.face_idx[ib]]),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  ③ 기체 한 대 전수 — 원장의 출처
# ─────────────────────────────────────────────────────────────────────────────
def placement_census(mesh, name="mesh", touch_tol=TOUCH_TOL_M, verbose=False) -> dict:
    """전 부품쌍 관계표 + 자기교차 + 뜬 부품.

    ⚠ 쌍을 고르는 법: AABB 거리(표면거리의 **하한**)가 접촉허용 안이면 «가까운 쌍» 으로 보고
      전 항목을 잰다. 그보다 먼 쌍은 관계가 **R0(떨어짐)로 확정**되므로(하한이 이미 크다)
      다시 잴 필요가 없다 — 대신 «뜬 부품» 판정에 필요한 **최근접 거리**는 그 쌍들까지
      훑어서 구한다(아래 nearest 루프)."""
    parts = split_parts(mesh)
    n = len(parts)
    area_all = float(sum(float(p.A.sum()) for p in parts))

    #  ⑴ 자기교차
    selfs = [self_intersection(p) for p in parts]
    self_bad = [s for s in selfs if s["n_pairs"] > 0]

    #  ⑵ 가까운 쌍 전수
    rels, cache = [], {}
    for x in range(n):
        for y in range(x + 1, n):
            if parts[x].aabb_gap(parts[y]) > touch_tol:
                continue
            r = pair_relation(parts[x], parts[y], touch_tol=touch_tol)
            cache[(x, y)] = r
            rels.append(r)

    #  ⑶ 뜬 부품 — 부품마다 **최근접 부호간극**. AABB 하한으로 가지치기 + 조기중단.
    floats = []
    for x in range(n):
        order = sorted((parts[x].aabb_gap(parts[y]), y) for y in range(n) if y != x)
        best, who = np.inf, None
        for lb, y in order:
            if lb >= best:
                break
            key = (min(x, y), max(x, y))
            r = cache.get(key)
            if r is None:
                r = pair_relation(parts[x], parts[y], touch_tol=touch_tol)
                cache[key] = r
            g = r["gap_mm"] / 1000.0
            if g < best:
                best, who = g, parts[y].pid
            if best <= touch_tol:
                break
        floats.append(dict(pid=parts[x].pid, group=parts[x].group,
                           nearest=who, gap_mm=round(float(best) * 1000.0, 6),
                           faces=int(len(parts[x].F)),
                           area_mm2=round(float(parts[x].A.sum()) * 1e6, 4)))

    #  ⑷ 기체 단위 면적 합 — **면 번호의 합집합**으로 센다(같은 면이 여러 쌍에 걸려도 한 번).
    nF = int(len(mesh.f))
    m_cross = np.zeros(nF, bool)
    m_copl = np.zeros(nF, bool)
    m_inside = np.zeros(nF, bool)
    for r in rels:
        m_cross[r["_gf_cross"]] = True
        m_copl[r["_gf_coplanar"]] = True
        m_inside[r["_gf_inside"]] = True
    A_glob = _tri_geom(np.asarray(mesh.v, float), np.asarray(mesh.f, np.int64))[2]

    def apct(mask):
        return round(100.0 * float(A_glob[mask].sum()) / float(A_glob.sum()), 4) \
            if A_glob.sum() > 0 else 0.0

    def amm2(mask):
        return round(float(A_glob[mask].sum()) * 1e6, 4)

    def tot(key):
        return round(sum(r[key] for r in rels), 6)

    counts = {}
    for r in rels:
        counts[r["relation"]] = counts.get(r["relation"], 0) + 1
    counts["R0_떨어짐"] = counts.get("R0_떨어짐", 0) + (n * (n - 1) // 2 - len(rels))

    blind = [dict(pid=p.pid, group=p.group, faces=int(len(p.F)),
                  area_mm2=round(float(p.A.sum()) * 1e6, 4),
                  why="비수밀 — 내부판정(contains) 성립 안 함. ⭐교차 검사는 그대로 본다")
             for p in parts if not p.watertight]

    out = dict(
        name=name, mesh_sha1=fingerprint(mesh),
        n_faces=int(len(mesh.f)), n_parts=n,
        total_area_mm2=round(area_all * 1e6, 4),
        touch_tol_mm=touch_tol * 1000.0,
        relations=counts,
        n_pairs_measured=len(rels), n_pairs_total=n * (n - 1) // 2,
        self_intersection=dict(
            n_parts=len(self_bad), n_pairs=int(sum(s["n_pairs"] for s in self_bad)),
            area_mm2=round(sum(s["area_mm2"] for s in self_bad), 6),
            parts=self_bad[:12]),
        crossing=dict(
            n_pairs=sum(1 for r in rels if r["relation"] == "R2_관통"),
            tri_pairs=int(sum(r["cross_pairs"] for r in rels)),
            area_mm2=amm2(m_cross), area_pct=apct(m_cross),
            area_sum_over_pairs_mm2=tot("cross_area_mm2")),
        coplanar=dict(
            n_pairs=sum(1 for r in rels if r["coplanar"]),
            area_mm2=amm2(m_copl), area_pct=apct(m_copl),
            area_sum_over_pairs_mm2=round(tot("coplanar_a_mm2") + tot("coplanar_b_mm2"), 6),
            pairs=[dict(a=r["a"], b=r["b"], mm2=round(r["coplanar_a_mm2"] + r["coplanar_b_mm2"], 4),
                        gap_mm=r["gap_mm"])
                   for r in sorted(rels, key=lambda r: -(r["coplanar_a_mm2"] + r["coplanar_b_mm2"]))
                   if r["coplanar"]][:8]),
        inside_faces=dict(area_mm2=amm2(m_inside), area_pct=apct(m_inside)),
        engulfed=[dict(a=r["a"], b=r["b"], a_in_b=r["a_in_b_pct"], b_in_a=r["b_in_a_pct"],
                       depth_mm=r["penetration_depth_mm"])
                  for r in rels if r["relation"] == "R3_완전매몰"],
        floating=sorted([f for f in floats if f["gap_mm"] > touch_tol * 1000.0],
                        key=lambda f: -f["gap_mm"]),
        parts_nearest=floats,
        blind_parts=blind,
        top_pairs=[{k: v for k, v in r.items() if not k.startswith("_")}
                   for r in sorted(rels, key=lambda r: -(r["cross_area_mm2"]))[:10]],
        #  ⭐ **잰 쌍 전부**(감사 추적용 원장). 요약만 싣고 끝내면 «어디를 봤는지» 를 확인할 수 없다.
        pairs_all=[dict(a=r["a"], b=r["b"], rel=r["relation"], cross=r["cross_pairs"],
                        gap_mm=r["gap_mm"], depth_mm=r["penetration_depth_mm"],
                        copl_mm2=round(r["coplanar_a_mm2"] + r["coplanar_b_mm2"], 4),
                        a_in_b=r["a_in_b_pct"], b_in_a=r["b_in_a_pct"])
                   for r in sorted(rels, key=lambda r: (r["a"], r["b"]))],
    )
    #  ⭐ 측정법 대조 — «한 방향 정점↔정점» 잣대였다면 **판정이 뒤집혔을** 쌍. 판정엔 안 쓰고 기록만.
    diff = [dict(a=r["a"], b=r["b"], groups=r["groups"], relation_true=r["relation"],
                 relation_one_way=r["relation_if_one_way_ruler"],
                 gap_bidir_mm=r["gap_bidir_mm"], gap_vertex_only_mm=r["gap_vertex_only_mm"])
            for r in rels if r["one_way_ruler_wrong"]]
    out["one_way_ruler_false_verdicts"] = dict(
        n=len(diff), read_ko="한 방향·정점↔정점 잣대였다면 «떨어짐(뜬 부품)» 이라고 답했을 쌍",
        worst=sorted(diff, key=lambda d: -d["gap_vertex_only_mm"])[:8])
    #  ⭐ 방향이 왜 둘 다 필요한가 — **정점↔면조차** 한 방향만 재면 틀린다. 실측으로 보인다.
    #  ⚠ 붙어 있는 쌍(작은 쪽 ≈ 0)은 비가 무한대로 튀어 뜻이 없다 — **둘 다 1 µm 이상**인
    #    쌍만 센다. 그래야 «떨어진 거리를 한 방향으로 재면 얼마나 틀리나» 라는 물음이 성립한다.
    dd = [dict(a=r["a"], b=r["b"], a_to_b_mm=r["gap_a_to_b_mm"], b_to_a_mm=r["gap_b_to_a_mm"],
               ratio=round(max(r["gap_a_to_b_mm"], r["gap_b_to_a_mm"])
                           / min(r["gap_a_to_b_mm"], r["gap_b_to_a_mm"]), 2))
          for r in rels if min(r["gap_a_to_b_mm"], r["gap_b_to_a_mm"]) >= 1e-3]
    out["direction_matters"] = dict(
        read_ko="정점↔면을 **한 방향만** 재면 얼마나 틀리는가 — 두 방향 값의 비(둘 다 1 µm 이상인 "
                "쌍만). 정점이 성긴 쪽에서만 재면 접촉면 한복판을 통째로 놓친다.",
        n_pairs=len(dd),
        worst=sorted(dd, key=lambda d: -d["ratio"])[:8],
        max_ratio=max([d["ratio"] for d in dd], default=1.0))
    #  ⭐ 봉인용 지문 — **관계표 자체**의 해시. 형상이 그대로면 값이 그대로여야 한다(결정성).
    out["relation_sha1"] = hashlib.sha1(
        "|".join(f"{r['a']}~{r['b']}~{r['relation']}~{r['cross_pairs']}~"
                 f"{round(r['gap_mm'], 4)}~{round(r['coplanar_a_mm2'] + r['coplanar_b_mm2'], 3)}"
                 for r in sorted(rels, key=lambda r: (r["a"], r["b"]))).encode()).hexdigest()
    if verbose:
        print(f"  {name:12s} 부품 {n:3d} · 쌍(잰것) {len(rels):3d} · 관계 {counts} · "
              f"자기교차 {len(self_bad)} · 동일평면 {out['coplanar']['area_mm2']:.2f} mm² · "
              f"뜬부품 {len(out['floating'])}")
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  ④ 예산표 — ⚠ 전부 «지금 이만큼이다» 라는 **선언**이지 «이만큼이 옳다» 가 아니다.
#     (이 저장소의 기존 규약 — PROP_BELL_* · BURIED_FACE_BUDGET_PCT 와 같은 뜻.)
#     값은 2026-08-16 전 기종 실측으로 초기화했고, 새로 생기는 결함은 예산을 넘겨 **실패**한다.
# ─────────────────────────────────────────────────────────────────────────────
#  ⑴ 자기교차 — 원칙은 0 이다. 한 부품이 자기를 뚫는 것은 어떤 경우에도 설계가 아니다.
#     ⭐ 2026-08-16 실측: **전 기종 0**. 그래서 이 표에는 예외가 하나도 없다.
SELF_INTERSECT_BUDGET = {"_default": 0}

#  ⑵ 부품 간 교차(관통) 면적 [기체 표면적 대비 %] — 우리 조립은 그룹끼리 불리언 합집합을
#     **안 하므로** 설계상 파고드는 자리가 있다(암이 동체에 꽂히고, 프롭이 벨 위에 앉는다).
#     ⚠ 뜻: «다른 부품 표면에 잘리는 삼각형» 의 면적 비율. 매몰면적(아래 inside_faces)과 다르다.
CROSS_AREA_BUDGET_PCT: dict = {
    "_default": 0.1,
    "mini5pro": 38.8,     # 실측 35.27
    "mavic4pro": 26.6,    # 실측 24.15
    "matrice4e": 33.9,    # 실측 30.82
    "s1000plus": 17.9,    # 실측 16.31
    "phantom4": 30.5,     # 실측 27.74
    "typhoonh480": 31.2,  # 실측 28.40
    "x500v2": 44.1,       # 실측 40.09
    "phantom3": 22.8,     # 실측 20.69
    "m350rtk": 34.4,      # 실측 31.27
    "mini2": 38.6,        # 실측 35.07
}

#  ⑶ 동일평면 면적 [기체 표면적 대비 %] — 같은 자리에 두 껍질이 겹치면 PO 가 같은 면을
#     **두 재질로 두 번** 더한다(SBR 은 first-hit 이라 어느 한쪽만 맞고, 어느 쪽이 이길지는
#     광선 순서가 정한다 — 즉 두 커널 다 이 자리에서 답이 흔들린다).
#     ⭐ 큰 자리: x500v2 9.16 %(accent 판이 arm 표면에 딱 붙어 있다) · s1000plus 5.07 %.
COPLANAR_AREA_BUDGET_PCT: dict = {
    "_default": 0.1,
    "mini5pro": 0.85,     # 실측 0.768
    "mavic4pro": 1.76,    # 실측 1.597
    "matrice4e": 0.15,    # 실측 0.132
    "s1000plus": 5.58,    # 실측 5.070
    "phantom4": 1.54,     # 실측 1.399
    "typhoonh480": 0.08,  # 실측 0.070
    "x500v2": 10.10,      # 실측 9.155
    "phantom3": 2.70,     # 실측 2.450
    "m350rtk": 1.19,      # 실측 1.076
    "mini2": 0.85,        # 실측 0.771
}

#  ⑷ 뜬 부품 — (기종, 그룹) → 허용 이격 [mm]. **원칙은 «붙어 있어야 한다»(0)** 이고,
#     지금 떠 있는 것만 여기 선언한다. ⚠ 선언은 «옳다» 는 뜻이 아니다 — 아래 FLOAT_NOTE 가
#     칸마다 «설계» 인지 «의심» 인지 적는다. 의심 칸은 형상 라운드의 할 일 목록이다.
FLOAT_BUDGET_MM: dict = {
    "_default": 0.0,
    ("mini5pro", "prop"): 0.80,        # 실측 0.711
    ("s1000plus", "prop"): 1.40,       # 실측 1.244
    ("s1000plus", "pcb"): 6.50,        # 실측 5.931
    ("phantom4", "gear"): 8.90,        # 실측 8.052
    ("phantom4", "canopy"): 5.00,      # 실측 4.525
    ("x500v2", "prop"): 2.20,          # 실측 1.935
    ("x500v2", "pcb"): 5.50,           # 실측 5.000
    ("phantom3", "prop"): 1.00,        # 실측 0.911
    ("phantom3", "gear"): 15.20,       # 실측 13.838
    ("phantom3", "camera"): 9.00,      # 실측 8.184
}
FLOAT_NOTE = {
    ("mini5pro", "prop"): "설계 — 프롭은 모터 벨 위 스탠드오프(drones.PROP_STANDOFF_M)로 띄운다",
    ("s1000plus", "prop"): "설계 — 같음",
    ("x500v2", "prop"): "설계 — 같음",
    ("phantom3", "prop"): "설계 — 같음",
    ("s1000plus", "pcb"): "⚠의심 — 기판이 아무 것에도 안 닿는다(스탠드오프 부품이 없다). 형상 라운드 몫",
    ("x500v2", "pcb"): "⚠의심 — 같음(5.0 mm)",
    ("phantom4", "gear"): "⚠⚠의심 — **착륙 다리가 동체에서 8 mm 떠 있다**. 실물은 붙어 있다",
    ("phantom4", "canopy"): "⚠의심 — 캐노피 조각 하나가 4.5 mm 떠 있다",
    ("phantom3", "gear"): "⚠⚠의심 — 다리가 13.8 mm 떠 있다(가장 큰 이격)",
    ("phantom3", "camera"): "⚠의심 — 짐벌/카메라 조각들이 서로·동체에서 2.4~8.2 mm 씩 떨어져 있다",
}

#  ⑸ 완전매몰 쌍 개수 — battery/pcb 가 셸 안에 통째로 든 것은 **설계**다(mesh_buried 머리말:
#     반투명 셸을 통과해 내부 금속이 보이는 효과를 그렇게 1차 근사한다). 개수를 못 박아,
#     **새로 통째로 묻히는 부품이 생기면** 걸리게 한다.
ENGULFED_PAIRS_BUDGET: dict = {
    "_default": 0,
    "mini5pro": 2, "mavic4pro": 4, "matrice4e": 1, "s1000plus": 0, "phantom4": 10,
    "typhoonh480": 1, "x500v2": 0, "phantom3": 3, "m350rtk": 1, "mini2": 0,
}


def _budget(tbl, name, key=None):
    if key is not None and (name, key) in tbl:
        return tbl[(name, key)]
    return tbl.get(name, tbl["_default"])


def check_placement(census: dict) -> dict:
    """원장 한 줄 ↔ 예산표 대조. 반환 dict 의 `ok` 가 게이트 판정이다."""
    nm = census["name"]
    fails = []
    si = census["self_intersection"]
    if si["n_pairs"] > _budget(SELF_INTERSECT_BUDGET, nm):
        fails.append(f"자기교차 {si['n_pairs']}쌍 > 예산 {_budget(SELF_INTERSECT_BUDGET, nm)}")
    cx = census["crossing"]["area_pct"]
    if cx > _budget(CROSS_AREA_BUDGET_PCT, nm):
        fails.append(f"부품간 교차면적 {cx} % > 예산 {_budget(CROSS_AREA_BUDGET_PCT, nm)} %")
    cp = census["coplanar"]["area_pct"]
    if cp > _budget(COPLANAR_AREA_BUDGET_PCT, nm):
        fails.append(f"동일평면 {cp} % > 예산 {_budget(COPLANAR_AREA_BUDGET_PCT, nm)} %")
    ne = len(census["engulfed"])
    if ne > _budget(ENGULFED_PAIRS_BUDGET, nm):
        fails.append(f"완전매몰 쌍 {ne} > 예산 {_budget(ENGULFED_PAIRS_BUDGET, nm)}")
    for f in census["floating"]:
        lim = _budget(FLOAT_BUDGET_MM, nm, f["group"])
        if f["gap_mm"] > lim:
            fails.append(f"뜬 부품 {f['pid']} 이격 {f['gap_mm']} mm > 예산 {lim} mm "
                         f"(가장 가까운 것 {f['nearest']})")
    return dict(name=nm, failures=fails, ok=not fails,
                budgets=dict(self_intersect=_budget(SELF_INTERSECT_BUDGET, nm),
                             cross_pct=_budget(CROSS_AREA_BUDGET_PCT, nm),
                             coplanar_pct=_budget(COPLANAR_AREA_BUDGET_PCT, nm),
                             engulfed_pairs=_budget(ENGULFED_PAIRS_BUDGET, nm)))


def census_all(verbose=True, keys=None) -> dict:
    """DRONES 레지스트리 전 기종. 빌드가 깨진 기종은 **빈칸으로 남긴다**(가짜 통과 금지)."""
    from drones import DRONES, build_drone
    out = {}
    for k, s in DRONES.items():
        if keys and k not in keys:
            continue
        try:
            m = build_drone(s)
        except Exception as e:                       # noqa: BLE001
            out[k] = dict(name=k, build_failed=f"{type(e).__name__}: {e}", ok=None)
            if verbose:
                print(f"  {k:12s} ⛔ 빌드 실패 — {type(e).__name__}: {e}")
            continue
        c = placement_census(m, k, verbose=verbose)
        c["verdict"] = check_placement(c)
        out[k] = c
    return out


def assert_placement_ok(keys=None):
    """회귀 봉인 — 예산을 넘기면 예외. 빌드 실패도 실패로 친다."""
    res = census_all(verbose=False, keys=keys)
    bad = {k: (v.get("build_failed") or v["verdict"]["failures"])
           for k, v in res.items() if v.get("build_failed") or not v["verdict"]["ok"]}
    if bad:
        raise AssertionError(f"배치·겹침·묻힘 검사 실패: {bad}")
    return True


if __name__ == "__main__":
    import json
    print("=" * 108)
    print("배치·겹침·묻힘 전수 — 부품쌍 관계(떨어짐/접촉/관통/완전매몰) · 자기교차 · 동일평면 · 뜬 부품")
    print("=" * 108)
    res = census_all(verbose=True)
    for k, c in res.items():
        if c.get("build_failed"):
            continue
        v = c["verdict"]
        print(f"\n[{k}] {'✅' if v['ok'] else '❌'} {v['failures']}")
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=1)[:4000])
