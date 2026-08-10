# -*- coding: utf-8 -*-
"""
render_md_anim.py — ⭐**호버링 애니메이션**(TX/RX + 도는 프로펠러)을 Sionna 렌더로 만든다.

왜
--
사용자 요청(2026-08-10, 재요청): *"레포트에 Tx, Rx 드론 호버링이 그려진 것의 애니메이션을
넣어줘. 많은 자원을 써서라도 좀 그럴듯하게 그려서 레포트에 넣어줘. 지금 시나리오 너무 느리게
프로펠러가 돌아서 현실성이 너무 떨어지는 것 같아. 여러장의 사진을 렌더링해서 좀 그럴듯한
속도로 돌아가게 해줘"*

첫 판의 두 가지 잘못
  1. **너무 느렸다.** 블레이드 한 주기(7.9 ms)를 36 프레임 × 60 ms 로 늘여 재생 2.16 s
     → 슬로모션 ×274. 프로펠러가 기어갔다.
  2. **TX/RX 가 화면에 없었다.** `show_devices=False` 로 꺼 놓고 근접 컷만 그렸다.

이 판이 고치는 것
  1. 회전각을 프레임당 **15°** 로 키우고 프레임 지연을 **30 ms** 로 줄여 슬로모션을
     ×45 대로 내렸다. 아래 «속도 산수» 참조.
  2. **두 칸 화면**을 한 GIF 에 담는다.
       위칸(main) 드론 근접 — 블레이드가 크게 보인다(이게 주인공).
       아래칸(wide) 배치 전체 — 레이더(TX·RX)와 표적이 한 화면에.
     드론을 크게 보는 것과 TX/RX 를 함께 보는 것은 한 컷에서 양립하지 않는다(3 m 떨어져 있고
     드론은 0.6 m 다). 그래서 나눠 담았다.

속도 산수 (숫자는 실행 시점에 원장에서 읽어 다시 계산한다 — 여기 적힌 건 예시다)
    호버 rpm 3800  → 1회전 15.79 ms → 블레이드 주기(2엽, 180°) 7.89 ms
    프레임당 15°   → 실시간 0.658 ms/프레임
    표시 30 ms/프레임 → 슬로모션 = 30 / 0.658 ≈ ×45.6
    96 프레임 = 8 블레이드 주기 = 실시간 63 ms → 재생 2.88 s
  ⚠ 프레임당 각이 크면 **역회전 착시**(wagon-wheel)가 난다. 2엽 프로펠러는 180° 대칭이라
    프레임당 90° 를 넘으면 위험하다 — 15° 는 그 한참 아래다.
  ⚠ 루프가 이어지려면 총 회전각이 180° 의 정수배여야 한다. 로터마다 rpm 이 미세하게 달라
    정확히는 안 맞는다 — 그 어긋남(seam)을 재서 JSON 에 적는다.
  ⚠ **정직하게**: 프레임당 15° 는 180°/15 = 12 프레임마다 형상이 되돌아온다는 뜻이다.
    96 프레임은 그 12 프레임짜리 시각 주기를 8 번 담은 «영상» 이다 — 주기운동을 찍은 실제
    영상이 그렇듯이. 로터별 rpm 이 달라 프레임이 완전히 같지는 않다(누적 어긋남도 기록).

기하 — 씬 정본을 따른다
  드론은 원점, 레이더는 거리 3 m · 고각 −15°. **기선 0 = 진짜 모노스태틱**(2026-08-10 정정)
  이라 TX 와 RX 가 같은 점이다. 마커가 완전히 겹치므로 **공 하나로** 그린다(RX 구를 TX 구
  안에 넣고 색을 같게 둔다). 글자는 넣지 않는다 — 그게 무엇인지는 리포트 본문이 말한다.
  기선 값은 `benchmark/render_md_scene.py` 의 `BASE` 를 **읽어서** 쓴다(하드코딩 아님).

시나리오 출처
  `outputs/report07_three_engines.json` 의 `_meta`(기체·az·el·거리·f_c·로터별 rpm)를
  **읽는 시점 값으로** 쓴다. 파일이 없거나 갱신 중이면 스펙에서 다시 계산한다(그 사실도 기록).

    PYTHONPATH=src python benchmark/render_md_anim.py            # 본 산출
    PYTHONPATH=src python benchmark/render_md_anim.py --smoke    # 2 프레임 저해상도 점검

환경변수(재현용 주입점)
    SIONNA2_GPU        쓸 GPU 고정(없으면 MDANIM_GPUS 후보 중 여유 메모리 최대 카드)
                       ⭐ 이 판의 산출물은 SIONNA2_GPU=2 로 핀해 **한 카드에서** 뽑았다
    MDANIM_GPUS        후보 GPU 목록 (기본 "0,1,2,3" — 판정은 여유 메모리)
    MDANIM_W           프레임 가로 픽셀 (기본 1800; 두 칸이 이 폭을 공유한다)
    MDANIM_H_MAIN      위칸 세로 (기본: 내용 가로세로비에서 역산 — panel_height)
    MDANIM_H_WIDE      아래칸 세로 (기본: 같은 역산)
    MDANIM_SPP         프레임당 표본 수 (기본 256) ⚠ W·H·spp·4 B 가 GPU 메모리다
    MDANIM_MEM_FRAC    표본버퍼가 쓸 여유 메모리 비율 (기본 0.40) — spp 를 자동으로 낮춘다
    MDANIM_FRAMES      프레임 수 (기본 96)
    MDANIM_PERIODS     루프에 담을 블레이드 주기 수 (기본 8)
    MDANIM_MS          GIF 프레임 지연 [ms] (기본 30) ⚠ 20 ms 미만은 브라우저가 100 ms 로 올린다
    MDANIM_GIF_W       GIF 가로 픽셀 (기본 1300 — 렌더본을 축소해 파일을 줄인다)
    MDANIM_MAX_MB      GIF 상한 [MB] (기본 12.0 — 리포트에 base64 로 박힌다)

산출
    outputs/figures/report07_anim.gif          최종 애니메이션
    outputs/figures/report07_anim_poster.png   첫 프레임 정지컷(GIF 안 되는 뷰어용)
    outputs/report07_anim.json                 근거·설정 기록
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, "src"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# --------------------------------------------------------------------------- #
#  GPU 선택 — ⚠ mitsuba/sionna import 전에 끝내야 한다
# --------------------------------------------------------------------------- #
def _gpu_free_mb() -> dict[int, int]:
    """nvidia-smi 로 카드별 **여유 메모리**[MiB]. 판정 기준은 메모리다(util% 아님)."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
             "--format=csv,noheader,nounits"], text=True, timeout=20)
    except Exception:
        return {}
    free = {}
    for line in out.strip().splitlines():
        try:
            i, used, total = [int(x.strip()) for x in line.split(",")]
            free[i] = total - used
        except ValueError:
            continue
    return free


