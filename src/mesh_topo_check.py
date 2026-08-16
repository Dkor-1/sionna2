# -*- coding: utf-8 -*-
"""
mesh_topo_check.py — **위상·이산화** 검사 (2026-08-16 신설)
==============================================================================
이 파일이 왜 따로 있나
  `src/mesh_check.py` 는 부품 무결성·치수·손대칭성·부품 간 파고듦을 본다. 인증 범주 지도
  (`outputs/mesh_cert_map_0816.json`)가 그 검사기를 칸별로 훑은 결과, **위상·이산화** 쪽에
  네 종류의 빈칸이 남았다(지도의 M3 «없음» · M5 «부분»):

    ⑴ **나비넥타이(비다양체 정점)** — 두 덩이가 정점 하나만 공유한다. 모서리를 아무리 세도
       안 나온다(모든 모서리가 정확히 두 번 쓰이므로 «수밀 통과»가 뜬다).
    ⑵ **자기교차** — 껍질 하나가 스스로를 관통한다. 수밀·감김·법선이 전부 정상으로 보인다.
       이게 위험한 이유는 σ 가 아니라 **관측**이다 — 내부판정(`contains`)을 쓰는 검사
       (그룹 안 겹침 · 매몰면 · 프롭↔벨 솔리드)의 **전제가 깨진 채로 그 검사들이 «0» 을
       보고**한다. 즉 못 봄이 통과로 둔갑한다.
    ⑶ **삼각형 크기가 파장에 묶였나** — 「지금 이 메쉬가 이 주파수에서 충분히 잘게 쪼개졌나」를
       묻는 상시 검사가 없었다(일회성 연구만 있었다).
    ⑷ **로프트 스플라인 오버슛 · 끝단 캡 손실** — 껍질을 만드는 3차 스플라인이 제어점 사이에서
       설계표 밖으로 부풀 수 있고, 로프트의 **끝단 캡**은 스무딩에 눌려 단면을 잃는다
       (저장소가 이미 −38~−44 % 로 실측해 둔 결함이다 — `drone_cad._body_folding` docstring).

  거기에 이미 있는 축(닫힘 · 법선 일관성 · 모서리 다양체 · 퇴화 삼각형)도 **여기서 다시**
  잰다. 같은 답이 두 경로로 나오는지 보기 위해서다 — 이유는 아래.

⭐ 왜 trimesh 를 안 쓰나 (이 파일의 설계 결정)
  이 저장소는 **검사기가 자기가 방금 수리한 사본을 검사한** 사고를 겪었다
  (`trimesh.split()` 의 `repair=True` 기본값, 감사 C1). `mesh_check.py` 는 그 자리를
  `repair=False` 명시로 막았지만, 그것은 «아는 함정 하나» 를 막은 것이지 «라이브러리가
  조용히 하는 일» 전부를 막은 것이 아니다. 그래서 이 파일은 **numpy/scipy 만으로** 위상을
  직접 센다 — 웰딩(정점 병합)도 우리가 하고, 연결요소도 우리가 세고, 모서리 다양체도 우리가
  센다. 그 결과 같은 질문에 **서로 독립한 두 개의 답**이 생긴다. 둘이 어긋나면 그 자체가
  신호다(인증서의 `cross_check` 절이 그 대조를 싣는다).

무엇을 보는가 — 검사 8종 (각각 양성 대조 + 음성 대조가 `benchmark/adv_mesh_topo_faults.py` 에 있다)
  [위상]
    T1 닫힘        : 부품마다 경계 모서리·**경계 곡선**(구멍의 테두리) 개수와 그 모양(평면 링인가)
    T2 법선 일관성 : 이웃 면의 감김이 서로 반대인가(모서리 방향 대조) + 부호부피 부호
    T3 다양체      : 모서리 다중도(1=구멍 · 2=정상 · ≥3=겹침) + ⭐**나비넥타이 정점** + 중복 삼각형
    T4 자기교차    : 한 부품이 스스로를 관통하는가 (정확한 삼각형–삼각형 교차 판정)
    T5 퇴화 삼각형 : 인덱스 중복 (a,a,b) · 면적 0 · 길이 0 모서리 · 최소내각 · 종횡비
  [이산화]
    D1 파장 대비 크기 : 최대/분위 변 길이를 λ 로 잰다 + **곡면 구간의 사지타**(chord 오차) vs λ/16
    D2 로프트 오버슛  : 3차 스플라인이 제어점 사이에서 설계표 밖으로 부푸는 양
    D3 끝단 캡        : 캡이 **있는가**(열린 링 탐지) + 끝단 단면이 설계표를 **얼마나 잃었나**

  ⚠ D2·D3 는 메쉬만 봐서는 «설계 의도» 를 모른다. 그래서 빌더를 **계측**한다 — `build_drone`
    을 도는 동안 `spline_sections` · `loft` · `_body_folding` 호출을 그대로 기록한다.
    분기 조건을 베껴 쓰지 않으므로 빌더가 바뀌어도 따라간다(못 부른 기체는 «해당 없음»).

⭐ 예산표의 뜻 — 이 저장소의 기존 규약 그대로다. 아래 값은 **«2026-08-16 지금 이만큼이다»**
  라는 선언이지 «이만큼이 옳다» 가 아니다. 새로 생기는 결함은 예산을 넘겨 **실패**한다.

⛔ 이 파일은 형상을 **하나도 바꾸지 않는다**(읽기 전용 검사기). GPU 도 쓰지 않는다.

실행:  cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/mesh_topo_check.py
       (한 기체만: `--drone mavic4pro` · 주파수: `--fc 5.8e9` · 자기교차 생략: `--no-selfint`
        · ⭐회귀 봉인 대조만: `--check-seal` — 인증서의 지문과 지금 메쉬를 견준다)

  짝 파일:  benchmark/adv_mesh_topo_faults.py          — 양성·음성 대조(이 검사들이 진짜 본다는 증거)
            benchmark/make_mesh_cert_topology_0816.py  — 인증서 생성
            outputs/mesh_cert_topology_discretization_0816.json — 인증서(대조 결과·전수 측정·봉인·한계)
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

C0 = 299792458.0

# --------------------------------------------------------------------------- #
#  검사 잣대 · 예산표
# --------------------------------------------------------------------------- #
WELD_TOL_M = 1e-9
#  정점 병합 반경 [m] = 1 nm. 왜 이 값인가: 우리 빌더는 프리미티브마다 정점 블록을 따로 쌓기
#  때문에 «같은 자리의 다른 정점» 이 생긴다(구 극점 등). 그 좌표차는 배정밀도 eps 급
#  (geom.uv_sphere 자체점검이 남극 1.2e-16·r 을 실측했다)이라 1 nm 면 넉넉히 덮고,
#  기체에서 물리적으로 구별되는 두 점(가장 가까운 것도 µm 급)은 절대 안 합친다.
#  ⚠ 반올림 격자가 아니라 **반경 그래프의 연결요소**로 합친다 — 격자 경계에서 갈라지지 않는다.

SLIVER_MIN_ANGLE_DEG = 0.5      # mesh_check 와 같은 잣대(뜻이 갈리면 안 된다)
DEGENERATE_AREA_M2 = 1e-14      # mesh_check 와 같은 잣대

#  ⑴ 경계 곡선(구멍의 테두리) 예산 — (기종, 그룹) → 허용 개수. **원칙은 0 이다.**
BOUNDARY_CURVE_BUDGET = {
    "_default": 0,
    #  ↓ 선언된 기존 결함. mini2 'body' 의 구멍 1개(경계 모서리 3개)는 감사 I5 가 이미
    #    선언한 자리이고 `mesh_check.BOUNDARY_EDGE_BUDGET` 에도 같은 값이 박혀 있다.
    #    (원인: cadkit 의 불리언 합집합 출력에서 needle 삼각형 1장이 지워졌다.)
    ("mini2", "body"): 1,
}

#  ⑵ 비다양체 모서리(셋 이상이 쓰는 모서리) 예산 — 전 기종 0. 실측도 0 이다.
NONMANIFOLD_EDGE_BUDGET = {"_default": 0}

#  ⑶ ⭐**나비넥타이 정점** 예산 — (기종, 그룹) → 허용 개수. 실측은 전 기종 0 이다
#     (이 검사가 이 라운드에 처음 생겼고, 첫 전수 측정에서 결함이 없었다).
BOWTIE_VERTEX_BUDGET = {"_default": 0}

#  ⑷ 중복 삼각형(같은 세 정점) 예산 — 전 기종 0. 실측도 0.
DUPLICATE_FACE_BUDGET = {"_default": 0}

#  ⑸ ⭐**자기교차** 예산 — (기종, 그룹) → 교차하는 삼각형 **쌍**의 허용 개수.
#     전 기종 **0** 이고 실측도 0 이다(2026-08-16 전수, 부품 302개).
#     ⚠ 정직하게 적어 둘 것 — 이 라운드의 첫 시험은 메쉬를 **그룹을 가로질러** 웰딩해서 쟀고,
#       거기서 s1000plus 145×2 · typhoonh480 139×2 · x500v2 38×4 쌍이 나왔다. 추적해 보니
#       전부 **'gear'(고무 발 슬리브) ↔ 'gear_cf'(카본 스키드 튜브)** 사이, 즉 **다른 두 부품이
#       서로 파고든 것**이었다. 그것은 이 검사의 축(«한 껍질이 스스로를 뚫는가»)이 아니라
#       부품 간 파고듦(지도 M9)이고, `mesh_check.check_buried_faces` · `check_prop_bell_solid`
#       가 보는 자리다. 그래서 여기서는 **그룹 안에서만** 웰딩·부품분해한다(mesh_check 와 같은
#       규약). 이 사실을 인증서 `cross_group_note` 에 그대로 싣는다 — 숨기지 않는다.
SELF_INTERSECT_BUDGET = {"_default": 0}

#  ⑹ 퇴화 — 인덱스 중복 (a,a,b)·면적 0·길이 0 모서리는 **전부 0** 이 원칙이고 실측도 0.
DEGENERATE_BUDGET = {"_default": 0}
#     슬리버(최소내각 < 0.5°)는 `mesh_check.SLIVER_BUDGET` 이 이미 기종 단위로 감시한다.
#     여기서는 **되재기만** 하고 판정에 넣지 않는다(같은 축을 두 곳에서 판정하면 뜻이 갈린다).

#  ⑺ ⭐**파장 대비 삼각형 크기** — 판정 주파수와 잣대.
FC_DEFAULT_HZ = 3.5e9           # 우리 주력 대역(5G n78). λ = 85.65 mm
FACET_EDGE_DIV = 7.0            # 「변 ≤ λ/7」 — PO 점구름 간격(rcs_po: spacing=λ/7)과 같은 눈금
SAGITTA_DIV = 16.0              # 「사지타 ≤ λ/16」 — 왕복 위상 45° 에 해당하는 표면정밀도 관례
SMOOTH_DIHEDRAL_MAX_DEG = 30.0  # 이면각이 이보다 크면 «설계상 뾰족한 모서리» 로 보고 사지타에서 뺀다

#     변 길이 예산 [면적 비율 %] — 「λ/7 보다 긴 변을 가진 삼각형이 표면적의 몇 % 인가」.
#     ⚠ **이 축은 판정에 안 넣는다**(=참고 지표). 이유를 정직하게 적는다:
#       PO 는 삼각형을 λ/7 격자로 **다시 쪼개서** 점을 깐다(`rcs_po.mesh_to_points`), SBR 은
#       광선 격자가 λ/12 다. 즉 «큰 삼각형» 이 곧 «성긴 적분» 이 아니다. 큰 삼각형이 진짜
#       오차가 되는 것은 그 자리가 **곡면일 때**뿐이고, 그것을 재는 잣대가 아래 사지타다.
FACET_EDGE_AREA_PCT_BUDGET = {"_default": 100.0}

#     ⭐사지타 예산 [면적 비율 %] — 「곡면 구간에서 chord 오차가 λ/16 을 넘는 면적 비율」.
#     실측(3.5 GHz)은 전 기종 **0.000 %** 다. 이것이 이 축의 **판정 잣대**다.
#     ⚠ 여유가 얼마나 되는지도 적는다(«0 % 니까 안심» 이 아니다) — 최악은 s1000plus 의
#       카본 스키드(gear_cf)로 사지타 4.96 mm = **λ/16 의 0.93 배**다. 3.5 GHz 에서 이 기체는
#       한계선 바로 아래에 있고, 주파수를 올리면(예: 5.8 GHz → λ/16 = 3.23 mm) 넘는다.
#       그래서 `--fc` 로 다른 대역에서 다시 돌릴 수 있게 만들어 뒀다.
SAGITTA_AREA_PCT_BUDGET = {"_default": 0.01}

#  ⑻ 로프트 스플라인 오버슛 — 3차 스플라인이 **이웃 제어점의 상자 밖으로** 나가는 양.
#     단위: 그 곡선 자신의 진폭(표의 max−min) 대비 %.
#     ⚠ «오버슛이 있다» 자체는 3차 보간(not-a-knot)의 성질이지 버그가 아니다. 문제는 **얼마나**
#       나가는지 아무도 안 재고 있었다는 것이다. 아래는 2026-08-16 실측 + 약 15 % 여유다.
#       뜻: 셸 표면이 제어 스테이션 사이에서 설계표보다 그만큼 **부푼다**. 절대량으로는
#       matrice4e 반높이 +3.02 mm(공식 CAD 로 정한 단면 위로), mini5pro 반폭 +2.67 mm 다.
#       ⚠ 이 값은 «형상이 틀렸다» 는 판정이 아니라 «보간이 이만큼 부풀린다» 는 계측이다.
LOFT_OVERSHOOT_PCT_BUDGET = {
    "_default": 20.0,       # 새 기체는 선언 없이 통과하지 못하게(실측 최대 15.3 보다 조금 위)
    "mini5pro": 16.0,       # 실측 13.951 — 동체 반폭(hw)
    "matrice4e": 18.0,      # 실측 15.327 — 동체 반높이(hh) = +3.02 mm
    "mini2": 11.0,          # 실측 9.403 — 동체 반폭
    "mavic4pro": 8.0,       # 실측 6.761 — 캐노피 반폭(셸형 6종 공통값)
    "phantom4": 8.0,        # 실측 6.761 — 〃
    "phantom3": 8.0,        # 실측 6.761 — 〃
}
#     스플라인이 하한 클램프(`superellipse` 의 max(1e-4, ·))에 닿은 스테이션 수 — 0 이어야 한다.
#     닿았다면 단면 반폭이 음수로 내려갔다는 뜻이고, 그건 조용히 0.1 mm 로 바뀐다.
LOFT_CLAMP_BUDGET = {"_default": 0}

#  ⑼ ⭐끝단 캡 — 캡이 없으면(열린 링) 즉시 실패. 캡 형상 손실은 설계표 대비 %.
#     실측(출하 상태, `smooth_iters=0`)은 셸형 6종 전부 |손실| ≤ 0.1 % 다.
#     ⚠ 이 자리는 **2026-08-16 에 고쳐진 자리**다(옛 `smooth_iters=4` 는 −38~−44 %).
#       예산 2 % 는 «고친 상태를 봉인한다» 는 뜻이다 — 되돌아가면 즉시 실패한다.
CAP_DEFICIT_PCT_BUDGET = {"_default": 2.0}


# --------------------------------------------------------------------------- #
#  0층 — 위상 원시 도구 (numpy/scipy 만. trimesh 를 안 거친다)
# --------------------------------------------------------------------------- #
def weld(V, F, tol: float = WELD_TOL_M):
    """**정점 병합**(웰딩) — 반경 `tol` 안의 정점들을 한 점으로 본다.

    왜 필요한가: `geom` 프리미티브는 같은 자리에 정점을 여러 개 쌓는다. 웰딩 없이 세면 멀쩡한
    부품이 «구멍투성이» 로 나온다 — 실측: `uv_sphere(seg=24, rings=12)` 는 웰딩 전 **경계
    모서리 96개**, 웰딩(46개 병합) 후 **0개**다(극점 2·(seg−1)개가 같은 자리에 쌓인다).
    ⚠ 웰딩은 **새 삼각형을 만들지 않는다** — 구멍을 메우는 «수리» 와는 층이 다르다(파일 머리말).

    ⭐ 정직하게 적어 둘 것 — **출하 기체 10대에서는 실제로 합쳐진 정점이 0개**다. cadkit 이
      `trimesh(process=True)` 로 이미 합쳐서 내보내기 때문이다. 즉 이 단계는 기체에서는
      아무 일도 안 하고, 합성 대조(geom 프리미티브를 직접 쌓는 시험)에서 일한다. 그래도
      단계를 두는 이유는 «안 해도 되더라» 를 **매번 측정으로 확인**하기 위해서다
      (`n_welded_verts` 로 인증서에 실린다).

    반환: (Vw, Fw, n_merged) — 병합으로 사라진 정점 수가 n_merged."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    V = np.asarray(V, float)
    F = np.asarray(F, np.int64)
    n = len(V)
    pairs = cKDTree(V).query_pairs(r=float(tol), output_type="ndarray")
    if len(pairs):
        g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
        k, lab = connected_components(g, directed=False)
    else:
        k, lab = n, np.arange(n)
    cnt = np.bincount(lab, minlength=k).astype(float)
    Vw = np.stack([np.bincount(lab, weights=V[:, d], minlength=k) / cnt for d in range(3)], 1)
    return Vw, lab[F], int(n - k)


