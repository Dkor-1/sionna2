# -*- coding: utf-8 -*-
"""
prop_thickness.py — **프로펠러 날 두께를 기종별로, 우리 메쉬에서 직접 잰다** (2026-08-16)
=============================================================================================
감사 `docs/MESH_AUDIT_0816.md` I1 — «이 감사에서 가장 큰 단일 실행가능 dB» 의 집행 파일이다.

■ 무엇이 문제였나 (쉬운 말로)
  전파 계산에서 프로펠러 날은 «두께 d 의 얇은 판» 으로 다뤄진다. 그 d 가 반사 세기를 정하는데,
  저장소는 **전 기종에 스칼라 하나(1.43 mm)** 를 써 왔다. 그런데
    ① 그 1.43 mm 는 메쉬를 잰 값이 아니라 **matrice4e 를 가정하고 상수에서 유도한 값**이고
       (`benchmark/material_sources.py :: blade_thickness_stats`, 감사 m1),
    ② 우리 메쉬의 실제 날 두께는 기종마다 **4.5 배** 벌어진다(아래 표).
  실증 표적이 Matrice 4E → **Mini 5 Pro** 로 옮겨가는 중인데, mini5pro 에 1.43 mm 를 그대로
  쓰면 프롭 에코를 **몇 dB 밝게** 본다. 그래서 «기종별로, 메쉬에서» 재는 함수가 필요하다.

■ 어떻게 재나 — 감사 원장과 **같은 자**
  프로펠러 단면의 정식 정의는 «반경 r 인 **원통**으로 자른 면» 이다(평면으로 자르면 스윕이 큰
  프롭에서 팁을 빗나간다). 그래서
    1. 회전축(z) 중심 반경 r 원통과 메쉬의 **정확한 교선**을 구한다.
       ⭐ 표면을 무작위로 뿌려 근사하지 않는다 — 모서리마다 |P(t)|_xy = r 을 푸는 2차방정식을
         닫힌 형태로 풀어 교점을 얻고, 삼각형별 선분을 이어 **닫힌 고리**를 만든다.
         그래서 **결과가 씨앗(seed)에 안 흔들린다**(무작위 표집판은 같은 기체에서 ±2~5 % 튀었다).
    2. 그 고리에서 **최대 캘리퍼 = 시위(chord)**, **넓이 ÷ 시위 = 시위평균 두께**.
       ⭐ 넓이÷시위가 곧 «시위 전체에 걸친 평균 두께» 다(∫t dx / c). 구간을 잘라 최대·최소를
         재는 방식보다 정확하고 잡음이 없다.
    3. 스팬평균은 **시위 가중**(∫t·c dr / ∫c dr) — 산란 기여가 국소 면적에 비례하기 때문이다.
    4. 허브는 «t/c 가 0.20 을 넘거나 원주각이 75° 를 넘으면 날이 아니다» 로 걸러낸다
       (`benchmark/measure_reference_props.py` 와 같은 규약).

■ 자를 먼저 검증했다
  · 이 파일이 재는 프롭 지름은 전 10기종에서 공칭값과 **소수 둘째자리까지 일치**한다
    (119.10 / 152.40 / … / 533.40 mm) — 스윕디스크 정규화가 실제로 작동한다는 독립 확인.
  · matrice4e 에 대해 이 파일이 내는 두께(1.414 mm, 0.20–0.96R)는 해석식 정본 1.4302 mm 와
    **1.1 % (|Γ| 로 0.09 dB)** 안에서 만난다 — 잣대가 서로를 지지한다.
  · 감사 원장의 기종별 값(mini2 0.664 … m350rtk 2.879 mm)보다 **일관되게 4~7 % 낮다.**
    원인은 알고 있다: 원장은 시위의 3~97 % 구간을 41 조각으로 잘라 각 조각의 최대·최소로
    두께를 읽었고(끝의 얇은 부분이 빠져 평균이 올라간다), 여기서는 넓이÷시위로 **전 시위**를
    적분한다. **기종 간 비(=dB 를 만드는 것)는 그대로다** — 최대/최소 배수 원장 4.34 ↔ 여기 4.48.

■ 이 파일이 «모른다» 고 말하는 것
  · 이것은 **우리 메쉬의 두께**이지 실물 프롭의 두께가 아니다. 실물 실측은 DJI Mini 2 공식
    CAD 하나뿐이고(0.60 mm, 0.20–0.96R), matrice4e 실물 날 두께는 저장소에 **1차 출처가 0** 이다
    (감사 판정보류 ?2 — 두 추정이 0.99 ↔ 1.40 mm 로 1.41 배 벌어진다).
  · 그러므로 여기 숫자는 «우리 형상 법칙이 함의하는 두께» 이고, 실물 앵커링은 별개 축이다.

실행:  cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
         benchmark/measure_prop_thickness_by_drone.py
산출:  outputs/prop_thickness_by_drone.json   (이 파일의 `load_ledger()` 가 읽는다)
GPU 미사용 — numpy·trimesh CPU 만 쓴다.
"""
from __future__ import annotations

