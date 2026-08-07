# -*- coding: utf-8 -*-
"""
articulated_fast.py — **빠른 분절 자세 생성기** (로터별 rpm 지원)
=================================================================
`drones.pose_articulated()` 와 **같은 결과**를 내되, 위상마다 드론을 다시 짓지 않는다.

왜 필요한가 — 측정된 병목
--------------------------
`pose_articulated()` 는 호출할 때마다 `build_frame()` + `build_propeller()` 로
드론 전체를 파라메트릭 기하부터 다시 만들고, `Mesh.transformed()` 가 파이썬 리스트로
정점을 되돌리고, `merge()` 가 면을 파이썬 루프로 이어붙인다.

  실측 (matrice4e, GPU2, 2026-08-07)
      메쉬 조립 `pose_articulated`   1,631 ms
      씬 빌드                            29 ms
      광선 추적 + 집계                   44 ms
  → **시간의 96% 가 기하 재생성**이었다. 광선은 싸다.

⭐ 설계 출처 — 선배(홍지혁) `po_mdoppler/po_sim/mesh.py`
   "Per-face vertices are precomputed once at load so each pulse is a handful of
    vectorised matmuls." 같은 생각을 우리 파라메트릭 기하에 적용한다.

무엇이 열리는가
----------------
1. ⭐ **로터별 rpm**. 지금 `microdoppler_sbr()` 은 위상 하나 φ 로 네 로터를 함께 돌린다
   (`microdoppler.py:158`). 그래서 신호가 φ 의 주기함수가 되고, 스펙트로그램이 시간에
   변하지 않는다. 실제 기체는 모터마다 제어 루프가 따로 돌아 rpm 이 몇 % 씩 다르다.
   로터마다 위상을 따로 주려면 «위상 하나짜리 표» 트릭이 깨지는데, 조립이 싸지면
   시간표본마다 직접 추적해도 된다.
2. **긴 관측창**. 도플러 분해능은 `f_flash / (창에 든 주기 수)` 이므로 창을 늘려야 좋아진다.
   표본 수를 늘리는 것으로는 안 된다(N 이 약분된다).

정확성
-------
`pose(...)` 결과는 같은 인자의 `pose_articulated(...)` 와 **정점 배열이 같다**
(부동소수 반올림까지; `verify()` 가 검사한다). 면·그룹은 순서까지 같다.
"""
from __future__ import annotations

import numpy as np

from drones import build_frame, build_propeller, rotor_layout
from geom import Mesh, rotate, translate


class _MeshView:
    """`sbr_field`/`_mi_scene_from_mesh` 가 요구하는 것만 가진 가벼운 메쉬.

    그쪽은 `mesh.v` · `mesh.f` · `mesh.g` 만 `np.asarray` 로 읽는다. 파이썬 리스트로
    되돌리는 비용을 안 내려고 numpy 배열을 그대로 준다."""

    __slots__ = ("v", "f", "g")

    def __init__(self, v, f, g):
        self.v = v
        self.f = f
        self.g = g

    def n_tris(self) -> int:
        return len(self.f)

    def bounds(self):
        return self.v.min(0), self.v.max(0)

    def to_mesh(self) -> Mesh:
        """진짜 `geom.Mesh` 로 되돌린다 (렌더·저장처럼 느려도 되는 곳에서만)."""
        m = Mesh()
        m.v = [tuple(map(float, p)) for p in self.v]
        m.f = [tuple(map(int, t)) for t in self.f]
        m.g = list(self.g)
        return m