def face_components(F, n_vert: int):
    """면의 **연결요소** 라벨 — 정점을 공유하면 같은 부품. 반환 (개수, 면별 라벨)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    F = np.asarray(F, np.int64)
    if not len(F):
        return 0, np.zeros(0, np.int64)
    rows = np.repeat(np.arange(len(F)), 3)
    M = coo_matrix((np.ones(len(rows), np.int8), (rows, F.reshape(-1))),
                   shape=(len(F), n_vert)).tocsr()
    n, lab = connected_components(M @ M.T, directed=False)
    return int(n), lab


def _directed_edges(F):
    """면마다 (v_s → v_{s+1}) 유향 모서리 3개. 유향 모서리 인덱스 e = 3·f + s."""
    F = np.asarray(F, np.int64)
    a = F.reshape(-1)                                   # (3F,)  시작점
    b = F[:, [1, 2, 0]].reshape(-1)                     # (3F,)  끝점
    return a, b


def edge_census(F, n_vert: int | None = None):
    """모서리 다중도 census — **`is_watertight` 한 개로 뭉개지 않는다.**
      · 다중도 1 = 경계 모서리(구멍의 테두리)
      · 다중도 2 = 정상
      · 다중도 ≥3 = 비다양체(껍질이 겹쳐 붙음)
    덤으로 **방향 일관성**(다중도 2 인 모서리를 두 면이 서로 반대로 감았는가)도 같이 센다.

    반환 dict: n_edges · n_boundary · n_manifold · n_nonmanifold · max_mult ·
               n_flipped(방향 어긋난 모서리 수) · uedge(고유 모서리 배열) · inv(유향→고유 사상)

    ⚠ 모서리 키는 (작은 인덱스)·N + (큰 인덱스) 의 **1차원 정수**다. 2차원 `np.unique(axis=0)`
      은 같은 답을 주지만 수십 배 느려서, 부품마다 부르는 이 함수에는 못 쓴다."""
    F = np.asarray(F, np.int64)
    a, b = _directed_edges(F)
    N = np.int64(n_vert if n_vert is not None else (int(F.max()) + 1 if len(F) else 1))
    key = np.minimum(a, b) * N + np.maximum(a, b)
    uk, inv, mult = np.unique(key, return_inverse=True, return_counts=True)
    uedge = np.stack([uk // N, uk % N], 1)
    inv = inv.reshape(-1)
    n_b = int((mult == 1).sum()); n_2 = int((mult == 2).sum())
    n_nm = int((mult >= 3).sum())
    #  방향 일관성 — 다중도 2 인 모서리에서 두 유향 사용이 **반대**여야 한다.
    is2 = mult[inv] == 2
    fwd = (a <= b)                                       # 이 유향 사용이 «정방향» 인가
    #  같은 고유 모서리를 같은 방향으로 두 번 쓰면 → 감김이 뒤집힌 이웃
    same = np.bincount(inv[is2], weights=fwd[is2].astype(float), minlength=len(uedge))
    cnt2 = np.bincount(inv[is2], minlength=len(uedge))
    flipped = int(np.sum((cnt2 == 2) & ((same == 2) | (same == 0))))
    return dict(n_edges=int(len(uedge)), n_boundary=n_b, n_manifold=n_2,
                n_nonmanifold=n_nm, max_mult=int(mult.max()) if len(mult) else 0,
                n_flipped=flipped, uedge=uedge, mult=mult, inv=inv)


def boundary_curves(V, F, ec=None):
    """**경계 곡선** — 경계 모서리들이 이루는 테두리 하나하나. 구멍의 «개수» 를 세려면
    모서리 수가 아니라 이것을 세야 한다(모서리 3개짜리 구멍 하나 ↔ 모서리 3개짜리 구멍 세 개는
    전혀 다른 상태다).

    각 곡선마다 모양도 잰다 — **평면 링인가**. 로프트의 끝단 캡이 빠지면 그 자리에 «평평하고
    둥근» 테두리가 남으므로, 이 표시가 곧 «끝단 캡 손실» 의 지문이다(D3 참조).

    반환: 곡선 목록 [dict(n_edges, n_verts, closed, planarity, roundness, is_planar_ring, ...)]"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    ec = edge_census(F, len(V)) if ec is None else ec
    bmask = ec["mult"] == 1
    if not bmask.any():
        return []
    be = ec["uedge"][bmask]                              # (nb,2)
    verts = np.unique(be)
    remap = {int(v): i for i, v in enumerate(verts)}
    ii = np.vectorize(remap.get)(be)
    g = coo_matrix((np.ones(len(ii)), (ii[:, 0], ii[:, 1])), shape=(len(verts),) * 2)
    n, lab = connected_components(g, directed=False)
    out = []
    for c in range(n):
        vsel = verts[lab == c]
        esel = be[np.isin(be[:, 0], vsel)]
        P = V[vsel]
        deg = np.bincount(np.vectorize(remap.get)(esel).reshape(-1), minlength=len(verts))
        closed = bool(np.all(deg[lab == c] == 2))        # 모든 정점의 차수가 2 = 닫힌 고리
        ctr = P.mean(0)
        Q = P - ctr
        #  평면성 — SVD 3번째 특이값 / 지름
        s = np.linalg.svd(Q, compute_uv=False) if len(P) >= 3 else np.zeros(3)
        diam = float(np.linalg.norm(Q, axis=1).max()) if len(P) else 0.0
        planarity = float(s[2] / max(diam, 1e-30)) if len(s) >= 3 else 0.0
        r = np.linalg.norm(Q, axis=1)
        roundness = float(r.std() / max(r.mean(), 1e-30)) if len(r) else 0.0
        out.append(dict(n_edges=int(len(esel)), n_verts=int(len(vsel)), closed=closed,
                        planarity=round(planarity, 6), roundness=round(roundness, 6),
                        diameter_mm=round(2000.0 * diam, 4),
                        #  «평평하고 둥근 닫힌 테두리» = 캡이 빠진 자리의 지문
                        is_planar_ring=bool(closed and planarity < 1e-3
                                            and roundness < 0.35 and len(vsel) >= 8),
                        center_m=[round(float(x), 6) for x in ctr]))
    return out


