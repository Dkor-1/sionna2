# -*- coding: utf-8 -*-
"""
tm_envs.py — 표적모형(target-model) 비교를 태울 **환경 축** 확정 + 근거 수치 생산

무엇을 하나
  1) 저장소에 이미 있는 환경 자산(챔버 씬 / 실외 RT 씬 / 바닥유령 / ECA·클러터 / 자유공간)을 전수 확인한다.
  2) 각 환경에서 **표적이 몇 개의 방향(aspect)으로 조명되고 몇 개의 방향으로 산란하는가**를
     Sionna RT 로 직접 잰다 — 이게 "표적모형(각도분해 σ vs 스칼라 σ)이 갈리는가"의 물리적 판별자다.
     ⚠ 표적을 씬에 넣지 않고 **표적 위치에 수신기/송신기를 놓아** 환경이 주는 방향집합만 잰다.
  3) 결과를 outputs/tm_envs.json 으로 떨군다. 손으로 적은 숫자는 없다.

⚠ 이 파일이 만드는 why_sensitive 는 **가설**이다(측정 아님). JSON 에 status="hypothesis" 로 박는다.
⚠ outputs/report13_sigma_grid.json · outputs/rcs_anchor.json 은 07-31 메쉬 개편 이전 산출물이라 낡았다.
   여기서는 **절대 σ 레벨을 인용하지 않는다** — meta 만 읽어 낡음을 기록한다.

실행: SIONNA2_GPU=0 PYTHONPATH=src:benchmark ~/.venvs/py312/bin/python benchmark/tm_envs.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

ROOT = "/workspace/sionna"
OUT = os.path.join(ROOT, "outputs", "tm_envs.json")

sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

from gpu import pick as _pick_gpu            # noqa: E402  ⚠ mitsuba import 전
_pick_gpu(verbose=True)

import mitsuba as mi                          # noqa: E402
import sionna.rt as rt                        # noqa: E402

from bistatic_scene import TX, RX, TGT, bistatic_params   # noqa: E402
import freespace_scene as fss                             # noqa: E402
from render_rt import make_scene                          # noqa: E402
import report14_scene as r14                              # noqa: E402

C0 = 299792458.0
FC = 3.5e9


# --------------------------------------------------------------------------- #
#  공통 — 환경이 표적에게 주는 '방향집합' 측정
# --------------------------------------------------------------------------- #
def _reset_radios(sc):
    for n in list(getattr(sc, "transmitters", {}) or {}):
        sc.remove(n)
    for n in list(getattr(sc, "receivers", {}) or {}):
        sc.remove(n)


def _top_hits(sc, sol, p, k=4):
    """상위 전력 경로가 **어느 물체**를 맞았나 — '바닥이 살아 있다'를 이름으로 못박는다."""
    names = {int(o.object_id): n for n, o in sc.objects.items()}
    O = np.asarray(p.objects)
    if O.size == 0:
        return []
    O = O.reshape(O.shape[0], -1)
    no_obj = int(np.iinfo(O.dtype).max) if np.issubdtype(O.dtype, np.integer) else -1
    order = np.argsort(sol["pw"])[::-1][:k]
    out = []
    for i in order:
        hits = [names.get(int(O[d, i]), None) for d in range(O.shape[0])
                if int(O[d, i]) != no_obj and int(O[d, i]) in names]
        out.append(dict(rel_db=float(10 * np.log10(sol["pw"][i] / sol["pw"].max())),
                        tau_ns=float(sol["tau"][i] * 1e9), objects=hits or ["LOS"]))
    return out


def _solve(sc, a_pos, b_pos, max_depth=3, diffuse=False, spp=1_000_000, want_paths=False):
    """a→b 경로를 푼다. 반환: (지연, 상대전력dB, b 에서의 도래각 θ_r·φ_r, a 에서의 출발각 θ_t·φ_t)."""
    _reset_radios(sc)
    sc.add(rt.Transmitter("probe_tx", position=mi.Point3f(*[float(v) for v in a_pos])))
    sc.add(rt.Receiver("probe_rx", position=mi.Point3f(*[float(v) for v in b_pos])))
    p = rt.PathSolver()(scene=sc, max_depth=int(max_depth), los=True,
                        specular_reflection=True, diffuse_reflection=bool(diffuse),
                        refraction=False, samples_per_src=int(spp), seed=1)
    tau = np.asarray(p.tau).ravel()
    n = tau.shape[0]
    if n == 0:
        return None
    a = np.asarray(p.a)
    amp = (a[0] + 1j * a[1]).reshape(-1, n).sum(axis=0)
    keep = tau >= 0
    tau, amp = tau[keep], amp[keep]
    th_r = np.asarray(p.theta_r).ravel()[keep]
    ph_r = np.asarray(p.phi_r).ravel()[keep]
    th_t = np.asarray(p.theta_t).ravel()[keep]
    ph_t = np.asarray(p.phi_t).ravel()[keep]
    pw = np.abs(amp) ** 2
    sol = dict(tau=tau, pw=pw, theta_r=th_r, phi_r=ph_r, theta_t=th_t, phi_t=ph_t)
    if want_paths:
        sol["top_hits"] = _top_hits(sc, sol, p)
    return sol


def _aspect_stats(sol, dir_key, power_floor_db=-30.0):
    """방향집합 통계. 최강경로 대비 power_floor_db 위 경로만 '유효 조명'으로 센다."""
    if sol is None:
        return dict(n_paths=0, n_significant=0)
    pw, th, ph = sol["pw"], sol[f"theta_{dir_key}"], sol[f"phi_{dir_key}"]
    p0 = pw.max()
    sig = pw >= p0 * 10 ** (power_floor_db / 10.0)
    ths, phs, pws = np.degrees(th[sig]), np.degrees(ph[sig]), pw[sig]
    # 최강경로 방향 대비 각거리(구면) — '표적이 얼마나 다른 자세로 보이는가'
    i0 = int(np.argmax(pws))
    v = np.stack([np.sin(np.radians(ths)) * np.cos(np.radians(phs)),
                  np.sin(np.radians(ths)) * np.sin(np.radians(phs)),
                  np.cos(np.radians(ths))], axis=1)
    cosang = np.clip(v @ v[i0], -1, 1)
    sep = np.degrees(np.arccos(cosang))
    return dict(
        n_paths=int(pw.size), n_significant=int(sig.sum()),
        power_floor_db=float(power_floor_db),
        theta_deg_min=float(ths.min()), theta_deg_max=float(ths.max()),
        phi_deg_min=float(phs.min()), phi_deg_max=float(phs.max()),
        aspect_sep_deg_max=float(sep.max()), aspect_sep_deg_p90=float(np.percentile(sep, 90)),
        aspect_sep_deg_median=float(np.median(sep)),
        secondary_rel_db=(float(10 * np.log10(np.sort(pws)[-2] / p0)) if pws.size > 1 else None),
        dyn_range_db=float(10 * np.log10(pws.max() / pws.min())) if pws.size > 1 else 0.0,
        delay_spread_ns=float((sol["tau"][sig].max() - sol["tau"][sig].min()) * 1e9),
    )


# --------------------------------------------------------------------------- #
#  ENV A — 자유공간 (대조군)
# --------------------------------------------------------------------------- #
def env_freespace():
    """FS-1 자유공간: 환경 산란체가 0개 → 조명 1방향·산란 1방향. 해석적으로 확정된다."""
    tx, rx = (0.0, 0.0, 25.0), (500.0, 0.0, 3.0)
    tgt, vel = (300.0, 200.0, 80.0), (5.0, 0.0, 0.0)
    p = fss.fs_params(tx, rx, tgt, vel, 1.84e9)
    return dict(
        geometry=dict(tx=list(tx), rx=list(rx), tgt=list(tgt), vel=list(vel), fc_hz=1.84e9),
        derived={k: float(v) for k, v in p.items() if np.isscalar(v)},
        illumination_dirs=1, scattering_dirs=1,
        aspect_sep_deg_max=0.0,
        note="환경 산란체 0 — 표적은 이등분선 하나의 자세로만 보인다(해석적, RT 불필요)",
    )


# --------------------------------------------------------------------------- #
#  ENV B — 반무향 챔버(바닥 반사)
# --------------------------------------------------------------------------- #
def env_chamber():
    """챔버(30×20×11, 5면 흡수체 + 반사성 콘크리트 바닥). 표적 위치에서 방향집합을 잰다."""
    sc = make_scene(drone=None, with_chamber=True, cutaway=False, vel=None, fc=FC)
    t0 = time.time()
    ill = _solve(sc, TX, TGT, max_depth=3, diffuse=False, want_paths=True)
    sca = _solve(sc, TGT, RX, max_depth=3, diffuse=False, want_paths=True)
    g = bistatic_params(TX, RX, TGT, (-3.0, 2.0, 0.5), FC)
    # 바닥(z=0) 거울상 기하 — 표적경유 유령이 존재함을 닫힌형으로 확인
    rx_img = np.array(RX, float); rx_img[2] = -rx_img[2]
    tx_img = np.array(TX, float); tx_img[2] = -tx_img[2]
    tgt_a = np.array(TGT, float)
    r2_ghost = float(np.linalg.norm(rx_img - tgt_a))
    rb_ghost = float(np.linalg.norm(tgt_a - np.array(TX, float)) + r2_ghost
                     - np.linalg.norm(np.array(RX, float) - np.array(TX, float)))

    def _el(p):
        u = np.asarray(p, float) - tgt_a
        return float(np.degrees(np.arcsin(u[2] / np.linalg.norm(u))))

    def _sep(p, q):
        a1 = np.asarray(p, float) - tgt_a; a1 /= np.linalg.norm(a1)
        a2 = np.asarray(q, float) - tgt_a; a2 /= np.linalg.norm(a2)
        return float(np.degrees(np.arccos(np.clip(a1 @ a2, -1, 1))))

    floor_aspect = dict(
        el_direct_from_tx_deg=_el(TX), el_floorimage_from_tx_deg=_el(tx_img),
        el_direct_to_rx_deg=_el(RX), el_floorimage_to_rx_deg=_el(rx_img),
        aspect_sep_tx_deg=_sep(TX, tx_img), aspect_sep_rx_deg=_sep(RX, rx_img),
        note=("바닥 거울상 경로는 표적을 **직접경로와 다른 앙각**으로 본다 — "
              "각도분해 σ 만이 두 경로에 다른 σ 를 줄 수 있다(순수 기하, RT 무관)"))
    return dict(
        scene="chamber 30x20x11 semi-anechoic (5-face absorber + concrete floor)",
        tx=list(TX), rx=list(RX), tgt=list(TGT), fc_hz=FC,
        bistatic={k: float(v) for k, v in g.items() if np.isscalar(v)},
        illumination=dict(has_los=_has_los(ill, TX, TGT),
                          top_hits=(ill or {}).get("top_hits", []), **_aspect_stats(ill, "r")),
        scattering=dict(has_los=_has_los(sca, TGT, RX),
                        top_hits=(sca or {}).get("top_hits", []), **_aspect_stats(sca, "t")),
        floor_image_geometry=dict(rb_direct_m=float(g["Rb"]), rb_ghost_m=rb_ghost,
                                  sep_m=rb_ghost - float(g["Rb"]), **floor_aspect),
        rt_seconds=time.time() - t0,
    )


# --------------------------------------------------------------------------- #
#  ENV C — 실외 다중경로(street canyon, 내장 씬)
# --------------------------------------------------------------------------- #
def _has_los(sol, a, b):
    """LOS(직선거리 지연) 경로가 실제로 존재하나 — 가림 판정."""
    if sol is None or sol["tau"].size == 0:
        return None
    los = float(np.linalg.norm(np.asarray(b, float) - np.asarray(a, float))) / C0
    return bool(np.any(np.abs(sol["tau"] - los) < 1e-10))


def env_outdoor(scene_name="street_canyon",
                drone_pos=(0.0, -5.0, 20.0), shadow_pos=(30.0, -15.0, 8.0)):
    """내장 실외 씬. 표적(드론)을 캐니언 위에 두고 조명/산란 방향집합 + 환경 클러터 경로를 잰다.

    ⚠ 위치는 사전 스캔으로 고른 것이다 — drone_pos 는 LOS 有(다중경로 풍부),
      shadow_pos 는 **LOS 차단 + 반사경로만 생존**(가림 케이스). 건물 내부 좌표는 배제했다."""
    sc = r14.load_outdoor_scene(scene_name, fc=FC, diffuse=True)
    tx_pos, rx_pos = [-40.0, 0.0, 10.0], [40.0, 0.0, 3.0]
    t0 = time.time()
    ill = _solve(sc, tx_pos, drone_pos, max_depth=3, diffuse=False)
    sca = _solve(sc, drone_pos, rx_pos, max_depth=3, diffuse=False)
    # 가림 시험 — 건물 그늘 위치에서 LOS 가 끊기고 반사경로만 남는지
    ill_sh = _solve(sc, tx_pos, shadow_pos, max_depth=3, diffuse=False)
    sca_sh = _solve(sc, shadow_pos, rx_pos, max_depth=3, diffuse=False)
    clut = r14.extract_clutter_paths(sc, tx_pos, rx_pos, max_depth=3, diffuse=True,
                                     drop_los=True, top_k=80)
    return dict(
        scene=scene_name, n_objects=int(len(sc.objects)),
        tx=tx_pos, rx=rx_pos, tgt=list(drone_pos), fc_hz=FC,
        illumination=dict(has_los=_has_los(ill, tx_pos, drone_pos), **_aspect_stats(ill, "r")),
        scattering=dict(has_los=_has_los(sca, drone_pos, rx_pos), **_aspect_stats(sca, "t")),
        shadowed_probe=dict(
            pos=list(shadow_pos),
            illumination=dict(has_los=_has_los(ill_sh, tx_pos, shadow_pos),
                              **_aspect_stats(ill_sh, "r")),
            scattering=dict(has_los=_has_los(sca_sh, shadow_pos, rx_pos),
                            **_aspect_stats(sca_sh, "t"))),
        env_clutter=dict(total_paths=int(clut["total_paths"]), kept=int(clut["n_path"]),
                         tau_ns_min=float(clut["tau"].min() * 1e9),
                         tau_ns_max=float(clut["tau"].max() * 1e9),
                         theta_r_deg_min=float(np.degrees(clut["theta_r"]).min()),
                         theta_r_deg_max=float(np.degrees(clut["theta_r"]).max()),
                         power_range_db=float(10 * np.log10(
                             (np.abs(clut["amp"]) ** 2).max() / (np.abs(clut["amp"]) ** 2).min()))),
        rt_seconds=time.time() - t0,
    )


# --------------------------------------------------------------------------- #
#  ENV D — 클러터(cold 도플러퍼짐 + hot) + ECA
# --------------------------------------------------------------------------- #
def env_clutter():
    """기존 산출물에서 클러터 환경의 성질만 읽는다(재실행 없음 — 상대비교에 필요한 구조만)."""
    out = dict(model="statistical cold(C=100, 4 iso-Rb rings, +-1 m/s) + hot clutter, ECA front-end",
               producer=["benchmark/verify_clutter_doppler.py", "benchmark/verify_eca.py"],
               illumination_dirs=1, scattering_dirs=1, aspect_sep_deg_max=0.0,
               note="클러터는 표적의 자세를 바꾸지 않는다 — 표적셀 경쟁전력만 바꾼다")
    for tag, f in (("clutter_doppler", "outputs/verify_clutter_doppler.json"),
                   ("eca", "outputs/verify_eca.json")):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            d = json.load(open(p))
            out[tag] = dict(exists=True, sections=list(d.keys()),
                            mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                time.localtime(os.path.getmtime(p))))
        else:
            out[tag] = dict(exists=False)
    return out


# --------------------------------------------------------------------------- #
#  자산 전수조사 + 낡음 표기
# --------------------------------------------------------------------------- #
def _stat(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return dict(path=rel, exists=False)
    return dict(path=rel, exists=True, bytes=os.path.getsize(p),
                mtime=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(p))))


def inventory():
    scripts = ["src/chamber.py", "src/scene_build.py", "src/render_rt.py", "src/radar_scene.py",
               "src/bistatic_scene.py", "src/monostatic_scene.py",
               "src/freespace_scene.py", "src/freespace_link.py", "src/freespace_detect.py",
               "src/experiment_freespace_sigma.py", "src/experiment_freespace_range.py",
               "src/experiment_ghost.py", "src/experiment_detection.py",
               "src/report14_scene.py", "src/report14_stap.py", "src/passive_process.py",
               "benchmark/rt_experiments.py", "benchmark/verify_floor_ghost.py",
               "benchmark/verify_eca.py", "benchmark/verify_clutter_doppler.py",
               "benchmark/verify_freespace.py", "benchmark/geometry_grid.py",
               "benchmark/geometry_benchmark.py", "benchmark/rcs_anchor.py"]
    docs = ["docs/GEOMETRY_BENCHMARK.md", "docs/REPORT14_SPEC.md", "docs/REPORT13_SPEC.md",
            "docs/VERIFY_CLUTTER.md", "docs/RESUME.md", "docs/RETRACTION_LOG.md"]
    outs = ["outputs/geometry_benchmark.json", "outputs/geometry_grid.json",
            "outputs/floor_ghost_verify.json", "outputs/report3_rt.json",
            "outputs/rt_env_clutter.json", "outputs/verify_eca.json",
            "outputs/verify_clutter_doppler.json", "outputs/detection_ghost.json",
            "outputs/report13_freespace.json", "outputs/report13_sigma_grid.json",
            "outputs/rcs_anchor.json", "outputs/verify_ghost_impact.json",
            "outputs/mono_link.json", "outputs/verify_freespace.json"]
    return dict(scripts=[_stat(s) for s in scripts],
                docs=[_stat(s) for s in docs],
                outputs=[_stat(s) for s in outs])


def staleness():
    """07-31 메쉬 개편 대비 낡음 — 어느 표적모형 분기가 영향을 받나."""
    mesh = [_stat("src/drones.py"), _stat("src/drone_cad.py")]
    sig = _stat("outputs/report13_sigma_grid.json")
    anc = _stat("outputs/rcs_anchor.json")
    meta = {}
    p = os.path.join(ROOT, "outputs/report13_sigma_grid.json")
    if os.path.exists(p):
        meta = json.load(open(p)).get("meta", {})
        meta = {k: meta[k] for k in ("generated", "git_rev", "engine", "div", "backend")
                if k in meta}
    return dict(
        mesh_sources=mesh, sigma_grid=sig, rcs_anchor=anc, sigma_grid_meta=meta,
        verdict=("sigma_grid/rcs_anchor 는 메쉬 소스(drones.py·drone_cad.py)보다 낡았다 — "
                 "절대 σ 레벨 인용 금지"),
        affected_branch="branch_C_ours_sbr_po_angle_resolved",
        unaffected_branches=["branch_A_isotropic_point_scalar_sigma",
                             "branch_B_stock_sionna_rt_mesh"],
        why=("A 는 스칼라 상수 σ, B 는 Sionna 재질·메쉬가 직접 경로를 만들며 우리 σ 격자를 읽지 않는다. "
             "C 만 report13_sigma_grid.json 을 조회한다 → 낡음은 3분기 중 C 한 곳에만 들어간다. "
             "3분기 상대비교의 '순위'는 C 의 절대레벨이 아니라 C 의 각도구조에 달려 있고, "
             "각도구조도 07-31 메쉬 변경(동체 셸·암 단면)에 영향을 받으므로 "
             "⭐ C 분기 결론은 rcs_anchor 재생성 후 반드시 재확인한다."))


def git_rev():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return None


# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    print("[1/5] 자산 전수조사...", flush=True)
    inv = inventory()
    stale = staleness()

    print("[2/5] ENV A 자유공간(대조군)...", flush=True)
    a = env_freespace()

    print("[3/5] ENV B 챔버 RT 방향집합...", flush=True)
    b = env_chamber()

    print("[4/5] ENV C 실외 street canyon RT 방향집합...", flush=True)
    c = env_outdoor()

    print("[5/5] ENV D 클러터...", flush=True)
    d = env_clutter()

    envs = [
        dict(id="E0_freespace", name="자유공간 (대조군)",
             physics="none — 환경 산란체 0",
             script="PYTHONPATH=src:benchmark python src/experiment_freespace_range.py",
             support_scripts=["src/freespace_scene.py", "src/freespace_link.py",
                              "src/freespace_detect.py", "src/experiment_freespace_sigma.py"],
             runnable="yes (CPU, 새 씬 제작 0)", measured=a,
             why_sensitive=(
                 "[가설] 표적은 이등분선 **한 방향**으로만 조명되고 한 방향으로만 산란한다"
                 "(측정 aspect_sep_deg_max=0). 그래서 세 표적모형의 차이는 그 한 자세의 σ 값 차이로 "
                 "**환원**된다 — 각도구조(널·로브)는 φ·el 을 스윕할 때만 드러나고, 한 점에서는 "
                 "스칼라 σ 로도 같은 검출확률을 낸다. ⇒ 여기서 세 분기가 갈리면 그것은 환경 탓이 아니라 "
                 "σ **레벨** 차이다 — 다른 환경의 낙차를 재는 **영점**이 된다."),
             hypothesis_falsifier=(
                 "φ·el 스윕 위에서 세 분기의 Pd 곡선이 상수 dB 오프셋만큼 차이나면 가설 지지. "
                 "오프셋이 각도에 따라 바뀌면(교차가 생기면) 가설 반증 — 자유공간에서도 각도구조가 산다.")),
        dict(id="E1_chamber_floor", name="반무향 챔버 — 반사 바닥(표적경유 유령)",
             physics="바닥반사 — 표적을 경유한 2차 경로가 거울상 자세로 표적을 다시 본다",
             script="PYTHONPATH=src:benchmark python benchmark/rt_experiments.py --quick --only depth,floor,ghost",
             support_scripts=["src/render_rt.py::make_scene", "src/chamber.py",
                              "benchmark/verify_floor_ghost.py", "src/experiment_ghost.py"],
             runnable="yes (GPU, 챔버 씬·메쉬 존재, depth 스윕 실측 5.7 s)", measured=b,
             why_sensitive=(
                 "[가설] 바닥 거울상 경로는 표적을 **직접경로와 다른 앙각**으로 때린다 — 측정된 순수 기하가 "
                 "그것을 확정한다(floor_image_geometry: 직접 조명은 표적 **위**에서, 바닥경유 조명은 표적 "
                 "**아래**에서 온다 — el 부호가 뒤집힌다). 즉 직접경로는 드론의 등/옆구리를, 유령경로는 "
                 "**배(belly)** 를 본다. 각도분해 σ 를 가진 분기(C)만 두 경로에 **서로 다른 σ** 를 줄 수 있고, "
                 "스칼라 σ 분기(A)는 유령/직접 비를 순수 기하·프레넬로만 낸다. 드론은 등과 배의 σ 가 크게 "
                 "다른 납작한 물체이므로 유령 세기 예측이 분기마다 갈릴 것이다. 스톡 Sionna 분기(B)는 "
                 "few-λ 드론에서 산란적분이 없어 유령 경로 자체를 **만들지 못하거나** 재질 S 노브에만 "
                 "반응할 것이다(report3 [C][D][E] 가 이미 그 방향을 가리킨다). "
                 "⭐ 측정된 사다리에서 챔버는 **각거리 축의 1위**다 — 닫힌 상자라 사방에서 되돌아온다. "
                 "다만 그 경로들은 흡수체를 거쳐 약하다(illumination.secondary_rel_db) — "
                 "각거리는 크고 전력은 작다는 조합이라, 이 칸은 '자세차가 커도 약하면 안 갈리는가'를 묻는다."),
             hypothesis_falsifier=(
                 "유령/직접 전력비를 세 분기로 예측해 비교한다. A 와 C 의 비가 1 dB 안이면 가설 반증 — "
                 "각도분해가 바닥반사에서 값을 못 낸다. B 가 유령 경로를 아예 못 만들면 그것은 "
                 "'표적모형이 환경을 못 태운다'는 별개의 결과로 기록한다.")),
        dict(id="E2_outdoor_canyon", name="실외 street canyon — 다중경로 + 가림",
             physics="다중경로 + 가림/그림자 — 여러 벽 반사가 표적을 여러 자세로 조명, 건물이 LOS 를 끊는다",
             script="PYTHONPATH=src:benchmark python src/report14_scene.py",
             support_scripts=["src/report14_scene.py", "src/report14_stap.py",
                              "docs/REPORT14_SPEC.md"],
             runnable="yes (GPU, 내장 씬 로컬 존재 — 다운로드·제작 불필요, 스모크 통과)", measured=c,
             why_sensitive=(
                 "[가설] 여기서 표적모형 차이가 **가장 크게** 벌어진다. 이유 둘: "
                 "(1) 조명 경로가 여러 개이고 그중 2번째가 LOS 와 **거의 맞먹는 전력**이다"
                 "(illumination.secondary_rel_db — 흡수체가 없으므로 챔버보다 훨씬 세다). "
                 "각도분해 σ 는 경로마다 다른 값을 주고 스칼라 σ 는 전부 같은 값을 주므로, "
                 "비슷한 세기의 경로들이 코히어런트하게 합쳐질 때 이 차이가 **진폭과 위상 둘 다** 바꾼다. "
                 "(2) 가림(shadowed_probe: has_los=false)이 생기면 살아남는 조명이 전부 벽 반사이고 "
                 "그 자세는 LOS 자세에서 최대 aspect_sep_deg_max 만큼 떨어져 있다 — 평균 σ 만 가진 모형은 "
                 "**계통 편향**을 내고, 그 편향은 자세에 따라 부호가 바뀔 수 있다. "
                 "⇒ '가림이 있으면 형상이 중요해진다' 를 정면으로 시험하는 칸이다. "
                 "⚠ 측정된 사다리에서 실외 LOS 칸은 각거리 축에서는 챔버에 진다 — 이 가설이 참이려면 "
                 "**각거리가 아니라 상대전력**이 지배변수여야 한다. 그 자체가 시험 대상이다."),
             hypothesis_falsifier=(
                 "그늘 위치(shadowed_probe)와 LOS 위치에서 세 분기의 SCNR/Pd 를 잰다. "
                 "그늘에서 분기 간 격차가 LOS 격차보다 크지 않으면 가설 반증. "
                 "또 실외 LOS 칸의 분기 간 격차가 챔버보다 작으면 '각거리가 지배변수' 쪽으로 반증된다. "
                 "⚠ 표적을 씬에 넣지 않고 경로만 재는 지금 방식은 **환경이 주는 방향집합**만 증명한다 — "
                 "실제 σ 결합은 3분기 실행에서 나온다.")),
        dict(id="E3_clutter_eca", name="클러터 — cold(도플러퍼짐) + hot, ECA 전단",
             physics="클러터 — 표적이 아닌 산란체가 같은 거리·도플러 셀에서 경쟁한다",
             script="E3_N_C2=30 E3_N_C3=30 E3_N_C4=30 PYTHONPATH=src:benchmark python benchmark/verify_clutter_doppler.py",
             support_scripts=["benchmark/verify_eca.py", "src/passive_process.py"],
             runnable="yes (CPU, N 을 환경변수로 줄일 수 있음)", measured=d,
             why_sensitive=(
                 "[가설] 여기서 표적모형 차이가 **가장 작다**. 클러터는 표적의 자세를 바꾸지 않고 "
                 "(측정 aspect_sep_deg_max=0) 표적셀의 경쟁전력만 올린다. 그러면 세 분기는 "
                 "**표적 에코의 평균 전력** 하나로만 갈리고, SCNR 은 그 평균에 선형이다 — "
                 "각도구조는 SCNR 에 들어갈 통로가 없다. ⇒ 이 칸이 참이면 '환경이 리치해도 클러터형이면 "
                 "평균 σ 만 있으면 된다' 가 되고, E1·E2 와 대비되어 **어떤 물리가 형상을 부르는지**를 가른다. "
                 "⚠ 단 하나의 통로가 남아 있다 — 저속 드론은 클러터 도플러대에 묻히고(C4), 각도분해 σ 가 "
                 "표적 자세변화에 따른 **에코 변조**를 만들면 그 변조가 도플러축에 실릴 수 있다. "
                 "이 통로는 CPI 안에서 자세가 바뀌는 경우에만 열린다."),
             hypothesis_falsifier=(
                 "세 분기의 SCNR 차이가 평균 σ 차이(dB)와 1:1 로 맞으면 가설 지지. "
                 "SCNR 차이가 평균 σ 차이보다 크면 반증 — 각도구조가 클러터 환경에도 통로를 갖는다.")),
    ]

    # 파생 — 환경을 '표적이 몇 개의 자세로 보이는가' 로 줄세운다(가설의 예측변수)
    #        ⭐ 두 축을 **따로** 센다: 각거리(얼마나 다른 자세인가)와 상대전력(그 자세가 얼마나 센가).
    #           둘이 서로 다른 순서를 내므로 하나로 합치지 않는다.
    def _row(rid, v, extra=None):
        if isinstance(v, dict) and "n_significant" in v:
            r = dict(id=rid, n_significant_illumination_dirs=int(v["n_significant"]),
                     aspect_sep_deg_max=float(v.get("aspect_sep_deg_max", 0.0)),
                     secondary_rel_db=v.get("secondary_rel_db"),
                     has_los=v.get("has_los"))
        else:
            r = dict(id=rid, n_significant_illumination_dirs=1, aspect_sep_deg_max=0.0,
                     secondary_rel_db=None, has_los=True)
        if extra:
            r.update(extra)
        return r

    ladder = []
    for e in envs:
        m = e["measured"]
        ladder.append(_row(e["id"], m.get("illumination", m)))
        if e["id"] == "E2_outdoor_canyon":
            sh = m["shadowed_probe"]
            ladder.append(_row("E2b_outdoor_shadowed", sh["illumination"],
                               dict(note="같은 씬·같은 TX, 건물 그늘 위치 — LOS 차단")))
    by_angle = sorted(ladder, key=lambda r: -r["aspect_sep_deg_max"])
    by_power = sorted(ladder, key=lambda r: -(r["secondary_rel_db"]
                                              if r["secondary_rel_db"] is not None else -999.0))

    res = dict(
        meta=dict(
            title="표적모형 비교를 태울 환경 축 확정",
            generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            producer="benchmark/tm_envs.py",
            git_rev=git_rev(),
            python=sys.version.split()[0],
            gpu_policy="GPU2 는 benchmark/rcs_anchor.py 재생성 중 — 건드리지 않음. 이 실행은 GPU 0.",
            elapsed_s=None,
        ),
        target_model_branches=[
            dict(id="branch_A_isotropic_point_scalar_sigma",
                 what="등방 점표적 — 스칼라 상수 σ 주입 (mainstream h = h_bg + h_target)",
                 uses_stale_sigma=False,
                 where="src/freespace_link.echo_power_w · src/passive_process.make_cpi 의 a_tgt"),
            dict(id="branch_B_stock_sionna_rt_mesh",
                 what="스톡 Sionna RT — 드론 메쉬를 씬에 넣고 PathSolver 가 직접 경로를 만든다(산란적분 없음)",
                 uses_stale_sigma=False,
                 where="src/render_rt.make_scene(drone=...) + benchmark/rt_experiments.py"),
            dict(id="branch_C_ours_sbr_po_angle_resolved",
                 what="우리 SBR+PO 각도분해 σ(az, el, band) 격자 조회",
                 uses_stale_sigma=True,
                 where="outputs/report13_sigma_grid.json (via src/experiment_freespace_sigma.py)"),
        ],
        staleness=stale,
        inventory=inv,
        envs=envs,
        aspect_diversity_ladder=dict(
            rows=ladder,
            ranked_by_angular_spread=[r["id"] for r in by_angle],
            ranked_by_secondary_power=[r["id"] for r in by_power],
            what=("환경이 표적에게 주는 **유효 조명방향 수**·최강경로 대비 **각거리 최대값**·"
                  "**2번째 경로의 상대전력**. 이 셋이 표적모형 민감도의 예측변수다."),
            reading=("⭐ 두 축의 순서가 **다르다** — 챔버는 각거리에서 이기고(닫힌 상자라 사방에서 "
                     "되돌아온다) 실외는 2번째 경로의 상대전력에서 이긴다(흡수체가 없다). "
                     "가림 케이스(E2b)는 LOS 자체가 없어 조명 전부가 비-LOS 자세로 들어온다 — "
                     "두 축 모두에서 극단이다."),
            status="measured (환경 구조만) — 표적모형 간 낙차는 아직 측정하지 않았다"),
        control="E0_freespace",
        runnable_now=True,
        caveats=[
            "⚠ why_sensitive 는 전부 **가설**이다 — 측정 결과가 아니다. 각 항에 hypothesis_falsifier 를 붙였다.",
            "⚠ outputs/report13_sigma_grid.json · outputs/rcs_anchor.json 은 07-31 메쉬 개편 이전 산출물이다. "
            "절대 σ 레벨을 인용하지 않는다. 이 낡음은 3분기 중 branch_C 하나에만 들어간다(staleness.why 참조).",
            "⚠ 이 파일의 measured 블록은 **환경이 표적에게 주는 방향집합·경로구조**만 잰 것이다. "
            "표적모형별 σ 결합·검출 결과는 아직 재지 않았다.",
            "⚠ 새 씬은 하나도 만들지 않았다 — 챔버 메쉬·Sionna 내장 실외 씬·자유공간 순수함수·"
            "통계 클러터 모델 전부 저장소에 이미 있는 것이다.",
        ],
    )
    res["meta"]["elapsed_s"] = time.time() - t0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, default=float)
    print(f"→ {OUT}  ({res['meta']['elapsed_s']:.1f}s)")


if __name__ == "__main__":
    main()
