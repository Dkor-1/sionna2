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

■ 설계 원칙 — calibration-robust 하이브리드 (근거: docs/VERIFY_RT_VS_PO.md · benchmark/verify_rt_no_rcs.py)
  Sionna RT 의 기본 path solver 에는 산란적분(PO) 단계가 없어 표적 σ 가 창발하지 않는다:
  표적에서 나오는 경로는 정반사(image-source = 무한거울, σ 와 무관: 평판 변 0.2→4 m 로 σ 를
  52 dB 바꿔도 진폭비 −7.91 dB 불변)와 확산(산란계수 S 의 함수, σ 의 함수가 아님)뿐이다.
  (RT 자체가 원리적으로 불가능한 게 아니라 — SBR=GO+PO 는 RCS 를 계산한다 — Sionna RT 의
   전파용 path solver 에 그 단계가 없다는 좁은 명제다.) RT 절대전력 보정도 까다롭다. 그래서:
    · RT 는 **iso 안테나**로 순수 기하/재질만 → 경로들의 '직접파 대비 진폭비'만 취함(보정 무관).
    · **직접파 절대크기·잡음** = link_budget(EIRP·kTB),  **표적 σ** = PO(해석해 대조 검증:
      볼록 PEC ±0.015 dB; 드론 절대값은 실측 앵커링 전까지 미확정).
    · 클러터 = RT 가 찾아준 (상대지연, 직접파대비 진폭비) → 상위에서 dpi_amp 로 스케일.
  깨끗한 챔버(흡수체)면 RT 클러터가 미미 → RT ≈ Analytic (= 서로 교차검증).
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
import sys
from dataclasses import dataclass

import numpy as np

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from bistatic_scene import bistatic_params, C0          # noqa: E402  (numpy 전용)
from rcs_po import mesh_to_points, rcs_from_points       # noqa: E402  (engine="po" 비교용)
from drones import DRONES, build_drone, drone_gamma_map, DRONE_GROUP_MAT  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_CMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "chamber"))
_DMESH = os.path.abspath(os.path.join(_HERE, "..", "assets", "meshes", "drones"))
_OUT = os.path.abspath(os.path.join(_HERE, "..", "outputs"))

# =========================================================================== #
#  표적 σ — **SBR (Mitsuba 광선 + PO 적분, 가림 포함)** 이 기본 엔진이다
# =========================================================================== #
#  2026-07-14. 여기가 report5 의 마지막 구멍이었다: polar/bands(report2) 는 이미 SBR 인데
#  벤치마크의 σ 만 순수 PO(rcs_po.rcs_from_points, **가림 없음**)를 써서 드론 RCS 를
#  **+4~5 dB 과대평가**하고 있었다(mavic4pro el=15° 방위평균: PO −16.8 → SBR −22.1 dBsm).
#  σ 는 링크버짓에 그대로 곱해지므로 이 과대평가가 **에코 SNR → SCR → Pd 전체**에 실려 있었다.
#
#  ■ 왜 캐시가 필요한가 — SBR 은 GPU(Mitsuba/OptiX)를 쓴다
#    run_matrix 는 셀들을 ProcessPoolExecutor 워커로 뿌린다. 워커마다 CUDA 컨텍스트를 새로
#    만들면 (a) GPU 메모리가 워커 수만큼 곱해지고 (b) fork 된 프로세스에서 CUDA 초기화가
#    깨질 수 있다. 그래서 **메인 프로세스에서 필요한 시선각을 전부 모아 SBR 로 한 번에 계산해
#    디스크 캐시(outputs/sigma_sbr_cache.json)** 에 넣고, 워커는 **표를 조회만** 한다.
#    → sbr_sigma_prefill(requests) 가 그 일을 하고, 여러 GPU 에 분배한다(gpu.parallel_over_gpus).
#    워커에는 SIONNA2_NO_GPU=1 을 걸어, 캐시 미스가 나면 조용히 PO 로 흘러가는 대신
#    **큰 소리로 실패**하게 한다(잘못된 σ 로 매트릭스를 채우느니 멈추는 게 낫다).
SIGMA_CACHE = os.path.join(_OUT, "sigma_sbr_cache.json")
RCS_ENGINE = os.environ.get("SIONNA2_BENCH_RCS", "sbr")   # "sbr"(기본) | "po"(비교용)

