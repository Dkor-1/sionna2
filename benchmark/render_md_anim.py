# -*- coding: utf-8 -*-
"""
render_md_anim.py — ⭐**호버링하는 드론 애니메이션**(프로펠러만 도는 GIF)을 Sionna 렌더로 만든다.

왜
--
사용자 요청(2026-08-10): *"혹시 호버링하는 드론 애니메이션도 렌더링해서 보여줄 수 있을까?
레포트7에 넣고싶어"*

리포트 07 의 논지는 «호버링 = 정지가 아니다» 이다. 기체는 제자리에 떠 있지만 프로펠러는
초당 수십 바퀴를 돈다. 그 회전이 **신호의 전부**다 — 그것이 마이크로도플러다. 정지 그림
(report07_f0a/f0b/f0c)은 배치를 보여줄 뿐 «무엇이 움직이는가» 를 못 보여준다. 이 스크립트가
그 한 컷을 움직이게 만든다.

무엇을 그리나
  · 기체는 제자리(호버 자세, 원점). **로터만 돈다.**
  · 로터별 rpm 과 회전 방향(CW/CCW 혼합)은 `articulated_fast.FastPoser` 가 이미 가진 것을
    그대로 쓴다 — 여기서 새로 정하지 않는다.
  · 시점은 **레이더가 보는 방향**(az 0 · el −15°, 배 쪽). `render_md_scene.py` 의 f0b 와
    같은 시선축이되, 드론이 화면을 채우도록 그 축 위에서 앞으로 당긴 위치다
    (TX/RX 는 카메라 뒤로 빠져 안 보인다 — 배치 그림은 f0a/f0b/f0c 가 이미 담당한다).
  · ⚠ **글자 없음**(라벨·주석·스케일바 전부 없음). 설정은 리포트 본문이 담는다.

루프
  블레이드 한 주기(= 360°/날개수 회전)를 프레임으로 균등 분할한다. 2날 프로펠러는 180°
  회전에 형상이 그대로이므로 GIF 가 끊김 없이 돈다. 로터마다 rpm 이 다르지만 한 주기 동안의
  위상 어긋남은 ±(180°×rpm산포) ≈ 0.4° 라 눈에 보이지 않는다(JSON 에 기록).
  ⚠ 실제 회전(초당 ~63 바퀴)은 사람 눈에 안 보인다 → **슬로모션**이고, 몇 배인지 JSON 에 남긴다.

시나리오 출처
  `outputs/report07_three_engines.json` 의 `_meta`(기체·az·el·거리·f_c·로터별 rpm)를
  **읽는 시점 값으로** 쓴다. 하드코딩하지 않는다. 파일이 없거나 갱신 중이면 스펙에서 다시
  계산한다(그 사실도 JSON 에 남긴다).

    PYTHONPATH=src python benchmark/render_md_anim.py            # 본 산출
    PYTHONPATH=src python benchmark/render_md_anim.py --smoke    # 2 프레임 저해상도 점검

환경변수(재현용 주입점)
    SIONNA2_GPU        쓸 GPU 고정(없으면 MDANIM_GPUS 후보 중 여유 메모리 최대 카드)
    MDANIM_GPUS        후보 GPU 목록 (기본 "0,1,3")
    MDANIM_RES_W/H     프레임 렌더 해상도 (기본 1440×900)
    MDANIM_SPP         프레임당 표본 수 (기본 512)  ⚠ W·H·spp·4 B 가 GPU 메모리다
    MDANIM_FRAMES      프레임 수 (기본 32)
    MDANIM_MS          GIF 프레임 지연 [ms] (기본 60)
    MDANIM_GIF_W       GIF 가로 픽셀 (기본 960 — 렌더본을 축소해 파일을 줄인다)
    MDANIM_MAX_MB      GIF 상한 [MB] (기본 8.0)

산출
    outputs/figures/report07_anim.gif          최종 애니메이션
    outputs/figures/report07_anim_poster.png   첫 프레임 정지컷(GIF 안 되는 뷰어용)
    outputs/report07_anim.json                 근거·설정 기록
"""
from __future__ import annotations

import argparse
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
    """후보(기본 0·1·3) 중 여유 메모리가 가장 많은 카드를 고른다.
    ⚠ 2026-08-10 현재 GPU2 는 σ격자·RCS 스윕·세 엔진 재계산이 점유 중이라 후보에서 뺀다
      (MDANIM_GPUS 로 덮을 수 있다)."""
    free = _gpu_free_mb()
    forced = os.environ.get("SIONNA2_GPU")
    cands = [int(x) for x in os.environ.get("MDANIM_GPUS", "0,1,3").split(",") if x.strip()]
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
#  ⚠ 프레임 스크래치는 .gitignore 에 등록된 outputs/meshes/report15_probe/ 아래에만 둔다.
FRAMES = os.path.join(RP.SCRATCH, "report07_anim_frames")

