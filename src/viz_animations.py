# -*- coding: utf-8 -*-
"""
viz_animations.py — 실험별 애니메이션(GIF) 모음 (matplotlib, GPU 불필요)
=========================================================================
이미 있는 GIF: turntable_*(report1), report3_articulation, report4_tracking.
여기서 추가로 만드는 것:
  report2_anim_rcs.gif            : 표적 회전 → RCS 글린트 + 조명면 변화 (report2)
  report3_anim_microdoppler.gif   : 회전 프로펠러 + 스펙트로그램 시간커서 (report3)
  report2_anim_occupancy.gif      : 점유 G1→G2→G3 그리드 채움 + 거리분해능 (report2)
"""
from __future__ import annotations
import os
import numpy as np

import vizstyle
vizstyle.use_korean()
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Polygon as MplPoly
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from drones import DRONES, build_drone, build_propeller, drone_label
from rcs_po import drone_rcs_pattern, drone_rcs_pattern_bw, angular_smooth, dbsm

FIG = os.path.join(os.path.dirname(__file__), "..", "outputs", "figures")
#  ⭐ 2026-07-30 (Phase 3): `name.replace("DJI ", "")` 였다 — DJI 만 아는 규약이라 비-DJI
#     기종(Yuneec·Holybro)은 제조사 접두어가 그대로 남아 그림 제목만 형식이 달랐다.
#     제조사 목록을 아는 곳은 `drones.drone_label` 한 군데뿐이다(기존 5종 문자열은 동일).
_NAME = {k: drone_label(k) for k in DRONES}


def _face_geom(mesh):
    V = np.array(mesh.v); F = np.array(mesh.f)
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    nrm = np.cross(v1 - v0, v2 - v0)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nhat = nrm / (np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-30)
    return V, F, nhat, area


def _look(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])


# --------------------------------------------------------------------------- #
#  (1) report2 — RCS 글린트 스윕 (표적 회전 시 RCS 출렁 + 조명면)
# --------------------------------------------------------------------------- #
def _visible_faces(scene, cen, u):
    """면 무게중심에서 레이더 방향(+û)으로 광선을 쏴 **탈출하는 면만** 남긴다(가림 판정).

    ⚠ 이게 없으면 n̂·û>0 이라는 이유만으로 **앞 구조에 가려진 뒷면까지 '조명면'으로 색칠**하게 된다
      — 그림이 물리적으로 틀린다. SBR(rcs_sbr)이 σ 에서 하는 것과 같은 판정을 색칠에도 적용한다."""
    import mitsuba as mi
    O = cen + 1e-3 * u
    si = scene.ray_intersect(mi.Ray3f(o=mi.Point3f(*O.T.astype(np.float32)),
                                      d=mi.Vector3f(*np.tile(u, (len(O), 1)).T.astype(np.float32))))
    return ~np.asarray(si.is_valid()).astype(bool)       # True = 가려지지 않음(진짜 조명면)