_SIG: dict | None = None          # 디스크 캐시 (문자열키 → σ[m²])
_SIG_DIRTY = False


@functools.lru_cache(maxsize=None)
def _mesh_fp(drone_key: str) -> str:
    """드론 메쉬 **지문**(8 hex). σ 캐시 키에 넣어 **메쉬가 바뀌면 캐시가 저절로 무효화**되게 한다.
    ⚠ 없으면 (드론,fc,az,el) 만으로 키가 잡혀, CAD 를 고쳐도 옛 σ 를 조용히 재사용한다 —
      링크버짓·SCR·Pd 가 전부 옛 형상 위에서 계산되는 사고가 된다."""
    v = np.asarray(build_drone(DRONES[drone_key]).v, float)
    h = hashlib.md5(np.round(v, 6).tobytes())
    h.update(str(v.shape).encode())
    return h.hexdigest()[:8]


def _sig_key(drone_key, fc, az, el):
    """캐시 키 — 각도는 밀리도(1e-3°)로 반올림해 부동소수 재현성 확보.
    메쉬 지문을 포함한다(위 _mesh_fp 참고)."""
    return (f"{drone_key}@{_mesh_fp(drone_key)}|{round(fc/1e6, 3)}"
            f"|{round(float(az)*1000):d}|{round(float(el)*1000):d}")


def _sig_load():
    global _SIG
    if _SIG is None:
        try:
            with open(SIGMA_CACHE) as f:
                _SIG = json.load(f)
        except Exception:
            _SIG = {}
    return _SIG


def sigma_cache_save():
    """메모리 캐시를 디스크에 쓴다 (프리필/메인 프로세스에서만 호출)."""
    global _SIG_DIRTY
    if _SIG is None or not _SIG_DIRTY:
        return
    os.makedirs(_OUT, exist_ok=True)
    tmp = SIGMA_CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(_SIG, f)
    os.replace(tmp, SIGMA_CACHE)
    _SIG_DIRTY = False


def look_angles(u1, u2, az_span_deg=8.0, n_az=5):
    """시선(이등분선) → (az_list[deg], el[deg]). σ 조회·프리필의 **단일 진리원**.
    û_look = (u1+u2)/|u1+u2| = 표적→'등가 모노스태틱 레이더' 방향(바이스태틱 등가정리)."""
    b = np.asarray(u1, float) + np.asarray(u2, float)
    n = float(np.linalg.norm(b))
    look = (b / n) if n > 1e-9 else np.asarray(u1, float)
    az = float(np.degrees(np.arctan2(look[1], look[0])))
    el = float(np.degrees(np.arcsin(np.clip(look[2], -1.0, 1.0))))
    if n_az > 1 and az_span_deg > 0:
        az_list = az + np.linspace(-az_span_deg / 2, az_span_deg / 2, int(n_az))
    else:
        az_list = np.array([az])
    return np.asarray(az_list, float), el


def _group_mat(drone_key):
    """드론 그룹 → 재질키 (materials.py 단일 진리원; Sionna 와 같은 표)."""
    return {g: mat for g, (mat, _) in DRONE_GROUP_MAT.items()}


def _sbr_sigma(drone_key, fc, az_list, el):
    """캐시 조회 → 미스는 SBR 로 계산(메인 프로세스에서만). 반환 σ 배열."""
    global _SIG_DIRTY
    cache = _sig_load()
    keys = [_sig_key(drone_key, fc, a, el) for a in az_list]
    miss = [i for i, k in enumerate(keys) if k not in cache]
    if miss:
        if os.environ.get("SIONNA2_NO_GPU"):
            raise RuntimeError(
                f"σ 캐시 미스 ({drone_key} @{fc/1e9:.3f}GHz, el={el:.3f}°, {len(miss)}개) — "
                "워커에서는 SBR(GPU)을 돌리지 않는다. 메인 프로세스에서 "
                "channel.sbr_sigma_prefill() 로 먼저 캐시를 채우세요.")
        from rcs_sbr import rcs_sbr_batch                       # GPU (mitsuba) — 지연 import
        mesh = build_drone(DRONES[drone_key])
        s = np.atleast_1d(rcs_sbr_batch(mesh, _group_mat(drone_key), fc,
                                        az_deg=np.asarray(az_list, float)[miss], el_deg=el,
                                        cache_key=(drone_key, round(fc / 1e6))))
        for i, v in zip(miss, s):
            cache[keys[i]] = float(v)
        _SIG_DIRTY = True
        sigma_cache_save()
    return np.array([cache[k] for k in keys], float)