#  ⚠ 표본 버퍼 = W·H·spp·4 B 가 GPU 메모리에 그대로 잡힌다(실패 전례: 2560×1600×2048 = 32 GiB OOM).
#    2026-08-10 현재 공용 카드 0·1·3 의 여유는 1.8~3.6 GiB 사이에서 출렁인다 → 1.3 GB 로 잡는다.
#    가로로 긴 2:1 프레임인 이유: 이 기체는 가로 0.62 m · 세로 0.19 m 라 정사각 프레임은 흰 여백이다.
RES_W = int(os.environ.get("MDANIM_RES_W", "1600"))
RES_H = int(os.environ.get("MDANIM_RES_H", "800"))
SPP = int(os.environ.get("MDANIM_SPP", "256"))
N_FRAMES = int(os.environ.get("MDANIM_FRAMES", "36"))
DELAY_MS = int(os.environ.get("MDANIM_MS", "60"))
GIF_W = int(os.environ.get("MDANIM_GIF_W", "1280"))
MAX_MB = float(os.environ.get("MDANIM_MAX_MB", "8.0"))
FOV = 26.0                       # render_md_scene.py 의 f0b 와 같은 화각
FILL = 0.78                      # 드론이 화면 가로의 몇 할을 채울까 (카메라 거리를 이걸로 정한다)
#  ⚠ 정직성: `Scene.render_to_file` 에는 시드 인자가 없다(서명 실측). 재현성은 «자세·카메라·
#    spp·해상도가 결정론적으로 정해진다» 는 데서 온다 — 위상은 rpm 과 프레임 수로 계산되고
#    카메라는 메쉬 크기에서 역산되므로, 같은 인자로 다시 돌리면 같은 그림이 나온다.


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
    return dict(source=src, meta=meta, spec=spec, drone=key, fc_hz=fc,
                az_deg=az, el_deg=el, range_m=rng, rpm_per_rotor=rpms,
                blades=blades, f_flash_hz=f_flash)


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


def camera_axis(az_deg: float, el_deg: float):
    """레이더 → 표적 시선의 정규직교 기저 (w=시선방향, r=화면 가로, v=화면 세로)."""
    u = RP.look_dir(az_deg, el_deg)                     # 표적 → 레이더
    w = -u / np.linalg.norm(u)                          # 카메라가 보는 방향(레이더 → 표적)
    up = np.array([0.0, 0.0, 1.0])
    r = np.cross(w, up); r /= np.linalg.norm(r)
    v = np.cross(r, w)
    return u / np.linalg.norm(u), w, r, v


def frame_camera(mv, az_deg, el_deg, res, fov=FOV, fill=FILL):
    """드론이 화면 가로의 `fill` 만큼을 채우도록 **시선축 위에서** 카메라 거리를 정한다.
    ⭐ 거리를 손으로 박지 않고 **렌더될 크기에서 역산**한다(기체가 바뀌어도 프레이밍이 산다).
    겨냥점은 메쉬 바운딩박스 중심 — 원점을 겨누면 기체가 화면에서 위로 치우친다."""
    u, w, r, v = camera_axis(az_deg, el_deg)
    b0, b1 = mv.bounds()
    c = (np.asarray(b0, float) + np.asarray(b1, float)) / 2.0
    V = np.asarray(mv.v, float) - c
    half_r = float(np.abs(V @ r).max())
    half_v = float(np.abs(V @ v).max())
    fx = math.radians(fov) / 2.0
    fy = math.atan(math.tan(fx) * res[1] / res[0])
    d = max(half_r / math.tan(fx * fill), half_v / math.tan(fy * fill))
    pos = c + d * u                                      # 표적 중심에서 레이더 쪽으로 d
    return (rt.Camera(position=mi.Point3f(*[float(x) for x in pos]),
                      look_at=mi.Point3f(*[float(x) for x in c])),
            dict(position=[float(x) for x in pos], look_at=[float(x) for x in c],
                 distance_m=float(d), fov_deg=float(fov), fill_frac=float(fill),
                 half_width_m=half_r, half_height_m=half_v,
                 aim_ko="메쉬 바운딩박스 중심"))


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