def anim_rcs_aspect(outdir=FIG, target="mavic4pro", fc=3.5e9, el=22.0, n_frames=48, fps=12):
    spec = DRONES[target]; mesh = build_drone(spec)
    V, F, nhat, area = _face_geom(mesh)
    tris0 = [[V[a], V[b], V[c]] for (a, b, c) in mesh.f]
    # 가림 판정용 Mitsuba 씬 — σ 를 내는 SBR 과 **같은 기하**를 쓴다(한 번만 만들고 프레임마다 재사용)
    from rcs_sbr import _mi_scene_from_mesh
    from drones import DRONE_GROUP_MAT
    _scene, _, _ = _mi_scene_from_mesh(mesh, {g: m for g, (m, _d) in DRONE_GROUP_MAT.items()})
    cen = V[F].mean(axis=1)
    az_fine = np.arange(0, 360, 2.0)
    # 대역폭 평균(100MHz) — 단일주파수 널은 이산화 의존 아티팩트라 그리지 않는다(rcs_po 참조)
    sig, _ = drone_rcs_pattern_bw(target, fc, 100e6, az_fine, el_deg=el)
    sig = angular_smooth(sig, 3.0, float(az_fine[1] - az_fine[0]))   # 정적 폴라 그림과 동일 규약
    rcs_db = dbsm(sig)
    az_frames = np.linspace(0, 360, n_frames, endpoint=False)
    cmap = cm.inferno
    b0, b1 = V.min(0), V.max(0); c = (b0+b1)/2; half = (b1-b0).max()/2

    DR = 25.0                                       # viz_mesh.fig_mesh_facets 와 동일한 25 dB 동적범위(색규약 통일)

    fig = plt.figure(figsize=(12, 5.6), constrained_layout=True)
    ax3 = fig.add_subplot(1, 2, 1, projection="3d")
    axp = fig.add_subplot(1, 2, 2, projection="polar")
    fig.suptitle(f"RCS glint — {_NAME[target]} @ {fc/1e9:.1f} GHz", fontsize=15, fontweight="bold")
    # 이 그림엔 컬러바가 없다 → 색 규약은 캡션에 남긴다(GIF 라 bbox_inches 를 못 쓰므로 supxlabel)
    fig.supxlabel(f"Left: SBR facets — bright = strong, gray = back-facing OR occluded by the airframe, "
                  f"arrow = radar LOS ({DR:.0f} dB range) · Right: RCS vs azimuth\n"
                  "Occlusion is decided by Mitsuba rays, exactly as in the RCS integral -- a face that "
                  "faces the radar but sits behind the body contributes nothing.",
                  fontsize=8.5, color="0.45")

    def update(kf):
        azd = az_frames[kf]; u = _look(azd, el)
        proj = nhat @ u
        vis = _visible_faces(_scene, cen, u)                        # 가림 판정(SBR 과 동일)
        lit = (proj > 0) & vis
        contrib = np.where(lit, proj, 0.0)*area
        cdb = 10*np.log10(contrib/(contrib.max()+1e-30) + 1e-30)    # eps 필수(후면 0 → -inf 방지)
        cn = np.clip((cdb + DR)/DR, 0.0, 1.0)
        cols = [cmap(x) if L else (0.75, 0.75, 0.78) for x, L in zip(cn, lit)]
        ax3.clear()
        ax3.add_collection3d(Poly3DCollection(tris0, facecolors=cols, edgecolors=(0, 0, 0, 0.12), linewidths=0.1))
        # LOS 화살표: 카메라를 LOS 와 어긋나게(+18°/+35°) 둬야 화살표가 화면에서 길이를 갖는다
        base = c + u*half*2.4; tip = c + u*half*1.15
        ax3.quiver(base[0], base[1], base[2], *(tip-base), color="#1565c0", lw=2.2, arrow_length_ratio=0.3)
        L = half*1.15                               # 표적이 화면을 꽉 채우도록(기존 1.6 → 드론이 작게 보였음)
        ax3.set_xlim(c[0]-L, c[0]+L); ax3.set_ylim(c[1]-L, c[1]+L); ax3.set_zlim(c[2]-L, c[2]+L)
        try: ax3.set_box_aspect((1, 1, 1))
        except Exception: pass
        ax3.set_axis_off(); ax3.view_init(elev=el + 18, azim=azd + 35)
        # 폴라 RCS
        axp.clear()
        RFLOOR = -45.0            # 코히런트 PO 의 깊은 널(폭 2~3°, −70 dBsm)이 선을 원 중심까지
                                  # 끌고 들어가 '표적 소멸'처럼 보이는 걸 막는다(실제론 대역폭·
                                  # 거칠기·다중경로가 널을 메운다). 정적 폴라 그림과 동일 규약.
        axp.plot(np.radians(az_fine), np.maximum(rcs_db, RFLOOR), color="#c62828", lw=1.3)
        cur = dbsm(sig[np.argmin(np.abs(az_fine - (azd % 360)))])
        axp.plot([np.radians(azd)], [max(cur, RFLOOR)], "o", color="#1565c0", ms=11)
        axp.plot([np.radians(azd), np.radians(azd)], [RFLOOR, max(cur, RFLOOR)],
                 color="#1565c0", lw=1, alpha=0.5)
        axp.set_theta_zero_location("N"); axp.set_theta_direction(-1)
        axp.set_rlim(RFLOOR, None)
        axp.set_title(f"Azimuth {azd:.0f}° → RCS {cur:.1f} dBsm", fontsize=11.5)
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report2_anim_rcs.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=84)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (2) report3 — 회전 프로펠러 + 마이크로도플러 스펙트로그램 커서
# --------------------------------------------------------------------------- #
def anim_microdoppler(outdir=FIG, target="mavic4pro", rpm=None, n_frames=48, fps=12):
    from microdoppler import microdoppler_series, spectrogram
    from drones import rotor_layout
    spec = DRONES[target]
    rpm = rpm if rpm is not None else spec.hover_rpm     # 드론별 hover_rpm
    prf, n_t = 20000.0, 6144
    t, E, info = microdoppler_series(spec, rpm=rpm, prf=prf, n_t=n_t, az=0.0, el=15.0)
    f, tt, Sdb = spectrogram(E, prf, nperseg=64, noverlap=58, nfft=1024)
    # 프로펠러 1개(허브 로컬) 상단투영 폴리곤
    prop = build_propeller(spec, n=12)
    Vp = np.array(prop.v)
    tris = [[Vp[a][:2], Vp[b][:2], Vp[c][:2]] for (a, b, c) in prop.f]  # xy 투영
    R = spec.prop_dia_mm/1000/2
    omega = 2*np.pi*rpm/60.0
    # 왼쪽 패널이 그리는 로터는 #1(=rotor_layout 의 첫 로터). 장착각(base_ang=rotor_deg+12°)과
    # 회전방향(dir=±1)을 그대로 써야 그림의 위상이 microdoppler.py 의 θ(t)=base+dir·ω·t 와 같아진다.
    rot0 = rotor_layout(spec)[0]                  # mavic4pro: base_ang=44°, dir=+1(CCW)
    # 시간축: 전체 307ms 를 48프레임으로 훑으면 프레임 간격(6.5ms)이 플래시 주기(5.45ms)보다 커서
    # 커서가 매번 플래시를 건너뛴다 → **플래시 3주기(≈16.4ms)로 확대**해 커서가 줄무늬 위를 지나가게 한다.
    t0 = float(tt[0]); t1 = t0 + 3.0/info["flash_hz"]
    t_frames = np.linspace(t0, t1, n_frames)      # 0.35 ms/frame ≪ 플래시 주기 5.45 ms
    zs = (tt >= t0 - 1e-3) & (tt <= t1 + 1e-3)    # 확대창 밖은 렌더 낭비(vmin/vmax 고정이라 색은 동일)
    tt_z, Sdb_z = tt[zs], Sdb[:, zs]
    u2 = _look(0, 0)[:2]                          # 레이더 LOS(방위 0) 상단투영
    spin = "CCW" if rot0["dir"] > 0 else "CW"

    fig, (axm, axs) = plt.subplots(1, 2, figsize=(12.5, 5.4), constrained_layout=True)
    # (참고, 코드로 측정한 mavic4pro 값) 지배 플래시 각 81.3°(부피크 94.0°, 상대진폭 0.62), 대각쌍(0·2 / 1·3)이
    # 같은 위상 → 버스트 2갈래(1.1~1.5 / 2.0~2.4 ms), STFT 창 3.2 ms 가 이를 한 줄무늬로 뭉갠다. 본문 설명 참조.
    fig.suptitle(f"How micro-Doppler arises — {_NAME[target]}", fontsize=15, fontweight="bold")

    # ── 하단 캡션 3줄. (fig.text 로 상단에 두면 서브플롯 제목과 겹친다 — constrained_layout 이
    #    fig.text 자리를 잡아 주지 않기 때문. supxlabel 은 레이아웃이 자리를 확보해 준다.)
    #    1행 provenance : 두 헤드라인 숫자(f_tip·flash)가 무엇에 매달려 있는지. hover_rpm 은 DJI 미발표
    #                     → **우리 추정치**이고, f_tip 은 fc 에 선형이므로 반송파를 반드시 적는다.
    #                     (덱 전체에 'GHz' 가 한 번도 안 나오던 문제 — Wi-Fi/LTE/5G 비교와 직결)
    #    2행 로터 정체/위상,  3~4행 **DC(몸체) 제거** + 점선 밖 에너지의 정직한 2분해.
    #    3~4행이 없으면 "저 밝은 건 몸체인가요?" / "왜 tip Doppler 를 넘어가죠?" 를 반드시 맞는다.
    #
    #    ※ 점선 밖 에너지를 "전부 STFT leakage" 라고 하면 **절반은 거짓**이다(창을 64배 늘려 실측):
    #       nperseg 64→2048 (3.2→102 ms) 스윕 결과 —
    #         대역밖 peak : -8.5 dB → -16.6 dB 로 수렴(1833 Hz), 더는 안 내려감 = 분해능 무관
    #         -45 dB 폭  : 2500 Hz → 2029 Hz 로 수렴
    #         @2500 Hz   : -42.6 → -90.2 dB (48 dB 붕괴) = 순수 창 leakage
    #         @2200 Hz   : -27.3 → -56.2 dB (29 dB 붕괴) = 대부분 leakage
    #         @2000 Hz   : -15.4 → -31.2 dB 에서 바닥 = **분해능 무관 → leakage 아님**
    #       (i) 먼 꼬리(≳2.2 kHz)만 창 leakage. (ii) 가까운 어깨(~2.0 kHz)는 **블레이드 플래시**
    #       (서브-ms 진폭 트랜지언트)가 183 Hz 플래시 콤과 컨볼루션돼 생기는 진짜 신호구조 —
    #       단, 그것도 '팁보다 빠른 산란체'는 아니다. (iii) 반박 불가한 상한은 **운동학 천장**:
    #       반지름 r 인 블레이드 점의 |f_d| ≤ 2ωr·cos(el)/λ. 실제 점구름(build_propeller)의
    #       r_max=134.4 mm → 1746 Hz. 모델 안 어떤 것도 이걸 못 넘는다. (점선은 규격 반지름
    #       133.5 mm 의 1734 Hz 그대로 — microdoppler.py 는 건드리지 않는다.)
    # θ·ω 는 NanumGothic 에 글리프가 없어 두부(□)로 깨진다 → mathtext(DejaVu) 로 렌더
    win_ms = 1e3 * 64 / prf                        # nperseg=64 → STFT 창 길이[ms]
    df_stft = prf / 64.0                           # STFT 빈 간격[Hz] (=1/T, 제로패딩 무관). Hann 주엽 반폭 = 2빈(±625Hz)
    # 운동학 천장: 그림이 쓰는 바로 그 점구름에서 최대 반지름을 뽑아 계산(하드코딩 금지)
    r_max = float(np.max(np.hypot(Vp[:, 0], Vp[:, 1])))
    f_ceil = 2.0 * omega * r_max / info["lam"] * np.cos(np.radians(info["el"]))   # 1746 Hz
    fig.supxlabel(f"{rpm:.0f} rpm (assumed — DJI publishes none)  ·  fc {info['fc']/1e9:.1f} GHz (5G n78)  ·  "
                  f"az {info['az']:.0f}° / el {info['el']:.0f}°  ·  monostatic  ·  "
                  f"PRF {prf/1e3:.0f} kHz (ideal)\n"
                  f"Rotor #1 (mount {rot0['base_ang']:.0f}°, {spin}) drawn with the model's own phase "
                  r"$\theta(t)=\theta_0+\mathrm{dir}\cdot\omega t$"
                  f" · diagonal pairs share phase → one stripe every {1e3/info['flash_hz']:.2f} ms\n"
                  f"Static 0-Doppler (body) removed — blade-only residual.  Kinematic ceiling: the mesh "
                  f"reaches r = {r_max*1e3:.0f} mm, so "
                  r"$|f_d|\leq 2\omega r\cos(\mathrm{el})/\lambda$ = "
                  f"{f_ceil:.0f} Hz — nothing in the model is faster.\n"
                  f"Past ~2.2 kHz the wash is Hann-window leakage ({win_ms:.1f} ms window, {df_stft:.0f} Hz "
                  f"bins): it falls 48 dB at 2.5 kHz when the window is lengthened to 102 ms.\n"
                  f"The shoulder out to ~2.0 kHz does not fall: {info['flash_hz']:.0f} Hz blade-flash "
                  f"sidebands (amplitude modulation), not a faster scatterer.",
                  fontsize=8.5, color="0.45")

    # ── 스펙트로그램은 **한 번만** 그린다(예전엔 update 안에서 clear+pcolormesh → 컬러바를 달 수 없었다).
    #    프레임마다 움직이는 건 흰 커서 하나뿐.
    pcm = axs.pcolormesh(tt_z*1e3, f, Sdb_z, cmap="turbo", vmin=-45, vmax=0, shading="gouraud")
    for sgn in (+1, -1):
        axs.axhline(sgn*info["f_tip"], color="k", ls="--", lw=1.2, zorder=4)
    cursor = axs.axvline(t_frames[0]*1e3, color="w", lw=1.6, zorder=5)
    axs.set_xlim(t_frames[0]*1e3, t_frames[-1]*1e3)
    axs.set_ylim(-1.5*info["f_tip"], 1.5*info["f_tip"])
    axs.set_xlabel("Time [ms]"); axs.set_ylabel("Doppler [Hz]")
    axs.set_title(f"Tip Doppler ±{info['f_tip']:.0f} Hz · flash {info['flash_hz']:.0f} Hz", fontsize=11.5)
    cb = fig.colorbar(pcm, ax=axs, pad=0.02)
    cb.set_label("Normalized power [dB]", fontsize=9)
    cb.ax.tick_params(labelsize=8)

    def update(kf):
        tk = t_frames[kf]
        ph = rot0["base_ang"] + rot0["dir"]*np.degrees(omega*tk)     # 물리(microdoppler.py)와 동일한 위상
        cph, sph = np.cos(np.radians(ph)), np.sin(np.radians(ph))
        Rz = np.array([[cph, -sph], [sph, cph]])
        axm.clear()
        for tri in tris:
            poly = (Rz @ np.array(tri).T).T
            axm.add_patch(MplPoly(poly, closed=True, facecolor="0.2", edgecolor="0.35", lw=0.3))
        axm.arrow(0, 0, u2[0]*R*1.3, u2[1]*R*1.3, color="#1565c0", lw=2.5,
                  head_width=R*0.12, length_includes_head=True, zorder=5)
        axm.text(u2[0]*R*1.45, u2[1]*R*1.1, "Radar", color="#1565c0", fontsize=9)
        axm.set_xlim(-R*1.5, R*1.5); axm.set_ylim(-R*1.5, R*1.5); axm.set_aspect("equal")
        axm.set_axis_off(); axm.set_title(f"t={tk*1e3:.2f} ms · blade angle {ph % 360:.0f}°", fontsize=10.5)
        cursor.set_xdata([tk*1e3, tk*1e3])                            # 커서만 이동(컬러바 유지)
        return ()

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report3_anim_microdoppler.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=86)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


