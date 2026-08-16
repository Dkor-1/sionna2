# -*- coding: utf-8 -*-
"""
mesh_dimref.py — **치수·외부 기준 대조**: 메쉬를 «바깥의 참값» 과 견준다
==============================================================================
왜 필요한가 (2026-08-16, 인증 라운드)
  `mesh_check.py` 의 검사는 대부분 «메쉬가 **자기 자신과** 앞뒤가 맞는가» 를 본다. 거기에
  `check_dimensions` 가 세 수(프롭 지름·로터 대각·공식 외형)를 `DroneSpec` 과 대조하는데,
  **`DroneSpec` 자체가 우리가 적어 넣은 수**다. 그래서 «스펙대로 정확히 지은, 그러나 실물과
  다른 기체» 는 원리적으로 통과한다(범주 지도 M14).
  이 파일은 그 구멍을 막는다 — 참값의 출처를 **저장소 밖의 물건**(제조사 공식 CAD·공표 제원·
  제품 사진 계측)으로 두고, 기체 × 부품 칸마다 잔차와 **근거 등급**을 남긴다.

무엇이 다른가 (mesh_check.check_dimensions ↔ 이 파일)
  · check_dimensions : 메쉬 ↔ **DroneSpec**       (내부 일관성. 스펙이 틀리면 같이 틀린다)
  · mesh_dimref      : 메쉬 ↔ **공식 CAD·공표·사진** (외부 참값. 스펙이 틀리면 여기서 걸린다)

용어 한 줄 풀이
  · **잔차(residual)**   : 우리 메쉬에서 잰 값 − 바깥 참값. (+)면 우리가 크다.
  · **표준불확도 u**     : 참값이 얼마나 흔들리는지를 «1 시그마» 로 적은 수[mm].
  · **확장불확도 U**     : U = k·u_c (k=2, 약 95 % 포함). **허용오차는 이 U 다.**
  · **근거 등급**        : [A] 공식 CAD 직접 · [B] 사진 계측 · [C] 계열 유추 · [D] 대리.
  · **순환(circular)**   : 그 참값에서 상수를 유도해 놓고 다시 그 참값과 견주는 것. 일치해도
                           «독립 증거» 가 아니다 — 값이 메쉬에 **실렸다**는 것만 증명한다.

⭐ 허용오차에 임의 숫자를 쓰지 않는다
  기존 검사들의 «1 % · 3 %» 같은 잣대는 실측 후 여유를 붙인 **선언**이다. 여기서는 다르게 한다:
  허용오차 U 는 **참값의 측정 불확실도에서 유도**한다(§TOL_POLICY). 유도 문장이 없는 행은
  `guard_tolerance_provenance()` 가 **실패시킨다** — 근거 없는 숫자가 표에 들어오지 못하게.

⛔ M4T / M4E 규칙 (이 파일이 코드로 강제한다)
  `assets/meshes/reference/matrice4-M4T_v2.step` 은 **Matrice 4T** 판이다. 기체(셸·암·모터·
  다리·배터리베이)는 4E 와 공유하지만 **짐벌은 다른 물건**이다. 그래서 이 파일의 참값 표에서
  matrice4e 의 짐벌/카메라 **치수** 행이 공식 CAD 를 출처로 쓰면 `guard_m4t_gimbal()` 이
  **실패한다**. (짐벌의 **위치**는 CAD 를 써도 된다 — 크래들이 붙는 자리는 기체 쪽 형상이다.)

실행
  python src/mesh_dimref.py              전 기종 잔차표를 화면에 찍는다
  python src/mesh_dimref.py --key mini2  한 기종만
  ⛔ GPU 안 쓴다(전부 CPU). 파일도 안 쓴다 — 인증서는 benchmark/ 쪽 스크립트가 쓴다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#  k = 2 — 국제 관례(GUM)의 확장계수. «약 95 % 를 덮는다» 는 뜻이고, 이 파일에서 유일하게
#  «관례로 고른» 수다. 나머지 숫자는 전부 측정에서 유도된다.
K_COVERAGE = 2.0

_SQRT3 = math.sqrt(3.0)


# --------------------------------------------------------------------------- #
#  ① 참값의 «출처 등급» 과 그 등급의 표준불확도 u_ref — **전부 유도된 수다**
# --------------------------------------------------------------------------- #
#  읽는 법: 각 항목의 u_mm 은 «그 출처가 참값을 얼마나 정확히 주는가» 이고, derivation 이
#  그 수가 어디서 나왔는지다. 두 갈래뿐이다.
#    (a) 공표값 — 반올림 자리에서 나온다. N mm 자리까지 적혔으면 참값은 ±N/2 안의 어딘가이고,
#        어디인지 모르므로 균등분포다 ⇒ u = (N/2)/√3.  (GUM 4.3.7 의 표준 처리)
#    (b) CAD/GLB 자산 — 그 자산이 **공표값을 몇 mm 로 재현했는가**의 RMS 를 쓴다. 자산이
#        실물과 얼마나 다른지는 직접 못 재지만, 공표값과의 어긋남은 그 상한의 관측치다.
#        ⚠ 이 안에는 공표값의 반올림도 이미 섞여 있다 — 그래서 (a)와 **겹쳐 더하지 않는다**.
REF_CLASS: dict[str, dict] = {
    "pub_1mm": dict(
        u_mm=0.5 / _SQRT3,
        derivation="공표값이 1 mm 자리까지 반올림 → 참값은 ±0.5 mm 균등분포 → u = 0.5/√3 = 0.289 mm",
    ),
    "pub_0p1mm": dict(
        u_mm=0.05 / _SQRT3,
        derivation="공표값이 0.1 mm 자리까지 → ±0.05 mm 균등분포 → u = 0.05/√3 = 0.029 mm",
    ),
    "cad_m4t": dict(
        u_mm=math.sqrt((0.001 ** 2 + 0.021 ** 2 + 0.323 ** 2) / 3.0),
        derivation=(
            "DJI M4T 공식 STEP 이 공표 3건을 재현한 잔차의 RMS — 폭 387.501↔387.5(0.001) · "
            "높이 149.521↔149.5(0.021) · 길이 307.323↔307.0(0.323) mm ⇒ u = 0.187 mm. "
            "(대각 −1.96 mm 는 «공표 대각의 정의가 다르다» 고 원장이 스스로 표시했으므로 뺐다)"
        ),
        source_file="outputs/meshfix_matrice4e.json :: scale_check",
    ),
    "glb_mini2": dict(
        u_mm=math.sqrt((0.113 ** 2 + 0.434 ** 2 + 0.023 ** 2) / 3.0),
        derivation=(
            "DJI Mini 2 공식 GLB 가 공표 펼침 3축을 재현한 잔차의 RMS — 159.113↔159(0.113) · "
            "203.434↔203(0.434) · 55.977↔56(−0.023) mm ⇒ u = 0.260 mm"
        ),
        source_file="outputs/meshdef_mini2_glb.json :: scale_verification",
    ),
    "step_x500": dict(
        u_mm=math.sqrt((0.28 ** 2 + 0.0 ** 2 + 0.0 ** 2 + 0.28 ** 2) / 4.0),
        derivation=(
            "Holybro X500 V2 공식 STEP 이 공표 4건을 재현한 잔차의 RMS — 판 143.72↔144(−0.28) · "
            "판두께 2.000↔2(0.00) · 판간격 28.000↔28(0.00) · 다리높이 215.28↔215(0.28) mm "
            "⇒ u = 0.198 mm"
        ),
        source_file="outputs/x500v2_cad.json",
    ),
    "photo": dict(
        u_mm=None,       # 행마다 다르다 — ref_band_pct 에서 계산한다
        derivation=(
            "사진 계측은 축척 앵커와 모서리 집기(edge localisation)가 오차를 만든다. 저장소는 "
            "사진 유래 값마다 밴드(예: ±15 %)를 선언해 왔으므로, 그 밴드를 균등분포로 보고 "
            "u = (밴드 반폭)/√3 로 환산한다. 밴드가 선언 안 된 사진 값은 이 파일이 **참값으로 쓰지 않는다**."
        ),
    ),
}


def _u_ref(row: "DimRef") -> tuple[float, str]:
    """행의 참값 표준불확도[mm] 와 그 유도 문장."""
    cls = REF_CLASS[row.ref_class]
    if row.ref_class == "photo":
        if row.ref_band_pct is None or row.ref_mm is None:
            raise ValueError(f"{row.rid}: 사진 유래 행인데 밴드(ref_band_pct)가 없다")
        u = abs(row.ref_mm) * (row.ref_band_pct / 100.0) / _SQRT3
        return u, (f"{cls['derivation']} — 이 행의 선언 밴드 ±{row.ref_band_pct} % "
                   f"⇒ u = {abs(row.ref_mm):.2f}×{row.ref_band_pct/100:.3f}/√3 = {u:.3f} mm")
    return float(cls["u_mm"]), cls["derivation"]


# --------------------------------------------------------------------------- #
#  ② 잣대(측정자) — 우리 메쉬에서 «참값과 같은 정의로» 재는 함수들
# --------------------------------------------------------------------------- #
#  ⚠ 여기가 이 파일에서 가장 조심할 자리다. 같은 이름의 치수라도 **정의가 다르면 다른 수**다.
#     실제로 감사 I10 ① 은 matrice4e 길이를 «메쉬 전체 bbox» 로 재서 +7.96 % 라 적었는데,
#     공표 307 mm 는 공식 CAD 가 «앞 암 끝 페어링 → 뒤 암 끝 페어링» 이라고 확정한 수다.
#     정의를 맞춰 재면 −0.36 % 다. 그래서 잣대마다 정의를 문자열로 들고 다닌다.

def _components(F: np.ndarray) -> list[np.ndarray]:
    """면 배열을 **연결요소(부품)** 로 쪼갠다 — trimesh 를 안 거치고 인덱스 연결만 본다."""
    from mesh_check import _raw_components
    used = np.unique(F)
    remap = np.zeros(int(used.max()) + 1, np.int64)
    remap[used] = np.arange(len(used))
    n, lab = _raw_components(remap[F], len(used))
    return [F[lab == i] for i in range(n)]


@dataclass
class MeshRuler:
    """한 기체의 메쉬를 재는 자. 모든 값 mm, 좌표는 저장소 규약(+x 기수 · z 위)."""
    key: str
    spec: object
    V: np.ndarray                     # (n,3) mm
    F: np.ndarray
    G: np.ndarray
    _cache: dict = field(default_factory=dict)

    # ---- 기본 도구 -------------------------------------------------------
    def _grp_faces(self, *groups) -> np.ndarray:
        sel = np.zeros(len(self.G), bool)
        for g in groups:
            sel |= (self.G == g)
        return self.F[sel]

    def _grp_pts(self, *groups):
        f = self._grp_faces(*groups)
        return self.V[np.unique(f)] if len(f) else None

    def has(self, *groups) -> bool:
        return any((self.G == g).any() for g in groups)

    @property
    def rotors(self):
        if "rotors" not in self._cache:
            from drones import rotor_layout
            rl = rotor_layout(self.spec)
            self._cache["rotors"] = (rl, np.asarray([r["center"] for r in rl], float) * 1000.0)
        return self._cache["rotors"]

    @property
    def prop_clusters(self):
        """로터별 (프롭 면 인덱스, 스윕 중심 xy, 스윕 반경, 날 z 평균)."""
        if "props" in self._cache:
            return self._cache["props"]
        _, ctr = self.rotors
        Fp = self._grp_faces("prop")
        C = self.V[Fp].mean(1)
        idx = np.linalg.norm(C[:, None, :2] - ctr[None, :, :2], axis=2).argmin(1)
        out = []
        for i in range(len(ctr)):
            sel = idx == i
            if not sel.any():
                out.append(None)
                continue
            P = self.V[Fp[sel]].reshape(-1, 3)
            cx, cy = float(P[:, 0].mean()), float(P[:, 1].mean())
            R = float(np.hypot(P[:, 0] - cx, P[:, 1] - cy).max())
            out.append((cx, cy, R, float(P[:, 2].mean())))
        self._cache["props"] = out
        return out

    def _motor_comp(self, i: int):
        """로터 i 에 가장 가까운 'motor' 그룹 연결요소의 정점."""
        ck = f"motor{i}"
        if ck in self._cache:
            return self._cache[ck]
        _, ctr = self.rotors
        best, bd = None, 1e18
        for c in _components(self._grp_faces("motor")):
            P = self.V[np.unique(c)]
            d = math.hypot(P[:, 0].mean() - ctr[i, 0], P[:, 1].mean() - ctr[i, 1])
            if d < bd:
                bd, best = d, P
        self._cache[ck] = best
        return best

    # ---- 잣대들 ----------------------------------------------------------
    def frame_bbox(self) -> np.ndarray:
        """**프로펠러를 뺀** 기체 bbox 세 축[mm]. DJI 의 «펼침(프롭 제외)» 규약."""
        nonp = np.unique(self.F[self.G != "prop"])
        P = self.V[nonp]
        return P.max(0) - P.min(0)

    def full_bbox(self) -> np.ndarray:
        """프로펠러 포함 bbox — 단, **날이 멈춘 자세**의 bbox다(스윕 아님)."""
        return self.V.max(0) - self.V.min(0)

    def sweep_envelope(self) -> np.ndarray:
        """**스윕 디스크** 외형[mm] — 프롭이 도는 원반까지 포함한 «프롭 포함» 규약.
        날이 멈춘 자세의 bbox 와 다르다. DJI 의 «펼침(프롭 포함)» 은 이쪽이다."""
        xs, ys = [], []
        for c in self.prop_clusters:
            if c is None:
                continue
            cx, cy, R, _ = c
            xs += [cx - R, cx + R]
            ys += [cy - R, cy + R]
        nonp = np.unique(self.F[self.G != "prop"])
        P = self.V[nonp]
        return np.array([max(xs) - min(xs), max(ys) - min(ys),
                         float(P[:, 2].max() - P[:, 2].min())])

    def prop_dia(self, i=None) -> float:
        """스윕 지름[mm]. i 를 주면 그 로터만."""
        cs = [c for c in self.prop_clusters if c is not None]
        if i is not None:
            c = self.prop_clusters[i]
            return 2.0 * c[2] if c else float("nan")
        return float(np.mean([2.0 * c[2] for c in cs]))

    def wheelbase(self) -> float:
        """**마주보는 로터축 사이 거리**[mm] = 제조사가 «Diagonal» 로 적는 수.
        (평균 반경 ×2 가 아니다 — 사다리꼴 배치에서 둘이 갈린다)"""
        cs = [c for c in self.prop_clusters if c is not None]
        n = len(cs)
        if n < 2:
            return float("nan")
        best = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                best = max(best, math.hypot(cs[i][0] - cs[j][0], cs[i][1] - cs[j][1]))
        return best

    def rotor_r(self, i) -> float:
        c = self.prop_clusters[i]
        return math.hypot(c[0], c[1]) if c else float("nan")

    def rotor_az(self, i) -> float:
        c = self.prop_clusters[i]
        return math.degrees(math.atan2(c[1], c[0])) % 360.0 if c else float("nan")

    def rotor_z(self, i) -> float:
        c = self.prop_clusters[i]
        return c[3] if c else float("nan")

    def rotor_dz(self) -> float:
        """앞 로터 − 뒤 로터의 프롭 평면 높이차[mm]."""
        cs = [c for c in self.prop_clusters if c is not None]
        fr = [c for c in cs if c[0] > 0]
        re = [c for c in cs if c[0] < 0]
        if not fr or not re:
            return float("nan")
        return float(np.mean([c[3] for c in fr]) - np.mean([c[3] for c in re]))

    def motor_span(self, axis: int) -> float:
        """'motor' 그룹의 축방향 폭[mm] — 암 끝(모터 마운트) 사이 거리의 잣대."""
        P = self._grp_pts("motor")
        return float(P[:, axis].max() - P[:, axis].min())

    def motor_od(self, i=0) -> float:
        """로터 i 모터 부품의 **최대 지름**[mm] (부품 자기 축 기준)."""
        P = self._motor_comp(i)
        r = np.hypot(P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean())
        return 2.0 * float(r.max())

    def motor_z(self, i=0, which="lo") -> float:
        """로터 i 모터 부품의 z 최저/최고[mm]. ⚠ 이 부품에 나사 포스트가 포함된 기체
        (mini2)에서는 'hi' 가 벨 꼭대기가 아니다 — 그 행은 참값 표에서 제외했다."""
        P = self._motor_comp(i)
        return float(P[:, 2].min() if which == "lo" else P[:, 2].max())

    def motor_h(self, i=0) -> float:
        P = self._motor_comp(i)
        return float(np.ptp(P[:, 2]))

    def shell_x(self, which="max") -> float:
        """**셸(동체)** 의 앞끝/뒤끝 x[mm]. 셸형 기체는 암이 body 그룹에 합쳐져 있으므로,
        캐노피 반폭의 1.15 배 안쪽(|y|)에 있는 body 삼각형만 골라 «동체» 로 본다."""
        Fb = self._grp_faces("body")
        if not len(Fb):
            return float("nan")
        ylim = self._shell_ylim()
        C = self.V[Fb].mean(1)
        P = self.V[np.unique(Fb[np.abs(C[:, 1]) <= ylim])]
        return float(P[:, 0].max() if which == "max" else P[:, 0].min())

    def shell_z(self, which="min") -> float:
        Fb = self._grp_faces("body")
        if not len(Fb):
            return float("nan")
        ylim = self._shell_ylim()
        C = self.V[Fb].mean(1)
        P = self.V[np.unique(Fb[np.abs(C[:, 1]) <= ylim])]
        return float(P[:, 2].min() if which == "min" else P[:, 2].max())

    def _shell_ylim(self) -> float:
        if self.has("canopy"):
            return 1.15 * float(np.abs(self._grp_pts("canopy")[:, 1]).max())
        return 0.30 * float(self.frame_bbox()[1])

    def top_z(self) -> float:
        """프롭을 뺀 **최고점** z[mm]."""
        nonp = np.unique(self.F[self.G != "prop"])
        return float(self.V[nonp][:, 2].max())

    def bottom_z(self) -> float:
        """프롭을 뺀 **최저점** z[mm] = 접지면."""
        nonp = np.unique(self.F[self.G != "prop"])
        return float(self.V[nonp][:, 2].min())

    def gear_bottom_z(self) -> float:
        P = self._grp_pts("gear", "gear_cf")
        return float(P[:, 2].min()) if P is not None else float("nan")

    def gear_height_below(self, ref_z: float) -> float:
        return float(ref_z - self.gear_bottom_z())

    def foot_r(self, front=True) -> float:
        """착륙 발(다리 끝) 중심의 반경[mm] — 앞/뒤 각각의 평균."""
        Fg = self._grp_faces("gear", "gear_cf")
        if not len(Fg):
            return float("nan")
        rs = []
        for c in _components(Fg):
            P = self.V[np.unique(c)]
            cx, cy = float(P[:, 0].mean()), float(P[:, 1].mean())
            if (cx > 0) == front and abs(cy) > 1e-6:
                rs.append(math.hypot(cx, cy))
        return float(np.mean(rs)) if rs else float("nan")

    def part_box(self, group: str, axis: int, pick="volume") -> float:
        """그룹 안 **한 부품**의 bbox 변 길이[mm]. pick='volume' 이면 가장 큰 부품,
        'front' 면 가장 앞(+x)에 있는 부품."""
        Fg = self._grp_faces(group)
        if not len(Fg):
            return float("nan")
        best, score = None, -1e18
        for c in _components(Fg):
            P = self.V[np.unique(c)]
            s = float(np.prod(P.max(0) - P.min(0))) if pick == "volume" else float(P[:, 0].mean())
            if s > score:
                score, best = s, P
        return float((best.max(0) - best.min(0))[axis])

    def part_centre(self, group: str, axis: int, pick="volume") -> float:
        Fg = self._grp_faces(group)
        if not len(Fg):
            return float("nan")
        best, score = None, -1e18
        for c in _components(Fg):
            P = self.V[np.unique(c)]
            s = float(np.prod(P.max(0) - P.min(0))) if pick == "volume" else float(P[:, 0].mean())
            if s > score:
                score, best = s, P
        return float(0.5 * (best.max(0) + best.min(0))[axis])

    def plate(self, what: str) -> float:
        """열린 프레임(plate_stack)의 판 치수[mm] — 'span'·'t'·'gap'·'stack'·'bottom_z'.

        ⚠ 'deck' 그룹에는 판 말고도 페이로드 레일·플랫폼 판·GNSS 마스트가 같이 들어 있다.
          «판» 의 정의를 **거의 정사각형이고 아주 얇다** 로 못박아 그것들을 배제한다:
            · 평면 종횡비 min/max ≥ 0.8   (레일 250×9.3 → 0.037 배제, 플랫폼 65×93 → 0.70 배제)
            · 두께 ≤ 0.1 × 짧은 변        (마스트 4×3.9×112.8 배제)"""
        Fd = self._grp_faces("deck")
        if not len(Fd):
            return float("nan")
        plates = []
        for c in _components(Fd):
            P = self.V[np.unique(c)]
            sz = P.max(0) - P.min(0)
            a, b = float(min(sz[0], sz[1])), float(max(sz[0], sz[1]))
            if b <= 0 or a / b < 0.8 or sz[2] > 0.1 * a:
                continue
            plates.append((float(P[:, 2].min()), float(P[:, 2].max()), b))
        if len(plates) < 2:
            return float("nan")
        plates.sort()
        lo, hi = plates[0], plates[-1]
        if what == "span":
            return float(np.mean([p[2] for p in plates]))
        if what == "t":
            return float(np.mean([p[1] - p[0] for p in plates]))
        if what == "gap":
            return float(hi[0] - lo[1])
        if what == "stack":
            return float(hi[1] - lo[0])
        if what == "bottom_z":
            return float(lo[0])
        raise KeyError(what)

    def rail(self, what: str) -> float:
        """페이로드 레일(하판 밑을 앞뒤로 가로지르는 가는 막대)의 치수[mm] — 'track'·'len'.
        판·플랫폼과 구별하는 정의: **한 축으로만 아주 길다**(긴 변 > 짧은 변 5 배)."""
        Fd = self._grp_faces("deck")
        if not len(Fd):
            return float("nan")
        rails = []
        for c in _components(Fd):
            P = self.V[np.unique(c)]
            sz = P.max(0) - P.min(0)
            if sz[0] > 5.0 * max(sz[1], sz[2]):
                rails.append((float(0.5 * (P[:, 1].min() + P[:, 1].max())), float(sz[0])))
        if len(rails) < 2:
            return float("nan")
        if what == "track":
            return float(max(r[0] for r in rails) - min(r[0] for r in rails))
        if what == "len":
            return float(np.mean([r[1] for r in rails]))
        raise KeyError(what)

    def arm_od(self) -> float:
        """열린 프레임의 암 **튜브 외경**[mm] — 수평 튜브라 z 폭이 곧 지름이다.
        ⚠ 셸형 기체는 암이 body 그룹에 합쳐져 있어 이 잣대를 쓸 수 없다(그래서 그 행이 없다)."""
        P = self._grp_pts("arm")
        return float(np.ptp(P[:, 2])) if P is not None else float("nan")

    def motor_top_to_gear_bottom(self) -> float:
        """**모터 꼭대기 → 발**[mm]. 일부 제조사(DJI Phantom 3)가 «높이» 를 이렇게 정의한다 —
        기체 bbox 높이와 다른 수다."""
        _, ctr = self.rotors
        top = max(float(self._motor_comp(i)[:, 2].max()) for i in range(len(ctr)))
        return float(top - self.gear_bottom_z())

    def skid_track(self) -> float:
        """좌우 스키드(가로 튜브) 축 사이 거리[mm]."""
        Fg = self._grp_faces("gear")
        ys = []
        for c in _components(Fg):
            P = self.V[np.unique(c)]
            sz = P.max(0) - P.min(0)
            if sz[0] > 3 * max(sz[1], sz[2]):        # x 로 길쭉한 막대 = 스키드
                ys.append(float(0.5 * (P[:, 1].min() + P[:, 1].max())))
        if len(ys) < 2:
            return float("nan")
        return float(max(ys) - min(ys))

    #  ---- 면분할이 잣대에 주는 불확도 u_disc -----------------------------
    def u_disc_radius(self, i=0) -> float:
        """다면체로 지은 원통을 «지름» 으로 잴 때 생기는 불확도[mm].
        외접(꼭짓점)과 내접(변 중앙)이 다르므로 그 절반을 균등분포로 본다."""
        P = self._motor_comp(i)
        r = np.hypot(P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean())
        r = r[r > 0.9 * r.max()]
        return float((r.max() - r.min()) / _SQRT3)


def ruler(spec, mesh=None) -> MeshRuler:
    from drones import build_drone
    m = mesh if mesh is not None else build_drone(spec)
    return MeshRuler(key=spec.key, spec=spec,
                     V=np.asarray(m.v, float) * 1000.0,
                     F=np.asarray(m.f, np.int64),
                     G=np.asarray(m.g))


def mesh_fingerprint(mesh) -> str:
    """메쉬 지문 — 정점·면·그룹의 sha256 앞 16자리. 인증서가 «어떤 메쉬를 봤는지» 를 못박는다."""
    h = hashlib.sha256()
    h.update(np.asarray(mesh.v, float).round(9).tobytes())
    h.update(np.asarray(mesh.f, np.int64).tobytes())
    h.update("|".join(map(str, mesh.g)).encode())
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------- #
#  ③ 참값 표 — **바깥에서 온 수**만 들어온다
# --------------------------------------------------------------------------- #
@dataclass
class DimRef:
    rid: str                 # 행 번호
    key: str                 # 기체
    part: str                # 부품(등급 행렬의 열)
    quantity: str            # 무엇을 재나
    measure: str             # 잣대 이름(아래 _MEASURE 에 실행식)
    ref_mm: float | None     # 바깥 참값[mm]. None = 참값 없음(모름)
    ref_class: str           # REF_CLASS 키
    grade: str               # A / A- / B / B- / C / D
    source: str              # 근거 한 줄
    source_file: str | None  # 저장소 안의 근거 파일(있으면 provenance 검사가 연다)
    definition: str          # ⭐ 참값과 우리 잣대가 **같은 것을 재는지** 적는 자리
    circularity: str         # independent / partly_circular / circular
    u_def_mm: float          # 정의 차이에서 오는 불확도
    u_def_why: str
    ref_band_pct: float | None = None   # 사진 유래 행의 선언 밴드
    note: str = ""
    #  ⭐ 참값이 **파일에 그대로 적힌 수가 아니라 그 수들로 계산한 값**일 때, 계산에 쓴
    #    원재료를 여기 적는다. 근거 파일 대조는 이 수들을 찾는다 — «유도값을 저장값인 척»
    #    하지 못하게 막는 자리다(빈칸이면 ref_mm 자신을 찾는다).
    source_values: tuple | None = None


def _R(*a, **kw) -> DimRef:
    return DimRef(*a, **kw)


#  ⚠ 잣대 실행식 — MeshRuler 의 메서드를 문자열에서 부른다. 표를 한눈에 읽히게 하려고
#    이렇게 뒀다. 새 잣대를 쓰려면 여기에 등록해야 한다(오타가 조용히 통과하지 않는다).
_MEASURE = {
    "frame_L": lambda r: r.frame_bbox()[0],
    "frame_W": lambda r: r.frame_bbox()[1],
    "frame_H": lambda r: r.frame_bbox()[2],
    "sweep_L": lambda r: r.sweep_envelope()[0],
    "sweep_W": lambda r: r.sweep_envelope()[1],
    "prop_dia": lambda r: r.prop_dia(),
    "wheelbase": lambda r: r.wheelbase(),
    "motor_span_x": lambda r: r.motor_span(0),
    "motor_span_y": lambda r: r.motor_span(1),
    "motor_od0": lambda r: r.motor_od(0),
    "motor_h0": lambda r: r.motor_h(0),
    "motor_z0_lo": lambda r: r.motor_z(0, "lo"),
    "motor_z1_lo": lambda r: r.motor_z(1, "lo"),
    "motor_z_sep": lambda r: r.motor_z(0, "lo") - r.motor_z(1, "lo"),
    "rotor0_r": lambda r: r.rotor_r(0),
    "rotor1_r": lambda r: r.rotor_r(1),
    "rotor0_az": lambda r: r.rotor_az(0),
    "rotor1_az": lambda r: r.rotor_az(1),
    "rotor_dz": lambda r: r.rotor_dz(),
    "shell_nose_x": lambda r: r.shell_x("max"),
    "shell_tail_x": lambda r: r.shell_x("min"),
    "shell_belly_z": lambda r: r.shell_z("min"),
    "shell_crown_z": lambda r: r.shell_z("max"),
    "top_z": lambda r: r.top_z(),
    "bottom_z": lambda r: r.bottom_z(),
    "gear_bottom_z": lambda r: r.gear_bottom_z(),
    "foot_r_front": lambda r: r.foot_r(True),
    "foot_r_rear": lambda r: r.foot_r(False),
    "gimbal_L": lambda r: r.part_box("camera", 0, "front"),
    "gimbal_W": lambda r: r.part_box("camera", 1, "front"),
    "gimbal_H": lambda r: r.part_box("camera", 2, "front"),
    "gimbal_cx": lambda r: r.part_centre("camera", 0, "front"),
    "gimbal_cz": lambda r: r.part_centre("camera", 2, "front"),
    "battery_L": lambda r: r.part_box("battery", 0, "volume"),
    "battery_W": lambda r: r.part_box("battery", 1, "volume"),
    "battery_H": lambda r: r.part_box("battery", 2, "volume"),
    "pcb_L": lambda r: r.part_box("pcb", 0, "volume"),
    "pcb_W": lambda r: r.part_box("pcb", 1, "volume"),
    "pcb_H": lambda r: r.part_box("pcb", 2, "volume"),
    "arm_od": lambda r: r.arm_od(),
    "rail_track": lambda r: r.rail("track"),
    "rail_len": lambda r: r.rail("len"),
    "motor_top_to_gear_bottom": lambda r: r.motor_top_to_gear_bottom(),
    "plate_span": lambda r: r.plate("span"),
    "plate_t": lambda r: r.plate("t"),
    "plate_gap": lambda r: r.plate("gap"),
    "plate_stack": lambda r: r.plate("stack"),
    "skid_track": lambda r: r.skid_track(),
    #  하판 **아랫면** 기준 다리 높이 — CAD 참값과 같은 정의(원장 x500v2_cad.json)
    "gear_h_below_deck": lambda r: r.plate("bottom_z") - r.gear_bottom_z(),
}

#  잣대별 «면분할 불확도» u_disc 를 어떻게 얻는가. 없는 잣대는 0 이고 이유를 적는다.
_U_DISC = {
    "motor_od0": lambda r: r.u_disc_radius(0),
}
_U_DISC_ZERO_WHY = ("이 잣대는 상자·평면·최댓값 위치라 삼각형 분할이 값을 바꾸지 않는다"
                    "(원통을 지름으로 재는 잣대만 u_disc 가 붙는다)")


#  ---- 표 ---------------------------------------------------------------- #
#  ⭐ 규약: 여기에 적는 ref_mm 은 **바깥에서 온 수**여야 한다. `DroneSpec` 의 값을 베껴
#     적으면 그건 외부 대조가 아니라 자기대조이고, 이 파일의 존재 이유가 사라진다.
#     그래서 source_file 을 두고 `audit_reference_provenance()` 가 실제로 열어 확인한다.
REFS: list[DimRef] = [
    # ====================== matrice4e — DJI M4T 공식 STEP [A] ============== #
    _R("M4E-01", "matrice4e", "airframe", "펼침 길이(암 끝 ↔ 암 끝)", "motor_span_x",
       307.0, "pub_1mm", "A",
       "DJI Matrice 4 시리즈 공표 «펼침 307 mm»; 공식 CAD 가 그 정의를 «앞 암 끝 페어링 → 뒤 암 끝 페어링»으로 확정(307.323 mm)",
       "outputs/meshfix_matrice4e.json",
       "⭐정의 주의 — 이 수는 기체 bbox 가 **아니다**. 짐벌·다리를 뺀 암-대-암이다. "
       "메쉬 전체 bbox 로 재면 331.4 mm 라 +7.9 % 로 보이지만 그건 다른 물건을 잰 것이다(감사 I10 ①).",
       "independent", 0.5,
       "우리 잣대는 'motor' 그룹 x 폭(모터 벨 바깥)이고 참값은 암 끝 페어링이다. CAD 에서 둘의 "
       "차이는 페어링이 벨을 감싸는 두께이고 그 값은 원장에 없다 ⇒ 0.5 mm 로 선언한다."),
    _R("M4E-02", "matrice4e", "airframe", "펼침 폭(앞 모터 마운트 바깥)", "motor_span_y",
       387.5, "pub_0p1mm", "A",
       "DJI 공표 387.5 mm; 공식 CAD 가 387.501 mm 로 재현(+0.003 %)",
       "outputs/meshfix_matrice4e.json",
       "앞 모터 마운트 좌↔우 바깥. 우리 잣대는 'motor' 그룹 y 폭이다.",
       "independent", 0.5,
       "M4E-01 과 같은 이유(페어링 두께 미기록) ⇒ 0.5 mm."),
    _R("M4E-03", "matrice4e", "airframe", "높이(접지 → RTK 터렛 꼭대기)", "frame_H",
       149.5, "pub_0p1mm", "A",
       "DJI 공표 149.5 mm; CAD 149.521 mm 로 재현. ⭐이 일치가 «149.5 는 터렛 포함·GNSS 커버 제외» 를 확정",
       "outputs/meshfix_matrice4e.json",
       "접지점 → RTK 터렛 꼭대기. 우리 잣대는 프롭 제외 bbox 높이다(둘이 같은 두 점).",
       "circular", 0.0,
       "⛔ 이 행은 **순환**이다 — `envelope_mm=(None,None,149.5)` 가 프레임을 그 높이로 "
       "강제하므로 일치는 보장돼 있다. 그래도 싣는 이유: 강제가 **풀렸는지**를 감시한다."),
    _R("M4E-04", "matrice4e", "body", "셸 앞끝 x", "shell_nose_x",
       159.01, "cad_m4t", "A",
       "공식 CAD 셸 솔리드(기수 상·하)의 우리 좌표 x 최대", "outputs/meshfix_matrice4e.json",
       "셸만(암 제외). 우리 잣대는 body 그룹에서 |y| ≤ 1.15×캐노피 반폭인 삼각형의 x 최대.",
       "independent", 0.3,
       "우리 «셸 자르기»(|y| 문턱)가 CAD 의 솔리드 선택과 정확히 같지는 않다. 문턱을 1.0~1.3 배로 "
       "흔들었을 때 x 최대가 움직이는 폭이 0.3 mm 안이라 그 값을 쓴다."),
    _R("M4E-05", "matrice4e", "body", "셸 뒤끝 x", "shell_tail_x",
       -75.59, "cad_m4t", "A",
       "공식 CAD 셸 솔리드의 우리 좌표 x 최소", "outputs/meshfix_matrice4e.json",
       "M4E-04 와 같은 잣대의 반대쪽.", "independent", 0.3, "M4E-04 와 같은 이유."),
    _R("M4E-06", "matrice4e", "body", "셸 배(아래) z", "shell_belly_z",
       -30.81, "cad_m4t", "A",
       "공식 CAD 셸 하부 커버의 우리 좌표 z 최소", "outputs/meshfix_matrice4e.json",
       "셸 아랫면. 우리 잣대는 같은 «셸 자르기» 안의 z 최소.",
       "independent", 0.3, "M4E-04 와 같은 이유."),
    _R("M4E-07", "matrice4e", "body", "셸 등(위) z", "shell_crown_z",
       69.11, "cad_m4t", "A",
       "공식 CAD 셸 상부 커버의 우리 좌표 z 최대", "outputs/meshfix_matrice4e.json",
       "셸 윗면(RTK 터렛 제외).", "independent", 0.3, "M4E-04 와 같은 이유."),
    _R("M4E-08", "matrice4e", "gear", "접지점 z", "gear_bottom_z",
       -59.82, "cad_m4t", "A",
       "공식 CAD 발 접지점의 우리 좌표 z", "outputs/meshfix_matrice4e.json",
       "다리 맨 아래. 우리 잣대는 gear·gear_cf 그룹의 z 최소.",
       "independent", 0.0, "같은 점을 재므로 정의 차이가 없다."),
    _R("M4E-09", "matrice4e", "accent", "RTK 터렛 꼭대기 z", "top_z",
       89.70, "cad_m4t", "A",
       "공식 CAD RTK 터렛 상단(우리 좌표)", "outputs/meshfix_matrice4e.json",
       "프롭 제외 최고점. GNSS 커버(+2.0 mm)는 CAD 도 우리도 안 센다.",
       "independent", 0.0, "같은 점을 재므로 정의 차이가 없다."),
    _R("M4E-10", "matrice4e", "motor", "앞 로터 반경", "rotor0_r",
       227.16, "cad_m4t", "A",
       "공식 CAD 앞 모터축 (x 139.49, y 179.28) → r 227.16", "outputs/meshfix_matrice4e.json",
       "로터축의 xy 반경. 우리 잣대는 프롭 군집 xy 무게중심의 반경(2날 프롭이라 축 위에 온다).",
       "independent", 0.0, "같은 양을 잰다."),
    _R("M4E-11", "matrice4e", "motor", "뒤 로터 반경", "rotor1_r",
       209.92, "cad_m4t", "A",
       "공식 CAD 뒤 모터축 (x −139.49, y 156.87) → r 209.92", "outputs/meshfix_matrice4e.json",
       "M4E-10 의 뒤쪽.", "independent", 0.0, "같은 양을 잰다."),
    _R("M4E-12", "matrice4e", "motor", "앞 로터 방위각", "rotor0_az",
       52.115, "cad_m4t", "A",
       "공식 CAD 앞 모터축 방위각[deg]", "outputs/meshfix_matrice4e.json",
       "⚠ 단위가 도(deg)다 — 잔차·허용오차도 도로 읽는다(아래 unit 필드).",
       "independent", 0.0, "같은 양을 잰다.", None,
       "unit=deg. u_ref 는 반경 227 mm 에서 0.187 mm 가 만드는 각도(0.047°)로 환산해 쓴다."),
    _R("M4E-13", "matrice4e", "motor", "앞 모터 부품 z 최저(벨 밑동)", "motor_z0_lo",
       -8.51, "cad_m4t", "A",
       "공식 CAD 앞 벨 z 범위 [−8.51, 8.03] 의 아래끝", "outputs/meshfix_matrice4e.json",
       "모터 벨 아랫면. 우리 'motor' 부품에는 나사 포스트가 없어 부품 z 최소가 곧 벨 밑동이다.",
       "independent", 0.0, "같은 면을 잰다."),
    _R("M4E-14", "matrice4e", "motor", "모터 벨 높이", "motor_h0",
       16.54, "cad_m4t", "A",
       "공식 CAD 앞 벨 z 범위 [−8.51, 8.03] 의 폭 — ⚠**유도값**이다(원장에 16.54 라는 수는 없다)",
       "outputs/meshfix_matrice4e.json",
       "벨 z 폭. 우리 잣대는 'motor' 부품 z 폭.",
       "independent", 0.0, "같은 양을 잰다.",
       source_values=(-8.51, 8.03)),
    _R("M4E-15", "matrice4e", "gear", "앞 발 반경", "foot_r_front",
       216.52, "cad_m4t", "A",
       "공식 CAD 앞 발 (x 135.23, y 169.10) → r 216.52", "outputs/meshfix_matrice4e.json",
       "발 중심의 xy 반경. 우리 잣대는 gear 부품 중심의 반경.",
       "independent", 2.0,
       "CAD 값은 발의 «접지 자리» 이고 우리 값은 다리 부품 전체의 bbox 중심이라 원뿔이 기울면 "
       "둘이 어긋난다. 다리 벌림 20°·높이 53 mm 에서 그 어긋남은 최대 2 mm 다."),
    _R("M4E-16", "matrice4e", "gear", "뒤 발 반경", "foot_r_rear",
       208.54, "cad_m4t", "A",
       "공식 CAD 뒤 발 (x −139.74, y 154.79) → r 208.54", "outputs/meshfix_matrice4e.json",
       "M4E-15 의 뒤쪽.", "independent", 2.0, "M4E-15 와 같은 이유."),
    #  ⛔ M4T/M4E 규칙 — 짐벌 «치수» 는 사진이 참값이고 CAD 를 쓰면 안 된다.
    _R("M4E-17", "matrice4e", "camera", "짐벌 폭(좌우)", "gimbal_W",
       59.0, "photo", "B",
       "제품 사진 계측(59×47×52 mm). ⛔ M4T CAD 는 **짐벌이 다른 물건**이라 쓰지 않는다",
       "outputs/meshfix_matrice4e.json",
       "⚠ 우리 잣대는 카메라 그룹 최전방 부품의 bbox 라 크래들·요크까지 센다. 사진 값은 짐벌 "
       "몸체만이다 ⇒ 우리가 더 크게 나오는 것이 정상이고, 이 행은 **경보용이 아니라 기록용**이다.",
       "independent", 0.0,
       "정의 차이가 크지만 그 크기를 모른다 ⇒ u_def 로 감추지 않고 note 에 적고 informational 로 둔다.",
       15.0,
       "informational — 정의가 달라 판정하지 않는다. 밴드 ±15 % 는 저장소의 사진 유래 값 관례."),
    _R("M4E-18", "matrice4e", "camera", "짐벌 매달린 자리 x", "gimbal_cx",
       148.3, "cad_m4t", "A",
       "공식 CAD 로 정정된 짐벌 **부착 위치**(F10). ⭐위치는 기체 쪽 형상이라 M4T 를 써도 된다",
       "outputs/meshfix_matrice4e.json",
       "짐벌 부품 bbox 중심 x. 규칙: **치수는 금지, 위치는 허용**.",
       "partly_circular", 1.0,
       "F10 이 코드에 적용되면 이 값은 설계 목표가 되어 순환이 된다. 그래도 «적용됐는가» 를 "
       "감시할 값어치가 있어 싣는다. u_def 1.0 mm 는 부품 bbox 중심 ↔ 크래들 부착점의 차이."),
    _R("M4E-19", "matrice4e", "battery", "배터리 상자 길이", "battery_L",
       145.47, "pub_0p1mm", "B",
       "DJI 공표 배터리(TB4x) 치수에서 온 상자(F11, source='published spec')",
       "outputs/meshfix_matrice4e.json",
       "가장 큰 battery 부품의 x 폭.", "circular", 0.0,
       "⛔ F11 이 이미 적용돼 이 값이 코드 상수가 됐다 ⇒ 순환. 회귀 감시용으로만 싣는다."),

    _R("M4E-20", "matrice4e", "prop", "프롭 스윕 지름", "prop_dia",
       274.0, "pub_1mm", "A",
       "DJI Matrice 4 시리즈 매뉴얼 p.101 프롭표(1154F 27.4×13.7 cm). 표준 1157F 도 같은 지름",
       "src/drones.py :: DRONES['matrice4e'].note",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ `prop_dia_mm=274` 가 같은 공표에서 왔다 ⇒ 순환."),

    # ====================== mini2 — DJI 공식 GLB [A] ======================= #
    _R("MI2-01", "mini2", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       159.113, "glb_mini2", "A",
       "DJI 공식 GLB(WM161 펼침) 프롭 제외 bbox 길이 — 이 라운드가 GLB 를 다시 열어 재현",
       "outputs/meshdef_mini2_glb.json",
       "프롭 8장을 뺀 bbox. 우리 잣대도 프롭 그룹을 뺀 bbox 다.",
       "partly_circular", 0.0,
       "정의가 같다. 단 body_l_mm=159 가 셸 비율의 분모라 부분적으로 순환이다."),
    _R("MI2-02", "mini2", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       203.434, "glb_mini2", "A",
       "같은 GLB 의 프롭 제외 bbox 폭", "outputs/meshdef_mini2_glb.json",
       "MI2-01 과 같은 잣대의 y 축.", "partly_circular", 0.0, "정의가 같다."),
    _R("MI2-03", "mini2", "airframe", "펼침 높이(프롭 제외)", "frame_H",
       55.977, "glb_mini2", "A",
       "같은 GLB 의 프롭 제외 bbox 높이", "outputs/meshdef_mini2_glb.json",
       "MI2-01 과 같은 잣대의 z 축.", "circular", 0.0,
       "⛔ `envelope_mm=(None,None,56)` 이 높이를 강제한다 ⇒ 순환. 강제가 풀렸는지만 본다."),
    _R("MI2-04", "mini2", "motor", "모터축 대각(휠베이스)", "wheelbase",
       213.051, "glb_mini2", "A",
       "GLB 모터 벨 4개의 축 사이 대각(좌우 두 대각의 차 0.0004 mm)",
       "outputs/meshdef_mini2_glb.json",
       "마주보는 로터축 거리. 우리 잣대는 프롭 군집 중심 사이 최대거리.",
       "partly_circular", 0.0, "정의가 같다. rotor_r/deg 가 이 CAD 에서 나왔으므로 부분 순환."),
    _R("MI2-05", "mini2", "motor", "모터 벨 지름", "motor_od0",
       18.203, "glb_mini2", "A",
       "GLB 앞 모터 벨 파트(polySurface76) bbox 18.203×18.133", "outputs/meshdef_mini2_glb.json",
       "벨 최대 지름. 우리 잣대는 모터 부품의 자기축 최대지름 ×2.",
       "partly_circular", 0.035,
       "GLB 벨의 x·y bbox 가 18.203/18.133 로 0.07 mm 다르다(원통이 다각형으로 구워져 있다) "
       "⇒ 그 절반 0.035 mm 를 정의 불확도로 쓴다."),
    _R("MI2-06", "mini2", "motor", "앞 모터 벨 밑동 z", "motor_z0_lo",
       18.886, "glb_mini2", "A",
       "GLB 앞 벨 밑동 z(우리 프레임)", "outputs/meshdef_mini2_glb.json",
       "벨 아랫면. 우리 'motor' 부품은 나사 포스트를 **위쪽에** 달고 있어 z 최소는 여전히 벨 밑동이다.",
       "independent", 0.0, "같은 면을 잰다."),
    _R("MI2-07", "mini2", "motor", "앞뒤 벨 밑동 높이차", "motor_z_sep",
       21.801, "glb_mini2", "A",
       "GLB 앞 벨 밑동 − 뒤 벨 밑동", "outputs/meshdef_mini2_glb.json",
       "두 로터 평면의 높이차. 우리 잣대도 두 모터 부품 z 최소의 차.",
       "independent", 0.0, "같은 양을 잰다."),
    _R("MI2-08", "mini2", "camera", "짐벌 상자 길이", "gimbal_L",
       40.567, "glb_mini2", "A",
       "GLB 짐벌 파트(polySurface204) bbox 40.567×32.239×34.012",
       "outputs/meshdef_mini2_glb.json",
       "짐벌 몸체 bbox. 우리 잣대는 카메라 그룹 최전방 부품 bbox.",
       "circular", 0.0,
       "⛔ 이 기체의 짐벌 인자는 그 파트에서 역산됐다(원장 K10) ⇒ 순환. 값이 메쉬에 실렸는지만 본다."),
    _R("MI2-09", "mini2", "camera", "짐벌 상자 폭", "gimbal_W",
       32.239, "glb_mini2", "A",
       "같은 파트의 y 폭", "outputs/meshdef_mini2_glb.json",
       "MI2-08 과 같은 잣대의 y.", "circular", 0.0, "MI2-08 과 같은 이유."),
    _R("MI2-10", "mini2", "camera", "짐벌 상자 높이", "gimbal_H",
       34.012, "glb_mini2", "A",
       "같은 파트의 z 폭", "outputs/meshdef_mini2_glb.json",
       "MI2-08 과 같은 잣대의 z.", "circular", 0.0, "MI2-08 과 같은 이유."),
    _R("MI2-11", "mini2", "prop", "프롭 스윕 지름", "prop_dia",
       119.233, "glb_mini2", "A",
       "GLB 프롭 날을 **모터축 기준**으로 잰 지름(앞 118.591 · 뒤 119.875 의 평균)",
       "outputs/meshdef_mini2_glb.json",
       "⭐ 회전 중심이 모터축이므로 «축 기준» 이 물리적으로 옳은 지름이다(원장 C3). "
       "우리 잣대는 프롭 군집 무게중심 기준이라 축과 0.4~1.1 mm 어긋날 수 있다.",
       "independent", 0.75,
       "GLB 에서 날 메쉬 중심이 모터축에서 앞 0.368 · 뒤 1.121 mm 벗어나 있다(원장 C3) "
       "⇒ 그 평균 0.75 mm 를 정의 불확도로 쓴다."),
    _R("MI2-12", "mini2", "gear", "기체 최저점 z", "bottom_z",
       -24.52, "glb_mini2", "A",
       "GLB 프롭 제외 최저점", "outputs/meshdef_mini2_glb.json",
       "⛔ 원장이 스스로 «이건 정의이지 측정이 아니다» 라고 적었다 — 원점 z 를 이 점으로 **정의**했다.",
       "circular", 0.0,
       "정의로 고정된 값이라 잔차가 0 인 것은 당연하다. 독립 증거는 MI2-03 의 세로 span 뿐이다."),

    # ====================== x500v2 — Holybro 공식 STEP [A] ================= #
    _R("X50-01", "x500v2", "deck", "판 한 변", "plate_span",
       143.72, "step_x500", "A",
       "공식 STEP 하판 외곽(공표 144)", "outputs/x500v2_cad.json",
       "판의 마주보는 직선변 사이. 우리 잣대는 deck 그룹의 판 부품 최대 변.",
       "circular", 0.0, "⛔ `plate_mm` 이 이 CAD 값으로 채워져 있다 ⇒ 순환(회귀 감시용)."),
    _R("X50-02", "x500v2", "deck", "판 두께", "plate_t",
       2.0, "step_x500", "A",
       "공식 STEP 하판 상·하면 차(공표 2)", "outputs/x500v2_cad.json",
       "판 한 장의 두께.", "circular", 0.0, "X50-01 과 같은 이유."),
    _R("X50-03", "x500v2", "deck", "판 사이 간격", "plate_gap",
       28.0, "step_x500", "A",
       "공식 STEP 하판 윗면 → 상판 아랫면(공표 28)", "outputs/x500v2_cad.json",
       "두 판의 **마주보는 면 사이 빈 간격**.", "circular", 0.0, "X50-01 과 같은 이유."),
    _R("X50-04", "x500v2", "deck", "판 스택 총높이", "plate_stack",
       32.0, "step_x500", "A",
       "공식 STEP 하판 아랫면 → 상판 윗면", "outputs/x500v2_cad.json",
       "판+간격+판.", "circular", 0.0, "X50-01 과 같은 이유."),
    _R("X50-05", "x500v2", "motor", "모터축 대각(휠베이스)", "wheelbase",
       502.8, "step_x500", "A",
       "공식 STEP 대각 모터 간격 502.8 mm — ⭐공표 500 은 **반올림**이고 CAD 가 참값이다",
       "outputs/x500v2_cad.json",
       "마주보는 모터축 거리. 우리 잣대는 프롭 군집 중심 사이 최대거리.",
       "independent", 0.0,
       "정의가 같다. ⭐이 행은 **독립**이다 — 우리 diagonal_mm 은 공표 500 이라 CAD 502.8 과 "
       "다른 수이고, 잔차가 그 차이를 그대로 드러낸다."),
    _R("X50-06", "x500v2", "motor", "모터 벨 지름", "motor_od0",
       28.0, "step_x500", "A",
       "AIR2216II 모터 단품 STEP 의 최대 반복 원통면(판매페이지 캔 외경 28 과 정합)",
       "outputs/x500v2_cad.json",
       "벨 캔 외경. 우리 잣대는 모터 부품의 자기축 최대지름.",
       "independent", 0.0, "정의가 같다."),
    _R("X50-07", "x500v2", "gear", "다리 높이(하판 아랫면 → 최저점)", "gear_h_below_deck",
       215.28, "step_x500", "A",
       "공식 STEP 하판 아랫면 → 폼 최하점(공표 215 를 CAD 가 재현)", "outputs/x500v2_cad.json",
       "판 밑에서 접지까지. 우리 잣대는 (판 스택 절반) − (gear 최저 z).",
       "circular", 0.0, "⛔ `gear_h_mm=215` 가 코드에 있다 ⇒ 순환(회귀 감시용)."),
    _R("X50-08", "x500v2", "gear", "좌우 스키드 축 간격", "skid_track",
       239.91, "step_x500", "A",
       "공식 STEP 좌우 스키드 축 간격. ⚠사진 실측 180 mm 는 시차 오류였다",
       "outputs/x500v2_cad.json",
       "가로 튜브 두 개의 축 사이. 우리 잣대는 x 로 길쭉한 gear 부품 두 개의 y 중심 차.",
       "independent", 0.0, "정의가 같다."),
    _R("X50-10", "x500v2", "arm", "암 튜브 외경", "arm_od",
       16.0, "step_x500", "A",
       "Holybro 공표 16 mm; 공식 STEP 의 클램프 보어(뿌리 15.90 · 모터끝 16.00)가 확증. "
       "⚠CAD 튜브 솔리드 자체는 15.4 로 언더사이즈로 그려져 있다(클램프 여유)",
       "outputs/x500v2_cad.json",
       "카본 파이프 바깥지름. 우리 잣대는 arm 그룹의 z 폭(수평 튜브라 z 폭 = 지름).",
       "circular", 0.0, "⛔ `arm_od_mm=16.0` 이 이 CAD 에서 왔다 ⇒ 순환(회귀 감시용)."),
    _R("X50-11", "x500v2", "deck", "페이로드 레일 좌우 간격", "rail_track",
       60.0, "step_x500", "A",
       "공식 STEP 좌우 레일 축 간격", "outputs/x500v2_cad.json",
       "레일 두 개의 y 중심 차. 우리 잣대는 deck 그룹에서 «한 축으로만 아주 긴» 부품 둘의 y 중심 차.",
       "circular", 0.0, "⛔ 레일 위치가 이 CAD 에서 왔다 ⇒ 순환."),
    _R("X50-12", "x500v2", "deck", "페이로드 레일 길이", "rail_len",
       250.0, "step_x500", "A",
       "공식 STEP 레일 길이(공표 250 과 일치)", "outputs/x500v2_cad.json",
       "레일 한 개의 x 길이.", "circular", 0.0, "⛔ 같은 이유 ⇒ 순환."),
    _R("X50-13", "x500v2", "pcb", "전원모듈 PCB 길이", "pcb_L",
       55.0, "step_x500", "A",
       "공식 STEP 의 PM06 전원모듈 조립 bbox 55×11.99×35 (CAD 축: x 전방 · y 상방 · z 좌우)",
       "outputs/x500v2_cad.json",
       "PCB 앞뒤 길이.", "circular", 0.0,
       "⛔ `drone_cad` 의 `pm06_mm` 이 이 CAD 에서 왔다(코드 주석이 그렇게 적는다) ⇒ 순환."),
    _R("X50-14", "x500v2", "pcb", "전원모듈 PCB 폭", "pcb_W",
       35.0, "step_x500", "A",
       "같은 CAD bbox 의 좌우(35.0)", "outputs/x500v2_cad.json",
       "PCB 좌우 폭. ⚠CAD 축이 우리와 달라 z_cad = 좌우다.", "circular", 0.0, "X50-13 과 같다."),
    _R("X50-15", "x500v2", "pcb", "전원모듈 PCB 두께", "pcb_H",
       11.99, "step_x500", "A",
       "공식 STEP 의 PM06 **조립 bbox** 상하 11.99 mm(커넥터·스탠드오프 포함)",
       "outputs/x500v2_cad.json",
       "⚠**정의가 둘이다** — 같은 CAD 에서 «조립 bbox» 는 11.99 이고 «보드 모서리 bbox» 는 "
       "5.19 다(drone_cad.py 의 pm06 주석이 그렇게 적는다). 우리 메쉬는 후자(5.2)를 쓴다. "
       "즉 이 잔차는 결함이 아니라 **다른 물건을 잰 것**이다.",
       "circular", 0.0,
       "두 정의의 차(6.8 mm)는 커넥터·스탠드오프 높이이고 그 값을 우리가 따로 재지 않았다 ⇒ "
       "u_def 로 감추지 않고 «기록만» 으로 둔다."),
    _R("X50-09", "x500v2", "prop", "프롭 스윕 지름", "prop_dia",
       254.0, "pub_1mm", "B",
       "Holybro X500 V2 킷 공표 프롭 1045(10×4.5 in = 254 mm). ⚠CAD 에 프롭은 없다",
       "assets/meshes/reference/SOURCES.md",
       "10 in 공칭 지름. 우리 잣대는 스윕 지름.",
       "circular", 0.0, "⛔ `prop_dia_mm=254` 가 같은 공표에서 왔다 ⇒ 순환."),

    # ====================== mini5pro — 공표 제원 [A-pub] =================== #
    _R("M5P-01", "mini5pro", "airframe", "펼침 길이(프롭 **포함**)", "sweep_L",
       304.0, "pub_1mm", "A",
       "DJI 공식 스펙 페이지 «Unfolded 304×380×91 mm (프로펠러 포함)» — 매뉴얼 PDF 로 교차확인",
       "docs/drone_specs_2026.json",
       "⭐ 프롭 «포함» 이므로 멈춘 날의 bbox 가 아니라 **스윕 디스크** 외형과 견줘야 한다. "
       "우리 잣대는 로터 중심 ± 스윕 반경.",
       "partly_circular", 0.0,
       "정의가 같다. 단 rotor_r_mm 이 이 공표 외형에서 유도됐을 수 있어 부분 순환으로 적는다."),
    _R("M5P-02", "mini5pro", "airframe", "펼침 폭(프롭 **포함**)", "sweep_W",
       380.0, "pub_1mm", "A",
       "같은 공표의 폭", "docs/drone_specs_2026.json",
       "M5P-01 과 같은 잣대의 y.", "partly_circular", 0.0, "M5P-01 과 같다."),
    _R("M5P-03", "mini5pro", "prop", "프롭 스윕 지름", "prop_dia",
       152.4, "pub_0p1mm", "A",
       "DJI 매뉴얼 «6028F 152.4×71.1 mm (지름×피치)»", "docs/drone_specs_2026.json",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ `prop_dia_mm` 이 같은 공표에서 왔다 ⇒ 순환."),
    _R("M5P-04", "mini5pro", "battery", "배터리 길이", "battery_L",
       86.10, "pub_0p1mm", "A",
       "DJI 매뉴얼 배터리 BWXNN5-2788-7.0 «86.10×54.89×24.85 mm»",
       "docs/drone_specs_2026.json",
       "배터리 팩 바깥치수. 우리 잣대는 battery 그룹의 가장 큰 부품 bbox.",
       "independent", 0.0,
       "⭐**독립**이다 — 우리 배터리 상자는 셸 비율에서 나왔고 이 공표값을 쓴 적이 없다."),
    _R("M5P-05", "mini5pro", "battery", "배터리 폭", "battery_W",
       54.89, "pub_0p1mm", "A",
       "같은 공표", "docs/drone_specs_2026.json", "M5P-04 와 같은 잣대의 y.",
       "independent", 0.0, "M5P-04 와 같다."),
    _R("M5P-06", "mini5pro", "battery", "배터리 높이", "battery_H",
       24.85, "pub_0p1mm", "A",
       "같은 공표", "docs/drone_specs_2026.json", "M5P-04 와 같은 잣대의 z.",
       "independent", 0.0, "M5P-04 와 같다."),
    _R("M5P-07", "mini5pro", "gear", "착륙다리 길이", None, None, "photo", "B",
       "⚠ DJI 는 다리 치수를 공개하지 않는다. 사진 계측 31.0 mm ±15 % 가 저장소의 유일한 근거이고, "
       "그 사진 계측은 **우리 상수 자체**라 외부 참값이 아니다",
       "src/drones.py :: DRONES['mini5pro'].note",
       "빈칸으로 남긴다 — 가짜 통과보다 낫다.",
       "circular", 0.0, "참값이 없다.", 15.0,
       "모름 — 외부 참값 없음. 이 칸은 «장담 못 한다» 로 인증서에 실린다."),

    # ====================== mavic4pro — 공표 제원 [A-pub] ================== #
    _R("M4P-01", "mavic4pro", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       328.7, "pub_0p1mm", "A",
       "DJI 공표 «Unfolded 328.7×390.5×135.2 mm (프로펠러 제외)»",
       "docs/drone_specs_2026.json",
       "프롭 제외 bbox. 우리 잣대도 같다.",
       "independent", 0.0,
       "⭐**독립**이다 — 2026-07-30 라운드가 L/W 강제를 **풀었다**(note). 지금 프레임 길이는 "
       "«주장» 이 아니라 로터 배치와 짐벌 돌출에서 **지어진** 값이다."),
    _R("M4P-02", "mavic4pro", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       390.5, "pub_0p1mm", "A",
       "같은 공표의 폭", "docs/drone_specs_2026.json", "M4P-01 과 같은 잣대의 y.",
       "independent", 0.0, "M4P-01 과 같다."),
    _R("M4P-03", "mavic4pro", "airframe", "펼침 높이(프롭 제외)", "frame_H",
       135.2, "pub_0p1mm", "A",
       "같은 공표의 높이", "docs/drone_specs_2026.json", "M4P-01 과 같은 잣대의 z.",
       "circular", 0.0, "⛔ `envelope_mm=(None,None,135.2)` 가 강제한다 ⇒ 순환."),
    _R("M4P-04", "mavic4pro", "prop", "프롭 스윕 지름", "prop_dia",
       267.0, "pub_1mm", "A",
       "DJI 부품표 1158F «26.7×14.7 cm»", "src/drones.py :: DRONES['mavic4pro'].note",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ `prop_dia_mm` 이 같은 공표에서 왔다 ⇒ 순환."),

    # ====================== phantom3 / phantom4 — 공표 도면 [A-pub] ======== #
    _R("P3-01", "phantom3", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       289.5, "pub_0p1mm", "A",
       "DJI 치수 도면 «289.5×289.0×185.0 mm, 프로펠러 제외, 높이는 모터 상단→발»",
       "src/drones.py :: DRONES['phantom3'].note",
       "프롭 제외 bbox 길이.", "partly_circular", 0.0,
       "rotor_deg 45° 가 이 두 공표 평면치수에서 유도됐다(note) ⇒ 부분 순환."),
    _R("P3-02", "phantom3", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       289.0, "pub_0p1mm", "A",
       "같은 도면의 폭", "src/drones.py :: DRONES['phantom3'].note",
       "P3-01 과 같은 잣대의 y.", "partly_circular", 0.0, "P3-01 과 같다."),
    _R("P3-03", "phantom3", "motor", "모터축 대각", "wheelbase",
       350.0, "pub_1mm", "A",
       "DJI 공표 대각 350 mm(Pro/Adv/SE/Standard 공용)",
       "src/drones.py :: DRONES['phantom3'].note",
       "마주보는 모터축 거리.", "circular", 0.0, "⛔ `diagonal_mm=350` 이 같은 공표다 ⇒ 순환."),
    _R("P3-04", "phantom3", "airframe", "높이(모터 상단 → 발)", "motor_top_to_gear_bottom",
       185.0, "pub_0p1mm", "A",
       "DJI 치수 도면의 높이 185.0 mm — ⭐그 도면이 **모터 상단에서 발까지**를 잰다는 것은 "
       "저장소의 픽셀 감사가 확정했다(프롭 위를 기준으로 잡으면 206.4 mm = +11.6 % 가 된다)",
       "src/drones.py :: DRONES['phantom3'].note",
       "⭐정의가 bbox 높이와 다르다 — 우리 잣대도 «모터 부품 최고점 − gear 최저점» 으로 맞췄다. "
       "envelope_mm 이 강제하는 것은 bbox 높이이지 이 수가 아니므로 이 행은 강제를 안 받는다.",
       "independent", 0.0,
       "참값의 정의를 잣대가 그대로 따라간다. 우리 모터 부품 꼭대기가 실물의 모터 캡 꼭대기와 "
       "같은 면인지는 확인됐다(프롭은 그 위에 따로 얹힌다)."),
    _R("P3-05", "phantom3", "prop", "프롭 스윕 지름", "prop_dia",
       240.0, "pub_1mm", "A",
       "DJI E305 추진계 표의 9450 «24×12.7 cm»(phantom4 와 같은 부품번호)",
       "src/drones.py :: DRONES['phantom3'].note",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ 같은 공표에서 왔다 ⇒ 순환."),
    _R("P4-01", "phantom4", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       289.5, "pub_0p1mm", "A",
       "DJI 공표 289.5×289.5×196 mm", "docs/drone_specs_2026.json",
       "프롭 제외 bbox 길이.", "independent", 0.0,
       "⭐**독립**이다 — phantom4 는 envelope L/W 강제가 없고 rotor_deg 도 45° 고정이라 "
       "프레임 길이가 셸·암에서 지어진다."),
    _R("P4-02", "phantom4", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       289.5, "pub_0p1mm", "A",
       "같은 공표", "docs/drone_specs_2026.json", "P4-01 과 같은 잣대의 y.",
       "independent", 0.0, "P4-01 과 같다."),
    _R("P4-03", "phantom4", "prop", "프롭 스윕 지름", "prop_dia",
       240.0, "pub_1mm", "A",
       "DJI 프롭 치수표 9450 «24×12.7 cm»", "src/drones.py :: DRONES['phantom4'].note",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ 같은 공표에서 왔다 ⇒ 순환."),

    # ====================== typhoonh480 — Yuneec 공표 + 시뮬 CAD =========== #
    _R("TY-01", "typhoonh480", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       457.0, "pub_1mm", "A",
       "Yuneec 공표 기체 크기 520×457×310 mm(폭 우선 표기; CAD 가 520=좌우·457=전후를 확정)",
       "assets/meshes/reference/SOURCES.md",
       "프롭 제외 bbox 길이(전후).", "independent", 0.0,
       "⭐**독립**이다 — envelope 은 높이만 강제하고 L/W 는 안 건다(note)."),
    _R("TY-02", "typhoonh480", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       520.0, "pub_1mm", "A",
       "같은 공표의 좌우", "assets/meshes/reference/SOURCES.md",
       "TY-01 과 같은 잣대의 y.", "independent", 0.0, "TY-01 과 같다."),
    _R("TY-03", "typhoonh480", "airframe", "팁 외형(프롭 **포함** 폭)", "sweep_W",
       711.0, "pub_1mm", "A",
       "Yuneec 공표 팁-대-팁 711 mm(480 대각 + 230 프롭으로도 재현)",
       "src/drones.py :: DRONES['typhoonh480'].note",
       "프롭 스윕까지 포함한 좌우. 우리 잣대는 스윕 디스크 외형.",
       "partly_circular", 0.0,
       "diagonal 480 과 prop_dia 230.2 가 둘 다 공표/CAD 실측이고, 이 행은 그 둘의 «합» 이 "
       "세 번째 공표값과 맞는지를 본다 ⇒ 완전 순환은 아니다."),
    _R("TY-04", "typhoonh480", "prop", "프롭 스윕 지름", "prop_dia",
       230.098, "pub_0p1mm", "B-",
       "Yuneec 시뮬레이터 자산(rotors_simulator STL)에서 실측한 프롭 지름 — ⚠제조사 CAD 가 아니다",
       "outputs/reference_props.json",
       "프롭 스윕 지름.", "circular", 0.0, "⛔ `prop_dia_mm=230.2` 가 이 실측에서 왔다 ⇒ 순환."),

    # ====================== m350rtk — DJI 공표 [A-pub] ===================== #
    _R("M35-01", "m350rtk", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       810.0, "pub_1mm", "A",
       "DJI 공표 «펼침(프롭 제외) 810×670 mm»", "src/drones.py :: DRONES['m350rtk'].note",
       "프롭 제외 bbox 길이.", "partly_circular", 0.0,
       "rotor_deg 38.65° 가 이 두 공표 평면치수와 895 휠베이스에서 유도됐다(note) ⇒ 부분 순환. "
       "그래도 **잔차는 0 이 아니다** — 유도는 모터축까지이고 bbox 는 암 끝·프롭 허브가 정한다."),
    _R("M35-02", "m350rtk", "airframe", "펼침 폭(프롭 제외)", "frame_W",
       670.0, "pub_1mm", "A",
       "같은 공표", "src/drones.py :: DRONES['m350rtk'].note",
       "M35-01 과 같은 잣대의 y.", "partly_circular", 0.0, "M35-01 과 같다."),
    _R("M35-03", "m350rtk", "motor", "모터축 대각", "wheelbase",
       895.0, "pub_1mm", "A",
       "DJI 공표 휠베이스 895 mm", "src/drones.py :: DRONES['m350rtk'].note",
       "마주보는 모터축 거리.", "circular", 0.0, "⛔ `diagonal_mm=895` 가 같은 공표다 ⇒ 순환."),

    _R("M35-04", "m350rtk", "prop", "프롭 스윕 지름", "prop_dia",
       533.4, "pub_1mm", "C",
       "⚠**2차 출처**다 — DJI 는 모델명(2110s)만 공표하고 기하는 안 낸다. 533.4 mm 는 "
       "«21×10 in» 이라는 유통사 수치다(기종 note 가 스스로 SECONDARY 라고 적는다)",
       "src/drones.py :: DRONES['m350rtk'].note",
       "프롭 공칭 지름.", "circular", 0.0,
       "⛔ `prop_dia_mm` 이 같은 2차 출처에서 왔다 ⇒ 순환. 등급도 [C] 로 낮춘다."),

    # ====================== s1000plus — DJI 공표 [A-pub] =================== #
    _R("S10-01", "s1000plus", "airframe", "펼침 길이(프롭 제외)", "frame_L",
       1016.0, "pub_1mm", "A",
       "DJI 공표 «펼침 1016×1016×380 mm»", "docs/drone_specs_2026.json",
       "프롭 제외 bbox 길이.", "circular", 0.0,
       "⛔ `envelope_mm=(1016,1016,380)` 이 세 축을 다 강제한다 ⇒ 완전 순환. 강제 감시용."),
    _R("S10-02", "s1000plus", "motor", "모터축 대각", "wheelbase",
       1045.0, "pub_1mm", "A",
       "DJI 공표 휠베이스 1045 mm", "docs/drone_specs_2026.json",
       "마주보는 모터축 거리.", "circular", 0.0, "⛔ 같은 공표 ⇒ 순환."),
    _R("S10-03", "s1000plus", "prop", "프롭 스윕 지름", "prop_dia",
       381.0, "pub_1mm", "A",
       "DJI 공표 1552 프롭 15 in = 381 mm", "docs/drone_specs_2026.json",
       "프롭 공칭 지름.", "circular", 0.0, "⛔ 같은 공표 ⇒ 순환."),
]


#  각도 단위인 행(잔차를 도로 읽는 행)의 목록 — 실수로 mm 로 읽지 않도록 여기 한 곳에 둔다.
_DEG_ROWS = {"M4E-12"}
#  판정하지 않고 기록만 하는 행(정의가 달라 견줄 수 없는 것) — 이유는 각 행의 note 에 있다.
_INFORMATIONAL = {"M4E-17", "M5P-07", "X50-15"}


# --------------------------------------------------------------------------- #
#  ④ 대조 실행
# --------------------------------------------------------------------------- #
def _tolerance(row: DimRef, rl: MeshRuler | None) -> dict:
    """행의 확장불확도 U[mm 또는 deg] 와 그 유도 내역."""
    if row.ref_mm is None:
        #  참값이 없으면 허용오차도 없다 — NaN 을 흘리지 않고 «모름» 을 명시한다.
        return dict(u_ref=None, u_ref_why="참값 없음 — 허용오차를 유도할 근거가 없다",
                    u_def=None, u_def_why=row.u_def_why, u_disc=None,
                    u_disc_why=_U_DISC_ZERO_WHY, u_combined=None, k=K_COVERAGE, U=None,
                    formula="해당 없음(참값 없음)")
    u_ref, why_ref = _u_ref(row)
    u_def = float(row.u_def_mm)
    fn = _U_DISC.get(row.measure)
    if fn is not None and rl is not None:
        u_disc = float(fn(rl))
        why_disc = ("다면체 원통을 지름으로 잴 때 외접·내접이 다르다 — 실측 편차/√3")
    else:
        u_disc, why_disc = 0.0, _U_DISC_ZERO_WHY
    if row.rid in _DEG_ROWS and row.ref_mm is not None:
        #  각도 행 — 길이 불확도를 반경으로 나눠 각도로 환산한다.
        r_mm = 227.16
        u_ref = math.degrees(u_ref / r_mm)
        u_def = math.degrees(u_def / r_mm) if u_def else 0.0
        why_ref += f" → 반경 {r_mm} mm 에서 각도로 환산"
    u_c = math.sqrt(u_ref ** 2 + u_def ** 2 + u_disc ** 2)
    return dict(u_ref=round(u_ref, 4), u_ref_why=why_ref,
                u_def=round(u_def, 4), u_def_why=row.u_def_why,
                u_disc=round(u_disc, 4), u_disc_why=why_disc,
                u_combined=round(u_c, 4), k=K_COVERAGE, U=round(K_COVERAGE * u_c, 4),
                formula="U = k·√(u_ref² + u_def² + u_disc²), k = 2")


def check_key(key: str, mesh=None, declared: dict | None = None) -> dict:
    """한 기체의 **외부 기준 대조**. declared 를 주면 «회귀 판정» 도 같이 낸다."""
    from drones import DRONES
    spec = DRONES[key]
    rl = ruler(spec, mesh)
    rows, n_pass, n_fail, n_info, n_unknown = [], 0, 0, 0, 0
    for row in REFS:
        if row.key != key:
            continue
        tol = _tolerance(row, rl)
        meas = None
        if row.measure is not None:
            try:
                meas = float(_MEASURE[row.measure](rl))
            except Exception as e:                              # noqa: BLE001
                meas = None
                row_err = f"{type(e).__name__}: {e}"
            else:
                row_err = None
        else:
            row_err = None
        unit = "deg" if row.rid in _DEG_ROWS else "mm"
        resid = (None if (meas is None or row.ref_mm is None or math.isnan(meas))
                 else meas - row.ref_mm)
        if row.rid in _INFORMATIONAL or row.ref_mm is None or resid is None:
            verdict = "모름" if row.ref_mm is None else "기록만"
            n_unknown += 1 if row.ref_mm is None else 0
            n_info += 1 if row.ref_mm is not None else 0
        else:
            verdict = "일치" if abs(resid) <= tol["U"] else "어긋남"
            n_pass += verdict == "일치"
            n_fail += verdict == "어긋남"
        d = dict(
            rid=row.rid, key=row.key, part=row.part, quantity=row.quantity,
            measure=row.measure, unit=unit,
            measured=None if meas is None else round(meas, 4),
            reference=row.ref_mm,
            residual=None if resid is None else round(resid, 4),
            residual_pct=(None if (resid is None or not row.ref_mm)
                          else round(100.0 * resid / abs(row.ref_mm), 4)),
            tolerance=tol, verdict=verdict,
            grade=row.grade, ref_class=row.ref_class, source=row.source,
            source_file=row.source_file, definition=row.definition,
            circularity=row.circularity, note=row.note, error=row_err,
        )
        if declared is not None and row.rid in declared and resid is not None:
            dec = float(declared[row.rid])
            #  회귀 판정 — «선언된 현 상태보다 나빠졌는가». 예산 규약은 저장소의 기존
            #  BOUNDARY_EDGE_BUDGET 표와 같은 뜻이다: «이만큼이 옳다»가 아니라 «지금 이만큼이다».
            d["declared_residual"] = round(dec, 4)
            d["regression_ok"] = bool(abs(resid) <= max(abs(dec) * 1.02, abs(dec) + tol["U"]))
        rows.append(d)
    return dict(key=key, n_rows=len(rows), n_match=n_pass, n_mismatch=n_fail,
                n_informational=n_info, n_unknown=n_unknown,
                truth_ok=bool(n_fail == 0),
                regression_ok=bool(all(r.get("regression_ok", True) for r in rows)),
                rows=rows)


def check_all(keys=None, meshes=None, declared: dict | None = None) -> dict:
    from drones import DRONES
    keys = list(keys or DRONES.keys())
    out = {}
    for k in keys:
        m = (meshes or {}).get(k)
        out[k] = check_key(k, mesh=m, declared=declared)
    return out


# --------------------------------------------------------------------------- #
#  ⑤ 가드 — 표 자체를 검사한다 (숫자가 아니라 **규칙**을 지키는지)
# --------------------------------------------------------------------------- #
def guard_m4t_gimbal(rows: list[DimRef] | None = None) -> dict:
    """⛔ M4T/M4E 규칙 — matrice4e 의 **짐벌/카메라 «치수»** 행이 공식 CAD 를 참값으로 쓰면 실패.
    (짐벌의 **위치** 행은 허용한다 — 크래들이 붙는 자리는 기체 쪽 형상이라 4T·4E 가 같다.)"""
    rows = REFS if rows is None else rows
    CAD = {"cad_m4t"}
    #  «치수» 로 보는 잣대들. 위치(centre)는 여기 없다.
    SIZE = {"gimbal_L", "gimbal_W", "gimbal_H"}
    bad = [r.rid for r in rows
           if r.key == "matrice4e" and r.part == "camera"
           and r.measure in SIZE and r.ref_class in CAD]
    return dict(name="M4T/M4E 짐벌 규칙", n_checked=sum(1 for r in rows if r.key == "matrice4e"),
                violations=bad, ok=not bad,
                rule="matrice4e 짐벌 «치수» 참값에 M4T 공식 CAD 를 쓰지 않는다(짐벌만 다른 기체다). 위치는 허용.")


def guard_tolerance_provenance(rows: list[DimRef] | None = None) -> dict:
    """허용오차에 **유도 문장이 없는 행**을 막는다 — 임의 숫자 금지 규약의 코드판."""
    rows = REFS if rows is None else rows
    bad = []
    for r in rows:
        if r.ref_class not in REF_CLASS:
            bad.append((r.rid, "모르는 ref_class"))
            continue
        if not (r.u_def_why or "").strip():
            bad.append((r.rid, "u_def 유도 문장 없음"))
        if r.ref_class == "photo" and r.ref_mm is not None and r.ref_band_pct is None:
            bad.append((r.rid, "사진 유래인데 밴드 선언 없음"))
        if not (r.definition or "").strip():
            bad.append((r.rid, "정의 문장 없음"))
    return dict(name="허용오차 유도 강제", n_checked=len(rows), violations=bad, ok=not bad,
                rule="모든 행은 (a) 아는 ref_class · (b) u_def 유도 문장 · (c) 정의 문장을 가져야 한다.")


def audit_reference_provenance(root: str | None = None,
                               rows: list[DimRef] | None = None) -> dict:
    """[A] 주장의 **근거 파일을 실제로 열어** 그 값이 나오는지 본다.
    못 열거나 값이 안 나오면 그 행의 등급은 신뢰할 수 없다(범주 지도 M15 의 요구)."""
    rows = REFS if rows is None else rows
    root = root or _ROOT
    res = []
    cache: dict[str, object] = {}
    for r in rows:
        sf = (r.source_file or "").split(" ::")[0].strip()
        if not sf:
            res.append(dict(rid=r.rid, source_file=None, exists=False, value_found=None,
                            status="출처 파일 미기재"))
            continue
        p = os.path.join(root, sf)
        ex = os.path.exists(p)
        want = (list(r.source_values) if r.source_values
                else ([] if r.ref_mm is None else [float(r.ref_mm)]))
        found = None
        if ex and want:
            if p.endswith(".json"):
                if p not in cache:
                    try:
                        cache[p] = json.load(open(p, encoding="utf-8"))
                    except Exception:                            # noqa: BLE001
                        cache[p] = None
                found = all(_json_contains_number(cache[p], float(v)) for v in want)
            else:
                if p not in cache:
                    try:
                        cache[p] = open(p, encoding="utf-8", errors="replace").read()
                    except Exception:                            # noqa: BLE001
                        cache[p] = ""
                found = all(_text_contains_number(cache[p], float(v)) for v in want)
        if r.ref_mm is None:
            status = "참값 없음 — 모름 칸"
        elif not ex:
            status = "파일 없음"
        elif found:
            status = "확인"
        else:
            status = "파일은 있으나 값 미발견"
        res.append(dict(rid=r.rid, grade=r.grade, source_file=sf, exists=bool(ex),
                        looked_for=want, value_found=found, status=status))
    n_ok = sum(1 for x in res if x["status"] == "확인")
    n_bad = sum(1 for x in res if x["status"] == "파일은 있으나 값 미발견")
    return dict(name="근거 파일 대조", n_rows=len(res), n_confirmed=n_ok,
                n_missing_file=sum(1 for x in res if x["status"] == "파일 없음"),
                n_value_not_found=n_bad,
                n_no_reference=sum(1 for x in res if x["status"] == "참값 없음 — 모름 칸"),
                rows=res,
                ok=bool(all(x["exists"] for x in res) and n_bad == 0),
                rule="모든 행의 source_file 은 저장소에 실재해야 하고, [A]/[B] 행의 참값은 그 파일 "
                     "안에서 다시 찾을 수 있어야 한다. 못 찾으면 인증서에 «미확인» 으로 남는다.")


def _json_contains_number(obj, val: float, rtol=2e-4) -> bool:
    """JSON 어딘가에 그 수가 (반올림 표기 포함) 들어 있는가."""
    if obj is None:
        return False
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            stack.extend(o.values())
        elif isinstance(o, (list, tuple)):
            stack.extend(o)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            if abs(float(o) - val) <= max(abs(val) * rtol, 5e-3):
                return True
        elif isinstance(o, str):
            if _text_contains_number(o, val):
                return True
    return False


def _text_contains_number(txt: str, val: float, rtol=2e-4) -> bool:
    import re
    for m in re.finditer(r"-?\d+(?:\.\d+)?", txt):
        try:
            x = float(m.group())
        except ValueError:
            continue
        if abs(x - val) <= max(abs(val) * rtol, 5e-3):
            return True
    return False


# --------------------------------------------------------------------------- #
#  ⑥ 근거 등급 행렬 (기체 × 부품)
# --------------------------------------------------------------------------- #
#  ⚠ 이 표는 «치수 참값의 등급» 이다 — 재질·전기물성의 등급이 아니다.
#    빈칸(«모름»)을 채우지 않는 것이 이 표의 규율이다.
PARTS = ("airframe", "body", "canopy", "arm", "motor", "prop",
         "camera", "gear", "battery", "pcb", "deck", "accent")

GRADE_DEFS = {
    "A": "그 기체의 공식 CAD/공표 제원을 직접 읽었다",
    "A-": "공식에 준하는 1차 자산이나 한 단계 약하다(제품 뷰어용 자산 등)",
    "B": "그 기체의 제품 사진을 계측했다",
    "B-": "사진이지만 자세·축척 근거가 약하다 / 제조사 아닌 시뮬레이터 자산",
    "C": "같은 계열의 다른 기체에서 유추했다",
    "D": "다른 물건을 대리로 빌려 썼다",
    "모름": "외부 참값이 저장소에 없다 — 빈칸으로 남긴다",
}


def grade_matrix(rows: list[DimRef] | None = None) -> dict:
    """기체 × 부품 등급 행렬. 행이 있는 칸만 등급이 붙고, 나머지는 «모름» 이다."""
    from drones import DRONES
    rows = REFS if rows is None else rows
    order = {"A": 0, "A-": 1, "B": 2, "B-": 3, "C": 4, "D": 5}
    out = {}
    for k in DRONES:
        cell = {}
        for p in PARTS:
            rs = [r for r in rows if r.key == k and r.part == p and r.ref_mm is not None]
            if not rs:
                miss = [r for r in rows if r.key == k and r.part == p]
                cell[p] = dict(grade="모름", n_rows=0,
                               why=(miss[0].source if miss else "이 칸을 보는 외부 참값 행이 없다"))
                continue
            best = min(rs, key=lambda r: order.get(r.grade, 9))
            cell[p] = dict(grade=best.grade, n_rows=len(rs),
                           source=best.source_file, rids=[r.rid for r in rs],
                           independent=sum(1 for r in rs if r.circularity == "independent"))
        out[k] = cell
    return out


# --------------------------------------------------------------------------- #
#  ⑦ 화면 출력
# --------------------------------------------------------------------------- #
def report(res: dict) -> str:
    L = [f"  {'행':8s} {'부품':9s} {'무엇':26s} {'메쉬':>10s} {'참값':>10s} "
         f"{'잔차':>9s} {'허용U':>8s} {'등급':4s} 판정"]
    for r in res["rows"]:
        mv = "—" if r["measured"] is None else f"{r['measured']:10.3f}"
        rv = "—" if r["reference"] is None else f"{r['reference']:10.3f}"
        dv = "—" if r["residual"] is None else f"{r['residual']:+9.3f}"
        uv = f"{r['tolerance']['U']:8.3f}" if r["reference"] is not None else "       —"
        mark = {"일치": "✅", "어긋남": "❌", "기록만": "📝", "모름": "⬜"}[r["verdict"]]
        L.append(f"  {r['rid']:8s} {r['part']:9s} {r['quantity'][:26]:26s} {mv} {rv} {dv} {uv} "
                 f"{r['grade']:4s} {mark}{r['verdict']}")
    L.append(f"  → 일치 {res['n_match']} · 어긋남 {res['n_mismatch']} · "
             f"기록만 {res['n_informational']} · 모름 {res['n_unknown']}")
    return "\n".join(L)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    keys = None
    if "--key" in argv:
        keys = [argv[argv.index("--key") + 1]]
    print("=" * 112)
    print("치수·외부 기준 대조 — 메쉬 ↔ 공식 CAD·공표 제원·사진 (mesh_dimref)")
    print(f"허용오차 U = k·√(u_ref²+u_def²+u_disc²), k = {K_COVERAGE}  ⇒ 임의 숫자 없음")
    print("=" * 112)
    g1, g2 = guard_m4t_gimbal(), guard_tolerance_provenance()
    print(f"[가드] {g1['name']}: {'✅' if g1['ok'] else '❌ ' + str(g1['violations'])}")
    print(f"[가드] {g2['name']}: {'✅' if g2['ok'] else '❌ ' + str(g2['violations'])}")
    res = check_all(keys)
    n_bad = 0
    for k, r in res.items():
        if not r["n_rows"]:
            continue
        print(f"\n[{k}]")
        print(report(r))
        n_bad += r["n_mismatch"]
    print(f"\n{'='*112}\n어긋난 행 합계 {n_bad}  "
          f"(⚠ «어긋남» 은 결함 신고이지 실패가 아니다 — 인증서가 칸마다 선언을 붙인다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
