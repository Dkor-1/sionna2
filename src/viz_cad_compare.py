# -*- coding: utf-8 -*-
"""
viz_cad_compare.py — **제조사 공식 CAD 와의 대조**: 치수·구조·패싯
====================================================================

무엇을 하나
-----------
`assets/meshes/reference_study/` 의 **제조사 1차 CAD** 세 건과 우리 파라메트릭 메쉬를
같은 자로 잰다.

  · **Holybro X500 V2** — 우리 `x500v2` 와 **같은 기체**다. 치수를 1:1 로 맞댈 수 있다.
  · **ModalAI Sentinel** — 다른 기체지만 프롭 팁 반경 0.361 m 로 우리 `matrice4e`(0.356)·
    `mavic4pro`(0.358) 와 같은 크기대이고, **부품이 재질명으로 갈린 유일한 공식 어셈블리**다.
  · **Freefly Astro** — 다른 기체이고 **셸(외피)뿐**이지만, 0.4–0.73 m 공백을 메우는 큰 쿼드다.

만드는 것
---------
  outputs/mesh_compare_cad.json            원장 (모든 숫자의 출처)
  outputs/figures/cad_compare_dimensions.png   치수: 우리 vs CAD vs 공표
  outputs/figures/cad_compare_facets.png       패싯 크기·PO 위상오차 분포
  outputs/figures/cad_compare_structure.png    구조: 부품 수·범주별 면적 점유

⛔ 라이선스
-----------
ModalAI·Freefly·Holybro·Parrot 는 **라이선스를 명시하지 않는다**. 치수 대조·구조 학습은
자유롭게 하되 **그들의 지오메트리를 우리 자산에 복사하지 않고, 그들의 메쉬를 이미지로
재배포하지 않는다.** 이 스크립트는 CAD 를 **숫자로만** 다룬다 — 렌더는 우리 메쉬만 한다.

⭐ 방법에 대한 정직한 진술 — "패싯이 λ 보다 작아야 한다"는 절반만 맞다
--------------------------------------------------------------------
우리 PO 적분(`rcs_sbr`)은 **패싯마다 적분하지 않는다.** Mitsuba 광선을 간격
d = λ/12 (3.5 GHz 에서 7.14 mm) 격자로 쏘고 **맞은 지점**에서 적분한다. 그래서 평평한
면은 패싯이 아무리 커도 손해가 없다 — 큰 삼각형이 평면을 **정확히** 표현하기 때문이다.
실제로 제조사 CAD 자신도 평면 위에서는 250 mm 짜리 삼각형을 쓴다.

진짜로 걸리는 것은 두 가지다.
  (1) **곡면의 새그(sagitta)** — 다면체가 매끄러운 면에서 δ 만큼 벗어나면 왕복 위상이
      2kδ 만큼 틀어진다. 국소 반경 R ≈ s/θ (s=패싯 크기, θ=인접면 꺾임각) 이므로
      **δ ≈ s·θ/8**. 이 스크립트는 이걸 잰다.
  (2) **광선 격자보다 작은 디테일** — d=7.14 mm 보다 작은 나사산·와셔는 광선이
      못 본다. 제조사 CAD 면적의 30–40 % 가 그 아래에 있다. 우리가 그걸 안 만든 것은
      결함이 아니라 **적분 격자와 맞는 선택**이다.

θ ≥ 30° 인 면은 곡면 이산화가 아니라 **진짜 모서리**(판 끝·직각)이므로 새그 통계에서
빼고 그 면적 비율을 따로 보고한다.

실행
----
  cd /home/yunjung/workspace/sionna2
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/viz_cad_compare.py
  ... --only measure     # JSON 만
  ... --only figs        # 그림만 (JSON 을 디스크에서 다시 읽는다)
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import time

import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ⚠ 나눔고딕에는 유니코드 마이너스(U+2212)가 없다 → 로그축 눈금이 `10^{π1}` 로 깨진다.
#   수식(mathtext)만 DejaVu 로 돌린다. 본문 한글 폰트는 그대로다.
plt.rcParams["mathtext.fontset"] = "dejavusans"

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
LEDGER = os.path.join(OUT, "mesh_compare_cad.json")
X500_CAD_JSON = os.path.join(OUT, "x500v2_cad.json")
REF = os.path.join(ROOT, "assets", "meshes", "reference_study")

C0 = 299_792_458.0
BANDS = {"LTE": 1.843e9, "5G": 3.500e9, "WiFi": 5.210e9}
FC_REF = BANDS["5G"]                      # 패싯 판정 기준 밴드
RAY_DIV = 12                              # rcs_sbr.DEFAULT_DIV 와 같아야 한다(아래에서 검사)
SHARP_DEG = 30.0                          # 이 이상 꺾이면 '진짜 모서리' 로 보고 새그 통계에서 뺀다
PHASE_BUDGET_DEG = 22.5                   # 왕복 위상 2kδ 예산 = λ/16 경로차

MESH_SOURCES = ("src/drone_cad.py", "src/drones.py", "src/cadkit.py", "src/geom.py")

#: 공식 CAD 세 건. `maps_to` 가 None 이면 **다른 기체**라 치수 1:1 대조를 하지 않는다.
CAD_FILES = {
    "holybro_x500v2": dict(
        label="Holybro X500 V2", short="X500 V2",
        glb="holybro_x500v2/x500v2-frame.glb", maps_to="x500v2",
        vendor="Holybro", licence="no licence stated - dimensions only, do not redistribute",
        note_ko="우리 x500v2 와 **같은 기체**. 244 인스턴스 어셈블리(나사까지 들어 있다)."),
    "modalai_sentinel": dict(
        label="ModalAI Sentinel", short="Sentinel",
        glb="modalai_sentinel/sentinel_drone.glb", maps_to=None,
        vendor="ModalAI", licence="no licence stated - dimensions only, do not redistribute",
        note_ko="다른 기체. 부품명이 재질을 자백하는 유일한 공식 어셈블리(McMaster 품번까지 남아 있다)."),
    "freefly_astro": dict(
        label="Freefly Astro (Max)", short="Astro",
        glb="freefly_astro_max/astro_max.glb", maps_to=None,
        vendor="Freefly", licence="no licence stated - dimensions only, do not redistribute",
        note_ko="다른 기체이고 파일명이 [Shelled] — **외피뿐, 내부 산란체 없음**. 외형 치수만 값어치가 있다."),
}

#: 공표 제원 vs **제조사 자신의 CAD**. 우리 메쉬가 도달할 수 있는 정확도의 **바닥**을 정한다.
#:   published 는 제조사가 낸 숫자, cad_key 는 아래 `_cad_named_dims` 가 재는 이름.
#:   cad_key   = 이 스크립트가 GLB 에서 직접 잰 값의 이름
#:   json_key  = 있으면 `outputs/x500v2_cad.json`(STEP 원문에서 **원통면 축**으로 잰 값)을 우선한다.
#:               STEP 쪽이 정밀도가 높다 — GLB 값은 교차검증으로만 남긴다.
SPEC_VS_CAD = (
    dict(cad="holybro_x500v2", dim="Wheelbase\n(motor-to-motor diagonal)",
         published_mm=500.0, cad_key="wheelbase_mm", json_key="wheelbase_mm",
         source="docs.holybro.com X500 V2 spec sheet, 'Wheelbase: 500mm'",
         caveat="published value is rounded"),
    dict(cad="holybro_x500v2", dim="Plate width\nacross flats",
         published_mm=144.0, cad_key="plate_span_across_flats_mm",
         json_key="plate_span_across_flats_mm",
         source="docs.holybro.com X500 V2, '144 x 144 mm' plate", caveat=None),
    dict(cad="holybro_x500v2", dim="Landing gear\nheight",
         published_mm=215.0, cad_key="gear_height_mm", json_key="gear_height_mm",
         source="docs.holybro.com X500 V2 landing gear", caveat=None),
    dict(cad="modalai_sentinel", dim="Motor-to-motor\nsquare side",
         published_mm=334.0, cad_key="motor_square_side_mm", json_key=None,
         source="docs.modalai.com Sentinel, 334 x 334 x 133 mm", caveat=None),
    dict(cad="modalai_sentinel", dim="Overall\nheight",
         published_mm=187.0, cad_key="overall_height_mm", json_key=None,
         source="docs.modalai.com Sentinel, 591 x 591 x 187 mm with props", caveat=None),
    dict(cad="freefly_astro", dim="Motor-axis\ndiagonal",
         published_mm=917.0, cad_key="motor_axis_diagonal_mm", json_key=None,
         source="docs.freeflysystems.com Astro, 917 mm (36.1 in) diagonal",
         caveat="917 is likely mount-edge to mount-edge, not axis to axis"),
)

#: CAD 부품명 → 범주. 위에서부터 처음 맞는 것을 쓴다(순서가 의미를 갖는다).
CAT_RULES = (
    ("fastener",    r"^(GB70|ZSLM|LM-M|M25-|M3-\d|NILONGZHU|9\d{4}A\d|90304A|95947A|Aluminum_Standoffs)"),
    ("motor",       r"(DJ-2216|T-MOTOR)"),
    ("electronics", r"(PCB-|BM06B|XT60|CAMERA|GUANGLIU|VOXL|ESC|VoxlStCam|New 4K|GPS|SpektrumRC|SF-C7|Tracking45|Fan)"),
    ("tube / arm",  r"(CARBON-FIBER-TUBE|GUAN-CHENG|Arm -)"),
    ("plate / body", r"(PLATE|PLAT-|PYLONS|plate|DeckBody|Lid|Tray|Oval|Standoff)"),
    ("landing gear", r"(JIAO-EVA|MAO-JIAO|landing_gear|Foot|skid)"),
    ("clamp / mount", r"(HMX5V|JIA-|JIAO-|HUAN-|ZHIJIA|mount|mast|Damper)"),
)
CAT_ORDER = ("plate / body", "tube / arm", "motor", "electronics",
             "landing gear", "clamp / mount", "fastener", "other")

#: 색 — dataviz 기본 팔레트의 categorical 슬롯 1..7 을 **고정 순서**로 쓴다(돌려쓰지 않는다).
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7")
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
CAD_GREY = "#3a3a38"
STATUS = {"good": "#0ca30c", "warning": "#fab219", "critical": "#d03b3b"}


# --------------------------------------------------------------------------- #
#  0.  자잘한 유틸
# --------------------------------------------------------------------------- #
def _mtime(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _stamp(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else None


def _load_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _categorise(name: str) -> str:
    for cat, pat in CAT_RULES:
        if re.search(pat, name):
            return cat
    return "other"


def _base_name(k: str) -> str:
    """trimesh 가 인스턴스마다 붙이는 `_1`,`_2` 접미사를 떼어 **부품 종류**를 얻는다."""
    return re.sub(r"_\d+$", "", k)


# --------------------------------------------------------------------------- #
#  1.  패싯 통계 — 이 파일의 물리적 핵심
# --------------------------------------------------------------------------- #
def _sagitta(V_mm, F, adj, adj_ang, adj_edges):
    """면마다 (곡면 새그 δ [mm], 최대 꺾임각 θ [rad]).

    ⭐ **새그는 곡률 방향의 폭으로 정해진다 — 최장변이 아니다.**
    한 모서리 e 에서 표면이 θ 만큼 꺾이면 곡률은 **e 에 수직인** 방향으로 돈다. 그 방향의
    패싯 폭은 삼각형의 e 에 대한 높이 w = 2A/|e| 다. 국소 반경 R ≈ w/θ 이므로

        δ ≈ w·θ/8

    이걸 최장변으로 계산하면 **가늘고 긴 패싯에서 완전히 틀린다**: 길이 400 mm 짜리
    암 튜브를 12각형 한 마디로 만들면 최장변은 400 mm 지만 실제 새그는 원주 폭
    (≈5 mm)로 정해져 0.3 mm 밖에 안 된다. 초판이 이 실수를 했고 s1000plus 의 암을
    통째로 불량으로 찍었다 — 아래 식이 그 정정이다."""
    tri = V_mm[F]
    A = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    delta = np.zeros(len(F))
    theta = np.zeros(len(F))
    if len(adj):
        e = V_mm[adj_edges[:, 1]] - V_mm[adj_edges[:, 0]]
        Le = np.maximum(np.linalg.norm(e, axis=1), 1e-9)
        w = 0.5 * (2.0 * A[adj[:, 0]] / Le + 2.0 * A[adj[:, 1]] / Le)   # 곡률 방향 평균 폭
        d = w * adj_ang / 8.0
        np.maximum.at(delta, adj[:, 0], d)
        np.maximum.at(delta, adj[:, 1], d)
        np.maximum.at(theta, adj[:, 0], adj_ang)
        np.maximum.at(theta, adj[:, 1], adj_ang)
    return delta, theta, A


def facet_stats(V_mm: np.ndarray, F: np.ndarray, adj, adj_ang, adj_edges,
                lam_mm: float) -> dict:
    """패싯 크기 · 곡면 새그 · PO 왕복 위상오차의 **면적가중** 분포.

    s   = 패싯 최장변 [mm]  (크기 분포용. 판정 기준은 아니다 — 평면은 커도 정확하다)
    θ   = 인접면과의 꺾임각 최대 [rad]
    δ   = 곡면 새그 [mm]   (`_sagitta` 참조 — 곡률 방향 폭으로 계산한다)
    φ   = 2kδ = 왕복 위상오차 [deg]   ← PO 적분이 실제로 겪는 오차
    θ ≥ SHARP_DEG 인 면은 **진짜 모서리**로 보고 φ 통계에서 빼되 면적비를 보고한다."""
    tri = V_mm[F]
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    L = np.stack([np.linalg.norm(b - a, axis=1),
                  np.linalg.norm(c - b, axis=1),
                  np.linalg.norm(a - c, axis=1)], axis=1)
    s = L.max(axis=1)

    delta, theta, A = _sagitta(V_mm, F, adj, adj_ang, adj_edges)
    sharp = theta >= np.radians(SHARP_DEG)
    smooth = ~sharp

    k = 2.0 * np.pi / lam_mm
    phase = np.degrees(2.0 * k * delta)          # 왕복 위상오차 [deg]

    def aw(x, w, qs):
        """면적가중 분위수."""
        if not len(x) or w.sum() <= 0:
            return [None] * len(qs)
        o = np.argsort(x)
        cw = np.cumsum(w[o]) / w[o].sum()
        return [float(np.interp(q, cw, x[o])) for q in qs]

    d_ray = lam_mm / RAY_DIV
    Asum = float(A.sum())
    return dict(
        n_tris=int(len(F)), area_mm2=Asum,
        facet_mm_aw=dict(zip(("p50", "p90", "p99", "max"),
                             aw(s, A, (0.5, 0.9, 0.99, 1.0)))),
        facet_mm_count=dict(zip(("p50", "p90", "p99", "max"),
                                [float(x) for x in np.percentile(s, [50, 90, 99, 100])])),
        area_frac_below_ray_spacing=float(A[s < d_ray].sum() / Asum),
        area_frac_above_lambda_over_10=float(A[s > lam_mm / 10.0].sum() / Asum),
        area_frac_sharp_edge=float(A[sharp].sum() / Asum),
        phase_deg_aw=dict(zip(("p50", "p90", "p99", "max"),
                              aw(phase[smooth], A[smooth], (0.5, 0.9, 0.99, 1.0)))),
        area_frac_phase_over_budget=float(A[smooth][phase[smooth] > PHASE_BUDGET_DEG].sum() / Asum),
        sagitta_mm_aw=dict(zip(("p50", "p90", "p99"),
                               aw(delta[smooth], A[smooth], (0.5, 0.9, 0.99)))),
        # 그림이 그대로 그릴 수 있는 면적가중 CDF (100 점으로 다운샘플)
        cdf_facet_mm=_cdf(s, A), cdf_phase_deg=_cdf(phase[smooth], A[smooth]),
        ray_spacing_mm=float(d_ray), lambda_mm=float(lam_mm),
    )


def _hotspots(V_mm, F, G, adj, adj_ang, adj_edges, lam_mm) -> dict:
    """그룹별로 **위상 예산을 넘긴 면적**과 그 비율. 어디를 더 잘게 만들면 되는지 알려준다."""
    delta, theta, A = _sagitta(V_mm, F, adj, adj_ang, adj_edges)
    ok = theta < np.radians(SHARP_DEG)
    phase = np.degrees(2.0 * (2.0 * np.pi / lam_mm) * delta)
    bad = ok & (phase > PHASE_BUDGET_DEG)
    tot_bad = float(A[bad].sum())
    out = {}
    for g in sorted(set(G.tolist())):
        sel = (G == g)
        ab = float(A[sel & bad].sum())
        if ab <= 0:
            continue
        out[g] = dict(area_over_budget_mm2=ab,
                      frac_of_group=float(ab / A[sel].sum()),
                      frac_of_all_over_budget=float(ab / tot_bad) if tot_bad > 0 else 0.0,
                      worst_phase_deg=float(phase[sel & bad].max()))
    return dict(total_area_over_budget_mm2=tot_bad,
                frac_of_mesh=float(tot_bad / A.sum()),
                by_group=dict(sorted(out.items(),
                                     key=lambda kv: -kv[1]["area_over_budget_mm2"])))


def _plain_log_x(ax):
    """로그 x축 눈금을 **평범한 숫자**로 적는다.
    ⚠ 기본 포맷터는 `$10^{-1}$` 를 수식으로 쓰는데 나눔고딕에 유니코드 마이너스(U+2212)가
      없어서 `10^{π1}` 로 깨진다. 0.1/1/10/100 이 읽기도 더 낫다."""
    from matplotlib.ticker import FuncFormatter, NullFormatter

    def f(v, _):
        if v <= 0:
            return ""
        return f"{v:g}" if v >= 1 else f"{v:.10f}".rstrip("0").rstrip(".")
    ax.xaxis.set_major_formatter(FuncFormatter(f))
    ax.xaxis.set_minor_formatter(NullFormatter())


def _cdf(x, w, n=140):
    """면적가중 CDF 를 n 점으로 줄여 (x, F) 로 돌려준다."""
    if not len(x) or w.sum() <= 0:
        return dict(x=[], f=[])
    o = np.argsort(x)
    cw = np.cumsum(w[o]) / w[o].sum()
    q = np.linspace(0.0, 1.0, n)
    return dict(x=[float(v) for v in np.interp(q, cw, x[o])], f=[float(v) for v in q])


def _adjacency(mesh):
    """trimesh 인접면·꺾임각·공유모서리. **정점 병합이 선행돼야** 모서리가 잡힌다."""
    mesh.merge_vertices()
    return (np.asarray(mesh.face_adjacency, int),
            np.asarray(mesh.face_adjacency_angles, float),
            np.asarray(mesh.face_adjacency_edges, int))


# --------------------------------------------------------------------------- #
#  2.  공식 CAD 측정
# --------------------------------------------------------------------------- #
def _up_axis(ext: np.ndarray) -> int:
    """세 축 중 **가장 짧은** 축을 상하축으로 본다. 멀티로터에서만 성립하는 규칙이므로
    측정한 높이를 공표 높이와 대조해서 확인한다(SPEC_VS_CAD 가 그 검사다)."""
    return int(np.argmin(ext))


def _quadrant(P: np.ndarray, c=(0.0, 0.0)) -> np.ndarray:
    """평면좌표 부호로 사분면 라벨. 세 CAD 모두 모터가 사분면마다 하나인 X 배치라
    각도 반올림(45° 에서 애매해진다)보다 이쪽이 안전하다.
    ⚠ 기준점 c 는 **기체 중심**이다 — 원점이 아니다(Sentinel CAD 는 원점이 기체 밖에 있다)."""
    return ((P[:, 0] > c[0]).astype(int) * 2 + (P[:, 1] > c[1]).astype(int))


def _ring_radius(P: np.ndarray, c0) -> tuple | None:
    """사분면마다 하나씩 있는 점군의 **중심원 반경**과 그 원의 중심.
    bbox 중심 c0 에서 시작해 한 번 되풀이한다(사분면 평균들의 평균이 진짜 중심이다)."""
    if len(P) < 4:
        return None
    c = np.asarray(c0, float)
    for _ in range(2):
        q = _quadrant(P, c)
        ring = [P[q == k].mean(axis=0) for k in range(4) if (q == k).any()]
        if len(ring) != 4:
            return None
        ring = np.array(ring)
        c = ring.mean(axis=0)
    return float(np.linalg.norm(ring - c, axis=1).mean()), [float(x) for x in c]


def _hub_ring_radius(V_mm: np.ndarray, up: int, plan: list, c0) -> dict | None:
    """부품 이름이 없는 CAD(Freefly Astro)에서 **모터축 원**을 찾는다.

    모터 허브는 축 주위의 **회전체 원판**이다. 상하축을 얇은 슬랩으로 훑으면서
    사분면별 중앙값을 후보 축으로 잡고, 그 슬랩이 정말 원판인지 두 조건으로 판정한다:
      · 사분면 점의 99 % 가 후보 축에서 60 mm 안에 있다 (= 블레이드가 아니라 원판)
      · 네 사분면의 반경이 0.5 mm 이내로 일치한다 (= 4회 대칭)
    프로펠러 블레이드가 있는 슬랩은 첫 조건에서 탈락한다."""
    yy = V_mm[:, up]
    y0, y1 = float(yy.min()), float(yy.max())
    c0 = np.asarray(c0, float)
    r_plan_max = float(np.hypot(V_mm[:, plan[0]] - c0[0], V_mm[:, plan[1]] - c0[1]).max())
    hits = []
    for lo in np.arange(y0 + 0.60 * (y1 - y0), y1 - 4.0, 2.0):
        S = V_mm[(yy > lo) & (yy < lo + 4.0)][:, plan]
        if len(S) < 400:
            continue
        q = _quadrant(S, c0)
        med, frac = [], []
        for k in range(4):
            P = S[q == k]
            if len(P) < 100:
                break
            c = np.median(P, axis=0)
            med.append(c)
            frac.append(float((np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) < 60.0).mean()))
        if len(med) != 4:
            continue
        med = np.array(med)
        r = np.linalg.norm(med - med.mean(axis=0), axis=1)
        if r.std() < 0.5 and min(frac) > 0.93 and r.mean() > 0.25 * r_plan_max:
            hits.append((float(lo) + 2.0, float(r.mean()), float(min(frac))))
    if not hits:
        return None
    return dict(radius_mm=float(np.median([h[1] for h in hits])),
                n_slabs=len(hits), slab_y_mm=[h[0] for h in hits],
                slab_radius_mm=[h[1] for h in hits])


def _cad_named_dims(cid: str, scene, parts: dict) -> dict:
    """기체별 **이름 붙은 치수** — 공표값과 맞댈 수 있는 것만 잰다."""
    ext = (scene.bounds[1] - scene.bounds[0]) * 1000.0
    up = _up_axis(ext)
    plan = [i for i in range(3) if i != up]
    ctr = 0.5 * (scene.bounds[1] + scene.bounds[0]) * 1000.0
    c0 = [float(ctr[plan[0]]), float(ctr[plan[1]])]
    out = dict(overall_height_mm=float(ext[up]),
               overall_plan_mm=[float(ext[i]) for i in plan],
               up_axis=int(up), plan_centre_mm=c0)

    def centres(pat):
        """이름이 pat 에 맞는 부품들의 **인스턴스 중심** (mm, 평면 2성분)."""
        C = [p["centre_mm"] for n, p in parts.items() if re.search(pat, n)]
        return np.array([[c[plan[0]], c[plan[1]]] for c in C], float) if C else np.zeros((0, 2))

    if cid == "holybro_x500v2":
        got = _ring_radius(centres(r"^DJ-2216-KV880"), c0)   # 모터 8 인스턴스(=4기 × 2솔리드)
        if got:
            out["motor_axis_radius_mm"], out["motor_ring_centre_mm"] = got
            out["wheelbase_mm"] = 2.0 * got[0]
        bp = parts.get("BOTTOM-PLATE-X500-V5")
        if bp:
            out["plate_span_across_flats_mm"] = float(min(bp["ext_mm"][plan[0]],
                                                          bp["ext_mm"][plan[1]]))
            # 착륙장치 높이 = 하판 아랫면 → 최하점
            out["gear_height_mm"] = float(bp["min_mm"][up] - scene.bounds[0][up] * 1000.0)
    elif cid == "modalai_sentinel":
        got = _ring_radius(centres(r"^T-MOTOR"), c0)
        if got:
            out["motor_axis_radius_mm"], out["motor_ring_centre_mm"] = got
            out["motor_axis_diagonal_mm"] = 2.0 * got[0]
            out["motor_square_side_mm"] = 2.0 * got[0] / np.sqrt(2.0)
    elif cid == "freefly_astro":
        m = scene.to_mesh() if hasattr(scene, "to_mesh") else scene
        hub = _hub_ring_radius(np.asarray(m.vertices, float) * 1000.0, up, plan, c0)
        if hub:
            out["motor_axis_radius_mm"] = hub["radius_mm"]
            out["motor_axis_diagonal_mm"] = 2.0 * hub["radius_mm"]
            out["hub_detection"] = hub
    return out


def measure_cad(cid: str, verbose=True) -> dict:
    import trimesh
    spec = CAD_FILES[cid]
    path = os.path.join(REF, spec["glb"])
    t0 = time.time()
    scene = trimesh.load(path)
    geoms = getattr(scene, "geometry", {"_": scene})

    # ⚠ Scene 의 `geometry[name].vertices` 는 **부품 로컬 좌표**다. 조립 위치는 `scene.graph` 의
    #   노드 변환에 들어 있다. 이걸 안 씌우면 모든 부품이 원점에 겹쳐 보이고 모터 링 반경이
    #   0 으로 나온다(예외는 안 난다 — 그래서 여기 적어 둔다).
    parts, cat_n, cat_area = {}, collections.Counter(), collections.Counter()
    nodes = list(getattr(scene, "graph", None).nodes_geometry) if hasattr(scene, "graph") else []
    if nodes:
        items = []
        for node in nodes:
            T, gname = scene.graph[node]
            g = scene.geometry[gname]
            items.append((gname, trimesh.transform_points(np.asarray(g.vertices, float), T), g))
    else:
        items = [(k, np.asarray(g.vertices, float), g) for k, g in geoms.items()]
    for name, Vw, g in items:
        Vg = Vw * 1000.0
        tri = Vg[np.asarray(g.faces, int)]
        area = float(0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0],
                                                   tri[:, 2] - tri[:, 0]), axis=1).sum())
        parts[name] = dict(n_tris=int(len(g.faces)), area_mm2=area,
                           ext_mm=[float(x) for x in (Vg.max(0) - Vg.min(0))],
                           centre_mm=[float(x) for x in 0.5 * (Vg.max(0) + Vg.min(0))],
                           min_mm=[float(x) for x in Vg.min(0)])
        cat = _categorise(_base_name(name))
        cat_n[cat] += 1
        cat_area[cat] += area

    types = collections.Counter(_base_name(k) for k, _, _ in items)
    mesh = scene.to_mesh() if hasattr(scene, "to_mesh") else scene
    adj, ang, aed = _adjacency(mesh)
    V_mm = np.asarray(mesh.vertices, float) * 1000.0
    F = np.asarray(mesh.faces, int)

    rec = dict(
        label=spec["label"], short=spec["short"], vendor=spec["vendor"],
        licence=spec["licence"], note_ko=spec["note_ko"], maps_to=spec["maps_to"],
        file=os.path.relpath(path, ROOT), file_bytes=os.path.getsize(path),
        file_mtime=_stamp(_mtime(path)),
        n_instances=len(items), n_part_types=len(types),
        instance_counts={k: int(v) for k, v in sorted(types.items(), key=lambda kv: -kv[1])},
        category_instances={k: int(cat_n.get(k, 0)) for k in CAT_ORDER if cat_n.get(k)},
        category_area_mm2={k: float(cat_area.get(k, 0.0)) for k in CAT_ORDER if cat_area.get(k)},
        bbox_mm=[float(x) for x in (scene.bounds[1] - scene.bounds[0]) * 1000.0],
        dims=_cad_named_dims(cid, scene, parts),
        facets={b: facet_stats(V_mm, F, adj, ang, aed, C0 / f * 1000.0) for b, f in BANDS.items()},
        load_s=round(time.time() - t0, 1),
    )
    if verbose:
        d = rec["facets"]["5G"]
        print(f"  [CAD] {spec['label']:22s} {rec['n_instances']:4d} inst / "
              f"{rec['n_part_types']:3d} types · {d['n_tris']:>9,} tris · "
              f"facet aw p50 {d['facet_mm_aw']['p50']:.2f} mm · "
              f"phase p99 {d['phase_deg_aw']['p99']:.1f} deg  ({rec['load_s']}s)")
    return rec


# --------------------------------------------------------------------------- #
#  3.  우리 메쉬 측정
# --------------------------------------------------------------------------- #
def measure_ours(verbose=True) -> dict:
    import trimesh
    from drones import (DRONES, build_drone, drone_keys, drone_label, DRONE_GROUP_MAT,
                        MATERIAL_COLOR)
    from mesh_check import check_mesh

    out = {}
    for key in drone_keys():
        spec = DRONES[key]
        mm = build_drone(spec)
        V = np.asarray(mm.v, float)
        F = np.asarray(mm.f, int)
        G = np.asarray(mm.g, object)
        m = trimesh.Trimesh(vertices=V.copy(), faces=F.copy(), process=False)
        adj, ang, aed = _adjacency(m)
        # ⚠ merge_vertices 는 면 순서를 바꾸지 않는다 → G 를 그대로 쓸 수 있다.
        V_mm = np.asarray(m.vertices, float) * 1000.0
        Fm = np.asarray(m.faces, int)
        chk = check_mesh(mm, key)

        tri = V_mm[Fm]
        area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        grp_area = {g: float(area[G == g].sum()) for g in sorted(set(mm.g))}

        out[key] = dict(
            name=spec.name, label=drone_label(key),
            n_tris=int(len(Fm)),
            n_parts=int(sum(v["n_parts"] for v in chk["groups"].values())),
            n_groups=len(grp_area),
            bbox_mm=[float(x) for x in (V.max(0) - V.min(0)) * 1000.0],
            group_area_mm2=grp_area,
            group_material={g: DRONE_GROUP_MAT[g][0] for g in grp_area},
            # ⭐ 재질색은 `drones.MATERIAL_COLOR` 가 유일한 출처다 — 여기서 새 색을 만들지 않는다.
            material_color={DRONE_GROUP_MAT[g][0]: [float(c) for c in
                                                    MATERIAL_COLOR[DRONE_GROUP_MAT[g][0]]]
                            for g in grp_area},
            facets={b: facet_stats(V_mm, Fm, adj, ang, aed, C0 / f * 1000.0) for b, f in BANDS.items()},
            # ⭐ 예산 초과 면적이 **어느 그룹에** 있나 — 고칠 곳을 알려주는 유일한 숫자다.
            phase_hotspots_5g=_hotspots(V_mm, Fm, G, adj, ang, aed, C0 / BANDS["5G"] * 1000.0),
        )
        if verbose:
            d = out[key]["facets"]["5G"]
            print(f"  [ours] {key:12s} {out[key]['n_parts']:4d} parts · {d['n_tris']:>7,} tris · "
                  f"facet aw p50 {d['facet_mm_aw']['p50']:6.2f} mm · "
                  f"phase p99 {d['phase_deg_aw']['p99']:5.1f} deg · "
                  f"A(phi>{PHASE_BUDGET_DEG:.0f}) {d['area_frac_phase_over_budget']*100:5.2f} %")
    return out


# --------------------------------------------------------------------------- #
#  4.  X500 V2 치수 1:1 대조 — 우리 메쉬에서 **직접 재서** CAD·공표와 맞댄다
# --------------------------------------------------------------------------- #
def measure_our_x500_dims() -> dict:
    """우리 `x500v2` 메쉬에서 이름 붙은 치수를 뽑는다. 전부 **메쉬에서 잰 값**이고
    `drone_cad.X500V2` 표를 읽어오지 않는다 — 표의 의도가 실제 메쉬로 실현됐는지가 요점이다."""
    from drones import DRONES, build_frame, build_drone, rotor_layout
    spec = DRONES["x500v2"]
    fr = build_frame(spec)
    V = np.asarray(fr.v, float) * 1000.0
    F = np.asarray(fr.f, int)
    G = np.asarray(fr.g, object)

    def pts(groups):
        idx = np.where(np.isin(G, list(groups)))[0]
        return V[np.unique(F[idx])]

    D = {}
    deck = pts(["deck"])
    # 판 두 장의 z 준위 — 중심의 스탠드오프·마스트를 피하려고 반경 40 mm 밖만 본다.
    # ⚠ 팔각판의 꼭짓점 반경은 across-flats/2 보다 크다(87 mm) → 상한을 두면 판을 통째로 놓친다.
    rim = deck[(np.hypot(deck[:, 0], deck[:, 1]) > 40.0) & (np.abs(deck[:, 2]) < 20.0)]
    lev = np.unique(np.round(rim[:, 2], 3))
    if len(lev) >= 4:
        zb0, zb1, zt0, zt1 = lev[0], lev[1], lev[-2], lev[-1]
        D["plate_thickness_mm"] = float(zb1 - zb0)
        D["plate_gap_mm"] = float(zt0 - zb1)
        D["plate_stack_height_mm"] = float(zt1 - zb0)
        slab = deck[(deck[:, 2] > zb0 - 0.05) & (deck[:, 2] < zb1 + 0.05) &
                    (np.hypot(deck[:, 0], deck[:, 1]) < 130.0)]
        D["plate_span_across_flats_mm"] = float(max(np.ptp(slab[:, 0]), np.ptp(slab[:, 1])))
    else:
        zb0 = zt1 = 0.0

    # 모터 링 — 메쉬에서 직접(spec.diagonal 을 쓰지 않는다)
    mo = pts(["motor"])
    lab = np.round((np.arctan2(mo[:, 1], mo[:, 0]) - np.pi / 4) / (np.pi / 2)).astype(int) % 4
    ring = np.array([mo[lab == q][:, :2].mean(axis=0) for q in range(4)])
    r_mot = float(np.linalg.norm(ring, axis=1).mean())
    D["motor_axis_radius_mm"] = r_mot
    D["wheelbase_mm"] = 2.0 * r_mot
    # 모터 캔 외경 — 캔 z 구간에서 **모터축 기준** 최대 반경 ×2
    c = ring[0]
    near = mo[np.hypot(mo[:, 0] - c[0], mo[:, 1] - c[1]) < 40.0]
    can = near[near[:, 2] > near[:, 2].min() + 0.55 * np.ptp(near[:, 2])]
    if len(can):
        D["motor_bell_od_mm"] = float(2.0 * np.hypot(can[:, 0] - c[0], can[:, 1] - c[1]).max())

    # 암 튜브 — 45° 축 좌표계로 옮겨서 잰다
    A = pts(["arm"])
    u = np.array([np.cos(np.pi / 4), np.sin(np.pi / 4)])
    alo = A[:, 0] * u[0] + A[:, 1] * u[1]
    lat = -A[:, 0] * u[1] + A[:, 1] * u[0]
    # ⚠ lat 은 **직선**까지의 거리라 반대편 암(−135°)도 함께 걸린다 → alo>0 으로 한쪽만 본다.
    tube = A[(np.abs(lat) < 9.0) & (np.abs(A[:, 2]) > 6.5) & (alo > 0.0)]
    if len(tube):
        t_alo = tube[:, 0] * u[0] + tube[:, 1] * u[1]
        D["arm_tube_length_mm"] = float(t_alo.max() - t_alo.min())
    mid = A[(np.abs(lat) < 12.0) & (alo > 100.0) & (alo < 180.0)]
    if len(mid):
        D["arm_tube_od_mm"] = float(max(np.ptp(mid[:, 2]),
                                        np.ptp(-mid[:, 0] * u[1] + mid[:, 1] * u[0])))

    # 착륙장치 — 스키드는 x 축을 따르는 회전체다
    gr = pts(["gear", "gear_cf", "accent"])
    z_low = float(np.concatenate([gr[:, 2], V[:, 2]]).min())
    D["gear_height_mm"] = float(zb0 - z_low)
    D["overall_height_frame_only_mm"] = float(zt1 - z_low)
    sk = gr[gr[:, 2] < z_low + 20.0]
    if len(sk):
        pos = sk[sk[:, 1] > 0]
        D["skid_track_mm"] = float(2.0 * 0.5 * (pos[:, 1].min() + pos[:, 1].max()))
        D["skid_tube_length_mm"] = float(np.ptp(sk[:, 0]))
        D["skid_foam_sleeve_od_mm"] = float(np.ptp(sk[:, 2]))

    # 페이로드 레일 + GPS 마스트 (둘 다 carbon = 'deck' 그룹)
    rail = deck[(deck[:, 2] < -24.0) & (deck[:, 2] > -36.0) &
                (np.abs(deck[:, 1]) > 20.0) & (np.abs(deck[:, 1]) < 40.0)]
    if len(rail):
        pos = rail[rail[:, 1] > 0]
        D["payload_rail_track_mm"] = float(2.0 * 0.5 * (pos[:, 1].min() + pos[:, 1].max()))
        D["payload_rail_length_mm"] = float(np.ptp(rail[:, 0]))
    D["gps_mast_top_above_plate_mm"] = float(deck[:, 2].max() - zt1)
    D["overall_height_with_gps_mast_mm"] = float(deck[:, 2].max() - z_low)

    # 프로펠러 — 전체 드론에서 로터 중심 기준 팁 반경 ×2
    full = build_drone(spec)
    Vf = np.asarray(full.v, float) * 1000.0
    Ff = np.asarray(full.f, int)
    Gf = np.asarray(full.g, object)
    pv = Vf[np.unique(Ff[np.where(Gf == "prop")[0]])]
    ctr = np.array(rotor_layout(spec)[0]["center"]) * 1000.0
    d = np.hypot(pv[:, 0] - ctr[0], pv[:, 1] - ctr[1])
    D["prop_dia_mm"] = float(2.0 * d[d < 200.0].max())
    D["prop_ring_radius_mm"] = float(np.hypot(ctr[0], ctr[1]))
    return D


#: 우리 측정 이름 → (표시명, x500v2_cad.json 키, DroneSpec 에서 공표값을 뽑는 함수)
#:   공표값은 **손으로 적지 않고** DroneSpec 필드에서 꺼낸다(그 필드가 저장소의 공표값 원장이다).
X500_MATCH = (
    ("wheelbase_mm", "Wheelbase (motor-to-motor)", "wheelbase_mm",
     lambda s: float(s.diagonal_mm)),
    ("motor_axis_radius_mm", "Motor axis radius", "motor_axis_radius_mm",
     lambda s: float(s.diagonal_mm) / 2.0),
    # ⭐ 프롭이 앉는 반경은 `rotor_layout` 이 정하고 모터 캔은 `drone_cad.X500V2` 가 정한다 —
    #    두 값이 다르면 프롭이 자기 모터 위에 정확히 앉지 않는다. 그래서 따로 잰다.
    ("prop_ring_radius_mm", "Propeller ring radius", "motor_axis_radius_mm",
     lambda s: float(s.diagonal_mm) / 2.0),
    ("plate_span_across_flats_mm", "Plate width across flats", "plate_span_across_flats_mm",
     lambda s: float(s.plate_mm[0])),
    ("plate_thickness_mm", "Plate thickness", "plate_thickness_mm",
     lambda s: float(s.plate_mm[2])),
    ("plate_gap_mm", "Plate gap", "plate_gap_mm",
     lambda s: float(s.plate_mm[3])),
    ("plate_stack_height_mm", "Plate stack height", "plate_stack_height_mm",
     lambda s: float(s.plate_mm[2] + s.plate_mm[3] + s.plate_mm[4])),
    ("arm_tube_od_mm", "Arm tube OD", "arm_tube_od_mm",
     lambda s: float(s.arm_od_mm)),
    ("arm_tube_length_mm", "Arm tube length", "arm_tube_length_mm", None),
    ("motor_bell_od_mm", "Motor can OD", "motor_bell_od_mm", None),
    ("gear_height_mm", "Landing gear height", "gear_height_mm",
     lambda s: float(s.gear_h_mm)),
    ("skid_track_mm", "Skid track", "skid_track_mm", None),
    ("skid_tube_length_mm", "Skid tube length", "skid_tube_length_mm", None),
    ("skid_foam_sleeve_od_mm", "Skid foam sleeve OD", "skid_foam_sleeve_od_mm", None),
    ("payload_rail_track_mm", "Payload rail track", "payload_rail_track_mm", None),
    ("payload_rail_length_mm", "Payload rail length", "payload_rail_length_mm", None),
    ("gps_mast_top_above_plate_mm", "GPS mast above top plate", "gps_mast_top_above_plate_mm", None),
    ("overall_height_frame_only_mm", "Overall height (frame)", "overall_height_frame_only_mm", None),
    ("overall_height_with_gps_mast_mm", "Overall height (with mast)",
     "overall_height_with_gps_mast_mm", None),
    ("prop_dia_mm", "Propeller diameter", None,
     lambda s: float(s.prop_dia_mm)),
)


def build_x500_table(ours: dict) -> list:
    from drones import DRONES
    spec = DRONES["x500v2"]
    cad = _load_json(X500_CAD_JSON) or {}
    rows = []
    for key, label, cad_key, pub in X500_MATCH:
        o = ours.get(key)
        cv = None
        if cad_key and cad_key in cad:
            v = cad[cad_key]["value"]
            cv = float(v) if not isinstance(v, list) else None
        pv = pub(spec) if pub else None
        r = dict(key=key, label=label, ours_mm=o, cad_mm=cv, published_mm=pv,
                 cad_source=("outputs/x500v2_cad.json:" + cad_key) if cad_key else None,
                 published_source="src/drones.py DroneSpec('x500v2')" if pub else None)
        if o is not None and cv:
            r["d_cad_mm"] = o - cv
            r["d_cad_pct"] = 100.0 * (o - cv) / cv
        if o is not None and pv:
            r["d_pub_mm"] = o - pv
            r["d_pub_pct"] = 100.0 * (o - pv) / pv
        rows.append(r)
    return rows


# --------------------------------------------------------------------------- #
#  5.  원장
# --------------------------------------------------------------------------- #
def measure(verbose=True) -> dict:
    os.makedirs(FIG, exist_ok=True)
    t0 = time.time()
    from rcs_sbr import DEFAULT_DIV
    if int(DEFAULT_DIV) != RAY_DIV:
        raise ValueError(f"광선 격자 분모가 어긋났다: rcs_sbr.DEFAULT_DIV={DEFAULT_DIV} vs "
                         f"viz_cad_compare.RAY_DIV={RAY_DIV}. 패싯 판정 기준이 통째로 바뀌므로 "
                         f"여기서 막는다 — 둘을 맞추고 다시 실행할 것.")
    if verbose:
        print("■ 공식 CAD 측정")
    cad = {cid: measure_cad(cid, verbose) for cid in CAD_FILES}
    if verbose:
        print("■ 우리 메쉬 측정")
    ours = measure_ours(verbose)
    if verbose:
        print("■ X500 V2 치수 대조")
    x500_ours = measure_our_x500_dims()
    table = build_x500_table(x500_ours)

    x500_json = _load_json(X500_CAD_JSON) or {}
    svc = []
    for e in SPEC_VS_CAD:
        glb = cad[e["cad"]]["dims"].get(e["cad_key"])
        jv = (x500_json.get(e["json_key"]) or {}).get("value") if e["json_key"] else None
        cv = float(jv) if isinstance(jv, (int, float)) else (float(glb) if glb is not None else None)
        if cv is None:
            continue
        svc.append(dict(cad=e["cad"], aircraft=CAD_FILES[e["cad"]]["short"], dim=e["dim"],
                        published_mm=e["published_mm"], cad_mm=cv,
                        cad_method=("outputs/x500v2_cad.json (STEP cylinder axes)"
                                    if jv is not None else "this script, from the vendor GLB"),
                        cad_glb_crosscheck_mm=(float(glb) if glb is not None else None),
                        d_mm=float(cv - e["published_mm"]),
                        d_pct=100.0 * (cv - e["published_mm"]) / e["published_mm"],
                        caveat=e["caveat"], source=e["source"]))

    J = dict(
        meta=dict(
            stamp=_stamp(time.time()),
            generator="src/viz_cad_compare.py",
            elapsed_s=round(time.time() - t0, 1),
            fc_ref_hz=FC_REF, lambda_ref_mm=C0 / FC_REF * 1000.0,
            ray_spacing_mm=C0 / FC_REF * 1000.0 / RAY_DIV, ray_div=RAY_DIV,
            sharp_edge_deg=SHARP_DEG, phase_budget_deg=PHASE_BUDGET_DEG,
            mesh_sources={p: _stamp(_mtime(os.path.join(ROOT, p))) for p in MESH_SOURCES},
            licence_note=("Manufacturer CAD (Holybro / ModalAI / Freefly) states no licence. "
                          "Measured for dimension comparison only. Their geometry is NOT copied "
                          "into our assets and their meshes are NOT rendered in our reports."),
            method_ko=("PO 적분은 패싯이 아니라 λ/12 광선 격자에서 일어난다 → 패싯 크기 자체가 "
                       "아니라 (a) 곡면 새그 δ≈s·θ/8 이 만드는 왕복 위상 2kδ 와 (b) 광선 간격 "
                       "아래로 내려간 디테일 비율이 판정 기준이다."),
        ),
        bands={b: dict(fc_hz=f, lambda_mm=C0 / f * 1000.0) for b, f in BANDS.items()},
        official_cad=cad,
        ours=ours,
        x500v2_dimensions=dict(
            ours_measured_mm=x500_ours,
            rows=table,
            note_ko=("⚠ 우리 x500v2 메쉬는 **이 CAD 에서 뽑은 표**(drone_cad.X500V2)로 지어졌다. "
                     "따라서 이 표의 CAD 열과의 일치는 독립 검증이 아니라 **설계 의도가 메쉬로 "
                     "실현됐는지**의 검사다. 독립적인 것은 공표(published) 열과의 차이와, "
                     "아래 구조·패싯 비교다."),
        ),
        spec_vs_cad=svc,
    )
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    if verbose:
        print(f"→ {os.path.relpath(LEDGER, ROOT)}  ({time.time() - t0:.1f}s)")
    return J


# --------------------------------------------------------------------------- #
#  6.  그림
# --------------------------------------------------------------------------- #
def _fmt(v, nd=2):
    return "—" if v is None else f"{v:,.{nd}f}"


def fig_dimensions(J: dict, outdir=FIG):
    """치수: 우리 메쉬 vs 제조사 CAD vs 공표 제원."""
    rows = [r for r in J["x500v2_dimensions"]["rows"] if r["ours_mm"] is not None]
    n = len(rows)
    h_top = 0.40 * n                       # 표 높이 [inch]
    h_bot, pad_t, pad_gap, pad_b = 2.05, 1.72, 1.05, 1.42
    H = pad_t + h_top + pad_gap + h_bot + pad_b
    fig = plt.figure(figsize=(15.2, H))

    def rect(x0, w, y_top_in, h_in):
        return [x0, 1.0 - (y_top_in + h_in) / H, w, h_in / H]

    # ---- (a) 절대값 표 -----------------------------------------------------
    ax = fig.add_axes(rect(0.006, 0.515, pad_t, h_top)); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, n + 1.6)
    cols = (0.015, 0.505, 0.655, 0.805, 0.955)
    hdr = ("Dimension", "ours [mm]", "official CAD", "published")
    for x, h, ha in zip(cols, hdr, ("left", "right", "right", "right")):
        ax.text(x, n + 0.62, h, ha=ha, va="center", fontsize=10.2, color=INK, fontweight="bold")
    ax.plot([0.01, 0.97], [n + 0.25] * 2, color=INK, lw=1.1)
    for i, r in enumerate(rows):
        y = n - 1 - i
        if i % 2 == 0:
            ax.axhspan(y - 0.5, y + 0.5, color="#f4f4f1", lw=0)
        ax.text(cols[0], y, r["label"], ha="left", va="center", fontsize=9.6, color=INK)
        ax.text(cols[1], y, _fmt(r["ours_mm"]), ha="right", va="center", fontsize=9.6, color=INK)
        ax.text(cols[2], y, _fmt(r["cad_mm"]), ha="right", va="center", fontsize=9.6,
                color=INK2 if r["cad_mm"] is not None else MUTED)
        ax.text(cols[3], y, _fmt(r["published_mm"], 1), ha="right", va="center", fontsize=9.6,
                color=INK2 if r["published_mm"] is not None else MUTED)
    ax.set_title("(a)  Holybro X500 V2 — matched dimensions", fontsize=11.6,
                 color=INK, loc="left", pad=9)

    # ---- (b) Δ% 도트 플롯 --------------------------------------------------
    ax = fig.add_axes(rect(0.575, 0.408, pad_t, h_top))
    lim = 0.0
    for r in rows:
        for k in ("d_cad_pct", "d_pub_pct"):
            if r.get(k) is not None:
                lim = max(lim, abs(r[k]))
    lim = float(np.clip(lim * 1.55, 1.35, 30.0))   # ±1 % 띠가 **띠로 보이도록** 여유를 둔다
    ax.axvspan(-1, 1, color="#eef4fb", lw=0, zorder=0)
    ax.axvline(0, color=INK, lw=1.2, zorder=3)
    for i, r in enumerate(rows):
        y = n - 1 - i
        if i % 2 == 0:
            ax.axhspan(y - 0.5, y + 0.5, color="#f4f4f1", lw=0, zorder=0)
        dc, dp = r.get("d_cad_pct"), r.get("d_pub_pct")
        if dc is not None and dp is not None and abs(dc - dp) > 1e-9:
            ax.plot([np.clip(dc, -lim, lim), np.clip(dp, -lim, lim)], [y, y],
                    color=GRID, lw=1.6, zorder=2, solid_capstyle="round")
        if dp is not None:
            ax.plot([np.clip(dp, -lim, lim)], [y], marker="s", ms=7.5, mfc="white",
                    mec=SERIES[1], mew=2.0, zorder=5)
        if dc is not None:
            ax.plot([np.clip(dc, -lim, lim)], [y], marker="o", ms=8.0,
                    color=SERIES[0], zorder=6)
        big = max([abs(v) for v in (dc, dp) if v is not None] or [0.0])
        if big > 1.0:
            v = dc if (dc is not None and abs(dc) >= abs(dp or 0)) else dp
            ax.annotate(f"{v:+.1f} %", (np.clip(v, -lim, lim), y),
                        textcoords="offset points", xytext=(11 if v > 0 else -11, 0),
                        ha="left" if v > 0 else "right", va="center",
                        fontsize=8.6, color=INK2)
    ax.set_xlim(-lim, lim); ax.set_ylim(-0.5, n + 1.6)
    ax.set_yticks([]); ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_xlabel("our mesh minus reference  [%]", fontsize=10, color=INK2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=8, color=SERIES[0],
                              label="vs official CAD"),
                       Line2D([], [], marker="s", ls="", ms=7.5, mfc="white", mec=SERIES[1],
                              mew=2.0, label="vs published spec")],
              loc="lower center", bbox_to_anchor=(0.5, 1.004), ncol=2, frameon=False,
              fontsize=9.4, labelcolor=INK2, handletextpad=0.35, columnspacing=1.6)
    ax.set_title("(b)  deviation of our mesh   (shaded band = $\\pm$1 %)", fontsize=11.6,
                 color=INK, loc="left", pad=26)

    # ---- (c) 제조사 공표값 vs 제조사 자신의 CAD ---------------------------
    ax = fig.add_axes(rect(0.068, 0.917, pad_t + h_top + pad_gap, h_bot))
    svc = J["spec_vs_cad"]
    xs = np.arange(len(svc))
    vals = [e["d_pct"] for e in svc]
    cols_ = [STATUS["good"] if abs(v) <= 1.0 else (STATUS["warning"] if abs(v) <= 5.0
             else STATUS["critical"]) for v in vals]
    # ⚠ 막대로 그리면 ±0.13 % 가 **선 하나로 사라진다** — 값이 작다는 사실은 보이되 마크는
    #   보여야 하므로 롤리팝(줄기+점)으로 그린다.
    for x, v, c in zip(xs, vals, cols_):
        ax.plot([x, x], [0.0, v], color=c, lw=3.4, solid_capstyle="round", zorder=3)
        ax.plot([x], [v], marker="o", ms=10.5, color=c, zorder=4)
    ax.axhline(0, color=INK, lw=1.1, zorder=2)
    for x, e, v in zip(xs, svc, vals):
        ax.annotate(f"{v:+.2f} %\n{e['cad_mm']:,.1f} vs {e['published_mm']:,.0f} mm",
                    (x, v), textcoords="offset points",
                    xytext=(0, 12 if v >= 0 else -12), ha="center",
                    va="bottom" if v >= 0 else "top", fontsize=8.8, color=INK2)
    marks = {i: "$^{\\dagger}$" for i, e in enumerate(svc) if e.get("caveat")}
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{e['aircraft']}\n{e['dim']}{marks.get(i, '')}"
                        for i, e in enumerate(svc)], fontsize=9, color=INK2)
    ax.set_ylabel("manufacturer CAD minus\nits own published spec  [%]", fontsize=9.6, color=INK2)
    m = max(abs(v) for v in vals) if vals else 1.0
    ax.set_ylim(-2.2 * m, 2.2 * m)
    ax.tick_params(colors=MUTED, labelsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("(c)  how far a manufacturer's own CAD sits from its own published spec "
                 "— the accuracy floor any spec-driven mesh inherits",
                 fontsize=11.6, color=INK, loc="left", pad=9)

    fig.text(0.006, 1.0 - 0.40 / H, "Our parametric meshes against manufacturer CAD — dimensions",
             fontsize=15.0, color=INK, ha="left", va="center")
    fig.text(0.006, 1.0 - 0.76 / H,
             "Our x500v2 mesh is built from a table extracted from this same CAD, so the "
             "'official CAD' column is a build-fidelity check, not independent validation. "
             "The independent numbers are the published-spec column and panel (c).",
             fontsize=9.6, color=MUTED, ha="left", va="center")
    foot = "\n".join(f"$^{{\\dagger}}$ {e['aircraft']} {e['dim'].replace(chr(10), ' ')}: "
                     f"{e['caveat']}" for e in svc if e.get("caveat"))
    fig.text(0.068, 0.42 / H, foot, fontsize=8.6, color=MUTED, ha="left", va="center",
             style="italic", linespacing=1.5)
    fig.text(0.985, 0.10 / H,
             "CAD measured for comparison only; manufacturer geometry is not redistributed.",
             fontsize=8.2, color=MUTED, ha="right", va="center")
    p = os.path.join(outdir, "cad_compare_dimensions.png")
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print(f"  → {os.path.relpath(p, ROOT)}")
    return p


def fig_facets(J: dict, outdir=FIG):
    """패싯 크기·PO 위상오차 — 우리 7종 vs 공식 CAD 3건."""
    keys = list(J["ours"])
    lam = J["meta"]["lambda_ref_mm"]
    d_ray = J["meta"]["ray_spacing_mm"]
    colour = {k: SERIES[i % len(SERIES)] for i, k in enumerate(keys)}
    cad_ls = {"holybro_x500v2": "-", "modalai_sentinel": "--", "freefly_astro": ":"}

    fig, axes = plt.subplots(1, 3, figsize=(16.4, 7.1))
    fig.subplots_adjust(left=0.048, right=0.995, top=0.735, bottom=0.098, wspace=0.245)

    # ---- (a) 패싯 크기 CDF --------------------------------------------------
    ax = axes[0]
    for k in keys:
        c = J["ours"][k]["facets"]["5G"]["cdf_facet_mm"]
        ax.plot(np.maximum(c["x"], 1e-3), np.array(c["f"]) * 100.0,
                color=colour[k], lw=2.0, zorder=4)
    for cid, rec in J["official_cad"].items():
        c = rec["facets"]["5G"]["cdf_facet_mm"]
        ax.plot(np.maximum(c["x"], 1e-3), np.array(c["f"]) * 100.0,
                color=CAD_GREY, lw=2.6, ls=cad_ls[cid], zorder=5)
    #  세로 기준선 — λ/12 와 λ/10 은 x 로 20 % 밖에 안 떨어져서 라벨을 **y 로** 엇갈리게 둔다.
    for x, lab, yy in ((d_ray, f"ray grid $\\lambda/{RAY_DIV}$ = %.1f mm" % d_ray, 0.985),
                       (lam / 10.0, "$\\lambda/10$", 0.55),
                       (lam, "$\\lambda$ = %.0f mm" % lam, 0.985)):
        ax.axvline(x, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=2)
        ax.text(x, yy, " " + lab, rotation=90, fontsize=8.8, color=INK2,
                ha="left", va="top", transform=ax.get_xaxis_transform(),
                bbox=dict(fc="white", ec="none", pad=1.4), zorder=6)
    ax.set_xscale("log"); ax.set_xlim(0.05, 600); ax.set_ylim(0, 100)
    _plain_log_x(ax)
    ax.set_xlabel("facet size (longest edge)  [mm]", fontsize=10, color=INK2)
    ax.set_ylabel("share of surface area at or below  [%]", fontsize=10, color=INK2)
    ax.set_title("(a)  facet size — area-weighted", fontsize=11.6, color=INK, loc="left", pad=8)

    # ---- (b) PO 위상오차 CDF ----------------------------------------------
    ax = axes[1]
    for k in keys:
        c = J["ours"][k]["facets"]["5G"]["cdf_phase_deg"]
        ax.plot(np.maximum(c["x"], 1e-3), np.array(c["f"]) * 100.0,
                color=colour[k], lw=2.0, zorder=4)
    for cid, rec in J["official_cad"].items():
        c = rec["facets"]["5G"]["cdf_phase_deg"]
        ax.plot(np.maximum(c["x"], 1e-3), np.array(c["f"]) * 100.0,
                color=CAD_GREY, lw=2.6, ls=cad_ls[cid], zorder=5)
    ax.axvline(PHASE_BUDGET_DEG, color=STATUS["critical"], lw=1.3, ls=(0, (4, 3)), zorder=3)
    ax.text(PHASE_BUDGET_DEG, 0.985,
            f"  budget {PHASE_BUDGET_DEG:.0f}$^\\circ$ = $\\lambda/16$ path",
            rotation=90, fontsize=8.8, color=STATUS["critical"], ha="left", va="top",
            transform=ax.get_xaxis_transform(),
            bbox=dict(fc="white", ec="none", pad=1.4), zorder=6)
    ax.set_xscale("log"); ax.set_xlim(0.01, 200); ax.set_ylim(0, 100)
    _plain_log_x(ax)
    ax.set_xlabel("round-trip phase error $2k\\delta$ on smooth surfaces  [deg]",
                  fontsize=10, color=INK2)
    ax.set_ylabel("share of smooth-surface area at or below  [%]", fontsize=10, color=INK2)
    ax.set_title("(b)  what facetting actually costs the PO integral",
                 fontsize=11.6, color=INK, loc="left", pad=8)

    # ---- (c) 위상오차 p99 + 예산 초과 면적 ---------------------------------
    ax = axes[2]
    items = [(J["ours"][k]["label"].split(" (")[0], colour[k],
              J["ours"][k]["facets"]["5G"]["phase_deg_aw"]["p99"],
              J["ours"][k]["facets"]["5G"]["area_frac_phase_over_budget"] * 100.0)
             for k in keys]
    items += [(J["official_cad"][c]["short"] + "  (CAD)", CAD_GREY,
               J["official_cad"][c]["facets"]["5G"]["phase_deg_aw"]["p99"],
               J["official_cad"][c]["facets"]["5G"]["area_frac_phase_over_budget"] * 100.0)
              for c in J["official_cad"]]
    items.sort(key=lambda t: t[2])
    y = np.arange(len(items))
    ax.barh(y, [t[2] for t in items], color=[t[1] for t in items], height=0.62, zorder=3)
    xmax = max(PHASE_BUDGET_DEG * 1.42, max(t[2] for t in items) * 1.55)
    for yy, t in zip(y, items):
        ax.text(t[2] + xmax * 0.015, yy,
                f"{t[2]:.1f}$^\\circ$   ({t[3]:.2f} % over)", va="center",
                fontsize=8.8, color=INK2)
    ax.axvline(PHASE_BUDGET_DEG, color=STATUS["critical"], lw=1.3, ls=(0, (4, 3)), zorder=4)
    ax.text(PHASE_BUDGET_DEG, 1.012, f"budget {PHASE_BUDGET_DEG:.0f}$^\\circ$",
            fontsize=8.8, color=STATUS["critical"], ha="center", va="bottom",
            transform=ax.get_xaxis_transform(), zorder=6)
    ax.set_yticks(y); ax.set_yticklabels([t[0] for t in items], fontsize=9.4, color=INK2)
    ax.set_xlabel("99th-percentile phase error $2k\\delta$  [deg]", fontsize=10, color=INK2)
    ax.set_xlim(0, xmax)
    ax.set_title("(c)  worst-case facetting cost at 3.5 GHz",
                 fontsize=11.6, color=INK, loc="left", pad=8)

    for ax in axes:
        ax.tick_params(colors=MUTED, labelsize=9)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.grid(color=GRID, lw=0.7, zorder=0)
        ax.set_axisbelow(True)

    handles = [Line2D([], [], color=colour[k], lw=2.0,
                      label=J["ours"][k]["label"].split(" (")[0]) for k in keys]
    handles += [Line2D([], [], color=CAD_GREY, lw=2.6, ls=cad_ls[c],
                       label=J["official_cad"][c]["short"] + "  (official CAD)")
                for c in J["official_cad"]]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.048, 0.845), ncol=5,
               frameon=False, fontsize=9.4, labelcolor=INK2,
               handletextpad=0.5, columnspacing=1.5)

    fig.text(0.008, 0.975, "Is our facetting good enough for the PO integral?",
             fontsize=15.0, color=INK, ha="left", va="top")
    fig.text(0.008, 0.938,
             "The PO integral samples a $\\lambda/12$ ray grid, not the facets — so a large facet on a "
             "flat panel costs nothing, and detail below the ray spacing buys nothing.\nWhat costs is "
             "sagitta on curved surfaces: $\\delta \\approx w\\theta/8$, with $\\theta$ the turn "
             "between adjacent facets and $w$ the facet width across that turn, giving round-trip "
             "phase $2k\\delta$.",
             fontsize=9.6, color=MUTED, ha="left", va="top", linespacing=1.5)
    p = os.path.join(outdir, "cad_compare_facets.png")
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print(f"  → {os.path.relpath(p, ROOT)}")
    return p


def fig_structure(J: dict, outdir=FIG):
    """구조: 부품 수, 범주별 인스턴스·면적 점유, 우리 재질 그룹, 광선 격자 아래 디테일."""
    keys = list(J["ours"])
    cad_ids = list(J["official_cad"])
    cat_col = {c: SERIES[i % len(SERIES)] for i, c in enumerate(CAT_ORDER[:-1])}
    cat_col["other"] = MUTED
    short = {k: J["ours"][k]["label"].split(" (")[0] for k in keys}

    W = 16.4
    pad_t, h_row, pad_leg, pad_mid, pad_b = 1.40, 2.40, 0.72, 0.62, 0.55
    H = pad_t + h_row + pad_leg + pad_mid + h_row + pad_leg + pad_b
    fig = plt.figure(figsize=(W, H))

    def rect(x0, w, y_top_in, h_in):
        return [x0, 1.0 - (y_top_in + h_in) / H, w, h_in / H]

    row1, row2 = pad_t, pad_t + h_row + pad_leg + pad_mid
    LX, LW, RX, RW = 0.072, 0.355, 0.545, 0.435

    # ---- (a) 부품 수 --------------------------------------------------------
    ax = fig.add_axes(rect(LX, LW, row1, h_row))
    lab, npart, col = [], [], []
    for k in keys:
        lab.append(short[k]); npart.append(J["ours"][k]["n_parts"])
        col.append(SERIES[keys.index(k) % len(SERIES)])
    for c in cad_ids:
        lab.append(J["official_cad"][c]["short"] + "  (CAD)")
        npart.append(J["official_cad"][c]["n_instances"])
        col.append(CAD_GREY)
    y = np.arange(len(lab))[::-1]
    ax.barh(y, npart, height=0.6, color=col, zorder=3)
    for yy, v in zip(y, npart):
        ax.text(v * 1.10, yy, f"{v:,}", va="center", fontsize=9, color=INK2)
    ax.set_xscale("log"); ax.set_xlim(1, 1400)
    _plain_log_x(ax)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9.2, color=INK2)
    ax.set_ylim(-0.7, len(lab) - 0.3)
    ax.set_xlabel("separate solid parts in the mesh  (log)", fontsize=10, color=INK2)
    ax.set_title("(a)  how many parts", fontsize=11.6, color=INK, loc="left", pad=8)

    # ---- (b) 범주별 인스턴스 / 면적 -----------------------------------------
    #  ⚠ Astro 는 부품이 1개(이름 없는 셸)라 범주 막대가 100 % other 로만 나온다 →
    #     막대 두 줄을 낭비하지 말고 글로 적는다.
    ax = fig.add_axes(rect(RX, RW, row1, h_row))
    bars, blabels = [], []
    for c in cad_ids:
        rec = J["official_cad"][c]
        if rec["n_part_types"] <= 1 or not rec["category_instances"]:
            continue
        bars.append(rec["category_instances"]); blabels.append(f"{rec['short']}\ninstances")
        bars.append(rec["category_area_mm2"]); blabels.append(f"{rec['short']}\nsurface area")
    y = np.arange(len(bars))[::-1]
    used = []
    for yy, d in zip(y, bars):
        tot = sum(d.values()) or 1.0
        x0 = 0.0
        for cat in CAT_ORDER:
            v = d.get(cat)
            if not v:
                continue
            used.append(cat)
            w = 100.0 * v / tot
            ax.barh(yy, w, left=x0, height=0.56, color=cat_col[cat], zorder=3,
                    edgecolor="white", lw=1.4)
            if w > 6.5:
                ax.text(x0 + w / 2.0, yy, f"{w:.0f}", ha="center", va="center",
                        fontsize=8.6, color="white", fontweight="bold")
            x0 += w
    ax.set_yticks(y); ax.set_yticklabels(blabels, fontsize=9.0, color=INK2)
    ax.set_ylim(-0.8, len(bars) - 0.2)
    ax.set_xlim(0, 100); ax.set_xlabel("share  [%]", fontsize=10, color=INK2)
    ax.set_title("(b)  what a real CAD is made of — and what it spends its surface on",
                 fontsize=11.6, color=INK, loc="left", pad=8)
    astro = [J["official_cad"][c]["short"] for c in cad_ids
             if J["official_cad"][c]["n_part_types"] <= 1]
    seen = [c for c in CAT_ORDER if c in used]
    ax.legend(handles=[Line2D([], [], marker="s", ls="", ms=9, color=cat_col[c], label=c)
                       for c in seen],
              loc="upper left", bbox_to_anchor=(0.0, -0.235), ncol=4, frameon=False,
              fontsize=9.0, labelcolor=INK2, handletextpad=0.3, columnspacing=1.3)

    # ---- (c) 우리 재질 그룹 면적 점유 --------------------------------------
    ax = fig.add_axes(rect(LX, LW, row2, h_row))
    mats = sorted({m for k in keys for m in J["ours"][k]["group_material"].values()})
    #  ⭐ 색은 `drones.MATERIAL_COLOR` 그대로. ⚠ plastic 과 prop_plastic 은 **같은 회색**이다
    #     (같은 재질, 얇은 날개라 |Γ| 만 다르다) → 색만으로는 못 가르므로 프롭에 해치를 준다.
    mcol = {}
    for k in keys:
        mcol.update({m: tuple(c) for m, c in J["ours"][k]["material_color"].items()})
    mhatch = {m: ("///" if m == "prop_plastic" else None) for m in mats}

    def _ink_on(rgb):
        return "white" if (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) < 0.55 else INK

    y = np.arange(len(keys))[::-1]
    for yy, k in zip(y, keys):
        rec = J["ours"][k]
        agg = collections.Counter()
        for g, a in rec["group_area_mm2"].items():
            agg[rec["group_material"][g]] += a
        tot = sum(agg.values()) or 1.0
        x0 = 0.0
        for m in mats:
            v = agg.get(m, 0.0)
            if v <= 0:
                continue
            w = 100.0 * v / tot
            ax.barh(yy, w, left=x0, height=0.6, color=mcol[m], zorder=3,
                    edgecolor="white", lw=1.4, hatch=mhatch[m])
            if w > 9.0:
                ax.text(x0 + w / 2.0, yy, f"{w:.0f}", ha="center", va="center",
                        fontsize=8.4, color=_ink_on(mcol[m]), fontweight="bold", zorder=5)
            x0 += w
    ax.set_yticks(y); ax.set_yticklabels([short[k] for k in keys], fontsize=9.2, color=INK2)
    ax.set_ylim(-0.7, len(keys) - 0.3)
    ax.set_xlim(0, 100); ax.set_xlabel("share of surface area  [%]", fontsize=10, color=INK2)
    ax.set_title("(c)  our meshes by PO material group   (colours = drones.MATERIAL_COLOR)",
                 fontsize=11.6, color=INK, loc="left", pad=8)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, fc=mcol[m], ec=MUTED, lw=0.7,
                                     hatch=mhatch[m], label=m) for m in mats],
              loc="upper left", bbox_to_anchor=(0.0, -0.235), ncol=4, frameon=False,
              fontsize=9.0, labelcolor=INK2, handletextpad=0.5, columnspacing=1.3,
              handlelength=1.5, handleheight=1.1)

    # ---- (d) 광선 격자 아래 디테일 ------------------------------------------
    ax = fig.add_axes(rect(RX, RW, row2, h_row))
    items = [(short[k], SERIES[keys.index(k) % len(SERIES)],
              J["ours"][k]["facets"]["5G"]["area_frac_below_ray_spacing"] * 100.0) for k in keys]
    items += [(J["official_cad"][c]["short"] + "  (CAD)", CAD_GREY,
               J["official_cad"][c]["facets"]["5G"]["area_frac_below_ray_spacing"] * 100.0)
              for c in cad_ids]
    items.sort(key=lambda t: t[2])
    y = np.arange(len(items))
    ax.barh(y, [t[2] for t in items], color=[t[1] for t in items], height=0.6, zorder=3)
    for yy, t in zip(y, items):
        ax.text(t[2] + 1.1, yy, f"{t[2]:.0f} %", va="center", fontsize=9, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([t[0] for t in items], fontsize=9.2, color=INK2)
    ax.set_ylim(-0.7, len(items) - 0.3)
    ax.set_xlim(0, 100)
    ax.set_xlabel(f"surface area on facets smaller than the ray grid "
                  f"({J['meta']['ray_spacing_mm']:.2f} mm)  [%]", fontsize=10, color=INK2)
    ax.set_title("(d)  detail the PO ray grid cannot resolve", fontsize=11.6,
                 color=INK, loc="left", pad=8)

    for ax in fig.axes:
        ax.tick_params(colors=MUTED, labelsize=9)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
        ax.set_axisbelow(True)

    fig.text(0.008, 1.0 - 0.34 / H, "Structure, not just size — our meshes against manufacturer CAD",
             fontsize=15.0, color=INK, ha="left", va="center")
    x5 = J["official_cad"]["holybro_x500v2"]
    fst = x5["category_instances"].get("fastener", 0)
    fig.text(0.008, 1.0 - 0.70 / H,
             f"A production CAD carries every screw: {fst} of {x5['n_instances']} instances in the "
             f"X500 V2 assembly are fasteners, and "
             f"{100.0 * x5['facets']['5G']['area_frac_below_ray_spacing']:.0f} % of its surface sits "
             f"on facets finer than our ray grid. Our meshes model the scatterers, not the hardware "
             f"store."
             + (f"\n{', '.join(astro)} is absent from (b): it is a single unnamed solid — "
                f"a shelled exterior with no part structure at all." if astro else ""),
             fontsize=9.6, color=MUTED, ha="left", va="center", linespacing=1.5)
    fig.text(0.99, 0.16 / H,
             "CAD measured for comparison only; manufacturer geometry is not redistributed.",
             fontsize=8.2, color=MUTED, ha="right", va="center")
    p = os.path.join(outdir, "cad_compare_structure.png")
    fig.savefig(p, dpi=135, facecolor="white")
    plt.close(fig)
    print(f"  → {os.path.relpath(p, ROOT)}")
    return p


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="공식 제조사 CAD 대조 — 치수·구조·패싯")
    ap.add_argument("--only", choices=("measure", "figs"), default=None)
    a = ap.parse_args()
    os.makedirs(FIG, exist_ok=True)
    J = measure() if a.only != "figs" else _load_json(LEDGER)
    if J is None:
        raise SystemExit(f"원장이 없다: {LEDGER} — 먼저 --only measure 로 만들 것.")
    if a.only != "measure":
        print("■ 그림")
        fig_dimensions(J)
        fig_facets(J)
        fig_structure(J)


if __name__ == "__main__":
    main()