class FastPoser:
    """드론 하나를 한 번 지어 두고, 로터 위상만 바꿔 가며 자세를 찍어낸다.

        fp = FastPoser(DRONES["matrice4e"])
        mv = fp.pose([12.0, -12.0, 33.0, -33.0])      # 로터별 위상[deg]
        E  = sbr_field(mv, gmat, fc, u)

    ⚠ 몸체 자세(`body_rpy`)·위치(`body_pos`)는 **생성 시점에 고정**된다. 몸체가 움직이는
      시나리오는 자세마다 `FastPoser` 를 새로 만들어야 한다(그건 원래 비용이 든다).
      로터만 도는 정지비행에서는 하나로 충분하다.
    """

    def __init__(self, spec, body_rpy=(0.0, 0.0, 0.0), body_pos=(0.0, 0.0, 0.0)):
        self.spec = spec
        roll, pitch, yaw = body_rpy
        B = (translate(*[float(x) for x in body_pos])
             @ rotate("z", yaw) @ rotate("y", pitch) @ rotate("x", roll))
        self._B = B

        frame = build_frame(spec).transformed(B)
        prop_ccw = build_propeller(spec)                 # dir=+1 (CCW) 기준 형상
        prop_cw = build_propeller(spec, mirror=True)     # dir=−1 (CW) 거울상
        self.rl = rotor_layout(spec)

        # ── 정점·면·그룹을 한 번만 이어붙인다 (pose_articulated 와 같은 순서) ──
        v_blocks = [np.asarray(frame.v, float)]
        f_blocks = [np.asarray(frame.f, np.int64)]
        g_blocks = [np.asarray(frame.g, dtype=object)]
        base = len(frame.v)

        self._rotor_slices = []      # 로터별 정점 구간 (start, stop)
        self._rotor_local = []       # 회전 전 로컬 정점 (동차좌표 (n,4))
        self._rotor_const = []       # B @ T(center) @ Rz(base_ang) — 위상과 무관한 부분
        self._rotor_base = []        # base_ang [deg]

        for rot in self.rl:
            src = prop_ccw if rot["dir"] > 0 else prop_cw
            pv = np.asarray(src.v, float)
            cx, cy, cz = rot["center"]
            self._rotor_slices.append((base, base + len(pv)))
            self._rotor_local.append(np.c_[pv, np.ones(len(pv))])
            self._rotor_const.append(B @ translate(cx, cy, cz))
            self._rotor_base.append(float(rot["base_ang"]))

            v_blocks.append(np.zeros((len(pv), 3)))       # pose() 가 채운다
            f_blocks.append(np.asarray(src.f, np.int64) + base)
            g_blocks.append(np.full(len(src.f), "prop", dtype=object))
            base += len(pv)

        self.v = np.concatenate(v_blocks, axis=0)
        self.f = np.concatenate(f_blocks, axis=0)
        self.g = np.concatenate(g_blocks, axis=0)
        self.n_rotors = len(self.rl)
        self.dirs = [r["dir"] for r in self.rl]

    # ------------------------------------------------------------------ #
    def pose(self, rotor_phase_deg=None) -> _MeshView:
        """로터 위상[deg] 목록 → 메쉬 스냅샷. 정점 배열은 **매번 새로 만든다**
        (호출자가 여러 자세를 동시에 들고 있어도 안전하도록)."""
        if rotor_phase_deg is None:
            rotor_phase_deg = [0.0] * self.n_rotors
        v = self.v.copy()
        for i, ph in enumerate(rotor_phase_deg):
            M = self._rotor_const[i] @ rotate("z", self._rotor_base[i] + float(ph))
            a, b = self._rotor_slices[i]
            v[a:b] = (M @ self._rotor_local[i].T).T[:, :3]
        return _MeshView(v, self.f, self.g)

    # ------------------------------------------------------------------ #
    def verify(self, phases=(0.0, 17.0, 41.5, 123.0), tol=1e-9) -> dict:
        """`drones.pose_articulated` 와 결과가 같은지 검사한다.

        ⭐ 이 검사가 이 모듈의 존재 근거다 — 빠른 것이 아니라 **같은 것**이어야 한다."""
        from drones import pose_articulated
        worst_v = 0.0
        for ph in phases:
            ref = pose_articulated(self.spec,
                                   rotor_phase_deg=[d * ph for d in self.dirs])
            got = self.pose([d * ph for d in self.dirs])
            rv = np.asarray(ref.v, float)
            assert rv.shape == got.v.shape, f"정점 수 다름 {rv.shape} vs {got.v.shape}"
            assert np.array_equal(np.asarray(ref.f, np.int64), got.f), "면 인덱스 다름"
            assert list(ref.g) == list(got.g), "그룹 다름"
            worst_v = max(worst_v, float(np.abs(rv - got.v).max()))
        return {"max_abs_vertex_diff_m": worst_v, "ok": worst_v <= tol,
                "tol": tol, "n_phases": len(phases),
                "n_vert": int(len(self.v)), "n_tri": int(len(self.f))}


# ---------------------------------------------------------------------- #
def rotor_phases(t, rpm_per_rotor, dirs, base_deg=None):
    """시간축 → 로터별 위상[deg].

    rpm_per_rotor : 길이 n_rotors. ⭐ **로터마다 다른 rpm** 을 줄 수 있다 —
      이것이 스펙트로그램을 시간에 따라 변하게 만드는 요인이다.
    dirs          : 로터별 회전 부호 (+1 CCW / −1 CW).
    base_deg      : 로터별 t=0 위상 오프셋. None 이면 0.
      ⚠ 실제 기체는 t=0 에 네 로터가 정렬돼 있을 이유가 없다.

    반환 (n_t, n_rotors) [deg].
    """
    t = np.asarray(t, float)
    rpm = np.asarray(rpm_per_rotor, float)
    d = np.asarray(dirs, float)
    b = np.zeros(len(rpm)) if base_deg is None else np.asarray(base_deg, float)
    return b[None, :] + d[None, :] * (360.0 * rpm[None, :] / 60.0) * t[:, None]


if __name__ == "__main__":
    import sys
    import time
    from drones import DRONES, pose_articulated

    print(f"{'기체':16s} {'정점':>7s} {'삼각형':>8s} {'느린[ms]':>9s} {'빠른[ms]':>9s} "
          f"{'배속':>7s}  일치")
    for key in ("mini5pro", "matrice4e", "phantom4"):
        spec = DRONES[key]
        fp = FastPoser(spec)
        chk = fp.verify()
        dirs = fp.dirs

        t0 = time.time()
        for ph in (5.0, 25.0, 45.0):
            pose_articulated(spec, rotor_phase_deg=[d * ph for d in dirs])
        slow = (time.time() - t0) / 3 * 1e3

        fp.pose([0] * fp.n_rotors)                       # 워밍업
        t0 = time.time()
        for ph in np.linspace(0, 180, 50):
            fp.pose([d * ph for d in dirs])
        fast = (time.time() - t0) / 50 * 1e3

        print(f"{spec.name:16s} {chk['n_vert']:7d} {chk['n_tri']:8d} "
              f"{slow:9.1f} {fast:9.2f} {slow/fast:6.0f}x  "
              f"{'✅' if chk['ok'] else '❌'} 최대차 {chk['max_abs_vertex_diff_m']:.2e} m")
    sys.exit(0)