def _pick_gpu() -> dict:
    """후보 중 여유 메모리가 가장 많은 카드를 고른다. SIONNA2_GPU 가 있으면 그걸 따른다.
    ⚠ 2026-08-10 이 산출물은 **SIONNA2_GPU=2 로 핀해서** 뽑았다(사용자 지시로 후보 제한
      «0·1·3» 이 그날 취소됐다). 후보 목록을 특정 카드로 굳히지 않는다 — 그런 굳힘이 하루
      만에 낡았다. 판정은 언제나 **여유 메모리**이고, 고정이 필요하면 SIONNA2_GPU 를 쓴다."""
    free = _gpu_free_mb()
    forced = os.environ.get("SIONNA2_GPU")
    cands = [int(x) for x in os.environ.get("MDANIM_GPUS", "0,1,2,3").split(",") if x.strip()]
    if forced is not None and forced.strip() != "":
        idx = int(forced)
        why = "SIONNA2_GPU 로 강제"
    elif free:
        pool = {i: f for i, f in free.items() if i in cands} or free
        idx = max(pool, key=lambda i: pool[i])
        why = (f"후보 {cands} 중 여유 메모리 최대 "
               f"({', '.join(f'GPU{i}:{free[i]}MiB' for i in sorted(free))})")
    else:
        idx, why = 0, "nvidia-smi 실패 — GPU0 로 대체"
    os.environ["SIONNA2_GPU"] = str(idx)
    return dict(gpu=int(idx), free_mb=int(free.get(idx, -1)), free_mb_all=free, why_ko=why)


GPU_INFO = _pick_gpu()

from gpu import pick                                                    # noqa: E402
pick(verbose=True)

import numpy as np                                                      # noqa: E402
import mitsuba as mi                                                    # noqa: E402
import sionna.rt as rt                                                  # noqa: E402

import report15_probe as RP                                             # noqa: E402
from articulated_fast import FastPoser, rotor_phases                    # noqa: E402
from drones import DRONES, DRONE_GROUP_MAT, drone_colors                # noqa: E402

FIGDIR = os.path.join(ROOT, "outputs", "figures")
GIF = os.path.join(FIGDIR, "report07_anim.gif")
POSTER = os.path.join(FIGDIR, "report07_anim_poster.png")
OUTJ = os.path.join(ROOT, "outputs", "report07_anim.json")
SCEN = os.path.join(ROOT, "outputs", "report07_three_engines.json")
SCENE_CANON = os.path.join(HERE, "render_md_scene.py")
#  ⚠ 프레임 스크래치는 .gitignore 에 등록된 outputs/meshes/report15_probe/ 아래에만 둔다.
FRAMES = os.path.join(RP.SCRATCH, "report07_anim_frames")

#  ⚠ 표본 버퍼 = W·H·spp·4 B 가 GPU 메모리에 그대로 잡힌다(실패 전례: 2560×1600×2048 = 32 GiB OOM).
#    공용 카드라 여유가 출렁이므로 시작 시점 여유의 MEM_FRAC 만큼으로 spp 를 자동으로 깎고,
#    그래도 OOM 이면 프레임 단위로 spp 를 반씩 줄여 재시도한다.
W = int(os.environ.get("MDANIM_W", "1800"))
#  ⭐ 칸 높이는 손으로 박지 않는다 — **내용의 가로세로비에서 역산**한다(panel_height 참조).
#     드론은 가로 0.62 m·세로 0.19 m 라 정사각 칸은 흰 여백이고, 레이더~표적 3 m 선은 더 눕는다.
#     MDANIM_H_MAIN/H_WIDE 를 주면 역산을 덮어쓴다(고정하고 싶을 때만).
SPP = int(os.environ.get("MDANIM_SPP", "384"))
MEM_FRAC = float(os.environ.get("MDANIM_MEM_FRAC", "0.40"))
N_FRAMES = int(os.environ.get("MDANIM_FRAMES", "96"))
N_PERIODS = int(os.environ.get("MDANIM_PERIODS", "8"))
DELAY_MS = int(os.environ.get("MDANIM_MS", "30"))
GIF_W = int(os.environ.get("MDANIM_GIF_W", "1300"))
MAX_MB = float(os.environ.get("MDANIM_MAX_MB", "12.0"))
GUTTER = 18                       # 두 칸 사이 흰 여백[px]

#  fill = 내용이 칸 **가로**의 몇 할을 채우나 / vfill = **세로**의 몇 할. 칸 높이는 이 둘에서 나온다.
#  근접 칸은 세로에 여유를 둬야 프로펠러가 답답하지 않고, 배치 칸은 대각선이라 꽉 채우는 게 낫다.
FOV_MAIN, FILL_MAIN, VFILL_MAIN = 26.0, 0.86, 0.62
FOV_WIDE, FILL_WIDE, VFILL_WIDE = 40.0, 0.86, 0.86
WIDE_DIR = (0.15, 1.0, 0.30)      # 아래칸 시점 — 옆(+y)에서 살짝 위. 레이더 왼쪽·표적 오른쪽
DEV_R = 0.09                      # TX 마커 반지름[m] — 씬 정본 f0a 와 같은 값 (RX 는 이 안에 들어간다)
DEV_RGB = (0.85, 0.13, 0.13)      # TX·RX **같은 색** — 한 점의 모노스태틱 레이더로 읽히게
#  ⚠ 정직성: `Scene.render_to_file` 에는 시드 인자가 없다(서명 실측). 재현성은 «자세·카메라·
#    spp·해상도가 결정론적으로 정해진다» 는 데서 온다 — 위상은 rpm 과 프레임 수로 계산되고
#    카메라는 메쉬·레이더 위치에서 역산되므로, 같은 인자로 다시 돌리면 같은 그림이 나온다.