# --------------------------------------------------------------------------- #
#  GIF 조립 — render_rt.make_gif 규약(PIL 만·loop=0·optimize) + **크기 상한 강제**
# --------------------------------------------------------------------------- #
def build_gif(png_files, out_path, ms=DELAY_MS, width=GIF_W, max_mb=MAX_MB) -> dict:
    """프레임 PNG → GIF. 색수·해상도를 낮춰가며 `max_mb` 이하로 맞춘다.

    ⭐ **전역 팔레트**를 쓴다(프레임마다 팔레트를 새로 뽑는 render_rt.make_gif 와 다른 점).
      배경이 흰색으로 고정된 이 장면에서는 프레임별 팔레트가 깜빡임을 만들고 파일도 더 크다."""
    from PIL import Image
    src = [Image.open(p).convert("RGB") for p in png_files]
    attempts = []
    for width_try in (width, int(width * 0.85), int(width * 0.72)):
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
                if all(v >= 248 for v in pl[j:j + 3]):
                    pl[j:j + 3] = [255, 255, 255]
            for im in q:
                im.putpalette(pl)
            q[0].save(out_path, save_all=True, append_images=q[1:], duration=ms,
                      loop=0, optimize=True)
            mb = os.path.getsize(out_path) / 1e6
            attempts.append(dict(width=width_try, colors=colors, mb=round(mb, 3)))
            print(f"    [gif] {width_try}×{h} · {colors}색 → {mb:.2f} MB", flush=True)
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
                colors=attempts[-1]["colors"], delay_ms=int(ms), n_frames=len(png_files),
                loop=0, attempts=attempts, under_limit=False, max_mb=max_mb)


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", default=None, help="기본은 report07_three_engines.json 의 기체")
    ap.add_argument("--frames", type=int, default=N_FRAMES)
    ap.add_argument("--spp", type=int, default=SPP)
    ap.add_argument("--res", default=f"{RES_W}x{RES_H}")
    ap.add_argument("--periods", type=int, default=1, help="루프에 담을 블레이드 주기 수")
    ap.add_argument("--smoke", action="store_true", help="2 프레임·저해상도 점검(산출물 안 덮음)")
    ap.add_argument("--keep-frames", action="store_true")
    a = ap.parse_args()

    res = tuple(int(x) for x in a.res.lower().split("x"))
    n_f, spp = a.frames, a.spp
    if a.smoke:                                           # 화면비는 그대로 두고 크기·표본만 줄인다
        n_f, spp, res = 2, 64, (res[0] // 2, res[1] // 2)

    sc = scenario(a.drone)
    spec = sc["spec"]
    fp = FastPoser(spec)                                  # 호버 = 몸체 고정, 로터만 돈다
    rpms = np.asarray(sc["rpm_per_rotor"], float)

    # ── 루프 시간축 ────────────────────────────────────────────────────────
    #   블레이드 주기 T = 1/f_flash. n_periods·T 를 프레임으로 **균등 분할**(endpoint 제외)
    #   → 마지막 프레임 다음이 첫 프레임이라 GIF 가 이어진다.
    T = 1.0 / float(sc["f_flash_hz"])
    t = np.arange(n_f) / n_f * (a.periods * T)
    ph = rotor_phases(t, rpms, fp.dirs)                    # (n_f, n_rotors) [deg]
    #  로터별 rpm 이 다르니 한 바퀴 뒤 위상이 정확히 안 맞는다 — 그 어긋남을 잰다(정직성).
    #  이상적이면 각 로터가 정확히 `periods × (360/날개수)` 만큼 돌아 형상이 되돌아온다.
    close = np.abs(rotor_phases(np.array([a.periods * T]), rpms, fp.dirs)[0] - ph[0])
    ideal = a.periods * 360.0 / sc["blades"]
    seam_deg = float(np.abs((close - ideal + 180.0) % 360.0 - 180.0).max())

    playback_s = n_f * DELAY_MS / 1000.0
    slowmo = playback_s / (a.periods * T)

    print(f"\n═══ {spec.name} 호버 애니메이션 ═══")
    print(f"  시나리오 출처 : {sc['source']}")
    print(f"  GPU {GPU_INFO['gpu']} (여유 {GPU_INFO['free_mb']} MiB) — {GPU_INFO['why_ko']}")
    print(f"  f_flash {sc['f_flash_hz']:.2f} Hz · 블레이드 주기 {T*1e3:.3f} ms × {a.periods}")
    print(f"  로터별 rpm {np.round(rpms, 1).tolist()} · 방향 {fp.dirs}")
    print(f"  프레임 {n_f} 장 · {res[0]}×{res[1]} · spp {spp} "
          f"(표본버퍼 {res[0]*res[1]*spp*4/1e9:.2f} GB)")
    print(f"  재생 {playback_s:.2f} s → 슬로모션 ×{slowmo:.0f} · 이음매 어긋남 {seam_deg:.2f}°",
          flush=True)

    os.makedirs(FIGDIR, exist_ok=True)
    if os.path.isdir(FRAMES):
        shutil.rmtree(FRAMES, ignore_errors=True)
    os.makedirs(FRAMES, exist_ok=True)

    files, per_frame, spp_used, camrec, geo = [], [], [], None, None
    t_all = time.time()
    for i in range(n_f):
        t0 = time.time()
        scene, d, mv = posed_scene(fp, spec, ph[i], f"ANIM{i % 2}", sc["fc_hz"])
        #  TX/RX 는 정본 배치대로 넣되(기하를 JSON 에 남기려고) 렌더에는 안 그린다
        #  (show_devices=False) — 이 그림의 주인공은 도는 프로펠러다.
        geo = RP.place(scene, az=sc["az_deg"], el=sc["el_deg"], rng=sc["range_m"])
        if camrec is None:
            camera, camrec = frame_camera(mv, sc["az_deg"], sc["el_deg"], res)
        p = os.path.join(FRAMES, f"frame_{i:03d}.png")
        #  ⚠ 공용 GPU 라 여유가 프레임 중간에 줄 수 있다. OOM 이면 죽지 말고 spp 를 반으로
        #    줄여 다시 시도한다(프레임마다 다른 spp 를 쓰면 밝기가 아니라 잡음만 달라진다).
        spp_i = spp
        while True:
            try:
                scene.render_to_file(camera=camera, filename=p, num_samples=spp_i,
                                     resolution=res, fov=FOV, show_devices=False)
                break
            except Exception as e:
                if spp_i <= 32:
                    raise
                spp_i //= 2
                print(f"    ⚠ 프레임 {i} 렌더 실패({type(e).__name__}) → spp {spp_i} 로 재시도",
                      flush=True)
        spp_used.append(int(spp_i))
        white_png(p)
        files.append(p)
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
                  f"누적 {done:6.1f}s  ETA {(n_f-i-1)*np.mean(per_frame):5.1f}s", flush=True)
    render_s = time.time() - t_all

    if a.smoke:
        print(f"\n[smoke] 프레임만 확인: {FRAMES}\n  카메라 {camrec}")
        return

    shutil.copyfile(files[0], POSTER)                     # 정지컷 = 첫 프레임(렌더 해상도 그대로)
    gif = build_gif(files, GIF)

    rec = {
        "_meta": {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "script": "benchmark/render_md_anim.py",
            "purpose_ko": ("리포트 07 — 호버링은 «정지» 가 아니다. 기체는 제자리, 프로펠러만 돈다. "
                           "그 회전이 마이크로도플러의 원천이라는 것을 움직임으로 보여준다."),
            "scenario_source": sc["source"],
            "drone": sc["drone"], "name": spec.name,
            "fc_hz": sc["fc_hz"], "az_deg": sc["az_deg"], "el_deg": sc["el_deg"],
            "range_m": sc["range_m"],
            "determinism_ko": ("Scene.render_to_file 에는 시드 인자가 없다(서명 실측). "
                               "재현성은 자세(rpm·프레임 수로 계산)·카메라(메쉬 크기에서 역산)·"
                               "spp·해상도가 모두 결정론적이라는 데서 온다."),
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
        "loop": {
            "f_flash_hz": float(sc["f_flash_hz"]),
            "blade_period_ms": float(T * 1e3),
            "n_periods": int(a.periods),
            "loop_real_ms": float(a.periods * T * 1e3),
            "n_frames": int(n_f),
            "blade_deg_per_frame": float(a.periods * (360.0 / sc["blades"]) / n_f),
            "rotor_deg_per_frame": float(a.periods * 360.0 * rpms.mean() / 60.0 * T / n_f),
            "playback_s": float(playback_s),
            "frame_delay_ms": int(DELAY_MS),
            "slowmotion_factor": float(slowmo),
            "seam_mismatch_deg": float(seam_deg),
            "seam_note_ko": ("로터마다 rpm 이 달라 한 주기 뒤 위상이 정확히 안 맞는다. "
                             "그 어긋남이 seam_mismatch_deg 이고, 이 값이 작아서 루프가 이어진다."),
            "honesty_ko": (f"실제 프로펠러는 초당 {rpms.mean()/60:.1f} 바퀴 돈다. "
                           f"그대로 재생하면 눈에 안 보이므로 이 GIF 는 "
                           f"약 {slowmo:.0f} 배 느린 슬로모션이다."),
        },
        "render": {
            "engine": "Sionna RT scene.render_to_file (Mitsuba path tracer)",
            "resolution": [int(res[0]), int(res[1])], "spp": int(spp),
            "spp_actual_min": int(min(spp_used)), "spp_actual_max": int(max(spp_used)),
            "spp_downgraded_frames": int(sum(1 for s in spp_used if s < spp)),
            "sample_buffer_gb": float(res[0] * res[1] * spp * 4 / 1e9),
            "camera": camrec,
            "camera_note_ko": ("render_md_scene.py 의 f0b 와 같은 시선축(레이더 → 표적, az 0 · "
                               "el −15°)이되, 드론이 화면을 채우도록 그 축 위에서 앞으로 당겼다. "
                               "TX/RX 는 카메라 뒤라 화면에 없다 — 배치는 f0a/f0b/f0c 담당."),
            "geometry": geo,
            "background": "white (viz_report1._whiten 과 같은 밝기-알파 합성)",
            "text_in_figure": "none (규약: 렌더 안에 글자 금지)",
            "seconds_total": float(render_s),
            "seconds_per_frame_mean": float(np.mean(per_frame)),
            "seconds_per_frame_min": float(np.min(per_frame)),
            "seconds_per_frame_max": float(np.max(per_frame)),
        },
        "outputs": {
            "gif": os.path.relpath(GIF, ROOT),
            "poster_png": os.path.relpath(POSTER, ROOT),
            "gif_size_mb": gif["size_mb"], "gif_px": [gif["width"], gif.get("height")],
            "gif_colors": gif["colors"], "gif_under_limit": gif["under_limit"],
            "gif_max_mb": gif["max_mb"], "gif_attempts": gif["attempts"],
        },
        #  ⭐ 리포트 본문에 넣을 문단 초안 — 숫자는 위 기록에서 그대로 뽑아 쓴다(손입력 금지).
        #     ⚠ make_report07_overview.py 는 이 스크립트가 건드리지 않는다. 초안만 남긴다.
        "report_paragraph_ko": (
            f"호버링하는 {spec.name}. 기체는 제자리에 떠 있지만 프로펠러 {int(spec.num_rotors)}개는 "
            f"계속 돈다(호버 {rpms.mean():.0f} rpm, 로터마다 조금씩 다르고 CW/CCW 가 섞여 있다). "
            f"시점은 레이더가 보는 방향(방위 {sc['az_deg']:.0f}° · 고각 {sc['el_deg']:.0f}°)이라 "
            f"이 그림이 곧 송수신기가 마주보는 면이다. 볼 것은 하나다 — 동체는 한 픽셀도 "
            f"안 움직이는데 블레이드의 방향만 프레임마다 바뀐다. 그 바뀌는 부분이 되돌아오는 "
            f"신호의 위상을 흔들고, 그것이 이 편에서 다루는 마이크로도플러다. "
            f"⚠ 실제 블레이드는 초당 {rpms.mean()/60:.0f} 바퀴를 돌아 눈으로는 볼 수 없다 — "
            f"이 애니메이션은 블레이드 한 주기({T*1e3:.1f} ms)를 {n_f} 프레임으로 나눈 "
            f"약 {slowmo:.0f} 배 슬로모션이다."),
        "reproduce": ("SIONNA2_GPU=%d PYTHONPATH=src python benchmark/render_md_anim.py "
                      "--frames %d --spp %d --res %dx%d" %
                      (GPU_INFO["gpu"], n_f, spp, res[0], res[1])),
    }
    with open(OUTJ, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)

    if not a.keep_frames:
        shutil.rmtree(FRAMES, ignore_errors=True)

    print(f"\n✅ {os.path.relpath(GIF, ROOT)}  {gif['size_mb']:.2f} MB "
          f"({gif['width']}×{gif.get('height')} · {gif['colors']}색 · {n_f} 프레임)")
    print(f"✅ {os.path.relpath(POSTER, ROOT)}")
    print(f"✅ {os.path.relpath(OUTJ, ROOT)}")
    print(f"   렌더 {render_s:.1f}s (프레임당 {np.mean(per_frame):.2f}s) · "
          f"슬로모션 ×{slowmo:.0f}")


if __name__ == "__main__":
    main()