# --------------------------------------------------------------------------- #
#  (3) report2 — 점유 G1→G2→G3 그리드 채움 + 거리프로파일
# --------------------------------------------------------------------------- #
def anim_occupancy(outdir=FIG, target="mavic4pro", R=10.0, hold=10, fps=6):
    from waveforms import nr_downlink
    from radar_process import range_profile, mainlobe_width_m
    from viz_occupancy import _grid_image          # 리소스그리드 그리기 단일 출처
    # 그림 제목용 영문 모드 설명(waveforms.MODE_DESC['nr'] 는 한국어라 렌더 텍스트엔 이걸 사용)
    # G1 = 유휴 셀(상시 기준신호는 SSB 뿐) · G2 = 측위 세션이 켜져 PRS 등장(데이터는 없음 → PDSCH-DMRS 없음)
    mode_en = {"G1": "idle cell — SSB only (always-on ref)",
               "G2": "+PRS positioning +control",
               "G3": "+PDSCH data (+DMRS)"}
    modes = ["G1", "G2", "G3"]
    wfs = {m: nr_downlink(occupancy=m) for m in modes}
    sig, _ = drone_rcs_pattern(target, wfs["G3"].carrier_hz, np.array([0.0])); sig = float(sig[0])
    seq = [m for m in modes for _ in range(hold)]

    fig, (axg, axr) = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    # 서사: 분해능을 정하는 건 '점유율'이 아니라 '패시브 수신기가 빌려 쓸 수 있는 기준신호의 대역'.
    # G2 에서 PRS(측위 세션)가 켜지며 대역이 뛰고, G3 는 데이터만 더 찰 뿐 기준은 그대로 PRS.
    fig.suptitle("5G occupancy — idle cell vs positioning session", fontsize=15, fontweight="bold")
    fig.supxlabel("Resolution follows the reference bandwidth: PRS (G2) widens it 7 → 98 MHz; "
                  "G3 adds data only, same reference",
                  fontsize=8.5, color="0.45")

    def update(kf):
        m = seq[kf]; wf = wfs[m]
        axg.clear()
        _grid_image(axg, wf)                       # 그리드 사진은 viz_occupancy 와 동일 로직 재사용
        axg.set_title(f"{m} · {mode_en[m]} · occupancy {wf.occupancy_frac*100:.0f}%", fontsize=10.5)  # 애니메이션용 짧은 제목으로 덮어쓰기
        axr.clear()
        rm, prof, pr, pv = range_profile(wf, R, sig, snr_db=18, passive=True, up=8,
                                         rng=np.random.default_rng(kf))   # up=8: 거리축 보간(실측≈이론)
        pdb = 20*np.log10(prof/prof.max()+1e-12); res = mainlobe_width_m(rm, prof)
        axr.plot(rm, pdb, color="#2e7d32", lw=1.6); axr.axvline(R, color="k", ls="--", lw=1)
        axr.set_xlim(0, 2*R+5); axr.set_ylim(-40, 2)
        axr.set_xlabel("Range [m]"); axr.set_ylabel("Matched filter [dB]")
        # 범례/제목은 '실측 -3dB 폭'과 '이론 c/B(바이스태틱)'를 구분해 표기
        axr.set_title(f"Ref {wf.ref_name} {wf.ref_bw_hz/1e6:.0f}MHz -> theory {wf.range_resolution_m:.1f} m, "
                      f"measured -3dB {res:.1f} m", fontsize=10.5)
        return ()

    anim = FuncAnimation(fig, update, frames=len(seq), blit=False)
    os.makedirs(outdir, exist_ok=True)
    fn = os.path.join(outdir, "report2_anim_occupancy.gif")
    anim.save(fn, writer=PillowWriter(fps=fps), dpi=90)
    plt.close(fig); print("[anim]", os.path.relpath(fn)); return fn


def build_all(outdir=FIG):
    anim_rcs_aspect(outdir)
    anim_microdoppler(outdir)
    anim_occupancy(outdir)
    print("실험 애니메이션 완료 →", os.path.relpath(outdir))


if __name__ == "__main__":
    build_all()