# --------------------------------------------------------------------------- #
#  기선(baseline) — 씬 정본 render_md_scene.py 의 BASE 를 **읽는다**
# --------------------------------------------------------------------------- #
def scene_baseline(default: float = 0.0) -> tuple[float, str]:
    """`AZ, EL, RNG, BASE = ...` 한 줄을 ast 로 읽어 BASE 만 꺼낸다.
    ⭐ import 하지 않는 이유: 그 모듈은 import 시점에 GPU 를 잡는다(부작용)."""
    try:
        with open(SCENE_CANON, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Tuple)):
                continue
            elts = node.targets[0].elts
            if not all(isinstance(t, ast.Name) for t in elts):
                continue
            names = [t.id for t in elts]
            if "BASE" not in names:
                continue
            vals = ast.literal_eval(node.value)
            if len(vals) != len(names):
                continue
            return (float(vals[names.index("BASE")]),
                    f"benchmark/render_md_scene.py 에서 읽음 ({dict(zip(names, vals))})")
    except Exception as e:
        return float(default), f"기본값 {default} — render_md_scene.py 읽기 실패: {e}"
    return float(default), f"기본값 {default} — render_md_scene.py 에서 BASE 를 못 찾음"


# --------------------------------------------------------------------------- #
#  시나리오 — report07_three_engines.json 의 _meta 를 **읽는 시점 값**으로
# --------------------------------------------------------------------------- #
def scenario(drone_cli: str | None) -> dict:
    """이 편의 정본 시나리오. 파일이 없거나 깨졌으면 스펙에서 다시 계산한다."""
    meta, src = {}, "fallback(스펙에서 재계산)"
    try:
        with open(SCEN, encoding="utf-8") as f:
            meta = (json.load(f) or {}).get("_meta", {}) or {}
        if meta:
            src = f"{os.path.relpath(SCEN, ROOT)} (_meta.generated={meta.get('generated')})"
    except Exception as e:                                   # 재계산 중이면 여기로 온다
        src = f"fallback — {os.path.relpath(SCEN, ROOT)} 읽기 실패: {e}"

    key = drone_cli or meta.get("drone") or "matrice4e"
    spec = DRONES[key]
    fc = float(meta.get("fc_hz", 3.5e9))
    az = float(meta.get("az_deg", 0.0))
    el = float(meta.get("el_deg", -15.0))
    rng = float(meta.get("range_m", 3.0))
    rpm0 = float(getattr(spec, "hover_rpm", 6000.0))
    rpms = meta.get("rpm_per_rotor")
    if not rpms or len(rpms) != int(spec.num_rotors):
        #  세 엔진 스크립트와 같은 규약(로터별 미세 산포). 값은 그쪽이 정본이다.
        spread = float(os.environ.get("SIONNA2_MD_SPREAD", "0.0022"))
        pattern = np.array([+1.0, -1.0, -0.55, +0.55])
        rpms = (rpm0 * (1.0 + spread * np.resize(pattern, int(spec.num_rotors)))).tolist()
        src += " · rpm_per_rotor 는 스펙에서 재계산"
    rpms = [float(x) for x in rpms]
    blades = int(spec.prop_blades)
    f_flash = float(meta.get("f_flash_hz", blades * float(np.mean(rpms)) / 60.0))
    base, base_src = scene_baseline()
    return dict(source=src, meta=meta, spec=spec, drone=key, fc_hz=fc,
                az_deg=az, el_deg=el, range_m=rng, rpm_per_rotor=rpms,
                blades=blades, f_flash_hz=f_flash,
                baseline_m=base, baseline_source=base_src)


# --------------------------------------------------------------------------- #
#  자세 → 씬  (report07_three_engine_maps.py 와 **같은 조립 경로**)
# --------------------------------------------------------------------------- #
def posed_scene(fp: FastPoser, spec, phases_deg, tag: str, fc: float):
    """로터별 위상[deg] → 드론 한 대만 있는 자유공간 씬. (scene, scratch_dir, mesh_view)"""
    mv = fp.pose(phases_deg)
    m = mv.to_mesh()                                    # Sionna 는 진짜 geom.Mesh 가 필요
    d = os.path.join(RP.SCRATCH, f"{spec.key}_{tag}")
    objs = m.write_obj_per_group(d, spec.key)
    cols = drone_colors(spec)
    parts = [RP.Part(name=f"{spec.key}_{g}_{tag}", obj=p,
                     mat_key=DRONE_GROUP_MAT[g][0], color=cols[g])
             for g, p in objs.items()]
    return RP.build_scene(parts, fc=fc), d, mv


# --------------------------------------------------------------------------- #
#  카메라 — 담아야 할 점들을 주면 **화면에 다 들어오는 거리**를 역산한다
# --------------------------------------------------------------------------- #
def _basis(view_dir):
    """카메라는 aim + d·n̂ 에 앉는다. (n̂, 시선 w, 화면가로 r, 화면세로 v)."""
    n = np.asarray(view_dir, float)
    n = n / np.linalg.norm(n)
    w = -n
    up = np.array([0.0, 0.0, 1.0])
    r = np.cross(w, up)
    if np.linalg.norm(r) < 1e-9:                        # 수직 내려다보기 방어
        r = np.cross(w, np.array([1.0, 0.0, 0.0]))
    r /= np.linalg.norm(r)
    v = np.cross(r, w)
    return n, w, r, v


def panel_height(points, view_dir, width, fill, vfill, lo=0.22, hi=0.62) -> int:
    """내용이 칸 가로의 `fill`·세로의 `vfill` 을 채우도록 **칸 높이를 역산**한다.

    화면상 반폭/반높이는 카메라 거리와 무관하고 **시선 방향만으로** 정해진다(정규직교 투영).
    → 해상도를 고르기 전에 미리 잴 수 있다. 손으로 박은 높이는 기체·거리가 바뀌면 죽는다."""
    _, _, r, v = _basis(view_dir)
    P = np.asarray(points, float).reshape(-1, 3)
    hr = 0.5 * float((P @ r).max() - (P @ r).min())
    hv = 0.5 * float((P @ v).max() - (P @ v).min())
    h = width * (hv / max(hr, 1e-9)) * (fill / vfill)
    return int(round(min(max(h, lo * width), hi * width) / 2.0) * 2)      # 짝수 픽셀


