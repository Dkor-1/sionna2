# -*- coding: utf-8 -*-
"""
verify_frozen_grid.py — ⭐**얼린 광선 격자(`grid_ref`) 배선의 계약 검사**
==========================================================================
`outputs/sbr_grid_convergence.json` 이 밝힌 것: 슬로타임 스펙트럼의 광대역 바닥은 광선이
성겨서가 아니라 **자세마다 격자를 다시 정의해서** 생긴다(생산 팔 기울기 −0.55 R² 0.94 ↔
격자를 얼리면 −2.09 R² 0.987). 그래서 `rcs_sbr.sbr_field` / `sbr_field_bistatic` 에
keyword-only 인자 `grid_ref` 를 배선했다. 이 스크립트는 그 배선이 **약속한 대로만** 하는지를
숫자로 남긴다. 커널을 고치지 않는다 — 숫자가 안 맞으면 맞추지 말고 왜 다른지 적는다.

세 과녁
  [G1] **비트 동일 회귀** — `grid_ref=None` 은 배선 전(git HEAD 판) 과 **비트 단위로 같은가**.
       비교 상대를 재구현하지 않는다: `git show HEAD:src/rcs_sbr.py` 를 그대로 별도 모듈로
       올려 같은 프로세스에서 나란히 부른다. 여러 기체·주파수·자세·시선, 모노 + 바이스태틱.
       ⚠ 이게 통과해야 기존 원장(report07 계열)이 살아 있다고 말할 수 있다.
  [G2] **얼리면 정말 안 움직이는가** — 로터를 한 바퀴 돌리며 커널이 실제로 쓰는 격자
       (ctr·Rout·n) 를 `rcs_sbr.grid_used`(커널과 같은 `_grid_for` 를 부른다) 로 읽어
       자세에 따라 변하는지 직접 본다. 생산 팔은 변해야 하고(대조), 얼린 팔은 **한 톨도**
       변하면 안 된다. 더해서
         · 자세 하나로 만든 판을 그 자세에 주면 생산 격자와 **비트 동일** (판 공식이 같다는 증거)
         · 얼린 격자에서 모노 ↔ 바이스태틱(û_s=û_i) 이 여전히 겹치는가 (둘이 안 갈렸는가)
         · 독립 구현(benchmark/sbr_grid_convergence_md.py `_field_grid` — 원장을 만든 그 팔)과
           같은 값이 나오는가
  [G3] **덮개** — 얼린 격자가 **모든 자세**의 정점을 품는가. 판을 만들 때 안 넣은 자세까지
       포함해 여유[mm·칸]를 재고, 일부러 작게 만든 판에서는 커널이 **예외를 던지는지**까지
       확인한다(검사가 헛돌지 않는다는 증거).

원장:  outputs/verify_frozen_grid.json

실행:
    cd sionna2 && SIONNA2_GPU=2 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python \
        benchmark/verify_frozen_grid.py
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("SIONNA2_GPU", "2")      # ⭐사용자 지시(2026-08-10): 오늘은 GPU 2 만.

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (os.path.join(_ROOT, "src"), _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                      # noqa: E402

import rcs_sbr as rsb                                                   # noqa: E402
from rcs_sbr import (C0, _look, grid_ref_from, grid_ref_margin,          # noqa: E402
                     grid_used, sbr_field, sbr_field_bistatic)
from drones import DRONES, DRONE_GROUP_MAT, pose_articulated            # noqa: E402
from articulated_fast import FastPoser, rotor_phases                    # noqa: E402

OUT = os.path.join(_ROOT, "outputs", "verify_frozen_grid.json")
GM = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}

#  [G1] 사다리 — 4 기체 × 2 대역 × 3 자세 = **24 케이스**(모노). 바이스태틱은 그 중 16.
AIRFRAMES = ["mini5pro", "mavic4pro", "matrice4e", "s1000plus"]
BANDS = [1.8e9, 3.5e9]
LOOKS = [(0.0, -15.0), (37.0, 8.0), (-24.0, 6.0)]
PAD = 1.15                       # sbr_field 기본과 같다


def _iso():
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _bits(z):
    """복소수의 **비트 패턴** — 부동소수 비교가 아니라 바이트 비교를 한다."""
    return np.complex128(z).tobytes()


def _relerr(a, b):
    a, b = complex(a), complex(b)
    return float(abs(a - b) / abs(b)) if abs(b) > 0 else float(abs(a - b))


# ═══════════════════════════════════════════════════════════════════════════ #
#  배선 전 커널을 그대로 올린다 (재구현 금지 — git 이 갖고 있는 것을 쓴다)
# ═══════════════════════════════════════════════════════════════════════════ #
def load_baseline():
    """`git show HEAD:src/rcs_sbr.py` 를 별도 모듈로 import 해서 돌려준다.

    ⚠ 같은 프로세스 안이므로 mitsuba/drjit/씬 캐시 밖의 조건이 전부 같다 — 차이가 나면
      그건 배선 탓이지 환경 탓이 아니다."""
    src = subprocess.check_output(["git", "-C", _ROOT, "show", "HEAD:src/rcs_sbr.py"])
    scratch = os.environ.get("SIONNA2_SCRATCH") or tempfile.mkdtemp(prefix="rcs_sbr_base_")
    os.makedirs(scratch, exist_ok=True)
    path = os.path.join(scratch, "_rcs_sbr_head_baseline.py")
    with open(path, "wb") as fh:
        fh.write(src)
    import importlib.util
    spec = importlib.util.spec_from_file_location("rcs_sbr_head_baseline", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    head = subprocess.check_output(["git", "-C", _ROOT, "rev-parse", "HEAD"]).decode().strip()
    return mod, path, head


def _poses(spec):
    n = int(spec.num_rotors)
    yield "aligned", pose_articulated(spec, rotor_phase_deg=[0.0] * n)
    yield "spun", pose_articulated(spec, rotor_phase_deg=[37.2 + 9.1 * i for i in range(n)])
    yield "tilted", pose_articulated(spec, body_rpy=(4.0, -7.0, 23.0),
                                     rotor_phase_deg=[11.0 * i - 5.0 for i in range(n)])


# ═══════════════════════════════════════════════════════════════════════════ #
#  [G1] grid_ref=None 이 배선 전과 비트 동일인가
# ═══════════════════════════════════════════════════════════════════════════ #
def gate_bit_identity(base):
    cases = []
    t0 = time.time()
    icase = 0
    for key in AIRFRAMES:
        spec = DRONES[key]
        for pname, mesh in _poses(spec):
            for fc in BANDS:
                az, el = LOOKS[icase % len(LOOKS)]      # 시선도 케이스마다 돌린다
                icase += 1
                u = _look(az, el)
                ck = ("vfg", key, pname, round(fc / 1e6), az, el)
                E_new = complex(sbr_field(mesh, GM, fc, u, cache_key=ck))
                E_old = complex(base.sbr_field(mesh, GM, fc, u, cache_key=ck))
                row = dict(kind="mono", drone=key, pose=pname, fc_ghz=round(fc / 1e9, 3),
                           az=az, el=el, abs_new=abs(E_new), abs_old=abs(E_old),
                           rel_err=_relerr(E_new, E_old),
                           bit_identical=bool(_bits(E_new) == _bits(E_old)))
                #  바이스태틱도 같이 — 두 함수가 갈리면 안 된다. (기체 절반에서)
                if key in ("mavic4pro", "matrice4e"):
                    u_s = _look(az + 55.0, el + 12.0)
                    B_new = complex(sbr_field_bistatic(mesh, GM, fc, u, u_s, cache_key=ck))
                    B_old = complex(base.sbr_field_bistatic(mesh, GM, fc, u, u_s, cache_key=ck))
                    cases.append(dict(kind="bistatic", drone=key, pose=pname,
                                      fc_ghz=round(fc / 1e9, 3), az=az, el=el,
                                      beta_deg=float(np.degrees(np.arccos(
                                          np.clip(u @ u_s, -1, 1)))),
                                      abs_new=abs(B_new), abs_old=abs(B_old),
                                      rel_err=_relerr(B_new, B_old),
                                      bit_identical=bool(_bits(B_new) == _bits(B_old))))
                cases.append(row)
            rsb._SCENE_CACHE.clear()
            base._SCENE_CACHE.clear()
    by_kind = {}
    for k in sorted({c["kind"] for c in cases}):
        sub = [c for c in cases if c["kind"] == k]
        by_kind[k] = dict(n=len(sub), n_bit_identical=sum(c["bit_identical"] for c in sub),
                          max_rel_err=max(c["rel_err"] for c in sub))
    return dict(
        n_cases=len(cases), n_mono=by_kind.get("mono", {}).get("n", 0),
        n_bistatic=by_kind.get("bistatic", {}).get("n", 0),
        seconds=time.time() - t0,
        n_bit_identical=sum(c["bit_identical"] for c in cases),
        max_rel_err=max(c["rel_err"] for c in cases),
        by_kind=by_kind,
        passed=bool(all(c["bit_identical"] for c in cases)),
        cases=cases,
        note=("배선 전(git HEAD) 커널을 같은 프로세스에 올려 나란히 부른 결과. "
              "복소수 **바이트 비교**다 — 위상까지 한 비트도 안 달라야 한다."),
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  [G2]·[G3] 로터 한 바퀴 — 얼린 격자가 정말 안 움직이고 표적을 덮는가
# ═══════════════════════════════════════════════════════════════════════════ #
def gate_frozen(n_pose=64, n_build=16, n_field=8, drone=None, fc=None, az=None, el=None):
    """자세 사다리 하나에 [G2]·[G3] 를 같이 태운다 (씬을 아끼려고 한 루프로 묶었다)."""
    meta = json.load(open(os.path.join(_ROOT, "outputs", "report07_three_engines.json")))["_meta"]
    drone = drone or meta["drone"]
    fc = float(fc or meta["fc_hz"])
    az = float(meta["az_deg"] if az is None else az)
    el = float(meta["el_deg"] if el is None else el)
    prf = float(meta["prf_hz"])
    rpms = np.asarray(meta["rpm_per_rotor"], float)
    lam = C0 / fc
    d = lam / rsb.DEFAULT_DIV
    u = _look(az, el)

    fp = FastPoser(DRONES[drone])
    #  ⭐ 슬로타임 몇 스텝이 아니라 **가장 느린 로터가 한 바퀴 도는 시간**을 훑는다 — 그래야
    #     각 로터가 자기 위상 전 구간을 밟고, 합집합 bbox 가 «전 자세를 덮는다» 는 말이 참이 된다.
    #     (bbox 는 로터별 극값의 합집합이라, 각 로터가 한 바퀴만 돌면 조합은 따로 안 봐도 된다.)
    t_rev = 60.0 / float(np.min(rpms))
    tt = np.arange(n_pose) / n_pose * t_rev
    ph = rotor_phases(tt, rpms, fp.dirs)
    poses = [fp.pose(ph[i]) for i in range(n_pose)]

    #  판은 **일부 자세로만** 만든다 — 안 넣은 자세까지 덮는지가 [G3] 의 요점이다.
    build_idx = list(range(0, n_pose, max(1, n_pose // n_build)))
    ref = grid_ref_from([poses[i] for i in build_idx], fc, spacing=d, pad=PAD)

    prod, froz, cover = [], [], []
    for i, mv in enumerate(poses):
        gp = grid_used(mv, fc, u, spacing=d, pad=PAD)
        gf = grid_used(mv, fc, u, spacing=d, pad=PAD, grid_ref=ref)
        prod.append(gp)
        froz.append(gf)
        cover.append(grid_ref_margin(mv, u, ref, spacing=d))

    def _col(rows, key):
        return np.asarray([r[key] for r in rows], float)

    ctr_p = np.asarray([r["ctr"] for r in prod], float)
    ctr_f = np.asarray([r["ctr"] for r in froz], float)
    n_p = _col(prod, "n")
    n_f = _col(froz, "n")
    R_p = _col(prod, "Rout")
    R_f = _col(froz, "Rout")

    #  얼린 팔은 «변하지 않는다» 를 부동소수 오차 없이 본다 — 배열 바이트 비교.
    frozen_bit_const = bool(
        ctr_f.tobytes() == np.repeat(ctr_f[:1], n_pose, axis=0).tobytes()
        and n_f.tobytes() == np.full(n_pose, n_f[0]).tobytes()
        and R_f.tobytes() == np.full(n_pose, R_f[0]).tobytes())

    g2 = dict(
        n_pose=n_pose, n_build=len(build_idx), drone=drone, fc_ghz=round(fc / 1e9, 3),
        az_deg=az, el_deg=el, prf_hz=prf, spacing_mm=d * 1e3,
        sweep="가장 느린 로터 한 바퀴", sweep_ms=float(t_rev * 1e3),
        grid_ref=ref.asjson(),
        prod=dict(n_min=int(n_p.min()), n_max=int(n_p.max()),
                  n_changes=int((np.diff(n_p) != 0).sum()),
                  ctr_dot_u_ptp_mm=float(np.ptp(_col(prod, "ctr_dot_u")) * 1e3),
                  ctr_ptp_mm=[float(x) for x in np.ptp(ctr_p, axis=0) * 1e3],
                  Rout_ptp_mm=float(np.ptp(R_p) * 1e3),
                  n_rays_mean=float(_col(prod, "n_rays").mean())),
        frozen=dict(n=int(n_f[0]), n_changes=int((np.diff(n_f) != 0).sum()),
                    ctr_dot_u_ptp_mm=float(np.ptp(_col(froz, "ctr_dot_u")) * 1e3),
                    ctr_ptp_mm=[float(x) for x in np.ptp(ctr_f, axis=0) * 1e3],
                    Rout_ptp_mm=float(np.ptp(R_f) * 1e3),
                    n_rays=int(_col(froz, "n_rays")[0]),
                    bit_constant=frozen_bit_const),
        extra_ray_cost=float(_col(froz, "n_rays")[0] / _col(prod, "n_rays").mean()),
        #  ⚠ ctr_f 는 (n_pose, 3) 이다 — np.ptp 를 축 없이 부르면 «자세 사이 변화» 가 아니라
        #    x·y·z 를 뒤섞은 전역 폭이 나온다(첫 판에서 이걸로 헛 FAIL 을 냈다). 축을 준다.
        passed=bool(frozen_bit_const
                    and float(np.ptp(n_f)) == 0.0
                    and float(np.ptp(ctr_f, axis=0).max()) == 0.0
                    and float(np.ptp(R_f)) == 0.0),
        note=("커널이 실제로 쓰는 격자를 `rcs_sbr.grid_used`(= 커널과 같은 `_grid_for`) 로 읽었다. "
              "생산 팔의 흔들림은 대조군이다 — 그게 원장이 지목한 원인이다."),
    )

    m_min = np.asarray([c["margin_min_m"] for c in cover], float)
    off_build = [i for i in range(n_pose) if i not in set(build_idx)]
    g3 = dict(
        n_pose=n_pose, n_pose_not_in_ref=len(off_build),
        all_covered=bool(all(c["covered"] for c in cover)),
        margin_min_mm=float(m_min.min() * 1e3),
        margin_min_cells=float(min(c["margin_min_cells"] for c in cover)),
        margin_min_mm_poses_not_in_ref=float(min(m_min[i] for i in off_build) * 1e3)
        if off_build else None,
        worst_pose=int(np.argmin(m_min)),
        worst=cover[int(np.argmin(m_min))],
        passed=bool(all(c["covered"] for c in cover)),
        note=("가로 두 축은 광선 원점이 깔린 범위 ±(n−1)d/2, 세로는 광선 출발 평면 Rout 로 잰 "
              "여유다. 판을 만들 때 **안 넣은** 자세도 같이 검사한다."),
    )

    # ── 필드 수준 확인 (광선을 실제로 쏜다) ──────────────────────────────── #
    fidx = list(range(0, n_pose, max(1, n_pose // n_field)))[:n_field]
    rows = []
    for i in fidx:
        mv = poses[i]
        E_prod = complex(sbr_field(mv, GM, fc, u, spacing=d))
        E_froz = complex(sbr_field(mv, GM, fc, u, spacing=d, grid_ref=ref))
        #  ① 이 자세의 «생산 격자» 를 판으로 만들어 주면 생산 경로와 비트 동일이어야 한다
        #     (판 공식이 생산 공식과 같다 + grid_ref 가 실제로 격자를 몬다는 증거).
        self_ref = grid_ref_from(mv, fc, spacing=d, pad=PAD)
        E_self = complex(sbr_field(mv, GM, fc, u, spacing=d, grid_ref=self_ref))
        #  ② 얼린 격자에서 모노 ↔ 바이스태틱(û_s=û_i) 이 여전히 겹치는가
        B_froz = complex(sbr_field_bistatic(mv, GM, fc, u, u, spacing=d, grid_ref=ref))
        rows.append(dict(
            pose=i,
            abs_prod=abs(E_prod), abs_froz=abs(E_froz),
            d_level_db=float(20 * np.log10(abs(E_froz) / abs(E_prod))) if abs(E_prod) else None,
            d_phase_deg=float(np.degrees(np.angle(E_froz / E_prod))) if abs(E_prod) else None,
            self_ref_bit_identical=bool(_bits(E_self) == _bits(E_prod)),
            self_ref_rel_err=_relerr(E_self, E_prod),
            bistatic_rel_err=_relerr(B_froz, E_froz),
            bistatic_bit_identical=bool(_bits(B_froz) == _bits(E_froz)),
        ))
    field = dict(
        n_field=len(rows),
        self_ref_all_bit_identical=bool(all(r["self_ref_bit_identical"] for r in rows)),
        self_ref_max_rel_err=max(r["self_ref_rel_err"] for r in rows),
        bistatic_max_rel_err=max(r["bistatic_rel_err"] for r in rows),
        bistatic_all_bit_identical=bool(all(r["bistatic_bit_identical"] for r in rows)),
        froz_vs_prod_level_db_ptp=float(np.ptp([r["d_level_db"] for r in rows])),
        froz_differs_from_prod=bool(all(abs(r["d_phase_deg"]) > 1e-9 or
                                        abs(r["d_level_db"]) > 1e-12 for r in rows)),
        rows=rows,
        note=("self_ref = 그 자세 하나로 만든 판. 생산 경로와 **비트 동일**이어야 하고, 그래야 "
              "얼린 판과의 차이가 «격자를 얼린 효과» 라고 말할 수 있다."),
        passed=bool(all(r["self_ref_bit_identical"] for r in rows)
                    and max(r["bistatic_rel_err"] for r in rows) <= 1e-9),
    )

    # ── 독립 구현 대조: 원장을 만든 그 팔(_field_grid) 과 같은 값인가 ──────── #
    indep = dict(available=False)
    try:
        from sbr_grid_convergence_md import _field_grid          # noqa: WPS433
        shells = rsb._resolve_shells(sorted(set(np.asarray(fp.g).tolist())), GM, None)
        worst, r_rows = 0.0, []
        for i in fidx[:4]:
            mv = poses[i]
            e_ref, n_ref, _ = _field_grid(rsb, mv, GM, fc, u, d,
                                          np.asarray(ref.ctr, float), float(ref.Rout), shells)
            e_ker = complex(sbr_field(mv, GM, fc, u, spacing=d, grid_ref=ref))
            re = _relerr(e_ker, e_ref)
            worst = max(worst, re)
            r_rows.append(dict(pose=i, rel_err=re, n_grid_indep=int(n_ref), n_grid_ref=int(ref.n),
                               bit_identical=bool(_bits(e_ker) == _bits(e_ref))))
        indep = dict(available=True, max_rel_err=float(worst), rows=r_rows,
                     n_matches=bool(all(r["n_grid_indep"] == r["n_grid_ref"] for r in r_rows)),
                     passed=bool(worst <= 1e-12),
                     note=("benchmark/sbr_grid_convergence_md.py `_field_grid` — "
                           "outputs/sbr_grid_convergence.json 의 얼린 팔을 낸 독립 구현이다. "
                           "커널 배선이 그 실험과 같은 물리를 하는지 본다."))
    except Exception as e:                                        # noqa: BLE001
        indep = dict(available=False, error=f"{type(e).__name__}: {e}")

    # ── 음성 대조: 검사가 헛돌지 않는가 ─────────────────────────────────── #
    neg = {}
    small = ref._replace(Rout=float(ref.Rout) * 0.35,
                         n=max(3, int(ref.n * 0.35)))
    try:
        sbr_field(poses[0], GM, fc, u, spacing=d, grid_ref=small)
        neg["too_small_raises"] = False
        neg["too_small_msg"] = "예외가 안 났다 — 덮개 검사가 헛돈다"
    except ValueError as e:
        neg["too_small_raises"] = True
        neg["too_small_msg"] = str(e)[:200]
    try:
        sbr_field(poses[0], GM, fc, u, spacing=d * 1.5, grid_ref=ref)
        neg["spacing_mismatch_raises"] = False
    except ValueError as e:
        neg["spacing_mismatch_raises"] = True
        neg["spacing_mismatch_msg"] = str(e)[:200]
    neg["passed"] = bool(neg["too_small_raises"] and neg["spacing_mismatch_raises"])
    neg["note"] = ("일부러 작은 판·간격이 다른 판을 주면 커널이 **예외를 던져야** 한다. "
                   "안 던지면 [G3] 통과는 의미가 없다.")

    return g2, g3, field, indep, neg


def main():
    t0 = time.time()
    base, base_path, head = load_baseline()
    print(f"[base] git HEAD {head[:10]} → {base_path}", flush=True)

    g1 = gate_bit_identity(base)
    print(f"[G1] {g1['n_cases']} 케이스 · 비트동일 {g1['n_bit_identical']} · "
          f"max rel err {g1['max_rel_err']:.3e} · {'PASS' if g1['passed'] else 'FAIL'}", flush=True)

    g2, g3, field, indep, neg = gate_frozen()
    print(f"[G2] 얼린 격자 불변 {g2['frozen']['bit_constant']} "
          f"(생산 n {g2['prod']['n_min']}~{g2['prod']['n_max']}, {g2['prod']['n_changes']} 회 튐 · "
          f"ctr·û {g2['prod']['ctr_dot_u_ptp_mm']:.1f} mm 흔들림) · "
          f"{'PASS' if g2['passed'] else 'FAIL'}", flush=True)
    print(f"[G3] 덮개 최소여유 {g3['margin_min_mm']:.1f} mm "
          f"({g3['margin_min_cells']:.1f} 칸) · {'PASS' if g3['passed'] else 'FAIL'}", flush=True)
    print(f"[field] self_ref 비트동일 {field['self_ref_all_bit_identical']} · "
          f"bistatic max rel {field['bistatic_max_rel_err']:.3e} · "
          f"독립구현 {indep.get('max_rel_err')} · 음성대조 {neg['passed']}", flush=True)

    passed = bool(g1["passed"] and g2["passed"] and g3["passed"] and field["passed"]
                  and neg["passed"] and (not indep.get("available") or indep.get("passed")))

    doc = dict(
        _meta=dict(
            generated=_iso(), host=socket.gethostname(),
            script="benchmark/verify_frozen_grid.py",
            gpu=os.environ.get("SIONNA2_GPU"),
            baseline_git=head, baseline_file=os.path.relpath(base_path, _ROOT),
            kernel="src/rcs_sbr.py — sbr_field / sbr_field_bistatic 의 keyword-only `grid_ref`",
            angle_gamma=bool(rsb.ANGLE_GAMMA), grid_ref_check=bool(rsb.GRID_REF_CHECK),
            default_div=int(rsb.DEFAULT_DIV),
            motivation=("outputs/sbr_grid_convergence.json — 슬로타임 바닥의 지배 원인은 광선 "
                        "이산화가 아니라 «자세마다 격자를 다시 정의하는 것». 얼린 팔만 d² 로 "
                        "수렴한다(기울기 −2.09, R² 0.987)."),
            seconds=time.time() - t0,
        ),
        gate1_bit_identity=g1,
        gate2_frozen_grid_invariant=g2,
        gate3_coverage=g3,
        field_level=field,
        independent_implementation=indep,
        negative_controls=neg,
        passed=passed,
        caveats=[
            "기본값은 안 바뀐다 — grid_ref=None 이면 배선 전과 비트 동일(G1). 기존 원장은 그대로다.",
            "얼리기는 공짜가 아니다: 광선 수가 늘고(이 판 실측 extra_ray_cost), 백색 슬로타임 "
            "잡음이 **결정론적 레벨 편향**으로 바뀐다(오프셋 한 판에 레벨이 걸린다).",
            "이 게이트는 **배선의 계약**만 본다. 얼린 격자로 마이크로도플러 원장을 다시 낼지는 "
            "별개 결정이고, 그때는 리포트 수치가 전부 갱신되어야 한다.",
        ],
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"→ {OUT}   전체 {'PASS' if passed else 'FAIL'}  ({time.time()-t0:.0f}s)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