# --- 프리필: 필요한 시선각을 모아 SBR 로 한 번에 (여러 GPU 분배) --------------------
def _prefill_worker(gpu_index, items):
    """gpu.parallel_over_gpus 워커 — **반드시 모듈 최상위 함수**.
    items: [(drone_key, fc, el, (az…)), …] → [σ 배열, …]"""
    os.environ["SIONNA2_GPU"] = str(gpu_index)               # mitsuba import 전에 고정
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_index)
    os.environ.pop("SIONNA2_NO_GPU", None)
    # ⚠ src/gpu.py 버그 우회 — pick() 은 CUDA_VISIBLE_DEVICES 가 이미 있으면 조기 반환하며
    #   _BUDGET_MB 를 계산하지 않는다. 그러면 budget_mb() 가 정의되지 않은 이름
    #   DEFAULT_TARGET_MB 를 참조해 NameError 로 죽는다(rcs_sbr_batch 가 budget_mb 를 쓴다).
    #   공유모듈이라 고치지 않고 여기서 예산만 직접 채운다(보고 사항).
    import gpu as _g
    free = next((g["free_mb"] for g in _g.gpu_status() if g["index"] == int(gpu_index)), 8000)
    _g._PICKED, _g._BUDGET_MB = str(gpu_index), _g._compute_budget(free)
    from rcs_sbr import rcs_sbr_batch
    out = []
    for drone_key, fc, el, az in items:
        mesh = build_drone(DRONES[drone_key])
        s = rcs_sbr_batch(mesh, _group_mat(drone_key), fc, az_deg=np.asarray(az, float),
                          el_deg=float(el), cache_key=(drone_key, round(fc / 1e6)))
        out.append(np.atleast_1d(s).astype(float).tolist())
    return out


def sbr_sigma_prefill(requests, verbose=True):
    """requests: [(drone_key, fc, u1, u2, az_span_deg, n_az), …]
    → 필요한 (드론, fc, el) 그룹별로 방위각을 모아 **SBR 을 GPU 들에 분배**해 캐시를 채운다.
    ⚠ mitsuba 를 import 하기 **전에**(=메인 프로세스가 CUDA 컨텍스트를 만들기 전에) 부를 것."""
    global _SIG_DIRTY
    cache = _sig_load()
    need: dict = {}
    for drone_key, fc, u1, u2, span, n_az in requests:
        az_list, el = look_angles(u1, u2, span, n_az)
        for a in az_list:
            k = _sig_key(drone_key, fc, a, el)
            if k not in cache:
                need.setdefault((drone_key, float(fc), round(el, 3)), set()).add(round(float(a), 3))
    if not need:
        if verbose:
            print(f"[σ] SBR 캐시 적중 — 새로 계산할 시선각 없음 ({len(cache)}개 저장됨)")
        return 0
    items = [(d, fc, el, tuple(sorted(azs))) for (d, fc, el), azs in need.items()]
    n_new = sum(len(it[3]) for it in items)
    if verbose:
        print(f"[σ] SBR 프리필 — {len(items)} 그룹 / {n_new} 시선각 (가림 포함, GPU)")
    from gpu import parallel_over_gpus
    res = parallel_over_gpus(items, _prefill_worker, verbose=verbose)
    for (drone_key, fc, el, azs), sig in zip(items, res):
        for a, s in zip(azs, np.atleast_1d(sig)):
            cache[_sig_key(drone_key, fc, a, el)] = float(s)
    _SIG_DIRTY = True
    sigma_cache_save()
    if verbose:
        print(f"[σ] 캐시 저장 → {os.path.relpath(SIGMA_CACHE, os.path.join(_HERE, '..'))} "
              f"({len(cache)}개)")
    return n_new