def fit_camera(points, view_dir, res, fov, fill):
    """점구름 전부가 화면 안에 들어오는 최소 거리를 **원근을 정확히 반영해** 푼다.

    화면 반각 θ 에 대해 점이 프레임 안에 있으려면  |Δr| ≤ (d + Δw)·tan(θ·fill).
    → d ≥ |Δr|/tan(θ·fill) − Δw. 모든 점·두 축에 대해 최대를 취한다.
    (직교근사로 재면 카메라 쪽으로 튀어나온 점이 잘린다 — 프로펠러 앞날이 그렇다.)"""
    n, w, r, v = _basis(view_dir)
    P = np.asarray(points, float).reshape(-1, 3)
    pr, pv, pw = P @ r, P @ v, P @ w
    cr = 0.5 * (pr.min() + pr.max())
    cv = 0.5 * (pv.min() + pv.max())
    cw = 0.5 * (pw.min() + pw.max())
    aim = cr * r + cv * v + cw * w                      # r·v·w 는 정규직교 → 좌표 재조립
    fx = math.radians(fov) / 2.0
    fy = math.atan(math.tan(fx) * res[1] / res[0])
    tx, ty = math.tan(fx * fill), math.tan(fy * fill)
    dw = pw - cw
    d = float(max((np.abs(pr - cr) / tx - dw).max(),
                  (np.abs(pv - cv) / ty - dw).max()))
    d = max(d, 1e-3)
    pos = aim + d * n
    cam = rt.Camera(position=mi.Point3f(*[float(x) for x in pos]),
                    look_at=mi.Point3f(*[float(x) for x in aim]))
    rec = dict(position=[float(x) for x in pos], look_at=[float(x) for x in aim],
               distance_m=d, fov_deg=float(fov), fill_frac=float(fill),
               half_width_m=float(0.5 * (pr.max() - pr.min())),
               half_height_m=float(0.5 * (pv.max() - pv.min())),
               depth_span_m=float(pw.max() - pw.min()),
               view_dir=[float(x) for x in n],
               fit_ko="점구름 전부가 프레임 안에 들어오는 최소 거리(원근 정확 해)")
    return cam, rec, (pos, w)