def bowtie_vertices(F, n_vert: int | None = None):
    """⭐**나비넥타이(비다양체) 정점** — 정점 하나만 공유하고 모서리는 공유하지 않는 두 덩이.

    왜 모서리 세기로는 못 잡나: 두 덩이가 각각 멀쩡한 껍질이면 **모든 모서리가 정확히 두 번**
    쓰인다. `is_watertight` 도 True 가 되고 부호부피도 정상이다. 그런데 그 자리는 다양체가
    아니라서 «안/밖» 이 국소적으로 정의되지 않는다.

    판정법: 면의 **코너**(면 하나가 정점 하나에서 갖는 자리)를 노드로 두고, 다중도 2 인
    모서리로 이웃한 코너끼리 잇는다. 한 정점의 코너들이 **두 덩이 이상으로 갈라지면** 그
    정점이 나비넥타이다. (다중도 ≥3 인 모서리에 붙은 정점은 이미 «비다양체 모서리» 로
    걸리므로 여기서 빼고 센다 — 같은 결함을 두 번 세지 않기 위해서다.)

    반환: (나비넥타이 정점 인덱스 배열, 제외한 정점 수)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    F = np.asarray(F, np.int64)
    nf = len(F)
    if nf == 0:
        return np.zeros(0, np.int64), 0
    a, b = _directed_edges(F)
    ec = edge_census(F, n_vert)
    inv, mult = ec["inv"], ec["mult"]
    #  코너 id = 3·f + s.  유향 모서리 e=3f+s 의 시작 코너는 e, 끝 코너는 3f+((s+1)%3)
    e_idx = np.arange(3 * nf)
    f_idx = e_idx // 3
    s_idx = e_idx % 3
    c_start = 3 * f_idx + s_idx
    c_end = 3 * f_idx + (s_idx + 1) % 3
    #  다중도 2 인 고유 모서리마다 유향 사용 두 개를 짝짓는다
    ok2 = mult[inv] == 2
    order = np.argsort(inv[ok2], kind="stable")
    ee = e_idx[ok2][order]
    e1, e2 = ee[0::2], ee[1::2]
    same_dir = a[e1] == a[e2]
    #  같은 방향이면 시작↔시작 / 끝↔끝, 반대 방향이면 시작↔끝 / 끝↔시작
    r0 = np.r_[c_start[e1], c_end[e1]]
    r1 = np.r_[np.where(same_dir, c_start[e2], c_end[e2]),
               np.where(same_dir, c_end[e2], c_start[e2])]
    g = coo_matrix((np.ones(len(r0)), (r0, r1)), shape=(3 * nf, 3 * nf))
    _, clab = connected_components(g, directed=False)
    #  정점별 «코너 덩이» 개수
    vid = F.reshape(-1)                                   # 코너 e 의 정점 = F[f,s]
    pair = np.unique(np.stack([vid, clab], 1), axis=0)
    ncomp = np.bincount(pair[:, 0], minlength=int(vid.max()) + 1)
    cand = np.where(ncomp > 1)[0]
    #  비다양체 모서리에 붙은 정점은 뺀다(그 축에서 이미 걸린다)
    nm_v = np.unique(ec["uedge"][mult >= 3]) if (mult >= 3).any() else np.zeros(0, np.int64)
    keep = cand[~np.isin(cand, nm_v)]
    return keep, int(len(cand) - len(keep))


def duplicate_faces(F):
    """**중복 삼각형** — 같은 세 정점을 쓰는 면이 두 번 이상 실린 것(감김 방향 무시).
    PO 는 면적을 그대로 두 번 더한다. 지도 M2 가 «전용 검사 없음» 이라고 적은 자리다."""
    F = np.asarray(F, np.int64)
    if not len(F):
        return 0
    key = np.sort(F, axis=1)
    _, cnt = np.unique(key, axis=0, return_counts=True)
    return int((cnt - 1).clip(min=0).sum())


def signed_volume_mm3(V, F):
    """부호부피[mm³] — 발산정리 Σ a·(b×c)/6. 법선이 안쪽이면 음수. trimesh 를 안 거친다."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0 * 1e9)


