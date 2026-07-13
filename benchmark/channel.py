# -*- coding: utf-8 -*-
"""
channel.py — (benchmark) 채널/기하 모델: 바이스태틱 CIR 상태
============================================================
스왑 가능한 두 백엔드가 **같은 ChannelState** 를 돌려준다:
  · AnalyticChannel : 닫힌형 바이스태틱 기하 + PO-RCS.  GPU 불필요 — 어디서나 즉시 실행.
  · SionnaRTChannel : Sionna RT PathSolver 로 **환경 멀티패스(클러터) CIR** 생성.
                      GPU/OptiX 필요 (py312 venv + CUDA_VISIBLE_DEVICES=2 에서 실행).

■ Analytic(개발·기준) vs RT(교차검증) 분업
  · Analytic : 하네스 로직·물리(link_budget)·DSP 개발/검증 + RT 의 closed-form 기준.
  · RT       : 같은 셀을 SionnaRTChannel 로 스왑해 흡수체 챔버 잔향 등 환경효과 실측.
  두 백엔드가 동일 ChannelState 를 주므로 상위 하네스는 **엔진과 무관하게 동일**하다.

■ 설계 원칙 — calibration-robust 하이브리드 (report2 근거)
  RT 의 '작은 드론' 후방산란 RCS 는 표본잡음·글린트로 불안정하고, RT 절대전력 보정도
  까다롭다. 그래서:
    · RT 는 **iso 안테나**로 순수 기하/재질만 → 경로들의 '직접파 대비 진폭비'만 취함(보정 무관).
    · **직접파 절대크기·잡음** = link_budget(EIRP·kTB),  **표적 σ** = PO(검증됨).
    · 클러터 = RT 가 찾아준 (상대지연, 직접파대비 진폭비) → 상위에서 dpi_amp 로 스케일.
  깨끗한 챔버(흡수체)면 RT 클러터가 미미 → RT ≈ Analytic (= 서로 교차검증).
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import numpy as np

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from bistatic_scene import bistatic_params, C0          # noqa: E402  (numpy 전용)
from rcs_po import mesh_to_points, rcs_from_points       # noqa: E402
from drones import DRONES, build_drone                   # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_CMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "chamber"))
_DMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "drones"))

# 드론 점구름 캐시 (mesh_to_points 는 비싸므로 (드론,반송파)당 1회만) ---------------
_PTS_CACHE: dict = {}


def _drone_points(drone_key, fc):
    lam = C0 / fc
    spacing = lam / 7.0                                   # rcs_po 기본값과 동일(정확도/속도)
    key = (drone_key, round(fc / 1e6))
    if key not in _PTS_CACHE:
        mesh = build_drone(DRONES[drone_key])
        _PTS_CACHE[key] = mesh_to_points(mesh, spacing)
    return _PTS_CACHE[key]


def bistatic_rcs_m2(drone_key, fc, u1, u2, az_span_deg=8.0, n_az=5):
    """바이스태틱 RCS ≈ **이등분선 방향의 모노스태틱 RCS**(바이스태틱 등가정리).
    û_look = (u1+u2)/|u1+u2| = 표적→'등가 레이더' 방향 (u1=표적→TX, u2=표적→RX).

    **자세 소구간 평균**(공정성): 단일-자세 PO-RCS 는 글린트로 값이 심하게 출렁여
    (스냅샷마다 수 dB) SCR·Pd 를 자세운(luck)에 좌우시킨다. 그래서 시선 방위 ±az_span/2
    를 n_az 점으로 평균한 **기대 RCS**(선형 m² 평균)를 쓴다 → 궤적 따라 부드럽고 공정.
    az_span_deg=0 또는 n_az=1 이면 단일-자세(예전 동작).
    주의(단순화): 드론 yaw=0(몸체 x축 = world x) 가정. β→180°(순 전방산란)이면 u1 대체."""
    b = np.asarray(u1) + np.asarray(u2)
    n = np.linalg.norm(b)
    look = (b / n) if n > 1e-9 else np.asarray(u1)
    az = float(np.degrees(np.arctan2(look[1], look[0])))
    el = float(np.degrees(np.arcsin(np.clip(look[2], -1.0, 1.0))))
    if n_az > 1 and az_span_deg > 0:
        az_list = az + np.linspace(-az_span_deg / 2, az_span_deg / 2, int(n_az))
    else:
        az_list = [az]
    P, N, dA = _drone_points(drone_key, fc)
    sig = rcs_from_points(P, N, dA, fc, az_deg=az_list, el_deg=el)   # (n_az,) σ[m²]
    return float(np.mean(sig))                                       # 선형 평균 = 기대 RCS


@dataclass
class ChannelState:
    """한 스냅샷(위치·속도)에서의 바이스태틱 채널 상태(엔진 독립 표현).

    clutter/rt_echo_ratio 는 **직접파 대비 진폭비**(절대 보정 무관)로 표현한다.
    상위 하네스가 link_budget 의 dpi_amp(직접파 절대크기)로 스케일한다."""
    tau: float               # 표적 에코 상대지연 [s] (바이스태틱, 직접파 기준)
    fd: float                # 표적 도플러 [Hz]
    R1: float                # TX→표적 [m]
    R2: float                # 표적→RX [m]
    L: float                 # 베이스라인 |TX−RX| [m]
    beta: float              # 바이스태틱 각 [deg]
    sigma_m2: float          # 표적 RCS [m²] (PO, 반송파·자세 반영)
    lam: float               # 파장 [m]
    clutter: tuple = ()      # ((상대지연[s], 직접파대비 진폭비), …) 정적(0-도플러) 반사체
    rt_echo_ratio: float | None = None   # RT 표적에코/직접파 진폭비(‘rt’ 표적모드용). Analytic=None
    backend: str = "analytic"


class AnalyticChannel:
    """닫힌형 바이스태틱 기하 + PO-RCS.
    '깨끗한(챔버형) 통제 환경' 사양에 정확히 부합:
    직접파 + 표적 바이스태틱 에코 + kTB 잡음(상위에서 부가), 클러터 없음(clean).
    GPU/OptiX 불필요, GT 정확·무료. RT 백엔드의 closed-form 교차검증 기준으로도 쓴다."""
    kind = "analytic"

    def __init__(self, clutter=(), rcs_az_span_deg=8.0, rcs_n_az=5):
        self._clutter = tuple(clutter)      # 원하면 간단한 정적 클러터 모델 주입 가능
        self._az_span = rcs_az_span_deg     # RCS 자세 소구간 평균(글린트 완화·공정성)
        self._n_az = rcs_n_az

    def state(self, tx, rx, tgt, vel, fc, drone_key) -> ChannelState:
        p = bistatic_params(tx, rx, tgt, vel, fc)
        sigma = bistatic_rcs_m2(drone_key, fc, p["u1"], p["u2"],
                                az_span_deg=self._az_span, n_az=self._n_az)
        return ChannelState(tau=p["tau"], fd=p["fd"], R1=p["R1"], R2=p["R2"],
                            L=p["L"], beta=p["beta"], sigma_m2=sigma, lam=p["lam"],
                            clutter=self._clutter, rt_echo_ratio=None, backend="analytic")


class SionnaRTChannel:
    """Sionna RT PathSolver 로 **환경 멀티패스 CIR** 추출 (GPU·OptiX 필요).

    빠른 개발·대규모 스윕은 AnalyticChannel 로, 환경효과 검증은 이 백엔드로 스왑한다.

    [무엇을 RT 로 뽑나]  iso 안테나(순수 기하/재질)로 광선추적 → 경로 3분류:
        · 직접파 : 상호작용 0 (LOS) → 지연·진폭 참조 기준(dpi 는 link_budget 이 절대화).
        · 표적에코: 표적 근방 상호작용 → RT 진폭비(‘rt’ 모드) 또는 PO(‘po’ 모드, 권장).
        · 클러터 : 그 외 상호작용(벽 등) → (상대지연, 직접파대비 진폭비).
    [무엇을 link_budget/PO 로 절대화]  직접파 크기·잡음(EIRP·kTB), 표적 σ(PO).
      → RT 절대전력 보정에 의존하지 않는다(모두 직접파 대비 '비율'로 참조).

    [실행]  radar_scene.py 의 검증된 solve_paths/paths_arrays 를 재사용한다.
        CUDA_VISIBLE_DEVICES=2 /home/yunjung/.venvs/py312/bin/python -c "from channel import SionnaRTChannel; ..."
      (scene_build 가 mitsuba import 전에 GPU 2번을 setdefault 로 지정한다)
    """
    kind = "sionna_rt"

    def __init__(self, with_chamber=False, target_amp="po", max_depth=3,
                 spp=1_000_000, echo_radius=2.0, cutaway=False,
                 min_clutter_ratio=1e-3, max_clutter=8,
                 rcs_az_span_deg=8.0, rcs_n_az=5):
        # with_chamber : 기본 False(자유공간·깨끗한 교차검증). **이제 벤치마크 기하는 챔버
        #   스케일**(geometry.py: TX/RX 30m 챔버 벽)이라 with_chamber=True 로 실제 흡수체
        #   챔버 안 멀티패스(약한 잔향 클러터)를 RT 로 뽑을 수 있다. 자유공간이면 클러터≈0
        #   → RT ≈ Analytic (기하 교차검증). 챔버면 RT 가 약한 잔향 클러터를 실측.
        self.with_chamber = with_chamber
        self.target_amp = target_amp          # 'po'(권장, 하이브리드) | 'rt'(RT 산란비 사용)
        self.max_depth = max_depth
        self.spp = spp
        self.echo_radius = echo_radius        # 표적 근방 판정 반경 [m]
        self.cutaway = cutaway
        self.min_clutter_ratio = min_clutter_ratio
        self.max_clutter = max_clutter
        self.rcs_az_span_deg = rcs_az_span_deg   # RCS 자세평균(Analytic 과 동일 규약)
        self.rcs_n_az = rcs_n_az

    @staticmethod
    def _require():
        try:
            import mitsuba  # noqa: F401
            import sionna.rt  # noqa: F401
        except Exception as e:
            raise RuntimeError(
                "SionnaRTChannel 은 Sionna RT(mitsuba/drjit) + GPU/OptiX 가 필요합니다.\n"
                "  · py312 venv + CUDA_VISIBLE_DEVICES=2 에서 실행하세요.\n"
                "  · OptiX 로딩 실패(libnvoptix.so.1) 시 NVIDIA_DRIVER_CAPABILITIES=all 또는\n"
                "    DRJIT_LIBOPTIX_PATH 지정으로 해결합니다(benchmark/README 참고).\n"
                f"(원인: {type(e).__name__}: {e})")

    def state(self, tx, rx, tgt, vel, fc, drone_key) -> ChannelState:
        self._require()
        # scene_build 를 먼저 import — CUDA_VISIBLE_DEVICES(GPU 2번) setdefault 가
        # mitsuba/sionna 의 CUDA 초기화보다 앞서 실행되도록 순서 보장.
        from scene_build import build_scene, chamber_parts, drone_parts
        import mitsuba as mi
        import sionna.rt as rt
        # radar_scene 의 검증된 도구 재사용(모노 → 바이스태틱은 Tx/Rx 분리만 다름)
        from radar_scene import solve_paths, paths_arrays

        # 1) 바이스태틱 장면: (선택)챔버 + 표적 드론(실제 world 위치)
        parts = []
        if self.with_chamber:
            cparts, _info = chamber_parts(_CMESH, cutaway=self.cutaway)
            parts += cparts
        dp, _mesh = drone_parts(DRONES[drone_key],
                                position=tuple(float(v) for v in tgt),
                                yaw_deg=0.0, mesh_dir=os.path.join(_DMESH, drone_key))
        parts += dp
        scene = build_scene(parts, fc=fc)

        # 2) 조명원 Tx / 감시 Rx 분리 배치. **iso 패턴**(순수 기하/재질 → 진폭비만 취함).
        scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
        scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
        T = rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in tx]))
        R = rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx]))
        scene.add(T); scene.add(R)

        # 3) 광선추적 → 경로 (직접파 LOS + 벽 반사 + 표적 산란)
        paths = solve_paths(scene, spp=self.spp, max_depth=self.max_depth)
        a, tau, dop, V, inter = paths_arrays(paths)      # a:복소이득, tau:지연[s], V:정점, inter:상호작용
        a = np.asarray(a); tau = np.asarray(tau)

        # 4) 경로 3분류: 직접파(무상호작용) / 표적에코(표적근방) / 클러터(그외 상호작용)
        tgtp = np.asarray(tgt, float)
        depth, Pn = inter.shape
        any_inter = np.zeros(Pn, bool)
        near_tgt = np.zeros(Pn, bool)
        for d in range(depth):
            present = inter[d] != 0
            any_inter |= present
            dist = np.linalg.norm(V[d] - tgtp, axis=-1)
            near_tgt |= present & (dist < self.echo_radius)
        is_direct = ~any_inter
        is_echo = near_tgt
        is_clut = any_inter & ~near_tgt

        # 5) 직접파(참조 기준): 절대크기는 link_budget 이 담당 → 여기선 지연·복소합만.
        a_dir = complex(np.sum(a[is_direct])) if is_direct.any() else complex(np.sum(a))
        tau_dir = float(np.min(tau[is_direct])) if is_direct.any() else float(np.min(tau))
        A_dir = abs(a_dir) + 1e-30

        # 6) 표적 σ: PO(권장). RT 진폭비도 함께 계산해 리포트/‘rt’모드에 제공.
        p = bistatic_params(tx, rx, tgt, vel, fc)
        sigma = bistatic_rcs_m2(drone_key, fc, p["u1"], p["u2"],
                                az_span_deg=self.rcs_az_span_deg, n_az=self.rcs_n_az)
        a_echo = complex(np.sum(a[is_echo])) if is_echo.any() else 0.0 + 0j
        rt_echo_ratio = float(abs(a_echo) / A_dir) if is_echo.any() else None

        # 7) 클러터: RT 상대(지연, 직접파대비 진폭비). dtau>0(직접파 이후)만, 강한 순 상위 N개.
        clut = []
        for i in np.where(is_clut)[0]:
            dtau = float(tau[i] - tau_dir)
            rel = float(abs(a[i]) / A_dir)
            if dtau > 0 and rel > self.min_clutter_ratio:
                clut.append((dtau, rel))
        clut = tuple(sorted(clut, key=lambda c: -c[1])[:self.max_clutter])

        return ChannelState(tau=p["tau"], fd=p["fd"], R1=p["R1"], R2=p["R2"], L=p["L"],
                            beta=p["beta"], sigma_m2=sigma, lam=p["lam"],
                            clutter=clut, rt_echo_ratio=rt_echo_ratio, backend="sionna_rt")


def get_channel(kind="analytic", **kw):
    """'analytic' | 'sionna_rt' → 채널 백엔드 인스턴스."""
    if kind == "analytic":
        keep = ("clutter", "rcs_az_span_deg", "rcs_n_az")
        return AnalyticChannel(**{k: v for k, v in kw.items() if k in keep})
    if kind == "sionna_rt":
        return SionnaRTChannel(**kw)
    raise ValueError(f"unknown channel kind: {kind}")


if __name__ == "__main__":
    from geometry import TX, RX, CENTER
    ch = AnalyticChannel()
    print(f"챔버 배치  TX={TX} RX={RX}  center={CENTER}  (RCS 자세평균 on)")
    for drone in ("mini5pro", "mavic4pro", "s1000plus"):
        for fc in (1.843e9, 3.5e9):
            st = ch.state(TX, RX, CENTER, (-3, 2, 0.5), fc, drone)
            print(f"{drone:10s} @{fc/1e9:.2f}GHz  σ={10*np.log10(st.sigma_m2):6.1f}dBsm  "
                  f"Rb={st.tau*C0:6.1f}m  fd={st.fd:+7.1f}Hz  β={st.beta:.0f}°  "
                  f"clutter={len(st.clutter)}  backend={st.backend}")
