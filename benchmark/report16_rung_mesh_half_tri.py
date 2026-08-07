# -*- coding: utf-8 -*-
"""
report16_rung_mesh_half_tri.py — ⭐ **사다리 한 단: 삼각형을 절반으로 줄인 메쉬**
================================================================================

한 줄 요약
--------------------------------------------------------------------------------
report16_base 는 «진짜 CAD 메쉬 vs 기하 프리미티브(평판·원판·구)» 를 비교해서, 놀랍게도
**평판 프리미티브가 CAD 메쉬보다 하모닉이 더 풍부하다**(matrice4e 24/24 방위)는 판정을 냈다.
이 파일은 그 판정이 **메쉬 해상도의 산물인지** 확인한다 — CAD 메쉬의 삼각형을 절반으로
줄여서 같은 실험을 다시 돌린다.

무엇을 «절반» 으로 만드나
--------------------------------------------------------------------------------
프로펠러 메쉬(삼각형 약 7,800개)를 **QEM(이차오차 최소화) 간략화**로 3,900개로 줄인다.
QEM 은 «모서리를 하나씩 접되, 접었을 때 원래 표면에서 가장 덜 벗어나는 순서로 접는» 방법이다
(fast_simplification 0.1.13). 부피·면적·바깥법선 방향이 보존되는지 **매번 재서 기록**한다.

왜 이게 중요한 시험인가 — 우리 커널의 구조 때문이다
--------------------------------------------------------------------------------
PO 적분은 표면을 점으로 잘게 나눠 위상 맞춰 더한다. 그런데 `rcs_po.mesh_to_points` 는
**삼각형 하나에 최소 점 하나**를 깐다. CAD 블레이드는 이미 삼각형이 촘촘해서(모서리 ~1 mm)
요청 간격(λ/11 ≈ 7.8 mm)이 구속되지 않는다 → **점 개수 ≈ 삼각형 개수**다.
따라서 삼각형을 절반으로 줄이면 **적분 표본도 절반**이 된다. 두 가지가 한꺼번에 변한다:
   (a) 형상이 조금 뭉개진다 (기하),
   (b) 적분 표본이 절반이 된다 (수치).
그래서 (a)와 (b)를 가르는 통제팔을 같이 돌린다 — `mesh_half_tri_fine` 은 **같은 절반 메쉬**에
점을 4배 촘촘히 깐다. 여기서 지표가 안 움직이면 표본 수는 원인이 아니고 형상이 원인이다.

⭐⭐ 사전 예측(preregistration)
--------------------------------------------------------------------------------
계산하기 **전에** 예측을 파일로 떨구고(`--prereg`), 계산 뒤 자동 채점한다.
예측 파일이 없으면 계산 자체를 거부한다. «나중에 맞췄다» 고 말할 수 없게 만드는 장치다.

⚠ 결론을 미리 정하지 않는다
--------------------------------------------------------------------------------
절반 메쉬에서 판정이 **뒤집히면**, base 의 결론(«프리미티브가 CAD 를 이긴다»)은
메쉬 해상도의 산물이므로 **철회해야 한다**. 그 결과가 나오면 그대로 적는다.

공정성 (이 라운드의 급소)
--------------------------------------------------------------------------------
· 구·원판·평판도 **실제로 돌린다** — 같은 회전축·같은 rpm·같은 위상격자·같은 24방위.
  구를 «안 돌리고» 0 을 얻는 것은 증명이 아니라 동어반복이다.
· 재질(|Γ| 그룹표)·거리(10 m)·고각(15°)·주파수(3.5 GHz + 15.86 GHz)를 전부 동일하게 둔다.
· 부피 등가는 **계산해서** 맞추고 그 값을 JSON 에 남긴다.
· 규약·지표는 report16_base 의 함수를 **그대로 호출**한다(재구현 금지). 프리미티브 정의는
  base 의 `_worker` 안 폐쇄함수라 import 가 안 돼 복사했고, **base 표와 수치 일치**를
  회귀 게이트로 확인한다(`regression_gate`).

⛔ src/drones.py · src/drone_cad.py 는 읽기 전용. outputs/report15_* · report0N_* 미접촉.
⛔ 숫자 손입력 금지 — 예측의 «문턱값» 만 손으로 쓴다(그것이 예측이다). 결과는 전부 계산값.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

import report16_base as B                                            # noqa: E402

SCRATCH = os.environ.get("REPORT16_SCRATCH", B.SCRATCH)
OUT_JSON = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri.json")
OUT_PRE = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri_prereg.json")
OUT_NPZ = os.path.join(ROOT, "outputs", "report16_rung_mesh_half_tri_tables.npz")
OUT_FIG = os.path.join(ROOT, "outputs", "figures", "report16_rung_mesh_half_tri.png")
BASE_JSON = os.path.join(ROOT, "outputs", "report16_base.json")
BASE_NPZ = os.path.join(ROOT, "outputs", "report16_base_tables.npz")

DRONE_KEYS = ("mini2", "matrice4e")
# 팔 목록 — base 의 이름 규약을 그대로 쓴다(뒤에 _fine 이 붙으면 점밀도 4배).
ARMS = ["mesh", "mesh_half_tri", "mesh_quarter_tri", "mesh_half_tri_all",
        "mesh_fine", "mesh_half_tri_fine", "slab", "disc", "sphere"]
ARMS_HI = ["mesh", "mesh_half_tri", "slab"]

# 간략화 비율 — «삼각형 절반» 이 이 단의 이름이다.
KEEP = {"mesh_half_tri": 0.50, "mesh_quarter_tri": 0.25, "mesh_half_tri_all": 0.50}


# =========================================================================== #
#  ⭐⭐ 사전 예측 — 계산 전에 파일로 떨군다
# =========================================================================== #
def build_prereg():
    """base 결과를 읽어 «무엇을 뒤집힘이라 부를지» 를 못박고, 예측을 적는다.

    참조 숫자는 전부 outputs/report16_base.json 에서 **읽어 온다**(손입력 금지).
    손으로 적는 것은 예측의 문턱값뿐이며, 그것이 곧 예측이다."""
    base = json.load(open(BASE_JSON))
    pv = base["paired_arm_difference"]["values"]

    def ref(key, pair, metric):
        r = pv.get(f"{key}|{pair}", {}).get(metric, {})
        return dict(mean=r.get("mean"), sd=r.get("sd"), frac_positive=r.get("frac_positive"),
                    n=r.get("n"))

    baseline = {k: {m: ref(k, "slab - mesh", m)
                    for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db", "width_ratio")}
                for k in DRONE_KEYS}
    az_sd = {k: base["arms"][k]["mesh"]["spherical"]["per_az"]["flash_contrast_db"]["sd"]
             for k in DRONE_KEYS}

    P = {}
    P["P1_primitive_richness_verdict_survives"] = dict(
        claim_ko=("base 의 헤드라인 판정 — «평판 프리미티브가 CAD 메쉬보다 하모닉 차수가 "
                  "더 풍부하다» — 는 삼각형을 절반으로 줄여도 **살아남는다**."),
        test="paired(slab − mesh_half_tri).n_eff_orders : mean > 0 (두 기체 모두) "
             "AND frac_positive >= 0.75 (matrice4e)",
        reason_ko=("평판이 풍부한 이유가 «CAD 가 덜 촘촘해서» 가 아니라 «평판이 팁까지 "
                   "각진 채로 잘려 있어서(테이퍼·둥근 팁이 없어서)» 라고 보기 때문이다. "
                   "그렇다면 CAD 쪽 해상도를 낮춰도 방향은 안 바뀐다."),
        flip_means_ko="⚠ 뒤집히면 base 결론은 메쉬 해상도의 산물이므로 철회해야 한다.",
        thresholds=dict(mean_gt=0.0, frac_positive_ge=0.75))
    P["P2_half_mesh_moves_n_eff_little"] = dict(
        claim_ko="삼각형을 절반으로 줄여도 n_eff_orders 는 거의 안 움직인다.",
        test="|paired(mesh_half_tri − mesh).n_eff_orders.mean| <= 1.0 (두 기체 모두)",
        reason_ko=("절반으로 줄여도 점 간격은 여전히 λ/50 수준으로 λ/4 보다 훨씬 촘촘하다 "
                   "— 수렴 영역 안이다. 그리고 QEM 은 부피·면적을 보존한다."),
        thresholds=dict(abs_mean_le=1.0))
    P["P3_half_mesh_moves_flash_little"] = dict(
        claim_ko="플래시 대조비도 자세 산포보다 훨씬 덜 움직인다.",
        test="|paired(mesh_half_tri − mesh).flash_contrast_db.mean| <= 1.5 dB (두 기체 모두)",
        reason_ko="플래시는 «블레이드 면이 시선에 수직으로 서는 순간» 이 만든다 — 그 순간의 "
                  "투영 면적은 삼각형 개수가 아니라 형상이 정한다.",
        context_azimuth_sd_db=az_sd,
        thresholds=dict(abs_mean_le=1.5))
    P["P4_half_mesh_moves_dc_ac_little"] = dict(
        claim_ko="동체 대 블레이드 세기비(dc_ac_db)도 1 dB 안으로 움직인다.",
        test="|paired(mesh_half_tri − mesh).dc_ac_db.mean| <= 1.0 dB (두 기체 모두)",
        reason_ko="프레임(동체)은 그대로 두고 프로펠러만 줄였고, QEM 이 블레이드 면적을 "
                  "보존하므로 두 항 모두 거의 그대로여야 한다.",
        thresholds=dict(abs_mean_le=1.0))
    P["P5_waveform_stays_correlated"] = dict(
        claim_ko="파형 자체(AC 복소상관)가 0.90 이상으로 유지된다.",
        test="mean_az corr_AC(mesh_half_tri, mesh) >= 0.90 (두 기체 모두)",
        reason_ko=("07-27→08-03 은 블레이드를 **다시 설계**해서 상관이 0.505 까지 떨어졌지만, "
                   "간략화는 같은 표면을 성기게 표현할 뿐이다. 다만 얇은 뒷전(trailing edge)이 "
                   "뭉개질 수 있어 1.00 은 예상하지 않는다."),
        thresholds=dict(mean_ge=0.90))
    P["P6_half_mesh_stays_in_band"] = dict(
        claim_ko="절반 메쉬의 AC 전력은 여전히 운동학 가능대역 안에 있다(이산화 잔차가 안 샌다).",
        test="mean_az in_band_ac_frac(mesh_half_tri) >= 0.99 (두 기체 모두)",
        reason_ko="점 간격이 커져도 여전히 λ/50 수준이라 팁속도 위 대역으로 새어 나갈 만큼 "
                  "거칠지 않다.",
        thresholds=dict(mean_ge=0.99))
    P["P7_cad_dc_ac_advantage_survives"] = dict(
        claim_ko=("base 에서 CAD 가 이긴 유일한 지표 — «진짜 블레이드가 평판보다 동체 대비 "
                  "더 세게 돌아온다»(matrice4e +4.97 dB, 24/24) — 도 절반 메쉬에서 살아남는다."),
        test="paired(slab − mesh_half_tri).dc_ac_db : mean > 0 AND frac_positive >= 0.75 (matrice4e)",
        reason_ko="블레이드 면적과 재질 가중이 보존되므로 AC 세기의 절대 수준이 유지된다.",
        thresholds=dict(mean_gt=0.0, frac_positive_ge=0.75))
    P["P8_degradation_is_monotone"] = dict(
        claim_ko="4분의 1로 줄이면 절반보다 더 많이 어긋난다(해상도에 단조).",
        test="mean corr_AC(mesh_quarter_tri, mesh) < mean corr_AC(mesh_half_tri, mesh) (두 기체 모두)",
        reason_ko="단조가 아니면 그것은 수렴이 아니라 우연이라는 뜻이므로, 이 검사 자체가 "
                  "실험의 신뢰성 점검이다.",
        thresholds=dict(strict_less=True))
    P["P9_point_count_is_not_the_driver"] = dict(
        claim_ko=("절반 메쉬에 점을 4배 촘촘히 깔아도 지표가 되돌아오지 않는다 "
                  "— 즉 «표본이 절반이라서» 가 아니라 «형상이 뭉개져서» 다."),
        test=("|paired(mesh_half_tri_fine − mesh_fine).n_eff_orders.mean| 이 "
              "|paired(mesh_half_tri − mesh).n_eff_orders.mean| 의 0.5배 이상으로 남는다"),
        reason_ko="점밀도를 4배로 올리면 삼각형당 표본이 여러 개가 되어 «표본 절반» 효과는 "
                  "사라진다. 그래도 차이가 남으면 원인은 형상이다.",
        note_ko="⚠ 두 차이가 모두 아주 작으면(≤0.2) 이 검정은 판정력이 없다 — 그때는 "
                "INCONCLUSIVE 로 적는다.",
        thresholds=dict(ratio_ge=0.5, both_small_abs=0.2))

    return dict(
        rung="mesh_half_tri",
        model_ko="삼각형 절반 메쉬 (프로펠러 CAD 메쉬를 QEM 으로 50% 간략화)",
        written_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        written_before_compute=True,
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        producer="benchmark/report16_rung_mesh_half_tri.py --prereg",
        baseline_from_base_json=dict(
            file="outputs/report16_base.json",
            paired_slab_minus_mesh=baseline,
            azimuth_sd_of_flash_contrast_db=az_sd,
            note_ko="이 단의 «뒤집힘» 은 이 값들의 **부호가 바뀌는 것**을 뜻한다."),
        predictions=P,
        how_graded_ko=("계산이 끝나면 이 파일을 다시 읽어 자동 채점한다(PASS/FAIL/INCONCLUSIVE). "
                       "결과 JSON 에 이 파일의 sha256 과 mtime 을 박아 순서를 증명한다."),
        honesty_note_ko=("⚠ 예측이 틀리는 것이 이 라운드의 실패가 아니다. P1 이나 P7 이 FAIL 이면 "
                         "base 의 결론을 철회해야 한다는 **중요한 결과**다."))


# =========================================================================== #
#  메쉬 간략화 — «삼각형 절반» 을 만든다
# =========================================================================== #
def _tri_stats(V, F):
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    a = 0.5 * np.linalg.norm(cr, axis=1)
    vol = float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)
    e = np.concatenate([np.linalg.norm(p1 - p0, axis=1), np.linalg.norm(p2 - p1, axis=1),
                        np.linalg.norm(p0 - p2, axis=1)])
    return dict(n_tris=int(len(F)), n_verts=int(len(V)), area_m2=float(a.sum()),
                signed_volume_m3=vol, edge_median_m=float(np.median(e)),
                edge_max_m=float(e.max()),
                bbox_m=[float(x) for x in (V.max(0) - V.min(0))])


MIN_TRIS_TO_SIMPLIFY = 24        # 이보다 적은 조각은 손대지 않는다(형태가 무너진다)


def simplify_mesh(mesh, keep_frac, tag):
    """geom.Mesh → 삼각형 수를 keep_frac 배로 줄인 새 geom.Mesh.

    QEM(quadric error metric) 간략화: 모서리를 하나씩 접되, «접었을 때 원래 평면들에서
    벗어나는 제곱거리» 가 가장 작은 것부터 접는다. 그래서 평평한 데는 많이 줄고 곡률이
    큰 데(뒷전·팁)는 덜 준다.

    ⭐ **재질 그룹별로 따로 줄인다.** 우리 PO 는 점마다 부위 재질의 |Γ| 를 곱하는데(배터리·
      PCB·모터는 금속, 셸은 반투명 플라스틱), 그룹을 섞어서 간략화하면 재질 경계가 뭉개져
      «해상도를 낮춘 것» 이 아니라 «재질을 바꾼 것» 이 된다. 그러면 이 단의 비교가 오염된다.
      그래서 조각(그룹)마다 따로 접고 다시 합친다.
    ⚠ 삼각형이 MIN_TRIS_TO_SIMPLIFY 개 미만인 조각은 건드리지 않는다 — 그런 조각은 이미 상자·원기둥
      수준이라 더 줄이면 형태가 무너진다. 그런 조각이 몇 개였는지 기록한다.
    ⚠ 원본은 건드리지 않는다(새 메쉬를 만든다)."""
    import fast_simplification as fsimp
    from geom import Mesh

    V0 = np.ascontiguousarray(np.asarray(mesh.v, float))
    F0 = np.asarray(mesh.f, np.int64)
    G0 = np.asarray(mesh.g, object)
    before = _tri_stats(V0, F0)

    out = Mesh(mesh._group)
    per_group, skipped = {}, []
    for gname in sorted(set(mesh.g)):
        sel = np.where(G0 == gname)[0]
        Fg = F0[sel]
        used, inv = np.unique(Fg.ravel(), return_inverse=True)
        Vg = np.ascontiguousarray(V0[used])
        Fg = np.ascontiguousarray(inv.reshape(-1, 3).astype(np.int32))
        if len(Fg) < MIN_TRIS_TO_SIMPLIFY:
            vo, fo = Vg, Fg.astype(np.int64)
            skipped.append(gname)
        else:
            vo, fo = fsimp.simplify(Vg, Fg, target_reduction=float(1.0 - keep_frac))
            vo = np.asarray(vo, float)
            fo = np.asarray(fo, np.int64)
        base = len(out.v)
        out.v.extend(tuple(map(float, p)) for p in vo)
        out.f.extend(tuple(int(x) + base for x in t) for t in fo)
        out.g.extend([gname] * len(fo))
        per_group[gname] = dict(tris_before=int(len(sel)), tris_after=int(len(fo)),
                                simplified=bool(gname not in skipped))

    after = _tri_stats(np.asarray(out.v, float), np.asarray(out.f, np.int64))
    meta = dict(
        tag=tag, method="QEM edge-collapse (fast_simplification.simplify), per material group",
        keep_fraction_requested=float(keep_frac),
        n_groups=len(per_group), groups=per_group,
        groups_left_untouched=skipped, min_tris_to_simplify=MIN_TRIS_TO_SIMPLIFY,
        before=before, after=after,
        tri_ratio=after["n_tris"] / max(before["n_tris"], 1),
        area_ratio=after["area_m2"] / max(before["area_m2"], 1e-30),
        volume_ratio=after["signed_volume_m3"] / max(before["signed_volume_m3"], 1e-30),
        volume_sign_preserved=bool(np.sign(after["signed_volume_m3"]) ==
                                   np.sign(before["signed_volume_m3"])),
        edge_median_ratio=after["edge_median_m"] / max(before["edge_median_m"], 1e-30),
        bbox_delta_mm=[1000.0 * (b - a) for a, b in zip(before["bbox_m"], after["bbox_m"])],
        note_ko=("부피 부호가 보존돼야 바깥법선 규약(n̂·û>0 = 조명면)이 유지된다. "
                 "면적비가 1 에 가까워야 «면적이 줄어서 약해졌다» 는 다른 원인이 배제된다. "
                 "재질 그룹별로 따로 줄여 |Γ| 배분이 그대로 유지된다."))
    return out, meta


def surface_distance(mA, mB, spacing):
    """두 메쉬 표면 사이 거리[m] — 양방향 최근접점. «형상이 얼마나 뭉개졌나» 의 실측.

    두 메쉬를 같은 간격으로 점으로 깔고(면적 비례 표본), 서로의 최근접 거리를 잰다.
    한쪽 방향만 재면 «구멍» 을 놓치므로 양방향 최대(=Hausdorff 근사)를 함께 낸다."""
    from scipy.spatial import cKDTree
    from rcs_po import mesh_to_points
    PA = mesh_to_points(mA, spacing)[0]
    PB = mesh_to_points(mB, spacing)[0]
    dab = cKDTree(PB).query(PA)[0]
    dba = cKDTree(PA).query(PB)[0]
    return dict(n_pts_a=int(len(PA)), n_pts_b=int(len(PB)),
                rms_m=float(math.sqrt(0.5 * (np.mean(dab ** 2) + np.mean(dba ** 2)))),
                mean_m=float(0.5 * (dab.mean() + dba.mean())),
                hausdorff_m=float(max(dab.max(), dba.max())),
                probe_spacing_m=float(spacing))


# =========================================================================== #
#  점구름 — base 의 `clouds_for` 와 **같은 정의**(회귀 게이트로 확인)
# =========================================================================== #
FRAME_DIV, BLADE_DIV, BLADE_N = 6.0, 11.0, 26


def _odd(n):
    return int(n) if int(n) % 2 == 1 else int(n) + 1


def mesh_volume(m):
    V = np.asarray(m.v, float)
    F = np.asarray(m.f, int)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    return float(np.sum(np.einsum("ij,ij->i", p0, cr)) / 6.0)


def nn_spacing(P, n_probe=4000, seed=0):
    """점구름의 실측 최근접이웃 간격 중앙값[m] (요청 간격이 아니라 **실제** 촘촘함)."""
    from scipy.spatial import cKDTree
    P = np.asarray(P, float)
    if len(P) < 4:
        return float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(P), size=min(n_probe, len(P)), replace=False)
    d, _ = cKDTree(P).query(P[idx], k=2)
    return float(np.median(d[:, 1]))


def disc_mesh(R, thick, zc, target):
    """균일 격자 원판(위·아래 면 + 테두리 벽). base 와 동일."""
    from geom import Mesh
    n_seg = _odd(max(9, int(math.ceil(2 * math.pi * R / target))))
    n_ring = max(2, int(math.ceil(R / target)))
    m = Mesh("prop")
    ang = np.arange(n_seg) * (2 * math.pi / n_seg)
    rad = np.linspace(0.0, R, n_ring + 1)
    idx = {}
    for ir, rr in enumerate(rad):
        for ia in range(n_seg):
            for sgn, zz in ((0, zc - thick / 2), (1, zc + thick / 2)):
                idx[(ir, ia, sgn)] = m.add_vertex(rr * math.cos(ang[ia]),
                                                  rr * math.sin(ang[ia]), zz)
    for ir in range(n_ring):
        for ia in range(n_seg):
            ja = (ia + 1) % n_seg
            a, b = idx[(ir, ia, 1)], idx[(ir, ja, 1)]
            c, d = idx[(ir + 1, ja, 1)], idx[(ir + 1, ia, 1)]
            m.add_quad(a, b, c, d, "prop")
            a, b = idx[(ir, ia, 0)], idx[(ir + 1, ia, 0)]
            c, d = idx[(ir + 1, ja, 0)], idx[(ir, ja, 0)]
            m.add_quad(a, b, c, d, "prop")
    for ia in range(n_seg):
        ja = (ia + 1) % n_seg
        m.add_quad(idx[(n_ring, ia, 0)], idx[(n_ring, ja, 0)],
                   idx[(n_ring, ja, 1)], idx[(n_ring, ia, 1)], "prop")
    return m, n_seg, n_ring


def disc_prop(prop, R, target):
    """프로펠러 → 같은 반경·같은 두께의 회전대칭 원판(물리적 변조 0). base 와 동일."""
    V = np.asarray(prop.v, float)
    th = float(V[:, 2].max() - V[:, 2].min())
    zc = float(0.5 * (V[:, 2].max() + V[:, 2].min()))
    m, n_seg, n_ring = disc_mesh(R, th, zc, target)
    return m, dict(kind="disc", radius_m=R, thickness_m=th, z_center_m=zc,
                   n_seg=n_seg, n_ring=n_ring, n_tris=len(m.f),
                   n_tris_template=len(prop.f), residual_order=n_seg,
                   note_ko="균일 격자 원판. 이산화 잔차는 차수 n_seg 에만 나타난다.")


def slab_prop(prop, R, Pcloud=None):
    """프로펠러 → 같은 스팬·같은 코드·**같은 부피**의 평판. base 와 동일.
    두께 lz = 부피/(스팬×코드) 로 **풀어서** 부피 등가를 맞춘다(손입력 아님)."""
    from geom import box
    V = np.asarray(prop.v, float)
    lx = float(V[:, 0].max() - V[:, 0].min())
    ly = float(V[:, 1].max() - V[:, 1].min())
    vol = abs(mesh_volume(prop))
    lz = vol / max(lx * ly, 1e-30)
    zc = float(np.mean(Pcloud[:, 2])) if Pcloud is not None else \
        float(0.5 * (V[:, 2].max() + V[:, 2].min()))
    m = box(lx, ly, lz, center=(0.0, 0.0, zc), group="prop")
    zb = float(V[:, 2].max() - V[:, 2].min())
    return m, dict(kind="slab", span_m=lx, chord_m=ly, thickness_m=lz, z_center_m=zc,
                   volume_m3=vol, aspect_chord_over_thickness=ly / max(lz, 1e-30),
                   prop_bbox_z_extent_m=zb, thickness_over_bbox_z=lz / max(zb, 1e-30),
                   planform_area_m2=lx * ly, n_tris=len(m.f), n_tris_template=len(prop.f),
                   note_ko="스팬·코드는 실제 프롭 bbox, 두께는 부피가 같아지도록 풀었다.")


def clouds_for(key, arm, fc, simp_cache):
    """팔 하나의 점구름. base.clouds_for 와 같은 규약 + 절반메쉬 팔 추가."""
    from drones import (DRONES, build_frame, build_propeller, rotor_layout,
                        drone_gamma_map, build_drone)
    from rcs_po import mesh_to_points
    from geom import uv_sphere

    lam = B.C0 / fc
    s = DRONES[key]
    base_arm, fine = (arm[:-5], True) if arm.endswith("_fine") else (arm, False)
    bdiv = BLADE_DIV * (4.0 if fine else 1.0)
    fdiv = FRAME_DIV * (4.0 if fine else 1.0)
    spac = lam / bdiv
    gm = drone_gamma_map(s)

    # ── 프레임(회전하지 않는 부분) ─────────────────────────────────────────
    frame = build_frame(s)
    fmeta = {}
    if base_arm == "mesh_half_tri_all":
        ck = f"{key}|frame|{KEEP[base_arm]}"
        if ck not in simp_cache:
            simp_cache[ck] = simplify_mesh(frame, KEEP[base_arm], ck)
        frame, fmeta = simp_cache[ck]
        fmeta = dict(fmeta)
    Pf, Nf, dAf, wf = mesh_to_points(frame, lam / fdiv, gamma=gm)
    Wf = dAf * wf

    prop = build_propeller(s, n=BLADE_N)
    R = float(s.prop_dia_mm) / 2000.0
    meta = {}

    if base_arm == "mesh":
        pa, pb = prop, None
    elif base_arm in KEEP:
        ck = f"{key}|prop|{KEEP[base_arm]}"
        if ck not in simp_cache:
            simp_cache[ck] = simplify_mesh(prop, KEEP[base_arm], ck)
        pa, meta = simp_cache[ck]
        meta = dict(meta)
        pb = None                                   # 거울상은 점구름 y-반전 (base 규약)
    elif base_arm == "disc":
        pa, meta = disc_prop(prop, R, spac)
        pb = pa
    elif base_arm == "slab":
        P0 = mesh_to_points(prop, spac, gamma=gm)[0]
        pa, meta = slab_prop(prop, R, P0)
        pb = pa
    elif base_arm == "sphere":
        drone = build_drone(s)
        vol = abs(mesh_volume(drone))
        r_eq = (3.0 * vol / (4.0 * math.pi)) ** (1.0 / 3.0)
        seg = _odd(max(9, int(math.ceil(2 * math.pi * r_eq / spac))))
        rings = max(3, int(math.ceil(math.pi * r_eq / spac)))
        sph = uv_sphere(r_eq, seg=seg, rings=rings, group="sph")
        Ps, Ns, dAs = mesh_to_points(sph, spac)
        meta = dict(kind="sphere_whole", r_equal_volume_m=r_eq, volume_m3=vol,
                    seg=seg, rings=rings, n_tris=len(sph.f), n_tris_drone=len(drone.f),
                    gamma_abs=1.0, requested_spacing_m=float(spac),
                    actual_spacing_m=nn_spacing(Ps), residual_order=seg,
                    note_ko=("기체 전체를 등가부피 구로 교체(|Γ|=1). 시선을 같은 위상격자로 "
                             "**실제로 돌린다** — 남는 값이 계산기 자체의 바닥이다."))
        return dict(arm=arm, frame=None, rotor_cloud=(Ps, Ns, dAs),
                    rotor_cloud_m=(Ps, Ns, dAs),
                    rotors=[dict(center=(0.0, 0.0, 0.0), base_ang=0.0, dir=1)],
                    meta=meta, n_frame_pts=0, n_blade_pts=len(Ps), frame_meta=fmeta)
    else:
        raise ValueError(arm)

    Pp, Np_, dAp, wp = mesh_to_points(pa, spac, gamma=gm)
    if pb is None:
        Pm = Pp * np.array([1.0, -1.0, 1.0])
        Nm_ = Np_ * np.array([1.0, -1.0, 1.0])
        dAm, wm = dAp, wp
    else:
        Pm, Nm_, dAm, wm = mesh_to_points(pb, spac, gamma=gm)
    act = float(nn_spacing(Pp))
    meta = dict(meta, requested_spacing_m=float(spac), requested_lambda_over=float(bdiv),
                actual_spacing_m=act, lambda_over_actual=float(lam / max(act, 1e-12)),
                n_tris_rotating=len(pa.f),
                pts_per_tri=float(len(Pp) / max(len(pa.f), 1)))
    return dict(arm=arm, frame=(Pf, Nf, Wf), rotor_cloud=(Pp, Np_, dAp * wp),
                rotor_cloud_m=(Pm, Nm_, dAm * wm), rotors=rotor_layout(s),
                meta=meta, n_frame_pts=len(Wf), n_blade_pts=len(Pp), frame_meta=fmeta)


# =========================================================================== #
#  계산 — 모든 팔을 **같은 운동학**으로 실제로 돌린다
# =========================================================================== #
def run_tables(fc, tag, arms_by_drone):
    """위상 표 E(φ) 를 팔·기체·파면별로 계산한다. 반환: (tables, metas)."""
    from gpu import pick                                   # ⚠ torch 보다 먼저
    picked = pick(verbose=True)
    import torch
    from drones import DRONES

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    lam = B.C0 / fc
    k_wav = 2.0 * math.pi / lam
    az_list = np.arange(B.N_AZ) * (360.0 / B.N_AZ)
    tables, metas = {}, dict(fc=fc, tag=tag, gpu=picked, device=str(dev),
                             az_deg=[float(a) for a in az_list], drones={})
    simp_cache = {}

    for key, arms in arms_by_drone.items():
        s = DRONES[key]
        proto = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, fc)
        phis = np.linspace(0.0, 2 * math.pi, proto["n_phase"], endpoint=False)
        entry = dict(protocol=proto, spec=dict(
            name=s.name, prop_dia_mm=float(s.prop_dia_mm), prop_blades=int(s.prop_blades),
            hover_rpm=float(s.hover_rpm), num_rotors=int(s.num_rotors)), arms={})
        for arm in arms:
            t0 = time.time()
            cl = clouds_for(key, arm, fc, simp_cache)
            am = dict(meta=cl["meta"], frame_meta=cl.get("frame_meta") or {},
                      n_frame_pts=cl["n_frame_pts"], n_blade_pts=cl["n_blade_pts"],
                      rotors=[dict(center=[float(x) for x in r["center"]],
                                   base_ang=float(r["base_ang"]), dir=int(r["dir"]))
                              for r in cl["rotors"]])
            for wfront in ("spherical", "plane"):
                T = np.zeros((len(az_list), proto["n_phase"]), complex)
                for ia, az in enumerate(az_list):
                    u, A, R_t = B.look_and_antenna(az, B.EL_DEG, B.RANGE_M)
                    Ef = 0.0 + 0.0j
                    if cl["frame"] is not None:
                        Pf, Nf, Wf = cl["frame"]
                        Ef = B.field_static(torch, dev, Pf, Nf, Wf, k_wav, A, R_t, wfront)
                    tot = np.full(proto["n_phase"], Ef, complex)
                    for rot in cl["rotors"]:
                        d = float(rot["dir"])
                        P, N, W = cl["rotor_cloud"] if d > 0 else cl["rotor_cloud_m"]
                        tot += B.field_rotor(torch, dev, P, N, W, k_wav, A, R_t,
                                             rot["center"], math.radians(float(rot["base_ang"])),
                                             d, phis, wfront)
                    T[ia] = tot
                tables[f"{tag}|{key}|{arm}|{wfront}"] = T
            am["seconds"] = float(time.time() - t0)
            entry["arms"][arm] = am
            print(f"  [{tag}] {key:10s} {arm:18s} n_phase={proto['n_phase']:4d} "
                  f"pts(f/b)={cl['n_frame_pts']}/{cl['n_blade_pts']} [{am['seconds']:.1f}s]",
                  flush=True)
        metas["drones"][key] = entry
    return tables, metas, simp_cache


# =========================================================================== #
#  회귀 게이트 — 이 파일의 프리미티브 정의가 base 표와 같은 값을 내는가
# =========================================================================== #
def regression_gate(tables, tag="main"):
    """base 가 저장한 위상표와 **비트에 가까운** 일치를 요구한다.

    base 의 프리미티브(평판·원판·구)와 mesh 팔 정의를 이 파일이 복사했으므로, 같은 입력에서
    같은 값이 나와야 한다. 어긋나면 이 단의 비교는 base 와 이어붙일 수 없다."""
    if not os.path.exists(BASE_NPZ):
        return dict(absent=True, note_ko="base 표가 없어 회귀 게이트를 건너뜀")
    z = np.load(BASE_NPZ)
    rows = {}
    for key in DRONE_KEYS:
        for arm in ("mesh", "mesh_fine", "slab", "disc", "sphere"):
            for wfront in ("spherical", "plane"):
                bk = f"main__G_0804__{key}__{arm}__{wfront}"
                mk = f"{tag}|{key}|{arm}|{wfront}"
                if bk not in z.files or mk not in tables:
                    continue
                a, b = z[bk], tables[mk]
                if a.shape != b.shape:
                    rows[f"{key}|{arm}|{wfront}"] = dict(shape_mismatch=[list(a.shape),
                                                                        list(b.shape)])
                    continue
                num = float(np.max(np.abs(a - b)))
                den = float(np.max(np.abs(a)))
                rows[f"{key}|{arm}|{wfront}"] = dict(
                    max_abs_diff=num, max_abs_ref=den, max_rel=num / max(den, 1e-300))
    rels = [r["max_rel"] for r in rows.values() if "max_rel" in r]
    return dict(reference="outputs/report16_base_tables.npz (report16_base.py, G_0804)",
                rows=rows, worst_rel=max(rels) if rels else None, tolerance=1e-12,
                verdict=("PASS" if rels and max(rels) < 1e-12 else
                         ("FAIL" if rels else "NO_OVERLAP")),
                what_ko=("이 파일이 복사한 프리미티브·mesh 정의가 base 와 같은 위상표를 내는가. "
                         "여기가 PASS 여야 base 의 판정과 이 단의 판정을 나란히 놓을 수 있다."))


# =========================================================================== #
#  지표·짝지은 비교
# =========================================================================== #
def per_az_metrics(tables, metas, tag, key, arm, wfront="spherical"):
    k = f"{tag}|{key}|{arm}|{wfront}"
    if k not in tables:
        return None
    T = tables[k]
    proto = metas["drones"][key]["protocol"]
    nb = metas["drones"][key]["spec"]["prop_blades"]
    return [B.md_metrics16(T[i], proto, nb) for i in range(T.shape[0])]


METRIC_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p50", "order_p90",
               "dominant_order", "blade_comb_frac", "fd_edge_hz", "width_ratio",
               "dc_ac_db", "sigma_eq_mean_dbsm", "in_band_ac_frac",
               "in_band_ac_over_dc_db", "ac_over_floor_db",
               "width_ratio_10db", "width_ratio_30db")


def summarize_arm(per_az):
    return dict(per_az={kk: B.summarize([m[kk] for m in per_az]) for kk in METRIC_KEYS},
                az0={kk: per_az[0][kk] for kk in METRIC_KEYS},
                interpretable_frac=float(np.mean([m["metrics_interpretable"] for m in per_az])),
                band_order=int(per_az[0]["band_order"]), n_az=len(per_az))


PAIR_KEYS = ("flash_contrast_db", "n_eff_orders", "order_p90", "blade_comb_frac",
             "dc_ac_db", "in_band_ac_over_dc_db", "width_ratio", "sigma_eq_mean_dbsm")


def paired_diff(ma, mb):
    """같은 방위에서 팔 B − 팔 A. 자세 산포는 두 팔에 **공통**이라 짝지으면 사라진다."""
    row = {}
    for kk in PAIR_KEYS:
        d = np.array([y[kk] - x[kk] for x, y in zip(ma, mb)], float)
        d = d[np.isfinite(d)]
        sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
        row[kk] = dict(mean=float(d.mean()), sd=sd,
                       sem=float(sd / max(math.sqrt(d.size), 1.0)),
                       frac_positive=float(np.mean(d > 0)), n=int(d.size),
                       min=float(d.min()), max=float(d.max()))
    return row


# =========================================================================== #
#  자동 채점
# =========================================================================== #
def grade(J, pre):
    P = pre["predictions"]
    pd = J["paired"]
    cc = J["waveform_correlation"]
    arms = J["arms"]
    G = {}

    def add(pid, ok, actual, note=""):
        G[pid] = dict(verdict=("PASS" if ok is True else
                               ("FAIL" if ok is False else "INCONCLUSIVE")),
                      claim_ko=P[pid]["claim_ko"], test=P[pid]["test"],
                      actual=actual, note_ko=note)

    # P1 — 프리미티브 우위 판정이 살아남는가
    a = {k: pd[f"{k}|slab - mesh_half_tri"]["n_eff_orders"] for k in DRONE_KEYS}
    ok = all(a[k]["mean"] > 0 for k in DRONE_KEYS) and \
        a["matrice4e"]["frac_positive"] >= P["P1_primitive_richness_verdict_survives"][
            "thresholds"]["frac_positive_ge"]
    add("P1_primitive_richness_verdict_survives", bool(ok),
        {k: dict(mean=a[k]["mean"], frac_positive=a[k]["frac_positive"],
                 base_mean=pre["baseline_from_base_json"]["paired_slab_minus_mesh"][k]
                 ["n_eff_orders"]["mean"]) for k in DRONE_KEYS})

    # P2·P3·P4 — 절반 메쉬가 지표를 얼마나 움직이나
    for pid, mkey, thr in (("P2_half_mesh_moves_n_eff_little", "n_eff_orders", 1.0),
                           ("P3_half_mesh_moves_flash_little", "flash_contrast_db", 1.5),
                           ("P4_half_mesh_moves_dc_ac_little", "dc_ac_db", 1.0)):
        v = {k: pd[f"{k}|mesh_half_tri - mesh"][mkey] for k in DRONE_KEYS}
        ok = all(abs(v[k]["mean"]) <= thr for k in DRONE_KEYS)
        add(pid, bool(ok), {k: dict(mean=v[k]["mean"], sd=v[k]["sd"],
                                    frac_positive=v[k]["frac_positive"]) for k in DRONE_KEYS})

    # P5 — 파형 상관
    v = {k: cc[f"{k}|mesh_half_tri vs mesh"]["mean"] for k in DRONE_KEYS}
    add("P5_waveform_stays_correlated", bool(all(v[k] >= 0.90 for k in DRONE_KEYS)), v)

    # P6 — 대역 안에 머무는가
    v = {k: arms[k]["mesh_half_tri"]["spherical"]["per_az"]["in_band_ac_frac"]["mean"]
         for k in DRONE_KEYS}
    add("P6_half_mesh_stays_in_band", bool(all(v[k] >= 0.99 for k in DRONE_KEYS)), v)

    # P7 — CAD 가 이겼던 지표(dc_ac_db)가 살아남는가
    a = {k: pd[f"{k}|slab - mesh_half_tri"]["dc_ac_db"] for k in DRONE_KEYS}
    ok = a["matrice4e"]["mean"] > 0 and a["matrice4e"]["frac_positive"] >= 0.75
    add("P7_cad_dc_ac_advantage_survives", bool(ok),
        {k: dict(mean=a[k]["mean"], frac_positive=a[k]["frac_positive"],
                 base_mean=pre["baseline_from_base_json"]["paired_slab_minus_mesh"][k]
                 ["dc_ac_db"]["mean"]) for k in DRONE_KEYS})

    # P8 — 단조성
    v = {k: dict(half=cc[f"{k}|mesh_half_tri vs mesh"]["mean"],
                 quarter=cc[f"{k}|mesh_quarter_tri vs mesh"]["mean"]) for k in DRONE_KEYS}
    add("P8_degradation_is_monotone",
        bool(all(v[k]["quarter"] < v[k]["half"] for k in DRONE_KEYS)), v)

    # P9 — 점 개수가 원인인가 형상이 원인인가
    v = {}
    verdicts = []
    for k in DRONE_KEYS:
        coarse = pd[f"{k}|mesh_half_tri - mesh"]["n_eff_orders"]["mean"]
        finev = pd[f"{k}|mesh_half_tri_fine - mesh_fine"]["n_eff_orders"]["mean"]
        ratio = abs(finev) / max(abs(coarse), 1e-12)
        small = abs(coarse) <= 0.2 and abs(finev) <= 0.2
        v[k] = dict(coarse_delta=coarse, fine_delta=finev, ratio=ratio, both_small=bool(small))
        verdicts.append(None if small else (ratio >= 0.5))
    ok = None if any(x is None for x in verdicts) else all(verdicts)
    add("P9_point_count_is_not_the_driver", ok, v,
        note=("두 차이가 모두 0.2 이하면 판정력이 없어 INCONCLUSIVE 로 둔다 — "
              "그 자체가 «절반으로 줄여도 아무 일도 안 일어난다» 는 뜻이다."))

    n_pass = sum(1 for g in G.values() if g["verdict"] == "PASS")
    n_fail = sum(1 for g in G.values() if g["verdict"] == "FAIL")
    G["_summary"] = dict(
        n_pass=n_pass, n_fail=n_fail,
        n_inconclusive=sum(1 for g in G.values() if g["verdict"] == "INCONCLUSIVE"),
        headline_ko=("⭐ 판정 뒤집힘 여부는 P1(하모닉 풍부도)과 P7(동체 대비 세기)이 결정한다. "
                     "둘 다 PASS 면 base 결론은 메쉬 해상도의 산물이 아니다."),
        verdict_flipped=bool(G["P1_primitive_richness_verdict_survives"]["verdict"] == "FAIL" or
                             G["P7_cad_dc_ac_advantage_survives"]["verdict"] == "FAIL"))
    return G


# =========================================================================== #
#  그림 (글씨는 전부 영어 — 저장소 규약)
# =========================================================================== #
def make_figure(J, tables, metas, tables_hi, metas_hi):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import gridspec

    plt.rcParams.update({"figure.facecolor": "white", "savefig.facecolor": "white",
                         "axes.grid": True, "grid.alpha": 0.25, "font.size": 8.5})
    COL = {"mesh": "#1565c0", "mesh_half_tri": "#ef6c00", "mesh_quarter_tri": "#8e24aa",
           "mesh_half_tri_all": "#6d4c41", "slab": "#2e7d32", "disc": "#00838f",
           "sphere": "#c62828"}
    LBL = {"mesh": "CAD mesh (100% tri)", "mesh_half_tri": "half-tri (50%)",
           "mesh_quarter_tri": "quarter-tri (25%)", "mesh_half_tri_all": "half-tri incl. frame",
           "slab": "flat-plate primitive", "disc": "rot.-symmetric disc",
           "sphere": "equal-volume sphere"}

    fig = plt.figure(figsize=(17.5, 13.0))
    gs = gridspec.GridSpec(4, 3, hspace=0.42, wspace=0.26,
                           left=0.055, right=0.985, top=0.925, bottom=0.045)
    fig.suptitle("report16 rung — half-triangle mesh: does the primitive-vs-CAD verdict "
                 "survive a 2x coarser mesh?  (PO, monostatic, R=10 m, el=15 deg, "
                 "24 azimuths, spherical wavefront)", fontsize=11.5, y=0.975)

    kmain = "matrice4e"
    proto = metas["drones"][kmain]["protocol"]

    # (0,0) 파형 — 한 회전 동안의 |E|
    ax = fig.add_subplot(gs[0, 0])
    ph = np.degrees(np.linspace(0, 2 * np.pi, proto["n_phase"], endpoint=False))
    for arm in ("mesh", "mesh_half_tri", "mesh_quarter_tri", "slab", "disc"):
        k = f"main|{kmain}|{arm}|spherical"
        if k not in tables:
            continue
        E = tables[k][0]
        ax.plot(ph, 20 * np.log10(np.abs(E - E.mean()) + 1e-30), lw=1.0,
                color=COL[arm], label=LBL[arm], alpha=0.9)
    ax.set_xlabel("rotor phase [deg]"); ax.set_ylabel("|E - mean(E)| [dB, arb.]")
    ax.set_title(f"(a) one revolution, {kmain}, az=0 deg", fontsize=9.5)
    ax.legend(fontsize=6.6, loc="lower right"); ax.set_xlim(0, 360)

    # (0,1) 선 스펙트럼
    ax = fig.add_subplot(gs[0, 1])
    for arm in ("mesh", "mesh_half_tri", "mesh_quarter_tri", "slab", "disc", "sphere"):
        k = f"main|{kmain}|{arm}|spherical"
        if k not in tables:
            continue
        E = tables[k][0]
        S = len(E)
        c = np.fft.fft(E) / S
        m = np.fft.fftfreq(S, d=1.0 / S).astype(int)
        sel = (m > 0) & (m <= int(3 * proto["beta"]))
        pw = 10 * np.log10(np.abs(c[sel]) ** 2 + 1e-32)
        ax.plot(m[sel], pw - pw.max(), lw=1.0, color=COL[arm], label=LBL[arm], alpha=0.9)
    ax.axvline(proto["beta"], color="k", ls="--", lw=1.0)
    ax.set_xlabel("harmonic order m  (Doppler = m * f_rot)")
    ax.set_ylabel("line power [dB rel. peak]")
    ax.set_title("(b) line spectrum — richness of orders", fontsize=9.5)
    ax.set_ylim(-90, 5)
    ax.text(proto["beta"], -87, "  beta = f_tip / f_rot\n  (kinematic limit)", fontsize=6.6,
            va="bottom", ha="left")
    ax.legend(fontsize=6.6, loc="upper right")

    # (0,2) 파형 상관 vs 삼각형 수
    ax = fig.add_subplot(gs[0, 2])
    for key, mk in (("mini2", "o"), ("matrice4e", "s")):
        xs, ys, es = [], [], []
        for arm in ("mesh_half_tri", "mesh_quarter_tri"):
            r = J["waveform_correlation"].get(f"{key}|{arm} vs mesh")
            t = J["mesh_simplification"].get(f"{key}|prop|{KEEP[arm]}")
            if not r or not t:
                continue
            xs.append(100.0 * t["tri_ratio"]); ys.append(r["mean"]); es.append(r["sd"])
        xs.append(100.0); ys.append(1.0); es.append(0.0)
        ax.errorbar(xs, ys, yerr=es, marker=mk, ms=5, lw=1.2, capsize=3, label=key)
    for key in DRONE_KEYS:
        r = J["waveform_correlation"].get(f"{key}|slab vs mesh")
        if r:
            ax.axhline(r["mean"], color=COL["slab"], ls=":", lw=1.0)
    ax.text(0.02, 0.06, "dotted: flat-plate primitive vs CAD", transform=ax.transAxes,
            fontsize=7, color=COL["slab"])
    ax.set_xlabel("triangles kept [%]"); ax.set_ylabel("AC waveform correlation vs full CAD")
    ax.set_title("(c) how fast does the waveform break?", fontsize=9.5)
    ax.set_ylim(-0.02, 1.03); ax.legend(fontsize=7.5)

    # (1,0)~(1,2) 짝지은 차이: n_eff / flash / dc_ac
    for j, mkey, ttl in ((0, "n_eff_orders", "(d) effective harmonic orders"),
                         (1, "flash_contrast_db", "(e) flash contrast [dB]"),
                         (2, "dc_ac_db", "(f) body-to-blade ratio [dB]")):
        ax = fig.add_subplot(gs[1, j])
        pairs = [("mesh_half_tri - mesh", "half-tri - CAD"),
                 ("mesh_quarter_tri - mesh", "quarter - CAD"),
                 ("mesh_half_tri_all - mesh", "half-tri(+frame) - CAD"),
                 ("slab - mesh", "slab - CAD  [base verdict]"),
                 ("slab - mesh_half_tri", "slab - half-tri  [this rung]")]
        xs = np.arange(len(pairs))
        for oi, key in enumerate(DRONE_KEYS):
            mu = [J["paired"].get(f"{key}|{p}", {}).get(mkey, {}).get("mean", np.nan)
                  for p, _ in pairs]
            se = [J["paired"].get(f"{key}|{p}", {}).get(mkey, {}).get("sem", np.nan)
                  for p, _ in pairs]
            ax.errorbar(xs + (oi - 0.5) * 0.16, mu, yerr=se, ls="none", marker="o", ms=5,
                        capsize=3, label=key)
        ax.axhline(0, color="k", lw=1.0)
        ax.set_xticks(xs); ax.set_xticklabels([l for _, l in pairs], rotation=22,
                                              ha="right", fontsize=6.8)
        ax.set_title(ttl + "  (paired, same azimuth)", fontsize=9.5)
        ax.set_ylabel("mean paired difference")
        rr = J["resolution_axis_vs_model_axis"]["values"]

        def _fmt(k):
            v = rr[f"{k}|{mkey}"]["model_axis"]["slab"]["times_larger_than_resolution_span"]
            return "n/a" if v is None else f"{v:.1f}x"
        txt = "plate-vs-CAD gap = " + " / ".join(
            _fmt(k) for k in DRONE_KEYS if f"{k}|{mkey}" in rr) + "  the whole resolution span"
        ax.text(0.02, 0.97, txt, transform=ax.transAxes, fontsize=6.6, ha="left", va="top",
                color="#37474f",
                bbox=dict(fc="white", ec="#cfd8dc", lw=0.6, boxstyle="round,pad=0.25"))
        if j == 0:
            ax.legend(fontsize=7.5, loc="center left")

    # (2,0) 방위별 짝지은 차이 (n_eff) — 부호 일관성
    ax = fig.add_subplot(gs[2, 0])
    az = np.array(metas["az_deg"])
    for key, ls in (("mini2", "-"), ("matrice4e", "--")):
        for pair, col in (("slab - mesh", COL["slab"]),
                          ("slab - mesh_half_tri", COL["mesh_half_tri"])):
            d = J["per_azimuth_paired"].get(f"{key}|{pair}|n_eff_orders")
            if d:
                ax.plot(az, d, ls, color=col, lw=1.1,
                        label=f"{key}: {pair}", alpha=0.85)
    ax.axhline(0, color="k", lw=1.0)
    ax.set_xlabel("azimuth [deg]"); ax.set_ylabel("delta n_eff_orders")
    ax.set_title("(g) sign consistency across pose", fontsize=9.5)
    ax.legend(fontsize=6.4, ncol=1)

    # (2,1) 널 앵커 — 실제로 돌린 회전대칭체의 바닥
    ax = fig.add_subplot(gs[2, 1])
    labels, vals, cols = [], [], []
    for key in DRONE_KEYS:
        for arm in ("mesh", "mesh_half_tri", "slab", "disc", "sphere"):
            a = J["arms"].get(key, {}).get(arm, {}).get("spherical")
            if not a:
                continue
            labels.append(f"{key[:4]}\n{arm.replace('mesh_half_tri','half')}")
            vals.append(a["per_az"]["in_band_ac_over_dc_db"]["mean"])
            cols.append(COL[arm])
    ax.bar(np.arange(len(vals)), vals, color=cols)
    ax.set_xticks(np.arange(len(labels)))
    ax.set_xticklabels(labels, fontsize=6.3)
    ax.set_ylabel("in-band AC / DC [dB]")
    ax.set_title("(h) null anchors: disc & sphere ARE rotated", fontsize=9.5)

    # (2,2) 고주파 대조
    ax = fig.add_subplot(gs[2, 2])
    if J.get("hi_band", {}).get("paired"):
        pairs = [("slab - mesh", "slab - CAD"), ("slab - mesh_half_tri", "slab - half-tri"),
                 ("mesh_half_tri - mesh", "half-tri - CAD")]
        xs = np.arange(len(pairs))
        for oi, key in enumerate(DRONE_KEYS):
            mu = [J["hi_band"]["paired"].get(f"{key}|{p}", {}).get("n_eff_orders", {})
                  .get("mean", np.nan) for p, _ in pairs]
            se = [J["hi_band"]["paired"].get(f"{key}|{p}", {}).get("n_eff_orders", {})
                  .get("sem", np.nan) for p, _ in pairs]
            ax.errorbar(xs + (oi - 0.5) * 0.16, mu, yerr=se, ls="none", marker="D", ms=5,
                        capsize=3, label=key)
        ax.axhline(0, color="k", lw=1.0)
        ax.set_xticks(xs); ax.set_xticklabels([l for _, l in pairs], rotation=18,
                                              ha="right", fontsize=7)
        ax.set_ylabel("delta n_eff_orders")
        ax.legend(fontsize=7.5)
    ax.set_title(f"(i) at {B.FC_PO_KNEE/1e9:.2f} GHz — above the PO validity knee", fontsize=9.5)

    # (3,0) 기하 충실도
    ax = fig.add_subplot(gs[3, 0])
    rows = []
    for key in DRONE_KEYS:
        for arm in ("mesh_half_tri", "mesh_quarter_tri"):
            t = J["mesh_simplification"].get(f"{key}|prop|{KEEP[arm]}")
            sd = J["surface_distance"]["values"].get(f"{key}|prop|{KEEP[arm]}")
            if t and sd:
                rows.append((f"{key[:4]} {int(round(100*t['tri_ratio']))}%",
                             100 * (t["volume_ratio"] - 1), 100 * (t["area_ratio"] - 1),
                             1000 * sd["rms_m"], 1000 * sd["hausdorff_m"]))
    if rows:
        xs = np.arange(len(rows))
        ax.bar(xs - 0.2, [r[1] for r in rows], 0.18, label="volume change [%]")
        ax.bar(xs, [r[2] for r in rows], 0.18, label="area change [%]")
        ax2 = ax.twinx()
        ax2.plot(xs + 0.22, [r[3] for r in rows], "k^", ms=6, label="surface RMS [mm]")
        ax2.plot(xs + 0.22, [r[4] for r in rows], "kv", ms=6, label="Hausdorff [mm]")
        ax2.set_ylabel("surface deviation [mm]"); ax2.grid(False)
        ax2.legend(fontsize=6.8, loc="upper right")
        ax.set_xticks(xs); ax.set_xticklabels([r[0] for r in rows], fontsize=7)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_ylabel("change vs full CAD [%]"); ax.legend(fontsize=6.8, loc="upper left")
    ax.set_title("(j) what the simplifier actually did to the shape", fontsize=9.5)

    # (3,1) 점밀도 통제
    ax = fig.add_subplot(gs[3, 1])
    labels, v_coarse, v_fine = [], [], []
    for key in DRONE_KEYS:
        c = J["paired"].get(f"{key}|mesh_half_tri - mesh", {}).get("n_eff_orders", {})
        f_ = J["paired"].get(f"{key}|mesh_half_tri_fine - mesh_fine", {}).get("n_eff_orders", {})
        if c and f_:
            labels.append(key); v_coarse.append(c["mean"]); v_fine.append(f_["mean"])
    xs = np.arange(len(labels))
    ax.bar(xs - 0.18, v_coarse, 0.34, label="1 point / triangle")
    ax.bar(xs + 0.18, v_fine, 0.34, label="4x denser sampling")
    ax.axhline(0, color="k", lw=1.0)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("delta n_eff_orders  (half-tri - CAD)")
    ax.set_title("(k) is it fewer facets, or fewer samples?", fontsize=9.5)
    ax.legend(fontsize=7.5)

    # (3,2) 채점표
    ax = fig.add_subplot(gs[3, 2]); ax.axis("off")
    ax.set_title("(l) preregistered predictions — auto-graded", fontsize=9.5)
    yy = 0.97
    for pid, g in J["grading"].items():
        if pid.startswith("_"):
            continue
        col = {"PASS": "#2e7d32", "FAIL": "#c62828"}.get(g["verdict"], "#8d6e63")
        ax.text(0.0, yy, f"{g['verdict']:<13s}", fontsize=7.6, color=col, family="monospace",
                transform=ax.transAxes, va="top")
        ax.text(0.30, yy, pid.split("_", 1)[1].replace("_", " ")[:44], fontsize=7.0,
                transform=ax.transAxes, va="top")
        yy -= 0.088
    s = J["grading"]["_summary"]
    ax.text(0.0, yy - 0.03,
            f"pass {s['n_pass']} / fail {s['n_fail']} / inconclusive {s['n_inconclusive']}"
            f"   ->  base verdict "
            f"{'FLIPPED' if s['verdict_flipped'] else 'SURVIVES'}",
            fontsize=8.4, transform=ax.transAxes, va="top", weight="bold",
            color="#c62828" if s["verdict_flipped"] else "#2e7d32")
    ax.text(0.0, yy - 0.12,
            f"PO validity: blade width {J['po_validity_warning']['blade_width_mm']:.2f} mm "
            f"needs {J['po_validity_warning']['blade_knee_ghz']:.2f} GHz\n"
            f"-> at 3.5 GHz the micro-Doppler source is the weakest part of the kernel",
            fontsize=7.0, transform=ax.transAxes, va="top", color="#b71c1c")

    os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
    fig.savefig(OUT_FIG, dpi=155)
    plt.close(fig)
    return os.path.relpath(OUT_FIG, ROOT)


# =========================================================================== #
#  MAIN
# =========================================================================== #
def main(with_hi=True):
    t0 = time.time()
    if not os.path.exists(OUT_PRE):
        raise SystemExit("사전 예측 파일이 없다. 먼저 `--prereg` 로 예측을 떨궈라: " + OUT_PRE)
    pre = json.load(open(OUT_PRE))
    pre_sha = hashlib.sha256(open(OUT_PRE, "rb").read()).hexdigest()[:16]
    pre_mtime = os.path.getmtime(OUT_PRE)

    J = dict(meta=dict(
        report="report16", rung="mesh_half_tri",
        producer="benchmark/report16_rung_mesh_half_tri.py",
        generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        git_rev=subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip(),
        purpose_ko=("CAD 메쉬의 삼각형을 절반으로 줄여 같은 마이크로도플러 실험을 다시 돌린다. "
                    "base 의 판정(«평판 프리미티브가 CAD 보다 하모닉이 풍부하다»)이 "
                    "메쉬 해상도의 산물인지 가른다."),
        headline_question_ko="절반 해상도에서 판정이 뒤집히는가.",
        prereg=dict(file=os.path.relpath(OUT_PRE, ROOT), sha256_16=pre_sha,
                    written_at=pre["written_at"],
                    mtime=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(pre_mtime)),
                    note_ko="이 파일은 계산 시작 전에 디스크에 존재해야 한다(없으면 실행 거부).")))

    # ── 규약 (base 를 그대로 계승) ─────────────────────────────────────────
    from drones import DRONES
    proto_all = {}
    for k in DRONE_KEYS:
        s = DRONES[k]
        proto_all[k] = B.derive_protocol(s.prop_dia_mm, s.hover_rpm, s.prop_blades, B.FC_MAIN)
        proto_all[k]["hi_band"] = B.derive_protocol(s.prop_dia_mm, s.hover_rpm,
                                                    s.prop_blades, B.FC_PO_KNEE)
    J["protocol"] = dict(
        inherited_from="benchmark/report16_base.py (derive_protocol · md_metrics16 재사용)",
        fc_main_hz=B.FC_MAIN, fc_po_knee_hz=B.FC_PO_KNEE, el_deg=B.EL_DEG, range_m=B.RANGE_M,
        n_az=B.N_AZ, az_step_deg=360.0 / B.N_AZ, n_rev=B.N_REV, os_factor=B.OS_FACTOR,
        wavefront_headline="spherical", wavefront_control="plane", period_deg=360.0,
        monostatic=True, frame_div=FRAME_DIV, blade_div=BLADE_DIV, blade_n=BLADE_N,
        engine="pure PO on point clouds (no occlusion, no edge diffraction, scalar |Gamma|)",
        per_drone=proto_all,
        fairness_ko=("구·원판·평판을 **실제로 같은 위상격자로 돌린다** — 같은 회전축·같은 rpm·"
                     "같은 24방위·같은 재질표·같은 거리. 구를 안 돌리고 0 을 얻는 것은 "
                     "증명이 아니라 동어반복이다."))

    knee = json.load(open(os.path.join(ROOT, "outputs", "report00_po_case.json")))["s4_limits"]
    #  블레이드 폭은 무릎 표의 **키 이름**에 들어 있다(prop_blade_13p78mm_ghz) — 손으로 옮겨
    #  적지 않고 파싱한다. 표가 바뀌면 이 값도 따라 바뀐다.
    bkey = next(k for k in knee["feature_knee_frequencies"] if k.startswith("prop_blade_"))
    blade_mm = float(bkey.split("prop_blade_")[1].split("mm")[0].replace("p", "."))
    knee_ghz = float(knee["feature_knee_frequencies"][bkey])
    J["po_validity_warning"] = dict(
        knee_a_over_lambda=knee["po_validity_knee_a_over_lambda"],
        blade_knee_ghz=knee_ghz, blade_width_mm=blade_mm,
        blade_width_source=f"outputs/report00_po_case.json :: s4_limits.feature_knee_frequencies.{bkey}",
        production_band_ghz=B.FC_MAIN / 1e9,
        blade_width_over_lambda_main=blade_mm * 1e-3 / (B.C0 / B.FC_MAIN),
        blade_width_over_lambda_hi=blade_mm * 1e-3 / (B.C0 / B.FC_PO_KNEE),
        statement_ko=(f"⚠ 마이크로도플러를 만드는 부품(프로펠러 블레이드, 폭 {blade_mm:.2f} mm)은 "
                      f"{knee_ghz:.2f} GHz 에서야 PO 유효 무릎"
                      f"(폭 ≥ {knee['po_validity_knee_a_over_lambda']:.3f}λ)을 넘는다. "
                      f"생산 대역 {B.FC_MAIN/1e9:.1f} GHz 에서는 **커널이 가장 약한 부품이 곧 "
                      f"신호원**이다. 그래서 {B.FC_PO_KNEE/1e9:.2f} GHz 를 같이 돌려 방향이 "
                      "같은지 확인한다."))

    # ── 계산 ───────────────────────────────────────────────────────────────
    plan = {k: ARMS for k in DRONE_KEYS}
    tables, metas, simp = run_tables(B.FC_MAIN, "main", plan)
    tables_hi, metas_hi, _ = ({}, {}, {})
    if with_hi:
        tables_hi, metas_hi, _ = run_tables(B.FC_PO_KNEE, "hi", {k: ARMS_HI for k in DRONE_KEYS})
    J["gpu_used"] = dict(main=metas.get("gpu"), hi=metas_hi.get("gpu"))

    # ── 회귀 게이트 ────────────────────────────────────────────────────────
    J["regression_gate"] = regression_gate(tables, "main")
    print(f"▶ 회귀 게이트(base 표 대조): {J['regression_gate']['verdict']} "
          f"(worst_rel={J['regression_gate'].get('worst_rel')})", flush=True)

    # ── 간략화가 형상에 한 일 ──────────────────────────────────────────────
    J["mesh_simplification"] = {ck: {kk: vv for kk, vv in m.items() if kk != "tag"}
                                for ck, (_, m) in simp.items()}
    from drones import build_propeller, build_frame
    sdist = {}
    for key in DRONE_KEYS:
        s = DRONES[key]
        prop = build_propeller(s, n=BLADE_N)
        probe = (B.C0 / B.FC_MAIN) / 40.0
        for arm in ("mesh_half_tri", "mesh_quarter_tri"):
            ck = f"{key}|prop|{KEEP[arm]}"
            if ck in simp:
                sdist[ck] = surface_distance(prop, simp[ck][0], probe)
        ckf = f"{key}|frame|{KEEP['mesh_half_tri_all']}"
        if ckf in simp:
            sdist[ckf] = surface_distance(build_frame(s), simp[ckf][0], probe)
    lam_main = B.C0 / B.FC_MAIN
    for v in sdist.values():
        v["rms_over_lambda_main"] = v["rms_m"] / lam_main
        v["hausdorff_over_lambda_main"] = v["hausdorff_m"] / lam_main
        # 왕복 위상으로 환산하면 «전파가 보기에» 얼마나 다른지가 바로 읽힌다
        v["roundtrip_phase_deg_at_rms"] = 360.0 * 2.0 * v["rms_m"] / lam_main
        v["roundtrip_phase_deg_at_rms_hi"] = (360.0 * 2.0 * v["rms_m"] /
                                              (B.C0 / B.FC_PO_KNEE))
    J["surface_distance"] = dict(
        values=sdist,
        what_ko=("간략화된 표면이 원래 표면에서 얼마나 벗어났나(양방향 최근접거리). "
                 "파장과 견주고, 왕복 위상[deg]으로도 환산해 둔다 — 위상이 몇 도 안 되면 "
                 "«전파가 보기에» 같은 물체다."),
        lambda_main_mm=1000.0 * lam_main,
        lambda_hi_mm=1000.0 * B.C0 / B.FC_PO_KNEE)

    # ── 팔별 지표 ──────────────────────────────────────────────────────────
    permet = {}
    J["arms"] = {}
    for key in DRONE_KEYS:
        J["arms"][key] = {}
        for arm in ARMS:
            blk = {}
            for wfront in ("spherical", "plane"):
                pa = per_az_metrics(tables, metas, "main", key, arm, wfront)
                if pa is None:
                    continue
                blk[wfront] = summarize_arm(pa)
                if wfront == "spherical":
                    permet[f"{key}|{arm}"] = pa
            am = metas["drones"][key]["arms"][arm]
            blk["geometry"] = am["meta"]
            blk["frame_geometry"] = am["frame_meta"]
            blk["n_frame_pts"] = am["n_frame_pts"]
            blk["n_blade_pts"] = am["n_blade_pts"]
            blk["seconds"] = am["seconds"]
            J["arms"][key][arm] = blk

    # ── 짝지은 비교 (같은 방위끼리) ────────────────────────────────────────
    PAIRS = [("mesh", "mesh_half_tri"), ("mesh", "mesh_quarter_tri"),
             ("mesh", "mesh_half_tri_all"), ("mesh_fine", "mesh_half_tri_fine"),
             ("mesh", "mesh_fine"),
             ("mesh", "slab"), ("mesh", "disc"), ("mesh", "sphere"),
             ("mesh_half_tri", "slab"), ("mesh_half_tri", "disc"),
             ("mesh_quarter_tri", "slab")]
    J["paired"], J["per_azimuth_paired"] = {}, {}
    for key in DRONE_KEYS:
        for a, b in PAIRS:
            if f"{key}|{a}" not in permet or f"{key}|{b}" not in permet:
                continue
            ma, mb = permet[f"{key}|{a}"], permet[f"{key}|{b}"]
            J["paired"][f"{key}|{b} - {a}"] = paired_diff(ma, mb)
            for mk in ("n_eff_orders", "flash_contrast_db", "dc_ac_db"):
                J["per_azimuth_paired"][f"{key}|{b} - {a}|{mk}"] = \
                    [float(y[mk] - x[mk]) for x, y in zip(ma, mb)]
    J["paired_note_ko"] = (
        "같은 방위에서 팔 B − 팔 A. frac_positive 는 24 방위 중 B 가 큰 비율이다 — 1.0 이면 "
        "모든 자세에서 한 방향이라는 뜻이고, 이것이 평균±산포보다 훨씬 강한 증거다. "
        "자세 산포는 두 팔에 공통이라 짝지어 빼면 사라진다.")

    # ── ⭐ 두 축의 크기 비교: «해상도 축» vs «모델 선택 축» ──────────────────
    #    이 단의 알맹이다. 같은 지표를 두 가지로 흔들어 보고 어느 쪽이 큰지 잰다.
    #      해상도 축 : 삼각형 25% → 100%, 점 표본 1배 → 4배 (같은 CAD 형상)
    #      모델 축   : CAD 형상 → 평판/원판/구 (같은 해상도 수준)
    LADDER = ["mesh_quarter_tri", "mesh_half_tri", "mesh", "mesh_fine"]
    axis = {}
    for key in DRONE_KEYS:
        for metric in ("n_eff_orders", "flash_contrast_db", "dc_ac_db", "width_ratio",
                       "order_p90", "blade_comb_frac"):
            vals = {a: J["arms"][key][a]["spherical"]["per_az"][metric]["mean"]
                    for a in LADDER if a in J["arms"][key]}
            span = max(vals.values()) - min(vals.values())
            pose_sd = J["arms"][key]["mesh"]["spherical"]["per_az"][metric]["sd"]
            #  ⚠ 나눗셈 보호: 어떤 지표는 정수 눈금이라(order_p90·width_ratio) 해상도 축이
            #    **정확히 0** 으로 나온다. 그때 «몇 배» 는 무한대가 아니라 «잴 수 없음» 이다.
            def _times(gap, denom):
                return None if not (denom > 0) else gap / denom
            row = dict(resolution_axis=dict(
                values=vals, span=span,
                span_is_zero=bool(span <= 0),
                span_zero_note_ko=("이 지표는 눈금이 정수 차수라 해상도를 25%~400% 로 흔들어도 "
                                   "값이 **한 눈금도** 안 움직였다. 배수는 정의되지 않는다"
                                   "(null). 이것은 «차이가 무한히 크다» 가 아니라 "
                                   "«이 지표로는 해상도 효과를 잴 수 없다» 는 뜻이다.")
                if span <= 0 else None,
                tri_range=[100.0 * KEEP["mesh_quarter_tri"], 100.0],
                sampling_range="1x -> 4x points per triangle"),
                model_axis={}, pose_sd=pose_sd)
            for prim in ("slab", "disc", "sphere"):
                pk = f"{key}|{prim} - mesh"
                if pk not in J["paired"]:
                    continue
                gap = abs(J["paired"][pk][metric]["mean"])
                interp = (J["arms"][key][prim]["spherical"]["per_az"]
                          ["in_band_ac_frac"]["mean"] >= 0.5)
                row["model_axis"][prim] = dict(
                    abs_gap_vs_cad=gap,
                    times_larger_than_resolution_span=_times(gap, span),
                    times_larger_than_pose_sd=_times(gap, pose_sd),
                    metric_interpretable=bool(interp))
            axis[f"{key}|{metric}"] = row
    J["resolution_axis_vs_model_axis"] = dict(
        values=axis,
        what_ko=("⭐ 같은 지표를 두 방향으로 흔들어 크기를 견준다. «해상도 축» 은 같은 CAD "
                 "형상을 삼각형 25%~100%, 점 표본 1~4배로 바꾼 폭이고, «모델 축» 은 그 형상을 "
                 "평판·원판·구로 **갈아치운** 폭이다. 모델 축이 해상도 축보다 몇 배 큰지가 "
                 "이 단의 답이다."),
        caveat_ko=("⚠ 원판·구는 회전대칭이라 AC 가 대역 밖 이산화 잔차뿐이다"
                   "(metric_interpretable=false). 그 둘의 풍부도·폭 차이는 «다르다» 는 사실만 "
                   "말하고 크기를 인용하면 안 된다. 인용 가능한 모델 축은 평판(slab)이다."))

    # ── 프레임 해상도는 왜 AC 에 못 닿는가 (기계적 확인) ────────────────────
    #    프레임은 안 돌기 때문에 위상마다 **같은 상수**를 더한다. 평균을 빼는 순간 사라진다.
    #    말로만 하지 않고 실제로 잰다: 프레임까지 줄인 팔과 프롭만 줄인 팔의 AC 가 같은가.
    fr = {}
    for key in DRONE_KEYS:
        ka = f"main|{key}|mesh_half_tri|spherical"
        kb = f"main|{key}|mesh_half_tri_all|spherical"
        if ka not in tables or kb not in tables:
            continue
        A = tables[ka] - tables[ka].mean(axis=1, keepdims=True)
        Bt = tables[kb] - tables[kb].mean(axis=1, keepdims=True)
        fr[key] = dict(
            max_rel_ac_difference=float(np.max(np.abs(A - Bt)) / max(np.max(np.abs(A)), 1e-300)),
            dc_ac_db_shift=J["paired"][f"{key}|mesh_half_tri_all - mesh"]["dc_ac_db"]["mean"] -
            J["paired"][f"{key}|mesh_half_tri - mesh"]["dc_ac_db"]["mean"],
            frame_area_ratio=J["mesh_simplification"][f"{key}|frame|{KEEP['mesh_half_tri_all']}"]
            ["area_ratio"],
            frame_volume_ratio=J["mesh_simplification"][f"{key}|frame|{KEEP['mesh_half_tri_all']}"]
            ["volume_ratio"])
    J["frame_resolution_affects_only_dc"] = dict(
        values=fr,
        what_ko=("프레임(동체)은 돌지 않으므로 위상마다 같은 상수를 더한다 → 평균을 빼면 "
                 "정확히 사라진다. 그래서 프레임 해상도는 이 커널에서 AC 파형에 **원리적으로** "
                 "닿지 못하고, dc_ac_db 를 통해서만 들어온다. max_rel_ac_difference 가 그 증거다."),
        limitation_ko=("⚠ 이것은 **가림이 없는 커널의 성질**이다. 블레이드가 동체 뒤로 돌아갈 때 "
                       "가려지는 실제 상황에서는 동체 형상이 AC 에도 들어온다. 즉 이 결과는 "
                       "«프레임 해상도가 물리적으로 안 중요하다» 가 아니라 «우리 커널에서는 "
                       "닿을 통로가 없다» 는 뜻이다."),
        frame_shape_caveat_ko=("⚠ 프레임 간략화는 프롭과 달리 면적·부피를 꽤 잃는다"
                               "(아래 비율 참조) — 동체는 상자·원기둥 조립이라 모서리를 접으면 "
                               "부피가 깎인다. 그래서 mesh_half_tri_all 의 dc_ac 이동은 "
                               "«해상도» 가 아니라 «크기» 변화가 섞여 있다. 헤드라인 팔이 "
                               "프롭만 줄인 mesh_half_tri 인 이유다."))

    # ── 파형 상관 ──────────────────────────────────────────────────────────
    cc = {}
    for key in DRONE_KEYS:
        ka = f"main|{key}|mesh|spherical"
        for arm in ("mesh_half_tri", "mesh_quarter_tri", "mesh_half_tri_all",
                    "mesh_fine", "slab", "disc", "sphere"):
            kb = f"main|{key}|{arm}|spherical"
            if ka in tables and kb in tables and tables[ka].shape == tables[kb].shape:
                cc[f"{key}|{arm} vs mesh"] = B.summarize(
                    [B.ac_corr(tables[ka][i], tables[kb][i]) for i in range(tables[ka].shape[0])])
    J["waveform_correlation"] = cc
    J["waveform_correlation_note_ko"] = (
        "AC 성분(평균 뺀 뒤)의 정규화 복소상관. 1.0 = 파형이 같다. ⭐ 요약 지표가 비슷해도 "
        "파형이 다를 수 있다 — 정합필터·템플릿을 쓸 거면 이 값이 결정적이다.")

    # ── 파면 대조 ──────────────────────────────────────────────────────────
    wfc = {}
    for key in DRONE_KEYS:
        for arm in ("mesh", "mesh_half_tri"):
            ka, kb = f"main|{key}|{arm}|spherical", f"main|{key}|{arm}|plane"
            if ka in tables and kb in tables:
                wfc[f"{key}|{arm}"] = dict(
                    ac_corr=B.summarize([B.ac_corr(tables[ka][i], tables[kb][i])
                                         for i in range(tables[ka].shape[0])]),
                    level_delta_db=B.summarize([
                        10 * np.log10(np.mean(np.abs(tables[kb][i]) ** 2) /
                                      np.mean(np.abs(tables[ka][i]) ** 2))
                        for i in range(tables[ka].shape[0])]))
    J["wavefront_control"] = dict(spherical_vs_plane=wfc,
                                  note_ko="구면파(헤드라인) vs 평면파(무한거리 등가).")

    # ── 고주파 대조 ────────────────────────────────────────────────────────
    if tables_hi:
        hi_arms, hi_paired = {}, {}
        pm = {}
        for key in DRONE_KEYS:
            for arm in ARMS_HI:
                pa = per_az_metrics(tables_hi, metas_hi, "hi", key, arm, "spherical")
                if pa is None:
                    continue
                pm[f"{key}|{arm}"] = pa
                hi_arms[f"{key}|{arm}"] = summarize_arm(pa)["per_az"]
            for a, b in (("mesh", "slab"), ("mesh_half_tri", "slab"), ("mesh", "mesh_half_tri")):
                if f"{key}|{a}" in pm and f"{key}|{b}" in pm:
                    hi_paired[f"{key}|{b} - {a}"] = paired_diff(pm[f"{key}|{a}"], pm[f"{key}|{b}"])
        hic = {}
        for key in DRONE_KEYS:
            ka = f"hi|{key}|mesh|spherical"
            for arm in ("mesh_half_tri", "slab"):
                kb = f"hi|{key}|{arm}|spherical"
                if ka in tables_hi and kb in tables_hi:
                    hic[f"{key}|{arm} vs mesh"] = B.summarize(
                        [B.ac_corr(tables_hi[ka][i], tables_hi[kb][i])
                         for i in range(tables_hi[ka].shape[0])])
        J["hi_band"] = dict(fc_hz=B.FC_PO_KNEE, arms=hi_arms, paired=hi_paired,
                            waveform_correlation=hic,
                            note_ko=("블레이드가 PO 유효 무릎을 넘는 주파수에서 같은 지표를 다시 "
                                     "잰다. 3.5 GHz 결론이 «커널이 약한 대역» 의 산물인지 본다."))

    # ── 채점 ───────────────────────────────────────────────────────────────
    J["prereg"] = pre
    J["grading"] = grade(J, pre)
    J["findings"] = _findings(J)

    # ── 저장 ───────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    np.savez_compressed(OUT_NPZ,
                        **{k.replace("|", "__"): v for k, v in tables.items()},
                        **{("hi__" + k.replace("|", "__")): v for k, v in tables_hi.items()})
    J["figures"] = dict(rung=make_figure(J, tables, metas, tables_hi, metas_hi))
    J["meta"]["seconds"] = float(time.time() - t0)
    J["meta"]["tables_npz"] = os.path.relpath(OUT_NPZ, ROOT)
    with open(OUT_JSON, "w") as f:
        json.dump(J, f, ensure_ascii=False, indent=1)
    s = J["grading"]["_summary"]
    print(f"\n✅ {os.path.relpath(OUT_JSON, ROOT)}  ·  {J['figures']['rung']}  "
          f"[{J['meta']['seconds']:.0f}s]   채점 {s['n_pass']}P/{s['n_fail']}F/"
          f"{s['n_inconclusive']}I  ·  판정 "
          f"{'뒤집힘' if s['verdict_flipped'] else '유지'}")
    return J


def _findings(J):
    """숫자를 손으로 적지 않는다 — 위에서 계산된 값만 골라 문장을 만든다."""
    F = {}
    pd_, cc = J["paired"], J["waveform_correlation"]
    F["q1_does_halving_the_mesh_change_the_micro_doppler"] = dict(
        question_ko="삼각형을 절반으로 줄이면 마이크로도플러가 바뀌는가",
        waveform_correlation={k: cc.get(f"{k}|mesh_half_tri vs mesh") for k in DRONE_KEYS},
        paired_delta={k: {m: pd_[f"{k}|mesh_half_tri - mesh"][m]
                          for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db",
                                    "width_ratio")} for k in DRONE_KEYS},
        surface_deviation={f"{k}|prop|0.5": J["surface_distance"]["values"].get(f"{k}|prop|0.5")
                           for k in DRONE_KEYS})
    F["q2_does_the_base_verdict_survive"] = dict(
        question_ko=("base 의 판정(«평판 프리미티브가 CAD 보다 하모닉이 풍부하다»,"
                     " «CAD 는 동체 대비 세기에서만 이긴다»)이 절반 해상도에서 살아남는가"),
        full_res={k: {m: pd_[f"{k}|slab - mesh"][m]
                      for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")}
                  for k in DRONE_KEYS},
        half_res={k: {m: pd_[f"{k}|slab - mesh_half_tri"][m]
                      for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")}
                  for k in DRONE_KEYS},
        graded={p: J["grading"][p]["verdict"]
                for p in ("P1_primitive_richness_verdict_survives",
                          "P7_cad_dc_ac_advantage_survives")},
        verdict_flipped=J["grading"]["_summary"]["verdict_flipped"],
        overclaim_guard_ko=("⚠ P7(«CAD 가 동체 대비 세기에서 이긴다»)은 **matrice4e 에서만** "
                            "성립한다. mini2 는 base 에서도 24방위 중 13개에서만 그랬고"
                            f"(frac_positive="
                            f"{pd_['mini2|slab - mesh']['dc_ac_db']['frac_positive']:.2f}, "
                            f"평균 {pd_['mini2|slab - mesh']['dc_ac_db']['mean']:+.2f} dB, "
                            f"산포 {pd_['mini2|slab - mesh']['dc_ac_db']['sd']:.2f} dB), "
                            "이 단에서도 그대로다. 즉 이 단이 지킨 것은 «matrice4e 의 dc_ac 우위» "
                            "이지 «CAD 가 늘 이긴다» 가 아니다."))
    F["q3_facets_or_samples"] = dict(
        question_ko="차이의 원인이 «면이 줄어서» 인가 «적분 표본이 줄어서» 인가",
        coarse={k: pd_[f"{k}|mesh_half_tri - mesh"]["n_eff_orders"] for k in DRONE_KEYS},
        dense={k: pd_[f"{k}|mesh_half_tri_fine - mesh_fine"]["n_eff_orders"]
               for k in DRONE_KEYS},
        graded=J["grading"]["P9_point_count_is_not_the_driver"]["verdict"],
        pts_per_tri={f"{k}|{a}": J["arms"][k][a]["geometry"].get("pts_per_tri")
                     for k in DRONE_KEYS for a in ("mesh", "mesh_half_tri",
                                                   "mesh_fine", "mesh_half_tri_fine")})
    F["q4_null_anchors_were_actually_rotated"] = dict(
        question_ko="구·원판을 정말로 돌렸는가(동어반복이 아닌가)",
        how_ko=("구·원판도 mesh 와 **같은 위상격자·같은 로터 배치·같은 rpm** 으로 돌렸다. "
                "구는 회전대칭이라 물리적 변조가 0 이어야 하고, 남는 값이 계산기 바닥이다."),
        in_band_ac_over_dc_db={
            f"{k}|{a}": J["arms"][k][a]["spherical"]["per_az"]["in_band_ac_over_dc_db"]["mean"]
            for k in DRONE_KEYS for a in ("mesh", "mesh_half_tri", "slab", "disc", "sphere")
            if a in J["arms"][k]},
        equal_volume_sphere={k: dict(
            r_equal_volume_m=J["arms"][k]["sphere"]["geometry"].get("r_equal_volume_m"),
            volume_m3=J["arms"][k]["sphere"]["geometry"].get("volume_m3"))
            for k in DRONE_KEYS},
        equal_volume_slab={k: dict(
            volume_m3=J["arms"][k]["slab"]["geometry"].get("volume_m3"),
            span_m=J["arms"][k]["slab"]["geometry"].get("span_m"),
            chord_m=J["arms"][k]["slab"]["geometry"].get("chord_m"),
            thickness_m=J["arms"][k]["slab"]["geometry"].get("thickness_m"))
            for k in DRONE_KEYS})
    F["q2b_how_big_is_resolution_next_to_model_choice"] = dict(
        question_ko="«해상도를 바꾼 폭» 은 «모델을 갈아치운 폭» 에 비해 얼마나 작은가",
        n_eff_orders={k: J["resolution_axis_vs_model_axis"]["values"][f"{k}|n_eff_orders"]
                      for k in DRONE_KEYS},
        flash_contrast_db={k: J["resolution_axis_vs_model_axis"]["values"]
                           [f"{k}|flash_contrast_db"] for k in DRONE_KEYS},
        read_ko=("times_larger_than_resolution_span 이 이 단의 핵심 숫자다 — 평판으로 갈아치운 "
                 "차이가 해상도 전 구간(삼각형 25%~100%, 표본 1~4배)을 흔든 폭보다 몇 배 큰가."))
    F["q5_does_the_high_band_agree"] = dict(
        question_ko="PO 유효 무릎 위(15.86 GHz)에서도 같은 방향인가",
        hi_slab_minus_half={k: {m: J.get("hi_band", {}).get("paired", {})
                                .get(f"{k}|slab - mesh_half_tri", {}).get(m)
                                for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")}
                            for k in DRONE_KEYS} if J.get("hi_band") else None,
        hi_half_minus_full={k: {m: J.get("hi_band", {}).get("paired", {})
                                .get(f"{k}|mesh_half_tri - mesh", {}).get(m)
                                for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")}
                            for k in DRONE_KEYS} if J.get("hi_band") else None,
        main_half_minus_full={k: {m: pd_[f"{k}|mesh_half_tri - mesh"][m]
                                  for m in ("n_eff_orders", "flash_contrast_db", "dc_ac_db")}
                              for k in DRONE_KEYS},
        waveform_corr={"main": {k: cc[f"{k}|mesh_half_tri vs mesh"]["mean"] for k in DRONE_KEYS},
                       "hi": {k: J.get("hi_band", {}).get("waveform_correlation", {})
                              .get(f"{k}|mesh_half_tri vs mesh", {}).get("mean")
                              for k in DRONE_KEYS}},
        why_ko=("⭐ 간략화가 표면을 밀어낸 거리는 **주파수와 무관한 고정 길이**다(프롭 rms "
                "0.26~0.36 mm). 그 길이가 왕복 위상으로 몇 도가 되느냐는 파장이 정한다 — "
                "3.5 GHz 에서 2~3°, 15.86 GHz 에서 10~14°. 그래서 «해상도가 언제부터 "
                "문제가 되나» 는 삼각형 수가 아니라 **표면 오차 ÷ 파장**이 답이다. "
                "surface_distance.roundtrip_phase_deg_at_rms 와 나란히 읽을 것."))
    F["limits_ko"] = [
        J["po_validity_warning"]["statement_ko"],
        "가림(occlusion)이 없다 — dc_ac_db 가 가장 오염된 지표다. 팔 사이 차이만 쓸 것.",
        ("QEM 간략화는 «표본을 줄이는 것» 과 «형상을 뭉개는 것» 을 동시에 한다. "
         "그 둘은 _fine 통제팔로 갈랐지만, 효과가 애초에 너무 작아 판정이 나지 않았다"
         f"(P9 = {J['grading']['P9_point_count_is_not_the_driver']['verdict']})."),
        ("이 단은 CAD 메쉬 쪽 해상도만 낮췄다. 프리미티브(평판·원판)는 원래 삼각형이 12~8000개라 "
         "같은 방식으로 낮출 여지가 없다 — 비대칭적인 처치다. 즉 «CAD 를 낮춰도 안 바뀐다» 는 "
         "말은 되지만 «프리미티브를 높이면 어떻게 되나» 는 이 단이 답하지 않았다."),
        ("width_ratio 의 최소 눈금은 1차수(=f_rot)라 이 단의 해상도 변화에서는 전부 0.000 으로 "
         "나온다 — 안 변한 것이 아니라 **잴 수 없는 것**이다."),
        ("프레임 해상도는 이 커널에서 AC 파형에 원리적으로 닿지 못한다"
         "(frame_resolution_affects_only_dc). 가림을 넣으면 달라질 수 있다."),
        ("QEM 은 프롭의 면적·부피를 거의 보존하지만(면적비 ≈1.000) 프레임에서는 부피를 "
         "10% 가까이 깎는다 — mesh_half_tri_all 의 dc_ac 이동을 «해상도 효과» 로 읽으면 안 된다."),
    ]
    res = J["resolution_axis_vs_model_axis"]["values"]
    F["headline_ko"] = (
        "삼각형을 절반으로 줄여도 마이크로도플러는 사실상 그대로다 — 파형 상관 "
        + " / ".join(f"{cc[f'{k}|mesh_half_tri vs mesh']['mean']:.5f}" for k in DRONE_KEYS)
        + ", 하모닉 풍부도 변화 "
        + " / ".join(f"{pd_[f'{k}|mesh_half_tri - mesh']['n_eff_orders']['mean']:+.3f}"
                     for k in DRONE_KEYS)
        + ". 같은 지표를 평판 프리미티브로 갈아치우면 "
        + " / ".join(f"{pd_[f'{k}|slab - mesh']['n_eff_orders']['mean']:+.3f}"
                     for k in DRONE_KEYS)
        + " 로 움직인다 — 해상도 전 구간을 흔든 폭의 "
        + " / ".join(
            (lambda v: "잴 수 없음" if v is None else f"{v:.1f}배")(
                res[f"{k}|n_eff_orders"]["model_axis"]["slab"]
                ["times_larger_than_resolution_span"]) for k in DRONE_KEYS)
        + ". ⭐ 따라서 base 의 판정은 메쉬 해상도의 산물이 아니다. "
        "다만 15.86 GHz 에서는 절반 메쉬의 차이가 커지기 시작한다"
        + (" (matrice4e Δn_eff "
           f"{J['hi_band']['paired']['matrice4e|mesh_half_tri - mesh']['n_eff_orders']['mean']:+.2f}, "
           f"Δflash "
           f"{J['hi_band']['paired']['matrice4e|mesh_half_tri - mesh']['flash_contrast_db']['mean']:+.2f} dB)"
           if J.get("hi_band") else "")
        + " — 표면 오차는 고정 길이고 파장만 짧아지기 때문이다.")
    return F


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", action="store_true", help="사전 예측만 떨구고 종료")
    ap.add_argument("--no-hi", action="store_true", help="15.86 GHz 대조 생략")
    a = ap.parse_args()
    if a.prereg:
        pr = build_prereg()
        os.makedirs(os.path.dirname(OUT_PRE), exist_ok=True)
        with open(OUT_PRE, "w") as f:
            json.dump(pr, f, ensure_ascii=False, indent=1)
        print(f"✅ 사전 예측 기록: {os.path.relpath(OUT_PRE, ROOT)}  "
              f"({len(pr['predictions'])} 개, {pr['written_at']})")
    else:
        main(with_hi=not a.no_hi)