def fit_spp(res, spp_req: int, free_mb: int, frac: float = MEM_FRAC) -> int:
    """표본버퍼(W·H·spp·4 B)가 여유 메모리의 `frac` 을 넘지 않게 spp 를 깎는다.
    ⭐ 공용 카드라 «요청대로 밀어붙이기» 가 곧 OOM 이다 — 먼저 재고 시작한다."""
    if free_mb is None or free_mb <= 0:
        return int(spp_req)
    cap = int(frac * free_mb * 1024 * 1024 / (res[0] * res[1] * 4))
    cap = (cap // 32) * 32
    return int(max(32, min(spp_req, cap)))


# --------------------------------------------------------------------------- #
#  흰 배경 합성 — viz_report1._whiten / render_report13._white_png 와 **같은 규약**
# --------------------------------------------------------------------------- #
def white_png(path: str) -> str:
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB"), float) / 255.0
    lum = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
    if np.mean([lum[0, 0], lum[0, -1], lum[-1, 0], lum[-1, -1]]) > 0.6:
        return path                                      # 이미 흰 배경
    a = np.clip((lum - 0.025) / 0.14, 0, 1)
    comp = im * a[..., None] + (1 - a[..., None])
    Image.fromarray((np.clip(comp, 0, 1) * 255).astype("uint8")).save(path)
    return path


def stack_panels(paths, out_path, gutter: int = GUTTER) -> tuple[int, int]:
    """칸들을 세로로 쌓아 한 프레임으로. 사이는 흰 여백(선·글자 없음)."""
    from PIL import Image
    ims = [Image.open(p).convert("RGB") for p in paths]
    w = max(im.width for im in ims)
    h = sum(im.height for im in ims) + gutter * (len(ims) - 1)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    y = 0
    for im in ims:
        canvas.paste(im, ((w - im.width) // 2, y))
        y += im.height + gutter
        im.close()
    canvas.save(out_path)
    return w, h


# --------------------------------------------------------------------------- #
#  GIF 조립 — render_rt.make_gif 규약(PIL 만·loop=0·optimize) + **크기 상한 강제**
# --------------------------------------------------------------------------- #
def build_gif(png_files, out_path, ms=DELAY_MS, width=GIF_W, max_mb=MAX_MB) -> dict:
    """프레임 PNG → GIF. 폭·색수를 낮춰가며 `max_mb` 이하로 맞춘다.

    ⭐ **전역 팔레트**를 쓴다(프레임마다 팔레트를 새로 뽑는 render_rt.make_gif 와 다른 점).
      배경이 흰색으로 고정된 이 장면에서는 프레임별 팔레트가 깜빡임을 만들고 파일도 더 크다."""
    from PIL import Image
    src = [Image.open(p).convert("RGB") for p in png_files]
    attempts = []
    for width_try in (width, int(width * 0.88), int(width * 0.76), int(width * 0.64)):
        for colors in (128, 96, 64, 48):
            h = int(round(src[0].height * width_try / src[0].width))
            fr = [im.resize((width_try, h), Image.LANCZOS) for im in src]
            pal = fr[0].quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
            q = [f.quantize(palette=pal, dither=Image.Dither.FLOYDSTEINBERG) for f in fr]
            #  ⚠ 배경이 253,253,252 로 양자화되면 흰 리포트 지면 위에 옅은 사각 테두리가 보인다.
            #    **양자화 뒤에** 거의-흰 팔레트 항목만 순백으로 바꾼다(픽셀 인덱스는 그대로라
            #    다시 매핑되지 않는다 — 양자화 전에 바꾸면 오히려 249 로 밀린다. 실측).
            pl = list(q[0].getpalette() or [])
            for j in range(0, len(pl), 3):
                if all(val >= 248 for val in pl[j:j + 3]):
                    pl[j:j + 3] = [255, 255, 255]
            for im in q:
                im.putpalette(pl)
            q[0].save(out_path, save_all=True, append_images=q[1:], duration=ms,
                      loop=0, optimize=True)
            mb = os.path.getsize(out_path) / 1e6
            attempts.append(dict(width=width_try, colors=colors, mb=round(mb, 3)))
            print(f"    [gif] {width_try}×{h} · {colors}색 → {mb:.2f} MB", flush=True)
            for im in fr:
                im.close()
            if mb <= max_mb:
                for im in src:
                    im.close()
                return dict(path=out_path, size_mb=float(mb), width=width_try, height=h,
                            colors=colors, delay_ms=int(ms), n_frames=len(q), loop=0,
                            attempts=attempts, under_limit=True, max_mb=max_mb)
    for im in src:
        im.close()
    mb = os.path.getsize(out_path) / 1e6
    return dict(path=out_path, size_mb=float(mb), width=attempts[-1]["width"],
                height=None, colors=attempts[-1]["colors"], delay_ms=int(ms),
                n_frames=len(png_files), loop=0, attempts=attempts,
                under_limit=False, max_mb=max_mb)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default=None, help="기본은 report07_three_engines.json 의 기체")
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    ap.add_argument("--spp", type=int, default=SPP)
    ap.add_argument("--width", type=int, default=W)
    ap.add_argument("--periods", type=int, default=N_PERIODS,
                    help="루프에 담을 블레이드 주기 수 (프레임당 회전각 = periods·180°/frames)")
    ap.add_argument("--ms", type=int, default=DELAY_MS)
    ap.add_argument("--smoke", action="store_true", help="2 프레임·저해상도 점검(산출물 안 덮음)")
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()

    n_f, spp_req, ww = a.frames, a.spp, a.width
    if a.smoke:                                           # 화면비는 그대로, 크기·표본만 줄인다
        n_f, spp_req, ww = 2, 64, ww // 3

    sc = scenario(a.drone)
    spec = sc["spec"]
    fp = FastPoser(spec)                                  # 호버 = 몸체 고정, 로터만 돈다
    rpms = np.asarray(sc["rpm_per_rotor"], float)

    # ── 루프 시간축 ────────────────────────────────────────────────────────
    #   블레이드 주기 T = 1/f_flash. periods·T 를 프레임으로 **균등 분할**(endpoint 제외)
    #   → 마지막 프레임 다음이 첫 프레임이라 GIF 가 이어진다.
    T = 1.0 / float(sc["f_flash_hz"])
    t = np.arange(n_f) / n_f * (a.periods * T)
    ph = rotor_phases(t, rpms, fp.dirs)                    # (n_f, n_rotors) [deg]
    #  로터별 rpm 이 다르니 한 바퀴 뒤 위상이 정확히 안 맞는다 — 그 어긋남을 잰다(정직성).
    #  이상적이면 각 로터가 정확히 `periods × (360/날개수)` 만큼 돌아 형상이 되돌아온다.
    close = np.abs(rotor_phases(np.array([a.periods * T]), rpms, fp.dirs)[0] - ph[0])
    ideal = a.periods * 360.0 / sc["blades"]
    seam_deg = float(np.abs((close - ideal + 180.0) % 360.0 - 180.0).max())

    deg_per_frame = a.periods * (360.0 / sc["blades"]) / n_f      # 로터 회전각/프레임
    dt_real = deg_per_frame / 360.0 * 60.0 / float(rpms.mean())   # 프레임 사이 실시간[s]
    playback_s = n_f * a.ms / 1000.0
    slowmo = playback_s / (a.periods * T)
    unique_phases = (360.0 / sc["blades"]) / deg_per_frame        # 형상이 되돌아오는 프레임 수

    warn = []
    if deg_per_frame > 0.5 * (360.0 / sc["blades"]):
        warn.append(f"프레임당 {deg_per_frame:.1f}° 는 날개 대칭각의 절반을 넘는다 — "
                    f"역회전 착시(wagon-wheel) 위험")
    if a.ms < 20:
        warn.append(f"프레임 지연 {a.ms} ms 는 브라우저가 100 ms 로 올려 버린다(20 ms 미만 규칙)")
    if not (20.0 <= slowmo <= 90.0):
        warn.append(f"슬로모션 ×{slowmo:.0f} 가 목표대(×30~60) 밖이다")

    # ── 기하: 씬 정본대로 TX/RX 를 놓는다(기선은 render_md_scene.py 에서 읽었다) ──
    u = RP.look_dir(sc["az_deg"], sc["el_deg"])            # 표적 → 레이더
    radar = float(sc["range_m"]) * u

    #  ⭐ 카메라는 **한 번만** 잡고 전 프레임 고정한다 — 그래야 «동체는 안 움직이고 날만
    #    돈다» 가 보인다. 다만 블레이드가 도는 동안 실루엣이 커지므로, 위상 여러 개의
    #    정점을 합친 **회전 포락선**으로 프레이밍을 잡는다(한 위상만 보면 날 끝이 잘린다).
    env = np.vstack([np.asarray(fp.pose(rotor_phases(np.array([k / 12.0 * T]), rpms, fp.dirs)[0]).v,
                                float) for k in range(12)])
    dev_pts = radar + DEV_R * np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0],
                                        [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
    wide_pts = np.vstack([env, dev_pts])

    #  ⭐ 칸 높이 역산 (환경변수로 덮어쓸 수 있다)
    hm = int(os.environ.get("MDANIM_H_MAIN", "0")) or \
        panel_height(env, u, ww, FILL_MAIN, VFILL_MAIN)
    hw = int(os.environ.get("MDANIM_H_WIDE", "0")) or \
        panel_height(wide_pts, WIDE_DIR, ww, FILL_WIDE, VFILL_WIDE)
    res_main, res_wide = (ww, hm), (ww, hw)

    cam_main, rec_main, (pos_main, w_main) = fit_camera(env, u, res_main, FOV_MAIN, FILL_MAIN)
    cam_wide, rec_wide, (pos_wide, w_wide) = fit_camera(wide_pts, WIDE_DIR,
                                                        res_wide, FOV_WIDE, FILL_WIDE)
    #  근접 칸에서 레이더 공이 카메라 **뒤**면 그리라고 해 봐야 안 보인다 → 오버레이 렌더
    #  (본 렌더 외에 2 장 더 그린다)를 건너뛴다. 판정은 시선축 부호 하나로 끝난다.
    dev_in_main = bool(float((radar - pos_main) @ w_main) > 0.0)
    dev_in_wide = bool(float((radar - pos_wide) @ w_wide) > 0.0)

    spp_main = fit_spp(res_main, spp_req, GPU_INFO["free_mb"])
    spp_wide = fit_spp(res_wide, spp_req, GPU_INFO["free_mb"])

    views = [
        dict(key="main", cam=cam_main, res=res_main, fov=FOV_MAIN, spp=spp_main,
             show_devices=dev_in_main, rec=rec_main,
             what_ko="드론 근접 — 레이더가 보는 방향(az/el 그대로), 블레이드가 크게 보인다"),
        dict(key="wide", cam=cam_wide, res=res_wide, fov=FOV_WIDE, spp=spp_wide,
             show_devices=dev_in_wide, rec=rec_wide,
             what_ko="배치 전체 — 옆에서 본 레이더(TX·RX 한 점)와 표적, 그 사이 3 m"),
    ]

    print(f"\n═══ {spec.name} 호버 애니메이션 (재제작) ═══")
    print(f"  시나리오 출처 : {sc['source']}")
    print(f"  기선          : {sc['baseline_m']:.3f} m — {sc['baseline_source']}")
    print(f"  GPU {GPU_INFO['gpu']} (여유 {GPU_INFO['free_mb']} MiB) — {GPU_INFO['why_ko']}")
    print(f"  f_flash {sc['f_flash_hz']:.2f} Hz · 블레이드 주기 {T*1e3:.3f} ms × {a.periods}")
    print(f"  로터별 rpm {np.round(rpms, 1).tolist()} · 방향 {fp.dirs}")
    print(f"  프레임 {n_f} 장 · 프레임당 {deg_per_frame:.2f}° (실시간 {dt_real*1e3:.3f} ms)")
    print(f"  위칸 {res_main[0]}×{res_main[1]} spp {spp_main} "
          f"(버퍼 {res_main[0]*res_main[1]*spp_main*4/1e9:.2f} GB, 장치 {dev_in_main})")
    print(f"  아래칸 {res_wide[0]}×{res_wide[1]} spp {spp_wide} "
          f"(버퍼 {res_wide[0]*res_wide[1]*spp_wide*4/1e9:.2f} GB, 장치 {dev_in_wide})")
    print(f"  재생 {playback_s:.2f} s @ {a.ms} ms → ⭐슬로모션 ×{slowmo:.1f} "
          f"(옛 판 ×274) · 이음매 {seam_deg:.2f}°")
    for m in warn:
        print(f"  ⚠ {m}")
    print(flush=True)

    os.makedirs(FIGDIR, exist_ok=True)
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES, exist_ok=True)

    files, per_frame, geo = [], [], None
    spp_used = {v["key"]: [] for v in views}
    frame_px = None
    t_all = time.time()
    for i in range(n_f):
        t0 = time.time()
        scene, d, mv = posed_scene(fp, spec, ph[i], f"ANIM{i % 2}", sc["fc_hz"])
        geo = RP.place(scene, az=sc["az_deg"], el=sc["el_deg"], rng=sc["range_m"],
                       baseline=sc["baseline_m"])
        #  ⭐ TX·RX 가 같은 점이다(기선 0). 겹친 마커를 정직하게 처리한다:
        #    RX 구를 TX 구 **안에** 넣고 색을 같게 둬서 화면에는 공이 하나만 보이게 한다.
        #    (같은 반지름이면 두 구면이 z-fighting 으로 얼룩진다 — 실측.)
        scene.get("tx").display_radius = DEV_R
        scene.get("rx").display_radius = DEV_R * 0.55
        scene.get("tx").color = DEV_RGB
        scene.get("rx").color = DEV_RGB

        panels = []
        for v in views:
            p = os.path.join(FRAMES, f"{v['key']}_{i:03d}.png")
            #  ⚠ 공용 GPU 라 여유가 프레임 중간에 줄 수 있다. OOM 이면 죽지 말고 spp 를 반으로
            #    줄여 다시 시도한다(프레임마다 다른 spp 는 밝기가 아니라 잡음만 바꾼다).
            spp_i = v["spp"]
            while True:
                try:
                    scene.render_to_file(camera=v["cam"], filename=p, num_samples=spp_i,
                                         resolution=v["res"], fov=v["fov"],
                                         show_devices=v["show_devices"],
                                         show_orientations=False)
                    break
                except Exception as e:
                    if spp_i <= 32:
                        raise
                    spp_i //= 2
                    print(f"    ⚠ 프레임 {i} [{v['key']}] 렌더 실패({type(e).__name__})"
                          f" → spp {spp_i} 로 재시도", flush=True)
            spp_used[v["key"]].append(int(spp_i))
            white_png(p)
            panels.append(p)

        f = os.path.join(FRAMES, f"frame_{i:03d}.png")
        frame_px = stack_panels(panels, f)
        for p in panels:
            os.remove(p)
        files.append(f)

        RP.drop_scratch(d)
        del scene
        try:                                              # 프레임마다 GPU 메모리 반환
            import drjit as dr
            dr.flush_malloc_cache()
        except Exception:
            pass
        per_frame.append(time.time() - t0)
        if i == 0 or (i + 1) % 8 == 0 or i == n_f - 1:
            done = time.time() - t_all
            print(f"    프레임 {i+1:3d}/{n_f}  {per_frame[-1]:5.2f}s  "
                  f"누적 {done:6.1f}s  ETA {(n_f-i-1)*np.mean(per_frame):6.1f}s", flush=True)
    render_s = time.time() - t_all

    if a.smoke:
        print(f"\n[smoke] 프레임만 확인: {FRAMES}  ({frame_px[0]}×{frame_px[1]})")
        print(f"  위칸 카메라 {rec_main}\n  아래칸 카메라 {rec_wide}")
        return

    shutil.copyfile(files[0], POSTER)                     # 정지컷 = 첫 프레임(렌더 해상도 그대로)
    gif = build_gif(files, GIF, ms=a.ms)

    rec = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "script": "benchmark/render_md_anim.py",
            "purpose_ko": ("리포트 07 — 호버링은 «정지» 가 아니다. 기체는 제자리, 프로펠러만 돈다. "
                           "그 회전이 마이크로도플러의 원천이라는 것을 움직임으로 보여준다. "
                           "이 판은 (1) 회전을 그럴듯한 속도로 올리고 (2) TX/RX 를 화면에 넣었다."),
            "revision_ko": ("2026-08-10 재제작. 옛 판은 36 프레임×60 ms 로 블레이드 한 주기만 덮어 "
                            "슬로모션 ×274 였고 TX/RX 를 껐다(show_devices=False)."),
            "scenario_source": sc["source"],
            "drone": sc["drone"], "name": spec.name,
            "fc_hz": sc["fc_hz"], "az_deg": sc["az_deg"], "el_deg": sc["el_deg"],
            "range_m": sc["range_m"],
            "baseline_m": sc["baseline_m"], "baseline_source": sc["baseline_source"],
            "determinism_ko": ("Scene.render_to_file 에는 시드 인자가 없다(서명 실측). "
                               "재현성은 자세(rpm·프레임 수로 계산)·카메라(회전 포락선에서 역산)·"
                               "spp·해상도가 모두 결정론적이라는 데서 온다."),
            "warnings": warn,
        },
        "gpu": GPU_INFO,
        "rotors": {
            "n_rotors": int(spec.num_rotors), "prop_blades": int(sc["blades"]),
            "prop_dia_mm": float(spec.prop_dia_mm),
            "rpm_per_rotor": [float(x) for x in rpms],
            "rpm_mean": float(rpms.mean()),
            "rpm_ptp_over_mean": float((rpms.max() - rpms.min()) / rpms.mean()),
            "rpm_spread_frac_scenario": (float(sc["meta"]["rpm_spread_frac"])
                                         if "rpm_spread_frac" in sc["meta"] else None),
            "spin_dirs": [int(x) for x in fp.dirs],
            "note_ko": ("로터별 rpm 과 CW/CCW 는 FastPoser/시나리오 JSON 이 정한 것을 그대로 썼다 "
                        "— 이 스크립트는 회전 방향을 새로 정하지 않는다."),
        },
        #  ⭐ 속도 산수 — 사용자 지적("너무 느리게 돈다")에 대한 계산 근거를 한 자리에 모은다
        "speed": {
            "hover_rpm_mean": float(rpms.mean()),
            "rev_per_s": float(rpms.mean() / 60.0),
            "seconds_per_rev_ms": float(60.0 / rpms.mean() * 1e3),
            "blade_symmetry_deg": float(360.0 / sc["blades"]),
            "blade_period_ms": float(T * 1e3),
            "rotor_deg_per_frame": float(deg_per_frame),
            "real_ms_per_frame": float(dt_real * 1e3),
            "frame_delay_ms": int(a.ms),
            "slowmotion_factor": float(slowmo),
            "playback_s": float(playback_s),
            "loop_real_ms": float(a.periods * T * 1e3),
            "chain_ko": (f"호버 {rpms.mean():.0f} rpm → 1회전 {60.0/rpms.mean()*1e3:.2f} ms → "
                         f"프레임당 {deg_per_frame:.2f}° = 실시간 {dt_real*1e3:.3f} ms → "
                         f"표시 {a.ms} ms/프레임 → 슬로모션 ×{slowmo:.1f}"),
            "previous_slowmotion": 273.6,
            "wagon_wheel_ko": (f"프레임당 {deg_per_frame:.1f}° 는 2엽 대칭각 "
                               f"{360.0/sc['blades']:.0f}° 의 {deg_per_frame/(360.0/sc['blades'])*100:.0f}% "
                               f"— 50% 를 넘으면 역회전처럼 보인다. 안전 구간."),
            "browser_delay_rule_ko": ("GIF 지연이 20 ms 미만이면 브라우저가 100 ms 로 올린다. "
                                      f"{a.ms} ms 는 그 위라 그대로 재생된다."),
        },
        #  ⚠ **깨면 안 되는 키**: src/make_report07_overview.py 가 §0 문장을 짤 때
        #    loop.blade_period_ms · loop.blade_deg_per_frame · loop.n_frames 를 읽는다
        #    (rotors.rpm_mean · _meta.name/az_deg/el_deg 도). 이름을 바꾸면 리포트 빌드가
        #    KeyError 로 죽는다 — 그 파일은 다른 작업자 소유라 여기서 못 고친다.
        "loop": {
            "f_flash_hz": float(sc["f_flash_hz"]),
            "blade_period_ms": float(T * 1e3),
            "n_periods": int(a.periods),
            "loop_real_ms": float(a.periods * T * 1e3),
            "n_frames": int(n_f),
            "blade_deg_per_frame": float(deg_per_frame),
            "rotor_deg_per_frame": float(deg_per_frame),
            "playback_s": float(playback_s),
            "frame_delay_ms": int(a.ms),
            "slowmotion_factor": float(slowmo),
            "unique_visual_phases": float(unique_phases),
            "repeats_in_clip": float(n_f / unique_phases),
            "seam_mismatch_deg": float(seam_deg),
            "seam_note_ko": ("로터마다 rpm 이 달라 루프 끝의 위상이 시작 위상과 정확히 안 맞는다. "
                             "그 어긋남이 seam_mismatch_deg 다. 주기를 많이 담을수록 커진다 "
                             f"(옛 판은 1 주기 0.40°, 이 판은 {a.periods} 주기 {seam_deg:.2f}°)."),
            "honesty_ko": (f"프레임당 {deg_per_frame:.1f}° 이므로 {unique_phases:.0f} 프레임마다 "
                           f"형상이 되돌아온다. {n_f} 프레임 클립은 그 시각 주기를 "
                           f"{n_f/unique_phases:.0f} 번 담은 **영상**이다 — 주기운동을 찍은 실제 "
                           f"영상이 그렇듯이. 로터별 rpm 이 달라 되풀이가 완전히 같지는 않고, "
                           f"클립 끝까지 누적 어긋남이 {seam_deg:.2f}° 다."),
        },
        "render": {
            "engine": "Sionna RT scene.render_to_file (Mitsuba path tracer)",
            "layout_ko": ("한 프레임 = 두 칸 세로 쌓기. 위칸 근접(드론 크게) · 아래칸 배치 전체"
                          "(TX/RX 포함). 사이는 흰 여백만 — 선도 글자도 없다."),
            "frame_px": [int(frame_px[0]), int(frame_px[1])],
            "gutter_px": GUTTER,
            "views": [
                dict(key=v["key"], resolution=[int(v["res"][0]), int(v["res"][1])],
                     fov_deg=float(v["fov"]), spp_requested=int(spp_req),
                     spp_used=int(v["spp"]),
                     spp_actual_min=int(min(spp_used[v["key"]])),
                     spp_actual_max=int(max(spp_used[v["key"]])),
                     spp_downgraded_frames=int(sum(1 for s in spp_used[v["key"]]
                                                   if s < v["spp"])),
                     sample_buffer_gb=float(v["res"][0] * v["res"][1] * v["spp"] * 4 / 1e9),
                     show_devices=bool(v["show_devices"]), camera=v["rec"],
                     what_ko=v["what_ko"])
                for v in views
            ],
            "spp_autofit_ko": (f"요청 spp {spp_req} 를 시작 시점 여유 메모리 "
                               f"{GPU_INFO['free_mb']} MiB 의 {MEM_FRAC:.0%} 안에 들어오도록 깎았다 "
                               f"(위칸 {spp_main} · 아래칸 {spp_wide}). 그래도 OOM 이면 "
                               f"프레임 단위로 반씩 줄여 재시도한다."),
            "devices": {
                "tx": geo["tx"], "rx": geo["rx"],
                "baseline_m": geo["baseline_m"], "bistatic_deg": geo["bistatic_deg"],
                "tau_expect_ns": geo["tau_expect_ns"],
                "display_radius_tx_m": DEV_R, "display_radius_rx_m": DEV_R * 0.55,
                "color_rgb": list(DEV_RGB),
                "overlap_ko": ("기선 0 = 진짜 모노스태틱이라 TX 와 RX 가 같은 점이다. "
                               "RX 구를 TX 구 안에 넣고 색을 같게 둬서 화면에는 **공 하나**만 "
                               "보인다 — 같은 반지름이면 두 구면이 z-fighting 으로 얼룩진다. "
                               "글자는 넣지 않았다(규약)."),
                "render_note_ko": ("Sionna 는 장치를 **발광 구**로 별도 렌더해 깊이로 합성한다"
                                   "(renderer.get_overlay_scene 실측) — 씬 조명을 바꾸지 않으므로 "
                                   "장치를 켜도 드론의 밝기·재질 표현은 그대로다."),
            },
            "background": "white (viz_report1._whiten 과 같은 밝기-알파 합성)",
            "text_in_figure": "none (규약: 렌더 안에 글자·눈금·라벨 금지)",
            "seconds_total": float(render_s),
            "seconds_per_frame_mean": float(np.mean(per_frame)),
            "seconds_per_frame_min": float(np.min(per_frame)),
            "seconds_per_frame_max": float(np.max(per_frame)),
        },
        "outputs": {
            "gif": os.path.relpath(GIF, ROOT),
            "poster_png": os.path.relpath(POSTER, ROOT),
            "gif_size_mb": gif["size_mb"], "gif_px": [gif["width"], gif.get("height")],
            "gif_colors": gif["colors"], "gif_delay_ms": gif["delay_ms"],
            "gif_n_frames": gif["n_frames"],
            "gif_under_limit": gif["under_limit"], "gif_max_mb": gif["max_mb"],
            "gif_attempts": gif["attempts"],
        },
        #  ⭐ 리포트 §0 본문에 넣을 문단 초안 — 숫자는 위 기록에서 그대로 뽑아 쓴다(손입력 금지).
        #     ⚠ make_report07_overview.py 는 이 스크립트가 건드리지 않는다. 초안만 남긴다.
        "report_paragraph_ko": (
            f"호버링하는 {spec.name}. 아래칸이 배치다 — 붉은 공 하나가 레이더고, 거기서 "
            f"{sc['range_m']:.0f} m 떨어진 곳에 드론이 떠 있다(고각 {sc['el_deg']:.0f}°, 즉 "
            f"레이더가 드론을 올려다본다). 공이 하나인 이유는 기선이 0 인 **진짜 모노스태틱**이라 "
            f"송신기와 수신기가 같은 점에 있기 때문이다. 위칸은 그 레이더 시선에서 드론을 당겨 본 "
            f"모습이고, 볼 것은 하나다 — 동체는 한 픽셀도 안 움직이는데 프로펠러 "
            f"{int(spec.num_rotors)}개의 날 방향만 프레임마다 바뀐다(호버 {rpms.mean():.0f} rpm, "
            f"로터마다 조금씩 다르고 CW/CCW 가 섞여 있다). 그 바뀌는 부분이 되돌아오는 신호의 "
            f"위상을 흔들고, 그것이 이 편에서 다루는 마이크로도플러다. "
            f"⚠ 실제 날은 초당 {rpms.mean()/60:.0f} 바퀴를 돌아 눈으로는 볼 수 없다 — 이 "
            f"애니메이션은 프레임 사이 실시간 {dt_real*1e3:.2f} ms 를 {a.ms} ms 로 늘여 튼 "
            f"약 {slowmo:.0f} 배 슬로모션이다(프레임당 {deg_per_frame:.0f}° 회전)."),
        "reproduce": ("SIONNA2_GPU=%d PYTHONPATH=src python benchmark/render_md_anim.py "
                      "--frames %d --periods %d --spp %d --width %d --ms %d" %
                      (GPU_INFO["gpu"], n_f, a.periods, spp_req, ww, a.ms)),
    }
    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)

    if not a.keep_frames:
        shutil.rmtree(FRAMES, ignore_errors=True)

    print(f"\n✅ {os.path.relpath(GIF, ROOT)}  {gif['size_mb']:.2f} MB "
          f"({gif['width']}×{gif.get('height')} · {gif['colors']}색 · {n_f} 프레임 @ {a.ms} ms)")
    print(f"✅ {os.path.relpath(POSTER, ROOT)}  ({frame_px[0]}×{frame_px[1]})")
    print(f"✅ {os.path.relpath(OUTJ, ROOT)}")
    print(f"   렌더 {render_s:.1f}s (프레임당 {np.mean(per_frame):.2f}s) · "
          f"⭐슬로모션 ×{slowmo:.1f} (옛 판 ×274) · 이음매 {seam_deg:.2f}°")


if __name__ == "__main__":
    main()