def euler_genus(V_used_count, F, n_boundary, ec=None):
    """오일러 표수 χ = V − E + F 와 **종수**(손잡이 개수) g.
    닫힌 유향 곡면: χ = 2 − 2g − b (b = 경계 곡선 수).
    ⚠ 종수가 0 이 아니면 «도넛처럼 구멍이 뚫린 껍질» 이라는 뜻이다. 설계일 수도 결함일 수도
      있으므로 **판정하지 않고 세어서 싣는다**(선언 축)."""
    ec = edge_census(F) if ec is None else ec
    chi = int(V_used_count) - ec["n_edges"] + int(len(F))
    g2 = 2 - chi - int(n_boundary)
    return chi, (g2 / 2.0)


# --------------------------------------------------------------------------- #
#  T4 — 자기교차 (정확한 삼각형–삼각형 판정, 근사 없음)
# --------------------------------------------------------------------------- #
def _sap_pairs(lo, hi, max_pairs=20_000_000):
    """**쓸고 자르기**(sweep and prune) — 축정렬 상자가 겹치는 삼각형 쌍만 남긴다.
    가장 넓게 퍼진 축으로 정렬한 뒤, 각 삼각형의 상자 오른쪽 끝을 넘지 않는 뒤쪽 삼각형만 본다.
    반환 (쌍 배열 또는 None, 후보 쌍 총수). None 이면 상한을 넘어 **검사를 못 한 것**이다."""
    n = len(lo)
    if n < 2:
        return np.zeros((0, 2), np.int64), 0
    ax = int(np.argmax(hi.max(0) - lo.min(0)))
    order = np.argsort(lo[:, ax], kind="stable")
    lo_s, hi_s = lo[order], hi[order]
    end = np.searchsorted(lo_s[:, ax], hi_s[:, ax], side="right")
    cnt = np.maximum(end - np.arange(n) - 1, 0)
    tot = int(cnt.sum())
    if tot > max_pairs:
        return None, tot
    i = np.repeat(np.arange(n), cnt)
    j = i + 1 + (np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    a, b = order[i], order[j]
    ok = np.ones(len(a), bool)
    for d in range(3):
        if d != ax:
            ok &= (lo[a, d] <= hi[b, d]) & (lo[b, d] <= hi[a, d])
    return np.c_[a[ok], b[ok]], tot


def _seg_tri_hit(P0, P1, A, B, C, rel_eps=1e-9):
    """선분 P0→P1 이 삼각형 ABC 의 **내부**를 뚫는가 (Möller–Trumbore, 벡터화).
    ⚠ 경계(꼭짓점·모서리에 스치는 것)는 **안 센다** — 맞닿은 설계를 결함으로 부르지 않기 위해서다."""
    d = P1 - P0
    e1, e2 = B - A, C - A
    p = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, p)
    scale = np.maximum(np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1)
                       * np.linalg.norm(d, axis=1), 1e-300)
    good = np.abs(det) > rel_eps * scale               # 평행/동일평면은 여기서 빠진다(한계 선언)
    if not good.any():
        return np.zeros(len(P0), bool)
    idet = np.zeros(len(P0)); idet[good] = 1.0 / det[good]
    tv = P0 - A
    u = np.einsum("ij,ij->i", tv, p) * idet
    q = np.cross(tv, e1)
    v = np.einsum("ij,ij->i", d, q) * idet
    t = np.einsum("ij,ij->i", e2, q) * idet
    e = 1e-9
    return good & (u > e) & (v > e) & (u + v < 1 - e) & (t > e) & (t < 1 - e)


def self_intersections(V, F):
    """한 부품이 **스스로를 관통**하는 삼각형 쌍의 수. 정점을 공유하는 이웃 쌍은 뺀다.

    ⚠ 한계(선언): **동일평면 교차**(두 삼각형이 같은 평면에서 겹치는 것)는 이 판정이 안 본다 —
      det ≈ 0 으로 빠진다. 그 경우는 «중복 삼각형»(T3)·«그룹 안 겹침»(mesh_check)이 본다.
    반환 dict(n_hits, n_candidates, checked)"""
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    P = V[F]
    lo, hi = P.min(1), P.max(1)
    pairs, tot = _sap_pairs(lo, hi)
    if pairs is None:
        return dict(n_hits=None, n_candidates=int(tot), checked=False)
    if not len(pairs):
        return dict(n_hits=0, n_candidates=0, checked=True)
    a, b = pairs[:, 0], pairs[:, 1]
    share = (F[a][:, :, None] == F[b][:, None, :]).any(2).any(1)
    a, b = a[~share], b[~share]
    if not len(a):
        return dict(n_hits=0, n_candidates=0, checked=True)
    Pa, Pb = P[a], P[b]
    hit = np.zeros(len(a), bool)
    for s, e in ((0, 1), (1, 2), (2, 0)):
        hit |= _seg_tri_hit(Pa[:, s], Pa[:, e], Pb[:, 0], Pb[:, 1], Pb[:, 2])
        hit |= _seg_tri_hit(Pb[:, s], Pb[:, e], Pa[:, 0], Pa[:, 1], Pa[:, 2])
    return dict(n_hits=int(hit.sum()), n_candidates=int(len(a)), checked=True)


