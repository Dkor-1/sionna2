# -*- coding: utf-8 -*-
"""
das_fleet_sigma.py — ⭐ Das 함대 σ(f, θb) 계산기 (모노 + 바이스태틱 7 각도)
==========================================================================
무엇을 하나
  `outputs/das_fleet_spec.json` 이 확정한 기하·격자·규약 그대로 우리 SBR+PO 커널을 돌려
  σ(θb, f, φ) 를 낸다. 대조·통계·적합은 여기서 하지 않는다 — 그건 `das_fleet_ours.py` 다.
  이 파일은 **원시 σ 만** 만들고 중간 저장을 남긴다.

■ 기하 (das_fleet_spec.json :: theta_b_definition 축자 구현)
    θb 는 TX–표적–RX **낀각**이다 (이등분선 기준이 아니다. 반각도 아니다).
    회전대가 도는 것은 표적이고 TX 는 고정이므로, 표적 좌표계에서 보면
        입사 방위 = φ,   산란 방위 = φ + θb,   고도 el = 0 (Fig.1 은 평면도)
    이고 φ 를 그 기체의 Table I 방위격자대로 훑는다.
    ⛔ 이등분선 고정(bisector-fixed)으로 TX·RX 를 대칭으로 벌리면 **다른 실험**이다 — 금지.
    û_i = 표적→TX, û_s = 표적→RX (둘 다 outward). rcs_sbr 규약과 같다.

■ 왜 rcs_sbr_multistatic 인가
    조명(광선추적)은 û_i 로만 결정되므로 **한 φ 에서 한 번만 쏘고** 7 개 û_s 에 대해 위상합과
    출사 그림자광선만 반복한다. 7 각도가 1 각도의 몇 배가 아니라 조금 더 비쌀 뿐이다.

■ 규약 고정 (outputs/das_fleet_prereg.json :: execution_contract — 계산 전에 봉인된 값)
    div=16 (격자 λ/16) · jitter=2 · max_bounce=1 · penetrate=True · exit_vis=True ·
    symmetrize=False · ptd=False.
    ⚠ 이 값들을 여기서 바꾸면 통제군(phantom3, outputs/p3_ours.json)과 설정이 달라져
      함대 대조가 무효가 된다. 진단으로 흔들어 보려면 --mode recip / --mode exitvis 를 쓴다
      (헤드라인과 **다른 파일**에 쓴다).

■ exit_vis (출사 가시성) — 명시
    수신 게이트가 법선 판정 (n̂·û_s>0) 하나뿐이면 수신기를 향한 면이 기체에 가려져 있어도
    100% 로 계상된다. 그래서 히트점마다 û_s 로 그림자광선을 1 발 더 쏴 실제로 뚫려 있는 면만
    남긴다(rcs_sbr._exit_visible). **θb=0 에서는 no-op** 이다(first-hit 이 이미 그 가림을 뺐다).
    즉 이 항은 바이스태틱 열에서만 실제로 면을 깎는다 — 모노 열은 손대지 않으므로 θb=0 대조는
    이 선택에 영향받지 않는다.

■ symmetrize — **끈다**. 근거는 파일 하단 `WHY_NO_SYMMETRIZE` 참조.

■ 중간 저장 (세션이 끊겨도 이어간다)
    outputs/partial/das_fleet_0803/{airframe}/f{idx:04d}_s{stage}.json
    한 파일 = 한 주파수에서 **그 단계에 새로 계산된 방위각들**의 σ. 단계가 올라갈수록 방위가
    촘촘해지고, 이미 계산한 방위는 다시 계산하지 않는다(합집합이 곧 현재 해상도).
    파일이 이미 있으면 건너뛴다 → 죽었다 다시 띄우면 이어서 간다.

실행 예:
    PYTHONPATH=src:benchmark SIONNA2_GPU=2 ~/.venvs/py312/bin/python \
        benchmark/das_fleet_sigma.py --airframe mini2 --stage 2 --shard 0 --nshard 8
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "benchmark")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                                    # noqa: E402
from gpu import pick                                                  # noqa: E402

pick()                                                                # ⚠ mitsuba import 전에

from rcs_sbr import rcs_sbr_multistatic, _look                        # noqa: E402
from drones import DRONES, build_drone, DRONE_GROUP_MAT               # noqa: E402

C0 = 299792458.0
PARTIAL = os.path.join(ROOT, "outputs", "partial", "das_fleet_0803")

#  Das Table III 의 바이스태틱 열 — 0:15:90 (§II-1 축자).
THETA_B = [0, 15, 30, 45, 60, 75, 90]

#  ⭐ 커널 설정 — 사전등록(execution_contract)이 봉인한 값. 여기서 바꾸지 않는다.
DIV = 16
JITTER = 2
PENETRATE = True
EXIT_VIS = True
SYMMETRIZE = False

WHY_NO_SYMMETRIZE = (
    "symmetrize=False. 근거 셋. (1) **통제군 정합** — 함대 대조의 기준점인 phantom3 "
    "(outputs/p3_ours.json) 이 symmetrize 없이 계산됐다. 여기서만 켜면 네 기체를 한 자로 잰다는 "
    "전제가 깨진다. (2) **정보가 늘지 않는다** — σ_sym=√(σ(i,s)σ(s,i)) 는 두 평가값의 기하평균일 "
    "뿐이고 어느 쪽이 참인지에 대한 정보는 없다. 두 오차가 dB 에서 같은 방향이면 전혀 개선되지 "
    "않는다(rcs_sbr.rcs_sbr_multistatic docstring 의 정직 표기). (3) **비용** — 수신방향마다 "
    "조명추적을 한 번 더 하므로 7 각도에서 약 8 배다. 대신 상반성 위반량 자체를 --mode recip 로 "
    "**측정해서** 바이스태틱 열의 불확도로 병기한다 — 감추는 대신 재는 쪽을 골랐다."
)

#  기체별 격자 — das_fleet_spec.json :: conditions_by_airframe / comparison_plan 그대로.
GRIDS = {
    "mini2": dict(
        mesh_key="mini2", band_ghz=(21.0, 27.0),
        f_ghz=np.linspace(21.0, 27.0, 41),          # Δ=0.15 GHz, 41 점
        az_n=720,                                   # Table I: 0 ≤ φ(=0.5°) ≤ 360
        az_note="0:0.5:360 (720 unique) — Das Table I 격자 그대로",
        f_note=("Das Table I 은 21–27 GHz 501 점(12 MHz)이다. 우리는 같은 **창**에 41 점 "
                "(Δ=0.15 GHz)을 둔다 — 적합 대상이 μ=a·f+b 라 표본밀도가 아니라 창과 균등성이 "
                "기울기를 정하고, phantom3 라운드의 21 점이 SE 0.066 dB/GHz 였으므로 41 점이면 "
                "6 GHz 창에서도 SE 가 0.1 dB/GHz 아래로 내려간다."),
        proxy_mesh=False),
    "m350rtk": dict(
        mesh_key="m350rtk", band_ghz=(21.0, 27.0),
        f_ghz=np.linspace(21.0, 27.0, 41),
        az_n=720,
        az_note="0:0.5:360 (720 unique) — Das Table I 격자 그대로",
        f_note="mini2 와 동일",
        proxy_mesh=False),
    "phantom2": dict(
        mesh_key="phantom3", band_ghz=(11.0, 26.0),
        #  ⭐ Das 의 μ 적합 정의역은 원시 2001 점이 아니라 **200 MHz 서브밴드 중심 150 점**
        #    (f_i = 11 + 0.1i, i=0..149) 이다(§II-3c). 그 격자에서 5 칸씩 뽑아 30 점을 쓴다.
        f_ghz=11.0 + 0.1 * np.arange(0, 150, 5),
        az_n=360,
        az_note="0:1:360 (360 unique) — Das Table I 격자 그대로",
        f_note="Das 서브밴드 중심 격자(11+0.1i)의 stride-5 부분표집 30 점 = 11.0~25.5 GHz",
        proxy_mesh=True),
}

#  단계별 (주파수 stride, 방위 stride). 격자가 촘촘해질수록 앞 단계 표본이 **부분집합으로
#  재사용**된다 — 어느 단계에서 멈춰도 그때까지가 완결형이고 버리는 계산이 없다.
STAGES = {0: (8, 8), 1: (4, 4), 2: (2, 2), 3: (1, 1),
          6: (1, 8)}          # ⭐ 41 주파수 x 90 방위 — 아래 LADDER 주석 참조

#  ⭐ 기체별 **사다리 순서**. m350rtk 만 다르다.
#    m350rtk 는 한 표본이 mini2 의 ~16 배(반경 0.72 m vs 0.18 m → 광선 n² 이 그만큼)라
#    같은 벽시계로 살 수 있는 표본이 적다. 그 예산을 **방위보다 주파수에** 쓴다:
#      · 대조에 쓰는 헤드라인은 μ(f) 직선적합의 f_c 값과 기울기 a 다. 둘 다 **주파수 표본수**가
#        정밀도를 지배한다 — 방위평균의 표본오차(≈ε/√N_az)는 적합에서 √N_f 로 한 번 더 줄지만
#        주파수 표본이 적으면 끝점 레버리지가 기울기를 끌어간다(phantom3 21 점 라운드의 교훈).
#      · 그래서 6→(1,8) 을 2 단계(21f x 360az) **앞에** 끼워 41 주파수를 90 방위로 먼저 채운다.
#        N_az=90 에서 dB 영역 방위평균의 SE ≈ ε/√90 ≈ 0.73 dB 이고, 41 주파수 적합을 거치면
#        μ(f_c) 의 SE 는 ≈0.11 dB 로 내려간다. 방위 밀도를 먼저 올리는 것보다 이쪽이 싸다.
#      · ⚠ 대신 **주파수당** ε 와 σ(φ) 로브 구조는 성기다. Das Table I 격자(0:0.5:360)와의
#        차이는 산출물 caveat 에 그대로 적는다.
LADDER = {"mini2": [0, 1, 2, 3], "phantom2": [0, 1, 2, 3], "m350rtk": [0, 1, 6, 2, 3]}

_MESH: dict = {}


def mesh_for(af: str):
    mk = GRIDS[af]["mesh_key"]
    if mk not in _MESH:
        _MESH[mk] = build_drone(DRONES[mk])
    return _MESH[mk]


def group_mat() -> dict:
    """재질 규약 — rcs_anchor.raw_sigma_az / p3_ours 와 **같은 출처·같은 사전**."""
    return {g: m for g, (m, _) in DRONE_GROUP_MAT.items()}


def az_full(af: str) -> np.ndarray:
    n = GRIDS[af]["az_n"]
    return np.linspace(0.0, 360.0, n, endpoint=False)


def stage_sets(af: str, stage: int):
    """(이 단계의 주파수 인덱스, 이 단계의 방위 인덱스, {주파수 인덱스: 앞 단계들이 이미 덮은 방위}).

    '앞 단계' 는 그 기체 LADDER 에서 이 단계보다 **먼저 오는 모든 단계**의 합집합이다
    (직전 하나가 아니다 — m350rtk 처럼 사다리가 중첩이 아닌 순서를 쓰면 직전만 봐서는 틀린다)."""
    fs, azs = STAGES[stage]
    nf = len(GRIDS[af]["f_ghz"])
    na = GRIDS[af]["az_n"]
    fi = np.arange(0, nf, fs)
    ai = np.arange(0, na, azs)
    lad = LADDER[af]
    prev: dict = {}
    for t in lad[:lad.index(stage)]:
        tfs, tazs = STAGES[t]
        ta = set(np.arange(0, na, tazs).tolist())
        for k in np.arange(0, nf, tfs):
            prev.setdefault(int(k), set()).update(ta)
    return fi, ai, prev


#  한 작업 단위의 방위 표본 수. 작게 잡을수록 (a) 병렬도가 올라가고 (b) 세션이 끊겼을 때
#  잃는 계산이 줄고 (c) 파일이 늘어난다. 30 은 m350rtk 최악(≈33 s/표본)에서 한 작업 ≈ 17 분이다.
CHUNK = 30


def todo_for(af: str, stage: int):
    """[(f_idx, chunk_id, 새로 계산할 방위 인덱스)] — 이미 파일이 있는 작업은 뺀다.

    '새로' = 그 주파수가 직전 단계에도 있었다면 직전 단계 방위집합을 뺀 차집합, 처음 나온
    주파수라면 이 단계 방위집합 전부. 낮은 단계의 표본은 **부분집합이라 재사용**된다."""
    fi, ai, prev = stage_sets(af, stage)
    out = []
    for k in fi:
        done = prev.get(int(k))
        new = np.array(sorted(set(ai.tolist()) - done)) if done else ai
        if new.size == 0:
            continue
        for c, s in enumerate(range(0, new.size, CHUNK)):
            if os.path.exists(part_path(af, int(k), stage, c)):
                continue
            out.append((int(k), c, new[s:s + CHUNK]))
    return out


def part_path(af: str, f_idx: int, stage: int, chunk: int) -> str:
    return os.path.join(PARTIAL, af, f"f{f_idx:04d}_s{stage}_c{chunk:02d}.json")


def compute_one(af: str, f_idx: int, az_idx: np.ndarray, stage: int) -> dict:
    """한 주파수에서 주어진 방위각들의 σ(θb) 를 낸다 → 부분 저장 dict."""
    G = GRIDS[af]
    fghz = float(G["f_ghz"][f_idx])
    fc = fghz * 1e9
    lam = C0 / fc
    mesh, gm = mesh_for(af), group_mat()
    AZ = az_full(af)[az_idx]
    ck = (G["mesh_key"], round(fc / 1e6), "dasfleet")

    sig = np.empty((AZ.size, len(THETA_B)))
    t0 = time.time()
    for j, phi in enumerate(AZ):
        u_i = _look(phi, 0.0)
        U_s = [_look(phi + tb, 0.0) for tb in THETA_B]
        sig[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
            mesh, gm, fc, u_i, U_s, spacing=lam / DIV, cache_key=ck,
            penetrate=PENETRATE, jitter=JITTER, exit_vis=EXIT_VIS,
            symmetrize=SYMMETRIZE), float))
    dt = time.time() - t0
    return dict(airframe=af, mesh_key=G["mesh_key"], proxy_mesh=bool(G["proxy_mesh"]),
                f_idx=f_idx, f_ghz=fghz, stage=stage, theta_b=THETA_B,
                az_idx=az_idx.tolist(), az_deg=AZ.tolist(),
                sigma_lin_m2=sig.tolist(),
                kernel=dict(div=DIV, jitter=JITTER, penetrate=PENETRATE,
                            exit_vis=EXIT_VIS, symmetrize=SYMMETRIZE, ptd=False,
                            max_bounce=1, spacing="lambda/16"),
                geometry="incident az=phi, scattered az=phi+theta_b, el=0 (target frame)",
                runtime_s=round(dt, 2), n_az=int(AZ.size),
                gpu=os.environ.get("CUDA_VISIBLE_DEVICES", "?"),
                generated=time.strftime("%Y-%m-%d %H:%M:%S"))


def save(d: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp{os.getpid()}"
    with open(tmp, "w") as fh:
        json.dump(d, fh)
    os.replace(tmp, path)                     # 원자적 — 중간에 죽어도 반쪽 파일이 안 남는다


# --------------------------------------------------------------------------- #
#  진단 모드 1 — 상반성 위반 (symmetrize 를 안 켠 대가를 **재서** 남긴다)
# --------------------------------------------------------------------------- #
def run_recip(af: str, n_az: int, f_list, shard: int, nshard: int):
    G = GRIDS[af]
    mesh, gm = mesh_for(af), group_mat()
    AZ = np.linspace(0.0, 360.0, n_az, endpoint=False)
    for fi, fghz in enumerate(f_list):
        if fi % nshard != shard:
            continue
        p = os.path.join(PARTIAL, af, f"recip_f{fghz:.3f}.json")
        if os.path.exists(p):
            continue
        fc, lam = fghz * 1e9, C0 / (fghz * 1e9)
        ck = (G["mesh_key"], round(fc / 1e6), "dasfleet")
        fwd = np.empty((AZ.size, len(THETA_B)))
        rev = np.empty((AZ.size, len(THETA_B)))
        t0 = time.time()
        for j, phi in enumerate(AZ):
            u_i = _look(phi, 0.0)
            U_s = [_look(phi + tb, 0.0) for tb in THETA_B]
            fwd[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, gm, fc, u_i, U_s, spacing=lam / DIV, cache_key=ck,
                penetrate=PENETRATE, jitter=JITTER, exit_vis=EXIT_VIS), float))
            for t, u_s in enumerate(U_s):          # 역기하: 조명과 수신을 맞바꾼다
                rev[j, t] = float(np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                    mesh, gm, fc, u_s, [u_i], spacing=lam / DIV, cache_key=ck,
                    penetrate=PENETRATE, jitter=JITTER, exit_vis=EXIT_VIS), float))[0])
        save(dict(airframe=af, mode="reciprocity", f_ghz=fghz, theta_b=THETA_B,
                  az_deg=AZ.tolist(), sigma_fwd=fwd.tolist(), sigma_rev=rev.tolist(),
                  runtime_s=round(time.time() - t0, 2),
                  what=("fwd = σ(û_i→û_s), rev = σ(û_s→û_i). 상반성은 정리이므로 dB 차이는 "
                        "전부 모형오차다. θb=0 에서는 정의상 0.")), p)
        print(f"[recip] {af} f={fghz} done {time.time()-t0:.0f}s", flush=True)


# --------------------------------------------------------------------------- #
#  진단 모드 2 — exit_vis on/off (출사 가시성이 바이스태틱 열에서 얼마를 깎나)
# --------------------------------------------------------------------------- #
def run_exitvis(af: str, n_az: int, f_list, shard: int, nshard: int):
    G = GRIDS[af]
    mesh, gm = mesh_for(af), group_mat()
    AZ = np.linspace(0.0, 360.0, n_az, endpoint=False)
    for fi, fghz in enumerate(f_list):
        if fi % nshard != shard:
            continue
        p = os.path.join(PARTIAL, af, f"exitvis_f{fghz:.3f}.json")
        if os.path.exists(p):
            continue
        fc, lam = fghz * 1e9, C0 / (fghz * 1e9)
        ck = (G["mesh_key"], round(fc / 1e6), "dasfleet")
        on = np.empty((AZ.size, len(THETA_B)))
        off = np.empty((AZ.size, len(THETA_B)))
        t0 = time.time()
        for j, phi in enumerate(AZ):
            u_i = _look(phi, 0.0)
            U_s = [_look(phi + tb, 0.0) for tb in THETA_B]
            kw = dict(spacing=lam / DIV, cache_key=ck, penetrate=PENETRATE, jitter=JITTER)
            on[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, gm, fc, u_i, U_s, exit_vis=True, **kw), float))
            off[j] = np.atleast_1d(np.asarray(rcs_sbr_multistatic(
                mesh, gm, fc, u_i, U_s, exit_vis=False, **kw), float))
        save(dict(airframe=af, mode="exit_vis", f_ghz=fghz, theta_b=THETA_B,
                  az_deg=AZ.tolist(), sigma_exitvis_on=on.tolist(),
                  sigma_exitvis_off=off.tolist(), runtime_s=round(time.time() - t0, 2),
                  what="on = 헤드라인 설정. θb=0 에서 둘의 차는 0 이어야 한다(no-op 검산)."), p)
        print(f"[exitvis] {af} f={fghz} done {time.time()-t0:.0f}s", flush=True)


# --------------------------------------------------------------------------- #
#  작업 배분 — **정적 샤딩이 아니라 잠금파일로 선점**한다
#      워커를 몇 개 띄우든, 도중에 더 띄우든, 죽여도 서로 조율이 필요 없다. GPU 여유를 보며
#      워커 수를 실시간으로 늘리고 줄일 수 있어야 해서 이렇게 짰다(고정 샤드는 그게 안 된다).
#      죽은 워커가 남긴 잠금은 STALE_S 를 넘기면 회수한다.
# --------------------------------------------------------------------------- #
STALE_S = 3 * 3600


def _claim(path: str) -> bool:
    lock = path + ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:                                     # 죽은 워커의 잠금 회수
            if time.time() - os.path.getmtime(lock) > STALE_S and not os.path.exists(path):
                os.remove(lock)
                return _claim(path)
        except OSError:
            pass
        return False
    except OSError:
        return False


def _release(path: str):
    try:
        os.remove(path + ".lock")
    except OSError:
        pass


def run_plan(plan):
    """plan = [(airframe, stage), ...] 를 순서대로 훑으며 남은 작업을 선점해 계산한다."""
    for af, stage in plan:
        os.makedirs(os.path.join(PARTIAL, af), exist_ok=True)
        while True:
            todo = todo_for(af, stage)
            if not todo:
                break
            did = 0
            for f_idx, chunk, new_az in todo:
                p = part_path(af, f_idx, stage, chunk)
                if os.path.exists(p) or not _claim(p):
                    continue
                try:
                    d = compute_one(af, f_idx, new_az, stage)
                    d["chunk"] = chunk
                    save(d, p)
                    did += 1
                    print(f"[{af} s{stage}] f={d['f_ghz']:.3f} c{chunk} "
                          f"n_az={d['n_az']} {d['runtime_s']:.0f}s", flush=True)
                finally:
                    _release(p)
            if did == 0:            # 남은 것이 전부 다른 워커가 잡고 있는 중 → 다음 단계로
                break
        print(f"[{af} s{stage}] 이 워커가 할 일 없음", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--airframe", default="", choices=[""] + sorted(GRIDS))
    ap.add_argument("--plan", default="", help="예: mini2:0,phantom2:0,m350rtk:0")
    ap.add_argument("--mode", default="main", choices=["main", "recip", "exitvis"])
    ap.add_argument("--n-az", type=int, default=24)
    ap.add_argument("--freqs", default="")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshard", type=int, default=1)
    a = ap.parse_args()

    if a.mode != "main":
        fl = [float(x) for x in a.freqs.split(",") if x.strip()] or \
             list(np.asarray(GRIDS[a.airframe]["f_ghz"])[[0, len(GRIDS[a.airframe]["f_ghz"]) // 2, -1]])
        os.makedirs(os.path.join(PARTIAL, a.airframe), exist_ok=True)
        (run_recip if a.mode == "recip" else run_exitvis)(a.airframe, a.n_az, fl, a.shard, a.nshard)
        return

    plan = [(s.split(":")[0], int(s.split(":")[1])) for s in a.plan.split(",") if s.strip()]
    run_plan(plan)


if __name__ == "__main__":
    main()
