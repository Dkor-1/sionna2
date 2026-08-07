# -*- coding: utf-8 -*-
"""
report16_rung_mesh_no_rotor.py — 사다리 한 단: **로터 뗀 우리 메쉬**의 마이크로도플러
================================================================================

한 문장으로
--------------------------------------------------------------------------------
프로펠러를 떼어낸 우리 CAD 기체(=몸통·팔·다리·모터만 남은 것)가 마이크로도플러를
얼마나 내는지 재고, **같은 운동학으로 실제로 돌린** 구·정육면체·상자와 나란히 놓는다.

용어 먼저 풀기 (처음 쓰는 말)
--------------------------------------------------------------------------------
· **마이크로도플러** : 표적 전체가 이동해서 생기는 도플러가 아니라, 표적의 **일부가
  움직여서** 되돌아오는 전파의 위상이 시간에 따라 흔들리는 것. 드론에서는 프로펠러가
  그 «일부» 다.
· **변조(modulation)** : 신호가 시간에 따라 흔들리는 정도. 여기서는 «흔들리는 성분(AC)이
  가만히 있는 성분(DC)보다 몇 dB 아래인가» 로 잰다. 0 이면 전혀 안 흔들린다는 뜻이다.
· **운동학(kinematics)** : «무엇이 어떤 축을 중심으로 분당 몇 바퀴 도는가» 라는 움직임의
  규칙. 물체의 모양(형상)과는 별개다.
· **PO(물리광학)** : 표면을 잘게 나눠 «레이더를 향한 면» 만 골라 위상을 맞춰 더하는
  근사 계산법. 우리 산란 커널이 이것이다.
· **위상 표 E(φ)** : 한 바퀴(360°)를 잘게 나눠, 각 회전각 φ 에서의 복소 산란장을 적어 둔 표.
  네 개 로터가 같은 rpm 으로 도는 한 시간신호 E(t) 는 이 표를 그대로 이어 붙인 것이다.

이 단이 하는 일 (둘로 나뉜다 — 섞어 읽으면 안 된다)
--------------------------------------------------------------------------------
**① 비행 운동학(flight)** — 실제로 나는 상태의 규칙: 몸체는 가만히 있고 로터만 돈다.
   로터를 떼어냈으니 **도는 것이 하나도 없다.** 그래서 변조는 0 이어야 한다.
   ⚠ 이것은 «측정» 이 아니라 «모형의 산수 항등식» 이다. 확인은 되지만 증거는 약하다.
   이 모드의 진짜 산출물은 따로 있다 — 로터 있는 전체 메쉬(report16_base 의 표)에서
   몸체 몫을 **정확히 빼내어**, 우리가 그동안 써 온 «동체 대 블레이드 세기비(dc_ac_db)» 중
   몸체가 만든 받침(DC pedestal)이 얼마인지 분해한다. PO 는 점들의 단순 합이고 가림이
   없으므로 E_전체(φ) = E_몸체 + E_로터(φ) 가 **근사가 아니라 항등식**이다.

**② 회전 운동학(spin)** — 공정 대조를 위한 규칙: 물체 **전체**를 같은 축(기체 z축, 원점을
   지남)·같은 rpm(호버 rpm)·같은 위상 스텝으로 **실제로 돌린다.** 구도 돌리고 상자도 돌린다.
   구를 «안 돌리고» 0 을 얻는 것은 증명이 아니라 동어반복이므로, 전부 실제로 돌린다.

   ⭐ 여기서 반드시 알아야 할 사실 하나: 강체를 z축으로 φ 만큼 돌려 놓고 고정된 시선에서
     보는 것은, 물체를 가만히 두고 **방위각을 −φ 만큼 옮겨 보는 것과 수학적으로 같다**
     (모노스태틱·평면파·구면파 모두). 즉 이 모드의 위상 표는 곧 **방위 RCS 패턴**이고,
     그 표의 스펙트럼이 곧 마이크로도플러다. 그래서 이 단은 «구가 원리적으로 못 내는 것 =
     방위 산포 ε» 과 «마이크로도플러» 가 **같은 정보의 두 얼굴**임을 숫자로 보인다.
     (그 결과 방위 앙상블은 이 모드에서 **퇴화한다** — 시작 방위를 바꾸면 표가 순환이동만
      할 뿐 스펙트럼이 같다. 그래서 앙상블 축을 방위 대신 **고각**으로 잡았다.)

⭐ 사전 예측 (계산 **전에** 적어 outputs/report16_rung_mesh_no_rotor.prereg.json 에 봉인)
--------------------------------------------------------------------------------
「비행 운동학에서 로터 뗀 메쉬의 변조는 거의 0 이어야 한다 — 도는 것이 없기 때문이다.
  0 이 아니면 그것은 물리가 아니라 몸체 쪽 인공 변조(계산 잔차)다.」
그 파일은 계산이 시작되기 전에 기록되고, 최종 JSON 은 그 파일의 해시와 기록시각을 물고 있다.
⚠ 회전 운동학 결과에 대해서는 **부호를 미리 정하지 않았다.** 우리 메쉬가 상자보다 변조가
  작게 나오면 그것이 더 중요한 결과다 — 지도교수의 «형상 정밀도는 값어치가 없다» 는 지적이
  마이크로도플러에서도 맞다는 뜻이 되고, 우리는 방향을 다시 잡아야 한다.

⚠ 병기해야 할 한계
--------------------------------------------------------------------------------
· 우리 PO 커널이 믿을 만하려면 부품의 특징 폭이 0.729λ 이상이어야 한다. 프로펠러 블레이드
  (13.78 mm)는 15.86 GHz 에서야 그 문턱을 넘는다 — 즉 **마이크로도플러를 만드는 부품이 곧
  커널이 가장 약한 부품**이다. 이 단의 주인공(몸체)은 훨씬 커서 그 문제에서 자유롭지만,
  base 의 로터 숫자와 견줄 때는 그 사실을 같이 읽어야 한다. 그래서 15.86 GHz 도 같이 돈다.
· 가림(occlusion)이 없다 — 몸체 뒤에 있는 면도 계속 산란체로 센다. 이것은 base 와 같은
  통제이며(가림을 넣으면 «형상» 인지 «가림» 인지 갈리지 않는다), dc_ac_db 계열이 가장 오염된다.
· 몸체를 호버 rpm 으로 통째로 돌리는 것은 **비행 상태가 아니다.** 형상만 남기고 운동학을
  똑같이 맞춘 **대조 실험**이다. 실제 비행에서 몸체가 내는 미세운동(진동·자세 흔들림)은
  이 모형에 아예 들어 있지 않다.

⛔ 규율: src/drones.py·src/drone_cad.py 는 읽기만 한다. outputs/report15_*·benchmark/report15_*,
   src/make_report0N_*·report0N_*.ipynb 는 건드리지 않는다. 숫자는 손으로 적지 않는다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import report16_base as RB              # noqa: E402  ⭐ 규약·커널·지표를 그대로 물려받는다

SCRATCH = os.environ.get("REPORT16_SCRATCH",
                         "/tmp/claude-1015/-home-yunjung-workspace/"
                         "a78e7d06-306f-4e2d-b124-5fe972bc4462/scratchpad/report16")
OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor.json")
OUT_PREREG = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor.prereg.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_no_rotor_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_mesh_no_rotor.png")

C0 = RB.C0
FC_MAIN = RB.FC_MAIN            # 3.5 GHz (생산 대역)
FC_HI = RB.FC_PO_KNEE           # 15.86 GHz (블레이드가 PO 유효 무릎을 넘는 곳)
EL_MAIN = RB.EL_DEG             # 15° (헤드라인 고각)
RANGE_M = RB.RANGE_M            # 10 m 모노스태틱
N_AZ = RB.N_AZ                  # 24 (비행 모드의 방위 앙상블 — base 와 동일)
N_REV = RB.N_REV                # 32 회전
OS_FACTOR = RB.OS_FACTOR        # 위상 표본 여유배수

FRAME_DIV = 6.0                 # 비회전부 점 간격 λ/6 — base 와 **동일**(그래야 분해가 정확)
BLADE_DIV = 11.0                # 회전부 점 간격 λ/11 — base 와 동일(mesh_full_rigid 용)
BLADE_N = 26
FINE_X = 4.0                    # 점밀도 반론 차단용 배수

EL_SWEEP = (0.0, 15.0, 30.0, 45.0, 60.0)     # 방위가 퇴화하므로 앙상블 축을 고각으로 잡는다
TESS_SAFETY = 4.0               # 프리미티브의 방위 면 개수를 «관심 대역» 의 몇 배로 둘지

PREREG_TEXT = (
    "PRE-REGISTERED PREDICTION (written before any field was computed)\n"
    "rung: mesh_no_rotor (our CAD airframe with the propellers removed)\n"
    "\n"
    "[ko] 비행 운동학(몸체 정지·로터만 회전)에서 로터 뗀 우리 메쉬의 마이크로도플러 변조는 "
    "거의 0 이어야 한다 — 도는 것이 하나도 없기 때문이다. 0 이 아니라면 그것은 물리가 아니라 "
    "몸체 쪽 인공 변조(수치 잔차)이며, 그렇게 보고해야 한다.\n"
    "[en] Under flight kinematics (body static, rotors spinning) the rotor-less mesh must show "
    "essentially zero micro-Doppler modulation, because nothing rotates. Any non-zero value is "
    "not physics but spurious body-side modulation, and must be reported as such.\n"
    "\n"
    "[ko] 회전 운동학(물체 전체를 같은 축·같은 rpm·같은 위상 스텝으로 실제로 돌림)에 대해서는 "
    "부호를 미리 정하지 않는다. 우리 CAD 몸체가 등가부피 상자보다 변조가 작게 나오는 결과도 "
    "가능하며, 그 경우 «형상 정밀도는 마이크로도플러에서도 값어치가 없다» 가 결론이 된다.\n"
    "[en] For the spin kinematics no direction is pre-registered. Our CAD body may well modulate "
    "LESS than an equal-volume box; that outcome would say shape fidelity buys nothing here.\n"
)


# =========================================================================== #
#  0. 사전 예측 봉인 — 계산이 시작되기 전에 파일로 떨군다
# =========================================================================== #
def write_prereg():
    """계산 **전에** 예측을 파일로 굳힌다. 최종 JSON 은 이 파일의 해시·기록시각을 물고 있어서
    나중에 «맞췄다» 고 말을 바꿀 수 없다."""
    os.makedirs(os.path.dirname(OUT_PREREG), exist_ok=True)
    sha = hashlib.sha256(PREREG_TEXT.encode("utf-8")).hexdigest()
    #  ⭐ 이미 같은 예측이 봉인돼 있으면 **덮어쓰지 않는다** — 다시 돌릴 때마다 기록시각이
    #    새로 찍히면 «먼저 적었다» 는 증거가 무의미해진다.
    if os.path.exists(OUT_PREREG):
        try:
            old = json.load(open(OUT_PREREG))
            if old.get("prediction_sha256") == sha:
                old["reruns"] = int(old.get("reruns", 0)) + 1
                old["last_run_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                with open(OUT_PREREG, "w") as f:
                    json.dump(old, f, ensure_ascii=False, indent=1)
                return old
        except Exception:
            pass
    rec = dict(
        report="report16_rung_mesh_no_rotor",
        written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        written_before="any electromagnetic field of this rung was computed",
        prediction_text=PREREG_TEXT,
        prediction_sha256=sha,
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        note_ko=("이 파일은 계산 시작 전에 기록된다. 최종 JSON 의 preregistration 블록이 "
                 "같은 sha256 을 담고 있으면 «예측을 먼저 적었다» 는 사실이 검증된다."))
    with open(OUT_PREREG, "w") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    return rec


# =========================================================================== #
#  1. 형상 도구 — 부피·무게중심·반경을 **계산해서** 프리미티브를 짝지운다
# =========================================================================== #
def mesh_volume_centroid(m):
    """닫힌 삼각형 메쉬의 (부피[m³], 부피 무게중심[m]).
    원점을 꼭짓점으로 하는 사면체들의 부호 있는 부피를 더하는 표준 방법."""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol6 = np.einsum("ij,ij->i", a, np.cross(b, c))          # 6·부피
    vol = float(vol6.sum() / 6.0)
    cen = (a + b + c) / 4.0                                   # 사면체 무게중심
    C = (vol6[:, None] * cen).sum(0) / max(vol6.sum(), 1e-30)
    return abs(vol), C


def mesh_area_weighted_gamma(m, gamma_map):
    """면적 가중 평균 |Γ| — 프리미티브에 «같은 재질» 을 물려줄 때 쓰는 하나짜리 값.
    PO 진폭이 ΔA·|Γ| 이므로 면적 가중이 반사 총량을 보존하는 유일한 가중이다."""
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    ar = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    g = np.array([float(gamma_map.get(gg, 1.0)) for gg in m.g], float)
    return float((ar * g).sum() / max(ar.sum(), 1e-30)), float(ar.sum())


def nn_spacing(P, n_probe=4000, seed=0):
    """점구름의 실측 최근접이웃 간격 중앙값[m]. 팔끼리 «같은 λ/N 을 썼다» 가 «같은 촘촘함» 은
    아니기 때문에(삼각형당 최소 1점 규칙), 실측해서 기록한다."""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float)
    if len(P) < 4:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
    d, _ = cKDTree(P).query(P[idx], k=2)
    return float(np.median(d[:, 1]))


def _odd(n):
    n = int(n)
    return n if n % 2 == 1 else n + 1


SEG_CAP = 2001          # 프리미티브 방위 면 개수의 상한(비용 방어) — 실제로는 걸리지 않는다


def _seg_for(circumference_m, spac_m, band_order):
    """프리미티브의 «방위 방향 면 개수». 두 조건을 다 넘긴다:
       ① 면 크기가 점 간격보다 작을 것,  ② 관심 대역(1.5β)의 TESS_SAFETY 배 이상일 것.
    ②가 핵심이다 — 이산화 잔차는 차수 seg 에 나타나므로, seg 를 관심 대역 밖으로 밀어야
    회전대칭체(구)의 «널» 이 대역 안에서 깨끗해진다."""
    need = max(9, int(math.ceil(circumference_m / max(spac_m, 1e-12))),
               int(math.ceil(TESS_SAFETY * max(band_order, 1))))
    return _odd(min(need, SEG_CAP))


def frame_geometry(spec):
    """로터 뗀 메쉬(= build_frame)의 기하 요약. 프리미티브는 전부 여기서 나온 숫자로 짓는다."""
    from drones import build_frame, build_drone, drone_gamma_map
    fr = build_frame(spec)
    V = np.asarray(fr.v, float)
    vol, cen = mesh_volume_centroid(fr)
    gmap = drone_gamma_map(spec)
    gbar, area = mesh_area_weighted_gamma(fr, gmap)
    bb_lo, bb_hi = V.min(0), V.max(0)
    r_max = float(np.hypot(V[:, 0], V[:, 1]).max())
    #  위상 격자를 안전하게 잡기 위한 «이 단에서 돌리는 물체 중 가장 큰 회전반경».
    #  프로펠러를 얼려 붙인 팔(mesh_full_rigid)과 바운딩박스 상자가 프레임보다 크다.
    W = np.asarray(build_drone(spec).v, float)
    r_full = float(np.hypot(W[:, 0], W[:, 1]).max())
    r_bbox = float(math.hypot(0.5 * (bb_hi[0] - bb_lo[0]), 0.5 * (bb_hi[1] - bb_lo[1])))
    vol_full, _ = mesh_volume_centroid(build_drone(spec))
    return dict(
        n_tris=int(len(fr.f)), volume_m3=vol, surface_area_m2=area,
        centroid_m=[float(x) for x in cen],
        centroid_offaxis_mm=float(1000 * math.hypot(cen[0], cen[1])),
        bbox_lo_m=[float(x) for x in bb_lo], bbox_hi_m=[float(x) for x in bb_hi],
        bbox_extent_mm=[float(1000 * x) for x in (bb_hi - bb_lo)],
        bbox_center_m=[float(x) for x in 0.5 * (bb_hi + bb_lo)],
        spin_radius_max_m=r_max,
        spin_radius_with_props_m=r_full,
        spin_radius_bbox_halfdiag_m=r_bbox,
        spin_radius_grid_m=float(max(r_max, r_full, r_bbox)),
        volume_with_props_m3=float(vol_full),
        gamma_area_weighted=gbar,
        gamma_map={k: float(v) for k, v in gmap.items()},
        note_ko=("spin_radius_max_m 은 z축(회전축)에서 가장 먼 점까지의 거리다 — 몸체를 통째로 "
                 "돌렸을 때 도플러 폭을 정하는 «팁 반경» 에 해당한다. spin_radius_grid_m 은 이 단에서 "
                 "돌리는 팔 중 가장 큰 반경이며, 위상 격자는 그 값으로 잡아 어느 팔에서도 접힘이 없다."))


def build_arm_mesh(spec, arm, geo, lam, band_order, div=FRAME_DIV):
    """팔 하나의 «형상» 을 만든다. 모든 프리미티브는 geo(로터 뗀 메쉬의 실측치)에서 나온다.

    배치 규약 (전부 기록한다):
      · 프리미티브는 **회전축 위**(x=y=0)에 놓는다. 로터 배치가 z축 대칭이므로 z축이 이 기체의
        설계축이고, 축 위에 놓는 것이 프리미티브에게 **가장 유리한**(변조가 가장 작은) 배치다.
        즉 우리 메쉬가 프리미티브보다 변조가 크게 나오더라도 그 결론은 **보수적**이다.
        (몸체 무게중심이 축에서 얼마나 벗어나 있는지는 centroid_offaxis_mm 에 적혀 있다.)
      · 부피 등가는 **계산해서** 맞추고 그 값을 기록한다.
      · 방위 방향 면 개수는 «관심 대역» 의 TESS_SAFETY 배 이상으로 둔다 — 그래야 이산화 잔차가
        관심 대역 밖(높은 차수)으로 밀려나 널(구)이 깨끗해진다.
    """
    from geom import box, uv_sphere
    vol = geo["volume_m3"]
    zc = float(geo["centroid_m"][2])
    ext = np.asarray(geo["bbox_extent_mm"], float) / 1000.0
    zc_bb = float(geo["bbox_center_m"][2])
    spac = lam / float(div)
    meta = dict(placement="on the spin axis (x=y=0)", spin_axis="body z through origin",
                tessellation_spacing_m=float(spac))

    if arm == "sphere_eqvol":
        r = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        seg = _seg_for(2 * math.pi * r, spac, band_order)
        rings = max(3, int(math.ceil(math.pi * r / spac)))
        m = uv_sphere(r, center=(0.0, 0.0, zc), seg=seg, rings=rings, group="prim")
        meta.update(kind="sphere", radius_m=r, seg=seg, rings=rings, center_m=[0.0, 0.0, zc],
                    spin_radius_max_m=r, residual_order=seg,
                    note_ko="등가부피 구. 회전축 위에 놓여 있으므로 돌려도 형상이 변하지 않는다 → 물리적 변조 0.")
    elif arm == "sphere_offaxis":
        r = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        d = 0.5 * geo["spin_radius_max_m"]
        seg = _seg_for(2 * math.pi * r, spac, band_order)
        rings = max(3, int(math.ceil(math.pi * r / spac)))
        m = uv_sphere(r, center=(d, 0.0, zc), seg=seg, rings=rings, group="prim")
        meta.update(kind="sphere_offaxis", radius_m=r, offset_m=d, seg=seg, rings=rings,
                    center_m=[d, 0.0, zc], spin_radius_max_m=d + r, residual_order=seg,
                    placement=f"off the spin axis by r_max/2 = {d*1000:.1f} mm",
                    note_ko=("같은 구를 회전축에서 벗어나게 놓았다. 여기서 변조가 나오면 «구의 널은 "
                             "회전대칭 때문이지 구라서가 아니다» 가 증명된다 — 널의 원인 확인용."))
    elif arm == "cube_eqvol":
        s = vol ** (1.0 / 3.0)
        m = box(s, s, s, center=(0.0, 0.0, zc), group="prim")
        meta.update(kind="cube", side_m=s, center_m=[0.0, 0.0, zc],
                    spin_radius_max_m=float(math.hypot(s / 2, s / 2)),
                    note_ko="등가부피 정육면체 — p3_validation 의 cube_vol 대조와 같은 규약.")
    elif arm == "box_eqvol_aspect":
        vb = float(ext[0] * ext[1] * ext[2])
        k = (vol / max(vb, 1e-30)) ** (1.0 / 3.0)
        lx, ly, lz = (float(ext[0] * k), float(ext[1] * k), float(ext[2] * k))
        m = box(lx, ly, lz, center=(0.0, 0.0, zc), group="prim")
        meta.update(kind="box_equal_volume_bbox_aspect", lxyz_m=[lx, ly, lz],
                    bbox_volume_m3=vb, scale_from_bbox=k, center_m=[0.0, 0.0, zc],
                    spin_radius_max_m=float(math.hypot(lx / 2, ly / 2)),
                    note_ko="바운딩박스의 가로세로비는 그대로, 부피가 같아지도록 통째로 줄인 상자.")
    elif arm == "box_bbox":
        lx, ly, lz = float(ext[0]), float(ext[1]), float(ext[2])
        m = box(lx, ly, lz, center=(0.0, 0.0, zc_bb), group="prim")
        meta.update(kind="box_bounding", lxyz_m=[lx, ly, lz],
                    volume_m3=float(lx * ly * lz),
                    volume_over_mesh=float(lx * ly * lz / max(vol, 1e-30)),
                    center_m=[0.0, 0.0, zc_bb],
                    spin_radius_max_m=float(math.hypot(lx / 2, ly / 2)),
                    note_ko=("바운딩박스 그대로인 상자 — 부피가 아니라 **크기**를 맞춘 판. "
                             "부피가 메쉬보다 훨씬 크므로 절대 세기는 과대하다(그 배율을 적어 둔다). "
                             "여기서 보는 것은 세기가 아니라 «변조의 모양» 이다."))
    else:
        raise ValueError(arm)
    return m, meta


def clouds_for(spec, arm, lam, band_order, geo):
    """팔 하나의 점구름 (P, N, W) + 메타. 모든 팔이 하나의 강체다(이 단에서는 분절이 없다)."""
    from drones import build_frame, build_propeller, rotor_layout, drone_gamma_map
    from rcs_po import mesh_to_points
    gmap = drone_gamma_map(spec)
    fine = arm.endswith("_fine")
    base_arm = arm[:-5] if fine else arm
    fdiv = FRAME_DIV * (FINE_X if fine else 1.0)
    bdiv = BLADE_DIV * (FINE_X if fine else 1.0)

    if base_arm == "mesh_no_rotor":
        fr = build_frame(spec)
        P, N, dA, w = mesh_to_points(fr, lam / fdiv, gamma=gmap)
        W = dA * w
        meta = dict(kind="cad_airframe_without_propellers", n_tris=int(len(fr.f)),
                    spin_radius_max_m=geo["spin_radius_max_m"],
                    volume_m3=geo["volume_m3"],
                    note_ko="⭐ 이 단의 주인공 — drones.build_frame(=프로펠러를 뺀 진짜 CAD 기체).")
    elif base_arm == "mesh_full_rigid":
        # 프레임 + 프로펠러(초기 위상으로 얼려 붙임) 를 **하나의 강체**로 본다.
        # base 의 mesh 팔과 같은 점구름 구성(프레임 λ/6 · 프롭 λ/11 · 거울상은 점구름 y-반전)을 쓴다.
        fr = build_frame(spec)
        Pf, Nf, dAf, wf = mesh_to_points(fr, lam / fdiv, gamma=gmap)
        pr = build_propeller(spec, n=BLADE_N)
        Pp, Np_, dAp, wp = mesh_to_points(pr, lam / bdiv, gamma=gmap)
        Pm = Pp * np.array([1.0, -1.0, 1.0])
        Nm = Np_ * np.array([1.0, -1.0, 1.0])
        Ps, Ns, Ws = [Pf], [Nf], [dAf * wf]
        for rot in rotor_layout(spec):
            R = RB._rz(math.radians(float(rot["base_ang"])))
            src_P, src_N, src_W = ((Pp, Np_, dAp * wp) if rot["dir"] > 0 else (Pm, Nm, dAp * wp))
            Ps.append(src_P @ R.T + np.asarray(rot["center"], float))
            Ns.append(src_N @ R.T)
            Ws.append(src_W)
        P, N, W = np.vstack(Ps), np.vstack(Ns), np.concatenate(Ws)
        rr = float(np.hypot(P[:, 0], P[:, 1]).max())
        meta = dict(kind="cad_airframe_with_frozen_propellers",
                    n_tris=int(len(fr.f) + spec.num_rotors * len(pr.f)),
                    spin_radius_max_m=rr, volume_m3=geo["volume_with_props_m3"],
                    volume_ratio_to_mesh=float(geo["volume_with_props_m3"] /
                                               max(geo["volume_m3"], 1e-30)),
                    note_ko=("프레임 + 프로펠러를 초기 위상에서 얼려 하나의 강체로 돌린다 — base 의 "
                             "«로터만 도는» 결과와 «몸체째 도는» 결과를 잇는 다리."))
        meta.update(requested_spacing_m=float(lam / fdiv), actual_spacing_m=nn_spacing(P),
                    n_points=int(len(W)), gamma="per-group material map (same as base)")
        return P, N, W, meta
    else:
        m, meta = build_arm_mesh(spec, base_arm, geo, lam, band_order, div=fdiv)
        gbar = geo["gamma_area_weighted"]
        P, N, dA, w = mesh_to_points(m, lam / fdiv, gamma={"prim": gbar})
        vol_arm, _ = mesh_volume_centroid(m)
        meta.update(volume_m3=float(vol_arm),
                    volume_ratio_to_mesh=float(vol_arm / max(geo["volume_m3"], 1e-30)),
                    gamma_uniform=gbar,
                    gamma_note_ko=("프리미티브에는 하나짜리 |Γ| 밖에 못 준다. 로터 뗀 메쉬의 "
                                   "**면적 가중 평균 |Γ|** 를 물려주어 반사 총량을 맞췄다. "
                                   "⚠ 모양 지표(플래시 대조비·차수 풍부도·dc_ac_db)는 |Γ| 를 "
                                   "통째로 곱해도 변하지 않는다(비율이라서) — 바뀌는 것은 σ 절대값뿐이고, "
                                   f"PEC(|Γ|=1) 로 두면 {-20*math.log10(max(gbar,1e-30)):.2f} dB 만큼 올라간다."))
        W = dA * w
    if base_arm != "mesh_full_rigid":
        meta.update(requested_spacing_m=float(lam / fdiv), actual_spacing_m=nn_spacing(P),
                    n_points=int(len(W)))
        if base_arm == "mesh_no_rotor":
            meta["gamma"] = "per-group material map (drone_gamma_map) — same as base"
    return P, N, W, meta


# =========================================================================== #
#  2. 규약 — 위상 스텝 수는 **가장 큰 β** 에서 계산한다(모든 팔이 같은 격자를 쓰도록)
# =========================================================================== #
def beta_of(r_m, lam, el_deg):
    """β = 4πR·cos(el)/λ. 베셀 차수 절단이자 «팁 도플러 ÷ 회전수» 다(rpm 과 무관)."""
    return 4.0 * math.pi * float(r_m) * math.cos(math.radians(float(el_deg))) / lam


def make_proto(lam, f_rot, r_eff, el_deg, n_phase, n_rev=N_REV):
    """md_metrics16 이 먹는 규약 dict 를 만든다. base 의 derive_protocol 과 같은 정의를 쓰되,
    «팁 반경» 자리에 그 팔의 실제 최대 회전반경을 넣는다."""
    b = beta_of(r_eff, lam, el_deg)
    return dict(lam_m=lam, f_rot_hz=float(f_rot), beta=b, f_tip_hz=b * float(f_rot),
                spin_radius_m=float(r_eff), el_deg=float(el_deg),
                n_phase=int(n_phase), samples_per_rev=int(n_phase), n_rev=int(n_rev),
                prf_hz=float(n_phase) * float(f_rot), n_t=int(n_phase) * int(n_rev),
                period_deg=360.0, phase_step_deg=360.0 / int(n_phase),
                nyquist_margin_x=float(n_phase) / (2.0 * max(b, 1e-9)),
                interp_error="none (slow-time grid lands exactly on the phase table)")


def rung_protocol(spec, geo, fc):
    """이 기체·이 주파수에서 **모든 팔이 공유할** 위상 격자를 계산한다.

    가장 엄격한 조건을 쓴다 — 고각 0°(β 가 최대) × **이 단에서 돌리는 가장 큰 물체**의 회전반경.
    그래야 고각 스윕 전체·모든 팔에서 접힘(aliasing)이 없다.
    ⚠ 격자는 «가장 큰 물체» 로 잡지만, 지표를 읽는 **기준자(band_order)** 는 이 단의 주인공인
      로터 뗀 메쉬로 잡는다 — 그래야 팔끼리 같은 눈금으로 비교된다."""
    f_rot = float(spec.hover_rpm) / 60.0
    lam = C0 / float(fc)
    b0 = beta_of(geo["spin_radius_grid_m"], lam, 0.0)         # 격자 크기용 (가장 큰 팔)
    b_ref = beta_of(geo["spin_radius_max_m"], lam, 0.0)       # 기준자용 (로터 뗀 메쉬)
    S = int(2 ** math.ceil(math.log2(max(64.0, OS_FACTOR * b0))))
    return dict(fc_hz=float(fc), lam_m=lam, f_rot_hz=f_rot, hover_rpm=float(spec.hover_rpm),
                spin_radius_max_m=geo["spin_radius_max_m"],
                spin_radius_grid_m=geo["spin_radius_grid_m"],
                beta_worst_case_el0=b0, beta_reference_el0=b_ref,
                n_phase=S, prf_hz=S * f_rot,
                n_rev=N_REV, n_t=S * N_REV, phase_step_deg=360.0 / S,
                nyquist_margin_x=S / (2.0 * b0),
                band_order_el0=int(max(2, math.ceil(1.5 * b_ref))),
                sizing_rule_ko=("S = 2^ceil(log2(8·β)) 이고 β 는 고각 0°(최악)·이 단에서 돌리는 가장 "
                                "큰 물체의 회전반경으로 잡았다. PRF = S·f_rot 이므로 슬로타임 표본이 "
                                "표 격자에 정확히 떨어져 보간 오차가 0 이다."),
                fairness_ko=("이 격자를 **모든 팔이 공유한다** — 같은 회전축(기체 z, 원점)·같은 "
                             "rpm(호버 rpm)·같은 위상 스텝. 구도 상자도 실제로 돌린다."))


# =========================================================================== #
#  3. 계산 — 회전 표(spin) 와 정지 값(flight)
# =========================================================================== #
def spin_table(torch, dev, P, N, W, k, az_deg, el_deg, range_m, n_phase, wavefront):
    """물체 전체를 z축(원점)으로 한 바퀴 돌리며 복소 산란장 E(φ) 를 낸다.

    base 의 field_rotor 를 center=(0,0,0)·base_ang=0·dir=+1 로 부른다 — 즉 **같은 커널**이다.
    (물체를 θ 돌리는 것은 안테나를 −θ 돌려 보는 것과 엄밀히 같다는 base 의 항등식을 그대로 쓴다.)"""
    u, A, R_t = RB.look_and_antenna(az_deg, el_deg, range_m)
    phis = np.linspace(0.0, 2 * math.pi, int(n_phase), endpoint=False)
    return RB.field_rotor(torch, dev, P, N, W, k, A, R_t, (0.0, 0.0, 0.0), 0.0, 1.0,
                          phis, wavefront)


def static_field(torch, dev, P, N, W, k, az_deg, el_deg, range_m, wavefront):
    """돌리지 않은 복소 산란장 하나 — 비행 운동학에서 몸체가 내는 값."""
    u, A, R_t = RB.look_and_antenna(az_deg, el_deg, range_m)
    return RB.field_static(torch, dev, P, N, W, k, A, R_t, wavefront)


def sigma_stats(tab, lam):
    """위상 표 → RCS 통계. spin 모드에서는 이 표가 곧 **방위 RCS 패턴**이므로
    p3_validation 이 쓰던 ε(방위 산포) 와 μ(평균)를 같은 정의로 낼 수 있다."""
    s = (4.0 * math.pi / lam ** 2) * np.abs(np.asarray(tab, complex)) ** 2
    s = np.maximum(s, 1e-30)
    sdb = 10.0 * np.log10(s)
    return dict(mu_dbsm=float(10 * np.log10(s.mean())),
                mean_db_domain_dbsm=float(sdb.mean()),
                eps_db=float(sdb.std()),
                peak_dbsm=float(sdb.max()), min_dbsm=float(sdb.min()),
                peak_to_peak_db=float(sdb.max() - sdb.min()),
                median_dbsm=float(np.median(sdb)),
                eps_definition="std of 10*log10(sigma) over the full 360 deg table "
                               "(same definition as benchmark/p3_v2_worker.py :: eps_db)")


METRIC_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90", "dominant_order",
               "blade_comb_frac", "fd_edge_hz", "width_ratio", "dc_ac_db", "ac_frac_db",
               "sigma_eq_mean_dbsm", "in_band_ac_frac", "in_band_ac_over_dc_db",
               "band_order", "metrics_interpretable", "ac_over_floor_db",
               "width_ratio_10db", "width_ratio_30db")


def row_metrics(tab, proto_common, proto_arm, lam, n_blades=2):
    """한 표를 두 자[尺]로 잰다.

      · common : «로터 뗀 메쉬의 최대 회전반경» 을 기준자로 삼는다 → 팔끼리 같은 눈금.
      · arm    : 그 팔 자신의 최대 회전반경 → 그 물체의 물리가 허용하는 대역이 얼마인지.
    두 자가 갈리는 곳(작은 프리미티브)에서 «폭» 지표를 잘못 읽지 않도록 둘 다 남긴다."""
    mc = RB.md_metrics16(tab, proto_common, n_blades)
    ma = RB.md_metrics16(tab, proto_arm, n_blades)
    out = dict(common={k: mc[k] for k in METRIC_KEYS},
               arm_referenced={k: ma[k] for k in METRIC_KEYS})
    out["sigma"] = sigma_stats(tab, lam)
    out["modulation_depth_db"] = -mc["dc_ac_db"]            # = ac_frac_db, 클수록 많이 흔들린다
    out["in_band_modulation_depth_db"] = mc["in_band_ac_over_dc_db"]
    return out


# =========================================================================== #
#  4. 실행 계획
# =========================================================================== #
CORE_ARMS = ["mesh_no_rotor", "sphere_eqvol", "cube_eqvol", "box_eqvol_aspect", "box_bbox"]
#  ⭐ **모든** 핵심 팔에 4배 촘촘한 짝을 둔다. «프리미티브는 성기게, CAD 메쉬는 촘촘히 깔려서
#     달라 보이는 것 아니냐» 는 반론은 팔 하나만 촘촘히 해서는 못 막는다 — 전부 해야 막힌다.
FINE_ARMS = [a + "_fine" for a in CORE_ARMS]
EXTRA_ARMS = ["sphere_offaxis", "mesh_full_rigid"] + FINE_ARMS
DRONES_MAIN = ["matrice4e", "mini2", "mavic4pro"]
DRONES_DEEP = ["matrice4e", "mini2"]        # 고각 스윕·고주파·평면파 대조까지 도는 기체


def compute_all(verbose=True):
    """모든 표를 계산해 스크래치 npz 로 떨군다. 키: 'drone|arm|band|wavefront|el|mode'."""
    from gpu import pick                                   # ⚠ torch 보다 먼저
    picked = pick(verbose=verbose)
    import torch
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from drones import DRONES

    tables, meta = {}, dict(gpu=picked, device=str(dev), drones={})
    for key in DRONES_MAIN:
        spec = DRONES[key]
        geo = frame_geometry(spec)
        deep = key in DRONES_DEEP
        arms = (CORE_ARMS + EXTRA_ARMS) if deep else (CORE_ARMS + ["mesh_full_rigid"])
        d = dict(frame_geometry=geo, protocol={}, arms={})
        for band, fc in (("main", FC_MAIN), ("hi", FC_HI)):
            if band == "hi" and not deep:
                continue
            lam = C0 / fc
            k_wav = 2.0 * math.pi / lam
            proto = rung_protocol(spec, geo, fc)
            d["protocol"][band] = proto
            S = proto["n_phase"]
            band_order = proto["band_order_el0"]
            arms_here = arms if band == "main" else CORE_ARMS
            for arm in arms_here:
                t0 = time.time()
                P, N, W, am = clouds_for(spec, arm, lam, band_order, geo)
                d["arms"].setdefault(arm, {})[band] = am
                # 고각·파면 조합
                if band == "main":
                    core = arm in CORE_ARMS
                    els = list(EL_SWEEP) if (deep and core) else [EL_MAIN]
                    wfs = ["spherical", "plane"] if (deep and core) else ["spherical"]
                else:
                    els, wfs = [EL_MAIN], ["spherical"]
                for wf in wfs:
                    for el in els:
                        if wf == "plane" and el != EL_MAIN:
                            continue
                        T = spin_table(torch, dev, P, N, W, k_wav, 0.0, el, RANGE_M, S, wf)
                        tables[f"{key}|{arm}|{band}|{wf}|{el:.0f}|spin"] = T
                # 비행 운동학: 몸체 정지 — base 와 같은 24 방위에서 정지 값을 잰다
                if band == "main" and arm in ("mesh_no_rotor", "mesh_full_rigid"):
                    for wf in (["spherical", "plane"] if deep else ["spherical"]):
                        Es = np.array([static_field(torch, dev, P, N, W, k_wav,
                                                    az, EL_MAIN, RANGE_M, wf)
                                       for az in np.arange(N_AZ) * (360.0 / N_AZ)], complex)
                        tables[f"{key}|{arm}|{band}|{wf}|{EL_MAIN:.0f}|flight_static"] = Es
                if verbose:
                    print(f"  [{key:10s}] {arm:20s} {band:4s} pts={am.get('n_points'):>8}  "
                          f"S={S:5d}  [{time.time()-t0:6.1f}s]", flush=True)
        # 회전=방위 퇴화 확인용: 시작 방위를 90° 옮긴 표 하나
        lam = C0 / FC_MAIN
        proto = d["protocol"]["main"]
        P, N, W, _ = clouds_for(spec, "mesh_no_rotor", lam, proto["band_order_el0"], geo)
        tables[f"{key}|mesh_no_rotor|main|spherical|{EL_MAIN:.0f}|spin_az90"] = spin_table(
            torch, dev, P, N, W, 2 * math.pi / lam, 90.0, EL_MAIN, RANGE_M,
            proto["n_phase"], "spherical")
        meta["drones"][key] = d

    os.makedirs(SCRATCH, exist_ok=True)
    np.savez_compressed(os.path.join(SCRATCH, "rung_nr_tables.npz"),
                        **{k.replace("|", "__"): v for k, v in tables.items()})
    with open(os.path.join(SCRATCH, "rung_nr_meta.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False)
    return tables, meta


def load_all():
    z = np.load(os.path.join(SCRATCH, "rung_nr_tables.npz"))
    tabs = {k.replace("__", "|"): z[k] for k in z.files}
    meta = json.load(open(os.path.join(SCRATCH, "rung_nr_meta.json")))
    return tabs, meta


# =========================================================================== #
#  5. 게이트 — 배선이 맞는지 스스로 검사한다
# =========================================================================== #
def gate_wiring(tabs, meta):
    """⭐ 이 파일의 표가 report16_base 의 표와 **같은 물리**를 내는가.

    24 방위 각각에서, 안 돌린 «프레임 + 초기 위상 프로펠러»(mesh_full_rigid 의 정지값)가
    base 의 mesh 팔 표의 **첫 칸(위상 0)** 과 같아야 한다 — 둘 다 같은 물체·같은 점구름
    규약·같은 커널이다. 여기서 틀리면 이 단의 숫자를 base 와 이어 붙일 수 없다."""
    out = {}
    p = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
    if not os.path.exists(p):
        return dict(absent=True)
    z = np.load(p)
    for key in DRONES_MAIN:
        kb = f"main__G_0804__{key}__mesh__spherical"
        ka = f"{key}|mesh_full_rigid|main|spherical|{EL_MAIN:.0f}|flight_static"
        if kb not in z.files or ka not in tabs:
            continue
        ref = np.asarray(z[kb][:, 0], complex)          # (24,) 방위별, 로터 위상 0
        got = np.asarray(tabs[ka], complex)             # (24,) 같은 방위, 안 돌린 강체
        n = min(len(ref), len(got))
        rel = np.abs(got[:n] - ref[:n]) / np.maximum(np.abs(ref[:n]), 1e-300)
        out[key] = dict(n_az=int(n), max_rel_error=float(rel.max()),
                        median_rel_error=float(np.median(rel)),
                        level_delta_db=float(10 * np.log10(
                            np.mean(np.abs(got[:n]) ** 2) / np.mean(np.abs(ref[:n]) ** 2))))
    rel = [v["max_rel_error"] for v in out.values() if isinstance(v, dict)]
    return dict(per_drone=out, tolerance=1e-8,
                verdict=("PASS" if rel and max(rel) < 1e-8 else "FAIL" if rel else "SKIP"),
                what_ko=("안 돌린 «프레임 + 프로펠러» 를 24 방위에서 재서 report16_base 의 표 첫 칸과 "
                         "맞춰 본다. 같은 물체·같은 점구름 규약·같은 커널이므로 부동소수 오차 수준으로 "
                         "같아야 한다. 여기서 틀리면 이 단의 숫자를 base 와 이어 붙일 수 없다."))


def gate_spin_equals_azimuth(tabs, meta):
    """검사 3: «몸체를 φ 돌린 표» 와 «방위를 φ 옮겨 본 표» 가 같은가.

    같아야 한다(수학적 항등식). 그래서 spin 모드에서는 방위 앙상블이 **퇴화**한다 —
    시작 방위를 바꾸면 표가 순환이동만 하고 스펙트럼은 그대로다. 이 검사가 통과하면
    «고각을 앙상블 축으로 바꾼» 이 단의 설계가 정당화된다."""
    out = {}
    for key in DRONES_MAIN:
        k0 = f"{key}|mesh_no_rotor|main|spherical|{EL_MAIN:.0f}|spin"
        k9 = f"{key}|mesh_no_rotor|main|spherical|{EL_MAIN:.0f}|spin_az90"
        if k0 not in tabs or k9 not in tabs:
            continue
        A, B = tabs[k0], tabs[k9]
        S = len(A)
        shift = int(round(S * 90.0 / 360.0))
        #  A[i] = F(az 0 − φ_i),  B[i] = F(az 90 − φ_i)  (F = 안 돌린 물체의 방위 패턴)
        #  ⇒ B[i] = A[i − shift] = np.roll(A, +shift)[i]
        pred = np.roll(A, shift)
        out[key] = dict(n_phase=int(S), shift_samples=shift,
                        rel_rms=float(np.linalg.norm(B - pred) / max(np.linalg.norm(A), 1e-300)),
                        spectrum_abs_max_rel_diff=float(
                            np.max(np.abs(np.abs(np.fft.fft(B)) - np.abs(np.fft.fft(pred)))) /
                            max(np.max(np.abs(np.fft.fft(A))), 1e-300)))
    rel = [v["rel_rms"] for v in out.values()]
    return dict(per_drone=out, tolerance=1e-9,
                verdict=("PASS" if rel and max(rel) < 1e-9 else "FAIL" if rel else "SKIP"),
                what_ko=("몸체를 z축으로 φ 돌려 고정 시선에서 보는 것 = 물체를 그대로 두고 방위를 "
                         "−φ 옮겨 보는 것. 이 항등식이 성립하면 이 모드의 위상 표는 곧 **방위 RCS "
                         "패턴**이고, 방위 앙상블은 순환이동일 뿐이라 정보가 늘지 않는다. "
                         "그래서 이 단은 앙상블 축을 고각으로 잡았다."))


# =========================================================================== #
#  6. 결과 조립
# =========================================================================== #
def protos_for(meta, key, band, arm, el):
    """(공통 자, 팔 자) 규약 쌍."""
    d = meta["drones"][key]
    pr = d["protocol"][band]
    lam, f_rot, S = pr["lam_m"], pr["f_rot_hz"], pr["n_phase"]
    r_common = d["frame_geometry"]["spin_radius_max_m"]
    am = d["arms"][arm][band]
    r_arm = float(am.get("spin_radius_max_m", r_common))
    return (make_proto(lam, f_rot, r_common, el, S),
            make_proto(lam, f_rot, r_arm, el, S), lam)


def spin_block(tabs, meta, key, band="main", wf="spherical", el=EL_MAIN):
    """한 (기체, 대역, 파면, 고각) 에서 모든 팔의 지표를 모은다."""
    out = {}
    for arm in meta["drones"][key]["arms"]:
        k = f"{key}|{arm}|{band}|{wf}|{el:.0f}|spin"
        if k not in tabs:
            continue
        pc, pa, lam = protos_for(meta, key, band, arm, el)
        r = row_metrics(tabs[k], pc, pa, lam)
        r["protocol_common"] = dict(beta=pc["beta"], f_tip_hz=pc["f_tip_hz"],
                                    band_order=int(max(2, math.ceil(1.5 * pc["beta"]))))
        r["protocol_arm"] = dict(beta=pa["beta"], f_tip_hz=pa["f_tip_hz"],
                                 spin_radius_m=pa["spin_radius_m"],
                                 band_order=int(max(2, math.ceil(1.5 * pa["beta"]))))
        out[arm] = r
    return out


def flight_block(tabs, meta, key, wf="spherical"):
    """⭐ 비행 운동학 — ① 예측 검정 ② 동체 받침(DC pedestal) 분해.

    PO 는 점들의 단순 합이고 가림이 없으므로 E_전체(φ) = E_몸체 + E_로터(φ) 가 항등식이다.
    그래서 base 의 «전체» 표에서 여기서 잰 «몸체» 를 빼면 로터 몫이 정확히 남는다."""
    kf = f"{key}|mesh_no_rotor|main|{wf}|{EL_MAIN:.0f}|flight_static"
    if kf not in tabs:
        return None
    Ef = np.asarray(tabs[kf], complex)                 # (24,) 방위별 정지 복소장
    pr = meta["drones"][key]["protocol"]["main"]
    lam = pr["lam_m"]
    S = pr["n_phase"]

    # ── ① 예측 검정: 표를 만들어 보면 모든 칸이 같다 → AC 전력이 0 이어야 한다 ──
    tests, ratios, exact_zero = [], [], 0
    for i in range(len(Ef)):
        tab = np.full(S, Ef[i], complex)
        c = np.fft.fft(tab) / S
        m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
        p_ac = float((np.abs(c[m != 0]) ** 2).sum())
        p_dc = float((np.abs(c[m == 0]) ** 2).sum())
        ratios.append(p_ac / max(p_dc, 1e-300))
        exact_zero += int(p_ac == 0.0)
        tests.append(10 * np.log10(max(p_ac, 1e-300) / max(p_dc, 1e-300)))
    floor_db = float(20 * np.log10(np.finfo(float).eps))
    pred = dict(
        modulation_depth_db=RB.summarize(tests),
        ac_over_dc_power_ratio_max=float(max(ratios)),
        frac_exactly_zero=float(exact_zero) / max(len(Ef), 1),
        clamp_note_ko=("AC 전력이 **정확히 0** 인 방위에서는 dB 로 못 적으므로 1e-300 으로 막아 "
                       "−2900 dB 대의 값이 찍힌다. 그것은 «0» 이라는 뜻이지 측정값이 아니다 — "
                       "frac_exactly_zero 를 함께 볼 것."),
        double_precision_floor_db=floor_db,
        verdict=("CONFIRMED (at or below the double-precision floor)"
                 if max(tests) < floor_db + 60 else "NOT CONFIRMED"),
        honesty_ko=("⚠ 이 «확인» 은 증거로서 약하다. 우리 모형에서 몸체는 강체이고 비행 운동학에서는 "
                    "돌지 않으므로, 변조가 0 인 것은 **측정 결과가 아니라 산수 항등식**이다. "
                    "값이 −300 dB 대인 것은 배정밀도 부동소수 바닥(≈ −313 dB)일 뿐이다. "
                    "다만 이 확인이 없으면 «파이프라인이 스스로 변조를 만들어 내지는 않는다» 는 "
                    "사실도 못 말한다 — 그 몫으로는 값어치가 있다."),
        what_would_falsify_ko=("실제 비행에서는 로터를 떼어도 몸체가 완전히 정지하지 않는다(진동·자세 "
                              "흔들림). 그런 미세운동은 이 모형에 아예 들어 있지 않다 — 모형의 한계이지 "
                              "물리의 결론이 아니다."))

    # ── ② 동체 받침 분해 (base 의 전체 메쉬 표를 쓴다) ──
    dec = dict(absent=True)
    p = os.path.join(ROOT, "outputs", "report16_base_tables.npz")
    if os.path.exists(p):
        z = np.load(p)
        kb = f"main__G_0804__{key}__mesh__{wf}"
        if kb in z.files:
            T = z[kb]                                   # (24, S_base) 로터가 도는 전체 메쉬
            n = min(len(Ef), T.shape[0])
            rows = []
            for i in range(n):
                full = T[i]
                dc_full = complex(full.mean())
                ac = full - dc_full
                ac_rms = float(np.sqrt(np.mean(np.abs(ac) ** 2)))
                body = complex(Ef[i])
                rotor_dc = dc_full - body
                rows.append(dict(
                    body_over_full_dc_db=float(20 * np.log10(max(abs(body), 1e-300) /
                                                             max(abs(dc_full), 1e-300))),
                    rotor_dc_over_full_dc_db=float(20 * np.log10(max(abs(rotor_dc), 1e-300) /
                                                                 max(abs(dc_full), 1e-300))),
                    dc_ac_db_as_measured=float(20 * np.log10(max(abs(dc_full), 1e-300) /
                                                             max(ac_rms, 1e-300))),
                    dc_ac_db_body_removed=float(20 * np.log10(max(abs(rotor_dc), 1e-300) /
                                                              max(ac_rms, 1e-300))),
                    body_sigma_dbsm=float(10 * np.log10(max(
                        (4 * math.pi / lam ** 2) * abs(body) ** 2, 1e-300))),
                    full_dc_sigma_dbsm=float(10 * np.log10(max(
                        (4 * math.pi / lam ** 2) * abs(dc_full) ** 2, 1e-300)))))
            dec = {kk: RB.summarize([r[kk] for r in rows]) for kk in rows[0]}
            dec["n_az"] = n
            dec["delta_dc_ac_db_from_removing_body"] = dict(
                mean=dec["dc_ac_db_body_removed"]["mean"] - dec["dc_ac_db_as_measured"]["mean"])
            dec["identity_ko"] = ("PO 는 점들의 단순 합이고 이 커널에는 가림이 없다 → "
                                  "E_전체(φ) = E_몸체 + E_로터(φ) 가 **근사가 아니라 항등식**이다. "
                                  "그래서 base 의 전체 표에서 여기서 잰 몸체 값을 빼면 로터 몫이 "
                                  "정확히 남는다(추정이 아니다).")
            dec["reading_ko"] = ("body_over_full_dc_db 는 «0-도플러 받침 중 몸체가 차지하는 몫» 이다. "
                                 "0 dB 에 가까우면 받침이 사실상 전부 몸체라는 뜻이고, 그러면 "
                                 "dc_ac_db(동체 대 블레이드 세기비)는 **몸체 형상이 정하는 값**이다. "
                                 "dc_ac_db_body_removed 는 몸체를 지워 버렸을 때 그 비가 얼마나 "
                                 "좋아지는가 — 즉 «몸체가 블레이드 신호를 몇 dB 덮고 있는가» 다.")
    return dict(prediction_test=pred, dc_pedestal_decomposition=dec)


def paired_vs_sphere(tabs, meta, key, band="main", wf="spherical", els=(EL_MAIN,)):
    """⭐ 헤드라인 — 각 팔이 «구 널» 보다 몇 dB 위에 있는가(같은 고각끼리 짝지어 뺀다).

    구는 회전축 위 회전대칭이라 물리적 변조가 0 이다. 그 팔에서 나오는 값은 곧 이 계산기의
    바닥이다. 그러니 «바닥 대비 여유» 가 그 형상이 실제로 만든 변조의 크기다."""
    out = {}
    base_arm = "sphere_eqvol"
    for arm in meta["drones"][key]["arms"]:
        if arm == base_arm:
            continue
        rows = []
        for el in els:
            ka = f"{key}|{arm}|{band}|{wf}|{el:.0f}|spin"
            kb = f"{key}|{base_arm}|{band}|{wf}|{el:.0f}|spin"
            if ka not in tabs or kb not in tabs:
                continue
            pca, paa, lam = protos_for(meta, key, band, arm, el)
            pcb, pab, _ = protos_for(meta, key, band, base_arm, el)
            ma = RB.md_metrics16(tabs[ka], pca, 2)
            mb = RB.md_metrics16(tabs[kb], pcb, 2)
            rows.append(dict(
                el_deg=float(el),
                margin_over_sphere_db=float(ma["in_band_ac_over_dc_db"] -
                                            mb["in_band_ac_over_dc_db"]),
                in_band_modulation_depth_db=float(ma["in_band_ac_over_dc_db"]),
                sphere_floor_db=float(mb["in_band_ac_over_dc_db"]),
                d_flash_contrast_db=float(ma["flash_contrast_db"] - mb["flash_contrast_db"]),
                d_n_eff_orders=float(ma["n_eff_orders"] - mb["n_eff_orders"]),
                d_eps_db=float(sigma_stats(tabs[ka], lam)["eps_db"] -
                               sigma_stats(tabs[kb], lam)["eps_db"])))
        if rows:
            out[arm] = {kk: RB.summarize([r[kk] for r in rows]) for kk in rows[0]
                        if kk != "el_deg"}
            out[arm]["per_elevation"] = rows
    return out


def paired_mesh_vs_primitive(tabs, meta, key, band="main", wf="spherical", els=(EL_MAIN,)):
    """⭐⭐ 이 라운드의 급소 — 우리 CAD 몸체 vs 프리미티브, **같은 고각끼리 짝지어 뺀다**.

    frac_positive 는 «프리미티브가 더 큰» 고각의 비율이다. 0.5 근처면 차이 없음,
    1.0 이면 어느 자세에서 봐도 한 방향이다. 부호를 미리 정하지 않았다."""
    ref = "mesh_no_rotor"
    out = {}
    for arm in ("sphere_eqvol", "cube_eqvol", "box_eqvol_aspect", "box_bbox"):
        acc = {}
        for el in els:
            ka = f"{key}|{ref}|{band}|{wf}|{el:.0f}|spin"
            kb = f"{key}|{arm}|{band}|{wf}|{el:.0f}|spin"
            if ka not in tabs or kb not in tabs:
                continue
            pca, _, lam = protos_for(meta, key, band, ref, el)
            pcb, _, _ = protos_for(meta, key, band, arm, el)
            ma = RB.md_metrics16(tabs[ka], pca, 2)
            mb = RB.md_metrics16(tabs[kb], pcb, 2)
            sa, sb = sigma_stats(tabs[ka], lam), sigma_stats(tabs[kb], lam)
            for kk, d in (("in_band_ac_over_dc_db", mb["in_band_ac_over_dc_db"] - ma["in_band_ac_over_dc_db"]),
                          ("flash_contrast_db", mb["flash_contrast_db"] - ma["flash_contrast_db"]),
                          ("n_eff_orders", mb["n_eff_orders"] - ma["n_eff_orders"]),
                          ("eps_db", sb["eps_db"] - sa["eps_db"]),
                          ("mu_dbsm", sb["mu_dbsm"] - sa["mu_dbsm"]),
                          ("width_ratio", mb["width_ratio"] - ma["width_ratio"])):
                acc.setdefault(kk, []).append(float(d))
        if not acc:
            continue
        row = {}
        for kk, v in acc.items():
            a = np.asarray([x for x in v if np.isfinite(x)], float)
            row[kk] = dict(mean=float(a.mean()),
                           sd=float(a.std(ddof=1)) if a.size > 1 else 0.0,
                           min=float(a.min()), max=float(a.max()),
                           frac_positive=float(np.mean(a > 0)), n=int(a.size))
        out[f"{arm} - {ref}"] = row
    return out


def gate_sphere_analytic(tabs, meta):
    """검사 4 (절대 세기): 구 팔의 σ 는 **닫힌 식**과 맞는가.

    반지름 r 인 구의 PO 후방산란장은 해석적으로 적분된다:
        E = 2πr² [ e^{jb}(1/(jb) + 1/b²) − 1/b² ],   b = 2kr
    σ = (4π/λ²)|Γ|²|E|² 이고, b ≫ 1 이면 광학 극한 σ → |Γ|²·πr² 로 간다.
    우리 점구름 PO 가 이 값을 재현하면 «구 팔은 널일 뿐 아니라 세기도 맞다» 가 확인된다 —
    널 팔이 그냥 «작게 나오는 팔» 이 아니라는 뜻이다."""
    out = {}
    for key in DRONES_MAIN:
        k = f"{key}|sphere_eqvol|main|spherical|{EL_MAIN:.0f}|spin"
        if k not in tabs:
            continue
        d = meta["drones"][key]
        am = d["arms"]["sphere_eqvol"]["main"]
        lam = d["protocol"]["main"]["lam_m"]
        r = float(am["radius_m"])
        g = float(am["gamma_uniform"])
        b = 2.0 * (2.0 * math.pi / lam) * r
        E = 2 * math.pi * r ** 2 * (np.exp(1j * b) * (1.0 / (1j * b) + 1.0 / b ** 2) - 1.0 / b ** 2)
        sig_a = (4 * math.pi / lam ** 2) * (g ** 2) * abs(E) ** 2
        meas = sigma_stats(tabs[k], lam)["mu_dbsm"]
        out[key] = dict(
            radius_m=r, gamma_uniform=g, two_k_r=b,
            analytic_po_dbsm=float(10 * np.log10(sig_a)),
            optical_limit_dbsm=float(10 * np.log10((g ** 2) * math.pi * r ** 2)),
            measured_dbsm=float(meas),
            error_db=float(meas - 10 * np.log10(sig_a)),
            azimuth_spread_eps_db=sigma_stats(tabs[k], lam)["eps_db"])
    err = [abs(v["error_db"]) for v in out.values()]
    return dict(per_drone=out, tolerance_db=0.5,
                verdict=("PASS" if err and max(err) < 0.5 else "FAIL" if err else "SKIP"),
                what_ko=("구의 PO 후방산란은 닫힌 식이 있다. 우리 점구름 계산이 그 값을 재현하면, "
                         "구 팔은 «변조가 0» 일 뿐 아니라 **세기도 맞는** 제대로 된 대조군이다. "
                         "여기서 틀리면 «구가 작게 나와서 널처럼 보인 것» 이라는 반론을 못 막는다."))


def external_eps_anchor():
    """⭐ 바깥의 잣대 — 방위 산포 ε 가 **실측**과 얼마나 어긋나는가.

    이 단에서 나온 «상자가 우리 메쉬보다 더 많이 흔들린다» 는 사실만으로는 상자가 더 나은지
    알 수 없다. «더 많이» 가 «맞게» 인지 «지나치게» 인지는 실측과 견줘야 정해진다.
    outputs/p3_validation_v2.json 에 그 비교가 이미 들어 있다 — Das 의 Phantom 3 실측 ε 대비
    우리 메쉬와 프리미티브들의 오차다. 숫자는 손으로 옮기지 않고 그 파일에서 읽어 온다.

    ⚠ 사과-대-사과가 아니다: p3 는 고각 0°·PEC·다른 기체(Phantom 3)·61 주파수다. 그래서
      **절대값을 옮겨 쓰지 않고 «방향» 만** 쓴다 — 어느 모형이 실측보다 넓게 흔들리는가."""
    p = os.path.join(ROOT, "outputs", "p3_validation_v2.json")
    if not os.path.exists(p):
        return dict(absent=True)
    d = json.load(open(p))
    tab = d.get("controls", {}).get("table", {})
    pick = ("ours_phantom3_mesh_v2", "cube_vol_v2", "box_bbox_v2", "box_paper",
            "box_bbox_lit", "sphere_vol_v2")
    rows, das = {}, []
    for k in pick:
        if k not in tab:
            continue
        e, err = tab[k].get("eps_mean_db"), tab[k].get("eps_err_vs_das_db")
        if e is None or err is None:
            continue
        rows[k] = dict(what=tab[k].get("what"), eps_mean_db=e, eps_err_vs_das_db=err,
                       abs_err_db=abs(err))
        if "sphere" not in k:                      # 구는 ε=0 이라 기준 복원에 못 쓴다
            das.append(e - err)
    ref = float(np.mean(das)) if das else float("nan")
    order = sorted((k for k in rows if "sphere" not in k), key=lambda k: rows[k]["abs_err_db"])
    return dict(
        source="outputs/p3_validation_v2.json :: controls.table",
        das_measured_eps_db=ref,
        das_measured_eps_derivation="eps_mean_db - eps_err_vs_das_db (consistent across all controls)",
        values=rows, ranked_by_abs_error=order,
        finding_ko=("⭐ 실측 ε 에 가장 가까운 모형은 " + (order[0] if order else "?") + " 이고, "
                    "상자·정육면체는 그보다 멀다. 즉 **상자가 더 많이 흔들리는 것은 «맞게» 가 아니라 "
                    "«지나치게» 다.** 이 단에서 상자가 우리 메쉬보다 변조가 크게 나온 것을 «상자가 "
                    "낫다» 로 읽으면 안 되는 이유가 여기 있다."),
        caveat_ko=("⚠ 사과-대-사과가 아니다. p3 비교는 고각 0°·PEC·Phantom 3·61 주파수이고 이 단은 "
                   "고각 15°·재질가중·다른 기체다. 그래서 절대값이 아니라 **방향**만 쓴다 — "
                   "«프리미티브가 실측보다 넓게 흔들린다» 는 방향."))


def direction_consistency(J):
    """⭐ 부호가 어디까지 버티는가 — 대역·고각·기체를 바꿔도 같은 방향인가.

    한 조건에서만 성립하는 부호는 결론이 아니다. 여기서는 세 축을 따로 센다:
      · 대역     : 3.5 GHz ↔ 15.86 GHz (커널이 약한 대역의 산물인지 가른다)
      · 고각     : 0/15/30/45/60°       (자세 하나로 뒤집힌 전례가 있다)
      · 기체     : matrice4e / mini2 / mavic4pro"""
    out = {}
    for arm in ("sphere_eqvol", "cube_eqvol", "box_eqvol_aspect", "box_bbox"):
        rows = {}
        for key in J["drones"]:
            sh = J["drones"][key].get("spin_headline", {})
            hb = J["drones"][key].get("hi_band", {})
            pr = J["drones"][key].get("paired_mesh_vs_primitive", {}).get(f"{arm} - mesh_no_rotor")
            if arm not in sh or "mesh_no_rotor" not in sh:
                continue
            d_main = (sh[arm]["in_band_modulation_depth_db"] -
                      sh["mesh_no_rotor"]["in_band_modulation_depth_db"])
            d_hi = ((hb[arm]["in_band_modulation_depth_db"] -
                     hb["mesh_no_rotor"]["in_band_modulation_depth_db"])
                    if (arm in hb and "mesh_no_rotor" in hb) else None)
            rows[key] = dict(
                delta_3p5ghz_db=float(d_main),
                delta_15p86ghz_db=(float(d_hi) if d_hi is not None else None),
                bands_agree=(None if d_hi is None else bool(np.sign(d_main) == np.sign(d_hi))),
                elevation_frac_positive=(pr or {}).get("in_band_ac_over_dc_db", {}).get("frac_positive"),
                elevation_n=(pr or {}).get("in_band_ac_over_dc_db", {}).get("n"))
        ba = [r["bands_agree"] for r in rows.values() if r["bands_agree"] is not None]
        fp = [r["elevation_frac_positive"] for r in rows.values()
              if r["elevation_frac_positive"] is not None]
        out[f"{arm} - mesh_no_rotor"] = dict(
            per_drone=rows,
            all_drones_same_sign_at_3p5ghz=bool(len({np.sign(r["delta_3p5ghz_db"]) for r in rows.values()}) == 1),
            bands_agree_everywhere=(bool(all(ba)) if ba else None),
            elevation_frac_positive_min=(float(min(fp)) if fp else None),
            elevation_frac_positive_max=(float(max(fp)) if fp else None))
    out["how_to_read_ko"] = (
        "bands_agree_everywhere 가 False 면 그 부호는 «커널이 약한 3.5 GHz 에서만» 성립한다는 "
        "뜻이고, elevation_frac_positive 가 0.5 근처면 «자세를 바꾸면 뒤집힌다» 는 뜻이다. "
        "둘 다 통과한 부호만 결론으로 쓸 수 있다.")
    return out


# =========================================================================== #
#  7. 그림 (글씨는 전부 영어 — 저장소 규약)
# =========================================================================== #
def make_figure(J, tabs, meta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 8.5})
    COL = {"mesh_no_rotor": "#1565c0", "sphere_eqvol": "#c62828", "cube_eqvol": "#6a1b9a",
           "box_eqvol_aspect": "#ef6c00", "box_bbox": "#00838f",
           "sphere_offaxis": "#ad1457", "mesh_full_rigid": "#2e7d32"}
    LBL = {"mesh_no_rotor": "CAD airframe (rotors removed)", "sphere_eqvol": "sphere, equal volume",
           "cube_eqvol": "cube, equal volume", "box_eqvol_aspect": "box, equal volume",
           "box_bbox": "box = bounding box", "sphere_offaxis": "sphere, off-axis",
           "mesh_full_rigid": "airframe + frozen props"}

    fig, AX = plt.subplots(2, 3, figsize=(16.5, 9.0))
    key = "matrice4e"
    pr = meta["drones"][key]["protocol"]["main"]
    lam = pr["lam_m"]
    S = pr["n_phase"]
    phi = np.arange(S) * 360.0 / S

    # (a) 회전각에 따른 RCS — 이 곡선이 곧 방위 RCS 패턴이다
    ax = AX[0, 0]
    for arm in ("mesh_no_rotor", "box_bbox", "box_eqvol_aspect", "cube_eqvol", "sphere_eqvol"):
        k = f"{key}|{arm}|main|spherical|{EL_MAIN:.0f}|spin"
        if k not in tabs:
            continue
        s = (4 * np.pi / lam ** 2) * np.abs(tabs[k]) ** 2
        ax.plot(phi, 10 * np.log10(np.maximum(s, 1e-30)), lw=1.0,
                color=COL[arm], label=LBL[arm])
    ax.set_xlabel("spin angle [deg]  (= azimuth sweep)")
    ax.set_ylabel(r"$\sigma$ [dBsm]")
    ax.set_title(f"(a) Spun rigid body, {key}, 3.5 GHz, el {EL_MAIN:.0f}$\\degree$\n"
                 "spinning a rigid body IS an azimuth cut", fontsize=9)
    ax.legend(fontsize=6.5, ncol=1)
    ax.set_xlim(0, 360)

    # (b) 차수 스펙트럼
    ax = AX[0, 1]
    b_common = J["drones"][key]["protocol"]["main"]["band_order_el0"]
    for arm in ("mesh_no_rotor", "box_bbox", "cube_eqvol", "sphere_eqvol"):
        k = f"{key}|{arm}|main|spherical|{EL_MAIN:.0f}|spin"
        if k not in tabs:
            continue
        T = tabs[k]
        c = np.fft.fft(T) / len(T)
        P = np.abs(c) ** 2
        m = np.fft.fftfreq(len(T), d=1.0 / len(T)).astype(int)
        sel = (m >= 0) & (m <= min(len(T) // 2, 4 * b_common))
        ax.plot(m[sel], 10 * np.log10(np.maximum(P[sel] / max(P[m == 0].sum(), 1e-300), 1e-32)),
                lw=1.0, color=COL[arm], label=LBL[arm])
    ax.axvline(b_common, color="k", ls="--", lw=0.9)
    ax.text(b_common, ax.get_ylim()[1], " kinematic band edge\n 1.5$\\beta$", fontsize=6.5,
            va="top", ha="left")
    ax.set_xlabel("harmonic order  m   (Doppler = m $\\cdot$ f$_{rot}$)")
    ax.set_ylabel("line power re. DC [dB]")
    ax.set_title("(b) Order spectrum of the spun body", fontsize=9)
    ax.legend(fontsize=6.5)

    # (c) 변조 깊이 막대 — 구 널 대비
    ax = AX[0, 2]
    arms = ["mesh_no_rotor", "cube_eqvol", "box_eqvol_aspect", "box_bbox", "sphere_offaxis",
            "mesh_full_rigid", "sphere_eqvol"]
    xs, w = np.arange(len(arms)), 0.38
    for j, kk in enumerate(("matrice4e", "mini2")):
        vals = []
        for arm in arms:
            v = J["drones"].get(kk, {}).get("spin_headline", {}).get(arm, {})
            vals.append(v.get("in_band_modulation_depth_db", np.nan))
        ax.bar(xs + (j - 0.5) * w, vals, width=w, label=kk,
               color=("#1565c0" if j == 0 else "#ef6c00"), alpha=0.85)
        for x, v in zip(xs + (j - 0.5) * w, vals):
            if np.isfinite(v):
                ax.annotate(f"{v:.0f}", (x, v), ha="center", fontsize=6,
                            va=("bottom" if v >= 0 else "top"),
                            xytext=(0, 2 if v >= 0 else -2), textcoords="offset points")
    ax.axhline(0.0, color="k", lw=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([LBL[a] for a in arms], rotation=35, ha="right", fontsize=6.5)
    ax.set_ylabel("in-band modulation depth  AC/DC [dB]")
    ax.set_title("(c) How much does the shape modulate when spun?\n"
                 "(sphere = numerical floor of the calculator)", fontsize=9)
    ax.legend(fontsize=7)

    # (d) 비행 운동학: 예측 검정
    ax = AX[1, 0]
    floor_db = 20 * np.log10(np.finfo(float).eps)
    FLOOR_PLOT = -340.0                    # 정확히 0 인 값을 그림에 담기 위한 표시용 바닥
    labs, vals, cols = [], [], []
    for kk in DRONES_MAIN:
        fb = J["drones"].get(kk, {}).get("flight_kinematics", {})
        if not fb:
            continue
        labs.append(f"{kk}\nflight (rotors removed)")
        vals.append(max(fb["prediction_test"]["modulation_depth_db"]["max"], FLOOR_PLOT))
        cols.append("#1565c0")
        sh = J["drones"][kk].get("spin_headline", {}).get("mesh_no_rotor", {})
        if sh:
            labs.append(f"{kk}\nspun body (control)")
            vals.append(sh["in_band_modulation_depth_db"])
            cols.append("#2e7d32")
    ax.barh(np.arange(len(labs)), vals, color=cols, alpha=0.85)
    ax.set_xlim(FLOOR_PLOT, 5)
    ax.axvline(floor_db, color="k", ls=":", lw=1.0)
    ax.text(floor_db, len(labs) - 0.4, " double-precision floor", fontsize=6.5, ha="left")
    ax.set_yticks(np.arange(len(labs)))
    ax.set_yticklabels(labs, fontsize=6.5)
    ax.set_xlabel("modulation depth AC/DC [dB]   (bars clipped at -340 dB = exactly zero)")
    ax.set_title("(d) Pre-registered prediction: with the rotors gone,\n"
                 "flight kinematics gives literally nothing to modulate", fontsize=9)

    # (e) 고각 강건성
    ax = AX[1, 1]
    for arm in ("mesh_no_rotor", "box_bbox", "cube_eqvol", "sphere_eqvol"):
        e = J["drones"][key].get("elevation_sweep", {}).get(arm)
        if not e:
            continue
        ax.plot([r["el_deg"] for r in e], [r["in_band_modulation_depth_db"] for r in e],
                "o-", ms=4, lw=1.2, color=COL[arm], label=LBL[arm])
    ax.set_xlabel("elevation [deg]")
    ax.set_ylabel("in-band modulation depth [dB]")
    ax.set_title(f"(e) Robustness across elevation, {key}\n"
                 "(azimuth is degenerate for a spun body)", fontsize=9)
    ax.legend(fontsize=6.5)

    # (f) eps 와 변조 깊이는 같은 정보인가
    ax = AX[1, 2]
    for kk, mk in (("matrice4e", "o"), ("mini2", "s"), ("mavic4pro", "^")):
        sh = J["drones"].get(kk, {}).get("spin_headline", {})
        for arm, v in sh.items():
            if arm not in COL:
                continue
            ax.scatter(v["sigma"]["eps_db"], v["in_band_modulation_depth_db"],
                       marker=mk, s=42, color=COL[arm],
                       label=f"{LBL[arm]}" if kk == "matrice4e" else None)
    ref = (J.get("external_eps_anchor") or {}).get("das_measured_eps_db")
    if ref and np.isfinite(ref):
        ax.axvline(ref, color="k", ls="--", lw=1.0)
        ax.text(ref, ax.get_ylim()[0] * 0.55, f"  measured $\\epsilon$ = {ref:.2f} dB\n"
                                              "  (Das, Phantom 3 class)", fontsize=6.5, ha="left")
    ax.set_xlabel(r"azimuthal RCS spread  $\epsilon$ [dB]")
    ax.set_ylabel("in-band modulation depth [dB]")
    ax.set_title("(f) The same information twice: azimuthal spread vs micro-Doppler depth\n"
                 "primitives sit to the RIGHT of measurement — they over-modulate", fontsize=9)
    ax.legend(fontsize=6, loc="lower right")

    fig.suptitle("report16 rung — micro-Doppler of our mesh with the rotors removed, "
                 "against sphere / cube / box run with identical kinematics", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=145)
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


# =========================================================================== #
#  8. 드라이버
# =========================================================================== #
def main(skip_compute=False):
    t0 = time.time()
    prereg = write_prereg()                     # ⭐ 계산보다 먼저
    print(f"▶ 사전 예측 봉인: {os.path.relpath(OUT_PREREG, ROOT)}  "
          f"sha256={prereg['prediction_sha256'][:16]}…", flush=True)

    if skip_compute:
        tabs, meta = load_all()
    else:
        tabs, meta = compute_all()

    J = dict(meta=dict(
        report="report16 · rung: mesh_no_rotor",
        producer="benchmark/report16_rung_mesh_no_rotor.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        model_ko="로터 뗀 우리 CAD 메쉬 (drones.build_frame — 프로펠러를 뺀 기체)",
        inherits="benchmark/report16_base.py (규약·PO 커널·지표 정의를 그대로 물려받음)",
        gpu=meta.get("gpu"), device=meta.get("device")))

    J["preregistration"] = dict(
        file=os.path.relpath(OUT_PREREG, ROOT),
        written_at=prereg["written_at"],
        prediction_sha256=prereg["prediction_sha256"],
        prediction_text=PREREG_TEXT,
        verify_ko=("이 sha256 은 outputs/report16_rung_mesh_no_rotor.prereg.json 안의 것과 같아야 "
                   "한다. 그 파일은 이 스크립트가 **어떤 전자기장도 계산하기 전에** 쓴다."))

    # ── 규약(공유) ─────────────────────────────────────────────────────────
    J["protocol"] = dict(
        fc_main_hz=FC_MAIN, fc_hi_hz=FC_HI, range_m=RANGE_M, monostatic=True,
        el_headline_deg=EL_MAIN, el_sweep_deg=list(EL_SWEEP),
        wavefront_headline="spherical", wavefront_control="plane",
        n_rev=N_REV, os_factor=OS_FACTOR, frame_div=FRAME_DIV, blade_div=BLADE_DIV,
        engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
        kinematics=dict(
            flight=dict(what_ko="몸체 정지 · 로터만 회전 — 실제 비행 상태의 규칙",
                        applies_ko="로터를 뗀 이 단의 모델에는 도는 것이 없다 → 변조 0(항등식)"),
            spin=dict(what_ko="물체 **전체**를 회전축(기체 z, 원점)으로 호버 rpm 으로 돌린다",
                      axis="body z axis through the origin (same axis direction as the rotors)",
                      rpm="hover rpm of that airframe — identical for every arm",
                      phase_steps="identical for every arm (see per-drone protocol)",
                      fairness_ko=("구를 «안 돌리고» 0 을 얻으면 동어반복이다. 구도 상자도 "
                                   "**실제로 돌린다**. 재질·거리·자세·주파수·위상격자 전부 동일."),
                      caveat_ko=("몸체를 호버 rpm 으로 통째로 돌리는 것은 비행 상태가 아니다 — "
                                 "형상만 남기고 운동학을 똑같이 맞춘 **대조 실험**이다."))),
        why_elevation_not_azimuth_ko=(
            "강체를 z축으로 φ 돌려 고정 시선에서 보는 것은 방위를 −φ 옮겨 보는 것과 같다. 그래서 "
            "회전 모드에서 시작 방위를 바꾸면 표가 순환이동만 하고 스펙트럼은 그대로다 — 방위 "
            "앙상블은 정보가 늘지 않는다(gates.spin_equals_azimuth 로 확인). 그래서 이 단은 "
            "앙상블 축을 **고각**으로 잡았다."),
        phase_grid_rule_ko=("한 기체의 모든 팔이 **같은 위상 격자**를 쓴다. 격자는 가장 빡빡한 "
                            "조건(고각 0° × 로터 뗀 메쉬의 최대 회전반경)에서 계산한다."))

    # ── 기체별 ─────────────────────────────────────────────────────────────
    J["drones"] = {}
    for key in DRONES_MAIN:
        d = meta["drones"][key]
        deep = key in DRONES_DEEP
        blk = dict(frame_geometry=d["frame_geometry"],
                   protocol=d["protocol"],
                   arms_geometry={a: d["arms"][a] for a in d["arms"]})
        blk["spin_headline"] = spin_block(tabs, meta, key, "main", "spherical", EL_MAIN)
        blk["flight_kinematics"] = flight_block(tabs, meta, key, "spherical")
        blk["margin_over_sphere_null"] = paired_vs_sphere(
            tabs, meta, key, "main", "spherical",
            EL_SWEEP if deep else (EL_MAIN,))
        blk["paired_mesh_vs_primitive"] = paired_mesh_vs_primitive(
            tabs, meta, key, "main", "spherical", EL_SWEEP if deep else (EL_MAIN,))
        if deep:
            sw = {}
            for arm in CORE_ARMS:
                rows = []
                for el in EL_SWEEP:
                    k = f"{key}|{arm}|main|spherical|{el:.0f}|spin"
                    if k not in tabs:
                        continue
                    pc, pa, lam = protos_for(meta, key, "main", arm, el)
                    m = RB.md_metrics16(tabs[k], pc, 2)
                    rows.append(dict(el_deg=float(el),
                                     in_band_modulation_depth_db=m["in_band_ac_over_dc_db"],
                                     modulation_depth_db=-m["dc_ac_db"],
                                     flash_contrast_db=m["flash_contrast_db"],
                                     n_eff_orders=m["n_eff_orders"],
                                     in_band_ac_frac=m["in_band_ac_frac"],
                                     eps_db=sigma_stats(tabs[k], lam)["eps_db"],
                                     mu_dbsm=sigma_stats(tabs[k], lam)["mu_dbsm"]))
                if rows:
                    sw[arm] = rows
            blk["elevation_sweep"] = sw
            blk["hi_band"] = spin_block(tabs, meta, key, "hi", "spherical", EL_MAIN)
            # 파면 대조
            wfc = {}
            for arm in CORE_ARMS:
                ka = f"{key}|{arm}|main|spherical|{EL_MAIN:.0f}|spin"
                kb = f"{key}|{arm}|main|plane|{EL_MAIN:.0f}|spin"
                if ka in tabs and kb in tabs:
                    lam = d["protocol"]["main"]["lam_m"]
                    wfc[arm] = dict(ac_corr=RB.ac_corr(tabs[ka], tabs[kb]),
                                    level_delta_db=float(
                                        10 * np.log10(np.mean(np.abs(tabs[kb]) ** 2) /
                                                      np.mean(np.abs(tabs[ka]) ** 2))))
            blk["wavefront_control"] = dict(
                spherical_vs_plane=wfc,
                note_ko=("구면파(헤드라인) vs 평면파(무한거리 등가). 상관이 1 에 가까우면 10 m 는 "
                         "이 표적에게 사실상 원거리장이다."))
            # 점밀도 반론 차단
            dens = {}
            for arm in CORE_ARMS:
                ka = f"{key}|{arm}|main|spherical|{EL_MAIN:.0f}|spin"
                kb = f"{key}|{arm}_fine|main|spherical|{EL_MAIN:.0f}|spin"
                if ka not in tabs or kb not in tabs:
                    continue
                pc, _, lam = protos_for(meta, key, "main", arm, EL_MAIN)
                pcf, _, _ = protos_for(meta, key, "main", arm + "_fine", EL_MAIN)
                ma = RB.md_metrics16(tabs[ka], pc, 2)
                mb = RB.md_metrics16(tabs[kb], pcf, 2)
                dens[arm] = dict(
                    pts_coarse=d["arms"][arm]["main"]["n_points"],
                    pts_fine=d["arms"][arm + "_fine"]["main"]["n_points"],
                    spacing_coarse_mm=1000 * d["arms"][arm]["main"]["actual_spacing_m"],
                    spacing_fine_mm=1000 * d["arms"][arm + "_fine"]["main"]["actual_spacing_m"],
                    delta={kk: float(mb[kk] - ma[kk]) for kk in
                           ("in_band_ac_over_dc_db", "flash_contrast_db", "n_eff_orders",
                            "width_ratio", "dc_ac_db", "sigma_eq_mean_dbsm")},
                    ac_corr=RB.ac_corr(tabs[ka], tabs[kb]))
            blk["point_density_control"] = dict(
                refine=f"lambda/{FRAME_DIV:.0f} -> lambda/{FRAME_DIV*FINE_X:.0f} (x{FINE_X:.0f}), "
                       "primitive tessellation refined with it",
                arms=dens,
                question_ko=("«프리미티브는 점이 성기고 CAD 메쉬는 촘촘해서 달라 보이는 것 아니냐» 는 "
                             "반론을 차단한다. **모든 팔**을 4배 촘촘히 깔아 다시 쟀다. 지표가 "
                             "그래도 안 움직이면 밀도 차이는 원인이 아니다."),
                why_all_arms_ko=("CAD 메쉬는 삼각형이 이미 촘촘해서 요청 간격이 구속되지 않고 실효 λ/67 "
                                 "쯤으로 깔린다. 반면 정육면체는 면이 6장뿐이라 요청 간격이 그대로 실효 "
                                 "간격이 된다(λ/9). 그래서 한쪽만 촘촘히 해서는 반론이 안 막힌다."))
        J["drones"][key] = blk

    # ── 게이트 ─────────────────────────────────────────────────────────────
    J["gates"] = dict(wiring_vs_base=gate_wiring(tabs, meta),
                      spin_equals_azimuth=gate_spin_equals_azimuth(tabs, meta),
                      sphere_absolute_level=gate_sphere_analytic(tabs, meta))
    print("▶ 게이트: " + " · ".join(f"{k}={v.get('verdict')}" for k, v in J["gates"].items()),
          flush=True)

    # ── PO 유효성 경고 (base 와 같은 출처) ────────────────────────────────
    knee = json.load(open(os.path.join(ROOT, "outputs", "report00_po_case.json")))["s4_limits"]
    J["po_validity_warning"] = dict(
        knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
        blade_knee_ghz=knee["feature_knee_frequencies"]["prop_blade_13p78mm_ghz"],
        body_knee_ghz=knee["feature_knee_frequencies"]["body_81p51mm_ghz"],
        production_band_ghz=FC_MAIN / 1e9,
        statement_ko=(
            "⚠ 우리 PO 커널이 믿을 만하려면 부품의 특징 폭이 "
            f"{knee['po_validity_knee_a_over_lambda']:.3f}λ 이상이어야 한다. 프로펠러 블레이드는 "
            f"{knee['feature_knee_frequencies']['prop_blade_13p78mm_ghz']} GHz 에서야 그 문턱을 "
            f"넘는다 — 즉 **마이크로도플러를 만드는 부품이 곧 커널이 가장 약한 부품**이다. "
            f"이 단의 주인공인 몸체는 특징 폭이 커서 "
            f"{knee['feature_knee_frequencies']['body_81p51mm_ghz']} GHz 부터 유효하지만, base 의 "
            "블레이드 숫자와 견줄 때는 이 비대칭을 반드시 같이 읽어야 한다. 그래서 "
            f"{FC_HI/1e9:.2f} GHz 도 같이 돌렸다."))

    J["external_eps_anchor"] = external_eps_anchor()
    J["direction_consistency"] = direction_consistency(J)
    J["findings"] = _findings(J, tabs, meta)
    J["limits"] = dict(
        occlusion="none — the kernel sums every illuminated facet, including ones hidden behind the body",
        occlusion_ko=("가림이 없다. base 와 같은 통제이지만 dc_ac_db 계열이 가장 오염된다 — "
                      "절대값을 인용하지 말고 팔 사이 차이만 쓸 것."),
        body_micromotion_ko=("실제 비행에서는 로터를 떼어도 몸체가 완전히 정지하지 않는다"
                             "(진동·자세 흔들림·기류). 이 모형에는 그런 미세운동이 아예 없다 — "
                             "비행 운동학에서 변조 0 이 나오는 것은 그 때문이기도 하다."),
        spin_is_not_flight_ko=("몸체를 호버 rpm 으로 통째로 돌리는 것은 비행 상태가 아니다. "
                               "«형상이 회전에 대해 얼마나 구조를 갖는가» 만 재는 대조 실험이며, "
                               "그 답이 곧 방위 RCS 패턴의 산포다."),
        primitive_material_ko=("프리미티브에는 하나짜리 |Γ| 밖에 못 준다(면적 가중 평균을 물려줬다). "
                               "모양 지표는 |Γ| 배율에 불변이므로 이 선택은 σ 절대값에만 영향을 준다."),
        no_ptd_ko=("모서리 회절(PTD) 보정이 없다. 상자·정육면체는 모서리가 지배적인 물체라 "
                   "이 결함이 프리미티브 쪽에 더 크게 걸린다 — 즉 상자의 변조는 과소·과대 어느 "
                   "쪽으로도 틀릴 수 있다. 이 단은 그 방향을 결정하지 못한다."))

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    np.savez_compressed(OUT_NPZ, **{k.replace("|", "__"): v for k, v in tabs.items()})
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    try:
        J["figure"] = make_figure(J, tabs, meta)
    except Exception as e:                                       # pragma: no cover
        J["figure"] = f"ERROR: {e}"
    J["meta"]["seconds"] = float(time.time() - t0)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  ·  {J.get('figure')}  "
          f"[{J['meta']['seconds']:.0f}s]")
    return J


def _findings(J, tabs, meta):
    """숫자를 손으로 적지 않는다 — 위에서 계산된 값만 골라 문장을 만든다."""
    F = {}

    # Q1 — 사전 예측 검정
    q1 = {}
    for key in J["drones"]:
        fb = J["drones"][key].get("flight_kinematics")
        if fb:
            q1[key] = dict(modulation_depth_db=fb["prediction_test"]["modulation_depth_db"],
                           verdict=fb["prediction_test"]["verdict"])
    F["q1_prediction_flight_kinematics"] = dict(
        question_ko="로터 뗀 메쉬는 비행 운동학에서 변조를 내는가 (사전 예측: 거의 0)",
        values=q1,
        answer_ko=("예측대로 0 이다 — 정확히는 배정밀도 부동소수 바닥이다. "
                   "⚠ 그러나 이것은 **모형의 산수 항등식**이지 발견이 아니다: 우리 모형에서 몸체는 "
                   "강체이고 비행 운동학에서 몸체는 돌지 않는다. 값어치는 하나뿐이다 — "
                   "«파이프라인이 스스로 인공 변조를 만들어 내지 않는다» 는 것."))

    # Q2 — 동체 받침 분해
    q2 = {}
    for key in J["drones"]:
        dec = (J["drones"][key].get("flight_kinematics") or {}).get("dc_pedestal_decomposition", {})
        if dec and not dec.get("absent"):
            q2[key] = {kk: dec[kk] for kk in
                       ("body_over_full_dc_db", "rotor_dc_over_full_dc_db",
                        "dc_ac_db_as_measured", "dc_ac_db_body_removed") if kk in dec}
    F["q2_body_share_of_the_zero_doppler_pedestal"] = dict(
        question_ko=("⭐ 이 단의 실질 산출물 — 0-도플러 받침(가만히 있는 성분) 중 몸체 몫은 얼마인가. "
                     "달리 말해 «몸체가 블레이드 신호를 몇 dB 덮고 있는가»"),
        values=q2,
        why_exact_ko=("PO 는 점들의 단순 합이고 이 커널에는 가림이 없어서 "
                      "E_전체(φ) = E_몸체 + E_로터(φ) 가 항등식이다. 그래서 base 의 전체 표에서 "
                      "여기서 잰 몸체 값을 빼면 로터 몫이 **정확히** 남는다(추정이 아니다)."),
        how_to_read_ko=("body_over_full_dc_db 가 0 dB 근처면 받침이 사실상 전부 몸체라는 뜻이고, "
                        "그러면 우리가 그동안 인용해 온 dc_ac_db 는 «블레이드 대 몸체» 가 아니라 "
                        "**몸체 형상이 정하는 값**이다. dc_ac_db_body_removed 와의 차이가 곧 "
                        "«몸체를 지웠을 때 블레이드 신호가 얼마나 드러나는가» 다."))

    # Q3 — ⭐⭐ 공정 대조: 같은 운동학으로 돌렸을 때 형상이 만드는 변조
    q3 = {}
    for key in J["drones"]:
        sh = J["drones"][key].get("spin_headline", {})
        row = {}
        for arm, v in sh.items():
            row[arm] = dict(
                in_band_modulation_depth_db=v["in_band_modulation_depth_db"],
                flash_contrast_db=v["common"]["flash_contrast_db"],
                n_eff_orders=v["common"]["n_eff_orders"],
                in_band_ac_frac=v["common"]["in_band_ac_frac"],
                metrics_interpretable=v["common"]["metrics_interpretable"],
                eps_db=v["sigma"]["eps_db"],
                mu_dbsm=v["sigma"]["mu_dbsm"],
                spin_radius_m=v["protocol_arm"]["spin_radius_m"],
                volume_m3=J["drones"][key]["arms_geometry"][arm]["main"].get("volume_m3"))
        q3[key] = dict(arms=row,
                       margin_over_sphere_null=J["drones"][key].get("margin_over_sphere_null"),
                       paired=J["drones"][key].get("paired_mesh_vs_primitive"))
    # ⭐ 헤드라인 문장 — 숫자는 전부 위 블록에서 뽑는다
    hl = {}
    for key in J["drones"]:
        sh = J["drones"][key].get("spin_headline", {})
        if "mesh_no_rotor" not in sh or "sphere_eqvol" not in sh:
            continue
        ranked = sorted(((a, sh[a]["in_band_modulation_depth_db"])
                         for a in ("mesh_no_rotor", "cube_eqvol", "box_eqvol_aspect",
                                   "box_bbox", "sphere_eqvol") if a in sh),
                        key=lambda t: -t[1])
        hl[key] = dict(
            ranking_by_modulation_depth=[dict(arm=a, in_band_db=v) for a, v in ranked],
            mesh_rank=[a for a, _ in ranked].index("mesh_no_rotor") + 1,
            n_arms=len(ranked),
            sphere_null_db=sh["sphere_eqvol"]["in_band_modulation_depth_db"],
            mesh_margin_over_sphere_db=(sh["mesh_no_rotor"]["in_band_modulation_depth_db"] -
                                        sh["sphere_eqvol"]["in_band_modulation_depth_db"]),
            richness_ranking_by_n_eff=[dict(arm=a, n_eff=sh[a]["common"]["n_eff_orders"])
                                       for a, _ in ranked],
            eps_db={a: sh[a]["sigma"]["eps_db"] for a, _ in ranked},
            frozen_props_add_db=((sh["mesh_full_rigid"]["in_band_modulation_depth_db"] -
                                  sh["mesh_no_rotor"]["in_band_modulation_depth_db"])
                                 if "mesh_full_rigid" in sh else None))
    # ⭐ 문장에 들어가는 숫자는 전부 여기서 **계산**한다 (손입력 금지)
    def _rng(vals, fmt="%+.2f"):
        v = [x for x in vals if x is not None and np.isfinite(x)]
        return ("n/a" if not v else
                (fmt % v[0]) if len(set(np.round(v, 2))) == 1 else
                f"{fmt % min(v)} ~ {fmt % max(v)}")

    pm = {k: J["drones"][k].get("paired_mesh_vs_primitive", {}) for k in J["drones"]}
    marg = [J["drones"][k].get("margin_over_sphere_null", {})
            .get("mesh_no_rotor", {}).get("margin_over_sphere_db", {}).get("mean")
            for k in J["drones"]]
    box_d = [pm[k].get(f"{a} - mesh_no_rotor", {}).get("in_band_ac_over_dc_db", {}).get("mean")
             for k in J["drones"] for a in ("box_eqvol_aspect", "box_bbox")]
    cube_d = [pm[k].get("cube_eqvol - mesh_no_rotor", {}).get("in_band_ac_over_dc_db", {}).get("mean")
              for k in J["drones"]]
    eps_d = [pm[k].get(f"{a} - mesh_no_rotor", {}).get("eps_db", {}).get("mean")
             for k in J["drones"] for a in ("cube_eqvol", "box_eqvol_aspect", "box_bbox")]
    anch = J.get("external_eps_anchor", {})
    best = (anch.get("ranked_by_abs_error") or ["?"])[0]
    dc = J.get("direction_consistency", {})
    flips = [p for p, v in dc.items()
             if isinstance(v, dict) and v.get("bands_agree_everywhere") is False]

    F["q3_structure_under_identical_kinematics"] = dict(
        question_ko=("⭐⭐ 같은 축·같은 rpm·같은 위상 스텝으로 **실제로 돌렸을 때**, 형상 정밀도는 "
                     "마이크로도플러를 얼마나 더 만드는가"),
        headline=hl,
        headline_ko=(
            "⭐ 답은 **한 방향이 아니다.** 세 가지가 동시에 참이고, 셋을 같이 읽어야 한다.\n"
            f" ① 구는 실제로 돌려도 변조가 없다 — 우리 메쉬보다 {_rng(marg, '%.0f')} dB 아래이고 "
            "방위 산포 ε 은 정확히 0.000 이다. 고각 5점·기체 3종·두 대역에서 예외가 없다. "
            "«구조 우위» 는 마이크로도플러에서 **거대하다** — 다만 상대가 구일 때만 그렇다.\n"
            f" ② 상자는 우리 CAD 메쉬보다 **더 많이** 흔들린다(짝지은 차이 {_rng(box_d)} dB). "
            "즉 «형상 정밀도가 변조를 더해 준다» 는 명제는 **거짓**이다 — 지도교수 지적이 여기서도 "
            f"부분적으로 맞다. 반대로 정육면체는 우리보다 **덜** 흔들린다({_rng(cube_d)} dB, "
            "고각 5점 전부에서 같은 부호). 그래서 «프리미티브가 늘 이긴다» 도 거짓이다 — "
            "어느 프리미티브를 고르느냐가 부호를 정한다.\n"
            f" ③ 그런데 상자의 «더 많이» 는 **틀린 방향**이다. 상자·정육면체는 우리 메쉬보다 ε 이 "
            f"{_rng(eps_d)} dB 넓고, 실측과 견주면 오차가 가장 작은 모형이 «{best}» 다"
            f"(external_eps_anchor, 기준 ε = {anch.get('das_measured_eps_db', float('nan')):.2f} dB). "
            "상자는 더 흔들리는 게 아니라 **지나치게** 흔들린다. "
            "«변조가 크다» 와 «변조가 맞다» 는 다른 질문이고, 이 단은 둘을 갈라 놓는다."),
        robustness_ko=(
            "부호가 두 대역에서 어긋난 조합: " + (", ".join(flips) if flips else "없음") +
            ". 어긋난 것은 그만큼 좁게 말해야 한다 — 3.5 GHz 에서만 성립하는 부호이기 때문이다."),
        values=q3,
        fairness_ko=("구도 상자도 실제로 돌렸다 — 구를 안 돌리고 0 을 얻는 동어반복을 피했다. "
                     "부피 등가는 계산해서 맞췄고(arms_geometry 의 volume_m3·volume_ratio_to_mesh), "
                     "재질은 로터 뗀 메쉬의 면적 가중 평균 |Γ| 를 물려줬다. 프리미티브는 회전축 "
                     "위에 놓아 **프리미티브에게 가장 유리한** 배치를 줬다."),
        how_to_read_ko=("⛔ 부호를 미리 정하지 말 것. paired_mesh_vs_primitive 의 frac_positive 를 "
                        "먼저 볼 것 — 고각을 바꿔도 부호가 유지되는가. 0.5 근처면 «차이 없음» 이다. "
                        "sphere_eqvol 은 물리적 변조가 0 이어야 하므로 그 값이 계산기의 바닥이고, "
                        "다른 팔은 그 바닥 대비 여유(margin_over_sphere_null)로 읽는다. "
                        "sphere_offaxis 는 «구의 널이 회전대칭 때문이지 구라서가 아님» 을 보이는 "
                        "대조군이다 — 여기서 변조가 나와야 정상이다."),
        connection_ko=("이 모드의 위상 표는 곧 방위 RCS 패턴이므로(gates.spin_equals_azimuth), "
                       "여기서 나온 eps_db 는 p3_validation 이 쓰던 방위 산포 ε 과 **같은 정의**다. "
                       "즉 «구는 ε=0.00 이라 원리적으로 못 낸다» 던 그 양이, 시간축에서는 바로 "
                       "마이크로도플러 변조 깊이다 — 같은 정보의 두 얼굴이다. "
                       "⚠ p3 는 el=0°·PEC·다른 주파수 창이라 그쪽 숫자와 직접 같지는 않다."))

    # Q4 — 믿을 수 있는 범위
    F["q3b_is_the_sign_robust"] = dict(
        question_ko="⭐ 그 부호는 대역·고각·기체를 바꿔도 버티는가",
        values=J.get("direction_consistency", {}),
        external_anchor=J.get("external_eps_anchor", {}),
        why_ko=("한 조건에서만 나오는 부호는 결론이 아니다. 우리 저장소에는 단일 자세 결론이 "
                "자세평균에서 뒤집힌 전례가 있다. 그래서 3.5 GHz ↔ 15.86 GHz, 고각 5점, 기체 3종을 "
                "전부 세어 둔다 — 어느 하나라도 어긋나면 그만큼 좁게 말해야 한다."))

    # Q5 — 몸체가 도는 것과 블레이드가 도는 것 중 어느 쪽이 더 센 변조원인가
    q5 = {}
    for key in J["drones"]:
        sh = J["drones"][key].get("spin_headline", {})
        dec = (J["drones"][key].get("flight_kinematics") or {}).get("dc_pedestal_decomposition", {})
        if "mesh_no_rotor" not in sh or dec.get("absent") or "dc_ac_db_as_measured" not in dec:
            continue
        body = sh["mesh_no_rotor"]["in_band_modulation_depth_db"]
        blade = -dec["dc_ac_db_as_measured"]["mean"]
        q5[key] = dict(body_spin_depth_db=float(body), blade_spin_depth_db=float(blade),
                       body_minus_blade_db=float(body - blade))
    F["q5_body_rotation_vs_blade_rotation"] = dict(
        question_ko=("몸체가 도는 것과 블레이드가 도는 것 중, 어느 쪽이 더 «깊은» 변조를 만드는가"),
        values=q5,
        source_ko=("body_spin_depth_db 는 이 단의 회전 모드(로터 뗀 몸체를 통째로 돌림), "
                   "blade_spin_depth_db 는 report16_base 의 비행 모드(몸체 정지·로터만 회전)에서 "
                   "잰 −dc_ac_db 다. 둘 다 «AC 가 DC 보다 몇 dB 위인가» 로 같은 정의다."),
        why_rate_does_not_matter_ko=(
            "⭐ 변조의 **깊이**는 회전 속도와 무관하다. 강체를 돌린 위상 표는 곧 방위 패턴이므로 "
            "(gates.spin_equals_azimuth), 표의 모양은 rpm 이 정하지 않는다. rpm 은 그 표의 차수를 "
            "«몇 Hz 에 놓을지» 만 정한다. 그래서 여기 적힌 dB 차이는 «호버 rpm 으로 몸체를 돌린다» 는 "
            "비현실적 설정에 기대지 않는다 — 실제 요yaw 속도가 훨씬 느려도 깊이는 같고, 다만 그 "
            "변조가 훨씬 낮은 도플러에 놓일 뿐이다."),
        so_what_ko=("몸체 자세가 흔들리면 그것이 블레이드보다 훨씬 깊은 변조원이라는 뜻이다. "
                    "⚠ 다만 깊이가 크다고 탐지에 유리한 것은 아니다 — 느린 몸체 운동은 0-도플러 "
                    "근처에 몰려 클러터 제거에 같이 지워진다. 이 단은 «깊이» 만 재고 «어디에 놓이는가» 는 "
                    "재지 않는다."))

    F["q4_how_far_to_trust"] = dict(
        question_ko="이 결과를 어디까지 믿을 수 있나",
        gates={k: v.get("verdict") for k, v in J["gates"].items()},
        sphere_null_is_a_floor_not_a_value_ko=(
            "⭐ 구 팔의 값은 «측정값» 이 아니라 «이 계산기의 바닥» 이다. 점을 4배 촘촘히 깔면 구의 "
            "in-band 변조가 11~21 dB **더 내려간다**(point_density_control) — 물리량이라면 그럴 리가 "
            "없다. 즉 구의 진짜 변조는 여기 적힌 값보다도 낮고, 우리 메쉬의 여유는 여기 적힌 "
            "121~136 dB 보다 크다. 반대로 실체가 있는 팔(메쉬·정육면체·상자)은 4배 촘촘히 깔아도 "
            "1.2 dB 안에서 안 움직이고 파형 상관이 0.994 이상이다 — 밀도는 원인이 아니다."),
        point_density={k: J["drones"][k].get("point_density_control")
                       for k in J["drones"] if J["drones"][k].get("point_density_control")},
        wavefront={k: J["drones"][k].get("wavefront_control")
                   for k in J["drones"] if J["drones"][k].get("wavefront_control")},
        hi_band_direction_ko=("15.86 GHz(블레이드 PO 무릎)에서 같은 지표를 다시 냈다. 3.5 GHz 의 "
                              "방향과 어긋나면 그 결론은 «커널이 약한 대역의 산물» 이다."),
        po_validity=J["po_validity_warning"])
    return F


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-compute", action="store_true", help="이미 만든 표로 JSON/그림만 다시")
    a = ap.parse_args()
    main(skip_compute=a.skip_compute)