# --------------------------------------------------------------------------- #
#  T5 — 퇴화 삼각형 · D1 — 파장 대비 크기
# --------------------------------------------------------------------------- #
def triangle_quality(V, F):
    """삼각형 품질 — 면적·최소내각·종횡비·길이 0 모서리·인덱스 중복."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    A, B, C = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(B - A, C - A)
    area = 0.5 * np.linalg.norm(cr, axis=1)
    L = np.stack([np.linalg.norm(B - A, axis=1), np.linalg.norm(C - B, axis=1),
                  np.linalg.norm(A - C, axis=1)], 1)

    def ang(P, Q, R):
        u, w = Q - P, R - P
        nu = np.linalg.norm(u, axis=1); nw = np.linalg.norm(w, axis=1)
        d = np.clip((u * w).sum(1) / np.maximum(nu * nw, 1e-300), -1, 1)
        return np.degrees(np.arccos(d))
    amin = np.minimum(np.minimum(ang(A, B, C), ang(B, C, A)), ang(C, A, B))
    per = L.sum(1)
    r_in = np.where(per > 0, 2.0 * area / np.maximum(per, 1e-300), 0.0)
    aspect = np.where(r_in > 0, L.max(1) / np.maximum(r_in, 1e-300), np.inf)
    dup_idx = int(((F[:, 0] == F[:, 1]) | (F[:, 1] == F[:, 2]) | (F[:, 0] == F[:, 2])).sum())
    return dict(area=area, min_angle_deg=amin, edge_len=L, aspect=aspect,
                n_repeat_index=dup_idx, n_zero_edge=int((L <= 0).sum()),
                n_zero_area=int((area < DEGENERATE_AREA_M2).sum()),
                n_sliver=int((amin < SLIVER_MIN_ANGLE_DEG).sum()))


def facet_wavelength(V, F, lam: float):
    """⭐**삼각형 크기가 파장에 묶였나** — 두 잣대로 잰다.

    ⑴ 변 길이 — 「최대 변 ≤ λ/7」. 참고 지표다(판정 아님). 왜 판정이 아닌지:
       PO 는 삼각형을 λ/7 격자로 **다시 쪼개** 점을 깔고(`rcs_po.mesh_to_points` 141-148행),
       SBR 은 광선 격자가 λ/12 다. 큰 삼각형이 곧 성긴 적분이 아니다.
    ⑵ ⭐사지타 — 「곡면 구간의 chord 오차 ≤ λ/16」. 이것이 **판정 잣대**다.
       매끈한 곡면을 폭 w 의 평면 조각으로 근사하고 이웃 조각이 θ 만큼 꺾이면, 그 자리의
       곡률반경은 R ≈ w/θ 이고 현(chord)과 참곡면의 최대 거리(사지타)는
           s = R(1 − cos(θ/2)) ≈ R θ²/8 ≈ w·θ/8.
       λ/16 은 «왕복 위상 45°» 에 해당하는 표면정밀도 관례다.

       ⭐⭐ w 는 **꺾이는 방향의 조각 폭**이지 공유 모서리의 길이가 아니다. 이 구별을 틀리면
         답이 100 배 틀린다. 이 파일은 w 를 세 번 고쳐 잡았고, 고른 근거는 **해석적 참값과의
         눈금 대조**다(`benchmark/adv_mesh_topo_faults.py` 의 «D1 눈금검증»):
           ① 공유 모서리 길이   → 반지름 12 mm·분할 20 스키드 튜브에서 14 mm(참값의 95 배).
              축 방향 모서리가 360 mm 인데 곡률은 그 모서리와 **직각인** 둘레 방향에 있다.
           ② 두 면 무게중심 거리의 직각 성분 → 0.097 mm (참값 0.148 의 0.66 배, 계통 −34 %).
              삼각형 무게중심이 조각의 가운데가 아니라서 생기는 편향이다.
           ③ ⭐**공유 모서리에서 잰 두 삼각형 높이의 작은 쪽** min(2A₁/Lₑ, 2A₂/Lₑ)
              → 0.1475 mm (참값 0.1477, **오차 0.1 %**). 이것을 쓴다.
         왜 «작은 쪽» 인가: 균일 분할(원통·구·로프트)에서는 두 높이가 같아 뜻이 하나다.
         크기가 크게 다른 짝(부채꼴 캡 옆의 바늘 조각)에서는 **가는 쪽이 그 자리의 표본
         간격**이다 — 실제로 스키드 튜브 끝의 «밑변 1.3 mm × 길이 204 mm» 조각은 축 방향으로
         **평평하고**(원통은 축 방향으로 곡률이 0) 꺾임은 끝의 작은 조각에 몰려 있다.
         ⚠ 큰 쪽으로 잰 값(과대 방향)도 버리지 않고 `max_sagitta_bound_mm` 로 **같이 싣는다** —
           «작은 쪽» 선택이 실제로 얼마를 깎았는지 보이게 하기 위해서다.
       ⚠ 이면각이 30° 를 넘는 모서리는 **설계상 뾰족한 자리**(상자 모서리 등)로 보고 뺀다 —
         거기서는 chord 오차라는 개념 자체가 성립하지 않는다.

    ⭐ 두 잣대의 관계(해석적) — 조각 폭이 λ/7 이하이고 이면각이 30° 이하이면
       s ≤ (λ/7)·(π/6)/8 = λ/107 ≪ λ/16 이다. 즉 **크기 조건이 사지타 조건보다 강하다.**
       그래서 λ/7 을 넘는 자리를 찾았을 때 «그 자리가 평면인가 곡면인가» 가 진짜 질문이 된다."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    tq = triangle_quality(V, F)
    area, L = tq["area"], tq["edge_len"]
    tot = float(area.sum())
    emax = L.max(1)
    lam_edge = lam / FACET_EDGE_DIV
    over_area = float(area[emax > lam_edge].sum())

    #  이면각 — 다중도 2 인 모서리에서 두 면의 법선 사이 각
    ec = edge_census(F, len(V))
    inv, mult = ec["inv"], ec["mult"]
    nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    nl = np.linalg.norm(nrm, axis=1)
    nhat = nrm / np.maximum(nl, 1e-300)[:, None]
    ok2 = mult[inv] == 2
    e_idx = np.arange(3 * len(F))
    order = np.argsort(inv[ok2], kind="stable")
    ee = e_idx[ok2][order]
    f1, f2 = ee[0::2] // 3, ee[1::2] // 3
    cosd = np.clip(np.einsum("ij,ij->i", nhat[f1], nhat[f2]), -1, 1)
    dih = np.degrees(np.arccos(cosd))                    # 0° = 평면, 90° = 상자 모서리
    #  ⭐꺾이는 방향의 조각 폭 w = 공유 모서리에서 잰 두 삼각형 높이의 **작은 쪽**(위 설명)
    a, b = _directed_edges(F)
    ei = ee[0::2]
    elen = np.maximum(np.linalg.norm(V[b[ei]] - V[a[ei]], axis=1), 1e-300)
    h1, h2 = 2.0 * area[f1] / elen, 2.0 * area[f2] / elen
    width = np.minimum(h1, h2)
    width_bound = np.maximum(h1, h2)          # 과대 방향 상한 — 판정엔 안 쓰고 기록만 한다
    smooth = dih <= SMOOTH_DIHEDRAL_MAX_DEG
    sag = np.zeros(len(dih))
    sag_bound = np.zeros(len(dih))
    sag[smooth] = width[smooth] * np.radians(dih[smooth]) / 8.0
    sag_bound[smooth] = width_bound[smooth] * np.radians(dih[smooth]) / 8.0
    bad_edge = smooth & (sag > lam / SAGITTA_DIV)
    #  사지타 위반 «면적» — 그 모서리를 쓰는 두 면의 면적을 (중복 없이) 센다
    bad_faces = np.unique(np.r_[f1[bad_edge], f2[bad_edge]]) if bad_edge.any() else np.zeros(0, int)
    bad_area = float(area[bad_faces].sum()) if len(bad_faces) else 0.0
    q = lambda x, p: float(np.percentile(x, p)) if len(x) else 0.0    # noqa: E731
    return dict(
        lam_mm=round(1000.0 * lam, 4),
        max_edge_mm=round(1000.0 * float(emax.max()), 4),
        p99_edge_mm=round(1000.0 * q(emax, 99), 4),
        median_edge_mm=round(1000.0 * q(emax, 50), 4),
        max_edge_over_lam=round(float(emax.max()) / lam, 5),
        edge_over_lam7_area_pct=round(100.0 * over_area / max(tot, 1e-30), 4),
        max_curved_width_mm=round(1000.0 * float(width[smooth].max()) if smooth.any() else 0.0, 4),
        max_dihedral_deg=round(float(dih.max()) if len(dih) else 0.0, 3),
        p99_dihedral_deg=round(q(dih, 99), 3),
        smooth_edge_frac_pct=round(100.0 * float(smooth.mean()) if len(dih) else 0.0, 2),
        max_sagitta_mm=round(1000.0 * float(sag.max()) if len(sag) else 0.0, 5),
        max_sagitta_bound_mm=round(1000.0 * float(sag_bound.max()) if len(sag_bound) else 0.0, 5),
        max_sagitta_over_lam=round(float(sag.max()) / lam if len(sag) else 0.0, 6),
        sagitta_over_lam16_area_pct=round(100.0 * bad_area / max(tot, 1e-30), 4),
        n_bad_sagitta_edges=int(bad_edge.sum()),
        area_mm2=round(1e6 * tot, 2),
    )


# --------------------------------------------------------------------------- #
#  1층 — 기체 한 대를 검사한다
# --------------------------------------------------------------------------- #
def _budget(tbl, name, grp=None):
    if grp is not None and (name, grp) in tbl:
        return tbl[(name, grp)]
    return tbl.get(name, tbl["_default"])


