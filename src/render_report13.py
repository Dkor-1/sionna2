# -*- coding: utf-8 -*-
"""
render_report13.py — report13 (자유공간 검지거리) **Sionna RT 자체 렌더**
================================================================================
report13 은 챔버를 벗어난 **자유공간(FS-1)** 편이다. 이 모듈은 그 무대·표적을
**Sionna RT 렌더러(Mitsuba 백엔드)로 실제로 그린다** — 도식이 아니라 시뮬레이터가 본 것.

무엇을 그리나 (spec §12)
  RT GIF
    R1  r13_five_lineup_orbit.gif  — 전 기종 동일축척 1열(target_extent 순) 궤도
    R2  r13_aspect_<drone>.gif ×5  — 기종별 드론 yaw 0→360°(프롭위상), 시선 el=el_look(음수)
    R3  r13_geometry_orbit.gif     — 자유공간 바이스태틱 기하(TX마스트25/RX3/표적, 바닥·벽 없음)
    R4  r13_scale_zoom.gif         — powers-of-ten 줌(20km→…→1m 메쉬), 마지막 8f만 RT
  스틸 22장 (outputs/renders/r13_*.png)
    r13_10_<drone>_aspect_{best,median,worst}.png  15장 — 자세각=σ격자 p90/p50/p10 az
    r13_20_five_row.png                             1장 — 전 기종 동일축척(target_extent 순)
    r13_30_geometry_schematic.png                   1장 — TX마스트·RX·표적(스케일브레이크 명시)
    r13_40_<drone>_material.png ×3                  3장 — mini5pro/matrice4e/s1000plus(재질색)
    r13_50_{belly,top}.png ×2                       2장 — 같은 기체 el=−15° vs +15°(F9 근거)

★ 설계 근거 (왜 이렇게 했나)
  1. **챔버 금지.** report01~12 는 무향실 30×20×11 안이지만 report13 은 FS-1(자유공간)이다.
     그래서 `render_rt.make_scene(with_chamber=False)` 만 쓰고 챔버 하드코딩 카메라 `render_rt.CAMS`
     는 **절대 쓰지 않는다**(챔버 좌표에 묶여 있음). 프레이밍은 메쉬 span 에서 매번 계산한다.
  2. **render_rt.make_gif 는 수정 금지 · 호출만.** GIF 배경 흰합성은 신규 `_gif_white()` 가
     프레임별로 먼저 하고 나서 `make_gif` 를 그대로 부른다(리포트는 흰 배경).
  3. **프레임 디렉토리는 render_anim._framedir() 로 먼저 비운다** — 프레임 수가 줄면 옛 프레임이
     새 GIF 에 섞여 표적이 순간이동하던 아티팩트를 막는다(render_anim 주석의 감사 교훈 계승).
  4. **⚠ 해상도 상한.** 2560×1600×spp4096 은 OOM(sionna2-gpu-policy 메모). 스틸 ≤1600×1200@spp1536,
     GIF ≤1600×900@spp512. **스모크는 저해상도 스틸 1장만**(--smoke).
  5. **스케일바는 자기교정.** 흰 배경 렌더에서 표적의 **픽셀 바운딩박스**를 측정해 실제 크기(span[m])와
     대응시켜 1 m 바를 그린다 — 원근 렌더에서 손으로 px/m 를 못 박는 문제를 측정으로 해결한다.
     마커만 있는 기하 장면은 자기교정이 불가하므로 스케일브레이크 텍스트만 넣는다(정직).
  6. **자세각은 σ격자 JSON 에서 읽는다**(spec §12): best=p90 az, median=p50, worst=p10.
     격자(`outputs/report13_sigma_grid.json`)가 아직 없으면(다른 그룹 산출물) 고정 방위로
     graceful 대체하고 경고를 찍는다 — 렌더 자체는 돈다.

실행 (렌더는 GPU 필요, SIONNA2_GPU=3 권장):
  SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/render_report13.py --smoke      # 스모크(스틸 1장→/tmp)
  SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/render_report13.py --which stills
  SIONNA2_GPU=3 PYTHONPATH=src:benchmark python src/render_report13.py --which gifs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

# ⚠ mitsuba/OptiX 는 import 시점에 CUDA_VISIBLE_DEVICES 를 읽는다. scene_build import 가
#   gpu.pick() 을 부르므로, 그 전에 SIONNA2_GPU 를 못박아야 한다(spec §12: 렌더=GPU3).
#   호출자가 이미 세팅했으면 존중(setdefault).
os.environ.setdefault("SIONNA2_GPU", "3")

_HERE = os.path.dirname(os.path.abspath(__file__))
_BENCH = os.path.abspath(os.path.join(_HERE, "..", "benchmark"))
for _p in (_HERE, _BENCH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                              # noqa: E402

# 렌더 엔진·헬퍼는 전부 **기존 모듈 import**(재구현 금지, spec §9/규칙 3).
from render_rt import make_scene, cam, make_gif, OUT, DMESH, FC  # noqa: E402
from render_anim import _framedir                                # noqa: E402  프레임 디렉토리 청소 규약
from scene_build import build_scene, drone_parts                 # noqa: E402
import mitsuba as mi                                             # noqa: E402
import sionna.rt as rt                                           # noqa: E402
from drones import DRONES, build_drone                           # noqa: E402
from freespace_scene import (FS_TX, FS_RX, target_pos,           # noqa: E402
                             DRONE_ORDER, L_REF, PHI_HEADLINE_DEG, FS_ALT)

ROOT = os.path.abspath(os.path.join(_HERE, ".."))
ANIM = os.path.join(OUT, "anim")                                 # RT GIF 산출 경로 = outputs/renders/anim
SIGMA_JSON = os.path.join(ROOT, "outputs", "report13_sigma_grid.json")

# 스틸/오빗 상한(spec §12, OOM 회피). 스모크는 이보다 훨씬 작게 별도 지정.
STILL_RES = (1600, 1200)
STILL_SPP = 1536
GIF_RES = (1600, 900)
GIF_SPP = 512


# =========================================================================== #
#  기하 헬퍼
# =========================================================================== #
def _span(drone: str) -> float:
    """드론 메쉬의 3D 대각 span[m] — 프레이밍 반경 계산용(render_rt 규약과 동일)."""
    V = np.asarray(build_drone(DRONES[drone]).v, float)
    return float(np.linalg.norm(V.max(0) - V.min(0)))


def _extent_xy(drone: str) -> float:
    """드론의 최대 수평 크기[m] — 스케일바 자기교정용(bbox x/y 중 큰 쪽)."""
    V = np.asarray(build_drone(DRONES[drone]).v, float)
    d = V.max(0) - V.min(0)
    return float(max(d[0], d[1]))


def _orbit_cams(center, radius, height_frac, n, look=None):
    """center 둘레를 도는 카메라 (pos, look) 리스트. height_frac=수직 높이/radius."""
    look = tuple(center) if look is None else look
    cams = []
    for k in range(n):
        th = 2 * np.pi * k / n
        pos = (center[0] + radius * np.cos(th),
               center[1] + radius * np.sin(th),
               center[2] + radius * height_frac)
        cams.append((pos, look))
    return cams


# =========================================================================== #
#  흰 배경 합성 · 스케일바 · GIF (신규 — render_rt.make_gif 는 건드리지 않는다)
# =========================================================================== #
def _white_png(path: str) -> str:
    """검정 배경 렌더를 흰 배경으로 제자리 합성(밝기 알파). viz_report1._whiten 과 동일 규약."""
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB"), float) / 255.0
    lum = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
    if np.mean([lum[0, 0], lum[0, -1], lum[-1, 0], lum[-1, -1]]) > 0.6:
        return path                                             # 이미 흰 배경
    a = np.clip((lum - 0.025) / 0.14, 0, 1)
    comp = im * a[..., None] + (1 - a[..., None])
    Image.fromarray((np.clip(comp, 0, 1) * 255).astype("uint8")).save(path)
    return path


def _obj_bbox_px(path: str, thr: float = 0.985):
    """흰 배경 PNG 에서 표적(비-흰 픽셀)의 픽셀 바운딩박스 (x0,y0,x1,y1). 없으면 None.
    스케일바 자기교정에 쓴다 — 손으로 px/m 를 못박지 않고 **렌더된 크기를 측정**한다."""
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB"), float) / 255.0
    lum = 0.299 * im[..., 0] + 0.587 * im[..., 1] + 0.114 * im[..., 2]
    mask = lum < thr
    if not mask.any():
        return None
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _scalebar(path: str, obj_width_m: float | None = None, label: str = "1 m",
              scale_break: bool = False) -> str:
    """RT 프레임에 (a) 1 m 스케일바 (b) 스케일브레이크 텍스트를 강제로 얹는다(spec §12).

    ★ obj_width_m 이 주어지면 **자기교정**: 흰 배경에서 표적의 픽셀 폭을 재서
      px_per_m = bbox_px / obj_width_m 로 1 m 바 길이를 구한다(원근 근사, 표적 평면 기준).
      마커만 있는 장면(기하 오빗 등)은 obj_width_m=None 으로 두면 바 없이 스케일브레이크만 넣는다.
    영문 텍스트만 사용(그림 텍스트 영어 규칙)."""
    from PIL import Image, ImageDraw
    im = Image.open(path).convert("RGB")
    W, H = im.size
    dr = ImageDraw.Draw(im)
    pad = max(10, W // 60)
    if scale_break:
        txt = "scale break"
        dr.text((W // 2 - 4 * len(txt), pad), txt, fill=(200, 40, 40))
    bar_px, bar_label = None, label
    if obj_width_m is not None and obj_width_m > 0:
        bb = _obj_bbox_px(path)
        if bb is not None and bb[2] > bb[0]:
            px_per_m = (bb[2] - bb[0]) / obj_width_m
            # 1 m 가 화면을 넘으면(표적이 프레임을 꽉 채운 클로즈업) 들어맞는 가장 큰 '깔끔한' 길이로 낮춘다.
            for L, lab in ((1.0, "1 m"), (0.5, "0.5 m"), (0.2, "0.2 m"),
                           (0.1, "0.1 m"), (0.05, "5 cm")):
                cand = px_per_m * L
                if 6 <= cand <= 0.42 * W:
                    bar_px, bar_label = cand, lab
                    break
    x0, y0 = pad, H - pad
    if bar_px is not None:
        dr.line([(x0, y0), (x0 + bar_px, y0)], fill=(20, 20, 20), width=max(2, H // 260))
        for xx in (x0, x0 + bar_px):                            # 끝 캡
            dr.line([(xx, y0 - 6), (xx, y0 + 6)], fill=(20, 20, 20), width=max(2, H // 300))
        dr.text((x0, y0 - 20), bar_label, fill=(20, 20, 20))
    else:
        # 자기교정 불가(마커 장면 등) — 바 대신 안내 텍스트만(날조 금지)
        dr.text((x0, y0 - 16), "scale: see caption", fill=(90, 90, 90))
    im.save(path)
    return path


def _gif_white(frame_dir: str, gif_path: str, ms: int = 90) -> str:
    """프레임별 흰 배경 합성 후 make_gif 로 조립(render_rt.make_gif **수정 안 함**, 호출만)."""
    import glob
    for f in sorted(glob.glob(os.path.join(frame_dir, "frame_*.png"))):
        _white_png(f)
    os.makedirs(os.path.dirname(gif_path), exist_ok=True)
    return make_gif(frame_dir, gif_path, ms=ms)


# =========================================================================== #
#  단일 스틸 렌더 (out_dir 지정 가능 — 스모크는 /tmp, 실산출은 outputs/renders)
# =========================================================================== #
def _render_still(scene, name: str, campos, look, out_dir: str,
                  res=STILL_RES, spp=STILL_SPP, fov=35.0,
                  obj_width_m: float | None = None, scale_break: bool = False,
                  scalebar: bool = True, clip=None) -> str:
    """scene 을 out_dir/name.png 로 렌더 → 흰 배경 → 스케일바. 경로 반환.
    렌더 자체는 Sionna 의 scene.render_to_file(=render_rt.shot 이 내부에서 쓰는 것과 동일)."""
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, f"{name}.png")
    t0 = time.time()
    scene.render_to_file(camera=cam(campos, look), filename=p, num_samples=spp,
                         resolution=res, fov=fov, clip_at=clip)
    _white_png(p)
    if scalebar:
        _scalebar(p, obj_width_m=obj_width_m, scale_break=scale_break)
    print(f"  [still] {os.path.relpath(p, ROOT):52s} ({time.time()-t0:5.1f}s)")
    return p


# =========================================================================== #
#  자세각 조회 — σ격자 JSON 에서 p10/p50/p90 방위(best/median/worst)
# =========================================================================== #
def _aspect_azimuths(drone: str, grid: dict | None) -> dict:
    """σ격자에서 드론의 방위별 σ 분포를 읽어 best(p90)/median(p50)/worst(p10) 방위[deg]를 정한다.

    ★ 격자 스키마는 experiment_freespace_sigma.py(다른 그룹)가 확정한다 — 아직 없으면
      여러 개연적 경로를 시도하고, 실패하면 고정 방위(0/90/180)로 graceful 대체 + 경고.
      렌더가 멈추지 않는 것이 우선(스펙: '없으면 graceful')."""
    default = {"best": 0.0, "median": 90.0, "worst": 180.0, "_source": "fallback(fixed az)"}
    if not grid:
        return default
    # 개연적 경로들: sigma.grid[drone] 아래 az 배열 + σ(dBsm) 배열을 찾는다.
    node = grid.get("sigma", grid).get("grid", grid) if isinstance(grid, dict) else None
    cand = None
    if isinstance(node, dict):
        cand = node.get(drone)
    if cand is None and isinstance(grid.get("drones"), dict):
        cand = grid["drones"].get(drone)
    if not isinstance(cand, dict):
        return default
    # cand 가 밴드중첩({band:{sigma_smooth_dbsm,az_deg,el_deg}}) 이면 @3.5 GHz 밴드 선택.
    if "az_deg" not in cand and "az" not in cand:
        cand = cand.get("5G NR 3.5 GHz") or next(iter(cand.values()), None)
        if not isinstance(cand, dict):
            return default
    az = cand.get("az_deg") or cand.get("az")
    # σ 는 (밴드×주파×el×az) 다차원일 수 있다 — az 축으로 평균낸 1D 를 찾거나 만든다.
    sig = (cand.get("sigma_az_dbsm") or cand.get("sigma_smooth_dbsm")
           or cand.get("sigma_smooth") or cand.get("mean_dbsm") or cand.get("sigma"))
    try:
        az = np.asarray(az, float).ravel()
        sig = np.asarray(sig, float)
        while sig.ndim > 1:
            sig = np.nanmean(sig, axis=0)
        if az.shape[0] != sig.shape[0] or az.size == 0:
            return default
        p10, p50, p90 = np.percentile(sig, [10, 50, 90])
        worst = float(az[int(np.argmin(np.abs(sig - p10)))])
        median = float(az[int(np.argmin(np.abs(sig - p50)))])
        best = float(az[int(np.argmin(np.abs(sig - p90)))])
        return {"best": best, "median": median, "worst": worst, "_source": "sigma_grid"}
    except Exception:
        return default


def _load_sigma_grid() -> dict | None:
    if os.path.exists(SIGMA_JSON):
        try:
            return json.load(open(SIGMA_JSON, encoding="utf-8"))
        except Exception:
            pass
    return None


# =========================================================================== #
#  다중 드론 1열(lineup) 자유공간 씬 — 챔버·바닥 없음
# =========================================================================== #
def _lineup_scene(order=DRONE_ORDER, gap=1.4):
    """전 기종(DRONE_ORDER)을 target_extent 순으로 y축 1열 배치한 자유공간 씬 + 전체 폭·중심 반환.
    챔버·바닥·TX/RX 없음(순수 표적 5개). 인접 간격 = 큰 쪽 span × gap."""
    spans = {k: _span(k) for k in order}
    ys, y = [], 0.0
    for i, k in enumerate(order):
        if i > 0:
            y += 0.5 * (spans[order[i - 1]] + spans[k]) * gap
        ys.append(y)
    y0 = 0.5 * (ys[0] + ys[-1])                                 # 중앙 정렬
    parts = []
    for k, yc in zip(order, ys):
        dp, _ = drone_parts(DRONES[k], position=(0.0, yc - y0, 0.0), yaw_deg=0.0,
                            mesh_dir=os.path.join(DMESH, k))
        parts += dp
    scene = build_scene(parts, fc=FC)
    total = (ys[-1] - ys[0]) + spans[order[-1]]
    center = (0.0, 0.0, 0.0)
    return scene, total, center, spans


# =========================================================================== #
#  기하 스키매틱 씬 — 자유공간 바이스태틱(TX 마스트/RX/표적), 바닥·벽 없음
# =========================================================================== #
def _geometry_scene(drone="mavic4pro", L=L_REF, d=None, compress=None):
    """자유공간 바이스태틱 기하 씬: TX 마스트(0,0,25) · RX(L,0,3) · 표적.
    ⚠ 실제 L=500 m·표적 0.5 m 는 렌더에 담으면 표적이 사실상 안 보인다(그게 scale 문제의 핵심).
      그래서 **compress 배율**로 TX/RX 를 압축해 한 화면에 담고, 프레임에 'scale break' 를 강제한다.
      표적은 실제 크기 그대로 둔다(크기 대비를 정직하게)."""
    d = 0.35 * L if d is None else d
    P = target_pos(d, PHI_HEADLINE_DEG, L, FS_ALT[0])           # 표적 실좌표
    compress = compress if compress is not None else (8.0 / max(L, 1.0))  # 500m→~8m 로 압축
    tx = tuple(np.asarray(FS_TX) * compress)
    rx = tuple(np.asarray(FS_RX(L)) * compress)
    pc = tuple(np.asarray(P) * compress)
    dp, _ = drone_parts(DRONES[drone], position=pc, yaw_deg=0.0,
                        mesh_dir=os.path.join(DMESH, drone))
    scene = build_scene(dp, fc=FC)
    scene.tx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    scene.rx_array = rt.PlanarArray(num_rows=1, num_cols=1, pattern="iso", polarization="V")
    T = rt.Transmitter("tx", position=mi.Point3f(*[float(v) for v in tx]))
    R = rt.Receiver("rx", position=mi.Point3f(*[float(v) for v in rx]))
    T.display_radius = 0.6
    R.display_radius = 0.6
    scene.add(T)
    scene.add(R)
    span = float(np.linalg.norm(np.asarray(rx) - np.asarray(tx)))
    center = tuple((np.asarray(tx) + np.asarray(rx) + np.asarray(pc)) / 3.0)
    return scene, span, center, compress


# =========================================================================== #
#  스틸 22장
# =========================================================================== #
def still_five_row(out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> str:
    """r13_20_five_row — 전 기종 동일축척 1열(target_extent 순)."""
    scene, total, center, spans = _lineup_scene()
    r = total * 0.95
    campos = (r * 0.85, -r * 0.55, r * 0.28)                   # 약간 위·앞에서 1열 조망
    return _render_still(scene, "r13_20_five_row", campos, center, out_dir,
                         res=res, spp=spp, fov=42.0, obj_width_m=total)


def still_aspect(drone: str, grid=None, out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> dict:
    """r13_10_<drone>_aspect_{best,median,worst} — σ p90/p50/p10 방위에서 본 3장."""
    az = _aspect_azimuths(drone, grid)
    sc = make_scene(drone=drone, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
    span = _span(drone)
    r = span * 1.12
    el = -0.26                                                 # 살짝 아래에서(배 belly 강조, FS-1 시선)
    out = {}
    for tag in ("best", "median", "worst"):
        a = np.deg2rad(az[tag])
        campos = (r * np.cos(a) * np.cos(el), r * np.sin(a) * np.cos(el), r * np.sin(el) + 0.03 * span)
        out[tag] = _render_still(sc, f"r13_10_{drone}_aspect_{tag}", campos, (0, 0, 0),
                                 out_dir, res=res, spp=spp, fov=35.0, obj_width_m=_extent_xy(drone))
    out["_az_source"] = az["_source"]
    return out


def still_geometry_schematic(out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> str:
    """r13_30_geometry_schematic — TX 마스트·RX·표적(scale break 강제)."""
    scene, span, center, comp = _geometry_scene()
    r = span * 1.25
    campos = (center[0] + r * 0.4, center[1] - r, center[2] + r * 0.45)
    # 마커 장면이라 자기교정 불가 → obj_width_m=None, scale break 텍스트만(정직)
    return _render_still(scene, "r13_30_geometry_schematic", campos, center, out_dir,
                         res=res, spp=spp, fov=40.0, obj_width_m=None, scale_break=True)


def still_material(drone: str, out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> str:
    """r13_40_<drone>_material — 재질색이 보이는 클로즈업(iso)."""
    sc = make_scene(drone=drone, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
    r = _span(drone) * 1.12
    campos = (r * 0.74, -r * 0.60, r * 0.34)
    return _render_still(sc, f"r13_40_{drone}_material", campos, (0, 0, 0), out_dir,
                         res=res, spp=spp, fov=35.0, obj_width_m=_extent_xy(drone))


def still_belly_vs_top(drone="mavic4pro", out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> dict:
    """r13_50_{belly,top} — 같은 기체 el=−15°(배) vs +15°(등). F9 시각 근거."""
    sc = make_scene(drone=drone, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
    r = _span(drone) * 1.12
    out = {}
    for tag, el_deg in (("belly", -15.0), ("top", +15.0)):
        el = np.deg2rad(el_deg)
        campos = (r * np.cos(el), -0.15 * r, r * np.sin(el))
        out[tag] = _render_still(sc, f"r13_50_{tag}", campos, (0, 0, 0), out_dir,
                                 res=res, spp=spp, fov=35.0, obj_width_m=_extent_xy(drone))
    return out


def render_all_stills(out_dir=OUT, res=STILL_RES, spp=STILL_SPP) -> dict:
    """스틸 22장 전부."""
    grid = _load_sigma_grid()
    if grid is None:
        print("  ⚠ report13_sigma_grid.json 없음 → 자세각 고정방위 대체(경고)")
    out = {"aspect": {}, "material": {}}
    for k in DRONE_ORDER:
        out["aspect"][k] = still_aspect(k, grid, out_dir, res, spp)              # 15장
    out["five_row"] = still_five_row(out_dir, res, spp)                          # 1장
    out["geometry"] = still_geometry_schematic(out_dir, res, spp)               # 1장
    for k in ("mini5pro", "matrice4e", "s1000plus"):
        out["material"][k] = still_material(k, out_dir, res, spp)                # 3장
    out["belly_vs_top"] = still_belly_vs_top("mavic4pro", out_dir, res, spp)     # 2장
    return out


# =========================================================================== #
#  RT GIF R1~R4
# =========================================================================== #
def gif_five_lineup_orbit(n=48, res=GIF_RES, spp=GIF_SPP, ms=90) -> str:
    """R1 — 전 기종 동일축척 1열 궤도(target_extent 순)."""
    scene, total, center, spans = _lineup_scene()
    name = "r13_five_lineup_orbit"
    fdir = _framedir(name)
    cams = _orbit_cams(center, total * 1.3, 0.32, n)
    for i, (pos, look) in enumerate(cams):
        scene.render_to_file(camera=cam(pos, look), filename=os.path.join(fdir, f"frame_{i:03d}.png"),
                             num_samples=spp, resolution=res, fov=40.0)
    for f in sorted(__import__("glob").glob(os.path.join(fdir, "frame_*.png"))):
        _scalebar(f, obj_width_m=total)                        # 스케일바(흰합성은 _gif_white 가)
    return _gif_white(fdir, os.path.join(ANIM, f"{name}.gif"), ms=ms)


def gif_aspect(drone: str, n=24, res=(900, 900), spp=256, ms=100, grid=None) -> str:
    """R2 — 기종별 드론 yaw 0→360°(프롭 위상), 시선 el=el_look(음수). RT 좌패널.
    ⚠ σ(ψ) 극좌표 다이얼(우패널)은 matplotlib(viz_report13)의 몫 — 여기선 RT 좌패널만 낸다."""
    name = f"r13_aspect_{drone}"
    fdir = _framedir(name)
    span = _span(drone)
    r = span * 1.20
    el = -0.26                                                 # el_look 음수(배를 본다)
    a = np.deg2rad(90.0)                                        # 시선 고정(정면 약간 옆)
    campos = (r * np.cos(a) * np.cos(el), r * np.sin(a) * np.cos(el), r * np.sin(el) + 0.03 * span)
    for i in range(n):
        yaw = 360.0 * i / n
        sc = make_scene(drone=drone, tgt=(0.0, 0.0, 0.0), with_chamber=False, vel=None)
        # yaw 회전: 씬을 새로 만들지 않고 드론 오브젝트 orientation 을 돌린다(프롭 위상 표현)
        for nm, obj in sc.objects.items():
            if nm.startswith(drone):
                obj.orientation = mi.Point3f(0.0, 0.0, float(np.deg2rad(yaw)))
        sc.render_to_file(camera=cam(campos, (0, 0, 0)), filename=os.path.join(fdir, f"frame_{i:03d}.png"),
                          num_samples=spp, resolution=res, fov=32.0)
    for f in sorted(__import__("glob").glob(os.path.join(fdir, "frame_*.png"))):
        _scalebar(f, obj_width_m=_extent_xy(drone))
    return _gif_white(fdir, os.path.join(ANIM, f"{name}.gif"), ms=ms)


def gif_geometry_orbit(n=48, res=(1600, 1100), spp=GIF_SPP, ms=90) -> str:
    """R3 — 자유공간 바이스태틱 기하(TX마스트/RX/표적, 바닥·벽 없음) 궤도. scale break 강제."""
    scene, span, center, comp = _geometry_scene()
    name = "r13_geometry_orbit"
    fdir = _framedir(name)
    cams = _orbit_cams(center, span * 1.3, 0.35, n)
    for i, (pos, look) in enumerate(cams):
        scene.render_to_file(camera=cam(pos, look), filename=os.path.join(fdir, f"frame_{i:03d}.png"),
                             num_samples=spp, resolution=res, fov=45.0)
    for f in sorted(__import__("glob").glob(os.path.join(fdir, "frame_*.png"))):
        _scalebar(f, obj_width_m=None, scale_break=True)
    return _gif_white(fdir, os.path.join(ANIM, f"{name}.gif"), ms=ms)


def gif_scale_zoom(n=40, res=(1280, 860), spp=256, ms=160) -> str:
    """R4 — powers-of-ten 줌(먼 기하 → 표적 메쉬). 매 프레임 스케일바 + 'scale break'.
    ⚠ 실제 '20km→500m→60m→1m' 4단 스케일브레이크의 앞 3단(Cassini/베이스라인/고도)은 도식(matplotlib)
      영역이라, RT 모듈인 여기서는 **기하 씬을 카메라로 줌인**(먼 궤도→표적 클로즈업)해 마지막 구간의
      스케일 문제를 정직하게 보인다. 앞단 도식은 viz_report13(R4 조립)에서 합성한다."""
    scene, span, center, comp = _geometry_scene()
    name = "r13_scale_zoom"
    fdir = _framedir(name)
    r_far, r_near = span * 1.6, span * 0.06
    for i in range(n):
        t = i / (n - 1)
        r = r_far * (r_near / r_far) ** t                      # 로그 줌
        pos = (center[0] + r * 0.5, center[1] - r, center[2] + r * 0.5)
        scene.render_to_file(camera=cam(pos, center), filename=os.path.join(fdir, f"frame_{i:03d}.png"),
                             num_samples=spp, resolution=res, fov=40.0)
    for f in sorted(__import__("glob").glob(os.path.join(fdir, "frame_*.png"))):
        _scalebar(f, obj_width_m=None, scale_break=True)
    return _gif_white(fdir, os.path.join(ANIM, f"{name}.gif"), ms=ms)


def render_all_gifs() -> dict:
    out = {}
    out["R1"] = gif_five_lineup_orbit()
    grid = _load_sigma_grid()
    out["R2"] = {k: gif_aspect(k, grid=grid) for k in DRONE_ORDER}
    out["R3"] = gif_geometry_orbit()
    out["R4"] = gif_scale_zoom()
    return out


# =========================================================================== #
#  스모크 — 저해상도 스틸 1장(2560×1600×4096 OOM 회피, spec §12/규칙 2)
# =========================================================================== #
def smoke(out_dir=None) -> dict:
    """스틸 1장만 저해상도로 렌더해 파이프라인(씬 조립·렌더·흰합성·스케일바)이 도는지 확인.
    산출은 /tmp 스크래치(outputs 오염 금지)."""
    out_dir = out_dir or os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "r13_render_smoke")
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    p = still_material("mavic4pro", out_dir=out_dir, res=(640, 480), spp=96)
    ok = os.path.exists(p) and os.path.getsize(p) > 0
    return {"still": p, "exists": ok, "bytes": os.path.getsize(p) if ok else 0,
            "seconds": round(time.time() - t0, 1),
            "gpu": os.environ.get("CUDA_VISIBLE_DEVICES", os.environ.get("SIONNA2_GPU", "?"))}


# =========================================================================== #
def main():
    ap = argparse.ArgumentParser(description="report13 RT 렌더(자유공간, 챔버 금지)")
    ap.add_argument("--which", default="all",
                    choices=["all", "stills", "gifs", "r1", "r2", "r3", "r4", "smoke"])
    ap.add_argument("--drone", default=None, help="r2(aspect) 특정 드론만")
    ap.add_argument("--smoke", action="store_true", help="저해상도 스틸 1장(/tmp)만")
    a = ap.parse_args()

    if a.smoke or a.which == "smoke":
        print(json.dumps(smoke(), ensure_ascii=False, indent=2))
        return
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(ANIM, exist_ok=True)
    t0 = time.time()
    if a.which in ("all", "stills"):
        render_all_stills()
    if a.which in ("all", "gifs"):
        render_all_gifs()
    if a.which == "r1":
        gif_five_lineup_orbit()
    if a.which == "r2":
        keys = [a.drone] if a.drone else list(DRONE_ORDER)
        grid = _load_sigma_grid()
        for k in keys:
            gif_aspect(k, grid=grid)
    if a.which == "r3":
        gif_geometry_orbit()
    if a.which == "r4":
        gif_scale_zoom()
    print(f"\n✅ report13 렌더 완료 ({time.time()-t0:.0f}s) → {os.path.relpath(OUT, ROOT)}/")


if __name__ == "__main__":
    main()
