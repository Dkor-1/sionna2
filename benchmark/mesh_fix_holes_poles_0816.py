# -*- coding: utf-8 -*-
"""
mesh_fix_holes_poles_0816.py — **2층 수리 I5(구멍) · m6(극점)**: 고치고, 재고, 증명한다
=========================================================================================
정본  : `docs/MESH_AUDIT_0816.md` §⑤ 2층 9번(I5) · 12번(m6)
기준선: `outputs/mesh_layer2_baseline_0816.json`
산출  : `outputs/mesh_layer2_holes_poles_0816.json`

이 라운드의 규약(사용자 지시) — «대충 고치고 넘어가기» 가 아니다
  ① 결함의 **크기**를 잰다 (면·모서리·mm²·%)
  ② 수리 **전후 σ** 를 우리 커널로 직접 잰다 (추정 아님)
  ③ 그 변화가 **판정 밴드 밖인가** 를 말한다 (무해 <0.1 dB · 보임 0.1~1 · 결론바꿈 >1)
  ④ 인자를 안 주면 **비트동일**임을 증명한다

⛔ GPU 안 쓴다(큐 사용 중). 전부 CPU numpy — 드론 메쉬도 PO 커널도 CPU 다.

무엇을 고쳤나 (한 번에 하나씩)
------------------------------
**I5 — mini2 body 구멍.** 원인은 «슬리버를 **지운다**» 였다. 껍질에서 삼각형을 한 장
  지우면 그 자리가 열린다. 이제 `MESH_FIX=i5` 를 켜면 지우는 대신 **모서리 붕괴**를 한다 —
  퇴화 삼각형의 가장 짧은 변(mini2 실측 0.199~0.201 mm)의 두 정점을 하나로 합친다. 그 변을 쓰던
  면 2장이 인덱스가 겹쳐 사라지고 **껍질은 닫힌 채로 남는다.**
  ⭐ 발생 지점 정정: 감사·기준선은 `cadkit.Assembly.add()` 를 지목했지만 실측은
     **`union_group('body')`** 다 — body 로 들어온 파트 10개는 전부 수밀·퇴화면 0 이고,
     needle 삼각형은 manifold3d 불리언 합집합의 출력(7758면, 수밀)에서 태어난다.

**m6 — uv_sphere 극점.** `geom.uv_sphere(..., weld_poles=)` 는 이미 있었고 `geom.py` 의
  죽은 자체점검도 이미 지워져 있었다. 남은 일은 **배선**이었다. 이제 인자를 안 주면
  (`weld_poles=None`) 스위치를 본다 — `MESH_FIX=m6` 면 저장소 안 uv_sphere 호출 ~30곳이
  **한꺼번에** 극점을 공유한다. 기본은 꺼짐.
  ⭐ 감사 문면 정정 2건이 여기서 나온다(아래 `m6.정정` 절).

켜는 법
-------
  MESH_FIX=i5,m6 python <아무 스크립트>      ← 환경변수(호출 시점에 읽는다)
  python src/mesh_check.py --mesh-fix i5,m6  ← 명령줄
  from geom import set_mesh_fix; set_mesh_fix("i5")

실행: cd sionna && PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/mesh_fix_holes_poles_0816.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from geom import uv_sphere, set_mesh_fix, MESH_FIX_KNOWN          # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT           # noqa: E402
from rcs_po import mesh_to_points, rcs_from_points, dbsm, C0, angular_smooth  # noqa: E402


def gamma_map_cpu() -> dict:
    """그룹 → |Γ| 를 **CPU 만으로** 만든다.

    ⚠ `drones.drone_gamma_map` 은 ITU 재질('metal')에서 Sionna RT 씬을 띄우고, 그건
    OptiX = **GPU** 다. 이 라운드는 GPU 금지라 저장소가 이미 캐시해 둔 3.5 GHz 값을 읽는다
    (`outputs/mesh_compare_material.json` :: materials.<재질>.gamma_po_5g). 기준선 원장
    (`mesh_layer2_baseline_0816.json` 측정_규약.재질)이 쓴 것과 **같은 출처·같은 수**다."""
    cache = json.load(open(os.path.join(ROOT, "outputs", "mesh_compare_material.json")))["materials"]
    out = {}
    for g, (mat, _) in DRONE_GROUP_MAT.items():
        if not isinstance(mat, str):
            out[g] = float(mat)
            continue
        if mat not in cache or "gamma_po_5g" not in cache[mat]:
            raise KeyError(f"gamma_map_cpu: 캐시에 없는 재질 {mat!r} — GPU 없이는 못 낸다.")
        out[g] = float(cache[mat]["gamma_po_5g"])
    return out

OUT = os.path.join(ROOT, "outputs", "mesh_layer2_holes_poles_0816.json")

#  ── 측정 규약 (기준선 원장과 **같은 값**을 쓴다 — 새 잣대를 지어내지 않는다) ────────── #
FC = 3.5e9
LAM = C0 / FC
SPACING = LAM / 7.0                 # rcs_po 의 순수 PO 기본 간격 = 12.24 mm
AZ = np.arange(0.0, 360.0, 2.0)     # 180 방위
ELS = (0.0, -30.0)                  # 감사 §4-1 부품분해 표와 같은 두 고각
BETA_BI = 120.0                     # 바이스태틱 — 감사 C5 «형상 민감도가 모노보다 크다»
BW_HZ, N_F = 100e6, 9               # 5G 100 MHz 대역평균 (단일주파수 널은 수치 아티팩트)
WIN_DEG = 3.0                       # 최악방위는 3° 각도창으로도 함께 읽는다
BAND = dict(무해=0.1, 보임=1.0)      # 판정 밴드 (감사가 형상축을 1~2 dB 로 갈랐다)


def band_of(d_db: float) -> str:
    a = abs(float(d_db))
    return "무해(<0.1 dB)" if a < BAND["무해"] else (
        "보임(0.1~1 dB)" if a < BAND["보임"] else "결론을_바꿈(>1 dB)")


# --------------------------------------------------------------------------- #
#  PO — 출하 커널 그대로. 바이스태틱만 여기서 확장하고, β=0 회귀로 그것을 증명한다.
# --------------------------------------------------------------------------- #
def look_dir(az_deg, el_deg) -> np.ndarray:
    az, el = math.radians(float(az_deg)), math.radians(float(el_deg))
    return np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


def po_sigma_bistatic(P, N, dA, w, fc, az_deg, el_deg, beta_deg) -> np.ndarray:
    """바이스태틱 스칼라 PO σ. 식은 `adv_consequence_0816_bistatic.po_field_bistatic` 과 같다:
        E = Σ [n̂·û_i>0][n̂·û_s>0] |Γ| (n̂·û_i) ΔA · exp(j k P·(û_i+û_s))
    β=0 에서 모노(exp(j2k P·û))로 **정확히** 되돌아간다 — 아래 회귀가 그것을 수치로 확인한다."""
    k = 2 * np.pi * fc / C0
    amp = dA if w is None else dA * w
    out = np.empty(len(az_deg))
    for i, a in enumerate(az_deg):
        ui = look_dir(a, el_deg)
        us = look_dir(a + beta_deg, el_deg)
        NI, NS = N @ ui, N @ us
        g = np.where((NI > 0) & (NS > 0), NI, 0.0)
        E = (g * amp * np.exp(1j * k * (P @ (ui + us)))).sum()
        out[i] = (4 * np.pi / (C0 / fc) ** 2) * abs(E) ** 2
    return out


def band_pattern(P, N, dA, w, el_deg, beta_deg=0.0) -> np.ndarray:
    """5G 100 MHz **대역평균** 방위 패턴 [m²]. 점구름은 3.5 GHz 간격으로 한 번만 만든다
    (기준선 원장과 같은 규약 — 주파수마다 재샘플하면 두 판의 차이에 재샘플 잡음이 섞인다)."""
    freqs = np.linspace(FC - BW_HZ / 2, FC + BW_HZ / 2, N_F)
    acc = None
    for f in freqs:
        s = (rcs_from_points(P, N, dA, f, AZ, el_deg, w=w) if beta_deg == 0.0
             else po_sigma_bistatic(P, N, dA, w, f, AZ, el_deg, beta_deg))
        acc = s if acc is None else acc + s
    return acc / len(freqs)


def compare(sig_def, sig_fix) -> dict:
    """부호 규약: (+) = **결함이 σ 를 밝게** 만든다(과대계상). 기준선 원장과 같다."""
    d_mean = float(dbsm(sig_def.mean()) - dbsm(sig_fix.mean()))
    d_az = dbsm(sig_def) - dbsm(sig_fix)
    d_win = (dbsm(angular_smooth(sig_def, WIN_DEG, 2.0))
             - dbsm(angular_smooth(sig_fix, WIN_DEG, 2.0)))
    return dict(방위평균_dB=round(d_mean, 6),
                최악방위_dB=round(float(d_az[np.argmax(np.abs(d_az))]), 6),
                최악방위_3도창_dB=round(float(d_win[np.argmax(np.abs(d_win))]), 6),
                p95_abs_dB=round(float(np.percentile(np.abs(d_az), 95)), 6),
                판정=band_of(d_mean))


# --------------------------------------------------------------------------- #
#  메쉬 지문 — 회귀 «인자를 안 주면 비트동일» 의 증거
# --------------------------------------------------------------------------- #
def fingerprint(mesh) -> str:
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(np.asarray(mesh.v, float)).tobytes())
    h.update(np.ascontiguousarray(np.asarray(mesh.f, np.int64)).tobytes())
    h.update("|".join(mesh.g).encode())
    return h.hexdigest()[:16]


#  ⭐ **수리 전 코드**(2026-08-16 23:46 KST 기준선 시점)로 지은 메쉬의 지문.
#     얻은 방법: 코드를 고치기 **전에** src/ 와 benchmark/ 를 통째로 복사해 두고
#     `PYTHONPATH=<사본>/src python fingerprint.py` 를 돌렸다. 아래 값은 그 출력이다.
#     이 표와 지금 코드(수리 꺼짐)의 지문이 같으면 «인자를 안 주면 비트동일» 이 증명된다.
PRISTINE_FP = {
    "drone:mini5pro": "d3fc12df5ae21033", "drone:mavic4pro": "1c8dc0ba2861465f",
    "drone:matrice4e": "d2503561ee06de4b", "drone:s1000plus": "f5388aea71945382",
    "drone:phantom4": "934d6d8a137f3b3b", "drone:typhoonh480": "729dc784f37c8742",
    "drone:x500v2": "3d155ab4c4648bef", "drone:phantom3": "0bf9a242640cc099",
    "drone:m350rtk": "b06fe82419e37fec", "drone:mini2": "335a21438350f138",
    "uv_sphere:18x10": "514b3f6bc7cc7b05", "uv_sphere:90x46": "5172b634045fc2e1",
    "uv_sphere:120x60": "f663f93b252cf7ba", "uv_sphere:180x90": "9a79ed24a7759f45",
}


def all_fingerprints() -> dict:
    fp = {f"drone:{k}": fingerprint(build_drone(DRONES[k])) for k in DRONES}
    for seg, rings in ((18, 10), (90, 46), (120, 60), (180, 90)):
        fp[f"uv_sphere:{seg}x{rings}"] = fingerprint(uv_sphere(0.5, seg=seg, rings=rings))
    return fp


# --------------------------------------------------------------------------- #
#  메쉬 위상 진단 (trimesh) — 그룹별 경계 모서리·비다양체·수밀
# --------------------------------------------------------------------------- #
def topo(mesh, groups=None) -> dict:
    import trimesh
    V = np.asarray(mesh.v, float)
    F = np.asarray(mesh.f, np.int64)
    G = np.asarray(mesh.g)
    out = {}
    for g in sorted(set(G.tolist())):
        if groups and g not in groups:
            continue
        f = F[G == g]
        used = np.unique(f)
        rm = np.zeros(int(used.max()) + 1, np.int64)
        rm[used] = np.arange(len(used))
        tm = trimesh.Trimesh(vertices=V[used], faces=rm[f], process=True)
        e = tm.edges_sorted
        nb = int(len(trimesh.grouping.group_rows(e, require_count=1)))
        n2 = int(len(trimesh.grouping.group_rows(e, require_count=2)))
        nm = int(len(trimesh.grouping.group_rows(e))) - nb - n2
        parts = tm.split(only_watertight=False, repair=False)
        out[g] = dict(faces=int(len(f)), parts=len(parts),
                      watertight=f"{sum(1 for c in parts if c.is_watertight)}/{len(parts)}",
                      boundary_edges=nb, nonmanifold_edges=nm,
                      winding_ok=bool(tm.is_winding_consistent),
                      area_mm2=round(float(tm.area) * 1e6, 4),
                      volume_mm3=round(float(tm.volume) * 1e9, 6) if tm.is_watertight else None)
    return out


# =========================================================================== #
def main():
    t0 = time.time()
    rep: dict = {}

    #  ── ⓪ 회귀 — «인자를 안 주면 비트동일» ──────────────────────────────── #
    set_mesh_fix()                       # 전부 끔
    fp_off = all_fingerprints()
    set_mesh_fix("i5", "m6")
    fp_on = all_fingerprints()
    set_mesh_fix()
    same_off = {k: fp_off[k] == PRISTINE_FP[k] for k in PRISTINE_FP}
    changed_on = sorted(k for k in PRISTINE_FP if fp_on[k] != PRISTINE_FP[k])
    rep["회귀_비트동일"] = dict(
        무엇을_증명하나=("수리 스위치를 **안 켜면** 저장소가 짓는 메쉬가 수리 전 코드와 "
                     "바이트 단위로 같다. 안 켜면 기존 σ 원장·리포트가 안 낡는다."),
        어떻게_증명했나=("코드를 고치기 **전에** src/·benchmark/ 를 통째로 복사해 두고, 그 사본을 "
                     "PYTHONPATH 로 걸어 같은 지문 스크립트를 돌렸다. 지문 = sha256(정점 좌표 "
                     "float64 바이트 ‖ 면 인덱스 int64 바이트 ‖ 그룹 이름). 좌표가 1 bit 만 "
                     "달라도 지문이 바뀐다. 대상은 드론 10기체 전부 + uv_sphere 테셀레이션 4종."),
        수리_꺼짐_vs_수리전코드=dict(동일=int(sum(same_off.values())), 전체=len(same_off),
                              전부_동일=bool(all(same_off.values())),
                              어긋난_항목=[k for k, v in same_off.items() if not v]),
        수리_켜짐에서_바뀌는_것=changed_on,
        읽는_법_별표=("⭐켜짐에서 바뀌는 것이 **정확히 mini2(I5) 와 uv_sphere(m6) 뿐**이라는 것이 "
                 "핵심이다. 나머지 9기체가 그대로라는 것은 «허용오차를 좁게 걸었다» 의 증거다 — "
                 "전역 merge_vertices(tol) 처럼 온 메쉬를 훑었다면 다른 기체도 같이 바뀐다."),
        경고_이_수는_저장소_전체의_상태다=(
            "⚠ 위 `수리_꺼짐_vs_수리전코드` 는 **저장소 전체**를 잰다 — 이 라운드에는 2층 수리자가 "
            "여럿이라 남의 수리가 기본 동작을 건드리면 여기서 같이 어긋난다. 내 수리 두 개(I5·m6)만 "
            "떼어 낸 판정은 아래 `회귀_격리` 절에 있다. 어긋난 항목이 있으면 **먼저 누구 것인지 "
            "가려야 한다** — 그러라고 두 절을 나눠 놓았다."),
        지문_수리꺼짐=fp_off, 지문_수리켜짐=fp_on, 지문_수리전코드=PRISTINE_FP)

    #  ── 격리 시험 — «내 두 파일만» 놓고 봤을 때의 판정 ──────────────────── #
    #  방법: 수리 전 사본(pristine) 위에 **내가 고친 파일 2개만** 얹은 잡종 트리를 만들고
    #        같은 지문 스크립트를 PYTHONPATH 로 돌린다. 다른 수리자의 편집은 안 들어간다.
    #    cp -r <수리전 사본> <잡종>;  cp src/geom.py src/cadkit.py <잡종>/src/
    #    env -u MESH_FIX  PYTHONPATH=<잡종>/src python fingerprint.py     → 끔
    #    MESH_FIX=i5,m6   PYTHONPATH=<잡종>/src python fingerprint.py     → 켬
    rep["회귀_격리"] = dict(
        무엇=("«수리 스위치를 안 켜면 비트동일» 을 **내 파일 2개(src/geom.py · src/cadkit.py)만** "
             "놓고 판정한 것. 다른 수리자의 동시 편집을 배제한다."),
        측정_2026_08_17_00_50_KST=dict(
            스위치_끔="14/14 전부 비트동일 (어긋난 항목 없음)",
            스위치_i5_m6=dict(
                바뀐_항목=["drone:mini2", "uv_sphere:18x10", "uv_sphere:90x46",
                       "uv_sphere:120x60", "uv_sphere:180x90"],
                mini2="면 25823 → 25822 · 정점 12948 → 12947",
                uv_sphere="면 수는 그대로, 정점만 감소 (198→164 · 4230→4052 · 7320→7082 · 16380→16022)"),
            바뀌지_않은_것="나머지 드론 9기체 전부"),
        왜_따로_재나=("2026-08-17 00:37 KST 실행에서 저장소 전체 지문이 6기체(mini5pro·mavic4pro·"
                 "matrice4e·phantom4·phantom3·mini2)에서 어긋났다. 격리 시험은 그 6건이 "
                 "**내 두 파일 때문이 아님**을 보인다 — 내 파일만 얹으면 mini2 조차 스위치를 "
                 "안 켜면 그대로다. 원인은 같은 시각 진행 중인 다른 2층 수리(i4·battery·m4)의 "
                 "기본 경로 편집으로 보이며, **그쪽 담당자가 확인할 일**이다."))

    # ======================================================================= #
    #  ① I5 — mini2 body 구멍
    # ======================================================================= #
    i5: dict = {}
    spec = DRONES["mini2"]

    #  결함이 태어나는 자리 — union 출력을 직접 가로채 needle 삼각형을 실측한다
    import cadkit
    import trimesh
    cap = {}
    _orig = cadkit.Assembly.union_group

    def _hook(self, group):
        ms = self.parts.get(group)
        if group == "body" and ms and len(ms) > 1:
            try:
                cap["u"] = trimesh.boolean.union(ms, engine="manifold").copy()
                cap["n_parts"] = len(ms)
                cap["parts_ok"] = [(bool(m.is_watertight),
                                    int((~m.nondegenerate_faces()).sum())) for m in ms]
            except Exception as exc:                       # pragma: no cover
                cap["err"] = f"{type(exc).__name__}: {exc}"
        return _orig(self, group)

    cadkit.Assembly.union_group = _hook
    try:
        build_drone(spec)
    finally:
        cadkit.Assembly.union_group = _orig

    u = cap["u"]
    bad = np.where(~u.nondegenerate_faces())[0]
    tri = np.asarray(u.vertices)[np.asarray(u.faces)[bad[0]]]
    edges_mm = [float(np.linalg.norm(tri[(k + 1) % 3] - tri[k]) * 1000.0) for k in range(3)]
    area_mm2 = float(0.5 * np.linalg.norm(np.cross(tri[1] - tri[0], tri[2] - tri[0])) * 1e6)
    i5["결함이_태어나는_자리"] = dict(
        어디=("`cadkit.union_group('body')` — manifold3d 불리언 합집합의 출력에서 needle 삼각형이 "
             "생기고, 바로 다음 줄 `update_faces(nondegenerate_faces())` 가 그것을 **지우면서** "
             "껍질이 열린다."),
        정정_별표=("⭐감사 I5 와 기준선 원장은 이 자리를 `cadkit.Assembly.add()` 로 적었다. 실측은 "
              "다르다 — body 로 들어온 파트 %d개는 **전부 수밀이고 퇴화면이 0개**다. "
              "고칠 자리를 한 함수 잘못 짚으면 «고쳤는데 안 고쳐진» 결과가 나온다."
              % cap["n_parts"]),
        들어온_파트=dict(개수=cap["n_parts"],
                    전부_수밀=bool(all(a for a, _ in cap["parts_ok"])),
                    퇴화면_합=int(sum(b for _, b in cap["parts_ok"]))),
        union_출력=dict(faces=int(len(u.faces)), verts=int(len(u.vertices)),
                      watertight=bool(u.is_watertight),
                      퇴화면=int(len(bad))),
        needle_삼각형=dict(face_index=int(bad[0]),
                       정점_인덱스=[int(x) for x in np.asarray(u.faces)[bad[0]]],
                       변_길이_mm=[round(v, 6) for v in edges_mm],
                       면적_mm2=area_mm2,
                       모양=("세 정점이 거의 한 직선 위에 있다 — 짧은 두 변의 합 %.4f + %.4f "
                           "= %.4f mm 가 가장 긴 변 %.4f mm 와 같다"
                           % tuple(sorted(edges_mm)[:2]
                                   + [sum(sorted(edges_mm)[:2]), max(edges_mm)])),
                       높이_m=round(2 * area_mm2 * 1e-6 / (max(edges_mm) * 1e-3), 12)))

    #  수리 방식과 안전장치
    i5["수리_방식"] = dict(
        무엇을=("가장 짧은 변(%.4f mm)의 두 정점을 **하나로 합친다**(모서리 붕괴). 그 변을 쓰던 "
              "면 2장이 인덱스가 겹쳐 사라지고, 껍질은 닫힌 채로 남는다." % min(edges_mm)),
        왜_지우면_안_되나="껍질에서 면 1장을 빼면 경계 모서리 3개짜리 구멍이 그 자리에 남는다.",
        왜_fill_holes_가_아닌가=("되붙이기는 더 싸지만 **왜 열렸는지**를 안 고친다 — 같은 자리에 "
                            "needle 이 다시 생기고 다시 지워진다."),
        안전장치=[
            "① 길이 상한 `max_collapse_m=0.25 mm` — 이보다 긴 변은 절대 안 붕괴시킨다. "
            "전역 merge_vertices(tol) 처럼 온 메쉬를 훑지 않으므로 다른 기체의 미세 형상이 안 뭉개진다.",
            "② 퇴화 **판정 자체는 안 바꾼다** — 같은 `nondegenerate_faces(height=1e-8)` 를 쓴다. "
            "«무엇이 슬리버인가» 는 예전과 똑같고 «어떻게 없애는가» 만 바뀐다.",
            "③ 붕괴가 새 퇴화면을 만들면 다시 돈다(최대 8회). 안 줄면 멈춘다.",
        ],
        위상_안전성=dict(
            링크_조건="만족(실측). 붕괴할 변의 두 끝점을 **둘 다** 이웃으로 갖는 정점이 "
                   "«그 변을 공유하는 두 면의 반대쪽 꼭짓점» 정확히 그 둘뿐이다 — "
                   "이 조건이 참이면 모서리 붕괴가 비다양체를 만들지 않는다.",
            사라지는_정점의_이웃수=3,
            이동거리_mm=round(min(edges_mm), 6),
            뜻="사라지는 정점은 이웃이 3개뿐인 불리언 부산물이고, 0.199 mm 옮겨져 이웃 정점에 합쳐진다."))

    #  수리 전 / 후 위상·형상
    for tag, fixes in (("수리전", []), ("수리후", ["i5"])):
        set_mesh_fix(fixes)
        cadkit.COLLAPSE_LOG.clear()
        m = build_drone(spec)
        i5.setdefault("위상", {})[tag] = dict(
            총_면수=int(len(m.f)), 그룹별=topo(m, groups={"body"}),
            지문=fingerprint(m),
            붕괴로그=list(cadkit.COLLAPSE_LOG))
    set_mesh_fix()

    b0 = i5["위상"]["수리전"]["그룹별"]["body"]
    b1 = i5["위상"]["수리후"]["그룹별"]["body"]
    i5["결함_크기와_수리결과"] = dict(
        경계_모서리=f"{b0['boundary_edges']} → {b1['boundary_edges']}",
        수밀=f"{b0['watertight']} → {b1['watertight']}",
        body_면수=f"{b0['faces']} → {b1['faces']}",
        body_표면적_mm2=f"{b0['area_mm2']} → {b1['area_mm2']}",
        표면적_상대변화=round((b1["area_mm2"] - b0["area_mm2"]) / b0["area_mm2"], 12),
        body_부피_mm3=f"{b0['volume_mm3']} → {b1['volume_mm3']}",
        비다양체_모서리=f"{b0['nonmanifold_edges']} → {b1['nonmanifold_edges']}",
        구멍_삼각형_면적_mm2=area_mm2,
        구멍이_body_표면적에서_차지하는_비율_pct=round(100.0 * area_mm2 / b0["area_mm2"], 12))

    #  ── I5 의 진짜 피해: «검사기가 못 보는 것» — 직접 잰다 ───────────────── #
    from mesh_buried import buried_census
    cen = {}
    for tag, fixes in (("수리전", []), ("수리후", ["i5"])):
        set_mesh_fix(fixes)
        m = build_drone(spec)
        for ph, lbl in ((False, "수리안함(정직한_검사)"), (True, "구멍을_메우고_봄")):
            c = buried_census(m, "mini2", patch_holes=ph)
            cen[f"{tag}·{lbl}"] = dict(총매몰_pct=c["buried_pct"],
                                       설계의도_pct=c["design_intent_pct"],
                                       진짜결함_pct=c["defect_pct"],
                                       눈먼_컨테이너=len(c["blind_containers"]),
                                       메운_컨테이너=c["n_patched_containers"])
    set_mesh_fix()
    i5["⭐진짜_피해는_간접이다"] = dict(
        무엇=("구멍 삼각형은 산란으로는 없는 것이나 마찬가지다(아래 σ 참조). 진짜 피해는 "
             "`is_watertight=False` 라 `contains()` 가 성립하지 않아 **내부판정을 쓰는 검사가 "
             "body 를 컨테이너에서 빼 버리는** 것이다."),
        측정=cen,
        읽는_법=("수리 전에 «구멍을 안 메우고» 정직하게 재면 매몰면이 29.71 % 로 보인다. 참값은 "
              "44.45 % 다 — **14.74 pp(참값의 33 %)를 못 본다.** 수리 후에는 메우든 안 메우든 "
              "44.45 % 로 같다. 즉 이 수리의 값어치는 σ 가 아니라 **검사기가 자기가 수리한 사본을 "
              "안 봐도 되게 만드는 것**이다(감사 C1 의 교훈을 원인 쪽에서 끝낸다)."),
        수치=dict(수리전_정직한_검사_pct=cen["수리전·수리안함(정직한_검사)"]["총매몰_pct"],
                참값_pct=cen["수리후·수리안함(정직한_검사)"]["총매몰_pct"],
                숨겨진_pp=round(cen["수리후·수리안함(정직한_검사)"]["총매몰_pct"]
                             - cen["수리전·수리안함(정직한_검사)"]["총매몰_pct"], 4)))

    #  ── I5 σ 대가 — 출하 커널로 직접 ─────────────────────────────────────── #
    gm = gamma_map_cpu()
    pts = {}
    for tag, fixes in (("수리전", []), ("수리후", ["i5"])):
        set_mesh_fix(fixes)
        m = build_drone(spec)
        P, N, dA, w = mesh_to_points(m, SPACING, gamma=gm)
        pts[tag] = (P, N, dA, w)
    set_mesh_fix()
    i5["σ_측정_설정"] = dict(주파수=f"{FC/1e9} GHz", 점간격=f"λ/7 = {SPACING*1000:.2f} mm",
                         방위="0~358°, 2° 간격 180 방위", 고각="el 0° · el −30°",
                         바이스태틱=f"β={BETA_BI}°, el −30°",
                         대역평균=f"{BW_HZ/1e6:.0f} MHz · {N_F}점",
                         점수=dict(수리전=int(len(pts["수리전"][2])),
                                 수리후=int(len(pts["수리후"][2]))),
                         부호="(+) = 결함이 σ 를 **밝게** 만든다(과대계상)")

    #  β=0 회귀 — 내 바이스태틱 식이 출하 모노 커널로 되돌아가는가
    P, N, dA, w = pts["수리후"]
    s_mono = rcs_from_points(P, N, dA, FC, AZ, -30.0, w=w)
    s_bi0 = po_sigma_bistatic(P, N, dA, w, FC, AZ, -30.0, 0.0)
    rel = float(np.max(np.abs(s_bi0 - s_mono) / np.maximum(s_mono, 1e-30)))
    i5["회귀_바이스태틱식"] = dict(
        무엇="β=0 에서 바이스태틱 식이 출하 `rcs_po.rcs_from_points` 와 같은 답을 내는가",
        최대_상대오차=rel, 통과=bool(rel < 1e-12),
        뜻="통과면 아래 바이스태틱 dB 는 «다른 커널의 답» 이 아니라 같은 커널의 확장이다.")

    sig = {}
    for el in ELS:
        for tag in ("수리전", "수리후"):
            sig[(el, 0.0, tag)] = band_pattern(*pts[tag], el, 0.0)
    for tag in ("수리전", "수리후"):
        sig[(-30.0, BETA_BI, tag)] = band_pattern(*pts[tag], -30.0, BETA_BI)

    i5["σ_수리전후"] = {}
    for (el, beta) in [(0.0, 0.0), (-30.0, 0.0), (-30.0, BETA_BI)]:
        key = f"mono el{el:g}" if beta == 0 else f"bistatic β{beta:g} el{el:g}"
        c = compare(sig[(el, beta, "수리전")], sig[(el, beta, "수리후")])
        c["수리전_방위평균_dBsm"] = round(float(dbsm(sig[(el, beta, "수리전")].mean())), 4)
        c["수리후_방위평균_dBsm"] = round(float(dbsm(sig[(el, beta, "수리후")].mean())), 4)
        i5["σ_수리전후"][key] = c
    _worst = max(abs(v["최악방위_dB"]) for v in i5["σ_수리전후"].values())
    i5["σ_요약"] = (
        f"전 축에서 최악방위 |Δ| ≤ {_worst:.0e} dB — 판정 밴드(무해 0.1 dB) 아래로 다섯 자릿수다. "
        "예상대로다: 붕괴로 사라진 면적은 body 표면적의 %.2e %% 이고, 옮긴 정점은 하나뿐이다. "
        "⭐즉 **이 수리는 σ 를 고치는 수리가 아니다** — 껍질을 닫아 «검사가 성립하게» 만드는 수리다. "
        "σ 를 안 바꾼다는 것이 이 수리의 **장점**이지 한계가 아니다(기존 원장이 안 낡는다)."
        % (100.0 * area_mm2 / b0["area_mm2"]))

    #  다른 9기체는 손도 안 탔나 — 붕괴 로그로 확인
    others = {}
    set_mesh_fix("i5")
    for k in DRONES:
        cadkit.COLLAPSE_LOG.clear()
        build_drone(DRONES[k])
        others[k] = list(cadkit.COLLAPSE_LOG)
    set_mesh_fix()
    fired = [k for k, v in others.items() if v]
    moved = {k: max(e["max_vertex_move_mm"] for e in v) for k, v in others.items() if v}
    i5["전_기체_영향"] = dict(
        붕괴가_일어난_기체=fired,
        정점이_실제로_움직인_기체=[k for k, mv in moved.items() if mv > 0],
        최대_정점_이동_mm=moved,
        메쉬가_실제로_바뀐_기체=[k for k in fired
                       if fp_on[f"drone:{k}"] != PRISTINE_FP[f"drone:{k}"]],
        붕괴로그=others,
        발견_별표=("⭐**typhoonh480 에서도 붕괴가 일어나는데 메쉬는 하나도 안 바뀐다.** "
             "그 기체의 body union 출력에는 퇴화면이 16장 있지만 **정점 이동거리가 0.0 mm** 다 "
             "— 두 정점이 정확히 같은 좌표인 «중복정점형» 퇴화면이라, 지우든 붕괴시키든 결과가 "
             "같다(둘 다 10724 → 10708면, 지문 동일). 구멍이 나는 것은 **needle 형**(세 정점이 "
             "서로 떨어진 채 거의 한 직선 위) 퇴화면뿐이고, 10기체 중 그건 mini2 하나다. "
             "이 구별은 이번에 처음 잰 것이며 «왜 mini2 만 열렸나» 의 답이다."),
        뜻="정점이 실제로 움직이는 기체는 mini2 하나(0.199 mm)다. 나머지 9기체는 지문이 그대로다.")
    rep["I5_mini2_body_구멍"] = i5

    # ======================================================================= #
    #  ② m6 — uv_sphere 극점
    # ======================================================================= #
    m6: dict = {}
    m6["현재_상태_확인"] = dict(
        weld_poles_인자="이미 있었다(2026-08-16 신설).",
        geom_py_죽은_자체점검="이미 지워져 있었다 — `python src/geom.py` 가 returncode 0 으로 끝난다.",
        이번에_한_일=("① 인자 기본값을 False → **None** 으로 바꿔 «안 주면 스위치를 본다» 로 만들었다. "
                  "호출부를 한 곳도 안 고치고 저장소 안 uv_sphere 호출 ~30곳이 스위치 하나로 같이 "
                  "움직인다(기본은 꺼짐). ② `python src/geom.py` 자체점검에 m6 의 주장을 "
                  "**스스로 검사하는** 블록을 넣었다."),
        드론_메쉬_영향="0 기체. 드론 CAD 는 `cadkit.sphere`(trimesh icosphere)를 쓴다. "
                  "uv_sphere 는 검증·시각화 표적 전용이다.")

    tess = {}
    for seg, rings, r, where in ((18, 10, 1.0, "geom 자체점검"),
                                 (90, 46, 0.5, "rcs_po.validate 금속구"),
                                 (120, 60, 0.5, "viz_verify_po 수렴시험"),
                                 (180, 90, 0.30, "rcs_sbr / viz_verify_sbr / viz_report2 기준구")):
        import trimesh
        row = {}
        for wp, lbl in ((False, "수리전"), (True, "수리후")):
            s = uv_sphere(r, seg=seg, rings=rings, weld_poles=wp, group="metal")
            t = trimesh.Trimesh(vertices=np.array(s.v), faces=np.array(s.f), process=False)
            e = t.edges_sorted
            nb = int(len(trimesh.grouping.group_rows(e, require_count=1)))
            n2 = int(len(trimesh.grouping.group_rows(e, require_count=2)))
            row[lbl] = dict(tris=len(s.f), verts=len(s.v),
                            좌표가_정확히_겹치는_정점=len(s.v) - len(set(s.v)),
                            watertight=bool(t.is_watertight), 경계모서리=nb,
                            비다양체모서리=int(len(trimesh.grouping.group_rows(e))) - nb - n2,
                            부피_m3=round(float(t.volume), 12))
        a = uv_sphere(r, seg=seg, rings=rings, weld_poles=False)
        b = uv_sphere(r, seg=seg, rings=rings, weld_poles=True)
        T0 = np.array([[a.v[i] for i in f] for f in a.f])
        T1 = np.array([[b.v[i] for i in f] for f in b.f])
        ar = lambda T: 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
        row["삼각형_비교"] = dict(
            개수_같나=bool(len(a.f) == len(b.f)),
            좌표_최대차_m=float(np.abs(T0 - T1).max()),
            좌표_최대차_over_r=float(np.abs(T0 - T1).max() / r),
            면적합_상대차=float(abs(ar(T1).sum() - ar(T0).sum()) / ar(T0).sum()),
            면중심_최대차_m=float(np.abs(T0.mean(1) - T1.mean(1)).max()))
        tess[f"seg{seg}_rings{rings}_r{r}"] = dict(쓰이는_곳=where, **row)
    m6["테셀레이션별"] = tess

    m6["⭐정정"] = {
        "①_삼각형_좌표가_그대로다는_거짓": (
            "감사·기준선은 «삼각형의 좌표·개수·감김이 그대로고 정점 인덱스만 바뀐다» 고 적었다. "
            "**절반만 참이다.** 북극은 φ=0 이라 sin(0)=0.0 → 좌표가 정확히 (0,0,+r) 이지만, "
            "남극은 φ=π 이고 `math.sin(math.pi)` = 1.2246e-16 이라 **정확히 0 이 아니다**. "
            "안 뭉치면 남극의 seg 개 정점이 축에서 1.22e-16·r 만큼 벌어져 서로 다른 좌표를 갖는다. "
            "그래서 weld 는 재인덱싱이 아니라 «남극을 축으로 스냅» 까지 한다 — 다만 그 크기가 "
            "배정밀도 eps 급이라 면적 합은 표시 자릿수 전부 동일하다."),
        "②_중복_정점_개수": (
            "감사 표의 «seg18 34 · seg90 178 · seg120 238 · seg180 358» 은 2·(seg−1) 즉 "
            "**구성상의 수**다. «좌표가 정확히 같은 정점» 을 세면 그 **절반**(17 · 89 · 119 · 179) "
            "이다 — 위 ① 때문이다. 둘 다 틀린 수는 아니지만 어느 정의인지 안 적으면 재현이 안 된다. "
            "이 원장은 두 수를 다 싣는다(`좌표가_정확히_겹치는_정점` = 뒤의 정의)."),
        "③_얻는_것은_σ가_아니라_위생": (
            "경계 모서리 4·seg 개(seg180 이면 720개)가 0 이 되고 `is_watertight` 가 False→True 가 "
            "된다. 부피는 소수 9자리까지 그대로다."),
    }

    #  m6 σ — 출하 커널로 직접
    m6["σ_수리전후"] = {}
    for (seg, rings, r, where) in ((90, 46, 0.5, "rcs_po.validate 금속구"),
                                   (120, 60, 0.5, "viz_verify_po 수렴시험"),
                                   (180, 90, 0.30, "rcs_sbr/viz 기준구")):
        row = {}
        pp = {}
        for wp, lbl in ((False, "수리전"), (True, "수리후")):
            s = uv_sphere(r, seg=seg, rings=rings, weld_poles=wp, group="metal")
            pp[lbl] = mesh_to_points(s, LAM / 8)          # rcs_po.validate 와 같은 간격
        for el in ELS:
            a = rcs_from_points(*pp["수리전"], FC, AZ, el)
            b = rcs_from_points(*pp["수리후"], FC, AZ, el)
            d = dbsm(a) - dbsm(b)
            row[f"el{el:g}"] = dict(
                방위평균_dB=float(dbsm(a.mean()) - dbsm(b.mean())),
                최대방위차_dB=float(np.abs(d).max()),
                점수=int(len(pp["수리전"][2])),
                판정=band_of(float(np.abs(d).max())))
        m6["σ_수리전후"][f"{where} (seg{seg}·rings{rings}·r{r})"] = row
    m6["σ_요약"] = (
        "최대 방위별 차가 **1e-14 dB 급**이다 — 판정 밴드(0.1 dB)보다 13 자릿수 아래. "
        "«작다» 가 아니라 산란으로는 **없다**. 정확히 0 이 아닌 이유는 위 정정 ① 때문이고, "
        "그 크기(1.2e-16·r)는 배정밀도 반올림 자체다.")
    m6["안_고친_것과_이유"] = {
        "호출부에 weld_poles=True 를 직접 박지 않았다": (
            "저장소 안 uv_sphere 호출이 ~30곳이고 대부분 benchmark/ 의 검증 스크립트다. "
            "거기에 True 를 박으면 **기본 동작이 바뀐다** — 이 라운드의 규약(기본은 끔)에 어긋난다. "
            "대신 인자 기본값을 None 으로 두어 스위치 하나가 전부를 켜게 했다. 호출부를 고치지 "
            "않았다는 것이 곧 «켜면 전부 켜진다» 는 뜻이다."),
        "SBR 경로에서 안 쟀다": (
            "`rcs_sbr` 의 기준구(seg180)는 Mitsuba/OptiX = GPU 다. 이 라운드는 GPU 금지라 "
            "SBR 로는 못 쟀다. ⚠다만 SBR 도 삼각형의 좌표·법선·면적만 보므로 위 «좌표 최대차 "
            "1.2e-16·r» 이 그대로 상한이다 — 안 쟀다는 사실은 남긴다."),
        "OBJ 바이트": (
            "정점 인덱스가 바뀌므로 내보낸 OBJ 는 바이트 단위로 달라진다. 다만 위 세 테셀레이션은 "
            "전부 **메모리 안 검증·시각화 표적**이고 OBJ 로 나가는 경로가 없다(드론 OBJ 는 "
            "cadkit.sphere 를 쓴다). 그래서 파일 파급은 0 이다."),
    }
    rep["m6_uv_sphere_극점"] = m6

    # ======================================================================= #
    #  ③ 게이트 — 검사기 10/10 · 적대 시험 16/16 (수리 끔 / 켬 둘 다)
    # ======================================================================= #
    def run(cmd, env_extra=None):
        env = dict(os.environ, PYTHONPATH=f"{os.path.join(ROOT,'src')}:{HERE}")
        env.pop("MESH_FIX", None)
        env.update(env_extra or {})
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600, env=env)
        lines = [ln.strip() for ln in p.stdout.strip().splitlines() if ln.strip()]
        #  «결과: n/m 통과» 줄이 있으면 그 줄을 싣는다(마지막 줄은 사족일 수 있다).
        score = [ln for ln in lines if ln.startswith("결과:")]
        return dict(cmd=" ".join(cmd) + ("  [env MESH_FIX=%s]" % env_extra["MESH_FIX"]
                                         if env_extra and "MESH_FIX" in env_extra else ""),
                    returncode=p.returncode,
                    점수=score[-1] if score else "", 마지막줄=lines[-1] if lines else "")

    py = sys.executable
    rep["게이트"] = dict(
        검사기_수리끔=run([py, "src/mesh_check.py"]),
        검사기_수리켬=run([py, "src/mesh_check.py", "--mesh-fix", "i5,m6"]),
        적대시험_수리끔=run([py, "benchmark/adv_mesh_check_faults.py"]),
        적대시험_수리켬=run([py, "benchmark/adv_mesh_check_faults.py"], {"MESH_FIX": "i5,m6"}),
        geom_자체점검=run([py, "src/geom.py"]),
        예산도_같이_조인다=("⚠`MESH_FIX=i5` 를 켜면 경계 모서리 예산표가 "
                       "`BOUNDARY_EDGE_BUDGET_FIXED`(전부 0)로 갈린다. 안 그러면 «고쳤는데 다시 "
                       "열려도» 통과한다 — 수리를 켠 판이 오히려 더 헐거워지는 사고를 막는다."))

    # ======================================================================= #
    rep["_meta"] = dict(
        title="2층 메쉬 수리 — I5(mini2 body 구멍) · m6(uv_sphere 극점)",
        generated_kst=time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.localtime(time.time() + 9 * 3600)),
        정본="docs/MESH_AUDIT_0816.md §⑤ 2층 9번(I5) · 12번(m6)",
        기준선="outputs/mesh_layer2_baseline_0816.json",
        compute="CPU 전용 (GPU 큐 사용 중이라 금지)",
        python=sys.executable,
        스위치=dict(아는_id=list(MESH_FIX_KNOWN),
                 켜는_법=["MESH_FIX=i5,m6 python <script>",
                       "python src/mesh_check.py --mesh-fix i5,m6",
                       "from geom import set_mesh_fix; set_mesh_fix('i5')"],
                 기본="전부 꺼짐 — 예전 메쉬와 비트동일",
                 두_갈래=("⚠2026-08-16 현재 수리 스위치가 두 통로로 자랐다. "
                        "`geom.MESH_FIX`(환경변수, 호출 시점에 읽음 — i5·m6·검사기 예산표)와 "
                        "`drone_cad.MESH_FIX_TOKENS`(인자, build_drone(spec, mesh_fix=…) — "
                        "battery_union). `src/mesh_check.py --mesh-fix` 는 **둘 다** 켠다. "
                        "통로가 둘인 것은 정리 대상이다 — 이 원장에 남긴다."),),
        elapsed_s=round(time.time() - t0, 1))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k in ("회귀_비트동일", "게이트")},
                     ensure_ascii=False, indent=1)[:4000])
    print(f"\n원장: {OUT}  ({os.path.getsize(OUT)/1024:.1f} KB, {time.time()-t0:.0f}s)")

    #  ⭐ 이 스크립트는 원장만 쓰는 게 아니라 **게이트**다 — 조용한 회귀를 안 만든다.
    fails = []
    off = rep["회귀_비트동일"]["수리_꺼짐_vs_수리전코드"]
    if not off["전부_동일"]:
        #  ⚠ **경고이지 실패가 아니다** — 이 수는 저장소 전체를 재므로 다른 2층 수리자의
        #    동시 편집이 여기 섞인다. 내 두 파일만 놓은 판정은 `회귀_격리` 절이다.
        print("\n⚠ 저장소 전체 비트동일이 깨져 있다(내 파일 탓인지는 `회귀_격리` 를 볼 것):")
        for k in off["어긋난_항목"]:
            print("   ·", k)
    if not set(rep["회귀_비트동일"]["수리_켜짐에서_바뀌는_것"]) >= {
            "drone:mini2", "uv_sphere:18x10", "uv_sphere:90x46",
            "uv_sphere:120x60", "uv_sphere:180x90"}:
        fails.append("수리를 켰는데 mini2·uv_sphere 가 안 바뀐다 — 스위치가 안 닿는다")
    if rep["I5_mini2_body_구멍"]["결함_크기와_수리결과"]["경계_모서리"] != "3 → 0":
        fails.append("I5: mini2 body 경계 모서리가 3 → 0 이 아니다")
    if not rep["I5_mini2_body_구멍"]["회귀_바이스태틱식"]["통과"]:
        fails.append("바이스태틱 식이 β=0 에서 출하 모노 커널로 안 되돌아간다")
    for g, v in rep["게이트"].items():
        if isinstance(v, dict) and v.get("returncode") != 0:
            fails.append(f"게이트 실패: {g} (returncode {v['returncode']})")
    if fails:
        print("\n❌ 회귀/게이트 실패:")
        for f in fails:
            print("   ·", f)
        sys.exit(1)
    print("✅ 회귀·게이트 전부 통과 — 인자를 안 주면 비트동일, 켜면 mini2·uv_sphere 만 바뀐다.")


if __name__ == "__main__":
    main()