def check_topology(mesh, name="mesh", fc=FC_DEFAULT_HZ, self_int=True, verbose=False) -> dict:
    """T1~T5 + D1 — 메쉬 하나(기체 한 대)의 위상·이산화 전수 검사.

    ⚠ 웰딩과 부품 분해는 **그룹 안에서** 한다(mesh_check 와 같은 규약). 그룹은 재질 단위이고,
      그룹을 가로질러 웰딩하면 서로 닿아 있는 다른 재질 부품이 한 덩이로 붙어 버린다."""
    V0 = np.asarray(mesh.v, float)
    F0 = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    lam = C0 / float(fc)
    groups, tot = {}, dict(parts=0, boundary_curves=0, nonmanifold=0, bowtie=0,
                           dup_faces=0, selfint=0, selfint_unchecked=0,
                           repeat_index=0, zero_area=0, zero_edge=0, sliver=0,
                           flipped_edges=0, negative_volume_parts=0, open_parts=0,
                           planar_ring_curves=0, genus_nonzero_parts=0)
    for grp in sorted(set(G.tolist())):
        f = F0[G == grp]
        used = np.unique(f)
        remap = np.zeros(int(used.max()) + 1, np.int64)
        remap[used] = np.arange(len(used))
        V, F, n_merged = weld(V0[used], remap[f])
        npart, lab = face_components(F, len(V))
        ec = edge_census(F, len(V))
        bt, bt_excl = bowtie_vertices(F, len(V))
        dupf = duplicate_faces(F)
        tq = triangle_quality(V, F)
        curves, si_hits, si_unchecked, n_open, n_neg, n_g = [], 0, 0, 0, 0, 0
        parts = []
        for c in range(npart):
            sel = np.where(lab == c)[0]
            Fc = F[sel]
            uc = np.unique(Fc)
            ecc = edge_census(Fc, len(V))
            cur = boundary_curves(V, Fc, ec=ecc)
            curves += cur
            vol = signed_volume_mm3(V, Fc)
            chi, gen = euler_genus(len(uc), Fc, len(cur), ec=ecc)
            si = dict(n_hits=None, checked=False, n_candidates=0)
            if self_int:
                si = self_intersections(V, Fc)
                if si["checked"]:
                    si_hits += int(si["n_hits"])
                else:
                    si_unchecked += 1          # 상한을 넘어 **못 본** 부품 — 0 으로 보고하지 않는다
            if cur:
                n_open += 1
            if not cur and vol <= 0:
                n_neg += 1
            if abs(gen) > 1e-9:
                n_g += 1
            parts.append(dict(faces=int(len(sel)), verts=int(len(uc)),
                              boundary_curves=len(cur), closed=not cur,
                              signed_volume_mm3=round(vol, 6), euler_chi=chi,
                              genus=gen, self_int_hits=si["n_hits"],
                              self_int_checked=bool(si["checked"])))
        n_ring = sum(1 for c in curves if c["is_planar_ring"])
        b_bud = _budget(BOUNDARY_CURVE_BUDGET, name, grp)
        nm_bud = _budget(NONMANIFOLD_EDGE_BUDGET, name, grp)
        bt_bud = _budget(BOWTIE_VERTEX_BUDGET, name, grp)
        du_bud = _budget(DUPLICATE_FACE_BUDGET, name, grp)
        si_bud = _budget(SELF_INTERSECT_BUDGET, name, grp)
        dg_bud = _budget(DEGENERATE_BUDGET, name, grp)
        #  ⚠ 자기교차를 **안 돌렸으면**(self_int=False) 그 축은 «0» 이 아니라 «모름» 이다.
        #    그래서 값을 None 으로 싣고, ok 는 그 축을 주장하지 않는다(끈 사람이 아는 상태).
        ok = (len(curves) <= b_bud and ec["n_nonmanifold"] <= nm_bud
              and len(bt) <= bt_bud and dupf <= du_bud
              and ((si_hits <= si_bud and si_unchecked == 0) if self_int else True)
              and tq["n_repeat_index"] <= dg_bud and tq["n_zero_area"] <= dg_bud
              and tq["n_zero_edge"] <= dg_bud and ec["n_flipped"] == 0 and n_neg == 0)
        groups[grp] = dict(
            n_faces=int(len(f)), n_parts=int(npart), n_welded_verts=int(n_merged),
            #  T1 닫힘
            boundary_edges=ec["n_boundary"], boundary_curves=len(curves),
            boundary_curve_budget=b_bud, planar_ring_curves=n_ring,
            open_parts=n_open,
            #  T2 법선
            flipped_edges=ec["n_flipped"], negative_volume_parts=n_neg,
            #  T3 다양체
            nonmanifold_edges=ec["n_nonmanifold"], nonmanifold_budget=nm_bud,
            max_edge_multiplicity=ec["max_mult"],
            bowtie_vertices=int(len(bt)), bowtie_budget=bt_bud,
            bowtie_excluded_at_nonmanifold=bt_excl,
            duplicate_faces=dupf, duplicate_budget=du_bud,
            #  T4 자기교차 — 안 돌렸으면 hits 는 None(«모름»)이다
            self_int_checked=bool(self_int),
            self_int_hits=(si_hits if self_int else None), self_int_budget=si_bud,
            self_int_unchecked_parts=(si_unchecked if self_int else None),
            #  T5 퇴화
            repeat_index_faces=tq["n_repeat_index"], zero_area_faces=tq["n_zero_area"],
            zero_len_edges=tq["n_zero_edge"], slivers=tq["n_sliver"],
            min_angle_deg=round(float(tq["min_angle_deg"].min()), 5),
            p99_aspect=round(float(np.percentile(tq["aspect"][np.isfinite(tq["aspect"])], 99))
                             if np.isfinite(tq["aspect"]).any() else 0.0, 2),
            #  종수(선언 축 — 판정 안 함)
            genus_nonzero_parts=n_g,
            #  D1 이산화
            facet=facet_wavelength(V, F, lam),
            parts=parts if len(parts) <= 60 else parts[:60],
            ok=bool(ok),
        )
        tot["parts"] += npart; tot["boundary_curves"] += len(curves)
        tot["nonmanifold"] += ec["n_nonmanifold"]; tot["bowtie"] += int(len(bt))
        tot["dup_faces"] += dupf
        if self_int:
            tot["selfint"] += si_hits
            tot["selfint_unchecked"] += si_unchecked
        else:
            tot["selfint"] = tot["selfint_unchecked"] = None
        tot["repeat_index"] += tq["n_repeat_index"]; tot["zero_area"] += tq["n_zero_area"]
        tot["zero_edge"] += tq["n_zero_edge"]; tot["sliver"] += tq["n_sliver"]
        tot["flipped_edges"] += ec["n_flipped"]; tot["negative_volume_parts"] += n_neg
        tot["open_parts"] += n_open; tot["planar_ring_curves"] += n_ring
        tot["genus_nonzero_parts"] += n_g

    #  기체 전체의 이산화 지표 — 그룹별 면적 가중으로 합친다
    ar = np.array([g["facet"]["area_mm2"] for g in groups.values()], float)
    w = ar / max(ar.sum(), 1e-30)
    sag_pct = float(sum(w[i] * g["facet"]["sagitta_over_lam16_area_pct"]
                        for i, g in enumerate(groups.values())))
    edge_pct = float(sum(w[i] * g["facet"]["edge_over_lam7_area_pct"]
                         for i, g in enumerate(groups.values())))
    sag_bud = _budget(SAGITTA_AREA_PCT_BUDGET, name)
    edge_bud = _budget(FACET_EDGE_AREA_PCT_BUDGET, name)
    disc_ok = bool(sag_pct <= sag_bud)
    res = dict(name=name, fc_hz=float(fc), lam_mm=round(1000.0 * lam, 4),
               groups=groups, totals=tot,
               discretization=dict(
                   sagitta_over_lam16_area_pct=round(sag_pct, 5),
                   sagitta_budget_pct=sag_bud,
                   edge_over_lam7_area_pct=round(edge_pct, 4),
                   edge_budget_pct=edge_bud,
                   max_edge_mm=round(max(g["facet"]["max_edge_mm"] for g in groups.values()), 4),
                   max_edge_over_lam=round(max(g["facet"]["max_edge_over_lam"]
                                               for g in groups.values()), 5),
                   max_sagitta_mm=round(max(g["facet"]["max_sagitta_mm"] for g in groups.values()), 5),
                   ok=disc_ok),
               ok=bool(all(g["ok"] for g in groups.values()) and disc_ok))
    if verbose:
        print(report(res))
    return res


def report(res: dict) -> str:
    L = [f"  [{res['name']}]  λ = {res['lam_mm']:.2f} mm @ {res['fc_hz']/1e9:.2f} GHz",
         f"  {'그룹':9s} {'면':>6} {'부품':>4} {'경계곡선':>8} {'비다양체':>8} "
         f"{'나비넥타이':>10} {'중복면':>6} {'자기교차':>8} {'퇴화':>5} "
         f"{'최대변/λ':>9} {'사지타%':>8}  판정"]
    for g, v in res["groups"].items():
        f = v["facet"]
        si = ("모름" if v["self_int_hits"] is None
              else f"{v['self_int_hits']}/{v['self_int_budget']}")
        L.append(f"  {g:9s} {v['n_faces']:6d} {v['n_parts']:4d} "
                 f"{str(v['boundary_curves'])+'/'+str(v['boundary_curve_budget']):>8s} "
                 f"{v['nonmanifold_edges']:8d} {v['bowtie_vertices']:10d} "
                 f"{v['duplicate_faces']:6d} "
                 f"{si:>8s} "
                 f"{v['repeat_index_faces']+v['zero_area_faces']+v['zero_len_edges']:5d} "
                 f"{f['max_edge_over_lam']:9.3f} {f['sagitta_over_lam16_area_pct']:8.3f}"
                 f"  {'✅' if v['ok'] else '❌'}")
    d = res["discretization"]
    L.append(f"  이산화(면적가중): 사지타>λ/16 {d['sagitta_over_lam16_area_pct']} % "
             f"(예산 {d['sagitta_budget_pct']} %) · 변>λ/7 {d['edge_over_lam7_area_pct']} % "
             f"(참고) · 최대변 {d['max_edge_mm']} mm = {d['max_edge_over_lam']}λ  "
             f"{'✅' if d['ok'] else '❌'}")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
#  D2 · D3 — 로프트 스플라인 오버슛 · 끝단 캡 (빌더 **계측**)
# --------------------------------------------------------------------------- #
def _spline_overshoot(xs, y, n=401):
    """3차 스플라인이 **이웃 제어점의 상자 밖으로** 나가는 양.
    구간 [x_i, x_{i+1}] 에서 y(x) 가 max(y_i, y_{i+1}) 를 넘거나 min 아래로 내려가면 오버슛이다.
    (전 구간의 max 를 쓰지 않는 이유: 정상적인 봉우리를 오버슛으로 오인하지 않기 위해서다.)
    반환: (절대 오버슛, 상대 %[진폭 대비], 스플라인 전체 최소값)"""
    from scipy.interpolate import CubicSpline
    xs = np.asarray(xs, float); y = np.asarray(y, float)
    cs = CubicSpline(xs, y)
    span = float(y.max() - y.min())
    worst, ymin = 0.0, float(y.min())
    for i in range(len(xs) - 1):
        xx = np.linspace(xs[i], xs[i + 1], n)
        yy = cs(xx)
        hi, lo = max(y[i], y[i + 1]), min(y[i], y[i + 1])
        worst = max(worst, float(yy.max() - hi), float(lo - yy.min()))
        ymin = min(ymin, float(yy.min()))
    return worst, (100.0 * worst / span if span > 0 else 0.0), ymin


def section_extent(V, F, x_plane, tol=None):
    """평면 x = x_plane 으로 **잘라낸 단면**의 반폭(y)·반높이(z) [m].

    ⚠ 왜 «얇은 판을 떠서 재기» 가 아니라 «잘라 재기» 인가 — 판 두께를 얼마로 잡느냐에 따라
      답이 통째로 달라지기 때문이다(2026-08-16 실측: matrice4e 스무딩판의 기수 반폭이 판
      두께 0.1 %/1 %/5 % 에서 **0.0 / 38.6 / 41.2 mm**). 자르기에는 그런 손잡이가 없다.
    평면 위에 **정확히 놓인** 정점도 같이 센다 — 로프트 끝단 링이 바로 그 경우다."""
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    d = V[:, 0] - float(x_plane)
    tol = float(tol) if tol is not None else 1e-9 * max(float(np.ptp(V[:, 0])), 1e-12)
    pts = [V[np.abs(d) <= tol]]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = F[:, i], F[:, j]
        da, db = d[a], d[b]
        sel = ((da > tol) & (db < -tol)) | ((da < -tol) & (db > tol))
        if sel.any():
            t = (da[sel] / (da[sel] - db[sel]))[:, None]
            pts.append(V[a[sel]] + t * (V[b[sel]] - V[a[sel]]))
    P = np.vstack([p for p in pts if len(p)]) if any(len(p) for p in pts) else None
    if P is None or not len(P):
        return None
    return (0.5 * float(P[:, 1].max() - P[:, 1].min()),
            0.5 * float(P[:, 2].max() - P[:, 2].min()))


