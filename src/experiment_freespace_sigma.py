# -*- coding: utf-8 -*-
"""
experiment_freespace_sigma.py — (report13) 자유공간 드론 **σ 격자 생산자** (docs/REPORT13_SPEC §6, §9)
=========================================================================================================
report13 만 챔버를 벗어나 **자유공간(FS-1)** 에서 "이 드론이 몇 m 까지 보이나"를 묻는다. 그 답의
입력이 되는 것이 여기서 만드는 **RCS σ 격자**다. 이 파일은 σ 만 생산해 `outputs/report13_sigma_grid.json`
에 쓴다 — 링크버짓/검출은 `experiment_freespace_range.py` 소관이다.

■ 무엇이 report2 와 같고 무엇이 다른가
  같다 : SBR 엔진(`rcs_sbr.rcs_sbr_batch`, penetrate=True·jitter=2), div, 대역평균(n_f), 3° 각도평활.
  다르다 : **el 이 음수**다(★spec §6.1/S8). report2 는 el=+15°(지상에서 드론을 올려다보는 각)로
           **드론 등짝(top)** 을 봤지만, 자유공간 바이스태틱의 이등분선 앙각은 전 구간 **음수**라
           우리는 드론 **배(belly)** 를 본다(`freespace_scene.look_el_deg` 가 항상 음수). 그래서
           el 격자를 [0,−0.5,−1,−2,−3.5,−5,−8,−12,−20]° 로 **유효도메인에 조밀 배치**한다.

■ ⚠ 재사용 규약과 그 한계(정직 표기 — 스펙 §6.1/§9 두 mandate 가 충돌한다)
  · 스펙 §9 : "새 워커 금지" — ProcessPool 워커를 새로 만들지 말고 `channel._prefill_worker` 재사용.
  · 스펙 §6.1: "engine = rcs_sbr_batch(div=16)" **그리고** "channel.sbr_sigma_prefill 재사용".
  그런데 `channel._prefill_worker` 는 `rcs_sbr_batch` 를 **spacing 인자 없이** 부르므로 항상
  `DEFAULT_DIV(=12)` 로 계산한다 — div=16 을 새 워커 없이 얻으려면 두 길뿐이다:
    (a) `backend="prefill"` : `sbr_sigma_prefill` 재사용(멀티 GPU·budget NameError 우회 내장).
        div=16 은 **전역상수 속성교체**(절대규칙 1)로: `rcs_sbr.DEFAULT_DIV=16` 를 프리필 **전에**
        세팅하면 Linux fork 로 워커가 상속한다. ★프리필은 `gpu.all_usable()` 로 여유 GPU **전부**
        (0~3)에 뿌린다 — `SIONNA2_GPU` 를 존중하지 않으므로 GPU 를 제한해야 하는 상황에선 쓰지 말 것.
    (b) `backend="direct"`(스모크·GPU 제한용) : 메인 프로세스에서 `rcs_sbr_batch(spacing=λ/div)` 를
        **직접** 부른다(스펙 §6.1 이 이름으로 지정한 바로 그 호출). div 을 정확히 주므로 report2 와
        비트단위로 같은 엔진이고, `gpu.pick()`(SIONNA2_GPU 존중)이 잡은 **한 장**만 쓴다.
  두 backend 모두 **다중반사 금지**(스펙 §9): `rcs_sbr(...,max_bounce≥2)` 를 쓰지 않고 1-bounce 배치만.

■ σ 인용 정책(스펙 §6.5, 승계): 백분위(p10/p50/p90)·커버리지만. 널최소값·σ_min·aspect-peak·
  절대점값·단일 "검지거리 N m" 금지. m² 선형평균(dB 평균 아님 — Jensen 낙관).

실행(스모크): SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/experiment_freespace_sigma.py \
                --smoke --backend direct --drone mini5pro --band lte --out /tmp/.../sigma.json
출력(정본): outputs/report13_sigma_grid.json   (기존 파일 무수정 — 신규 산출물)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                     # noqa: E402

C0 = 299792458.0
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")  # 정본 산출경로(코드에만)

# ── 축·값 (스펙 §6.1) ───────────────────────────────────────────────────────────
# 5 기종 target_extent 오름차순(F17) — freespace_scene.DRONE_ORDER 단일 진리원.
from freespace_scene import DRONE_ORDER                               # noqa: E402

#: 밴드 (name, fc[Hz], bw[Hz]) — report2 viz_report2.BANDS 와 동일(색만 제거).
BANDS = [
    ("LTE 1.8 GHz",   1.843e9, 20e6),
    ("5G NR 3.5 GHz", 3.500e9, 100e6),
    ("WiFi 5.2 GHz",  5.210e9, 80e6),
]
_BAND_BY_STD = {"lte": BANDS[0], "nr": BANDS[1], "wifi": BANDS[2]}

AZ_GRID = np.arange(0.0, 360.0, 3.0)          # 0…357°, 3° (120점) — 스펙 §6.1
# el 음수 확정(★A2/S8): 지상 TX/RX + 공중 표적 이등분선 el 전구간 음수. 유효도메인에 조밀.
#
# ⭐ 2026-08-03 **고도축 확장 — −20° 클램프 제거** (φ 스윕 라운드가 찾은 결함)
#   무엇이 문제였나 : 격자가 −20° 에서 끊겨 있었는데 소비자의 이등분선 앙각은 훨씬 아래로
#     내려간다. 공표된 φ 스윕(L=500 m·alt=60 m·d 100…20 km·φ 전주기)에서 **조회의 11.9 %**,
#     고도 120 m 변형에서는 **23.7 %** 가 −20° 밖이었고 전부 −20° 행으로 **말없이 클램프**됐다
#     (최저 −88.1°, d=100 m·φ=180°). `experiment_freespace_range._sigma_at` 이 그 사실을
#     세기만 하고 값은 그대로 썼다.
#   새 점을 왜 여기 두는가 (근거는 측정 두 가지, 짐작 아님)
#     ① 조회밀도 : −20° 밖 조회의 31 % 가 [−25,−20), 17.6 % 가 [−30,−25) 에 몰린다. 위쪽은
#        촘촘히(4°), 가운데는 7° 로 벌린다.
#     ② σ(el) 곡률 : 2.5° 미세 스캔(outputs/partial/sigma_regen_0803/probe)에서 −20~−60° 는
#        2.5° 당 0.2~1 dB 로 완만하지만 −78° 아래는 천정 실루엣이 급변해 2.5° 당 4~10 dB 까지
#        뛴다. 그래서 −78° 아래는 3° 로 다시 좁힌다.
#   +el 을 넣지 않는 이유 : 표적이 조명원 마스트(25 m)와 수신기(3 m) **둘 다보다 높으면**
#     이등분선 z 성분이 항등적으로 음수다(관측 최대 −0.13°). +el 은 표적 고도가 25 m 아래로
#     내려갈 때만 생기는데 report13 장면은 그런 고도를 쓰지 않는다.
#   ⚠ el=−90° 행은 시선벡터가 방위와 무관해(û=(0,0,−1)) **한 값이 az 전체에 복제**된다.
#     모노스태틱 물리로는 옳지만 방위평균이 없는 행이라 방위 통계를 인용하면 안 된다.
EL_GRID = np.array([0.0, -0.5, -1.0, -2.0, -3.5, -5.0, -8.0, -12.0, -20.0,
                    -24.0, -28.0, -33.0, -38.0, -44.0, -50.0, -57.0, -64.0,
                    -71.0, -78.0, -81.0, -84.0, -87.0, -90.0])
N_F = 3                                        # 반송파 ±1.5% 3점 대역평균 (스펙 §6.1)
FRAC_BW = 0.015                                # ±1.5%
DIV = 16                                       # ★report2 와 div=16 일치(A17)
SMOOTH_DEG = 3.0                               # 3° 각도평활(널 깊이 인용불가)
JITTER = 2                                     # 격자 위상 평균(절대 σ 안정, ±1.5→±0.15 dB)


# --------------------------------------------------------------------------- #
#  내부 — SBR 엔진 호출(두 backend). 재구현 없음, rcs_sbr_batch 1-bounce 만.
# --------------------------------------------------------------------------- #
def _gm(drone):
    """드론 그룹→재질 맵(materials.py 단일 진리원). channel._group_mat 와 동일 규약."""
    from channel import _group_mat
    return _group_mat(drone)


def _sigma_az_direct(drone, fc, az_deg, el_deg, div=DIV):
    """`backend="direct"` — 메인 프로세스에서 `rcs_sbr_batch(spacing=λ/div)` 직접 호출.

    스펙 §6.1 이 이름으로 지정한 바로 그 엔진 호출이다(penetrate=True·jitter=2·1-bounce).
    div 을 정확히 주므로 report2(div=16)와 같은 엔진이며, gpu.pick() 이 잡은 한 장만 쓴다.
    반환: σ[m²] 배열(len=az)."""
    from drones import DRONES, build_drone
    from rcs_sbr import rcs_sbr_batch
    lam = C0 / float(fc)
    mesh = build_drone(DRONES[drone])
    s = rcs_sbr_batch(mesh, _gm(drone), float(fc),
                      az_deg=np.asarray(az_deg, float), el_deg=float(el_deg),
                      spacing=lam / float(div), penetrate=True, jitter=JITTER,
                      cache_key=(drone, round(fc / 1e6), round(el_deg, 3), int(div)))
    return np.atleast_1d(np.asarray(s, float))


def _prefill_reuse(drone, fc, az_grid, el_grid, div=DIV, verbose=True):
    """`backend="prefill"` — `channel.sbr_sigma_prefill` 재사용(멀티 GPU·budget 우회 내장).

    ⚠ div=16 은 **전역상수 속성교체**(절대규칙 1)로 얻는다: `rcs_sbr.DEFAULT_DIV=div` 를 프리필
      **전에** 세팅하면 fork 된 워커가 상속한다(`_prefill_worker` 는 spacing 을 못 받으므로 이 길뿐).
    ⚠ `sbr_sigma_prefill` 은 (drone,fc,u1,u2,span,n_az) 를 받아 `look_angles` 로 az/el 을 만든다.
      직접 (az,el) 격자를 채우려면 u1=u2=û(az,el)·span=0·n_az=1 로 되돌린다(왕복 정확).
    ⚠ `gpu.all_usable()` 로 여유 GPU 를 **전부**(0~3) 쓴다 — SIONNA2_GPU 를 존중하지 않는다.
      GPU 를 제한해야 하면 backend="direct" 를 쓸 것(스모크가 그렇게 한다)."""
    import rcs_sbr
    rcs_sbr.DEFAULT_DIV = int(div)                       # ★fork 상속용 전역 속성교체
    from channel import sbr_sigma_prefill, _sbr_sigma
    reqs = []
    for el in el_grid:
        for az in az_grid:
            u = _unit(az, el)
            reqs.append((drone, float(fc), u, u, 0.0, 1))
    sbr_sigma_prefill(reqs, verbose=verbose)             # GPU 분배 + 캐시 저장
    out = np.zeros((len(el_grid), len(az_grid)))
    for i, el in enumerate(el_grid):
        out[i] = _sbr_sigma(drone, float(fc), np.asarray(az_grid, float), float(round(el, 3)))
    return out                                           # σ[m²] (el, az)


def _unit(az_deg, el_deg):
    """(az,el)[deg] → 단위 시선벡터 û. look_angles(û,û,0,1) 의 역."""
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def _sigma_grid_one(drone, fc, bw, az_grid, el_grid, n_f=N_F, div=DIV,
                    smooth_deg=SMOOTH_DEG, backend="direct", verbose=True):
    """한 (드론, 반송파) 의 σ(az, el) 격자 — 대역평균(n_f) + 3° 각도평활.

    각 el 에서 n_f 개 주파수(fc·(1±1.5%))의 σ(az) 를 **m² 선형평균**(대역평균), 그다음 3° 각도평활.
    (스펙 §6.2: 파이프라인과 동일 추정량 — dB 평균 아님. Jensen 낙관은 meta 에 표기.)
    반환 dict: sigma_m2(el,az), sigma_smooth_m2(el,az)."""
    from rcs_po import angular_smooth
    az_step = float(az_grid[1] - az_grid[0]) if len(az_grid) > 1 else 1.0
    freqs = (fc * np.linspace(1 - FRAC_BW, 1 + FRAC_BW, n_f)) if n_f > 1 else np.array([fc])

    if backend == "prefill":
        # 프리필은 단일주파수 캐시라 밴드평균을 주파수마다 반복 프리필로 얻는다.
        acc = None
        for f in freqs:
            g = _prefill_reuse(drone, float(f), az_grid, el_grid, div=div, verbose=verbose)
            acc = g if acc is None else acc + g
        sig = acc / len(freqs)
    else:                                                # direct
        sig = np.zeros((len(el_grid), len(az_grid)))
        for i, el in enumerate(el_grid):
            acc = None
            for f in freqs:
                s = _sigma_az_direct(drone, float(f), az_grid, float(el), div=div)
                acc = s if acc is None else acc + s
            sig[i] = acc / len(freqs)
            if verbose:
                print(f"      el={el:+6.1f}°  σ mean={_dbsm(np.mean(sig[i])):+6.2f} "
                      f"med={_dbsm(np.median(sig[i])):+6.2f} dBsm")

    sm = np.array([angular_smooth(sig[i], smooth_deg, az_step) for i in range(len(el_grid))])
    return dict(sigma_m2=sig, sigma_smooth_m2=sm)


def _dbsm(x):
    return float(10.0 * np.log10(np.maximum(x, 1e-30)))


# --------------------------------------------------------------------------- #
#  ⭐ 측정 앵커 → 검출사슬 (결함 D-B 수리, 2026-08-03)
# --------------------------------------------------------------------------- #
#  왜 이 절이 생겼나 — **앵커는 리포트 계층에만 있었다.**
#    `src/experiment_freespace_sigma.py` 와 `src/experiment_freespace_range.py` 에
#    `sigma_anchor` 참조가 **0건**이었다. 즉 "앵커링된 밴드 비교" 는 리포트의 참이고
#    검출수치(R90)의 거짓이었다. 생산 σ 는 우리 PO 원시출력 그대로였다.
#
#  ■ 어떻게 도달시키나 — **σ 격자에 밴드당 스칼라 Δ_b 를 실어 보낸다**
#    앵커 분해형은 `σ(f,φ,θ) = A(f)·B1(φ,θ)·B2` 다(`src/sigma_anchor.py`). 재보정은
#    **밴드당 스칼라 곱** 하나이므로 밴드 안의 각도구조·널 위치·정규화 잔차분포(B1·B2)는
#    비트단위로 불변이다. 그래서 σ 격자 JSON 에 `anchor.delta_db[drone][band]` 를 add-only
#    로 실으면 소비자(`experiment_freespace_range._sigma_at`)는 조회값에 곱하기만 하면 된다.
#    ⇒ 앵커가 **el 격자 전체**(우리 배(belly) 시선 포함)에 같은 스칼라로 걸린다. 이것이
#      "각도패턴은 우리 기하, 레벨·기울기는 측정" 이라는 분해형의 정의 그대로다.
#
#  ■ ⚠⚠ **두 가지(branch)를 반드시 함께 들고 다닌다** (2026-08-03 검증 워크플로 정정)
#    Das μ 를 우리 선형평균 규약으로 옮기는 +2.5068 dB(=10/ln10·γ, 지수분포/Swerling I·II)를
#    "근거 없으니 끄라" 던 지시가 **그 자체로 틀렸다**:
#      · 넣으면 Das↔Yuan 이 우리 대역에서 0.25 dB 안에서 일치한다.
#      · 빼면 2.26~2.39 dB 어긋난다(같은 원자료인데!).
#      · Yuan Fig 6a 의 Rician K 가 −10 dB 아래 = 사실상 지수분포 = +2.5068 이 정확한 자리.
#    그래도 **조용한 단일값은 금지**다. `conv_on`/`conv_off` 두 갈래를 항상 같이 낸다.
#    ★그리고 이 갈래는 **순위를 바꿀 수 없다** — 아래 `ANCHOR_BRANCH_NOTE` 참조.
ANCHOR_MODE_DEFAULT = "slope_only"          # R4: 레벨은 우리 것 보존, 기울기만 측정 (크기가정 불필요)
ANCHOR_MODES = ("slope_only", "level_and_slope")
ANCHOR_BRANCHES = ("conv_on", "conv_off")   # +2.5068 dB 규약변환 켬/끔
ANCHOR_BRANCH_DEFAULT = "conv_on"
ANCHOR_EL_REF_DEG = 0.0                     # Δ_b 를 재는 앙각 컷 (앵커의 방위면과 고도정합)

ANCHOR_BRANCH_NOTE = (
    "The +2.5068 dB statistic-convention offset is a PURE LEVEL knob: it enters anchor_mu_dbsm "
    "as the same constant in every band. Under mode='slope_only' the production default it "
    "cancels EXACTLY (target = mu_anchor + (mean(mu_our) - mean(mu_anchor))), so both branches "
    "give bit-identical deltas. Under 'level_and_slope' it shifts every band by the same "
    "+2.5068 dB, i.e. it moves absolute R but cannot change which waveform wins. Report both "
    "branches anyway and lead with the slope, where it cancels.")


def _anchor_target_dbsm(f_ghz, mu_our_dbsm, drone_key, mode, branch, anchor_name,
                        size_law="L2", allow_extrapolation=False):
    """(내부) 재보정 목표 레벨 A(f) [dBsm] — `sigma_anchor.relevel` 의 target 식을 갈래별로.

    `relevel()` 은 `to_linear_mean=True` 를 하드코딩하므로 `conv_off` 갈래를 낼 수 없다.
    그래서 target 식만 여기서 갈래별로 만들고, `conv_on` 결과가 `relevel()` 과 같은지
    `anchor_deltas()` 가 **매번 대조**한다(우리 계산이 아니라 생산함수가 정답이다)."""
    import sigma_anchor as SA
    f = np.asarray(f_ghz, float)
    mu_a = np.asarray(SA.anchor_mu_dbsm(f, anchor=anchor_name,
                                        to_linear_mean=(branch == "conv_on"),
                                        allow_extrapolation=allow_extrapolation), float)
    mu_our = np.asarray(mu_our_dbsm, float)
    if mode == "slope_only":
        return mu_a + (mu_our.mean() - mu_a.mean()), 0.0
    dsize = float(SA.size_correction_db(drone_key, size_law, SA.ANCHORS[anchor_name]["D_ref_m"]))
    return mu_a + dsize, dsize


def anchor_deltas(grid, drones=None, bands=None, el_ref_deg=ANCHOR_EL_REF_DEG,
                  modes=ANCHOR_MODES, branches=ANCHOR_BRANCHES, anchor_name=None,
                  size_law="L2", use_smooth=True) -> dict:
    """⭐ σ 격자 → **밴드당 재보정량 Δ_b [dB]** (두 갈래 × 두 모드). GPU 불필요.

    인자
      grid : `build_sigma_grid()["grid"]` 또는 산출물 JSON 의 `sigma.grid`
      el_ref_deg : Δ 를 재는 앙각 컷. 기본 0° — 앵커가 방위면 측정이라 **고도정합**이 된다
                   (`sigma_anchor.ANCHORS['yuan_phantom3_azplane'].elevation`). 곱은 스칼라라
                   격자 전체 el 에 같은 값이 걸린다(분해형 정의).
    반환 dict:
      by_drone[drone][mode][branch] = {delta_db{band}, mu_our_dbsm{band}, mu_after_dbsm{band},
                                       slope_before/after/anchor_db_per_ghz, size_correction_db}
      relevel_crosscheck : 생산함수 `sigma_anchor.relevel` 과의 최대 |Δ| [dB] (0 이어야 한다)
      branch_cancellation : 갈래 차 |Δ_on − Δ_off| 의 모드별 최대 [dB]
    """
    import sigma_anchor as SA
    anchor_name = anchor_name or SA.DEFAULT_ANCHOR
    drones = list(drones or grid.keys())
    out, xchk, bcan = {}, [], {m: [] for m in modes}
    for dr in drones:
        node = grid.get(dr)
        if not isinstance(node, dict):
            continue
        bnames = list(bands or node.keys())
        key = "sigma_smooth_dbsm" if use_smooth else "sigma_dbsm"
        sig_by_band, f_by_band = {}, {}
        for b in bnames:
            el = np.asarray(node[b]["el_deg"], float)
            i = int(np.argmin(np.abs(el - float(el_ref_deg))))
            if abs(el[i] - float(el_ref_deg)) > 1e-6:
                raise ValueError(f"{dr}/{b}: el={el_ref_deg}° 행이 격자에 없다 (가장 가까운 {el[i]}°)")
            sig_by_band[b] = 10.0 ** (np.asarray(node[b][key], float)[i] / 10.0)
            f_by_band[b] = float(node[b]["fc_hz"]) / 1e9
        f = np.array([f_by_band[b] for b in bnames])
        mu_our = np.array([SA.linear_mean_dbsm(sig_by_band[b]) for b in bnames])
        out[dr] = {}
        for mode in modes:
            out[dr][mode] = {}
            dd = {}
            for br in branches:
                target, dsize = _anchor_target_dbsm(f, mu_our, dr, mode, br, anchor_name,
                                                    size_law=size_law)
                delta = target - mu_our
                dd[br] = delta
                a_bef, _ = SA.fit_slope_db_per_ghz(f, mu_our)
                a_aft, _ = SA.fit_slope_db_per_ghz(f, target)
                out[dr][mode][br] = dict(
                    delta_db={b: float(delta[i]) for i, b in enumerate(bnames)},
                    mu_our_dbsm={b: float(mu_our[i]) for i, b in enumerate(bnames)},
                    mu_after_dbsm={b: float(target[i]) for i, b in enumerate(bnames)},
                    f_ghz={b: float(f[i]) for i, b in enumerate(bnames)},
                    slope_before_db_per_ghz=float(a_bef), slope_after_db_per_ghz=float(a_aft),
                    slope_anchor_db_per_ghz=float(SA.ANCHORS[anchor_name]["a"]),
                    size_correction_db=float(dsize), size_law=(size_law if mode == "level_and_slope" else None))
            if set(branches) == set(ANCHOR_BRANCHES):
                bcan[mode].append(float(np.max(np.abs(dd["conv_on"] - dd["conv_off"]))))
            # 생산함수 대조 — conv_on 은 relevel() 과 **같아야** 한다
            rl = SA.relevel(sig_by_band, f_by_band, dr, mode=mode, anchor=anchor_name,
                            size_law=size_law)
            if "conv_on" in out[dr][mode]:
                mine = out[dr][mode]["conv_on"]["delta_db"]
                xchk.append(float(max(abs(mine[b] - rl["delta_db"][b]) for b in bnames)))
    return dict(
        by_drone=out, anchor=anchor_name, el_ref_deg=float(el_ref_deg),
        statistic=("azimuth LINEAR mean (10log10 mean sigma_m2) at el_ref, "
                   "sigma_anchor.linear_mean_dbsm"),
        relevel_crosscheck_max_abs_db=(float(max(xchk)) if xchk else None),
        relevel_crosscheck_note=("conv_on branch must equal sigma_anchor.relevel() exactly; "
                                 "the production function is the oracle, not this replica"),
        branch_cancellation_max_abs_db={m: (float(max(v)) if v else None) for m, v in bcan.items()},
        branch_note=ANCHOR_BRANCH_NOTE,
        smooth=bool(use_smooth), source="src/sigma_anchor.py (Das/Yuan Phantom 3, ONE measurement)")


def apply_anchor(sigma_m2, delta_db):
    """앵커 Δ [dB] 를 σ[m²] 에 건다 — **스칼라 곱 하나**. 각도구조는 비트 불변.

    검출사슬(`experiment_freespace_range._sigma_at`)이 조회한 σ 에 이걸 곱하면 앵커가
    R90 에 도달한다. `delta_db=0.0` 이면 항등(수리 전 거동)."""
    return np.asarray(sigma_m2, float) * 10.0 ** (float(delta_db) / 10.0)


def anchored_grid(grid, deltas, mode=ANCHOR_MODE_DEFAULT, branch=ANCHOR_BRANCH_DEFAULT):
    """σ 격자에 Δ 를 **실체화**해 `sigma_anchored_dbsm` 를 add-only 로 붙인다(선택).

    기본 생산경로는 배열을 복제하지 않고 `anchor.delta_db` 만 실어 보낸다(스칼라 하나면
    충분하고 JSON 이 두 배가 되지 않는다). 소비자가 배열을 원할 때만 이걸 쓴다."""
    by = deltas["by_drone"]
    for dr, node in grid.items():
        if dr not in by:
            continue
        dm = by[dr][mode][branch]["delta_db"]
        for b, bn in node.items():
            if b not in dm:
                continue
            bn["anchor_delta_db"] = float(dm[b])
            bn["sigma_anchored_dbsm"] = [[v + float(dm[b]) for v in row]
                                         for row in bn["sigma_smooth_dbsm"]]
    return grid


def _stats(sig_m2):
    """σ[m²] 배열 → 인용 가능한 통계(dBsm). 파이프라인 추정량 = m² 선형평균(§6.2)."""
    a = np.asarray(sig_m2, float).ravel()
    p = np.percentile(a, [10, 50, 90])
    return dict(mean_dbsm=_dbsm(np.mean(a)),                 # m² 선형평균
                median_dbsm=_dbsm(np.median(a)),
                p10_dbsm=_dbsm(p[0]), p50_dbsm=_dbsm(p[1]), p90_dbsm=_dbsm(p[2]),
                peak_dbsm=_dbsm(np.max(a)), min_smooth_dbsm=_dbsm(np.min(a)),
                n=int(a.size))


# --------------------------------------------------------------------------- #
#  스펙 §9 시그니처 (5개)
# --------------------------------------------------------------------------- #
def build_sigma_grid(drones, bands, az, el, n_f=N_F, div=DIV, smooth_deg=SMOOTH_DEG,
                     backend="prefill", verbose=True) -> dict:
    """**σ 격자**(F5 직교히트맵의 원천) — (드론×밴드×el×az) SBR σ, 대역평균+3° 평활.

    스펙 §6.1: az 0…357/3°, **음의 el** 9점, 반송파 ±1.5% n_f 점, div=16, penetrate·jitter=2.
    `backend="prefill"`(정본, 재사용 mandate) 또는 `"direct"`(스모크·GPU 제한).

    인자
      drones : 드론 키 리스트(target_extent 순 권장)
      bands  : [(name, fc, bw), …]
      az, el : 방위·앙각 격자[deg] (el 은 음수)
    반환 dict:
      {"grid": {drone: {band_name: {el_deg, az_deg, fc_hz, bw_hz,
                                    sigma_dbsm[el][az], sigma_smooth_dbsm[el][az],
                                    stats{mean,median,p10,p50,p90,peak,min_smooth},
                                    by_el{el: stats}}}}}"""
    az = np.asarray(az, float)
    el = np.asarray(el, float)
    grid = {}
    for drone in drones:
        grid.setdefault(drone, {})
        for (bname, fc, bw) in bands:
            if verbose:
                print(f"  [σ] {drone:10s} {bname:14s} fc={fc/1e9:.3f}GHz backend={backend}")
            g = _sigma_grid_one(drone, fc, bw, az, el, n_f=n_f, div=div,
                                smooth_deg=smooth_deg, backend=backend, verbose=verbose)
            sm = g["sigma_smooth_m2"]
            by_el = {f"{e:+.1f}": _stats(sm[i]) for i, e in enumerate(el)}
            grid[drone][bname] = dict(
                el_deg=el.tolist(), az_deg=az.tolist(), fc_hz=float(fc), bw_hz=float(bw),
                sigma_dbsm=[[_dbsm(v) for v in row] for row in g["sigma_m2"]],
                sigma_smooth_dbsm=[[_dbsm(v) for v in row] for row in sm],
                stats=_stats(sm), by_el=by_el)
    return dict(grid=grid)


def multistatic_check(drones, bands, beta_grid=(0, 15, 30, 45, 60, 75, 90), n_az=24,
                      el_deg=-2.0, div=DIV, backend="direct", verbose=True) -> dict:
    """**멀티스태틱 Δσ(β)** — 조명 û_i 1회, û_s 만 β 로 벌려 `rcs_sbr_multistatic` 재사용 (§6.3).

    Δσ(β)=σ_multi−σ_bisector[dB]. u_s_list=[û_i] 가 모노(=이등분선). β>90° 는 SBR 유효범위 밖이라
    조명게이트·수신게이트 상호배타로 σ→0(전방산란 무효, ★rcs_sbr.py:252-255) → 유효범위만 인용.
    상반성 σ(i,s) vs σ(s,i) rms 도 함께(★깊은널 5~9 dB).

    반환 dict: {drone:{band:{beta_deg, dsigma_mean_db, dsigma_rms_db, dsigma_p95_db,
                             reciprocity_rms_db, valid}}}"""
    from drones import DRONES, build_drone
    from rcs_sbr import rcs_sbr_multistatic
    az = np.linspace(0.0, 360.0, int(n_az), endpoint=False)
    out = {}
    for drone in drones:
        mesh = build_drone(DRONES[drone])
        out.setdefault(drone, {})
        for (bname, fc, bw) in bands:
            lam = C0 / float(fc)
            rows = {}
            for beta in beta_grid:
                dvals, recip = [], []
                for a in az:
                    ui = _unit(a, el_deg)
                    us = _rotate_toward(ui, beta)          # û_i 를 β 벌린 방향
                    sig = rcs_sbr_multistatic(mesh, _gm(drone), float(fc), ui, [ui, us],
                                              spacing=lam / float(div), penetrate=True,
                                              jitter=JITTER, cache_key=(drone, round(fc / 1e6)))
                    sig = np.atleast_1d(np.asarray(sig, float))
                    s_mono, s_multi = float(sig[0]), float(sig[1])
                    dvals.append(_dbsm(s_multi) - _dbsm(s_mono))
                    # 상반성: σ(i→s) vs σ(s→i)
                    sig2 = np.atleast_1d(np.asarray(
                        rcs_sbr_multistatic(mesh, _gm(drone), float(fc), us, [ui],
                                            spacing=lam / float(div), penetrate=True,
                                            jitter=JITTER, cache_key=(drone, round(fc / 1e6))), float))
                    recip.append(_dbsm(s_multi) - _dbsm(float(sig2[0])))
                dvals = np.asarray(dvals)
                rows[str(int(beta))] = dict(
                    dsigma_mean_db=float(np.mean(dvals)), dsigma_rms_db=float(np.sqrt(np.mean(dvals ** 2))),
                    dsigma_p95_db=float(np.percentile(np.abs(dvals), 95)),
                    reciprocity_rms_db=float(np.sqrt(np.mean(np.asarray(recip) ** 2))),
                    valid=bool(beta <= 90.0), n_az=int(n_az))
            out[drone][bname] = rows
            if verbose:
                print(f"  [multistatic] {drone} {bname}: "
                      + " ".join(f"β{b}:{rows[b]['dsigma_mean_db']:+.1f}" for b in rows))
    return out


def _rotate_toward(u, beta_deg):
    """û 를 임의 수직축 둘레로 β[deg] 회전한 단위벡터(멀티스태틱 û_s 생성)."""
    u = np.asarray(u, float) / np.linalg.norm(u)
    tmp = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e = np.cross(u, tmp); e /= np.linalg.norm(e)
    b = np.radians(beta_deg)
    return u * np.cos(b) + e * np.sin(b)


def sigma_confidence(drones, bands) -> dict:
    """**σ 엔진 신뢰도 지도** D/λ (§6.4, F15). GPU 불필요(기하만).

    D=`radar_scene.target_extent`(bbox 최대 수평치수), λ=c/fc. D/λ<3 셀은 few-λ 라 SBR+PO 낙관·
    신뢰 낮음(그림에 세로선). ★mini5pro@LTE=2.32λ 가 최악(헤드라인 하한칸)."""
    from radar_scene import target_extent
    out = {}
    for drone in drones:
        D = float(target_extent(drone))
        out[drone] = dict(extent_m=D, D_over_lambda={})
        for (bname, fc, bw) in bands:
            r = D / (C0 / float(fc))
            out[drone]["D_over_lambda"][bname] = dict(
                value=float(r), fc_hz=float(fc), few_lambda=bool(r < 3.0))
    return dict(D_definition="radar_scene.target_extent (bbox max horizontal)",
                few_lambda_threshold=3.0, by_drone=out)


def counterfactual_common_carrier(drones, fc=3.5e9, az=None, el=None, n_f=N_F,
                                   div=DIV, backend="direct", verbose=True) -> dict:
    """**공통 반송파 반사실**(F10) — 모든 드론 σ 를 같은 3.5 GHz 에서 계산.

    밴드효과(λ²σ·기준대역·반복률)를 분리하려면 파형과 σ(f) 를 떼야 한다. 여기서는 σ 를 **한
    반송파에 고정**해 놓고(다른 밴드의 W/L/G 파형을 이 σ 위에 얹는 쪽은 range 실험이 함) 드론별
    σ 통계만 낸다. σ 격자는 build_sigma_grid 재사용(GPU 추가 0회는 캐시 히트시)."""
    az = AZ_GRID if az is None else np.asarray(az, float)
    el = EL_GRID if el is None else np.asarray(el, float)
    g = build_sigma_grid(drones, [("common 3.5 GHz", float(fc), 100e6)], az, el,
                         n_f=n_f, div=div, backend=backend, verbose=verbose)
    stats = {d: g["grid"][d]["common 3.5 GHz"]["stats"] for d in drones}
    return dict(fc_hz=float(fc), stats=stats,
                note="σ fixed at one carrier; waveform/band effect is decomposed in the range "
                     "experiment (F10 5-term). Compares airframe σ structure at equal carrier.")


def perturbation_grid(drones, bands, div_list=(12, 24), az=None, el_deg=-2.0,
                      n_boot=200, backend="direct", verbose=True) -> dict:
    """**(드론×밴드) 독립 섭동**(§6.4, F11) — div 교차 = 셀오차, 부트스트랩 = 통계오차.

    통짜 −3/0/+3 시프트(항등 순위보존)를 폐기하고, 실제 수치 불확실성 두 원천을 낸다:
      · div 교차(12↔24) 방위평균 σ 차이 = **격자 이산화 셀오차**(★report2: div 12↔16 방위평균 0.03 dB).
      · 방위 부트스트랩 = 통계 산포.
    각 (드론,밴드) 를 **독립** 섭동해 순위안정을 검사(통짜 시프트로는 rank_flip 이 항등적 0)."""
    az = np.arange(0.0, 360.0, 6.0) if az is None else np.asarray(az, float)
    rng = np.random.default_rng(13)
    out = {}
    for drone in drones:
        out.setdefault(drone, {})
        for (bname, fc, bw) in bands:
            means = {}
            base_az_sigma = None
            for div in div_list:
                sig = _sigma_az_direct(drone, float(fc), az, float(el_deg), div=div)
                means[str(int(div))] = _dbsm(np.mean(sig))
                if base_az_sigma is None:
                    base_az_sigma = sig
            div_keys = [str(int(d)) for d in div_list]
            cell_err = abs(means[div_keys[-1]] - means[div_keys[0]])
            # 방위 부트스트랩(마지막 div 격자 위)
            boots = [_dbsm(np.mean(rng.choice(base_az_sigma, base_az_sigma.size, replace=True)))
                     for _ in range(int(n_boot))]
            out[drone][bname] = dict(
                mean_dbsm_by_div=means, cell_error_db=float(cell_err),
                bootstrap_std_db=float(np.std(boots)),
                bootstrap_ci95_db=[float(np.percentile(boots, 2.5)),
                                   float(np.percentile(boots, 97.5))])
            if verbose:
                print(f"  [perturb] {drone} {bname}: cell_err={cell_err:.3f} "
                      f"boot_std={out[drone][bname]['bootstrap_std_db']:.3f} dB")
    return dict(method="drone_band_independent (div cross + azimuth bootstrap)",
                div_list=list(div_list), by_drone_band=out)


# --------------------------------------------------------------------------- #
#  I/O — 증분저장(재시작)
# --------------------------------------------------------------------------- #
def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def _meta(az, el, n_f, div, smooth_deg, bands, backend, extra=None):
    import subprocess
    try:
        rev = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                      stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        rev = ""
    m = dict(report="report13", producer="experiment_freespace_sigma.py",
             generated=time.strftime("%Y-%m-%dT%H:%M:%S"), git_rev=rev,
             engine="sbr (rcs_sbr_batch, 1-bounce, penetrate=True)", jitter=JITTER,
             div=int(div), div_note="report2 uses div=16; DEFAULT_DIV=12 — direct backend honors "
             "div exactly, prefill backend needs rcs_sbr.DEFAULT_DIV monkeypatch (fork-inherited)",
             backend=backend, az_deg=np.asarray(az, float).tolist(),
             el_deg=np.asarray(el, float).tolist(),
             el_note="NEGATIVE el (belly view); report2 was +15 deg (top). look_el_deg always <0.",
             n_f=int(n_f), frac_bw=FRAC_BW, smooth_deg=float(smooth_deg),
             bands=[[b[0], float(b[1]), float(b[2])] for b in bands],
             drone_order=list(DRONE_ORDER),
             quote_policy="percentiles/coverage only; NO null-min/sigma-min/aspect-peak/point value; "
                          "m^2 linear mean (Jensen-optimistic, recorded)",
             gpus=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    if extra:
        m.update(extra)
    return m


def _derive_aggregates(out):
    """grid/multistatic 에서 소비자(viz F6/F9/F14c)가 읽는 **파생 평탄 구조**를 추가한다(add-only).
      · sigma.stats[drone] : NR(@3.5 GHz) 밴드 σ 정렬 CDF + 앙각 곡선(음의 el).
      · multistatic.{beta_deg, delta_sigma_mean_db} : 드론·밴드 평균 Δσ(β) 평탄곡선.
    격자 자체는 밴드중첩(grid[drone][band])을 유지한다 — 이건 그 위에 얹는 요약이다."""
    NR = "5G NR 3.5 GHz"
    grid = (out.get("sigma") or {}).get("grid")
    if isinstance(grid, dict):
        stats = {}
        for drone, bands in grid.items():
            if not isinstance(bands, dict):
                continue
            node = bands.get(NR) or next(iter(bands.values()), None)
            if not isinstance(node, dict):
                continue
            sm = np.asarray(node.get("sigma_smooth_dbsm", []), float)
            el = np.asarray(node.get("el_deg", []), float)
            if sm.size == 0:
                continue
            flat = np.sort(sm.ravel())
            vs_el = (sm.mean(axis=1).tolist()
                     if (sm.ndim == 2 and sm.shape[0] == el.size) else [])
            stats[drone] = dict(band=NR, sigma_sorted_dbsm=flat.tolist(),
                                cdf=np.linspace(0.0, 1.0, flat.size).tolist(),
                                el_deg=el.tolist(), sigma_vs_el_dbsm=vs_el)
        if stats:
            out["sigma"]["stats"] = stats

    ms = out.get("multistatic")
    if isinstance(ms, dict) and ms:
        betas, acc = None, None
        for drone, bands in ms.items():
            if not isinstance(bands, dict):
                continue
            for band, rows in bands.items():
                if not isinstance(rows, dict):
                    continue
                bs = sorted(int(b) for b in rows if str(b).lstrip("-").isdigit())
                if not bs:
                    continue
                if betas is None:
                    betas, acc = bs, [[] for _ in bs]
                if bs == betas:
                    for i, b in enumerate(bs):
                        v = rows[str(b)].get("dsigma_mean_db")
                        if v is not None:
                            acc[i].append(float(v))
        if betas:
            out["multistatic"]["beta_deg"] = [float(b) for b in betas]
            out["multistatic"]["delta_sigma_mean_db"] = [
                (float(np.mean(a)) if a else 0.0) for a in acc]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="report13 자유공간 σ 격자 생산자")
    ap.add_argument("--drone", default=None, help="한 드론만(증분저장·재시작). 미지정=전체")
    ap.add_argument("--band", default=None, choices=["lte", "nr", "wifi"], help="한 밴드만")
    ap.add_argument("--backend", default="prefill", choices=["prefill", "direct"])
    ap.add_argument("--out", default=SIGMA_JSON)
    ap.add_argument("--smoke", action="store_true", help="스모크(az 8·el 3·n_f 1·no multistatic 스윕)")
    ap.add_argument("--force", action="store_true", help="이미 있는 드론도 재계산")
    ap.add_argument("--parts", default="grid,confidence,anchor",
                    help="쉼표목록: grid,multistatic,confidence,counterfactual,perturbation,anchor")
    ap.add_argument("--anchor-mode", default=ANCHOR_MODE_DEFAULT, choices=list(ANCHOR_MODES))
    ap.add_argument("--anchor-branch", default=ANCHOR_BRANCH_DEFAULT, choices=list(ANCHOR_BRANCHES))
    ap.add_argument("--materialize-anchor", action="store_true",
                    help="sigma_anchored_dbsm 배열까지 실체화(기본은 delta_db 스칼라만)")
    args = ap.parse_args(argv)

    # GPU — mitsuba import 전에 pick (SIONNA2_GPU 존중). direct backend 는 이 한 장만 쓴다.
    from gpu import pick
    pick(verbose=True)

    drones = [args.drone] if args.drone else list(DRONE_ORDER)
    bands = [_BAND_BY_STD[args.band]] if args.band else list(BANDS)
    az, el, n_f = AZ_GRID, EL_GRID, N_F
    beta_grid, n_az_ms = (0, 15, 30, 45, 60, 75, 90), 24
    if args.smoke:
        az = np.arange(0.0, 360.0, 45.0)          # 8점
        el = np.array([0.0, -2.0, -8.0])          # 3점
        n_f = 1
        beta_grid, n_az_ms = (0, 30, 90), 4
    parts = [p.strip() for p in args.parts.split(",") if p.strip()]

    out = _load(args.out) or {}
    out.setdefault("meta", _meta(az, el, n_f, DIV, SMOOTH_DEG, bands, args.backend,
                                 extra=dict(smoke=bool(args.smoke))))
    out.setdefault("sigma", {"grid": {}})

    t0 = time.time()
    # ── grid: 드론별 증분저장(재시작 가능) ──
    if "grid" in parts:
        for drone in drones:
            if (drone in out["sigma"]["grid"]) and not args.force:
                print(f"  [σ] {drone} 이미 있음 — 건너뜀(--force 로 재계산)")
                continue
            g = build_sigma_grid([drone], bands, az, el, n_f=n_f, div=DIV,
                                 backend=args.backend, verbose=True)
            out["sigma"]["grid"][drone] = g["grid"][drone]
            _save(args.out, out)                   # ★드론 하나 끝날 때마다 저장
            print(f"  [σ] {drone} 저장 → {args.out}")

    if "confidence" in parts:
        out["sigma_confidence"] = sigma_confidence(drones, bands)
        _save(args.out, out)
    if "multistatic" in parts:
        out["multistatic"] = multistatic_check(drones, bands, beta_grid=beta_grid,
                                               n_az=n_az_ms, backend=args.backend)
        _save(args.out, out)
    if "counterfactual" in parts:
        out["counterfactual_common_carrier"] = counterfactual_common_carrier(
            drones, az=az, el=el, n_f=n_f, backend=args.backend)
        _save(args.out, out)
    if "perturbation" in parts:
        out["perturbation"] = perturbation_grid(drones, bands, backend=args.backend)
        _save(args.out, out)

    # ── ⭐ 앵커(D-B): 밴드당 Δ 를 격자에 실어 검출사슬로 보낸다 (add-only, GPU 0회) ──
    if "anchor" in parts:
        try:
            g = out["sigma"]["grid"]
            dl = anchor_deltas(g, drones=[d for d in drones if d in g])
            out["sigma"]["anchor"] = dl
            out["sigma"]["anchor"]["applied_default"] = dict(
                mode=args.anchor_mode, branch=args.anchor_branch,
                consumer=("experiment_freespace_range._sigma_at 가 조회 σ 에 "
                          "experiment_freespace_sigma.apply_anchor(sigma, delta_db) 를 곱한다"),
                switch="anchor_on (기본 켬); 끄면 delta=0 = 수리 전 거동")
            if args.materialize_anchor:
                anchored_grid(g, dl, mode=args.anchor_mode, branch=args.anchor_branch)
            _save(args.out, out)
            print(f"  [anchor] Δ 산출 (mode={args.anchor_mode} branch={args.anchor_branch}) "
                  f"relevel 대조 max|Δ|={dl['relevel_crosscheck_max_abs_db']:.2e} dB")
        except Exception as e:
            print(f"  [anchor] skip: {type(e).__name__}: {e}  "
                  f"(앵커는 3밴드 전부 있는 격자에서만 낼 수 있다 — --band 로 한 밴드만 돌린 경우 정상)")

    # ── 파생 평탄 구조(add-only) — 소비자 F6/F9/F14c 가 읽는 sigma.stats·multistatic 평탄 ──
    _derive_aggregates(out)
    out["meta"]["runtime_s"] = round(time.time() - t0, 1)
    _save(args.out, out)
    print(f"\n[σ] 완료 ({out['meta']['runtime_s']}s) → {args.out}")
    return out


if __name__ == "__main__":
    main()
