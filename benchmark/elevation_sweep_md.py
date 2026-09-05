# -*- coding: utf-8 -*-
"""
elevation_sweep_md.py — **거리 대신 앙각을 바꿔가며 마이크로도플러를 그린다.**

사용자(2026-08-11)
> "이번 주 팀미팅 준비하면서 같은 각도에서 거리만 멀어지게 해서 STFT 했잖아.
>  그걸 **엘리베이션을 바꿔가며** 그려보는 것부터 우선적으로 해볼 수 있을까?"

■ 왜 이 축인가
거리 축에서는 우리 커널의 맵이 거의 안 변했다(상관 0.983 / 0.999 / 0.983). 산란 진폭은
표적의 성질이고 거리는 링크버짓의 몫이라 그게 맞다. **앙각은 다르다** — 표적이 실제로
다르게 보이는 축이다.
⛔**«우리 커널만 답할 수 있다» 는 2026-09-04 에 뺐다.** 두 엔진이 각도 의존을 **다른 길로**
낸다: 우리 커널은 면적분으로 로브를 내고, PathSolver 는 경로 합으로 낸다 — 확산 반사 포함이고
**이 스크립트 700 행이 켠다**(`diffuse_reflection=diffuse`). 이 판의 다섯 팔 규약이 그 위에
서 있다. ⛔어느 쪽이 현실에 가까운지는 **실측 대조가 0 건이라 여기서 말하지 않는다.**

■ ⭐예측 — 재기 전에 못 박는다
    f_flash = 날개 수 × 회전수 = 126.67 Hz  ← **앙각과 무관**
    f_tip   = 2·(2π f_rev R)/λ · cos(el)    ← **cos(el) 로 줄어든다**

| el | cos | f_tip [Hz] |
|---|---|---|
| 0° | 1.000 | 1272 |
| −15° (덱) | 0.966 | 1229 |
| −30° | 0.866 | 1102 |
| −45° | 0.707 | 900 |
| −60° | 0.500 | 636 |
| −75° | 0.259 | 329 |
| −90° (직하방) | 0.000 | **0** |

⇒ **플래시 박자는 그대로, 날개끝 도플러 폭 f_tip 만 0 으로 간다.**
⛔**«마이크로도플러가 원리적으로 사라진다 / 머리 위 드론은 안 보인다» 는 2026-09-04 에
  철회한다.** 직하방 기록을 다시 재 보면(el −90, 자세 8192, 평균 제거 후 FFT, PRF 19,700 Hz)
  **f_flash 선이 두 엔진 모두 127.5 Hz 에 또렷이 선다**(예측 126.67 Hz). 선 세기 ÷ 스펙트럼
  중앙값은 우리 커널 49 배 · PathSolver(다 끔) 494 배이고, PathSolver 쪽은 배음 252.5 · 505 Hz
  까지 남는다. **사라지는 것은 «폭» 이지 «박자» 가 아니다.** 그리고 «안 보인다» 는 탐지
  판정인데 이 저장소에 ROC·실측 근거가 없다.

■ ⚠대역을 앙각마다 다시 잡아야 한다
덱의 대역은 `0.35~1.0 × f_tip` 인데 f_tip 이 앙각에 걸리므로 **고정 대역을 쓰면 안 된다.**
이 스크립트는 두 가지를 다 낸다 —
  (a) `band=track`  앙각마다 그 앙각의 f_tip 으로 대역을 다시 잡는다 ⭐정본
  (b) `band=fixed`  덱의 −15° 대역(430~1229 Hz)을 그대로 쓴다 → 앙각이 내려가면 **비어 간다**
(b) 를 함께 내는 이유는 «고정 대역을 쓰면 어디서 무너지나» 가 그 자체로 결과이기 때문이다.

■ 축 하나만 바꾼다
로터는 **덱과 같은 결정론 패턴**을 쓴다(OU 프리셋이 아니다). 로터와 앙각을 같이 바꾸면
무엇이 무엇을 바꿨는지 못 가른다. 거리는 **10 m 구면**으로 고정한다 — 앙각이 바뀌어도 표적까지의 거리가 일정하다
  (`place()` 가 `tx = c + R·û` 이고 baseline 0 이라 |tx−c| = R 로 항상 같다).
  ⚠10 m 는 원거리장 경계 2D²/λ ≈ 14.08 m **안쪽**이다. 우리 커널은 `range_m` 구면파로
  처리하고 PathSolver 는 실제 기하라 원래 문제없다 — 다만 «근거리장 판» 이라고 적어야 한다.

    # 우리 커널
    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py \
        --engine ours --shard 0 --nshards 8
    # Sionna PathSolver
    SIONNA2_GPU=2 PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py \
        --engine sionna --shard 0 --nshards 8
    # 병합·분석
    PYTHONPATH=src:benchmark python benchmark/elevation_sweep_md.py --merge
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

# ⛔(2026-08-15 제거) 옛 «GPU2 고정» 유물 setdefault("SIONNA2_GPU","2") 가 여기 있었다.
#   런처가 CUDA_VISIBLE_DEVICES 로 보낸 카드를 gpu.pick() 이 이 유물로 덮어써서, 분산
#   투입한 팔들이 전부 물리 GPU2 에 쌓였다. 카드 선택은 런처(감시기·수동)가 한다.

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⭐⭐**스레드 캡을 코드로 못 박는다** (2026-08-20). 환경변수만으로는 **안 걸린다** —
#   `DRJIT_NUM_THREADS`·`MI_NUM_THREADS` 는 drjit 1.3.1 · mitsuba 3.8.0 에 **없는 이름**이다
#   (패키지 전체 grep 0 건). 실측: env 로 2 를 걸어도 dr.thread_count() 가 **192** 이고,
#   병렬 작업 한 번에 프로세스 스레드가 **200 개**로 뛴다. 랩 서버를 마비시킨 그 경로다.
#   ⭐여기(워커 본체)에 있어야 **어느 런처로 띄우든** 걸린다.
try:
    from thread_guard import apply as _thread_apply
    _TG = _thread_apply(int(os.environ.get("OMP_NUM_THREADS", "2")), verbose=False)
except Exception as _e:                                                  # noqa: BLE001
    _TG = {"err": str(_e)[:120]}

import numpy as np                                                      # noqa: E402

FC, RANGE_M = 3.5e9, 10.0          # ⭐사용자 지시(2026-08-11) — 구면 반경 10 m 고정
ELS = (0.0, -15.0, -30.0, -45.0, -60.0, -75.0, -90.0)
DIV = 12                            # 격자 간격 λ/12 — 덱과 같은 규약
SHD = f"{ROOT}/outputs/elev_sweep_shards"
OUT = f"{ROOT}/outputs/elevation_sweep_md.json"
OUTN = f"{ROOT}/outputs/elevation_sweep_md.npz"
TJ = json.load(open(f"{ROOT}/outputs/report07_three_engines.json"))["_meta"]


def los(az_deg: float, el_deg: float) -> np.ndarray:
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


#: ⭐**실외 환경 축** (2026-08-31 신설) — 지금까지 장면에는 드론밖에 없었다
#  ■ 왜 — `build_scene` 은 빈 씬에 드론 부품만 넣는다. 그래서 우리가 «클러터» 라고 부르며
#    걷어낸 것은 전부 **드론 자신의 동체**였다. 환경 클러터는 한 번도 없었다.
#  ■ 기하 — 드론이 원점이고 레이다는 `rng·sin(el)` 깊이에 온다(report15_probe.place).
#    ⛔그러니 **지면은 그보다 더 아래**여야 한다. 안 그러면 레이다가 땅속에 들어간다.
#    15 m·el −90 이면 −15 m 이므로 비행고도를 **20 m** 로 잡아 여유를 둔다.
#  ■ ⛔실외만 쓴다(사용자 지시 2026-08-31). 실내 챔버는 이 축에 넣지 않는다.
#: 기본 씬을 쓸 때 드론이 뜨는 높이[m] — 레이다가 rng·sin(el) 깊이에 오므로 그보다 커야 한다
ENV_BUILTIN_ALT = 25.0

ENV_SPECS = {
    "outdoor01": dict(
        dir=f"{ROOT}/assets/meshes/outdoor01", alt_m=20.0,
        parts=[("ground", "concrete_dark", (0.42, 0.40, 0.37)),
               ("bldg_a", "concrete_light", (0.78, 0.80, 0.84)),
               ("bldg_b", "concrete_light", (0.78, 0.80, 0.84)),
               ("bldg_c", "concrete_light", (0.78, 0.80, 0.84)),
               ("bldg_d", "concrete_light", (0.78, 0.80, 0.84)),
               ("pole_a", "metal", (0.45, 0.47, 0.50)),
               ("pole_b", "metal", (0.45, 0.47, 0.50))]),
}


def build_scene_builtin(RP, parts, name: str, fc: float):
    """⭐엔비디아 기본 씬 안에 드론을 넣는다 (2026-09-01 신설).

    ■ 왜 — 우리가 만든 120×120 m 콘크리트 평면은 **매끄러운 거울**이라 최악에 가깝다.
      실제 도시 장면에서도 같은 일이 나는지 보려면 남의 씬으로 갈아 끼워 봐야 한다.
    ■ 기하 — 스윕은 드론이 **원점**이고 레이다가 `rng·sin(el)` 깊이에 오는 규약이다.
      기본 씬은 자기 좌표를 갖고 있으므로 **씬을 드론 아래로 내려** 그 규약을 지킨다.
      내리는 양은 `ENV_BUILTIN_ALT` — 레이다가 땅속에 안 들어갈 만큼이다.
    ⚠재질·기하는 그 씬이 정한 것을 그대로 쓴다(우리가 고른 것이 아니다).
    """
    from sionna.rt import load_scene, scene as _S
    import mitsuba as _mi
    if not hasattr(_S, name):
        raise SystemExit(f"⛔ 모르는 기본 씬: {name} — 아는 것 "
                         f"{[n for n in dir(_S) if not n.startswith('_')]}")
    sc = load_scene(getattr(_S, name))
    sc.frequency = fc
    sc.tx_array = RP.rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                    polarization="V")
    sc.rx_array = RP.rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso",
                                    polarization="V")
    #: ⛔씬을 통째로 옮기지 않는다 — 이름 없는 물체가 있는 씬(simple_street_canyon)에서
    #   `SceneObject.position` 설정이 `KeyError: no-name-1.vertex_positions` 로 죽는다.
    #   ⇒ **씬은 그대로 두고 드론을 그 위로 올린다.** 레이다도 같은 중심에 매인다.
    ctr = (0.0, 0.0, float(ENV_BUILTIN_ALT))
    from materials import make_material
    objs = []
    for p in parts:
        mat = make_material(p.mat_key, name=f"mat_{p.name}", color=p.color)
        o = (RP.rt.SceneObject(mi_mesh=p.mi_mesh, name=p.name, radio_material=mat)
             if getattr(p, "mi_mesh", None) is not None
             else RP.rt.SceneObject(fname=p.obj, name=p.name, radio_material=mat))
        objs.append(o)
    sc.edit(add=objs)
    #: 얹은 **드론 부품만** 올린다(씬 물체는 안 건드린다)
    for o in objs:
        _c = o.position
        o.position = _mi.Point3f(float(_c.x[0]) + ctr[0], float(_c.y[0]) + ctr[1],
                                 float(_c.z[0]) + ctr[2])
    return sc, ctr


def env_parts(Part, key: str):
    """환경 부품 목록. 지면이 드론 **아래** 오도록 통째로 내린다."""
    if key not in ENV_SPECS:
        raise SystemExit(f"⛔ 모르는 환경: {key} — 아는 것 {list(ENV_SPECS)}")
    spec = ENV_SPECS[key]
    dz = -float(spec["alt_m"])
    out = []
    for nm, mat, col in spec["parts"]:
        f = os.path.join(spec["dir"], f"{nm}.obj")
        if not os.path.exists(f):
            raise SystemExit(f"⛔ 환경 메쉬가 없다: {f} — "
                             f"benchmark/make_outdoor_scene_0831.py 를 먼저 돌려라")
        out.append(Part(name=f"env_{nm}", obj=f, mat_key=mat, color=col,
                        position=(0.0, 0.0, dz)))
    return out


def rule_spp(rng_m: float) -> int:
    """(R/3)² × 1M — 덱과 같은 광선 규칙."""
    return int(round(1_000_000 * (rng_m / 3.0) ** 2))


#  ⭐**셸 두께 정정 축** (R2, 2026-08-15 신설)
#  ■ 무엇이 결함이었나
#    `src/materials.py:make_material()` 의 비-ITU 분기가 `thickness` 를 안 넘겨서 Sionna 기본값
#    **0.1 m(=10 cm)** 이 쓰였다(`sionna/rt/constants.py:80`). 드론 셸은 실제로 1~3 mm 다.
#    두께는 굴절뿐 아니라 **정반사 계수도** 바꾸므로(ITU-R P.2040 단층 슬래브) 이 오염은
#    굴절 팔이 아니라 **모든 PathSolver 팔**에 걸려 있었다.
#  ■ CPU 로 먼저 재 봤다 — `benchmark/slab_thickness_check.py`
#    플라스틱 셸 정반사 |R|: 100 mm −13.38 dB · 3 mm −14.97 · 2 mm −18.28 · 1 mm −24.16 dB.
#    2 mm 로 고치면 수직입사 **−4.90 dB** · 각도평균 **−5.82 dB** 움직인다 → ⓪ 격자 밴드
#    3.86 dB **밖**이라 GPU 를 살 값어치가 있다. 1↔3 mm 안에서만 9.19 dB 가 갈리므로
#    **단일값이 아니라 민감도 축(1·2·3 mm)** 으로 돌린다(두께는 출처가 없다 — RETRACTION_LOG A3).
#  ■ 탄소섬유는 손잡이가 없다 — 표피깊이 0.155 mm 라 1 mm 도 이미 여러 표피깊이(0.00 dB 차이).
#  ■ 우리 커널에는 두께가 없다(|Γ|·τ 뿐) → 이 인자는 **PathSolver 팔 전용**이다.
def _tag_thickness(shell_mm: float, prop_mm: float) -> str:
    """⭐셸/프롭 두께 꼬리표. **0 이면 빈 문자열** — 안 주면 기존 샤드와 이름이 같다(비트동일).
    예: shell 2 mm → `_shell2mm` · prop 1 mm → `_prop1mm` (둘 다면 이어 붙는다)."""
    return ("" if not shell_mm else f"_shell{shell_mm:g}mm") \
        + ("" if not prop_mm else f"_prop{prop_mm:g}mm")


def thickness(a) -> tuple[float, float, str]:
    """`--shell-mm`·`--prop-mm` → (셸 mm, 프롭 mm, 꼬리표). 안 주면 (0, 0, "") 라 아무 일도
    없다 — `materials.set_thickness_mm()` 을 **부르지 않으므로** 예전과 비트동일하다."""
    sh = float(getattr(a, "shell_mm", 0.0) or 0.0)
    pr = float(getattr(a, "prop_mm", 0.0) or 0.0)
    # ⛔단위 사고를 **양쪽에서** 막는다. 0.002(m) 를 그대로 치면 0.002 mm(=2 µm)가 되고,
    #   100 을 치면 «지금 돌고 있는 잘못된 판» 을 일부러 재현하는 셈이라 둘 다 죽인다.
    #   창은 0.1~20 mm — 드론 셸(1~3 mm)과 그 언저리만 허용한다.
    for nm, v in (("--shell-mm", sh), ("--prop-mm", pr)):
        if v == 0.0:
            continue                     # 안 준 것 — 아무 일도 안 일어난다(비트동일)
        if not (0.1 <= v <= 20.0):
            raise SystemExit(
                f"⛔ {nm} 단위는 **mm** 다(셸 1~3 mm, 허용 0.1~20). 받은 값 {v!r} 은 범위 밖. "
                f"· 0.002 처럼 작으면 **미터를 그대로 친 것**이다(0.002 m = 2 mm → '2' 라고 쓴다). "
                f"· 100 처럼 크면 Sionna 기본값 판을 재현하려는 것인데, 그건 인자를 **아예 빼면** "
                f"된다(그게 기존 샤드다).")
    return sh, pr, _tag_thickness(sh, pr)


def parse_grid_shift(text) -> tuple:
    """`--grid-shift` 를 (e1 칸, e2 칸, 꼬리표) 로 푼다 — **0 이면 꼬리표가 없다.**

        ""  · "0" · "0,0"  →  (0.0, 0.0, "")            ⭐기존 샤드 이름과 같아진다
        "0.5"              →  (0.5, 0.5, "_shift0.5")
        "0.5,0.25"         →  (0.5, 0.25, "_shift0.5x0.25")

    칸 단위다(실제 이동거리 = 칸 × 격자간격 d). 꼬리표가 안 붙는 자리가 곧 «인자를 안 주면
    비트 동일» 이라는 철칙의 배선이다 — 값이 0 이면 아래 run() 이 판을 아예 안 옮긴다."""
    t = str(text or "").strip().replace("x", ",")
    if not t:
        return 0.0, 0.0, ""
    parts = [p for p in t.split(",") if p.strip() != ""]
    try:
        v = [float(p) for p in parts]
    except ValueError:
        v = []
    if len(v) not in (1, 2):
        raise SystemExit(f"⛔ --grid-shift 형식: <칸수> 또는 <e1칸>,<e2칸> (받은 값 {text!r})")
    s1, s2 = (v[0], v[0]) if len(v) == 1 else (v[0], v[1])
    if s1 == 0.0 and s2 == 0.0:
        return 0.0, 0.0, ""
    return s1, s2, (f"_shift{s1:g}" if s1 == s2 else f"_shift{s1:g}x{s2:g}")


# ═══ 반송파 ═════════════════════════════════════════════════════════════════
#  ⭐**안 주면 기존과 비트동일**이 이 배관의 유일한 규약이다(--div·--parts·--az-deg 와 같다).
#    3.5 GHz 로 접히면 모듈 상수 FC 를 **그대로** 돌려주고 꼬리표도 안 붙인다 → 파일 이름이
#    옛 샤드와 같아 이미 계산한 것을 그대로 건너뛴다.
#  ⚠파장이 바뀌면 따라 바뀌는 것(전수):
#    · 격자 간격 d = λ/div  → run() 이 fc 로 다시 잰다. **div 는 12 로 둔다**(λ/12 규약 유지).
#    · 얼린 격자 판 gref    → 같은 d 로 다시 만든다(칸 수 n 이 ∝1/λ 로 는다).
#    · 우리 커널 sbr_field  → 파수 k·재질 |Γ| 를 fc 로 계산한다.
#    · PathSolver scene.frequency → 재질 슬래브 계수가 두께/λ 로 바뀐다.
#    · 위상 exp(−j2πfc·τ)  → 도플러가 여기서 나온다.
#    · f_tip = 2·(2π f_rev R)/λ·cos(el) → 병합 쪽 f_tip_at 이 팔 이름의 꼬리표로 읽는다.
#  ⚠안 바뀌는 것: f_flash(= 날개 수 × 회전수) · 광선 예산 규칙 (R/3)²×1M · 기하(가림·앙각).
def carrier(a) -> tuple[float, str]:
    """`--fc-ghz` → (fc[Hz], 파일명 꼬리표). 안 주면 규약값 3.5 GHz 라 꼬리표가 없다.

    꼬리표는 **MHz** 로 적는다 — 5.8 GHz → `_fc5800`. (docs/NEXT_EXPERIMENTS.md 의 표기)"""
    ghz = float(getattr(a, "fc_ghz", 0.0) or FC / 1e9)
    if not (0.1 <= ghz <= 300.0):
        # ⛔설계서 옛 표기 «--fc 5.8e9» 를 그대로 치는 사고를 여기서 잡는다(5.8e9 GHz 가 된다).
        raise SystemExit(f"⛔ --fc-ghz 는 **GHz** 다(예: 5.8). 받은 값 {ghz!r} 은 범위 밖이다.")
    fc = ghz * 1e9
    if abs(fc - FC) <= 1.0:              # 1 Hz 안이면 규약값 — 상수를 그대로 써서 비트동일
        return FC, ""
    return fc, f"_fc{fc / 1e6:g}"


def carrier_of(arm: str) -> float:
    """병합 쪽 — 팔(파일) 이름의 `_fc<MHz>` 꼬리표에서 반송파를 읽는다. 없으면 규약값.

    ⚠`_parts...` 꼬리표에 그룹 이름 `fc`(비행제어기)가 섞일 수 있어 **숫자를 반드시** 요구한다
      (`_partsfc` 는 안 걸린다)."""
    m = re.search(r"_fc(\d+(?:\.\d+)?)", arm)
    return FC if not m else float(m.group(1)) * 1e6




def require_cuda_variant() -> None:
    """⛔**GPU 가 안 열렸는데 조용히 CPU 로 도는 것**을 막는다 (2026-08-20 신설).

    Sionna 는 CUDA 초기화가 실패하면 **예외도 경고도 없이** `llvm_ad_mono_polarized` 로
    떨어진다(실측). 그 상태로 생산을 돌리면 **GPU 판과 똑같은 이름의 샤드**를 CPU 로 써서
    원장에 두 엔진이 섞인다 — 나중에 구별할 방법이 없다.
    ⇒ 생산 진입점에서 변종을 확인하고, CUDA 가 아니면 **멈춘다**.

    ⭐탈출구: 정말 CPU 로 돌려야 하면 `SIONNA2_ALLOW_CPU=1` 을 준다(그때는 본인 책임).
    """
    if os.environ.get("SIONNA2_ALLOW_CPU") == "1":
        return
    try:
        import mitsuba as mi
        v = mi.variant() or ""
    except Exception as e:                                      # noqa: BLE001
        raise SystemExit(f"⛔ Mitsuba 를 못 불러왔다: {e}")
    if not v.startswith("cuda"):
        raise SystemExit(
            f"⛔ Mitsuba 변종이 {v!r} 다 — GPU 가 안 열려 **CPU 로 떨어졌다**.\n"
            f"   이대로 돌리면 GPU 판과 **같은 이름**의 샤드를 CPU 로 써서 원장이 섞인다.\n"
            f"   · nvidia-smi 가 되는지, /dev/nvidia* 가 열리는지 확인할 것\n"
            f"   · 정말 CPU 로 돌리려면 SIONNA2_ALLOW_CPU=1 (원장 오염은 본인 책임)")


# ═══ 계산 ═══════════════════════════════════════════════════════════════════
def run(a) -> None:
    from gpu import pick
    pick(verbose=False)
    # ⛔⛔**조기 건너뛰기(A14)를 철회했다** (2026-08-20 15:5x). 파일 이름을 별표로 좁혔더니
    #   `*` 가 _sw…·_d1/_d2·_rot…·_div…·_parts… 를 **전부 삼켜서**, 만들어야 할 샤드를
    #   «이미 있다» 고 오판했다. 실제 피해: 15:29~15:38 에 10 줄이 rc=0 «성공» 으로 넘어가고
    #   **샤드 32 칸**이 안 났다(≈20 워커-시간). 정확한 이름은 앙각 루프 안(`:492`·`:387`)이
    #   본 코드와 같은 조각으로 만들므로, 그 검사만 남긴다.
    #   ⇒ 되살리려면 **이름 조립을 함수 하나로 빼서 둘이 같은 코드를 부르게** 해야 한다.
    from articulated_fast import FastPoser, rotor_phases
    from drones import DRONES, DRONE_GROUP_MAT

    drone_key = str(getattr(a, "drone", "") or TJ.get("drone", "matrice4e"))
    spec = DRONES[drone_key]
    fp = FastPoser(spec, prop_scale=float(getattr(a, "prop_scale", 1.0) or 1.0),
                   frame_scale=float(getattr(a, "frame_scale", 1.0) or 1.0),
                   body_scale=float(getattr(a, "body_scale", 1.0) or 1.0))
    # ⭐자세 «표집률» 을 인자로 덮어쓴다 (2026-08-27 신설).
    #   ⛔--n-poses 는 «촘촘함» 이 아니라 «기록 길이» 다 — 자세 간격 dt=1/prf 는 n 과 무관하다.
    #   블레이드 통과당 자세 수를 늘리려면 이쪽을 올려야 한다. 안 주면 원장값이라 동작 불변.
    _prf_arg = float(getattr(a, "prf", 0.0) or 0.0)
    prf = _prf_arg if _prf_arg > 0 else float(TJ["prf_hz"])
    # ⭐자세 수는 인자로 덮어쓸 수 있다. 기본은 원장값이라 기존 동작과 같다.
    n = int(getattr(a, "n_poses", 0) or TJ["n"])
    #: ⭐방위는 인자로 덮어쓸 수 있다. 안 주면 원장값이라 기존 동작과 같다.
    _az_arg = float(getattr(a, "az_deg", float("nan")))
    az = float(TJ.get("az_deg", 0.0)) if np.isnan(_az_arg) else _az_arg
    # ⭐덱과 **같은** 로터 설정 — 축 하나만 바꾼다
    rpms = np.asarray(TJ["rpm_per_rotor"], float)
    # ⚠기체를 바꾸면 로터 수가 달라진다(s1000plus 는 8 개, 원장 배열은 4 개다).
    #   그때는 그 기체의 호버 회전수에 원장과 **같은 상대 산포**를 얹어 만든다 —
    #   산포를 버리면 네 로터가 완전 동기라 빗살이 인위로 깨끗해진다.
    n_rot = len(fp.dirs)
    if (getattr(a, "drone", "") and drone_key != TJ.get("drone", "matrice4e")) \
            or rpms.size != n_rot:
        base = float(getattr(spec, "hover_rpm", float(np.mean(rpms))))
        rel = rpms / np.mean(rpms)                       # 원장의 상대 산포
        rel = np.resize(rel, n_rot)                      # 로터 수에 맞춰 되풀이
        rpms = base * rel
        print(f"  ⚠로터 {n_rot} 개 — 원장 배열({rpms.size if rpms.size!=n_rot else 4} 개)과 달라 "
              f"{spec.key} 호버 {base:.0f} rpm 에 원장 산포를 얹어 만든다", flush=True)
    #: ⭐로터 프리셋 축(2026-08-18 신설) — 안 주면 **비트동일**(1 차원 상수 rpm 경로).
    #   주면 `src/rotor_dynamics.rpm_series()` 가 (n, n_rotors) rpm 열을 만들고
    #   `rotor_phases` 가 그것을 적분한다(θ=ω·t 가 성립 안 하므로 cumsum 경로).
    #   ⚠**프리셋은 원장 산포를 «더하는» 것이 아니라 «갈아끼운다»** — 프리셋 자신이
    #     로터별 정지 산포(static_offsets)를 만들기 때문에, 원장 산포를 남기면 두 번 센다.
    #     그래서 rpm0 는 원장 배열의 **평균**만 물려준다.
    rot_diag = None
    _rp = getattr(a, "rotor_preset", "")
    if _rp:
        from rotor_dynamics import get as _rget, rpm_series, initial_phase_deg
        _jit = _rget(_rp)
        _rng = np.random.default_rng(int(getattr(a, "rotor_seed", 0)))
        _rpm_t, rot_diag = rpm_series(float(np.mean(rpms)), n_rot, n, prf, _jit, _rng)
        _b = initial_phase_deg(n_rot, _jit, _rng, 360.0 / float(getattr(spec, "blades", 2)))
        ph = rotor_phases(np.arange(n) / prf, _rpm_t, fp.dirs, base_deg=_b, dt=1.0 / prf)
        print(f"  ⭐로터 프리셋 {_rp} — {rot_diag.get('mode')} · "
              f"정지 산포 σ {getattr(_jit, 'static_sigma', 0):.4f} · "
              f"흔들림 σ {getattr(_jit, 'wobble_sigma', 0):.4f} · 씨앗 "
              f"{int(getattr(a, 'rotor_seed', 0))}", flush=True)
    else:
        ph = rotor_phases(np.arange(n) / prf, rpms, fp.dirs)
    els = tuple(float(x) for x in a.els.split(',') if x.strip()) or ELS
    # ⭐**2026-09-05 — 이름 규약을 `:+.0f` 에서 `:+g` 로 바꿨다.**
    #   전 판은 «앙각은 정수여야 한다» 로 막았다(2026-08-20). 막은 이유는 물리가 아니라
    #   **이름이 잘려 −52.5 가 진짜 −52 샤드와 조용히 섞이는 것** 하나였고, 주석 자신이
    #   «소수 앙각이 정말 필요하면 이름 규약부터 바꿔야 한다» 고 적어 두었다.
    #   ⇒ 정면 창의 폭(N=3 이 az 0·el 0 한 점에서만 난다 — 그 점이 얼마나 좁은가)을
    #     재려면 0.05°~0.7° 가 필요하다. 그래서 규약을 바꾼다.
    #   ⭐**옛 샤드와 안 갈린다** — `:+g` 는 정수에서 `:+.0f` 와 **글자가 같다**
    #     (+0 · −15 · −30 · −90 · +15 전부 확인). 소수만 새로 살아난다(−0.5 → `_el-0.5_`).
    #   ⛔막던 것은 그대로 막는다 — 이름이 **겹치는지**를 직접 본다.
    _seen: dict = {}
    for e in els:
        k = f"{e:+g}"
        if k in _seen and abs(_seen[k] - e) > 1e-9:
            raise SystemExit(
                f"⛔ 앙각 {_seen[k]} 와 {e} 가 파일 이름에서 같은 `_el{k}_` 가 된다 — "
                f"두 칸이 한 칸으로 조용히 섞인다. 앙각을 갈라 주거나 이름 규약을 고칠 것.")
        _seen[k] = e
    idx = np.arange(a.shard, n, a.nshards)
    os.makedirs(SHD, exist_ok=True)
    # ⭐거리·깊이는 인자로 받는다. 기본값이면 꼬리표가 안 붙어 기존 샤드 이름과 같다.
    rng_m = float(getattr(a, "range_m", RANGE_M) or RANGE_M)
    # ⭐평면파는 range_m=None 으로 넘긴다(rcs_sbr:1090 «None 이면 평면파»).
    #   PathSolver 는 실제 기하를 쓰므로 이 스위치가 없다 — 우리 팔 전용이다.
    plane = bool(getattr(a, "plane_wave", False))
    # ⭐반송파도 인자로 받는다. 3.5 GHz 면 상수 FC 를 그대로 써서 기존 샤드와 비트동일하다.
    fc, tagfc = carrier(a)
    # ⭐셸/프롭 두께. 안 주면 (0,0,"") 라 재질을 아예 안 건드린다 → 기존 샤드와 비트동일.
    shell_mm, prop_mm, tagth = thickness(a)
    # ⭐⭐**메쉬 수리 꼬리표** (2026-08-17 신설). 2026-08-16 에 정본 수리(battery·i5)를 기본으로
    #   켰는데 파일 이름이 그대로라, 러너가 **옛 메쉬로 낸 샤드를 그대로 재사용**했다(작업이 3~4 초
    #   «건너뜀» 으로 끝나 재계산이 통째로 무효였다). 재질 두께(`tagth`)와 같은 규약으로 못 박는다:
    #     · 수리를 끄면(`MESH_FIX=none`) 꼬리표 없음 → 옛 샤드와 이름이 같아 비트동일.
    #     · 켜면 `_mfix<수리id 사전순>` — 어떤 판인지 이름만 봐도 읽힌다.
    from geom import mesh_fix_set as _mfs, blade_law_canon as _blc         # noqa: E402
    _fixes = sorted(_mfs())
    tagmf = "" if not _fixes else "_mfix" + "".join(_fixes)
    # ⭐날 법칙도 같은 규약 — 옛 판(legacy)이면 꼬리표 없음(비트동일), 정본이면 이름에 박힌다.
    _law = _blc()
    tagmf += "" if _law == "legacy" else "_bl" + _law.replace("_", "")

    tagr = ("" if not getattr(a, "drone", "") else f"_{drone_key}") \
        + ("" if abs(rng_m - RANGE_M) < 1e-9 else f"_r{rng_m:g}") \
        + ("" if not getattr(a, "n_poses", 0) else f"_n{n}") \
        + ("" if _prf_arg <= 0 else f"_prf{prf:g}") \
        + ("" if not int(getattr(a, "rep", 0)) else f"_rep{int(a.rep)}") \
        + ("" if not getattr(a, "env", "")
           else "_env" + str(a.env).replace(":", "-")) \
        + ("" if float(getattr(a, "env_scat", -1.0)) < 0
           else f"_S{float(a.env_scat):g}") \
        + ("" if abs(float(getattr(a, "prop_scale", 1.0) or 1.0) - 1.0) < 1e-9
           else f"_ps{float(a.prop_scale):g}") \
        + ("" if abs(float(getattr(a, "frame_scale", 1.0) or 1.0) - 1.0) < 1e-9
           else f"_fs{float(a.frame_scale):g}") \
        + ("" if abs(float(getattr(a, "body_scale", 1.0) or 1.0) - 1.0) < 1e-9
           else f"_bs{float(a.body_scale):g}") \
        + ("_pw" if plane else "") \
        + ("_det" if getattr(a, "det", False) else "") \
        + ("" if np.isnan(_az_arg) else f"_az{_az_arg:g}") \
        + ("" if not getattr(a, "rotor_preset", "") else f"_rot{a.rotor_preset}") \
        + ("" if not int(getattr(a, "rotor_seed", 0)) else f"s{int(a.rotor_seed)}") \
        + tagfc + tagth + tagmf

    if tagth and a.engine in ("ours", "ours_free", "ours_gpu"):
        raise SystemExit("⛔ --shell-mm/--prop-mm 은 PathSolver 팔 전용이다 — 우리 커널에는 "
                         "두께 개념이 없다(셸은 |Γ|=gamma_po 와 τ=1−|Γ|² 뿐이다). "
                         "그대로 두면 이름만 바뀌고 내용이 같은 샤드가 생겨 원장이 거짓말을 한다. "
                         "우리 커널 쪽 두께 감도가 필요하면 materials.MATERIALS['plastic']"
                         "['gamma_po'] 를 바꾸는 별도 축으로 설계할 것.")

    # ⭐격자 **위상 널** — 같은 격자를 반 칸 옆으로 옮겨 다시 잰다(칸 단위).
    #   안 주면 (0,0,"") 라 판을 아예 안 옮기고 꼬리표도 없다 → 기존 샤드와 비트동일.
    sh1, sh2, tagsh = parse_grid_shift(getattr(a, "grid_shift", ""))
    if tagsh and a.engine == "sionna":
        raise SystemExit("⛔ --grid-shift 는 우리 커널 전용이다 — PathSolver 는 표면 격자를 "
                         "안 쓴다(광선을 Rx 에서 쏘고 경로를 찾는다). 옮길 격자가 없다.")

    if a.engine in ("ours", "ours_free", "ours_gpu"):
        # ⛔⛔**우리 커널에는 --env 를 줄 수 없다** (2026-09-01).
        #  ■ 왜 — 아래 sbr_field 는 `mv`(자세 잡힌 **드론 메쉬**)만 받는다. 환경 부품은
        #    PathSolver 씬(build_scene)에만 붙으므로 여기까지 오지 않는다.
        #    그런데 파일 이름에는 `_env<이름>` 이 그대로 붙어서, **자유공간 데이터가
        #    실외 데이터 행세를 한다.** 실제로 그런 샤드 6 개가 났고 지웠다
        #    (ours 실외 vs 자유공간 상대차 1e−16 = float64 엡실론).
        #  ■ 되게 하려면 — 격자가 표적 bbox 로 정해지므로 지면 120×120 m 를 통째로 넣으면
        #    격자점이 9,409 → 7.5 억(79,483 배)이 된다.
        #    ⛔**«프레넬 존 조각을 주면 23 배로 감당된다» 는 철회한다**(2026-09-04,
        #    리포트 12 절 3 이 이 파일을 이름으로 지목했다). 그 23 배는 조각을 **제 자리가
        #    아니라 자기 원점에 홀로** 놓았을 때의 값이다. `grid_ref_from` 은 넘긴 메쉬
        #    **전부의 합집합 bbox** 로 격자를 잡으므로, 2×2 m 조각을 드론 메쉬에 합치면
        #    **1,388 배(el −30°) · 1,279 배(el −60°)** 다. 값을 정하는 것은 조각 크기가
        #    아니라 **조각과 드론 사이 거리**이고, 얼마면 되는지는 아직 **모른다.**
        #    그 설계 전에는 조용히 틀린 이름을 만들지 말고 **막는다.**
        if getattr(a, "env", ""):
            raise SystemExit(
                f"⛔ --engine {a.engine} 에는 --env 를 줄 수 없다 — 우리 커널은 "
                f"sbr_field(mv, ...) 로 **드론 메쉬만** 받아 환경이 도달하지 않는다. "
                f"그런데 파일 이름에는 _env{a.env} 가 붙어 자유공간 데이터가 실외 행세를 "
                f"한다. 되게 하려면 지면 조각을 메쉬에 합치는 설계가 먼저다 — 격자가 "
                f"합집합 bbox 로 정해지므로 온 지면은 79,483 배이고, ⛔«프레넬 조각이면 "
                f"23 배» 는 철회됐다(2×2 m 조각을 합치면 1,388 배다. 리포트 12 절 3).")
        from rcs_sbr import sbr_field, grid_ref_from, grid_ref_margin, grid_ref_shift
        gm = {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}
        #: ⭐격자 간격 λ/div. div 를 안 주면 규약값 12 라 기존 샤드와 비트동일하다.
        div = int(getattr(a, "div", 0) or DIV)
        #: ⚠간격은 **λ/div** 라 반송파를 옮기면 저절로 따라 줄어든다 — div 12 를 유지하면
        #   5.8 GHz 판도 같은 λ/12 규약이라 R16 격자 밴드를 그대로 인용할 수 있다.
        d = (2.998e8 / fc) / div
        probes = [fp.pose(ph[i]) for i in range(0, n, max(1, n // 64))]
        gref = grid_ref_from(probes, fc, spacing=d)
        # ⭐가림 대조군 — 동체의 **면만** 뺀다. 정점(mv.v)은 그대로 둬서 bbox·광선격자가
        #   같으므로 «동체가 막느냐» 하나만 다른 단일축이 된다(report15b 의 blade_free 규약).
        prop_only = (a.engine == "ours_free")
        # ⭐GPU 커널 — 옛 커널(rcs_sbr)을 **그대로 둔 채** 나란히 쓴다.
        #   산출 이름이 `ours_gpu…` 로 갈리므로 두 원장이 절대 안 섞인다.
        #   ⛔K=1 로 못 박혀 있다(적대적 검증: K≥2 는 값이 --nshards 를 탄다).
        _gpu = None
        if a.engine == "ours_gpu":
            if a.ptd:
                raise SystemExit("⛔ --engine ours_gpu 는 PTD 를 아직 안 옮겼다 — "
                                 "--ptd 는 --engine ours 로 돌릴 것.")
            from rcs_sbr_gpu import BatchSBR
        if prop_only:
            keep = np.asarray(fp.g) == "prop"
            f_keep, g_keep = fp.f[keep], fp.g[keep]
        for el in els:
            tagd = ("_ptd" if a.ptd else "") + tagr \
                + ("" if not getattr(a, "div", 0) else f"_div{div}") + tagsh
            f = f"{SHD}/{a.engine}{tagd}_el{el:+g}_{a.shard:02d}.npz"
            if getattr(a, "dry_run", False):
                print(f"  [dry] {'있음' if os.path.exists(f) else '없음'}  "
                      f"{os.path.basename(f)}", flush=True); continue
            if os.path.exists(f) and not a.overwrite:
                print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
            u = los(az, el)
            #: ⭐가로축 (e1,e2) 는 û 가 정하므로 판을 **앙각마다** 옮긴다. 크기(d·n·Rout)는
            #   그대로고 원점만 움직인다 — 안 주면 gref 그 객체를 그대로 쓴다(비트동일).
            gref_el = grid_ref_shift(gref, (sh1, sh2), u) if tagsh else gref
            if tagsh:
                mgn = min(grid_ref_margin(m_, u, gref_el, spacing=d)["margin_min_m"]
                          for m_ in probes)
                print(f"  격자 위상 널 el{el:+g}: {sh1:g}·{sh2:g} 칸 = "
                      f"{np.hypot(sh1, sh2)*d*1e3:.2f} mm 이동 · n={gref_el.n} (안 바뀜) · "
                      f"남은 덮개 여유 {mgn*1e3:+.2f} mm ({mgn/d:+.2f} 칸)", flush=True)
            E = np.zeros(idx.size, complex); t0 = time.time()
            if a.engine == "ours_gpu":
                # ⭐GPU 커널은 씬·광선다발을 **앙각마다 한 번** 짓고 자세만 갈아 넣는다.
                #   (광선은 보는 방향에만 매인다 — 생산 루프는 앙각 고정이라 사실상 공짜)
                _gpu = BatchSBR(fp.pose(ph[int(idx[0])]), gm, fc, K=1, spacing=d,
                                grid_ref=gref_el, penetrate=True, angle_gamma=True)
            for j, i in enumerate(idx):
                mv = fp.pose(ph[int(i)])
                if prop_only:
                    mv.f, mv.g = f_keep, g_keep          # 정점은 그대로 — bbox 보존
                if _gpu is not None:
                    E[j] = _gpu.field([mv], u, range_m=(None if plane else rng_m))[0]
                else:
                    E[j] = sbr_field(mv, gm, fc, u, spacing=d, grid_ref=gref_el,
                                     range_m=(None if plane else rng_m), ptd=bool(a.ptd))
                if j and j % 128 == 0:
                    e = time.time() - t0
                    print(f"    el{el:+g} sh{a.shard}: {j}/{idx.size} "
                          f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)
            np.savez_compressed(f, idx=idx, E=E,
                                meta=np.array([el, a.shard, a.nshards, n, prf,
                                               time.time() - t0]),
                                # ⭐출처 — 우리 팔은 광선 예산·깊이가 없으므로 NaN 으로 둔다.
                                #   평면파는 range_m 을 NaN 으로 적어 «무한거리» 를 표시한다.
                                cfg=np.array([np.nan if plane else rng_m,
                                              np.nan, np.nan, 0.0]))
            print(f"  ✅ {a.engine} el{el:+g} sh{a.shard} · {idx.size} 자세 · "
                  f"{(time.time()-t0)/60:.1f}분", flush=True)
        return

    # ── Sionna PathSolver ───────────────────────────────────────────────────
    import report15_probe as RP
    require_cuda_variant()          # ⭐GPU 가 안 열렸으면 여기서 멈춘다
    from drones import drone_colors
    # ⭐셸 두께 정정 — **켰을 때만** 재질에 두께를 물린다(안 켜면 materials 가 예전처럼
    #   thickness 를 아예 안 넘겨 Sionna 기본 0.1 m → 옛 샤드와 비트동일).
    #   재질은 아래 build_scene 이 자세마다 새로 만드므로 여기서 한 번 걸어 두면 전부 적용된다.
    if tagth:
        import materials as _M
        _st = _M.set_thickness_mm(shell=(shell_mm or None), prop=(prop_mm or None))
        print("  ⭐두께 정정: " + " · ".join(f"{k} {v*1e3:g} mm" for k, v in _st.items())
              + "  (안 준 비-ITU 재질은 Sionna 기본 100 mm 그대로 — carbon 은 표피깊이 "
                "0.155 mm 라 두께를 안 탄다)", flush=True)
    spp = int(a.spp) if a.spp else rule_spp(rng_m)
    # ⭐깊이는 물리 스위치와 분리한다. --max-depth 를 안 주면 옛 규칙 그대로다.
    mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else (3 if a.physics else 1)
    # ⭐--only 는 스위치 하나만 켠다(단일축 귀속). --physics 와 배타적이다.
    only = str(getattr(a, "only", "") or "")
    #: 확산 반사 — 스윕의 상수였다(켬). 순정 기본값·--sw 팔만 바꾼다.
    diffuse = True
    swbits = str(getattr(a, "sw", "") or "").upper()
    if swbits:
        import re as _re
        m = _re.fullmatch(r"R([01])D([01])E([01])F([01])", swbits)
        if not m:
            raise SystemExit(f"⛔ --sw 형식: R<0|1>D<0|1>E<0|1>F<0|1> (받은 값 {swbits!r})")
        r_, d_, e_, f_ = (bool(int(x)) for x in m.groups())
        sw = dict(refraction=r_, diffraction=d_, edge_diffraction=e_)
        diffuse = f_
        mdep = int(a.max_depth) if getattr(a, "max_depth", 0) else 1
    elif getattr(a, "stock", False):
        sw = dict(refraction=True, diffraction=False, edge_diffraction=False)
        mdep = 3
        diffuse = False
    elif only:
        sw = dict(refraction=(only == "refr"), diffraction=(only == "diffr"),
                  edge_diffraction=(only == "edge"))
        mdep = 3 if only == "depth3" else 1
    else:
        sw = dict(refraction=bool(a.physics), diffraction=bool(a.physics),
                  edge_diffraction=bool(a.physics))
    cols = drone_colors(spec)
    for el in els:
        tagp = (("" if not a.spp else f"_p{a.spp}") + ("_phys" if a.physics else "")
                + (f"_sw{swbits}" if swbits else "")
                + ("_stockdef" if getattr(a, "stock", False) else "")
                + (f"_only{only}" if only else "")
                + (f"_parts{str(a.parts).replace(',', '').replace('-', 'no')}"
                   if getattr(a, "parts", "") else "")
                + tagr + ("" if not getattr(a, "max_depth", 0) else f"_d{mdep}"))
        # ⭐--inmem 은 정점·면이 비트 동일이라 꼬리표를 **안 붙인다**(붙이면 옛 샤드를 못 잇는다).
        #   ⛔대신 아래 cfg 메타에 기록해 «어느 길로 났는지» 를 남긴다.
        f = f"{SHD}/sionna{tagp}_el{el:+g}_{a.shard:02d}.npz"
        if getattr(a, "dry_run", False):
            print(f"  [dry] {'있음' if os.path.exists(f) else '없음'}  "
                  f"{os.path.basename(f)}", flush=True); continue
        if os.path.exists(f) and not a.overwrite:
            print(f"  건너뜀 {os.path.basename(f)}", flush=True); continue
        E = np.zeros(idx.size, complex); npaths = np.zeros(idx.size, int)
        # ⭐**돌려받은 경로 수를 따로 적는다**(2026-09-02). `npaths` 는 NO_OBJ 마스크를
        #   통과해 «남은» 수라, 경로가 하나 빠졌을 때 그것이 **PathSolver 가 못 찾은 것**인지
        #   **우리 마스크가 버린 것**인지 서명이 똑같아 못 가른다. 두 수를 다 적으면 갈린다.
        nret = np.zeros(idx.size, int)
        #: ⭐**같은 줄이 여러 번 적히는 자리**(2026-09-03).
        #  정면(el 0°)에서 목록에 **완전히 같은 항목**이 여러 번 들어온다 — 같은 물체·같은
        #  삼각형·같은 진폭·같은 지연. 결맞음 합이라 그 수만큼 곱해진다
        #  (matrice4e 3 · mini5pro 2 · mavic4pro 4 — outputs/copies_id_0903.json).
        #  ⛔어느 쪽이 옳은지 우리는 모른다 — 그래서 **두 값을 다 적는다.**
        #    E        지금까지 하던 대로 목록을 그대로 다 더한 값
        #    E_dedup  같은 줄을 한 번만 센 합
        #    n_dup    그렇게 지워진 줄 수 (0 이면 중복이 없었다)
        E_dedup = np.zeros(idx.size, complex)
        n_dup = np.zeros(idx.size, int)
        t0 = time.time()
        # ⭐A3 — 솔버 객체를 자세마다 새로 만들지 않는다(인자가 루프 상수다).
        _solver = RP.rt.PathSolver()
        # ⭐인메모리 경로 — 자세가 바뀌어도 안 변하는 것(면·그룹·재번호표)을 한 번만 짓는다.
        #   `FastPoser` 가 자세마다 **같은** f·g 객체를 돌려주므로 구조적으로 안전하다
        #   (`src/articulated_fast.py:120-126, 147`).
        _lay = _mesh_cache = _par_cache = None
        if getattr(a, "inmem", False):
            from mesh_inmem import InMemGroups
            _mv0 = fp.pose(ph[int(idx[0])])
            _lay = InMemGroups(_mv0.f, _mv0.g)
            # ⭐A2 — `mi.Mesh` 를 자세마다 새로 만들지 않는다. 면 연결은 안 변하므로
            #   **한 번 만들고 정점만 갈아 끼운다**. 이름도 고정한다(옛 코드의 `{i%2}` 는
            #   OBJ 파일이 두 벌 번갈아 쓰이던 시절의 유물이라 인메모리엔 필요 없다).
            _mesh_cache, _par_cache = {}, {}
            for g in _lay.names:
                _m, _pp = _lay.make_mesh(RP.mi, _mv0.v, g, name=f"{spec.key}_{g}")
                _mesh_cache[g], _par_cache[g] = _m, _pp
        for j, i in enumerate(idx):
            i = int(i)
            if _lay is not None:
                mv = fp.pose(ph[i])
                paths_obj = {g: None for g in _lay.names}
                for g in _lay.names:
                    _lay.update_vertices(RP.mi, _par_cache[g], mv.v, g)
                mi_meshes = _mesh_cache
                dd = None
            else:
                mi_meshes = None
                m = fp.pose(ph[i]).to_mesh()
            # ⭐프로세스마다 다른 폴더를 쓴다 (2026-08-11 결함 정정).
            #   전에는 이름에 앙각·샤드만 들어 있어서, **광선 예산이 다른 두 실행**을
            #   동시에 띄우면 같은 폴더를 썼다. 자세마다 drop_scratch 로 지우므로
            #   한쪽이 읽는 중에 다른 쪽이 지워 «OBJ file not found» 로 터졌다
            #   (el 0 사다리에서 샤드 7 개 손실). PID 를 넣으면 어떤 동시 실행과도 안 겹친다.
                dd = os.path.join(RP.SCRATCH,
                                  f"elev_{spec.key}_e{el:+g}s{a.shard}"
                                  f"_p{spp}_pid{os.getpid()}_{i%2}")
                paths_obj = m.write_obj_per_group(dd, spec.key)
            if getattr(a, "parts", ""):
                ps_ = str(a.parts)
                if ps_.startswith("-"):                  # -prop → prop 만 뺀 나머지 전부
                    dropg = set(ps_[1:].split(","))
                    paths_obj = {g: p for g, p in paths_obj.items() if g not in dropg}
                else:
                    keepg = set(ps_.split(","))
                    paths_obj = {g: p for g, p in paths_obj.items() if g in keepg}
                if not paths_obj:
                    raise SystemExit(f"⛔ --parts {a.parts}: 남는 그룹이 없다")
            parts = [RP.Part(name=(f"{spec.key}_{g}" if mi_meshes is not None
                                   else f"{spec.key}_{g}_{i%2}"), obj=(p or ""),
                             mat_key=DRONE_GROUP_MAT[g][0], color=cols[g],
                             mi_mesh=(None if mi_meshes is None else mi_meshes[g]))
                     for g, p in paths_obj.items()]
            # ⭐실외 환경 축 — 주면 드론 부품 뒤에 환경을 얹는다.
            #   ⭐`--env sionna:<이름>` 이면 우리 메쉬 대신 **엔비디아 기본 씬**을 쓴다
            #     (simple_street_canyon · munich · etoile · florence · san_francisco …).
            #     그때는 드론을 그 씬 **안에** 넣는다 — 씬을 먼저 열고 부품을 edit(add) 한다.
            #   ⛔이건 **PathSolver 씬**에만 붙는다 — 아래 우리 커널 분기는 sbr_field 에
            #     드론 메쉬만 넘기므로 환경이 도달하지 않는다. 그래서 --engine ours 에
            #     --env 를 주면 위에서 거부한다(2026-09-01).
            _envn = getattr(a, "env", "")
            _ctr = (0.0, 0.0, 0.0)
            if _envn.startswith("sionna:"):
                sc, _ctr = build_scene_builtin(RP, parts, _envn.split(":", 1)[1], fc)
            else:
                if _envn:
                    parts = parts + env_parts(RP.Part, _envn)
                sc = RP.build_scene(parts, fc=fc)
            #: ⭐거칠기 — 환경 재질의 **산란계수 S** 를 갈아 끼운다(ITU-R P.2040 계열).
            #  S=0 이면 완벽한 거울(정반사가 한 방향으로 몰린다), S→1 이면 확산으로 흩어진다.
            #  ⚠우리 콘크리트 기본값이 **S=0.0**(src/materials.py:69·72)이라 지금 지면은
            #    거울이다 — 실제 흙·풀·자갈은 그보다 거칠다. 그 차이를 재는 축이다.
            _S = float(getattr(a, "env_scat", -1.0))
            if _envn and _S >= 0.0:
                _n = 0
                for _nm, _ob in sc.objects.items():
                    if _envn.startswith("sionna:") or str(_nm).startswith("env_"):
                        try:
                            _ob.radio_material.scattering_coefficient = _S
                            _n += 1
                        except Exception:
                            pass
                if j == 0 and el == els[0]:
                    print(f"  ⭐환경 거칠기 S={_S:g} — 물체 {_n} 개에 걸었다", flush=True)
            RP.place(sc, center=_ctr, az=az, el=el, rng=rng_m, baseline=0.0)
            p = _solver(
                sc, los=True, specular_reflection=True, diffuse_reflection=diffuse,
                # ⭐--physics 면 굴절·회절·모서리회절을 전부 켠다.
                #   깊이는 --max-depth 로 따로 준다(안 주면 옛 규칙 3/1).
                max_depth=mdep, **sw,
                samples_per_src=spp, max_num_paths_per_src=RP.MAX_PATHS, seed=1)
            try:
                aa, tau, _, O = RP.unpack(p, want_doppler=False)
            except ValueError:
                aa = np.zeros(0)
            if aa.size:
                hit = (O != RP.NO_OBJ).any(axis=0) if O.size else np.zeros(aa.size, bool)
                _t = aa[hit] * np.exp(-1j * 2 * np.pi * fc * tau[hit])
                if getattr(a, "det", False):
                    # ⭐순서를 못 박는다 — PathSolver 가 돌려주는 경로 **순서**가 매번 달라서
                    #   같은 코드로도 합이 갈린다(실측 4 판 4 종류). 정렬하면 고정된다.
                    # ⚠지연만으로는 모자라다 — **지연이 똑같은 경로 쌍**이 있으면 그 둘의
                    #   앞뒤를 못 가른다(실측: 512 자세 중 1 개가 마지막 비트에서 갈렸다).
                    #   그래서 지연 → 실수부 → 허수부 순으로 열쇠를 겹쳐 완전히 결정한다.
                    _hv = _t
                    _ord = np.lexsort((_hv.imag, _hv.real, tau[hit]))
                    _t = _t[_ord]
                E[j] = complex(np.sum(_t))
                npaths[j] = int(hit.sum())
                nret[j] = int(aa.size)          # ⭐마스크 «전» 수
                #: ⭐같은 줄을 한 번만 센 합 — 열쇠는 «물체·삼각형·진폭·지연» 넷이다.
                #  ⚠삼각형까지 넣는 까닭 — 대칭 기하에서 **서로 다른 경로**가 우연히 같은
                #    진폭·지연을 가질 수 있다. 그것까지 지우면 진짜 신호를 버린다.
                try:
                    _pr = np.asarray(p.primitives)[:, 0, 0, :]
                except Exception:                              # noqa: BLE001
                    _pr = None
                _ah = aa[hit]
                _cols = [_ah.real, _ah.imag, tau[hit]]
                if O.size:
                    _cols += [O[d][hit].astype(float) for d in range(O.shape[0])]
                if _pr is not None and _pr.size:
                    _cols += [_pr[d][hit].astype(float) for d in range(_pr.shape[0])]
                _u, _first = np.unique(np.stack(_cols, axis=1), axis=0, return_index=True)
                E_dedup[j] = complex(np.sum(_t[np.sort(_first)]))
                n_dup[j] = int(_t.size - _first.size)
            if dd is not None:
                RP.drop_scratch(dd)
            if j and j % 128 == 0:
                e = time.time() - t0
                print(f"    el{el:+g} sh{a.shard}: {j}/{idx.size} "
                      f"{e/60:.1f}분 ETA {(idx.size-j)/j*e/60:.1f}분", flush=True)
        np.savez_compressed(f, idx=idx, E=E, npaths=npaths, nret=nret,
                            E_dedup=E_dedup, n_dup=n_dup,
                            meta=np.array([el, a.shard, a.nshards, n, prf,
                                           time.time() - t0, spp]),
                            # ⭐출처 — meta 모양은 안 바꾼다(기존 병합 코드 보호)
                            cfg=np.array([rng_m, mdep, spp,
                                          float(bool(a.physics)),
                                          float(sw["refraction"]),
                                          float(sw["diffraction"]),
                                          float(sw["edge_diffraction"])]))
        print(f"  ✅ sionna el{el:+g} sh{a.shard} · {idx.size} 자세 · "
              f"{(time.time()-t0)/60:.1f}분", flush=True)


# ═══ 병합·분석 ══════════════════════════════════════════════════════════════
def f_tip_at(el_deg: float, arm: str = "") -> float:
    import sys as _s; _s.path.insert(0, f"{ROOT}/src")
    from drones import DRONES
    # ⚠병합·분석 경로 — 팔 이름에 기체 태그(_mini5pro 등)가 있으면 **그 기체**의 제원을
    #   쓴다. 전에는 원장 기본 기체(matrice4e)로 일괄 계산해 기체 팔의 f_tip 이 틀렸다.
    key = TJ.get("drone", "matrice4e")
    for k in DRONES:
        if f"_{k}_" in arm or arm.endswith(f"_{k}"):
            key = k
            break
    spec = DRONES[key]
    # ⚠반송파도 팔 이름에서 읽는다 — 한 원장에 3.5 GHz 팔과 5.8 GHz 팔이 함께 살기 때문이다.
    #   꼬리표가 없으면 규약값 FC 라 옛 팔의 값은 한 비트도 안 바뀐다.
    lam = 2.998e8 / carrier_of(arm)
    R = spec.prop_dia_mm / 2000.0
    # ⛔**프롭 배율 꼬리표를 읽는다** (2026-08-31 적대 검증이 잡았다).
    #   전에는 `_ps<k>` 를 안 봐서 네 배율이 전부 x1.0 대역(446~1273 Hz)으로 읽혔다 —
    #   원장 18 행의 f_tip_hz 가 모두 같은 값이었다. 대역이 배율을 안 따라가면
    #   「프롭을 키웠는데 박자가 안 는다」가 **잣대 탓인지 물리 탓인지 못 가른다.**
    #   ⚠f_tip 은 팁속도라 **프롭 지름에만** 비례한다 — frame/body 배율은 안 걸린다.
    _m = re.search(r"_ps([0-9.]+)", arm)
    if _m:
        try:
            R *= float(_m.group(1))
        except ValueError:
            pass
    f_rev = float(getattr(spec, "hover_rpm", 6000.0)) / 60.0
    return 2.0 * (2 * np.pi * f_rev * R) / lam * np.cos(np.radians(el_deg))


def analyse() -> None:
    from md_mapstyle import auto_periods, flash_spec
    prf, ffl = float(TJ["prf_hz"]), float(TJ["f_flash_hz"])
    per = auto_periods(prf, ffl)
    ft_deck = float(TJ["f_tip_hz"])                 # −15° 의 f_tip (덱 대역의 기준)

    # ⭐**같은 STFT 를 두 번 돌지 않는다** (2026-08-20). 행마다 `track` 과 `fixed` 두 번
    #   부르는데 인자(E·prf·ffl·per)가 **완전히 같다** — 대역(lo·hi)만 다르고 그건 STFT
    #   **뒤에만** 쓰인다. 병합 1 회에 −16~27 s. ⛔값은 안 바뀐다(같은 입력 → 같은 출력).
    _stft_cache = {}

    def _stft(E):
        k = id(E)
        v = _stft_cache.get(k)
        if v is None:
            v = flash_spec(np.asarray(E, complex), prf, ffl, per)
            _stft_cache.clear()          # 한 행만 붙잡는다 — 메모리가 안 늘게
            _stft_cache[k] = v
        return v

    def band_metrics(E, lo, hi):
        f, t, S, _ = _stft(E)
        b = (np.abs(f) >= lo) & (np.abs(f) <= hi)
        if b.sum() < 2:
            return dict(n_bins=int(b.sum()), beat_hz=None, h1_over_h2_db=None,
                        band_power_db=None)
        g = (S[b, :] ** 2).sum(axis=0)
        pw = 10 * np.log10(g.mean())
        g = g - g.mean()
        dt = float(t[1] - t[0]); m = len(g)
        A = np.abs(np.fft.rfft(g * np.hanning(m), n=64 * m))
        fr = np.fft.rfftfreq(64 * m, dt)
        if A.max() <= 0:
            return dict(n_bins=int(b.sum()), beat_hz=None, h1_over_h2_db=None,
                        band_power_db=round(pw, 2))
        A = A / A.max()
        sel = (fr >= 40) & (fr <= 400)
        i0 = int(np.where(sel)[0][0]); i = int(np.argmax(A[sel])) + i0
        y0, y1, y2 = A[i - 1], A[i], A[i + 1]
        den = y0 - 2 * y1 + y2
        pk = fr[i] + (0.5 * (y0 - y2) / den if den else 0.0) * (fr[1] - fr[0])

        def pkdb(f0, h=18.0):
            w = (fr >= f0 - h) & (fr <= f0 + h)
            return 20 * np.log10(A[w].max()) if w.any() else np.nan
        return dict(n_bins=int(b.sum()), beat_hz=round(float(pk), 2),
                    h1_over_h2_db=round(float(pkdb(ffl) - pkdb(2 * ffl)), 2),
                    band_power_db=round(pw, 2))

    rows, series = [], {}
    # ⭐샤드 폴더에 실제로 있는 팔을 전부 집는다 — --spp 로 낸 것은
    #   sionna_p250000000_... 처럼 예산 꼬리표가 붙어 이름이 고정되지 않는다.
    # ⭐**샤드 폴더를 한 번만 훑는다** (2026-08-20). 전에는 팔×앙각마다 glob 를 다시 돌아
    #   **3,146 회**(그중 2,380 회가 헛방)였다 — 7.87 s → 5.6 ms (1,400 배).
    #   ⛔파일 목록과 정렬 순서는 옛 `sorted(glob(...))` 와 **완전히 같다**(766 칸 0 불일치 확인).
    _all = sorted(glob.glob(f"{SHD}/*_el*.npz"))
    _by = {}
    for _f in _all:
        _b = os.path.basename(_f)
        _m = re.search(r"^(.*)_el([+-]\d+(?:\.\d+)?)_\d+\.npz$", _b)
        if _m:
            _by.setdefault((_m.group(1), float(_m.group(2))), []).append(_f)
    engines = sorted({k[0] for k in _by},
                     key=lambda e: (not e.startswith("ours"), e))
    # ⭐앙각도 **디스크에서 읽는다** — 상수 ELS 만 돌면 −52·−68·−82 처럼 규약 밖 각도로
    #   돌린 완결 칸이 영원히 원장에 못 들어온다(2026-08-16 에 34 칸이 그렇게 묶여 있었다).
    els_on_disk = sorted({k[1] for k in _by}, reverse=True)
    for eng in engines:
        for el in (els_on_disk or ELS):
            fs = _by.get((eng, float(el)), [])       # ⭐한 번 훑어 만든 사전에서 꺼낸다
            if not fs:
                continue
            E = None; secs = 0.0; npa = []; cfg = None
            for f in fs:
                z = np.load(f); ii = z["idx"].astype(int)
                if E is None:
                    E = np.zeros(int(np.asarray(z["meta"], float)[3]), complex)
                E[ii] = z["E"]; secs += float(np.asarray(z["meta"], float)[5])
                if "npaths" in z: npa.append(z["npaths"])
                # ⭐행마다 자기 판을 싣는다 — 한 원장에 10 m 와 15 m 가 함께 살기 때문.
                #   옛 샤드에는 cfg 가 없으므로 모듈 기본값으로 채운다.
                if cfg is None and "cfg" in z:
                    cfg = np.asarray(z["cfg"], float)
            miss = int((E == 0).sum())
            ft = f_tip_at(el, eng)
            series[f"{eng}/el{el:+g}"] = E
            if cfg is not None:
                # ⚠우리 팔은 깊이·광선 예산 개념이 없어 NaN 으로 적는다 → None 으로 읽는다.
                #   평면파 팔은 range_m 도 NaN 이다(무한거리).
                def _f(v):
                    return None if (v is None or np.isnan(v)) else float(v)

                def _i(v):
                    return None if (v is None or np.isnan(v)) else int(v)

                prov = dict(range_m=_f(cfg[0]), max_depth=_i(cfg[1]),
                            spp=_i(cfg[2]), physics=bool(cfg[3]))
                if prov["range_m"] is None:      # 평면파 — 이름의 _r 꼬리표를 쓴다
                    mr = re.search(r"_r(\d+(?:\.\d+)?)", eng)
                    prov["range_m"] = float(mr.group(1)) if mr else RANGE_M
                    prov["illumination"] = "plane wave (infinite range)"
            else:
                # cfg 가 없는 샤드 — **이름에서 읽는다.** 우리 팔 분기는 cfg 를 안 남기고,
                # 2026-08-12 이전 샤드도 없다. 거리는 _r<N> 꼬리표가 진실이다.
                m_spp = re.search(r"_p(\d+)", eng)
                m_rng = re.search(r"_r(\d+(?:\.\d+)?)", eng)
                rng = float(m_rng.group(1)) if m_rng else RANGE_M
                prov = dict(range_m=rng,
                            max_depth=(3 if eng.endswith("_phys") else 1),
                            spp=(int(m_spp.group(1)) if m_spp else rule_spp(rng)),
                            physics=eng.endswith("_phys"))
                if eng.startswith("ours"):
                    # 우리 커널은 광선 예산·반사 깊이 개념이 없다 — 격자로 푼다
                    prov.update(max_depth=None, spp=None, physics=None)
            #: ⭐방위·격자 축은 cfg 에 자리가 없다(옛 샤드와 호환을 지킨다) — 이름에서 읽는다.
            m_sw = re.search(r"_sw(R[01]D[01]E[01]F[01])", eng)
            if m_sw:
                b = m_sw.group(1)
                prov["switches"] = dict(refraction=b[1] == "1", diffraction=b[3] == "1",
                                        edge_diffraction=b[5] == "1", diffuse=b[7] == "1")
            m_az = re.search(r"_az(-?\d+(?:\.\d+)?)", eng)
            m_div = re.search(r"_div(\d+)", eng)
            prov["az_deg"] = float(m_az.group(1)) if m_az else float(TJ.get("az_deg", 0.0))
            prov["grid_div"] = int(m_div.group(1)) if m_div else (
                DIV if eng.startswith("ours") else None)
            #: ⭐격자 위상 널 — 격자를 **몇 칸 옆으로 옮겨** 잰 판인가(칸 단위, [e1, e2]).
            #   꼬리표가 없으면 원판이라 [0,0] 이다. PathSolver 팔에는 격자가 없어 None.
            m_sh = re.search(r"_shift(-?\d+(?:\.\d+)?)(?:x(-?\d+(?:\.\d+)?))?", eng)
            prov["grid_shift_cells"] = (
                [float(m_sh.group(1)), float(m_sh.group(2) or m_sh.group(1))] if m_sh
                else ([0.0, 0.0] if eng.startswith("ours") else None))
            #: ⭐셸·프롭 두께 [mm] — 꼬리표가 없는 PathSolver 팔은 **100 mm**(Sionna 기본값)다.
            #   그 100 은 «안 정한 값» 이 아니라 **실제로 그 판 위에서 계산된 값**이라 반드시
            #   싣는다(정정 이전 모든 sionna 수치에 붙는 단서다). 우리 커널에는 두께가 없다 → None.
            m_th = re.search(r"_shell(\d+(?:\.\d+)?)mm", eng)
            m_tp = re.search(r"_prop(\d+(?:\.\d+)?)mm", eng)
            _ours = eng.startswith("ours")
            prov["shell_mm"] = None if _ours else (
                float(m_th.group(1)) if m_th else 100.0)
            prov["prop_mm"] = None if _ours else (
                float(m_tp.group(1)) if m_tp else 100.0)
            #: ⭐반송파 — 꼬리표가 없으면 규약값 3.5 GHz. f_tip 은 이미 이 값으로 잡혀 있다.
            fc_arm = carrier_of(eng)
            prov["fc_hz"] = fc_arm
            # ⭐«덱 고정 대역» 은 −15°·3.5 GHz 에서 잰 자리다. 반송파를 옮긴 팔에는 **λ 비로
            #   늘려서** 같은 물리적 자리를 가리키게 한다(R23② 판정 규약). 3.5 GHz 면 ×1.0 이라
            #   옛 값과 비트동일하다.
            ftd = ft_deck if fc_arm == FC else ft_deck * (fc_arm / FC)
            rows.append(dict(
                engine=eng, el_deg=el, cos_el=round(float(np.cos(np.radians(el))), 4),
                f_tip_hz=round(ft, 1), n_poses=len(E), n_missing=miss,
                seconds=round(secs, 1), **prov,
                npaths_median=int(np.median(np.concatenate(npa))) if npa else None,
                # ⛔**결측 자세(0)를 평균에서 뺀다** (2026-08-20 정정). 예전에는 안 채워진
                #   자세의 0 이 그대로 평균에 들어가 레벨을 낮췄다 — 원장 766 행 중 **52 행**이
                #   틀렸고 최악은 **−24.08 dB** 였다. `n_missing` 은 이미 세고 있었는데
                #   평균만 그걸 안 봤다. (정정 기록: docs/RETRACTION_LOG.md)
                level_db=round(float(20 * np.log10(
                    (np.abs(E[E != 0]).mean() if miss and (E != 0).any()
                     else np.abs(E).mean()) + 1e-300)), 2),
                # ⭐(a) 앙각마다 대역을 다시 잡는다 — 정본
                track=band_metrics(E, 0.35 * ft, max(ft, 1e-6)),
                # (b) 덱의 −15° 대역 고정 — 어디서 무너지나 (반송파를 옮긴 팔은 λ 비로 늘린다)
                fixed=band_metrics(E, 0.35 * ftd, ftd)))

    if not rows:
        raise SystemExit(f"⛔ {SHD} 에 샤드가 없다")
    # ⭐부호 표식 — 샤드가 이미 정정본(R28)이므로 정정기가 다시 손대면 안 된다.
    # ⭐압축을 뺀다 — 2.9 s 아끼고 파일은 76.6 → 87.5 MiB (비트동일)
    np.savez(OUTN, phase_sign_v2=np.array([1], np.int8), **series)
    json.dump({"_meta": {
        "generator": "benchmark/elevation_sweep_md.py",
        "question_ko": "거리 대신 앙각을 바꾸면 마이크로도플러가 어떻게 변하나",
        # ⛔이 원장은 **거리가 하나가 아니다.** 행마다 range_m 을 실어 두었으니
        #   그 열을 읽어라. 아래 두 키는 옛 판(10 m)의 기본값일 뿐이다.
        "range_m_legacy_default": RANGE_M,
        "range_note_ko": ("⭐이 원장에는 **여러 거리·설정의 팔이 함께** 산다. 거리·깊이·"
                          "광선수·물리 여부는 **행마다** `range_m · max_depth · spp · "
                          "physics` 열에 실려 있다 — 그 열을 읽어라. "
                          "10 m 는 원거리장 경계 2D²/λ ≈ 14.08 m 의 **안쪽**(근거리장)이고, "
                          "15 m 는 **밖**이다. 두 거리의 값을 나란히 놓을 때는 그 사실을 "
                          "반드시 적는다."),
        "ranges_present_m": sorted({r["range_m"] for r in rows}),
        # ⭐재설계판(2026-08-13)의 **머리 판** — 리포트 16 이 이 값을 쓴다.
        #   원장에 10 m 옛 팔이 함께 살지만, 이 권이 서술하는 실험은 15 m 다.
        "range_m_primary": 15.0,
        "primary_note_ko": ("리포트 16 이 서술하는 판은 **15 m** 다 — 원거리장 경계 "
                            "2D²/λ ≈ 14.08 m 의 **밖**이다. 같은 원장에 10 m 옛 팔이 "
                            "함께 있으니 행의 `range_m` 열로 갈라 읽는다."),
        "ours_illumination": "spherical wave at 15 m",
        # ⭐리포트 16 이 «왜 이 거리인가» 를 인용하는 자리. 재설계판 기준으로 다시 쓴다.
        "range_why_ko": ("⭐2026-08-13 재설계 — 거리를 **15 m** 로 옮겼다. 원거리장 경계 "
                         "2D²/λ ≈ 14.08 m(메쉬 3D 대각 0.78 m 기준)의 **밖**이라, 옛 10 m 판이 "
                         "받던 «근거리장 판» 이라는 단서가 필요 없다. 우리 커널은 그 거리의 "
                         "구면파로 조명하고 PathSolver 는 실제 기하를 쓴다. ⚠같은 원장에 "
                         "10 m 옛 팔이 함께 사니 행의 `range_m` 열로 갈라 읽는다."),
        "sionna_spp_primary": 4_000_000_000,
        # ⛔이 원장은 **반송파도 하나가 아니다.** 행마다 fc_hz 를 실었으니 그 열을 읽어라.
        "fc_hz": FC,
        "fc_note_ko": ("⭐`fc_hz` 는 옛 판(3.5 GHz)의 **기본값**일 뿐이다 — 반송파는 **행마다** "
                       "`fc_hz` 열에 있다. λ 가 바뀌면 f_tip·격자 간격·원거리장 경계가 함께 "
                       "바뀐다(격자는 λ/12 규약을 유지하므로 칸이 촘촘해진다). 두 반송파의 값을 "
                       "나란히 놓을 때는 반드시 그 열로 갈라 읽고, 어느 항이 λ 비로 닫히고 어느 "
                       "항이 안 닫히는지는 outputs/carrier_transition_table.json 을 인용한다."),
        "carriers_present_hz": sorted({r["fc_hz"] for r in rows}),
        "prf_hz": prf, "f_flash_hz": ffl,
        # ⛔`elevations_deg` 는 이 **스크립트의 설계 격자**다 — 원장이 실제로 담은 각이
        #   아니다. 원장은 병합으로 자라서 뒤에 붙은 탐침 각을 함께 싣는다.
        #   ⭐둘을 가르지 않으면 이 값을 읽는 쪽이 표를 설계 점과 탐침 각으로 섞는다
        #     (2026-09-02 리포트 16 조각 78 에서 실제로 그랬다).
        "elevations_deg": list(ELS), "drone": TJ.get("drone"),
        "elevations_present_deg": sorted({float(r["el_deg"]) for r in rows},
                                         reverse=True),
        "elevations_note_ko": ("`elevations_deg` = 설계 격자(이 스크립트 기본값), "
                               "`elevations_present_deg` = 원장에 실제로 있는 각의 합집합. "
                               "팔마다 덮은 각이 다르니 «몇 점을 쟀나» 는 행의 `el_deg` 를 "
                               "팔로 갈라 세어야 한다."),
        "rotor_ko": "덱과 같은 결정론 패턴(OU 프리셋 아님) — 축을 하나만 바꾼다",
        "rpm_per_rotor": TJ.get("rpm_per_rotor"),
        "grid_ko": "얼린 격자(자세 합집합 bbox), λ/12",
        "grid_shift_ko": ("⭐행의 `grid_shift_cells` 는 «같은 격자를 몇 칸 옆으로 옮겨 쟀나» 다"
                          "(칸 단위 [e1,e2], 원판은 [0,0]). 격자 간격·칸 수·광선 수는 그대로고 "
                          "표본을 찍는 자리만 다르다 — `grid_div` 와 짝지어 읽어야 «촘촘해서» 와 "
                          "«어디를 찍어서» 를 가를 수 있다. 읽는 법은 docs/GRID_PHASE_NULL.md"),
        "thickness_note_ko": ("⛔**두께 단서(정정 이전 판)** — 행의 `shell_mm`·`prop_mm` 이 "
                              "**100.0** 인 PathSolver 팔은 Sionna 기본값 0.1 m(=10 cm) 슬래브 "
                              "위에서 계산된 값이다. 드론 셸은 실제로 1~3 mm 이고, 두께는 굴절만이 "
                              "아니라 **정반사 계수도** 바꾼다(ITU-R P.2040 단층 슬래브). CPU 실측 "
                              "outputs/slab_thickness_check.json: 셸 정반사가 100 mm 대비 2 mm 에서 "
                              "−4.90 dB(수직)·−5.82 dB(각도평균) 로, ⓪ 격자 밴드 3.86 dB **밖**이다. "
                              "⚠두께 자체는 **출처가 없다**(RETRACTION_LOG A3) — 1·2·3 mm 는 "
                              "측정값이 아니라 민감도 축이다. 우리 커널에는 두께 개념이 없어 "
                              "(|Γ|·τ 뿐) ours 팔은 None 이다."),
        "ours_illumination_ko": "우리 팔은 행의 range_m 으로 구면파 조명 — 행마다 다르다",
        "spp_note_ko": "광선 수는 행의 spp 열에 있다 — 규칙값 (R/3)²×1M 을 --spp 로 덮은 팔이 많다",
        "band_track_ko": "⭐정본 — 앙각마다 그 앙각의 f_tip 으로 0.35~1.0 배",
        "band_fixed_ko": "덱의 −15° 대역(430~1229 Hz) 고정 — 앙각이 내려가면 비어 간다",
        #: ⛔2026-09-04 — 이 파일 머리말은 「직하방에서 마이크로도플러가 원리적으로
        #  사라진다」를 철회했는데 **원장에 나가는 이 문자열은 그대로**였다. 원장을 읽는
        #  쪽은 철회를 볼 방법이 없다. 정정이 아래에만 쌓이는 버릇 그 자체다.
        "prediction_ko": "f_flash 는 앙각과 무관(126.67 Hz), f_tip 만 cos(el) 로 줄어든다. "
                         "직하방(−90°)에서는 **날개끝 도플러 폭 f_tip 이 0 으로 간다.** "
                         "⛔전 판의 «마이크로도플러가 원리적으로 사라진다» 는 철회했다"
                         "(2026-09-04) — el −90 기록을 다시 재면 f_flash 선이 두 엔진 모두 "
                         "127.5 Hz 에 또렷이 선다(예측 126.67 Hz). 사라지는 것은 **폭**이지 "
                         "**박자**가 아니다."},
        "rows": rows}, open(OUT, "w"), ensure_ascii=False, indent=1)

    print(f"\n═══ 앙각 스윕 · R = {RANGE_M:.0f} m · 예측 f_flash {ffl:.2f} Hz ═══\n")
    print(f"{'엔진':>7} {'el':>5} {'f_tip':>7} | {'박자(추적대역)':>13} {'1x−2x':>7} "
          f"{'레벨':>8} | {'박자(고정대역)':>13} {'빈수':>5}")
    for r in rows:
        t, x = r["track"], r["fixed"]
        bt = f"{t['beat_hz']:.2f}" if t["beat_hz"] else "  —"
        bx = f"{x['beat_hz']:.2f}" if x["beat_hz"] else "  —"
        h = f"{t['h1_over_h2_db']:+.2f}" if t["h1_over_h2_db"] is not None else "  —"
        print(f"{r['engine']:>7} {r['el_deg']:>5.0f} {r['f_tip_hz']:>7.0f} | "
              f"{bt:>13} {h:>7} {r['level_db']:>8.2f} | {bx:>13} {x['n_bins']:>5}")
    print(f"\n✅ {OUT}\n✅ {OUTN}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--physics", action="store_true",
                    help="⭐PathSolver 의 물리를 **전부 켠다** — 굴절·회절·모서리회절·다중반사. "
                         "기본 실행은 refraction=False·diffraction=False·max_depth=1 이라 "
                         "«PathSolver 가 굴절/회절을 더 잘 담는다» 를 시험한 적이 없었다. "
                         "같은 광선 예산에서 물리만 켜고 끄는 단일축 대조가 된다.")
    ap.add_argument("--ptd", action="store_true",
                    help="⭐우리 팔의 **모서리 회절(PTD 프린지)** 을 켠다. 기본은 ptd=False 라 "
                         "두 팔 다 모서리 회절이 없었다.")
    ap.add_argument("--engine", default="ours",
                    # ⭐ours_gpu — SBR+PO 를 GPU 로 옮긴 판(src/rcs_sbr_gpu.py, 2026-08-20).
                    #   옛 ours 와 **나란히** 산다. 이름이 `ours_gpu…` 로 갈려 원장이 안 섞인다.
                    #   ⛔PTD·바이스태틱·다중반사·jitter 는 안 옮겼다 — 그 팔은 ours 로.
                    choices=("ours", "ours_free", "ours_gpu", "sionna"),
                    help="ours=동체 포함(가림 있음) · ours_free=⭐동체 **면만** 빼서 "
                         "가림을 없앤 대조군(정점은 그대로라 bbox·광선격자 동일) · ⭐ours_gpu=같은 물리를 GPU 로 옮긴 판(옛 ours 와 나란히 산다) · sionna")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--els", default="",
                    help="쉼표로 앙각을 골라 돈다. 비면 7 점 전부. 예: --els 0")
    ap.add_argument("--spp", type=int, default=0,
                    help="0 이면 규칙값 (R/3)^2 x 1M. ⭐경로 수를 100 개 이상으로 "
                         "올리려면 직접 준다 — 규칙값은 10 m 에서 경로 6~13 개뿐이라 "
                         "«계단 잡음이 가장 심한 구간» 이다(2026-08-11 실측).")
    ap.add_argument("--range-m", type=float, default=RANGE_M,
                    help="⭐구면 반경 [m]. 기본 10 m 는 2D²/λ = 14.076 m 경계 **안쪽**이라 "
                         "근거리장이다(audit_po_trust.json:nearfield_verdict). 15 를 주면 "
                         "경계 밖이라 원거리장 가정이 선다. 10 이 아니면 파일명에 _r<R> 이 "
                         "붙어 기존 샤드와 섞이지 않는다.")
    ap.add_argument("--drone", default="",
                    help="⭐표적 기체를 바꾼다(기본은 원장의 matrice4e). 프롭 지름이 다르면 "
                         "f_flash·f_tip 이 함께 바뀐다 — 분류 축의 첫 재료다. "
                         "파일명에 _<기체> 가 붙는다.")
    ap.add_argument("--sw", default="",
                    help="⭐스위치를 **비트로 직접** 준다: R<0|1>D<0|1>E<0|1>F<0|1> — "
                         "굴절·회절·모서리회절·확산반사. 예: --sw R1D0E0F1. "
                         "--physics·--only·--stock 과 배타적이고, 깊이는 --max-depth 로. "
                         "⚠소스 실측: E 는 D=1 일 때만 뜻이 있다(sb_candidate_generator:338). "
                         "파일명에 _sw<비트> 가 붙는다.")
    ap.add_argument("--stock", action="store_true",
                    help="⭐PathSolver 를 **순정 기본값 그대로** 돌린다 — refraction=True · "
                         "diffraction=False · edge=False · max_depth=3 · diffuse=False. "
                         "우리 «물리 끔» 판(셋 다 끔·깊이 1·확산 켬)과도, «켬» 판과도 다른 "
                         "제3의 조합이다. 파일명에 _stockdef 가 붙는다.")
    ap.add_argument("--only", default="",
                    help="⭐물리 스위치를 **하나씩** 켠다 — refr | diffr | edge | depth3. "
                         "--physics 는 넷을 한꺼번에 켜서 귀속이 불가능하다. "
                         "파일명에 _only<이름> 이 붙는다.")
    ap.add_argument("--plane-wave", action="store_true",
                    help="⭐우리 팔을 **평면파**(range_m=None · 무한거리 등가)로 돌린다. "
                         "구면파와의 차이가 근접장 곡률의 몫이므로, 나딧 잔여가 «근접장 탓이냐 "
                         "격자 churn 탓이냐» 를 가르는 단일축이 된다(RESUME 미해결 4번). "
                         "파일명에 _pw 가 붙는다.")
    ap.add_argument("--env-scat", dest="env_scat", type=float, default=-1.0,
                    help="⭐환경 재질의 **산란계수 S**(거칠기). 0 이면 완벽한 거울, 1 이면 "
                         "완전 확산이다(ITU-R P.2040 계열 — 에너지를 정반사와 확산으로 가른다). "
                         "⚠우리 콘크리트 기본값이 S=0.0 이라 지금 지면은 거울이다. "
                         "안 주면(−1) 재질 기본값 그대로. 파일명에 _S<값> 이 붙는다.")
    ap.add_argument("--body-scale", dest="body_scale", type=float, default=1.0,
                    help="⭐**동체만** 키우거나 줄인다(허브·프롭 고정). 우리 기전 가설 "
                         "「정면에서 동체 거울이 날개를 묻는다」를 직접 시험하는 축이다 — "
                         "동체를 줄여서 날개가 드러나면 기전이 확인된다. "
                         "파일명에 _bs<배율> 이 붙는다.")
    ap.add_argument("--frame-scale", dest="frame_scale", type=float, default=1.0,
                    help="⭐**동체와 로터 허브 위치**를 함께 키운다. --prop-scale 과 짝지어 쓴다 — "
                         "둘 다 k 면 «기체 전체를 k 배»(겹침 없음), frame 만 k 면 «프레임만 벌림». "
                         "⛔prop 만 키우면 이웃 프롭이 관통한다(matrice4e 는 틈이 5.9 mm 뿐). "
                         "파일명에 _fs<배율> 이 붙는다.")
    ap.add_argument("--prop-scale", dest="prop_scale", type=float, default=1.0,
                    help="⭐프롭 **크기만** 바꾼다(허브 위치·동체·회전수 고정). "
                         "「프롭이 크면 정면에서도 박자가 보인다」를 확인하는 대조축이다. "
                         "⚠박자 주파수는 안 변하고 f_tip 은 배율에 비례한다 — 판독에서 "
                         "곱해 줘야 한다. 파일명에 _ps<배율> 이 붙는다.")
    ap.add_argument("--env", type=str, default="",
                    help="⭐실외 환경 이름(outdoor01). 주면 지면·건물·기둥을 장면에 얹고 "
                         "파일명에 _env<이름> 이 붙는다. ⛔안 주면 지금까지와 같은 "
                         "**자유공간**이다 — 빈 씬에 드론 부품만 들어간다.")
    ap.add_argument("--rep", type=int, default=0,
                    help="⭐되풀이 판 번호. **파일 이름에만** _rep<N> 을 붙이고 물리는 "
                         "아무것도 안 바꾼다 — 같은 칸을 여러 판 돌려 «자연 산포» 를 재려고 "
                         "있다(docs/EQUIVALENCE_GATES.md B 층은 ≥6 판을 요구한다). "
                         "PathSolver 는 결정적이지 않으므로(#1175) 판마다 값이 갈린다. "
                         "⛔우리 커널은 결정적이라 되풀이해도 같은 값이 나와야 한다.")
    ap.add_argument("--prf", type=float, default=0.0,
                    help="⭐자세 표집률 [Hz]. 안 주면 원장값(19700). ⛔--n-poses 로는 "
                         "촘촘해지지 않는다(그건 기록 길이다) — 블레이드 통과당 자세 수를 "
                         "늘리려면 이 인자를 쓴다. 파일명에 _prf<Hz> 가 붙는다.")
    ap.add_argument("--n-poses", type=int, default=0,
                    help="⭐슬로타임 자세 수. 0 이면 원장값(report07_three_engines:_meta.n = 4096). "
                         "박자 FFT 분해능 = prf/n 이라 4096 은 4.89 Hz 이고, h1/h2 판별창(±18 Hz)에 "
                         "3.7 빈이 들어간다. 원래 리포트 16 은 8192 를 썼다(2.45 Hz). "
                         "⛔줄이면 안 된다 — 2048 이면 판별창이 1.8 빈이라 고조파비가 안 나온다. "
                         "0 이 아니면 파일명에 _n<N> 이 붙는다.")
    ap.add_argument("--max-depth", type=int, default=0,
                    help="⭐PathSolver 의 반사 깊이를 직접 준다. 0 이면 기존 규칙 "
                         "(--physics 면 3, 아니면 1). 물리 스위치와 깊이를 **가르는** 인자다 — "
                         "전에는 --physics 하나에 묶여 있어 귀속이 불가능했다. "
                         "0 이 아니면 파일명에 _d<N> 이 붙는다.")
    ap.add_argument("--az-deg", type=float, default=float("nan"),
                    help="⭐방위각 [°]. 비우면 원장값(report07_three_engines:_meta.az_deg). "
                         "지금까지 모든 판이 방위 한 자리에서만 잰 것이라 «다른 방위에서도 "
                         "같은 결론이 서는가» 를 시험한 적이 없다. 파일명에 _az<N> 이 붙는다.")
    #: ⭐**2026-08-29 착지 — 이제 기본값이다.** 되돌리려면 `--no-inmem`.
    #  준비 단계(2026-08-20)에는 옵트인이었는데 착지를 안 해서, 8/27~28 큐가
    #  전부 이걸 빠뜨린 채 자세당 62 ms 를 헛되이 썼다. 저장소 관례대로
    #  (`report_mesh/src/make_mesh02.py:791`) 기본을 새 동작으로 두고 옛 길을 스위치로 남긴다.
    #  ⚠정점·면은 OBJ 판과 **비트 동일**(A 층)이지만 객체 «이름» 이 달라진다
    #    (`{key}_{g}` 대 `{key}_{g}_{i%2}`). 솔버 산출은 **자연 산포 안**(B 층)으로
    #    판정됐다 — `outputs/adv_refute_hashlottery_0824.json`. `docs/EQUIVALENCE_GATES.md` 참조.
    ap.add_argument("--inmem", dest="inmem", action="store_true", default=True,
                    help="메쉬를 디스크 안 거치고 바로 올린다. ⭐**이제 기본값**이라 "
                         "이 인자는 아무 효과가 없다(옛 잡 파일 호환용). "
                         "옛 OBJ 왕복 길로 되돌리려면 --no-inmem.")
    ap.add_argument("--no-inmem", dest="inmem", action="store_false",
                    help="⛔옛 길 — 자세마다 정점을 텍스트 OBJ 로 썼다가 되읽는다"
                         "(자세당 62 ms). 회귀 대조용으로만 쓴다.")
    ap.add_argument("--det", action="store_true",
                    help="⭐**재현 가능하게 만든다** (2026-08-20). PathSolver 는 같은 씬·같은 "
                         "시드로 두 번 풀어도 **경로가 담기는 순서**가 달라진다(GPU 가 수만 "
                         "스레드로 병렬 수집하므로). 값 자체는 같지만 순서가 다르면 부동소수점 "
                         "합이 마지막 자리에서 갈린다 — 실측: 같은 코드 4 판에서 E 가 4 종류. "
                         "이 인자를 주면 **지연 기준으로 정렬한 뒤** 더해서 항상 같은 값이 "
                         "나온다(실측 4 판 전부 비트 동일, 지연 동률 0 건). "
                         "⛔안 주면 옛 방식 그대로다 — 기존 샤드와 같은 길.")
    ap.add_argument("--dry-run", action="store_true",
                    help="⭐**만들 샤드 이름만 찍고 끝낸다** — 솔버를 안 돈다. "
                         "2026-08-18 교훈: «rc=0» 도 «샤드 수가 늘었다» 도 성공 증거가 "
                         "아니다. 큐를 짜면 먼저 이걸로 **기대한 팔 이름이 나오는지** 본다 "
                         "(인자 하나를 빠뜨리면 조용히 **다른 팔**이 만들어진다).")
    ap.add_argument("--rotor-preset", default="",
                    help="⭐로터 요동 프리셋 이름 (src/rotor_dynamics.PRESETS): legacy · "
                         "indoor · outdoor · outdoor_v2 …. **안 주면 기존과 비트동일**"
                         "(로터마다 상수 rpm). 주면 정지 산포와 시간 흔들림이 있는 rpm 열로 "
                         "바뀌고 파일명에 _rot<이름> 이 붙는다. "
                         "⚠프리셋은 원장 산포를 더하는 게 아니라 **갈아끼운다** — 프리셋이 "
                         "로터별 산포를 스스로 만들기 때문이다(두 번 세면 안 된다). "
                         "⛔산포를 키우면 빗살 격자가 어긋난다 — 잣대부터 다시 정의할 것"
                         "(noise_main_gates G5).")
    ap.add_argument("--rotor-seed", type=int, default=0,
                    help="로터 프리셋의 난수 씨앗. 0 이면 꼬리표가 안 붙는다.")
    ap.add_argument("--div", type=int, default=0,
                    help="⭐우리 커널의 표면 격자 간격을 λ/DIV 로 정한다. 0 이면 규약값 12. "
                         "상한 위 누설이 격자 표본화에서 오는지 가르는 축이다 — 촘촘하게 "
                         "하면 내려가야 한다. 계산량은 대략 DIV² 로 는다. "
                         "0 이 아니면 파일명에 _div<N> 이 붙는다. (PathSolver 에는 없는 축)")
    ap.add_argument("--fc-ghz", type=float, default=FC / 1e9,
                    help="⭐반송파 [GHz]. 기본 3.5 는 지금까지의 모든 판이 쓴 값이라 "
                         "**안 주면 기존 샤드와 비트동일**이고 꼬리표도 안 붙는다. "
                         "5.8 을 주면 파일명에 _fc5800 이 붙어 옛 샤드와 안 섞인다. "
                         "⚠λ 가 바뀌면 격자 간격(λ/div)·얼린 격자 칸 수·f_tip·원거리장 경계가 "
                         "함께 바뀐다 — **--div 는 12 로 두어야** λ/12 규약이 유지돼 R16 격자 "
                         "밴드를 그대로 인용할 수 있다. 무엇이 λ 비로 닫히고 무엇이 안 닫히는지는 "
                         "outputs/carrier_transition_table.json (R23①) 을 볼 것. "
                         "⛔단위는 GHz 다 — 설계서 옛 표기 «--fc 5.8e9» 를 그대로 치면 죽는다.")
    ap.add_argument("--grid-shift", "--grid-phase", default="",
                    help="⭐**격자 위상 널** — 같은 λ/DIV 격자를 반 칸(0.5) 옆으로 옮겨 다시 잰다. "
                         "칸 단위이고 스칼라면 두 가로축에 같이, «0.5,0.25» 면 따로 준다. "
                         "안 주면(또는 0) 판을 안 옮기고 꼬리표도 안 붙어 **기존 샤드와 비트동일**. "
                         "격자 간격·칸 수·광선 수는 **안 바뀐다** — 표본을 찍는 자리만 바뀐다. "
                         "그래서 --div 로 촘촘히 했을 때의 변화가 «촘촘해서» 인지 «원점이 달라서» "
                         "인지를 이 인자로만 가를 수 있다. 이동판과 원판의 차이가 λ/12↔λ/24 차이와 "
                         "비슷하면 그 변화는 해상도가 아니라 표본 자리의 몫이다(그러면 더 촘촘한 "
                         "격자를 사는 것은 낭비다). ⭐1.0 은 격자가 자기 위에 겹치는 배선 검사용이다. "
                         "우리 커널 전용(PathSolver 에는 표면 격자가 없다). "
                         "파일명에 _shift<칸수> 가 붙는다. 읽는 법 docs/GRID_PHASE_NULL.md")
    ap.add_argument("--shell-mm", type=float, default=0.0,
                    help="⭐드론 **셸 두께 [mm]** — plastic·plastic_blue(동체·캐노피·착륙장치·"
                         "식별색)를 이 두께의 슬래브로 만든다. 0 이면 아무것도 안 건드려 "
                         "**기존 샤드와 비트동일**(=Sionna 기본값 100 mm 가 그대로 쓰인다). "
                         "⛔지금까지의 모든 PathSolver 수치는 그 100 mm 판 위의 값이다 — "
                         "두께는 굴절만이 아니라 **정반사도** 바꾼다(ITU-R P.2040 단층 슬래브). "
                         "CPU 실측(outputs/slab_thickness_check.json): 셸 정반사가 100 mm 대비 "
                         "3 mm −1.6 · 2 mm −4.9 · 1 mm −10.8 dB. ⭐두께에는 **출처가 없으니"
                         "**(RETRACTION_LOG A3) 한 값을 못 박지 말고 1·2·3 mm 를 **민감도 축**"
                         "으로 돌린다. ⚠기준선 팔도 반드시 같은 두께로 함께 낸다 — 2 mm 굴절을 "
                         "100 mm 기준선과 겨루면 지금보다 나쁜 비교다. 파일명에 _shell<N>mm.")
    ap.add_argument("--prop-mm", type=float, default=0.0,
                    help="⭐**프로펠러 두께 [mm]** — prop_plastic 만 바꾼다. --shell-mm 과 갈라 둔 "
                         "이유는 «표적 축(마이크로도플러)이 안 움직이는 판» 을 하나 확보하기 "
                         "위해서다(셸만 고치고 날개는 그대로 두는 팔). 0 이면 안 건드린다"
                         "(비트동일). 날개는 셸보다 얇다는 것이 우리 |Γ| 표의 방향이므로 "
                         "보통 셸보다 작은 값을 준다. 파일명에 _prop<N>mm. "
                         "⚠carbon(암·데크)에는 손잡이가 없다 — 표피깊이 0.155 mm 라 0.5 mm 든 "
                         "100 mm 든 반사가 같다(실측 0.00 dB).")
    ap.add_argument("--parts", default="",
                    help="쉼표 구분 그룹 필터(예: prop) — Sionna 가지 전용. 장면에 그 "
                         "그룹 부품만 넣는다(0° 붕괴 기전 검증: 기근이냐 익사냐). "
                         "꼬리표 _parts<이름>. 우리 커널 쪽 대응물은 ours_free 엔진.")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    a = ap.parse_args()
    analyse() if a.merge else run(a)


if __name__ == "__main__":
    main()