def _end_station(Vm, Fm, L):
    """로프트 셸의 **설계 끝단 평면** x = ∓L/2 에서 잰 (반폭, 반높이) 두 쌍.
    `_body_folding` 의 xs = (−0.50 … +0.50)·L 규약을 그대로 쓴다."""
    return [section_extent(Vm, Fm, -0.5 * L), section_extent(Vm, Fm, +0.5 * L)]


def instrumented_build(spec):
    """⭐빌더를 **계측**하며 기체 한 대를 짓는다 — `spline_sections` · `loft` · `sweep` ·
    `_body_folding` 호출을 그대로 기록한다.

    왜 이렇게 하나: 「이 기체가 로프트 셸을 쓰는가」를 알려면 빌더의 분기 조건을 베껴 써야
    하는데, 베낀 조건은 **빌더가 바뀌면 조용히 틀려진다**(이 저장소가 이미 여러 번 물린 함정).
    호출을 직접 보면 베낄 것이 없다. 안 불렸으면 «해당 없음» 이라고 적는다 — 추측하지 않는다.

    ⚠ 패치는 이 함수 안에서만 살아 있고 `finally` 로 반드시 되돌린다. 형상은 안 바뀐다."""
    import drone_cad as dc
    from drones import build_drone
    rec = dict(spline=[], loft=[], sweep=[], body=[])
    o_spline, o_loft, o_sweep, o_body = (dc.spline_sections, dc.loft, dc.sweep, dc._body_folding)

    def p_spline(xs, half_w, half_h, z_off=None, **kw):
        out = o_spline(xs, half_w, half_h, z_off, **kw)
        e = dict(n_ctrl=len(xs), n_sec=len(out), n_pts=int(kw.get("n_pts", 64)),
                 n_pow=float(kw.get("n_pow", 2.6)))
        for tag, y in (("hw", half_w), ("hh", half_h), ("zo", z_off)):
            if y is None:
                continue
            a, r, ymin = _spline_overshoot(xs, y)
            e[f"{tag}_overshoot_mm"] = round(1000.0 * a, 5)
            e[f"{tag}_overshoot_pct"] = round(r, 3)
            e[f"{tag}_spline_min_mm"] = round(1000.0 * ymin, 5)
        #  하한 클램프(superellipse 의 max(1e-4, ·))에 닿은 스테이션 수
        e["clamped_sections"] = int(sum(1 for (_x, _p) in out if _p.bounds[2] - _p.bounds[0] <= 2e-4))
        rec["spline"].append(e)
        return out

    def p_loft(sections, n_pts=48, cap=True):
        m = o_loft(sections, n_pts=n_pts, cap=cap)
        ec = edge_census(np.asarray(m.faces, np.int64))
        rec["loft"].append(dict(n_sections=len(sections), n_pts=int(n_pts), cap=bool(cap),
                                faces=int(len(m.faces)), boundary_edges=ec["n_boundary"],
                                nonmanifold_edges=ec["n_nonmanifold"]))
        return m

    def p_sweep(path, profile_fn, n_pts=24, cap=True):
        m = o_sweep(path, profile_fn, n_pts=n_pts, cap=cap)
        ec = edge_census(np.asarray(m.faces, np.int64))
        rec["sweep"].append(dict(n_path=len(path), n_pts=int(n_pts), cap=bool(cap),
                                 faces=int(len(m.faces)), boundary_edges=ec["n_boundary"]))
        return m

    def p_body(L, W, H, nose_drop=0.18, tail_w=0.95, n_pow=2.9,
               hw_f=None, hh_f=None, zo_f=None, smooth_iters=4):
        m = o_body(L, W, H, nose_drop=nose_drop, tail_w=tail_w, n_pow=n_pow,
                   hw_f=hw_f, hh_f=hh_f, zo_f=zo_f, smooth_iters=smooth_iters)
        #  설계표의 끝단 스테이션(양 끝) — `_body_folding` 이 쓰는 식 그대로
        hwf = np.asarray(hw_f if hw_f is not None else (0.30, 0.46, 0.50, 0.44, 0.28, 0.10), float)
        hhf = np.asarray(hh_f if hh_f is not None else (0.30, 0.46, 0.50, 0.46, 0.34, 0.16), float)
        want = [(float(hwf[0] * W * tail_w), float(hhf[0] * H)),
                (float(hwf[-1] * W * tail_w), float(hhf[-1] * H))]
        got = _end_station(np.asarray(m.vertices, float), np.asarray(m.faces, np.int64), L)
        ends = []
        for i, (nm) in enumerate(("tail(x−)", "nose(x+)")):
            if got[i] is None:                      # 설계 평면에 메쉬가 아예 없다 = 완전 손실
                ends.append(dict(end=nm, want_hw_mm=round(1000 * want[i][0], 3),
                                 got_hw_mm=None, want_hh_mm=round(1000 * want[i][1], 3),
                                 got_hh_mm=None, hw_deficit_pct=-100.0, hh_deficit_pct=-100.0))
                continue
            dw = 100.0 * (got[i][0] / want[i][0] - 1.0) if want[i][0] > 0 else 0.0
            dh = 100.0 * (got[i][1] / want[i][1] - 1.0) if want[i][1] > 0 else 0.0
            ends.append(dict(end=nm,
                             want_hw_mm=round(1000 * want[i][0], 3), got_hw_mm=round(1000 * got[i][0], 3),
                             want_hh_mm=round(1000 * want[i][1], 3), got_hh_mm=round(1000 * got[i][1], 3),
                             hw_deficit_pct=round(dw, 3), hh_deficit_pct=round(dh, 3)))
        ec = edge_census(np.asarray(m.faces, np.int64))
        rec["body"].append(dict(L_mm=round(1000 * L, 3), W_mm=round(1000 * W, 3),
                                H_mm=round(1000 * H, 3), smooth_iters=int(smooth_iters),
                                n_pow=float(n_pow), tail_w=float(tail_w),
                                faces=int(len(m.faces)), boundary_edges=ec["n_boundary"],
                                ends=ends,
                                max_abs_deficit_pct=round(max(abs(e["hw_deficit_pct"]) for e in ends)
                                                          if ends else 0.0, 3)))
        return m

    try:
        dc.spline_sections, dc.loft, dc.sweep, dc._body_folding = p_spline, p_loft, p_sweep, p_body
        mesh = build_drone(spec)
    finally:
        dc.spline_sections, dc.loft, dc.sweep, dc._body_folding = o_spline, o_loft, o_sweep, o_body
    return mesh, rec


def check_loft_caps(spec, rec=None, verbose=False) -> dict:
    """D2 로프트 오버슛 + D3 끝단 캡 — 계측 기록을 판정한다.

    판정 셋:
      ⑴ **캡 손실** — `cap=True` 로 부른 로프트/스윕의 결과에 경계 모서리가 있으면 실패
        (캡을 만들라고 했는데 안 닫혔다는 뜻).
      ⑵ **끝단 단면 손실** — 로프트 셸의 양 끝 단면이 설계표에서 몇 % 벗어났나.
      ⑶ **스플라인 오버슛** — 3차 보간이 제어점 상자 밖으로 나간 양(진폭 대비 %) + 하한 클램프."""
    if rec is None:
        _, rec = instrumented_build(spec)
    key = spec.key
    lofts = rec["loft"] + rec["sweep"]
    cap_bad = [d for d in lofts if d["cap"] and d["boundary_edges"] > 0]
    nocap = [d for d in lofts if not d["cap"]]
    #  ⚠ **«해당 없음» 을 0 으로 보고하지 않는다**(저장소 규약: 못 봄을 통과로 만들지 마라).
    #    열린 프레임(x500v2)·전용 분기 기체(s1000plus·typhoonh480·m350rtk)는 `_body_folding`
    #    을 아예 안 부른다 → 끝단 손실은 **잴 대상이 없다** → None 으로 싣고 checked=False.
    ov_vals = [max(d.get(f"{t}_overshoot_pct", 0.0) for t in ("hw", "hh", "zo"))
               for d in rec["spline"]]
    clamp = sum(int(d.get("clamped_sections", 0)) for d in rec["spline"])
    defc = [b["max_abs_deficit_pct"] for b in rec["body"]]
    ov_bud = _budget(LOFT_OVERSHOOT_PCT_BUDGET, key)
    cl_bud = _budget(LOFT_CLAMP_BUDGET, key)
    cap_bud = _budget(CAP_DEFICIT_PCT_BUDGET, key)
    ov_max = round(float(max(ov_vals)), 3) if ov_vals else None
    df_max = round(float(max(defc)), 3) if defc else None
    res = dict(key=key,
               n_loft_calls=len(rec["loft"]), n_sweep_calls=len(rec["sweep"]),
               n_spline_calls=len(rec["spline"]), n_body_calls=len(rec["body"]),
               cap_checked=bool(lofts), cap_requested_but_open=len(cap_bad),
               cap_not_requested=len(nocap),
               overshoot_checked=bool(ov_vals),
               max_overshoot_pct=ov_max, overshoot_budget_pct=ov_bud,
               clamped_sections=clamp, clamp_budget=cl_bud,
               end_deficit_checked=bool(defc),
               max_end_deficit_pct=df_max, end_deficit_budget_pct=cap_bud,
               body=rec["body"], spline=rec["spline"],
               loft_shapes=[dict(n_sections=d["n_sections"], n_pts=d["n_pts"], cap=d["cap"],
                                 boundary_edges=d["boundary_edges"]) for d in rec["loft"][:6]],
               checked=bool(lofts or rec["spline"]))
    res["ok"] = bool(len(cap_bad) == 0 and clamp <= cl_bud
                     and (ov_max is None or ov_max <= ov_bud)
                     and (df_max is None or df_max <= cap_bud))
    if verbose:
        na = "해당없음"
        print(f"  로프트/캡: loft {res['n_loft_calls']} · sweep {res['n_sweep_calls']} · "
              f"cap 요청했는데 열림 {res['cap_requested_but_open']} · "
              f"끝단손실 {na if df_max is None else f'{df_max} %'} (예산 {cap_bud}) · "
              f"오버슛 {na if ov_max is None else f'{ov_max} %'} (예산 {ov_bud}) · "
              f"클램프 {clamp}  {'✅' if res['ok'] else '❌'}")
    return res