import json
import os

import numpy as np

#: 산출 원장 경로 — 기종별 두께 표
LEDGER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "outputs", "prop_thickness_by_drone.json")

#: 헤드라인 스팬 밴드 (r/R). 감사가 DJI 실물과 우리 메쉬를 견줄 때 쓴 «두 쪽 같은 자» 다.
#:   안쪽 0.20 미만 = 허브에 물린 생크라 익형이 아니고,
#:   바깥쪽 0.96 초과 = 로프트 마감면(팁 캡) 인공물이 섞인다.
BAND_HEADLINE = (0.20, 0.96)
#: 참고용 밴드 — 날 전체 / 팁 쪽(마이크로도플러 f_tip 을 만드는 구간)
BAND_FULL = (0.10, 0.98)
BAND_TIP = (0.80, 0.96)

#: 문서가 «정본» 이라 부르는 해석식 값[mm] (matrice4e 가정, 상수에서 유도 — 감사 m1)
CANON_ANALYTIC_MM = 1.4302


# --------------------------------------------------------------------------- #
#  ① 원통 단면 — 정확한 교선
# --------------------------------------------------------------------------- #
def cylinder_section_loops(V: np.ndarray, F: np.ndarray, r: float) -> list[np.ndarray]:
    """반경 `r` 원통(축 = z)과 삼각형 메쉬의 교선을 **닫힌 고리** 목록으로 돌려준다.

    돌려주는 각 고리는 (n, 2) 배열이고 열은 `(u, v)` = (호길이, 축방향):
      u = r·(φ − φ_중심)  — 원통을 펼친 좌표. v = z.
    교점은 모서리마다 |P(t)|_xy = r 을 만족하는 t 를 **2차방정식으로 정확히** 풀어 얻는다."""
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    if len(F) == 0:
        return []
    s_all = np.hypot(V[:, 0], V[:, 1]) - r

    # 모서리를 유일화한다(삼각형 세 모서리 → 공유 모서리는 하나로)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key = np.sort(E, axis=1)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()                       # numpy 2.x 는 (n,1) 을 줄 수 있다
    s = s_all[uniq]
    cross = (s[:, 0] * s[:, 1]) < 0                     # 원통면을 가로지르는 모서리
    ci = np.flatnonzero(cross)
    if len(ci) < 3:
        return []

    A, B = V[uniq[ci, 0]], V[uniq[ci, 1]]
    d = B - A
    qa = d[:, 0] ** 2 + d[:, 1] ** 2
    qb = 2.0 * (A[:, 0] * d[:, 0] + A[:, 1] * d[:, 1])
    qc = A[:, 0] ** 2 + A[:, 1] ** 2 - r * r
    disc = np.sqrt(np.maximum(qb * qb - 4.0 * qa * qc, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        t1 = (-qb + disc) / (2.0 * qa)
        t2 = (-qb - disc) / (2.0 * qa)
    t = np.where((t1 >= -1e-12) & (t1 <= 1.0 + 1e-12), t1, t2)
    P = A + np.clip(t, 0.0, 1.0)[:, None] * d           # 교점 [m]

    # 삼각형마다 «가로지른 모서리 2개» → 선분 하나
    pt_of_edge = -np.ones(len(uniq), np.int64)
    pt_of_edge[ci] = np.arange(len(ci))
    tri_e = np.stack([inv[:len(F)], inv[len(F):2 * len(F)], inv[2 * len(F):]], axis=1)
    hit = cross[tri_e]
    adj: dict[int, list[int]] = {}
    for tri in np.flatnonzero(hit.sum(1) == 2):
        a, b = pt_of_edge[tri_e[tri][hit[tri]]]
        adj.setdefault(int(a), []).append(int(b))
        adj.setdefault(int(b), []).append(int(a))
    if not adj:
        return []

    # 선분을 이어 고리로
    seen: set[int] = set()
    loops = []
    for start in list(adj):
        if start in seen:
            continue
        chain = [start]
        seen.add(start)
        cur, prev = start, None
        while True:
            nxt = [q for q in adj[cur] if q != prev and q not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen.add(cur)
            chain.append(cur)
        if len(chain) < 6 or start not in adj.get(chain[-1], []):
            continue                                     # 안 닫힌 사슬은 버린다
        p = P[np.asarray(chain)]
        phi = np.arctan2(p[:, 1], p[:, 0])
        phi0 = np.arctan2(np.sin(phi).mean(), np.cos(phi).mean())
        rel = np.mod(phi - phi0 + np.pi, 2.0 * np.pi) - np.pi   # 중심 기준 언랩
        loops.append(np.c_[r * rel, p[:, 2]])
    return loops


def section_metrics(Q: np.ndarray) -> dict | None:
    """닫힌 단면 고리 → 시위·단면적·**시위평균 두께**·최대두께.

    · 시위 = 볼록껍질의 최대 캘리퍼(가장 먼 두 점 사이 거리)
    · 시위평균 두께 = 단면적 ÷ 시위  (= ∫t dx / c, 정의 그대로)
    · 최대두께 = 시위선에 수직인 방향의 폭"""
    from scipy.spatial import ConvexHull
    if len(Q) < 4:
        return None
    try:
        H = Q[ConvexHull(Q).vertices]
    except Exception:
        return None
    D = H[:, None, :] - H[None, :, :]
    d2 = (D ** 2).sum(-1)
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    c = float(np.sqrt(d2[i, j]))
    if c <= 0:
        return None
    x, y = Q[:, 0], Q[:, 1]
    area = abs(float(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))
    e = (H[j] - H[i]) / c
    Pc = (Q - H[i]) @ np.array([[e[0], e[1]], [-e[1], e[0]]]).T
    t_max = float(Pc[:, 1].max() - Pc[:, 1].min())
    return dict(chord=c, area=area, t_chordmean=area / c, t_max=t_max)


# --------------------------------------------------------------------------- #
#  ② 기종 하나 재기
# --------------------------------------------------------------------------- #
def prop_thickness_profile(spec, n: int = 10, step: float = 0.01,
                           rr_lo: float = 0.10, rr_hi: float = 0.98,
                           blade_law: str = "legacy", pitch_law=None,
                           tc_max: float = 0.20, arc_max_deg: float = 75.0) -> dict:
    """기종 하나의 **반경별 두께 프로파일**. 값 단위는 전부 mm.

    `n` 은 `drones.build_propeller` 의 스팬 분할 힌트(기본 10 = 실제 출하 경로 n_sec 20).
    돌려주는 `stations` 는 «r/R, 시위, 시위평균두께, 최대두께» 표이고,
    `bands` 는 밴드별 시위가중 스팬평균이다."""
    from drones import build_propeller

    m = build_propeller(spec, n=n, blade_law=blade_law, pitch_law=pitch_law)
    V = np.asarray(m.v, float) * 1000.0                  # m → mm
    F = np.asarray(m.f, np.int64)
    R_disc = float(np.hypot(V[:, 0], V[:, 1]).max())

    per_rr: dict[float, list[dict]] = {}
    for rr in np.arange(rr_lo, rr_hi + 1e-9, step):
        r = float(rr) * R_disc
        for Q in cylinder_section_loops(V, F, r):
            mt = section_metrics(Q)
            if mt is None:
                continue
            arc = float(np.degrees((Q[:, 0].max() - Q[:, 0].min()) / max(r, 1e-12)))
            if arc > arc_max_deg or mt["t_max"] / mt["chord"] > tc_max:
                continue                                  # 허브·생크는 날이 아니다
            per_rr.setdefault(round(float(rr), 4), []).append(mt)

    rr_v, ch_v, tc_v, tm_v, nb_v = [], [], [], [], []
    for rr in sorted(per_rr):
        g = per_rr[rr]
        rr_v.append(rr)
        ch_v.append(float(np.mean([q["chord"] for q in g])))
        tc_v.append(float(np.mean([q["t_chordmean"] for q in g])))
        tm_v.append(float(np.mean([q["t_max"] for q in g])))
        nb_v.append(len(g))                               # 그 반경에서 잡힌 날 장수
    rr_a, ch_a, tc_a, tm_a = map(np.asarray, (rr_v, ch_v, tc_v, tm_v))

    def band_mean(lo, hi, y):
        sel = (rr_a >= lo) & (rr_a <= hi)
        if sel.sum() < 3:
            return None
        return float(np.trapezoid(y[sel] * ch_a[sel], rr_a[sel])
                     / np.trapezoid(ch_a[sel], rr_a[sel]))

    bands = {}
    for name, (lo, hi) in (("headline_0p20_0p96", BAND_HEADLINE),
                           ("full_0p10_0p98", BAND_FULL),
                           ("tip_0p80_0p96", BAND_TIP)):
        bands[name] = dict(r_over_R=[lo, hi],
                           t_chordmean_mm=band_mean(lo, hi, tc_a),
                           t_max_mm=band_mean(lo, hi, tm_a))
    return dict(
        key=getattr(spec, "key", None), name=getattr(spec, "name", None),
        prop_dia_nominal_mm=float(spec.prop_dia_mm),
        prop_dia_measured_mm=2.0 * R_disc,
        prop_blades=int(spec.prop_blades),
        blade_law=blade_law, pitch_law=pitch_law or "legacy",
        n_sec=max(12, n * 2), n_stations=len(rr_v),
        n_blades_seen=int(np.median(nb_v)) if nb_v else 0,
        bands=bands,
        stations=[dict(r_over_R=float(a), chord_mm=float(b), t_chordmean_mm=float(c),
                       t_max_mm=float(d), t_over_c=float(d / b) if b else None)
                  for a, b, c, d in zip(rr_v, ch_v, tc_v, tm_v)],
    )


def prop_slab_thickness_mm(spec, band: tuple = BAND_HEADLINE, **kw) -> float:
    """⭐**이 기체의 프롭 슬래브 두께[mm]** — 재질 계산에 넘길 한 숫자.

        from materials import set_thickness_mm
        from prop_thickness import prop_slab_thickness_mm
        set_thickness_mm(prop=prop_slab_thickness_mm(DRONES["mini5pro"]))

    ⚠ 메쉬를 새로 지어서 재므로 기체당 0.5~1 초 걸린다. 반복해서 쓸 값이면
      `load_ledger()` 로 원장에서 읽어라(같은 수, 즉시)."""
    prof = prop_thickness_profile(spec, **kw)
    for b in prof["bands"].values():
        if tuple(b["r_over_R"]) == tuple(band):
            return float(b["t_chordmean_mm"])
    lo, hi = band
    rr = np.asarray([s["r_over_R"] for s in prof["stations"]])
    ch = np.asarray([s["chord_mm"] for s in prof["stations"]])
    tc = np.asarray([s["t_chordmean_mm"] for s in prof["stations"]])
    sel = (rr >= lo) & (rr <= hi)
    return float(np.trapezoid(tc[sel] * ch[sel], rr[sel]) / np.trapezoid(ch[sel], rr[sel]))


# --------------------------------------------------------------------------- #
#  ③ 원장 읽기 — 값만 필요할 때(즉시)
# --------------------------------------------------------------------------- #
def load_ledger(path: str | None = None) -> dict:
    """`outputs/prop_thickness_by_drone.json` 을 읽어 돌려준다. 없으면 예외."""
    p = path or LEDGER_PATH
    if not os.path.exists(p):
        raise FileNotFoundError(
            f"{p} 가 없다. 먼저 만들어라: "
            f"PYTHONPATH=src:benchmark python benchmark/measure_prop_thickness_by_drone.py")
    with open(p) as f:
        return json.load(f)


def thickness_mm(key: str, band: str = "headline_0p20_0p96", path: str | None = None) -> float:
    """원장에서 기종 하나의 두께[mm]를 꺼낸다(메쉬를 다시 안 짓는다)."""
    doc = load_ledger(path)
    return float(doc["per_drone"][key]["bands"][band]["t_chordmean_mm"])
