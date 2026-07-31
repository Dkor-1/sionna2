# -*- coding: utf-8 -*-
"""
viz_mesh_photo.py — **사진 vs 현재 메쉬**, 실루엣 겹침을 숫자로
==========================================================================

무엇을 하나
-----------
기체 사진 한 장을 고르고, **그 사진의 카메라 자세를 추정해서** 현재 메쉬를 같은 자세로
렌더한 뒤, 두 실루엣을 겹쳐 **IoU 한 숫자**로 일치도를 말한다. 형용사는 쓰지 않는다.
그리고 어긋난 자리는 **색으로 칠하고 면적을 mm² 로 적는다** — 확인만 하는 대조는 증거가 아니다.

측정량의 정의 (그림·JSON 이 쓰는 것과 같은 정의다)
-----------------------------------------------
* **실루엣**   배경에서 분리한 2치 마스크. 사진은 배경색 거리, 메쉬는 표면점 래스터화.
* **IoU**      |교집합| / |합집합|. **최적 정합 뒤**의 값이다 — 아래 자유도를 맞추고 잰다.
* **정합 자유도** 카메라 방위·고각·화면 롤(=SO(3) 전부) · 원근 세기 q · 등방배율 s · 평행이동.
  실루엣 대조는 **형상**을 재는 것이지 사진 속 절대 크기를 재는 게 아니므로 s 는 맞춘다.
  (절대 치수는 제조사 공표값 대조가 하고, 그 숫자는 `outputs/mesh_gallery.json` 에 있다.)
* **프로펠러 위상** 로터마다 **자유 파라미터**다. 사진 속 블레이드 방위는 촬영자가 아무렇게나
  놓은 값이라, 고정하면 IoU 가 형상이 아니라 블레이드 우연을 재게 된다.
* **경계오차**  두 실루엣 윤곽선 사이 **대칭 거리** [mm]. 배율 s 가 px→mm 를 준다.
* **q**        원근 세기. 카메라 거리 D 에 대해 q = span/D. q=0 이 정투영이다.
  제품 사진은 근접 촬영이라 0 이 아니다 — x500v2 SOURCES.md 가 시차로 겪은 그 문제다.

헤드라인은 **선언한 시선방향 안에서** 잰다
------------------------------------------
자유 탐색만 하면 카메라를 실제와 다른 각도로 기울여 형상 차이를 가릴 수 있다. 그래서 두 번 잰다 —
사람이 사진을 보고 선언한 시선방향에서 20° 이내로 묶은 값(헤드라인)과, 묶지 않은 값(비교용).
둘의 차이 `free_iou_gain` 이 곧 정보다: 자유 카메라가 훨씬 높으면 **맞는 각도보다 틀린 각도에
더 잘 맞는다**는 뜻이고, 그건 자세 모호성이 아니라 형상 차이다.

지표에는 **눈금**이 붙어 있다
---------------------------
기체마다 자기 메쉬로 만든 가짜 사진을 같은 파이프라인에 넣어 **상한**을 잰다(`calibrate`).
가는 암·블레이드 때문에 상한은 1.0 이 아니고, 자세가 1° 어긋나면 IoU 가 0.09 떨어진다.
`_meta.metric_calibration` 의 민감도 표가 사진 IoU 를 읽는 기준선이다.

무엇을 만드나
------------
  outputs/figures/mesh_photo_<key>.png     기체별: 사진 · 메쉬 · 겹침 · 숫자 + 그 기체 사진 전부
  outputs/figures/mesh_photo_summary.png   7종 IoU 한 장 (기체별 상한 표시)
  outputs/mesh_compare_photo.json          전 조합의 수치 원장

규약
----
  · 그림 안 글자는 전부 영어. 산문·주석·print 는 한국어.
  · 그림의 숫자는 손으로 적지 않는다 — `build_all()` 이 재서 원장에 쓰고 그림은 원장을 읽는다.
  · 색 = `drones.MATERIAL_COLOR` 순수 재질 5색(메쉬 렌더). 차이 색은 겹침 패널에서만 쓴다.
  · 사진 출처·라이선스는 `assets/photos/<key>/SOURCES.md` 를 따른다. 기록이 없으면 **없다고 적는다**.
  · ⛔ `typhoonh480/_c04_skylarkcoder.jpg` 는 분쟁 자료다 — 이 파일은 쓰지 않는다.

실행
----
  cd /home/yunjung/workspace/sionna2
  SIONNA2_CPU=1 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python src/viz_mesh_photo.py
  ... --keys mini5pro,mavic4pro     # 일부만
  ... --quick                       # 점 수·격자 줄여 빠르게(수치는 거칠어진다)
  ... --redraw                      # 원장에서 그림만 다시(재정합 없음)
  ... --calib-only                  # 원장에 기체별 지표 눈금만 덧붙인다
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import time

import numpy as np
import scipy.ndimage as ndi
from PIL import Image

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

import viz_mesh_gallery as G            # 직교 카메라·음영 규약을 그대로 쓴다(렌더러 재사용)
from drones import (DRONES, MATERIAL_COLOR, build_frame, build_propeller, drone_keys,
                    drone_label, rotor_layout)

ROOT = G.ROOT
OUT = G.OUT
FIG = G.FIG
LEDGER = os.path.join(OUT, "mesh_compare_photo.json")
PHOTO_DIR = os.path.join(ROOT, "assets", "photos")

MESH_SOURCES = G.MESH_SOURCES
MEASURED = G.MEASURED

# --- 겹침 패널 색 (3분류 + 중립) ------------------------------------------------ #
C_AGREE = "#9aa3ab"      # 중립 회색 — 두 실루엣이 겹친 자리
C_MESH = "#d1495b"       # 붉은색 — 메쉬에만 있는 자리
C_PHOTO = "#1b6ca8"      # 푸른색 — 사진에만 있는 자리
GRAY = G.GRAY


# --------------------------------------------------------------------------- #
#  0.  사진 등록부 — 무엇을 쓰고 무엇을 왜 안 쓰는가
# --------------------------------------------------------------------------- #
#  props : 사진에 프로펠러가 달려 있나. False 면 메쉬도 **프레임만**으로 견준다
#          (프레임 킷 사진에 프롭 달린 메쉬를 겹치면 IoU 는 형상이 아니라 구성 차이를 잰다).
#  expect: 사람이 눈으로 읽은 대략의 (방위, 고각) [deg]. 탐색은 이 값을 쓰지 않고
#          전 방위를 훑는다 — 이 값은 **결과가 엉뚱한 데 앉았는지 검사**하는 용도다.
#  credit/licence : SOURCES.md 에 적힌 그대로. 기록이 없으면 None 이고 그림에 "not recorded" 로 나간다.
_DJI = dict(credit="DJI product image", licence=None,
            provenance="assets/photos/<key>/ 에 SOURCES.md 없음 — 출처·라이선스 미기록")

PHOTOS: dict[str, list[dict]] = {
    "mini5pro": [
        dict(file="mini 5 pro_1.png", expect=(0, 12), props=True,
             note="front, camera slightly above", **_DJI),
        dict(file="mini 5 pro_3.png", expect=(0, 85), props=True,
             note="from above (azimuth unconstrained at this elevation)", **_DJI),
        dict(file="mini 5 pro_2.png", expect=(35, 30), props=True,
             note="three-quarter, nose toward the camera and to the left", **_DJI),
    ],
    "mavic4pro": [
        dict(file="mavic 4 pro_1.png", expect=(0, 14), props=True,
             note="front, slightly above", **_DJI),
        dict(file="mavic 4 pro_3.png", expect=(0, 3), props=True,
             note="head-on, near eye level", **_DJI),
        dict(file="mavic 4 pro_2.png", expect=(0, 40), props=True,
             note="front from well above, symmetric", **_DJI),
        dict(file="mavic 4 pro_4.png", expect=(40, 15), props=True,
             note="three-quarter, gimbal facing the camera and to the left", **_DJI),
    ],
    "matrice4e": [
        dict(file="matrice 4E_5.png", expect=(0, 85), props=True,
             note="from above, X rotor layout", **_DJI),
        dict(file="matrice 4E_1.png", expect=(0, 16), props=True,
             note="front, slightly above", **_DJI),
        dict(file="matrice 4E_3.png", expect=(0, 4), props=True,
             note="head-on, eye level", **_DJI),
        # matrice 4E_2.png 은 뺐다 — 거의 정측면이라 **기수가 어느 쪽인지 눈으로 못 정한다**.
        #   선언 자세가 틀리면 헤드라인 IoU 가 형상이 아니라 내 오독을 재게 된다.
    ],
    "phantom4": [
        dict(file="Phantom 4 Pro+ V2.0_5.png", expect=(0, 85), props=True,
             note="from above", **_DJI),
        dict(file="Phantom 4 Pro+ V2.0_4.png", expect=(0, 22), props=True,
             note="front, above", **_DJI),
        dict(file="Phantom 4 pro + V2_1.png", expect=(32, 20), props=True,
             note="three-quarter, gimbal toward the camera and to the left", **_DJI),
        dict(file="Phantom 4 Pro+ V2.0_2.png", expect=(0, 15), props=True,
             note="front, slightly above", **_DJI),
    ],
    "s1000plus": [
        dict(file="s1000+_1.png", expect=(0, 85), props=True,
             note="from above, 8 arms deployed",
             credit="DJI product image", licence=None,
             provenance="SOURCES.md 없음. 이미지에 판매점 워터마크가 있다"),
        # 8각 대칭이라 방위를 45° 안으로밖에 못 좁힌다 → 창을 넓혀 선언 오차를 흡수한다.
        dict(file="s1000+_2.png", expect=(0, 18), props=True, window=34.0,
             note="front, slightly above; eight-fold symmetry leaves azimuth ambiguous",
             credit="DJI product image", licence=None,
             provenance="SOURCES.md 없음"),
    ],
    "typhoonh480": [
        # ⛔ _c04_skylarkcoder.jpg 는 등록하지 않는다(분쟁 자료, SOURCES.md 의 🔴 경고).
        dict(file="typhoonh480_y04_official_pursuit.png", expect=(0, 72), props=True,
             window=26.0,
             note="from above, landing gear retracted (the mesh has it down)",
             credit="Yuneec International (official product image, via Wayback Machine)",
             licence="Copyright Yuneec — attribution required when published",
             provenance="assets/photos/typhoonh480/SOURCES.md"),
        dict(file="typhoonh480_y03_official_hero.png", expect=(25, 28), props=True,
             note="front three-quarter from above, gear down",
             credit="Yuneec International (official product image, via Wayback Machine)",
             licence="Copyright Yuneec — attribution required when published",
             provenance="assets/photos/typhoonh480/SOURCES.md"),
    ],
    "x500v2": [
        # 상판에 인쇄된 전방 화살표가 기수를 준다. _09 는 화살표가 왼쪽 위(카메라 반대)를 향한다.
        dict(file="x500v2_09_arf_iso34_props.jpg", expect=(150, 28), props=True, window=30.0,
             note="ARF build, three-quarter from behind-left (top-plate arrow points away); "
                  "no GPS mast and no battery, the mesh is the full kit",
             credit="Holybro product photo",
             licence="Manufacturer product image — attribution required when published",
             provenance="assets/photos/x500v2/SOURCES.md"),
        dict(file="x500v2_03_top_ortho.jpg", expect=(0, 85), props=False,
             note="frame kit from above: no propellers, no motors, no battery",
             credit="Holybro product photo",
             licence="Manufacturer product image — attribution required when published",
             provenance="assets/photos/x500v2/SOURCES.md"),
        dict(file="x500v2_01_arf_front34_props.jpg", expect=(180, 25), props=True, window=26.0,
             note="ARF build seen from behind and above (top-plate arrow points away)",
             credit="Holybro product photo",
             licence="Manufacturer product image — attribution required when published",
             provenance="assets/photos/x500v2/SOURCES.md"),
    ],
}

#: 이 파일들은 **일부러 뺐다**. 이유를 기록에 남긴다(원장 _meta.excluded 로 나간다).
EXCLUDED = [
    dict(key="typhoonh480", file="typhoonh480_c04_skylarkcoder.jpg",
         reason="disputed provenance: uploaded as own work but is a manufacturer render, "
                "badge reads CYCLONE and the gimbal is not a CGO3+ (SOURCES.md)"),
    dict(key="typhoonh480", file="typhoonh480_y01_official_gear_down.png",
         reason="animation composite: ghost copies of the arms would enter the silhouette"),
    dict(key="typhoonh480", file="typhoonh480_y02_official_gear_up.png",
         reason="animation composite: ghost copies of the arms would enter the silhouette"),
    dict(key="typhoonh480", file="typhoonh480_c01_cebit2017_iso34.jpg",
         reason="exhibition background: no background/foreground separation by colour"),
    dict(key="typhoonh480", file="typhoonh480_c02_field_2025_02.jpg",
         reason="in flight: propellers are motion blurred, silhouette is a smear"),
    dict(key="typhoonh480", file="typhoonh480_c03_field_2025_10.jpg",
         reason="in flight: propellers are motion blurred"),
    dict(key="typhoonh480", file="typhoonh480_c05_uasconf_a.jpg",
         reason="grass background, aircraft is a small part of the frame"),
    dict(key="typhoonh480", file="typhoonh480_c06_uasconf_b.jpg",
         reason="grass background, aircraft is a small part of the frame"),
    dict(key="typhoonh480", file="typhoonh480_y05_official_header.png",
         reason="propellers motion blurred"),
    dict(key="x500v2", file="x500v2_15_built_aircraft_field.jpg",
         reason="outdoor background, no colour separation"),
    dict(key="x500v2", file="x500v2_04_dimensioned_drawing.jpg",
         reason="dimension arrows and text are part of the image, they enter the silhouette"),
    dict(key="matrice4e", file="matrice 4E_2.png",
         reason="near-side view: which end is the nose cannot be read off the photograph, and a "
                "wrong declared aspect would be measured as a shape error"),
]
#: 부품 클로즈업 사진은 전기체 실루엣이 아니므로 등록 자체를 안 한다(위 목록에도 넣지 않는다).


# --------------------------------------------------------------------------- #
#  1.  사진 → 실루엣 마스크
# --------------------------------------------------------------------------- #
def clean_mask(m: np.ndarray, hole_frac=0.004) -> np.ndarray:
    """두 마스크에 **똑같이** 거는 정리: 1px 닫기 + 작은 구멍 메우기 + 파편 제거.

    사진과 메쉬에 같은 처리를 걸어야 대조가 공정하다. 큰 구멍(암 사이 빈 공간)은
    바깥과 이어져 있어 애초에 구멍이 아니고, 여기서 메워지지도 않는다."""
    m = ndi.binary_closing(m, structure=np.ones((3, 3), bool))
    filled = ndi.binary_fill_holes(m)
    holes, nh = ndi.label(filled & ~m)
    if nh:
        area = ndi.sum(np.ones_like(holes, float), holes, np.arange(1, nh + 1))
        small = np.flatnonzero(area < hole_frac * max(m.sum(), 1)) + 1
        if len(small):
            m = m | np.isin(holes, small)
    lab, n = ndi.label(m)
    if n > 1:                                  # 본체에서 떨어진 파편(그림자·워터마크)을 버린다
        area = ndi.sum(np.ones_like(lab, float), lab, np.arange(1, n + 1))
        keep = np.flatnonzero(area >= 0.02 * area.max()) + 1
        m = np.isin(lab, keep)
    return m


def seg_sensitivity(path: str, max_side=640, thresholds=(0.03, 0.055, 0.09, 0.14)):
    """실루엣 면적이 **분리 임계값에 얼마나 흔들리는가** [%]. 기준은 우리가 쓰는 0.055.

    흰 기체를 흰 배경에서 찍은 사진(phantom4)은 이 값이 수십 %로 튄다. 그러면 IoU 는
    메쉬 충실도가 아니라 분리 임계값을 재게 된다 — 그래서 숫자로 남기고 그림에 띄운다."""
    im = Image.open(path).convert("RGBA")
    if max(im.size) > max_side:
        f = max_side / max(im.size)
        im = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.LANCZOS)
    a = np.asarray(im, float) / 255.0
    alpha = a[..., 3]
    if float((alpha < 0.98).mean()) > 0.02:
        return None                                   # 알파 채널 사진은 임계값을 안 쓴다
    rgb = a[..., :3] * alpha[..., None] + (1.0 - alpha[..., None])
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(edge, axis=0)
    dist = np.abs(rgb - bg).max(axis=2)
    areas = [float(clean_mask(dist > t).sum()) for t in thresholds]
    base = areas[list(thresholds).index(0.055)]
    pct = [100.0 * (x / base - 1.0) for x in areas]
    return dict(thresholds=list(thresholds), area_change_pct=[round(v, 2) for v in pct],
                spread_pct=round(max(pct) - min(pct), 2),
                fragile=bool(max(pct) - min(pct) > 12.0),
                note="silhouette area against the background-distance threshold, "
                     "relative to the 0.055 we use")


def photo_mask(path: str, max_side=760, pad_frac=0.20):
    """사진 → (RGB float[0,1], 실루엣 bool, 진단 dict).

    두 갈래다 — 알파가 실제로 쓰인 PNG 는 알파를, 아니면 **테두리 픽셀의 배경색**에서
    잰 색거리를 쓴다. 임계값은 배경 잡음의 몇 배로 정하고 그 값을 진단에 남긴다.

    ⭐ 화면을 사방으로 `pad_frac` 만큼 넓힌다(배경으로 채운다). 넓히지 않으면 메쉬가
    사진 밖으로 나간 부분이 **어느 실루엣에도 안 잡혀** IoU 가 낙관적으로 나온다 —
    실측으로 s1000+ 톱뷰에서 메쉬 점의 16.6 % 가 그렇게 잘려 나갔다. 이 사진들은 기체가
    프레임 안에 여유를 두고 들어 있으므로, 프레임 밖은 배경으로 두는 것이 맞다."""
    im = Image.open(path).convert("RGBA")
    if max(im.size) > max_side:
        f = max_side / max(im.size)
        im = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.LANCZOS)
    a = np.asarray(im, float) / 255.0
    alpha = a[..., 3]
    rgb = a[..., :3] * alpha[..., None] + (1.0 - alpha[..., None])       # 흰 배경 위 합성
    used_alpha = float((alpha < 0.98).mean()) > 0.02
    if used_alpha:
        m = alpha > 0.5
        thr = None
        bg = np.array([1.0, 1.0, 1.0])
    else:
        edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        bg = np.median(edge, axis=0)
        noise = float(np.median(np.abs(edge - bg).max(axis=1)))
        thr = max(0.055, 6.0 * noise)                                    # 배경 잡음의 6배
        m = np.abs(rgb - bg).max(axis=2) > thr
    m = clean_mask(m)
    pad = int(round(pad_frac * max(m.shape)))
    if pad:
        m = np.pad(m, pad, mode="constant", constant_values=False)
        rgb = np.stack([np.pad(rgb[..., c], pad, mode="constant", constant_values=bg[c])
                        for c in range(3)], axis=-1)
    diag = dict(source="alpha channel" if used_alpha else "background colour distance",
                pad_px=int(pad),
                pad_note="canvas widened by this many pixels on each side so that mesh area "
                         "outside the photograph frame is counted as mesh-only instead of "
                         "being clipped away",
                sensitivity=seg_sensitivity(path, max_side),
                max_side=int(max_side),
                background_rgb=[round(float(x), 3) for x in bg],
                threshold=(None if thr is None else round(float(thr), 4)),
                image_px=[int(im.width), int(im.height)],
                mask_area_px=int(m.sum()),
                mask_area_frac=round(float(m.mean()), 4))
    return rgb, m, diag


# --------------------------------------------------------------------------- #
#  2.  메쉬 → 표면 점구름 (프레임 + 로터별 프로펠러)
# --------------------------------------------------------------------------- #
def _sample(V, F, gid_of_face, n, rng):
    """면적 비례 표면 샘플. (점 (n,3), 그룹 인덱스 (n,), 단위법선 (n,3))

    법선까지 돌려주는 이유: 같은 점구름으로 **실루엣 마스크와 음영 렌더를 둘 다** 만든다.
    렌더와 마스크가 같은 점에서 나오면 그림과 숫자가 어긋날 수 없다."""
    tri = V[F]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    area = 0.5 * ln
    tot = float(area.sum())
    if n <= 0 or tot <= 0:
        return np.zeros((0, 3)), np.zeros(0, int), np.zeros((0, 3)), tot
    idx = rng.choice(len(F), size=n, p=area / tot)
    u = rng.random(n)
    v = rng.random(n)
    flip = u + v > 1.0
    u[flip], v[flip] = 1.0 - u[flip], 1.0 - v[flip]
    t = tri[idx]
    P = t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])
    N = nrm[idx] / np.where(ln[idx, None] < 1e-30, 1.0, ln[idx, None])
    return P, gid_of_face[idx], N, tot


def mesh_parts(key: str, n_points: int, include_props=True, seed=7):
    """현재 소스에서 메쉬를 만들고 **프레임 1 + 로터별 프롭 N** 으로 나눈 점구름을 준다.

    로터별로 나누는 이유: 프로펠러 위상이 로터마다 자유 파라미터라서, 위상을 바꿀 때
    그 로터의 점만 다시 투영하면 되도록 하기 위해서다."""
    rng = np.random.default_rng(seed)
    spec = DRONES[key]
    fr = build_frame(spec)
    Vf = np.asarray(fr.v, float)
    Ff = np.asarray(fr.f, int)
    groups = sorted(set(fr.g))
    if include_props:
        groups = sorted(set(groups) | {"prop"})
    gindex = {g: i for i, g in enumerate(groups)}
    gid_f = np.array([gindex[g] for g in fr.g], int)

    p_ccw = build_propeller(spec)
    p_cw = build_propeller(spec, mirror=True)
    Vp = {1: np.asarray(p_ccw.v, float), -1: np.asarray(p_cw.v, float)}
    Fp = {1: np.asarray(p_ccw.f, int), -1: np.asarray(p_cw.f, int)}
    rl = rotor_layout(spec) if include_props else []

    # 면적 비례로 점을 나눈다 → 어느 부품이든 화면 밀도가 같다
    def _area(V, F):
        t = V[F]
        return float(0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]),
                                          axis=1).sum())
    a_f = _area(Vf, Ff)
    a_p = [_area(Vp[r["dir"]], Fp[r["dir"]]) for r in rl]
    a_tot = a_f + sum(a_p)

    Pf, gf, Nf, _ = _sample(Vf, Ff, gid_f, int(round(n_points * a_f / a_tot)), rng)
    parts = [dict(name="frame", P=Pf, gid=gf, N=Nf, rotor=None)]
    gi_prop = gindex.get("prop")
    for i, rot in enumerate(rl):
        d = rot["dir"]
        nid = np.zeros(len(Fp[d]), int) + gi_prop
        Pp, gp, Np, _ = _sample(Vp[d], Fp[d], nid, int(round(n_points * a_p[i] / a_tot)), rng)
        parts.append(dict(name=f"prop{i}", P=Pp, gid=gp, N=Np, rotor=i,
                          center=np.asarray(rot["center"], float),
                          base_ang=float(rot["base_ang"])))
    # 전체 bbox — 원근 기준면과 span 을 여기서 정한다(프롭 포함/제외 구성 그대로)
    allP = np.concatenate([p["P"] for p in parts if len(p["P"])])
    lo, hi = allP.min(0), allP.max(0)
    return dict(parts=parts, groups=groups, centre=0.5 * (lo + hi),
                span=float((hi - lo).max()), n_rotors=len(rl),
                Vf=Vf, Ff=Ff, gf=gid_f, Vp=Vp, Fp=Fp, rl=rl, spec=spec,
                include_props=include_props)


def spin(P, centre, ang_deg):
    """로터 축(z) 둘레로 프롭 점을 돌린다 — 사진 속 블레이드 방위를 맞추기 위한 자유도."""
    a = np.radians(ang_deg)
    c, s = np.cos(a), np.sin(a)
    d = P - centre
    return np.stack([c * d[:, 0] - s * d[:, 1] + centre[0],
                     s * d[:, 0] + c * d[:, 1] + centre[1],
                     d[:, 2] + centre[2]], axis=1)


# --------------------------------------------------------------------------- #
#  3.  투영 · 래스터화
# --------------------------------------------------------------------------- #
def basis_roll(elev, azim, roll):
    """(r,u,d) 를 화면 롤 만큼 돌린다. (azim,elev,roll) 세 각이 SO(3) 전부를 훑는다."""
    r, u, d = G.view_basis(elev, azim)
    c, s = np.cos(np.radians(roll)), np.sin(np.radians(roll))
    return (c * r + s * u, -s * r + c * u, d)


def project(P, b, q, span, z0):
    """3D 점 → 2D 화면좌표 [m]. q = span/D 가 원근 세기(q=0 이 정투영)."""
    r, u, d = b
    zc = P @ d
    f = 1.0 / (1.0 - q * (zc - z0) / span) if q else 1.0
    return np.stack([(P @ r) * f, (P @ u) * f], axis=1)


def raster(XY, s, tx, ty, shape):
    H, W = shape
    ix = np.rint(XY[:, 0] * s + tx).astype(np.int64)
    iy = np.rint(-XY[:, 1] * s + ty).astype(np.int64)
    ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    m = np.zeros(H * W, bool)
    m[iy[ok] * W + ix[ok]] = True
    return m.reshape(H, W)


def raster_union(XYs, s, tx, ty, shape, close=True):
    m = np.zeros(shape, bool)
    for XY in XYs:
        if len(XY):
            m |= raster(XY, s, tx, ty, shape)
    return ndi.binary_closing(m, structure=np.ones((3, 3), bool)) if close else m


def iou(a, b):
    inter = np.count_nonzero(a & b)
    uni = np.count_nonzero(a | b)
    return inter / uni if uni else 0.0


# --------------------------------------------------------------------------- #
#  4.  정합 — 자세 → (배율, 이동) → 프롭 위상
# --------------------------------------------------------------------------- #
#  ⭐ 왜 **두 갈래**로 재나
#  ----------------------------------------------------------------------------
#  자유 탐색만 하면 카메라를 실제와 다른 각도로 기울여서 형상 차이를 **가릴 수** 있다.
#  (실제로 mini5pro 정면 사진에 고각 50° 를 물려서 IoU 를 올린다 — 사진은 12° 쯤이다.)
#  그래서 두 번 잰다:
#    · declared — 사람이 사진을 보고 선언한 시선방향에서 **20° 이내**로 묶고 잰다. 헤드라인 숫자.
#    · free     — 시선방향을 묶지 않고 IoU 최대를 찾는다. 둘의 차이가 곧 정보다:
#                 자유 탐색이 훨씬 높으면 "맞는 각도보다 틀린 각도에 더 잘 맞는다" 는 뜻이고,
#                 그건 자세 모호성이 아니라 형상 차이다.
def view_dir(az, el):
    e, a = np.radians(el), np.radians(az)
    return np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])


def view_angle(az1, el1, az2, el2) -> float:
    """두 시선방향 사이 각 [deg]. 톱뷰에서 방위가 롤과 겹쳐 무의미해지는 문제를 피한다."""
    c = float(np.clip(view_dir(az1, el1) @ view_dir(az2, el2), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


class Fitter:
    """한 (기체 구성 × 사진) 조합의 정합기. 점구름을 한 번만 준비해 두고 반복 평가한다."""

    def __init__(self, parts, centre, span, target, shape):
        self.P = [np.ascontiguousarray(p["P"] - centre) for p in parts]
        self.rot = [p["rotor"] for p in parts]
        self.ctr = [None if p["rotor"] is None else np.asarray(p["center"], float) - centre
                    for p in parts]
        self.span = span
        self.target = target
        self.shape = shape
        self.n_rot = sum(1 for r in self.rot if r is not None)
        self.n_eval = 0

    # -- 투영 / 점수 -------------------------------------------------------- #
    def xys(self, az, el, ro, q, phases=None):
        b = basis_roll(el, az, ro)
        out = []
        for P, r, c in zip(self.P, self.rot, self.ctr):
            pts = P if (r is None or not phases or not phases[r]) else spin(P, c, phases[r])
            out.append(project(pts, b, q, self.span, 0.0))
        return out

    def score(self, XYs, s, tx, ty, close=False):
        self.n_eval += 1
        return iou(raster_union(XYs, s, tx, ty, self.shape, close=close), self.target)

    # -- (배율, 이동) ------------------------------------------------------- #
    def _inits(self, XYs):
        """초기값 두 개 — **면적 일치**와 **외접상자 일치**. 형상이 많이 다르면 둘이 크게 갈린다."""
        A = np.concatenate([x for x in XYs if len(x)])
        ys, xs = np.nonzero(self.target)
        if len(xs) == 0:
            return []
        cx, cy = xs.mean(), ys.mean()
        out = []
        ex, ey = max(np.ptp(A[:, 0]), 1e-9), max(np.ptp(A[:, 1]), 1e-9)
        for s in (np.ptp(xs) / ex, np.ptp(ys) / ey):
            cm = A.mean(0)
            tx, ty = cx - cm[0] * s, cy + cm[1] * s
            m = raster_union(XYs, s, tx, ty, self.shape)
            if not m.any():
                continue
            s2 = s * float(np.sqrt(self.target.sum() / m.sum()))       # 면적 일치 보정
            for ss in (s, s2):
                m = raster_union(XYs, ss, tx, ty, self.shape)
                if not m.any():
                    continue
                yy, xx = np.nonzero(m)
                out.append((float(ss), float(tx + cx - xx.mean()), float(ty + cy - yy.mean())))
        return out

    def align(self, XYs, refine=True):
        """(IoU, s, tx, ty). refine=True 면 패턴탐색으로 배율·이동을 조인다."""
        best = (-1.0, 1.0, 0.0, 0.0)
        for s, tx, ty in self._inits(XYs):
            v = self.score(XYs, s, tx, ty)
            if v > best[0]:
                best = (v, s, tx, ty)
        if not refine or best[0] < 0:
            return best
        v, s, tx, ty = best
        ds, dt = 0.06, 6.0
        for _ in range(7):
            moved = False
            for fs in (1 - ds, 1.0, 1 + ds):
                for ex in (-dt, 0.0, dt):
                    for ey in (-dt, 0.0, dt):
                        vv = self.score(XYs, s * fs, tx + ex, ty + ey)
                        if vv > v:
                            v, s, tx, ty, moved = vv, s * fs, tx + ex, ty + ey, True
            if not moved:
                ds, dt = ds * 0.45, max(dt * 0.45, 0.6)
                if ds < 0.004:
                    break
        return (v, s, tx, ty)

    # -- 6자유도 나침반 탐색 -------------------------------------------------- #
    #  ⭐ 왜 이렇게까지 조이나: 이 지표는 **가늘다**. 같은 메쉬끼리 재도 자세가 1° 어긋나면
    #     IoU 가 0.91, 2° 면 0.83, 배율이 1% 어긋나면 0.95 로 떨어진다(측정값, `calibrate()`).
    #     0.5° / 0.3% 까지 조이지 않으면 지표가 형상이 아니라 **정합 실패**를 재게 된다.
    def polish(self, az, el, ro, q, s, tx, ty, ph, keep=None, tol=0.12):
        x = [az, el, ro, q, np.log(s), tx, ty]
        step = [4.0, 4.0, 3.0, 0.06, 0.03, 4.0, 4.0]
        lo = [-1e9, -1e9, -1e9, 0.0, -1e9, -1e9, -1e9]
        hi = [1e9, 1e9, 1e9, 1.2, 1e9, 1e9, 1e9]

        def val(x):
            if keep is not None and not keep(x[0], x[1]):
                return -1.0
            return self.score(self.xys(x[0], x[1], x[2], x[3], ph), np.exp(x[4]), x[5], x[6])
        v = val(x)
        while max(step[0], step[1], step[2]) > tol:
            moved = False
            for i in range(7):
                for sgn in (+1, -1):
                    y = list(x)
                    y[i] = float(np.clip(x[i] + sgn * step[i], lo[i], hi[i]))
                    if y[i] == x[i]:
                        continue
                    vv = val(y)
                    if vv > v:
                        v, x, moved = vv, y, True
                        break
            if not moved:
                step = [t * 0.5 for t in step]
        return v, x[0], x[1], x[2], x[3], float(np.exp(x[4])), x[5], x[6]

    # -- 로터별 프롭 위상 ---------------------------------------------------- #
    def opt_phases(self, az, el, ro, q, s, tx, ty, phases, step=10.0, sweeps=2, window=None):
        """좌표하강. 부품별 마스크를 들고 있다가 **바뀐 로터만** 다시 래스터화한다.
        window 를 주면 현재 위상 ±window 만 훑는다(거친 탐색 뒤 조일 때)."""
        if not self.n_rot:
            return list(phases), self.score(self.xys(az, el, ro, q), s, tx, ty, close=True)
        b = basis_roll(el, az, ro)
        ph = list(phases)
        masks = []
        for P, r, c in zip(self.P, self.rot, self.ctr):
            pts = P if r is None else spin(P, c, ph[r])
            masks.append(raster_union([project(pts, b, q, self.span, 0.0)], s, tx, ty,
                                      self.shape, close=False))
        strct = np.ones((3, 3), bool)
        for _ in range(sweeps):
            for i, r in enumerate(self.rot):
                if r is None:
                    continue
                grid = (np.arange(0.0, 180.0, step) if window is None
                        else ph[r] + np.arange(-window, window + 1e-9, step))
                others = np.zeros(self.shape, bool)
                for j in range(len(masks)):
                    if j != i:
                        others |= masks[j]
                bp, bv, bm = ph[r], -1.0, masks[i]
                for g in grid:
                    XY = project(spin(self.P[i], self.ctr[i], g), b, q, self.span, 0.0)
                    mi = raster_union([XY], s, tx, ty, self.shape, close=False)
                    vv = iou(ndi.binary_closing(others | mi, structure=strct), self.target)
                    self.n_eval += 1
                    if vv > bv:
                        bp, bv, bm = float(g), vv, mi
                ph[r], masks[i] = bp, bm
        return ph, bv


def _pose_grid(az_step, el_lo, el_hi, el_step, keep=None):
    for az in np.arange(0.0, 360.0, az_step):
        for el in np.arange(el_lo, el_hi + 1e-6, el_step):
            if keep is None or keep(az, el):
                yield float(az), float(el)


def fit_pose(parts, target, shape, span, centre, *, declared=None, window_deg=20.0,
             quick=False, log=None, want_free=True):
    """자세 + 배율·이동 + 로터별 프롭 위상을 IoU 최대로 맞춘다.

    declared 가 있으면 **그 시선방향에서 window_deg 이내**로 묶어서 한 번 더 맞추고
    두 결과를 함께 돌려준다(위 주석의 두 갈래)."""
    F = Fitter(parts, centre, span, target, shape)
    az_step = 15.0 if quick else 10.0
    el_step = 12.0 if quick else 8.0
    rolls = (0.0,) if quick else (-10.0, -5.0, 0.0, 5.0, 10.0)
    qs = (0.0, 0.25, 0.6) if quick else (0.0, 0.15, 0.3, 0.5, 0.75, 1.0)
    ph_step = 15.0 if quick else 10.0
    n_keep = 8 if quick else 20

    def branch(keep, tag):
        # --- A. 자세 훑기 (롤 0, 정투영, 프롭 위상 0) --------------------------- #
        cand = [(F.align(F.xys(az, el, 0.0, 0.0), refine=False)[0], az, el)
                for az, el in _pose_grid(az_step, -36.0, 90.0, el_step, keep)]
        if not cand:
            return None
        cand.sort(reverse=True)
        # --- A2. 전 로터 공통 위상 — 위상 0 때문에 옳은 자세가 밀려나는 것을 막는다 --- #
        cand2 = []
        for _v, az, el in cand[:n_keep]:
            for g in np.arange(0.0, 180.0, 30.0 if quick else 20.0):
                ph = [g] * F.n_rot
                cand2.append((F.align(F.xys(az, el, 0.0, 0.0, ph), refine=False)[0], az, el, g))
        cand2.sort(reverse=True)
        # --- B. 롤 · 원근 ------------------------------------------------------ #
        cand3 = []
        for _v, az, el, g in cand2[: (3 if quick else 6)]:
            ph = [g] * F.n_rot
            for ro in rolls:
                for q in qs:
                    cand3.append((F.align(F.xys(az, el, ro, q, ph), refine=False)[0],
                                  az, el, ro, q, g))
        cand3.sort(reverse=True)
        # --- C. 후보별 (배율·이동 → 위상 → 6자유도 조이기) 를 번갈아 ------------- #
        best = None
        for _v, az, el, ro, q, g in cand3[: (2 if quick else 4)]:
            ph = [g] * F.n_rot
            v, s, tx, ty = F.align(F.xys(az, el, ro, q, ph))
            ph, v = F.opt_phases(az, el, ro, q, s, tx, ty, ph, step=ph_step)
            v, az2, el2, ro2, q2, s, tx, ty = F.polish(az, el, ro, q, s, tx, ty, ph, keep,
                                                       tol=(1.0 if quick else 0.5))
            if best is None or v > best[0]:
                best = (v, az2, el2, ro2, q2, s, tx, ty, ph)
        v, az, el, ro, q, s, tx, ty, ph = best
        # --- D. 위상과 자세를 번갈아 끝까지 조인다 ------------------------------ #
        if not quick:
            for ps, win, tolerance in ((4.0, 16.0, 0.25), (1.5, 6.0, 0.10)):
                ph, _ = F.opt_phases(az, el, ro, q, s, tx, ty, ph, step=ps, sweeps=1, window=win)
                v, az, el, ro, q, s, tx, ty = F.polish(az, el, ro, q, s, tx, ty, ph, keep,
                                                       tol=tolerance)
        out = dict(iou=float(v), azim=float(az % 360.0), elev=float(el), roll=float(ro),
                   q=float(q), scale_px_per_m=float(s), tx=float(tx), ty=float(ty),
                   phases=[float(x) for x in ph], branch=tag,
                   n_pose_evaluated=len(cand), n_eval=int(F.n_eval))
        if log:
            log(f"      [{tag}] az={out['azim']:.1f} el={el:.1f} roll={ro:.1f} "
                f"q={q:.2f}  IoU={v:.4f}")
        return out

    if declared is None:
        free = branch(None, "free")
        return free, free
    az0, el0 = declared
    dec = branch(lambda a, e: view_angle(a, e, az0, el0) <= window_deg, "declared")
    #  자유 갈래는 **비교용**이다 — 눈금 계산처럼 비교가 필요 없을 땐 건너뛴다(비용 절반).
    free = branch(None, "free") if want_free else dict(dec, branch="declared (free skipped)")
    return (dec or free), free


# --------------------------------------------------------------------------- #
#  5.  최종 측정 — 마스크·차이 덩어리·경계오차
# --------------------------------------------------------------------------- #
def final_masks(parts, fit, span, centre, shape, groups):
    """정합된 자세에서 **전체 마스크 + 그룹별 마스크**를 만든다(차이 덩어리 귀속용)."""
    b = basis_roll(fit["elev"], fit["azim"], fit["roll"])
    s, tx, ty = fit["scale_px_per_m"], fit["tx"], fit["ty"]
    gmask = {g: np.zeros(shape, bool) for g in groups}
    total = np.zeros(shape, bool)
    for p in parts:
        pts = p["P"] - centre
        if p["rotor"] is not None and fit["phases"][p["rotor"]]:
            pts = spin(pts, p["center"] - centre, fit["phases"][p["rotor"]])
        XY = project(pts, b, fit["q"], span, 0.0)
        for gi in np.unique(p["gid"]):
            sel = p["gid"] == gi
            m = raster(XY[sel], s, tx, ty, shape)
            gmask[groups[gi]] |= m
            total |= m
    return clean_mask(total), gmask


def contour_error(a, b, mm_per_px):
    """두 실루엣 **윤곽선** 사이 대칭 거리 [mm]: 평균과 95 백분위."""
    def edge(m):
        return m & ~ndi.binary_erosion(m, structure=np.ones((3, 3), bool))
    ea, eb = edge(a), edge(b)
    if not ea.any() or not eb.any():
        return None, None
    da = ndi.distance_transform_edt(~eb)[ea]
    db = ndi.distance_transform_edt(~ea)[eb]
    d = np.concatenate([da, db]) * mm_per_px
    return float(d.mean()), float(np.percentile(d, 95))


def diff_blobs(mesh_m, photo_m, gmask, groups, mm_per_px, min_frac=0.006, top=4):
    """차이(합집합에서 겹치지 않은 부분)를 덩어리로 쪼개 **면적과 소속 부품**을 붙인다."""
    from scipy.spatial import cKDTree
    uni = float(np.count_nonzero(mesh_m | photo_m))
    out = []
    pix_mm2 = mm_per_px ** 2
    # 메쉬에만 있는 자리 → 그 자리를 차지한 그룹이 곧 원인
    lab, n = ndi.label(mesh_m & ~photo_m)
    for i in range(1, n + 1):
        blob = lab == i
        a = float(blob.sum())
        if a / uni < min_frac:
            continue
        own = max(groups, key=lambda g: np.count_nonzero(gmask[g] & blob))
        out.append(dict(side="mesh only", part=own, area_frac=a / uni,
                        area_mm2=a * pix_mm2,
                        centroid=[float(x) for x in ndi.center_of_mass(blob)]))
    # 사진에만 있는 자리 → 가장 가까운 메쉬 부품에 귀속
    pts, lbl = [], []
    for g in groups:
        yy, xx = np.nonzero(gmask[g])
        if len(yy):
            k = max(1, len(yy) // 4000)
            pts.append(np.stack([yy[::k], xx[::k]], 1))
            lbl += [g] * len(yy[::k])
    tree = cKDTree(np.concatenate(pts)) if pts else None
    lab, n = ndi.label(photo_m & ~mesh_m)
    for i in range(1, n + 1):
        blob = lab == i
        a = float(blob.sum())
        if a / uni < min_frac:
            continue
        c = ndi.center_of_mass(blob)
        near = lbl[tree.query(np.array(c))[1]] if tree else "?"
        out.append(dict(side="photo only", part=near, area_frac=a / uni,
                        area_mm2=a * pix_mm2, centroid=[float(x) for x in c]))
    out.sort(key=lambda d: -d["area_frac"])
    return out[:top]


def clipped_fraction(parts, fit, span, centre, shape):
    """메쉬 점 중 **화면 밖으로 나간 비율**. 잘린 부분은 어느 쪽 면적에도 안 잡히므로
    IoU 를 낙관적으로 만든다 — 그래서 숫자로 남긴다."""
    b = basis_roll(fit["elev"], fit["azim"], fit["roll"])
    s, tx, ty = fit["scale_px_per_m"], fit["tx"], fit["ty"]
    H, W = shape
    n_out = n_tot = 0
    for p in parts:
        pts = p["P"] - centre
        if p["rotor"] is not None and fit["phases"][p["rotor"]]:
            pts = spin(pts, p["center"] - centre, fit["phases"][p["rotor"]])
        XY = project(pts, b, fit["q"], span, 0.0)
        ix = XY[:, 0] * s + tx
        iy = -XY[:, 1] * s + ty
        n_out += int(((ix < 0) | (ix >= W) | (iy < 0) | (iy >= H)).sum())
        n_tot += len(ix)
    return n_out / max(n_tot, 1)


def radial_ratio(mesh_m, photo_m, n=180):
    """방향별 최대 반경비 r_mesh/r_photo — **배율에 무관한 형상 기술자**.

    IoU 하나로는 "어디가 얼마나" 를 못 말한다. 사진 실루엣의 무게중심에서 각도 n 등분으로
    바깥 반경을 재서 비율을 보면, 값이 1 근처면 외곽선이 겹치고, 0.7 이면 그 방향으로
    메쉬가 사진의 70 % 까지밖에 못 뻗는다는 뜻이다."""
    ys, xs = np.nonzero(photo_m)
    if len(xs) == 0:
        return None
    cy, cx = ys.mean(), xs.mean()

    def prof(m):
        y2, x2 = np.nonzero(m)
        th = np.arctan2(y2 - cy, x2 - cx)
        r = np.hypot(y2 - cy, x2 - cx)
        b = ((th + np.pi) / (2 * np.pi) * n).astype(int) % n
        out = np.zeros(n)
        np.maximum.at(out, b, r)
        return out
    rp, rm = prof(photo_m), prof(mesh_m)
    ok = (rp > 1) & (rm > 1)
    if ok.sum() < n // 4:
        return None
    q = rm[ok] / rp[ok]
    return dict(median=float(np.median(q)), p10=float(np.percentile(q, 10)),
                p90=float(np.percentile(q, 90)), n_directions=int(ok.sum()),
                definition="max silhouette radius of the mesh over that of the photograph, "
                           "measured from the photograph centroid in 180 directions")


def measure_pair(parts_hi, target, shape, span, centre, groups, fit):
    """정합 결과를 **높은 점밀도**로 다시 그려 최종 수치를 낸다(탐색용 마스크보다 정밀)."""
    mesh_m, gmask = final_masks(parts_hi, fit, span, centre, shape, groups)
    mm_per_px = 1000.0 / fit["scale_px_per_m"]
    inter = int(np.count_nonzero(mesh_m & target))
    uni = int(np.count_nonzero(mesh_m | target))
    fp = int(np.count_nonzero(mesh_m & ~target))
    fn = int(np.count_nonzero(target & ~mesh_m))
    cmean, c95 = contour_error(mesh_m, target, mm_per_px)

    def bbox_ar(m):
        ys, xs = np.nonzero(m)
        w, h = float(np.ptp(xs) + 1), float(np.ptp(ys) + 1)
        return w, h, w / h
    pw, ph, par = bbox_ar(target)
    mw, mh, mar = bbox_ar(mesh_m)
    a_ph = float(np.count_nonzero(target))
    a_me = float(np.count_nonzero(mesh_m))
    return dict(
        iou=inter / uni if uni else 0.0,
        mesh_only_frac=fp / uni if uni else 0.0,
        photo_only_frac=fn / uni if uni else 0.0,
        contour_mean_mm=cmean, contour_p95_mm=c95,
        contour_mean_pct_span=(None if cmean is None else 100.0 * cmean / (span * 1000.0)),
        mm_per_px=mm_per_px,
        silhouette_px=dict(photo=[pw, ph], mesh=[mw, mh]),
        aspect_photo=par, aspect_mesh=mar,
        aspect_err_pct=100.0 * (mar - par) / par,
        # 배율이 IoU 최대로 맞춰진 뒤의 면적비 — 1보다 크면 같은 외곽에 메쉬가 더 꽉 찼다는 뜻
        fill_ratio=a_me / a_ph if a_ph else None,
        implied_span_mm=float(span * 1000.0),
        clipped_frac=clipped_fraction(parts_hi, fit, span, centre, shape),
        radial_ratio=radial_ratio(mesh_m, target),
        blobs=diff_blobs(mesh_m, target, gmask, groups, mm_per_px),
    ), mesh_m, gmask


# --------------------------------------------------------------------------- #
#  6.  그림
# --------------------------------------------------------------------------- #
def render_points(parts, fit, span, centre, shape, groups):
    """정합된 자세 그대로 **점 z-버퍼 렌더**. (RGB 이미지, 덮인 픽셀 마스크)

    삼각형 화가알고리즘(mean-depth 정렬)은 큰 삼각형이 작은 삼각형을 밀어내서
    셸 안의 배터리·PCB 가 겉으로 배어 나온다. 점은 크기가 없으므로 깊이 정렬이 곧 정답이다.
    실루엣 마스크와 **같은 점**에서 나오므로 그림과 숫자가 어긋날 수 없다."""
    from drones import DRONE_GROUP_MAT
    b = basis_roll(fit["elev"], fit["azim"], fit["roll"])
    r, u, d = b
    s, tx, ty = fit["scale_px_per_m"], fit["tx"], fit["ty"]
    L = G._LIGHT_CAM[0] * r + G._LIGHT_CAM[1] * u + G._LIGHT_CAM[2] * d
    cmap = np.array([MATERIAL_COLOR[DRONE_GROUP_MAT[g][0]] for g in groups], float)
    H, W = shape
    XYs, Ns, Gs, Ds = [], [], [], []
    for p in parts:
        pts, nrm = p["P"] - centre, p["N"]
        if p["rotor"] is not None and fit["phases"][p["rotor"]]:
            a = np.radians(fit["phases"][p["rotor"]])
            c0, s0 = np.cos(a), np.sin(a)
            R = np.array([[c0, -s0, 0.0], [s0, c0, 0.0], [0.0, 0.0, 1.0]])
            pts = spin(pts, p["center"] - centre, fit["phases"][p["rotor"]])
            nrm = nrm @ R.T
        XYs.append(project(pts, b, fit["q"], span, 0.0))
        Ns.append(nrm)
        Gs.append(p["gid"])
        Ds.append(pts @ d)
    XY = np.concatenate(XYs); N = np.concatenate(Ns)
    Gi = np.concatenate(Gs); dep = np.concatenate(Ds)
    front = (N @ d) > 0                                     # 뒷면은 그리지 않는다
    ix = np.rint(XY[:, 0] * s + tx).astype(np.int64)
    iy = np.rint(-XY[:, 1] * s + ty).astype(np.int64)
    ok = front & (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
    idx = iy[ok] * W + ix[ok]
    shade = G.AMBIENT + (1.0 - G.AMBIENT) * np.clip(N[ok] @ L, 0.0, 1.0)
    col = np.clip(cmap[Gi[ok]] * shade[:, None], 0.0, 1.0)
    order = np.argsort(dep[ok])                             # 먼 점부터 → 가까운 점이 이긴다
    img = np.ones((H * W, 3))
    cov = np.zeros(H * W, bool)
    img[idx[order]] = col[order]
    cov[idx] = True
    return img.reshape(H, W, 3), cov.reshape(H, W)


def draw_render(ax, parts, fit, span, centre, shape, groups):
    img, cov = render_points(parts, fit, span, centre, shape, groups)
    holes = ndi.binary_closing(cov, structure=np.ones((3, 3), bool)) & ~cov
    if holes.any():                                          # 점 사이 바늘구멍 = 표본 간격일 뿐이므로
        _, (yy, xx) = ndi.distance_transform_edt(~cov, return_indices=True)
        img[holes] = img[yy[holes], xx[holes]]               # 가장 가까운 렌더 색으로 메운다
    ax.imshow(img)
    ax.set_axis_off()


def _view_window(*masks, margin=0.07):
    """표시용 창 [x0,x1,y0,y1]. 계산은 넓힌 화폭에서 하고 **보여줄 때만** 여백을 잘라낸다."""
    u = masks[0].copy()
    for m in masks[1:]:
        u |= m
    ys, xs = np.nonzero(u)
    H, W = u.shape
    mx = margin * max(np.ptp(xs), np.ptp(ys))
    return (max(xs.min() - mx, 0), min(xs.max() + mx, W - 1),
            min(ys.max() + mx, H - 1), max(ys.min() - mx, 0))


def _apply_window(ax, win):
    ax.set_xlim(win[0], win[1])
    ax.set_ylim(win[2], win[3])


def _blob_letter(i):
    return "ABCD"[i] if i < 4 else "?"


#: 그림에 필요한 무거운 것(사진 마스크·고밀도 점구름·메쉬 마스크)을 (기체, 파일)별로 들고 있는다.
#: 원장만 있으면 여기서 **다시 만들 수 있다** → `redraw()` 로 재정합 없이 그림만 다시 그린다.
_CACHE: dict = {}


_PARTS: dict = {}


def _parts_for(key, props, n_final=1_200_000):
    """(기체, 프롭포함) 조합의 고밀도 점구름 — 같은 기체의 사진끼리 공유한다(메모리·시간)."""
    if (key, props) not in _PARTS:
        _PARTS[(key, props)] = mesh_parts(key, n_final, include_props=props)
    return _PARTS[(key, props)]


def _cache_for(key, rec_photo, n_final=1_200_000):
    ck = (key, rec_photo["file"])
    if ck in _CACHE and "parts" in _CACHE[ck]:
        return _CACHE[ck]
    path = os.path.join(PHOTO_DIR, key, rec_photo["file"])
    # ⚠ 마스크 크기가 정합 때와 같아야 한다 — fit 의 배율·이동이 그 픽셀계의 값이다.
    #   원장에 기록이 없으면(옛 판) 기본 실행값 640 을 쓴다.
    rgb, pm, _seg = photo_mask(path, max_side=rec_photo["segmentation"].get("max_side", 600))
    pr = _parts_for(key, rec_photo["props_in_photo"], n_final)
    mesh_m, _g = final_masks(pr["parts"], rec_photo["fit"], pr["span"], pr["centre"],
                             pm.shape, pr["groups"])
    _CACHE[ck] = dict(rgb=rgb, photo_mask=pm, mesh_mask=mesh_m, parts=pr["parts"],
                      span=pr["span"], centre=pr["centre"], groups=pr["groups"])
    return _CACHE[ck]


def fig_pair(key, J, outdir=FIG):
    """기체 1종 최종 그림: 사진 · 메쉬 · 겹침 · 숫자. 숫자는 전부 원장에서 읽는다."""
    rec = J["airframes"][key]
    best = rec["photos"][rec["best_index"]]
    meta = J["_meta"]
    cal = (meta.get("metric_calibration") or {}).get(key)
    cache = _cache_for(key, best)
    rgb, photo_m, mesh_m = cache["rgb"], cache["photo_mask"], cache["mesh_mask"]
    parts_hi, span_hi, centre_hi = cache["parts"], cache["span"], cache["centre"]
    H, W = photo_m.shape
    m = best["metrics"]
    win = _view_window(photo_m, mesh_m)      # 세 패널이 **같은 창**을 본다(여백만 잘라낸다)

    n_ph = len(rec["photos"])
    fig = plt.figure(figsize=(19.4, 10.6))
    outer = fig.add_gridspec(2, 1, height_ratios=[1.0, 0.415],
                             left=0.007, right=0.995, top=0.900, bottom=0.052, hspace=0.115)
    gs = outer[0].subgridspec(1, 4, width_ratios=[1.0, 1.0, 1.0, 1.02], wspace=0.045)

    # (a) 사진 + 추출한 실루엣 윤곽 --------------------------------------------- #
    axA = fig.add_subplot(gs[0])
    axA.imshow(rgb)
    axA.contour(photo_m.astype(float), levels=[0.5], colors=[C_PHOTO], linewidths=1.1)
    _apply_window(axA, win)
    axA.set_axis_off()
    axA.set_title(f"Photograph  ({best['file']})\nblue outline = extracted silhouette, "
                  f"{best['segmentation']['source']}", fontsize=9.6, color="#222")

    # (b) 메쉬 렌더(같은 자세) -------------------------------------------------- #
    axB = fig.add_subplot(gs[1])
    draw_render(axB, parts_hi, best["fit"], span_hi, centre_hi, (H, W), cache["groups"])
    _apply_window(axB, win)
    axB.set_title(f"Current mesh, fitted camera\naz {best['fit']['azim']:.0f}deg  "
                  f"el {best['fit']['elev']:.0f}deg  roll {best['fit']['roll']:.0f}deg  "
                  f"{_qtxt(best['fit']['q'])}", fontsize=9.6, color="#222")

    # (c) 겹침 ------------------------------------------------------------------ #
    axC = fig.add_subplot(gs[2])
    ov = np.ones((H, W, 3))
    lum = rgb.mean(2)
    ov[:] = (0.86 + 0.14 * lum)[..., None]                      # 사진을 옅게 깔아 맥락 유지
    both = mesh_m & photo_m
    ov[both] = _hex(C_AGREE)
    ov[mesh_m & ~photo_m] = _hex(C_MESH)
    ov[photo_m & ~mesh_m] = _hex(C_PHOTO)
    axC.imshow(ov)
    axC.contour(photo_m.astype(float), levels=[0.5], colors=["#0d3c5c"], linewidths=0.8)
    for i, bl in enumerate(m["blobs"]):
        y, x = bl["centroid"]
        axC.annotate(_blob_letter(i), xy=(x, y), fontsize=11, fontweight="bold",
                     color="#111", ha="center", va="center",
                     bbox=dict(boxstyle="circle,pad=0.16", fc="white", ec="#111", lw=1.0))
    _apply_window(axC, win)
    axC.set_axis_off()
    axC.set_title(f"Silhouette overlay  —  IoU = {m['iou']:.3f}", fontsize=11.4,
                  color="#222", fontweight="bold")
    axC.legend(handles=[Patch(fc=C_AGREE, label="both"),
                        Patch(fc=C_MESH, label="mesh only"),
                        Patch(fc=C_PHOTO, label="photo only")],
               loc="lower center", ncol=3, fontsize=8.6, frameon=False,
               bbox_to_anchor=(0.5, -0.055))

    # (d) 숫자 ------------------------------------------------------------------ #
    axD = fig.add_subplot(gs[3]); axD.set_axis_off()
    axD.set_xlim(0, 1); axD.set_ylim(0, 1)
    y = 0.995
    def row(lab, val, note=None, dy=0.0425, bold=False, size=9.0):
        """한 줄 = 라벨 · 값 · (여러 줄 가능한) 주석. note 는 리스트로 주면 줄바꿈된다."""
        nonlocal y
        axD.text(0.0, y, lab, fontsize=size, va="top", color="#333")
        axD.text(0.455, y, val, fontsize=size, va="top",
                 fontweight="bold" if bold else "normal")
        if note:
            for k2, ln in enumerate([note] if isinstance(note, str) else note):
                axD.text(0.455, y - 0.0265 - 0.0225 * k2, ln, fontsize=7.1, va="top", color=GRAY)
                dy += 0.0135 if k2 else 0.0125
        y -= dy
    def head(t):
        nonlocal y
        y -= 0.010
        axD.text(0.0, y, t, fontsize=9.4, va="top", fontweight="bold", color="#111")
        axD.plot([0, 1], [y - 0.019] * 2, color="#dddddd", lw=0.8)
        y -= 0.044
    head("Match")
    row("Silhouette IoU", f"{m['iou']:.3f}",
        ["intersection / union, after best-fit alignment"]
        + ([f"exact copy of this mesh scores {cal['recovered_iou']:.3f}"] if cal else []),
        bold=True, size=10.2)
    row("Mesh only", f"{100*m['mesh_only_frac']:.1f} %  of union", "mesh covers, photo does not")
    row("Photo only", f"{100*m['photo_only_frac']:.1f} %  of union", "photo covers, mesh does not")
    row("Outline error, mean", f"{m['contour_mean_mm']:.1f} mm",
        f"{m['contour_mean_pct_span']:.2f} % of the {m['implied_span_mm']:.0f} mm span")
    row("Outline error, p95", f"{m['contour_p95_mm']:.1f} mm")
    row("Silhouette aspect W/H", f"{m['aspect_mesh']:.3f}  vs  {m['aspect_photo']:.3f}",
        f"mesh is {m['aspect_err_pct']:+.1f} % — scale-free proportion check")
    row("Filled area, mesh / photo", f"{m['fill_ratio']:.3f}",
        "inside the same outline, at the fitted scale")
    rr = m.get("radial_ratio")
    if rr:
        row("Outline reach, mesh / photo", f"{rr['median']:.2f}   "
            f"[{rr['p10']:.2f} .. {rr['p90']:.2f}]",
            ["max radius per direction, median and 10-90 %",
             "1.00 means the two outlines reach equally far"])
    sens = (best["segmentation"] or {}).get("sensitivity")
    if sens and sens["fragile"]:
        row("Silhouette is threshold-bound", f"{sens['spread_pct']:.0f} %  area swing",
            ["white airframe on white background:",
             "the threshold moves the outline more", "than the mesh does"])
    if m.get("clipped_frac", 0) > 0.002:
        row("Mesh outside the frame", f"{100*m['clipped_frac']:.1f} % of mesh points",
            "clipped area counts in neither silhouette")
    head("Fitted camera")
    row("Azimuth / elevation", f"{best['fit']['azim']:.1f} / {best['fit']['elev']:.1f} deg",
        [f"declared by eye: {best['expect'][0]:.0f} / {best['expect'][1]:.0f} deg",
         f"fit sits {best['fit_delta_deg']:.0f} deg from it, "
         f"window {best['window_deg']:.0f} deg"])
    row("Image roll", f"{best['fit']['roll']:.1f} deg")
    row("Perspective", _qtxt(best["fit"]["q"]), "q = span / camera distance")
    row("Scale", f"{m['mm_per_px']:.2f} mm / pixel")
    row("Propeller phase", _phasetxt(best["fit"]["phases"]),
        ["free parameter per rotor: blade azimuth", "in a photograph is arbitrary"])
    row("Unconstrained camera", f"IoU {best['free_fit']['iou']:.3f}",
        [f"camera allowed to leave the declared aspect:",
         f"{best['free_delta_deg']:.0f} deg away, {best['free_iou_gain']:+.3f} IoU"])
    head("Largest disagreements")
    for i, bl in enumerate(m["blobs"]):
        row(f"{_blob_letter(i)}   {bl['side']}",
            f"{100*bl['area_frac']:.1f} %   {bl['area_mm2']/100.0:.1f} cm2",
            f"nearest mesh part: {bl['part']}", dy=0.038)
    if not m["blobs"]:
        row("", "no blob above 0.6 % of union")
    axD.set_ylim(min(y, 0.0) - 0.015, 1.005)      # 내용 높이에 맞춘다(축 밖으로 새지 않게)

    # (e) 이 기체의 사진 전부 — 한 장짜리 대조는 우연일 수 있다 ------------------- #
    gsb = outer[1].subgridspec(1, max(n_ph, 3), wspace=0.05)
    for i, ph in enumerate(rec["photos"]):
        axe = fig.add_subplot(gsb[i])
        c2 = _cache_for(key, ph)
        pm2, mm2 = c2["photo_mask"], c2["mesh_mask"]
        ov2 = np.ones(pm2.shape + (3,))
        ov2[mm2 & pm2] = _hex(C_AGREE)
        ov2[mm2 & ~pm2] = _hex(C_MESH)
        ov2[pm2 & ~mm2] = _hex(C_PHOTO)
        axe.imshow(ov2)
        _apply_window(axe, _view_window(pm2, mm2))
        axe.set_axis_off()
        mark = "  <- shown above" if i == rec["best_index"] else ""
        axe.set_title(f"{ph['file']}   IoU {ph['metrics']['iou']:.3f}{mark}\n"
                      f"declared aspect {ph['expect'][0]:.0f} / {ph['expect'][1]:.0f} deg, "
                      f"fit {ph['fit']['azim']:.0f} / {ph['fit']['elev']:.0f} deg, "
                      f"outline {ph['metrics']['contour_mean_mm']:.1f} mm",
                      fontsize=8.2, color=("#111" if i == rec["best_index"] else "#555"))
    fig.text(0.007, 0.043,
             f"Every photograph of this airframe that survives the source rules, fitted the same "
             f"way ({n_ph} of {rec['n_photos_available']} files in assets/photos/{key}/).",
             fontsize=8.2, color="#333", ha="left")

    fig.suptitle(f"{rec['label']}  —  mesh vs photograph"
                 + ("   [physically measured airframe]" if key in MEASURED else ""),
                 fontsize=16.0, fontweight="bold", y=0.982)
    fig.text(0.5, 0.938, best["headline"], ha="center", fontsize=10.6, color="#333")
    fig.text(0.008, 0.024,
             f"Photo: {best['credit']}  ·  licence: {best['licence'] or 'not recorded'}"
             f"  ·  {best['note']}", fontsize=7.8, color=GRAY, ha="left")
    fig.text(0.008, 0.006,
             f"Mesh rebuilt from {' + '.join(MESH_SOURCES[:2])} (newest edit "
             f"{meta['mesh_source_newest']})  ·  every number injected from "
             f"outputs/mesh_compare_photo.json, generated {meta['generated']}  ·  "
             f"IoU is measured after fitting camera pose, scale, position and per-rotor "
             f"propeller phase — it grades shape, not the size printed in the photo.",
             fontsize=7.4, color=GRAY, ha="left")
    os.makedirs(outdir, exist_ok=True)
    p = os.path.join(outdir, f"mesh_photo_{key}.png")
    fig.savefig(p, dpi=132, facecolor="white")
    plt.close(fig)
    print(f"  🖼  outputs/figures/mesh_photo_{key}.png")
    return p


def _hex(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)])


def _qtxt(q):
    return "orthographic" if q < 0.02 else f"camera at {1.0/q:.1f} x span"


def _phasetxt(ph):
    return "none (no propellers)" if not ph else " / ".join(f"{p:.0f}" for p in ph) + " deg"


def fig_summary(J, outdir=FIG):
    """7종 한 장 — 기체별 최고 IoU 막대 + 다른 사진들 점 + **지표 눈금**(자기자신 상한·민감도)."""
    A = J["airframes"]
    cal = J["_meta"].get("metric_calibration") or {}
    keys = sorted(A, key=lambda k: -A[k]["best_iou"])
    n = len(keys)
    fig = plt.figure(figsize=(16.8, 8.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.22, 1.0], height_ratios=[1.0, 0.52],
                          left=0.098, right=0.985, top=0.828, bottom=0.098,
                          wspace=0.18, hspace=0.42)

    ax = fig.add_subplot(gs[:, 0])
    ypos = np.arange(n)[::-1]
    vals = [A[k]["best_iou"] for k in keys]
    cols = ["#1b6ca8" if k in MEASURED else "#8fa6b8" for k in keys]
    ax.barh(ypos, vals, height=0.56, color=cols, zorder=3)
    for yy, k, v in zip(ypos, keys, vals):
        others = [p["metrics"]["iou"] for p in A[k]["photos"]]
        ax.plot(others, [yy] * len(others), "o", ms=5.0, mfc="white",
                mec="#37474f", mew=1.1, zorder=4, ls="none")
        ax.text(v + 0.012, yy, f"{v:.3f}", va="center", fontsize=10.2, fontweight="bold")
        ax.text(v + 0.085, yy, f"{A[k]['best_file']}", va="center", fontsize=7.6, color=GRAY)
    for yy, k in zip(ypos, keys):
        c = cal.get(k)
        if not c:
            continue
        ax.plot([c["recovered_iou"]] * 2, [yy - 0.34, yy + 0.34], color="#b71c1c", lw=2.0,
                zorder=6)
    if cal:
        ax.plot([], [], color="#b71c1c", lw=2.0,
                label="ceiling: this mesh fitted against an exact copy of itself")
        ax.legend(loc="lower right", fontsize=8.6, frameon=False)
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{A[k]['label']}" + ("  *" if k in MEASURED else "") for k in keys],
                       fontsize=10.4)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(-0.7, n - 0.1)
    ax.set_xlabel("Silhouette IoU against the best-matched photograph", fontsize=10.2)
    ax.grid(axis="x", alpha=0.25, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_title("Bar = best photo of that airframe.  Circles = every other photo fitted.  "
                 "*  physically measured airframe", fontsize=9.8, color="#333", loc="left",
                 pad=8)

    # --- 지표 눈금: 자세오차 → IoU (이 지표가 얼마나 가파른가) ------------------ #
    axc = fig.add_subplot(gs[1, 1])
    if cal:
        for k in keys:
            c = cal.get(k)
            if not c:
                continue
            d = [0.0] + [float(k2) for k2 in c["sensitivity"]["pose_off_deg"]]
            y = [c["sensitivity"]["same_pose_other_sample"]] + \
                list(c["sensitivity"]["pose_off_deg"].values())
            meas = k in MEASURED
            axc.plot(d, y, "-o" if meas else "-", color="#b71c1c" if meas else "#b8b8b8",
                     lw=2.0 if meas else 1.1, ms=4.0, zorder=4 if meas else 2)
        for j, k in enumerate([x for x in keys if x in MEASURED]):
            c = cal.get(k)
            if c:
                yy = list(c["sensitivity"]["pose_off_deg"].values())[-1]
                axc.annotate(A[k]["label"], (5.0, yy), textcoords="offset points",
                             xytext=(-6, 10 if j == 0 else -14), fontsize=8.2, ha="right",
                             color="#b71c1c")
        axc.set_xlabel("Camera pose error [deg]", fontsize=9.0)
        axc.set_ylabel("IoU", fontsize=9.0)
        axc.set_ylim(0.4, 1.03)
        axc.grid(alpha=0.25)
        for sp in ("top", "right"):
            axc.spines[sp].set_visible(False)
        axc.tick_params(labelsize=8.2)
        axc.set_title("How steep the metric is: each mesh against an exact copy of itself,\n"
                      "with the camera moved off by a few degrees.  One line per airframe.",
                      fontsize=9.0, color="#333", loc="left")
    else:
        axc.set_axis_off()

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_axis_off()
    ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    ax2.text(0.0, 0.985, "Where the mesh and the photograph disagree", fontsize=11.0,
             fontweight="bold", va="top")
    hdr = [("airframe", 0.0), ("IoU", 0.325), ("outline", 0.45), ("mesh only", 0.60),
           ("photo only", 0.745), ("largest disagreement", 0.995)]
    y = 0.885
    for t, x in hdr:
        ax2.text(x, y, t, fontsize=8.4, color=GRAY, ha="right" if x > 0.3 else "left")
    ax2.plot([0, 1], [y - 0.030] * 2, color="#cccccc", lw=0.8)
    y -= 0.100
    for k in keys:
        m = A[k]["photos"][A[k]["best_index"]]["metrics"]
        b = m["blobs"][0] if m["blobs"] else None
        ax2.text(0.0, y, A[k]["label"], fontsize=9.2, va="center")
        ax2.text(0.325, y, f"{m['iou']:.3f}", fontsize=9.2, va="center", ha="right",
                 fontweight="bold")
        ax2.text(0.45, y, f"{m['contour_mean_mm']:.0f} mm", fontsize=9.2, va="center", ha="right")
        ax2.text(0.60, y, f"{100*m['mesh_only_frac']:.0f} %", fontsize=9.2, va="center",
                 ha="right", color=C_MESH)
        ax2.text(0.745, y, f"{100*m['photo_only_frac']:.0f} %", fontsize=9.2, va="center",
                 ha="right", color=C_PHOTO)
        ax2.text(0.995, y, "-" if b is None else
                 f"{b['part']}, {100*b['area_frac']:.0f} % ({b['side']})",
                 fontsize=8.4, va="center", ha="right", color="#333")
        y -= 0.098
    ax2.text(0.0, y - 0.03, J["_meta"]["summary_note"], fontsize=8.6, color="#333", va="top")

    fig.suptitle("Seven airframes against real photographs — the number is silhouette IoU",
                 fontsize=16.0, fontweight="bold", y=0.972)
    fig.text(0.5, 0.888,
             f"{J['_meta']['n_pairs']} photographs fitted across {len(A)} airframes.  "
             f"IoU is measured after fitting camera azimuth, elevation, image roll, "
             f"perspective, scale, position and per-rotor propeller phase.",
             ha="center", fontsize=10.4, color="#333")
    fig.text(0.098, 0.030,
             f"Mesh rebuilt from {' + '.join(MESH_SOURCES[:2])} (newest edit "
             f"{J['_meta']['mesh_source_newest']})  ·  numbers injected from "
             f"outputs/mesh_compare_photo.json, generated {J['_meta']['generated']}",
             fontsize=7.6, color=GRAY, ha="left")
    p = os.path.join(outdir, "mesh_photo_summary.png")
    fig.savefig(p, dpi=134, facecolor="white")
    plt.close(fig)
    print("  🖼  outputs/figures/mesh_photo_summary.png")
    return p


# --------------------------------------------------------------------------- #
#  7.  구동
# --------------------------------------------------------------------------- #


WINDOW_DEG = 20.0        # 선언한 시선방향에서 이만큼 안에서만 자세를 찾는다(헤드라인 갈래)


# --------------------------------------------------------------------------- #
#  ⭐ 지표 눈금 — "IoU 0.5 는 얼마나 나쁜가" 에 답하는 대조군
# --------------------------------------------------------------------------- #
def calibrate(key="mini5pro", shape=(430, 640), n_final=1_200_000, n_fit=150_000,
              pose=(25.0, 18.0, -4.0, 0.30), verbose=True) -> dict:
    """메쉬로 **가짜 사진**을 만들어 같은 파이프라인에 넣는다. 두 가지를 얻는다.

    1. 상한 — 형상이 완전히 같을 때 이 파이프라인이 내는 IoU. 사진 IoU 를 읽는 기준선.
    2. 민감도 — 자세·배율·프롭 위상이 조금 어긋날 때 IoU 가 얼마나 떨어지는가.
       드론처럼 가는 구조는 IoU 가 매우 가팔라서, 이 표 없이는 숫자를 해석할 수 없다."""
    az, el, ro, q = pose
    A = mesh_parts(key, n_final, include_props=True, seed=7)
    B = mesh_parts(key, n_final, include_props=True, seed=99)
    ph = [40.0, 110.0, 20.0, 150.0][: max(1, A["n_rotors"])]
    ph = (ph * 4)[: A["n_rotors"]]
    FA = Fitter(A["parts"], A["centre"], A["span"], np.zeros(shape, bool), shape)
    FB = Fitter(B["parts"], B["centre"], B["span"], np.zeros(shape, bool), shape)
    XY = FA.xys(az, el, ro, q, ph)
    s0 = 0.92 * shape[1] / np.ptp(np.concatenate(XY)[:, 0])
    tx0, ty0 = shape[1] * 0.5, shape[0] * 0.52
    ref = clean_mask(raster_union(XY, s0, tx0, ty0, shape))

    def mB(daz=0.0, dph=0.0, fs=1.0):
        p2 = list(ph); p2[0] = p2[0] + dph
        return clean_mask(raster_union(FB.xys(az + daz, el, ro, q, p2), s0 * fs, tx0, ty0, shape))

    sens = dict(
        same_pose_other_sample=iou(ref, mB()),
        pose_off_deg={f"{d}": iou(ref, mB(daz=d)) for d in (0.5, 1.0, 2.0, 3.0, 5.0)},
        scale_off_pct={f"{d}": iou(ref, mB(fs=1 + d / 100.0)) for d in (0.5, 1.0, 2.0, 4.0)},
        one_prop_phase_off_deg={f"{d}": iou(ref, mB(dph=d)) for d in (5.0, 10.0, 20.0)})

    pr = mesh_parts(key, n_fit, include_props=True)
    t0 = time.time()
    fit, _free = fit_pose(pr["parts"], ref, shape, pr["span"], pr["centre"],
                          declared=(az, el), window_deg=WINDOW_DEG, want_free=False)
    m, _mm, _g = measure_pair(A["parts"], ref, shape, A["span"], A["centre"], A["groups"], fit)
    out = dict(
        airframe=key,
        purpose="같은 파이프라인에 **자기 자신**을 넣었을 때의 상한과 민감도",
        truth=dict(azim=az, elev=el, roll=ro, q=q, phases=ph, scale_px_per_m=float(s0)),
        recovered=dict(azim=fit["azim"], elev=fit["elev"], roll=fit["roll"], q=fit["q"],
                       phases=fit["phases"], scale_px_per_m=fit["scale_px_per_m"]),
        recovered_iou=m["iou"],
        recovered_contour_mean_mm=m["contour_mean_mm"],
        pose_error_deg=view_angle(fit["azim"], fit["elev"], az, el),
        scale_error_pct=100.0 * (fit["scale_px_per_m"] / s0 - 1.0),
        sensitivity=sens,
        reading=(f"An exact copy of the mesh scores {m['iou']:.3f} here. One degree of pose "
                 f"error takes it to {sens['pose_off_deg']['1.0']:.3f} and one percent of "
                 f"scale error to {sens['scale_off_pct']['1.0']:.3f}: arms and blades a few "
                 f"pixels wide make this metric steep."),
        runtime_s=round(time.time() - t0, 1))
    if verbose:
        print(f"  🎚  지표 눈금({key}): 자기자신 IoU {m['iou']:.3f}, "
              f"자세오차 {out['pose_error_deg']:.2f}°, 배율오차 {out['scale_error_pct']:+.2f}%")
    return out


def _headline(m, rec):
    """그림 부제 — '무엇을 했고 결과가 얼마인가' 한 줄. 숫자는 인자에서만 온다."""
    worst = m["blobs"][0] if m["blobs"] else None
    tail = ("" if worst is None else
            f"  The largest single disagreement is the {worst['part']}, "
            f"{100*worst['area_frac']:.0f} % of the union, {worst['side']}.")
    free = rec["free_fit"]
    gain = free["iou"] - m["iou"]
    tail2 = ("" if gain <= 0.02 else
             f"  A camera free to move anywhere reaches {free['iou']:.3f} by swinging "
             f"{rec['free_delta_deg']:.0f} deg off the declared aspect.")
    return (f"Silhouette IoU {m['iou']:.3f}, mean outline error {m['contour_mean_mm']:.1f} mm "
            f"({m['contour_mean_pct_span']:.2f} % of span).{tail}{tail2}")


def run_key(key, quick=False, n_fit=150_000, n_final=1_200_000):
    t0 = time.time()
    spec = DRONES[key]
    entries = PHOTOS.get(key, [])
    print(f"[{key}] {drone_label(key)} — 사진 {len(entries)}장")
    out = []
    parts_cache = {}
    for e in entries:
        path = os.path.join(PHOTO_DIR, key, e["file"])
        if not os.path.exists(path):
            print(f"    ⚠ 파일 없음: {e['file']}")
            continue
        t1 = time.time()
        rgb, pm, seg = photo_mask(path, max_side=460 if quick else 600)
        shape = pm.shape
        if e["props"] not in parts_cache:
            parts_cache[e["props"]] = (mesh_parts(key, n_fit, include_props=e["props"]),
                                       mesh_parts(key, n_final, include_props=e["props"]))
        pr, prh = parts_cache[e["props"]]
        win = float(e.get("window", WINDOW_DEG))
        fit, free = fit_pose(pr["parts"], pm, shape, pr["span"], pr["centre"],
                             declared=tuple(e["expect"]), window_deg=win,
                             quick=quick, log=lambda s: print(s))
        m, mesh_m, _g = measure_pair(prh["parts"], pm, shape, prh["span"],
                                     prh["centre"], prh["groups"], fit)
        rec = dict(file=e["file"], credit=e["credit"], licence=e["licence"],
                   provenance=e["provenance"], note=e["note"],
                   props_in_photo=bool(e["props"]),
                   compared_against=("full drone" if e["props"] else
                                     "frame only (photo has no propellers)"),
                   expect=list(e["expect"]),
                   window_deg=win,
                   fit_delta_deg=view_angle(fit["azim"], fit["elev"], *e["expect"]),
                   # 정합이 창 경계에 붙어 있으면 **선언 자세가 틀렸을 가능성**을 뜻한다.
                   fit_at_window_edge=bool(
                       view_angle(fit["azim"], fit["elev"], *e["expect"]) > 0.92 * win),
                   free_delta_deg=view_angle(free["azim"], free["elev"], *e["expect"]),
                   free_fit=free, free_iou_gain=float(free["iou"] - fit["iou"]),
                   segmentation=seg, fit=fit, metrics=m,
                   runtime_s=round(time.time() - t1, 1))
        rec["headline"] = _headline(m, rec)
        out.append(rec)
        _CACHE[(key, e["file"])] = dict(rgb=rgb, photo_mask=pm, mesh_mask=mesh_m,
                                        parts=prh["parts"], span=prh["span"],
                                        centre=prh["centre"], groups=prh["groups"])
        print(f"    {e['file']:40s} IoU {m['iou']:.3f}  outline {m['contour_mean_mm']:5.1f} mm"
              f"  (mesh-only {100*m['mesh_only_frac']:.0f}% / photo-only "
              f"{100*m['photo_only_frac']:.0f}%)  free {free['iou']:.3f} @ "
              f"{rec['free_delta_deg']:.0f} deg  [{rec['runtime_s']} s]")
    if not out:
        return None
    bi = int(np.argmax([o["metrics"]["iou"] for o in out]))
    pr = parts_cache[out[bi]["props_in_photo"]][0]
    return dict(key=key, name=spec.name, label=drone_label(key),
                span_m=pr["span"], centre_m=[float(x) for x in pr["centre"]],
                measured_airframe=key in MEASURED,
                n_photos_available=len([f for f in glob.glob(os.path.join(PHOTO_DIR, key, "*"))
                                        if not f.endswith(".md")]),
                photos=out, best_index=bi, best_file=out[bi]["file"],
                best_iou=out[bi]["metrics"]["iou"],
                runtime_s=round(time.time() - t0, 1))


def build_all(keys=None, quick=False, figures=True, calib=True):
    keys = list(keys or drone_keys())
    t0 = time.time()
    newest = max(os.path.getmtime(os.path.join(ROOT, p)) for p in MESH_SOURCES
                 if os.path.exists(os.path.join(ROOT, p)))
    cal = {k: calibrate(k) for k in keys} if calib else None
    A = {}
    for k in keys:
        r = run_key(k, quick=quick)
        if r:
            A[k] = r
    n_pairs = sum(len(v["photos"]) for v in A.values())
    ious = [v["best_iou"] for v in A.values()]
    J = dict(
        _meta=dict(
            generated=time.strftime("%Y-%m-%d %H:%M:%S"),
            generator="src/viz_mesh_photo.py :: build_all()",
            purpose="사진과 현재 메쉬의 실루엣 일치도를 숫자로 남긴다(IoU·경계오차·차이 덩어리).",
            mesh_sources={p: time.strftime("%Y-%m-%d %H:%M:%S",
                                           time.localtime(os.path.getmtime(
                                               os.path.join(ROOT, p))))
                          for p in MESH_SOURCES if os.path.exists(os.path.join(ROOT, p))},
            mesh_source_newest=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(newest)),
            n_airframes=len(A), n_pairs=n_pairs,
            iou_range=[float(min(ious)), float(max(ious))] if ious else None,
            method=dict(
                silhouette="photo: alpha channel where present, else colour distance from the "
                           "border-median background; mesh: area-weighted surface point sampling "
                           "rasterised into the same pixel grid. Identical cleanup on both "
                           "(1 px closing, holes below 0.4 % of area filled, fragments below "
                           "2 % of the largest component dropped).",
                fitted_dof="camera azimuth, elevation, image roll (together all of SO(3)), "
                           "perspective strength q = span / camera distance, isotropic scale, "
                           "translation, and one propeller phase per rotor.",
                why_scale_is_fitted="the silhouette test grades shape. Absolute size is graded "
                                    "separately against the published envelope, in "
                                    "outputs/mesh_gallery.json.",
                why_prop_phase_is_fitted="blade azimuth in a photograph is whatever the "
                                         "photographer left it at; holding it fixed would grade "
                                         "coincidence instead of geometry.",
                iou="intersection over union of the two silhouettes at the fitted pose.",
                contour_error="symmetric distance between the two outlines, mean and 95th "
                              "percentile, converted to mm by the fitted scale.",
                blobs="connected components of the disagreement larger than 0.6 % of the union, "
                      "attributed to the mesh part that occupies (mesh-only) or lies nearest "
                      "(photo-only) that area.",
                search="two branches. The headline fit keeps the viewing direction within "
                       f"{WINDOW_DEG:.0f} deg of the aspect declared by eye for that photograph, "
                       "so the mesh is graded at the angle the photograph was actually taken "
                       "from. A second, unconstrained fit sweeps azimuth over the full circle "
                       "and elevation -36 to +90 deg; free_iou_gain is how much IoU the camera "
                       "buys by leaving the declared aspect, and a large gain is a shape "
                       "difference, not a pose ambiguity.",
                calibration="every airframe is also fitted against an exact copy of its own "
                            "mesh, so each one has its own ceiling: "
                            + (", ".join(f"{k} {v['recovered_iou']:.3f}"
                                         for k, v in sorted(cal.items())) if cal else "n/a")
                            + ". The ceiling is not 1.0 because arms and blades are a few pixels "
                              "wide, which makes IoU steep. _meta.metric_calibration holds the "
                              "sensitivity table per airframe.",
                limits="orthographic-plus-single-q camera, no lens distortion, no articulation "
                       "other than propeller phase (gimbal pitch, arm fold and landing-gear "
                       "state stay as built).",
            ),
            summary_note=(""),
            metric_calibration=cal,
            excluded=EXCLUDED,
            figures=dict(per_airframe="outputs/figures/mesh_photo_<key>.png",
                         summary="outputs/figures/mesh_photo_summary.png"),
            runtime_s=round(time.time() - t0, 1)),
        airframes=A)
    # 요약 한 줄도 계산값으로 만든다(손으로 적지 않는다)
    if A:
        lo = min(A, key=lambda k: A[k]["best_iou"])
        hi = max(A, key=lambda k: A[k]["best_iou"])
        J["_meta"]["summary_note"] = (
            f"Best match {A[hi]['label']} at IoU {A[hi]['best_iou']:.3f}, "
            f"weakest {A[lo]['label']} at {A[lo]['best_iou']:.3f}. "
            f"Outline error runs "
            f"{min(v['photos'][v['best_index']]['metrics']['contour_mean_mm'] for v in A.values()):.0f}"
            f" to "
            f"{max(v['photos'][v['best_index']]['metrics']['contour_mean_mm'] for v in A.values()):.0f}"
            f" mm.")
    partial = sorted(A) != sorted(drone_keys())
    if not partial:
        os.makedirs(OUT, exist_ok=True)
        with open(LEDGER, "w", encoding="utf-8") as f:
            json.dump(J, f, ensure_ascii=False, indent=1)
        print(f"  📒 outputs/mesh_compare_photo.json  ({len(A)}종 / {n_pairs}쌍)")
    else:
        print(f"  ⚠ 부분 실행({len(A)}/{len(DRONES)}종) — 원장을 덮어쓰지 않는다.")
    if figures:
        for k in A:
            fig_pair(k, J)
        if not partial:
            fig_summary(J)
    return J


def calibrate_into_ledger(keys=None):
    """이미 있는 원장에 **기체별 지표 눈금**만 계산해 덧붙인다(정합은 다시 하지 않는다)."""
    with open(LEDGER, encoding="utf-8") as f:
        J = json.load(f)
    cal = J["_meta"].get("metric_calibration")
    cal = cal if isinstance(cal, dict) and "recovered_iou" not in cal else {}
    for k in (keys or list(J["airframes"])):
        cal[k] = calibrate(k)
    for k, rec in J["airframes"].items():           # 옛 원장에는 없는 진단을 채워 넣는다
        for ph in rec["photos"]:
            ph.setdefault("fit_at_window_edge",
                          bool(ph["fit_delta_deg"] > 0.92 * ph["window_deg"]))
    J["_meta"]["metric_calibration"] = cal
    J["_meta"]["method"]["calibration"] = (
        "every airframe is also fitted against an exact copy of its own mesh, so each one has "
        "its own ceiling: " + ", ".join(f"{k} {v['recovered_iou']:.3f}"
                                        for k, v in sorted(cal.items()))
        + ". The ceiling is not 1.0 because arms and blades are a few pixels wide, which makes "
          "IoU steep. _meta.metric_calibration holds the sensitivity table per airframe.")
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    print(f"  📒 눈금 {len(cal)}종을 원장에 기록했다")
    return J


def remeasure(keys=None):
    """두 갈래를 **같은 점밀도(120만)** 로 다시 재고 잘림 진단을 채운다.

    탐색용 마스크(15만 점)와 최종 마스크의 값은 다르다. 두 갈래를 나란히 놓으려면 같은 자로
    재야 한다 — 그러지 않으면 free_iou_gain 이 밀도 차이를 섞어 담는다."""
    with open(LEDGER, encoding="utf-8") as f:
        J = json.load(f)
    for k in (keys or list(J["airframes"])):
        rec = J["airframes"][k]
        for ph in rec["photos"]:
            path = os.path.join(PHOTO_DIR, k, ph["file"])
            _rgb, pm, _sg = photo_mask(path, max_side=ph["segmentation"].get("max_side", 600))
            pr = _parts_for(k, ph["props_in_photo"])
            md, _mm, _g = measure_pair(pr["parts"], pm, pm.shape, pr["span"], pr["centre"],
                                       pr["groups"], ph["fit"])
            mf, _mm, _g = measure_pair(pr["parts"], pm, pm.shape, pr["span"], pr["centre"],
                                       pr["groups"], ph["free_fit"])
            ph["metrics"] = md
            ph["free_fit"]["iou_search_grid"] = ph["free_fit"]["iou"]
            ph["free_fit"]["iou"] = mf["iou"]
            ph["free_fit"]["contour_mean_mm"] = mf["contour_mean_mm"]
            ph["free_fit"]["clipped_frac"] = mf["clipped_frac"]
            ph["free_iou_gain"] = float(mf["iou"] - md["iou"])
            ph["segmentation"].setdefault(
                "sensitivity", seg_sensitivity(path, ph["segmentation"].get("max_side", 600)))
            ph["headline"] = _headline(md, ph)
            print(f"  {k:12s} {ph['file']:40s} IoU {md['iou']:.3f}  free {mf['iou']:.3f} "
                  f"(gain {ph['free_iou_gain']:+.3f})  clipped {100*md['clipped_frac']:.2f} %")
        rec["best_index"] = int(np.argmax([o["metrics"]["iou"] for o in rec["photos"]]))
        rec["best_file"] = rec["photos"][rec["best_index"]]["file"]
        rec["best_iou"] = rec["photos"][rec["best_index"]]["metrics"]["iou"]
        _PARTS.clear()
    J["_meta"]["method"]["free_branch"] = (
        "the unconstrained fit is re-measured at the same point density as the headline, so the "
        "two IoUs are on one scale. free_fit.iou_search_grid keeps the coarser search value.")
    with open(LEDGER, "w", encoding="utf-8") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    return J


def redraw(keys=None):
    """원장(outputs/mesh_compare_photo.json)만 읽어 **재정합 없이 그림만** 다시 그린다."""
    with open(LEDGER, encoding="utf-8") as f:
        J = json.load(f)
    for k in (keys or J["airframes"]):
        fig_pair(k, J)
    fig_summary(J)
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-calib", action="store_true")
    ap.add_argument("--redraw", action="store_true", help="원장에서 그림만 다시 그린다")
    ap.add_argument("--calib-only", action="store_true", help="원장에 기체별 눈금만 덧붙인다")
    ap.add_argument("--finalise", action="store_true",
                    help="원장 후처리: 자유갈래 재측정 + 기체별 눈금 + 그림 재생성")
    a = ap.parse_args()
    ks = [k.strip() for k in a.keys.split(",")] if a.keys else None
    if a.finalise:
        remeasure(ks)
        calibrate_into_ledger(ks)
        redraw(ks)
    elif a.calib_only:
        calibrate_into_ledger(ks)
    elif a.redraw:
        redraw(ks)
    else:
        build_all(ks, quick=a.quick, figures=not a.no_figures, calib=not a.no_calib)
    print("사진 대조 완료 →", os.path.relpath(FIG, ROOT))