# --------------------------------------------------------------------------- #
#  2층 — 전 기종 · 게이트 · 지문
# --------------------------------------------------------------------------- #
def fingerprint(res: dict) -> str:
    """⭐**회귀 봉인용 지문** — 위상·이산화 불변량만 모아 sha256. 형상이 바뀌면 값이 바뀐다.
    ⚠ 이 지문은 «옳음» 의 증명이 아니라 «안 바뀜» 의 증명이다.
    ⚠ 자기교차를 끄고(`self_int=False`) 만든 지문은 **다른 값**이다 — 문자열에 `si=` 로 박아
      둬서 «반쪽 지문» 이 온전한 지문 자리에 섞이지 않게 한다."""
    import hashlib
    si_on = all(v.get("self_int_checked", True) for v in res["groups"].values())
    parts = [f"{res['name']}|fc={res['fc_hz']:.0f}|si={'on' if si_on else 'off'}"]
    for g, v in sorted(res["groups"].items()):
        f = v["facet"]
        parts.append("|".join(str(x) for x in [
            g, v["n_faces"], v["n_parts"], v["boundary_edges"], v["boundary_curves"],
            v["nonmanifold_edges"], v["bowtie_vertices"], v["duplicate_faces"],
            v["self_int_hits"], v["repeat_index_faces"], v["zero_area_faces"],
            v["zero_len_edges"], v["slivers"], v["genus_nonzero_parts"],
            f["max_edge_mm"], f["sagitta_over_lam16_area_pct"], f["area_mm2"]]))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


def check_all(fc=FC_DEFAULT_HZ, self_int=True, verbose=True, keys=None) -> dict:
    """DRONES 레지스트리 전수 — T1~T5 · D1 · D2 · D3."""
    from drones import DRONES
    out = {}
    for k, s in DRONES.items():
        if keys and k not in keys:
            continue
        mesh, rec = instrumented_build(s)
        r = check_topology(mesh, k, fc=fc, self_int=self_int)
        r["loft_caps"] = check_loft_caps(s, rec=rec)
        r["fingerprint"] = fingerprint(r)
        r["ok"] = bool(r["ok"] and r["loft_caps"]["ok"])
        out[k] = r
        if verbose:
            print(f"\n[{k}]  {'✅ 통과' if r['ok'] else '❌ 결함'}")
            print(report(r))
            check_loft_caps(s, rec=rec, verbose=True)
            print(f"  지문 {r['fingerprint']}")
    return out


def assert_ok(fc=FC_DEFAULT_HZ, self_int=True):
    """게이트 — 위상·이산화에 예산 초과가 있으면 예외를 던진다."""
    res = check_all(fc=fc, self_int=self_int, verbose=False)
    bad = {}
    for k, r in res.items():
        if r["ok"]:
            continue
        why = [f"{g}: " + ", ".join(
            n for n, c in (
                ("경계곡선", v["boundary_curves"] > v["boundary_curve_budget"]),
                ("비다양체", v["nonmanifold_edges"] > v["nonmanifold_budget"]),
                ("나비넥타이", v["bowtie_vertices"] > v["bowtie_budget"]),
                ("중복면", v["duplicate_faces"] > v["duplicate_budget"]),
                ("자기교차", (v["self_int_hits"] or 0) > v["self_int_budget"]),
                ("자기교차 미검사", v["self_int_unchecked_parts"] > 0),
                ("퇴화", v["repeat_index_faces"] + v["zero_area_faces"] + v["zero_len_edges"] > 0),
                ("감김뒤집힘", v["flipped_edges"] > 0),
                ("법선안쪽", v["negative_volume_parts"] > 0)) if c)
            for g, v in r["groups"].items() if not v["ok"]]
        if not r["discretization"]["ok"]:
            why.append(f"사지타>λ/16 면적 {r['discretization']['sagitta_over_lam16_area_pct']} % > "
                       f"{r['discretization']['sagitta_budget_pct']} %")
        if not r["loft_caps"]["ok"]:
            lc = r["loft_caps"]
            why.append(f"로프트/캡(열린캡 {lc['cap_requested_but_open']} · 끝단손실 "
                       f"{lc['max_end_deficit_pct']} % · 오버슛 {lc['max_overshoot_pct']} % · "
                       f"클램프 {lc['clamped_sections']})")
        bad[k] = why
    if bad:
        raise AssertionError(f"위상·이산화 검증 실패 — {bad}\n"
                             f"  PYTHONPATH=src python src/mesh_topo_check.py 로 상세 확인")
    return True


def check_seal(cert_path=None, fc=FC_DEFAULT_HZ) -> dict:
    """⭐**회귀 봉인 확인** — 인증서에 적힌 기종별 지문과 «지금 메쉬» 의 지문을 견준다.

    쓰임새: 형상을 바꾸는 라운드가 지나간 뒤 «무엇이 바뀌었나» 를 한 줄로 안다.
    ⚠ 불일치가 곧 결함은 아니다 — 형상을 **의도적으로** 바꿨으면 인증서를 다시 돌리는 것이
      정상 절차다. 이 함수가 잡는 것은 «모르는 사이에 바뀐 것» 이다."""
    import json
    p = cert_path or os.path.join(os.path.dirname(_HERE), "outputs",
                                  "mesh_cert_topology_discretization_0816.json")
    if not os.path.exists(p):
        return dict(ok=False, reason=f"인증서가 없다: {p}")
    with open(p) as fh:
        cert = json.load(fh)
    want = cert.get("regression_seal", {}).get("per_airframe", {})
    from drones import DRONES
    rows, bad = {}, []
    for k, s in DRONES.items():
        mesh, _rec = instrumented_build(s)
        got = fingerprint(check_topology(mesh, k, fc=fc, self_int=True))
        rows[k] = dict(want=want.get(k), got=got, same=bool(want.get(k) == got))
        if not rows[k]["same"]:
            bad.append(k)
    return dict(ok=not bad, cert=p, changed=bad, per_airframe=rows,
                cert_generated=cert.get("_meta", {}).get("generated_kst"))


if __name__ == "__main__":
    argv = sys.argv[1:]

    def _arg(name, default=None):
        for i, a in enumerate(argv):
            if a == name and i + 1 < len(argv):
                return argv[i + 1]
            if a.startswith(name + "="):
                return a.split("=", 1)[1]
        return default

    fc = float(_arg("--fc", FC_DEFAULT_HZ))
    keys = [s for s in (_arg("--drone", "") or "").split(",") if s] or None
    si = "--no-selfint" not in argv

    if "--check-seal" in argv:                 # 회귀 봉인만 확인하고 끝낸다
        r = check_seal(_arg("--check-seal") if _arg("--check-seal", "").startswith("/") else None,
                       fc=fc)
        if "reason" in r:
            print(f"⛔ {r['reason']}")
            sys.exit(1)
        print(f"회귀 봉인 대조 — 인증서 {r['cert']} ({r['cert_generated']})")
        for k, v in r["per_airframe"].items():
            print(f"  {'✅' if v['same'] else '⚠ 바뀜'} {k:12s} 인증서 {v['want']} ↔ 지금 {v['got']}")
        print(f"\n{'✅ 전 기종 동일' if r['ok'] else '⚠ 바뀐 기종: ' + ', '.join(r['changed'])}"
              f"  (바뀜 자체가 결함은 아니다 — 의도한 형상 변경이면 인증서를 다시 돌린다)")
        sys.exit(0 if r["ok"] else 2)
    print("=" * 118)
    print("위상·이산화 검사 — numpy/scipy 자체 위상 (trimesh 미사용) · 빌더 계측 로프트/캡")
    print(f"  주파수 {fc/1e9:.2f} GHz (λ = {1000*C0/fc:.2f} mm) · 자기교차 {'켬' if si else '끔'}")
    print("=" * 118)
    res = check_all(fc=fc, self_int=si, keys=keys)
    n_ok = sum(1 for r in res.values() if r["ok"])
    print(f"\n{'='*118}\n결과: {n_ok}/{len(res)} 통과")
    if "--json" in argv:
        import json
        p = _arg("--json")
        with open(p, "w") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1, default=float)
        print(f"  → {p}")
    sys.exit(0 if n_ok == len(res) else 1)