# --- 옛 순수 PO (engine="po") — **비교용으로만** 남긴다 -----------------------------
_PTS_CACHE: dict = {}


def _drone_points(drone_key, fc):
    lam = C0 / fc
    spacing = lam / 7.0
    key = (drone_key, round(fc / 1e6))
    if key not in _PTS_CACHE:
        mesh = build_drone(DRONES[drone_key])
        _PTS_CACHE[key] = mesh_to_points(mesh, spacing,
                                          gamma=drone_gamma_map(DRONES[drone_key]))
    return _PTS_CACHE[key]


def bistatic_rcs_m2(drone_key, fc, u1, u2, az_span_deg=8.0, n_az=5, engine=None):
    """바이스태틱 RCS ≈ **이등분선 방향의 모노스태틱 RCS**(바이스태틱 등가정리).

      engine="sbr" (기본) : Mitsuba 광선 + PO 표면적분. **가림 포함**. 캐시/GPU.
      engine="po"         : 옛 점구름 PO. **가림 없음** → +4~5 dB 과대. 비교용.

    **자세 소구간 평균**(공정성): 단일-자세 RCS 는 글린트로 값이 심하게 출렁여(스냅샷마다 수 dB)
    SCR·Pd 를 자세운(luck)에 좌우시킨다. 그래서 시선 방위 ±az_span/2 를 n_az 점으로 평균한
    **기대 RCS**(선형 m² 평균)를 쓴다. az_span_deg=0 또는 n_az=1 이면 단일-자세.
    주의(단순화): 드론 yaw=0(몸체 x축 = world x) 가정. β→180°(순 전방산란)이면 u1 대체."""
    az_list, el = look_angles(u1, u2, az_span_deg, n_az)
    eng = engine or RCS_ENGINE
    if eng == "sbr":
        sig = _sbr_sigma(drone_key, fc, az_list, el)
    else:
        P, N, dA, w = _drone_points(drone_key, fc)
        sig = rcs_from_points(P, N, dA, fc, az_deg=az_list, el_deg=el, w=w)
    return float(np.mean(sig))                                # 선형 평균 = 기대 RCS


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
    """닫힌형 바이스태틱 기하 + **SBR-RCS**(가림 포함) + (선택)정적 클러터.

    이름은 'Analytic' 이지만 **σ 는 더 이상 해석식이 아니다** — Mitsuba 광선이 실제로 맞은
    면들 위의 PO 적분(SBR)이다(캐시 조회). 여기서 'analytic' 은 **환경 경로**(직접파·표적
    에코의 지연/도플러/확산손실)를 닫힌형 기하로 푼다는 뜻이다. 그 환경 경로마저 RT 로
    바꾸고 싶으면 SionnaRTChannel, 또는 rt_chamber_clutter() 로 RT 실측 잔향을 주입한다."""
    kind = "analytic"

    def __init__(self, clutter=(), rcs_az_span_deg=8.0, rcs_n_az=5, rcs_engine=None):
        self._clutter = tuple(clutter)      # 정적 클러터 (RT 실측 or 가정) — 진폭비
        self._az_span = rcs_az_span_deg     # RCS 자세 소구간 평균(글린트 완화·공정성)
        self._n_az = rcs_n_az
        self._engine = rcs_engine           # None=SBR(기본), "po"=옛 엔진(비교용)

    def state(self, tx, rx, tgt, vel, fc, drone_key) -> ChannelState:
        p = bistatic_params(tx, rx, tgt, vel, fc)
        sigma = bistatic_rcs_m2(drone_key, fc, p["u1"], p["u2"],
                                az_span_deg=self._az_span, n_az=self._n_az,
                                engine=self._engine)
        return ChannelState(tau=p["tau"], fd=p["fd"], R1=p["R1"], R2=p["R2"],
                            L=p["L"], beta=p["beta"], sigma_m2=sigma, lam=p["lam"],
                            clutter=self._clutter, rt_echo_ratio=None, backend="analytic")


# --------------------------------------------------------------------------- #
#  RT 실측 챔버 잔향 캐시 — 환경(경로)은 RT, σ 는 SBR (하이브리드)
# --------------------------------------------------------------------------- #
#  정적 클러터는 이 하네스에서 **죽은 파라미터**다(ECA 사영 + 0-도플러 행 마스킹으로 삼중
#  차단; docs/VERIFY_CLUTTER.md). 그래도 **가정치(CH_CLUTTER_RATIO)를 RT 실측으로 바꾸는
#  것은 정직함의 문제**다 — 수치는 한 자리도 안 바뀌지만, 더 이상 "우리가 클러터를 가정했다"
#  고 말하지 않아도 된다. 비싼 RT 를 셀마다 돌리지 않도록 반송파별로 한 번 뽑아 캐시한다.
RT_CLUTTER_CACHE = os.path.join(_OUT, "rt_env_clutter.json")
_RTC: dict | None = None


def rt_chamber_clutter(fc, tx=None, rx=None, tgt=None, drone_key="mavic4pro",
                       spp=1_000_000, compute=False, verbose=True):
    """반송파 fc 의 **RT 실측 챔버 잔향** ((상대지연[s], 직접파대비 진폭비), …).
    캐시에 없고 compute=True 면 SionnaRTChannel(GPU)로 뽑아 캐시에 저장한다.
    캐시에 없고 compute=False 면 () — 호출자가 가정치로 폴백할 수 있다."""
    global _RTC
    if _RTC is None:
        try:
            with open(RT_CLUTTER_CACHE) as f:
                _RTC = json.load(f)
        except Exception:
            _RTC = {}
    key = f"{round(fc/1e6, 3)}"
    if key in _RTC:
        return tuple((float(dt), float(r)) for dt, r in _RTC[key])
    if not compute:
        return ()
    from geometry import TX, RX, CENTER
    st = SionnaRTChannel(with_chamber=True, spp=spp).state(
        tx if tx is not None else TX, rx if rx is not None else RX,
        tgt if tgt is not None else CENTER, (0.0, 0.0, 0.0), fc, drone_key)
    _RTC[key] = [[float(dt), float(r)] for dt, r in st.clutter]
    os.makedirs(_OUT, exist_ok=True)
    with open(RT_CLUTTER_CACHE, "w") as f:
        json.dump(_RTC, f, indent=1)
    if verbose:
        print(f"[RT] {fc/1e9:.3f} GHz 챔버 잔향 {len(st.clutter)}개 실측 → 캐시 "
              f"({', '.join(f'{dt*1e9:.1f}ns/{20*np.log10(r):+.1f}dB' for dt, r in st.clutter[:4])})")
    return tuple(st.clutter)


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
        # 'po'(권장, 하이브리드) | 'rt'(진단용 only — RT 표적경로는 절대진폭 소스로 쓰면 안 된다,
        #                              docs/VERIFY_RT_VS_PO.md §6 유효조건 2)
        self.target_amp = target_amp
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
        keep = ("clutter", "rcs_az_span_deg", "rcs_n_az", "rcs_engine")
        return AnalyticChannel(**{k: v for k, v in kw.items() if k in keep})
    if kind == "sionna_rt":
        return SionnaRTChannel(**kw)
    raise ValueError(f"unknown channel kind: {kind}")


if __name__ == "__main__":
    from geometry import TX, RX, CENTER
    print(f"챔버 배치  TX={TX} RX={RX}  center={CENTER}  (RCS 자세평균 on)")
    print(f"{'드론':10s} {'fc':>8s} {'σ_SBR':>9s} {'σ_PO':>9s} {'가림효과':>9s}   기하")
    sbr, po = AnalyticChannel(), AnalyticChannel(rcs_engine="po")
    for drone in ("mini5pro", "mavic4pro", "s1000plus"):
        for fc in (1.843e9, 3.5e9):
            s = sbr.state(TX, RX, CENTER, (-3, 2, 0.5), fc, drone)
            p = po.state(TX, RX, CENTER, (-3, 2, 0.5), fc, drone)
            d = 10 * np.log10(s.sigma_m2 / p.sigma_m2)
            print(f"{drone:10s} {fc/1e9:6.2f}GHz {10*np.log10(s.sigma_m2):+8.1f} "
                  f"{10*np.log10(p.sigma_m2):+8.1f} {d:+8.1f}dB   "
                  f"Rb={s.tau*C0:5.1f}m fd={s.fd:+6.1f}Hz β={s.beta:.0f}°")
